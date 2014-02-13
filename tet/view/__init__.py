# -*- coding: utf-8 -*-
from __future__ import absolute_import, division,\
       print_function, unicode_literals

from pyramid.view import *

_pyramid_view_config = view_config

class view_config(_pyramid_view_config):
    def __init__(self, **settings):
        super(view_config, self).__init__(settings)

