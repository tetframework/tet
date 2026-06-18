=========
Utilities
=========

Tet provides a small set of focused utility modules under ``tet.util`` to
handle common tasks in web applications.

Cryptographic Utilities
========================

The ``tet.util.crypt`` module provides password hashing built on top of
passlib's SHA-256 crypt scheme.

Password Hashing
----------------

Two functions are exposed: ``crypt`` to hash a password and ``verify`` to
check a plaintext password against an existing hash. Both accept either
``str`` or ``bytes`` for the password.

.. code-block:: python

    from tet.util.crypt import crypt, verify

    # Hash a password
    hashed = crypt("my_secret_password")

    # Verify a password
    if verify("my_secret_password", hashed):
        print("Password is correct!")

Hashing uses ``passlib.hash.sha256_crypt`` (exposed as the module-level
``password_hash``), which handles salting automatically. For SQLAlchemy
models, consider ``tet.sqlalchemy.password.UserPasswordMixin``, which
integrates this functionality directly into your model.

Base64 and Crockford Base32 Utilities
======================================

The ``tet.util.base64`` module provides two codec classes, ``Base64`` and
``CrockfordBase32``, both deriving from ``BaseCodec``. Each codec exposes
``encode``, ``decode`` and ``normalize`` classmethods, plus a
``generate_characters`` classmethod inherited from ``BaseCodec``.

Standard Base64
---------------

.. code-block:: python

    from tet.util.base64 import Base64

    encoded = Base64.encode(b"hello")  # returns bytes
    decoded = Base64.decode(encoded)  # returns b"hello"

``Base64.encode`` wraps :func:`base64.b64encode` and returns ``bytes``;
``Base64.decode`` wraps :func:`base64.b64decode`. ``Base64.normalize`` is a
no-op that returns its argument unchanged. The class attributes are
``Base64.chars`` (a ``str`` of the 64-character alphabet,
``string.ascii_letters + string.digits + "+/"``), ``bits_per_char = 6`` and
``padding = True``.

Crockford Base32
----------------

Crockford's Base32 is a human-friendly encoding that avoids ambiguous
characters (``0``/``O`` and ``1``/``I``/``L``). It is case-insensitive on
decode and tolerates common transcription mistakes.

.. code-block:: python

    from tet.util.base64 import CrockfordBase32

    encoded = CrockfordBase32.encode(b"hello")  # returns str
    decoded = CrockfordBase32.decode(encoded)  # returns bytes

    # Ambiguous characters are normalized: O -> 0, I/L -> 1
    CrockfordBase32.normalize("O1L")  # "011"

``CrockfordBase32.encode`` accepts ``str`` or ``bytes`` and returns a ``str``
with any ``=`` padding stripped. ``CrockfordBase32.decode`` normalizes its
input by default (pass ``normalize=False`` to skip that), re-adds the
mandatory padding, and returns ``bytes``. ``CrockfordBase32.normalize``
translates the ambiguous characters and upper-cases the input. The class
attributes are ``CrockfordBase32.chars``
(``"0123456789ABCDEFGHJKMNPQRSTVWXYZ"``, a ``str``), ``bits_per_char = 5``
and ``padding = False``.

Generating Random Characters
----------------------------

``BaseCodec.generate_characters`` produces a random string of the requested
length using the codec's own alphabet, drawn from a cryptographically secure
source:

.. code-block:: python

    from tet.util.base64 import Base64, CrockfordBase32

    # 16 random Base64 characters
    token = Base64.generate_characters(16)

    # 26 random Crockford Base32 characters (good for IDs / tokens)
    ident = CrockfordBase32.generate_characters(26)

Internally it generates ``ceil(length * bits_per_char / 8)`` random bytes
with :func:`secrets.token_bytes`, runs them through the codec's ``encode``,
and truncates the result to ``length`` characters. Because any padding only
trails the data, the truncated slice never contains padding. A non-positive
``length`` returns an empty string.

Collection Utilities
====================

The ``tet.util.collections`` module provides a single helper, ``flatten``.

Flattening Nested Iterables
---------------------------

``flatten`` is a generator that recursively flattens an arbitrarily nested
iterable. ``str`` and ``bytes`` are treated as atomic values and are never
exploded into their characters.

