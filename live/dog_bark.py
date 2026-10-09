"""🐕 Kéo co chó sủa (switch LIVE_DOG_BARK, welcome flag `bark`): the lobby, the matching and the tug-of-war itself.
The rules, the money and the pure physics are in game/dog_bark.py; this file runs them in real time.

* The page puts the stake in escrow with the game command `jr_bark_join` (a `bark_tickets` row, status 'wait'), then
  sends `bark_find {ticket}`: the ticket must be this player's and still waiting. It joins the queue of its stake.
* Matching (at once, then every second): a random waiting player of the same stake, never from the same IP (a salted
  hash of the request IP, in memory only: never in a save, a row or a log), never someone blocked either way, never
  the same two players more than PAIR_MAX matches in a row (PairBook, memory only). Both tickets flip 'wait' -> 'play'
  in one transaction (guarded: a ticket refunded meanwhile is dropped). After DOG_AFTER seconds without a human, the
  house dog (🐕 Chó nhà Mây · <name>) takes the match ('wait' -> 'dog') when today's dog caps allow the stake; else the
  page is told and keeps waiting for a human until WAIT_LIVE, then the stake goes back.
* The match: COUNTDOWN seconds, then the rope (game/dog_bark.py Rope) every TICK. `bark_v {m, v: [0..100, ...]}` brings
  the loudness numbers (never audio: the page measures its own microphone), at most BATCH_MAX a frame and RATE_MAX a
  second (game Voice clamps them). `bark_st {m, x, a, b, left, fx?}` goes to the players and the watchers every
  ST_EVERY ticks. A player with no socket for GONE_S, or who sends `bark_quit`, loses.
* Settlement, once per ticket: 'play'/'dog' -> 'done' under a guarded UPDATE and its one payout row live_effects
  'bark:<ticket>' (kind 'bark') in the same transaction; then `bark_end` (the page collects the payout: POST
  /api/live/effects). A database error is retried; if the service stops, the game server's housekeeping refunds.
* Watching: `bark_lobby` lists the stakes waiting and the matches on; `bark_watch {m}` follows one, `bark_cheer {m, e}`
  throws 👏 or 🔥 (counted, shown on the next `bark_st`).

Frames (client -> server; replies in brackets)
  bark_lobby {}                 [bark_lobby {wait: [[stake, n]], matches: [...], me}]
  bark_find {ticket}            [bark_wait {ticket, stake, dog_after}]   then bark_go | bark_info | bark_back
  bark_cancel {ticket}          [bark_back {ticket, why: 'cancel'}]
  bark_rejoin {}                [bark_go (the match going on) | bark_wait | bark_none]
  bark_v {m, v}   bark_quit {m}   bark_watch {m} [bark_room]   bark_unwatch {}   bark_cheer {m, e}
Server pushes: bark_go {m, side, me, opp, stake, pot, limit, at, cd}, bark_st, bark_end {m, result, why, pay, x},
bark_info {ticket, code, msg}, bark_back {ticket, why}.
An older live service answers 'unknown'; the page only shows the game while the welcome's flags have `bark`.
"""
from __future__ import annotations

import asyncio
import json
import random
import secrets
import time

from game import dog_bark as G

from .db import Error as DbError, log
from .limits import LRU
from .protocol import Feature, LiveError, on

COUNTDOWN = 3.0
ST_EVERY = 2                      # a bark_st every 2 ticks (5 a second)
WATCH_MAX = 200                   # watchers of one match
MATCHES_MAX = 2000
QUEUE_MAX = 5000
CHEERS = ('👏', '🔥')
SETTLE_TRIES = 4
MATCH_RE = __import__('re').compile(r'm[0-9a-f]{12}')


class _Abort(Exception):
    pass


class Wait:
    __slots__ = ('ticket', 'sid', 'pid', 'name', 'stake', 'iph', 'since', 'dog_said', 'gone', 'busy')

    def __init__(self, ticket, player, stake, iph, since):
        self.ticket, self.sid, self.pid, self.name = ticket, player.sid, player.pid, player.name or 'Người chơi'
        self.stake, self.iph, self.since = stake, iph, since
        self.dog_said, self.gone, self.busy = False, None, False


class Side:
    __slots__ = ('sid', 'pid', 'name', 'ticket', 'voice', 'gone', 'quit', 'level')

    def __init__(self, w: Wait):
        self.sid, self.pid, self.name, self.ticket = w.sid, w.pid, w.name, w.ticket
        self.voice = G.Voice()
        self.gone = None
        self.quit = False
        self.level = 0.0


