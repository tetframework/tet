# -*- coding: utf-8 -*-
from __future__ import absolute_import, division,\
       print_function, unicode_literals

from pyramid.config import *
from tet.decorators import deprecated


class TetAppFactory(object):
    scan = None
    includes = None
    i18n = True

    def __new__(cls, global_config, **settings):
        instance = cls.instantiate()
        instance.init_app_factory(global_config, settings)
        return instance.construct_app()

    @classmethod
    def instantiate(cls):
        return super(TetAppFactory, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        super(TetAppFactory, self).__init__(*args, **kwargs)

    def _dummy(self, *a, **kw):
        pass

    def init_app_factory(self, global_config, settings):
        self.settings = settings
        self.global_config = global_config
        self.config = self.make_configurator()

        self.do_default_includes()

    def do_default_includes(self):
        self.config.include('tet.services')

    def make_configurator(self):
        return Configurator(settings=self.settings)

    pre_configure_app = _dummy
    configure_db = _dummy

    def configure_app(self, config):
        self.configure_db(config)
        self.configure_routes(config)

    def configure_routes(self, config):
        pass

    def post_configure_app(self, config):
        pass

    def do_scan(self):
        self.config.scan(self.scan)

    def do_include(self):
        for i in self.includes:
            self.config.include(i)

    def construct_app(self):
        if self.includes:
            self.do_include()

        self.pre_configure_app(self.config)
        self.configure_app(self.config)
        self.post_configure_app(self.config)

        if self.scan:
            self.do_scan()

        return self.wrap_app(self.config.make_wsgi_app())

    def wrap_app(self, app):
        return app

    @classmethod
    @deprecated
    def main(cls, global_config, **settings):
        return cls(global_config, **settings)
