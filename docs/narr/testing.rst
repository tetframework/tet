=======
Testing
=======

Tet applications and the Tet framework itself are tested with `pytest
<https://docs.pytest.org/>`_. This chapter documents the test layout actually
used in this project (Tet 0.5.0, Python 3.8+), the fixtures that ship in
``tests/conftest.py``, and practical patterns for testing your own Tet
applications.

Running the Tests
=================

Install Tet together with its test dependencies in editable mode and run
``pytest``::

    # Test dependencies only (pytest, pytest-cov)
    pip install -e '.[test]'

    # Full development toolchain (pytest, pytest-cov, black, ruff, mypy)
    pip install -e '.[dev]'

    # Run the whole suite
    pytest

The project configures pytest in ``pyproject.toml`` under
``[tool.pytest.ini_options]``. The relevant settings are::

    [tool.pytest.ini_options]
    testpaths = ["tests"]
    python_files = ["test_*.py", "*_test.py"]
    addopts = "-ra -q --strict-markers"
    markers = [
        "slow: marks tests as slow (deselect with '-m \"not slow\"')",
        "integration: marks tests as integration tests",
    ]

Because ``testpaths`` is set to ``tests``, a bare ``pytest`` invocation
collects only the ``tests/`` directory. ``--strict-markers`` means every
marker must be declared in ``markers`` (above) or collection fails, so use the
declared markers rather than inventing new ones.

Two markers are available:

``slow``
  Mark long-running tests. Deselect them with ``pytest -m "not slow"``.

``integration``
  Mark integration tests. Run only these with ``pytest -m integration``.

.. code-block:: python

    import pytest


    @pytest.mark.slow
    def test_expensive_operation(): ...


    @pytest.mark.integration
    def test_full_request_cycle(app): ...

Coverage is available through ``pytest-cov`` (installed by both the ``test``
and ``dev`` extras)::

    pytest --cov=tet --cov-report=term-missing

Built-in Fixtures
=================

The shared ``tests/conftest.py`` provides a small set of fixtures used
throughout the suite. They are all function-scoped.

``pyramid_config``
  A real :class:`pyramid.config.Configurator` with ``config.begin()`` already
  called; ``config.end()`` runs automatically on teardown. Use it to test
  ``includeme`` functions and configuration directives.

``pyramid_request``
  A :class:`pyramid.testing.DummyRequest` whose ``registry`` attribute is a
  :class:`unittest.mock.Mock`.

``pyramid_request_with_json``
  Like ``pyramid_request`` but with ``request.json_body`` set to an empty
  ``dict``.

``mock_db_session``
  A :class:`unittest.mock.Mock` with ``query``, ``add``, ``commit``,
  ``rollback`` and ``flush`` attributes pre-created as mocks.

``mock_model``
  A :class:`unittest.mock.Mock` with ``__tablename__`` set to
  ``"test_model"``.

The actual definitions look like this:

.. code-block:: python

    # tests/conftest.py
    from unittest.mock import Mock

    import pytest
    from pyramid import testing
    from pyramid.config import Configurator


    @pytest.fixture
    def pyramid_config():
        config = Configurator()
        config.begin()
        yield config
        config.end()


    @pytest.fixture
    def pyramid_request():
        request = testing.DummyRequest()
        request.registry = Mock()
        return request


    @pytest.fixture
    def mock_db_session():
        session = Mock()
        session.query = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.flush = Mock()
        return session

Testing ``includeme`` Functions
===============================

Most Tet modules expose an ``includeme(config)`` entry point. The
``pyramid_config`` fixture makes these easy to exercise. For example, the CSRF
module sets ``require_csrf=True``:

.. code-block:: python

    # tests/test_security_csrf.py
    from unittest.mock import Mock

    from tet.security.csrf import includeme


    def test_includeme_sets_csrf_defaults(pyramid_config):
        pyramid_config.set_default_csrf_options = Mock()

        includeme(pyramid_config)

        pyramid_config.set_default_csrf_options.assert_called_once_with(require_csrf=True)

Testing Views
=============

Pyramid views can be called directly with a dummy request. Use the
``pyramid_request`` fixture rather than constructing a request by hand:

.. code-block:: python

    # tests/test_views.py
    from myapp.views import home_view


    def test_home_view(pyramid_request):
        response = home_view(pyramid_request)
        assert response["message"] == "Hello, World!"

