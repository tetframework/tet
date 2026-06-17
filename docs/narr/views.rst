=====================
Views and Controllers
=====================

Views are the heart of any Pyramid application: callables that turn a request
(and, in traversal, a context) into a response. Tet does not replace Pyramid's
view machinery -- it builds directly on top of it. The :mod:`tet.view` module
re-exports the entire :mod:`pyramid.view` public API and then layers a few
conveniences on top:

- An :class:`tet.view.view_config` subclass of Pyramid's own ``view_config``,
  so you can import everything view-related from one place.
- An :class:`tet.view.expose` decorator that registers a controller method as
  a traversal view using venusian, the same scanning mechanism Pyramid itself
  uses.
- A :class:`tet.view.BaseController` class for building traversal-based,
  nestable controllers.
- A :class:`tet.view.ServiceViews` base class that ties view classes into the
  ``pyramid_di`` dependency-injection system, giving you ``self.request`` and
  ``self.context`` for free.

Everything below is grounded in the actual code in
``src/tet/view/__init__.py``. If you already know Pyramid views, you can keep
using them unchanged -- Tet's additions are opt-in.

A note on imports
-----------------

Because ``tet.view`` does ``from pyramid.view import *``, names such as
``view_defaults``, ``forbidden_view_config``, ``notfound_view_config`` and
``render_view_to_response`` are available straight from ``tet.view``. The one
deliberate shadow is ``view_config``: importing it from ``tet.view`` gives you
Tet's subclass rather than Pyramid's. They are behaviour-compatible today, so
mixing imports is harmless, but importing from one place keeps your code tidy.

.. code-block:: python

    # One import line for the common cases.
    from tet.view import view_config, view_defaults, ServiceViews

The extended ``view_config`` decorator
--------------------------------------

:class:`tet.view.view_config` is a thin subclass of
``pyramid.view.view_config``. Its constructor simply forwards every keyword
argument to the Pyramid base class:

.. code-block:: python

    class view_config(_pyramid_view_config):
        """Extended Pyramid view_config decorator."""

        def __init__(self, **settings):
            super().__init__(**settings)

That means it accepts exactly the predicates and settings you already know:
``route_name``, ``renderer``, ``request_method``, ``permission``,
``context``, ``name``, ``match_param``, and so on. The subclass exists so that
Tet owns the symbol and can extend it in the future without forcing you to
change imports.

A plain function view looks exactly like it does in Pyramid:

.. code-block:: python

    from tet.view import view_config

    @view_config(route_name="home", renderer="templates/home.html")
    def home_view(request):
        return {"title": "Welcome to Tet"}

As always, the decorator only records configuration; it does nothing until a
``config.scan()`` picks it up via venusian. Make sure the package containing
your views is scanned during application start-up.

Service-aware view classes with ``ServiceViews``
------------------------------------------------

The most idiomatic way to write views in Tet is the class-based style backed
by dependency injection. :class:`tet.view.ServiceViews` subclasses
``pyramid_di.RequestScopedBaseService``, so a fresh instance is created per
request and participates in the DI container. Its constructor takes the
request and also resolves the current context:

.. code-block:: python

    class ServiceViews(RequestScopedBaseService):
        def __init__(self, request: Request):
            super().__init__(request=request)
            self.context = getattr(request, "context", None)

In practice you subclass it, decorate methods with ``view_config``, and access
``self.request`` and ``self.context`` inside each method. Because the class is
a request-scoped service, you can also declare injected dependencies the same
way you would in any other ``pyramid_di`` service.

.. code-block:: python

    from tet.view import ServiceViews, view_config
    from pyramid_di import autowired

    class UserViews(ServiceViews):
        # A request-scoped service injected by pyramid_di.
        user_service = autowired(UserService)

        @view_config(route_name="users", renderer="json")
        def list_users(self):
            # self.request and self.context are available.
            return {"users": self.user_service.all()}

        @view_config(
            route_name="user",
            renderer="json",
            request_method="GET",
        )
        def show_user(self):
            user_id = self.request.matchdict["id"]
            return {"user": self.user_service.get(user_id)}

When you decorate methods of a class with ``view_config``, Pyramid records the
method name as the view's ``attr``. On scan, Pyramid instantiates the class
with the request and calls the named method, which is why ``self.request`` is
populated. Combine that with ``view_defaults`` to share settings across every
method of the class:

.. code-block:: python

    from tet.view import view_config, view_defaults, ServiceViews

    @view_defaults(route_name="account", renderer="json")
    class AccountViews(ServiceViews):
        @view_config(request_method="GET")
        def read(self):
            return {"id": self.context.id}

        @view_config(request_method="POST")
        def update(self):
            self.context.update(self.request.json_body)
            return {"status": "ok"}

Why use ``ServiceViews`` over plain functions? You get a natural place to keep
per-request collaborators (database sessions, domain services, the current
user) without threading them through every function call, and you get the
``pyramid_di`` lifecycle for free.

Traversal controllers with ``BaseController``
---------------------------------------------

For traversal-based applications, :class:`tet.view.BaseController` lets you
model your URL space as a tree of controller objects. A controller is both a
context (it appears as ``request.context``) and a container: indexing into it
with ``controller[name]`` resolves the next path segment.

