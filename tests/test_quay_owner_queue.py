"""Owner arrivals are bounded work, never automatic sales or polling rewards."""
import copy
import json
import unittest
from unittest.mock import patch

from game import quay_business as qb, quay_self as qs
from game.engine import GameError, migrate_state, validate_state
from tests.test_quay import opened, ST, act


class OwnerQueue(unittest.TestCase):
    def shop(self, staff=False, expensive=False):
        with patch.object(qb.time, 'time', return_value=2000000000):
            s = opened(staff=staff)
            st = ST(s)
            if expensive:
                st['menu'] = dict(on=['hong_tra'], p={'hong_tra':1000000})
            for dish in qs.menu(st)['on']:
                st['business']['stock'][dish] = 100
            s, _ = act(s, 'jr_quay_start', stall=st['id'])
        return s, ST(s)

    def test_customers_arrive_while_owner_prepares_without_selling(self):
        s, st = self.shop()
        before = copy.deepcopy(st['run']['current'])
        stock = dict(st['business']['stock'])
        qb.settle(s, now=2000000015)
        view = qs.run_view(s, st)
        self.assertGreaterEqual(len(view['crowd']), 5)
        self.assertEqual(st['run']['current'], before)
        self.assertEqual(st['business']['stock'], stock)
        self.assertEqual(st['business']['sold'], 0)
        self.assertEqual(st['business']['revenue'], 0)
        self.assertEqual(st['business']['profit_boost']['total'], 0)

    def test_waiters_take_over_immediately_and_each_sale_consumes_once(self):
        s, st = self.shop()
        qb.settle(s, now=2000000030)
        before = sum(st['business']['stock'].values())
        for _ in range(4):
            c = qs.run_view(s, st)['cust']
            with patch.object(qb.time, 'time', return_value=2000000030):
                s, _ = act(s, 'jr_quay_serve', stall=st['id'], items=c['items'], change=c['pay']-c['total'], smile=True)
            st = ST(s)
            self.assertIsNotNone(qs.run_view(s, st).get('cust'))
        self.assertEqual(st['business']['sold'], 4)
        self.assertEqual(before-sum(st['business']['stock'].values()), 4)

    def test_long_offline_queue_is_bounded_and_polling_invariant(self):
        for staff in (False, True):
            with self.subTest(staff=staff):
                s, st = self.shop(staff=staff)
                offline = copy.deepcopy(s)
                for at in range(2000000001, 2000000181):
                    qb.settle(s, now=at)
                qb.settle(offline, now=2000000180)
                self.assertEqual(s, offline)
                qb.settle(s, now=2100000000)
                self.assertLessEqual(len(ST(s)['run']['crowd']['waiting']), 7)
                self.assertLessEqual(len(qs.run_view(s, ST(s))['crowd']), 8)
                validate_state(s)

    def test_fussy_customers_speak_once_per_mood_and_relaxed_stay_calm(self):
        s, st = self.shop()
        qb.settle(s, now=2000000030)
        qb.settle(s, now=2000000120)
        view = qs.run_view(s, st)
        fussy = [r for r in view['crowd'] if r['temperament']=='fussy']
        calm = [r for r in view['crowd'] if r['temperament']=='relaxed']
        self.assertTrue(fussy)
        self.assertTrue(calm)
        self.assertTrue(all(r['mood']=='angry' and r['speech'] for r in fussy))
        self.assertTrue(all(r['mood']=='calm' for r in calm))
        self.assertLessEqual(len(view['voices']), 3)
        snapshot = copy.deepcopy(s)
        self.assertEqual(qs.run_view(s, st), view)
        self.assertEqual(s, snapshot, 'Rendering speech never appends history or changes the save')

    def test_extreme_price_does_not_get_a_free_queue(self):
        s, st = self.shop(expensive=True)
        qb.settle(s, now=2000003600)
        self.assertEqual(qs.run_view(s, st)['crowd'], [])
        self.assertNotIn('cust', qs.run_view(s, st))
        self.assertEqual(st['business']['sold'], 0)

    def test_old_active_customer_and_new_queue_survive_save_restore(self):
        s, st = self.shop()
        run = st['run']
        run.pop('crowd', None)
        for key in ('ticket','arrival_at','temperament','patience'):
            run['current'].pop(key, None)
        before = copy.deepcopy(run['current'])
        validate_state(s)
        qb.settle(s, now=2000000010)
        self.assertEqual({k:run['current'][k] for k in before}, before)
        saved = copy.deepcopy(s)
        restored = migrate_state(json.loads(json.dumps(s)))
        validate_state(restored)
        self.assertEqual(ST(restored)['run'], ST(saved)['run'])
        ST(restored)['run']['crowd']['waiting'] *= 10
        with self.assertRaises(GameError):
            validate_state(restored)

    def test_leaving_never_sells_queue_and_staff_can_continue(self):
        s, st = self.shop(staff=True)
        qb.settle(s, now=2000000020)
        with patch.object(qb.time, 'time', return_value=2000000020):
            s, _ = act(s, 'jr_quay_close', stall=st['id'])
        st = ST(s)
        sold = st['business']['sold']
        qb.settle(s, now=2000000320)
        self.assertGreater(st['business']['sold'], sold)
