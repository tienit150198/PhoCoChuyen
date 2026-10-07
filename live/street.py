"""🚶 Đi dạo khu phố (switch LIVE_STREET): online players stroll a place together, see each other move, talk in
speech bubbles, wave, sit at a tám chuyện table, and now and then something happens on the street.

Places and instances
* Four public places (live/street_data.py PLACES: Bờ hồ, Chợ đêm, Công viên, Phố đi bộ), each a 600 × 900
  world. A place has instances (rooms `walk:<place>:<n>`) of at most CAP = 20 players; `walk_in` picks the
  fullest instance with room that holds nobody blocked either way, else opens the next one.
* "Rủ đi cà phê" opens a private room `walk:cafe:<hex>` for the two of them (one table, two seats).
* A player is in one room at a time (all their tabs); a second tab walking in takes the first one out.

Moving (memory only, never the database)
* `move {x, y}`: the target is clamped into the place's walkable rectangles and routed around what is not
  walkable (lake, fountain, stalls) through the junctions between rectangles; the server stamps the start
  time and everyone interpolates `p` (the path) from `at` at SPEED units per second. At most 4 moves per
  second per player (the dispatcher's rate limit).
* Room diffs (moves, comings and goings, seats, table cards) are queued and sent as one `walk` frame at most
  every FLUSH = 0.1 s per room (≤ 10 per second); several moves of one player in that window send only the
  last. Speech bubbles and emotes go out at once.
* Blocks: blocked players are never put in the same instance; a block made during a stroll makes both
  invisible to each other at once (an `out` for each), and every frame from one never reaches the other.
* 🛵 Riding (public/js/v4/ride.js): `walk_in` may carry `r` {v: a two-wheeler's id, c: its paint id}, and `ride {r}`
  (r null: on foot again) changes it during a stroll. A rider moves RIDE_FAST times as fast: their public entry has
  `r` and `v` (their speed, units a second) only while riding, an `rd` diff {pid, r, v, p, at} tells the room, and
  their path is re-stamped from where they are. Optional everywhere: an older client sends none and ignores them
  (it draws a rider walking, a little behind); a café and a wedding are always on foot.
  💑 Vợ chồng chung xe (live/coride.py): `r` may name the spouse's vehicle (`o`: its owner's pid); first come drives
  (the other is answered `walk_taken {by, name}`, also as `taken` in walk_room); `back {to}` sits behind the spouse
  riding here: the passenger's entry has `b` (the driver's pid) and every walk of the driver is theirs too (`mv`
  with `b`); a `mv` without `b` is them on foot again.
* 🎨 A name colour, frame or title of the week (game/spend.py, read from `chat_style` by live/styles.py, never sent by a
  client): a public entry and a `card` may carry `st` {c?, f?, t?}; the bought title also leads `ti` after the honours,
  so an older client shows it as text. Optional: an older client ignores `st`, an older service sends none.

Talking
* `say {text}` goes through the chat's store_message (filters, mutes, duplicates, kept like all chat) in the
  channel = the room id, then to the room as `said` (a 6 s bubble on screen). The chat's route() makes `del`,
  `report` (3 → hidden) and the admin's hide/keep reach the room. `emote {e}`: 👋 ❤️ 😂 😮 🙏.
* `card {pid}` (tap a player): name, title, look, friend or not, and the player code for a friend request
  through the game's own friends API (accounts only).

Tables and happenings
* `sit {table}` / `stand` / `topic` (vote to change): a table seats 2-4; sitting deals a topic card, a new one
  every TOPIC_SECS (2 minutes) or as soon as everyone seated voted.
* Happenings (tick): at most one per public instance per HAPPEN_GAP (10 minutes): a vendor calls out, a
  lion-dance troupe crosses, or a lucky red envelope appears; the first `grab` gets a few xu through
  live/effects.grant (idempotent per envelope, capped per player per Vietnam day), paid into the wallet by the
  game server (game/live_effects.py).

Frames (client → server; replies in brackets)
  walk_places {}                                   [walk_places {places: [{id, name, icon, n}]}]
  walk_in {place, look, g, title, titles, r?}      [walk_room {place, room, me, people, tables, geo, hap, at}]
  walk_out {}  move {x, y}  say {text}  emote {e}  sit {table}  stand {}  topic {}  ride {r}  back {to}
  card {pid}                                       [card {...}]
  invite {pid}                                     [invite_sent {id, pid}]; the other gets invited {id, pid, name}
  invite_reply {id, ok}                            [both: walk_room of the café | the inviter: invite_no {id}]
  grab {id}                                        [grabbed {id, n}; the room: happen_end {id, pid, name, n}]
Server pushes: walk {ev: [{k: mv|in|out|tb|rd, ...}], at}, said, emoted, happen, happen_end, walk_left {why}.

For phase 3 (the dating bench lives in this scene): `spot(place, 'bench')` gives the bench's position,
`where(player)` the (place, room) a player is strolling in.
"""
from __future__ import annotations

import asyncio
import heapq
import math
import random
import re
import secrets
import time

from . import coride, effects, styles
from .db import Error as DbError, log
from .protocol import Feature, LiveError, on
from .street_data import ORG_GRADES, PET_ACCS, PET_BREEDS
from . import filters
from .street_data import (CERTS, COLOR_IDS, EMOTES, LOOK_DEFAULTS, LOOK_IDS, LOOK_SLOTS, PAINTABLE, PLACES, PUBLIC, TINT_MAX,
                          TINT_SLOTS, TITLES, TOPICS, VENDORS, H, W)

