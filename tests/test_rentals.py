"""Atomic player rental leases, residence, NPC demand and legacy market prices."""
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from game import accounts, housing as hs, rentals, marriage as mr, deco
from game.engine import GameError, validate_state
from game.storage import Store


class Rentals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'rentals.db', story=True)
        self.addCleanup(self.store.close_pool)
        patcher = patch('game.accounts.hash_password', lambda pw: 'scrypt$test$' + pw)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.seq = 0

    def user(self, name, wallet=100000):
        token, _, _ = self.store.session()
        token = accounts.register(self.store, token, dict(username=name + '_rent', password='matkhau-dai-lam',
            confirm='matkhau-dai-lam', display=name.title()))['token']
        def fill(s):
            s['journey']['wallet'] = wallet
            s['journey']['stats']['max_wallet'] = wallet
        mr._mutate(self.store, {self.store.key(token): fill})
        return token

    def state(self, tok):
        return self.store.read(tok)[0]

    def cmd(self, tok, action, **data):
        self.seq += 1
        return self.store.command(tok, f'rent-cmd-{self.seq:08d}', self.store.read(tok)[1], None, action, data)

    def act(self, tok, action, **data):
        self.seq += 1
        data.setdefault('rid', f'rent-api-{self.seq:08d}')
        return rentals.act(self.store, tok, action, data)

    def prop(self, owner):
        kind = next(k for k in hs.OWN if hs.HOMES[k]['price'] < 10000)
        self.cmd(owner, 'jr_home_buy', kind=kind, down=hs.HOMES[kind]['price'], months=12, confirm=True, move_in=False)
        return self.state(owner)['journey']['home']['props'][0]

    def listing(self, owner, rent=100):
        prop = self.prop(owner)
        out = self.act(owner, 'listing', property=prop['id'], rent=rent)
        return out['id'], prop

    def total(self, tok):
        state = self.state(tok)
        return state['journey']['wallet'] + (state['journey'].get('bank') or {}).get('balance', 0)

    def test_lease_payment_residence_retry_and_renew_once(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, prop = self.listing(owner, 100)
        start_owner, start_tenant = self.total(owner), self.total(tenant)
        self.act(tenant, 'accept', id=lid, rid='accept-idempotent')
        self.assertTrue(self.act(tenant, 'accept', id=lid, rid='accept-idempotent')['replayed'])
        self.assertEqual(self.total(owner), start_owner + 100)
        self.assertEqual(self.total(tenant), start_tenant - 100)
        state = self.state(tenant)
        self.assertEqual(deco.place(state['journey'])['where'], 'lease')
        self.assertTrue(deco.rooms_of(deco.place(state['journey'])['key']))
        self.assertEqual(hs.public(state)['place']['where_id'], 'lease')
        self.assertEqual(hs.living(state['journey'], 20)['rent'], hs.HOMES[prop['kind']]['upkeep'])
        before = state['journey']['rental']['end_day']
        self.act(tenant, 'renew', id=lid, rid='renew-idempotent')
        self.act(tenant, 'renew', id=lid, rid='renew-idempotent')
        self.assertEqual(self.total(owner), start_owner + 200)
        self.assertEqual(self.state(tenant)['journey']['rental']['end_day'], before + 5)
        self.act(tenant, 'leave', id=lid)
        self.assertIsNone(rentals.get(self.store, tenant)['tenancy'])
        self.assertNotIn('rental', self.state(tenant)['journey'])
        validate_state(self.state(tenant)); mr.validate_save(self.state(owner))

    def test_two_accepts_only_one_tenant_and_payment(self):
        owner, a, b = self.user('owner'), self.user('anna'), self.user('bella')
        lid, _ = self.listing(owner, 90)
        before = self.total(owner)
        gate = threading.Barrier(2)
        def accept(tok, rid):
            gate.wait()
            try:
                rentals.act(self.store, tok, 'accept', dict(id=lid, rid=rid))
                return True
            except rentals.RentalError as exc:
                self.assertEqual(exc.code, 'not_available')
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(accept, a, 'race-accept-one')
            second = pool.submit(accept, b, 'race-accept-two')
            self.assertEqual(sum((first.result(), second.result())), 1)
        self.assertEqual(self.total(owner), before + 90)

    def test_poor_tenant_rollback_and_landlord_cannot_evict_sell_move(self):
        owner, poor, tenant = self.user('owner'), self.user('poor', 1), self.user('tenant')
        lid, prop = self.listing(owner)
        before = self.total(owner)
        with self.assertRaises(rentals.RentalError):
            self.act(poor, 'accept', id=lid)
        self.assertEqual(self.total(owner), before)
        self.assertEqual(rentals.get(self.store, poor)['market'][0]['status'], 'listing')
        self.act(tenant, 'accept', id=lid)
        with self.assertRaises(rentals.RentalError):
            self.act(owner, 'cancel', id=lid)
        for action, fields in [('jr_home_move', {}), ('jr_home_let', {'on': True}),
                               ('jr_home_sell', {'value': hs.value_of(prop, self.state(owner)['journey']['life_day'])})]:
            with self.assertRaises(GameError):
                self.cmd(owner, action, id=prop['id'], confirm=True, **fields)
        self.assertIsNotNone(hs.find(hs.get(self.state(owner)), prop['id']))

    def test_expiry_uses_tenant_day_and_no_additional_charge(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, prop = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        end = self.state(tenant)['journey']['rental']['end_day']
        before = self.total(owner)
        def advance(s):
            s['journey']['life_day'] = end
            hs.on_life_day(s)
            deco.on_life_day(s)
        mr._mutate(self.store, {self.store.key(tenant): advance})
        self.cmd(tenant, 'settings', sound=False)
        self.assertIsNone(rentals.get(self.store, tenant)['tenancy'])
        self.assertNotIn('rental', self.state(tenant)['journey'])
        self.assertEqual(self.total(owner), before)
        self.cmd(owner, 'jr_home_move', id=prop['id'], confirm=True)

    def test_reset_import_and_missing_contract_cannot_bypass(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        for tok in (owner, tenant):
            with self.assertRaises(GameError):
                self.cmd(tok, 'reset_all', confirm=True)
            state = self.state(tok)
            with self.assertRaises(GameError):
                self.cmd(tok, 'import_save', save={'format': 'mot-ngay-lam-nghe/save-v4', 'state': state})

    def test_npc_ad_waits_and_price_demand_is_monotonic(self):
        owner = self.user('owner')
        prop = self.prop(owner)
        reference = hs.rent_of(prop['kind'])
        self.cmd(owner, 'jr_home_let', id=prop['id'], on=True, rent=reference * 3, confirm=True)
        state = self.state(owner)
        self.assertIsNone(hs.find(hs.get(state), prop['id'])['let'])
        self.assertEqual(state['journey']['rental_ads'][prop['id']]['rent'], reference * 3)
        self.assertEqual([hs.demand(n, 100) for n in [50, 100, 150, 200, 300, 1000]], [62, 50, 37, 25, 0, 0])
        for day in range(2, 12):
            state['journey']['life_day'] = day
            hs.on_life_day(state)
        self.assertIsNone(hs.find(hs.get(state), prop['id'])['let'])
        self.cmd(owner, 'jr_home_let', id=prop['id'], on=False, confirm=True)
        self.assertFalse(self.state(owner)['journey']['rental_ads'][prop['id']]['active'])

    def test_deletion_preflight_is_non_destructive_and_names_are_anonymized(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        with self.assertRaises(GameError):
            rentals.prepare_delete(self.store, owner)
        self.assertIsNotNone(self.state(owner))
        with self.store.connect() as db:
            self.assertFalse(db.execute('SELECT 1 FROM rental_closed_accounts WHERE sid=?', (self.store.key(owner),)).fetchone())
        self.act(tenant, 'leave', id=lid)
        self.store.delete(tenant)
        self.assertEqual(rentals.get(self.store, owner)['mine'][0]['tenant_name'], 'Người chơi đã xóa')

    def test_closed_account_cannot_accept_and_shared_mutation_cannot_remove_asset(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, prop = self.listing(owner)
        rentals.prepare_delete(self.store, tenant)
        with self.assertRaises(rentals.RentalError) as ex:
            self.act(tenant, 'accept', id=lid)
        self.assertEqual(ex.exception.code, 'account_closed')
        other = self.user('other')
        self.act(other, 'accept', id=lid)
        def remove(s):
            s['journey']['home']['props'] = []
        with self.assertRaises(GameError):
            mr._mutate(self.store, {self.store.key(owner): remove})
        self.assertIsNotNone(hs.find(hs.get(self.state(owner)), prop['id']))

    def test_import_cannot_mint_lease_for_other_account(self):
        owner, tenant, stranger = self.user('owner'), self.user('tenant'), self.user('stranger')
        lid, _ = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        stolen = self.state(tenant)
        with self.assertRaises(GameError) as ex:
            self.cmd(stranger, 'import_save', save={'format': 'mot-ngay-lam-nghe/save-v4', 'state': stolen})
        self.assertEqual(ex.exception.code, 'invalid_save')
        self.assertNotIn('rental', self.state(stranger)['journey'])

    def test_rented_house_furniture_belongs_to_tenant_and_survives_leaving(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        self.cmd(tenant, 'jr_deco_buy', item='cay_canh', confirm=True)
        before = deco.public(self.state(tenant))['bag']
        self.assertTrue(any(row['k'] == 'cay_canh' for row in before))
        self.act(tenant, 'leave', id=lid)
        self.assertEqual(deco.public(self.state(tenant))['bag'], before)
        self.assertEqual(deco.public(self.state(owner))['bag'], [])

    def test_paid_days_have_house_comfort_and_shared_move_is_blocked(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, prop = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        state = self.state(tenant)
        state['journey']['life']['spirit'] = 50
        state['journey']['life_day'] += 1
        hs.on_life_day(state)
        self.assertEqual(state['journey']['life']['spirit'], 50 + hs.HOMES[prop['kind']]['comfort'])
        self.assertEqual(state['journey']['home']['stats']['rent_days'], 1)
        with self.assertRaises(GameError):
            hs.accept_shared(state, {'id': 'h1', 'kind': prop['kind'], 'couple': 1, 'name': 'Partner'})

    def test_family_save_cannot_drop_active_contract(self):
        from game import family
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        broken = self.state(tenant)
        broken['journey'].pop('rental')
        sid = self.store.key(tenant)
        def drop(db):
            db.execute('SELECT 1 FROM sessions WHERE sid=? FOR UPDATE', (sid,))
            family._save(db, sid, broken, [])
        with self.assertRaises(GameError):
            self.store.transaction(drop)
        self.assertEqual(self.state(tenant)['journey']['rental']['id'], lid)

    def test_listing_names_follow_current_account_display(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner)
        self.store.transaction(lambda db: db.execute('UPDATE accounts SET display=? WHERE sid=?', ('Tên mới', self.store.key(owner))))
        self.assertEqual(rentals.get(self.store, tenant)['market'][0]['owner_name'], 'Tên mới')
        self.act(tenant, 'accept', id=lid)
        self.store.transaction(lambda db: db.execute('UPDATE accounts SET display=? WHERE sid=?', ('Khách mới', self.store.key(tenant))))
        self.assertEqual(rentals.get(self.store, owner)['mine'][0]['tenant_name'], 'Khách mới')

    def test_both_block_systems_hide_market_and_deny_accept_either_direction(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner)
        owner_sid, tenant_sid = self.store.key(owner), self.store.key(tenant)
        for table in ('marriage_blocks', 'blocks'):
            for a, b in ((owner_sid, tenant_sid), (tenant_sid, owner_sid)):
                if table == 'blocks':
                    a, b = rentals._pid(a), rentals._pid(b)
                column = 'sid' if table == 'marriage_blocks' else 'pid'
                self.store.transaction(lambda db: db.execute(f'INSERT INTO {table}({column},target,at) VALUES(?,?,0)', (a,b)))
                self.assertEqual(rentals.get(self.store, tenant)['market'], [])
                with self.assertRaises(rentals.RentalError) as err:
                    self.act(tenant, 'accept', id=lid)
                self.assertEqual(err.exception.code, 'blocked')
                self.store.transaction(lambda db: db.execute(f'DELETE FROM {table} WHERE {column}=? AND target=?', (a,b)))
        self.act(tenant, 'accept', id=lid)
        self.store.transaction(lambda db: db.execute('INSERT INTO blocks(pid,target,at) VALUES(?,?,0)', (rentals._pid(owner_sid),rentals._pid(tenant_sid))))
        with self.assertRaises(rentals.RentalError) as err:
            self.act(tenant, 'renew', id=lid)
        self.assertEqual(err.exception.code, 'blocked')
        self.act(tenant, 'leave', id=lid)  # blocking never traps someone in a lease

    def test_active_contract_is_never_buried_by_recent_history(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner)
        self.act(tenant, 'accept', id=lid)
        sid = self.store.key(owner)
        def history(db):
            for n in range(45):
                db.execute("INSERT INTO rentals(id,owner,property,kind,owner_name,rent,status,at,updated) VALUES(?,?,?,'tap_the','Owner',1,'cancelled',9999999999,9999999999)",
                           (f'history-{n}',sid,f'history-property-{n}'))
        self.store.transaction(history)
        mine = rentals.get(self.store, owner)['mine']
        self.assertEqual(len(mine), 40)
        self.assertEqual(mine[0]['id'], lid)
        self.assertEqual(mine[0]['status'], 'leased')

    def test_market_pagination_exposes_older_listings_without_overlap(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        sid = self.store.key(owner)
        def seed(db):
            for n in range(205):
                db.execute("INSERT INTO rentals(id,owner,property,kind,owner_name,rent,status,at,updated) VALUES(?,?,?,'tap_the','Owner',1,'listing',123,123)",
                           (f'page-{n:04d}',sid,f'page-property-{n}'))
        self.store.transaction(seed)
        first = rentals.get(self.store, tenant)
        second = rentals.get(self.store, tenant, offset=first['next_offset'])
        third = rentals.get(self.store, tenant, offset=second['next_offset'])
        self.assertEqual([len(p['market']) for p in (first,second,third)], [100,100,5])
        self.assertEqual((first['next_offset'],second['next_offset'],third['next_offset']), (100,200,None))
        ids = [r['id'] for p in (first,second,third) for r in p['market']]
        self.assertEqual(len(set(ids)),205)
        self.assertEqual(ids, sorted(ids, reverse=True))
        for bad in (-1, 1000001, '0', True):
            with self.assertRaises(rentals.RentalError):
                rentals.get(self.store, tenant, offset=bad)

    def test_market_acquisition_preserves_legacy_and_prevents_instant_flip(self):
        owner = self.user('owner')
        with patch('game.housing.pm.quote', return_value={'multiplier_bp': 15000, 'rent_bp': 10000, 'news': None}):
            prop = self.prop(owner)
            basis = self.state(owner)['journey']['property_market_basis'][prop['id']]
            self.assertEqual(basis, 15000)
            self.assertLessEqual(hs.value_of(prop, prop['day'], basis), prop['price'])
            old = dict(prop)
            self.assertEqual(hs.value_of(old, old['day']), old['price'] * 15000 // 10000 // 10 * 10)
            validate_state(self.state(owner))
        with patch('game.housing.pm.quote', return_value={'multiplier_bp': 7500, 'rent_bp': 10000, 'news': None}):
            self.assertLess(hs.value_of(prop, prop['day'], basis), prop['price'])


class Reclaim(Rentals):
    """F#225: a tenant who stops playing never runs out of life days; after the paid period the owner may reclaim."""

    def age(self, lid, days):
        self.store.transaction(lambda db: db.execute('UPDATE rentals SET updated=updated-? WHERE id=?', (days * 86400, lid)))

    def away(self, tok):
        sid = self.store.key(tok)
        self.store.transaction(lambda db: db.execute("UPDATE sessions SET updated_at='2000-01-01 00:00:00' WHERE sid=?", (sid,)))

    def mine(self, owner, lid):
        return next(r for r in rentals.get(self.store, owner)['mine'] if r['id'] == lid)

    def test_never_mid_period_then_after_five_real_days(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, prop = self.listing(owner, 100)
        self.act(tenant, 'accept', id=lid)
        row = self.mine(owner, lid)
        self.assertFalse(row['reclaim'])
        self.assertGreater(row['paid_until'], 0)
        with self.assertRaises(rentals.RentalError) as e:
            self.act(owner, 'reclaim', id=lid)
        self.assertEqual(e.exception.code, 'paid_period')
        self.assertIn('Chưa thể lấy lại nhà giữa kỳ', str(e.exception))
        with self.assertRaises(rentals.RentalError) as e:
            self.act(tenant, 'reclaim', id=lid)
        self.assertEqual(e.exception.code, 'forbidden')
        self.age(lid, 5.01)
        self.assertTrue(self.mine(owner, lid)['reclaim'])
        money = self.total(owner), self.total(tenant)
        out = self.act(owner, 'reclaim', id=lid, rid='reclaim-0000001')
        self.assertTrue(self.act(owner, 'reclaim', id=lid, rid='reclaim-0000001')['replayed'])
        self.assertIn('Đã lấy lại', out['message'])
        self.assertEqual((self.total(owner), self.total(tenant)), money)        # no money moves
        self.assertEqual(self.mine(owner, lid)['status'], 'ended')
        t = self.state(tenant)
        self.assertNotIn('rental', t['journey'])
        self.assertIsNone(rentals.get(self.store, tenant)['tenancy'])
        self.assertNotEqual(hs.public(t)['place']['where_id'], 'lease')
        self.assertIn('chủ nhà đã lấy lại nhà', t['journey']['home']['log'][-1]['text'])
        self.assertIn('Lấy lại', self.state(owner)['journey']['home']['log'][-1]['text'])
        with self.store.connect() as db:
            note = db.execute("SELECT text FROM inbox WHERE pid=? AND kind='rental'", (rentals._pid(self.store.key(tenant)),)).fetchone()
        self.assertIn('đã lấy lại nhà', note['text'])
        validate_state(t); mr.validate_save(t); validate_state(self.state(owner))
        self.cmd(tenant, 'jr_home_rent', kind=next(iter(hs.RENT)), confirm=True)   # finds a new home (commit hook happy)
        self.cmd(owner, 'jr_home_move', id=prop['id'], confirm=True)            # the owner has the home back
        with self.assertRaises(rentals.RentalError):
            self.act(owner, 'reclaim', id=lid)

    def test_an_absent_tenant_without_a_further_period(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner, 100)
        self.act(tenant, 'accept', id=lid)
        self.away(tenant)
        self.assertTrue(self.mine(owner, lid)['reclaim'])
        self.act(owner, 'reclaim', id=lid)
        self.assertNotIn('rental', self.state(tenant)['journey'])

    def test_a_further_period_bought_ahead_is_honoured(self):
        owner, tenant = self.user('owner'), self.user('tenant')
        lid, _ = self.listing(owner, 100)
        self.act(tenant, 'accept', id=lid)
        self.act(tenant, 'renew', id=lid)
        self.away(tenant)
        self.age(lid, 6)
        with self.assertRaises(rentals.RentalError) as e:
            self.act(owner, 'reclaim', id=lid)
        self.assertIn('trả trước thêm một kỳ', str(e.exception))
        self.assertIn('rental', self.state(tenant)['journey'])
        self.age(lid, 4.01)
        self.act(owner, 'reclaim', id=lid)
        self.assertNotIn('rental', self.state(tenant)['journey'])

    def test_terms_say_after_the_period_never_mid_period(self):
        terms = rentals.get(self.store, self.user('owner'))['rules']['terms']
        self.assertIn('không thể lấy lại nhà giữa kỳ', terms)
        self.assertIn('sau kỳ đã trả', terms)


if __name__ == '__main__':
    unittest.main()