.. code-block:: python

    from tet.util.collections import flatten

    nested = [1, [2, 3, [4, 5]], 6]
    list(flatten(nested))  # [1, 2, 3, 4, 5, 6]

    with_strings = ["hello", ["world", ["!"]]]
    list(flatten(with_strings))  # ["hello", "world", "!"]

Path Utilities
==============

The ``tet.util.path`` module provides ``caller_package``, used internally by
Tet's configuration system to determine which package called into the
framework.

Determining the Calling Package
-------------------------------

.. code-block:: python

    from tet.util.path import caller_package

    # The package module of the code that called the current function
    pkg = caller_package()

    # Skip additional modules when walking the stack
    pkg = caller_package(ignored_modules=("myframework.helpers",))

``caller_package`` walks up the call stack (starting a few frames up, and
always ignoring ``tet.util.path`` itself), skipping any module whose name is
in ``ignored_modules``. When it reaches the first non-ignored module it
returns that module if it is itself a package (its ``__file__`` ends in
``__init__.py``), otherwise it returns the package that contains the module.
It builds on Pyramid's ``pyramid.path.caller_module``, which can also be
overridden via the ``caller_module`` keyword argument for testing.

Export Utilities
================

The ``tet.util.export`` module provides ``exporter``, a small helper for
maintaining a module's ``__all__`` via a decorator.

Maintaining ``__all__``
-----------------------

``exporter()`` returns a ``(decorator, list)`` tuple. Bind the list to your
module's ``__all__`` and apply the decorator to anything you want exported;
each decorated object's ``__name__`` is appended to ``__all__`` and the object
is returned unchanged.

.. code-block:: python

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


    # __all__ == ["my_public_function", "MyPublicClass"]

Shell (pshell) Utilities
========================

The ``tet.util.pshell`` module provides snippet support for the Pyramid
``pshell`` interactive environment. A *snippet* is a ``.py`` file that defines
a ``run()`` function, which can then be invoked interactively.

Configuring Snippets
--------------------

Point the ``tet.snippets`` setting at a directory of snippet files in your INI
file:

.. code-block:: ini

    [app:main]
    tet.snippets = %(here)s/snippets

A snippet file ``snippets/create_user.py`` looks like:

.. code-block:: python

    def run(username, email):
        from myapp.models import User

        session = env["request"].dbsession
        user = User(username=username, email=email)
        session.add(user)
        return user

Using Snippets in pshell
------------------------

The ``Snippets`` factory builds a snippets-access object from an environment
mapping (the same ``env`` exposed in ``pshell``). Each ``.py`` file in the
configured directory becomes an attribute that, when called, executes that
file's ``run()`` function in the caller's globals:

.. code-block:: python

    from tet.util.pshell import Snippets

    snippets = Snippets(env)

    # List available snippets
    snippets()

    # Invoke snippets/create_user.py's run() function
    snippets.create_user("john", "john@example.com")

JSON Utilities
==============

The ``tet.util.json`` module provides ``js_safe_dumps`` for serializing data
to JSON that is safe to embed directly inside an HTML ``<script>`` element.

Safe Embedding in HTML/JavaScript
---------------------------------

``js_safe_dumps`` serializes its argument with :func:`json.dumps` and then
escapes the characters that are dangerous in an HTML/JS context. The escaped
characters are ``<``, ``>``, ``/`` and ``&`` (XSS-prevention), as well as the
Unicode line/paragraph separators `` `` and `` `` (which would
otherwise break JavaScript string literals).

.. code-block:: python

    from tet.util.json import js_safe_dumps

    data = {"name": "<script>alert('xss')</script>"}
    js_safe_dumps(data)
    # '{"name": "\\u003cscript\\u003ealert(\'xss\')\\u003c\\u002fscript\\u003e"}'

In a Tonnikala template, use ``$literal()`` so the already-escaped JSON is not
double-escaped:

.. code-block:: html

    <script>
        var config = $literal(js_safe_dumps(config_data));
    </script>

Best Practices
==============

**Use the secure codecs for tokens**
  Prefer ``CrockfordBase32.generate_characters`` / ``Base64.generate_characters``
  for identifiers and tokens; they draw from :mod:`secrets`.

**Hash passwords, never store them**
  Use ``crypt`` and ``verify`` (or ``UserPasswordMixin``) for password storage.

**Escape JSON destined for HTML**
  Use ``js_safe_dumps`` whenever JSON is embedded inside a ``<script>`` tag.
