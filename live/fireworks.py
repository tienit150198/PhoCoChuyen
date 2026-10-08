"""🎆 Pháo hoa cả phố (game/lux.py, Mạnh Thường Quân): the show on every open screen, not only a line of text.

Owner 08/10: "pháo hoa bé và pháo hoa lớn, phải có bắn toàn server cho mọi người thấy chứ k phải là chỉ có chữ nhé. Và
có thông báo dài luôn". The game server announces a paid show with NOTIFY in the purchase's own transaction (so a
refused command shows nothing):

    {op: 'fireworks', id, pid, size, name, wish, at}

and this sends `fireworks {id, size, name, wish, ago}` to every ready socket, wherever the player is in the game (the
page draws the bursts and a long banner: public/js/v4/fireworks.js). A player who blocked the giver, or was blocked by
them (Player.hidden, either way), still sees the sky but not who or the wish (`name` and `wish` empty). The pid never
leaves the service (the game's id holds it, so a page gets a random key instead: an anonymous giver stays anonymous).
Shows may come back to back (gap 0 since 08/10, game/lux_content.py): each page queues them; a repeated id is
dropped (the page queues anyway).

Late arrivals: a page that connects within LATE seconds of the start gets the same show in its welcome (`fw`, with
`ago`), so a reload or a player coming online right after still sees the banner. An older page ignores both.
"""
from __future__ import annotations

import re
import secrets
import time

from .protocol import Feature

LATE = 45.0                       # seconds after the start a new socket still gets the show (welcome `fw`)
SIZE_RE = re.compile(r'[a-z0-9_]{1,16}')
ID_RE = re.compile(r'[0-9a-f]{16}:[0-9]{1,10}')
PID_RE = re.compile(r'[0-9a-f]{16}')
CTRL = re.compile(r'[\x00-\x1f\x7f​-‏ -‮⁦-⁩]')


def _text(v, n: int) -> str:
    return CTRL.sub('', v).strip()[:n] if isinstance(v, str) else ''


class FireworksFeature(Feature):
    name = 'fireworks'

    def __init__(self, app):
        super().__init__(app)
        self.last: dict | None = None     # the latest show: dict(id, key (the id pages see), pid, size, name, wish, seen: when it reached this service)

    async def on_notify(self, event: dict):
        if event.get('op') != 'fireworks':
            return
        fid, size = event.get('id'), event.get('size')
        if not (isinstance(fid, str) and ID_RE.fullmatch(fid) and isinstance(size, str) and SIZE_RE.fullmatch(size)):
            return
        if self.last and self.last['id'] == fid:
            return
        pid = event.get('pid') if isinstance(event.get('pid'), str) and PID_RE.fullmatch(event['pid']) else ''
        t = time.time()
        show = dict(id=fid, key=secrets.token_hex(6), pid=pid, size=size, name=_text(event.get('name'), 24), wish=_text(event.get('wish'), 40), seen=t)
        self.last = show
        full, quiet = [], []
        for c in self.hub.conns:
            if not c.ready or c.closing:
                continue
            (quiet if pid and self.hub.blocked(c.player.pid, pid) else full).append(c)
        if full:
            self.hub.send_many(full, self._plain(show, False, t))
        if quiet:
            self.hub.send_many(quiet, self._plain(show, True, t))

    @staticmethod
    def _plain(show: dict, hide: bool, now: float) -> dict:
        return dict(t='fireworks', id=show['key'], size=show['size'], name='' if hide else show['name'],
                    wish='' if hide else show['wish'], ago=round(max(0.0, now - show['seen']), 1))

    def welcome(self, conn) -> dict:
        show, t = self.last, time.time()
        if not show or t - show['seen'] > LATE:
            return {}
        hide = bool(show['pid']) and self.hub.blocked(conn.player.pid, show['pid'])
        f = self._plain(show, hide, t)
        f.pop('t')
        return dict(fw=f)
