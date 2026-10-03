"""💍 Live weddings (switch LIVE_WEDDING; design docs/superpowers/specs/2026-10-01-live-wedding-design.md).

A couple who books their wedding at a real date and time (game/marriage.py → game/wedding_live.py `wedding_parties`),
or any couple with a wedding who picks a time for their party ("Tổ chức tiệc cưới", free), throws one party anyone
online can attend. This feature reads the booked parties, opens a room `wed:<wedding id>` OPEN_BEFORE (5 minutes)
before the start, the party lasts PARTY_SECS (10 minutes), and pays the rewards through live/effects.grant (rows the
game server pays on load, game/live_effects.py). The numbers live in game/wedding_live.py (owner-approved).

The room is the strolling machinery of live/street.py (place 'wedding': a flower gate, the tent, tables): avatars with
name tags, moves, speech bubbles (stored and filtered like chat, channel = the room id), emotes, the tables' topic
cards. At most VISIBLE (60) avatars: later guests watch from outside the gate ("đông quá") and are still counted.

Accounts only (owner, 1.0.1: only accounts talk; the anti-alt rule): a player without an account may watch the party
from outside the gate (the watchers' view), never chats (store_message refuses), never takes a photo, never counts.

Attendance (owner, 01/10 after the first party: everyone who walks in is recorded, the party lasts 10 minutes):
* a guest is written to `wedding_guests` the moment they walk in (or watch from the gate), whoever they are; one
  account counts once (by player, whatever the tabs); the couple are never their own guests;
* a counted guest (ok) is an account with a named save; a player without an account is recorded (ok=0) and watches;
* every minute of the party (at+60 … at+600) everyone present during that minute gets MINUTE_XU (20 xu): the
  couple always, counted guests from at most GUEST_WEDDINGS_PER_DAY weddings a day; `steps` = minutes present;
  closeness with each spouse once per wedding. The minute marks come from the clock and every payment has a fixed
  key, so a restart of this service loses nothing but the seconds before the guests' sockets walk back in;
* at the end each spouse gets HOST_XU (15 xu) per counted guest, and the title "Đám cưới đông vui 🎉" at 20, with
  the private congratulation card.

Also here (one process, so once): the reminder 30 minutes before (the couple's friends: inbox + web push), the
weekly race settle ("Khách mời của tuần": #1 🥇 Khách quý của phố 300 xu, #2-#3 🎊 Ăn cưới chuyên nghiệp 150 xu;
ties to whoever reached the count first), and the race titles worn on name tags the whole next week.
Every reward has a fixed key (paid once); settles and reminders are guarded in the database (done once).

The party's fun (1.3.0, owner 02/10 after reading the guests' chat; the show itself is public/js/v4/wedfeast.js on the
party clock, the same for everyone without a frame). Server frames only for what a player does:
* 🍽️ the mâm cỗ at the tables: `wed_eat {k: dish|beer|soda, d}`. Gắp một món: +1 tinh thần (EAT_MAX a party), uống
  bia: −1 tinh thần (BEER_MAX a party), nước ngọt: nothing. The spirit is a live_effects row with a fixed id per slot
  (`weat:<wedding>:<sid24>:<1..3>`, `wbeer:<wedding>:<sid24>:<1..2>`), so retries, tabs and restarts never pay more
  than the caps; the taken slots are read back by primary key (never a scan). The room sees who ate or drank what.
* 💐 the bouquet: at TOSS_AT the room hears `wed_toss_open {until}`; either spouse sends `wed_toss {}`, or after
  TOSS_WAIT it is thrown for them. One guest present catches it (picked at random, the ones near the stage more
  likely) and gets TOSS_XU (key `wtoss:<wedding>`: once a party, also after a restart).
* 🎧 the music: the groom picks a track of WL.MUSIC (`wed_music {k}`; the bride when the groom is not in the room, or
  either spouse when the couple's characters are not one man and one woman), at most once every MUSIC_GAP seconds a
  party. The room hears `wed_music {k, at, by, who}` and every guest plays that track from `at` (position = now − at,
  modulo its length; the march and the lion drums still come first). Kept in memory: a restart goes back to 'auto'.

Frames (client → server; replies in brackets)
  wed_list {}                         [wed_list {parties: [{id, a, b, at, end, open, n, mine}], now}]
  wed_in {id, look, g, title, titles}         [walk_room {..., wed: {id, a, b, pids, at, end, overflow, photos}}]
  wed_photo {}                        [the room: wed_photo {n, pid, name, at}: the taker's screen is uploaded to
                                       POST /api/wedding/photo at `at`]
  wed_eat {k, d}                      [wed_ate {k, d, n, left}; the room: wed_eat {pid, k, d}]
  wed_toss {}                         [the room: wed_toss {by, frm, pid, name, to, xu, at}]
  wed_music {k}                       [the room: wed_music {id, k, at, by, name, who: 'groom'|'bride'|'couple'}]
  (walk_out, move, say, emote, sit, stand, topic, card: live/street.py)
Server pushes: wed_start {id}, wed_end {id, n}, wed_xu {n, k, max, why?}, wed_paid {xu}, wed_toss_open {id, until},
walk_left {why: 'wed_end'}.
"""
from __future__ import annotations

