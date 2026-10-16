"""🏎️ Xe bản giới hạn and 🔨 Biển đẹp (owner 16/10 "gắn biển số vào và tăng % lợi nhuận (3-10% tùy mỗi cái)"):
the auction's limited vehicles land in the garage (never in the shop, never sold back), a won plate / registration /
yacht name is attached to, moved between and taken off the player's own vehicles of the right kind, the percent table
and its caps, the bonus paid once at shift close on the base work income only (never the fair, a transfer or itself),
locked at the shift's start, composed with 🔥 x3, the save checks, an auction lot of a vehicle won end to end on
PostgreSQL, and saves that cross the 2.4.34 build both ways (MNL_OLD_TREE, else ../../_wmain)."""
import copy
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from game import auction as au
from game import auction_content as AC
from game import engine as E
from game import garage as gr
from game import journey as jr
from game.engine import GameError, validate_state
from tests.pg_support import pg_only
from tests.test_bank import act, story

ROOT = Path(__file__).resolve().parents[1]
CID = 'grocery'


def win(s, item, amount=50_000, lot='20261016-1'):
    """What live_effects pays into the save when a lot is won (game/auction.py apply_fx)."""
    it = AC.ITEM[item]
    msg = au.apply_fx(s, dict(data=dict(lot=lot, what='win', item=item, kind=it['kind'], text=it['name'])), amount)
    validate_state(s)
    return msg


def rich(wallet=2_000_000):
    s = story(wallet)
    return s


def buy(s, vid):
    s, _ = act(s, 'jr_garage_buy', id=vid, confirm=True)
    return s


def rows(s, start='Biển đẹp'):
    return [h['amount'] for h in s['journey']['history'] if start in h['label']]


def shift(s, earn=1000, cid=CID, between=None, x3_on=False):
    """One shift of `cid`: open, `earn` xu of sales, `between(s)` mid-shift (a ride switch…), close. The new save, the
    end_day result."""
    if cid not in s['careers'] or not s['careers'][cid].get('started'):
        s, _ = E.apply_action(s, cid, 'select_career', {'confirm': True})
    s, _ = E.apply_action(s, cid, 'start_day')
    E.money(s, s['careers'][cid], earn, 'khách mua')
    if between:
        s = between(s) or s
    with mock.patch.object(jr.x3, 'on', lambda c, t=None: x3_on and c == cid):
        s, r = E.apply_action(s, cid, 'end_day', {'carry_event': True})
    validate_state(s)
    return s, r


class Catalogue(unittest.TestCase):
    def test_limited_editions_join_the_garage_but_not_the_shop(self):
        self.assertEqual({it['kind'] for it in AC.LIMITED}, {'vehicle'})
        groups = set()
        for it in AC.LIMITED:
            V = gr.VEHICLES[it['id']]
            self.assertTrue(gr.ID_RE.fullmatch(it['id']), it['id'])
            self.assertTrue(V['limited'])
            self.assertEqual(V['group'], gr.VEHICLES[it['base']]['group'])
            self.assertIn(V['paint'], gr.PAINT_INDEX)
            self.assertTrue(gr.PAINT_INDEX[V['paint']]['limited'])
            self.assertNotIn(it['id'], gr.SHOP)
            groups.add(V['group'])
        self.assertEqual(groups, {'bike', 'car', 'boat', 'plane'})        # motorbikes, cars, a yacht, a plane
        cat = gr.catalogue()
        self.assertEqual(cat['plate_pct']['cap'], 10)
        self.assertEqual(set(cat['plate_pct']['fit']), {'plate', 'reg', 'hull'})

    def test_new_plate_kinds(self):
        regs = [it for it in AC.ITEMS if it['kind'] == 'reg']
        hulls = [it for it in AC.ITEMS if it['kind'] == 'hull']
        self.assertIn('VN-A888', {it['name'] for it in regs})
        self.assertTrue(regs and hulls)
        self.assertEqual(len({it['id'] for it in AC.ITEMS}), len(AC.ITEMS))
        for it in regs + hulls + list(AC.LIMITED):
            self.assertIn(it['tier'], (1, 2, 3))
            self.assertTrue(it.get('story'))

    def test_percent_table_and_caps(self):
        for group, row in AC.PLATE_PCT.items():
            self.assertEqual(list(row), sorted(row), group)               # a rarer plate never gives less
            for tier in (1, 2, 3):
                base = next(v for v, V in gr.VEHICLES.items() if V['group'] == group and not V.get('limited'))
                self.assertTrue(3 <= gr.pct_of(base, tier) <= 10, (group, tier))
        self.assertEqual(gr.pct_of('xe_so', 1), 3)                        # the floor: a road plate on a motorbike
        self.assertEqual(gr.pct_of('phan_luc', 3), 9)
        self.assertEqual(gr.pct_of('lx_phan_luc_01', 3), 10)               # +1 on a limited edition, capped at 10
        self.assertEqual(gr.pct_of('lx_sieu_xe_01', 3), 8)
        with mock.patch.object(AC, 'LIMITED_PCT', 5):
            self.assertEqual(gr.pct_of('lx_phan_luc_01', 3), 10)           # never above PCT_CAP
        self.assertEqual(AC.PCT_CAP, 10)


