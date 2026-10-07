"""🏅 Danh hiệu bên tên (owner 07/10: "mấy người chat hỏi đáp thì hiển thị ra danh hiệu người ta đang có luôn nhé …
bảng xếp hạng, hội chợ event mà có là hiển thị ra hết"): every honour title a player holds now, as `tt`, a list of
ids, best first, beside the name on chat messages (Cả phố, DMs, groups, the quoted message of a reply), on walkers
and on a player's card. Never sent by a client; resolved here from the game's own records:

* 🏅 Danh hiệu tuần of the leaderboard (game/lb_titles.py, table `lb_weekly`, final=0 rows = this week's holders):
  `lb_<board>_<rank>` ("lb_wealth_3", "lb_milk_tea_1"). The game recomputes them once a day and freezes the week on
  Monday; when it does, it announces NOTIFY {op: 'honours_lb'} and the copy here is read again (else every LB_TTL).
  A week that ended is gone from the table, so it is gone from `tt`.
* 🏮 Hội chợ dân gian (game/fair.py TITLE_ROWS, kept in the save's journey.titles like any title, forever: the
  fair's own rule): `f_bao`, `f_dart`, …, and `f_king` / `f_master` given after the fair by game/fair_board.py.
  Read from the save (`sessions.state`, journey.titles only) per player, cached; the game announces
  NOTIFY {op: 'honours', pid} when one is granted (a fair round, a live reward).
* 💍 Khách mời của tuần (live/wedding.py): `w_vip` / `w_pro`, worn the week after the race, like the street's tag.

Bought titles of the week stay in `st` (live/styles.py); `ti` (the street's text) is unchanged, so an older client
shows what it showed before and ignores `tt`. An older service sends no `tt`.

Memory: an LRU of CACHE players (pid -> sid, fair ids), each refreshed after TTL seconds; the leaderboard holders are
one small table (≤ 40 + one per workplace) read at most every LB_TTL. No query per message: a chat frame only reads
the caches; a miss costs one batched primary-key query.
"""
from __future__ import annotations

import json
import time

from game.fair import AWARDS as FAIR_AWARDS, TITLE_ROWS as FAIR_ROWS
from game.lb_titles import honour, tier_of

from .auth import pid_of
from .db import Error as DbError, log
from .limits import LRU

CACHE = 20000
TTL = 900.0           # a player's fair titles (a NOTIFY drops the entry at once)
LB_TTL = 300.0        # the weekly leaderboard holders (a NOTIFY reads them again at once)
RETRY = 120.0         # a failed read is not tried again before this
MAX = 12              # ids sent at most
BATCH = 200
# The order of honour after the leaderboard: the fair's awards, the wedding race, then the fair's rounds.
FAIR = tuple(FAIR_AWARDS) + tuple(t for t, *_ in FAIR_ROWS if t not in FAIR_AWARDS)
FAIR_SET = frozenset(FAIR)
RACE = ('w_vip', 'w_pro')


def lb_id(board: str, rank: int) -> str:
    return f'lb_{board}_{rank}'


def fair_ids(titles) -> tuple:
    """The fair titles among a save's journey.titles (a dict id -> day), in the order of honour."""
    if not isinstance(titles, dict):
        return ()
    return tuple(t for t in FAIR if t in titles)


