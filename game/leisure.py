"""Free, private pixel leisure games. Only server-issued rounds can add keepsakes/laps.

There are no payments or money rewards. Public community-pool play is separate from
game.relax's existing villa ownership/needs rules. Old saves acquire this optional
journey field only when playing. Ordered checkpoint receipts and final round receipts
make retries harmless; private round state is never sent through live presence.
"""
from __future__ import annotations

import copy
import math
import re
import secrets
import time

KINDS = ('fishing', 'boat', 'pool')
FISH = ({'id': 'ca_ro', 'name': 'Cá rô', 'color': '#91ad73'},
        {'id': 'ca_chep', 'name': 'Cá chép', 'color': '#d89d5f'},
        {'id': 'ca_tram', 'name': 'Cá trắm', 'color': '#758d96'})
FISH_IDS = {f['id'] for f in FISH}
ENTRY = {'boat': [104, 150], 'pool': [86, 142]}
ROUTES = {'boat': [[144, 62], [260, 70], [252, 142], [104, 150]],
          'pool': [[86, 64], [250, 64], [250, 140], [86, 142]]}
MIN_SECONDS = {'fishing': 3, 'boat': 6, 'pool': 7}
MAX_SPEED = 110.0
TTL = 600
MAX_RECEIPTS = 12
LIMIT = 10**6
TOKEN = re.compile(r'[0-9a-f]{32}')


def _core():
    from . import engine
    return engine


def _fresh():
    return dict(v=1, fish={k: 0 for k in sorted(FISH_IDS)}, boat_laps=0, swim_laps=0, active=None, receipts=[])


def public(s):
    d = s['journey'].get('leisure') or _fresh()
    return dict(fish=dict(d['fish']), boat_laps=d['boat_laps'], swim_laps=d['swim_laps'])


def content():
    return dict(kinds=list(KINDS), fish=copy.deepcopy(list(FISH)), routes=copy.deepcopy(ROUTES), min_seconds=dict(MIN_SECONDS))


def _round_view(r):
    out = dict(id=r['id'], kind=r['kind'], now=time.time(), min_seconds=MIN_SECONDS[r['kind']], expires=r['expires'])
    if r['kind'] == 'fishing':
        out.update(bite_at=r['bite_at'], bite_window=1.6)
    else:
        out.update(entry=list(ENTRY[r['kind']]), checkpoints=copy.deepcopy(ROUTES[r['kind']]), next=r['next'])
    return out


