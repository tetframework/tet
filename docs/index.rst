===
Tet
===

**Unearthly intelligent batteries-included application framework built on Pyramid**

Tet is a web application framework that extends the Pyramid web framework with additional utilities, security features, and developer conveniences. It provides enhanced JSON handling, security features, SQLAlchemy integration, and various utility modules to make web development more productive.

Getting Started
===============

Installation
------------

Install Tet using pip::

    pip install tet

Quick Example
-------------

Here's a simple "Hello World" application using Tet's application factory::

    from tet.config import application_factory, ALL_FEATURES
    from pyramid.response import Response


    def hello_world(request):
        return Response('Hello World!')


    @application_factory(included_features=ALL_FEATURES)
    def main(config):
        """Tet application factory."""
        config.add_route('hello', '/')
        config.add_view(hello_world, route_name='hello')


    if __name__ == '__main__':
        from wsgiref.simple_server import make_server
        app = main({})  # Empty global_config
        server = make_server('0.0.0.0', 6543, app)
        server.serve_forever()

Documentation
=============

.. toctree::
   :maxdepth: 2

   narr/index
   tutorials/index
   api/index

Key Features
============

**Enhanced Security**
   Built-in CSRF protection, enhanced authorization policies, and safe JSON serialization.

**SQLAlchemy Integration**
   Custom root factories and enhanced database support with proper exception handling.

**JSON Utilities** 
   Safe JavaScript JSON serialization with XSS prevention and custom type adapters.

**Pyramid Extensions**
   Enhanced request/response objects, session management, and various utility modules.

**Developer Friendly**
   Comprehensive testing support, type hints, and extensive documentation.

Support and Development
=======================

* **GitHub Repository**: https://github.com/tetframework/tet (if available)
* **Issue Tracker**: Report bugs and request features
* **Documentation**: Complete API and narrative documentation
* **Author**: Antti Haapala <antti.haapala@anttipatterns.com>

Framework Integration
=====================

Tet integrates seamlessly with the Pyramid ecosystem:

* **Pyramid**: Built on top of the robust Pyramid web framework
* **SQLAlchemy**: Enhanced ORM integration with custom factories
* **pyramid_di**: Dependency injection support with request-scoped services
* **Passlib**: Password hashing and security utilities

What's New
==========

Version 0.4.1 includes:

* Request-scoped services with pyramid_di integration
* Enhanced SQLAlchemy root factory with proper exception handling
* Improved namespace package support
* Python 3.6+ compatibility

License
=======

Tet is licensed under the Python Software Foundation License.

Indices and Tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`