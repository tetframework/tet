from tet.security.authentication import JWTCookieAuthenticationPolicy, TokenAuthenticationPolicy

TARGET_MODULE = "test_authentication.py"
PYRAMID_TEST_APP = "pyramid_test_app"
PYRAMID_TEST_APP_WITH_JWT_COOKIE_POLICY = "pyramid_test_app_with_jwt_cookie_policy"
SECURITY_POLICY = "security_policy"


def pytest_collection_modifyitems(config, items):
    """
    Pre-filter: split items into those in test_authentication.py and others.
    Filter: remove items that require a security policy that is not TokenAuthenticationPolicy.

    More detail about this hook https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest.hookspec.pytest_collection
    """
    auth_items = [item for item in items if TARGET_MODULE in str(item.fspath)]
    other_items = [item for item in items if TARGET_MODULE not in str(item.fspath)]

    deselected_items = []
    kept_auth_items = []
    for item in auth_items:
        if hasattr(item, "callspec") and SECURITY_POLICY in item.callspec.params:
            param = item.callspec.params[SECURITY_POLICY]
            policy = param.get(SECURITY_POLICY) if isinstance(param, dict) else param
            if PYRAMID_TEST_APP in item.fixturenames and policy is not TokenAuthenticationPolicy:
                deselected_items.append(item)
                continue
            if (
                PYRAMID_TEST_APP_WITH_JWT_COOKIE_POLICY in item.fixturenames
                and policy is not JWTCookieAuthenticationPolicy
            ):
                deselected_items.append(item)
                continue
        kept_auth_items.append(item)

    kept_items = other_items + kept_auth_items
    if deselected_items:
        config.hook.pytest_deselected(items=deselected_items)
    items[:] = kept_items
