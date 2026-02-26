"""
Data Encryption Module for Zhang Health.

Provides field-level encryption for sensitive data (phone numbers, health readings)
stored in JSON files. Uses Fernet symmetric encryption from the cryptography library.

The encryption key is derived from an environment variable (DATA_ENCRYPTION_KEY).
If not set, the module operates in passthrough mode with a warning.

Usage:
    from data_encryption import encrypt_field, decrypt_field

    encrypted = encrypt_field("+12065551234")
    original  = decrypt_field(encrypted)
"""

import base64
import hashlib
import os
import warnings
from typing import Optional

# Try to import cryptography; fall back to base64 obfuscation if unavailable
try:
    from cryptography.fernet import Fernet, InvalidToken
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    InvalidToken = Exception


# ---------------------------------------------------------------------------
# Key Management
# ---------------------------------------------------------------------------

_ENCRYPTION_KEY_ENV = "DATA_ENCRYPTION_KEY"
_raw_key = os.getenv(_ENCRYPTION_KEY_ENV, "")

if HAS_CRYPTO and _raw_key:
    # Derive a valid Fernet key from the user-provided secret
    # (Fernet requires a 32-byte URL-safe base64-encoded key)
    _derived = hashlib.sha256(_raw_key.encode("utf-8")).digest()
    _fernet_key = base64.urlsafe_b64encode(_derived)
    _fernet = Fernet(_fernet_key)
    ENCRYPTION_ENABLED = True
elif HAS_CRYPTO and not _raw_key:
    _fernet = None
    ENCRYPTION_ENABLED = False
    warnings.warn(
        f"{_ENCRYPTION_KEY_ENV} not set. Sensitive data will be stored in plain text. "
        f"Set {_ENCRYPTION_KEY_ENV} in .env for production.",
        stacklevel=2,
    )
else:
    _fernet = None
    ENCRYPTION_ENABLED = False
    warnings.warn(
        "cryptography package not installed. Sensitive data will be stored in plain text. "
        "Install with: pip install cryptography",
        stacklevel=2,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def encrypt_field(value: str) -> str:
    """
    Encrypt a string value for storage.

    If encryption is enabled, returns a Fernet-encrypted base64 string
    prefixed with 'enc:' for identification.
    If encryption is disabled, returns the original value unchanged.
    """
    if not value or not ENCRYPTION_ENABLED or not _fernet:
        return value
    encrypted = _fernet.encrypt(value.encode("utf-8"))
    return f"enc:{encrypted.decode('utf-8')}"


def decrypt_field(value: str) -> str:
    """
    Decrypt a previously encrypted field value.

    If the value starts with 'enc:', it is decrypted.
    Otherwise, it is returned unchanged (backward compatibility with
    existing plain-text data).
    """
    if not value or not value.startswith("enc:"):
        return value
    if not ENCRYPTION_ENABLED or not _fernet:
        warnings.warn(
            "Encrypted data found but encryption is not enabled. "
            "Cannot decrypt. Returning raw value.",
            stacklevel=2,
        )
        return value
    try:
        encrypted_bytes = value[4:].encode("utf-8")
        return _fernet.decrypt(encrypted_bytes).decode("utf-8")
    except (InvalidToken, Exception) as e:
        warnings.warn(f"Decryption failed: {e}. Returning raw value.", stacklevel=2)
        return value


def is_encrypted(value: str) -> bool:
    """Check if a value is encrypted (has the 'enc:' prefix)."""
    return isinstance(value, str) and value.startswith("enc:")


def generate_key() -> str:
    """Generate a new random encryption key suitable for DATA_ENCRYPTION_KEY."""
    import secrets
    return secrets.token_urlsafe(32)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "generate-key":
        key = generate_key()
        print(f"\nGenerated encryption key:")
        print(f"  {key}\n")
        print(f"Add to your .env file:")
        print(f"  {_ENCRYPTION_KEY_ENV}={key}")
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        print(f"Encryption enabled: {ENCRYPTION_ENABLED}")
        print(f"Cryptography library: {'installed' if HAS_CRYPTO else 'NOT installed'}")
        print(f"Key configured: {'yes' if _raw_key else 'NO'}")
    else:
        print("Usage:")
        print("  python data_encryption.py generate-key   # Generate a new encryption key")
        print("  python data_encryption.py status          # Check encryption status")
