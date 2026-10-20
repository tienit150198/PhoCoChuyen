"""🏍️ Tiệm sửa xe Út Lanh: a motorbike repair shop in the hẻm, one bike at a time (owner 21/10 "làm thêm nghề khác").

A ticket is one customer's bike (a model, a colour, a plate) with one fault (moto_content.FAULTS: a puncture, oil past
its change, a worn spark plug, a slack chain, worn brake pads, a dead headlight, a weak battery, a bike that drank flood
water) and one or two awkward customer demands. It is a list of server-graded steps (game/careers/stepkit.py), worked
one at a time: hear the complaint and name the fault → settle the demands → the fault's own hands-on steps (the order of
a procedure, a pressure, a volume, a voltage, a wear reading) → [the hand-over checks] → give back the right bike by its
plate. A wrong answer stays open to redo and costs quality; parts are advanced against the ticket and settled once at
hand-back (net labour = the ticket's labour × quality), so an empty till never strands a bike. Between tickets the
counter has its surprises (kit.desk, moto_content.DESK), some of which come back days later (marks).

Players' own motorbikes are serviced for other players through 🛎️ Phố dịch vụ (game/moto_service.py): the order is
worked here as a three-step job (xm_svc) whose finish is recorded in this career's data (`svc_ok`), which the market's
deliver hook reads from the provider's save before it pays.
"""
from __future__ import annotations

from copy import deepcopy
from . import kit
from . import moto_content as C
from . import stepkit as sk

ID = 'moto'
CERT_ID = 'moto_basics'   # certificate_content.GROUPS (hire=False): its perk is 1 xu off the parts of each bike
PREFIX = 'xm_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('xm_step', 'xm_svc')
FREE = ('xm_intro',)
NO_TICK = ('xm_intro', 'xm_desk')
LINES = 24
SERVICES = ('bao_duong',)


# ---------------------------------------------------------------- building a ticket (pure: day, slot)
def _num(v: float) -> str:
    return f'{v:.1f}'.replace('.', ',')


def _km(v: int) -> str:
    """12345 → '12.345' (Vietnamese thousands)."""
    return f'{v:,}'.replace(',', '.')


def _plate(r) -> str:
    return f'{r.choice(C.PROVINCES)}-{r.choice("ABCDEFGHKLMNPSTUVXZ")}{r.randint(1, 9)} {r.randint(100, 999)}.{r.randint(10, 99)}'


def _pressure(r, job: str, who: str) -> tuple:
    front, back = r.choice(((29, 33), (30, 33), (29, 36), (32, 36)))
    loaded = r.random() < 0.5
    use = 'hay chở thêm vợ đi làm' if loaded else 'chỉ đi một mình'
    st = sk.step(job, 'ap', 'number', 'Bơm đúng áp suất bánh sau',
                 f'Tem dán trên càng xe: bánh trước {front} psi, bánh sau {back} psi; chở thêm người hoặc hàng thì cộng 3 psi bánh sau. '
                 f'{who} {use}. Bơm bánh sau bao nhiêu psi?', unit='psi')
    return st, back + (3 if loaded else 0)


def _oil_change(r, job: str) -> tuple:
    return sk.ordered(r, job, 'thay', 'Thay nhớt đúng thứ tự', 'Bấm lần lượt các việc theo đúng sổ tay của tiệm.', C.STEPS['nhot'])


