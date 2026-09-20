from extensions import db
from models import ManagedRole, SoDRule


def test_sod_rule_links_two_managed_roles(app):
    """
    Test that a SoDRule can be created linking two ManagedRole instances
    """

    # Create two ManagedRole instances
    role1 = ManagedRole(client_name="iam-admin-portal", role_name="role-manager")
    role2 = ManagedRole(client_name="iam-admin-portal", role_name="access-reviewer")

    db.session.add_all([role1, role2])
    db.session.flush()

    # Create a SoDRule linking the two roles
    sod_rule = SoDRule(
        name="Prevent self-review",
        first_role_id=role1.id,
        second_role_id=role2.id,
        outcome="deny",
    )

    db.session.add(sod_rule)
    db.session.commit()

    # Fetch the SoDRule from the database and verify the links
    fetched_rule = SoDRule.query.filter_by(name="Prevent self-review").first()
    assert fetched_rule is not None
    assert fetched_rule.outcome == "deny"
    assert {
        fetched_rule.first_role.role_name,
        fetched_rule.second_role.role_name,
    } == {
        "role-manager",
        "access-reviewer",
    }
    assert fetched_rule.first_role.id == role1.id
    assert fetched_rule.second_role.id == role2.id
