"""🧧 Lì xì cả phố (game/lixi.py): envelopes on every open screen and a card in Cả phố, not only a line of text.

The game server announces a paid packet with NOTIFY in the giver's own transaction (a refused command shows nothing)
and every grab with another:

    {op: 'lixi', id, pid, name, n, left, total, wish, at, exp}      a new packet
    {op: 'lixi_upd', id, left, done}                                an envelope taken, the last one, the 24 h sweep

This sends `lixi {id, name, n, left, total, wish, at, exp, ago}` and `lixi_upd {id, left, done}` to every ready socket
wherever the player is (the page lets envelopes fall over the screen and keeps the card in Cả phố: public/js/v4/lixi.js,
lixi-cards.js). A player who blocked the giver, or was blocked by them (Player.hidden, either way), gets the packet
without the name and the wish and with `no: true` (the game server refuses their grab anyway). The giver's pid never
leaves the service. No database work on the way: the packets still open are kept here (at most KEEP), read once at
start (an older database without the table: none), and a page that connects gets them in its welcome (`lx`), so a
reload or a player coming online later still sees the cards; GET /api/lixi has the whole last day. An older page
ignores both frames and the welcome key.
"""
from __future__ import annotations

import re
import time

from .db import Error as DbError, log
from .protocol import Feature

KEEP = 120                        # open packets kept for the welcome (game/lixi.py has no OPEN_MAX since 17/10)
RAIN = 60.0                       # seconds after the start a new socket still gets the falling envelopes (`ago` tells the page)
ID_RE = re.compile(r'lx[0-9a-f]{14}')
PID_RE = re.compile(r'[0-9a-f]{16}')
CTRL = re.compile(r'[\x00-\x1f\x7f​-‏ -‮⁦-⁩]')


def _text(v, n: int) -> str:
    return CTRL.sub('', v).strip()[:n] if isinstance(v, str) else ''


def _int(v, lo: int, hi: int) -> int | None:
    return v if type(v) is int and lo <= v <= hi else None


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 2**34 else None


class LixiFeature(Feature):
    name = 'lixi'

    def __init__(self, app):
        super().__init__(app)
        self.open: dict = {}          # id -> dict(id, pid, name, n, left, total, wish, at, exp)

    async def start(self):
        if self.db is None:
            return
        try:
            rows = await self.db.fetch("SELECT id, pid, name, n, left_n, total, wish, text, at, expires FROM lixi_packets "
                                       "WHERE status='open' AND expires>? ORDER BY at DESC LIMIT ?", (time.time(), KEEP))
        except DbError as e:   # the table comes with the game server's SCHEMA_VERSION 51: until then, none
            log('lixi start:', type(e).__name__)
            return
        except Exception as e:  # noqa: BLE001 - a missing table on an older database is not a reason to stop
            log('lixi start:', type(e).__name__)
            return
        for r in reversed(rows):
            from game.lixi import wish_text
            self._keep(dict(id=r['id'], pid=r['pid'], name=_text(r['name'], 24), n=int(r['n']), left=int(r['left_n']),
                            total=int(r['total']), wish=_text(wish_text(r['wish'], r['text']), 48), at=float(r['at']),
                            exp=float(r['expires'])))

    def _keep(self, p: dict) -> None:
        self.open[p['id']] = p
        t = time.time()
        for k in [k for k, x in self.open.items() if x['exp'] <= t or x['left'] <= 0]:
            self.open.pop(k, None)
        while len(self.open) > KEEP:
            self.open.pop(min(self.open, key=lambda k: self.open[k]['at']))

    @staticmethod
    def _plain(p: dict, hide: bool, now: float) -> dict:
        out = dict(id=p['id'], name='' if hide else p['name'], n=p['n'], left=p['left'], total=p['total'],
                   wish='' if hide else p['wish'], at=p['at'], exp=p['exp'], ago=round(max(0.0, now - p['at']), 1))
        if hide:
            out['no'] = True
        return out

    def _ready(self) -> list:
        return [c for c in self.hub.conns if c.ready and not c.closing]

    async def on_notify(self, event: dict):
        op = event.get('op')
        if op == 'lixi':
            pk = event.get('id')
            n, left, total = _int(event.get('n'), 1, 100), _int(event.get('left'), 0, 100), _int(event.get('total'), 1, 10**9)
            at, exp = _num(event.get('at')), _num(event.get('exp'))
            if not (isinstance(pk, str) and ID_RE.fullmatch(pk)) or None in (n, left, total, at, exp) or pk in self.open:
                return
            pid = event['pid'] if isinstance(event.get('pid'), str) and PID_RE.fullmatch(event['pid']) else ''
            p = dict(id=pk, pid=pid, name=_text(event.get('name'), 24), n=n, left=left, total=total, wish=_text(event.get('wish'), 48),
                     at=at, exp=exp)
            self._keep(p)
            t = time.time()
            full, quiet = [], []
            for c in self._ready():
                (quiet if pid and self.hub.blocked(c.player.pid, pid) else full).append(c)
            if full:
                self.hub.send_many(full, dict(t='lixi', **self._plain(p, False, t)))
            if quiet:
                self.hub.send_many(quiet, dict(t='lixi', **self._plain(p, True, t)))
        elif op == 'lixi_upd':
            pk, left = event.get('id'), _int(event.get('left'), 0, 100)
            if not (isinstance(pk, str) and ID_RE.fullmatch(pk)) or left is None:
                return
            done = event.get('done') is True or left == 0
            p = self.open.get(pk)
            if p:
                p['left'] = left
                if done:
                    self.open.pop(pk, None)
            conns = self._ready()
            if conns:
                self.hub.send_many(conns, dict(t='lixi_upd', id=pk, left=left, done=done))

    def welcome(self, conn) -> dict:
        t = time.time()
        live = [p for p in self.open.values() if p['exp'] > t and p['left'] > 0]
        if not live:
            return {}
        me = conn.player.pid
        return dict(lx=[self._plain(p, bool(p['pid']) and self.hub.blocked(me, p['pid']), t)
                        for p in sorted(live, key=lambda x: x['at'])])
