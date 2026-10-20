"""🛎️ Phố dịch vụ, review fixes of 22/10 (game/service_market.py and its careers): money steps that never wedge (a row
that always fails never blocks a healthy one nor the housekeeping; a full wallet and account falls back to the career's
fund or waits with a notice), a service this build does not know is never paid, delivered work is earned when the
provider leaves, spec checks run again inside the money transaction, the kill switches, the restore floors, the new
indexes, the batched people and polls, the rollback drain, the schema's bounded lock waits and the server's light
routes. Real PostgreSQL (TEST_DATABASE_URL)."""
import concurrent.futures
import importlib.util
import os
import time
from pathlib import Path
from unittest.mock import patch

from game import bank as bk
from game import journey as jr
from game import marriage as mr
from game import service_market as sm
from tests.test_service_market import HOOKS, _Helpers, _on_buyer

ROOT = Path(__file__).resolve().parents[1]


def _boom(state, order):
    raise RuntimeError('a hook that always fails')


def _drain_module():
    spec = importlib.util.spec_from_file_location('svc_drain', ROOT / 'scripts' / 'svc_drain.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Settle(_Helpers):
    def setUp(self):
        super().setUp()
        sm.register('milk_tea', 'boom', dict(name='Đơn hỏng', base=1000, deliver=lambda db, p, b, o: {'ok': 1}, on_buyer=_boom))
        sm.register('milk_tea', 'gift', dict(name='Quà tặng', base=1000, on_buyer=_on_buyer, confirm='buyer'))

    def ready(self, buyer, seller, service='tasting'):
        """An order delivered and confirmed whose money step has not run yet (status ready, due now)."""
        o = self.order(buyer, seller, service)
        self.post(seller, 'take', order=o['id'])
        with patch.object(sm, 'settle_quiet', lambda *a, **k: 0), patch.object(sm, 'settle_for', lambda *a, **k: 0):
            self.post(seller, 'done', order=o['id'])
            if self.row(o['id'])['status'] == 'delivered':
                self.post(buyer, 'confirm', order=o['id'])
        self.assertEqual(self.row(o['id'])['status'], 'ready')
        return o

    def test_a_row_that_always_fails_never_blocks_a_healthy_one_nor_the_housekeeping(self):
        a, b = self.user('rv_a'), self.user('rv_b')
        self.sell(a)
        self.sell(a, service='boom')
        bad = self.ready(b, a, 'boom')
        good = self.ready(b, a)
        with self.store.connect() as db:   # the bad one first in the housekeeping's order
            db.execute('UPDATE svc_orders SET due_at=1 WHERE id=?', (bad['id'],))
            db.execute('UPDATE svc_orders SET due_at=2 WHERE id=?', (good['id'],))
        ta = self.total(a)
        sm._swept[0] = 0.0
        sm.run_housekeeping(self.store)    # never raises
        self.assertEqual(self.row(good['id'])['status'], 'done', 'the healthy row is paid')
        self.assertEqual(self.total(a), ta + 1000 * 3 - sm.fee_of(3000))
        r = self.row(bad['id'])
        self.assertEqual(r['status'], 'ready', 'the failing row waits')
        self.assertGreater(r['due_at'], time.time() + sm.RETRY_BASE_S - 5, 'pushed back')
        self.assertEqual((sm._data(r)['tries'], sm._data(r)['stuck']), (1, 'RuntimeError'))
        # a GET never raises for it (the inbox settles the player's rows first)
        with self.store.connect() as db:
            db.execute('UPDATE svc_orders SET due_at=1 WHERE id=?', (bad['id'],))
        inbox = self.get(b, 'inbox')
        self.assertEqual(next(x for x in inbox['items'] if x['id'] == bad['id'])['stuck'], 'RuntimeError')
        self.assertEqual(sm._data(self.row(bad['id']))['tries'], 2)
        self.assertGreater(self.row(bad['id'])['due_at'], time.time() + 2 * sm.RETRY_BASE_S - 5, 'the wait doubles')
        # the server's housekeeping wraps the step too
        src = (ROOT / 'server.py').read_text(encoding='utf-8')
        self.assertIn('step("svc",lambda:service_market.run_housekeeping(store))', src)
        self.assertIn('step("photo",lambda:photo_studio.run_housekeeping(store))', src)

    def test_a_full_wallet_and_account_pays_the_career_fund_or_waits_with_a_notice(self):
        a, b = self.user('rv_fa'), self.user('rv_fb')
        self.sell(a)
        o = self.ready(b, a)
        mr._mutate(self.store, {self.sid(a): lambda s: s['journey'].update(wallet=jr.WALLET_MAX)})
        fund = self.state(a)['careers']['milk_tea']['money']
        self.assertEqual(sm.settle_for(self.store, self.sid(a)), 1)
        self.assertEqual(self.row(o['id'])['status'], 'done')
        self.assertEqual(self.state(a)['careers']['milk_tea']['money'] - fund, 3000 - sm.fee_of(3000), 'the career fund took it')
        self.assertEqual(self.wallet(a), jr.WALLET_MAX, 'nothing half-credited to the wallet')
        # a refund to a full wallet with no account: it waits, the buyer is told once, then it lands
        o2 = self.order(b, a)
        mr._mutate(self.store, {self.sid(b): lambda s: s['journey'].update(wallet=jr.WALLET_MAX - 10)})
        self.post(b, 'cancel', order=o2['id'])
        r = self.row(o2['id'])
        self.assertEqual((r['status'], sm._data(r)['stuck']), ('refund', 'full'))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT notice FROM marriage_people WHERE sid=?', (self.sid(b),)).fetchone()['notice'], sm.FULL_TEXT)
        mr._mutate(self.store, {self.sid(b): lambda s: s['journey'].update(wallet=1000)})
        with self.store.connect() as db:
            db.execute('UPDATE svc_orders SET due_at=1 WHERE id=?', (o2['id'],))
        sm.settle_for(self.store, self.sid(b))
        self.assertEqual(self.row(o2['id'])['status'], 'refunded')
        self.assertEqual(self.wallet(b), 1000 + 3000)

    def test_credit_refuses_before_anything_moves(self):
        a = self.user('rv_cr')
        s = self.state(a)
        s['journey']['wallet'] = jr.WALLET_MAX - 5
        before = (s['journey']['wallet'], len(s['journey'].get('history') or []))
        with self.assertRaises(sm.ServiceError) as cm:
            sm.credit(s, 100, 'x')
        self.assertEqual(cm.exception.code, 'full')
        self.assertEqual((s['journey']['wallet'], len(s['journey'].get('history') or [])), before)
        self.assertIsNone(bk.get(s))

    def test_a_service_this_build_does_not_know_is_never_paid(self):
        a, b = self.user('rv_ua'), self.user('rv_ub')
        self.sell(a)
        o = self.ready(b, a)
        ta = self.total(a)
        spec = sm.REGISTRY.pop(('milk_tea', 'tasting'))
        try:
            self.assertEqual(sm.settle_for(self.store, None), 0)
        finally:
            sm.REGISTRY[('milk_tea', 'tasting')] = spec
        r = self.row(o['id'])
        self.assertEqual((r['status'], self.total(a)), ('ready', ta), 'left for a build that knows its hooks')
        self.assertGreater(r['due_at'], time.time() + sm.RETRY_MAX_S - 60)
        self.assertEqual(sm._data(r)['stuck'], 'unknown_service')

    def test_delivered_work_is_earned_when_the_provider_leaves(self):
        a, b = self.user('rv_la'), self.user('rv_lb')
        self.sell(a, service='gift')
        self.sell(a)
        o = self.order(b, a, 'gift')
        self.post(a, 'take', order=o['id'])
        self.post(a, 'done', order=o['id'])
        self.assertEqual(self.row(o['id'])['status'], 'delivered')
        held = self.order(b, a)   # paid, never taken: refunded
        tb = self.total(b)
        HOOKS.clear()
        self.store.delete(a)
        self.get(b, 'inbox')
        r = self.row(o['id'])
        self.assertEqual((r['status'], r['paid'], r['fee']), ('done', 0, 1000 * 3), 'the payout is burned, never refunded')
        self.assertEqual([h[0] for h in HOOKS], ['buyer'], 'the buyer keeps the result (on_buyer ran once)')
        self.assertEqual(self.row(held['id'])['status'], 'refunded')
        self.assertEqual(self.total(b), tb + 3000, 'only the order never delivered comes back')


class Checks(_Helpers):
    def test_parallel_orders_run_the_check_inside_the_money_transaction(self):
        a, b = self.user('ck_a'), self.user('ck_b')

        def one_open(db, buyer, state):
            n = db.execute("SELECT COUNT(*) AS n FROM svc_orders WHERE buyer=? AND service='solo' AND status IN ('held','working')",
                           (buyer,)).fetchone()['n']
            return 'Bạn đã có một đơn loại này.' if n else ''
        sm.register('milk_tea', 'solo', dict(name='Một đơn thôi', base=1000, check=one_open))
        self.sell(a, service='solo')
        tb = self.total(b)

        def go(i):
            try:
                return self.post(b, 'order', pid=self.pid(a), career='milk_tea', service='solo', rid=f'solo-race-{i:04d}')['order']['status']
            except mr.MarriageError as e:
                return e.code
        with concurrent.futures.ThreadPoolExecutor(4) as ex:
            got = list(ex.map(go, range(4)))
        self.assertEqual(got.count('held'), 1, got)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) AS n FROM svc_orders WHERE buyer=? AND service='solo'", (self.sid(b),)).fetchone()['n'], 1)
        self.assertEqual(self.total(b), tb - 3000, 'one escrow')


