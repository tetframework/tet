from pyramid.config import Configurator


def includeme(config: Configurator) -> None:
    config.set_default_csrf_options(require_csrf=True)