PREFIX = 'walk:'
WEAR_MAX = 3              # game/journey.py WEAR_MAX: titles and certificates worn at once
LB_EVERY = 600            # seconds between reads of the weekly leaderboard titles (game/lb_titles.py lb_weekly)
CAP = 20                  # players per instance
INSTANCES_MAX = 250       # per place (5,000 sockets at most anyway)
SPEED = 170.0             # world units per second
FLUSH = 0.1               # seconds between two room diffs (≤ 10 per second)
EVENTS_MAX = 400          # queued diff events per room before an early flush
SAY_LEN = 120
TOPIC_SECS = 120
HAPPEN_GAP = 600          # at most one happening per public instance per 10 minutes
HAPPEN_JITTER = 300       # ... plus up to 5 minutes, so instances do not all fire at once
FIRST_HAPPEN = (60, 240)  # the first one in a new instance comes sooner
ENVELOPE_SECS = 45
ENVELOPE_XU = (3, 8)
ENVELOPE_CAP = 30         # xu from envelopes per player per Vietnam day
INVITE_SECS = 30
INVITES_MAX = 2000
SEEN_MAX = 6              # rooms a player may still report bubbles of (the last ones they were in)
STEP = 5.0                # sampling step when checking that a segment stays walkable
# 🛵 The vehicles a player may ride on a stroll (and at the fair): game/garage.py's two-wheelers (tests/test_ride.py
# keeps the two lists together). A car stays outside: these are walking places.
RIDES = frozenset({'xe_dap', 'xe_dap_dien', 'xe_so', 'xe_ga'})
RIDE_FAST = 1.6
_WORD = re.compile(r'[a-z0-9_]{1,24}')


def _num(v) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


# ---------------------------------------------------------------- geometry (mirrored in public/js/v4/walk.js)
class Geo:
    """A place's walkable rectangles, the junctions between them, the tables' seats and its spots."""

    def __init__(self, pid: str, spec: dict):
        self.id, self.name, self.icon = pid, spec['name'], spec['icon']
        self.private = bool(spec.get('private'))
        self.rects = [tuple(float(v) for v in r) for r in spec['walk']]
        self.junctions = []
        for i, a in enumerate(self.rects):
            for b in self.rects[i + 1:]:
                x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
                if x0 <= x1 and y0 <= y1:
                    self.junctions.append((round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)))
        n = len(self.junctions)
        self.jok = [[i != j and self.seg_ok(self.junctions[i], self.junctions[j]) for j in range(n)] for i in range(n)]
        self.tables = []
        for (x, y, seats) in spec['tables']:
            pts = []
            for i in range(seats):
                th = -math.pi / 2 + math.pi / seats + 2 * math.pi * i / seats
                pts.append(self.clamp(x + 56 * math.cos(th), y + 36 * math.sin(th)))
            self.tables.append(dict(x=x, y=y, n=seats, seats=pts))
        self.spots = {k: self.clamp(*v) for k, v in spec['spots'].items()}
        self.big = max(self.rects, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))

    def inside(self, x: float, y: float) -> bool:
        for (x0, y0, x1, y1) in self.rects:
            if x0 - .5 <= x <= x1 + .5 and y0 - .5 <= y <= y1 + .5:
                return True
        return False

    def clamp(self, x: float, y: float) -> tuple:
        """The walkable point nearest to (x, y)."""
        best, bd = None, None
        for (x0, y0, x1, y1) in self.rects:
            cx, cy = min(max(x, x0), x1), min(max(y, y0), y1)
            d = (cx - x) ** 2 + (cy - y) ** 2
            if bd is None or d < bd:
                best, bd = (cx, cy), d
        return (round(best[0], 1), round(best[1], 1))

    def seg_ok(self, a, b) -> bool:
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, math.ceil(d / STEP))
        for i in range(n + 1):
            t = i / n
            if not self.inside(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t):
                return False
        return True

    def route(self, a, b) -> list:
        """A walkable path from a to b (both walkable): straight when it can be, else through junctions."""
        a, b = (round(a[0], 1), round(a[1], 1)), (round(b[0], 1), round(b[1], 1))
        if self.seg_ok(a, b):
            return [list(a), list(b)]
        J = self.junctions
        n = len(J)
        start = [self.seg_ok(a, j) for j in J]
        end = [self.seg_ok(j, b) for j in J]
        heap = [(0.0, -1)]             # (distance so far, junction index; -1 is a)
        best = {-1: 0.0}
        prev: dict = {}
        goal, goal_d = None, math.inf
        while heap:
            d, u = heapq.heappop(heap)
            if d > best.get(u, math.inf) or d >= goal_d:
                continue
            here = a if u < 0 else J[u]
            if u >= 0 and end[u]:
                gd = d + math.hypot(b[0] - here[0], b[1] - here[1])
                if gd < goal_d:
                    goal, goal_d = u, gd
            for v in range(n):
                ok = start[v] if u < 0 else self.jok[u][v]
                if not ok:
                    continue
                nd = d + math.hypot(J[v][0] - here[0], J[v][1] - here[1])
                if nd < best.get(v, math.inf):
                    best[v] = nd
                    prev[v] = u
                    heapq.heappush(heap, (nd, v))
        if goal is None:
            return [list(a), list(a)]
        pts, u = [list(b)], goal
        while u is not None and u >= 0:
            pts.append(list(J[u]))
            u = prev.get(u)
        pts.append(list(a))
        return pts[::-1]

    def random_point(self, margin: float = 30.0) -> tuple:
        x0, y0, x1, y1 = random.choice(self.rects)
        mx, my = min(margin, (x1 - x0) / 2), min(margin, (y1 - y0) / 2)
        return (round(random.uniform(x0 + mx, x1 - mx), 1), round(random.uniform(y0 + my, y1 - my), 1))

    def public(self) -> dict:
        return dict(w=W, h=H, walk=[list(r) for r in self.rects], junctions=[list(j) for j in self.junctions],
                    tables=[dict(x=t['x'], y=t['y'], n=t['n'], seats=[list(s) for s in t['seats']]) for t in self.tables],
                    spots={k: list(v) for k, v in self.spots.items()})


GEO = {k: Geo(k, v) for k, v in PLACES.items()}


def clean_ride(r) -> dict | None:
    """The vehicle a player rides ({v, c, o?}) or None (on foot): never refused, anything odd counts as on foot.
    `o`: its owner's pid when it is the spouse's (live/coride.py checks it), kept only when it looks like one."""
    if not isinstance(r, dict) or not isinstance(r.get('v'), str) or r['v'] not in RIDES:
        return None
    c, o = r.get('c'), r.get('o')
    out = dict(v=r['v'], c=c if isinstance(c, str) and _WORD.fullmatch(c) else '')
    if isinstance(o, str) and coride.PID.fullmatch(o):
        out['o'] = o
    return out