class Honours:
    def __init__(self, app):
        self.app = app
        self.rows = LRU(CACHE)          # pid -> (fetched monotonic, sid | None, fair ids)
        self.lb: dict = {}              # sid -> [lb ids, best first]
        self.lb_at = -1e18              # monotonic of the last read
        self.off_until = 0.0

    # ---- invalidation (NOTIFY) -------------------------------------------------------------------------------
    def forget(self, pid: str) -> None:
        self.rows.pop(pid, None)

    def stale_lb(self) -> None:
        self.lb_at = -1e18

    def clear(self) -> None:
        self.rows.clear()
        self.stale_lb()

    # ---- the sources -----------------------------------------------------------------------------------------
    async def _lb_fresh(self, mono: float) -> None:
        if mono - self.lb_at < LB_TTL:
            return
        self.lb_at = mono
        try:
            rows = await self.app.db.fetch('SELECT sid, board, rank FROM lb_weekly WHERE final=0')
        except DbError as e:   # a database from before the table: no weekly titles
            log('honours lb:', type(e).__name__)
            self.lb_at = mono - LB_TTL + RETRY
            return
        held: dict = {}
        for r in rows:
            board, rank = r['board'], int(r['rank'])
            if isinstance(board, str) and tier_of(board, rank) is not None:
                held.setdefault(r['sid'], []).append((honour(board, rank), lb_id(board, rank)))
        self.lb = {sid: [x for _, x in sorted(v)] for sid, v in held.items()}

    def _race(self) -> dict:
        wed = self.app.by_name.get('wedding') if hasattr(self.app, 'by_name') else None
        if wed is None or not wed.enabled():
            return {}
        return getattr(wed, 'race_ids', None) or {}

    async def _fetch(self, miss: list, mono: float) -> None:
        """Read the fair titles of these players from their saves (journey.titles only), by sid when they are online,
        else through their public profile."""
        hub = getattr(self.app, 'hub', None)
        online = {}
        for pid in miss:
            p = hub.players.get(pid) if hub is not None else None
            if p is not None and getattr(p, 'sid', None):
                online[pid] = p.sid
        got: dict = {}   # pid -> (sid, ids)
        pick = "CASE WHEN left(s.state, 1) = '{' THEN s.state::json #>> '{journey,titles}' END AS ti"
        sids = list(online.values())
        for i in range(0, len(sids), BATCH):
            part = sids[i:i + BATCH]
            for r in await self.app.db.fetch(f"SELECT s.sid, {pick} FROM sessions s WHERE s.sid IN ({','.join('?' * len(part))})", part):
                got[pid_of(r['sid'])] = (r['sid'], _ids(r['ti']))
        rest = [pid for pid in miss if pid not in online]
        for i in range(0, len(rest), BATCH):
            part = rest[i:i + BATCH]
            for r in await self.app.db.fetch(f"SELECT p.pid, p.sid, {pick} FROM profiles p LEFT JOIN sessions s ON s.sid = p.sid "
                                             f"WHERE p.pid IN ({','.join('?' * len(part))})", part):
                got[r['pid']] = (r['sid'], _ids(r['ti']))
        for pid in miss:
            sid, ids = got.get(pid) or (online.get(pid), ())
            self.rows.put(pid, (mono, sid, ids))

    # ---- reading ---------------------------------------------------------------------------------------------
    async def of(self, pids) -> dict:
        """{pid: [ids]} for these players ([] for nobody honoured)."""
        mono = time.monotonic()
        ids = [p for p in dict.fromkeys(pids) if isinstance(p, str) and p and p != 'admin']
        if not ids:
            return {}
        await self._lb_fresh(mono)
        miss = []
        for pid in ids:
            hit = self.rows.get(pid)
            if hit is None or mono - hit[0] >= TTL:
                miss.append(pid)
        if miss and mono >= self.off_until:
            try:
                await self._fetch(miss, mono)
            except DbError as e:   # never a failed message because of a title
                log('honours:', type(e).__name__)
                self.off_until = mono + RETRY
        race = self._race()
        out = {}
        for pid in ids:
            hit = self.rows.get(pid)
            sid, fair = (hit[1], hit[2]) if hit else (None, ())
            got = list(self.lb.get(sid, ())) if sid else []
            r = race.get(pid)
            awards = [x for x in fair if x in FAIR_AWARDS]
            got += awards + ([r] if r in RACE else []) + [x for x in fair if x not in FAIR_AWARDS]
            out[pid] = got[:MAX]
        return out

    async def one(self, pid: str) -> list:
        return (await self.of([pid])).get(pid) or []


def _ids(raw) -> tuple:
    if not raw:
        return ()
    try:
        return fair_ids(json.loads(raw))
    except ValueError:
        return ()


def of_app(app) -> Honours:
    """The service's one Honours (made on first use)."""
    h = getattr(app, '_honours', None)
    if h is None:
        h = app._honours = Honours(app)
    return h


def on_notify(app, e: dict) -> None:
    """NOTIFY {op: 'honours', pid}: a title was granted; {op: 'honours_lb'}: the weekly holders moved; {op: 'face'}:
    a player deleted their data."""
    op = e.get('op')
    if op in ('honours', 'face') and isinstance(e.get('pid'), str):
        of_app(app).forget(e['pid'])
    elif op == 'honours_lb':
        of_app(app).stale_lb()


def put(frame: dict, tt) -> dict:
    """The frame with `tt` set (a copy when it changes; buffered frames are never mutated)."""
    tt = list(tt) if tt else None
    if frame.get('tt') == tt:
        return frame
    frame = dict(frame)
    if tt:
        frame['tt'] = tt
    else:
        frame.pop('tt', None)
    return frame


async def with_honours(app, frames: list, key: str = 'pid') -> list:
    """The frames with their authors' `tt` now."""
    if not frames:
        return frames
    hx = await of_app(app).of(f.get(key) for f in frames)
    return [put(f, hx.get(f.get(key))) for f in frames]
