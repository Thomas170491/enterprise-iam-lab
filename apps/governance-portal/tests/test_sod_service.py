from  services.sod_service import SOD_DENY,SOD_ALLOW,SOD_REQUIRES_REVIEW, evaluate_role_assignment
from models import ManagedRole, SoDRule
from extensions import db

def test_unmanaged_request_role_is_denied(app):
    result = evaluate_role_assignment("employee-portal", "unknown-role", [])
    
    assert result["decision"] == SOD_DENY
    assert result["reason"] == "role_not_managed"
    assert result["rule_id"] is None

    
def test_managed_role_without_conflict_is_allowed(app):
    test_managed_role = ManagedRole(
        client_name = "employee-portal",
        role_name = "finance-data-viewer"
    )
    
    db.session.add(test_managed_role)
    db.session.commit()
    
    result = evaluate_role_assignment("employee-portal","finance-data-viewer", [])
    
    assert result["decision"] == SOD_ALLOW
    assert result["reason"] == "no_sod_conflict"
    assert result["rule_id"] is None
    from  services.sod_service import SOD_DENY,SOD_ALLOW, evaluate_role_assignment
from models.managed_role import ManagedRole
from extensions import db

def test_unmanaged_request_role_is_denied(app):
    result = evaluate_role_assignment("employee-portal", "unknown-role", [])
    
    assert result["decision"] == SOD_DENY
    assert result["reason"] == "role_not_managed"
    assert result["rule_id"] is None

    
def test_managed_role_without_conflict_is_allowed(app):
    test_managed_role = ManagedRole(
        client_name = "employee-portal",
        role_name = "finance-data-viewer"
    )
    
    db.session.add(test_managed_role)
    db.session.commit()
    
    result = evaluate_role_assignment("employee-portal","finance-data-viewer", [])
    
    assert result["decision"] == SOD_ALLOW
    assert result["reason"] == "no_sod_conflict"
    assert result["rule_id"] is None
    
    
    
def test_matching_deny_rule_blocks_assignment(app):
    
    test_managed_role_deny_1 = ManagedRole(
        client_name = "employee-portal",
        role_name = "finance-data-viewer"
    )
    
    test_managed_role_deny_2 = ManagedRole(
        client_name = "employee-portal",
        role_name = "security-data-viewer"
    )
    
    db.session.add_all([test_managed_role_deny_1, test_managed_role_deny_2])
    db.session.flush()
    
    first_role_id, second_role_id = sorted([
        test_managed_role_deny_1.id,
        test_managed_role_deny_2.id,
    ])
    
    test_sod = SoDRule(
        first_role_id = first_role_id,
        second_role_id = second_role_id,
        outcome = SOD_DENY,
        name = "test",

    )
    
    db.session.add(test_sod)
    
    db.session.commit()
    
    result = evaluate_role_assignment("employee-portal", "security-data-viewer" , ["finance-data-viewer"] )
    
    assert result["decision"] == SOD_DENY
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == test_sod.id
    
    
def test_matching_review_rule_requires_review(app):
    """
    Verify that a review rule returns a requires-review decision.
    """
    current_role = ManagedRole(
        client_name = "employee-portal",
        role_name = "finance-data-viewer"
    )
    
    requested_role = ManagedRole(
        client_name = "employee-portal",
        role_name = "operations-data-viewer"
    )
    
    db.session.add_all([current_role, requested_role])
    db.session.flush()
    
    first_role_id, second_role_id = sorted([
        current_role.id,
        requested_role.id,
    ])
    
    sod_test = SoDRule(
        name = "Test Rule",
        first_role_id = first_role_id,
        second_role_id = second_role_id,
        outcome = SOD_REQUIRES_REVIEW
    )
    
 

    
    db.session.add(sod_test)
    db.session.commit()
    
    result = evaluate_role_assignment("employee-portal", "operations-data-viewer", ["finance-data-viewer"])
    
    assert result["decision"] == SOD_REQUIRES_REVIEW
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == sod_test.id
    
def test_disabled_sod_rule_is_ignored(app):
    
    """
    Verify that a disabled SoD rule does not affect role assignment.
    """
    
    current_role = ManagedRole(
        client_name = "employee-portal",
        role_name = "finance-data-viewer"
    )
    
    requested_role = ManagedRole(
        client_name = "employee-portal",
        role_name = "operations-data-viewer"
    )
    
    db.session.add_all([current_role, requested_role])
    db.session.flush()
    
    first_role_id, second_role_id = sorted([
        current_role.id,
        requested_role.id,
    ])
    

    
    sod_test = SoDRule(
        name = "Test Rule",
        first_role_id = first_role_id,
        second_role_id = second_role_id,
        outcome = SOD_DENY,
        enabled = False,
    )
    
    db.session.add(sod_test)
    db.session.commit()
    
    result = evaluate_role_assignment("employee-portal", "operations-data-viewer", ["finance-data-viewer"])
    
    assert result["decision"] == SOD_ALLOW
    assert result["reason"] == "no_sod_conflict"
    assert result["rule_id"] is None
    
 
def test_disabled_requested_role_is_denied(app):
    
    """
    Verify that a disabled managed role is denied by default.
    """
    requested_role = ManagedRole(
        client_name = "employee-portal",
        role_name = "finance-data-viewer",
        enabled = False
        
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
        client_name = "employee-portal",
        role_name = "operations-data-viewer"
    )
    
    conflicting_current_role  = ManagedRole(
        client_name = "employee-portal",
        role_name = "finance-data-viewer"
    )
    
    requested_role = ManagedRole(
        client_name = "employee-portal",
        role_name = "security-data-viewer"
    )
    
    db.session.add_all([current_role, conflicting_current_role, requested_role])
    db.session.flush()
    
    first_role_id, second_role_id = sorted([
        conflicting_current_role.id,
        requested_role.id,
    ])
    
    sod_test = SoDRule(
        name = "Test Rule",
        first_role_id = first_role_id,
        second_role_id = second_role_id,
        outcome = SOD_DENY,
    )
    
    
    db.session.add(sod_test)
    db.session.commit()
    
    result = evaluate_role_assignment("employee-portal","security-data-viewer", ["finance-data-viewer", "operations-data-viewer"])
    
        
    assert result["decision"] == SOD_DENY
    assert result["reason"] == "sod_rule_matched"
    assert result["rule_id"] == sod_test.id
    
