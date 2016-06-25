import sqlalchemy as sa
from sqlalchemy import orm as orm
from sqlalchemy.ext import declarative

from ..util.crypt import crypt, verify

class UserPasswordMixin(object):
    _password = None

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, password):
        self._password = crypt(password)

    def validate_password(self, password):
        if self._password is None:
            return False

        return verify(password, self._password)
