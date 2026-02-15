from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Enum, Boolean
from sqlalchemy.dialects.postgresql import JSONB

from tet.security.config import MultiFactorAuthMethodType, UTC


class MultiFactorAuthenticationMethodMixin:
    """
    Mixin to store and manage a user's multi-factor authentication method.

    Attributes:
        id (int): Primary key for the Multi-factor authentication record.
        method_type (MultiFactorAuthMethodType): Enum indicating the type of 2FA method (e.g. TOTP, U2F, etc.).
        data (dict): JSONB field holding method-specific configuration or secret data.
        is_active (bool): Flag indicating if the 2FA method is currently enabled.
        verified (bool): Flag indicating if the 2FA method has been verified for the user.
        created_at (datetime): Time when the record was created (timezone-aware).
        last_used_at (datetime, optional): Timestamp of the most recent use of the 2FA method.
    """

    __tablename__ = "multi_factor_authentication_method"
    id = Column(Integer, primary_key=True)
    method_type = Column(
        Enum(MultiFactorAuthMethodType, values_callable=lambda cls: [e.value for e in cls]),
        nullable=False,
        index=True,
    )
    data = Column(JSONB, nullable=False, default=dict)
    is_active = Column(Boolean, default=False, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(True), default=lambda: datetime.now(UTC))
    last_used_at = Column(DateTime(True), nullable=True)

    def mark_used(self):
        self.last_used_at = datetime.now(UTC)


class TokenMixin:
    """
    Stores long-term tokens for users with creation and optional expiration timestamps.

    User ID foreign key needs to be provided by the application.


    **Attributes:**

    * ``id:`` Primary key for the token.
    * ``secret_hash:`` The SHA-256 hashed secret.
    * ``created_at:`` Timestamp when the token was created.
    * ``expires_at:`` Optional timestamp for token expiration.

    """

    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True)
    secret_hash = Column(String, nullable=False)
    created_at = Column(DateTime(True), default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(True), nullable=True)
