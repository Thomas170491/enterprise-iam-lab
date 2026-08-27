

import pytest
import governance.routes as governance_routes
import services.audit_service as audit_service

from services.exceptions import AuditPersistenceError, AuditQueryError
from unittest.mock import Mock
from datetime import datetime
from types import SimpleNamespace


from auth.permissions import AUDIT_LOG_VIEWER


def test_record_audit_event(
    monkeypatch,
):
    fake_event = Mock()

    fake_event.id = 42

    mock_audit_event = Mock(
        return_value=fake_event
    )

    monkeypatch.setattr(
        audit_service,
        "AuditEvent",
        mock_audit_event,
    )

    mock_add = Mock()
    mock_commit = Mock()

    monkeypatch.setattr(
        audit_service.db.session,
        "add",
        mock_add,
    )

    monkeypatch.setattr(
        audit_service.db.session,
        "commit",
        mock_commit,
    )

    event = audit_service.record_audit_event(
        actor_user_id="actor-123",
        actor_username="e1001",
        action="identity.view",
        target_type="identity",
        target_id="user-123",
        target_name="e1004",
        outcome="success",
        details={
            "source": "governance-portal"
        },
    )

    mock_audit_event.assert_called_once_with(
        actor_user_id="actor-123",
        actor_username="e1001",
        action="identity.view",
        target_type="identity",
        target_id="user-123",
        target_name="e1004",
        outcome="success",
        details={
            "source": "governance-portal"
        },
    )

    mock_add.assert_called_once_with(
        fake_event
    )

    mock_commit.assert_called_once()

    assert event is fake_event

def test_record_audit_event_rolls_back_on_failure(monkeypatch):
        fake_event = Mock()

        monkeypatch.setattr(
            audit_service,
            "AuditEvent",
            Mock(return_value=fake_event),
        )

        mock_add = Mock()

        mock_commit = Mock(
            side_effect=audit_service.SQLAlchemyError(
                "database failure"
            )
        )

        mock_rollback = Mock()

        monkeypatch.setattr(
            audit_service.db.session,
            "add",
            mock_add,
        )

        monkeypatch.setattr(
            audit_service.db.session,
            "commit",
            mock_commit,
        )

        monkeypatch.setattr(
            audit_service.db.session,
            "rollback",
            mock_rollback,
        )

        with pytest.raises(
            AuditPersistenceError
        ) as exc_info:

            audit_service.record_audit_event(
                actor_user_id="actor-123",
                actor_username="e1001",
                action="identity.view",
                target_type="identity",
                target_id="user-123",
                target_name="e1004",
                outcome="success",
            )

        mock_add.assert_called_once_with(
            fake_event
        )

        mock_commit.assert_called_once()

        mock_rollback.assert_called_once()

        assert exc_info.value.reason == (
            "Failed to persist audit event: database failure"
        )

def test_get_recent_audit_events(
    monkeypatch
):
    fake_events = [
        Mock(),
        Mock(),
    ]

    fake_scalar_result = Mock()
    fake_scalar_result.all.return_value = fake_events

    fake_execute_result = Mock()
    fake_execute_result.scalars.return_value = (
        fake_scalar_result
    )

    mock_execute = Mock(
        return_value=fake_execute_result
    )

    monkeypatch.setattr(
        audit_service.db.session,
        "execute",
        mock_execute,
    )

    events = (
        audit_service.get_recent_audit_events(
            limit=50
        )
    )

    assert events == fake_events

    mock_execute.assert_called_once()

    fake_execute_result.scalars.assert_called_once()

    fake_scalar_result.all.assert_called_once()

def test_get_recent_audit_events_handles_failure(
    monkeypatch,
):
    mock_execute = Mock(
        side_effect=audit_service.SQLAlchemyError(
            "database unavailable"
        )
    )

    mock_rollback = Mock()

    monkeypatch.setattr(
        audit_service.db.session,
        "execute",
        mock_execute,
    )

    monkeypatch.setattr(
        audit_service.db.session,
        "rollback",
        mock_rollback,
    )

    with pytest.raises(
        AuditQueryError
    ) as exc_info:

        audit_service.get_recent_audit_events(
            limit=50
        )

    mock_execute.assert_called_once()
    mock_rollback.assert_called_once()

    assert exc_info.value.reason == (
        "Failed to retrieve audit events: database unavailable"
    )