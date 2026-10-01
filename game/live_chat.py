"""💬 Chat, the game server's side: the tables (SQLite twin of game/pg_schema.py), the admin "Chat" tab
(reports queue, hide / keep, mute 1 h / 24 h / 7 d) and the cleanup when a player deletes their data.

The chat itself runs in the live service (live/, `python3 -m live`, a WebSocket per player): it writes
messages, reports and auto-hides. The game server never sends a chat message. An admin decision is written
here, then announced with `pg_notify('mnl_live', <json>)` so the live service applies it at once (drops a
hidden message from its buffers and from every open screen, mutes an online player). On SQLite (dev, tests)
there is no NOTIFY: the live service sees the change on its next start.

Messages are never deleted (owner rule): an author's own delete empties the text (deleted=1); a hidden
message keeps its text for the admin (hidden 1 = three reports, waiting for review; 2 = hidden by an admin).
"""
from __future__ import annotations

import json
import time

from . import db as dbm

NOTIFY_CHANNEL = 'mnl_live'
MUTE_HOURS = (1, 24, 168)
QUEUE_MAX = 50
CONTEXT = 3                 # messages shown before and after a reported one
REASONS = ('spam', 'rude', 'private', 'scam', 'other')

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_channels (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL DEFAULT '', owner_pid TEXT, created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_members (
  channel TEXT NOT NULL, pid TEXT NOT NULL, sid TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'member', joined REAL NOT NULL,
  last_read INTEGER NOT NULL DEFAULT 0, muted_until REAL NOT NULL DEFAULT 0, pushed_at REAL NOT NULL DEFAULT 0,
  PRIMARY KEY (channel, pid)
);
CREATE TABLE IF NOT EXISTS chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT NOT NULL, pid TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
  av TEXT NOT NULL DEFAULT '', text TEXT NOT NULL, at REAL NOT NULL, hidden INTEGER NOT NULL DEFAULT 0,
  deleted INTEGER NOT NULL DEFAULT 0, reports INTEGER NOT NULL DEFAULT 0, reviewed_at REAL
);
CREATE TABLE IF NOT EXISTS chat_mutes (
  pid TEXT PRIMARY KEY, until REAL NOT NULL, by_admin TEXT NOT NULL DEFAULT '', reason TEXT NOT NULL DEFAULT '', at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS chat_prefs (pid TEXT PRIMARY KEY, online INTEGER NOT NULL DEFAULT 1, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS live_effects (
  id TEXT PRIMARY KEY, sid TEXT NOT NULL, kind TEXT NOT NULL, amount INTEGER NOT NULL DEFAULT 0, data TEXT NOT NULL DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'pending', at REAL NOT NULL, applied_at REAL
);
CREATE INDEX IF NOT EXISTS chat_members_pid ON chat_members(pid, channel);
CREATE INDEX IF NOT EXISTS chat_messages_channel ON chat_messages(channel, id);
CREATE INDEX IF NOT EXISTS chat_messages_pid ON chat_messages(pid, id);
CREATE INDEX IF NOT EXISTS chat_messages_reported ON chat_messages(id) WHERE reports > 0;
CREATE INDEX IF NOT EXISTS live_effects_sid ON live_effects(sid, status);
CREATE INDEX IF NOT EXISTS live_effects_day ON live_effects(sid, kind, at);
"""


class ChatAdminError(Exception):
    def __init__(self, message: str, code: str = 'chat_admin', status: int = 400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(cond, message: str, code: str = 'chat_admin', status: int = 400):
    if not cond:
        raise ChatAdminError(message, code, status)


def now() -> float:
    return time.time()


def pid_of(sid: str) -> str:
    from .social import pid_of as _pid
    return _pid(sid)


def notify(db, event: dict) -> None:
    """Tell the live service (PostgreSQL LISTEN mnl_live). Delivered when the transaction commits."""
    if dbm.is_pg(db):
        db.execute('SELECT pg_notify(?, ?)', (NOTIFY_CHANNEL, json.dumps(event, separators=(',', ':'))))


def _kind(channel: str) -> str:
    return 'town' if channel == 'town' else 'dm' if channel.startswith('dm:') else 'group' if channel.startswith('g:') else channel.split(':', 1)[0]


def _msg(r) -> dict:
    return dict(id=int(r['id']), ch=r['channel'], kind=_kind(r['channel']), pid=r['pid'], name=r['name'], av=r['av'],
                text=r['text'], at=float(r['at']), hidden=int(r['hidden']), deleted=int(r['deleted']), reports=int(r['reports']),
                reviewed=r['reviewed_at'] is not None)


def view(store) -> dict:
    """The admin "Chat" tab: reported messages waiting for a decision (with a few messages of context and the
    reasons), the active mutes, and the last messages of Cả phố."""
    t = now()
    with store.connect() as db:
        rows = db.execute('SELECT * FROM chat_messages WHERE reports > 0 AND reviewed_at IS NULL ORDER BY id DESC LIMIT ?',
                          (QUEUE_MAX,)).fetchall()
        items = []
        for r in rows:
            m = _msg(r)
            reasons = {}
            for x in db.execute("SELECT reason, COUNT(*) AS n FROM reports WHERE kind='chat' AND target=? GROUP BY reason",
                                (str(m['id']),)).fetchall():
                reasons[x['reason']] = int(x['n'])
            before = db.execute('SELECT * FROM chat_messages WHERE channel=? AND id<? ORDER BY id DESC LIMIT ?',
                                (m['ch'], m['id'], CONTEXT)).fetchall()
            after = db.execute('SELECT * FROM chat_messages WHERE channel=? AND id>? ORDER BY id LIMIT ?',
                               (m['ch'], m['id'], CONTEXT)).fetchall()
            m.update(reasons=reasons, context=[_msg(x) for x in reversed(before)] + [_msg(x) for x in after])
            items.append(m)
        mutes = [dict(pid=r['pid'], until=float(r['until']), by=r['by_admin'], reason=r['reason'], at=float(r['at']),
                      name=_last_name(db, r['pid']))
                 for r in db.execute('SELECT * FROM chat_mutes WHERE until > ? ORDER BY until DESC LIMIT 100', (t,)).fetchall()]
        town = [_msg(r) for r in db.execute("SELECT * FROM chat_messages WHERE channel='town' ORDER BY id DESC LIMIT 40").fetchall()]
        pending = db.execute('SELECT COUNT(*) FROM chat_messages WHERE reports > 0 AND reviewed_at IS NULL').fetchone()[0]
        auto = db.execute('SELECT COUNT(*) FROM chat_messages WHERE reports > 0 AND hidden = 1').fetchone()[0]
    return dict(items=items, mutes=mutes, town=town, counts=dict(pending=int(pending), auto_hidden=int(auto)),
                mute_hours=list(MUTE_HOURS), now=t)


def _last_name(db, pid: str) -> str:
    r = db.execute('SELECT name FROM chat_messages WHERE pid=? ORDER BY id DESC LIMIT 1', (pid,)).fetchone()
    return r['name'] if r else ''


def act(store, admin: str, data: dict) -> dict:
    """POST /api/admin/chat: {op: hide|keep, id} or {op: mute, pid, hours, reason?} or {op: unmute, pid}."""
    op = data.get('op')
    t = now()
    if op in ('hide', 'keep'):
        mid = data.get('id')
        need(type(mid) is int and mid > 0, 'Tin nhắn không hợp lệ.')

        def run(db):
            r = db.execute('SELECT * FROM chat_messages WHERE id=?', (mid,)).fetchone()
            need(r, 'Không tìm thấy tin nhắn.', 'not_found', 404)
            hidden = 2 if op == 'hide' else 0
            db.execute('UPDATE chat_messages SET hidden=?, reviewed_at=? WHERE id=?', (hidden, t, mid))
            notify(db, dict(op='hide' if hidden else 'unhide', id=mid, ch=r['channel']))
            return _msg(db.execute('SELECT * FROM chat_messages WHERE id=?', (mid,)).fetchone())
        return dict(ok=True, item=store.transaction(run))
    if op in ('mute', 'unmute'):
        pid = data.get('pid')
        need(isinstance(pid, str) and len(pid) == 16 and all(c in '0123456789abcdef' for c in pid), 'Người chơi không hợp lệ.')
        if op == 'mute':
            hours = data.get('hours')
            need(hours in MUTE_HOURS, 'Chỉ khóa 1 giờ, 24 giờ hoặc 7 ngày.')
            reason = str(data.get('reason') or '')[:120]
            until = t + hours * 3600

            def run(db):
                db.execute('INSERT INTO chat_mutes(pid, until, by_admin, reason, at) VALUES(?,?,?,?,?) '
                           'ON CONFLICT(pid) DO UPDATE SET until=excluded.until, by_admin=excluded.by_admin, '
                           'reason=excluded.reason, at=excluded.at', (pid, until, admin[:40], reason, t))
                notify(db, dict(op='mute', pid=pid, until=until))
            store.transaction(run)
            return dict(ok=True, pid=pid, until=until)

        def run(db):
            db.execute('UPDATE chat_mutes SET until=?, by_admin=?, at=? WHERE pid=?', (t, admin[:40], t, pid))
            notify(db, dict(op='mute', pid=pid, until=0))
        store.transaction(run)
        return dict(ok=True, pid=pid, until=0)
    raise ChatAdminError('Thao tác không hợp lệ.')


def forget(store, token: str) -> None:
    """A player deletes their data ("XOA"): their messages lose their text (as their own delete does), they
    leave every chat, and their chat settings go."""
    sid = store.key(token)
    pid = pid_of(sid)
    with store.connect() as db:
        db.execute("UPDATE chat_messages SET text='', deleted=1 WHERE pid=? AND deleted=0", (pid,))
        db.execute('DELETE FROM chat_members WHERE pid=?', (pid,))
        db.execute('DELETE FROM chat_prefs WHERE pid=?', (pid,))
