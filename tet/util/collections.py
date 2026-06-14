"""
Collection utilities for Tet applications.

This module provides utility functions for working with collections.

Example
-------

Flattening nested iterables::

    from tet.util.collections import flatten

    nested = [1, [2, 3, [4, 5]], 6]
    flat = list(flatten(nested))
    # flat == [1, 2, 3, 4, 5, 6]

    # Strings are not exploded
    with_strings = ["hello", ["world", ["!"]]]
    flat = list(flatten(with_strings))
    # flat == ["hello", "world", "!"]
"""
from collections.abc import Iterable


def flatten(l):
    """
    Flattens a deeply nested iterable, but does not explode
    str, bytes. From http://stackoverflow.com/a/2158532/

    :param l: the list
    :return: a generator of flattened items
    """

    for el in l:
        if isinstance(el, Iterable) and not isinstance(el, (str, bytes)):
            for sub in flatten(el):
                yield sub
        else:
            yield el