class LimitedEditions(unittest.TestCase):
    def test_win_parks_it_in_the_garage(self):
        s = rich()
        msg = win(s, 'lx_sieu_xe_01')
        self.assertIn('nhà xe', msg)
        g = s['journey']['garage']
        self.assertEqual(g['cars']['lx_sieu_xe_01']['c'], 'vang_kim')
        self.assertEqual(g['ride'], 'lx_sieu_xe_01')                       # nothing else to ride: it is "đang đi"
        self.assertIn('lx_sieu_xe_01', s['journey']['uniq_x']['own'])
        self.assertNotIn('lx_sieu_xe_01', s['journey']['uniq']['own'])     # the strict legacy block stays the old kinds
        pub = gr.public(s)
        car = next(c for c in pub['cars'] if c['id'] == 'lx_sieu_xe_01')
        self.assertEqual((car['limited'], car['sell']), (True, 0))
        self.assertNotIn('lx_sieu_xe_01', {m['id'] for m in pub['market']})
        self.assertIn('lx_sieu_xe_01', au.public(s)['own'])
        self.assertEqual(au.collection_score(s)[1:], (1, 1))                # one legendary piece in the collection
        # winning it twice (a replayed row) never duplicates it
        win(s, 'lx_sieu_xe_01', lot='20261016-2')
        self.assertEqual(list(s['journey']['garage']['cars']).count('lx_sieu_xe_01'), 1)

    def test_never_in_the_shop_never_sold_back(self):
        s = rich()
        with self.assertRaises(GameError):
            act(s, 'jr_garage_buy', id='lx_xe_ga_01', confirm=True)
        win(s, 'lx_xe_ga_01')
        before = s['journey']['wallet']
        with self.assertRaises(GameError) as e:
            act(s, 'jr_garage_sell', id='lx_xe_ga_01', confirm=True)
        self.assertEqual(e.exception.code, 'limited')
        self.assertEqual(s['journey']['wallet'], before)
        s, _ = act(s, 'jr_garage_ride', id='lx_xe_ga_01')
        s, _ = act(s, 'jr_garage_trip', id='lx_xe_ga_01')                  # it rides out like its base model

    def test_special_paints_only_on_limited_editions(self):
        s = buy(rich(), 'xe_ga')
        with self.assertRaises(GameError):
            act(s, 'jr_garage_paint', id='xe_ga', color='vang_kim')
        with self.assertRaises(GameError):
            act(s, 'jr_garage_buy', id='o_to_suv', color='bach_kim', confirm=True)
        win(s, 'lx_mui_tran_07')
        s, _ = act(s, 'jr_garage_paint', id='lx_mui_tran_07', color='bach_kim')
        s, _ = act(s, 'jr_garage_paint', id='lx_mui_tran_07', color='do')
        validate_state(s)


