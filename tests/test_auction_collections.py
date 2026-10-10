"""Collectible value is ownership + rarity, never bids or inflated prices."""
import json
import unittest
from game import auction as au, auction_content as C, leaderboard as lb
from tests.test_bank import story
from tests.pg_support import pg_only
from tests.test_leaderboard import Base


def owned(iid, price=5000):
    return dict(k=C.ITEM[iid]['kind'], t=C.ITEM[iid]['name'], d=2, p=price, lot='test-01')


class Collections(unittest.TestCase):
    def test_catalogue_has_four_new_distinct_paintings_and_provenance(self):
        art = [x for x in C.ITEMS if x['kind'] == 'art']
        self.assertEqual(len(art), 14)
        self.assertEqual(len({x['motif'] for x in art}), 14)
        for x in C.ITEMS:
            self.assertTrue(x['story'])
            self.assertEqual(x['collector_points'], {1: 10, 2: 40, 3: 120}[x['tier']])
        self.assertTrue(all(x['medium'] for x in art))

    def test_only_received_known_items_count_price_does_not(self):
        s = story(1000)
        s['journey']['uniq'] = au.initial()
        b = s['journey']['uniq']
        b['own'] = {'tr_sen_ho': owned('tr_sen_ho'), 'tr_nuoc_noi': owned('tr_nuoc_noi')}
        b['hold'] = {'test-02': dict(a=999999, b=0)}
        b['stats'] = dict(bids=999, won=999, xu=99999999)
        self.assertEqual(au.collection_score(s), (130, 2, 1))
        b['own']['tr_sen_ho']['p'] = 1000000000
        self.assertEqual(au.collection_score(s), (130, 2, 1))
        b['own']['unknown_future_item'] = owned('tr_sen_ho')
        b['own']['tr_tau_cuoi'] = dict(owned('tr_tau_cuoi'), k='phone')
        self.assertEqual(au.collection_score(s), (130, 2, 1))

    def test_old_saves_and_malformed_blocks_are_empty(self):
        for j in (None, {}, {'uniq': None}, {'uniq': {'own': []}}, {'uniq': {'own': {'tr_sen_ho': None}}}):
            self.assertEqual(au.collection_score({'journey': j}), (0, 0, 0))
        self.assertNotIn('collection', lb.summary(story(1000)))

    def test_board_score_tiebreak_and_public_fields(self):
        s = story(1000)
        s['journey']['uniq'] = au.initial()
        s['journey']['uniq']['own'] = {'tr_nuoc_noi': owned('tr_nuoc_noi')}
        row = lb.summary(s)['collection']
        self.assertEqual(row, (120, 1, 1, 0, 0, 1, 0, 1))
        self.assertEqual(lb.parse_query({'board': 'collection'}), ('collection', 50))
        data = dict(zip(lb._FIELDS, row), acct=True, display='Lan', gname=None)
        public = lb._row_out('collection', data)
        self.assertEqual((public['score'], public['items'], public['legendary']), (120, 1, 1))
        self.assertNotIn('sid', public)
        self.assertTrue(lb.heal(lb.summary(s)))

    def test_existing_lots_gain_provenance_without_changing_bid_terms(self):
        row = dict(id='test-01', item='tr_sen_ho', kind='art', tier=1, name='Sen hồ Mây', emoji='🖼️',
                   data='{"artist":"Cô Ba Lụa","motif":"lotus"}', start=5000, step=500,
                   starts_at=1, ends_at=999, status='open', high=5500, bids=2)
        v = au._lot_view(row)
        self.assertEqual(v['data']['medium'], C.ITEM['tr_sen_ho']['medium'])
        self.assertEqual(v['collector_points'], 10)
        self.assertEqual((v['start'], v['next'], v['high']), (5000, 6000, 5500))
        row['tier'] = 3  # operator price tier is not the object's rarity
        v = au._lot_view(row)
        self.assertEqual((v['tier'], v['rarity'], v['collector_points']), (3, 1, 10))

    def test_painting_delivered_by_older_node_is_restored_once(self):
        from game.engine import migrate_state, validate_state
        s = story(1000)
        s['journey']['uniq'] = au.initial()
        s['journey']['uniq']['own']['tr_long_van'] = owned('tr_long_van')
        s = migrate_state(s)
        validate_state(s)
        pieces = [x for x in s['journey']['reno']['items'] if x['k'] == 'uq_tr_long_van']
        self.assertEqual(len(pieces), 1)
        s = migrate_state(s)
        validate_state(s)
        self.assertEqual([x for x in s['journey']['reno']['items'] if x['k'] == 'uq_tr_long_van'], pieces)


@pg_only
class CollectionDatabase(Base):
    def collector(self, name, iid, price):
        from game import live_effects
        token = self.player(story(9000), account=name)
        it = C.ITEM[iid]
        data = dict(lot='test-01', what='win', item=iid, kind=it['kind'], text=it['name'], name=it['name'], src='auction')
        with self.store.connect() as db:
            db.execute('INSERT INTO live_effects(id,sid,kind,amount,data,status,at) VALUES(?,?,?,?,?,?,?)',
                       ('auc:collection:' + iid, self.sid(token), 'auction', price, json.dumps(data), 'pending', au.now()))
        result = live_effects.on_load(self.store, token, self.store.read(token)[0])
        self.assertTrue(result)
        return token

    def test_rank_uses_received_rarity_and_existing_visibility(self):
        lan = self.collector('Lan', 'tr_long_van', 500000)
        minh = self.collector('Minh', 'tr_sen_ho', 1000000)
        d = lb.view(self.store, 'collection', token=lan)
        self.assertEqual([(r['name'], r['score']) for r in d['rows']], [('Lan', 120), ('Minh', 10)])
        self.assertEqual((d['me']['rank'], d['me']['items']), (1, 1))
        lb.set_visible(self.store, lan, self.store.read(lan)[0], False)
        d = lb.view(self.store, 'collection', token=lan)
        self.assertEqual([r['name'] for r in d['rows']], ['Minh'])
        self.assertFalse(d['me']['visible'])
        self.assertEqual(d['me']['score'], 120)
        self.assertNotIn('sid', d['rows'][0])

    def test_upgrade_backfills_existing_owners_idempotently(self):
        lan = self.collector('Lan', 'tr_hac_ngoc', 50000)
        with self.store.connect() as db:
            db.execute("DELETE FROM leaderboard WHERE board='collection'")
            db.execute("INSERT INTO leaderboard_meta(k,v) VALUES('backfill','3') ON CONFLICT(k) DO UPDATE SET v='3'")
        self.assertGreater(lb.backfill(self.store, pause=0), 0)
        lb.clear_cache()
        d = lb.view(self.store, 'collection', token=lan)
        self.assertEqual(d['me']['score'], 40)
        self.assertEqual(lb.backfill(self.store, pause=0), 0)