def _fault_steps(r, fault: str, kind: str, level: int, who: str) -> list:
    """[(step, answer)] of the fault's own hands-on work."""
    out = []
    if fault == 'thung_sam':
        out.append(sk.ordered(r, 'sam', 'va', 'Vá săm đúng thứ tự', 'Bấm lần lượt từng việc vá săm, từ tháo bánh tới lắp lại.', C.STEPS['va']))
        out.append(_pressure(r, 'sam', who))
    elif fault == 'thay_nhot':
        last = r.randrange(8000, 30000, 10)
        odo = last + r.randrange(1500, 4200, 10)
        out.append((sk.step('nhot', 'km', 'number', 'Tính số km đã chạy',
                            f'Tem thay nhớt dán ở yếm xe: thay lúc {_km(last)} km. Đồng hồ công-tơ-mét giờ chỉ {_km(odo)} km. '
                            'Từ lần thay trước xe đã chạy bao nhiêu km?', unit='km'), odo - last))
        other = C.OIL_KIND['so' if kind == 'ga' else 'ga']
        opts, ids = sk.lettered(r, [('right', C.OIL_KIND[kind]), ('other', other)] + [(f'w{i}', w) for i, w in enumerate(C.OIL_WRONG)])
        kinds = dict(so='xe số', ga='xe tay ga', con='xe côn tay')
        out.append((sk.step('nhot', 'loai', 'choice', 'Chọn đúng loại nhớt', f'Đây là {kinds[kind]}. Đổ nhớt gì?', opts), ids['right']))
        out.append(_oil_change(r, 'nhot'))
        if level >= 1:
            cap, big = r.choice(((800, 1000), (900, 1100), (700, 900)))
            out.append((sk.step('nhot', 'ml', 'number', 'Đổ đúng lượng nhớt',
                                f'Sổ tay xe ghi: thay nhớt {_num(cap / 1000)} lít, rã máy {_num(big / 1000)} lít. Lần này chỉ thay nhớt. Đổ bao nhiêu ml?',
                                unit='ml'), cap))
    elif fault == 'bugi':
        every = r.choice((6000, 8000, 10000))
        last = r.randrange(5000, 20000, 100)
        odo = last + every + r.randrange(200, 2500, 50)
        out.append((sk.step('bugi', 'qua', 'number', 'Bugi quá hạn bao nhiêu km',
                            f'Sổ bảo dưỡng: thay bugi mỗi {_km(every)} km, lần trước thay ở {_km(last)} km, đồng hồ giờ {_km(odo)} km. '
                            'Bugi đã quá hạn bao nhiêu km?', unit='km'), odo - last - every))
        look = r.choice(tuple(C.PLUG_LOOK))
        opts, ids = sk.lettered(r, [(k, v[1]) for k, v in C.PLUG_LOOK.items()])
        out.append((sk.step('bugi', 'soi', 'choice', 'Soi đầu bugi cũ', f'Bugi tháo ra: {C.PLUG_LOOK[look][0]}. Điều đó cho thấy gì?', opts), ids[look]))
        out.append(sk.ordered(r, 'bugi', 'thay', 'Thay bugi đúng thứ tự', 'Bấm lần lượt các việc thay bugi.', C.STEPS['bugi']))
    elif fault == 'xich':
        lo, hi = r.choice(((20, 30), (25, 35), (20, 40)))
        mid = (lo + hi) // 2
        now = hi + r.randrange(4, 18, 2)
        out.append((sk.step('sen', 'chung', 'number', 'Chỉnh độ chùng sên',
                            f'Đo độ chùng ở giữa sên: {now} mm. Sổ tay: {lo}–{hi} mm, chỉnh về giữa khoảng. Phải rút bớt bao nhiêu mm?', unit='mm'),
                    now - mid))
        out.append(sk.ordered(r, 'sen', 'chinh', 'Chỉnh sên đúng thứ tự', 'Bấm lần lượt các việc chỉnh sên.', C.STEPS['sen']))
        if level >= 1:
            state = r.choice(tuple(C.SPROCKET))
            opts, ids = sk.lettered(r, [(k, v[1]) for k, v in C.SPROCKET.items()] + [(f'w{i}', w) for i, w in enumerate(C.SPROCKET_WRONG)])
            out.append((sk.step('sen', 'dia', 'choice', 'Soi nhông sên dĩa', f'{C.SPROCKET[state][0]}.', opts), ids[state]))
    elif fault == 'phanh':
        new, limit = r.choice((4, 5)), r.choice((1, 2))
        now = limit if r.random() < 0.6 else limit + r.choice((1, 2))
        worn = now <= limit
        out.append((sk.step('phanh', 'day', 'number', 'Đo má phanh',
                            f'Má phanh mới dày {new} mm, tới {limit} mm là phải thay. Đo má phanh còn {now} mm. '
                            'Còn dùng được bao nhiêu mm nữa trước giới hạn? (Tới giới hạn rồi thì ghi 0.)', unit='mm'), max(0, now - limit)))
        opts, ids = sk.lettered(r, [('new', C.BRAKE_NEW), ('ok', C.BRAKE_OK)] + [(f'w{i}', w) for i, w in enumerate(C.BRAKE_WRONG)])
        out.append((sk.step('phanh', 'chot', 'choice', 'Chốt cách xử lý phanh', 'Theo số đo vừa rồi, làm gì với má phanh?', opts), ids['new' if worn else 'ok']))
        if worn:
            out.append(sk.ordered(r, 'phanh', 'thay', 'Thay má phanh đúng thứ tự', 'Bấm lần lượt các việc thay má phanh.', C.STEPS['phanh']))
        lo, hi = r.choice(((10, 20), (10, 30), (20, 30)))
        out.append((sk.step('phanh', 'tay', 'number', 'Chỉnh hành trình tay thắng',
                            f'Sổ tay: hành trình tự do tay thắng {lo}–{hi} mm, chỉnh về giữa khoảng. Chỉnh về bao nhiêu mm?', unit='mm'), (lo + hi) // 2))
    elif fault == 'den':
        out.append(sk.picks(r, 'den', 'kiem', 'Chọn những chỗ phải kiểm', 'Đèn pha tắt ngúm, đèn hậu vẫn sáng. Kiểm những chỗ nào?',
                            C.LIGHT_GOOD, C.LIGHT_BAD))
        amp = r.choice((10, 15))
        out.append((sk.step('den', 'ampe', 'number', 'Lắp đúng cầu chì',
                            f'Nắp hộp cầu chì ghi {amp}A. Khách mua sẵn cầu chì {amp * 2}A “cho bền”. Lắp cầu chì bao nhiêu ampe?', unit='A'), amp))
        if level >= 1:
            out.append(sk.scenario(r, 'den', 'chap', 'Cầu chì mới lại đứt', C.FUSE_BLOWS))
    elif fault == 'acquy':
        state = r.choice(tuple(C.BATTERY))
        opts, ids = sk.lettered(r, [(k, v[1]) for k, v in C.BATTERY.items()] + [('w', C.BATTERY_WRONG)])
        out.append((sk.step('binh', 'do', 'choice', 'Đọc đồng hồ vôn', f'Tắt máy, đo hai cọc bình: {C.BATTERY[state][0]} V. Kết luận?', opts), ids[state]))
        if state == 'hong':
            out.append(sk.ordered(r, 'binh', 'thay', 'Thay bình đúng thứ tự', 'Bấm lần lượt các việc thay ắc quy.', C.STEPS['binh']))
        elif state == 'yeu':
            ah = r.choice((5, 7, 9))
            out.append((sk.step('binh', 'gio', 'number', 'Tính giờ sạc',
                                f'Bình {ah} Ah, sạc chậm dòng 0,5 A. Sạc từ cạn tới đầy mất khoảng bao nhiêu giờ (dung lượng chia dòng sạc)?', unit='giờ'), ah * 2))
        else:
            out.append(sk.scenario(r, 'binh', 'tiep', 'Bình đầy mà đề không quay',
                                   ('Bình đo 12,7 V mà bấm đề chỉ nghe tạch một tiếng. Kiểm gì tiếp?', 'Kiểm rơ-le đề, củ đề và dây mát',
                                    ('Thay bình mới cho chắc', 'Câu bình xe khác vào đề thử'))))
    else:   # ngap
        out.append(sk.scenario(r, 'ngap', 'dau', 'Việc đầu tiên', C.FLOOD_FIRST))
        out.append(sk.ordered(r, 'ngap', 'xu_ly', 'Xử lý xe lội nước', 'Bấm lần lượt các việc cứu máy, trước khi đề thử.', C.STEPS['ngap']))
        cap = r.choice((800, 900, 1000))
        out.append((sk.step('ngap', 'suc', 'number', 'Tính nhớt súc máy',
                            f'Nhớt lẫn nước phải súc: thay hai lần, mỗi lần {cap} ml. Tổng cộng bao nhiêu ml nhớt?', unit='ml'), 2 * cap))
    return out


def ticket(day: int, slot: int) -> dict:
    """The ticket of (day, slot): {steps, key, net, cost, …}. Pure."""
    r = kit.rng(ID, day, slot)
    level = sum(day >= n for n in C.MILESTONES)
    pool = [f for f in C.FAULT_ORDER if C.FAULTS[f]['day'] <= day]
    fault = r.choice(pool)
    F = C.FAULTS[fault]
    npc = r.choice(C.CUSTOMERS)
    who = C.PEOPLE[npc][0]
    bike, kind = r.choice(C.BIKES)
    color = r.choice(C.COLORS)
    plate = _plate(r)
    steps, key = [], {}

    def add(pair):
        st, ans = pair
        steps.append(st)
        key[st['id']] = ans

    others = r.sample([f for f in C.FAULT_ORDER if f != fault], 3)
    opts, ids = sk.lettered(r, [(f, C.FAULTS[f]['name']) for f in [fault] + others])
    say, see = r.choice(F['say']), r.choice(F['see'])
    add((sk.step('nghe', 'loi', 'choice', 'Nghe bệnh, chốt lỗi', f'{who}: “{say}” {see}', opts), ids[fault]))
    open_demands = [x for x in C.DEMANDS if x[0] <= day and (x[4] is None or fault in x[4])]
    want = 2 if level >= 2 and r.random() < 0.5 else 1
    demands = r.sample(open_demands, min(want, len(open_demands)))
    for i, d in enumerate(demands):
        add(sk.scenario(r, 'khach', f'd{i + 1}', 'Khách dặn điều oái oăm', d[1:4]))
    for pair in _fault_steps(r, fault, kind, level, who):
        add(pair)
    if r.random() < 0.5:
        add(sk.picks(r, 'giao', 'kiem', 'Kiểm trước khi giao xe', 'Xe đã sửa xong. Trước khi giao, làm những việc nào?',
                     r.sample(C.CHECKS_GOOD, 3), r.sample(C.CHECKS_BAD, 2)))
    tag = f'UL-{day:03d}{slot:02d}'
    near = [plate, plate[:-2] + plate[-1] + plate[-2] if plate[-1] != plate[-2] else plate[:-1] + str((int(plate[-1]) + 1) % 10),
            r.choice([p for p in C.PROVINCES if p != plate[:2]]) + plate[2:]]
    opts, ids = sk.lettered(r, [(f'p{i}', f'Biển {p} · {bike} màu {color}') for i, p in enumerate(near)])
    add((sk.step('giao', 'xe', 'choice', 'Giao đúng xe',
                 f'Khách đưa phiếu {tag}: {bike} màu {color}, biển {plate}. Ba chiếc giống hệt nhau đậu sát nhau. Giao chiếc nào?', opts), ids['p0']))
    net = F['net'] + 2 * len(demands) + level
    return dict(steps=steps, key=key, fault=fault, fault_name=F['name'], emoji=F['emoji'], bike=bike, kind=kind, color=color,
                plate=plate, tag=tag, npc=npc, opening=f'{who} dắt chiếc {bike.lower()} màu {color} vào tiệm: “{say}”',
                cost=F['cost'], net=net, demands=len(demands))


def make_task(day: int, slot: int, serial: int) -> dict:
    tk = ticket(day, slot)
    needs = {k: v for k, v in tk.items() if k not in ('key', 'npc', 'opening')}
    return kit.base_task(ID, day, slot, serial, tk['npc'], f'{tk["bike"]} màu {tk["color"]}', tk['opening'],
                         gen=GEN, kind='ticket', needs=needs, _key=tk['key'], at=0, work={}, errors=[], wrong=0,
                         quality=100, paid=0, lines=[], stage='work')


# ---------------------------------------------------------------- player jobs (🛎️ Phố dịch vụ, game/moto_service.py)
def svc_job(order: str, service: str) -> tuple:
    """(steps, key) of a player's order: the same three steps for one order, always. Pure."""
    r = kit.rng(ID, 'svc', order, service)
    return sk.pairs_to_steps((_pressure(r, 'bd', 'Chủ xe'), _oil_change(r, 'bd'),
                              sk.picks(r, 'bd', 'an_toan', 'Kiểm an toàn trước khi giao', 'Bảo dưỡng định kỳ: kiểm những gì?',
                                       ('Đèn, xi-nhan và còi', 'Độ mòn má phanh', 'Độ chùng sên', 'Gai lốp'),
                                       ('Tháo gương cho gọn', 'Chỉnh lùi đồng hồ km'))))


def _svc(d: dict, p: dict) -> dict:
    return sk.svc_work(d, p, SERVICES, svc_job, '🔧 Bảo dưỡng xong! Bấm Giao để trả xe cho khách ở 🛎️ Phố dịch vụ.')


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, earned=0)


def initial() -> dict:
    return dict(intro=False, today=_today(0), closed_day=0, stats=dict(jobs=0, good=0, active_days=0, earned=0, svc=0),
                desk=kit.desk_initial(), svc=[], svc_ok=[])


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _quality(wrong: int) -> int:
    return sk.quality(wrong, C.WRONG_COST, C.QUALITY_FLOOR)


def _severity(step_id: str) -> int:
    """A redone brake or flood step is a safety matter for the review."""
    return 2 if step_id.split('.')[0] in ('phanh', 'ngap') else 1


def _net(t: dict) -> int:
    return max(5, t['needs']['net'] * t['quality'] // 100)


def has_cert(s: dict) -> bool:
    rec = ((s.get('journey') or {}).get('certificates') or {}).get(CERT_ID)
    return isinstance(rec, dict) and rec.get('earned_day') is not None


def parts_cost(s: dict, n: dict) -> int:
    """What the parts of this bike cost the shop: the certificate's perk takes 1 xu off (never below 0)."""
    return max(0, n['cost'] - (1 if has_cert(s) else 0))


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('xm_intro', 'xm_step', 'xm_desk', 'xm_svc'), 'Thao tác ở tiệm sửa xe không hợp lệ.')
    d = _data(c)
    if name == 'xm_intro':
        d['intro'] = True
        return dict(message='Út Lanh quăng cho cái giẻ: “Nghe bệnh trước, cầm cờ lê sau nghe con.”')
    desk = d['desk']
    if name == 'xm_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở tiệm cần quyết, quyết xong rồi làm tiếp nhé.')
    if name == 'xm_svc':
        return _svc(d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Nghe khách tả bệnh xe trước đã.')
    correct, message, finished = sk.work(t, p, _quality, 'Út Lanh', LINES, _severity)
    if not finished:
        result = dict(message=message, correct=correct)
        _after(s, c, d, result)
        return result
    n = t['needs']
    net = _net(t)
    t['paid'] = net
    good = t['quality'] >= 90
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['earned'] += net
    kit.complete(s, c, t, net + n['cost'], f'Giao {n["bike"].lower()} biển {n["plate"]}: {n["fault_name"].lower()}, chất lượng {t["quality"]}%.',
                 bonus_base=net)
    paid_parts = parts_cost(s, n)
    kit.money(s, c, -paid_parts, f'Phụ tùng, vật tư: {n["fault_name"].lower()}', t['id'], 'materials')
    result = dict(message=f'Giao xe đúng phiếu {n["tag"]}. Thu {net + n["cost"]} xu: phụ tùng {n["cost"]} xu, công {net} xu.'
                          + (' 🎓 Đại lý bớt 1 xu phụ tùng nhờ chứng chỉ.' if paid_parts < n['cost'] else ''),
                  correct=good, celebrate=good)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, C.DESK, None)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(C.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    kit.desk_start(s, c, ID, d['desk'], C.DESK, None, c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], C.DESK)
    if today['day'] == c['day'] and today['good'] > 0 and d['closed_day'] != c['day']:
        d['stats']['active_days'] += 1
        d['closed_day'] = c['day']
    lines = [f'Út Lanh giao {today["jobs"]} xe, {today["good"]} xe đạt từ 90%, công sau phụ tùng {today["earned"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, jobs=today['jobs'], clean=today['good'], earned=today['earned'])


def known_request(c: dict, t: dict) -> str:
    extra = ' Khách còn dặn thêm điều oái oăm, chốt với khách trước khi làm nhé.' if t['needs']['demands'] else ''
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Nghe khách tả bệnh xe.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Xe đã giao; nhận xe tiếp theo.'


def feedback(c, t: dict) -> dict:
    steps = t['needs']['steps']
    n = len(t['errors'])
    talked = any(e.startswith('khach.') for e in t['errors'])
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='talk', label='Nói thật với khách', score=3 if talked else 5, note='Yêu cầu oái oăm đã chốt thật thà, có ghi phiếu.'),
                          dict(key='safe', label='Xe an toàn khi giao', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    elif t['at'] == 0:   # the first step names it: not before it is answered
        for k in ('fault', 'fault_name', 'emoji'):
            v['needs'].pop(k, None)
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    st = d['stats']
    d['mastered'] = st['good'] >= C.MASTER[0] and st['active_days'] >= C.MASTER[1]
    d['expert'] = st['good'] >= C.EXPERT[0] and st['active_days'] >= C.EXPERT[1]
    d['desk'] = kit.desk_public(d['desk'], C.DESK, ID, c)
    d['svc'], d['svc_ok'] = sk.svc_public(kit.data(c), svc_job)
    return d


def content() -> dict:
    return dict(
        rules=C.RULES,
        faults=[dict(id=k, name=v['name'], emoji=v['emoji'], day=v['day']) for k, v in C.FAULTS.items()],
        intro=dict(title='Một ngày ở tiệm sửa xe Út Lanh',
                   lead='Tiệm sửa xe máy đầu hẻm. Nghe khách tả bệnh, chốt lỗi, chốt với khách những điều oái oăm rồi mới cầm cờ lê. '
                        'Phụ tùng tiệm ứng theo phiếu, trừ một lần khi giao xe; tiền công giảm theo chất lượng.',
                   work=[['🛞', 'Vá săm, bơm đúng áp suất'], ['🛢️', 'Thay nhớt đúng loại, đúng lượng'],
                         ['🛑', 'Phanh, sên, bugi, ắc quy, đèn'], ['🌊', 'Xe lội nước: không đề vội']],
                   meet=[['🔧', 'Út Lanh chủ tiệm'], ['🧽', 'Tèo thợ phụ'], ['👵', 'Bà Chín bán vé số']],
                   stars=[['📏', 'Số đo theo sổ tay của tiệm, không đoán'], ['🌀', 'Khách oái oăm: nói thật, ghi phiếu']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    sk.validate_slip(t, original, FIXED, _quality, _net, LINES, 'phiếu sửa xe')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ tiệm sửa xe sai.')
    kit.need(type(d['intro']) is bool, 'Sổ tiệm sửa xe sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), 'Thống kê tiệm sửa xe sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số xe đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], C.DESK)
    sk.svc_validate(d, SERVICES, svc_job)


SPEC = dict(
    id=ID, prefix=PREFIX, category='shop', people=PEOPLE,
    meta=dict(short='Sửa xe máy', place=C.PLACE, tagline='Nghe bệnh trước, cầm cờ lê sau.', icon='wrench',
              color='#c0562b', light='#fbe9dd', weather='Mùi nhớt và cao su nóng', work='Phiếu sửa xe', station='Cầu nâng và tủ đồ nghề',
              greeting='Nghe khách tả bệnh, chốt lỗi, chốt với khách những điều oái oăm rồi mới đụng cờ lê.',
              caption='Xe êm, người yên tâm', map_label='SỬA XE ÚT LANH'),
    staff=[('Tèo', 'helper', 'Thợ phụ: rửa xe, bơm bánh, đưa đồ nghề.', 72, 80)], roles={'helper': 'Thợ phụ'},
    tip=1, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    activity=('🏍️', 'Sổ tay tiệm sửa xe', [('Lốp', 'Theo tem càng xe'), ('Nhớt', 'Đúng loại, đúng lượng'), ('Phanh', 'Tới giới hạn là thay'),
                                         ('Xe ngập', 'Không đề vội')],
              ['Nghe bệnh, chốt lỗi', 'Chốt với khách', 'Làm từng bước theo sổ tay', 'Kiểm và giao đúng xe']),
    stories=[('Chiếc cờ lê số 10', ('Út Lanh đưa chiếc cờ lê mòn vẹt: “Của ba cô để lại.”', 'Bạn siết con ốc xả nhớt vừa tay, không quá chặt.',
                                    'Út Lanh cười: “Ốc xả mà siết như siết nắp hũ là toét ren, nhớ nghe.”'))],
    review_asides=['Tiệm nói thật bệnh xe, không vẽ thêm.', 'Thay nhớt xong còn đưa nhớt cũ cho coi.', 'Bơm bánh đúng áp, xe chạy êm ru.'],
    situations=[],
    more_line='Thêm một chiếc xe vừa dắt vào tiệm.', open_line='Út Lanh kéo cửa sắt; cầu nâng, tủ đồ nghề và sổ tay tiệm đã sẵn.',
    guide='Nghe bệnh, chốt lỗi → chốt với khách điều oái oăm → làm từng bước theo sổ tay (thứ tự, áp suất, lượng nhớt, số đo) → '
          'kiểm trước khi giao → giao đúng xe theo biển số. Sai thì làm lại bước đó, tiền công giảm theo chất lượng.',
)
