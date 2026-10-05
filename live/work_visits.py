"""Ephemeral workplace presence; persisted place access is checked before every event.

The game server owns sanitized snapshots and orders. This service never reads a
save or trusts a client-supplied owner. One controlling tab per visitor, no history.
"""
from __future__ import annotations

import asyncio
import math
import re
import time

from . import jsonx
from .db import Error as DbError
from .fair import clean_point
from .protocol import Feature, LiveError, on
from .street import clean_look

PREFIX, CAP, CHECK_EVERY = 'visit:', 24, 2.0
PLACE = re.compile(r'[A-Za-z0-9_-]{1,80}')
PUBLIC = frozenset(('id','kind','target','name','title','owner','career','open','activity','staff','decor','theme','visibility','status','updated_at'))


def activity(text):
    try:
        data = jsonx.loads(text)
        return {k:v for k,v in data.items() if k in PUBLIC} if isinstance(data,dict) else {}
    except (TypeError,ValueError):
        return {}


# Batch all room memberships in one statement. Blocks include both stores and
# both directions; an owner may still enter their own temporarily closed shop.
ACCESS = """
SELECT v.sid, w.owner, w.data, w.updated_at,
 (v.sid=w.owner OR (w.visibility IN ('public','friends')
   AND (w.visibility='public' OR EXISTS(SELECT 1 FROM friends f WHERE f.sid=w.owner AND f.friend=v.sid))
   AND NOT EXISTS(SELECT 1 FROM marriage_blocks b WHERE (b.sid=w.owner AND b.target=v.sid) OR (b.sid=v.sid AND b.target=w.owner))
   AND NOT EXISTS(SELECT 1 FROM blocks b WHERE
    (b.pid=substring(encode(sha256(convert_to('pid:' || w.owner,'UTF8')),'hex'),1,16) AND b.target=v.pid) OR
    (b.pid=v.pid AND b.target=substring(encode(sha256(convert_to('pid:' || w.owner,'UTF8')),'hex'),1,16))))) AS allowed
FROM (VALUES {values}) AS v(sid,pid) JOIN sessions s ON s.sid=v.sid
JOIN work_visit_places w ON w.id=? JOIN sessions owner_save ON owner_save.sid=w.owner
"""


