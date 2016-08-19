from pyramid.config import Configurator


def i18n(config: Configurator):
    config.include('tet.renderers.tonnikala')
    config.set_tonnikala_l10n(True)


def includeme(config: Configurator):
    config.include('tonnikala.pyramid')
    config.add_tonnikala_extensions('.tk')
