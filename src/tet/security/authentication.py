import base64
import dataclasses
import enum
import hashlib
import io
import logging
import secrets
import typing as tp
from datetime import datetime, timedelta, timezone

import jwt
import pyotp
import qrcode
import qrcode.image.svg
import requests
from pyramid.authentication import CallbackAuthenticationPolicy
from pyramid.authorization import ACLHelper
from pyramid.config import Configurator
from pyramid.httpexceptions import (
    HTTPForbidden,
    HTTPUnauthorized,
    HTTPBadRequest,
    HTTPException,
    HTTPInternalServerError,
)
from pyramid.interfaces import ISecurityPolicy
from pyramid.request import Request
from pyramid.response import Response
from pyramid.security import NO_PERMISSION_REQUIRED, Everyone, Authenticated
from pyramid_di import RequestScopedBaseService, autowired
from sqlalchemy import Column, DateTime, Integer, String, Enum, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from sqlalchemy.sql import delete
from zope.interface import Interface, implementer

from tet.security.events import *

logger = logging.getLogger(__name__)
__all__ = [
    "TokenAuthenticationPolicy",
    "JWTCookieAuthenticationPolicy",
    "TokenMixin",
    "JWTRegisteredClaims",
    "MultiFactorAuthMethodType",
    "MultiFactorAuthenticationMethodMixin",
    "TetMultiFactorAuthenticationService",
    "TetTokenService",
    "TOTPData",
    "CookieAttributes",
]


@dataclasses.dataclass
class PasswordChangeData:
    current_password: str
    new_password: str


@dataclasses.dataclass
class JWTRegisteredClaims:
    """
    A dataclass representing the registered claims in a JSON Web Token (JWT).

    These claims are defined by the JWT specification (RFC 7519) and are commonly
    used for token validation. The fields are optional and can be included as needed.

    More info about the registered claims can be found here:
        https://pyjwt.readthedocs.io/en/2.0.1/usage.html?highlight=datetime#registered-claim-names

    Attributes:
        user_id (Any): User ID - The unique identifier for the user.
        iss (str): Issuer - Identifies the principal that issued the JWT.
        sub (str): Subject - Identifies the principal that is the subject of the JWT.
        aud (Union[str, list]): Audience - Identifies the recipients that the JWT is intended for.
        exp (datetime): Expiration Time - Identifies when the JWT expires.
        nbf (datetime): Not Before - Identifies when the JWT becomes valid.
        iat (datetime): Issued At - Identifies when the JWT was issued.
        jti (str): JWT ID - A unique identifier for the JWT.
        leeway (int): The amount of time (in seconds) that the token is valid before/after the specified time.

    Methods:
        to_dict() -> dict[str, Any]:
            Converts the dataclass instance into a dictionary

    Example:

        .. code-block:: python

            claims = JWTRegisteredClaims(
                iss="my-auth-service",
                sub="user123",
                aud="my-api.example.com",
                exp=datetime.utcnow() + timedelta(hours=1),
                iat=datetime.utcnow(),
                jti="unique-token-id-456"
            )

            payload = claims.to_dict()
    """

    user_id: tp.Any = None
    iss: str = None
    sub: str = None
    aud: tp.Union[str, list] = None
    exp: datetime = None
    nbf: datetime = None
    iat: datetime = None
    jti: str = None
    leeway: int = 0

    def to_dict(self) -> tp.Dict[str, tp.Any]:
        """
        Converts the JWTRegisteredClaims instance into a dictionary.

        Ensures that datetime fields (`exp`, `nbf`, `iat`) are represented
        as Unix timestamps (seconds since epoch) or datetime objects.

        Returns:
            dict[str, Any]: A dictionary representation of the registered claims.
        """
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}


@implementer(ISecurityPolicy)
class TokenAuthenticationPolicy(CallbackAuthenticationPolicy):
    """
    A Pyramid security policy for token-based authentication.

    All methods in this class are only invoked if the view has a `permission` set in `@view_config()`.
    This ensures that authentication and authorization checks are enforced before access is granted.

    Example:

    .. code-block:: python

        @view_config(route_name="home", renderer="json", permission="view")
        def home_view(request):
            user_id = request.authenticated_userid
            return {"message": f"Hello, User {user_id}"}
    """

    def __init__(self):
        self.acl = ACLHelper()

    def authenticated_userid(self, request: Request) -> tp.Optional[int]:
        """This method of the policy should
        only return a value if the request has been successfully authenticated.

        Returns:
           - Return the ``userid`` of the currently authenticated user
           - ``None`` if no user is authenticated.
        """
        token_service: TetTokenService = request.find_service(TetTokenService)
        jwt_token = request.headers.get(request.registry.tet_auth_access_token_header)

        if not jwt_token:
            return None

        payload = token_service.verify_jwt(jwt_token)

        return payload.get("user_id") if payload else None

    def permits(self, request, context, permission):
        principals = self.effective_principals(request)
        return self.acl.permits(context, principals, permission)

    def effective_principals(self, request) -> tp.List[str]:
        """This method of the policy should return at least one principal
        in the list: the userid of the user (and usually 'system.Authenticated'
        as well).
        Returns:
           A sequence representing the groups that the current user is in
        """
        principals = [Everyone]
        user_id = self.authenticated_userid(request)
        if user_id is not None:
            principals.extend([f"user:{user_id}", Authenticated])
        return principals

    def forget(self, request) -> tp.List[tuple[str, str]]:
        """
        This method does not need to be implemented for header-based authentication.
        """
        return []


