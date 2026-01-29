"""
Tet - Unearthly intelligent batteries-included application framework built on Pyramid.

Tet provides a set of utilities and conventions for building web applications
with Pyramid, including:

- Configuration helpers via :func:`tet.config.create_configurator` and
  :func:`tet.config.application_factory`
- JSON rendering with custom type adapters
- Tonnikala template integration
- SQLAlchemy session management
- Security utilities (CSRF protection, authorization)
- Internationalization support
- Various utility functions

Example usage::

    from tet.config import application_factory, ALL_FEATURES

    @application_factory(included_features=ALL_FEATURES)
    def main(config):
        config.add_route('home', '/')
        config.scan()
"""
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

