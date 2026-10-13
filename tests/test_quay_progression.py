"""Paid quay convenience: ownership, purchases and legacy assets."""
import copy
import unittest
from unittest.mock import patch
from game import quay, quay_business
from game.engine import validate_state
from tests.test_quay import owner, opened, act, refused, ST, Q


class PaidQuay(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(quay_business.time, 'time', return_value=1800000000)
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def buy(self, s, track, tier=0, stall=True):
        return act(s, 'jr_quay_convenience', track=track, expected_tier=tier,
                   **({'stall': ST(s)['id']} if stall else {}))

    def test_defaults_preserve_legacy_overstock(self):
        s = opened(staff=False)
        ST(s)['business']['stock'] = {'hong_tra': 700}
        before = copy.deepcopy(s)
        view = quay.public(s)
        self.assertEqual(view['slots']['limit'], 1)
        b = view['stalls'][0]['business']
        self.assertEqual((b['stock_capacity'], b['restock_batch'], b['stock_room']), (500, 5, 0))
        self.assertEqual(s, before)
        validate_state(s)
        refused(self, s, 'jr_quay_restock', stall=ST(s)['id'], items={'hong_tra': 1})

    def test_sequential_purchase_wallet_bank_and_replay(self):
        s = opened(wallet=10000, staff=False)
        s, _ = act(s, 'jr_bk_open')
        s['journey']['wallet'] = 1000
        s['journey']['bank']['balance'] = 9000
        fund = ST(s)['fund']
        s, _ = self.buy(s, 'storage')
        self.assertEqual(s['journey']['wallet'], 0)
        self.assertEqual(s['journey']['bank']['balance'], 7000)
        self.assertEqual(ST(s)['fund'], fund)
        self.assertEqual(ST(s)['business']['paid_tier'], {'storage': 1})
        refused(self, s, 'jr_quay_convenience', 'stale_tier', stall=ST(s)['id'], track='storage', expected_tier=0)
        refused(self, s, 'jr_quay_convenience', 'no_money', stall=ST(s)['id'], track='storage', expected_tier=1)
        for tier in (True, -1, 2, '1', None):
            refused(self, s, 'jr_quay_convenience', stall=ST(s)['id'], track='storage', expected_tier=tier)

    def test_independent_tracks_and_max_prices_logs(self):
        s = opened(wallet=600000000, staff=False)
        before = quay._have(s)
        for track in ('storage', 'restock', 'slots'):
            for tier in range(10):
                s, _ = self.buy(s, track, tier, stall=track != 'slots')
            refused(self, s, 'jr_quay_convenience', track=track, expected_tier=10,
                    **({'stall': ST(s)['id']} if track != 'slots' else {}))
        self.assertEqual(before - quay._have(s), 152692000 * 3)
        v = quay.public(s)
        self.assertEqual(v['slots']['limit'], 50)
        self.assertEqual(v['stalls'][0]['business']['stock_capacity'], 20000)
        self.assertEqual(v['stalls'][0]['business']['restock_batch'], 1000)
        validate_state(s)

    def test_open_slots_and_existing_many_quays(self):
        s = opened(wallet=100000, staff=False)
        refused(self, s, 'jr_quay_open', 'quay_slots', trade='milk_tea', place='xe', confirm=True)

        s, _ = self.buy(s, 'slots', stall=False)
        s, _ = act(s, 'jr_quay_open', trade='milk_tea', place='xe', confirm=True)
        self.assertEqual(len(Q(s)['stalls']), 2)
        Q(s).pop('paid_tier')
        before = copy.deepcopy(Q(s)['stalls'])
        self.assertEqual(quay.public(s)['slots']['remaining'], 0)
        self.assertEqual(quay.public(s)['slots']['over_limit'], 1)
        validate_state(s)
        self.assertEqual(Q(s)['stalls'], before)
        refused(self, s, 'jr_quay_open', 'quay_slots', trade='milk_tea', place='xe', confirm=True)

    def test_slots_can_be_bought_before_first_counter(self):
        s = owner(wallet=10000)
        s, _ = self.buy(s, 'slots', stall=False)
        self.assertEqual(quay.public(s)['slots']['remaining'], 2)
        self.assertEqual(s['journey']['wallet'], 7000)
        self.assertEqual(Q(s)['stalls'], [])

    def test_legacy_collection_above_maximum_stays_intact(self):
        s = opened(wallet=10000, staff=False)
        st = ST(s)
        Q(s)['stalls'] = [dict(copy.deepcopy(st), id=f'q{i}') for i in range(1, 52)]
        Q(s)['seq'] = 51
        validate_state(s)
        before = copy.deepcopy(s)
        view = quay.public(s)
        self.assertEqual(len(view['stalls']), 51)
        self.assertEqual(view['slots']['over_limit'], 50)
        self.assertEqual(s, before)
        Q(s)['paid_tier'] = {'slots': 10}
        refused(self, s, 'jr_quay_open', 'quay_slots', trade='milk_tea', place='xe', confirm=True)

    def test_aggregate_batch_and_reserved_capacity(self):
        s = opened(wallet=10000, staff=False)
        st = ST(s)
        st['business']['stock'] = {'hong_tra': 494}
        with patch('game.player_service_tasks.reserved', return_value=3):
            self.assertEqual(quay.public(s)['stalls'][0]['business']['stock_room'], 3)
            refused(self, s, 'jr_quay_restock', stall=st['id'], items={'hong_tra': 4})
            s, _ = act(s, 'jr_quay_restock', stall=st['id'], items={'hong_tra': 3})
        ST(s)['business']['stock'] = {}
        refused(self, s, 'jr_quay_restock', stall=st['id'], items={'hong_tra': 3, 'tra_dao': 3})
        s, _ = self.buy(s, 'restock')
        s, _ = act(s, 'jr_quay_restock', stall=st['id'], items={'hong_tra': 5, 'tra_dao': 5}, wallet=True)
        self.assertEqual(sum(ST(s)['business']['stock'].values()), 10)

    def test_unlock_and_physical_licences_still_apply(self):
        s = owner(wallet=100000, chapter=2)
        refused(self, s, 'jr_quay_convenience', track='slots', expected_tier=0)
        s = opened(wallet=100000, staff=False)
        self.assertEqual(quay.upgrade_cost(ST(s), 'sap'), 3200)
        s['journey']['certificates'] = {}
        refused(self, s, 'jr_quay_upgrade', 'business_license', stall=ST(s)['id'], place='sap', confirm=True)

    def test_top_bank_purchase_and_absolute_stock_ceiling(self):
        s = opened(wallet=10000, staff=False)
        s, _ = act(s, 'jr_bk_open')
        s['journey']['wallet'] = 0
        s['journey']['bank']['balance'] = 100000000
        ST(s)['business']['paid_tier'] = {'storage': 9, 'restock': 10}
        s, _ = self.buy(s, 'storage', 9)
        self.assertEqual(s['journey']['bank']['balance'], 0)
        self.assertEqual(s['journey']['bank']['log'][-1]['amt'], -100000000)
        ST(s)['fund'] = 1000000
        ST(s)['business']['stock'] = {'hong_tra': 19000}
        s, _ = act(s, 'jr_quay_restock', stall=ST(s)['id'], items={'hong_tra': 1000})
        refused(self, s, 'jr_quay_restock', stall=ST(s)['id'], items={'hong_tra': 1})
        validate_state(s)

    def test_invalid_saved_ownership_rejected(self):
        from game.engine import GameError, migrate_state
        s = opened(wallet=10000, staff=False)
        ST(s)['business']['paid_tier'] = {'storage': 0, 'restock': 0}
        Q(s)['paid_tier'] = {'slots': 0}
        validate_state(s)
        s, _ = self.buy(s, 'storage')
        self.assertEqual(ST(migrate_state(copy.deepcopy(s)))['business']['paid_tier'], {'storage': 1, 'restock': 0})
        for paid in ({'storage': True}, {'storage': 11}, {'slots': 1}, [], None):
            broken = copy.deepcopy(s)
            ST(broken)['business']['paid_tier'] = paid
            with self.assertRaises(GameError):
                validate_state(broken)


from tests.pg_support import pg_only


@pg_only
class PaidQuayStore(unittest.TestCase):
    def test_atomic_replay_and_stale_expected_tier_persisted(self):
        import tempfile
        from pathlib import Path
        from game.storage import Store
        from game import marriage
        from game.engine import GameError
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'paid-quay.db', story=True)
            try:
                token, _, _ = store.session()
                state = opened(wallet=10000, staff=False)
                marriage._mutate(store, {store.key(token): lambda s: (s.clear(), s.update(copy.deepcopy(state)))})
                rev = store.read(token)[1]
                payload = dict(stall='q1', track='storage', expected_tier=0)
                result = store.command(token, 'paid-quay-first', rev, None, 'jr_quay_convenience', payload)
                again = store.command(token, 'paid-quay-first', rev, None, 'jr_quay_convenience', payload)
                self.assertFalse(result['replayed'])
                self.assertTrue(again['replayed'])
                self.assertEqual(result['state'], again['state'])
                before, rev, _ = store.read(token)
                self.assertEqual(ST(before)['business']['paid_tier'], {'storage': 1})
                for request, body in [('paid-quay-stale', payload), ('paid-quay-poor', dict(payload, expected_tier=1))]:
                    with self.assertRaises(GameError):
                        store.command(token, request, rev, None, 'jr_quay_convenience', body)
                    after, after_rev, _ = store.read(token)
                    self.assertEqual((before, rev), (after, after_rev))
            finally:
                store.close_pool()

