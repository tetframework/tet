"""
Tests for tet.util.base64 module - Base64 and CrockfordBase32 codecs.
"""

import pytest
from tet.util.base64 import Base64, CrockfordBase32


class TestBase64:
    """Test Base64 codec functionality."""

    def test_encode_string(self):
        """Test encoding strings to base64."""
        result = Base64.encode(b"hello world")
        assert result == b"aGVsbG8gd29ybGQ="

    def test_decode_string(self):
        """Test decoding base64 strings."""
        result = Base64.decode(b"aGVsbG8gd29ybGQ=")
        assert result == b"hello world"

    def test_encode_decode_roundtrip(self):
        """Test encode/decode roundtrip."""
        original = b"The quick brown fox jumps over the lazy dog"
        encoded = Base64.encode(original)
        decoded = Base64.decode(encoded)
        assert decoded == original

    def test_normalize(self):
        """Test that normalize returns the input unchanged."""
        test_string = "test123"
        assert Base64.normalize(test_string) == test_string

    # Lengths around 3/4-byte group boundaries to catch padding leaking in.
    @pytest.mark.parametrize("length", [0, 1, 2, 3, 4, 5, 15, 16, 17, 100])
    def test_generate_characters(self, length):
        """Generated string has the exact length and only alphabet chars."""
        result = Base64.generate_characters(length)
        assert isinstance(result, str)
        assert len(result) == length
        allowed = set(Base64.chars.decode())
        assert set(result) <= allowed  # no '=' padding, only alphabet

    # If the byte count were under-provisioned, the final char would be the
    # zero-padded tail symbol carrying only a few real bits, so it could only
    # take a restricted subset of the alphabet. A full char ranges over all 64.
    @pytest.mark.parametrize("length", [1, 2, 5, 17])
    def test_last_character_is_full_entropy(self, length):
        """The final kept character must carry full bits (whole alphabet)."""
        alphabet = set(Base64.chars.decode())
        last_chars = {Base64.generate_characters(length)[-1] for _ in range(3000)}
        assert last_chars == alphabet

    def test_generate_characters_different(self):
        """Test that generated characters are random."""
        # Two long random strings should virtually never collide.
        first = Base64.generate_characters(32)
        second = Base64.generate_characters(32)
        assert first != second

    def test_empty_encode_decode(self):
        """Test encoding/decoding empty bytes."""
        encoded = Base64.encode(b"")
        assert encoded == b""
        decoded = Base64.decode(encoded)
        assert decoded == b""


class TestCrockfordBase32:
    """Test CrockfordBase32 codec functionality."""

    def test_encode_basic(self):
        """Test basic CrockfordBase32 encoding."""
        # Note: The encode method expects bytes
        result = CrockfordBase32.encode(b"hello")
        # Standard Base32 for "hello" is "NBSWY3DP"
        # Crockford replaces some chars
        assert result == "D1JPRV3F"

    def test_decode_basic(self):
        """Test basic CrockfordBase32 decoding."""
        result = CrockfordBase32.decode("D1JPRV3F")
        assert result == b"hello"

    def test_encode_decode_roundtrip(self):
        """Test encode/decode roundtrip."""
        original = b"The quick brown fox"
        encoded = CrockfordBase32.encode(original)
        decoded = CrockfordBase32.decode(encoded)
        assert decoded == original

    def test_no_padding(self):
        """Test that CrockfordBase32 doesn't use padding."""
        result = CrockfordBase32.encode(b"test")
        assert "=" not in result

    def test_normalize_lowercase(self):
        """Test normalization of lowercase letters."""
        normalized = CrockfordBase32.normalize("abcdefgh")
        assert normalized == "ABCDEFGH"

    def test_normalize_confusing_chars(self):
        """Test normalization of confusing characters O->0, I->1, L->1."""
        normalized = CrockfordBase32.normalize("OIL")
        assert normalized == "011"

    def test_decode_with_normalization(self):
        """Test decoding with automatic normalization."""
        # Use lowercase and confusing chars
        result = CrockfordBase32.decode("d1jprv3f")  # lowercase version
        assert result == b"hello"

    def test_decode_with_confusing_chars(self):
        """Test decoding handles O, I, L confusion."""
        # These should decode to the same thing since they normalize
        encoded = CrockfordBase32.encode(b"test")

        # Replace some chars with confusing equivalents if present
        if "0" in encoded:
            variant = encoded.replace("0", "O")
            assert CrockfordBase32.decode(variant) == b"test"

        if "1" in encoded:
            variant = encoded.replace("1", "I")
            assert CrockfordBase32.decode(variant) == b"test"

    @pytest.mark.parametrize("length", [0, 1, 2, 7, 8, 9, 20, 100])
    def test_generate_characters(self, length):
        """Generated string has the exact length and only alphabet chars."""
        result = CrockfordBase32.generate_characters(length)
        assert isinstance(result, str)
        assert len(result) == length
        assert set(result) <= set(CrockfordBase32.chars)

    @pytest.mark.parametrize("length", [1, 2, 3, 9])
    def test_last_character_is_full_entropy(self, length):
        """The final kept character must carry full bits (whole alphabet)."""
        alphabet = set(CrockfordBase32.chars)
        last_chars = {
            CrockfordBase32.generate_characters(length)[-1] for _ in range(3000)
        }
        assert last_chars == alphabet

    def test_chars_attribute(self):
        """Test the chars attribute contains correct Crockford alphabet."""
        expected = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
        assert CrockfordBase32.chars == expected

    def test_no_confusing_chars_in_encoding(self):
        """Test that encoding never produces O, I, or L."""
        # Encode various strings and check they don't contain confusing chars
        test_strings = [
            b"a",
            b"test",
            b"longer string here",
            b"1234567890",
            b"special!@#$%",
        ]
        for test_str in test_strings:
            encoded = CrockfordBase32.encode(test_str)
            assert "O" not in encoded  # Should use 0 instead
            assert "I" not in encoded  # Should use 1 instead
            assert "L" not in encoded  # Should use 1 instead

    def test_decode_without_normalization(self):
        """Test decoding with normalization disabled."""
        encoded = CrockfordBase32.encode(b"hello")
        # Uppercase should work without normalization
        decoded = CrockfordBase32.decode(encoded, normalize=False)
        assert decoded == b"hello"

    def test_various_lengths(self):
        """Test encoding/decoding various length inputs."""
        for length in [1, 5, 8, 13, 21, 34, 55]:
            original = b"x" * length
            encoded = CrockfordBase32.encode(original)
            decoded = CrockfordBase32.decode(encoded)
            assert decoded == original
            assert "=" not in encoded  # No padding
