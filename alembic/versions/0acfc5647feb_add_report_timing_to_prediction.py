"""add report_timing to prediction

Revision ID: 0acfc5647feb
Revises: 4bc52319f6de
Create Date: 2026-07-05 08:00:06.349110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0acfc5647feb'
down_revision: Union[str, Sequence[str], None] = '4bc52319f6de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('prediction', sa.Column('report_timing', sa.String(), nullable=True))
    op.execute("UPDATE prediction SET report_timing = 'UNKNOWN' WHERE report_timing IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('prediction', 'report_timing')
