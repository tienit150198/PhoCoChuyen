#!/usr/bin/env python3
"""English language pack builder.

Vietnamese is the source language everywhere; the browser swaps visible text
through public/i18n/en.json (see public/js/v4/i18n.js). This script:

  extract   collect every Vietnamese string the player can see (Python AST +
            JS/HTML literals), write i18n/source.json and split what is not
            translated yet into i18n/todo/part-NN.json for translators.
  merge     read filled i18n/todo/*.json, add them to i18n/translations.json.
  build     write public/i18n/en.json from translations for current sources.
  status    print coverage.

Strings built from pieces (f-strings, "a" + x, `${x} xu`) become patterns:
the Vietnamese template uses $1, $2 … for the variable parts, and the English
template must keep the same $n markers.
"""
from __future__ import annotations

import argparse
import ast
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / 'i18n'
TODO = I18N / 'todo'
DONE = I18N / 'done'
SOURCE = I18N / 'source.json'
MEMORY = I18N / 'translations.json'
OUT = ROOT / 'public' / 'i18n' / 'en.json'

VI = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]', re.I)
PH = '\x00'  # placeholder marker while scanning
WS = re.compile(r'\s+')
TAG = re.compile(r'<[^<>]*>')
FIELD = re.compile(r'\{[a-z_]+\}')
ATTR = re.compile(r'''\b(?:aria-label|placeholder|title|alt|data-tip)="([^"$]*(?:\x00[^"$]*)*)"''')


def norm(s: str) -> str:
    return WS.sub(' ', s).strip()


def has_vi(s: str) -> bool:
    return bool(VI.search(s))


class Collector:
    def __init__(self):
        self.strings: dict[str, str] = {}   # vi -> where
        self.patterns: dict[str, str] = {}  # vi template ($n) -> where

    def text(self, s: str, where: str, markup: bool = True):
        s = norm(html.unescape(s))
        if not s or not has_vi(s):
            return
        if PH in s:
            self.template(s, where, markup)
        else:
            self.strings.setdefault(s, where)

    def template(self, s: str, where: str, markup: bool = True):
        if markup:
            # JS/HTML: an edge ${…} is often an icon or a button, not text.
            # Drop leading/trailing placeholders + separators: "${a} · Tên ${b}" -> "Tên $1"
            s = re.sub(r'^[\x00\s·•|,:;–—-]+', '', s)
            s = re.sub(r'[\x00\s·•|,:;–—(-]+$', '', s) if s.rstrip().endswith(PH) and not re.search(r'\w\s*\x00\s*$', s) else s
        else:
            # Python and data text is plain: keep the whole template ("{a} báo
            # phải thu {b}") and only drop a value split off by a separator.
            s = re.sub(r'^\x00\s+[·•|–—]\s+', '', s)
            s = re.sub(r'\s+[·•|–—]\s+\x00$', '', s)
        s = norm(s)
        if not s or not has_vi(s.replace(PH, '')):
            return
        if PH not in s:
            self.strings.setdefault(s, where)
            return
        # Static pieces on their own are often full phrases too.
        n = 0

        def number(_):
            nonlocal n
            n += 1
            return f'${n}'
        tpl = re.sub(PH, number, s)
        self.patterns.setdefault(tpl, where)


# ------------------------------------------------------------------ Python
class PyVisitor(ast.NodeVisitor):
    def __init__(self, col: Collector, where: str):
        self.col, self.where = col, where

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            for line in node.value.split('\n'):
                # str.format templates ("… {note}.") are filled at runtime.
                self.col.text(FIELD.sub(PH, line), f'{self.where}:{node.lineno}', markup=False)

    def visit_JoinedStr(self, node):
        parts = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            else:
                parts.append(PH)
                self.visit(v.value)
        self.col.text(''.join(parts), f'{self.where}:{node.lineno}', markup=False)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Add):
            flat = []

            def walk(n):
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                    walk(n.left)
                    walk(n.right)
                else:
                    flat.append(n)
            walk(node)
            if any(isinstance(x, ast.Constant) and isinstance(x.value, str) and has_vi(x.value) for x in flat) and \
                    any(not (isinstance(x, ast.Constant)) for x in flat):
                parts = []
                for x in flat:
                    if isinstance(x, ast.Constant) and isinstance(x.value, str):
                        parts.append(x.value)
                    elif isinstance(x, ast.JoinedStr):
                        parts.append(''.join(str(v.value) if isinstance(v, ast.Constant) else PH for v in x.values))
                    else:
                        parts.append(PH)
                self.col.text(''.join(parts), f'{self.where}:{node.lineno}', markup=False)
        self.generic_visit(node)


