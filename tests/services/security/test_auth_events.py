import logging

import pytest
from pyramid import testing
from pyramid.events import subscriber

from tet.security.events import LoginSuccessEvent, LoginFailedEvent

logger = logging.getLogger(__name__)

DEFAULT_MESSAGE = "Event triggers the simulated audit log:"


@subscriber(LoginSuccessEvent)
def login_success_event_handler(event: LoginSuccessEvent):
    """
    Handle the LoginSuccessEvent.
    This is a placeholder for any additional logic you want to execute
    when a user successfully logs in.
    """
    logger.info(f"{DEFAULT_MESSAGE} {event.request.message}")


@subscriber(LoginFailedEvent)
def login_failed_event_handler(event: LoginFailedEvent):
    """
    Handle the LoginSuccessEvent.
    This is a placeholder for any additional logic you want to execute
    when a user successfully logs in.
    """
    logger.warning(f"{DEFAULT_MESSAGE} {event.request.message}")


@pytest.fixture
def pyramid_request_with_event(request):
    def _make(handler, event_class):
        config = testing.setUp()
        config.add_subscriber(handler, event_class)
        req = testing.DummyRequest()
        request.addfinalizer(testing.tearDown)
        return req

    return _make


def test_login_success_event(pyramid_request_with_event, caplog):
    req = pyramid_request_with_event(login_success_event_handler, LoginSuccessEvent)
    message = "Login successful"
    req.message = message
    with caplog.at_level("INFO", logger=__name__):
        req.registry.notify(LoginSuccessEvent(request=req))
    assert f"{DEFAULT_MESSAGE} {message}" in caplog.text


def test_login_failed_event(pyramid_request_with_event, caplog):
    req = pyramid_request_with_event(login_failed_event_handler, LoginFailedEvent)
    message = "Login failed"
    req.message = message
    with caplog.at_level("WARNING", logger=__name__):
        req.registry.notify(LoginFailedEvent(request=req))
    assert f"{DEFAULT_MESSAGE} {message}" in caplog.text


# TODO: More test with the actual views
