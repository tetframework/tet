import json

import pytest
from jwt import InvalidSignatureError
from sqlalchemy.orm import Session
from webtest import TestApp

from tests.models.accounts import User
from tet.security.authentication import TetTokenService

ACCESS_TOKEN_ENDPOINT = "/api/v1/auth/access-token"
LONG_TERM_TOKEN_ENDPOINT = "/api/v1/auth/login"
HOME_ROUTE = "/"


@pytest.fixture()
def test_app(pyramid_app):
    return TestApp(pyramid_app)


@pytest.fixture()
def long_term_token(pyramid_app, test_app, capture_token):
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = test_app.post(
        LONG_TERM_TOKEN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )

    return response.json["token"]


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


def test_create_user(db_session):
    default_user = create_user(db_session)
    user = db_session.query(User).filter(User.id == default_user.id).first()
    assert user is not None


@pytest.fixture
def capture_token(monkeypatch, token_service, db_session):
    captured_data = {}

    create_long_term_token = TetTokenService.create_long_term_token

    def wrapper(*args, **kwargs):
        token = create_long_term_token(*args, **kwargs)
        captured_data["token"] = token
        return token

    monkeypatch.setattr(TetTokenService, "create_long_term_token", wrapper)

    return captured_data


def test_login_view_should_return_long_term_token(test_app, capture_token):
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = test_app.post(
        url=LONG_TERM_TOKEN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    assert response.status_code == 200
    assert "user_id" in response.json
    assert "token" in response.json

    # Validate the token captured by monkeypatch
    assert "token" in capture_token
    assert capture_token["token"] == response.json["token"]

    token = response.json["token"]
    assert isinstance(token, str)
    assert len(token) > 0


def test_auth_should_return_access_token(long_term_token, test_app):
    headers = {"x-long-token": long_term_token}
    response = test_app.get(ACCESS_TOKEN_ENDPOINT, headers=headers, status=200)

    assert response.status_code == 200

    assert "x-access-token" in response.headers
    assert response.headers["x-access-token"] is not None


def test_access_token_should_work_to_access_protected_route(long_term_token, test_app):
    headers = {"x-long-token": long_term_token}
    response = test_app.get(ACCESS_TOKEN_ENDPOINT, headers=headers, status=200)
    assert response.status_code == 200

    access_token = response.headers["x-access-token"]
    assert access_token is not None

    headers = {"x-access-token": access_token}
    response = test_app.get(HOME_ROUTE, headers=headers, status=200)

    assert response.status_code == 200
    assert "message" in response.json
    assert response.json["message"] == "Hello, World!"


def test_login_view_should_raise_403_when_identity_not_found_in_the_db(test_app, pyramid_request):
    response = test_app.post(
        url=LONG_TERM_TOKEN_ENDPOINT,
        params=json.dumps({"user_identity": "invalid_user", "password": "wrong_password"}),
        content_type="application/json",
        status=403,
        expect_errors=True,
    )
    assert response.status_code == 403


def test_it_should_store_the_token_in_the_database(capture_token, test_app, pyramid_request):
    project_prefix = pyramid_request.registry.settings["project_prefix"]
    tet_token_service = TetTokenService(request=pyramid_request)
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    response = test_app.post(
        url=LONG_TERM_TOKEN_ENDPOINT,
        params=data,
        content_type="application/json",
        status=200,
    )
    assert response.status_code == 200
    assert "user_id" in response.json
    assert "token" in response.json

    # Validate the token captured by monkeypatch
    assert "token" in capture_token
    assert capture_token["token"] == response.json["token"]

    response_token = response.json["token"]
    assert isinstance(response_token, str)
    assert len(response_token) > 0

    token = tet_token_service.retrieve_and_validate_token(response_token, project_prefix)
    assert token is not None


def test_it_should_fail_to_access_the_protected_route_without_the_access_token(
    test_app,
):
    response = test_app.get(HOME_ROUTE, status=403, expect_errors=True)
    assert response.status_code == 403


def test_it_should_fail_to_access_the_protected_route_with_invalid_access_token(
    test_app,
):
    headers = {
        "x-access-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MzgwNjk5ODd9"
        ".oeTClyh2CDWH1eHJPuxlm8TwR4zzBK4QZkop17fROa"
    }
    pytest.raises(
        InvalidSignatureError,
        test_app.get,
        HOME_ROUTE,
        headers=headers,
        expect_errors=True,
    )
