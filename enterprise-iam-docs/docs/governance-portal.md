# Governance Portal

[Documentation index](../README.md#start-here) · [Architecture](../diagrams/iam-governance-portal-architecture.md)

## Responsibilities

The portal runs locally at `https://localhost:5001`. It provides identity search, effective-access inspection, audited Employee Portal role assignment/removal, SoD checks, access-review campaigns and an audit-log viewer.

The human OIDC client is `iam-admin-portal`. The backend obtains client-credentials tokens as `iam-governance-service` for Keycloak Admin API calls. The authenticated human ID and username remain the audit actor.

## Authorization

| Capability | Client role | Additional boundary |
| --- | --- | --- |
| Dashboard | `iam-dashboard-access` | Authenticated session |
| Identity inspection | `identity-viewer` | Backend route checks |
| Role assignment/removal | `role-manager` | Managed-role catalogue and assignment SoD policy |
| Campaign management | `access-review-manager` | Creator owns the campaign |
| Campaign reading as reviewer | `access-reviewer` | Campaign assigned to that user |
| Audit viewer | `audit-log-reviewer` | Read-only audit access |

Role definitions alone do not implement features. Identity editing, report exports and certification decisions remain planned. See [identity model](identity-model.md) for personas and group mappings.

## Role administration and SoD

The enabled managed-role catalogue limits administration scope. Employee Portal assignment requests evaluate current effective roles against database rules before mutation. Both deny and requires-review decisions block the assignment. See [segregation of duties](segregation-of-duties.md) for policies, audit order and failure behavior.

The Admin API service resolves client UUIDs, retrieves identities and role mappings, and performs assignments/removals. Direct mappings and effective mappings serve different purposes: G11 snapshots use direct mappings, while reviewer eligibility and assignment conflict evaluation use effective mappings.

## Data and audit

Governance uses a separate PostgreSQL database configured by `DATABASE_URI`. Its models include `AuditEvent`, `ManagedRole`, `SoDRule`, `AccessReview` and `AccessReviewItem`. Apply the committed migrations with `flask --app app db upgrade`.

The `/audit` page displays recorded events. G11 success events are `access_review.create`, `access_review.populate`, `access_review.open` and `access_review.cancel`. Route error logs contain event/outcome/reason context; they are distinct from durable success audit records. Full structured IAM security-event integration is G15 work.

## Service-account configuration used in the lab

The September walkthrough showed `realm-management/manage-users`, `view-users` and `query-clients` on the service account. These describe the current lab configuration, not a claim that its permissions are minimal for every deployment.

Fine-grained permissions assigned to `iam-governance-service-policy` cover:

| Resource | Scope | Purpose |
| --- | --- | --- |
| `employee-portal` client | View | Resolve and inspect the target client |
| `employee-portal` client | Map-roles | Governed business-role mappings |
| Users | Map-roles | User role mapping operations |
| `iam-admin-portal` client | View | Resolve the client during reviewer eligibility checks |

The last permission was added during G11 manual verification. Scope it to **Specific Clients → iam-admin-portal**, not All Clients. Seeing a client as the console administrator does not prove the service account can query it.

## Access reviews

See [Access reviews — G11](guides/g11-access-review-workflows.md) for routes, state transitions, ownership, reviewer eligibility, direct-role capture and known limits.
