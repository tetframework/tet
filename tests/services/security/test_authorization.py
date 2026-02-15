from unittest.mock import MagicMock, patch, call

from pyramid.config import Configurator
from zope.interface import implementer

from tet.security.authorization import (
    AuthorizationPolicyWrapper,
    INewAuthorizationPolicy,
    includeme,
)


def test_authorization_policy_wrapper_permits():
    """AuthorizationPolicyWrapper.permits should pass request from threadlocal."""
    mock_policy = MagicMock()
    mock_policy.permits.return_value = True
    wrapper = AuthorizationPolicyWrapper(mock_policy)

    mock_request = MagicMock()
    context = MagicMock()
    principals = ["system.Everyone", "user:1"]
    permission = "view"

    with patch("tet.security.authorization.get_current_request", return_value=mock_request):
        result = wrapper.permits(context, principals, permission)

    assert result is True
    mock_policy.permits.assert_called_once_with(mock_request, context, principals, permission)


def test_authorization_policy_wrapper_principals_allowed_by_permission():
    """AuthorizationPolicyWrapper should delegate principals_allowed_by_permission."""
    mock_policy = MagicMock()
    mock_policy.principals_allowed_by_permission.return_value = {"user:1", "group:admin"}
    wrapper = AuthorizationPolicyWrapper(mock_policy)

    mock_request = MagicMock()
    context = MagicMock()
    permission = "edit"

    with patch("tet.security.authorization.get_current_request", return_value=mock_request):
        result = wrapper.principals_allowed_by_permission(context, permission)

    assert result == {"user:1", "group:admin"}
    mock_policy.principals_allowed_by_permission.assert_called_once_with(
        mock_request, context, permission
    )


def test_includeme_adds_directive():
    """includeme should add set_authorization_policy directive to config."""
    config = MagicMock(spec=Configurator)
    includeme(config)
    config.add_directive.assert_called_once()
    directive_name = config.add_directive.call_args[0][0]
    assert directive_name == "set_authorization_policy"
    # Second arg should be callable
    directive_fn = config.add_directive.call_args[0][1]
    assert callable(directive_fn)


def test_set_authorization_policy_directive_with_standard_policy():
    """The registered directive should pass through a standard policy."""
    config = MagicMock(spec=Configurator)
    includeme(config)

    directive_fn = config.add_directive.call_args[0][1]

    mock_policy = MagicMock()
    config.maybe_dotted.return_value = mock_policy

    with patch(
        "tet.security.authorization.SecurityConfiguratorMixin.set_authorization_policy"
    ) as mock_set:
        directive_fn(config, mock_policy)

    config.maybe_dotted.assert_called_once_with(mock_policy)
    mock_set.assert_called_once_with(config, mock_policy)


def test_set_authorization_policy_isinstance_check_is_broken():
    """The isinstance check with zope Interface never triggers.

    authorization.py line 48 uses ``isinstance(policy, INewAuthorizationPolicy)``
    but zope Interfaces don't support Python's isinstance(); it should use
    ``INewAuthorizationPolicy.providedBy(policy)`` instead. As a result, the
    AuthorizationPolicyWrapper wrapping branch is dead code.
    """

    @implementer(INewAuthorizationPolicy)
    class NewPolicy:
        def permits(self, request, context, principals, permission):
            return True

        def principals_allowed_by_permission(self, request, context, permission):
            return set()

    policy = NewPolicy()
    # providedBy works, isinstance does not
    assert INewAuthorizationPolicy.providedBy(policy) is True
    assert isinstance(policy, INewAuthorizationPolicy) is False
