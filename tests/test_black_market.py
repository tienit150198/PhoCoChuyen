"""🕶️ Chợ đen (game/fair_bm.py, game/fair.py; owner 08/10: "k phải là hội chợ, nó là Chợ đen", bảo kê 10k xu, không
nộp thì bị trấn lột 30%, công an bắt cực cao): the bảo kê gate once a Vietnam day, the robbery, the arrests on every
paid round (stake lost, fine of 30% of the wallet, banned until the day ends), nothing about the rate on the client,
a save an older (1.9.26) server still validates, and the new name everywhere players see the fair."""
import datetime
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import tokenize
import unittest
from pathlib import Path
from unittest import mock

from game import bank as bk
from game import fair as fh
from game import fair_bm as bm
from game import fair_knife as knife
from game import fair_scratch as scratch
from game import journey as jr
from game.engine import GameError, new_state, validate_state

ROOT = Path(__file__).resolve().parents[1]
VN = fh.VN
OLD_RELEASE = '7b46fa1b'   # 1.9.26, the release this one may be rolled back to


def at(y, m, d, hh=12, mm=0, ss=0):
    return datetime.datetime(y, m, d, hh, mm, ss, tzinfo=VN).timestamp()


OPEN = at(2026, 10, 10, 20)   # day 2 of the edition (09/10 → 13/10)


def story(wallet=50000):
    s = new_state()
    jr.enable_story(s, 4242)
    s['journey']['gender'] = 'female'
    s['journey']['wallet'] = wallet
    validate_state(s)
    return s


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        self.t += 6   # past the pause between rounds (bầu cua's bowl too)
        return self.t


PAID = {   # every stall that takes a stake: (command, payload, stake)
    'bc': ('fair_bc', {'bets': {'cua': 100}}, 100),
    'xd': ('fair_xd', {'side': 'chan', 'stake': 50}, 50),
    'lt': ('fair_loto_buy', {'tier': 'lon', 'n': 1}, 10),
    'xs': ('fair_xs', {'price': scratch.TIERS[3]}, scratch.TIERS[3]),
    'kn': ('fair_kn_start', {'stake': knife.STAKES[2]}, knife.STAKES[2]),
}


