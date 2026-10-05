"""🏪 Quầy của bạn (game/quay.py): unlock, opening, NPC staff and wages, the daily run (mostly profitable, every trade
alike), Thu két, the idle stop, rent and its pause, thieves (rare, capped, the till only), the police, selling, the
views, validation, and saves crossing to the previous server (1.4.31) and back."""
import copy
import json
import os
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from game import journey as jr
from game import quay as qy
from game.engine import GameError, apply_action, migrate_state, new_state, public_state, validate_state

ROOT = Path(__file__).resolve().parents[1]


def story(wallet=5000, seed=4242):
    s = new_state()
    jr.enable_story(s, seed)
    j = s['journey']
    j['gender'] = 'female'
    j['wallet'] = wallet
    j['stats']['max_wallet'] = max(wallet, j['stats']['max_wallet'])
    validate_state(s)
    return s


def owner(wallet=5000, trade='milk_tea', served=12, chapter=3):
    s = story(wallet)
    j = s['journey']
    j['chapter'] = chapter
    j['done'] = list(range(1, chapter))
    for n in range(2, chapter + 1):
        jr._unlock_chapter(j, n)
    s['careers'][trade]['metrics']['served'] = served
    validate_state(s)
    return s


def act(s, _name, **p):
    return apply_action(s, None, _name, p)


def refused(test, s, _name, code=None, **p):
    before = copy.deepcopy(s)
    with test.assertRaises(GameError) as cm:
        act(s, _name, **p)
    test.assertEqual(s, before)   # a refusal changes nothing
    if code:
        test.assertEqual(cm.exception.code, code)
    return str(cm.exception)


def Q(s):
    return s['journey']['quay']


def ST(s, i=0):
    return Q(s)['stalls'][i]


def days(s, n=1, collect=False):
    """Close `n` life days the way end_day does for the counters: life_day moves, every counter runs the day."""
    with mock.patch.object(qy, '_x3', lambda t: False):
        for _ in range(n):
            s['journey']['life_day'] += 1
            qy.on_life_day(s)
    validate_state(s)
    return s


def opened(place='xe', wallet=5000, staff=True, **kw):
    s = owner(wallet, **kw)
    s, _ = act(s, 'jr_quay_open', trade='milk_tea', place=place, name='Trà Mây', confirm=True)
    if staff:
        for c in qy.candidates(s, ST(s))[:qy.PLACES[place]['slots']]:
            s, _ = act(s, 'jr_quay_hire', stall=ST(s)['id'], cand=c['id'], wage=c['ask'])
    return s


def bare(place, trade, seed=7, items=(), order='vua'):
    """A counter on its own (the simulation the economy tests use): staffed at what they ask, a big fund."""
    s = {'journey': {'seed': seed, 'life_day': 1, 'wallet': 10**6, 'story': True, 'history': [], 'in_debt': False,
                     'stats': {'max_wallet': 0}}, 'careers': {}}
    st = dict(id='q1', trade=trade, place=place, name='X', opened=0, day=0, fund=10**6, till=0, order=order, due=0, left=0,
              rep=100, items=list(items), staff=[], case=None, theft=0, hist=[], log=[])
    for c in qy.candidates(s, st)[:qy.PLACES[place]['slots']]:
        st['staff'].append(dict(id=c['id'], name=c['name'], wage=c['ask'], ask=c['ask'], mo=60, d=0, g=c['g']))
    return s, st


def simulate(place, trade, n=1000, **kw):
    s, st = bare(place, trade, **kw)
    nets, thefts = [], []
    with mock.patch.object(qy, '_x3', lambda t: False):
        for d in range(1, n + 1):
            s['journey']['life_day'] = d + 1
            st['left'] = 0
            till = st['till']
            fund = st['fund']
            qy.run_day(s, st, d)
            nets.append(st['hist'][-1]['net'])
            if st['theft'] == d:
                thefts.append((d, st['case']['lost'], st['case']['all'], fund))
            st['case'] = None
    return nets, thefts, st


