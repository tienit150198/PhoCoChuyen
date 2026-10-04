"""🧑‍🍳 Quầy của bạn, tự tay (game/quay_self.py): the board (dishes, prices in their band), the look (tables bought
once), online selling, a day at your own counter with no staff (serve, change, smile, online orders packed and
shipped, the tricky moments), one such day per life day and never twice (closing runs the life day; its end skips
it), a run left open closed at the life day's end, refusals that change nothing, never a debt, the economy (a 1.5.1
counter unchanged, a day at the counter worth one more pair of hands, not a second income), and saves crossing to
the 1.5.2 server and back."""
import copy
import json
import os
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from game import quay as qy
from game import quay_self as qs
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from game.quay_events import BY_ID, EVENTS
from tests.test_quay import ROOT, Q, ST, act, days, opened, refused, simulate

sys.path.insert(0, str(ROOT / 'scripts'))
import sim_quay  # noqa: E402


def stall_id(s):
    return ST(s)['id']


def serve_well(s, smile=True):
    run = ST(s)['run']
    c = qs.customer(s, ST(s), run, run['i'])
    return act(s, 'jr_quay_serve', stall=stall_id(s), items=c['items'], change=c['pay'] - c['total'], smile=smile)


def play(s, rng=None, ship='self'):
    """A careful day at the counter: every moment answered, every customer and order served right."""
    rng = rng or random.Random(1)
    sid = stall_id(s)
    if qs._open_run(ST(s), s['journey']['life_day']) is None:
        s, _ = act(s, 'jr_quay_start', stall=sid)
    for _ in range(40):
        run = ST(s)['run']
        n = qs.pending_event(run)
        if n is not None:
            s, _ = act(s, 'jr_quay_choose', stall=sid, pick=BY_ID[run['ev'][n]]['picks'][0][0])
            continue
        did = False
        for jn, done in enumerate(run['on']):
            o = qs.order(s, ST(s), run, jn)
            if not done and (run['i'] >= o['at'] - 1 or run['i'] >= run['k']) and run['u'] < run['sk']:
                s, _ = act(s, 'jr_quay_ship', stall=sid, order=jn, items=o['items'], seal=True, tool=o['tool'], note=o['sticker'], way=ship,
                           **({'route': o['route']} if ship == 'self' else {}))
                did = True
                break
        if did:
            continue
        if run['i'] >= run['k'] or run['u'] >= run['sk']:
            break
        s, _ = serve_well(s)
    s, r = act(s, 'jr_quay_close', stall=sid)
    return s, r


