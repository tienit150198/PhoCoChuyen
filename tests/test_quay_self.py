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

    def test_menu_all_dishes_and_free_integer_prices(self):
        s = opened('xe', staff=False)
        sid = stall_id(s)
        refused(self, s, 'jr_quay_menu', stall=sid, on=[])
        refused(self, s, 'jr_quay_menu', stall=sid, on=['banh_mi'])
        for bad in (0, -1, 8.5, True, 1000001):
            refused(self, s, 'jr_quay_menu', 'price_band', stall=sid, on=['matcha'], p={'matcha':bad})
        all_dishes = list(qs.DISH['milk_tea'])
        s, _ = act(s, 'jr_quay_menu', stall=sid, on=all_dishes, p={'matcha':1000000})
        self.assertEqual(ST(s)['menu']['on'], all_dishes)
        self.assertEqual(ST(s)['menu']['p']['matcha'], 1000000)
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
    def test_actual_manual_sale_and_restart_same_day(self):
        s = opened(staff=False)
        sid = stall_id(s)
        s, _ = act(s, 'jr_quay_start', stall=sid)
        self.assertTrue(ST(s)['run']['continuous'])
        refused(self,s,'jr_quay_start','busy',stall=sid)
        refused(self,s,'jr_quay_menu','busy',stall=sid,on=['matcha'])
        s, _ = serve_well(s)
        self.assertEqual(ST(s)['business']['sold'],1)
        till = ST(s)['till']
        s, _ = act(s,'jr_quay_close',stall=sid)
        self.assertEqual(ST(s)['till'],till)
        self.assertEqual(ST(s)['run']['sum']['auto'],0)
        s, _ = act(s,'jr_quay_start',stall=sid)
        self.assertFalse(ST(s)['run']['x'])
        validate_state(s)

    def test_mistakes_never_create_debt(self):
        s = opened(staff=False)
        sid = stall_id(s)
        s, _ = act(s,'jr_quay_start',stall=sid)
        c=qs.customer(s,ST(s),ST(s)['run'],0)
        s, _ = act(s,'jr_quay_serve',stall=sid,items=c['items'],change=10000,smile=False)
        self.assertGreaterEqual(ST(s)['fund'],0)
        self.assertGreaterEqual(ST(s)['till'],0)
        self.assertLessEqual(ST(s)['business']['expenses']['loss'],c['pay'])

    def test_online_slots_roll_and_stale_order_rejected(self):
        from game import quay_business as qb
        s=opened(staff=False);sid=stall_id(s)
        s,_=act(s,'jr_quay_online',stall=sid,on=True)
        s,_=act(s,'jr_quay_start',stall=sid)
        o=qs.order(s,ST(s),ST(s)['run'],0)
        args=dict(stall=sid,order=0,order_id=o['id'],items=o['items'],seal=True,tool=o['tool'],note=o['sticker'],way='self',route=o['route'])
        refused(self,s,'jr_quay_ship','waiting',**args)
        with mock.patch.object(qb.time,'time',return_value=o['available_at']/1000):
            s,r=act(s,'jr_quay_ship',**args)
        self.assertEqual(ST(s)['business']['sold'],1)
        self.assertEqual(len(ST(s)['run']['on']),3)
        self.assertNotEqual(qs.order(s,ST(s),ST(s)['run'],0)['id'],o['id'])
        nxt=qs.order(s,ST(s),ST(s)['run'],0)
        with mock.patch.object(qb.time,'time',return_value=nxt['available_at']/1000):
            refused(self,s,'jr_quay_ship','stale_order',**args)
        validate_state(s)

    def test_manual_run_survives_life_day_without_extra_income(self):
        s=opened(staff=False);sid=stall_id(s)
        s,_=act(s,'jr_quay_start',stall=sid)
        s,_=serve_well(s)
        sold=ST(s)['business']['sold'];cash=ST(s)['till']+ST(s)['fund']
        days(s,5)
        self.assertFalse(ST(s)['run']['x'])
        self.assertEqual(ST(s)['business']['sold'],sold)
        self.assertEqual(ST(s)['till']+ST(s)['fund'],cash)

    def test_close_empty_causes_no_gifted_sales(self):
        s=opened(staff=False);sid=stall_id(s)
        s,_=act(s,'jr_quay_start',stall=sid)
        s,_=act(s,'jr_quay_close',stall=sid)
        self.assertIsNone(ST(s)['run'])
        self.assertEqual(ST(s)['business']['sold'],0)

    def test_requires_stock_and_respects_old_debt(self):
        s=opened(staff=False);sid=stall_id(s)
        refused(self,s,'jr_quay_serve','no_run',stall=sid,items=['hong_tra'],change=0)
        ST(s)['due']=10
        refused(self,s,'jr_quay_start','closed',stall=sid)
        ST(s)['due']=0;ST(s)['business']['stock']={}
        refused(self,s,'jr_quay_start','sold_out',stall=sid)

    def test_legacy_event_catalogue_remains_valid(self):
        self.assertGreaterEqual(len(EVENTS),20)
        for event in EVENTS:
            self.assertTrue(2 <= len(event['picks']) <= 3)
            self.assertLessEqual(event['when'],{'online','rain','staff','power'})

    def test_tampering_rejected(self):
        s=opened(staff=False)
        for bad in (dict(menu=dict(on=['banh_mi'],p={})),dict(menu=dict(on=['matcha'],p={'matcha':1000001})),
                    dict(look=dict(c=9,d=[],t=0)),dict(look=dict(c=0,d=['x'],t=0)),dict(online='yes'),dict(rate=[1,99]),dict(run=dict(d=1))):
            t=copy.deepcopy(s);ST(t).update(bad)
            with self.assertRaises(GameError):validate_state(t)


