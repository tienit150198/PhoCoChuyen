"""🗺️ Bản đồ phố (public/js/scenes/town-place.js, public/js/v4/town-walk.js): every place on the town map opens the
workplace it says (feedback #140 "Tạp hoá không mở cửa được", the chat's "cà phê bánh với tạp hoá sao không mở tiệm
được"). Walks the map's mapping for every place: each building's id is a real career the server knows, with its own
sign, in the chapter the story opens it; every career has exactly one door; a place the player closed (Tạm đóng) says
so on its sign and its door offers "Mở lại" that goes straight in; a locked one says how it opens. The walking itself
(doors reachable, taps hitting the right building) is scripts/check_town_walk.mjs, run here when node is there."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from game import employment
from game import journey as jr
from game.content import CAREERS
from game.engine import apply_action, validate_state
from tests.test_journey import Play, act

ROOT = Path(__file__).resolve().parents[1]
PLACE = (ROOT / 'public/js/scenes/town-place.js').read_text(encoding='utf-8')
WALK = (ROOT / 'public/js/v4/town-walk.js').read_text(encoding='utf-8')


def rows():
    block = PLACE[PLACE.index('export const ROWS=['):PLACE.index('];', PLACE.index('export const ROWS=['))]
    return [re.findall(r"'([a-z_:]+)'", m) for m in re.findall(r"items:\[([^\]]*)\]", block)]


def signs():
    block = PLACE[PLACE.index('export const SIGNS={'):PLACE.index('};', PLACE.index('export const SIGNS={'))]
    return {k: e for k, e, _ in re.findall(r"([a-z_]+):\['([^']+)','([^']+)'\]", block)}


class Mapping(unittest.TestCase):
    def test_every_place_is_a_real_career_with_one_door_and_its_sign(self):
        ids = [k for district in rows() for k in district if not k.startswith('lm:')]
        self.assertEqual(len(ids), len(set(ids)), 'a career with two doors')
        self.assertEqual(sorted(set(ids) - set(CAREERS)), [], 'a door to a career the server does not know')
        self.assertEqual(sorted(set(CAREERS) - set(ids)), [], 'a career with no named door (it would join a row as a plain shop)')
        sg = signs()
        self.assertEqual(sorted(set(ids) - set(sg)), [])
        self.assertEqual(sg['grocery'], '🛒')
        self.assertEqual(sg['cafe_bakery'], '🥐')

    def test_every_place_opens_on_the_server_once_its_chapter_is_reached(self):
        unlock = {cid: n for n, cids in jr.CH_UNLOCKS.items() for cid in cids}
        for cid in CAREERS:
            self.assertIn(cid, unlock, f'{cid} never opens in the story')
        p = Play()
        s = p.s
        for cid in jr.CH_UNLOCKS[1]:                      # the first street: every lit shop takes the player in
            if cid not in CAREERS:
                continue
            s, _ = act(s, cid, 'select_career')
            self.assertEqual(s['current'], cid)
            if employment.required(cid):                    # a job to apply for first (Giao hàng): the door says "Cần xin việc"
                continue
            s, _ = act(s, cid, 'start_day')
            self.assertTrue(s['careers'][cid]['open'], cid)
            s, _ = act(s, cid, 'end_day', carry_event=True)
        validate_state(s)


class ClosedAndLocked(unittest.TestCase):
    def test_a_paused_place_says_so_and_reopens_straight_in(self):
        p = Play()
        s, _ = act(p.s, None, 'jr_pause', career='grocery', confirm=True)
        self.assertTrue(jr.public(s)['places']['grocery']['paused'])   # what the map reads (J.places[id].paused)
        s, r = apply_action(s, None, 'jr_reopen', dict(career='grocery', confirm=True))
        self.assertIn('mở cửa lại', r['message'])
        s, _ = act(s, 'grocery', 'select_career')
        s, _ = act(s, 'grocery', 'start_day')
        self.assertTrue(s['careers']['grocery']['open'])
        # The door's card: the reason, and one free button that reopens and goes in (go:1, v4/journey.js jrReopen; #oldcost).
        self.assertIn("act('Mở lại','jrReopen',{career:it.id,go:1}", WALK)
        self.assertIn('Mở lại miễn phí', WALK)
        self.assertIn('Bạn đã tạm đóng nơi này', WALK)
        self.assertIn("if(r&&data.go)await env.act('choose',{career:data.career})", (ROOT / 'public/js/v4/journey.js').read_text(encoding='utf-8'))
        self.assertIn("tr('⏸ Tạm đóng')", PLACE)                       # on the sign too, the shutter all the way down

    def test_a_locked_place_says_how_it_opens(self):
        self.assertIn('Mở ở chương ${n}', WALK)
        self.assertIn("act('📋 Danh sách','jrList'", WALK)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_navigation_controls(self):
        out = subprocess.run([shutil.which('node'), str(ROOT / 'tests' / 'delivery_town_navigation.mjs')], cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_walking_the_town(self):
        out = subprocess.run([shutil.which('node'), str(ROOT / 'scripts' / 'check_town_walk.mjs')], cwd=ROOT, capture_output=True,
                             text=True, encoding='utf-8', timeout=240)
        self.assertEqual(out.returncode, 0, out.stdout[-2000:] + out.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
