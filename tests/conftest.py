import logging
from functools import wraps

import pytest
from pyramid.httpexceptions import HTTPForbidden
from pyramid.request import Request
from pyramid.security import Allow, Authenticated, Everyone, Deny
from pyramid.testing import setUp, tearDown
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import Session

from tests.models.accounts import Base, Token, User
from tet.config import Configurator as tetConfigurator

DB_NAME = "test_tet"
DB_URL = f"postgresql:///{DB_NAME}"

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


# don't actually print the logger for this callback
def login_callback(request: Request) -> User.id:
    """This is just an example of a login callback. It should be defined by the pyramid app."""
    db_session = request.find_service(Session)
    payload = request.json_body
    # user_identity here could be an email, or username
    user_identity = payload['user_identity']
    user = (db_session.query(User)
            .filter(or_(User.email == user_identity,
                        User.name == user_identity))
            .first())
    if not user:
        return None
    return user.id


def secret_callback(request: Request) -> str:
    """Get it from the settings or elsewhere"""
    return request.registry.settings['tet.security.authentication.secret']


@pytest.fixture()
def pyramid_request(pyramid_app, db_engine):
    with pyramid_app.request_context({}) as request:
        setUp(registry=request.registry, request=request)
        yield request
    tearDown()


class RootFactory(object):
    __acl__ = [
        (Allow, Authenticated, 'view'),
        (Allow, 'group:editors', 'edit'),
        (Allow, Everyone, 'login'),
        (Deny, Everyone, 'delete')
    ]

    def __init__(self, request):
        self.request = request


@pytest.fixture()
def pyramid_app(db_engine):
    """Fixture to create and configure a Pyramid application."""
    settings = {
        'sqlalchemy.url': DB_URL,
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
        config.tet_configure_authentication_token(
            token_model=Token,
            project_prefix=config.registry.settings['project_prefix'],
            login_callback=login_callback,
            secret_callback=secret_callback,
        )
        config.add_route('home', '/')
        config.add_view(lambda request: {'message': 'Hello, World!'}, route_name='home', renderer='json')
        app = config.make_wsgi_app()
    yield app
