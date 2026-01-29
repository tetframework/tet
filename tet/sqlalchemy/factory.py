"""
Root factory base class for SQLAlchemy-backed traversal.

This module provides a base class for implementing Pyramid traversal
with SQLAlchemy models.

Example
-------

Creating a root factory for users::

    from sqlalchemy.orm import Session
    from tet.sqlalchemy.factory import SQLARootFactory

    class UserFactory(SQLARootFactory):
        def supplier(self, item):
            session = self.request.find_service(Session)
            return session.query(User).filter(User.id == int(item)).one()

Using in route configuration::

    config.add_route("user", "/users/{id}", factory=UserFactory)
"""
from sqlalchemy.exc import DataError
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound


class SQLARootFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, item):
        try:
            return self.supplier(item)
        except (MultipleResultsFound, NoResultFound, DataError) as e:
            raise KeyError(item) from e
