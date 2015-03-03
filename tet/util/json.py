import re
import json

subs = {
    u'\u2028': u'\\u2028',
    u'\u2029': u'\\u2029',
    u'<'     : u'\\u003c',
    u'>'     : u'\\u003e',
    u'/'     : u'\\u002f',
    u'&'     : u'\\u0026',
}

rep = re.compile(u'[{}]'.format(''.join(subs.keys())))

def js_safe_dumps(s):
    rv = json.dumps(s)
    return rep.sub(lambda m: subs.get(m.group(0) or m.group(0)), rv)
