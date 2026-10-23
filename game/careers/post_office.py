"""Cánh Thư: evidence-based postal work; all tariffs are fictional game rules."""
from __future__ import annotations

from copy import deepcopy
import json
from . import kit
from . import post_office_content as pc
from .. import consequences as cq

ID = 'post_office'
GEN = 1
PEOPLE = pc.PEOPLE
FIXED = ('gen', 'needs', '_key')
PHYSICAL = ('post_step',)
FREE = ('post_intro',)
NO_TICK = FREE


def _step(pid, kind, title, evidence, options=None):
    row = dict(id=f'{pid}.{kind}', parcel=pid, kind=kind, title=title, evidence=evidence)
    if options is not None:
        row['options'] = [dict(id=k, label=v) for k, v in options]
    return row


def make_task(day: int, slot: int, serial: int) -> dict:
    r = kit.rng(ID, day, slot)
    pool = [s for s in pc.SCENARIOS if s[1] <= day]
    newest = max(s[1] for s in pool)
    latest = [s for s in pool if s[1] == newest]
    row = latest[(day + slot) % len(latest)] if slot % 4 == 1 else pool[(day * 3 + slot) % len(pool)]
    vid, _, kind, item, title, opening, deadline, receipt, pack = row
    count = 3 if kind == 'batch' else 1
    parcels, steps, key = [], [], {}
    postage = 0
    for i in range(count):
        pid = f'p{i + 1}'
        zone, zone_label, base, route = pc.ZONES[(day + slot + i) % 3]
        mode = 'return' if vid.startswith('return') else 'collection' if kind == 'collection' else 'send'
        mode_label = {'return': 'hàng hoàn', 'collection': 'nhận tại quầy', 'send': 'gửi đi'}[mode]
        identity = 'hold' if vid == 'mismatch' else 'match'
        address = 'return_label' if mode == 'return' else 'repair' if vid == 'toy' or (day + slot + i) % 5 == 0 else 'keep'
        weight = r.choice((150, 250, 450, 500, 510, 750, 980, 1000, 1010, 1250, 1500, 1750, 2100, 2500, 3200))
        length = r.choice((65, 75, 90)) if vid == 'map' else r.choice((20, 35, 45, 60))
        thispack, due, signed = pack, deadline, receipt
        if vid == 'festival_batch':
            thispack, due, signed = [('cushion', 4, False), ('flat', 4, True), ('box', 1, False)][i]
        service = 'stored' if mode == 'collection' else 'return' if mode == 'return' else 'express' if due == 1 else 'registered' if signed else 'standard'
        fee = 0 if mode != 'send' else base + 3 * ((weight + 499) // 500) + dict((x[0], x[2]) for x in pc.SERVICES)[service] + (5 if length > 60 else 0)
        postage += fee
        recipient = ['Cô Hạnh', 'Mai', 'Anh Lộc'][(day + slot + i) % 3]
        sender = ['Chú Bình', 'Anh Lộc', 'Mai'][(day + i) % 3]
        expected = recipient if mode == 'collection' else sender
        presented = 'Anh Nam' if identity == 'hold' else expected
        town = f'{12 + i * 17 + day % 11} đường Hoa Giấy, {zone_label}'
        return_address = f'{8 + i * 9} đường Bến Mây, {zone_label}'
        parcel = dict(id=pid, code=f'CT{day:03d}{slot:02d}{i + 1}', item=item, mode=mode,
                      sender=sender, recipient=recipient, expected_person=expected, document_person=presented,
                      address='Thiếu số nhà' if address == 'repair' else town, confirmed_address=town,
                      sender_address=return_address, zone=zone, zone_label=zone_label, weight_g=weight,
                      declared_g=max(100, weight - r.choice((0, 50, 100))), length_cm=length,
                      deadline=due, signed=signed, packing_note=dict(pc.PACKS)[thispack])
        parcels.append(parcel)
        choices = [
            ('identity', 'Đối chiếu danh tính', f'Phiếu: {expected}. Giấy xuất trình: {presented}. Mã kiện: {parcel["code"]}.',
             [('match', 'Khớp tên và mã kiện'), ('hold', 'Giữ xác minh: tên không khớp'), ('trust', 'Tin lời nói, bỏ đối chiếu')], identity),
            ('address', 'Kiểm địa chỉ và nhãn', f'Nhãn: {parcel["address"]}. Phiếu xác minh: {town}. Người gửi: {return_address}. Loại việc: {mode_label}.',
             [('keep', 'Giữ nhãn đúng theo phiếu'), ('repair', 'Bổ sung số nhà theo phiếu đã xác minh'), ('return_label', 'Đổi nhãn hoàn về người gửi')], address),
            ('weight', 'Đọc cân thực tế', f'Cân đã trừ bì: {weight} g. Khách ước tính: {parcel["declared_g"]} g. Ghi số cân thực tế.', None, weight),
            ('pack', 'Kiểm bao gói an toàn', f'{item}. Yêu cầu bao gói: {parcel["packing_note"]}. Cạnh dài nhất: {length} cm.', pc.PACKS, thispack),
            ('service', 'Chọn dịch vụ phù hợp', f'Loại việc: {mode_label}. Hạn: {due} ngày. {"Cần chữ ký người nhận." if signed else "Không yêu cầu ký riêng."} Chọn mức rẻ nhất đáp ứng phiếu.',
             [(k, v) for k, v, _ in pc.SERVICES], service),
            ('tariff', 'Tính cước theo bảng game', f'{zone_label} · {weight} g · cạnh {length} cm. Loại việc: {mode_label}. Dùng bảng cước, làm tròn lên từng khối 500 g.', None, fee),
            ('route', 'Chia tuyến đúng mã kiện', f'{parcel["code"]} · {zone_label}. {"Chờ xác minh danh tính." if identity == "hold" else "Nhận tại quầy." if mode == "collection" else "Chuyển tuyến theo địa chỉ trên nhãn đã kiểm."}',
             [('A', 'Tuyến A · nội phố'), ('B', 'Tuyến B · vùng gần'), ('C', 'Tuyến C · vùng xa'), ('counter', 'Quầy trả hàng'), ('hold', 'Kệ giữ xác minh')],
             'hold' if identity == 'hold' else 'counter' if mode == 'collection' else route),
            ('proof', 'Lưu bằng chứng bàn giao', f'Mã {parcel["code"]}. {"Chưa xác minh được người nhận." if identity == "hold" else "Hoàn về người gửi." if mode == "return" else "Khách nhận ngay tại quầy." if mode == "collection" else "Nhân viên tuyến đã đối chiếu và ký bảng kê."}',
             [('manifest', 'Lưu bảng kê có chữ ký nhân viên tuyến'), ('signature', 'Lưu chữ ký đúng người nhận'), ('return_receipt', 'Lưu phiếu hoàn và lý do'), ('hold_notice', 'Lưu phiếu hẹn bổ sung giấy'), ('discard', 'Không cần lưu giấy')],
             'hold_notice' if identity == 'hold' else 'return_receipt' if mode == 'return' else 'signature' if mode == 'collection' else 'manifest'),
        ]
        for stage, label, evidence, options, answer in choices:
            step = _step(pid, stage, label, evidence, options)
            if options:
                r.shuffle(step['options'])
            steps.append(step); key[step['id']] = answer
    bonus = 9 if count == 3 else 6 if kind in ('fragile', 'collection', 'return') else 5
    return kit.base_task(ID, day, slot, serial, (day + slot) % len(PEOPLE), title, opening,
                         gen=GEN, kind=kind, needs=dict(variant=vid, parcels=parcels, steps=steps, bonus=bonus, postage=postage),
                         _key=key, at=0, work={}, errors=[], lines=[], stage='work')


def _today(day):
    return dict(day=day, jobs=0, qualified=0, postage=0, bonus=0, counted=0)


def initial():
    return dict(intro=False, today=_today(0), stats=dict(jobs=0, qualified=0, active_days=0, advanced=0, postage=0, bonus=0), last_active_day=0)


def _data(c):
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def handle(s, c, name, p):
    kit.need(name in ('post_intro', 'post_step'), 'Thao tác bưu điện không hợp lệ.')
    if name == 'post_intro':
        kit.data(c)['intro'] = True
        return dict(message='Bảng cước treo cạnh cân. Mình nhận từng kiện nhé.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc phiếu gửi trước khi thao tác.')
    kit.need(t['at'] < len(t['needs']['steps']), 'Bưu gửi này đã khép hồ sơ.')
    step = t['needs']['steps'][t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == step['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    value = p.get('value')
    if 'options' in step:
        kit.one_of(value, [o['id'] for o in step['options']])
    else:
        kit.integer(value, 0, 10000)
    kit.start_work(t)
    if value != t['_key'][step['id']]:
        if step['id'] not in t['errors']:
            t['errors'].append(step['id']); t['mistakes'] += 1
            cq.slip(t, step['id'], 1, 'Cần sửa: ' + step['title'])
        message = f'Chưa đúng. {step["evidence"]} Đối chiếu bảng quy tắc rồi thử lại.'
        t['lines'] = (t['lines'] + [message])[-24:]
        return dict(message=message, correct=False)
    t['work'][step['id']] = value
    t['at'] += 1
    t['lines'] = (t['lines'] + [f'✓ {step["parcel"]}: {step["title"]}.'])[-24:]
    if t['at'] < len(t['needs']['steps']):
        return dict(message='Đã ghi đúng. ' + t['needs']['steps'][t['at']]['title'], correct=True)
    d = _data(c)
    qualified = t['mistakes'] == 0
    bonus = max(4, t['needs']['bonus'] - t['mistakes'])
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1; bucket['qualified'] += int(qualified)
        bucket['postage'] += t['needs']['postage']; bucket['bonus'] += bonus
    if qualified and t['kind'] == 'batch':
        d['stats']['advanced'] += 1
    t['stage'] = 'done'
    kit.complete(s, c, t, bonus, 'Đã đối chiếu từng kiện và lưu đúng chứng từ bàn giao.')
    return dict(message=f'Đã khép phiếu. Cước {t["needs"]["postage"]} xu vào sổ bưu điện; thưởng hiệu suất {bonus} xu.', correct=qualified)


def on_start(s, c):
    _data(c)


def on_close(s, c):
    d = _data(c); today = d['today']
    if today['qualified'] and not today['counted'] and d['last_active_day'] < c['day']:
        d['stats']['active_days'] += 1; today['counted'] = 1; d['last_active_day'] = c['day']
    return dict(lines=[f'Cánh Thư: {today["jobs"]} phiếu xong, {today["qualified"]} phiếu không sai sót.',
                       f'Cước của bưu điện: {today["postage"]} xu. Thưởng hiệu suất: {today["bonus"]} xu.'],
                note='Lương ca do hợp đồng chi trả. Ngày có phiếu đạt chất lượng mới ghi vào hành trình nghề.')


def known_request(c, t):
    return t['opening'] + ' Đối chiếu phiếu → cân và bao gói → dịch vụ và cước → tuyến và chứng từ.'


def hint(c, t):
    if not t.get('known'):
        return 'Đọc phiếu để biết tên, địa chỉ, thời hạn và nội dung bưu gửi.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Phiếu đã hoàn tất; chọn khách tiếp theo.'


def feedback(c, t):
    groups = [('identity', 'Danh tính và địa chỉ', {'identity', 'address'}), ('care', 'Cân và bảo vệ kiện', {'weight', 'pack'}),
              ('fee', 'Dịch vụ và cước', {'service', 'tariff'}), ('proof', 'Tuyến và bàn giao', {'route', 'proof'})]
    return dict(criteria=[dict(key=k, label=label, score=max(1, 5 - sum(1 for e in t['errors'] if e.split('.')[1] in stages)),
                               note='Đối chiếu theo phiếu và bảng quy tắc trong game.') for k, label, stages in groups])


def public_task(t):
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    else:
        v['needs'].pop('postage', None)
    return v


def public_data(c):
    d = deepcopy(kit.data(c)); stats = d['stats']
    milestones = [dict(m, achieved=stats['qualified'] >= m['jobs'] and stats['active_days'] >= m['days'] and stats['advanced'] >= m['advanced']) for m in pc.MILESTONES]
    d['progress'] = dict(earned=[m['id'] for m in milestones if m['achieved']], milestones=milestones)
    return d


def content():
    return dict(notebook=pc.NOTEBOOK, zones=[dict(id=k, label=l, base=b, route=r) for k, l, b, r in pc.ZONES],
                services=[dict(id=k, label=l, extra=n) for k, l, n in pc.SERVICES],
                intro=dict(title='Một ngày ở Bưu điện Cánh Thư', lead='Mỗi bưu gửi là một lời hẹn. Cân đúng, tính đúng, trao đúng người. Cước thuộc bưu điện; bạn nhận lương ca và thưởng chất lượng nhỏ.',
                           work=[['🔎', 'So phiếu, tên và địa chỉ'], ['⚖️', 'Cân, bao gói và tính cước'], ['✉️', 'Chia tuyến, lưu chứng từ']],
                           meet=[['🙂', 'Cô Thư kèm ở quầy'], ['🚲', 'Anh Vũ nhận túi thư']],
                           stars=[['✓', 'Đọc số cân, không chép ước tính'], ['✓', 'Trao đúng người, lưu đúng phiếu']]))


def validate_task(t, original):
    for k in FIXED:
        kit.need(json.dumps(t.get(k), sort_keys=True) == json.dumps(original.get(k), sort_keys=True), 'Dữ kiện bưu gửi bị thay đổi: ' + k)
    steps = t['needs']['steps']; ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), 'Tiến trình bưu gửi sai.')
    kit.need(isinstance(t.get('work'), dict) and set(t['work']) == set(ids[:at]), 'Các bước đã ghi không liên tục.')
    kit.need(all(t['work'][sid] == t['_key'][sid] and type(t['work'][sid]) is type(t['_key'][sid]) for sid in ids[:at]), 'Kết quả bưu gửi sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) for e in errors), 'Nhật ký lỗi bưu gửi sai.')
    kit.need(len(errors) == len(set(errors)) and set(errors) <= set(ids[:min(at + 1, len(ids))]), 'Nhật ký lỗi bưu gửi sai.')
    kit.need(t.get('mistakes') >= len(errors), 'Số lỗi bưu gửi sai.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= 24 and all(isinstance(x, str) and len(x) < 500 for x in t['lines']), 'Nhật ký bưu gửi sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') == 'completed'), 'Chưa đủ chứng từ để hoàn thành bưu gửi.')


def validate_data(c):
    d = kit.data(c); base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ bưu điện sai.')
    kit.need(type(d['intro']) is bool, 'Giới thiệu bưu điện sai.')
    kit.integer(d['last_active_day'], 0, 10**7)
    for name in ('today', 'stats'):
        kit.need(isinstance(d[name], dict) and set(d[name]) == set(base[name]), 'Số liệu bưu điện sai.')
        for v in d[name].values(): kit.integer(v, 0, 10**9)
        kit.need(d[name]['qualified'] <= d[name]['jobs'], 'Số phiếu đạt chuẩn sai.')
    kit.integer(d['today']['counted'], 0, 1)
    kit.need(d['stats']['active_days'] <= d['stats']['qualified'] and d['stats']['advanced'] <= d['stats']['qualified'], 'Tiến trình nghề bưu điện sai.')


SPEC = dict(
    id=ID, prefix='post_', category='service', people=PEOPLE,
    meta=dict(short='Bưu điện', place='Bưu điện Cánh Thư', tagline='Gửi đúng lời hẹn, trao đúng người.', icon='mail', color='#b85b38', light='#fff0df',
              weather='Nắng nhẹ trên những túi thư', work='Bưu gửi', station='Quầy nhận & chia tuyến', greeting='Phiếu gửi bên trái, cân bên phải. Kiểm từng mã trước khi bàn giao nhé.',
              caption='Từ một lá thư đến cả chuyến hàng', map_label='BƯU ĐIỆN CÁNH THƯ'),
    staff=[('Anh Vũ', 'route', 'Thuộc từng tuyến, luôn đối chiếu bảng kê.', 82, 90),
           ('Cô Thư', 'counter', 'Kiểm phiếu kỹ và kiên nhẫn với khách.', 80, 92),
           ('Anh Toàn', 'parcel', 'Cân, dán tem, xếp bưu kiện theo vùng.', 84, 86),
           ('Chị Mai', 'counter', 'Nhận thư, giải thích cước chậm rãi cho người lớn tuổi.', 76, 93)],
    roles={'route': 'Chia tuyến', 'counter': 'Quầy nhận', 'parcel': 'Khai thác bưu kiện'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('✉️', 'Bảng cước trong game', [('Cân', 'Đọc khối lượng thực tế'), ('Cước', 'Vùng + khối 500 g + dịch vụ'), ('Tuyến', 'A, B, C'), ('Bàn giao', 'Lưu chứng từ')],
              ['Đối chiếu phiếu', 'Cân và bao gói', 'Tính cước', 'Chia tuyến và bàn giao']),
    stories=[('Lá thư trở về', ('Một lá thư thiếu số nhà nằm trên quầy.', 'Bạn đối chiếu phiếu bổ sung, ghi lại địa chỉ đủ.', 'Cô Thư nhận được lời cảm ơn từ người viết thư.'))],
    review_asides=['Mã kiện rõ ràng, cước tính đúng.', 'Bàn giao có giấy nhận, rất yên tâm.', 'Được giải thích từng khoản cước.'], situations=[],
    more_line='Túi thư mới vừa đến quầy.', open_line='Cô Thư đã mở quầy; bảng cước đặt ngay bên cân.',
    guide='Đọc phiếu, so tên và địa chỉ, đọc cân, chọn bao gói, dịch vụ, gõ cước, chia tuyến và lưu chứng từ. Tất cả quy tắc và mức cước chỉ dùng trong game.',
    employment=dict(postings=[dict(id='post-canhthu', org='Bưu điện Cánh Thư', kind='company', title='Nhân viên quầy bưu gửi', salary=(50, 65), probation_days=3,
                                  wants=['careful', 'numbers', 'communication'], perks=['Cô Thư hướng dẫn', 'Thưởng chất lượng nhỏ', 'Lương ca theo hợp đồng'],
                                  culture='Mỗi kiện có mã riêng, mỗi lần bàn giao có người ký.', questions=['mistake', 'conflict'], reference=False)], questions={}),
)
