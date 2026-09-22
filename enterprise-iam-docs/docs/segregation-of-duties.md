# Segregation of duties

[Documentation index](../README.md#start-here)

The Governance Portal evaluates Employee Portal role assignments against enabled segregation-of-duties (SoD) rules before changing access in Keycloak. The managed-role catalogue and rules are stored in PostgreSQL and seeded through Alembic migrations.

## Seeded Lab Policies

| Employee Portal role combination | Decision |
| --- | --- |
| `hr-data-viewer` + `finance-data-viewer` | Deny |
| `finance-data-viewer` + `security-data-viewer` | Requires review |

These are example lab policies, not universal departmental restrictions. The rules apply regardless of which role in the pair is requested.

## Evaluation Behavior

* Unmanaged or disabled requested roles are denied.
* The identity's current effective client roles are resolved through the managed-role catalogue and checked against the requested role.
* Held roles still participate in conflict checks when their catalogue entries are disabled; disabling a catalogue entry does not revoke access in Keycloak.
* Disabled SoD rules are ignored.
* A deny rule takes priority over a review rule.
* A review decision is preserved when later roles have no matching rule.
* If no enabled rule matches, the SoD decision is `allow`.

## Enforcement and Audit Trail

Each completed SoD evaluation records a `sod.evaluate` event containing the human actor, target identity, decision, reason, matching rule ID, and role context.

Both `deny` and `requires_review` block assignment before the Keycloak mutation and before any `role.assign` attempt event. The UI returns HTTP 403 with a specific explanation:

| Decision | User-facing explanation |
| --- | --- |
| Deny | This role combination violates a segregation-of-duties rule. No role was assigned. |
| Requires review | This role assignment requires review. No role was assigned. |

Allowed assignments proceed through the normal `role.assign` attempted and success/failure audit flow. If SoD auditing or the assignment attempt audit fails, assignment stops. Failure to persist the final success audit does not turn an already completed Keycloak assignment into a reported mutation failure.

## Validation

Automated tests cover unmanaged and disabled requested roles, matching deny and review rules, disabled rules, deny priority, held disabled roles, and preservation of a review decision after a later nonmatching role. Service and route tests cover assignment blocking, audit failures, and the specific HTTP 403 explanations.

Manual deny and requires-review checks confirmed that blocked requests produce SoD audit events without granting the requested Keycloak role or producing a subsequent `role.assign` event for the blocked request.

Run the Governance Portal test suite from its application directory with its virtual environment active:

```bash
pytest -q
```

## Current Scope and Limitations

* `requires_review` blocks assignment but does not create an approval request.
* Enforcement covers Employee Portal assignments made through the Governance Portal; direct changes in Keycloak bypass these checks.
* Existing conflicting access is not automatically detected or revoked.
* Governance administrator/auditor role conflicts and prevention of self-certification remain follow-up work.
* Catalogue approval and review metadata does not by itself implement an approval workflow.

---

## Planned Governance Separation

NovaSecure's design separates access administration from access certification.

### IAM Operator

Intended capabilities:

```text
identity-viewer
identity-manager
role-manager
report-exporter
```

The IAM Operator must not automatically receive:

```text
access-reviewer
```

### IAM Auditor

Intended capabilities:

```text
identity-viewer
access-reviewer
audit-log-reviewer
report-exporter
```

The IAM Auditor must not automatically receive:

```text
identity-manager
role-manager
```

This intended separation aims to prevent the same identity from administering access and independently certifying it. Automatic enforcement of Governance role conflicts and self-certification restrictions is not yet implemented.

### Additional planned SoD controls

Future governance rules will detect or reject combinations such as:

```text
iam-role-manager + security-auditor
payroll-creator + payroll-approver
access-requester + access-approver
application-developer + production-approver
```

Status:

```text
Planned — Governance role-conflict enforcement not yet implemented
```

Access review campaigns are documented separately in [G11 — Access review workflows](guides/g11-access-review-workflows.md). They do not turn a blocked SoD request into an approval workflow.
