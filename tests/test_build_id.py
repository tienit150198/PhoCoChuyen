"""engine.BUILD: the fingerprint of the code that migrates and validates saves (game/build_id.py)."""
import ast
import os
import re
import subprocess
import sys
import unittest
from unittest import mock

from game import build_id as bid
from game import engine
from game.content import CAREERS

GAME = os.path.dirname(bid.__file__)


def sources():
    for folder, dirs, files in os.walk(GAME):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for name in files:
            if name.endswith('.py'):
                path = os.path.join(folder, name)
                with open(path, encoding='utf-8') as fh:
                    yield os.path.relpath(path, GAME), fh.read()


class BuildIdTests(unittest.TestCase):
    def test_build_is_the_hash_of_the_import_closure(self):
        self.assertEqual(engine.BUILD, bid.build_id(CAREERS))
        self.assertRegex(engine.BUILD, r'^[0-9a-f]{20}$')

    def test_closure_holds_what_migration_and_validation_use(self):
        closure = bid.closure()
        for name in ('engine', 'content', 'operations', 'workplace_business', 'journey', 'whats_new', 'careers',
                     'experiences', 'inventory', 'employment', 'desk', 'archive', ''):
            self.assertIn(name, closure)
        careers = {m for m in bid._modules() if m.startswith('careers.')}
        self.assertTrue(careers and careers <= set(closure))  # careers/__init__ imports them by name

    def test_every_game_module_loaded_by_migrate_and_validate_is_hashed(self):
        code = ('import sys,json\n'
                'from game import engine\n'
                's=engine.new_state();engine.validate_state(engine.migrate_state(json.loads(json.dumps(s))))\n'
                'print(json.dumps(sorted(m[5:] for m in sys.modules if m.startswith("game."))))')
        out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True,
                             cwd=os.path.dirname(GAME))
        loaded = set(__import__('json').loads(out.stdout.strip().splitlines()[-1]))
        self.assertEqual(loaded - set(bid.closure()) - {'build_id'}, set())

    def test_the_scan_follows_every_import_form(self):
        mods = {'': 'x/__init__.py', 'a': 'x/a.py', 'b': 'x/b.py', 'pkg': 'x/pkg/__init__.py', 'pkg.c': 'x/pkg/c.py', 'd': 'x/d.py'}
        text = ('from . import a, b as bee\n'
                'def f():\n    from .pkg import c\n    import game.d\n'
                'from game import (\n    a,\n)\n')
        self.assertEqual(bid.imports('e', 'x/e.py', text, mods), {'a', 'b', 'pkg', 'pkg.c', 'd', ''})
        self.assertEqual(bid.imports('pkg.c', 'x/pkg/c.py', 'from ..a import x\nfrom . import c\n', mods), {'a', 'pkg', 'pkg.c', ''})

    def test_a_version_bump_alone_keeps_the_build(self):
        with open(os.path.join(GAME, '__init__.py'), 'rb') as fh:
            init = fh.read()
        tree = ast.parse(init)
        # game/__init__.py is the release number only (and its docstring)
        self.assertEqual([type(n).__name__ for n in tree.body], ['Expr', 'Assign'])
        self.assertEqual(tree.body[1].targets[0].id, '__version__')
        bumped = bid._VERSION.sub(b'', init.replace(b'__version__ = "', b'__version__ = "9.'), count=1)
        self.assertEqual(bumped, bid._VERSION.sub(b'', init, count=1))
        self.assertNotIn(b'__version__', bumped)
        real = open

        def fake(path, *a, **k):
            fh = real(path, *a, **k)
            if os.path.abspath(str(path)) == os.path.join(GAME, '__init__.py'):
                data = fh.read().replace(b'__version__ = "', b'__version__ = "9.')
                fh.close()
                import io
                return io.BytesIO(data)
            return fh
        with mock.patch('builtins.open', fake):
            self.assertEqual(bid.build_id(CAREERS), engine.BUILD)
        with mock.patch.object(bid, 'SAVE_EPOCH', bid.SAVE_EPOCH + 1):
            self.assertNotEqual(bid.build_id(CAREERS), engine.BUILD)

    def test_release_number_is_read_only_by_admin_statistics(self):
        users = {name for name, text in sources() if re.search(r'\b__version__\b', text)} - {'__init__.py', 'whats_new.py', 'build_id.py'}
        self.assertEqual(users, {'admin_kpi.py', 'admin_stats.py'})
        # whats_new.py names it in its docstring only
        with open(os.path.join(GAME, 'whats_new.py'), encoding='utf-8') as fh:
            tree = ast.parse(fh.read())
        self.assertFalse(any(isinstance(n, ast.Name) and n.id == '__version__' for n in ast.walk(tree)))

    def test_no_other_dynamic_import_of_game_modules(self):
        hits = {name for name, text in sources() if re.search(r'\bimport_module\b|\b__import__\s*\(\s*[\'"](?:game|\.)|importlib', text)}
        self.assertEqual(hits - {'build_id.py'}, {os.path.join('careers', '__init__.py')})  # build_id: its docs


if __name__ == '__main__':
    unittest.main()
