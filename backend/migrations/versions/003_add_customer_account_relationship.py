"""Add explicit customer login account relationship.

Revision ID: 003_customer_account_relationship
Revises: 002_site_survey_project
Create Date: 2026-10-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_customer_account_relationship"
down_revision: Union[str, None] = "002_site_survey_project"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.add_column(sa.Column("account_user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_customers_account_user_id_users",
            "users",
            ["account_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_customers_account_user_id",
            ["account_user_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("customers") as batch_op:
        batch_op.drop_constraint("uq_customers_account_user_id", type_="unique")
        batch_op.drop_constraint("fk_customers_account_user_id_users", type_="foreignkey")
        batch_op.drop_column("account_user_id")
