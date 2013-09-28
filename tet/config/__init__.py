# -*- coding: utf-8 -*-
from __future__ import absolute_import, division,\
       print_function, unicode_literals

from pyramid.config import *

class TetAppFactory(object):
    scan = None
    includes = None

    def __init__(self, *args, **kwargs):
        super(TetAppFactory, self).__init__(*args, **kwargs)

    def _dummy(self, *a, **kw):
        pass

    def init_app_factory(self, global_config, settings):
        self.settings = settings
        self.global_config = global_config
        self.config = self.make_configurator()

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
        if self.scan:
            self.do_scan()

        self.pre_configure_app(self.config)
        self.configure_app(self.config)
        self.post_configure_app(self.config)
        return self.config.make_wsgi_app()

    def __call__(self, global_config, **settings):
        self.init_app_factory(global_config, settings)
        return self.construct_app()

    @classmethod
    def main(cls, global_config, **settings):
        instance = cls()
        return instance(global_config, **settings)
