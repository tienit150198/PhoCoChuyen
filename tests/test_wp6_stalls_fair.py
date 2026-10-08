"""WP6 (06/10): stall theft odds that match their labels, the running cost, hiring reasons, the account age said
plainly, chat friend requests, the shop price board, the tax notice, the softer knife board, ring results drawn from
the player's aim and lô tô claims that are only fined for a never-called mark."""
import random
import time
import unittest
from unittest.mock import patch

from game import fair as fh
from game import fair_knife as kn
from game import fair_ring as ring
from game import friends
from game import quay as qy
from game import quay_economy as qe
from game import quay_hire as qh
from game import shop_events as se
from game.engine import GameError, validate_state
from game.extra_content import price_board
from tests.test_quay import bare, owner, act, Q
from tests.test_quay_hire import Base as HireBase
from tests.test_fair import FairBase, story


class StallTheft(unittest.TestCase):
    def sample(self, items=(), security=False):
        s, st = bare('xe', 'milk_tea', items=items)
        qy.ensure(s)['stalls'].append(st)
        qe.config(st)['security'] = security
        return s, st

    def test_factor_matches_the_labels(self):
        cases = {(): 1, ('camera',): .5, ('alarm',): .75, ('ket',): .8}
        for items, want in cases.items():
            _, st = self.sample(items)
            self.assertAlmostEqual(qe.theft_factor(st), want)
        _, st = self.sample(('camera', 'alarm', 'ket'), security=True)
        self.assertAlmostEqual(qe.theft_factor(st), .8 * .75 * .8 / 2)   # bảo vệ counts as the basic plan (-20%)

    def test_protection_really_cuts_the_daily_events(self):
        def thefts(items, security):
            s, st = self.sample(items, security)
            return sum(qe._event(s, st, day) in ('theft', 'robbery') for day in range(6, 6006))
        bare_n, safe_n = thefts((), False), thefts(('camera', 'alarm', 'ket'), True)
        self.assertGreater(bare_n, 200)
        self.assertLess(safe_n, bare_n * .4)
        self.assertGreater(safe_n, 0)   # still possible, as the labels say
        # Other events are untouched by the theft factor.
        s1, a = self.sample()
        s2, b = self.sample(('camera', 'alarm', 'ket'), True)
        other = lambda s, st: [qe._event(s, st, d) for d in range(6, 2006) if qe._event(s, st, d) not in ('theft', 'robbery', None)]
        self.assertEqual(other(s1, a), other(s2, b))

    def test_ket_keeps_half_the_till(self):
        s, st = self.sample(('ket',))
        st['till'] = 1000
        # Running costs left aside (they come from the same till): the theft alone leaves at least half of it.
        with patch.object(qe, '_event', return_value='theft'), patch.object(qy, '_from_till_fund', lambda st, amount: 0):
            qy._sell(s, st, 1)
        lost = st['hist'][-1]['costs']['incident']
        self.assertGreater(lost, 0)
        self.assertGreaterEqual(st['till'], lost)
        self.assertFalse(st['case']['all'])

    def test_business_theft_with_a_ket_never_takes_more_than_half(self):
        choice = next(x for x in se.CATALOGUE['theft']['choices'] if x['id'] == 'record')
        self.assertEqual(se._cost(choice, 1000, 'theft', ['ket'], 10**9, 20), 500)
        self.assertEqual(se._cost(choice, 1000, 'theft', [], 10**9, 20), 1000)

    def test_stall_view_shows_the_risk_and_labels_are_honest(self):
        s = owner(100000)
        s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='xe', confirm=True)
        st = qy.public(s)['stalls'][0]
        self.assertEqual(st['theft_risk']['per'], 'event')
        self.assertAlmostEqual(st['theft_risk']['pct'], 20.0)
        self.assertIn('50%', qy.ITEMS['camera']['line'])
        self.assertIn('nửa két', qy.ITEMS['ket']['line'])
        rc = st['business']['running_cost']
        self.assertEqual(rc['per_period'], sum(st['business']['rates'].values()))
        self.assertIn('accruing', rc)
        validate_state(s)


