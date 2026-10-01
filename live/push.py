"""Web push for a chat message to a player with no open socket, through the game's own queue
(game/push.py: `push_queue`, delivered by the game server's push loop; same rules as push.queue: only
players with a subscription whose `social` preference is on, at most 6 unsent). One push per chat per
player per `every` seconds (chat_members.pushed_at, so a restart does not reset it). Never for a chat whose
notifications the player turned off (chat_members.muted_until in the future, 🔔 live/chat.py notify)."""
from __future__ import annotations

import json
import time

from .db import Error, log


async def maybe_push(db, channel: str, pid: str, sid: str, body: str, url: str, every: float = 600) -> bool:
    t = time.time()
    try:
        if await db.execute('UPDATE chat_members SET pushed_at=? WHERE channel=? AND pid=? AND pushed_at<? AND muted_until<=?',
                            (t, channel, pid, t - every, t)) != 1:
            return False
        subs = await db.fetch('SELECT prefs FROM push_subs WHERE sid=?', (sid,))
        if not subs or not any(_social(r['prefs']) for r in subs):
            return False
        if await db.fetchval('SELECT COUNT(*) FROM push_queue WHERE sid=? AND sent=0', (sid,)) >= 6:
            return False
        await db.execute("INSERT INTO push_queue(sid, kind, body, url, at) VALUES(?, 'chat', ?, ?, ?)", (sid, body[:200], url[:200], t))
        return True
    except Error as e:
        log('push', type(e).__name__)
        return False


def _social(prefs) -> bool:
    try:
        return bool(json.loads(prefs or '{}').get('social', True))
    except (TypeError, ValueError):
        return True
