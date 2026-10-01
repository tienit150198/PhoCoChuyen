"""The salon bowl preview can never disagree with the bowl.

public/js/careers/salon_mix.js is a line-for-line port of game/careers/salon.py bowl_check. These tests run every
combination through both (node tests/salon_mix_parity.mjs) and require identical results:

- the two-tube bowl: every tube A × tube B (or none) × parts 1–3 each, × developer 10/20/30/40/not picked ×
  ratio right/wrong/not picked × every colour target in the game (and grey, developer unknown, …) × brassy base ×
  filtered photo × roots/dyed lengths;
- the single-tube bowls (old colour clients, toner, bleach) × developer × ratio × their recipes;
- what the preview sees once the stylist has found everything out (the task's public view) against what the
  server decides with the hidden key, for every colour, toner and bleach client.

Also: the rule table behind the developer notes matches every recipe in the game, and a save made mid-bowl plays on.
"""
import copy
import hashlib
import json
import shutil
import subprocess
import unittest
from pathlib import Path

import game.careers.kit as kit
from game.engine import public_state, validate_state
from game.careers import salon as S
from tests.helpers import Journey

ROOT = Path(__file__).resolve().parents[1]
DEVS = [10, 20, 30, 40, None]
RATIOS = ['1:1', '1:2', '1:1.5', None]
LIFTS = [None, dict(base=5, dyed=None), dict(base=6, dyed=7), dict(base=4, dyed=3)]


def two_tube_bowls() -> list:
    out = []
    for a in S.DYES:
        for pa in S.MIX_PARTS:
            out.append(['color', a['id'], dict(b=None, pa=pa, pb=0)])
            for b in S.DYES:
                if b['id'] != a['id']:
                    out.extend(['color', a['id'], dict(b=b['id'], pa=pa, pb=pb)] for pb in S.MIX_PARTS)
    return out


def colour_targets() -> list:
    """Every (level, tone) a client of the game can need, plus the filtered photo levels the preview may see first."""
    seen = []
    for j in S.JOBS2:
        col = j['k'].get('color')
        for lt in ([(col['level'], col['tone'])] if col else []) + ([(j['photo']['level'], j['photo']['band'])] if j['photo'].get('band') else []):
            if lt not in seen:
                seen.append(lt)
    for r in S.PHOTO_REAL:
        if (r['level'], r['tone']) not in seen:
            seen.append((r['level'], r['tone']))
    return seen


def mix_wants() -> list:
    wants = [None]
    for level, tone in colour_targets():
        wants.append(dict(level=level, tone=tone, dev=20, ratio='1:1', grey=False))
        wants.append(dict(level=level, tone=tone, dev=10, ratio='1:1', grey=True))
    wants += [dict(level=7, tone='warm', dev=None, ratio='1:1', grey=False),      # roots not seen yet
              dict(level=8, tone='ash', dev=30, ratio='1:1', grey=False),
              dict(level=5, tone='warm', dev=20, ratio='1:1', grey=True)]
    return wants


def single_bowls() -> list:
    return [['color', d['id'], None] for d in S.DYES] + [['toner', d['id'], None] for d in S.TONERS] + [['bleach', None, None]]


def single_wants() -> list:
    wants = [None, dict(dev=20, ratio='1:2'), dict(dev=10, ratio='1:2', shade=None)]
    for x in S.CLIENTS:
        for kind in ('color', 'bleach', 'toner'):
            w = x['key'].get(kind)
            if w and w not in wants:
                wants.append(dict(w))
    wants += [dict(shade=t['id'], dev=10, ratio='1:2') for t in S.TONERS]
    return wants


def grids() -> list:
    bowls = two_tube_bowls()
    hairs = [[w, b, lift] for w in (0, 1) for b in (False, True) for lift in (None, LIFTS[2])]
    return [
        # The mix maths against every target and hair condition (developer right or 40 vol: Linh's first word).
        dict(bowls=bowls, devs=[20, 40], ratios=['1:1'], hairs=hairs, wants=mix_wants()),
        # Developer and ratio against every target, with the roots and dyed lengths known or not.
        dict(bowls=bowls, devs=DEVS, ratios=['1:1', '1:2', None], hairs=[[0, False, lift] for lift in LIFTS], wants=mix_wants()),
        # Single tubes, toner and bleach.
        dict(bowls=single_bowls(), devs=DEVS, ratios=RATIOS, hairs=[[0, False, None]], wants=single_wants()),
    ]


def line(v: dict) -> str:
    m = v['mix']
    return json.dumps([v['issue'], v['hit'], m and [m['den'], m['lv'], m['tn'], m['nat'], m['band'], m['color']], v['text'],
                       v['level_ok'], v['band_ok'], v['nat_ok'], v['dlv'], v['dband'], v['dev_note'], v['need'], v['cap'],
                       v['tones'], v['block']], separators=(',', ':'), ensure_ascii=False)


