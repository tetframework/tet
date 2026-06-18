=================
Database Tutorial
=================

This tutorial covers using Tet's enhanced SQLAlchemy integration, including root factories, session management, and database best practices.

Database Setup
==============

Setting up SQLAlchemy with Tet's enhancements.

Basic Configuration
-------------------

Create your database models and configuration:

.. code-block:: python

    # models.py
    from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import relationship
    from datetime import datetime

    Base = declarative_base()


    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)
        username = Column(String(50), unique=True, nullable=False)
        email = Column(String(100), unique=True, nullable=False)
        password_hash = Column(String(128))
        created_at = Column(DateTime, default=datetime.utcnow)
        is_active = Column(Boolean, default=True)

        # Relationships
        posts = relationship("Post", back_populates="author")

        def __json__(self, request):
            """JSON serialization for Tet's renderer."""
            return {
                "id": self.id,
                "username": self.username,
                "email": self.email,
                "created_at": self.created_at,
                "is_active": self.is_active,
            }


    class Post(Base):
        __tablename__ = "posts"

        id = Column(Integer, primary_key=True)
        title = Column(String(200), nullable=False)
        content = Column(Text)
        author_id = Column(Integer, ForeignKey("users.id"))
        created_at = Column(DateTime, default=datetime.utcnow)
        is_published = Column(Boolean, default=False)

        # Relationships
        author = relationship("User", back_populates="posts")

        def __json__(self, request):
            return {
                "id": self.id,
                "title": self.title,
                "content": self.content,
                "author_id": self.author_id,
                "created_at": self.created_at,
                "is_published": self.is_published,
            }

Database Engine Setup
---------------------

.. code-block:: python

    # database.py
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base


    def get_engine(settings):
        """Create database engine from settings."""
        return create_engine(
            settings["sqlalchemy.url"],
            echo=settings.get("sqlalchemy.echo", False),
            pool_size=int(settings.get("sqlalchemy.pool_size", 10)),
            max_overflow=int(settings.get("sqlalchemy.max_overflow", 20)),
            pool_timeout=int(settings.get("sqlalchemy.pool_timeout", 30)),
            pool_recycle=int(settings.get("sqlalchemy.pool_recycle", 3600)),
        )


    def get_session_factory(engine):
        """Create session factory."""
        return sessionmaker(bind=engine)


    def initialize_database(engine):
        """Initialize database tables."""
        Base.metadata.create_all(engine)

Request-Scoped Sessions with Tet
==================================

Tet provides automatic database session management through pyramid_di and pyramid_tm.

Tet's SQLAlchemy Integration
----------------------------

.. code-block:: python

    # app.py
    from tet.config import application_factory, ALL_FEATURES
    from tet.sqlalchemy.simple import declarative_base

    # Create declarative base using Tet's helper
    Base = declarative_base()


    @application_factory(included_features=ALL_FEATURES)
    def main(config):
        """Tet application factory with database support."""

        # Include Tet's simple SQLAlchemy setup
        config.include("tet.sqlalchemy.simple")

        # Setup SQLAlchemy - automatically configures:
        # - pyramid_di service registration
        # - pyramid_tm transaction management
        # - Request-scoped sessions
        config.setup_sqlalchemy()

        # Routes and views
        config.add_route("users", "/users")
        config.add_route("user", "/users/{id}")
        config.scan("views")

Settings Configuration
----------------------

Configure your database in settings (e.g., `development.ini`):

.. code-block:: ini

    [app:main]
    use = egg:myapp

    # SQLAlchemy configuration
    sqlalchemy.url = sqlite:///myapp.db
    sqlalchemy.echo = false
    sqlalchemy.pool_size = 10

Automatic Features Included
---------------------------

When you use `config.setup_sqlalchemy()`, Tet automatically configures:

1. **pyramid_di**: For dependency injection
2. **pyramid_tm**: For transaction management
3. **Request-scoped sessions**: Sessions tied to request lifecycle
4. **Automatic commit/rollback**: Based on HTTP response status
5. **Session cleanup**: Sessions closed automatically after request

