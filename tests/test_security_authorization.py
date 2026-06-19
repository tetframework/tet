"""
Tests for tet.security.authorization module - Enhanced authorization policies.
"""

from unittest.mock import Mock, patch

from tet.security.authorization import (
    AuthorizationPolicyWrapper,
    INewAuthorizationPolicy,
    includeme,
)
from zope.interface import implementer


@implementer(INewAuthorizationPolicy)
class MockNewAuthorizationPolicy:
    """Mock implementation of INewAuthorizationPolicy."""

    def permits(self, request, context, principals, permission):
        return True

    def principals_allowed_by_permission(self, request, context, permission):
        return {"user:1", "group:admin"}


class TestAuthorizationPolicyWrapper:
    """Test the AuthorizationPolicyWrapper class."""

    def test_wrapper_initialization(self):
        """Test wrapper can be initialized with a policy."""
        policy = MockNewAuthorizationPolicy()
        wrapper = AuthorizationPolicyWrapper(policy)
        assert wrapper.wrapped is policy

    @patch("tet.security.authorization.get_current_request")
    def test_permits_adds_request(self, mock_get_request):
        """Test that permits method adds request parameter."""
        mock_request = Mock()
        mock_get_request.return_value = mock_request

        policy = MockNewAuthorizationPolicy()
        policy.permits = Mock(return_value=True)

        wrapper = AuthorizationPolicyWrapper(policy)

        context = object()
        principals = ["user:1"]
        permission = "view"

        result = wrapper.permits(context, principals, permission)

        assert result is True
        policy.permits.assert_called_once_with(mock_request, context, principals, permission)
        mock_get_request.assert_called_once()

    @patch("tet.security.authorization.get_current_request")
    def test_principals_allowed_by_permission_adds_request(self, mock_get_request):
        """Test that principals_allowed_by_permission adds request parameter."""
        mock_request = Mock()
        mock_get_request.return_value = mock_request

        policy = MockNewAuthorizationPolicy()
        policy.principals_allowed_by_permission = Mock(return_value={"user:1", "group:admin"})

        wrapper = AuthorizationPolicyWrapper(policy)

        context = object()
        permission = "edit"

        result = wrapper.principals_allowed_by_permission(context, permission)

        assert result == {"user:1", "group:admin"}
        policy.principals_allowed_by_permission.assert_called_once_with(
            mock_request, context, permission
        )
        mock_get_request.assert_called_once()

    @patch("tet.security.authorization.get_current_request")
    def test_wrapper_handles_none_request(self, mock_get_request):
        """Test wrapper handles case when no current request exists."""
        mock_get_request.return_value = None

        policy = MockNewAuthorizationPolicy()
        policy.permits = Mock(return_value=False)

        wrapper = AuthorizationPolicyWrapper(policy)

        result = wrapper.permits(object(), ["user:1"], "view")

        assert result is False
        # Should have been called with None as request
        policy.permits.assert_called_once()
        assert policy.permits.call_args[0][0] is None


class TestIncludeme:
    """Test the includeme configuration function."""

    def test_includeme_adds_directive(self, pyramid_config):
        """Test that includeme adds set_authorization_policy directive."""
        pyramid_config.add_directive = Mock()

        includeme(pyramid_config)

        pyramid_config.add_directive.assert_called_once()
        call_args = pyramid_config.add_directive.call_args
        assert call_args[0][0] == "set_authorization_policy"
        assert callable(call_args[0][1])

    def test_set_authorization_policy_with_new_policy(self, pyramid_config):
        """Test setting authorization policy with INewAuthorizationPolicy."""
        pyramid_config.add_directive = Mock()
        pyramid_config.maybe_dotted = Mock(side_effect=lambda x: x)

        includeme(pyramid_config)

        # Get the set_authorization_policy function that was registered
        set_auth_policy = pyramid_config.add_directive.call_args[0][1]

        # Create a new-style policy
        new_policy = MockNewAuthorizationPolicy()

        # Mock the parent class method
        from pyramid.config.security import SecurityConfiguratorMixin

        # Check if the policy implements the interface
        assert INewAuthorizationPolicy.providedBy(new_policy)

        with patch.object(SecurityConfiguratorMixin, "set_authorization_policy") as mock_set:
            # Call the directive
            set_auth_policy(pyramid_config, new_policy)

            # Should wrap the policy
            pyramid_config.maybe_dotted.assert_called_once_with(new_policy)
            mock_set.assert_called_once()

            # Check that a wrapper was created
            call_args = mock_set.call_args[0]
            assert call_args[0] is pyramid_config
            wrapped_policy = call_args[1]

            assert isinstance(wrapped_policy, AuthorizationPolicyWrapper)

    @patch("tet.security.authorization.SecurityConfiguratorMixin")
    def test_set_authorization_policy_with_old_policy(self, mock_security_mixin, pyramid_config):
        """Test setting authorization policy with old-style policy."""
        pyramid_config.add_directive = Mock()
        pyramid_config.maybe_dotted = Mock(side_effect=lambda x: x)

        includeme(pyramid_config)

        # Get the set_authorization_policy function
        set_auth_policy = pyramid_config.add_directive.call_args[0][1]

        # Create an old-style policy (not implementing INewAuthorizationPolicy)
        old_policy = Mock()

        # Call the directive
        set_auth_policy(pyramid_config, old_policy)

        # Should NOT wrap the policy
        pyramid_config.maybe_dotted.assert_called_once_with(old_policy)
        mock_security_mixin.set_authorization_policy.assert_called_once_with(
            pyramid_config, old_policy
        )

    def test_set_authorization_policy_with_dotted_name(self, pyramid_config):
        """Test setting authorization policy with dotted Python name."""
        pyramid_config.add_directive = Mock()

        # Mock maybe_dotted to return a resolved policy
        resolved_policy = MockNewAuthorizationPolicy()
        pyramid_config.maybe_dotted = Mock(return_value=resolved_policy)

        includeme(pyramid_config)

        # Get the set_authorization_policy function
        set_auth_policy = pyramid_config.add_directive.call_args[0][1]

        from pyramid.config.security import SecurityConfiguratorMixin

        with patch.object(SecurityConfiguratorMixin, "set_authorization_policy") as mock_set:
            # Call with a dotted name
            set_auth_policy(pyramid_config, "my.module.Policy")

            # Should resolve the dotted name
            pyramid_config.maybe_dotted.assert_called_once_with("my.module.Policy")

            # Check what was passed to set_authorization_policy
            call_args = mock_set.call_args[0]
            wrapped_policy = call_args[1]
            assert isinstance(wrapped_policy, AuthorizationPolicyWrapper)


class TestINewAuthorizationPolicy:
    """Test the INewAuthorizationPolicy interface."""

    def test_interface_methods(self):
        """Test that the interface defines the expected methods."""
        from zope.interface.verify import verifyClass

        # Verify our mock implementation properly implements the interface
        verifyClass(INewAuthorizationPolicy, MockNewAuthorizationPolicy)

    def test_interface_signatures(self):
        """Test the interface method signatures."""
        # The interface should have these methods defined as part of the interface
        # In Zope interfaces, methods are defined in the interface namespace
        permits_spec = INewAuthorizationPolicy.get("permits")
        principals_spec = INewAuthorizationPolicy.get("principals_allowed_by_permission")
        assert permits_spec is not None
        assert principals_spec is not None
