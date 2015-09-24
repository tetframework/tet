# -*- coding: utf-8 -*-
from __future__ import absolute_import, division,\
       print_function, unicode_literals

from pyramid.decorator import reify
import venusian
import re


_to_underscores = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
def _underscore(name):
    return _to_underscores.sub(r'_\1', name).lower()


_is_iface_name = re.compile('^I[A-Z].*')
class ServiceRegistry(object):
    def __init__(self):
        self.__services__ = []

    def _register_service(self, instance, interface):
        self.__services__.append((instance, interface))
        name = interface.__name__
        if _is_iface_name.match(name):
            name = name[1:]

        setattr(self, _underscore(name), instance)


def get_service_registry(registry):
    if not hasattr(registry, 'services'):
        registry.services = ServiceRegistry()

    return registry.services


def service(interface):
    def service_decorator(wrapped):
        def callback(scanner, name, ob):
            registry = scanner.config.registry
            if not isinstance(registry.queryUtility(interface), ob):
                ob_instance = ob(registry=registry)
                get_service_registry(registry)._register_service(ob_instance, interface)
                registry.registerUtility(ob_instance, interface)

        info = venusian.attach(wrapped, callback, category='tet.service')
        return wrapped

    return service_decorator


def autowired(interface, name=None):
    @reify
    def getter(self):
        return self.registry.getUtility(interface)

    return getter


class BaseService(object):
    def __init__(self, **kw):
        try:
            self.registry = kw.pop('registry')
            super(BaseService, self).__init__(**kw)

        except KeyError:
            raise TypeError("Registry to the base business must be provided")


def scan_services(config, *a, **kw):
    kw['categories'] = ('tet.service',)
    return config.scan(*a, **kw)


def includeme(config):
    config.add_directive('scan_services', scan_services)
    config.registry.services = ServiceRegistry()
