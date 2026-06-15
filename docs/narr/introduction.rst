============
Introduction
============

What is Tet?
============

Tet is an "unearthly intelligent batteries-included application framework built on Pyramid." It extends the robust Pyramid web framework with additional utilities, security features, and developer conveniences that make building web applications more productive and secure.

Core Philosophy
===============

Tet follows these core principles:

**Batteries Included**
  Tet provides commonly needed functionality out of the box, reducing the need to find and integrate multiple third-party packages.

**Security First**
  Security features like CSRF protection and safe JSON serialization are enabled by default and designed to prevent common vulnerabilities.

**Pyramid Compatible**
  Tet extends rather than replaces Pyramid, maintaining full compatibility with existing Pyramid applications and ecosystem.

**Developer Friendly**
  Enhanced development experience with better error handling, type hints, and comprehensive documentation.

Key Features Overview
====================

Enhanced Security
-----------------

Tet provides several security enhancements:

* **CSRF Protection**: Automatically enabled CSRF protection for forms
* **Authorization Policies**: Enhanced authorization with request-aware policies
* **Safe JSON Serialization**: Prevents XSS attacks when embedding JSON in HTML
* **SQL Injection Prevention**: Proper exception handling in SQLAlchemy factories

JSON Handling
------------

Tet includes advanced JSON handling capabilities:

* **XSS Prevention**: Automatic escaping of dangerous characters for inline JavaScript
* **Custom Type Adapters**: Built-in support for SQLAlchemy and datetime objects
* **Safe Serialization**: Unicode and HTML-safe JSON output

SQLAlchemy Integration
---------------------

Enhanced database support:

* **Root Factories**: Custom traversal root factories with proper exception handling
* **Session Management**: Enhanced session handling patterns
* **Type Safety**: Proper conversion of SQL exceptions to appropriate HTTP errors

Utility Modules
--------------

Comprehensive utility modules:

* **Cryptography**: Password hashing and security utilities
* **Collections**: Enhanced collection types and utilities
* **Path Handling**: File and path manipulation utilities
* **Export Functions**: Data export and serialization helpers

Framework Integration
====================

Tet integrates with the broader Python web ecosystem:

* **Pyramid**: Built on top of Pyramid's solid foundation
* **SQLAlchemy**: Enhanced ORM integration
* **pyramid_di**: Dependency injection with request-scoped services
* **Passlib**: Secure password handling

Architecture
===========

Tet uses a modular architecture where each component can be included independently:

.. code-block:: python

    from pyramid.config import Configurator

    def main():
        with Configurator() as config:
            # Include only the Tet features you need
            config.include('tet.security.csrf')
            config.include('tet.renderers.json')
            config.include('tet.security.authorization')

            # Your application configuration
            # ...

            return config.make_wsgi_app()

This modular approach allows you to adopt Tet features gradually and only include what your application needs.

Version History
==============

**Version 0.4.1** (Current)
  * Request-scoped services with pyramid_di integration
  * Enhanced SQLAlchemy root factory
  * Improved namespace package support
  * Python 3.6+ compatibility

**Version 0.4.0**
  * Replace zodb integration
  * pyramid_di integration improvements
  * Various bug fixes

**Earlier Versions**
  * Initial namespace package conversion
  * SQLAlchemy factory improvements
  * Package renamed to 'tet'

Getting Help
===========

* **Documentation**: This comprehensive documentation covers all aspects of Tet
* **Source Code**: Available on GitHub (if public repository exists)
* **Issues**: Report bugs and feature requests through the issue tracker
* **Community**: Connect with other Tet users and contributors
