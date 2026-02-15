from unittest.mock import MagicMock

from pyramid.config import Configurator

from tet.security.csrf import includeme


def test_includeme_sets_csrf_options():
    """includeme should call set_default_csrf_options(require_csrf=True)."""
    config = MagicMock(spec=Configurator)
    includeme(config)
    config.set_default_csrf_options.assert_called_once_with(require_csrf=True)
