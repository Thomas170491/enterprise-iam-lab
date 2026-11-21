# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Working agreement

This is a learning and portfolio project. The repository owner writes the code, one tested
slice at a time.

- Guide and explain by default. Write or edit application code only when explicitly asked.
- Exception: the `code-fixer` subagent (`.claude/agents/code-fixer.md`) may write tests and
  application code, but only to fix findings from the `code-reviewer` subagent that the owner
  has asked it to fix. It works test-first, one finding per slice, and never commits; the
  owner reviews and commits each slice. Do not run it unprompted.
- Work test-first in small slices: a failing test, the smallest change that passes, a commit.
- Whenever a step ends in a commit, supply the exact commit message, one per commit, in the
  style `type(scope): summary` (for example `test(access-reviews): cover ...`,
  `feat(access-reviews): ...`, `fix: ...`, `docs: ...`).
- Never read `apps/governance-portal/services/access_review_service.py` whole. Search it
  (grep for the function or error code), or read only the line range you need.

## What this is

NovaSecure is a fictional enterprise IAM lab: Keycloak (realm `novasecure`) as the identity
provider and two independent Flask apps that sign in through OIDC.

| App | Path | Port | Keycloak client | Database |
| --- | --- | --- | --- | --- |
| Employee Portal | `apps/employee-portal` | 5000 | `employee-portal` | Compose `portal-postgres` on `localhost:5433` |
| Governance Portal | `apps/governance-portal` | 5001 | `iam-admin-portal` (humans), `iam-governance-service` (backend service account) | Separately provisioned PostgreSQL, `DATABASE_URI` |

The apps share no code. Each has its own `.env`, requirements, virtualenv and Alembic
migrations. Several services exist in both (`token_service.py`, `jwks_service.py`,
`identity_service.py`) as separate copies that have diverged; change them per app.

Active development is in the Governance Portal. The Employee Portal is feature-complete for
now and is the application whose client roles Governance administers and reviews.

Documentation lives in `enterprise-iam-docs/` (index: `enterprise-iam-docs/README.md`, which
mirrors the root `README.md`). Milestone guides G1 to G11 are in `docs/guides/`; the roadmap
is `docs/roadmap.md`. The docs describe the G11 checkpoint and lag the code: G12 work
(grant-source capture, reviewer retain/revoke decisions) is already in the tree. Trust code
and tests over the prose for current behaviour.

## Commands

All Python commands run from inside the app directory. Modules import each other as top-level
packages (`from extensions import db`, `from services... import ...`), so running pytest or
Flask from the repository root fails with import errors.

### Governance Portal

```bash
cd apps/governance-portal
source venv/bin/activate            # this checkout uses venv/; the docs say .venv
python -m pip install -r requirements-dev.txt

python -m pytest -q                                              # whole suite
python -m pytest -q tests/test_access_review_decision_routes.py  # one file
python -m pytest -q tests/test_sod_service.py::test_name         # one test
python -m pytest -q -k "decision"                                # by keyword

flask --app app db upgrade                                       # apply migrations
flask --app app db migrate -m "describe the change"              # generate a migration
flask --app app run --port 5001 --cert ../../certs/localhost.pem --key ../../certs/localhost-key.pem
```

Tests need no Keycloak, PostgreSQL or `.env`: `tests/conftest.py` sets fake environment
values and an in-memory SQLite database before importing the app.

### Employee Portal

```bash
cd apps/employee-portal
source .venv/bin/activate
flask --app app db upgrade
flask --app app seed-db
flask --app app run --port 5000 --cert ../../certs/localhost.pem --key ../../certs/localhost-key.pem
python3 scripts/test-bearer-api.py   # live integration check; needs Keycloak and the app running
```

There is no pytest suite for the Employee Portal.

### Infrastructure and CI

```bash
docker compose up -d   # Keycloak at https://localhost:8080, its Postgres, Employee Postgres
```

Compose does not start either Flask app or a Governance database, and the Keycloak realm is
configured by hand (see `enterprise-iam-docs/docs/local-setup.md` and `identity-model.md`).
Session cookies are `Secure`, so the apps only work over HTTPS with the local certificates in
`certs/` (untracked).

CI (`.github/workflows/ci.yml`) runs three jobs: Governance pytest on Python 3.12, Bandit
(`-ll -ii`) over an explicit list of paths, and `pip-audit` on both `requirements.txt` files.
A new top-level package in either app must be added to the Bandit path list to be scanned.
Dependencies are pinned exactly; `pip-audit` findings are fixed by bumping the pin.

## Governance Portal architecture

`app.py` builds the app at import time (`app = create_app()`), and `config.py` raises at
import if `FLASK_SECRET_KEY`, `KEYCLOAK_CLIENT_SECRET` or `DATABASE_URI` is missing. Extension
singletons live in `extensions.py`.

Layers, from the request inwards:

- `auth/`: OIDC login and callback through Authlib. The callback stores a `user` dict in the
  server-side session (CacheLib files in `flask_session/`), and the Flask-Login `user_loader`
  in `auth/__init__.py` rebuilds `User` from it. There is no user table.
- `governance/routes.py`: every HTML route, in one blueprint. Each route stacks
  `@login_required` then `@client_role_required(<constant from auth/permissions.py>)`.
