# G1 — Scaffold

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Establish the Governance Portal's application structure so authentication, APIs, database models and business services can be initialized consistently.

## Implementation

`app.py` exposes `create_app()` and also creates the module-level `app` used by the Flask CLI. Configuration comes from `config.py`; shared extension instances live in `extensions.py` and are bound in the factory through `init_app`.

The factory initializes Flask-Smorest, Authlib, CSRF protection, Flask-Login, server-side sessions, SQLAlchemy and migrations. It registers the authentication and Governance blueprints and the health API, and renders the custom unauthorized template for HTTP 403.

| Area | Responsibility |
| --- | --- |
| `auth/` | Browser login, session user and role checks |
| `api/` | Health endpoint and OpenAPI scaffolding |
| `governance/` | HTML routes and workflow orchestration |
| `services/` | Identity, administrative and policy operations |
| `models/` and `migrations/` | Persistent data and schema changes |
| `templates/` and `static/` | Views and presentation |
| `tests/` | Isolated regression tests |

## Verify the milestone

The health endpoint is `GET /api/v1/health`. It returns `status: ok` and the application name. The OpenAPI document is served at `/api/openapi.json`. The scaffold tests check health, OpenAPI, route registration and secure cookies by default.

## Boundaries

The health response indicates application availability; it does not probe Keycloak or database readiness. OpenAPI scaffolding is not a complete Governance REST API. The factory described here includes extensions added after G1; these guides describe the current implementation, not historical source snapshots.

## Implementation references

- [app.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/app.py)
- [extensions.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/extensions.py)
- [config.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/config.py)
- [api/health.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/api/health.py)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_scaffold.py
```

Tests inspected: [test_scaffold.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_scaffold.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Local setup](../local-setup.md)
- [Governance portal](../governance-portal.md)

Previous: [Local setup](../local-setup.md) · Next: [G2 — OIDC authentication](g02-oidc-authentication.md)