def action(s, name, payload):
    e = _core()
    need = e.need
    need(isinstance(payload, dict), 'Dữ liệu hoạt động không hợp lệ.')
    now = time.time()
    if name == 'jr_leisure_start':
        kind = payload.get('kind')
        need(set(payload) == {'kind'} and isinstance(kind, str) and kind in KINDS, 'Chọn câu cá, chèo thuyền hoặc hồ bơi.')
        d = s['journey'].setdefault('leisure', _fresh())
        r = dict(id=secrets.token_hex(16), kind=kind, at=now, expires=now + TTL, next=0, last=now,
                 point=list(ENTRY.get(kind, [84, 154])), bite_at=0.0, fish=None)
        if kind == 'fishing':
            r.update(bite_at=now + 3 + secrets.randbelow(1500)/1000, fish=secrets.choice(sorted(FISH_IDS)))
        d['active'] = r
        return dict(message='', leisure_round=_round_view(r), leisure=public(s))
    need(name in ('jr_leisure_checkpoint', 'jr_leisure_finish'), 'Hoạt động không hợp lệ.', 'unknown_action')
    expected = {'round', 'index', 'x', 'y'} if name.endswith('checkpoint') else {'round'}
    token = payload.get('round')
    need(set(payload) == expected and isinstance(token, str) and bool(TOKEN.fullmatch(token)), 'Vòng chơi không hợp lệ.', 'bad_round')
    d = s['journey'].get('leisure')
    need(isinstance(d, dict), 'Hãy bắt đầu một vòng chơi trước.', 'bad_round')
    if name.endswith('finish') and any(x['id'] == token for x in d['receipts']):
        return dict(message='Vòng này đã được lưu.', duplicate=True, leisure=public(s))
    r = d['active']
    need(isinstance(r, dict) and r['id'] == token, 'Vòng chơi đã đóng hoặc thuộc lần chơi khác.', 'bad_round')
    need(r['at'] <= now <= r['expires'], 'Vòng chơi đã hết giờ. Hãy bắt đầu lại.', 'expired')
    kind = r['kind']
    if name.endswith('checkpoint'):
        index, x, y = payload.get('index'), payload.get('x'), payload.get('y')
        route = ROUTES.get(kind, [])
        need(type(index) is int and 0 <= index < len(route), 'Mốc đường không hợp lệ.')
        need(all(type(v) in (int, float) and math.isfinite(v) for v in (x, y)), 'Vị trí không hợp lệ.')
        target = route[index]
        need(math.hypot(x-target[0], y-target[1]) <= 10, 'Hãy đi đến vòng mốc đang sáng.', 'not_here')
        if index < r['next']:
            return dict(message='', duplicate=True, next=r['next'])
        need(index == r['next'], 'Đi qua từng mốc theo thứ tự nhé.', 'order')
        distance = math.hypot(x-r['point'][0], y-r['point'][1])
        need(now-r['last'] + .08 >= distance/MAX_SPEED, 'Bước đi quá nhanh. Đi tiếp rồi thử lại.', 'too_fast')
        r.update(next=index+1, last=now, point=[round(x, 2), round(y, 2)])
        return dict(message='', next=r['next'])
    need(now-r['at'] >= MIN_SECONDS[kind], 'Vòng chơi chưa hoàn thành.', 'too_early')
    if kind == 'fishing':
        need(r['bite_at'] <= now <= r['bite_at'] + 1.95, 'Cá đã nhả mồi. Thả cần lần nữa nhé!', 'missed')
        fish = r['fish']
        d['fish'][fish] = min(LIMIT, d['fish'][fish]+1)
        label = next(x['name'] for x in FISH if x['id'] == fish)
        message = f'Bạn bắt được {label}! Đã lưu vào sổ cá của bạn.'
    else:
        need(r['next'] == len(ROUTES[kind]), 'Đi qua đủ mốc rồi quay về bến nhé.', 'unfinished')
        key = 'boat_laps' if kind == 'boat' else 'swim_laps'
        d[key] = min(LIMIT, d[key]+1)
        message = 'Đã lưu một vòng chèo thuyền.' if kind == 'boat' else 'Đã lưu một vòng bơi.'
    d['receipts'] = (d['receipts'] + [dict(id=token, kind=kind)])[-MAX_RECEIPTS:]
    d['active'] = None
    return dict(message=message, leisure=public(s), celebrate=True)


def validate(s):
    if 'leisure' not in s.get('journey', {}):
        return
    e = _core()
    need, integer = e.need, e.integer
    d = s['journey']['leisure']
    bad = 'Dữ liệu đi chơi không hợp lệ.'
    need(isinstance(d, dict) and set(d) == {'v', 'fish', 'boat_laps', 'swim_laps', 'active', 'receipts'} and type(d['v']) is int and d['v'] == 1, bad, 'invalid_save')
    need(isinstance(d['fish'], dict) and set(d['fish']) == FISH_IDS, bad)
    for value in list(d['fish'].values()) + [d['boat_laps'], d['swim_laps']]:
        integer(value, 0, LIMIT)
    need(isinstance(d['receipts'], list) and len(d['receipts']) <= MAX_RECEIPTS, bad)
    ids = set()
    for receipt in d['receipts']:
        need(isinstance(receipt, dict) and set(receipt) == {'id', 'kind'} and receipt['kind'] in KINDS, bad)
        need(isinstance(receipt['id'], str) and bool(TOKEN.fullmatch(receipt['id'])) and receipt['id'] not in ids, bad)
        ids.add(receipt['id'])
    r = d['active']
    if r is None:
        return
    need(isinstance(r, dict) and set(r) == {'id', 'kind', 'at', 'expires', 'next', 'last', 'point', 'bite_at', 'fish'}, bad)
    need(isinstance(r['id'], str) and bool(TOKEN.fullmatch(r['id'])) and r['id'] not in ids and r['kind'] in KINDS, bad)
    need(all(type(r[k]) in (int, float) and math.isfinite(r[k]) and r[k] >= 0 for k in ('at', 'expires', 'last', 'bite_at')), bad)
    need(r['expires'] == r['at']+TTL and r['at'] <= r['last'] <= r['expires'], bad)
    integer(r['next'], 0, len(ROUTES.get(r['kind'], [])))
    need(isinstance(r['point'], list) and len(r['point']) == 2 and all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 320 for v in r['point']), bad)
    need((r['kind'] == 'fishing' and isinstance(r['fish'], str) and r['fish'] in FISH_IDS and r['at']+3 <= r['bite_at'] < r['at']+4.5) or
         (r['kind'] != 'fishing' and r['fish'] is None and r['bite_at'] == 0), bad)