Root Factories
==============

Use Tet's ``SQLARootFactory`` for traversal-based applications.

Basic Root Factory
------------------

.. code-block:: python

    # root.py
    from tet.sqlalchemy.factory import SQLARootFactory
    from models import User, Post
    from sqlalchemy.orm.exc import NoResultFound


    class UserRootFactory(SQLARootFactory):
        """Root factory for user resources."""

        def supplier(self, item):
            """Look up user by ID."""
            session = self.request.find_service(name="dbsession")
            try:
                return session.query(User).filter_by(id=int(item)).one()
            except (NoResultFound, ValueError):
                # These exceptions are converted to KeyError (404)
                raise


    class PostRootFactory(SQLARootFactory):
        """Root factory for post resources."""

        def supplier(self, item):
            """Look up post by ID or slug."""
            session = self.request.find_service(name="dbsession")

            try:
                # Try numeric ID first
                post_id = int(item)
                return session.query(Post).filter_by(id=post_id).one()
            except ValueError:
                # Try as slug
                try:
                    return session.query(Post).filter_by(slug=item).one()
                except NoResultFound:
                    raise

Multi-Model Root Factory
------------------------

.. code-block:: python

    class ApplicationRootFactory(SQLARootFactory):
        """Root factory that handles multiple resource types."""

        def supplier(self, item):
            """Route to appropriate model based on item format."""
            session = self.request.find_service(name="dbsession")

            # Handle different patterns
            if item.startswith("user-"):
                user_id = item[5:]  # Remove 'user-' prefix
                try:
                    return session.query(User).filter_by(id=int(user_id)).one()
                except (NoResultFound, ValueError):
                    raise

            elif item.startswith("post-"):
                post_id = item[5:]  # Remove 'post-' prefix
                try:
                    return session.query(Post).filter_by(id=int(post_id)).one()
                except (NoResultFound, ValueError):
                    raise

            else:
                # Try as numeric ID for backwards compatibility
                try:
                    # Default to User lookup
                    return session.query(User).filter_by(id=int(item)).one()
                except (NoResultFound, ValueError):
                    raise

Using Root Factories
--------------------

Configure traversal with root factories:

.. code-block:: python

    def main(global_config, **settings):
        with Configurator(settings=settings) as config:
            # Set root factory for traversal
            config.set_root_factory(ApplicationRootFactory)

            # Add traversal routes
            config.add_route("user_detail", "/users/*traverse")
            config.add_route("post_detail", "/posts/*traverse")

            return config.make_wsgi_app()

Database Views
==============

Create views that work with Tet's database integration.

User Management Views
---------------------

.. code-block:: python

    # views/users.py
    from pyramid.view import view_config
    from pyramid.httpexceptions import HTTPNotFound, HTTPBadRequest
    from pyramid_di import autowired
    from sqlalchemy.orm import Session
    from models import User


    class UserViews:
        """User management views with autowired dependencies."""

        # Database session automatically injected via pyramid_di
        session: Session = autowired()

        @view_config(route_name="users", request_method="GET", renderer="json")
        def list_users(self, request):
            """List all users."""
            # Pagination
            page = int(request.params.get("page", 1))
            per_page = int(request.params.get("per_page", 20))

            query = self.session.query(User).filter_by(is_active=True)

            # Apply filters
            if "search" in request.params:
                search = f"%{request.params['search']}%"
                query = query.filter(User.username.ilike(search))

            # Paginate
            total = query.count()
            users = query.offset((page - 1) * per_page).limit(per_page).all()

            return {
                "users": users,  # Automatically serialized by Tet
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
            }

        @view_config(route_name="user", request_method="GET", renderer="json")
        def get_user(self, request):
            """Get single user by ID."""
            user_id = request.matchdict["id"]

            try:
                user = self.session.query(User).filter_by(id=int(user_id)).one()
                return {"user": user}
            except (NoResultFound, ValueError):
                raise HTTPNotFound("User not found")

        @view_config(route_name="users", request_method="POST", renderer="json")
        def create_user(self, request):
            """Create new user."""
            data = request.json_body

            # Validation
            if not data.get("username") or not data.get("email"):
                raise HTTPBadRequest("Username and email are required")

            # Check for existing user
            existing = (
                self.session.query(User)
                .filter((User.username == data["username"]) | (User.email == data["email"]))
                .first()
            )

            if existing:
                raise HTTPBadRequest("Username or email already exists")

            # Create user
            user = User(
                username=data["username"],
                email=data["email"],
                password_hash=hash_password(data.get("password", "")),
            )

            self.session.add(user)
            # No manual commit needed - pyramid_tm handles it automatically

            return {"user": user, "message": "User created successfully"}