class Match:
    def __init__(self, mid, stake, a: Side, b: Side | None, dog: G.HouseDog | None, room, t: float):
        self.id, self.stake, self.a, self.b, self.dog, self.room = mid, stake, a, b, dog, room
        self.rope = G.Rope()
        self.go_at = t + COUNTDOWN
        self.n = 0
        self.over = False
        self.fx = {}
        self.lb = 0.0
        self.watchers = 0

    def sides(self):
        return [x for x in (self.a, self.b) if x is not None]

    def opp_view(self, me: Side) -> dict:
        if self.dog is not None:
            return self.dog.view()
        o = self.b if me is self.a else self.a
        return dict(house=False, name=o.name, pid=o.pid)

    def card(self) -> dict:
        b = dict(house=True, name=f'{G.HOUSE} · {self.dog.name}', emoji=self.dog.breed[2]) if self.dog else dict(house=False, name=self.b.name)
        return dict(m=self.id, stake=self.stake, a=dict(name=self.a.name), b=b, x=round(self.rope.x), left=round(max(0.0, self.rope.limit - self.rope.t)))


class DogBarkFeature(Feature):
    name, flag = 'bark', 'bark'

    def __init__(self, app):
        super().__init__(app)
        self.salt = secrets.token_bytes(16)         # the IP hashes are worthless outside this process
        self.queue: dict = {}                       # ticket -> Wait
        self.matches: dict = {}                     # match id -> Match
        self.in_match: dict = {}                    # sid -> match id
        self.pairs = G.PairBook()
        self.last_dog = LRU(20000)                  # sid -> the house dog's last name (a new one each match)
        self.rng = random.Random(secrets.randbits(64))
        self.loop = None

    # ---- helpers ----------------------------------------------------------------------------------------
    def _iph(self, conn) -> str:
        return G.ip_hash(self.salt, conn.ip)

    def _online(self, pid) -> bool:
        return bool(self.hub.conns_of(pid))

    def _to(self, pid, frame) -> None:
        self.hub.to_pids([pid], frame)

    @staticmethod
    def _ticket(v) -> str:
        if not (isinstance(v, str) and G.TICKET_RE.fullmatch(v)):
            raise LiveError('bad', 'Không có kèo này.')
        return v

    def _match_of(self, f, conn) -> Match:
        mid = f.get('m')
        m = self.matches.get(mid) if isinstance(mid, str) else None
        if m is None:
            raise LiveError('gone', 'Trận này đã xong.')
        return m

    # ---- lobby --------------------------------------------------------------------------------------------
    @on('bark_lobby', rate=(20, 10))
    async def lobby(self, conn, f):
        sid = conn.player.sid
        stakes: dict = {}
        for w in self.queue.values():
            if w.sid != sid:
                stakes[w.stake] = stakes.get(w.stake, 0) + 1
        ms = sorted(self.matches.values(), key=lambda m: -m.stake)[:20]
        mine = self.in_match.get(sid)
        waiting = next((w for w in self.queue.values() if w.sid == sid), None)
        return dict(t='bark_lobby', wait=sorted([[k, n] for k, n in stakes.items()], key=lambda x: -x[1])[:12],
                    matches=[m.card() for m in ms if not m.over], me=dict(m=mine, ticket=waiting.ticket if waiting else None))

    # ---- the queue ----------------------------------------------------------------------------------------
    @on('bark_find', rate=(10, 10))
    async def find(self, conn, f):
        p = conn.player
        ticket = self._ticket(f.get('ticket'))
        if p.sid in self.in_match:
            raise LiveError('busy', 'Bạn đang kéo co một trận rồi.')
        w = self.queue.get(ticket)
        if w is None:
            if len(self.queue) >= QUEUE_MAX:
                raise LiveError('full', 'Đông quá, thử lại sau chút nha.')
            row = await self.db.fetchrow('SELECT sid, stake, status FROM bark_tickets WHERE id=?', (ticket,))
            if not row or row['sid'] != p.sid:
                raise LiveError('bad', 'Không có kèo này.')
            if row['status'] != 'wait':
                raise LiveError('gone', 'Kèo này đã xong rồi.')
            w = self.queue[ticket] = Wait(ticket, p, int(row['stake']), self._iph(conn), time.monotonic())
        w.gone = None
        self.hub.send(conn, dict(t='bark_wait', ticket=ticket, stake=w.stake, dog_after=G.DOG_AFTER,
                                 waited=round(time.monotonic() - w.since, 1)))
        await self._try(w)
        return None

    @on('bark_cancel', rate=(10, 10))
    async def cancel(self, conn, f):
        ticket = self._ticket(f.get('ticket'))
        w = self.queue.get(ticket)
        if w is not None and w.sid != conn.player.sid:
            raise LiveError('bad', 'Không có kèo này.')
        if w is not None and w.busy:
            raise LiveError('busy', 'Đang ghép trận, chờ xíu nha.')
        self.queue.pop(ticket, None)
        back = await self._refund(ticket, conn.player.sid, 'cancel')
        return dict(t='bark_back', ticket=ticket, why='cancel', ok=back)

    async def _refund(self, ticket: str, sid: str, why: str) -> bool:
        t = time.time()

        async def run(tx):
            row = await tx.fetchrow("SELECT id, sid, stake, status FROM bark_tickets WHERE id=? AND sid=? AND status='wait' FOR UPDATE", (ticket, sid))
            if not row:
                return False
            if await tx.execute("UPDATE bark_tickets SET status='back', ended=?, pay=stake WHERE id=? AND status='wait'", (t, ticket)) != 1:
                return False
            await tx.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) ON CONFLICT(id) DO NOTHING",
                             (f'bark:{ticket}', sid, G.FX, int(row['stake']), json.dumps(dict(ticket=ticket, what='back', why=why, src='bark')), t))
            return True
        return bool(await self.db.transaction(run))

    @on('bark_rejoin', rate=(10, 10))
    async def rejoin(self, conn, f):
        p = conn.player
        mid = self.in_match.get(p.sid)
        m = self.matches.get(mid) if mid else None
        if m is not None and not m.over:
            me = m.a if m.a.sid == p.sid else m.b
            m.room.add(conn)
            me.gone = None
            self.hub.send(conn, self._go(m, me))
            return None
        w = next((x for x in self.queue.values() if x.sid == p.sid), None)
        if w is not None:
            w.gone = None
            return dict(t='bark_wait', ticket=w.ticket, stake=w.stake, dog_after=G.DOG_AFTER, waited=round(time.monotonic() - w.since, 1))
        return dict(t='bark_none')

    def _pick(self, w: Wait, t: float):
        out = []
        for o in self.queue.values():
            if o is w or o.busy or o.stake != w.stake or o.sid == w.sid or o.iph == w.iph:
                continue
            if self.hub.blocked(o.pid, w.pid) or not self.pairs.ok(o.sid, w.sid, t):
                continue
            out.append(o)
        return self.rng.choice(out) if out else None

    async def _try(self, w: Wait) -> None:
        if w.busy or w.ticket not in self.queue:
            return
        o = self._pick(w, time.time())
        if o is not None:
            await self._start_pvp(w, o)

    async def _start_pvp(self, w: Wait, o: Wait) -> None:
        if len(self.matches) >= MATCHES_MAX:
            return
        w.busy = o.busy = True
        mid = 'm' + secrets.token_hex(6)
        t = time.time()

        async def run(tx):
            for x in (w, o):
                n = await tx.execute("UPDATE bark_tickets SET status='play', match=?, opp='pvp', started=? WHERE id=? AND status='wait'",
                                     (mid, t, x.ticket))
                if n != 1:
                    raise _Abort(x.ticket)
        try:
            await self.db.transaction(run)
        except _Abort as e:
            w.busy = o.busy = False
            self.queue.pop(e.args[0], None)   # refunded (or settled) meanwhile: no longer waiting
            return
        except DbError as e:
            log('bark start:', type(e).__name__)
            w.busy = o.busy = False
            return
        for x in (w, o):
            self.queue.pop(x.ticket, None)
        self.pairs.played(w.sid, o.sid, t)
        self._begin(mid, w.stake, Side(w), Side(o), None)

    async def _start_dog(self, w: Wait) -> None:
        t = time.time()
        today = await self.db.fetchrow(G.TODAY_SQL, (w.sid, G.vn_day_start(t)))
        room = G.dog_room(dict(today)) if today else 0
        if w.stake > room:
            if not w.dog_said:
                w.dog_said = True
                msg = (f'{G.HOUSE} chỉ nhận kèo tới {G.fmt(room)} xu hôm nay. Chờ người thật nha.' if room >= G.MIN_STAKE else
                       f'{G.HOUSE} nghỉ rồi, hôm nay chỉ chờ người thật thôi nha.')
                self._to(w.pid, dict(t='bark_info', ticket=w.ticket, code='dog_full', msg=msg, room=room))
            return
        avoid = (self.last_dog.get(w.sid),)
        dog = G.HouseDog(random.Random(secrets.randbits(64)), avoid=avoid)
        mid = 'm' + secrets.token_hex(6)
        w.busy = True
        try:
            n = await self.db.execute("UPDATE bark_tickets SET status='dog', match=?, opp='dog', dog=?, started=? WHERE id=? AND status='wait'",
                                      (mid, dog.name, t, w.ticket))
        except DbError as e:
            log('bark dog:', type(e).__name__)
            w.busy = False
            return
        self.queue.pop(w.ticket, None)
        if n != 1:
            return
        self.last_dog.put(w.sid, dog.name)
        self._begin(mid, w.stake, Side(w), None, dog)

    # ---- the match ----------------------------------------------------------------------------------------
    def _begin(self, mid, stake, a: Side, b: Side | None, dog) -> None:
        room = self.hub.room('bark:' + mid)
        m = Match(mid, stake, a, b, dog, room, time.monotonic())
        self.matches[mid] = m
        for s in m.sides():
            self.in_match[s.sid] = mid
            for c in self.hub.conns_of(s.pid):
                room.add(c)
            self._to(s.pid, self._go(m, s))
        if self.loop is None:
            self.loop = asyncio.ensure_future(self._run())

    def _go(self, m: Match, me: Side) -> dict:
        side = 'a' if me is m.a else 'b'
        pay = 2 * m.stake if m.dog else G.pot(m.stake)
        return dict(t='bark_go', m=m.id, side=side, me=dict(name=me.name), opp=m.opp_view(me), stake=m.stake, pot=pay,
                    limit=m.rope.limit, cd=round(max(0.0, m.go_at - time.monotonic()), 2), x=round(m.rope.x, 1),
                    left=round(max(0.0, m.rope.limit - m.rope.t), 1))

    @on('bark_v', rate=(12, 1.0))
    async def voice(self, conn, f):
        mid = self.in_match.get(conn.player.sid)
        m = self.matches.get(mid) if mid else None
        if m is None or m.over or f.get('m') != m.id:
            return None
        me = m.a if m.a.sid == conn.player.sid else m.b
        me.voice.add(f.get('v'), time.monotonic())
        return None

    @on('bark_quit', rate=(5, 10))
    async def quit(self, conn, f):
        mid = self.in_match.get(conn.player.sid)
        m = self.matches.get(mid) if mid else None
        if m is None or m.over:
            return dict(t='bark_none')
        (m.a if m.a.sid == conn.player.sid else m.b).quit = True
        return None

    async def _run(self) -> None:
        try:
            while self.matches:
                t0 = time.monotonic()
                for m in list(self.matches.values()):
                    try:
                        self._step(m, t0)
                    except Exception as e:  # noqa: BLE001 - one match never stops the others
                        log('bark step', type(e).__name__, str(e)[:120])
                await asyncio.sleep(max(0.01, G.TICK - (time.monotonic() - t0)))
        finally:
            self.loop = None

    def _side_gone(self, s: Side, t: float) -> bool:
        if s.quit:
            return True
        if self._online(s.pid):
            s.gone = None
            return False
        if s.gone is None:
            s.gone = t
        return t - s.gone > G.GONE_S

    def _step(self, m: Match, t: float) -> None:
        if m.over:
            return
        ga = self._side_gone(m.a, t)
        gb = self._side_gone(m.b, t) if m.b else False
        if ga or gb:
            if ga and gb:
                first = 'draw' if (m.a.gone or t) == (m.b.gone or t) else ('b' if (m.a.gone or t) < (m.b.gone or t) else 'a')
                return self._finish(m, first, 'gone')
            return self._finish(m, 'b' if ga else 'a', 'quit' if (m.a.quit if ga else m.b.quit) else 'gone')
        if t < m.go_at:
            if m.n % ST_EVERY == 0:
                self._st(m, 0.0, 0.0)
            m.n += 1
            return
        la = 0.0 if m.a.gone else m.a.voice.level(t)
        if m.dog is not None:
            lb = m.dog.pull(la, m.a.voice.mean())
        else:
            lb = 0.0 if m.b.gone else m.b.voice.level(t)
        m.a.level, m.lb = la, lb
        out = m.rope.step(la, lb)
        m.n += 1
        if m.n % ST_EVERY == 0 or out:
            self._st(m, la, lb)
        if out:
            self._finish(m, out, 'end' if abs(m.rope.x) >= G.END else 'time')

    def _st(self, m: Match, la: float, lb: float) -> None:
        frame = dict(t='bark_st', m=m.id, x=round(m.rope.x, 1), a=round(la), b=round(min(100.0, lb)),
                     left=round(max(0.0, m.rope.limit - m.rope.t), 1))
        if m.fx:
            frame['fx'] = m.fx
            m.fx = {}
        m.room.send(frame)

    def _finish(self, m: Match, winner: str, why: str) -> None:
        m.over = True
        asyncio.ensure_future(self._settle(m, winner, why))

    async def _settle(self, m: Match, winner: str, why: str) -> None:
        t = time.time()
        rows = []
        for s in m.sides():
            side = 'a' if s is m.a else 'b'
            res = 'draw' if winner == 'draw' else 'win' if winner == side else 'lose'
            pay = m.stake if res == 'draw' else (2 * m.stake if m.dog else G.pot(m.stake)) if res == 'win' else 0
            rows.append((s, res, pay))
        prev = 'dog' if m.dog else 'play'

        async def run(tx):
            done = []
            for s, res, pay in rows:
                n = await tx.execute("UPDATE bark_tickets SET status='done', result=?, pay=?, ended=? WHERE id=? AND status=?",
                                     (res, pay, t, s.ticket, prev))
                if n == 1 and pay > 0:
                    what = 'win' if res == 'win' else 'draw'
                    await tx.execute("INSERT INTO live_effects(id, sid, kind, amount, data, status, at) VALUES(?,?,?,?,?,'pending',?) "
                                     'ON CONFLICT(id) DO NOTHING',
                                     (f'bark:{s.ticket}', s.sid, G.FX, pay, json.dumps(dict(ticket=s.ticket, what=what, src='bark')), t))
                done.append(n == 1)
            return done
        done = None
        for i in range(SETTLE_TRIES):
            try:
                done = await self.db.transaction(run)
                break
            except DbError as e:
                log('bark settle:', type(e).__name__)
                await asyncio.sleep(0.5 * (i + 1))
        for (s, res, pay), ok in zip(rows, done or [False] * len(rows)):
            self.in_match.pop(s.sid, None)
            self._to(s.pid, dict(t='bark_end', m=m.id, result=res, why=why, pay=pay if ok else 0, x=round(m.rope.x, 1),
                                 saved=bool(ok)))
        m.room.send(dict(t='bark_over', m=m.id, winner=winner, x=round(m.rope.x, 1)))
        self.matches.pop(m.id, None)
        self.hub.drop_room('bark:' + m.id)

    # ---- watching -------------------------------------------------------------------------------------------
    @on('bark_watch', rate=(10, 10))
    async def watch(self, conn, f):
        m = self._match_of(f, conn)
        if len({c.player.pid for c in m.room.conns}) >= WATCH_MAX + 2:
            raise LiveError('full', 'Đông người xem quá, thử trận khác nha.')
        for r in [r for r in list(conn.rooms) if r.id.startswith('bark:') and r is not m.room]:
            if conn.player.sid not in self.in_match:
                r.remove(conn)
        m.room.add(conn)
        return dict(t='bark_room', **m.card(), go=round(max(0.0, m.go_at - time.monotonic()), 2))

    @on('bark_unwatch', rate=(10, 10))
    async def unwatch(self, conn, f):
        if conn.player.sid in self.in_match:
            return None
        for r in [r for r in list(conn.rooms) if r.id.startswith('bark:')]:
            r.remove(conn)
        return None

    @on('bark_cheer', rate=(4, 1.0))
    async def cheer(self, conn, f):
        m = self._match_of(f, conn)
        e = f.get('e')
        if e not in CHEERS or conn not in m.room.conns:
            return None
        m.fx[e] = min(99, m.fx.get(e, 0) + 1)
        return None

    # ---- every second -----------------------------------------------------------------------------------------
    async def tick(self, now: float):
        t = time.monotonic()
        for w in list(self.queue.values()):
            if w.busy or w.ticket not in self.queue:
                continue
            if not self._online(w.pid):
                w.gone = w.gone or t
                if t - w.gone > G.GONE_S:
                    self.queue.pop(w.ticket, None)
                    await self._refund(w.ticket, w.sid, 'gone')
                continue
            w.gone = None
            if t - w.since > G.WAIT_LIVE:
                self.queue.pop(w.ticket, None)
                if await self._refund(w.ticket, w.sid, 'wait'):
                    self._to(w.pid, dict(t='bark_back', ticket=w.ticket, why='wait'))
                continue
            await self._try(w)
            if w.ticket in self.queue and not w.busy and t - w.since >= G.DOG_AFTER:
                await self._start_dog(w)

    async def on_close(self, conn):
        for r in [r for r in list(conn.rooms) if r.id.startswith('bark:')]:
            r.remove(conn)

    def welcome(self, conn) -> dict:
        return {}
