============
Introduction
============

What is Tet?
============

Tet is an "unearthly intelligent batteries-included application framework built
on Pyramid." It extends the robust Pyramid web framework with additional
utilities, security features, and developer conveniences that make building web
applications more productive and secure.

Tet does not replace Pyramid — it *extends* it. Every Tet feature is an
ordinary Pyramid include or directive, so you can adopt as much or as little of
Tet as you like and remain fully compatible with the Pyramid ecosystem.

Core Philosophy
===============

Tet follows these core principles:

**Batteries Included**
  Tet provides commonly needed functionality out of the box, reducing the need
  to find and integrate multiple third-party packages.

**Security First**
  Security features like CSRF protection and safe JSON serialization are enabled
  by default and designed to prevent common vulnerabilities.

**Pyramid Compatible**
  Tet extends rather than replaces Pyramid, maintaining full compatibility with
  existing Pyramid applications and ecosystem.

**Developer Friendly**
  Enhanced development experience with better error handling, type hints, and
  comprehensive documentation.

Key Features Overview
=====================

Application Assembly
--------------------

* **App factory**: the ``application_factory`` decorator and
  ``create_configurator`` helper wire up a configured application with sensible
  defaults. See :doc:`configuration`.
* **Dependency injection**: request-scoped services via ``pyramid_di``, exposed
  through ``tet.services``. See :doc:`services`.
* **Views and viewlets**: enhanced ``view_config``, class-based controllers, and
  a composable viewlet system for reusable template fragments. See :doc:`views`
  and :doc:`viewlets`.

Rendering and Templating
------------------------

* **Tonnikala templates**: a fast templating renderer with ``$`` interpolation.
  See :doc:`templating`.
* **Safe JSON**: XSS-safe JSON serialization with custom type adapters for
  SQLAlchemy and datetime objects. See :doc:`json`.
* **Internationalization**: translation and pluralization helpers wired into
  requests and templates. See :doc:`i18n`.
* **Static assets**: cache-breaking static views so browsers always pick up new
  asset versions. See :doc:`static`.

Security
--------

* **CSRF Protection**: automatically enabled CSRF protection.
* **Authorization Policies**: request-aware authorization policies.
* **Safe serialization**: prevents XSS when embedding JSON in HTML.

See :doc:`security`.

Data and Utilities
------------------

* **SQLAlchemy integration**: root factories that convert SQL lookup errors into
  ``KeyError`` for clean traversal, plus session helpers. See :doc:`sqlalchemy`.
* **Utility modules**: cryptography, Base64/Crockford Base32, collections, path
  handling, and more. See :doc:`utilities`.
* **Decorators**: small helpers such as ``deprecated`` and ``reify_attr``. See
  :doc:`decorators`.

Framework Integration
=====================

Tet integrates with the broader Python web ecosystem:

* **Pyramid**: built on top of Pyramid's solid foundation.
* **SQLAlchemy**: enhanced ORM integration.
* **pyramid_di**: dependency injection with request-scoped services.
* **Passlib**: secure password handling.

Architecture
============

Tet uses a modular architecture where each component can be included
independently:

.. code-block:: python

    from pyramid.config import Configurator


    def main(global_config, **settings):
        with Configurator(settings=settings) as config:
            # Include only the Tet features you need
            config.include("tet.security.csrf")
            config.include("tet.renderers.json")
            config.include("tet.security.authorization")

            # Your application configuration
            # ...

            return config.make_wsgi_app()

This modular approach lets you adopt Tet features gradually and include only
what your application needs. For a higher-level entry point that wires the
common features together, see the ``application_factory`` decorator in
:doc:`configuration`.

Requirements
============

* **Python**: 3.8 or newer.
* **Pyramid**: 1.9 or newer.
* Core dependencies: ``pyramid``, ``passlib``, ``sqlalchemy``, ``pyramid_di``.

Tet is currently at version **0.5.0** and is tested on Python 3.8 through 3.14.

Getting Help
============

* **Documentation**: this documentation covers the framework in depth — see the
  :doc:`tutorials <../tutorials/index>` for step-by-step walkthroughs.
* **Source Code**: https://github.com/tetframework/tet
* **Issues**: report bugs and feature requests through the issue tracker.
