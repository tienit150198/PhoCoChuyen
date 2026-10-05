import copy
import importlib
import unittest

from game.engine import GameError, new_state, validate_state, migrate_state
from tests.test_quay_business import fixture


class ShopEvents(unittest.TestCase):
    def test_four_expenses_are_visible_opt_in_budgeted_and_recorded_once(self):
        ev=self.api()
        expected={'equipment_repair':240,'stock_spoil':160,'staff_training':200,'local_promotion':180}
        self.assertTrue(set(expected)<=set(ev.CATALOGUE))
        self.assertNotIn('stock_spoil',ev.eligible_kinds('clothing',None))
        for kind,cost in expected.items():
            for quay in (False,True):
                with self.subTest(kind=kind,quay=quay):
                    s,c=self.spawn(kind,quay)
                    if quay:c.update(fund=1000,till=100)
                    else:
                        from game import operations
                        c['money']+=1000;operations.record_money(c,1000,'Vốn thử nghiệm','test-capital','other_income')
                    before=copy.deepcopy(c);public=ev.public(c,quay)
                    self.assertEqual(c,before)
                    paid=next(x for x in public['pending']['choices'] if x['cost'])
                    self.assertEqual(paid['cost'],cost);self.assertGreater(paid['rep'],0)
                    self.assertTrue(any(x['cost']==0 for x in public['pending']['choices']))
                    choose=ev.choose_quay if quay else lambda s,c,p:ev.choose_career(s,c,'milk_tea',p)
                    payload=dict(event=public['pending']['id'],choice=paid['id'],confirm=True)
                    cash=c['fund']+c['till'] if quay else c['money']
                    with self.assertRaises(GameError):choose(s,c,dict(payload,confirm=False))
                    choose(s,c,payload)
                    self.assertEqual(cash-(c['fund']+c['till'] if quay else c['money']),cost)
                    snapshot=copy.deepcopy(c)
                    with self.assertRaises(GameError):choose(s,c,payload)
                    self.assertEqual(c,snapshot)
                    ev.validate(c if quay else c['ops'],'q1' if quay else 'milk_tea','milk_tea','xe' if quay else None)
                    s,c=self.spawn(kind,quay)
                    if quay:c.update(fund=0,till=0)
                    else:c['money']=0
                    snapshot=copy.deepcopy(c)
                    with self.assertRaises(GameError):choose(s,c,payload)
                    self.assertEqual(c,snapshot)

    def test_protection_stacks_with_camera_without_eliminating_risk(self):
        ev=self.api()
        plain=ev.theft_probability([])
        self.assertAlmostEqual(ev.theft_probability(['alarm'],'premium'),plain*.75*.6)
        self.assertAlmostEqual(ev.theft_probability(['alarm','camera'],'premium'),plain*.75*.6*.5)
        self.assertGreater(ev.theft_probability(['alarm','camera','ket'],'premium'),0)

    def test_protective_equipment_quote_matches_actual_charge(self):
        ev=self.api()
        for kind,item,choice in [('power_cut','surge','repair'),('shop_inspection','hygiene','rectify')]:
            s,c=self.spawn(kind,True);c.update(fund=100,till=100)
            before=ev.public(c,True)['pending']
            regular=next(x['cost'] for x in before['choices'] if x['id']==choice)
            c['items'].append(item)
            quote=next(x['cost'] for x in ev.public(c,True)['pending']['choices'] if x['id']==choice)
            self.assertEqual(quote,(regular+1)//2)
            cash=c['fund']+c['till']
            tax_loss=c['business']['income_tax']['loss']
            ev.choose_quay(s,c,dict(event=before['id'],choice=choice,confirm=True))
            self.assertEqual(cash-c['fund']-c['till'],quote)
            self.assertEqual(c['business']['income_tax']['loss'],tax_loss+quote)
            ev.validate(c,c['id'],c['trade'],c['place'])
            # Historical discounts stay valid even if equipment later changes.
            c['items'].remove(item)
            ev.validate(c,c['id'],c['trade'],c['place'])

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('game.shop_events'), 'Recurring owner events are missing')
        return importlib.import_module('game.shop_events')

    def test_camera_halves_theft_for_every_security_configuration(self):
        ev = self.api()
        for items in ([], ['ket'], ['lock', 'bell', 'light']):
            self.assertGreater(ev.theft_probability(items + ['camera']), 0)
            self.assertEqual(ev.theft_probability(items + ['camera']), ev.theft_probability(items) / 2)
        # Same roll and selection pool: camera never renormalizes theft back up.
        plain = sum(ev.select_kind('milk_tea', 'xe', [], i, 1) == 'theft' for i in range(4000))
        camera = sum(ev.select_kind('milk_tea', 'xe', ['camera'], i, 1) == 'theft' for i in range(4000))
        self.assertTrue(.42 < camera / plain < .58, (plain, camera))

    def test_eligibility_and_at_least_ten_scenarios(self):
        ev = self.api()
        self.assertGreaterEqual(len(ev.CATALOGUE), 10)
        self.assertIn('dine_dash', ev.eligible_kinds('pho', None))
        self.assertNotIn('dine_dash', ev.eligible_kinds('clothing', None))
        self.assertIn('traffic_inspection', ev.eligible_kinds('milk_tea', 'xe'))
        self.assertNotIn('traffic_inspection', ev.eligible_kinds('milk_tea', 'kiot'))
        self.assertFalse(ev.career_eligible('accounting'))

    def test_migration_pending_reload_recurrence_and_offline_no_cost(self):
        ev = self.api(); s, st = fixture()
        from game import quay_business as qb
        qb.initialize(s, st, now=1000)
        ev.tick_quay(s, st)
        self.assertIsNone(st['shop_events']['pending'])
        money = st['fund'] + st['till']
        st['business']['sold'] += ev.GAP
        ev.tick_quay(s, st)
        pending = copy.deepcopy(st['shop_events']['pending'])
        self.assertIsNotNone(pending)
        ev.tick_quay(s, st)
        self.assertEqual(st['shop_events']['pending'], pending)
        reload = copy.deepcopy(s); ev.tick_quay(reload, reload['journey']['quay']['stalls'][0])
        self.assertEqual(s, reload)
        st['business']['sold'] += 100000
        ev.tick_quay(s, st)
        self.assertEqual(st['shop_events']['pending'], pending)
        self.assertEqual(st['fund'] + st['till'], money)
        view = ev.public(st, quay=True)
        choice = next(x for x in view['pending']['choices'] if x['affordable'])
        ev.choose_quay(s, st, dict(event=pending['id'], choice=choice['id'], confirm=True))
        before = copy.deepcopy(s)
        with self.assertRaises(GameError):
            ev.choose_quay(s, st, dict(event=pending['id'], choice=choice['id'], confirm=True))
        self.assertEqual(s, before)
        ev.tick_quay(s, st)
        self.assertIsNone(st['shop_events']['pending'])
        st['business']['sold'] += ev.GAP
        ev.tick_quay(s, st)
        self.assertNotEqual(st['shop_events']['pending']['id'], pending['id'])

    def spawn(self, kind, quay=False):
        ev = self.api()
        if quay:
            s, c = fixture()
            from game import quay_business as qb
            qb.initialize(s, c, now=1000)
            ev.tick_quay(s, c)
            container = c
        else:
            s = new_state(); c = s['careers']['milk_tea']; c['started'] = True
            ev.tick_career(s, c, 'milk_tea'); container = c['ops']
        container['shop_events']['seq'] = 1
        container['shop_events']['pending'] = ev.make_event(kind, 1, 'q1' if quay else 'milk_tea', False)
        return s, c

    def test_cost_ledger_once_and_quay_loss_accounting(self):
        ev = self.api()
        for quay in (False, True):
            s, c = self.spawn('influencer', quay)
            if quay: c.update(fund=100, till=100)
            event = ev.public(c, quay=quay)['pending']
            option = next(x for x in event['choices'] if x['cost'] > 0)
            before = c['fund'] + c['till'] if quay else c['money']
            choose = ev.choose_quay if quay else lambda s,c,p: ev.choose_career(s,c,'milk_tea',p)
            choose(s,c,dict(event=event['id'],choice=option['id'],confirm=True))
            after = c['fund'] + c['till'] if quay else c['money']
            self.assertEqual(before-after, option['cost'])
            if quay:self.assertEqual(c['business']['expenses']['loss'], option['cost'])
            else:
                f=c['ops']['finance']; self.assertEqual(c['money'],f['opening_balance']+sum(x['amount'] for x in f['ledger']))
                validate_state(s)

    def test_insufficient_funds_free_alternative_and_invalid_choice_atomic(self):
        ev = self.api(); s,c = self.spawn('shop_inspection'); c['money']=0
        event=ev.public(c)['pending']; expensive=next(x for x in event['choices'] if x['max_cost']>0)
        before=copy.deepcopy(c)
        with self.assertRaises(GameError):ev.choose_career(s,c,'milk_tea',dict(event=event['id'],choice=expensive['id'],confirm=True))
        self.assertEqual(c,before)
        for payload in (dict(event=event['id'],choice='forged',confirm=True),dict(event=event['id'],choice=expensive['id'],confirm=True,cost=0)):
            with self.assertRaises(GameError):ev.choose_career(s,c,'milk_tea',payload)
            self.assertEqual(c,before)
        free=next(x for x in event['choices'] if x['max_cost']==0)
        ev.choose_career(s,c,'milk_tea',dict(event=event['id'],choice=free['id'],confirm=True))
        self.assertEqual(c['money'],0)
        self.assertIsNone(c['ops']['shop_events']['pending'])

    def test_loss_is_bounded_and_camera_cannot_change_pending(self):
        ev=self.api(); s,c=self.spawn('theft'); event=copy.deepcopy(c['ops']['shop_events']['pending'])
        c['ops']['security']['items'].append('camera')
        ev.tick_career(s,c,'milk_tea')
        self.assertEqual(event,c['ops']['shop_events']['pending'])
        c['money']=5
        choice=ev.public(c)['pending']['choices'][-1]
        ev.choose_career(s,c,'milk_tea',dict(event=event['id'],choice=choice['id'],confirm=True))
        self.assertGreaterEqual(c['money'],4)

    def test_optional_state_roundtrip_and_corruption_rejected(self):
        ev=self.api(); s=new_state(); validate_state(s)
        c=s['careers']['milk_tea']; c['started']=True
        ev.tick_career(s,c,'milk_tea'); validate_state(s)
        self.assertEqual(migrate_state(s)['careers']['milk_tea']['ops']['shop_events'], c['ops']['shop_events'])
        c['ops']['shop_events']['seq']=-1
        with self.assertRaises(GameError):validate_state(s)

    def test_legacy_pending_work_blocks_a_second_event(self):
        ev=self.api(); s,c=self.spawn('influencer')
        state=c['ops']['shop_events'];state['pending']=None
        c['ops']['work_ticks']=state['next']
        c['event']={'stage':'opening'}
        ev.tick_career(s,c,'milk_tea')
        self.assertIsNone(state['pending'])
        c['event']=None
        ev.tick_career(s,c,'milk_tea')
        self.assertIsNotNone(state['pending'])
        sq,st=fixture()
        from game import quay_business as qb
        qb.initialize(sq,st,1000);st['business']['sold']=ev.GAP
        st['run']={'ev':['thieu_mon'],'eo':[],'i':10,'k':20}
        ev.tick_quay(sq,st)
        self.assertIsNone(st['shop_events']['pending'])

    def test_every_scenario_resolves_with_empty_till(self):
        ev=self.api()
        for kind in ev.CATALOGUE:
            s,c=self.spawn(kind,quay=True);c.update(fund=0,till=0)
            event=ev.public(c,quay=True)['pending']
            choice=next(x for x in event['choices'] if x['affordable'])
            ev.choose_quay(s,c,dict(event=event['id'],choice=choice['id'],confirm=True))
            self.assertEqual(c['fund']+c['till'],0)

    def test_real_action_routes_camera_purchase_and_public_views(self):
        from tests.test_quay import opened, act, ST
        from game.engine import apply_action, public_state
        ev=self.api();s=opened(staff=False);sid=ST(s)['id']
        s,_=act(s,'jr_quay_buy',stall=sid,item='camera',confirm=True)
        s,_=act(s,'jr_quay_start',stall=sid)
        self.assertEqual(ST(s)['run']['ev'],[])
        st=ST(s);st['shop_events']['seq']=1
        st['shop_events']['pending']=ev.make_event('influencer',1,sid,True)
        v=public_state(s)['journey']['quay']['stalls'][0]['shop_events']
        self.assertTrue(v['camera']);self.assertTrue(v['pending']['camera_at_event'])
        s,_=act(s,'jr_quay_event',stall=sid,event=v['pending']['id'],choice='decline',confirm=True)
        self.assertIsNone(ST(s)['shop_events']['pending']);validate_state(s)
        s,c=self.spawn('influencer')
        event=c['ops']['shop_events']['pending']
        s,_=apply_action(s,'milk_tea','ops_shop_event',dict(event=event['id'],choice='decline',confirm=True))
        self.assertIsNone(s['careers']['milk_tea']['ops']['shop_events']['pending']);validate_state(s)

    def test_reputation_changes_real_staff_and_quay_arrival_intervals(self):
        from tests.test_workplace_business import WorkplaceBusinessTests
        from game import workplace_business as wb, quay_business as qb
        ev=self.api()
        s,c,e=WorkplaceBusinessTests().sample('milk_tea')
        ev.tick_career(s,c,'milk_tea')
        baseline=wb._seconds(c,e)
        c['ops']['shop_events']['reputation']=10
        self.assertLess(wb._seconds(c,e),baseline)
        c['ops']['shop_events']['reputation']=-10
        self.assertGreater(wb._seconds(c,e),baseline)
        sq,st=fixture();qb.initialize(sq,st,1000)
        baseline=qb._intervals(st);st['rep']=110
        good=qb._intervals(st)
        self.assertTrue(all(good[k]<v for k,v in baseline.items()))
        self.assertEqual(ev.public(c)['demand_factor'],.9)


if __name__ == '__main__':unittest.main()
