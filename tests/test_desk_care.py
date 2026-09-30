"""The three original desk careers over several days, legacy stock on the shop clock and
AI-voiced support calls. Spec: docs/superpowers/specs/2026-09-29-desk-careers-care-ai-design.md."""
import copy
import http.client
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from game import engine as eng
from game.engine import GameError, apply_action, migrate_state, public_state, validate_state
from game.storage import Store
from server import GameServer
from tests.helpers import Journey
from tests.test_ai_chat import FakeLLM


def unchanged(test, j, action, **payload):
    before = copy.deepcopy(j.state)
    with test.assertRaises(GameError):
        j.act(action, **payload)
    test.assertEqual(j.state, before)


def next_day(j):
    j.act('end_day', carry_event=True)
    return j.act('start_day')


def care(j):
    return j.c['ext']['data']['care']


def pub(j):
    return public_state(j.state)['careers'][j.career]


class StockClockTests(unittest.TestCase):
    def test_distributor_runs_on_the_clock_never_in_beats(self):
        j = Journey('pharmacy')
        r = j.act('order_stock', item='P-02-A', qty=2)
        self.assertNotIn('nhịp', r['message'])
        self.assertIn('10:', r['message'])  # the 10:00 run (four runs a day, cut-off 09:00)
        ship = j.c['shipments'][-1]
        self.assertEqual((ship['supplier'], ship['lo'] % 1440, ship['hi'] % 1440), ('partner', 10 * 60, 10 * 60 + 30))
        view = next(x for x in pub(j)['shipments'] if x['id'] == ship['id'])
        self.assertFalse(view['ready_now'])
        self.assertNotIn('at', view)  # the real arrival stays hidden until it is due
        self.assertIsNone(view['actual'])
        self.assertTrue(view['eta_label'] and view['left_label'])
        unchanged(self, j, 'receive_stock', shipment=ship['id'], count=2)

    def test_cheaper_depot_arrives_this_afternoon_and_costs_less(self):
        j = Journey('pharmacy')
        before = j.c['money']
        j.act('order_stock', item='P-01-A', qty=4, supplier='depot')
        self.assertEqual(before - j.c['money'], 28)  # 8 × 4 × 0.85, rounded up
        ship = j.c['shipments'][-1]
        # Ordered before 13:00: the depot's afternoon run, 15:00–16:00 today.
        self.assertEqual(divmod(ship['lo'], 1440), (j.c['day'], 15 * 60))
        for _ in range(40):
            if next(x for x in pub(j)['shipments'] if x['id'] == ship['id'])['ready_now']:
                break
            j.act('advance')
        self.assertTrue(next(x for x in pub(j)['shipments'] if x['id'] == ship['id'])['ready_now'])
        j.act('receive_stock', shipment=ship['id'], count=ship['actual'])
        self.assertTrue(any(b['lot'] == 'P-01-A' and b['got'] == j.c['day'] for b in care(j)['batches']))

    def test_bad_supplier_and_other_career_rejected(self):
        j = Journey('pharmacy')
        unchanged(self, j, 'order_stock', item='P-01-A', qty=1, supplier='express')  # no courier for medicine
        unchanged(self, j, 'order_stock', item='P-01-A', qty=1, supplier=['partner'])
        k = Journey('mother_baby')
        unchanged(self, k, 'order_stock', item='socks', qty=1, supplier='depot')

    def test_old_parcels_in_beats_are_migrated(self):
        j = Journey('mother_baby')
        j.c['shipments'] = [dict(id='shipment-9', item='socks', qty=2, actual=2, ready=j.c['turn'] + 3, status='in_transit', cost=20),
                            dict(id='shipment-8', item='bear', qty=1, actual=1, ready=0, status='received', cost=48)]
        s = migrate_state(j.state)
        validate_state(s)
        new = s['careers']['mother_baby']['shipments']
        self.assertTrue(all('ready' not in x and 'at' in x for x in new))
        now = eng._now(s['careers']['mother_baby'], 'mother_baby')
        self.assertEqual(new[0]['at'] - now, 60)
        j.state = s
        for _ in range(3):
            j.act('advance')
        j.act('receive_stock', shipment='shipment-9', count=2)

    def test_helper_brings_parcels_to_the_door(self):
        j = Journey('mother_baby')
        j.c['upgrades'].append('assistant')
        j.act('order_stock', item='socks', qty=2)
        j.act('assistant_help')
        j.act('receive_stock', shipment=j.c['shipments'][-1]['id'], count=2)

    def test_parcel_arrival_is_announced_once(self):
        j = Journey('mother_baby')
        j.act('order_stock', item='socks', qty=1, supplier='express')
        notes = []
        for _ in range(6):
            notes += j.act('advance')['effects']
        self.assertEqual(sum('đã tới cửa kho' in n for n in notes), 1)

    def test_tampered_parcel_rejected(self):
        j = Journey('mother_baby')
        j.act('order_stock', item='socks', qty=1)
        for bad in (dict(supplier='depot'), dict(lo=0), dict(late=5)):
            s = copy.deepcopy(j.state)
            s['careers']['mother_baby']['shipments'][-1].update(bad)
            with self.assertRaises(GameError):
                validate_state(s)


class PharmacyCareTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey('pharmacy')

    def test_refill_call_brings_the_regular_on_time(self):
        j = self.j
        r = care(j)['regulars']['nam']
        self.assertEqual(r['due'], 3)
        unchanged(self, j, 'ph_care_call', who='nam')  # day 1: too early
        next_day(j)
        j.act('ph_care_call', who='nam')
        unchanged(self, j, 'ph_care_hand', who='nam', confirm=True)  # comes tomorrow
        next_day(j)
        money = j.c['money']
        stock = j.c['stock']['P-02-A']
        unchanged(self, j, 'ph_care_hand', who='nam')  # no confirm
        j.act('ph_care_hand', who='nam', confirm=True)
        self.assertEqual(j.c['stock']['P-02-A'], stock - 1)
        self.assertEqual(j.c['money'] - money, 35)  # on time and trust 3: a 5 xu thank-you
        r = care(j)['regulars']['nam']
        self.assertEqual((r['trust'], r['due'], r['hist'][-1][1]), (3, 8, 'ok'))
        validate_state(j.state)

    def test_forgotten_regular_comes_late_then_is_missed(self):
        j = self.j
        next_day(j)
        next_day(j)  # day 3: due, but nobody called
        unchanged(self, j, 'ph_care_hand', who='nam', confirm=True)
        next_day(j)  # day 4: they remember by themselves
        self.assertEqual(next(r for r in pub(j)['data']['care']['regulars'] if r['id'] == 'nam')['state'], 'here')
        r = next_day(j)  # never handed: missed at close
        nam = care(j)['regulars']['nam']
        self.assertEqual((nam['trust'], nam['missed'], nam['hist'][-1][1]), (1, 1, 'missed'))

    def test_expired_box_blocks_the_whole_lot_until_pulled(self):
        j = self.j
        for _ in range(3):
            next_day(j)  # day 4: the day-one near-dated boxes of P-02 are out of date
        bad = next(b for b in care(j)['batches'] if b['lot'] == 'P-02-A' and b['exp'] < j.c['day'])
        self.assertIn('P-02-A', eng.ph_shelf_block(j.c, 'P-02-A'))
        unchanged(self, j, 'ph_care_hand', who='nam', confirm=True)
        unchanged(self, j, 'ph_lot_pull', batch=next(b['id'] for b in care(j)['batches'] if b['lot'] == 'P-01-A'))  # a good box
        stock = j.c['stock']['P-02-A']
        j.act('ph_lot_pull', batch=bad['id'])
        self.assertEqual(j.c['stock']['P-02-A'], stock - bad['qty'])
        self.assertEqual(care(j)['waste'], bad['qty'] * 8)
        self.assertIsNone(eng.ph_shelf_block(j.c, 'P-02-A'))
        j.act('ph_care_hand', who='nam', confirm=True)

    def test_classic_slip_cannot_take_from_a_blocked_lot(self):
        j = Journey('pharmacy', slot=0, day=1)
        j.act('ask')
        lot = j.task['needs']['product'] + '-A'
        b = next(b for b in care(j)['batches'] if b['lot'] == lot)
        b['recalled'] = eng.RECALL_WHY[0]
        j.act('ph_inspect', lot=lot)
        unchanged(self, j, 'ph_pick', item=lot)
        money = j.c['money']
        j.act('ph_lot_pull', batch=b['id'])
        self.assertEqual(j.c['money'] - money, b['qty'] * 8)  # the distributor refunds a recall
        if j.c['stock'][lot]:
            j.act('ph_pick', item=lot)

    def test_recall_notice_on_schedule(self):
        j = self.j
        notes = []
        for _ in range(4):
            notes += next_day(j)['effects']
        self.assertEqual(j.c['day'], 5)
        self.assertTrue(any(n.startswith('📢') for n in notes))
        self.assertEqual(sum(1 for b in care(j)['batches'] if b['recalled']), 1)

    def test_fridge_log_windows_and_fixes(self):
        j = self.j
        unchanged(self, j, 'ph_fridge_log', slot='pm')  # 08:xx, afternoon reading from 14:00
        j.act('ph_fridge_log', slot='am')
        unchanged(self, j, 'ph_fridge_log', slot='am')
        unchanged(self, j, 'ph_fridge_fix', slot='am', fix='door')  # nothing to fix
        # a day with a power cut in the morning reading
        day = next(d for d in range(3, 200) if eng._fridge_reading(d, 'am')[1] == 'power')
        k = Journey('pharmacy', slot=0, day=day)
        k.act('ph_fridge_log', slot='am')
        k.act('ph_fridge_fix', slot='am', fix='door')  # wrong: the fridge is not running
        self.assertTrue(all(b['warm'] for b in care(k)['batches'] if b['lot'] == 'P-05-A'))
        self.assertIn('P-05-A', eng.ph_shelf_block(k.c, 'P-05-A'))
        k2 = Journey('pharmacy', slot=0, day=day)
        money = k2.c['money']
        k2.act('ph_fridge_log', slot='am')
        k2.act('ph_fridge_fix', slot='am', fix='move', confirm=True)
        self.assertEqual(money - k2.c['money'], 15)
        self.assertFalse(any(b['warm'] for b in care(k2)['batches']))

    def test_missed_fridge_log_feeds_the_inspection(self):
        j = self.j
        risk = j.c['ext']['data']['desk']['risk']
        r = j.act('end_day', carry_event=True)
        self.assertIn('thiếu lượt sáng', ' '.join(r['summary']['career']['lines']))  # the afternoon reading was not due yet
        self.assertGreater(j.c['ext']['data']['desk']['risk'], risk)

    def test_care_notices_reach_the_paper_desk(self):
        j = self.j
        desk = next(t for t in pub(j)['tasks'] if t.get('desk'))
        self.assertTrue(any('tủ mát' in n for n in desk['bulletin']))

    def test_tampered_lot_book_rejected(self):
        j = self.j
        for edit in (lambda c: c['batches'][0].update(lot='P-01-B'), lambda c: c['batches'][0].update(qty=0),
                     lambda c: c['regulars']['nam'].update(trust=9), lambda c: c.update(extra=1)):
            s = copy.deepcopy(j.state)
            edit(s['careers']['pharmacy']['ext']['data']['care'])
            with self.assertRaises(GameError):
                validate_state(s)


