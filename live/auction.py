"""🔨 Nhà đấu giá (game/auction.py): live prices for whoever has the auction house open, on the existing sockets.

No database work here and no polling: the game server announces every accepted bid and every settlement with
NOTIFY (in the bid's own transaction, so only committed bids are told), and this fans them out:

* `auction_watch {open}`: this socket watches the lots (open: false, or closing it, stops). At most WATCH_MAX sockets.
* NOTIFY {op: 'auction', lot, high, n, ends, next, name, lead, prev} → `auction_bid {lot, high, n, ends, next, name}` to
  the watchers (`lead: true` on the leader's own sockets), and `auction_outbid {lot, high}` to the previous leader's
  sockets wherever they are in the game (the page then collects the refund: POST /api/live/effects).
* NOTIFY {op: 'auction_end', lot, status, price, name, win} → `auction_end` to the watchers, `auction_won` to the
  winner's sockets.
A frame carries only what the lot card already shows (never a sid; an anonymous bidder stays "Ẩn danh").
"""
from __future__ import annotations

import re

from .protocol import Feature, LiveError, on

WATCH_MAX = 5000
LOT_RE = re.compile(r'[0-9a-z][0-9a-z\-]{1,23}')
PID_RE = re.compile(r'[0-9a-f]{16}')


def _int(v) -> int | None:
    return v if type(v) is int and 0 <= v <= 10**12 else None


def _lot(v) -> str | None:
    return v if isinstance(v, str) and LOT_RE.fullmatch(v) else None


def _pid(v) -> str | None:
    return v if isinstance(v, str) and PID_RE.fullmatch(v) else None


def _name(v) -> str:
    return v[:24] if isinstance(v, str) else ''


class AuctionFeature(Feature):
    name = 'auction'

    def __init__(self, app):
        super().__init__(app)
        self.viewers: set = set()

    async def start(self):
        self.cfg.flags_extra['auction'] = True

    @on('auction_watch', rate=(20, 10))
    async def watch(self, conn, f):
        if f.get('open') is False:
            self.viewers.discard(conn)
            return None
        if conn not in self.viewers and len(self.viewers) >= WATCH_MAX:
            raise LiveError('busy', 'Đông quá, giá sẽ cập nhật khi mở lại nhé.')
        self.viewers.add(conn)
        return dict(t='auction_on')

    async def on_close(self, conn):
        self.viewers.discard(conn)

    def _watchers(self) -> list:
        out = []
        for c in list(self.viewers):
            if c.closing:
                self.viewers.discard(c)
            else:
                out.append(c)
        return out

    async def on_notify(self, event: dict):
        op = event.get('op')
        if op == 'auction':
            lot, high, n = _lot(event.get('lot')), _int(event.get('high')), _int(event.get('n'))
            ends = event.get('ends')
            if not lot or high is None or n is None or not isinstance(ends, (int, float)):
                return
            frame = dict(t='auction_bid', lot=lot, high=high, n=n, ends=float(ends), next=_int(event.get('next')) or 0,
                         name=_name(event.get('name')))
            lead, prev = _pid(event.get('lead')), _pid(event.get('prev'))
            mine = self.hub.conns_of(lead) if lead else set()
            others = [c for c in self._watchers() if c not in mine]
            if others:
                self.hub.send_many(others, frame)
            if mine:
                self.hub.send_many([c for c in mine if not c.closing], dict(frame, lead=True))
            if prev and prev != lead:
                gone = [c for c in self.hub.conns_of(prev) if not c.closing]
                if gone:
                    self.hub.send_many(gone, dict(t='auction_outbid', lot=lot, high=high))
        elif op == 'auction_end':
            lot = _lot(event.get('lot'))
            status = event.get('status') if event.get('status') in ('sold', 'unsold', 'void') else None
            if not lot or not status:
                return
            frame = dict(t='auction_end', lot=lot, status=status, price=_int(event.get('price')) or 0, name=_name(event.get('name')))
            ws = self._watchers()
            if ws:
                self.hub.send_many(ws, frame)
            win = _pid(event.get('win'))
            if win:
                mine = [c for c in self.hub.conns_of(win) if not c.closing]
                if mine:
                    self.hub.send_many(mine, dict(frame, t='auction_won'))
