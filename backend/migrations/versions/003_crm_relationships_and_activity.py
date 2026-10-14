"""Add CRM relationships and activity tracking table

Revision ID: 003_crm_relationships_and_activity
Revises: 002_site_survey_project
Create Date: 2026-10-06 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_crm_sync_and_activity"
down_revision: Union[str, None] = "002_site_survey_project"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create activities table
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(length=150), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_activities_customer_id_customers", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_activities_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activities_id", "activities", ["id"], unique=False)
    op.create_index("ix_activities_entity_type", "activities", ["entity_type"], unique=False)
    op.create_index("ix_activities_entity_id", "activities", ["entity_id"], unique=False)
    op.create_index("ix_activities_customer_id", "activities", ["customer_id"], unique=False)
    op.create_index("ix_activities_created_at", "activities", ["created_at"], unique=False)

    # 2. Add source_lead_id to projects
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("source_lead_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_projects_source_lead_id", ["source_lead_id"])
        batch_op.create_foreign_key(
            "fk_projects_source_lead_id_leads",
            "leads",
            ["source_lead_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 3. Add lead_id to site_surveys
    with op.batch_alter_table("site_surveys") as batch_op:
        batch_op.add_column(sa.Column("lead_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_site_surveys_lead_id", ["lead_id"])
        batch_op.create_foreign_key(
            "fk_site_surveys_lead_id_leads",
            "leads",
            ["lead_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    # 3. Remove lead_id from site_surveys
    with op.batch_alter_table("site_surveys") as batch_op:
        batch_op.drop_constraint("fk_site_surveys_lead_id_leads", type_="foreignkey")
        batch_op.drop_index("ix_site_surveys_lead_id")
        batch_op.drop_column("lead_id")

    # 2. Remove source_lead_id from projects
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_source_lead_id_leads", type_="foreignkey")
        batch_op.drop_index("ix_projects_source_lead_id")
        batch_op.drop_column("source_lead_id")

    # 1. Drop activities table
    op.drop_index("ix_activities_created_at", table_name="activities")
    op.drop_index("ix_activities_customer_id", table_name="activities")
    op.drop_index("ix_activities_entity_id", table_name="activities")
    op.drop_index("ix_activities_entity_type", table_name="activities")
    op.drop_index("ix_activities_id", table_name="activities")
    op.drop_table("activities")