def outcome(v: dict) -> str:
    m = v['mix']
    return json.dumps([v['issue'], v['hit'], m and [m['den'], m['lv'], m['tn'], m['nat'], m['band'], m['color']], v['text']],
                      separators=(',', ':'), ensure_ascii=False)


def sha(lines: list) -> str:
    return hashlib.sha256('\n'.join(lines).encode('utf-8')).hexdigest()


def grid_lines(g: dict, bi: int) -> list:
    kind, shade, mx = g['bowls'][bi]
    return [line(S.bowl_check(kind, shade, mx, dev, ratio, want, warm, blind, lift))
            for dev in g['devs'] for ratio in g['ratios'] for warm, blind, lift in g['hairs'] for want in g['wants']]


# ------------------------------------------------------------------ the public view once everything is found out
def every_client_task() -> list:
    """One v0.5 task per colour/toner/bleach client (the filtered-photo client once per real photo)."""
    found = {}
    for day in range(1, 80):
        for slot in range(10):
            t = S.make_task(day, slot, 1)
            k = t['_key']
            if not t.get('gen') or not (k.get('color') or k.get('toner') or k.get('bleach')):
                continue
            tag = (t['title'], (t['_x'].get('real') or {}).get('level'))
            found.setdefault(tag, t)
    return list(found.values())


def seen_everything(t: dict) -> dict:
    t = copy.deepcopy(t)
    t.update(known=True, asked=list(S.TOPIC_IDS), inspected=list(S.ZONE_IDS), photo_seen=True)
    if t['_key'].get('bleach'):
        t['results']['bleach'] = dict(zone='ideal', secs=12.0, ok=True, shade='bleach', dev=20, ratio='1:2')
    return t


def server_lines(t: dict, bowls: list) -> list:
    out, k, h = [], t['_key'], t['_hair']
    for kind in kinds_of(t):
        if kind == 'color':
            blind = t['needs'].get('case') == 'photo' and not t.get('photo_seen')
            out += [outcome(S.bowl_check('color', shade, mx, dev, ratio, k['color'], h.get('warm', 0), blind))
                    for _, shade, mx in bowls for dev in DEVS for ratio in RATIOS]
        else:
            shades = [x['id'] for x in S.TONERS] if kind == 'toner' else [None]
            out += [outcome(S.bowl_check(kind, shade, None, dev, ratio, k[kind]))
                    for shade in shades for dev in DEVS for ratio in RATIOS]
    return out


def kinds_of(t: dict) -> list:
    return [kind for kind in ('color', 'bleach', 'toner') if t['_key'].get(kind)]


class SalonMixParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which('node')
        cls.cc = json.loads(json.dumps(S.content()))
        cls.grids = grids()
        cls.bowls = two_tube_bowls()
        cls.tasks = every_client_task()
        cls.views = [dict(view=json.loads(json.dumps(S.public_task(seen_everything(t)))), kinds=kinds_of(t)) for t in cls.tasks]
        cls.spec = json.dumps(dict(cc=cls.cc, grids=cls.grids, views=cls.views, bowls=cls.bowls, devs=DEVS, ratios=RATIOS))

    def run_node(self, *args):
        if not self.node:
            self.skipTest('node not installed')
        if not args and getattr(type(self), 'js', None):
            return type(self).js
        out = subprocess.run([self.node, str(ROOT / 'tests' / 'salon_mix_parity.mjs'), *args], input=self.spec, cwd=ROOT,
                             capture_output=True, text=True, timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr)
        res = json.loads(out.stdout)
        if not args:
            type(self).js = res
        return res

    def first_difference(self, mine: list, theirs: list) -> str:
        for i, (a, b) in enumerate(zip(mine, theirs)):
            if a != b:
                return f'case {i}: python {a} != js {b}'
        return f'{len(mine)} python lines, {len(theirs)} js lines'

    def test_every_combination_gives_the_same_verdict(self):
        js = self.run_node()['grids']
        cases = 0
        for gi, g in enumerate(self.grids):
            self.assertEqual(len(js[gi]), len(g['bowls']))
            for bi in range(len(g['bowls'])):
                lines = grid_lines(g, bi)
                cases += len(lines)
                if sha(lines) != js[gi][bi]:
                    theirs = self.run_node('dump', 'grid', str(gi), str(bi))
                    self.fail(f'grid {gi} bowl {g["bowls"][bi]}: {self.first_difference(lines, theirs)}')
        self.assertGreater(cases, 200_000)

    def test_preview_matches_the_server_once_everything_is_seen(self):
        js = self.run_node()['views']
        titles = {t['title'] for t in self.tasks}
        for j in S.JOBS2:
            if j['k'].get('color') or j['k'].get('toner') or j['k'].get('bleach') or j['case'] == 'photo':
                self.assertIn(j['title'], titles)
        self.assertEqual(len([t for t in self.tasks if t['needs'].get('case') == 'photo']), len(S.PHOTO_REAL))
        for i, t in enumerate(self.tasks):
            mine = server_lines(seen_everything(t), self.bowls)
            if sha(mine) != js[i]:
                theirs = self.run_node('dump', 'view', str(i))
                self.fail(f'{t["title"]}: {self.first_difference(mine, theirs)}')

    def test_preview_tables_match_every_recipe(self):
        """What the preview infers (target from the photo, grey from the roots, ratio by kind) is what the key holds,
        and the developer it names can lift the roots to the target (the notes never contradict the bowl)."""
        for t in self.tasks:
            v, k, h = self.views[self.tasks.index(t)]['view'], t['_key'], t['_hair']
            col = k.get('color')
            if col:
                tg = (v['real']['level'], v['real']['tone']) if v.get('real') else (v['needs']['photo']['level'], v['needs']['photo']['band'])
                self.assertEqual(tg, (col['level'], col['tone']), t['title'])
                self.assertEqual(col['grey'], (v['grey'] or 0) >= 50, t['title'])
                self.assertEqual(col['ratio'], S.KIND_RATIO['color'])
                self.assertEqual(v['recipe']['color']['dev'], col['dev'])
                tones = col['level'] - v['recipe']['color']['base']
                self.assertGreaterEqual(S.LIFT[col['dev']], tones, t['title'])
                self.assertEqual(S._dev_note(col['dev'], col['dev'], tones), 'ok')
                dyed = v['recipe']['color']['dyed']
                self.assertTrue(dyed is None or col['level'] <= dyed, t['title'])
            else:
                self.assertFalse(v['needs']['photo'].get('band') and not v.get('real'), t['title'])
            for kind in ('bleach', 'toner'):
                if k.get(kind):
                    self.assertEqual(k[kind]['ratio'], S.KIND_RATIO[kind])
        for x in S.CLIENTS:
            for kind in ('color', 'bleach', 'toner'):
                if x['key'].get(kind):
                    self.assertEqual(x['key'][kind]['ratio'], S.KIND_RATIO[kind], x['title'])

    def test_recipe_view_shows_only_what_was_found_out(self):
        grey = next(t for t in self.tasks if t['needs'].get('case') == 'grey')
        t = copy.deepcopy(grey)
        t.update(known=True)
        v = S.public_task(t)
        self.assertEqual(v['recipe']['color'], dict(dev=None, ratio='1:1', base=None, dyed=None))
        t['inspected'] = ['roots']
        self.assertEqual(S.public_task(t)['recipe']['color'], dict(dev=20, ratio='1:1', base=5, dyed=None))
        fix = copy.deepcopy(next(t for t in self.tasks if t['needs'].get('case') == 'fix'))
        fix.update(known=True, inspected=['roots', 'lengths'])
        self.assertEqual(S.public_task(fix)['recipe']['color'], dict(dev=10, ratio='1:1', base=6, dyed=7))
        idol = copy.deepcopy(next(t for t in self.tasks if t['_key'].get('toner')))
        idol.update(known=True)
        self.assertIsNone(S.public_task(idol)['recipe']['toner']['shade'])        # tint shows after the bleach
        self.assertEqual(S.public_task(seen_everything(idol))['recipe']['toner']['shade'], 'toner_silver')
        self.assertNotIn('_key', json.dumps(S.public_task(seen_everything(idol))))


class SalonMidBowlSave(unittest.TestCase):
    """A save made mid-task (bowl mixed, not applied) validates, shows the preview data and plays on to checkout."""

    def setUp(self):
        self.t0, self.old = 5000.0, kit.clock
        kit.clock = lambda: self.t0

    def tearDown(self):
        kit.clock = self.old

    def test_mid_bowl_save_plays_on(self):
        day, slot = next((d, s) for d in range(1, 45) for s in range(10) if S.make_task(d, s, 1)['needs'].get('case') == 'grey')
        j = Journey('salon', slot=slot, day=day)
        tid = j.task['id']
        j.act('ask')
        j.act('sl_consult', topic='history')
        j.act('sl_inspect', zone='roots')
        j.act('sl_plan', services=['color', 'cut'], sessions=1)
        j.act('sl_mix', kind='color', shade='dye_3_0', shade2='dye_7_3', parts=[1, 1], dev=20, ratio='1:1')
        saved = json.loads(json.dumps(j.state))
        validate_state(saved)
        j.state = saved
        view = next(v for v in public_state(j.state)['careers']['salon']['tasks'] if v['id'] == j.task['id'])
        self.assertEqual(view['recipe']['color']['dev'], 20)
        self.assertTrue(j.task['bowl']['ok'])
        j.act('sl_apply')
        self.t0 += 14
        j.act('sl_rinse')
        j.act('sl_cut', step='section')
        j.act('sl_cut', step='guide', length=1)
        j.act('sl_cut', step='check')
        j.act('sl_checkout', products=[], confirm=True)
        self.assertEqual(j.get(tid)['status'], 'completed')
        validate_state(json.loads(json.dumps(j.state)))


if __name__ == '__main__':
    unittest.main()
