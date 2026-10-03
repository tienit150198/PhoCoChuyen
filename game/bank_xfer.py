"""💸 Chuyển khoản bạn bè: a player sends xu from the bank app to a friend (owner 03/10, promised to players).

Saves are per-player documents, so a transfer is a row between two saves (`bank_xfers`), the quay_jobs way:

* send (POST /api/bank/xfer/send {to: friend's code, amount, note, src, rid}): ONE transaction writes the sender's
  save (the debit: the bank account, or the cash in hand) under its revision guard, the row (status 'sent') and the
  day counters. The row id comes from (sender, rid): a retried request finds its row and gets the same receipt, a
  double tap racing the first one hits the primary key and rolls back (never paid twice). Two different sends at
  once: the save's revision guard makes the second one recompute on the new balance (never overdrawn).
* receive (on_load, at /api/bootstrap; POST /api/bank/xfer/receive when the ticker's poll says something arrived;
  GET /api/bank/xfer): ONE transaction credits the receiver's save and flips the rows 'sent' -> 'done' (guarded by
  status, so a row is credited once whatever the tabs or processes). Into the bank account when the receiver has
  one (statement line + bank SMS), else into the cash in hand (wallet line). The receiver may be offline for weeks:
  the row waits. Unclaimed for UNCLAIMED_DAYS (or the receiver deleted their data): 'back', and the coins return to
  the sender through the live_effects inbox (kind 'coins', applied once by id).
* No new key in any save: only bank statement/SMS rows and wallet history rows of kinds every build knows, so saves
  stay valid for the previous server, and the previous server leaves the rows waiting (it never reads the table).

Against farming with second accounts (the main risk): both accounts registered ACCOUNT_DAYS days at least, the
sender at life day LIFE_DAYS, friends for FRIEND_MINUTES at least and not blocked, MIN_XU..SEND_DAY xu, at most
SEND_COUNT transfers and SEND_DAY xu sent per VN day, RECV_DAY xu received per VN day. The day counters
(`bank_xfer_days`) move with a conditional upsert in the same transaction, so two senders racing for one receiver
cannot pass the cap. No fee. The rows (sender, receiver, names, amount, note, time, status) are the audit log.

Tables: SCHEMA below (SQLite) and game/pg_schema.py (PostgreSQL, schema 15).
"""
from __future__ import annotations

import hashlib
import json
import re
import time

from . import marriage as mr

MIN_XU = 10              # smallest transfer
SEND_DAY = 2000          # xu a player sends per VN day (also the largest single transfer)
SEND_COUNT = 10          # transfers a player sends per VN day
RECV_DAY = 3000          # xu a player receives per VN day, from everyone
ACCOUNT_DAYS = 1         # both accounts registered at least this long (real days; owner 03/10: 1 day)
LIFE_DAYS = 10           # the sender's save has lived this many days
FRIEND_MINUTES = 60      # friends at least this long
NOTE_MAX = 60
UNCLAIMED_DAYS = 30      # a transfer nobody received goes back to the sender
BATCH = 20               # rows credited per load at most (the rest on the next one)
RECENT = 8
SWEEP_EVERY = 60.0
CHIPS = (50, 100, 200, 500, 1000)
KIND = 'bank'            # wallet history kind (journey.HISTORY_KINDS): every build knows it
BACK_SRC = 'xfer_back'   # live_effects data.src of a refund (game/live_effects.py LABELS)
DAY = 86400
STATUSES = ('sent', 'done', 'back')
GONE = 'Một người chơi'  # the name left on a deleted player's rows (game/marriage.py _display says the same)
RID_RX = re.compile(r'[A-Za-z0-9\-]{8,64}')

SCHEMA = """
CREATE TABLE IF NOT EXISTS bank_xfers (
  id TEXT PRIMARY KEY, code TEXT NOT NULL, sender TEXT NOT NULL, receiver TEXT NOT NULL, from_name TEXT NOT NULL,
  to_name TEXT NOT NULL, amount INTEGER NOT NULL, note TEXT NOT NULL DEFAULT '', src TEXT NOT NULL, status TEXT NOT NULL,
  day TEXT NOT NULL, at REAL NOT NULL, done_at REAL
);
CREATE INDEX IF NOT EXISTS bank_xfers_receiver ON bank_xfers(receiver, status);
CREATE INDEX IF NOT EXISTS bank_xfers_sender ON bank_xfers(sender, at);
CREATE INDEX IF NOT EXISTS bank_xfers_open ON bank_xfers(status, at);
CREATE TABLE IF NOT EXISTS bank_xfer_days (
  sid TEXT NOT NULL, day TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0, n INTEGER NOT NULL DEFAULT 0,
  got INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (sid, day)
);
"""

