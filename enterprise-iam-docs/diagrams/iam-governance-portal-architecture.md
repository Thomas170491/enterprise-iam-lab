# IAM Governance Portal Architecture

## High-Level Architecture

```text
                    +----------------------+
                    | Human IAM Users      |
                    | Leo / Emma / Nadia   |
                    +----------+-----------+
                               |
                              OIDC
                               |
                               v
                         +-----------+
                         | Keycloak  |
                         +-----------+
                               |
                               v
                 +----------------------------+
                 |  IAM Governance Portal     |
                 |       Flask :5001          |
                 +----------------------------+
                    |                    |
                    v                    v
              Jinja Frontend       Flask-Smorest API
                    |                    |
                    +---------+----------+
                              |
                              v
                        Service Layer
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
      Identity             Access / SoD        Reviews
      Services              Services            Service
          |                   |                   |
          +-------------------+-------------------+
                              |
                 +------------+-------------+
                 |                          |
                 v                          v
            Audit Service            Keycloak Admin
                 |                       Service
                 v                          |
          Governance DB                    |
          PostgreSQL :5434                 |
            |     |     |                  |
            |     |     |                  |
            v     v     v                  v
         Reviews Audit State       iam-governance-service
                                         |
                                   Client Credentials
                                         |
                                         v
                                Keycloak Admin REST API
                                         |
                                         v
                                      Keycloak