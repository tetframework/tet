========
Viewlets
========

Viewlets are reusable, composable template fragments that you render *within*
a page. Where a view renders one complete response, a viewlet renders a small,
self-contained chunk of HTML -- a sidebar, a user card, a navigation menu, a
flash-message banner -- that can be dropped into many different templates.

Tet's viewlet system lives in :mod:`tet.viewlet`. It is intentionally small:
the :func:`~tet.viewlet.viewlet` decorator turns a method that returns a dict
of template variables into a callable that renders a template fragment and
returns the resulting HTML string. A :class:`~tet.viewlet.BeforeViewletRender`
event is fired for every render, so subscribers can inject shared globals
(translation helpers, the current user, CSRF helpers) into the fragment's
rendering namespace -- exactly like Pyramid's ``BeforeRender`` does for
top-level templates.

Why viewlets
------------

Plain template includes get you part of the way, but they share the enclosing
template's namespace and have no place to run logic. A viewlet is different:

- It owns its **own template** (an asset spec), rendered in isolation.
- It runs **Python code** to assemble its data before rendering.
- It returns an **HTML string** you can place anywhere -- in a template, in a
  JSON payload, or in another viewlet.
- It participates in the **before-render event**, so the same globals your
  page templates rely on are available inside the fragment too.

This makes viewlets ideal for UI components that appear on many pages and need
a little logic of their own.

The viewlet decorator
---------------------

The core of the system is :func:`tet.viewlet.viewlet`. It takes a single
argument, ``renderer`` -- a template **asset specification** such as
``"myapp:templates/sidebar.tk"`` -- and decorates a method that returns a dict
of template variables:

.. code-block:: python

    from tet.viewlet import viewlet


    class MyViewlets:
        def __init__(self, request):
            self.request = request

        @viewlet("myapp:templates/sidebar.tk")
        def sidebar(self):
            return {"recent_posts": get_recent_posts(self.request)}

        @viewlet("myapp:templates/user_card.tk")
        def user_card(self, user):
            return {"user": user}

The dict your method returns becomes the template variables for the fragment.
Note ``user_card`` takes an extra ``user`` argument: viewlets are ordinary
callables, so they can accept positional and keyword arguments and pass data
straight through to their templates.

How rendering works
~~~~~~~~~~~~~~~~~~~~~

When you call a decorated method, the wrapper does four things, in order:

1. Resolves the request via :func:`~tet.viewlet.get_request`. This looks for a
   ``request`` attribute on the receiver (``self.request``) and falls back to
   treating the receiver itself as the request. This is why the
   ``MyViewlets`` class above stores ``self.request`` in ``__init__`` -- but it
   also means a bare function that receives a request directly works too.
2. Calls your function to get the ``renderval`` dict.
3. Builds a :class:`~tet.viewlet.BeforeViewletRender` event seeded with
   ``{"request": request}`` and notifies the registry, giving subscribers a
   chance to add globals (see below).
4. Calls :func:`~tet.viewlet.render_fragment` to render the template and
   returns the resulting HTML.

:func:`~tet.viewlet.render_fragment` is the low-level helper. It looks up the
renderer for the asset spec with Pyramid's ``get_renderer`` and calls the
renderer's ``fragment(tpl, dct, system)`` method:

.. code-block:: python

    def render_fragment(tpl, dct, system):
        renderer = get_renderer(tpl)
        return renderer.fragment(tpl, dct, system)

Because rendering goes through ``fragment``, the template renderer you point
at must support fragment rendering -- the Tonnikala renderer that ships with
Tet does. The ``.tk`` asset specs in these examples are Tonnikala templates.

Injecting globals: the before-render event
------------------------------------------

Top-level Pyramid templates receive globals through subscribers to the
``BeforeRender`` event. Viewlet fragments are rendered separately, so they
need their own hook -- that is :class:`tet.viewlet.IBeforeViewletRender`.

:class:`~tet.viewlet.BeforeViewletRender` is the concrete event class that
implements it. It subclasses ``dict`` (the rendering system dict) and carries
a ``rendering_val`` attribute holding the value your viewlet returned:

.. code-block:: python

    @implementer(IBeforeViewletRender)
    class BeforeViewletRender(dict):
        def __init__(self, system, rendering_val=None):
            super().__init__(system)
            self.rendering_val = rendering_val

Because :class:`~tet.viewlet.IBeforeViewletRender` derives from Pyramid's
``IDict``, the event is itself a mutable mapping. Subscribers add globals by
assigning keys on the event, and those keys become available in the fragment's
namespace. Subscribe to the standard ``BeforeRender`` event predicated on the
``IBeforeViewletRender`` interface so the subscriber fires *only* for viewlet
renders:

.. code-block:: python

    from pyramid.events import subscriber, BeforeRender
    from tet.viewlet import IBeforeViewletRender


    @subscriber(BeforeRender, IBeforeViewletRender)
    def add_viewlet_globals(event):
        request = event.get("request")
        if request is not None:
            event["_"] = request.localizer.translate
            event["current_user"] = getattr(request, "user", None)