_swept = [0.0]


class XferError(mr.MarriageError):
    """A refusal (shown as is). A MarriageError so the server answers it like Hôn nhân's."""


def need(cond, message: str, code: str = 'xfer_error', status: int = 400):
    if not cond:
        raise XferError(message, code, status)


def now() -> float:
    return time.time()


def vn_day(t: float | None = None) -> str:
    return time.strftime('%Y-%m-%d', time.gmtime((now() if t is None else t) + 7 * 3600))


def fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def xid_of(sid: str, rid: str) -> str:
    return 'ck-' + hashlib.sha256(f'{sid}|{rid}'.encode()).hexdigest()[:24]


def code_of(xid: str) -> str:
    """The transaction code on the receipt and the statements: 'CK' + 10 digits."""
    return 'CK' + str(int(hashlib.sha256(xid.encode()).hexdigest()[:12], 16) % 10 ** 10).zfill(10)


def clean_note(note) -> str:
    """Optional, one line, NOTE_MAX characters; links, e-mails and phone numbers hidden, rude words masked
    (the feedback/street cleaning: game/player_feedback.py clean_text)."""
    if note is None or note == '':
        return ''
    need(isinstance(note, str) and len(note) <= NOTE_MAX * 4, 'Lời nhắn không hợp lệ.', 'bad_note')
    from . import player_feedback as pfb
    text = re.sub(r'\s+', ' ', note).strip()
    need(len(text) <= NOTE_MAX, f'Lời nhắn tối đa {NOTE_MAX} ký tự nhé.', 'bad_note')
    try:
        return pfb.clean_text(text, NOTE_MAX).replace('\n', ' ')[:NOTE_MAX].strip()
    except pfb.FeedbackError:
        return ''


def _old_enough(db, sid: str) -> bool:
    r = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone()
    if not r:
        return False
    cut = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(now() - ACCOUNT_DAYS * DAY))
    return str(r['created_at']) <= cut


def _friend_since(db, sid: str, other: str) -> float | None:
    r = db.execute('SELECT since FROM friends WHERE sid=? AND friend=?', (sid, other)).fetchone()
    return float(r['since']) if r else None


def _today(db, sid: str, day: str) -> dict:
    r = db.execute('SELECT sent,n,got FROM bank_xfer_days WHERE sid=? AND day=?', (sid, day)).fetchone()
    return dict(sent=int(r['sent']), n=int(r['n']), got=int(r['got'])) if r else dict(sent=0, n=0, got=0)


def _who(store, token: str) -> tuple:
    sid, display = mr.whoami(store, token)
    need(sid, 'Tải lại trang để bắt đầu phiên chơi.', 'session_missing', 401)
    need(display, 'Tạo tài khoản để chuyển khoản nhé.', 'account_required', 403)
    return sid, display


def _lock(store, sid: str, state: dict | None) -> str | None:
    """Why this player cannot send yet (None: they can)."""
    j = (state or {}).get('journey') or {}
    if not j.get('story'):
        return 'Chuyển khoản chỉ có trong hành trình.'
    with store.connect() as db:
        if not _old_enough(db, sid):
            return f'Chuyển khoản mở khi tài khoản đủ {ACCOUNT_DAYS} ngày chơi game (đời thực).'
    if int(j.get('life_day') or 0) < LIFE_DAYS:
        return f'Chuyển khoản mở từ ngày sống {LIFE_DAYS}.'
    return None


def _receipt(r: dict, again: bool = False) -> dict:
    return dict(code=r['code'], to=r['to_name'], amount=int(r['amount']), note=r['note'], src=r['src'], at=int(r['at']),
                status=r['status'], again=again)


