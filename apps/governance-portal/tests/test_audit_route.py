from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import governance.routes as governance_routes

from auth.permissions import AUDIT_LOG_VIEWER

def _login_user(
    client,
    client_roles,
):
    with client.session_transaction() as sess:

        sess["user"] = {
            "sub": "test-subject",
            "username": "test-user",
            "name": "Test User",
            "email": "test@example.test",
            "client_roles": client_roles,
            "realm_roles": [],
        }

        sess["_user_id"] = "test-subject"
        sess["_fresh"] = True

def test_audit_log_route_access(
    client,
    monkeypatch,
):
    _login_user(
        client,
        [AUDIT_LOG_VIEWER],
    )

    fake_events = [
        SimpleNamespace(
            created_at=datetime(
                2026,
                8,
                27,
                12,
                0,
            ),
            actor_username="test-user",
            action="identity.view",
            target_id="user-123",
            target_name="e1004",
            outcome="success",
            details={
                "source": "governance-portal"
            },
        )
    ]

    mock_get_events = Mock(
        return_value=fake_events
    )

    monkeypatch.setattr(
        governance_routes,
        "get_recent_audit_events",
        mock_get_events,
    )

    response = client.get(
        "/audit"
    )

    assert response.status_code == 200

    assert b"test-user" in response.data
    assert b"identity.view" in response.data
    assert b"e1004" in response.data
    assert b"success" in response.data

    mock_get_events.assert_called_once_with(
        limit=100
    )

def test_audit_log_access_denied(
    client,
):
    _login_user(
        client,
        [],
    )

    response = client.get(
        "/audit"
    )

    assert response.status_code == 403