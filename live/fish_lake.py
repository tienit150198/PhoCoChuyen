"""🎣 Hồ câu đông vui (owner 24/10: "map câu cá nhiều người vào vẫn thấy được nhé, thấy nhân vật như ở ngoài luôn … để ai
câu lên con gì mình nhìn được ấy"; then "hồ k tối đa lượng người mỗi bến nha, cho k giới hạn đi"): everyone fishing at the
same spot (🏞️ Hồ phố, 🏞️ Sông, ⚓ Bến cảng, or the 🏝️ island of one trip) shares one lake with no cap, drawn as their real
characters (look, wings, the fish carried, the name with its 🎨 colour / frame of the week and its 🏅 titles), each on a
place along a long boardwalk (`s`, its slot; the client lays slots out alternately right and left of the middle, pos()).

Only cosmetic and public things go through here; the save never changes and nothing here is read on a hint:
* fl_in {spot, trip?, look, g, fh?, rod?}  [fl_room {room, spot, me, s, n, people, far, feed}]
  `people`: the FULL whole entries nearest to me; `far`: the others as {pid, name, s} (at most FAR_MAX, nearest first)
  so a crowd of hundreds stays one small frame; `n` everyone there. The island needs the trip (island_trips.ACCESS_SQL).
* fl_view {c}  [fl_near {room, c, people}]  where my view is now (a pos): the whole entries around it, and the hints I get.
* fl_act {k, d?, x?, rod?}  the cast (k 'cast': its distance `d` clamped to the rod's reach, `x` its sideways offset),
  'bite', 'reel', 'lost', 'idle': cosmetic hints, rate limited, sent only to viewers looking within NEAR of the caster.
* fl_card {pid}  [fl_card {pid, name, today?, best?, dex?}]  a fisher's mini card: today's best seen here (memory), the
  all-time heaviest (fish_best 'all') and the 📖 Sổ cá count (fish_dex), the last two only when they show on the boards.
* fl_say {text}  a bubble over my head for the people near me: the chat's store_message (filters, mutes, kept like all
  chat) in the channel 'fl:<spot>' (chat.route: delete, report, admin hide).
* fl_out {}  [fl_left {why: out}]
Server pushes: fl {room, ev: [{k: in | out | act (a: the hint's k) | catch | said, ...}]}, fl_left {why: other | gone}.

🐟 The catch is never a client's claim: the game server announces a kept fish (or the junk pulled up) after jr_fish_land
commits (game/fishing.py command_commit → NOTIFY {op: 'fish', sid, spot, s, g, r} / {op: 'fish', sid, junk}); it goes
to everyone at that lake with a line in the room's feed (the last FEED catches, memory only). An older client ignores
all of it; with the service off the lake is the single player's, as before.
"""
from __future__ import annotations

import math
import re
import time
from collections import deque

from game import fishing_content as C
from game.leaderboard import GUEST_DEFAULT

from .auth import pid_of
from . import bangs, fish_carry, honours, styles, wings
from .db import Error as DbError, log
from .limits import LRU
from .protocol import Feature, LiveError, on
from .street import clean_look

PREFIX = 'fl:'
PUBLIC = ('ho', 'song', 'bien')
TRIP_RE = re.compile(r'[0-9a-f]{16}')
SID_RE = re.compile(r'[0-9a-f]{64}')
FULL = 30            # whole entries in a snapshot / a view answer
FAR_MAX = 300        # compact entries in a snapshot
NEAR = 12            # pos units: a hint, a bubble or a whole entry reaches viewers looking this close
FEED = 20
SAY_LEN = 120
ACTS = frozenset(('cast', 'bite', 'reel', 'lost', 'idle'))
CARD_TTL = 60.0
CHECK_EVERY = 30.0   # an island lake: the trip is read again this often
POS_MAX = 100_000
REACH = (min(r['reach'][0] for r in C.RODS), max(r['reach'][1] for r in C.RODS))


