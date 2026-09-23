import logging
from typing import Any

from services.audit_service import record_audit_event
from services.exceptions import (
    AuditPersistenceError,
    KeycloakAdminAPIError,
    RoleAdministrationPolicyError,
)
from services.keycloak_admin_service import (
    get_client_uuid,
    get_client_role,
    get_effective_client_roles,
    assign_client_role,
    remove_client_role,
)

from services.sod_service import (
    SOD_ALLOW,
    evaluate_role_assignment,
)

from extensions import db
from models import ManagedRole

# The Governance Portal is currently allowed to administer
# application access for the Employee Portal only.
#
# This prevents a ROLE_MANAGER from using the same
# functionality to modify Governance Portal administrative roles.


logger = logging.getLogger(__name__)


def _record_role_audit_event(
    actor_user_id: str,
    actor_username: str,
    action: str,
    user_id: str,
    target_client_name: str,
    role: dict[str],
    service_client_id: str,
    outcome: str,
) -> Any:
    """
    Persist an audit record for a privileged role mutation.

    The human administrator remains the actor.
    The Keycloak service account is recorded separately
    as the technical executor.
    """

    return record_audit_event(
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        action=action,
        target_type="identity",
        target_id=user_id,
        target_name=None,
        outcome=outcome,
        details={
            "source": "governance-portal",
            "service_client": service_client_id,
            "client_name": target_client_name,
            "role_id": role["id"],
            "role_name": role["name"],
        },
    )


def _ensure_managed_client(target_client_name: str) -> None:
    """
    Reject role changes for clients that are outside the
    Governance Portal's administration scope.
    """

    managed_role_id = db.session.execute(
        db.select(ManagedRole.id)
        .where(
            target_client_name == ManagedRole.client_name,
            ManagedRole.enabled.is_(True),
        )
        .limit(1)
    ).scalar_one_or_none()

    if managed_role_id is None:
        raise RoleAdministrationPolicyError("unmanaged_client")


def _ensure_managed_role(target_client_name: str, role_name: str) -> None:
    """
    Reject role changes for roles that are outside the
    Governance Portal's administration scope.
    """
    managed_role_id = db.session.execute(
        db.select(ManagedRole.id).where(
            target_client_name == ManagedRole.client_name,
            role_name == ManagedRole.role_name,
            ManagedRole.enabled.is_(True),
        )
    ).scalar_one_or_none()

    if managed_role_id is None:
        raise RoleAdministrationPolicyError("unmanaged_role")


def _record_sod_audit_event(
    actor_user_id: str,
    actor_username: str,
    user_id: str,
    target_client_name: str,
    requested_role_name: str,
    current_role_names: list[str],
    service_client_id: str,
    sod_result: dict[str],
) -> None:
    """
    Persist the SoD evaluation result for a requested role assignment.
    """

    return record_audit_event(
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        action="sod.evaluate",
        target_type="identity",
        target_id=user_id,
        target_name=None,
        outcome=sod_result["decision"],
        details={
            "source": "governance-portal",
            "service_client": service_client_id,
            "client_name": target_client_name,
            "requested_role": requested_role_name,
            "current_roles": sorted(set(current_role_names)),
            "reason": sod_result["reason"],
            "rule_id": sod_result["rule_id"],
        },
    )


def get_managed_roles(
    target_client_name: str,
) -> list[str]:
    """
    Return the roles that Governance is allowed
    to administer for a managed client.
    """

    return (
        db.session.execute(
            db.select(ManagedRole.role_name)
            .where(
                target_client_name == ManagedRole.client_name,
                ManagedRole.enabled.is_(True),
            )
            .order_by(ManagedRole.role_name.asc())
        )
        .scalars()
        .all()
    )


