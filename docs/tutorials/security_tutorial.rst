=================
Security Tutorial
=================

This tutorial covers implementing security features in Tet applications, including CSRF protection, authorization policies, and safe data handling.

CSRF Protection Setup
=====================

Cross-Site Request Forgery (CSRF) protection is essential for web applications. Tet makes it easy to implement.

Basic CSRF Protection
---------------------

Enable CSRF protection in your application:

.. code-block:: python

    from pyramid.config import Configurator


    def main():
        with Configurator() as config:
            # Enable CSRF protection
            config.include("tet.security.csrf")

            # CSRF is now required for all state-changing requests
            return config.make_wsgi_app()

This automatically sets ``require_csrf=True`` for all views that modify state.

Working with CSRF Tokens
------------------------

**In HTML Forms**

.. code-block:: html

    <form method="post" action="/submit">
        <input type="hidden" name="csrf_token"
               value="${request.session.get_csrf_token()}">
        <input type="text" name="data" placeholder="Enter data">
        <input type="submit" value="Submit">
    </form>

**In AJAX Requests**

.. code-block:: javascript

    // Set CSRF token in meta tag (in your template)
    // <meta name="csrf-token" content="${request.session.get_csrf_token()}">

    function setupCSRF() {
        var token = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

        // jQuery setup
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                    xhr.setRequestHeader("X-CSRF-Token", token);
                }
            }
        });

        // Or with fetch API
        fetch('/api/data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': token
            },
            body: JSON.stringify(data)
        });
    }

**Manual CSRF Validation**

.. code-block:: python

    from pyramid.csrf import check_csrf_token
    from pyramid.httpexceptions import HTTPForbidden


    def secure_view(request):
        try:
            check_csrf_token(request)
        except HTTPForbidden:
            return {"error": "CSRF token missing or invalid"}

        # Process the request
        return {"status": "success"}

Authorization System
====================

Tet provides an enhanced authorization system that gives policies access to the request object.

Creating an Authorization Policy
--------------------------------

.. code-block:: python

    from tet.security.authorization import INewAuthorizationPolicy
    from zope.interface import implementer


    @implementer(INewAuthorizationPolicy)
    class MyAuthorizationPolicy:
        def permits(self, request, context, principals, permission):
            """Check if any principal has the given permission."""

            # Access request data for authorization decisions
            if permission == "admin":
                return "group:admin" in principals

            if permission == "edit":
                # Context-specific authorization
                if hasattr(context, "owner_id"):
                    user_id = request.authenticated_userid
                    return context.owner_id == user_id or "group:admin" in principals

            if permission == "view":
                # Public content
                if hasattr(context, "is_public") and context.is_public:
                    return True
                # Private content requires authentication
                return request.authenticated_userid is not None

            return False

        def principals_allowed_by_permission(self, request, context, permission):
            """Return principals allowed for a permission."""
            allowed = set()

            if permission == "admin":
                allowed.add("group:admin")
            elif permission == "edit":
                if hasattr(context, "owner_id"):
                    allowed.add(f"user:{context.owner_id}")
                allowed.add("group:admin")
            elif permission == "view":
                if hasattr(context, "is_public") and context.is_public:
                    allowed.add("system.Everyone")
                else:
                    allowed.add("system.Authenticated")

            return allowed

Registering the Authorization Policy
------------------------------------

.. code-block:: python

    def main():
        with Configurator() as config:
            # Include Tet's enhanced authorization
            config.include("tet.security.authorization")

            # Register your policy
            config.set_authorization_policy(MyAuthorizationPolicy())

            # Also set up authentication
            # (using your preferred authentication policy)

            return config.make_wsgi_app()

Using Authorization in Views
----------------------------

.. code-block:: python

    from pyramid.view import view_config
    from pyramid.httpexceptions import HTTPForbidden
    from pyramid.security import has_permission


    @view_config(route_name="edit_post", renderer="json", permission="edit")
    def edit_post(request):
        """This view requires 'edit' permission."""
        post_id = request.matchdict["id"]
        post = get_post(post_id)

        # Permission is already checked by the view decorator
        # Update the post
        post.title = request.json_body.get("title", post.title)

        return {"status": "updated", "post": post}


    @view_config(route_name="view_post", renderer="json")
    def view_post(request):
        """Manual permission checking."""
        post_id = request.matchdict["id"]
        post = get_post(post_id)

        # Check permission manually
        if not has_permission("view", post, request):
            raise HTTPForbidden("You don't have permission to view this post")

        return {"post": post}

