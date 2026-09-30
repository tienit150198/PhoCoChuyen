#!/usr/bin/env python3
"""Rehearse the SQLite -> PostgreSQL cutover on synthetic, production-shaped data.

  pg_rehearsal.py gen    --db D:/.../rehearsal/game.sqlite3 [--sessions 4000]
  pg_rehearsal.py writer --db ... --rate 30 [--seconds 0]         a live game: saves, receipts, prune...
  pg_rehearsal.py run    --db ... --pg-env-file FILE [--rate 30]  copy, syncs under load, timed cutover

The SQLite schema below is production v0.9.1 (game/storage.py, social.py, push.py,
admin_stats.py and the limits DB of server.py), so this does not depend on the
game code being ported at the same time. Nothing here is used by the game.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import secrets
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TZ = "+7 hours"

SQLITE_DDL = f"""
CREATE TABLE IF NOT EXISTS sessions (
  sid TEXT PRIMARY KEY, csrf TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
  state TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS receipts (
  sid TEXT NOT NULL, request_id TEXT NOT NULL, request_hash TEXT NOT NULL,
  result TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(sid,request_id), FOREIGN KEY(sid) REFERENCES sessions(sid)
);
CREATE TABLE IF NOT EXISTS accounts (
  uid INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, display TEXT NOT NULL,
  pw TEXT NOT NULL, sid TEXT UNIQUE NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS logins (
  token TEXT PRIMARY KEY, sid TEXT NOT NULL, csrf TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS logins_sid ON logins(sid);
CREATE TABLE IF NOT EXISTS player_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT NOT NULL, account TEXT,
  kind TEXT NOT NULL, text TEXT NOT NULL, context TEXT NOT NULL DEFAULT '{{}}',
  status TEXT NOT NULL DEFAULT 'new', reply TEXT,
  created_at REAL NOT NULL, updated_at REAL NOT NULL, replied_at REAL
);
CREATE INDEX IF NOT EXISTS player_feedback_sid ON player_feedback(sid, id);
CREATE INDEX IF NOT EXISTS player_feedback_status ON player_feedback(status, id);
CREATE TABLE IF NOT EXISTS archive (
  sid TEXT NOT NULL, career TEXT NOT NULL, kind TEXT NOT NULL, seq INTEGER NOT NULL,
  day INTEGER, row TEXT NOT NULL, created_at REAL NOT NULL DEFAULT (unixepoch()),
  FOREIGN KEY(sid) REFERENCES sessions(sid)
);
CREATE UNIQUE INDEX IF NOT EXISTS archive_rows ON archive(sid, career, kind, seq);
CREATE TABLE IF NOT EXISTS profiles (
  pid TEXT PRIMARY KEY, sid TEXT UNIQUE NOT NULL, name TEXT, name_key TEXT UNIQUE, bio TEXT NOT NULL DEFAULT '',
  avatar TEXT NOT NULL DEFAULT '🌸', visible INTEGER NOT NULL DEFAULT 0, shop TEXT NOT NULL DEFAULT '{{}}',
  served INTEGER NOT NULL DEFAULT 0, week_key TEXT NOT NULL DEFAULT '', week_base INTEGER NOT NULL DEFAULT 0,
  reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0,
  created REAL NOT NULL, updated REAL NOT NULL, seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS visits (from_pid TEXT, to_pid TEXT, day TEXT, at REAL, PRIMARY KEY(from_pid,to_pid,day));
CREATE TABLE IF NOT EXISTS previews (
  id INTEGER PRIMARY KEY AUTOINCREMENT, from_pid TEXT NOT NULL, to_pid TEXT NOT NULL, career TEXT NOT NULL, day TEXT NOT NULL,
  stars INTEGER NOT NULL, text TEXT NOT NULL, reply TEXT, reply_at REAL, at REAL NOT NULL, reports INTEGER NOT NULL DEFAULT 0,
  hidden INTEGER NOT NULL DEFAULT 0, UNIQUE(from_pid,to_pid,day)
);
CREATE TABLE IF NOT EXISTS gifts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, from_pid TEXT NOT NULL, to_pid TEXT NOT NULL, sticker TEXT NOT NULL, coins INTEGER NOT NULL,
  note TEXT NOT NULL DEFAULT '', day TEXT NOT NULL, at REAL NOT NULL, claimed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS market (
  id INTEGER PRIMARY KEY AUTOINCREMENT, seller TEXT NOT NULL, career TEXT NOT NULL, item TEXT NOT NULL, qty INTEGER NOT NULL,
  price INTEGER NOT NULL, life_left INTEGER NOT NULL, unit_cost INTEGER NOT NULL, listed_day INTEGER NOT NULL,
  status TEXT NOT NULL, buyer TEXT, at REAL NOT NULL, sold_at REAL, settled INTEGER NOT NULL DEFAULT 0,
  reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS board (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT NOT NULL, career TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL,
  at REAL NOT NULL, reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, post INTEGER NOT NULL, pid TEXT NOT NULL, text TEXT NOT NULL, at REAL NOT NULL,
  reports INTEGER NOT NULL DEFAULT 0, hidden INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS reactions (post INTEGER NOT NULL, pid TEXT NOT NULL, emoji TEXT NOT NULL, PRIMARY KEY(post,pid,emoji));
CREATE TABLE IF NOT EXISTS follows (pid TEXT NOT NULL, target TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY(pid,target));
CREATE TABLE IF NOT EXISTS blocks (pid TEXT NOT NULL, target TEXT NOT NULL, at REAL NOT NULL, PRIMARY KEY(pid,target));
CREATE TABLE IF NOT EXISTS reports (reporter TEXT NOT NULL, kind TEXT NOT NULL, target TEXT NOT NULL, reason TEXT NOT NULL, at REAL NOT NULL,
  PRIMARY KEY(reporter,kind,target));
CREATE TABLE IF NOT EXISTS inbox (
  id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL, ref TEXT, at REAL NOT NULL,
  read INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS inbox_pid ON inbox(pid, id);
CREATE INDEX IF NOT EXISTS board_career ON board(career, id);
CREATE INDEX IF NOT EXISTS market_status ON market(status, career);
CREATE INDEX IF NOT EXISTS preview_to ON previews(to_pid, id);
CREATE INDEX IF NOT EXISTS gifts_to ON gifts(to_pid, claimed);
CREATE TABLE IF NOT EXISTS push_subs (
  endpoint TEXT PRIMARY KEY, sid TEXT NOT NULL, created REAL NOT NULL, last_ok REAL, fails INTEGER NOT NULL DEFAULT 0,
  prefs TEXT NOT NULL DEFAULT '{{}}'
);
CREATE INDEX IF NOT EXISTS push_subs_sid ON push_subs(sid);
CREATE TABLE IF NOT EXISTS push_queue (
  id INTEGER PRIMARY KEY AUTOINCREMENT, sid TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL, url TEXT NOT NULL,
  at REAL NOT NULL, sent INTEGER NOT NULL DEFAULT 0, shown INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS push_queue_sid ON push_queue(sid, id);
CREATE TABLE IF NOT EXISTS push_daily (sid TEXT PRIMARY KEY, day TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS stat_sessions_seen ON sessions(updated_at, revision, sid);
CREATE TABLE IF NOT EXISTS stat_births (sid TEXT PRIMARY KEY, day TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS stat_births_day ON stat_births(day);
CREATE TABLE IF NOT EXISTS stat_active (day TEXT NOT NULL, sid TEXT NOT NULL, PRIMARY KEY(day, sid)) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS stat_active_sid ON stat_active(sid);
CREATE TABLE IF NOT EXISTS stat_fb_ack (id INTEGER PRIMARY KEY, at REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS stat_session_born AFTER INSERT ON sessions BEGIN
  INSERT OR IGNORE INTO stat_births(sid, day) VALUES (NEW.sid, date('now', '{TZ}'));
END;
CREATE TRIGGER IF NOT EXISTS stat_session_active AFTER UPDATE OF updated_at ON sessions BEGIN
  INSERT OR IGNORE INTO stat_active(day, sid) VALUES (date('now', '{TZ}'), NEW.sid);
END;
CREATE TRIGGER IF NOT EXISTS stat_session_gone AFTER DELETE ON sessions BEGIN
  DELETE FROM stat_births WHERE sid = OLD.sid;
  DELETE FROM stat_active WHERE sid = OLD.sid;
END;
CREATE TRIGGER IF NOT EXISTS stat_fb_seen AFTER UPDATE OF status ON player_feedback
  WHEN OLD.status = 'new' AND NEW.status != 'new' BEGIN
  INSERT OR IGNORE INTO stat_fb_ack(id, at) VALUES (NEW.id, NEW.updated_at);
END;
CREATE TRIGGER IF NOT EXISTS stat_fb_gone AFTER DELETE ON player_feedback BEGIN
  DELETE FROM stat_fb_ack WHERE id = OLD.id;
END;
"""
LIMITS_DDL = """
CREATE TABLE IF NOT EXISTS hits (k TEXT NOT NULL, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS hits_k ON hits(k, at);
"""
PRAGMAS = ("PRAGMA foreign_keys=ON", "PRAGMA busy_timeout=12000", "PRAGMA synchronous=NORMAL",
           "PRAGMA journal_size_limit=67108864")

CAREERS = ["bakery", "cafe", "florist", "grocery", "repair", "salon", "pet_care", "restaurant", "homestay",
           "farm", "delivery", "pharmacy", "milk_tea", "teacher", "tour", "accounting"]
WORDS = ("khách quen ghé mua ổ bánh mì và hỏi thăm chuyện nhà hôm nay trời mưa nên quán vắng hơn mọi ngày "
         "cô chủ tiệm hoa bên cạnh mang sang một bó cúc vàng anh giao hàng đến trễ mười phút vì kẹt xe "
         "đơn hàng online tăng gấp đôi sau khi đăng bài lên nhóm cư dân nhập thêm hai thùng sữa tươi").split()


def utc(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sentence(rng, n=None):
    return " ".join(rng.choice(WORDS) for _ in range(n or rng.randint(6, 18)))


def open_db(path: str) -> sqlite3.Connection:
    db = sqlite3.connect(path, isolation_level=None, timeout=12)
    db.execute("PRAGMA journal_mode=WAL")
    for p in PRAGMAS:
        db.execute(p)
    return db


def make_state(rng, target_bytes: int, pool: list) -> str:
    """A save of about `target_bytes`: careers with long feeds, a journey, settings. `tick` first
    so the writer can change a save without parsing 1 MB of JSON."""
    careers = {}
    size = 0
    while size < target_bytes:
        cid = rng.choice(CAREERS) + str(rng.randint(0, 3))
        feed = rng.choices(pool, k=rng.randint(40, 400))
        careers[cid] = dict(started=True, day=rng.randint(1, 90), xp=rng.randint(0, 5000), cash=rng.randint(-500, 90000),
                            stock={f"item{i}": rng.randint(0, 40) for i in range(rng.randint(5, 30))}, feed=feed)
        size += sum(len(e["text"]) + 60 for e in feed) + 300
    state = dict(tick=0, version=9, settings=dict(lang=rng.choice(["vi", "vi", "en"]), music=rng.random() < .5),
                 journey=dict(chapter=rng.randint(1, 6), life_day=rng.randint(1, 200), wallet=rng.randint(-300, 50000)),
                 careers=careers)
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"))


def gen(a):
    rng = random.Random(a.seed)
    path = Path(a.db)
    path.parent.mkdir(parents=True, exist_ok=True)
    limits = path.with_name(path.stem + "-limits.sqlite3")
    for p in (path, limits):
        for suf in ("", "-wal", "-shm"):
            q = Path(str(p) + suf)
            if q.exists():
                q.unlink()
    db = open_db(str(path))
    db.executescript(SQLITE_DDL)
    pool = [dict(day=rng.randint(1, 120), kind=rng.choice(["note", "sale", "event", "customer"]),
                 text=sentence(rng, rng.randint(10, 40)), money=rng.randint(-50, 400)) for _ in range(3000)]
    now = time.time()
    t0 = time.time()
    sids, played = [], []
    total = 0
    db.execute("BEGIN")
    for i in range(a.sessions):
        sid = hashlib.sha256(secrets.token_bytes(16)).hexdigest()
        target = int(min(1_300_000, max(100_000, rng.lognormvariate(12.75, 0.55))))  # median ~345 KB
        state = make_state(rng, target, pool)
        total += len(state.encode())
        last = now - rng.expovariate(1 / (6 * 86400))
        rev = rng.randint(1, 4000)
        db.execute("INSERT INTO sessions(sid,csrf,revision,state,updated_at) VALUES(?,?,?,?,?)",
                   (sid, secrets.token_urlsafe(24), rev, state, utc(last)))
        sids.append(sid)
        if rng.random() < .85:
            played.append(sid)
        if i % 200 == 199:
            db.execute("COMMIT")
            db.execute("BEGIN")
            print(f"  {i + 1} saves, {total / 1e6:.0f} MB, {time.time() - t0:.0f}s", flush=True)
    db.execute("COMMIT")
    db.execute("BEGIN")
    # stat tables (born/active days)
    for sid in sids:
        born = now - rng.randint(0, 120) * 86400
        db.execute("UPDATE stat_births SET day=? WHERE sid=?", (utc(born)[:10], sid))
        for d in rng.sample(range(120), rng.randint(1, 25)):
            db.execute("INSERT OR IGNORE INTO stat_active(day,sid) VALUES(?,?)", (utc(now - d * 86400)[:10], sid))
    # receipts: the last ~2 days of commands, up to 200 per save
    n = 0
    for sid in played:
        for j in range(min(200, int(rng.expovariate(1 / 30)))):
            res = json.dumps(dict(ok=True, message=sentence(rng), delta=dict(cash=rng.randint(-99, 999), xp=rng.randint(0, 40)),
                                  lines=[sentence(rng) for _ in range(rng.randint(1, 6))]), ensure_ascii=False)
            db.execute("INSERT INTO receipts(sid,request_id,request_hash,result,created_at) VALUES(?,?,?,?,?)",
                       (sid, secrets.token_hex(16), secrets.token_hex(32), res, utc(now - rng.random() * 2 * 86400)))
            n += 1
    print(f"  receipts {n}", flush=True)
    # archive: rows that left capped lists (grows forever)
    n = 0
    for sid in played:
        for career in rng.sample(CAREERS, rng.randint(1, 4)):
            for kind in rng.sample(["feed", "orders", "reviews", "ledger"], rng.randint(1, 3)):
                for seq in range(int(rng.expovariate(1 / 40))):
                    db.execute("INSERT INTO archive(sid,career,kind,seq,day,row,created_at) VALUES(?,?,?,?,?,?,?)",
                               (sid, career, kind, seq, rng.randint(1, 200),
                                json.dumps(dict(day=seq, text=sentence(rng), money=rng.randint(-50, 300)), ensure_ascii=False),
                                float(int(now - rng.random() * 90 * 86400))))
                    n += 1
    print(f"  archive {n}", flush=True)
    db.execute("COMMIT")
    db.execute("BEGIN")
    acc = rng.sample(played, int(len(played) * .3))
    for k, sid in enumerate(acc):
        c = utc(now - rng.random() * 100 * 86400)
        db.execute("INSERT INTO accounts(username,display,pw,sid,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                   (f"player_{k}", f"Người chơi {k}", "scrypt$" + secrets.token_hex(40), sid, c, c))
        for _ in range(rng.randint(1, 3)):
            db.execute("INSERT INTO logins(token,sid,csrf,created_at,seen_at) VALUES(?,?,?,?,?)",
                       (secrets.token_hex(32), sid, secrets.token_urlsafe(24), c, utc(now - rng.random() * 30 * 86400)))
    for k in range(max(50, a.sessions // 5)):
        t = now - rng.random() * 60 * 86400
        st = rng.choice(["new", "new", "seen", "done"])
        db.execute("INSERT INTO player_feedback(sid,account,kind,text,context,status,reply,created_at,updated_at,replied_at) "
                   "VALUES(?,?,?,?,?,?,?,?,?,?)", (rng.choice(sids), None, rng.choice(["bug", "idea", "praise"]), sentence(rng, 30),
                                                  json.dumps(dict(career=rng.choice(CAREERS), day=rng.randint(1, 50))), st,
                                                  sentence(rng) if st == "done" else None, t, t, t if st == "done" else None))
    pids = []
    for sid in rng.sample(played, int(len(played) * .4)):
        pid = secrets.token_hex(8)
        pids.append(pid)
        t = now - rng.random() * 90 * 86400
        name = f"Quán {pid}" if rng.random() < .7 else None
        db.execute("INSERT INTO profiles(pid,sid,name,name_key,bio,visible,shop,served,created,updated,seen) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (pid, sid, name, name.lower() if name else None, sentence(rng), int(rng.random() < .8),
                    json.dumps(dict(career=rng.choice(CAREERS), items=[sentence(rng, 4) for _ in range(12)]), ensure_ascii=False),
                    rng.randint(0, 900), t, t, t))
    for _ in range(len(pids) * 12):
        db.execute("INSERT OR IGNORE INTO visits(from_pid,to_pid,day,at) VALUES(?,?,?,?)",
                   (rng.choice(pids), rng.choice(pids), utc(now - rng.randint(0, 30) * 86400)[:10], now - rng.random() * 30 * 86400))
    for _ in range(len(pids) * 3):
        db.execute("INSERT OR IGNORE INTO previews(from_pid,to_pid,career,day,stars,text,at) VALUES(?,?,?,?,?,?,?)",
                   (rng.choice(pids), rng.choice(pids), rng.choice(CAREERS), utc(now - rng.randint(0, 60) * 86400)[:10],
                    rng.randint(1, 5), sentence(rng), now - rng.random() * 60 * 86400))
        db.execute("INSERT INTO gifts(from_pid,to_pid,sticker,coins,day,at,claimed) VALUES(?,?,?,?,?,?,?)",
                   (rng.choice(pids), rng.choice(pids), "🌸", rng.choice([0, 10, 20]), utc(now)[:10], now - rng.random() * 9e5, rng.randint(0, 1)))
        db.execute("INSERT INTO market(seller,career,item,qty,price,life_left,unit_cost,listed_day,status,at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (rng.choice(pids), rng.choice(CAREERS), "item" + str(rng.randint(0, 30)), rng.randint(1, 9), rng.randint(5, 500),
                    rng.randint(1, 9), rng.randint(3, 300), rng.randint(1, 90), rng.choice(["active", "sold", "expired"]), now - rng.random() * 9e5))
    for _ in range(len(pids) * 2):
        db.execute("INSERT INTO board(pid,career,kind,text,at) VALUES(?,?,?,?,?)",
                   (rng.choice(pids), rng.choice(CAREERS), rng.choice(["tip", "story", "ask"]), sentence(rng, 25), now - rng.random() * 9e5))
    posts = db.execute("SELECT max(id) FROM board").fetchone()[0] or 1
    for _ in range(len(pids) * 4):
        db.execute("INSERT INTO comments(post,pid,text,at) VALUES(?,?,?,?)", (rng.randint(1, posts), rng.choice(pids), sentence(rng), now))
        db.execute("INSERT OR IGNORE INTO reactions(post,pid,emoji) VALUES(?,?,?)", (rng.randint(1, posts), rng.choice(pids), "❤️"))
        db.execute("INSERT OR IGNORE INTO follows(pid,target,at) VALUES(?,?,?)", (rng.choice(pids), rng.choice(pids), now))
    for _ in range(len(pids) // 10):
        db.execute("INSERT OR IGNORE INTO blocks(pid,target,at) VALUES(?,?,?)", (rng.choice(pids), rng.choice(pids), now))
        db.execute("INSERT OR IGNORE INTO reports(reporter,kind,target,reason,at) VALUES(?,?,?,?,?)",
                   (rng.choice(pids), "board", str(rng.randint(1, posts)), "spam", now))
    for _ in range(len(pids) * 25):
        db.execute("INSERT INTO inbox(pid,kind,text,ref,at,read) VALUES(?,?,?,?,?,?)",
                   (rng.choice(pids), rng.choice(["visit", "gift", "review"]), sentence(rng), None, now - rng.random() * 50 * 86400, rng.randint(0, 1)))
    for sid in rng.sample(played, len(played) // 5):
        db.execute("INSERT INTO push_subs(endpoint,sid,created,prefs) VALUES(?,?,?,?)",
                   ("https://fcm.googleapis.com/fcm/send/" + secrets.token_urlsafe(90), sid, now, "{}"))
        db.execute("INSERT OR IGNORE INTO push_daily(sid,day) VALUES(?,?)", (sid, utc(now)[:10]))
        for _ in range(rng.randint(0, 8)):
            db.execute("INSERT INTO push_queue(sid,kind,body,url,at,sent) VALUES(?,?,?,?,?,?)",
                       (sid, "visit", sentence(rng), "/", now - rng.random() * 6 * 86400, rng.randint(0, 1)))
    db.execute("UPDATE player_feedback SET status='seen', updated_at=updated_at+1 WHERE status='new' AND id%3=0")
    db.execute("COMMIT")
    db.execute("DELETE FROM player_feedback WHERE id % 97 = 0")  # gaps + sqlite_sequence above max(id)
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    db.close()
    lim = open_db(str(limits))
    lim.executescript(LIMITS_DDL)
    lim.execute("BEGIN")
    for _ in range(20000):
        lim.execute("INSERT INTO hits(k,at) VALUES(?,?)", (rng.choice(["ai:", "acct-login:", "newsession:", "fb:"]) + secrets.token_hex(4),
                                                          now - rng.random() * 86400))
    lim.execute("COMMIT")
    lim.close()
    size = path.stat().st_size
    print(json.dumps(dict(db=str(path), mb=round(size / 1e6), sessions=a.sessions, state_mb=round(total / 1e6),
                          seconds=round(time.time() - t0))), flush=True)


# ---------------------------------------------------------------------------
# A live game


TICK = re.compile(r'^\{"tick":(\d+)')


def writer(a):
    """Rewrite random saves like the game does: one short BEGIN IMMEDIATE per command
    (state + revision + updated_at, a receipt, sometimes archive rows), plus new saves,
    deleted saves, receipt pruning, logins, social rows and rate-limit hits. Reports the
    achieved rate and the largest WAL seen (a reader pinning a snapshot shows up here)."""
    rng = random.Random(a.seed + os.getpid())
    db = open_db(a.db)
    lim = open_db(str(Path(a.db).with_name(Path(a.db).stem + "-limits.sqlite3")))
    sids = [r[0] for r in db.execute("SELECT sid FROM sessions")]
    hot = rng.sample(sids, max(1, len(sids) // 10))
    pool = [dict(day=1, kind="note", text=sentence(rng, 20), money=5) for _ in range(200)]
    stop = {"now": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(now=True))
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, lambda *_: stop.update(now=True))
    stop_file = Path(a.stop_file) if a.stop_file else None
    t0 = time.monotonic()
    n = new = gone = pruned = locked = 0
    lat = []
    wal_max = 0
    last_ck = time.monotonic()
    interval = 1.0 / a.rate
    nxt = time.monotonic()
    wal = Path(a.db + "-wal")
    while not stop["now"]:
        if a.seconds and time.monotonic() - t0 > a.seconds:
            break
        if stop_file and stop_file.exists():
            break
        now = time.time()
        r = rng.random()
        tw = time.perf_counter()
        try:
            db.execute("BEGIN IMMEDIATE")
            if r < 0.01:  # a new save
                sid = hashlib.sha256(secrets.token_bytes(16)).hexdigest()
                db.execute("INSERT INTO sessions(sid,csrf,state) VALUES(?,?,?)",
                           (sid, secrets.token_urlsafe(24), make_state(rng, rng.randint(100_000, 300_000), pool)))
                sids.append(sid)
                new += 1
            elif r < 0.013 and len(sids) > 100:  # "Xóa dữ liệu": a save and everything of it
                sid = sids.pop(rng.randrange(len(sids)))
                if sid in hot:
                    hot.remove(sid)
                for t in ("archive", "receipts", "logins", "accounts"):
                    db.execute(f"DELETE FROM {t} WHERE sid=?", (sid,))
                db.execute("DELETE FROM sessions WHERE sid=?", (sid,))
                gone += 1
            else:  # a command on a save (80% of them on the hot 10%)
                sid = rng.choice(hot) if rng.random() < .8 and hot else rng.choice(sids)
                row = db.execute("SELECT revision,state FROM sessions WHERE sid=?", (sid,)).fetchone()
                if row:
                    rev, state = row
                    m = TICK.match(state)
                    tick = int(m.group(1)) + 1 if m else 1
                    state = '{"tick":%d' % tick + state[m.end():] if m else state
                    db.execute("UPDATE sessions SET state=?,revision=?,updated_at=CURRENT_TIMESTAMP WHERE sid=? AND revision=?",
                               (state, rev + 1, sid, rev))
                    db.execute("INSERT INTO receipts(sid,request_id,request_hash,result) VALUES(?,?,?,?)",
                               (sid, secrets.token_hex(16), secrets.token_hex(32), json.dumps(dict(ok=True, n=tick, msg=sentence(rng)), ensure_ascii=False)))
                    if rng.random() < .3:
                        career, kind = rng.choice(CAREERS), "feed"
                        seq = db.execute("SELECT COALESCE(MAX(seq)+1,0) FROM archive WHERE sid=? AND career=? AND kind=?",
                                         (sid, career, kind)).fetchone()[0]
                        for j in range(rng.randint(1, 3)):
                            db.execute("INSERT INTO archive(sid,career,kind,seq,day,row) VALUES(?,?,?,?,?,?)",
                                       (sid, career, kind, seq + j, tick, json.dumps(dict(text=sentence(rng)), ensure_ascii=False)))
                    if rng.random() < .01:  # the player erases a history: deleted, restarts at seq 0
                        db.execute("DELETE FROM archive WHERE sid=? AND career=? AND kind='feed'", (sid, rng.choice(CAREERS)))
            if r > 0.97:  # the odds and ends of a real server
                db.execute("UPDATE logins SET seen_at=CURRENT_TIMESTAMP WHERE token=(SELECT token FROM logins ORDER BY random() LIMIT 1)")
                db.execute("INSERT INTO inbox(pid,kind,text,at) VALUES(?,?,?,?)", ("p" + secrets.token_hex(4), "visit", sentence(rng), now))
                db.execute("UPDATE profiles SET seen=? WHERE pid=(SELECT pid FROM profiles ORDER BY random() LIMIT 1)", (now,))
                db.execute("UPDATE player_feedback SET status='done',reply=?,updated_at=? WHERE id=(SELECT id FROM player_feedback WHERE status='new' LIMIT 1)",
                           (sentence(rng), now))
            db.execute("COMMIT")
            n += 1
            lat.append(time.perf_counter() - tw)
        except sqlite3.OperationalError as e:
            locked += "locked" in str(e)
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            print(f"[writer] {e}", file=sys.stderr, flush=True)
        try:
            if rng.random() < 0.05:
                lim.execute("INSERT INTO hits(k,at) VALUES(?,?)", ("ai:" + secrets.token_hex(3), now))
            if n % 500 == 0 and n:  # receipt pruning like prune_receipts: oldest rows, small batches
                db.execute("BEGIN IMMEDIATE")
                pruned += db.execute("DELETE FROM receipts WHERE rowid IN (SELECT rowid FROM receipts ORDER BY rowid LIMIT 200)").rowcount
                db.execute("COMMIT")
                lim.execute("DELETE FROM hits WHERE rowid IN (SELECT rowid FROM hits ORDER BY rowid LIMIT 50)")
        except sqlite3.OperationalError as e:  # busy: the game would retry later too
            locked += "locked" in str(e)
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
        if a.checkpoints and time.monotonic() - last_ck > 5:  # the game's maintenance thread (Store.checkpoint)
            db.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchall()
            db.execute("PRAGMA busy_timeout=300")  # like checkpoint(truncate_ms): never queue writers behind it
            try:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchall()
            except sqlite3.OperationalError:
                pass
            db.execute("PRAGMA busy_timeout=12000")
            last_ck = time.monotonic()
        try:
            wal_max = max(wal_max, wal.stat().st_size)
        except OSError:
            pass
        nxt += interval
        d = nxt - time.monotonic()
        if d > 0:
            time.sleep(d)
        else:
            nxt = time.monotonic()
    el = time.monotonic() - t0
    lat.sort()
    pct = lambda p: round(1000 * lat[min(len(lat) - 1, int(p * len(lat)))]) if lat else None
    out = dict(writes=n, seconds=round(el, 1), per_s=round(n / el, 1) if el else 0, new=new, deleted=gone, locked=locked,
               p50_ms=pct(.5), p95_ms=pct(.95), p99_ms=pct(.99), max_ms=round(1000 * lat[-1]) if lat else None,
               receipts_pruned=pruned, wal_max_mb=round(wal_max / 1e6, 1))
    Path(a.report).write_text(json.dumps(out)) if a.report else None
    print(json.dumps(out), flush=True)
    db.close()
    lim.close()


# ---------------------------------------------------------------------------
# The rehearsal


def run(a):
    mig = [sys.executable, str(HERE / "pg_migrate.py"), "--sqlite", a.db, "--pg-env-file", a.pg_env_file, "--json"]
    work = Path(a.db).parent
    rows = []
    results = {}

    def step(name, *extra, expect_ok=True):
        t0 = time.monotonic()
        p = subprocess.run(mig[:2] + list(extra[:1]) + mig[2:] + list(extra[1:]), capture_output=True, text=True, encoding="utf-8")
        el = time.monotonic() - t0
        res = {}
        for line in p.stdout.splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("event") == "result":
                res = ev
            if ev.get("event") == "verify" and ev.get("mismatch"):
                print(f"   mismatch {ev['table']}: {ev.get('mismatch')} ids={ev.get('ids')}", flush=True)
        ok = p.returncode == 0
        rows.append((name, round(el, 2), ok, {k: res.get(k) for k in ("mb", "mb_s", "upserted", "deleted", "mismatches", "in_flight") if k in res}))
        results[name] = dict({k: v for k, v in res.items() if k not in ("event", "t")}, wall_s=round(el, 2), rc=p.returncode)
        print(f"{name:<34} {el:8.2f}s rc={p.returncode} {rows[-1][3]}", flush=True)
        if expect_ok and not ok:
            sys.stderr.write(p.stderr[-3000:])
            raise SystemExit(f"step {name} failed")
        return res

    stop_file = work / "writer.stop"
    if stop_file.exists():
        stop_file.unlink()
    step("init (tables)", "init")
    wrep = work / "writer.json"
    ws = [subprocess.Popen([sys.executable, __file__, "writer", "--db", a.db, "--rate", str(a.rate / a.writers),
                            "--report", str(wrep) + str(i), "--stop-file", str(stop_file), "--seed", str(11 + i),
                            "--checkpoints", "1" if i == 0 else "0"])
          for i in range(a.writers)]
    time.sleep(3)
    try:
        if a.skip_copy:  # reuse the tables an earlier run copied: the first sync catches up
            c = {}
        else:
            c = step("copy (live, writer on)", "copy", "--restart", "--force", "--chunk-mb", str(a.chunk_mb), "--pause-ms", "20",
                     *(["--max-mb-per-s", str(a.max_mb_per_s)] if a.max_mb_per_s else []))
        for i in range(a.syncs):
            step(f"sync #{i + 1} (live)", "sync")
        step("verify --live (baseline, live)", "verify", "--live")
        step("sync (live, after baseline)", "sync")
        step("sync (live, just before stop)", "sync")
    finally:
        stop_file.touch()
        for w in ws:
            w.wait(timeout=120)
    t_down = time.monotonic()
    step("DOWNTIME: final sync", "sync")
    step("DOWNTIME: verify --fast", "verify", "--fast")
    step("DOWNTIME: finalize (triggers+seq)", "finalize")
    down = time.monotonic() - t_down
    rows.append(("= downtime (tool part)", round(down, 2), True, {}))
    print(f"{'= downtime (tool part)':<34} {down:8.2f}s", flush=True)
    step("full verify (after, offline)", "verify", expect_ok=True)
    parts = [json.loads(Path(str(wrep) + str(i)).read_text()) for i in range(a.writers) if Path(str(wrep) + str(i)).exists()]
    wstats = dict(writes=sum(p["writes"] for p in parts), per_s=round(sum(p["per_s"] for p in parts), 1),
                  wal_max_mb=max([p["wal_max_mb"] for p in parts] or [0]), deleted=sum(p["deleted"] for p in parts),
                  new=sum(p["new"] for p in parts), receipts_pruned=sum(p["receipts_pruned"] for p in parts),
                  locked=sum(p.get("locked", 0) for p in parts), p95_ms=max([p.get("p95_ms") or 0 for p in parts] or [0]),
                  p50_ms=max([p.get("p50_ms") or 0 for p in parts] or [0]), max_ms=max([p.get("max_ms") or 0 for p in parts] or [0]))
    size = Path(a.db).stat().st_size
    out = dict(db_mb=round(size / 1e6), writer=wstats, steps=results, downtime_tool_s=round(down, 2),
               copy_mb_s=c.get("mb_s"), copy_mb=c.get("mb"))
    (work / "rehearsal_result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(dict(writer=wstats, downtime_tool_s=round(down, 2), copy_mb_s=c.get("mb_s"))), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("--db", required=True)
    g.add_argument("--sessions", type=int, default=4000)
    g.add_argument("--seed", type=int, default=7)
    w = sub.add_parser("writer")
    w.add_argument("--db", required=True)
    w.add_argument("--rate", type=float, default=30)
    w.add_argument("--seconds", type=float, default=0)
    w.add_argument("--seed", type=int, default=11)
    w.add_argument("--report")
    w.add_argument("--stop-file")
    w.add_argument("--checkpoints", type=int, default=1)
    r = sub.add_parser("run")
    r.add_argument("--db", required=True)
    r.add_argument("--pg-env-file", required=True)
    r.add_argument("--rate", type=float, default=30)
    r.add_argument("--syncs", type=int, default=3)
    r.add_argument("--skip-copy", action="store_true", help="keep the PostgreSQL copy of an earlier run")
    r.add_argument("--writers", type=int, default=3)
    r.add_argument("--chunk-mb", type=float, default=8)
    r.add_argument("--max-mb-per-s", type=float, default=0)
    a = ap.parse_args()
    dict(gen=gen, writer=writer, run=run)[a.cmd](a)


if __name__ == "__main__":
    main()
