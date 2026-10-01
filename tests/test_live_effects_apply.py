"""🧧 Live rewards paid into the save (game/live_effects.py, /api/bootstrap, POST /api/live/effects): a row the
live service granted (live/effects.py grant) is paid exactly once, through the game's own command path, with a
wallet-history row; retries, tabs, crashes and pruned receipts never pay twice; a client cannot send it."""
import asyncio
import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from game import live_effects as lfx
from game.engine import GameError, migrate_state, validate_state
from game.storage import Store
from server import GameServer


class Base(unittest.TestCase):
    story = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'g.db'
        self.store = Store(self.path, story=self.story)
        self.addCleanup(self.store.close_pool)

    def guest(self):
        token, _, _ = self.store.session()
        return token

    def state(self, tok):
        return self.store.read(tok)[0]

    def wallet(self, tok):
        return self.state(tok)['journey']['wallet']

    def rows(self, tok):
        return [r for r in self.state(tok)['journey']['history'] if r['label'] == lfx.LABELS['envelope']]

    def grant(self, tok, eid='env:walk:boho:1:ab12cd34', amount=5, kind='coins', src='envelope'):
        """What live/effects.py grant writes."""
        sid = self.store.key(tok)
        self.store.transaction(lambda db: db.execute(
            "INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?, ?, ?, ?, ?, 'pending', ?)",
            (eid, sid, kind, amount, json.dumps(dict(src=src)), time.time())))
        return eid

    def load(self, tok):
        return lfx.on_load(self.store, tok, self.state(tok))

    def status(self, eid):
        with self.store.connect() as db:
            r = db.execute('SELECT status FROM live_effects WHERE id=?', (eid,)).fetchone()
        return r['status'] if r else None


