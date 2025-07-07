import json

import pytest
from jwt import InvalidSignatureError
from sqlalchemy.orm import Session
from webtest import TestApp

from tests.models.accounts import User
from tet.security.authentication import TetTokenService

LOGIN_ENDPOINT = "/api/v1/auth/login"
ACCESS_TOKEN_HEADER_NAME = "Authorization"
LONG_TERM_TOKEN_COOKIE_NAME = "refresh-token"
ACCESS_TOKEN_COOKIE_NAME = "access-token"
HOME_ROUTE = "/"


@pytest.fixture()
def pyramid_test_app(request, pyramid_app):
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
    default_user = db_session.query(User).filter(User.email == user.email).first()
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

    token = tet_token_service.retrieve_and_validate_token(refresh_token, project_prefix)
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
    pytest.raises(
        InvalidSignatureError,
        pyramid_test_app.get,
        HOME_ROUTE,
        headers=headers,
        expect_errors=True,
    )


@pytest.fixture()
def pyramid_test_app_with_jwt_cookie_policy(request, pyramid_app):
    return TestApp(pyramid_app)


def get_cookie(cookiejar, name):
    founded_cookie = [cookie for cookie in cookiejar if cookie.name == name]
    return founded_cookie[0].value if founded_cookie else None


def test_login_view_should_return_refresh_token(
    pyramid_test_app_with_jwt_cookie_policy, capture_token, pyramid_request
):
    refresh_token_cookie_name = pyramid_request.registry.tet_auth_long_term_token_cookie_name
    app = pyramid_test_app_with_jwt_cookie_policy
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = app.post(
        LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    refresh_token = get_cookie(app.cookiejar, refresh_token_cookie_name)
    assert response.status_code == 200
    assert refresh_token == capture_token["refresh_token"]


def test_login_view_should_return_access_token(
    pyramid_test_app_with_jwt_cookie_policy, capture_token, pyramid_request
):
    refresh_token_cookie_name = pyramid_request.registry.tet_auth_long_term_token_cookie_name
    app = pyramid_test_app_with_jwt_cookie_policy
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = app.post(
        LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    data = response.json
    refresh_token = get_cookie(app.cookiejar, refresh_token_cookie_name)
    assert response.status_code == 200
    assert refresh_token == capture_token["refresh_token"]
    assert capture_token["access_token"] == data["access_token"]


def test_access_token_should_work_to_access_protected_route_with_new_policy(
    pyramid_test_app_with_jwt_cookie_policy, capture_token, pyramid_request
):
    refresh_token_cookie_name = pyramid_request.registry.tet_auth_long_term_token_cookie_name
    app = pyramid_test_app_with_jwt_cookie_policy
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = app.post(
        LOGIN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    response_data = response.json
    refresh_token = get_cookie(app.cookiejar, refresh_token_cookie_name)
    access_token = response_data.get("access_token")
    assert response.status_code == 200
    assert refresh_token == capture_token["refresh_token"]
    assert capture_token["access_token"] == access_token

    headers = {ACCESS_TOKEN_HEADER_NAME: f"Bearer {access_token}"}
    response = app.get(HOME_ROUTE, headers=headers, status=200)

    assert response.status_code == 200


# TODO: Test it should be able to decode the access token using JWT
