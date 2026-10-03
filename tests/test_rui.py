"""🛡️ Rủi ro & bảo hiểm (game/rui.py) and 💰 Tiệm vàng (game/vang.py): new players left alone, the floor and the caps,
warning → prevention → card, insurance after its waiting days, premiums without debt, the thefts take cash only,
broken vehicles and homes (garage, reno), the month's waived bill, determinism, the views and their size, the save
checks, and saves that cross the 1.4.31 server both ways (MNL_OLD_TREE, else ../_rel1431/mot-ngay-lam-nghe)."""
import copy
import datetime
import json
import os
import random
import subprocess
import sys
import unittest
from pathlib import Path

from game import bank as bk
from game import garage as gr
from game import housing as hs
from game import journey as jr
from game import reno as rn
from game import rui
from game import upkeep as up
from game import vang
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from tests.test_bank import story

ROOT = Path(__file__).resolve().parents[1]
OLD_KINDS = ('living', 'upkeep', 'draw', 'invest', 'salary', 'reopen', 'incident', 'life', 'study', 'backdoor', 'bank', 'home', 'fair')


def act(s, name, **p):
    return apply_action(s, None, name, p)


def R(s):
    return s['journey']['rui']


def grown(wallet=2000, day=20, chapter=3, seed=4242, bank=0):
    """A story save past the new player's grace: life day `day`, chapter `chapter`, `wallet` cash, a bank account."""
    s = story(wallet, seed)
    j = s['journey']
    j['life_day'] = day
    j['chapter'] = chapter
    j['done'] = list(range(1, chapter))
    j['unlocked'] = sorted(set(j['unlocked']) | {c for n in range(1, chapter + 1) for c in jr.CH_UNLOCKS[n] if c in s['careers']})
    if bank is not None:
        j['bank'] = bk.initial(seed, day)
        j['bank']['balance'] = bank
    validate_state(s)
    rui.on_life_day(s)
    R(s)['since'] = R(s)['day'] = day - rui.QUIET   # met long ago: no quiet days left
    R(s)['next_ok'] = 0
    return s


def days(s, n=1):
    """Close `n` life days the way journey.after does: the bank, the homes, reno, the bills, then the risks."""
    notes = []
    for _ in range(n):
        s['journey']['life_day'] += 1
        notes += bk.on_life_day(s) + hs.on_life_day(s) + rn.on_life_day(s) + up.on_life_day(s) + rui.on_life_day(s)
    validate_state(s)
    return notes


def own_car(s, vid, ride=True):
    g = s['journey'].setdefault('garage', gr.initial())
    g['cars'][vid] = dict(c=gr.VEHICLES[vid]['paint'], n='', d=1, p=gr.VEHICLES[vid]['price'])
    if ride:
        g['ride'] = vid


def own_home(s, kind='nha_pho', hid='h1', live=True):
    h = s['journey'].get('home') or hs.initial(1)
    s['journey']['home'] = h
    x = dict(id=hid, kind=kind, price=hs.HOMES[kind]['price'], day=1, down=hs.HOMES[kind]['price'],
             fee=hs.buy_fee(hs.HOMES[kind]['price']), joint=0, loan=None, mv=0, let=None, keep=None)
    if live:
        h['own'] = x
    else:
        h['props'].append(x)
    return x


def reno(s, fix=None):
    """The lived-in home's Sửa nhà block; with `fix`, that part is repaired in Sửa nhà at its quoted price."""
    own = s['journey']['home']['own']
    r = rn._ensure(s, own)
    if fix:
        act_ok(s, 'jr_reno_fix', part=fix, confirm=True, cost=rn.fix_cost(own['kind'], fix, r['parts'][fix]['c']))
    return r


def warn(s, kind, sub='', ref=None, lead=1, cost=None):
    """Put a warning on the save, as _roll would (it happens `lead` life days from now)."""
    r = R(s)
    day = s['journey']['life_day']
    w = dict(kind=kind, sub=sub, ref=ref, day=day + lead, at=day, cost=0)
    r['warn'] = w
    w['cost'] = rui._projected(s, r, kind, sub, ref) if cost is None else cost
    return w


def rows(s, label=None):
    return [x for x in s['journey']['history'] if label is None or label in x['label']]


