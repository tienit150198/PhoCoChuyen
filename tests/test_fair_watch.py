"""🕶️ The police's eye on the skill stalls (game/fair_watch.py; owner 09/10: "phóng dao, ô ăn quan thì chơi hệ kĩ năng",
"bắt nếu cảm thấy có cheat hoặc spam"): honest play, however quick, randomized many times, is never caught; a script
that throws its knives before they happen, a burst of knife runs, ô ăn quan moves no hand makes and a burst of ô ăn
quan games are, with the Chợ đen's arrest (the stake if any, the fine, the trại tạm giữ); nothing about the thresholds
reaches the client; and the saves (a twist level in play, the watch's counters, a caught player) validate and
settle on the releases this one may be rolled back to (1.9.31, 1.9.30), and a run begun there settles here."""
import json
import os
import random
import subprocess
import sys
import unittest
from unittest import mock

from game import fair as fh
from game import fair_bm as bm
from game import fair_knife as kn
from game import fair_oaq as oaq
from game import fair_watch as w
from game import jail as jl
from game.engine import GameError, apply_action, public_state, validate_state
from tests.test_black_market import OPEN, BlackMarketBase, story
from tests.test_fair import greedy_move
from tests.test_fair_dog import OLD, OldServer as DogOldServer
from tests.test_fair_knife import crash_tap, safe_taps


class WatchBase(BlackMarketBase):
    """Inside the Chợ đen (no bảo kê asked), the arrest roll never fires, the trại tạm giữ on, a clock we move by hand."""

    def setUp(self):
        super().setUp()
        self.ask(False)
        roll = mock.Mock(return_value=True)   # the Chợ đen's roll would catch anything it was asked about
        p = mock.patch.object(bm, '_arrest_roll', roll)
        p.start()
        self.addCleanup(p.stop)
        self.roll = roll
        env = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        self.t = OPEN
        for mod in (fh, jl):
            p = mock.patch.object(mod, 'now', lambda: self.t)
            p.start()
            self.addCleanup(p.stop)

    def act(self, s, name, **p):
        return apply_action(s, None, name, p)

    def inside(self, wallet):
        return story(wallet)   # (the đàn em do not ask: straight in)

    def tick(self, seconds):
        self.t += seconds

    def run_of(self, s):
        return s['journey']['fair_kn']['run']

    def board(self, s):
        return fh._kn_sched(self.run_of(s), s['journey'])

    def throw(self, s, taps, ahead=0, latency=.2):
        """Send `taps` when the server has seen taps[-1] - ahead ms (+ latency) of the level pass."""
        run = self.run_of(s)
        self.t = run['at'] / 1000 + (taps[-1] - ahead) / 1000 + latency
        return self.act(s, 'fair_kn_throw', lv=run['lv'], taps=taps, id=f'{run["sd"]}-{run["lv"]}')

    def assert_free(self, r):
        self.assertNotIn('arrest', r.get('fair') or {})

    def assert_caught(self, s, r, words):
        a = r['fair']['arrest']
        self.assertIn(words, r['message'])
        self.assertEqual(a['say'], bm.SAY_CHEAT)
        self.assertEqual(a['jail'], bm.JAIL_DAYS)
        self.assertEqual(s['journey']['jail']['why'], 'bm')
        self.assertIn('tạm giữ 3 ngày', r['message'])
        validate_state(s)
        return a


