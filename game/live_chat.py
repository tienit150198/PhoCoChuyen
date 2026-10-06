"""💬 Chat, the game server's side: the PostgreSQL tables in game/pg_schema.py, the admin "Chat" tab
(reports queue, hide / keep, mute 1 h / 24 h / 7 d) and the cleanup when a player deletes their data.

The chat itself runs in the live service (live/, `python3 -m live`, a WebSocket per player): it writes
messages, reports and auto-hides. The game server never sends a chat message. An admin decision is written
here, then announced with `pg_notify('mnl_live', <json>)` so the live service applies it at once (drops a
hidden message from its buffers and from every open screen, mutes an online player).

DMs and groups are never deleted (owner rule); Cả phố keeps its newest 2,000 messages (owner, 01/10: the live
service prunes older ones, except a reported one still waiting for review). An author's own delete (Thu hồi, within 24 h)
empties the text (deleted=1; a message already reported keeps what was written in `raw`, for the admin); a hidden
message keeps its text for the admin (hidden 1 = three reports, waiting for review; 2 = hidden by an admin).

📌 Admins (ADMIN_USERS) post on Cả phố freely (owner, 01/10): their rows have adm=1 (a row with pid 'admin', written
straight into the database as an announcement, counts as one too). One message of Cả phố can be pinned
(`chat_pins`, one row per channel, written by the live service or scripts/chat_pin.py); hiding a message here, or a
player deleting their data, takes its pin away.

🙂 `chat_faces` (one row per player: the code of their drawn chat avatar, live/faces.py) is written by the live service;
deleting a player's data removes it here.

🗑️ "Xóa ở phía tôi" (live/chat.py): `chat_hides` (one message gone from one player's screens) and `chat_clears` (a whole
chat emptied for one player, up to an id) are written by the live service; the messages stay, so this tab and the
reports queue still show them. Deleting a player's data removes those rows here.

🔎 The admin "Tin nhắn" tab (search(), GET /api/admin/chat/messages): every chat, 200 messages a page, newest first,
filtered by kind (Cả phố / nhắn riêng / nhóm), chat, player, and words (text, original, name). Each request reads
at most WINDOW ids back from its cursor (the primary key), so a search never scans the whole table; "Tải cũ hơn"
moves the window. Since 1.2.2 a message the filter masked keeps what was typed in `raw` (admins only: the live
service never sends it to players); older messages only have the masked text.

🛟 Safety (moderation #14, 06/10): a report with reason 'minor' ("An toàn / trẻ vị thành niên") puts the message at the
top of the queue, highlighted (`safety`), until an admin decides; one report is enough to list it, nothing is hidden
or banned by itself. Tools, never an automatic ban: mute for N minutes (MUTE_MINUTES), 🐢 slow mode for one player or
for all of Cả phố (`chat_slow`, SCHEMA_VERSION 24: one message per `every` seconds until `until`), and the list of
account names that fail the name filter (game/accounts.py offending_names) with a one-click rename to "Cư dân <uid>".
"""
from __future__ import annotations

import json
import re
import time


NOTIFY_CHANNEL = 'mnl_live'
MUTE_HOURS = (1, 24, 168)
MUTE_MINUTES = (10, 30, 60, 180, 1440, 10080)   # 🔇 "khóa N phút" (moderation #14); hours above still accepted
SLOW_SECONDS = (30, 60, 120, 300)              # 🐢 one Cả phố message per N seconds…
SLOW_MINUTES = (30, 60, 180, 1440)             # …for this long
SLOW_TOWN = 'town'                             # the chat_slow row for everyone on Cả phố
QUEUE_MAX = 50
CONTEXT = 3                 # messages shown before and after a reported one
REASONS = ('spam', 'rude', 'private', 'scam', 'other', 'minor')   # minor: 🛟 an toàn / trẻ vị thành niên
SAFETY = 'minor'
PAGE = 200                  # messages per page of the "Tin nhắn" tab
WINDOW = 20000              # ids looked at per search request at most (one primary-key range)
KINDS = ('all', 'town', 'dm', 'group')
PID = re.compile(r'[0-9a-f]{16}|admin')





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
    db.execute('SELECT pg_notify(?, ?)', (NOTIFY_CHANNEL, json.dumps(event, separators=(',', ':'))))


