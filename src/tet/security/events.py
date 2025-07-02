import dataclasses
import typing as tp

from pyramid.request import Request

__all__ = [
    "TetAuthEvent",
    "ChangePasswordSuccessEvent",
    "ChangePasswordFailedEvent",
    "LoginSuccessEvent",
    "LoginFailedEvent",
    "MfaLoginSuccessEvent",
    "MfaLoginFailedEvent",
    "LogoutSuccessEvent",
    "LogoutFailedEvent",
    "DisableMfaSuccessEvent",
    "DisableMfaFailedEvent",
    "RevokeOtherRefreshTokensSuccessEvent",
    "RevokeOtherRefreshTokensFailedEvent",
    "RevokeCurrentRefreshTokensSuccessEvent",
    "RevokeCurrentRefreshTokensFailedEvent",
    "CreateTotpMethodSuccessEvent",
]


@dataclasses.dataclass(kw_only=True, slots=True)
class TetAuthEvent:
    request: Request
    extra_fields: tp.Dict[str, tp.Any] = dataclasses.field(default_factory=dict)


# Change password events
@dataclasses.dataclass()
class ChangePasswordSuccessEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class ChangePasswordFailedEvent(TetAuthEvent):
    pass


# Login events
@dataclasses.dataclass()
class LoginSuccessEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class LoginFailedEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class MfaLoginSuccessEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class MfaLoginFailedEvent(TetAuthEvent):
    pass


# Logout events
@dataclasses.dataclass()
class LogoutSuccessEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class LogoutFailedEvent(TetAuthEvent):
    pass


# MFA events
@dataclasses.dataclass()
class DisableMfaSuccessEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class DisableMfaFailedEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class CreateTotpMethodSuccessEvent(TetAuthEvent):
    pass


# Token events
@dataclasses.dataclass()
class RevokeOtherRefreshTokensSuccessEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class RevokeOtherRefreshTokensFailedEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class RevokeCurrentRefreshTokensSuccessEvent(TetAuthEvent):
    pass


@dataclasses.dataclass()
class RevokeCurrentRefreshTokensFailedEvent(TetAuthEvent):
    pass