def pos_at(path: list, t0: float, now: float, speed: float = SPEED) -> tuple:
    """Where someone walking `path` since t0 is at `now` (the last point once arrived)."""
    left = max(0.0, now - t0) * speed
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if left <= seg and seg > 0:
            t = left / seg
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        left -= seg
    return (path[-1][0], path[-1][1])


def clean_look(look, g) -> tuple[dict, str | None]:
    """The public look a client sends: a dict of wardrobe slots → item ids, and maybe `tint` {item id: colour id}
    (bảng màu: accessories since 1.3.1, then clothes and shoes). Wrong shape: refused; an id this build does not
    know: the gender's default for that slot, no colour. Only the colours of what is worn are kept (at most one
    small entry per slot of TINT_SLOTS in the frames)."""
    if g not in ('male', 'female', None):
        g = None
    out = dict(LOOK_DEFAULTS[g])
    if look is None:
        return out, g
    if not isinstance(look, dict) or len(look) > len(LOOK_SLOTS) + 2:
        raise LiveError('bad', 'Dáng nhân vật không hợp lệ.')
    tint = None
    for k, v in look.items():
        if k == 'uniform':
            continue
        if k == 'tint':
            if not isinstance(v, dict) or len(v) > TINT_MAX or not all(
                    isinstance(a, str) and isinstance(b, str) and len(a) <= 24 and len(b) <= 24 for a, b in v.items()):
                raise LiveError('bad', 'Dáng nhân vật không hợp lệ.')
            tint = v
            continue
        if k not in LOOK_SLOTS or not isinstance(v, str) or len(v) > 24:
            raise LiveError('bad', 'Dáng nhân vật không hợp lệ.')
        if v in LOOK_IDS[k]:
            out[k] = v
    if tint:
        worn = {out[slot]: tint[out[slot]] for slot in TINT_SLOTS
                if out[slot] in PAINTABLE and tint.get(out[slot]) in COLOR_IDS}
        if worn:
            out['tint'] = worn
    return out, g


def clean_rank(rk) -> dict | None:
    """🎖️ The rank a client says its character wears ({o: org, g: grade id}, game/org.py): kept only when both ids are
    known here; anything else simply shows no rank (never refused: an older or newer client still walks in)."""
    if isinstance(rk, dict) and len(rk) == 2 and rk.get('g') in ORG_GRADES.get(rk.get('o'), ()):
        return dict(o=rk['o'], g=rk['g'])
    return None


def clean_pet(pt) -> dict | None:
    """🐾 The pet a client says walks beside its character ({b: breed, c: coat, n: name, a: [accessory ids]},
    game/pets.py walk_ref): kept only when the breed and coat are known here; the name goes through the chat filter
    (heavy words masked, links and contacts dropped), unknown accessories are left out. Anything else shows no pet
    (never refused: an older or newer client still walks in)."""
    if not isinstance(pt, dict) or set(pt) - {'b', 'c', 'n', 'a'} or pt.get('b') not in PET_BREEDS:
        return None
    c = pt.get('c', 0)
    if type(c) is not int or not 0 <= c < PET_BREEDS[pt['b']]:
        return None
    n = filters.clean(pt.get('n'), 16, 1)
    n = filters.mask(n) if n else None
    acc = pt.get('a') if isinstance(pt.get('a'), list) else []
    out = dict(b=pt['b'], c=c, a=[x for x in acc[:3] if isinstance(x, str) and x in PET_ACCS])
    if n:
        out['n'] = n
    return out


class Walker:
    __slots__ = ('pid', 'player', 'name', 'title', 'look', 'g', 'path', 't0', 'seat', 'ride', 'back', 'pill', 'st', 'rk', 'pt')

    def __init__(self, player, look: dict, g, title, at: tuple, now: float, ride: dict | None = None, rk: dict | None = None,
                 pt: dict | None = None):
        self.rk, self.pt = rk, pt
        self.pid, self.player = player.pid, player
        self.name = player.name or 'Khách dạo phố'
        self.title, self.look, self.g = title, look, g
        self.path, self.t0, self.seat = [list(at), list(at)], now, None
        self.ride = ride
        self.back = self.pill = None   # 🛵 the driver I sit behind / who sits behind me (pids, live/coride.py)
        self.st = None                 # 🎨 name colour / frame / title of the week (live/styles.py), outside the look

    @property
    def speed(self) -> float:
        return SPEED * RIDE_FAST if self.ride or self.back else SPEED

    def at(self, now: float) -> tuple:
        return pos_at(self.path, self.t0, now, self.speed)

    def public(self) -> dict:
        d = dict(pid=self.pid, name=self.name, ti=self.title, lk=self.look, g=self.g, p=self.path, at=round(self.t0, 3),
                 s=list(self.seat) if self.seat else None)
        if self.rk:
            d['rk'] = self.rk
        if self.pt:
            d['pt'] = self.pt
        if self.ride:
            d['r'], d['v'] = self.ride, self.speed
        if self.back:
            d['b'], d['v'] = self.back, self.speed
        if self.st:
            d['st'] = self.st
        return d


class Table:
    __slots__ = ('i', 'x', 'y', 'n', 'pts', 'seats', 'topic', 'until', 'votes', 'deck')

    def __init__(self, i: int, spec: dict):
        self.i, self.x, self.y, self.n, self.pts = i, spec['x'], spec['y'], spec['n'], spec['seats']
        self.seats: list = [None] * self.n
        self.topic, self.until, self.votes, self.deck = None, 0.0, set(), []

    def seated(self) -> set:
        return {s for s in self.seats if s}

    def deal(self, now: float) -> None:
        if not self.deck:
            self.deck = random.sample(range(len(TOPICS)), len(TOPICS))
        self.topic, self.until = TOPICS[self.deck.pop()], now + TOPIC_SECS
        self.votes.clear()

    def public(self) -> dict:
        return dict(k='tb', i=self.i, seats=list(self.seats), topic=self.topic, until=round(self.until, 1), votes=len(self.votes))


