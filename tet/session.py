"""
Session factory utilities for Tet applications.

Provides a generic session factory that can wrap any session type.
"""
from pyramid.interfaces import ISessionFactory
from zope.interface import implementer


@implementer(ISessionFactory)
class TetSessionFactory:
    """
    A generic session factory that creates sessions of a given type.

    :param session_type: A callable that accepts a request and returns a session.
    """

    def __init__(self, session_type):
        self.session_type = session_type

    def __call__(self, request):
        """Create a session for the given request."""
        return self.session_type(request)
