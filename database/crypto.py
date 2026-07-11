"""
Fernet-based encrypt/decrypt helpers for user-supplied secrets stored at
rest (currently: UserSettings BYOK provider/API keys).

ENCRYPTION_KEY must be set in the environment - generate one once with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

This module fails fast (raises at import time) if ENCRYPTION_KEY is unset,
so the app refuses to start rather than silently storing/returning broken
data on the first settings write. Never rotate ENCRYPTION_KEY in place -
rotating it makes all previously-encrypted values undecryptable; a
rotation requires a migration that decrypts with the old key and
re-encrypts with the new one.
"""
import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not _ENCRYPTION_KEY:
    raise RuntimeError(
        "ENCRYPTION_KEY environment variable is not set. This key encrypts "
        "user-supplied BYOK API keys (UserSettings.*_api_key) at rest and is "
        "required to start the app. Generate one with "
        "`python -c \"from cryptography.fernet import Fernet; "
        "print(Fernet.generate_key().decode())\"` and set it in your .env "
        "(see .env.example)."
    )

_fernet = Fernet(
    _ENCRYPTION_KEY.encode() if isinstance(_ENCRYPTION_KEY, str) else _ENCRYPTION_KEY
)


def encrypt(value: Optional[str]) -> Optional[str]:
    """Encrypt a plaintext string for storage. None passes through as None."""
    if value is None:
        return None
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: Optional[str]) -> Optional[str]:
    """
    Decrypt a ciphertext string read from storage. None passes through as
    None. If the value isn't valid ciphertext for the current
    ENCRYPTION_KEY (e.g. a legacy plaintext row, or a wrong/rotated key),
    logs a warning and returns None rather than handing back garbage or
    raw ciphertext to callers.
    """
    if value is None:
        return None
    try:
        return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning(
            "Failed to decrypt a stored API key value - it is either legacy "
            "plaintext from before encryption was added, or was encrypted "
            "with a different ENCRYPTION_KEY. Treating it as unset."
        )
        return None