class Switches(_Helpers):
    def test_env_switches_read_one_way(self):
        for v, on in (('1', True), ('true', True), (' YES ', True), ('On', True), ('0', False), ('', False), ('false', False), ('off', False)):
            with patch.dict(os.environ, {'MNL_SVC_OFF': v}):
                self.assertEqual(sm.off(), on, v)
            with patch.dict(os.environ, {'MNL_HOTEL_OFF': v, 'MNL_RESTORE_OFF': v, 'MNL_RADIO_OFF': v, 'MNL_BIRTH_OFF': v, 'MNL_PHOTO_OFF': v}):
                from game import birth, hotel_stay, photo_studio, radio_station, restore_service
                self.assertEqual({birth.off(), hotel_stay.off(), photo_studio.off(), radio_station.off(), restore_service.off()}, {on}, v)

    def test_svc_off_stops_new_money_not_the_way_out(self):
        a, b = self.user('sw_a'), self.user('sw_b')
        self.sell(a)
        held, gone = self.order(b, a), self.order(b, a)
        self.sell(a, service='portrait', mode='nego')
        talk = self.offer(b, a, 4000, service='portrait')
        tb = self.total(b)
        with patch.dict(os.environ, {'MNL_SVC_OFF': '1'}):
            self.refused('svc_off', self.order, b, a)
            self.refused('svc_off', self.offer, b, a, 4000, service='portrait')
            self.refused('svc_off', self.post, a, 'answer', order=talk['id'], op='accept')
            self.assertTrue(self.get(b, 'inbox')['off'])
            self.assertTrue(self.get(b, 'dir')['off'])
            self.post(b, 'cancel', order=gone['id'])                     # a refund
            self.post(b, 'answer', order=talk['id'], op='cancel')        # a talk may stop
            self.post(a, 'take', order=held['id'])                       # paid work goes on and settles
            self.post(a, 'done', order=held['id'])
            self.post(b, 'confirm', order=held['id'])
        self.assertEqual([self.row(x['id'])['status'] for x in (gone, talk, held)], ['refunded', 'cancelled', 'done'])
        self.assertEqual(self.total(b), tb + 3000)