Authentication Integration
==========================

Combine Tet's authorization with authentication systems.

Using pyramid_jwt
-----------------

.. code-block:: python

    from pyramid_jwt import create_jwt_authentication_policy


    def main():
        with Configurator() as config:
            # JWT Authentication
            config.include("pyramid_jwt")
            config.set_jwt_authentication_policy(
                "secret_key", auth_type="Bearer", callback=get_user_from_jwt
            )

            # Tet Authorization
            config.include("tet.security.authorization")
            config.set_authorization_policy(MyAuthorizationPolicy())

            return config.make_wsgi_app()


    def get_user_from_jwt(userid, request):
        """Get user principals from JWT payload."""
        # Your user lookup logic
        user = get_user(userid)
        if user and user.is_active:
            principals = [f"user:{user.id}"]
            if user.is_admin:
                principals.append("group:admin")
            return principals
        return None

Creating Protected Resources
----------------------------

.. code-block:: python

    class Post:
        def __init__(self, id, title, content, owner_id, is_public=False):
            self.id = id
            self.title = title
            self.content = content
            self.owner_id = owner_id
            self.is_public = is_public

        def __acl__(self):
            """Access Control List for this resource."""
            return [
                (Allow, f"user:{self.owner_id}", "edit"),
                (Allow, f"user:{self.owner_id}", "delete"),
                (Allow, "group:admin", ALL_PERMISSIONS),
                (Allow, Everyone, "view") if self.is_public else (Deny, Everyone, "view"),
            ]

Safe Data Handling
==================

Tet provides utilities for safely handling user data and preventing common security vulnerabilities.

Safe JSON Serialization
-----------------------

Prevent XSS attacks when embedding JSON in HTML:

.. code-block:: python

    from tet.util.json import js_safe_dumps


    def user_profile_page(request):
        user_data = {
            "name": request.user.name,
            "bio": request.user.bio,  # Could contain HTML
            "preferences": request.user.preferences,
        }

        # Safe for embedding in HTML/JavaScript
        safe_json = js_safe_dumps(user_data)

        return {"user_json": safe_json}

In your template:

.. code-block:: html

    <script>
        // This is safe from XSS attacks
        var userData = ${user_json|n};

        // Use the data safely
        document.getElementById('user-name').textContent = userData.name;
    </script>

Input Validation and Sanitization
---------------------------------

.. code-block:: python

    import re
    from html import escape


    def sanitize_user_input(data):
        """Sanitize user input data."""
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Remove potentially dangerous characters
                value = re.sub(r'[<>"\']', "", value)
                # Escape HTML entities
                value = escape(value)
                # Limit length
                value = value[:1000]

            sanitized[key] = value

        return sanitized


    @view_config(
        route_name="update_profile",
        request_method="POST",
        renderer="json",
        permission="edit",
    )
    def update_profile(request):
        # Sanitize input data
        raw_data = request.json_body
        clean_data = sanitize_user_input(raw_data)

        # Update user profile with clean data
        user = request.user
        user.bio = clean_data.get("bio", user.bio)
        user.website = clean_data.get("website", user.website)

        return {"status": "updated"}

Session Security
================

Configure secure session settings for production.

Session Configuration
---------------------

.. code-block:: python

    def main(global_config, **settings):
        # Production session settings
        settings.update(
            {
                "session.secret": "your-very-secure-secret-key",
                "session.secure": True,  # HTTPS only
                "session.httponly": True,  # No JavaScript access
                "session.samesite": "Strict",  # CSRF protection
                "session.timeout": 3600,  # 1 hour timeout
                "session.cookie_max_age": 86400,  # 24 hours
            }
        )

        with Configurator(settings=settings) as config:
            config.include("pyramid_session")
            config.include("tet.security.csrf")

            return config.make_wsgi_app()

