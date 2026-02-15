# TODO: JWT Token Auth PR

## Critical — must fix before merge

### Remove `JWTCookieAuthenticationPolicy`
- Remove the entire `JWTCookieAuthenticationPolicy` class and related code
- JWT access tokens belong in `Authorization: Bearer` header only, never in cookies
- Putting JWT in a cookie requires CSRF protection (currently disabled!) and defeats
  the purpose of bearer tokens
- Only the **refresh token** belongs in a cookie (httpOnly, secure)
- Remove `COOKIE_LOGIN_VIEW` and any views/config that wire up cookie-based JWT auth

### Fix cookie defaults
- `CookieAttributes` must default to `httponly=True` and `secure=True`
- Current defaults (`False`/`False`) completely defeat the security benefit of
  storing the refresh token in a cookie (XSS protection)
- Consider adding a development mode that allows `secure=False` for localhost

### Fix shared mutable JWT claims object
- `create_short_term_jwt()` does `payload = self.jwt_claims` — this is a reference,
  not a copy, then mutates `user_id`, `iat`, `exp` on it
- Thread-unsafe: concurrent requests will corrupt each other's claims
- Fix: use `dataclasses.replace(self.jwt_claims)` or `copy.deepcopy()`
- Same issue with `DEFAULT_REGISTERED_CLAIMS`, `DEFAULT_COOKIE_ATTRIBUTES`,
  `DEFAULT_SECURITY_POLICY` — shared mutable instances

### Fix JWT exception handling
- `verify_jwt()` only catches `jwt.ExpiredSignatureError`
- `InvalidSignatureError`, `DecodeError`, `InvalidAudienceError`, `InvalidIssuerError`
  etc. will crash instead of returning `None`
- Catch `jwt.InvalidTokenError` (base class for all PyJWT exceptions)

### Add timeout to password breach API
- `requests.get(url)` in `is_password_breached()` has no timeout
- If Pwned Passwords API is down, the entire password change flow hangs
- Add `timeout=5` and wrap in try/except with graceful degradation:
  ```python
  try:
      response = requests.get(url, timeout=5)
      response.raise_for_status()
  except requests.RequestException:
      logger.warning("Password breach check unavailable")
      return False
  ```

## High priority

### Split `authentication.py` (1457 lines)
- This single file contains token service, auth service, MFA service, views,
  config dataclasses, security policies, and Pyramid configuration
- Suggested split:
  - `tet/security/config.py` — dataclasses (`CookieAttributes`, `JWTRegisteredClaims`, etc.)
  - `tet/security/tokens.py` — `TetTokenService` (create/validate tokens)
  - `tet/security/auth.py` — `TetAuthService` (password verification, breach check)
  - `tet/security/mfa.py` — `TetMFAService` (TOTP setup/verification)
  - `tet/security/views.py` — `AuthViews` (login, logout, refresh, MFA endpoints)
  - `tet/security/policy.py` — `TokenAuthenticationPolicy`
  - `tet/security/authentication.py` — top-level `includeme()` wiring it all together

### Add missing tests
- Invalid JWT signature → should return `None`, not crash
- Expired JWT → should return `None`
- Malformed/garbage token → should return `None`
- Missing refresh token cookie → should return 401
- Breach API timeout/failure → should degrade gracefully
- Concurrent token creation → verify no shared state corruption

### Input validation
- `create_long_term_token()` — validate `user_id` is not None
- `retrieve_and_validate_token()` — validate token format before DB lookup
- `create_short_term_jwt()` — validate user_id is JSON-serializable

## Minor

- Typo: "credientials" → "credentials" in `DEFAULT_UNAUTHORIZED_MESSAGE`
- Magic numbers (token ID length `8`, hash prefix `[:5]`) should be named constants
- Document why `require_csrf=False` on all auth endpoints (stateless Bearer token auth)
- Consider rate limiting guidance in docs (login, refresh, MFA endpoints)
