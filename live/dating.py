"""💕 "Bạn muốn hẹn hò?" (switch LIVE_DATING): the dating bench, the matcher and the 5-minute café date.
An in-game date, open to everyone (owner, 01/10: "hẹn hò trong game chứ không phải thật nên cứ thoải mái").

The bench ("Góc hẹn hò")
* Only accounts sit down (owner, 01/10: "người lạ không chat được", as for chat): a guest may look at the bench
  (`peek`), `sit` answers error 'account'.
* `queue {op:'sit', pref, g}` sits the player down: pref = who they would like to meet ('any', 'm', 'f'), g = their
  own character's Nam/Nữ ('m', 'f' or null), which the client reads from its save (the character's gender is the
  player's own pick in the game; the live service never reads a save). `queue {op:'stand'}` gets up, `queue
  {op:'peek'}` only asks. A named character is needed (the date shows names).
* The matcher (at once when someone sits, then every few seconds): the two longest-waiting compatible players.
  Compatible: each one's preference fits the other's character, both online, neither blocked the other (`blocks`
  or `marriage_blocks`, checked again in the database before the date starts), no date together in the last 24 h.
  Greedy from the oldest: the oldest waiting player gets the oldest partner that fits (`match()`, pure).

The date (room `date:<id>`, cap 2: every tab of both players), five minutes at most
  hello 4 s → card 1..3 (40 s each; both picked → revealed together for 4 s) → menu "Chọn món cho nhau" (60 s;
  each picks what they crave and orders for the other; both done → revealed for 6 s) → chat (60 s, or both tap
  "xong") → vote ❤️/👋 (30 s; no tap = 👋) → end.
* A player only ever gets their own view (`date` frames are per player): their own picks; the other's picks only
  once that card or the menu is revealed. Votes are never shown; the end is `match` (both ❤️) or `nope` (anything
  else), the same frame for both, so nobody learns who declined.
* Leaving (`date_leave`), blocking (`date_block`) or having no socket for 15 s ends the date for both: `left`
  for the one who went, `gone` (a gentle line) for the other.
* Both ❤️: friends both ways when both have an account (the `friends` rows, like accepting a request), the bond
  "Đang tìm hiểu 💕" (`date_bonds`, shown on each other's cards), and +5 tinh thần each through live/effects.py
  (`live_effects`, at most 15 a day; the game pays it on the next load, game/live_effects.py).
* Chat (the chat step): `date_say` goes through chat.store_message (filters, mutes, duplicates), channel
  `date:<id>`; chat.route('date:') makes deletes, reports (also `date_report`) and the admin Chat tab work on it.

Frames (client → server; replies in brackets)
  queue {op:'sit'|'stand'|'peek', pref, g, spot?}     [bench {state:'idle'|'wait', n, waited, pref}]
  answer {date, step:'card', i, pick} | {date, step:'menu', want, give} | {date, step:'chat'}   [date]
  heart {date, v:'heart'|'wave'}                      [date (mine only)]
  date_say {date, text, cid}                          [msg to both]
  date_leave {date}   date_block {date}   date_report {date, reason}
Server pushes: bench, date, bond {pid}; the welcome carries `bonds` (pids "đang tìm hiểu"), `bench` and `date`
(a reconnect lands back in the date it left).

Shorter waits (feedback #64, "ngồi ghế đợi lâu quá")
* The `bench` frame says how many wait now (`n`), how many sat down in the last RECENT_S (`recent`, me included) and
  the busiest two hours (`hot` [from, to] in Vietnam time, from the dates of the last 7 days and since; None until
  HOT_MIN dates). Players on the bench get a fresh `bench` when the count changes (at most every MATCH_EVERY).
* `date_call {}` ("📣 Rủ mọi người"): someone on the bench invites Cả phố. Everyone on Cả phố now (blocks respected)
  gets `call {ch:'town', id, kind:'date', pid, name, av, at}`, a line with a button to the dating corner; nothing is
  stored. Once per CALL_EVERY per player, CALL_MAX_HOUR an hour for the whole street; not when chat is muted, not when
  Cả phố is empty (then nothing is used up). [called {n, wait}]; the bench frame's `call` = seconds until the next one.
* After NPC_AFTER alone on the bench, the bench frame carries `npc` (which neighbour, 0..NPCS-1): the client seats a
  neighbour (clearly an NPC) with a few lines and a quick quiz; no rewards. A match (a real player) ends it.

Phase 2 (a bench spot in the street scene) sits players through the same `queue` frame with `spot:'street:<place>'`.
Everything here is bounded: the queue (3,000 seats), the 24 h memory of pairs (LRU), date ids kept for reports.
"""
from __future__ import annotations

import os
import re
import secrets
import time
from collections import deque

from .auth import pid_of
from .dating_content import CARDS, MENU, MENU_INDEX, QUICK
from .db import Error as DbError, log, wait_for_tables
from .effects import grant
from .limits import LRU
from .protocol import Feature, LiveError, on

