=====================
SQLAlchemy Integration
=====================

Tet provides enhanced SQLAlchemy integration with custom root factories, session management patterns, and proper exception handling.

Root Factories
==============

Tet's ``SQLARootFactory`` provides a secure and robust foundation for traversal-based applications.

Basic Root Factory
------------------

The ``SQLARootFactory`` is an abstract base class that handles SQL exceptions properly:

.. code-block:: python

    from tet.sqlalchemy.factory import SQLARootFactory
    from sqlalchemy.orm.exc import NoResultFound

    class MyRootFactory(SQLARootFactory):
        def supplier(self, item):
            """Override this method to provide object lookup logic."""
            session = self.request.dbsession
            try:
                return session.query(MyModel).filter_by(id=item).one()
            except NoResultFound:
                # This will be converted to KeyError, resulting in 404
                raise

Using the Root Factory
----------------------

Register your root factory with Pyramid:

.. code-block:: python

    from pyramid.config import Configurator

    def main():
        with Configurator() as config:
            config.set_root_factory(MyRootFactory)

            # Your routes using traversal
            config.add_route('item', '/items/{id}')

            return config.make_wsgi_app()

Exception Handling
-----------------

The ``SQLARootFactory`` automatically converts these exceptions to ``KeyError``:

* ``NoResultFound``: When a query returns no results
* ``MultipleResultsFound``: When a unique query finds multiple results
* ``DataError``: When there are data-related SQL errors (e.g., invalid UUID)

This conversion results in proper HTTP 404 responses instead of exposing SQL errors to users.

Advanced Root Factory Example
-----------------------------

A more sophisticated root factory with caching and multiple model types:

.. code-block:: python

    from tet.sqlalchemy.factory import SQLARootFactory
    from sqlalchemy.orm.exc import NoResultFound
    import re

    class ApplicationRoot(SQLARootFactory):
        def supplier(self, item):
            session = self.request.dbsession

            # Handle different ID patterns
            if re.match(r'^\d+$', item):
                # Numeric ID - look up by primary key
                try:
                    return session.query(MyModel).get(int(item))
                except (ValueError, NoResultFound):
                    raise

            elif re.match(r'^[a-f0-9-]{36}$', item):
                # UUID pattern - look up by UUID
                try:
                    return session.query(MyModel).filter_by(uuid=item).one()
                except NoResultFound:
                    raise

            else:
                # Try slug lookup
                try:
                    return session.query(MyModel).filter_by(slug=item).one()
                except NoResultFound:
                    raise

Session Management
==================

Tet provides automatic session management through its SQLAlchemy integration.

Tet's SQLAlchemy Simple Integration
----------------------------------

Use Tet's simple SQLAlchemy setup for automatic configuration:

.. code-block:: python

    from tet.config import application_factory, ALL_FEATURES
    from tet.sqlalchemy.simple import declarative_base

    # Create models using Tet's declarative base
    Base = declarative_base()

    @application_factory(included_features=ALL_FEATURES)
    def main(config):
        # Include Tet's SQLAlchemy integration
        config.include('tet.sqlalchemy.simple')

        # This automatically configures:
        # - pyramid_di for dependency injection
        # - pyramid_tm for transaction management
        # - Request-scoped database sessions
        config.setup_sqlalchemy()

Using Sessions in Views
-----------------------

Access the database session via pyramid_di autowired dependency injection:

.. code-block:: python

    from pyramid_di import autowired
    from sqlalchemy.orm import Session

    class ItemViews:
        """Views with autowired database session."""

        # Database session automatically injected via pyramid_di
        session: Session = autowired()

        @view_config(route_name='items', renderer='json')
        def list_items(self, request):
            # Use the autowired session - automatically managed
            items = self.session.query(MyModel).all()
            return {'items': items}

Automatic Features
-----------------

When using ``config.setup_sqlalchemy()``, you get all of this automatically:

**Dependency Injection (pyramid_di)**
  - Sessions are registered as services
  - Available via ``autowired`` class attributes
  - Request-scoped lifecycle management

**Transaction Management (pyramid_tm)**
  - Transactions start automatically per request
  - Committed on successful responses (2xx, 3xx)
  - Rolled back on exceptions or error responses (4xx, 5xx)
  - No manual commit/rollback needed

**Session Lifecycle**
  - Sessions created per request
  - Automatically closed after request completion
  - Proper cleanup and connection management

Model Integration
================

Tet's JSON renderer automatically handles SQLAlchemy model objects.

Model Serialization
-------------------

SQLAlchemy models can be made JSON-serializable:

