"""🏮 Hội chợ dân gian (game/fair.py, game/fair_board.py, game/fair_oaq.py, game/fair_ring.py): payouts, caps, the
back corner's raids, the calendar, idempotent commands, old saves, the lô tô round, ô ăn quan (rules, the opponents,
the prize and its daily cap), ném vòng, the Bảng vàng (xu won) and the one-time titles after the fair."""
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
from game import fair_cash as fc
from game import fair_food as ff
from game import fair_photo as fp
from game import needs as nd
from game import fair_ring as ring
from game import journey as jr
from game import leaderboard as lb
from game import live_effects as lfx
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state
from game.storage import Store

VN = fh.VN


def at(y, m, d, hh=12, mm=0, ss=0):
    return datetime.datetime(y, m, d, hh, mm, ss, tzinfo=VN).timestamp()


OPEN = at(2026, 10, 10, 20)         # day 2 of the default fair (09/10 → 13/10, owner 08/10: the fair opens again)
BEFORE = at(2026, 10, 8, 23, 59)
AFTER = at(2026, 10, 14, 0, 0)       # the first second after the fair


class Dice:
    """A stand-in for fair._rng: the dice faces, coins and draws we ask for."""
    def __init__(self, faces=(), coins=(), draws=(), bits=12345):
        self.faces, self.coins, self.draws, self.bits = list(faces), list(coins), list(draws), bits

    def choice(self, seq):
        return self.faces.pop(0) if self.faces and self.faces[0] in seq else seq[0]

    def randrange(self, n):
        return self.coins.pop(0) if self.coins else 0

    def random(self):
        return self.draws.pop(0) if self.draws else .25

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
        g = mock.patch.object(fh, 'BC_GAP_MS', 0)   # the test clock steps 2 s a call; test_the_bowl_opens_after_5_s checks the gap
        g.start()
        self.addCleanup(g.stop)
        # The police checks' own tests play as if well into a session; the quiet start (B6, GRACE_S / GRACE_ROUNDS)
        # has its own tests (tests/test_fair_police_grace.py), which put the real values back.
        for name in ('GRACE_S', 'GRACE_ROUNDS'):
            q = mock.patch.object(fh, name, 0)
            q.start()
            self.addCleanup(q.stop)
        self.dice(Dice())

    def dice(self, d):
        p = mock.patch.object(fh, '_rng', d)
        p.start()
        self.addCleanup(p.stop)
        return d

    def act(self, s, action, **p):
        return apply_action(s, None, action, p)


