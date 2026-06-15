from pyramid.interfaces import ISessionFactory
from zope.interface import implementer


@implementer(ISessionFactory)
class TetSessionFactory:
    def __init__(self, session_type):
        self.session_type = session_type

    def __call__(self, request):
        return self.session_type(request)
