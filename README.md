# Enterprise IAM & Access Governance Lab

A hands-on enterprise Identity and Access Management lab built around **Keycloak, OpenID Connect, Flask, RBAC, passkeys, and secure session management**.

The project models the IAM environment of the fictional organization **NovaSecure SA** and is designed to progressively demonstrate authentication, authorization, identity governance, lifecycle automation, segregation of duties, access reviews, and IAM security monitoring.

The first major milestone — the **NovaSecure Employee Portal MVP** — implements end-to-end authentication and role-based access control using Keycloak and Flask.

---

## Current Status

### Employee Portal MVP

Implemented:

* Keycloak identity provider
* PostgreSQL-backed Keycloak deployment
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
* Responsive Employee Portal interface

Future phases will add the IAM Governance Portal, REST APIs, LDAP, Joiner-Mover-Leaver automation, access reviews, segregation-of-duties enforcement, and SIEM monitoring.

---

# Architecture

## Current Employee Portal Authentication Flow

```text
Employee Browser
        |
        v
Flask Employee Portal
http://localhost:5000
        |
        | OpenID Connect
        v
Keycloak
http://localhost:8080
        |
        | Password / Passkey
        v
User Authentication
        |
        v
OIDC Authorization Code
        |
        v
/auth/callback
        |
        v
Authlib Token Validation
        |
        +--> Identity Claims
        |
        +--> Realm Roles
        |
        +--> Client Roles
        |
        v
Flask-Login Session
        |
        v
Application RBAC
        |
        +--> /profile
        +--> /department
        +--> /manager
```

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

* **Keycloak**
* OpenID Connect
* OAuth 2.0 Authorization Code Flow
* WebAuthn / Passkeys
* Realm roles
* Client roles
* Group-based access assignment

## Application

* Python
* Flask
* Authlib
* Flask-Login
* Flask-Session
* Flask-WTF
* CacheLib
* Jinja2

## Infrastructure

* Docker
* Docker Compose
* PostgreSQL

## Planned

* OpenLDAP
* Keycloak Admin REST API
* REST APIs
* ELK / Wazuh
* Automated JML workflows

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

defines the following client roles:

```text
portal-user
profile-viewer
department-viewer
manager-dashboard

hr-data-viewer
finance-data-viewer
it-data-viewer
operations-data-viewer
security-data-viewer
```

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

Users therefore inherit access through organizational group membership.

---

# Employee Portal

The Employee Portal is a Flask application secured by Keycloak using OpenID Connect.

Current protected routes:

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

---

## Department Resources

Department access is determined from the user's Keycloak client roles.

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

The current Employee Portal contains example department resources used to validate authorization behavior.

These resources will later be moved into a service layer and exposed through the REST API.

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

# Authentication

Authentication is delegated entirely to Keycloak.

The Flask application never receives or verifies the user's password or passkey directly.

The flow is:

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

Authlib processes the OIDC response and Flask-Login manages the authenticated application session.

---

# Passkeys / WebAuthn

The NovaSecure realm supports WebAuthn passwordless credentials.

A privileged test identity is used as the passkey pilot account.

The passkey authentication process remains entirely within Keycloak:

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

No WebAuthn private key material is handled by Flask.

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

from the Keycloak access token.

Custom decorators are then used to enforce authorization.

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

---

# Security Controls

The Employee Portal currently implements several security controls.

## OIDC Security

* Authorization Code Flow
* OIDC `state` validation
* ID/access-token validation
* Explicit Keycloak issuer validation
* Exact callback URI
* Exact post-logout redirect URI
* Confidential OIDC client
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

## Authorization Security

* Backend role enforcement
* Realm-role support
* Client-role support
* Custom reusable RBAC decorators
* `403 Forbidden` handling
* Navigation visibility separated from actual authorization

## Logout Security

Logout uses:

```text
POST /logout
```

rather than a state-changing GET request.

The POST request requires a CSRF token.

The logout process:

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

# Test Identities

All accounts and identity data are fictional.