# ---------------------------------------------------------------- send
def send(store, sid: str, display: str, d: dict) -> dict:
    rid = d.get('rid')
    need(isinstance(rid, str) and RID_RX.fullmatch(rid), 'Mã giao dịch không hợp lệ. Tải lại trang nhé.', 'bad_rid')
    xid = xid_of(sid, rid)
    with store.connect() as db:
        old = mr._row(db, 'SELECT * FROM bank_xfers WHERE id=? AND sender=?', (xid, sid))
    if old:   # a retry of a transfer that went through: the same receipt, nothing moves
        return dict(message=f'Đã chuyển {fmt(old["amount"])} xu cho {old["to_name"]}.', receipt=_receipt(old, True), changed=False)
    amount = d.get('amount')
    need(type(amount) is int and MIN_XU <= amount <= SEND_DAY, f'Chuyển từ {MIN_XU} tới {fmt(SEND_DAY)} xu mỗi lần nhé.', 'bad_amount')
    src = d.get('src', 'acc')
    need(src in ('acc', 'cash'), 'Chọn chuyển từ tài khoản hoặc tiền mặt nhé.', 'bad_src')
    note = clean_note(d.get('note'))
    loaded = mr._read_state(store, sid)
    need(loaded, 'Không tìm thấy tiến trình.', 'session_missing', 404)
    why = _lock(store, sid, loaded[0])
    need(not why, why or '', 'too_new', 403)
    t = now()
    with store.connect() as db:
        code = d.get('to')
        p = mr._find(db, mr.clean_code(code)) if isinstance(code, str) and code.strip() else None
        need(p and p['sid'] != sid, 'Chọn một người bạn để chuyển nhé.', 'not_found', 404)
        other = p['sid']
        name = mr._display(db, other)
    day = vn_day(t)
    xcode = code_of(xid)
    from . import bank as bk

    def fn(s):
        j = s['journey']
        need(j.get('story') and int(j['life_day']) >= LIFE_DAYS, f'Chuyển khoản mở từ ngày sống {LIFE_DAYS}.', 'too_new', 403)
        b = bk.get(s)
        if src == 'acc':
            need(b, 'Mở tài khoản Ngân hàng Phố trước nhé.', 'no_account')
            need(b['balance'] >= amount, f'Tài khoản chỉ còn {fmt(b["balance"])} xu.', 'not_enough')
            b['balance'] -= amount
            bk._log(b, j['life_day'], 'acc', f'💸 Chuyển khoản tới {name} · {xcode}', -amount)
        else:
            need(j['wallet'] >= amount, f'Tiền mặt chỉ còn {fmt(max(0, j["wallet"]))} xu.', 'not_enough')
            from . import journey as jr
            jr._wallet(j, -amount, KIND, f'💸 Chuyển khoản tới {name} · {xcode}')

    def ops(db):
        since = _friend_since(db, sid, other)
        need(since is not None, 'Chỉ chuyển được cho bạn bè thôi nhé.', 'not_friend', 403)
        need(since <= t - FRIEND_MINUTES * 60, f'Kết bạn đủ {FRIEND_MINUTES} phút rồi mới chuyển được nhé.', 'friend_new', 403)
        need(not mr._blocked(db, sid, other), 'Không chuyển được cho người này.', 'blocked', 403)
        need(_old_enough(db, other), f'Tài khoản của {name} chưa đủ {ACCOUNT_DAYS} ngày chơi game (đời thực).', 'too_new', 403)
        db.execute("INSERT INTO bank_xfers(id,code,sender,receiver,from_name,to_name,amount,note,src,status,day,at) "
                   "VALUES(?,?,?,?,?,?,?,?,?,'sent',?,?)", (xid, xcode, sid, other, display[:24], name[:24], amount, note, src, day, t))
        mine = _today(db, sid, day)
        need(mine['n'] < SEND_COUNT, f'Hôm nay bạn đã chuyển {SEND_COUNT} lần. Mai chuyển tiếp nhé.', 'limit_count', 429)
        left = SEND_DAY - mine['sent']
        need(amount <= left, f'Hôm nay bạn còn chuyển được {fmt(max(0, left))} xu thôi.' if left > 0
             else f'Hôm nay bạn đã chuyển đủ {fmt(SEND_DAY)} xu. Mai chuyển tiếp nhé.', 'limit_send', 429)
        room = RECV_DAY - _today(db, other, day)['got']
        need(amount <= room, f'Hôm nay {name} chỉ nhận thêm được {fmt(max(0, room))} xu.' if room >= MIN_XU
             else f'Hôm nay {name} đã nhận đủ chuyển khoản. Mai gửi tiếp nhé.', 'limit_receive', 429)

        # Conditional upserts: the caps hold even when two transactions race (the row lock / SQLite's write lock).
        # Both rows in sid order, so A->B and B->A at once never wait on each other (no PostgreSQL deadlock).
        def mine_up():
            n = db.execute('INSERT INTO bank_xfer_days(sid,day,sent,n,got) VALUES(?,?,?,1,0) ON CONFLICT(sid,day) DO UPDATE SET '
                           'sent=bank_xfer_days.sent+excluded.sent, n=bank_xfer_days.n+1 '
                           'WHERE bank_xfer_days.sent+excluded.sent<=? AND bank_xfer_days.n<?',
                           (sid, day, amount, SEND_DAY, SEND_COUNT)).rowcount
            need(n == 1, 'Hôm nay bạn đã chuyển đủ rồi. Mai chuyển tiếp nhé.', 'limit_send', 429)

        def theirs_up():
            n = db.execute('INSERT INTO bank_xfer_days(sid,day,sent,n,got) VALUES(?,?,0,0,?) ON CONFLICT(sid,day) DO UPDATE SET '
                           'got=bank_xfer_days.got+excluded.got WHERE bank_xfer_days.got+excluded.got<=?', (other, day, amount, RECV_DAY)).rowcount
            need(n == 1, f'Hôm nay {name} đã nhận đủ chuyển khoản. Mai gửi tiếp nhé.', 'limit_receive', 429)
        for _, up in sorted(((sid, mine_up), (other, theirs_up)), key=lambda x: x[0]):
            up()
    from . import db as dbm
    try:
        mr._mutate_retry(store, {sid: fn}, ops)
    except dbm.IntegrityError:   # the same rid twice at once: the first one went through
        with store.connect() as db:
            old = mr._row(db, 'SELECT * FROM bank_xfers WHERE id=? AND sender=?', (xid, sid))
        need(old, 'Chưa chuyển được, thử lại nhé.', 'busy', 409)
        return dict(message=f'Đã chuyển {fmt(old["amount"])} xu cho {old["to_name"]}.', receipt=_receipt(old, True), changed=False)
    _ping(store, other, f'💸 {display[:24]} chuyển cho bạn {fmt(amount)} xu' + (f': «{note}»' if note else '.'))
    with store.connect() as db:
        row = mr._row(db, 'SELECT * FROM bank_xfers WHERE id=?', (xid,))
    return dict(message=f'Đã chuyển {fmt(amount)} xu cho {name}.', receipt=_receipt(row), changed=True)


