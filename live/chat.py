"""💬 Chat (switch LIVE_CHAT): friend DMs, groups, "Cả phố", presence, unread, reports, blocks, mutes.

Channels
* `town` (Cả phố): everyone with a session reads it while it is on their screen (`join`/`leave`); posting
  needs a name, a session older than 10 minutes, and waits 10 s between two messages (slow mode).
* `dm:<pidA>:<pidB>` (pids sorted): two friends (`friends` both ways, no block either way). Created by the
  first `send {to: pid}`. A friend with no socket gets one web push per chat per 10 minutes at most.
* `g:<10 hex>`: a group made by its owner from their friends, at most 20 members; the owner adds and removes,
  anyone leaves (the oldest member becomes owner when the owner leaves).

Frames (client → server; replies in brackets)
  sync {}                                   [state {friends, chans}]
  join {ch:'town', after?}  leave {ch}      [joined {ch, msgs, more, wait, why}]
  send {ch | to, text, cid}                 [msg {..., cid} to me; msg to the others]
  history {ch, before?}                     [history {ch, msgs, more}]
  read {ch, id}                             [read {ch, id} to my other tabs]
  del {id}                                  [deleted {ch, id} to everyone who sees it]
  report {id, reason}  block {pid}  unblock {pid}
  prefs {online: bool}                      [prefs {online}]
  group_new {title, pids}  group_add {ch, pids}  group_kick {ch, pid}  group_leave {ch}  members {ch}
Server pushes: msg, deleted, presence {pid, on}, chan {chan}, unchan {ch}, muted {until}, read.

Phase 2/3 reuse store_message() for anything players type (bubbles, date chat) and route() so deletes,
reports and admin hides reach their rooms.
"""
from __future__ import annotations

import asyncio
import re
import secrets
import time

from . import filters
from .auth import pid_of, profile
from .limits import LRU
from .protocol import Feature, LiveError, on
from .push import maybe_push

CH_DM = re.compile(r'dm:([0-9a-f]{16}):([0-9a-f]{16})')
CH_GROUP = re.compile(r'g:[0-9a-f]{10}')
PID = re.compile(r'[0-9a-f]{16}')
REASONS = ('spam', 'rude', 'private', 'scam', 'other')
HIDE_AFTER = 3            # distinct reports that hide a message until an admin decides
DUP_SECS = 120            # the same text again in the same chat within this: dropped
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
    __slots__ = ('id', 'kind', 'title', 'owner', 'members')

    def __init__(self, cid, kind, title='', owner=None, members=None):
        self.id, self.kind, self.title, self.owner = cid, kind, title, owner
        self.members: dict = members if members is not None else {}   # pid -> sid (dm, group)