| Username | User         | Department             | Special role                   |
| -------- | ------------ | ---------------------- | ------------------------------ |
| `e1001`  | Alice Martin | Human Resources        | —                              |
| `e1002`  | Marc Dubois  | Finance                | Manager                        |
| `e1003`  | Nadia Rossi  | Security               | Security Analyst               |
| `e1004`  | Leo Bernard  | Information Technology | IAM Operator / Privileged User |
| `e1005`  | Emma Keller  | Security               | IAM Auditor                    |

Passwords are intentionally excluded from source control and documentation.

---

# Authorization Acceptance Tests

## Department access

| User         | Expected department    |
| ------------ | ---------------------- |
| Alice Martin | Human Resources        |
| Marc Dubois  | Finance                |
| Nadia Rossi  | Security               |
| Leo Bernard  | Information Technology |
| Emma Keller  | Security               |

## Manager access

| User         | `/manager`      |
| ------------ | --------------- |
| Alice Martin | `403 Forbidden` |
| Marc Dubois  | Allowed         |
| Nadia Rossi  | `403 Forbidden` |
| Leo Bernard  | `403 Forbidden` |
| Emma Keller  | `403 Forbidden` |

## Authentication state

Unauthenticated access to:

```text
/profile
/department
/manager
```

requires authentication.

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

---

# Project Structure

```text
enterprise-iam-lab/
├── apps/
│   └── employee-portal/
│       ├── app.py
│       ├── config.py
│       ├── requirements.txt
│       │
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── user.py
│       │   ├── routes.py
│       │   └── decorators.py
│       │
│       ├── portal/
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   └── department_data.py
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

## 1. Clone the repository

```bash
git clone <repository-url>
cd enterprise-iam-lab
```

---

## 2. Configure environment variables

Copy the provided example:

```bash
cp .env.example .env
```

Configure the required development values.

Never commit real secrets.

The Employee Portal also requires application-specific environment variables such as:

```text
FLASK_SECRET_KEY
KEYCLOAK_SERVER_URL
KEYCLOAK_REALM
KEYCLOAK_CLIENT_ID
KEYCLOAK_CLIENT_SECRET
FLASK_ENV
```

---

## 3. Start Keycloak and PostgreSQL

```bash
docker compose up -d
```

Keycloak is currently used locally at:

```text
http://localhost:8080
```

The NovaSecure realm and RBAC configuration are documented in:

```text
docs/identity-model.md
```

Current realm provisioning is documented but not yet fully automated.

---

## 4. Create the Employee Portal virtual environment

```bash
cd apps/employee-portal

python3 -m venv .venv
source .venv/bin/activate
```

---

## 5. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 6. Start the Employee Portal

```bash
flask --app app run --port 5000
```

Open:

```text
http://localhost:5000
```

For OIDC testing, consistently use `localhost` rather than mixing `localhost` and `127.0.0.1`.

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

The Flask development server must not be used as a production deployment.

---

# Secret Management

Secrets are stored outside source control.

The repository ignores:

```text
.env
.venv/
flask_session/
.flask_session/
__pycache__/
*.pyc
```

The repository has been checked to confirm that the current Flask secret and Keycloak client secret are absent from both:

* currently tracked files;
* Git commit history.

`.env.example` contains configuration placeholders only.

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

## Phase 2 — Employee Portal API

* [ ] `/api/v1/me`
* [ ] `/api/v1/access`
* [ ] `/api/v1/department`
* [ ] Service layer
* [ ] JSON error handling
* [ ] Bearer-token API authentication

## Phase 3 — IAM Governance Portal

* [ ] Identity search
* [ ] Effective access view
* [ ] Role management
* [ ] Access reviews
* [ ] Audit event viewer
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
* [ ] ELK / Wazuh integration
* [ ] IAM detection rules
* [ ] Privileged-role monitoring
* [ ] Authentication anomaly detection
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

# Project Goals

The final lab is intended to demonstrate practical experience across:

```text
Identity and Access Management
OpenID Connect
OAuth 2.0
Keycloak
RBAC
WebAuthn / Passkeys
Access Governance
Segregation of Duties
Joiner-Mover-Leaver Processes
REST API Security
IAM Monitoring
Incident Investigation
```

The project intentionally progresses from authentication and authorization into full identity lifecycle governance and security monitoring.

---

## Disclaimer

NovaSecure SA, its users, departments, identities, and business data are entirely fictional and exist only for this cybersecurity and IAM training environment.
