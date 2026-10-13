"""Owned interiors share town transport, never the outdoor room or save payload.

At most 200 occupied sites, 30 people/site. Access is checked on entry and social
commands; a bounded five-second sweep evicts idle guests after privacy changes.
Movement uses cached geometry and performs no database work.
"""
import json
import math
import re
import time
from .protocol import LiveError, on

SITE_MAP = 'scale-site-v1'
SITE_PREFIX = SITE_MAP + ':'
SITE_CAP = 30
SITE_ROOMS_MAX = 200
SITE_REFRESH = 5.0
OWNER_SQL = 'SELECT s.state FROM profiles p JOIN sessions s ON s.sid=p.sid WHERE p.pid=?'


def site_key(f):
    owner, career, site = (f.get(k) for k in ('owner', 'career', 'site'))
    if not (isinstance(owner, str) and re.fullmatch('[0-9a-f]{16}', owner)
            and isinstance(career, str) and re.fullmatch('[a-z_]{1,40}', career)
            and isinstance(site, str) and re.fullmatch(r'base|branch-[1-9][0-9]?', site)):
        raise LiveError('bad', 'Mã cơ sở không hợp lệ.')
    return owner, career, site


def public_site(row, career, site):
    try:
        state = json.loads(row['state']) if isinstance(row['state'], str) else row['state']
        scale = state.get('careers', {}).get(career, {}).get('scale', {})
        selected = next((s for s in scale.get('sites', []) if s.get('id') == site), None)
        if not selected or not scale.get('tier'):
            return None
        crew = {c.get('id'): c for c in scale.get('crew', [])}
        # Only the furniture/crew labels necessary to draw the public interior.
        resources = [dict(id=str(r['id'])[:80], site=site, busy=bool(r.get('busy')), crew_name=str(crew.get(r.get('crew'), {}).get('name', ''))[:32])
                     for r in scale.get('resources', []) if r.get('site') == site][:200]
        return dict(cid=career, site=dict(id=site, name=str(selected.get('name', 'Cơ sở'))[:60],
                                         public=selected.get('public') is True), resources=resources)
    except (TypeError, ValueError, KeyError, AttributeError):
        return None


def site_point(data, x, y):
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (x, y)):
        raise LiveError('bad', 'Vị trí không hợp lệ.')
    # Transport units are 20 local pixels: preserve existing speed/proximity budgets.
    px, py = x * 20, y * 20
    boxes = [(20, 265, 65, 25), (350, 260, 65, 25)]
    for i in range(min(6, len(data['resources']))):
        ax, ay = 70 + i % 3 * 145, 95 + i // 3 * 110
        bed = data['cid'] == 'homestay'
        boxes.append((ax - 25, ay - (77 if bed else 48), 50, 65 if bed else 32))
    if not (9 <= px <= 451 and 9 <= py <= 351) or any(
            bx-9 < px < bx+bw+9 and by-9 < py < by+bh+9 for bx, by, bw, bh in boxes):
        raise LiveError('bad', 'Vị trí này có đồ nội thất.')
    return round(float(x), 3), round(float(y), 3)


class ScaleSites:
    async def _site_read(self, owner, career, site):
        if self.db is None:
            raise LiveError('off', 'Chưa kết nối cơ sở trực tuyến.')
        row = await self.db.fetchrow(OWNER_SQL, (owner,))
        return public_site(row, career, site) if row else None

    def _site_evict(self, room, data):
        owner = room.data['site_key'][0]
        for c in list(room.conns):
            if data is None or (c.player.pid != owner and (not data['site']['public'] or self.hub.blocked(c.player.pid, owner))):
                self._leave(c)
                self.hub.send(c, dict(t='town_left', why='private', room=room.id))

    def _site_update(self, room, data):
        if data and self.hub.rooms.get(room.id) is room and data != room.data.get('site_layout'):
            room.data['site_layout'] = data
            corrected = set()
            for pid, walker in room.data['people'].items():
                try:
                    site_point(data, walker.x, walker.y)
                except LiveError:
                    walker.x, walker.y, walker.credit = 11.5, 16.25, 0
                    walker.last = time.monotonic()
                    corrected.add(pid)
                    self._queue(room, pid, dict(k='mv', pid=pid, x=walker.x, y=walker.y, direction=walker.direction))
            for conn in room.conns:
                point = dict(x=11.5, y=16.25) if conn.player.pid in corrected else {}
                self.hub.send(conn, dict(t='town_site', room=room.id, site=data['site'], layout=data, **point))

    async def _site_access(self, conn):
        room, _ = self._me(conn)
        key = room.data.get('site_key')
        if key:
            data = await self._site_read(*key)
            self._site_evict(room, data)
            if conn.ext.get('town') != room.id:
                raise LiveError('private', 'Cơ sở đã đóng cửa đón khách.')
            self._site_update(room, data)
        return room

    async def _refresh_sites(self, now):
        if now < getattr(self, '_sites_at', 0):
            return
        self._sites_at = now + SITE_REFRESH
        # Occupied rooms only; bounded by SITE_ROOMS_MAX, no player/save scan.
        cache = {}
        for room in list(self.hub.rooms_with_prefix(SITE_PREFIX)):
            key = room.data['site_key']
            if key not in cache:
                cache[key] = await self._site_read(*key)
            self._site_evict(room, cache[key])
            self._site_update(room, cache[key])

    @on('site_in', rate=(20, 60))
    async def site_in(self, conn, f):
        from .street import clean_look
        from .town import Walker, clean_direction
        key = site_key(f)
        data = await self._site_read(*key)
        await self._ensure_loaded(conn.player)
        if not data or (conn.player.pid != key[0] and (not data['site']['public'] or self.hub.blocked(conn.player.pid, key[0]))):
            raise LiveError('private', 'Cơ sở không tồn tại hoặc chưa mở đón khách.')
        rid = SITE_PREFIX + ':'.join(key)
        room = self.hub.rooms.get(rid)
        if room and len(room.data['people']) >= SITE_CAP and conn.player.pid not in room.data['people']:
            raise LiveError('full', 'Cơ sở đang đông, lát quay lại nhé.')
        if room is None and len(self.hub.rooms_with_prefix(SITE_PREFIX)) >= SITE_ROOMS_MAX:
            raise LiveError('full', 'Các cơ sở đang đông, lát quay lại nhé.')
        treasure = getattr(self.app, 'by_name', {}).get('treasure')
        if treasure is not None and treasure.enabled():
            await treasure.leave(conn)
        self._leave(conn, 'other', takeover=True)
        # Leaving the last occupant may have dropped this exact room.
        room = self.hub.rooms.get(rid)
        if room is None:
            room = self.hub.room(rid, cap=SITE_CAP, on_empty=self._empty)
            room.data.update(people={}, ev=[], mvi={}, h=None, last=0.0, hidden_seen=set(), site_key=key)
        room.data['site_layout'] = data
        room.add(conn)
        look, gender = clean_look(f.get('look'), f.get('g'))
        w = Walker(conn.player, look, gender, (11.5, 16.25), clean_direction(f.get('direction')))
        room.data['people'][w.pid] = w
        conn.ext['town'] = conn.player.ext['town'] = rid
        self._queue(room, w.pid, dict(k='in', **w.public()))
        return self._social_reply(dict(t='town_room', map=SITE_MAP, room=rid, me=w.pid,
            people=[p.public() for p in room.data['people'].values() if p.pid != w.pid and not self.hub.blocked(w.pid, p.pid)],
            cap=SITE_CAP, social=bool(self.cfg.chat and self.app.chat), owner=key[0],
            site=data['site'], layout=data, x=w.x, y=w.y), f)
