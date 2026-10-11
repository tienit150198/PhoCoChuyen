"""Legacy workplace incident paths must honor the shared monetary-loss policy."""
import copy
import subprocess
import types
import unittest
from unittest.mock import patch

from game import abandon, boba, desk, happenings, incidents, operations, quay_business, shop_events
from game.careers import kit, tra_da
from game.engine import apply_action, validate_state
from tests.helpers import Journey
from tests.test_abandon import story, open_place, start_first
from tests.test_incidents import set_money
from tests.test_quay_business import fixture
from tests import test_shop_events as shop_fixtures


def cap(cash, fine=False):
    return min(cash * (2 if fine else 1) // 100, 2000 if fine else 1000, max(0, cash-100))


class RemainingLosses(unittest.TestCase):
    def test_shop_bounded_fine_survives_validation_and_old_receipt_remains_valid(self):
        s, st = shop_fixtures.ShopEvents().spawn('traffic_inspection', True)
        st.update(fund=0, till=200)
        eid = st['shop_events']['pending']['id']
        shop_events.choose_quay(s, st, dict(event=eid, choice='fine', confirm=True))
        self.assertEqual(st['shop_fine_receipts'][-1]['cost'], 4)
        self.assertEqual(shop_events.public(st, True)['recent'][-1]['cost'], 4)
        shop_events.validate(st, st['id'], st['trade'], st['place'])
        old = types.ModuleType('game._old_shop_events')
        old.__package__ = 'game'
        source = subprocess.check_output(['git', 'show', '70a8a43d:game/shop_events.py']).decode('utf-8')
        exec(compile(source, '2.0.2/shop_events.py', 'exec'), old.__dict__)
        old.validate(st, st['id'], st['trade'], st['place'])
        historic = st.pop('shop_fine_receipts')[-1]
        historic['cost'] = 15
        st['shop_events']['recent'].append(historic)
        st['shop_events']['spent'] += 11
        shop_events.validate(st, st['id'], st['trade'], st['place'])
        old.validate(st, st['id'], st['trade'], st['place'])

    def test_operation_cash_theft_preserves_small_balances(self):
        for cash in (0, 1, 99, 100, 101, 1000, 1000000):
            j = Journey('milk_tea')
            j.c['stock'] = {}
            set_money(j.c, cash)
            wallet = j.state['journey']['wallet']
            row = operations.spawn_case(j.state, j.c, 'milk_tea', 'theft')
            self.assertEqual(row['loss']['cash'], min(18, cap(cash)))
            self.assertEqual(j.c['money'], cash-row['loss']['cash'])
            self.assertEqual(j.state['journey']['wallet'], wallet)

    def test_happening_theft_keeps_each_pocket_local(self):
        for career in ('milk_tea', 'teacher'):
            j = Journey(career)
            set_money(j.c, 101)
            j.state['journey']['wallet'] = 101
            live = dict(id='safe-theft', facts=dict(stock=[], cash=10000, wallet=10000, damage=0, comp=0))
            _, lines = happenings._apply(j.state, j.c, career, dict(kind='trom', label='Theft'), live, 100)
            self.assertEqual(j.c['money'], 100)
            self.assertEqual(j.state['journey']['wallet'], 100)
            self.assertEqual(sum(-x['amount'] for x in lines if x['where'] == 'wallet'), 1)

    def test_abandon_fine_uses_only_its_published_pocket(self):
        for career in ('grocery', 'teacher'):
            s = open_place(story(), career)
            start_first(s, career)
            c = s['careers'][career]
            set_money(c, 101)
            s['journey']['wallet'] = 101
            preview = abandon.assess(s, career)
            self.assertEqual(preview['fine'], 1)
            s, result = apply_action(s, 'milk_tea', 'select_career', {'confirm': True})
            paid = result['abandon']
            self.assertEqual(paid['fine'], 1)
            self.assertEqual((s['careers'][career]['money'], s['journey']['wallet']),
                             (101, 100) if preview['pocket'] == 'wallet' else (100, 101))
            validate_state(s)

    def test_new_quay_fine_has_no_deferred_balance(self):
        for cash in (0, 1, 99, 100, 101, 1000, 1000000):
            s, st = fixture(staff=False)
            quay_business.initialize(s, st, now=1000)
            st.update(fund=0, till=cash)
            paid = quay_business.assess_fine(st, 10**6)
            self.assertEqual(paid, cap(cash, True))
            self.assertEqual(st['business']['unpaid_fines'], 0)
            self.assertEqual(st['till'], cash-paid)
            self.assertEqual(st['business']['expenses']['loss'], paid)

    def test_legacy_quay_liability_is_forgiven_once_without_erasing_other_costs(self):
        s, st = fixture(staff=False)
        quay_business.initialize(s, st, now=1000)
        st.update(fund=0, till=101)
        b = st['business']
        b['unpaid_fines'] = 5000
        b['profit_boost']['costs'] = 5057
        b['income_tax']['loss'] = 5071
        b['expenses']['loss'] = 23
        expenses = copy.deepcopy(b['expenses'])
        self.assertEqual(quay_business.collect_fines(st), 0)
        self.assertEqual((st['till'], b['unpaid_fines'], b['profit_boost']['costs'], b['income_tax']['loss']), (101, 0, 57, 71))
        self.assertEqual(b['expenses'], expenses)
        st['till'] = 10000
        snapshot = copy.deepcopy(st)
        self.assertEqual(quay_business.collect_fines(st), 0)
        self.assertEqual(st, snapshot)

    def test_legacy_liability_migration_is_due_and_persisted_even_without_cash_or_time(self):
        s, st = fixture(staff=False)
        quay_business.initialize(s, st, now=1000)
        quay_business.settle(s, now=1000)
        st.update(fund=0, till=0)
        st['business'].update(unpaid_fines=12, paused=True)
        self.assertTrue(quay_business.due(s, now=1000))
        self.assertTrue(quay_business.settle(s, now=1000))
        self.assertEqual(st['business']['unpaid_fines'], 0)
        self.assertFalse(quay_business.settle(s, now=1000))

    def test_legacy_shift_does_not_collect_a_paid_fine_twice_or_an_old_unpaid_fine(self):
        from game import quay_self, traffic
        from tests.test_quay import opened, ST, act
        original = opened('xe', staff=False)
        original, _ = act(original, 'jr_quay_start', stall=ST(original)['id'])
        ST(original)['run'].pop('continuous')
        ST(original)['run'].update(m=0, sk=0, u=0, rv=0, co=0)
        for legacy_unpaid in (False, True):
            with self.subTest(legacy_unpaid=legacy_unpaid):
                control, charged = copy.deepcopy(original), copy.deepcopy(original)
                st = ST(charged)
                st['run']['m'] = -12 if legacy_unpaid else -1
                t = traffic.fresh()
                with patch.object(kit, 'clock', return_value=1001):
                    ch = traffic.issue(t, 'old-road', 0, 'y')
                    traffic.cross(t, ch['token'])
                ride = dict(picks=['S'], traffic=t)
                if not legacy_unpaid:
                    st['run']['traffic_paid'] = {ch['token']: 1}
                    st['run']['fine_paid'] = 1
                st['run']['rides'] = {'0': ride}
                quay_self.close(control, ST(control), control['journey']['life_day'])
                quay_self.close(charged, st, charged['journey']['life_day'])
                self.assertEqual(st['fund'] + st['till'], ST(control)['fund'] + ST(control)['till'])
                self.assertEqual(st['run']['sum']['net'], ST(control)['run']['sum']['net']-(0 if legacy_unpaid else 1))

    def test_delivery_red_receipt_records_actual_loss_and_never_invoices_rest(self):
        for cash in (1, 100, 101, 1000):
            j = Journey('delivery')
            set_money(j.c, cash)
            with patch.object(kit, 'clock', return_value=1000):
                r = j.act('dl_signal', target='gas', i=3, j=2, axis='y')
            token = r['traffic']['challenge']['token']
            with patch.object(kit, 'clock', return_value=1055):
                result = j.act('dl_cross', target='gas', token=token)
                replay = j.act('dl_cross', target='gas', token=token)
            paid = min(12, cap(cash, True))
            self.assertEqual(j.c['money'], cash-paid)
            self.assertEqual(result['receipt']['paid'], paid)
            self.assertEqual(replay['receipt']['paid'], paid)
            self.assertEqual(result['receipt']['fine'], 12)  # old receipt schema is retained
            self.assertFalse(any(b['source'] == token for b in j.c['ops']['finance']['bills']))
            validate_state(j.state)

    def test_legacy_fine_bill_closes_once_for_actual_small_payment(self):
        j = Journey('delivery')
        set_money(j.c, 101)
        operations.bill(j.c, 'traffic-old', 'fine', 'Vượt đèn đỏ', 12, j.c['day']+1, 'legacy')
        before = copy.deepcopy(j.c)
        preview = operations.public_operations(j.c, 'delivery')['finance']
        self.assertEqual(preview['bills'][0]['payable'], 1)
        self.assertEqual(preview['unpaid_total'], 1)
        self.assertEqual(j.c, before)
        j.act('ops_pay_bill', bill='traffic-old', confirm=True)
        bill = next(x for x in j.c['ops']['finance']['bills'] if x['id'] == 'traffic-old')
        self.assertEqual((j.c['money'], bill['status'], bill['paid_amount']), (100, 'paid', 1))
        validate_state(j.state)

    def test_grocery_pending_quote_uses_current_bounded_payment(self):
        from game.careers import grocery
        j = Journey('grocery')
        set_money(j.c, 101)
        d = j.c['ext']['data']
        d['fine'] = dict(amount=10000, lines=['Vi phạm cũ'], lots=[])
        grocery._open_fine(j.state, j.c, d)
        ev = grocery.public_data(j.c)['desk']['ev']
        self.assertIn('1 xu', ev['text'])
        self.assertEqual([o['cost'] for o in ev['options'] if o['id'] in ('pay','half')], [1, 1])

    def test_authored_desk_fines_and_scam_are_capped_once_with_actual_receipts(self):
        from game.careers import grocery, delivery
        for module, script, choice, fine in ((grocery,'GE-INSPECT','bribe',True), (grocery,'GE-REINSPECT','hide',True),
                (delivery,'DE-POLICE','dodge',True), (delivery,'DE-SCAM','pay',False), (delivery,'DE-BUMP','flee',True)):
            with self.subTest(script=script):
                j = Journey(module.ID)
                set_money(j.c, 101)
                d = j.c['ext']['data']['desk']
                d['ev'] = dict(id='probe-fine', script=script, day=j.c['day'], at='between')
                with patch.object(kit, 'rng') as rng:
                    rng.return_value.random.return_value = 1
                    result = kit.desk_choose(j.state, j.c, module.ID, d, module.EVENTS, choice)
                self.assertEqual(j.c['money'], 100)
                self.assertIn('1 xu', result['message'])
                self.assertEqual(d['last'].get('paid'), 1)
                validate_state(j.state)

    def test_authored_situation_fines_quote_and_charge_actual_amount(self):
        from game import situations
        for career, script, choice in (('grocery','GR-S01','sell'), ('delivery','DL-S06','against')):
            j = Journey(career)
            set_money(j.c, 101)
            j.c['ext']['situation'] = dict(id='probe-fine', script=script, day=j.c['day'], practice=False, stage='proposed', choice=choice, read=[])
            option = next(o for o in situations.public(j.c, career)['options'] if o['id']==choice)
            self.assertEqual(option['cost'], 1)
            result = j.act('sit_confirm', confirm=True)
            self.assertEqual(j.c['money'], 100)
            self.assertIn('1 xu', result['message'])
            self.assertIn('1 xu', situations.public(j.c, career)['outcome'])
            validate_state(j.state)

    def test_office_fine_preserves_reserve_and_books_actual_amount(self):
        from game.careers import office
        for cash in (0, 1, 99, 100, 101, 1000, 1000000):
            j = Journey('corp_accounting')
            set_money(j.c, cash)
            o = office.initial()
            paid = office.fine(j.state, j.c, o, 10**6, 'Trừ thưởng')
            self.assertEqual((paid, o['fines'], o['day_fines']), (cap(cash, True),)*3)
            self.assertEqual(j.c['money'], cash-paid)

    def test_tea_sweep_small_balance_survives(self):
        j = Journey('tra_da')
        set_money(j.c, 101)
        d = j.c['ext']['data']
        d['sweep'] = dict(stage='coming', stools=4, packed_stools=0, umbrella=True, folded=False)
        d['stall']['spot'] = 'le_duong'
        tra_da._sweep_resolve(j.state, j.c, d)
        self.assertEqual(j.c['money'], 100)
        self.assertEqual(d['sweep']['result']['fine'], 1)

    def test_incident_ticket_and_paid_result_show_actual_amount(self):
        from tests.test_incidents import open_day, fire, choose
        for script, option in (('noise_fine', 'pay'), ('racket_again', 'pay')):
            s = open_day('milk_tea')
            c = s['careers']['milk_tea']
            set_money(c, 1000)
            row = fire(s, 'milk_tea', script)
            if script == 'racket_again':row.update(wealth=10**8, percent=20)
            view = incidents.public(c, 'milk_tea', s)['active']
            if view['ticket']:self.assertEqual(view['ticket']['amount'], 20)
            s, _ = choose(s, 'milk_tea', option)
            view = incidents.public(s['careers']['milk_tea'], 'milk_tea', s)
            if script == 'racket_again':
                self.assertEqual(view['last']['label'], 'Trả 10 xu')
                self.assertEqual(view['log'][0]['label'], 'Trả 10 xu')
            validate_state(s)

    def test_incident_branch_preview_shares_the_event_cap(self):
        from tests.test_incidents import open_day, fire
        s = open_day('milk_tea')
        c = s['careers']['milk_tea']
        set_money(c, 5000)
        row = fire(s, 'milk_tea', 'food_hygiene')
        option = next(o for o in incidents._priced_spec(row, s, c)['options'] if o['id']=='envelope')
        quoted = incidents._lines(option, option['luck']['lose'])
        self.assertEqual(-sum(a for _, a, _ in quoted), 100)
        with patch.object(incidents, '_luck', return_value=False):
            incidents.decide(s, c, 'milk_tea', 'envelope')
        self.assertEqual(c['money'], 4900)
        validate_state(s)

    def test_incident_result_and_history_outcome_use_saved_actual_loss(self):
        from tests.test_incidents import open_day, fire, choose
        s = open_day('milk_tea')
        set_money(s['careers']['milk_tea'], 101)
        fire(s, 'milk_tea', 'fake_transfer')
        s, _ = choose(s, 'milk_tea', 'trust')
        c = s['careers']['milk_tea']
        self.assertEqual(c['money'], 100)
        view = incidents.public(c, 'milk_tea', s)
        self.assertIn('1 xu', view['last']['outcome'])
        self.assertIn('1 xu', view['log'][0]['outcome'])
        self.assertNotIn('60 xu', str(view['last']))

    def test_incident_fine_rechecks_cash_after_an_ordinary_repair(self):
        from tests.test_incidents import open_day, fire
        s = open_day('restaurant')
        c = s['careers']['restaurant']
        set_money(c, 0)
        s['journey']['wallet'] = 101
        row = fire(s, 'restaurant', 'drunk_bill')
        with patch.object(incidents, '_luck', return_value=False):
            incidents.decide(s, c, 'restaurant', 'fight')
        self.assertEqual(s['journey']['wallet'], 41)
        self.assertFalse(any(line['cat']=='fine' for line in c['incidents']['last']['lines']))

    def test_other_workplace_fine_handlers_preserve_reserve(self):
        from game.careers import cafe_bakery, grocery, homestay, pet_care, salon
        for career in ('cafe_bakery', 'homestay', 'grocery', 'milk_tea', 'pharmacy', 'pet_care', 'salon'):
            with self.subTest(career=career):
                j = Journey(career)
                set_money(j.c, 101)
                if career == 'cafe_bakery':
                    j.c['ext']['data']['clean_day'] = 0
                    cafe_bakery._ev_inspection(j.state, j.c, {'rules': {}}, 'show')
                elif career == 'homestay':
                    j.c['ext']['data']['safety_day'] = 0
                    homestay._desk_hook(j.state, j.c, 'inspect', None)
                elif career == 'grocery':
                    j.c['ext']['data']['fine'] = dict(amount=10000, lines=[], lots=[])
                    message = grocery._fine(j.state, j.c, 'pay', {})
                    self.assertIn('1 xu', message)
                elif career == 'milk_tea':
                    b = boba.state(j.c)
                    b['mess'] = boba.UNSAFE_MESS
                    boba._resolve(j.state, j.c, b, dict(kind='inspection', facts={}, id='safe-fine'), 'open')
                elif career in ('pet_care', 'salon'):
                    j.c['ext']['data']['sanitize_day'] = 0
                    (pet_care if career=='pet_care' else salon)._desk_hook(j.state, j.c, 'inspect', None)
                else:
                    d = desk.data(j.c)
                    d['risk'] = 10
                    from game import desk_content
                    j.c['day'] = desk_content.INSPECT_EVERY[career]
                    desk.on_close(j.state, j.c, career)
                self.assertEqual(j.c['money'], 100)

    def test_counter_traffic_receipt_and_shift_use_actual_payment(self):
        from tests.test_quay import opened, ST, act
        s = opened('xe', staff=False)
        sid = ST(s)['id']
        s, _ = act(s, 'jr_quay_online', stall=sid, on=True)
        s, _ = act(s, 'jr_quay_start', stall=sid)
        ST(s).update(fund=101, till=0)
        run = ST(s)['run']; before_m = run['m']
        at = run['order_data']['0']['available_at']/1000
        with patch('game.quay_business.time.time', return_value=at), patch.object(kit, 'clock', return_value=1000):
            s, r = act(s, 'jr_quay_signal', stall=sid, order=0)
        ch = r['traffic']['challenge']
        with patch('game.quay_business.time.time', return_value=at), patch.object(kit, 'clock', return_value=1120+10-ch['offset']):
            s, result = act(s, 'jr_quay_cross', stall=sid, order=0, turn='S', token=ch['token'])
            s, replay = act(s, 'jr_quay_cross', stall=sid, order=0, turn='S', token=ch['token'])
        self.assertEqual(result['receipt']['paid'], 1)
        self.assertEqual(replay['receipt']['paid'], 1)
        self.assertEqual(ST(s)['run']['m'], before_m-1)
        self.assertEqual(ST(s)['business']['unpaid_fines'], 0)
        self.assertEqual(set(ST(s)['run']['rides']['0']), {'picks', 'traffic'})
        validate_state(s)
        # A 2.0.2 worker removes the ride after delivery but retains unknown run metadata.
        ST(s)['run']['rides'].pop('0')
        validate_state(s)


if __name__ == '__main__':
    unittest.main()
