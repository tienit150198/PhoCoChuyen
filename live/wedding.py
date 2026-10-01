"""💍 Live weddings (switch LIVE_WEDDING; design docs/superpowers/specs/2026-10-01-live-wedding-design.md).

A couple who books their wedding at a real date and time (game/marriage.py → game/wedding_live.py `wedding_parties`)
throws a party anyone online can attend. This feature reads the booked parties, opens a room `wed:<wedding id>` 10
minutes before the start and closes it 30 minutes after, and pays the rewards through live/effects.grant (rows the
game server pays on load, game/live_effects.py). The numbers live in game/wedding_live.py (owner-approved).

The room is the strolling machinery of live/street.py (place 'wedding': a flower gate, the tent, tables): avatars with
name tags, moves, speech bubbles (stored and filtered like chat, channel = the room id), emotes, the tables' topic
cards. At most VISIBLE (60) avatars: later guests watch from outside the gate ("đông quá") and are still counted.

Attendance (memory, one second per tick; written to `wedding_guests` when a guest reaches 5 minutes):
* one account counts once (by player, whatever the tabs); the couple are never their own guests;
* a counted guest is a named save at least a day old (stat_births / first seen, as for Cả phố);
* every 5 minutes present: +15 xu, at most 4 per wedding, and only from 2 weddings a day per player; plus closeness
  with each spouse once per wedding;
* at the end each spouse gets 30 xu per counted guest (up to 50), +100 at 10 guests, +250 and the title
  "Đám cưới đông vui 🎉" at 20, with the private congratulation card.

Also here (one process, so once): the reminder 30 minutes before (the couple's friends: inbox + web push), the
weekly race settle ("Khách mời của tuần": #1 🥇 Khách quý của phố 300 xu, #2-#3 🎊 Ăn cưới chuyên nghiệp 150 xu;
ties to whoever reached the count first), and the race titles worn on name tags the whole next week.
Every reward has a fixed key (paid once); settles and reminders are guarded in the database (done once).

Frames (client → server; replies in brackets)
  wed_list {}                         [wed_list {parties: [{id, a, b, at, end, open, n, mine}], now}]
  wed_in {id, look, g, title}         [walk_room {..., wed: {id, a, b, pids, at, end, overflow, photos}}]
  wed_photo {}                        [the room: wed_photo {n, pid, name, at}: the taker's screen is uploaded to
                                       POST /api/wedding/photo at `at`]
  (walk_out, move, say, emote, sit, stand, topic, card: live/street.py)
Server pushes: wed_start {id}, wed_end {id, n}, wed_xu {n, steps}, wed_paid {xu}, walk_left {why: 'wed_end'}.
"""
from __future__ import annotations

import asyncio
import json
import random
import time

from game import wedding_live as WL

from . import effects
from .auth import clean_name, pid_of
from .db import Error as DbError, log
from .protocol import Feature, LiveError, on
from .street import GEO, Walker, clean_look

PREFIX = 'wed:'
REFRESH = 30.0              # seconds between two reads of the booked parties (and the reminder / settle checks)
PARTIES_MAX = 500
WATCHERS_MAX = 300          # guests watching from outside the gate, per party
PHOTO_GAP = 45.0            # seconds between two group photos of one party
TASKS_MAX = 2000
CLOSE_AFTER = 120.0         # the room stays this long after the end (goodbyes), then closes


class Att:
    """One player's presence at one party."""
    __slots__ = ('sid', 'pid', 'secs', 'steps', 'paid', 'reward', 'ok', 'lock')

    def __init__(self, sid: str, pid: str, ok: bool):
        self.sid, self.pid, self.ok = sid, pid, ok
        self.secs, self.steps, self.paid, self.reward = 0.0, 0, 0, None
        self.lock = asyncio.Lock()