class AccountAge(HireBase):
    def test_hours_left_and_whose_account(self):
        boss, ann = self.user('boss'), self.user('ann', old=False)
        with self.store.connect() as db:
            msg = qh._age_why(db, self.sid(ann), 'làm thêm')
            other = qh._age_why(db, self.sid(ann), 'nhận ca', 'Ann')
            self.assertIsNone(qh._age_why(db, self.sid(boss), 'làm thêm'))
            self.assertEqual(qh._age_why(db, 'no-such-sid', 'làm thêm')[:30], 'Bạn đang chơi bằng phiên khách'[:30])
        self.assertIn('ngày tuổi', msg)
        self.assertIn('giờ', msg)
        self.assertIn('không phải ngày sống', msg)
        self.assertTrue(other.startswith('Tài khoản của Ann'))

    def test_hours_are_counted_from_created_at(self):
        tok = self.user('cat', old=False)
        made = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 50 * 3600))
        self.store.transaction(lambda db: db.execute('UPDATE accounts SET created_at=? WHERE sid=?', (made, self.sid(tok))))
        with self.store.connect() as db:
            self.assertEqual(qh._age_wait(db, self.sid(tok)), 22)

    def test_locked_invite_is_shown_with_its_reason_and_the_owner_sees_why(self):
        boss, kid = self.user('boss'), self.user('kid', life=3)
        self.open_stall(boss)
        mr_code = self._befriend(boss, kid)
        self.act(boss, 'post', stall=self.stall(boss)['id'], wage=30, to=mr_code)
        board = self.view(kid)['board']
        self.assertEqual(len(board), 1)
        self.assertTrue(board[0]['invite'])
        self.assertIn('ngày sống', board[0]['locked'])
        mine = self.view(boss)['mine'][0]
        self.assertIn('Kid', mine['blocked'])
        self.assertEqual(qh.invite_count(self.store, kid), 1)
        self.assertEqual(qh.invite_count(self.store, boss), 0)

    def _befriend(self, a, b):
        from game import marriage as mr
        for tok in (a, b):
            mr.ensure_person(self.store, self.sid(tok))
        with self.store.connect() as db:
            code = db.execute('SELECT code FROM marriage_people WHERE sid=?', (self.sid(b),)).fetchone()['code']
        self.store.transaction(lambda db: friends._befriend(db, self.sid(a), self.sid(b), None))
        return code


class FriendCodes(HireBase):
    def test_own_code_and_unknown_code_say_why(self):
        from game import marriage as mr
        GameError = mr.MarriageError
        ann = self.user('ann')
        mr.ensure_person(self.store, self.sid(ann))
        with self.store.connect() as db:
            code = db.execute('SELECT code FROM marriage_people WHERE sid=?', (self.sid(ann),)).fetchone()['code']
        with self.assertRaises(GameError) as e:
            friends.request(self.store, self.sid(ann), 'Ann', dict(code=code))
        self.assertEqual(str(e.exception), 'Đây là mã của chính bạn.')
        with self.assertRaises(GameError) as e:
            friends.request(self.store, self.sid(ann), 'Ann', dict(code='PCC-ZZZZZZ'))
        self.assertIn('Không thấy mã', str(e.exception))


class PriceBoard(unittest.TestCase):
    def test_every_spec_price_has_a_row_with_a_name(self):
        from game.careers import PLUGINS
        board = price_board()
        for cid, mod in PLUGINS.items():
            prices = mod.SPEC.get('prices') or {}
            if prices:
                self.assertEqual([r['id'] for r in board[cid]], list(prices), cid)
                self.assertTrue(all(r['name'] and r['base'] == prices[r['id']] for r in board[cid]), cid)
        self.assertEqual(next(r for r in board['com'] if r['id'] == 'com_tam')['name'], 'Cơm tấm')


class KnifeAndRing(unittest.TestCase):
    def test_soft_board_is_gentler_and_carries_its_gap(self):
        old, new = kn.schedule(5, 3, 0, 135), kn.schedule(5, 3, 0, kn.SOFT_DIFFICULTY)
        self.assertLess(new['need'], old['need'])
        self.assertEqual(new['gap'], kn.SOFT_GAP)
        self.assertNotIn('gap', old)
        self.assertLess(abs(new['segs'][0][1]), abs(old['segs'][0][1]))
        # A knife 9° from another bounces on the old board, sticks on the soft one.
        sc = dict(new, pre=[0.0])
        t = next(t for t in range(0, 20000) if 8.6 < kn.dist(kn.lands(sc, t), 0.0) < 9.4)
        self.assertEqual(kn.judge(sc, [t])[1], -1)
        self.assertEqual(kn.judge(dict(sc, gap=kn.GAP), [t])[1], 0)
        self.assertIn('gap', kn.public_schedule(new))

    def test_ring_hits_land_next_to_the_aim(self):
        p = dict(xs=[10, 30, 50, 70, 90], period=2000, phase=0.0)
        taps = [100, 330, 500, 740, 910]                     # x = 10, 33, 50, 74, 91: 0, 3, 0, 4, 1 off a neck
        self.assertEqual(ring.land(p, taps, 3), [0, -1, 2, -1, 4])
        self.assertEqual(ring.land(p, taps, 4), [0, 1, 2, -1, 4])   # the ring let go furthest off a neck is left out
        self.assertEqual(ring.land(p, taps, 5), [0, 1, 2, 3, 4])
        self.assertEqual(ring.land(p, taps, 0), [-1] * 5)


