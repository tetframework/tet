# Changes


2026-06-17  Antti Haapala  <antti.haapala@anttipatterns.com>

    * 0.6a2: Add ``tet.security`` module with JWT-based authentication,
      refresh tokens, TOTP multi-factor authentication, login rate limiting,
      password management, and Pyramid security policy integration.
      Installable via the ``tet[security]`` extra.
    * New SQLAlchemy model mixins: ``TokenMixin``,
      ``MultiFactorAuthenticationMethodMixin``, ``TOTPUsedCodeMixin``,
      ``RateLimitAttemptMixin``.
    * Pyramid 2.0 compatibility for security/authorization imports.
    * Auth views registered via ``config.include("tet.security.authentication")``.
    * Event system for login, logout, password change, MFA, and token
      revocation (``tet.security.events``).
    * TOTP replay protection via UNLOGGED tables.
    * Login rate limiting by client IP.
    * Breached password checking via Have I Been Pwned API (k-anonymity).
    * Drop Python 3.8, 3.9 support. Require Python >= 3.10.


2026-06-16  Antti Haapala  <antti.haapala@anttipatterns.com>

    * 0.6a1: first 0.6 alpha. Migrated to a ``src/`` layout and replaced
      ``setup.py``/``setup.cfg`` with ``pyproject.toml``. PyPI publishing now
      uses OIDC trusted publishing via ``release.yml`` (no API token). Fixed
      ``Base64``/``CrockfordBase32.generate_characters`` to use ``secrets``.


2026-05-28  Antti Haapala  <antti.haapala@anttipatterns.com>

    * 0.5.0: ``tet.services`` now re-exports ``service``,
      ``RequestScopedBaseService``, ``ApplicationScopedBaseService``,
      ``BaseService`` and ``autowired`` from ``pyramid_di``. Application
      code should import these from ``tet.services`` rather than reaching
      into ``pyramid_di`` directly.


2025-01-28  Antti Haapala  <antti.haapala@anttipatterns.com>

    * Add Python 3.12, 3.13, 3.14 support. Drop Python 3.6, 3.7 support.
    * Add Sphinx documentation and ReadTheDocs integration.

2021-03-19  Antti Haapala  <antti.haapala@anttipatterns.com>

    * The tet.di request scoped services are now truly instantiated per request!

2016-08-19  Antti Haapala  <antti.haapala@anttipatterns.com>

    * SQLAlchemy root factory now gives NotFound on DataError; made into a implicit-namespace package;
      fixed backports.typing to greater than or equal to 1.1.

2013-09-07  Antti Haapala  <antti.haapala@anttipatterns.com>

    * renamed the package to `tet`
