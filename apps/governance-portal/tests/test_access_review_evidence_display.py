import pytest

from auth.permissions import ACCESS_REVIEW_MANAGER, ACCESS_REVIEWER
from extensions import db
from tests.access_review_helpers import _login_user

import services.access_review_service as access_review_service


def test_access_review_detail_shows_grant_sources(client):
    """
    Verify that the access review detail page displays grant sources for each role assignment.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name = "Grant source campaign",
        created_by_user_id = "manager-123",
        reviewer_user_id = "test-subject"
    )

    assignment_source="direct"
    grant_sources=[
        {
            "type": "user",
            "user_id": "user-123",
            "assigned_role_id": "finance-staff-id",
            "composite_path": ["finance-staff-id", "finance-role-id"],
        }
    ]

    assert isinstance(grant_sources, list)
    assert grant_sources[0]["assigned_role_id"] == "finance-staff-id"

    access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
        assignment_source= assignment_source,
        grant_sources= grant_sources,
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Grant Sources" in html
    assert "user-123" in html
    assert "finance-staff-id" in html


def test_access_review_detail_shows_inherited_group_grant(client):
    """
    Verify that a reviewer sees the granting group, membership group, and composite path.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name = "Inherited group campaign",
        created_by_user_id = "manager-123",
        reviewer_user_id = "test-subject"
    )

    assignment_source="inherited"
    grant_sources=[
        {
            "type": "group",
            "group_id": "finance-staff-group-id",
            "membership_group_id": "finance-team-id",
            "assigned_role_id": "finance-staff-id",
            "composite_path": ["finance-staff-id", "finance-role-id"],
        }
    ]

    assert isinstance(grant_sources, list)
    assert grant_sources[0]["assigned_role_id"] == "finance-staff-id"

    access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
        assignment_source= assignment_source,
        grant_sources= grant_sources,
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Grant Sources" in html
    assert "finance-staff-group-id" in html
    assert "finance-staff-id" in html
    assert "finance-team-id" in html


def test_access_review_detail_marks_missing_grant_evidence(client):
    """
    Verify that a review item without recorded grant evidence is labeled unavailable.
    """

    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name = "Missing grant evidence campaign",
        created_by_user_id = "manager-123",
        reviewer_user_id = "test-subject"
    )

    assignment_source="direct"
    grant_sources=[]

    access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
        assignment_source= assignment_source,
        grant_sources= grant_sources,
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Grant Sources" in html
    assert "Source evidence unavailable" in html


@pytest.mark.parametrize("grant_count", [0, 1, 2])
def test_access_review_detail_has_one_decision_header_per_table(client, grant_count):
    """
    Verify that the Decision column header appears once in the table head for any number of grants.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        "Header campaign",
        "manager-123",
        "test-subject",
    )
    access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
        assignment_source="direct",
        grant_sources=[
            {
                "type": "user",
                "user_id": "user-123",
                "assigned_role_id": f"assigned-role-{index}",
                "composite_path": [],
            }
            for index in range(grant_count)
        ],
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert html.count("<th ") == 6
    assert html.count('<th scope="col">Decision</th>') == 1

    table_head = html[html.index("<thead>"):html.index("</thead>")]
    table_body = html[html.index("<tbody>"):html.index("</tbody>")]

    assert '<th scope="col">Decision</th>' in table_head
    assert "<th " not in table_body
    assert table_body.count("<td") == table_head.count("<th ")


def test_manager_access_review_detail_shows_group_evidence_without_decision_controls(client):
    """
    Verify that a manager sees group grant evidence but cannot submit a reviewer decision.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="test-subject",
        reviewer_user_id="test-review-subject",
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="test-subject",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
        assignment_source="inherited",
        grant_sources=[
            {
                "type": "group",
                "group_id": "finance-staff-group-id",
                "membership_group_id": "finance-team-id",
                "assigned_role_id": "finance-staff-id",
                "composite_path": ["finance-staff-id", "finance-role-id"],
            }
        ],
    )
    access_review_service.open_access_review(campaign.id)
    db.session.commit()

    response = client.get(f"/access-reviews/manage/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "finance-staff-group-id" in html
    assert "finance-team-id" in html
    assert f"/access-reviews/{campaign.id}/items/{item.id}/decision" not in html
    assert "finance-data-viewer" in html
