import dataclasses
import enum
import typing as tp

from datetime import datetime, timedelta, timezone

from pyramid.request import Request

DEFAULT_JWT_ALGORITHM = "HS256"
DEFAULT_JWT_TOKEN_EXPIRATION_MINS = 15
DEFAULT_LONG_TERM_TOKEN_EXPIRATION_MINS = 60 * 12
DEFAULT_USER_ID_COLUMN = "user_id"
DEFAULT_LONG_TERM_TOKEN_NAME = "X-Long-Token"
DEFAULT_AUTHORIZATION_HEADER = "Authorization"
DEFAULT_REFRESH_TOKEN_COOKIE_NAME = "refresh-token"
DEFAULT_PATH = "/"
DEFAULT_UNAUTHORIZED_MESSAGE = """Access denied. You are not authorised to access this resource.
Please ensure that your credentials are correct and try again.
"""

DEFAULT_LOGIN_ATTR = "login"
UTC = timezone.utc
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
MIN_SCORE = 2
KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM = "settings.profile.changePasswordForm"
MFA_REQUIRED_KEY = "mfa_required"
TOKEN_ID_BYTE_LENGTH = 8


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


@dataclasses.dataclass
class CookieAttributes:
    name: str = None
    value: tp.Optional[str] = None
    max_age: tp.Optional[int | timedelta] = None
    domain: tp.Optional[str] = None
    path: str = DEFAULT_PATH
    secure: bool = True
    httponly: bool = True
    samesite: str = "Lax"
    overwrite: bool = True


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


@dataclasses.dataclass
class AuthLoginResult:
    """
    Dataclass for storing login data.

    Attributes:
        user_id: Unique identifier of the user.
        totp_token: Optional TOTP (Time-based One-Time Password) token for MFA.
        user_identity: Optional user identity (e.g., email, username, or id).
        mfa_required_key: Key indicating if MFA is required.
        success: Boolean indicating whether the login was successful.
    """

    user_id: tp.Any
    totp_token: tp.Optional[str] = None
    user_identity: tp.Optional[str] = None
    mfa_required_key: str = MFA_REQUIRED_KEY
    success: bool = False

    def __bool__(self) -> bool:
        """Returns True if login was successful, otherwise False."""
        return self.success


class ILoginCallback(tp.Protocol):
    """
    Authenticates a user and returns the user_id.

    **Returns:** ``user_id``
    """

    def __call__(self, request: Request) -> AuthLoginResult:
        pass


class ISecretCallback(tp.Protocol):
    """
    **Returns:** The secret key for JWT
    """

    def __call__(self, request: Request) -> tp.Union[str, dict]:
        pass


DEFAULT_REGISTERED_CLAIMS = JWTRegisteredClaims()
DEFAULT_COOKIE_ATTRIBUTES = CookieAttributes()