def _ping(store, sid: str, text: str) -> None:
    """A phone notification (game/push.py), best effort, after the write: never fails a transfer."""
    from . import push
    try:
        store.transaction(lambda db: push.queue(db, sid, 'gift', text, '/'), 250)
    except Exception:  # noqa: BLE001 - no push tables (tests, a dev database), a busy moment
        pass


# ---------------------------------------------------------------- receive
def _credit(s: dict, r: dict) -> str:
    """One transfer into the receiver's save. Returns where it went: 'acc' or 'cash'."""
    from . import bank as bk
    from . import bank_content as K
    j = s['journey']
    amount, name, note, code = int(r['amount']), r['from_name'], r['note'], r['code']
    said = f': «{note}»' if note else ''
    b = bk.get(s)
    if b is not None:
        b['balance'] += amount
        bk._log(b, j['life_day'], 'acc', f'💸 {name} chuyển khoản{said}', amount)
        bk._inbox(b, j['life_day'], 'sms', f'{K.BANK_NAME}: +{fmt(amount)} xu từ {name}. Mã GD {code}.' + (f' Lời nhắn: «{note}»' if note else ''))
        return 'acc'
    from . import journey as jr
    jr._wallet(j, amount, KIND, f'💸 {name} chuyển khoản{said}')
    return 'cash'


