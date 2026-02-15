TARGET_MODULE = "test_authentication.py"


def pytest_collection_modifyitems(config, items):
    """
    Pre-filter: split items into those in test_authentication.py and others.

    More detail about this hook https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_collection
    """
    auth_items = [item for item in items if TARGET_MODULE in str(item.fspath)]
    other_items = [item for item in items if TARGET_MODULE not in str(item.fspath)]

    kept_items = other_items + auth_items
    items[:] = kept_items
