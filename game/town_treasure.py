"""One global treasure wave per real UTC ten-minute bucket.

Only the live service writes short-lived position proofs. HTTP resolves the login
again, locks its save and the chest, and pays the fixed reward in that same
transaction. No browser coordinates or reward amount enter this operation.

Anti-farming (11/10 audit: bots collected every chest of every wave plus the
overnight backlog): a chest lives KEEP_WAVES waves, then it is gone; an account
picks at most WAVE_MAX chest per wave window and DAY_MAX in any 24 hours,
counted from the claimed rows (kept a day for replays, so no new table or save
key); and the account must be ACCOUNT_AGE old. Claims lock the session row
first, so two tabs of one account cannot pass a cap together.
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
KEEP_WAVES = 3          # a chest is claimable in its wave and the next two (20-30 minutes), then it expires
WAVE_MAX = 1            # chests one account picks in one wave window (PERIOD)
DAY_MAX = 5             # chests one account picks in any 24 hours (claimed rows are kept that long)
ACCOUNT_AGE = 86400     # the account is at least a day old (as game/bank_xfer.py ACCOUNT_DAYS)
DAY = 86400
MAP_ID = 'iso-town-v1'
START = (6.0, 6.0)
REQUEST = re.compile(r'[A-Za-z0-9._:-]{8,80}')
CHEST = re.compile(r'tt-[0-9]{1,12}-[0-4]')
INSERT_WAVE = 'INSERT INTO town_treasure_waves(bucket) VALUES(?) ON CONFLICT(bucket) DO NOTHING RETURNING bucket'
INSERT_CHEST = 'INSERT INTO town_treasure_chests(id,bucket,map_id,x,y) VALUES(?,?,?,?,?)'
# Unclaimed chests of the last KEEP_WAVES waves (parameters: chest_args()), one
# marker per exact authored location. The oldest id stays claimable until
# collected or expired; the next receipt then takes over.
SELECT_CHESTS = '''SELECT oldest.id,oldest.bucket,g.map_id,g.x,g.y,oldest.winner,g.count
 FROM (SELECT map_id,x,y,COUNT(*) AS count FROM town_treasure_chests
       WHERE winner IS NULL AND bucket>=? GROUP BY map_id,x,y) g
 CROSS JOIN LATERAL (SELECT id,bucket,winner FROM town_treasure_chests WHERE winner IS NULL AND bucket>=?
       AND map_id=g.map_id AND x=g.x AND y=g.y ORDER BY bucket,id LIMIT 1) oldest
 ORDER BY g.map_id,g.x,g.y'''
# One account's claims in the last 24 hours, and how many since the current wave window began.
SELECT_MINE = ('SELECT COUNT(*) AS day, COALESCE(SUM(CASE WHEN won_at>=? THEN 1 ELSE 0 END),0) AS wave '
               'FROM town_treasure_chests WHERE winner=? AND won_at>=?')
SELECT_WAVE_COUNT = 'SELECT COUNT(*) AS added FROM town_treasure_chests WHERE bucket=?'


class TreasureError(ValueError):
    def __init__(self, message, code='treasure_bad', status=400):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status


def need(ok, message, code='treasure_bad', status=400):
    if not ok:
        raise TreasureError(message, code, status)


def now():
    return time.time()


def first_bucket(at):
    """The oldest wave whose chests are still on the map at `at`."""
    return int(at // PERIOD) - KEEP_WAVES + 1


def chest_args(at):
    return (first_bucket(at),) * 2


def account_old_enough(created_at, at):
    """accounts.created_at is UTC text 'YYYY-MM-DD HH:MM:SS' (pg_schema.NOW_TEXT)."""
    cut = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(at - ACCOUNT_AGE))
    return bool(created_at) and str(created_at) <= cut


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


def view(rows, at, on=True, added=0):
    bucket = int(at // PERIOD)
    chests = [dict(id=r['id'], map_id=r['map_id'], x=r['x'], y=r['y'], claimed=False, count=int(r['count']),
                   gone_at=(int(r['bucket']) + KEEP_WAVES) * PERIOD) for r in rows]
    return dict(enabled=on, server_time=at,
                wave=dict(id=str(bucket), starts_at=bucket * PERIOD, expires_at=(bucket + 1) * PERIOD,
                          next_at=(bucket + 1) * PERIOD, added=added, per_wave=WAVE_MAX, per_day=DAY_MAX,
                          reward=REWARD, notice=f'{added} rương kho báu vừa xuất hiện trong phố! Mỗi rương có 10.000 xu, '
                                                f'mỗi người nhặt {WAVE_MAX} rương mỗi đợt, tối đa {DAY_MAX} rương một ngày.') if on else None,
                chests=chests, total_unclaimed=sum(c['count'] for c in chests))


def cleanup_sql(bucket, at):
    # Unclaimed chests expire after KEEP_WAVES waves (no overnight backlog). A
    # claimed chest keeps a full day of replay protection and per-day cap
    # accounting, measured from collection, not spawning.
    return [('DELETE FROM town_treasure_chests WHERE winner IS NULL AND bucket<?', (bucket - KEEP_WAVES + 1,)),
            ('DELETE FROM town_treasure_chests WHERE winner IS NOT NULL AND won_at<?', (at - AUDIT_BUCKETS * PERIOD,)),
            ('DELETE FROM town_treasure_waves w WHERE bucket<? AND NOT EXISTS '
             '(SELECT 1 FROM town_treasure_chests c WHERE c.bucket=w.bucket)', (bucket - AUDIT_BUCKETS,)),
            ('DELETE FROM town_treasure_proofs WHERE created_at<?', (at - PROOF_TTL,)),
            ('DELETE FROM town_treasure_presence WHERE seen_at<?', (at - 86400,))]


def ensure_wave(db, at):
    bucket = int(at // PERIOD)
    if db.execute(INSERT_WAVE, (bucket,)).fetchone():
        db.executemany(INSERT_CHEST, spawn_rows(bucket))
        for sql, args in cleanup_sql(bucket, at):
            db.execute(sql, args)
    return db.execute(SELECT_CHESTS, chest_args(at)).fetchall()


def snapshot(store):
    at = now()
    if not enabled():
        return view([], at, False)
    def read(db):
        rows = ensure_wave(db, at)
        added = db.execute(SELECT_WAVE_COUNT, (int(at // PERIOD),)).fetchone()['added']
        return view(rows, at, added=added)
    return store.transaction(read)


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
        account = db.execute('SELECT created_at FROM accounts WHERE sid=?', (sid,)).fetchone() if csrf else None
        need(account, 'Đăng nhập tài khoản để nhặt kho báu.', 'treasure_account', 403)
        saved = db.execute('SELECT state,revision FROM sessions WHERE sid=? FOR UPDATE', (sid,)).fetchone()
        need(saved, 'Phiên chơi không tồn tại.', 'session_missing', 401)
        chest = db.execute('SELECT * FROM town_treasure_chests WHERE id=? FOR UPDATE', (chest_id,)).fetchone()
        at = now()  # Lock waits must not extend a position proof's lifetime.
        need(chest, 'Rương này không còn trên bản đồ.', 'treasure_missing', 409)
        # A committed winner can replay after its proof expires.
        if chest['winner']:
            need(chest['winner'] == sid, 'Một người khác đã nhặt rương này.', 'treasure_taken', 409)
            return dict(state=public_state(migrate_state(store.parse_state(saved['state'], sid))),
                        revision=saved['revision'], result=json.loads(chest['result']), replayed=True)
        used = db.execute('SELECT id FROM town_treasure_chests WHERE winner=? AND request_id=?', (sid,request_id)).fetchone()
        need(not used, 'Mã yêu cầu đã dùng cho rương khác.', 'treasure_request', 409)
        need(int(chest['bucket']) >= first_bucket(at), 'Rương này đã biến mất rồi. Chờ đợt rương mới nhé!', 'treasure_missing', 409)
        need(account_old_enough(account['created_at'], at),
             'Tài khoản cần đủ 1 ngày tuổi mới nhặt được kho báu.', 'treasure_new', 403)
        # The session row is locked above, so one account's claims are serialized and the caps hold.
        mine = db.execute(SELECT_MINE, (int(at // PERIOD) * PERIOD, sid, at - DAY)).fetchone()
        need(int(mine['wave']) < WAVE_MAX, 'Bạn đã nhặt rương của đợt này rồi. Đợt sau nhặt tiếp nhé!', 'treasure_wave', 409)
        need(int(mine['day']) < DAY_MAX, f'Hôm nay bạn đã nhặt đủ {DAY_MAX} rương rồi. Mai quay lại nhé!', 'treasure_day', 409)
        position = db.execute('SELECT * FROM town_treasure_presence WHERE sid=? FOR UPDATE', (sid,)).fetchone()
        ticket = db.execute('SELECT * FROM town_treasure_proofs WHERE sid=? FOR UPDATE', (sid,)).fetchone()
        at = now()
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
        leaderboard.write(db,sid,leaderboard.summary(raw,leaderboard.fair_refund.of(store,sid)))
        db.execute("SELECT pg_notify('mnl_live',?)", (json.dumps(dict(kind='town_treasure', bucket=chest['bucket'])),))
        return dict(state=public_state(raw,migrated=True), revision=saved['revision']+1, result=result, replayed=False)
    return store.transaction(write)