@implementer(ISecurityPolicy)
class JWTCookieAuthenticationPolicy(TokenAuthenticationPolicy):
    """
    A Pyramid security policy that authenticates users via JWT tokens stored in cookies.

    All methods in this class are only invoked if the view has a `permission` set in `@view_config()`,
    ensuring authentication and authorization checks are enforced before access is granted.

    This policy retrieves JWT tokens from cookies instead of headers.
    """

    def __init__(self):
        super().__init__()


DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_JWT_TOKEN_EXPIRATION_MINS = 15
DEFAULT_LONG_TERM_TOKEN_EXPIRATION_MINS = 60 * 12
DEFAULT_USER_ID_COLUMN = "user_id"
DEFAULT_LONG_TERM_TOKEN_NAME = "X-Long-Token"
DEFAULT_ACCESS_TOKEN_NAME = "X-Access-Token"
DEFAULT_ACCESS_TOKEN_COOKIE_NAME = "access-token"
DEFAULT_REFRESH_TOKEN_COOKIE_NAME = "refresh-token"
DEFAULT_PATH = "/"
DEFAULT_REFRESH_TOKEN_ROUTE = "refresh_token"
DEFAULT_UNAUTHORIZED_MESSAGE = """Access denied. You are not authorised to access this resource.
Please ensure that your credientials are correct and try again.
"""


@dataclasses.dataclass
class CookieAttributes:
    name: str = None
    value: tp.Optional[str] = None
    max_age: tp.Optional[int | timedelta] = None
    domain: tp.Optional[str] = None
    path: str = DEFAULT_PATH
    secure: bool = False
    httponly: bool = False
    samesite: str = "Lax"
    overwrite: bool = True


DEFAULT_LOGIN_ATTR = "login"
COOKIE_LOGIN_VIEW = "cookie_login"
DEFAULT_REGISTERED_CLAIMS = JWTRegisteredClaims()
DEFAULT_SECURITY_POLICY = TokenAuthenticationPolicy()
DEFAULT_COOKIE_ATTRIBUTES = CookieAttributes()
UTC = timezone.utc
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
MIN_SCORE = 2
KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM = "settings.profile.changePasswordForm"


class ILoginCallback(tp.Protocol):
    """
    Authenticates a user and returns the user_id.

    **Returns:** ``user_id``
    """

    def __call__(self, request: Request) -> tp.Optional[tp.Any]:
        pass


class ISecretCallback(tp.Protocol):
    """
    **Returns:** The secret key for JWT
    """

    def __call__(self, request: Request) -> tp.Union[str, dict]:
        pass


