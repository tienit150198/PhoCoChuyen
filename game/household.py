"""Opt-in personal household. Care advances on life days, never wall time.

One child and one cat/dog belong to this save. No recurring charges, death,
automatic adoption or shared-spouse mutation. Purchases use the existing bank
payment reducer and command receipts. The optional block is ignored by old builds.
"""
from __future__ import annotations

from . import bank, needs

KINDS = {'child': ('👶', 'Em bé', 0), 'cat': ('🐱', 'Mèo', 30), 'dog': ('🐶', 'Cún', 30)}
ACTS = {
    'milk': dict(name='Chuẩn bị sữa và bữa ăn', emoji='🍼', slot='food', cost=4, kinds=['child']),
    'feed': dict(name='Cho ăn', emoji='🥣', slot='food', cost=3, kinds=['cat', 'dog']),
    'wash': dict(name='Vệ sinh, thay đồ sạch', emoji='🫧', slot='clean', cost=0, kinds=list(KINDS)),
    'play': dict(name='Chơi cùng nhau', emoji='🧸', slot='joy', cost=0, kinds=list(KINDS)),
    'read': dict(name='Đọc truyện cho bé', emoji='📖', slot='joy', cost=0, kinds=['child']),
    'walk': dict(name='Dạo quanh sân', emoji='🐾', slot='joy', cost=0, kinds=['cat', 'dog']),
}
OUTFITS = {
    'basic': dict(name='Đồ ở nhà', color='#efc78d', cost=0),
    'yem': dict(name='Yếm cầu vồng', color='#83b9db', cost=18),
    'flower': dict(name='Bộ hoa nhỏ', color='#e5a0b1', cost=22),
}
FIELDS = {'kind', 'name', 'since', 'day', 'did', 'care_days', 'bond', 'food', 'clean', 'joy', 'outfit', 'owned'}


def _e():
    from . import engine
    return engine


def _name(value):
    _e().need(isinstance(value, str) and 1 <= len(value.strip()) <= 24 and
              not any(ord(c) < 32 or c in '<>' for c in value), 'Tên cần từ 1 đến 24 ký tự, không dùng ký tự đặc biệt.')
    return value.strip()


def _today(j, m):
    return list(m['did']) if m['day'] == j['life_day'] else []


def _meters(j, m):
    gap = max(0, j['life_day'] - m['day'])
    return {k: max(0, m[k] - min(gap, 10) * 12) for k in ('food', 'clean', 'joy')}


def public(s):
    j = s.get('journey') or {}
    if not j.get('story'):
        return None
    h = j.get('household') or {}
    members = []
    for key in ('child', 'pet'):
        m = h.get(key)
        if not m:
            continue
        days = m['care_days']
        stage = ('Em bé' if days < 5 else 'Bé tập đi' if days < 20 else 'Bé đi học') if key == 'child' else ('Đang làm quen' if days < 5 else 'Bạn thân trong nhà' if days < 20 else 'Gắn bó thân thiết')
        done = _today(j, m)
        members.append(dict(id=key, kind=m['kind'], name=m['name'], emoji=KINDS[m['kind']][0], stage=stage,
                            care_days=days, next=5 if days < 5 else 20 if days < 20 else None,
                            bond=m['bond'], needs=_meters(j, m), outfit=m['outfit'], owned=list(m['owned']),
                            acts=[dict(id=k, **x, done=x['slot'] in done) for k, x in ACTS.items() if m['kind'] in x['kinds']]))
    return dict(members=members, locked=j.get('life_day', 1) < 10, day=j.get('life_day', 1),
                adopt=[dict(id=k, emoji=v[0], name=v[1], cost=v[2]) for k, v in KINDS.items()],
                outfits=[dict(id=k, **v) for k, v in OUTFITS.items()])