def receive(store, sid: str, story: bool | None = None) -> list:
    """Credit this save's waiting transfers. Returns [{code, name, amount, note, to}] of what arrived now."""
    got: list = []
    for _ in range(6):
        with store.connect() as db:
            rows = mr._rows(db, "SELECT * FROM bank_xfers WHERE receiver=? AND status='sent' ORDER BY at,id LIMIT ?", (sid, BATCH))
        if not rows:
            return got
        if story is None:
            loaded = mr._read_state(store, sid)
            story = bool(loaded and (loaded[0].get('journey') or {}).get('story'))
        if not story:   # a non-story save (dev, tests): the rows wait until it is one
            return got
        where: dict = {}
        ids = [r['id'] for r in rows]

        def fn(s, rows=rows, where=where):
            for r in rows:
                where[r['id']] = _credit(s, r)

        def ops(db, ids=ids):
            t = now()
            marks = ','.join('?' * len(ids))
            if db.execute(f"UPDATE bank_xfers SET status='done',done_at=? WHERE status='sent' AND receiver=? AND id IN ({marks})",
                          (t, sid, *ids)).rowcount != len(ids):
                raise mr._Retry()   # another tab credited some of them: compute again
        try:
            mr._mutate(store, {sid: fn}, ops)
        except mr._Retry:
            time.sleep(.01)
            continue
        got += [dict(code=r['code'], name=r['from_name'], amount=int(r['amount']), note=r['note'], to=where.get(r['id'], 'cash')) for r in rows]
        if len(rows) < BATCH:
            return got
    return got


def on_load(store, token: str, state: dict | None) -> tuple[bool, list]:
    """Bootstrap: credit what friends sent. (the save changed, [what arrived]). One indexed query when nothing waits."""
    sid = store.key(token)
    with store.connect() as db:
        if not db.execute("SELECT 1 FROM bank_xfers WHERE receiver=? AND status='sent' LIMIT 1", (sid,)).fetchone():
            return False, []
    got = receive(store, sid, bool(((state or {}).get('journey') or {}).get('story')))
    return bool(got), got


def waiting(db, sid: str) -> int:
    """Transfers waiting for this save (GET /api/news 'me': the client then asks to receive them)."""
    try:
        return 1 if db.execute("SELECT 1 FROM bank_xfers WHERE receiver=? AND status='sent' LIMIT 1", (sid,)).fetchone() else 0
    except Exception:  # noqa: BLE001 - a database without the table (an older schema): nothing waits
        return 0


# ---------------------------------------------------------------- back to the sender
def _back(db, r: dict) -> bool:
    """'sent' -> 'back', the coins to the sender's live_effects inbox (applied once by this id). True when it moved."""
    if db.execute("UPDATE bank_xfers SET status='back',done_at=? WHERE id=? AND status='sent'", (now(), r['id'])).rowcount != 1:
        return False
    data = json.dumps(dict(src=BACK_SRC, code=r['code']), ensure_ascii=False)
    db.execute("INSERT INTO live_effects(id,sid,kind,amount,data,status,at) VALUES(?,?,'coins',?,?,'pending',?) ON CONFLICT(id) DO NOTHING",
               (f'xfer:{r["id"]}:back', r['sender'], int(r['amount']), data, now()))
    return True


def sweep(store, force: bool = False) -> int:
    """Transfers nobody received in UNCLAIMED_DAYS go back. At most every SWEEP_EVERY seconds a process."""
    t = now()
    if not force and t - _swept[0] < SWEEP_EVERY:
        return 0
    _swept[0] = t
    with store.connect() as db:
        rows = mr._rows(db, "SELECT * FROM bank_xfers WHERE status='sent' AND at<? ORDER BY at LIMIT 50", (t - UNCLAIMED_DAYS * DAY,))
    for r in rows:
        store.transaction(lambda db, r=r: _back(db, r))
    return len(rows)


def forget(store, token: str) -> None:
    """Account deletion: transfers waiting for this player go back to their senders; names leave the other rows."""
    sid = store.key(token)

    def run(db):
        for r in mr._rows(db, "SELECT * FROM bank_xfers WHERE receiver=? AND status='sent'", (sid,)):
            _back(db, r)
        db.execute('UPDATE bank_xfers SET from_name=? WHERE sender=?', (GONE, sid))
        db.execute('UPDATE bank_xfers SET to_name=? WHERE receiver=?', (GONE, sid))
        db.execute('DELETE FROM bank_xfer_days WHERE sid=?', (sid,))
    store.transaction(run)