def _kind(channel: str) -> str:
    return 'town' if channel == 'town' else 'dm' if channel.startswith('dm:') else 'group' if channel.startswith('g:') else channel.split(':', 1)[0]


def _msg(r) -> dict:
    return dict(id=int(r['id']), ch=r['channel'], kind=_kind(r['channel']), pid=r['pid'], name=r['name'], av=r['av'],
                text=r['text'], at=float(r['at']), hidden=int(r['hidden']), deleted=int(r['deleted']), reports=int(r['reports']),
                reviewed=r['reviewed_at'] is not None, adm=1 if r['pid'] == 'admin' or _adm(r) else 0, raw=_raw(r))


def _raw(r):
    """What the player typed when the filter masked part of it (admins only), else None."""
    try:
        raw = r['raw']
    except (IndexError, KeyError):
        return None
    return raw if raw and raw != r['text'] else None


def _adm(r) -> bool:
    try:
        return bool(r['adm'])
    except (IndexError, KeyError):
        return False


def view(store) -> dict:
    """The admin "Chat" tab: reported messages waiting for a decision (with a few messages of context and the
    reasons), the active mutes, and the last messages of Cả phố."""
    t = now()
    with store.connect() as db:
        # 🛟 safety reports first (all of them that wait), then the newest other reports.
        safe_ids = [int(x['id']) for x in db.execute(
            "SELECT m.id FROM chat_messages m WHERE m.reports > 0 AND m.reviewed_at IS NULL AND EXISTS (SELECT 1 FROM reports r "
            "WHERE r.kind='chat' AND r.reason=? AND r.target=CAST(m.id AS text)) ORDER BY m.id DESC LIMIT ?", (SAFETY, QUEUE_MAX)).fetchall()]
        rows = [db.execute('SELECT * FROM chat_messages WHERE id=?', (i,)).fetchone() for i in safe_ids]
        rows += [r for r in db.execute('SELECT * FROM chat_messages WHERE reports > 0 AND reviewed_at IS NULL ORDER BY id DESC LIMIT ?',
                                       (QUEUE_MAX,)).fetchall() if int(r['id']) not in safe_ids]
        items = []
        for r in rows:
            if r is None:
                continue
            m = _msg(r)
            reasons = {}
            for x in db.execute("SELECT reason, COUNT(*) AS n FROM reports WHERE kind='chat' AND target=? GROUP BY reason",
                                (str(m['id']),)).fetchall():
                reasons[x['reason']] = int(x['n'])
            before = db.execute('SELECT * FROM chat_messages WHERE channel=? AND id<? ORDER BY id DESC LIMIT ?',
                                (m['ch'], m['id'], CONTEXT)).fetchall()
            after = db.execute('SELECT * FROM chat_messages WHERE channel=? AND id>? ORDER BY id LIMIT ?',
                               (m['ch'], m['id'], CONTEXT)).fetchall()
            m.update(reasons=reasons, context=[_msg(x) for x in reversed(before)] + [_msg(x) for x in after], safety=SAFETY in reasons)
            items.append(m)
        mutes = [dict(pid=r['pid'], until=float(r['until']), by=r['by_admin'], reason=r['reason'], at=float(r['at']),
                      name=_last_name(db, r['pid']))
                 for r in db.execute('SELECT * FROM chat_mutes WHERE until > ? ORDER BY until DESC LIMIT 100', (t,)).fetchall()]
        town = [_msg(r) for r in db.execute("SELECT * FROM chat_messages WHERE channel='town' ORDER BY id DESC LIMIT 40").fetchall()]
        pending = db.execute('SELECT COUNT(*) FROM chat_messages WHERE reports > 0 AND reviewed_at IS NULL').fetchone()[0]
        auto = db.execute('SELECT COUNT(*) FROM chat_messages WHERE reports > 0 AND hidden = 1').fetchone()[0]
        slows = [dict(pid=r['pid'], every=float(r['every']), until=float(r['until']), by=r['by_admin'], at=float(r['at']),
                      name='Cả phố' if r['pid'] == SLOW_TOWN else _last_name(db, r['pid']))
                 for r in db.execute('SELECT * FROM chat_slow WHERE until > ? ORDER BY until DESC LIMIT 100', (t,)).fetchall()]
        from .accounts import offending_names
        names = offending_names(db)
    return dict(items=items, mutes=mutes, town=town, slows=slows, names=names,
                counts=dict(pending=int(pending), auto_hidden=int(auto), safety=len(safe_ids), names=len(names)),
                mute_hours=list(MUTE_HOURS), mute_minutes=list(MUTE_MINUTES), slow_seconds=list(SLOW_SECONDS),
                slow_minutes=list(SLOW_MINUTES), now=t)