class Pure(unittest.TestCase):
    def test_windows(self):
        j = {}
        self.assertEqual([w.kn_start(j, 1000 + i) for i in range(w.KN_SPAM_RUNS)], [False] * (w.KN_SPAM_RUNS - 1) + [True])
        j = {}
        for i in range(w.KN_SPAM_RUNS - 1):
            self.assertFalse(w.kn_start(j, i * 1000))
        self.assertFalse(w.kn_start(j, w.KN_SPAM_MS))          # the window is over: a fresh one
        self.assertEqual(j[w.KEY]['ks'], [w.KN_SPAM_MS, 1])
        self.assertFalse(w.kn_start(j, 5))                     # the clock went back: a fresh one too
        j = {}
        self.assertFalse(w.kn_throw(j, 0, w.KN_AHEAD_MS))      # at the bound: fine
        self.assertNotIn('ka', j.get(w.KEY, {}))
        self.assertFalse(w.kn_throw(j, 0, w.KN_AHEAD_MS + 1))
        self.assertTrue(w.kn_throw(j, w.KN_AHEAD_WINDOW_MS - 1, 3999))
        w.clear(j, 'ka')
        self.assertFalse(w.kn_throw(j, 10**7, 3999))

    def test_oaq_moves(self):
        j = {}
        self.assertFalse(w.oaq_move(j, 0))                     # a game begun before this build: no clock yet
        w.oaq_start(j, 1000)
        t = 1000
        for i in range(w.OAQ_FAST_MOVES - 1):
            t += w.OAQ_FAST_MS - 1
            self.assertFalse(w.oaq_move(j, t))
        t += w.OAQ_FAST_MS                                      # not fast: not counted, the clock moves
        self.assertFalse(w.oaq_move(j, t))
        self.assertTrue(w.oaq_move(j, t + 1))
        self.assertEqual(j[w.KEY]['of'], [1000 + w.OAQ_FAST_MS - 1, w.OAQ_FAST_MOVES])
        j = {}
        w.oaq_start(j, 0)
        self.assertFalse(w.oaq_move(j, 1))
        self.assertFalse(w.oaq_move(j, w.OAQ_FAST_WINDOW_MS + 2))   # (not fast)
        w.oaq_start(j, w.OAQ_FAST_WINDOW_MS + 3)                    # games apart, the window apart: a fresh count
        self.assertFalse(w.oaq_move(j, w.OAQ_FAST_WINDOW_MS + 4))
        self.assertEqual(j[w.KEY]['of'], [w.OAQ_FAST_WINDOW_MS + 4, 1])

    def test_validate(self):
        good = {'ks': [1, 2], 'ka': [0, 0], 'os': [10**12, 5], 'ol': 3, 'of': [3, 4]}
        for v in ({}, good, {'ol': 0}):
            w.validate({w.KEY: v})
        w.validate({})
        for bad in ([], {'x': 1}, {'ks': [1]}, {'ks': [1, 2, 3]}, {'ks': (1, 2)}, {'ks': [-1, 2]}, {'of': -1}, {'of': [1]},
                    {'ol': '1'}, {'ka': [1, 10**7]}, {'os': [1.5, 2]}):
            with self.assertRaises(GameError):
                w.validate({w.KEY: bad})


