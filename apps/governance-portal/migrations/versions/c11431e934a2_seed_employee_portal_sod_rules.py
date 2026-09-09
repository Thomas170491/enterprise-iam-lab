"""seed employee portal sod rules

Revision ID: c11431e934a2
Revises: 95c3578daaf8
Create Date: 2026-09-09 15:30:17.523135

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c11431e934a2'
down_revision = '95c3578daaf8'
branch_labels = None
depends_on = None


def upgrade():
    """
    Seed example Employee Portal segregation-of-duties rules.
    """
    connection = op.get_bind()

    managed_roles = sa.table(
        "managed_roles",
        sa.column("id", sa.Integer),
        sa.column("client_name", sa.String),
        sa.column("role_name", sa.String),
    )

    role_ids = dict(
        connection.execute(
            sa.select(
                managed_roles.c.role_name,
                managed_roles.c.id,
            ).where(
                managed_roles.c.client_name == "employee-portal",
                managed_roles.c.role_name.in_([
                    "hr-data-viewer",
                    "finance-data-viewer",
                    "security-data-viewer",
                ]),
            )
        ).tuples().all()
    )
    
    required_roles = {
        "hr-data-viewer",
        "finance-data-viewer",
        "security-data-viewer",
    }

    missing_roles = required_roles - set(role_ids)

    if missing_roles:
        raise RuntimeError(
            "Cannot seed SoD rules; missing managed roles: "
            + ", ".join(sorted(missing_roles))
        )
    
    hr_finance_ids = sorted([
        role_ids["hr-data-viewer"],
        role_ids["finance-data-viewer"],
    ])

    finance_security_ids = sorted([
        role_ids["finance-data-viewer"],
        role_ids["security-data-viewer"],
    ])
    
    sod_rules = sa.table(
        "sod_rules",
        sa.column("name", sa.String),
        sa.column("first_role_id", sa.Integer),
        sa.column("second_role_id", sa.Integer),
        sa.column("outcome", sa.String),
        sa.column("enabled", sa.Boolean),
    )

    op.bulk_insert(
        sod_rules,
        [
            {
                "name": "employee-portal-hr-finance-deny",
                "first_role_id": hr_finance_ids[0],
                "second_role_id": hr_finance_ids[1],
                "outcome": "deny",
                "enabled": True,
            },
            {
                "name": "employee-portal-finance-security-review",
                "first_role_id": finance_security_ids[0],
                "second_role_id": finance_security_ids[1],
                "outcome": "requires_review",
                "enabled": True,
            },
        ],
    )

def downgrade():
    """
    Remove the two Employee Portal SoD rules seeded by this migration.
    """
    sod_rules = sa.table(
        "sod_rules",
        sa.column("name", sa.String),
    )

    op.execute(
        sod_rules.delete().where(
            sod_rules.c.name.in_([
                "employee-portal-hr-finance-deny",
                "employee-portal-finance-security-review",
            ])
        )
    )
