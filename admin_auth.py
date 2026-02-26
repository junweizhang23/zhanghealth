"""
Admin Authentication Module for Zhang Health.

Replaces the insecure pattern of using FLASK_SECRET_KEY as an admin token.
Uses HMAC-based token generation with a dedicated ADMIN_SECRET.

Usage:
    # Generate a token (run once, store in .env):
    python admin_auth.py generate

    # In API calls:
    curl -H "X-Admin-Token: <token>" http://localhost:5000/api/users
"""

import hashlib
import hmac
import os
import secrets
import time
import warnings
from typing import Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Dedicated admin secret — MUST be different from FLASK_SECRET_KEY
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
if not ADMIN_SECRET:
    ADMIN_SECRET = secrets.token_urlsafe(32)
    warnings.warn(
        "ADMIN_SECRET not set! Using auto-generated key. "
        "Admin tokens will not persist across restarts. "
        "Set ADMIN_SECRET in .env for production.",
        stacklevel=2,
    )

# Token validity period (default: 24 hours)
TOKEN_EXPIRY_SECONDS = int(os.getenv("ADMIN_TOKEN_EXPIRY", str(24 * 60 * 60)))


# ---------------------------------------------------------------------------
# Token Generation & Verification
# ---------------------------------------------------------------------------

def generate_admin_token(expires_in: Optional[int] = None) -> str:
    """
    Generate a time-limited admin token.

    The token format is: <expiry_timestamp>.<hmac_signature>
    This avoids the need for a database or external JWT library.

    Args:
        expires_in: Token validity in seconds (default: TOKEN_EXPIRY_SECONDS)

    Returns:
        A signed token string.
    """
    ttl = expires_in or TOKEN_EXPIRY_SECONDS
    expiry = int(time.time()) + ttl
    payload = str(expiry).encode("utf-8")
    signature = hmac.new(
        ADMIN_SECRET.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    return f"{expiry}.{signature}"


def verify_admin_token(token: str) -> Tuple[bool, str]:
    """
    Verify an admin token.

    Args:
        token: The token string to verify.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is empty.
    """
    if not token:
        return False, "No token provided"

    parts = token.split(".")
    if len(parts) != 2:
        return False, "Invalid token format"

    try:
        expiry = int(parts[0])
    except ValueError:
        return False, "Invalid token format"

    # Check expiry
    if time.time() > expiry:
        return False, "Token expired"

    # Verify HMAC signature
    expected_sig = hmac.new(
        ADMIN_SECRET.encode("utf-8"),
        str(expiry).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(parts[1], expected_sig):
        return False, "Invalid token signature"

    return True, ""


# ---------------------------------------------------------------------------
# Flask Decorator
# ---------------------------------------------------------------------------

def require_admin(f):
    """
    Flask route decorator that requires a valid admin token.

    Usage:
        @app.route("/api/admin-endpoint")
        @require_admin
        def admin_endpoint():
            return jsonify({"status": "ok"})
    """
    from functools import wraps
    from flask import request, jsonify

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        is_valid, error = verify_admin_token(token)
        if not is_valid:
            return jsonify({"error": "Unauthorized", "detail": error}), 401
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "generate":
        token = generate_admin_token()
        print(f"\nGenerated admin token (valid for {TOKEN_EXPIRY_SECONDS // 3600} hours):")
        print(f"  {token}\n")
        print("Usage:")
        print(f'  curl -H "X-Admin-Token: {token}" http://localhost:5000/api/users')
    else:
        print("Usage: python admin_auth.py generate")
