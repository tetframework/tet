"""
Tests for tet.renderers.json module - Enhanced JSON renderer with adapters.
"""

import datetime
from unittest.mock import Mock

from pyramid.renderers import JSON
from tet.renderers.json import (
    _get_json_renderer_registry,
    add_json_adapter,
    construct_default_renderer,
    hook_json_renderer,
    includeme,
)


class TestJsonRendererRegistry:
    """Test JSON renderer registry functionality."""

    def test_get_json_renderer_registry_creates_new(self, pyramid_config):
        """Test that registry is created if it doesn't exist."""
        # Ensure no registry exists
        assert not hasattr(pyramid_config.registry, "tet_json_renderers")

        registry = _get_json_renderer_registry(pyramid_config)

        assert hasattr(pyramid_config.registry, "tet_json_renderers")
        assert registry == {}
        assert pyramid_config.registry.tet_json_renderers is registry

    def test_get_json_renderer_registry_returns_existing(self, pyramid_config):
        """Test that existing registry is returned."""
        existing = {"test": "renderer"}
        pyramid_config.registry.tet_json_renderers = existing

        registry = _get_json_renderer_registry(pyramid_config)

        assert registry is existing


class TestHookJsonRenderer:
    """Test JSON renderer hooking functionality."""

    def test_hook_json_renderer_default_name(self, pyramid_config):
        """Test hooking renderer with default name."""
        renderer = Mock()
        pyramid_config.add_renderer = Mock()
        pyramid_config.registry.tet_json_renderers = {}

        hook_json_renderer(pyramid_config, renderer=renderer)

        pyramid_config.add_renderer.assert_called_once_with("json", renderer)
        assert pyramid_config.registry.tet_json_renderers["json"] is renderer

    def test_hook_json_renderer_custom_name(self, pyramid_config):
        """Test hooking renderer with custom name."""
        renderer = Mock()
        pyramid_config.add_renderer = Mock()
        pyramid_config.registry.tet_json_renderers = {}

        hook_json_renderer(pyramid_config, renderer=renderer, name="custom_json")

        pyramid_config.add_renderer.assert_called_once_with("custom_json", renderer)
        assert pyramid_config.registry.tet_json_renderers["custom_json"] is renderer


class TestAddJsonAdapter:
    """Test JSON adapter registration functionality."""

    def test_add_json_adapter_default_renderer(self, pyramid_config):
        """Test adding adapter to default json renderer."""
        mock_renderer = Mock()
        pyramid_config.registry.tet_json_renderers = {"json": mock_renderer}

        class CustomType:
            pass

        def adapter(obj, req):
            return {"custom": True}

        add_json_adapter(pyramid_config, for_=CustomType, adapter=adapter)

        mock_renderer.add_adapter.assert_called_once_with(
            type_or_iface=CustomType, adapter=adapter
        )

    def test_add_json_adapter_custom_renderer(self, pyramid_config):
        """Test adding adapter to custom renderer."""
        mock_renderer = Mock()
        pyramid_config.registry.tet_json_renderers = {"custom": mock_renderer}

        class CustomType:
            pass

        def adapter(obj, req):
            return {"custom": True}

        add_json_adapter(
            pyramid_config, for_=CustomType, adapter=adapter, renderer="custom"
        )

        mock_renderer.add_adapter.assert_called_once_with(
            type_or_iface=CustomType, adapter=adapter
        )