class BlackMarketBase(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {'MNL_BM_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        for k in ('MNL_FAIR_START', 'MNL_FAIR_DAYS'):
            os.environ.pop(k, None)
        self.clock = Clock(OPEN)
        p = mock.patch.object(fh, 'now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        self.ask(True)   # the đàn em ask (hên xui: tests/AskedOrNot covers the roll)

    def ask(self, on=True):
        p = mock.patch.object(bm, 'asked', lambda j, t: on)
        p.start()
        self.addCleanup(p.stop)

    def act(self, s, name, **p):
        return fh.action(s, name, p)

    def refused(self, s, name, code, **p):
        with self.assertRaises(GameError) as e:
            fh.action(s, name, p)
        self.assertEqual(e.exception.code, code)
        return e.exception

    def caught(self, on=True):
        p = mock.patch.object(bm, '_arrest_roll', lambda: on)
        p.start()
        self.addCleanup(p.stop)


class Gate(BlackMarketBase):
    def test_nothing_before_the_bao_ke(self):
        s = story()
        for name, p, _ in PAID.values():
            with self.subTest(name=name):
                self.refused(s, name, 'fair_bm_gate', **p)
        self.refused(s, 'fair_oaq_start', 'fair_bm_gate', lv='de')
        self.refused(s, 'fair_snack', 'fair_bm_gate', item='nuoc_mia')
        self.refused(s, 'fair_borrow', 'fair_bm_gate', amount=100)
        self.assertEqual(s['journey']['wallet'], 50000)
        b = fh.public(s)['bm']
        self.assertEqual((b['st'], b['inside'], b['ban'], b['fee']), ('', False, False, 10000))
        # the organisers' gift is still claimed at the gate
        s, r = self.act(s, 'fair_gift')
        self.assertEqual(s['journey']['wallet'], 50500)

    def test_pay_once_a_day(self):
        s = story(25000)
        s, r = self.act(s, 'fair_bm_pay')
        self.assertEqual(r['fair']['paid'], 10000)
        self.assertEqual(s['journey']['wallet'], 15000)
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['kind'], row['label']), (-10000, 'fair', bm.FEE_LABEL))
        self.assertEqual(s['journey']['fair_bm'], {'d': '2026-10-10', 's': 'paid'})
        self.assertTrue(fh.public(s)['bm']['inside'])
        s, r = self.act(s, 'fair_bm_pay')   # a retry, another tab: nothing more to pay
        self.assertTrue(r['fair']['again'])
        s, r = self.act(s, 'fair_bm_refuse')
        self.assertTrue(r['fair']['again'])
        self.assertEqual(s['journey']['wallet'], 15000)
        self.caught(False)
        s, r = self.act(s, 'fair_bc', bets={'ga': 10})
        self.assertEqual(r['fair']['game'], 'bc')
        self.assertEqual(s['journey']['fair']['stats']['lost'] - s['journey']['fair']['stats']['won'],
                         10000 - r['fair']['net'])   # the fee is a fair loss (the Bảng vàng)

    def test_pay_needs_the_fee_in_the_wallet(self):
        s = story(9999)
        e = self.refused(s, 'fair_bm_pay', 'fair_bm_short')
        self.assertIn('10.000', str(e))
        self.assertEqual(s['journey']['wallet'], 9999)
        self.assertNotIn('fair_bm', s['journey'])

    def test_refuse_robs_30_percent_of_the_wallet_only(self):
        s = story(12345)
        b = s['journey']['bank'] = bk.initial(1, 1)
        b['balance'] = 80000
        validate_state(s)
        s, r = self.act(s, 'fair_bm_refuse')
        self.assertEqual(r['fair']['robbed'], 12345 * 30 // 100)
        self.assertEqual(s['journey']['wallet'], 12345 - 3703)
        self.assertEqual(s['journey']['bank']['balance'], 80000)   # never the bank account
        row = s['journey']['history'][-1]
        self.assertEqual((row['amount'], row['label']), (-3703, bm.ROB_LABEL))
        self.assertIn('3.703', r['message'])
        self.assertEqual(s['journey']['fair_bm']['s'], 'robbed')
        self.assertTrue(fh.public(s)['bm']['inside'])

    def test_refuse_with_an_empty_or_owing_wallet(self):
        for w in (0, 3, -500):
            with self.subTest(wallet=w):
                s = story(w)
                rows = len(s['journey']['history'])
                s, r = self.act(s, 'fair_bm_refuse')
                self.assertEqual(r['fair']['robbed'], 3 * 30 // 100 if w == 3 else 0)
                self.assertEqual(s['journey']['wallet'], w)
                self.assertEqual(len(s['journey']['history']), rows)
                self.assertTrue(fh.public(s)['bm']['inside'])

    def test_a_huge_wallet_is_robbed_in_valid_rows(self):
        s = story(10**9)
        s, r = self.act(s, 'fair_bm_refuse')
        self.assertEqual(r['fair']['robbed'], 3 * 10**8)
        self.assertEqual(s['journey']['wallet'], 7 * 10**8)
        rows = [x for x in s['journey']['history'] if x['label'] == bm.ROB_LABEL]
        self.assertEqual(sum(x['amount'] for x in rows), -3 * 10**8)
        self.assertTrue(all(abs(x['amount']) <= 10**7 for x in rows))
        validate_state(s)

    def test_the_vietnam_day_ends_it(self):
        s = story()
        self.clock.t = at(2026, 10, 10, 23, 58)
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(False)
        self.clock.t = at(2026, 10, 10, 23, 59, 40)
        s, _ = self.act(s, 'fair_bc', bets={'ga': 1})   # still today
        self.clock.t = at(2026, 10, 11, 0, 0, 0)
        self.assertEqual(fh.public(s)['bm']['st'], '')
        self.refused(s, 'fair_bc', 'fair_bm_gate', bets={'ga': 1})
        s, r = self.act(s, 'fair_bm_pay')
        self.assertEqual(s['journey']['fair_bm'], {'d': '2026-10-11', 's': 'paid'})

    def test_closed_market_takes_no_bao_ke(self):
        s = story()
        self.clock.t = at(2026, 10, 14, 0, 0)
        self.refused(s, 'fair_bm_pay', 'fair_closed')
        self.refused(s, 'fair_bm_refuse', 'fair_closed')


class AskedOrNot(BlackMarketBase):
    """Owner 09/10: "phí bảo kê k phải khi nào cũng thu, tỷ lệ thu là hên xui 40% /2 ngày"."""

    def test_not_asked_walks_in_free(self):
        mock.patch.stopall()   # the real roll, the real clock, then the clock again
        self.setUp_clock_only()
        s = story()
        p = mock.patch.object(bm, 'asked', lambda j, t: False)
        p.start()
        self.addCleanup(p.stop)
        b = fh.public(s)['bm']
        self.assertEqual((b['st'], b['inside'], b['ban']), ('free', True, False))
        self.caught(False)
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('dice', r['fair'])
        s, r = self.act(s, 'fair_bm_pay')   # an old page: nothing taken
        self.assertTrue(r['fair']['again'])
        self.assertNotIn('fair_bm', s['journey'])
        self.caught(True)   # the police still come
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('arrest', r['fair'])
        self.assertEqual(fh.public(s)['bm']['st'], 'ban')
        validate_state(s)

    def setUp_clock_only(self):
        env = mock.patch.dict(os.environ, {'MNL_BM_OFF': '0'})
        env.start()
        self.addCleanup(env.stop)
        p = mock.patch.object(fh, 'now', self.clock)
        p.start()
        self.addCleanup(p.stop)

    def test_settled_for_the_two_day_stretch(self):
        s = story()
        self.clock.t = at(2026, 10, 11, 9)   # 11/10 and 12/10 are one stretch, 13/10 starts the next
        s, _ = self.act(s, 'fair_bm_pay')
        self.clock.t = at(2026, 10, 12, 22)
        self.assertEqual(fh.public(s)['bm']['st'], 'paid')
        self.caught(False)
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('dice', r['fair'])
        self.clock.t = at(2026, 10, 13, 0, 0, 1)
        self.assertEqual(fh.public(s)['bm']['st'], '')
        self.refused(s, 'fair_bc', 'fair_bm_gate', bets={'cua': 10})

    def test_a_ban_ends_with_the_day_not_the_bao_ke(self):
        s = story()
        self.clock.t = at(2026, 10, 11, 9)
        s, _ = self.act(s, 'fair_bm_refuse')
        self.caught(True)
        s, _ = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertEqual(fh.public(s)['bm']['st'], 'ban')
        self.clock.t = at(2026, 10, 12, 9)   # same stretch: in again, nothing to settle
        b = fh.public(s)['bm']
        self.assertEqual((b['st'], b['inside']), ('paid', True))
        w = s['journey']['wallet']
        s, r = self.act(s, 'fair_bm_pay')
        self.assertTrue(r['fair']['again'])
        self.assertEqual(s['journey']['wallet'], w)

    def test_the_roll_is_fixed_and_about_40_percent(self):
        mock.patch.stopall()
        j = story()['journey']
        t1, t2 = at(2026, 10, 11, 0, 1), at(2026, 10, 12, 23, 59)
        self.assertEqual(bm.asked(j, t1), bm.asked(j, t2), 'one answer for the whole stretch')
        self.assertEqual((bm.BM_ASK_P, bm.ASK_DAYS), (0.40, 2))
        hits = sum(bm.asked({'seed': seed}, at(2026, 10, 9 + 2 * k)) for seed in range(500) for k in range(4))
        self.assertTrue(0.35 < hits / 2000 < 0.45, hits)
        s = story()
        self.assertNotIn('ask', json.dumps(fh.public(s)['bm']))

    def test_old_save_block_kinds_still_read(self):
        j = {'seed': 1, 'fair_bm': {'d': 'not a date', 's': 'paid'}}
        self.assertEqual(bm.status(j, at(2026, 10, 11)), '')   # asked (patched): a broken date settles nothing


class Arrest(BlackMarketBase):
    def test_every_paid_stall_can_be_raided(self):
        for game, (name, p, stake) in PAID.items():
            with self.subTest(game=game):
                s = story(20000)
                s, _ = self.act(s, 'fair_bm_pay')   # 10,000 left
                with mock.patch.object(bm, '_arrest_roll', lambda: True):
                    s, r = self.act(s, name, **p)
                a = r['fair']['arrest']
                fine = (10000 - stake) * 30 // 100
                self.assertEqual((r['fair']['game'], a['stake'], a['fine']), (game, stake, fine))
                self.assertEqual(s['journey']['wallet'], 10000 - stake - fine)
                self.assertEqual(a['wallet'], s['journey']['wallet'])
                self.assertEqual(s['journey']['fair_bm']['s'], 'ban')
                self.assertNotIn('dice', r['fair'])   # no outcome
                last = s['journey']['history'][-1]
                self.assertEqual((last['amount'], last['label']), (-fine, bm.FINE_LABEL))
                self.assertTrue(s['journey']['history'][-2]['label'].startswith(fh.LABELS[game]))
                self.assertEqual(s['journey']['history'][-2]['amount'], -stake)
                self.assertIn('f_raid', s['journey']['titles'])
                self.assertIn('Công an ập vào', r['message'])
                pub = fh.public(s)['bm']
                self.assertEqual((pub['ban'], pub['inside']), (True, False))
                # thrown out until the day ends: no round, no bảo kê, no snack
                for n2, p2, _ in PAID.values():
                    self.refused(s, n2, 'fair_bm_ban', **p2)
                self.refused(s, 'fair_bm_pay', 'fair_bm_ban')
                self.refused(s, 'fair_snack', 'fair_bm_ban', item='nuoc_mia')

    def test_no_arrest_plays_the_round(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(False)
        s, r = self.act(s, 'fair_bc', bets={'cua': 100})
        self.assertIn('dice', r['fair'])
        self.assertNotIn('arrest', r['fair'])
        self.assertEqual(s['journey']['fair_bm']['s'], 'paid')

    def test_round_begun_still_finishes_after_a_ban(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(False)
        s, _ = self.act(s, 'fair_loto_buy', tier='lon', n=1)
        self.caught(True)
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('arrest', r['fair'])
        s, r = self.act(s, 'fair_loto_fold')   # LATE: finishing what was begun
        self.assertTrue(r['fair']['folded'])

    def test_the_fine_never_makes_debt(self):
        s = story(10050)
        s, _ = self.act(s, 'fair_bm_pay')   # 50 left
        self.caught(True)
        s, r = self.act(s, 'fair_xd', side='le', stake=50)
        self.assertEqual(r['fair']['arrest']['fine'], 0)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertFalse(s['journey']['in_debt'])
        validate_state(s)

    def test_next_day_back_in(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(True)
        s, _ = self.act(s, 'fair_bc', bets={'cua': 10})
        self.clock.t = at(2026, 10, 11, 9)
        self.assertEqual(fh.public(s)['bm'], dict(fee=10000, st='', inside=False, ban=False, who=list(bm.GUARD)))
        s, _ = self.act(s, 'fair_bm_refuse')
        self.caught(False)
        s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertIn('dice', r['fair'])

    def test_the_roll(self):
        class R:
            def __init__(self, x):
                self.x = x

            def random(self):
                return self.x
        self.assertEqual(bm.BM_ARREST_P, 0.20)
        with mock.patch.object(bm, '_rng', R(.1999)):
            self.assertTrue(bm._arrest_roll())
        with mock.patch.object(bm, '_rng', R(.2)):
            self.assertFalse(bm._arrest_roll())

    def test_arrests_leave_the_stalls_draws_alone(self):
        """The arrest has its own random source: a stall's scripted draws (fair._rng) are not consumed by it."""
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        seen = []

        class Dice:
            def choice(self, seq):
                seen.append('c')
                return seq[1]

            def random(self):
                seen.append('r')
                return .99

            def randrange(self, n):
                return 0

            def getrandbits(self, n):
                return 7
        with mock.patch.object(fh, '_rng', Dice()), mock.patch.object(bm, '_rng') as arr:
            arr.random.return_value = .9
            s, r = self.act(s, 'fair_bc', bets={'cua': 10})
        self.assertEqual(r['fair']['dice'], ['cua', 'cua', 'cua'])
        self.assertEqual(seen, ['c', 'c', 'c'])   # three dice and nothing else: as before the Chợ đen


class NothingShown(BlackMarketBase):
    def test_no_rate_reaches_the_client(self):
        s = story()
        f = fh.public(s)
        self.assertEqual(set(f['bm']), {'fee', 'st', 'inside', 'ban', 'who'})
        blob = json.dumps(f, ensure_ascii=False)
        for k in ('arrest_p', 'rob_pct', 'fine_pct', 'BM_ARREST'):
            self.assertNotIn(k, blob)
        s, _ = self.act(s, 'fair_bm_pay')
        self.caught(True)
        s, r = self.act(s, 'fair_bc', bets={'cua': 100})
        self.assertEqual(set(r['fair']['arrest']), {'game', 'stake', 'fine', 'wallet', 'say'})
        self.assertNotIn('%', r['message'])
        for text in (bm.NEED_IN, bm.BANNED, bm.SAY_ROB, bm.SAY_EMPTY, bm.SAY_PAID, bm.SAY_ARREST, bm.SHORT,
                     bm.FEE_LABEL, bm.ROB_LABEL, bm.FINE_LABEL):
            self.assertNotIn('%', text)
            self.assertNotIn('30', text)

    def test_the_client_prints_no_percentage(self):
        js = (ROOT / 'public/js/v4/fair.js').read_text(encoding='utf-8')
        part = js[js.index('/* ---- 🕶️ Chợ đen'):js.index('// 🥶 a long run')]
        self.assertIn('bmGate', part)
        self.assertNotRegex(part, r'\d+\s*%')
        self.assertNotIn('30', re.sub(r'#[0-9a-f]{3,6}|\b\d{1,2}px', '', part))


class OldServer(BlackMarketBase):
    """A save written here (paid, banned) validates on 1.9.26, the release this one may be rolled back to."""

    def old_tree(self):
        if os.environ.get('MNL_BM_OLD_TREE'):
            return Path(os.environ['MNL_BM_OLD_TREE'])
        tmp = tempfile.mkdtemp(prefix='mnl-1926-')
        try:
            data = subprocess.run(['git', 'archive', OLD_RELEASE, 'game', 'reference'], cwd=ROOT, capture_output=True,
                                  timeout=120, check=True).stdout
        except (OSError, subprocess.SubprocessError):
            self.skipTest(f'no git tree with {OLD_RELEASE} (MNL_BM_OLD_TREE)')
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            tar.extractall(tmp, filter='data')
        return Path(tmp)

    def test_new_saves_validate_on_1_9_26(self):
        s = story()
        s, _ = self.act(s, 'fair_bm_pay')
        paid = json.loads(json.dumps(s))
        self.caught(True)
        s, _ = self.act(s, 'fair_bc', bets={'cua': 100})
        banned = json.loads(json.dumps(s))
        s2 = story(5000)
        s2, _ = self.act(s2, 'fair_bm_refuse')
        old = self.old_tree()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state;'
                'out=[]\nfor s in json.load(sys.stdin):\n validate_state(s);s=migrate_state(s);validate_state(s);'
                'out.append(s["journey"].get("fair_bm"))\nprint(json.dumps(out))')
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(x for x in (str(old), os.environ.get('PYTHONPATH', '')) if x))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps([paid, banned, s2]), capture_output=True,
                             text=True, cwd=old, env=env, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        self.assertEqual(json.loads(out.stdout), [{'d': '2026-10-10', 's': 'paid'}, {'d': '2026-10-10', 's': 'ban'},
                                                  {'d': '2026-10-10', 's': 'robbed'}])

    def test_bad_blocks_are_refused(self):
        for bad in ({'d': '2026-10-10'}, {'d': '2026-10-10', 's': 'vip'}, {'d': 'hôm nay!!!', 's': 'paid'}, 'paid'):
            with self.subTest(bad=bad):
                s = story()
                s['journey']['fair_bm'] = bad
                with self.assertRaises(GameError):
                    validate_state(s)


class Renamed(unittest.TestCase):
    """Players see "Chợ đen": no "Hội chợ" left in the fair's strings (comments and quotes of the owner aside)."""
    PY = ('game/fair.py', 'game/fair_bm.py', 'game/fair_cash.py', 'game/fair_food.py', 'game/fair_photo.py',
          'live/fair.py')
    JS = ('public/js/v4/fair.js', 'public/js/v4/fair-booth.js', 'public/js/v4/fair-knife.js', 'public/js/v4/fair-walk.js',
          'public/js/v4/fair-scratch.js', 'public/js/v4/fair-loto.js', 'public/js/v4/honours.js', 'public/js/v4/journey.js',
          'public/js/v4/town-walk.js', 'public/js/scenes/town-place.js', 'public/js/scenes/fair-place.js', 'public/js/app.js')
    OLD = re.compile(r'[Hh]ội chợ')

    def test_python_strings(self):
        for f in self.PY:
            src = (ROOT / f).read_text(encoding='utf-8')
            lines = src.splitlines()
            for t in tokenize.generate_tokens(io.StringIO(src).readline):
                if t.type != tokenize.STRING or t.string.lstrip('rbfuRBFU').startswith(('"""', "'''")):
                    continue
                if '_OLD' in lines[t.start[0] - 1]:   # the former name, to keep today's older Sổ ví rows
                    continue
                with self.subTest(file=f, line=t.start[0]):
                    self.assertNotRegex(t.string, self.OLD)

    def test_js_code_lines(self):
        for f in self.JS:
            for i, ln in enumerate((ROOT / f).read_text(encoding='utf-8').splitlines(), 1):
                st = ln.lstrip()
                if st.startswith(('/*', '*', '//')):
                    continue
                code = ln.split('  // ')[0]
                with self.subTest(file=f, line=i):
                    self.assertNotRegex(code, self.OLD)

    def test_entry_and_title(self):
        self.assertIn('🕶️ Chợ đen', (ROOT / 'public/js/v4/town-walk.js').read_text(encoding='utf-8'))
        self.assertIn('<h2 id="fh-title">Chợ đen</h2>', (ROOT / 'public/js/v4/fair.js').read_text(encoding='utf-8'))
        names = {tid: name for tid, _, name, _ in fh.TITLE_ROWS}
        self.assertEqual(names['f_master'], 'Cao thủ chợ đen')
        self.assertTrue(all(v.endswith('chợ đen') for v in fh.LABELS.values()))


if __name__ == '__main__':
    unittest.main()
