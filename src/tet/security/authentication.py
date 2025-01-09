import hashlib
import secrets
import typing as tp
from datetime import UTC, datetime, timedelta

import jwt
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPForbidden
from pyramid.request import Request
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid_di import RequestScopedBaseService, autowired
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import Session
from zope.interface import Interface

__all__ = [
    "TokenAuthenticationPolicy",
    "TokenMixin",
    "auth_include",
]


SECRET_KEY = "hiddensecret"
JWT_ALGORITHM = "HS256"
DEFAULT_JWT_TOKEN_EXPIRATION_MINS = 15


def tet_config_auth(
    config: Configurator,
    token_model: tp.Any,
    user_id_column: str,
    user_verification: tp.Callable[[Request], tp.Any],
) -> None:
    """Configuration directive to set up the authentication system."""
    config.registry.tet_auth_token_model = token_model
    config.registry.tet_auth_user_id_column = user_id_column

    config.registry.tet_auth_user_verification = user_verification


class TokenAuthenticationPolicy:
    def authenticated_userid(self, request) -> int | None:
        """Return the userid of the currently authenticated user or ``None`` if
        no user is currently authenticated. This method of the policy should
        only return a value if the request has been successfully authenticated.
        """
        token_service: TetTokenService = request.find_service(TetTokenService)
        jwt_token = request.headers.get("x-jwt-token")

        if not jwt_token:
            return None

        payload = token_service.verify_jwt(jwt_token)

        return payload.get("user_id") if payload else None

    def effective_principals(self, request) -> list[str]:
        """Return a sequence representing the groups that the current user
        is in. This method of the policy should return at least one principal
        in the list: the userid of the user (and usually 'system.Authenticated'
        as well).
        """
        user_id = self.authenticated_userid(request)
        if user_id is not None:
            return [f"user:{user_id}", "system.Authenticated"]
        return ["system.Everyone"]

    def forget(self, request) -> list[tuple[str, str]]:
        """Return a set of headers suitable for 'forgetting' the current user
        on subsequent requests. An argument may be passed which can be used to
        modify the headers that are set.
        """
        return []


class TokenMixin:
    """
    Stores long-term tokens for users with creation and optional expiration timestamps.

    User ID foreign key needs to be provided by the application.

    Attributes:
    - id: Primary key for the token.
    - secret_hash: The SHA-256 hashed secret.
    - created_at: Timestamp when the token was created.
    - expires_at: Optional timestamp for token expiration.
    """

    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True)
    secret_hash = Column(String, nullable=False)
    created_at = Column(DateTime(True), default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime(True), nullable=True)


