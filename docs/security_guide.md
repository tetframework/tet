# Security Guide

`tet.security` provides JWT-based authentication, refresh tokens, multi-factor
authentication (TOTP), rate limiting, and password management for Pyramid
applications.  It builds on `pyramid_di` for dependency injection and ships
ready-made views that you can mount under any route prefix.

## Quick start

### 1. Define your models

Your application needs three SQLAlchemy models.  Tet provides mixins for each;
you add the foreign keys and any extra columns.

```python
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base

from tet.security.models import (
    MultiFactorAuthenticationMethodMixin,
    RateLimitAttemptMixin,
    TOTPUsedCodeMixin,
    TokenMixin,
)
from tet.sqlalchemy.password import UserPasswordMixin

Base = declarative_base()


class User(UserPasswordMixin, Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)


class Token(TokenMixin, Base):
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class MultiFactorAuthMethod(MultiFactorAuthenticationMethodMixin, Base):
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class TOTPUsedCode(TOTPUsedCodeMixin, Base):
    """UNLOGGED table -- survives restarts but not crashes."""
    __table_args__ = {"prefixes": ["UNLOGGED"]}
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class RateLimitAttempt(RateLimitAttemptMixin, Base):
    """UNLOGGED table for login rate-limiting."""
    __table_args__ = {"prefixes": ["UNLOGGED"]}
```

`TokenMixin` stores hashed refresh tokens.  `UserPasswordMixin` (from
`tet.sqlalchemy.password`) gives you `password` (a bcrypt-hashed column) and
`validate_password()`.

`TOTPUsedCode` and `RateLimitAttempt` are optional.  Mark them `UNLOGGED` for
performance -- they hold ephemeral data that is safe to lose on a crash.

### 2. Write a login callback

The login callback is where *your* authentication logic lives.  Tet calls it
with the current request; you verify credentials and return an
`AuthLoginResult`:

```python
from pyramid.httpexceptions import HTTPUnauthorized
from tet.security.config import AuthLoginResult

def login_callback(request):
    body = request.json_body
    email = body.get("user_identity", "")
    password = body.get("password", "")

    db = request.find_service(name="db")  # or however you get your session
    user = db.query(User).filter_by(email=email).one_or_none()

    if user is None or not user.validate_password(password):
        return AuthLoginResult(user_id=None, success=False)

    return AuthLoginResult(
        user_id=user.id,
        user_identity=email,
        totp_token=body.get("token"),  # forwarded if the client sent one
        success=True,
    )
```

If MFA is enabled for the user, `tet.security` handles the challenge
automatically -- you just need to pass through the `token` field from the
request body.

### 3. Provide a JWK resolver

The JWK resolver returns the secret used to sign and verify JWTs.  The
simplest case is a shared secret from your settings:

```python
def jwk_resolver(request):
    return request.registry.settings["auth.jwt_secret"]
```

For asymmetric algorithms (RS256, ES256, ...) return the appropriate key
object.

### 4. Wire it up in your Pyramid configuration

```python
from pyramid.config import Configurator
from tet.security.config import (
    CookieAttributes,
    JWTRegisteredClaims,
)


def main(global_config, **settings):
    config = Configurator(settings=settings)

    # Include tet.security -- registers routes, views, and services
    config.include("tet.security.authentication", route_prefix="api/auth")

    # Configure token authentication
    config.set_token_authentication(
        long_term_token_model=Token,
        multi_factor_auth_method_model=MultiFactorAuthMethod,
        user_model=User,
        project_prefix="MYAPP_",
        login_callback=login_callback,
        jwk_resolver=jwk_resolver,
        # Optional -- tune these to your needs:
        jwt_token_expiration_mins=15,
        long_term_token_expiration_mins=720,
        jwt_claims=JWTRegisteredClaims(
            iss="myapp",
            aud="myapp-api",
        ),
        cookie_attributes=CookieAttributes(
            name="refresh-token",
            path="/api/auth/",
            secure=True,
            httponly=True,
            samesite="Strict",
        ),
        # Optional -- pass models to enable, or omit to disable
        totp_used_code_model=TOTPUsedCode,
        rate_limit_model=RateLimitAttempt,
    )

    config.scan()
    return config.make_wsgi_app()
```

