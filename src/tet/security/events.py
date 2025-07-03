import dataclasses
import typing as tp

from pyramid.request import Request

__all__ = [
    "TetAuthEvent",
    "AuthnPasswordChange",
    "AuthnPasswordChangeFail",
    "AuthnLoginSuccess",
    "AuthnLoginFail",
    "AuthnLogoutSuccess",
    "AuthnLogoutFail",
    "AuthnMfaMethodDisabled",
    "AuthnMfaMethodDisableFail",
    "AuthnMfaMethodCreated",
    "AuthnRefreshTokensRevoked",
    "AuthnRefreshTokenRevokeFail",
    "AuthnCurrentRefreshTokenRevoked",
    "AuthnCurrentRefreshTokenRevokeFail",
    "AuthnInputValidationFail",
    "AuthzFail",
]


@dataclasses.dataclass(kw_only=True, slots=True)
class TetAuthEvent:
    """
    Base class for all authentication and authorisation event types.

    Attributes:
        request (Request): The originating request object.
    """

    request: Request


# Auth events


@dataclasses.dataclass()
class AuthzFail(TetAuthEvent):
    """
    AuthzFail[:userid,resource]
    Event for authorisation failure.

    Attributes:
        user_id (Any): Identifier of the user denied access.
        resource (str): Name of the resource denied.
    """

    user_id: tp.Any
    resource: str


# Change password events


@dataclasses.dataclass()
class AuthnPasswordChange(TetAuthEvent):
    """
    AuthnPasswordChange[:authenticated_userid]
    Event for successful password change.

    Attributes:
        authenticated_userid (Any): Identifier of the authenticated user.
    """

    authenticated_userid: tp.Any


@dataclasses.dataclass()
class AuthnPasswordChangeFail(TetAuthEvent):
    """
    AuthnPasswordChangeFail[:authenticated_userid]
    Event for failed password change.

    Attributes:
        authenticated_userid (Any): Identifier of the user.
    """

    authenticated_userid: tp.Any


# Login events


@dataclasses.dataclass()
class AuthnLoginSuccess(TetAuthEvent):
    """
    AuthnLoginSuccess[:userid]
    Event for successful login.

    Attributes:
        user_id (Any): Identifier of the user.
    """

    user_id: tp.Any


@dataclasses.dataclass()
class AuthnLoginFail(TetAuthEvent):
    """
    AuthnLoginFail[:userid]
    Event for failed login attempt.

    Attributes:
        user_id (Any): Identifier of the user.
    """

    user_id: tp.Any


# Logout events


@dataclasses.dataclass()
class AuthnLogoutSuccess(TetAuthEvent):
    """
    AuthnLogoutSuccess[:userid]
    Event for successful logout.

    Attributes:
        user_id (Any): Identifier of the user.
    """

    user_id: tp.Any


@dataclasses.dataclass()
class AuthnLogoutFail(TetAuthEvent):
    """
    AuthnLogoutFail[:userid]
    Event for failed logout.

    Attributes:
        user_id (Any): Identifier of the user.
    """

    user_id: tp.Any


# MFA events


@dataclasses.dataclass()
class AuthnMfaMethodDisabled(TetAuthEvent):
    """
    AuthnMfaMethodDisabled[:authenticated_userid, method]
    Event for successful MFA method disable.

    Attributes:
        authenticated_userid (Any): Identifier of the user.
        method (str): MFA method disabled.
    """

    authenticated_userid: tp.Any
    method: str


@dataclasses.dataclass()
class AuthnMfaMethodDisableFail(TetAuthEvent):
    """
    AuthnMfaMethodDisableFail[:authenticated_userid, method]
    Event for failed MFA method disable.

    Attributes:
        authenticated_userid (Any): Identifier of the user.
        method (str): MFA method attempted.
    """

    authenticated_userid: tp.Any
    method: str


@dataclasses.dataclass()
class AuthnMfaMethodCreated(TetAuthEvent):
    """
    AuthnMfaMethodCreated[:authenticated_userid, method]
    Event for successful creation of an MFA method.

    Attributes:
        authenticated_userid (Any): Identifier of the user.
        method (str): MFA method created.
    """

    authenticated_userid: tp.Any
    method: str


# Token events


@dataclasses.dataclass()
class AuthnRefreshTokensRevoked(TetAuthEvent):
    """
    AuthnRefreshTokensRevoked[:authenticated_userid]
    Event for revoking all refresh tokens.

    Attributes:
        authenticated_userid (Any): Identifier of the user.
    """

    authenticated_userid: tp.Any


@dataclasses.dataclass()
class AuthnRefreshTokenRevokeFail(TetAuthEvent):
    """
    AuthnRefreshTokenRevokeFail[:authenticated_userid]
    Event for failed revocation of all refresh tokens.

    Attributes:
        authenticated_userid (Any): Identifier of the user.
    """

    authenticated_userid: tp.Any


@dataclasses.dataclass()
class AuthnCurrentRefreshTokenRevoked(TetAuthEvent):
    """
    AuthnCurrentRefreshTokenRevoked[:authenticated_userid]
    Event for revoking the current refresh token.

    Attributes:
        authenticated_userid (Any): Identifier of the user.
    """

    authenticated_userid: tp.Any


@dataclasses.dataclass()
class AuthnCurrentRefreshTokenRevokeFail(TetAuthEvent):
    """
    AuthnCurrentRefreshTokenRevokeFail[:authenticated_userid]
    Event for failed revocation of the current refresh token.

    Attributes:
        authenticated_userid (Any): Identifier of the user.
    """

    authenticated_userid: tp.Any


@dataclasses.dataclass()
class AuthnInputValidationFail(TetAuthEvent):
    """
    AuthnInputValidationFail:[(fieldone,fieldtwo...),userid]
    Event for input validation failure during authentication.

    Attributes:
        userid (Any): Identifier of the user.
        fields (List[str]): List of field names that failed validation.
    """

    userid: tp.Any
    fields: tp.List[str]
