# G6 — Identity search

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Allow an authorized Governance user to locate a realm identity without copying the identity directory into the Governance database.

## Implementation

`GET /identities` requires `identity-viewer`. The route trims the `search` query parameter and distinguishes an initial page visit from an explicitly submitted search:

| Request | Behavior |
| --- | --- |
| `/identities` | Display the form without automatically querying users |
| `/identities?search=e1005` | Search Keycloak with the entered value |
| `/identities?search=` | Explicit empty search; request the bounded result set |

`search_identities` calls `search_users` with a default maximum of 20 and normalizes each Keycloak user representation for the template. The normalized fields include UUID, username, names, email, enabled state, employee ID, employment status, job title and risk level.

Keycloak custom attributes are generally lists. `_first_attribute` takes the first value when present and returns `None` when absent.

## Verify the milestone

Service tests check normalized users and missing attributes. Route tests cover login/role requirements, the initial empty page, submitted searches and explicitly empty searches.

In the local UI, search a fictional username, inspect its displayed attributes and follow the identity link. Do not treat the employee username as the UUID required by the Admin API or campaign form.

## Boundaries

This is bounded search, not a complete directory export or pagination workflow. Search results are live Keycloak data. A displayed identity does not confer permission to mutate its access; G9 checks mutation permissions separately.

## Implementation references

- [services/identity_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/identity_service.py)
- [governance/routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/governance/routes.py)
- [templates/identities.html](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/templates/identities.html)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_identity_service.py tests/test_identity_routes.py
```

Tests inspected: [test_identity_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_identity_service.py), [test_identity_routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/tests/test_identity_routes.py). These commands are provided for verification; they were not executed during this documentation update.

## Further reading

- [Identity model](../identity-model.md)
- [Governance portal](../governance-portal.md)

Previous: [G5 — Keycloak Admin API service](g05-keycloak-admin-api.md) · Next: [G7 — Effective identity access view](g07-effective-access-view.md)
