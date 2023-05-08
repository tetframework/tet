from pyramid.config import Configurator
from tet.decorators import reify_attr
from zope.interface import Interface
from zope.interface.interface import InterfaceClass

# noinspection PyUnresolvedReferences
from pyramid_di import (ServiceRegistry, get_service_registry, service, autowired, BaseService,
                        RequestScopedBaseService,
                        register_di_service, )


def register_tet_service(config: Configurator,
                         service_factory,
                         *,
                         scope='global',
                         interface=Interface,
                         name='',
                         context_iface=Interface, ):
    return register_di_service(config, service_factory, scope=scope, interface=interface, name=name,
                               context_iface=context_iface)


def includeme(config):
    config.include('pyramid_di')
    config.add_directive('register_tet_service', register_tet_service)
