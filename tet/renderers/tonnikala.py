"""
Tonnikala template engine integration for Tet applications.

This module integrates the Tonnikala template engine with Pyramid.
It is included automatically when using the ``renderers.tonnikala`` feature.

Features
--------

- Automatic ``.tk`` extension registration
- Optional i18n/l10n support via :func:`i18n` includeme

Template Syntax
---------------

Tonnikala uses ``$`` for expression interpolation. The ``$`` does not
necessarily require braces ``{}`` - it will resolve a continuous chain
of attribute access, method calls, and indexing as a single expression::

    $name                     <!-- simple variable -->
    $user.name                <!-- attribute access -->
    $user.get_full_name()     <!-- method call -->
    $items[0].title           <!-- indexing and attribute -->
    $viewlets.sidebar()       <!-- method call chain -->

Braces are only needed when the expression is followed by characters that
could be part of an identifier, or for complex expressions::

    ${name}suffix             <!-- disambiguate from $namesuffix -->
    ${x + y}                  <!-- arithmetic expression -->

Note that ``Hello $name.`` works because ``.`` followed by a non-letter
does not continue the attribute chain.

Use ``$literal()`` to output raw HTML without escaping::

    $literal(viewlets.sidebar())

Example
-------

Using Tonnikala templates::

    from tet.config import application_factory

    @application_factory(included_features=["renderers.tonnikala"])
    def main(config):
        config.add_route("home", "/")
        config.scan()


    # In views.py
    from pyramid.view import view_config

    @view_config(route_name="home", renderer="templates/home.tk")
    def home(request):
        return {"title": "Welcome", "name": "World"}

Sample template (home.tk)::

    <html>
    <head><title>$title</title></head>
    <body>
        <h1>Hello $name.</h1>
        <p>Welcome to $request.application_url</p>
    </body>
    </html>

With internationalization support::

    @application_factory(included_features=["renderers.tonnikala.i18n"])
    def main(config):
        config.add_route("home", "/")
        config.scan()
"""
from pyramid.config import Configurator


def i18n(config: Configurator):
    """
    Pyramid includeme for Tonnikala with i18n/l10n support.

    Includes the base Tonnikala renderer and enables localization.
    """
    config.include("tet.renderers.tonnikala")
    config.set_tonnikala_l10n(True)


def includeme(config: Configurator):
    """
    Pyramid includeme function for Tonnikala templates.

    Registers the Tonnikala renderer and adds ``.tk`` as a template extension.
    """
    config.include("tonnikala.pyramid")
    config.add_tonnikala_extensions(".tk")
