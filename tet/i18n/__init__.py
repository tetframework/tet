import sys

from pyramid.config import Configurator
from pyramid.i18n import get_localizer, TranslationStringFactory
from pyramid.threadlocal import get_current_request


def add_renderer_globals(event):
    request = event.get('request')

    if request is None:
        request = get_current_request()

    event['_'] = request.translate
    event['gettext'] = request.translate
    event['ngettext'] = request.pluralize
    event['localizer'] = request.localizer


def configure_i18n(config: Configurator, default_domain: str):
    config.add_subscriber(add_renderer_globals,
                          'pyramid.events.BeforeRender')
    config.add_subscriber(add_renderer_globals,
                          'tet.viewlet.IBeforeViewletRender')

    config.registry.tsf = tsf = TranslationStringFactory(default_domain)

    def translate(request):
        localizer = request.localizer

        def auto_translate(string, *, domain=default_domain, mapping=None, context=None):
            if isinstance(string, str):
                string = tsf(string, context=context)

            return localizer.translate(string, domain=domain, mapping=mapping)

        return auto_translate

    def pluralize(request):
        localizer = request.localizer

        def auto_pluralize(singular, plural, n, *, domain=default_domain, mapping=None, context=None):
            if isinstance(singular, str):
                singular = tsf(singular, context=context)

            return localizer.pluralize(singular, plural, n, domain=domain, mapping=mapping)

        return auto_pluralize

    config.add_request_method(translate, property=True, reify=True)
    config.add_request_method(pluralize, property=True, reify=True)
    config.add_request_method(get_localizer, name='localize', property=True, reify=True)


def includeme(config: Configurator):
    default_domain = config.get_settings().get('default_i18n_domain',
                                               config.package.__name__)
    configure_i18n(config, default_domain)