class Board(unittest.TestCase):
    def test_default_board_is_the_1_5_1_counter(self):
        for t in qy.TRADE_IDS:
            rows = qs.MENUS[t][:3]
            self.assertEqual(sum(r[3] for r in rows), 3 * qy.TRADES[t]['price'], t)   # three dishes average the trade's price
        s = opened('xe', staff=False)
        self.assertEqual(qs.board_pct(ST(s)), 100.0)
        self.assertEqual(qs.goods_pct(ST(s)), 100.0)
        self.assertEqual(qs.demand_pct(ST(s)), 100.0)

    def test_menu_band_count_and_saved_prices(self):
        s = opened('xe', staff=False)
        sid = stall_id(s)
        refused(self, s, 'jr_quay_menu', stall=sid, on=[])
        refused(self, s, 'jr_quay_menu', stall=sid, on=['ts_tran_chau', 'hong_tra', 'tra_dao', 'matcha', 'tra_chanh'])
        refused(self, s, 'jr_quay_menu', stall=sid, on=['banh_mi'])
        refused(self, s, 'jr_quay_menu', 'price_band', stall=sid, on=['matcha'], p={'matcha': 20})
        refused(self, s, 'jr_quay_menu', 'price_band', stall=sid, on=['matcha'], p={'matcha': 8.5})
        lo, hi = qs.band(11)
        s, r = act(s, 'jr_quay_menu', stall=sid, on=['matcha', 'ts_tran_chau'], p={'matcha': hi, 'ts_tran_chau': 9})
        self.assertEqual(ST(s)['menu'], dict(on=['ts_tran_chau', 'matcha'], p={'matcha': hi}))
        self.assertIn('Hơi đắt', r['message'])
        self.assertLess(qs.demand_pct(ST(s)), 90)
        s, r = act(s, 'jr_quay_menu', stall=sid, on=['tra_chanh', 'hong_tra'], p={'tra_chanh': qs.band(6)[0], 'hong_tra': 6})
        self.assertEqual(qs.react(ST(s)), 'cheap')
        self.assertGreater(qs.demand_pct(ST(s)), 100)
        validate_state(s)

    def test_look_tables_cost_once_decor_free(self):
        s = opened('sap', wallet=20000, staff=False)
        sid = stall_id(s)
        w = s['journey']['wallet']
        s, _ = act(s, 'jr_quay_look', stall=sid, c=3, d=['cay', 'meo'], name='Quán Mây')
        self.assertEqual((ST(s)['look'], ST(s)['name'], s['journey']['wallet']), (dict(c=3, d=['cay', 'meo'], t=0), 'Quán Mây', w))
        refused(self, s, 'jr_quay_look', stall=sid, t=2)                                    # tables want a confirm
        refused(self, s, 'jr_quay_look', stall=sid, t=5, confirm=True)                      # a stall takes 4
        refused(self, s, 'jr_quay_look', stall=sid, d=['cay', 'meo', 'hoa', 'radio'])
        refused(self, s, 'jr_quay_look', stall=sid, c=8)
        s, _ = act(s, 'jr_quay_look', stall=sid, t=2, confirm=True)
        self.assertEqual(s['journey']['wallet'], w - 2 * qs.TABLES['sap'][1])
        self.assertEqual(s['journey']['history'][-1]['kind'], 'invest')
        s, _ = act(s, 'jr_quay_look', stall=sid, t=1)                                       # fewer: free, no money back
        s, _ = act(s, 'jr_quay_look', stall=sid, t=2, confirm=True)
        self.assertEqual(s['journey']['wallet'], w - 3 * qs.TABLES['sap'][1])
        self.assertAlmostEqual(qs.demand_pct(ST(s)), 100 * (1 + 2 * qs.TABLE_PCT / 100))

    def test_online_toggle(self):
        s = opened('xe', staff=False)
        s, _ = act(s, 'jr_quay_online', stall=stall_id(s), on=True)
        self.assertIs(ST(s)['online'], True)
        self.assertAlmostEqual(qs.demand_pct(ST(s)), qs.ONLINE_REACH)
        refused(self, s, 'jr_quay_online', stall=stall_id(s), on='yes')