- `services/`: all business logic. Routes do not query models or call Keycloak directly.
- `models/`: `AuditEvent`, `ManagedRole`, `SoDRule`, `AccessReview`, `AccessReviewItem`.
- `api/health.py`: the only flask-smorest endpoint (`/api/v1/health`).

Conventions that span files:

- **Keycloak access.** `services/keycloak_admin_service.py` is the only module that calls the
  Admin REST API. Its functions are stateless and take `admin_api_url`, `token_url`,
  `client_id`, `client_secret` as arguments; routes read these from `current_app.config` and
  pass them down through the service layer. Each call fetches a service-account token via
  `keycloak_auth_service.get_service_access_token`, uses `timeout=5`, validates the response
  shape, and raises `KeycloakAdminAPIError` on any failure.
- **Error contract.** Services signal expected failures with `ValueError("<stable_code>")`,
  for example `access_review_not_found`, `access_review_not_draft`,
  `access_review_self_certification`. Routes compare `str(exc)` and map to a status:
  404 for not found or not owned, 409 for a state conflict, 400 otherwise. Keycloak, audit and
  SQLAlchemy failures map to 503. Renaming a code breaks the route mapping and its tests.
- **Ownership as 404.** `get_access_review_for_manager` and `get_access_review_for_reviewer`
  scope lookups to the caller and raise the not-found code for someone else's campaign, so
  existence is not disclosed.
- **Audit in the same transaction.** Access-review state changes have a core function that
  only flushes and a `*_with_audit` wrapper that calls it, calls
  `record_audit_event(..., commit=False)`, commits once, and rolls back on any exception.
  Routes call the wrapper. The audit actor is always the signed-in human; role-change events
  record the service account separately in `details`.
- **Two kinds of logging.** `AuditEvent` rows record successes durably. Denials and failures
  go to the app log through `_log_governance_event` in `routes.py` as JSON with stable
  `event`, `outcome`, `reason` fields. Never put exception messages, tokens or secrets in
  either.
- **Mutations.** State-changing routes are POST forms with a CSRF token and answer with a
  redirect (303 on the access-review routes).
- **Role administration scope.** `role_service.py` only touches roles listed and enabled in
  the `ManagedRole` catalogue (currently `employee-portal` roles), and runs
  `sod_service.evaluate_role_assignment` against the identity's effective roles first. Both
  `deny` and `requires_review` block the assignment. Catalogue entries and SoD rules are
  seeded by migrations, not by a seed command.
- **Access reviews.** Campaign status moves `draft` to `open` to `completed` or `cancelled`.
  Items are snapshots taken while the campaign is a draft. `assignment_source` is `direct`,
  `inherited` or `both`, and `grant_sources` holds the evidence in the format defined in
  `enterprise-iam-docs/docs/access-review-role-sources.md`; a group source is never inferred
  from a role merely being absent from direct mappings. Decisions are `retain` or `revoke`,
  made once, only by the assigned reviewer, only on an open campaign, and never on the
  reviewer's own access. A campaign's reviewer is never its creator
  (`access_review_creator_cannot_be_reviewer`). Recording a decision does not change
  anything in Keycloak.
- **Remediation.** `services/remediation_service.py`. A revoke sets `remediation_status`
  to `pending`; only the campaign's manager remediates it, on an open campaign. Live access
  for that one role is read first (`get_live_access_assessment`), and the two flags decide
  the action, never `drift` alone: role already gone → `completed`; no direct mapping →
  `incomplete` (manual); otherwise the direct mapping is removed through
  `role_service.remove_identity_client_role` with `expected_role_id`, live access is read
  again, and the item becomes `completed` or `incomplete`. role_service commits its own
  `role.remove` audit rows (the attempt before the Keycloak call, fail-closed); the status
  and the `access_review.remediation` event commit together at the end, and the status
  only moves from `pending`. Any failure before that leaves the item `pending` for a retry.

## Governance tests

- Tests are plain functions with a one-line docstring, grouped by behaviour into files such
  as `test_keycloak_admin_group_roles.py` and `test_access_review_capture.py`.
- Fixtures are `app` (creates and drops all tables per test) and `client`. Schema comes from
  `db.create_all()`, not from migrations, so migration-seeded rows (managed roles, SoD rules)
  must be inserted by the test.
- Route tests sign in by writing the session directly; see `_login_user(client, client_roles)`
  in `tests/access_review_helpers.py`, which the access-review route test files import.
- Keycloak is never contacted. Tests monkeypatch `get_service_access_token` and
  `requests.get`/`post`/`delete` on the `services.keycloak_admin_service` module, or patch the
  service function where the route or service imported it.
- The `app` fixture disables CSRF. CSRF tests re-enable it and read the token from the
  rendered form with `_CSRFFormParser`.
- A model change needs both an Alembic migration (PostgreSQL) and tests that pass on SQLite.

## Employee Portal notes

- `config.py` loads the repository-root `.env` (database credentials shared with Compose) and
  then its own `.env`.
- `api/decorators.py::api_login_required` accepts either a browser session or a Bearer token
  whose audience is `KEYCLOAK_API_AUDIENCE` (`employee-portal-api`), and sets `g.api_user`.
  API failures return JSON from `api/errors.py`, never a login redirect, and never reveal why
  a token was rejected.

## Safety

All identities and data are fictional, but `.env` files, `certs/`, `flask_session/` and raw
tokens stay out of git and out of logs and test output.