def msg_frame(r: dict) -> dict:
    f = dict(t='msg', ch=r['channel'], id=int(r['id']), pid=r['pid'], name=r['name'], av=r['av'], text=r['text'], at=round(float(r['at']), 3))
    if r.get('deleted'):
        f['text'], f['del'] = '', 1
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

    # ---- loading a player -----------------------------------------------------------------------------------
    async def load_friends(self, p) -> None:
        rows = await self.db.fetch('SELECT f.friend AS sid, a.display AS name, pr.avatar AS av FROM friends f '
                                   'LEFT JOIN accounts a ON a.sid=f.friend LEFT JOIN profiles pr ON pr.sid=f.friend '
                                   'WHERE f.sid=? ORDER BY f.since DESC LIMIT ?', (p.sid, FRIENDS_MAX))
        from .auth import AVATARS, clean_name
        p.friends = {pid_of(r['sid']): dict(sid=r['sid'], name=clean_name(r['name']) or 'Một người chơi',
                                            av=r['av'] if r['av'] in AVATARS else '🌸') for r in rows}

    async def load_hidden(self, p) -> None:
        a = await self.db.fetch('SELECT target AS x FROM blocks WHERE pid=? UNION SELECT pid AS x FROM blocks WHERE target=?', (p.pid, p.pid))
        b = await self.db.fetch('SELECT target AS x FROM marriage_blocks WHERE sid=? UNION SELECT sid AS x FROM marriage_blocks WHERE target=?', (p.sid, p.sid))
        p.hidden = {r['x'] for r in a} | {pid_of(r['x']) for r in b}

    async def chan_list(self, p) -> list:
        rows = await self.db.fetch(
            'SELECT c.id, c.kind, c.title, c.owner_pid, m.last_read, m.role, '
            'COALESCE((SELECT MAX(x.id) FROM chat_messages x WHERE x.channel=c.id), 0) AS last_id, '
            '(SELECT COUNT(*) FROM chat_members y WHERE y.channel=c.id) AS n '
            'FROM chat_members m JOIN chat_channels c ON c.id=m.channel WHERE m.pid=? ORDER BY last_id DESC LIMIT ?', (p.pid, CHANS_LISTED))
        if not rows:
            return []
        ids = [r['id'] for r in rows]
        marks = ','.join('?' * len(ids))
        unread = {r['ch']: int(r['n']) for r in await self.db.fetch(
            'SELECT m.channel AS ch, COUNT(x.id) AS n FROM chat_members m JOIN chat_messages x ON x.channel=m.channel '
            'AND x.id>m.last_read AND x.pid<>m.pid AND x.deleted=0 AND x.hidden=0 WHERE m.pid=? GROUP BY m.channel', (p.pid,))}
        lasts = [r['last_id'] for r in rows if r['last_id']]
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
        out = []
        for r in rows:
            c = dict(id=r['id'], kind=r['kind'], title=r['title'], unread=unread.get(r['id'], 0), read=int(r['last_read']))
            if r['kind'] == 'group':
                c.update(owner=r['owner_pid'], n=int(r['n']), role=r['role'])
            if r['id'] in peers:
                c['peer'] = peers[r['id']]
                c['peer']['on'] = p.show_online and self.hub.visible(c['peer']['pid'])
            m = last.get(r['id'])
            if m and m['hidden'] == 0 and m['pid'] not in p.hidden:
                c['last'] = msg_frame(m)
            out.append(c)
        return out

    def friend_list(self, p) -> list:
        return [dict(pid=k, name=v['name'], av=v['av'], on=bool(p.show_online and self.hub.visible(k)))
                for k, v in p.friends.items() if k not in p.hidden]

    def can_town(self, p) -> tuple[str, float]:
        """('ok', 0) or (why, seconds to wait): 'muted', 'account' (a guest: only accounts chat, owner 01/10),
        'new' (session < 10 min), 'name' (no name yet)."""
        t = time.time()
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

    async def on_hello(self, conn):
        p = conn.player
        if not p.loaded:
            await self.load_friends(p)
            await self.load_hidden(p)
            p.loaded = True
        conn.ext['chans'] = await self.chan_list(p)

    def welcome(self, conn) -> dict:
        p = conn.player
        why, wait = self.can_town(p)
        return dict(me=dict(pid=p.pid, name=p.name, av=p.av, account=p.account, online=p.show_online,
                            town=why, wait=round(wait, 1), muted=round(p.muted_until, 1) if p.muted_until > time.time() else 0),
                    friends=self.friend_list(p), chans=conn.ext.pop('chans', []),
                    limits=dict(town_every=self.cfg.town_every, town_len=self.cfg.town_len, text_len=self.cfg.text_len, group_max=self.cfg.group_max))

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
        members = {r['pid']: r['sid'] for r in await self.db.fetch('SELECT pid, sid FROM chat_members WHERE channel=?', (cid,))}
        return self.chans.put(cid, Chan(cid, row['kind'], row['title'], row['owner_pid'], members))

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

    # ---- storing a message (also for phase 2/3 channels) -----------------------------------------------------
    async def store_message(self, p, ch: str, text, limit: int, lines: int = 4) -> dict:
        """Check, filter and insert one message by player p in channel ch; returns its `msg` frame.
        Raises LiveError: text (empty/too long), name, muted, dup."""
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
        if p.muted_until > t:
            raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))
        fp = filters.fingerprint(clean)
        if any(c == ch and f == fp and t - at < DUP_SECS for c, f, at in p.recent):
            raise LiveError('dup', 'Bạn vừa gửi câu này rồi.')
        masked = filters.mask(clean)
        row = await self.db.fetchrow(
            'INSERT INTO chat_messages(channel, pid, name, av, text, at) SELECT ?, ?, ?, ?, ?, ? '
            'WHERE NOT EXISTS (SELECT 1 FROM chat_mutes WHERE pid=? AND until>?) RETURNING id',
            (ch, p.pid, p.name, p.av, masked, t, p.pid, t))
        if not row:
            until = await self.db.fetchval('SELECT until FROM chat_mutes WHERE pid=?', (p.pid,))
            p.muted_until = float(until or 0)
            raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))
        p.recent.append((ch, fp, t))
        return dict(t='msg', ch=ch, id=int(row['id']), pid=p.pid, name=p.name, av=p.av, text=masked, at=round(t, 3))

    # ---- handlers ------------------------------------------------------------------------------------------
    @on('sync', rate=(6, 60))
    async def sync(self, conn, f):
        p = conn.player
        await self.refresh(p)
        await self.load_friends(p)
        await self.load_hidden(p)
        why, wait = self.can_town(p)
        return dict(t='state', friends=self.friend_list(p), chans=await self.chan_list(p), town=why, wait=round(wait, 1),
                    online=p.show_online, me=dict(pid=p.pid, name=p.name, av=p.av, account=p.account, online=p.show_online,
                                                  town=why, wait=round(wait, 1), muted=round(p.muted_until, 1) if p.muted_until > time.time() else 0))

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
        why, wait = self.can_town(p)
        return dict(t='joined', ch='town', msgs=msgs, more=more, inc=inc, why=why, wait=round(wait, 1), n=len(self.town.players()))

    @on('leave', rate=(20, 10))
    async def leave(self, conn, f):
        if f.get('ch') == 'town':
            self.town.remove(conn)

    @on('send', rate=(12, 10))
    async def send(self, conn, f):
        p, t = conn.player, time.time()
        cid = f.get('cid') if isinstance(f.get('cid'), str) and len(f.get('cid')) <= 40 else None
        if f.get('to') is not None and f.get('ch') is None:
            c = await self.open_dm(p, f.get('to'))
        else:
            c = await self.member_chan(p, f.get('ch'))
        if c.kind == 'town':
            if not p.name or not p.account:
                await self.refresh(p)   # a guest who just registered can post at once, no reconnect
            why, wait = self.can_town(p)
            if why == 'account':
                raise LiveError('account', 'Tạo tài khoản để chat nhé.')
            if why == 'new':
                raise LiveError('new', 'Người mới vào phố đọc trước, lát nữa nhắn nhé.', wait=round(wait, 1))
            if why == 'name':
                raise LiveError('name', 'Đặt tên nhân vật trước khi nhắn nhé.')
            if why == 'muted':
                raise LiveError('muted', 'Bạn đang bị tạm khóa chat.', until=round(p.muted_until, 1))
            if wait > 0:
                raise LiveError('slow', f'Cả phố: {self.cfg.town_every:g} giây một tin.', wait=round(wait, 1))
            p.town_next = t + self.cfg.town_every          # before the await: a second tab cannot slip in
            try:
                frame = await self.store_message(p, 'town', f.get('text'), self.cfg.town_len, 3)
            except BaseException:
                p.town_next = 0.0
                raise
            self.town.buffer.append(frame)
            n = len({c.player.pid for c in self.town.conns})
            self.town.send(dict(frame, n=n), sender=p, skip=conn)   # n: people on Cả phố now
            self.hub.send(conn, dict(frame, cid=cid, wait=self.cfg.town_every, n=n))
            return None
        if c.kind == 'dm':
            other = next((x for x in c.members if x != p.pid), None)
            if not other or not await self.friendship(p, other):
                raise LiveError('not_friend', 'Hai bạn không còn là bạn bè, không nhắn riêng được nữa.')
        frame = await self.store_message(p, c.id, f.get('text'), self.cfg.text_len, 12)
        self.send_to_chan(c, frame, sender=p, skip=conn)
        self.hub.send(conn, dict(frame, cid=cid, to=f.get('to')) if f.get('to') else dict(frame, cid=cid))
        if c.kind == 'dm':
            other = next(x for x in c.members if x != p.pid)
            if not self.hub.online(other):
                self.spawn(maybe_push(self.db, c.id, other, c.members[other], f'{p.name}: {frame["text"][:80]}', f'/?chat={c.id}', PUSH_EVERY))
        return None

    @on('history', rate=(20, 10))
    async def history(self, conn, f):
        p = conn.player
        ch = f.get('ch')
        r = self._route(ch) if isinstance(ch, str) else None
        if r:
            if not r[1](p, ch):
                raise LiveError('no_chat', 'Không tìm thấy cuộc trò chuyện này.')
        else:
            await self.member_chan(p, ch)
        before = f.get('before')
        if type(before) is not int or before <= 0:
            before = 2 ** 62
        rows = await self.db.fetch('SELECT * FROM chat_messages WHERE channel=? AND id<? AND hidden=0 ORDER BY id DESC LIMIT ?',
                                   (ch, before, PAGE + 1))
        more = len(rows) > PAGE
        msgs = [msg_frame(r) for r in reversed(rows[:PAGE]) if r['pid'] not in p.hidden]
        return dict(t='history', ch=ch, msgs=msgs, more=more, before=f.get('before'))

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
        p, mid = conn.player, f.get('id')
        if type(mid) is not int or mid <= 0:
            raise LiveError('bad', 'Yêu cầu không hợp lệ.')
        row = await self.db.fetchrow("UPDATE chat_messages SET text='', deleted=1 WHERE id=? AND pid=? AND deleted=0 RETURNING channel", (mid, p.pid))
        if not row:
            raise LiveError('gone', 'Không thu hồi được tin này.')
        await self.gone(row['channel'], mid, hidden=False)
        return None

    async def gone(self, ch: str, mid: int, hidden: bool) -> None:
        """A message left everyone's screen: deleted by its author (the text is gone) or hidden (moderation)."""
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

    @on('report', rate=(10, 60))
    async def report(self, conn, f):
        p, mid, reason = conn.player, f.get('id'), f.get('reason', 'other')
        if type(mid) is not int or mid <= 0 or reason not in REASONS:
            raise LiveError('bad', 'Báo cáo không hợp lệ.')
        row = await self.db.fetchrow('SELECT channel, pid FROM chat_messages WHERE id=?', (mid,))
        if not row:
            raise LiveError('gone', 'Không tìm thấy tin nhắn.')
        if row['pid'] == p.pid:
            raise LiveError('bad', 'Đây là tin của bạn.')
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
        await self.db.execute('INSERT INTO blocks(pid, target, at) VALUES(?, ?, ?) ON CONFLICT(pid, target) DO NOTHING', (p.pid, other, time.time()))
        p.hidden.add(other)
        o = self.hub.players.get(other)
        if o:
            o.hidden.add(p.pid)
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
        self._push_chan(c)
        return None

    @on('group_kick', rate=(20, 600))
    async def group_kick(self, conn, f):
        p, x = conn.player, f.get('pid')
        c = await self._own_group(p, f.get('ch'))
        if x == p.pid or x not in c.members:
            raise LiveError('bad', 'Người này không ở trong nhóm.')
        await self.db.execute('DELETE FROM chat_members WHERE channel=? AND pid=?', (c.id, x))
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
        out = [dict(pid=r['pid'], role=r['role'], name=clean_name(r['display']) or clean_name(r['gname']) or 'Một người chơi',
                    av=r['avatar'] if r['avatar'] in AVATARS else '🌸', friend=r['pid'] in p.friends,
                    on=bool(p.show_online and self.hub.visible(r['pid']))) for r in rows]
        return dict(t='members', ch=c.id, members=out, owner=c.owner, title=c.title)

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
                                       (c.id, after, RESUME + 1))
            msgs = [msg_frame(r) for r in rows[:RESUME] if r['pid'] not in p.hidden]
            self.hub.send(conn, dict(t='missed', ch=c.id, msgs=msgs, more=len(rows) > RESUME))

    # ---- admin events (game/live_chat.py NOTIFY) -------------------------------------------------------------
    async def on_notify(self, e: dict):
        op = e.get('op')
        if op == 'hide' and type(e.get('id')) is int and isinstance(e.get('ch'), str):
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
                    self.send_to_chan(c, frame)
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
        pids = list(self.hub.players)
        for i in range(0, len(pids), 500):
            part = pids[i:i + 500]
            got = {r['pid']: float(r['until']) for r in await self.db.fetch(
                f"SELECT pid, until FROM chat_mutes WHERE pid IN ({','.join('?' * len(part))})", part)}
            for pid in part:
                p = self.hub.players.get(pid)
                if p:
                    p.muted_until = got.get(pid, 0.0)

    # ---- Cả phố keeps its newest TOWN_KEEP messages -------------------------------------------------------------
    async def tick(self, now: float):
        if not hasattr(self, '_prune_at'):
            self._prune_at = now + 60   # the first pruning a minute after start: a restart stays light
        if now >= self._prune_at:
            self._prune_at = now + PRUNE_EVERY
            await self.prune_town()

    async def prune_town(self, keep: int = TOWN_KEEP) -> int:
        """Delete Cả phố messages older than the newest `keep` (owner, 01/10: only Cả phố; DMs and groups are never
        touched), with their reports. A message whose report is still open (reported, not reviewed) stays until an
        admin decides. Small batches, a few per call: a long backlog goes over several prunings."""
        cut = await self.db.fetchval("SELECT id FROM chat_messages WHERE channel='town' ORDER BY id DESC LIMIT 1 OFFSET ?", (keep,))
        if cut is None:
            return 0
        gone = 0
        for _ in range(5):
            async def run(tx):
                ids = [r['id'] for r in await tx.fetch(
                    "SELECT id FROM chat_messages WHERE channel='town' AND id<=? AND NOT (reports>0 AND reviewed_at IS NULL) "
                    'ORDER BY id LIMIT ?', (cut, PRUNE_BATCH))]
                if ids:
                    marks = ','.join('?' * len(ids))
                    await tx.execute(f"DELETE FROM chat_messages WHERE channel='town' AND id IN ({marks})", ids)
                    await tx.execute(f"DELETE FROM reports WHERE kind='chat' AND target IN ({marks})", [str(i) for i in ids])
                return len(ids)
            n = await self.db.transaction(run)
            gone += n
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
