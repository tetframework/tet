from pyramid.config import Configurator


def includeme(config: Configurator):
    config.include('tonnikala.pyramid')
    config.add_tonnikala_extensions('.tk')
