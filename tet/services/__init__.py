"""
Dependency injection support for Tet applications.

This module provides dependency injection via ``pyramid_di``. It is included
automatically when using the ``services`` feature.

Example
-------

Defining a service::

    from pyramid_di import service, RequestScopedBaseService, autowired

    @service()
    class UserService(RequestScopedBaseService):
        def get_user(self, user_id):
            return self.request.dbsession.query(User).get(user_id)

    @service()
    class OrderService(RequestScopedBaseService):
        user_service = autowired(UserService)

        def get_user_orders(self, user_id):
            user = self.user_service.get_user(user_id)
            return user.orders

Setup and scanning services::

    from tet.config import application_factory

    @application_factory(included_features=["services"])
    def main(config):
        config.scan_services("myapp.services")
        config.scan()

Using services in class-based views::

    from pyramid.view import view_config
    from pyramid_di import autowired
    from myapp.services import UserService

    class UserViews:
        user_service = autowired(UserService)

        def __init__(self, request):
            self.request = request

        @view_config(route_name="user", renderer="json")
        def get_user(self):
            return self.user_service.get_user(self.request.matchdict["id"])

Using services in function-based views::

    from pyramid.view import view_config
    from myapp.services import UserService

    @view_config(route_name="user", renderer="json")
    def get_user(request):
        user_service = request.find_service(UserService)
        return user_service.get_user(request.matchdict["id"])
"""
from pyramid.config import Configurator


def includeme(config: Configurator) -> None:
    """Include pyramid_di for dependency injection support."""
    config.include("pyramid_di")
