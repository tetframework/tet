import json
import logging as l

import pytest
import structlog
from pyramid import testing
from pyramid.events import subscriber
from webtest import TestApp

from tests.services.constants import LOGIN_ENDPOINT
from tet.security.authentication import TetTokenService
from tet.security.events import AuthnLoginSuccess, AuthnLoginFail

logger = l.getLogger(__name__)

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
    Handle the LoginFailEvent.
    This is a placeholder for any additional logic you want to execute
    when a user failed to log in.
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


def test_login_success_event_with_fake_request(pyramid_request_with_event, caplog):
    req = pyramid_request_with_event(login_success_event_handler, AuthnLoginSuccess)
    user_identity = "example@gmail.invalid"
    message = f"User {user_identity} Login successful"
    req.message = message
    with caplog.at_level("INFO", logger=__name__):
        req.registry.notify(AuthnLoginSuccess(request=req, user_identity=user_identity))
    assert f"{DEFAULT_MESSAGE} {message}" in caplog.text


def test_login_failed_event_with_fake_request(pyramid_request_with_event, caplog):
    req = pyramid_request_with_event(login_failed_event_handler, AuthnLoginFail)
    user_identity = "user1@gmail.invalid"
    message = f"User {user_identity} Login failed"
    req.message = message
    with caplog.at_level("WARNING", logger=__name__):
        req.registry.notify(AuthnLoginFail(request=req, user_identity=user_identity))
    assert f"{DEFAULT_MESSAGE} {message}" in caplog.text


# More test with the actual views


@pytest.fixture()
def structlog_security_config():
    """
    Configure structlog for security-related logging.

    More info about structlog configuration:
    https://www.structlog.org/en/stable/configuration.html

    For more detail on each processor:
    https://www.structlog.org/en/stable/processors.html#module-structlog.processors

    For logger factory:
    https://www.structlog.org/en/stable/api.html#structlog.stdlib.LoggerFactory
    """
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    yield
    structlog.reset_defaults()


@pytest.fixture()
def pyramid_test_app_with_jwt_cookie_policy(request, pyramid_app):
    return TestApp(pyramid_app)


@pytest.fixture()
def token_service(pyramid_request):
    return pyramid_request.find_service(TetTokenService)


@pytest.fixture
def capture_token(monkeypatch, token_service, db_session):
    captured_data = {}

    create_long_term_token = TetTokenService.create_long_term_token
    create_short_term_jwt = TetTokenService.create_short_term_jwt

    def create_long_term_token_wrapper(*args, **kwargs):
        token = create_long_term_token(*args, **kwargs)
        captured_data["refresh_token"] = token
        return token

    def create_short_term_jwt_wrapper(*args, **kwargs):
        token = create_short_term_jwt(*args, **kwargs)
        captured_data["access_token"] = token
        return token

    monkeypatch.setattr(TetTokenService, "create_long_term_token", create_long_term_token_wrapper)
    monkeypatch.setattr(TetTokenService, "create_short_term_jwt", create_short_term_jwt_wrapper)
    return captured_data


DEFAULT_USER_IDENTITY = "exampple2@invalid.invalid"
DEFAULT_USER_PASSWORD = "1234@abcd"


def test_login_view_emits_success_event(
    pyramid_test_app_with_jwt_cookie_policy,
    capture_token,
    pyramid_request,
    caplog,
    structlog_security_config,
):
    app = pyramid_test_app_with_jwt_cookie_policy
    data = json.dumps({"user_identity": DEFAULT_USER_IDENTITY, "password": DEFAULT_USER_PASSWORD})
    expected_description = f"User {DEFAULT_USER_IDENTITY} logged in successfully."

    with caplog.at_level("INFO", logger="audit"):
        app.post(
            LOGIN_ENDPOINT,
            params=data,
            content_type="application/json",
            status=200,
        )

    matched = [
        r
        for r in caplog.records
        if r.levelname == "INFO" and r.name == "audit" and expected_description in r.getMessage()
    ]
    assert matched, f"No INFO log with description '{expected_description}' found in 'audit' logger"


def test_login_view_emits_fail_event(
    pyramid_test_app_with_jwt_cookie_policy, pyramid_request, caplog, structlog_security_config
):
    app = pyramid_test_app_with_jwt_cookie_policy
    data = json.dumps({"user_identity": DEFAULT_USER_IDENTITY, "password": "wrong_password"})

    with caplog.at_level("WARNING", logger="audit"):
        app.post(
            LOGIN_ENDPOINT,
            params=data,
            content_type="application/json",
            status=401,
        )
    expected_description = f"User {DEFAULT_USER_IDENTITY} failed to log in."
    matched = [
        r
        for r in caplog.records
        if r.levelname == "WARNING" and r.name == "audit" and expected_description in r.getMessage()
    ]
    assert matched, (
        f"No WARNING log with description '{expected_description}' found in 'audit' logger"
    )
