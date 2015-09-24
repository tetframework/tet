import warnings
import types

def _qualname(func):
    return getattr(func, '__qualname__', func.__name__)

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""

    def new_func(*args, **kwargs):
        warnings.warn("Call to deprecated function {}."
            .format(_qualname(func), category=DeprecationWarning, stacklevel=2)
        return func(*args, **kwargs)

    new_func.__name__ = func.__name__
    new_func.__doc__ = func.__doc__
    new_func.__dict__.update(func.__dict__)
    return new_func
