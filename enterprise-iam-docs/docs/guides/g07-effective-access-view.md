# G7 — Effective identity access view

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Show an identity's groups and role entitlements so an operator can inspect access before making a governed change.

## Implementation

`get_identity_access` aggregates the normalized user, groups, effective realm roles, effective client roles and direct client roles. The detail route targets `employee-portal` and requires `identity-viewer`.

The returned structure separates `identity`, `groups`, `realm_roles`, `client_roles` and `direct_client_roles`. The route also retrieves enabled managed-role choices and builds direct-role names for presentation.

This distinction matters: a role may be effective through a group or composite even when there is no direct mapping available to remove. The template limits removal controls to direct roles and users with the relevant management permission.

A successful detail view attempts to record an `identity.view` event with the human actor. A caught Keycloak API failure produces the detail error page with HTTP 502. Failure to persist the view audit is logged without discarding an otherwise successful read.

## Verify the milestone

Identity-route tests exercise aggregation, page access, upstream failures, managed choices, direct-role removal visibility and the absence of mutation controls for viewers.

Compare a user's direct and inherited role mappings in Keycloak with the identity detail page. Group-inherited roles belong in the effective view even though G11's initial snapshot capture excludes them.

## Boundaries

Multiple upstream calls do not create an atomic snapshot of Keycloak state. Roles can change between calls. This page is an access inspection view, not a full provenance graph or campaign snapshot. Effective-role inspection was implemented before G11's direct-only capture; extending campaign capture is G12 work.

## Implementation references

- [services/identity_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/identity_service.py)
- [governance/routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/governance/routes.py)
- [templates/identity_detail.html](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/templates/identity_detail.html)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_identity_routes.py
```

Tests inspected: [test_identity_routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_identity_routes.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Governance portal](../governance-portal.md)


Previous: [G6 — Identity search](g06-identity-search.md) · Next: [G8 — Audit data model and logging](g08-audit-model-and-logging.md)