def scan_python(col: Collector):
    files = sorted((ROOT / 'game').rglob('*.py')) + [ROOT / 'server.py']
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        try:
            tree = ast.parse(f.read_text(encoding='utf-8'), rel)
        except SyntaxError as e:
            print('skip', rel, e, file=sys.stderr)
            continue
        # Docstrings and comments are not player-facing.
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                    first.value.value = ''
        PyVisitor(col, rel).visit(tree)


# Reference data that game/content.py loads and ships to the player.
REFERENCE_FILES = ('catalog_16_careers.json', 'npcs_24.json', 'events_96.json', 'quests_12.json')


def scan_reference(col: Collector):
    def walk(x, where):
        if isinstance(x, str):
            for line in x.split('\n'):
                col.text(FIELD.sub(PH, line), where, markup=False)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v, where)
        elif isinstance(x, list):
            for v in x:
                walk(v, where)
    for name in REFERENCE_FILES:
        walk(json.loads((ROOT / 'reference' / 'data' / name).read_text(encoding='utf-8')), f'reference/data/{name}')


# ------------------------------------------------------------------ JavaScript
REGEX_BEFORE = set('(,=:[!&|?{};+-*%<>~^')
REGEX_WORDS = {'return', 'typeof', 'case', 'in', 'of', 'delete', 'void', 'throw', 'new', 'yield', 'await'}


def js_literals(src: str):
    """Yield (kind, text) for string and template literals. Template text has
    ${…} replaced by PH; nested literals inside ${…} are yielded too."""
    i, n = 0, len(src)
    last = ''   # last significant char
    word = ''   # last identifier
    while i < n:
        ch = src[i]
        if ch in ' \t\r\n':
            i += 1
            continue
        if src.startswith('//', i):
            j = src.find('\n', i)
            i = n if j < 0 else j
            continue
        if src.startswith('/*', i):
            j = src.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if ch in '\'"':
            j, buf = i + 1, []
            while j < n and src[j] != ch:
                if src[j] == '\\' and j + 1 < n:
                    buf.append(_unescape(src[j:j + 2]))
                    j += 2
                    continue
                buf.append(src[j])
                j += 1
            yield 'str', ''.join(buf)
            i, last, word = j + 1, ch, ''
            continue
        if ch == '`':
            text, i = _template(src, i + 1)
            yield from text
            last, word = '`', ''
            continue
        if ch == '/' and (last == '' or last in REGEX_BEFORE or word in REGEX_WORDS):
            j, cls = i + 1, False
            while j < n:
                c = src[j]
                if c == '\\':
                    j += 2
                    continue
                if c == '[':
                    cls = True
                elif c == ']':
                    cls = False
                elif c == '/' and not cls:
                    break
                elif c == '\n':
                    break
                j += 1
            i = j + 1
            while i < n and src[i].isalpha():
                i += 1
            last, word = '/', ''
            continue
        if ch.isalnum() or ch in '_$':
            j = i
            while j < n and (src[j].isalnum() or src[j] in '_$'):
                j += 1
            word, last = src[i:j], 'a'
            i = j
            continue
        last, word = ch, ''
        i += 1


def _unescape(esc: str) -> str:
    return {'\\n': '\n', '\\t': ' ', "\\'": "'", '\\"': '"', '\\\\': '\\', '\\`': '`'}.get(esc, esc[1:])


