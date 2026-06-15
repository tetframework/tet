==============
JSON Tutorial
==============

This tutorial covers Tet's advanced JSON handling capabilities, including safe serialization, custom adapters, and XSS prevention.

Enhanced JSON Renderer
======================

Tet provides an enhanced JSON renderer that automatically handles common Python types and provides security features.

Basic Setup
-----------

Enable Tet's JSON renderer in your application:

.. code-block:: python

    from pyramid.config import Configurator

    def main():
        with Configurator() as config:
            # Include Tet's enhanced JSON renderer
            config.include('tet.renderers.json')
            
            return config.make_wsgi_app()

The enhanced renderer automatically handles:

- **datetime objects**: Converted to ISO format strings
- **date objects**: Converted to ISO format strings  
- **SQLAlchemy NamedTuple results**: Converted to dictionaries

Built-in Type Support
---------------------

.. code-block:: python

    from datetime import datetime, date
    from pyramid.view import view_config

    @view_config(route_name='api_data', renderer='json')
    def api_data_view(request):
        return {
            'timestamp': datetime.now(),           # Automatically converted
            'birthday': date(1990, 5, 15),        # Automatically converted
            'message': 'Hello, World!',
            'count': 42
        }

    # Output:
    # {
    #     "timestamp": "2024-01-15T10:30:00",
    #     "birthday": "1990-05-15", 
    #     "message": "Hello, World!",
    #     "count": 42
    # }

SQLAlchemy Integration
---------------------

The JSON renderer automatically handles SQLAlchemy query results:

.. code-block:: python

    @view_config(route_name='user_stats', renderer='json')
    def user_stats(request):
        session = request.dbsession
        
        # Named tuple results are automatically serializable
        stats = session.query(
            User.name,
            User.email,
            func.count(Post.id).label('post_count')
        ).outerjoin(Post).group_by(User.id).all()
        
        return {'user_stats': stats}  # Automatically converted to list of dicts

Custom JSON Adapters
===================

Create custom adapters for your own types.

Simple Type Adapters
-------------------

.. code-block:: python

    from decimal import Decimal
    from uuid import UUID

    def decimal_adapter(obj, request):
        """Convert Decimal to string to avoid precision loss."""
        return str(obj)

    def uuid_adapter(obj, request):
        """Convert UUID to string."""
        return str(obj)

    def main():
        with Configurator() as config:
            config.include('tet.renderers.json')
            
            # Add custom adapters
            config.add_json_adapter(for_=Decimal, adapter=decimal_adapter)
            config.add_json_adapter(for_=UUID, adapter=uuid_adapter)
            
            return config.make_wsgi_app()

Model Adapters
-------------

Create adapters for your SQLAlchemy models:

.. code-block:: python

    class User(Base):
        __tablename__ = 'users'
        
        id = Column(Integer, primary_key=True)
        username = Column(String(50), unique=True)
        email = Column(String(100))
        password_hash = Column(String(128))  # Sensitive data
        created_at = Column(DateTime, default=datetime.utcnow)
        is_active = Column(Boolean, default=True)

    def user_adapter(user, request):
        """Safe user serialization - excludes sensitive data."""
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at,  # Automatically converted by Tet
            'is_active': user.is_active
            # Note: password_hash is deliberately excluded
        }

    # Register the adapter
    config.add_json_adapter(for_=User, adapter=user_adapter)

Context-Aware Adapters
---------------------

Adapters receive the request object, allowing for context-aware serialization:

.. code-block:: python

    def user_context_adapter(user, request):
        """Context-aware user serialization."""
        base_data = {
            'id': user.id,
            'username': user.username,
            'is_active': user.is_active
        }
        
        # Include email only for authenticated users
        if request.authenticated_userid:
            base_data['email'] = user.email
        
        # Include admin data for admin users
        if 'group:admin' in request.effective_principals:
            base_data.update({
                'created_at': user.created_at,
                'last_login': user.last_login,
                'login_count': user.login_count
            })
        
        return base_data

Multiple JSON Renderers
=======================

You can register multiple JSON renderers for different purposes.

Specialized Renderers
--------------------

.. code-block:: python

    from pyramid.renderers import JSON

    def main():
        with Configurator() as config:
            config.include('tet.renderers.json')
            
            # Create specialized renderers
            
            # Pretty-printed JSON for debugging
            debug_renderer = JSON(indent=2, sort_keys=True)
            config.add_json_renderer(
                renderer=debug_renderer,
                name='debug_json'
            )
            
            # Compact JSON for APIs
            api_renderer = JSON(separators=(',', ':'))
            config.add_json_renderer(
                renderer=api_renderer,
                name='api_json'
            )
            
            # Public API renderer with limited data
            public_renderer = JSON()
            public_renderer.add_adapter(User, user_public_adapter)
            config.add_json_renderer(
                renderer=public_renderer,
                name='public_json'
            )
            
            return config.make_wsgi_app()

