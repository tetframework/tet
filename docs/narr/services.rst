=================================
Dependency Injection and Services
=================================

Tet ships with a lightweight, request-scoped dependency injection (DI)
container built on `pyramid_di
<https://github.com/RatbraDev/pyramid_di>`_. The DI primitives live in the
:mod:`tet.services` module, which re-exports the ``pyramid_di`` building
blocks from a single, stable location so application code never has to reach
into ``pyramid_di`` directly.

This page explains what services solve, how to declare and register them,
how dependencies are wired together with ``autowired``, how the
request-scoped lifecycle works, and finishes with a realistic end-to-end
example.


Why dependency injection?
-------------------------

A typical web request needs to talk to a database session, look up the
current user, send email, call third-party APIs, and so on. If every view
constructs those collaborators itself, you end up with:

- views that know how to build their dependencies (and their dependencies'
  dependencies),
- duplicated wiring scattered across the codebase,
- objects with unclear lifetimes (created too often, or accidentally
  shared across requests),
- code that is hard to test because collaborators cannot be swapped out.

Dependency injection inverts that: a *service* declares what it needs, and
the container supplies it. Views and other services ask the container for a
service by type and receive a fully wired instance. The container also owns
the *lifecycle* of each service -- in Tet the common case is a service that
is instantiated **once per request** and discarded when the request ends.


Service base classes
--------------------

:mod:`tet.services` re-exports three base classes. Pick the one that matches
the lifetime your service needs:

:class:`~tet.services.RequestScopedBaseService`
    The workhorse. A fresh instance is created the first time it is
    requested within a given request, and the same instance is reused for
    the remainder of that request. Instances receive the active
    ``request`` as ``self.request``. Use this for anything that depends on
    per-request state (the database session, the authenticated user, the
    current locale, and so on).

:class:`~tet.services.ApplicationScopedBaseService`
    A single instance shared for the lifetime of the application (the
    Pyramid registry). Use this for stateless helpers or expensive,
    immutable resources -- but never store per-request state on it.

:class:`~tet.services.BaseService`
    The common base of the two above. You normally subclass one of the
    scoped classes rather than this directly.

All of these are imported from ``tet.services``:

.. code-block:: python

    from tet.services import (
        service,
        autowired,
        RequestScopedBaseService,
        ApplicationScopedBaseService,
        BaseService,
    )


Declaring a service
-------------------

Decorate a class with :func:`~tet.services.service` and subclass the
appropriate base. A request-scoped service automatically gets
``self.request``:

.. code-block:: python

    from tet.services import service, RequestScopedBaseService
    from myapp.models import User


    @service()
    class UserService(RequestScopedBaseService):
        def get_user(self, user_id):
            return self.request.dbsession.query(User).get(user_id)

The ``@service()`` decorator marks the class for registration. The actual
registration happens when you scan the module that contains it (see
`Registering services`_ below).


Declaring dependencies with ``autowired``
-----------------------------------------

A service rarely lives alone. To depend on another service, declare it as a
class attribute using :func:`~tet.services.autowired`. The attribute becomes
a descriptor that resolves the dependency lazily from the container the
first time it is accessed:

.. code-block:: python

    from tet.services import service, autowired, RequestScopedBaseService


    @service()
    class OrderService(RequestScopedBaseService):
        user_service = autowired(UserService)

        def get_user_orders(self, user_id):
            user = self.user_service.get_user(user_id)
            return user.orders

Here ``OrderService`` never constructs ``UserService`` itself. When
``self.user_service`` is first read, the container looks up (or instantiates)
the request-scoped ``UserService`` for the current request and hands it back.
Because both are request-scoped, every collaborator in a given request sees
the *same* ``UserService`` instance.

``autowired`` works the same way on any class the container instantiates --
including view classes (see `Using services in views`_).


Registering services
--------------------

Services must be enabled and then discovered. Enabling DI means including
``pyramid_di``; in a Tet application this is done by activating the
``services`` feature, whose ``includeme`` simply calls
``config.include("pyramid_di")``:

.. code-block:: python

    from tet.config import application_factory


    @application_factory(included_features=["services"])
    def main(config):
        config.scan_services("myapp.services")
        config.scan()

``included_features=["services"]`` pulls in :mod:`tet.services`, which wires
up ``pyramid_di`` and adds the ``scan_services`` directive (among others) to
the configurator. ``scan_services`` walks the given package and registers
every class decorated with ``@service()``. The regular ``config.scan()`` call
still handles your views and other Venusian decorators.

If you are configuring Pyramid manually rather than through Tet's feature
list, the equivalent explicit include is:

.. code-block:: python

    config.include("pyramid_di")  # or: config.include("tet.services")
    config.scan_services("myapp.services")

You can also register services imperatively, without the ``@service()``
decorator. This is handy for binding a concrete object or factory to an
interface or third-party type:

.. code-block:: python

    # Register an already-constructed instance under a type/name.
    config.register_service(my_instance, SomeType)


    # Register a factory called with (context, request) to build the service.
    def make_session_service(context, request):
        return build_session(request)


    config.register_service_factory(make_session_service, Session)

