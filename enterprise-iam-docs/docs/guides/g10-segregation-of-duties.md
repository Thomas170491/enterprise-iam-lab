# G10 — Segregation of Duties

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Prevent a governed role assignment from creating a configured conflict with the identity's current effective Employee Portal roles.

## Implementation

`ManagedRole` defines catalogue entries; `SoDRule` links a normalized pair of catalogue IDs with an enabled policy outcome. The evaluator receives the client, requested role and current role names and returns `decision`, `reason` and `rule_id`.

1. Deny an unmanaged or disabled requested role.
2. Resolve held roles through the same client's catalogue, including disabled catalogue entries for access already held.
3. For each held/requested pair, sort the IDs and look up the enabled rule.
4. Return immediately for a deny rule.
5. Preserve a review match while checking later roles for deny rules.
6. Return the saved review result after the loop, otherwise allow.

Returning the saved review rule is important: the final loop lookup may have no match, so it must not overwrite or replace earlier review evidence.

## Seeded policy and enforcement

| Pair | Decision |
| --- | --- |
| `hr-data-viewer` + `finance-data-viewer` | `deny` |
| `finance-data-viewer` + `security-data-viewer` | `requires_review` |

These are example lab policies. Both blocking decisions produce `sod.evaluate` audit evidence, prevent Keycloak assignment and return a specific HTTP 403 explanation. Neither produces a subsequent attempted assignment event for that blocked request.

## Verify the milestone

Tests cover managed/unmanaged and disabled requested roles, deny/review matches, ignored disabled rules, deny precedence, held disabled roles and a review match followed by a nonmatch. Role-service and route tests check that blocked decisions do not reach Keycloak assignment.

## Boundaries

`requires_review` currently blocks; it does not create an approval request. The evaluator considers current roles represented in the managed catalogue and configured rules; it is not a universal conflict scanner. It does not remediate pre-existing conflicts, enforce governance administrator/auditor separation or govern direct console changes. G11 periodic access campaigns are a separate workflow.

## Implementation references

- [services/sod_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/sod_service.py)
- [services/role_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/role_service.py)
- [models/managed_role.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/models/managed_role.py)
- [models/sod_rule.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/models/sod_rule.py)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_sod_service.py tests/test_sod_models.py tests/test_role_service.py tests/test_role_routes.py
```

Tests inspected: [test_sod_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_sod_service.py), [test_sod_models.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_sod_models.py), [test_role_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_role_service.py), [test_role_routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_role_routes.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Segregation of duties](../segregation-of-duties.md)


Previous: [G9 — Governed role administration](g09-governed-role-administration.md) · Next: [G11 — Access review workflows](g11-access-review-workflows.md)