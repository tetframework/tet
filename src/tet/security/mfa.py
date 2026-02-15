import base64
import io
import logging
import typing as tp

import pyotp
import qrcode
import qrcode.image.svg
from pyramid.httpexceptions import (
    HTTPForbidden,
    HTTPBadRequest,
    HTTPException,
    HTTPInternalServerError,
)
from pyramid.request import Request
from pyramid_di import RequestScopedBaseService, autowired
from sqlalchemy.orm import Session

import tet.security.events as security_events
from tet.security.config import (
    CookieAttributes,
    TOTPData,
    MultiFactorAuthMethodType,
)
from tet.security.tokens import TetTokenService
from tet.security.auth import TetAuthService

logger = logging.getLogger(__name__)


class TetMultiFactorAuthenticationService(RequestScopedBaseService):
    session: Session = autowired(Session)
    token_service: TetTokenService = autowired(TetTokenService)
    auth_service: TetAuthService = autowired(TetAuthService)

    def __init__(self, request: Request):
        super().__init__(request=request)
        self.tet_multi_factor_auth_method_model: tp.Any = (
            self.registry.tet_multi_factor_auth_method_model
        )
        self.project_prefix: str = self.registry.tet_auth_project_prefix
        self.long_term_token_cookie_name = self.registry.tet_auth_long_term_token_cookie_name
        self.long_term_token_expiration_mins = (
            self.registry.tet_auth_long_term_token_expiration_mins
        )

    def create_method(self, *, method_type: MultiFactorAuthMethodType, user_id: tp.Any, data: dict):
        """
        Create a new multifactor authentication method for a user.
        """
        new_mfa_method = self.tet_multi_factor_auth_method_model(
            method_type=method_type, user_id=user_id, data=data
        )
        self.session.add(new_mfa_method)
        self.session.flush()
        return new_mfa_method

    def disable_method(self, user_id: tp.Any, method_type: MultiFactorAuthMethodType):
        """
        Disable a multifactor authentication method for a user.
        """
        self.session.query(self.tet_multi_factor_auth_method_model).filter_by(
            user_id=user_id, method_type=method_type.value
        ).update({"is_active": False, "verified": False, "data": {}})

    @staticmethod
    def verify_totp(secret: tp.Any, token: tp.Any) -> bool:
        """
        Verify a one-time password for multifactor authentication.
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(token)

    def get_method(
        self,
        *,
        user_id: tp.Any,
        method_type: MultiFactorAuthMethodType,
        is_active: bool = True,
        verified: bool = True,
    ):
        """
        Retrieve a multifactor authentication method for a user.
        """
        conditions = [
            self.tet_multi_factor_auth_method_model.user_id == user_id,
            self.tet_multi_factor_auth_method_model.method_type == method_type,
        ]
        if is_active:
            conditions.append(self.tet_multi_factor_auth_method_model.is_active == is_active)
        if verified:
            conditions.append(self.tet_multi_factor_auth_method_model.verified == verified)
        return (
            self.session.query(self.tet_multi_factor_auth_method_model)
            .filter(*conditions)
            .one_or_none()
        )

    def get_active_methods_by_user_id(self, *, user_id: tp.Any):
        """
        Retrieve all multifactor authentication methods by user id.
        """
        return (
            self.session.query(self.tet_multi_factor_auth_method_model)
            .filter_by(user_id=user_id, is_active=True, verified=True)
            .all()
        )

    def is_totp_mfa_enabled(self, user_id: tp.Any = None) -> bool:
        """
        Check if multifactor authentication is enabled for the user.
        """
        return (
            self.session.query(self.tet_multi_factor_auth_method_model)
            .filter(
                self.tet_multi_factor_auth_method_model.user_id == user_id,
                self.tet_multi_factor_auth_method_model.is_active,
                self.tet_multi_factor_auth_method_model.verified,
            )
            .count()
            > 0
        )

    def handle_totp_verify(self, *, user_id: tp.Any, token: tp.Any, setup_key: tp.Any) -> dict:
        try:
            totp_mfa_method = self.get_method(
                user_id=user_id,
                method_type=MultiFactorAuthMethodType.TOTP,
                is_active=False,
                verified=False,
            )
            if not totp_mfa_method:
                raise HTTPForbidden(
                    json_body={"message": "Two-factor authentication method not found."}
                )

            if not setup_key:
                raise HTTPBadRequest(json_body={"message": "Missing TOTP secret."})

            is_valid = self.verify_totp(secret=setup_key, token=token)

            if not is_valid:
                raise HTTPForbidden(json_body={"message": "Two-factor authentication failed."})

            totp_mfa_method.mark_used()

            data = TOTPData(
                secret=setup_key,
                issuer=self.project_prefix,
            )
            totp_mfa_method.verified = True
            totp_mfa_method.is_active = True
            totp_mfa_method.data = data.to_dict()
            return {"success": is_valid}
        except KeyError as e:
            logger.exception(f"details {str(e)}")
            raise HTTPBadRequest(json_body={"message": "Missing required field."}) from e
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"details {str(e)}")
            raise HTTPInternalServerError(json_body={"message": "TOTP verification failed."}) from e

    def handle_totp_challenge(
        self,
        *,
        user_id: tp.Any,
        totp_token: str = None,
        cookie_attributes: CookieAttributes = None,
    ) -> dict[str, tp.Any]:
        totp_mfa_method = self.get_method(
            user_id=user_id,
            method_type=MultiFactorAuthMethodType.TOTP,
            is_active=True,
            verified=True,
        )
        if not totp_mfa_method:
            raise HTTPForbidden(
                json_body={"message": "Two-factor authentication method not found."}
            )

        secret = totp_mfa_method.data.get("secret")

        if not secret:
            raise HTTPBadRequest(json_body={"message": "Missing TOTP secret."})

        is_valid = self.verify_totp(secret=secret, token=totp_token)

        if not is_valid:
            raise HTTPForbidden(json_body={"message": "Two-factor authentication failed."})

        totp_mfa_method.mark_used()

        refresh_token = self.token_service.create_long_term_token(user_id=user_id, project_prefix=self.project_prefix)
        access_token = self.token_service.create_short_term_jwt(user_id)

        self.auth_service.set_cookies(
            cookie_attributes=cookie_attributes,
            refresh_token=refresh_token,
        )
        self.registry.notify(
            security_events.AuthnLoginSuccess(
                request=self.request,
                user_identity=self.request.json_body.get("user_identity", user_id),
            )
        )
        return {"success": is_valid, "access_token": access_token, "refresh_token": refresh_token}

    @staticmethod
    def _create_totp_data(issuer: str) -> TOTPData:
        secret = pyotp.random_base32()
        return TOTPData(
            secret=secret,
            issuer=issuer,
        )

    @staticmethod
    def generate_qr_img(user: tp.Any, mfa_secret: str, data: tp.Union[TOTPData]) -> str:
        otp_uri = pyotp.totp.TOTP(mfa_secret).provisioning_uri(
            name=user.display_name, issuer_name=data.issuer
        )
        factory = qrcode.image.svg.SvgImage
        qr = qrcode.QRCode(box_size=15, border=4)
        qr.add_data(otp_uri)
        qr.make(fit=True)
        img = qr.make_image(image_factory=factory)
        buffer = io.BytesIO()
        img.save(buffer)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def handle_totp_setup(self, *, user: tp.Any, project_prefix: str) -> dict:
        try:
            data: TOTPData = self._create_totp_data(issuer=project_prefix)
            existing_method = self.get_method(
                user_id=user.id,
                method_type=MultiFactorAuthMethodType.TOTP,
                is_active=False,
                verified=False,
            )
            if not existing_method:
                self.create_method(
                    method_type=MultiFactorAuthMethodType.TOTP,
                    user_id=user.id,
                    data=data.to_dict(),
                )
                self.request.registry.notify(
                    security_events.AuthnMfaMethodCreated(
                        request=self.request,
                        authenticated_userid=user.id,
                        method=MultiFactorAuthMethodType.TOTP.value,
                    )
                )
            mfa_secret = data.secret
            img_str = self.generate_qr_img(user=user, mfa_secret=mfa_secret, data=data)
            return {"secret": mfa_secret, "qr_code": f"data:image/svg+xml;base64,{img_str}"}
        except Exception as e:
            logger.exception(e)
            return dict(success=False, message="Error generating TOTP method")
