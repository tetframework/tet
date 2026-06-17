==========
Quickstart
==========

This tutorial will guide you through creating your first Tet application from scratch.

Installation
============

First, install Tet using pip::

    pip install tet

You'll also want to install Pyramid and other common dependencies::

    pip install pyramid pyramid_di sqlalchemy

Creating Your First Application
===============================

Let's create a simple web application using Tet's enhanced features.

Basic Application Structure
---------------------------

Create a new directory for your project and add the following files:

**app.py**

.. code-block:: python

    from tet.config import application_factory, ALL_FEATURES
    from pyramid.response import Response

    def hello_world(request):
        return Response('Hello, Tet!')

    def json_api(request):
        return {
            'message': 'Hello from Tet API!',
            'features': ['CSRF Protection', 'Safe JSON', 'Enhanced Auth']
        }

    @application_factory(included_features=ALL_FEATURES)
    def main(config):
        """Tet application factory."""
        # Add routes
        config.add_route('home', '/')
        config.add_route('api', '/api')

        # Add views
        config.add_view(hello_world, route_name='home')
        config.add_view(json_api, route_name='api', renderer='json')

    if __name__ == '__main__':
        from wsgiref.simple_server import make_server
        app = main({})  # Empty global_config
        server = make_server('0.0.0.0', 6543, app)
        print("Server running on http://localhost:6543")
        server.serve_forever()

Run your application::

    python app.py

Visit http://localhost:6543 to see your application running!

Adding Database Support
=======================

Let's enhance our application with database support using SQLAlchemy.

**models.py**

