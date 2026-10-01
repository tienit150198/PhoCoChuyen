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
  spirit: the life spirit (0-100), when the save has one; a spirit row may be negative (SPIRIT_DOWN..-1: a beer at a
  wedding party), every other kind only gives. title: a wedding title (game/wedding_live.py
  TITLE_NAMES) unlocked in the save. closeness: points between two players (`player_closeness`, beside the
  save, under the row's own pending -> applied guard). Kinds this build does not pay stay pending for a later
  build (never paid elsewhere). Story saves only, like system gifts.
* A coins row may carry `data.popup {title, text}`: once paid, the private card of game/system_gift.py shows it
  (a system_gifts row written as 'applied'): the couple's party total, an anniversary, the weekly race.
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
PAYS = ('coins', 'spirit', 'title')  # kinds this build applies to the save
BESIDE = ('closeness',)             # kinds this build applies beside the save (player_closeness, game/wedding_live.py)
LABELS = dict(envelope='🧧 Lì xì dạo phố', date='💕 Buổi hẹn trên phố', guest='💍 Đi ăn cưới', host='💍 Khách tới dự đám cưới',
              anniv='💞 Kỷ niệm ngày cưới', anniv_npc='🧧 Hàng xóm mừng kỷ niệm cưới', race='🥇 Khách mời của tuần', env='🧧 Phong bì mừng cưới',
              bouquet='💐 Bắt được hoa cưới')
LABEL = '🎁 Quà từ khu phố'         # any other source
AMOUNT_MAX = 2000                   # live/effects.py AMOUNT_MAX (the 1000-day anniversary is 1,500 xu)
SPIRIT_DOWN = -10                   # live/effects.py SPIRIT_DOWN: a 'spirit' row may take this much away at most
POPUP_TITLE, POPUP_TEXT = 80, 300   # the private card (game/system_gift.py) a row may carry: data.popup {title, text}
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
    amount = e.integer(p.get('amount'), SPIRIT_DOWN if kind == 'spirit' else 1, AMOUNT_MAX)
    e.need(amount != 0, 'Số lượng không hợp lệ.')
    h = short(eid)
    got = j.get('live_fx') if isinstance(j.get('live_fx'), list) else []
    if h in got:   # already paid (a receipt pruned meanwhile): nothing moves
        return s, dict(message='', live=dict(id=eid, kind=kind, amount=0, already=True))
    if kind == 'coins':
        jr._wallet(j, amount, KIND, LABELS.get(p.get('src'), LABEL))
        message = f'+{amount} xu vào ví.'
    elif kind == 'title':   # 💍 a wedding title (game/wedding_live.py TITLE_NAMES) or 🏆 a fair one (game/fair_board.py): unlocked once, kept like any title
        from .wedding_live import TITLE_NAMES
        from .fair import AWARD_NAMES
        names = {**TITLE_NAMES, **AWARD_NAMES}
        tid = p.get('title')
        e.need(tid in names and tid in jr.TITLE_INDEX, 'Danh hiệu không hợp lệ.')
        message = ''
        if tid not in j['titles']:
            j['titles'][tid] = j['life_day']
            jr._news(j, 'titles', 'titles', [tid])
            message = f'Danh hiệu mới: {names[tid]}.'
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
    kinds = PAYS + BESIDE
    marks = ','.join('?' * len(kinds))
    with store.connect() as db:
        rows = [dict(r) for r in db.execute(f"SELECT id,kind,amount,data FROM live_effects WHERE sid=? AND status='pending' "
                                            f'AND kind IN ({marks}) ORDER BY at,id LIMIT {BATCH}', (sid, *kinds))]
    if not rows or not ((state or {}).get('journey') or {}).get('story'):
        return False
    changed = False
    for r in rows:
        data = _data(r['data'])
        if r['kind'] in BESIDE:
            _beside(store, sid, r, data)
            continue
        src = data.get('src') if isinstance(data.get('src'), str) else None
        payload = dict(id=r['id'], kind=r['kind'], amount=int(r['amount']), src=src)
        if r['kind'] == 'title':
            payload['title'] = data.get('title')
        try:
            store.command(token, RID + short(r['id']), None, None, ACTION, payload, internal=True)
        except GameError:   # refused (a bad row): stays pending, the operator looks
            continue
        t = now()

        def done(db, r=r, t=t):
            if db.execute("UPDATE live_effects SET status='applied',applied_at=? WHERE id=? AND sid=? AND status='pending'", (t, r['id'], sid)).rowcount == 1:
                _popup(db, sid, r, data, t)
        store.transaction(done)
        changed = True
    return changed


def _data(raw) -> dict:
    try:
        d = json.loads(raw or '{}')
    except (TypeError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def _popup(db, sid: str, r: dict, data: dict, t: float) -> None:
    """A paid row that carries data.popup {title, text}: the private card of game/system_gift.py (already paid here,
    so the gift row is written as 'applied': the card shows once, its button marks it seen)."""
    pop = data.get('popup')
    if r['kind'] != 'coins' or not isinstance(pop, dict) or not isinstance(pop.get('title'), str) or not isinstance(pop.get('text'), str):
        return
    db.execute("INSERT INTO system_gifts(id,sid,coins,title,text,status,created,applied_at) VALUES(?,?,?,?,?,'applied',?,?) ON CONFLICT(id) DO NOTHING",
               ('fx-' + short(r['id']), sid, int(r['amount']), pop['title'][:POPUP_TITLE], pop['text'][:POPUP_TEXT], t, t))


def _beside(store, sid: str, r: dict, data: dict) -> None:
    """closeness: points between two players (player_closeness), applied with the row's own pending -> applied guard."""
    other = data.get('with')
    if not isinstance(other, str) or not 0 < len(other) <= 128 or other == sid:
        return
    t = now()

    def run(db):
        if db.execute("UPDATE live_effects SET status='applied',applied_at=? WHERE id=? AND sid=? AND status='pending'", (t, r['id'], sid)).rowcount != 1:
            return
        db.execute('INSERT INTO player_closeness(sid, other, points, updated) VALUES(?, ?, ?, ?) '
                   'ON CONFLICT(sid, other) DO UPDATE SET points=player_closeness.points+excluded.points, updated=excluded.updated',
                   (sid, other, int(r['amount']), t))
    store.transaction(run)


def forget(store, token: str) -> None:
    """Account deletion ("Xóa dữ liệu"): the rewards addressed to this save go with it."""
    sid = store.key(token)
    store.transaction(lambda db: db.execute('DELETE FROM live_effects WHERE sid=?', (sid,)))
