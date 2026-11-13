from urllib.parse import urlsplit

import pytest
from flask import url_for

from auth.permissions import ACCESS_REVIEW_MANAGER, ACCESS_REVIEWER
from extensions import db
from tests.access_review_helpers import _login_user

import services.access_review_service as access_review_service


def test_access_review_creation_form_allows_manager(client):
    """
    Verify that an access review manager can view the campaign creation form.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    response = client.get("/access-reviews/new")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Create access review" in html
    assert 'name="reviewer_user_id"' in html
    assert 'name="csrf_token"' in html


def test_access_review_creation_form_requires_authentication(client):
    """
    Verify that unauthenticated users are redirected to login.
    """
    response = client.get("/access-reviews/new")

    assert response.status_code == 302

    with client.application.test_request_context():
        login_url = url_for("auth.login")

    assert urlsplit(response.headers["Location"]).path == login_url


@pytest.mark.parametrize(
    "client_roles",
    [
        [],
        [ACCESS_REVIEWER],
    ],
)
def test_access_review_creation_form_requires_manager_role(
    client,
    client_roles,
):
    """
    Verify that only access review managers can open the creation form.
    """
    _login_user(client, client_roles)

    response = client.get("/access-reviews/new")

    assert response.status_code == 403


def test_manager_can_view_own_campaign(client):
    """
    Verify that an access review manager can view a campaign they created.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "test-campaign",
        "test-subject",
        "reviewer-123",
    )
    campaign_id = campaign.id

    response = client.get(f"/access-reviews/manage/{campaign_id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "test-campaign" in html


def test_manager_draft_campaign_displays_capture_form(client):
    """
    Verify that a manager's draft campaign displays the capture form with CSRF protection.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Draft campaign capture",
        "test-subject",
        "reviewer-123",
    )
    db.session.commit()

    response = client.get(f"/access-reviews/manage/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/populate"' in html
    assert 'name="user_id"' in html
    assert 'name="csrf_token"' in html
    assert "Capture access" in html


def test_manager_nonempty_draft_displays_open_form(client):
    """
    Verify that a manager's nonempty draft campaign displays the opening form.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Nonempty draft campaign",
        "test-subject",
        "reviewer-123",
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

    response = client.get(f"/access-reviews/manage/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/open"' in html
    assert "Open campaign" in html


def test_manager_empty_draft_hides_open_form(client):
    """
    Verify that an empty draft campaign does not display the opening form.
    """

    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Empty draft campaign",
        "test-subject",
        "reviewer-123",
    )

    db.session.commit()

    response = client.get(f"/access-reviews/manage/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/open"' not in html


@pytest.mark.parametrize(
    "status",
    ["open", "completed", "cancelled"],
)
def test_manager_non_draft_campaign_hides_capture_form(client, status):
    """
    Verify that open, completed, and cancelled campaigns do not display the capture form.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Draft campaign capture",
        "test-subject",
        "reviewer-123",
    )
    campaign.status = status
    db.session.commit()

    response = client.get(f"/access-reviews/manage/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/populate"' not in html
    assert 'name="user_id"' not in html
    assert "Capture access" not in html


def test_manager_cannot_view_other_manager_campaign(client):
    """
    Verify that an access review manager cannot view a campaign created by another manager.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "test-campaign",
        "other-manager",
        "reviewer-123",
    )
    campaign_id = campaign.id

    response = client.get(f"/access-reviews/manage/{campaign_id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 404
    assert "test-campaign" not in html


@pytest.mark.parametrize(
    "status",
    ["open", "completed", "cancelled"],
)
def test_manager_non_draft_campaign_hides_open_form(client, status):
    """
    Verify that non-draft campaigns do not display the opening form.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "Non-draft campaign",
        "test-subject",
        "reviewer-123",
    )
    access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    campaign.status = status
    db.session.commit()

    response = client.get(f"/access-reviews/manage/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/open"' not in html


def test_missing_campaign_returns_404(client):
    """
    Verify that requesting a nonexistent managed access review campaign returns HTTP 404.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    fake_id = 99999

    response = client.get(f"/access-reviews/manage/{fake_id}")
    assert response.status_code == 404


def test_reviewer_cannot_view_manager_route(client):
    """
    Verify that an access reviewer without the manager role cannot access the manager campaign detail route.
    """
    _login_user(client, [ACCESS_REVIEWER])

    fake_id = 99999

    response = client.get(f"/access-reviews/manage/{fake_id}")

    assert response.status_code == 403


def test_manage_access_reviews_requires_authentication(client):
    """
    Verify that unauthenticated users are redirected to login.
    """
    response = client.get("/access-reviews/manage")

    assert response.status_code == 302

    with client.application.test_request_context():
        login_url = url_for("auth.login")

    assert urlsplit(response.headers["Location"]).path == login_url


def test_manage_access_reviews_requires_manager_role(client):
    """
    Verify that reviewers without the manager role cannot access the manager campaign list.
    """
    _login_user(client, [ACCESS_REVIEWER])

    response = client.get("/access-reviews/manage")

    assert response.status_code == 403


def test_manage_access_reviews_shows_only_owned_campaigns(client):
    """
    Verify that a manager sees only campaigns they created.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    access_review_service.create_access_review(
        "My campaign",
        "test-subject",
        "reviewer-123",
    )

    access_review_service.create_access_review(
        "Other manager campaign",
        "other-manager",
        "reviewer-456",
    )

    db.session.commit()

    response = client.get("/access-reviews/manage")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "My campaign" in html
    assert "Other manager campaign" not in html


def test_manage_access_reviews_displays_empty_message(client):
    """
    Verify that a manager with no created campaigns sees the empty-state message.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    access_review_service.create_access_review(
        "Other manager campaign",
        "other-manager",
        "reviewer-456",
    )

    db.session.commit()

    response = client.get("/access-reviews/manage")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "No access review campaigns have been created by you." in html


@pytest.mark.parametrize("status", ["draft", "open"])
def test_manager_can_see_cancel_form_for_cancellable_campaign(client, status):
    """
    Verify that draft and open campaigns display the cancellation form to their manager.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    campaign = access_review_service.create_access_review(
        "Cancellable campaign", "test-subject", "reviewer-123"
    )
    campaign.status = status
    db.session.commit()

    response = client.get(f"/access-reviews/manage/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/cancel"' in html
    assert "Cancel campaign" in html


@pytest.mark.parametrize("status", ["completed", "cancelled"])
def test_manager_terminal_campaign_hides_cancel_form(client, status):
    """
    Verify that completed and cancelled campaigns hide the cancellation form.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    campaign = access_review_service.create_access_review(
        "Terminal campaign", "test-subject", "reviewer-123"
    )
    campaign.status = status
    db.session.commit()

    response = client.get(f"/access-reviews/manage/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'action="/access-reviews/manage/{campaign.id}/cancel"' not in html
    assert "Cancel campaign" not in html