def _template(src: str, i: int):
    """Parse a template literal starting after the backtick."""
    out, buf, n = [], [], len(src)
    while i < n:
        ch = src[i]
        if ch == '\\' and i + 1 < n:
            buf.append(_unescape(src[i:i + 2]))
            i += 2
            continue
        if ch == '`':
            out.insert(0, ('tpl', ''.join(buf)))
            return out, i + 1
        if src.startswith('${', i):
            depth, j = 1, i + 2
            start = j
            while j < n and depth:
                c = src[j]
                if c in '\'"':
                    q, j = c, j + 1
                    while j < n and src[j] != q:
                        j += 2 if src[j] == '\\' else 1
                elif c == '`':
                    _, j = _template(src, j + 1)
                    continue
                elif c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                j += 1
            out.extend(js_literals(src[start:j - 1]))
            buf.append(PH)
            i = j
            continue
        buf.append(ch)
        i += 1
    out.insert(0, ('tpl', ''.join(buf)))
    return out, n


def split_markup(col: Collector, text: str, where: str):
    for m in ATTR.finditer(text):
        col.text(m.group(1), where)
    for chunk in TAG.split(text):
        # A chunk that still contains a quote-y attribute fragment is code, not text.
        if '="' in chunk or chunk.count('<') or chunk.count('>'):
            chunk = re.split(r'[<>]', chunk)[-1] if '>' in chunk else chunk
            if '="' in chunk:
                continue
        col.text(chunk, where)


def scan_js(col: Collector):
    files = sorted((ROOT / 'public' / 'js').rglob('*.js')) + [ROOT / 'public' / 'sw.js']
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        src = f.read_text(encoding='utf-8')
        for kind, text in js_literals(src):
            if not has_vi(text):
                continue
            if '<' in text or kind == 'tpl':
                split_markup(col, text, rel)
            else:
                col.text(text, rel)


def scan_html(col: Collector):
    for f in [ROOT / 'public' / 'index.html']:
        rel = f.relative_to(ROOT).as_posix()
        text = f.read_text(encoding='utf-8')
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.S)
        text = re.sub(r'<meta[^>]*>', '', text)
        split_markup(col, text, rel)


# ------------------------------------------------------------------ commands
def load(path: Path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def never_shown() -> set:
    """Strings that exist in code but are never displayed (moderation word list)."""
    sys.path.insert(0, str(ROOT))
    from game.social import BANNED
    return set(BANNED)


def js_escape(text: str) -> str:
    """Escape for a JavaScript RegExp with the `u` flag (Python's re.escape also
    escapes spaces, '-', '#', '&'… which are syntax errors in unicode mode)."""
    return re.sub(r'[\\^$.*+?()[\]{}|/]', lambda m: '\\' + m.group(0), text)


def pattern_regex(tpl: str) -> str:
    parts = re.split(r'(\$\d+)', tpl)
    return ''.join('(.+?)' if re.fullmatch(r'\$\d+', p) else js_escape(p) for p in parts)


def extract(chunk: int):
    col = Collector()
    scan_python(col)
    scan_js(col)
    scan_html(col)
    scan_reference(col)
    for word in never_shown():
        col.strings.pop(word, None)
    I18N.mkdir(exist_ok=True)
    SOURCE.write_text(json.dumps(dict(strings=col.strings, patterns=col.patterns), ensure_ascii=False, indent=1), encoding='utf-8')
    mem = load(MEMORY, dict(strings={}, patterns={}))
    todo = [dict(vi=s, en='') for s in col.strings if not mem['strings'].get(s)]
    todo += [dict(vi=p, en='', pattern=True) for p in col.patterns if not mem['patterns'].get(p)]
    TODO.mkdir(exist_ok=True)
    for old in TODO.glob('part-*.json'):
        old.unlink()
    parts, cur, size = [], [], 0
    for item in todo:
        cur.append(item)
        size += len(item['vi'])
        if len(cur) >= chunk or size > chunk * 60:
            parts.append(cur)
            cur, size = [], 0
    if cur:
        parts.append(cur)
    for i, p in enumerate(parts, 1):
        (TODO / f'part-{i:02d}.json').write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'{len(col.strings)} strings, {len(col.patterns)} patterns; {len(todo)} to translate in {len(parts)} parts')


