"""🎁 Quà từ Phố Có Chuyện: a private gift from the operator to one save (an apology after an
outage, a thank-you). Only that save ever sees it.

Flow (statuses pending → applied → seen)
* scripts/grant_gift.py inserts a row in `system_gifts` (status 'pending'). It never touches a save.
* The player's next load (/api/bootstrap, after the marriage/social hooks) runs on_load: each
  pending gift goes through Store.command, the engine's normal command path, as the internal
  action `sys_gift` with the fixed request id ``sysgift-<id>``. The coins land in the journey
  wallet (👛 Ví) with a wallet-history row (kind 'life', LABEL), then the row becomes 'applied'.
* Paid once, whatever the retries, tabs or processes:
  - the request id: a second tab or a retry replays the stored receipt instead of paying again;
  - the save keeps the ids it was paid for (``journey['gifts']``, the last KEPT): once receipts
    are pruned (RECEIPT_DAYS), a gift whose row was not marked applied (a crash between the two
    writes) is still a no-op;
  - the row flips pending → applied only from 'pending'.
* Bootstrap lists the applied gifts not acknowledged yet (`gifts`: id, coins, title, text). The
  client (public/js/v4/gift.js) shows one card per gift; its button POSTs /api/gift/seen, which
  sets seen_at: the card never shows again, on any device.
* Story saves only (production runs the story for every save). A non-story save (dev, tests)
  keeps its gift pending, never paid elsewhere, until it is a story save.
* Loading the game never fails because of a gift: the server logs the error and loads the save.

Tables: SCHEMA below (SQLite, tests and dev) and game/pg_schema.py (PostgreSQL, production).
"""
from __future__ import annotations

import hashlib
import re
import time

from . import db as dbm

ACTION = 'sys_gift'                 # internal command (game/engine.py), never accepted from a client
RID = 'sysgift-'                    # request id prefix: sysgift-<id>
KIND = 'life'                       # journey wallet history kind (journey.HISTORY_KINDS): old saves stay valid
LABEL = '🎁 Quà từ Phố Có Chuyện'
MAX_COINS = 100_000                 # the owner's largest gift (03/10: 100k xu for one player)
LARGE = 1000                        # above this the grant tool wants --large: a typo (10000 for 100) is refused, not paid
TITLE_MAX = 80
TEXT_MAX = 300
KEPT = 50                           # ids of paid gifts kept in the save
SHOWN = 5                           # cards per load at most (the rest come on the next load)
ID_RX = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{2,63}')
_CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')

SCHEMA = """
CREATE TABLE IF NOT EXISTS system_gifts (
  id TEXT PRIMARY KEY, sid TEXT NOT NULL, coins INTEGER NOT NULL, title TEXT NOT NULL, text TEXT NOT NULL,
  status TEXT NOT NULL, created REAL NOT NULL, applied_at REAL, seen_at REAL
);
CREATE INDEX IF NOT EXISTS system_gifts_sid ON system_gifts(sid, status);
"""


class GiftError(ValueError):
    pass


def now() -> float:
    return time.time()


def valid_id(gid) -> bool:
    return isinstance(gid, str) and bool(ID_RX.fullmatch(gid))


def clean(text, most: int) -> str:
    """One line of text for the card: no control characters (newlines kept), trimmed, 1..most chars."""
    if not isinstance(text, str):
        raise GiftError('Nội dung cần là chữ.')
    out = _CONTROL.sub('', text).strip()
    if not 1 <= len(out) <= most:
        raise GiftError(f'Cần 1–{most} ký tự (đang có {len(out)}).')
    return out


# ---------------------------------------------------------------- the save (reducer, validation)
def apply(s: dict, p: dict) -> tuple[dict, dict]:
    """`sys_gift` {id, coins}: the coins into the journey wallet, once per gift id."""
    from . import engine as e
    from . import journey as jr
    j = s['journey']
    e.need(j.get('story'), 'Quà vào ví chỉ có trong hành trình.', 'not_story')
    gid = p.get('id')
    e.need(valid_id(gid), 'Mã quà không hợp lệ.')
    coins = e.integer(p.get('coins'), 1, MAX_COINS)
    got = j.get('gifts') if isinstance(j.get('gifts'), list) else []
    if gid in got:   # already paid (a receipt pruned meanwhile): nothing moves
        return s, dict(message='', gift=dict(id=gid, coins=0, already=True))
    jr._wallet(j, coins, KIND, LABEL)
    j['gifts'] = (got + [gid])[-KEPT:]
    e.validate_state(s)
    return s, dict(message=f'+{coins} xu vào ví.', gift=dict(id=gid, coins=coins))


def validate(j: dict) -> None:
    """journey['gifts'] (optional): ids of the gifts paid into this wallet."""
    if 'gifts' not in j:
        return
    from .engine import need
    g = j['gifts']
    need(isinstance(g, list) and len(g) <= KEPT and all(valid_id(x) for x in g) and len(set(g)) == len(g),
         'Danh sách quà trong bản lưu không hợp lệ.', 'invalid_save')


