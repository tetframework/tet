"""
Tests for tet.security.csrf module - CSRF protection configuration.
"""
from unittest.mock import Mock

from tet.security.csrf import includeme


class TestCSRFProtection:
    """Test CSRF protection configuration."""

    def test_includeme_sets_csrf_defaults(self, pyramid_config):
        """Test that includeme sets require_csrf=True by default."""
        # Mock the set_default_csrf_options method
        pyramid_config.set_default_csrf_options = Mock()

        # Call includeme
        includeme(pyramid_config)

        # Verify it was called with require_csrf=True
        pyramid_config.set_default_csrf_options.assert_called_once_with(require_csrf=True)

    def test_includeme_with_real_configurator(self):
        """Test with a real Pyramid Configurator."""
        from pyramid.config import Configurator

        config = Configurator()
        config.set_default_csrf_options = Mock()

        includeme(config)

        config.set_default_csrf_options.assert_called_once_with(require_csrf=True)
