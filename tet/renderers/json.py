"""
JSON rendering with custom type adapters for Tet applications.

This module provides a JSON renderer with sensible defaults and the ability
to register custom type adapters. It is included automatically when using
the ``renderers.json`` feature.

Features
--------

- Automatic serialization of :class:`datetime.datetime` and :class:`datetime.date`
  to ISO 8601 format
- SQLAlchemy keyed tuple support (when SQLAlchemy is installed)
- Extensible via custom type adapters

Example
-------

Adding a custom adapter for a model class::

    from tet.config import application_factory

    @application_factory(included_features=["renderers.json"])
    def main(config):
        config.add_json_adapter(
            for_=MyModel,
            adapter=lambda obj, request: {"id": obj.id, "name": obj.name},
        )
        config.scan()

Using a custom JSON renderer factory::

    from pyramid.renderers import JSON
    from tet.renderers.json import construct_default_renderer

    # Create a renderer with custom settings
    renderer = construct_default_renderer(
        renderer_factory=JSON,
        serializer=custom_serializer,
    )
"""
import datetime
from typing import Any, Callable, Dict

from pyramid.config import Configurator
from pyramid.renderers import JSON


def _get_json_renderer_registry(config: Configurator) -> Dict[str, Any]:
    if not hasattr(config.registry, 'tet_json_renderers'):
        config.registry.tet_json_renderers = {}

    return config.registry.tet_json_renderers


def hook_json_renderer(config: Configurator,
                       *,
                       renderer: Any,
                       name: str='json'):
    config.add_renderer(name, renderer)
    _get_json_renderer_registry(config)[name] = renderer


def add_json_adapter(config: Configurator,
                     *,
                     for_: type,
                     adapter: Callable[[Any], Any],
                     renderer: str='json'):
    _get_json_renderer_registry(config)[renderer].add_adapter(
        type_or_iface=for_,
        adapter=adapter
    )


def construct_default_renderer(renderer_factory: Callable[..., Any]=JSON,
                               **renderer_args):
    json_renderer = renderer_factory(**renderer_args)

    try:
        from sqlalchemy.util._collections import AbstractKeyedTuple
        json_renderer.add_adapter(AbstractKeyedTuple,
                                  lambda o, req: o._asdict())
        del AbstractKeyedTuple
    except ImportError:
        pass

    json_renderer.add_adapter(datetime.datetime, lambda d, req: d.isoformat())
    json_renderer.add_adapter(datetime.date, lambda d, req: d.isoformat())
    return json_renderer


def includeme(config: Configurator):
    renderer = construct_default_renderer()
    hook_json_renderer(config, renderer=renderer)
    config.add_directive('add_json_renderer', hook_json_renderer)
    config.add_directive('add_json_adapter', add_json_adapter)