def assign_identity_client_role(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
    target_client_name: str,
    role_name: str,
    actor_user_id: str,
    actor_username: str,
) -> dict[str]:
    """
    Assign a managed client role to an identity.

    This service coordinates the lower-level Keycloak
    Admin API operations required for role assignment.

    Privileged mutations are fail-closed if the initial
    audit event cannot be persisted.

    Assignments are evaluated against the identity's effective roles before mutation.
    """

    # ---------------------------------------------------------
    # 1. Enforce Governance policy
    # ---------------------------------------------------------

    _ensure_managed_client(target_client_name)

    _ensure_managed_role(target_client_name, role_name)

    effective_roles = get_effective_client_roles(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        user_id=user_id,
        target_client_name=target_client_name,
    )

    current_role_names = [role["name"] for role in effective_roles if role.get("name")]

    sod_result = evaluate_role_assignment(
        target_client_name=target_client_name,
        requested_role_name=role_name,
        current_role_names=current_role_names,
    )

    _record_sod_audit_event(
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        user_id=user_id,
        target_client_name=target_client_name,
        requested_role_name=role_name,
        current_role_names=current_role_names,
        service_client_id=client_id,
        sod_result=sod_result,
    )

    if sod_result["decision"] != SOD_ALLOW:
        raise RoleAdministrationPolicyError(f"sod_{sod_result['decision']}")

    # ---------------------------------------------------------
    # 2. Resolve Keycloak client
    # ---------------------------------------------------------

    # Keycloak's role-mapping API requires the client's
    # internal UUID rather than its human-readable clientId.
    client_uuid = get_client_uuid(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        client_name=target_client_name,
    )

    # ---------------------------------------------------------
    # 3. Resolve complete RoleRepresentation
    # ---------------------------------------------------------

    role = get_client_role(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        client_uuid=client_uuid,
        role_name=role_name,
    )

    # ---------------------------------------------------------
    # 4. Record mutation attempt
    # ---------------------------------------------------------

    # This audit event is intentionally NOT inside a try/except.
    #
    # If PostgreSQL cannot record the privileged operation,
    # AuditPersistenceError propagates and the Keycloak
    # mutation never happens.
    #
    # This gives us fail-closed behavior.
    _record_role_audit_event(
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        action="role.assign",
        user_id=user_id,
        target_client_name=target_client_name,
        role=role,
        service_client_id=client_id,
        outcome="attempted",
    )

    # ---------------------------------------------------------
    # 5. Perform Keycloak mutation
    # ---------------------------------------------------------

    try:
        assign_client_role(
            admin_api_url=admin_api_url,
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            user_id=user_id,
            client_uuid=client_uuid,
            role=role,
        )

    except KeycloakAdminAPIError:

        # The initial "attempted" audit record already exists.
        #
        # We now try to record the final failure result.
        # If this second audit write also fails, we must not
        # hide the original Keycloak error.
        try:
            _record_role_audit_event(
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                action="role.assign",
                user_id=user_id,
                target_client_name=target_client_name,
                role=role,
                service_client_id=client_id,
                outcome="failure",
            )

        except AuditPersistenceError:
            logger.exception("Failed to persist failed role assignment audit outcome")

        # Re-raise the original KeycloakAdminAPIError.
        raise

    # ---------------------------------------------------------
    # 6. Record successful mutation
    # ---------------------------------------------------------

    try:
        _record_role_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="role.assign",
            user_id=user_id,
            target_client_name=target_client_name,
            role=role,
            service_client_id=client_id,
            outcome="success",
        )

    except AuditPersistenceError:

        # The Keycloak mutation already succeeded.
        #
        # We cannot claim the assignment failed merely because
        # the second audit record could not be persisted.
        #
        # The original "attempted" record still exists.
        logger.exception("Failed to persist successful role assignment audit outcome")

    # ---------------------------------------------------------
    # 7. Return normalized result
    # ---------------------------------------------------------

    return {
        "user_id": user_id,
        "client_name": target_client_name,
        "role_id": role["id"],
        "role_name": role["name"],
    }


def remove_identity_client_role(
    admin_api_url: str,
    token_url: str,
    client_id: str,
    client_secret: str,
    user_id: str,
    target_client_name: str,
    role_name: str,
    actor_user_id: str,
    actor_username: str,
) -> dict[str, str]:
    """
    Remove a managed client role from an identity.

    This service coordinates the lower-level Keycloak
    Admin API operations required for role removal.

    Privileged mutations are fail-closed if the initial
    audit event cannot be persisted.
    """

    # ---------------------------------------------------------
    # 1. Enforce Governance policy
    # ---------------------------------------------------------

    _ensure_managed_client(target_client_name)

    _ensure_managed_role(target_client_name, role_name)
    # ---------------------------------------------------------
    # 2. Resolve Keycloak client
    # ---------------------------------------------------------

    client_uuid = get_client_uuid(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        client_name=target_client_name,
    )

    # ---------------------------------------------------------
    # 3. Resolve complete RoleRepresentation
    # ---------------------------------------------------------

    role = get_client_role(
        admin_api_url=admin_api_url,
        token_url=token_url,
        client_id=client_id,
        client_secret=client_secret,
        client_uuid=client_uuid,
        role_name=role_name,
    )

    # ---------------------------------------------------------
    # 4. Record mutation attempt
    # ---------------------------------------------------------

    # Fail closed if this cannot be persisted.
    _record_role_audit_event(
        actor_user_id=actor_user_id,
        actor_username=actor_username,
        action="role.remove",
        user_id=user_id,
        target_client_name=target_client_name,
        role=role,
        service_client_id=client_id,
        outcome="attempted",
    )

    # ---------------------------------------------------------
    # 5. Perform Keycloak mutation
    # ---------------------------------------------------------

    try:
        remove_client_role(
            admin_api_url=admin_api_url,
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            user_id=user_id,
            client_uuid=client_uuid,
            role=role,
        )

    except KeycloakAdminAPIError:

        # Record the failed operation, but preserve the
        # original Keycloak exception if auditing also fails.
        try:
            _record_role_audit_event(
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                action="role.remove",
                user_id=user_id,
                target_client_name=target_client_name,
                role=role,
                service_client_id=client_id,
                outcome="failure",
            )

        except AuditPersistenceError:
            logger.exception("Failed to persist failed role removal audit outcome")

        raise

    # ---------------------------------------------------------
    # 6. Record successful mutation
    # ---------------------------------------------------------

    try:
        _record_role_audit_event(
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action="role.remove",
            user_id=user_id,
            target_client_name=target_client_name,
            role=role,
            service_client_id=client_id,
            outcome="success",
        )

    except AuditPersistenceError:
        logger.exception("Failed to persist successful role removal audit outcome")

    # ---------------------------------------------------------
    # 7. Return normalized result
    # ---------------------------------------------------------

    return {
        "user_id": user_id,
        "client_name": target_client_name,
        "role_id": role["id"],
        "role_name": role["name"],
    }
