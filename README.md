# Enterprise IAM & Access Governance Lab

A hands-on enterprise Identity and Access Management lab built around **Keycloak, OpenID Connect, Flask, PostgreSQL, RBAC, passkeys, REST API security, and access governance**.

The project models the IAM environment of the fictional organization **NovaSecure SA** and is designed to progressively demonstrate authentication, authorization, identity governance, lifecycle automation, segregation of duties, access reviews, privileged-access controls, and IAM security monitoring.

The **NovaSecure Employee Portal** is functionally complete. It implements browser-based OIDC authentication, role-based authorization, database-backed department resources, a protected REST API, stateless Bearer-token authentication, and hardened JWT validation.

Development has now progressed into the **IAM Governance Portal**, which implements protected governance access, identity search, effective-access inspection, PostgreSQL-backed audit events, an audit-log viewer, Keycloak Admin REST API integration, and governed Employee Portal client-role assignment and removal.

---

## Current Status

### Employee Portal — Complete

Implemented:

* Keycloak identity provider
* PostgreSQL-backed Keycloak deployment
* Dedicated PostgreSQL database for the Employee Portal
* NovaSecure realm
* Department and governance group hierarchy
* Realm roles
* Application-specific client roles
* Group-based role inheritance
* OpenID Connect Authorization Code Flow
* Authlib OIDC integration
* Flask-Login session management
* Server-side Flask sessions
* Password authentication
* WebAuthn / passkey authentication
* Department-based authorization
* Manager-only RBAC
* Custom authorization decorators
* Custom `403 Forbidden` handling
* Coordinated Flask + Keycloak logout
* POST-based logout
* CSRF protection
* Secure cookie configuration
* SQLAlchemy data model
* Flask-Migrate database migrations
* Reproducible department/resource seed data
* Service layer for identity and access logic
* REST API under `/api/v1`
* Consistent JSON API error handling
* Browser-session API authentication
* Stateless Bearer-token API authentication
* `joserfc` JWT signature and claim validation
* RS256 algorithm restriction
* Explicit issuer validation
* Expiration validation
* Subject validation
* Dedicated `employee-portal-api` audience validation
* JWKS caching
* JWKS refresh path for Keycloak signing-key rotation
* Granular internal token-validation failure classification
* Bearer API integration test script
* Responsive Employee Portal interface

The **IAM Governance Portal is now under active development**. Identity search, effective-access inspection, audit logging, and governed client-role administration are implemented. Remaining governance work includes access reviews, segregation-of-duties enforcement, reporting, lifecycle automation, privileged-access workflows, and ELK/Wazuh monitoring.

---

# Architecture

- [Employee Portal Architecture](diagrams/employee-portal-architecture.md)
- [IAM Governance Portal Architecture](diagrams/iam-governance-portal-architecture.md)

## Target Architecture

```text
HR Identity Source
        |
        v
Joiner / Mover / Leaver Automation
        |
        v
     OpenLDAP
        |
        v
     Keycloak
        |
        +------------------------+
        |                        |
        v                        v
Employee Portal         IAM Governance Portal
        |                        |
        +------------+-----------+
                     |
                     v
               IAM Audit Events
                     |
                     v
                ELK / Wazuh
```

---

# Technology Stack

## Identity and Authentication

* **Keycloak 26.7.0**
* OpenID Connect
* OAuth 2.0 Authorization Code Flow
* WebAuthn / Passkeys
* Realm roles
* Client roles
* Group-based access assignment
* JWKS
* RS256 JWT signatures
* `joserfc`

## Application

* Python
* Flask
* Authlib
* Flask-Login
* Flask-Session
* Flask-WTF
* CacheLib
* Jinja2
* Requests

## Data Layer

* PostgreSQL 17
* Flask-SQLAlchemy
* SQLAlchemy
* Flask-Migrate
* Psycopg 3

## Infrastructure

* Docker
* Docker Compose
* Dedicated Keycloak PostgreSQL database
* Dedicated Employee Portal PostgreSQL database

## Governance and Administration

Implemented or actively used:

* IAM Governance Portal
* Keycloak Admin REST API
* Service-account authentication for administrative API operations
* Identity search
* Effective access inspection
* Governance RBAC
* PostgreSQL-backed audit events
* Audit-log viewer
* Governed Employee Portal client-role assignment and removal

