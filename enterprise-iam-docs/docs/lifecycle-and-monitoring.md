# Lifecycle and monitoring — planned

[Documentation index](../README.md#start-here)

This is target behavior, not implemented automation. Keycloak and the Flask portals currently provide the identity and governance foundation.

## Joiner process

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

## Mover process

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

## Leaver process

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

## IAM security monitoring

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

## Planned investigation scenarios

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
