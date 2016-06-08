from pyramid.renderers import get_renderer
from functools import wraps
from pyramid.events import BeforeRender
from pyramid.interfaces import IDict, Attribute
from zope.interface import (
    implementer,
    Interface
)


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
