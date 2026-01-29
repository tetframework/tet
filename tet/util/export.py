"""
Module export decorator utility.

This module provides a decorator that automatically maintains ``__all__``
for a module, making it easy to control what gets exported.

Example
-------

Using the exporter decorator::

    from tet.util.export import exporter

    export, __all__ = exporter()

    @export
    def my_public_function():
        pass

    @export
    class MyPublicClass:
        pass

    def _private_function():
        pass

    # __all__ now contains ['my_public_function', 'MyPublicClass']
"""


def exporter():
    """
    Create an easy export decorator with __all__

    :return: tuple export, __all__, to be set in the module
    """

    all_ = []

    def decorator(obj):
        all_.append(obj.__name__)
        return obj
    return decorator, all_
