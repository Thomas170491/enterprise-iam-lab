from services.sod_service import (
    SOD_DENY,
    SOD_ALLOW,
    SOD_REQUIRES_REVIEW,
    evaluate_role_assignment,
)
from models import ManagedRole, SoDRule
from extensions import db
from unittest.mock import Mock


def test_unmanaged_request_role_is_denied(app):
    result = evaluate_role_assignment("employee-portal", "unknown-role", [])

    assert result["decision"] == SOD_DENY
    assert result["reason"] == "role_not_managed"
    assert result["rule_id"] is None


def test_managed_role_without_conflict_is_allowed(app):
    test_managed_role = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer"
    )

    db.session.add(test_managed_role)
    db.session.commit()

    result = evaluate_role_assignment("employee-portal", "finance-data-viewer", [])

    assert result["decision"] == SOD_ALLOW
    assert result["reason"] == "no_sod_conflict"
    assert result["rule_id"] is None
    from services.sod_service import SOD_DENY, SOD_ALLOW, evaluate_role_assignment


from models.managed_role import ManagedRole
from extensions import db


def test_unmanaged_request_role_is_denied(app):
    result = evaluate_role_assignment("employee-portal", "unknown-role", [])

    assert result["decision"] == SOD_DENY
    assert result["reason"] == "role_not_managed"
    assert result["rule_id"] is None


def test_managed_role_without_conflict_is_allowed(app):
    test_managed_role = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer"
    )

    db.session.add(test_managed_role)
    db.session.commit()

    result = evaluate_role_assignment("employee-portal", "finance-data-viewer", [])

    assert result["decision"] == SOD_ALLOW
    assert result["reason"] == "no_sod_conflict"
    assert result["rule_id"] is None


def test_matching_deny_rule_blocks_assignment(app):

    test_managed_role_deny_1 = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer"
    )

    test_managed_role_deny_2 = ManagedRole(
        client_name="employee-portal", role_name="security-data-viewer"
    )

    db.session.add_all([test_managed_role_deny_1, test_managed_role_deny_2])
    db.session.flush()

    first_role_id, second_role_id = sorted(
        [
            test_managed_role_deny_1.id,
            test_managed_role_deny_2.id,
        ]
    )

    test_sod = SoDRule(
        first_role_id=first_role_id,
        second_role_id=second_role_id,
        outcome=SOD_DENY,
        name="test",
    )

    db.session.add(test_sod)

    db.session.commit()

    result = evaluate_role_assignment(
        "employee-portal", "security-data-viewer", ["finance-data-viewer"]
    )

    assert result["decision"] == SOD_DENY
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == test_sod.id


def test_matching_review_rule_requires_review(app):
    """
    Verify that a review rule returns a requires-review decision.
    """
    current_role = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer"
    )

    requested_role = ManagedRole(
        client_name="employee-portal", role_name="operations-data-viewer"
    )

    db.session.add_all([current_role, requested_role])
    db.session.flush()

    first_role_id, second_role_id = sorted(
        [
            current_role.id,
            requested_role.id,
        ]
    )

    sod_test = SoDRule(
        name="Test Rule",
        first_role_id=first_role_id,
        second_role_id=second_role_id,
        outcome=SOD_REQUIRES_REVIEW,
    )

    db.session.add(sod_test)
    db.session.commit()

    result = evaluate_role_assignment(
        "employee-portal", "operations-data-viewer", ["finance-data-viewer"]
    )

    assert result["decision"] == SOD_REQUIRES_REVIEW
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == sod_test.id


def test_disabled_sod_rule_is_ignored(app):
    """
    Verify that a disabled SoD rule does not affect role assignment.
    """

    current_role = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer"
    )

    requested_role = ManagedRole(
        client_name="employee-portal", role_name="operations-data-viewer"
    )

    db.session.add_all([current_role, requested_role])
    db.session.flush()

    first_role_id, second_role_id = sorted(
        [
            current_role.id,
            requested_role.id,
        ]
    )

    sod_test = SoDRule(
        name="Test Rule",
        first_role_id=first_role_id,
        second_role_id=second_role_id,
        outcome=SOD_DENY,
        enabled=False,
    )

    db.session.add(sod_test)
    db.session.commit()

    result = evaluate_role_assignment(
        "employee-portal", "operations-data-viewer", ["finance-data-viewer"]
    )

    assert result["decision"] == SOD_ALLOW
    assert result["reason"] == "no_sod_conflict"
    assert result["rule_id"] is None


def test_disabled_requested_role_is_denied(app):
    """
    Verify that a disabled managed role is denied by default.
    """
    requested_role = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer", enabled=False
    )

    db.session.add(requested_role)
    db.session.commit()

    result = evaluate_role_assignment("employee-portal", "finance-data-viewer", [])

    assert result["decision"] == SOD_DENY
    assert result["reason"] == "role_not_managed"
    assert result["rule_id"] is None