.. code-block:: python

    from sqlalchemy import Column, Integer, String, DateTime, create_engine
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from datetime import datetime

    Base = declarative_base()

    class User(Base):
        __tablename__ = 'users'

        id = Column(Integer, primary_key=True)
        name = Column(String(50), nullable=False)
        email = Column(String(100), unique=True, nullable=False)
        created = Column(DateTime, default=datetime.utcnow)

        def __json__(self, request):
            """JSON serialization for Tet's JSON renderer."""
            return {
                'id': self.id,
                'name': self.name,
                'email': self.email,
                'created': self.created  # Automatically converted by Tet
            }

    # Database setup
    engine = create_engine('sqlite:///tutorial.db', echo=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

**Enhanced app.py**

.. code-block:: python

    from tet.config import application_factory, ALL_FEATURES
    from pyramid.response import Response
    from pyramid_di import autowired
    from sqlalchemy.orm import Session
    from models import User

    def hello_world(request):
        return Response('Hello, Tet!')

    class UserViews:
        """User management views."""

        # Database session automatically injected via pyramid_di
        dbsession: Session = autowired()

        def create_user(self, request):
            # Use the autowired database session
            # Transaction managed automatically by pyramid_tm

            # Create a new user
            user = User(
                name='John Doe',
                email='john@example.com'
            )
            self.dbsession.add(user)
            # No need to commit - pyramid_tm handles transactions automatically

            return {'message': 'User created', 'user': user}

        def list_users(self, request):
            # Use the autowired database session
            users = self.dbsession.query(User).all()
            return {'users': users}

    @application_factory(included_features=ALL_FEATURES)
    def main(config):
        """Tet application factory with database support."""
        # Setup SQLAlchemy with automatic session management
        config.include('tet.sqlalchemy.simple')
        config.setup_sqlalchemy()

        # Routes
        config.add_route('home', '/')
        config.add_route('create_user', '/users/create')
        config.add_route('list_users', '/users')

        # Views
        config.add_view(hello_world, route_name='home')

        # Register class-based views
        user_views = UserViews()
        config.add_view(user_views.create_user, route_name='create_user',
                      request_method='POST', renderer='json')
        config.add_view(user_views.list_users, route_name='list_users', renderer='json')

    if __name__ == '__main__':
        from wsgiref.simple_server import make_server
        app = main({})
        server = make_server('0.0.0.0', 6543, app)
        print("Server running on http://localhost:6543")
        server.serve_forever()

Adding Security Features
========================

Let's add some security features to our application.

**Enhanced Views with CSRF Protection**

.. code-block:: python

    from pyramid.httpexceptions import HTTPForbidden
    from pyramid.csrf import check_csrf_token

    def secure_create_user(request):
        # CSRF protection is automatically enabled
        # This view will require CSRF token for POST requests

        try:
            # Validate CSRF token (optional explicit check)
            check_csrf_token(request)
        except HTTPForbidden:
            return {'error': 'CSRF token missing or invalid'}

        session = request.find_service(name='dbsession')

        # Get data from request
        name = request.json_body.get('name')
        email = request.json_body.get('email')

        if not name or not email:
            return {'error': 'Name and email are required'}

        # Create user
        user = User(name=name, email=email)
        session.add(user)
        session.commit()

        return {'message': 'User created successfully', 'user': user}

**Safe JSON for Frontend**

Create a template that safely embeds JSON:

**templates/users.pt** (Chameleon template)

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>
        <title>Users</title>
        <meta name="csrf-token" content="${request.session.get_csrf_token()}">
    </head>
    <body>
        <h1>Users</h1>
        <div id="users"></div>

        <script>
            // Safe JSON embedding using Tet's js_safe_dumps
            var users = ${users_json|n};

            // Display users
            var container = document.getElementById('users');
            users.forEach(function(user) {
                var div = document.createElement('div');
                div.textContent = user.name + ' (' + user.email + ')';
                container.appendChild(div);
            });
        </script>
    </body>
    </html>

**Updated view**

.. code-block:: python

    from tet.util.json import js_safe_dumps

    def users_page(request):
        session = request.find_service(name='dbsession')
        users = session.query(User).all()

        # Convert users to JSON-serializable format
        users_data = [user.__json__(request) for user in users]

        # Safe JSON for template embedding
        users_json = js_safe_dumps(users_data)

        return {'users_json': users_json}

Adding Testing
==============

Let's add some tests for our application.

**test_app.py**

.. code-block:: python

    import pytest
    from pyramid.testing import DummyRequest
    from models import User, Session, Base, engine

    @pytest.fixture
    def dbsession():
        """Create test database session."""
        # Create all tables
        Base.metadata.create_all(engine)
        session = Session()
        yield session
        session.rollback()
        session.close()
        Base.metadata.drop_all(engine)

    def test_create_user(dbsession):
        from app import create_user

        # Mock request with database session
        request = DummyRequest()
        request.find_service = lambda name: dbsession
        request.json_body = {
            'name': 'Test User',
            'email': 'test@example.com'
        }

        # Test the view
        result = create_user(request)

        assert result['message'] == 'User created'
        assert result['user'].name == 'Test User'

    def test_list_users(dbsession):
        from app import list_users

        # Create test data
        user1 = User(name='User 1', email='user1@example.com')
        user2 = User(name='User 2', email='user2@example.com')
        dbsession.add_all([user1, user2])
        dbsession.commit()

        # Mock request
        request = DummyRequest()
        request.find_service = lambda name: dbsession

        # Test the view
        result = list_users(request)

        assert len(result['users']) == 2

Run the tests::

    pytest test_app.py

Production Configuration
========================

For production deployment, create a proper configuration file.

**production.ini**

.. code-block:: ini

    [app:main]
    use = egg:myapp

    # Database configuration
    sqlalchemy.url = postgresql://user:pass@localhost/myapp

    # Session configuration
    session.secret = your-very-secure-secret-key-here
    session.secure = true
    session.httponly = true
    session.samesite = Strict

    # Security settings
    csrf.secret = another-secure-secret-for-csrf

    # Logging
    [loggers]
    keys = root, myapp

    [handlers]
    keys = console

    [formatters]
    keys = generic

    [logger_root]
    level = WARN
    handlers = console

    [logger_myapp]
    level = WARN
    handlers =
    qualname = myapp

    [handler_console]
    class = StreamHandler
    args = (sys.stderr,)
    level = NOTSET
    formatter = generic

    [formatter_generic]
    format = %(asctime)s %(levelname)-5.5s [%(name)s:%(lineno)s][%(funcName)s()] %(message)s

**wsgi.py** for production deployment

.. code-block:: python

    from pyramid.paster import get_app, setup_logging
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(here, 'production.ini')

    setup_logging(config_file)
    application = get_app(config_file, 'main')

Deploy with gunicorn::

    pip install gunicorn
    gunicorn --bind 0.0.0.0:8000 wsgi:application

Next Steps
==========

Congratulations! You've created a complete Tet application with:

- Enhanced JSON rendering with automatic type conversion
- CSRF protection for security
- Database integration with SQLAlchemy
- Request-scoped services with pyramid_di
- Safe JSON embedding for frontend integration
- Basic testing setup

**What's Next?**

1. **Explore Security Features**: Learn more about Tet's authorization system
2. **Advanced JSON Handling**: Create custom JSON adapters for your types
3. **Database Patterns**: Use Tet's root factories for traversal-based applications
4. **Utility Modules**: Explore Tet's cryptography, path, and other utilities
5. **Testing**: Add comprehensive tests using Tet's testing patterns

Check out the other tutorials and narrative documentation for more advanced topics!
