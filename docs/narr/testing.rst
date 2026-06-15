=======
Testing
=======

Tet applications can be thoroughly tested using pytest and various testing utilities. This chapter covers testing patterns, fixtures, and best practices for Tet applications.

Testing Framework
================

Tet applications use pytest as the primary testing framework with additional utilities for web application testing.

Basic Test Setup
---------------

.. code-block:: python

    # conftest.py
    import pytest
    from pyramid.config import Configurator
    from pyramid.testing import setUp, tearDown

    @pytest.fixture(scope='function')
    def config():
        """Pyramid configurator for testing."""
        config = setUp()
        config.include('tet.renderers.json')
        yield config
        tearDown()

    @pytest.fixture(scope='function')
    def request(config):
        """Mock request object for testing."""
        from pyramid.testing import DummyRequest
        request = DummyRequest()
        request.registry = config.registry
        return request

Testing Views
=============

Testing Pyramid views with Tet enhancements.

Basic View Testing
-----------------

.. code-block:: python

    # test_views.py
    import pytest
    from pyramid.testing import DummyRequest
    from myapp.views import home_view

    def test_home_view():
        request = DummyRequest()
        response = home_view(request)
        
        assert response['message'] == 'Hello, World!'

JSON View Testing
----------------

Test views that use Tet's JSON renderer:

.. code-block:: python

    def test_api_view(config, request):
        from myapp.views import api_view
        
        # Configure JSON renderer
        config.include('tet.renderers.json')
        
        # Test the view
        result = api_view(request)
        
        assert 'data' in result
        assert isinstance(result['data'], list)

Integration Testing
==================

Testing complete request/response cycles.

WebTest Integration
------------------

.. code-block:: python

    # conftest.py
    import pytest
    from webtest import TestApp
    from myapp import main

    @pytest.fixture(scope='session')
    def app():
        """Create test application."""
        settings = {
            'sqlalchemy.url': 'sqlite:///:memory:',
            'debug': True,
        }
        app = main({}, **settings)
        return TestApp(app)

    # test_integration.py
    def test_home_page(app):
        response = app.get('/')
        assert response.status_code == 200
        assert b'Hello' in response.body

    def test_api_endpoint(app):
        response = app.get('/api/users')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

Database Testing
===============

Testing with SQLAlchemy and database operations.

Database Fixtures
----------------