def test_all_current_roles_are_checked_for_conflicts(app):
    """
    Verify that every current role is checked before allowing an assignment.
    """

    current_role = ManagedRole(
        client_name="employee-portal", role_name="operations-data-viewer"
    )

    conflicting_current_role = ManagedRole(
        client_name="employee-portal", role_name="finance-data-viewer"
    )

    requested_role = ManagedRole(
        client_name="employee-portal", role_name="security-data-viewer"
    )

    db.session.add_all([current_role, conflicting_current_role, requested_role])
    db.session.flush()

    first_role_id, second_role_id = sorted(
        [
            conflicting_current_role.id,
            requested_role.id,
        ]
    )

    sod_test = SoDRule(
        name="Test Rule",
        first_role_id=first_role_id,
        second_role_id=second_role_id,
        outcome=SOD_DENY,
    )

    db.session.add(sod_test)
    db.session.commit()

    result = evaluate_role_assignment(
        "employee-portal",
        "security-data-viewer",
        ["finance-data-viewer", "operations-data-viewer"],
    )

    assert result["decision"] == SOD_DENY
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == sod_test.id


def test_deny_takes_priority_over_review(app):
    """
    Verify that a deny decision overrides a review decision when both rules match.
    """
    current_review_role = ManagedRole(
        client_name="employee-portal",
        role_name="operations-data-viewer",
    )

    current_deny_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
    )

    requested_role = ManagedRole(
        client_name="employee-portal",
        role_name="security-data-viewer",
    )

    db.session.add_all([current_deny_role, current_review_role, requested_role])

    db.session.flush()

    first_role_id, second_role_id = sorted([current_deny_role.id, requested_role.id])

    reivew_rule = SoDRule(
        name="Operations and security require review",
        first_role_id=current_review_role.id,
        second_role_id=second_role_id,
        outcome=SOD_REQUIRES_REVIEW,
    )

    deny_rule = SoDRule(
        name="Finance and operations requires deny",
        first_role_id=first_role_id,
        second_role_id=second_role_id,
        outcome=SOD_DENY,
    )

    db.session.add_all([reivew_rule, deny_rule])
    db.session.commit()

    result = evaluate_role_assignment(
        target_client_name="employee-portal",
        current_role_names=["operations-data-viewer", "finance-data-viewer"],
        requested_role_name="security-data-viewer",
    )

    assert result["decision"] == SOD_DENY
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == deny_rule.id


def test_disabled_current_role_still_triggers_sod_deny(app):
    """
    Verify that a held role still triggers an enabled deny rule
    when its managed-role catalogue entry is disabled.
    """
    current_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=False,
    )

    requested_role = ManagedRole(
        client_name="employee-portal",
        role_name="security-data-viewer",
        enabled=True,
    )

    db.session.add_all([current_role, requested_role])
    db.session.flush()

    first_role_id, second_role_id = sorted(
        [
            current_role.id,
            requested_role.id,
        ]
    )

    deny_rule = SoDRule(
        name="Finance and security conflict",
        first_role_id=first_role_id,
        second_role_id=second_role_id,
        outcome=SOD_DENY,
        enabled=True,
    )

    db.session.add(deny_rule)
    db.session.commit()

    result = evaluate_role_assignment(
        target_client_name="employee-portal",
        requested_role_name="security-data-viewer",
        current_role_names=["finance-data-viewer"],
    )

    assert result["decision"] == SOD_DENY
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == deny_rule.id


def test_review_decision_survives_later_nonmatching_role(app, monkeypatch):
    """
    Verify that a review match is preserved when a later held role
    has no matching SoD rule.
    """
    review_role = ManagedRole(
        client_name="employee-portal",
        role_name="finance-data-viewer",
        enabled=True,
    )

    unrelated_role = ManagedRole(
        client_name="employee-portal",
        role_name="operations-data-viewer",
        enabled=True,
    )

    requested_role = ManagedRole(
        client_name="employee-portal",
        role_name="security-data-viewer",
        enabled=True,
    )

    db.session.add_all(
        [
            review_role,
            unrelated_role,
            requested_role,
        ]
    )
    db.session.flush()

    first_role_id, second_role_id = sorted([requested_role.id, review_role.id])

    requires_review = SoDRule(
        outcome=SOD_REQUIRES_REVIEW,
        first_role_id=first_role_id,
        second_role_id=second_role_id,
        name="My Rule",
        enabled=True,
    )

    db.session.add(requires_review)
    db.session.commit()

    requested_result = Mock()
    requested_result.scalar_one_or_none.return_value = requested_role

    current_result = Mock()
    current_result.scalars.return_value.all.return_value = [review_role, unrelated_role]

    review_result = Mock()
    review_result.scalar_one_or_none.return_value = requires_review

    no_match_result = Mock()
    no_match_result.scalar_one_or_none.return_value = None

    fake_execute = Mock(
        side_effect=[
            requested_result,
            current_result,
            review_result,
            no_match_result,
        ]
    )

    monkeypatch.setattr(db.session, "execute", fake_execute)

    result = evaluate_role_assignment(
        "employee-portal",
        "security-data-viewer",
        ["finance-data-viewer", "operations-data-viewer"],
    )

    assert result["decision"] == SOD_REQUIRES_REVIEW
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == requires_review.id

    fake_execute.call_count == 4
