"""🧭 The first-day coach (game/coach, public/js/tutorial/coach*.js): every workplace has its own walk, every
[[button]] of the guide's steps is either a step's control or shown as its words, the labels and selectors it rings
exist in the game, its words are short and have their English, the browser copy is current, the engine behaves
(tests/coach_engine.mjs with node), and its memory rides in settings.notesSeen, which the previous release accepts."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from game import coach as C
from game import guide_content as G
from game.careers import PLUGINS
from game.content import CAREERS as GAME_CAREERS
from game.engine import apply_action, new_state, validate_state, notes_seen

ROOT = Path(__file__).resolve().parents[1]
LABEL = re.compile(r'\[\[(.+?)\]\]')
GENERATED = ('guide_content.py', 'guide-content.js', 'coach-content.js')
ATTR = re.compile(r'\[data-([a-z-]+)="([^"]+)"\]')


def _source() -> str:
    parts = []
    for base, pattern in ((ROOT / 'public' / 'js', '*.js'), (ROOT / 'game', '*.py')):
        for f in base.rglob(pattern):
            if f.name in GENERATED or '__pycache__' in f.parts or 'coach' in f.parts:
                continue
            parts.append(f.read_text(encoding='utf-8', errors='replace'))
    return '\n'.join(parts)


SOURCE = _source()
EMOJI = re.compile(r'[\U0001F000-\U0001FAFF☀-➿️‍]')


def _plain(label: str) -> str:
    return EMOJI.sub('', label).strip()


class Coverage(unittest.TestCase):
    def test_every_workplace_has_its_own_coach(self):
        ids = set(PLUGINS) | set(GAME_CAREERS)
        self.assertEqual(sorted(ids - set(G.ORDER)), [], 'a workplace without a guide entry')
        missing = [cid for cid in G.ORDER if not C.own(cid)]
        self.assertEqual(missing, [], 'workplaces whose coach is only derived from the guide (write their steps)')
        for cid in G.ORDER:
            with self.subTest(career=cid):
                self.assertGreaterEqual(len(C.steps_for(cid)), 3)

    def test_every_guide_button_is_a_target_or_words(self):
        for cid in G.ORDER:
            steps = C.raw(cid)
            targets = {k for s in steps for k in s.get('k', [])}
            refs = {s['g'] if isinstance(s.get('g'), int) else None for s in steps}
            for i, line in enumerate(G.CAREERS[cid]['steps']):
                labels = LABEL.findall(line)
                if not labels:
                    continue
                with self.subTest(career=cid, line=line[:50]):
                    self.assertTrue(i in refs or set(labels) <= targets,
                                    f'{cid}: guide step {i} ({labels}) is neither a step (g={i}) nor every label a target')

    def test_steps_are_well_formed(self):
        keys = {'e', 't', 'k', 's', 'g', 'v', 'w', 'o', 'x', 'at', 'f'}
        for cid in G.ORDER:
            for s in C.raw(cid):
                with self.subTest(career=cid, step=s.get('t', '')[:40]):
                    self.assertLessEqual(set(s), keys)
                    self.assertTrue(s.get('e') and s.get('t'))
                    self.assertTrue(s.get('x') or s.get('k') or s.get('s'), 'a step needs a control, or x=True for words only')
                    if 'g' in s:
                        self.assertTrue(C.guide_line(cid, s['g']))
                    if 'at' in s:
                        self.assertIn(s['at'], ('any', 'job'))

    def test_labels_exist_in_the_ui(self):
        for cid in G.ORDER:
            for s in C.raw(cid):
                for label in s.get('k', []) + (s.get('v') or {}).get('k', []):
                    with self.subTest(career=cid, label=label):
                        self.assertIn(_plain(label), SOURCE, f'{cid}: label "{label}" is not in the game UI')

    def test_selectors_name_real_attributes(self):
        for cid in G.ORDER:
            for s in C.raw(cid):
                for sel in s.get('s', []) + (s.get('v') or {}).get('s', []):
                    for name, value in ATTR.findall(sel):
                        with self.subTest(career=cid, sel=sel):
                            if name == 'coach':
                                self.assertIn(f'data-coach="{value}"', SOURCE, f'{cid}: no control carries data-coach="{value}"')
                            else:
                                bare = value.split(':', 1)[1] if value.startswith('car:') else value
                                self.assertTrue(value in SOURCE or bare in SOURCE, f'{cid}: {sel}: "{value}" is not in the game')

    def test_words_are_short_and_have_english(self):
        en = C.english()
        over = json.loads((ROOT / 'i18n' / 'overrides.json').read_text(encoding='utf-8'))['strings']
        for cid in G.ORDER:
            if not C.own(cid):
                continue
            for line in C.words(cid):
                with self.subTest(career=cid, line=line[:40]):
                    self.assertLessEqual(len(line), 90, 'a bubble line is a few words on a phone')
                    self.assertNotIn('<', line)
                    self.assertIn(line, en, 'add its English to the module EN')
                    self.assertEqual(over.get(line), en[line], 'run `python -m game.coach --i18n`')
        for vi, text in C.ENGINE_EN.items():
            with self.subTest(line=vi):
                self.assertEqual(over.get(vi), text, 'run `python -m game.coach --i18n`')

    def test_engine_words_are_listed(self):
        js = ''.join((ROOT / 'public' / 'js' / 'tutorial' / f).read_text(encoding='utf-8') for f in ('coach.js', 'coach-core.js'))
        said = set(re.findall(r"L\('([^']+)'\)", js)) | set(re.findall(r"t:'([^']+)'", js))
        said |= {m for m in re.findall(r"'([^']*(?:Bấm|bảng này|mục này|Chưa thấy)[^']*)'", js)}
        for line in said:
            with self.subTest(line=line):
                self.assertIn(line, C.ENGINE_EN)

    def test_generated_js_is_current(self):
        js = (ROOT / 'public' / 'js' / 'tutorial' / 'coach-content.js').read_text(encoding='utf-8')
        self.assertEqual(js, C.render_js(), 'run `python -m game.coach`')


class Engine(unittest.TestCase):
    def test_engine_with_node(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'coach_engine.mjs'), json.dumps(list(G.ORDER))], cwd=ROOT,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_wired_in_both_layouts(self):
        app = (ROOT / 'public' / 'js' / 'app.js').read_text(encoding='utf-8')
        self.assertIn('data-action="coachStart"', app, '⋯ → 🧭 Hướng dẫn in every work sheet (both layouts share sideItems)')
        self.assertIn("'coachStart'", app, 'the tutorial module loads on that tap (TUT_OPEN)')
        index = (ROOT / 'public' / 'js' / 'tutorial' / 'index.js').read_text(encoding='utf-8')
        self.assertIn('coachBoot(env)', index)
        self.assertIn("case'coachStart'", index)


class SaveCompat(unittest.TestCase):
    """The coach keeps no new save key: its marks are ids in settings.notesSeen ("co-…", "cd-…", "cn1"), a setting every
    release since the tutorial accepts with the same rule (≤ 12 ids of [a-z0-9-]{1,24}). A rollback keeps the save
    valid; the older build simply shows no coach."""

    def test_marks_are_valid_seen_ids(self):
        every = 'co-' + 'v' * 12, 'cd-' + 'v' * 12, 'gd-' + 'v' * 12
        notes = ','.join(['onb1', 'h-job', 'h-money', 'h-clock', 'h-door', 'cn1', *every])
        self.assertEqual(notes_seen(notes), notes)
        s = new_state()
        s, _ = apply_action(s, None, 'settings', {'notesSeen': notes})
        self.assertEqual(s['settings']['notesSeen'], notes)
        validate_state(s)

    def test_previous_release_accepts_them(self):
        # The rule the previous release validates with (git: the same notes_seen since it was added): replayed here
        # from its source so a change to it in this branch would show up as a difference.
        old = subprocess.run(['git', 'show', 'origin/main:game/engine.py'], cwd=ROOT, capture_output=True, text=True)
        if old.returncode:
            self.skipTest('no git history')
        m = re.search(r'def notes_seen\(v\).*?return ",".join\(ids\)\n', old.stdout, re.S)
        self.assertIsNotNone(m)
        scope: dict = {}
        from game.engine import need  # the helper the rule calls
        exec(compile(m.group(0), 'engine_head.py', 'exec'), {'need': need, 're': re}, scope)
        notes = 'onb1,cn1,co-' + 'v' * 12 + ',cd-' + 'v' * 12 + ',gd-' + 'v' * 12
        self.assertEqual(scope['notes_seen'](notes), notes)


if __name__ == '__main__':
    unittest.main()