class Plates(unittest.TestCase):
    def setUp(self):
        s = buy(buy(buy(rich(), 'o_to_suv'), 'xe_ga'), 'xe_dap')
        s, _ = act(s, 'jr_garage_ride', id='o_to_suv')
        win(s, 'pl_30k66666')                                              # tier 2 road plate
        self.s = s

    def test_legacy_plate_shows_on_the_ride_until_moved(self):
        s = self.s
        self.assertNotIn('uniq_x', s['journey'])                           # a plain plate win keeps the old shape
        b = gr.bonus_now(s)
        self.assertEqual((b['id'], b['item'], b['pct']), ('o_to_suv', 'pl_30k66666', 5))
        s, _ = act(s, 'jr_garage_ride', id='xe_dap')
        self.assertIsNone(gr.bonus_now(s))                                 # a pedal bike carries no plate

    def test_attach_move_detach(self):
        s = self.s
        s, r = act(s, 'jr_garage_plate', item='pl_30k66666', id='xe_ga')
        self.assertIn('30K-666.66', r['message'])
        self.assertEqual(s['journey']['uniq_x']['on'], {'pl_30k66666': 'xe_ga'})
        self.assertIsNone(gr.bonus_now(s))                                 # it is on the scooter, the SUV is ridden
        s, _ = act(s, 'jr_garage_ride', id='xe_ga')
        self.assertEqual(gr.bonus_now(s)['pct'], 4)                        # motorbike, tier 2
        s, r = act(s, 'jr_garage_plate', item='pl_30k66666', id='xe_ga')
        self.assertTrue(r.get('duplicate'))
        s, _ = act(s, 'jr_garage_plate', item='pl_30k66666', id='o_to_suv')  # moved
        self.assertEqual(s['journey']['uniq_x']['on'], {'pl_30k66666': 'o_to_suv'})
        pub = gr.public(s)
        self.assertEqual(next(c for c in pub['cars'] if c['id'] == 'o_to_suv')['uq']['t'], '30K-666.66')
        self.assertNotIn('uq', next(c for c in pub['cars'] if c['id'] == 'xe_ga'))
        self.assertEqual(pub['plates'][0]['on'], 'o_to_suv')
        s, r = act(s, 'jr_garage_plate', item='pl_30k66666', id=None)       # taken off
        self.assertEqual(s['journey']['uniq_x']['on'], {})
        self.assertIsNone(gr.bonus_now(s))
        s, r = act(s, 'jr_garage_plate', item='pl_30k66666', id=None)
        self.assertTrue(r.get('duplicate'))
        validate_state(s)

    def test_one_plate_per_vehicle(self):
        s = self.s
        win(s, 'pl_29a88888', lot='20261016-3')                            # tier 3
        s, _ = act(s, 'jr_garage_plate', item='pl_30k66666', id='o_to_suv')
        s, r = act(s, 'jr_garage_plate', item='pl_29a88888', id='o_to_suv')
        self.assertIn('cất lại', r['message'])                            # the first one goes back to its box
        self.assertEqual(s['journey']['uniq_x']['on'], {'pl_29a88888': 'o_to_suv'})
        self.assertEqual(gr.bonus_now(s)['pct'], 7)

    def test_fit_rules(self):
        s = buy(buy(self.s, 'du_thuyen'), 'phan_luc')
        win(s, 'rg_vna888', lot='20261016-4')
        win(s, 'hn_hoang_hon', lot='20261016-5')
        for item, wrong in (('pl_30k66666', 'phan_luc'), ('pl_30k66666', 'xe_dap'), ('rg_vna888', 'o_to_suv'), ('hn_hoang_hon', 'phan_luc')):
            with self.assertRaises(GameError) as e:
                act(s, 'jr_garage_plate', item=item, id=wrong)
            self.assertEqual(e.exception.code, 'wrong_kind', (item, wrong))
        with self.assertRaises(GameError) as e:
            act(s, 'jr_garage_plate', item='pl_29a88888', id='o_to_suv')   # not won
        self.assertEqual(e.exception.code, 'not_owned')
        with self.assertRaises(GameError):
            act(s, 'jr_garage_plate', item='rg_vna888', id='may_bay_nho')  # a plane not owned
        s, _ = act(s, 'jr_garage_plate', item='rg_vna888', id='phan_luc')
        s, _ = act(s, 'jr_garage_plate', item='hn_hoang_hon', id='du_thuyen')
        s, r = act(s, 'jr_garage_ride', id='phan_luc')
        self.assertIn('+9%', r['message'])
        self.assertEqual(gr.bonus_now(s)['pct'], 9)
        s, _ = act(s, 'jr_garage_ride', id='du_thuyen')
        self.assertEqual(gr.bonus_now(s)['pct'], 8)
        validate_state(s)

    def test_selling_a_vehicle_takes_its_plate_off(self):
        s = self.s
        s, _ = act(s, 'jr_garage_plate', item='pl_30k66666', id='xe_ga')
        s, r = act(s, 'jr_garage_sell', id='xe_ga', confirm=True)
        self.assertEqual(s['journey']['uniq_x']['on'], {})
        self.assertIn('30K-666.66', r['message'])
        validate_state(s)


