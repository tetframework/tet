"""
Safe JSON encoding for embedding in HTML/JavaScript.

This module provides a JSON encoder that escapes characters that could
cause issues when embedding JSON in HTML or JavaScript contexts.

The following characters are escaped:

- ``<``, ``>``, ``/``, ``&`` - Prevents XSS via script injection
- ``\\u2028``, ``\\u2029`` - Line/paragraph separators that break JS strings

Example
-------

Safe embedding in HTML::

    from tet.util.json import js_safe_dumps

    data = {"name": "<script>alert('xss')</script>"}
    safe_json = js_safe_dumps(data)
    # Returns: {"name": "\\u003cscript\\u003ealert('xss')\\u003c/script\\u003e"}

In a template::

    <script>
        var config = ${js_safe_dumps(config_data) | n};
    </script>
"""
import json
import re

subs = {
    '\u2028': '\\u2028',
    '\u2029': '\\u2029',
    '<'     : '\\u003c',
    '>'     : '\\u003e',
    '/'     : '\\u002f',
    '&'     : '\\u0026',
}


rep = re.compile('[{}]'.format(''.join(subs.keys())))


def js_safe_dumps(s):
    rv = json.dumps(s)
    return rep.sub(lambda m: subs.get(m.group(0) or m.group(0)), rv)
