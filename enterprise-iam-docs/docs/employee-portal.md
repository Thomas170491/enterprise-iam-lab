# Employee Portal

[Documentation index](../README.md#start-here) · [Architecture](../diagrams/employee-portal-architecture.md)

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

`Department` has a one-to-many relationship with `DepartmentResource`.

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

## Database and setup

The Employee Portal stores departments and department resources in its own PostgreSQL database at `localhost:5433`. Keycloak remains the identity and entitlement source. Schema changes use Alembic; `flask --app app seed-db` populates example resource data. See [local setup](local-setup.md), [security controls](security-controls.md) and [testing](testing.md).
