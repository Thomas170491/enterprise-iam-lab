# G2 — OIDC authentication

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Authenticate human Governance users through Keycloak and establish a server-side application session.

## Implementation

1. `GET /login` asks Authlib to start the OIDC Authorization Code Flow for `iam-admin-portal`.
2. Keycloak authenticates the user and returns to `/auth/callback`.
3. Authlib exchanges the code for tokens. The app validates the access token and extracts realm roles and this client's roles.
4. The callback uses the OIDC user information and checks that its `sub` matches the validated access-token subject.
5. The application constructs a `User`, saves the identity/roles in the server-side session and calls `login_user`.
6. The user is redirected to the dashboard, where the dashboard role is checked independently.

The user loader reconstructs the user on subsequent requests. If the stored subject does not match Flask-Login's user ID, it clears the inconsistent session and returns no user.

Logout is an authenticated, CSRF-protected POST. It clears the local session and redirects to Keycloak's logout endpoint with the configured post-logout redirect and an ID-token hint when available.

## Verify the milestone

Authentication tests exercise the redirect, callback/session creation and logout. User-loader tests cover normal reconstruction, missing session data and subject mismatch. Token-service tests cover role extraction and claim validation helpers.

For a manual check, log in with a configured test identity over HTTPS, inspect the expected dashboard authorization outcome, then log out and revisit a protected page.

## Boundaries

Authentication alone grants no administrative permission. Roles stored in the session are not continuously fetched from Keycloak on every request; session state and live reviewer eligibility checks are distinct. The Governance browser client and backend service client have separate secrets and purposes.

## Implementation references

- [auth/routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/auth/routes.py)
- [auth/user.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/auth/user.py)
- [auth/__init__.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/auth/__init__.py)
- [services/token_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/token_service.py)
- [services/jwks_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/jwks_service.py)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_auth.py tests/test_user_loader.py tests/test_token_service.py
```

Tests inspected: [test_auth.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_auth.py), [test_user_loader.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_user_loader.py), [test_token_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_token_service.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Security controls](../security-controls.md)
- [Local setup](../local-setup.md)

Previous: [G1 — Scaffold](g01-scaffold.md) · Next: [G3 — Governance RBAC](g03-governance-rbac.md)
