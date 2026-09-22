# Roadmap

[Documentation index](../README.md#start-here)

Follow the [G1–G11 guides](guides/README.md) for implementation and validation details.

## Governance milestones

| Step | Milestone | Status at the G11 documentation checkpoint |
| --- | --- | --- |
| G1 | Scaffold | Implemented |
| G2 | OIDC authentication | Implemented |
| G3 | Governance RBAC | Implemented |
| G4 | Service authentication | Implemented |
| G5 | Keycloak Admin API service | Implemented |
| G6 | Identity search | Implemented |
| G7 | Effective identity access view | Implemented |
| G8 | Audit data model and logging | Implemented |
| G9 | Governed role administration | Implemented |
| G10 | Segregation of Duties | Implemented for managed Employee Portal assignments |
| G11 | Access review workflows | Implemented; manual walkthrough recorded; direct-role-only scope |
| G12 | Certification decisions | Next; also extend capture to inherited/effective access |
| G13 | Audit event viewer | Basic viewer already present; dedicated milestone review remains |
| G14 | Reporting | Planned |
| G15 | Structured IAM security events | Planned; route JSON log messages already present |
| G16 | Security regression suite | Existing tests present; consolidated milestone remains |
| G17 | Final documentation | Planned; documentation maintained throughout |

## G12 scope agreed after manual verification

Add retain/revoke decisions by the assigned reviewer, decision auditing and campaign completion rules. Extend capture beyond direct mappings and design assignment-source tracking before attempting inherited-access remediation. A role may remain effective after its direct mapping is removed. Prevent self-certification and define how changed live access is handled before applying decisions.

These are planned requirements, not current guarantees. An SoD `requires_review` result still blocks role assignment without creating an approval request; that approval workflow is distinct from periodic access certification.

## Employee Portal milestones

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

## Wider enterprise scope

LDAP federation, HR-driven provisioning, automated JML, privileged-access workflows, governance role-conflict enforcement and SIEM investigation scenarios extend beyond the current campaign implementation. See [lifecycle and monitoring](lifecycle-and-monitoring.md).
