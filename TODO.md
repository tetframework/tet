# TODO

## Upstream

- Pyramid depends on `pkg_resources` which was removed in setuptools 82.
  Pin `setuptools<82` until Pyramid releases a fix.

## Security

### TOTP replay protection — DONE
- ~~Add an UNLOGGED PostgreSQL table to track used TOTP time steps per user~~
- Implemented via `TOTPUsedCodeMixin` + `FOR UPDATE` on the MFA method row
- `cleanup_used_codes()` method available for periodic cleanup

### Rate limiting — DONE
- ~~Login endpoint has no rate limiting~~
- Implemented via `RateLimitAttemptMixin` (UNLOGGED table) + `TetRateLimitService`
- Login endpoint rate-limited by client IP (configurable max attempts / window)
- Rate limit records use a separate DB connection to survive transaction rollback
- Extend to refresh, MFA, and password change endpoints as needed

### Token cleanup — DONE
- ~~No mechanism to purge expired long-term tokens~~
- `TetTokenService.cleanup_expired_tokens()` available — call from a cron job or admin endpoint

### Pyramid 2.0 compatibility — DONE
- ~~`NO_PERMISSION_REQUIRED` still imported from `pyramid.security`~~
- Now uses try/except compatibility import (pyramid.authorization → pyramid.security fallback)
- CI matrix tests both Pyramid ~=1.9.0 and ~=2.0

### TOTP secret encryption at rest
- TOTP secrets are stored as plaintext in the `data` JSONB column
- Consider encrypting with an application-level key before storing

### Future rate limiting
- Rate limit token refresh, MFA verify, and password change endpoints
- Per-account rate limiting (in addition to per-IP)

## Input validation
- `create_long_term_token()` — validate `user_id` is not None
- `retrieve_and_validate_token()` — validate token format before DB lookup
- `create_short_term_jwt()` — validate user_id is JSON-serializable

## Architecture

### TOTP verification in PL/pgSQL (future)
- Move TOTP verification into a PL/pgSQL function for fully atomic
  verify + replay check + insert (requires `pgcrypto` for HMAC-SHA1)
- Current approach (Python verify + FOR UPDATE + insert) is safe but
  requires a round trip per step

### Test infrastructure
- Tests depend on a running PostgreSQL instance (`test_tet` database)
- Consider testcontainers or similar for CI portability

## Documentation
- Document why `require_csrf=False` on all auth endpoints (stateless Bearer token auth)
- Document the security model: token lifecycle, MFA flow, cookie handling
- API endpoint documentation (beyond the existing `docs/authentication_apis.md`)
