"""add updated_at to policies

Revision ID: 7a94410433f0
Revises: 0001_initial
Create Date: 2026-06-29 21:31:14.667470
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a94410433f0'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('policies', sa.Column(
        'updated_at',
        sa.DateTime(timezone=True),
        server_default=sa.text('now()'),
        nullable=False,
    ))


def downgrade() -> None:
    op.drop_column('policies', 'updated_at')
