"""🎈 Rewards from the live service (live/, `python3 -m live`): the game server's side.

The live service never writes a save. When it rewards a player (phase 3: +tinh thần after a date where both tapped
❤️; phase 2: a few xu from a lucky red envelope) it inserts a row in `live_effects` (live/effects.py grant():
idempotent by id, capped per kind per Vietnam day). This module pays those rows into the save, the
game/system_gift.py pattern:

* on_load(store, token, state), called by /api/bootstrap beside system_gift.on_load: each pending row of this save
  goes through Store.command, the engine's normal command path, as the internal action `sys_live` with the fixed
  request id ``live-<id>``; then the row flips pending → applied.
* Paid once, whatever the retries, tabs or processes: the request id (a second tab or a retry replays the stored
  receipt), the ids kept in the save (``journey['live_fx']``, the last KEPT: a row not marked applied after a crash
  is a no-op once its receipt is pruned), and the pending → applied guard on the row.
* Kinds paid: `coins` (the journey wallet, history kind 'life', the row's label or LABEL) and `spirit` (tinh thần,
  journey.life, clamped 0–100 like every other change). Any other kind stays pending, never paid elsewhere.
* Story saves only (production runs the story for every save); a non-story save keeps its rows pending.
* Loading the game never fails because of an effect: the server logs the error and loads the save.
"""
from __future__ import annotations

import hashlib
import json
import re
import time

ACTION = 'sys_live'                 # internal command (game/engine.py), never accepted from a client
RID = 'live-'                       # request id prefix: live-<id>
KIND = 'life'                       # journey wallet history kind (journey.HISTORY_KINDS)
LABEL = '🎈 Quà từ phố'
KINDS = ('coins', 'spirit')
AMOUNT_MAX = 1000                   # live/effects.py AMOUNT_MAX
KEPT = 60                           # ids of paid effects kept in the save
PER_LOAD = 20
ID_RX = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:@-]{2,119}')
_LABEL_BAD = re.compile(r'[\x00-\x1f\x7f<>]')


def now() -> float:
    return time.time()


def valid_id(eid) -> bool:
    return isinstance(eid, str) and bool(ID_RX.fullmatch(eid))


def request_id(eid: str) -> str:
    rid = RID + eid
    return rid if len(rid) <= 100 else RID + hashlib.sha256(eid.encode()).hexdigest()[:40]


def label_of(data) -> str:
    try:
        text = (json.loads(data or '{}') or {}).get('label')
    except (TypeError, ValueError, AttributeError):
        text = None
    text = _LABEL_BAD.sub('', text).strip()[:60] if isinstance(text, str) else ''
    return text or LABEL


# ---------------------------------------------------------------- the save (reducer, validation)
def apply(s: dict, p: dict) -> tuple[dict, dict]:
    """`sys_live` {id, kind, amount, label?}: one live reward into the save, once per effect id."""
    from . import engine as e
    from . import journey as jr
    from . import life
    j = s['journey']
    e.need(j.get('story'), 'Quà từ phố chỉ có trong hành trình.', 'not_story')
    eid, kind = p.get('id'), p.get('kind')
    e.need(valid_id(eid), 'Mã quà không hợp lệ.')
    e.need(kind in KINDS, 'Loại quà không hợp lệ.')
    amount = e.integer(p.get('amount'), 1, AMOUNT_MAX)
    got = j.get('live_fx') if isinstance(j.get('live_fx'), list) else []
    if eid in got:   # already paid (a receipt pruned meanwhile): nothing moves
        return s, dict(message='', live=dict(id=eid, kind=kind, amount=0, already=True))
    if kind == 'coins':
        label = p.get('label') if isinstance(p.get('label'), str) and p.get('label') else LABEL
        jr._wallet(j, amount, KIND, label[:60])
        moved = amount
        message = f'+{amount} xu vào ví.'
    else:
        moved = life._spirit(life._state(s), amount)
        message = f'+{moved} tinh thần.' if moved else ''
    j['live_fx'] = (got + [eid])[-KEPT:]
    e.validate_state(s)
    return s, dict(message=message, live=dict(id=eid, kind=kind, amount=moved))


def validate(j: dict) -> None:
    """journey['live_fx'] (optional): ids of the live rewards paid into this save."""
    if 'live_fx' not in j:
        return
    from .engine import need
    g = j['live_fx']
    need(isinstance(g, list) and len(g) <= KEPT and all(valid_id(x) for x in g) and len(set(g)) == len(g),
         'Danh sách quà từ phố trong bản lưu không hợp lệ.', 'invalid_save')


# ---------------------------------------------------------------- loading a save
def on_load(store, token: str, state: dict | None) -> bool:
    """Bootstrap: pay this save's pending live rewards. True when the save changed. One indexed query when
    there is none (live_effects_sid)."""
    from .engine import GameError
    sid = store.key(token)
    with store.connect() as db:
        rows = [dict(r) for r in db.execute("SELECT id,kind,amount,data FROM live_effects WHERE sid=? AND status='pending' "
                                            'ORDER BY at,id LIMIT ?', (sid, PER_LOAD))]
    if not rows or not ((state or {}).get('journey') or {}).get('story'):
        return False
    changed = False
    for r in rows:
        if r['kind'] not in KINDS or not valid_id(r['id']):
            continue
        payload = dict(id=r['id'], kind=r['kind'], amount=int(r['amount']))
        if r['kind'] == 'coins':
            payload['label'] = label_of(r['data'])
        try:
            store.command(token, request_id(r['id']), None, None, ACTION, payload, internal=True)
        except GameError:   # refused (e.g. an amount out of range): stays pending, the operator looks
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
