import json
import logging
import typing as tp

import pytest
from pyramid.request import Request
from pyramid.response import Response
from pyramid.security import Allow, Authenticated, Everyone, Deny
from pyramid.testing import setUp, tearDown
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tests.models.accounts import Base, Token, User, MultiFactorAuthenticationMethod
from tet.config import Configurator as tetConfigurator
from tet.security.authentication import (
    TokenAuthenticationPolicy,
    JWTCookieAuthenticationPolicy,
    AuthLoginResult,
)
from tet.view import view_config

DB_NAME = "test_tet"
DB_URL = f"postgresql+psycopg2://test_tet:test_tet@localhost:5432/{DB_NAME}"

logger = logging.getLogger(__name__)


def create_test_database():
    # TODO: create the DB, but for now on we assume it must exists
    pass


@pytest.fixture()
def database():
    create_test_database()
    yield
    # could drop the db here, but it's probably not necessary


@pytest.fixture()
def db_engine(database):
    engine = create_engine(DB_URL)
    Base.metadata.create_all(engine)
    yield engine
    # TODO: Dropping all entities will disrupt the saving of tokens in the security/authentication module.
    #  Investigate the workflow and resolve the issue.
    # Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def transaction_manager(pyramid_request):
    return pyramid_request.tm


@pytest.fixture()
def db_session(db_engine, pyramid_request, transaction_manager):
    with transaction_manager:
        session = pyramid_request.find_service(Session)
        yield session


def login_callback(request: Request) -> AuthLoginResult:
    """This is just an example of a login callback. It should be defined by the pyramid app."""
    if not request.content_length:
        return AuthLoginResult(user_id=None)

    db_session = request.find_service(Session)

    payload = request.json_body
    user_identity = payload.get("user_identity")
    totp_token = payload.get("totp_token")

    if not user_identity:
        return AuthLoginResult(user_id=None)

    user: User = db_session.query(User).filter(User.email == user_identity).one_or_none()
    if not user or not user.validate_password(payload.get("password", "")):
        return AuthLoginResult(
            user_id=None,
            user_identity=user_identity,
        )

    return AuthLoginResult(
        user_id=user.id,
        user_identity=user_identity,
        totp_token=totp_token,
    )


def jwk_resolver(request: Request) -> str:
    """Get it from the settings or elsewhere"""
    return request.registry.settings["tet.security.authentication.secret"]


@pytest.fixture()
def pyramid_request(pyramid_app, db_engine):
    with pyramid_app.request_context({}) as request:
        setUp(registry=request.registry, request=request)
        yield request
    tearDown()


class RootFactory(object):
    __acl__ = [
        (Allow, Authenticated, "view"),
        (Allow, "group:editors", "edit"),
        (Allow, Everyone, "login"),
        (Deny, Everyone, "delete"),
    ]

    def __init__(self, request):
        self.request = request


@pytest.fixture()
def pyramid_config(db_engine):
    """Fixture to create and configure a Pyramid application."""
    settings = {
        "sqlalchemy.url": DB_URL,
        "project_prefix": "tet",
        "pyramid.includes": ["pyramid_tm"],
        "tet.security.authentication.secret": "secret",
    }
    with tetConfigurator() as config:
        config.add_settings(settings)
        config.include("tet.sqlalchemy.simple")
        config.include("pyramid_tm")
        config.include("pyramid_di")
        config.setup_sqlalchemy(engine=db_engine)
        config.set_root_factory(RootFactory)
        config.include("tet.security.authentication", route_prefix="/api/v1/auth")
    yield config


JWT_AUTH = "TOKEN_AUTH"
JWT_COOKIE_AUTH = "JWT_COOKIE_AUTH"


@pytest.fixture(
    params=[
        pytest.param({"security_policy": TokenAuthenticationPolicy}, id=JWT_AUTH),
        pytest.param({"security_policy": JWTCookieAuthenticationPolicy}, id=JWT_COOKIE_AUTH),
    ]
)
def security_policy(request):
    return request.param["security_policy"]


@view_config(route_name="home", renderer="json", permission="view")
def home_view(request: Request):
    response: Response = request.response
    response.text = json.dumps({"message": "Hello, World!"})
    response.content_type = "application/json"
    return response


@pytest.fixture()
def pyramid_app(security_policy, pyramid_config):
    pyramid_config.set_token_authentication(
        long_term_token_model=Token,
        project_prefix=pyramid_config.registry.settings["project_prefix"],
        login_callback=login_callback,
        jwk_resolver=jwk_resolver,
        security_policy=security_policy(),
        user_model=User,
        multi_factor_auth_method_model=MultiFactorAuthenticationMethod,
    )
    pyramid_config.add_route("home", "/")
    pyramid_config.add_view(
        home_view,
        route_name="home",
        renderer="json",
        permission="view",
    )
    pyramid_config.scan("tests.services.security.subscribers.auth_subscribers")
    app = pyramid_config.make_wsgi_app()
    yield app