Rate Limiting
=============

Implement rate limiting for API endpoints.

Simple Rate Limiting
--------------------

.. code-block:: python

    from functools import wraps
    from time import time
    from pyramid.httpexceptions import HTTPTooManyRequests

    # Simple in-memory rate limiter (use Redis in production)
    request_counts = {}


    def rate_limit(max_requests=10, window=60):
        """Rate limiting decorator."""

        def decorator(func):
            @wraps(func)
            def wrapper(request):
                client_ip = request.environ.get("REMOTE_ADDR")
                current_time = time()

                # Clean old entries
                cutoff = current_time - window
                request_counts[client_ip] = [
                    timestamp
                    for timestamp in request_counts.get(client_ip, [])
                    if timestamp > cutoff
                ]

                # Check rate limit
                if len(request_counts[client_ip]) >= max_requests:
                    raise HTTPTooManyRequests("Rate limit exceeded")

                # Record this request
                request_counts[client_ip].append(current_time)

                return func(request)

            return wrapper

        return decorator


    @view_config(route_name="api_endpoint", renderer="json")
    @rate_limit(max_requests=5, window=60)  # 5 requests per minute
    def api_endpoint(request):
        return {"data": "sensitive_information"}

Security Headers
================

Add security headers to your responses.

Security Headers Middleware
---------------------------

.. code-block:: python

    def security_headers_tween_factory(handler, registry):
        """Add security headers to all responses."""

        def security_headers_tween(request):
            response = handler(request)

            # Security headers
            response.headers.update(
                {
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "X-XSS-Protection": "1; mode=block",
                    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                }
            )

            return response

        return security_headers_tween


    def main():
        with Configurator() as config:
            # Add security headers tween
            config.add_tween(
                "myapp.security_headers_tween_factory", under="pyramid_tm.tm_tween_factory"
            )

            return config.make_wsgi_app()

Testing Security Features
=========================

Test your security implementations.

Testing CSRF Protection
-----------------------

.. code-block:: python

    def test_csrf_protection(app):
        # GET request should work
        response = app.get("/form")
        assert response.status_code == 200

        # POST without CSRF token should fail
        response = app.post("/submit", {"data": "test"}, expect_errors=True)
        assert response.status_code == 403

        # POST with CSRF token should work
        # (Extract token from form or session)

Testing Authorization
---------------------

.. code-block:: python

    def test_authorization_policy():
        from myapp.security import MyAuthorizationPolicy
        from pyramid.testing import DummyRequest

        policy = MyAuthorizationPolicy()
        request = DummyRequest()

        # Test admin permission
        assert policy.permits(request, None, ["group:admin"], "admin")
        assert not policy.permits(request, None, ["user:123"], "admin")

        # Test context-specific permission
        context = Mock(owner_id=123, is_public=False)
        assert policy.permits(request, context, ["user:123"], "edit")
        assert not policy.permits(request, context, ["user:456"], "edit")

Security Checklist
==================

Use this checklist to ensure your Tet application is secure:

**Authentication & Authorization**
- [ ] Implement proper authentication system
- [ ] Use Tet's enhanced authorization policies
- [ ] Validate permissions on all protected resources
- [ ] Use strong session configuration

**CSRF Protection**
- [ ] Enable CSRF protection with ``tet.security.csrf``
- [ ] Include CSRF tokens in all forms
- [ ] Configure CSRF headers for AJAX requests
- [ ] Test CSRF protection thoroughly

**Data Security**
- [ ] Use ``js_safe_dumps`` for JSON embedding
- [ ] Sanitize and validate all user inputs
- [ ] Escape HTML output appropriately
- [ ] Use parameterized database queries

**Network Security**
- [ ] Use HTTPS in production
- [ ] Configure security headers
- [ ] Implement rate limiting for APIs
- [ ] Use secure session cookies

**Error Handling**
- [ ] Don't leak sensitive information in error messages
- [ ] Log security events appropriately
- [ ] Use proper HTTP status codes
- [ ] Handle edge cases securely

Remember: Security is an ongoing process, not a one-time setup. Regularly review and update your security measures!
