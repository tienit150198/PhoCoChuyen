"""Nếp Thơm: ticketed garment batches with label-aware processing and rework.

Materials are supplied against the ticket and settled from its receipt, so an
empty wallet cannot strand a load. No waiting timers or client-authoritative pay.
"""
from __future__ import annotations
from copy import deepcopy
from . import kit

ID = 'laundry'
STAGES = ('inspect', 'sort', 'treat', 'wash', 'dry', 'finish', 'check', 'deliver', 'done')
LABELS = dict(inspect='Kiểm đồ và nhãn', sort='Tách màu và chất liệu', treat='Xử lý vết bẩn',
              wash='Chọn chương trình giặt', dry='Làm khô', finish='Ủi và gấp', check='Kiểm chất lượng', deliver='Trả đúng phiếu')
PEOPLE = [('Chị Thơm', 'Chủ tiệm', 'Chỉ cách đọc nhãn và giữ đồ của khách.'),
          ('Anh Phúc', 'Nhân viên văn phòng', 'Áo cần thẳng nếp cho buổi thuyết trình.'),
          ('Cô Hòa', 'Thợ may', 'Mang lụa và đồ thêu tới, dặn giữ dáng.'),
          ('Bác Bình', 'Hàng xóm', 'Gửi áo khoác và rèm cửa của gia đình.'),
          ('Chị Lan', 'Quản lý nhà nghỉ', 'Gửi bộ khăn, ga có đánh số phòng.'),
          ('Minh', 'Sinh viên', 'Đồ thể thao và đồng phục câu lạc bộ.')]
# title, introduction day, material pool, handling request
ORDERS = (
    ('office', 'Áo sơ mi đi làm', 1, ('cotton',), 'hang'),
    ('school', 'Đồng phục đến lớp', 1, ('cotton', 'poly'), 'fold'),
    ('sport', 'Đồ câu lạc bộ', 1, ('poly',), 'fold'),
    ('silk', 'Khăn lụa của cô Hòa', 4, ('silk',), 'fold'),
    ('embroidered', 'Áo thêu đi lễ', 4, ('silk', 'cotton'), 'hang'),
    ('linen', 'Bộ lanh ngày nắng', 4, ('linen',), 'hang'),
    ('wool', 'Áo len đầu mùa', 10, ('wool',), 'fold'),
    ('raincoat', 'Áo khoác chống thấm', 10, ('shell',), 'hang'),
    ('mixedcoat', 'Túi áo khoác gia đình', 10, ('wool', 'shell'), 'fold'),
    ('curtains', 'Rèm cửa phòng khách', 20, ('linen', 'poly'), 'hang'),
    ('tablecloth', 'Khăn bàn quán nhỏ', 20, ('cotton', 'linen'), 'fold'),
    ('hotel', 'Mẻ khăn nhà nghỉ', 40, ('towel',), 'fold'),
    ('hotel_linen', 'Bộ ga theo số phòng', 40, ('cotton', 'linen'), 'fold'),
    ('heirloom', 'Bộ lụa và len lưu niệm', 40, ('silk', 'wool'), 'fold'),
)
MATERIALS = {
    'cotton': ('Cotton', 'normal40', 'low', 'medium'),
    'poly': ('Sợi tổng hợp', 'sport30', 'shade', 'lowiron'),
    'silk': ('Lụa', 'hand20', 'shade', 'cloth'),
    'linen': ('Vải lanh', 'linen40', 'line', 'steam'),
    'wool': ('Len', 'wool20', 'flat', 'nosteam'),
    'shell': ('Vải chống thấm', 'shell30', 'shade', 'noiron'),
    'towel': ('Bông khăn dày', 'hygiene60', 'mediumdry', 'noiron'),
}
OPTIONS = {
    'wash': [('normal40', 'Thường · 40°C'), ('sport30', 'Đồ thể thao · 30°C'), ('hand20', 'Giặt tay nhẹ · 20°C'),
             ('linen40', 'Vải lanh · 40°C'), ('wool20', 'Len · 20°C, không vắt'), ('shell30', 'Chống thấm · 30°C'),
             ('hygiene60', 'Khăn bông · 60°C'), ('boil', 'Giặt mạnh · 90°C')],
    'dry': [('low', 'Sấy nhẹ'), ('shade', 'Treo trong bóng râm'), ('line', 'Phơi dây'),
            ('flat', 'Trải phẳng trên khăn'), ('mediumdry', 'Sấy vừa'), ('hot', 'Sấy nóng')],
    'treat': [('soap', 'Xà phòng trung tính: dầu/mồ hôi'), ('cold', 'Nước lạnh: vết máu'),
              ('brush', 'Chải khô: bùn'), ('dab', 'Thấm nhẹ: trà/cà phê'), ('delicate', 'Dung dịch dịu cho lụa/len'),
              ('none', 'Không tẩy: không có vết'), ('bleach', 'Tẩy clo mạnh')],
    'finish': [('medium', 'Ủi vừa'), ('lowiron', 'Ủi nhiệt thấp'), ('cloth', 'Ủi thấp qua khăn lót'),
               ('steam', 'Ủi hơi khi còn hơi ẩm'), ('nosteam', 'Vuốt dáng, không ép nhiệt'), ('noiron', 'Không ủi')],
}
COLORS = (('white', 'trắng'), ('light', 'màu nhạt'), ('dark', 'màu đậm'))
STAINS = (('oil', 'dầu', 'soap'), ('sweat', 'mồ hôi', 'soap'), ('blood', 'máu', 'cold'),
          ('mud', 'bùn khô', 'brush'), ('tea', 'trà', 'dab'), ('none', 'không có vết', 'none'))