Using Different Renderers
-------------------------

.. code-block:: python

    @view_config(route_name='debug_data', renderer='debug_json')
    def debug_view(request):
        return {'complex_data': get_complex_debug_data()}

    @view_config(route_name='api_data', renderer='api_json')
    def api_view(request):
        return {'users': User.query.all()}

    @view_config(route_name='public_api', renderer='public_json')
    def public_api_view(request):
        return {'users': User.query.filter_by(is_public=True).all()}

Safe JavaScript Serialization
=============================

Tet provides utilities to safely embed JSON in HTML pages, preventing XSS attacks.

The XSS Problem
--------------

Standard JSON serialization can be dangerous when embedded in HTML:

.. code-block:: python

    import json

    # Dangerous user input
    user_input = {"message": "</script><script>alert('XSS')</script>"}

    # Standard JSON - UNSAFE
    json_string = json.dumps(user_input)
    # {"message": "</script><script>alert('XSS')</script>"}

When embedded in HTML:

.. code-block:: html

    <!-- DANGEROUS - DON'T DO THIS -->
    <script>
        var data = {"message": "</script><script>alert('XSS')</script>"};
    </script>
    <!-- The XSS payload executes! -->

Safe Serialization Solution
---------------------------

Use Tet's ``js_safe_dumps`` function:

.. code-block:: python

    from tet.util.json import js_safe_dumps

    # Safe serialization
    safe_json = js_safe_dumps(user_input)
    # {"message": "\\u003c/script\\u003e\\u003cscript\\u003ealert('XSS')\\u003c/script\\u003e"}

    @view_config(route_name='user_page', renderer='mytemplate.pt')
    def user_page_view(request):
        user_data = {
            'name': request.user.name,
            'preferences': request.user.preferences,
            'bio': request.user.bio  # Could contain dangerous content
        }
        
        # Safe for HTML embedding
        safe_user_json = js_safe_dumps(user_data)
        
        return {'user_json': safe_user_json}

Template Integration
-------------------

In your Chameleon template:

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        <title>User Profile</title>
    </head>
    <body>
        <div id="user-profile"></div>
        
        <script>
            // Safe JSON embedding - no XSS risk
            var userData = ${user_json|n};
            
            // Use the data safely
            document.getElementById('user-profile').innerHTML = 
                '<h1>' + escapeHtml(userData.name) + '</h1>' +
                '<p>' + escapeHtml(userData.bio) + '</p>';
            
            function escapeHtml(text) {
                var div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
        </script>
    </body>
    </html>

Advanced JSON Handling
======================

Complex serialization scenarios and patterns.

Nested Object Serialization
---------------------------

Handle complex nested objects:

.. code-block:: python

    class BlogPost(Base):
        __tablename__ = 'posts'
        
        id = Column(Integer, primary_key=True)
        title = Column(String(200))
        content = Column(Text)
        author_id = Column(Integer, ForeignKey('users.id'))
        created_at = Column(DateTime, default=datetime.utcnow)
        
        # Relationship
        author = relationship('User', back_populates='posts')
        comments = relationship('Comment', back_populates='post')

    def post_adapter(post, request):
        """Serialize blog post with nested objects."""
        return {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'created_at': post.created_at,
            'author': {
                'id': post.author.id,
                'username': post.author.username
            },
            'comment_count': len(post.comments),
            'comments': [
                {
                    'id': comment.id,
                    'content': comment.content,
                    'author': comment.author.username,
                    'created_at': comment.created_at
                }
                for comment in post.comments[:5]  # Limit to recent comments
            ]
        }

Pagination-Aware JSON
--------------------

Handle paginated results:

.. code-block:: python

    def paginated_adapter(query_result, request):
        """Adapter for paginated query results."""
        page = int(request.params.get('page', 1))
        per_page = int(request.params.get('per_page', 20))
        
        # Paginate the query
        total = query_result.count()
        items = query_result.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            'items': items,  # Will be serialized by their own adapters
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page,
                'has_next': page * per_page < total,
                'has_prev': page > 1
            }
        }

Error Response JSON
------------------

Standardize error responses:

.. code-block:: python

    from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound

    class APIError(Exception):
        def __init__(self, message, code=None, details=None):
            self.message = message
            self.code = code
            self.details = details or {}

    def api_error_adapter(error, request):
        """Serialize API errors consistently."""
        return {
            'error': {
                'message': error.message,
                'code': error.code,
                'details': error.details,
                'timestamp': datetime.utcnow().isoformat()
            }
        }

    def error_view(request):
        """Handle API errors."""
        try:
            # Your business logic
            result = do_something()
            return {'data': result}
        except ValidationError as e:
            raise APIError(
                message="Validation failed",
                code="VALIDATION_ERROR",
                details={'field_errors': e.errors}
            )
        except PermissionError:
            raise APIError(
                message="Permission denied",
                code="PERMISSION_DENIED"
            )

Performance Optimization
=======================

Optimize JSON serialization for performance.

Lazy Loading with JSON
----------------------

.. code-block:: python

    from sqlalchemy.orm import load_only

    @view_config(route_name='users_api', renderer='json')
    def users_api_light(request):
        """Optimized user listing - only load needed fields."""
        session = request.dbsession
        
        # Only load fields we'll serialize
        users = session.query(User).options(
            load_only(User.id, User.username, User.email, User.created_at)
        ).all()
        
        return {'users': users}

Caching JSON Responses
---------------------

.. code-block:: python

    from functools import lru_cache
    from pyramid.response import Response
    import json

    @lru_cache(maxsize=100)
    def get_cached_stats():
        """Cache expensive statistics calculation."""
        # Expensive computation
        return calculate_complex_stats()

    @view_config(route_name='stats_api')
    def stats_api(request):
        """Cached JSON response."""
        stats = get_cached_stats()
        
        # Manual JSON response with caching headers
        response = Response(
            body=json.dumps(stats),
            content_type='application/json'
        )
        response.cache_control.max_age = 300  # 5 minutes
        return response

JSON Schema Validation
=====================

Validate JSON input using schemas.

Input Validation
---------------

.. code-block:: python

    import jsonschema
    from pyramid.httpexceptions import HTTPBadRequest

    USER_CREATE_SCHEMA = {
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "minLength": 3,
                "maxLength": 50,
                "pattern": "^[a-zA-Z0-9_]+$"
            },
            "email": {
                "type": "string",
                "format": "email"
            },
            "age": {
                "type": "integer",
                "minimum": 13,
                "maximum": 120
            }
        },
        "required": ["username", "email"],
        "additionalProperties": False
    }

    def validate_json_input(data, schema):
        """Validate JSON data against schema."""
        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            raise HTTPBadRequest(json_body={
                'error': 'Validation failed',
                'details': e.message,
                'path': list(e.absolute_path)
            })

    @view_config(route_name='create_user', request_method='POST', renderer='json')
    def create_user(request):
        # Validate input
        validate_json_input(request.json_body, USER_CREATE_SCHEMA)
        
        # Create user with validated data
        user_data = request.json_body
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            age=user_data.get('age')
        )
        
        return {'user': user}

Testing JSON APIs
================

Test your JSON endpoints thoroughly.

Basic JSON Testing
-----------------

.. code-block:: python

    def test_user_api(app):
        # Test successful response
        response = app.get('/api/users/1')
        assert response.status_code == 200
        assert response.content_type == 'application/json'
        
        data = response.json
        assert 'id' in data
        assert 'username' in data
        assert 'password_hash' not in data  # Sensitive data excluded

    def test_json_input_validation(app):
        # Test invalid JSON input
        invalid_data = {'username': 'x'}  # Too short
        
        response = app.post_json('/api/users', invalid_data, expect_errors=True)
        assert response.status_code == 400
        
        error_data = response.json
        assert 'error' in error_data

Custom JSON Assertions
---------------------

.. code-block:: python

    def assert_json_structure(data, expected_keys):
        """Assert JSON has expected structure."""
        assert isinstance(data, dict)
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

    def assert_iso_datetime(datetime_string):
        """Assert string is valid ISO datetime."""
        from datetime import datetime
        try:
            datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        except ValueError:
            raise AssertionError(f"Invalid ISO datetime: {datetime_string}")

    def test_user_json_structure(app):
        response = app.get('/api/users/1')
        user_data = response.json
        
        assert_json_structure(user_data, ['id', 'username', 'email', 'created_at'])
        assert_iso_datetime(user_data['created_at'])

Best Practices
=============

**Security First**
- Always use ``js_safe_dumps`` when embedding JSON in HTML
- Never include sensitive data in JSON responses
- Validate all JSON input with schemas

**Performance**
- Use lazy loading for database queries
- Cache expensive JSON responses
- Only load and serialize needed fields

**Consistency**
- Use adapters for consistent object serialization
- Standardize error response formats
- Use ISO format for dates and times

**Testing**
- Test JSON structure and content
- Test both success and error responses
- Validate security aspects (no sensitive data leakage)

**Documentation**
- Document JSON API schemas
- Provide example requests and responses
- Document custom adapters and their behavior