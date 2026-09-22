# G3 — Governance RBAC

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Separate authenticated access from the permissions required to inspect identities, administer roles, manage campaigns and read audits.

## Implementation

Protected routes combine `login_required` with `client_role_required`. The latter compares the required role with `current_user.client_roles`, returning HTTP 403 if absent. Permission constants live in `auth/permissions.py` and must match the exact `iam-admin-portal` client-role names in Keycloak.

| Permission | Current use |
| --- | --- |
| `iam-dashboard-access` | Dashboard |
| `identity-viewer` | Identity search and access inspection |
| `role-manager` | Governed Employee Portal role changes |
| `audit-log-reviewer` | Audit viewer |
| `access-review-manager` | G11 campaign management |
| `access-reviewer` | G11 assigned campaign viewing |

`identity-manager` and `report-exporter` also exist as constants, but their presence does not implement identity editing or reporting.

## Verify the milestone

RBAC tests check authenticated/unauthenticated dashboard requests and the custom 403 page. Permission-name tests protect the constants. Persona tests exercise the configured role bundles for Leo, Emma, Nadia and Alice.

When testing a route, check its backend response as well as navigation visibility. In G11, role permission is followed by ownership or reviewer-assignment checks; a manager role does not confer ownership of every campaign.

## Boundaries

Persona tests describe intended bundles; they do not prevent an administrator from assigning conflicting roles in Keycloak. A standalone realm role such as `iam-operator` does not automatically imply a client role unless an explicit mapping/composite grants it. Automatic governance role-conflict enforcement and self-certification restrictions remain future work.

## Implementation references

- [auth/permissions.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/auth/permissions.py)
- [auth/decorators.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/auth/decorators.py)
- [governance/routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/governance/routes.py)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_RBAC.py tests/test_permissions.py tests/test_persona_rbac.py
```

Tests inspected: [test_RBAC.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_RBAC.py), [test_permissions.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_permissions.py), [test_persona_rbac.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_persona_rbac.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Identity model](../identity-model.md)
- [Governance portal](../governance-portal.md)

Previous: [G2 — OIDC authentication](g02-oidc-authentication.md) · Next: [G4 — Service authentication](g04-service-authentication.md)