class PaidOnce(Base):
    def test_paid_once_with_a_history_row_and_a_valid_save(self):
        tok = self.guest()
        w0, rev0 = self.wallet(tok), self.store.read(tok)[1]
        eid = self.grant(tok)
        self.assertEqual((self.wallet(tok), self.store.read(tok)[1]), (w0, rev0), 'granting never touches the save')
        self.assertTrue(self.load(tok))
        self.assertEqual(self.wallet(tok), w0 + 5)
        rows = self.rows(tok)
        self.assertEqual([(r['amount'], r['kind'], r['career']) for r in rows], [(5, 'life', None)])
        self.assertEqual(self.status(eid), 'applied')
        self.assertFalse(self.load(tok))
        self.assertEqual(self.wallet(tok), w0 + 5)
        s = self.state(tok)
        validate_state(migrate_state(s))
        self.assertEqual(s['journey']['live_fx'], [lfx.short(eid)])

    def test_retry_crash_and_pruned_receipts(self):
        tok = self.guest()
        w0 = self.wallet(tok)
        eid = self.grant(tok)
        self.load(tok)
        again = self.store.command(tok, lfx.RID + lfx.short(eid), None, None, lfx.ACTION, dict(id=eid, kind='coins', amount=5, src='envelope'), internal=True)
        self.assertTrue(again['replayed'])
        sid = self.store.key(tok)
        self.store.transaction(lambda db: db.execute("UPDATE live_effects SET status='pending', applied_at=NULL WHERE id=?", (eid,)))
        self.store.transaction(lambda db: db.execute('DELETE FROM receipts WHERE sid=?', (sid,)))
        self.assertTrue(self.load(tok))   # the no-op command still went through
        self.assertEqual(self.wallet(tok), w0 + 5)
        self.assertEqual(len(self.rows(tok)), 1)
        self.assertEqual(self.status(eid), 'applied')

    def test_two_tabs_at_once(self):
        tok = self.guest()
        w0 = self.wallet(tok)
        self.grant(tok)
        self.grant(tok, eid='env:walk:chodem:2:00ff00ff', amount=7)
        state = self.state(tok)
        errors = []

        def tab():
            try:
                lfx.on_load(self.store, tok, state)
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=tab) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(self.wallet(tok), w0 + 12)
        self.assertEqual(len(self.rows(tok)), 2)

    def test_the_real_grant_then_load(self):
        from live.db import PgDB, SqliteDB
        from live.effects import grant
        tok = self.guest()
        w0 = self.wallet(tok)
        sid = self.store.key(tok)

        async def run():
            pg = self.store.pg
            db = PgDB(pg.url, pg.schema) if pg else SqliteDB(str(self.path))
            try:
                a = await grant(db, sid, 'coins', 6, key='env:walk:boho:1:aaaa0001', data=dict(src='envelope'), cap=10)
                b = await grant(db, sid, 'coins', 6, key='env:walk:boho:1:aaaa0002', data=dict(src='envelope'), cap=10)   # over the cap
                return a, b
            finally:
                await db.close()
        self.assertEqual(asyncio.run(run()), (True, False))
        self.assertTrue(self.load(tok))
        self.assertEqual(self.wallet(tok), w0 + 6)

    def test_spirit_and_unknown_kinds(self):
        tok = self.guest()
        s = self.state(tok)
        before = (s['journey'].get('life') or {}).get('spirit')
        self.grant(tok, eid='date:1:x', kind='spirit', amount=3, src='date')
        self.grant(tok, eid='date:1:y', kind='closeness', amount=2, src='date')   # not paid by this build: stays pending
        self.assertTrue(self.load(tok))
        after = (self.state(tok)['journey'].get('life') or {}).get('spirit')
        if isinstance(before, int):
            self.assertEqual(after, min(100, before + 3))
        self.assertEqual(self.status('date:1:x'), 'applied')
        self.assertEqual(self.status('date:1:y'), 'pending')

    def test_a_client_cannot_send_it_and_amounts_are_checked(self):
        tok = self.guest()
        rev = self.store.read(tok)[1]
        with self.assertRaises(GameError) as e:
            self.store.command(tok, 'client-req-0001', rev, None, lfx.ACTION, dict(id='env:x:1', kind='coins', amount=5))
        self.assertEqual(e.exception.code, 'forbidden')
        for bad in (dict(id='env:x:1', kind='coins', amount=lfx.AMOUNT_MAX + 1), dict(id='bad id!', kind='coins', amount=1),
                    dict(id='env:x:1', kind='gold', amount=1)):
            with self.assertRaises(GameError, msg=bad):
                self.store.command(tok, 'live-badbadbad01', None, None, lfx.ACTION, bad, internal=True)

    def test_bad_lists_in_a_save_are_refused(self):
        s = migrate_state(self.state(self.guest()))
        for bad in ('x', ['nothex'], ['0123456789abcdef'] * 2, ['%016x' % i for i in range(lfx.KEPT + 1)]):
            s['journey']['live_fx'] = bad
            with self.assertRaises(GameError):
                validate_state(s)
        s['journey']['live_fx'] = ['0123456789abcdef']
        validate_state(s)

    def test_only_its_own_save(self):
        a, b = self.guest(), self.guest()
        wb = self.wallet(b)
        self.grant(a)
        self.assertFalse(self.load(b))
        self.assertEqual(self.wallet(b), wb)