## Planned

* OpenLDAP
* HR identity source
* Automated JML workflows
* Access reviews
* Governance reporting
* Segregation-of-duties enforcement
* Privileged-access workflows
* ELK / Wazuh

---

# Fictional Organization

The lab models the fictional company:

**NovaSecure SA**

Departments:

* Human Resources
* Finance
* Information Technology
* Security
* Operations

The identity architecture separates:

```text
Department membership
        +
Business functions
        +
Governance responsibilities
```

This allows access to be assigned using group membership rather than direct user-role assignment wherever possible.

---

# Keycloak Group Model

```text
/departments
├── finance
├── hr
├── it
├── operations
└── security

/governance
├── iam-operators
├── iam-auditors
├── security-analysts
└── privileged-users

/business-functions
└── managers
```

Department groups provide baseline Employee Portal access.

Governance groups represent privileged or security-specific responsibilities.

---

# Realm Roles

Organization-wide roles currently include:

```text
employee
manager
privileged-user
iam-operator
iam-auditor
security-analyst
```

Realm roles represent responsibilities that apply across the NovaSecure environment rather than to one specific application.

---

# Employee Portal Roles

The Keycloak client:

```text
employee-portal
```

defines client roles for portal access, profile access, manager access, and department-scoped data access.

```text
portal-user
profile-viewer
manager-dashboard

hr-data-viewer
finance-data-viewer
it-data-viewer
operations-data-viewer
security-data-viewer
```

The current Keycloak lab also contains the department-viewer entitlement used during the Employee Portal authorization build.

Example:

```text
/departments/hr
        |
        +--> employee
        +--> portal-user
        +--> profile-viewer
        +--> department-viewer
        +--> hr-data-viewer
```

Users therefore inherit application access through organizational group membership.

---

# Employee Portal

The Employee Portal is a Flask application secured by Keycloak using OpenID Connect.

Protected HTML routes include:

```text
/profile
/department
/manager
```

## Profile

Authenticated employees can view identity information obtained through the OIDC login flow.

Example information:

```text
Name
Username
Email
OIDC Subject Identifier
```

The stable OIDC `sub` claim is used as the primary authenticated identity identifier inside the application.

---

## Department Resources

Department access is determined from Keycloak client roles and resolved through the service layer against the Employee Portal database.

```text
hr-data-viewer
        -> Human Resources

finance-data-viewer
        -> Finance

it-data-viewer
        -> Information Technology

operations-data-viewer
        -> Operations

security-data-viewer
        -> Security
```

Department resources are no longer hardcoded in the portal route layer. They are stored in PostgreSQL and queried through SQLAlchemy models and the access service.

The data model contains:

```text
Department
    |
    +--> code
    +--> name
    +--> client_role
    |
    +--> DepartmentResource[]
```

A user with no recognized department role receives an authorization failure.

A user with roles for multiple departments triggers a domain-level `DepartmentAccessConflict`, which is returned as an API `409 Conflict` and is retained as a future IAM/SIEM detection scenario.

---

## Manager Dashboard

The Manager Dashboard requires:

```text
manager-dashboard
```

The backend route independently validates the role.

Navigation visibility is therefore only a user-interface convenience and is **not** treated as an authorization control.

Example:

```text
Marc Dubois
/manager
-> 200 OK
```

```text
Alice Martin
/manager
-> 403 Forbidden
```

---

# Employee Portal REST API

The Employee Portal exposes a versioned REST API:

```text
/api/v1
```

Implemented endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/me` | Return the authenticated identity |
| `GET /api/v1/access` | Return realm and Employee Portal client roles |
| `GET /api/v1/department` | Return the authorized department and database-backed resources |

The route layer delegates identity and access logic to reusable services rather than duplicating authorization logic in each endpoint.

## API Authentication Modes

The API supports two authentication modes:

```text
Authenticated Flask session
            OR
