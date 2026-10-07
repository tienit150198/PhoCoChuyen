"""🎙️ The SFU for Phòng hát's live mic (LiveKit server, self-hosted: deploy/livekit/README.md).

Only the live service talks to it, and only for two things:
* tokens: a LiveKit access token is a JWT (HS256) signed with the API secret. `token()` makes one for ONE SFU room
  and ONE identity (the player's pid): the stage singer gets `canPublish` for the microphone only and nothing else
  (no data, no metadata, no subscribing); a listener gets `canSubscribe` only and is `hidden` (listeners never see
  each other). No token ever carries `recorder`, `roomRecord`, `roomAdmin` or `roomCreate` for a player.
* the server API (Twirp over HTTP on 127.0.0.1, an admin token made per call): CreateRoom before any token is
  given (the SFU's `room.auto_create` is off: a token for a deleted room joins nothing), DeleteRoom to cut a mic
  (every participant, the singer included, is disconnected at once), RemoveParticipant (a listener who blocked the
  singer, or who left the room), ListRooms (stale rooms after a restart).

Nothing here records: LiveKit records only through its separate Egress service, which is not installed, and no
grant here allows it. Settings (live/config.py): LIVEKIT_URL (what browsers open: wss://…), LIVEKIT_API_URL
(the server API, default http://127.0.0.1:7880), LIVEKIT_API_KEY, LIVEKIT_API_SECRET.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request

from .db import log

SOURCE = 'microphone'
API_TIMEOUT = 3.0
ADMIN_TTL = 60


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def sign(claims: dict, secret: str) -> str:
    """A compact JWT, HS256 (what LiveKit verifies)."""
    head = _b64(json.dumps(dict(alg='HS256', typ='JWT'), separators=(',', ':')).encode())
    body = _b64(json.dumps(claims, separators=(',', ':'), ensure_ascii=False).encode())
    mac = hmac.new(secret.encode(), f'{head}.{body}'.encode('ascii'), hashlib.sha256).digest()
    return f'{head}.{body}.{_b64(mac)}'


def verify(token: str, secret: str, now: float | None = None) -> dict | None:
    """The claims of a token signed with `secret` and valid now; None otherwise (tests, and a check of our own)."""
    try:
        head, body, mac = token.split('.')
        want = hmac.new(secret.encode(), f'{head}.{body}'.encode('ascii'), hashlib.sha256).digest()
        if not hmac.compare_digest(want, _unb64(mac)) or json.loads(_unb64(head)).get('alg') != 'HS256':
            return None
        claims = json.loads(_unb64(body))
    except (ValueError, TypeError):
        return None
    t = time.time() if now is None else now
    if not (claims.get('nbf', 0) - 5 <= t < claims.get('exp', 0)):
        return None
    return claims


def room_name(rid: str, e: str, n: int) -> str:
    """The SFU room of one mic session: one Phòng hát room, one song (its ticket `e`), the n-th time the singer
    turned the mic on during it. A new song or a new mic session never reuses a name, so an old token joins nothing."""
    return f'{rid.replace(":", "-")}.{hashlib.sha256(e.encode()).hexdigest()[:10]}.{int(n)}'


class Sfu:
    def __init__(self, url: str = '', api: str = '', key: str = '', secret: str = '', timeout: float = API_TIMEOUT):
        self.url, self.api, self.key, self.secret, self.timeout = url, (api or '').rstrip('/'), key, secret, timeout
        self.calls = self.fails = 0

    @property
    def configured(self) -> bool:
        return bool(self.url and self.api and self.key and self.secret)

    def token(self, identity: str, name: str, room: str, *, publish: bool, ttl: float, now: float | None = None) -> str:
        """A player's token for one SFU room: the singer publishes the microphone only; a listener only listens."""
        t = int(time.time() if now is None else now)
        if publish:
            video = dict(room=room, roomJoin=True, canPublish=True, canPublishSources=[SOURCE], canSubscribe=False,
                         canPublishData=False, canUpdateOwnMetadata=False)
        else:
            video = dict(room=room, roomJoin=True, canPublish=False, canPublishSources=[], canSubscribe=True,
                         canPublishData=False, canUpdateOwnMetadata=False, hidden=True)
        claims = dict(iss=self.key, sub=identity, name=(name or '')[:40], nbf=t - 2, exp=t + max(10, int(ttl)), jti=f'{identity}:{room}', video=video)
        return sign(claims, self.secret)

    def _admin(self, room: str | None = None) -> str:
        t = int(time.time())
        video = dict(roomCreate=True, roomList=True, roomAdmin=True)
        if room:
            video['room'] = room
        return sign(dict(iss=self.key, sub='mnl-live', nbf=t - 2, exp=t + ADMIN_TTL, video=video), self.secret)

    def _post(self, method: str, body: dict, room: str | None) -> dict | None:
        req = urllib.request.Request(f'{self.api}/twirp/livekit.RoomService/{method}', data=json.dumps(body).encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self._admin(room)})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:   # noqa: S310 - the local SFU's API
                raw = r.read(1 << 20)
            return json.loads(raw or b'{}')
        except urllib.error.HTTPError as e:
            if e.code == 404 and method in ('DeleteRoom', 'RemoveParticipant'):
                return {}   # already gone: that is what we wanted
            log('sfu:', method, e.code)
        except (urllib.error.URLError, OSError, ValueError) as e:
            log('sfu:', method, type(e).__name__)
        return None

    async def call(self, method: str, body: dict, room: str | None = None) -> dict | None:
        if not self.configured:
            return None
        self.calls += 1
        out = await asyncio.to_thread(self._post, method, body, room)
        if out is None:
            self.fails += 1
        return out

    async def create_room(self, room: str, max_participants: int, empty_timeout: int = 60) -> bool:
        return await self.call('CreateRoom', dict(name=room, max_participants=max_participants, empty_timeout=empty_timeout,
                                                   departure_timeout=10), room) is not None

    async def delete_room(self, room: str) -> bool:
        return await self.call('DeleteRoom', dict(room=room), room) is not None

    async def remove(self, room: str, identity: str) -> bool:
        return await self.call('RemoveParticipant', dict(room=room, identity=identity), room) is not None

    async def rooms(self) -> list:
        out = await self.call('ListRooms', {})
        return [r.get('name', '') for r in (out or {}).get('rooms') or []]

    async def participants(self, room: str) -> list:
        out = await self.call('ListParticipants', dict(room=room), room)
        return (out or {}).get('participants') or []