Every fragment rendered through a viewlet now sees ``_`` and ``current_user``
in its template namespace, in addition to whatever its own method returned.

Registering viewlets as a template global
-----------------------------------------

A viewlet method is only useful from a template if the template can reach it.
The idiomatic approach is to expose the viewlet container under a single
template global -- conventionally ``viewlets`` -- by adding it in an ordinary
``BeforeRender`` subscriber for *page* templates:

.. code-block:: python

    from pyramid.events import subscriber, BeforeRender


    @subscriber(BeforeRender)
    def add_viewlets(event):
        request = event.get("request")
        if request is not None:
            event["viewlets"] = MyViewlets(request=request)

Now every page template has a ``viewlets`` object whose attributes are your
decorated methods.

Calling viewlets from templates
-------------------------------

Tonnikala uses ``$`` for expression interpolation, and a ``$`` chains attribute
access, method calls and indexing into a single expression. A viewlet call is
just a method call on the ``viewlets`` global:

.. code-block:: html

    $viewlets.sidebar()

There is a catch, though. A viewlet returns an HTML **string**, and Tonnikala
escapes interpolated values by default. If you write ``$viewlets.sidebar()``
directly, the markup will be HTML-escaped and rendered as visible text rather
than as HTML. To emit the fragment as raw markup, wrap the call in
``$literal(...)``:

.. code-block:: html

    <div class="sidebar">
        $literal(viewlets.sidebar())
    </div>

    <div class="user-card">
        $literal(viewlets.user_card(user))
    </div>

Note how arguments flow through: ``viewlets.user_card(user)`` passes the
``user`` template variable straight into the viewlet, which forwards it to its
own template as ``{"user": user}``.

A realistic example: a user-card viewlet
----------------------------------------

Putting it together, here is a small "user card" component used in a sidebar.
First, the viewlet container:

.. code-block:: python

    from pyramid.events import subscriber, BeforeRender
    from tet.viewlet import viewlet, IBeforeViewletRender


    class AccountViewlets:
        def __init__(self, request):
            self.request = request

        @viewlet("myapp:templates/viewlets/user_card.tk")
        def user_card(self, user):
            return {
                "user": user,
                "is_self": user.id == self.request.authenticated_userid,
            }

        @viewlet("myapp:templates/viewlets/sidebar.tk")
        def sidebar(self):
            return {
                "current_user": self.request.user,
                "unread_count": self.request.user.unread_notifications(),
            }


    @subscriber(BeforeRender)
    def add_account_viewlets(event):
        request = event.get("request")
        if request is not None:
            event["viewlets"] = AccountViewlets(request=request)


    @subscriber(BeforeRender, IBeforeViewletRender)
    def add_viewlet_globals(event):
        request = event.get("request")
        if request is not None:
            event["_"] = request.localizer.translate

The ``user_card.tk`` template -- a self-contained fragment that relies both on
the dict the viewlet returned and on the ``_`` global injected by the
before-render subscriber:

.. code-block:: html

    <div class="user-card">
        <img src="$user.avatar_url" alt="$user.display_name">
        <span class="name">$user.display_name</span>
        <py:if test="is_self">
            <span class="badge">$_('You')</span>
        </py:if>
    </div>

And the ``sidebar.tk`` template, which composes the user-card viewlet inside
itself by calling back through the ``viewlets`` global:

.. code-block:: html

    <aside class="sidebar">
        $literal(viewlets.user_card(current_user))
        <p class="notifications">
            $_('Unread'): $unread_count
        </p>
    </aside>

Finally, dropping the sidebar into a page layout:

.. code-block:: html

    <body>
        <main>
            $literal(content)
        </main>
        $literal(viewlets.sidebar())
    </body>

Each render goes through the same pipeline: the request is resolved, the
viewlet's data dict is built, the :class:`~tet.viewlet.BeforeViewletRender`
event is fired so ``_`` is added, and the fragment is rendered and returned as
HTML for ``$literal`` to emit.

Tips and gotchas
----------------

- **Always use** ``$literal(...)`` around viewlet calls. Without it the HTML is
  escaped. This is the single most common mistake.
- **Keep template variable names distinct** from injected globals. If your
  viewlet returns a key that a subscriber also sets, the value your function
  returned takes precedence -- the event globals fill in the rest.
- **Viewlets compose.** A viewlet template may itself call other viewlets via
  the ``viewlets`` global, as the sidebar example shows.
- **The renderer must support fragments.** Point viewlets at the Tonnikala
  renderer (``.tk`` asset specs); ``render_fragment`` calls the renderer's
  ``fragment`` method, which not every renderer provides.

See also
--------

- :doc:`views` -- writing full views and renderers.
- :doc:`templating` -- the Tonnikala template language, including ``$``
  interpolation and ``$literal``.
- :doc:`i18n` -- providing translation globals such as ``_`` to your fragments.