Authorization: Bearer <access_token>
```

For session-authenticated API requests, `g.api_user` references the authenticated Flask-Login user.

For Bearer requests, the API validates the token, creates a request-local user object, stores it in `g.api_user`, and discards it when the request ends.

This preserves stateless Bearer authentication.

## API Error Model

API errors are returned as JSON rather than HTML redirects.

Examples:

```json
{
  "error": "authentication_required",
  "message": "Authentication is required."
}
```

```json
{
  "error": "invalid_access_token",
  "message": "The access token is invalid or expired."
}
```

Application-level API handlers provide JSON responses for common API errors such as:

```text
401 Authentication Required
403 Forbidden
404 Not Found
405 Method Not Allowed
```

Domain-specific authorization failures remain more precise, including:

```text
403 department_access_not_found
409 access_conflict
```

---

# Authentication

Authentication is delegated to Keycloak.

The Flask application never receives or verifies the user's password or passkey directly during the browser OIDC flow.

```text
/login
   |
   v
Keycloak Authorization Endpoint
   |
   v
User Authentication
   |
   v
Authorization Code
   |
   v
/auth/callback
   |
   v
Token Exchange
   |
   v
Validated Identity
```

Authlib performs the OIDC protocol exchange and Flask-Login manages the authenticated browser session.

The Employee Portal additionally validates access-token signatures and security-relevant claims with `joserfc` before extracting roles.

---

# Passkeys / WebAuthn

The NovaSecure realm supports WebAuthn/passkey credentials.

A privileged fictional test identity is used as the passkey pilot account.

```text
Employee Portal
      |
      v
Keycloak
      |
      v
WebAuthn / Passkey
      |
      v
Successful OIDC Authentication
      |
      v
Employee Portal
```

No WebAuthn private-key material is handled by Flask.

---

# Authorization

Authentication and authorization are deliberately separated.

```text
Authentication
"Who is this?"
       |
       v
Keycloak + OIDC

Authorization
"What can this identity access?"
       |
       v
Keycloak Roles + Flask RBAC
```

The Employee Portal extracts:

```text
realm_access
resource_access
```

from validated Keycloak access tokens.

Custom decorators and service-layer checks enforce authorization.

Conceptually:

```python
@login_required
@client_role_required("manager-dashboard")
def manager():
    ...
```

An authenticated user without the required role receives:

```text
403 Forbidden
```

The access service also detects inconsistent department authorization, including multiple department-scoped roles on one identity.

---

# JWT and Bearer-Token Security

Bearer-token authentication is validated independently of Flask sessions.

## Signature Verification

The token service:

* restricts accepted JWT algorithms to `RS256`;
* retrieves trusted Keycloak public signing keys from the realm JWKS endpoint;
* verifies the JWT signature before trusting its claims.

## Claim Validation

Bearer API tokens are validated for:

```text
iss  -> expected NovaSecure Keycloak realm
exp  -> token must not be expired
sub  -> token must identify a subject
aud  -> token must be intended for employee-portal-api
```

The dedicated API audience is:

```text
employee-portal-api
```

This prevents the API from accepting a valid Keycloak token that was issued for another resource server.

## JWKS Caching

Keycloak public signing keys are cached in memory to avoid contacting the JWKS endpoint for every Bearer request.

The cache currently uses a five-minute default TTL:

```text
300 seconds
```

The JWKS service also contains a forced-refresh path intended for signing-key rotation scenarios where the cached key set does not contain the token's key ID (`kid`).

## Internal Validation Reasons

Detailed JWT validation failures are classified internally so they can later become structured security telemetry.

Examples include:

```text
malformed_token
bad_signature
invalid_algorithm
invalid_key_id
token_decode_failed
expired_token
missing_expiration
invalid_expiration
missing_subject
missing_issuer
invalid_issuer
missing_audience
invalid_audience
```

The API does **not** expose those detailed reasons to callers. External clients receive a generic `401` response while the application retains the internal reason for logging and future SIEM integration.

Raw access tokens must not be written to application logs.

---

# Security Controls

## OIDC Security

* Authorization Code Flow
* OIDC `state` validation
* ID/access-token processing
* Explicit Keycloak issuer validation
* Exact callback URI
* Exact post-logout redirect URI
* Confidential browser OIDC client
* Client secret stored outside source control

## Session Security

* Flask-Login
* Server-side Flask sessions
* `HttpOnly` session cookies
* `SameSite=Lax`
* Environment-dependent `Secure` cookie behavior
* Dedicated Flask secret key

Development:

```text
SESSION_COOKIE_SECURE = False
```

Production over HTTPS:

```text
SESSION_COOKIE_SECURE = True
```

## API Security

* JSON authentication failures instead of browser redirects
* Stateless Bearer authentication
* RS256 restriction
* JWKS-based signature verification
* Issuer validation
* Expiration validation
* Subject validation
* Dedicated API audience validation
* Generic external token errors
* Granular internal token-error classification
* No raw JWT logging
* `GET`-only read endpoints for the current API surface

## Authorization Security

* Backend role enforcement
* Realm-role support
* Client-role support
* Custom reusable RBAC decorators
* Service-layer authorization logic
* `403 Forbidden` handling
* `409 Conflict` handling for inconsistent department entitlements
* Navigation visibility separated from actual authorization

## Logout Security

Logout uses:

```text
POST /logout
```

rather than a state-changing GET request.

The POST request requires a CSRF token.

```text
Flask-Login logout
        |
        v
