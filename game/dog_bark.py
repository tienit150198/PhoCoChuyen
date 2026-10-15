"""🐕 Kéo co chó sủa: removed (owner 15/10 "xóa trò 'kéo co chó sủa' đi cho nhẹ"). What is left is only what money and
saves already written by 2.4.15 and older need, so nothing a player owns is lost and a rollback keeps working:

* The command `jr_bark_join` refuses (code 'bark_off', nothing taken): no new stake ever goes into escrow.
* A `live_effects` row of kind 'bark' (a pot won, a draw's or a cancel's stake back) still pays once (apply_fx, called
  by game/live_effects.py) and its row flips pending → applied in the save's own transaction (fx_commit, called by
  game/storage.py for every live_fx), exactly as in 2.4.15.
* Housekeeping (server.py, every 30 s; one indexed query on the open-ticket partial index): a ticket still open after
  WAIT_MAX / STUCK_MAX (no live service plays it any more) is given back under the same guarded UPDATE, once, with its
  one 'bark' payout row: what 2.4.15 did with a stale ticket.
* forget: a player who erases their data loses their ticket rows (as before).

The table `bark_tickets` (game/pg_schema.py, SCHEMA_VERSION 34/35) and every row in it stay: never dropped. No save key
was ever written by the game (the stake left with a Sổ ví row). The weekly titles stay valid: game/dog_bark_board.py.
"""
from __future__ import annotations

import datetime
import json
import re
import time

COMMANDS = ('jr_bark_join',)
FX = 'bark'                        # live_effects kind
KIND = 'life'                      # wallet history kind (journey.HISTORY_KINDS): every build knows it
LABEL = '🐕 Kéo co chó sủa'
WAIT_MAX = 300.0                   # a waiting ticket older than this goes back (as 2.4.15)
STUCK_MAX = 600.0                  # a ticket in a match started longer ago than this goes back (as 2.4.15)
TICKET_RE = re.compile(r'k[0-9a-f]{20}')
VN = datetime.timezone(datetime.timedelta(hours=7))
OPEN = ('wait', 'play', 'dog')


def now() -> float:
    return time.time()


def fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _core():
    from . import engine
    return engine


def action(s: dict, name: str, p: dict) -> dict:
    """`jr_bark_*`: the game is gone; refuse cleanly before anything leaves the wallet."""
    _core().need(False, 'Kéo co chó sủa đã ngừng rồi nha.', 'bark_off')
    return {}


def apply_fx(s: dict, p: dict, amount: int) -> str:
    """A 'bark' live_effects row paid into the save (game/live_effects.py apply): a win, a draw's or a cancel's stake."""
    e = _core()
    data = p.get('data') if isinstance(p.get('data'), dict) else {}
    what, ticket = data.get('what'), data.get('ticket')
    e.need(what in ('win', 'draw', 'back') and isinstance(ticket, str) and TICKET_RE.fullmatch(ticket), 'Dữ liệu kéo co không hợp lệ.')
    from . import journey as jr
    j = s['journey']
    label = {'win': 'thắng kèo', 'draw': 'hòa, trả cược', 'back': 'trả lại cược'}[what]
    jr._wallet(j, amount, KIND, f'{LABEL} · {label}')
    if what == 'win':
        return f'🐕 Thắng kèo kéo co! +{fmt(amount)} xu vào ví.'
    return f'🐕 {fmt(amount)} xu cược đã về ví.'


def fx_commit(db, sid: str, result) -> None:
    """live_fx of a 'bark' or 'bark_weekly' row, in the save's transaction: the row flips pending → applied here, once
    (a GameError rolls the payment back)."""
    live = (result or {}).get('live') if isinstance(result, dict) else None
    if not isinstance(live, dict) or live.get('kind') not in (FX, 'bark_weekly') or live.get('already'):
        return
    _core().need(db.execute("UPDATE live_effects SET status='applied', applied_at=? WHERE id=? AND sid=? AND kind=? AND status='pending'",
                            (now(), live.get('id'), sid, live.get('kind'))).rowcount == 1, 'Khoản này đã xử lý rồi.', 'bark_sync')


def refund_rows(db, rows, t: float, why: str) -> int:
    """Give these tickets' stakes back ('back'), each once: the guarded UPDATE, then its one payout row."""
    n = 0
    for x in rows:
        if db.execute("UPDATE bark_tickets SET status='back', result='', ended=?, pay=stake WHERE id=? AND status=?",
                      (t, x['id'], x['status'])).rowcount != 1:
            continue
        db.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT DO NOTHING",
                   (f'bark:{x["id"]}', x['sid'], FX, int(x['stake']), json.dumps(dict(ticket=x['id'], what='back', why=why, src='bark')), t))
        n += 1
    return n


def housekeeping(store, t: float | None = None) -> int:
    """Refund tickets left waiting (WAIT_MAX) or stuck in a match (STUCK_MAX). Idempotent."""
    t = now() if t is None else t

    def run(db):
        rows = [dict(x) for x in db.execute(
            "SELECT id, sid, stake, status FROM bark_tickets WHERE (status='wait' AND created<?) OR (status IN ('play','dog') AND started<?) "
            'ORDER BY created LIMIT 200 FOR UPDATE SKIP LOCKED', (t - WAIT_MAX, t - STUCK_MAX)).fetchall()]
        return refund_rows(db, rows, t, 'stale')
    return store.transaction(run)


def run_housekeeping(store) -> None:
    """server.py maintenance (every 30 s). Never raises."""
    import sys
    try:
        n = housekeeping(store)
        if n:
            sys.stderr.write(f'[dog_bark] refunded {n} stale tickets\n')
    except Exception as e:  # noqa: BLE001 - housekeeping never takes the server down
        sys.stderr.write(f'[dog_bark] housekeeping: {type(e).__name__}\n')


def forget(db, sid: str) -> None:
    """A player erased their data: their tickets go (their escrow went with the save)."""
    db.execute('DELETE FROM bark_tickets WHERE sid=?', (sid,))
    from . import dog_bark_board
    dog_bark_board.forget(db, sid)
