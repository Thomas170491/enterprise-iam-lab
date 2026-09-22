# Local setup

[Documentation index](../README.md#start-here)

These steps describe the current local HTTPS lab. They are not a complete automated bootstrap of the realm: Keycloak users, groups, clients, role mappings and administrative permissions must also be configured as described in the [identity model](identity-model.md) and [Governance guide](governance-portal.md).

## Prerequisites

Docker with Compose, Python 3.12 and virtual environments, a local PostgreSQL instance for Governance, and locally trusted TLS certificates for `localhost`.

Clone the repository and configure the infrastructure environment:

```bash
git clone https://github.com/Thomas170491/enterprise-iam-lab.git
cd enterprise-iam-lab
cp .env.example .env
```

Fill the root `.env` with local values for `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD`, `PORTAL_DB`, `PORTAL_DB_USER` and `PORTAL_DB_PASSWORD`. Do not overwrite an existing configured `.env`.

Place your local certificate and private key at `certs/localhost.pem` and `certs/localhost-key.pem`. The certificate must cover `localhost`; its issuing CA must be trusted by the browser and Requests. Certificates and secrets are not shipped in the repository.

```bash
docker compose up -d
```

| Component | Local access |
| --- | --- |
| Keycloak | `https://localhost:8080` (container TLS port 8443) |
| Employee PostgreSQL | `localhost:5433` |
| Governance PostgreSQL | Separately provisioned; the example URI uses `localhost:5432` |

Compose starts `iam-postgres`, `employee-portal-postgres` and `iam-keycloak`. It does not start either Flask application or a Governance PostgreSQL container. Avoid removing persistent database volumes unless intentionally resetting the lab.

## Keycloak application setup

Create/configure realm `novasecure`, clients `employee-portal`, `iam-admin-portal` and `iam-governance-service`, and the documented roles/groups. Browser clients require their own secrets; the service client requires service accounts/client-credentials authentication.

Register exact callback and logout URLs for each browser app: `https://localhost:5000/auth/callback` and `/logged-out` on port 5000 for Employee; the equivalent URLs on port 5001 for Governance. Use `localhost` consistently. Configure the `employee-portal-api` audience for Employee API tokens. See the [Governance permissions](governance-portal.md#service-account-configuration-used-in-the-lab) required for reviewer lookup.

## Employee Portal

From the repository root:

```bash
cd apps/employee-portal
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set `FLASK_SECRET_KEY`, `KEYCLOAK_SERVER_URL=https://localhost:8080`, `KEYCLOAK_REALM=novasecure`, `KEYCLOAK_CLIENT_ID=employee-portal`, its client secret and `KEYCLOAK_API_AUDIENCE=employee-portal-api`. Database credentials are read from the root environment. If needed, set `REQUESTS_CA_BUNDLE` to a CA bundle that trusts your local CA.

```bash
flask --app app db upgrade
flask --app app seed-db
flask --app app run --port 5000 --cert ../../certs/localhost.pem --key ../../certs/localhost-key.pem
```

Open `https://localhost:5000`.

## Governance Portal

In a separate terminal, from the repository root:

```bash
cd apps/governance-portal
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Provision the `governance` database and an application database user on your local PostgreSQL instance first. Set the URI using that user's credentials. This step is independent of the two Compose databases.

| Variable | Purpose |
| --- | --- |
| `FLASK_SECRET_KEY` | Independent random secret for this app |
| `KEYCLOAK_SERVER_URL` | `https://localhost:8080` |
| `KEYCLOAK_REALM` | `novasecure` |
| `KEYCLOAK_CLIENT_ID` | `iam-admin-portal` |
| `KEYCLOAK_CLIENT_SECRET` | Governance browser client secret |
| `KEYCLOAK_SERVICE_CLIENT_ID` | `iam-governance-service` |
| `KEYCLOAK_SERVICE_CLIENT_SECRET` | Service-account client secret |
| `DATABASE_URI` | Governance SQLAlchemy connection URL |
| `REQUESTS_CA_BUNDLE` | CA bundle trusted by Requests; example uses Linux system bundle |

The actual database environment key is **`DATABASE_URI`**, even though one startup error message currently says `DATABASE_URL`.

```bash
flask --app app db upgrade
flask --app app run --port 5001 --cert ../../certs/localhost.pem --key ../../certs/localhost-key.pem
```

Open `https://localhost:5001`. Current application configs require secure session cookies, so use HTTPS. See [testing](testing.md) for commands and [access reviews](guides/g11-access-review-workflows.md#troubleshooting) for the G11 integration fixes.