class Grace(unittest.TestCase):
    def test_new_players_and_the_floor_meet_nothing(self):
        for day, chapter, wallet in ((5, 3, 5000), (20, 2, 5000), (20, 3, 250)):
            s = grown(wallet, day, chapter, bank=None)
            own_car(s, 'o_to_mini')
            for _ in range(40):
                days(s)
                if s['journey']['life_day'] < rui.START_DAY or chapter < rui.START_CHAPTER or wallet < rui.FLOOR:
                    self.assertIsNone(R(s)['warn'])
                    self.assertIsNone(R(s)['card'])
            if wallet < rui.FLOOR:
                self.assertEqual(R(s)['stats'].get('warned', 0), 0)
        self.assertTrue(public_state(grown(800, 10, 2))['rui']['calm'])

    def test_quiet_days_after_this_build_meets_a_save(self):
        s = story(5000)
        j = s['journey']
        j['life_day'], j['chapter'], j['done'] = 30, 3, [1, 2]
        notes = rui.on_life_day(s)
        self.assertTrue(any(n.startswith('🛡️') for n in notes))   # one intro line
        for _ in range(rui.QUIET - 1):
            j['life_day'] += 1
            rui.on_life_day(s)
            self.assertIsNone(R(s)['warn'])

    def test_rolls_come_and_are_deterministic(self):
        def run(seed):
            s = grown(6000, seed=seed)
            own_car(s, 'xe_ga')
            own_home(s)
            out = []
            for _ in range(60):
                days(s)
                r = R(s)
                out.append((r['warn'] or {}).get('kind'))
                if r['card']:
                    act_ok(s, 'jr_rui_choose', id=r['card']['id'], choice=rui.options(s, r)[-1]['id'])
            return out, R(s)['stats']
        a, st = run(11)
        self.assertEqual(run(11)[0], a)
        self.assertGreater(st.get('warned', 0), 2)
        self.assertNotEqual(run(12)[0], a)

    def test_no_life_day_no_roll(self):
        s = grown(6000)
        own_car(s, 'xe_ga')
        for _ in range(30):
            s, _ = act(s, 'jr_rui_pol', id='yte', on=True)
            s, _ = act(s, 'jr_rui_pol', id='yte', on=False)
        self.assertIsNone(R(s)['warn'])
        self.assertEqual(R(s)['stats'].get('warned', 0), 0)

    def test_an_older_build_ran_days_only_the_last_is_looked_at(self):
        s = grown(6000)
        R(s)['pol'] = {'yte': s['journey']['life_day']}
        s['journey']['life_day'] += 12
        rui.on_life_day(s)
        self.assertEqual(R(s)['day'], s['journey']['life_day'])
        self.assertLessEqual(R(s)['acc'], rui.premium_milli(s, 'yte'))   # one day of premium, not twelve
        self.assertLessEqual(R(s)['stats'].get('warned', 0), 1)


def act_ok(s, name, **p):
    """Through the engine, keeping `s` (the engine works on a copy)."""
    t, res = apply_action(s, None, name, p)
    s.clear()
    s.update(t)
    return res


