import warnings
from functools import update_wrapper


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    def new_func(*args, **kwargs):
        warnings.warn(
            "Call to deprecated function {}."
            .format(func.__qualname__, category=DeprecationWarning, stacklevel=2))

        return func(*args, **kwargs)

    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func


class reify_attr(object):
    """
    reify_attr is like pyramid reify, but instead of getting the name of the
    attribute from the decorated method, it uses the name of actual attribute,
    by finding it on the class in Python <=3.5, and using the ``__set_name__``
    on Python 3.6.
    """
    def __init__(self, wrapped):
        self.wrapped = wrapped
        update_wrapper(self, wrapped)
        self.names = None

    def __get__(self, inst, objtype=None):
        if inst is None:
            return self

        val = self.wrapped(inst)
        if self.names is None:
            names = []
            for name, value in list(objtype.__dict__.items()):
                if value is self:
                    names.append(name)

            self.names = names

        for name in self.names:
            setattr(inst, name, val)

        return val

    def __set_name__(self, owner, name):
        if self.names is None:
            self.names = [name]
        else:
            self.names.append(name)
