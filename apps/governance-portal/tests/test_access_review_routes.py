from urllib.parse import urlsplit

import pytest
from flask import url_for
from models import AccessReview
from auth.permissions import ACCESS_REVIEW_MANAGER, ACCESS_REVIEWER
from extensions import db
from services.access_review_service import (
    add_access_review_item,
    create_access_review,
)


def _login_user(client, client_roles):
    """
    Authenticate a test user with the specified client roles.
    """
    with client.session_transaction() as session:
        session["user"] = {
            "sub": "test-subject",
            "username": "test-user",
            "name": "Test User",
            "email": "test@example.test",
            "client_roles": client_roles,
            "realm_roles": [],
        }
        session["_user_id"] = "test-subject"
        session["_fresh"] = True


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

    review = create_access_review(
        name="My campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    create_access_review(
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


def test_access_reviews_ignores_supplied_reviewer_id( client):
    """
    Verify that a query parameter cannot expose another reviewer's campaigns.
    """
    _login_user(client, [ACCESS_REVIEWER])

    create_access_review(
        name="My campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    create_access_review(
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

    create_access_review(
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

    review = create_access_review(
        name="Assigned campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{review.id}")

    assert response.status_code == 403
    assert "Assigned campaign" not in response.get_data(as_text=True)


def test_access_review_detail_displays_assigned_campaign( client):
    """
    Verify that the assigned reviewer can view a campaign and its captured access.
    """
    _login_user(client, [ACCESS_REVIEWER])

    review = create_access_review(
        name="Finance access review",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    add_access_review_item(
        review_id=review.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )

    other_review = create_access_review(
        name="Separate campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="test-subject",
    )
    add_access_review_item(
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
    assert "Draft" in html
    assert "No due date" in html
    assert 'href="/access-reviews"' in html

    assert "Separate campaign" not in html
    assert "bob" not in html
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

    review = create_access_review(
        name="Private campaign",
        created_by_user_id="creator-123",
        reviewer_user_id="other-reviewer",
    )
    add_access_review_item(
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


def test_access_review_detail_displays_empty_items_message( client):
    """
    Verify that a campaign without snapshots displays an explanatory message.
    """
    _login_user(client, [ACCESS_REVIEWER])

    review = create_access_review(
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
    
def test_access_review_creation_form_allows_manager( client):
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

def test_access_review_manager_can_create_campaign(client):
    """
    Verify that an access review manager can create a draft campaign.
    """
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    response = client.post(
        "/access-reviews/new",
        data={
            "name": "September access review",
            "reviewer_user_id": "reviewer-123",
            "due_at": "",
        },
    )

    assert response.status_code == 303

    review = db.session.execute(
        db.select(AccessReview).where(
            AccessReview.name == "September access review"
        )
    ).scalar_one()

    assert review.created_by_user_id == "test-subject"
    assert review.reviewer_user_id == "reviewer-123"
    assert review.status == "draft"
    assert review.due_at is None

    assert response.headers["Location"].endswith(
        f"/access-reviews/manage/{review.id}"
    )
    

def test_manager_can_view_own_campaign(client):
    """
    Verify that an access review manager can view a campaign they created.
    """
  
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    
    campaign = create_access_review("test-campaign","test-subject","reviewer-123")
    campaign_id = campaign.id
    
    response= client.get(f"/access-reviews/manage/{campaign_id}")
    html = response.get_data(as_text=True)
    
    assert response.status_code == 200
    assert "test-campaign" in html

def test_manager_cannot_view_other_manager_campaign(client) :
    """
    Verify that an access review manager cannot view a campaign created by another manager.
    """
        
    _login_user(client, [ACCESS_REVIEW_MANAGER])
    
    campaign = create_access_review("test-campaign", "other-manager", "reviewer-123")
    campaign_id = campaign.id
    
    response= client.get(f"/access-reviews/manage/{campaign_id}")
    html = response.get_data(as_text=True)
    
    assert response.status_code == 404
    assert "test-campaign" not in html 
    
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

    create_access_review(
        "My campaign",
        "test-subject",
        "reviewer-123",
    )

    create_access_review(
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

    create_access_review(
        "Other manager campaign",
        "other-manager",
        "reviewer-456",
    )

    db.session.commit()

    response = client.get("/access-reviews/manage")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "No access review campaigns have been created by you." in html