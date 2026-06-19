from tet.security.authentication import (
    TokenMixin,
    MultiFactorAuthenticationMethodMixin,
    TOTPUsedCodeMixin,
    RateLimitAttemptMixin,
)
from tet.sqlalchemy.password import UserPasswordMixin

from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy import orm
from sqlalchemy.orm import declarative_base
from sqlalchemy.schema import MetaData

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)
Base = declarative_base(metadata=metadata)


class User(UserPasswordMixin, Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    email = Column(Text, nullable=False, unique=True)
    name = Column(Text, nullable=False, unique=True)
    display_name = Column(Text, nullable=False, default="")
    is_admin = Column(Boolean, nullable=False, default=False, server_default="false")


class Token(TokenMixin, Base):
    __tablename__ = "token"
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    user = orm.relationship(User, backref="tokens")


class MultiFactorAuthenticationMethod(MultiFactorAuthenticationMethodMixin, Base):
    __tablename__ = "multi_factor_authentication_method"
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    user = orm.relationship(User, backref="multi_factor_authentication_methods")

    # Unique constraint on (user_id, method_type)
    __table_args__ = (
        UniqueConstraint("user_id", "method_type", name="unique_mfa_method_type_per_user"),
    )


class TOTPUsedCode(TOTPUsedCodeMixin, Base):
    __tablename__ = "totp_used_code"
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    __table_args__ = (
        UniqueConstraint("user_id", "time_step", name="uq_totp_used_code_user_time_step"),
        {"prefixes": ["UNLOGGED"]},
    )


class RateLimitAttempt(RateLimitAttemptMixin, Base):
    __tablename__ = "rate_limit_attempt"
    __table_args__ = {"prefixes": ["UNLOGGED"]}


__all__ = ["User", "Token", "Base", "metadata", "TOTPUsedCode", "RateLimitAttempt"]
