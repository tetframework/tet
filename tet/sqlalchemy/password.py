import sqlalchemy as sa
from sqlalchemy import orm as orm
from sqlalchemy.ext import declarative

from ..util.crypt import crypt, verify

class UserPasswordMixin(object):
    _password = sa.Column('password', sa.Unicode, nullable=True)

    def _set_password(self, password):
        self._password = crypt(password)

    def _get_password(self):
        """Return the hashed version of the password."""
        return self._password

    def validate_password(self, password):
        if self._password is None:
            return False

        return verify(password, self._password)

    @declarative.declared_attr
    def password(cls):
        return orm.synonym('_password', descriptor=property(cls._get_password,
                                                            cls._set_password))