Tet itself uses ``register_service_factory`` internally -- for example
:mod:`tet.sqlalchemy.simple` registers the SQLAlchemy ``Session`` as a
request-scoped service factory so views can simply do
``request.find_service(Session)``.


Retrieving a service
--------------------

There are two ways to get a service instance, depending on where you are.

Inside another service or any class the container instantiates, prefer
``autowired`` (shown above) -- it is declarative and resolves lazily.

Anywhere you hold a ``request`` -- most commonly a function-based view --
call ``request.find_service``:

.. code-block:: python

    from pyramid.view import view_config
    from myapp.services import UserService


    @view_config(route_name="user", renderer="json")
    def get_user(request):
        user_service = request.find_service(UserService)
        return user_service.get_user(request.matchdict["id"])

``find_service`` looks the service up by type (and optional ``name=`` for
named registrations). For a request-scoped service it returns the cached
instance for the current request, creating it on first use.


The request-scoped lifecycle
----------------------------

Request scoping is the heart of Tet's DI model, so it is worth being precise
about what "once per request" means:

- The **first** time a request-scoped service is needed during a request --
  whether via ``find_service`` or via an ``autowired`` attribute -- the
  container instantiates it and caches it on the request.
- Every **subsequent** lookup within the *same* request returns that cached
  instance. Two collaborators that both depend on ``UserService`` share one
  instance.
- When the request ends, the cache is discarded. The **next** request gets
  brand-new instances.

This makes request-scoped services the right place for per-request state
(the database session, the current user, request-specific caches) without
any risk of leaking that state across requests. Conversely, never stash
per-request data on an :class:`~tet.services.ApplicationScopedBaseService`,
which is shared by every request and every thread.


Using services in views
-----------------------

Class-based views can themselves declare dependencies with ``autowired``,
because the view class is instantiated through the container:

.. code-block:: python

    from pyramid.view import view_config
    from tet.services import autowired
    from myapp.services import UserService


    class UserViews:
        user_service = autowired(UserService)

        def __init__(self, request):
            self.request = request

        @view_config(route_name="user", renderer="json")
        def get_user(self):
            user_id = self.request.matchdict["id"]
            return self.user_service.get_user(user_id)

Tet also provides :class:`tet.view.ServiceViews`, a
:class:`~tet.services.RequestScopedBaseService` subclass meant to be used as
a base for view classes. It gives you ``self.request`` and ``self.context``
for free, so you can drop the boilerplate ``__init__``:

.. code-block:: python

    from pyramid.view import view_config
    from tet.services import autowired
    from tet.view import ServiceViews
    from myapp.services import UserService


    class UserViews(ServiceViews):
        user_service = autowired(UserService)

        @view_config(route_name="user", renderer="json")
        def get_user(self):
            return self.user_service.get_user(self.request.matchdict["id"])


End-to-end example
------------------

Putting it all together: a ``UserService`` and an ``OrderService`` that
depends on it, both scanned at startup and consumed from a view. Assume the
SQLAlchemy ``Session`` is registered as a service (see
:doc:`sqlalchemy`).

``myapp/services.py``:

.. code-block:: python

    from sqlalchemy.orm import Session

    from tet.services import service, autowired, RequestScopedBaseService
    from myapp.models import User


    @service()
    class UserService(RequestScopedBaseService):
        # The SQLAlchemy session is itself a request-scoped service.
        dbsession = autowired(Session)

        def get_user(self, user_id):
            return self.dbsession.query(User).get(user_id)


    @service()
    class OrderService(RequestScopedBaseService):
        user_service = autowired(UserService)

        def get_user_orders(self, user_id):
            user = self.user_service.get_user(user_id)
            if user is None:
                return []
            return list(user.orders)

``myapp/views.py``:

.. code-block:: python

    from pyramid.view import view_config

    from tet.services import autowired
    from tet.view import ServiceViews
    from myapp.services import UserService, OrderService


    class UserViews(ServiceViews):
        user_service = autowired(UserService)
        order_service = autowired(OrderService)

        @view_config(route_name="user", renderer="json")
        def get_user(self):
            user = self.user_service.get_user(self.request.matchdict["id"])
            return {"id": user.id, "name": user.name}

        @view_config(route_name="user_orders", renderer="json")
        def get_orders(self):
            user_id = self.request.matchdict["id"]
            orders = self.order_service.get_user_orders(user_id)
            return [{"id": o.id, "total": str(o.total)} for o in orders]

``myapp/__init__.py``:

.. code-block:: python

    from tet.config import application_factory


    @application_factory(included_features=["services"])
    def main(config):
        config.include("tet.sqlalchemy.simple")
        config.setup_sqlalchemy()

        config.add_route("user", "/users/{id}")
        config.add_route("user_orders", "/users/{id}/orders")

        config.scan_services("myapp.services")
        config.scan()

During a single request to ``/users/42/orders``, the container creates one
``OrderService``, one ``UserService``, and one ``Session`` -- each reused
wherever it is needed -- and then discards them when the response is sent.


See also
--------

- :doc:`views` -- view classes, ``ServiceViews``, and rendering.
- :doc:`sqlalchemy` -- registering the SQLAlchemy ``Session`` as a
  request-scoped service.
- :doc:`configuration` -- ``application_factory``, ``create_configurator``,
  and the Tet feature list.