def merge():
    """Translators either fill "en" in i18n/todo/part-NN.json or write
    i18n/done/part-NN.json as {"<index>": "English"} (index into the todo list)."""
    mem = load(MEMORY, dict(strings={}, patterns={}))
    added = bad = 0
    for f in sorted(TODO.glob('part-*.json')):
        items = load(f, [])
        done = load(DONE / f.name, {})
        for i, item in enumerate(items):
            if not item.get('en') and isinstance(done.get(str(i)), str):
                item['en'] = done[str(i)]
        for item in items:
            vi, en = item.get('vi'), (item.get('en') or '').strip()
            if not vi or not en:
                continue
            if item.get('pattern'):
                if sorted(re.findall(r'\$\d+', vi)) != sorted(re.findall(r'\$\d+', en)):
                    print('placeholder mismatch:', f.name, vi, '=>', en, file=sys.stderr)
                    bad += 1
                    continue
                mem['patterns'][vi] = en
            else:
                if re.search(r'\$\d', en) and not re.search(r'\$\d', vi):
                    print('stray placeholder:', f.name, vi, '=>', en, file=sys.stderr)
                    bad += 1
                    continue
                mem['strings'][vi] = en
            added += 1
    for word in never_shown():
        mem['strings'].pop(word, None)
    MEMORY.write_text(json.dumps(mem, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8')
    print(f'merged {added} translations ({bad} rejected)')


SEGMENT = re.compile(r'\s+[·•|–—→]\s+')
SENTENCE = re.compile(r'(?<=[.!?…])\s+')


def _renumber(vi: str, en: str):
    """Placeholders of a segment renumbered $1.. in Vietnamese order, or None
    if the English segment does not carry exactly the same ones."""
    found = re.findall(r'\$(\d+)', vi)
    if sorted(found) != sorted(re.findall(r'\$(\d+)', en)) or len(set(found)) != len(found):
        return None
    table = {old: str(i) for i, old in enumerate(found, 1)}
    fix = lambda s: re.sub(r'\$(\d+)', lambda m: '$' + table[m.group(1)], s)
    return fix(vi), fix(en)


def expand(strings: dict, patterns: dict):
    """The UI often shows pieces of a translated string: one sentence of a
    tagline, the label before an HTML control ("Kiểu nhạc${…}"), or one
    " · " segment. Derive those pieces from existing pairs; never override."""
    add_s, add_p = {}, {}

    def pair(vi, en):
        vi, en = vi.strip(), en.strip()
        if not vi or not en or vi == en or not has_vi(re.sub(r'\$\d+', '', vi)):
            return
        if '$' in vi:
            r = _renumber(vi, en)
            if r and re.sub(r'\$\d+', '', r[0]).strip():
                add_p.setdefault(*r)
        elif '$' not in en:
            add_s.setdefault(vi, en)

    def split(vi, en, rx):
        a, b = rx.split(vi), rx.split(en)
        if len(a) > 1 and len(a) == len(b):
            for x, y in zip(a, b):
                pair(x, y)

    # (A sentence shown without its final period is handled in i18n.js.)
    for vi, en in list(strings.items()):
        split(vi, en, SENTENCE)
        split(vi, en, SEGMENT)
    for vi, en in list(patterns.items()):
        if not en:
            continue
        split(vi, en, SENTENCE)
        split(vi, en, SEGMENT)
        # Label followed or preceded by markup: "Kiểu nhạc$1" -> "Kiểu nhạc".
        if len(re.findall(r'\$\d+', vi)) == 1:
            for rx in (r'^(.*?)\s*\$\d+$', r'^\$\d+\s*(.*?)$'):
                a, b = re.match(rx, vi), re.match(rx, en)
                if a and b:
                    pair(a.group(1), b.group(1))
    for k, v in add_s.items():
        strings.setdefault(k, v)
    for k, v in add_p.items():
        patterns.setdefault(k, v)
    return len(add_s), len(add_p)


def titled(table: dict):
    """Teacher lines carry {Title}/{title} or "cô/thầy"; the server fills in the
    player's own title (Cô/Thầy) before sending, so add both filled-in keys."""
    for vi, en in list(table.items()):
        if not en:
            continue
        if '{Title}' in vi or '{title}' in vi:
            e = en.replace('{Title}', 'Teacher').replace('{title}', 'teacher')
            for big, small in (('Cô', 'cô'), ('Thầy', 'thầy')):
                table.setdefault(vi.replace('{Title}', big).replace('{title}', small), e)
        if 'cô/thầy' in vi.lower():
            for small, title in (('cô', 'Ms.'), ('thầy', 'Mr.')):
                table.setdefault(vi.replace('cô/thầy', small).replace('Cô/thầy', small.capitalize()), en.replace('Ms./Mr.', title))


def build():
    src = load(SOURCE, None)
    if src is None:
        sys.exit('run extract first')
    mem = load(MEMORY, dict(strings={}, patterns={}))
    skip = never_shown()
    strings = {k: mem['strings'][k] for k in src['strings'] if mem['strings'].get(k) and k not in skip}
    # Translations from earlier builds stay valid for runtime strings that the
    # scanner cannot see (content assembled at runtime).
    for k, v in mem['strings'].items():
        if k not in skip:
            strings.setdefault(k, v)
    # Hand-written fixes for short, context-dependent UI words win over the memory.
    over = load(I18N / 'overrides.json', dict(strings={}, patterns={}))
    strings.update(over.get('strings', {}))
    mem['patterns'].update(over.get('patterns', {}))
    expand(strings, mem['patterns'])
    titled(strings)
    titled(mem['patterns'])
    pats = [(k, v) for k, v in mem['patterns'].items() if v]
    # Longest literal first so specific templates win over generic ones.
    pats.sort(key=lambda kv: -len(re.sub(r'\$\d+', '', kv[0])))
    patterns = [[pattern_regex(k), v] for k, v in pats]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(strings=strings, patterns=patterns), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'wrote {OUT.relative_to(ROOT)}: {len(strings)} strings, {len(patterns)} patterns, {OUT.stat().st_size // 1024} KB')


def status():
    src = load(SOURCE, dict(strings={}, patterns={}))
    mem = load(MEMORY, dict(strings={}, patterns={}))
    s = sum(1 for k in src['strings'] if mem['strings'].get(k))
    p = sum(1 for k in src['patterns'] if mem['patterns'].get(k))
    print(f'strings {s}/{len(src["strings"])} · patterns {p}/{len(src["patterns"])}')


def check(part: str):
    """Validate i18n/done/part-NN.json against its todo list."""
    name = f'part-{int(part):02d}.json'
    items = load(TODO / name, [])
    done = load(DONE / name, {})
    problems = []
    for i, item in enumerate(items):
        en = done.get(str(i))
        if not isinstance(en, str) or not en.strip():
            problems.append(f'{i}: missing')
            continue
        want = sorted(re.findall(r'\$\d+', item['vi'])) if item.get('pattern') else []
        if sorted(re.findall(r'\$\d+', en)) != want:
            problems.append(f'{i}: placeholders {want} vs {en!r}')
        else:
            words = en.split()
            vi_words = [w for w in words if VI.search(w)]
            # Names keep diacritics; a mostly-Vietnamese sentence was probably skipped.
            if len(words) >= 3 and len(vi_words) > len(words) * 0.5:
                problems.append(f'{i}: still Vietnamese? {en!r}')
    extra = [k for k in done if not k.isdigit() or int(k) >= len(items)]
    print(f'{name}: {len(items)} items, {len(done)} translated, {len(problems)} problems, {len(extra)} unknown keys')
    for x in problems[:40]:
        print('  ', x)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('command', choices=['extract', 'merge', 'build', 'status', 'check'])
    ap.add_argument('part', nargs='?', help='part number for check')
    ap.add_argument('--chunk', type=int, default=450, help='items per todo part')
    a = ap.parse_args()
    dict(extract=lambda: extract(a.chunk), merge=merge, build=build, status=status, check=lambda: check(a.part or '1'))[a.command]()
