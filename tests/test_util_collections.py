"""
Tests for tet.util.collections module - Collection utilities.
"""
from tet.util.collections import flatten


class TestFlatten:
    """Test the flatten function for nested iterables."""

    def test_flatten_simple_list(self):
        """Test flattening a simple list."""
        result = list(flatten([1, 2, 3]))
        assert result == [1, 2, 3]

    def test_flatten_nested_list(self):
        """Test flattening a nested list."""
        result = list(flatten([1, [2, 3], 4]))
        assert result == [1, 2, 3, 4]

    def test_flatten_deeply_nested(self):
        """Test flattening deeply nested structures."""
        result = list(flatten([1, [2, [3, [4, 5]], 6], 7]))
        assert result == [1, 2, 3, 4, 5, 6, 7]

    def test_flatten_mixed_types(self):
        """Test flattening with mixed data types."""
        result = list(flatten([1, [2.5, "three"], [True, None]]))
        assert result == [1, 2.5, "three", True, None]

    def test_flatten_preserves_strings(self):
        """Test that strings are not exploded into characters."""
        result = list(flatten(["hello", ["world", "test"]]))
        assert result == ["hello", "world", "test"]
        # Ensure string isn't split into chars
        assert result != ["h", "e", "l", "l", "o", "world", "test"]

    def test_flatten_preserves_bytes(self):
        """Test that bytes are not exploded into individual bytes."""
        result = list(flatten([b"hello", [b"world", b"test"]]))
        assert result == [b"hello", b"world", b"test"]

    def test_flatten_with_tuples(self):
        """Test flattening with tuples."""
        result = list(flatten([1, (2, 3), [4, (5, 6)]]))
        assert result == [1, 2, 3, 4, 5, 6]

    def test_flatten_with_sets(self):
        """Test flattening with sets."""
        result = sorted(flatten([1, {2, 3}, [4, {5, 6}]]))
        assert result == [1, 2, 3, 4, 5, 6]

    def test_flatten_with_generators(self):
        """Test flattening with generator expressions."""
        gen = (x for x in [1, 2, 3])
        result = list(flatten([0, gen, 4]))
        assert result == [0, 1, 2, 3, 4]

    def test_flatten_empty_list(self):
        """Test flattening empty list."""
        result = list(flatten([]))
        assert result == []

    def test_flatten_nested_empty_lists(self):
        """Test flattening nested empty lists."""
        result = list(flatten([[], [[], []]]))
        assert result == []

    def test_flatten_single_element(self):
        """Test flattening single element."""
        result = list(flatten([42]))
        assert result == [42]

    def test_flatten_complex_nested_structure(self):
        """Test complex nested structure with various types."""
        input_data = [
            1,
            [2, "three"],
            [[4], [5, [6, 7]]],
            (8, 9),
            [b"bytes", ["nested", "strings"]],
            [[[[[10]]]]],
            []
        ]
        result = list(flatten(input_data))
        expected = [1, 2, "three", 4, 5, 6, 7, 8, 9, b"bytes", "nested", "strings", 10]
        assert result == expected

    def test_flatten_with_none_values(self):
        """Test flattening with None values."""
        result = list(flatten([1, [None, 2], [[None]], None]))
        assert result == [1, None, 2, None, None]

    def test_flatten_unicode_strings(self):
        """Test that Unicode strings are preserved."""
        result = list(flatten(["hello", ["世界", "🌍"]]))
        assert result == ["hello", "世界", "🌍"]

    def test_flatten_dict_values(self):
        """Test flattening dict values (iterates over keys)."""
        # Note: iterating over dict yields keys only
        result = sorted(flatten([{"a": 1, "b": 2}, ["c"]]))
        assert result == ["a", "b", "c"]

    def test_flatten_dict_items(self):
        """Test flattening dict items explicitly."""
        d = {"a": 1, "b": 2}
        result = list(flatten([d.items()]))
        # dict.items() returns tuples which get flattened
        # Can't sort mixed types, so check elements separately
        assert set(result) == {"a", "b", 1, 2}

    def test_flatten_range_objects(self):
        """Test flattening range objects."""
        result = list(flatten([range(3), [range(3, 6)]]))
        assert result == [0, 1, 2, 3, 4, 5]

    def test_flatten_is_generator(self):
        """Test that flatten returns a generator."""
        import types
        result = flatten([1, [2, 3]])
        assert isinstance(result, types.GeneratorType)

    def test_flatten_lazy_evaluation(self):
        """Test that flatten uses lazy evaluation."""
        def gen_with_side_effect():
            yield 1
            yield [2, 3]
            raise Exception("Should not reach here if lazy")

        result = flatten(gen_with_side_effect())
        # Take only first two elements, should not trigger exception
        first_two = []
        for i, item in enumerate(result):
            if i >= 2:
                break
            first_two.append(item)
        assert first_two == [1, 2]
