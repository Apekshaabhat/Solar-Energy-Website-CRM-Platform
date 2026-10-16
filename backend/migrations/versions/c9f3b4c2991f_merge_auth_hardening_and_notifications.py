"""merge_auth_hardening_and_notifications

Revision ID: c9f3b4c2991f
Revises: 004_auth_hardening, 005_add_notifications
Create Date: 2026-10-16 12:31:12.872001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9f3b4c2991f'
down_revision: Union[str, None] = ('004_auth_hardening', '005_add_notifications')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
