"""Optional courier contracts tied to successful delivery career commands.

Career delivery fees and COD keep their existing accounting. This branch pays
only a quoted contract bonus, once, after new matching deliveries. Nothing runs
offline. No client-supplied progress or reward amounts are accepted.
"""
from . import bank

CONTRACTS = {
    'local': dict(name='Tuyến hàng xóm', emoji='📦', target=3, fee=24, cost=3, level=1, category='all'),
    'food': dict(name='Bữa nóng đến nhà', emoji='🍲', target=3, fee=30, cost=4, level=1, category='food'),
    'express': dict(name='Chuyến giao đúng hẹn', emoji='⚡', target=5, fee=48, cost=6, level=2, category='all'),
    'chain': dict(name='Đối tác chuỗi cửa hàng', emoji='🏪', target=8, fee=84, cost=10, level=3, category='all'),
}
GEAR = {
    'bag': dict(name='Túi giao hàng chuyên dụng', emoji='🎒', cost=35, desc='Giảm 1 xu khấu trừ thưởng cho mỗi đơn có phàn nàn.'),
    'cover': dict(name='Gói hỗ trợ sự cố hợp đồng', emoji='🛡️', cost=60, desc='Giảm một nửa khấu trừ thưởng còn lại. Không hoàn tiền phạt giao thông.'),
}


def _e():
    from . import engine
    return engine


def _done(s):
    return int(s['careers'].get('delivery', {}).get('metrics', {}).get('deliveries_done', 0))


def _level(h):
    return 1 + int(h.get('completed', 0) >= 3) + int(h.get('completed', 0) >= 10)


def _deduction(h, a):
    amount = a['bad'] * (3 if 'bag' in h['gear'] else 4)
    return (amount + 1) // 2 if 'cover' in h['gear'] else amount


def public(s):
    j = s.get('journey') or {}
    if not j.get('story'):
        return None
    h = j.get('courier') or dict(completed=0, delivered=0, earned=0, gear=[], active=None, history=[])
    level = _level(h)
    active = None
    if h['active']:
        a = h['active']; x = CONTRACTS[a['kind']]
        deduction = min(x['fee'], _deduction(h, a))
        active = dict(a, **{k: v for k, v in x.items() if k != 'kind'}, deduction=deduction,
                      bonus=x['fee'] - deduction, ready=a['done'] >= x['target'])
    return dict(level=level, completed=h['completed'], delivered=h['delivered'], earned=h['earned'], active=active,
                unlocked='delivery' in j.get('unlocked', []),
                contracts=[dict(id=k, **v, locked=level < v['level']) for k, v in CONTRACTS.items()],
                gear=[dict(id=k, **v, owned=k in h['gear']) for k, v in GEAR.items()], history=list(reversed(h['history'])))


def action(s, name, p):
    e = _e(); j = s.get('journey')
    e.need(j and j.get('story') and 'delivery' in j['unlocked'], 'Mở nghề Giao hàng trước nhé.', 'locked')
    allowed = {'jr_ship_accept': {'kind', 'confirm', 'pay'}, 'jr_ship_collect': set(),
               'jr_ship_cancel': {'confirm'}, 'jr_ship_gear': {'item', 'confirm', 'pay'}}
    e.need(name in allowed and isinstance(p, dict) and set(p) <= allowed[name], 'Thao tác hợp đồng không hợp lệ.')
    pay = p.get('pay', 'auto')
    e.need(isinstance(pay, str) and pay in ('auto', 'cash', 'account', 'card', 'joint'), 'Chọn nguồn thanh toán hợp lệ.')
    h = j.get('courier')
    if name == 'jr_ship_accept':
        kind = p.get('kind')
        e.need(isinstance(kind, str) and kind in CONTRACTS, 'Chọn hợp đồng giao hàng.')
        x = CONTRACTS[kind]
        e.need(not h or h['active'] is None, 'Hoàn tất hoặc hủy hợp đồng đang nhận trước nhé.')
        e.need(_level(h or {}) >= x['level'], 'Hoàn tất thêm hợp đồng để mở tuyến này.', 'locked')
        e.need(p.get('confirm') is True, 'Xác nhận nhận hợp đồng và chi phí chuẩn bị.')
        receipt = bank.pay(s, x['cost'], 'Chuẩn bị ' + x['name'], method=pay, kind='life')
        if h is None:
            h = j['courier'] = dict(v=1, seq=0, completed=0, delivered=0, earned=0, gear=[], active=None, history=[])
        h['seq'] += 1
        h['active'] = dict(kind=kind, seq=h['seq'], day=j['life_day'], done=0, bad=0, last=_done(s))
        return dict(message=f'Đã nhận {x["name"]}. Giao {x["target"]} đơn mới phù hợp trong nghề Giao hàng. {receipt["text"]}')
    e.need(h is not None, 'Nhận hợp đồng đầu tiên trước nhé.')
    if name == 'jr_ship_gear':
        key = p.get('item')
        e.need(isinstance(key, str) and key in GEAR and key not in h['gear'], 'Món này không hợp lệ hoặc đã có.')
        e.need(p.get('confirm') is True, 'Xác nhận mua đồ nghề.')
        receipt = bank.pay(s, GEAR[key]['cost'], GEAR[key]['name'], method=pay, kind='life')
        h['gear'].append(key)
        return dict(message=f'Đã có {GEAR[key]["name"]}. {receipt["text"]}')
    a = h['active']
    e.need(a is not None, 'Chưa có hợp đồng đang làm.', 'already_done')
    if name == 'jr_ship_cancel':
        e.need(p.get('confirm') is True, 'Xác nhận hủy hợp đồng. Chi phí chuẩn bị không hoàn lại.')
        h['active'] = None
        return dict(message='Đã hủy hợp đồng, không bị phạt thêm. Chi phí chuẩn bị đã dùng không hoàn lại.')
    x = CONTRACTS[a['kind']]
    e.need(a['done'] >= x['target'], 'Chưa giao đủ đơn mới theo hợp đồng.')
    deduction = min(x['fee'], _deduction(h, a)); amount = x['fee'] - deduction
    from . import journey
    if amount:
        journey._wallet(j, amount, 'salary', 'Thưởng hợp đồng · ' + x['name'], 'delivery')
    h['completed'] += 1; h['earned'] += amount
    h['history'] = (h['history'] + [dict(seq=a['seq'], kind=a['kind'], day=j['life_day'], fee=x['fee'],
                                      deduction=deduction, bonus=amount, cost=x['cost'])])[-12:]
    h['active'] = None
    return dict(message=f'Hoàn tất {x["name"]}: thưởng {x["fee"]} − khấu trừ {deduction} = {amount} xu vào ví. Phí giao từng đơn vẫn tính riêng trong nghề.')