class Unlock(unittest.TestCase):
    def test_locked_before_chapter_three_and_without_a_trade(self):
        s = owner(chapter=2)
        self.assertIn('chương 3', refused(self, s, 'jr_quay_open', 'locked', trade='milk_tea', place='xe', confirm=True))
        s = owner(served=3)
        refused(self, s, 'jr_quay_open', 'locked', trade='milk_tea', place='xe', confirm=True)
        s = owner()
        refused(self, s, 'jr_quay_open', 'locked', trade='florist', place='xe', confirm=True)   # a trade you do not know
        self.assertEqual(qy.known_trades(s), ['milk_tea'])

    def test_view_only_once_reached(self):
        s = story()
        self.assertNotIn('quay', public_state(s)['journey'])          # a new player: nothing in the state
        s = owner()
        v = public_state(s)['journey']['quay']
        self.assertEqual(v['stalls'], [])
        self.assertIsNone(v['lock'])
        self.assertEqual(v['can'], ['milk_tea'])
        self.assertIn('quay', jr.content())


class Opening(unittest.TestCase):
    def test_open_takes_price_and_fund(self):
        s = owner(2000)
        s, r = act(s, 'jr_quay_open', trade='milk_tea', place='xe', name='  Trà Mây  ', confirm=True)
        st = ST(s)
        self.assertEqual(st['name'], 'Trà Mây')
        self.assertEqual(st['fund'] + st['business']['expenses']['goods'], qy.start_fund('xe'))
        self.assertEqual(s['journey']['wallet'], 2000 - qy.open_cost('xe'))
        row = s['journey']['history'][-1]
        self.assertEqual((row['kind'], row['amount'], row['career']), ('invest', -qy.open_cost('xe'), 'milk_tea'))
        self.assertIn('cands', public_state(s)['journey']['quay']['stalls'][0])

    def test_open_uses_the_bank_after_the_wallet(self):
        s = owner(500)
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=400)
        s['journey']['bank']['balance'] += 600
        s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='xe', confirm=True)
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 1000 - (qy.open_cost('xe') - 100))

    def test_refusals(self):
        s = owner(100)
        self.assertIn('Cần', refused(self, s, 'jr_quay_open', 'no_money', trade='milk_tea', place='xe', confirm=True))
        s = owner(50000)
        refused(self, s, 'jr_quay_open', trade='milk_tea', place='xe')                  # no confirm
        refused(self, s, 'jr_quay_open', trade='milk_tea', place='villa', confirm=True)
        refused(self, s, 'jr_quay_open', trade='milk_tea', place='xe', name='x' * 40, confirm=True)
        s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='xe', confirm=True)
        s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='sap', confirm=True)
        s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='kiot', confirm=True)
        self.assertEqual(len(Q(s)['stalls']), 3)
        s2 = owner(5000)
        s2['journey']['wallet'] = -5
        refused(self, s2, 'jr_quay_open', 'in_debt', trade='milk_tea', place='xe', confirm=True)


