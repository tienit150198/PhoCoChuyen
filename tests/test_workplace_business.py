"""Continuous independent staff orders use server time, actual stock and local funds."""
import copy
import unittest
from unittest.mock import patch

from game import operations as ops
from game.engine import GameError, new_state
from game import workplace_business as wb


class WorkplaceBusinessTests(unittest.TestCase):
    def sample(self, career='accounting'):
        s = new_state()
        c = s['careers'][career]
        c.update(open=True, started=True)
        with patch.object(wb.time, 'time', return_value=2000000000):
            ops.action(s, c, career, 'ops_hire', {'candidate': career+'-staff-1', 'confirm': True})
            wb.settle(s)
        return s, c, c['ops']['staff'][0]

    def next(self, c):
        return min(x['at'] for x in c['ops']['business']['pending'].values())

    def test_hiring_while_owner_closed_starts_staff_clock(self):
        s=new_state();c=s['careers']['accounting'];c['started']=True
        with patch.object(wb.time,'time',return_value=2000000000):
            ops.action(s,c,'accounting','ops_hire',{'candidate':'accounting-staff-1','confirm':True})
            wb.settle(s)
        self.assertFalse(c['open']);self.assertTrue(c['ops']['staff'][0]['on_shift'])
        wb.settle(s,self.next(c));self.assertEqual(c['ops']['business']['served'],1)

    def test_closed_owner_poll_and_offline_have_equal_profit_and_carry(self):
        s,c,e=self.sample();c['open']=False;other=copy.deepcopy(s)
        now=self.next(c);step=next(iter(c['ops']['business']['pending'].values()))['seconds']
        for at in range(now,now+step*10,step):wb.settle(s,at)
        wb.settle(other,now+step*9)
        self.assertEqual(s,other)
        before=copy.deepcopy(other);wb.settle(other,now+step*9);self.assertEqual(before,other)

    def test_legacy_anchor_and_poll_idempotence(self):
        s,c,e=self.sample()
        b=c['ops']['business'];self.assertEqual(b['served'],0)
        now=self.next(c);before=c['money']
        self.assertTrue(wb.due(s,now));self.assertTrue(wb.settle(s,now))
        self.assertEqual(b['served'],1);self.assertGreater(b['revenue'],0)
        row=b['recent'][-1]
        self.assertEqual(c['money']-before,row['revenue']-row['cash_expenses']+wb.public(c,now)['recent'][-1]['profit_bonus'])
        snap=copy.deepcopy(s);self.assertFalse(wb.settle(s,now));self.assertEqual(s,snap)
        self.assertEqual(c['money'],c['ops']['finance']['opening_balance']+sum(x['amount'] for x in c['ops']['finance']['ledger']))

    def test_all_41_careers_have_real_independent_orders_and_keep_manual_work(self):
        self.assertEqual(len(new_state()['careers']),43)   # + library (thư viện), oil (thợ dầu khí)
        for career in new_state()['careers']:
            with self.subTest(career=career):
                s,c,e=self.sample(career);tasks=copy.deepcopy(c['tasks'])
                s['current']='mother_baby' if career!='mother_baby' else 'accounting'
                wb.settle(s,self.next(c))
                self.assertEqual(c['ops']['business']['served'],1)
                self.assertEqual(c['tasks'],tasks)
                self.assertEqual(wb.public(c)['recent'][-1]['employee'],e['id'])
                ops.validate(c,career)

    def test_no_staff_offshift_incident_rest_and_strike_do_not_earn(self):
        for mode in ('none','off','incident','rest','strike','fired'):
            with self.subTest(mode=mode):
                s,c,e=self.sample();at=self.next(c)
                if mode=='none':c['ops']['staff']=[]
                elif mode=='off':e['on_shift']=False
                elif mode=='incident':c['ops']['incident']={'practice':False,'status':'noticed','employee':e['id']}
                elif mode=='strike':e['strike']=True
                elif mode=='fired':e['status']='former'
                else:e['rest_until']=c['turn']+4
                wb.settle(s,at+10000)
                self.assertEqual(c['ops']['business']['served'],0)

    def test_stock_is_consumed_fefo_and_stops_without_autobuy(self):
        s,c,e=self.sample('grocery')
        inv=c['ext']['inv'];inv['lots']=[dict(id='late',item='rice',qty=10,unit_cost=5,expires=7,received=1,supplier='opening'),dict(id='early',item='rice',qty=6,unit_cost=4,expires=3,received=1,supplier='opening')]
        wallet=s['journey']['wallet'];wb.settle(s,self.next(c))
        row=wb._recent(c)[-1];q=row['items']['rice']
        self.assertEqual(set(row['items']),{'rice'});self.assertGreater(q,1)
        lots={x['id']:x['qty'] for x in inv['lots']}
        self.assertEqual(lots.get('late'),10);self.assertEqual(lots.get('early',0),6-q)
        self.assertEqual(row['goods'],4*q)
        wb.settle(s,self.next(c)+10000)
        self.assertEqual(c['ops']['business']['reason'],'stock')
        self.assertEqual(sum(r['items']['rice'] for r in wb._recent(c)),16-sum(x['qty'] for x in inv['lots']))
        self.assertEqual(s['journey']['wallet'],wallet)

    def test_insufficient_funds_stop_before_stock_or_income(self):
        s,c,e=self.sample('grocery');c['money']=0
        lots=copy.deepcopy(c['ext']['inv']['lots'])
        wb.settle(s,self.next(c)+10000)
        self.assertEqual(c['money'],0);self.assertEqual(c['ext']['inv']['lots'],lots)
        self.assertEqual(c['ops']['business']['served'],0)
        self.assertEqual(c['ops']['business']['reason'],'fund')

    def test_bounded_catchup_preserves_backlog_and_does_not_repeat(self):
        s,c,e=self.sample();c['money']=100000
        now=self.next(c)+10000000
        wb.settle(s,now)
        self.assertEqual(c['ops']['business']['served'],wb.MAX_ORDERS)
        self.assertTrue(wb.due(s,now))
        wb.settle(s,now)
        self.assertEqual(c['ops']['business']['served'],2*wb.MAX_ORDERS)

    def test_public_marks_remaining_catchup_until_all_due_orders_finish(self):
        s,c,e=self.sample();now=self.next(c)+1000
        with patch.object(wb,'MAX_ORDERS',1):
            wb.settle(s,now)
        self.assertTrue(wb.public(c,now)['catching_up'])
        wb.settle(s,now)
        self.assertFalse(wb.public(c,now)['catching_up'])
        self.assertGreater(wb.public(c,now)['next_at'],now)

    def test_new_staff_does_not_also_work_on_turns_or_accrue_old_payroll(self):
        s,c,e=self.sample();at=self.next(c)
        for _ in range(10):ops.tick(s,c,'accounting','advance')
        self.assertEqual(e['jobs'],0);self.assertFalse(c['ops']['attendance'])
        wb.settle(s,at)
        self.assertEqual(e['jobs'],1);self.assertEqual(ops._payroll(c,c['day']),[])
        self.assertEqual(ops.job_bonus(c,c['day']),[])

    def test_public_projection_read_only_and_corrupt_timestamp_rejected(self):
        s,c,e=self.sample();before=copy.deepcopy(c)
        v=ops.public_operations(c)['business'];v['recent'].append({})
        self.assertEqual(c,before)
        c['ops']['business']['pending'][e['id']]['at']=True
        with self.assertRaises(GameError):ops.validate(c,'accounting')

    def test_pause_command_is_no_longer_supported(self):
        s,c,e=self.sample()
        before=copy.deepcopy(s)
        with self.assertRaises(GameError):ops.action(s,c,'accounting','ops_staff_business_pause',{'paused':True})
        self.assertEqual(s,before)

    def test_end_day_preserves_staff_timer_and_completes_while_owner_closed(self):
        s,c,e=self.sample()
        before=copy.deepcopy(c['ops']['business']['pending']);at=self.next(c)
        ops.on_close(s,c,'accounting')
        c['open']=False
        self.assertEqual(c['ops']['business']['pending'],before)
        self.assertTrue(e['on_shift']);self.assertTrue(wb.due(s,at))
        wb.settle(s,at);self.assertEqual(c['ops']['business']['served'],1)
        self.assertEqual(wb.public(c,at)['status'],'running')

    def test_legacy_closed_and_paused_resume_from_now_without_backpay(self):
        for reason in ('closed','paused'):
            with self.subTest(reason=reason):
                s,c,e=self.sample();c['ops'].pop('business_profit',None)
                b=c['ops']['business'];b['reason']=reason;b['paused']=reason=='paused'
                c['open']=reason!='closed';now=2000100000
                self.assertTrue(wb.due(s,now));wb.settle(s,now)
                self.assertEqual(b['served'],0);self.assertFalse(b['paused']);self.assertGreater(self.next(c),now)
                wb.settle(s,self.next(c));self.assertEqual(b['served'],1)
                ops.validate(c,'accounting')

    def test_profit_bonus_is_40_percent_of_positive_margin_with_fractional_carry(self):
        s,c,e=self.sample();cash=c['money'];base_tax=c['ops']['finance']['period_revenue']
        for _ in range(10):wb.settle(s,self.next(c))
        b=c['ops']['business'];rows=b['recent'];profit=sum(max(0,r['revenue']-r['goods']-r['wage']-r['materials']) for r in rows)
        bonus,carry=divmod(profit*40,100);p=c['ops']['business_profit']
        self.assertEqual((p['total'],p['carry']),(bonus,carry))
        self.assertEqual(c['money']-cash,sum(r['revenue']-r['cash_expenses'] for r in rows)+bonus)
        self.assertEqual(c['ops']['finance']['period_revenue']-base_tax,b['revenue'],'bonus is other_income, not extra taxable customer revenue')
        self.assertEqual(sum(x['amount'] for x in c['ops']['finance']['ledger'] if x['category']=='other_income'),bonus)
        public=wb.public(c);self.assertEqual(public['net'],b['net']+bonus);self.assertEqual(public['profit_bonus'],bonus)
        self.assertEqual(sum(r['profit_bonus'] for r in public['recent']),bonus)
        self.assertEqual(set(b),set(wb._new(0)),'old exact-key business schema stays compatible')
        ops.validate(c,'accounting')

    def test_loss_making_orders_never_receive_bonus(self):
        s,c,e=self.sample()
        with patch.dict(wb.ORDERS,{'accounting':('Loss order',1,5,{})}):
            wb.settle(s,self.next(c))
        self.assertLess(c['ops']['business']['net'],0)
        self.assertEqual(c['ops']['business_profit']['total'],0)

    def test_profit_carry_corruption_is_rejected(self):
        s,c,e=self.sample();wb.settle(s,self.next(c))
        c['ops']['business_profit']['carry']=True
        with self.assertRaises(GameError):ops.validate(c,'accounting')

    def test_many_careers_catch_up_in_time_order(self):
        s,c,e=self.sample()
        other=s['careers']['secretary'];other.update(open=True,started=True)
        with patch.object(wb.time,'time',return_value=2000000000):
            ops.action(s,other,'secretary','ops_hire',{'candidate':'secretary-staff-1','confirm':True})
        wb.settle(s,2000000000+10000000)
        self.assertGreater(c['ops']['business']['served'],0)
        self.assertGreater(other['ops']['business']['served'],0)

    def test_resource_stop_does_not_write_on_each_poll(self):
        s,c,e=self.sample();c['money']=0
        wb.settle(s,self.next(c));before=copy.deepcopy(s)
        self.assertFalse(wb.due(s,2000100000))
        self.assertFalse(wb.settle(s,2000100000))
        self.assertEqual(s,before)

    def test_legacy_basket_reservation_is_not_consumed(self):
        s,c,e=self.sample('mother_baby')
        for k in c['stock']:c['stock'][k]=0
        c['stock']['bunny']=1
        c['tasks']=[dict(status='waiting',basket={'bunny':1})]
        wb.settle(s,self.next(c))
        self.assertEqual(c['stock']['bunny'],1)
        self.assertEqual(c['ops']['business']['reason'],'stock')

    def test_legacy_attendance_remains_payable_exactly_once(self):
        s,c,e=self.sample();ops._attendance(c,e)
        c['ops']['attendance'][str(c['day'])][e['id']]['jobs']=2
        wb.settle(s,self.next(c))
        self.assertEqual(len(ops._payroll(c,c['day'])),1)
        ops._payroll(c,c['day'])
        self.assertEqual(len(c['ops']['finance']['bills']),1)
        self.assertEqual(ops.job_bonus(c,c['day'])[0]['jobs'],2)

    def test_gear_changes_next_order_not_pending_order(self):
        s,c,e=self.sample();first=self.next(c)
        with patch('game.work_gear.factor',return_value=1.6):
            wb.settle(s,2000000030)
            self.assertEqual(self.next(c),first)
            wb.settle(s,first)
            self.assertLess(self.next(c)-first,60)

    def test_poll_partition_produces_identical_receipts_and_money(self):
        s,c,e=self.sample();batched=copy.deepcopy(s)
        for now in range(2000000010,2000000601,10):wb.settle(s,now)
        wb.settle(batched,2000000600)
        self.assertEqual(s,batched)

    def test_grocery_scanned_goods_are_reserved_for_owner(self):
        s,c,e=self.sample('grocery')
        c['ext']['inv']['lots']=[dict(id='only',item='rice',qty=6,unit_cost=14,expires=99,received=1,supplier='opening')]
        c['tasks']=[dict(id='manual',career='grocery',kind='checkout',status='waiting',stage='basket',scanned={'rice':2},weighed={})]
        wb.settle(s,self.next(c))
        self.assertEqual(c['ops']['business']['served'],0)
        self.assertEqual(c['ops']['business']['reason'],'stock')

    def test_clothing_reserved_sizes_survive_staff_sale(self):
        from game.careers import clothing
        s,c,e=self.sample('clothing');clothing._sync(c)
        row=c['ext']['data']['grid']['tee']
        c['tasks']=[dict(id='manual',career='clothing',status='waiting',picks=[dict(item='tee',size=size) for size,qty in row.items() for _ in range(qty)])]
        wb.settle(s,self.next(c))
        self.assertEqual(c['ops']['business']['served'],1)
        self.assertEqual(wb.public(c)['recent'][-1]['items'],{'shirt':1})
        self.assertEqual(sum(c['ext']['data']['grid']['tee'].values()),sum(row.values()))

    def test_milk_tea_uses_prepared_base_and_actual_cup_stock(self):
        from game import boba
        for missing in ('milk','cups',None):
            with self.subTest(missing=missing):
                s,c,e=self.sample('milk_tea');b=boba.state(c)
                c['life']['pantry']=[dict(id='one',item='milk',qty=0 if missing=='milk' else 1,unit_cost=4,expires=3,received=1)]
                b['cups']['M']=0 if missing=='cups' else 1
                wb.settle(s,self.next(c)+10000)
                self.assertEqual(c['ops']['business']['served'],0 if missing else 1)
                self.assertEqual(c['ops']['business']['reason'],'stock')
                if not missing:
                    self.assertEqual(b['cups']['M'],0)
                    self.assertEqual(boba.stock(c)['milk'],0)