class WorkVisitsFeature(Feature):
    name, flag = 'visits', 'visits'

    def __init__(self,app):
        super().__init__(app)
        self.check_at = 0.0
        self.seq = 0
        self.join_locks = {}

    def _current(self,conn):
        room = self.hub.rooms.get(conn.ext.get('visit'))
        return room if room and conn.player.ext.get('visit_conn') is conn and conn in room.conns else None

    def _people(self,room):
        return [dict(x) for x in room.data['people'].values()]

    def _tell(self,room):
        room.send(dict(t='visit_people',place=room.data['place'],people=self._people(room)))

    def _detach(self,conn,why=None,tell=True):
        rid = conn.ext.pop('visit',None)
        room = self.hub.rooms.get(rid)
        if conn.player.ext.get('visit_conn') is conn:
            conn.player.ext.pop('visit_conn',None)
            if room:
                room.data['people'].pop(conn.player.pid,None)
                room.data['joined'].pop(conn.player.pid,None)
        if room:
            room.remove(conn)
            if tell and room.conns:self._tell(room)
        if why:self.hub.send(conn,dict(t='visit_left',place=rid[len(PREFIX):] if rid else '',why=why))

    async def _access(self,place,conns):
        if not conns:return []
        args = [x for c in conns for x in (c.player.sid,c.player.pid)]
        return await self.db.fetch(ACCESS.format(values=','.join('(?,?)' for _ in conns)),(*args,place))

    async def _blocked_pairs(self,conns):
        if len(conns)<2:return []
        sids,pids = [c.player.sid for c in conns],[c.player.pid for c in conns]
        marks = ','.join('?' for _ in conns)
        rows = await self.db.fetch(f'SELECT sid AS a,target AS b FROM marriage_blocks WHERE sid IN ({marks}) AND target IN ({marks})',(*sids,*sids))
        social = await self.db.fetch(f'SELECT pid AS a,target AS b FROM blocks WHERE pid IN ({marks}) AND target IN ({marks})',(*pids,*pids))
        sid_to_pid = {c.player.sid:c.player.pid for c in conns}
        return [(sid_to_pid[r['a']],sid_to_pid[r['b']]) for r in rows]+[(r['a'],r['b']) for r in social]

    async def _refresh(self,room):
        conns = list(room.conns)
        try:
            rows = await self._access(room.data['place'],conns)
            pairs = await self._blocked_pairs(conns)
        except DbError:
            for c in conns:self._detach(c,'changed',tell=False)
            raise
        allowed = {r['sid'] for r in rows if r['allowed']}
        removed = False
        # Only detach the later arrival of a blocked pair. Never broadcast their
        # identity to one another while revoking membership.
        kicked = set()
        for a,b in pairs:
            joined=room.data['joined']
            kicked.add(max((a,b),key=lambda p:joined.get(p,0)))
        for c in conns:
            if self._current(c) is room and (c.player.sid not in allowed or c.player.pid in kicked):
                self._detach(c,'changed',tell=False);removed=True
        if self.hub.rooms.get(room.id) is not room:return
        if removed:self._tell(room)
        if rows and rows[0]['updated_at'] != room.data.get('updated'):
            room.data.update(updated=rows[0]['updated_at'],activity=activity(rows[0]['data']))
            room.send(dict(t='visit_activity',place=room.data['place'],activity=room.data['activity']))

    async def _check(self,conn):
        room=self._current(conn)
        if room is None:raise LiveError('no_visit','Bạn chưa ở chỗ làm này.')
        await self._refresh(room)
        if self._current(conn) is not room:raise LiveError('no_visit','Chỗ làm đã đổi quyền đón khách.')
        return room

    @on('visit_in',rate=(20,60))
    async def visit_in(self,conn,f):
        place=f.get('place')
        if not isinstance(place,str) or not PLACE.fullmatch(place):raise LiveError('bad','Chỗ làm không hợp lệ.')
        # Serialize membership admission for this workplace, including waiters:
        # two blocked strangers joining simultaneously cannot miss one another.
        entry=self.join_locks.setdefault(place,[asyncio.Lock(),0]);entry[1]+=1
        try:
            async with entry[0]:
                return await self._join(conn,f,place)
        finally:
            entry[1]-=1
            if not entry[1]:self.join_locks.pop(place,None)

    async def _join(self,conn,f,place):
        point=clean_point([f.get('x'),f.get('y')]) if 'x' in f or 'y' in f else [.5,.8]
        look,gender=clean_look(f.get('look'),f.get('g'))
        p=conn.player;ticket=(conn,object());p.ext['visit_join']=ticket
        rows=await self._access(place,[conn])
        room=self.hub.rooms.get(PREFIX+place)
        if room:await self._refresh(room)
        peers=list(room.conns) if room else []
        pairs=await self._blocked_pairs([conn]+[c for c in peers if c.player.pid!=p.pid])
        if p.ext.get('visit_join') is not ticket or conn.closing or conn not in p.conns:return
        if not rows or not rows[0]['allowed'] or any(p.pid in pair for pair in pairs):
            raise LiveError('no_visit','Chỗ làm đang đóng hoặc chưa đón bạn lúc này.')
        old=p.ext.get('visit_conn')
        if old:self._detach(old,'other' if old is not conn else None)
        room=self.hub.room(PREFIX+place,cap=CAP,on_empty=lambda r:self.hub.drop_room(r.id))
        if not room.data:room.data.update(place=place,people={},joined={},updated=rows[0]['updated_at'],activity=activity(rows[0]['data']))
        if not room.add(conn):raise LiveError('full','Tiệm đang đông, bạn ghé lại sau một chút nhé.')
        self.seq+=1
        room.data['joined'][p.pid]=self.seq
        room.data['people'][p.pid]=dict(pid=p.pid,name=p.name,fc=p.fc,av=p.av,lk=look,g=gender,x=point[0],y=point[1])
        conn.ext['visit']=room.id;p.ext['visit_conn']=conn
        self._tell(room)
        return dict(t='visit_state',place=place,me=p.pid,people=self._people(room),activity=room.data['activity'],cap=CAP)

    @on('visit_out',rate=(30,60))
    async def visit_out(self,conn,f):
        joining=conn.player.ext.get('visit_join')
        if joining and joining[0] is conn:conn.player.ext.pop('visit_join',None)
        rid=conn.ext.get('visit','')
        self._detach(conn)
        return dict(t='visit_left',place=rid[len(PREFIX):] if rid else '',why='out')

    @on('visit_mv',rate=(4,1))
    async def visit_mv(self,conn,f):
        path,ms=f.get('p'),f.get('ms')
        if not isinstance(path,list) or len(path)!=2 or type(ms) not in (int,float) or not math.isfinite(ms):raise LiveError('bad','Vị trí không hợp lệ.')
        path=[clean_point(v) for v in path]
        room=await self._check(conn)
        person=room.data['people'][conn.player.pid]
        path[0]=[person['x'],person['y']]
        person['x'],person['y']=path[-1]
        room.send(dict(t='visit_mv',place=room.data['place'],pid=conn.player.pid,p=path,ms=int(min(3000,max(0,ms)))))

    @on('visit_emote',rate=(6,10))
    async def visit_emote(self,conn,f):
        kind=f.get('kind')
        if kind not in ('wave','heart','cheer'):raise LiveError('bad','Chọn cử chỉ hợp lệ nhé.')
        room=await self._check(conn)
        room.send(dict(t='visit_emote',place=room.data['place'],pid=conn.player.pid,kind=kind))

    @on('visit_chat',rate=(6,10))
    async def visit_chat(self,conn,f):
        text=f.get('text')
        if not isinstance(text,str) or not text.strip() or len(text)>300:raise LiveError('bad','Lời nhắn từ 1 đến 300 ký tự nhé.')
        if conn.player.muted_until and conn.player.muted_until > time.time():raise LiveError('muted','Bạn đang tạm ngừng gửi tin nhắn.')
        room=await self._check(conn)
        text=' '.join(text.split())
        room.send(dict(t='visit_chat',place=room.data['place'],pid=conn.player.pid,name=conn.player.name,text=text))

    async def on_close(self,conn):
        self._detach(conn)

    async def tick(self,now):
        if now<self.check_at:return
        self.check_at=now+CHECK_EVERY
        for room in list(self.hub.rooms_with_prefix(PREFIX)):
            try:await self._refresh(room)
            except (LiveError,*DbError):pass
