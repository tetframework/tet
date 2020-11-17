import re
import json

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
