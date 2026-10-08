"""💌 Thiệp mời cưới cả phố (game/wed_invite.py): tell every open page that a new card is out.

The game server announces a paid card with NOTIFY in the payment's own transaction (a refused send tells nobody):

    {op: 'wedinvite', id, pids: [the sender's pid, the partner's pid]}

and this sends `wedinvite {id}` to every ready socket except the couple's own and anyone who blocked either of them
or was blocked by them (Player.hidden). The frame carries no text: the page asks GET /api/wedinvite a moment later and
the game server decides what this player is shown (once, at most a few a day, blocks again). The pids never leave
the service. An older page ignores the frame; a page that connects later gets the card when it loads.
"""
from __future__ import annotations

import re

from .protocol import Feature

PID_RE = re.compile(r'[0-9a-f]{16}')


class WedInviteFeature(Feature):
    name = 'wedinvite'

    def __init__(self, app):
        super().__init__(app)
        self.last = 0                      # the newest card announced (a repeated NOTIFY is dropped)

    async def on_notify(self, event: dict):
        if event.get('op') != 'wedinvite':
            return
        cid = event.get('id')
        if type(cid) is not int or cid <= self.last:
            return
        self.last = cid
        pids = [p for p in (event.get('pids') or []) if isinstance(p, str) and PID_RE.fullmatch(p)][:2]
        out = []
        for c in self.hub.conns:
            if not c.ready or c.closing:
                continue
            me = c.player.pid
            if me in pids or any(self.hub.blocked(me, p) for p in pids):
                continue
            out.append(c)
        if out:
            self.hub.send_many(out, dict(t='wedinvite', id=cid))
