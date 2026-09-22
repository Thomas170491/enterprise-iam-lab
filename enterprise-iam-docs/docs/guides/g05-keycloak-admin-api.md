# G5 — Keycloak Admin API service

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Encapsulate Keycloak HTTP operations so routes and policy services can work with identities and roles without constructing every request themselves.

## Implementation

The Admin API service obtains service tokens, uses Authorization headers and timeouts, checks HTTP status and validates expected response shapes for its read helpers.

| Helper family | Purpose |
| --- | --- |
| `search_users`, `get_user` | Search realm identities or retrieve one user UUID |
| `get_user_groups` | Retrieve the user's groups |
| `get_effective_realm_roles` | Retrieve effective realm-role mappings |
| `get_client_uuid` | Resolve a public client ID to Keycloak's internal client UUID |
| `get_effective_client_roles` | Retrieve client mappings through the composite endpoint |
| `get_direct_client_roles` | Retrieve direct client-role mappings |
| `get_client_role` | Retrieve the role representation used in mutations |
| `assign_client_role`, `remove_client_role` | Submit a role representation to user role-mapping endpoints |

Client ID and internal client UUID are different identifiers. Role-mapping endpoints use the UUID; callers use meaningful client IDs such as `employee-portal`.

## Verify the milestone

Admin-service tests mock user/group/role responses, missing clients and assignment/removal HTTP errors. Live verification must separately exercise the service account's resource visibility and mapping permissions.

G11 exposed this distinction: the console administrator could see `iam-admin-portal`, while the service query returned no matching client until the service policy gained View access to that specific client.

## Boundaries

These are low-level operations. Governance routes call higher-level policy/audit services for mutations; calling the raw helpers directly does not enforce the managed catalogue, SoD policy or human audit flow. Retrieving effective roles also does not provide a complete explanation of every group/composite inheritance path.

## Implementation references

- [services/keycloak_admin_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/keycloak_admin_service.py)
- [services/keycloak_auth_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/keycloak_auth_service.py)
- [services/exceptions.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/exceptions.py)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_keycloak_admin_service.py
```

Tests inspected: [test_keycloak_admin_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_keycloak_admin_service.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Governance portal](../governance-portal.md)


Previous: [G4 — Service authentication](g04-service-authentication.md) · Next: [G6 — Identity search](g06-identity-search.md)
