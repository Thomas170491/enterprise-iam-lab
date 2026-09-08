"""seed managed employee portal roles

Revision ID: 95c3578daaf8
Revises: ebd443f2cd0e
Create Date: 2026-09-09 00:10:49.831716

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95c3578daaf8'
down_revision = 'ebd443f2cd0e'
branch_labels = None
depends_on = None


def upgrade():
        """
        Seed the managed-role catalogue with Employee Portal roles.
        """
        managed_roles = sa.table(
        "managed_roles",
        sa.column("client_name", sa.String),
        sa.column("role_name", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("risk_level", sa.String),
        sa.column("is_privileged", sa.Boolean),
        sa.column("assignment_mode", sa.String),
        sa.column("requires_approval", sa.Boolean),
        sa.column("requires_review", sa.Boolean),
        )
        
        op.bulk_insert(
        managed_roles,
        [
            {
                "client_name": "employee-portal",
                "role_name": "manager-dashboard",
                "enabled": True,
                "risk_level": "medium",
                "is_privileged": True,
                "assignment_mode": "direct",
                "requires_approval": True,
                "requires_review": True,
            },
            {
                "client_name": "employee-portal",
                "role_name": "hr-data-viewer",
                "enabled": True,
                "risk_level": "high",
                "is_privileged": True,
                "assignment_mode": "direct",
                "requires_approval": True,
                "requires_review": True,
            },
                        {
                "client_name": "employee-portal",
                "role_name": "finance-data-viewer",
                "enabled": True,
                "risk_level": "high",
                "is_privileged": True,
                "assignment_mode": "direct",
                "requires_approval": True,
                "requires_review": True,
            },
            {
                "client_name": "employee-portal",
                "role_name": "it-data-viewer",
                "enabled": True,
                "risk_level": "medium",
                "is_privileged": False,
                "assignment_mode": "direct",
                "requires_approval": False,
                "requires_review": True,
            },
            {
                "client_name": "employee-portal",
                "role_name": "operations-data-viewer",
                "enabled": True,
                "risk_level": "medium",
                "is_privileged": False,
                "assignment_mode": "direct",
                "requires_approval": False,
                "requires_review": True,
            },
            {
                "client_name": "employee-portal",
                "role_name": "security-data-viewer",
                "enabled": True,
                "risk_level": "high",
                "is_privileged": True,
                "assignment_mode": "direct",
                "requires_approval": True,
                "requires_review": True,
            },
        ],
    )

def downgrade():
    """
        Remove the Employee Portal roles inserted by this migration.
        """
    managed_roles = sa.table(
            "managed_roles",
            sa.column("client_name", sa.String),
            sa.column("role_name", sa.String),
        )

    op.execute(
            managed_roles.delete().where(
                managed_roles.c.client_name == "employee-portal",
                managed_roles.c.role_name.in_([
                    "manager-dashboard",
                    "hr-data-viewer",
                    "finance-data-viewer",
                    "it-data-viewer",
                    "operations-data-viewer",
                    "security-data-viewer",
                ]),
            )
        )