That single `config.include` registers all the auth routes and view classes.
`set_token_authentication` stores your models and callbacks on the registry
so the built-in services can find them at request time.


## What you get

After the setup above, the following routes are available (under your chosen
`route_prefix`):

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/login` | Authenticate, return access + refresh tokens |
| POST | `/logout` | Revoke current refresh token |
| POST | `/token/refresh` | Exchange refresh token for new access token |
| POST | `/users/me/password` | Change password (authenticated) |
| DELETE | `/users/me/tokens/others` | Revoke all other refresh tokens |
| POST | `/mfa/app/setup` | Begin TOTP setup (returns QR code) |
| POST | `/mfa/app/verify` | Verify TOTP code to complete setup |
| GET | `/mfa/methods` | List active MFA methods |
| POST | `/mfa/app/disable` | Disable a TOTP method |

All routes except `/login`, `/token/refresh`, and `/logout` require
authentication (the default permission is `"view"`).


## How the token flow works

1. **Login** -- client sends credentials to `/login`.  The login callback
   verifies them.  On success, the server creates a long-term refresh token
   (stored hashed in the database) and a short-lived JWT access token.  The
   refresh token is set as an `HttpOnly` cookie; the access token is returned
   in the JSON body.

2. **Authenticated requests** -- the client sends the access token in the
   `Authorization: Bearer <token>` header.  The `TokenAuthenticationPolicy`
   verifies it on every request that has a `permission` set.

3. **Token refresh** -- when the access token expires, the client calls
   `/token/refresh`.  The refresh token cookie is validated against the
   database and a new access token is issued.

4. **Logout** -- `/logout` deletes the refresh token from the database and
   clears the cookie.


## Multi-factor authentication (TOTP)

TOTP support is built in.  The flow from the client's perspective:

1. **Setup** -- `POST /mfa/app/setup` with `{"method_type": "TOTP"}`.  Returns
   a `secret` and a `qr_code` (base64-encoded SVG).  The user scans the QR
   code with their authenticator app.

2. **Verify** -- `POST /mfa/app/verify` with `{"token": "<6-digit code>"}`.
   If correct, the method is marked active and verified.

3. **Login with MFA** -- when a user with an active TOTP method logs in, the
   first `/login` call returns `{"mfa_required": true}`.  The client then
   re-sends the login request with the `token` field included.

### Replay protection

If you pass a `totp_used_code_model` to `set_token_authentication`, each
time-step is recorded and a code cannot be reused within its validity window.
The model should be an UNLOGGED table for performance.  Call
`TetMultiFactorAuthenticationService.cleanup_used_codes()` periodically to
prune old entries.


## Rate limiting

Pass a `rate_limit_model` to `set_token_authentication` to enable login
rate limiting.  The defaults are 10 attempts per IP address in a 5-minute
window (configurable via `login_rate_limit_max_attempts` and
`login_rate_limit_window_seconds`).

When the limit is exceeded, the login endpoint returns `429 Too Many Requests`.

Rate limit records are written on a separate connection so they survive
transaction rollbacks.  Call `TetRateLimitService.cleanup()` periodically to
prune old entries.


## Events

Every authentication action fires a Pyramid event that you can subscribe to
for logging, auditing, or side effects:

```python
from tet.security.events import AuthnLoginSuccess, AuthnLoginFail

def on_login_success(event):
    log.info("Login: user=%s ip=%s", event.user_identity, event.request.client_addr)

def on_login_fail(event):
    log.warning("Failed login: user=%s ip=%s", event.user_identity, event.request.client_addr)