Relationship Handling
---------------------

.. code-block:: python

    @view_config(route_name="user_posts", renderer="json")
    def get_user_posts(request):
        """Get posts by user."""
        user_id = request.matchdict["user_id"]
        session = request.find_service(name="dbsession")

        try:
            user = session.query(User).filter_by(id=int(user_id)).one()
        except (NoResultFound, ValueError):
            raise HTTPNotFound("User not found")

        # Get user's posts with eager loading
        posts = (
            session.query(Post)
            .filter_by(author_id=user.id, is_published=True)
            .order_by(Post.created_at.desc())
            .all()
        )

        return {"user": user, "posts": posts, "post_count": len(posts)}

Complex Queries
---------------

.. code-block:: python

    from sqlalchemy import func, desc


    @view_config(route_name="user_stats", renderer="json")
    def user_statistics(request):
        """Get user statistics."""
        session = request.find_service(name="dbsession")

        # Complex query with aggregations
        stats = (
            session.query(
                User.id,
                User.username,
                func.count(Post.id).label("post_count"),
                func.max(Post.created_at).label("last_post_date"),
            )
            .outerjoin(Post)
            .group_by(User.id)
            .all()
        )

        # The results are automatically JSON-serializable
        return {"user_stats": stats}


    @view_config(route_name="popular_posts", renderer="json")
    def popular_posts(request):
        """Get popular posts with author info."""
        session = request.find_service(name="dbsession")

        # Join query with eager loading
        posts = (
            session.query(Post)
            .join(User)
            .filter(Post.is_published == True)
            .order_by(desc(Post.created_at))
            .limit(10)
            .all()
        )

        # Custom serialization including author info
        result = []
        for post in posts:
            result.append(
                {
                    "id": post.id,
                    "title": post.title,
                    "content": post.content[:200] + "...",  # Truncate
                    "created_at": post.created_at,
                    "author": {"id": post.author.id, "username": post.author.username},
                }
            )

        return {"posts": result}

Transaction Management
======================

Tet automatically handles database transactions through pyramid_tm.

Automatic Transaction Management
--------------------------------

With Tet's SQLAlchemy setup, transactions are handled automatically:

.. code-block:: python

    @application_factory(included_features=ALL_FEATURES)
    def main(config):
        """Tet automatically includes pyramid_tm."""
        config.include("tet.sqlalchemy.simple")
        config.setup_sqlalchemy()

        # pyramid_tm is automatically included and configured
        # Transactions are:
        # - Started for each request
        # - Committed on successful response (2xx, 3xx)
        # - Rolled back on exceptions or error responses (4xx, 5xx)

Working with Automatic Transactions
-----------------------------------

Your views don't need to manage transactions manually:

.. code-block:: python

    @view_config(route_name="complex_operation", renderer="json")
    def complex_database_operation(request):
        """Complex operation with automatic transaction management."""
        session = request.find_service(Session)

        # All operations happen in one transaction
        # Create user
        user = User(username="newuser", email="new@example.com")
        session.add(user)
        session.flush()  # Get the ID without committing

        # Create initial post
        post = Post(
            title="Welcome Post",
            content="Welcome to the platform!",
            author_id=user.id,
            is_published=True,
        )
        session.add(post)

        # If view returns successfully, transaction commits automatically
        # If any exception is raised, transaction rolls back automatically
        return {"message": "Operation completed successfully", "user": user}