class Economy(unittest.TestCase):
    def test_a_staffed_counter_with_the_default_board_is_unchanged(self):
        nets, _, _ = simulate('sap', 'milk_tea', 300)
        with mock.patch.object(qs, 'demand_pct', lambda st: 100.0), mock.patch.object(qs, 'board_pct', lambda st, b=None: 100.0), \
                mock.patch.object(qs, 'goods_pct', lambda st, b=None: 100.0):
            old, _, _ = simulate('sap', 'milk_tea', 300)
        self.assertEqual(nets, old)

    def test_manual_service_is_limited_to_purchased_inventory(self):
        from game import quay_business as qb
        s=opened(staff=False);sid=stall_id(s)
        stock=sum(ST(s)['business']['stock'].values())
        s,_=act(s,'jr_quay_start',stall=sid)
        for _ in range(stock):
            at=ST(s)['run']['next_at']/1000
            with mock.patch.object(qb.time,'time',return_value=at):s,_=serve_well(s)
        self.assertEqual(ST(s)['business']['sold'],stock)
        self.assertEqual(sum(ST(s)['business']['stock'].values()),0)
        with mock.patch.object(qb.time,'time',return_value=ST(s)['run']['next_at']/1000):
            with self.assertRaises(GameError):serve_well(s)


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

    def test_continuous_runtime_survives_previous_server_read_roundtrip(self):
        self.old_tree()
        s=opened('sap',wallet=20000,staff=False)
        sid=stall_id(s)
        s,_=act(s,'jr_quay_start',stall=sid)
        s,_=serve_well(s)
        s,_=act(s,'jr_quay_close',stall=sid)
        prog=('import json,sys;from game.engine import validate_state,migrate_state,public_state;'
              's=migrate_state(json.load(sys.stdin));validate_state(s);public_state(s);print(json.dumps(s))')
        back=self.run_old(prog,s)
        self.assertEqual(ST(back)['business'],ST(s)['business'])
        back=migrate_state(back);validate_state(back)
        before=ST(back)['till']+ST(back)['fund']
        days(back,1)
        self.assertEqual(ST(back)['till']+ST(back)['fund'],before)

    def test_a_closed_day_is_not_run_again_by_the_1_5_2_server(self):
        self.old_tree()
        s = opened('sap', wallet=20000)
        s, _ = act(s, 'jr_quay_start', stall=stall_id(s))
        s, _ = serve_well(s)
        s, _ = act(s, 'jr_quay_close', stall=stall_id(s))
        n = len(ST(s)['hist'])
        prog = ('import json,sys;from game.engine import validate_state,migrate_state;from game import quay as qy;s=json.load(sys.stdin);'
                's=migrate_state(s);validate_state(s);s["journey"]["life_day"]+=1;qy.on_life_day(s);validate_state(s);print(json.dumps(s))')
        back = self.run_old(prog, s)
        self.assertEqual(len(back['journey']['quay']['stalls'][0]['hist']), n)   # the day at the counter was that day


if __name__ == '__main__':
    unittest.main()
