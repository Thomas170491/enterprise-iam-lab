from models import AccessReviewItem
from services.remediation_service import assess_live_access

USER_ID = "5c6d7e8f-1a2b-4c3d-8e9f-0a1b2c3d4e5f"
ROLE_ID = "finance-role-id"
PARENT_ROLE_ID = "finance-bundle-role-id"
GROUP_ID = "finance-group-id"

USER_GRANT = {
    "type": "user",
    "user_id": USER_ID,
    "assigned_role_id": ROLE_ID,
    "composite_path": [],
}
GROUP_GRANT = {
    "type": "group",
    "group_id": GROUP_ID,
    "membership_group_id": GROUP_ID,
    "assigned_role_id": ROLE_ID,
    "composite_path": [],
}


def _item(grant_sources):
    """
    Build an unsaved captured item for the finance role with the given evidence.
    """
    return AccessReviewItem(
        user_id=USER_ID,
        username="alice",
        client_name="employee-portal",
        role_id=ROLE_ID,
        role_name="finance-data-viewer",
        assignment_source="direct",
        grant_sources=grant_sources,
    )


def _live(grant_sources, assignment_source="direct"):
    """
    Build the resolver's live answer for the finance role with the given evidence.
    """
    return [
        {
            "role_id": ROLE_ID,
            "role_name": "finance-data-viewer",
            "assignment_source": assignment_source,
            "grant_sources": grant_sources,
        }
    ]


def test_assess_live_access_reports_no_drift_when_sources_match():
    """
    Verify that unchanged live evidence is no drift and the direct grant is removable.
    """
    result = assess_live_access(_item([USER_GRANT]), _live([USER_GRANT]))

    assert result == {
        "drift": "none",
        "direct_grant_present": True,
        "other_grants_present": False,
    }


def test_assess_live_access_reports_role_removed_when_role_is_no_longer_effective():
    """
    Verify that a role missing from live access is reported as already removed.
    """
    result = assess_live_access(_item([USER_GRANT]), [])

    assert result == {
        "drift": "role_removed",
        "direct_grant_present": False,
        "other_grants_present": False,
    }


def test_assess_live_access_reports_newly_inherited_role():
    """
    Verify that a role now also granted by a group is drift with a grant that direct removal leaves.
    """
    result = assess_live_access(_item([USER_GRANT]), _live([USER_GRANT, GROUP_GRANT], "both"))

    assert result == {
        "drift": "sources_changed",
        "direct_grant_present": True,
        "other_grants_present": True,
    }


def test_assess_live_access_reports_source_changed_to_group_only():
    """
    Verify that a role now granted only by a group is drift with no directly removable grant.
    """
    result = assess_live_access(_item([USER_GRANT]), _live([GROUP_GRANT], "inherited"))

    assert result == {
        "drift": "sources_changed",
        "direct_grant_present": False,
        "other_grants_present": True,
    }


def test_assess_live_access_ignores_grant_order():
    """
    Verify that the same grants in a different order are not drift.
    """
    result = assess_live_access(
        _item([USER_GRANT, GROUP_GRANT]), _live([GROUP_GRANT, USER_GRANT], "both")
    )

    assert result == {
        "drift": "none",
        "direct_grant_present": True,
        "other_grants_present": True,
    }


def test_assess_live_access_treats_composite_only_grant_as_not_directly_removable():
    """
    Verify that a role reached only through a directly held composite is not directly removable.
    """
    composite_grant = {
        "type": "user",
        "user_id": USER_ID,
        "assigned_role_id": PARENT_ROLE_ID,
        "composite_path": [PARENT_ROLE_ID, ROLE_ID],
    }

    result = assess_live_access(_item([USER_GRANT]), _live([composite_grant], "direct"))

    assert result == {
        "drift": "sources_changed",
        "direct_grant_present": False,
        "other_grants_present": True,
    }


def test_assess_live_access_ignores_other_live_roles():
    """
    Verify that live roles other than the item's own role do not affect the assessment.
    """
    other_role = {
        "role_id": "hr-role-id",
        "role_name": "hr-data-viewer",
        "assignment_source": "direct",
        "grant_sources": [{**USER_GRANT, "assigned_role_id": "hr-role-id"}],
    }

    result = assess_live_access(_item([USER_GRANT]), [other_role] + _live([USER_GRANT]))

    assert result == {
        "drift": "none",
        "direct_grant_present": True,
        "other_grants_present": False,
    }


def test_assess_live_access_keeps_direct_grant_alongside_user_composite_grant():
    """
    Verify that a direct grant plus a user composite grant for the role is removable and leaves another grant.
    """
    composite_grant = {
        "type": "user",
        "user_id": USER_ID,
        "assigned_role_id": PARENT_ROLE_ID,
        "composite_path": [PARENT_ROLE_ID, ROLE_ID],
    }

    result = assess_live_access(
        _item([USER_GRANT, composite_grant]),
        _live([USER_GRANT, composite_grant], "direct"),
    )

    assert result == {
        "drift": "none",
        "direct_grant_present": True,
        "other_grants_present": True,
    }


def test_assess_live_access_reports_legacy_item_without_evidence_as_sources_changed():
    """
    Verify that a legacy item captured with no grant evidence always shows sources_changed.
    """
    result = assess_live_access(_item([]), _live([USER_GRANT]))

    assert result == {
        "drift": "sources_changed",
        "direct_grant_present": True,
        "other_grants_present": False,
    }


def test_assess_live_access_reports_unchanged_inherited_only_access():
    """
    Verify that unchanged group-only access is no drift and has no directly removable grant.
    """
    result = assess_live_access(_item([GROUP_GRANT]), _live([GROUP_GRANT], "inherited"))

    assert result == {
        "drift": "none",
        "direct_grant_present": False,
        "other_grants_present": True,
    }
