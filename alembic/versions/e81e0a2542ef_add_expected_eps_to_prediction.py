"""add expected_eps to prediction

Revision ID: e81e0a2542ef
Revises: ace7fb00fa76
Create Date: 2026-07-11 11:04:47.608294

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e81e0a2542ef'
down_revision: Union[str, Sequence[str], None] = 'ace7fb00fa76'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('prediction', sa.Column('expected_eps', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('prediction', 'expected_eps')
