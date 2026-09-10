# Enterprise IAM Lab — Identity Model

## 1. Project Objective

The **Enterprise IAM Lab** models an enterprise identity and access management environment for the fictional organization **NovaSecure SA**.

The project is designed to demonstrate:

* Centralized identity management
* OpenID Connect single sign-on
* Role-based access control
* Passkey / WebAuthn authentication
* Multifactor authentication
* Privileged-access controls
* Segregation of duties
* Identity lifecycle management
* Joiner, mover, and leaver automation
* Access reviews and certification
* IAM audit logging and security monitoring

The project is being implemented incrementally. The Employee Portal authentication, RBAC, and REST API are implemented. The Governance Portal implements identity search, effective-access inspection, audited role administration, and Employee Portal SoD enforcement. Lifecycle automation, LDAP integration, approval and access-review workflows, and centralized security monitoring remain later phases.

---

# 2. Fictional Organization

**Organization:** NovaSecure SA

NovaSecure is modeled as a medium-sized organization with the following departments:

* Human Resources
* Finance
* Information Technology
* Security
* Operations

Each employee belongs to a department group that provides baseline access through inherited role mappings.

---

# 3. IAM Architecture

The target architecture is:

```text
HR Identity Source
        ↓
Joiner / Mover / Leaver Automation
        ↓
     OpenLDAP
        ↓
     Keycloak
        ↓
 ┌───────────────┬─────────────────────┐
 │               │                     │
Employee      IAM Governance       Applications /
Portal           Portal                APIs
 │               │
 └───────────────┴───────────────┐
                                 ↓
                           IAM Audit Events
                                 ↓
                            ELK / Wazuh
```

## Current implementation

The currently implemented authentication path is:

```text
Employee Browser
        ↓
Flask Employee Portal
        ↓
OpenID Connect
        ↓
Keycloak
        ↓
Password / Passkey Authentication
        ↓
OIDC Authorization Code
        ↓
Flask Callback
        ↓
Validated Identity + Roles
        ↓
Flask-Login Session
        ↓
Application RBAC
```

---

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

---

# 5. Applications

## 5.1 Employee Portal

Keycloak client:

```text
employee-portal
```

Local development URL:

```text
http://localhost:5000
```

Current functions:

* Authenticate through Keycloak using OIDC
* Authenticate with username/email and password
* Authenticate using registered passkeys
* View personal profile information
* View department resources
* View manager-only resources when authorized
* Enforce client-role-based authorization
* Return `403 Forbidden` for unauthorized access
* Maintain authenticated sessions using Flask-Login
* Use server-side Flask sessions
* Perform coordinated Flask and Keycloak logout
* Protect logout using POST and CSRF validation

### Current protected routes

```text
/profile
/department
/manager
```

The `/manager` route requires:

```text
manager-dashboard
```

The `/department` route derives access from department-specific client roles.

---

## 5.2 IAM Governance Portal

Keycloak client:

```text
iam-admin-portal
```

Status: **Implemented for identity inspection, audited Employee Portal role administration, and SoD enforcement.**

Implemented functions:

* Protected governance access and dashboard RBAC
* Identity search and effective-access inspection
* Keycloak Admin REST API integration using a service account
* Governed Employee Portal role assignment and removal
* PostgreSQL-backed audit events and an audit-log viewer
* Database-backed managed-role catalogue and SoD rules
* SoD decision auditing and specific HTTP 403 rejection messages

