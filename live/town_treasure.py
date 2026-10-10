"""Treasure cadence, live-only proximity attestations and persisted entry anchors.

No save is read on movement. Checkpoints batch public positions every two seconds;
each account has one current lease across tabs and service workers. A new/restarted
socket resumes that anchor rather than accepting arbitrary browser coordinates.
"""
from __future__ import annotations

import hashlib
import secrets
import time

from game import town_treasure as tt
from .protocol import Feature, LiveError, on

CHECKPOINT = 2.0
REFRESH = 15.0


class TownTreasureFeature(Feature):
    name, flag = 'treasure', 'treasure'

    def __init__(self, app):
        super().__init__(app)
        self.snapshot = None
        self.refresh_at = self.checkpoint_at = 0.0

    async def refresh(self, broadcast=False):
        at = tt.now()
        bucket = int(at // tt.PERIOD)
        async def work(db):
            if await db.fetchrow(tt.INSERT_WAVE, (bucket,)):
                for row in tt.spawn_rows(bucket):
                    await db.execute(tt.INSERT_CHEST, row)
                for sql, args in tt.cleanup_sql(bucket, at):
                    await db.execute(sql, args)
            return await db.fetch(tt.SELECT_CHESTS, (bucket,))
        rows = await self.db.transaction(work)
        old = self.snapshot
        self.snapshot = tt.view(rows, at)
        self.refresh_at = time.monotonic() + REFRESH
        if broadcast or not old or old['wave']['id'] != self.snapshot['wave']['id'] or old['chests'] != self.snapshot['chests']:
            self.hub.send_many([c for c in self.hub.conns if c.ready], dict(t='town_treasure', **self.snapshot))
        return self.snapshot

    async def on_hello(self, conn):
        if self.enabled() and (not self.snapshot or self.snapshot['wave']['expires_at'] <= tt.now()):
            await self.refresh()

    def welcome(self, conn):
        return dict(treasure=self.snapshot) if self.enabled() and self.snapshot else {}

    async def enter(self, conn):
        """Called only from authenticated town_in; returns authoritative x/y."""
        from .town import clean_point
        if not conn.player.account:
            return None
        sid, lease, at = conn.player.sid, secrets.token_hex(16), tt.now()
        async def work(db):
            await db.execute('INSERT INTO town_treasure_presence(sid,lease,map_id,x,y,seen_at,online) VALUES(?,?,?,?,?,?,1) ON CONFLICT(sid) DO NOTHING',
                             (sid,lease,tt.MAP_ID,*tt.START,at))
            row = await db.fetchrow('SELECT * FROM town_treasure_presence WHERE sid=? FOR UPDATE', (sid,))
            try:
                point = clean_point(row['x'], row['y']) if row['map_id'] == tt.MAP_ID else tt.START
            except LiveError:
                point = tt.START
            await db.execute('UPDATE town_treasure_presence SET lease=?,map_id=?,x=?,y=?,seen_at=?,online=1 WHERE sid=?',
                             (lease,tt.MAP_ID,*point,at,sid))
            await db.execute('DELETE FROM town_treasure_proofs WHERE sid=?', (sid,))
            return point
        point = await self.db.transaction(work)
        conn.ext['treasure_lease'] = lease
        return point

    async def leave(self, conn):
        lease = conn.ext.pop('treasure_lease', None)
        if lease:
            await self.db.execute('UPDATE town_treasure_presence SET online=0 WHERE sid=? AND lease=?', (conn.player.sid,lease))

    async def on_close(self, conn):
        if self.enabled():
            await self.leave(conn)

    async def checkpoint(self):
        from .town import PREFIX
        at, mono = tt.now(), time.monotonic()
        updates = []
        for room in self.hub.rooms_with_prefix(PREFIX):
            for conn in room.conns:
                w = room.data['people'].get(conn.player.pid)
                lease = conn.ext.get('treasure_lease')
                if w and lease and conn.ready and not conn.closing:
                    updates.append((conn.player.sid, lease, w.x, w.y, at - max(0.0, mono - w.last), 0 if w.activity else 1))
        # One SQL statement per 250 walkers, never a query per movement frame.
        for start in range(0, len(updates), 250):
            batch = updates[start:start + 250]
            values = ','.join('(?,?,?::double precision,?::double precision,?::double precision,?::bigint)' for _ in batch)
            await self.db.execute('UPDATE town_treasure_presence p SET x=v.x,y=v.y,seen_at=v.seen_at,online=v.online FROM (VALUES '+values+
                                  ') v(sid,lease,x,y,seen_at,online) WHERE p.sid=v.sid AND p.lease=v.lease AND p.seen_at<=v.seen_at',
                                  tuple(v for row in batch for v in row))

    @on('town_treasure_prepare', rate=(12, 60))
    async def prepare(self, conn, frame):
        if not conn.player.account:
            raise LiveError('treasure_account', 'Đăng nhập tài khoản để nhặt kho báu.')
        town = self.app.by_name['town']
        _, w = town._me(conn)
        at = tt.now()
        chest_id = frame.get('chest_id')
        if not isinstance(chest_id, str) or not tt.CHEST.fullmatch(chest_id):
            raise LiveError('treasure_bad', 'Mã rương không hợp lệ.')
        lease = conn.ext.get('treasure_lease')
        age = time.monotonic() - w.last
        if not lease or w.activity is not None or not 0 <= age <= tt.POSITION_TTL:
            raise LiveError('treasure_presence', 'Hãy đi sát rương trong phố rồi thử lại.')
        proof = secrets.token_hex(24)
        async def work(db):
            chest = await db.fetchrow('SELECT * FROM town_treasure_chests WHERE id=?', (chest_id,))
            if not chest or chest['bucket'] != int(at // tt.PERIOD):
                raise LiveError('treasure_expired', 'Rương này đã hết hạn.')
            if chest['winner']:
                raise LiveError('treasure_taken', 'Một người khác đã nhặt rương này.')
            position = dict(map_id=tt.MAP_ID,x=w.x,y=w.y,seen_at=at-age,online=1)
            if not tt.near(position,chest,at):
                raise LiveError('treasure_presence', 'Hãy đi sát rương trong phố rồi thử lại.')
            changed = await db.execute('UPDATE town_treasure_presence SET x=?,y=?,seen_at=?,online=1 WHERE sid=? AND lease=?',
                                      (w.x,w.y,at-age,conn.player.sid,lease))
            if changed != 1:
                raise LiveError('treasure_presence', 'Vị trí đã chuyển sang cửa sổ khác. Vào lại phố nhé.')
            await db.execute('INSERT INTO town_treasure_proofs(sid,chest_id,proof_hash,lease,created_at) VALUES(?,?,?,?,?) '
                             'ON CONFLICT(sid) DO UPDATE SET chest_id=excluded.chest_id,proof_hash=excluded.proof_hash,lease=excluded.lease,created_at=excluded.created_at',
                             (conn.player.sid,chest_id,hashlib.sha256(proof.encode()).hexdigest(),lease,at))
        await self.db.transaction(work)
        out = dict(t='town_treasure_ready',chest_id=chest_id,proof=proof,expires_at=at+tt.PROOF_TTL)
        if isinstance(frame.get('cid'),str) and len(frame['cid'])<=40:
            out['cid']=frame['cid']
        return out

    async def tick(self, now):
        if not self.snapshot or self.snapshot['wave']['expires_at'] <= tt.now() or time.monotonic() >= self.refresh_at:
            await self.refresh()
        if time.monotonic() >= self.checkpoint_at:
            self.checkpoint_at = time.monotonic() + CHECKPOINT
            await self.checkpoint()

    async def on_notify(self, event):
        if self.enabled() and event.get('kind') == 'town_treasure':
            await self.refresh(broadcast=True)