def action(s, name, p):
    e = _e()
    j = s.get('journey')
    e.need(j and j.get('story'), 'Chăm sóc gia đình chỉ có trong hành trình.', 'locked')
    e.need(j['life_day'] >= 10, 'Mở góc gia đình từ ngày sống 10.', 'locked')
    allowed = {
        'jr_hh_adopt': {'kind', 'name', 'confirm', 'pay'},
        'jr_hh_care': {'member', 'act', 'pay'},
        'jr_hh_rename': {'member', 'name'},
        'jr_hh_style': {'member', 'item', 'confirm', 'pay'},
    }
    e.need(name in allowed and isinstance(p, dict) and set(p) <= allowed[name], 'Thao tác gia đình không hợp lệ.')
    e.need(isinstance(p.get('pay', 'auto'), str) and p.get('pay', 'auto') in bank.PREFS, 'Cách thanh toán không hợp lệ.')
    h = j.get('household')
    if name == 'jr_hh_adopt':
        kind = p.get('kind')
        e.need(isinstance(kind, str) and kind in KINDS, 'Chọn em bé, mèo hoặc cún.')
        key = 'child' if kind == 'child' else 'pet'
        e.need(not h or not h.get(key), 'Nhà đã có thành viên này rồi.', 'already_owned')
        who = _name(p.get('name'))
        e.need(p.get('confirm') is True, 'Xác nhận đón thành viên mới về nhà.')
        cost = KINDS[kind][2]
        payment = bank.pay(s, cost, 'Đồ dùng đón thú cưng', method=p.get('pay', 'auto'), kind='life') if cost else None
        if h is None:
            h = j['household'] = dict(v=1, child=None, pet=None)
        h[key] = dict(kind=kind, name=who, since=j['life_day'], day=j['life_day'], did=[], care_days=0,
                      bond=0, food=65, clean=65, joy=65, outfit='basic', owned=['basic'])
        return dict(message=f'{KINDS[kind][0]} {who} đã về nhà. Ghé góc gia đình để chăm sóc nhé.' + (f' {payment["text"]}' if payment else ''))
    key = p.get('member')
    e.need(isinstance(key, str) and key in ('child', 'pet') and h and h.get(key), 'Chưa có thành viên này.')
    m = h[key]
    if name == 'jr_hh_rename':
        m['name'] = _name(p.get('name'))
        return dict(message=f'Đã đổi tên thành {m["name"]}.')
    if name == 'jr_hh_style':
        item = p.get('item')
        e.need(key == 'child' and isinstance(item, str) and item in OUTFITS, 'Chọn bộ đồ cho bé.')
        if item not in m['owned']:
            e.need(p.get('confirm') is True, 'Xác nhận mua bộ đồ cho bé.')
            bank.pay(s, OUTFITS[item]['cost'], OUTFITS[item]['name'], method=p.get('pay', 'auto'), kind='life')
            m['owned'].append(item)
        m['outfit'] = item
        return dict(message=f'{m["name"]} đã thay {OUTFITS[item]["name"].lower()}.')
    aid = p.get('act')
    e.need(isinstance(aid, str) and aid in ACTS and m['kind'] in ACTS[aid]['kinds'], 'Chọn một việc chăm sóc phù hợp.')
    x = ACTS[aid]
    did = _today(j, m)
    e.need(x['slot'] not in did, 'Hôm nay đã chăm sóc phần này rồi. Mai ghé lại nhé.', 'already_done')
    payment = bank.pay(s, x['cost'], x['name'], method=p.get('pay', 'auto'), kind='life') if x['cost'] else None
    m.update(_meters(j, m))
    if not did:
        m['care_days'] = min(10**6, m['care_days'] + 1)
        needs._spirit(s, 1)
    m['day'] = j['life_day']
    m['did'] = did + [x['slot']]
    m[x['slot']] = min(100, m[x['slot']] + 35)
    m['bond'] = min(100, m['bond'] + 2)
    line = {'food': 'ăn ngon lành, trông vui hẳn lên', 'clean': 'sạch sẽ thơm tho rồi', 'joy': 'thích lắm, cứ muốn chơi cùng bạn thêm'}[x['slot']]
    return dict(message=f'{x["emoji"]} {m["name"]} {line}.' + (f' {payment["text"]}' if payment else ''))


def validate(s):
    j = s.get('journey') or {}
    if 'household' not in j:
        return
    e = _e()
    h = j['household']
    bad = 'Dữ liệu gia đình không hợp lệ.'
    e.need(isinstance(h, dict) and set(h) == {'v', 'child', 'pet'} and type(h['v']) is int and h['v'] == 1, bad, 'invalid_save')
    for key in ('child', 'pet'):
        m = h[key]
        if m is None:
            continue
        e.need(isinstance(m, dict) and set(m) == FIELDS, bad, 'invalid_save')
        e.need(isinstance(m['kind'], str) and m['kind'] in (('child',) if key == 'child' else ('cat', 'dog')), bad)
        _name(m['name'])
        e.integer(m['since'], 10, j['life_day'])
        e.integer(m['day'], m['since'], j['life_day'])
        e.integer(m['care_days'], 0, min(10**6, m['day'] - m['since'] + 1))
        for k in ('bond', 'food', 'clean', 'joy'):
            e.integer(m[k], 0, 100)
        e.need(isinstance(m['did'], list) and all(isinstance(x, str) for x in m['did']) and
               len(m['did']) == len(set(m['did'])) and set(m['did']) <= {'food', 'clean', 'joy'}, bad)
        e.need(isinstance(m['owned'], list) and all(isinstance(x, str) for x in m['owned']) and
               len(m['owned']) == len(set(m['owned'])) and 'basic' in m['owned'] and set(m['owned']) <= set(OUTFITS), bad)
        e.need(isinstance(m['outfit'], str) and m['outfit'] in m['owned'], bad)
