from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound


class SQLARootFactory(object):
    def __init__(self, request):
        self.request = request

    def __getitem__(self, item):
        try:
            return self.supplier(item)
        except (MultipleResultsFound, NoResultFound) as e:
            raise KeyError(item) from e
