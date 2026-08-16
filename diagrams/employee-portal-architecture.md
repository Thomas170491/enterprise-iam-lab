# Employee Portal Architecture

## High-Level Architecture

```text
                        NovaSecure Employee Portal


                              EMPLOYEES

                    Alice / Marc / Nadia / etc.
                              |
                              | OIDC
                              | Authorization Code Flow
                              v
                         +-----------+
                         | Keycloak  |
                         |   :8080   |
                         +-----------+
                              |
                              | authenticated identity
                              | realm + client roles
                              v
                 +----------------------------+
                 |      Employee Portal       |
                 |     localhost:5000         |
                 +----------------------------+
                      |                  |
                      |                  |
                      v                  v
               Jinja Frontend        REST API
               HTML / Forms         /api/v1/...
                      |                  |
                      +--------+---------+
                               |
                               v
                     +-------------------+
                     |   Service Layer   |
                     +-------------------+
                               |
                  +------------+------------+
                  |                         |
                  v                         v
           Identity Service          Access Service
                  |                         |
                  |                         v
                  |                  Department RBAC
                  |                         |
                  +------------+------------+
                               |
                               v
                    Employee Portal PostgreSQL
                         localhost:5433
                               |
                     +---------+---------+
                     |                   |
                     v                   v
                Departments       Department Resources
```

---

## Browser Authentication Flow

```text
Employee Browser
        |
        | GET /login
        v
Employee Portal
localhost:5000
        |
        | OIDC Authorization Request
        v
Keycloak
localhost:8080
        |
        +--> Password
        |
        +--> Passkey / WebAuthn
        |
        v
Successful Authentication
        |
        v
Authorization Code
        |
        v
/auth/callback
        |
        v
Authlib Token Exchange
        |
        v
Access Token Validation
        |
        +--> RS256 Signature
        +--> Issuer
        +--> Expiration
        +--> Subject
        |
        v
Identity + Role Extraction
        |
        +--> realm_access
        +--> resource_access
        |
        v
Flask-Login
        |
        v
Server-Side Flask Session
        |
        v
Application RBAC
        |
        +--> /profile
        +--> /department
        +--> /manager
```

---

## REST API Authentication Flow

The Employee Portal REST API supports either an authenticated browser
session or a stateless Bearer token.

```text
                         API Request
                              |
                  +-----------+-----------+
                  |                       |
                  v                       v
           Flask Session          Bearer Access Token
                  |                       |
                  |                       v
                  |               JWT Decode / Verify
                  |                       |
                  |                       v
                  |                 JWKS Service
                  |                       |
                  |                Cached KeySet
                  |                       |
                  |                       v
                  |                Claim Validation
                  |                       |
                  |             +---------+---------+
                  |             |         |         |
                  |            iss       exp       sub
                  |                                 |
                  |                                aud
                  |                                 |
                  +---------------+-----------------+
                                  |
                                  v
                              g.api_user
                                  |
                                  v
                            Service Layer
                                  |
                   +--------------+--------------+
                   |              |              |
                   v              v              v
             /api/v1/me    /api/v1/access  /api/v1/department
```

Bearer authentication is stateless. A Bearer token does not create a
Flask-Login session.

---

## JWT Validation Architecture

```text
Bearer Access Token
        |
        v
Token Service
        |
        +--> Restrict algorithm to RS256
        |
        v
JWKS Service
        |
        +--> In-memory JWKS cache
        |
        +--> 300-second default TTL
        |
        +--> forced refresh on unknown kid
        |
        v
Keycloak JWKS Endpoint
        |
        v
Signature Verification
        |
        v
Claim Validation
        |
        +--> exp
        +--> sub
        +--> iss
        +--> aud = employee-portal-api
        |
        v
Validated Claims
        |
        v
Realm + Client Role Extraction
```

Internal token-validation failures are classified using reasons such as:

```text
malformed_token
bad_signature
invalid_algorithm
invalid_key_id
expired_token
missing_subject
invalid_issuer
invalid_audience
```

The API returns generic authentication errors externally and never logs
raw Bearer tokens.

---

## Authorization Flow

```text
Authenticated User
        |
        v
Realm + Client Roles
        |
        +-----------------------------+
        |                             |
        v                             v
HTML Route RBAC                 REST API RBAC
        |                             |
        +-------------+---------------+
                      |
                      v
                Access Service
                      |
                      v
          Match Department Client Role
                      |
            +---------+---------+
            |                   |
            v                   v
       No Match             One Match
            |                   |
            v                   v
       403 Forbidden       Department Data
                                |
                                v
                         PostgreSQL Resources


                    Multiple Matches
                           |
                           v
                DepartmentAccessConflict
                           |
                 +---------+---------+
                 |                   |
                 v                   v
            HTML 409             API 409
                                 access_conflict
```

Example department entitlements:

```text
hr-data-viewer
finance-data-viewer
it-data-viewer
operations-data-viewer
security-data-viewer
```

---

## Manager Authorization Flow

```text
Marc Dubois
    |
    | manager-dashboard
    v
GET /manager
    |
    v
Backend Role Check
    |
    v
200 OK


Alice Martin
    |
    | no manager-dashboard
    v
GET /manager
    |
    v
Backend Role Check
    |
    v
403 Forbidden
```

Navigation visibility is not considered an authorization control.
Authorization is independently enforced by the backend.

---

## Employee Portal Data Architecture

```text
Keycloak
   |
   | Identity
   | Realm Roles
   | Client Roles
   v
Employee Portal
   |
   v
Service Layer
   |
   +-----------------------+
   |                       |
   v                       v
Identity Service       Access Service
                           |
                           v
                 Employee Portal PostgreSQL
                           |
                  +--------+--------+
                  |                 |
                  v                 v
             Department     DepartmentResource
                  |
                  | 1
                  |
                  +-------------------- *
```

Keycloak remains the source of authentication and entitlement data.

The Employee Portal database stores application resource data rather
than duplicating the Keycloak identity store.

---

## Logout Flow

```text
Employee
   |
   | POST /logout
   v
CSRF Validation
   |
   v
Flask-Login Logout
   |
   v
Local Session Cleanup
   |
   v
Keycloak OIDC Logout Endpoint
   |
   v
Keycloak SSO Session Terminated
   |
   v
Validated Post-Logout Redirect
   |
   v
/logged-out
```

---

## Current Security Boundaries

```text
                    +----------------------+
                    |      Keycloak        |
                    | Authentication       |
                    | Password / Passkey   |
                    +----------+-----------+
                               |
                               | OIDC
                               v
                    +----------------------+
                    |   Employee Portal    |
                    | Application RBAC     |
                    +----------+-----------+
                               |
                  +------------+------------+
                  |                         |
                  v                         v
           Browser Session             Bearer API
                  |                         |
           Flask-Login               JWT Validation
                  |                         |
                  +------------+------------+
                               |
                               v
                         Service Layer
                               |
                               v
                      Application Database
```

Key security properties:

```text
Authentication       -> Keycloak
Browser session      -> Flask-Login + Flask-Session
Authorization        -> Backend RBAC + service-layer checks
API authentication   -> Session OR stateless Bearer token
JWT trust            -> RS256 + Keycloak JWKS
API audience         -> employee-portal-api
Application data     -> dedicated PostgreSQL database
Logout mutation      -> POST + CSRF
```