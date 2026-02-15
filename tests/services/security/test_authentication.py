import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import jwt as pyjwt
import pytest
import requests as req_lib
from pyramid.httpexceptions import HTTPUnauthorized
from sqlalchemy.orm import Session
from webtest import TestApp

from tests.models.accounts import User
from tests.services.constants import LOGIN_ENDPOINT, ACCESS_TOKEN_HEADER_NAME, HOME_ROUTE
from tests.services.utils.authentication import get_cookie
from tet.security.auth import TetAuthService
from tet.security.config import PasswordChangeData
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
    user = db_session.query(User).filter(User.email == "exampple2@invalid.invalid").one_or_none()
    if user:
        # Always reset password to known state
        user.password = "1234@abcd"
        db_session.flush()
        return user

    user = User(email="exampple2@invalid.invalid", name="example2", is_admin=True)
    user.password = "1234@abcd"
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
    auth_service = TetAuthService(request=pyramid_request)
    pyramid_request.registry.settings["pwned_passwords_api_url"] = "https://api.pwnedpasswords.com/range/"

    with patch("tet.security.auth.requests.get", side_effect=req_lib.ConnectionError("timeout")):
        result = auth_service.is_password_breached("test_password_123")
    assert result is False


# --- Token validation edge cases ---


def test_retrieve_token_with_invalid_prefix(token_service, pyramid_request):
    """Token with wrong prefix should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid token prefix"):
        token_service.retrieve_and_validate_token(token="WRONG_PREFIX_ABC123", prefix="tet")


def test_retrieve_token_not_found_in_db(token_service, capture_token, pyramid_request, db_session):
    """Token ID not in DB should raise ValueError."""
    # Create a valid-looking token with a non-existent ID
    import secrets, hashlib
    from tet.security.config import TOKEN_ID_BYTE_LENGTH

    prefix = pyramid_request.registry.settings["project_prefix"]
    fake_id = (999999).to_bytes(TOKEN_ID_BYTE_LENGTH, "little")
    fake_secret = secrets.token_bytes(32)
    payload = fake_id + fake_secret
    fake_token = f"{prefix}{payload.hex().upper()}"

    with pytest.raises(ValueError, match="Token not found"):
        token_service.retrieve_and_validate_token(token=fake_token, prefix=prefix)


def test_retrieve_token_with_wrong_secret(token_service, capture_token, pyramid_request, db_session):
    """Token with wrong secret should raise ValueError."""
    import secrets
    from tet.security.config import TOKEN_ID_BYTE_LENGTH

    prefix = pyramid_request.registry.settings["project_prefix"]
    user = create_user(db_session)

    # Create a real token to get a valid token ID
    real_token = token_service.create_long_term_token(user_id=user.id, project_prefix=prefix)
    payload_hex = real_token[len(prefix):]
    payload_bytes = bytes.fromhex(payload_hex)
    token_id_bytes = payload_bytes[:TOKEN_ID_BYTE_LENGTH]

    # Replace the secret with garbage
    wrong_secret = secrets.token_bytes(32)
    tampered_payload = token_id_bytes + wrong_secret
    tampered_token = f"{prefix}{tampered_payload.hex().upper()}"

    with pytest.raises(ValueError, match="Invalid token"):
        token_service.retrieve_and_validate_token(token=tampered_token, prefix=prefix)


def test_create_short_term_jwt_requires_user_id(token_service):
    """create_short_term_jwt should raise ValueError when user_id is falsy."""
    with pytest.raises(ValueError, match="User ID is required"):
        token_service.create_short_term_jwt(None)


# --- Auth service tests ---


@pytest.fixture()
def auth_service(pyramid_request):
    return pyramid_request.find_service(TetAuthService)


def test_validate_and_create_jwt(auth_service, capture_token, pyramid_test_app, pyramid_request, db_session):
    """validate_and_create_jwt should return a valid JWT from a refresh token."""
    create_user(db_session)
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    login_response = pyramid_test_app.post(
        LOGIN_ENDPOINT, params=data, content_type="application/json", status=200,
    )
    refresh_token = login_response.json["refresh_token"]
    access_token = auth_service.validate_and_create_jwt(refresh_token=refresh_token)
    assert access_token is not None
    assert isinstance(access_token, str)


def test_validate_and_create_jwt_invalid_token_raises_401(auth_service):
    """Invalid refresh token should raise HTTPUnauthorized."""
    with pytest.raises(HTTPUnauthorized):
        auth_service.validate_and_create_jwt(refresh_token="tet_INVALID_TOKEN_DATA")


def test_verify_password(auth_service, db_session):
    """verify_password should delegate to user model."""
    user = create_user(db_session)
    # The test User model uses validate_password (from UserPasswordMixin),
    # but TetAuthService.verify_password calls user.verify_password.
    # Downstream apps must provide verify_password on their user model.
    user.verify_password = user.validate_password
    assert auth_service.verify_password(user=user, password="1234@abcd") is True
    assert auth_service.verify_password(user=user, password="wrong") is False


def test_get_current_user(auth_service, db_session):
    """get_current_user should return the user or None."""
    user = create_user(db_session)
    found = auth_service.get_current_user(user.id)
    assert found is not None
    assert found.id == user.id

    not_found = auth_service.get_current_user(999999)
    assert not_found is None


def test_assess_password_strength():
    """Password strength scoring."""
    assert TetAuthService.assess_password_strength("") == 0
    assert TetAuthService.assess_password_strength("short") == 1
    assert TetAuthService.assess_password_strength("a_long_enough_pw") == 5


def test_is_password_breached_returns_true_when_found(pyramid_request):
    """Should return True when password hash suffix is found in API response."""
    auth_service = TetAuthService(request=pyramid_request)
    pyramid_request.registry.settings["pwned_passwords_api_url"] = "https://api.pwnedpasswords.com/range/"

    # SHA1 of "password" starts with 5BAA6 -> suffix is 1E4C9B93F3F0682250B6CF8331B7EE68FD8
    import hashlib
    sha1 = hashlib.sha1(b"password").hexdigest().upper()
    suffix = sha1[5:]

    mock_response = MagicMock()
    mock_response.text = f"{suffix}:12345\nOTHERHASH:1"
    mock_response.raise_for_status = MagicMock()

    with patch("tet.security.auth.requests.get", return_value=mock_response):
        assert auth_service.is_password_breached("password") is True


def test_is_password_breached_returns_false_when_not_found(pyramid_request):
    """Should return False when password hash suffix is not in API response."""
    auth_service = TetAuthService(request=pyramid_request)
    pyramid_request.registry.settings["pwned_passwords_api_url"] = "https://api.pwnedpasswords.com/range/"

    mock_response = MagicMock()
    mock_response.text = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0:1\nBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB0:2"
    mock_response.raise_for_status = MagicMock()

    with patch("tet.security.auth.requests.get", return_value=mock_response):
        assert auth_service.is_password_breached("test_password_unique_42") is False


def test_change_password_success(auth_service, db_session):
    """Successful password change."""
    user = create_user(db_session)
    user.verify_password = user.validate_password
    payload = PasswordChangeData(current_password="1234@abcd", new_password="new_secure_password_123")

    with patch.object(auth_service, "is_password_breached", return_value=False):
        result = auth_service.change_password(payload=payload, user=user)
    assert result is True


def test_change_password_wrong_current_password(auth_service, db_session):
    """Wrong current password should raise ValueError."""
    user = create_user(db_session)
    user.verify_password = user.validate_password
    payload = PasswordChangeData(current_password="wrong_password", new_password="new_secure_password_123")

    with patch.object(auth_service, "is_password_breached", return_value=False):
        with pytest.raises(ValueError, match="INVALID_CREDENTIALS"):
            auth_service.change_password(payload=payload, user=user)


def test_change_password_too_short(auth_service, db_session):
    """Password shorter than MIN_PASSWORD_LENGTH should fail validation."""
    user = create_user(db_session)
    user.verify_password = user.validate_password
    payload = PasswordChangeData(current_password="1234@abcd", new_password="short")

    with patch.object(auth_service, "is_password_breached", return_value=False):
        with pytest.raises(ValueError, match="PASSWORD_STRENGTH_TOO_WEAK|INCORRECT_PASSWORD_LENGTH"):
            auth_service.change_password(payload=payload, user=user)


def test_change_password_breached(auth_service, db_session):
    """Breached password should raise ValueError."""
    user = create_user(db_session)
    payload = PasswordChangeData(current_password="1234@abcd", new_password="new_secure_password_123")

    with patch.object(auth_service, "is_password_breached", return_value=True):
        with pytest.raises(ValueError, match="PASSWORD_LEAKED"):
            auth_service.change_password(payload=payload, user=user)


# --- View endpoint integration tests ---


def _set_refresh_cookie(test_app, refresh_token, cookie_name="refresh-token"):
    """Manually set the refresh token cookie to work around webtest domain matching."""
    test_app.set_cookie(cookie_name, refresh_token)


def test_refresh_token_from_cookie(pyramid_test_app, capture_token, pyramid_request):
    """Refresh token in cookie should work for token refresh."""
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    login_resp = pyramid_test_app.post(
        LOGIN_ENDPOINT, params=data, content_type="application/json", status=200,
    )
    refresh_token = login_resp.json["refresh_token"]

    # Webtest has domain matching issues with localhost, so set cookie manually
    pyramid_test_app.cookiejar.clear()
    _set_refresh_cookie(pyramid_test_app, refresh_token)

    response = pyramid_test_app.post(
        "/api/v1/auth/token/refresh",
        params=json.dumps({}),
        content_type="application/json",
        status=200,
    )
    assert response.json["success"] is True
    assert "access_token" in response.json


def test_login_mfa_required_returns_mfa_flag(pyramid_test_app, capture_token, pyramid_request, db_session):
    """When MFA is enabled and no TOTP token provided, should return mfa_required."""
    create_user(db_session)
    from tet.security.mfa import TetMultiFactorAuthenticationService

    with patch.object(TetMultiFactorAuthenticationService, "is_totp_mfa_enabled", return_value=True):
        data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
        response = pyramid_test_app.post(
            LOGIN_ENDPOINT, params=data, content_type="application/json", status=200,
        )
    assert response.json["success"] is True
    assert response.json.get("mfa_required") is True
    assert "access_token" not in response.json


def test_logout_endpoint(pyramid_test_app, capture_token, pyramid_request, db_session):
    """Logout should succeed for an authenticated user."""
    create_user(db_session)
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    login_resp = pyramid_test_app.post(
        LOGIN_ENDPOINT, params=data, content_type="application/json", status=200,
    )
    access_token = login_resp.json["access_token"]
    refresh_token = login_resp.json["refresh_token"]

    # Set cookie manually for webtest domain compatibility
    _set_refresh_cookie(pyramid_test_app, refresh_token)

    response = pyramid_test_app.post(
        "/api/v1/auth/logout",
        headers={ACCESS_TOKEN_HEADER_NAME: f"Bearer {access_token}"},
        content_type="application/json",
        status=200,
    )
    assert response.json["success"] is True


def test_change_password_endpoint(pyramid_test_app, capture_token, pyramid_request, db_session):
    """Change password via HTTP endpoint."""
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    login_resp = pyramid_test_app.post(
        LOGIN_ENDPOINT, params=data, content_type="application/json", status=200,
    )
    access_token = login_resp.json["access_token"]
    refresh_token = login_resp.json["refresh_token"]
    _set_refresh_cookie(pyramid_test_app, refresh_token)

    # Mock change_password to avoid actual DB mutation (unit-tested separately above)
    with patch.object(TetAuthService, "change_password", return_value=True), \
         patch.object(TetTokenService, "delete_other_tokens"):
        response = pyramid_test_app.post(
            "/api/v1/auth/users/me/password",
            params=json.dumps({
                "currentPassword": "1234@abcd",
                "newPassword": "new_secure_password_123",
            }),
            headers={ACCESS_TOKEN_HEADER_NAME: f"Bearer {access_token}"},
            content_type="application/json",
            status=200,
        )
    assert response.json["success"] is True


def test_change_password_endpoint_wrong_current(pyramid_test_app, capture_token, pyramid_request, db_session):
    """Change password with wrong current password should return 403."""
    data = json.dumps({"user_identity": "exampple2@invalid.invalid", "password": "1234@abcd"})
    login_resp = pyramid_test_app.post(
        LOGIN_ENDPOINT, params=data, content_type="application/json", status=200,
    )
    access_token = login_resp.json["access_token"]
    refresh_token = login_resp.json["refresh_token"]
    _set_refresh_cookie(pyramid_test_app, refresh_token)

    with patch.object(TetAuthService, "change_password", side_effect=ValueError("INVALID_CREDENTIALS")):
        response = pyramid_test_app.post(
            "/api/v1/auth/users/me/password",
            params=json.dumps({
                "currentPassword": "wrong_password",
                "newPassword": "new_secure_password_123",
            }),
            headers={ACCESS_TOKEN_HEADER_NAME: f"Bearer {access_token}"},
            content_type="application/json",
            status=403,
            expect_errors=True,
        )
    assert response.status_code == 403
