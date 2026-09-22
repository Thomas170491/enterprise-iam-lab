# G9 — Governed role administration

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Permit authorized operators to assign or remove supported Employee Portal roles with policy checks and human-attributed audit records.

## Implementation

The browser mutation routes require `role-manager`, authentication and CSRF protection. They select `employee-portal` on the server rather than trusting a submitted client override.

The role service checks that an enabled managed role exists for the client and that the requested role is enabled in the catalogue. It resolves the client UUID and role representation before recording a required attempted event and calling Keycloak.

The current assignment path includes the G10 SoD evaluation before the attempted mutation event. Removal does not run assignment SoD evaluation; it still requires catalogue scope and an initial audit.

## Audit sequence and failures

For an allowed assignment, the sequence is `sod.evaluate`, `role.assign` with `attempted`, the Keycloak call, then `role.assign` with `success` or `failure`. Removal uses attempted and final `role.remove` events.

If required pre-mutation auditing fails, no role mutation occurs. If Keycloak fails and failure auditing also fails, the original Keycloak error is preserved. If Keycloak succeeds but final audit persistence fails, the service logs that problem rather than claiming the completed change failed.

## Verify the milestone

Service tests cover managed choices, assignment/removal, actor attribution, rejected scope and audit-failure ordering. Route/security regressions cover forged unmanaged roles, forged client selection, unauthorized removal and CSRF behavior. Test fixtures seed managed roles and mock the Admin API rather than changing real Keycloak users.

## Boundaries

Removing a direct role mapping may leave effective access through inheritance. Direct Keycloak administration bypasses portal policy. The current route scope and seeded catalogue target Employee Portal; the service's catalogue lookup is not a separate hardcoded restriction against every possible future client entry. Review catalogue and Keycloak permissions together before expanding scope.

Catalogue approval metadata is not an implemented approval workflow. Disabled catalogue entries also block this service's removal path; disabling an entry does not revoke existing Keycloak access.

## Implementation references

- [services/role_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/role_service.py)
- [governance/routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/governance/routes.py)
- [models/managed_role.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/models/managed_role.py)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_role_service.py tests/test_role_routes.py tests/test_role_security_regressions.py
```

Tests inspected: [test_role_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_role_service.py), [test_role_routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_role_routes.py), [test_role_security_regressions.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_role_security_regressions.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Segregation of duties](../segregation-of-duties.md)
- [Governance portal](../governance-portal.md)

Previous: [G8 — Audit data model and logging](g08-audit-model-and-logging.md) · Next: [G10 — Segregation of Duties](g10-segregation-of-duties.md)
