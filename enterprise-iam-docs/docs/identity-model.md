# Identity model

[Documentation index](../README.md#start-here)

This document defines NovaSecure's organizational identity model. Group-derived access is the baseline; temporary direct assignments used in manual tests are not baseline entitlements. Keycloak user UUIDs identify campaign creators, reviewers and captured identities; employee usernames are display identifiers.

The lab currently spells the general department role `departement-viewer`. Role names are exact identifiers. The Governance reviewer role is `access-reviewer` (not the historical typo `acces-reviewer`).

# 2. Fictional Organization

**Organization:** NovaSecure SA

NovaSecure is modeled as a medium-sized organization with the following departments:

* Human Resources
* Finance
* Information Technology
* Security
* Operations

Each employee belongs to a department group that provides baseline access through inherited role mappings.

# 4. Identity Provider

NovaSecure uses **Keycloak** as the current identity provider and authorization server.

Realm:

```text
novasecure
```

Keycloak currently provides:

* User authentication
* OpenID Connect
* Application SSO
* User and group management
* Realm roles
* Client roles
* Password authentication
* WebAuthn / passkeys
* Authentication sessions
* OIDC tokens
* Role information consumed by applications

The Keycloak `master` realm is reserved for server administration.

NovaSecure workforce identities are created in the `novasecure` realm.

# 6. Identity Attributes

NovaSecure identities use stable technical usernames instead of email addresses as permanent identity identifiers.

Example:

```text
Username: e1001
Email: alice.martin@novasecure.local
```

The username remains stable even if the user's email address changes.

## Core identity attributes

Each identity may contain:

```text
employee_id
username
first_name
last_name
email
employment_status
job_title
risk_level
department
```

Current custom Keycloak attributes include:

```text
employee_id
employment_status
job_title
risk_level
```

### Example

```text
employee_id       = E1004
username          = e1004
name              = Leo Bernard
employment_status = active
job_title         = IAM Operator
risk_level        = privileged
department        = Information Technology
```

---

# 7. Department Groups

The current department hierarchy is:

```text
/departments
├── finance
├── hr
├── it
├── operations
└── security
```

Each department group receives the baseline:

```text
employee
```

realm role.

Users also inherit Employee Portal client roles through their department group.

## Department metadata

### Finance

```text
department_code = FIN
department_name = Finance
data_classification = confidential
```

### Human Resources

```text
department_code = HR
department_name = Human Resources
data_classification = restricted
```

### Information Technology

```text
department_code = IT
department_name = Information Technology
data_classification = internal
```

### Operations

```text
department_code = OPS
department_name = Operations
data_classification = internal
```

### Security

```text
department_code = SEC
department_name = Security
data_classification = restricted
```

---

# 8. Governance and Business Groups

NovaSecure separates organizational membership from governance duties.

Current structure:

```text
/governance
├── iam-operators
├── iam-auditors
├── security-analysts
└── privileged-users

/business-functions
└── managers
```

This allows an identity to simultaneously belong to:

* one organizational department;
* zero or more governance groups;
* zero or more business-function groups.

Example:

```text
Leo Bernard
├── /departments/it
├── /governance/iam-operators
└── /governance/privileged-users
```

---

# 9. Realm Roles

Realm roles describe organization-wide responsibilities.

Current roles:

| Realm role         | Purpose                                                 |
| ------------------ | ------------------------------------------------------- |
| `employee`         | Baseline role for active employees                      |
| `manager`          | Identifies employees with management responsibilities   |
| `privileged-user`  | Identifies identities with elevated or sensitive access |
| `iam-operator`     | Identity-management operational role                    |
| `iam-auditor`      | Identity-governance and access-review role              |
| `security-analyst` | Security monitoring and IAM-event review role           |

Realm roles describe the user's organizational or governance function rather than access to one specific application.

---

# 10. Employee Portal Client Roles

The `employee-portal` client currently defines:

| Client role              | Purpose                           |
| ------------------------ | --------------------------------- |
| `portal-user`            | Access the Employee Portal        |
| `profile-viewer`         | View personal profile information |
| `departement-viewer`      | View department information       |
| `manager-dashboard`      | Access manager-only functionality |
| `finance-data-viewer`    | Access Finance resources          |
| `hr-data-viewer`         | Access Human Resources resources  |
| `it-data-viewer`         | Access IT resources               |
| `operations-data-viewer` | Access Operations resources       |
| `security-data-viewer`   | Access Security resources         |

Department permissions are inherited through group membership.

Example:

```text
/departments/hr

Inherited realm role:
employee

Inherited Employee Portal roles:
portal-user
profile-viewer
departement-viewer
hr-data-viewer
```

---

# 11. IAM Governance Portal Client Roles

The `iam-admin-portal` client defines the authorization model for the Governance Portal.

| Client role            | Purpose                              |
| ---------------------- | ------------------------------------ |
| `iam-dashboard-access` | Access the governance application    |
| `identity-viewer`      | View identities                      |
| `identity-manager`     | Modify identity information          |
| `access-reviewer`      | View assigned review campaigns       |
| `access-review-manager` | Create and manage owned review campaigns |
| `audit-log-reviewer`     | Review IAM and authentication events |
| `role-manager`         | Manage role assignments              |
| `report-exporter`      | Export governance reports            |

The portal enforces dashboard, identity-viewing, role-management, audit-viewing and access-review permissions. `identity-manager` and `report-exporter` are catalogue roles; their presence does not mean those future workflows are implemented. Campaign ownership and reviewer assignment are checked in addition to client roles.

---

# 12. Current Test Identities

All identities are fictional.

| Username | Name         | Department             | Job title        | Risk       |
| -------- | ------------ | ---------------------- | ---------------- | ---------- |
| `e1001`  | Alice Martin | Human Resources        | HR Specialist    | Standard   |
| `e1002`  | Marc Dubois  | Finance                | Finance Manager  | Elevated   |
| `e1003`  | Nadia Rossi  | Security               | Security Analyst | Elevated   |
| `e1004`  | Leo Bernard  | Information Technology | IAM Operator     | Privileged |
| `e1005`  | Emma Keller  | Security               | IAM Auditor      | Elevated   |

Passwords are deliberately excluded from project documentation and source control.

---

# 13. Current Group Memberships

## Alice Martin — E1001

```text
/departments/hr
```

Effective realm roles:

```text
employee
```

Effective Employee Portal roles:

```text
portal-user
profile-viewer
departement-viewer
hr-data-viewer
```

---

## Marc Dubois — E1002

```text
/departments/finance
/business-functions/managers
```

Effective realm roles:

```text
employee
manager
```

Effective Employee Portal roles:

```text
portal-user
profile-viewer
departement-viewer
finance-data-viewer
manager-dashboard
```

---

## Nadia Rossi — E1003

```text
/departments/security
/governance/security-analysts
```

Effective realm roles:

```text
employee
security-analyst
```

Effective Employee Portal roles:

```text
portal-user
profile-viewer
departement-viewer
security-data-viewer
```

Effective IAM Governance roles:

```text
iam-dashboard-access
identity-viewer
audit-log-reviewer
```

---

## Leo Bernard — E1004

```text
/departments/it
/governance/iam-operators
/governance/privileged-users
```

Effective realm roles:

```text
employee
iam-operator
privileged-user
```

Effective Employee Portal roles:

```text
portal-user
profile-viewer
departement-viewer
it-data-viewer
```

Effective IAM Governance roles:

```text
iam-dashboard-access
identity-viewer
identity-manager
role-manager
report-exporter
```

For G11, Leo also has `iam-admin-portal/access-review-manager`. This was assigned for campaign management; do not assume `iam-operator` automatically grants it. Leo is also the passkey / WebAuthn pilot identity.

---

## Emma Keller — E1005

```text
/departments/security
/governance/iam-auditors
```

Effective realm roles:

```text
employee
iam-auditor
```

Effective Employee Portal roles:

```text
portal-user
profile-viewer
departement-viewer
security-data-viewer
```

Effective IAM Governance roles:

```text
iam-dashboard-access
identity-viewer
access-reviewer
audit-log-reviewer
report-exporter
```

## Workflow documentation

Application behavior lives in [Employee Portal](employee-portal.md) and [Governance Portal](governance-portal.md). See [security controls](security-controls.md) for authentication, [access reviews](guides/g11-access-review-workflows.md) for G11 and [lifecycle and monitoring](lifecycle-and-monitoring.md) for planned JML processes.

<a id="17-segregation-of-duties"></a>
## Segregation of duties

The detailed policy reference has moved to [segregation-of-duties.md](segregation-of-duties.md). The old numbered anchor is retained for existing links.