def pos(s: int) -> int:
    """Where slot `s` stands along the boardwalk: 0 the middle, then 1, -1, 2, -2, … (public/js/v4/fish-lake-layout.js)."""
    return 0 if s <= 0 else (s + 1) // 2 if s % 2 else -(s // 2)


def room_id(spot: str, trip: str = '') -> str:
    return PREFIX + (f'dao:{trip}' if spot == 'dao' else spot)


def clean_act(f: dict, rod: str) -> dict:
    """A hint {k, d?, x?, rod?} from a client, or LiveError: the distance inside the rod's reach, x within ±1."""
    k = f.get('k')
    if not isinstance(k, str) or k not in ACTS:
        raise LiveError('bad', 'Không hiểu động tác này.')
    out = dict(k=k)
    r = f.get('rod')
    if r is not None:
        if not isinstance(r, str) or r not in C.ROD:
            raise LiveError('bad', 'Cần câu không hợp lệ.')
        out['rod'] = r
        rod = r
    if k == 'cast':
        d, x = f.get('d'), f.get('x', 0)
        if type(d) not in (int, float) or not math.isfinite(d) or type(x) not in (int, float) or not math.isfinite(x):
            raise LiveError('bad', 'Cú quăng không hợp lệ.')
        lo, hi = C.ROD[rod]['reach'] if rod in C.ROD else REACH
        out['d'] = round(min(hi, max(lo, float(d))), 1)
        out['x'] = round(min(1.0, max(-1.0, float(x))), 3)
    return out