CHECKS = ('count', 'stains', 'dry', 'finish', 'tag')
FIXED = ('needs', '_key', 'kind')


def make_task(day, slot, serial):
    r = kit.rng(ID, day, slot)
    pool = [o for o in ORDERS if o[2] <= day]
    kind, title, _, mats, packing = pool[(day + slot - 1) % len(pool)]
    garments, key = [], {st: {} for st in ('sort', 'treat', 'wash', 'dry', 'finish')}
    qty = r.randint(2, 4)
    tag = f'NT-{day:04d}-{slot:02d}'
    for i in range(qty):
        mat = mats[(i + r.randrange(len(mats))) % len(mats)]
        name, wash, dry, iron = MATERIALS[mat]
        color, color_name = r.choice(COLORS)
        stain, stain_name, treatment = r.choice(STAINS)
        if mat in ('silk', 'wool') and stain != 'none':
            treatment = 'delicate'
        iid = f'g{i + 1}'
        sort = f'{color}_{mat}'
        finish = f'{iron}_{packing}'
        garments.append(dict(id=iid, name=f'Món {i + 1} · {name}', material=mat, color=color,
                             description=f'{name}, {color_name}; vết {stain_name}.', stain=stain,
                             label=f'{dict(OPTIONS["wash"])[wash]}; {dict(OPTIONS["dry"])[dry]}; {dict(OPTIONS["finish"])[iron]}.',
                             packing='Treo móc' if packing == 'hang' else 'Gấp theo phiếu', tag=f'{tag}/{i + 1}'))
        for st, val in [('sort', sort), ('treat', treatment), ('wash', wash), ('dry', dry), ('finish', finish)]:
            key[st][iid] = val
    level = sum(day >= n for n in (4, 10, 20, 40))
    cost = qty + 2 + (1 if level >= 2 else 0)
    net = 12 + qty * 2 + level
    needs = dict(garments=garments, tag=tag, tag_options=[tag, f'NT-{day:04d}-{slot + 1:02d}', f'NT-{day:04d}-{slot + 2:02d}'],
                 cost=cost, gross=cost + net, net=net, quantity=qty,
                 note='Vật tư và nước được tiệm ứng theo phiếu, trừ một lần khi trả đồ. Sai thao tác phải sửa, công giảm theo chất lượng.')
    return kit.base_task(ID, day, slot, serial, (slot + day) % len(PEOPLE), title,
                         f'Nhờ tiệm xử lý {qty} món, giữ đúng nhãn và trả theo phiếu {tag}.',
                         kind=kind, needs=needs, _key=key, stage='inspect', work={}, quality=100,
                         repairs=[], last_issue='', paid=False)


def initial():
    return dict(today=dict(day=0, jobs=0, good=0, earned=0), stats=dict(jobs=0, good=0, active_days=0, earned=0), closed_day=0)


def _data(c):
    return kit.data(c)