Handling Transaction Rollbacks
------------------------------

To trigger a rollback, raise an HTTP exception:

.. code-block:: python

    from pyramid.httpexceptions import HTTPBadRequest


    @view_config(route_name="conditional_operation", renderer="json")
    def conditional_operation(request):
        session = request.find_service(Session)

        # Do some work
        user = User(username="test")
        session.add(user)

        # Check some condition
        if some_validation_fails():
            # This will cause automatic transaction rollback
            raise HTTPBadRequest("Validation failed")

        # If we reach here, transaction will commit automatically
        return {"user": user}

Bulk Operations
---------------

.. code-block:: python

    @view_config(route_name="bulk_import", request_method="POST", renderer="json")
    def bulk_import_users(request):
        """Bulk import users efficiently."""
        session = request.find_service(name="dbsession")
        users_data = request.json_body.get("users", [])

        try:
            # Bulk insert for better performance
            user_objects = []
            for user_data in users_data:
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=hash_password(user_data.get("password", "")),
                )
                user_objects.append(user)

            # Bulk save
            session.bulk_save_objects(user_objects)
            session.commit()

            return {
                "message": f"Successfully imported {len(user_objects)} users",
                "count": len(user_objects),
            }

        except Exception as e:
            session.rollback()
            raise HTTPBadRequest(f"Bulk import failed: {str(e)}")

Database Migrations
===================

Handle database schema changes.

Simple Migration System
-----------------------

.. code-block:: python

    # migrations.py
    from sqlalchemy import text

    MIGRATIONS = {
        "001_add_user_bio": """
            ALTER TABLE users ADD COLUMN bio TEXT;
        """,
        "002_add_post_slug": """
            ALTER TABLE posts ADD COLUMN slug VARCHAR(200);
            CREATE INDEX idx_posts_slug ON posts(slug);
        """,
        "003_add_timestamps": """
            ALTER TABLE users ADD COLUMN updated_at TIMESTAMP;
            ALTER TABLE posts ADD COLUMN updated_at TIMESTAMP;
        """,
    }


    def run_migrations(engine):
        """Run pending migrations."""
        with engine.connect() as conn:
            # Create migrations table if it doesn't exist
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            )

            # Get applied migrations
            result = conn.execute(text("SELECT id FROM migrations"))
            applied = {row[0] for row in result}

            # Run pending migrations
            for migration_id, sql in MIGRATIONS.items():
                if migration_id not in applied:
                    print(f"Running migration: {migration_id}")
                    conn.execute(text(sql))
                    conn.execute(
                        text("INSERT INTO migrations (id) VALUES (:id)"),
                        {"id": migration_id},
                    )
                    conn.commit()

Using Alembic
-------------

For production applications, use Alembic for migrations:

.. code-block:: bash

    pip install alembic
    alembic init alembic
    alembic revision --autogenerate -m "Initial migration"
    alembic upgrade head

Testing Database Code
=====================

Test your database interactions thoroughly.

Database Test Setup
-------------------

.. code-block:: python

    # conftest.py
    import pytest
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, User, Post


    @pytest.fixture(scope="session")
    def engine():
        """Create test database engine."""
        return create_engine("sqlite:///:memory:", echo=False)


    @pytest.fixture(scope="session")
    def tables(engine):
        """Create all tables for testing."""
        Base.metadata.create_all(engine)
        yield
        Base.metadata.drop_all(engine)


    @pytest.fixture(scope="function")
    def dbsession(engine, tables):
        """Create database session for each test."""
        Session = sessionmaker(bind=engine)
        session = Session()
        yield session
        session.rollback()
        session.close()


    @pytest.fixture
    def sample_user(dbsession):
        """Create sample user for testing."""
        user = User(
            username="testuser", email="test@example.com", password_hash="hashed_password"
        )
        dbsession.add(user)
        dbsession.commit()
        return user

