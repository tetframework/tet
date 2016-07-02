import sys
from itertools import count

from pyramid.path import caller_module


def caller_package(ignored_modules=(), caller_module=caller_module):
    ignored_modules = set(ignored_modules)
    ignored_modules.add(__name__)
    for i in count(3):
        # caller_module in arglist for tests
        module = caller_module(i)
        if getattr(module, '__name__', '__main__') in ignored_modules:
            continue

        f = getattr(module, '__file__', '')
        if f.endswith(('__init__.py', '__init__$py')):  # empty at >>>
            # Module is a package
            return module

        # Go up one level to get package
        package_name = module.__name__.rsplit('.', 1)[0]
        return sys.modules[package_name]