def set_token_authentication(
    config: Configurator,
    *,
    long_term_token_model: tp.Any,
    multi_factor_auth_method_model: tp.Any,
    user_model: tp.Any,
    project_prefix: str,
    login_callback: ILoginCallback,
    jwk_resolver: ISecretCallback,
    user_id_column: str = DEFAULT_USER_ID_COLUMN,
    jwt_algorithm: str = DEFAULT_JWT_ALGORITHM,
    jwt_token_expiration_mins: int = DEFAULT_JWT_TOKEN_EXPIRATION_MINS,
    long_term_token_expiration_mins: int = DEFAULT_LONG_TERM_TOKEN_EXPIRATION_MINS,
    access_token_header: str = DEFAULT_ACCESS_TOKEN_NAME,
    long_term_token_header: str = DEFAULT_LONG_TERM_TOKEN_NAME,
    long_term_token_cookie_name: str = DEFAULT_REFRESH_TOKEN_COOKIE_NAME,
    jwt_claims: JWTRegisteredClaims = DEFAULT_REGISTERED_CLAIMS,
    refresh_token_route: str = DEFAULT_REFRESH_TOKEN_ROUTE,
    cookie_attributes: tp.Optional[CookieAttributes] = None,
    security_policy: tp.Optional[
        tp.Union[type["TokenAuthenticationPolicy"], type["JWTCookieAuthenticationPolicy"]]
    ] = DEFAULT_SECURITY_POLICY,
) -> None:
    """
    Configure token-based authentication for a Pyramid application (with conflict detection).

    .. note::

        This function is intended to be used as a Pyramid configuration directive. By calling
        :meth:`pyramid.config.Configurator.action` with a unique ``discriminator``, it ensures
        that conflicts are detected if multiple parts of the application try to register the
        same directive.
    Example:
        1. **Add the directive** (typically in your ``includeme`` function):

        .. code-block:: python

           from pyramid.config import Configurator
           from myproject.auth import set_token_authentication

           def includeme(config: Configurator):
               # Register the custom directive
               config.add_directive(
                   'set_token_authentication',
                   set_token_authentication
               )

        2. **Use the directive** somewhere after including it:

        .. code-block:: python

           def main(global_config, **settings):
               config = Configurator(settings=settings)
               config.include('myproject')  # calls includeme(...)

               config.set_token_authentication(
                   long_term_token_model=MyTokenModel,
                   project_prefix='my_project',
                   login_callback=verify_user,
                   jwk_resolver=get_secret,
                   jwt_algorithm='HS256',
                   jwt_token_expiration_mins=120
               )

               return config.make_wsgi_app()

        **Accessing the Configured Values**

        Later in the application code, it can retrieve these values from ``request.registry``:

        .. code-block:: python

           @view_config(route_name='home')
           def home_view(request):
               long_term_token_model = request.registry.tet_auth_long_term_token_model
               prefix = request.registry.tet_auth_project_prefix
               # ... do something with these values ...

    Args:
        config: The current Pyramid :class:`pyramid.config.Configurator` instance.
        long_term_token_model: A token model class or object representing user tokens.
        project_prefix: A project-specific prefix (could be used for namespacing).
        user_id_column: Column name or attribute for user ID in the token model. Defaults to ``"user_id"``.
        login_callback: A callable to verify user credentials/status from the database.
        jwk_resolver: A callable that returns a secret key or keys for token signing.
        jwt_algorithm: The JWT algorithm to use (default: ``"HS256"``).
        jwt_token_expiration_mins: JWT expiration time in minutes (default: 15).
        access_token_header: The header name for the access token (default: ``"X-Access-Token"``).
        long_term_token_header: The header name for the long-term token (default: ``"X-Long-Token"``).
        jwt_claims: Default JWT registered claims to include in the token payload.
        security_policy: A custom security policy to use for token authentication.
    """

    def register():
        config.registry.tet_auth_long_term_token_model = long_term_token_model
        config.registry.tet_multi_factor_auth_method_model = multi_factor_auth_method_model
        config.registry.tet_auth_user_model = user_model
        config.registry.tet_auth_project_prefix = project_prefix
        config.registry.tet_auth_user_id_column = user_id_column
        config.registry.tet_auth_access_token_header = access_token_header
        config.registry.tet_auth_long_term_token_header = long_term_token_header
        config.registry.tet_auth_long_term_token_cookie_name = long_term_token_cookie_name
        config.registry.tet_auth_jwt_claims = jwt_claims
        config.registry.tet_auth_cookie_attributes = cookie_attributes

        config.registry.tet_auth_login_callback = login_callback
        config.registry.tet_auth_jwk_resolver = jwk_resolver
        config.registry.tet_auth_jwt_algorithm = jwt_algorithm
        config.registry.tet_auth_jwt_expiration_mins = jwt_token_expiration_mins
        config.registry.tet_auth_long_term_token_expiration_mins = long_term_token_expiration_mins
        config.registry.tet_auth_refresh_token_route = refresh_token_route
        config.registry.tet_auth_security_policy = security_policy

    config.action(discriminator="set_token_authentication", callable=register)

    config.set_security_policy(security_policy)


