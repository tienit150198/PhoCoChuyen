"""🏮 Hội chợ dân gian (game/fair.py, game/fair_board.py, game/fair_oaq.py, game/fair_ring.py): payouts, caps, the
back corner's raids, the calendar, idempotent commands, old saves, the lô tô round, ô ăn quan (rules, the opponents,
the prize and its daily cap), ném vòng, the Bảng vàng points and the one-time titles after the fair."""
import datetime
import json
import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from game import accounts, social
from game import fair as fh
from game import fair_board as fb
from game import fair_oaq as oaq
from game import fair_ring as ring
from game import journey as jr
from game import leaderboard as lb
from game import live_effects as lfx
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from game.storage import Store

VN = fh.VN


def at(y, m, d, hh=12, mm=0, ss=0):
    return datetime.datetime(y, m, d, hh, mm, ss, tzinfo=VN).timestamp()


OPEN = at(2026, 10, 4, 20)          # day 2 of the default fair (03/10 → 07/10)
BEFORE = at(2026, 10, 2, 23, 59)
AFTER = at(2026, 10, 8, 0, 0)        # the first second after the fair


class Dice:
    """A stand-in for fair._rng: the dice faces, coins and draws we ask for."""
    def __init__(self, faces=(), coins=(), draws=(), bits=12345):
        self.faces, self.coins, self.draws, self.bits = list(faces), list(coins), list(draws), bits

    def choice(self, seq):
        return self.faces.pop(0) if self.faces else seq[0]

    def randrange(self, n):
        return self.coins.pop(0) if self.coins else 0

    def random(self):
        return self.draws.pop(0) if self.draws else .5

    def getrandbits(self, n):
        return self.bits


def story(wallet=200):
    s = new_state()
    jr.enable_story(s, 4242)
    s['journey']['gender'] = 'female'
    s['journey']['wallet'] = wallet
    validate_state(s)
    return s


class Clock:
    """fh.now under the test's control (each call moves 2 s, so rounds never trip the pause between rounds)."""
    def __init__(self, t):
        self.t = t

    def __call__(self):
        self.t += 2
        return self.t


class FairBase(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {}, clear=False)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop('MNL_FAIR_START', None)
        os.environ.pop('MNL_FAIR_DAYS', None)
        self.clock = Clock(OPEN)
        p = mock.patch.object(fh, 'now', self.clock)
        p.start()
        self.addCleanup(p.stop)
        self.dice(Dice())

    def dice(self, d):
        p = mock.patch.object(fh, '_rng', d)
        p.start()
        self.addCleanup(p.stop)
        return d

    def act(self, s, action, **p):
        return apply_action(s, None, action, p)


class BauCua(FairBase):
    def test_standard_payouts_and_the_bao_bonus(self):
        s = story(100)
        self.dice(Dice(faces=['cua', 'cua', 'tom']))
        s, r = self.act(s, 'fair_bc', bets={'cua': 5, 'ca': 3})
        # cua twice: stake back + 1:1 per die = 15; ca lost 3 → net +7
        self.assertEqual((r['fair']['back'], r['fair']['net']), (15, 7))
        self.assertEqual(s['journey']['wallet'], 107)
        self.dice(Dice(faces=['nai', 'nai', 'nai']))
        s, r = self.act(s, 'fair_bc', bets={'nai': 2})
        self.assertEqual((r['fair']['back'], r['fair']['bao']), (2 * (1 + fh.BAO), 'nai'))
        self.assertIn('f_bao', s['journey']['titles'])
        self.dice(Dice(faces=['ga', 'bau', 'ca']))
        s, r = self.act(s, 'fair_bc', bets={'tom': 4})
        self.assertEqual(r['fair']['net'], -4)
        validate_state(s)

    def test_house_edge_is_slight(self):
        """Exact return of one xu on a face over the 216 outcomes."""
        faces = fh.FACES
        back = 0
        for a in faces:
            for b in faces:
                for c in faces:
                    k = [a, b, c].count('bau')
                    back += 0 if not k else (1 + fh.BAO if k == 3 else 1 + k)
        rtp = back / 216
        self.assertGreater(rtp, .95)
        self.assertLess(rtp, 1)

    def test_stake_rules(self):
        s = story(100)
        for bets in ({}, {'cop': 1}, {'cua': 0}, {'cua': 21}, {'cua': 10, 'tom': 11}, {'cua': 1.5}, {'cua': True}):
            with self.assertRaises(GameError, msg=bets):
                self.act(s, 'fair_bc', bets=bets)
        with self.assertRaises(GameError):
            apply_action(s, None, 'fair_bc', {'bets': {'cua': 1}, 'extra': 1})

    def test_no_loans(self):
        s = story(3)
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_bc', bets={'cua': 5})
        self.assertEqual(e.exception.code, 'fair_wallet')
        s['journey']['wallet'] = -10
        with self.assertRaises(GameError):
            self.act(s, 'fair_bc', bets={'cua': 1})

    def test_daily_net_loss_cap_and_a_win_gives_room_back(self):
        s = story(1000)
        self.dice(Dice(faces=['ga'] * 300))
        lost = 0
        while lost + 20 <= fh.DAY_CAP:
            s, r = self.act(s, 'fair_bc', bets={'cua': 20})
            lost += 20
        left = fh.DAY_CAP - lost
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_bc', bets={'cua': 20})
        self.assertEqual(e.exception.code, 'fair_enough')
        s, _ = self.act(s, 'fair_bc', bets={'cua': left})
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertIn('đủ rồi', e.exception.message)
        self.assertEqual(s['journey']['fair']['net'], -fh.DAY_CAP)
        self.assertTrue(public_state(s)['fair']['today']['done'])
        # the next Vietnam day starts afresh
        self.clock.t = at(2026, 10, 5, 8)
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(s['journey']['fair']['net'], -1)

    def test_too_fast(self):
        s = story(100)
        self.clock.t = OPEN
        with mock.patch.object(fh, 'now', lambda: OPEN):
            s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
            with self.assertRaises(GameError) as e:
                self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(e.exception.code, 'fair_slow')

    def test_one_wallet_row_per_game_and_day(self):
        s = story(500)
        self.dice(Dice(faces=['cua'] * 3 + ['ga'] * 3 + ['cua', 'tom', 'ga']))
        s, _ = self.act(s, 'fair_bc', bets={'cua': 2})
        s, _ = self.act(s, 'fair_loto_buy')
        s, _ = self.act(s, 'fair_bc', bets={'cua': 2})
        s, _ = self.act(s, 'fair_bc', bets={'cua': 2})
        rows = [r for r in s['journey']['history'] if r['kind'] == 'fair']
        self.assertEqual([r['label'] for r in rows], ['🦀 Bầu cua hội chợ · 3 ván', '🎱 Lô tô hội chợ · 1 tờ'])
        self.assertEqual(rows[0]['amount'], (2 * (1 + fh.BAO) - 2) - 2 + 2)   # bão, nothing, one cua
        self.assertEqual(sum(r['amount'] for r in rows), s['journey']['wallet'] - 500)
        validate_state(s)