``BaseController`` implements ``__getitem__`` with two lookup strategies, in
order:

1. If the controller defines a ``_lookup(name)`` method, it is tried first.
   Returning a value resolves the segment; raising ``KeyError`` falls through.
2. Otherwise, if a class attribute with that name is itself a
   ``BaseController`` subclass, it is instantiated with the current request and
   wired up with ``__parent__`` and ``__name__`` so Pyramid's location
   machinery works.

If neither succeeds, a ``KeyError`` is raised, which Pyramid turns into a 404.

.. code-block:: python

    def __getitem__(self, name):
        if hasattr(self, "_lookup"):
            try:
                return self._lookup(name)
            except KeyError:
                pass

        child_controller = getattr(self, name, None)
        if isclass(child_controller) and issubclass(child_controller, BaseController):
            child = child_controller(self.request)
            child.__parent__ = self
            child.__name__ = name
            return child

        raise KeyError(f"Child not found: {name}")

A realistic controller tree mixes static child controllers (declared as nested
classes) with dynamic lookups (implemented in ``_lookup``):

.. code-block:: python

    from tet.view import BaseController, expose

    class UserController(BaseController):
        def __init__(self, request):
            self.request = request

        @expose(renderer="json")
        def index(self):
            return {"user": self.__name__}


    class UsersController(BaseController):
        def __init__(self, request):
            self.request = request

        @expose(renderer="json")
        def index(self):
            # Reached at /users/ -- "index" maps to the empty view name.
            return {"users": ["alice", "bob"]}

        def _lookup(self, name):
            # Reached at /users/<name>/ for any name.
            child = UserController(self.request)
            child.__parent__ = self
            child.__name__ = name
            return child


    class RootController(BaseController):
        def __init__(self, request):
            self.request = request

        # Static child: /users/ resolves to UsersController.
        users = UsersController

Wire the root controller up as your root factory and Tet/Pyramid will traverse
through the tree segment by segment, calling the exposed method on whichever
controller is the final context.

Exposing controller methods with ``expose``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inside a ``BaseController``, decorate the methods you want to publish with
:class:`tet.view.expose`. The decorator stores its keyword settings and uses
venusian to defer registration until ``config.scan()`` runs -- the same
deferred-registration pattern Pyramid uses everywhere. On scan it calls
``config.add_view(...)`` for the method.

Two behaviours are worth remembering:

- The method name becomes the view name, with one special case: a method named
  ``index`` is registered with the empty name (``""``), so it answers the
  default view for that context. ``profile`` would answer ``.../profile``.
- ``expose`` is class-scope only. It inspects the venusian scope and raises
  ``ValueError("expose can be only applied to instance methods!")`` if attached
  anywhere other than a method defined at class scope.

.. code-block:: python

    from tet.view import BaseController, expose

    class ArticleController(BaseController):
        def __init__(self, request):
            self.request = request

        @expose(renderer="json")
        def index(self):
            # Default view for this context: /articles/<id>/
            return {"article": self.__name__}

        @expose(renderer="templates/comments.html", request_method="GET")
        def comments(self):
            # Named view: /articles/<id>/comments
            return {"comments": []}

Under the hood ``expose`` registers a small wrapper that re-dispatches to the
context, ``getattr(request.context, attr_name)()``, and passes the context
class as the ``context`` predicate so the view only matches that controller.
Any extra keywords you give to ``expose`` (``renderer``, ``request_method``,
``permission``, ...) flow straight into ``add_view``, just like ``view_config``.

Choosing between the styles
---------------------------

- Reach for plain ``view_config`` functions for small, route-mapped endpoints.
- Reach for ``ServiceViews`` when you want route-mapped views with injected
  dependencies and shared per-request state -- this is the recommended default
  for most Tet applications.
- Reach for ``BaseController`` plus ``expose`` when your application is
  traversal-oriented and you want the URL hierarchy to mirror an object tree.

All three coexist in the same application; pick per feature, not per project.

Registering and scanning
------------------------

None of these decorators take effect until the configurator scans them. A
minimal setup looks like:

.. code-block:: python

    from pyramid.config import Configurator

    def main(global_config, **settings):
        with Configurator(settings=settings) as config:
            config.include("pyramid_di")          # required for ServiceViews
            config.add_route("users", "/users")
            config.add_route("user", "/users/{id}")
            config.scan("myapp.views")            # picks up view_config / expose
            return config.make_wsgi_app()

For traversal controllers, also set your ``RootController`` as the root factory
(see :doc:`sqlalchemy` for the SQLAlchemy-backed variant) and scan the module
that defines them so ``expose`` registrations are collected.

See also
--------

- :doc:`viewlets` -- composing reusable view fragments within a page.
- :doc:`configuration` -- including Tet modules and wiring the configurator.
- :doc:`sqlalchemy` -- root factories for traversal-based controllers.
- :doc:`json` -- the JSON renderer used by the examples above.
- The upstream `Pyramid views documentation
  <https://docs.pylonsproject.org/projects/pyramid/en/latest/narr/views.html>`_.
