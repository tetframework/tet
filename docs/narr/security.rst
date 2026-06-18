=================
Security Features
=================

Tet provides several security enhancements over base Pyramid to help protect your applications from common web vulnerabilities.

CSRF Protection
===============

Tet enables CSRF (Cross-Site Request Forgery) protection by default through the ``tet.security.csrf`` module.

Basic Usage
-----------

To enable CSRF protection in your application:

.. code-block:: python

    from pyramid.config import Configurator


    def main():
        with Configurator() as config:
            config.include("tet.security.csrf")
            # CSRF protection is now enabled by default
            # with require_csrf=True

            return config.make_wsgi_app()

This automatically sets ``require_csrf=True`` as the default CSRF option, meaning all form submissions and state-changing requests will require CSRF tokens.

Working with CSRF Tokens
------------------------

In your templates, include CSRF tokens in forms:

.. code-block:: html

    <form method="post" action="/submit">
        <input type="hidden" name="csrf_token" value="$request.session.get_csrf_token()">
        <!-- Your form fields -->
        <input type="submit" value="Submit">
    </form>

For AJAX requests, include the CSRF token in headers:

.. code-block:: javascript

    $.ajaxSetup({
        headers: {
            'X-CSRF-Token': $('meta[name=csrf-token]').attr('content')
        }
    });

Enhanced Authorization
======================

Tet provides an enhanced authorization system that gives authorization policies access to the current request object.

Request-Aware Authorization Policies
------------------------------------

Traditional Pyramid authorization policies receive limited context. Tet's ``INewAuthorizationPolicy`` interface provides access to the request object:

.. code-block:: python

    from tet.security.authorization import INewAuthorizationPolicy
    from zope.interface import implementer


    @implementer(INewAuthorizationPolicy)
    class MyAuthorizationPolicy:
        def permits(self, request, context, principals, permission):
            # Access to request object for richer authorization logic
            if request.path.startswith("/admin/"):
                return "admin" in principals
            return True

        def principals_allowed_by_permission(self, request, context, permission):
            # This method is optional. If you do not use
            # pyramid.security.principals_allowed_by_permission, you may
            # raise NotImplementedError here instead.
            raise NotImplementedError()

Using Enhanced Authorization
----------------------------

Register your authorization policy with Tet:

.. code-block:: python

    from pyramid.config import Configurator


    def main():
        with Configurator() as config:
            config.include("tet.security.authorization")
            # set_authorization_policy is added by the include above
            config.set_authorization_policy(MyAuthorizationPolicy())

            return config.make_wsgi_app()

Including ``tet.security.authorization`` adds the
``config.set_authorization_policy`` directive. When you pass an object
providing ``INewAuthorizationPolicy`` (or a dotted name resolving to one),
it is wrapped in ``AuthorizationPolicyWrapper``, which implements Pyramid's
``IAuthorizationPolicy``. The wrapper retrieves the current request via
``pyramid.threadlocal.get_current_request`` and passes it as the first
argument to your policy's ``permits`` and
``principals_allowed_by_permission`` methods. Objects that do not provide
``INewAuthorizationPolicy`` are passed through to Pyramid unchanged.

SQLAlchemy Security
===================

Tet provides secure SQLAlchemy integration through the ``SQLARootFactory`` class.

Safe Root Factory
-----------------

The ``SQLARootFactory`` properly handles SQL exceptions and converts them to appropriate HTTP errors:

.. code-block:: python

    from tet.sqlalchemy.factory import SQLARootFactory
    from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
    from sqlalchemy.exc import DataError


    class MyRootFactory(SQLARootFactory):
        def supplier(self, item):
            # Your logic to fetch objects by ID
            session = self.request.dbsession
            try:
                return session.query(MyModel).filter_by(id=item).one()
            except (NoResultFound, MultipleResultsFound, DataError):
                # These exceptions are automatically converted to KeyError
                # which Pyramid translates to 404 Not Found
                raise

Exception Handling
------------------

The root factory automatically converts these SQL exceptions to ``KeyError``:

* ``NoResultFound``: When a query returns no results
* ``MultipleResultsFound``: When a unique query returns multiple results
* ``DataError``: When there are data-related SQL errors (e.g., invalid UUID format)

This prevents SQL errors from leaking to users and provides appropriate HTTP error responses.

Input Validation and Sanitization
=================================

While Tet doesn't provide input validation directly, it integrates well with validation libraries and provides utilities for safe data handling.

Safe JSON Serialization
-----------------------

Use Tet's JSON utilities to prevent XSS when embedding JSON in HTML:

.. code-block:: python

    from tet.util.json import js_safe_dumps

    # Safe for embedding in HTML/JavaScript
    safe_json = js_safe_dumps(user_data)

    # In your template:
    # <script>var userData = $literal(safe_json);</script>

The ``js_safe_dumps`` function escapes dangerous characters:

* ``<`` → ``\\u003c``
* ``>`` → ``\\u003e``
* ``/`` → ``\\u002f``
* ``&`` → ``\\u0026``
* ``\u2028`` → ``\\u2028`` (Line separator)
* ``\u2029`` → ``\\u2029`` (Paragraph separator)

Security Best Practices
=======================

When using Tet, follow these security best practices:

**Always Enable CSRF Protection**
  Include ``tet.security.csrf`` in production applications.

**Use Safe JSON Serialization**
  Use ``tet.util.json.js_safe_dumps`` when embedding JSON in HTML.

**Implement Proper Authorization**
  Use Tet's enhanced authorization policies for fine-grained access control.

**Handle SQL Exceptions Properly**
  Use ``SQLARootFactory`` or similar patterns to prevent information leakage.

**Validate All Inputs**
  While Tet provides utilities, always validate and sanitize user inputs.

**Keep Dependencies Updated**
  Regularly update Tet and its dependencies to get security fixes.

Security Considerations
=======================

**Session Security**
  Configure secure session settings in production:

.. code-block:: python

    settings = {
        "session.secret": "your-secret-key",
        "session.secure": True,  # HTTPS only
        "session.httponly": True,  # No JavaScript access
        "session.samesite": "Strict",  # CSRF protection
    }

**HTTPS in Production**
  Always use HTTPS in production environments and configure appropriate security headers.

**Database Security**
  Use parameterized queries (SQLAlchemy ORM does this automatically) and proper database permissions.
