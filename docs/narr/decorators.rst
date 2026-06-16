==========================
Decorators and Descriptors
==========================

The :mod:`tet.decorators` module collects a small set of general-purpose
helpers that are useful throughout a Tet application: a decorator for marking
APIs as deprecated and a reify-style cached-property descriptor that is aware
of the attribute name it is bound to.

Both helpers are importable directly from the package:

.. code-block:: python

    from tet.decorators import deprecated, reify_attr

The module is deliberately tiny and dependency-free, so it is safe to use in
library code, models, services, and views alike.


``deprecated``
--------------

:func:`deprecated` is a function decorator that marks a callable as
deprecated. The wrapped function continues to work exactly as before, but
every call now emits a :class:`DeprecationWarning` before delegating to the
original implementation.

Use it when you want to retire a function or method but cannot remove it yet
because callers still depend on it. The warning gives downstream code a clear
signal (and, in test suites that turn warnings into errors, a hard failure)
without breaking runtime behaviour.

Signature
~~~~~~~~~

.. code-block:: python

    deprecated(func)

It takes a single callable and returns a wrapper with the same name,
docstring, and ``__dict__`` as the original. The warning message is built from
the function's ``__qualname__``, so it correctly identifies methods nested in
classes (e.g. ``MyService.old_method``).

Behaviour
~~~~~~~~~

When the wrapped function is called, it issues:

.. code-block:: text

    Call to deprecated function <qualname>.

The warning is raised with ``stacklevel=2``, which means the warning is
attributed to the *caller* of the deprecated function rather than to the
wrapper inside :mod:`tet.decorators`. That makes the warning point at the line
of code that actually needs to change.

.. note::

   Python silences :class:`DeprecationWarning` by default outside of
   ``__main__`` and test runners. To see the warnings during development, run
   Python with ``-W default::DeprecationWarning`` or configure the
   :mod:`warnings` filter explicitly. Most test runners (including pytest)
   surface these warnings out of the box.

Example
~~~~~~~

.. code-block:: python

    from tet.decorators import deprecated


    @deprecated
    def render_legacy_template(name):
        """Old rendering path; use render_template() instead."""
        return _legacy_render(name)


    # Calling it still works, but emits:
    #   DeprecationWarning: Call to deprecated function render_legacy_template.
    html = render_legacy_template("home")

It works equally well on methods, where ``__qualname__`` produces a fully
qualified name in the warning:

.. code-block:: python

    class ReportService:
        @deprecated
        def export_csv(self, report):
            # Warning text: "Call to deprecated function ReportService.export_csv."
            return self._export(report, fmt="csv")


``reify_attr``
--------------

:class:`reify_attr` is a cached-property descriptor. The first time the
attribute is accessed on an instance, the wrapped function is called and its
return value is computed; that value is then written back onto the instance so
that subsequent accesses read a plain attribute and never call the function
again.

It is similar in spirit to Pyramid's ``pyramid.decorator.reify``, but with one
key difference: ``reify_attr`` caches under the *name the descriptor is bound
to on the class*, not the name of the decorated method. This matters when the
descriptor is assigned to an attribute whose name differs from the wrapped
function, or assigned dynamically. It is intended as a building block for
descriptors such as ``autowired`` in ``pyramid_di``, which need to know their
own attribute name in order to cache the resolved value on the instance.

Signature
~~~~~~~~~

.. code-block:: python

    class reify_attr:
        def __init__(self, wrapped): ...

It is used as a decorator on a method that takes ``self`` and returns the
value to cache. The descriptor copies the wrapped function's metadata via
:func:`functools.update_wrapper`.

How caching and name resolution work
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Name discovery via ``__set_name__``:** when the descriptor is created as
  part of a class body, Python calls ``__set_name__`` and ``reify_attr``
  records the attribute name (or names, if the same descriptor object is bound
  to several attributes).
- **Fallback discovery:** if ``__set_name__`` was never called (for example,
  the descriptor was attached to the class dynamically after definition), the
  name is discovered lazily on first access by scanning the owner class's
  ``__dict__`` for the attributes that point at this descriptor.
- **Write-back on access:** on first ``__get__`` for an instance, the wrapped
  function is invoked and the result is stored on the instance under every
  resolved name via :func:`setattr`. Because instance attributes shadow class
  descriptors for non-data descriptors, later accesses return the cached value
  directly without invoking the function again.
- **Class access:** accessing the attribute on the class itself (``inst`` is
  ``None``) returns the descriptor object rather than computing a value.

.. note::

   ``reify_attr`` is a *non-data* descriptor (it defines ``__get__`` but not
   ``__set__``), which is exactly what allows the instance attribute written on
   first access to take precedence on subsequent reads. If you need to force
   recomputation, delete the cached instance attribute (``del inst.name``).

Example
~~~~~~~

.. code-block:: python

    from tet.decorators import reify_attr


    class Report:
        def __init__(self, rows):
            self.rows = rows

        @reify_attr
        def summary(self):
            # Computed once, then cached on the instance as `summary`.
            print("computing summary...")
            return {
                "count": len(self.rows),
                "total": sum(r.amount for r in self.rows),
            }


    report = Report(load_rows())
    report.summary   # prints "computing summary..." and computes the dict
    report.summary   # returns the cached dict; no print, no recompute

Because caching uses the bound attribute name, you can rely on the cached value
living under the attribute you actually access, which is what makes it suitable
for descriptor-composition patterns like dependency-injection ``autowired``
fields.


See also
--------

- :doc:`utilities` -- the broader set of helper utilities in ``tet.util``
  (cryptography, base64, collections, paths, and JSON helpers).
- :doc:`configuration` -- configuring a Tet application and including Tet
  components via ``config.include(...)``.
