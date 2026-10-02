"""📖 Hướng dẫn: every workplace has a complete career guide, every game topic has words,
the button names the guides quote exist in the game, and the browser copy is current."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from game import guide_content as G
from game.careers import PLUGINS
from game.content import CAREERS as GAME_CAREERS

ROOT = Path(__file__).resolve().parents[1]
BUILTIN = ('milk_tea', 'grocery', 'delivery', 'cafe_bakery', 'florist', 'mother_baby', 'restaurant', 'pet_care',
           'salon', 'repair', 'farm', 'homestay', 'customer_care', 'pharmacy', 'tour_guide', 'teacher', 'accounting',
           'corp_accounting', 'tax_payroll', 'group_accounting')
GROUPS = ('start', 'journey', 'jobs', 'customers', 'money', 'stock', 'life', 'staff', 'social', 'account', 'new', 'settings')
LABEL = re.compile(r'\[\[(.+?)\]\]')
GENERATED = ('guide_content.py', 'guide-content.js')


def _source() -> str:
    """Everything the player can see a label in: the client code and the server content."""
    parts = []
    for base, pattern in ((ROOT / 'public' / 'js', '*.js'), (ROOT / 'game', '*.py')):
        for f in base.rglob(pattern):
            if f.name in GENERATED or '__pycache__' in f.parts:
                continue
            parts.append(f.read_text(encoding='utf-8', errors='replace'))
    return '\n'.join(parts)


SOURCE = _source()


def _texts(entry: dict):
    """Every player-facing line of a career entry."""
    yield entry.get('intro', '')
    for j in entry.get('jobs', []):
        yield j['name']
        yield j['how']
    for m in entry.get('mistakes', []):
        yield m['bad']
        yield m['result']
    for key in ('steps', 'stars', 'prep', 'surprises'):
        yield from entry.get(key, [])


class CareerGuides(unittest.TestCase):
    def test_every_workplace_has_an_entry(self):
        ids = set(BUILTIN) | set(PLUGINS) | set(GAME_CAREERS)
        missing = sorted(ids - set(G.CAREERS))
        self.assertEqual(missing, [], 'workplaces without a guide entry (add them to game/guide_content.py)')

    def test_entries_are_complete(self):
        for cid, e in G.CAREERS.items():
            with self.subTest(career=cid):
                for key in ('emoji', 'name'):
                    self.assertTrue(isinstance(e.get(key), str) and e[key].strip(), f'{cid}: {key}')
                if e.get('stub'):
                    self.assertIn(cid, G.PENDING, f'{cid}: only careers still being built may be stubs')
                    continue
                self.assertTrue(e.get('intro', '').strip(), f'{cid}: intro')
                for key in G.REQUIRED:
                    self.assertTrue(e.get(key), f'{cid}: section {key} is empty')
                for j in e['jobs']:
                    self.assertTrue(j.get('emoji') and j.get('name', '').strip() and j.get('how', '').strip(), f'{cid}: job {j}')
                for m in e['mistakes']:
                    self.assertTrue(m.get('bad', '').strip() and m.get('result', '').strip(), f'{cid}: mistake {m}')
                for key in ('steps', 'stars', 'prep', 'surprises'):
                    for line in e.get(key, []):
                        self.assertTrue(isinstance(line, str) and line.strip(), f'{cid}: blank line in {key}')
                self.assertGreaterEqual(len(e['steps']), 3, f'{cid}: a job needs a few steps')

    def test_real_career_is_not_a_stub(self):
        # A workplace that is in the game must have its full guide, except the ones still being built.
        for cid in set(PLUGINS) | set(GAME_CAREERS):
            if cid in G.PENDING:
                continue
            with self.subTest(career=cid):
                self.assertFalse(G.CAREERS[cid].get('stub'), f'{cid}: write its guide')

    def test_button_names_exist_in_the_ui(self):
        for cid, e in G.CAREERS.items():
            used = {x for line in _texts(e) for x in LABEL.findall(line)}
            with self.subTest(career=cid):
                self.assertEqual(sorted(used - set(e.get('buttons', []))), [], f'{cid}: [[labels]] missing from buttons')
                for label in e.get('buttons', []):
                    self.assertIn(label, SOURCE, f'{cid}: button "{label}" is not in the game UI')

    def test_lines_are_short_and_plain(self):
        for cid, e in G.CAREERS.items():
            for line in _texts(e):
                with self.subTest(career=cid, line=line[:40]):
                    self.assertLessEqual(len(line), 200, 'keep guide lines short')
                    self.assertNotIn('<', line)
                    self.assertEqual(line.count('[['), line.count(']]'))


class GameGuide(unittest.TestCase):
    def test_every_group_has_topics(self):
        ids = [g['id'] for g in G.GROUPS]
        self.assertEqual(sorted(ids), sorted(GROUPS))
        for g in G.GROUPS:
            with self.subTest(group=g['id']):
                self.assertTrue(g['emoji'] and g['title'].strip())
                self.assertTrue(g['topics'], f'{g["id"]}: no topics')

    def test_every_topic_has_content(self):
        seen = set()
        overview = set(re.findall(r'\{id:"([a-z_]+)"', (ROOT / 'public' / 'js' / 'tutorial' / 'guide-data.js').read_text(encoding='utf-8')))
        for g in G.GROUPS:
            for t in g['topics']:
                with self.subTest(topic=t.get('id')):
                    self.assertNotIn(t['id'], seen, 'topic ids are unique')
                    seen.add(t['id'])
                    self.assertTrue(t['emoji'] and t['title'].strip())
                    self.assertGreaterEqual(len(t['points']), 2)
                    for p in t['points']:
                        self.assertTrue(isinstance(p, str) and p.strip() and len(p) <= 200 and '<' not in p, p)
                        for label in LABEL.findall(p):
                            self.assertIn(label, SOURCE, f'topic {t["id"]}: "{label}" is not in the game UI')
                    if t.get('pic'):
                        self.assertIn(t['pic'], overview, 'pic names an OVERVIEW illustration')
                    if t.get('stub'):
                        self.assertTrue(t['points'][0].startswith('🚧'), 'a stub topic says it is coming')
                    go = t.get('go')
                    if go:
                        a = go['action']
                        self.assertTrue(go.get('label'))
                        self.assertTrue(re.search(rf"""data-action="{a}"|case\s*'{a}'|\['{a}',|action===?'{a}'""", SOURCE),
                                        f'topic {t["id"]}: no control handles data-action "{a}"')


class QuickAnswers(unittest.TestCase):
    """❓ Hỏi nhanh: a short answer per question players ask, naming real buttons; its button only opens a screen."""

    def test_short_answers(self):
        self.assertTrue(10 <= len(G.QUICK) <= 15, 'keep Hỏi nhanh to 10–15 questions')
        ids = [x['id'] for x in G.QUICK]
        self.assertEqual(len(ids), len(set(ids)), 'question ids are unique')
        topics = {t['id'] for g in G.GROUPS for t in g['topics']}
        for x in G.QUICK:
            with self.subTest(q=x['id']):
                self.assertNotIn(x['id'], topics | {'quick'}, 'a question id is not a topic id (both open by `topic`)')
                self.assertTrue(x['emoji'] and x['q'].strip() and len(x['q']) <= 80 and '<' not in x['q'])
                self.assertTrue(1 <= len(x['a']) <= 3, 'answer in 1–3 lines')
                for line in x['a']:
                    self.assertTrue(isinstance(line, str) and line.strip() and len(line) <= 160 and '<' not in line, line)
                    self.assertEqual(line.count('[['), line.count(']]'))
                    for label in LABEL.findall(line):
                        self.assertIn(label, SOURCE, f'{x["id"]}: "{label}" is not in the game UI')

    def test_buttons_open_real_screens(self):
        for x in G.QUICK:
            go = x.get('go')
            if not go:
                continue
            with self.subTest(q=x['id']):
                self.assertTrue(go.get('label'))
                if 'sec' in go:
                    self.assertIn(go['sec'], G.SECTIONS)
                    continue
                a = go['action']
                self.assertTrue(re.search(rf"""data-action="{a}"|case\s*'{a}'|\['{a}',|action===?'{a}'""", SOURCE),
                                f'{x["id"]}: no control handles data-action "{a}"')

    def test_hub_and_menu_are_wired(self):
        guide = (ROOT / 'public' / 'js' / 'tutorial' / 'guide.js').read_text(encoding='utf-8')
        self.assertIn('Hỏi nhanh', guide)
        self.assertIn('id="gh-quick"', guide)
        app = (ROOT / 'public' / 'js' / 'app.js').read_text(encoding='utf-8')
        self.assertIn("mini('tutGuide','question','Hỏi nhanh'", app, 'the menu footer opens Hỏi nhanh in one tap')
        tut = (ROOT / 'public' / 'js' / 'tutorial' / 'index.js').read_text(encoding='utf-8')
        self.assertIn('data-topic="quick"', tut, 'Cài đặt opens Hỏi nhanh')


class NextStepButton(unittest.TestCase):
    """The work screen's bottom button (public/js/v4/guide.js): a step it can only point at reads as a pointer."""

    def test_pointer_button(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('node not installed')
        out = subprocess.run([node, str(ROOT / 'tests' / 'guide_cta.mjs')], cwd=ROOT, capture_output=True, text=True,
                             encoding='utf-8', timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)


class BrowserCopy(unittest.TestCase):
    def test_generated_js_is_current(self):
        js = (ROOT / 'public' / 'js' / 'tutorial' / 'guide-content.js').read_text(encoding='utf-8')
        self.assertEqual(js, G.render_js(), 'run `python -m game.guide_content`')

    def test_public_is_json_without_test_fields(self):
        data = G.public()
        raw = json.dumps(data, ensure_ascii=False)
        self.assertNotIn('"buttons"', raw)
        self.assertEqual(data['order'], [cid for cid in G.ORDER if cid in G.CAREERS])
        self.assertEqual(set(data['careers']), set(G.CAREERS))

    def test_hub_is_wired(self):
        guide = (ROOT / 'public' / 'js' / 'tutorial' / 'guide.js').read_text(encoding='utf-8')
        self.assertIn("import('./guide-content.js')", guide)
        for label in ('Hướng dẫn chơi', 'Hướng dẫn nghề', 'data-tut-career', 'data-gh-q'):
            self.assertIn(label, guide)
        app = (ROOT / 'public' / 'js' / 'app.js').read_text(encoding='utf-8')
        self.assertIn('guideHelp(career())', app, 'the "?" in a work screen header opens that career\'s guide')


if __name__ == '__main__':
    unittest.main()
