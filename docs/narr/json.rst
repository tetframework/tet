=============
JSON Handling
=============

Tet provides enhanced JSON handling capabilities that go beyond Python's standard JSON module, with built-in security features and custom type adapters.

Safe JavaScript Serialization
=============================

One of Tet's key security features is safe JSON serialization that prevents XSS attacks when embedding JSON data in HTML pages.

The Problem
-----------

Standard JSON serialization can be unsafe when embedded in HTML:

.. code-block:: python

    import json

    # This data contains potentially dangerous characters
    user_data = {"message": "</script><script>alert('XSS')</script>"}

    # Standard JSON - UNSAFE for HTML embedding
    unsafe_json = json.dumps(user_data)
    # Result: {"message": "</script><script>alert('XSS')</script>"}

When embedded in HTML, this could execute malicious JavaScript:

.. code-block:: text

    <!-- DANGEROUS - DON'T DO THIS -->
    <script>
        var userData = {"message": "</script><script>alert('XSS')</script>"};
    </script>

The Solution: js_safe_dumps
---------------------------

Tet's ``js_safe_dumps`` function escapes dangerous characters:

.. code-block:: python

    from tet.util.json import js_safe_dumps

    user_data = {"message": "</script><script>alert('XSS')</script>"}

    # Safe for embedding in HTML/JavaScript
    safe_json = js_safe_dumps(user_data)
    # Result: {"message": "\\u003c/script\\u003e\\u003cscript\\u003ealert('XSS')\\u003c/script\\u003e"}

Escaped Characters
------------------

``js_safe_dumps`` escapes these dangerous characters:

* ``<`` → ``\\u003c`` (Prevents tag injection)
* ``>`` → ``\\u003e`` (Prevents tag injection)
* ``/`` → ``\\u002f`` (Prevents script tag closing)
* ``&`` → ``\\u0026`` (Prevents HTML entity issues)
* ``\u2028`` → ``\\u2028`` (Line separator - can break JavaScript)
* ``\u2029`` → ``\\u2029`` (Paragraph separator - can break JavaScript)

Usage in Templates
------------------

Use the safe JSON in your templates:

.. code-block:: html

    <script>
        var userData = ${safe_json|n};
    </script>

The ``|n`` filter outputs the value without HTML-escaping in the Tonnikala template engine, which is what you want since ``js_safe_dumps`` has already produced a string that is safe to embed in a ``<script>`` element.

Enhanced JSON Renderer
======================

Tet provides an enhanced JSON renderer that automatically handles common Python types.

Built-in Type Adapters
----------------------

The enhanced renderer includes adapters for:

**SQLAlchemy NamedTuple Results**
  Automatically converts SQLAlchemy ``AbstractKeyedTuple`` objects to dictionaries:

.. code-block:: python

    # Query result will be automatically serializable
    result = session.query(User.name, User.email).first()
    # The tuple can be directly returned from a view

**Datetime Objects**
  Automatic ISO format serialization for dates and datetimes:

.. code-block:: python

    from datetime import datetime, date

    data = {"created": datetime.now(), "birthday": date(1990, 1, 1)}
    # Will serialize as:
    # {
    #     'created': '2024-01-15T10:30:00',
    #     'birthday': '1990-01-01'
    # }

Using the Enhanced Renderer
---------------------------

Enable the enhanced JSON renderer in your application:

.. code-block:: python

    from pyramid.config import Configurator


    def main():
        with Configurator() as config:
            config.include("tet.renderers.json")
            # Enhanced JSON renderer is now available

            return config.make_wsgi_app()

The renderer is automatically registered as the default ``json`` renderer.

Custom JSON Adapters
====================

You can register custom adapters for your own types.

Adding Custom Adapters
----------------------

Use the ``add_json_adapter`` directive to register custom type adapters:

.. code-block:: python

    from decimal import Decimal
    from pyramid.config import Configurator


    def decimal_adapter(obj, request):
        return str(obj)


    def main():
        with Configurator() as config:
            config.include("tet.renderers.json")

            # Add custom adapter for Decimal
            config.add_json_adapter(for_=Decimal, adapter=decimal_adapter)

            return config.make_wsgi_app()

Multiple Renderers
------------------

You can register multiple JSON renderers with different names:

.. code-block:: python

    from pyramid.renderers import JSON


    def main():
        with Configurator() as config:
            config.include("tet.renderers.json")

            # Create a custom renderer for API responses
            api_renderer = JSON()
            api_renderer.add_adapter(MyModel, lambda obj, req: obj.to_dict())

            config.add_json_renderer(renderer=api_renderer, name="api_json")

            return config.make_wsgi_app()

Then use it in your views:

.. code-block:: python

    @view_config(route_name="api_endpoint", renderer="api_json")
    def api_view(request):
        return {"data": MyModel.query.all()}

JSON in Views
=============

Using JSON renderers in your Pyramid views is straightforward.

Basic JSON Response
-------------------

.. code-block:: python

    @view_config(route_name="api", renderer="json")
    def api_view(request):
        return {
            "status": "success",
            "data": get_some_data(),
            "timestamp": datetime.now(),  # Automatically converted
        }

Handling JSON Input
-------------------

For processing JSON request bodies:

.. code-block:: python

    @view_config(route_name="api_post", request_method="POST", renderer="json")
    def api_post_view(request):
        try:
            json_data = request.json_body
        except ValueError:
            return {"error": "Invalid JSON"}

        # Process the JSON data
        result = process_data(json_data)

        return {"result": result}

Error Handling
--------------

Handle JSON-related errors gracefully:

.. code-block:: python

    from pyramid.httpexceptions import HTTPBadRequest


    @view_config(route_name="api", renderer="json")
    def api_view(request):
        try:
            data = request.json_body
        except ValueError as e:
            raise HTTPBadRequest(json_body={"error": "Invalid JSON: " + str(e)})

        return process_data(data)

Performance Considerations
==========================

**Caching JSON Responses**
  Consider caching frequently requested JSON data:

.. code-block:: python

    from functools import lru_cache


    @lru_cache(maxsize=100)
    def get_cached_data():
        return expensive_data_operation()


    @view_config(route_name="api", renderer="json")
    def api_view(request):
        return {"data": get_cached_data()}

**Large Data Sets**
  For large data sets, consider pagination or streaming:

.. code-block:: python

    @view_config(route_name="api", renderer="json")
    def api_view(request):
        page = int(request.params.get("page", 1))
        limit = int(request.params.get("limit", 20))

        data = get_paginated_data(page=page, limit=limit)

        return {"data": data, "page": page, "limit": limit, "has_more": len(data) == limit}

Best Practices
==============

**Always Use Safe Serialization**
  When embedding JSON in HTML, always use ``js_safe_dumps``.

**Register Type Adapters**
  Register adapters for your custom types to ensure consistent serialization.

**Handle Errors Gracefully**
  Always handle JSON parsing errors and return appropriate error responses.

**Use Appropriate HTTP Status Codes**
  Return proper HTTP status codes with your JSON responses.

**Validate JSON Input**
  Always validate JSON input data before processing.

**Consider Security**
  Be careful about what data you include in JSON responses to avoid information leakage.
