from unittest.mock import Mock

import pytest

import services.audit_service as audit_service

from services.exceptions import AuditPersistenceError

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