class BookkeepingCareTests(unittest.TestCase):
    def setUp(self):
        self.j = Journey('accounting')
        next_day(self.j)  # day 2: Cô Hoa brings month 1

    def book(self, cid):
        return eng._ac_book(care(self.j)['clients'][cid])

    def test_client_file_learns_habits_from_what_was_found(self):
        j = self.j
        case = eng._ac_case(eng.AC_CLIENT['hoa'], 0)
        unchanged(self, j, 'ac_book_check', client='hoa', check='cash')  # open first
        j.act('ac_book_open', client='hoa')
        for k in eng.AC_CHECKS:
            j.act('ac_book_check', client='hoa', check=k)
        known = care(j)['clients']['hoa']['known']
        self.assertEqual(set(known), {k for k in ('cash', 'personal') if case['issues'][k]})
        view = next(x for x in pub(j)['data']['care']['clients'] if x['id'] == 'hoa')
        self.assertEqual(view['book']['found'], {k: case['issues'][k] for k in eng.AC_CHECKS})

    def test_close_grades(self):
        j = self.j
        case = eng._ac_case(eng.AC_CLIENT['hoa'], 0)
        j.act('ac_book_open', client='hoa')
        if case['missing']:
            unchanged(self, j, 'ac_book_close', client='hoa', confirm=True)  # still missing receipts
        left = sum(case['issues'].values())
        money = j.c['money']
        j.act('ac_book_close', client='hoa', note='missing_note' if case['missing'] else 'full', confirm=True)
        closed = care(j)['clients']['hoa']['months'][-1]['closed']
        self.assertEqual(closed['grade'], 'rough' if left else 'good' if case['missing'] else 'perfect')
        self.assertEqual(j.c['money'] - money, closed['fee'])

    def test_missing_receipts_arrive_days_later_or_need_a_follow_up(self):
        j = self.j
        for _ in range(2):
            next_day(j)  # day 4: Bà Sáu (always sends late) brings month 1
        self.assertEqual(j.c['day'], 4)
        j.act('ac_book_open', client='sau')
        j.act('ac_book_chase', client='sau')
        b = self.book('sau')
        self.assertEqual(b['promise'], 6)
        unchanged(self, j, 'ac_book_chase', client='sau')  # too early to chase again
        next_day(j)
        next_day(j)
        self.assertFalse(self.book('sau')['source'])  # forgot, as her file will say
        j.act('ac_book_chase', client='sau')
        self.assertTrue(self.book('sau')['source'])
        self.assertIn('late', care(j)['clients']['sau']['known'])
        for k in eng.AC_CHECKS:
            j.act('ac_book_check', client='sau', check=k)
        j.act('ac_book_close', client='sau', confirm=True)
        self.assertEqual(care(j)['clients']['sau']['months'][-1]['closed']['grade'], 'perfect')

    def test_deadline_then_lost_box(self):
        j = self.j
        next_day(j)
        next_day(j)
        r = next_day(j)  # day 5: close of day 5 = due of month 1
        r = j.act('end_day', carry_event=True)
        self.assertTrue(self.book('hoa')['late'])
        self.assertTrue(any('Trễ hạn khóa sổ' in x for x in r['summary']['career']['lines']))
        j.act('start_day')
        r = j.act('end_day', carry_event=True)
        self.assertEqual(care(j)['clients']['hoa']['months'][-1]['closed']['grade'], 'lost')
        self.assertEqual(care(j)['clients']['hoa']['trust'], 0)
        validate_state(j.state)

    def test_care_actions_work_while_a_paper_case_is_active(self):
        j = self.j
        j.c['active_task'] = next(t['id'] for t in j.c['tasks'] if t.get('desk') and t['status'] == 'new')
        j.act('ac_book_open', client='hoa')

    def test_input_validation(self):
        j = self.j
        for p in (dict(client='nobody'), dict(client=['hoa']), dict()):
            unchanged(self, j, 'ac_book_open', **p)
        j.act('ac_book_open', client='hoa')
        unchanged(self, j, 'ac_book_check', client='hoa', check='late')
        unchanged(self, j, 'ac_book_close', client='hoa', note='whatever', confirm=True)
        s = copy.deepcopy(j.state)
        s['careers']['accounting']['ext']['data']['care']['clients']['hoa']['known'].append('round')
        with self.assertRaises(GameError):
            validate_state(s)


