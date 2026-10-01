"""Who is on a socket: the `mnl_session` cookie resolved exactly like game/storage.py Store.resolve
(sha256 of the token → `logins` → the account's save; else the token's own hash, unless an account owns
it: a rotated pre-registration cookie stops working), then a save that exists. Nothing of the save is read.

    pid      the public id, sha256('pid:' + sid)[:16] (game/social.py pid_of)
    name     the account's display name, else the guest's character name (leaderboard_players, kept by every
             command), else the Phố nghề name; '' = not named yet (can read, cannot post)
    av       the Phố nghề avatar (default 🌸)
    age      for "new sessions read-only on Cả phố": born before today (stat_births, Vietnam day) = old; else
             the oldest of the account's creation, the profile's, the first played command (stat_play)
"""
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from http.cookies import CookieError, SimpleCookie

COOKIE = 'mnl_session'
TOKEN = re.compile(r'[0-9a-f]{64}')
_NAME_BAD = re.compile(r'[\x00-\x1f\x7f<>&"`]')
DEFAULT_NAME = 'Mây'      # game/accounts.py DEFAULT_NAME: the unnamed character
AVATARS = ('🌸', '☕', '🍜', '🎉', '💪', '🌈', '🍀', '⭐', '🧁', '🎁', '🧑‍🍳', '👩‍🏫', '🧑‍💼', '🧑‍🌾', '🐱', '🐶')


def pid_of(sid: str) -> str:
    return hashlib.sha256(('pid:' + sid).encode()).hexdigest()[:16]


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def token_from(cookie_header: str | None) -> str | None:
    if not cookie_header:
        return None
    try:
        c = SimpleCookie()
        c.load(cookie_header)
    except CookieError:
        return None
    v = c[COOKIE].value if COOKIE in c else None
    return v if v and TOKEN.fullmatch(v) else None


def clean_name(name) -> str:
    text = _NAME_BAD.sub('', str(name or '')).strip()
    if text == DEFAULT_NAME:
        return ''
    return text[:24]


def vn_today(t: float | None = None) -> str:
    return (datetime.fromtimestamp(time.time() if t is None else t, timezone.utc) + timedelta(hours=7)).strftime('%Y-%m-%d')


def _utc_text(s) -> float | None:
    try:
        return datetime.strptime(str(s), '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


@dataclass
class Ident:
    sid: str
    pid: str
    name: str
    av: str
    account: bool
    old: bool                 # older than the "new session" window for sure
    since: float | None       # the oldest known timestamp of this player (None: never seen)
    online: bool              # "hiện online" (chat_prefs, default on)
    muted_until: float


_SQL = """
SELECT (SELECT 1 FROM sessions WHERE sid=?) AS has,
       (SELECT display FROM accounts WHERE sid=?) AS display,
       (SELECT created_at FROM accounts WHERE sid=?) AS acreated,
       (SELECT name FROM leaderboard_players WHERE sid=?) AS gname,
       (SELECT name FROM profiles WHERE sid=?) AS pname,
       (SELECT avatar FROM profiles WHERE sid=?) AS avatar,
       (SELECT created FROM profiles WHERE sid=?) AS pcreated,
       (SELECT day FROM stat_births WHERE sid=?) AS born,
       (SELECT MIN(first_at) FROM stat_play WHERE sid=?) AS first_play,
       (SELECT online FROM chat_prefs WHERE pid=?) AS online,
       (SELECT until FROM chat_mutes WHERE pid=?) AS muted
"""


async def resolve_sid(db, token: str) -> str | None:
    h = digest(token)
    row = await db.fetchrow('SELECT (SELECT sid FROM logins WHERE token=?) AS lsid, '
                            '(SELECT 1 FROM accounts WHERE sid=?) AS owned', (h, h))
    if row and row['lsid']:
        return row['lsid']
    if row and row['owned']:
        return None   # this cookie was rotated when its save became an account: only a login row reaches it
    return h


async def identify(db, token: str | None) -> Ident | None:
    """The player behind a cookie token, or None (no token, unknown save, revoked cookie)."""
    if not token or not TOKEN.fullmatch(token):
        return None
    sid = await resolve_sid(db, token)
    if not sid:
        return None
    pid = pid_of(sid)
    r = await db.fetchrow(_SQL, (sid,) * 9 + (pid, pid))
    if not r or not r['has']:
        return None
    name = clean_name(r['display']) or clean_name(r['gname']) or clean_name(r['pname'])
    av = r['avatar'] if r['avatar'] in AVATARS else '🌸'
    stamps = [x for x in (_utc_text(r['acreated']), r['pcreated'], r['first_play']) if x]
    old = bool(r['born']) and str(r['born']) < vn_today()
    return Ident(sid=sid, pid=pid, name=name, av=av, account=r['display'] is not None, old=old,
                 since=float(min(stamps)) if stamps else None, online=r['online'] is None or bool(r['online']),
                 muted_until=float(r['muted'] or 0))
