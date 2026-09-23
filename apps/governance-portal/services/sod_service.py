from models import ManagedRole, SoDRule
from extensions import db

SOD_ALLOW = "allow"
SOD_DENY = "deny"
SOD_REQUIRES_REVIEW = "requires_review"


def evaluate_role_assignment(
    target_client_name: str,
    requested_role_name: str,
    current_role_names: list,
) -> dict[str]:
    """
    Evaluate a requested client-role assignment against enabled SoD rules.

    The requested role and the identity's current roles are resolved through
    the managed-role catalogue. Each current role is checked against the
    requested role for an enabled segregation-of-duties rule.

    Returns a dictionary containing:
        decision: allow, deny, or requires_review.
        reason: A stable identifier explaining the decision.
        rule_id: The matching SoD rule ID, or None when no rule matched.

    Requests for unmanaged or disabled roles are denied by default.
    Deny rules take precedence over review rules across all matching role pairs.

    Held roles remain subject to SoD checks even when their catalogue
    entries are disabled.
    """

    requested_role = db.session.execute(
        db.select(ManagedRole).filter_by(
            client_name=target_client_name,
            role_name=requested_role_name,
            enabled=True,
        )
    ).scalar_one_or_none()

    if requested_role is None:
        return {"decision": SOD_DENY, "reason": "role_not_managed", "rule_id": None}

    current_roles = (
        db.session.execute(
            db.select(ManagedRole).where(
                ManagedRole.client_name == target_client_name,
                ManagedRole.role_name.in_(current_role_names),
            )
        )
        .scalars()
        .all()
    )

    review_rule = None

    for role in current_roles:

        current_role_id = role.id

        first_role_id, second_role_id = sorted([current_role_id, requested_role.id])

        matching_rule = db.session.execute(
            db.select(SoDRule).where(
                SoDRule.first_role_id == first_role_id,
                SoDRule.second_role_id == second_role_id,
                SoDRule.enabled.is_(True),
            )
        ).scalar_one_or_none()

        if matching_rule is not None:

            if matching_rule.outcome == SOD_DENY:
                return {
                    "decision": SOD_DENY,
                    "reason": "sod_rule_matched",
                    "rule_id": matching_rule.id,
                }

            if matching_rule.outcome == SOD_REQUIRES_REVIEW:
                review_rule = matching_rule

    if review_rule is not None:

        return {
            "decision": SOD_REQUIRES_REVIEW,
            "reason": "sod_rule_matched",
            "rule_id": review_rule.id,
        }

    return {
        "decision": SOD_ALLOW,
        "reason": "no_sod_conflict",
        "rule_id": None,
    }