class BauCua(FairBase):
    def test_the_bowl_opens_after_5_s(self):
        s = story(100)                                     # owner 03/10: mỗi lần bấm đợi 5s để mở
        with mock.patch.object(fh, 'BC_GAP_MS', 4800):
            s, r = self.act(s, 'fair_bc', bets={'cua': 1})
            with self.assertRaises(GameError) as e:
                self.act(s, 'fair_bc', bets={'cua': 1})
            self.assertEqual(e.exception.code, 'fair_slow')
            self.clock.t += 5
            s, r = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertEqual(public_state(s)['fair']['rules']['bc_open'], 5000)

    def test_a_long_bau_cua_run_keeps_its_rate(self):
        j, f = {}, dict(fh.initial(), date=fh.vn_date(OPEN))
        ps = [fh.luck_p(j, f, 'bc', OPEN + 5 * i) for i in range(40)]
        self.assertEqual(set(ps), {fh.LUCK_BASE})                     # 06/10: no repetition decay
        self.assertGreaterEqual(min(ps), fh.WIN_P_LOW)

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
        self.dice(Dice(faces=['ga', 'bau', 'ca'], draws=[.9]))   # a draw past WIN_P: a round that goes the house's way
        s, r = self.act(s, 'fair_bc', bets={'tom': 4})
        self.assertEqual(r['fair']['net'], -4)
        validate_state(s)

    def test_fair_dice_alone_would_favour_the_house(self):
        """Exact return of one xu on a face over the 216 outcomes: why the rounds are drawn the player's way."""
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
        for bets in ({}, {'cop': 1}, {'cua': 0}, {'cua': 1001}, {'cua': 500, 'tom': 501}, {'cua': 1.5}, {'cua': True}):
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

    def test_no_daily_loss_cap_only_the_wallet(self):
        s = story(1000)
        self.dice(Dice(faces=['ga'] * 300, draws=[.99] * 300))
        for _ in range(20):                                               # 400 xu lost: way past the old 150 a day
            s, r = self.act(s, 'fair_bc', bets={'cua': 20})
        self.assertLess(s['journey']['fair']['net'], -150)
        self.assertEqual(s['journey']['wallet'], 1000+s['journey']['fair']['net'])
        self.assertFalse(public_state(s)['fair']['today']['done'])
        validate_state(s)
        s['journey']['wallet'] = 5
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_bc', bets={'cua': 6})
        self.assertEqual(e.exception.code, 'fair_wallet')

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
        self.dice(Dice(faces=['cua'] * 3 + ['ga'] * 3 + ['cua', 'tom', 'ga'], draws=[.1, .9, .9, .1]))
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
        self.dice(Dice(coins=[1, 1, 0, 0], draws=[.9, .1]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=30)
        self.assertEqual((r['fair']['raid'], r['fair']['even'], r['fair']['net']), (False, True, 30))
        self.dice(Dice(coins=[1, 0, 0, 0], draws=[.9, .9]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)
        self.assertEqual(r['fair']['net'], -10)
        self.assertEqual(s['journey']['wallet'], 220)

    def test_stakes(self):
        s = story(200)
        for p in (dict(side='chan', stake=9), dict(side='chan', stake=1001), dict(side='x', stake=10), dict(stake=10)):
            with self.assertRaises(GameError, msg=p):
                apply_action(s, None, 'fair_xd', p)

    def test_raid_confiscates_fines_and_closes_the_corner(self):
        s = story(200)
        self.dice(Dice(draws=[0.0]))
        s, r = self.act(s, 'fair_xd', side='le', stake=40)
        f = r['fair']
        self.assertTrue(f['raid'])
        self.assertEqual((f['stake'], f['fine'], f['net']), (40, 40 // fh.FINE_DIV, -40 - 40 // fh.FINE_DIV))
        self.assertEqual(s['journey']['wallet'], 200 - 40 - 40 // fh.FINE_DIV)
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

    def test_the_fine_is_a_quarter_of_the_stake(self):
        s = story(1000)
        self.dice(Dice(draws=[0.0]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=50)
        self.assertEqual((r['fair']['fine'], r['fair']['net']), (12, -62))
        self.assertEqual(fh.xd_fine(10), fh.FINE_MIN)

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
        self.assertEqual((a, b), (int(at(2026, 10, 9, 0)), int(at(2026, 10, 14, 0))))
        self.assertTrue(fh.is_open(at(2026, 10, 9, 0)) and fh.is_open(at(2026, 10, 13, 23, 59)) and not fh.is_open(AFTER))
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': '2026-11-20', 'MNL_FAIR_DAYS': '3'}):
            self.assertEqual(fh.window(), (int(at(2026, 11, 20, 0)), int(at(2026, 11, 23, 0))))
            self.assertEqual(fh.edition(), 'fair20261120')
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': 'not a date'}):
            self.assertEqual(fh.edition(), 'fair20261009')

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
        self.assertEqual(v['money'], dict(total=0, days=0))
        self.assertNotIn('points', v)
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


def fits(rv: dict, want_win: bool) -> bool:
    """The rounds fair.loto_rs draws: won with a call to spare, or a neighbour first."""
    return rv['mine'] < rv['npc_done'] if want_win else rv['npc_done'] < rv['mine']


def loto_dice(rs: int, want_win: bool) -> Dice:
    """fair._rng for a purchase: the draw that decides the round, then the round id."""
    return Dice(bits=rs, draws=[0 if want_win else .99])


def winning_rs(want_win: bool, slot: int) -> int:
    for rs in range(5000):
        if fits(fh.round_view(dict(slot=slot, rs=rs, at=0, stage='play')), want_win):
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
        self.dice(loto_dice(winning_rs(win, slot), win))
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
        self.assertNotIn('points', r['fair'])                            # no fair points any more (owner 03/10: xu won)
        self.assertEqual(public_state(s)['fair']['today_xu']['lt'], fh.LOTO_PRIZE - fh.LOTO_PRICE)   # 💰 xu kiếm hôm nay
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

    def test_the_round_is_decided_first(self):
        """Owner 03/10: "tỷ lệ thắng 53%": the draw (fair._rng) decides, the round id fits it; a won round leaves the
        player at least one call to hô before the first neighbour."""
        self.dice(random.Random(7))
        for want in (True, False) * 20:
            lt = dict(slot=29_000_000 + fh._rng.randrange(10**4), rs=0, at=0, stage='play')
            lt['rs'] = fh.loto_rs(lt, want)
            self.assertTrue(0 <= lt['rs'] < 2**31)
            rv = fh.round_view(lt)
            self.assertTrue(fits(rv, want), want)
            self.assertEqual(rv, fh.round_view(dict(lt)))   # replays the same from {slot, rs}
            self.assertEqual(sorted(rv['seq']), list(range(1, 91)))

    def test_a_round_bought_before_the_change_still_plays(self):
        """A round in a save from 1.4.15 (any rs, the plain card or the gánh) is replayed and paid the same way."""
        s = story(100)
        slot = int(self.clock.t // 60) + 1
        rs = winning_rs(True, slot)
        s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(self.clock.t), ed=fh.edition(),
                                    loto=dict(slot=slot, rs=rs, at=int(self.clock.t), stage='play'))
        validate_state(s)
        rv = fh.round_view(s['journey']['fair']['loto'])
        pos = {n: i for i, n in enumerate(rv['seq'])}
        row = min(range(3), key=lambda i: max(pos[n] for n in rv['card'][i]))
        s, r = self.act(s, 'fair_loto_kinh', row=row, at=max(pos[n] for n in rv['card'][row]) + 1)
        self.assertEqual((r['fair']['won'], r['fair']['prize']), (True, fh.LOTO_PRIZE))


def slot_with(mode: str, start: float) -> int:
    """The first minute from `start` whose vòng is `mode` (fh.mode_of)."""
    slot = int(start // 60) + 1
    while fh.mode_of(slot) != mode:
        slot += 1
    return slot


def show_rs(lt: dict, want_win: bool) -> int:
    """A round id (rs) where the player's best card does (not) fill the vòng's pattern first."""
    for rs in range(5000):
        if fits(fh.round_view(dict(lt, rs=rs)), want_win):
            return rs
    raise AssertionError('no such round')


def marks_for(rv: dict, ci: int, k: int) -> list:
    """Every number of card ci called in the first k calls: what a player who marked by hand would hold."""
    called = set(rv['seq'][:k])
    return [n for r in rv['cards'][ci] for n in r if n in called]


class LotoShow(FairBase):
    """🎱 Gánh lô tô: tiers, several tờ, the vòng of the minute, side bets, Kinh by the player's own marks (no
    auto-mark), Kinh hụt, the day's tally, the caps, old saves and the older client."""

    def buy(self, s, mode='thuong', win=True, **p):
        slot = slot_with(mode, self.clock.t)
        p.setdefault('tier', 'vua')
        p.setdefault('n', 1)
        lt = dict(slot=slot, rs=0, at=0, stage='play', mode=mode, tier=p['tier'], n=p['n'], fk=0)
        if win is not None:
            self.dice(loto_dice(show_rs(lt, win), win))
        self.clock.t = slot * 60 + 1
        s, r = self.act(s, 'fair_loto_buy', mode=mode, **p)
        return s, r, fh.round_view(s['journey']['fair']['loto'])

    def test_the_old_client_buys_the_plain_card(self):
        s = story(100)
        s, r = self.act(s, 'fair_loto_buy')
        lt = s['journey']['fair']['loto']
        self.assertEqual(set(lt), set(fh.LOTO_KEYS))            # nothing new in the save for the older client's card
        self.assertEqual(s['journey']['wallet'], 100 - fh.LOTO_PRICE)
        v = public_state(s)['fair']['loto']
        self.assertEqual((v['mode'], v['cards'], v['prize'], v['need']), ('thuong', [v['card']], fh.LOTO_PRIZE, 1))
        self.assertEqual(fh.prize_of('thuong', fh.LOTO_TIERS['vua'], 1), fh.LOTO_PRIZE)

    def test_tiers_cards_and_what_they_cost(self):
        s = story(200)
        s, r, rv = self.buy(s, tier='lon', n=3)
        self.assertEqual(s['journey']['wallet'], 200 - 30)
        self.assertEqual((len(rv['cards']), rv['price'], r['fair']['cost']), (3, 10, 30))
        self.assertEqual(len({n for c in rv['cards'] for r_ in c for n in r_}) > 15, True)   # three different tờ
        v = public_state(s)['fair']
        self.assertEqual(v['loto']['cards'], rv['cards'])
        g = v['ganh']
        self.assertEqual(len(g['modes']), 10)
        self.assertEqual(g['prizes']['thuong']['lon'][2], rv['prize'])
        validate_state(s)

    def test_bad_purchases_are_refused(self):
        s = story(200)
        slot = slot_with('thuong', self.clock.t)
        self.clock.t = slot * 60 + 1
        for p in (dict(tier='xl', n=1), dict(tier='vua', n=4), dict(tier='vua', n=0), dict(tier='vua', n='1'),
                  dict(tier='vua', n=1, cl=['chan', 3]), dict(tier='vua', n=1, cl=['ba', 2]), dict(tier='vua', n=1, cot=[9, 2]),
                  dict(tier='vua', n=1, cot=['1', 2]), dict(tier='vua', n=1, extra=1), dict(tier=['vua'], n=1),
                  dict(tier='vua', n=1, cl='chan'), dict(tier='vua', n=1, cl=[['chan'], 2])):
            with self.assertRaises(GameError, msg=p):
                self.act(s, 'fair_loto_buy', **p)
            self.clock.t = slot * 60 + 1
        other = next(m for m in fh.LOTO_MODES if m != fh.mode_of(slot))
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_loto_buy', tier='vua', n=1, mode=other)
        self.assertEqual(e.exception.code, 'fair_loto_mode')

    def test_only_the_wallet_limits_a_purchase(self):
        s = story(25)
        with self.assertRaises(GameError) as e:        # 3 × 10 > the wallet: no loans
            self.buy(s, tier='lon', n=3)
        self.assertEqual(e.exception.code, 'fair_wallet')
        s = story(1000)
        s['journey']['fair'] = fh.initial()
        f = s['journey']['fair']
        # owner 03/10: no daily money cap and no round limit for the lô tô; the wallet is the only limit
        f.update(date=fh.vn_date(self.clock.t + 120), net=-(fh.DAY_CAP + 500), rounds=fh.ROUNDS_DAY)
        s, r, rv = self.buy(s, tier='lon', n=1)
        self.assertEqual(s['journey']['fair']['rounds'], fh.ROUNDS_DAY)   # not counted against the other stalls' rounds
        self.assertLess(s['journey']['fair']['net'], -fh.DAY_CAP)
        validate_state(s)

    def test_side_bets_take_no_new_bets(self):
        """08/10 (SIDE_OPEN): the minute's calls are public, a player who saw them could pick the likely chẵn/lẻ or cột
        (scripts/sim_fair_odds.py --side: 107% / 164% back): no new side bet, the tờ alone are still sold."""
        self.assertFalse(fh.SIDE_OPEN)
        s = story(200)
        for p in (dict(cl=['le', 4]), dict(cot=[3, 6]), dict(cl=['chan', 2], cot=[0, 2])):
            with self.assertRaises(GameError, msg=p) as e:
                self.buy(s, tier='nho', n=1, **p)
            self.assertEqual(e.exception.code, 'fair_loto_side')
            self.assertEqual(s['journey']['wallet'], 200)
        g = public_state(s)['fair']['ganh']
        self.assertEqual((g['side'], g['side_stakes']), (False, []))
        s, r, rv = self.buy(s, tier='nho', n=1)
        self.assertEqual(s['journey']['wallet'], 200 - 2)
        self.assertNotIn('sb', s['journey']['fair']['loto'])

    @mock.patch.object(fh, 'SIDE_OPEN', True)
    def test_side_bets_are_settled_at_the_purchase(self):
        """Rounds bought while they were open (before 08/10) settled at the purchase; the save and the view keep them."""
        s = story(200)
        s, r, rv = self.buy(s, tier='nho', n=1, cl=['le', 4], cot=[3, 6])
        back = fh.side_back({'cl': ['le', 4], 'cot': [3, 6]}, rv['chot_n'])
        self.assertEqual(s['journey']['wallet'], 200 - 2 - 4 - 6 + back['cl'] + back['cot'])
        self.assertEqual(rv['chot'], min(rv['mine'], rv['npc_done']))
        self.assertEqual(rv['chot_n'], rv['seq'][rv['chot'] - 1])
        side = public_state(s)['fair']['loto']['side']
        self.assertEqual({k: v['back'] for k, v in side.items()}, back)
        # a later Kinh or fold pays nothing more on the side
        w = s['journey']['wallet']
        s, _ = self.act(s, 'fair_loto_fold')
        self.assertEqual(s['journey']['wallet'], w)

    def test_side_bet_odds(self):
        sb = lambda k, pick, stake=2: fh.side_back({k: [pick, stake]}, x)[k]
        for x in range(1, 91):
            want = 0 if x in fh.BAY_NUMS else 4 if x % 2 == 0 else 0
            self.assertEqual(sb('cl', 'chan', 2), want, x)
            col = 0 if x < 10 else min(8, x // 10)
            self.assertEqual(sb('cot', col, 4), 34, x)       # 4 × 8.5
            self.assertEqual(sb('cot', (col + 1) % 9, 4), 0)
        self.assertEqual(fh.side_back({'cl': ['le', 6]}, 7), {'cl': 0})   # cô Bảy's 7 loses lẻ too
        self.assertEqual(fh.side_back({'cl': ['chan', 6]}, 70), {'cl': 0})

    def test_odds_with_perfect_play(self):
        """Seeded purchases drawn like fair_loto_buy: a perfect player wins about BASES['lt'] of the rounds of every vòng
        and still comes out a little behind (08/10, the house always wins: scripts/sim_fair_odds.py); blind side bets keep a
        small edge."""
        self.dice(random.Random(4242))
        cl = cot = 0
        for mode in fh.LOTO_MODES:
            for n in (1, 3):
                wins = gain = 0
                N = 300
                for i in range(N):
                    lt = dict(slot=29_000_000 + i, rs=0, at=0, stage='play', mode=mode, tier='vua', n=n, fk=0)
                    lt['rs'] = fh.loto_rs(lt, fh._rng.random() < fh.luck_p({}, None, 'lt', OPEN, stake=5 * n))
                    rv = fh.round_view(lt)
                    won = rv['mine'] <= rv['npc_done']
                    wins += won
                    gain += (rv['prize'] if won else 0) - n * rv['price']
                    if mode == 'thuong':
                        cl += fh.side_back({'cl': ['chan', 2]}, rv['chot_n'])['cl'] / 2
                        cot += sum(fh.side_back({'cot': [c, 2]}, rv['chot_n'])['cot'] for c in range(9)) / 2 / 9
                probability = fh.chance_rate('lt', OPEN, 5 * n)
                self.assertAlmostEqual(wins / N, probability, delta=.08, msg=(mode, n))
                ev = gain / (N * n * 5)
                expected = probability * fh.prize_of(mode, 5, n) / (n * 5) - 1
                self.assertAlmostEqual(ev, expected, delta=.20, msg=(mode, n, ev))
        p = fh.chance_rate('lt', OPEN)
        for k in fh.LOTO_MODES:   # 08/10: the house always wins: a perfect player gets 91..96% back (no farming)
            for tier, price in fh.LOTO_TIERS.items():
                for n in range(1, fh.LOTO_CARDS + 1):
                    self.assertTrue(.90 <= p * fh.prize_of(k, price, n) / (n * price) <= .96, (k, tier, n))
        self.assertTrue(.88 < cl / 600 < 1.05, cl / 600)   # blind side bets (closed since 08/10: SIDE_OPEN)
        self.assertTrue(.8 < cot / 600 < 1.05, cot / 600)

    def test_kinh_by_the_players_own_marks(self):
        s = story(200)
        s, _, rv = self.buy(s, n=2)
        k = rv['mine']
        ci = min(range(2), key=lambda i: fh.done_at(rv['cards'][i], {n: j for j, n in enumerate(rv['seq'])}))
        with self.assertRaises(GameError):              # a mark that is not on that tờ: refused outright
            self.act(s, 'fair_loto_kinh', card=ci, at=k, marks=[n for n in range(1, 91) if n not in {x for r in rv['cards'][ci] for x in r}][:1])
        w = s['journey']['wallet']
        s, r = self.act(s, 'fair_loto_kinh', card=ci, at=k, marks=marks_for(rv, ci, k))
        self.assertTrue(r['fair']['won'])
        self.assertEqual(s['journey']['wallet'], w + rv['prize'])
        self.assertEqual(s['journey']['fair']['ltd']['w'], 1)
        validate_state(s)

    def test_no_auto_mark(self):
        """The server never marks for the player: a full row on the tờ is not a Kinh until the player marked it."""
        s = story(200)
        s, _, rv = self.buy(s)
        k = rv['mine']
        for bad in (dict(card=0, at=k, marks=None), dict(card=1, at=k, marks=[]), dict(card=0, at=0, marks=[]),
                    dict(card=0, at=k, marks=['1']), dict(card=0, at=k, marks=[rv['card'][0][0]] * 2)):
            with self.assertRaises(GameError, msg=bad):
                self.act(s, 'fair_loto_kinh', **bad)
        w = s['journey']['wallet']
        partial = marks_for(rv, 0, k)
        full = [row for row in rv['cards'][0] if set(row) <= set(partial)]
        # Every mark was called, only the rows are short: refused with the reason, no fine, no Kinh hụt counted (06/10).
        for marks in ([], [n for n in partial if n not in full[0][:1]]):
            with self.assertRaises(GameError) as ctx:
                self.act(s, 'fair_loto_kinh', card=0, at=k, marks=marks)
            self.assertEqual(ctx.exception.code, 'fair_loto_short')
        self.assertEqual((s['journey']['wallet'], s['journey']['fair']['loto'].get('fk', 0)), (w, 0))

    def test_kinh_hut_a_small_funny_penalty_and_no_limit(self):
        s = story(200)
        s, _, rv = self.buy(s)
        k = rv['mine']
        w = s['journey']['wallet']
        uncalled = next(n for r_ in rv['cards'][0] for n in r_ if n not in rv['seq'][:k])
        s, r = self.act(s, 'fair_loto_kinh', card=0, at=k, marks=marks_for(rv, 0, k) + [uncalled])   # marked a number never called
        self.assertEqual((r['fair']['hut'], r['fair']['fine'], r['fair']['out']), (True, fh.KINH_FINE, False))
        self.assertEqual(s['journey']['wallet'], w - fh.KINH_FINE)
        for i in range(2, 8):                           # owner 03/10: "kinh hụt thoải mái", the cards stay in
            s, r = self.act(s, 'fair_loto_kinh', card=0, at=k, marks=[uncalled])
            self.assertEqual((r['fair']['hut'], r['fair']['out'], r['fair']['fk']), (True, False, min(i, 3)))   # the stored count stays ≤ 3 (older servers' bound)
        self.assertEqual(s['journey']['fair']['loto']['stage'], 'play')
        self.assertEqual(s['journey']['wallet'], w - fh.KINH_FINE * 7)
        self.assertEqual(s['journey']['fair']['ltd']['fk'], 7)
        validate_state(s)
        s, r = self.act(s, 'fair_loto_kinh', card=0, at=k, marks=marks_for(rv, 0, k))   # and can still win the round
        self.assertTrue(r['fair']['won'])
        self.assertNotIn('hut_max', public_state(s)['fair']['loto'])
        validate_state(s)

    def test_the_fine_never_takes_the_wallet_below_zero(self):
        s = story(2)
        s, _, rv = self.buy(s, tier='nho')
        self.assertEqual(s['journey']['wallet'], 0)
        uncalled = next(n for r_ in rv['cards'][0] for n in r_ if n not in rv['seq'][:rv['mine']])
        s, r = self.act(s, 'fair_loto_kinh', card=0, at=rv['mine'], marks=[uncalled])
        self.assertEqual((r['fair']['hut'], r['fair']['fine']), (True, 0))
        self.assertEqual(s['journey']['wallet'], 0)

    def test_kinh_doi_needs_two_rows_and_the_title(self):
        s = story(200)
        s, _, rv = self.buy(s, 'doi')
        self.assertEqual(rv['need'], 2)
        pos = {n: i for i, n in enumerate(rv['seq'])}
        one = fh.done_at(rv['card'], pos, 1)
        if one < rv['mine']:   # one row full, the second not yet: refused with the reason, no fine (06/10)
            w = s['journey']['wallet']
            with self.assertRaises(GameError) as ctx:
                self.act(s, 'fair_loto_kinh', card=0, at=one, marks=marks_for(rv, 0, one))
            self.assertEqual((ctx.exception.code, s['journey']['wallet']), ('fair_loto_short', w))
        s, r = self.act(s, 'fair_loto_kinh', card=0, at=rv['mine'], marks=marks_for(rv, 0, rv['mine']))
        self.assertTrue(r['fair']['won'])
        self.assertIn('f_kinh2', s['journey']['titles'])
        s2, _, _ = self.buy(story(200), 'doi')
        with self.assertRaises(GameError):              # the older client cannot claim a Kinh đôi with one row
            self.act(s2, 'fair_loto_kinh', row=0, at=90)

    def test_hu_dem_hoi_and_lat_nguoc(self):
        t = at(2026, 10, 10, 20, 5)
        self.assertEqual({fh.mode_of(int(t // 60) + i) for i in range(100)}, {'dem'})
        self.assertNotIn('dem', {fh.mode_of(int(at(2026, 10, 10, 12) // 60) + i) for i in range(100)})
        self.clock.t = t
        s = story(200)
        s, _, rv = self.buy(s, 'dem')
        self.assertEqual((rv['need'], len(rv['npcs'])), (3, 6))
        s, r = self.act(s, 'fair_loto_kinh', card=0, at=rv['mine'], marks=marks_for(rv, 0, rv['mine']))
        self.assertTrue(r['fair']['won'])
        self.assertEqual(r['fair']['prize'], fh.prize_of('dem', 5, 1))
        self.assertIn('f_hu', s['journey']['titles'])
        self.clock.t = OPEN
        s, _, rv = self.buy(s, 'nguoc')
        s, r = self.act(s, 'fair_loto_kinh', card=0, at=rv['mine'], marks=marks_for(rv, 0, rv['mine']))
        self.assertIn('f_nguoc', s['journey']['titles'])

    def test_late_and_lost_rounds_tally_the_neighbour(self):
        s = story(200)
        s, _, rv = self.buy(s, win=False)
        s, r = self.act(s, 'fair_loto_kinh', card=0, at=rv['mine'], marks=marks_for(rv, 0, rv['mine']))
        self.assertEqual((r['fair']['won'], r['fair']['by']), (False, rv['npc_name']))
        ltd = s['journey']['fair']['ltd']
        self.assertEqual((ltd['r'], ltd['w'], sum(ltd['npc']), ltd['npc'][rv['npc_k']]), (1, 0, 1, 1))
        s, _, rv = self.buy(s)
        s, _, _ = self.buy(s)                            # a new purchase folds the round being played
        self.assertEqual(sum(s['journey']['fair']['ltd']['npc']), 2)
        self.assertEqual(public_state(s)['fair']['ganh']['today']['r'], 3)
        self.clock.t = at(2026, 10, 11, 9)
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertNotIn('ltd', s['journey']['fair'])   # a new Vietnam day: a new tally
        self.assertEqual(public_state(s)['fair']['ganh']['today']['r'], 0)

    @mock.patch.object(fh, 'SIDE_OPEN', True)   # a round with side bets, bought before 08/10
    def test_saves_old_and_new(self):
        s = story(200)
        s, _, _ = self.buy(s, tier='lon', n=2, cl=['chan', 2], cot=[0, 2])
        validate_state(s)
        ok = json.loads(json.dumps(s))
        ok['journey']['fair']['loto']['fk'] = 9         # any number of Kinh hụt now
        validate_state(ok)
        for patch in (dict(mode='x'), dict(tier='x'), dict(n=4), dict(fk=-1), dict(fk=fh.FK_MAX + 1), dict(sb={'cl': ['chan', 3]}), dict(sb={'x': [1, 2]}),
                      dict(sb={'cot': [9, 2]}), dict(extra=1)):
            bad = json.loads(json.dumps(s))
            bad['journey']['fair']['loto'].update(patch)
            with self.assertRaises(GameError, msg=patch):
                validate_state(bad)
        for ltd in ({'r': 1}, dict(r=1, w=0, fk=0, npc=[0]), dict(r=-1, w=0, fk=0, npc=[0] * 6)):
            bad = json.loads(json.dumps(s))
            bad['journey']['fair']['ltd'] = ltd
            with self.assertRaises(GameError, msg=ltd):
                validate_state(bad)
        old = json.loads(json.dumps(s))                 # a save from before the gánh lô tô
        old['journey']['fair'].pop('ltd')
        old['journey']['fair']['loto'] = dict(slot=1, rs=2, at=3, stage='lost')
        validate_state(old)

    def test_the_older_client_on_a_plain_card(self):
        """A card bought by the older client is claimed the old way and pays LOTO_PRIZE."""
        s = story(100)
        slot = int(self.clock.t // 60) + 1
        self.dice(loto_dice(winning_rs(True, slot), True))
        self.clock.t = slot * 60 + 1
        s, _ = self.act(s, 'fair_loto_buy')
        rv = fh.round_view(s['journey']['fair']['loto'])
        pos = {n: i for i, n in enumerate(rv['seq'])}
        row = min(range(3), key=lambda i: max(pos[n] for n in rv['card'][i]))
        s, r = self.act(s, 'fair_loto_kinh', row=row, at=max(pos[n] for n in rv['card'][row]) + 1)
        self.assertEqual((r['fair']['won'], r['fair']['prize'], r['fair']['row']), (True, fh.LOTO_PRIZE, row))


class Money(FairBase):
    """🏆 Bảng vàng (owner 03/10: "tính tổng tiền mọi người thắng… tiền thắng nhiều xếp top"): the xu won this edition."""
    def test_the_score_is_the_xu_won_at_every_stall(self):
        s = story(1000)
        self.dice(Dice(faces=['cua', 'cua', 'tom']))
        s, r = self.act(s, 'fair_bc', bets={'cua': 5, 'ca': 3})              # +7
        self.assertNotIn('points', r['fair'])
        self.dice(Dice(draws=[0.0]))
        s, r = self.act(s, 'fair_xd', side='chan', stake=10)               # raided: the stake and the fine
        self.assertTrue(r['fair']['raid'])
        lost = -r['fair']['net']
        with mock.patch.object(oaq, 'ai_move', weakest):
            s, _ = self.act(s, 'fair_oaq_start', lv='kho')
            s, r = OAQStall.finish(self, s)
        self.assertEqual(r['fair']['end']['prize'], fh.OAQ_PRIZE['kho'])   # a skill stall's xu count too
        won = 7 - lost + fh.OAQ_PRIZE['kho']
        self.assertEqual(s['journey']['wallet'], 1000 + won)
        self.assertEqual(fh.money_of(s['journey']), (won, 1))
        self.assertEqual(lb.summary(s)[fh.board()], (won, 0, 0, 0, 1, 0, 0, 0))
        self.assertNotIn(fh.edition(), lb.summary(s))                       # the points board is not written any more
        v = public_state(s)['fair']
        self.assertEqual((v['money'], v['board']), (dict(total=won, days=1), fh.board()))
        validate_state(s)

    def test_the_gift_and_a_loan_are_not_winnings(self):
        s = story(0)
        s, _ = self.act(s, 'fair_gift')
        s, _ = self.act(s, 'fair_borrow', amount=100)
        self.assertEqual(fh.money_of(s['journey']), (0, 0))
        self.assertNotIn(fh.board(), lb.summary(s))

    def test_a_loss_is_below_zero_and_off_the_board(self):
        s = story(100)
        self.dice(Dice(faces=['ga', 'bau', 'ca'], draws=[.9]))
        s, r = self.act(s, 'fair_bc', bets={'tom': 4})
        self.assertEqual(r['fair']['net'], -4)
        self.assertEqual(fh.money_of(s['journey'])[0], -4)
        self.assertNotIn(fh.board(), lb.summary(s))
        self.assertEqual(public_state(s)['fair']['money']['total'], -4)     # shown as lỗ
        validate_state(s)

    def test_an_older_save_with_points_keeps_them_untouched(self):
        s = story(100)
        s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition(), pts=40, dpts=fh.POINTS_DAY, pdays=1,
                                    pday=fh.vn_date(OPEN), stats=dict(fh.initial()['stats'], won=30, lost=10, earned=15))
        validate_state(s)
        self.assertEqual(fh.money_of(s['journey']), (35, 1))
        self.dice(Dice(faces=['cua', 'ga', 'ga']))
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})                      # +1
        f = s['journey']['fair']
        self.assertEqual((f['pts'], f['dpts'], fh.money_of(s['journey'])), (40, fh.POINTS_DAY, (36, 1)))

    def test_a_new_edition_starts_from_zero(self):
        s = story(100)
        self.dice(Dice(faces=['cua', 'cua', 'cua']))
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        self.assertGreater(fh.money_of(s['journey'])[0], 0)
        with mock.patch.dict(os.environ, {'MNL_FAIR_START': '2026-12-01'}):
            self.assertEqual(fh.money_of(s['journey']), (0, 0))
            self.assertNotIn(fh.board(), lb.summary(s))
            self.clock.t = at(2026, 12, 2)
            self.dice(Dice(faces=['ga', 'bau', 'ca'], draws=[.9]))
            s, _ = self.act(s, 'fair_bc', bets={'tom': 2})
            self.assertEqual(fh.money_of(s['journey']), (-2, 1))           # this edition's money only
            self.assertEqual(s['journey']['fair']['stats']['bc'], 2)        # the other stats stay lifetime
        validate_state(s)


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
        """Bé Bi stays approachable; Ông Hai now consistently beats shallow look-ahead players."""
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
        self.assertLess(wins(player(2), 'kho'), .15)


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

    def test_a_win_pays_the_level_prize(self):
        for level, prize in (('de', 50), ('kho', 10000)):
            with self.subTest(level=level):
                s = story(0)
                with mock.patch.object(oaq, 'ai_move', weakest):
                    s, r = self.act(s, 'fair_oaq_start', lv=level)
                    self.assertEqual(s['journey']['fair']['pdays'], 1)  # the day played: no chance round needed
                    if level == 'kho':   # 06/10: Ông Hai opens, the board comes back on the player's turn
                        self.assertEqual((r['fair']['view']['ply'], r['fair']['trace'][0][:2]), (1, ['turn', 1]))
                    else:
                        self.assertEqual(r['fair']['view']['b'], oaq.new_game()['b'])
                    advertised = public_state(s)['fair']['rules']['oaq_prize'][level]
                    s, r = self.finish(s)
                end = r['fair']['end']
                self.assertEqual((end['stage'], end['prize']), ('won', prize))
                self.assertEqual(advertised, prize)
                self.assertEqual(r['fair']['view']['prize'], prize)
                j = s['journey']
                self.assertEqual(j['wallet'], prize)
                self.assertEqual(j['history'][-1]['amount'], prize)
                self.assertEqual('f_oaq' in j['titles'], level == 'kho')
                self.assertEqual(j['fair']['net'], 0)  # earning is not betting: the loss cap is untouched
                self.assertEqual(j['history'][-1]['label'], f'{fh.LABELS["oaq"]} · 1 ván thắng')
                validate_state(s)

    def test_no_daily_earning_cap(self):
        s = story(0)                                                   # owner 03/10: kiếm không giới hạn
        with mock.patch.object(oaq, 'ai_move', weakest):
            prizes = []
            for _ in range(4):
                s, _ = self.act(s, 'fair_oaq_start', lv='kho')
                s, r = self.finish(s)
                prizes.append(r['fair']['end']['prize'])
        self.assertEqual(prizes, [10000, 10000, 10000, 10000])
        self.assertEqual(s['journey']['wallet'], 40000)
        self.assertLessEqual(s['journey']['fair']['earn']['oaq'], fh.EARN_DAY['oaq'])   # the counter stays in the older bound
        self.assertTrue(public_state(s)['fair']['earn']['oaq']['nocap'])
        self.clock.t = at(2026, 10, 11, 9)                              # a new day
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

    def test_a_move_for_an_old_board_is_refused(self):
        s = story(0)
        s, r = self.act(s, 'fair_oaq_start', lv='de')
        self.assertEqual(public_state(s)['fair']['rules']['oaq_turn'], 1)
        ply = r['fair']['view']['ply']
        c, d = greedy_move(s['journey']['fair']['oaq']['g'])
        s, r = self.act(s, 'fair_oaq_move', cell=c, dir=d, ply=ply)       # the newer client: the board it played on
        self.assertGreater(r['fair']['view']['ply'], ply)
        if s['journey']['fair']['oaq']['stage'] == 'play':
            c, d = greedy_move(s['journey']['fair']['oaq']['g'])
            with self.assertRaises(GameError) as e:                       # a second tap / another tab: the same ply again
                self.act(s, 'fair_oaq_move', cell=c, dir=d, ply=ply)
            self.assertEqual(e.exception.code, 'fair_oaq_turn')
            with self.assertRaises(GameError):
                self.act(s, 'fair_oaq_move', cell=c, dir=d, ply='1')
            s, _ = self.act(s, 'fair_oaq_move', cell=c, dir=d)               # the older client: no ply, as before

    def test_a_game_begun_while_open_can_be_finished(self):
        s = story(0)
        self.clock.t = AFTER - 60
        with mock.patch.object(oaq, 'ai_move', weakest):
            s, _ = self.act(s, 'fair_oaq_start', lv='de')
            self.clock.t = AFTER + 10
            s, r = self.finish(s)
            self.assertEqual(r['fair']['end']['prize'], fh.OAQ_PRIZE['de'])
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
        self.assertEqual(ring.judge(p, [500, 520, 1500, 100, 1900]), [2, 2, 2, 0, 0])   # one bottle takes several rings

    def test_all_five_pays_the_bonus_and_title(self):
        s = story(0)
        s, rd = self.start(s)
        taps = aim(rd)
        self.assertEqual(len(taps), 5)
        self.clock.t += taps[-1] / 1000
        self.dice(Dice(draws=[.1], coins=[4, 0, 1, 2, 3, 4]))
        s, r = self.act(s, 'fair_ring_throw', id=rd['id'], taps=taps)
        self.assertEqual((r['fair']['n'], r['fair']['prize']), (5, 5 * fh.RING_HIT + fh.RING_ALL))
        self.assertEqual(fh.money_of(s['journey'])[0], 5 * fh.RING_HIT + fh.RING_ALL)
        self.assertIn('f_ring', s['journey']['titles'])
        self.assertIsNone(public_state(s)['fair']['ring'])          # the round is done
        with self.assertRaises(GameError):                          # and paid once
            self.act(s, 'fair_ring_throw', id=rd['id'], taps=taps)
        validate_state(s)

    def test_misses_and_three_hits(self):
        s = story(0)
        s, rd = self.start(s)
        s['journey'].pop('fair_chance')  # a round bought before the change keeps skill rules
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

    def test_no_round_limit_and_no_earning_cap(self):
        s = story(0)
        paid = []
        s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(OPEN), ed=fh.edition(), earn=dict(oaq=0, ring=fh.EARN_DAY['ring'], ring_n=fh.RING_DAY))
        for _ in range(4):
            s, rd = self.start(s)
            self.dice(Dice(draws=[.1], coins=[4, 0, 1, 2, 3, 4]))
            taps = aim(rd)
            self.clock.t += 60
            s, r = self.act(s, 'fair_ring_throw', id=rd['id'], taps=taps)
            paid.append(r['fair']['prize'])
            self.dice(Dice(bits=12345 + len(paid)))
        self.assertEqual(paid, [23, 23, 23, 23])
        self.assertEqual(s['journey']['wallet'], 92)
        self.assertEqual(s['journey']['fair']['net'], 0)
        self.assertEqual(s['journey']['fair']['earn']['ring_n'], fh.RING_DAY)   # counters stop at the older bounds
        validate_state(s)



class Odds(FairBase):
    """The dice and coin stalls lean the player's way (WIN_P of the rounds, tapering from TAPER_FROM to WIN_P_LOW at
    TAPER_TO), simulated with a seeded random.Random standing in for the OS source; what is shown matches the result."""
    N = 20000

    def setUp(self):
        super().setUp()
        self.dice(random.Random(20261003))

    def rounds(self, roll, net=0, n=None):
        """Win rate and return per xu staked over n rounds drawn like fair_bc / fair_xd do at today's luck net."""
        f = dict(fh.initial(), date=fh.vn_date(OPEN), net=net)
        wins = gained = staked = 0
        for _ in range(n or self.N):
            stake, d = roll(fh._rng.random() < fh.win_p(f, OPEN))
            wins += d > 0
            gained += d
            staked += stake
        return wins / (n or self.N), gained / staked

    def bc(self, bets):
        stake = sum(bets.values())

        def roll(want):
            dice = fh.bc_roll(bets, want)
            self.assertEqual(len(dice), 3)
            return stake, fh.bc_back(bets, dice) - stake
        return roll

    def xd(self, side, stake):
        def roll(want):
            if fh._rng.random() * 100 < fh.RAID_PCT:
                return stake, -stake - fh.xd_fine(stake)
            coins = fh.xd_toss(side, want)
            right = (side == 'chan') == (sum(coins) % 2 == 0)
            self.assertEqual(right, want)                                # the coins always match the outcome
            return stake, stake if right else -stake
        return roll

    def test_bau_cua(self):
        for bets in ({'cua': 5}, {'cua': 3, 'tom': 2}, {'ga': 10, 'nai': 10}):
            rate, ev = self.rounds(self.bc(bets))
            self.assertTrue(fh.WIN_P - .02 <= rate <= fh.WIN_P + .02, (bets, rate))
            nets = [fh.bc_back(bets,d)-sum(bets.values()) for d in fh.BC_OUTCOMES]
            positive = [n for n in nets if n>0]; other = [n for n in nets if n<=0]
            expected = (fh.WIN_P*sum(positive)/len(positive)+(1-fh.WIN_P)*sum(other)/len(other))/sum(bets.values())
            self.assertAlmostEqual(ev, expected, delta=.03)

    def test_xoc_dia(self):
        rate, ev = self.rounds(self.xd('le', 20))
        self.assertTrue(fh.WIN_P - .03 <= rate <= fh.WIN_P + .01, rate)   # the 1 % raids lose too
        r = fh.RAID_PCT / 100
        expected = (1 - r) * (2 * fh.WIN_P - 1) - r * (1 + fh.xd_fine(20) / 20)
        self.assertAlmostEqual(ev, expected, delta=.025)

    def test_a_long_run_of_one_stall(self):
        j, f = {}, dict(fh.initial(), date=fh.vn_date(OPEN))
        base = fh.chance_rate('xd', OPEN)
        ps = [fh.luck_p(j, f, 'xd', OPEN + i) for i in range(40)]
        self.assertEqual(ps[:fh.RUN_FREE], [base] * fh.RUN_FREE)
        self.assertAlmostEqual(ps[fh.RUN_FREE], base - fh.RUN_STEP)
        self.assertEqual(ps[-1], fh.XD_FLOOR)                            # 07/10: a long run cools to the floor
        self.assertGreaterEqual(base, fh.P_FLOOR)
        self.assertEqual(fh.luck_p(j, f, 'bc', OPEN + 41), fh.chance_rate('bc', OPEN + 41))
        j[fh.COOL_KEY]['xd'].update(n=30, at=int(OPEN), sw=1)
        self.assertEqual(fh.luck_p(j, f, 'xd', OPEN + fh.RUN_GAP + 5), base)   # a break: a new run
        s = story(100)
        s['journey']['fair_run'] = dict(g='bc', n=3, at=1)
        validate_state(s)
        s['journey']['fair_run'] = dict(g='oaq', n=3, at=1)
        with self.assertRaises(GameError):
            validate_state(s)

    def test_no_money_taper(self):
        self.assertEqual(fh.win_p(None, OPEN), fh.WIN_P)
        rate, _ = self.rounds(self.xd('chan', 10), net=fh.TAPER_FROM - 1)
        self.assertTrue(fh.WIN_P - .03 <= rate <= fh.WIN_P + .01, rate)
        for net in ((fh.TAPER_FROM + fh.TAPER_TO) // 2, fh.TAPER_TO - 1, 10 ** 5):   # 06/10: the same rate at any net
            rate, _ = self.rounds(self.bc({'cua': 5}), net=net, n=6000)
            self.assertTrue(fh.WIN_P - .02 <= rate <= fh.WIN_P + .02, (net, rate))

    def test_the_rounds_played_show_what_they_paid(self):
        s = story(10 ** 5)
        for i in range(150):
            self.clock.t = OPEN + 3 * i
            bets = {'cua': 3, 'ga': 2}
            before = s['journey']['wallet']
            s, r = self.act(s, 'fair_bc', bets=bets)
            self.clock.t += 3
            self.assertEqual(r['fair']['back'], fh.bc_back(bets, r['fair']['dice']))
            self.assertEqual(s['journey']['wallet'] - before, r['fair']['net'])
            s['journey']['fair']['raid_until'] = 0                       # past any raid's cooldown
            s, r = self.act(s, 'fair_xd', side='le', stake=20)
            if not r['fair']['raid']:
                self.assertEqual(r['fair']['even'], sum(r['fair']['coins']) % 2 == 0)
                self.assertEqual(r['fair']['net'] > 0, not r['fair']['even'])
        validate_state(s)

    def test_no_win_stop_no_daily_cap_no_round_limit(self):
        s = story(10 ** 6)
        s['journey']['fair'] = dict(fh.initial(), date=fh.vn_date(OPEN), net=fh.TAPER_TO + 3000, rounds=fh.ROUNDS_DAY,
                                    ed=fh.edition())
        self.assertEqual(fh.win_p(s['journey']['fair'], OPEN), fh.WIN_P)   # far past the old taper: the same rate
        s, _ = self.act(s, 'fair_bc', bets={'cua': 1})
        s['journey']['fair']['net'] = -10 ** 5                             # a big losing day: still playable
        s, _ = self.act(s, 'fair_xd', side='chan', stake=50)
        v = public_state(s)['fair']['today']
        self.assertFalse(v['done'])
        self.assertEqual(v['left'], s['journey']['wallet'])
        self.assertEqual(s['journey']['fair']['rounds'], fh.ROUNDS_DAY)   # a counter only, bounded for older validators
        validate_state(s)


class FairFood(FairBase):
    """🍡 The food carts (game/fair_food.py): a few xu from the wallet, no bụng / tỉnh táo up like the work day's Ăn
    thêm, one Sổ ví row a day, refused when full, short of xu or closed; nothing new in journey['fair']."""

    def fed(self, wallet=50, full=50, wake=50):
        s = story(wallet)
        n = nd.ensure(s)
        n.update(full=full, wake=wake)
        validate_state(s)
        return s

    def test_a_snack_costs_xu_and_fills_the_belly(self):
        s = self.fed()
        s, r = self.act(s, 'fair_snack', item='bap_nuong')
        x = ff.MENU['bap_nuong']
        self.assertEqual(s['journey']['wallet'], 50 - x['price'])
        self.assertEqual(s['journey']['needs']['full'], 50 + x['full'])
        self.assertEqual((r['fair']['game'], r['fair']['say']), ('food', x['say']))
        self.assertNotIn('points', r['fair'])
        s, r = self.act(s, 'fair_snack', item='nuoc_mia')
        y = ff.MENU['nuoc_mia']
        self.assertEqual(s['journey']['needs']['wake'], 50 + y['wake'])
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['label'], row['amount']), ('fair', '🍡 Ăn vặt hội chợ · 2 món', -(x['price'] + y['price'])))
        self.assertNotIn('fair', s['journey'])            # not a game: journey['fair'] is not even created
        self.assertEqual(fh.money_of(s['journey']), (0, 0))   # snacks are not on the Bảng vàng
        self.assertNotIn('lt', public_state(s)['fair']['today_xu'])
        validate_state(s)

    def test_full_still_buys_short_or_closed_refused(self):
        # owner 03/10: "kẹo bông, nước mía… hội chợ không mua được, sửa cho mua nhé" (fresh from breakfast = FULL_CAP)
        s = self.fed(full=100, wake=100)
        s, r = self.act(s, 'fair_snack', item='keo_bong')
        self.assertEqual(s['journey']['wallet'], 50 - ff.MENU['keo_bong']['price'])
        self.assertEqual((s['journey']['needs']['full'], s['journey']['needs']['wake']), (100, 100))
        self.assertIn('ăn cho vui', r['fair']['say'])
        s = self.fed(full=nd.FULL_CAP, wake=nd.WAKE_CAP)
        s, r = self.act(s, 'fair_snack', item='nuoc_mia')
        self.assertEqual(s['journey']['needs']['wake'], min(100, nd.WAKE_CAP + ff.MENU['nuoc_mia']['wake']))
        self.assertNotIn('ăn cho vui', r['fair']['say'])
        s = self.fed(wallet=1)
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_snack', item='banh_trang')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(s['journey']['wallet'], 1)
        for bad in (dict(item='pho'), dict(item=['che']), dict(), dict(item='che', n=2)):
            with self.assertRaises(GameError, msg=bad):
                self.act(s, 'fair_snack', **bad)
        s = self.fed()
        for t in (BEFORE, AFTER):
            self.clock.t = t
            with self.assertRaises(GameError) as e:
                self.act(s, 'fair_snack', item='keo_bong')
            self.assertEqual(e.exception.code, 'fair_closed')

    def test_the_menu_says_why(self):
        s = self.fed(wallet=2, full=100, wake=100)
        food = {x['id']: x for x in public_state(s)['fair']['food']}
        self.assertEqual(set(food), set(ff.MENU))
        self.assertEqual({x['cart'] for x in food.values()}, set(ff.CARTS))
        self.assertEqual((food['keo_bong']['ok'], food['keo_bong']['why']), (True, ''))   # full: still sold
        self.assertEqual((food['nuoc_mia']['ok'], food['nuoc_mia']['why']), (True, ''))
        self.assertEqual((food['che']['ok'], food['che']['why']), (False, 'Chưa đủ xu'))
        s = self.fed(wallet=2)
        food = {x['id']: x for x in public_state(s)['fair']['food']}
        self.assertEqual((food['banh_trang']['ok'], food['banh_trang']['why']), (False, 'Chưa đủ xu'))
        self.assertTrue(food['keo_bong']['ok'])

    def test_a_new_life_day_starts_a_new_row(self):
        s = self.fed()
        s, _ = self.act(s, 'fair_snack', item='tau_hu')
        s['journey']['life_day'] += 1
        s['journey']['needs']['full'] = 40
        s, _ = self.act(s, 'fair_snack', item='tau_hu')
        rows = [r for r in s['journey']['history'] if r['label'].startswith(ff.LABEL)]
        self.assertEqual([r['label'] for r in rows], ['🍡 Ăn vặt hội chợ · 1 món'] * 2)



class FairPhoto(FairBase):
    """📸 The photobooth's ticket (game/fair_photo.py): PRICE xu from the wallet a shoot, one Sổ ví row a life day,
    refused when short (never debt), closed or malformed; nothing new in the save (the validator of the release before
    it, which is this one's, takes the save as it is), not on the Bảng vàng."""

    def test_a_ticket_costs_the_price_one_row_a_day(self):
        s = story(12)
        self.assertEqual(public_state(s)['fair']['photo'], dict(price=fp.PRICE, shots=fp.SHOTS, ok=True, why=''))
        s, r = self.act(s, 'fair_photo')
        self.assertEqual(r['fair'], dict(game='photo', price=fp.PRICE, shots=fp.SHOTS, n=1))
        s, r = self.act(s, 'fair_photo', mode='friends')
        self.assertEqual((s['journey']['wallet'], r['fair']['n']), (12 - 2 * fp.PRICE, 2))
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['label'], row['amount']), ('fair', '📸 Chụp ảnh hội chợ · 2 lượt', -2 * fp.PRICE))
        self.assertEqual([k for k in s['journey'] if k.startswith('fair')], [])   # nothing of the fair in the save
        self.assertEqual(fh.money_of(s['journey']), (0, 0))
        self.assertEqual(public_state(s)['fair']['photo'], dict(price=fp.PRICE, shots=fp.SHOTS, ok=False, why='Chưa đủ xu'))
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_photo', mode='stranger')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual(s['journey']['wallet'], 12 - 2 * fp.PRICE)   # never below what it holds
        s['journey']['life_day'] += 1
        s['journey']['wallet'] = 20
        s, _ = self.act(s, 'fair_photo')
        rows = [r['label'] for r in s['journey']['history'] if r['label'].startswith(fp.LABEL)]
        self.assertEqual(rows, ['📸 Chụp ảnh hội chợ · 2 lượt', '📸 Chụp ảnh hội chợ · 1 lượt'])
        validate_state(s)

    def test_refused_when_closed_or_malformed(self):
        s = story(50)
        for bad in (dict(mode='group'), dict(mode=3), dict(n=4), dict(mode='solo', price=0)):
            with self.assertRaises(GameError, msg=bad):
                self.act(s, 'fair_photo', **bad)
        for t in (BEFORE, AFTER):
            self.clock.t = t
            with self.assertRaises(GameError) as e:
                self.act(s, 'fair_photo')
            self.assertEqual(e.exception.code, 'fair_closed')
        self.assertEqual(s['journey']['wallet'], 50)


class FairPhotoPreviousServer(FairBase):
    """The fair photo history stays compatible with 1.5.1–1.5.4. Use each old
    build's untouched career state: unrelated later menus need newer validators.
    """

    def prev_trees(self):
        root = Path(__file__).resolve().parents[2]
        if os.environ.get('MNL_PREV_TREE'):
            cands = [os.environ['MNL_PREV_TREE']]
        else:
            cands = [str(root / f'_rel{v}' / 'mot-ngay-lam-nghe') for v in ('154', '153', '152', '151')]
        trees = [t for t in cands if (Path(t) / 'game' / 'engine.py').is_file()]
        if not trees:
            self.skipTest('no 1.5.1-1.5.4 tree (MNL_PREV_TREE)')
        return trees

    def test_a_save_with_shoots_crosses_the_previous_builds(self):
        import subprocess
        import sys
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,new_state;s=json.load(sys.stdin);'
                'assert not s["careers"]["cafe_bakery"]["started"] and not s["careers"]["cafe_bakery"]["tasks"];'
                's["careers"]["cafe_bakery"]=new_state()["careers"]["cafe_bakery"];'
                's=migrate_state(s);validate_state(s);print(json.dumps(s))')
        for old in self.prev_trees():
            with self.subTest(tree=old):
                s = story(40)
                for mode in ('solo', 'friends', 'stranger'):
                    s, _ = self.act(s, 'fair_photo', mode=mode)
                validate_state(s)
                env = dict(os.environ, PYTHONPATH=old)
                out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True,
                                     cwd=old, env=env, encoding='utf-8', timeout=300)
                self.assertEqual(out.returncode, 0, out.stderr[-3000:])
                back = json.loads(out.stdout)
                self.assertEqual(back['journey']['history'][-1], s['journey']['history'][-1])
                self.assertEqual(back['journey']['wallet'], 40 - 3 * fp.PRICE)
                back = migrate_state(back)
                validate_state(back)
                back, r = self.act(back, 'fair_photo')
                self.assertEqual(r['fair']['n'], 4)


class FairCash(FairBase):
    """🎁 tiền vốn and 💸 vay nóng (game/fair_cash.py)."""
    def test_the_gift_once_per_edition_and_not_winnings(self):
        s = story(0)
        self.assertTrue(public_state(s)['fair']['cash']['gift_ready'])
        s, r = self.act(s, 'fair_gift')
        self.assertEqual((s['journey']['wallet'], r['fair']['gift']), (fc.GIFT, fc.GIFT))
        self.assertFalse(public_state(s)['fair']['cash']['gift_ready'])
        with self.assertRaises(GameError) as e:
            self.act(s, 'fair_gift')
        self.assertEqual(e.exception.code, 'fair_gift_done')
        self.assertNotIn('fair', s['journey'])                         # not in today's net, not in points
        validate_state(s)
        self.clock.t = AFTER
        self.assertFalse(public_state(dict(s, journey=dict(s['journey'], fair_cash=None)))['fair']['cash']['gift_ready'])

    def test_borrow_and_repay(self):
        s = story(10)
        for bad in (0, 49, 501, 150, '100', True):
            with self.assertRaises(GameError, msg=bad):
                self.act(s, 'fair_borrow', amount=bad)
        s, r = self.act(s, 'fair_borrow', amount=100)
        self.assertEqual((s['journey']['wallet'], r['fair']['due']), (110, 120))
        with self.assertRaises(GameError) as e:                          # one at a time
            self.act(s, 'fair_borrow', amount=50)
        self.assertEqual(e.exception.code, 'fair_loan_open')
        with self.assertRaises(GameError) as e:                          # 110 in the wallet < 120 owed
            self.act(s, 'fair_repay')
        self.assertEqual(e.exception.code, 'fair_wallet')
        self.assertEqual(public_state(s)['fair']['cash']['loan'], dict(p=100, due=120))
        s['journey']['wallet'] = 130
        s, _ = self.act(s, 'fair_repay')
        self.assertEqual((s['journey']['wallet'], s['journey']['fair_cash']['loan']), (10, None))
        self.assertEqual(fc.owed(50), 60)
        self.assertEqual(fc.owed(300), 360)
        rows = [r['label'] for r in s['journey']['history'] if r['kind'] == 'fair']
        self.assertTrue(any('Vay nóng' in x for x in rows) and any('Trả vay' in x for x in rows))
        validate_state(s)

    def test_the_close_collects_wallet_then_bank_then_a_debt(self):
        s = story(0)
        s, _ = self.act(s, 'fair_borrow', amount=500)                   # owes 600
        s['journey']['wallet'] = 100
        from game import bank as bk
        s['journey']['bank'] = bk.initial(s['journey']['seed'], s['journey']['life_day'])
        s['journey']['bank']['balance'] = 200
        self.clock.t = AFTER + 60
        s, _ = apply_action(s, None, 'settings', {'name': 'Lan'})     # any command after the close
        j = s['journey']
        self.assertEqual((j['wallet'], j['bank']['balance'], j['fair_cash']['debt'], j['fair_cash']['loan']), (0, 0, 300, None))
        self.assertFalse(j['in_debt'])                                  # never below zero
        j['wallet'] = 120                                               # later income
        s, _ = apply_action(s, None, 'settings', {'name': 'Lan'})
        self.assertEqual((s['journey']['wallet'], s['journey']['fair_cash']['debt']), (0, 180))
        s['journey']['wallet'] = 500
        s, _ = apply_action(s, None, 'settings', {'name': 'Lan'})     # the rest at the next command
        self.assertEqual((s['journey']['wallet'], s['journey']['fair_cash']['debt']), (320, 0))
        validate_state(s)
        with self.assertRaises(GameError):
            self.act(s, 'fair_borrow', amount=50)                       # the fair is over

    def test_bad_cash_data_is_refused_and_old_saves_load(self):
        s = story()
        validate_state(s)
        s, _ = self.act(s, 'fair_borrow', amount=200)
        for k, v in (('debt', -1), ('loan', dict(ed='x', p=200, due=200)), ('extra', 1), ('gift', 5)):
            bad = json.loads(json.dumps(s))
            bad['journey']['fair_cash'][k] = v
            with self.assertRaises(GameError, msg=k):
                validate_state(bad)


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
        self.dice(Dice(faces=['ga'] * 9, draws=[.99]))
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
        self.score(c, 5)    # as much as b, reached later
        ed = fh.board()
        view = lb.view(self.store, ed, 20, a)
        self.assertEqual([r['name'] for r in view['rows']], ['Anh Ba', 'Chị Tư', 'Cô Năm'])
        self.assertEqual([r['xu'] for r in view['rows']], [90, 50, 50])     # A .25 draw wins even cooled off (06/10: 55% floor); wins pay 10 xu.
        self.assertEqual((view['me']['rank'], view['me']['xu']), (1, 90))
        old = lb.view(self.store, fh.edition(), 20, a)                       # an older client asks by the edition
        self.assertEqual((old['board'], old['rows'], bool(old['fair'])), (fh.edition(), view['rows'], True))
        self.assertFalse(view['fair']['settled'])
        self.assertEqual([t['name'] for t in view['fair']['tiers']], ['Vua trò chơi', 'Cao thủ hội chợ'])
        self.assertEqual(lb.parse_query({'board': ed}), (ed, 50))
        self.assertEqual(lb.parse_query({'board': fh.edition()}), (fh.edition(), 50))
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
        rows = lb.view(self.store, fh.board(), 20, a)
        self.assertEqual([r['name'] for r in rows['rows']], ['Chị Tư'])
        self.assertIsNotNone(rows['me']['rank'])   # still sees their own place
        got = fb.settle(self.store, AFTER + fb.GRACE)
        self.assertEqual([(w['rank'], w['title']) for w in got], [(1, 'f_king')])
        self.assertEqual(got[0]['sid'], self.store.key(b))


    def test_a_loss_leaves_the_board_and_old_point_rows_are_not_read(self):
        a, b = self.player('Anh Ba'), self.player('Chị Tư')
        self.score(a, 2)
        with self.store.connect() as db:   # a row an older server wrote: points on the edition's own board
            db.execute("INSERT INTO leaderboard(sid,board,score,k1,k2,level,days,served,stars,mastered,since,updated) "
                       "VALUES(?,?,500,0,0,0,1,0,0,0,1,1)", (self.store.key(b), fh.edition()))
            db.commit()
        lb.clear_cache()
        self.assertEqual([r['name'] for r in lb.view(self.store, fh.board(), 20, a)['rows']], ['Anh Ba'])
        self.dice(Dice(faces=['ga', 'bau', 'ca'], draws=[.9] * 5))
        for _ in range(3):
            self.cmd(a, 'fair_bc', {'bets': {'tom': 20}})                    # 20 xu − 60 xu: a loss
        lb.clear_cache()
        self.assertEqual(lb.view(self.store, fh.board(), 20, a)['rows'], [])
        self.assertIsNone(lb.view(self.store, fh.board(), 20, a)['me']['rank'])

    def test_a_row_dropped_meanwhile_comes_back_on_the_next_command(self):
        """Rolling release: an older server's write drops the xu row (or the save won before the board counted xu);
        the first command a process sees of that save writes it again, even with no number moving."""
        a = self.player('Anh Ba')
        self.score(a, 2)
        sid = self.store.key(a)
        with self.store.connect() as db:
            db.execute('DELETE FROM leaderboard WHERE sid=?', (sid,))
            db.commit()
        self.cmd(a, 'settings', {'sound': False})                            # remembered: nothing moved, nothing written
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT 1 FROM leaderboard WHERE sid=? AND board=?', (sid, fh.board())).fetchone())
        with lb._recent_lock:
            lb._recent.clear()                                              # another process (or a restart)
        self.cmd(a, 'settings', {'sound': True})
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT score FROM leaderboard WHERE sid=? AND board=?', (sid, fh.board())).fetchone()[0], 20)


if __name__ == '__main__':
    unittest.main()