PREFS = ('any', 'm', 'f')
GENDERS = ('m', 'f')
HELLO_S, CARD_S, REVEAL_S, MENU_S, MENU_REVEAL_S, CHAT_S, VOTE_S = 4.0, 40.0, 4.0, 60.0, 6.0, 60.0, 30.0
GONE_S = 15.0             # no socket for this long ends the date
N_CARDS, N_MENU = 3, 6
QUEUE_MAX = 3000
SCAN = 100                # partners looked at per bucket for one waiting player (blocked / dated pairs skipped)
AGAIN_S = 86400           # no second date with the same person within 24 h
MATCH_EVERY = 3.0         # the matcher also runs this often (a partner came back online, a 24 h window ended)
SPIRIT, SPIRIT_CAP = 5, 15
SAY_LEN = 200
FRIENDS_MAX = 200         # game/friends.py FRIENDS_MAX
REASONS = ('spam', 'rude', 'private', 'scam', 'other')
REPORT_MSGS = 20
SPOT = re.compile(r'[a-z0-9:_-]{1,40}')
DATE_ID = re.compile(r'[0-9a-f]{12}')
RECENT_S = 1800           # "đã ghé trong 30 phút qua"
HOT_DAYS, HOT_MIN = 7, 5  # the busiest hours: dates of the last 7 days (and since), shown from 5 dates on
TZ = 7 * 3600             # the hours are shown in Vietnam time
CALL_EVERY = 600          # 📣 one invitation per player per 10 minutes
CALL_MAX_HOUR = 6         # and at most this many an hour on the whole street
NPC_AFTER = 120.0         # seconds alone on the bench before a neighbour sits down
NPCS = 3                  # neighbours the client knows (public/js/v4/dating.js NPCS)


class Seat:
    """One player waiting on the bench."""
    __slots__ = ('pid', 'pref', 'g', 'since', 'spot', 'npc')

    def __init__(self, pid: str, pref: str = 'any', g: str | None = None, since: float = 0.0, spot: str = ''):
        self.pid, self.pref, self.g, self.since, self.spot = pid, pref, g, since, spot
        self.npc = False   # the bench frame with the neighbour went out

    def __repr__(self):
        return f'Seat({self.pid}, {self.pref}, {self.g}, {self.since})'


def fits(a: Seat, b: Seat) -> bool:
    """Each one's preference fits the other's character (an unknown character fits only 'any')."""
    return (a.pref == 'any' or a.pref == b.g) and (b.pref == 'any' or b.pref == a.g)


def _partner_keys(a: Seat) -> list:
    gs = (a.pref,) if a.pref in GENDERS else ('m', 'f', None)
    prefs = ('any',) + ((a.g,) if a.g in GENDERS else ())
    return [(g, p) for g in gs for p in prefs]


def match(seats, ok=lambda a, b: True, scan: int = SCAN) -> list:
    """Pairs to seat at a café table. `seats` in any order; the oldest waiting seat gets the oldest partner that
    fits and that ok(a, b) accepts (online, not blocked, not dated in the last 24 h), and so on down the bench.
    Buckets by (character, preference), so one pass costs about len(seats) × 6 looks."""
    seats = sorted(seats, key=lambda s: (s.since, s.pid))
    buckets: dict = {}
    for s in seats:
        buckets.setdefault((s.g, s.pref), []).append(s)
    used: set = set()
    out = []
    for a in seats:
        if a.pid in used:
            continue
        best = None
        for key in _partner_keys(a):
            n = 0
            for b in buckets.get(key, ()):
                if best is not None and (b.since, b.pid) >= (best.since, best.pid):
                    break                  # this bucket has nobody older than the partner already found
                if b is a or b.pid in used:
                    continue
                n += 1
                if n > scan:
                    break
                if ok(a, b):
                    best = b
                    break
        if best is not None:
            used.add(a.pid)
            used.add(best.pid)
            out.append((a, best))
    return out


class Recent:
    """Distinct players seen in the last `window` seconds (at most `cap` kept: the count saturates there)."""

    def __init__(self, window: float = RECENT_S, cap: int = 20000):
        self.window, self.cap = window, cap
        self.last: dict = {}
        self.log: deque = deque()

    def put(self, pid: str, t: float) -> None:
        if pid not in self.last and len(self.last) >= self.cap:
            return
        self.last[pid] = t
        self.log.append((t, pid))

    def count(self, now: float) -> int:
        while self.log and self.log[0][0] < now - self.window:
            t, pid = self.log.popleft()
            if self.last.get(pid) == t:
                del self.last[pid]
        return len(self.last)


