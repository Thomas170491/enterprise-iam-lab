# Testing and verification

[Documentation index](../README.md#start-here)

## Governance automated tests

From the repository root, using the Governance virtual environment:

```bash
cd apps/governance-portal
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

If your existing environment is named `venv`, activate `venv/bin/activate` instead. Tests use fake configuration and SQLite through the fixtures; Keycloak calls are mocked. They do not require production credentials or validate the live service-account configuration.

Focused G11 checks:

```bash
python -m pytest -q tests/test_access_review_models.py tests/test_access_review_service.py tests/test_access_review_audit.py tests/test_access_review_routes.py
```

Coverage includes model constraints, input validation, campaign state changes, manager ownership, reviewer assignment, role eligibility, direct managed-role capture, duplicate suppression, transaction rollback, audit actor attribution, route errors, form visibility and missing/invalid/valid CSRF tokens.

The normal app fixture disables CSRF for isolated route tests. Dedicated CSRF cases enable it explicitly and verify that invalid requests never call the mutation service.

## CI

The committed workflow runs three jobs on main pushes and pull requests: Governance pytest on Python 3.12, Bandit over the configured application paths, and pip-audit for both applications' dependencies. Consult the [Actions page](https://github.com/Thomas170491/enterprise-iam-lab/actions) for current results. A dependency/SAST pass does not establish that every endpoint or runtime configuration is secure.

No test count or current CI success is asserted by this documentation update. The G11 live verification is recorded in [G11 — Access review workflows](guides/g11-access-review-workflows.md#manual-verification--2026-09-22).

## Employee Portal acceptance and integration checks

### Department Access

| User | Expected department |
| --- | --- |
| Alice Martin | Human Resources |
| Marc Dubois | Finance |
| Nadia Rossi | Security |
| Leo Bernard | Information Technology |
| Emma Keller | Security |

### Manager Access

| User | `/manager` |
| --- | --- |
| Alice Martin | `403 Forbidden` |
| Marc Dubois | Allowed |
| Nadia Rossi | `403 Forbidden` |
| Leo Bernard | `403 Forbidden` |
| Emma Keller | `403 Forbidden` |

### Authentication State

Unauthenticated access to protected HTML routes requires authentication.

Unauthenticated REST requests return JSON `401` responses instead of redirecting to the login page.

### Passkey

The privileged test identity can:

```text
Register a passkey
        |
        v
Sign out
        |
        v
Authenticate with the passkey
        |
        v
Complete the OIDC flow
```

### CSRF

A valid logout request:

```text
POST /logout
+ valid CSRF token
-> accepted
```

A POST without the CSRF token:

```text
POST /logout
+ missing / invalid CSRF token
-> rejected
```

### Bearer API Integration Test

The repository includes:

```text
apps/employee-portal/scripts/test-bearer-api.py
```

The integration test obtains a real Keycloak access token for the fictional Finance manager identity and validates both successful and failed API authentication paths.

Previously documented Employee Portal integration result (not rerun during the G11 documentation update):

```text
PASS: /me -> HTTP 200
PASS: /access -> HTTP 200
PASS: /department -> HTTP 200
PASS: Missing authentication -> HTTP 401
PASS: Malformed Bearer header -> HTTP 401
PASS: Invalid Bearer token -> HTTP 401

Result: 6/6 tests passed
```

A separate negative test also confirmed that a correctly signed Keycloak token without the required `employee-portal-api` audience is rejected with `401 Unauthorized`.

#### Test-Only Keycloak Client

Bearer integration testing uses a local test-only client:

```text
employee-portal-cli-test
```

Direct Access Grants are used only to simplify automated local integration testing. This client is **not** part of the intended production architecture and should be disabled or removed when the integration test is not required.

Run the existing integration script from `apps/employee-portal` with Keycloak and the app running:

```bash
python3 scripts/test-bearer-api.py
```

Ensure its local URLs and CA trust match the HTTPS lab. Do not print access tokens or real passwords in test output.