class Perf(_Helpers):
    def test_people_in_one_batch_match_one_by_one(self):
        a, b = self.user('pp_a'), self.user('pp_b')
        with self.store.connect() as db:
            got = sm._people(db, [self.sid(a), self.sid(b), 'no-such-sid'])
            for sid in (self.sid(a), self.sid(b), 'no-such-sid'):
                self.assertEqual(got[sid], sm._person(db, sid))

    def test_inbox_poll_writes_the_network_tag_at_most_once_per_window(self):
        a = self.user('pp_t')
        calls = []
        real = sm.record_net
        with patch.object(sm, 'record_net', side_effect=lambda *x, **k: (calls.append(1), real(*x, **k))[1]):
            for _ in range(3):
                sm.get(self.store, a, None, 'inbox', {}, ip='10.9.8.7')
        self.assertEqual(len(calls), 1)

    def test_inbox_reads_marks_in_one_query_and_the_directory_offset_is_capped(self):
        a, b = self.user('pp_ia'), self.user('pp_ib')
        self.sell(a)
        for _ in range(3):
            self.complete(b, a)
        seen = []
        real = sm._marks
        with patch.object(sm, '_marks', side_effect=lambda *x: (seen.append(1), real(*x))[1]):
            items = self.get(b, 'inbox')['items']
        self.assertEqual((len(items), len(seen)), (3, 1))
        d = self.get(b, 'dir', offset='999999')
        self.assertIsNone(d['next'])
        self.assertEqual(d['items'], [])

    def test_regulars_count_is_cached_and_refreshed_by_a_deal(self):
        a, b = self.user('pp_ra'), self.user('pp_rb')
        self.sell(a)
        self.complete(b, a)
        with self.store.connect() as db:
            self.assertEqual(sm.regulars_count(db, self.sid(a)), 0)
            with patch.object(sm, 'regulars', side_effect=AssertionError('cached')):
                self.assertEqual(sm.regulars_count(db, self.sid(a)), 0)
        self.complete(b, a)   # a deal in this process: read again
        with self.store.connect() as db:
            self.assertEqual(sm.regulars_count(db, self.sid(a)), 1)

    def test_the_badges_of_a_news_poll_share_one_connection(self):
        sid = self.sid(self.user('pp_al'))
        n = []
        real = self.store.connect
        with patch.object(self.store, 'connect', side_effect=lambda *x, **k: (n.append(1), real(*x, **k))[1]):
            out = mr.alerts(self.store, sid)
        self.assertEqual(len(n), 2, 'the marriage counts, then one for 🛎️ 🏨 💒')
        self.assertEqual((out['svc'], out['wedsvc']), (0, 0))

    def test_new_indexes_match_the_queries(self):
        from game import pg_schema
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 75)
        with self.store.connect() as db:
            rows = {r['indexname']: r['indexdef'] for r in db.execute(
                "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname=current_schema() AND indexname IN "
                "('svc_orders_due_all','svc_orders_working','svc_orders_buyer_alert','birth_stays_pair')").fetchall()}
        self.assertEqual(set(rows), {'svc_orders_due_all', 'svc_orders_working', 'svc_orders_buyer_alert', 'birth_stays_pair'})
        self.assertIn("'refund'", rows['svc_orders_due_all'])
        self.assertIn("'working'", rows['svc_orders_working'])

    def test_photo_packages_share_one_provider_query_per_connection(self):
        from game import photo_studio as P
        sm.install_own(strict=True)
        n = []
        real = P._rows
        with patch.object(P, '_rows', side_effect=lambda *x, **k: (n.append(1), real(*x, **k))[1]):
            with self.store.connect() as db:
                for pkg in P.ORDER:
                    sm.get_spec(P.CAREER, pkg)['providers'](db, sm.LISTING_MAX, 0)
        self.assertEqual(len(n), 1)


