"""encrypt user settings api keys

Revision ID: a87ea9fce36f
Revises: e81e0a2542ef
Create Date: 2026-07-11 12:21:33.894683

Phase 0 security hardening: UserSettings.*_api_key columns move from
plaintext to Fernet-encrypted values (see database/crypto.py), applied
going forward by the API's GET/POST /earnings/settings handlers and the
get_pipeline_for_user / analyze_ticker_task code paths.

This migration does NOT attempt to encrypt existing plaintext values in
SQL - Fernet encryption requires the application's ENCRYPTION_KEY and a
Python cryptography call, neither of which is available/appropriate to
run from a raw SQL migration. Since this is pre-beta (no real user data
to preserve), the safe option is to null out any existing key values so
the app never returns/uses a plaintext value as if it were ciphertext.
Affected users (if any, in dev/local DBs) will need to re-enter their
BYOK API keys in Settings after this migration runs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a87ea9fce36f'
down_revision: Union[str, Sequence[str], None] = 'e81e0a2542ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_KEY_COLUMNS = [
    "gemini_api_key",
    "openai_api_key",
    "anthropic_api_key",
    "newsapi_api_key",
    "alphavantage_api_key",
    "earningsapi_api_key",
]


def upgrade() -> None:
    """Null out any existing plaintext API key values.

    Pre-beta: no real user data to preserve, so we don't attempt to
    encrypt in place. Any existing BYOK keys must be re-entered by the
    user after this migration.
    """
    conn = op.get_bind()
    set_clause = ", ".join(f"{col} = NULL" for col in _KEY_COLUMNS)
    conn.execute(sa.text(f"UPDATE user_settings SET {set_clause}"))


def downgrade() -> None:
    """No-op: the plaintext values nulled out by upgrade() cannot be
    recovered (they were never captured by this migration)."""
    pass