Local identity session cleanup
        |
        v
Keycloak OIDC logout
        |
        v
Keycloak SSO session terminated
        |
        v
Validated post-logout redirect
```

---

# Database Model

The Employee Portal has its own PostgreSQL database, separate from the Keycloak database.

Docker exposes the Employee Portal database locally on:

```text
localhost:5433
```

Current application tables include:

```text
departments
department_resources
```

The relationship is:

```text
Department 1 ---- * DepartmentResource
```

Department role mapping is stored with the department record through its `client_role` value.

Database schema changes are managed through Flask-Migrate/Alembic.

Initial department/resource data can be recreated with the seed command:

```bash
flask --app app seed-db
```

---

# Test Identities

All accounts and identity data are fictional.

| Username | User | Department | Special role |
| --- | --- | --- | --- |
| `e1001` | Alice Martin | Human Resources | — |
| `e1002` | Marc Dubois | Finance | Manager |
| `e1003` | Nadia Rossi | Security | Security Analyst |
| `e1004` | Leo Bernard | Information Technology | IAM Operator / Privileged User |
| `e1005` | Emma Keller | Security | IAM Auditor |

Passwords are intentionally excluded from source control and documentation.

---

# Acceptance and Integration Tests

## Department Access

| User | Expected department |
| --- | --- |
| Alice Martin | Human Resources |
| Marc Dubois | Finance |
| Nadia Rossi | Security |
| Leo Bernard | Information Technology |
| Emma Keller | Security |

## Manager Access

| User | `/manager` |
| --- | --- |
| Alice Martin | `403 Forbidden` |
| Marc Dubois | Allowed |
| Nadia Rossi | `403 Forbidden` |
| Leo Bernard | `403 Forbidden` |
| Emma Keller | `403 Forbidden` |

## Authentication State

Unauthenticated access to protected HTML routes requires authentication.

Unauthenticated REST requests return JSON `401` responses instead of redirecting to the login page.

## Passkey

The privileged test identity can:

```text
Register a passkey
        |
        v
Sign out
        |
        v
Authenticate with the passkey
        |
        v
Complete the OIDC flow
```

## CSRF

A valid logout request:

```text
POST /logout
+ valid CSRF token
-> accepted
```

A POST without the CSRF token:

```text
POST /logout
+ missing / invalid CSRF token
-> rejected
```

## Bearer API Integration Test

The repository includes:

```text
apps/employee-portal/scripts/test-bearer-api.py
```

The integration test obtains a real Keycloak access token for the fictional Finance manager identity and validates both successful and failed API authentication paths.

Current successful test set:

```text
PASS: /me -> HTTP 200
PASS: /access -> HTTP 200
PASS: /department -> HTTP 200
PASS: Missing authentication -> HTTP 401
PASS: Malformed Bearer header -> HTTP 401
PASS: Invalid Bearer token -> HTTP 401