class KnifeHumans(WatchBase):
    def human_session(self, rng, runs):
        """A person at the stall: aims (the clear spots, starting when they like), the level clock on the page a
        little behind the server's or up to ~1 s ahead (the state's whole-second clock), a slow or a quick network,
        stops or plays on, loses now and then, sometimes rattles off runs as fast as a hand can."""
        s = self.inside(10**6)
        for _ in range(runs):
            quick = rng.random() < .35
            self.tick(rng.uniform(1.2, 2.5) if quick else rng.uniform(2, 25))
            s, r = self.act(s, 'fair_kn_start', stake=rng.choice(kn.STAKES))
            self.assert_free(r)
            for lv in range(1, kn.LEVELS + 1):
                sc = self.board(s)
                if rng.random() < (.5 if quick else .12):     # a knife on a knife
                    taps = safe_taps(sc, rng.randint(1, 3), start=rng.randint(150, 900))
                    taps.append(crash_tap(sc, taps))
                else:
                    taps = safe_taps(sc, sc['need'], start=rng.randint(150, 1500 if quick else 4000))
                ahead = rng.uniform(-300, 1000)                  # the page's level clock against the server's
                s, r = self.throw(s, taps, ahead=ahead, latency=rng.uniform(.03, .9))
                self.assert_free(r)
                if r['fair'].get('lost') or r['fair'].get('all'):
                    break
                self.tick(rng.uniform(.75, 1.2) if quick else rng.uniform(1, 6))   # the choice
                if quick or rng.random() < .55:
                    s, r = self.act(s, 'fair_kn_stop')
                    self.assert_free(r)
                    break
                s['journey']['fair_kn']['run']['nx'] = 0
                s, r = self.act(s, 'fair_kn_next')
                self.assert_free(r)
        self.assertNotIn('jail', s['journey'])
        validate_state(s)
        return s

    def test_honest_play_is_never_caught(self):
        for seed in range(6):
            with self.subTest(seed=seed):
                self.human_session(random.Random(seed), 70)
        self.roll.assert_not_called()

    def test_a_fast_hand_for_five_minutes_on_end_is_not_caught(self):
        """Runs started 3.1 s apart (every one thrown and lost as fast as the page lets) for six minutes."""
        s = self.inside(10**6)
        for i in range(115):
            self.tick(3.1)
            s, r = self.act(s, 'fair_kn_start', stake=10)
            self.assert_free(r)
            s['journey']['fair_kn']['run']['sg'] = 'lost'
        self.assertNotIn('jail', s['journey'])


