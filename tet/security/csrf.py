"""
CSRF token protection for Tet applications.

This module enables CSRF (Cross-Site Request Forgery) protection by default.
It is included automatically when using the ``security.csrf`` feature.

When enabled, all state-changing requests (POST, PUT, DELETE, etc.) require
a valid CSRF token.

Example
-------

Enabling CSRF protection::

    from tet.config import application_factory

    @application_factory(included_features=["security.csrf"])
    def main(config):
        config.add_route("home", "/")
        config.scan()

In templates, include the CSRF token in forms::

    <form method="POST">
        <input type="hidden" name="csrf_token"
               value="${request.session.get_csrf_token()}">
        <!-- form fields -->
    </form>
"""
from pyramid.config import Configurator


def includeme(config: Configurator) -> None:
    """
    Pyramid includeme that enables CSRF protection by default.

    All state-changing requests will require a valid CSRF token.
    """
    config.set_default_csrf_options(require_csrf=True)