Result: 6/6 tests passed
```

A separate negative test also confirmed that a correctly signed Keycloak token without the required `employee-portal-api` audience is rejected with `401 Unauthorized`.

### Test-Only Keycloak Client

Bearer integration testing uses a local test-only client:

```text
employee-portal-cli-test
```

Direct Access Grants are used only to simplify automated local integration testing. This client is **not** part of the intended production architecture and should be disabled or removed when the integration test is not required.

---

# Project Structure

```text
enterprise-iam-lab/
├── apps/
│   └── employee-portal/
│       ├── .env.example
│       ├── app.py
│       ├── config.py
│       ├── extensions.py
│       ├── requirements.txt
│       ├── seed.py
│       │
│       ├── migrations/
│       │
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── routes.py
│       │   └── decorators.py
│       │
│       ├── portal/
│       │   ├── __init__.py
│       │   └── routes.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── decorators.py
│       │   ├── errors.py
│       │   └── routes.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   └── ...
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   ├── identity_service.py
│       │   ├── access_service.py
│       │   ├── exceptions.py
│       │   ├── jwks_service.py
│       │   └── token_service.py
│       │
│       ├── scripts/
│       │   └── test-bearer-api.py
│       │
│       ├── templates/
│       │   ├── base.html
│       │   ├── home.html
│       │   ├── profile.html
│       │   ├── department.html
│       │   ├── manager.html
│       │   ├── access-denied.html
│       │   └── logged-out.html
│       │
│       └── static/
│           └── style.css
│
├── docs/
│   └── identity-model.md
│
├── diagrams/
│
├── portfolio/
│
├── compose.yaml
├── .env.example
├── .gitignore
└── README.md
```

---

# Running the Lab

## Requirements

You will need:

* Docker
* Docker Compose
* Python 3
* Python virtual environments
* A modern browser with WebAuthn support

---

## 1. Clone the Repository

```bash
git clone <repository-url>
cd enterprise-iam-lab
```

---

## 2. Configure Infrastructure Environment Variables

Copy the root example:

```bash
cp .env.example .env
```

The root environment configures the Keycloak and Employee Portal PostgreSQL containers.

Example variable names:

```text
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
KEYCLOAK_ADMIN
KEYCLOAK_ADMIN_PASSWORD
PORTAL_DB
PORTAL_DB_USER
PORTAL_DB_PASSWORD
```

Never commit real secrets.

---

## 3. Start Keycloak and PostgreSQL

```bash
docker compose up -d
```

The compose stack currently starts:

```text
iam-postgres
employee-portal-postgres
iam-keycloak
```

Local endpoints:

```text
Keycloak:                 http://localhost:8080
Employee Portal database: localhost:5433
```

The Keycloak database and Employee Portal database use separate Docker volumes.

Avoid destructive volume removal unless intentionally resetting the lab.

---

## 4. Create the Employee Portal Virtual Environment

```bash
cd apps/employee-portal