class StaffCatalogueTests(unittest.TestCase):
    """F#197 / F#195: staff sell across the real catalogue, in stock, and every order earns."""

    def sample(self, career, who=1):
        s = new_state(); c = s['careers'][career]; c.update(open=True, started=True)
        with patch.object(wb.time, 'time', return_value=2000000000):
            ops.action(s, c, career, 'ops_hire', {'candidate': f'{career}-staff-{who}', 'confirm': True})
            wb.settle(s)
        c['ops']['finance']['opening_balance'] += 100000 - c['money']; c['money'] = 100000
        return s, c, c['ops']['staff'][0]

    def next(self, c):
        return min(x['at'] for x in c['ops']['business']['pending'].values())

    def run_out(self, s, c):
        wb.settle(s, self.next(c) + 100000)
        return wb._recent(c)

    def test_mother_baby_sells_many_products_and_keeps_going_without_bunnies(self):
        s, c, e = self.sample('mother_baby')
        c['stock']['bunny'] = 0
        before = {k: v for k, v in c['stock'].items() if v}
        self.assertGreater(len(before), 3)
        wb.settle(s, self.next(c) + 2000)
        rows = wb._recent(c)
        self.assertGreater(c['ops']['business']['served'], 3)
        sold = {i for r in rows for i in r['items']}
        self.assertGreater(len(sold), 2)
        self.assertNotIn('bunny', sold)
        for r in rows:
            for item, qty in r['items'].items():
                self.assertLessEqual(qty, before[item])
        ops.validate(c, 'mother_baby')

    def test_every_menu_career_order_earns_against_replacement_cost(self):
        from game import staff_orders as so
        for career in sorted(so.MENUS):
            for who in (1, 4):
                with self.subTest(career=career, who=who):
                    try:
                        s, c, e = self.sample(career, who)
                    except GameError:
                        continue
                    # A raise must not turn staff orders into losses: baskets grow instead.
                    if who == 4:
                        c['ops']['staff_life']['raises'][e['id']] = 6
                        wb.refresh(c, career, 2000000001)
                    rows = self.run_out(s, c)
                    self.assertTrue(rows, career)
                    cost = so.costs(career)
                    for r in rows:
                        replacement = sum(cost[i] * q for i, q in r['items'].items())
                        self.assertGreaterEqual(r['revenue'] - r['cash_expenses'] - replacement, 1, r)
                        self.assertGreaterEqual(r['revenue'] * 100 // 84 * 84 // 100 - r['cash_expenses'] - replacement, 1, r)
                    self.assertEqual(c['ops']['business']['reason'], 'stock')
                    self.assertEqual(c['ops']['business']['recent'], [])
                    ops.validate(c, career)

    def test_ice_cream_never_sells_a_tub_at_a_scoop_price(self):
        s, c, e = self.sample('ice_cream')
        rows = self.run_out(s, c)
        tubs = [r for r in rows if set(r['items']) - {'que'}]
        self.assertTrue(tubs)
        for r in tubs:
            self.assertEqual(sum(r['items'].values()), 1)
            self.assertIn('1,2 kg', r['label'])
            self.assertGreaterEqual(r['revenue'], 50)
        self.assertGreaterEqual(wb.ORDERS['ice_cream'][1], 60)

    def test_poll_and_offline_pick_the_same_catalogue_orders(self):
        for career in ('mother_baby', 'grocery', 'com'):
            with self.subTest(career=career):
                s, c, e = self.sample(career); other = copy.deepcopy(s)
                start = self.next(c)
                step = next(iter(c['ops']['business']['pending'].values()))['seconds']
                for at in range(start, start + step * 8, step): wb.settle(s, at)
                wb.settle(other, start + step * 7)
                self.assertEqual(s, other)

    def test_receipts_stay_readable_by_the_previous_release(self):
        s, c, e = self.sample('mother_baby')
        legacy = wb._new(0)['recent']
        self.assertEqual(legacy, [])
        wb.settle(s, self.next(c))
        b = c['ops']['business']
        self.assertEqual(b['recent'], [])
        self.assertEqual(len(c['ops']['business_receipts']), 1)
        self.assertNotIn('business_clothing_receipts', c['ops'])
        # A legacy bunny receipt from the old release merges with the sidecar.
        row = dict(c['ops']['business_receipts'][0], id='staff-order-mother_baby-99', items={'bunny': 1})
        b['recent'] = [row]
        ops.validate(c, 'mother_baby')
        self.assertEqual(len(wb.public(c)['recent']), 2)
        bad = copy.deepcopy(c); bad['ops']['business_receipts'][0]['items'] = {'tee': 1}
        with self.assertRaises(GameError): ops.validate(bad, 'mother_baby')
        bad = copy.deepcopy(c); bad['ops']['business_clothing_receipts'] = []
        with self.assertRaises(GameError): ops.validate(bad, 'mother_baby')

    def test_public_explains_next_order_and_names_what_ran_out(self):
        s, c, e = self.sample('pho')
        nxt = wb.public(c)['next_order']
        self.assertTrue(nxt['label'].startswith('Đơn riêng: phở'))
        self.assertEqual(nxt['wage'], 3); self.assertEqual(nxt['materials'], 2)
        self.assertGreater(nxt['margin'], 0)
        self.assertIn('quỹ nghề', wb.public(c)['money_note'])
        for lot in c['ext']['inv']['lots']:
            if lot['item'] == 'rau': lot['qty'] = 0
        wb.settle(s, self.next(c) + 1000)
        pub = wb.public(c)
        self.assertEqual(pub['reason'], 'stock')
        self.assertIn('Đĩa rau thơm', pub['reason_text'])
        self.assertNotIn('next_order', pub)

    def test_low_prices_stop_with_a_reason_instead_of_losing(self):
        s, c, e = self.sample('grocery')
        c['ext']['inv']['lots'] = [dict(id='few', item='egg', qty=3, unit_cost=2, expires=99, received=1, supplier='opening')]
        wb.settle(s, self.next(c) + 1000)
        self.assertEqual(c['ops']['business']['served'], 0)
        self.assertIn('không đủ bù lương', wb.public(c)['reason_text'])


class MergedStockOrder(unittest.TestCase):
    """F#194: the mother & baby stock room orders several items in one supplier order."""

    def journey(self, money=5000):
        from tests.helpers import Journey
        j = Journey()
        j.c['ops']['finance']['opening_balance'] += money - j.c['money']; j.c['money'] = money
        return j

    def test_one_payment_one_van_one_row_per_line(self):
        from game.engine import public_state, validate_state, stock_vans
        j = self.journey()
        money = j.c['money']
        r = j.act('order_stock', lines=[dict(item='cat_bag', qty=2), dict(item='bunny', qty=3), dict(item='bear', qty=1)], supplier='express')
        rows = j.c['shipments'][-3:]
        self.assertEqual([(x['item'], x['qty']) for x in rows], [('cat_bag', 2), ('bunny', 3), ('bear', 1)])
        self.assertEqual(len({(x['placed'], x['lo'], x['hi'], x['at'], x['supplier']) for x in rows}), 1)
        self.assertEqual(stock_vans(j.c), 1)
        self.assertEqual(money - j.c['money'], sum(x['cost'] for x in rows))
        self.assertEqual(len([x for x in j.c['ops']['finance']['ledger'] if x['ref'] == rows[0]['id']]), 1)
        self.assertIn('gộp 3 mã', r['message'])
        validate_state(j.state)
        for _ in range(8):
            if all(x['ready_now'] for x in public_state(j.state)['careers']['mother_baby']['shipments']): break
            j.act('advance')
        for x in rows:
            j.act('receive_stock', shipment=x['id'], count=x['qty'])
        self.assertEqual(j.c['stock']['bunny'], 6 + 3)
        validate_state(j.state)

    def test_bad_lines_change_nothing(self):
        for lines in ([], [dict(item='bunny', qty=1)] * 2, [dict(item='nope', qty=1)], [dict(item='bunny', qty=7)],
                      [dict(item='bunny', qty=6), dict(item='bear', qty=0)], 'bunny', [dict(item=f'x{i}', qty=1) for i in range(13)]):
            with self.subTest(lines=lines):
                j = self.journey(); before = copy.deepcopy(j.state)
                with self.assertRaises(GameError): j.act('order_stock', lines=lines)
                self.assertEqual(j.state, before)

    def test_vans_cap_counts_merged_orders_once(self):
        from game.engine import STOCK_VANS, stock_vans
        j = self.journey(money=50000)
        from game.content import PRODUCTS
        ids = [p['id'] for p in PRODUCTS][:STOCK_VANS + 3]
        j.act('order_stock', lines=[dict(item=i, qty=1) for i in ids[:4]])
        for i in ids[4:4 + STOCK_VANS - 1]:
            j.act('order_stock', item=i, qty=1)
        self.assertEqual(stock_vans(j.c), STOCK_VANS)
        with self.assertRaises(GameError): j.act('order_stock', item=ids[-1], qty=1)

    def test_single_item_order_is_unchanged(self):
        j = self.journey()
        r = j.act('order_stock', item='cat_bag', qty=2, supplier='express')
        self.assertTrue(r['message'].startswith('Đã đặt 2 × '))
        self.assertNotIn('một chuyến', r['message'])
        self.assertEqual(j.c['shipments'][-1]['item'], 'cat_bag')


if __name__=='__main__':unittest.main()
