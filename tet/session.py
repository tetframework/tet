from zope.interface import implementer
from pyramid.session import *


@implementer(ISessionFactory)
class TetSessionFactory(self)
    def __init__(self, session_type):
        self.session_type = session_type

    def __call__(self, request):
        return self.session_type(request)