.. code-block:: python

    from sqlalchemy import Column, Integer, String, DateTime
    from sqlalchemy.ext.declarative import declarative_base

    Base = declarative_base()

    class User(Base):
        __tablename__ = 'users'

        id = Column(Integer, primary_key=True)
        name = Column(String(50))
        email = Column(String(100))
        created = Column(DateTime)

        def __json__(self, request):
            """Custom JSON serialization method."""
            return {
                'id': self.id,
                'name': self.name,
                'email': self.email,
                'created': self.created  # Automatically converted by Tet
            }

Alternatively, use the JSON adapter system:

.. code-block:: python

    def user_adapter(user, request):
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'created': user.created
        }

    def main():
        with Configurator() as config:
            config.include('tet.renderers.json')
            config.add_json_adapter(for_=User, adapter=user_adapter)

            return config.make_wsgi_app()

Query Result Handling
---------------------

Tet automatically handles SQLAlchemy query results:

.. code-block:: python

    @view_config(route_name='user_summary', renderer='json')
    def user_summary(request):
        session = request.find_service(name='dbsession')

        # Named tuple results are automatically serializable
        results = session.query(User.name, User.email).all()

        return {'users': results}  # Automatically converted to list of dicts

Database Configuration
=====================

Setting Up SQLAlchemy with Tet
------------------------------

A complete database configuration example:

.. code-block:: python

    from pyramid.config import Configurator
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from pyramid_di import service

    # Database configuration
    def get_engine(settings):
        return create_engine(settings['sqlalchemy.url'])

    def get_session_factory(engine):
        return sessionmaker(bind=engine)

    @service(name='dbsession', scope='request')
    def get_db_session(request):
        session_factory = request.registry['db_session_factory']
        session = session_factory()

        def cleanup(request):
            session.close()

        request.add_finished_callback(cleanup)
        return session

    def main(global_config, **settings):
        config = Configurator(settings=settings)

        # Database setup
        engine = get_engine(settings)
        session_factory = get_session_factory(engine)
        config.registry['db_session_factory'] = session_factory

        # Include Tet features
        config.include('pyramid_di')
        config.include('tet.renderers.json')

        return config.make_wsgi_app()

Connection Pooling
-----------------

Configure SQLAlchemy connection pooling:

.. code-block:: python

    from sqlalchemy import create_engine

    def get_engine(settings):
        return create_engine(
            settings['sqlalchemy.url'],
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600
        )

Testing with Databases
=====================

Testing Patterns
----------------

Use pytest fixtures for database testing:

.. code-block:: python

    import pytest
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from myapp.models import Base

    @pytest.fixture(scope='session')
    def engine():
        return create_engine('sqlite:///:memory:')

    @pytest.fixture(scope='session')
    def tables(engine):
        Base.metadata.create_all(engine)
        yield
        Base.metadata.drop_all(engine)

    @pytest.fixture
    def dbsession(engine, tables):
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.rollback()
        session.close()

Testing Root Factories
----------------------

Test your root factories with proper mocking:

.. code-block:: python

    import pytest
    from unittest.mock import Mock
    from myapp.models import MyModel
    from myapp.root import MyRootFactory

    def test_root_factory_success(dbsession):
        # Create test data
        obj = MyModel(name='test')
        dbsession.add(obj)
        dbsession.commit()

        # Mock request
        request = Mock()
        request.dbsession = dbsession

        # Test root factory
        root = MyRootFactory(request)
        result = root[str(obj.id)]

        assert result == obj

    def test_root_factory_not_found(dbsession):
        request = Mock()
        request.dbsession = dbsession

        root = MyRootFactory(request)

        with pytest.raises(KeyError):
            root['nonexistent']

Best Practices
=============

**Use Request-Scoped Sessions**
  Always use request-scoped database sessions to avoid connection leaks.

**Handle Exceptions Properly**
  Use Tet's root factories to convert SQL exceptions to appropriate HTTP responses.

**Implement Custom Serialization**
  Use ``__json__`` methods or JSON adapters for model serialization.

**Use Transactions**
  Include ``pyramid_tm`` for automatic transaction management.

**Test Database Code**
  Use proper testing patterns with database fixtures and rollbacks.

**Configure Connection Pooling**
  Set appropriate connection pool settings for production.

**Monitor Performance**
  Use SQLAlchemy's logging to monitor and optimize database queries.

Security Considerations
======================

**Parameterized Queries**
  SQLAlchemy ORM automatically uses parameterized queries to prevent SQL injection.

**Input Validation**
  Always validate input data before using it in database queries.

**Sensitive Data**
  Be careful about what model attributes are included in JSON serialization.

**Database Permissions**
  Use appropriate database user permissions in production.

**Connection Security**
  Use SSL/TLS for database connections in production environments.
