# G4 — Service authentication

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Give the Governance backend its own identity for Keycloak Admin API calls while keeping the human operator as the accountable audit actor.

## Implementation

`get_service_access_token` posts to the realm's token endpoint using `grant_type=client_credentials`. Requests supplies the service client ID and secret through HTTP Basic authentication, with a five-second timeout.

The helper raises `KeycloakServiceAuthenticationError` for caught HTTP/network failures and for a response lacking an access token. It returns the token to the caller; Admin API helpers send it in an Authorization Bearer header.

| Configuration | Value or source |
| --- | --- |
| Service client | `iam-governance-service` |
| Token endpoint | Realm OIDC token endpoint from app configuration |
| Client ID | `KEYCLOAK_SERVICE_CLIENT_ID` |
| Client secret | `KEYCLOAK_SERVICE_CLIENT_SECRET`, outside source control |

Use the locally trusted CA bundle for HTTPS. The browser user's token is not substituted for the service credentials.

## Verify the milestone

The service-authentication tests mock successful token issuance, a failed HTTP request and a missing token. A real integration check also requires service accounts enabled on the client and the correct client secret.

## Boundaries

A valid token does not prove the service account is authorized to read a client or modify a role mapping. Those permissions are checked by Keycloak separately. The current helper performs token retrieval for its callers rather than maintaining a shared token cache. Its JSON parsing is not a complete schema-validation layer; do not interpret these tests as coverage of every malformed upstream response.

## Implementation references

- [services/keycloak_auth_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/keycloak_auth_service.py)
- [services/exceptions.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/exceptions.py)
- [config.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/config.py)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_keycloak_auth_service.py
```

Tests inspected: [test_keycloak_auth_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_keycloak_auth_service.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Governance portal](../governance-portal.md)
- [Security controls](../security-controls.md)

Previous: [G3 — Governance RBAC](g03-governance-rbac.md) · Next: [G5 — Keycloak Admin API service](g05-keycloak-admin-api.md)
