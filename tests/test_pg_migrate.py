"""scripts/pg_migrate.py: copy, delta sync (updates, inserts, deletes), verify (a flipped byte),
resume after an interrupt, reverse-sync, the cutover guard. Needs PostgreSQL:
TEST_DATABASE_URL (or PG_MIGRATE_TEST_URL); skipped otherwise. Each test works in its own
PostgreSQL schemas (game tables + bookkeeping), dropped afterwards."""
import contextlib
import io
import json
import os
import secrets
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
URL = (os.environ.get("PG_MIGRATE_TEST_URL") or os.environ.get("TEST_DATABASE_URL") or "").strip()

try:
    import psycopg  # noqa: F401
    import pg_migrate
    import pg_rehearsal
except ImportError:  # no psycopg: skipped below
    psycopg = None

SKIP = not URL or psycopg is None


def state(n, tick=0):
    return json.dumps(dict(tick=tick, careers={f"c{i}": dict(feed=["phở bò tái " * 40] * 20) for i in range(n)}), ensure_ascii=False)


@unittest.skipIf(SKIP, "TEST_DATABASE_URL is not set (or psycopg is missing)")
class PgMigrateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "game.sqlite3")
        self.limits = str(Path(self.tmp.name) / "game-limits.sqlite3")
        tag = secrets.token_hex(4)
        self.schema, self.meta = f"mig_{tag}", f"migmeta_{tag}"
        self.old_meta = pg_migrate.META
        pg_migrate.META = self.meta
        sep = "&" if "?" in URL else "?"
        self.url = URL + sep + "options=" + quote(f"-csearch_path={self.schema}")
        with psycopg.connect(URL, autocommit=True) as c:
            c.execute(f'CREATE SCHEMA "{self.schema}"')
        s = sqlite3.connect(self.db, isolation_level=None)
        s.execute("PRAGMA journal_mode=WAL")
        s.executescript(pg_rehearsal.SQLITE_DDL)
        s.execute("BEGIN")
        for i in range(12):
            sid = f"{i:02d}" + secrets.token_hex(31)
            s.execute("INSERT INTO sessions(sid,csrf,revision,state,updated_at) VALUES(?,?,?,?,?)",
                      (sid, "csrf", i + 1, state(i % 4 + 1), "2026-09-29 10:00:00"))
            for j in range(5):
                s.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)", (sid, f"r{j}", "h", '{"ok":true}'))
                s.execute("INSERT INTO archive(sid,career,kind,seq,day,row,created_at) VALUES(?,?,?,?,?,?,?)",
                          (sid, "cafe", "feed", j, j, '{"t":"bán được 3 ly"}', 1727600000.0))
        s.execute("INSERT INTO accounts(username,display,pw,sid) VALUES('an','An','x',(SELECT min(sid) FROM sessions))")
        s.execute("INSERT INTO logins(token,sid,csrf) VALUES('tok1',(SELECT min(sid) FROM sessions),'c')")
        for k in range(5):
            s.execute("INSERT INTO player_feedback(sid,kind,text,created_at,updated_at) VALUES('x','bug','lỗi',1.5,1.5)")
        s.execute("DELETE FROM player_feedback WHERE id=5")  # sqlite_sequence stays at 5
        s.execute("INSERT INTO inbox(pid,kind,text,at) VALUES('p1','gift','quà',1727600000.25)")
        # played today before the cutover: a rollback's upsert of this save must not trip the stat trigger
        s.execute("INSERT OR IGNORE INTO stat_active(day,sid) VALUES(date('now','+7 hours'),(SELECT min(sid) FROM sessions))")
        s.execute("COMMIT")
        s.close()
        lim = sqlite3.connect(self.limits, isolation_level=None)
        lim.executescript(pg_rehearsal.LIMITS_DDL)
        lim.executemany("INSERT INTO hits(k,at) VALUES(?,?)", [("ai:1", 1.0), ("ai:1", 1.0), ("fb:2", 2.5)])
        lim.close()

    def tearDown(self):
        pg_migrate.META = self.old_meta
        with psycopg.connect(URL, autocommit=True) as c:
            c.execute(f'DROP SCHEMA IF EXISTS "{self.schema}" CASCADE')
            c.execute(f'DROP SCHEMA IF EXISTS "{self.meta}" CASCADE')
        self.tmp.cleanup()

    # helpers
    def run_tool(self, *args, db=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            rc = pg_migrate.main([args[0], "--sqlite", db or self.db, "--limits", self.limits, "--pg", self.url, "--json", *args[1:]])
        events = [json.loads(line) for line in out.getvalue().splitlines() if line.startswith("{")]
        result = ([e for e in events if e["event"] == "result"] or [{}])[-1]
        return rc, result, events

    def ok(self, *args, **kw):
        rc, result, events = self.run_tool(*args, **kw)
        self.assertEqual(rc, 0, [e for e in events if e["event"] in ("error", "verify") and (e.get("mismatch") or e["event"] == "error")])
        return result

    def sql(self, q, args=None):
        with psycopg.connect(self.url, autocommit=True) as c:
            cur = c.execute(q, args)
            return cur.fetchall() if cur.description else None

    def lite(self):
        s = sqlite3.connect(self.db, isolation_level=None)
        return s

    def copied(self):
        self.ok("init")
        self.ok("copy")

    # tests
    def test_copy_then_full_verify(self):
        self.copied()
        self.assertEqual(self.sql("SELECT count(*) FROM sessions")[0][0], 12)
        self.assertEqual(self.sql("SELECT count(*) FROM hits")[0][0], 3)
        r = self.ok("verify")
        self.assertEqual(r["mismatches"], 0)
        again = self.ok("copy")  # idempotent: already copied tables are skipped
        self.assertEqual(again["rows"], 0)

    def test_sync_updates_inserts_deletes_and_converges(self):
        self.copied()
        s = self.lite()
        sids = [r[0] for r in s.execute("SELECT sid FROM sessions ORDER BY sid")]
        s.execute("UPDATE sessions SET state=?,revision=revision+1 WHERE sid=?", (state(2, tick=9), sids[0]))
        s.execute("INSERT INTO sessions(sid,csrf,state) VALUES('new-save','c',?)", (state(1),))
        s.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)", (sids[0], "r9", "h", "{}"))
        s.execute("DELETE FROM receipts WHERE sid=? AND request_id='r0'", (sids[1],))          # prune
        for t in ("archive", "receipts", "logins", "accounts"):
            s.execute(f"DELETE FROM {t} WHERE sid=?", (sids[2],))
        s.execute("DELETE FROM sessions WHERE sid=?", (sids[2],))                            # erased save
        s.execute("DELETE FROM archive WHERE sid=? AND seq>=3", (sids[3],))                  # history erased...
        s.execute("UPDATE archive SET row='{\"t\":\"khác\"}' WHERE sid=? AND seq=0", (sids[3],))
        s.execute("UPDATE logins SET seen_at='2026-09-30 01:00:00'")
        s.execute("UPDATE player_feedback SET status='done' WHERE id=1")                    # trigger -> stat_fb_ack
        s.execute("DELETE FROM inbox")
        s.close()
        lim = sqlite3.connect(self.limits, isolation_level=None)
        lim.execute("DELETE FROM hits WHERE k='fb:2'")
        lim.close()
        r = self.ok("sync")
        self.assertGreater(r["upserted"], 0)
        self.assertGreater(r["deleted"], 0)
        self.assertEqual(self.ok("verify")["mismatches"], 0)
        self.assertEqual(self.sql("SELECT count(*) FROM sessions WHERE sid=%s", (sids[2],))[0][0], 0)
        self.assertEqual(self.sql("SELECT count(*) FROM stat_fb_ack")[0][0], 1)
        r2 = self.ok("sync")
        self.assertEqual((r2["upserted"], r2["deleted"]), (0, 0))  # converged

    def test_verify_finds_a_flipped_byte_and_sync_repairs_it(self):
        self.copied()
        sid = self.sql("SELECT min(sid) FROM sessions")[0][0]
        # same revision, one byte different: only the sha256 of the save can see it
        self.sql("UPDATE sessions SET state=overlay(state placing 'X' from 20 for 1) WHERE sid=%s", (sid,))
        rc, result, events = self.run_tool("verify")
        self.assertEqual(rc, 1)
        bad = [e for e in events if e["event"] == "verify" and e["mismatch"]]
        self.assertEqual([e["table"] for e in bad], ["sessions"])
        self.assertEqual(bad[0]["ids"], [sid[:16]])  # ids only, never the save
        self.assertNotIn("phở", json.dumps(events, ensure_ascii=False))
        self.sql("UPDATE archive SET day=day+1 WHERE seq=1 AND sid=%s", (sid,))
        rc, _, _ = self.run_tool("verify")
        self.assertEqual(rc, 1)
        self.ok("sync")  # the verify queued both for repair
        self.assertEqual(self.ok("verify")["mismatches"], 0)

    def test_fast_verify_checks_rows_synced_since_the_baseline(self):
        self.copied()
        self.ok("verify")  # baseline
        s = self.lite()
        sid = s.execute("SELECT max(sid) FROM sessions").fetchone()[0]
        s.execute("UPDATE sessions SET state=?,revision=revision+1 WHERE sid=?", (state(3, 5), sid))
        s.close()
        self.ok("sync")
        r = self.ok("verify", "--fast")
        self.assertEqual(r["mode"], "fast")
        # a byte flipped after the sync in a synced save is caught by the fast verify
        self.sql("UPDATE sessions SET state=overlay(state placing 'Y' from 30 for 1) WHERE sid=%s", (sid,))
        rc, _, _ = self.run_tool("verify", "--fast")
        self.assertEqual(rc, 1)

    def test_resume_after_interrupt(self):
        self.ok("init")
        real = pg_migrate.PGSide.copy_rows
        calls = {"n": 0}

        def flaky(side, spec, rows):
            calls["n"] += 1
            if calls["n"] == 3:
                raise KeyboardInterrupt
            return real(side, spec, rows)
        pg_migrate.PGSide.copy_rows = flaky
        try:
            rc, _, _ = self.run_tool("copy", "--chunk-mb", "0.05")
        finally:
            pg_migrate.PGSide.copy_rows = real
        self.assertEqual(rc, 130)
        partial = self.sql("SELECT count(*) FROM sessions")[0][0]
        self.assertTrue(0 < partial < 12, partial)
        self.ok("copy", "--chunk-mb", "0.05")  # resumes: no duplicate key errors, nothing missing
        self.assertEqual(self.sql("SELECT count(*) FROM sessions")[0][0], 12)
        self.assertEqual(self.ok("verify")["mismatches"], 0)

    def test_cutover_guard_and_reverse_sync(self):
        self.copied()
        self.ok("sync")
        self.ok("finalize")
        nxt = self.sql("SELECT nextval(pg_get_serial_sequence('player_feedback','id'))")[0][0]
        self.assertEqual(nxt, 6)  # after sqlite_sequence (5), not max(id) (4)
        self.ok("mark-cutover")
        rc, result, events = self.run_tool("sync")
        self.assertEqual(rc, 2)  # refuses to overwrite the live PostgreSQL
        # the game plays on PostgreSQL: new save, a changed save, pruned receipts, a new feedback
        sid = self.sql("SELECT min(sid) FROM sessions")[0][0]
        self.sql("INSERT INTO sessions(sid,csrf,revision,state) VALUES('pg-born','c',1,%s)", (state(1),))
        self.sql("UPDATE sessions SET state=%s, revision=revision+1, updated_at='2026-09-30 01:02:03' WHERE sid=%s", (state(2, 77), sid))
        self.sql("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(%s,'pg1','h','{}')", (sid,))
        self.sql("DELETE FROM receipts WHERE request_id='r4'")
        self.sql("INSERT INTO player_feedback(sid,kind,text,created_at,updated_at) VALUES('y','idea','ý',2,2)")
        before = Path(self.db).read_bytes()
        out = str(Path(self.tmp.name) / "rollback.sqlite3")
        lim_out = str(Path(self.tmp.name) / "rollback-limits.sqlite3")
        self.ok("reverse-sync", "--from-backup", self.db, "--out", out, "--limits-out", lim_out)
        self.assertEqual(Path(self.db).read_bytes(), before)  # the snapshot is never written
        s = sqlite3.connect(out)
        self.assertEqual(s.execute("SELECT revision FROM sessions WHERE sid='pg-born'").fetchone(), (1,))
        self.assertEqual(s.execute("SELECT count(*) FROM receipts WHERE request_id='r4'").fetchone(), (0,))
        self.assertEqual(s.execute("SELECT max(id) FROM player_feedback").fetchone(), (7,))  # 6 went to nextval above
        s.close()
        self.assertFalse(Path(out + "-wal").exists())
        s = sqlite3.connect(out)
        self.assertEqual(s.execute("SELECT count(*) FROM sqlite_master WHERE type='trigger'").fetchone(), (5,))  # restored
        s.close()
        # the new file equals PostgreSQL, row for row
        rc, result, _ = self.run_tool("verify", db=out)
        self.assertEqual((rc, result["mismatches"]), (0, 0))
        rc, _, _ = self.run_tool("reverse-sync", "--from-backup", self.db, "--out", self.db)
        self.assertEqual(rc, 2)  # never into the live/original file


if __name__ == "__main__":
    unittest.main()
