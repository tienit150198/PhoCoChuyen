"""🔨 Nhà đấu giá đồ độc bản (game/auction.py): the catalogue, the save block, the bid's escrow (wallet then bank, never
a debt), the database side on real PostgreSQL (row lock, compare-and-set, refunds through live_effects, voided refunds
reused, anti-snipe, the account age), settlement exactly once whatever the threads, and the money invariant: only the
winner's money leaves the game."""
import copy
import datetime
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from game import auction as au
from game import auction_content as C
from game import deco_content as DC
from game import spend_content as SC
from game.engine import GameError, validate_state
from tests.pg_support import pg_only
from tests.test_bank import act, story

T0 = 1_791_300_000.0          # 2026-10-06 (Tuesday) 21:20 Vietnam time


def money(s):
    b = s['journey'].get('bank')
    return s['journey']['wallet'] + (b['balance'] if b else 0)


def holds(s):
    return au.held(s)


class Catalogue(unittest.TestCase):
    def test_items_unique_tiers_and_kinds(self):
        ids = [it['id'] for it in C.ITEMS]
        self.assertEqual(len(ids), len(set(ids)))
        for it in C.ITEMS:
            self.assertRegex(it['id'], au.ITEM_RE)
            self.assertIn(it['kind'], au.KINDS)
            self.assertIn(it['tier'], C.TIERS)
            self.assertLessEqual(len(it['name']), au.TEXT_MAX)
        self.assertEqual([C.TIERS[t]['start'] for t in (1, 2, 3)], [5_000, 50_000, 500_000])
        for k in au.KINDS:   # every kind at every tier it is planned for exists
            self.assertTrue(any(it['kind'] == k for it in C.ITEMS))

    def test_titles_and_paintings_registered(self):
        for it in C.ITEMS:
            if it['kind'] == 'title':
                x = SC.STYLE_ITEMS[it['id']]
                self.assertEqual((x['kind'], x['price'], x['earn']), ('title', 0, C.EARN))
            if it['kind'] == 'art':
                x = DC.ITEMS['uq_' + it['id']]
                self.assertTrue(x['uq'] and x['price'] == 0 and x['spot'] == 'wall')

    def test_min_next(self):
        self.assertEqual(au.min_next(0, 5000, 500, 0), 5000)
        self.assertEqual(au.min_next(5000, 5000, 500, 1), 5500)          # the step (5 % = 250)
        self.assertEqual(au.min_next(100_000, 50_000, 2500, 3), 105_000)  # 5 %
        self.assertEqual(au.min_next(101, 5000, 1, 1), 107)               # 5 % rounded up

    def test_plan_is_deterministic_and_after_the_peak(self):
        for i in range(60):
            d = datetime.date(2026, 10, 7) + datetime.timedelta(i)
            p = au.plan(d)
            self.assertEqual(p, au.plan(d))
            self.assertTrue(1 <= len(p) <= 3)
            for x in p:
                t = datetime.datetime.fromtimestamp(x['starts_at'], au.VN)
                self.assertTrue((t.hour, t.minute) >= (20, 30) and t.hour < 22)
                self.assertEqual(x['ends_at'] - x['starts_at'], 24 * 3600)
            it = au.pick(d, 1, 1, set())
            self.assertEqual(it['tier'], 1)
        self.assertIsNone(au.pick(datetime.date(2026, 10, 7), 1, 1, {it['id'] for it in C.ITEMS}))

    def test_plate_folding_blocks_copies(self):
        self.assertIn(au.fold_plate('29a 888 88'), au.plates())
        self.assertIn(au.fold_plate('68-loc-68'), au.plates())
        self.assertNotIn(au.fold_plate('LAN-01'), au.plates())