When a view reads JSON from the request body, use
``pyramid_request_with_json`` and set the body content you need:

.. code-block:: python

    def test_api_view(pyramid_request_with_json):
        pyramid_request_with_json.json_body = {"name": "example"}

        from myapp.views import create_view

        result = create_view(pyramid_request_with_json)
        assert result["created"] is True

Testing the JSON Renderer
=========================

Tet's JSON renderer lives in :mod:`tet.renderers.json`. The public surface is:

``construct_default_renderer(renderer_factory=JSON, **renderer_args)``
  Builds a Pyramid :class:`pyramid.renderers.JSON` renderer pre-loaded with
  adapters for :class:`datetime.datetime`, :class:`datetime.date`, and (when
  SQLAlchemy is installed) SQLAlchemy keyed tuples.

``hook_json_renderer(config, *, renderer, name="json")``
  Registers a renderer under a name and records it in the per-registry
  renderer registry.

``add_json_adapter(config, *, for_, adapter, renderer="json")``
  Adds a type adapter to a named, already-registered renderer.

``includeme(config)``
  Registers the default renderer and adds the ``add_json_renderer`` and
  ``add_json_adapter`` directives.

Note that ``construct_default_renderer`` returns a Pyramid ``JSON`` renderer
*factory* instance. It is not a plain callable that turns data into a string;
to actually render, Pyramid calls it with renderer ``info`` to obtain the
render function. The simplest way to test serialization is therefore to test
the adapters and helpers directly, or to register the renderer on a
configurator. To check that the default adapters are present:

.. code-block:: python

    # tests/test_renderers_json.py
    from tet.renderers.json import construct_default_renderer


    def test_default_renderer_constructs():
        renderer = construct_default_renderer()
        # It is a Pyramid JSON renderer factory instance with adapters added.
        assert renderer is not None

To test the configuration directives, use ``pyramid_config`` and inspect the
per-registry renderer registry that ``hook_json_renderer`` maintains:

.. code-block:: python

    from unittest.mock import Mock

    from tet.renderers.json import hook_json_renderer


    def test_hook_json_renderer_default_name(pyramid_config):
        renderer = Mock()
        pyramid_config.add_renderer = Mock()
        pyramid_config.registry.tet_json_renderers = {}

        hook_json_renderer(pyramid_config, renderer=renderer)

        pyramid_config.add_renderer.assert_called_once_with("json", renderer)
        assert pyramid_config.registry.tet_json_renderers["json"] is renderer

Testing Safe JSON Serialization
===============================

:func:`tet.util.json.js_safe_dumps` escapes characters that are dangerous
inside inline ``<script>`` blocks. Unlike the renderer above, it *is* a plain
callable that returns a string:

.. code-block:: python

    # tests/test_util_json.py
    from tet.util.json import js_safe_dumps


    def test_escapes_less_than():
        result = js_safe_dumps("test<script>")
        assert result == '"test\\u003cscript\\u003e"'
        assert "<" not in result
        assert ">" not in result

The ``<``, ``>`` and ``/`` characters are escaped to their ``\uXXXX`` forms,
so the output is safe to embed directly in HTML.

Testing the SQLAlchemy Root Factory
===================================

:class:`tet.sqlalchemy.factory.SQLARootFactory` converts SQLAlchemy lookup
exceptions into :class:`KeyError`. It can be tested with the
``pyramid_request`` fixture and a mocked ``supplier`` method, mirroring the
real test suite:

.. code-block:: python

    # tests/test_sqlalchemy_factory.py
    from unittest.mock import Mock

    import pytest
    from sqlalchemy.orm.exc import NoResultFound

    from tet.sqlalchemy.factory import SQLARootFactory


    def test_getitem_success(pyramid_request):
        factory = SQLARootFactory(pyramid_request)
        expected = Mock()
        factory.supplier = Mock(return_value=expected)

        assert factory["test_id"] is expected
        factory.supplier.assert_called_once_with("test_id")


    def test_getitem_raises_keyerror_on_noresult(pyramid_request):
        factory = SQLARootFactory(pyramid_request)
        factory.supplier = Mock(side_effect=NoResultFound("No result found"))

        with pytest.raises(KeyError) as exc_info:
            _ = factory["missing_id"]

        # NoResultFound is preserved as the cause of the KeyError.
        assert isinstance(exc_info.value.__cause__, NoResultFound)