@dataclasses.dataclass
class TOTPData:
    """
    Dataclass for storing TOTP-specific configuration data.

    Attributes:
        secret: The shared secret key for TOTP generation.
        issuer: The name of the service or application issuing the TOTP code.
        digits: The number of digits in the generated TOTP code.
        period: The time period (in seconds) for TOTP code generation.
        algorithm: The hash algorithm used for TOTP generation.
    """

    secret: str
    issuer: str
    digits: int = 6
    period: int = 30
    algorithm: str = "SHA1"

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class MultiFactorAuthMethodType(enum.Enum):
    """
    Enum for the available multi-factor authentication methods.

    Attributes:
        HOTP: HMAC-based One Time Password
        TOTP: Time-based One Time Password
        U2F: Universal 2nd Factor
        HMAC: Hash-based Message Authentication Code
        OTP: One Time Password
        SMS: Short Message Service
    """

    TOTP = "totp"
    HOTP = "hotp"
    U2F = "u2f"
    HMAC = "hmac"
    OTP = "otp"
    SMS = "sms"


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
        self, user_id: tp.Any, project_prefix: str, expire_timestamp: tp.Optional[datetime] = None
    ) -> str:
        """
        Generates a long-term token for a user with a project-specific prefix and stores it in the database.
        Args:
            user_id: The ID of the user for whom the token is generated.
            project_prefix: A prefix indicating the project this token is for.
            Expire_timestamp: (Optional) Expiration timestamp for the token.

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

        token_id = stored_token.id.to_bytes(8, "little")
        payload = token_id + secret
        token = f"{project_prefix}{payload.hex().upper()}"

        return token

    def retrieve_and_validate_token(self, token: str, prefix: str) -> tp.Any:
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

        payload_hex = token[len(prefix) :]
        payload = bytes.fromhex(payload_hex)
        token_id_bytes = payload[:8]
        secret = payload[8:]

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
        Generates a short-term JWT with a 15-minute expiration.

        Args:
            user_id: The ID of the user for whom the JWT is generated.
        Returns:
            The encoded JWT as a string.
        """
        # TODO: In the next update, we can add more encoding options here, such as headers, json_encoder.
        if not user_id:
            raise ValueError("User ID is required")

        payload = self.jwt_claims
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
        except jwt.ExpiredSignatureError:
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


class TetAuthService(RequestScopedBaseService):
    db_session: Session = autowired(Session)
    token_service = autowired(TetTokenService)

    def __init__(self, request: Request):
        super().__init__(request=request)
        self.project_prefix: str = self.registry.tet_auth_project_prefix
        self.long_term_token_cookie_name = self.registry.tet_auth_long_term_token_cookie_name
        self.long_term_token_expiration_mins = (
            self.registry.tet_auth_long_term_token_expiration_mins
        )
        self.user_model: tp.Any = self.registry.tet_auth_user_model

    def set_cookies(
        self,
        cookie_attributes: CookieAttributes,
        **kwargs,
    ):
        route_prefix = kwargs.pop("route_prefix")
        refresh_token = kwargs.pop("refresh_token")

        if cookie_attributes:
            cookie_attributes.value = refresh_token
            if not cookie_attributes.max_age:
                cookie_attributes.max_age = self.long_term_token_expiration_mins * 60

        cookie_attrs = cookie_attributes or CookieAttributes(
            name=self.long_term_token_cookie_name,
            value=refresh_token,
            max_age=self.long_term_token_expiration_mins * 60,
            path=f"{route_prefix}/",
        )
        self.request.response.set_cookie(
            **cookie_attrs.__dict__,
            **kwargs,
        )

    def delete_cookie(self, *, name: str, path: str = "/", **kwargs):
        self.request.response.delete_cookie(
            name=name,
            path=path,
            **kwargs,
        )

    def validate_and_create_jwt(self, refresh_token: str, route_prefix: str) -> str:
        try:
            token_from_db = self.token_service.retrieve_and_validate_token(
                refresh_token, self.project_prefix
            )
        except ValueError as e:
            logger.exception(f"Error validating token: {e}")
            self.delete_cookie(
                name=self.long_term_token_cookie_name,
                path=f"{route_prefix}/",
            )
            raise HTTPUnauthorized() from e

        user_id = getattr(token_from_db, self.token_service.user_id_column)

        return self.token_service.create_short_term_jwt(user_id)

    def verify_password(self, user: tp.Any, password: str) -> bool:
        return user.verify_password(password)

    def is_password_breached(self, password: str) -> bool:
        sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1_hash[:5], sha1_hash[5:]
        url = f"{self.request.registry.settings['pwned_passwords_api_url']}{prefix}"
        response = requests.get(url)
        response.raise_for_status()

        for line in response.text.splitlines():
            hash_suffix, count = line.split(":")
            if hash_suffix == suffix:
                return True
        return False

    @staticmethod
    def assess_password_strength(password: str) -> int:
        strength = 0
        if len(password) > 0:
            strength += 1
        if len(password) >= MIN_PASSWORD_LENGTH:
            strength += 4
        return strength

    def get_current_user(self, user_id: tp.Any) -> tp.Optional[tp.Any]:
        return (
            self.db_session.query(self.user_model)
            .filter(self.user_model.id == user_id)
            .one_or_none()
        )

    def change_password(self, payload: PasswordChangeData, user: tp.Any) -> bool:
        is_valid = self.password_change_validation(payload=payload, user=user)
        user.password = payload.new_password
        self.db_session.flush()
        return is_valid

    def password_change_validation(self, payload: PasswordChangeData, user: tp.Any) -> bool:
        if self.is_password_breached(payload.new_password):
            raise ValueError(
                f"{KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM}.PASSWORD_LEAKED_EASY_TO_GUESS"
            )

        validations = [
            (
                self.assess_password_strength(payload.new_password) >= MIN_SCORE,
                f"{KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM}.PASSWORD_STRENGTH_TOO_WEAK",
            ),
            (
                MIN_PASSWORD_LENGTH <= len(payload.new_password) <= MAX_PASSWORD_LENGTH,
                f"{KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM}.INCORRECT_PASSWORD_LENGTH",
            ),
            (
                self.verify_password(user=user, password=payload.current_password),
                f"{KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM}.INVALID_CREDENTIALS",
            ),
        ]
        for condition, error_message in validations:
            if not condition:
                raise ValueError(error_message)
        return True


