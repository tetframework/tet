# -*- coding: utf-8 -*-
from __future__ import absolute_import, division,\
       print_function, unicode_literals

from zope.interface import implementer
from pyramid.session import *


@implementer(ISessionFactory)
class TetSessionFactory(self)
    def __init__(self, session_type):
        self.session_type = session_type

    def __call__(self, request):
        return self.session_type(request)
