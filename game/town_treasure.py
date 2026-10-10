"""One global treasure wave per real UTC ten-minute bucket.

Only the live service writes short-lived position proofs. HTTP resolves the login
again, locks its save and the chest, and pays the fixed reward in that same
transaction. No browser coordinates or reward amount enter this operation.
"""
from __future__ import annotations

import json
import math
import os
import re
import secrets
import time
from functools import lru_cache

from .engine import migrate_state, public_state
from .storage import serialize, _archive_rows, _write_archive
from . import archive, journey, leaderboard

PERIOD = 600
REWARD = 10000
RADIUS = 1.6
PROOF_TTL = 5.0
POSITION_TTL = 12.0
AUDIT_BUCKETS = 144
MAP_ID = 'iso-town-v1'
START = (6.0, 6.0)
REQUEST = re.compile(r'[A-Za-z0-9._:-]{8,80}')
CHEST = re.compile(r'tt-[0-9]{1,12}-[0-4]')
INSERT_WAVE = 'INSERT INTO town_treasure_waves(bucket) VALUES(?) ON CONFLICT(bucket) DO NOTHING RETURNING bucket'
INSERT_CHEST = 'INSERT INTO town_treasure_chests(id,bucket,map_id,x,y) VALUES(?,?,?,?,?)'
SELECT_CHESTS = 'SELECT id,bucket,map_id,x,y,winner FROM town_treasure_chests WHERE bucket=? ORDER BY id'


