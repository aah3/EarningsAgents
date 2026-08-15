"""add fiscal period to prediction

Adds the fiscal reporting period (e.g. Q1 / 2026, rendered "2026Q1" in the UI)
to `prediction` so history can be filtered and sorted by reporting period in
SQL. Existing rows are backfilled by scripts/backfill_fiscal_period.py.

Revision ID: b7c41d29e5aa
Revises: 3197622d2454
Create Date: 2026-08-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b7c41d29e5aa'
down_revision: Union[str, Sequence[str], None] = '3197622d2454'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('prediction', sa.Column('fiscal_quarter', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('prediction', sa.Column('fiscal_year', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_prediction_fiscal_quarter'), 'prediction', ['fiscal_quarter'], unique=False)
    op.create_index(op.f('ix_prediction_fiscal_year'), 'prediction', ['fiscal_year'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_prediction_fiscal_year'), table_name='prediction')
    op.drop_index(op.f('ix_prediction_fiscal_quarter'), table_name='prediction')
    op.drop_column('prediction', 'fiscal_year')
    op.drop_column('prediction', 'fiscal_quarter')
