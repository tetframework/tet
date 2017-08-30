from inspect import isclass

from pyramid.request import Request
from pyramid.view import *
from pyramid.view import view_config as _pyramid_view_config
from tet.services import RequestScopedBaseService


class view_config(_pyramid_view_config):
    def __init__(self, **settings):
        super(view_config, self).__init__(**settings)


class expose(object):
    """
    """

    venusian = venusian

    def __init__(self, **settings):
        self.__dict__.update(settings)

    def __call__(self, wrapped):
        settings = self.__dict__.copy()

        def callback(context, name, ob):
            config = context.config.with_package(info.module)

            name = attr_name
            if name == 'index':
                name = ''

            def view_wrapper(request):
                # TODO: should we stack the request?
                return getattr(request.context, attr_name)()

            config.add_view(view=view_wrapper, name=name, context=ob, **settings)

        info = self.venusian.attach(wrapped, callback, category='pyramid')

        if info.scope != 'class':
            # if the decorator was attached to a method in a class, or
            # otherwise executed at class scope, we need to set an
            # 'attr' into the settings if one isn't already in there
            raise ValueError("expose can be only applied to instance methods!")

        attr_name = wrapped.__name__

        settings['_info'] = info.codeinfo # fbo "action_method"
        return wrapped


class BaseController(object):
    def __getitem__(self, name):
        if hasattr(self, '_lookup'):
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

        raise KeyError("Child not found: %s" % name)


class ServiceViews(RequestScopedBaseService):
    def __init__(self, request: Request):
        super().__init__(request=request)
        self.context = getattr(request, 'context', None)
