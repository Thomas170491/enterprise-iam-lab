# G8 — Audit data model and logging

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Persist who performed a Governance operation, what it targeted and its outcome so later reviews can reconstruct activity.

## Implementation

`AuditEvent` stores actor ID/username, action, target type/ID/name, outcome, details and creation time. Schema changes are managed through Alembic. The durable records live in the Governance PostgreSQL database, not the Keycloak database.

`record_audit_event` creates the model and normally commits. Its later-added `commit=False` option flushes without committing, allowing G11 wrappers to commit a campaign change and its audit together. Caught SQLAlchemy errors roll back and become `AuditPersistenceError`.

`get_recent_audit_events` returns recent records newest first with a default limit of 100. The existing `/audit` viewer requires `audit-log-reviewer`; G13 remains the dedicated viewer milestone review.

## Audit semantics

| Context | Failure behavior |
| --- | --- |
| Identity inspection | Log audit failure; successful read can still render |
| Role mutation attempt | Required audit must persist before Keycloak mutation |
| Role mutation final outcome | Log final audit failure; do not misrepresent a completed Keycloak change |
| G11 campaign mutation | Commit campaign and success event together or roll both back |

The actor is the authenticated human. The technical service client is separate context. Route JSON log messages and database audit records serve different purposes; they are not interchangeable.

## Verify the milestone

Audit-service tests cover event creation, rollback, caller-owned transactions, recent queries and query failures. The live G11 audit screenshot shows create, populate, open and cancel attributed to Leo while Emma views them.

## Boundaries

The current implementation does not establish cryptographic tamper evidence, immutable external storage, a retention policy or SIEM delivery. The database and Keycloak do not share a distributed transaction. G15 will consolidate structured security events.

## Implementation references

- [models/audit_event.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/models/audit_event.py)
- [services/audit_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/audit_service.py)
- [governance/routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/governance/routes.py)
- [templates/audit-log.html](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/templates/audit-log.html)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_audit_service.py tests/test_audit_route.py
```

Tests inspected: [test_audit_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_audit_service.py), [test_audit_route.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_audit_route.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Security controls](../security-controls.md)

Previous: [G7 — Effective identity access view](g07-effective-access-view.md) · Next: [G9 — Governed role administration](g09-governed-role-administration.md)
