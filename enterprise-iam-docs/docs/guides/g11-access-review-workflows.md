# G11 — Access review workflows

[Milestone index](README.md) · [Documentation index](../README.md)

## Purpose

Let a manager prepare an access review campaign, capture identity-role snapshots and assign a reviewer. Preserve the campaign and its audit evidence through opening and cancellation.

A snapshot records access selected for review at capture time. Capturing it does not grant or revoke the role, and subsequent Keycloak changes do not automatically update the snapshot.

## Implementation

`AccessReview` stores the campaign name, creator, assigned reviewer, status, timestamps and optional due date. `AccessReviewItem` stores the campaign reference, identity UUID, username, client, role UUID, role name and capture timestamp. A database uniqueness constraint prevents duplicate campaign/user/client/role combinations.

1. Create a draft after validating the inputs and reviewer eligibility. The reviewer must exist, be enabled and hold the effective `iam-admin-portal/access-reviewer` role.
2. Resolve the campaign through its authenticated manager before allowing a mutation.
3. Retrieve an identity's direct Employee Portal role mappings and retain roles enabled in the managed-role catalogue.
4. Skip existing snapshots and add eligible new items while the campaign remains in draft.
5. Open a nonempty draft to prevent further capture.
6. Allow cancellation from draft or open, preserving captured items.

Core service functions flush without committing. Audited wrappers perform the operation and write its success audit event with `commit=False`, then commit once. Exceptions trigger rollback and are re-raised so the campaign change and audit record succeed or fail together.

## Permissions and lifecycle

Managers require `access-review-manager` and can manage only campaigns they created. Reviewers require `access-reviewer` and can read only campaigns assigned to their authenticated user UUID. These are client roles under `iam-admin-portal`. Missing and inaccessible campaigns receive the same not-found response.

| State | G11 behavior |
| --- | --- |
| `draft` | Capture access; open when nonempty; cancel |
| `open` | Read snapshots; cancel; no further capture |
| `cancelled` | Read preserved snapshots; no further mutations |
| `completed` | Model status reserved for the later certification workflow |

Reviewer lists include all assigned campaign statuses. Opening does not mark the first moment that a reviewer can see a campaign. Mutation routes use POST with CSRF protection and redirect to the manager detail page after success.

Audit actions are `access_review.create`, `access_review.populate`, `access_review.open` and `access_review.cancel`. Events identify the human actor and campaign; population records the number of items added, and state transitions record the previous and new statuses.

## Verify the milestone

Automated coverage checks input validation, ownership, reviewer eligibility, capture filtering, duplicate suppression, state transitions, snapshot preservation, transaction rollback, route permissions and CSRF protection. Keycloak calls are mocked in automated tests.

The manual walkthrough on 2026-09-22 confirmed campaign creation by Leo, capture of Alice's directly assigned Finance role, opening, reviewer access by Emma and cancellation with the snapshot preserved. The audit viewer showed creation, population, opening and cancellation events. An earlier inherited-only capture correctly added zero items under the G11 capture rules.

See the [manual verification and screenshots](#manual-verification--2026-09-22) for evidence and its limits.

## Boundaries

G11 captures direct Employee Portal mappings whose catalogue entries are enabled. It does not expand group or composite inheritance into effective-access snapshots. Reviewer eligibility does use effective roles, so inherited reviewer permission is accepted.

Repeated capture adds eligible missing items; it does not reconcile or delete old snapshots. A successful capture may add zero items. Cancellation does not revoke live access.

There are no certification decisions, automated revocations, completion workflow, deadline enforcement or reminders. Self-certification prevention is not implemented. G12 will add certification decisions and extend capture to inherited/effective access, preserving assignment provenance so remediation can distinguish direct mappings from group or composite sources.

## Implementation references

- [models/access_review.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/models/access_review.py)
- [models/access_review_item.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/models/access_review_item.py)
- [services/access_review_service.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/services/access_review_service.py)
- [governance/routes.py](https://github.com/Thomas170491/enterprise-iam-lab/blob/b6072773931b2b593a7264c375fd6ab1035686fa/apps/governance-portal/governance/routes.py)

## Focused tests

Run from `apps/governance-portal` with its virtual environment active:

```bash
python -m pytest -q tests/test_access_review_service.py tests/test_access_review_audit.py tests/test_access_review_routes.py
```

These commands cover the service, audit wrappers and routes. They were not executed during this documentation update. The source references above are pinned to the same reviewed commit as the G1–G10 guides.

## Manual verification — 2026-09-22

Campaign: **G11 manual verification**. Manager: **Leo (`e1004`)**.
Reviewer: **Emma (`e1005`)**. Captured identity: **Alice (`e1001`)**.

### Draft campaign

The manager created a draft campaign assigned to Emma.
No access items had been captured yet.

![Draft campaign assigned to Emma](../../portfolio/g11/01-draft-campaign.png)

### Open campaign

Alice's directly assigned `employee-portal/finance-data-viewer`
role was captured. Opening the campaign changed its status to
`open` and removed the capture form.

![Open campaign with Alice's captured Finance role](../../portfolio/g11/02-open-campaign.png)

### Cancelled campaign

Cancellation changed the status to `cancelled`, preserved the
captured snapshot and removed the mutation controls.

![Cancelled campaign preserving its captured snapshot](../../portfolio/g11/03-cancelled-campaign.png)

### Audit trail

The audit viewer records campaign creation, population, opening
and cancellation, with Leo (`e1004`) identified as the actor.

The first population attempt captured zero items because the
identity had only inherited access. After a direct assignment
was added, the next attempt captured one item.

![Audit trail for campaign creation, population, opening and cancellation](../../portfolio/g11/04-audit-trail.png)

### Evidence limits

Emma's reviewer access was manually confirmed, but a screenshot
of her campaign detail page is not included.

The cancelled campaign screenshot demonstrates snapshot retention.
It does not independently prove that the live Keycloak role mapping
remained unchanged.

## Further reading


- [Governance Portal](../governance-portal.md)
- [Testing](../testing.md)

Previous: [G10 — Segregation of Duties](g10-segregation-of-duties.md) · Next: [G12 — Certification decisions (planned)](../roadmap.md)