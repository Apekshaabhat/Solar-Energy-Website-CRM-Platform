"""Add created_by_user_id to customers and leads.

Revision ID: 007_add_created_by_user
Revises: 006_convert_to_admin_sales_roles
Create Date: 2026-11-03 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "007_add_created_by_user"
down_revision: Union[str, Sequence[str], None] = "006_convert_to_admin_sales_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add created_by_user_id to customers table
    op.add_column(
        "customers",
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_customers_created_by_user_id_users"),
            nullable=True,
        ),
    )
    op.create_index("ix_customers_created_by_user_id", "customers", ["created_by_user_id"], unique=False)

    # 2. Add created_by_user_id to leads table
    op.add_column(
        "leads",
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_leads_created_by_user_id_users"),
            nullable=True,
        ),
    )
    op.create_index("ix_leads_created_by_user_id", "leads", ["created_by_user_id"], unique=False)

    # 3. Backfill initial records
    op.execute(
        sa.text("UPDATE leads SET created_by_user_id = assigned_user_id WHERE assigned_user_id IS NOT NULL")
    )
    op.execute(
        sa.text("UPDATE customers SET created_by_user_id = assigned_user_id WHERE assigned_user_id IS NOT NULL")
    )


def downgrade() -> None:
    op.drop_index("ix_leads_created_by_user_id", table_name="leads")
    op.drop_column("leads", "created_by_user_id")
    op.drop_index("ix_customers_created_by_user_id", table_name="customers")
    op.drop_column("customers", "created_by_user_id")