class TetTokenService(RequestScopedBaseService):
    session: Session = autowired(Session)

    def __init__(self, request: Request):
        super().__init__(request=request)

        self.token_model = self.registry.tet_auth_token_model
        self.user_id_column = self.registry.tet_auth_user_id_column
        self.jwt_expiration_mins = self.registry.get("tet_auth_jwt_expiration_mins", DEFAULT_JWT_TOKEN_EXPIRATION_MINS)

    def create_long_term_token(self, user_id: int, project_prefix: str, expire_timestamp=None, description=None) -> str:
        """
        Generates a long-term token for a user with a project-specific prefix and stores it in the database.

        Args:
        - user_id: The ID of the user for whom the token is generated.
        - project_prefix: A prefix indicating the project this token is for.
        - expire_timestamp: (Optional) Expiration timestamp for the token.
        - description: (Optional) Description for the token.

        Returns:
        - The plaintext long-term token with the project-specific prefix.
        """
        secret = secrets.token_bytes(32)
        hashed_secret = hashlib.sha256(secret).digest()

        stored_token = self.token_model(
            secret_hash=hashed_secret.hex(),
            created_at=datetime.now(UTC),
            expires_at=expire_timestamp,
        )
        setattr(stored_token, self.user_id_column, user_id)

        self.session.add(stored_token)
        self.session.flush()

        token_id = stored_token.id.to_bytes(8, "little")
        payload = token_id + secret
        token = f"{project_prefix}{payload.hex().upper()}"

        return token

    def retrieve_and_validate_token(self, token: str, prefix: str) -> tp.Any:
        """
        Retrieves and validates a long-term token from the database.

        Args:
        - token: The token string to validate.
        - prefix: The expected project-specific prefix for the token.

        Returns:
        - The validated Token object from the database.

        Raises:
        - ValueError: If the token is invalid, expired, or not found.
        """
        if not token.startswith(prefix):
            raise ValueError("Invalid token prefix")

        payload_hex = token[len(prefix) :]
        payload = bytes.fromhex(payload_hex)
        token_id_bytes = payload[:8]
        secret = payload[8:]

        token_id = int.from_bytes(token_id_bytes, "little")

        token_from_db = self.session.query(self.token_model).filter(self.token_model.id == token_id).one_or_none()

        if not token_from_db:
            raise ValueError("Token not found")

        if token_from_db.secret_hash != hashlib.sha256(secret).digest().hex():
            raise ValueError("Invalid token")

        if token_from_db.expires_at and token_from_db.expires_at < datetime.now(UTC):
            raise ValueError("Token expired")

        return token_from_db

    def create_short_term_jwt(self, user_id: int) -> str:
        """
        Generates a short-term JWT with a 15-minute expiration.

        Args:
        - user_id: The ID of the user for whom the JWT is generated.

        Returns:
        - The encoded JWT as a string.
        """
        payload = {
            "user_id": user_id,
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)

    def verify_jwt(self, token: str) -> dict | None:
        """
        Verifies and decodes a JWT, ensuring it is valid and not expired.

        Args:
        - token: The JWT to verify.

        Returns:
        - The decoded payload if the JWT is valid.
        - None if the JWT is invalid or expired.
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None


class AuthViews:
    token_service: TetTokenService = autowired(TetTokenService)

    def __init__(self, request: Request):
        self.request = request
        self.registry = request.registry

    def login_view(self) -> dict[str, tp.Any] | HTTPForbidden:
        request = self.request
        user_verification = request.registry.tet_auth_user_verification

        user_id = user_verification(request)

        if user_id is None:
            return HTTPForbidden()

        token = self.token_service.create_long_term_token(user_id, "what", expire_timestamp=None, description=None)

        resp = request.response
        resp.headers["x-long-token"] = token

        return dict(
            user_id=user_id,
            token=token,
        )

    def jwt_token_view(self) -> str:
        request = self.request
        token = request.headers.get("x-long-token")

        try:
            token_from_db = self.token_service.retrieve_and_validate_token(token, "what")
        except ValueError as e:
            request.response.status = 401
            return str(e)

        user_id = getattr(token_from_db, self.token_service.user_id_column)

        jwt_token = self.token_service.create_short_term_jwt(user_id)

        request.response.headers["x-jwt-token"] = jwt_token

        return "ok"


def auth_include(config: Configurator):
    """Routes and stuff to register maybe under a prefix"""
    config.add_view(
        AuthViews,
        attr="login_view",
        route_name="tet_auth_login",
        renderer="json",
        request_method="POST",
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED,
    )
    config.add_route("tet_auth_login", "login")

    config.add_view(
        AuthViews,
        attr="jwt_token_view",
        route_name="tet_auth_jwt",
        renderer="string",
        request_method="GET",
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED,
    )
    config.add_route("tet_auth_jwt", "jwt-token")

    config.add_directive("tet_config_auth", tet_config_auth)

    config.register_service_factory(lambda ctx, req: TetTokenService(request=req), TetTokenService, Interface)

    config.set_default_permission("view")
    config.set_authentication_policy(TokenAuthenticationPolicy())
    config.set_authorization_policy(ACLAuthorizationPolicy())