.. code-block:: python

    # conftest.py
    import pytest
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from myapp.models import Base

    @pytest.fixture(scope='session')
    def engine():
        """Create test database engine."""
        return create_engine('sqlite:///:memory:', echo=False)

    @pytest.fixture(scope='session')
    def tables(engine):
        """Create all tables."""
        Base.metadata.create_all(engine)
        yield
        Base.metadata.drop_all(engine)

    @pytest.fixture(scope='function')
    def dbsession(engine, tables):
        """Create database session for each test."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

Testing Root Factories
----------------------

Test Tet's SQLAlchemy root factories:

.. code-block:: python

    def test_root_factory_success(dbsession):
        from myapp.models import User
        from myapp.root import UserRootFactory
        from pyramid.testing import DummyRequest
        
        # Create test data
        user = User(name='Test User', email='test@example.com')
        dbsession.add(user)
        dbsession.commit()
        
        # Test root factory
        request = DummyRequest()
        request.dbsession = dbsession
        
        root = UserRootFactory(request)
        found_user = root[str(user.id)]
        
        assert found_user == user

    def test_root_factory_not_found(dbsession):
        from myapp.root import UserRootFactory
        from pyramid.testing import DummyRequest
        
        request = DummyRequest()
        request.dbsession = dbsession
        
        root = UserRootFactory(request)
        
        with pytest.raises(KeyError):
            root['nonexistent']

Security Testing
===============

Testing Tet's security features.

CSRF Testing
-----------

.. code-block:: python

    def test_csrf_protection(app):
        # GET request should work
        response = app.get('/form')
        assert response.status_code == 200
        
        # POST without CSRF token should fail
        with pytest.raises(Exception):  # CSRF error
            app.post('/form', {'data': 'test'})
        
        # POST with CSRF token should work
        # (Implementation depends on your CSRF setup)

Authorization Testing
--------------------

.. code-block:: python

    def test_authorization_policy():
        from myapp.security import MyAuthorizationPolicy
        from pyramid.testing import DummyRequest
        
        policy = MyAuthorizationPolicy()
        request = DummyRequest()
        
        # Test permission checking
        result = policy.permits(
            request=request,
            context=None,
            principals=['user:123'],
            permission='edit'
        )
        
        assert result is True  # or False, depending on logic

JSON Testing
===========

Testing Tet's JSON functionality.

JSON Serialization Testing
--------------------------

.. code-block:: python

    def test_json_serialization(config):
        from tet.renderers.json import construct_default_renderer
        from datetime import datetime
        
        renderer = construct_default_renderer()
        
        data = {
            'timestamp': datetime.now(),
            'count': 42
        }
        
        result = renderer(data, {})
        
        # Should be valid JSON
        import json
        parsed = json.loads(result)
        assert 'timestamp' in parsed
        assert parsed['count'] == 42

Safe JSON Testing
----------------

.. code-block:: python

    def test_safe_json_serialization():
        from tet.util.json import js_safe_dumps
        
        dangerous_data = {
            'script': '</script><script>alert("XSS")</script>'
        }
        
        safe_json = js_safe_dumps(dangerous_data)
        
        # Should escape dangerous characters
        assert '<' not in safe_json
        assert '\\u003c' in safe_json

Mock Testing
===========

Using mocks for isolated testing.

Service Mocking
--------------

.. code-block:: python

    from unittest.mock import Mock, patch

    def test_view_with_service():
        from myapp.views import user_list_view
        from pyramid.testing import DummyRequest
        
        # Mock the database service
        mock_session = Mock()
        mock_session.query.return_value.all.return_value = [
            Mock(id=1, name='User 1'),
            Mock(id=2, name='User 2'),
        ]
        
        request = DummyRequest()
        request.find_service = Mock(return_value=mock_session)
        
        result = user_list_view(request)
        
        assert len(result['users']) == 2

External Service Mocking
-----------------------

.. code-block:: python

    @patch('myapp.services.external_api_call')
    def test_external_service(mock_api_call):
        mock_api_call.return_value = {'status': 'success'}
        
        from myapp.services import process_external_data
        
        result = process_external_data('test_data')
        
        assert result['status'] == 'success'
        mock_api_call.assert_called_once_with('test_data')

Fixture Patterns
================

Common fixture patterns for Tet applications.

User Authentication Fixtures
----------------------------

.. code-block:: python

    @pytest.fixture
    def authenticated_user(dbsession):
        """Create an authenticated user for testing."""
        from myapp.models import User
        
        user = User(
            username='testuser',
            email='test@example.com',
            is_active=True
        )
        dbsession.add(user)
        dbsession.commit()
        return user

    @pytest.fixture
    def authenticated_request(request, authenticated_user):
        """Create request with authenticated user."""
        request.user = authenticated_user
        return request

Application State Fixtures
--------------------------

.. code-block:: python

    @pytest.fixture
    def sample_data(dbsession):
        """Create sample data for testing."""
        from myapp.models import User, Post
        
        users = [
            User(username=f'user{i}', email=f'user{i}@example.com')
            for i in range(3)
        ]
        
        for user in users:
            dbsession.add(user)
        
        dbsession.commit()
        
        posts = [
            Post(title=f'Post {i}', content=f'Content {i}', author=users[0])
            for i in range(5)
        ]
        
        for post in posts:
            dbsession.add(post)
        
        dbsession.commit()
        
        return {'users': users, 'posts': posts}

Performance Testing
==================

Testing performance characteristics of your application.

Response Time Testing
--------------------

.. code-block:: python

    import time

    def test_api_response_time(app):
        start_time = time.time()
        response = app.get('/api/users')
        end_time = time.time()
        
        assert response.status_code == 200
        assert end_time - start_time < 1.0  # Should respond within 1 second

Load Testing with Locust
------------------------

.. code-block:: python

    # locustfile.py
    from locust import HttpUser, task, between

    class WebsiteUser(HttpUser):
        wait_time = between(1, 3)
        
        @task
        def index_page(self):
            self.client.get("/")
        
        @task(3)
        def api_users(self):
            self.client.get("/api/users")

Test Organization
================

Organizing tests for maintainability.

Directory Structure
------------------

.. code-block::

    tests/
    ├── conftest.py           # Shared fixtures
    ├── unit/                 # Unit tests
    │   ├── test_models.py
    │   ├── test_views.py
    │   └── test_utilities.py
    ├── integration/          # Integration tests
    │   ├── test_api.py
    │   └── test_web.py
    ├── functional/           # Functional tests
    │   └── test_workflows.py
    └── performance/          # Performance tests
        └── test_load.py

Test Categories
--------------

**Unit Tests**
  Test individual functions and classes in isolation.

**Integration Tests**
  Test how components work together.

**Functional Tests**
  Test complete user workflows.

**Performance Tests**
  Test response times and resource usage.

Continuous Integration
=====================

Running tests in CI environments.

pytest Configuration
-------------------

.. code-block:: ini

    # pytest.ini
    [tool:pytest]
    testpaths = tests
    python_files = test_*.py
    python_classes = Test*
    python_functions = test_*
    addopts = 
        --strict-markers
        --disable-warnings
        --cov=myapp
        --cov-report=html
        --cov-report=term-missing

GitHub Actions Example
---------------------

.. code-block:: yaml

    # .github/workflows/test.yml
    name: Tests
    
    on: [push, pull_request]
    
    jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: [3.8, 3.9, '3.10', 3.11]
        
        steps:
        - uses: actions/checkout@v4
        - name: Set up Python ${{ matrix.python-version }}
          uses: actions/setup-python@v4
          with:
            python-version: ${{ matrix.python-version }}
        
        - name: Install dependencies
          run: |
            python -m pip install --upgrade pip
            pip install -e .[dev]
        
        - name: Run tests
          run: pytest

Best Practices
=============

**Use Fixtures Liberally**
  Create reusable fixtures for common test data and setup.

**Test Edge Cases**
  Test not just the happy path, but error conditions and edge cases.

**Mock External Dependencies**
  Mock external APIs and services to make tests reliable and fast.

**Use Meaningful Test Names**
  Test function names should clearly describe what is being tested.

**Keep Tests Independent**
  Each test should be able to run independently of others.

**Test Database Interactions**
  Use transactions and rollbacks to keep database tests isolated.

**Use Parametrized Tests**
  Use pytest's parametrize decorator to test multiple inputs efficiently.

**Measure Coverage**
  Use coverage tools to ensure adequate test coverage.

**Test Security Features**
  Specifically test security-related functionality like CSRF and authorization.

**Performance Benchmarks**
  Include basic performance tests to catch regressions early.