# ---------------------------------------------------------------- loading a save
def on_load(store, token: str, state: dict | None) -> tuple[bool, list]:
    """Bootstrap: pay this save's pending gifts, list the ones not acknowledged yet.
    Returns (the save changed, [{id, coins, title, text}]). One indexed query when there is none."""
    from .engine import GameError
    sid = store.key(token)
    with store.connect() as db:
        rows = [dict(r) for r in db.execute("SELECT id,coins,title,text,status FROM system_gifts "
                                            "WHERE sid=? AND status IN ('pending','applied') ORDER BY created,id LIMIT 20", (sid,))]
    if not rows:
        return False, []
    story = bool(((state or {}).get('journey') or {}).get('story'))
    changed = False
    for r in rows:
        if r['status'] != 'pending' or not story:
            continue
        try:
            store.command(token, RID + r['id'], None, None, ACTION, dict(id=r['id'], coins=int(r['coins'])), internal=True)
        except GameError:   # refused (e.g. a receipt with other content): stays pending, the operator looks
            continue
        t = now()
        store.transaction(lambda db, gid=r['id'], t=t: db.execute(
            "UPDATE system_gifts SET status='applied',applied_at=? WHERE id=? AND sid=? AND status='pending'", (t, gid, sid)))
        r['status'] = 'applied'
        changed = True
    shown = [dict(id=r['id'], coins=int(r['coins']), title=r['title'], text=r['text']) for r in rows if r['status'] == 'applied']
    return changed, shown[:SHOWN]


def seen(store, token: str, gid) -> bool:
    """POST /api/gift/seen {id}: this save's card was acknowledged. False for an unknown id,
    someone else's gift, or one already seen (the answer is the same: nothing to show)."""
    if not valid_id(gid):
        return False
    sid = store.key(token)
    t = now()
    return store.transaction(lambda db: db.execute(
        "UPDATE system_gifts SET status='seen',seen_at=? WHERE id=? AND sid=? AND status='applied'", (t, gid, sid)).rowcount) == 1


def forget(store, token: str) -> None:
    """Account deletion ("Xóa dữ liệu"): the gifts addressed to this save go with it."""
    sid = store.key(token)
    store.transaction(lambda db: db.execute('DELETE FROM system_gifts WHERE sid=?', (sid,)))


# ---------------------------------------------------------------- granting (scripts/grant_gift.py)
def default_id(sid: str, coins: int, title: str, text: str) -> str:
    """The same gift (save, coins, words) always gets the same id: running a grant twice is a no-op."""
    h = hashlib.sha256('\x1f'.join((sid, str(coins), title, text)).encode()).hexdigest()
    return 'g-' + h[:20]


def grant(store, sid: str, coins: int, title: str, text: str, gid: str | None = None, dry_run: bool = False) -> dict:
    """Queue one gift for a save. Idempotent by id: the same id with the same content is 'exists';
    with other content, GiftError (nothing written). Returns {status, gift}, status in
    'created' | 'exists' | 'would_create' (dry run)."""
    if not isinstance(sid, str) or not sid or len(sid) > 128:
        raise GiftError('sid không hợp lệ.')
    if type(coins) is not int or not 1 <= coins <= MAX_COINS:
        raise GiftError(f'Số xu cần từ 1 đến {MAX_COINS}.')
    title, text = clean(title, TITLE_MAX), clean(text, TEXT_MAX)
    gid = gid or default_id(sid, coins, title, text)
    if not valid_id(gid):
        raise GiftError('Mã quà (--id) chỉ gồm chữ, số, . _ - (3–64 ký tự), bắt đầu bằng chữ hoặc số.')
    with store.connect() as db:
        if not db.execute('SELECT 1 FROM sessions WHERE sid=?', (sid,)).fetchone():
            raise GiftError('Không có bản lưu nào với sid này.')
    gift = dict(id=gid, sid=sid, coins=coins, title=title, text=text)

    def same(row) -> dict:
        have = dict(row)
        if (have['sid'], int(have['coins']), have['title'], have['text']) != (sid, coins, title, text):
            raise GiftError(f'Mã quà {gid} đã dùng cho một quà khác (sid/xu/chữ khác): không ghi gì.')
        return dict(status='exists', gift=have)
    with store.connect() as db:
        row = db.execute('SELECT * FROM system_gifts WHERE id=?', (gid,)).fetchone()
    if row:
        return same(row)
    if dry_run:
        return dict(status='would_create', gift=gift)
    try:
        store.transaction(lambda db: db.execute(
            "INSERT INTO system_gifts(id,sid,coins,title,text,status,created) VALUES(?,?,?,?,?,'pending',?)",
            (gid, sid, coins, title, text, now())))
    except dbm.IntegrityError:   # the same id landed first (two runs at once)
        with store.connect() as db:
            return same(db.execute('SELECT * FROM system_gifts WHERE id=?', (gid,)).fetchone())
    with store.connect() as db:
        return dict(status='created', gift=dict(db.execute('SELECT * FROM system_gifts WHERE id=?', (gid,)).fetchone()))