class TetMultiFactorAuthenticationService(RequestScopedBaseService):
    session: Session = autowired(Session)
    token_service: TetTokenService = autowired(TetTokenService)
    auth_service: TetAuthService = autowired(TetAuthService)

    def __init__(self, request: Request):
        super().__init__(request=request)
        self.tet_multi_factor_auth_method_model: tp.Any = (
            self.registry.tet_multi_factor_auth_method_model
        )
        self.project_prefix: str = self.registry.tet_auth_project_prefix
        self.long_term_token_cookie_name = self.registry.tet_auth_long_term_token_cookie_name
        self.long_term_token_expiration_mins = (
            self.registry.tet_auth_long_term_token_expiration_mins
        )

    def create_method(self, *, method_type: MultiFactorAuthMethodType, user_id: tp.Any, data: dict):
        """
        Create a new multifactor authentication method for a user.
        """
        new_mfa_method = self.tet_multi_factor_auth_method_model(
            method_type=method_type, user_id=user_id, data=data
        )
        self.session.add(new_mfa_method)
        self.session.flush()
        return new_mfa_method

    def disable_method(self, user_id: tp.Any, method_type: MultiFactorAuthMethodType):
        """
        Disable a multifactor authentication method for a user.
        """
        self.session.query(self.tet_multi_factor_auth_method_model).filter_by(
            user_id=user_id, method_type=method_type.value
        ).update({"is_active": False, "verified": False, "data": {}})

    @staticmethod
    def verify_totp(secret: tp.Any, token: tp.Any) -> bool:
        """
        Verify a one-time password for multifactor authentication.
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(token)

    def get_method(
        self,
        *,
        user_id: tp.Any,
        method_type: MultiFactorAuthMethodType,
        is_active: bool = True,
        verified: bool = True,
    ):
        """
        Retrieve a multifactor authentication method for a user.
        """
        conditions = [
            self.tet_multi_factor_auth_method_model.user_id == user_id,
            self.tet_multi_factor_auth_method_model.method_type == method_type,
        ]
        if is_active:
            conditions.append(self.tet_multi_factor_auth_method_model.is_active == is_active)
        if verified:
            conditions.append(self.tet_multi_factor_auth_method_model.verified == verified)
        return (
            self.session.query(self.tet_multi_factor_auth_method_model)
            .filter(*conditions)
            .one_or_none()
        )

    def get_active_methods_by_user_id(self, *, user_id: tp.Any):
        """
        Retrieve all multifactor authentication methods by user id.
        """
        return (
            self.session.query(self.tet_multi_factor_auth_method_model)
            .filter_by(user_id=user_id, is_active=True, verified=True)
            .all()
        )

    def is_totp_mfa_enabled(self, user_id: tp.Any = None) -> bool:
        """
        Check if multifactor authentication is enabled for the user.
        """
        return (
            self.session.query(self.tet_multi_factor_auth_method_model)
            .filter(
                self.tet_multi_factor_auth_method_model.user_id == user_id,
                self.tet_multi_factor_auth_method_model.is_active,
                self.tet_multi_factor_auth_method_model.verified,
            )
            .count()
            > 0
        )

    def handle_totp_verify(self, user_id: tp.Any, token: tp.Any, setup_key: tp.Any) -> dict:
        try:
            totp_mfa_method = self.get_method(
                user_id=user_id,
                method_type=MultiFactorAuthMethodType.TOTP,
                is_active=False,
                verified=False,
            )
            if not totp_mfa_method:
                raise HTTPForbidden(
                    json_body={"message": "Two-factor authentication method not found."}
                )

            if not setup_key:
                raise HTTPBadRequest(json_body={"message": "Missing TOTP secret."})

            is_valid = self.verify_totp(secret=setup_key, token=token)

            if not is_valid:
                raise HTTPForbidden(json_body={"message": "Two-factor authentication failed."})

            totp_mfa_method.mark_used()

            data = TOTPData(
                secret=setup_key,
                issuer=self.project_prefix,
            )
            totp_mfa_method.verified = True
            totp_mfa_method.is_active = True
            totp_mfa_method.data = data.to_dict()
            return {"success": is_valid}
        except KeyError as e:
            raise HTTPBadRequest(
                json_body={"message": "Missing required field.", "details": str(e)}
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPInternalServerError(
                json_body={"message": "TOTP verification failed.", "details": str(e)}
            ) from e

    def handle_totp_challenge(
        self,
        user_id: tp.Any,
        totp_token: str = None,
        cookie_attributes: CookieAttributes = None,
        route_prefix: str = None,
    ) -> dict[str, tp.Any]:
        try:
            totp_mfa_method = self.get_method(
                user_id=user_id,
                method_type=MultiFactorAuthMethodType.TOTP,
                is_active=True,
                verified=True,
            )
            if not totp_mfa_method:
                raise HTTPForbidden(
                    json_body={"message": "Two-factor authentication method not found."}
                )

            secret = totp_mfa_method.data.get("secret")

            if not secret:
                raise HTTPBadRequest(json_body={"message": "Missing TOTP secret."})

            is_valid = self.verify_totp(secret=secret, token=totp_token)

            if not is_valid:
                raise HTTPForbidden(json_body={"message": "Two-factor authentication failed."})

            totp_mfa_method.mark_used()

            refresh_token = self.token_service.create_long_term_token(user_id, self.project_prefix)
            access_token = self.token_service.create_short_term_jwt(user_id)

            self.auth_service.set_cookies(
                cookie_attributes=cookie_attributes,
                refresh_token=refresh_token,
                route_prefix=route_prefix,
            )
            self.registry.notify(MfaLoginSuccessEvent(request=self.request))
            return {"success": is_valid, "access_token": access_token}
        except KeyError as e:
            self.registry.notify(MfaLoginFailedEvent(request=self.request))
            raise HTTPBadRequest(
                json_body={"message": "Missing required field.", "details": str(e)}
            ) from e
        except Exception as e:
            self.registry.notify(MfaLoginFailedEvent(request=self.request))
            raise HTTPInternalServerError(
                json_body={"message": "TOTP verification failed.", "details": str(e)}
            ) from e

    @staticmethod
    def _create_totp_data(issuer: str) -> TOTPData:
        secret = pyotp.random_base32()
        return TOTPData(
            secret=secret,
            issuer=issuer,
        )

    @staticmethod
    def generate_qr_img(user: tp.Any, mfa_secret: str, data: tp.Union[TOTPData]) -> str:
        otp_uri = pyotp.totp.TOTP(mfa_secret).provisioning_uri(
            name=user.display_name, issuer_name=data.issuer
        )
        factory = qrcode.image.svg.SvgImage
        qr = qrcode.QRCode(box_size=15, border=4)
        qr.add_data(otp_uri)
        qr.make(fit=True)
        img = qr.make_image(image_factory=factory)
        buffer = io.BytesIO()
        img.save(buffer)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def handle_totp_setup(self, *, user: tp.Any, project_prefix: str) -> dict:
        try:
            data: TOTPData = self._create_totp_data(issuer=project_prefix)
            existing_method = self.get_method(
                user_id=user.id,
                method_type=MultiFactorAuthMethodType.TOTP,
                is_active=False,
                verified=False,
            )
            if not existing_method:
                self.create_method(
                    method_type=MultiFactorAuthMethodType.TOTP,
                    user_id=user.id,
                    data=data.to_dict(),
                )
            mfa_secret = data.secret
            img_str = self.generate_qr_img(user=user, mfa_secret=mfa_secret, data=data)
            return {"secret": mfa_secret, "qr_code": f"data:image/svg+xml;base64,{img_str}"}
        except Exception as e:
            logger.exception(e)
            return dict(success=False, message="Error generating TOTP method")


class AuthViews:
    token_service: TetTokenService = autowired(TetTokenService)
    auth_service: TetAuthService = autowired(TetAuthService)
    multi_factor_auth_service: TetMultiFactorAuthenticationService = autowired(
        TetMultiFactorAuthenticationService
    )
    db_session: Session = autowired(Session)

    def __init__(self, request: Request):
        self.request = request
        self.registry = request.registry
        self.response = request.response
        self.project_prefix = self.registry.tet_auth_project_prefix
        self.long_term_token_cookie_name = self.registry.tet_auth_long_term_token_cookie_name
        self.long_term_token_expiration_mins = (
            self.registry.tet_auth_long_term_token_expiration_mins
        )
        self.refresh_token_route = self.registry.tet_auth_refresh_token_route
        self.route_prefix = self.request.current_route_path().rpartition("/")[0]
        self.login_callback = self.registry.tet_auth_login_callback
        self.cookie_attributes: tp.Optional[CookieAttributes] = (
            self.registry.tet_auth_cookie_attributes
        )

    def login(self) -> dict[str, tp.Any]:
        user_id = self.login_callback(self.request)
        if user_id is None:
            self.registry.notify(LoginFailedEvent(request=self.request))
            raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})

        payload = self.request.json_body
        totp_token = payload.get("token")
        response_payload: dict[str, tp.Any] = {"success": True}
        refresh_token = self.token_service.create_long_term_token(user_id, self.project_prefix)
        access_token = self.token_service.create_short_term_jwt(user_id)

        if self.multi_factor_auth_service.is_totp_mfa_enabled(user_id):
            if not totp_token:
                response_payload["mfa_required"] = True
                return response_payload

            return self.multi_factor_auth_service.handle_totp_challenge(
                user_id=user_id, totp_token=totp_token
            )

        self.auth_service.set_cookies(
            cookie_attributes=self.cookie_attributes,
            refresh_token=refresh_token,
            route_prefix=self.route_prefix,
        )
        response_payload["access_token"] = access_token

        self.registry.notify(LoginSuccessEvent(request=self.request))
        return response_payload

    def mfa_verify(self) -> dict:
        """
        Verifies the TOTP code for the currently authenticated user.

        Raises:
            HTTPUnauthorized: If no authenticated user ID is found in the request.

        Returns:
            dict: Result of the TOTP verification for the user.
        """
        user_id = self.request.authenticated_userid
        if not user_id:
            raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})

        payload = self.request.json_body
        token = payload["token"]
        setup_key = payload["setup_key"]
        return self.multi_factor_auth_service.handle_totp_verify(
            user_id=user_id, token=token, setup_key=setup_key
        )

    def refresh_token(self) -> tp.Union[tp.Dict[str, tp.Any], HTTPUnauthorized]:
        refresh_token = self.request.cookies.get(self.long_term_token_cookie_name)
        if not refresh_token:
            raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})

        access_token = self.auth_service.validate_and_create_jwt(
            refresh_token=refresh_token, route_prefix=self.route_prefix
        )
        return {"success": True, "access_token": access_token}

    def change_password(self):
        user_id = self.request.authenticated_userid
        if user_id is None:
            self.registry.notify(ChangePasswordFailedEvent(request=self.request))
            raise HTTPUnauthorized(
                json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE, "success": False}
            )
        try:
            data = self.request.json_body
            payload = PasswordChangeData(
                current_password=data["currentPassword"],
                new_password=data["newPassword"],
            )
            user = self.auth_service.get_current_user(user_id)
            is_valid = self.auth_service.change_password(payload=payload, user=user)
            self.token_service.delete_other_tokens(user=user)
            self.registry.notify(ChangePasswordSuccessEvent(request=self.request))
            return {"success": is_valid}
        except ValueError as e:
            self.registry.notify(ChangePasswordFailedEvent(request=self.request))
            return HTTPForbidden(json_body={"message": str(e), "success": False})

    def logout(self) -> tp.Union[tp.Dict[str, tp.Any], HTTPForbidden, Response]:
        try:
            user_id = self.request.authenticated_userid
            user = self.auth_service.get_current_user(user_id=user_id)
            self.token_service.delete_token(user=user)
            self.response.delete_cookie(
                name=self.long_term_token_cookie_name,
                path=f"{self.route_prefix}/",
            )
            self.registry.notify(LogoutSuccessEvent(request=self.request))
        except Exception:
            self.registry.notify(LogoutFailedEvent(request=self.request))
            return HTTPForbidden(json_body={"message": "Failed to logout", "success": False})
        return {"success": True}

    def disable_mfa_method(self):
        user_id = self.request.authenticated_userid
        if user_id is None:
            raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})
        payload = self.request.json_body
        mfa_method_type = MultiFactorAuthMethodType(payload["method_type"])
        if not mfa_method_type:
            raise HTTPForbidden(json_body={"message": "Invalid MFA method type"})
        try:
            self.multi_factor_auth_service.disable_method(
                user_id=user_id, method_type=mfa_method_type
            )
            self.registry.notify(DisableMfaSuccessEvent(request=self.request))
        except Exception:
            self.registry.notify(DisableMfaFailedEvent(request=self.request))
            return HTTPForbidden(json_body={"message": "Failed to disable MFA method"})
        return {"success": True}

    def revoke_other_tokens(self):
        user_id = self.request.authenticated_userid
        user = self.auth_service.get_current_user(user_id=user_id)
        payload = self.request.json_body
        if user is None or not self.auth_service.verify_password(
            user=user, password=payload.get("password", "")
        ):
            self.registry.notify(RevokeOtherRefreshTokensFailedEvent(request=self.request))
            raise HTTPUnauthorized(json_body={"message": "Unauthorized", "success": False})
        self.token_service.delete_other_tokens(user=user)
        self.registry.notify(RevokeOtherRefreshTokensSuccessEvent(request=self.request))
        return {"success": True}

    def get_mfa_methods(self) -> dict[str, tp.List[tp.Any]]:
        user_id = self.request.authenticated_userid
        if user_id is None:
            raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})
        mfa_methods: tp.List[tp.Any] = self.multi_factor_auth_service.get_active_methods_by_user_id(
            user_id=user_id
        )
        return {"method_types": [mfa_method.method_type.value for mfa_method in mfa_methods]}

    def generate_mfa_totp(self):
        user_id = self.request.authenticated_userid
        user = self.auth_service.get_current_user(user_id=user_id)
        if user_id is None:
            raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})

        payload = self.request.json_body
        if payload["method_type"] == MultiFactorAuthMethodType.TOTP.value:
            return self.multi_factor_auth_service.handle_totp_setup(
                user=user, project_prefix=self.project_prefix
            )
        return None


def includeme(config: Configurator):
    """Routes and stuff to register maybe under a prefix"""
    config.add_route("tet_auth_login", "/login")
    config.add_route("tet_auth_logout", "/logout")
    config.add_route("tet_auth_refresh_token", "/token/refresh")
    config.add_route("tet_auth_change_password", "/users/me/password")
    config.add_route("tet_auth_revoke_other_tokens", "/users/me/tokens/others")
    config.add_route("tet_auth_mfa_verify", "/mfa/app/verify")
    config.add_route("tet_auth_disable_mfa_method", "/mfa/app/disable")
    config.add_route("tet_auth_generate_mfa_totp", "/mfa/app/setup")
    config.add_route("tet_auth_get_mfa_methods", "/mfa/methods")

    config.add_view(
        AuthViews,
        attr="generate_mfa_totp",
        route_name="tet_auth_generate_mfa_totp",
        request_method="POST",
        renderer="json",
        require_csrf=False,
    )
    config.add_view(
        AuthViews,
        attr="get_mfa_methods",
        route_name="tet_auth_get_mfa_methods",
        request_method="GET",
        renderer="json",
        require_csrf=False,
    )
    config.add_view(
        AuthViews,
        attr="revoke_other_tokens",
        route_name="tet_auth_revoke_other_tokens",
        request_method="DELETE",
        renderer="json",
        require_csrf=False,
    )
    config.add_view(
        AuthViews,
        attr="disable_mfa_method",
        route_name="tet_auth_disable_mfa_method",
        request_method="POST",
        renderer="json",
        require_csrf=False,
    )
    config.add_view(
        AuthViews,
        attr="logout",
        route_name="tet_auth_logout",
        request_method="POST",
        renderer="json",
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED,
    )
    config.add_view(
        AuthViews,
        attr="change_password",
        route_name="tet_auth_change_password",
        request_method="POST",
        renderer="json",
        require_csrf=False,
    )
    config.add_view(
        AuthViews,
        attr="refresh_token",
        route_name="tet_auth_refresh_token",
        renderer="json",
        request_method="POST",
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED,
    )

    config.add_view(
        AuthViews,
        attr="mfa_verify",
        route_name="tet_auth_mfa_verify",
        renderer="json",
        request_method="POST",
        require_csrf=False,
    )

    config.add_view(
        AuthViews,
        attr=DEFAULT_LOGIN_ATTR,
        route_name="tet_auth_login",
        renderer="json",
        request_method="POST",
        require_csrf=False,
        permission=NO_PERMISSION_REQUIRED,
    )

    config.add_directive("set_token_authentication", set_token_authentication)

    config.include("pyramid_di")
    config.register_service_factory(
        lambda ctx, req: TetTokenService(request=req), TetTokenService, Interface
    )
    config.register_service_factory(
        lambda ctx, req: TetMultiFactorAuthenticationService(request=req),
        TetMultiFactorAuthenticationService,
        Interface,
    )
    config.register_service_factory(
        lambda ctx, req: TetAuthService(request=req),
        TetAuthService,
        Interface,
    )

    config.set_default_permission("view")
