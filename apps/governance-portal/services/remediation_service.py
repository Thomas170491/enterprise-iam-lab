"""
Remediation of revoked access review items: compare captured evidence with live
Keycloak access, and remove the user's direct role mapping where that ends the access.
"""

import json
from typing import Any

from extensions import db
from models import AccessReviewItem
from services.access_review_service import (
    get_access_review_for_manager,
    resolve_user_client_role_sources,
)
from services.audit_service import record_audit_event
from services.role_service import remove_identity_client_role


def _is_direct_mapping(grant: dict[str, Any], role_id: str) -> bool:
    """
    Return whether a grant is the user's own direct mapping of exactly this role.
    """
    return (
        grant["type"] == "user"
        and grant["assigned_role_id"] == role_id
        and grant["composite_path"] == []
    )


def assess_live_access(
    item: AccessReviewItem,
    live_roles: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compare a captured item with live role evidence and report what removing its direct role would do.

    drift is "none" when the live grants equal the captured ones (in any order),
    "role_removed" when the role is no longer effective, and "sources_changed" otherwise.
    drift is evidence to record; it does not choose the remediation action. That is decided
    by direct_grant_present and other_grants_present. Legacy items captured with
    grant_sources == [] always show sources_changed.
    direct_grant_present is true when a user grant maps exactly this role, so removing
    the user's direct role mapping removes that grant. other_grants_present is true when
    any live grant would survive that removal (a group grant or a composite path).
    """
    live_role = next(
        (role for role in live_roles if role["role_id"] == item.role_id), None
    )

    if live_role is None:
        return {
            "drift": "role_removed",
            "direct_grant_present": False,
            "other_grants_present": False,
        }

    live_grants = live_role["grant_sources"]

    captured = {json.dumps(grant, sort_keys=True) for grant in item.grant_sources}
    live = {json.dumps(grant, sort_keys=True) for grant in live_grants}

    return {
        "drift": "none" if captured == live else "sources_changed",
        "direct_grant_present": any(
            _is_direct_mapping(grant, item.role_id) for grant in live_grants
        ),
        "other_grants_present": any(
            not _is_direct_mapping(grant, item.role_id) for grant in live_grants
        ),
    }


def get_live_access_assessment(
    item: AccessReviewItem,
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
) -> dict[str, Any]:
    """
    Read the item's role from Keycloak and assess it against the captured evidence.

    Only the item's own role is traced, so an untraceable unrelated role cannot block it.
    Keycloak failures and role_source_untraceable propagate: remediation must not act on them.
    """
    live_roles = resolve_user_client_role_sources(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=item.user_id,
        target_client_name=item.client_name,
        role_ids={item.role_id},
    )

    return assess_live_access(item, live_roles)


def remediate_access_review_item_with_audit(
    review_id: int,
    item_id: int,
    manager_user_id: str,
    actor_username: str,
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
) -> AccessReviewItem:
    """
    Remediate one revoked item of an open campaign owned by the manager.

    Live access is read first and decides the action:
    - the role is no longer effective: completed, no Keycloak write ("already_removed");
    - no direct mapping of the role: incomplete, no Keycloak write ("manual_required");
    - otherwise the direct mapping is removed through role_service, which audits the
      attempt before calling Keycloak and refuses a role whose ID is not the item's;
      live access is read again: completed if the role is gone, else incomplete
      ("direct_role_removed").

    role_service commits its own role.remove audit rows. The item's remediation status
    and the access_review.remediation audit event are committed together at the end,
    and the status only moves from pending, so a concurrent or repeated run cannot
    overwrite a result. Any failure before that leaves the item pending for a retry.
    """
    keycloak_args = {
        "admin_api_url": admin_api_url,
        "token_url": token_url,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    try:
        campaign = get_access_review_for_manager(review_id, manager_user_id)

        if campaign.status != "open":
            raise ValueError("access_review_not_open")

        item = db.session.get(AccessReviewItem, item_id)

        if item is None or item.review_id != campaign.id:
            raise ValueError("access_review_item_not_found")

        if item.decision != "revoke" or item.remediation_status != "pending":
            raise ValueError("access_review_item_not_pending_remediation")

        before = get_live_access_assessment(item, **keycloak_args)

        if before["drift"] == "role_removed":
            action, result = "already_removed", "completed"

        elif not before["direct_grant_present"]:
            action, result = "manual_required", "incomplete"

        else:
            remove_identity_client_role(
                **keycloak_args,
                user_id=item.user_id,
                target_client_name=item.client_name,
                role_name=item.role_name,
                actor_user_id=manager_user_id,
                actor_username=actor_username,
                expected_role_id=item.role_id,
            )

            after = get_live_access_assessment(item, **keycloak_args)
            action = "direct_role_removed"
            result = "completed" if after["drift"] == "role_removed" else "incomplete"

        updated = db.session.execute(
            db.update(AccessReviewItem)
            .where(
                AccessReviewItem.id == item.id,
                AccessReviewItem.remediation_status == "pending",
            )
            .values(remediation_status=result)
            .execution_options(synchronize_session=False)
        )

        if updated.rowcount != 1:
            raise ValueError("access_review_item_not_pending_remediation")

        record_audit_event(
            actor_user_id=manager_user_id,
            actor_username=actor_username,
            action="access_review.remediation",
            target_type="access_review_item",
            target_id=str(item.id),
            outcome="success",
            details={
                "source": "governance-portal",
                "service_client": client_id,
                "review_id": review_id,
                "user_id": item.user_id,
                "client_name": item.client_name,
                "role_id": item.role_id,
                "role_name": item.role_name,
                "drift": before["drift"],
                "action": action,
                "remediation_status": result,
            },
            commit=False,
        )

        db.session.commit()

    except Exception:
        db.session.rollback()
        raise

    db.session.refresh(item)
    return item