class WeddingFeature(Feature):
    name, flag = 'wedding', 'wedding'

    def __init__(self, app):
        super().__init__(app)
        self.parties: dict = {}     # wedding id -> party dict
        self.att: dict = {}         # wedding id -> {pid: Att}
        self.names: dict = {}       # sid -> display name (bounded by the parties)
        self.race: dict = {}        # pid -> race title text worn this week
        self.race_week = None
        self.next_refresh = 0.0
        self.refreshing = None      # the schedule read in flight (others wait for it)
        self.last = 0.0
        self.tasks: set = set()

    @property
    def street(self):
        return self.app.by_name['street']

    async def start(self):
        if self.app.chat:
            self.app.chat.route(PREFIX, audience=self.street._audience, can_read=self.street._can_read)
        self.street.leave_hooks.append(self._leave_watch)

    def race_title(self, pid: str) -> str | None:
        return self.race.get(pid)

    def stats(self) -> dict:
        return dict(parties=len(self.parties), watching=sum(len(self.att.get(w, {})) for w in self.parties))

    # ---- the schedule ---------------------------------------------------------------------------------------
    async def _name(self, sid: str) -> str:
        n = self.names.get(sid)
        if n is None:
            r = await self.db.fetchrow('SELECT (SELECT display FROM accounts WHERE sid=?) AS d, (SELECT name FROM leaderboard_players WHERE sid=?) AS g', (sid, sid))
            n = clean_name((r or {}).get('d')) or clean_name((r or {}).get('g')) or 'Một người chơi'
            self.names[sid] = n
        return n

    async def refresh(self, now: float) -> None:
        """Booked parties from two days ago (an unsettled one after a restart) to 15 days ahead; the reminders; the
        settle of parties that ended; the weekly race."""
        rows = await self.db.fetch("SELECT wedding, couple, a, b, at, reminded FROM wedding_parties WHERE status='booked' AND at>? AND at<? "
                                   'ORDER BY at LIMIT ?', (now - 2 * 86400, now + 15 * 86400, PARTIES_MAX))
        keep = {}
        for r in rows:
            wid = int(r['wedding'])
            p = self.parties.get(wid) or dict(id=wid, couple=int(r['couple']), a=r['a'], b=r['b'], at=float(r['at']), started=False, ending=False,
                                              closed=False, photos=None, photo_at=0.0, n=0)
            p['at'] = float(r['at'])
            p['na'], p['nb'] = await self._name(r['a']), await self._name(r['b'])
            p['pa'], p['pb'] = pid_of(r['a']), pid_of(r['b'])
            keep[wid] = p
            if r['reminded'] is None and p['at'] - WL.REMIND_BEFORE <= now < p['at']:
                await self._remind(p, now)
        for wid, p in self.parties.items():   # ended or settled meanwhile: kept until its room closes
            if wid not in keep and not p.get('closed'):
                keep[wid] = p
        self.parties = keep
        live_sids = {p[k] for p in keep.values() for k in ('a', 'b')}
        if len(self.names) > 4 * PARTIES_MAX:
            self.names = {k: v for k, v in self.names.items() if k in live_sids}
        await self._race(now)

    async def _remind(self, p: dict, now: float) -> None:
        """30 minutes before: the couple's friends get an inbox line and a web push (once, guarded in the database)."""
        if await self.db.execute('UPDATE wedding_parties SET reminded=? WHERE wedding=? AND reminded IS NULL', (now, p['id'])) != 1:
            return
        rows = await self.db.fetch('SELECT DISTINCT friend FROM friends WHERE sid IN (?, ?) AND friend NOT IN (?, ?) LIMIT 400', (p['a'], p['b'], p['a'], p['b']))
        text = f'💍 30 phút nữa là đám cưới của {p["na"]} và {p["nb"]}. Mở Khu phố › Lịch cưới để vào dự nhé!'
        for r in rows:
            sid = r['friend']
            try:
                await self.db.execute('UPDATE marriage_people SET notice=?, notice_at=? WHERE sid=?', (text, now, sid))
                await _push(self.db, sid, 'wedding', f'{p["na"]} và {p["nb"]} cưới lúc {WL.fmt_at(p["at"])[-5:]}. Vào dự cho vui nhé!')
            except DbError as e:
                log('wedding remind', type(e).__name__)

    # ---- the weekly race ------------------------------------------------------------------------------------
    async def _race(self, now: float) -> None:
        prev = WL.vn_week(WL.week_start(now) - 3600)
        if self.race_week == prev:
            return
        row = await self.db.fetchrow('SELECT top FROM wedding_race WHERE week=?', (prev,))
        if row is None:
            await self.settle_week(prev)
            row = await self.db.fetchrow('SELECT top FROM wedding_race WHERE week=?', (prev,))
        top = json.loads(row['top']) if row else []
        self.race = {w['pid']: WL.TITLE_NAMES[w['title']] for w in top if w.get('title') in WL.TITLE_NAMES}
        self.race_week = prev

    async def settle_week(self, week: str) -> list:
        return await settle_week(self.db, week)

    # ---- rooms ----------------------------------------------------------------------------------------------
    def _room(self, p: dict):
        rid = f'{PREFIX}{p["id"]}'
        room = self.hub.rooms.get(rid)
        if room is None:
            room = self.street._new_room(rid, 'wedding', cap=0, on_empty=self._empty)
            room.data.update(wid=p['id'], watch={})
        return room

    def _empty(self, room) -> None:
        self.street._empty(room)

    def _open(self, p: dict, now: float) -> bool:
        return p['at'] - WL.OPEN_BEFORE <= now < p['at'] + WL.PARTY_SECS

    def _info(self, p: dict, room, overflow: bool) -> dict:
        n = len(room.data['people']) + len(room.data['watch'])
        return dict(id=p['id'], a=p['na'], b=p['nb'], pids=[p['pa'], p['pb']], at=p['at'], end=p['at'] + WL.PARTY_SECS, n=n,
                    overflow=overflow, photos=p['photos'] or 0, photos_max=WL.PHOTOS_MAX, visible=WL.VISIBLE)

    @on('wed_list', rate=(10, 10))
    async def wed_list(self, conn, f):
        now = time.time()
        if not self.parties and now >= self.next_refresh - REFRESH + 5:
            await self._refresh_now(now)
        me = conn.player.pid
        out = []
        for p in sorted(self.parties.values(), key=lambda x: x['at']):
            if p['at'] + WL.PARTY_SECS < now or p.get('closed'):
                continue
            room = self.hub.rooms.get(f'{PREFIX}{p["id"]}')
            n = len(room.data['people']) + len(room.data['watch']) if room is not None else 0
            hidden = p['pa'] in conn.player.hidden or p['pb'] in conn.player.hidden
            if hidden:
                continue
            out.append(dict(id=p['id'], a=p['na'], b=p['nb'], at=p['at'], end=p['at'] + WL.PARTY_SECS, open=self._open(p, now), n=n,
                            mine=me in (p['pa'], p['pb'])))
            if len(out) >= 50:
                break
        return dict(t='wed_list', parties=out, now=round(now, 3), open_before=WL.OPEN_BEFORE)

    async def _refresh_now(self, now: float) -> None:
        """Read the schedule now, or wait for the read already in flight (a crowd joining at once reads it once)."""
        if self.refreshing is not None:
            await asyncio.shield(self.refreshing)
            return
        self.refreshing = asyncio.ensure_future(self.refresh(now))
        try:
            await asyncio.shield(self.refreshing)
        finally:
            self.refreshing = None
            self.next_refresh = now + REFRESH

    @on('wed_in', rate=(8, 60))
    async def wed_in(self, conn, f):
        wid = f.get('id')
        now = time.time()
        if type(wid) is int and wid not in self.parties:
            await self._refresh_now(now)
        p = self.parties.get(wid) if type(wid) is int else None
        if p is None or p.get('closed'):
            raise LiveError('gone', 'Không tìm thấy đám cưới này.')
        if now < p['at'] - WL.OPEN_BEFORE:
            raise LiveError('early', f'Tiệc mở lúc {WL.fmt_at(p["at"] - WL.OPEN_BEFORE)[-5:]}, quay lại nhé!')
        if now >= p['at'] + WL.PARTY_SECS:
            raise LiveError('over', 'Tiệc đã tàn rồi.')
        pl = conn.player
        if p['pa'] in pl.hidden or p['pb'] in pl.hidden:
            raise LiveError('gone', 'Không tìm thấy đám cưới này.')
        look, g = clean_look(f.get('look'), f.get('g'))
        await self.street._ensure_loaded(pl)
        self.street._leave_player(pl, 'other', keep=conn)
        self._leave_watch(pl)
        room = self._room(p)
        couple = pl.pid in (p['pa'], p['pb'])
        geo = GEO['wedding']
        if couple or len(room.data['people']) < WL.VISIBLE:
            if couple:
                x, y = geo.spots['stage']
                at = geo.clamp(x + (-55 if pl.pid == p['pa'] else 55), y + 20)   # side by side, their name tags apart
                title = '💍 Chú rể' if g == 'male' else '💍 Cô dâu' if g == 'female' else '💍 Cô dâu chú rể'
            else:
                x, y = geo.spots['spawn']
                at = geo.clamp(x + random.uniform(-90, 90), y + random.uniform(-30, 30))
                title = self.street.title_of(pl, f.get('title'))
            self.street._enter(room, conn, Walker(pl, look, g, title, at, now))
            overflow = False
        else:
            if len(room.data['watch']) >= WATCHERS_MAX:
                raise LiveError('full', 'Đông quá, cổng đã kín người. Thử lại sau ít phút nhé.')
            room.add(conn)
            room.data['watch'][pl.pid] = pl
            pl.ext['wed_watch'] = room.id
            conn.ext['wed_watch'] = room.id
            overflow = True
        if p['photos'] is None:
            p['photos'] = int(await self.db.fetchval('SELECT COUNT(*) FROM wedding_photos WHERE wedding=?', (p['id'],)) or 0)
        snap = self.street._snapshot(room, pl, now)
        snap['wed'] = self._info(p, room, overflow)
        return snap

    def _leave_watch(self, player) -> None:
        rid = player.ext.pop('wed_watch', None)
        room = self.hub.rooms.get(rid) if rid else None
        if room is None:
            return
        room.data['watch'].pop(player.pid, None)
        for c in [c for c in room.conns if c.player is player and c.ext.get('wed_watch') == rid]:
            c.ext.pop('wed_watch', None)
            room.remove(c)

    async def on_close(self, conn):
        rid = conn.ext.pop('wed_watch', None)
        if not rid:
            return
        room = self.hub.rooms.get(rid)
        p = conn.player
        if room is not None and not any(c.player is p for c in room.conns):
            room.data['watch'].pop(p.pid, None)
            if p.ext.get('wed_watch') == rid:
                p.ext.pop('wed_watch', None)

    # ---- the group photo ------------------------------------------------------------------------------------
    @on('wed_photo', rate=(3, 60))
    async def wed_photo(self, conn, f):
        room, w = self.street._me(conn)
        wid = room.data.get('wid')
        p = self.parties.get(wid)
        if p is None:
            raise LiveError('bad', 'Chỉ chụp ảnh chung ở đám cưới.')
        now = time.time()
        if now - p['photo_at'] < PHOTO_GAP:
            raise LiveError('slow', 'Vừa chụp xong, chờ chút nhé.', wait=round(PHOTO_GAP - (now - p['photo_at']), 1))
        if (p['photos'] or 0) >= WL.PHOTOS_MAX:
            raise LiveError('full', f'Đã chụp đủ {WL.PHOTOS_MAX} tấm rồi.')
        p['photo_at'] = now
        n = (p['photos'] or 0) + 1
        if await self.db.execute('INSERT INTO wedding_photos(wedding, n, sid, at) VALUES(?, ?, ?, ?) ON CONFLICT(wedding, n) DO NOTHING',
                                 (wid, n, conn.player.sid, now)) != 1:
            p['photos'] = int(await self.db.fetchval('SELECT COUNT(*) FROM wedding_photos WHERE wedding=?', (wid,)) or 0)
            raise LiveError('slow', 'Có người vừa bấm chụp, cười lên nào!')
        p['photos'] = n
        room.send(dict(t='wed_photo', id=wid, n=n, pid=w.pid, name=w.name, at=round(now + 3, 3)))
        return None

    # ---- every second: attendance, start, end ---------------------------------------------------------------
    async def tick(self, now: float):
        dt = min(5.0, max(0.0, now - self.last)) if self.last else 1.0   # a clock that steps back adds nothing
        self.last = max(self.last, now)
        if now >= self.next_refresh and self.refreshing is None:
            self.next_refresh = now + REFRESH
            self.spawn(self._refresh_now(now))
        for p in list(self.parties.values()):
            room = self.hub.rooms.get(f'{PREFIX}{p["id"]}')
            if room is not None and self._open(p, now):
                self._attend(p, room, dt, now)
            if now >= p['at'] and not p['started']:
                p['started'] = True
                if room is not None:
                    room.send(dict(t='wed_start', id=p['id']))
            if now >= p['at'] + WL.PARTY_SECS and not p['ending']:
                p['ending'] = True
                self.spawn(self.settle_party(p))
            if now >= p['at'] + WL.PARTY_SECS + CLOSE_AFTER and not p.get('closed'):
                p['closed'] = True
                self._close(p)
                self.att.pop(p['id'], None)

    def _attend(self, p: dict, room, dt: float, now: float) -> None:
        att = self.att.setdefault(p['id'], {})
        present = list(room.data['people']) + list(room.data['watch'])
        for pid in present:
            if pid in (p['pa'], p['pb']):
                continue
            a = att.get(pid)
            if a is None:
                pl = self.hub.players.get(pid)
                if pl is None:
                    continue
                since = pl.since or self.app.first_seen(pid)
                a = att[pid] = Att(pl.sid, pid, ok=bool(pl.name) and (pl.old or now - since >= 86400))
            a.secs += dt
            steps = min(WL.GUEST_STEPS, int(a.secs // WL.GUEST_STEP))
            if steps > a.steps:
                a.steps = steps
                self.spawn(self._step(p, a, steps))

    async def _step(self, p: dict, a: Att, steps: int) -> None:
        """A guest reached steps × 5 minutes: counted (the first time), then paid for every step not paid yet."""
        async with a.lock:
            now = time.time()
            if a.reward is None:
                day, week = WL.vn_day(now), WL.vn_week(now)

                async def run(tx):
                    n = await tx.fetchval('SELECT COUNT(*) FROM wedding_guests WHERE sid=? AND day=? AND paid=1 AND wedding<>?', (a.sid, day, p['id']))
                    paid = 1 if a.ok and int(n or 0) < WL.GUEST_WEDDINGS_PER_DAY else 0
                    await tx.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?, ?, ?, ?, ?, 0, ?, ?, ?) '
                                     'ON CONFLICT(wedding, sid) DO NOTHING', (p['id'], a.sid, a.pid, int(a.ok), paid, now, day, week))
                    row = await tx.fetchrow('SELECT paid, steps FROM wedding_guests WHERE wedding=? AND sid=?', (p['id'], a.sid))
                    return int(row['paid']), int(row['steps'])
                paid, done = await self.db.transaction(run)
                a.reward, a.paid = bool(paid), done
                if a.reward:
                    for side in ('a', 'b'):
                        await effects.grant(self.db, a.sid, 'closeness', WL.GUEST_CLOSE, f'wedc:{p["id"]}:{a.sid[:24]}:{side}', dict(src='wedding', **{'with': p[side]}))
            if not a.reward or steps <= a.paid:
                return
            for k in range(a.paid + 1, steps + 1):
                await effects.grant(self.db, a.sid, 'coins', WL.GUEST_XU, f'wedg:{p["id"]}:{a.sid[:24]}:{k}', dict(src='guest'))
            await self.db.execute('UPDATE wedding_guests SET steps=? WHERE wedding=? AND sid=? AND steps<?', (steps, p['id'], a.sid, steps))
            got = (steps - a.paid) * WL.GUEST_XU
            a.paid = steps
            self.hub.send_many(self.hub.conns_of(a.pid), dict(t='wed_xu', id=p['id'], n=got, steps=steps, max=WL.GUEST_STEPS))

    async def settle_party(self, p: dict) -> int:
        """The end: each spouse's reward for the guests who stayed 5 minutes (once), then the party is done."""
        n = min(WL.HOST_COUNT_MAX, int(await self.db.fetchval('SELECT COUNT(*) FROM wedding_guests WHERE wedding=? AND ok=1', (p['id'],)) or 0))
        total = n * WL.HOST_XU + sum(xu for k, xu, _ in WL.HOST_BONUS if n >= k)
        if total:
            for side, other in (('a', 'nb'), ('b', 'na')):
                text = f'{n} khách đã ở lại chung vui với bạn và {p[other]}. Mỗi người nhận {total} xu mừng từ khu phố 💛'
                await effects.grant(self.db, p[side], 'coins', total, f'wedhost:{p["id"]}:{side}',
                                    dict(src='host', popup=dict(title='💍 Đám cưới của hai bạn', text=text)))
                for k, _, tid in WL.HOST_BONUS:
                    if tid and n >= k:
                        await effects.grant(self.db, p[side], 'title', 1, f'wedhost:{p["id"]}:{side}:{tid}', dict(title=tid))
        await self.db.execute("UPDATE wedding_parties SET status='done', guests=?, done_at=? WHERE wedding=? AND status='booked'", (n, time.time(), p['id']))
        room = self.hub.rooms.get(f'{PREFIX}{p["id"]}')
        if room is not None:
            room.send(dict(t='wed_end', id=p['id'], n=n))
            if total:
                self.hub.send_many([c for c in room.conns if c.player.pid in (p['pa'], p['pb'])], dict(t='wed_paid', id=p['id'], xu=total))
        return n

    def _close(self, p: dict) -> None:
        room = self.hub.rooms.get(f'{PREFIX}{p["id"]}')
        if room is None:
            return
        for c in list(room.conns):
            pl = c.player
            if pl.ext.get('walk') == room.id:
                pl.ext.pop('walk', None)
            if pl.ext.get('wed_watch') == room.id:
                pl.ext.pop('wed_watch', None)
            c.ext.pop('walk', None)
            c.ext.pop('wed_watch', None)
            self.hub.send(c, dict(t='walk_left', why='wed_end'))
        self.street._empty(room)

    def spawn(self, coro) -> None:
        if len(self.tasks) >= TASKS_MAX:
            coro.close()
            return
        task = asyncio.ensure_future(self._guard(coro))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    @staticmethod
    async def _guard(coro) -> None:
        try:
            await coro
        except DbError as e:
            log('wedding db:', type(e).__name__, e)
        except Exception as e:  # noqa: BLE001 - one bad party never stops the others
            log('wedding:', type(e).__name__, e)


