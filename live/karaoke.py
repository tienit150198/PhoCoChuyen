"""🎤 Phòng hát Mây (switch LIVE_KARAOKE, off by default; welcome flag `kara`; owner 06/10, karaoke phase 1).

Three public themed rooms anyone online can walk into (THEMES: Nhạc trẻ, Bolero · trữ tình, Nhạc quốc tế), at most
ROOM_CAP people each; a full room opens an overflow room of the same theme (`kara:tre-2` …, PER_THEME rooms a theme
at most). Memory only, like the photobooth's rooms: a restart empties the queues and the clients walk back in.
Modelled on the wedding room (live/wedding.py): one shared clock for the music (`at` in server time; each client plays
from now − at), bubbles stored and filtered like chat (channel = the room id, the chat's route() so reports and an
admin's hide reach the room), accounts only for anything but listening (the anti-alt rule).

The stage (no live voice in v1: everyone watches the same YouTube video at the same second)
* `kara_add {vid, e}`: a song joins the queue. `e` is a "lượt hát" ticket bought on the game server (POST
  /api/karaoke/queue, game/karaoke.py: QUEUE_XU, the first of the day free), redeemed here once (kara_tickets.used).
  The song must have passed the oEmbed check (kara_songs ok=1) and not be banned. One song a player in a room's
  queue, HOUR_MAX an hour, QUEUE_MAX a queue. `kara_can {}` says beforehand whether an add would be taken (so nobody
  pays for a refused one; an unused ticket is handed back by the game server anyway).
* The head of the queue whose singer is in the room goes on stage: `kara_play {e, vid, title, by, at, dur}` with
  `at` = now + LEAD (the load lead: every player starts at the same second). A singer away from the room is passed
  over, and dropped after ABSENT_WAIT. Clients report the video length (`kara_dur`, the median of the first three);
  the song ends at at + dur (DUR_MAX at most: cut), then `kara_end {why, hearts, cheers, tips}` and APPLAUSE
  seconds of applause before the next one. The ticket is stamped `played` (game/karaoke.py tips check it).
* `kara_skip {e}`: the singer, or an admin. `kara_vote {e}`: vote-skip by the accounts present, need =
  max(min(3, voters), 40 % of voters).
* `kara_react {k}` (REACTS) and `kara_cheer {}` (hold-to-cheer pulses): anonymous counts, batched to the room as
  `kara_fx {r, cheer}` at most every FX_EVERY seconds. Tips are paid on the game server (POST /api/karaoke/tip) and
  announced here from its NOTIFY (op 'kara_tip') as `kara_tipped`.
* `kara_say {text}`: a bubble (chat.store_message: filters, mutes; `kara_said` to the room, blocks respected).

🧩 Đoán bài (text only; the YouTube player is never hidden or covered for it)
* `kara_round {mode: 'lyric'|'emoji', clue, answer, vid?}`: the host gives a short lyric line with blanks (at most
  CLUE_WORDS words, at least one ___) or emoji clues, and the answer (alternatives split by '/'). Everyone sees
  `kara_round {id, host, mode, clue, until, words}`. One round a room at a time, GUESS_SECS long.
* Guesses are bubbles: a `kara_say` while a round is open is matched against the answer first (game/karaoke.py
  match: accent-insensitive, normalised, a small typo allowed on long answers). A right one is never shown (it would
  spoil it): the round ends with `kara_reveal {answer, by, xu}`; a close one tells only its writer (`kara_near`).
* The first right guess wins GUESS_XU from a fixed pool (live/effects.grant, key `kguess:<host>:<round>`, paid once),
  at most GUESS_DAY_CAP a player a Vietnam day, at most GUESS_HOST_DAY paid rounds a host a day, never the host,
  never in the first GUESS_MIN_SECS. Nothing else creates money.
* A timeout, or the host ending it (`kara_round_end`) or leaving: `kara_reveal` with no winner. Either way the host's
  YouTube link (checked like a queued song) then plays as a reward: it goes to the front of the queue.

Moderation
* Admins (ADMIN_USERS) in a room: skip any song, `kara_kick {pid}` (out of every room for KICK_SECS),
  `kara_close {}` (everyone out, the room shut for CLOSE_SECS), `kara_ban {vid}` (kara_songs.banned; skipped if
  playing, gone from every queue, refused afterwards), and end any round. The same from the admin site through the
  game server (game/karaoke.py admin_act → NOTIFY op 'kara').
* `kara_report {pid | vid, reason}` → `reports` (kind 'kara'; 'minor' first in the admin queue). Bubbles are reported
  with the chat's own `report {id}`.
* A chat mute (NOTIFY op 'mute') takes the player's songs out of every queue, ends their song and their round.
  Muted players cannot queue, talk, guess or host.
* Blocks: bubbles, a round's clue and reveal, tips and the people list skip players who blocked each other.

🎙️ Mic trực tiếp (switch LIVE_KARAOKE_MIC, welcome flag `kara_mic`; owner 07/10; game/karaoke_mic.py, live/sfu.py)
* Only the singer on stage may turn a live mic on (`kara_mic {on: 1}`); everyone in the room hears them through the
  SFU (LiveKit); listeners never speak, nothing is recorded. Accounts only, not muted, at least MIC_ACCOUNT_DAYS old,
  and a stored birth year (asked once on the game server: POST /api/karaoke/birth) of someone 16 or older (error codes
  'birth' and 'young'). Each mic session gets its own SFU room (live/sfu.py room_name: room, song, n-th session),
  created before any token is given; the singer's token publishes the microphone only, a listener's (`kara_listen`)
  subscribes only and is good for LISTEN_TTL seconds to join.
* Voice and music together: the singer's page sends its own video time (`kara_vt {e, vt, st, r, rtt}`, about once a
  second while the mic is on); it is relayed, stamped, to the mic's listeners (`kara_vt {e, vt, at, r?, rtt?}`), whose
  video then follows the singer's minus the voice's delay (v4/karaoke.js sync()). Data never goes over the SFU.
* The room sees `kara_live {on, by, until}` (and `stage.mic`): "🎤 Đang phát trực tiếp giọng hát".
* Cut (the SFU room is deleted: the singer and every listener are disconnected at once, an old token joins nothing):
  the song ends, is skipped, voted off, cut by an admin, the singer is kicked or muted or leaves, the room closes,
  MIC_SECS after it was first turned on, `kara_mic {on: 0}`, an admin (`kara_mic_cut`, or the admin site: NOTIFY op
  'kara' act 'mic'), or MIC_REPORTS distinct reports of the singer while it is on. A cut by an admin or by reports
  holds for the rest of the song.
* Blocks: a player who blocked the singer, or whom the singer blocked, gets no listening token; a block made while the
  mic is on removes that listener from the SFU room within a second (tick). Leaving the Phòng hát room does too.

Frames (client → server; replies in brackets)
  kara_time {c}                     [kara_time {c, at}]  (the server clock)
  kara_list {}                      [kara_list {rooms: [{id, name, emoji, theme, n, cap, song, q, closed}]}]
  kara_in {id | theme}              [kara_room {id, name, emoji, theme, cap, me, account, adm, n, people, stage, queue,
                                     round, now, reacts, tips, price, moved?}]
  kara_out {}                       [kara_left {why: 'out'}]
  kara_can {}                       [kara_can {ok, why}]
  kara_add {vid, e}                 [kara_added {e}]          kara_dur {e, dur}     kara_skip {e}     kara_vote {e}
  kara_react {k}   kara_cheer {}    kara_say {text} [kara_said … to the room]      kara_report {pid | vid, reason}
  kara_round {mode, clue, answer, vid?}   kara_round_end {}       kara_kick {pid}  kara_close {}  kara_ban {vid}
  kara_mic {on}                     [kara_mic {on, url?, token?, until?}]   kara_listen {} [kara_listen {on, url?, token?, e?}]
  kara_mic_cut {}  (admin)          kara_vt {e, vt, st?, r?, rtt?}  (the live singer; no reply)
Server pushes: kara_ppl {n, pid, name, on}, kara_q {queue}, kara_play, kara_stage, kara_votes {e, n, need},
kara_end, kara_fx {r, cheer}, kara_tipped {e, frm, name, xu}, kara_said, kara_round, kara_reveal, kara_near,
kara_won {xu}, kara_left {why: out | other | kick | closed}, kara_live {on, e, by?, until?, why?}, kara_listen {on: 0},
kara_vt {e, vt, at, r?, rtt?} (to the mic's listeners).
"""
from __future__ import annotations

