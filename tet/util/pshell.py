import os
import glob
import inspect


class SnippetAccess(object):
    def __init__(self, filename):
        self.filename = filename

    def __call__(self, *args, **kwargs):
        with open(self.filename, 'rb') as f:
            content = f.read()

        lcls = {}
        glbls = inspect.stack()[1][0].f_globals
        exec(content, glbls, lcls)
        return lcls['run'](*args, **kwargs)

    def __repr__(self):
        return 'Snippet: %s' % self.filename


def _list_paths(snippet_path):
    for file in glob.glob(os.path.join(snippet_path, '*.py')):
        mod = os.path.splitext(os.path.basename(file))[0]
        yield mod, file


class _Snippets(object):
    def __init__(self, env):
        self._env = env
        self._snippet_path = self._env['registry'].settings.get('tet.snippets')
        self._snippets = []
        if self._snippet_path:
            for mod, file in _list_paths(self._snippet_path):
                setattr(self, mod, SnippetAccess(file))
                self._snippets.append(mod)

    def __call__(self):
        print("Available snippets:")
        for i in sorted(self._snippets):
            print("  *", i)

    def __repr__(self):
        return 'Snippets access. call with () to list snippets'

def Snippets(snippet_path):
    class Snippets(_Snippets):
        pass

    return Snippets(snippet_path)
