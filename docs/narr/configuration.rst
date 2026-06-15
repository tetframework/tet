=============
Configuration
=============

Tet provides enhanced configuration capabilities that extend Pyramid's configuration system with additional directives and conveniences.

Basic Configuration
==================

Tet modules are configured through Pyramid's ``Configurator`` using the ``include`` directive.

Application Factory Pattern
---------------------------

Tet uses an application factory decorator that automatically configures features:

.. code-block:: python

    from tet.config import application_factory, ALL_FEATURES, MINIMAL_FEATURES

    @application_factory(included_features=ALL_FEATURES)
    def main(config):
        """Tet application factory."""
        # Your application configuration
        config.add_route('home', '/')
        config.scan()

    # Or with minimal features
    @application_factory(included_features=MINIMAL_FEATURES)
    def minimal_main(config):
        """Minimal Tet application."""
        config.include('tet.renderers.json')  # Add features manually
        config.add_route('api', '/api')

Available Features
------------------

Tet provides predefined feature sets:

* ``ALL_FEATURES``: All Tet features enabled
* ``MINIMAL_FEATURES``: No features (empty list)

Individual features can be included:

* ``"services"`` - Service configuration
* ``"i18n"`` - Internationalization support
* ``"renderers.json"`` - Enhanced JSON renderer
* ``"renderers.tonnikala"`` - Tonnikala template renderer
* ``"renderers.tonnikala.i18n"`` - Tonnikala with i18n
* ``"security.authorization"`` - Enhanced authorization
* ``"security.csrf"`` - CSRF protection

Manual Configuration
--------------------

For fine-grained control, create the configurator manually:

.. code-block:: python

    from tet.config import create_configurator

    def main(global_config, **settings):
        config = create_configurator(
            global_config=global_config,
            settings=settings,
            included_features=['renderers.json', 'security.csrf'],
            excluded_features=['i18n']
        )

        # Your configuration
        config.add_route('home', '/')
        config.scan()

        return config.make_wsgi_app()

Configuration Directives
========================

Tet adds several custom configuration directives to enhance Pyramid's functionality.

JSON Renderer Directives
------------------------

**add_json_renderer**
  Register a custom JSON renderer:

.. code-block:: python

    from pyramid.renderers import JSON

    # Create custom renderer
    api_renderer = JSON()

    # Register with custom name
    config.add_json_renderer(
        renderer=api_renderer,
        name='api_json'
    )

**add_json_adapter**
  Register a type adapter for JSON serialization:

.. code-block:: python

    from decimal import Decimal

    def decimal_adapter(obj, request):
        return str(obj)

    config.add_json_adapter(
        for_=Decimal,
        adapter=decimal_adapter,
        renderer='json'  # Optional, defaults to 'json'
    )

Authorization Directive
----------------------

**set_authorization_policy**
  Enhanced authorization policy registration that supports Tet's ``INewAuthorizationPolicy``:

.. code-block:: python

    from tet.security.authorization import INewAuthorizationPolicy

    # Your custom authorization policy
    policy = MyAuthorizationPolicy()

    # Register with enhanced support
    config.set_authorization_policy(policy)

Module Configuration
===================

Individual Tet modules can be configured with specific options.

CSRF Configuration
-----------------

The CSRF module sets secure defaults but can be customized:

.. code-block:: python

    def main(global_config, **settings):
        with Configurator(settings=settings) as config:
            # Include CSRF with custom options
            config.include('tet.security.csrf')

            # Override CSRF settings if needed
            config.set_default_csrf_options(
                require_csrf=True,
                token='csrf_token',
                header='X-CSRF-Token'
            )

            return config.make_wsgi_app()

JSON Renderer Configuration
---------------------------

Customize the JSON renderer behavior:

.. code-block:: python

    from pyramid.renderers import JSON

    def main(global_config, **settings):
        with Configurator(settings=settings) as config:
            # Include JSON renderer
            config.include('tet.renderers.json')

            # Add custom adapters
            config.add_json_adapter(
                for_=MyModel,
                adapter=lambda obj, req: obj.to_dict()
            )

            # Create specialized renderer
            api_renderer = JSON(sort_keys=True, indent=2)
            config.add_json_renderer(
                renderer=api_renderer,
                name='pretty_json'
            )

            return config.make_wsgi_app()

Settings Integration
===================

Tet modules respect Pyramid's settings system for configuration.

Database Settings
----------------

Configure SQLAlchemy integration through settings:

.. code-block:: ini

    # development.ini
    [app:main]
    use = egg:myapp

    # Database configuration
    sqlalchemy.url = postgresql://user:pass@localhost/myapp
    sqlalchemy.pool_size = 10
    sqlalchemy.max_overflow = 20

    # Session configuration
    session.secret = your-secret-key-here
    session.cookie_httponly = true
    session.cookie_secure = true

Security Settings
----------------

Configure security-related settings:

.. code-block:: ini

    # production.ini
    [app:main]
    # CSRF settings
    csrf.secret = different-secret-for-csrf
    csrf.timeout = 7200

    # Authorization settings
    auth.policy = myapp.security.AuthPolicy
    auth.secret = auth-signing-secret

Application Settings
-------------------

Access settings in your application code:

.. code-block:: python

    def my_view(request):
        settings = request.registry.settings

        # Access configuration values
        database_url = settings.get('sqlalchemy.url')
        debug_mode = settings.get('debug', False)

        return {'debug': debug_mode}

Environment Configuration
========================

Tet applications can be configured for different environments.

Development Configuration
-------------------------

