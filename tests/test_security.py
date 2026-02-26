"""Tests for zhanghealth security modules: admin_auth and data_encryption."""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set test secrets before importing modules
os.environ["ADMIN_SECRET"] = "test_admin_secret_key_for_testing_only"
os.environ["DATA_ENCRYPTION_KEY"] = ""  # Will test with and without

from admin_auth import generate_admin_token, verify_admin_token
from data_encryption import encrypt_field, decrypt_field, is_encrypted


class TestAdminTokenGeneration:
    """Test admin token generation."""

    def test_generate_token_returns_string(self):
        token = generate_admin_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_token_contains_parts(self):
        token = generate_admin_token()
        # Token format: timestamp.signature
        parts = token.split(".")
        assert len(parts) == 2

    def test_tokens_are_unique(self):
        t1 = generate_admin_token()
        time.sleep(1.1)  # Tokens use second-level timestamps
        t2 = generate_admin_token()
        assert t1 != t2

    def test_custom_expiry(self):
        token = generate_admin_token(expires_in=3600)
        assert isinstance(token, str)
        assert len(token) > 0


class TestAdminTokenVerification:
    """Test admin token verification."""

    def test_valid_token_verifies(self):
        token = generate_admin_token(expires_in=3600)
        valid, msg = verify_admin_token(token)
        assert valid is True

    def test_invalid_token_fails(self):
        valid, msg = verify_admin_token("invalid.token")
        assert valid is False

    def test_empty_token_fails(self):
        valid, msg = verify_admin_token("")
        assert valid is False

    def test_tampered_token_fails(self):
        token = generate_admin_token(expires_in=3600)
        parts = token.split(".")
        tampered = parts[0] + ".tampered_signature"
        valid, msg = verify_admin_token(tampered)
        assert valid is False

    def test_expired_token_fails(self):
        token = generate_admin_token(expires_in=1)
        time.sleep(2)
        valid, msg = verify_admin_token(token)
        assert valid is False


class TestDataEncryptionWithoutKey:
    """Test data encryption when no key is set (graceful degradation)."""

    def test_encrypt_returns_original_without_key(self):
        # With empty DATA_ENCRYPTION_KEY, should return original
        os.environ["DATA_ENCRYPTION_KEY"] = ""
        # Re-import to pick up new env
        import importlib
        import data_encryption
        importlib.reload(data_encryption)
        result = data_encryption.encrypt_field("test_data")
        assert result == "test_data"

    def test_decrypt_returns_original_without_key(self):
        os.environ["DATA_ENCRYPTION_KEY"] = ""
        import importlib
        import data_encryption
        importlib.reload(data_encryption)
        result = data_encryption.decrypt_field("test_data")
        assert result == "test_data"


class TestDataEncryptionWithKey:
    """Test data encryption when key is properly set."""

    @pytest.fixture(autouse=True)
    def setup_encryption_key(self):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        os.environ["DATA_ENCRYPTION_KEY"] = key
        import importlib
        import data_encryption
        importlib.reload(data_encryption)
        self.enc_module = data_encryption
        yield
        os.environ["DATA_ENCRYPTION_KEY"] = ""

    def test_encrypt_changes_data(self):
        encrypted = self.enc_module.encrypt_field("sensitive_phone_number")
        assert encrypted != "sensitive_phone_number"

    def test_encrypt_decrypt_roundtrip(self):
        original = "+1-555-123-4567"
        encrypted = self.enc_module.encrypt_field(original)
        decrypted = self.enc_module.decrypt_field(encrypted)
        assert decrypted == original

    def test_is_encrypted_detects_encrypted(self):
        encrypted = self.enc_module.encrypt_field("test")
        assert self.enc_module.is_encrypted(encrypted) is True

    def test_is_encrypted_detects_plain(self):
        assert self.enc_module.is_encrypted("plain_text") is False

    def test_encrypt_empty_string(self):
        encrypted = self.enc_module.encrypt_field("")
        assert encrypted == ""

    def test_encrypt_none_returns_none(self):
        result = self.enc_module.encrypt_field(None)
        assert result is None

    def test_decrypt_none_returns_none(self):
        result = self.enc_module.decrypt_field(None)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
