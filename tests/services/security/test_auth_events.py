import logging

import pytest
from pyramid import testing
from pyramid.events import subscriber

from tet.security.events import AuthnLoginSuccess, AuthnLoginFail

logger = logging.getLogger(__name__)

DEFAULT_MESSAGE = "Event triggers the simulated audit log:"


@subscriber(AuthnLoginSuccess)
def login_success_event_handler(event: AuthnLoginSuccess):
    """
    Handle the LoginSuccessEvent.
    This is a placeholder for any additional logic you want to execute
    when a user successfully logs in.
    """
    logger.info(f"{DEFAULT_MESSAGE} {event.request.message}")


@subscriber(AuthnLoginFail)
def login_failed_event_handler(event: AuthnLoginFail):
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
    req = pyramid_request_with_event(login_success_event_handler, AuthnLoginSuccess)
    user_identity = "example@gmail.invalid"
    message = f"User {user_identity} Login successful"
    req.message = message
    with caplog.at_level("INFO", logger=__name__):
        req.registry.notify(AuthnLoginSuccess(request=req, user_identity=user_identity))
    assert f"{DEFAULT_MESSAGE} {message}" in caplog.text


def test_login_failed_event(pyramid_request_with_event, caplog):
    req = pyramid_request_with_event(login_failed_event_handler, AuthnLoginFail)
    user_identity = "user1@gmail.invalid"
    message = f"User {user_identity} Login failed"
    req.message = message
    with caplog.at_level("WARNING", logger=__name__):
        req.registry.notify(AuthnLoginFail(request=req, user_identity=user_identity))
    assert f"{DEFAULT_MESSAGE} {message}" in caplog.text


# TODO: More test with the actual views
