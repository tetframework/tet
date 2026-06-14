"""
Password hashing utilities using passlib.

This module provides functions for securely hashing and verifying
passwords using SHA-256 crypt.

Example
-------

Hashing and verifying passwords::

    from tet.util.crypt import crypt, verify

    # Hash a password
    hashed = crypt("my_secret_password")

    # Verify a password
    if verify("my_secret_password", hashed):
        print("Password is correct!")

Note
----

For SQLAlchemy models, consider using :class:`tet.sqlalchemy.password.UserPasswordMixin`
which integrates this functionality directly into your model.
"""
import passlib.hash

password_hash = passlib.hash.sha256_crypt


def crypt(password):
    """
    Hash a password using SHA-256 crypt.

    :param password: Plaintext password (str or bytes)
    :return: Hashed password string
    """
    if isinstance(password, str):
        password_8bit = password.encode()
    else:
        password_8bit = password

    rv = password_hash.encrypt(password_8bit)
    if not isinstance(rv, str):
        rv = rv.decode()

    return rv


def verify(password, hash):
    """
    Verify a password against a hash.

    :param password: Plaintext password to verify (str or bytes)
    :param hash: Hash to verify against
    :return: True if password matches, False otherwise
    """
    if isinstance(password, str):
        password_8bit = password.encode()
    else:
        password_8bit = password

    return password_hash.verify(password_8bit, hash)
