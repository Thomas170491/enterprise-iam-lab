from auth.permissions import ACCESS_REVIEWER
from extensions import db
from tests.access_review_helpers import _login_user

import services.access_review_service as access_review_service


def test_access_review_detail_shows_decision_controls_for_pending_item(client):
    """
    Verify that an assigned reviewer sees retain and revoke controls for an open item.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f"/access-reviews/{campaign.id}/items/{item.id}/decision" in html
    assert 'name="decision"' in html
    assert 'value="retain"' in html
    assert 'value="revoke"' in html
    assert 'name="csrf_token"' in html
    assert 'method="POST"' in html


def test_access_review_detail_offers_comment_box_for_pending_item(client):
    """
    Verify that the decision form for an open item offers an optional comment limited to 1000 characters.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
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
    access_review_service.open_access_review(campaign.id)
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<textarea" in html
    assert 'name="comment"' in html
    assert 'maxlength="1000"' in html


def test_access_review_detail_shows_service_recorded_decision_without_controls(client):
    """
    Verify that a decided item shows its decision without retain or revoke controls.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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
    access_review_service.record_access_review_decision(
        review_id=campaign.id,
        item_id=item.id,
        decision="retain",
        reviewer_user_id="test-subject",
    )
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Retain" in html
    assert f"/access-reviews/{campaign.id}/items/{item.id}/decision" not in html


def test_access_review_detail_shows_saved_decision_without_controls(client):
    """
    Verify that a decided item shows its decision without retain or revoke controls.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
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

    response = client.post(
        f"/access-reviews/{campaign.id}/items/{item.id}/decision",
        data={"decision": "retain"},
    )

    assert response.status_code == 303

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Retain" in html
    assert f"/access-reviews/{campaign.id}/items/{item.id}/decision" not in html


def test_access_review_detail_hides_decision_controls_for_own_item(client):
    """
    Verify that a reviewer cannot see decision controls for their own access.
    """
    _login_user(client, [ACCESS_REVIEWER])

    campaign = access_review_service.create_access_review(
        name="Decision campaign",
        created_by_user_id="manager-123",
        reviewer_user_id="test-subject",
    )
    item = access_review_service.add_access_review_item(
        review_id=campaign.id,
        user_id="test-subject",
        username="alice",
        client_name="employee-portal",
        role_id="finance-role-id",
        role_name="finance-data-viewer",
    )
    access_review_service.open_access_review(campaign.id)
    db.session.commit()

    response = client.get(f"/access-reviews/{campaign.id}")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f"/access-reviews/{campaign.id}/items/{item.id}/decision" not in html
    assert "finance-data-viewer" in html
