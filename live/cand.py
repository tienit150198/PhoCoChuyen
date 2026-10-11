"""👮 Công an phường Mây at Chợ đen (game/cand_ops.py): a stop's moves pushed to the two players' open pages.

No database work here: the game server announces every move of a stop with NOTIFY in that move's own transaction (a
refused move tells nobody):

    {op: 'cand', to: pid, k: 'ask' | 'offer' | 'done', id, act, text, by?, amount?, left?}

and this sends `cand {k, id, act, text, by?, amount?, left?}` to that player's ready sockets: 'ask' to the player
stopped (the page asks: Hợp tác / Đưa phong bì), 'offer' to the officer (an envelope: Nhận / Từ chối), 'done' to
either (the outcome, the page reloads the save). The pid never leaves the service. `welcome.flags.cand` tells the page
the pushes come (without it the page polls POST /api/marriage/cand_poll while it waits). An older page ignores the
frame; the stop still settles by itself (no answer = cooperation).
"""
from __future__ import annotations

import re

from .protocol import Feature

PID_RE = re.compile(r'[0-9a-f]{16}')
ID_RE = re.compile(r'cs[0-9a-f]{16}')
KINDS = ('ask', 'offer', 'done')
ACTS = ('search', 'fine', 'hold', 'arrest')


def frame(event: dict) -> tuple[str, dict] | None:
    """(pid, the frame) of a NOTIFY, or None when it is not a well-formed stop event."""
    if not isinstance(event, dict) or event.get('op') != 'cand':
        return None
    to, k, sid, act = event.get('to'), event.get('k'), event.get('id'), event.get('act')
    if not (isinstance(to, str) and PID_RE.fullmatch(to) and k in KINDS and isinstance(sid, str) and ID_RE.fullmatch(sid)
            and act in ACTS):
        return None
    f = dict(t='cand', k=k, id=sid, act=act, text=event['text'][:200] if isinstance(event.get('text'), str) else '')
    if isinstance(event.get('by'), str):
        f['by'] = event['by'][:40]
    for key in ('amount', 'left'):
        v = event.get(key)
        if type(v) is int and 0 <= v <= 10**6:
            f[key] = v
    return to, f


class CandFeature(Feature):
    name = 'cand'

    async def start(self):
        self.cfg.flags_extra['cand'] = True

    async def on_notify(self, event: dict):
        got = frame(event)
        if not got:
            return
        pid, f = got
        conns = [c for c in self.hub.conns_of(pid) if getattr(c, 'ready', True) and not c.closing]
        if conns:
            self.hub.send_many(conns, f)
