"""💬 Chat (switch LIVE_CHAT): friend DMs, groups, "Cả phố", presence, unread, reports, blocks, mutes.

Channels
* `town` (Cả phố): everyone with a session reads it while it is on their screen (`join`/`leave`); posting
  needs a name, a session older than 10 minutes, and waits 10 s between two messages (slow mode).
* `dm:<pidA>:<pidB>` (pids sorted): two friends (`friends` both ways, no block either way). Created by the
  first `send {to: pid}`. A friend with no socket gets one web push per chat per 10 minutes at most.
* `g:<10 hex>`: a group made by its owner from their friends, at most 20 members; the owner adds and removes,
  anyone leaves (the oldest member becomes owner when the owner leaves). Members with no socket get the same
  web push as a DM (since 1.2.4, feedback #66).

🔔 Notifications per chat (feedback #66): `notify {ch, v}` with v 'on', '8h' or 'off' sets chat_members.muted_until
(0 = on, a time = quiet until then, QUIET_FOREVER = off; the column is there since schema 6, nothing else used it).
A quiet chat gets no web push; messages still arrive and its unread count still shows in the list, but the client
leaves it out of the badges (live.unread). The chat list (`state.chans`) carries `quiet` (until) for quiet chats.

Frames (client → server; replies in brackets)
  sync {}                                   [state {friends, chans}]
  join {ch:'town', after?}  leave {ch}      [joined {ch, msgs, more, wait, why}]
  send {ch | to, text, cid, reply_to?}      [msg {..., cid, reply?} to me; msg to the others]
  history {ch, before?}                     [history {ch, msgs, more}]
  read {ch, id}                             [read {ch, id} to my other tabs]
  del {id}                                  [deleted {ch, id} to everyone who sees it]
  report {id, reason}  block {pid}  unblock {pid}
  prefs {online: bool}                      [prefs {online}]
  group_new {title, pids}  group_add {ch, pids}  group_kick {ch, pid}  group_leave {ch}  members {ch}
  pin {id}  unpin {}                        [pinned {ch:'town', pin} to everyone on Cả phố]   admins only
  react {id, e}                             [reacts {ch, id, r, by, e} to everyone who sees the chat]
  notify {ch, v:'on'|'8h'|'off'}            [quiet {ch, until} to my tabs]
  face {fc}                                 [faced {pid, fc} to my tabs, Cả phố and my online friends]
  hide {id}                                 [hid {ch, id} to my tabs]                   🗑️ when welcome.flags.chatdel
  clear {chs: [ch, ...]}                    [cleared {chs: {ch: upto}} to my tabs]
  blocks {}                                 [blocks {list: [{pid, name, av, fc?}]}]     🚫 when welcome.flags.blocks
Server pushes: msg, deleted, presence {pid, on}, chan {chan}, unchan {ch}, muted {until}, read, pinned, reacts, quiet, faced.

Replies store only a source ID. Each output resolves it to reply={id,pid,name,text} (160 characters), or
{id,unavailable:true}, using current source visibility for that reader. Buffer and pin caches never retain
quoted text. reply_hidden {pid} invalidates already displayed quotes after a bilateral block or account erasure.

🗑️ Deleting (owner, 03/10: "nhấn giữ để xóa tin nhắn", "bạn bè cho chọn xóa tin nhắn, xóa hết ở màn list"):
* `del {id}` (Thu hồi): my own message, for everyone, within RECALL_SECS (24 h; admins any time). The row stays as a
  tombstone (deleted=1, text emptied, shown as "Tin nhắn đã thu hồi"); a message somebody already reported keeps what
  was written in `raw`, for the admin who reviews the report.
* `hide {id}` (Xóa ở phía tôi): any message of Cả phố, a DM or a group leaves MY screens only (`chat_hides`).
* `clear {chs}` (the chat list, "Chọn" → Xóa): whole DMs / groups emptied for me only, up to their newest message
  (`chat_clears`; they count as read). A DM I emptied leaves my list until a new message comes; a group stays.
Pages (joined, history, missed) and the chat list leave those out for me; nobody else's view changes and the admin
screens still show every message. Hidden ids are read for a page by primary key, and only for a player who ever hid
one (p.ext['hides']); the clear marks of a chat ride with its members (Chan.cleared). The two tables come with
SCHEMA_VERSION 13 from the game server: until they exist this service runs without them (welcome.flags.chatdel false,
`hide`/`clear` answer 'off', looked for again every DEL_POLL s), so the game server and this service roll out in any order.

🙂 Faces (owner, 02/10: "avatar cho mọi người chat… chỉnh được áo quần thì sẽ có ở đó luôn"): a player's drawn chat
avatar with the clothes they wear, as a small code of whitelisted ids (live/faces.py; built by the client from the save,
public/js/v4/face-code.js). It comes with `hello {fc}` and `face {fc}` (only once the welcome's `me` has an `fc` key: an
older service never gets a frame it does not know), is kept per player in `chat_faces` (this service is its only
writer, so the in-memory cache is the truth) and goes out as `fc` beside `av`: on live messages, on the messages of a
page (joined, history, missed: the author's face NOW, so a change of clothes shows on the old lines too), on friends,
DM peers, members and `me`. A frame without `fc` (an older service, a player who keeps an emoji) shows `av` as
before; an older client ignores `fc` and `faced`.

😍 Reactions (owner, 01/10: "nhấn giữ là reaction"): one of REACTS per player per message (`chat_reacts`, primary key
(msg, pid)) in Cả phố, DMs and groups. `react {id, e}` sets e; the same e again (or e null) takes it back; another
replaces it. Not on a hidden or deleted message, not by a muted player or a guest, DMs and groups only for their
members. Counts go out as `reacts {ch, id, r: {emoji: n}, by, e}` (by: who, e: their reaction now); messages sent
in pages (joined, history, missed) carry `r` and `my` (my own). Counts are cached in memory per message (LRU, filled
by one grouped query over the page's ids, the primary key); `my` is read only for messages that have reactions.

📌 Admins (owner, 01/10): an account whose username is in ADMIN_USERS (cfg.admins, read from `accounts` with the
player's name and age) posts on Cả phố with no slow mode, no "new player" wait and no mute, up
to 500 characters and 6 lines, links and numbers left as written; their frames carry `adm: 1` (column
chat_messages.adm; a row with pid 'admin', written straight into the database, counts as one too). Nobody can
report an admin message. An admin pins one Cả phố message for everyone (`chat_pins`, one row): the `joined` frame
carries `pin` (the message frame or null) and a change goes out as `pinned`. The pin goes away with its message
(deleted, hidden, a player's data deleted); pruning never removes it. scripts/chat_pin.py pins from the server; the
service reads the pin row (one primary-key lookup) every 30 s, and at once on a NOTIFY {op: 'pin'}.

Phase 2/3 reuse store_message() for anything players type (bubbles, date chat) and route() so deletes,
reports and admin hides reach their rooms.
"""
from __future__ import annotations

import asyncio
import re
import secrets
import time

from . import faces as facemod
from . import filters
from . import chat_reply
from . import player_names
from .auth import pid_of, profile
from .db import Error as DbError
from .limits import LRU
from .protocol import Feature, LiveError, on
from .push import maybe_push

CH_DM = re.compile(r'dm:([0-9a-f]{16}):([0-9a-f]{16})')
CH_GROUP = re.compile(r'g:[0-9a-f]{10}')
PID = re.compile(r'[0-9a-f]{16}')
REASONS = ('spam', 'rude', 'private', 'scam', 'other')
HIDE_AFTER = 3            # distinct reports that hide a message until an admin decides
PAGE = 30                 # messages per load: the first one and each "Xem cũ hơn" (owner, 01/10)
RESUME = 50               # messages sent after a reconnect, per open chat
TOWN_KEEP = 2000          # Cả phố keeps its newest 2,000 messages (owner, 01/10); DMs and groups keep everything
PRUNE_EVERY = 300         # seconds between two prunings of Cả phố
PRUNE_BATCH = 500         # rows per batch, at most 5 batches per pruning
TITLE_LEN = 40
GROUPS_OWNED = 20
CHANS_LISTED = 100
FRIENDS_MAX = 200
PUSH_EVERY = 600          # seconds between two pushes of one chat to one player
QUIET_FOREVER = 4102444800.0   # chat_members.muted_until of a chat whose notifications are off (2100-01-01)
QUIET_HOURS = 8           # "Tắt 8 giờ"
PIN_POLL = 30             # seconds between two reads of the pin row (a pin written from outside: scripts/chat_pin.py)
ADMIN_PID = 'admin'       # rows written straight into the database by the operator (an announcement): admin messages
REACTS = ('❤️', '😂', '😮', '😢', '👍', '🔥')   # the long-press bar, in this order
REACT_CACHE = 20000       # messages whose reaction counts are kept in memory
FACE_CACHE = 20000        # 🙂 players whose face code is kept in memory
RECALL_SECS = 86400       # 🗑️ a message can be taken back (Thu hồi) for 24 hours
CLEAR_MAX = 20            # 🗑️ chats emptied by one `clear`
BLOCKS_LISTED = 50        # 🚫 people listed under "Đã chặn"
DEL_POLL = 60             # 🗑️ seconds between two looks for the tables of "xóa ở phía tôi" while they are missing


def dm_id(a: str, b: str) -> str:
    x, y = sorted((a, b))
    return f'dm:{x}:{y}'


def kind_of(ch: str) -> str:
    if ch == 'town':
        return 'town'
    if CH_DM.fullmatch(ch):
        return 'dm'
    if CH_GROUP.fullmatch(ch):
        return 'group'
    return ch.split(':', 1)[0]


class Chan:
    __slots__ = ('id', 'kind', 'title', 'owner', 'members', 'quiet', 'cleared')

    def __init__(self, cid, kind, title='', owner=None, members=None, quiet=None, cleared=None):
        self.id, self.kind, self.title, self.owner = cid, kind, title, owner
        self.members: dict = members if members is not None else {}   # pid -> sid (dm, group)
        self.quiet: dict = quiet if quiet is not None else {}         # pid -> muted_until (🔔 notifications off until)
        self.cleared: dict = cleared if cleared is not None else {}   # pid -> 🗑️ emptied for them up to this id