class FairWinRate(FairBase):
    """Owner 07/10: every luck stall is won about 50% of the time in normal play (a long winning streak cools off to
    50%); a long run of one stall cools to 40%. Real commands, a seeded source standing in for the OS one."""
    N = 1500

    def setUp(self):
        super().setUp()
        self.dice(random.Random(6102026))

    def play(self, game, run=8, n=None, skip=0):
        """n rounds of one stall, another stall every `run` rounds (normal play, as if the player went over to
        another stall: a new run; None: one long run); the share won after the first `skip` rounds."""
        s, wins = story(10 ** 7), 0
        for i in range((n or self.N) + skip):
            if i == skip:
                wins = 0
            if run and i and i % run == 0:
                for key in ('fair_run', 'fair_run2', 'fair_run3', fh.COOL_KEY):   # as if 3 rounds elsewhere
                    s['journey'].pop(key, None)
            f = s['journey'].get('fair')
            if f:
                f['raid_until'] = 0                       # past a raid's cooldown
            if game == 'bc':
                s, r = self.act(s, 'fair_bc', bets={'cua': 2})
                wins += r['fair']['net'] > 0
            elif game == 'xd':
                s, r = self.act(s, 'fair_xd', side='le', stake=10)
                wins += r['fair']['net'] > 0              # a raid is a lost round
            elif game == 'xs':
                s, r = self.act(s, 'fair_xs', price=2)
                wins += r['fair']['prize'] > 0
            elif game == 'lt':
                s, r = self.act(s, 'fair_loto_buy', tier='nho', n=1)
                rv = fh.round_view(s['journey']['fair']['loto'])
                wins += rv['mine'] <= rv['npc_done']      # a player who marks and calls Kinh in time wins
            else:
                s, r = self.act(s, 'fair_ring_start')
                s, r = self.act(s, 'fair_ring_throw', id=r['fair']['round']['id'], taps=[0, 300, 600, 900, 1200])
                wins += r['fair']['n'] > 0
        validate_state(s)
        return wins / (n or self.N)

    def test_every_luck_stall_is_won_at_its_own_rate(self):
        # owner 08/10 "đảm bảo nhà cái luôn thắng": each stall's fresh draw (fair.BASES) is under what breaks even
        for game in fh.CHANCE_GAMES:
            if game == 'bc':
                continue   # owner 06/10: bầu cua rolls honest dice (tests/test_fair_bc_honest.py), no luck draw
            with self.subTest(game=game):
                rate = self.play(game)
                want = fh.BASES[game] * (1 - fh.RAID_PCT / 100) if game == 'xd' else fh.BASES[game]   # a raid is a loss
                self.assertAlmostEqual(rate, want, delta=.03, msg=(game, rate))
                if game in ('xd', 'lt'):
                    self.assertLess(want, .5)   # the even-money stalls

    def test_spamming_one_stall_cools_to_40_percent(self):
        for game in ('xd', 'xs', 'ring'):
            with self.subTest(game=game):
                rate = self.play(game, run=None, n=1000, skip=fh.RUN_FREE + 12)
                self.assertAlmostEqual(rate, .40, delta=.035, msg=(game, rate))

    def test_long_streaks_cool_only_to_win_p_low(self):
        for game, base in (('bc', fh.LUCK_BASE), ('xd', fh.XD_BASE)):
            j, used = {}, []

            class Spy(random.Random):
                def random(self_inner):
                    x = super().random()
                    used.append(x)
                    return x
            with patch.object(fh, '_rng', Spy(77)):
                results = [fh._draw_luck(j, game, base) for _ in range(60000)]
            rate = sum(results) / len(results)
            self.assertAlmostEqual(rate, base, delta=.01, msg=game)   # the stall's own rate (fair.BASES), streaks and all
            if game == 'xd':
                self.assertLess(base * (1 - fh.RAID_PCT / 100), .5)
            windows = [sum(results[i:i + 1000]) / 1000 for i in range(0, 60000, 1000)]
            self.assertGreaterEqual(min(windows), fh.WIN_P_LOW - .02, game)   # 1000 draws at .485: some noise
            streak = 0   # after four wins in a row the next draw is never worse than WIN_P_LOW
            for won, x in zip(results, used):
                if streak >= fh.STREAK:
                    self.assertEqual(won, x < fh.WIN_P_LOW)
                streak = streak + 1 if won else 0


class TaxNotice(unittest.TestCase):
    def test_period_log_shows_the_calculation(self):
        from game import operations as ops
        with open(ops.__file__, encoding='utf-8') as fh_src:
            src = fh_src.read()
        self.assertIn('× {RULES["tax_percent"]}% = thuế', src)


if __name__ == '__main__':
    unittest.main()
