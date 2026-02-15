import typing as tp

from pyramid.config import Configurator
from pyramid.security import NO_PERMISSION_REQUIRED
from zope.interface import Interface

from tet.security.config import (
    AuthLoginResult,
    CookieAttributes,
    ILoginCallback,
    ISecretCallback,
    JWTRegisteredClaims,
    MultiFactorAuthMethodType,
    PasswordChangeData,
    TOTPData,
    DEFAULT_JWT_ALGORITHM,
    DEFAULT_JWT_TOKEN_EXPIRATION_MINS,
    DEFAULT_LONG_TERM_TOKEN_EXPIRATION_MINS,
    DEFAULT_USER_ID_COLUMN,
    DEFAULT_LONG_TERM_TOKEN_NAME,
    DEFAULT_AUTHORIZATION_HEADER,
    DEFAULT_REFRESH_TOKEN_COOKIE_NAME,
    DEFAULT_REGISTERED_CLAIMS,
    DEFAULT_LOGIN_ATTR,
)
from tet.security.models import (
    MultiFactorAuthenticationMethodMixin,
    TokenMixin,
)
from tet.security.policy import TokenAuthenticationPolicy
from tet.security.tokens import TetTokenService
from tet.security.auth import TetAuthService
from tet.security.mfa import TetMultiFactorAuthenticationService
from tet.security.views import AuthViews

__all__ = [
    "AuthLoginResult",
    "AuthViews",
    "CookieAttributes",
    "ILoginCallback",
    "ISecretCallback",
    "JWTRegisteredClaims",
    "MultiFactorAuthMethodType",
    "MultiFactorAuthenticationMethodMixin",
    "PasswordChangeData",
    "TetAuthService",
    "TetMultiFactorAuthenticationService",
    "TetTokenService",
    "TOTPData",
    "TokenAuthenticationPolicy",
    "TokenMixin",
]

DEFAULT_SECURITY_POLICY = TokenAuthenticationPolicy()


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
    authorization_header: str = DEFAULT_AUTHORIZATION_HEADER,
    long_term_token_header: str = DEFAULT_LONG_TERM_TOKEN_NAME,
    long_term_token_cookie_name: str = DEFAULT_REFRESH_TOKEN_COOKIE_NAME,
    jwt_claims: JWTRegisteredClaims = DEFAULT_REGISTERED_CLAIMS,
    cookie_attributes: tp.Optional[CookieAttributes] = None,
    security_policy: tp.Optional[type["TokenAuthenticationPolicy"]] = DEFAULT_SECURITY_POLICY,
) -> None:
    """
    Configure token-based authentication for a Pyramid application (with conflict detection).

    Args:
        config: The current Pyramid :class:`pyramid.config.Configurator` instance.
        long_term_token_model: A token model class or object representing user tokens.
        multi_factor_auth_method_model: A model class for storing MFA methods.
        user_model: The user model class.
        project_prefix: A project-specific prefix (could be used for namespacing).
        login_callback: A callable to verify user credentials/status from the database.
        jwk_resolver: A callable that returns a secret key or keys for token signing.
        user_id_column: Column name or attribute for user ID in the token model.
        jwt_algorithm: The JWT algorithm to use (default: ``"HS256"``).
        jwt_token_expiration_mins: JWT expiration time in minutes (default: 15).
        long_term_token_expiration_mins: Long-term token expiration in minutes (default: 720).
        authorization_header: The header name for the access token.
        long_term_token_header: The header name for the long-term token.
        long_term_token_cookie_name: Cookie name for the refresh token.
        jwt_claims: Default JWT registered claims to include in the token payload.
        cookie_attributes: Optional cookie attributes for refresh token cookies.
        security_policy: A security policy instance to use for token authentication.
    """

    def register():
        config.registry.tet_auth_long_term_token_model = long_term_token_model
        config.registry.tet_multi_factor_auth_method_model = multi_factor_auth_method_model
        config.registry.tet_auth_user_model = user_model
        config.registry.tet_auth_project_prefix = project_prefix
        config.registry.tet_auth_user_id_column = user_id_column
        config.registry.tet_authz_header = authorization_header
        config.registry.tet_auth_long_term_token_header = long_term_token_header
        config.registry.tet_auth_long_term_token_cookie_name = long_term_token_cookie_name
        config.registry.tet_auth_jwt_claims = jwt_claims
        config.registry.tet_auth_cookie_attributes = cookie_attributes

        config.registry.tet_auth_login_callback = login_callback
        config.registry.tet_auth_jwk_resolver = jwk_resolver
        config.registry.tet_auth_jwt_algorithm = jwt_algorithm
        config.registry.tet_auth_jwt_expiration_mins = jwt_token_expiration_mins
        config.registry.tet_auth_long_term_token_expiration_mins = long_term_token_expiration_mins
        config.registry.tet_auth_security_policy = security_policy

    config.action(discriminator="set_token_authentication", callable=register)

    config.set_security_policy(security_policy)


def includeme(config: Configurator):
    """Routes and stuff to register maybe under a prefix"""
    config.registry.tet_auth_route_prefix = config.route_prefix or ""

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