class DateRewards(Base):
    """💕 A date's spirit (live/dating.py grants 'spirit' with src 'date'): paid once, clamped, gone with the save."""

    def spirit(self, tok):
        return migrate_state(self.state(tok))['journey']['life']['spirit']

    def test_date_spirit_once_and_clamped(self):
        tok = self.guest()
        before = self.spirit(tok)
        self.grant(tok, eid='date:0123456789ab:aaaaaaaaaaaaaaaa', kind='spirit', amount=5, src='date')
        self.assertTrue(self.load(tok))
        self.assertEqual(self.spirit(tok), min(100, before + 5))
        self.assertFalse(self.load(tok))
        self.assertEqual(self.spirit(tok), min(100, before + 5))
        self.grant(tok, eid='date:0123456789ac:aaaaaaaaaaaaaaaa', kind='spirit', amount=1000, src='date')
        self.load(tok)
        self.assertEqual(self.spirit(tok), 100)
        validate_state(migrate_state(self.state(tok)))

    def test_a_beer_takes_a_little_spirit_once(self):
        """1.3.0: a beer at a wedding party is a negative spirit row (live/wedding.py wed_eat): paid once, clamped at 0;
        more than SPIRIT_DOWN, or a negative row of another kind, is refused and stays pending."""
        tok = self.guest()
        before = self.spirit(tok)
        self.grant(tok, eid='wbeer:7:aaaaaaaaaaaaaaaaaaaaaaaa:1', kind='spirit', amount=-1, src='wed_beer')
        self.assertTrue(self.load(tok))
        self.assertEqual(self.spirit(tok), max(0, before - 1))
        self.assertFalse(self.load(tok))
        self.assertEqual(self.spirit(tok), max(0, before - 1))
        self.grant(tok, eid='wbeer:7:bad:1', kind='spirit', amount=lfx.SPIRIT_DOWN - 1, src='wed_beer')
        self.grant(tok, eid='wbeer:7:bad:2', kind='coins', amount=-5, src='wed_beer')
        self.load(tok)
        self.assertEqual((self.status('wbeer:7:bad:1'), self.status('wbeer:7:bad:2')), ('pending', 'pending'))
        self.assertEqual(self.spirit(tok), max(0, before - 1))
        validate_state(migrate_state(self.state(tok)))

    def test_live_grant_refuses_negative_but_a_little_spirit(self):
        from live.effects import grant

        async def run():
            for kind, amount in (('coins', -1), ('spirit', 0), ('spirit', lfx.SPIRIT_DOWN - 1)):
                with self.assertRaises(ValueError):
                    await grant(None, 'sid', kind, amount, key='k:1')
        asyncio.run(run())

    def test_forget(self):
        tok = self.guest()
        self.grant(tok, eid='date:1:forget', kind='spirit', src='date')
        lfx.forget(self.store, tok)
        self.assertIsNone(self.status('date:1:forget'))

    def test_schema_7_has_the_date_tables(self):
        from game import pg_schema
        self.assertGreaterEqual(pg_schema.SCHEMA_VERSION, 7)   # 7: live_dates, date_bonds (1.0.1)
        for name in ('live_dates', 'date_bonds'):
            self.assertIn(f'CREATE TABLE IF NOT EXISTS {name}', pg_schema.TABLES_DDL)
            self.assertIn(name, pg_schema.TABLE)
        with self.store.connect() as db:
            for name in ('live_dates', 'date_bonds'):
                db.execute(f'SELECT 1 FROM {name} LIMIT 1').fetchall()


class NotStory(Base):
    story = False

    def test_stays_pending(self):
        tok = self.guest()
        w0 = self.wallet(tok)
        eid = self.grant(tok)
        self.assertFalse(self.load(tok))
        self.assertEqual(self.wallet(tok), w0)
        self.assertEqual(self.status(eid), 'pending')


class Http(Base):
    """/api/bootstrap pays on load; POST /api/live/effects pays now (the stroll, right after an envelope)."""

    def setUp(self):
        super().setUp()
        self.server = GameServer(('127.0.0.1', 0), self.store)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def req(self, method, path, body=None, cookie=None, csrf=None):
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=20)
        headers = {'Host': f'127.0.0.1:{self.server.server_address[1]}'}
        if cookie:
            headers['Cookie'] = cookie
        if csrf:
            headers['X-Game-CSRF'] = csrf
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers['Content-Type'] = 'application/json'
        c.request(method, path, data, headers)
        r = c.getresponse()
        out = (r.status, json.loads(r.read() or b'{}'), r.getheader('Set-Cookie'))
        c.close()
        return out

    def test_bootstrap_and_post(self):
        st, boot, cookie = self.req('GET', '/api/bootstrap?lite=1')
        self.assertEqual(st, 200)
        cookie = cookie.split(';', 1)[0]
        tok = cookie.split('=', 1)[1]
        w0 = boot['state']['journey']['wallet']
        self.grant(tok)
        st, out, _ = self.req('POST', '/api/live/effects', {}, cookie, boot['csrf'])
        self.assertEqual(st, 200, out)
        self.assertTrue(out['paid'])
        self.assertEqual(out['state']['journey']['wallet'], w0 + 5)
        st, out, _ = self.req('POST', '/api/live/effects', {}, cookie, boot['csrf'])
        self.assertFalse(out['paid'])
        self.grant(tok, eid='env:walk:boho:3:cafe0003', amount=4)
        st, boot2, _ = self.req('GET', '/api/bootstrap?lite=1', cookie=cookie)
        self.assertEqual(boot2['state']['journey']['wallet'], w0 + 9)
        st, out, _ = self.req('POST', '/api/live/effects', {}, cookie, None)
        self.assertEqual(st, 403)   # no CSRF header


if __name__ == '__main__':
    unittest.main()
