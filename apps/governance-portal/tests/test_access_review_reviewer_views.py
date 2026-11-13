from urllib.parse import urlsplit

import pytest
from flask import url_for

from auth.permissions import ACCESS_REVIEW_MANAGER, ACCESS_REVIEWER
from extensions import db
from tests.access_review_helpers import _login_user

import services.access_review_service as access_review_service


def test_access_reviews_requires_authentication(client):
    """
    Verify that unauthenticated visitors are redirected to login.
    """
    response = client.get("/access-reviews")

    assert response.status_code == 302

    with client.application.test_request_context():
        login_url = url_for("auth.login")

    assert urlsplit(response.headers["Location"]).path == login_url


@pytest.mark.parametrize(
    "client_roles",
    [[], [ACCESS_REVIEW_MANAGER]],
)
def test_access_reviews_rejects_user_without_reviewer_role(
    client,
    client_roles,
):
    """
    Verify that reviewer access requires the reviewer role, including for managers.
    """
    _login_user(client, client_roles)

    response = client.get("/access-reviews")

    assert response.status_code == 403


def test_access_reviews_shows_only_assigned_campaigns(client):
    """
    Verify that the page displays only campaigns assigned to the authenticated reviewer.
    """
    _login_user(client, [ACCESS_REVIEWER])

    review = access_review_service.create_access_review(
        name="My campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    access_review_service.create_access_review(
        name="Other campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="other-reviewer",
    )
    db.session.commit()

    response = client.get("/access-reviews")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "My campaign" in html
    assert "Other campaign" not in html
    assert "Draft" in html
    assert "No due date" in html
    assert f'href="/access-reviews/{review.id}"' in html


def test_access_reviews_ignores_supplied_reviewer_id(client):
    """
    Verify that a query parameter cannot expose another reviewer's campaigns.
    """
    _login_user(client, [ACCESS_REVIEWER])

    access_review_service.create_access_review(
        name="My campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    access_review_service.create_access_review(
        name="Private campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="other-reviewer",
    )
    db.session.commit()

    response = client.get(
        "/access-reviews",
        query_string={"reviewer_user_id": "other-reviewer"},
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "My campaign" in html
    assert "Private campaign" not in html


def test_access_reviews_displays_empty_message(client):
    """
    Verify that reviewers without assigned campaigns see the empty-state message.
    """
    _login_user(client, [ACCESS_REVIEWER])

    access_review_service.create_access_review(
        name="Other campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="other-reviewer",
    )
    db.session.commit()

    response = client.get("/access-reviews")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "No access review campaigns are assigned to you." in html
    assert "Other campaign" not in html


def test_access_review_detail_requires_authentication(client):
    """
    Verify that unauthenticated visitors cannot access campaign details.
    """
    response = client.get("/access-reviews/1")

    assert response.status_code == 302

    with client.application.test_request_context():
        login_url = url_for("auth.login")

    assert urlsplit(response.headers["Location"]).path == login_url


@pytest.mark.parametrize(
    "client_roles",
    [[], [ACCESS_REVIEW_MANAGER]],
)
def test_access_review_detail_requires_reviewer_role(
    app,
    client,
    client_roles,
):
    """
    Verify that campaign assignment alone does not grant reviewer access.
    """
    _login_user(client, client_roles)

    review = access_review_service.create_access_review(
        name="Assigned campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{review.id}")

    assert response.status_code == 403
    assert "Assigned campaign" not in response.get_data(as_text=True)


def test_access_review_detail_displays_assigned_campaign(client):
    """
    Verify that the assigned reviewer can view a campaign and its captured access.
    """
    _login_user(client, [ACCESS_REVIEWER])

    review = access_review_service.create_access_review(
        name="Finance access review",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    access_review_service.add_access_review_item(
        review_id=review.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )

    other_review = access_review_service.create_access_review(
        name="Separate campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    access_review_service.add_access_review_item(
        review_id=other_review.id,
        user_id="user-456",
        username="bob",
        client_name="employee-portal",
        role_id="security-role-id",
        role_name="security-data-viewer",
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{review.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Finance access review" in html
    assert "alice" in html
    assert "employee-portal" in html
    assert "finance-data-viewer" in html
    assert "draft" in html
    assert "No due date" in html
    assert 'href="/access-reviews"' in html

    assert "Separate campaign" not in html
    assert "<td>bob</td>" not in html
    assert "security-data-viewer" not in html


@pytest.mark.parametrize(
    "query_string",
    [
        {},
        {"reviewer_user_id": "other-reviewer"},
    ],
)
def test_access_review_detail_rejects_other_reviewer(
    client,
    query_string,
):
    """
    Verify that another reviewer's campaign stays inaccessible despite supplied parameters.
    """
    _login_user(client, [ACCESS_REVIEWER])

    review = access_review_service.create_access_review(
        name="Private campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="other-reviewer",
    )
    access_review_service.add_access_review_item(
        review_id=review.id,
        user_id="private-user-123",
        username="private-employee",
        client_name="employee-portal",
        role_id="security-role-id",
        role_name="security-data-viewer",
    )
    db.session.commit()

    response = client.get(
        f"/access-reviews/{review.id}",
        query_string=query_string,
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "Private campaign" not in html
    assert "private-employee" not in html
    assert "security-data-viewer" not in html


def test_access_review_detail_rejects_missing_campaign(client):
    """
    Verify that a nonexistent campaign returns HTTP 404 for an authenticated reviewer.
    """
    _login_user(client, [ACCESS_REVIEWER])

    response = client.get("/access-reviews/999999")

    assert response.status_code == 404


def test_access_review_detail_displays_empty_items_message(client):
    """
    Verify that a campaign without snapshots displays an explanatory message.
    """
    _login_user(client, [ACCESS_REVIEWER])

    review = access_review_service.create_access_review(
        name="Empty draft campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{review.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Empty draft campaign" in html
    assert "No access items have been captured for this campaign." in html


def test_reviewer_campaign_detail_hides_open_form(client):
    """
    Verify that the reviewer detail page does not display campaign opening controls.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Reviewer populated campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
    )
    access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/open"' not in html


@pytest.mark.parametrize("status", ["draft", "open"])
def test_reviewer_campaign_detail_hides_cancel_form(client, status):
    """
    Verify that reviewer pages hide cancellation controls for draft and open campaigns.
    """
    _login_user(client, [ACCESS_REVIEWER])
    campaign = access_review_service.create_access_review(
        "Assigned campaign", "manager-123", "test-subject"
    )
    campaign.status = status
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/cancel"' not in html
    assert "Cancel campaign" not in html
