import hashlib
import logging
import typing as tp

import requests
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.request import Request
from pyramid_di import RequestScopedBaseService, autowired
from sqlalchemy.orm import Session

from tet.security.config import (
    CookieAttributes,
    PasswordChangeData,
    MIN_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_SCORE,
    KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM,
)
from tet.security.tokens import TetTokenService

logger = logging.getLogger(__name__)


class TetAuthService(RequestScopedBaseService):
    db_session: Session = autowired(Session)
    token_service = autowired(TetTokenService)

    def __init__(self, request: Request):
        super().__init__(request=request)
        self.project_prefix: str = self.registry.tet_auth_project_prefix
        self.long_term_token_cookie_name = self.registry.tet_auth_long_term_token_cookie_name
        self.long_term_token_expiration_mins = (
            self.registry.tet_auth_long_term_token_expiration_mins
        )
        self.user_model: tp.Any = self.registry.tet_auth_user_model
        self.route_prefix: str = self.registry.tet_auth_route_prefix

    @property
    def _cookie_path(self) -> str:
        return f"{self.route_prefix}/"

    def set_cookies(
        self,
        *,
        cookie_attributes: CookieAttributes,
        refresh_token: str,
        **kwargs,
    ):
        if cookie_attributes:
            cookie_attributes.value = refresh_token
            if not cookie_attributes.max_age:
                cookie_attributes.max_age = self.long_term_token_expiration_mins * 60

        cookie_attrs = cookie_attributes or CookieAttributes(
            name=self.long_term_token_cookie_name,
            value=refresh_token,
            max_age=self.long_term_token_expiration_mins * 60,
            path=self._cookie_path,
        )
        self.request.response.set_cookie(
            **cookie_attrs.__dict__,
            **kwargs,
        )

    def delete_cookie(self, *, name: str, path: str = None, **kwargs):
        self.request.response.delete_cookie(
            name=name,
            path=path or self._cookie_path,
            **kwargs,
        )

    def validate_and_create_jwt(self, *, refresh_token: str) -> str:
        try:
            token_from_db = self.token_service.retrieve_and_validate_token(
                token=refresh_token, prefix=self.project_prefix
            )
        except ValueError as e:
            logger.exception(f"Error validating token: {e}")
            self.delete_cookie(name=self.long_term_token_cookie_name)
            raise HTTPUnauthorized() from e

        user_id = getattr(token_from_db, self.token_service.user_id_column)

        return self.token_service.create_short_term_jwt(user_id)

    def verify_password(self, user: tp.Any, password: str) -> bool:
        return user.verify_password(password)

    def is_password_breached(self, password: str) -> bool:
        sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1_hash[:5], sha1_hash[5:]
        url = f"{self.request.registry.settings['pwned_passwords_api_url']}{prefix}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except requests.RequestException:
            logger.warning("Password breach check unavailable")
            return False

        for line in response.text.splitlines():
            hash_suffix, count = line.split(":")
            if hash_suffix == suffix:
                return True
        return False

    @staticmethod
    def assess_password_strength(password: str) -> int:
        strength = 0
        if len(password) > 0:
            strength += 1
        if len(password) >= MIN_PASSWORD_LENGTH:
            strength += 4
        return strength

    def get_current_user(self, user_id: tp.Any) -> tp.Optional[tp.Any]:
        return (
            self.db_session.query(self.user_model)
            .filter(self.user_model.id == user_id)
            .one_or_none()
        )

    def change_password(self, payload: PasswordChangeData, user: tp.Any) -> bool:
        is_valid = self.password_change_validation(payload=payload, user=user)
        user.password = payload.new_password
        self.db_session.flush()
        return is_valid

    def password_change_validation(self, payload: PasswordChangeData, user: tp.Any) -> bool:
        if self.is_password_breached(payload.new_password):
            raise ValueError(
                f"{KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM}.PASSWORD_LEAKED_EASY_TO_GUESS"
            )

        validations = [
            (
                self.assess_password_strength(payload.new_password) >= MIN_SCORE,
                f"{KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM}.PASSWORD_STRENGTH_TOO_WEAK",
            ),
            (
                MIN_PASSWORD_LENGTH <= len(payload.new_password) <= MAX_PASSWORD_LENGTH,
                f"{KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM}.INCORRECT_PASSWORD_LENGTH",
            ),
            (
                self.verify_password(user=user, password=payload.current_password),
                f"{KEY_PREFIX_PROFILE_CHANGE_PASSWORD_FORM}.INVALID_CREDENTIALS",
            ),
        ]
        for condition, error_message in validations:
            if not condition:
                raise ValueError(error_message)
        return True
