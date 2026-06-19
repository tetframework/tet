import logging

import structlog
from pyramid.events import subscriber

from tet.security.events import AuthnLoginFail, AuthnLoginSuccess

struct_logger = structlog.get_logger("audit")


def struct_log(event_name: str, description: str, level: int = None, **extra_fields) -> None:
    try:
        struct_logger.log(
            level=level,
            event=event_name,
            description=description,
            **extra_fields,
        )
    except Exception as e:
        struct_logger.exception(
            event="audit_log_error",
            description=f"Failed to log event: {e}",
        )


# Login events
@subscriber(AuthnLoginFail)
def handle_login_failed_event(event: AuthnLoginFail):
    user_identity = event.user_identity
    description = f"User {user_identity} failed to log in."
    struct_log(
        event_name=f"authn_login_fail:{user_identity}",
        description=description,
        level=logging.WARNING,
    )


@subscriber(AuthnLoginSuccess)
def handle_login_success_event(event: AuthnLoginSuccess):
    user_identity = event.user_identity
    description = f"User {user_identity} logged in successfully."
    struct_log(
        event_name=f"authn_login_success:{user_identity}",
        description=description,
        level=logging.INFO,
    )
