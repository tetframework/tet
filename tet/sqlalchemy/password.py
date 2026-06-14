"""
Password hashing mixin for SQLAlchemy user models.

This module provides a mixin class that adds secure password handling
to SQLAlchemy models using bcrypt hashing.

Example
-------

Creating a user model with password support::

    from sqlalchemy import Column, Integer, String
    from sqlalchemy.ext.declarative import declarative_base
    from tet.sqlalchemy.password import UserPasswordMixin

    Base = declarative_base()

    class User(UserPasswordMixin, Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)
        username = Column(String(100), unique=True, nullable=False)

Using the password property::

    user = User(username="john")
    user.password = "secret123"  # Automatically hashed

    # Later, validate password
    if user.validate_password("secret123"):
        print("Password correct!")
"""
import sqlalchemy as sa
from sqlalchemy import orm as orm
from sqlalchemy.ext import declarative

from ..util.crypt import crypt, verify


class UserPasswordMixin(object):
    """
    Mixin that adds password hashing to SQLAlchemy user models.

    Provides a ``password`` property that automatically hashes on set,
    and a :meth:`validate_password` method for verification.
    """

    _password = sa.Column("password", sa.Unicode, nullable=True)

    def _set_password(self, password):
        self._password = crypt(password)

    def _get_password(self):
        """Return the hashed version of the password."""
        return self._password

    def validate_password(self, password):
        """
        Validate a plaintext password against the stored hash.

        :param password: Plaintext password to validate
        :return: True if password matches, False otherwise
        """
        if self._password is None:
            return False

        return verify(password, self._password)

    @declarative.declared_attr
    def password(cls):
        """Password property that hashes on set and returns hash on get."""
        return orm.synonym(
            "_password", descriptor=property(cls._get_password, cls._set_password)
        )
