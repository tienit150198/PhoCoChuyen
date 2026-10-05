"""Character renames update account display names without changing login identity."""
import asyncio
import concurrent.futures
import json
import threading
import uuid
from unittest.mock import patch

from game import accounts, friends, marriage, pg_schema
from tests.test_marriage import Base


class PlayerNames(Base):
    def setUp(self):
        super().setUp()
        self.a, self.b = self.user('nameowner'), self.user('namefriend')
        self.befriend(self.sid(self.a), self.sid(self.b))
        self.code(self.a)
        self.code(self.b)

    def rename(self, name, token=None, request=None):
        token = token or self.a
        return self.store.command(token, request or str(uuid.uuid4()), self.store.read(token)[1], None, 'settings', dict(name=name))

    def identity(self):
        with self.store.connect() as db:
            account = dict(db.execute('SELECT uid,username,pw,sid FROM accounts WHERE sid=?', (self.sid(self.a),)).fetchone())
            logins = [dict(r) for r in db.execute('SELECT token,sid,csrf FROM logins WHERE sid=? ORDER BY token', (self.sid(self.a),)).fetchall()]
            profile = dict(db.execute('SELECT name,name_key FROM profiles WHERE sid=?', (self.sid(self.a),)).fetchone())
        return account, logins, profile

    def test_registered_rename_updates_all_name_readers_in_both_store_paths(self):
        from live import auth
        store = self.store
        class AsyncRead:
            async def fetchrow(self, sql, args=()):
                with store.connect() as db:
                    row = db.execute(sql, args).fetchone()
                    return dict(row) if row else None
        original = self.identity()
        for tries, name in ((4, 'Lan Anh'), (0, 'Minh Tú')):
            with self.subTest(tries=tries), patch('game.storage.OPTIMISTIC_TRIES', tries):
                result = self.rename(name)
                self.assertEqual(result['state']['name'], name)
                self.assertEqual(accounts.status(self.store, self.a)['display'], name)
                with self.store.connect() as db:
                    self.assertEqual(marriage._display(db, self.sid(self.a)), name)
                    self.assertEqual(friends._card(db, self.sid(self.b), self.sid(self.a))['name'], name)
                self.assertEqual(asyncio.run(auth.profile(AsyncRead(), self.sid(self.a))).name, name)
                self.assertEqual(self.identity(), original)

    def test_same_name_and_receipt_replay_do_not_notify_again(self):
        from game import live_chat
        with patch.object(live_chat, 'notify', wraps=live_chat.notify) as notify:
            request = str(uuid.uuid4())
            self.rename('Tên Mới', request=request)
            self.rename('Tên Mới', request=request)
            self.rename('Tên Mới')
            self.assertEqual(notify.call_count, 1)
            self.assertEqual(notify.call_args.args[1], dict(op='name', sid=self.sid(self.a)))

    def test_notification_failure_rolls_back_name_save_and_credentials(self):
        for tries in (4, 0):
            with self.subTest(tries=tries), patch('game.storage.OPTIMISTIC_TRIES', tries):
                old = self.store.read(self.a)[:2], accounts.status(self.store, self.a), self.identity()
                with patch('game.live_chat.notify', side_effect=RuntimeError('notification failed')):
                    with self.assertRaises(RuntimeError):
                        self.rename('Không Được Ghi')
                self.assertEqual((self.store.read(self.a)[:2], accounts.status(self.store, self.a), self.identity()), old)

    def set_legacy_name(self, token, name):
        with self.store.connect() as db:
            state = json.loads(db.execute('SELECT state FROM sessions WHERE sid=?', (self.sid(token),)).fetchone()['state'])
            state['name'] = name
            db.execute('UPDATE sessions SET state=? WHERE sid=?', (json.dumps(state), self.sid(token)))

    def upgrade(self, force=False):
        with self.store.connect() as db:
            return pg_schema.ensure(db, force=force)

    def test_schema22_repairs_existing_names_once_and_preserves_identity(self):
        original = self.identity()
        self.set_legacy_name(self.a, 'Tên Đã Đổi')
        self.set_legacy_name(self.b, 'Mây')
        with self.store.connect() as db:
            db.execute("UPDATE mnl_meta SET value='21' WHERE key='schema_version'")
        self.assertTrue(self.upgrade())
        self.assertEqual(accounts.status(self.store, self.a)['display'], 'Tên Đã Đổi')
        self.assertEqual(accounts.status(self.store, self.b)['display'], 'Namefriend')
        self.assertEqual(self.identity(), original)
        self.assertFalse(self.upgrade())
        with self.store.connect() as db:
            db.execute('UPDATE accounts SET display=? WHERE sid=?', ('Keep Later Value', self.sid(self.a)))
        self.upgrade(force=True)
        self.assertEqual(accounts.status(self.store, self.a)['display'], 'Keep Later Value')

    def test_schema22_skips_blank_and_missing_names(self):
        self.set_legacy_name(self.a, '   ')
        self.set_legacy_name(self.b, None)
        with self.store.connect() as db:
            db.execute("UPDATE mnl_meta SET value='21' WHERE key='schema_version'")
        self.upgrade()
        self.assertEqual(accounts.status(self.store, self.a)['display'], 'Nameowner')
        self.assertEqual(accounts.status(self.store, self.b)['display'], 'Namefriend')

    def test_schema_upgrade_releases_ddl_locks_before_waiting_for_active_player(self):
        locked, repairing = threading.Event(), threading.Event()
        with self.store.connect() as db:
            db.execute("UPDATE mnl_meta SET value='18' WHERE key='schema_version'")
        sid = self.sid(self.a)
        original = pg_schema.repair_character_names
        def player():
            with self.store.connect() as db, db.raw.transaction():
                db.raw.execute("SET LOCAL lock_timeout='2s'")
                db.execute('SELECT sid FROM sessions WHERE sid=? FOR UPDATE', (sid,))
                locked.set()
                self.assertTrue(repairing.wait(8))
                db.execute('UPDATE accounts SET updated_at=updated_at WHERE sid=?', (sid,))
        def repair(db):
            repairing.set()
            return original(db)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            active = pool.submit(player)
            self.assertTrue(locked.wait(8))
            with patch.object(pg_schema, 'repair_character_names', repair):
                upgrade = pool.submit(self.upgrade)
                active.result(timeout=10)
                self.assertTrue(upgrade.result(timeout=10))
        with self.store.connect() as db:
            self.assertEqual(pg_schema.installed_version(db), 22)

    def test_failed_name_repair_can_resume_after_ddl_commits(self):
        with self.store.connect() as db:
            db.execute("UPDATE mnl_meta SET value='18' WHERE key='schema_version'")
        with patch.object(pg_schema, 'repair_character_names', side_effect=RuntimeError('retry repair')):
            with self.assertRaisesRegex(RuntimeError, 'retry repair'):
                self.upgrade()
        with self.store.connect() as db:
            self.assertEqual(pg_schema.installed_version(db), 21)
        self.assertTrue(self.upgrade())

    def test_repair_waiting_for_concurrent_rename_uses_locked_current_save(self):
        entered, release, repairing = threading.Event(), threading.Event(), threading.Event()
        backend = []
        original = accounts.sync_character_name
        def paused(db, sid, before, after):
            original(db, sid, before, after)
            entered.set()
            self.assertTrue(release.wait(8))
        def repair():
            with self.store.connect() as db:
                backend.append(db.raw.info.backend_pid)
                repairing.set()
                pg_schema.repair_character_names(db)
        with patch.object(accounts, 'sync_character_name', paused), concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            change = pool.submit(self.rename, 'Tên Vừa Đổi')
            self.assertTrue(entered.wait(8))
            repair_task = pool.submit(repair)
            try:
                self.assertTrue(repairing.wait(8))
                blocked = False
                for _ in range(100):
                    with self.store.connect() as db:
                        row = db.execute('SELECT wait_event_type FROM pg_stat_activity WHERE pid=?', (backend[0],)).fetchone()
                    if row and row['wait_event_type'] == 'Lock':
                        blocked = True
                        break
                    threading.Event().wait(.01)
                self.assertTrue(blocked, 'Repair must wait for the active session rename transaction')
            finally:
                release.set()
            change.result(timeout=10)
            repair_task.result(timeout=10)
        self.assertEqual(self.state(self.a)['name'], 'Tên Vừa Đổi')
        self.assertEqual(accounts.status(self.store, self.a)['display'], 'Tên Vừa Đổi')

    def test_other_settings_do_not_override_account_name(self):
        with patch('game.live_chat.notify') as notify:
            self.store.command(self.a, str(uuid.uuid4()), self.store.read(self.a)[1], None, 'settings', dict(musicVolume=25))
            notify.assert_not_called()
        self.assertEqual(accounts.status(self.store, self.a)['display'], 'Nameowner')
