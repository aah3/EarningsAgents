"""add_sector_to_prediction

Revision ID: ace7fb00fa76
Revises: 670a06f4212d
Create Date: 2026-07-09 19:22:27.189587

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ace7fb00fa76'
down_revision: Union[str, Sequence[str], None] = '670a06f4212d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


import sqlmodel


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('prediction', sa.Column('sector', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('prediction', 'sector')
