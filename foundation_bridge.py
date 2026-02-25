"""Foundation Bridge — Imports from the shared foundation repository.

This module provides a single integration point between {PROJECT_NAME}
and the shared foundation repository (git submodule at ./foundation).

Usage:
    from foundation_bridge import (
        get_llm_client,
        get_notification_service,
        get_memory_store,
        get_design_token_css,
    )

See: https://github.com/junweizhang23/foundation
"""
import os
import sys

# Add foundation to Python path
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_FOUNDATION_ROOT = os.path.join(_PROJECT_ROOT, "foundation")

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
        """Get a pre-configured LLM client from foundation."""
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
        """Get a pre-configured notification service from foundation."""
        service = NotificationService()

        email_user = os.getenv("EMAIL_USER")
        email_pass = os.getenv("EMAIL_PASSWORD")
        if email_user and email_pass:
            service.add_channel(f"mailto://{email_user}:{email_pass}@gmail.com")

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


# ─── Memory Store (Cross-Agent Personalization) ─────────────────────────────
try:
    from utils.python.memory_store import MemoryStore

    def get_memory_store(base_dir: str = None) -> "MemoryStore":
        """Get the shared memory store for cross-agent personalization.

        Args:
            base_dir: Override memory directory. Defaults to ~/.zhang_memory/
        """
        return MemoryStore(base_dir=base_dir)

except ImportError:
    def get_memory_store(**kwargs):
        raise ImportError(
            "Foundation memory store not available. "
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
    """Read foundation design token CSS for embedding in templates."""
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
