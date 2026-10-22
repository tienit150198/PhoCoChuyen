"""🤝 Phụ kiện đôi (game/friend_charms.py, góp ý #484, owner 22/10): a pair is bought once (the price leaves the buyer's
wallet in the save's own transaction), offered to a friend only, accepted (both wear it, each sees the other's name) or
declined (back to the box), cancelled, sold back from the box; no limit on pairs worn; what the character draws is the
count by kind; an old save loads unchanged; 🛍️ the accessories are sold at Tiệm phụ kiện (the wardrobe's words)."""
import json

from game import friend_charms as fc
from game import marriage as mr
from game import wardrobe as wd
from game.engine import migrate_state, new_state, validate_state
from tests.test_marriage import Base


class Charms(Base):
    def charm(self, tok, kind='tri_ki', **d):
        out = self.act(tok, 'charm_buy', kind=kind, **d)
        return out, [x for x in out['charms']['box'] if x['kind'] == kind][0]['id'] if out['charms']['box'] else None

    def pair(self, a, b, kind='tri_ki'):
        self.befriend(self.sid(a), self.sid(b))
        _, cid = self.charm(a, kind)
        self.act(a, 'charm_offer', id=cid, code=self.code(b))
        self.act(b, 'charm_respond', id=cid, answer='accept')
        return cid

    def mine(self, tok):
        return self.act(tok, 'charm_view')['charms']

    def test_buy_takes_the_price_once_and_fills_the_box(self):
        a = self.user('fc_buy', wallet=1000)
        price = fc.INDEX['chi_cot']['price']
        self.assertEqual(price, 220, 'base 200, +10 % price index')
        out, cid = self.charm(a, 'chi_cot', rid='same-rid-0001')
        self.assertEqual(self.wallet(a), 1000 - price)
        self.assertEqual(out['revision'], self.store.read(a)[1], 'the answer carries the save the client adopts')
        self.assertEqual(out['state']['journey']['wallet'], 1000 - price)
        again = self.act(a, 'charm_buy', kind='chi_cot', rid='same-rid-0001')
        self.assertIn('đã mua rồi', again['message'])
        self.assertEqual(self.wallet(a), 1000 - price, 'a retried request pays nothing')
        box = self.mine(a)['box']
        self.assertEqual([(x['id'], x['kind'], x['price'], x['sell']) for x in box], [(cid, 'chi_cot', price, price * 80 // 100)])
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'charm_buy', kind='nhan_cuoi')

    def test_not_enough_money_and_the_box_limit(self):
        a = self.user('fc_poor', wallet=50)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'charm_buy', kind='tri_ki')
        self.assertEqual(e.exception.code, 'not_enough')
        self.assertEqual((self.wallet(a), self.mine(a)['box']), (50, []))
        self.fund(a, 100000)
        for _ in range(fc.BOX_MAX):
            self.act(a, 'charm_buy', kind='tri_ki')
        self.assertFalse(self.mine(a)['can_buy'])
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'charm_buy', kind='tri_ki')
        self.assertEqual(e.exception.code, 'box_full')

    def test_guests_and_strangers_cannot(self):
        a, b = self.user('fc_a'), self.user('fc_b')
        guest, _, _ = self.store.session()
        with self.assertRaises(mr.MarriageError) as e:
            mr.act(self.store, guest, 'charm_buy', dict(kind='tri_ki'))
        self.assertIn('phụ kiện đôi', e.exception.message)
        _, cid = self.charm(a)
        with self.assertRaises(mr.MarriageError) as e:
            self.act(a, 'charm_offer', id=cid, code=self.code(b))
        self.assertEqual(e.exception.code, 'not_friends')
        before = self.wallet(a)
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'charm_buy', kind='ban_than', code=self.code(b))
        self.assertEqual(self.wallet(a), before, 'refused before any payment')
        with self.assertRaises(mr.MarriageError):
            self.act(b, 'charm_offer', id=cid, code=self.code(a))   # not b's pair
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'charm_offer', id=cid, code=self.code(a))

    def test_offer_accept_and_both_wear_it_with_each_others_name(self):
        a, b = self.user('fc_lan'), self.user('fc_mai')
        self.befriend(self.sid(a), self.sid(b))
        self.assertEqual([f['name'] for f in self.mine(a)['friends']], ['Fc_Mai'])
        _, cid = self.charm(a, 'ban_than')
        self.act(a, 'charm_offer', id=cid, code=self.code(b))
        self.assertEqual(self.mine(a)['sent'][0]['name'], 'Fc_Mai')
        self.assertEqual([(x['id'], x['name']) for x in self.mine(b)['incoming']], [(cid, 'Fc_Lan')])
        self.assertIn('Tiệm phụ kiện', self.view(b)['me']['notice'])
        self.assertEqual(fc.boot(self.store, b), dict(worn={}, incoming=1))
        out = self.act(b, 'charm_respond', id=cid, answer='accept')
        self.assertIn('Fc_Lan', out['message'])
        va, vb = self.mine(a), self.mine(b)
        self.assertEqual([(p['kind'], p['name'], p['on'], p['mine']) for p in va['pairs']], [('ban_than', 'Fc_Mai', True, True)])
        self.assertEqual([(p['kind'], p['name'], p['on'], p['mine']) for p in vb['pairs']], [('ban_than', 'Fc_Lan', True, False)])
        self.assertEqual((va['worn'], vb['worn'], va['box'], vb['incoming']), ({'ban_than': 1}, {'ban_than': 1}, [], []))
        self.assertEqual(fc.boot(self.store, a), dict(worn={'ban_than': 1}, incoming=0))
        with self.assertRaises(mr.MarriageError):
            self.act(b, 'charm_respond', id=cid, answer='accept')

    def test_decline_cancel_and_expiry_bring_it_back_to_the_box(self):
        a, b = self.user('fc_x'), self.user('fc_y')
        self.befriend(self.sid(a), self.sid(b))
        _, cid = self.charm(a)
        self.act(a, 'charm_offer', id=cid, code=self.code(b))
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'charm_sell', id=cid)   # waiting for an answer
        self.act(b, 'charm_respond', id=cid, answer='decline')
        self.assertEqual([x['id'] for x in self.mine(a)['box']], [cid])
        self.assertIn('chưa nhận', self.view(a)['me']['notice'])
        self.act(a, 'charm_offer', id=cid, code=self.code(b))
        self.act(a, 'charm_cancel', id=cid)
        self.assertEqual((self.mine(a)['sent'], self.mine(b)['incoming']), ([], []))
        self.act(a, 'charm_offer', id=cid, code=self.code(b))
        self.clock.t += fc.OFFER_DAYS * 86400 + 60
        self.assertEqual((self.mine(b)['incoming'], [x['id'] for x in self.mine(a)['box']]), ([], [cid]))
        with self.assertRaises(mr.MarriageError):
            self.act(b, 'charm_respond', id=cid, answer='accept')

    def test_sell_back_from_the_box_once(self):
        a = self.user('fc_sell', wallet=1000)
        _, cid = self.charm(a, 'chi_cot')
        paid = fc.INDEX['chi_cot']['price']
        self.act(a, 'charm_sell', id=cid)
        self.assertEqual(self.wallet(a), 1000 - paid + paid * 80 // 100)
        self.act(a, 'charm_sell', id=cid)
        self.assertEqual(self.wallet(a), 1000 - paid + paid * 80 // 100)
        self.assertEqual(self.mine(a)['box'], [])

    def test_no_limit_on_pairs_worn_and_the_switches(self):
        a = self.user('fc_many', wallet=100000)
        friends = [self.user(f'fc_f{i}') for i in range(4)]
        ids = [self.pair(a, f, kind) for f, kind in zip(friends, ('chi_cot', 'chi_cot', 'tri_ki', 'ban_than'))]
        ids.append(self.pair(a, friends[0], 'tri_ki'))   # two pairs with the same friend are fine too
        self.assertEqual(self.mine(a)['worn'], {'chi_cot': 2, 'ban_than': 1, 'tri_ki': 2})
        self.act(friends[0], 'charm_wear', id=ids[0], on=False)
        self.assertEqual(self.mine(a)['worn']['chi_cot'], 2, 'each side has its own switch')
        self.assertEqual(self.mine(friends[0])['worn'], {'tri_ki': 1})
        self.act(a, 'charm_wear', id=ids[1], on=False)
        self.assertEqual(self.mine(a)['worn'], {'chi_cot': 1, 'ban_than': 1, 'tri_ki': 2})
        self.act(a, 'charm_wear', all=True, on=False)
        self.assertEqual(self.mine(a)['worn'], {})
        self.act(a, 'charm_wear', all=True, on=True)
        self.assertEqual(sum(self.mine(a)['worn'].values()), 5)
        with self.assertRaises(mr.MarriageError):
            self.act(self.user('fc_other'), 'charm_wear', id=ids[2], on=False)
        with self.assertRaises(mr.MarriageError):
            self.act(a, 'charm_wear', id=ids[2], on='yes')

    def test_a_deleted_friend_leaves_the_pair_named(self):
        a, b = self.user('fc_keep'), self.user('fc_gone')
        self.pair(a, b, 'chi_cot')
        mr.forget(self.store, b)
        pairs = self.mine(a)['pairs']
        self.assertEqual([(p['kind'], p['name'], p['on']) for p in pairs], [('chi_cot', 'Fc_Gone', True)])

    def test_the_old_save_is_untouched(self):
        s = new_state()
        before = json.dumps(s, sort_keys=True)
        s2 = migrate_state(json.loads(before))
        validate_state(s2)
        self.assertNotIn('charms', s2)
        a = self.user('fc_save', wallet=1000)
        self.charm(a)
        st = self.state(a)
        self.assertFalse({'charms', 'friend_charms', 'pairs'} & set(st), 'no save key: the table holds the pairs')
        validate_state(migrate_state(json.loads(json.dumps(st))))


class Shop(Base):
    def test_accessories_point_to_the_new_shop(self):
        c = wd.content()
        self.assertEqual(c['acc_shop']['name'], 'Tiệm phụ kiện')
        self.assertEqual([k['id'] for k in c['pairs']['kinds']], ['chi_cot', 'ban_than', 'tri_ki'])
        s = new_state()
        s['journey']['gender'] = 'female'
        wd.migrate(s)
        self.assertIn('Tiệm phụ kiện', wd.locked(s, 'mu_len'))
        self.assertIn('tủ đồ', wd.locked(s, 'ao_len'))

    def test_the_client_draws_and_sells_them(self):
        import shutil
        import subprocess
        from pathlib import Path
        if not shutil.which('node'):
            self.skipTest('Node is needed for the shared character painters')
        root = Path(__file__).resolve().parents[1]
        r = subprocess.run(['node', str(root / 'tests' / 'friend-charms.mjs')], cwd=root, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class Database(Base):
    def test_a_new_table_only_and_the_live_release_runs_no_ddl_past_its_version(self):
        import re
        import subprocess
        from pathlib import Path
        from game import pg_schema
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 86)
        names = [t['name'] for t in pg_schema.TABLES]
        self.assertLess(names.index('friend_charms'), names.index('mnl_meta'))
        ddl = pg_schema.TABLES_DDL
        part = ddl[ddl.index('CREATE TABLE IF NOT EXISTS friend_charms'):]
        self.assertNotIn('REFERENCES', part, 'no FK')
        self.assertFalse(re.search(r'\b(ALTER|DROP|UPDATE|INSERT)\b', part), 'a new table and indexes only, no backfill')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM friend_charms').fetchone()[0], 0)
        root = Path(__file__).resolve().parents[1]
        old = subprocess.run(['git', 'show', 'd4eb098b:game/pg_schema.py'], cwd=root, capture_output=True, text=True, encoding='utf-8')
        if old.returncode:
            self.skipTest('no git tree with d4eb098b (2.5.2.4)')
        self.assertIn('SCHEMA_VERSION = 84', old.stdout)
        self.assertNotIn('friend_charms', old.stdout)
        self.assertIn('previous_version >= SCHEMA_VERSION and not missing_tables(raw)', old.stdout)