import asyncio
import math
import re
import secrets
import statistics
import time

from game import karaoke as KG
from game import karaoke_mic as KM

from . import effects, filters
from .db import Error as DbError, log
from .limits import LRU, Window
from .protocol import Feature, LiveError, on
from .sfu import Sfu, room_name

PREFIX = 'kara:'
THEMES = {'tre': ('Nhạc trẻ', '🎧'), 'bolero': ('Bolero · trữ tình', '🌾'), 'qt': ('Nhạc quốc tế', '🌍')}
ORDER = ('tre', 'bolero', 'qt')
ROOM_RX = re.compile(r'kara:(tre|bolero|qt)(?:-([2-9]))?')
ROOM_CAP = KG.ROOM_CAP
PER_THEME = 4                 # rooms a theme at most (the first and its overflow rooms)
QUEUE_MAX = 12
HOUR_MAX = 6                  # songs one player adds in an hour
LEAD = 5.0                    # seconds from kara_play to the first frame (every phone loads, then starts at once)
DUR_DEFAULT = 420.0           # no length reported: 7 minutes
DUR_MAX = 420.0               # a song is cut at 7 minutes
DUR_MIN = 15.0
APPLAUSE = 10.0               # the applause moment after a song (owner 06/10: 10 s)
SHORT_CLAP = 3.0              # after a skip, a vote, an admin
ABSENT_WAIT = 12.0            # a singer away from the room keeps their place this long
FX_EVERY = 0.5
CHEER_STEP, CHEER_DECAY = 4.0, 6.0
REACTS = ('👏', '❤️', '🔥', '😂', '🎉', '🌹', '🥹', '💯')
KICK_SECS = 3600
CLOSE_SECS = 600
GUESS_SECS = 60.0
GUESS_GAP = 30.0              # one round per host per this many seconds
GUESS_MIN_SECS = 5.0          # a right guess this fast pays nothing (bots, friends told in advance)
SAY_LEN = 120
TASKS_MAX = 500
REASONS = KG.REASONS
VT_GAP = 0.6                  # 🎙️ kara_vt: one relayed at most this often (the singer's page sends one a second)
VT_SPAN = 15.0                # a singer's video time this far from the shared clock is not relayed
VT_BACK = 1.5                 # the singer's own time stamp is trusted this far back at most
VT_RTT_MAX = 3000             # ms
VT_RATE = (0.5, 2.0)          # a playback rate relayed (the page nudges 0.95 / 1.05)


class Member:
    __slots__ = ('pid', 'player', 'conn', 'name', 'since')

    def __init__(self, conn, now: float):
        self.conn, self.player, self.pid = conn, conn.player, conn.player.pid
        self.name = conn.player.name or 'Khách'
        self.since = now


class Entry:
    __slots__ = ('e', 'vid', 'title', 'pid', 'sid', 'name', 'reward', 'away')

    def __init__(self, e, vid, title, pid, sid, name, reward=False):
        self.e, self.vid, self.title, self.pid, self.sid, self.name, self.reward = e, vid, title, pid, sid, name, reward
        self.away = 0.0

    def view(self) -> dict:
        out = dict(e=self.e, vid=self.vid, title=self.title, by=dict(pid=self.pid, name=self.name))
        if self.reward:
            out['reward'] = 1
        return out


def vote_need(voters: int) -> int:
    """Votes that skip a song: max(min(3, voters), 40 % of voters); 1 when only one listener is there."""
    return max(1, min(3, voters), math.ceil(0.4 * voters))


def parse_room(rid) -> tuple | None:
    m = ROOM_RX.fullmatch(rid) if isinstance(rid, str) else None
    return (m.group(1), int(m.group(2) or 1)) if m else None


def room_id(theme: str, n: int) -> str:
    return f'{PREFIX}{theme}' + ('' if n == 1 else f'-{n}')


