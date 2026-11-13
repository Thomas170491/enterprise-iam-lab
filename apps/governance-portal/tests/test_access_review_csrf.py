from unittest.mock import Mock

import pytest

from auth.permissions import ACCESS_REVIEW_MANAGER, ACCESS_REVIEWER
from extensions import db
from tests.access_review_helpers import _CSRFFormParser, _login_user

import governance.routes as governance_routes
import services.access_review_service as access_review_service


@pytest.mark.parametrize("action", ["create", "populate", "open", "cancel"])
@pytest.mark.parametrize("token_state", ["missing", "invalid", "valid"])
def test_access_review_mutations_require_valid_csrf_token(
    client, monkeypatch, action, token_state
):
    """
    Verify that mutation routes reject missing or invalid CSRF tokens and accept valid ones.
    """
    monkeypatch.setitem(client.application.config, "WTF_CSRF_ENABLED", True)
    _login_user(client, [ACCESS_REVIEW_MANAGER])

    campaign = access_review_service.create_access_review(
        "CSRF campaign", "test-subject", "reviewer-123"
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
    campaign_id = campaign.id

    # Isolate CSRF enforcement from persistence and external Keycloak calls.
    fake_service = Mock(return_value=campaign)

    monkeypatch.setattr(
        governance_routes,
        f"{action}_access_review_with_audit",
        fake_service
    )

    if action == "create":
        form_url = "/access-reviews/new"
        post_url = form_url
        data = {
            "name": "CSRF campaign",
            "reviewer_user_id": "4e7b2a9c-1d3f-4c8e-b5a6-7f0e1d2c3b4a",
            "due_at": "",
        }
    else:
        form_url = f"/access-reviews/manage/{campaign_id}"
        post_url = f"{form_url}/{action}"
        data = {"user_id": "user-123"} if action == "populate" else {}

    form_response = client.get(form_url)
    assert form_response.status_code == 200

    # Extract the token from the submitted form, not the navigation logout form.
    parser = _CSRFFormParser(post_url)
    parser.feed(form_response.get_data(as_text=True))
    assert parser.csrf_token, f"Missing CSRF token in form for {post_url}"

    if token_state == "valid":
        data["csrf_token"] = parser.csrf_token
    elif token_state == "invalid":
        data["csrf_token"] = "invalid-test-token"

    response = client.post(post_url, data=data)

    if token_state == "valid":
        assert response.status_code == 303
        fake_service.assert_called_once()
    else:
        assert response.status_code == 400
        fake_service.assert_not_called()


@pytest.mark.parametrize("token_state", ["missing", "invalid", "valid"])
def test_access_review_decision_requires_valid_csrf_token(
    client, monkeypatch, token_state
):
    """
    Verify that the decision route rejects missing or invalid CSRF tokens and accepts a valid one.
    """
    monkeypatch.setitem(client.application.config, "WTF_CSRF_ENABLED", True)
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        "CSRF campaign", "manager-123", "test-subject"
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="user-123",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    access_review_service.open_access_review(campaign.id)
    db.session.commit()

    # Isolate CSRF enforcement from persistence.
    fake_service = Mock(return_value=item)

    monkeypatch.setattr(
        governance_routes,
        "record_access_review_decision_with_audit",
        fake_service,
    )

    form_url = f"/access-reviews/{campaign.id}"
    post_url = f"{form_url}/items/{item.id}/decision"
    data = {"decision": "retain"}

    form_response = client.get(form_url)
    assert form_response.status_code == 200

    # Extract the token from the decision form, not the navigation logout form.
    parser = _CSRFFormParser(post_url)
    parser.feed(form_response.get_data(as_text=True))
    assert parser.csrf_token, f"Missing CSRF token in form for {post_url}"

    if token_state == "valid":
        data["csrf_token"] = parser.csrf_token
    elif token_state == "invalid":
        data["csrf_token"] = "invalid-test-token"

    response = client.post(post_url, data=data)

    if token_state == "valid":
        assert response.status_code == 303
        fake_service.assert_called_once()
    else:
        assert response.status_code == 400
        fake_service.assert_not_called()
