"""
Tests for tet.util.crypt module - Password hashing utilities.
"""
from tet.util.crypt import crypt, password_hash, verify


class TestCrypt:
    """Test password hashing functionality."""

    def test_crypt_string_password(self):
        """Test hashing a string password."""
        hashed = crypt("mypassword")
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != "mypassword"  # Should be hashed, not plain
        # Should be a sha256_crypt hash (starts with $5$)
        assert hashed.startswith("$5$")

    def test_crypt_bytes_password(self):
        """Test hashing a bytes password."""
        hashed = crypt(b"mypassword")
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != "mypassword"
        assert hashed.startswith("$5$")

    def test_verify_correct_string_password(self):
        """Test verifying correct string password."""
        password = "correctpassword"
        hashed = crypt(password)
        assert verify(password, hashed) is True

    def test_verify_correct_bytes_password(self):
        """Test verifying correct bytes password."""
        password = b"correctpassword"
        hashed = crypt(password)
        assert verify(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "correctpassword"
        hashed = crypt(password)
        assert verify("wrongpassword", hashed) is False

    def test_verify_mixed_types(self):
        """Test verifying with mixed string/bytes types."""
        # Hash with string, verify with bytes
        hashed = crypt("mypassword")
        assert verify(b"mypassword", hashed) is True

        # Hash with bytes, verify with string
        hashed = crypt(b"mypassword")
        assert verify("mypassword", hashed) is True

    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (due to salt)."""
        password = "samepassword"
        hash1 = crypt(password)
        hash2 = crypt(password)
        # Hashes should be different due to random salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify(password, hash1) is True
        assert verify(password, hash2) is True

    def test_unicode_password(self):
        """Test hashing Unicode passwords."""
        password = "пароль🔐"
        hashed = crypt(password)
        assert verify(password, hashed) is True
        assert verify("wrongпароль", hashed) is False

    def test_empty_password(self):
        """Test hashing empty password."""
        hashed = crypt("")
        assert hashed is not None
        assert verify("", hashed) is True
        assert verify("notempty", hashed) is False

    def test_long_password(self):
        """Test hashing very long password."""
        password = "x" * 1000
        hashed = crypt(password)
        assert verify(password, hashed) is True
        assert verify("x" * 999, hashed) is False

    def test_special_characters_password(self):
        """Test hashing passwords with special characters."""
        password = "p@$$w0rd!#%&*()[]{}|\\<>?,./;:'\"~`"
        hashed = crypt(password)
        assert verify(password, hashed) is True

    def test_password_hash_is_sha256_crypt(self):
        """Test that password_hash is indeed sha256_crypt."""
        from passlib.hash import sha256_crypt
        assert password_hash is sha256_crypt

    def test_hash_format(self):
        """Test the format of generated hashes."""
        hashed = crypt("test")
        # SHA-256 crypt format: $5$salt$hash
        parts = hashed.split("$")
        assert len(parts) >= 4
        assert parts[0] == ""  # First part is empty before first $
        assert parts[1] == "5"  # 5 indicates SHA-256
        # parts[2] is the salt
        # parts[3] is the hash

    def test_consistent_verification(self):
        """Test that verification is consistent across multiple attempts."""
        password = "consistency_test"
        hashed = crypt(password)

        # Verify multiple times
        for _ in range(5):
            assert verify(password, hashed) is True
            assert verify("wrong", hashed) is False

    def test_bytes_and_string_equivalence(self):
        """Test that bytes and string passwords are treated equivalently."""
        password_str = "testpassword"
        password_bytes = b"testpassword"

        hashed_from_str = crypt(password_str)
        hashed_from_bytes = crypt(password_bytes)

        # Cross-verification should work
        assert verify(password_str, hashed_from_bytes) is True
        assert verify(password_bytes, hashed_from_str) is True
