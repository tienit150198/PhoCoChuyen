"""🧰 Xưởng phục chế Hồn Xưa: old and broken things brought back, one ticket at a time (owner 21/10, "làm hết đi").

A ticket is one piece (a grandfather's clock, a rattan chair, a mother's wedding áo dài…) with two or three damages
written as signs, one or two awkward customer demands (restore_content.DEMANDS: keep the scratch the child made, an
"heirloom" whose age the customer lies about, a missing part, haggling, grandma's piece wanted brand new…), the parts
it needs and the right finish. Eight server-graded stages: read the signs → settle the demands → parts → clean by
material → fix each damage → finish → final checks → hand back on the right ticket. A wrong choice stays at its stage
and costs quality; materials are advanced against the ticket and settled once at hand-back, so an empty wallet never
strands a piece. Everything is a pure function of (day, slot); answers stay server side (`_key`).

Players' own broken things (a broken vehicle, a worn part of their home, furniture made "cổ điển") are restored for
other players through 🛎️ Phố dịch vụ: game/restore_service.py.
"""
from __future__ import annotations
from copy import deepcopy
from . import kit
from . import restore_content as C

ID = 'restore'
PREFIX = 'phc_'
STAGES = ('inspect', 'talk', 'parts', 'clean', 'fix', 'finish', 'check', 'deliver', 'done')
LABELS = dict(inspect='Đọc dấu hiệu hư hỏng', talk='Chốt yêu cầu với khách', parts='Lo linh kiện', clean='Làm sạch theo chất liệu',
              fix='Phục hồi từng hư hỏng', finish='Hoàn thiện', check='Kiểm lần cuối', deliver='Trả đúng phiếu')
PEOPLE = C.PEOPLE
FIXED = ('needs', '_key', 'kind')
CHECK_IDS = tuple(k for k, _ in C.CHECKS)
MILESTONES = (4, 10, 20, 40)


def _rotate(rows: list, n: int) -> list:
    n %= max(1, len(rows))
    return rows[n:] + rows[:n]