config.add_subscriber(on_login_success, AuthnLoginSuccess)
config.add_subscriber(on_login_fail, AuthnLoginFail)
```

Available events:

| Event | Fired when |
|-------|-----------|
| `AuthnLoginSuccess` | Successful login |
| `AuthnLoginFail` | Failed login attempt |
| `AuthnLogoutSuccess` | Successful logout |
| `AuthnLogoutFail` | Failed logout |
| `AuthnPasswordChange` | Password changed |
| `AuthnPasswordChangeFail` | Password change failed |
| `AuthnMfaMethodCreated` | New MFA method set up |
| `AuthnMfaMethodDisabled` | MFA method disabled |
| `AuthnRefreshTokensRevoked` | Other refresh tokens revoked |
| `AuthnCurrentRefreshTokenRevoked` | Current refresh token revoked |
| `AuthzFail` | Authorization denied |

All events carry the originating `request` and the relevant user identifier.


## Password validation

`TetAuthService.change_password()` enforces:

- Minimum length of 12 characters, maximum 128
- A strength score (based on length heuristics)
- A check against the [Have I Been Pwned](https://haveibeenpwned.com/Passwords)
  breached passwords API (via k-anonymity -- only a 5-character SHA-1 prefix
  is sent)

Configure the API URL in your settings:

```ini
pwned_passwords_api_url = https://api.pwnedpasswords.com/range/
```


## Customising the security policy

The default `TokenAuthenticationPolicy` reads the JWT from the `Authorization`
header and resolves principals as `[Everyone]` (unauthenticated) or
`[Everyone, "user:<id>", Authenticated]`.

To add custom principals (roles, groups), subclass and override
`effective_principals`:

```python
from tet.security.policy import TokenAuthenticationPolicy

class MyPolicy(TokenAuthenticationPolicy):
    def effective_principals(self, request):
        principals = super().effective_principals(request)
        user_id = self.authenticated_userid(request)
        if user_id is not None:
            # Add roles from your database, cache, etc.
            principals.extend(get_user_roles(request, user_id))
        return principals
```

Pass your custom policy to `set_token_authentication`:

```python
config.set_token_authentication(
    ...,
    security_policy=MyPolicy(),
)
```


## Services

The following services are registered and available via `request.find_service()`:

- **`TetTokenService`** -- create/validate long-term tokens, create/verify JWTs,
  delete tokens, clean up expired tokens.
- **`TetAuthService`** -- cookie management, password change/validation, user
  lookup.
- **`TetMultiFactorAuthenticationService`** -- TOTP setup, verification,
  method management, replay protection.
- **`TetRateLimitService`** -- rate limit checking and cleanup.

All are request-scoped.  In your own services, inject them with `autowired()`:

```python
from pyramid_di import RequestScopedBaseService, autowired
from tet.security.tokens import TetTokenService

class MyService(RequestScopedBaseService):
    token_service: TetTokenService = autowired(TetTokenService)

    def do_something(self):
        jwt = self.token_service.create_short_term_jwt(user_id=42)
        ...
```


## Settings reference

All settings are passed to `set_token_authentication()`.  The only ones that
are required have no default:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `long_term_token_model` | *(required)* | SQLAlchemy model using `TokenMixin` |
| `multi_factor_auth_method_model` | *(required)* | Model using `MultiFactorAuthenticationMethodMixin` |
| `user_model` | *(required)* | Your user model (must have `id`, `validate_password()`, `display_name`) |
| `project_prefix` | *(required)* | Prefix for long-term token strings (e.g. `"MYAPP_"`) |
| `login_callback` | *(required)* | Callable `(request) -> AuthLoginResult` |
| `jwk_resolver` | *(required)* | Callable `(request) -> str | dict` returning the JWT signing key |
| `jwt_algorithm` | `"HS256"` | JWT signing algorithm |
| `jwt_token_expiration_mins` | `15` | Access token lifetime in minutes |
| `long_term_token_expiration_mins` | `720` | Refresh token lifetime in minutes (12 hours) |
| `authorization_header` | `"Authorization"` | Header name for access tokens |
| `long_term_token_cookie_name` | `"refresh-token"` | Cookie name for refresh tokens |
| `jwt_claims` | `JWTRegisteredClaims()` | Default registered claims for JWTs |
| `cookie_attributes` | `None` | `CookieAttributes` for refresh token cookies |
| `security_policy` | `TokenAuthenticationPolicy()` | The Pyramid security policy |
| `totp_used_code_model` | `None` | Model for TOTP replay protection (enables if set) |
| `rate_limit_model` | `None` | Model for rate limiting (enables if set) |
| `login_rate_limit_max_attempts` | `10` | Max login attempts per key in window |
| `login_rate_limit_window_seconds` | `300` | Rate limit window (seconds) |
