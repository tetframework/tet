"""
Static file serving with cache-busting support.

This module provides utilities for serving static files with automatic
cache-busting via versioned URLs. When the application starts, a unique
cache-breaker token is generated based on the current timestamp.

Features
--------

- Automatic cache-busting URLs for static assets
- Graceful handling of old cache-breaker values (301 redirect)
- Graceful handling of future cache-breaker values (503 retry)

Example
-------

Setting up static files with cache-busting::

    from tet.config import application_factory

    @application_factory()
    def main(config):
        config.include("tet.static")
        config.add_static_view_with_breaker(
            name="static/{breaker}",
            path="myapp:static",
        )
        config.scan()

In templates, use the versioned URL::

    <link href="${request.static_url('myapp:static/style.css')}" rel="stylesheet">
"""
import os
import time
from pipes import quote

from pyramid.httpexceptions import (
    HTTPMovedPermanently,
    HTTPNotFound,
    HTTPServiceUnavailable,
)

# todo: use other versioning where possible
cachebreaker = None


def set_cachebreaker(config, cachebreaker):
    config.registry.cachebreaker = cachebreaker


def make_redirector(redirected_route):
    def redirect_breaker(request):
        current_breaker = request.registry.cachebreaker
        breaker = request.matchdict['breaker']
        path = request.matchdict['path']

        if breaker < current_breaker:
            return HTTPMovedPermanently(request.route_url(redirected_route, breaker=current_breaker, path=path))

        # too recent breaker
        if breaker > current_breaker:
            # return 503 Service Unavailable - retry after 3 seconds
            rv = HTTPServiceUnavailable()
            rv.retry_after = 3
            return rv

        # finally come here, if no match found in static assets
        return HTTPNotFound("No such asset")

    return redirect_breaker


def add_static_view_with_breaker(config, name, path, **kw):
    if not '{breaker}' in name:
        raise ValueError("Invalid path to add_static_view_with_breaker: missing name")

    url = name.replace('{breaker}', config.registry.cachebreaker)
    config.add_static_view(name=url, path=path, **kw)

    redirected_route = name + '-redirect'
    redirected_url = name.rstrip('/') + '/*path'
    config.add_route(name=name + '-breaker',       pattern=redirected_url)
    config.add_view(route_name=name + '-breaker',  view=make_redirector(redirected_route))
    config.add_route(name=redirected_route,        pattern=redirected_url, static=True)


def includeme(config):
    config.registry.cachebreaker = "%012d" % int(time.time() * 1000)
    config.add_directive('set_cachebreaker', set_cachebreaker)
    config.add_directive('add_static_view_with_breaker', add_static_view_with_breaker)