def open_case(j, tid):
    t = j.get(tid)
    j.act('cs_identity', task=tid)
    for e in t['evidence']:
        j.act('cs_evidence', task=tid, evidence=e['id'])
    j.act('cs_propose', task=tid, solution=t['solution'])


class SupportCareTests(unittest.TestCase):
    def reship(self):
        """A 'missing item' case on day 3 or later: the warehouse ships it tomorrow."""
        for d in range(3, 60):
            j = Journey('customer_care', slot=0, day=d)
            if not j.task.get('desk') and j.task['solution'] == 'reship':
                return j
        raise AssertionError('no reship case')

    def test_first_days_keep_a_short_wait(self):
        j = Journey('customer_care')
        tid = j.task['id']
        open_case(j, tid)
        r = j.act('cs_execute', task=tid)
        self.assertNotIn('nhịp', r['message'])
        j.act('advance')
        j.act('advance')
        self.assertEqual(j.get(tid)['status'], 'awaiting_confirmation')

    def test_reship_waits_for_the_warehouse_over_night(self):
        j = self.reship()
        tid = j.task['id']
        open_case(j, tid)
        j.act('cs_execute', task=tid)
        t = j.get(tid)
        self.assertEqual((t['wait'], t['ready_at'] // 1440), ('kho', j.c['day'] + 1))
        for _ in range(10):
            j.act('advance')
        self.assertEqual(j.get(tid)['status'], 'executing')
        r = next_day(j)
        self.assertTrue(any('bàn giao' in n for n in r['effects']))
        h = care(j)['handover']
        self.assertEqual([x['task'] for x in h['rows']], [tid])
        self.assertTrue(j.get(tid)['upd'])  # the result is due this afternoon: call before noon
        j.act('cs_handover_read')
        self.assertTrue(care(j)['handover']['read'])
        r = j.act('cs_call', task=tid, pick='update')
        self.assertEqual(r['kept'], 'Đã gọi cập nhật đúng hẹn trước 12:00.')
        for _ in range(20):
            j.act('advance')
        self.assertEqual(j.get(tid)['status'], 'awaiting_confirmation')
        j.act('cs_confirm', task=tid)
        j.act('cs_close', task=tid)
        card = care(j)['people'][j.get(tid)['npc']]
        self.assertIn('theo 1 ngày', card['last'][-1]['note'])
        self.assertEqual(j.get(tid)['mistakes'], 0)

    def test_missed_update_and_first_response_cost_satisfaction(self):
        j = self.reship()
        tid = j.task['id']
        open_case(j, tid)
        j.act('cs_execute', task=tid)
        next_day(j)
        notes = []
        for _ in range(14):
            notes += j.act('advance')['effects']
        self.assertTrue(j.get(tid)['upd']['late'])
        self.assertEqual(j.get(tid)['mistakes'], 1)
        self.assertTrue(any('tự gọi lên' in n for n in notes))
        k = self.reship()
        for _ in range(10):  # two hours (x PATIENCE_FACTOR 1.2 = 144 min) of shop time from the first look at the case
            k.act('advance')
        self.assertEqual(k.task['sla'], 'late')
        self.assertEqual(k.task['mistakes'], 1)

    def test_call_rules(self):
        j = Journey('customer_care')
        tid = j.task['id']
        unchanged(self, j, 'cs_call', task=tid, pick='update')  # verify the order code first
        j.act('cs_identity', task=tid)
        turn = j.c['turn']
        j.act('cs_call', task=tid, pick='ask')
        self.assertEqual(j.c['turn'], turn + 1)  # picking up the phone takes 20 minutes
        j.act('cs_call', task=tid, pick='bye')
        self.assertEqual(j.c['turn'], turn + 1)  # the rest of the call does not
        r = j.act('cs_call', task=tid, text='Bạn phiền quá, tự đi mà kiểm')
        self.assertEqual((r['intent'], j.get(tid)['mistakes']), ('rude', 1))
        r = j.act('cs_call', task=tid, text='Mình cam kết hoàn tiền ngay cho bạn')
        self.assertEqual(r['intent'], 'promise')
        self.assertEqual(j.c['money'], Journey('customer_care').c['money'])  # words never move money
        for p in (dict(pick='refund'), dict(text=''), dict(text='x' * 201), dict(pick='ask', text='hi')):
            unchanged(self, j, 'cs_call', task=tid, **p)
        for _ in range(eng.CS_CALL_MAX - 4):
            j.act('cs_call', task=tid, pick='ask')
        unchanged(self, j, 'cs_call', task=tid, pick='ask')
        self.assertLessEqual(len(j.get(tid)['call']), 20)
        validate_state(j.state)

    def test_overpromise_shows_at_close(self):
        j = Journey('customer_care')
        tid = j.task['id']
        open_case(j, tid)
        j.act('cs_call', task=tid, text='Mình đảm bảo 100% mai tới')
        j.act('cs_execute', task=tid)
        j.act('advance')
        j.act('advance')
        j.act('cs_confirm', task=tid)
        j.act('cs_close', task=tid)
        self.assertEqual(j.get(tid)['mistakes'], 1)

    def test_call_context_carries_facts_not_the_answer(self):
        j = Journey('customer_care')
        tid = j.task['id']
        j.act('cs_identity', task=tid)
        j.act('cs_call', task=tid, pick='ask')
        info = eng.cs_call_context(j.state, tid)
        self.assertEqual(info['npc'], j.task['npc'])
        self.assertNotIn('solution', json.dumps(info['context']))
        self.assertEqual([x['role'] for x in info['history']], ['user', 'npc'])
        self.assertNotIn('call', [k for k, v in public_state(j.state)['careers']['customer_care']['tasks'][0].items() if v is None])

    def test_trend_and_history_after_days(self):
        j = Journey('customer_care')
        for t in list(j.c['tasks']):
            j.solve(t['id'])
        r = j.act('end_day', carry_event=True)
        self.assertTrue(any('Mức hài lòng hôm nay' in x for x in r['summary']['career']['lines']))
        self.assertEqual(len(care(j)['trend']), 1)
        view = pub(j)['data']['care']
        self.assertTrue(view['people'])

    def test_tampered_call_rejected(self):
        j = Journey('customer_care')
        tid = j.task['id']
        j.act('cs_identity', task=tid)
        j.act('cs_call', task=tid, pick='ask')
        for edit in (lambda t: t['call'].append(dict(who='boss', text='hi')), lambda t: t.update(tone='angry'),
                     lambda t: t['call'][-1].update(mode='gpt')):
            s = copy.deepcopy(j.state)
            edit(next(t for t in s['careers']['customer_care']['tasks'] if t['id'] == tid))
            with self.assertRaises(GameError):
                validate_state(s)


class SupportCallRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.llm = ThreadingHTTPServer(('127.0.0.1', 0), FakeLLM)
        threading.Thread(target=cls.llm.serve_forever, daemon=True).start()
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / 'state.db')
        cls.server = GameServer(('127.0.0.1', 0), cls.store)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port
        cls.env = patch.dict(os.environ, {'QUIET': '1', 'LLM_BASE_URL': f'http://127.0.0.1:{cls.llm.server_port}/v1', 'LLM_MODEL': 'fake', 'LLM_API_KEY': 'k'})
        cls.env.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.llm.shutdown()
        cls.llm.server_close()
        cls.temp.cleanup()
        cls.env.stop()

    def setUp(self):
        FakeLLM.requests = []
        FakeLLM.reply = 'Ờ, vậy mình chờ thêm chút. Có tin thì gọi mình liền nha.'
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        con.request('GET', '/api/bootstrap', headers={'Host': f'127.0.0.1:{self.port}'})
        res = con.getresponse()
        self.cookie = res.getheader('Set-Cookie').split(';')[0]
        self.csrf = json.loads(res.read())['csrf']
        con.close()
        self.j = Journey('customer_care')
        self.tid = self.j.task['id']
        self.j.act('cs_identity', task=self.tid)
        self.put(self.j.state)

    def put(self, state):
        token = self.cookie.split('=', 1)[1]
        with self.store.connect() as db:
            db.execute('UPDATE sessions SET state=?, revision=revision+1 WHERE sid=?', (json.dumps(state, ensure_ascii=False), self.store.key(token)))

    def saved(self):
        return self.store.read(self.cookie.split('=', 1)[1])

    def call(self, csrf=True, **body):
        h = {'Host': f'127.0.0.1:{self.port}', 'Cookie': self.cookie, 'Content-Type': 'application/json'}
        if csrf:
            h['X-Game-CSRF'] = self.csrf
        con = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        con.request('POST', '/api/ai/support_call', body=json.dumps(dict(dict(career='customer_care', task=self.tid), **body)), headers=h)
        res = con.getresponse()
        out = res.status, json.loads(res.read() or b'{}')
        con.close()
        return out

    def line(self):
        t = next(t for t in self.saved()[0]['careers']['customer_care']['tasks'] if t['id'] == self.tid)
        return t['call'][-1], t

    def test_ai_line_stored_with_the_scripted_fact(self):
        status, data = self.call(pick='sorry')
        self.assertEqual((status, data['mode']), (200, 'ai'), data)
        last, t = self.line()
        self.assertEqual((last['mode'], last['text']), ('ai', FakeLLM.reply))
        self.assertTrue(last['canonical'])
        validate_state(self.saved()[0])
        body = FakeLLM.requests[-1]['messages']
        self.assertIn('tổng đài', body[0]['content'])  # purpose=support_call
        facts = json.loads(body[1]['content'])
        self.assertEqual(facts['task']['case'], t['title'])
        self.assertNotIn('solution', json.dumps(facts['task']))
        self.assertEqual(self.saved()[0]['careers']['customer_care']['money'], self.j.c['money'])

    def test_typed_text_and_guards(self):
        FakeLLM.reply = 'Được rồi, bên bạn hoàn cho mình 999 xu nhé.'
        status, data = self.call(text='Bạn chờ thêm chút nhé, mình đang kiểm')
        self.assertEqual((status, data['mode'], data['reason']), (200, 'scripted', 'new_numeric_claim'))
        self.assertEqual(self.line()[0]['mode'], 'scripted')
        status, data = self.call(text='chém nó đi')
        self.assertEqual((status, data['mode']), (200, 'guard'))
        self.assertEqual(self.call(text='a' * 201)[0], 400)
        self.assertEqual(self.call(pick='refund')[0], 400)
        self.assertEqual(self.call(csrf=False, pick='ask')[0], 403)
        self.assertEqual(self.call(career='restaurant', pick='ask')[0], 400)

    def test_no_consent_and_budget_fall_back_to_the_script(self):
        self.j.act('settings', aiConsent=False)
        self.put(self.j.state)
        status, data = self.call(pick='ask')
        self.assertEqual((data['mode'], data['reason']), ('scripted', 'no_consent'))
        self.assertEqual(FakeLLM.requests, [])
        self.j.act('settings', aiConsent=True)
        self.put(self.j.state)
        with patch.dict(os.environ, {'AI_CHAT_PER_MINUTE': '1'}):
            modes = [self.call(pick='ask')[1] for _ in range(2)]
        self.assertEqual([m['mode'] for m in modes], ['ai', 'scripted'])
        self.assertEqual(modes[1]['reason'], 'rate_limit')

    def test_revision_conflict(self):
        _, rev, _ = self.saved()
        status, data = self.call(pick='ask', expected_revision=rev - 1, request_id='call-conflict-1')
        self.assertEqual(status, 409)
        self.assertIn('state', data)


if __name__ == '__main__':
    unittest.main()