class Save(unittest.TestCase):
    def test_absent_block_is_valid_and_hidden(self):
        s = story(1000)
        validate_state(s)
        self.assertIsNone(au.public(s))
        self.assertNotIn('uniq', s['journey'])

    def test_bid_holds_wallet_then_bank(self):
        s = story(30_000)
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=20_000)
        m0 = money(s)
        s, r = act(s, 'jr_auc_bid', lot='20261007-1', amount=12_000, label='Mây-0001')
        U = s['journey']['uniq']
        self.assertEqual(U['hold']['20261007-1'], dict(a=12_000, b=2_000))   # 10,000 cash, 2,000 from the account
        self.assertEqual(money(s) + holds(s), m0)
        self.assertEqual(r['auction']['delta'], 12_000)
        s, r = act(s, 'jr_auc_bid', lot='20261007-1', amount=13_000)        # raising: only the difference
        self.assertEqual(r['auction'], dict(lot='20261007-1', amount=13_000, before=12_000, delta=1_000, anon=False))
        self.assertEqual(U['hold']['20261007-1']['a'], 12_000)             # (the copy above is the older state)
        self.assertEqual(s['journey']['uniq']['hold']['20261007-1'], dict(a=13_000, b=3_000))
        s2, r = act(s, 'jr_auc_bid', lot='20261007-1', amount=13_000)       # a second tap
        self.assertTrue(r['duplicate'])
        self.assertEqual(s2['journey']['uniq'], s['journey']['uniq'])
        validate_state(s)

    def test_refusals_change_nothing(self):
        s = story(4_000)
        for p, code in ((dict(lot='20261007-1', amount=5_000), 'not_enough'), (dict(lot='BAD ID', amount=5_000), None),
                        (dict(lot='20261007-1', amount=0), None), (dict(lot='20261007-1', amount=5000, anon='x'), None)):
            before = copy.deepcopy(s)
            with self.assertRaises(GameError) as cm:
                act(s, 'jr_auc_bid', **p)
            self.assertEqual(s, before)
            if code:
                self.assertEqual(cm.exception.code, code)
        s['journey']['wallet'] = -10
        with self.assertRaises(GameError):
            act(s, 'jr_auc_bid', lot='20261007-1', amount=1)                # never with a wallet in debt

    def test_fx_back_and_win(self):
        s = story(60_000)
        s, _ = act(s, 'jr_bk_open')
        s, _ = act(s, 'jr_bk_deposit', amount=50_000)
        s, _ = act(s, 'jr_auc_bid', lot='20261007-2', amount=55_000)
        m = money(s)
        au.apply_fx(s, dict(data=dict(lot='20261007-2', what='back', name='Tranh')), 55_000)
        self.assertEqual(money(s), m + 55_000)
        self.assertEqual(s['journey']['bank']['balance'], 50_000)          # the bank part went back to the bank
        self.assertEqual(holds(s), 0)
        s, _ = act(s, 'jr_auc_bid', lot='20261007-3', amount=50_000)
        m = money(s)
        msg = au.apply_fx(s, dict(data=dict(lot='20261007-3', what='win', item='dh_ky_lan', kind='title', text='Kỳ Lân Phố Mây')), 50_000)
        self.assertIn('thắng', msg)
        self.assertEqual(money(s), m)                                       # burned: nothing comes back
        self.assertEqual(holds(s), 0)
        self.assertEqual(s['journey']['uniq']['own']['dh_ky_lan']['p'], 50_000)
        self.assertEqual(s['journey']['spend']['own']['dh_ky_lan'], SC.PERMANENT)
        s2, _ = act(s, 'jr_auc_bid', lot='20261007-4', amount=5_000)
        au.apply_fx(s2, dict(data=dict(lot='20261007-4', what='win', item='tr_sen_ho', kind='art', text='Sen hồ Mây')), 5_000)
        self.assertTrue(any(x['k'] == 'uq_tr_sen_ho' for x in s2['journey']['reno']['items']))
        validate_state(s2)

    def test_validate_and_upgrade(self):
        s = story(10_000)
        s, _ = act(s, 'jr_auc_bid', lot='20261007-1', amount=6_000)
        for bad in (dict(v=2), dict(hold={'x y': dict(a=1, b=0)}), dict(hold={'20261007-1': dict(a=5, b=6)}),
                    dict(own={'dh_x': dict(k='car', t='x', d=1, p=1, lot='20261007-1')}), dict(extra=1)):
            t = copy.deepcopy(s)
            t['journey']['uniq'].update(bad)
            with self.assertRaises(GameError):
                validate_state(t)
        t = copy.deepcopy(s)
        t['journey']['uniq']['new_key'] = 1
        t['journey']['uniq']['hold']['20261007-1']['z'] = 1
        au.upgrade(t['journey'])
        self.assertEqual(t['journey']['uniq'], s['journey']['uniq'])      # a newer build's extras dropped, the hold kept