def _like(term: str) -> str:
    return '%' + re.sub(r'([!%_])', r'!\1', term) + '%'


def search(store, q: dict) -> dict:
    """GET /api/admin/chat/messages?kind=&ch=&pid=&q=&before=: one page of messages, newest first.

    kind: all | town | dm | group; ch: one chat id; pid: one player (a 16-hex pid, or 'admin'); q: words in the text,
    the original (raw) or the name; a q that is a pid filters by that player. before: the cursor (ids below it).
    Bounded: a chat (ch), a player (pid) or Cả phố without words walk an index ((channel, id), (pid, id)) for at
    most PAGE + 1 rows; anything else (words, DMs, groups, everything) looks only at the WINDOW ids below the cursor.
    `next` is the cursor of the next page (None: nothing older), `scanned` the oldest id looked at when windowed."""
    kind = q.get('kind') if q.get('kind') in KINDS else 'all'
    ch = q.get('ch') if isinstance(q.get('ch'), str) and 0 < len(q.get('ch')) <= 64 else None
    pid = str(q.get('pid') or '').strip().lower() or None
    need(pid is None or PID.fullmatch(pid), 'Mã người chơi không hợp lệ.')
    text = ' '.join(str(q.get('q') or '').split())[:80]
    if text and not pid and PID.fullmatch(text.lower()):
        pid, text = text.lower(), ''
    before = q.get('before')
    before = int(before) if isinstance(before, (int, str)) and str(before).isdigit() and int(before) > 0 else None
    with store.connect() as db:
        top = int(db.execute('SELECT MAX(id) FROM chat_messages').fetchone()[0] or 0)
        hi = min(before - 1, top) if before else top
        where, args = ['id <= ?'], [hi]
        indexed = not text and (ch is not None or pid is not None or kind == 'town')
        lo = None
        if not indexed:
            lo = max(0, hi - WINDOW)
            where.append('id > ?')
            args.append(lo)
        if ch:
            where.append('channel = ?')
            args.append(ch)
        elif kind == 'town':
            where.append("channel = 'town'")
        elif kind == 'dm':
            where.append("substr(channel, 1, 3) = 'dm:'")
        elif kind == 'group':
            where.append("substr(channel, 1, 2) = 'g:'")
        if pid:
            where.append('pid = ?')
            args.append(pid)
        if text:
            op = 'ILIKE'
            where.append(f"(text {op} ? ESCAPE '!' OR raw {op} ? ESCAPE '!' OR name {op} ? ESCAPE '!')")
            args += [_like(text)] * 3
        rows = db.execute(f"SELECT * FROM chat_messages WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT ?",
                          (*args, PAGE + 1)).fetchall() if hi > 0 else []
        more = len(rows) > PAGE
        items = [_msg(r) for r in rows[:PAGE]]
        groups = sorted({m['ch'] for m in items if m['kind'] == 'group'})
        titles = {}
        if groups:
            titles = {r['id']: r['title'] for r in db.execute(
                f"SELECT id, title FROM chat_channels WHERE id IN ({','.join('?' * len(groups))})", groups).fetchall()}
        for m in items:
            if m['ch'] in titles:
                m['title'] = titles[m['ch']]
        player = dict(pid=pid, name=_last_name(db, pid)) if pid else None
    nxt = items[-1]['id'] if more else (lo + 1 if lo else None)
    return dict(items=items, next=nxt, scanned=lo, top=top, page=PAGE, window=WINDOW, player=player,
                filters=dict(kind=kind, ch=ch, pid=pid, q=text))


def _last_name(db, pid: str) -> str:
    r = db.execute('SELECT name FROM chat_messages WHERE pid=? ORDER BY id DESC LIMIT 1', (pid,)).fetchone()
    return r['name'] if r else ''


def _pid_ok(pid) -> bool:
    return isinstance(pid, str) and len(pid) == 16 and all(c in '0123456789abcdef' for c in pid)