# ---------------------------------------------------------------- the screen
def view(store, sid: str, state: dict) -> dict:
    """GET /api/bank/xfer: my friends (who can receive), today's room, the last transfers both ways."""
    sweep(store)
    from . import friends as fr
    from .social import pid_of
    t = now()
    day = vn_day(t)
    fr.ensure_codes(store, sid)
    with store.connect() as db:
        rows = mr._rows(db, 'SELECT f.friend, f.since, p.code FROM friends f JOIN marriage_people p ON p.sid=f.friend '
                            'WHERE f.sid=? ORDER BY f.since LIMIT ?', (sid, fr.FRIENDS_MAX))
        faces = {}
        if rows:
            pids = {pid_of(r['friend']): r['friend'] for r in rows}
            marks = ','.join('?' * len(pids))
            try:
                for f in db.execute(f'SELECT pid, code FROM chat_faces WHERE pid IN ({marks})', tuple(pids)).fetchall():
                    faces[pids[f['pid']]] = f['code']
            except Exception:  # noqa: BLE001 - no chat tables: plain avatars
                pass
        friends = []
        for r in rows:
            why = None
            if float(r['since']) > t - FRIEND_MINUTES * 60:
                why = f'Kết bạn đủ {FRIEND_MINUTES} phút rồi chuyển nhé'
            elif mr._blocked(db, sid, r['friend']):
                continue
            elif not _old_enough(db, r['friend']):
                why = f'Tài khoản bạn ấy chưa đủ {ACCOUNT_DAYS} ngày chơi game (đời thực)'
            friends.append(dict(code=r['code'], name=mr._display(db, r['friend']), fc=faces.get(r['friend']), ok=why is None, why=why))
        friends.sort(key=lambda f: (not f['ok'], f['name'].lower()))
        mine = _today(db, sid, day)
        recent = []
        for r in mr._rows(db, 'SELECT * FROM bank_xfers WHERE sender=? ORDER BY at DESC LIMIT ?', (sid, RECENT)):
            recent.append((float(r['at']), dict(dir='out', code=r['code'], name=r['to_name'], amount=int(r['amount']), note=r['note'],
                                                status=r['status'], at=int(r['at']))))
        for r in mr._rows(db, "SELECT * FROM bank_xfers WHERE receiver=? AND status='done' ORDER BY done_at DESC LIMIT ?", (sid, RECENT)):
            recent.append((float(r['done_at'] or r['at']), dict(dir='in', code=r['code'], name=r['from_name'], amount=int(r['amount']),
                                                                 note=r['note'], status=r['status'], at=int(r['done_at'] or r['at']))))
    recent.sort(key=lambda x: -x[0])
    return dict(friends=friends, lock=_lock(store, sid, state), recent=[x[1] for x in recent[:RECENT]],
                today=dict(sent=mine['sent'], n=mine['n'], left=max(0, SEND_DAY - mine['sent']), count_left=max(0, SEND_COUNT - mine['n'])),
                rules=dict(min=MIN_XU, send_day=SEND_DAY, send_count=SEND_COUNT, recv_day=RECV_DAY, account_days=ACCOUNT_DAYS,
                           life_days=LIFE_DAYS, friend_minutes=FRIEND_MINUTES, note_max=NOTE_MAX, chips=list(CHIPS)))


def get(store, token: str, state: dict) -> dict:
    """GET /api/bank/xfer: what friends sent is credited first (the state comes back when it moved)."""
    sid, _ = _who(store, token)
    got = receive(store, sid)
    if got:
        state = mr._read_state(store, sid)[0]
    out = view(store, sid, state)
    out.update(got=got, changed=bool(got))
    return out


def act(store, token: str, op: str, d: dict) -> dict:
    """POST /api/bank/xfer/<op>: send | receive. Returns {message, changed, …}."""
    need(isinstance(d, dict), 'Dữ liệu không hợp lệ.')
    sid, display = _who(store, token)
    if op == 'receive':
        got = receive(store, sid)
        return dict(message='', got=got, changed=bool(got))
    need(op == 'send', 'Không có thao tác này.', 'not_found', 404)
    mr.ensure_person(store, sid)
    return send(store, sid, display, d)
