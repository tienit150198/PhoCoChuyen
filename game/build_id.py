"""The build fingerprint stamped on saves (engine.BUILD, state["check"]["build"]).

A save stamped with BUILD was migrated and fully validated by this code: migrate_state returns
it as it is, and a command on it re-validates only what it changed (game/storage.py). So BUILD
must change whenever the code that migrates or validates a save could behave differently, and
should not change otherwise: every new BUILD makes the first command of every save after the
deploy a full load (migrate + validate of all 41 careers), the most expensive command there is.
Until 1.7.15 BUILD hashed every file of game/, so every deploy that touched game/ did that.

BUILD is the SHA-256 of:
* SAVE_EPOCH: bump it to force a full migration + validation of every save without a code change;
* the career list (CAREERS, passed in by engine);
* every module of game/ that engine.py can import, transitively: module-level imports and the
  imports inside functions, and every module of a package that loads its modules by name
  (game/careers/__init__.py uses importlib). migrate_state, validate_state, validate_career and
  everything they can call live there, the content tables the validators regenerate tasks from
  included (scripts/check_task_compat.py stays the release gate for those);
* game/__init__.py without its `__version__ = "..."` line: the release number is read only by
  admin statistics (tests/test_build_id.py keeps it so), so a version bump alone keeps BUILD.

Left out: modules engine cannot import at all (the admin users page, the board AI, dialogue and
guide content, observability, state_delta, TikTok login, web assets, this module). A finer cut
(only the functions migrate/validate can reach) is not sound here: a syntax-tree walk that
follows plugin hooks (PLUGINS[cid].validate_data, mod.heal_save), getattr names and dispatch
tables reaches 11,481 of the 11,824 module-level definitions of game/ from those four functions.

The import scan is textual (_IMPORT): anything that looks like an import of a game module counts,
even in a comment or a string. That can only add modules, never miss one. Dynamic imports of
game modules exist only in game/careers/__init__.py (see above); tests/test_build_id.py keeps it so.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets

SAVE_EPOCH = 1
ROOT = os.path.dirname(os.path.abspath(__file__))
ENTRY = 'engine'
PACKAGE = ''  # game/__init__.py in the module map

# `from . import a, b as c`, `from .x import y`, `from ..x import y`, `from game.x import y`,
# `from game import x`, `import game.x`. Parenthesised name lists may span lines.
_IMPORT = re.compile(r'^[ \t]*(?:from[ \t]+(\.+|game\b\.?)([\w.]*)[ \t]+import[ \t]+(\([^)]*\)|[^\n#;]+)'
                     r'|import[ \t]+(game\.[\w.]+(?:[ \t]*,[ \t]*[\w.]+)*))', re.M)
_VERSION = re.compile(rb'^__version__[ \t]*=[ \t]*"[^"\n]*"[ \t]*\r?\n', re.M)


def _modules() -> dict:
    """{dotted name relative to game/ ('' for game/__init__.py): file path}."""
    out = {}
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d != '__pycache__')
        for name in sorted(files):
            if name.endswith('.py'):
                rel = os.path.relpath(os.path.join(folder, name), ROOT)[:-3].replace(os.sep, '.')
                key = PACKAGE if rel == '__init__' else rel[:-len('.__init__')] if rel.endswith('.__init__') else rel
                out[key] = os.path.join(folder, name)
    return out


def imports(name: str, path: str, text: str, mods: dict) -> set:
    """Game modules a module's source may import (textual, see the module doc)."""
    package = name if path.endswith('__init__.py') else name.rpartition('.')[0]
    found = set()
    for m in _IMPORT.finditer(text):
        dots, base, names, plain = m.groups()
        if plain:
            for part in plain.split(','):
                mod = part.strip().split(' ')[0]
                mod = mod[len('game.'):] if mod.startswith('game.') else mod
                while mod:
                    if mod in mods:
                        found.add(mod)
                    mod = mod.rpartition('.')[0]
            continue
        if dots.startswith('game'):
            parts = [p for p in base.split('.') if p]
        else:
            up = len(dots) - 1
            pkg = [p for p in package.split('.') if p]
            parts = (pkg[:len(pkg) - up] if up else pkg) + [p for p in base.split('.') if p]
        head = '.'.join(parts)
        if head in mods:
            found.add(head)
        for item in names.strip('()').replace('\n', ' ').split(','):
            item = item.strip().split(' ')[0]
            sub = (head + '.' + item) if head else item
            if item and sub in mods:
                found.add(sub)
        while head:  # importing a package's module runs the package's __init__ too
            head = head.rpartition('.')[0]
            if head in mods:
                found.add(head)
    return found


def closure(entry: str = ENTRY) -> dict:
    """{module: source bytes} of `entry` and every game module it can import, transitively."""
    mods = _modules()
    seen, stack = {}, [entry, PACKAGE]  # importing game.engine runs game/__init__.py first
    while stack:
        name = stack.pop()
        if name in seen or name not in mods:
            continue
        with open(mods[name], 'rb') as fh:
            data = fh.read()
        seen[name] = data
        stack.extend(imports(name, mods[name], data.decode('utf-8', 'replace'), mods) - set(seen))
        if mods[name].endswith('__init__.py') and name != PACKAGE:  # a package may load its modules by name
            stack.extend(m for m in mods if m.startswith(name + '.') and m not in seen)
    return seen


def build_id(careers) -> str:
    """Fingerprint of the save-shaping code (see the module doc)."""
    h = hashlib.sha256(f'epoch:{SAVE_EPOCH}\0'.encode() + ','.join(careers).encode() + b'\0')
    try:
        for name, data in sorted(closure().items()):
            if name == PACKAGE:
                data = _VERSION.sub(b'', data, count=1)
            h.update(name.encode() + b'\0' + data + b'\0')
    except OSError:
        return 'unknown-' + secrets.token_hex(8)  # never matches: always the full migrate + validation
    return h.hexdigest()[:20]