class Bonus(unittest.TestCase):
    def plated(self, vid='o_to_suv', item='pl_30k66666', wallet=2_000_000):
        s = buy(rich(wallet), vid)
        s, _ = act(s, 'jr_garage_ride', id=vid)
        win(s, item)
        return s

    def test_paid_once_on_the_shift_income(self):
        s = self.plated()                                                  # SUV + tier 2 plate: 5 %
        s, r = shift(s, 1000)
        base = r['summary']['net']
        self.assertGreater(base, 0)
        self.assertEqual(rows(s), [base * 5 // 100])
        self.assertEqual((r['summary']['journey']['plate'], r['summary']['journey']['plate_pct']), (base * 5 // 100, 5))
        self.assertTrue(any('Biển đẹp +5%' in e for e in r['effects']))
        self.assertNotIn('plate_lock', s['journey'])                       # the lock is used once

    def test_not_on_other_money(self):
        s = self.plated()

        def fair(st):   # the fair, a gift, a transfer: wallet money that is no shift income
            jr._wallet(st['journey'], 50_000, 'fair', '🎪 Chợ đen')
        s, r = shift(s, 0, between=fair)
        self.assertEqual(rows(s), [])
        self.assertNotIn('plate', r['summary']['journey'])
        n = len(s['journey']['history'])
        from tests.test_bank import days
        days(s, 2, salary=500)                                             # life days without a shift: nothing
        self.assertEqual(rows(s), [])
        self.assertGreater(len(s['journey']['history']), n)

    def test_base_net_leaves_other_multipliers_out(self):
        result = dict(summary=dict(net=1000, ot=dict(total=100), mastery=dict(bonus=50), competition=dict(bonus=20), tile=30))
        self.assertEqual(jr._base_net(result, dict(boost=200)), 600)

    def test_shift_cap(self):
        s = self.plated('phan_luc', 'pl_29a88888')                         # a road plate never fits a plane
        self.assertIsNone(gr.bonus_now(s))
        s = self.plated('sieu_xe', 'pl_29a88888')                          # 7 %
        s, r = shift(s, 100_000)
        self.assertEqual(rows(s), [AC.BONUS_CAP])

    def test_locked_at_the_shift_start(self):
        s = self.plated()
        s = buy(s, 'xe_ga')
        s, _ = act(s, 'jr_garage_plate', item='pl_30k66666', id='o_to_suv')   # (unattached, a plate shows on the ride)
        # switching to the plated vehicle mid-shift pays nothing
        s, _ = act(s, 'jr_garage_ride', id='xe_ga')
        s, r = shift(s, 1000, between=lambda st: act(st, 'jr_garage_ride', id='o_to_suv')[0])
        self.assertEqual(rows(s), [])
        # a better plate moved on mid-shift never raises it
        win(s, 'pl_29a88888', lot='20261016-7')
        s, _ = act(s, 'jr_garage_plate', item='pl_30k66666', id='o_to_suv')
        n = len(rows(s))
        s, r = shift(s, 1000, between=lambda st: act(st, 'jr_garage_plate', item='pl_29a88888', id='o_to_suv')[0])
        self.assertEqual(rows(s)[n:], [r['summary']['net'] * 5 // 100])
        # leaving the plated vehicle mid-shift: nothing
        s, r = shift(s, 1000, between=lambda st: act(st, 'jr_garage_ride', id='xe_ga')[0])
        self.assertEqual(len(rows(s)), n + 1)
        # taking the plate off mid-shift: nothing
        s, _ = act(s, 'jr_garage_ride', id='o_to_suv')
        s, r = shift(s, 1000, between=lambda st: act(st, 'jr_garage_plate', item='pl_29a88888', id=None)[0])
        self.assertEqual(len(rows(s)), n + 1)

    def test_with_x3(self):
        s = self.plated()
        s, r = shift(s, 1000, x3_on=True)
        base = r['summary']['net']
        self.assertEqual([h['amount'] for h in s['journey']['history'] if h['label'].startswith('🔥')], [base * 2])
        self.assertEqual(rows(s), [base * 5 // 100])                      # on the base, never on the x3 bonus
        self.assertEqual(r['summary']['journey']['x3'], base * 2)

    def test_past_the_real_time_allowance(self):
        s = self.plated()
        with mock.patch.object(jr.icl, 'day_paid', lambda st: False):
            s, r = shift(s, 1000)
        self.assertEqual(rows(s), [])


class Save(unittest.TestCase):
    def test_validate_and_upgrade(self):
        s = buy(rich(), 'xe_ga')
        win(s, 'rg_vna168')
        win(s, 'pl_30k66666', lot='20261016-2')
        s, _ = act(s, 'jr_garage_plate', item='pl_30k66666', id='xe_ga')
        for bad in ({'v': 2, 'own': {}, 'on': {}}, {'v': 1, 'own': {}, 'on': {}, 'z': 1}, {'v': 1, 'own': {}, 'on': {'pl_x': 'BAD ID'}},
                    {'v': 1, 'own': {'pl_x': dict(k='plate', t='X', d=1, p=1, lot='20261016-1')}, 'on': {}},   # an old kind
                    {'v': 1, 'own': {}, 'on': {'a_1': 'xe_ga', 'a_2': 'xe_ga'}}):                           # two on one
            t = copy.deepcopy(s)
            t['journey']['uniq_x'] = bad
            with self.assertRaises(GameError):
                validate_state(t)
        for bad in ({'grocery': 11}, {'grocery': 0}, {'BAD': 5}, [1]):
            t = copy.deepcopy(s)
            t['journey']['plate_lock'] = bad
            with self.assertRaises(GameError):
                validate_state(t)
            t = E.migrate_state(t)
            validate_state(t)
            self.assertNotIn('plate_lock', t['journey'])
        t = copy.deepcopy(s)
        del t['journey']['garage']['cars']['xe_ga']                       # sold by an older build
        t['journey']['garage']['ride'] = None
        validate_state(t)                                                  # shape only: the views skip it
        self.assertIsNone(gr.bonus_now(t))
        t = E.migrate_state(t)
        self.assertEqual(t['journey']['uniq_x']['on'], {})

    def test_public_state_is_small(self):
        s = buy(rich(), 'xe_ga')
        win(s, 'pl_30k66666')
        pub = E.public_state(s)
        g = pub['journey']['garage']
        self.assertEqual(g['plates'][0]['t'], '30K-666.66')
        self.assertLess(len(json.dumps(g)), 4000)


@unittest.skipUnless(shutil.which('node'), 'needs node')
class Clients(unittest.TestCase):
    """Both interfaces render it: tests/vehicle-ui.mjs (old: garage, auction, ride.js) from this real save, and
    tests/isometric-vehicles.mjs (new: vehicle-art.js, the town presence, the Phaser scene's budget)."""

    def fixture(self):
        s = buy(buy(buy(buy(rich(), 'o_to_suv'), 'xe_dap'), 'xe_ga'), 'du_thuyen')
        win(s, 'lx_sieu_xe_01')
        win(s, 'pl_29a88888', amount=90_000, lot='20261016-2')
        win(s, 'pl_30k66666', lot='20261016-3')
        win(s, 'pl_may0001', amount=10_000, lot='20261016-4')
        s, _ = act(s, 'jr_garage_plate', item='pl_29a88888', id='lx_sieu_xe_01')
        s, _ = act(s, 'jr_garage_plate', item='pl_30k66666', id='xe_ga')
        s, _ = act(s, 'jr_garage_ride', id='lx_sieu_xe_01')
        return dict(journey=E.public_state(s)['journey'], garage=gr.catalogue(), auction=au.catalogue())

    def node(self, *args):
        out = subprocess.run(['node', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, (out.stdout + out.stderr)[-4000:])

    def test_old_interface(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'fixture.json'
            f.write_text(json.dumps(self.fixture(), ensure_ascii=False), encoding='utf-8')
            self.node('tests/vehicle-ui.mjs', str(f))

    def test_new_interface(self):
        self.node('tests/isometric-vehicles.mjs')

    def test_shift_summary_chip(self):
        src = (ROOT / 'public/js/app.js').read_text(encoding='utf-8')
        self.assertIn('🚗 Biển đẹp +${fmt(jr.plate_pct)}%: +${fmt(jr.plate)} xu', src)
        en = json.loads((ROOT / 'public/i18n/en.json').read_text(encoding='utf-8'))
        for vi in ('🔨 Gắn biển', 'Xe bản giới hạn chỉ có ở Nhà đấu giá.', 'Cub Kỷ Niệm số 81'):
            self.assertIn(vi, en['strings'], vi)


@pg_only
class AuctionLot(unittest.TestCase):
    """A limited vehicle's lot, end to end: bid, settle, live_effects, the garage."""
    from tests.test_auction import Database as _D
    setUp, state, bid, pay, lot, row = _D.setUp, _D.state, _D.bid, _D.pay, _D.lot, _D.row
    del _D

    def player(self, wallet=2_000_000):
        """tests/test_auction.py Database.player, on any Python 3.10+ (datetime.timezone.utc)."""
        import datetime
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)
        sid = self.store.key(token)

        def fn(s):
            s['name'] = 'Lan'
            s['journey']['wallet'] = wallet
        mr._mutate(self.store, {sid: fn})
        created = (datetime.datetime.fromtimestamp(self.t[0], datetime.timezone.utc) - datetime.timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S')
        with self.store.connect() as db:
            db.execute('INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?,?,?,?,?)',
                       (f'u{sid[:10]}', 'Lan', 'x', sid, created))
            db.execute('INSERT INTO logins(token, sid, csrf) VALUES(?,?,?)', (self.store.digest(token), sid, 'c' * 48))
        return token

    def test_vehicle_lot_won_into_the_garage(self):
        a = self.player(wallet=3_000_000)
        lid = self.lot(item='lx_xe_so_81')
        r = self.row(lid)
        self.assertEqual((r['kind'], json.loads(r['data'])['serial']), ('vehicle', '81/81'))
        self.t[0] += 1
        self.bid(a, lid, r['start'])
        self.t[0] = self.row(lid)['ends_at'] + 1
        self.assertEqual(au.settle_one(self.store, lid), 'sold')
        self.pay(a)
        s = self.state(a)
        self.assertIn('lx_xe_so_81', s['journey']['garage']['cars'])
        self.assertIn('lx_xe_so_81', s['journey']['uniq_x']['own'])
        validate_state(s)

    def test_registration_lot_and_its_plate_on_the_live_maps(self):
        import asyncio
        from live import plates
        a = self.player(wallet=3_000_000)
        lid = self.lot(item='rg_vna888')
        self.t[0] += 1
        self.bid(a, lid, self.row(lid)['start'])
        self.t[0] = self.row(lid)['ends_at'] + 1
        self.assertEqual(au.settle_one(self.store, lid), 'sold')
        self.pay(a)
        self.assertIn('rg_vna888', self.state(a)['journey']['uniq_x']['own'])
        sid = self.store.key(a)

        class P:
            ext = {}
        P.sid = sid

        class DB:
            def __init__(self, store):
                self.store = store

            async def fetch(self, q, args):
                with self.store.connect() as db:
                    return [dict(r) for r in db.execute(q, args).fetchall()]
        got = asyncio.run(plates.keep(DB(self.store), P, dict(v='phan_luc', c='', p='VN-A888')))
        self.assertEqual(got, dict(v='phan_luc', c='', p='VN-A888'))
        P.ext = {}
        got = asyncio.run(plates.keep(DB(self.store), P, dict(v='phan_luc', c='', p='VN-A168')))
        self.assertEqual(got, dict(v='phan_luc', c=''))                    # a plate they did not win: dropped


class OldServer(unittest.TestCase):
    """2.4.34 (the rollback target; floor 2.4.27) keeps and accepts every save this build writes, and back."""

    def old_tree(self):
        for old in [os.environ.get('MNL_OLD_TREE'), *(str(p / '_wmain') for p in ROOT.parents)]:
            if old and (Path(old) / 'game' / 'engine.py').is_file() and (Path(old) / 'game' / 'garage.py').is_file():
                return old
        self.skipTest('no 2.4.34 tree (MNL_OLD_TREE)')

    def run_old(self, old, prog, s):
        env = dict(os.environ, PYTHONPATH=old + os.pathsep + os.environ.get('PYTHONPATH', ''), PYTHONUTF8='1')
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def busy_save(self):
        s = buy(buy(buy(rich(), 'o_to_suv'), 'xe_ga'), 'phan_luc')
        win(s, 'lx_sieu_xe_01')
        win(s, 'lx_phan_luc_01', lot='20261016-2')
        win(s, 'pl_29a88888', lot='20261016-3')
        win(s, 'rg_vna888', lot='20261016-4')
        win(s, 'hn_ngoc_may', lot='20261016-5')
        win(s, 'pl_may0001', lot='20261016-6')
        s, _ = act(s, 'jr_garage_plate', item='pl_29a88888', id='lx_sieu_xe_01')
        s, _ = act(s, 'jr_garage_plate', item='pl_may0001', id='xe_ga')
        s, _ = act(s, 'jr_garage_plate', item='rg_vna888', id='lx_phan_luc_01')
        s, _ = act(s, 'jr_garage_ride', id='lx_sieu_xe_01')
        s, _ = act(s, 'jr_garage_paint', id='lx_sieu_xe_01', color='bach_kim')
        s, _ = E.apply_action(s, CID, 'select_career', {'confirm': True})
        s, _ = E.apply_action(s, CID, 'start_day')                       # mid-shift: plate_lock on the save
        self.assertEqual(s['journey']['plate_lock'], {CID: 8})
        validate_state(s)
        return s

    def test_saves_cross_the_old_build_both_ways(self):
        old = self.old_tree()
        s = self.busy_save()
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action,public_state,GameError;'
                'from game import garage as gr, auction as au, auction_content as AC;'
                'from game.content import CAREERS;s=json.load(sys.stdin);'
                's["careers"]={k:v for k,v in s["careers"].items() if k in CAREERS};'
                's["journey"]["unlocked"]=[c for c in s["journey"]["unlocked"] if c in CAREERS];'
                's=migrate_state(s);validate_state(s);public_state(s);'
                's,_=apply_action(s,None,"jr_garage_sell",{"id":"xe_ga","confirm":True});'   # the old build sells a plated car
                's,_=apply_action(s,"grocery","end_day",{"carry_event":True});validate_state(s);'
                'code="";\n'
                'try:\n au.apply_fx(s,dict(data=dict(lot="20261016-9",what="win",item="lx_xe_ga_01",kind="vehicle",text="X")),1)\n'
                'except GameError as e:\n code=e.code or "refused"\n'
                'validate_state(s)\n'
                'print(json.dumps(dict(s=s,code=code,items=[it["id"] for it in AC.ITEMS],vehicles=list(gr.VEHICLES))))')
        got = self.run_old(old, prog, s)
        self.assertTrue(got['code'])                                       # an old build leaves the new kinds pending
        self.assertTrue(set(got['items']) <= set(AC.ITEM))                 # no auction item renamed or removed
        self.assertTrue(set(got['vehicles']) <= set(gr.VEHICLES))          # no vehicle id renamed or removed
        back = got['s']
        self.assertEqual(back['journey']['uniq_x']['own'], s['journey']['uniq_x']['own'])
        self.assertIn('lx_sieu_xe_01', back['journey']['garage']['cars'])  # kept by shape
        self.assertNotIn('xe_ga', back['journey']['garage']['cars'])
        back = E.migrate_state(back)
        validate_state(back)
        self.assertNotIn('pl_may0001', back['journey']['uniq_x']['on'])   # its car was sold: back in its box
        self.assertEqual(back['journey']['uniq_x']['on'], {'pl_29a88888': 'lx_sieu_xe_01', 'rg_vna888': 'lx_phan_luc_01'})
        back, _ = act(back, 'jr_garage_ride', id='lx_sieu_xe_01')
        self.assertEqual(gr.bonus_now(back)['pct'], 8)
        E.public_state(back)


if __name__ == '__main__':
    unittest.main()
