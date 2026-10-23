"""Merge the customer account and CRM migration branches.

Revision ID: e31c0a8d4f72
Revises: 003_customer_account_relationship, c9f3b4c2991f
Create Date: 2026-10-23 00:00:00.000000

"""
from typing import Sequence, Union


revision: str = "e31c0a8d4f72"
down_revision: Union[str, Sequence[str], None] = (
    "003_customer_account_relationship",
    "c9f3b4c2991f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
