"""🧧 Rewards from the live service (live/), paid into the save by the game server.

The live service never writes a save. When it grants something (Đi dạo: the first to tap a lucky red envelope
gets a few xu; dates, phase 3: a spirit boost), it inserts a `live_effects` row (live/effects.py grant: the
row id is the idempotency key, a daily cap per kind and player, status 'pending'). This module pays them, the
game/system_gift.py way:

* on_load(store, token, state), called by /api/bootstrap (and by POST /api/live/effects, which the stroll
  calls right after an envelope so the wallet moves at once): each pending row of a kind this build knows
  goes through Store.command, the engine's own command path, as the internal action `live_fx` with the fixed
  request id ``live-<hash of the row id>``; then the row becomes 'applied'.
* Paid once, whatever the retries, tabs or processes:
  - the request id: a second tab or a retry replays the stored receipt instead of paying again;
  - the save keeps a short hash of the rows it was paid for (``journey['live_fx']``, the last KEPT): once
    receipts are pruned, a row not marked applied (a crash between the two writes) is still a no-op;
  - the row flips pending → applied only from 'pending'.
* coins: into the journey wallet (👛 Ví) with a wallet-history row (kind 'life', the label of its source).
  spirit: the life spirit (0-100), when the save has one. Kinds this build does not pay stay pending for a
  later build (never paid elsewhere). Story saves only, like system gifts.
* Loading the game never fails because of an effect: the caller logs the error and loads the save.

Table: `live_effects` (game/live_chat.py SCHEMA on SQLite, game/pg_schema.py on PostgreSQL).
"""
from __future__ import annotations

import hashlib
import json
import re
import time

ACTION = 'live_fx'                  # internal command (game/engine.py), never accepted from a client
RID = 'live-'                       # request id prefix: live-<hash>
KIND = 'life'                       # journey wallet history kind (journey.HISTORY_KINDS): old saves stay valid
PAYS = ('coins', 'spirit')          # kinds this build applies
LABELS = dict(envelope='🧧 Lì xì dạo phố', date='💕 Buổi hẹn trên phố')
LABEL = '🎁 Quà từ khu phố'         # any other source
AMOUNT_MAX = 1000                   # live/effects.py AMOUNT_MAX
KEPT = 60                           # hashes of paid rows kept in the save
BATCH = 20                          # rows paid per load at most (the rest on the next load)
ID_RX = re.compile(r'[A-Za-z0-9][A-Za-z0-9:._\-]{2,119}')
HASH_RX = re.compile(r'[0-9a-f]{16}')


def now() -> float:
    return time.time()


def valid_id(eid) -> bool:
    return isinstance(eid, str) and bool(ID_RX.fullmatch(eid))


def short(eid: str) -> str:
    """The 16-hex hash of a row id kept in the save (rows ids can be long)."""
    return hashlib.sha256(eid.encode()).hexdigest()[:16]


# ---------------------------------------------------------------- the save (reducer, validation)
def apply(s: dict, p: dict) -> tuple[dict, dict]:
    """`live_fx` {id, kind, amount, src}: one granted reward into the save, once per row id."""
    from . import engine as e
    from . import journey as jr
    j = s['journey']
    e.need(j.get('story'), 'Quà vào ví chỉ có trong hành trình.', 'not_story')
    eid = p.get('id')
    e.need(valid_id(eid), 'Mã phần thưởng không hợp lệ.')
    kind = p.get('kind')
    e.need(kind in PAYS, 'Loại phần thưởng không hợp lệ.')
    amount = e.integer(p.get('amount'), 1, AMOUNT_MAX)
    h = short(eid)
    got = j.get('live_fx') if isinstance(j.get('live_fx'), list) else []
    if h in got:   # already paid (a receipt pruned meanwhile): nothing moves
        return s, dict(message='', live=dict(id=eid, kind=kind, amount=0, already=True))
    if kind == 'coins':
        jr._wallet(j, amount, KIND, LABELS.get(p.get('src'), LABEL))
        message = f'+{amount} xu vào ví.'
    else:
        L = j.get('life')
        if isinstance(L, dict) and type(L.get('spirit')) is int:
            L['spirit'] = max(0, min(100, L['spirit'] + amount))
        message = ''
    j['live_fx'] = (got + [h])[-KEPT:]
    e.validate_state(s)
    return s, dict(message=message, live=dict(id=eid, kind=kind, amount=amount))


def validate(j: dict) -> None:
    """journey['live_fx'] (optional): hashes of the live rewards paid into this save."""
    if 'live_fx' not in j:
        return
    from .engine import need
    g = j['live_fx']
    need(isinstance(g, list) and len(g) <= KEPT and all(isinstance(x, str) and HASH_RX.fullmatch(x) for x in g) and len(set(g)) == len(g),
         'Danh sách phần thưởng trong bản lưu không hợp lệ.', 'invalid_save')


# ---------------------------------------------------------------- loading a save
def on_load(store, token: str, state: dict | None) -> bool:
    """Pay this save's pending live rewards. True when the save changed. One indexed query when there is none."""
    from .engine import GameError
    sid = store.key(token)
    marks = ','.join('?' * len(PAYS))
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(f"SELECT id,kind,amount,data FROM live_effects WHERE sid=? AND status='pending' "
                                            f'AND kind IN ({marks}) ORDER BY at,id LIMIT {BATCH}', (sid, *PAYS))]
    if not rows or not ((state or {}).get('journey') or {}).get('story'):
        return False
    changed = False
    for r in rows:
        try:
            src = json.loads(r['data'] or '{}').get('src')
        except (TypeError, ValueError, AttributeError):
            src = None
        try:
            store.command(token, RID + short(r['id']), None, None, ACTION,
                          dict(id=r['id'], kind=r['kind'], amount=int(r['amount']), src=src if isinstance(src, str) else None), internal=True)
        except GameError:   # refused (a bad row): stays pending, the operator looks
            continue
        t = now()
        store.transaction(lambda db, eid=r['id'], t=t: db.execute(
            "UPDATE live_effects SET status='applied',applied_at=? WHERE id=? AND sid=? AND status='pending'", (t, eid, sid)))
        changed = True
    return changed


def forget(store, token: str) -> None:
    """Account deletion ("Xóa dữ liệu"): the rewards addressed to this save go with it."""
    sid = store.key(token)
    store.transaction(lambda db: db.execute('DELETE FROM live_effects WHERE sid=?', (sid,)))