.. code-block:: python

    # development.py
    def main(global_config, **settings):
        # Development-specific settings
        settings.update({
            'debug': True,
            'reload_templates': True,
            'sqlalchemy.echo': True,
        })

        with Configurator(settings=settings) as config:
            config.include('tet.security.csrf')
            config.include('tet.renderers.json')

            # Development-only includes
            if settings.get('debug'):
                config.include('pyramid_debugtoolbar')

            return config.make_wsgi_app()

Production Configuration
-----------------------

.. code-block:: python

    # production.py
    def main(global_config, **settings):
        # Production-specific settings
        settings.update({
            'debug': False,
            'reload_templates': False,
            'session.secure': True,
            'session.httponly': True,
        })

        with Configurator(settings=settings) as config:
            config.include('tet.security.csrf')
            config.include('tet.security.authorization')
            config.include('tet.renderers.json')

            # Production-only security
            config.set_default_csrf_options(require_csrf=True)

            return config.make_wsgi_app()

Testing Configuration
--------------------

.. code-block:: python

    # testing.py
    def main(global_config, **settings):
        # Testing-specific settings
        settings.update({
            'debug': True,
            'sqlalchemy.url': 'sqlite:///:memory:',
            'csrf.disable': True,  # Disable CSRF for easier testing
        })

        with Configurator(settings=settings) as config:
            config.include('tet.renderers.json')

            # Conditional CSRF inclusion
            if not settings.get('csrf.disable'):
                config.include('tet.security.csrf')

            return config.make_wsgi_app()

Advanced Configuration
=====================

Complex configuration scenarios and patterns.

Factory Configuration
--------------------

Configure root factories and other components:

.. code-block:: python

    from tet.sqlalchemy.factory import SQLARootFactory

    class MyRootFactory(SQLARootFactory):
        def supplier(self, item):
            # Implementation here
            pass

    def main(global_config, **settings):
        with Configurator(settings=settings) as config:
            # Set custom root factory
            config.set_root_factory(MyRootFactory)

            # Configure based on settings
            if settings.get('use_traversal'):
                config.add_route('api', '/api/*traverse')
            else:
                config.add_route('api', '/api/{action}')

            return config.make_wsgi_app()

Service Configuration
--------------------

Configure services with pyramid_di:

.. code-block:: python

    from pyramid_di import service

    @service(name='mailer', scope='singleton')
    def create_mailer(settings):
        smtp_host = settings.get('mail.smtp.host', 'localhost')
        return MailerService(smtp_host)

    def main(global_config, **settings):
        with Configurator(settings=settings) as config:
            config.include('pyramid_di')
            config.include('tet.renderers.json')

            # Services are automatically available
            return config.make_wsgi_app()

Configuration Validation
========================

Validate configuration to catch errors early.

Settings Validation
-------------------

.. code-block:: python

    def validate_settings(settings):
        """Validate required settings."""
        required = [
            'sqlalchemy.url',
            'session.secret',
        ]

        missing = [key for key in required if not settings.get(key)]
        if missing:
            raise ValueError(f"Missing required settings: {missing}")

        # Validate specific values
        if len(settings.get('session.secret', '')) < 32:
            raise ValueError("session.secret must be at least 32 characters")

    def main(global_config, **settings):
        # Validate configuration early
        validate_settings(settings)

        with Configurator(settings=settings) as config:
            # Configuration continues...
            return config.make_wsgi_app()

Configuration Utilities
=======================

Helper functions for configuration management.

Settings Helper
---------------

.. code-block:: python

    def get_settings_helper(settings):
        """Create a helper for accessing settings."""

        class SettingsHelper:
            def __init__(self, settings):
                self.settings = settings

            def get_bool(self, key, default=False):
                value = self.settings.get(key, default)
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)

            def get_int(self, key, default=0):
                return int(self.settings.get(key, default))

            def get_list(self, key, separator=',', default=None):
                value = self.settings.get(key, default or [])
                if isinstance(value, str):
                    return [item.strip() for item in value.split(separator)]
                return value

        return SettingsHelper(settings)

Configuration Profiles
=====================

Managing different configuration profiles.

Profile System
--------------

.. code-block:: python

    PROFILES = {
        'development': {
            'debug': True,
            'sqlalchemy.echo': True,
            'reload_templates': True,
        },
        'testing': {
            'debug': True,
            'sqlalchemy.url': 'sqlite:///:memory:',
            'csrf.disable': True,
        },
        'production': {
            'debug': False,
            'session.secure': True,
            'session.httponly': True,
        }
    }

    def main(global_config, **settings):
        # Load profile-specific settings
        profile = settings.get('profile', 'development')
        profile_settings = PROFILES.get(profile, {})

        # Merge settings with profile taking precedence
        final_settings = {**settings, **profile_settings}

        with Configurator(settings=final_settings) as config:
            # Configure based on merged settings
            return config.make_wsgi_app()

Best Practices
=============

**Validate Early**
  Validate configuration at application startup to catch errors early.

**Use Environment Variables**
  Use environment variables for sensitive configuration like secrets and API keys.

**Profile-Based Configuration**
  Use configuration profiles for different environments.

**Document Settings**
  Document all configuration options and their effects.

**Secure Defaults**
  Use secure defaults and require explicit configuration for less secure options.

**Modular Configuration**
  Keep configuration modular and only include what you need.

**Settings Helpers**
  Create helper functions for common configuration patterns like boolean conversion.

**Configuration Testing**
  Test your configuration validation and different configuration scenarios.
