=====================================
Extended Request and Response Objects
=====================================

Tet ships two very small modules, :mod:`tet.request` and
:mod:`tet.response`, that sit directly on top of Pyramid's
:mod:`pyramid.request` and :mod:`pyramid.response`. If you open them
expecting a large subclass hierarchy you will be surprised: in version
0.5.0 they are deliberately thin **re-export shims**. This page explains
what they actually contain, why they are written that way, and how the
request gains extra behaviour at runtime through other Tet modules.

Honesty first: what is in the modules
-------------------------------------

Both modules re-export the public API of their Pyramid counterpart and
nothing more. The complete source of :mod:`tet.request` is:

.. code-block:: python

    """
    Re-export of Pyramid request classes.

    This module re-exports all public symbols from :mod:`pyramid.request`
    for convenience.
    """

    from pyramid.request import *  # noqa: F403  (re-export pyramid.request API)

and :mod:`tet.response` mirrors it exactly for :mod:`pyramid.response`.

That means importing from Tet gives you the genuine Pyramid classes:

.. code-block:: python

    from tet.request import Request
    from tet.response import Response

    # These are the very same objects Pyramid hands you:
    from pyramid.request import Request as PyramidRequest

    assert Request is PyramidRequest

There is currently **no** ``tet.request.Request`` subclass, no overridden
``Response``, and no extra methods defined inside these two files. Anything
you can do with :class:`pyramid.request.Request` you can do with the symbol
imported from :mod:`tet.request`, because it is the identical class.

Why re-export at all?
---------------------

A one-line ``from pyramid.request import *`` module may look pointless, but
it buys two concrete things.

**A single, stable import surface.** Application code and the rest of the
Tet framework import request and response types from ``tet.request`` /
``tet.response`` rather than reaching directly into Pyramid. The intent is
that *where* a class lives is a Tet implementation detail. Consumers depend
on the Tet name, not on the Pyramid name.

**A designated extension point.** Because every Tet application already
imports from these modules, they are the natural home for any future
subclassing or behaviour Tet wants to add. The day Tet needs a customised
``Request`` (for example, a typed accessor or a default property), it can be
introduced here and every importer picks it up without changing a single
import line. Until that day, the shim keeps the contract in place at zero
cost and zero behavioural surprise.

This is the standard "wrap the dependency behind your own module" pattern:
pay a trivial price now to keep a seam open for later.

How the request is *actually* extended
--------------------------------------

The interesting part is that Tet **does** extend the request object - just
not by subclassing it in :mod:`tet.request`. Pyramid's idiomatic mechanism
for adding behaviour to a request is
:meth:`pyramid.config.Configurator.add_request_method`, which attaches
methods or reified properties to the live request at configuration time.
Tet uses exactly this mechanism, so the additions show up on the very same
:class:`pyramid.request.Request` instances you import from
:mod:`tet.request`.

The clearest example lives in :mod:`tet.i18n`. When you include i18n
support, :func:`tet.i18n.configure_i18n` registers three request members:

.. code-block:: python

    config.add_request_method(translate, property=True, reify=True)
    config.add_request_method(pluralize, property=True, reify=True)
    config.add_request_method(get_localizer, name="localize", property=True, reify=True)

After that runs, ordinary request objects expose:

- ``request.translate`` - a callable that translates a message string,
  applying the configured default domain and the request's localizer.
- ``request.pluralize`` - a callable that selects the singular or plural
  form for a count ``n``.
- ``request.localize`` - the Pyramid :class:`~pyramid.i18n.Localizer`
  for the current request.

(Tet's i18n code also references ``request.localizer``, the standard
Pyramid-provided localizer property.)

Using the extended request in a view
------------------------------------

Because the additions are plain request attributes, you use them directly
on the ``request`` argument of any view. Enable the feature first - here via
Tet's feature-based configuration:

.. code-block:: python

    from tet.config import application_factory


    @application_factory(included_features=["i18n"])
    def main(config):
        config.add_translation_dirs("myapp:locale")
        config.scan()

Then call the request methods from a view callable:

.. code-block:: python

    from pyramid.view import view_config


    @view_config(route_name="hello", renderer="json")
    def hello(request):
        # request.translate was added by tet.i18n via add_request_method
        return {"message": request.translate("Hello, World!")}


    @view_config(route_name="cart", renderer="json")
    def cart(request):
        count = len(request.session.get("items", []))
        # request.pluralize chooses singular/plural for the count
        label = request.pluralize(
            "${n} item",
            "${n} items",
            count,
            mapping={"n": count},
        )
        return {"summary": label}

The ``translate`` and ``pluralize`` callables accept keyword-only
``domain``, ``mapping`` and ``context`` arguments, matching the signatures
defined in :func:`tet.i18n.configure_i18n`:

.. code-block:: python

    msg = request.translate(
        "Saved",
        domain="myapp",
        context="button",
    )

Working with responses
----------------------

The response side is symmetric and, today, purely a re-export. Construct
and manipulate responses exactly as you would with Pyramid - either by
returning a renderer-friendly value, or by building a
:class:`~pyramid.response.Response` explicitly:

.. code-block:: python

    from tet.response import Response
    from pyramid.view import view_config


    @view_config(route_name="ping")
    def ping(request):
        return Response(
            body=b"pong",
            content_type="text/plain",
            charset="utf-8",
        )

You may also reach the per-request response object Pyramid creates as
``request.response`` and mutate it in place; nothing in Tet changes that
behaviour:

.. code-block:: python

    @view_config(route_name="download", renderer="json")
    def download(request):
        request.response.headers["Cache-Control"] = "no-store"
        return {"ok": True}

Practical guidance
------------------

- **Import from Tet, not Pyramid.** Prefer ``from tet.request import
  Request`` and ``from tet.response import Response`` in application code.
  It costs nothing today and keeps you on the framework's extension seam.
- **Do not expect Tet-only methods on the bare class.** Members like
  ``translate``, ``pluralize`` and ``localize`` exist only after the
  relevant feature (``i18n``) has been included. They are runtime additions
  via ``add_request_method``, not class attributes you can find by reading
  :mod:`tet.request`.
- **Add your own request methods the same way.** If you need a custom
  accessor on every request, register it in an ``includeme`` with
  ``config.add_request_method(...)`` rather than subclassing. This is the
  pattern Tet itself follows and it composes cleanly with the shim.

.. code-block:: python

    from pyramid.config import Configurator


    def current_user(request):
        # reified so it is computed at most once per request
        return request.session.get("user_id")


    def includeme(config: Configurator) -> None:
        config.add_request_method(current_user, property=True, reify=True)

See also
--------

- :doc:`i18n` - the i18n feature that adds ``request.translate``,
  ``request.pluralize`` and ``request.localize``.
- :doc:`views` - writing view callables that receive the extended request
  and return responses.
- :doc:`configuration` - enabling features such as ``i18n`` through Tet's
  application factory.
