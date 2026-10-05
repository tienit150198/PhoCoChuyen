"""PostgreSQL is required; local namespace paths never hold database files."""
import asyncio
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from game import db as dbm
from game.storage import Store
from live.db import open_db


class TestEnvironmentIsolationTests(unittest.TestCase):
    def test_file_database_url_cannot_override_explicit_test_endpoint(self):
        import server

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("DATABASE_URL=postgresql://file-configured@127.0.0.1:1/ordinary\nMNL_ISOLATION_EXAMPLE=loaded\n", encoding="utf-8")
            with patch.dict(os.environ, {"TEST_DATABASE_URL": "postgresql://localhost/isolated"}, clear=True), patch.object(server, "ROOT", root):
                server.load_env()
                self.assertNotIn("DATABASE_URL", os.environ)
                self.assertEqual(os.environ["MNL_ISOLATION_EXAMPLE"], "loaded")

    def test_explicit_process_database_url_is_preserved(self):
        import server

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text("DATABASE_URL=postgresql://file-configured@127.0.0.1:1/ordinary\n", encoding="utf-8")
            values = {"DATABASE_URL": "postgresql://localhost/explicit", "TEST_DATABASE_URL": "postgresql://localhost/isolated"}
            with patch.dict(os.environ, values, clear=True), patch.object(server, "ROOT", root):
                server.load_env()
                self.assertEqual(os.environ["DATABASE_URL"], values["DATABASE_URL"])

    def test_subprocess_server_import_keeps_test_endpoint_isolated(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "server.py").write_bytes((root / "server.py").read_bytes())
            (folder / ".env").write_text("DATABASE_URL=postgresql://file-configured@127.0.0.1:1/ordinary\n", encoding="utf-8")
            python_path = os.pathsep.join(filter(None, (str(root), os.environ.get("PYTHONPATH", ""))))
            env = dict(os.environ, TEST_DATABASE_URL="postgresql://localhost/isolated", PYTHONPATH=python_path, MNL_PG_TEST_KEEP="1")
            env.pop("DATABASE_URL", None)
            result = subprocess.run([sys.executable, "-c", "import os, server; from game import db; assert 'DATABASE_URL' not in os.environ; assert db.test_mode()"],
                                    cwd=folder, env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


@unittest.skipUnless(sys.platform == "win32", "Windows asyncio policy")
class WindowsAsyncTests(unittest.TestCase):
    def test_postgres_async_uses_selector_policy(self):
        self.assertIsInstance(asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy)


class DatabaseConfigTests(unittest.TestCase):
    def test_missing_database_url_is_rejected(self):
        with patch.dict(os.environ, {"DATABASE_URL": "", "TEST_DATABASE_URL": ""}):
            with self.assertRaisesRegex(SystemExit, "DATABASE_URL.*required"):
                dbm.database_url()

    def test_missing_url_does_not_create_a_local_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "game"
            with patch.dict(os.environ, {"DATABASE_URL": "", "TEST_DATABASE_URL": ""}):
                with self.assertRaises(SystemExit):
                    Store(path)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_invalid_test_url_is_rejected(self):
        with patch.dict(os.environ, {"DATABASE_URL": "", "TEST_DATABASE_URL": "file:game.db"}):
            with self.assertRaisesRegex(SystemExit, "TEST_DATABASE_URL"):
                dbm.database_url()

    def test_malformed_postgres_url_is_rejected_without_exposing_password(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://player:private-password@localhost:invalid/game", "TEST_DATABASE_URL": ""}):
            with self.assertRaises(SystemExit) as caught:
                dbm.database_url()
        self.assertNotIn("private-password", str(caught.exception))

    def test_database_url_takes_precedence_over_test_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": " postgresql://localhost/game ", "TEST_DATABASE_URL": "postgresql://localhost/test"}):
            self.assertEqual(dbm.database_url(), "postgresql://localhost/game")
            self.assertFalse(dbm.test_mode())

    def test_live_service_requires_a_postgres_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "game"
            path.touch()
            cfg = SimpleNamespace(db_url=None, db_path=str(path), db_schema=None, pool_max=2)
            with self.assertRaisesRegex(SystemExit, "DATABASE_URL"):
                asyncio.run(open_db(cfg))


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL") and not os.environ.get("DATABASE_URL"), "requires isolated TEST_DATABASE_URL")
class PostgresNamespaceTests(unittest.TestCase):
    def test_live_service_queries_postgres_async(self):
        async def query():
            db = await open_db(SimpleNamespace(db_url=os.environ["TEST_DATABASE_URL"], db_schema=None, pool_max=2))
            try:
                return await db.fetchval("SELECT ? AS value", (42,))
            finally:
                await db.close()

        self.assertEqual(asyncio.run(query()), 42)

    def test_store_and_shared_limits_create_no_database_files(self):
        import server

        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "game")
            try:
                limits = server.SharedLimits(store)
                self.assertTrue(limits.hit("ai:postgres-only", 1, 60))
                self.assertFalse(limits.hit("ai:postgres-only", 1, 60))
                self.assertEqual(list(Path(tmp).iterdir()), [])
                with store.connect() as conn:
                    self.assertEqual(conn.dialect, "pg")
            finally:
                store.close_pool()


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL") and not os.environ.get("DATABASE_URL"), "requires isolated TEST_DATABASE_URL")
class PostgresHousekeepingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "housekeeping")

    def tearDown(self):
        self.store.close_pool()
        self.tmp.cleanup()

    def guest(self, age):
        with patch.dict(os.environ, {"LAZY_SAVES": "1"}):
            token, csrf, _ = self.store.session()
        sid = self.store.digest(token)
        with self.store.connect() as db:
            db.execute(f"UPDATE sessions SET updated_at={dbm.UTC_INTERVAL_TEXT} WHERE sid=?", (age, sid))
        return token, sid, csrf

    def receipt(self, sid, request_id, age):
        with self.store.connect() as db:
            db.execute(f"INSERT INTO receipts(sid,request_id,request_hash,result,created_at) VALUES(?,?,?,?,{dbm.UTC_INTERVAL_TEXT})",
                       (sid, request_id, "hash", "{}", age))

    def test_fractional_receipt_retention_uses_the_postgres_utc_clock(self):
        _, sid, _ = self.guest("-1 hour")
        self.receipt(sid, "expired", "-13 hours")
        self.receipt(sid, "retained", "-11 hours")
        self.assertEqual(self.store.prune_receipts(days=.5, keep=10), 1)
        with self.store.connect() as db:
            self.assertEqual([r[0] for r in db.execute("SELECT request_id FROM receipts")], ["retained"])

    def test_fractional_guest_retention_removes_only_expired_unused_saves(self):
        _, old_sid, _ = self.guest("-13 hours")
        _, recent_sid, _ = self.guest("-11 hours")
        self.assertEqual(self.store.prune_guests(days=.5), 1)
        with self.store.connect() as db:
            self.assertEqual([r[0] for r in db.execute("SELECT sid FROM sessions")], [recent_sid])
            self.assertIsNone(db.execute("SELECT 1 FROM sessions WHERE sid=?", (old_sid,)).fetchone())

    def test_housekeeping_preserves_accounts_and_recent_devices(self):
        _, expired_sid, _ = self.guest("-181 days")
        _, recent_sid, _ = self.guest("-179 days")
        _, owned_sid, csrf = self.guest("-181 days")
        with self.store.connect() as db:
            db.execute("INSERT INTO accounts(username,display,pw,sid) VALUES(?,?,?,?)", ("housekeep", "Housekeep", "test-only", owned_sid))
            for name, age in (("expired-device", "-181 days"), ("recent-device", "-179 days")):
                db.execute(f"INSERT INTO logins(token,sid,csrf,seen_at) VALUES(?,?,?,{dbm.UTC_INTERVAL_TEXT})", (name, owned_sid, csrf, age))
        self.receipt(owned_sid, "expired-receipt", "-4 days")
        self.receipt(owned_sid, "recent-receipt", "-2 days")
        self.assertEqual(self.store.prune(idle_days=180, receipt_days=3), dict(receipts=1, sessions=1))
        with self.store.connect() as db:
            self.assertCountEqual([r[0] for r in db.execute("SELECT sid FROM sessions")], [recent_sid, owned_sid])
            self.assertEqual([r[0] for r in db.execute("SELECT token FROM logins")], ["recent-device"])
            self.assertEqual([r[0] for r in db.execute("SELECT request_id FROM receipts")], ["recent-receipt"])
            self.assertIsNone(db.execute("SELECT 1 FROM sessions WHERE sid=?", (expired_sid,)).fetchone())

    def test_login_seen_time_refreshes_only_after_one_hour(self):
        stale_token, stale_sid, stale_csrf = self.guest("-1 day")
        recent_token, recent_sid, recent_csrf = self.guest("-1 day")
        with self.store.connect() as db:
            for token, sid, csrf, age in ((stale_token, stale_sid, stale_csrf, "-2 hours"), (recent_token, recent_sid, recent_csrf, "-30 minutes")):
                db.execute(f"INSERT INTO logins(token,sid,csrf,seen_at) VALUES(?,?,?,{dbm.UTC_INTERVAL_TEXT})", (self.store.digest(token), sid, csrf, age))
            recent_before = db.execute("SELECT seen_at FROM logins WHERE token=?", (self.store.digest(recent_token),)).fetchone()[0]
        self.assertEqual(self.store.session(stale_token), (stale_token, stale_csrf, False))
        self.assertEqual(self.store.session(recent_token), (recent_token, recent_csrf, False))
        with self.store.connect() as db:
            stale_is_recent = db.execute(f"SELECT seen_at>{dbm.UTC_INTERVAL_TEXT} FROM logins WHERE token=?", ("-1 minute", self.store.digest(stale_token))).fetchone()[0]
            recent_after = db.execute("SELECT seen_at FROM logins WHERE token=?", (self.store.digest(recent_token),)).fetchone()[0]
        self.assertTrue(stale_is_recent)
        self.assertEqual(recent_after, recent_before)
