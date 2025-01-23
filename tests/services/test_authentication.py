import pytest
from sqlalchemy.orm import Session
from webtest import TestApp

from tests.conftest import pyramid_app
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
    response = test_app.post(LONG_TERM_TOKEN_ENDPOINT, status=200)

    assert response.status_code == 200
    assert "user_id" in response.json
    assert "token" in response.json

    # Validate the token captured by monkeypatch
    assert "token" in capture_token
    assert capture_token["token"] == response.json["token"]

    token = response.json['token']
    assert isinstance(token, str)
    assert len(token) > 0
    return token


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


def test_login_view_should_return_long_term_token(long_term_token):
    assert long_term_token is not None
    assert len(long_term_token) > 0


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

# Test it should stored the token in the database
# Test it should failed to access the protected route without the access token
# Test it should failed to access the protected route with invalid access token