def on_action(s, career, action_name, p, result):
    if career != 'delivery' or action_name not in ('dl_deliver', 'dl_safedrop'):
        return
    h = (s.get('journey') or {}).get('courier')
    if not h or not h['active']:
        return
    a = h['active']; current = _done(s)
    if current <= a['last']:
        return
    a['last'] = current
    c = s['careers']['delivery']
    t = next((t for t in c['tasks'] if t['id'] == p.get('task')), None)
    if not t or t.get('status') != 'completed' or t.get('run', {}).get('outcome') not in ('delivered', 'safedrop'):
        return
    x = CONTRACTS[a['kind']]
    if a['done'] >= x['target'] or (x['category'] != 'all' and t['needs']['kind'] != x['category']):
        return
    a['done'] += 1; h['delivered'] += 1
    if t['run'].get('late') or t.get('mistakes'):
        a['bad'] += 1
    result.setdefault('effects', []).append(f'📦 {x["name"]}: {a["done"]}/{x["target"]} đơn.' + (' Đủ đơn rồi, mở Sổ shipper nhận thưởng nhé.' if a['done'] == x['target'] else ''))


def validate(s):
    j = s.get('journey') or {}; h = j.get('courier')
    if h is None:
        return
    e = _e(); bad = 'Sổ hợp đồng giao hàng không hợp lệ.'
    e.need(isinstance(h, dict) and set(h) == {'v','seq','completed','delivered','earned','gear','active','history'} and type(h['v']) is int and h['v'] == 1, bad)
    for k in ('seq','completed','delivered','earned'):
        e.integer(h[k], 0, 10**9)
    e.need(h['completed'] <= h['seq'], bad)
    e.need(h['completed'] * min(x['target'] for x in CONTRACTS.values()) <= h['delivered'] <= h['seq'] * max(x['target'] for x in CONTRACTS.values()), bad)
    e.need(h['earned'] <= h['completed'] * max(x['fee'] for x in CONTRACTS.values()), bad)
    e.need(isinstance(h['gear'], list) and all(isinstance(x,str) and x in GEAR for x in h['gear']) and len(set(h['gear'])) == len(h['gear']), bad)
    a = h['active']
    if a is not None:
        e.need(isinstance(a,dict) and set(a) == {'kind','seq','day','done','bad','last'} and isinstance(a['kind'],str) and a['kind'] in CONTRACTS, bad)
        e.integer(a['seq'], h['seq'], h['seq']); e.integer(a['day'], 1, j['life_day'])
        e.integer(a['done'], 0, min(h['delivered'],CONTRACTS[a['kind']]['target'])); e.integer(a['bad'], 0, a['done']); e.integer(a['last'], 0, _done(s))
        e.need(h['completed'] < h['seq'],bad)
    e.need(isinstance(h['history'],list) and len(h['history']) == min(h['completed'],12), bad)
    previous=0
    for r in h['history']:
        e.need(isinstance(r,dict) and set(r) == {'seq','kind','day','fee','deduction','bonus','cost'} and isinstance(r['kind'],str) and r['kind'] in CONTRACTS, bad)
        e.integer(r['seq'],previous+1,h['seq']-int(a is not None)); e.integer(r['day'],1,j['life_day'])
        previous=r['seq']
        for k in ('fee','deduction','bonus','cost'):
            e.integer(r[k],0,1000)
        e.need(r['bonus'] == r['fee'] - r['deduction'], bad)
        e.need(r['fee']==CONTRACTS[r['kind']]['fee'] and r['cost']==CONTRACTS[r['kind']]['cost'],bad)
    e.need(sum(r['bonus'] for r in h['history'])<=h['earned'],bad)