class TreasureError(ValueError):
    def __init__(self, message, code='treasure_bad', status=400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(ok, message, code='treasure_bad', status=400):
    if not ok:
        raise TreasureError(message, code, status)


def now():
    return time.time()


def enabled():
    return all(os.environ.get(k, '').strip().lower() in ('1', 'true', 'yes', 'on')
               for k in ('LIVE_TOWN', 'LIVE_TOWN_TREASURE'))


@lru_cache(maxsize=1)
def locations():
    # Public authored service approaches are known reachable ground. Interiors,
    # player homes and unrelated room coordinate spaces are never candidates.
    from live.town import _LAYOUT, clean_point
    from live.protocol import LiveError
    candidates = set()
    for place in _LAYOUT['amenities'] + _LAYOUT['lots']:
        p = place.get('door') or place.get('at')
        if not isinstance(p, dict):
            continue
        try:
            candidates.add(clean_point(p.get('x'), p.get('y')))
        except LiveError:
            pass
    if len(candidates) < 5:
        raise RuntimeError('Treasure requires at least five public reachable approaches')
    return tuple(sorted(candidates))


def spawn_rows(bucket):
    points = secrets.SystemRandom().sample(locations(), 3 + secrets.randbelow(3))
    return [(f'tt-{bucket}-{i}', bucket, MAP_ID, x, y) for i, (x, y) in enumerate(points)]


def view(rows, at, on=True):
    bucket = int(at // PERIOD)
    chests = [dict(id=r['id'], map_id=r['map_id'], x=r['x'], y=r['y'], claimed=bool(r['winner'])) for r in rows]
    return dict(enabled=on, server_time=at,
                wave=dict(id=str(bucket), starts_at=bucket * PERIOD, expires_at=(bucket + 1) * PERIOD,
                          reward=REWARD, notice=f'{len(chests)} rương kho báu vừa xuất hiện trong phố! Mỗi rương có 10.000 xu.') if on else None,
                chests=chests)


def cleanup_sql(bucket, at):
    return [('DELETE FROM town_treasure_waves WHERE bucket<?', (bucket - AUDIT_BUCKETS,)),
            ('DELETE FROM town_treasure_proofs WHERE created_at<?', (at - PROOF_TTL,)),
            ('DELETE FROM town_treasure_presence WHERE seen_at<?', (at - 86400,))]


def ensure_wave(db, at):
    bucket = int(at // PERIOD)
    if db.execute(INSERT_WAVE, (bucket,)).fetchone():
        db.executemany(INSERT_CHEST, spawn_rows(bucket))
        for sql, args in cleanup_sql(bucket, at):
            db.execute(sql, args)
    return db.execute(SELECT_CHESTS, (bucket,)).fetchall()


def snapshot(store):
    at = now()
    if not enabled():
        return view([], at, False)
    return store.transaction(lambda db: view(ensure_wave(db, at), at))


def near(position, chest, at):
    return (position and position['online'] and position['map_id'] == chest['map_id']
            and 0 <= at - position['seen_at'] <= POSITION_TTL
            and math.hypot(position['x'] - chest['x'], position['y'] - chest['y']) <= RADIUS)


def claim(store, token, data):
    need(enabled(), 'Kho báu đang tắt.', 'treasure_off', 404)
    chest_id, proof, request_id = (data.get(k) for k in ('chest_id', 'proof', 'request_id'))
    need(isinstance(chest_id, str) and CHEST.fullmatch(chest_id), 'Mã rương không hợp lệ.')
    need(isinstance(request_id, str) and REQUEST.fullmatch(request_id), 'Mã yêu cầu không hợp lệ.')
    need(isinstance(proof, str) and re.fullmatch(r'[a-f0-9]{48}', proof), 'Cần xác nhận vị trí trực tiếp.', 'treasure_presence', 403)

    def write(db):
        # Same session-first lock order as Store.command and account switches.
        sid, csrf = store._resolve(db, store.digest(token))
        need(csrf and db.execute('SELECT 1 FROM accounts WHERE sid=?', (sid,)).fetchone(),
             'Đăng nhập tài khoản để nhặt kho báu.', 'treasure_account', 403)
        saved = db.execute('SELECT state,revision FROM sessions WHERE sid=? FOR UPDATE', (sid,)).fetchone()
        need(saved, 'Phiên chơi không tồn tại.', 'session_missing', 401)
        chest = db.execute('SELECT * FROM town_treasure_chests WHERE id=? FOR UPDATE', (chest_id,)).fetchone()
        at = now()  # Lock waits must not extend a wave or a proof's lifetime.
        need(chest, 'Rương này đã hết hạn.', 'treasure_expired', 409)
        # A committed winner can replay even after its proof/chest expires.
        if chest['winner']:
            need(chest['winner'] == sid, 'Một người khác đã nhặt rương này.', 'treasure_taken', 409)
            return dict(state=public_state(migrate_state(store.parse_state(saved['state'], sid))),
                        revision=saved['revision'], result=json.loads(chest['result']), replayed=True)
        need(chest['bucket'] == int(at // PERIOD), 'Rương này đã hết hạn.', 'treasure_expired', 409)
        used = db.execute('SELECT id FROM town_treasure_chests WHERE winner=? AND request_id=?', (sid,request_id)).fetchone()
        need(not used, 'Mã yêu cầu đã dùng cho rương khác.', 'treasure_request', 409)
        position = db.execute('SELECT * FROM town_treasure_presence WHERE sid=? FOR UPDATE', (sid,)).fetchone()
        ticket = db.execute('SELECT * FROM town_treasure_proofs WHERE sid=? FOR UPDATE', (sid,)).fetchone()
        at = now()
        need(chest['bucket'] == int(at // PERIOD), 'Rương này đã hết hạn.', 'treasure_expired', 409)
        need(ticket and ticket['chest_id'] == chest_id and secrets.compare_digest(ticket['proof_hash'], store.digest(proof))
             and 0 <= at - ticket['created_at'] <= PROOF_TTL and position and ticket['lease'] == position['lease']
             and near(position, chest, at), 'Hãy đi sát rương trong phố rồi thử lại.', 'treasure_presence', 403)
        raw = store.parse_state(saved['state'], sid)
        before = dict(raw.get('careers', {}))
        with archive.collect() as box:
            raw = migrate_state(raw, owned=True)
            from . import jail
            need(not jail.jailed(raw), 'Bạn chưa thể nhặt kho báu lúc này.', 'jailed', 409)
            j = raw['journey']
            need(j.get('story'), 'Kho báu dành cho ví hành trình.', 'treasure_story', 409)
            need(j['wallet'] + REWARD <= 10**9, 'Ví đã đầy, hãy dùng bớt xu rồi nhặt rương.', 'wallet_full', 409)
            journey._wallet(j, REWARD, 'life', '🧰 Kho báu trong phố')
            serialized = serialize(raw, full=True)
            cut = _archive_rows(box, before, raw, '')
        result = dict(message='Bạn nhặt được 10.000 xu vào ví hành trình!',
                      treasure=dict(chest_id=chest_id, coins=REWARD, wave_id=str(chest['bucket'])))
        db.execute('UPDATE sessions SET state=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE sid=?', (serialized,sid))
        db.execute('UPDATE town_treasure_chests SET winner=?,won_at=?,request_id=?,result=? WHERE id=?',
                   (sid,at,request_id,json.dumps(result,ensure_ascii=False),chest_id))
        db.execute('DELETE FROM town_treasure_proofs WHERE sid=?', (sid,))
        _write_archive(db,sid,cut)
        leaderboard.write(db,sid,leaderboard.summary(raw))
        db.execute("SELECT pg_notify('mnl_live',?)", (json.dumps(dict(kind='town_treasure', bucket=chest['bucket'])),))
        return dict(state=public_state(raw,migrated=True), revision=saved['revision']+1, result=result, replayed=False)
    return store.transaction(write)