class FishLakeFeature(Feature):
    name, flag = 'fish_lake', 'fish'

    def __init__(self, app):
        super().__init__(app)
        self.today = LRU(20000)   # pid -> (vn day, {s, g, r}): the heaviest fish seen landed today
        self.cards = LRU(5000)    # pid -> (monotonic, best | None, dex | None, visible)
        self.check_at = 0.0

    async def start(self):
        if self.app.chat:
            self.app.chat.route(PREFIX, audience=self._audience, can_read=self._can_read)

    def _audience(self, ch: str) -> list:
        r = self.hub.rooms.get(ch)
        return [r] if r is not None else []

    def _can_read(self, player, ch: str) -> bool:
        return ch in player.ext.get('fl_seen', ())

    # ---- the room -----------------------------------------------------------------------------------------------
    def _empty(self, room):
        self.hub.drop_room(room.id)

    def _current(self, conn):
        rid = conn.ext.get('fl')
        room = self.hub.rooms.get(rid) if rid else None
        if room is None or conn.player.ext.get('fl_conn') is not conn or conn not in room.conns:
            return None
        return room

    def _need(self, conn):
        room = self._current(conn)
        if room is None:
            raise LiveError('no_lake', 'Bạn chưa ở hồ câu.')
        return room

    def _detach(self, conn, why=None):
        rid = conn.ext.pop('fl', None)
        conn.ext.pop('fl_c', None)
        room = self.hub.rooms.get(rid) if rid else None
        p = conn.player
        if p.ext.get('fl_conn') is conn:
            p.ext.pop('fl_conn', None)
            if room is not None:
                person = room.data['people'].pop(p.pid, None)
                if person is not None:
                    room.data['slots'].pop(person['s'], None)
                    room.send(dict(t='fl', room=room.id, ev=[dict(k='out', pid=p.pid)]), skip=conn)
        if room is not None:
            room.remove(conn)
        if why:
            self.hub.send(conn, dict(t='fl_left', why=why))

    @staticmethod
    def _slot(room, pid: str) -> int:
        slots, was = room.data['slots'], room.data['was']
        s = was.get(pid)
        if s is not None and s not in slots:   # back after a reconnect: the same place when it is still free
            return s
        s = 0
        while s in slots:
            s += 1
        return s

    def _focus(self, conn, room) -> float:
        c = conn.ext.get('fl_c')
        if c is None:
            me = room.data['people'].get(conn.player.pid)
            c = pos(me['s']) if me else 0
        return c

    def _visible(self, a, b) -> bool:
        return b.pid not in a.hidden and a.pid not in b.hidden

    def _around(self, room, viewer, c: float, n: int, skip_pid=None) -> list:
        """The people nearest to `c` that `viewer` may see (not themselves), nearest first."""
        players = {x.player.pid: x.player for x in room.conns}
        out = [x for pid, x in room.data['people'].items()
               if pid != skip_pid and pid in players and self._visible(viewer, players[pid])]
        out.sort(key=lambda x: (abs(pos(x['s']) - c), x['s']))
        return out[:n]

    @staticmethod
    def _compact(x: dict) -> dict:
        return dict(pid=x['pid'], name=x['name'], s=x['s'])

    def _near_conns(self, room, at: float, sender, skip=None) -> tuple[list, list]:
        """(the sockets looking within NEAR of `at`, the others), both without `skip` and anyone hidden either way."""
        near, far = [], []
        for c in room.conns:
            if c is skip or not c.ready or not self._visible(sender, c.player):
                continue
            (near if abs(self._focus(c, room) - at) <= NEAR else far).append(c)
        return near, far

    async def _access(self, sid: str, trip: str) -> bool:
        isl = self.app.by_name.get('island')
        if isl is None:
            return False
        _, kind = await isl._access(sid, trip)
        return bool(kind)

    # ---- frames ---------------------------------------------------------------------------------------------------
    @on('fl_in', rate=(20, 60))
    async def fl_in(self, conn, f):
        spot, trip = f.get('spot'), f.get('trip') or ''
        if spot == 'dao':
            if not isinstance(trip, str) or not TRIP_RE.fullmatch(trip):
                raise LiveError('bad', 'Chuyến đi không hợp lệ.')
        elif not isinstance(spot, str) or spot not in PUBLIC:
            raise LiveError('bad', 'Chỗ câu không hợp lệ.')
        else:
            trip = ''
        look, gender = clean_look(f.get('look'), f.get('g'))
        rod = f.get('rod') if isinstance(f.get('rod'), str) and f.get('rod') in C.ROD else 'tre'
        p = conn.player
        ticket = object()
        p.ext['fl_join'] = ticket
        fh = await fish_carry.keep(self.db, p, fish_carry.clean(f.get('fh')))   # 🎣 the fish carried (live/fish_carry.py)
        if trip and not await self._access(p.sid, trip):
            raise LiveError('no_island', 'Bạn không ở trên hòn đảo này.')
        wg = await wings.of_app(self.app).one(p)          # 🪽 read from the game's tables, never from the frame
        st = await styles.of_app(self.app).one(p.pid)     # 🎨 name colour / frame of the week
        tt = await honours.of_app(self.app).one(p.pid)    # 🏅 every honour title held now
        bg = await bangs.of_app(self.app).one(p.pid)      # ⚔️ the bang tag
        if p.ext.get('fl_join') is not ticket or conn.closing or conn not in p.conns:
            return None
        old = p.ext.get('fl_conn')
        if old is not None:
            self._detach(old, 'other' if old is not conn else None)
        rid = room_id(spot, trip)
        room = self.hub.room(rid, on_empty=self._empty)
        if not room.data:
            room.data.update(spot=spot, trip=trip, people={}, slots={}, was={}, feed=deque(maxlen=FEED))
        room.add(conn)
        s = self._slot(room, p.pid)
        room.data['slots'][s] = p.pid
        was = room.data['was']
        was[p.pid] = s
        if len(was) > 4 * FAR_MAX:
            for k in list(was)[:len(was) - 2 * FAR_MAX]:
                was.pop(k, None)
        person = dict(pid=p.pid, name=p.name or 'Mây', s=s, lk=look, g=gender, rod=rod)
        for k, v in (('fc', p.fc), ('fh', fh), ('wg', wg), ('st', st or None), ('tt', tt or None), ('bg', bg)):
            if v:
                person[k] = v
        room.data['people'][p.pid] = person
        conn.ext['fl'] = rid
        conn.ext['fl_c'] = pos(s)
        p.ext['fl_conn'] = conn
        seen = p.ext.setdefault('fl_seen', set())
        if len(seen) > 32:
            seen.clear()
        seen.add(rid)
        near, far = self._near_conns(room, pos(s), p, skip=conn)
        self.hub.send_many(near, dict(t='fl', room=rid, ev=[dict(k='in', **person)]))
        self.hub.send_many(far, dict(t='fl', room=rid, ev=[dict(k='in', **self._compact(person))]))
        whole = self._around(room, p, pos(s), FULL, skip_pid=p.pid)
        got = {x['pid'] for x in whole}
        rest = [self._compact(x) for x in self._around(room, p, pos(s), FULL + FAR_MAX, skip_pid=p.pid) if x['pid'] not in got][:FAR_MAX]
        return dict(t='fl_room', room=rid, spot=spot, me=p.pid, s=s, n=len(room.data['people']), people=whole, far=rest,
                    feed=[x for x in room.data['feed'] if self._visible_pid(p, x['pid'])])

    def _visible_pid(self, viewer, pid: str) -> bool:
        other = self.hub.players.get(pid)
        return pid not in viewer.hidden and not (other and viewer.pid in other.hidden)

    @on('fl_out', rate=(20, 60))
    async def fl_out(self, conn, f):
        conn.player.ext.pop('fl_join', None)
        self._detach(conn)
        return dict(t='fl_left', why='out')

    @on('fl_view', rate=(6, 3.0))
    async def fl_view(self, conn, f):
        c = f.get('c')
        if type(c) not in (int, float) or not math.isfinite(c):
            raise LiveError('bad', 'Vị trí không hợp lệ.')
        room = self._need(conn)
        c = round(min(POS_MAX, max(-POS_MAX, float(c))), 2)
        conn.ext['fl_c'] = c
        return dict(t='fl_near', room=room.id, c=c, people=self._around(room, conn.player, c, FULL, skip_pid=conn.player.pid))

    @on('fl_act', rate=(16, 10.0))
    async def fl_act(self, conn, f):
        room = self._need(conn)
        p = conn.player
        person = room.data['people'].get(p.pid)
        if person is None:
            raise LiveError('no_lake', 'Bạn chưa ở hồ câu.')
        a = clean_act(f, person['rod'])
        if 'rod' in a:
            person['rod'] = a['rod']
        if a['k'] in ('idle', 'lost'):
            person.pop('a', None)
        else:
            person['a'] = {k: v for k, v in a.items() if k != 'rod'}
        near, _ = self._near_conns(room, pos(person['s']), p, skip=conn)
        ev = dict(k='act', pid=p.pid, a=a['k'], **{k: v for k, v in a.items() if k != 'k'})
        self.hub.send_many(near, dict(t='fl', room=room.id, ev=[ev]))

    @on('fl_card', rate=(10, 10.0))
    async def fl_card(self, conn, f):
        pid = f.get('pid')
        room = self._need(conn)
        x = room.data['people'].get(pid) if isinstance(pid, str) else None
        if x is None or not self._visible_pid(conn.player, pid):
            raise LiveError('gone', 'Người này không còn ở hồ.')
        out = dict(t='fl_card', pid=pid, name=x['name'])
        day = vn_day()
        hit = self.today.get(pid)
        if hit and hit[0] == day:
            out['today'] = dict(hit[1])
        other = self.hub.players.get(pid)
        from . import notes
        nt = await notes.of_app(self.app).one(conn.player, pid)   # 💭 their note (live/notes.py)
        if nt:
            out['nt'] = nt
        best, dex, vis = await self._card(other) if other else (None, None, False)
        if vis:
            if best:
                out['best'] = best
            if dex:
                out['dex'] = dex
        return out

    async def _card(self, player) -> tuple:
        mono = time.monotonic()
        hit = self.cards.get(player.pid)
        if hit and mono - hit[0] < CARD_TTL:
            return hit[1:]
        sid = player.sid
        try:
            row = await self.db.fetchrow(
                'SELECT (SELECT n FROM fish_dex WHERE sid=?) AS n, (SELECT uid FROM accounts WHERE sid=?) AS uid, '
                '(SELECT name FROM leaderboard_players WHERE sid=?) AS gname, (SELECT show FROM leaderboard_players WHERE sid=?) AS show',
                (sid, sid, sid, sid))
            b = await self.db.fetchrow("SELECT sp, g, r FROM fish_best WHERE sid=? AND week='all'", (sid,))
        except DbError as e:   # a busy database or one from before the tables: the card without them
            log('fish card:', type(e).__name__)
            return None, None, False
        account = row is not None and row['uid'] is not None
        show = row['show'] if row is not None else None
        vis = bool(show if show is not None else (1 if account else (GUEST_DEFAULT if row is not None and row['gname'] else 0)))
        best = dict(s=b['sp'], g=int(b['g']), r=int(b['r'])) if b and b['sp'] in C.SPECIES else None
        dex = int(row['n']) if row is not None and row['n'] else None
        self.cards.put(player.pid, (mono, best, dex, vis))
        return best, dex, vis

    @on('fl_say', rate=(5, 10.0))
    async def fl_say(self, conn, f):
        room = self._need(conn)
        p = conn.player
        if not self.app.chat:
            raise LiveError('off', 'Trò chuyện đang tắt.')
        frame = await self.app.chat.store_message(p, room.id, f.get('text'), SAY_LEN, 2)
        person = room.data['people'].get(p.pid) if self.hub.rooms.get(room.id) is room else None
        if person is not None:
            near, _ = self._near_conns(room, pos(person['s']), p)
            self.hub.send_many(near, dict(t='fl', room=room.id, ev=[dict(k='said', pid=p.pid, id=frame['id'], text=frame['text'])]))

    # ---- 🐟 the catch: only from the game server, after jr_fish_land committed ------------------------------------
    async def on_notify(self, event):
        if not self.enabled() or event.get('op') != 'fish':
            return
        sid = event.get('sid')
        if not isinstance(sid, str) or not SID_RE.fullmatch(sid):
            return
        player = self.hub.players.get(pid_of(sid))
        conn = player.ext.get('fl_conn') if player is not None and player.sid == sid else None
        room = self._current(conn) if conn is not None else None
        if room is None:
            return
        junk = event.get('junk')
        if junk is not None:
            if not any(j[0] == junk for j in C.JUNK):
                return
            ev = dict(k='catch', pid=player.pid, junk=junk)
        else:
            sp, g, spot = event.get('s'), event.get('g'), event.get('spot')
            info = C.SPECIES.get(sp) if isinstance(sp, str) else None
            if info is None or type(g) is not int or g <= 0 or spot != room.data['spot']:
                return
            ev = dict(k='catch', pid=player.pid, s=sp, g=g, r=info['r'])
            line = dict(pid=player.pid, name=player.name or 'Mây', s=sp, g=g, r=info['r'], at=round(time.time(), 1))
            room.data['feed'].append(line)
            day = vn_day()
            hit = self.today.get(player.pid)
            if not hit or hit[0] != day or hit[1]['g'] < g:
                self.today.put(player.pid, (day, dict(s=sp, g=g, r=info['r'])))
            self.cards.pop(player.pid, None)
            ev['feed'] = line
        person = room.data['people'].get(player.pid)
        if person is not None:
            person.pop('a', None)
        room.send(dict(t='fl', room=room.id, ev=[ev]), sender=player)

    # ---- lifecycle ------------------------------------------------------------------------------------------------
    async def on_close(self, conn):
        self._detach(conn)

    async def tick(self, now):
        if now < self.check_at:
            return
        self.check_at = now + CHECK_EVERY
        for room in list(self.hub.rooms_with_prefix(PREFIX + 'dao:')):
            for conn in list(room.conns):
                try:
                    ok = await self._access(conn.player.sid, room.data['trip'])
                except DbError:
                    continue
                if not ok and self._current(conn) is room:
                    self._detach(conn, 'gone')


def vn_day() -> int:
    """Today in Vietnam (UTC+7) as a day number: 'today's best' turns over at local midnight."""
    return int((time.time() + 7 * 3600) // 86400)
