"""Add user invitations, customer linking, and audit log columns

Revision ID: 004_invitations_customer_audit
Revises: 003_crm_sync_and_activity
Create Date: 2026-10-09 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_invitations_customer_audit"
down_revision: Union[str, None] = "003_crm_sync_and_activity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add customer_id, invitation_token_hash, invitation_expires_at to users
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("invitation_token_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("invitation_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_users_customer_id", ["customer_id"])
        batch_op.create_index("ix_users_invitation_token_hash", ["invitation_token_hash"])
        batch_op.create_foreign_key(
            "fk_users_customer_id_customers",
            "customers",
            ["customer_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 2. Add previous_value and new_value to activities
    with op.batch_alter_table("activities") as batch_op:
        batch_op.add_column(sa.Column("previous_value", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("new_value", sa.Text(), nullable=True))


def downgrade() -> None:
    # 2. Remove columns from activities
    with op.batch_alter_table("activities") as batch_op:
        batch_op.drop_column("new_value")
        batch_op.drop_column("previous_value")

    # 1. Remove columns from users
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_customer_id_customers", type_="foreignkey")
        batch_op.drop_index("ix_users_invitation_token_hash")
        batch_op.drop_index("ix_users_customer_id")
        batch_op.drop_column("invitation_expires_at")
        batch_op.drop_column("invitation_token_hash")
        batch_op.drop_column("customer_id")