def msg_frame(r: dict) -> dict:
    f = dict(t='msg', ch=r['channel'], id=int(r['id']), pid=r['pid'], name=r['name'], av=r['av'], text=r['text'], at=round(float(r['at']), 3))
    if r.get('adm') or r['pid'] == ADMIN_PID:
        f['adm'] = 1
    if r.get('deleted'):
        f['text'], f['del'] = '', 1
    elif r.get('reply_to'):
        f['reply_to'] = int(r['reply_to'])  # internal only; resolve for each viewer at the output boundary
    return f


class ChatFeature(Feature):
    name, flag = 'chat', 'chat'

    def __init__(self, app):
        super().__init__(app)
        self.chans = LRU(5000)
        self.town = self.hub.room('town', buffer=self.cfg.buffer)
        self.town_more = False         # older Cả phố messages exist in the database
        self.routes: dict = {}         # channel prefix -> (audience(ch) -> rooms, can_read(player, ch) -> bool)
        self.tasks: set = set()
        self.pin: dict | None = None   # 📌 the pinned Cả phố message (its frame, without `t`), or None
        self.pin_key = None            # (message id, pinned at) of that pin: what the 30 s poll compares
        self._pin_at = 0.0             # next poll of the pin row
        self.reacts = LRU(REACT_CACHE)  # 😍 message id -> {emoji: count} ({} = none), the only writer is this service
        self.push_tried = LRU(20000)    # 🔔 (channel, pid) -> last push attempt: no database write per message
        self.faces = LRU(FACE_CACHE)    # 🙂 pid -> face code ('' = none, shows the emoji)
        self.del_ok = False             # 🗑️ chat_hides / chat_clears exist (SCHEMA_VERSION 13)
        self._del_at = 0.0              # next look for them while they are missing
        self.reply_epoch = 0            # invalidates quote SELECTs already in flight
        self.names = LRU(20000)         # pid -> current account display; '' means keep a guest/system snapshot

    # ---- extension: other features' channels -------------------------------------------------------------
    def route(self, prefix: str, audience, can_read) -> None:
        """Phase 2/3: messages of channels starting with `prefix` (e.g. 'street:') live in the rooms
        audience(ch) returns; can_read(player, ch) guards history and reports."""
        self.routes[prefix] = (audience, can_read)

    def _route(self, ch: str):
        for prefix, r in self.routes.items():
            if ch.startswith(prefix):
                return r
        return None

    # ---- start -----------------------------------------------------------------------------------------------
    async def start(self):
        await self.db.execute("INSERT INTO chat_channels(id, kind, title, owner_pid, created) VALUES('town', 'town', 'Cả phố', NULL, ?) "
                              'ON CONFLICT(id) DO NOTHING', (time.time(),))
        rows = await self.db.fetch("SELECT * FROM chat_messages WHERE channel='town' AND hidden=0 ORDER BY id DESC LIMIT ?", (self.cfg.buffer + 1,))
        self.town_more = len(rows) > self.cfg.buffer
        for r in reversed(rows[:self.cfg.buffer]):
            self.town.buffer.append(msg_frame(r))
        await self.sync_pin(announce=False)
        self._pin_at = time.time() + PIN_POLL   # just read: the next look in 30 s
        await self.check_del()

    async def check_del(self) -> bool:
        """🗑️ Are the tables of "xóa ở phía tôi" there (a game server of SCHEMA_VERSION 13 has started)? Sets
        welcome.flags.chatdel; never waits for them (an older database: the rest of the chat works as before)."""
        try:
            await self.db.fetchval('SELECT 1 FROM chat_hides LIMIT 1')
            await self.db.fetchval('SELECT 1 FROM chat_clears LIMIT 1')
            ok = True
        except DbError:
            ok = False
        if ok and not self.del_ok:
            self.chans.clear()   # chats read before carry no clear marks
        self.del_ok = ok
        self.cfg.flags_extra['chatdel'] = bool(ok and self.cfg.chat)
        self.cfg.flags_extra['blocks'] = bool(self.cfg.chat)   # 🚫 `blocks` (the list to unblock from) is answered
        self._del_at = time.time() + DEL_POLL
        return ok

    # ---- admins ----------------------------------------------------------------------------------------------
    def is_admin(self, p) -> bool:
        """ADMIN_USERS (cfg.admins) holds this player's account username (read from `accounts` when the player is
        loaded or refreshed; never from the client)."""
        u = getattr(p, 'username', '')
        return bool(u) and u in self.cfg.admins

    def need_admin(self, p) -> None:
        if not self.is_admin(p):
            raise LiveError('admin', 'Chỉ Ban quản lý ghim được tin.')

    # ---- 📌 the pinned message of Cả phố -------------------------------------------------------------------
    async def pin_for(self, p, *, resolve=True) -> dict | None:
        """The pin as this player sees it: nothing when they blocked its author (or were blocked)."""
        pin = self.pin
        if not pin or pin['pid'] in p.hidden or await self.my_hides(p, [pin['id']]):
            return None
        result = (await chat_reply.project(self, p, [pin]))[0] if resolve else pin
        return result if self.pin is pin else None

    async def sync_pin(self, announce: bool = True) -> None:
        """Read the pin row (one primary-key lookup, its message by primary key). A pin whose message is gone
        (deleted, hidden, pruned, not on Cả phố) is removed. When it changed, tell everyone on Cả phố."""
        r = await self.db.fetchrow(
            'SELECT p.msg AS pin_msg, p.at AS pin_at, m.id, m.channel, m.pid, m.name, m.av, m.text, m.at, m.hidden, m.deleted, m.adm, m.reply_to '
            "FROM chat_pins p LEFT JOIN chat_messages m ON m.id=p.msg WHERE p.channel='town'")
        pin, key = None, None
        if r:
            if r['id'] is None or r['channel'] != 'town' or r['hidden'] or r['deleted']:
                await self.db.execute("DELETE FROM chat_pins WHERE channel='town' AND msg=?", (r['pin_msg'],))
            else:
                pin = msg_frame(r)
                pin.pop('t', None)
                key = (int(r['pin_msg']), float(r['pin_at']))
        if key == self.pin_key:
            return
        self.pin, self.pin_key = pin, key
        if announce:
            await self.announce_pin()

    async def announce_pin(self, extra=()) -> None:
        """`pinned` to everyone on Cả phố (and `extra` sockets): null to those who blocked its author."""
        conns = list(self.town.conns) + [c for c in extra if c not in self.town.conns and c.ready]
        for c in conns:
            self.hub.send(c, dict(t='pinned', ch='town', pin=await self.pin_for(c.player)))

    @on('pin', rate=(10, 60))
    async def pin_msg(self, conn, f):
        p, mid = conn.player, f.get('id')
        self.need_admin(p)
        if type(mid) is not int or mid <= 0:
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        if not await self.db.fetchval("SELECT id FROM chat_messages WHERE id=? AND channel='town' AND hidden=0 AND deleted=0", (mid,)):
            raise LiveError('gone', 'Không tìm thấy tin nhắn này.')
        await self.db.execute("INSERT INTO chat_pins(channel, msg, by_pid, at) VALUES('town', ?, ?, ?) "
                              'ON CONFLICT(channel) DO UPDATE SET msg=excluded.msg, by_pid=excluded.by_pid, at=excluded.at',
                              (mid, p.pid, time.time()))
        await self.sync_pin(announce=False)
        await self.announce_pin(extra=[conn])
        return None

    @on('unpin', rate=(10, 60))
    async def unpin_msg(self, conn, f):
        self.need_admin(conn.player)
        await self.db.execute("DELETE FROM chat_pins WHERE channel='town'")
        await self.sync_pin(announce=False)
        await self.announce_pin(extra=[conn])
        return None

    # ---- loading a player -----------------------------------------------------------------------------------
    async def load_friends(self, p) -> None:
        rows = await self.db.fetch('SELECT f.friend AS sid, a.display AS name, pr.avatar AS av FROM friends f '
                                   'LEFT JOIN accounts a ON a.sid=f.friend LEFT JOIN profiles pr ON pr.sid=f.friend '
                                   'WHERE f.sid=? ORDER BY f.since DESC LIMIT ?', (p.sid, FRIENDS_MAX))
        from .auth import AVATARS, clean_name
        p.friends = {pid_of(r['sid']): dict(sid=r['sid'], name=clean_name(r['name']) or 'Một người chơi',
                                            av=r['av'] if r['av'] in AVATARS else '🌸') for r in rows}
        await self.faces_of(p.friends)

    async def load_hidden(self, p) -> None:
        a = await self.db.fetch('SELECT target AS x FROM blocks WHERE pid=? UNION SELECT pid AS x FROM blocks WHERE target=?', (p.pid, p.pid))
        b = await self.db.fetch('SELECT target AS x FROM marriage_blocks WHERE sid=? UNION SELECT sid AS x FROM marriage_blocks WHERE target=?', (p.sid, p.sid))
        p.hidden = {r['x'] for r in a} | {pid_of(r['x']) for r in b}

    async def chan_list(self, p) -> list:
        clr = ('COALESCE(k.upto, 0) AS upto ', 'LEFT JOIN chat_clears k ON k.channel=m.channel AND k.pid=m.pid ') if self.del_ok else ('0 AS upto ', '')
        rows = await self.db.fetch(
            'SELECT c.id, c.kind, c.title, c.owner_pid, m.last_read, m.role, m.muted_until, '
            'COALESCE((SELECT MAX(x.id) FROM chat_messages x WHERE x.channel=c.id), 0) AS last_id, '
            '(SELECT COUNT(*) FROM chat_members y WHERE y.channel=c.id) AS n, ' + clr[0] +
            'FROM chat_members m JOIN chat_channels c ON c.id=m.channel ' + clr[1] +
            'WHERE m.pid=? ORDER BY last_id DESC LIMIT ?', (p.pid, CHANS_LISTED))
        # 🗑️ a DM I emptied leaves my list until somebody writes again
        rows = [r for r in rows if not (r['kind'] == 'dm' and r['upto'] and int(r['last_id']) <= int(r['upto']))]
        if not rows:
            return []
        ids = [r['id'] for r in rows]
        marks = ','.join('?' * len(ids))
        unread = {r['ch']: int(r['n']) for r in await self.db.fetch(
            'SELECT m.channel AS ch, COUNT(x.id) AS n FROM chat_members m JOIN chat_messages x ON x.channel=m.channel '
            'AND x.id>m.last_read AND x.pid<>m.pid AND x.deleted=0 AND x.hidden=0 WHERE m.pid=? GROUP BY m.channel', (p.pid,))}
        lasts = [int(r['last_id']) for r in rows if r['last_id'] and int(r['last_id']) > int(r['upto'])]
        gone = await self.my_hides(p, lasts)   # 🗑️ a last message I deleted on my side: no preview
        lasts = [i for i in lasts if i not in gone]
        last = {}
        if lasts:
            for r in await self.db.fetch(f"SELECT * FROM chat_messages WHERE id IN ({','.join('?' * len(lasts))})", lasts):
                last[r['channel']] = r
        peers = {}
        dms = [i for i in ids if i.startswith('dm:')]
        if dms:
            from .auth import AVATARS, clean_name
            for r in await self.db.fetch(
                    f"SELECT m.channel, m.pid, a.display, lp.name AS gname, pr.avatar FROM chat_members m "
                    f"LEFT JOIN accounts a ON a.sid=m.sid LEFT JOIN leaderboard_players lp ON lp.sid=m.sid "
                    f"LEFT JOIN profiles pr ON pr.sid=m.sid WHERE m.channel IN ({','.join('?' * len(dms))}) AND m.pid<>?", (*dms, p.pid)):
                peers[r['channel']] = dict(pid=r['pid'], name=clean_name(r['display']) or clean_name(r['gname']) or 'Một người chơi',
                                           av=r['avatar'] if r['avatar'] in AVATARS else '🌸', friend=r['pid'] in p.friends)
        fx = await self.faces_of([x['pid'] for x in peers.values()])
        out = []
        for r in rows:
            c = dict(id=r['id'], kind=r['kind'], title=r['title'], unread=unread.get(r['id'], 0), read=int(r['last_read']))
            if float(r['muted_until'] or 0) > time.time():
                c['quiet'] = round(float(r['muted_until']))   # 🔔 notifications off until then
            if r['kind'] == 'group':
                c.update(owner=r['owner_pid'], n=int(r['n']), role=r['role'])
            if r['id'] in peers:
                c['peer'] = peers[r['id']]
                if fx.get(c['peer']['pid']):
                    c['peer']['fc'] = fx[c['peer']['pid']]
                c['peer']['on'] = p.show_online and self.hub.visible(c['peer']['pid'])
            m = last.get(r['id'])
            if m and m['hidden'] == 0 and m['pid'] not in p.hidden:
                c['last'] = msg_frame(m)
            out.append(c)
        previews = await chat_reply.project(self, p, [c['last'] for c in out if 'last' in c])
        for c, preview in zip((c for c in out if 'last' in c), previews):
            c['last'] = preview
        return out

    def friend_list(self, p) -> list:
        out = []
        for k, v in p.friends.items():
            if k not in p.hidden:
                f = dict(pid=k, name=v['name'], av=v['av'], on=bool(p.show_online and self.hub.visible(k)))
                if self.faces.get(k):   # filled by load_friends, kept current by `face`
                    f['fc'] = self.faces[k]
                out.append(f)
        return out

    def can_town(self, p) -> tuple[str, float]:
        """('ok', 0) or (why, seconds to wait): 'muted', 'account' (a guest: only accounts chat, owner 01/10),
        'new' (session < 10 min), 'name' (no name yet)."""
        t = time.time()
        if self.is_admin(p):    # admins: no mute, no wait, no slow mode (owner, 01/10)
            return ('ok' if p.name else 'name'), 0.0
        if p.muted_until > t:
            return 'muted', p.muted_until - t
        if not p.account:
            return 'account', 0
        if not p.old:
            since = p.since or self.app.first_seen(p.pid)
            left = since + self.cfg.new_secs - t
            if left > 0:
                return 'new', left
        if not p.name:
            return 'name', 0
        return 'ok', max(0.0, p.town_next - t)

    async def refresh(self, p) -> None:
        """Name, avatar, age and mute again from the database (a guest names their character after the socket
        opened; a profile picture changed)."""
        ident = await profile(self.db, p.sid)
        if ident:
            p.update(ident)
            await self.fit_face(p)

    async def on_hello(self, conn):
        p = conn.player
        if not p.loaded:
            await self.load_friends(p)
            await self.load_hidden(p)
            p.fc = (await self.faces_of([p.pid])).get(p.pid) or None
            p.loaded = True
        if self.del_ok and 'hides' not in p.ext:   # 🗑️ ever deleted a message on their side? (else no lookups per page)
            p.ext['hides'] = bool(await self.db.fetchval('SELECT 1 FROM chat_hides WHERE pid=? LIMIT 1', (p.pid,)))
        await self.fit_face(p)   # the profile emoji may have changed since (read again at every connect)
        fc = conn.ext.pop('fc', None)
        if fc is not None:   # a client of this release: the face it wears now (an older one keeps the stored face)
            code = facemod.clean(fc, p.av)
            if code is not None and await self.store_face(p, code):
                self.announce_face(p, skip_conn=conn)
        conn.ext['chans'] = await self.chan_list(p)
        conn.ext['reply_epoch'] = self.reply_epoch

    def welcome(self, conn) -> dict:
        p = conn.player
        chans = conn.ext.pop('chans', [])
        if conn.ext.pop('reply_epoch', self.reply_epoch) != self.reply_epoch:
            # Other features may await after our on_hello, before welcome is written.
            for channel in chans:
                last = channel.get('last', {})
                if last.get('reply'):
                    last['reply'] = dict(id=last['reply']['id'], unavailable=True)
        return dict(me=self.me(p), friends=self.friend_list(p), chans=chans,
                    limits=dict(town_every=self.cfg.town_every, town_len=self.cfg.town_len, text_len=self.cfg.text_len, group_max=self.cfg.group_max,
                                admin_len=self.cfg.admin_len))

    def me(self, p) -> dict:
        why, wait = self.can_town(p)
        adm = self.is_admin(p)
        out = dict(pid=p.pid, name=p.name, av=p.av, fc=p.fc or '', account=p.account, friend_card=True, online=p.show_online, town=why,
                   wait=round(wait, 1), muted=round(p.muted_until, 1) if p.muted_until > time.time() and not adm else 0)
        if adm:
            out['adm'] = 1
        return out

    def on_gone(self, player):
        pass

    # ---- channels -------------------------------------------------------------------------------------------
    async def chan(self, cid) -> Chan | None:
        if not isinstance(cid, str) or len(cid) > 64:
            return None
        if cid == 'town':
            return Chan('town', 'town', 'Cả phố')
        c = self.chans.get(cid)
        if c is not None:
            return c
        if not (CH_DM.fullmatch(cid) or CH_GROUP.fullmatch(cid)):
            return None
        row = await self.db.fetchrow('SELECT id, kind, title, owner_pid FROM chat_channels WHERE id=?', (cid,))
        if not row:
            return None
        if self.del_ok:   # 🗑️ with what each member emptied (chat_clears, its primary key)
            rows = await self.db.fetch('SELECT m.pid, m.sid, m.muted_until, k.upto FROM chat_members m '
                                       'LEFT JOIN chat_clears k ON k.channel=m.channel AND k.pid=m.pid WHERE m.channel=?', (cid,))
        else:
            rows = await self.db.fetch('SELECT pid, sid, muted_until FROM chat_members WHERE channel=?', (cid,))
        members = {r['pid']: r['sid'] for r in rows}
        quiet = {r['pid']: float(r['muted_until']) for r in rows if float(r['muted_until'] or 0) > 0}
        cleared = {r['pid']: int(r['upto']) for r in rows if r.get('upto')}
        return self.chans.put(cid, Chan(cid, row['kind'], row['title'], row['owner_pid'], members, quiet, cleared))

    async def member_chan(self, p, cid) -> Chan:
        c = await self.chan(cid)
        if c is None or (c.kind != 'town' and p.pid not in c.members):
            raise LiveError('no_chat', 'Không tìm thấy cuộc trò chuyện này.')
        return c

    async def friendship(self, p, other_pid: str) -> str | None:
        """The friend's sid when we are friends now and nobody blocked anybody; else None."""
        f = p.friends.get(other_pid)
        if f is None:
            await self.load_friends(p)
            f = p.friends.get(other_pid)
        if f is None or other_pid in p.hidden:
            return None
        r = await self.db.fetchrow(
            'SELECT (SELECT 1 FROM friends WHERE sid=? AND friend=?) AS f, '
            '(SELECT 1 FROM blocks WHERE (pid=? AND target=?) OR (pid=? AND target=?) LIMIT 1) AS b1, '
            '(SELECT 1 FROM marriage_blocks WHERE (sid=? AND target=?) OR (sid=? AND target=?) LIMIT 1) AS b2',
            (p.sid, f['sid'], p.pid, other_pid, other_pid, p.pid, p.sid, f['sid'], f['sid'], p.sid))
        if not r or not r['f'] or r['b1'] or r['b2']:
            if r and (r['b1'] or r['b2']):
                p.hidden.add(other_pid)
            return None
        return f['sid']

    async def open_dm(self, p, other_pid) -> Chan:
        if not isinstance(other_pid, str) or not PID.fullmatch(other_pid) or other_pid == p.pid:
            raise LiveError('no_chat', 'Không tìm thấy người này.')
        other_sid = await self.friendship(p, other_pid)
        if not other_sid:
            raise LiveError('not_friend', 'Chỉ nhắn riêng được với bạn bè.')
        cid = dm_id(p.pid, other_pid)
        c = await self.chan(cid)
        if c is None or other_pid not in c.members or p.pid not in c.members:
            t = time.time()

            async def run(tx):
                await tx.execute("INSERT INTO chat_channels(id, kind, title, owner_pid, created) VALUES(?, 'dm', '', NULL, ?) "
                                 'ON CONFLICT(id) DO NOTHING', (cid, t))
                for pid, sid in ((p.pid, p.sid), (other_pid, other_sid)):
                    await tx.execute("INSERT INTO chat_members(channel, pid, sid, role, joined) VALUES(?, ?, ?, 'member', ?) "
                                     'ON CONFLICT(channel, pid) DO NOTHING', (cid, pid, sid, t))
            await self.db.transaction(run)
            self.chans.pop(cid, None)
            c = await self.chan(cid)
        return c

    def send_to_chan(self, c: Chan, frame, sender=None, skip=None) -> None:
        if c.kind == 'town':
            self.town.send(frame, sender, skip)
            return
        r = self._route(c.id)
        if r:
            for room in r[0](c.id):
                room.send(frame, sender, skip)
            return
        self.hub.to_pids(c.members, frame, sender if c.kind == 'group' else None, skip)

    async def deliver_message(self, c: Chan, frame, sender=None, skip=None) -> None:
        """Project quotes for their recipient; keep the existing channel audience/block rules."""
        if not frame.get('reply_to'):
            self.send_to_chan(c, frame, sender=sender, skip=skip)
            return
        if c.kind == 'town':
            targets = list(self.town.conns)
        else:
            targets = [conn for pid in c.members for conn in self.hub.conns_of(pid)]
        by_player = {}
        for conn in targets:
            if conn is skip or not conn.ready:
                continue
            if sender and c.kind != 'dm' and (conn.player.pid in sender.hidden or sender.pid in conn.player.hidden):
                continue
            by_player.setdefault(conn.player, []).append(conn)
        projected = await chat_reply.project_many(self, list(by_player), [frame])
        for player, conns in by_player.items():
            if sender and c.kind != 'dm' and (player.pid in sender.hidden or sender.pid in player.hidden):
                continue
            if c.kind != 'town' and player.pid not in c.members:
                continue
            if c.kind == 'town':
                conns = [conn for conn in conns if conn in self.town.conns]
            self.hub.send_many(conns, projected[player.pid][0])

    # ---- storing a message (also for phase 2/3 channels) -----------------------------------------------------
    async def store_message(self, p, ch: str, text, limit: int, lines: int = 4, admin: bool = False, reply_to=None) -> dict:
        """Check, filter and insert one message by player p in channel ch; returns its `msg` frame.
        Repeated content is allowed. Raises LiveError: text (empty/too long), name, muted.
        admin=True (an admin on Cả phố): no mute or masking; the row/frame are marked adm=1."""
        t = time.time()
        clean = filters.clean(text, limit, lines)
        if clean is None:
            raise LiveError('text', f'Tin nhắn từ 1 đến {limit} ký tự nhé.')
        if not p.name or not p.account:
            await self.refresh(p)   # a guest who just registered or named their character
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để chat nhé.')
        if not p.name:
            raise LiveError('name', 'Đặt tên nhân vật trước khi nhắn nhé.')
        self.names.put(p.pid, p.name)
        if admin:
            row = await self.db.fetchrow('INSERT INTO chat_messages(channel, pid, name, av, text, at, adm, reply_to) VALUES(?, ?, ?, ?, ?, ?, 1, ?) RETURNING id',
                                         (ch, p.pid, p.name, p.av, clean, t, reply_to))
            return self._faced(p, dict(t='msg', ch=ch, id=int(row['id']), pid=p.pid, name=p.name, av=p.av, text=clean, at=round(t, 3), adm=1,
                                       **({'reply_to': reply_to} if reply_to else {})))
        if p.muted_until > t:
            raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))
        masked = filters.mask(clean)
        raw = clean if masked != clean else None   # 🔎 what was typed, for the admin screen only (never sent to players)
        row = await self.db.fetchrow(
            'INSERT INTO chat_messages(channel, pid, name, av, text, at, raw, reply_to) SELECT ?, ?, ?, ?, ?, ?, ?, ? '
            'WHERE NOT EXISTS (SELECT 1 FROM chat_mutes WHERE pid=? AND until>?) RETURNING id',
            (ch, p.pid, p.name, p.av, masked, t, raw, reply_to, p.pid, t))
        if not row:
            until = await self.db.fetchval('SELECT until FROM chat_mutes WHERE pid=?', (p.pid,))
            p.muted_until = float(until or 0)
            raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))
        return self._faced(p, dict(t='msg', ch=ch, id=int(row['id']), pid=p.pid, name=p.name, av=p.av, text=masked, at=round(t, 3),
                                   **({'reply_to': reply_to} if reply_to else {})))

    # ---- 🙂 faces ---------------------------------------------------------------------------------------------
    @staticmethod
    def _faced(p, frame: dict) -> dict:
        if p.fc:
            frame['fc'] = p.fc
        return frame

    async def faces_of(self, pids) -> dict:
        """{pid: face code ('' = none)} for these players: from memory, else one primary-key query per 500."""
        out, miss = {}, []
        for pid in set(pids):
            v = self.faces.get(pid)
            if v is None:
                miss.append(pid)
            else:
                out[pid] = v
        for i in range(0, len(miss), 500):
            part = miss[i:i + 500]
            got = {r['pid']: r['code'] for r in await self.db.fetch(
                f"SELECT pid, code FROM chat_faces WHERE pid IN ({','.join('?' * len(part))})", part)}
            for pid in part:
                out[pid] = self.faces.put(pid, facemod.clean(got.get(pid)) or '')
        return out

    async def with_faces(self, msgs: list) -> list:
        """The messages with their authors' faces now (copies where it changes; a frame of the buffer keeps the face
        its author had when it was sent)."""
        if not msgs:
            return msgs
        fx = await self.faces_of(m['pid'] for m in msgs)
        out = []
        for m in msgs:
            fc = fx.get(m['pid']) or None
            if m.get('fc') != fc:
                m = dict(m)
                if fc:
                    m['fc'] = fc
                else:
                    m.pop('fc', None)
            out.append(m)
        return out

    async def store_face(self, p, code: str) -> bool:
        """Keep my face (a cleaned code, '' = none). True when it changed."""
        if code == (p.fc or ''):
            return False
        if code:
            await self.db.execute('INSERT INTO chat_faces(pid, code, at) VALUES(?, ?, ?) '
                                  'ON CONFLICT(pid) DO UPDATE SET code=excluded.code, at=excluded.at', (p.pid, code, time.time()))
        else:
            await self.db.execute('DELETE FROM chat_faces WHERE pid=?', (p.pid,))
        p.fc = code or None
        self.faces.put(p.pid, code)
        return True

    async def fit_face(self, p) -> None:
        """The stored face was cleaned without knowing its owner: an automatic face (a1) of someone who has since picked
        an emoji in their Phố nghề profile goes, so the emoji shows."""
        if p.fc and facemod.clean(p.fc, p.av) == '' and await self.store_face(p, ''):
            self.announce_face(p)

    def announce_face(self, p, skip_conn=None) -> None:
        """`faced {pid, fc}` to my other tabs, everyone on Cả phố and my online friends (open screens redraw my lines)."""
        conns = {c for c in p.conns if c.ready} | set(self.town.conns)
        for pid in p.friends:
            o = self.hub.players.get(pid)
            if o:
                conns |= {c for c in o.conns if c.ready}
        conns = [c for c in conns if c is not skip_conn and c.player.pid not in p.hidden and p.pid not in c.player.hidden]
        self.hub.send_many(conns, dict(t='faced', pid=p.pid, fc=p.fc or ''))

    @on('face', rate=(6, 60))
    async def face(self, conn, f):
        """🙂 My face changed (the builder, the wardrobe): '' = back to my emoji."""
        p, fc = conn.player, f.get('fc')
        code = '' if fc == '' else facemod.clean(fc, p.av)
        if code is None:
            raise LiveError('bad', 'Ảnh đại diện không hợp lệ.')
        if await self.store_face(p, code):
            self.announce_face(p, skip_conn=conn)
        return dict(t='faced', pid=p.pid, fc=p.fc or '')

    # ---- handlers ------------------------------------------------------------------------------------------
    @on('sync', rate=(6, 60))
    async def sync(self, conn, f):
        p = conn.player
        await self.refresh(p)
        await self.load_friends(p)
        await self.load_hidden(p)
        why, wait = self.can_town(p)
        return dict(t='state', friends=self.friend_list(p), chans=await self.chan_list(p), town=why, wait=round(wait, 1),
                    online=p.show_online, me=self.me(p))

    @on('join', rate=(20, 10))
    async def join(self, conn, f):
        if f.get('ch') != 'town':
            raise LiveError('no_chat', 'Không tìm thấy phòng này.')
        p = conn.player
        self.town.add(conn)
        after = f.get('after')
        msgs = [m for m in self.town.buffer if m['pid'] not in p.hidden]
        more = self.town_more or len(self.town.buffer) >= self.cfg.buffer or len(msgs) > PAGE
        msgs = msgs[-PAGE:]
        inc = False   # True: only what came after the client's last message (it keeps what it has)
        if type(after) is int and after > 0 and (not self.town.buffer or self.town.buffer[0]['id'] <= after + 1):
            msgs, inc = [m for m in self.town.buffer if m['id'] > after and m['pid'] not in p.hidden], True
        msgs = await self.without_hides(p, msgs)
        msgs = await self.with_faces(await self.with_reacts(p, msgs))
        pin = await self.pin_for(p, resolve=False)
        projected = await chat_reply.project(self, p, msgs + ([pin] if pin else []))
        msgs = projected[:len(msgs)]
        pin = projected[-1] if pin is not None and self.pin is pin else None
        why, wait = self.can_town(p)
        return dict(t='joined', ch='town', msgs=msgs, more=more, inc=inc, why=why, wait=round(wait, 1),
                    n=len(self.town.players()), pin=pin)

    @on('leave', rate=(20, 10))
    async def leave(self, conn, f):
        if f.get('ch') == 'town':
            self.town.remove(conn)

    @on('send', rate=(12, 10))
    async def send(self, conn, f):
        p, t = conn.player, time.time()
        reply_to = chat_reply.reply_id(f)
        cid = f.get('cid') if isinstance(f.get('cid'), str) and len(f.get('cid')) <= 40 else None
        if f.get('to') is not None and f.get('ch') is None:
            c = await self.open_dm(p, f.get('to'))
        else:
            c = await self.member_chan(p, f.get('ch'))
        await chat_reply.validate(self, p, c.id, reply_to)
        if c.kind == 'town':
            if not p.name or not p.account:
                await self.refresh(p)   # a guest who just registered can post at once, no reconnect
            admin = self.is_admin(p)
            why, wait = self.can_town(p)
            if why == 'account':
                raise LiveError('account', 'Tạo tài khoản để chat nhé.')
            if why == 'new':
                raise LiveError('new', 'Người mới vào phố đọc trước, lát nữa nhắn nhé.', wait=round(wait, 1))
            if why == 'name':
                raise LiveError('name', 'Đặt tên nhân vật trước khi nhắn nhé.')
            if why == 'muted':
                raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))
            if admin:   # 📌 admins post freely: no slow mode, longer, links kept (owner, 01/10)
                frame = await self.store_message(p, 'town', f.get('text'), self.cfg.admin_len, self.cfg.admin_lines, admin=True, reply_to=reply_to)
            else:
                if wait > 0:
                    raise LiveError('slow', f'Cả phố: {self.cfg.town_every:g} giây một tin.', wait=round(wait, 1))
                p.town_next = t + self.cfg.town_every          # before the await: a second tab cannot slip in
                try:
                    frame = await self.store_message(p, 'town', f.get('text'), self.cfg.town_len, 3, reply_to=reply_to)
                except BaseException:
                    p.town_next = 0.0
                    raise
            self.town.buffer.append(frame)
            n = len({c.player.pid for c in self.town.conns})
            await self.deliver_message(c, dict(frame, n=n), sender=p, skip=conn)   # n: people on Cả phố now
            mine = (await chat_reply.project(self, p, [frame]))[0]
            self.hub.send(conn, dict(mine, cid=cid, wait=0 if admin else self.cfg.town_every, n=n))
            return None
        if c.kind == 'dm':
            other = next((x for x in c.members if x != p.pid), None)
            if not other or not await self.friendship(p, other):
                raise LiveError('not_friend', 'Hai bạn không còn là bạn bè, không nhắn riêng được nữa.')
        frame = await self.store_message(p, c.id, f.get('text'), self.cfg.text_len, 12, reply_to=reply_to)
        await self.deliver_message(c, frame, sender=p, skip=conn)
        mine = (await chat_reply.project(self, p, [frame]))[0]
        self.hub.send(conn, dict(mine, cid=cid, to=f.get('to')) if f.get('to') else dict(mine, cid=cid))
        self.push_offline(c, p, frame)
        return None

    def push_offline(self, c: Chan, p, frame: dict) -> None:
        """🔔 A web push to the members of a DM or group with no socket, unless the chat is quiet for them; one per chat
        per member per PUSH_EVERY (remembered here first, so a busy group writes nothing per message)."""
        if c.kind not in ('dm', 'group'):
            return
        t = time.time()
        body = f'{p.name}: {frame["text"][:80]}' if c.kind == 'dm' else f'{c.title} · {p.name}: {frame["text"][:80]}'
        for pid, sid in list(c.members.items()):
            if pid == p.pid or self.hub.online(pid) or c.quiet.get(pid, 0) > t or pid in p.hidden:
                continue
            last = self.push_tried.get((c.id, pid))
            if last is not None and t - last < PUSH_EVERY:
                continue
            self.push_tried.put((c.id, pid), t)
            self.spawn(maybe_push(self.db, c.id, pid, sid, body, f'/?chat={c.id}', PUSH_EVERY))

    @on('notify', rate=(20, 60))
    async def notify(self, conn, f):
        """🔔 Notifications of one DM or group: 'on', '8h' (quiet for QUIET_HOURS) or 'off' (until turned on)."""
        p, v = conn.player, f.get('v')
        if v not in ('on', '8h', 'off'):
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        c = await self.member_chan(p, f.get('ch'))
        if c.kind not in ('dm', 'group'):
            raise LiveError('bad', 'Cả phố không gửi thông báo.')
        until = 0.0 if v == 'on' else time.time() + QUIET_HOURS * 3600 if v == '8h' else QUIET_FOREVER
        await self.db.execute('UPDATE chat_members SET muted_until=? WHERE channel=? AND pid=?', (until, c.id, p.pid))
        if until:
            c.quiet[p.pid] = until
        else:
            c.quiet.pop(p.pid, None)
        self.hub.send_many([x for x in p.conns if x.ready], dict(t='quiet', ch=c.id, until=round(until)))
        return None

    @on('history', rate=(20, 10))
    async def history(self, conn, f):
        p = conn.player
        ch = f.get('ch')
        r = self._route(ch) if isinstance(ch, str) else None
        if r:
            if not r[1](p, ch):
                raise LiveError('no_chat', 'Không tìm thấy cuộc trò chuyện này.')
            upto = 0
        else:
            upto = (await self.member_chan(p, ch)).cleared.get(p.pid, 0)   # 🗑️ emptied for me up to there
        before = f.get('before')
        if type(before) is not int or before <= 0:
            before = 2 ** 62
        rows = await self.db.fetch('SELECT * FROM chat_messages WHERE channel=? AND id<? AND id>? AND hidden=0 ORDER BY id DESC LIMIT ?',
                                   (ch, before, upto, PAGE + 1))
        more = len(rows) > PAGE
        msgs = [msg_frame(r) for r in reversed(rows[:PAGE]) if r['pid'] not in p.hidden]
        if not r:   # 😍 Cả phố, DMs, groups (not the street's bubbles)
            msgs = await self.with_reacts(p, await self.without_hides(p, msgs))
        return dict(t='history', ch=ch, msgs=await chat_reply.project(self, p, await self.with_faces(msgs)), more=more, before=f.get('before'))

    @on('read', rate=(40, 10))
    async def read(self, conn, f):
        p, ch, mid = conn.player, f.get('ch'), f.get('id')
        if type(mid) is not int or mid <= 0:
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        c = await self.member_chan(p, ch)
        if c.kind == 'town':
            return None
        await self.db.execute('UPDATE chat_members SET last_read=? WHERE channel=? AND pid=? AND last_read<?', (mid, c.id, p.pid, mid))
        self.hub.send_many([x for x in p.conns if x is not conn and x.ready], dict(t='read', ch=c.id, id=mid))
        return None

    @on('del', rate=(10, 10))
    async def delete(self, conn, f):
        """Thu hồi: my own message, for everyone, within RECALL_SECS (admins: any time). A reported message keeps what
        was written in `raw` for the admin who reviews it; any other loses its text."""
        p, mid = conn.player, f.get('id')
        if type(mid) is not int or mid <= 0:
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        since = 0.0 if self.is_admin(p) else time.time() - RECALL_SECS
        row = await self.db.fetchrow("UPDATE chat_messages SET text='', raw=CASE WHEN reports>0 THEN COALESCE(raw, text) ELSE NULL END, deleted=1 "
                                     'WHERE id=? AND pid=? AND deleted=0 AND at>? RETURNING channel', (mid, p.pid, since))
        if not row:
            if since and await self.db.fetchval('SELECT 1 FROM chat_messages WHERE id=? AND pid=? AND deleted=0', (mid, p.pid)):
                raise LiveError('old', 'Tin đã quá 24 giờ, không thu hồi được nữa.')
            raise LiveError('gone', 'Không thu hồi được tin này.')
        await self.gone(row['channel'], mid, hidden=False)
        return None

    # ---- 🗑️ deleted on my side only ---------------------------------------------------------------------------
    async def my_hides(self, p, ids) -> set:
        """Which of these message ids p deleted on their side: primary-key lookups, only for a player who ever did."""
        ids = [i for i in ids if type(i) is int]
        if not ids or not self.del_ok or not p.ext.get('hides'):
            return set()
        out = set()
        for k in range(0, len(ids), 200):
            part = ids[k:k + 200]
            out.update(int(r['msg']) for r in await self.db.fetch(
                f"SELECT msg FROM chat_hides WHERE pid=? AND msg IN ({','.join('?' * len(part))})", (p.pid, *part)))
        return out

    async def without_hides(self, p, msgs: list) -> list:
        gone = await self.my_hides(p, [m['id'] for m in msgs])
        return [m for m in msgs if m['id'] not in gone] if gone else msgs

    async def need_del(self, p) -> None:
        if not self.del_ok:
            raise LiveError('off', 'Chưa xóa được lúc này, thử lại sau nhé.')
        if not p.account:
            await self.refresh(p)   # a guest who just registered
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để dùng chat nhé.')

    @on('hide', rate=(30, 60))
    async def hide(self, conn, f):
        """Xóa ở phía tôi: one message of Cả phố, a DM or a group leaves my screens (every tab), nobody else's."""
        p, mid = conn.player, f.get('id')
        if type(mid) is not int or mid <= 0:
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        await self.need_del(p)
        row = await self.db.fetchrow('SELECT channel FROM chat_messages WHERE id=?', (mid,))
        if not row or kind_of(row['channel']) not in ('town', 'dm', 'group'):
            raise LiveError('gone', 'Tin nhắn này không còn.')
        await self.member_chan(p, row['channel'])
        await self.db.execute('INSERT INTO chat_hides(pid, msg, at) VALUES(?, ?, ?) ON CONFLICT(pid, msg) DO NOTHING', (p.pid, mid, time.time()))
        p.ext['hides'] = True
        self.reply_epoch += 1
        self.hub.send_many([x for x in p.conns if x.ready], dict(t='hid', ch=row['channel'], id=mid))
        return None

    @on('clear', rate=(10, 60))
    async def clear(self, conn, f):
        """Empty whole DMs / groups for me (the chat list's "Xóa"): every message up to the newest one now leaves my
        screens, and they count as read. The others in the chat keep theirs."""
        p, chs = conn.player, f.get('chs')
        if not isinstance(chs, list) or not chs or len(chs) > CLEAR_MAX or not all(isinstance(x, str) for x in chs) or len(set(chs)) != len(chs):
            raise LiveError('bad', 'Chọn cuộc trò chuyện để xóa nhé.')
        await self.need_del(p)
        cs = []
        for ch in chs:
            c = await self.member_chan(p, ch)
            if c.kind not in ('dm', 'group'):
                raise LiveError('bad', 'Không xóa được Cả phố.')
            cs.append(c)
        t = time.time()

        async def run(tx):
            out = {}
            for c in cs:
                upto = int(await tx.fetchval('SELECT COALESCE(MAX(id), 0) FROM chat_messages WHERE channel=?', (c.id,)) or 0)
                if upto:
                    await tx.execute('INSERT INTO chat_clears(channel, pid, upto, at) VALUES(?, ?, ?, ?) ON CONFLICT(channel, pid) '
                                     'DO UPDATE SET upto=excluded.upto, at=excluded.at WHERE chat_clears.upto<excluded.upto', (c.id, p.pid, upto, t))
                    await tx.execute('UPDATE chat_members SET last_read=? WHERE channel=? AND pid=? AND last_read<?', (upto, c.id, p.pid, upto))
                out[c.id] = upto
            return out
        done = await self.db.transaction(run)
        self.reply_epoch += 1
        for c in cs:
            if done.get(c.id):
                c.cleared[p.pid] = max(c.cleared.get(p.pid, 0), done[c.id])
        self.hub.send_many([x for x in p.conns if x.ready], dict(t='cleared', chs=done))
        return None

    async def gone(self, ch: str, mid: int, hidden: bool) -> None:
        """A message left everyone's screen: deleted by its author (the text is gone) or hidden (moderation)."""
        self.reply_epoch += 1
        self.reacts.pop(mid, None)   # 😍 its reactions leave the screens with it (clients drop them on `deleted`)
        if ch == 'town':
            for m in list(self.town.buffer):
                if m['id'] == mid:
                    if hidden:
                        self.town.buffer.remove(m)
                    else:
                        m['text'], m['del'] = '', 1
        c = await self.chan(ch) if ch == 'town' or CH_DM.fullmatch(ch) or CH_GROUP.fullmatch(ch) else Chan(ch, kind_of(ch))
        if c is not None:
            frame = dict(t='deleted', ch=ch, id=mid)
            if hidden:
                frame['hidden'] = 1
            self.send_to_chan(c, frame)
        if ch == 'town' and self.pin and self.pin['id'] == mid:   # 📌 its pin goes with it
            await self.db.execute("DELETE FROM chat_pins WHERE channel='town' AND msg=?", (mid,))
            await self.sync_pin()

    @on('friend_card', rate=(10, 60))
    async def friend_card(self, conn, f):
        """A readable chat author's public code, used by the existing HTTP friend_request action."""
        p, mid = conn.player, f.get('id')
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để kết bạn nhé.')
        if type(mid) is not int or mid <= 0:
            raise LiveError('bad', 'Tin nhắn không hợp lệ.')
        row = await self.db.fetchrow('SELECT channel, pid, hidden, deleted FROM chat_messages WHERE id=?', (mid,))
        if row and row['pid'] == p.pid:
            raise LiveError('gone', 'Đây là tin của chính bạn mà.')
        if not row or row['hidden'] or row['deleted']:
            raise LiveError('gone', 'Tin này đã bị thu hồi hoặc ẩn. Bấm Kết bạn ở một tin khác của bạn ấy, hoặc tìm trong mục Bạn bè nhé.')
        # Only town/DM/group messages rendered by chat.js; a message ID cannot grant access to a private room.
        channel = await self.member_chan(p, row['channel'])
        if mid <= channel.cleared.get(p.pid, 0):
            raise LiveError('gone', 'Không tìm thấy người chơi này.')
        await self.load_hidden(p)
        if row['pid'] in p.hidden or mid in await self.my_hides(p, [mid]):
            raise LiveError('gone', 'Không tìm thấy người chơi này.')
        other = self.hub.players.get(row['pid'])
        if other is not None:
            sid = other.sid if other.account else None
        else:
            sid = await self.db.fetchval('SELECT p.sid FROM profiles p JOIN accounts a ON a.sid=p.sid WHERE p.pid=?', (row['pid'],))
            if not sid:
                sid = await self.db.fetchval('SELECT m.sid FROM chat_members m JOIN accounts a ON a.sid=m.sid WHERE m.pid=? LIMIT 1', (row['pid'],))
        if not sid:
            raise LiveError('gone', 'Bạn ấy đang chơi bằng phiên khách (chưa có tài khoản) hoặc đã rời phố, nên chưa kết bạn được.')
        blocked = await self.db.fetchval('SELECT 1 FROM marriage_blocks WHERE (sid=? AND target=?) OR (sid=? AND target=?) LIMIT 1', (p.sid, sid, sid, p.sid))
        if blocked:
            raise LiveError('gone', 'Không tìm thấy người chơi này.')
        code = await self.db.fetchval('SELECT code FROM marriage_people WHERE sid=?', (sid,))
        if not code:
            import secrets
            for _ in range(8):
                now = time.time()
                candidate = 'PCC-' + ''.join(secrets.choice('23456789ABCDEFGHJKMNPQRSTUVWXYZ') for _ in range(6))
                await self.db.execute('INSERT INTO marriage_people(sid, code, created, updated) VALUES(?, ?, ?, ?) ON CONFLICT DO NOTHING', (sid, candidate, now, now))
                code = await self.db.fetchval('SELECT code FROM marriage_people WHERE sid=?', (sid,))
                if code:
                    break
        if not code:
            raise LiveError('busy', 'Chưa gửi được, thử lại nhé.')
        return dict(t='friend_card', id=mid, pid=row['pid'], code=code)

    @on('report', rate=(10, 60))
    async def report(self, conn, f):
        p, mid, reason = conn.player, f.get('id'), f.get('reason', 'other')
        if type(mid) is not int or mid <= 0 or reason not in REASONS:
            raise LiveError('bad', 'Báo cáo không hợp lệ.')
        row = await self.db.fetchrow('SELECT channel, pid, adm FROM chat_messages WHERE id=?', (mid,))
        if not row:
            raise LiveError('gone', 'Không tìm thấy tin nhắn.')
        if row['pid'] == p.pid:
            raise LiveError('bad', 'Đây là tin của bạn.')
        if row['adm'] or row['pid'] == ADMIN_PID:
            raise LiveError('bad', 'Đây là tin của Ban quản lý.')
        r = self._route(row['channel'])
        if r:
            if not r[1](p, row['channel']):
                raise LiveError('no_chat', 'Không tìm thấy cuộc trò chuyện này.')
        else:
            await self.member_chan(p, row['channel'])
        t = time.time()

        async def run(tx):
            n = await tx.execute("INSERT INTO reports(reporter, kind, target, reason, at) VALUES(?, 'chat', ?, ?, ?) "
                                 'ON CONFLICT(reporter, kind, target) DO NOTHING', (p.pid, str(mid), reason, t))
            if n != 1:
                return None
            return await tx.fetchrow('UPDATE chat_messages SET reports=reports+1 WHERE id=? RETURNING reports, hidden, reviewed_at', (mid,))
        upd = await self.db.transaction(run)
        if upd and int(upd['reports']) >= HIDE_AFTER and int(upd['hidden']) == 0 and upd['reviewed_at'] is None:
            if await self.db.execute('UPDATE chat_messages SET hidden=1 WHERE id=? AND hidden=0', (mid,)) == 1:
                await self.gone(row['channel'], mid, hidden=True)
        return dict(t='reported', id=mid)

    @on('block', rate=(10, 60))
    async def block(self, conn, f):
        p, other = conn.player, f.get('pid')
        if not isinstance(other, str) or not PID.fullmatch(other) or other == p.pid:
            raise LiveError('bad', 'Người chơi không hợp lệ.')
        from game.home_guests import LOCK_PAIR_SQL, pair_lock_key
        from . import jsonx

        async def block_pair(tx):
            sid = await tx.fetchval("SELECT sid FROM accounts WHERE substring(encode(sha256(convert_to('pid:' || sid,'UTF8')),'hex'),1,16)=? LIMIT 1", (other,))
            if sid:
                await tx.execute(LOCK_PAIR_SQL, (pair_lock_key(p.sid, sid),))
            await tx.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?) ON CONFLICT(pid, target) DO NOTHING', (p.pid, other, time.time()))
            if sid:
                await tx.execute("UPDATE home_guest_invites SET status='revoked' WHERE status IN ('pending','accepted') AND ((owner=? AND guest=?) OR (owner=? AND guest=?))", (p.sid, sid, sid, p.sid))
                for target in (p.sid, sid):
                    await tx.execute("SELECT pg_notify('mnl_live',?)", (jsonx.dumps(dict(t='home_changed',sid=target)).decode(),))
        await self.db.transaction(block_pair)
        self.reply_epoch += 1
        p.hidden.add(other)
        self.hub.send_many(self.hub.conns_of(p.pid), dict(t='reply_hidden', pid=other))
        o = self.hub.players.get(other)
        if o:
            o.hidden.add(p.pid)
            self.hub.send_many(self.hub.conns_of(other), dict(t='reply_hidden', pid=p.pid))
            if p.announced:
                self.hub.send_many([c for c in o.conns if c.ready], dict(t='presence', pid=p.pid, on=False))
        return dict(t='blocked', pid=other, on=True)

    @on('unblock', rate=(10, 60))
    async def unblock(self, conn, f):
        p, other = conn.player, f.get('pid')
        if not isinstance(other, str) or not PID.fullmatch(other):
            raise LiveError('bad', 'Người chơi không hợp lệ.')
        await self.db.execute('DELETE FROM blocks WHERE pid=? AND target=?', (p.pid, other))
        await self.load_hidden(p)
        o = self.hub.players.get(other)
        if o:
            await self.load_hidden(o)
        return dict(t='blocked', pid=other, on=other in p.hidden)

    @on('blocks', rate=(10, 60))
    async def block_list(self, conn, f):
        """🚫 Who I blocked (my own `blocks` rows, newest first, at most BLOCKS_LISTED), to unblock them (feedback #93).
        The name: my friend's, else the one on their newest chat message (index chat_messages_pid), else a stand-in."""
        p = conn.player
        rows = await self.db.fetch('SELECT target FROM blocks WHERE pid=? ORDER BY at DESC LIMIT ?', (p.pid, BLOCKS_LISTED))
        out = []
        for r in rows:
            x, fr = r['target'], p.friends.get(r['target'])
            if fr:
                name, av = fr['name'], fr['av']
            else:
                m = await self.db.fetchrow('SELECT name, av FROM chat_messages WHERE pid=? ORDER BY id DESC LIMIT 1', (x,))
                name, av = (m['name'], m['av']) if m else ('', '')
            out.append(dict(pid=x, name=name or 'Một người chơi', av=av or '🌸'))
        fx = await self.faces_of([x['pid'] for x in out])
        for x in out:
            if fx.get(x['pid']):
                x['fc'] = fx[x['pid']]
        return dict(t='blocks', list=out)

    @on('prefs', rate=(10, 60))
    async def prefs(self, conn, f):
        p, online = conn.player, f.get('online')
        if type(online) is not bool:
            raise LiveError('bad', 'Thiết lập không hợp lệ.')
        await self.db.execute('INSERT INTO chat_prefs(pid, online, updated) VALUES(?, ?, ?) '
                              'ON CONFLICT(pid) DO UPDATE SET online=excluded.online, updated=excluded.updated', (p.pid, int(online), time.time()))
        self.hub.set_visible(p, online)
        self.hub.send_many([x for x in p.conns if x.ready], dict(t='prefs', online=online))
        if online:   # back in sight: the friends who are online now
            self.hub.send_many([x for x in p.conns if x.ready], dict(t='state', friends=self.friend_list(p)))
        return None

    # ---- groups --------------------------------------------------------------------------------------------
    async def _friend_pids(self, p, pids) -> list:
        if not isinstance(pids, list) or not pids or len(pids) > self.cfg.group_max:
            raise LiveError('bad', 'Chọn bạn để mời nhé.')
        out = []
        for x in pids:
            if not isinstance(x, str) or not PID.fullmatch(x) or x == p.pid or x in out:
                raise LiveError('bad', 'Danh sách không hợp lệ.')
            out.append(x)
        if any(x not in p.friends for x in out):
            await self.load_friends(p)
        if any(x not in p.friends or x in p.hidden for x in out):
            raise LiveError('not_friend', 'Chỉ mời được bạn bè.')
        return out

    def _chan_summary(self, c: Chan, pid: str) -> dict:
        return dict(id=c.id, kind=c.kind, title=c.title, owner=c.owner, n=len(c.members), role='owner' if c.owner == pid else 'member', unread=0)

    def _push_chan(self, c: Chan) -> None:
        for pid in c.members:
            self.hub.send_many(self.hub.conns_of(pid), dict(t='chan', chan=self._chan_summary(c, pid)))

    @on('group_new', rate=(5, 3600))
    async def group_new(self, conn, f):
        p = conn.player
        if not p.account:
            await self.refresh(p)
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để chat nhé.')
        title = filters.clean(f.get('title'), TITLE_LEN, 1)
        if not title:
            raise LiveError('text', f'Tên nhóm từ 1 đến {TITLE_LEN} ký tự.')
        pids = await self._friend_pids(p, f.get('pids'))
        if len(pids) + 1 > self.cfg.group_max:
            raise LiveError('full', f'Nhóm tối đa {self.cfg.group_max} người.')
        if await self.db.fetchval("SELECT COUNT(*) FROM chat_channels WHERE owner_pid=? AND kind='group'", (p.pid,)) >= GROUPS_OWNED:
            raise LiveError('full', f'Bạn đã lập {GROUPS_OWNED} nhóm.')
        cid, t, title = 'g:' + secrets.token_hex(5), time.time(), filters.mask(title)
        members = {p.pid: p.sid, **{x: p.friends[x]['sid'] for x in pids}}

        async def run(tx):
            await tx.execute("INSERT INTO chat_channels(id, kind, title, owner_pid, created) VALUES(?, 'group', ?, ?, ?)", (cid, title, p.pid, t))
            for pid, sid in members.items():
                await tx.execute('INSERT INTO chat_members(channel, pid, sid, role, joined) VALUES(?, ?, ?, ?, ?)',
                                 (cid, pid, sid, 'owner' if pid == p.pid else 'member', t))
        await self.db.transaction(run)
        c = self.chans.put(cid, Chan(cid, 'group', title, p.pid, members))
        self._push_chan(c)
        return dict(t='chan', chan=self._chan_summary(c, p.pid), open=True, cid=f.get('cid'))

    async def _own_group(self, p, ch) -> Chan:
        c = await self.member_chan(p, ch)
        if c.kind != 'group':
            raise LiveError('bad', 'Đây không phải nhóm.')
        if c.owner != p.pid:
            raise LiveError('owner', 'Chỉ trưởng nhóm làm được việc này.')
        return c

    @on('group_add', rate=(20, 600))
    async def group_add(self, conn, f):
        p = conn.player
        c = await self._own_group(p, f.get('ch'))
        pids = [x for x in await self._friend_pids(p, f.get('pids')) if x not in c.members]
        if len(c.members) + len(pids) > self.cfg.group_max:
            raise LiveError('full', f'Nhóm tối đa {self.cfg.group_max} người.')
        t = time.time()

        async def run(tx):
            for x in pids:
                await tx.execute("INSERT INTO chat_members(channel, pid, sid, role, joined) VALUES(?, ?, ?, 'member', ?) "
                                 'ON CONFLICT(channel, pid) DO NOTHING', (c.id, x, p.friends[x]['sid'], t))
        await self.db.transaction(run)
        for x in pids:
            c.members[x] = p.friends[x]['sid']
            c.quiet.pop(x, None)   # a new membership row: notifications on
        self._push_chan(c)
        return None

    @on('group_kick', rate=(20, 600))
    async def group_kick(self, conn, f):
        p, x = conn.player, f.get('pid')
        c = await self._own_group(p, f.get('ch'))
        if x == p.pid or x not in c.members:
            raise LiveError('bad', 'Người này không ở trong nhóm.')
        await self.db.execute('DELETE FROM chat_members WHERE channel=? AND pid=?', (c.id, x))
        self.reply_epoch += 1
        c.members.pop(x, None)
        self.hub.send_many(self.hub.conns_of(x), dict(t='unchan', ch=c.id))
        self._push_chan(c)
        return None

    @on('group_leave', rate=(20, 600))
    async def group_leave(self, conn, f):
        p = conn.player
        c = await self.member_chan(p, f.get('ch'))
        if c.kind != 'group':
            raise LiveError('bad', 'Đây không phải nhóm.')

        async def run(tx):
            await tx.execute('DELETE FROM chat_members WHERE channel=? AND pid=?', (c.id, p.pid))
            if c.owner == p.pid:
                nxt = await tx.fetchrow('SELECT pid FROM chat_members WHERE channel=? ORDER BY joined, pid LIMIT 1', (c.id,))
                if nxt:
                    await tx.execute("UPDATE chat_members SET role='owner' WHERE channel=? AND pid=?", (c.id, nxt['pid']))
                await tx.execute('UPDATE chat_channels SET owner_pid=? WHERE id=?', (nxt['pid'] if nxt else None, c.id))
                return nxt['pid'] if nxt else None
            return c.owner
        c.owner = await self.db.transaction(run)
        self.reply_epoch += 1
        c.members.pop(p.pid, None)
        self.hub.send_many([x for x in p.conns if x.ready], dict(t='unchan', ch=c.id))
        self._push_chan(c)
        return None

    @on('members', rate=(20, 60))
    async def members(self, conn, f):
        p = conn.player
        c = await self.member_chan(p, f.get('ch'))
        if c.kind == 'town':
            raise LiveError('bad', 'Cả phố không có danh sách thành viên.')
        from .auth import AVATARS, clean_name
        rows = await self.db.fetch('SELECT m.pid, m.role, a.display, lp.name AS gname, pr.avatar FROM chat_members m '
                                   'LEFT JOIN accounts a ON a.sid=m.sid LEFT JOIN leaderboard_players lp ON lp.sid=m.sid '
                                   'LEFT JOIN profiles pr ON pr.sid=m.sid WHERE m.channel=? ORDER BY CASE WHEN m.role=\'owner\' THEN 0 ELSE 1 END, m.joined, m.pid', (c.id,))
        fx = await self.faces_of([r['pid'] for r in rows])
        out = [dict(pid=r['pid'], role=r['role'], name=clean_name(r['display']) or clean_name(r['gname']) or 'Một người chơi',
                    av=r['avatar'] if r['avatar'] in AVATARS else '🌸', friend=r['pid'] in p.friends,
                    on=bool(p.show_online and self.hub.visible(r['pid'])), **({'fc': fx[r['pid']]} if fx.get(r['pid']) else {}))
               for r in rows]
        return dict(t='members', ch=c.id, members=out, owner=c.owner, title=c.title)

    # ---- 😍 reactions ---------------------------------------------------------------------------------------
    @staticmethod
    def _ordered(counts: dict) -> dict:
        return {e: counts[e] for e in REACTS if counts.get(e)}

    async def react_counts(self, ids) -> dict:
        """{id: {emoji: n}} for these messages: from memory, else one grouped query per 200 ids (primary key)."""
        out, miss = {}, []
        for i in ids:
            c = self.reacts.get(i)
            if c is None:
                miss.append(i)
            else:
                out[i] = c
        for k in range(0, len(miss), 200):
            part = miss[k:k + 200]
            got = {i: {} for i in part}
            for r in await self.db.fetch(f"SELECT msg, emoji, COUNT(*) AS n FROM chat_reacts WHERE msg IN ({','.join('?' * len(part))}) "
                                         'GROUP BY msg, emoji', part):
                got.setdefault(int(r['msg']), {})[r['emoji']] = int(r['n'])
            for i, c in got.items():
                out[i] = self.reacts.put(i, c)
        return out

    async def with_reacts(self, p, msgs: list) -> list:
        """The messages with `r` (counts) and `my` (p's own) where they have reactions; copies, never the buffer's
        frames. One more query (p's reactions) only when some message has reactions."""
        ids = [m['id'] for m in msgs if not m.get('del')]
        if not ids:
            return msgs
        counts = await self.react_counts(ids)
        has = [i for i in ids if counts.get(i)]
        if not has:
            return msgs
        mine = {int(r['msg']): r['emoji'] for r in await self.db.fetch(
            f"SELECT msg, emoji FROM chat_reacts WHERE pid=? AND msg IN ({','.join('?' * len(has))})", (p.pid, *has))}
        out = []
        for m in msgs:
            c = None if m.get('del') else counts.get(m['id'])
            if c:
                m = dict(m, r=self._ordered(c))
                if m['id'] in mine:
                    m['my'] = mine[m['id']]
            out.append(m)
        return out

    @on('react', rate=(30, 10))
    async def react(self, conn, f):
        p, mid, e = conn.player, f.get('id'), f.get('e')
        if type(mid) is not int or mid <= 0 or (e is not None and e not in REACTS):
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        if not p.account:
            await self.refresh(p)
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để thả cảm xúc nhé.')
        if p.muted_until > time.time() and not self.is_admin(p):
            raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))
        row = await self.db.fetchrow('SELECT channel, pid, hidden, deleted FROM chat_messages WHERE id=?', (mid,))
        if not row or row['hidden'] or row['deleted'] or row['pid'] in p.hidden:
            raise LiveError('gone', 'Tin nhắn này không còn.')
        if kind_of(row['channel']) not in ('town', 'dm', 'group'):
            raise LiveError('bad', 'Không thả cảm xúc ở đây được.')
        c = await self.member_chan(p, row['channel'])
        t = time.time()

        async def run(tx):
            cur = await tx.fetchval('SELECT emoji FROM chat_reacts WHERE msg=? AND pid=?', (mid, p.pid))
            new = None if e is None or cur == e else e
            if new is None:
                if cur is not None:
                    await tx.execute('DELETE FROM chat_reacts WHERE msg=? AND pid=?', (mid, p.pid))
            else:
                await tx.execute('INSERT INTO chat_reacts(msg, pid, emoji, at) VALUES(?, ?, ?, ?) '
                                 'ON CONFLICT(msg, pid) DO UPDATE SET emoji=excluded.emoji, at=excluded.at', (mid, p.pid, new, t))
            rows = await tx.fetch('SELECT emoji, COUNT(*) AS n FROM chat_reacts WHERE msg=? GROUP BY emoji', (mid,))
            return new, {r['emoji']: int(r['n']) for r in rows}
        new, counts = await self.db.transaction(run)
        self.reacts.put(mid, counts)
        frame = dict(t='reacts', ch=c.id, id=mid, r=self._ordered(counts), by=p.pid, e=new)
        self.send_to_chan(c, frame, sender=p)
        if c.kind == 'town' and conn not in self.town.conns:
            self.hub.send(conn, frame)
        return None

    # ---- resume ---------------------------------------------------------------------------------------------
    async def resume(self, conn, resume) -> None:
        """After a reconnect: what each open chat missed (at most 10 chats, 50 messages each)."""
        if not isinstance(resume, dict):
            return
        p = conn.player
        for ch, after in list(resume.items())[:10]:
            if type(after) is not int or after < 0:
                continue
            try:
                c = await self.member_chan(p, ch)
            except LiveError:
                continue
            if c.kind == 'town':
                continue    # Cả phố: the client joins again with `after`
            rows = await self.db.fetch('SELECT * FROM chat_messages WHERE channel=? AND id>? AND hidden=0 ORDER BY id LIMIT ?',
                                       (c.id, max(after, c.cleared.get(p.pid, 0)), RESUME + 1))
            msgs = await self.without_hides(p, [msg_frame(r) for r in rows[:RESUME] if r['pid'] not in p.hidden])
            msgs = await chat_reply.project(self, p, await self.with_faces(await self.with_reacts(p, msgs)))
            self.hub.send(conn, dict(t='missed', ch=c.id, msgs=msgs, more=len(rows) > RESUME))

    # ---- admin events (game/live_chat.py NOTIFY) -------------------------------------------------------------
    async def renamed(self, sid):
        """Publish only the public identity; the account name comes from the committed profile."""
        ident = await profile(self.db, sid)
        if not ident or not ident.name:
            return
        pid, name = ident.pid, ident.name
        self.names.put(pid, name)
        player = self.hub.players.get(pid)
        if player:
            player.name = name
            for conn in player.conns:
                for room in conn.rooms:
                    resident = room.data.get('people', {}).get(pid)
                    if isinstance(resident, dict) and 'name' in resident:
                        resident['name'] = name  # shared-home snapshots for later entrants
        for other in self.hub.players.values():
            if pid in other.friends:
                other.friends[pid]['name'] = name
        for message in self.town.buffer:
            if message['pid'] == pid:
                message['name'] = name
        if self.pin and self.pin['pid'] == pid:
            self.pin['name'] = name
        # Friends, current DM/group peers, and people sharing an active room can see the label.
        peers = {r['pid'] for r in await self.db.fetch(
            'SELECT DISTINCT peer.pid FROM chat_members mine JOIN chat_members peer ON peer.channel=mine.channel WHERE mine.pid=?', (pid,))}
        peers.add(pid)
        conns = set(self.town.conns)
        for other in self.hub.players.values():
            if other.pid in peers or pid in other.friends:
                conns.update(c for c in other.conns if c.ready)
        if player:
            for conn in player.conns:
                for room in conn.rooms:
                    conns.update(c for c in room.conns if c.ready)
        # Read both block systems now, including changes made through the game HTTP API.
        from types import SimpleNamespace
        visibility = SimpleNamespace(pid=pid, sid=sid, hidden=set())
        await self.load_hidden(visibility)
        conns = [c for c in conns if c.ready and c.player.pid not in visibility.hidden and pid not in c.player.hidden]
        self.hub.send_many(conns, dict(t='renamed', pid=pid, name=name))

    async def on_notify(self, e: dict):
        op = e.get('op')
        if op == 'name' and isinstance(e.get('sid'), str) and re.fullmatch(r'[0-9a-f]{64}', e['sid']):
            await self.renamed(e['sid'])
        elif op == 'hide' and type(e.get('id')) is int and isinstance(e.get('ch'), str):
            await self.gone(e['ch'], e['id'], hidden=True)
        elif op == 'unhide' and type(e.get('id')) is int:
            r = await self.db.fetchrow('SELECT * FROM chat_messages WHERE id=? AND hidden=0', (e['id'],))
            if r:
                frame = dict(msg_frame(r), restore=1)
                if r['channel'] == 'town' and self.town.buffer is not None:
                    ids = [m['id'] for m in self.town.buffer]
                    if r['id'] not in ids and (not ids or r['id'] > ids[0]):
                        items = sorted([*self.town.buffer, msg_frame(r)], key=lambda m: m['id'])
                        self.town.buffer.clear()
                        self.town.buffer.extend(items[-self.cfg.buffer:])
                c = await self.chan(r['channel']) if kind_of(r['channel']) in ('town', 'dm', 'group') else Chan(r['channel'], kind_of(r['channel']))
                if c:
                    await self.deliver_message(c, frame)
        elif op == 'pin':   # scripts/chat_pin.py on PostgreSQL
            await self.sync_pin()
        elif op == 'face' and isinstance(e.get('pid'), str):   # 🙂 a player deleted their data (game/live_chat.py forget)
            self.reply_epoch += 1
            self.names.put(e['pid'], '')
            self.faces.put(e['pid'], '')
            # Account erasure emits this event: invalidate existing quotes on every open screen,
            # while new pages always re-read the source's deleted flag from the database.
            self.hub.send_many([c for c in self.hub.conns if c.ready], dict(t='reply_hidden', pid=e['pid']))
            for m in self.town.buffer:
                if m['pid'] == e['pid']:
                    m['text'], m['del'] = '', 1
                    m.pop('reply_to', None)
            self.chans.clear()  # the erased player was removed from chat_members
            await self.sync_pin()
            p = self.hub.players.get(e['pid'])
            if p:
                p.fc = None
        elif op == 'mute' and isinstance(e.get('pid'), str):
            p = self.hub.players.get(e['pid'])
            if p:
                p.muted_until = float(e.get('until') or 0)
                self.hub.send_many([c for c in p.conns if c.ready], dict(t='muted', until=round(p.muted_until, 1)))

    async def reconcile(self) -> None:
        """The LISTEN connection came back: admin events may have been missed while it was down."""
        ids = [m['id'] for m in self.town.buffer]
        if ids:
            rows = await self.db.fetch(f"SELECT id, hidden FROM chat_messages WHERE id IN ({','.join('?' * len(ids))}) AND hidden<>0", ids)
            for r in rows:
                await self.gone('town', int(r['id']), hidden=True)
        await self.sync_pin()
        pids = list(self.hub.players)
        for i in range(0, len(pids), 500):
            part = pids[i:i + 500]
            got = {r['pid']: float(r['until']) for r in await self.db.fetch(
                f"SELECT pid, until FROM chat_mutes WHERE pid IN ({','.join('?' * len(part))})", part)}
            for pid in part:
                p = self.hub.players.get(pid)
                if p:
                    p.muted_until = got.get(pid, 0.0)
        known = {p.pid: (p.sid, p.name) for p in self.hub.players.values()}
        for p in self.hub.players.values():
            for pid, friend in p.friends.items():
                known.setdefault(pid, (friend['sid'], friend['name']))
        self.names.clear()
        current = await player_names.names_of(self, known)
        for pid, (sid, old_name) in known.items():
            if current.get(pid) and current[pid] != old_name:
                await self.renamed(sid)

    # ---- Cả phố keeps its newest TOWN_KEEP messages -------------------------------------------------------------
    async def tick(self, now: float):
        if not hasattr(self, '_prune_at'):
            self._prune_at = now + 60   # the first pruning a minute after start: a restart stays light
        if now >= self._prune_at:
            self._prune_at = now + PRUNE_EVERY
            await self.prune_town()
        if now >= self._pin_at:   # 📌 a pin written from outside (scripts/chat_pin.py), a message hidden by an admin
            self._pin_at = now + PIN_POLL
            await self.sync_pin()
        if not self.del_ok and now >= self._del_at:   # 🗑️ the game server of SCHEMA_VERSION 13 may have started since
            await self.check_del()

    async def prune_town(self, keep: int = TOWN_KEEP) -> int:
        """Delete Cả phố messages older than the newest `keep` (owner, 01/10: only Cả phố; DMs and groups are never
        touched), with their reports. A message whose report is still open (reported, not reviewed) stays until an
        admin decides; the pinned message stays while it is pinned. Small batches, a few per call: a long backlog goes over several prunings."""
        cut = await self.db.fetchval("SELECT id FROM chat_messages WHERE channel='town' ORDER BY id DESC LIMIT 1 OFFSET ?", (keep,))
        if cut is None:
            return 0
        gone = 0
        for _ in range(5):
            async def run(tx):
                ids = [r['id'] for r in await tx.fetch(
                    "SELECT id FROM chat_messages WHERE channel='town' AND id<=? AND NOT (reports>0 AND reviewed_at IS NULL) "
                    'AND id NOT IN (SELECT msg FROM chat_pins) ORDER BY id LIMIT ?', (cut, PRUNE_BATCH))]
                if ids:
                    marks = ','.join('?' * len(ids))
                    await tx.execute(f"DELETE FROM chat_messages WHERE channel='town' AND id IN ({marks})", ids)
                    await tx.execute(f"DELETE FROM reports WHERE kind='chat' AND target IN ({marks})", [str(i) for i in ids])
                    await tx.execute(f'DELETE FROM chat_reacts WHERE msg IN ({marks})', ids)
                    if self.del_ok:
                        await tx.execute(f'DELETE FROM chat_hides WHERE msg IN ({marks})', ids)
                return len(ids)
            n = await self.db.transaction(run)
            gone += n
            if n:
                for k in [k for k in self.reacts if k <= cut]:
                    self.reacts.pop(k, None)
            if n < PRUNE_BATCH:
                break
        self.town_more = self.town_more and bool(await self.db.fetchval(
            "SELECT 1 FROM chat_messages WHERE channel='town' AND hidden=0 AND id<? LIMIT 1", ((self.town.buffer[0]['id'] if self.town.buffer else 0),)))
        return gone

    # ---- background work ------------------------------------------------------------------------------------
    def spawn(self, coro) -> None:
        if len(self.tasks) > 500:   # bounded: under a flood, a push is skipped rather than queued
            coro.close()
            return
        task = asyncio.ensure_future(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