Approval workflows, access certification, governance reporting, and privileged-access workflows remain planned. See [Segregation of Duties](#17-segregation-of-duties) for policy details and current limitations.

---

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
| `department-viewer`      | View department information       |
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
department-viewer
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
| `access-reviewer`      | Conduct access reviews               |
| `audit-log-reviewer`     | Review IAM and authentication events |
| `role-manager`         | Manage role assignments              |
| `report-exporter`      | Export governance reports            |

The portal enforces implemented dashboard, identity-viewing, role-management, and audit-review permissions. Roles for planned features do not imply that those workflows are already available.

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
department-viewer
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
department-viewer
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
department-viewer
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
department-viewer
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

Leo is also used as the current passkey / WebAuthn pilot identity.

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
department-viewer
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

---

# 14. Current Authentication Controls

The Employee Portal currently uses:

* OpenID Connect Authorization Code Flow
* Keycloak authentication
* Authlib OIDC client integration
* Flask-Login
* Server-side Flask sessions
* `HttpOnly` session cookies
* `SameSite=Lax`
* Environment-dependent `Secure` cookies
* Exact OIDC callback URIs
* Exact post-logout redirect URIs
* OIDC `state` validation
* Signed-token validation
* Passkey / WebAuthn support
* CSRF-protected POST logout

The development environment currently uses HTTP on localhost.

Production deployment would require HTTPS and:

```text
SESSION_COOKIE_SECURE = True
```

---

# 15. Authorization Model

Authentication answers:

```text
Who is the user?
```

Authorization answers:

```text
What may the authenticated user access?
```

The Employee Portal extracts both realm and client roles from the Keycloak-issued access token.

Application access is enforced using:

```text
Flask-Login @login_required
+
custom realm-role decorators
+
custom client-role decorators
```

Example:

```text
/manager
```

requires:

```text
manager-dashboard
```

Expected behavior:

```text
Marc Dubois → 200 OK
Alice Martin → 403 Forbidden
```

The visibility of navigation links is only a user-interface control.

Authorization is independently enforced by the backend route.

---

# 16. Department Access Model

Department access currently maps Keycloak client roles to application departments.

```text
hr-data-viewer
→ Human Resources

finance-data-viewer
→ Finance

it-data-viewer
→ Information Technology

operations-data-viewer
→ Operations

security-data-viewer
→ Security
```

The Employee Portal currently exposes example department resources for MVP validation.

These resources are temporary application data.

Future versions will derive department membership from authoritative identity attributes and obtain application resources through a dedicated service layer.

---

# 17. Segregation of Duties

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

---

# 18. Joiner Process

Status:

```text
Planned
```

Future joiner automation will:

1. Receive the workforce identity from the authoritative HR source.
2. Assign a unique employee identifier and username.
3. Create or synchronize the directory identity.
4. Add the employee to the correct department group.
5. Assign birthright access.
6. Require secure initial credential setup.
7. Require MFA/passkey enrollment for privileged identities.
8. Record the provisioning event.
9. Send relevant events to the IAM audit pipeline.

---

# 19. Mover Process

Status:

```text
Planned
```

When an employee changes department, the future lifecycle engine will:

1. Detect the organizational change.
2. Remove obsolete department memberships.
3. Remove access inherited from the previous department.
4. Add the new department group.
5. Assign new birthright access.
6. Check for segregation-of-duties conflicts.
7. Review retained privileged access.
8. Require approval when appropriate.
9. Record all access changes.

A major security objective is preventing **access accumulation** when employees change roles.

---

# 20. Leaver Process

Status:

```text
Planned
```

When an employee leaves NovaSecure:

1. Disable the identity.
2. Prevent further authentication.
3. Revoke active sessions.
4. Revoke refresh tokens.
5. Remove privileged access.
6. Remove application access.
7. Preserve required audit records.
8. Record the termination action.

The account may be retained in a disabled state when required for audit or forensic purposes.

---

# 21. Access Reviews

Status:

```text
Planned
```

The IAM Governance Portal will support access certification.

Reviewers will be able to:

* Review user access
* Review privileged roles
* Determine how access was granted
* Approve continued access
* Revoke unnecessary access
* Record certification decisions

Users must not be permitted to approve their own privileged-access requests.

---

# 22. IAM Security Monitoring

Status:

```text
Planned
```

Keycloak, the Governance Portal, and lifecycle automation will eventually send security-relevant events to ELK or Wazuh.

Planned monitored events include:

* Authentication failures
* Successful authentication
* Passkey registration
* Privileged-role assignment
* User disablement
* Department changes
* Role additions and removals
* Access-review decisions
* Unauthorized API requests
* Session-integrity anomalies

The final lab will include a security investigation involving obsolete access retained after an employee transfer.

---

# 23. Current Employee Portal Acceptance Tests

The following tests are currently implemented and validated.

## Authentication

* An employee can authenticate through Keycloak.
* OIDC Authorization Code Flow completes successfully.
* Authenticated identity information is available to Flask.
* A registered passkey can be used for authentication.
* An unauthenticated user is redirected to authentication when accessing protected routes.

## Department authorization

| User         | Expected department    |
| ------------ | ---------------------- |
| Alice Martin | Human Resources        |
| Marc Dubois  | Finance                |
| Nadia Rossi  | Security               |
| Leo Bernard  | Information Technology |
| Emma Keller  | Security               |

## Manager authorization

```text
Marc Dubois
→ /manager
→ access granted
```

```text
Alice Martin
→ /manager
→ 403 Forbidden
```

Equivalent denial applies to other identities without `manager-dashboard`.

## Session and logout security

* Flask-Login maintains authenticated user state.
* Server-side sessions are used.
* Logout uses POST.
* Logout requires a valid CSRF token.
* Missing CSRF token causes the request to be rejected.
* Application logout terminates the local session.
* Keycloak logout terminates the identity-provider session.
* The user is returned only to the explicitly permitted logged-out page.

---

# 24. Future Acceptance Tests

Later project phases will validate:

* An IAM operator can modify identity data.
* An IAM auditor cannot modify identities.
* An IAM auditor can conduct access reviews.
* An IAM operator cannot certify access they administer.
* Governance administrator/auditor role conflicts are rejected; Employee Portal assignment conflicts are already covered in Section 17.
* A transferred employee loses obsolete access.
* A terminated employee cannot authenticate.
* Privileged users are required to use strong authentication.
* Lifecycle events produce audit records.
* IAM security events are visible in the SIEM.
* Unauthorized REST API operations return appropriate `401` or `403` responses.

---

# 25. Implementation Status

## Implemented

* Keycloak + PostgreSQL deployment
* NovaSecure realm
* Realm roles
* Department groups
* Governance groups
* Business-function groups
* Employee Portal OIDC client
* IAM Governance Portal authorization model
* Test identities
* Group-based role inheritance
* Flask Employee Portal
* Authlib OIDC integration
* OIDC Authorization Code Flow
* Flask-Login integration
* Server-side sessions
* Profile view
* Department-based authorization
* Manager RBAC
* Custom authorization decorators
* Custom `403 Forbidden` page
* Passkey / WebAuthn authentication
* Coordinated application and Keycloak logout
* POST logout
* CSRF protection
* Basic responsive Employee Portal UI
* Employee Portal REST API and service layer
* IAM Governance Portal identity search and effective-access inspection
* Keycloak Admin REST API integration
* Audited Employee Portal client-role administration
* PostgreSQL audit events and audit-log viewer
* Managed-role catalogue and Employee Portal SoD enforcement

## Planned

* Governance REST API
* OpenLDAP
* Joiner–Mover–Leaver automation
* Access-review workflows
* Governance administrator/auditor role-conflict controls and approval workflows
* IAM audit-event pipeline
* ELK/Wazuh integration
* Detection rules
* IAM investigation scenario
* Production-style HTTPS deployment