class Drain(_Helpers):
    def test_drain_settles_or_refunds_everything_held_and_is_a_dry_run_by_default(self):
        mod = _drain_module()
        a, b = self.user('dr_a'), self.user('dr_b')
        self.sell(a)
        self.sell(a, service='portrait', mode='nego')
        held = self.order(b, a)
        working = self.order(b, a)
        self.post(a, 'take', order=working['id'])
        delivered = self.order(b, a)
        self.post(a, 'take', order=delivered['id'])
        self.post(a, 'done', order=delivered['id'])
        talk = self.offer(b, a, 4000, service='portrait')
        ta, tb = self.total(a), self.total(b)
        dry = mod.drain(self.store)
        self.assertEqual((dry['before']['svc_orders.held']['n'], dry['before']['svc_orders.working']['n'],
                          dry['before']['svc_orders.delivered']['n'], dry['before']['svc_orders.talk']['n']), (1, 1, 1, 1))
        self.assertNotIn('after', dry)
        self.assertEqual(self.row(held['id'])['status'], 'held', 'a dry run changes nothing')
        out = mod.drain(self.store, write=True)
        self.assertEqual(out['left'], 0, out)
        self.assertEqual([self.row(x['id'])['status'] for x in (held, working, delivered, talk)], ['refunded', 'refunded', 'done', 'cancelled'])
        self.assertEqual(self.total(b), tb + 6000, 'held and working back in full')
        self.assertEqual(self.total(a), ta + 3000 - sm.fee_of(3000), 'delivered work paid 95 %')

    def test_drain_settles_this_builds_legacy_orders_before_an_older_build_can(self):
        from game import player_service_tasks as pst
        from game import work_visits as wv
        mod = _drain_module()
        a, b = self.user('dr_la'), self.user('dr_lb')
        self.sell(a, service='job')
        offer = self.get(b, 'dir', career='milk_tea', service='job')['items'][0]['offers'][0]
        tb = self.total(b)
        o = self.post(b, 'order', pid=self.pid(a), career='milk_tea', service='job', place=offer['place'], offer_id=offer['offer_id'],
                      rid='drain-legacy-01')['order']
        self.assertEqual(tb - self.total(b), offer['price'])
        with patch.object(wv, '_bridge', return_value=pst):
            out = mod.drain(self.store, write=True)
        self.assertEqual(out['left'], 0, out)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM work_service_orders WHERE id=?', (o['id'],)).fetchone()['status'], 'cancelled')
        self.assertEqual(self.total(b), tb, 'refunded in full')

    def test_strip_default_is_the_careers_live_does_not_know(self):
        from tests.helpers import NEWER_THAN_LIVE
        spec = importlib.util.spec_from_file_location('strip_new_careers', ROOT / 'scripts' / 'strip_new_careers.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(tuple(mod.DEFAULT_CAREERS.split(',')), NEWER_THAN_LIVE)
        doc = (ROOT / 'docs' / 'SERVICE_MARKET.md').read_text(encoding='utf-8')
        self.assertIn('## Rollback runbook', doc)
        self.assertIn('scripts/svc_drain.py --write', doc)
        self.assertIn('strip --careers reception,teller,restore,research,radio', doc)


class Schema(_Helpers):
    def raw(self):
        import psycopg
        from game import db as dbm
        c = psycopg.connect(dbm.database_url(), autocommit=True)
        c.execute('SELECT set_config(%s, %s, false)', ('search_path', self.store.pg.schema))
        self.addCleanup(c.close)
        return c

    def test_upgrade_never_waits_long_behind_a_player_transaction(self):
        import psycopg
        from game import pg_schema
        holder = self.raw()
        holder.execute('BEGIN')
        holder.execute("UPDATE work_service_orders SET fee=fee WHERE id='none'")   # a live write: ROW EXCLUSIVE on the table
        t0 = time.monotonic()
        with patch.dict(os.environ, {'MNL_DDL_LOCK_TIMEOUT': '150ms', 'MNL_DDL_LOCK_TRIES': '2', 'MNL_DDL_LOCK_LAST': '200ms'}):
            with patch('time.sleep', lambda s: None), self.assertRaises(psycopg.errors.LockNotAvailable):
                with self.store.connect() as db:
                    pg_schema.ensure(db, force=True)
        self.assertLess(time.monotonic() - t0, 10.0)
        holder.execute('SELECT 1')   # the player's transaction was never touched
        holder.execute('ROLLBACK')
        with patch.dict(os.environ, {'MNL_DDL_LOCK_TIMEOUT': '2s'}):
            with self.store.connect() as db:
                self.assertTrue(pg_schema.ensure(db, force=True))


class Server(_Helpers):
    def test_light_routes_are_three_separate_conditions(self):
        src = (ROOT / 'server.py').read_text(encoding='utf-8')
        self.assertNotIn('startswith("/api/radio/" or', src)
        self.assertIn('route.startswith("/api/radio/") or route.startswith("/api/townfair/") or route=="/api/admin/radio"', src)
        self.assertIn('marriage.act(self.server.store,token,route[len("/api/marriage/"):],data,ip=self.client_ip())', src)
