"""
Tests for tet.sqlalchemy.factory module - SQLAlchemy root factory with exception handling.
"""

from unittest.mock import Mock

import pytest
from sqlalchemy.exc import DataError
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from tet.sqlalchemy.factory import SQLARootFactory


class TestSQLARootFactory:
    """Test the SQLARootFactory class."""

    def test_initialization(self, pyramid_request):
        """Test factory initialization with request."""
        factory = SQLARootFactory(pyramid_request)
        assert factory.request is pyramid_request

    def test_getitem_success(self, pyramid_request):
        """Test successful item retrieval."""
        factory = SQLARootFactory(pyramid_request)

        # Mock the supplier method
        expected_result = Mock()
        factory.supplier = Mock(return_value=expected_result)

        result = factory["test_id"]

        assert result is expected_result
        factory.supplier.assert_called_once_with("test_id")

    def test_getitem_raises_keyerror_on_noresult(self, pyramid_request):
        """Test that NoResultFound is converted to KeyError."""
        factory = SQLARootFactory(pyramid_request)

        # Mock supplier to raise NoResultFound
        factory.supplier = Mock(side_effect=NoResultFound("No result found"))

        with pytest.raises(KeyError) as exc_info:
            _ = factory["missing_id"]

        assert str(exc_info.value) == "'missing_id'"
        # Check the cause chain
        assert isinstance(exc_info.value.__cause__, NoResultFound)

    def test_getitem_raises_keyerror_on_multipleresults(self, pyramid_request):
        """Test that MultipleResultsFound is converted to KeyError."""
        factory = SQLARootFactory(pyramid_request)

        # Mock supplier to raise MultipleResultsFound
        factory.supplier = Mock(
            side_effect=MultipleResultsFound("Multiple results found")
        )

        with pytest.raises(KeyError) as exc_info:
            _ = factory["duplicate_id"]

        assert str(exc_info.value) == "'duplicate_id'"
        # Check the cause chain
        assert isinstance(exc_info.value.__cause__, MultipleResultsFound)

    def test_getitem_raises_keyerror_on_dataerror(self, pyramid_request):
        """Test that DataError is converted to KeyError."""
        factory = SQLARootFactory(pyramid_request)

        # Mock supplier to raise DataError
        # DataError requires specific arguments: (statement, params, orig, dbapi_base_err)
        orig_error = Exception("Invalid data")
        data_error = DataError("statement", {}, orig_error)
        factory.supplier = Mock(side_effect=data_error)

        with pytest.raises(KeyError) as exc_info:
            _ = factory["invalid_id"]

        assert str(exc_info.value) == "'invalid_id'"
        # Check the cause chain
        assert isinstance(exc_info.value.__cause__, DataError)

    def test_getitem_propagates_other_exceptions(self, pyramid_request):
        """Test that other exceptions are not caught."""
        factory = SQLARootFactory(pyramid_request)

        # Mock supplier to raise a different exception
        factory.supplier = Mock(side_effect=ValueError("Some other error"))

        # Should NOT be converted to KeyError
        with pytest.raises(ValueError) as exc_info:
            _ = factory["test_id"]

        assert str(exc_info.value) == "Some other error"

    def test_subclass_with_supplier(self, pyramid_request):
        """Test using a subclass with a supplier method."""

        class ConcreteFactory(SQLARootFactory):
            def supplier(self, item_id):
                # Simulate database lookup
                if item_id == "exists":
                    return {"id": item_id, "name": "Test Item"}
                elif item_id == "duplicate":
                    raise MultipleResultsFound("Multiple items found")
                else:
                    raise NoResultFound("Item not found")

        factory = ConcreteFactory(pyramid_request)

        # Test successful retrieval
        result = factory["exists"]
        assert result == {"id": "exists", "name": "Test Item"}

        # Test not found
        with pytest.raises(KeyError):
            _ = factory["missing"]

        # Test duplicate
        with pytest.raises(KeyError):
            _ = factory["duplicate"]

    def test_request_available_in_subclass(self, pyramid_request):
        """Test that request is available in subclass methods."""

        class RequestAwareFactory(SQLARootFactory):
            def supplier(self, item_id):
                # Access request in supplier
                assert self.request is not None
                return f"Item for user: {getattr(self.request, 'user', 'anonymous')}"

        pyramid_request.user = "testuser"
        factory = RequestAwareFactory(pyramid_request)

        result = factory["any_id"]
        assert result == "Item for user: testuser"

    def test_factory_as_traversal_root(self, pyramid_request):
        """Test factory can be used as Pyramid traversal root."""

        class TraversalFactory(SQLARootFactory):
            __name__ = ""
            __parent__ = None

            def supplier(self, name):
                if name == "users":
                    return Mock(__name__="users", __parent__=self)
                raise NoResultFound()

        factory = TraversalFactory(pyramid_request)

        # Should work with traversal
        users = factory["users"]
        assert users.__name__ == "users"
        assert users.__parent__ is factory

        # Missing resources should raise KeyError (for traversal)
        with pytest.raises(KeyError):
            _ = factory["missing"]