class Flow(unittest.TestCase):
    def test_a_warning_prevented_never_comes(self):
        s = grown(3000, bank=0)
        own_car(s, 'o_to_mini')
        w = warn(s, 'xe', 'car', 'o_to_mini')
        v = public_state(s)['rui']['warn']
        self.assertEqual(v['opts'][0]['id'], 'kiem')
        fee = v['opts'][0]['cost']
        self.assertEqual(fee, -(-w['cost'] * rui.PREVENT_PCT // 100))
        before = s['journey']['wallet']
        act_ok(s, 'jr_rui_prevent', opt='kiem')
        self.assertEqual(before - s['journey']['wallet'], fee)
        self.assertIsNone(R(s)['warn'])
        days(s, 3)
        self.assertIsNone(R(s)['card'])
        self.assertEqual(R(s)['stats']['prevented'], 1)

    def test_a_warning_left_becomes_a_card_with_choices(self):
        s = grown(3000)
        own_car(s, 'o_to_mini')
        warn(s, 'xe', 'car', 'o_to_mini')
        notes = days(s)
        c = R(s)['card']
        self.assertEqual((c['kind'], c['ref'], c['cost']), ('xe', 'o_to_mini', 3000 * rui.XE_PCT // 10000))
        self.assertTrue(any('hỏng' in n for n in notes))
        v = public_state(s)['rui']['card']
        self.assertEqual([o['id'] for o in v['opts']], ['sua', 'de'])   # a car: no do-it-yourself
        w = s['journey']['wallet']
        act_ok(s, 'jr_rui_choose', id=c['id'], choice='sua')
        self.assertEqual(w - s['journey']['wallet'], 120)
        self.assertEqual(rows(s, 'Sửa xe')[-1]['kind'], 'life')
        self.assertIsNone(R(s)['card'])

    def test_insurance_pays_after_its_waiting_days(self):
        s = grown(3000)
        own_car(s, 'o_to_mini')
        act_ok(s, 'jr_rui_pol', id='xe', on=True)
        warn(s, 'xe', 'car', 'o_to_mini')        # warned the day it was bought: not covered
        days(s)
        self.assertEqual(R(s)['card']['cover'], 0)
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='sua')
        days(s, rui.WAIT)
        warn(s, 'xe', 'car', 'o_to_mini')
        days(s)
        self.assertEqual(R(s)['card']['cover'], 80)
        w = s['journey']['wallet']
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='sua')
        self.assertEqual(w - s['journey']['wallet'], 120 - 120 * 80 // 100)
        self.assertEqual(R(s)['stats']['covered'], 96)

    def test_illness_choices_and_the_company_bhyt(self):
        s = grown(3000)
        from game import life
        life.migrate(s)
        warn(s, 'om', 'cam')
        days(s)
        ids = [o['id'] for o in public_state(s)['rui']['card']['opts']]
        self.assertEqual(ids, ['kham', 'thuoc', 'nghi'])
        spirit = s['journey']['life']['spirit']
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='nghi')
        self.assertEqual(s['journey']['life']['spirit'], max(0, spirit + rui.SPIRIT['nghi']))
        self.assertEqual(rui.cover(s, R(s), 'om', 1), 0)
        cid = next(c for c in s['careers'])
        s['careers'][cid]['job'] = dict(s['careers'][cid].get('job') or {}, status='hired', promo={'rank': 1})
        self.assertEqual(rui.cover(s, R(s), 'om', 1), 80)

    def test_caps_event_and_month(self):
        s = grown(1300, bank=0)                  # W − FLOOR = 1 000
        own_car(s, 'mui_tran')                   # a repair would be 480
        warn(s, 'xe', 'car', 'mui_tran')
        days(s)
        self.assertEqual(R(s)['card']['cost'], 1000 * rui.EVENT_PCT // 100)
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='sua')
        m = R(s)['month']
        self.assertLessEqual(m['lost'], m['w'] * rui.MONTH_PCT // 100)
        if m['n'] < rui.MONTH_EVENTS:            # still in the same tháng: one more may come, within what is left
            warn(s, 'xe', 'car', 'mui_tran')
            days(s)
            if R(s)['card'] and R(s)['month']['i'] == m['i']:
                self.assertLessEqual(R(s)['card']['cost'] + m['lost'], m['w'] * rui.MONTH_PCT // 100)

    def test_month_event_count(self):
        s = grown(50000, day=21)                 # day 21: the first morning of a tháng
        own_car(s, 'o_to_mini')
        days(s)
        for _ in range(rui.MONTH_EVENTS + 1):
            R(s)['card'] = None
            warn(s, 'om', 'cam')
            days(s)
        self.assertLessEqual(R(s)['month']['n'], rui.MONTH_EVENTS)
        self.assertGreaterEqual(R(s)['stats'].get('fizzled', 0), 1)

    def test_thefts_take_cash_only_and_banking_prevents(self):
        s = grown(5300, bank=20000)
        warn(s, 'moc', 'vi')
        bal = s['journey']['bank']['balance']
        days(s)
        lost = 5300 - s['journey']['wallet']
        self.assertEqual(lost, min(rui.MOC_MAX, (5300 - rui.FLOOR) * rui.MOC_PCT // 100))   # 600: well under the 8 % cap
        self.assertEqual(s['journey']['bank']['balance'], bal)
        self.assertEqual(rows(s, 'Bị móc túi')[-1]['kind'], 'life')
        self.assertEqual(public_state(s)['rui']['card']['loss'], lost)
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='bao')
        days(s, rui.BACK_DAYS)
        self.assertIsNone(R(s)['back'])
        # banked before it happens: the thief finds nothing
        s = grown(5300, bank=0)
        R(s)['month']['n'] = 0
        warn(s, 'trom', 'nha')
        act_ok(s, 'jr_rui_prevent', opt='gui')
        self.assertEqual(s['journey']['wallet'], 50)
        self.assertEqual(s['journey']['bank']['balance'], 5250)
        days(s, 3)
        self.assertIsNone(R(s)['card'])

    def test_the_safe_and_the_lock(self):
        s = grown(5300)
        own_home(s, 'can_ho_mini')
        act_ok(s, 'jr_rui_gear', id='ket')
        self.assertEqual(s['journey']['wallet'], 4800)
        r = R(s)
        self.assertEqual(rui._theft(s, r, 'trom'), min(rui.TROM_MAX, 4500 * rui.TROM_PCT // 100) // 4)
        p0 = next(p for p, k, *_ in rui.candidates(s, r, 30) if k == 'trom')
        act_ok(s, 'jr_rui_gear', id='khoa')
        p1 = next(p for p, k, *_ in rui.candidates(s, R(s), 30) if k == 'trom')
        self.assertLess(p1, p0)

    def test_first_parking_fine_is_a_reminder(self):
        s = grown(3000)
        own_car(s, 'o_to_suv')
        warn(s, 'phat', 'do', 'o_to_suv')
        w = s['journey']['wallet']
        days(s)
        self.assertEqual(R(s)['card']['sub'], 'nhac')
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='ok')
        self.assertEqual(s['journey']['wallet'], w)
        R(s)['month']['n'] = 0
        warn(s, 'phat', 'do', 'o_to_suv')
        days(s)
        self.assertEqual(R(s)['card']['cost'], rui._phat_cost(6600))

    def test_unanswered_card_takes_the_default(self):
        s = grown(3000)
        own_car(s, 'xe_ga')
        warn(s, 'xe', 'bike', 'xe_ga')
        days(s)
        self.assertEqual([o['id'] for o in rui.options(s, R(s))], ['sua', 'tu', 'de'])
        notes = days(s, rui.CARD_DAYS)
        self.assertTrue(any('tự động' in n for n in notes))
        self.assertIn('xe_ga', R(s)['broken']['xe'])
        # a broken vehicle: no ride out, sells for less, repaired later
        self.assertIn('hỏng', gr.why_not_trip(s, 'xe_ga'))
        car = next(c for c in public_state(s)['journey']['garage']['cars'] if c['id'] == 'xe_ga')
        self.assertEqual(car['broken'], 40)
        self.assertEqual(car['sell'], gr.sell_price(1000) - 40)
        with self.assertRaises(GameError):
            act(s, 'jr_garage_trip', id='xe_ga')
        act_ok(s, 'jr_rui_fix', kind='xe', ref='xe_ga')
        self.assertNotIn('xe_ga', R(s)['broken']['xe'])
        self.assertIsNone(gr.why_not_trip(s, 'xe_ga'))

    def test_a_home_left_broken_loses_its_comfort_until_fixed(self):
        s = grown(9000)
        own_home(s, 'nha_pho')
        reno(s)
        warn(s, 'nha', 'dot', 'h1')
        days(s)
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='de')
        self.assertEqual(rn.get(s)['parts']['roof']['c'], rn.WORN_AT - 15)
        self.assertEqual(rn.perk_off(s), 'cond')
        reno(s, fix='roof')     # fixed in Sửa nhà: the sự cố is over too
        days(s)
        self.assertNotIn('h1', R(s)['broken']['nha'])

    def test_a_home_repaired_comes_back_to_100(self):
        s = grown(9000)
        own_home(s, 'nha_pho')
        reno(s)
        rn.get(s)['parts']['power']['c'] = 70
        warn(s, 'nha', 'ong', 'h1')
        days(s)
        w = s['journey']['wallet']
        act_ok(s, 'jr_rui_choose', id=R(s)['card']['id'], choice='tho')
        self.assertEqual(rn.get(s)['parts']['power']['c'], 100)
        self.assertEqual(w - s['journey']['wallet'], hs.HOMES['nha_pho']['price'] * rui.NHA_SUBS['ong'][2] // 10000)
        self.assertEqual(rows(s, 'Vỡ ống nước')[-1]['kind'], 'home')

    def test_a_waived_bill_doubles_the_odds(self):
        s = grown(0, bank=0)
        own_car(s, 'o_to_mini')
        up.on_life_day(s)
        while s['journey']['life_day'] % up.MONTH_DAYS:
            days(s)
        days(s, up.MONTH_DAYS)                     # nothing to pay with: the bill is waived
        self.assertEqual(R(s)['waived'], s['journey']['life_day'])
        s['journey']['wallet'] = 3000
        r = R(s)
        p = next(p for p, k, *_ in rui.candidates(s, r, s['journey']['life_day']) if k == 'xe')
        self.assertEqual(p, rui.XE_P[0] * 2 // (2 if s['journey']['life_day'] < rui.EASE_DAY else 1))


class Money(unittest.TestCase):
    def test_premiums_billed_and_never_a_debt(self):
        s = grown(400, bank=0)
        own_car(s, 'xe_ga')
        act_ok(s, 'jr_rui_pol', id='yte', on=True)
        act_ok(s, 'jr_rui_pol', id='xe', on=True)
        self.assertEqual(rui.premium_month(s, 'xe'), -(-1000 * 25 // 10000))
        while s['journey']['life_day'] % rui.MONTH_DAYS:
            days(s)
        days(s, rui.MONTH_DAYS)
        self.assertEqual(rows(s, 'Phí bảo hiểm')[-1]['kind'], 'upkeep')
        s['journey']['wallet'] = 0
        R(s)['card'] = R(s)['warn'] = None
        notes = days(s, rui.MONTH_DAYS)
        self.assertEqual(R(s)['pol'], {})
        self.assertTrue(any('tạm ngưng' in n for n in notes))
        self.assertGreaterEqual(s['journey']['wallet'], 0)

    def test_the_wallet_never_goes_below_zero(self):
        rng = random.Random(5)
        for seed in range(8):
            s = grown(rng.randint(300, 4000), seed=seed, bank=rng.randint(0, 3000))
            own_car(s, 'xe_ga')
            own_car(s, 'o_to_mini', ride=bool(seed % 2))
            own_home(s, 'nha_san')
            for pid in ('yte', 'xe', 'nha'):
                if rng.random() < .5:
                    act_ok(s, 'jr_rui_pol', id=pid, on=True)
            for _ in range(80):
                s['journey']['wallet'] = max(0, s['journey']['wallet'] - rng.randint(0, 200))
                days(s)
                r = R(s)
                if r['card'] and rng.random() < .6:
                    opts = [o for o in rui.options(s, r) if o['ok']]
                    act_ok(s, 'jr_rui_choose', id=r['card']['id'], choice=rng.choice(opts)['id'])
                if r['warn'] and rng.random() < .3:
                    opts = [o for o in rui.warn_options(s, r) if o['ok']]
                    if opts:
                        act_ok(s, 'jr_rui_prevent', opt=opts[0]['id'])
                self.assertGreaterEqual(s['journey']['wallet'], 0)
                self.assertGreaterEqual(s['journey']['bank']['balance'], 0)
                self.assertFalse(s['journey']['in_debt'])
            self.assertTrue(all(x['kind'] in OLD_KINDS for x in s['journey']['history']))

    def test_refusals(self):
        s = grown(30)
        with self.assertRaises(GameError):
            act(s, 'jr_rui_gear', id='ket')          # not enough
        with self.assertRaises(GameError):
            act(s, 'jr_rui_pol', id='xe', on=True)    # nothing to insure
        with self.assertRaises(GameError):
            act(s, 'jr_rui_pol', id='nope', on=True)
        _, res = act(s, 'jr_rui_choose', id='r9', choice='sua')
        self.assertTrue(res.get('duplicate'))
        with self.assertRaises(GameError):
            act(s, 'jr_rui_nope')


class Gold(unittest.TestCase):
    def setUp(self):
        self._now = vang.now
        vang.now = lambda: datetime.datetime(2026, 10, 20, 12, tzinfo=vang.VN).timestamp()

    def tearDown(self):
        vang.now = self._now

    def test_one_price_a_day_for_everyone(self):
        d = datetime.date(2026, 10, 20)
        self.assertEqual(vang.price(d), vang.price(d))
        self.assertEqual(vang.price(vang.EPOCH), vang.BASE)
        h = vang.history(d)
        self.assertEqual((len(h), h[-1]), (vang.HIST, vang.price(d)))
        self.assertTrue(all(300 < p < 800 for p in h))
        moves = [abs(b - a) / a for a, b in zip(h, h[1:])]
        self.assertLess(max(moves), .1)
        os.environ['MNL_GOLD_SALT'] = 'another'
        try:
            self.assertNotEqual(vang.history(d), h)
        finally:
            os.environ.pop('MNL_GOLD_SALT')

    def test_buy_and_sell_around_the_price(self):
        s = story(1000)
        p = vang.price()
        s, r = act(s, 'jr_vang_buy', phan=12)
        cost = -(-12 * vang.buy_price(p) // 10)
        self.assertEqual(s['journey']['wallet'], 1000 - cost)
        self.assertEqual(s['journey']['vang']['phan'], 12)
        self.assertEqual(s['journey']['history'][-1]['kind'], 'invest')
        v = public_state(s)['vang']
        self.assertEqual((v['phan'], v['value'], v['p']), (12, 12 * vang.sell_price(p) // 10, p))
        self.assertLess(v['value'], cost)                     # the round trip costs about 5 %
        s, _ = act(s, 'jr_vang_sell', phan=2)
        self.assertEqual(s['journey']['vang']['cost'], cost - cost * 2 // 12)
        s, r = act(s, 'jr_vang_sell', all=True)
        self.assertEqual((s['journey']['vang']['phan'], s['journey']['vang']['cost']), (0, 0))
        self.assertIn('Lỗ', r['message'])
        with self.assertRaises(GameError):
            act(s, 'jr_vang_sell', all=True)
        with self.assertRaises(GameError):
            act(s, 'jr_vang_buy', phan=10**6)
        s['journey']['wallet'] = -5
        s['journey']['in_debt'] = True
        with self.assertRaises(GameError):
            act(s, 'jr_vang_buy', phan=1)

    def test_paid_from_the_bank_when_the_cash_is_short(self):
        s = story(100)
        s, _ = act(s, 'jr_bk_open')
        s['journey']['bank']['balance'] = 5000
        s, _ = act(s, 'jr_vang_buy', phan=50)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 5100 - vang.cost_of(50))
        self.assertGreater(rui.wealth(s), 0)
        self.assertEqual(rui.wealth(s), 5100 - vang.cost_of(50) + vang.worth(50))


class Save(unittest.TestCase):
    def test_bad_blocks_are_refused_and_unknown_fields_kept(self):
        s = grown(3000)
        own_car(s, 'xe_ga')
        warn(s, 'xe', 'bike', 'xe_ga')
        validate_state(s)
        for bad in ([], {'v': 2}, dict(R(s), warn=dict(kind='zz')), dict(R(s), pol={'xx': 3}), dict(R(s), gear=['tui', 'tui']),
                    dict(R(s), acc=-1), dict(R(s), broken={'xe': {'a': {'c': -1, 'd': 1}}, 'nha': {}})):
            x = copy.deepcopy(s)
            x['journey']['rui'] = bad
            with self.assertRaises(GameError, msg=repr(bad)[:80]):
                validate_state(x)
        x = copy.deepcopy(s)
        x['journey']['rui']['later'] = {'a': 1}               # a newer build's field
        validate_state(x)
        for bad in ({'v': 1, 'phan': -1, 'cost': 0, 'stats': {}, 'log': []}, {'v': 1, 'phan': 0, 'cost': 5, 'stats': {}, 'log': []}):
            x = copy.deepcopy(s)
            x['journey']['vang'] = bad
            with self.assertRaises(GameError):
                validate_state(x)

    def test_views_are_small(self):
        s = grown(3000)
        own_car(s, 'xe_ga')
        own_home(s, 'nha_pho')
        warn(s, 'xe', 'bike', 'xe_ga')
        days(s)
        v = public_state(s)
        self.assertIn('card', v['rui'])
        self.assertLess(len(json.dumps(v['rui'], ensure_ascii=False)), 1500)
        self.assertLess(len(json.dumps(v['vang'], ensure_ascii=False)), 400)
        self.assertNotIn('rui', v['journey'])


class OldServer(unittest.TestCase):
    """1.4.31 (the previous server of the rolling release) keeps and accepts every save this build writes."""

    def old_tree(self):
        old = os.environ.get('MNL_OLD_TREE') or str(ROOT.parent / '_rel1431' / 'mot-ngay-lam-nghe')
        if not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no 1.4.31 tree (MNL_OLD_TREE)')
        return old

    def run_old(self, old, prog, s):
        env = dict(os.environ, PYTHONPATH=old + os.pathsep + os.environ.get('PYTHONPATH', ''))
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def busy_save(self):
        """Every kind of money movement and block this build writes."""
        s = grown(9000, bank=4000)
        own_car(s, 'xe_ga')
        own_car(s, 'o_to_suv')
        own_home(s, 'nha_pho')
        reno(s)
        for pid in ('yte', 'xe', 'nha'):
            act_ok(s, 'jr_rui_pol', id=pid, on=True)
        act_ok(s, 'jr_rui_gear', id='tui')
        act_ok(s, 'jr_vang_buy', phan=25)
        act_ok(s, 'jr_vang_sell', phan=5)
        script = [('xe', 'bike', 'xe_ga', 'sua'), ('nha', 'dot', 'h1', 'de'), ('om', 'cam', None, 'kham'), ('moc', 'vi', None, 'bao'),
                  ('moc', 'dt', None, 'mua'), ('trom', 'nha', None, 'thoi'), ('phat', 'do', 'o_to_suv', 'ok'),
                  ('phat', 'do', 'o_to_suv', 'nop'), ('xe', 'car', 'o_to_suv', 'de')]
        for kind, sub, ref, choice in script:
            R(s)['month']['n'] = 0
            R(s)['month']['w'] = 10**6
            warn(s, kind, sub, ref)
            days(s)
            c = R(s)['card']
            self.assertIsNotNone(c, kind)
            act_ok(s, 'jr_rui_choose', id=c['id'], choice=choice)
        warn(s, 'om', 'cam')                                  # an open warning and a card on the save
        act_ok(s, 'jr_rui_prevent', opt='kiem')
        R(s)['month']['n'] = 0
        warn(s, 'xe', 'bike', 'xe_ga')
        days(s, 3)
        days(s, rui.MONTH_DAYS)                               # a premium bill
        validate_state(s)
        kinds = {x['kind'] for x in s['journey']['history']}
        self.assertTrue(kinds <= set(OLD_KINDS), kinds)
        return s

    def test_saves_cross_the_1431_build_both_ways(self):
        old = self.old_tree()
        s = self.busy_save()
        self.assertTrue(R(s)['broken']['xe'] and R(s)['broken']['nha'])
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action,public_state,GameError;'
                'from game.content import CAREERS;s=json.load(sys.stdin);s["careers"]={k:v for k,v in s["careers"].items() if k in CAREERS};'
                's["journey"]["unlocked"]=[c for c in s["journey"]["unlocked"] if c in CAREERS];'   # careers newer than 1.4.31
                's=migrate_state(s);validate_state(s);public_state(s);'
                's,_=apply_action(s,None,"jr_garage_trip",{"id":"o_to_suv"});'   # the old build lets a broken car out: harmless
                'code="";\n'
                'try:\n apply_action(s,None,"jr_rui_pol",{"id":"yte","on":False})\n'
                'except GameError as e:\n code=e.code\n'
                'print(json.dumps(dict(s=s,code=code)))')
        got = self.run_old(old, prog, s)
        self.assertEqual(got['code'], 'unknown_action')
        back = got['s']
        self.assertEqual(back['journey']['rui'], s['journey']['rui'])
        self.assertEqual(back['journey']['vang'], s['journey']['vang'])
        back = migrate_state(back)
        validate_state(back)
        days(back)
        act_ok(back, 'jr_rui_fix', kind='xe', ref='o_to_suv')
        validate_state(back)


if __name__ == '__main__':
    unittest.main()