class KnifeScripts(WatchBase):
    def test_throws_sent_before_they_happen_are_caught(self):
        s = self.inside(100000)
        s, r = self.act(s, 'fair_kn_start', stake=1000)
        sc = self.board(s)
        taps = safe_taps(sc, sc['need'], start=3200)
        s, r = self.throw(s, taps, ahead=3000, latency=0)        # sent 3 s ahead: once, noted
        self.assertTrue(r['fair']['cleared'])
        self.tick(1)
        s, r = self.act(s, 'fair_kn_stop')
        paid = r['fair']['prize']
        self.tick(30)
        s, r = self.act(s, 'fair_kn_start', stake=1000)
        sc = self.board(s)
        wallet = s['journey']['wallet']
        s, r = self.throw(s, safe_taps(sc, sc['need'], start=3500), ahead=3400, latency=0)
        a = self.assert_caught(s, r, 'tay ném nhanh bất thường')
        self.assertEqual((a['stake'], a['fine']), (1000, wallet * 30 // 100))
        self.assertEqual(s['journey']['wallet'], wallet - a['fine'])   # the stake went in at the start, no prize
        self.assertEqual(self.run_of(s)['sg'], 'lost')
        self.assertEqual(s['journey']['wallet'], 100000 - 1000 + paid - 1000 - a['fine'])
        self.assertNotIn('ka', s['journey'][w.KEY])                      # a fresh start once out
        self.assertNotIn('2500', r['message'])
        with self.assertRaises(GameError) as e:                          # the cell: no Chợ đen
            self.act(s, 'fair_kn_start', stake=10)
        self.assertEqual(e.exception.code, 'jailed')

    def test_a_burst_of_runs_is_caught(self):
        s = self.inside(10**6)
        for i in range(w.KN_SPAM_RUNS - 1):
            self.tick(1.5)
            s, r = self.act(s, 'fair_kn_start', stake=500)
            self.assert_free(r)
            s['journey']['fair_kn']['run']['sg'] = 'lost'
        wallet = s['journey']['wallet']
        self.tick(1.5)
        s, r = self.act(s, 'fair_kn_start', stake=500)
        a = self.assert_caught(s, r, 'phóng dao liên tục bất thường')
        self.assertEqual((a['stake'], a['fine']), (500, (wallet - 500) * 30 // 100))
        self.assertEqual(s['journey']['wallet'], wallet - 500 - a['fine'])
        self.assertEqual(s['journey']['history'][-1]['label'], bm.FINE_LABEL)
        self.roll.assert_not_called()

    def test_the_kill_switch_turns_the_eye_off(self):
        s = self.inside(10**6)
        with mock.patch.dict(os.environ, {'MNL_BM_OFF': '1'}):
            for i in range(w.KN_SPAM_RUNS + 5):
                self.tick(1)
                s, r = self.act(s, 'fair_kn_start', stake=2)
                self.assert_free(r)
                s['journey']['fair_kn']['run']['sg'] = 'lost'
        self.assertNotIn(w.KEY, s['journey'])


class OAQ(WatchBase):
    def play(self, s, gap, rng=None, moves=None):
        """Moves `gap()` s after the game's previous command until the game ends (or `moves` were played)."""
        n = 0
        r = None
        while s['journey']['fair']['oaq']['stage'] == 'play' and (moves is None or n < moves):
            self.tick(gap())
            c, d = greedy_move(s['journey']['fair']['oaq']['g'])
            s, r = self.act(s, 'fair_oaq_move', cell=c, dir=d, ply=s['journey']['fair']['oaq']['g']['ply'])
            n += 1
            if 'arrest' in r['fair']:
                break
        return s, r, n

    def test_honest_games_are_never_caught(self):
        for seed in range(5):
            rng = random.Random(seed)
            s = self.inside(1000)
            with self.subTest(seed=seed):
                for _ in range(12):
                    self.tick(rng.uniform(1, 20))
                    s, r = self.act(s, 'fair_oaq_start', lv=rng.choice(oaq.LEVELS))
                    self.assert_free(r)
                    s, r, n = self.play(s, lambda: rng.uniform(.6, 6) if rng.random() < .8 else rng.uniform(.4, .7))
                    self.assert_free(r)
                self.assertNotIn('jail', s['journey'])

    def test_fishing_for_an_opening_is_not_caught(self):
        """New game, give up, new game: 5.5 s a time for ten minutes."""
        s = self.inside(0)
        for _ in range(110):
            self.tick(5.5)
            s, r = self.act(s, 'fair_oaq_start', lv='kho')
            self.assert_free(r)
        self.assertNotIn('jail', s['journey'])

    def test_moves_no_hand_makes_are_caught(self):
        s = self.inside(20000)
        total = 0
        for game in range(3):   # a game can end in fewer moves: the count runs on into the next
            self.tick(1)
            s, r = self.act(s, 'fair_oaq_start', lv='de')
            s, r, n = self.play(s, lambda: .1)
            total += n
            if 'arrest' in r['fair']:
                break
        self.assertEqual(total, w.OAQ_FAST_MOVES)
        a = self.assert_caught(s, r, 'nước đi nhanh bất thường')
        before = a['wallet'] + a['fine']                                 # (an earlier game may have been won)
        self.assertGreaterEqual(before, 20000)
        self.assertEqual((a['stake'], a['fine']), (0, before * 30 // 100))   # no stake: the fine and the cell
        self.assertEqual(s['journey']['wallet'], before - a['fine'])
        self.assertEqual(s['journey']['fair']['oaq']['stage'], 'lost')
        self.assertNotIn('Mất', r['message'])

    def test_a_burst_of_games_is_caught(self):
        s = self.inside(5000)
        for _ in range(w.OAQ_SPAM_GAMES - 1):
            self.tick(1)
            s, r = self.act(s, 'fair_oaq_start', lv='de')
            self.assert_free(r)
        self.tick(1)
        s, r = self.act(s, 'fair_oaq_start', lv='de')
        a = self.assert_caught(s, r, 'bày bàn liên tục bất thường')
        self.assertEqual((a['stake'], a['fine']), (0, 1500))

    def test_a_won_game_pays_the_old_prizes(self):   # owner 09/10: "thắng ông Hai vẫn là 10k/1 lần"
        self.assertEqual(public_state(story(0))['fair']['rules']['oaq_prize'], {'de': 50, 'kho': 10000})


class NothingShown(WatchBase):
    def test_no_threshold_reaches_the_client(self):
        s = self.inside(10**6)
        s, _ = self.act(s, 'fair_oaq_start', lv='de')
        s, _ = self.act(s, 'fair_kn_start', stake=10)
        self.assertIn(w.KEY, s['journey'])
        blob = json.dumps(public_state(s), ensure_ascii=False)
        for k in ('fair_watch', 'KN_AHEAD', 'OAQ_FAST', '"ks"', '"ka"', '"os"', '"ol"', '"of"'):
            self.assertNotIn(k, blob)
        with open(fh.__file__, encoding='utf-8') as fp:
            src = fp.read()
        for line in src.splitlines():
            if 'bất thường, nghi gian lận' in line:
                self.assertNotRegex(line.split("f'", 1)[1], r'\d{2,}|%|giây|ms')
        self.assertNotRegex(bm.SAY_CHEAT, r'\d')


class OldServer(DogOldServer):
    """Saves this build writes (a twist level in play, the watch's counters, a player caught by it) validate and
    load on 1.9.31 and 1.9.30; a twist level in play there settles on the board that server shows; a run begun on
    1.9.31 settles here on the board it was shown."""

    test_saves_after_a_race_validate_on_older_releases = None   # (the dog race's own, in tests/test_fair_dog.py)

    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {'MNL_JAIL_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        self.t = OPEN
        for mod in (fh, jl):
            p = mock.patch.object(mod, 'now', lambda: self.t)
            p.start()
            self.addCleanup(p.stop)

    def run_old(self, rev, prog, data):
        old = self.old_tree(rev)
        env = dict(os.environ, MNL_BM_OFF='1', MNL_JAIL_OFF='1',
                   PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(data), capture_output=True, text=True,
                             cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout.strip().splitlines()[-1])

    def new_saves(self):
        s = self.inside(10**5)
        s, _ = apply_action(s, None, 'fair_kn_start', {'stake': 1000})
        run = s['journey']['fair_kn']['run']
        sc = fh._kn_sched(run, s['journey'])
        taps = safe_taps(sc, sc['need'])
        self.t = run['at'] / 1000 + taps[-1] / 1000 + .2
        s, r = apply_action(s, None, 'fair_kn_throw', {'lv': 1, 'taps': taps})
        self.assertTrue(r['fair']['cleared'])
        s['journey']['fair_kn']['run']['nx'] = 0
        self.t += 2
        s, _ = apply_action(s, None, 'fair_kn_next', {})                # level 2 in play, × 1.05
        self.t += 2
        s, _ = apply_action(s, None, 'fair_oaq_start', {'lv': 'de'})
        c, d = greedy_move(s['journey']['fair']['oaq']['g'])
        self.t += 3
        s, _ = apply_action(s, None, 'fair_oaq_move', {'cell': c, 'dir': d})
        playing = json.loads(json.dumps(s))
        self.assertEqual(set(playing['journey'][w.KEY]), {'ks', 'os', 'ol'})
        self.assertIn(fh.KN_TWIST_KEY, playing['journey'])
        caught = json.loads(json.dumps(s))
        run = caught['journey']['fair_kn']['run']
        caught['journey'][w.KEY]['ka'] = [run['at'], w.KN_AHEAD_FLAGS - 1]
        sc = fh._kn_sched(run, caught['journey'])
        taps = safe_taps(sc, sc['need'], start=3200)
        self.t = run['at'] / 1000 + (taps[-1] - 3000) / 1000
        caught, r = apply_action(caught, None, 'fair_kn_throw', {'lv': 2, 'taps': taps})
        self.assertIn('arrest', r['fair'])
        self.assertIn('jail', caught['journey'])
        return playing, caught

    def test_saves_validate_and_a_twist_level_settles_on_older_releases(self):
        playing, caught = self.new_saves()
        prog = r'''
import json, sys
from game import fair as fh, fair_knife as kn
from game.engine import validate_state, migrate_state, public_state, apply_action
saves, t = json.load(sys.stdin)
out = []
for s in saves:
    validate_state(s); s = migrate_state(s); validate_state(s); public_state(s)
    out.append(s['journey']['wallet'])
s = saves[0]
fh.now = lambda: t
run = s['journey']['fair_kn']['run']
sc = fh._kn_sched(run, s['journey'])
assert public_state(s)['fair']['knife']['run']['board']['segs'] == json.loads(json.dumps(sc['segs']))
taps, at = [], 300
while len(taps) < sc['need']:
    stuck, hit = kn.judge(sc, taps); a = kn.lands(sc, at)
    if all(kn.dist(a, b) >= kn.GAP + 1 for b in sc['pre'] + stuck): taps.append(at); at += kn.MIN_TAP
    else: at += 5
fh.now = lambda: run['at'] / 1000 + taps[-1] / 1000 + .2
s, r = apply_action(s, None, 'fair_kn_throw', {'lv': 2, 'taps': taps})
assert r['fair'].get('cleared'), r
fh.now = lambda: run['at'] / 1000 + taps[-1] / 1000 + 2
s, r = apply_action(s, None, 'fair_kn_stop', {})
validate_state(s)
out.append(r['fair']['prize'])
print(json.dumps(out))
'''
        for rev, name in OLD:
            with self.subTest(release=name):
                out = self.run_old(rev, prog, [[playing, caught], self.t])
                self.assertEqual(out[:2], [playing['journey']['wallet'], caught['journey']['wallet']])
                self.assertEqual(out[2], kn.prize(1000, 2))

    def test_a_run_begun_on_the_last_release_settles_here(self):
        s = self.inside(5000)
        prog = r'''
import json, sys
from game import fair as fh
from game.engine import apply_action
s, t = json.load(sys.stdin)
fh.now = lambda: t
s, r = apply_action(s, None, 'fair_kn_start', {'stake': 100})
s['journey']['fair_kn']['run']['nx'] = 0
print(json.dumps([s, r['fair']['run']['board']['segs']]))
'''
        rev, name = OLD[0]
        s, segs = self.run_old(rev, prog, [s, self.t])   # (1.9.31: 1.9.30 has the same knife rules)
        j = s['journey']
        self.assertNotIn(fh.KN_TWIST_KEY, j)
        validate_state(s)
        run = j['fair_kn']['run']
        sc = fh._kn_sched(run, j)
        self.assertEqual(json.loads(json.dumps(sc['segs'])), segs)       # the board it was shown
        taps = safe_taps(sc, sc['need'])
        self.t = run['at'] / 1000 + taps[-1] / 1000 + .2
        s, r = apply_action(s, None, 'fair_kn_throw', {'lv': 1, 'taps': taps})
        self.assertTrue(r['fair']['cleared'])
        s['journey']['fair_kn']['run']['nx'] = 0                         # (no x2 level in this test)
        self.t += 2
        s, r = apply_action(s, None, 'fair_kn_next', {})                 # the next level is this build's: faster
        run = s['journey']['fair_kn']['run']
        self.assertEqual(s['journey'][fh.KN_TWIST_KEY], {'at': run['at'], 'seed': run['sd']})
        self.t += 1
        sc = fh._kn_sched(run, s['journey'])
        taps = safe_taps(sc, sc['need'])
        self.t = run['at'] / 1000 + taps[-1] / 1000 + .2
        s, r = apply_action(s, None, 'fair_kn_throw', {'lv': 2, 'taps': taps})
        self.assertTrue(r['fair']['cleared'])
        self.t += 1
        s, r = apply_action(s, None, 'fair_kn_stop', {})
        self.assertEqual(r['fair']['prize'], kn.prize(100, 2))
        validate_state(s)


del DogOldServer

if __name__ == '__main__':
    unittest.main()
