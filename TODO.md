# TODO

## Upstream

- Pyramid depends on `pkg_resources` which was removed in setuptools 82.
  Pin `setuptools<82` until Pyramid releases a fix.

## Remaining improvements

### Input validation
- `create_long_term_token()` — validate `user_id` is not None
- `retrieve_and_validate_token()` — validate token format before DB lookup
- `create_short_term_jwt()` — validate user_id is JSON-serializable

### Documentation
- Document why `require_csrf=False` on all auth endpoints (stateless Bearer token auth)
- Consider rate limiting guidance in docs (login, refresh, MFA endpoints)