The factory also converts :class:`sqlalchemy.orm.exc.MultipleResultsFound` and
:class:`sqlalchemy.exc.DataError` into ``KeyError`` in the same way.

Testing with a Real Database
============================

The built-in ``mock_db_session`` fixture is enough for unit tests that only
need to assert how a session is used. When you need real persistence, define
your own SQLAlchemy fixtures in your application's ``conftest.py``:

.. code-block:: python

    # conftest.py (in your application)
    import pytest
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from myapp.models import Base


    @pytest.fixture(scope="session")
    def engine():
        return create_engine("sqlite:///:memory:")


    @pytest.fixture(scope="session")
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

Integration Testing with WebTest
================================

For full request/response cycles, build your WSGI application and wrap it in a
`WebTest <https://docs.pylonsproject.org/projects/webtest/>`_ ``TestApp``.
WebTest is not a dependency of Tet, so add it to your own test requirements.

.. code-block:: python

    # conftest.py (in your application)
    import pytest
    from webtest import TestApp

    from myapp import main


    @pytest.fixture(scope="session")
    def app():
        settings = {"sqlalchemy.url": "sqlite:///:memory:"}
        return TestApp(main({}, **settings))


    # test_integration.py
    import pytest


    @pytest.mark.integration
    def test_home_page(app):
        response = app.get("/")
        assert response.status_code == 200

Mock Testing
============

Use :mod:`unittest.mock` to isolate views and services from their
dependencies. The ``mock_db_session`` fixture provides a ready-made mocked
session:

.. code-block:: python

    from unittest.mock import Mock


    def test_view_with_service(pyramid_request, mock_db_session):
        mock_db_session.query.return_value.all.return_value = [
            Mock(id=1, name="User 1"),
            Mock(id=2, name="User 2"),
        ]
        pyramid_request.find_service = Mock(return_value=mock_db_session)

        from myapp.views import user_list_view

        result = user_list_view(pyramid_request)
        assert len(result["users"]) == 2

Patch external calls at the point where they are used:

.. code-block:: python

    from unittest.mock import patch


    @patch("myapp.services.external_api_call")
    def test_external_service(mock_api_call):
        mock_api_call.return_value = {"status": "success"}

        from myapp.services import process_external_data

        result = process_external_data("test_data")
        assert result["status"] == "success"
        mock_api_call.assert_called_once_with("test_data")

Test Organization
=================

The Tet test suite keeps a flat ``tests/`` directory whose module names mirror
the package layout, for example::

    tests/
    ├── conftest.py                      # Shared fixtures
    ├── test_renderers_json.py
    ├── test_security_authorization.py
    ├── test_security_csrf.py
    ├── test_sqlalchemy_factory.py
    ├── test_util_base64.py
    ├── test_util_collections.py
    ├── test_util_crypt.py
    └── test_util_json.py

Tests are grouped into classes (``class TestSomething:``) with descriptive
method names. Because ``python_files`` is ``["test_*.py", "*_test.py"]``, both
``test_foo.py`` and ``foo_test.py`` are collected.

Continuous Integration
======================

A minimal GitHub Actions workflow that installs the test extra and runs the
suite across the supported Python versions:

.. code-block:: yaml

    # .github/workflows/test.yml
    name: Tests

    on: [push, pull_request]

    jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: ['3.8', '3.9', '3.10', '3.11', '3.12', '3.13']

        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: ${{ matrix.python-version }}
          - run: |
              python -m pip install --upgrade pip
              pip install -e '.[test]'
          - run: pytest

Best Practices
==============

**Reuse the built-in fixtures**
  Prefer ``pyramid_config``, ``pyramid_request`` and ``mock_db_session`` over
  re-creating equivalents in every test module.

**Respect strict markers**
  Only ``slow`` and ``integration`` are declared. With ``--strict-markers`` an
  undeclared marker fails collection; declare new markers in ``pyproject.toml``
  before using them.

**Test the public API**
  Import from documented entry points such as
  :func:`tet.util.json.js_safe_dumps` and
  :class:`tet.sqlalchemy.factory.SQLARootFactory`.

**Test edge cases**
  Cover error conditions explicitly, for example the ``KeyError`` conversion in
  ``SQLARootFactory``.

**Keep tests independent**
  Each test should run on its own; the function-scoped fixtures help enforce
  this.

**Measure coverage**
  Use ``pytest --cov=tet`` (via ``pytest-cov``) to find untested code paths.