python3 -m venv .venv
source .venv/bin/activate
```

---

## 5. Configure Employee Portal Environment Variables

Copy the application example:

```bash
cp .env.example .env
```

Application-specific variables include:

```text
FLASK_SECRET_KEY
FLASK_ENV
KEYCLOAK_SERVER_URL
KEYCLOAK_REALM
KEYCLOAK_CLIENT_ID
KEYCLOAK_CLIENT_SECRET
KEYCLOAK_API_AUDIENCE
```

The expected API audience is:

```text
employee-portal-api
```

Database credentials are loaded from the project-level environment file.

---

## 6. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 7. Apply Database Migrations

```bash
flask --app app db upgrade
```

---

## 8. Seed Department Resources

```bash
flask --app app seed-db
```

---

## 9. Start the Employee Portal

```bash
flask --app app run --port 5000
```

Open:

```text
http://localhost:5000
```

For OIDC testing, consistently use `localhost` rather than mixing `localhost` and `127.0.0.1`.

---

## 10. Run the Bearer API Integration Test

With the Employee Portal and Keycloak running and the test-only Keycloak client configured:

```bash
python3 scripts/test-bearer-api.py
```

The script prompts for the fictional test user's Keycloak password without printing it and does not print the raw access token.

---

# Development Security Notice

This project currently uses:

```text
http://localhost
```

for local development.

This is appropriate only for an isolated development lab.

A production-style deployment would require:

* HTTPS
* TLS certificates
* `SESSION_COOKIE_SECURE=True`
* Production WSGI server
* Reverse proxy
* Hardened Keycloak production configuration
* Secure secrets management
* Persistent production-grade session storage
* Appropriate network segmentation
* Production-grade database controls
* Centralized security logging and monitoring

The Flask development server must not be used as a production deployment.

---

# Secret Management

Secrets are stored outside source control.

The repository ignores runtime secret files and local development artifacts such as:

```text
.env
.venv/
flask_session/
.flask_session/
__pycache__/
*.pyc
```

The root and Employee Portal `.env.example` files contain placeholders or non-secret identifiers only.

Raw passwords, Flask secret keys, Keycloak client secrets, and Bearer tokens must not be committed or logged.

---

# Documentation

Detailed IAM architecture and identity-model documentation:

```text
docs/identity-model.md
```

Portfolio evidence and Keycloak configuration screenshots are stored under:

```text
portfolio/
```

---

# Roadmap

## Phase 1 — Employee Portal

* [x] Keycloak realm
* [x] OIDC client
* [x] Authentication
* [x] Passkeys
* [x] Flask-Login
* [x] Realm/client role extraction
* [x] Custom RBAC decorators
* [x] Department authorization
* [x] Manager authorization
* [x] Secure logout
* [x] CSRF protection
* [x] Responsive interface
* [x] Dedicated Employee Portal PostgreSQL database
* [x] SQLAlchemy data model
* [x] Database migrations
* [x] Reproducible resource seed data

## Phase 2 — Employee Portal API

* [x] `/api/v1/me`
* [x] `/api/v1/access`
* [x] `/api/v1/department`
* [x] Service layer
* [x] JSON error handling
* [x] Browser-session API authentication
* [x] Bearer-token API authentication
* [x] JWT audience validation
* [x] `joserfc` token validation
* [x] JWKS caching
* [x] Signing-key refresh path
* [x] Granular internal JWT validation errors
* [x] Bearer API integration tests

## Phase 3 — IAM Governance Portal

* [x] OIDC authentication
* [x] Governance dashboard RBAC
* [x] Identity search
* [x] Effective access view
* [x] Keycloak Admin REST API integration
* [x] PostgreSQL audit-event persistence
* [x] Audit event viewer
* [x] Governed Employee Portal client-role assignment
* [x] Governed Employee Portal client-role removal
* [x] Role-administration audit trail
* [ ] Access reviews
* [ ] Governance reports
* [ ] Segregation-of-duties enforcement

## Phase 4 — Directory and Lifecycle

* [ ] OpenLDAP
* [ ] HR identity source
* [ ] Joiner automation
* [ ] Mover automation
* [ ] Leaver automation
* [ ] Privileged-access workflows

## Phase 5 — Security Monitoring

* [ ] Keycloak audit pipeline
* [ ] Employee Portal structured security events
* [ ] ELK / Wazuh integration
* [ ] IAM detection rules
* [ ] Privileged-role monitoring
* [ ] Authentication anomaly detection
* [ ] JWT validation failure monitoring
* [ ] IAM investigation scenario

---

# Planned Governance Model

The IAM Governance Portal will separate access administration from access certification.

Example:

```text
IAM Operator
------------
identity-viewer
identity-manager
role-manager
report-exporter


IAM Auditor
-----------
identity-viewer
access-reviewer
audit-log-viewer
report-exporter
```

This is intended to demonstrate enterprise **segregation of duties**.

An IAM operator should not independently certify access they administer.

An IAM auditor should not automatically receive the ability to modify identities or role assignments.

---

# Planned Security Monitoring Scenarios

The Employee Portal already detects several conditions that will later be converted into structured IAM security events.

Examples include:

```text
iam.multiple_department_roles
iam.stale_access_after_department_transfer
iam.sod_violation
iam.privileged_role_assigned
api.authorization_denied
oidc.token_validation_failed
oidc.invalid_audience
oidc.jwks_fetch_failed
iam.session_identity_mismatch
```

A flagship future investigation scenario is a mover event where a Finance employee transfers to Security but accidentally retains the Finance entitlement. The portal detects the conflicting department roles, the event is forwarded to the SIEM, and an analyst correlates the access conflict with the identity lifecycle change before revoking the obsolete entitlement.

---

# Project Goals

The final lab is intended to demonstrate practical experience across:

```text
Identity and Access Management
OpenID Connect
OAuth 2.0
Keycloak
RBAC
WebAuthn / Passkeys
REST API Security
JWT Validation
JWKS
Access Governance
Segregation of Duties
Joiner-Mover-Leaver Processes
Privileged Access
IAM Monitoring
Incident Investigation
```

The project intentionally progresses from authentication and authorization into full identity lifecycle governance and security monitoring.

---

## Disclaimer

NovaSecure SA, its users, departments, identities, and business data are entirely fictional and exist only for this cybersecurity and IAM training environment.