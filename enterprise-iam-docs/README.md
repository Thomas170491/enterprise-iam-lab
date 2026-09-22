# Enterprise IAM & Access Governance Lab

NovaSecure is a fictional enterprise IAM environment built with **Keycloak, Flask, PostgreSQL and OpenID Connect**. The lab demonstrates how authentication, application authorization, governed role changes and access reviews fit together.

## Current scope

| Component | Implemented scope |
| --- | --- |
| Employee Portal | OIDC login, passkeys, department and manager RBAC, database-backed resources, session and Bearer-token REST API authentication |
| Governance Portal | Identity search, effective-access inspection, audited role administration, database-backed segregation-of-duties checks and an audit viewer |
| Access reviews — G11 | Manager-owned campaigns, reviewer eligibility checks, direct-role snapshots, opening, cancellation and transactional audit events |

**G12 is next:** certification decisions and inherited-access capture. G11 captures only directly assigned, enabled managed roles from `employee-portal`; it does not certify or revoke access.

The September 22, 2026 manual walkthrough exercised campaign creation, capture, opening, reviewer access and cancellation against real Keycloak and PostgreSQL. See the [verification record](docs/guides/g11-access-review-workflows.md#manual-verification--2026-09-22) for evidence and its limits.
 
## Start here

| Document | Contents |
| --- | --- |
| [G1–G11 milestone guides](docs/guides/README.md) | Step-by-step implementation explanations, focused tests and boundaries |
| [Local setup](docs/local-setup.md) | TLS, Docker, environment configuration, databases and app startup |
| [Identity model](docs/identity-model.md) | Fictional users, attributes, groups, realm roles and client roles |
| [Employee Portal](docs/employee-portal.md) | Browser features, REST endpoints and application data |
| [Governance Portal](docs/governance-portal.md) | Administrative boundaries, service account, role changes and audit logging |
| [Segregation of duties](docs/segregation-of-duties.md) | Seeded policies, precedence, blocking behavior and limitations |
| [Access reviews](docs/guides/g11-access-review-workflows.md) | G11 workflow, permissions, snapshots, audit trail and manual evidence |
| [Security controls](docs/security-controls.md) | OIDC, sessions, JWT validation, CSRF and deployment limits |
| [Testing](docs/testing.md) | Automated tests, CI and integration checks |
| [Roadmap](docs/roadmap.md) | G1–G17 progress and later enterprise-lab phases |
| [Lifecycle and monitoring](docs/lifecycle-and-monitoring.md) | Planned JML processes, SIEM integration and investigation scenarios |

Architecture: [Employee Portal](diagrams/employee-portal-architecture.md) · [Governance Portal](diagrams/iam-governance-portal-architecture.md).

## Repository map

| Path | Purpose |
| --- | --- |
| `apps/employee-portal/` | Employee-facing Flask application and Bearer API test script |
| `apps/governance-portal/` | Governance application, models, migrations and pytest suite |
| `enterprise-iam-docs/docs/` | Topic-specific documentation |
| `enterprise-iam-docs/diagrams/` | Architecture references |
| `enterprise-iam-docs/portfolio/` | Configuration and workflow evidence |
| `compose.yaml` | Keycloak and its PostgreSQL database, plus Employee Portal PostgreSQL |
| `.github/workflows/ci.yml` | Governance tests, Bandit and dependency auditing |

The Governance database is configured separately through `DATABASE_URI`; it is not provisioned by the current Compose file.

## Technology

Python 3.12 for Governance CI; Flask, Authlib, Flask-Login, Flask-Session/CacheLib, Flask-WTF, SQLAlchemy/Alembic, Psycopg, Requests and `joserfc`. Compose pins Keycloak 26.7.0 and PostgreSQL 17 Alpine images.

## Scope and safety

This is a local learning and portfolio lab, not a production deployment. Local HTTPS is configured, but Keycloak still uses `start-dev` and Flask is run with its development server. LDAP, lifecycle automation, certification decisions and centralized SIEM integration remain future work.

All identities and business data are fictional. Credentials, private keys, session data and raw tokens must stay outside source control.