def make_task(day, slot, serial):
    r = kit.rng(ID, day, slot)
    pool = [o for o in C.ITEMS if o[2] <= day]
    kind, title, _, material, damage_pool, finish, parts = pool[(day + slot - 1) % len(pool)]
    level = sum(day >= n for n in MILESTONES)
    k = min(len(damage_pool), 2 + (1 if level >= 2 and r.random() < .5 else 0))
    chosen = set(r.sample(list(damage_pool), k))
    damages = [d for d in damage_pool if d in chosen]
    signs = []
    for i, dmg in enumerate(damages):
        signs.append(dict(id=f's{i + 1}', text=f'Dấu hiệu {i + 1}: {C.DAMAGES[dmg][1]}.'))
    open_demands = [d for d in C.DEMAND_ORDER if C.DEMANDS[d][0] <= day and material in C.DEMANDS[d][4].get('only', (material,))]
    want = 2 if level >= 2 else 1
    demands = []
    for d in r.sample(open_demands, min(want, len(open_demands))):
        if C.DEMANDS[d][4].get('finish') and any(C.DEMANDS[x][4].get('finish') for x in demands):
            continue   # one finish wish a ticket: "keep the scratch" and "make it brand new" never meet
        demands.append(d)
    demands = [d for d in C.DEMAND_ORDER if d in demands]
    need_parts = sorted(r.sample(list(parts), min(len(parts), 1 + (1 if level >= 1 and len(parts) > 1 else 0))), key=parts.index)
    missing = need_parts[r.randrange(len(need_parts))] if 'missing' in demands else None
    tag = f'HX-{day:04d}-{slot:02d}'
    for d in demands:
        fx = C.DEMANDS[d][4]
        finish = fx.get('finish', finish)
    talk = []
    for i, d in enumerate(demands):
        _, words, options, _, _ = C.DEMANDS[d]
        talk.append(dict(id=d, text=words, options=[dict(id=a, label=b) for a, b in _rotate(list(options), day + slot + i)]))
    part_rows = [dict(id=f'p{i + 1}', name=p, missing=p == missing) for i, p in enumerate(need_parts)]
    key = dict(
        inspect={s['id']: dmg for s, dmg in zip(signs, damages)},
        talk={d: C.DEMANDS[d][3] for d in demands},
        parts={p['id']: ('make' if p['missing'] else 'stock') for p in part_rows},
        clean=C.MATERIALS[material][1],
        fix={dmg: C.FIXES[dmg] for dmg in damages},
        finish=finish,
    )
    cost = 2 + len(part_rows) + (1 if missing else 0)
    net = 14 + 3 * len(damages) + 2 * len(demands) + level
    who = (slot + day) % len(PEOPLE)
    needs = dict(item=title, material=material, material_name=C.MATERIALS[material][0], signs=signs, demands=talk,
                 parts=part_rows, tag=tag, tag_options=[tag, f'HX-{day:04d}-{slot + 1:02d}', f'HX-{day:04d}-{slot + 2:02d}'],
                 cost=cost, gross=cost + net, net=net, damages=len(damages),
                 note='Vật tư và linh kiện được xưởng ứng theo phiếu, trừ một lần khi trả đồ. Sai thì sửa ngay tại bước đó, công giảm theo chất lượng.')
    return kit.base_task(ID, day, slot, serial, who, title,
                         f'Nhờ xưởng phục chế {title.lower()}: {len(signs)} chỗ hư, giữ hồn món đồ và trả theo phiếu {tag}.',
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
    t['repairs'].append(dict(stage=stage, items=[str(x)[:100] for x in bad[:4]]))
    t['repairs'] = t['repairs'][-60:]
    t['mistakes'] += 1
    t['quality'] = max(40, 100 - 12 * t['mistakes'])
    t['last_issue'] = f'{LABELS[stage]} chưa đúng: {", ".join(bad[:4])}. {HELP[stage]}'
    return dict(message=t['last_issue'], correct=False)


HELP = dict(
    inspect='Đọc lại từng dấu hiệu, mở sổ nghề nếu cần.',
    talk='Nói thật, ghi phiếu, không làm giả và không giấu khách.',
    parts='Thiếu linh kiện thì chế lại cùng vật liệu và ghi phiếu; không tháo đồ người khác, không lắp thiếu.',
    clean='Mỗi chất liệu một cách làm sạch; nước áp lực, nhám mạnh và thuốc tẩy làm mất lớp gốc.',
    fix='Mỗi hư hỏng một cách phục hồi; đinh, keo 502, băng keo làm hỏng món đồ.',
    finish='Hoàn thiện theo món đồ, hoặc theo điều khách đã chốt ở quầy.',
    check='Kiểm đủ bốn mục trước khi gói đồ.',
    deliver='So tem trên món đồ với phiếu khách đưa.',
)


def _choices(p, ids, allowed, message):
    value = p.get('choices')
    kit.need(isinstance(value, dict) and set(value) == set(ids), message)
    for v in value.values():
        kit.one_of(v, allowed)
    return {k: value[k] for k in ids}


def handle(s, c, name, p):
    kit.need(name in {PREFIX + st for st in STAGES[:-1]}, 'Thao tác phục chế không hợp lệ.')
    t = kit.task(c, p)
    kit.need(t['known'], 'Nghe khách kể và nhận phiếu trước đã.')
    stage = name[len(PREFIX):]
    kit.need(t['stage'] == stage, 'Làm xong bước hiện tại trước nhé.')
    n, key = t['needs'], t['_key']
    if stage == 'inspect':
        value = _choices(p, [x['id'] for x in n['signs']], set(C.DAMAGES), 'Gọi tên hư hỏng cho đủ từng dấu hiệu.')
        bad = [f'dấu hiệu {i + 1}' for i, x in enumerate(n['signs']) if value[x['id']] != key['inspect'][x['id']]]
    elif stage == 'talk':
        value = p.get('choices')
        kit.need(isinstance(value, dict) and set(value) == set(key['talk']), 'Trả lời đủ từng yêu cầu của khách.')
        for d in n['demands']:
            kit.one_of(value[d['id']], {o['id'] for o in d['options']})
        value = {d: value[d] for d in key['talk']}
        bad = [f'yêu cầu {i + 1}' for i, d in enumerate(key['talk']) if value[d] != key['talk'][d]]
    elif stage == 'parts':
        value = _choices(p, [x['id'] for x in n['parts']], {k for k, _ in C.PART_OPTIONS}, 'Chọn cách lo cho đủ từng linh kiện.')
        bad = [x['name'] for x in n['parts'] if value[x['id']] != key['parts'][x['id']]]
    elif stage in ('clean', 'finish'):
        rows = C.CLEAN_OPTIONS if stage == 'clean' else C.FINISH_OPTIONS
        value = kit.one_of(p.get('choice'), {k for k, _ in rows}, 'Chọn một cách.')
        bad = [dict(rows)[value]] if value != key[stage] else []
    elif stage == 'fix':
        value = _choices(p, list(key['fix']), {k for k, _ in C.FIX_OPTIONS}, 'Chọn cách phục hồi cho đủ từng hư hỏng.')
        bad = [C.DAMAGES[d][0].lower() for d in key['fix'] if value[d] != key['fix'][d]]
    elif stage == 'check':
        value = kit.id_list(p.get('checks'), CHECK_IDS)
        kit.need(set(value) == set(CHECK_IDS), 'Kiểm đủ bốn mục trước khi gói đồ.')
        value, bad = list(CHECK_IDS), []
    else:   # deliver
        value = kit.one_of(p.get('tag'), n['tag_options'], 'Chọn một phiếu đang ở quầy.')
        bad = ['phiếu khách không khớp tem đồ'] if value != n['tag'] else []
    if bad:
        return _mistake(t, stage, bad)
    kit.start_work(t)
    t['work'][stage] = deepcopy(value)
    t['last_issue'] = ''
    t['stage'] = STAGES[STAGES.index(stage) + 1]
    if stage != 'deliver':
        return dict(message=f'{LABELS[stage]}: đúng rồi. Tiếp: {LABELS[t["stage"]]}.', correct=True)
    d = _data(c)
    net = max(5, n['net'] * t['quality'] // 100)
    t['paid'] = True
    on_start(s, c)
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(t['quality'] >= 90)
        bucket['earned'] += net
    kit.complete(s, c, t, net + n['cost'], f'Trả {n["item"].lower()} theo phiếu {n["tag"]}; chất lượng {t["quality"]}%.', bonus_base=net)
    kit.money(s, c, -n['cost'], 'Vật tư và linh kiện phục chế theo phiếu', t['id'], 'materials')
    return dict(message=f'Đã trả đồ đúng phiếu. Thu {net + n["cost"]} xu, vật tư {n["cost"]} xu, còn {net} xu công.',
                correct=t['quality'] >= 90, celebrate=t['quality'] >= 90)


def step_options(stage):
    rows = {'inspect': [(k, v[0]) for k, v in C.DAMAGES.items()], 'parts': C.PART_OPTIONS, 'clean': C.CLEAN_OPTIONS,
            'fix': C.FIX_OPTIONS, 'finish': C.FINISH_OPTIONS}.get(stage, [])
    return [dict(id=k, label=v) for k, v in rows]


def on_close(s, c):
    d = _data(c)
    today = d['today']
    if today['day'] == c['day'] and today['jobs'] > 0 and d['closed_day'] != c['day']:
        d['stats']['active_days'] += 1
        d['closed_day'] = c['day']
    return dict(lines=[f'Hồn Xưa trả {today["jobs"]} món, {today["good"]} món đạt từ 90%, công sau vật tư {today["earned"]} xu.'],
                jobs=today['jobs'], clean=today['good'], earned=today['earned'])


def known_request(c, t):
    extra = ' Khách còn dặn thêm vài điều oái oăm, chốt ở quầy trước nhé.' if t['needs']['demands'] else ''
    return t['opening'] + extra


def public_task(t):
    out = deepcopy({k: v for k, v in t.items() if not k.startswith('_')})
    if not t['known']:
        out['needs'] = None
    else:
        out['options'] = step_options(t['stage'])
        out['instruction'] = hint(None, t)
        if t['stage'] in ('fix', 'finish', 'check', 'deliver', 'done'):
            out['found'] = [dict(id=dmg, name=C.DAMAGES[dmg][0]) for dmg in t['work'].get('inspect', {}).values()]
    return out


def public_data(c):
    d = deepcopy(_data(c))
    d['mastered'] = d['stats']['good'] >= 100 and d['stats']['active_days'] >= 30
    d['expert'] = d['stats']['good'] >= 180 and d['stats']['active_days'] >= 45
    d['chapter'] = sum(c['day'] >= n for n in (1,) + MILESTONES)
    return d


RULES = C.RULES


def content():
    return dict(rules=RULES, stages=LABELS, checks=[dict(id=k, label=v) for k, v in C.CHECKS],
                people=[dict(name=a, role=b, note=c) for a, b, c in PEOPLE])


def hint(c, t):
    return {
        'inspect': 'Đọc từng dấu hiệu trên phiếu rồi gọi đúng tên hư hỏng.',
        'talk': 'Khách dặn mấy điều oái oăm: chọn cách trả lời thật thà, có ghi phiếu.',
        'parts': 'Linh kiện còn trong ngăn thì lấy; thiếu thì chế lại cùng vật liệu và ghi phiếu.',
        'clean': 'Chọn cách làm sạch hợp chất liệu của món đồ.',
        'fix': 'Chọn cách phục hồi cho từng hư hỏng vừa tìm ra.',
        'finish': 'Hoàn thiện theo món đồ, hoặc theo điều đã chốt với khách.',
        'check': 'Kiểm chắc chắn, ảnh trước sau, phiếu ghi đúng tuổi và dặn cách giữ gìn.',
        'deliver': 'So tem trên món đồ với phiếu khách đưa rồi bàn giao.',
    }.get(t['stage'], 'Phiếu đã hoàn tất.')


def feedback(c, t):
    score = max(1, min(5, (t['quality'] + 19) // 20))
    talked = any(s['stage'] == 'talk' for s in t['repairs'])
    return dict(criteria=[dict(key='craft', label='Giữ hồn món đồ', score=score, note=f'Chất lượng {t["quality"]}%'),
                          dict(key='talk', label='Chốt yêu cầu với khách', score=3 if talked else 5,
                               note='Yêu cầu oái oăm đã chốt thật thà, có ghi phiếu')])


def validate_task(t, original):
    kit.need(t.get('stage') in STAGES, 'Bước phục chế không hợp lệ.')
    for field in FIXED:
        kit.need(t.get(field) == original.get(field), 'Dữ kiện phiếu phục chế đã thay đổi.')
    at = STAGES.index(t['stage'])
    work = t.get('work')
    kit.need(isinstance(work, dict) and set(work) == set(STAGES[:at]), 'Tiến trình phục chế không khớp.')
    key = t['_key']
    for stage, value in work.items():
        expected = (list(CHECK_IDS) if stage == 'check' else t['needs']['tag'] if stage == 'deliver' else key[stage])
        kit.need(value == expected, 'Kết quả bước phục chế chưa khớp phiếu.')
    kit.integer(t.get('quality'), 40, 100)
    kit.need(t['quality'] == max(40, 100 - 12 * t['mistakes']), 'Điểm chất lượng phục chế không khớp.')
    kit.need(type(t.get('paid')) is bool and t['paid'] == (t['stage'] == 'done'), 'Thanh toán phục chế không khớp.')
    kit.need((t['stage'] == 'done') == (t['status'] == 'completed'), 'Phiếu phục chế chưa hoàn thành.')
    kit.need(at == 0 or t['known'], 'Chưa nhận phiếu phục chế.')
    kit.need(isinstance(t.get('repairs'), list) and len(t['repairs']) == min(60, t['mistakes']), 'Nhật ký sửa sai không khớp.')
    for slip in t['repairs']:
        kit.need(isinstance(slip, dict) and slip.get('stage') in LABELS and isinstance(slip.get('items'), list)
                 and 1 <= len(slip['items']) <= 4 and all(isinstance(x, str) and len(x) <= 100 for x in slip['items']), 'Nhật ký sửa sai lỗi.')
    kit.need(isinstance(t.get('last_issue'), str) and len(t['last_issue']) <= 600, 'Nhắc sửa sai lỗi.')


def validate_data(c):
    d = _data(c)
    kit.need(isinstance(d, dict) and set(d) == set(initial()), 'Sổ xưởng phục chế sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(initial()[field]), 'Thống kê phục chế sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số phiếu đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['jobs'], 'Ngày làm thực tế sai.')


SPEC = dict(id=ID, prefix=PREFIX, category='shop',
    meta=dict(short='Phục chế', place=C.PLACE, tagline='Giữ hồn đồ xưa, sửa cái hỏng, nói thật với khách.',
              icon='wrench', color='#8a5a2b', light='#f6ead9', weather='Mùi sáp ong và dầu gỗ',
              work='Phiếu phục chế', station='Bàn khám đồ và tủ linh kiện',
              greeting='Nghe khách kể, khám dấu hiệu, chốt yêu cầu oái oăm rồi mới đụng tay.',
              caption='Đồ cũ có hồn, thợ có tâm', map_label='XƯỞNG PHỤC CHẾ HỒN XƯA'),
    people=PEOPLE, staff=[('Lụa', 'care', 'Ghi phiếu, chụp ảnh trước và sau.', 80, 85)], roles={'care': 'Ghi phiếu'},
    tip=0, physical=tuple(PREFIX + st for st in STAGES[:-1]), free_actions=(), no_tick=(), waste_items=(),
    activity=('🧰', 'Sổ nghề phục chế', [('Gỗ', 'Lau dầu'), ('Kim loại', 'Chải mềm'), ('Vết kỷ niệm', 'Giữ lại'), ('Tuổi đồ', 'Ghi thật')],
              ['Đọc dấu hiệu', 'Chốt yêu cầu khách', 'Làm sạch và phục hồi', 'Hoàn thiện, kiểm và trả đồ']),
    stories=[('Chiếc đồng hồ không chạy', ('Chú Khải giữ một chiếc đồng hồ quả lắc chưa từng sửa.', 'Bạn tìm ra chiếc lò xo gãy giấu trong máy.', 'Đồng hồ điểm chuông, chú Khải kể chuyện người tặng.'))],
    review_asides=['Đồ về còn nguyên hồn, phiếu ghi rõ ràng.', 'Thợ nói thật tuổi món đồ, yên tâm ghê.'], situations=[],
    more_line='Khách ôm tới thêm một món đồ cũ.', open_line='Bàn khám đồ đã lau, tủ linh kiện đã mở. Nhận phiếu đầu tiên nhé.',
    guide='Hỏi → đọc dấu hiệu → chốt yêu cầu oái oăm → linh kiện → làm sạch → phục hồi → hoàn thiện → kiểm → trả đúng phiếu.')