@pg_only
class Database(unittest.TestCase):
    """game/auction.py's database side through the real command path (game/storage.py) on PostgreSQL."""

    def setUp(self):
        from game.storage import Store
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 's.db', story=True)
        self.addCleanup(self.store.close_pool)
        au._VIEW.clear()
        au._planned.clear()
        self.n = 0
        self.t = [T0]
        p = patch('game.auction.now', lambda: self.t[0])
        p.start()
        self.addCleanup(p.stop)

    def player(self, wallet=2_000_000, bank=0, name='Lan', days=10):
        from game import marriage as mr
        token, _, _ = self.store.session()
        self.store.read(token)
        sid = self.store.key(token)

        def fn(s):
            s['name'] = name
            s['journey']['wallet'] = wallet
            if bank:
                from game import bank as bk
                s2, _ = act(s, 'jr_bk_open')
                s['journey']['bank'] = s2['journey']['bank']
                s['journey']['bank']['balance'] = bank
        mr._mutate(self.store, {sid: fn})
        if days is not None:
            created = (datetime.datetime.fromtimestamp(self.t[0], datetime.UTC) - datetime.timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            with self.store.connect() as db:
                db.execute('INSERT INTO accounts(username, display, pw, sid, created_at) VALUES(?,?,?,?,?)',
                           (f'u{sid[:10]}', name, 'x', sid, created))
                db.execute('INSERT INTO logins(token, sid, csrf) VALUES(?,?,?)', (self.store.digest(token), sid, 'c' * 48))
        return token

    def state(self, token):
        return self.store.read(token)[0]

    def bid(self, token, lot, amount, **kw):
        self.n += 1
        return self.store.command(token, f'auc-{self.n:08d}-{threading.get_ident() % 100000}', self.store.read(token)[1], None,
                                  'jr_auc_bid', dict(lot=lot, amount=amount, **kw))

    def pay(self, token):
        from game import live_effects
        return live_effects.on_load(self.store, token, self.state(token))

    def lot(self, item='pl_may0001', hours=24, tier=None):
        d = dict(item=item, hours=hours)
        if tier:
            d['tier'] = tier
        return au.admin_add(self.store, 'op', d)['id']

    def row(self, lid):
        with self.store.connect() as db:
            return dict(db.execute('SELECT * FROM auction_lots WHERE id=?', (lid,)).fetchone())

    def fx(self, sid=None):
        with self.store.connect() as db:
            q = "SELECT id, sid, amount, status, data FROM live_effects WHERE kind='auction'" + (' AND sid=?' if sid else '') + ' ORDER BY id'
            return [dict(r) for r in db.execute(q, (sid,) if sid else ()).fetchall()]

    def total(self, tokens):
        return sum(money(self.state(t)) + holds(self.state(t)) for t in tokens)

    # ------------------------------------------------------------------ bidding
    def test_outbid_refund_raise_and_resync(self):
        a, b = self.player(name='Lan'), self.player(name='Minh')
        start = self.total([a, b])
        lid = self.lot()
        self.t[0] += 1
        self.bid(a, lid, 5_000, label='Mây-0001')
        self.assertEqual(self.state(a)['journey']['wallet'], 2_000_000 - 5_000)
        with self.assertRaises(GameError) as cm:                          # under the next minimum: nothing held
            self.bid(b, lid, 5_400)
        self.assertEqual(cm.exception.code, 'outbid')
        self.assertEqual(self.state(b)['journey']['wallet'], 2_000_000)
        self.bid(b, lid, 5_500)
        r = self.row(lid)
        self.assertEqual((r['high'], r['high_sid'], r['bids']), (5_500, self.store.key(b), 2))
        rows = self.fx(self.store.key(a))
        self.assertEqual([(x['amount'], x['status']) for x in rows], [(5_000, 'pending')])
        self.assertEqual(self.total([a, b]), start)                       # a's refund still counts as held in a's save
        # a raises without having loaded the refund: the pending refund is reused, only the difference is held
        self.bid(a, lid, 6_000)
        self.assertEqual(self.state(a)['journey']['wallet'], 2_000_000 - 6_000)
        self.assertEqual([x['status'] for x in self.fx(self.store.key(a))], ['void'])
        self.assertFalse(self.pay(a))                                     # nothing left to pay a
        self.bid(b, lid, 7_000)                                           # b was refunded 5,500 (pending) and bids again
        self.assertEqual(self.state(b)['journey']['wallet'], 2_000_000 - 7_000)
        self.assertTrue(self.pay(a))                                      # a's 6,000 back
        self.assertEqual(self.state(a)['journey']['wallet'], 2_000_000)
        self.assertEqual(holds(self.state(a)), 0)
        self.assertEqual(self.total([a, b]), start)
        self.bid(b, lid, 7_500)                                           # the leader raises: +500 only
        self.assertEqual(self.state(b)['journey']['wallet'], 2_000_000 - 7_500)
        with self.store.connect() as db:
            held = db.execute('SELECT SUM(held) AS h FROM auction_bids WHERE lot=?', (lid,)).fetchone()['h']
        self.assertEqual(held, 7_500)

    def test_account_age_and_open_window(self):
        a = self.player(days=1)
        g = self.player(days=None)
        lid = self.lot()
        self.t[0] += 1
        for tok in (a, g):
            with self.assertRaises(GameError) as cm:
                self.bid(tok, lid, 5_000)
            self.assertEqual(cm.exception.code, 'too_new')
            self.assertEqual(self.state(tok)['journey']['wallet'], 2_000_000)
            self.assertNotIn('uniq', self.state(tok)['journey'])
        ok = self.player()
        later = au.admin_add(self.store, 'op', dict(item='pl_43a77777', hours=1, delay=30))['id']
        with self.assertRaises(GameError) as cm:
            self.bid(ok, later, 5_000)
        self.assertEqual(cm.exception.code, 'not_open')
        self.t[0] += 31 * 60 + 3600
        with self.assertRaises(GameError) as cm:
            self.bid(ok, later, 5_000)
        self.assertEqual(cm.exception.code, 'closed')
        self.assertEqual(self.state(ok)['journey']['wallet'], 2_000_000)

    def test_anti_snipe(self):
        a, b = self.player(), self.player(name='Minh')
        lid = self.lot(hours=1)
        end = self.row(lid)['ends_at']
        self.t[0] = end - 600
        self.bid(a, lid, 5_000)
        self.assertEqual(self.row(lid)['ends_at'], end)                   # 10 minutes before: no change
        self.t[0] = end - 60
        self.bid(b, lid, 6_000)
        self.assertEqual(self.row(lid)['ends_at'], end + 300)             # last 5 minutes: +5 minutes
        self.t[0] = end + 10                                              # past the planned end, inside the extension
        self.assertIsNone(au.settle_one(self.store, lid))
        self.bid(a, lid, 7_000)
        self.assertEqual(self.row(lid)['ends_at'], end + 600)
        self.t[0] = end + 601
        self.assertEqual(au.settle_one(self.store, lid), 'sold')

    def test_settlement_burns_only_the_winner_and_runs_once(self):
        a, b, c = self.player(), self.player(name='Minh', bank=300_000, wallet=1_000), self.player(name='Hoa')
        tokens = [a, b, c]
        start = self.total(tokens)
        lid = self.lot(item='dh_ky_lan', tier=2)
        self.t[0] += 1
        self.bid(a, lid, 50_000)
        self.bid(b, lid, 60_000, anon=True)
        self.bid(c, lid, 70_000)
        self.bid(b, lid, 80_000, anon=True)
        self.t[0] = self.row(lid)['ends_at'] + 1
        out = []
        threads = [threading.Thread(target=lambda: out.append(au.settle_one(self.store, lid))) for _ in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.assertEqual(sorted(x for x in out if x), ['sold'])
        self.assertEqual(au.settle_due(self.store), [])
        r = self.row(lid)
        self.assertEqual((r['status'], r['price'], r['winner_name']), ('sold', 80_000, C.ANON))
        for t in tokens:
            self.pay(t)
        self.assertEqual(self.total(tokens), start - 80_000)              # only the winner's money left the game
        sb = self.state(b)
        self.assertEqual(sb['journey']['uniq']['own']['dh_ky_lan']['p'], 80_000)
        self.assertEqual(holds(sb), 0)
        self.assertEqual(sb['journey']['bank']['balance'] + sb['journey']['wallet'], 301_000 - 80_000)
        self.assertNotIn('pending', {x['status'] for x in self.fx()})
        self.assertEqual(self.pay(b), False)                              # paid once
        view = au.view(self.store, a)
        self.assertEqual(view['past'][0]['winner'], C.ANON)
        self.assertEqual(view['burned'], 80_000)
        with self.assertRaises(Exception):                                # sold: never auctioned again
            au.admin_add(self.store, 'op', dict(item='dh_ky_lan'))

    def test_unsold_goes_back_to_the_pool(self):
        lid = self.lot(item='tr_hai_dang', hours=1)
        self.t[0] += 3601
        self.assertEqual(au.settle_one(self.store, lid), 'unsold')
        self.assertEqual(au.settle_one(self.store, lid), None)
        self.assertTrue(au.admin_add(self.store, 'op', dict(item='tr_hai_dang'))['ok'])

    def test_leader_who_erased_their_data(self):
        a, b = self.player(), self.player(name='Minh')
        lid = self.lot(hours=1)
        self.t[0] += 1
        self.bid(a, lid, 5_000)
        self.bid(b, lid, 6_000)
        self.store.delete(b)
        self.t[0] += 3600
        self.assertEqual(au.settle_one(self.store, lid), 'void')
        self.assertEqual([x for x in self.fx() if x['id'].endswith(':win')], [])
        self.pay(a)
        self.assertEqual(money(self.state(a)), 2_000_000)

    def test_concurrent_bids_never_lose_a_hold(self):
        tokens = [self.player(name=f'P{i}', wallet=1_000_000) for i in range(8)]
        start = self.total(tokens)
        lid = self.lot(item='ph_0999999999', tier=1)
        self.t[0] += 1
        errors, ok = [], []

        def run(tok, k):
            for step in range(12):
                v = au.view(self.store, tok)
                cur = next(x for x in v['lots'] if x['id'] == lid)
                try:
                    self.bid(tok, lid, cur['next'] + 100 * k + step)
                    ok.append(1)
                except GameError as e:
                    errors.append(e.code)
        threads = [threading.Thread(target=run, args=(t, i)) for i, t in enumerate(tokens)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.assertTrue(ok)
        self.assertTrue(set(errors) <= {'outbid', 'auction_sync'}, errors)
        r = self.row(lid)
        with self.store.connect() as db:
            bids = [dict(x) for x in db.execute('SELECT * FROM auction_bids WHERE lot=?', (lid,)).fetchall()]
        self.assertEqual([x['sid'] for x in bids if x['held'] > 0], [r['high_sid']])   # one escrow: the leader's
        self.assertEqual(sum(x['held'] for x in bids), r['high'])
        self.assertEqual(r['bids'], len(ok))
        self.assertEqual(self.total(tokens), start)                       # nothing lost while bidding
        self.t[0] = r['ends_at'] + 1
        self.assertEqual(au.settle_one(self.store, lid), 'sold')
        for t in tokens:
            self.pay(t)
        self.assertEqual(self.total(tokens), start - r['high'])
        winners = [t for t in tokens if 'ph_0999999999' in (self.state(t)['journey'].get('uniq') or {}).get('own', {})]
        self.assertEqual(len(winners), 1)
        self.assertTrue(all(holds(self.state(t)) == 0 for t in tokens))

    def test_plan_created_once_by_many_workers(self):
        self.t[0] = datetime.datetime(2026, 10, 10, 9, 0, tzinfo=au.VN).timestamp()
        out = []
        threads = [threading.Thread(target=lambda: out.append(au.ensure_plan(self.store, force=True))) for _ in range(6)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        n = len(au.plan(datetime.date(2026, 10, 10)))
        self.assertEqual(sum(out), n)
        with self.store.connect() as db:
            rows = db.execute("SELECT id, item, tier FROM auction_lots WHERE id LIKE '20261010-%' ORDER BY id").fetchall()
        self.assertEqual([r['tier'] for r in rows], list(range(1, n + 1)))
        self.assertEqual(len({r['item'] for r in rows}), n)
