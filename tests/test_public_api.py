"""
Public API contract tests.

Every symbol listed here is part of the published API.  If an import
fails or a type check breaks, a downstream consumer's code would break
too — fix the library, not this test.
"""

import dataclasses
import enum
import types

import pytest
from pyramid.request import Request


# ── tet.security (package) ──────────────────────────────────────────

def test_tet_security_exports():
    from tet.security import (
        Allowed,
        AuthLoginResult,
        AuthViews,
        CookieAttributes,
        Denied,
        ILoginCallback,
        ISecretCallback,
        JWTRegisteredClaims,
        MultiFactorAuthMethodType,
        MultiFactorAuthenticationMethodMixin,
        NO_PERMISSION_REQUIRED,
        PasswordChangeData,
        TetAuthService,
        TetMultiFactorAuthenticationService,
        TetTokenService,
        TOTPData,
        TokenAuthenticationPolicy,
        TokenMixin,
    )

    assert dataclasses.is_dataclass(AuthLoginResult)
    assert dataclasses.is_dataclass(CookieAttributes)
    assert dataclasses.is_dataclass(JWTRegisteredClaims)
    assert dataclasses.is_dataclass(PasswordChangeData)
    assert dataclasses.is_dataclass(TOTPData)
    assert issubclass(MultiFactorAuthMethodType, enum.Enum)
    assert isinstance(NO_PERMISSION_REQUIRED, str)


# ── tet.security.authentication ─────────────────────────────────────

def test_tet_security_authentication_exports():
    from tet.security.authentication import (
        AuthLoginResult,
        AuthViews,
        CookieAttributes,
        ILoginCallback,
        ISecretCallback,
        JWTRegisteredClaims,
        MultiFactorAuthMethodType,
        MultiFactorAuthenticationMethodMixin,
        NO_PERMISSION_REQUIRED,
        PasswordChangeData,
        RateLimitAttemptMixin,
        TetAuthService,
        TetMultiFactorAuthenticationService,
        TetRateLimitService,
        TetTokenService,
        TOTPData,
        TOTPUsedCodeMixin,
        TokenAuthenticationPolicy,
        TokenMixin,
        includeme,
        set_token_authentication,
    )

    assert callable(includeme)
    assert callable(set_token_authentication)


# ── tet.security.authorization ───────────────────────────────────────

def test_tet_security_authorization_exports():
    from tet.security.authorization import (
        ACLHelper,
        Allow,
        Allowed,
        Authenticated,
        AuthorizationPolicyWrapper,
        Denied,
        Deny,
        Everyone,
        INewAuthorizationPolicy,
        NO_PERMISSION_REQUIRED,
        includeme,
    )

    assert callable(includeme)


# ── tet.security.compat ──────────────────────────────────────────────

def test_tet_security_compat_exports():
    from tet.security.compat import (
        ACLHelper,
        ALL_PERMISSIONS,
        Allow,
        Allowed,
        Authenticated,
        DENY_ALL,
        Denied,
        Deny,
        Everyone,
        NO_PERMISSION_REQUIRED,
    )

    assert isinstance(NO_PERMISSION_REQUIRED, str)


# ── tet.security.events ─────────────────────────────────────────────

def test_tet_security_events_exports():
    from tet.security.events import (
        AuthnCurrentRefreshTokenRevokeFail,
        AuthnCurrentRefreshTokenRevoked,
        AuthnInputValidationFail,
        AuthnLoginFail,
        AuthnLoginSuccess,
        AuthnLogoutFail,
        AuthnLogoutSuccess,
        AuthnMfaMethodCreated,
        AuthnMfaMethodDisableFail,
        AuthnMfaMethodDisabled,
        AuthnPasswordChange,
        AuthnPasswordChangeFail,
        AuthnRefreshTokenRevokeFail,
        AuthnRefreshTokensRevoked,
        AuthzFail,
        TetAuthEvent,
    )

    assert dataclasses.is_dataclass(TetAuthEvent)
    for cls in (
        AuthnLoginSuccess,
        AuthnLoginFail,
        AuthnLogoutSuccess,
        AuthnLogoutFail,
        AuthnPasswordChange,
        AuthnPasswordChangeFail,
        AuthnMfaMethodCreated,
        AuthnMfaMethodDisabled,
        AuthnMfaMethodDisableFail,
        AuthnRefreshTokensRevoked,
        AuthnRefreshTokenRevokeFail,
        AuthnCurrentRefreshTokenRevoked,
        AuthnCurrentRefreshTokenRevokeFail,
        AuthzFail,
        AuthnInputValidationFail,
    ):
        assert dataclasses.is_dataclass(cls), f"{cls.__name__} is not a dataclass"


# ── tet.security.models ─────────────────────────────────────────────

def test_tet_security_models_exports():
    from tet.security.models import (
        MultiFactorAuthenticationMethodMixin,
        RateLimitAttemptMixin,
        TOTPUsedCodeMixin,
        TokenMixin,
    )

    for mixin in (
        MultiFactorAuthenticationMethodMixin,
        RateLimitAttemptMixin,
        TOTPUsedCodeMixin,
        TokenMixin,
    ):
        assert hasattr(mixin, "__tablename__"), f"{mixin.__name__} missing __tablename__"


# ── tet.security.config (dataclasses & enums) ───────────────────────

def test_tet_security_config_exports():
    from tet.security.config import (
        AuthLoginResult,
        CookieAttributes,
        ILoginCallback,
        ISecretCallback,
        JWTRegisteredClaims,
        MultiFactorAuthMethodType,
        PasswordChangeData,
        TOTPData,
    )

    claims = JWTRegisteredClaims()
    assert isinstance(claims.to_dict(), dict)

    cookie = CookieAttributes()
    assert cookie.secure is True
    assert cookie.httponly is True

    totp = TOTPData(secret="JBSWY3DPEHPK3PXP", issuer="test")
    assert isinstance(totp.to_dict(), dict)

    result = AuthLoginResult(user_id=None)
    assert not bool(result)

    assert MultiFactorAuthMethodType.TOTP.value == "totp"


# ── tet.security.policy ─────────────────────────────────────────────

def test_tet_security_policy_exports():
    from tet.security.policy import TokenAuthenticationPolicy

    policy = TokenAuthenticationPolicy()
    assert callable(getattr(policy, "authenticated_userid", None))
    assert callable(getattr(policy, "permits", None))
    assert callable(getattr(policy, "effective_principals", None))
    assert callable(getattr(policy, "forget", None))


# ── Service classes ──────────────────────────────────────────────────

def test_service_classes_importable():
    from tet.security.tokens import TetTokenService
    from tet.security.auth import TetAuthService
    from tet.security.mfa import TetMultiFactorAuthenticationService
    from tet.security.rate_limit import TetRateLimitService

    for svc in (TetTokenService, TetAuthService, TetMultiFactorAuthenticationService, TetRateLimitService):
        assert isinstance(svc, type), f"{svc} is not a class"
