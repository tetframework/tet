"""
Base64 and Crockford Base32 encoding utilities.

This module provides encoding utilities including standard Base64 and
Crockford's Base32, which is human-friendly (avoids ambiguous characters
like 0/O and 1/I/L).

Example
-------

Using standard Base64::

    from tet.util.base64 import Base64

    encoded = Base64.encode(b"hello")
    decoded = Base64.decode(encoded)

    # Generate random Base64 characters
    random_str = Base64.generate_characters(16)

Using Crockford Base32::

    from tet.util.base64 import CrockfordBase32

    encoded = CrockfordBase32.encode(b"hello")
    decoded = CrockfordBase32.decode(encoded)

    # Crockford Base32 is case-insensitive and handles ambiguous chars
    CrockfordBase32.decode("O1L")  # Treated as "011"
"""
import base64
import random
import string

maketrans = bytes.maketrans


class BaseCodec(object):
    """Base class for encoding codecs."""

    @classmethod
    def generate_characters(cls, length):
        """Generate random characters from the codec's character set."""
        randomizer = random.SystemRandom()
        max_num = len(cls.chars) - 1
        return b"".join(
            cls.chars[randomizer.randint(0, max_num)] for i in range(length)
        ).decode()


class Base64(BaseCodec):
    """Standard Base64 encoding."""

    chars = (string.ascii_letters + string.digits + "+/").encode()
    padding = True

    @classmethod
    def encode(cls, string):
        """Encode bytes to Base64."""
        return base64.b64encode(string)

    @classmethod
    def normalize(cls, string):
        """Normalize input (no-op for standard Base64)."""
        return string

    @classmethod
    def decode(cls, string):
        """Decode Base64 to bytes."""
        return base64.b64decode(string)

_std_b32_to_crockford_b32 = maketrans(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567",
    b"0123456789ABCDEFGHJKMNPQRSTVWXYZ"
)

_crockford_b32_to_std_b32 = maketrans(
    b"0OI1L23456789ABCDEFGHJKMNPQRSTVWXYZ",
    b"AABBBCDEFGHIJKLMNOPQRSTUVWXYZ234567"
)

_normalize_crockford_b32 = maketrans(
    b"OIL" + string.ascii_lowercase.encode(),
    b"011" + string.ascii_uppercase.encode()
)

class CrockfordBase32(BaseCodec):
    """
    Crockford's Base32 encoding.

    Human-friendly encoding that avoids ambiguous characters (0/O, 1/I/L).
    Case-insensitive and handles common transcription errors.
    """

    chars = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    padding = False

    @classmethod
    def encode(cls, string, normalize=True, validate=False):
        """Encode bytes to Crockford Base32."""
        if isinstance(string, str):
            string = string.decode()

        return base64.b32encode(string).translate(
            _std_b32_to_crockford_b32, b"="
        ).decode()

    @classmethod
    def decode(cls, string, normalize=True, validate=False):
        """Decode Crockford Base32 to bytes."""
        if normalize:
            string = cls.normalize(string)

        if isinstance(string, str):
            string = string.encode()

        # Ensure the mandatory padding is correct:
        b32 = string.upper()
        b32 += b"=" * ((8 - len(b32) % 8) % 8)
        return base64.b32decode(b32.translate(_crockford_b32_to_std_b32))

    @classmethod
    def normalize(cls, string):
        """Normalize input by handling ambiguous characters (O->0, I/L->1)."""
        if isinstance(string, str):
            string = string.encode()

        string = string.translate(_normalize_crockford_b32)
        return string.decode()