class Day(unittest.TestCase):
    def test_a_cart_with_no_staff_runs_a_day_by_hand(self):
        s = opened('xe', staff=False)
        sid = stall_id(s)
        day = s['journey']['life_day']
        till = ST(s)['till']
        s, _ = act(s, 'jr_quay_start', stall=sid)
        run = ST(s)['run']
        self.assertTrue(qs.WALKINS[0] <= run['k'] <= qs.WALKINS[1])
        self.assertEqual(len(run['ev']), 2)
        refused(self, s, 'jr_quay_start', 'done_today', stall=sid)
        refused(self, s, 'jr_quay_menu', 'busy', stall=sid, on=['matcha'])
        c = qs.customer(s, ST(s), run, 0)
        refused(self, s, 'jr_quay_serve', stall=sid, items=['banh_mi'], change=0)            # not this trade's dish
        s, r = act(s, 'jr_quay_serve', stall=sid, items=c['items'], change=c['pay'] - c['total'], smile=True)
        self.assertEqual(ST(s)['run']['ss'], 5)
        self.assertEqual(ST(s)['till'], till)                                                 # the till moves at closing
        s, r = play(s)
        self.assertIn('Đóng ca', r['message'])
        st = ST(s)
        self.assertTrue(st['run']['x'])
        self.assertEqual(st['day'], day)
        self.assertGreater(st['till'], till)
        self.assertEqual(st['hist'][-1]['d'], day)
        self.assertEqual(st['hist'][-1].get('s'), 1)
        refused(self, s, 'jr_quay_start', 'done_today', stall=sid)                           # once a life day
        n = len(st['hist'])
        days(s, 1)                                                                            # the life day ends: not run twice
        self.assertEqual(len(ST(s)['hist']), n)
        days(s, 1)                                                                            # no staff, nobody there: no sale
        self.assertEqual(len(ST(s)['hist']), n)
        s, _ = act(s, 'jr_quay_start', stall=sid)                                            # a new day: again
        validate_state(s)

    def test_mistakes_cost_a_little_never_a_debt(self):
        s = opened('xe', staff=False)
        sid = stall_id(s)
        s, _ = act(s, 'jr_quay_start', stall=sid)
        run = ST(s)['run']
        c = qs.customer(s, ST(s), run, 0)
        wrong = [d for d in qs.menu(ST(s))['on'] if d not in c['items']][:1]
        s, r = act(s, 'jr_quay_serve', stall=sid, items=wrong, change=c['pay'] - c['total'] + 5, smile=False)
        run = ST(s)['run']
        self.assertEqual(run['ss'], 1)
        self.assertEqual(run['m'], -5)                                                       # the extra change is lost
        self.assertIn('Thối dư 5 xu', r['message'])
        c = qs.customer(s, ST(s), run, 1)
        s, r = act(s, 'jr_quay_serve', stall=sid, items=c['items'], change=10**4, smile=True)
        self.assertGreaterEqual(ST(s)['run']['m'], -5 - c['pay'])                            # never more than they paid
        ST(s)['fund'] = 0
        s, _ = act(s, 'jr_quay_close', stall=sid)
        self.assertGreaterEqual(ST(s)['fund'], 0)
        self.assertGreaterEqual(ST(s)['till'], 0)
        validate_state(s)

    def test_online_orders_packed_and_shipped(self):
        s = opened('xe', staff=False)
        sid = stall_id(s)
        s, _ = act(s, 'jr_quay_online', stall=sid, on=True)
        s, _ = act(s, 'jr_quay_start', stall=sid)
        run = ST(s)['run']
        self.assertEqual(len(run['on']), qs.ONLINE_N)
        o = qs.order(s, ST(s), run, 0)
        refused(self, s, 'jr_quay_ship', stall=sid, order=0, items=o['items'], seal=True, tool=o['tool'], note=o['sticker'], way='self')  # no route
        refused(self, s, 'jr_quay_ship', stall=sid, order=1, items=o['items'], seal=True, way='ship')                                       # not here yet
        s, r = act(s, 'jr_quay_ship', stall=sid, order=0, items=o['items'], seal=True, tool=o['tool'], note=o['sticker'], way='self', route=o['route'])
        self.assertEqual(ST(s)['run']['on'][0], 5)
        self.assertEqual(ST(s)['rate'], [1, 50])
        refused(self, s, 'jr_quay_ship', stall=sid, order=0, items=o['items'], seal=True, way='ship')                                       # shipped already
        app = round(o['total'] * qs.ONLINE_FEE / 100)
        self.assertEqual(ST(s)['run']['rv'], o['total'] - app)
        while ST(s)['run']['i'] < 3:
            if qs.pending_event(ST(s)['run']) is not None:
                ev = BY_ID[ST(s)['run']['ev'][qs.pending_event(ST(s)['run'])]]
                s, _ = act(s, 'jr_quay_choose', stall=sid, pick=ev['picks'][-1][0])
                continue
            s, _ = serve_well(s)
        o1 = qs.order(s, ST(s), ST(s)['run'], 1)
        rv = ST(s)['run']['rv']
        s, r = act(s, 'jr_quay_ship', stall=sid, order=1, items=o1['items'][:1] + o1['items'][:1] + ['tra_chanh'], seal=False, tool=not o1['tool'],
                   note=False, way='ship')
        st1 = ST(s)['run']['on'][1]
        self.assertGreaterEqual(st1, 1)
        self.assertLessEqual(st1, 2)
        fee = max(2, round(o1['total'] * qs.SHIPPER_FEE / 100))
        self.assertEqual(ST(s)['run']['rv'] - rv, o1['total'] - round(o1['total'] * qs.ONLINE_FEE / 100) - fee)
        view = public_state(s)['journey']['quay']['stalls'][0]['run']
        self.assertEqual([o['stars'] for o in view['orders']], [5, st1])
        validate_state(s)

    def test_tricky_moments(self):
        self.assertGreaterEqual(len(EVENTS), 20)
        for e in EVENTS:
            self.assertTrue(2 <= len(e['picks']) <= 3, e['id'])
            self.assertLessEqual(e['when'], {'online', 'rain', 'staff', 'power'}, e['id'])
            for _k, label, outs in e['picks']:
                self.assertLessEqual(len(label), 40)
                for w, o in outs:
                    self.assertTrue(w > 0 and set(o) <= {'m', 'b', 'r', 's', 'k', 't', 'need'} and o['t'], (e['id'], o))
                    self.assertGreaterEqual(o.get('m', 0), -2)
        s = opened('sap', wallet=20000)
        sid = stall_id(s)
        s, _ = act(s, 'jr_quay_start', stall=sid)
        refused(self, s, 'jr_quay_choose', 'no_event', stall=sid, pick='x')
        for _ in range(qs.EVENT_AT[0]):
            s, _ = serve_well(s)
        n = qs.pending_event(ST(s)['run'])
        self.assertEqual(n, 0)
        refused(self, s, 'jr_quay_serve', 'event', stall=sid, items=['hong_tra'], change=0)
        view = public_state(s)['journey']['quay']['stalls'][0]['run']
        self.assertEqual(view['ev']['id'], ST(s)['run']['ev'][0])
        self.assertNotIn('cust', view)
        refused(self, s, 'jr_quay_choose', stall=sid, pick='nope')
        s, r = act(s, 'jr_quay_choose', stall=sid, pick=view['ev']['picks'][0][0])
        self.assertTrue(r['message'])
        self.assertIsNone(qs.pending_event(ST(s)['run']))

    def test_seeded_per_day_and_varied(self):
        seen = set()
        for d in range(20, 60):
            s = opened('sap', wallet=20000)
            s['journey']['life_day'] = d
            ST(s)['day'] = d - 1
            s, _ = act(s, 'jr_quay_start', stall=stall_id(s))
            seen.update(ST(s)['run']['ev'])
            again = qs._pick_events(s, ST(s), d, False)
            self.assertEqual(again, ST(s)['run']['ev'])
        self.assertGreaterEqual(len(seen), 15)

    def test_open_run_closes_when_the_life_day_ends(self):
        s = opened('xe', staff=False)
        sid = stall_id(s)
        day = s['journey']['life_day']
        s, _ = act(s, 'jr_quay_start', stall=sid)
        s, _ = serve_well(s)
        days(s, 1)
        st = ST(s)
        self.assertTrue(st['run']['x'])
        self.assertEqual(st['hist'][-1]['d'], day)
        self.assertEqual(st['day'], day)

    def test_close_before_serving_gives_the_day_back(self):
        s = opened('xe')
        sid = stall_id(s)
        s, _ = act(s, 'jr_quay_start', stall=sid)
        s, r = act(s, 'jr_quay_close', stall=sid)
        self.assertIsNone(ST(s)['run'])
        n = len(ST(s)['hist'])
        days(s, 1)                                                     # the staff sell that day as usual
        self.assertEqual(len(ST(s)['hist']), n + 1)

    def test_rent_still_due_on_a_day_at_the_counter(self):
        s = opened('xe', staff=False)
        sid = stall_id(s)
        st = ST(s)
        target = st['opened'] + qy.MONTH_DAYS - 1           # the counter's 5th day pays rent
        while s['journey']['life_day'] < target:
            days(s, 1)
        s, _ = play(s)
        self.assertEqual(ST(s)['hist'][-1]['costs']['rent'], qy.PLACES['xe']['rent']//qy.MONTH_DAYS)

    def test_refusals_closed_counter_and_no_fund(self):
        s = opened('xe', staff=False)
        sid = stall_id(s)
        refused(self, s, 'jr_quay_serve', 'no_run', stall=sid, items=['hong_tra'], change=0)
        refused(self, s, 'jr_quay_close', 'no_run', stall=sid)
        ST(s)['due'] = 10
        refused(self, s, 'jr_quay_start', 'closed', stall=sid)
        ST(s)['due'] = 0
        ST(s)['fund'] = ST(s)['till'] = 0
        refused(self, s, 'jr_quay_start', 'no_money', stall=sid)

    def test_tampering_rejected(self):
        s = opened('xe', staff=False)
        for bad in (dict(menu=dict(on=['banh_mi'], p={})), dict(menu=dict(on=['matcha'], p={'matcha': 99})), dict(look=dict(c=9, d=[], t=0)),
                    dict(look=dict(c=0, d=['x'], t=0)), dict(look=dict(c=0, d=[], t=3)), dict(online='yes'), dict(rate=[1, 99]),
                    dict(run=dict(d=1))):
            t = copy.deepcopy(s)
            ST(t).update(bad)
            with self.assertRaises(GameError):
                validate_state(t)


class Economy(unittest.TestCase):
    def test_a_staffed_counter_with_the_default_board_is_unchanged(self):
        nets, _, _ = simulate('sap', 'milk_tea', 300)
        with mock.patch.object(qs, 'demand_pct', lambda st: 100.0), mock.patch.object(qs, 'board_pct', lambda st, b=None: 100.0), \
                mock.patch.object(qs, 'goods_pct', lambda st, b=None: 100.0):
            old, _, _ = simulate('sap', 'milk_tea', 300)
        self.assertEqual(nets, old)

    def test_a_day_at_the_counter_is_worth_a_pair_of_hands_not_a_second_income(self):
        for place in qy.PLACE_IDS:
            for trade in ('milk_tea', 'clothing'):
                staffed, _ = sim_quay.simulate(place, trade, 120, 'staffed')
                alone, win = sim_quay.simulate(place, trade, 120, 'self')
                both, _ = sim_quay.simulate(place, trade, 120, 'both')
                online, _ = sim_quay.simulate(place, trade, 120, 'both', online=True)
                sloppy, swin = sim_quay.simulate(place, trade, 120, 'sloppy')
                value = qy.shift_value(place, trade)
                self.assertGreater(win, 0.9, (place, trade))
                self.assertGreater(alone, sloppy, (place, trade))                  # mistakes reduce final profit
                self.assertGreater(both, staffed, (place, trade))
                self.assertLess(both - staffed, 1.0 * value, (place, trade))   # at most one more pair of hands
                self.assertLess(online-both, value*.35, (place, trade))       # online: a little more, never double
                self.assertLess(alone, 120, (place, trade))                    # a milk tea day of the career pays 60-450


class OldServer(unittest.TestCase):
    """Every save this build writes must be accepted by the previous release (1.5.2)."""

    def old_tree(self):
        old = os.environ.get('MNL_OLD_TREE_152') or str(ROOT.parent / '_rel152' / 'mot-ngay-lam-nghe')
        if not (Path(old) / 'game' / 'quay.py').is_file():
            self.skipTest('no 1.5.2 tree (MNL_OLD_TREE_152)')
        return old

    def run_old(self, prog, s):
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=old, PYTHONDONTWRITEBYTECODE='1')
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def test_a_self_run_save_on_the_1_5_2_server_and_back(self):
        s = opened('sap', wallet=20000)
        sid = stall_id(s)
        s, _ = act(s, 'jr_quay_menu', stall=sid, on=['matcha', 'tra_dao', 'hong_tra', 'tra_chanh'], p={'matcha': 12})
        s, _ = act(s, 'jr_quay_look', stall=sid, c=6, d=['meo', 'long_den'], t=2, confirm=True)
        s, _ = act(s, 'jr_quay_online', stall=sid, on=True)
        s, _ = play(s)                                         # a closed day at the counter (the day has run)
        days(s, 1)
        s, _ = act(s, 'jr_quay_start', stall=sid)             # and one left open
        s, _ = serve_well(s)
        validate_state(s)
        day = s['journey']['life_day']
        hist = len(ST(s)['hist'])
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,apply_action,public_state,GameError;'
                'from game.content import CAREERS;from game import quay as qy;s=json.load(sys.stdin);'
                's=migrate_state(s);validate_state(s);public_state(s);'
                's,_=apply_action(s,None,"jr_quay_till",{"stall":"q1"});validate_state(s);'
                'code="";\n'
                'try:\n apply_action(s,None,"jr_quay_serve",{"stall":"q1","items":["matcha"],"change":0})\n'
                'except GameError as e:\n code=e.code\n'
                's["journey"]["life_day"]+=1;qy.on_life_day(s);validate_state(s);'
                'print(json.dumps(dict(s=s,code=code)))')
        got = self.run_old(prog, s)
        self.assertEqual(got['code'], 'unknown_action')                         # a new page on the old server: refused cleanly
        back = got['s']
        st = back['journey']['quay']['stalls'][0]
        for k in ('menu', 'look', 'online', 'rate', 'run'):
            self.assertEqual(st[k], ST(s)[k], k)                               # the old build kept the new keys untouched
        self.assertEqual(len(st['hist']), hist + 1)                            # it ran the open day there (staff on)
        back = migrate_state(back)
        validate_state(back)
        back['journey']['life_day'] += 1
        qy.on_life_day(back)                                                   # here: the stale run is dropped, no double day
        self.assertIsNone(ST(back)['run'])
        self.assertEqual(len(ST(back)['hist']), hist + 2)
        self.assertEqual(ST(back)['hist'][-2]['d'], day)
        validate_state(back)

    def test_a_closed_day_is_not_run_again_by_the_1_5_2_server(self):
        s = opened('sap', wallet=20000)
        s, _ = play(s)
        n = len(ST(s)['hist'])
        prog = ('import json,sys;from game.engine import validate_state,migrate_state;from game import quay as qy;s=json.load(sys.stdin);'
                's=migrate_state(s);validate_state(s);s["journey"]["life_day"]+=1;qy.on_life_day(s);validate_state(s);print(json.dumps(s))')
        back = self.run_old(prog, s)
        self.assertEqual(len(back['journey']['quay']['stalls'][0]['hist']), n)   # the day at the counter was that day


if __name__ == '__main__':
    unittest.main()