import asyncio
import json
import math
import random
import re
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
RID = re.compile(r'[A-Za-z0-9\-]{8,24}')   # a red envelope's request id (game/wedding_live.py envelope)
TASKS_MAX = 2000
CLOSE_AFTER = 120.0         # the room stays this long after the end (goodbyes), then closes


class Att:
    """One player's presence at one party."""
    __slots__ = ('sid', 'pid', 'ok', 'couple', 'seen', 'mins', 'paid', 'told', 'lock', 'rec')

    def __init__(self, sid: str, pid: str, ok: bool, couple: bool = False):
        self.sid, self.pid, self.ok, self.couple = sid, pid, ok, couple
        self.seen, self.mins, self.told = 0.0, 0, False
        self.paid = True if couple else None    # None: decided at the first minute (the daily cap)
        self.lock = asyncio.Lock()
        self.rec = None                          # the task writing the guest row


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

    def _mins(self, p: dict, pid: str | None) -> int:
        a = self.att.get(p['id'], {}).get(pid) if pid else None
        return a.mins if a else 0

    def _info(self, p: dict, room, overflow, pid: str | None = None) -> dict:
        """overflow: False (in the party), 'full' (more than VISIBLE) or 'account' (a player without an account watches).
        🧧 envs: quick picks; env_free: any amount, no cap (env_max is only the text older clients print)."""
        n = len(room.data['people']) + len(room.data['watch'])
        return dict(id=p['id'], a=p['na'], b=p['nb'], pids=[p['pa'], p['pb']], at=p['at'], end=p['at'] + WL.PARTY_SECS, n=n,
                    overflow=overflow, photos=p['photos'] or 0, photos_max=WL.PHOTOS_MAX, visible=WL.VISIBLE,
                    minutes=WL.PARTY_MINUTES, xu=WL.MINUTE_XU, host_xu=WL.HOST_XU, mins=self._mins(p, pid),
                    envs=list(WL.ENVELOPES), env_free=True, env_max=WL.ENVELOPE_MAX_OLD, wishes=list(WL.WISHES),
                    dishes=list(WL.DISHES), eat=self._left(p, pid), toss=self._toss_view(p), music=p.get('music'),
                    musics=list(WL.MUSIC))

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
        why = None if couple or (pl.account and len(room.data['people']) < WL.VISIBLE) else 'full' if pl.account else 'account'
        if why is None:
            if couple:
                x, y = geo.spots['stage']
                at = geo.clamp(x + (-55 if pl.pid == p['pa'] else 55), y + 20)   # side by side, their name tags apart
                title = '💍 Chú rể' if g == 'male' else '💍 Cô dâu' if g == 'female' else '💍 Cô dâu chú rể'
            else:
                x, y = geo.spots['spawn']
                at = geo.clamp(x + random.uniform(-90, 90), y + random.uniform(-30, 30))
                await self.street.lb_fresh()
                title = self.street.title_of(pl, f.get('title'), f.get('titles'))
            self.street._enter(room, conn, Walker(pl, look, g, title, at, now))
            overflow = False
        else:
            if len(room.data['watch']) >= WATCHERS_MAX:
                raise LiveError('full', 'Đông quá, cổng đã kín người. Thử lại sau ít phút nhé.')
            room.add(conn)
            room.data['watch'][pl.pid] = pl
            pl.ext['wed_watch'] = room.id
            conn.ext['wed_watch'] = room.id
            overflow = why
        if p['photos'] is None:
            p['photos'] = int(await self.db.fetchval('SELECT COUNT(*) FROM wedding_photos WHERE wedding=?', (p['id'],)) or 0)
        snap = self.street._snapshot(room, pl, now)
        self._arrive(p, pl, couple, now)
        snap['wed'] = self._info(p, room, overflow, pl.pid)
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

    # ---- 🍽️ the mâm cỗ: a dish, a beer, a soft drink -----------------------------------------------------------
    def _left(self, p: dict, pid: str | None) -> dict:
        """What this player may still eat and drink with an effect (as far as this process knows)."""
        a = self.att.get(p['id'], {}).get(pid) if pid else None
        eats = p.get('eats') or {}
        out = {}
        for k, cap in (('dish', WL.EAT_MAX), ('beer', WL.BEER_MAX)):
            got = eats.get((a.sid, k)) if a else None
            out[k] = cap - len(got) if got is not None else cap
        return out

    async def _slots(self, p: dict, sid: str, k: str, prefix: str, cap: int) -> set:
        """The slots this player already used (cached; read back once by primary key after a restart)."""
        eats = p.setdefault('eats', {})
        got = eats.get((sid, k))
        if got is None:
            ids = [f'{prefix}:{p["id"]}:{sid[:24]}:{i}' for i in range(1, cap + 1)]
            rows = await self.db.fetch(f'SELECT id FROM live_effects WHERE id IN ({",".join("?" * len(ids))})', tuple(ids))
            done = {int(r['id'].rsplit(':', 1)[1]) for r in rows}
            got = eats.setdefault((sid, k), done)
        return got

    @on('wed_eat', rate=(8, 10))
    async def wed_eat(self, conn, f):
        room, w = self.street._me(conn)
        p = self.parties.get(room.data.get('wid'))
        k, d = f.get('k'), f.get('d')
        if p is None or k not in ('dish', 'beer', 'soda') or (k == 'dish' and not (type(d) is int and 0 <= d < len(WL.DISHES))):
            raise LiveError('bad', 'Món này không có trên mâm.')
        d = d if k == 'dish' else None
        now = time.time()
        if not self._open(p, now) or p['ending']:
            raise LiveError('over', 'Tiệc tàn rồi, cỗ dọn mất rồi 😅')
        pl = conn.player
        n, left = 0, None
        if k != 'soda':
            cap, amount, prefix = (WL.EAT_MAX, WL.EAT_SPIRIT, 'weat') if k == 'dish' else (WL.BEER_MAX, WL.BEER_SPIRIT, 'wbeer')
            got = await self._slots(p, pl.sid, k, prefix, cap)
            for i in range(1, cap + 1):
                if i in got:
                    continue
                got.add(i)   # before the await: a second tap takes the next slot
                try:
                    ok = await effects.grant(self.db, pl.sid, 'spirit', amount, f'{prefix}:{p["id"]}:{pl.sid[:24]}:{i}', dict(src=f'wed_{k}'))
                except BaseException:
                    got.discard(i)
                    raise
                if ok:
                    n = amount
                break
            left = cap - len(got)
        if self.hub.rooms.get(room.id) is room:
            room.send(dict(t='wed_eat', pid=w.pid, k=k, d=d), sender=pl)
        return dict(t='wed_ate', id=p['id'], k=k, d=d, n=n, left=left)

    # ---- 💐 the bouquet toss ------------------------------------------------------------------------------------
    def _toss_view(self, p: dict) -> dict:
        st = p.get('toss_state')
        return dict(at=WL.TOSS_AT, open=st == 'open', until=round(p['toss_until'], 3) if st == 'open' else None, done=p.get('toss'))

    def _toss_tick(self, p: dict, room, now: float) -> None:
        """TOSS_AT: open the toss (once; after a restart only if nobody caught it yet); TOSS_WAIT later: throw it."""
        st = p.get('toss_state')
        if st is None and p['at'] + WL.TOSS_AT <= now < p['at'] + WL.PARTY_SECS - 5:
            p['toss_state'] = 'checking'
            self.spawn(self._toss_open(p, now))
        elif st == 'open' and now >= p['toss_until']:
            p['toss_state'] = 'done'
            self.spawn(self._toss(p, room, None))

    async def _toss_open(self, p: dict, now: float) -> None:
        try:
            caught = await self.db.fetchval('SELECT sid FROM live_effects WHERE id=?', (f'wtoss:{p["id"]}',))
        except BaseException:
            p['toss_state'] = None   # tried again at the next tick
            raise
        if caught:
            p['toss_state'] = 'done'
            return
        p['toss_until'] = min(now + WL.TOSS_WAIT, p['at'] + WL.PARTY_SECS - 3)
        p['toss_state'] = 'open'
        room = self.hub.rooms.get(f'{PREFIX}{p["id"]}')
        if room is not None:
            room.send(dict(t='wed_toss_open', id=p['id'], until=round(p['toss_until'], 3)))

    @on('wed_toss', rate=(3, 10))
    async def wed_toss(self, conn, f):
        room, w = self.street._me(conn)
        p = self.parties.get(room.data.get('wid'))
        if p is None or w.pid not in (p['pa'], p['pb']):
            raise LiveError('bad', 'Chỉ cô dâu chú rể mới tung hoa được nha 💐')
        st = p.get('toss_state')
        if st == 'done':
            raise LiveError('done', 'Hoa cưới tung rồi!')
        if st != 'open':
            raise LiveError('early', 'Chờ MC gọi tung hoa nhé!')
        p['toss_state'] = 'done'
        await self._toss(p, room, w.pid)
        return None

    async def _toss(self, p: dict, room, by: str | None) -> None:
        """Throw the bouquet: from the spouse who pressed (else either spouse here, else the stage) to one guest present,
        the ones near the stage likelier. Nobody but the couple here: it lands on the floor."""
        if room is None or self.hub.rooms.get(room.id) is not room:
            room = self.hub.rooms.get(f'{PREFIX}{p["id"]}')
        if room is None:
            return
        now = time.time()
        people = room.data['people']
        thrower = people.get(by) if by else (people.get(p['pa']) or people.get(p['pb']))
        sx, sy = GEO['wedding'].spots['stage']
        fx, fy = thrower.at(now) if thrower else (sx, sy)
        cands = [w for pid, w in people.items() if pid not in (p['pa'], p['pb']) and w.player.account]
        out = dict(t='wed_toss', id=p['id'], by=thrower.pid if thrower else None, frm=[round(fx, 1), round(fy, 1)], at=round(now, 3),
                   pid=None, name=None, to=None, xu=0)
        if cands:
            weights = []
            for w in cands:
                x, y = w.at(now)
                weights.append(1.0 / (1.0 + (math.hypot(x - sx, y - sy) / 140.0) ** 2))
            c = random.choices(cands, weights)[0]
            cx, cy = c.at(now)
            ok = await effects.grant(self.db, c.player.sid, 'coins', WL.TOSS_XU, f'wtoss:{p["id"]}', dict(src='bouquet'))
            out.update(pid=c.pid, name=c.name, to=[round(cx, 1), round(cy, 1)], xu=WL.TOSS_XU if ok else 0)
        p['toss'] = dict(pid=out['pid'], name=out['name'])
        if self.hub.rooms.get(room.id) is room:
            room.send(out)

    # ---- 🎧 the groom picks the music ---------------------------------------------------------------------------
    @staticmethod
    def _dj(p: dict, room) -> tuple:
        """Who may pick the music now: (pids, who). The groom (the spouse whose character is a man, the other not);
        the bride when he is not in the room; either spouse when the couple are not one man and one woman."""
        people = room.data['people']
        here = [people[pid] for pid in (p['pa'], p['pb']) if pid in people]
        men = [w for w in here if w.g == 'male']
        if len(men) == 1:
            return {men[0].pid}, 'groom'
        if len(here) == 1 and here[0].g == 'female':
            return {here[0].pid}, 'bride'
        return {w.pid for w in here}, 'couple'

    @on('wed_music', rate=(6, 20))
    async def wed_music(self, conn, f):
        room, w = self.street._me(conn)
        p = self.parties.get(room.data.get('wid'))
        k = f.get('k')
        if p is None or w.pid not in (p['pa'], p['pb']):
            raise LiveError('bad', 'Chỉ chú rể (hoặc cô dâu) mới chọn nhạc được nha 🎧')
        if k not in WL.MUSIC:
            raise LiveError('bad', 'Bài này không có trong danh sách.')
        pids, who = self._dj(p, room)
        if w.pid not in pids:
            raise LiveError('bad', 'Chú rể đang giữ quyền chọn nhạc nha 🎧')
        now = time.time()
        if not self._open(p, now) or p['ending']:
            raise LiveError('over', 'Tiệc tàn rồi.')
        last = p.get('music')
        if last and now - last['at'] < WL.MUSIC_GAP:
            raise LiveError('slow', 'Vừa đổi nhạc xong, nghe thử chút đã nha!', wait=round(WL.MUSIC_GAP - (now - last['at']), 1))
        p['music'] = dict(k=k, at=round(now, 3), by=w.pid, name=w.name, who=who)
        room.send(dict(t='wed_music', id=p['id'], **p['music']))
        return None

    # ---- 🧧 a guest's red envelope (paid by the game server, POST /api/marriage/envelope) ----------------------
    @on('wed_env', rate=(30, 60))   # spam guard only: each one is an envelope already paid (no cap on giving)
    async def wed_env(self, conn, f):
        """The sender's client says "sent": the debit row is read back (this player's, this wedding's), then the room
        sees who gave how much and the wish (once per envelope), and the couple's wallets are paid now."""
        room, w = self.street._me(conn)
        wid = room.data.get('wid')
        p = self.parties.get(wid)
        rid = f.get('rid')
        if p is None or not isinstance(rid, str) or not RID.fullmatch(rid):
            raise LiveError('bad', 'Phong bì không hợp lệ.')
        eid = f'wenv:{wid}:{rid}'
        told = p.setdefault('envs', set())
        if eid in told:
            return None
        r = await self.db.fetchrow('SELECT amount, data FROM marriage_effects WHERE id=? AND sid=?', (eid, conn.player.sid))
        if not r:
            raise LiveError('bad', 'Phong bì không hợp lệ.')
        told.add(eid)
        try:
            wish = json.loads(r['data'] or '{}').get('wish')
        except ValueError:
            wish = None
        text = WL.WISHES[wish] if type(wish) is int and 0 <= wish < len(WL.WISHES) else ''
        room.send(dict(t='wed_env', id=wid, pid=w.pid, name=w.name, n=-int(r['amount']), text=text))
        return None

    # ---- every second: attendance, start, end ---------------------------------------------------------------
    async def tick(self, now: float):
        self.last = max(self.last, now)
        if now >= self.next_refresh and self.refreshing is None:
            self.next_refresh = now + REFRESH
            self.spawn(self._refresh_now(now))
        for p in list(self.parties.values()):
            room = self.hub.rooms.get(f'{PREFIX}{p["id"]}')
            if room is not None and self._open(p, now):
                self._attend(p, room, now)
                self._toss_tick(p, room, now)
            if now >= p['at'] and not p.get('closed'):
                self._minutes(p, now)
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

    def _arrive(self, p: dict, pl, couple: bool, now: float) -> None:
        """Walked in (or watching from the gate): recorded at once (a guest row), present from now."""
        att = self.att.setdefault(p['id'], {})
        a = att.get(pl.pid)
        if a is None:
            a = att[pl.pid] = Att(pl.sid, pl.pid, ok=couple or bool(pl.account and pl.name), couple=couple)
        elif not a.ok and pl.account and pl.name:   # signed up or named during the party
            a.ok, a.rec = True, None
        a.seen = max(a.seen, now)
        if not couple and a.rec is None:
            a.rec = asyncio.ensure_future(self._record(p, a, now))
            self.tasks.add(a.rec)
            a.rec.add_done_callback(self.tasks.discard)

    async def _record(self, p: dict, a: Att, now: float) -> None:
        """The guest row (once; after a restart it reads back the minutes and the daily-cap decision already made)."""
        try:
            async with a.lock:
                await self.db.execute('INSERT INTO wedding_guests(wedding, sid, pid, ok, paid, steps, counted_at, day, week) VALUES(?, ?, ?, ?, 0, 0, ?, ?, ?) '
                                      'ON CONFLICT(wedding, sid) DO NOTHING', (p['id'], a.sid, a.pid, int(a.ok), now, WL.vn_day(now), WL.vn_week(now)))
                row = await self.db.fetchrow('SELECT ok, paid, steps FROM wedding_guests WHERE wedding=? AND sid=?', (p['id'], a.sid))
                if row:
                    a.mins = max(a.mins, int(row['steps']))
                    if int(row['paid']):
                        a.paid = True
                    if a.ok and not int(row['ok']):   # named or signed up since the first visit
                        await self.db.execute('UPDATE wedding_guests SET ok=1 WHERE wedding=? AND sid=?', (p['id'], a.sid))
        except DbError as e:
            a.rec = None   # tried again at the next tick
            log('wedding record:', type(e).__name__, e)

    def _attend(self, p: dict, room, now: float) -> None:
        """Every second: who is here (in the party or at the gate) is present during this minute."""
        for pid, w in list(room.data['people'].items()):
            self._arrive(p, w.player, pid in (p['pa'], p['pb']), now)
        for pid, pl in list(room.data['watch'].items()):
            self._arrive(p, pl, pid in (p['pa'], p['pb']), now)

    def _minutes(self, p: dict, now: float) -> None:
        """The minute marks at+60 … at+600: everyone present during the minute that just ended is paid."""
        if 'minute' not in p:   # first seen by this process: the marks already past were paid by the one before
            p['minute'] = max(0, min(WL.PARTY_MINUTES, int((now - p['at']) // WL.MINUTE_SECS)))
        while p['minute'] < WL.PARTY_MINUTES and now >= p['at'] + WL.MINUTE_SECS * (p['minute'] + 1):
            p['minute'] += 1
            k = p['minute']
            mark = p['at'] + WL.MINUTE_SECS * k
            who = [a for a in self.att.get(p['id'], {}).values() if a.seen > mark - WL.MINUTE_SECS]
            if who:
                self.spawn(self._pay_minute(p, k, who))

    async def _pay_minute(self, p: dict, k: int, who: list) -> None:
        for a in who:
            try:
                await self._pay_one(p, k, a)
            except DbError as e:
                log('wedding minute:', type(e).__name__, e)

    async def _pay_one(self, p: dict, k: int, a: Att) -> None:
        if a.rec is not None and not a.rec.done():
            await asyncio.shield(a.rec)
        async with a.lock:
            if not a.couple:
                a.mins += 1
                await self.db.execute('UPDATE wedding_guests SET steps=? WHERE wedding=? AND sid=? AND steps<?', (a.mins, p['id'], a.sid, a.mins))
            if not a.ok:
                if not a.told:
                    a.told = True
                    self.hub.send_many(self.hub.conns_of(a.pid), dict(t='wed_xu', id=p['id'], n=0, k=k, max=WL.PARTY_MINUTES, why='account'))
                return
            if a.paid is None:
                day = WL.vn_day(time.time())

                async def run(tx):
                    n = await tx.fetchval('SELECT COUNT(*) FROM wedding_guests WHERE sid=? AND day=? AND paid=1 AND wedding<>?', (a.sid, day, p['id']))
                    if int(n or 0) >= WL.GUEST_WEDDINGS_PER_DAY:
                        return False
                    await tx.execute('UPDATE wedding_guests SET paid=1 WHERE wedding=? AND sid=?', (p['id'], a.sid))
                    return True
                a.paid = bool(await self.db.transaction(run))
                for side in ('a', 'b'):
                    await effects.grant(self.db, a.sid, 'closeness', WL.GUEST_CLOSE, f'wedc:{p["id"]}:{a.sid[:24]}:{side}', dict(src='wedding', **{'with': p[side]}))
            if not a.paid:
                if not a.told:
                    a.told = True
                    self.hub.send_many(self.hub.conns_of(a.pid), dict(t='wed_xu', id=p['id'], n=0, k=k, max=WL.PARTY_MINUTES, why='cap'))
                return
            await effects.grant(self.db, a.sid, 'coins', WL.MINUTE_XU, f'wedm:{p["id"]}:{a.sid[:24]}:{k}', dict(src='couple' if a.couple else 'guest'))
            self.hub.send_many(self.hub.conns_of(a.pid), dict(t='wed_xu', id=p['id'], n=WL.MINUTE_XU, k=k, max=WL.PARTY_MINUTES))

    async def settle_party(self, p: dict) -> int:
        """The end: each spouse gets HOST_XU per counted guest who came (once), then the party is done."""
        n = min(WL.HOST_COUNT_MAX, int(await self.db.fetchval('SELECT COUNT(*) FROM wedding_guests WHERE wedding=? AND ok=1 AND steps>=?', (p['id'], WL.GUEST_MIN_MINUTES)) or 0))
        total = n * WL.HOST_XU + sum(xu for k, xu, _ in WL.HOST_BONUS if n >= k)
        if total:
            for side, other in (('a', 'nb'), ('b', 'na')):
                text = f'{n} khách đã đến chung vui với bạn và {p[other]}. Mỗi khách {WL.HOST_XU} xu: bạn nhận {total} xu mừng từ khu phố 💛'
                env = int(await self.db.fetchval('SELECT COALESCE(SUM(amount), 0) FROM live_effects WHERE sid=? AND id LIKE ?',
                                                 (p[side], f'wedenv:{p["id"]}:{side}:%')) or 0)
                if env:   # the guests' red envelopes (already in the wallet): their half
                    text += f' 🧧 Phong bì khách mừng: {env} xu (đã vào ví).'
                first = min(total, effects.AMOUNT_MAX)   # a very full party: the rest in more rows (each paid once)
                await effects.grant(self.db, p[side], 'coins', first, f'wedhost:{p["id"]}:{side}',
                                    dict(src='host', popup=dict(title='💍 Đám cưới của hai bạn', text=text)))
                for i, k in enumerate(range(first, total, effects.AMOUNT_MAX), 2):
                    await effects.grant(self.db, p[side], 'coins', min(effects.AMOUNT_MAX, total - k), f'wedhost:{p["id"]}:{side}:{i}', dict(src='host'))
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
    rows = await db.fetch('SELECT sid, pid, COUNT(*) AS n, MAX(counted_at) AS last FROM wedding_guests WHERE week=? AND ok=1 AND steps>=? '
                          'GROUP BY sid, pid ORDER BY n DESC, last ASC, sid LIMIT ?', (week, WL.GUEST_MIN_MINUTES, len(WL.RACE)))
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

