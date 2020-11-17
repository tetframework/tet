from typing import Callable, Any

import sys

from collections import ChainMap
from collections.abc import Mapping
from functools import wraps
from pyramid.config import *

from pyramid.config import Configurator
from tet.decorators import deprecated
from tet.i18n import configure_i18n
from tet.util.collections import flatten
from tet.util.path import caller_package


class TetAppFactory(object):
    """
    This method is deprecated in favour of procedural configuration /
    pyramid_zcml with create_configurator. See `application_factory`
    decorator for more details.
    """

    scan = None
    includes = []
    excludes = []
    i18n = True
    default_i18n_domain = None
    settings = {}
    global_config = None

    # :type config: Configurator
    config = None
    default_includes = [
        'tet.services',
        'tet.renderers.json'
    ]

    @deprecated
    def __new__(cls, global_config, **settings_kw):
        instance = cls.instantiate()
        instance.init_app_factory(global_config, settings_kw)
        return instance.construct_app()

    @classmethod
    def instantiate(cls):
        return super(TetAppFactory, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        super(TetAppFactory, self).__init__()

    def _dummy(self, config: Configurator):
        pass

    def init_app_factory(self, global_config, settings):
        self.settings = settings
        self.global_config = global_config
        self.config = self.make_configurator()

        self.do_default_includes()

    def do_default_includes(self):
        excludes = set(self.excludes)

        def conditional_include(item):
            if item not in excludes:
                self.config.include(item)

        for item in self.default_includes:
            conditional_include(item)

    def prepare_i18n(self):
        if self.i18n:
            configure_i18n(self.config, self.default_i18n_domain)

    def make_configurator(self) -> Configurator:
        return Configurator(settings=self.settings)

    pre_configure_app = _dummy
    configure_db = _dummy

    def configure_app(self, config: Configurator) -> None:
        self.configure_db(config)
        self.configure_routes(config)

    def configure_routes(self, config: Configurator) -> None:
        pass

    def post_configure_app(self, config: Configurator) -> None:
        pass

    def do_scan(self) -> None:
        self.config.scan(self.scan)

    def do_include(self) -> None:
        for i in self.includes:
            self.config.include(i)

    def construct_app(self) -> None:
        if self.includes:
            self.do_include()

        self.prepare_i18n()
        self.pre_configure_app(self.config)
        self.configure_app(self.config)
        self.post_configure_app(self.config)

        if self.scan:
            self.do_scan()

        return self.wrap_app(self.config.make_wsgi_app())

    def wrap_app(self, app) -> None:
        return app

    @classmethod
    @deprecated
    def main(cls, global_config, **settings):
        return cls(global_config, **settings)


ALL_FEATURES = [
    'services',
    'i18n',
    'renderers.json',
    'renderers.tonnikala',
    'renderers.tonnikala.i18n',
    'security.authorization',
    'security.csrf'
]

MINIMAL_FEATURES = []


def create_configurator(*,
                        global_config=None,
                        settings=None,
                        merge_global_config=True,
                        configurator_class=Configurator,
                        included_features=(),
                        excluded_features=(),
                        package=None,
                        **kw) -> Configurator:

    defaults = {}
    if merge_global_config and isinstance(global_config, Mapping):
        settings = ChainMap(settings, global_config, defaults)

    extracted_settings = {}

    if package is None:
        package = caller_package(ignored_modules=[__name__])

    for name in ['default_i18n_domain']:
        if name in kw:
            extracted_settings[name] = kw.pop(name)

    if hasattr(package, '__name__'):
        package_name = package.__name__
    else:
        package_name = package

    defaults['default_i18n_domain'] = package_name

    config = configurator_class(settings=settings,
                                package=package,
                                **kw)
    config.add_settings(extracted_settings)
    included_features = list(flatten(included_features))
    excluded_features = set(flatten(excluded_features))

    feature_set = set(included_features) - set(excluded_features)
    config.registry.tet_features = feature_set

    for feature_name in included_features:
        if feature_name in feature_set:
            try:
                config.include('tet.' + feature_name)
            except Exception as e:
                print('Unable to include feature {}: {}'.format(
                    feature_name,
                    e
                ), file=sys.stderr)
                raise

    return config


def application_factory(factory_function: Callable[[Configurator], Any]=None,
                        configure_only=False,
                        included_features=ALL_FEATURES,
                        excluded_features=(),
                        package=None,
                        **extra_parameters):
    """
    A decorator for main method / application configurator for Tet. The
    wrapped function must accept a single argument - the Configurator. The
    wrapper itself accepts arguments (global_config, **settings) like an
    ordinary Pyramid/Paster application entry point does.

    If configure_only=False (the default), then the return value is a
    WSGI application created from the configurator.

    `included_features` contains an iterable of features that should be
    automatically included in the application. By default all standard Tet
    features are  included. For maximal future compatibility you can specify the
    included feature names here.

    `excluded_features` should be an iterable of features that shouldn't be
     automatically included - this serves as a fast way to get all standard
     features except a named few.

    `package` should be the package passed to the Configurator object;
    otherwise the package of the caller is assumed.

    :param factory_function: The actual wrapped factory function that
    accepts parameter (config: Configurator)
    :param configure_only: True if no WSGI application is to be made, false
    to actually create the WSGI application as the return value
    :param included_features: The iterable of included features. This can
    in turn contain other iterables; they are flattened by the wrapper into
    a list of strings.
    :param excluded_features: The iterable of excluded features. This can
    in turn contain other iterables; they are flattened by the wrapper into
    a list of strings.
    :param extra_parameters: extra parameters that will be passed as-is to
    the actual configurator generation.
    :return: the WSGI app if `configure_only` is `False`; `config`, if
    `configure_only` is `True`.
    """

    if package is None:
        package = caller_package(ignored_modules=[__name__])

    def decorator(function):
        @wraps(function)
        def wrapper(*a, **kw):
            if len(a) > 1:
                raise TypeError('application_factory wrapped function '
                                'called with more than 1 positional argument')

            global_config = a[0] if a else None
            settings = kw
            config = create_configurator(global_config=global_config,
                                         settings=settings,
                                         included_features=included_features,
                                         excluded_features=excluded_features,
                                         package=package,
                                         **extra_parameters)

            returned = function(config)
            if isinstance(returned, Configurator):
                config = returned

            if not configure_only:
                return config.make_wsgi_app()
            else:
                return returned

        return wrapper

    if factory_function is not None:
        if not callable(factory_function):
            raise TypeError("Factory function was specified but not callable")
        else:
            return decorator(factory_function)

    else:
        return decorator