class Staff(unittest.TestCase):
    def test_hire_wage_bounds_and_slots(self):
        s = opened('xe', staff=False)
        cands = qy.candidates(s, ST(s))
        self.assertEqual(len(cands), 3)
        c = cands[0]
        sid = ST(s)['id']
        self.assertIn('chê', refused(self, s, 'jr_quay_hire', 'too_low', stall=sid, cand=c['id'], wage=c['ask'] * 59 // 100))
        refused(self, s, 'jr_quay_hire', 'too_high', stall=sid, cand=c['id'], wage=c['ask'] * 3 + 1)
        s, _ = act(s, 'jr_quay_hire', stall=sid, cand=c['id'], wage=c['ask'] * 2)
        self.assertEqual(ST(s)['staff'][0]['mo'], 100)                      # paid twice what they ask: delighted
        refused(self, s, 'jr_quay_hire', 'full', stall=sid, cand=cands[1]['id'], wage=cands[1]['ask'])   # a cart: one person
        self.assertNotIn('cands', public_state(s)['journey']['quay']['stalls'][0])
        s, _ = act(s, 'jr_quay_wage', stall=sid, staff=c['id'], wage=c['ask'])
        s, _ = act(s, 'jr_quay_fire', stall=sid, staff=c['id'], confirm=True)
        self.assertEqual(ST(s)['staff'], [])

    def test_candidates_change_each_month_and_skip_the_hired(self):
        s = opened('kiot', wallet=30000, staff=False)
        a = [c['id'] for c in qy.candidates(s, ST(s))]
        s, _ = act(s, 'jr_quay_hire', stall=ST(s)['id'], cand=a[0], wage=30)
        self.assertNotIn(a[0], [c['id'] for c in qy.candidates(s, ST(s))])
        names = set()
        for m in range(8):
            s['journey']['life_day'] = 1 + m * qy.MONTH_DAYS
            names.add(tuple(c['id'] for c in qy.candidates(s, ST(s))))
        self.assertGreater(len(names), 1)

    def test_morale_follows_the_wage(self):
        s = opened('sap', wallet=20000, staff=False)
        sid = ST(s)['id']
        low, high = qy.candidates(s, ST(s))[:2]
        s, _ = act(s, 'jr_quay_hire', stall=sid, cand=low['id'], wage=low['ask'] * 6 // 10 + 1)
        s, _ = act(s, 'jr_quay_hire', stall=sid, cand=high['id'], wage=high['ask'] * 3 // 2)
        days(s, 6)
        a, b = ST(s)['staff']
        self.assertLess(a['mo'], 60)
        self.assertGreaterEqual(b['mo'], 80)


class DailyRun(unittest.TestCase):
    def test_takings_go_to_till_and_collection_to_wallet(self):
        from game import quay_business as qb
        s=opened('xe');st=ST(s)
        at=st['business']['cursor']/1000
        qb.settle(s,now=at+600)
        self.assertGreater(st['business']['sold'],0)
        till,wallet=st['till'],s['journey']['wallet']
        with mock.patch.object(qb.time,'time',return_value=at+600):
            s,_=act(s,'jr_quay_till',stall=st['id'])
        self.assertEqual(s['journey']['wallet'],wallet+till)
        self.assertEqual(ST(s)['till'],0)

    def test_life_days_never_double_pay_wall_clock(self):
        from game import quay_business as qb
        s=opened('xe');st=ST(s)
        qb.settle(s,now=st['business']['cursor']/1000+600)
        cash=st['till']+st['fund'];sold=st['business']['sold']
        days(s,5)
        self.assertEqual(st['till']+st['fund'],cash)
        self.assertEqual(st['business']['sold'],sold)

    def test_no_staff_no_run_no_cost(self):
        s = opened('xe', staff=False)
        fund = ST(s)['fund']
        days(s, 4)
        self.assertEqual((ST(s)['fund'], ST(s)['till'], ST(s)['hist']), (fund, 0, []))

    def test_absence_does_not_force_closure(self):
        s=opened('xe')
        days(s,qy.LEFT_DAYS+10)
        self.assertFalse(public_state(s)['journey']['quay']['stalls'][0]['closed'])
        self.assertEqual(ST(s)['left'],0)

    def test_out_of_fund_closes_the_day(self):
        s = opened('xe')
        ST(s)['fund'] = 0
        days(s, 1)
        self.assertEqual(ST(s)['hist'], [])

    def test_order_levels(self):
        s = opened('xe')
        s, _ = act(s, 'jr_quay_order', stall=ST(s)['id'], level='nhieu')
        self.assertEqual(ST(s)['order'], 'nhieu')
        refused(self, s, 'jr_quay_order', stall=ST(s)['id'], level='rat_nhieu')

    def test_upgrades(self):
        s = opened('xe')
        sid = ST(s)['id']
        w = s['journey']['wallet']
        s, _ = act(s, 'jr_quay_buy', stall=sid, item='ket', confirm=True)
        self.assertEqual(s['journey']['wallet'], w - qy.ITEMS['ket']['price']['xe'])
        refused(self, s, 'jr_quay_buy', stall=sid, item='ket', confirm=True)
        refused(self, s, 'jr_quay_buy', stall=sid, item='robot', confirm=True)
        s['journey']['wallet'] = 10
        refused(self, s, 'jr_quay_buy', 'no_money', stall=sid, item='bang', confirm=True)


class Rent(unittest.TestCase):
    def test_rent_is_elapsed_operating_time(self):
        from game import quay_business as qb
        s=opened('xe');st=ST(s)
        st['fund']=100000
        st['business']['stock']={d:1000 for d in qy._qs().menu(st)['on']}
        qb.settle(s,now=st['business']['cursor']/1000+600*qy.MONTH_DAYS)
        self.assertEqual(st['business']['expenses']['rent'],qy.PLACES['xe']['rent'])
        self.assertEqual(st['due'],0)

    def test_unpaid_rent_pauses_never_a_debt(self):
        s = opened('xe', staff=False)
        st = ST(s)
        st['fund'] = 0
        s['journey']['wallet'] = 0
        # Existing unpaid rent remains payable; idle days add no new charge.
        st['due'] = qy.PLACES['xe']['rent']
        days(s, qy.MONTH_DAYS)
        self.assertEqual(ST(s)['due'], qy.PLACES['xe']['rent'])
        self.assertEqual(s['journey']['wallet'], 0)                        # never below zero
        self.assertTrue(public_state(s)['journey']['quay']['stalls'][0]['closed'])
        refused(self, s, 'jr_quay_pay', 'no_money', stall=st['id'])
        s['journey']['wallet'] = 100
        s, _ = act(s, 'jr_quay_pay', stall=st['id'])
        self.assertEqual((ST(s)['due'], s['journey']['wallet']), (0, 100 - qy.PLACES['xe']['rent']))
        self.assertEqual(s['journey']['history'][-1]['kind'], 'upkeep')


class Economy(unittest.TestCase):
    def test_normal_margin_modest_everywhere(self):
        from game import quay_economy as qe
        for place in qy.PLACE_IDS:
            for trade in qy.TRADE_IDS:
                s,st=bare(place,trade); qy.ensure(s)['stalls'].append(st)
                revenue=net=0
                with mock.patch.object(qe,'_event',return_value=None), mock.patch.object(qy,'_x3',return_value=False):
                    for d in range(1,601):
                        qy._sell(s,st,d)
                        revenue+=st['hist'][-1]['rev'];net+=st['hist'][-1]['net']
                self.assertTrue(.08 <= net/revenue <= .18,(place,trade,net/revenue))

    def test_bad_days_exist_but_business_recovers(self):
        nets,_,_=simulate('sap','cafe_bakery',600)
        self.assertGreater(sum(nets),0)
        self.assertTrue(any(n<0 for n in nets))
        self.assertGreater(len(set(nets)),20)

    def test_shift_value(self):
        for place in qy.PLACE_IDS:
            for trade in qy.TRADE_IDS:
                self.assertTrue(50 <= qy.shift_value(place, trade) <= 160, (place, trade))


class Thieves(unittest.TestCase):
    def test_rare_capped_and_only_the_till(self):
        for place in qy.PLACE_IDS:
            nets, thefts, st = simulate(place, 'milk_tea', 2000, seed=11)
            self.assertTrue(10 <= len(thefts) <= 150, (place, len(thefts)))   # occasionally
            days_ = [d for d, *_ in thefts]
            self.assertTrue(all(b - a >= qy.THEFT_GAP for a, b in zip(days_, days_[1:])))
            self.assertTrue(all(d > qy.THEFT_SAFE_DAYS for d in days_))
            self.assertTrue(all(lost > 0 for _, lost, _, _ in thefts))

    def test_cap_and_safe(self):
        from game import quay_economy as qe
        losses=[]
        for safe in (False,True):
            s,st=bare('xe','milk_tea',seed=3,items=['ket'] if safe else [])
            st['till']=5000
            with mock.patch.object(qe,'_event',return_value='theft'):
                qy._sell(s,st,20)
            losses.append(st['case']['lost'])
            self.assertLessEqual(st['case']['lost'], qy.THEFT_CAP*max(qy.avg_revenue(st),qy.THEFT_MIN))
            self.assertEqual(st['fund'],10**6)
            if safe:self.assertFalse(st['case']['all'])
        self.assertLess(losses[1],losses[0])

    def test_police(self):
        s = opened('xe')
        st = ST(s)
        st['case'] = dict(day=s['journey']['life_day'] - 1, lost=40, all=False, rep=False, due=0)
        s, r = act(s, 'jr_quay_police', stall=st['id'])
        self.assertTrue(ST(s)['case']['rep'])
        refused(self, s, 'jr_quay_police', stall=st['id'])
        days(s, qy.POLICE_DAYS + 1)
        self.assertIsNone(ST(s)['case'])
        self.assertTrue(any('Công an' in x['t'] for x in ST(s)['log']))

    def test_unreported_case_closes(self):
        s = opened('xe')
        ST(s)['case'] = dict(day=s['journey']['life_day'] - 1, lost=40, all=False, rep=False, due=0)
        days(s, 7)
        self.assertIsNone(ST(s)['case'])


class Selling(unittest.TestCase):
    def test_sell_back(self):
        s = opened('xe')
        days(s, 2)
        st = ST(s)
        back = qy.PLACES['xe']['price'] // 2 + st['till'] + st['fund']
        w = s['journey']['wallet']
        s, _ = act(s, 'jr_quay_sell', stall=st['id'], confirm=True)
        self.assertEqual(s['journey']['wallet'], w + back)
        self.assertEqual(Q(s)['stalls'], [])
        refused(self, s, 'jr_quay_till', 'no_stall', stall=st['id'])

    def test_credit_after_selling_goes_to_the_wallet(self):
        s = opened('xe')
        sid = ST(s)['id']
        line = qy.credit(s, sid, 'shift', 30, 'Ca của Lan')
        self.assertIn('két', line)
        s, _ = act(s, 'jr_quay_sell', stall=sid, confirm=True)
        w = s['journey']['wallet']
        qy.credit(s, sid, 'refund', 20, 'Trả lại lương giữ')
        self.assertEqual(s['journey']['wallet'], w + 20)
        validate_state(s)


class Validation(unittest.TestCase):
    def test_tampering_is_rejected(self):
        s = opened('xe')
        days(s, 2)
        validate_state(s)
        for edit in (lambda q: q.update(v=2), lambda q: q['stalls'][0].update(fund=-1), lambda q: q['stalls'][0].update(place='villa'),
                     lambda q: q['stalls'][0].update(rep=200), lambda q: q['stalls'][0]['staff'][0].update(mo=101),
                     lambda q: q['stalls'][0]['items'].append('robot'), lambda q: q['stalls'].append(copy.deepcopy(q['stalls'][0])),
                     lambda q: q['stalls'][0].pop('till'), lambda q: q.update(shift={'id': 'x'}), lambda q: q.update(out=[{}]),
                     lambda q: q['stalls'][0].update(name=''), lambda q: q['stalls'][0]['hist'].append({'d': 1})):
            bad = copy.deepcopy(s)
            edit(bad['journey']['quay'])
            with self.assertRaises(GameError):
                validate_state(bad)

    def test_a_newer_build_may_add_keys(self):
        s = opened('xe')
        ST(s)['future'] = 1
        Q(s)['later'] = []
        ST(s)['staff'][0]['extra'] = 'x'
        validate_state(s)

    def test_determinism(self):
        with mock.patch('game.quay_business.time.time',return_value=1000):
            a, b = opened('sap', wallet=20000), opened('sap', wallet=20000)
        days(a, 12)
        days(b, 12)
        self.assertEqual(Q(a), Q(b))

    def test_public_state_budget_untouched_for_new_players(self):
        from tests.test_journey import Play
        p = Play()
        self.assertNotIn('quay', public_state(p.s)['journey'])


class PreviousServer(unittest.TestCase):
    """Quay state crosses 1.4.31; this is not a whole-save rollback guarantee for newer careers/menus."""

    def old_tree(self):
        old = os.environ.get('MNL_OLD_TREE') or str(ROOT.parent / '_rel1431' / 'mot-ngay-lam-nghe')
        if not (Path(old) / 'game' / 'engine.py').is_file():
            self.skipTest('no 1.4.31 tree (MNL_OLD_TREE)')
        return old

    def run_old(self, prog, s):
        old = self.old_tree()
        env = dict(os.environ, PYTHONPATH=old, PYTHONDONTWRITEBYTECODE='1')
        out = subprocess.run([sys.executable, '-c', prog], input=json.dumps(s), capture_output=True, text=True, cwd=old, env=env,
                             encoding='utf-8', timeout=300)
        self.assertEqual(out.returncode, 0, out.stderr[-3000:])
        return json.loads(out.stdout)

    def test_a_counter_save_on_the_previous_server_and_back(self):
        s = opened('sap', wallet=20000)
        days(s, 7)
        s, _ = act(s, 'jr_quay_till', stall=ST(s)['id'])
        s, _ = act(s, 'jr_quay_fund', stall=ST(s)['id'], amount=50)
        s, _ = act(s, 'jr_quay_fund', stall=ST(s)['id'], amount=-20)
        s, _ = act(s, 'jr_quay_buy', stall=ST(s)['id'], item='bang', confirm=True)
        ST(s)['case'] = dict(day=s['journey']['life_day'] - 1, lost=40, all=False, rep=False, due=0)
        Q(s)['shift'] = dict(id='qj-0123456789ab', career='milk_tea', day=3, base=0, wage=40, value=70, who='Lan', name='Trà Lan', until=2000000000)
        Q(s)['out'] = [dict(id='qj-0123456789ac', tasks=3, stars=45, late=False)]
        s['journey']['live_fx'] = ['0123456789abcdef']
        validate_state(s)
        kinds = {r['kind'] for r in s['journey']['history']}
        self.assertTrue(kinds <= {'invest', 'draw', 'upkeep', 'living', 'salary', 'life'}, kinds)
        cafe = s['careers']['cafe_bakery']
        self.assertEqual((cafe['day'], cafe['open'], cafe['tasks'], cafe['active_task'], cafe['metrics']),
                         (1, False, [], None, {}))
        # Only the untouched cafe gets its old menu defaults; all quay state remains under test.
        prog = ('import json,sys;from game.engine import validate_state,migrate_state,new_state,apply_action,public_state,GameError;'
                'from game.content import CAREERS;s=json.load(sys.stdin);s["careers"]={k:v for k,v in s["careers"].items() if k in CAREERS};'
                's["careers"]["cafe_bakery"]=new_state()["careers"]["cafe_bakery"];'
                's["journey"]["unlocked"]=[k for k in s["journey"]["unlocked"] if k in CAREERS];'   # 1.5.0's new careers (not this feature)
                's=migrate_state(s);validate_state(s);public_state(s);'
                's,_=apply_action(s,"milk_tea","select_career",{});s,_=apply_action(s,"milk_tea","start_day",{});'
                's,_=apply_action(s,"milk_tea","end_day",{"carry_event":True});validate_state(s);'
                'code="";\n'
                'try:\n apply_action(s,None,"jr_quay_till",{"stall":"q1"})\n'
                'except GameError as e:\n code=e.code\n'
                'print(json.dumps(dict(s=s,code=code)))')
        got = self.run_old(prog, s)
        self.assertEqual(got['code'], 'unknown_action')                  # a new page on the old server: refused cleanly
        back = got['s']
        self.assertEqual(back['journey']['quay'], s['journey']['quay'])   # the old build kept the block untouched
        back = migrate_state(back)
        validate_state(back)
        before = len(ST(back)['hist'])
        qy.on_life_day(back)                                               # the day played there is caught up here
        self.assertEqual(len(ST(back)['hist']), before)
        validate_state(back)


if __name__ == '__main__':
    unittest.main()
