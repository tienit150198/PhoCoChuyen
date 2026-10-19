"""Nearby speech uses the chat's storage/moderation; movement remains memory-only."""
from collections import OrderedDict
import math
import secrets
import time

from .protocol import LiveError, on

TALK_PREFIX = 'iso-talk:'
SOCIAL_RANGE = 8.0
EMOTES = frozenset(('👋', '❤️', '😂', '😮', '🙏', '👏', '👍'))
RECEIPTS_MAX, RECEIPT_TTL = 4096, 600


class Audience:
    """A message's actual recipients, never an entire room's later occupants."""
    def __init__(self, town, room, pids, author):
        self.town, self.room, self.pids, self.author = town, room, frozenset(pids), author
        self.until = time.monotonic() + RECEIPT_TTL

    def allows(self, player):
        return (time.monotonic() < self.until and player.pid in self.pids
                and (not self.room.data.get('site_key') or player.ext.get('town') == self.room.id)
                and not self.town.hub.blocked(player.pid, self.author))

    def send(self, frame, sender=None, skip=None):
        hub = self.town.hub
        if hub.rooms.get(self.room.id) is not self.room:
            return 0
        return hub.send_many([c for c in self.room.conns if c is not skip and c.ready
                              and self.allows(c.player)
                              and (sender is None or not hub.blocked(c.player.pid, sender.pid))], frame)