async def settle_week(db, week: str) -> list:
    """Pay a finished week's top 3 of "Khách mời của tuần" (fixed keys: paid once; ties to whoever reached the count
    first), then record it in wedding_race. Safe to run again: the live service runs it at its first schedule read after
    each Monday 00:00 (Vietnam), scripts/wedding_week.py by hand."""
    rows = await db.fetch('SELECT sid, pid, COUNT(*) AS n, MAX(counted_at) AS last FROM wedding_guests WHERE week=? AND ok=1 '
                          'GROUP BY sid, pid ORDER BY n DESC, last ASC, sid LIMIT ?', (week, len(WL.RACE)))
    top = []
    for (rank, xu, tid), r in zip(WL.RACE, rows):
        key = f'race:{week}:{rank}'
        text = f'Tuần {week[-2:]}, bạn dự {int(r["n"])} đám cưới và đứng hạng {rank} Khách mời của tuần. Danh hiệu “{WL.TITLE_NAMES[tid]}” theo bạn cả tuần này 🎉'
        await effects.grant(db, r['sid'], 'coins', xu, key, dict(src='race', popup=dict(title=WL.TITLE_NAMES[tid], text=text)))
        await effects.grant(db, r['sid'], 'title', 1, key + ':t', dict(title=tid))
        top.append(dict(rank=rank, sid=r['sid'], pid=r['pid'], n=int(r['n']), title=tid))
    await db.execute('INSERT INTO wedding_race(week, settled, top) VALUES(?, ?, ?) ON CONFLICT(week) DO NOTHING',
                     (week, time.time(), json.dumps(top, separators=(',', ':'))))
    return top


async def _push(db, sid: str, kind: str, body: str, url: str = '/') -> bool:
    """One web push through the game's queue (game/push.py rules: a subscription whose `social` preference is on,
    at most 6 unsent)."""
    subs = await db.fetch('SELECT prefs FROM push_subs WHERE sid=?', (sid,))
    if not subs or not any(_social(r['prefs']) for r in subs):
        return False
    if int(await db.fetchval('SELECT COUNT(*) FROM push_queue WHERE sid=? AND sent=0', (sid,)) or 0) >= 6:
        return False
    await db.execute('INSERT INTO push_queue(sid, kind, body, url, at) VALUES(?, ?, ?, ?, ?)', (sid, kind, body[:200], url[:200], time.time()))
    return True


def _social(prefs) -> bool:
    try:
        return bool(json.loads(prefs or '{}').get('social', True))
    except (TypeError, ValueError):
        return True

