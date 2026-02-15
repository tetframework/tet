import logging
import typing as tp

from pyramid.httpexceptions import (
    HTTPForbidden,
    HTTPUnauthorized,
    HTTPBadRequest,
    HTTPException,
    HTTPInternalServerError,
)
from pyramid.request import Request
from pyramid.response import Response
from pyramid_di import autowired
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import tet.security.events as security_events
from tet.security.config import (
    CookieAttributes,
    PasswordChangeData,
    AuthLoginResult,
    MultiFactorAuthMethodType,
    DEFAULT_UNAUTHORIZED_MESSAGE,
)
from tet.security.tokens import TetTokenService
from tet.security.auth import TetAuthService
from tet.security.mfa import TetMultiFactorAuthenticationService

logger = logging.getLogger(__name__)


class AuthViews:
    token_service: TetTokenService = autowired(TetTokenService)
    auth_service: TetAuthService = autowired(TetAuthService)
    multi_factor_auth_service: TetMultiFactorAuthenticationService = autowired(
        TetMultiFactorAuthenticationService
    )
    db_session: Session = autowired(Session)

    def __init__(self, request: Request):
        self.request = request
        self.registry = request.registry
        self.response = request.response
        self.project_prefix = self.registry.tet_auth_project_prefix
        self.long_term_token_cookie_name = self.registry.tet_auth_long_term_token_cookie_name
        self.long_term_token_expiration_mins = (
            self.registry.tet_auth_long_term_token_expiration_mins
        )
        self.route_prefix = self.registry.tet_auth_route_prefix
        self.login_callback = self.registry.tet_auth_login_callback
        self.cookie_attributes: tp.Optional[CookieAttributes] = (
            self.registry.tet_auth_cookie_attributes
        )

    def _require_authenticated_userid(self) -> tp.Any:
        user_id = self.request.authenticated_userid
        if user_id is None:
            raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})
        return user_id

    def login(self) -> dict[str, tp.Any]:
        auth_result: AuthLoginResult = self.login_callback(self.request)
        user_id = auth_result.user_id
        user_identity = auth_result.user_identity
        totp_token = auth_result.totp_token
        response_payload: dict[str, tp.Any] = {"success": True}

        try:
            if user_id is None:
                raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})
            refresh_token = self.token_service.create_long_term_token(user_id=user_id, project_prefix=self.project_prefix)
            access_token = self.token_service.create_short_term_jwt(user_id)

            if self.multi_factor_auth_service.is_totp_mfa_enabled(user_id):
                if not totp_token:
                    response_payload[auth_result.mfa_required_key] = True
                    return response_payload

                return self.multi_factor_auth_service.handle_totp_challenge(
                    user_id=user_id, totp_token=totp_token
                )

            self.auth_service.set_cookies(
                cookie_attributes=self.cookie_attributes,
                refresh_token=refresh_token,
            )
            response_payload["access_token"] = access_token
            response_payload["refresh_token"] = refresh_token

            self.registry.notify(
                security_events.AuthnLoginSuccess(
                    request=self.request, user_identity=user_identity
                )
            )
            return response_payload

        except KeyError as e:
            self.registry.notify(
                security_events.AuthnLoginFail(request=self.request, user_identity=user_identity)
            )
            logger.exception(f"Missing required field during login: {str(e)}")
            return HTTPBadRequest(json_body={"message": "Missing required field."})
        except HTTPException as e:
            self.registry.notify(
                security_events.AuthnLoginFail(request=self.request, user_identity=user_identity)
            )
            return e
        except Exception as e:
            logger.exception(f"Error during login: {str(e)}")
            self.registry.notify(
                security_events.AuthnLoginFail(request=self.request, user_identity=user_identity)
            )
            return HTTPInternalServerError(json_body={"message": "Login failed"})

    def mfa_verify(self) -> dict:
        """
        Verifies the TOTP code for the currently authenticated user.

        Raises:
            HTTPUnauthorized: If no authenticated user ID is found in the request.

        Returns:
            dict: Result of the TOTP verification for the user.
        """
        user_id = self._require_authenticated_userid()
        payload = self.request.json_body
        token = payload["token"]
        setup_key = payload["setup_key"]
        try:
            return self.multi_factor_auth_service.handle_totp_verify(
                user_id=user_id, token=token, setup_key=setup_key
            )
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.exception(f"Error verifying MFA: {e}")
            raise HTTPInternalServerError(
                json_body={"message": "Failed to verify MFA"}
            ) from e

    def refresh_token(self) -> tp.Union[tp.Dict[str, tp.Any], HTTPUnauthorized]:
        refresh_token = self.request.cookies.get(self.long_term_token_cookie_name)
        if not refresh_token:
            try:
                refresh_token = self.request.json_body.get("refresh_token")
            except Exception:
                pass
        if not refresh_token:
            raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})

        access_token = self.auth_service.validate_and_create_jwt(
            refresh_token=refresh_token
        )
        return {"success": True, "access_token": access_token}

    def change_password(self):
        user_id = None
        try:
            user_id = self._require_authenticated_userid()
            data = self.request.json_body
            payload = PasswordChangeData(
                current_password=data["currentPassword"],
                new_password=data["newPassword"],
            )
            user = self.auth_service.get_current_user(user_id)
            is_valid = self.auth_service.change_password(payload=payload, user=user)
            self.token_service.delete_other_tokens(user=user)
            self.registry.notify(
                security_events.AuthnPasswordChange(
                    request=self.request, authenticated_userid=user_id
                )
            )
            return {"success": is_valid}
        except ValueError as e:
            self.registry.notify(
                security_events.AuthnPasswordChangeFail(
                    request=self.request, authenticated_userid=user_id
                )
            )
            logger.error(f"Error while validating password change: {e}")
            return HTTPForbidden(
                json_body={"message": "Invalid password change request", "success": False}
            )
        except HTTPException as e:
            self.registry.notify(
                security_events.AuthnPasswordChangeFail(
                    request=self.request, authenticated_userid=user_id
                )
            )
            return e
        except Exception as e:
            logger.exception(f"Error changing password: {e}")
            self.registry.notify(
                security_events.AuthnPasswordChangeFail(
                    request=self.request, authenticated_userid=user_id
                )
            )
            return HTTPForbidden(
                json_body={"message": "Failed to change password", "success": False}
            )

    def logout(self) -> tp.Union[tp.Dict[str, tp.Any], HTTPForbidden, Response]:
        user_id = None
        try:
            user_id = self._require_authenticated_userid()
            user = self.auth_service.get_current_user(user_id=user_id)
            if not user:
                raise HTTPUnauthorized(json_body={"message": DEFAULT_UNAUTHORIZED_MESSAGE})
            self.token_service.delete_token(user=user)
            self.auth_service.delete_cookie(name=self.long_term_token_cookie_name)
            self.registry.notify(
                security_events.AuthnCurrentRefreshTokenRevoked(
                    request=self.request, authenticated_userid=user_id
                )
            )
            self.registry.notify(
                security_events.AuthnLogoutSuccess(
                    request=self.request, user_id=user_id
                )
            )
            return {"success": True}
        except HTTPException as e:
            self.registry.notify(
                security_events.AuthnLogoutFail(
                    request=self.request, user_id=user_id
                )
            )
            return e
        except SQLAlchemyError as e:
            logger.exception(f"Database error during logout: {e}")
            self.registry.notify(
                security_events.AuthnCurrentRefreshTokenRevokeFail(
                    request=self.request, authenticated_userid=user_id
                )
            )
            return HTTPForbidden(json_body={"message": "Failed to logout", "success": False})
        except Exception as e:
            logger.exception(f"Error logging out: {e}")
            self.registry.notify(
                security_events.AuthnLogoutFail(
                    request=self.request, user_id=user_id
                )
            )
            return HTTPForbidden(json_body={"message": "Failed to logout", "success": False})

    def disable_mfa_method(self):
        user_id = None
        payload = self.request.json_body
        mfa_method_type = MultiFactorAuthMethodType(payload["method_type"])
        try:
            user_id = self._require_authenticated_userid()
            self.multi_factor_auth_service.disable_method(
                user_id=user_id, method_type=mfa_method_type
            )
            self.registry.notify(
                security_events.AuthnMfaMethodDisabled(
                    request=self.request,
                    authenticated_userid=user_id,
                    method=mfa_method_type.value,
                )
            )
            return {"success": True}
        except HTTPException as e:
            self.registry.notify(
                security_events.AuthnMfaMethodDisableFail(
                    request=self.request,
                    authenticated_userid=user_id,
                    method=mfa_method_type.value,
                )
            )
            return e
        except Exception as e:
            logger.exception(f"Error disabling MFA method: {e}")
            self.registry.notify(
                security_events.AuthnMfaMethodDisableFail(
                    request=self.request,
                    authenticated_userid=user_id,
                    method=mfa_method_type.value,
                )
            )
            return HTTPForbidden(json_body={"message": "Failed to disable MFA method"})

    def revoke_other_tokens(self):
        user_id = None
        payload = self.request.json_body
        try:
            user_id = self._require_authenticated_userid()
            user = self.auth_service.get_current_user(user_id=user_id)
            if user is None:
                raise HTTPUnauthorized(json_body={"message": "Unauthorized", "success": False})

            if not self.auth_service.verify_password(
                user=user, password=payload.get("password", "")
            ):
                raise HTTPUnauthorized(json_body={"message": "Unauthorized", "success": False})

            self.token_service.delete_other_tokens(user=user)
            self.registry.notify(
                security_events.AuthnRefreshTokensRevoked(
                    request=self.request,
                    authenticated_userid=user_id,
                )
            )
            return {"success": True}
        except HTTPException as e:
            self.registry.notify(
                security_events.AuthnRefreshTokenRevokeFail(
                    request=self.request,
                    authenticated_userid=user_id,
                )
            )
            return e
        except Exception as e:
            logger.exception(f"Error revoking other tokens: {e}")
            self.registry.notify(
                security_events.AuthnRefreshTokenRevokeFail(
                    request=self.request,
                    authenticated_userid=user_id,
                )
            )
            return HTTPForbidden(
                json_body={"message": "Failed to revoke other tokens", "success": False}
            )

    def get_mfa_methods(self) -> dict[str, tp.List[tp.Any]]:
        user_id = self._require_authenticated_userid()
        try:
            mfa_methods: tp.List[tp.Any] = (
                self.multi_factor_auth_service.get_active_methods_by_user_id(user_id=user_id)
            )
            return {"method_types": [mfa_method.method_type.value for mfa_method in mfa_methods]}
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.exception(f"Error retrieving MFA methods: {e}")
            raise HTTPInternalServerError(
                json_body={"message": "Failed to retrieve MFA methods"}
            ) from e

    def generate_mfa_totp(self):
        user_id = self._require_authenticated_userid()
        user = self.auth_service.get_current_user(user_id=user_id)
        payload = self.request.json_body
        try:
            if payload["method_type"] == MultiFactorAuthMethodType.TOTP.value:
                return self.multi_factor_auth_service.handle_totp_setup(
                    user=user, project_prefix=self.project_prefix
                )
            return None
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.exception(f"Error generating TOTP method: {e}")
            raise HTTPInternalServerError(
                json_body={"message": "Failed to generate TOTP method"}
            ) from e