class TownSocial:
    """Mixin: handlers are discovered by TownFeature's existing dispatcher."""
    async def start(self):
        self.social_receipts = OrderedDict()
        if self.app.chat:
            self.app.chat.route(TALK_PREFIX, self._social_audience, self._social_can_read)

    @staticmethod
    def _social_reply(out, request):
        cid = request.get('cid')
        return dict(out, cid=cid) if isinstance(cid, str) and len(cid) <= 40 else out

    def _social_prune(self):
        now = time.monotonic()
        while self.social_receipts:
            first = next(iter(self.social_receipts))
            if len(self.social_receipts) <= RECEIPTS_MAX and self.social_receipts[first].until > now:
                break
            self.social_receipts.popitem(last=False)

    def _social_audience(self, ch):
        self._social_prune()
        a = self.social_receipts.get(ch)
        return [a] if a else []

    def _social_can_read(self, player, ch):
        self._social_prune()
        a = self.social_receipts.get(ch)
        return bool(a and a.allows(player))

    def _social_near(self, a, b):
        return (a.activity is None and b.activity is None
                and math.hypot(a.x - b.x, a.y - b.y) <= SOCIAL_RANGE
                and not self.hub.blocked(a.pid, b.pid))

    async def _social_me(self, conn, fresh_mute=False):
        await self._site_access(conn)
        room, w = self._me(conn)
        if not self.cfg.chat or self.app.chat is None:
            raise LiveError('off', 'Trò chuyện đang tạm nghỉ.')
        if w.activity is not None:
            raise LiveError('not_in', 'Quay lại phố để trò chuyện nhé.')
        p = conn.player
        if not p.account:
            await self.app.chat.refresh(p)
        if not p.account:
            raise LiveError('account', 'Tạo tài khoản để tương tác nhé.')
        if p.muted_until > time.time():
            raise LiveError('muted', 'Bạn đang bị tạm khóa chat.')
        if fresh_mute:
            until = await self.db.fetchval('SELECT until FROM chat_mutes WHERE pid=?', (p.pid,))
            if until and float(until) > time.time():
                p.muted_until = float(until)
                raise LiveError('muted', 'Bạn đang bị tạm khóa chat.')
        # refresh() awaits DB; a second tab may have taken over meanwhile.
        current, current_w = self._me(conn)
        if current is not room or current_w is not w or w.activity is not None:
            raise LiveError('not_in', 'Bạn đã rời khu phố này.')
        return room, w

    def _social_other(self, room, w, pid):
        other = room.data['people'].get(pid) if isinstance(pid, str) else None
        if other is None or other is w or not self._social_near(w, other):
            raise LiveError('gone', 'Bạn ấy đã đi xa hoặc không còn ở gần đây.')
        return other

    @on('town_say', rate=(3, 10))
    async def town_say(self, conn, f):
        room, w = await self._social_me(conn)
        ch = TALK_PREFIX + secrets.token_hex(12)
        # Snapshot the audience before storage; never admit newcomers during await.
        recipients = {o.pid for o in room.data['people'].values() if self._social_near(w, o)}
        frame = await self.app.chat.store_message(conn.player, ch, f.get('text'), 120, 2)
        current, current_w = self._me(conn)
        if current is not room or current_w is not w or w.activity is not None:
            raise LiveError('not_in', 'Bạn đã rời khu phố này.')
        targets = {o.pid for o in room.data['people'].values()
                   if o.pid in recipients and self._social_near(w, o)}
        audience = Audience(self, room, targets, w.pid)
        self.social_receipts[ch] = audience
        self._social_prune()
        out = dict(t='town_said', room=room.id, ch=ch, pid=w.pid, name=conn.player.name,
                   id=frame['id'], text=frame['text'], at=frame['at'])
        audience.send(out, sender=conn.player, skip=conn)
        return self._social_reply(out, f)

    @on('town_emote', rate=(4, 4))
    async def town_emote(self, conn, f):
        room, w = await self._social_me(conn, fresh_mute=True)
        emoji, target = f.get('e'), f.get('target')
        if not isinstance(emoji, str) or emoji not in EMOTES:
            raise LiveError('bad', 'Không có biểu cảm này.')
        other = self._social_other(room, w, target) if target is not None else None
        out = dict(t='town_emoted', room=room.id, pid=w.pid, e=emoji)
        if other:
            out['target'] = other.pid
        # Both ends must be visible to a spectator of a targeted interaction.
        targets = {o.pid for o in room.data['people'].values() if self._social_near(w, o)
                   and (other is None or self._social_near(other, o))}
        Audience(self, room, targets, w.pid).send(out, sender=conn.player, skip=conn)
        return self._social_reply(out, f)

    @on('town_card', rate=(20, 60))
    async def town_card(self, conn, f):
        await self._site_access(conn)
        room, w = self._me(conn)
        other = self._social_other(room, w, f.get('pid'))
        if not self.cfg.chat or not self.app.chat:
            raise LiveError('off', 'Trò chuyện đang tạm nghỉ.')
        await self.app.chat.load_friends(conn.player)
        code = None
        friend = other.pid in conn.player.friends
        if not friend and conn.player.account and other.player.account:
            # Same public friend code and creation rules as the existing walk card.
            street = self.app.by_name.get('street')
            if street:
                code = await street._code(other.player.sid)
        current, current_w = self._me(conn)
        if current is not room or current_w is not w:
            raise LiveError('gone', 'Bạn đã rời khu phố này.')
        other = self._social_other(room, w, other.pid)
        out = dict(t='town_card', room=room.id, pid=other.pid, name=other.player.name,
                   friend=friend, account=other.player.account, code=code)
        if getattr(other, 'bg', None):   # ⚔️ the bang tag (live/bangs.py)
            out['bg'] = dict(other.bg)
        return self._social_reply(out, f)

    async def prune_social_messages(self, now=None, batch=200):
        """Keep a day for recall; pending reports remain until an admin reviews them.

        One call deletes at most 200 messages. The channel range and ordering use
        chat_messages_channel(channel, id), avoiding a scan through private chat.
        """
        if self.db is None or self.app.chat is None:
            return 0
        cutoff = (time.time() if now is None else now) - 86400
        limit = min(200, max(1, int(batch)))

        async def run(tx):
            ids = [int(r['id']) for r in await tx.fetch(
                "SELECT id FROM chat_messages WHERE channel>=? AND channel<? "
                "AND channel LIKE 'iso-talk:%' AND at<? "
                'AND NOT (reports>0 AND reviewed_at IS NULL) '
                'ORDER BY channel,id LIMIT ? FOR UPDATE SKIP LOCKED',
                (TALK_PREFIX, 'iso-talk;', cutoff, limit))]
            if not ids:
                return []
            marks = ','.join('?' for _ in ids)
            await tx.execute(f"DELETE FROM reports WHERE kind='chat' AND target IN ({marks})", [str(i) for i in ids])
            await tx.execute(f'DELETE FROM chat_reacts WHERE msg IN ({marks})', ids)
            if self.app.chat.del_ok:
                await tx.execute(f'DELETE FROM chat_hides WHERE msg IN ({marks})', ids)
            await tx.execute(f'DELETE FROM chat_messages WHERE id IN ({marks})', ids)
            return ids

        ids = await self.db.transaction(run)
        for mid in ids:
            self.app.chat.reacts.pop(mid, None)
        return len(ids)
