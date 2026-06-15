=========================
Templating with Tonnikala
=========================

Tet ships first-class support for the `Tonnikala
<https://github.com/tetframework/Tonnikala>`_ template engine. Tonnikala is a
fast, XML-based template language that compiles your templates straight to
Python bytecode, so rendering is quick and template errors surface as ordinary
Python tracebacks.

This guide shows how to enable the Tonnikala renderer in a Tet application, how
to return template renderings from views, and how the Tonnikala interpolation
syntax works.

The integration lives in :mod:`tet.renderers.tonnikala`. The public surface is
small and deliberate:

- ``includeme(config)`` -- the Pyramid includeme that registers the renderer
  and the ``.tk`` template extension.
- ``i18n(config)`` -- an includeme that pulls in the base renderer and turns on
  Tonnikala's localization support.


Enabling the renderer
----------------------

The renderer is wired up with a standard Pyramid include. You can include it
directly on the configurator:

.. code-block:: python

    from pyramid.config import Configurator

    def main(global_config, **settings):
        config = Configurator(settings=settings)
        config.include("tet.renderers.tonnikala")
        config.add_route("home", "/")
        config.scan()
        return config.make_wsgi_app()

Calling ``config.include("tet.renderers.tonnikala")`` runs
:func:`tet.renderers.tonnikala.includeme`, which does two things:

#. Includes ``tonnikala.pyramid``, registering Tonnikala as a Pyramid renderer.
#. Calls ``config.add_tonnikala_extensions(".tk")`` so that any renderer whose
   name ends in ``.tk`` is rendered with Tonnikala.

If your application is assembled with Tet's feature-based
:func:`tet.config.application_factory`, request the renderer as a feature
instead of including it by hand:

.. code-block:: python

    from tet.config import application_factory

    @application_factory(included_features=["renderers.tonnikala"])
    def main(config):
        config.add_route("home", "/")
        config.scan()

Both approaches end up calling the same ``includeme``; pick whichever matches
how the rest of your application is configured.


Rendering templates from views
------------------------------

Once the renderer is enabled, point a view's ``renderer`` argument at a
template whose name ends in ``.tk``. The view returns a plain dictionary; the
keys of that dictionary become the top-level variables available inside the
template.

.. code-block:: python

    from pyramid.view import view_config

    @view_config(route_name="home", renderer="templates/home.tk")
    def home(request):
        return {"title": "Welcome", "name": "World"}

The ``renderer`` value is resolved as a Pyramid asset specification. A bare
path such as ``"templates/home.tk"`` is interpreted relative to the package the
view is defined in. To reference a template in another package, use the fully
qualified ``package:path`` form:

.. code-block:: python

    @view_config(route_name="home", renderer="myapp:templates/home.tk")
    def home(request):
        return {"title": "Welcome", "name": "World"}

Inside the template, in addition to the keys you returned, the current
``request`` is always available, so you can reach request attributes like
``request.application_url`` directly.


Template syntax
---------------

Tonnikala templates are well-formed XML/HTML documents. Dynamic content is
produced with ``$`` interpolation and a handful of control attributes. The
example below shows a complete template that consumes the dictionary returned
by the ``home`` view above:

.. code-block:: html

    <html>
    <head><title>$title</title></head>
    <body>
        <h1>Hello $name.</h1>
        <p>Welcome to $request.application_url</p>
    </body>
    </html>

Save this as ``templates/home.tk`` next to your views and the ``home`` view
will render it.


Interpolating expressions with ``$``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``$`` sign interpolates an expression. What makes Tonnikala convenient is
that ``$`` does **not** always require braces: it greedily resolves a
*continuous chain* of attribute access, method calls, and indexing as a single
expression.

.. code-block:: html

    $name                     <!-- simple variable -->
    $user.name                <!-- attribute access -->
    $user.get_full_name()     <!-- method call -->
    $items[0].title           <!-- indexing and attribute -->
    $viewlets.sidebar()       <!-- method call chain -->

The chain stops at the first character that cannot continue a Python
expression of this kind. This is why ``Hello $name.`` renders correctly: the
``.`` is immediately followed by the end of the line (a non-letter), so it does
not continue the attribute chain and is treated as literal punctuation.


When to use braces
~~~~~~~~~~~~~~~~~~~

Braces ``${...}`` are only needed in two situations.

First, when the expression is immediately followed by characters that could be
read as part of the identifier. Without braces, Tonnikala would try to resolve
the whole run as one name:

.. code-block:: html

    <!-- Wrong: looks for a variable called "namesuffix" -->
    $namesuffix

    <!-- Right: interpolate "name", then the literal text "suffix" -->
    ${name}suffix

Second, for any expression more complex than a chain of access and calls, such
as arithmetic or operators:

.. code-block:: html

    <p>Total: ${x + y}</p>

If in doubt, braces are always safe; they simply make the expression
boundaries explicit.


Outputting raw HTML with ``$literal``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default every interpolated value is HTML-escaped, which is what you want for
user-supplied data. When a value is already trusted markup -- for example the
HTML produced by a viewlet -- wrap it in ``$literal(...)`` to emit it verbatim,
without escaping:

.. code-block:: html

    <aside>
        $literal(viewlets.sidebar())
    </aside>

Only use ``$literal`` on content you control. Passing unescaped user input
through it reintroduces the cross-site scripting risk that escaping exists to
prevent.


Internationalized templates
---------------------------

To translate template text, enable the i18n-aware variant of the renderer.
Instead of including ``tet.renderers.tonnikala`` directly, include the
:func:`tet.renderers.tonnikala.i18n` includeme:

.. code-block:: python

    config.include("tet.renderers.tonnikala.i18n")

This includeme first includes the base renderer and then calls
``config.set_tonnikala_l10n(True)``, which switches on Tonnikala's localization
machinery so that translatable strings in your templates are passed through the
active translation domain.

With the feature-based factory, request the i18n feature instead:

.. code-block:: python

    from tet.config import application_factory

    @application_factory(included_features=["renderers.tonnikala.i18n"])
    def main(config):
        config.add_route("home", "/")
        config.scan()

Enabling i18n does not change the syntax shown above; it only adds translation
of marked-up text. See the internationalization guide for how to mark and
extract translatable strings.


See also
--------

- :doc:`views` -- defining views and choosing renderers.
- :doc:`viewlets` -- composing reusable fragments such as ``viewlets.sidebar()``
  for use with ``$literal``.
- :doc:`i18n` -- setting up translation domains and extracting messages.