class ChieuTrong(FairBase):
    def test_even_money(self):
        s = story(200)
        self.dice(Dice(coins=[1, 1, 0, 0], draws=[.9]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=30)
        self.assertEqual((r['fair']['raid'], r['fair']['even'], r['fair']['net']), (False, True, 30))
        self.dice(Dice(coins=[1, 0, 0, 0], draws=[.9]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertEqual(r['fair']['net'], -10)
        self.assertEqual(s['journey']['wallet'], 220)

    def test_stakes(self):
        s = story(200)
        for p in (dict(side='chan', stake=9), dict(side='chan', stake=51), dict(side='x', stake=10), dict(stake=10)):
            with self.assertRaises(GameError, msg=p):
                apply_action(s, None, 'fair_xd', p)

    def test_raid_confiscates_fines_and_closes_the_corner(self):
        s = story(200)
        self.dice(Dice(draws=[0.0]))
        s, r = self.act(s, 'fair_xd', side='le', stake=40)
        f = r['fair']
        self.assertTrue(f['raid'])
        self.assertEqual((f['stake'], f['fine'], f['net']), (40, 20, -60))
        self.assertEqual(s['journey']['wallet'], 140)
        self.assertIn('f_raid', s['journey']['titles'])
        self.assertIn('Công an phường', r['message'])
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_xd', side='le', stake=10)
        self.assertEqual(e.exception.code, 'fair_raided')
        self.assertGreater(public_state(s)['fair']['raid_left'], 0)
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})   # the front stalls stay open
        self.clock.t += fh.RAID_COOLDOWN
        self.dice(Dice(draws=[.9], coins=[0, 0, 0, 0]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertFalse(r['fair']['raid'])
        validate_state(s)

    def test_the_fine_never_takes_the_wallet_below_zero(self):
        s = story(12)
        self.dice(Dice(draws=[0.0]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertEqual((r['fair']['fine'], s['journey']['wallet']), (2, 0))
        self.assertFalse(s['journey']['in_debt'])

    def test_only_the_back_corner_is_ever_raided(self):
        """A raid draw of 0 every time: bầu cua and lô tô never meet the police; the back corner always does."""
        s = story(1000)
        self.dice(Dice(draws=[0.0] * 50, faces=['ga'] * 90))
        for _ in range(10):
            s, r = self.act(s, 'fair_bc', bets={'cua': 1})
            self.assertNotIn('raid', r['fair'])
        s, r = self.act(s, 'fair_loto_buy')
        self.assertNotIn('raid', r['fair'])
        self.assertEqual(s['journey']['fair']['stats']['raids'], 0)
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertTrue(r['fair']['raid'])

    def test_the_day_cap_counts_the_fine(self):
        s = story(1000)
        s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(OPEN), net=-(fh.DAY_CAP - 20), ed=fh.edition())
        with self.assertRaises(GameError) as e:   # 20 at stake + 10 fine > 20 left
            self.act(s, 'fair_xd', side='chan', stake=20)
        self.assertEqual(e.exception.code, 'fair_enough')
        self.dice(Dice(draws=[0.0]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=13)   # 13 + 6 fits
        self.assertGreaterEqual(s['journey']['fair']['net'], -fh.DAY_CAP)


class Calendar(FairBase):
    def test_closed_outside_the_window(self):
        s = story()
        for t in (BEFORE, AFTER, at(2027, 1, 1)):
            self.clock.t = t
            for action, p in (('fair_bc', {'bets': {'cua': 1}}), ('fair_xd', {'side': 'chan', 'stake': 10}), ('fair_loto_buy', {})):
                with self.assertRaises(GameError) as e:
                    apply_action(s, None, action, p)
                self.assertEqual(e.exception.code, 'fair_closed')
        self.clock.t = BEFORE
        self.assertIn('chưa mở', fh.SOON)
        v = public_state(s)['fair']
        self.assertEqual((v['show'], v['soon'], v['open']), (True, True, False))
        self.clock.t = AFTER
        v = public_state(s)['fair']
        self.assertEqual((v['show'], v['over'], v['open']), (True, True, False))
        self.clock.t = at(2026, 12, 1)
        self.assertEqual(public_state(s)['fair']['show'], False)

    def test_window_and_override(self):
        a, b = fh.window()
        self.assertEqual((a, b), (int(at(2026, 10, 3, 0)), int(at(2026, 10, 8, 0))))
        self.assertTrue(fh.is_open(at(2026, 10, 3, 0)) and fh.is_open(at(2026, 10, 7, 23, 59)) and not fh.is_open(AFTER))
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': '2026-11-20', 'MNL_FAIR_DAYS': '3'}):
            self.assertEqual(fh.window(), (int(at(2026, 11, 20, 0)), int(at(2026, 11, 23, 0))))
            self.assertEqual(fh.edition(), 'fair20261120')
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': 'not a date'}):
            self.assertEqual(fh.edition(), 'fair20261003')

    def test_story_only(self):
        s = new_state()
        with self.assertRaises(GameError):
            apply_action(s, None, 'fair_bc', {'bets': {'cua': 1}})
        self.assertFalse(public_state(s)['fair']['show'])


class OldSaves(FairBase):
    def test_a_save_without_the_fair_loads_and_validates(self):
        s = story()
        self.assertNotIn('fair', s['journey'])
        validate_state(migrate_state(s))
        v = public_state(s)['fair']
        self.assertEqual(v['points']['total'], 0)
        self.assertIsNone(v['loto'])

    def test_bad_fair_data_is_refused(self):
        s = story()
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        validate_state(s)
        for k, v in (('net', 'x'), ('rounds', -1), ('dpts', fh.POINTS_DAY + 1), ('ed', 'nope'), ('stats', {}), ('loto', {'slot': 1})):
            bad = json.loads(json.dumps(s))
            bad['journey']['fair'][k] = v
            with self.assertRaises(GameError, msg=k):
                validate_state(bad)
        bad = json.loads(json.dumps(s))
        bad['journey']['fair']['extra'] = 1
        with self.assertRaises(GameError):
            validate_state(bad)


def winning_rs(want_win: bool, slot: int) -> int:
    for rs in range(5000):
        rv = fh.round_view(dict(slot=slot, rs=rs, at=0, stage='play'))
        if (rv['mine'] <= rv['npc_done']) == want_win:
            return rs
    raise AssertionError('no such round')


class Loto(FairBase):
    def test_cards(self):
        r = random.Random(7)
        for _ in range(200):
            c = fh.card(r)
            self.assertEqual([len(row) for row in c], [5, 5, 5])
            nums = [n for row in c for n in row]
            self.assertEqual(len(set(nums)), 15)
            self.assertTrue(all(1 <= n <= 90 for n in nums))
        self.assertEqual(sorted(fh.calls(123)), list(range(1, 91)))
        self.assertEqual(fh.calls(123), fh.calls(123), 'the same minute calls the same numbers for everyone')
        self.assertNotEqual(fh.calls(123), fh.calls(124))

    def _buy(self, s, win):
        slot = int(self.clock.t // 60) + 1
        self.dice(Dice(bits=winning_rs(win, slot)))
        self.clock.t = slot * 60 + 1
        s, r = self.act(s, 'fair_loto_buy')
        return s, fh.round_view(s['journey']['fair']['loto'])

    def test_kinh_wins_the_prize_once(self):
        s = story(100)
        s, rv = self._buy(s, True)
        self.assertEqual(s['journey']['wallet'], 100 - fh.LOTO_PRICE)
        pos = {n: i for i, n in enumerate(rv['seq'])}
        row = min(range(3), key=lambda i: max(pos[n] for n in rv['card'][i]))
        k = max(pos[n] for n in rv['card'][row]) + 1
        with self.assertRaises(GameError) as e:   # one call too early: the row is not full
            self.act(s, 'fair_loto_kinh', row=row, at=k - 1)
        self.assertEqual(e.exception.code, 'fair_loto_short')
        s, r = self.act(s, 'fair_loto_kinh', row=row, at=k)
        self.assertTrue(r['fair']['won'])
        self.assertEqual(s['journey']['wallet'], 100 - fh.LOTO_PRICE + fh.LOTO_PRIZE)
        self.assertIn('f_loto', s['journey']['titles'])
        with self.assertRaises(GameError):
            self.act(s, 'fair_loto_kinh', row=row, at=k)
        validate_state(s)

    def test_late_kinh_loses(self):
        s = story(100)
        s, rv = self._buy(s, False)
        pos = {n: i for i, n in enumerate(rv['seq'])}
        row = min(range(3), key=lambda i: max(pos[n] for n in rv['card'][i]))
        k = max(pos[n] for n in rv['card'][row]) + 1
        self.assertGreater(k, rv['npc_done'])
        s, r = self.act(s, 'fair_loto_kinh', row=row, at=k)
        self.assertFalse(r['fair']['won'])
        self.assertEqual(r['fair']['by'], rv['npc_name'])
        self.assertEqual(s['journey']['fair']['loto']['stage'], 'lost')
        self.assertEqual(s['journey']['wallet'], 100 - fh.LOTO_PRICE)

    def test_public_round_and_fold(self):
        s = story(100)
        s, rv = self._buy(s, True)
        v = public_state(s)['fair']['loto']
        self.assertEqual((v['stage'], v['card'], v['seq'], v['npc_done']), ('play', rv['card'], rv['seq'], rv['npc_done']))
        self.assertEqual(len(v['npcs']), fh.LOTO_NPCS)
        s, _ = self.act(s, 'fair_loto_fold')
        self.assertEqual(s['journey']['fair']['loto']['stage'], 'lost')

    def test_rtp_with_perfect_play(self):
        """Over many rounds a perfect player gets back a bit less than the card price."""
        wins = sum(1 for rs in range(3000) for rv in [fh.round_view(dict(slot=rs * 7, rs=rs, at=0, stage='play'))] if rv['mine'] <= rv['npc_done'])
        rtp = wins / 3000 * fh.LOTO_PRIZE / fh.LOTO_PRICE
        self.assertGreater(rtp, .85)
        self.assertLess(rtp, 1.03)


class Points(FairBase):
    def test_points_rules_and_the_daily_cap(self):
        s = story(1000)
        self.dice(Dice(faces=['cua', 'ga', 'ga'] + ['ga'] * 3))
        s, r = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(r['fair']['points'], 2)            # the day + a face that came up
        s, r = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(r['fair']['points'], 0)            # nothing came up
        self.dice(Dice(draws=[0.0]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertEqual(r['fair']['points'], 0)            # raided: nothing
        self.dice(Dice(faces=['cua'] * 300))
        for _ in range(40):
            s, r = self.act(s, 'fair_bc', bets={'cua': 1})
        f = s['journey']['fair']
        self.assertEqual((f['dpts'], f['pts']), (fh.POINTS_DAY, fh.POINTS_DAY))
        self.clock.t = at(2026, 10, 5, 9)
        s, r = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(r['fair']['points'], 2)
        self.assertEqual((s['journey']['fair']['pts'], s['journey']['fair']['pdays']), (fh.POINTS_DAY + 2, 2))
        self.assertEqual(lb.summary(s)[fh.edition()][:1], (fh.POINTS_DAY + 2,))

    def test_no_points_after_the_close(self):
        s = story(100)
        self.clock.t = at(2026, 10, 7, 23, 58)
        slot = int(self.clock.t // 60) + 1
        self.dice(Dice(bits=winning_rs(True, slot)))
        self.clock.t = slot * 60 + 1
        s, r = self.act(s, 'fair_loto_buy')
        before = s['journey']['fair']['pts']
        rv = fh.round_view(s['journey']['fair']['loto'])
        pos = {n: i for i, n in enumerate(rv['seq'])}
        row = min(range(3), key=lambda i: max(pos[n] for n in rv['card'][i]))
        self.clock.t = AFTER + 30
        s, r = self.act(s, 'fair_loto_kinh', row=row, at=max(pos[n] for n in rv['card'][row]) + 1)
        self.assertTrue(r['fair']['won'])                    # the card bought while open is paid
        self.assertEqual(s['journey']['fair']['pts'], before)  # but the board is closed

    def test_a_new_edition_starts_from_zero(self):
        s = story(100)
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertGreater(s['journey']['fair']['pts'], 0)
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': '2026-12-01'}):
            self.assertEqual(fh.points_of(s['journey']), (0, 0))
            self.assertNotIn(fh.edition(), lb.summary(s))


def board(b, q=(1, 1), cap=(0, 0, 0, 0), ply=0):
    g = dict(b=list(b), q=list(q), cap=list(cap), ply=ply)
    assert oaq.valid(g), g
    return g


class OAQRules(unittest.TestCase):
    """game/fair_oaq.py: sowing, captures (chained), quan non, rải quân, the end."""

    def test_sow_pick_up_and_capture(self):
        g = oaq.new_game()
        trace = []
        got = oaq.play(g, 0, 1, 1, trace)
        # 5 dân from ô 1 to 2..6, ô 7 is full: take its 5 on to 8..11 and 0; ô 1 is empty, ô 2 (6) is captured
        self.assertEqual(got, 6)
        self.assertEqual(g['b'], [1, 0, 0, 6, 6, 6, 1, 0, 6, 6, 6, 6])
        self.assertEqual(g['cap'], [6, 0, 0, 0])
        self.assertEqual([e[0] for e in trace].count('pick'), 2)
        self.assertEqual(trace[-1], ['cap', 2, 6, 0])
        self.assertTrue(oaq.valid(g))

    def test_chained_captures_take_a_quan(self):
        # ô 1 (1 dân) → 2; 3 empty: take 4 (3); 5 empty: take the right quan ô (its quan gone, 2 dân); 7 is full: stop
        g = board([0, 1, 0, 0, 3, 0, 2, 5, 5, 5, 5, 5], q=(1, 0), cap=(9, 1, 10, 0))
        self.assertEqual(oaq.play(g, 0, 1, 1), 5)
        self.assertEqual(g['cap'][:2], [14, 1])
        # and a quan ô with its quan and enough dân is taken whole: 5 dân + the quan
        g = board([0, 0, 0, 1, 0, 0, 5, 5, 5, 5, 5, 5], cap=(9, 0, 10, 0))
        self.assertEqual(oaq.play(g, 0, 3, 1), 5 + oaq.QUAN)
        self.assertEqual((g['q'], g['b'][6]), ([1, 0], 0))

    def test_quan_non_cannot_be_taken_and_a_quan_ends_the_turn(self):
        g = board([0, 0, 0, 1, 0, 0, 2, 5, 5, 5, 5, 5], cap=(12, 0, 10, 0))
        trace = []
        self.assertEqual(oaq.play(g, 0, 3, 1, trace), 0)
        self.assertEqual(trace[-1], ['non', 6])
        g = board([0, 0, 0, 0, 1, 0, 0, 5, 5, 5, 5, 5], cap=(14, 0, 10, 0))
        self.assertEqual(oaq.play(g, 0, 4, 1), 0)           # the last dân lands next to the quan ô: the turn ends
        self.assertEqual(g['b'][5], 1)

    def test_two_empty_in_a_row_end_the_turn(self):
        g = board([0, 1, 0, 0, 0, 3, 0, 5, 5, 5, 5, 5], cap=(11, 0, 10, 0))
        self.assertEqual(oaq.play(g, 0, 1, 1), 0)

    def test_rai_quan_and_the_end(self):
        g = board([3, 0, 0, 0, 0, 0, 2, 5, 5, 5, 5, 5], cap=(8, 0, 12, 0))
        trace = []
        self.assertTrue(oaq.begin_turn(g, 0, trace))
        self.assertEqual((g['b'][1:6], g['cap'][0], trace), ([1] * 5, 3, [['seed', 0]]))
        g = board([3, 0, 0, 0, 0, 0, 2, 5, 5, 5, 5, 5], cap=(4, 0, 16, 0))
        self.assertFalse(oaq.begin_turn(g, 0))             # nothing to rải: the game ends, the rows go home
        self.assertTrue(oaq.valid(g))
        self.assertEqual(sum(g['b']), 0)
        g = board([0, 2, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0], q=(0, 0), cap=(20, 1, 25, 1))
        self.assertFalse(oaq.begin_turn(g, 1))             # hết quan, tàn dân
        self.assertEqual((oaq.score(g, 0), oaq.score(g, 1)), (22 + oaq.QUAN, 28 + oaq.QUAN))

    def test_random_games_keep_every_dan_and_end(self):
        rng = random.Random(7)
        for i in range(150):
            g, side = oaq.new_game(), 0
            while oaq.begin_turn(g, side):
                moves = oaq.legal(g, side)
                c, d = rng.choice(moves) if side == 0 or i % 3 == 0 else oaq.ai_move(g, 'de' if i % 2 else 'kho', rng, side)
                oaq.play(g, side, c, d)
                self.assertTrue(oaq.valid(g))
                side = 1 - side
            self.assertEqual(oaq.score(g, 0) + oaq.score(g, 1), 50 + 2 * oaq.QUAN)
            self.assertLessEqual(g['ply'], oaq.MAX_PLY)

    def test_the_opponents_strength(self):
        """Simple but not dumb: a greedy player usually beats Bé Bi and rarely Ông Hai; looking two turns ahead
        gives a fair chance against Ông Hai."""
        def player(depth):
            def pick(g, rng):
                vals = []
                for c, d in oaq.legal(g, 0):
                    k = oaq.copy(g)
                    oaq.play(k, 0, c, d)
                    vals.append((oaq._search(k, 1, 0, depth - 1), rng.random(), (c, d)))
                return max(vals)[2]
            return pick

        def wins(p, level, n=50):
            rng = random.Random(11)
            won = 0
            for _ in range(n):
                g, side = oaq.new_game(), 0
                while oaq.begin_turn(g, side):
                    c, d = p(g, rng) if side == 0 else oaq.ai_move(g, level, rng)
                    oaq.play(g, side, c, d)
                    side = 1 - side
                won += oaq.score(g, 0) > oaq.score(g, 1)
            return won / n
        self.assertGreater(wins(player(1), 'de'), .5)
        self.assertLess(wins(player(1), 'kho'), .25)
        self.assertTrue(.15 < wins(player(2), 'kho') < .75)


def weakest(g, level, rng, side=1):
    """A stand-in opponent that gives everything away (to reach a won game quickly)."""
    best = None
    for c, d in oaq.legal(g, side):
        k = oaq.copy(g)
        v = oaq.play(k, side, c, d)
        if best is None or v < best[0]:
            best = (v, (c, d))
    return best[1]


def greedy_move(g):
    best = None
    for c, d in oaq.legal(g, 0):
        k = oaq.copy(g)
        v = oaq.play(k, 0, c, d)
        if best is None or v > best[0]:
            best = (v, (c, d))
    return best[1]


class OAQStall(FairBase):
    def finish(self, s):
        r = None
        while s['journey']['fair']['oaq']['stage'] == 'play':
            c, d = greedy_move(s['journey']['fair']['oaq']['g'])
            s, r = self.act(s, 'fair_oaq_move', cell=c, dir=d)
            self.assertTrue(r['fair']['trace'])
        return s, r

    def test_a_win_pays_the_level_prize_and_points(self):
        s = story(0)
        with mock.patch.object(oaq, 'ai_move', weakest):
            s, r = self.act(s, 'fair_oaq_start', lv='kho')
            self.assertEqual(r['fair']['points'], fh.PT_DAY)          # the day played: no chance round needed
            self.assertEqual(r['fair']['view']['b'], oaq.new_game()['b'])
            s, r = self.finish(s)
        end = r['fair']['end']
        self.assertEqual((end['stage'], end['prize'], end['points']), ('won', fh.OAQ_PRIZE['kho'], fh.PT_OAQ))
        j = s['journey']
        self.assertEqual(j['wallet'], fh.OAQ_PRIZE['kho'])
        self.assertIn('f_oaq', j['titles'])
        self.assertEqual(j['fair']['net'], 0)                         # earning is not betting: the loss cap is untouched
        self.assertEqual(j['history'][-1]['label'], f'{fh.LABELS["oaq"]} · 1 ván thắng')
        validate_state(s)

    def test_the_daily_earning_cap(self):
        s = story(0)
        with mock.patch.object(oaq, 'ai_move', weakest):
            prizes = []
            for _ in range(4):
                s, _ = self.act(s, 'fair_oaq_start', lv='kho')
                s, r = self.finish(s)
                prizes.append(r['fair']['end']['prize'])
        self.assertEqual(prizes, [30, 30, 30, 0])
        self.assertTrue(r['fair']['end']['capped'])
        self.assertEqual(s['journey']['wallet'], fh.EARN_DAY['oaq'])
        self.assertEqual(public_state(s)['fair']['earn']['oaq'], dict(today=90, cap=90, left=0))
        self.clock.t = at(2026, 10, 5, 9)                              # a new day
        with mock.patch.object(oaq, 'ai_move', weakest):
            s, _ = self.act(s, 'fair_oaq_start', lv='de')
            s, r = self.finish(s)
        self.assertEqual(r['fair']['end']['prize'], fh.OAQ_PRIZE['de'])

    def test_a_loss_costs_nothing(self):
        s = story(50)
        s, _ = self.act(s, 'fair_oaq_start', lv='de')
        s, r = self.act(s, 'fair_oaq_quit')
        self.assertEqual((s['journey']['fair']['oaq']['stage'], s['journey']['wallet']), ('lost', 50))
        s, _ = self.act(s, 'fair_oaq_start', lv='kho')
        s, _ = self.act(s, 'fair_oaq_start', lv='de')                  # a new game gives the old one up
        self.assertEqual(s['journey']['fair']['stats']['oaq'], 3)
        with self.assertRaises(GameError):
            self.act(s, 'fair_oaq_move', cell=8, dir=1)                # not your ô
        with self.assertRaises(GameError):
            self.act(s, 'fair_oaq_move', cell=1, dir=2)
        with self.assertRaises(GameError):
            self.act(s, 'fair_oaq_move', cell=1, dir=True)

    def test_a_game_begun_while_open_can_be_finished(self):
        s = story(0)
        self.clock.t = AFTER - 60
        with mock.patch.object(oaq, 'ai_move', weakest):
            s, _ = self.act(s, 'fair_oaq_start', lv='de')
            self.clock.t = AFTER + 10
            s, r = self.finish(s)
            self.assertEqual(r['fair']['end']['prize'], fh.OAQ_PRIZE['de'])
            self.assertEqual(r['fair']['end']['points'], 0)          # the board is closed
            with self.assertRaises(GameError):
                self.act(s, 'fair_oaq_start', lv='de')

    def test_bad_game_data_is_refused(self):
        s = story()
        s, _ = self.act(s, 'fair_oaq_start', lv='de')
        validate_state(s)
        bad = json.loads(json.dumps(s))
        bad['journey']['fair']['oaq']['g']['b'][1] += 1              # a dân out of nowhere
        with self.assertRaises(GameError):
            validate_state(bad)
        bad = json.loads(json.dumps(s))
        bad['journey']['fair']['earn']['oaq'] = fh.EARN_DAY['oaq'] + 1
        with self.assertRaises(GameError):
            validate_state(bad)


def aim(p, skip=()):
    """Throw times (ms) that ring each bottle once (in order of time), GAP apart."""
    taps, t, todo = [], 0, [i for i in range(ring.BOTTLES) if i not in skip]
    while todo and t < 60000:
        x = ring.x_at(p, t)
        for i in todo:
            if abs(x - p['xs'][i]) < 1 and (not taps or t - taps[-1] >= ring.GAP):
                taps.append(t)
                todo.remove(i)
                break
        t += 1
    return taps


class RingToss(FairBase):
    def start(self, s):
        s, r = self.act(s, 'fair_ring_start')
        return s, r['fair']['round']

    def test_formula_and_judge(self):
        p = dict(xs=[10, 30, 50, 70, 90], period=2000, phase=0.0)
        self.assertEqual((ring.x_at(p, 0), ring.x_at(p, 500), ring.x_at(p, 1000), ring.x_at(p, 1500)), (0, 50, 100, 50))
        self.assertEqual(ring.judge(p, [500, 520, 1500, 100, 1900]), [2, -1, -1, 0, -1])

    def test_all_five_pays_the_bonus_points_and_title(self):
        s = story(0)
        s, rd = self.start(s)
        taps = aim(rd)
        self.assertEqual(len(taps), 5)
        self.clock.t += taps[-1] / 1000
        s, r = self.act(s, 'fair_ring_throw', id=rd['id'], taps=taps)
        self.assertEqual((r['fair']['n'], r['fair']['prize']), (5, 5 * fh.RING_HIT + fh.RING_ALL))
        self.assertEqual(r['fair']['points'], fh.PT_RING5)
        self.assertIn('f_ring', s['journey']['titles'])
        self.assertIsNone(public_state(s)['fair']['ring'])          # the round is done
        with self.assertRaises(GameError):                          # and paid once
            self.act(s, 'fair_ring_throw', id=rd['id'], taps=taps)
        validate_state(s)

    def test_misses_and_three_hits(self):
        s = story(0)
        s, rd = self.start(s)
        taps = aim(rd, skip=(3, 4))
        last = taps[-1]
        taps += [last + 300, last + 600]
        hits = ring.judge(ring.params(rd['id']), taps)
        self.clock.t += 60
        s, r = self.act(s, 'fair_ring_throw', id=rd['id'], taps=taps)
        n = sum(h >= 0 for h in hits)
        self.assertGreaterEqual(n, 3)
        self.assertEqual((r['fair']['n'], r['fair']['prize']), (n, n * fh.RING_HIT + (fh.RING_ALL if n == 5 else 0)))

    def test_throws_must_be_plausible(self):
        s = story(0)
        s, rd = self.start(s)
        taps = aim(rd)
        for bad in (taps[:4], [taps[0]] * 5, [t + 30000 for t in taps], [-1] + taps[1:], taps[:4] + [taps[3] + 10]):
            with self.assertRaises(GameError, msg=bad):
                self.act(s, 'fair_ring_throw', id=rd['id'], taps=bad)
        with self.assertRaises(GameError):
            self.act(s, 'fair_ring_throw', id=rd['id'] + 1, taps=taps)

    def test_the_daily_earning_cap(self):
        s = story(0)
        paid = []
        for _ in range(4):
            s, rd = self.start(s)
            taps = aim(rd)
            self.clock.t += 60
            s, r = self.act(s, 'fair_ring_throw', id=rd['id'], taps=taps)
            paid.append(r['fair']['prize'])
            self.dice(Dice(bits=12345 + len(paid)))
        self.assertEqual(paid, [15, 15, 15, 0])
        self.assertEqual(s['journey']['wallet'], fh.EARN_DAY['ring'])
        self.assertEqual(s['journey']['fair']['net'], 0)


class StoreBase(FairBase):
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'g.db', story=True)
        self.addCleanup(self.store.close_pool)
        social.ensure(self.store)
        lb.clear_cache()
        self.addCleanup(lb.clear_cache)
        fb._done.clear()
        self.addCleanup(fb._done.clear)
        self.n = 0

    def player(self, name, wallet=500):
        token, _, _ = self.store.session()
        self.n += 1
        out = accounts.register(self.store, token, dict(username=f'fair{self.n}x', password='mat-khau-dai-1', confirm='mat-khau-dai-1', display=name))
        tok = out['token']
        from game import marriage as mr

        def fn(s):
            s['name'] = name
            s['journey'].update(gender='male', intro=True, wallet=wallet)
        mr._mutate(self.store, {self.store.key(tok): fn})
        return tok

    def cmd(self, tok, action, payload, rid=None):
        self.n += 1
        rev = self.store.read(tok)[1]
        return self.store.command(tok, rid or f'fair-test-{self.n:05d}', rev, None, action, payload)


class Idempotent(StoreBase):
    def test_a_retried_request_is_paid_once(self):
        tok = self.player('Lan')
        rev = self.store.read(tok)[1]
        self.dice(Dice(faces=['ga'] * 9))
        a = self.store.command(tok, 'fair-retry-0001', rev, None, 'fair_bc', {'bets': {'cua': 5}})
        b = self.store.command(tok, 'fair-retry-0001', rev, None, 'fair_bc', {'bets': {'cua': 5}})
        self.assertTrue(b['replayed'])
        self.assertEqual(a['result'], b['result'])
        self.assertEqual(self.store.read(tok)[0]['journey']['wallet'], 495)
        with self.assertRaises(GameError):   # the same id with another bet
            self.store.command(tok, 'fair-retry-0001', rev, None, 'fair_bc', {'bets': {'cua': 6}})


class Board(StoreBase):
    def score(self, tok, rounds):
        self.dice(Dice(faces=['cua'] * (3 * rounds)))
        for _ in range(rounds):
            self.cmd(tok, 'fair_bc', {'bets': {'cua': 1}})

    def test_board_settle_once_and_titles_paid_once(self):
        a, b, c = self.player('Anh Ba'), self.player('Chị Tư'), self.player('Cô Năm')
        self.score(b, 5)
        self.score(a, 9)
        self.score(c, 5)    # same points as b, reached later
        ed = fh.edition()
        view = lb.view(self.store, ed, 20, a)
        self.assertEqual([r['name'] for r in view['rows']], ['Anh Ba', 'Chị Tư', 'Cô Năm'])
        self.assertEqual([r['points'] for r in view['rows']], [10, 6, 6])
        self.assertEqual(view['me']['rank'], 1)
        self.assertFalse(view['fair']['settled'])
        self.assertEqual([t['name'] for t in view['fair']['tiers']], ['Vua trò chơi', 'Cao thủ hội chợ'])
        self.assertEqual(lb.parse_query({'board': ed}), (ed, 50))
        # not before the end
        self.assertIsNone(fb.settle(self.store, AFTER - 1))
        got = fb.settle(self.store, AFTER + fb.GRACE)
        self.assertEqual([(w['rank'], w['title']) for w in got], [(1, 'f_king'), (2, 'f_master'), (3, 'f_master')])
        self.assertIsNone(fb.settle(self.store, AFTER + 3600))
        fb._done.clear()   # another process: the mark in the database stops it
        self.assertIsNone(fb.settle(self.store, AFTER + 3600))
        with self.store.connect() as db:
            n = db.execute("SELECT COUNT(*) FROM live_effects WHERE kind='title'").fetchone()[0]
        self.assertEqual(n, 3)
        # paid on the next load, once
        self.assertTrue(lfx.on_load(self.store, a, self.store.read(a)[0]))
        self.assertFalse(lfx.on_load(self.store, a, self.store.read(a)[0]))
        sa = self.store.read(a)[0]
        self.assertIn('f_king', sa['journey']['titles'])
        validate_state(migrate_state(sa))
        lfx.on_load(self.store, c, self.store.read(c)[0])
        self.assertIn('f_master', self.store.read(c)[0]['journey']['titles'])
        view = lb.view(self.store, ed, 20, c)
        self.assertTrue(view['fair']['settled'])
        self.assertEqual([(w['rank'], w['name'], w['me']) for w in view['fair']['winners']],
                         [(1, 'Anh Ba', False), (2, 'Chị Tư', False), (3, 'Cô Năm', True)])

    def test_hidden_players_are_not_ranked_or_crowned(self):
        a, b = self.player('Anh Ba'), self.player('Chị Tư')
        self.score(a, 9)
        self.score(b, 3)
        lb.set_visible(self.store, a, self.store.read(a)[0], False)
        lb.clear_cache()
        rows = lb.view(self.store, fh.edition(), 20, a)
        self.assertEqual([r['name'] for r in rows['rows']], ['Chị Tư'])
        self.assertIsNotNone(rows['me']['rank'])   # still sees their own place
        got = fb.settle(self.store, AFTER + fb.GRACE)
        self.assertEqual([(w['rank'], w['title']) for w in got], [(1, 'f_king')])
        self.assertEqual(got[0]['sid'], self.store.key(b))


if __name__ == '__main__':
    unittest.main()
