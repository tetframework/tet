"""
Viewlet rendering utilities for Tet applications.

Viewlets are reusable template fragments that can be rendered from within
views. This module provides the :func:`viewlet` decorator for creating
viewlets that render a template and return HTML.

Example
-------

Creating a viewlet class and registering it as a template global::

    from pyramid.events import subscriber
    from tet.viewlet import viewlet, IBeforeViewletRender
    from pyramid.events import BeforeRender

    class MyViewlets:
        def __init__(self, request):
            self.request = request

        @viewlet("myapp:templates/sidebar.tk")
        def sidebar(self):
            return {"recent_posts": get_recent_posts(self.request)}

        @viewlet("myapp:templates/user_card.tk")
        def user_card(self, user):
            return {"user": user}

    @subscriber(BeforeRender, IBeforeViewletRender)
    def add_viewlets(event):
        request = event.get("request")
        if request:
            event["viewlets"] = MyViewlets(request=request)

In templates, use ``$literal()`` to render viewlet output::

    <div class="sidebar">
        $literal(viewlets.sidebar())
    </div>

    <div class="user-card">
        $literal(viewlets.user_card(user))
    </div>
"""
from functools import wraps

from pyramid.events import BeforeRender
from pyramid.interfaces import Attribute, IDict
from pyramid.renderers import get_renderer
from zope.interface import Interface, implementer


def render_fragment(tpl, dct, system):
    renderer = get_renderer(tpl)
    return renderer.fragment(tpl, dct, system)


def get_request(self_or_request):
    if hasattr(self_or_request, 'request'):
        return self_or_request.request

    return self_or_request


class IBeforeViewletRender(IDict):
    rendering_val = Attribute('The value returned by a view or passed to a '
                              '``render`` method for this rendering. '
                              'This feature is new in Pyramid 1.2.')


@implementer(IBeforeViewletRender)
class BeforeViewletRender(dict):
    def __init__(self, system, rendering_val=None):
        super(BeforeViewletRender, self).__init__(system)
        self.rendering_val = rendering_val


def viewlet(renderer):
    def wrap(func):
        @wraps(func)
        def wrapper(self_or_req, *a, **kw):
            request = get_request(self_or_req)

            renderval = func(self_or_req, *a, **kw)

            system = BeforeViewletRender(dict(request=request), renderval)
            request.registry.notify(system)
            return render_fragment(renderer, renderval, system)

        return wrapper

    return wrap
