"""
Configuration module for Zhang Health.
Loads settings from environment variables (.env file).
"""

import os
import secrets as _secrets
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Flask
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "")
    if not FLASK_SECRET_KEY:
        FLASK_SECRET_KEY = _secrets.token_urlsafe(32)
        import warnings
        warnings.warn(
            "FLASK_SECRET_KEY not set! Using auto-generated key. "
            "Sessions will not persist across restarts. "
            "Set FLASK_SECRET_KEY in .env for production.",
            stacklevel=2,
        )

    # Webhook
    WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "http://localhost:5000")

    # Admin
    ADMIN_PHONE = os.getenv("ADMIN_PHONE", "")

    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    USERS_FILE = os.path.join(DATA_DIR, "users.json")
    LOG_DIR = os.path.join(BASE_DIR, "logs")

    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        missing = []
        if not cls.TWILIO_ACCOUNT_SID:
            missing.append("TWILIO_ACCOUNT_SID")
        if not cls.TWILIO_AUTH_TOKEN:
            missing.append("TWILIO_AUTH_TOKEN")
        if not cls.TWILIO_PHONE_NUMBER:
            missing.append("TWILIO_PHONE_NUMBER")
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please copy .env.example to .env and fill in your credentials."
            )
