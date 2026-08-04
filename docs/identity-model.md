# Enterprise IAM Lab — Identity Model

## 1. Project objective

Build an enterprise IAM environment that demonstrates:

- Single sign-on with OpenID Connect
- Centralized identity management
- Role-based access control
- Multifactor authentication
- Joiner, mover, and leaver automation
- Segregation-of-duties controls
- Access reviews
- IAM security monitoring

## 2. Fictional organization

Company name: NovaSecure SA

Departments:

- Human Resources
- Finance
- Information Technology
- Security
- Operations

## 3. Applications

### Employee Portal

Available to all employees.

Functions:

- View personal profile
- View department
- View assigned roles
- View manager information

### IAM Administration Portal

Available only to authorized IAM personnel.

Functions:

- View users
- Request role assignments
- Disable accounts
- Review access
- View IAM audit events

## 4. Initial users

| Username | Department | Job title | Employment type |
|---|---|---|---|
| alice.martin | Human Resources | HR Officer | Employee |
| bob.keller | Finance | Finance Analyst | Employee |
| claire.morel | Security | SOC Analyst | Employee |
| david.rossi | Information Technology | IAM Administrator | Employee |
| emma.bernard | Operations | Operations Consultant | Contractor |

## 5. Roles

### Organization roles

- employee
- contractor
- manager

### Application roles

- employee-portal-user
- profile-reader
- team-profile-reader
- iam-user-reader
- iam-user-manager
- iam-role-manager
- access-reviewer
- security-auditor

## 6. Initial role assignments

| User | Roles |
|---|---|
| alice.martin | employee, employee-portal-user, profile-reader |
| bob.keller | employee, employee-portal-user, profile-reader |
| claire.morel | employee, employee-portal-user, profile-reader, security-auditor |
| david.rossi | employee, employee-portal-user, iam-user-manager, iam-role-manager |
| emma.bernard | contractor, employee-portal-user, profile-reader |

## 7. Access rules

- All active employees can access the Employee Portal.
- Contractors receive limited access.
- Only IAM administrators can create, disable, or modify identities.
- Security auditors can view audit events but cannot change users.
- Users must not approve their own privileged-access requests.
- Privileged users must use MFA.
- Disabled users must not be able to authenticate.

## 8. Segregation-of-duties rules

The following combinations are prohibited:

- iam-role-manager + security-auditor
- payroll-creator + payroll-approver
- access-requester + access-approver
- application-developer + production-approver

## 9. Joiner process

When a new employee joins:

1. Create the directory account.
2. Assign a unique username.
3. Add the user to the appropriate department group.
4. Assign birthright access.
5. Require a password change.
6. Require MFA for privileged roles.
7. Record the provisioning event.

## 10. Mover process

When an employee changes department:

1. Remove obsolete department access.
2. Assign the new department's access.
3. Check for segregation-of-duties conflicts.
4. Require approval for privileged access.
5. Record all role changes.

## 11. Leaver process

When an employee leaves:

1. Disable the directory account.
2. Revoke active sessions.
3. Revoke refresh tokens.
4. Remove privileged roles.
5. Prevent further authentication.
6. Preserve audit records.

## 12. Initial acceptance tests

- An employee can access the Employee Portal.
- A contractor receives limited access.
- An employee cannot access the IAM Administration Portal.
- An IAM administrator can access IAM management functions.
- A security auditor can read logs but cannot change users.
- A prohibited role combination is rejected.
- A transferred employee loses obsolete access.
- A terminated employee cannot log in.
- Privileged users must configure MFA.
