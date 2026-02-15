import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import jwt as pyjwt
import pytest
from sqlalchemy.orm import Session
from webtest import TestApp

from tests.models.accounts import User
from tests.services.constants import LOGIN_ENDPOINT, ACCESS_TOKEN_HEADER_NAME, HOME_ROUTE
from tests.services.utils.authentication import get_cookie
from tet.security.tokens import TetTokenService


@pytest.fixture()
def pyramid_test_app(pyramid_app):
    return TestApp(pyramid_app)


@pytest.fixture()
def authentication_tokens(pyramid_test_app, capture_token, pyramid_request):
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = pyramid_test_app.post(
        LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    data = response.json
    refresh_token_cookie_name = pyramid_request.registry.tet_auth_long_term_token_cookie_name
    refresh_token = get_cookie(pyramid_test_app.cookiejar, refresh_token_cookie_name)
    access_token = data["access_token"]
    return refresh_token, access_token


def create_user(db_session: Session):
    user = User(email="exampple2@invalid.invalid", name="example2", is_admin=True)
    user.password = "1234@abcd"
    default_user = db_session.query(User).filter(User.email == user.email).one_or_none()
    if default_user:
        return default_user

    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture()
def token_service(pyramid_request):
    return pyramid_request.find_service(TetTokenService)


def test_create_user(db_session, pyramid_test_app):
    default_user = create_user(db_session)
    user = db_session.query(User).filter(User.id == default_user.id).first()
    assert user is not None


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


def test_login_view_should_return_long_term_token(pyramid_test_app, capture_token, pyramid_request):
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = pyramid_test_app.post(
        url=LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    assert response.status_code == 200
    # Validate the token captured by monkeypatch
    refresh_token_cookie_name = pyramid_request.registry.tet_auth_long_term_token_cookie_name
    refresh_token = get_cookie(pyramid_test_app.cookiejar, refresh_token_cookie_name)
    assert capture_token["refresh_token"] == refresh_token

    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 0


def test_login_should_return_refresh_token_in_body(pyramid_test_app, capture_token, pyramid_request):
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = pyramid_test_app.post(
        url=LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    assert response.status_code == 200
    response_data = response.json
    assert "refresh_token" in response_data
    assert response_data["refresh_token"] == capture_token["refresh_token"]


def test_auth_should_return_access_token(pyramid_test_app, capture_token, pyramid_request):
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = pyramid_test_app.post(
        LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    assert response.status_code == 200
    response_data = response.json
    assert "success" in response_data
    assert "access_token" in response_data
    assert response_data["access_token"] == capture_token["access_token"]


def test_access_token_should_work_to_access_protected_route(
    authentication_tokens, pyramid_test_app
):
    refresh_token, access_token = authentication_tokens
    headers = {ACCESS_TOKEN_HEADER_NAME: f"Bearer {access_token}"}
    response = pyramid_test_app.get(HOME_ROUTE, headers=headers, status=200)

    assert response.status_code == 200
    assert "message" in response.json
    assert response.json["message"] == "Hello, World!"


def test_login_view_should_raise_401_when_identity_not_found_in_the_db(
    pyramid_test_app, pyramid_request
):
    response = pyramid_test_app.post(
        url=LOGIN_ENDPOINT,
        params=json.dumps({"user_identity": "invalid_user", "password": "wrong_password"}),
        content_type="application/json",
        status=401,
        expect_errors=True,
    )
    assert response.status_code == 401


def test_it_should_store_the_token_in_the_database(
    capture_token, pyramid_test_app, pyramid_request
):
    project_prefix = pyramid_request.registry.settings["project_prefix"]
    tet_token_service = TetTokenService(request=pyramid_request)
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = pyramid_test_app.post(
        url=LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    data = response.json
    assert response.status_code == 200
    refresh_token_cookie_name = pyramid_request.registry.tet_auth_long_term_token_cookie_name
    refresh_token = get_cookie(pyramid_test_app.cookiejar, refresh_token_cookie_name)
    # Validate the token captured by monkeypatch
    assert capture_token["refresh_token"] == refresh_token
    assert capture_token["access_token"] == data["access_token"]
    assert isinstance(refresh_token, str)
    assert len(refresh_token) > 0

    token = tet_token_service.retrieve_and_validate_token(token=refresh_token, prefix=project_prefix)
    assert token is not None


def test_it_should_fail_to_access_the_protected_route_without_the_access_token(
    pyramid_test_app,
):
    response = pyramid_test_app.get(HOME_ROUTE, status=403, expect_errors=True)
    assert response.status_code == 403


def test_it_should_fail_to_access_the_protected_route_with_invalid_access_token(
    pyramid_test_app,
):
    headers = {
        ACCESS_TOKEN_HEADER_NAME: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MzgwNjk5ODd9"
        ".oeTClyh2CDWH1eHJPuxlm8TwR4zzBK4QZkop17fROa"
    }
    response = pyramid_test_app.get(
        HOME_ROUTE,
        headers=headers,
        status=403,
        expect_errors=True,
    )
    assert response.status_code == 403


def test_verify_jwt_returns_none_for_expired_token(token_service, pyramid_request):
    """Expired JWT should return None, not raise."""
    secret = pyramid_request.registry.settings["tet.security.authentication.secret"]
    expired_payload = {
        "user_id": 1,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    expired_token = pyjwt.encode(expired_payload, secret, algorithm="HS256")
    result = token_service.verify_jwt(expired_token)
    assert result is None


def test_verify_jwt_returns_none_for_invalid_signature(token_service):
    """JWT signed with wrong key should return None, not raise."""
    wrong_payload = {
        "user_id": 1,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    bad_token = pyjwt.encode(wrong_payload, "wrong-secret", algorithm="HS256")
    result = token_service.verify_jwt(bad_token)
    assert result is None


def test_verify_jwt_returns_none_for_malformed_token(token_service):
    """Completely malformed token should return None, not raise."""
    result = token_service.verify_jwt("not.a.valid.jwt.token")
    assert result is None


def test_refresh_token_endpoint_returns_401_when_no_token(pyramid_test_app):
    """Missing refresh token should return 401."""
    response = pyramid_test_app.post(
        "/api/v1/auth/token/refresh",
        params=json.dumps({}),
        content_type="application/json",
        status=401,
        expect_errors=True,
    )
    assert response.status_code == 401


def test_refresh_token_from_request_body(pyramid_test_app, capture_token, pyramid_request):
    """Refresh token should be accepted from request body as well as cookie."""
    # First login to get a refresh token
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    login_response = pyramid_test_app.post(
        LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    refresh_token = login_response.json["refresh_token"]

    # Clear cookies so it must come from request body
    pyramid_test_app.cookiejar.clear()

    response = pyramid_test_app.post(
        "/api/v1/auth/token/refresh",
        params=json.dumps({"refresh_token": refresh_token}),
        content_type="application/json",
        status=200,
    )
    assert response.status_code == 200
    assert "access_token" in response.json
    assert response.json["success"] is True


def test_breach_api_timeout_graceful_degradation(pyramid_request):
    """Breach API timeout should return False, not crash."""
    import requests as req_lib
    from tet.security.auth import TetAuthService

    auth_service = TetAuthService(request=pyramid_request)
    pyramid_request.registry.settings["pwned_passwords_api_url"] = "https://api.pwnedpasswords.com/range/"

    with patch("tet.security.auth.requests.get", side_effect=req_lib.ConnectionError("timeout")):
        result = auth_service.is_password_breached("test_password_123")
    assert result is False