Testing Views with Database
---------------------------

.. code-block:: python

    # test_views.py
    def test_create_user(dbsession):
        from views.users import create_user
        from pyramid.testing import DummyRequest

        # Mock request
        request = DummyRequest()
        request.find_service = lambda name: dbsession
        request.json_body = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
        }

        # Test the view
        result = create_user(request)

        assert result["message"] == "User created successfully"
        assert result["user"].username == "newuser"

        # Verify in database
        user = dbsession.query(User).filter_by(username="newuser").first()
        assert user is not None
        assert user.email == "new@example.com"


    def test_user_posts(dbsession, sample_user):
        from views.users import get_user_posts
        from pyramid.testing import DummyRequest

        # Create test posts
        post1 = Post(title="Post 1", author_id=sample_user.id, is_published=True)
        post2 = Post(title="Post 2", author_id=sample_user.id, is_published=False)
        dbsession.add_all([post1, post2])
        dbsession.commit()

        # Test the view
        request = DummyRequest()
        request.find_service = lambda name: dbsession
        request.matchdict = {"user_id": str(sample_user.id)}

        result = get_user_posts(request)

        assert result["user"].id == sample_user.id
        assert len(result["posts"]) == 1  # Only published posts
        assert result["posts"][0].title == "Post 1"

Testing Root Factories
----------------------

.. code-block:: python

    def test_user_root_factory(dbsession, sample_user):
        from root import UserRootFactory
        from pyramid.testing import DummyRequest

        request = DummyRequest()
        request.find_service = lambda name: dbsession

        root = UserRootFactory(request)

        # Test successful lookup
        found_user = root[str(sample_user.id)]
        assert found_user == sample_user

        # Test not found
        with pytest.raises(KeyError):
            root["999"]

Performance Optimization
========================

Optimize database performance.

Query Optimization
------------------

.. code-block:: python

    from sqlalchemy.orm import joinedload, selectinload


    @view_config(route_name="optimized_posts", renderer="json")
    def optimized_posts_view(request):
        """Optimized post loading with eager loading."""
        session = request.find_service(name="dbsession")

        # Eager load relationships to avoid N+1 queries
        posts = (
            session.query(Post)
            .options(
                joinedload(Post.author),  # Join load for one-to-one/many-to-one
                selectinload(Post.comments),  # Select load for one-to-many
            )
            .filter_by(is_published=True)
            .all()
        )

        return {"posts": posts}

Connection Pooling
------------------

.. code-block:: python

    def get_engine(settings):
        """Configure engine with optimized connection pooling."""
        return create_engine(
            settings["sqlalchemy.url"],
            # Connection pool settings
            pool_size=20,  # Number of connections to maintain
            max_overflow=50,  # Additional connections beyond pool_size
            pool_timeout=30,  # Seconds to wait for connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            # Query optimization
            echo=False,  # Don't log SQL in production
            echo_pool=False,  # Don't log pool events
        )

Query Caching
-------------

.. code-block:: python

    from functools import lru_cache


    @lru_cache(maxsize=100)
    def get_popular_tags():
        """Cache popular tags query."""
        # This would need to be implemented with cache invalidation
        # in a real application
        pass

Best Practices
==============

**Session Management**
- Always use request-scoped sessions
- Ensure sessions are properly closed
- Use transaction management (pyramid_tm)

**Query Optimization**
- Use eager loading to avoid N+1 queries
- Only select needed columns for large datasets
- Use proper indexing on frequently queried columns

**Error Handling**
- Use Tet's root factories for proper exception handling
- Handle database exceptions gracefully
- Provide meaningful error messages

**Security**
- Always use parameterized queries (SQLAlchemy ORM does this)
- Validate input data before database operations
- Don't expose sensitive data in JSON responses

**Testing**
- Use isolated test databases
- Test both success and failure scenarios
- Use fixtures for consistent test data

**Performance**
- Configure appropriate connection pooling
- Use database migrations for schema changes
- Monitor query performance in production
