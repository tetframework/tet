import pytest
from sqlalchemy import create_engine, text

TARGET_MODULE = "test_authentication.py"
DB_URL = "postgresql+psycopg2://test_tet:test_tet@localhost:5432/test_tet"


def pytest_collection_modifyitems(config, items):
    """
    Pre-filter: split items into those in test_authentication.py and others.

    More detail about this hook https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_collection
    """
    auth_items = [item for item in items if TARGET_MODULE in str(item.fspath)]
    other_items = [item for item in items if TARGET_MODULE not in str(item.fspath)]

    kept_items = other_items + auth_items
    items[:] = kept_items


@pytest.fixture(autouse=True, scope="session")
def _cleanup_mfa_from_previous_runs():
    """Remove MFA methods left over from a previous test run."""
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM multi_factor_authentication_method"))
        conn.commit()
    engine.dispose()