class StreetFeature(Feature):
    name, flag = 'street', 'street'
    PREFIXES = (PREFIX, 'wed:')        # rooms this machinery runs: strolls, and live/wedding.py's parties

    def __init__(self, app):
        super().__init__(app)
        self.invites: dict = {}        # id -> dict(frm, to, room, until)
        self.flushes = 0               # diff frames sent (stats)
        self.leave_hooks: list = []    # fn(player): live/wedding.py forgets an overflow guest on walk_out
        self.lb: dict = {}             # sid -> the best weekly leaderboard title held now (game/lb_titles.py)
        self.lb_at = 0.0
        if self.cfg.street or self.cfg.fair:   # 💑 `back`, `fair_back`, `o` and `b` are understood (live/coride.py)
            self.cfg.flags_extra['coride'] = True

    def enabled(self) -> bool:
        """Moves, bubbles, emotes and tables also run the wedding parties (LIVE_WEDDING); walk_in needs LIVE_STREET."""
        return bool(self.cfg.street or getattr(self.cfg, 'wedding', False))

    def rooms(self) -> list:
        return [r for p in self.PREFIXES for r in self.hub.rooms_with_prefix(p)]

    def title_of(self, player, title, titles=None, st=None) -> str | None:
        """The name tag's title. An honour first: this week's race title (live/wedding.py), else the best weekly
        leaderboard title held now (lb_weekly), else a 🎨 title of the week the player paid for (`st`, live/styles.py);
        then what the player wears (`titles`: up to WEAR_MAX title and certificate ids, or the one `title` of an older
        client). The first shows by name, the others by emoji: "👑 Trùm cuối của phố 🌱🎓"."""
        wed = self.app.by_name.get('wedding')
        won = wed.race_title(player.pid) if wed is not None and wed.enabled() else None
        won = won or self.lb.get(player.sid) or styles.title_text(st)
        ids = titles if isinstance(titles, list) and titles else [title]
        worn = []
        for x in ids[:WEAR_MAX]:
            text = (TITLES.get(x) or CERTS.get(x)) if isinstance(x, str) else None
            if text and text not in worn:
                worn.append(text)
        lead = won or (worn.pop(0) if worn else None)
        if lead is None:
            return None
        icons = ''.join(t.split(' ', 1)[0] for t in worn if t != lead)
        return f'{lead} {icons}' if icons else lead

    async def lb_fresh(self, now: float | None = None) -> None:
        """Read the weekly leaderboard titles every LB_EVERY seconds (≤ 58 rows; the game refreshes them daily)."""
        now = time.time() if now is None else now
        if now - self.lb_at < LB_EVERY:
            return
        self.lb_at = now
        try:
            rows = await self.db.fetch('SELECT sid, board, rank, title FROM lb_weekly WHERE final=0')
        except DbError as e:   # a database from before the table: no weekly titles
            log('lb titles:', type(e).__name__)
            return
        from game.lb_titles import honour
        best: dict = {}
        for r in rows:
            k = honour(r['board'], int(r['rank']))
            if r['sid'] not in best or k < best[r['sid']][0]:
                best[r['sid']] = (k, r['title'])
        self.lb = {sid: v[1] for sid, v in best.items()}

    async def start(self):
        if self.app.chat:
            self.app.chat.route(PREFIX, audience=self._audience, can_read=self._can_read)

    # ---- for the chat's route (bubbles: delete, report, admin hide) and for phase 3 --------------------------
    def _audience(self, ch: str) -> list:
        r = self.hub.rooms.get(ch)
        return [r] if r is not None else []

    def _can_read(self, player, ch: str) -> bool:
        return ch in player.ext.get('walk_seen', ())

    def spot(self, place: str, name: str):
        g = GEO.get(place)
        return g.spots.get(name) if g else None

    def where(self, player) -> tuple | None:
        rid = player.ext.get('walk')
        room = self.hub.rooms.get(rid) if rid else None
        return (room.data['place'], room) if room is not None else None

    # ---- rooms ----------------------------------------------------------------------------------------
    def _new_room(self, rid: str, place: str, cap: int | None = None, on_empty=None):
        """A room of this machinery. cap: None = the place's (20, or 2 for the café); 0 = no cap (a wedding counts its own)."""
        room = self.hub.room(rid, cap=(CAP if not GEO[place].private else 2) if cap is None else cap, on_empty=on_empty or self._empty)
        now = time.time()
        room.data.update(place=place, people={}, tables=[Table(i, t) for i, t in enumerate(GEO[place].tables)], ev=[], mvi={},
                         h=None, last=0.0, hap=None, env=None, hidden_seen=set(),
                         next_hap=now + random.uniform(*FIRST_HAPPEN) if not GEO[place].private else math.inf)
        return room

    def _empty(self, room) -> None:
        h = room.data.get('h')
        if h is not None:
            h.cancel()
        self.hub.drop_room(room.id)
        for k in [k for k, v in self.invites.items() if v['room'] == room.id]:
            self.invites.pop(k, None)

    def _pick(self, place: str, p):
        rooms = [r for r in self.hub.rooms_with_prefix(f'{PREFIX}{place}:')]
        ok = [r for r in rooms if len(r.data['people']) < CAP and
              not any(q in p.hidden or p.pid in w.player.hidden for q, w in r.data['people'].items())]
        if ok:
            return max(ok, key=lambda r: (len(r.data['people']), -int(r.id.rsplit(':', 1)[1])))
        if len(rooms) >= INSTANCES_MAX:
            raise LiveError('full', 'Chỗ này đông quá, thử chỗ khác nhé.')
        used = {r.id for r in rooms}
        n = 1
        while f'{PREFIX}{place}:{n}' in used:
            n += 1
        return self._new_room(f'{PREFIX}{place}:{n}', place)

    def _enter(self, room, conn, w: Walker) -> None:
        p = conn.player
        room.add(conn)
        room.data['people'][p.pid] = w
        p.ext['walk'] = room.id
        conn.ext['walk'] = room.id
        seen = p.ext.setdefault('walk_seen', [])
        if room.id not in seen:
            seen.append(room.id)
            del seen[:-SEEN_MAX]
        self._queue(room, p.pid, dict(k='in', **w.public()))

    def _snapshot(self, room, p, now: float) -> dict:
        d = room.data
        g = GEO[d['place']]
        people = [w.public() for q, w in d['people'].items() if q == p.pid or not (q in p.hidden or p.pid in w.player.hidden)]
        hap = d['hap'] if d['hap'] and d['hap']['end'] > now else None
        env = d['env']
        return dict(t='walk_room', place=d['place'], name=g.name, icon=g.icon, private=g.private, room=room.id, me=p.pid,
                    people=people, tables=[t.public() for t in d['tables']], geo=g.public(), speed=SPEED, cap=CAP,
                    hap=hap, env=dict(id=env['id'], x=env['x'], y=env['y'], until=round(env['until'], 1)) if env and not env['taken'] else None,
                    at=round(now, 3))

    def _remove_walker(self, room, pid: str) -> None:
        d = room.data
        w = d['people'].pop(pid, None)
        if w is None:
            return
        if w.seat:
            self._unseat(room, w, time.time())
        if w.back:   # 🛵 a passenger left: the seat behind is free
            dr = d['people'].get(w.back)
            if dr is not None and dr.pill == pid:
                dr.pill = None
        if w.pill:   # the driver left: the passenger gets off where they are, on foot
            self._hop_off(room, d['people'].get(w.pill), time.time())
        for k in [k for k, v in self.invites.items() if pid in (v['frm'], v['to'])]:
            self.invites.pop(k, None)
        self._queue(room, pid, dict(k='out', pid=pid))

    def _leave_player(self, p, why: str | None = None, keep=None) -> None:
        """Take every socket of player p out of the room they stroll in (`keep`: the socket that asked)."""
        rid = p.ext.pop('walk', None)
        room = self.hub.rooms.get(rid) if rid else None
        if room is None:
            return
        for c in [c for c in room.conns if c.player is p]:
            c.ext.pop('walk', None)
            if why and c is not keep:
                self.hub.send(c, dict(t='walk_left', why=why))
        if self.hub.rooms.get(rid) is room:
            self._remove_walker(room, p.pid)
        for c in [c for c in room.conns if c.player is p]:
            room.remove(c)

    def _me(self, conn):
        rid = conn.ext.get('walk')
        room = self.hub.rooms.get(rid) if rid else None
        w = room.data['people'].get(conn.player.pid) if room is not None else None
        if w is None:
            raise LiveError('not_in', 'Bạn chưa ở trên phố.')
        return room, w

    async def _ensure_loaded(self, p) -> None:
        chat = self.app.chat
        if chat is None:
            return
        if not p.loaded:   # the chat is off: its hello did not load friends and blocks
            await chat.load_friends(p)
            await chat.load_hidden(p)
            p.loaded = True
        if not p.name:
            await chat.refresh(p)

    # ---- the diff queue (≤ 10 frames per second per room) -------------------------------------------------
    def _queue(self, room, sender: str | None, ev: dict) -> None:
        d = room.data
        if ev['k'] == 'mv' and sender in d['mvi']:
            d['ev'][d['mvi'][sender]] = (sender, ev)
        else:
            if ev['k'] == 'mv':
                d['mvi'][sender] = len(d['ev'])
            d['ev'].append((sender, ev))
        if len(d['ev']) >= EVENTS_MAX:
            if d['h'] is not None:
                d['h'].cancel()
            self._flush(room)
            return
        if d['h'] is None:
            delay = max(0.0, d['last'] + FLUSH - time.monotonic())
            d['h'] = asyncio.get_running_loop().call_later(delay, self._flush, room)

    def _flush(self, room) -> None:
        d = room.data
        d['h'] = None
        evs, d['ev'], d['mvi'], d['last'] = d['ev'], [], {}, time.monotonic()
        if not evs or self.hub.rooms.get(room.id) is not room:
            return
        self.flushes += 1
        at = round(time.time(), 3)
        conns = [c for c in room.conns if c.ready]
        pids = {c.player.pid for c in conns}
        if not any(c.player.hidden & pids for c in conns):
            self.hub.send_many(conns, dict(t='walk', ev=[e for _, e in evs], at=at))
            return
        senders = {s for s, _ in evs if s}
        groups: dict = {}
        for c in conns:
            me = c.player
            ex = frozenset(s for s in senders if s in me.hidden or self.hub.blocked(me.pid, s))
            groups.setdefault(ex, []).append(c)
        for ex, cs in groups.items():
            out = [e for s, e in evs if s not in ex]
            if out:
                self.hub.send_many(cs, dict(t='walk', ev=out, at=at))

    # ---- handlers -----------------------------------------------------------------------------------------
    @on('walk_places', rate=(10, 10))
    async def walk_places(self, conn, f):
        if not self.cfg.street:
            raise LiveError('off', 'Tính năng này đang tắt.')
        out = []
        for place in PUBLIC:
            n = sum(len(r.data['people']) for r in self.hub.rooms_with_prefix(f'{PREFIX}{place}:'))
            g = GEO[place]
            out.append(dict(id=place, name=g.name, icon=g.icon, n=n))
        rid = conn.ext.get('walk')
        return dict(t='walk_places', places=out, here=rid)

    @on('walk_in', rate=(8, 60))
    async def walk_in(self, conn, f):
        if not self.cfg.street:
            raise LiveError('off', 'Tính năng này đang tắt.')
        place = f.get('place')
        if place not in PUBLIC:
            raise LiveError('bad', 'Không có chỗ này.')
        look, g = clean_look(f.get('look'), f.get('g'))
        p = conn.player
        await self.lb_fresh()
        st = await styles.of_app(self.app).one(p.pid)   # 🎨 read from chat_style, never from the frame
        title = self.title_of(p, f.get('title'), f.get('titles'), st)
        await self._ensure_loaded(p)
        r, by = await coride.check(self.db, self.hub, p, clean_ride(f.get('r')))   # no await from here on
        self._leave_player(p, 'other', keep=conn)
        room = self._pick(place, p)
        now = time.time()
        sx, sy = GEO[place].spots['spawn']
        at = GEO[place].clamp(sx + random.uniform(-150, 150), sy + random.uniform(-45, 45))
        w = Walker(p, look, g, title, at, now, r, clean_rank(f.get('rk')), clean_pet(f.get('pt')))
        w.st = st or None
        self._enter(room, conn, w)
        out = self._snapshot(room, p, now)
        if by:
            out['taken'] = coride.taken_frame('walk_taken', self.hub, by)
        return out

    @on('walk_out', rate=(10, 60))
    async def walk_out(self, conn, f):
        self._leave_player(conn.player, 'out', keep=conn)
        for fn in self.leave_hooks:
            fn(conn.player)
        return dict(t='walk_left', why='out')

    @on('move', rate=(4, 1.0))
    async def move(self, conn, f):
        room, w = self._me(conn)
        x, y = f.get('x'), f.get('y')
        if not (_num(x) and _num(y)):
            raise LiveError('bad', 'Vị trí không hợp lệ.')
        if w.back:   # 🛵 sitting behind: the driver drives
            return None
        now = time.time()
        if w.seat:
            self._unseat(room, w, now)
        g = GEO[room.data['place']]
        w.path, w.t0 = g.route(w.at(now), g.clamp(x, y)), now
        self._queue(room, w.pid, dict(k='mv', pid=w.pid, p=w.path, at=round(now, 3)))
        self._carry(room, w)
        return None

    @on('ride', rate=(6, 10))
    async def ride(self, conn, f):
        """🛵 On or off the vehicle mid-stroll (`r`: {v, c} or null). Where they are now stays; the rest of the
        path goes on at the new speed."""
        room, w = self._me(conn)
        if w.back or GEO[room.data['place']].private:
            return None
        r, by = await coride.check(self.db, self.hub, conn.player, clean_ride(f.get('r')))   # no await from here on
        room, w = self._me(conn)
        if w.back:
            return None
        if by:
            return coride.taken_frame('walk_taken', self.hub, by)
        if r == w.ride:
            return None
        now = time.time()
        here, end = w.at(now), tuple(w.path[-1])
        if r is None and w.pill:
            self._hop_off(room, room.data['people'].get(w.pill), now)
        w.ride = r
        w.path, w.t0 = GEO[room.data['place']].route(here, end), now
        self._queue(room, w.pid, dict(k='rd', pid=w.pid, r=r, v=w.speed, p=w.path, at=round(now, 3)))
        self._carry(room, w)
        return None

    # ---- 🛵 sitting behind the spouse (live/coride.py) ---------------------------------------------------------
    def _carry(self, room, w: Walker) -> None:
        """The driver's passenger goes the driver's way (an older client: walking it, a little behind)."""
        q = room.data['people'].get(w.pill) if w.pill else None
        if q is None or q.back != w.pid:
            w.pill = None
            return
        q.path, q.t0 = [list(pt) for pt in w.path], w.t0
        self._queue(room, q.pid, dict(k='mv', pid=q.pid, p=q.path, at=round(q.t0, 3), b=w.pid, v=q.speed))

    def _hop_off(self, room, q, now: float) -> None:
        """The passenger q gets off where the vehicle is now, on foot (a walk of nowhere: `b` gone)."""
        if q is None or not q.back:
            return
        d = room.data['people'].get(q.back)
        if d is not None and d.pill == q.pid:
            d.pill = None
        here = q.at(now)
        q.back = None
        q.path, q.t0 = [list(here), list(here)], now
        self._queue(room, q.pid, dict(k='mv', pid=q.pid, p=q.path, at=round(now, 3)))

    @on('back', rate=(6, 10))
    async def back(self, conn, f):
        """🛵 `back {to}`: sit behind my husband / wife riding here (to: null: get off)."""
        room, w = self._me(conn)
        to = f.get('to')
        if to is None:
            self._hop_off(room, w, time.time())
            return None
        if not isinstance(to, str) or not coride.PID.fullmatch(to):
            raise LiveError('bad', 'Không có ai như vậy.')
        sp = await coride.spouse(self.db, conn.player)
        room, w = self._me(conn)
        d = room.data['people'].get(to)
        if sp != to or d is None or GEO[room.data['place']].private:
            raise LiveError('no_back', 'Chỉ ngồi sau xe của vợ/chồng mình thôi.')
        if w.back == to:
            return None
        if not d.ride or d.back or d.pill not in (None, w.pid):
            raise LiveError('no_back', 'Xe này không còn chỗ ngồi sau.')
        now = time.time()
        if w.seat:
            self._unseat(room, w, now)
        if w.pill:
            self._hop_off(room, room.data['people'].get(w.pill), now)
        if w.ride:   # off my own vehicle first (it goes home)
            here = w.at(now)
            w.ride, w.path, w.t0 = None, [list(here), list(here)], now
            self._queue(room, w.pid, dict(k='rd', pid=w.pid, r=None, v=w.speed, p=w.path, at=round(now, 3)))
        w.back, d.pill = to, w.pid
        self._carry(room, d)
        return None

    @on('say', rate=(5, 10))
    async def say(self, conn, f):
        room, w = self._me(conn)
        p = conn.player
        frame = await self.app.chat.store_message(p, room.id, f.get('text'), SAY_LEN, 2)
        if self.hub.rooms.get(room.id) is room and p.pid in room.data['people']:
            room.send(dict(t='said', ch=room.id, pid=p.pid, id=frame['id'], text=frame['text'], at=frame['at']), sender=p)
        return None

    @on('emote', rate=(4, 4))
    async def emote(self, conn, f):
        room, w = self._me(conn)
        e = f.get('e')
        if e not in EMOTES:
            raise LiveError('bad', 'Không có biểu cảm này.')
        room.send(dict(t='emoted', pid=w.pid, e=e), sender=conn.player)
        return None

    # ---- tables ---------------------------------------------------------------------------------------------
    def _unseat(self, room, w: Walker, now: float) -> None:
        ti, si = w.seat
        w.seat = None
        tb = room.data['tables'][ti]
        if tb.seats[si] == w.pid:
            tb.seats[si] = None
        tb.votes.discard(w.pid)
        if not tb.seated():
            tb.topic, tb.until = None, 0.0
            tb.votes.clear()
        elif tb.votes and tb.votes >= tb.seated():
            tb.deal(now)
        self._queue(room, None, tb.public())

    @on('sit', rate=(6, 10))
    async def sit(self, conn, f):
        room, w = self._me(conn)
        i = f.get('table')
        tables = room.data['tables']
        if type(i) is not int or not 0 <= i < len(tables):
            raise LiveError('bad', 'Không có bàn này.')
        tb = tables[i]
        if w.seat and w.seat[0] == i:
            return None
        if None not in tb.seats:
            raise LiveError('full', 'Bàn đủ người rồi.')
        now = time.time()
        if w.seat:
            self._unseat(room, w, now)
        self._hop_off(room, w, now)
        if w.pill:   # parking to sit: the passenger gets off too
            self._hop_off(room, room.data['people'].get(w.pill), now)
        si = tb.seats.index(None)
        tb.seats[si] = w.pid
        w.seat = (i, si)
        g = GEO[room.data['place']]
        w.path, w.t0 = g.route(w.at(now), tuple(tb.pts[si])), now
        if tb.topic is None:
            tb.deal(now)
        self._queue(room, w.pid, dict(k='mv', pid=w.pid, p=w.path, at=round(now, 3)))
        self._queue(room, None, tb.public())
        return None

    @on('stand', rate=(6, 10))
    async def stand(self, conn, f):
        room, w = self._me(conn)
        if w.seat:
            self._unseat(room, w, time.time())
        return None

    @on('topic', rate=(6, 30))
    async def topic(self, conn, f):
        room, w = self._me(conn)
        if not w.seat:
            raise LiveError('bad', 'Ngồi vào bàn trước nhé.')
        tb = room.data['tables'][w.seat[0]]
        tb.votes.add(w.pid)
        if tb.votes >= tb.seated():
            tb.deal(time.time())
        self._queue(room, None, tb.public())
        return None

    # ---- a player's card, coffee for two -----------------------------------------------------------------
    def _other(self, room, p, pid):
        w = room.data['people'].get(pid) if isinstance(pid, str) else None
        if w is None or pid == p.pid or pid in p.hidden or p.pid in w.player.hidden:
            raise LiveError('gone', 'Người này vừa đi mất rồi.')
        return w

    async def _code(self, sid: str) -> str | None:
        """The player code (PCC-XXXXXX) of an account for a friend request through the game's friends API.
        An account that never opened Bạn bè / Hôn nhân gets one now, exactly as a friends search would."""
        code = await self.db.fetchval('SELECT code FROM marriage_people WHERE sid=?', (sid,))
        if code:
            return code
        for _ in range(8):
            t = time.time()
            new = 'PCC-' + ''.join(secrets.choice('23456789ABCDEFGHJKMNPQRSTUVWXYZ') for _ in range(6))
            await self.db.execute('INSERT INTO marriage_people(sid, code, created, updated) VALUES(?, ?, ?, ?) ON CONFLICT DO NOTHING',
                                  (sid, new, t, t))
            code = await self.db.fetchval('SELECT code FROM marriage_people WHERE sid=?', (sid,))
            if code:
                return code
        return None

    @on('card', rate=(20, 60))
    async def card(self, conn, f):
        room, me = self._me(conn)
        p = conn.player
        w = self._other(room, p, f.get('pid'))
        o = w.player
        if w.pid not in p.friends and self.app.chat:
            await self.app.chat.load_friends(p)
        friend = w.pid in p.friends
        code = None
        if not friend and p.account and o.account:
            try:
                code = await self._code(o.sid)
            except DbError as e:
                log('card code:', type(e).__name__)
        return dict(t='card', pid=w.pid, name=w.name, ti=w.title, lk=w.look, g=w.g, friend=friend, account=o.account,
                    code=code, cafe=room.id.startswith(PREFIX) and not GEO[room.data['place']].private, **({'st': w.st} if w.st else {}))

    @on('invite', rate=(4, 60))
    async def invite(self, conn, f):
        room, me = self._me(conn)
        p = conn.player
        if GEO[room.data['place']].private or not room.id.startswith(PREFIX):
            raise LiveError('bad', 'Ở đây chưa rủ đi cà phê được.')
        w = self._other(room, p, f.get('pid'))
        for k in [k for k, v in self.invites.items() if v['frm'] == p.pid]:
            self.invites.pop(k, None)
        if len(self.invites) >= INVITES_MAX:
            raise LiveError('busy', 'Phố đang đông, thử lại sau nhé.')
        iid = secrets.token_hex(4)
        self.invites[iid] = dict(frm=p.pid, to=w.pid, room=room.id, until=time.time() + INVITE_SECS)
        self.hub.send_many([c for c in room.conns if c.player is w.player],
                           dict(t='invited', id=iid, pid=p.pid, name=me.name, lk=me.look, g=me.g, ttl=INVITE_SECS))
        return dict(t='invite_sent', id=iid, pid=w.pid, ttl=INVITE_SECS)

    @on('invite_reply', rate=(10, 60))
    async def invite_reply(self, conn, f):
        p = conn.player
        inv = self.invites.get(f.get('id')) if isinstance(f.get('id'), str) else None
        if inv is None or inv['to'] != p.pid:
            raise LiveError('gone', 'Lời rủ này hết hạn rồi.')
        self.invites.pop(f['id'], None)
        room = self.hub.rooms.get(inv['room'])
        frm = self.hub.players.get(inv['frm'])
        if f.get('ok') is not True or room is None or frm is None or inv['frm'] not in room.data['people'] or p.pid not in room.data['people']:
            if room is not None and frm is not None:
                self.hub.send_many([c for c in room.conns if c.player is frm], dict(t='invite_no', id=f['id'], pid=p.pid))
            if f.get('ok') is True:
                raise LiveError('gone', 'Bạn ấy vừa đi mất rồi.')
            return None
        self._cafe(room, [frm, p], time.time())
        return None

    def _cafe(self, street, players: list, now: float) -> None:
        g = GEO['cafe']
        cafe = self._new_room(f'{PREFIX}cafe:{secrets.token_hex(5)}', 'cafe')
        moving = []
        for p in players:
            conns = [c for c in street.conns if c.player is p]
            old = street.data['people'][p.pid]
            self._leave_player(p)
            moving.append((p, conns, old))
        for k, (p, conns, old) in enumerate(moving):
            sx, sy = g.spots['spawn']
            w = Walker(p, old.look, old.g, old.title, g.clamp(sx + (50 if k == 0 else -50), sy), now, rk=old.rk)   # seat 0 is on the right
            w.st = old.st
            for c in conns:
                self._enter(cafe, c, w)
            tb = cafe.data['tables'][0]
            tb.seats[k] = p.pid
            w.seat = (0, k)
            w.path, w.t0 = g.route(w.at(now), tuple(tb.pts[k])), now
        cafe.data['tables'][0].deal(now)
        cafe.data['ev'], cafe.data['mvi'] = [], {}    # the snapshot below already has all of it
        for p, conns, old in moving:
            self.hub.send_many(conns, self._snapshot(cafe, p, now))

    # ---- happenings ---------------------------------------------------------------------------------------
    def _happen(self, room, now: float, kind: str | None = None) -> None:
        d = room.data
        place = d['place']
        g = GEO[place]
        kind = kind or random.choice(('vendor', 'vendor', 'lion', 'env'))
        x0, y0, x1, y1 = g.big
        y = round(random.uniform(y0 + 40, y1 - 40), 1)
        rtl = random.random() < .5
        if kind == 'vendor':
            who, text = random.choice(VENDORS[place])
            hap = dict(k='vendor', who=who, text=text, y=y, rtl=rtl, dur=10, at=round(now, 3))
        elif kind == 'lion':
            hap = dict(k='lion', y=y, rtl=rtl, dur=12, at=round(now, 3))
        else:
            x, ey = g.random_point(40)
            env = dict(id=secrets.token_hex(4), x=x, y=ey, until=now + ENVELOPE_SECS, n=random.randint(*ENVELOPE_XU), taken=None)
            d['env'] = env
            hap = dict(k='env', id=env['id'], x=x, y=ey, until=round(env['until'], 1), dur=ENVELOPE_SECS, at=round(now, 3))
        d['hap'] = dict(hap, end=now + hap['dur'])
        room.send(dict(t='happen', **hap))

    @on('grab', rate=(6, 10))
    async def grab(self, conn, f):
        room, w = self._me(conn)
        env = room.data['env']
        if env is None or env['id'] != f.get('id') or env['until'] < time.time():
            raise LiveError('gone', 'Lì xì bay mất rồi!')
        if env['taken']:
            raise LiveError('late', 'Có người nhanh tay hơn rồi!')
        env['taken'] = w.pid            # before the await: a second tap anywhere loses
        p = conn.player
        try:
            ok = await effects.grant(self.db, p.sid, 'coins', env['n'], key=f"env:{room.id}:{env['id']}",
                                     data=dict(src='envelope', place=room.data['place']), cap=ENVELOPE_CAP, cap_like='env:%')
        except BaseException:
            env['taken'] = None
            raise
        if not ok:
            env['taken'] = None
            raise LiveError('cap', 'Hôm nay bạn nhận đủ lì xì rồi, để phần người khác nhé!')
        if room.data['env'] is env:
            room.data['env'] = None
            if room.data['hap'] and room.data['hap'].get('id') == env['id']:
                room.data['hap'] = None
        room.send(dict(t='happen_end', id=env['id'], pid=w.pid, name=w.name, n=env['n']))
        return dict(t='grabbed', id=env['id'], n=env['n'])

    # ---- every second ------------------------------------------------------------------------------------
    async def tick(self, now: float):
        for room in self.rooms():
            d = room.data
            for tb in d['tables']:
                if tb.topic and now >= tb.until and tb.seated():
                    tb.deal(now)
                    self._queue(room, None, tb.public())
            env = d['env']
            if env and now >= env['until'] and not env['taken']:
                d['env'] = None
                room.send(dict(t='happen_end', id=env['id']))
            if now >= d['next_hap']:
                d['next_hap'] = now + HAPPEN_GAP + random.uniform(0, HAPPEN_JITTER)
                self._happen(room, now)
            self._check_blocks(room)
        for k, inv in list(self.invites.items()):
            if now >= inv['until']:
                self.invites.pop(k, None)
                room, frm = self.hub.rooms.get(inv['room']), self.hub.players.get(inv['frm'])
                if room is not None and frm is not None:
                    self.hub.send_many([c for c in room.conns if c.player is frm], dict(t='invite_no', id=k, pid=inv['to']))

    def _check_blocks(self, room) -> None:
        """A block made during the stroll: from now on the two do not see each other."""
        d = room.data
        people = d['people']
        if len(people) < 2:
            return
        for pid, w in people.items():
            for q in w.player.hidden & people.keys():
                pair = frozenset((pid, q))
                if pair in d['hidden_seen']:
                    continue
                d['hidden_seen'].add(pair)
                for a, b in ((pid, q), (q, pid)):
                    pa = people.get(a)
                    if pa is not None:
                        self.hub.send_many([c for c in room.conns if c.player is pa.player], dict(t='walk', ev=[dict(k='out', pid=b)], at=round(time.time(), 3)))

    async def on_close(self, conn):
        rid = conn.ext.pop('walk', None)
        if not rid:
            return
        p = conn.player
        room = self.hub.rooms.get(rid)
        if room is not None and not any(c.player is p for c in room.conns):
            self._remove_walker(room, p.pid)
        if p.ext.get('walk') == rid and (room is None or not any(c.player is p for c in room.conns)):
            p.ext.pop('walk', None)

    def stats(self) -> dict:
        rooms = self.hub.rooms_with_prefix(PREFIX)
        return dict(walk_rooms=len(rooms), walkers=sum(len(r.data['people']) for r in rooms), walk_flushes=self.flushes,
                    invites=len(self.invites))