class TestConstructDefaultRenderer:
    """Test default renderer construction."""

    def test_construct_default_renderer_basic(self):
        """Test constructing default renderer with basic adapters."""
        renderer = construct_default_renderer()

        assert isinstance(renderer, JSON)

        # The adapters are added but not exposed directly
        # We need to test by rendering actual objects
        import json

        # Test datetime adapter
        dt = datetime.datetime(2024, 1, 15, 12, 30, 45)
        # JSON renderer __call__ returns a render function
        render_fn = renderer({})
        result = render_fn({"dt": dt}, {})
        parsed = json.loads(result)
        assert parsed["dt"] == dt.isoformat()

        # Test date adapter
        d = datetime.date(2024, 1, 15)
        result = render_fn({"d": d}, {})
        parsed = json.loads(result)
        assert parsed["d"] == d.isoformat()

    def test_construct_default_renderer_with_sqlalchemy(self):
        """Test renderer construction when SQLAlchemy is available."""
        # Just test it doesn't crash - SQLAlchemy adapter is added if available
        renderer = construct_default_renderer()
        assert isinstance(renderer, JSON)

    def test_construct_default_renderer_custom_factory(self):
        """Test constructing renderer with custom factory."""
        mock_factory = Mock()
        mock_renderer = Mock()
        mock_factory.return_value = mock_renderer

        renderer = construct_default_renderer(
            renderer_factory=mock_factory, some_arg="value"
        )

        mock_factory.assert_called_once_with(some_arg="value")
        assert renderer is mock_renderer

    def test_datetime_adapter_functionality(self):
        """Test the datetime adapter works correctly."""
        renderer = construct_default_renderer()
        import json

        dt = datetime.datetime(2024, 3, 15, 14, 30, 0, 123456)
        render_fn = renderer({})
        result = render_fn({"dt": dt}, {})
        parsed = json.loads(result)

        assert parsed["dt"] == "2024-03-15T14:30:00.123456"

    def test_date_adapter_functionality(self):
        """Test the date adapter works correctly."""
        renderer = construct_default_renderer()
        import json

        d = datetime.date(2024, 3, 15)
        render_fn = renderer({})
        result = render_fn({"d": d}, {})
        parsed = json.loads(result)

        assert parsed["d"] == "2024-03-15"


class TestIncludeme:
    """Test the includeme configuration function."""

    def test_includeme_basic_setup(self, pyramid_config):
        """Test basic setup through includeme."""
        pyramid_config.add_renderer = Mock()
        pyramid_config.add_directive = Mock()

        includeme(pyramid_config)

        # Should add renderer
        assert pyramid_config.add_renderer.called
        call_args = pyramid_config.add_renderer.call_args
        assert call_args[0][0] == "json"
        assert isinstance(call_args[0][1], JSON)

        # Should add directives
        assert pyramid_config.add_directive.call_count == 2

        # Check directives added
        calls = pyramid_config.add_directive.call_args_list
        directive_names = [call[0][0] for call in calls]
        assert "add_json_renderer" in directive_names
        assert "add_json_adapter" in directive_names

    def test_includeme_creates_registry(self, pyramid_config):
        """Test that includeme creates the renderer registry."""
        pyramid_config.add_renderer = Mock()
        pyramid_config.add_directive = Mock()

        includeme(pyramid_config)

        assert hasattr(pyramid_config.registry, "tet_json_renderers")
        assert "json" in pyramid_config.registry.tet_json_renderers

    def test_includeme_renderer_has_adapters(self, pyramid_config):
        """Test that the renderer has default adapters."""
        pyramid_config.add_renderer = Mock()
        pyramid_config.add_directive = Mock()

        includeme(pyramid_config)

        renderer = pyramid_config.add_renderer.call_args[0][1]

        # Check it's a JSON renderer with proper functionality
        assert isinstance(renderer, JSON)
        # Test by rendering actual objects
        import json

        dt = datetime.datetime.now()
        render_fn = renderer({})
        result = render_fn({"dt": dt}, {})
        parsed = json.loads(result)
        assert "dt" in parsed

    def test_complete_integration(self, pyramid_config):
        """Test complete integration of JSON renderer setup."""
        pyramid_config.add_renderer = Mock()
        pyramid_config.add_directive = Mock()

        includeme(pyramid_config)

        # Get the registered functions
        add_json_renderer_func = None
        add_json_adapter_func = None

        for call in pyramid_config.add_directive.call_args_list:
            if call[0][0] == "add_json_renderer":
                add_json_renderer_func = call[0][1]
            elif call[0][0] == "add_json_adapter":
                add_json_adapter_func = call[0][1]

        assert add_json_renderer_func is hook_json_renderer
        assert add_json_adapter_func is add_json_adapter

        # Test using the directives
        class TestClass:
            def to_dict(self):
                return {"test": "value"}

        # Add a custom adapter
        add_json_adapter_func(
            pyramid_config, for_=TestClass, adapter=lambda obj, req: obj.to_dict()
        )

        # Verify it was added to the renderer
        # Since the renderer is mocked in add_renderer, we just verify the structure
        assert "json" in pyramid_config.registry.tet_json_renderers
