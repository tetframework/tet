"""
Tests for tet.util.json module - JavaScript-safe JSON serialization.
"""
import json

from tet.util.json import js_safe_dumps


class TestJsSafeDumps:
    """Test JavaScript-safe JSON dumping functionality."""

    def test_basic_string(self):
        """Test basic string encoding."""
        assert js_safe_dumps("hello") == '"hello"'

    def test_basic_dict(self):
        """Test basic dictionary encoding."""
        assert js_safe_dumps({"key": "value"}) == '{"key": "value"}'

    def test_basic_list(self):
        """Test basic list encoding."""
        assert js_safe_dumps([1, 2, 3]) == '[1, 2, 3]'

    def test_escapes_less_than(self):
        """Test that < is escaped for XSS prevention."""
        result = js_safe_dumps("test<script>")
        assert result == '"test\\u003cscript\\u003e"'
        assert "<" not in result
        assert ">" not in result

    def test_escapes_greater_than(self):
        """Test that > is escaped for XSS prevention."""
        result = js_safe_dumps("test>value")
        assert result == '"test\\u003evalue"'
        assert ">" not in result

    def test_escapes_forward_slash(self):
        """Test that / is escaped for script tag prevention."""
        result = js_safe_dumps("</script>")
        assert result == '"\\u003c\\u002fscript\\u003e"'
        assert "/" not in result

    def test_escapes_ampersand(self):
        """Test that & is escaped for HTML safety."""
        result = js_safe_dumps("test&value")
        assert result == '"test\\u0026value"'
        assert "&" not in result

    def test_escapes_line_separator(self):
        """Test that U+2028 line separator is escaped."""
        result = js_safe_dumps("test\u2028value")
        assert result == '"test\\u2028value"'
        assert "\u2028" not in result

    def test_escapes_paragraph_separator(self):
        """Test that U+2029 paragraph separator is escaped."""
        result = js_safe_dumps("test\u2029value")
        assert result == '"test\\u2029value"'
        assert "\u2029" not in result

    def test_multiple_escapes(self):
        """Test multiple dangerous characters in one string."""
        dangerous = "<script>alert('XSS');</script>"
        result = js_safe_dumps(dangerous)
        assert "<" not in result
        assert ">" not in result
        assert "/" not in result
        assert "&" not in result
        # Verify it can be decoded back
        decoded = json.loads(result)
        assert decoded == dangerous

    def test_nested_structures_with_dangerous_chars(self):
        """Test nested structures containing dangerous characters."""
        data = {
            "html": "<div>Content</div>",
            "script": "</script>",
            "items": ["<item1>", "</item2>", "&item3"]
        }
        result = js_safe_dumps(data)
        assert "<" not in result
        assert ">" not in result
        assert "/" not in result  # The forward slash in the dangerous content
        assert "&" not in result
        # Verify structure is preserved
        decoded = json.loads(result)
        assert decoded == data

    def test_unicode_handling(self):
        """Test that other Unicode characters are handled correctly."""
        data = "Hello 世界 🌍"
        result = js_safe_dumps(data)
        decoded = json.loads(result)
        assert decoded == data

    def test_complex_nested_object(self):
        """Test complex nested object with various dangerous characters."""
        data = {
            "user_input": "<img src=x onerror='alert(1)'>",
            "url": "https://example.com/path",
            "content": "Line1\u2028Line2\u2029Line3",
            "mixed": ["<tag>", {"nested": "</closing>"}, "&escaped"],
            "number": 42,
            "boolean": True,
            "null": None
        }
        result = js_safe_dumps(data)
        # Check all dangerous chars are escaped
        assert "<" not in result
        assert ">" not in result
        assert "\u2028" not in result
        assert "\u2029" not in result
        assert "&" not in result
        # Verify data integrity
        decoded = json.loads(result)
        assert decoded == data

    def test_empty_values(self):
        """Test empty strings, lists, and dicts."""
        assert js_safe_dumps("") == '""'
        assert js_safe_dumps([]) == '[]'
        assert js_safe_dumps({}) == '{}'

    def test_special_json_values(self):
        """Test special JSON values like null, true, false."""
        assert js_safe_dumps(None) == 'null'
        assert js_safe_dumps(True) == 'true'
        assert js_safe_dumps(False) == 'false'
