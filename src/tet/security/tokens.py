import dataclasses
import hashlib
import logging
import secrets
import typing as tp

from datetime import datetime, timedelta

import jwt
from pyramid.request import Request
from pyramid_di import RequestScopedBaseService, autowired
from sqlalchemy.orm import Session
from sqlalchemy.sql import delete

from tet.security.config import JWTRegisteredClaims, UTC, TOKEN_ID_BYTE_LENGTH

logger = logging.getLogger(__name__)


class TetTokenService(RequestScopedBaseService):
    db_session: Session = autowired(Session)

    def __init__(self, request: Request):
        super().__init__(request=request)
        self.project_prefix: str = self.registry.tet_auth_project_prefix
        self.long_term_token_model: tp.Any = self.registry.tet_auth_long_term_token_model
        self.long_term_token_cookie_name: str = self.registry.tet_auth_long_term_token_cookie_name
        self.user_id_column: str = self.registry.tet_auth_user_id_column
        self.jwt_expiration_mins: int = self.registry.tet_auth_jwt_expiration_mins
        self.jwt_algorithm: str = self.registry.tet_auth_jwt_algorithm
        self.jwt_claims: JWTRegisteredClaims = self.registry.tet_auth_jwt_claims

    def create_long_term_token(
        self, *, user_id: tp.Any, project_prefix: str, expire_timestamp: tp.Optional[datetime] = None
    ) -> str:
        """
        Generates a long-term token for a user with a project-specific prefix and stores it in the database.
        Args:
            user_id: The ID of the user for whom the token is generated.
            project_prefix: A prefix indicating the project this token is for.
            expire_timestamp: (Optional) Expiration timestamp for the token.

        Returns:
            The plaintext long-term token with the project-specific prefix.
        """
        if not expire_timestamp:
            expire_timestamp = datetime.now(UTC) + timedelta(hours=12)

        secret = secrets.token_bytes(32)
        hashed_secret = hashlib.sha256(secret).digest()

        stored_token = self.long_term_token_model(
            secret_hash=hashed_secret.hex(),
            created_at=datetime.now(UTC),
            expires_at=expire_timestamp,
        )
        setattr(stored_token, self.user_id_column, user_id)

        self.db_session.add(stored_token)
        self.db_session.flush()

        token_id = stored_token.id.to_bytes(TOKEN_ID_BYTE_LENGTH, "little")
        payload = token_id + secret
        token = f"{project_prefix}{payload.hex().upper()}"

        return token

    def retrieve_and_validate_token(self, *, token: str, prefix: str) -> tp.Any:
        """
        Retrieves and validates a long-term token from the database.

        Args:
            token: The token string to validate.
            prefix: The expected project-specific prefix for the token.

        Returns:
            The validated Token object from the database.

        Raises:
            ValueError: If the token is invalid, expired, or not found.
        """
        if not token.startswith(prefix):
            raise ValueError("Invalid token prefix")

        payload_hex = token[len(prefix):]
        payload = bytes.fromhex(payload_hex)
        token_id_bytes = payload[:TOKEN_ID_BYTE_LENGTH]
        secret = payload[TOKEN_ID_BYTE_LENGTH:]

        token_id = int.from_bytes(token_id_bytes, "little")

        token_from_db = (
            self.db_session.query(self.long_term_token_model)
            .filter(self.long_term_token_model.id == token_id)
            .one_or_none()
        )

        if not token_from_db:
            raise ValueError("Token not found")

        if token_from_db.secret_hash != hashlib.sha256(secret).digest().hex():
            raise ValueError("Invalid token")

        if token_from_db.expires_at and token_from_db.expires_at < datetime.now(UTC):
            raise ValueError("Token expired")

        return token_from_db

    def create_short_term_jwt(self, user_id: tp.Any) -> str:
        """
        Generates a short-term JWT with a configurable expiration.

        Args:
            user_id: The ID of the user for whom the JWT is generated.
        Returns:
            The encoded JWT as a string.
        """
        if not user_id:
            raise ValueError("User ID is required")

        payload = dataclasses.replace(self.jwt_claims)
        payload.user_id = user_id
        payload.iat = datetime.now(UTC)
        payload.exp = payload.iat + timedelta(minutes=self.jwt_expiration_mins)
        return jwt.encode(
            payload.to_dict(),
            self.registry.tet_auth_jwk_resolver(self.request),
            algorithm=self.jwt_algorithm,
        )

    def verify_jwt(self, token: str) -> tp.Optional[tp.Dict[str, tp.Any]]:
        """
        Verifies and decodes a JWT, ensuring it is valid and not expired.

        Args:
            token (str): The JWT to verify.

        Returns:
            - The ``decoded payload`` if the JWT is valid
            - ``None`` if the JWT is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.registry.tet_auth_jwk_resolver(self.request),
                algorithms=[self.jwt_algorithm],
                leeway=self.jwt_claims.leeway,
                audience=self.jwt_claims.aud,
                subject=self.jwt_claims.sub,
                issuer=self.jwt_claims.iss,
            )
            return payload
        except jwt.InvalidTokenError:
            return None

    def _get_current_token(self) -> tp.Any:
        return self.retrieve_and_validate_token(
            token=self.request.cookies.get(self.long_term_token_cookie_name),
            prefix=self.project_prefix,
        )

    def _delete_execution(self, condition: list) -> None:
        stmt = delete(self.long_term_token_model).where(*condition)
        self.db_session.execute(stmt)
        self.db_session.flush()

    def delete_other_tokens(self, *, user: tp.Any = None) -> None:
        current_token = self._get_current_token()
        condition = [
            self.long_term_token_model.user_id == user.id,
            self.long_term_token_model.id != current_token.id,
        ]
        self._delete_execution(condition)

    def delete_token(self, *, user: tp.Any = None) -> None:
        current_token = self.retrieve_and_validate_token(
            token=self.request.cookies.get(self.long_term_token_cookie_name),
            prefix=self.project_prefix,
        )
        condition = [
            self.long_term_token_model.user_id == user.id,
            self.long_term_token_model.id == current_token.id,
        ]
        self._delete_execution(condition)