def act(store, admin: str, data: dict) -> dict:
    """POST /api/admin/chat: {op: hide|keep, id} or {op: mute, pid, hours | minutes, reason?} or {op: unmute, pid}
    or 🐢 {op: slow, pid | 'town', seconds, minutes} / {op: unslow, pid | 'town'} or {op: rename, uid} (names list)."""
    op = data.get('op')
    t = now()
    if op == 'rename':
        from .accounts import rename_safe, AccountError
        try:
            return rename_safe(store, data.get('uid'), admin)
        except AccountError as e:
            raise ChatAdminError(e.message, e.code, e.status) from None
    if op in ('slow', 'unslow'):
        pid = data.get('pid')
        need(pid == SLOW_TOWN or _pid_ok(pid), 'Người chơi không hợp lệ.')
        if op == 'slow':
            every, minutes = data.get('seconds'), data.get('minutes')
            need(every in SLOW_SECONDS, 'Chọn 30, 60, 120 hoặc 300 giây một tin.')
            need(minutes in SLOW_MINUTES, 'Chọn thời hạn 30 phút, 1 giờ, 3 giờ hoặc 24 giờ.')
            until = t + minutes * 60
        else:
            every, until = 0, t

        def run(db):
            db.execute('INSERT INTO chat_slow(pid, every, until, by_admin, at) VALUES(?,?,?,?,?) '
                       'ON CONFLICT(pid) DO UPDATE SET every=excluded.every, until=excluded.until, by_admin=excluded.by_admin, '
                       'at=excluded.at', (pid, float(every), until, admin[:40], t))
            notify(db, dict(op='slow', pid=pid))
        store.transaction(run)
        return dict(ok=True, pid=pid, every=every, until=until if op == 'slow' else 0)
    if op in ('hide', 'keep'):
        mid = data.get('id')
        need(type(mid) is int and mid > 0, 'Tin nhắn không hợp lệ.')

        def run(db):
            r = db.execute('SELECT * FROM chat_messages WHERE id=?', (mid,)).fetchone()
            need(r, 'Không tìm thấy tin nhắn.', 'not_found', 404)
            hidden = 2 if op == 'hide' else 0
            db.execute('UPDATE chat_messages SET hidden=?, reviewed_at=? WHERE id=?', (hidden, t, mid))
            if hidden:
                db.execute('DELETE FROM chat_pins WHERE msg=?', (mid,))   # a hidden message is never pinned
            notify(db, dict(op='hide' if hidden else 'unhide', id=mid, ch=r['channel']))
            return _msg(db.execute('SELECT * FROM chat_messages WHERE id=?', (mid,)).fetchone())
        return dict(ok=True, item=store.transaction(run))
    if op in ('mute', 'unmute'):
        pid = data.get('pid')
        need(_pid_ok(pid), 'Người chơi không hợp lệ.')
        if op == 'mute':
            hours, minutes = data.get('hours'), data.get('minutes')
            if minutes is not None:
                need(minutes in MUTE_MINUTES, 'Chỉ khóa 10 phút, 30 phút, 1 giờ, 3 giờ, 24 giờ hoặc 7 ngày.')
            else:
                need(hours in MUTE_HOURS, 'Chỉ khóa 1 giờ, 24 giờ hoặc 7 ngày.')
                minutes = hours * 60
            reason = str(data.get('reason') or '')[:120]
            until = t + minutes * 60

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
        db.execute('DELETE FROM chat_pins WHERE msg IN (SELECT id FROM chat_messages WHERE pid=?)', (pid,))
        db.execute('DELETE FROM chat_reacts WHERE pid=?', (pid,))
        db.execute("UPDATE chat_messages SET text='', raw=NULL, deleted=1 WHERE pid=? AND deleted=0", (pid,))
        db.execute('DELETE FROM chat_members WHERE pid=?', (pid,))
        db.execute('DELETE FROM chat_prefs WHERE pid=?', (pid,))
        db.execute('DELETE FROM chat_faces WHERE pid=?', (pid,))
        db.execute('DELETE FROM chat_hides WHERE pid=?', (pid,))    # 🗑️ what they deleted on their side
        db.execute('DELETE FROM chat_clears WHERE pid=?', (pid,))
        db.execute('DELETE FROM chat_slow WHERE pid=?', (pid,))   # 🐢 their slow mode
        notify(db, dict(op='face', pid=pid))   # 🙂 the live service forgets the face it keeps in memory
