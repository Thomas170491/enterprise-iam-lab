# Security controls and boundaries

[Documentation index](../README.md#start-here)

## Browser authentication and sessions

Keycloak handles passwords and passkeys. Authlib performs the OIDC Authorization Code exchange; the apps use Flask-Login and server-side Flask-Session storage through CacheLib. Browser roles are derived from validated tokens. Registered callback and post-logout URLs must exactly match the application's HTTPS origin.

Both current app configurations set `SESSION_COOKIE_SECURE=True`, `HttpOnly=True` and `SameSite=Lax`. The Employee and Governance applications use distinct cookie names. Tests override selected settings in their isolated fixtures.

State-changing browser forms, including logout and campaign actions, use POST and CSRF tokens. Hiding a navigation link or form is a UI convenience; route decorators and service ownership checks enforce access.

## Employee Portal JWT and Bearer-token validation

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

## Governance boundaries

Human users authenticate through `iam-admin-portal`; administrative requests use the separate `iam-governance-service` client. Audit events attribute actions to the human actor. Keycloak service permissions and application RBAC are separate controls.

Campaign data and their success audit events commit in one database transaction. This guarantee does not extend to distributed atomicity between PostgreSQL and Keycloak for role mutations. See [SoD enforcement](segregation-of-duties.md#enforcement-and-audit-trail).

G11 checks manager ownership and reviewer assignment. Automatic administrator/auditor role-conflict enforcement and self-certification prevention remain follow-up work. Direct Keycloak role changes bypass the Governance Portal's SoD checks.

## Secrets and deployment limits

Keep `.env` files, TLS private keys, session files and raw credentials/tokens outside source control. Use the example environment files only as templates. Trust the local certificate authority in the browser and Python HTTP client; do not disable TLS verification to solve certificate errors.

Local HTTPS does not make this a production deployment. Production work still includes a production WSGI server and reverse proxy, Keycloak production configuration, secrets management, suitable shared session storage, database controls, network boundaries and centralized monitoring. The current Compose command is `start-dev`.

The test-only `employee-portal-cli-test` client uses Direct Access Grants for local Bearer integration testing; it is not the intended production authentication architecture.
