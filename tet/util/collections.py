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
