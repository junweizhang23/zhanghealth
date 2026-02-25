"""Foundation Bridge — Imports from the shared foundation repository.

This module provides a single integration point between zhanghealth
and the shared foundation repository (git submodule at ./foundation).

Usage:
    from foundation_bridge import (
        get_llm_client,
        get_notification_service,
        get_design_token_css,
    )

See: https://github.com/junweizhang23/foundation
"""
import os
import sys

# Add foundation to Python path
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_FOUNDATION_ROOT = os.path.join(_PROJECT_ROOT, "foundation")
_FOUNDATION_PYTHON = os.path.join(_FOUNDATION_ROOT, "utils", "python")

if os.path.isdir(_FOUNDATION_ROOT) and _FOUNDATION_ROOT not in sys.path:
    sys.path.insert(0, _FOUNDATION_ROOT)


# ─── LLM Client (via LiteLLM) ───────────────────────────────────────────────
try:
    from utils.python.llm_client import LLMClient

    def get_llm_client(
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> "LLMClient":
        """Get a pre-configured LLM client from foundation.
        Falls back gracefully if foundation is not available.
        """
        return LLMClient(
            model=model or os.getenv("AI_MODEL", "gpt-4.1-mini"),
            temperature=temperature,
            max_tokens=max_tokens,
        )

except ImportError:
    def get_llm_client(**kwargs):
        raise ImportError(
            "Foundation LLM client not available. "
            "Run: git submodule update --init --recursive"
        )


# ─── Notification Service (via Apprise) ─────────────────────────────────────
try:
    from utils.python.notification import NotificationService

    def get_notification_service() -> "NotificationService":
        """Get a pre-configured notification service from foundation.
        Auto-configures channels from environment variables:
        - EMAIL_USER / EMAIL_PASSWORD → Email notifications
        - TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID → Telegram notifications
        - TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM → SMS notifications
        """
        service = NotificationService()

        # Auto-configure email if available
        email_user = os.getenv("EMAIL_USER")
        email_pass = os.getenv("EMAIL_PASSWORD")
        if email_user and email_pass:
            service.add_channel(f"mailto://{email_user}:{email_pass}@gmail.com")

        # Auto-configure Telegram if available
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat = os.getenv("TELEGRAM_CHAT_ID")
        if telegram_token and telegram_chat:
            service.add_channel(f"tgram://{telegram_token}/{telegram_chat}")

        return service

except ImportError:
    def get_notification_service(**kwargs):
        raise ImportError(
            "Foundation notification service not available. "
            "Run: git submodule update --init --recursive"
        )


# ─── Auth Utilities ──────────────────────────────────────────────────────────
try:
    from utils.python.auth import create_token, verify_token, has_agent_access, FamilyRole
except ImportError:
    create_token = None
    verify_token = None
    has_agent_access = None
    FamilyRole = None


# ─── PDF Toolkit ─────────────────────────────────────────────────────────────
try:
    from utils.python.pdf_toolkit import PDFToolkit

    def get_pdf_toolkit() -> "PDFToolkit":
        """Get the foundation PDF toolkit for local PDF processing."""
        return PDFToolkit()

except ImportError:
    def get_pdf_toolkit():
        raise ImportError(
            "Foundation PDF toolkit not available. "
            "Install: pip install PyMuPDF Pillow"
        )


# ─── Design Tokens ──────────────────────────────────────────────────────────
FOUNDATION_CSS_DIR = os.path.join(_FOUNDATION_ROOT, "design", "tokens")
APPLE_MINIMAL_CSS = os.path.join(FOUNDATION_CSS_DIR, "apple-minimal.css")
CLAUDE_WARM_CSS = os.path.join(FOUNDATION_CSS_DIR, "claude-warm.css")


def get_design_token_css(theme: str = "apple-minimal") -> str:
    """Read foundation design token CSS for embedding in templates.
    Args:
        theme: 'apple-minimal' or 'claude-warm'
    Returns:
        CSS content string, or empty string if not available
    """
    css_file = APPLE_MINIMAL_CSS if theme == "apple-minimal" else CLAUDE_WARM_CSS
    try:
        with open(css_file, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""


# ─── Schema Paths ────────────────────────────────────────────────────────────
SCHEMAS_DIR = os.path.join(_FOUNDATION_ROOT, "schemas")
HEALTH_RECORD_SCHEMA = os.path.join(SCHEMAS_DIR, "health-record.schema.json")
FINANCIAL_RECORD_SCHEMA = os.path.join(SCHEMAS_DIR, "financial-record.schema.json")
MEMORY_SCHEMA = os.path.join(SCHEMAS_DIR, "memory.schema.json")
