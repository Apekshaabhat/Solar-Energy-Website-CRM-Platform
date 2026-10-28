"""Convert internal workforce to Admin and Sales Rep roles.

Revision ID: 006_convert_to_admin_sales_roles
Revises: e31c0a8d4f72
Create Date: 2026-10-26 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "006_convert_to_admin_sales_roles"
down_revision: Union[str, Sequence[str], None] = "e31c0a8d4f72"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Normalize administrator accounts
    op.execute(
        sa.text(
            "UPDATE users SET role = 'Admin' "
            "WHERE LOWER(TRIM(role)) IN ('admin', 'administrator')"
        )
    )

    # 2. Convert internal workforce roles (Manager, Support, Sales Rep variations) to 'Sales Rep'
    op.execute(
        sa.text(
            "UPDATE users SET role = 'Sales Rep' "
            "WHERE LOWER(TRIM(role)) IN ('manager', 'support', 'sales', 'sales_rep', 'sales representative')"
        )
    )

    # 3. For any obsolete customer-login accounts, convert them safely to Sales Rep with Inactive status
    # so they cannot access CRM workforce features without explicit administrative review
    op.execute(
        sa.text(
            "UPDATE users SET role = 'Sales Rep', status = 'Inactive' "
            "WHERE LOWER(TRIM(role)) = 'customer'"
        )
    )


def downgrade() -> None:
    pass