class KaraokeFeature(Feature):
    name, flag = 'karaoke', 'kara'

    def __init__(self, app):
        super().__init__(app)
        self.kicked = LRU(5000)          # pid -> until (an admin's kick: every room)
        self.closed: dict = {}           # room id -> until (an admin closed it)
        self.tasks: set = set()
        self.plays = self.rounds = self.wins = self.mics = 0
        cfg = self.cfg
        self.sfu = Sfu(cfg.sfu_url, cfg.sfu_api, cfg.sfu_key, cfg.sfu_secret)

    async def start(self):
        if self.app.chat:
            self.app.chat.route(PREFIX, audience=self._audience, can_read=self._can_read)
        if self._mic_on():
            self.spawn(self._sweep())

    def _mic_on(self) -> bool:
        return bool(self.cfg.flags().get('kara_mic'))

    async def _sweep(self) -> None:
        """Mic rooms left on the SFU by a previous run of this service (a restart forgets every room): delete them."""
        for name in await self.sfu.rooms():
            if name.startswith('kara-'):
                await self.sfu.delete_room(name)

    # ---- the chat's routes (bubbles: reports, admin hides) ------------------------------------------------
    def _audience(self, ch: str) -> list:
        r = self.hub.rooms.get(ch)
        return [r] if r is not None else []

    @staticmethod
    def _can_read(player, ch: str) -> bool:
        return ch in player.ext.get('kara_seen', ())

    # ---- helpers ----------------------------------------------------------------------------------------
    def _admin(self, p) -> bool:
        chat = self.app.chat
        return bool(chat and chat.is_admin(p))

    def _rooms(self) -> list:
        return self.hub.rooms_with_prefix(PREFIX)

    async def _ensure_loaded(self, p) -> None:
        chat = self.app.chat
        if chat is None:
            return
        if not p.loaded:   # the chat is off: its hello did not load friends and blocks
            await chat.load_friends(p)
            await chat.load_hidden(p)
            p.loaded = True
        if not p.name or not p.account:
            await chat.refresh(p)

    def _new_room(self, theme: str, n: int):
        rid = room_id(theme, n)
        room = self.hub.room(rid, on_empty=self._empty)
        if not room.data:
            name, emoji = THEMES[theme]
            room.data.update(theme=theme, n=n, name=name if n == 1 else f'{name} {n}', emoji=emoji, people={}, queue=[],
                             stage=None, phase='idle', at=0.0, until=0.0, dur=DUR_DEFAULT, durs={}, votes=set(), hearts=0,
                             cheers=0, tips=0, fx={}, cheer=0.0, fx_due=False, round=None, mic=None)
        return room

    def _empty(self, room) -> None:
        if not room.data.get('people'):
            self._mic_off(room, 'empty', cut=True)
            self.hub.drop_room(room.id)

    def _mine(self, conn):
        rid = conn.ext.get('kara')
        room = self.hub.rooms.get(rid) if rid else None
        m = room.data['people'].get(conn.player.pid) if room is not None else None
        if m is None or m.conn is not conn:
            raise LiveError('not_in', 'Bạn chưa vào Phòng hát.')
        return room, m

    def _need_account(self, p, what: str = 'hát cùng mọi người') -> None:
        if not p.account:
            raise LiveError('account', f'Tạo tài khoản để {what} nhé.')
        if p.muted_until > time.time() and not self._admin(p):
            raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))

    def _send_from(self, room, frame: dict, pid: str | None, skip=None) -> None:
        """To the room (but `skip`), except players who blocked `pid` or whom `pid` blocked."""
        if not pid:
            room.send(frame, skip=skip)
            return
        p = self.hub.players.get(pid)
        hid = p.hidden if p else set()
        self.hub.send_many([c for c in room.conns if c is not skip and c.player.pid not in hid and pid not in c.player.hidden], frame)

    def _people(self, room, p) -> list:
        return [dict(pid=m.pid, name=m.name) for m in room.data['people'].values()
                if m.pid not in p.hidden and p.pid not in m.player.hidden][:ROOM_CAP + 5]

    def _voters(self, d) -> int:
        st = d['stage']
        return sum(1 for m in d['people'].values() if m.player.account and (st is None or m.pid != st.pid))

    def _stage(self, d) -> dict | None:
        st = d['stage']
        if st is None:
            return None
        out = dict(st.view(), phase=d['phase'], at=round(d['at'], 3), dur=round(d['dur'], 1), until=round(d['until'], 3),
                   votes=len(d['votes']), need=vote_need(self._voters(d)), hearts=d['hearts'], cheers=d['cheers'], tips=d['tips'])
        mic = d.get('mic')
        if mic is not None and mic['on'] and mic['e'] == st.e:
            out['mic'] = dict(on=1, until=round(mic['until'], 3))
        return out

    def _round(self, d, p=None) -> dict | None:
        rd = d['round']
        if rd is None or (p is not None and (rd['host'] in p.hidden or p.pid in self._hidden_of(rd['host']))):
            return None
        return dict(id=rd['id'], host=dict(pid=rd['host'], name=rd['name']), mode=rd['mode'], clue=rd['clue'], until=round(rd['until'], 3),
                    words=rd['words'], reward=bool(rd['vid']))

    def _hidden_of(self, pid: str) -> set:
        p = self.hub.players.get(pid)
        return p.hidden if p else set()

    def snapshot(self, room, p) -> dict:
        d = room.data
        return dict(t='kara_room', id=room.id, name=d['name'], emoji=d['emoji'], theme=d['theme'], cap=ROOM_CAP, me=p.pid,
                    account=bool(p.account), adm=1 if self._admin(p) else 0, n=len(d['people']), people=self._people(room, p),
                    stage=self._stage(d), queue=[e.view() for e in d['queue']], round=self._round(d, p), now=round(time.time(), 3),
                    reacts=list(REACTS), tips=list(KG.TIP_CHIPS), price=KG.QUEUE_XU, lead=LEAD)

    def _tell_queue(self, room) -> None:
        room.send(dict(t='kara_q', id=room.id, queue=[e.view() for e in room.data['queue']]))

    def _tell_stage(self, room) -> None:
        room.send(dict(t='kara_stage', id=room.id, stage=self._stage(room.data)))

    # ---- the list, in and out -----------------------------------------------------------------------------
    @on('kara_time', rate=(12, 10))
    async def kara_time(self, conn, f):
        """The server clock for the shared video (the client keeps the reply with the smallest round trip)."""
        c = f.get('c')
        return dict(t='kara_time', c=c if type(c) is int and 0 <= c < 10**6 else 0, at=round(time.time(), 4))

    @on('kara_list', rate=(10, 10))
    async def kara_list(self, conn, f):
        now = time.time()
        out = []
        for theme in ORDER:
            name, emoji = THEMES[theme]
            for n in range(1, PER_THEME + 1):
                rid = room_id(theme, n)
                room = self.hub.rooms.get(rid)
                if room is None and n > 1:
                    continue
                d = room.data if room is not None else {}
                st = d.get('stage')
                out.append(dict(id=rid, name=d.get('name') or name, emoji=emoji, theme=theme, n=len(d.get('people') or {}), cap=ROOM_CAP,
                                song=dict(vid=st.vid, title=st.title, by=st.name) if st is not None else None, q=len(d.get('queue') or []),
                                closed=self.closed.get(rid, 0) > now, rnd=bool(d.get('round'))))
        return dict(t='kara_list', rooms=out, price=KG.QUEUE_XU)

    def _pick(self, theme: str, want: int | None, p, now: float):
        """The room to enter: the one asked for when it has room, else the first of the theme with room (an overflow
        room opens when all are full). Admins always fit."""
        adm = self._admin(p)
        order = ([want] if want else []) + [n for n in range(1, PER_THEME + 1) if n != want]
        for n in order:
            rid = room_id(theme, n)
            if self.closed.get(rid, 0) > now and not adm:
                continue
            room = self.hub.rooms.get(rid)
            if room is None:
                return self._new_room(theme, n)
            if p.pid in room.data['people'] or adm or len(room.data['people']) < ROOM_CAP:
                return room
        return None

    @on('kara_in', rate=(10, 60))
    async def kara_in(self, conn, f):
        p = conn.player
        now = time.time()
        if self.kicked.get(p.pid, 0) > now and not self._admin(p):
            raise LiveError('kicked', 'Bạn tạm thời chưa vào Phòng hát được.')
        got = parse_room(f.get('id'))
        theme, want = got if got else (f.get('theme'), None)
        if theme not in THEMES:
            raise LiveError('bad', 'Không thấy phòng này.')
        await self._ensure_loaded(p)
        if want and self.closed.get(room_id(theme, want), 0) > now and not self._admin(p):
            raise LiveError('closed', 'Phòng này đang tạm đóng, thử phòng khác nhé.')
        room = self._pick(theme, want, p, now)
        if room is None:
            raise LiveError('full', 'Các phòng đều đông quá, lát quay lại nhé.')
        d = room.data
        m = d['people'].get(p.pid)
        if m is not None:   # back in from another tab of mine, or the same tab again
            if m.conn is not conn:
                old = m.conn
                m.conn = conn
                room.add(conn)
                conn.ext['kara'] = room.id
                old.ext.pop('kara', None)
                self.hub.send(old, dict(t='kara_left', why='other'))
                room.remove(old)
        else:
            self._leave(p, 'other', keep=conn)
            room = self.hub.rooms.get(room.id) or self._new_room(theme, d['n'])
            d = room.data
            m = Member(conn, now)
            d['people'][p.pid] = m
            room.add(conn)
            conn.ext['kara'] = room.id
            self._send_from(room, dict(t='kara_ppl', id=room.id, n=len(d['people']), pid=p.pid, name=m.name, on=1), p.pid, skip=conn)
        p.ext['kara'] = room.id
        seen = p.ext.setdefault('kara_seen', set())
        if len(seen) < 32:
            seen.add(room.id)
        out = self.snapshot(room, p)
        if want and room.id != room_id(theme, want):
            out['moved'] = 1
        return out

    def _leave(self, p, why: str | None = None, keep=None) -> None:
        rid = p.ext.pop('kara', None)
        room = self.hub.rooms.get(rid) if rid else None
        if room is None:
            return
        d = room.data
        m = d['people'].pop(p.pid, None)
        if m is None:
            return
        m.conn.ext.pop('kara', None)
        if why and m.conn is not keep:
            self.hub.send(m.conn, dict(t='kara_left', id=room.id, why=why))
        mic = d.get('mic')
        if mic is not None and mic['on']:
            if mic['pid'] == p.pid:          # the singer left the room: their mic goes off (they may turn it on again)
                self._mic_off(room, 'left')
            elif p.pid in mic['subs']:       # a listener left: out of the SFU room too
                mic['subs'].discard(p.pid)
                self.spawn(self.sfu.remove(mic['sfu'], p.pid))
        rd = d['round']
        if rd and rd['host'] == p.pid:
            self._reveal(room, None, 'left')
        alive = self.hub.rooms.get(room.id) is room
        room.remove(m.conn)   # the last one out drops the room
        if alive and d['people']:
            self._send_from(room, dict(t='kara_ppl', id=room.id, n=len(d['people']), pid=p.pid, on=0), p.pid)

    @on('kara_out', rate=(20, 60))
    async def kara_out(self, conn, f):
        self._leave(conn.player, 'other', keep=conn)
        return dict(t='kara_left', why='out')

    async def on_close(self, conn):
        rid = conn.ext.pop('kara', None)
        room = self.hub.rooms.get(rid) if rid else None
        if room is None:
            return
        p = conn.player
        m = room.data['people'].get(p.pid)
        if m is not None and m.conn is conn:   # its song keeps its place for ABSENT_WAIT (the client comes back in)
            p.ext['kara'] = rid
            self._leave(p)

    # ---- the queue -----------------------------------------------------------------------------------------
    def _why_not(self, room, p) -> str | None:
        d = room.data
        if not p.account:
            return 'account'
        if p.muted_until > time.time():
            return 'muted'
        if any(e.pid == p.pid and not e.reward for e in d['queue']) or (d['stage'] is not None and d['stage'].pid == p.pid and d['phase'] in ('deck', 'play') and not d['stage'].reward):
            return 'queued'
        if len(d['queue']) >= QUEUE_MAX:
            return 'full'
        w = p.ext.get('kara_hour')
        if w is not None and w.wait() > 0:
            return 'hour'
        return None

    WHY = dict(account='Tạo tài khoản để hát nhé.', muted='Bạn đang bị tạm khóa chat.', queued='Bạn đã có một bài trong hàng rồi.',
               full='Hàng chờ đầy rồi, đợi chút nhé.', hour=f'Mỗi giờ hát tối đa {HOUR_MAX} bài thôi nha.')

    @on('kara_can', rate=(20, 60))
    async def kara_can(self, conn, f):
        room, m = self._mine(conn)
        why = self._why_not(room, conn.player)
        return dict(t='kara_can', ok=why is None, why=why, msg=self.WHY.get(why, ''))

    @on('kara_add', rate=(6, 60))
    async def kara_add(self, conn, f):
        room, m = self._mine(conn)
        p = conn.player
        why = self._why_not(room, p)
        if why:
            raise LiveError(why, self.WHY[why])
        vid, e = f.get('vid'), f.get('e')
        if not (isinstance(vid, str) and KG.VID_RX.fullmatch(vid)) or not (isinstance(e, str) and KG.TICKET_RX.fullmatch(e)):
            raise LiveError('bad', 'Bài hát không hợp lệ.')
        song = await self.db.fetchrow('SELECT title, ok, banned FROM kara_songs WHERE vid=?', (vid,))
        if not song or int(song['banned']) or not int(song['ok']):
            raise LiveError('song', 'Bài này chưa phát được ở đây, chọn bài khác nhé.')
        t = time.time()
        n = await self.db.execute('UPDATE kara_tickets SET used=1, vid=?, room=? WHERE id=? AND sid=? AND kind=? AND used=0 AND at>?',
                                  (vid, room.id, e, p.sid, 'queue', t - KG.TICKET_DAYS * 86400))
        if n != 1:
            raise LiveError('ticket', 'Lượt hát không hợp lệ, thử lại nhé.')
        w = p.ext.get('kara_hour')
        if w is None:
            w = p.ext['kara_hour'] = Window(HOUR_MAX, 3600)
        w.hit()
        if self.hub.rooms.get(room.id) is not room:   # the room went meanwhile: the ticket is spent, put the song back in
            room = self._new_room(room.data['theme'], room.data['n'])
        room.data['queue'].append(Entry(e, vid, filters.mask(str(song['title'] or ''))[:KG.TITLE_LEN] or 'Bài hát YouTube', p.pid, p.sid, m.name))
        if room.data['phase'] == 'idle':
            self._advance(room, t)   # on stage now (it tells the queue)
        else:
            self._tell_queue(room)
        return dict(t='kara_added', e=e)

    # ---- the stage ---------------------------------------------------------------------------------------
    def _advance(self, room, now: float) -> None:
        d = room.data
        if d['phase'] != 'idle':
            return
        pick, changed = None, False
        for en in list(d['queue']):
            if en.reward or en.pid in d['people']:
                pick = en
                break
            if not en.away:
                en.away = now
            elif now - en.away > ABSENT_WAIT:
                d['queue'].remove(en)
                changed = True
        if pick is None:
            if changed:
                self._tell_queue(room)
            return
        d['queue'].remove(pick)
        at = now + LEAD
        d.update(stage=pick, phase='deck', at=at, until=at, dur=DUR_DEFAULT, durs={}, votes=set(), hearts=0, cheers=0, tips=0, fx={}, cheer=0.0)
        self.plays += 1
        room.send(dict(t='kara_play', id=room.id, **pick.view(), at=round(at, 3), dur=None, now=round(now, 3)))
        self._tell_queue(room)
        if not pick.reward:
            self.spawn(self._played(pick, now))

    async def _played(self, en: Entry, now: float) -> None:
        await self.db.execute('UPDATE kara_tickets SET played=? WHERE id=?', (now, en.e))
        await self.db.execute('UPDATE kara_songs SET plays=plays+1 WHERE vid=?', (en.vid,))

    def _end(self, room, why: str, now: float) -> None:
        d = room.data
        st = d['stage']
        if st is None or d['phase'] not in ('deck', 'play'):
            return
        clap = APPLAUSE if why in ('done', 'cut') else SHORT_CLAP
        self._mic_off(room, 'end', cut=True)
        d.update(phase='clap', until=now + clap)
        self._flush(room)
        room.send(dict(t='kara_end', id=room.id, e=st.e, why=why, by=dict(pid=st.pid, name=st.name), hearts=d['hearts'], cheers=d['cheers'],
                       tips=d['tips'], until=round(now + clap, 3)))

    @on('kara_dur', rate=(6, 60))
    async def kara_dur(self, conn, f):
        room, m = self._mine(conn)
        d = room.data
        st, dur = d['stage'], f.get('dur')
        if st is None or f.get('e') != st.e or type(dur) not in (int, float) or not 1 <= dur <= 36000 or len(d['durs']) >= 3:
            return None
        d['durs'][m.pid] = float(dur)
        d['dur'] = max(DUR_MIN, min(DUR_MAX, statistics.median(d['durs'].values())))
        if len(d['durs']) == 1:
            self._tell_stage(room)
        return None

    @on('kara_skip', rate=(10, 60))
    async def kara_skip(self, conn, f):
        room, m = self._mine(conn)
        d = room.data
        st = d['stage']
        adm = self._admin(conn.player)
        if st is None or d['phase'] not in ('deck', 'play') or (f.get('e') is not None and f.get('e') != st.e):
            raise LiveError('gone', 'Bài này đã xong rồi.')
        if st.pid != m.pid and not adm:
            raise LiveError('bad', 'Chỉ người hát bỏ được bài của mình. Bạn có thể bỏ phiếu.')
        self._end(room, 'skip' if st.pid == m.pid else 'admin', time.time())
        return None

    @on('kara_vote', rate=(10, 60))
    async def kara_vote(self, conn, f):
        room, m = self._mine(conn)
        d = room.data
        st, p = d['stage'], conn.player
        if st is None or d['phase'] not in ('deck', 'play') or f.get('e') != st.e:
            raise LiveError('gone', 'Bài này đã xong rồi.')
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để bỏ phiếu nhé.')
        if st.pid == m.pid:
            raise LiveError('bad', 'Bấm Bỏ bài để dừng bài của bạn.')
        d['votes'].add(m.pid)
        need = vote_need(self._voters(d))
        room.send(dict(t='kara_votes', id=room.id, e=st.e, n=len(d['votes']), need=need))
        if len(d['votes']) >= need:
            self._end(room, 'vote', time.time())
        return None

    # ---- the room's reactions ---------------------------------------------------------------------------
    def _fx_soon(self, room) -> None:
        d = room.data
        if d['fx_due']:
            return
        d['fx_due'] = True
        asyncio.get_running_loop().call_later(FX_EVERY, self._flush, room)

    def _flush(self, room) -> None:
        d = room.data
        d['fx_due'] = False
        if self.hub.rooms.get(room.id) is not room or (not d['fx'] and not d['cheer']):
            return
        r, d['fx'] = d['fx'], {}
        room.send(dict(t='kara_fx', id=room.id, r=r, cheer=round(d['cheer'])))

    @on('kara_react', rate=(3, 1.0))
    async def kara_react(self, conn, f):
        room, m = self._mine(conn)
        k = f.get('k')
        if k not in REACTS:
            raise LiveError('bad', 'Không có biểu cảm này.')
        if not conn.player.account:
            raise LiveError('account', 'Tạo tài khoản để thả tim nhé.')
        d = room.data
        d['fx'][k] = d['fx'].get(k, 0) + 1
        if d['stage'] is not None and d['phase'] in ('deck', 'play'):
            d['hearts'] += 1
        self._fx_soon(room)
        return None

    @on('kara_cheer', rate=(5, 1.0))
    async def kara_cheer(self, conn, f):
        room, m = self._mine(conn)
        if not conn.player.account:
            return None
        d = room.data
        d['cheer'] = min(100.0, d['cheer'] + CHEER_STEP)
        if d['stage'] is not None and d['phase'] in ('deck', 'play'):
            d['cheers'] += 1
        self._fx_soon(room)
        return None

    # ---- bubbles and guesses ----------------------------------------------------------------------------
    @on('kara_say', rate=(4, 5))
    async def kara_say(self, conn, f):
        room, m = self._mine(conn)
        p = conn.player
        self._need_account(p, 'nhắn trong phòng')
        text = f.get('text')
        d = room.data
        rd = d['round']
        if rd and not rd['done'] and p.pid != rd['host'] and isinstance(text, str) and len(text) <= SAY_LEN:
            hit = KG.match(text, rd['keys'])
            if hit == 'yes':
                await self._win(room, rd, m)
                return dict(t='kara_said', id=room.id, win=1)
            if hit == 'near':
                self.hub.send(conn, dict(t='kara_near', id=room.id, rid=rd['id']))
        frame = await self.app.chat.store_message(p, room.id, text, SAY_LEN, 1)
        if self.hub.rooms.get(room.id) is room and p.pid in room.data['people']:
            self._send_from(room, dict(t='kara_said', ch=room.id, pid=p.pid, name=m.name, id=frame['id'], text=frame['text'], at=frame['at']), p.pid)
        return None

    @on('kara_round', rate=(4, 600))
    async def kara_round(self, conn, f):
        room, m = self._mine(conn)
        p = conn.player
        self._need_account(p, 'đố bài')
        if not p.name:
            raise LiveError('name', 'Đặt tên nhân vật trước nhé.')
        d = room.data
        now = time.time()
        if d['round'] is not None:
            raise LiveError('busy', 'Đang có câu đố rồi, đoán cùng mọi người nhé.')
        last = p.ext.get('kara_round_at', 0.0)
        if now - last < GUESS_GAP:
            raise LiveError('slow', 'Nghỉ chút rồi đố tiếp nha.', wait=round(GUESS_GAP - (now - last), 1))
        try:
            clue = KG.check_clue(f.get('mode'), f.get('clue'))
        except KG.KaraError as e:
            raise LiveError(e.code, e.message) from None
        keys = KG.answers(f.get('answer'))
        if not keys:
            raise LiveError('bad_answer', f'Đáp án từ 2 tới {KG.ANSWER_LEN} ký tự nhé.')
        shown = filters.mask(filters.clean(str(f.get('answer')).split('/')[0], KG.ANSWER_LEN, 1) or keys[0])
        vid, title = None, ''
        if f.get('vid'):
            vid = KG.parse_vid(f.get('vid'))
            song = await self.db.fetchrow('SELECT title, ok, banned FROM kara_songs WHERE vid=?', (vid,)) if vid else None
            if not song or int(song['banned']) or not int(song['ok']):
                raise LiveError('song', 'Link thưởng chưa kiểm tra được. Bấm Kiểm tra trước nhé.')
            title = filters.mask(str(song['title'] or ''))[:KG.TITLE_LEN]
        if d['round'] is not None or self.hub.rooms.get(room.id) is not room:
            raise LiveError('busy', 'Đang có câu đố rồi, đoán cùng mọi người nhé.')
        p.ext['kara_round_at'] = now
        rd = dict(id=f'{int(now * 1000):x}{secrets.token_hex(2)}', host=p.pid, sid=p.sid, name=m.name, mode=f.get('mode'), clue=clue,
                  keys=keys, answer=shown, words=KG.answer_words(keys), at=now, until=now + GUESS_SECS, vid=vid, title=title, done=False)
        d['round'] = rd
        self.rounds += 1
        self._send_from(room, dict(t='kara_round', id=room.id, round=self._round(d)), p.pid)
        return None

    @on('kara_round_end', rate=(6, 60))
    async def kara_round_end(self, conn, f):
        room, m = self._mine(conn)
        rd = room.data['round']
        if rd is None:
            return None
        if rd['host'] != m.pid and not self._admin(conn.player):
            raise LiveError('bad', 'Chỉ người đố kết thúc được.')
        self._reveal(room, None, 'host' if rd['host'] == m.pid else 'admin')
        return None

    async def _win(self, room, rd: dict, m: Member) -> None:
        rd['done'] = True   # before any await: one winner
        now = time.time()
        xu = 0
        if now - rd['at'] >= GUESS_MIN_SECS:
            try:
                xu = await self._prize(rd, m.player)
            except DbError as e:
                log('karaoke prize:', type(e).__name__)
        self._reveal(room, m, 'won', xu)
        if xu:
            self.wins += 1
            self.hub.send_many(self.hub.conns_of(m.pid), dict(t='kara_won', id=room.id, xu=xu))

    async def _prize(self, rd: dict, p) -> int:
        start = KG.day_start()
        n = int(await self.db.fetchval('SELECT COUNT(*) FROM live_effects WHERE id LIKE ? AND at>=?', (f'kguess:{rd["host"]}:%', start)) or 0)
        if n >= KG.GUESS_HOST_DAY:
            return 0
        ok = await effects.grant(self.db, p.sid, 'coins', KG.GUESS_XU, f'kguess:{rd["host"]}:{rd["id"]}', dict(src='kara_guess'),
                                 cap=KG.GUESS_DAY_CAP, cap_like='kguess:%')
        return KG.GUESS_XU if ok else 0

    def _reveal(self, room, winner: Member | None, why: str, xu: int = 0) -> None:
        d = room.data
        rd = d['round']
        if rd is None:
            return
        rd['done'] = True
        d['round'] = None
        frame = dict(t='kara_reveal', id=room.id, rid=rd['id'], answer=rd['answer'], clue=rd['clue'], mode=rd['mode'], why=why, xu=xu,
                     by=dict(pid=winner.pid, name=winner.name) if winner else None, vid=rd['vid'], title=rd['title'])
        self._send_from(room, frame, rd['host'])
        if rd['vid'] and len(d['queue']) < QUEUE_MAX + 2:   # the host's link plays next, as the round's reward
            d['queue'].insert(0, Entry('r-' + rd['id'], rd['vid'], rd['title'] or 'Bài hát YouTube', rd['host'], rd['sid'], rd['name'], reward=True))
            self._tell_queue(room)
            self._advance(room, time.time())

    # ---- 🎙️ the live mic ---------------------------------------------------------------------------------
    def _split(self, a: str, b: str) -> bool:
        """True when either of two players blocked the other."""
        return b in self._hidden_of(a) or a in self._hidden_of(b)

    @staticmethod
    def _new_mic(st: Entry, name: str, now: float, cut: str | None = None) -> dict:
        return dict(e=st.e, pid=st.pid, name=name, n=0, sfu='', on=False, busy=False, cut=cut, until=now + KM.MIC_SECS,
                    subs=set(), reports=set(), vt_at=0.0)

    def _song_mic(self, d) -> dict | None:
        """The mic session of the song on stage (None: not turned on yet, or the dict is an older song's)."""
        st, mic = d['stage'], d.get('mic')
        return mic if st is not None and mic is not None and mic['e'] == st.e else None

    def _my_stage(self, room, p) -> Entry:
        d = room.data
        st = d['stage']
        if st is None or st.pid != p.pid or d['phase'] not in ('deck', 'play') or p.pid not in d['people']:
            raise LiveError('stage', 'Chỉ người đang trên sân khấu mới bật mic được.')
        return st

    def _mic_view(self, room, mic: dict) -> dict:
        return dict(t='kara_live', id=room.id, on=1, e=mic['e'], by=dict(pid=mic['pid'], name=mic['name']), until=round(mic['until'], 3))

    def _mic_token(self, room, mic: dict, m: Member, now: float) -> dict:
        return dict(t='kara_mic', id=room.id, on=1, e=mic['e'], url=self.sfu.url, room=mic['sfu'], until=round(mic['until'], 3),
                    token=self.sfu.token(m.pid, m.name, mic['sfu'], publish=True, ttl=mic['until'] - now + 30, now=now))

    def _mic_off(self, room, why: str, cut: bool = False) -> None:
        """The mic goes off: its SFU room is deleted (the singer and every listener disconnected at once). `cut`: not
        again for the rest of this song."""
        mic = room.data.get('mic')
        if mic is None:
            return
        if cut and mic['cut'] is None:
            mic['cut'] = why
        if not mic['on']:
            return
        mic['on'] = False
        name, mic['subs'] = mic['sfu'], set()
        self.spawn(self.sfu.delete_room(name))
        room.send(dict(t='kara_live', id=room.id, on=0, e=mic['e'], why=why))

    def _mic_ban(self, room, why: str) -> None:
        """An admin cut: the mic goes off and stays off for this song, even if it was not on yet."""
        d = room.data
        st = d['stage']
        if st is not None and self._song_mic(d) is None and d['phase'] in ('deck', 'play'):
            d['mic'] = self._new_mic(st, st.name, time.time(), cut=why)
        self._mic_off(room, why, cut=True)

    def _mic_blocks(self, room, mic: dict) -> None:
        """A block made while the mic is on: that listener leaves the SFU room."""
        for pid in [x for x in mic['subs'] if self._split(mic['pid'], x)]:
            mic['subs'].discard(pid)
            self.spawn(self.sfu.remove(mic['sfu'], pid))
            self.hub.send_many(self.hub.conns_of(pid), dict(t='kara_listen', id=room.id, on=0, e=mic['e']))

    MIC_NO = dict(cut='Mic của bài này đã bị tắt.', time=f'Hết {KM.MIC_SECS // 60} phút mic của bài này rồi.', busy='Đang bật mic, chờ chút nhé.')

    @on('kara_mic', rate=(10, 60))
    async def kara_mic(self, conn, f):
        room, m = self._mine(conn)
        if not self._mic_on():
            raise LiveError('off', 'Mic trực tiếp chưa mở.')
        d, p = room.data, conn.player
        if not f.get('on'):
            mic = self._song_mic(d)
            if mic is not None and mic['pid'] == p.pid:
                self._mic_off(room, 'off')
            return dict(t='kara_mic', id=room.id, on=0)
        st = self._my_stage(room, p)
        self._need_account(p, 'hát trực tiếp')

        def ready(mic, now):
            """None when a new session may start; else a reply (the session on now) or a refusal."""
            if mic is None:
                return None
            if mic['cut']:
                raise LiveError('cut', self.MIC_NO['cut'])
            if now >= mic['until']:
                raise LiveError('time', self.MIC_NO['time'])
            if mic['on']:   # the singer's page lost the SFU and asks again: a fresh token for the same session
                return self._mic_token(room, mic, m, now)
            if mic['busy']:
                raise LiveError('busy', self.MIC_NO['busy'])
            return None
        out = ready(self._song_mic(d), time.time())
        if out:
            return out
        try:
            row = await self.db.fetchrow('SELECT a.created_at, b.year FROM accounts a LEFT JOIN account_birth b ON b.sid=a.sid WHERE a.sid=?', (p.sid,))
        except DbError as e:
            log('karaoke mic:', type(e).__name__)
            raise LiveError('busy', 'Máy chủ đang bận, thử lại nhé.') from None
        if not row:
            raise LiveError('account', 'Tạo tài khoản để hát trực tiếp nhé.')
        if row['year'] is None:
            raise LiveError('birth', 'Cho Phòng hát biết năm sinh của bạn trước khi mở mic nhé.')
        if not KM.age_ok(int(row['year'])):
            raise LiveError('young', f'Mic trực tiếp dành cho bạn từ {KM.MIN_AGE} tuổi. Bạn vẫn nghe và cổ vũ mọi người được nha 🎧')
        if not KM.account_old_enough(row['created_at']) and not self._admin(p):
            raise LiveError('too_new', f'Mic trực tiếp mở khi tài khoản đủ {KM.MIC_ACCOUNT_DAYS} ngày nhé.')
        now = time.time()
        st = self._my_stage(room, p)   # again: the song may have ended meanwhile
        mic = self._song_mic(d)
        out = ready(mic, now)
        if out:
            return out
        if mic is None:
            mic = d['mic'] = self._new_mic(st, m.name, now)
        mic['busy'] = True
        try:
            mic['n'] += 1
            name = room_name(room.id, st.e, mic['n'])
            ok = await self.sfu.create_room(name, ROOM_CAP + 10)
        finally:
            mic['busy'] = False
        if not ok:
            raise LiveError('sfu', 'Mic đang bận, thử lại sau ít phút nhé.')
        if (d.get('mic') is not mic or mic['cut'] or mic['on'] or self.hub.rooms.get(room.id) is not room or d['stage'] is not st
                or d['phase'] not in ('deck', 'play') or p.pid not in d['people'] or time.time() >= mic['until']):
            self.spawn(self.sfu.delete_room(name))
            raise LiveError('gone', 'Bài này đã xong rồi.')
        mic.update(sfu=name, on=True, subs=set())
        self.mics += 1
        room.send(self._mic_view(room, mic))
        return self._mic_token(room, mic, m, time.time())

    @on('kara_listen', rate=(20, 60))
    async def kara_listen(self, conn, f):
        """A listening token for the mic on now: subscribe only, hidden, LISTEN_TTL seconds to join. Nothing for the
        singer, for anyone the singer blocked or who blocked them (and nothing says why), or when it is off."""
        room, m = self._mine(conn)
        d = room.data
        mic = self._song_mic(d)
        if not self._mic_on() or mic is None or not mic['on'] or m.pid == mic['pid'] or self._split(mic['pid'], m.pid):
            return dict(t='kara_listen', id=room.id, on=0)
        mic['subs'].add(m.pid)
        return dict(t='kara_listen', id=room.id, on=1, e=mic['e'], url=self.sfu.url, room=mic['sfu'],
                    token=self.sfu.token(m.pid, m.name, mic['sfu'], publish=False, ttl=KM.LISTEN_TTL))

    @on('kara_vt', rate=(4, 3.0))
    async def kara_vt(self, conn, f):
        """🎙️ Voice and music together ("bị delay xíu", 07/10): while the mic is on, the singer's page sends its own
        video time about once a second (`vt`, seconds into the song; `st`, its server-clock reading of that moment;
        `r`, its playback rate while its own sync nudges it; `rtt`, its media path's round trip in ms). Only the stage singer of the live mic, a number near the shared
        clock (VT_SPAN), at most one every VT_GAP seconds. Relayed, stamped with `at` (server time of `vt`: the
        singer's `st` when it is no more than VT_BACK old, else now), to the mic's listeners in this room (blocks
        respected); a listener's video then follows the singer's minus the voice's delay. Anything else is dropped
        without a word (an older page never sends it; an older service answers 'unknown', which the page ignores)."""
        room, m = self._mine(conn)
        d = room.data
        mic = self._song_mic(d)
        if mic is None or not mic['on'] or mic['pid'] != m.pid or f.get('e') != mic['e'] or d['phase'] not in ('deck', 'play'):
            return None
        vt, st, r, rtt = f.get('vt'), f.get('st'), f.get('r'), f.get('rtt')
        if type(vt) not in (int, float) or not math.isfinite(vt) or not 0 <= vt <= DUR_MAX + VT_SPAN:
            return None
        now = time.time()
        if abs(vt - (now - d['at'])) > VT_SPAN or now - mic['vt_at'] < VT_GAP:
            return None
        mic['vt_at'] = now
        at = min(now, max(now - VT_BACK, float(st))) if type(st) in (int, float) and math.isfinite(st) else now
        frame = dict(t='kara_vt', id=room.id, e=mic['e'], vt=round(float(vt), 3), at=round(at, 3))
        if type(rtt) in (int, float) and math.isfinite(rtt) and 0 <= rtt <= VT_RTT_MAX:
            frame['rtt'] = int(rtt)
        if type(r) in (int, float) and math.isfinite(r) and VT_RATE[0] <= r <= VT_RATE[1] and r != 1:
            frame['r'] = round(float(r), 3)
        subs = mic['subs']
        self.hub.send_many([c for c in room.conns if c is not conn and c.player.pid in subs and not self._split(m.pid, c.player.pid)], frame)
        return None

    @on('kara_mic_cut', rate=(20, 60))
    async def kara_mic_cut(self, conn, f):
        room, _ = self._mine(conn)
        self._need_admin(conn.player)
        self._mic_ban(room, 'admin')
        return None

    # ---- reports -------------------------------------------------------------------------------------------
    @on('kara_report', rate=(10, 3600))
    async def kara_report(self, conn, f):
        room, m = self._mine(conn)
        p = conn.player
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để báo cáo nhé.')
        reason = f.get('reason', 'other')
        if reason not in REASONS:
            raise LiveError('bad', 'Báo cáo không hợp lệ.')
        d = room.data
        pid, vid = f.get('pid'), f.get('vid')
        entries = ([d['stage']] if d['stage'] else []) + d['queue']
        if isinstance(pid, str) and pid != p.pid and (pid in d['people'] or any(e.pid == pid for e in entries) or (d['round'] and d['round']['host'] == pid)):
            target = 'p:' + pid
        elif isinstance(vid, str) and any(e.vid == vid for e in entries):
            target = 'v:' + vid
        else:
            raise LiveError('bad', 'Không tìm thấy mục để báo cáo.')
        mic = self._song_mic(d)
        live = mic is not None and mic['on'] and target == 'p:' + mic['pid']
        if live:   # 🎙️ about the live voice: the admin queue shows it as such ('m:<pid>')
            target = 'm:' + mic['pid']
        await self.db.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'kara', ?, ?, ?) "
                              'ON CONFLICT(reporter, kind, target) DO NOTHING', (p.pid, target, reason, time.time()))
        if live and mic['on'] and self.hub.rooms.get(room.id) is room:   # 🎙️ reports of the live singer cut the mic
            mic['reports'].add(p.pid)
            if len(mic['reports']) >= KM.MIC_REPORTS:
                self._mic_off(room, 'reports', cut=True)
        return dict(t='kara_reported', target=target)

    # ---- admins ------------------------------------------------------------------------------------------
    def _need_admin(self, p) -> None:
        if not self._admin(p):
            raise LiveError('admin', 'Chỉ Ban quản lý làm được.')

    @on('kara_kick', rate=(20, 60))
    async def kara_kick(self, conn, f):
        self._mine(conn)
        self._need_admin(conn.player)
        pid = f.get('pid')
        if not isinstance(pid, str) or not KG.PID_RX.fullmatch(pid) or pid == conn.player.pid:
            raise LiveError('bad', 'Người chơi không hợp lệ.')
        self.kick(pid)
        return None

    @on('kara_close', rate=(20, 60))
    async def kara_close(self, conn, f):
        room, _ = self._mine(conn)
        self._need_admin(conn.player)
        self.close(room.id)
        return None

    @on('kara_ban', rate=(20, 60))
    async def kara_ban(self, conn, f):
        self._mine(conn)
        p = conn.player
        self._need_admin(p)
        vid = f.get('vid')
        if not isinstance(vid, str) or not KG.VID_RX.fullmatch(vid):
            raise LiveError('bad', 'Mã bài không hợp lệ.')
        t = time.time()
        await self.db.execute("INSERT INTO kara_songs(vid, title, channel, ok, why, checked_at, banned, banned_by, banned_at) VALUES(?, '', '', 0, '', 0, 1, ?, ?) "
                              'ON CONFLICT(vid) DO UPDATE SET banned=1, banned_by=excluded.banned_by, banned_at=excluded.banned_at',
                              (vid, (getattr(p, 'username', '') or 'admin')[:40], t))
        self.ban(vid)
        return dict(t='kara_banned', vid=vid)

    def kick(self, pid: str) -> None:
        self.kicked.put(pid, time.time() + KICK_SECS)
        p = self.hub.players.get(pid)
        for room in self._rooms():
            self._drop_player(room, pid, end_why='admin')
        if p is not None:
            self._leave(p, 'kick')

    def close(self, rid: str) -> None:
        self.closed[rid] = time.time() + CLOSE_SECS
        if len(self.closed) > 64:
            now = time.time()
            self.closed = {k: v for k, v in self.closed.items() if v > now}
        room = self.hub.rooms.get(rid)
        if room is None:
            return
        self._mic_off(room, 'closed', cut=True)
        for pid in list(room.data['people']):
            p = self.hub.players.get(pid)
            if p is not None and p.ext.get('kara') == rid:
                self._leave(p, 'closed')
        if self.hub.rooms.get(rid) is room:
            self.hub.drop_room(rid)

    def ban(self, vid: str) -> None:
        now = time.time()
        for room in self._rooms():
            d = room.data
            n = len(d['queue'])
            d['queue'] = [e for e in d['queue'] if e.vid != vid]
            if len(d['queue']) != n:
                self._tell_queue(room)
            if d['stage'] is not None and d['stage'].vid == vid:
                self._end(room, 'admin', now)

    def _drop_player(self, room, pid: str, end_why: str) -> None:
        """A muted or kicked player: their songs out of the queue, their song and their round ended."""
        d = room.data
        n = len(d['queue'])
        d['queue'] = [e for e in d['queue'] if e.pid != pid or e.reward]
        if len(d['queue']) != n:
            self._tell_queue(room)
        if d['stage'] is not None and d['stage'].pid == pid and not d['stage'].reward:
            self._end(room, end_why, time.time())
        if d['round'] and d['round']['host'] == pid:
            self._reveal(room, None, 'admin')

    async def on_notify(self, e: dict):
        op = e.get('op')
        if op == 'mute' and isinstance(e.get('pid'), str) and float(e.get('until') or 0) > time.time():
            for room in self._rooms():
                self._drop_player(room, e['pid'], 'admin')
        elif op == 'face' and isinstance(e.get('pid'), str):   # a player deleted their data
            for room in self._rooms():
                self._drop_player(room, e['pid'], 'admin')
        elif op == 'kara_tip' and isinstance(e.get('e'), str):
            for room in self._rooms():
                d = room.data
                st = d['stage']
                if st is not None and st.e == e['e']:
                    xu = int(e.get('xu') or 0)
                    d['tips'] += xu
                    self._send_from(room, dict(t='kara_tipped', id=room.id, e=st.e, frm=dict(pid=e.get('frm'), name=str(e.get('name') or '')[:24]), xu=xu,
                                               tips=d['tips']), e.get('frm') if isinstance(e.get('frm'), str) else None)
        elif op == 'kara':
            act = e.get('act')
            rid, pid, vid = e.get('room'), e.get('pid'), e.get('vid')
            room = self.hub.rooms.get(rid) if isinstance(rid, str) and parse_room(rid) else None
            if act == 'skip' and room is not None:
                self._end(room, 'admin', time.time())
            elif act == 'close' and isinstance(rid, str) and parse_room(rid):
                self.close(rid)
            elif act == 'end_round' and room is not None:
                self._reveal(room, None, 'admin')
            elif act == 'kick' and isinstance(pid, str) and KG.PID_RX.fullmatch(pid):
                self.kick(pid)
            elif act == 'ban' and isinstance(vid, str) and KG.VID_RX.fullmatch(vid):
                self.ban(vid)
            elif act == 'mic' and room is not None:   # 🎙️ the admin site cut the room's live mic
                self._mic_ban(room, 'admin')

    # ---- every second ------------------------------------------------------------------------------------
    async def tick(self, now: float):
        for room in self._rooms():
            d = room.data
            if not d.get('people') and not room.conns:   # opened by a join that did not happen
                self._mic_off(room, 'empty', cut=True)
                self.hub.drop_room(room.id)
                continue
            mic = d.get('mic')
            if mic is not None and mic['on']:
                if now >= mic['until']:
                    self._mic_off(room, 'time', cut=True)
                else:
                    self._mic_blocks(room, mic)
            if d['phase'] == 'deck' and now >= d['at']:
                d['phase'] = 'play'
            if d['phase'] == 'play' and now >= d['at'] + d['dur']:
                self._end(room, 'cut' if d['dur'] >= DUR_MAX and max(d['durs'].values(), default=0) > DUR_MAX else 'done', now)
            elif d['phase'] == 'clap' and now >= d['until']:
                d.update(phase='idle', stage=None, votes=set())
                self._tell_stage(room)
            if d['phase'] == 'idle' and d['queue']:
                self._advance(room, now)
            rd = d['round']
            if rd is not None and now >= rd['until']:
                self._reveal(room, None, 'time')
            if d['cheer'] > 0:
                d['cheer'] = max(0.0, d['cheer'] - CHEER_DECAY)
                self._fx_soon(room)

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
            log('karaoke db:', type(e).__name__, e)
        except Exception as e:  # noqa: BLE001
            log('karaoke:', type(e).__name__, e)

    def stats(self) -> dict:
        rooms = self._rooms()
        return dict(kara_rooms=len(rooms), kara_people=sum(len(r.data.get('people') or {}) for r in rooms), kara_plays=self.plays,
                    kara_rounds=self.rounds, kara_wins=self.wins, kara_mics=self.mics,
                    kara_live=sum(1 for r in rooms if (r.data.get('mic') or {}).get('on')), kara_sfu_fails=self.sfu.fails)
