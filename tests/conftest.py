"""
Pytest configuration and fixtures for Tet framework tests.
"""
from unittest.mock import Mock

import pytest
from pyramid import testing
from pyramid.config import Configurator


@pytest.fixture
def pyramid_config():
    """Create a Pyramid configurator for testing."""
    config = Configurator()
    config.begin()
    yield config
    config.end()


@pytest.fixture
def pyramid_request():
    """Create a dummy Pyramid request for testing."""
    request = testing.DummyRequest()
    request.registry = Mock()
    return request


@pytest.fixture
def pyramid_request_with_json():
    """Create a dummy Pyramid request with JSON body."""
    request = testing.DummyRequest()
    request.json_body = {}
    request.registry = Mock()
    return request


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.flush = Mock()
    return session


@pytest.fixture
def mock_model():
    """Create a mock SQLAlchemy model."""
    model = Mock()
    model.__tablename__ = 'test_model'
    return model