def on_start(s, c):
    d = _data(c)
    if d['today']['day'] != c['day']:
        d['today'] = dict(day=c['day'], jobs=0, good=0, earned=0)


def _mistake(t, stage, bad):
    t['repairs'].append(dict(stage=stage, items=bad))
    t['repairs'] = t['repairs'][-60:]
    t['mistakes'] += 1
    t['quality'] = max(40, 100 - 12 * t['mistakes'])
    t['last_issue'] = f'{LABELS[stage]} chưa khớp: {", ".join(bad)}. Đọc lại nhãn và bảng hướng dẫn, sửa ngay tại bước này.'
    return dict(message=t['last_issue'], correct=False)


def handle(s, c, name, p):
    kit.need(name in {'ld_' + st for st in STAGES[:-1]}, 'Thao tác giặt ủi không hợp lệ.')
    t = kit.task(c, p)
    kit.need(t['known'], 'Hỏi khách và đọc phiếu trước khi nhận đồ.')
    stage = name[3:]
    kit.need(t['stage'] == stage, 'Làm xong bước hiện tại trước nhé.')
    ids = [g['id'] for g in t['needs']['garments']]
    if stage == 'inspect':
        value = kit.id_list(p.get('items'), ids)
        kit.need(set(value) == set(ids), 'Kiểm nhãn, màu và vết bẩn của đủ các món.')
        value = list(ids)
    elif stage == 'check':
        value = kit.id_list(p.get('checks'), CHECKS)
        kit.need(set(value) == set(CHECKS), 'Kiểm đủ số món, vết bẩn, độ khô, nếp đồ và tem phiếu.')
        value = list(CHECKS)
    elif stage == 'deliver':
        value = kit.one_of(p.get('tag'), t['needs']['tag_options'], 'Chọn một phiếu đang ở quầy.')
        if value != t['needs']['tag']:
            return _mistake(t, stage, ['phiếu khách không khớp tem đồ'])
    else:
        value = p.get('choices')
        kit.need(isinstance(value, dict) and set(value) == set(ids), 'Chọn cách xử lý cho đủ từng món.')
        allowed = {v['id'] for v in step_options(stage)}
        for v in value.values():
            kit.one_of(v, allowed)
        bad = [g['name'] for g in t['needs']['garments'] if value[g['id']] != t['_key'][stage][g['id']]]
        if bad:
            return _mistake(t, stage, bad)
    kit.start_work(t)
    t['work'][stage] = deepcopy(value)
    t['last_issue'] = ''
    t['stage'] = STAGES[STAGES.index(stage) + 1]
    if stage != 'deliver':
        return dict(message=f'{LABELS[stage]} đã khớp phiếu. Tiếp: {LABELS[t["stage"]]}.', correct=True)
    n, d = t['needs'], _data(c)
    # The receipt pays materials plus earned labour. A repair affects labour only.
    net = max(5, n['net'] * t['quality'] // 100)
    t['paid'] = True
    on_start(s, c)
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(t['quality'] >= 90)
        bucket['earned'] += net
    kit.complete(s, c, t, net + n['cost'], f'Trả đủ {n["quantity"]} món theo phiếu {n["tag"]}; chất lượng {t["quality"]}%.', bonus_base=net)
    kit.money(s, c, -n['cost'], 'Nước, chất giặt và bao gói theo phiếu', t['id'], 'supplies')
    return dict(message=f'Đã trả đúng đồ. Thu {net + n["cost"]} xu, vật tư {n["cost"]} xu, còn {net} xu.', correct=t['quality'] >= 90, celebrate=t['quality'] >= 90)


def step_options(stage):
    if stage == 'sort':
        rows = [(f'{color}_{mat}', f'{name} · {m[0]}') for color, name in COLORS for mat, m in MATERIALS.items()]
    elif stage == 'finish':
        rows = [(f'{k}_{pack}', f'{label} · {name}') for k, label in OPTIONS['finish'] for pack, name in [('fold', 'gấp'), ('hang', 'treo móc')]]
    else:
        rows = OPTIONS.get(stage, [])
    return [dict(id=k, label=v) for k, v in rows]


def on_close(s, c):
    d = _data(c)
    today = d['today']
    if today['day'] == c['day'] and today['jobs'] > 0 and d['closed_day'] != c['day']:
        d['stats']['active_days'] += 1
        d['closed_day'] = c['day']
    return dict(lines=[f'Nếp Thơm trả {today["jobs"]} phiếu, {today["good"]} phiếu đạt từ 90%, công sau vật tư {today["earned"]} xu.'], jobs=today['jobs'], clean=today['good'], earned=today['earned'])


def known_request(c, t):
    return t['opening'] + ' Mỗi món có nhãn riêng; tách cả màu lẫn chất liệu.'


def public_task(t):
    out = deepcopy({k: v for k, v in t.items() if not k.startswith('_')})
    if not t['known']:
        out['needs'] = None
    else:
        out['options'] = step_options(t['stage'])
        out['instruction'] = hint(None, t)
    return out


def public_data(c):
    d = deepcopy(_data(c))
    d['mastered'] = d['stats']['good'] >= 100 and d['stats']['active_days'] >= 30
    d['expert'] = d['stats']['good'] >= 180 and d['stats']['active_days'] >= 45
    d['chapter'] = sum(c['day'] >= n for n in (1, 4, 10, 20, 40))
    return d


RULES = [
    'Mỗi giỏ chỉ chứa cùng nhóm màu và cùng chất liệu. Trắng, màu nhạt và màu đậm luôn tách nhau.',
    'Vết dầu hoặc mồ hôi dùng xà phòng trung tính; máu dùng nước lạnh; bùn khô chải khô; trà thấm nhẹ. Không có vết thì không tẩy.',
    'Mọi vết trên lụa hoặc len dùng dung dịch dịu riêng. Không dùng clo mạnh.',
    'Chương trình, nhiệt độ và cách làm khô phải đúng nhãn. Len trải phẳng; lụa và đồ chống thấm treo râm.',
    'Ủi theo nhãn rồi treo/gấp theo khách dặn; kiểm đủ món và tem phiếu trước khi trả.',
    'Chương 1 ngày 1: đồ thường; ngày 4: lụa và lanh; ngày 10: len và áo khoác; ngày 20: rèm, khăn bàn; ngày 40: mẻ nhà nghỉ và đồ lưu niệm.',
    'Thợ vững tay: 100 phiếu đạt từ 90% và 30 ngày có trả đồ. Nghệ nhân Nếp Thơm: 180 phiếu đạt từ 90% và 45 ngày có trả đồ. Ca rỗng không được tính.',
]


def content():
    return dict(rules=RULES, stages=LABELS, people=[dict(name=a, role=b, note=c) for a, b, c in PEOPLE])


def hint(c, t):
    return {
        'inspect': 'Đọc nhãn từng món, màu, vết bẩn và yêu cầu treo/gấp. Đánh dấu đủ các món rồi nhận phiếu.',
        'sort': 'Xếp mỗi món vào giỏ có đúng nhóm màu và chất liệu. Mở bảng hướng dẫn nếu cần.',
        'treat': 'Chọn chất xử lý theo vết bẩn; lụa/len có vết luôn dùng dung dịch dịu riêng.',
        'wash': 'Chọn cả chương trình và nhiệt độ khớp nhãn của từng món.',
        'dry': 'Chọn cách làm khô đúng nhãn: đừng sấy nóng đồ cần phơi râm hoặc trải phẳng.',
        'finish': 'Khớp cách ủi trên nhãn và yêu cầu treo/gấp ghi trên từng món.',
        'check': 'Đối chiếu số món, vết bẩn, độ khô, nếp đồ và tem phiếu trước khi đóng gói.',
        'deliver': 'So tem từng món với số phiếu khách xuất trình rồi bàn giao.',
    }.get(t['stage'], 'Phiếu đã hoàn tất.')


def feedback(c, t):
    score = max(1, min(5, (t['quality'] + 19) // 20))
    return dict(criteria=[dict(key='craft', label='Giữ chất liệu và nếp đồ', score=score, note=f'Chất lượng {t["quality"]}%'),
                          dict(key='tag', label='Đối chiếu phiếu', score=3 if any(s['stage'] == 'deliver' for s in t['repairs']) else 5,
                               note='Tem từng món đã đối chiếu khi giao')])


def validate_task(t, original):
    kit.need(t.get('stage') in STAGES, 'Bước giặt ủi không hợp lệ.')
    for field in FIXED:
        kit.need(t.get(field) == original.get(field), 'Dữ kiện phiếu giặt đã thay đổi.')
    at = STAGES.index(t['stage'])
    work = t.get('work')
    kit.need(isinstance(work, dict) and set(work) == set(STAGES[:at]), 'Tiến trình giặt ủi không khớp.')
    for stage, value in work.items():
        expected = ([g['id'] for g in t['needs']['garments']] if stage == 'inspect' else
                    list(CHECKS) if stage == 'check' else t['needs']['tag'] if stage == 'deliver' else t['_key'][stage])
        kit.need(value == expected, 'Kết quả bước giặt chưa khớp phiếu.')
    kit.integer(t.get('quality'), 40, 100)
    kit.need(t['quality'] == max(40, 100 - 12 * t['mistakes']), 'Điểm chất lượng giặt không khớp.')
    kit.need(type(t.get('paid')) is bool and t['paid'] == (t['stage'] == 'done'), 'Thanh toán giặt không khớp.')
    kit.need((t['stage'] == 'done') == (t['status'] == 'completed'), 'Phiếu giặt chưa hoàn thành.')
    kit.need(at == 0 or t['known'], 'Chưa nhận phiếu giặt.')
    kit.need(isinstance(t.get('repairs'), list) and len(t['repairs']) == min(60, t['mistakes']), 'Nhật ký sửa đồ không khớp.')
    for slip in t['repairs']:
        kit.need(isinstance(slip, dict) and slip.get('stage') in LABELS and isinstance(slip.get('items'), list)
                 and 1 <= len(slip['items']) <= 4 and all(isinstance(x, str) and len(x) <= 100 for x in slip['items']), 'Nhật ký sửa đồ sai.')
    kit.need(isinstance(t.get('last_issue'), str) and len(t['last_issue']) <= 600, 'Nhắc sửa đồ sai.')


def validate_data(c):
    d = _data(c)
    kit.need(isinstance(d, dict) and set(d) == set(initial()), 'Sổ tiệm giặt sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(initial()[field]), 'Thống kê giặt sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số phiếu đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['jobs'], 'Ngày làm thực tế sai.')


SPEC = dict(id=ID, prefix='ld_', category='shop',
    meta=dict(short='Giặt ủi', place='Tiệm giặt ủi Nếp Thơm', tagline='Đúng nhãn vải, sạch từng món, trả đúng người.',
              icon='shirt', color='#398b96', light='#e2f5f5', weather='Gió thơm qua giàn phơi', work='Phiếu giặt',
              station='Bàn kiểm đồ và máy giặt', greeting='Hỏi khách, kiểm nhãn rồi tách từng mẻ theo màu và vải.',
              caption='Nếp áo thẳng, lời hẹn tròn', map_label='TIỆM GIẶT NẾP THƠM'),
    people=PEOPLE, staff=[('Nhàn', 'care', 'Kiểm đồ và nhắc nhãn giặt.', 82, 86)], roles={'care': 'Kiểm đồ'},
    tip=0, physical=tuple('ld_' + st for st in STAGES[:-1]), free_actions=(), no_tick=(), waste_items=(),
    activity=('🧺', 'Bảng chăm vải', [('Len', 'Trải phẳng'), ('Lụa', 'Giặt nhẹ'), ('Màu đậm', 'Giỏ riêng'), ('Phiếu', 'Đúng khách')],
              ['Đọc nhãn', 'Tách màu và vải', 'Giặt và làm khô', 'Ủi, kiểm và trả đồ']),
    stories=[('Chiếc áo đầu tiên', ('Chị Thơm giữ chiếc móc gỗ từ ngày mở tiệm.', 'Bạn sửa lại tem giấy đã phai trên móc.', 'Một khách cũ nhận ra nét chữ năm xưa.'))],
    review_asides=['Đồ sạch, đúng nhãn, tem phiếu rõ ràng.', 'Nếp áo gọn, nhận đủ từng món.'], situations=[],
    more_line='Khách mang tới một túi đồ nữa.', open_line='Giàn phơi sạch, máy đã sẵn sàng. Nhận phiếu đầu tiên nhé.',
    guide='Hỏi → kiểm nhãn → tách màu/vải → xử lý vết → giặt → làm khô → ủi/gấp → kiểm → trả đúng phiếu.')