def hour_of(t: float) -> int:
    return int((t + TZ) // 3600) % 24


def hot_hours(hours: list, least: int = HOT_MIN) -> list | None:
    """[from, to] (Vietnam time) of the busiest two hours in a row, or None with fewer than `least` dates."""
    if sum(hours) < least:
        return None
    best = max(range(24), key=lambda h: (hours[h] + hours[(h + 1) % 24], hours[h], -h))   # a tie: from the busier hour
    return [best, (best + 2) % 24]


def pair_key(a: str, b: str) -> tuple:
    return (a, b) if a < b else (b, a)


class Date:
    """A café date between two players: the steps, the private picks and the clock."""

    def __init__(self, did: str, a: dict, b: dict, now: float, speed: float = 1.0, rng=None):
        rng = rng or secrets.SystemRandom()
        self.id, self.ch = did, 'date:' + did
        self.pids = (a['pid'], b['pid'])
        self.info = {a['pid']: a, b['pid']: b}      # pid -> {pid, sid, name, av, account}
        self.cards = rng.sample(range(len(CARDS)), N_CARDS)
        self.menu = [m[0] for m in rng.sample(MENU, N_MENU)]
        self.picks = {p: [None] * N_CARDS for p in self.pids}
        self.want = dict.fromkeys(self.pids)
        self.give = dict.fromkeys(self.pids)
        self.votes = dict.fromkeys(self.pids)
        self.chat_done: set = set()
        self.speed = speed if speed > 0 else 1.0
        self.step, self.i, self.shown, self.ordered = 'hello', 0, False, False
        self.start = now
        self.until = now + self.secs(HELLO_S)
        self.away: dict = {}                         # pid -> when their last socket closed
        self.ending = False

    def secs(self, s: float) -> float:
        return s / self.speed

    def other(self, pid: str) -> str:
        return self.pids[1] if pid == self.pids[0] else self.pids[0]

    def revealed(self) -> int:
        """Cards whose picks both players may see."""
        if self.step in ('hello',):
            return 0
        if self.step == 'card':
            return self.i + (1 if self.shown else 0)
        return N_CARDS

    def same(self) -> int:
        a, b = self.pids
        return sum(1 for k in range(self.revealed()) if self.picks[a][k] is not None and self.picks[a][k] == self.picks[b][k])

    def hits(self) -> int:
        """Orders that were right (0–2), once the menu is revealed."""
        if not self.ordered:
            return 0
        a, b = self.pids
        return int(self.give[a] is not None and self.give[a] == self.want[b]) + int(self.give[b] is not None and self.give[b] == self.want[a])

    # ---- the clock ------------------------------------------------------------------------------------------
    def advance(self, now: float) -> bool:
        """Move on when a step is over (time is up, or both have answered). True when the vote is over."""
        a, b = self.pids
        for _ in range(8):   # a few steps at most per call (a late tick)
            if self.step == 'hello':
                if now < self.until:
                    return False
                self.step, self.i, self.shown, self.until = 'card', 0, False, now + self.secs(CARD_S)
            elif self.step == 'card':
                both = self.picks[a][self.i] is not None and self.picks[b][self.i] is not None
                if not self.shown:
                    if not both and now < self.until:
                        return False
                    self.shown, self.until = True, now + self.secs(REVEAL_S)
                    return False
                if now < self.until:
                    return False
                if self.i + 1 < N_CARDS:
                    self.i, self.shown, self.until = self.i + 1, False, now + self.secs(CARD_S)
                else:
                    self.step, self.shown, self.until = 'menu', False, now + self.secs(MENU_S)
            elif self.step == 'menu':
                both = all(self.want[p] is not None and self.give[p] is not None for p in self.pids)
                if not self.shown:
                    if not both and now < self.until:
                        return False
                    self.shown = self.ordered = True
                    self.until = now + self.secs(MENU_REVEAL_S)
                    return False
                if now < self.until:
                    return False
                self.step, self.shown, self.until = 'chat', False, now + self.secs(CHAT_S)
            elif self.step == 'chat':
                if len(self.chat_done) < 2 and now < self.until:
                    return False
                self.step, self.until = 'vote', now + self.secs(VOTE_S)
            elif self.step == 'vote':
                return all(self.votes[p] for p in self.pids) or now >= self.until
            else:
                return False
        return False

    # ---- what one player sees -------------------------------------------------------------------------------
    def view(self, pid: str, now: float) -> dict:
        o = self.other(pid)
        peer = self.info[o]
        f = dict(t='date', id=self.id, step=self.step, left=round(max(0.0, self.until - now), 1), of=N_CARDS,
                 peer=dict(pid=o, name=peer['name'], av=peer['av']))
        n = self.revealed()
        f['cards'] = [dict(q=CARDS[c][0], opts=list(CARDS[c][1]), me=self.picks[pid][k], them=self.picks[o][k])
                      for k, c in enumerate(self.cards[:n])]
        f['same'] = self.same()
        if self.step == 'card':
            q, opts = CARDS[self.cards[self.i]]
            f.update(i=self.i, q=q, opts=list(opts), mine=self.picks[pid][self.i], peer_done=self.picks[o][self.i] is not None,
                     shown=self.shown)
        if self.step == 'menu':
            f.update(menu=[dict(id=m, emo=MENU_INDEX[m][1], name=MENU_INDEX[m][2]) for m in self.menu], want=self.want[pid],
                     give=self.give[pid], peer_done=self.want[o] is not None and self.give[o] is not None, shown=self.shown)
        if self.ordered:
            item = lambda m: dict(id=m, emo=MENU_INDEX[m][1], name=MENU_INDEX[m][2]) if m else None   # noqa: E731
            f['order'] = dict(i_gave=item(self.give[pid]), they_want=item(self.want[o]), they_gave=item(self.give[o]),
                              i_want=item(self.want[pid]), hits=self.hits())
        if self.step == 'chat':
            f.update(done=pid in self.chat_done, quick=list(QUICK))
        if self.step == 'vote':
            f['mine'] = self.votes[pid]
        return f


class DatingFeature(Feature):
    name, flag = 'dating', 'dating'

    def __init__(self, app):
        super().__init__(app)
        self.queue: dict = {}           # pid -> Seat
        self.dates: dict = {}           # date id -> Date (in progress)
        self.in_date: dict = {}         # pid -> Date
        self.recent = LRU(100000)       # (pid, pid) -> when they last dated
        self.members = LRU(20000)       # 'date:<id>' -> (pid, pid): who may read and report its chat
        self.bonds = LRU(20000)         # pid -> set of pids "đang tìm hiểu"
        self.dirty = False
        self.matching = False
        self.last_match = 0.0
        self.started = self.ended = 0
        self.sat = Recent()             # who sat down lately ("đã ghé")
        self.hours = [0] * 24           # dates per hour of the day (Vietnam time): the busiest hours
        self.calls = LRU(20000)         # 📣 pid -> their last invitation
        self.called: deque = deque()    # when the street was invited in the last hour
        self.told_n = 0                 # the bench count the waiting players last heard

    @property
    def speed(self) -> float:
        """1 in production. Tests and the load test run dates faster (cfg.date_speed, env LIVE_DATE_SPEED)."""
        v = getattr(self.cfg, 'date_speed', None) or os.environ.get('LIVE_DATE_SPEED') or 1.0
        try:
            return max(0.1, float(v))
        except ValueError:
            return 1.0

    # ---- start ----------------------------------------------------------------------------------------------
    async def start(self):
        await wait_for_tables(self.db, ('live_dates', 'date_bonds', 'live_effects'))
        since = time.time() - AGAIN_S
        for r in await self.db.fetch("SELECT a, b, at FROM live_dates WHERE at>? AND how<>'cancelled' ORDER BY at LIMIT ?", (since, 100000)):
            self.recent.put(pair_key(r['a'], r['b']), float(r['at']))
        for r in await self.db.fetch('SELECT at FROM live_dates WHERE at>? ORDER BY at DESC LIMIT ?', (time.time() - HOT_DAYS * 86400, 20000)):
            self.hours[hour_of(float(r['at']))] += 1    # (index live_dates_at)
        chat = self.app.chat
        if chat is not None:
            chat.route('date:', audience=self._audience, can_read=lambda p, ch: p.pid in (self.members.get(ch) or ()))

    def _audience(self, ch: str) -> list:
        r = self.hub.rooms.get(ch)
        return [r] if r else []

    # ---- sockets --------------------------------------------------------------------------------------------
    async def on_hello(self, conn):
        p = conn.player
        if self.bonds.get(p.pid) is None:
            rows = await self.db.fetch('SELECT b AS x FROM date_bonds WHERE a=? UNION SELECT a AS x FROM date_bonds WHERE b=?', (p.sid, p.sid))
            self.bonds.put(p.pid, {pid_of(r['x']) for r in rows[:FRIENDS_MAX]})
        d = self.in_date.get(p.pid)
        if d is not None:           # back after a reconnect: into the date again
            d.away.pop(p.pid, None)
            room = self.hub.rooms.get(d.ch)
            if room is not None:
                room.add(conn)

    def welcome(self, conn) -> dict:
        p = conn.player
        out = dict(bonds=sorted(self.bonds.get(p.pid) or ()))
        d = self.in_date.get(p.pid)
        if d is not None:
            out['date'] = d.view(p.pid, time.time())
        elif p.pid in self.queue:
            out['bench'] = self.bench(p.pid)
        return out

    async def on_close(self, conn):
        p = conn.player
        if any(c.ready for c in p.conns):
            return
        if self.queue.pop(p.pid, None) is not None:
            self.dirty = True
        d = self.in_date.get(p.pid)
        if d is not None:
            d.away.setdefault(p.pid, time.time())

    def on_gone(self, player):
        self.queue.pop(player.pid, None)

    # ---- the bench ------------------------------------------------------------------------------------------
    def bench(self, pid: str) -> dict:
        s, now = self.queue.get(pid), time.time()
        n = len(self.queue)
        f = dict(t='bench', state='wait' if s else 'idle', n=n, recent=max(n, self.sat.count(now)), hot=hot_hours(self.hours))
        if s:
            f.update(waited=round(now - s.since, 1), pref=s.pref, call=round(self.call_wait(pid, now)))
            if s.npc:
                f['npc'] = int(s.since) % NPCS
        return f

    def npc_due(self, s: Seat, now: float) -> bool:
        return now - s.since >= NPC_AFTER / self.speed

    def call_wait(self, pid: str, now: float) -> float:
        """Seconds until this player may invite the street again (0: now)."""
        while self.called and self.called[0] <= now - 3600:
            self.called.popleft()
        last = self.calls.get(pid)
        mine = max(0.0, last + CALL_EVERY - now) if last is not None else 0.0
        street = max(0.0, self.called[0] + 3600 - now) if len(self.called) >= CALL_MAX_HOUR else 0.0
        return max(mine, street)

    @on('date_call', rate=(6, 60))
    async def call(self, conn, f):
        """📣 "Rủ mọi người": a line on Cả phố with a button to the dating corner (nothing stored)."""
        p, now = conn.player, time.time()
        if p.pid not in self.queue:
            raise LiveError('sit', 'Ngồi xuống ghế trước đã nhé.')
        chat = self.app.chat
        if chat is None:
            raise LiveError('off', 'Cả phố đang tắt.')
        if p.muted_until > now:
            raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))
        last = self.calls.get(p.pid)
        if last is not None and now - last < CALL_EVERY:
            raise LiveError('slow', 'Bạn vừa rủ rồi, lát nữa rủ tiếp nhé.', wait=round(last + CALL_EVERY - now))
        wait = self.call_wait(p.pid, now)
        if wait > 0:
            raise LiveError('busy', 'Phố vừa được rủ rồi, lát nữa thử lại nhé.', wait=round(wait))
        town = chat.town
        reach = [c for c in town.conns if c.player.pid != p.pid and p.pid not in c.player.hidden and c.player.pid not in p.hidden]
        if not reach:
            raise LiveError('empty', 'Cả phố đang vắng, lát nữa rủ nhé.')
        self.calls.put(p.pid, now)
        self.called.append(now)
        town.send(dict(t='call', ch='town', id='call:' + secrets.token_hex(4), kind='date', pid=p.pid, name=p.name, av=p.av,
                       at=round(now, 3)), sender=p)
        self.push_bench(p.pid)
        return dict(t='called', n=len({c.player.pid for c in reach}), wait=CALL_EVERY)

    def push_bench(self, pid: str) -> None:
        self.hub.send_many(self.hub.conns_of(pid), self.bench(pid))

    @on('queue', rate=(20, 60))
    async def queue_frame(self, conn, f):
        p, op = conn.player, f.get('op', 'sit')
        if op == 'peek':
            return self.bench(p.pid)
        if op == 'stand':
            if self.queue.pop(p.pid, None) is not None:
                self.dirty = True
            self.push_bench(p.pid)
            return None
        if op != 'sit':
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        pref, g, spot = f.get('pref', 'any'), f.get('g'), f.get('spot') or ''
        if pref not in PREFS or g not in (None, *GENDERS) or not isinstance(spot, str) or (spot and not SPOT.fullmatch(spot)):
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        if p.pid in self.in_date:
            raise LiveError('busy', 'Bạn đang trong một buổi hẹn.')
        if not p.name and self.app.chat is not None:
            await self.app.chat.refresh(p)
        if not p.name:
            raise LiveError('name', 'Đặt tên nhân vật trước khi hẹn hò nhé.')
        if not p.account and self.app.chat is not None:
            await self.app.chat.refresh(p)           # registered after the socket opened
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để hẹn hò nhé.')   # only accounts (owner, 01/10: "người lạ không chat được")
        if not p.loaded and not p.ext.get('hid') and self.app.chat is not None:
            await self.app.chat.load_hidden(p)       # chat off: the blocks are still needed here
            p.ext['hid'] = True
        s = self.queue.get(p.pid)
        if s is not None:
            s.pref, s.g, s.spot = pref, g, spot      # a new preference keeps the place on the bench
        else:
            if len(self.queue) >= QUEUE_MAX:
                raise LiveError('full', 'Ghế đang kín chỗ, lát quay lại nha.')
            self.queue[p.pid] = Seat(p.pid, pref, g, time.time(), spot)
            self.sat.put(p.pid, time.time())
        self.dirty = True
        self.push_bench(p.pid)
        await self.run_matcher()
        return None

    def ok_pair(self, a: Seat, b: Seat) -> bool:
        if a.pid in self.in_date or b.pid in self.in_date:
            return False
        if not (self.hub.online(a.pid) and self.hub.online(b.pid)) or self.hub.blocked(a.pid, b.pid):
            return False
        t = self.recent.get(pair_key(a.pid, b.pid))
        return t is None or time.time() - t >= AGAIN_S

    async def run_matcher(self) -> None:
        if self.matching:
            self.dirty = True
            return
        self.matching = True
        try:
            while self.dirty:
                self.dirty = False
                self.last_match = time.time()
                for a, b in match(list(self.queue.values()), self.ok_pair):
                    if self.queue.get(a.pid) is a and self.queue.get(b.pid) is b:
                        await self.begin(a, b)
        finally:
            self.matching = False

    def _ident(self, pid: str) -> dict | None:
        p = self.hub.players.get(pid)
        if p is None or not self.hub.online(pid):
            return None
        return dict(pid=p.pid, sid=p.sid, name=p.name, av=p.av, account=bool(p.account))

    async def begin(self, a: Seat, b: Seat) -> None:
        """Seat two players at a café table (both are taken off the bench first)."""
        self.queue.pop(a.pid, None)
        self.queue.pop(b.pid, None)
        ia, ib = self._ident(a.pid), self._ident(b.pid)
        if ia is None or ib is None:
            for s, i in ((a, ia), (b, ib)):
                if i is not None:
                    self.queue[s.pid] = s
            self.dirty = True
            return
        try:
            blocked = await self.db.fetchrow(
                'SELECT (SELECT 1 FROM blocks WHERE (pid=? AND target=?) OR (pid=? AND target=?) LIMIT 1) AS b1, '
                '(SELECT 1 FROM marriage_blocks WHERE (sid=? AND target=?) OR (sid=? AND target=?) LIMIT 1) AS b2',
                (a.pid, b.pid, b.pid, a.pid, ia['sid'], ib['sid'], ib['sid'], ia['sid']))
            if blocked and (blocked['b1'] or blocked['b2']):
                for x, y in ((a.pid, b.pid), (b.pid, a.pid)):
                    p = self.hub.players.get(x)
                    if p is not None:
                        p.hidden.add(y)
                self._back(a, b)
                return
            did = secrets.token_hex(6)
            x, y = pair_key(a.pid, b.pid)
            t = time.time()
            await self.db.execute('INSERT INTO live_dates(id, a, b, a_sid, b_sid, at) VALUES(?, ?, ?, ?, ?, ?)',
                                  (did, x, y, ia['sid'] if x == a.pid else ib['sid'], ib['sid'] if x == a.pid else ia['sid'], t))
        except DbError as e:
            log('dating begin db:', type(e).__name__)
            self._back(a, b)
            return
        ia, ib = self._ident(a.pid), self._ident(b.pid)   # the awaits: still both here?
        if ia is None or ib is None or a.pid in self.in_date or b.pid in self.in_date:
            self._back(*(s for s, i in ((a, ia), (b, ib)) if i is not None and s.pid not in self.in_date))
            try:
                await self.db.execute("UPDATE live_dates SET ended=?, how='cancelled' WHERE id=?", (time.time(), did))
            except DbError as e:
                log('dating cancel db:', type(e).__name__)
            return
        d = Date(did, ia, ib, time.time(), self.speed)
        self.dates[did] = d
        self.started += 1
        self.hours[hour_of(t)] += 1
        self.recent.put(pair_key(a.pid, b.pid), t)
        self.members.put(d.ch, d.pids)
        room = self.hub.room(d.ch, cap=2)
        for pid in d.pids:
            self.in_date[pid] = d
            for c in self.hub.conns_of(pid):
                room.add(c)
        self.push(d)

    def _back(self, *seats) -> None:
        """Seats back on the bench where they were (an unlucky match: blocked, or the other one left)."""
        for s in seats:
            if self.hub.online(s.pid) and s.pid not in self.in_date:
                self.queue[s.pid] = s
                self.push_bench(s.pid)
        self.dirty = True

    # ---- the date -------------------------------------------------------------------------------------------
    def push(self, d: Date, only: str | None = None) -> None:
        now = time.time()
        for pid in d.pids:
            if only is None or pid == only:
                self.hub.send_many(self.hub.conns_of(pid), d.view(pid, now))

    def mine(self, p, did) -> Date:
        d = self.in_date.get(p.pid)
        if d is None or d.ending or (did is not None and did != d.id):
            raise LiveError('no_date', 'Buổi hẹn đã kết thúc.')
        return d

    async def step(self, d: Date) -> None:
        before = (d.step, d.i, d.shown)
        if d.advance(time.time()):
            await self.finish(d, 'vote')
        elif (d.step, d.i, d.shown) != before:
            self.push(d)

    @on('answer', rate=(30, 10))
    async def answer(self, conn, f):
        p = conn.player
        d = self.mine(p, f.get('date'))
        step = f.get('step')
        if step != d.step or d.shown:
            raise LiveError('step', 'Bước này qua rồi.')
        if step == 'card':
            i, pick = f.get('i'), f.get('pick')
            if i != d.i:
                raise LiveError('step', 'Bước này qua rồi.')
            if type(pick) is not int or not 0 <= pick < len(CARDS[d.cards[i]][1]):
                raise LiveError('bad', 'Lựa chọn không hợp lệ.')
            if d.picks[p.pid][i] is not None:
                raise LiveError('done', 'Bạn chọn rồi.')
            d.picks[p.pid][i] = pick
        elif step == 'menu':
            want, give = f.get('want'), f.get('give')
            if want not in d.menu or give not in d.menu:
                raise LiveError('bad', 'Món không có trong thực đơn.')
            if d.give[p.pid] is not None:
                raise LiveError('done', 'Bạn gọi món rồi.')
            d.want[p.pid], d.give[p.pid] = want, give
        elif step == 'chat':
            d.chat_done.add(p.pid)
        else:
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        if d.advance(time.time()):
            await self.finish(d, 'vote')
        else:   # my pick to me, "đã chọn" to the other (never what I picked), or the reveal to both
            self.push(d)
        return None

    @on('heart', rate=(10, 10))
    async def heart(self, conn, f):
        p = conn.player
        d = self.mine(p, f.get('date'))
        v = f.get('v')
        if d.step != 'vote':
            raise LiveError('step', 'Chưa tới lúc chọn.')
        if v not in ('heart', 'wave'):
            raise LiveError('bad', 'Lựa chọn không hợp lệ.')
        if d.votes[p.pid] is not None:
            raise LiveError('done', 'Bạn chọn rồi.')
        d.votes[p.pid] = v
        if d.advance(time.time()):
            await self.finish(d, 'vote')
        else:
            self.push(d, only=p.pid)   # the other one is not told that I have chosen
        return None

    @on('date_say', rate=(8, 10))
    async def say(self, conn, f):
        p = conn.player
        d = self.mine(p, f.get('date'))
        if d.step != 'chat':
            raise LiveError('step', 'Chưa tới lúc trò chuyện.')
        cid = f.get('cid') if isinstance(f.get('cid'), str) and len(f.get('cid')) <= 40 else None
        frame = await self.app.chat.store_message(p, d.ch, f.get('text'), SAY_LEN, 3)
        room = self.hub.rooms.get(d.ch)
        if room is not None:
            room.send(frame, sender=p, skip=conn)
        self.hub.send(conn, dict(frame, cid=cid))
        return None

    @on('date_leave', rate=(10, 60))
    async def leave(self, conn, f):
        d = self.mine(conn.player, f.get('date'))
        await self.finish(d, 'left', by=conn.player.pid)
        return None

    @on('date_block', rate=(10, 60))
    async def block(self, conn, f):
        p = conn.player
        d = self.mine(p, f.get('date'))
        other = d.other(p.pid)
        t = time.time()
        await self.db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?) ON CONFLICT(pid, target) DO NOTHING', (p.pid, other, t))
        sa, sb = sorted((d.info[p.pid]['sid'], d.info[other]['sid']))
        await self.db.execute('DELETE FROM date_bonds WHERE a=? AND b=?', (sa, sb))
        p.hidden.add(other)
        o = self.hub.players.get(other)
        if o is not None:
            o.hidden.add(p.pid)
        for x, y in ((p.pid, other), (other, p.pid)):
            s = self.bonds.get(x)
            if s:
                s.discard(y)
        await self.finish(d, 'left', by=p.pid)
        self.hub.send_many(self.hub.conns_of(p.pid), dict(t='blocked', pid=other, on=True))
        return None

    @on('date_report', rate=(5, 60))
    async def report(self, conn, f):
        """Report the other one of a date (during it, or soon after): each of their messages in the date's chat
        gets a report (kind 'chat'), so it lands in the admin Chat tab with its context."""
        p, did, reason = conn.player, f.get('date'), f.get('reason', 'other')
        if not isinstance(did, str) or not DATE_ID.fullmatch(did) or reason not in REASONS:
            raise LiveError('bad', 'Báo cáo không hợp lệ.')
        ch = 'date:' + did
        pids = self.members.get(ch)
        if not pids or p.pid not in pids:
            raise LiveError('no_date', 'Không tìm thấy buổi hẹn này.')
        other = pids[1] if pids[0] == p.pid else pids[0]
        t = time.time()

        async def run(tx):
            rows = await tx.fetch('SELECT id FROM chat_messages WHERE channel=? AND pid=? ORDER BY id DESC LIMIT ?', (ch, other, REPORT_MSGS))
            for r in rows:
                if await tx.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'chat', ?, ?, ?) "
                                    'ON CONFLICT(reporter, kind, target) DO NOTHING', (p.pid, str(r['id']), reason, t)) == 1:
                    await tx.execute('UPDATE chat_messages SET reports=reports+1 WHERE id=?', (r['id'],))
            await tx.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'date', ?, ?, ?) "
                             'ON CONFLICT(reporter, kind, target) DO NOTHING', (p.pid, f'{did}:{other}', reason, t))
        await self.db.transaction(run)
        return dict(t='reported', date=did)

    async def finish(self, d: Date, how: str, by: str | None = None) -> None:
        """The end, for both: 'match' / 'nope' after the vote; 'left' (who went) / 'gone' (the other) otherwise."""
        if d.ending:
            return
        d.ending = True
        mutual = how == 'vote' and all(d.votes[p] == 'heart' for p in d.pids)
        result = 'match' if mutual else 'nope' if how == 'vote' else 'left'
        t = time.time()
        friends, spirit = False, dict.fromkeys(d.pids, 0)
        try:
            await self.db.execute('UPDATE live_dates SET ended=?, how=?, same=?, hits=? WHERE id=?', (t, result, d.same(), d.hits(), d.id))
            if mutual:
                friends, spirit = await self.bond(d)
        except DbError as e:
            log('dating finish db:', type(e).__name__)
        d.step = 'end'
        self.dates.pop(d.id, None)
        for pid in d.pids:
            if self.in_date.get(pid) is d:
                del self.in_date[pid]
        self.ended += 1
        for pid in d.pids:
            o = d.other(pid)
            end = dict(t='date', id=d.id, step='end', same=d.same(), of=N_CARDS, hits=d.hits(),
                       peer=dict(pid=o, name=d.info[o]['name'], av=d.info[o]['av']))
            if result == 'left':
                end['how'] = 'left' if pid == by else 'gone'
            else:
                end['how'] = result
            if mutual:
                end.update(friends=friends, spirit=spirit[pid])
            self.hub.send_many(self.hub.conns_of(pid), end)
        self.hub.drop_room(d.ch)

    async def bond(self, d: Date) -> tuple:
        """Both ❤️: the bond, friends (both have an account), +spirit (capped per day, paid once)."""
        a, b = (d.info[p] for p in d.pids)
        sa, sb = sorted((a['sid'], b['sid']))
        t = time.time()
        befriend = a['account'] and b['account']

        async def run(tx):
            await tx.execute('INSERT INTO date_bonds(a, b, at) VALUES(?, ?, ?) ON CONFLICT(a, b) DO UPDATE SET at=excluded.at', (sa, sb, t))
            if not befriend:
                return False
            if await tx.fetchval('SELECT 1 FROM friends WHERE sid=? AND friend=?', (a['sid'], b['sid'])):
                return True
            if await tx.fetchval('SELECT 1 FROM marriage_blocks WHERE (sid=? AND target=?) OR (sid=? AND target=?) LIMIT 1',
                                 (a['sid'], b['sid'], b['sid'], a['sid'])):
                return False
            for s in (a['sid'], b['sid']):
                if await tx.fetchval('SELECT COUNT(*) FROM friends WHERE sid=?', (s,)) >= FRIENDS_MAX:
                    return False
            for x, y in ((a['sid'], b['sid']), (b['sid'], a['sid'])):
                await tx.execute('INSERT INTO friends(sid, friend, since) VALUES(?, ?, ?) ON CONFLICT(sid, friend) DO NOTHING', (x, y, t))
            await tx.execute("UPDATE friend_requests SET status='cancelled', decided=? WHERE status='pending' AND "
                             '((from_sid=? AND to_sid=?) OR (from_sid=? AND to_sid=?))', (t, a['sid'], b['sid'], b['sid'], a['sid']))
            return True
        friends = await self.db.transaction(run)
        spirit = {}
        for p in (a, b):
            ok = await grant(self.db, p['sid'], 'spirit', SPIRIT, key=f'date:{d.id}:{p["pid"]}', data=dict(src='date', date=d.id), cap=SPIRIT_CAP)
            spirit[p['pid']] = SPIRIT if ok else 0
        for x, y in ((a['pid'], b['pid']), (b['pid'], a['pid'])):
            s = self.bonds.get(x)
            if s is not None:
                s.add(y)
            self.hub.send_many(self.hub.conns_of(x), dict(t='bond', pid=y))
        chat = self.app.chat
        if friends and chat is not None:
            for pid in d.pids:
                p = self.hub.players.get(pid)
                if p is not None:
                    await chat.load_friends(p)
                    self.hub.send_many([c for c in p.conns if c.ready], dict(t='state', friends=chat.friend_list(p)))
        return friends, spirit

    # ---- every second ---------------------------------------------------------------------------------------
    async def tick(self, now: float):
        for d in list(self.dates.values()):
            if d.ending:
                continue
            gone = next((pid for pid, at in d.away.items() if now - at >= GONE_S and not self.hub.conns_of(pid)), None)
            if gone is not None:
                await self.finish(d, 'left', by=gone)
                continue
            await self.step(d)
        if self.queue and (self.dirty or now - self.last_match >= MATCH_EVERY):
            self.dirty = True
            await self.run_matcher()
            self.tell_bench(now)

    def tell_bench(self, now: float) -> None:
        """After a matcher run: a neighbour for whoever has been alone NPC_AFTER, and the new count for everyone on the
        bench when it changed (one frame each, at most every MATCH_EVERY)."""
        n, changed = len(self.queue), len(self.queue) != self.told_n
        self.told_n = n
        for s in list(self.queue.values()):
            due = not s.npc and self.npc_due(s, now)
            if due:
                s.npc = True
            if due or changed:
                self.push_bench(s.pid)

    def stats(self) -> dict:
        return dict(bench=len(self.queue), dates=len(self.dates), started=self.started, ended=self.ended)
