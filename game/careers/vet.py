"""🩺 Phòng khám Thú y Cỏ May: a salaried vet at the clinic every pet owner in town already knows (game/pets.py sends
pets there for 🩺 khám and 💉 tiêm), owner 21/10 "làm thêm nghề khác".

A case is one pet on the table (a name, dog or cat, a cage number, a collar) with one problem (vet_content.CASES: a
vaccination, a nail trim, ticks, a dog that ate chocolate, a puppy with bloody diarrhoea, a male cat that cannot pee,
a swallowed sock or thread, a planned spay) and one or two awkward owner demands. It is a list of server-graded steps
(game/careers/stepkit.py), worked one at a time: hear the owner and name the problem → settle the demands → the case's
own hands-on steps (weighing by difference, a temperature read, a dose by weight, a fluid volume, the order of a
procedure) → [what to tell the owner] → hand back the right pet by its cage slip. A wrong answer stays open to redo and
costs quality. The clinic pays a salary (employment posting) and a small quality bonus per case, like 📻 the radio.
Between cases the clinic has its surprises (kit.desk, vet_content.DESK), some of which come back days later (marks).

Players' own pets are examined and vaccinated for other players through 🛎️ Phố dịch vụ (game/vet_service.py): the
order is worked here as a three-step job (ty_svc) whose finish is recorded in this career's data (`svc_ok`), which the
market's deliver hook reads from the provider's save before it pays.
"""
from __future__ import annotations

from copy import deepcopy

from . import kit
from . import stepkit as sk
from . import vet_content as C

ID = 'vet'
PREFIX = 'ty_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('ty_step', 'ty_svc')
FREE = ('ty_intro',)
NO_TICK = ('ty_intro', 'ty_desk')
LINES = 24
SERVICES = ('kham', 'tiem')


# ---------------------------------------------------------------- building a case (pure: day, slot)
def _g(v: int) -> str:
    return f'{v:,}'.replace(',', '.')


def _weigh(r, job: str, kind: str, kgs) -> tuple:
    """((step, answer), kg): weighing by difference. Dogs: the assistant holds the pet on the people scale (kg);
    cats: in the carrier on the kitchen scale (g)."""
    kg = r.choice(kgs)
    if kind == 'dog':
        alone = r.randint(48, 62)
        st = sk.step(job, 'can', 'number', 'Cân bé',
                     f'Chị Duyên ôm bé đứng lên cân: {alone + kg} kg. Chị Duyên đứng một mình: {alone} kg. Bé nặng bao nhiêu kg?', unit='kg')
        return (st, kg), kg
    cage = r.choice((900, 1100, 1300))
    st = sk.step(job, 'can', 'number', 'Cân bé',
                 f'Cân cả lồng xách: {_g(kg * 1000 + cage)} g. Lồng rỗng: {_g(cage)} g. Bé nặng bao nhiêu gam?', unit='g')
    return (st, kg * 1000), kg


def _temp(r, job: str, fever: bool) -> tuple:
    reading = r.choice(('39,8', '40,1', '40,4')) if fever else r.choice(('38,3', '38,6', '38,8'))
    opts, ids = sk.lettered(r, [('ok', C.TEMP_READ['ok']), ('sot', C.TEMP_READ['sot'])] + [(f'w{i}', w) for i, w in enumerate(C.TEMP_WRONG)])
    return sk.step(job, 'nhiet', 'choice', 'Đo thân nhiệt', f'Nhiệt kế hậu môn: {reading} °C. Kết luận?', opts), ids['sot' if fever else 'ok']


def _case_steps(r, case: str, kind: str, level: int) -> list:
    """[(step, answer)] of the case's own hands-on work."""
    out = []
    if case == 'tiem':
        if level >= 1:
            out.append(_weigh(r, 'tiem', kind, (3, 4, 5, 6) if kind == 'cat' else (4, 6, 8, 12))[0])
        fever = r.random() < 0.3
        out.append(_temp(r, 'tiem', fever))
        if fever:
            out.append(sk.scenario(r, 'tiem', 'hoan', 'Chủ nài tiêm luôn',
                                   ('Chủ: “Tiêm luôn hôm nay đi, đi lại mất công lắm.”', 'Hoãn tiêm, khám tìm nguyên nhân sốt, hẹn tiêm khi hết sốt',
                                    ('Tiêm luôn cho chủ vui', 'Tiêm rồi cho thêm thuốc hạ sốt'))))
        else:
            out.append(sk.ordered(r, 'tiem', 'quy_trinh', 'Tiêm đúng thứ tự', 'Bấm lần lượt các việc tiêm phòng.', C.STEPS['tiem']))
    elif case == 'cat_mong':
        out.append(sk.ordered(r, 'mong', 'quy_trinh', 'Cắt móng đúng thứ tự', 'Bấm lần lượt các việc cắt móng.', C.STEPS['mong']))
        front, back = (5, 4)
        done = r.choice((1, 2, 3))
        legs = ['chân trước trái', 'chân trước phải', 'chân sau trái', 'chân sau phải'][:done]
        left = 2 * front + 2 * back - sum(front if 'trước' in x else back for x in legs)
        out.append((sk.step('mong', 'dem', 'number', 'Đếm móng còn lại',
                            f'Mỗi chân trước {front} móng, mỗi chân sau {back} móng. Đã cắt xong: {", ".join(legs)}. Còn bao nhiêu móng?', unit='móng'), left))
        if level >= 1:
            out.append(sk.scenario(r, 'mong', 'tuy', 'Lỡ cắt trúng tủy', C.QUICK_BLEED))
    elif case == 've':
        (pair, kg) = _weigh(r, 've', 'dog', (3, 6, 9, 12, 18, 30))
        out.append(pair)
        band = next(i for i, (hi, _) in enumerate(C.PIPETTE) if kg < hi)
        opts, ids = sk.lettered(r, [(i, label) for i, (_, label) in enumerate(C.PIPETTE)])
        out.append((sk.step('ve', 'ong', 'choice', 'Chọn ống thuốc nhỏ gáy', f'Bé nặng {kg} kg. Ống nào?', opts), ids[band]))
        out.append(sk.ordered(r, 've', 'go', 'Gỡ ve đúng thứ tự', 'Bấm lần lượt các việc gỡ con ve to sau tai.', C.STEPS['ve']))
        if level >= 1:
            out.append(sk.picks(r, 've', 'dan', 'Dặn chủ phòng ve', 'Dặn chủ những gì?', C.TICK_GOOD, C.TICK_BAD))
    elif case == 'socola':
        (pair, kg) = _weigh(r, 'socola', 'dog', (5, 10, 15, 20, 25, 30))
        out.append(pair)
        early = r.random() < 0.65
        out.append(sk.scenario(r, 'socola', 'gio', 'Ăn bao lâu rồi?', C.CHOC_EARLY if early else C.CHOC_LATE))
        if early:
            out.append((sk.step('socola', 'lieu', 'number', 'Tính liều thuốc gây nôn',
                                f'Sổ tay: 1 ml cho mỗi 5 kg. Bé nặng {kg} kg. Bao nhiêu ml?', unit='ml'), kg // 5))
        out.append(sk.picks(r, 'socola', 'dan', 'Dặn chủ ở nhà', 'Dặn chủ những gì?', C.CHOC_HOME_GOOD, C.CHOC_HOME_BAD))
    elif case == 'parvo':
        out.append(sk.scenario(r, 'parvo', 'cach_ly', 'Việc đầu tiên', C.PARVO_FIRST))
        (pair, kg) = _weigh(r, 'parvo', 'dog', (2, 3, 4, 5))
        out.append(pair)
        rate, hours = r.choice((4, 5, 6)), r.choice((4, 6, 8))
        out.append((sk.step('parvo', 'dich', 'number', 'Tính lượng dịch truyền',
                            f'Truyền dịch {rate} ml mỗi kg mỗi giờ, trong {hours} giờ. Bé nặng {kg} kg. Tổng bao nhiêu ml?', unit='ml'),
                    rate * kg * hours))
        out.append(sk.ordered(r, 'parvo', 've_sinh', 'Làm việc trong phòng cách ly', 'Bấm lần lượt các việc ở phòng cách ly.', C.STEPS['parvo']))
    elif case == 'tac_tieu':
        out.append(sk.scenario(r, 'tieu', 'gap', 'Chủ muốn để mai', C.URINE_FIRST))
        (pair, kg) = _weigh(r, 'tieu', 'cat', (3, 4, 5, 6))
        out.append(pair)
        out.append((sk.step('tieu', 'nuoc', 'number', 'Lượng nước mỗi ngày',
                            f'Sổ tay: khoảng 50 ml nước mỗi kg mỗi ngày. Bé nặng {kg} kg. Mỗi ngày bé cần bao nhiêu ml?', unit='ml'), 50 * kg))
        out.append(sk.picks(r, 'tieu', 'dan', 'Dặn chủ sau khi thông tiểu', 'Dặn chủ những gì?', C.URINE_GOOD, C.URINE_BAD))
    elif case == 'di_vat':
        out.append(sk.scenario(r, 'divat', 'dau', 'Việc đầu tiên', C.FOREIGN_FIRST))
        film = r.choice(tuple(C.FOREIGN_XRAY))
        opts, ids = sk.lettered(r, [(k, v[1]) for k, v in C.FOREIGN_XRAY.items()] + [('w', C.FOREIGN_WRONG)])
        out.append((sk.step('divat', 'phim', 'choice', 'Đọc phim X-quang', f'Phim chụp: {C.FOREIGN_XRAY[film][0]}. Quyết thế nào?', opts), ids[film]))
        if film == 'to':
            hour = r.choice((14, 15, 16, 17))
            out.append((sk.step('divat', 'nhin', 'number', 'Giờ ăn bữa cuối',
                                f'Mổ lúc {hour} giờ. Sổ tay: nhịn ăn 8 tiếng trước mổ. Bé được ăn bữa cuối trước mấy giờ?', unit='giờ'), hour - 8))
            out.append(sk.ordered(r, 'divat', 'mo', 'Mổ đúng thứ tự', 'Bấm lần lượt các việc của ca mổ.', C.STEPS['mo']))
        else:
            out.append(sk.picks(r, 'divat', 'dan', 'Dặn chủ theo dõi', 'Dặn chủ những gì?', C.ADVICE_GOOD, C.ADVICE_BAD))
    else:   # triet_san
        hour = r.choice((13, 14, 15, 16))
        out.append((sk.step('triet', 'nhin', 'number', 'Giờ ăn bữa cuối',
                            f'Mổ lúc {hour} giờ. Sổ tay: nhịn ăn 8 tiếng trước mổ. Bé được ăn bữa cuối trước mấy giờ?', unit='giờ'), hour - 8))
        if level >= 1 and r.random() < 0.3:
            out.append(sk.scenario(r, 'triet', 'an_roi', 'Bé đã ăn sáng', C.FED_ALREADY))
        else:
            out.append(sk.ordered(r, 'triet', 'mo', 'Mổ đúng thứ tự', 'Bấm lần lượt các việc của ca mổ.', C.STEPS['mo']))
            out.append(sk.picks(r, 'triet', 'dan', 'Dặn chủ sau mổ', 'Dặn chủ những gì?', C.AFTER_OP_GOOD, C.AFTER_OP_BAD))
    return out


def case(day: int, slot: int) -> dict:
    """The case of (day, slot): {steps, key, bonus, …}. Pure."""
    r = kit.rng(ID, day, slot)
    level = sum(day >= n for n in C.MILESTONES)
    pool = [k for k in C.CASE_ORDER if C.CASES[k]['day'] <= day]
    name = r.choice(pool)
    K = C.CASES[name]
    kind = r.choice(K['kinds'])
    pet, _, what = r.choice([x for x in C.PETS if x[1] == kind])
    owner = r.choice(C.OWNERS)
    who = C.PEOPLE[owner][0]
    say, see = r.choice(K['say']), r.choice(K['see'])
    pairs = []
    others = r.sample([k for k in C.CASE_ORDER if k != name], 3)
    opts, ids = sk.lettered(r, [(k, C.CASES[k]['name']) for k in [name] + others])
    pairs.append((sk.step('kham', 'benh', 'choice', 'Nghe chủ kể, chốt bệnh', f'{who}: “{say}” {see}', opts), ids[name]))
    open_demands = [x for x in C.DEMANDS if x[0] <= day and (x[4] is None or name in x[4] or kind in x[4])]
    want = 2 if level >= 2 and r.random() < 0.5 else 1
    demands = r.sample(open_demands, min(want, len(open_demands)))
    for i, x in enumerate(demands):
        pairs.append(sk.scenario(r, 'chu', f'd{i + 1}', 'Chủ nuôi dặn điều oái oăm', x[1:4]))
    pairs += _case_steps(r, name, kind, level)
    cage = r.randint(1, 9)
    collar = r.choice(C.COLLARS)
    near = [(cage, collar), (cage % 9 + 1, collar), (cage, r.choice([x for x in C.COLLARS if x != collar]))]
    opts, ids = sk.lettered(r, [(f'p{i}', f'Chuồng {n} · bé {pet} ({what}) · {col}') for i, (n, col) in enumerate(near)])
    pairs.append((sk.step('tra', 'be', 'choice', 'Trả đúng bé',
                          f'{who} đưa phiếu: chuồng {cage}, bé {pet}, {what}, {collar}. Ba bé giống nhau đang chờ. Trả bé nào?', opts), ids['p0']))
    steps, key = sk.pairs_to_steps(pairs)
    return dict(steps=steps, key=key, case=name, case_name=K['name'], emoji=K['emoji'], pet=pet, pet_kind=kind, what=what,
                cage=cage, collar=collar, npc=owner, opening=f'{who} bế bé {pet} ({what}) vào phòng khám: “{say}”',
                bonus=K['bonus'] + len(demands), demands=len(demands))


def make_task(day: int, slot: int, serial: int) -> dict:
    cs = case(day, slot)
    needs = {k: v for k, v in cs.items() if k not in ('key', 'npc', 'opening')}
    return kit.base_task(ID, day, slot, serial, cs['npc'], f'Bé {cs["pet"]} ({cs["what"]})', cs['opening'],
                         gen=GEN, kind='case', needs=needs, _key=cs['key'], at=0, work={}, errors=[], wrong=0,
                         quality=100, paid=0, lines=[], stage='work')


# ---------------------------------------------------------------- player jobs (🛎️ Phố dịch vụ, game/vet_service.py)
def svc_job(order: str, service: str) -> tuple:
    """(steps, key) of a player's order: the same three steps for one order, always. Pure."""
    r = kit.rng(ID, 'svc', order, service)
    kind = r.choice(('dog', 'cat'))
    weigh = _weigh(r, 'dv', kind, (3, 4, 5) if kind == 'cat' else (4, 6, 8, 12))[0]
    if service == 'tiem':
        return sk.pairs_to_steps((weigh, _temp(r, 'dv', False),
                                  sk.ordered(r, 'dv', 'tiem', 'Tiêm đúng thứ tự', 'Bấm lần lượt các việc tiêm phòng.', C.STEPS['tiem'])))
    return sk.pairs_to_steps((weigh, sk.ordered(r, 'dv', 'kham', 'Khám tổng quát đúng thứ tự', 'Bấm lần lượt các việc khám.', C.STEPS['kham']),
                              sk.picks(r, 'dv', 'dan', 'Dặn chủ', 'Khám xong, dặn chủ những gì?', C.ADVICE_GOOD, C.ADVICE_BAD)))


def _svc(d: dict, p: dict) -> dict:
    return sk.svc_work(d, p, SERVICES, svc_job, '🩺 Khám xong! Bấm Giao để trả bé cho chủ ở 🛎️ Phố dịch vụ.')


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, bonus=0)


def initial() -> dict:
    return dict(intro=False, today=_today(0), closed_day=0, stats=dict(jobs=0, good=0, active_days=0, bonus=0, svc=0),
                desk=kit.desk_initial(), svc=[], svc_ok=[])


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _quality(wrong: int) -> int:
    return sk.quality(wrong, C.WRONG_COST, C.QUALITY_FLOOR)


def _bonus(t: dict) -> int:
    return max(3, t['needs']['bonus'] * t['quality'] // 100)


def _severity(step_id: str) -> int:
    """A redone emergency step (isolation, a dose, an urgent cat) weighs more in the review."""
    return 2 if step_id.split('.')[0] in ('parvo', 'tieu', 'socola', 'divat') else 1


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('ty_intro', 'ty_step', 'ty_desk', 'ty_svc'), 'Thao tác ở phòng khám không hợp lệ.')
    d = _data(c)
    if name == 'ty_intro':
        d['intro'] = True
        return dict(message='Bác sĩ Thảo đưa ống nghe: “Cân bé trước, tính liều sau, và nói thật với chủ nghe em.”')
    desk = d['desk']
    if name == 'ty_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở phòng khám cần quyết, quyết xong rồi khám tiếp nhé.')
    if name == 'ty_svc':
        return _svc(d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Nghe chủ kể bệnh của bé trước đã.')
    correct, message, finished = sk.work(t, p, _quality, 'Bác sĩ Thảo', LINES, _severity)
    if not finished:
        result = dict(message=message, correct=correct)
        _after(s, c, d, result)
        return result
    n = t['needs']
    bonus = _bonus(t)
    t['paid'] = bonus
    good = t['quality'] >= 90
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['bonus'] += bonus
    kit.complete(s, c, t, bonus, f'Trả bé {n["pet"]} ({n["case_name"].lower()}) đúng chuồng {n["cage"]}, chất lượng {t["quality"]}%.')
    result = dict(message=f'Trả bé {n["pet"]} đúng chuồng {n["cage"]}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.', correct=good, celebrate=good)
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
    lines = [f'Phòng khám Cỏ May: bạn khám {today["jobs"]} ca, {today["good"]} ca đạt từ 90%, thưởng chất lượng {today["bonus"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, jobs=today['jobs'], clean=today['good'], bonus=today['bonus'])


def known_request(c: dict, t: dict) -> str:
    extra = ' Chủ nuôi còn dặn thêm điều oái oăm, chốt với chủ trước khi làm nhé.' if t['needs']['demands'] else ''
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Nghe chủ kể bệnh của bé.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Đã trả bé; mời ca tiếp theo.'


def feedback(c, t: dict) -> dict:
    steps = t['needs']['steps']
    n = len(t['errors'])
    talked = any(e.startswith('chu.') for e in t['errors'])
    return dict(criteria=[dict(key='steps', label='Khám, chữa đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='talk', label='Nói thật với chủ nuôi', score=3 if talked else 5, note='Yêu cầu oái oăm đã chốt thật thà.'),
                          dict(key='safe', label='Bé an toàn', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    elif t['at'] == 0:   # the first step names it: not before it is answered
        for k in ('case', 'case_name', 'emoji'):
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
        cases=[dict(id=k, name=v['name'], emoji=v['emoji'], day=v['day']) for k, v in C.CASES.items()],
        intro=dict(title='Một ngày ở Phòng khám Thú y Cỏ May',
                   lead='Phòng khám chó mèo cả phố hay ghé. Nghe chủ kể, cân bé, chốt bệnh, chốt với chủ những điều oái oăm rồi mới làm. '
                        'Lương theo hợp đồng, thêm thưởng nhỏ theo chất lượng từng ca.',
                   work=[['💉', 'Tiêm phòng: đo nhiệt trước'], ['⚖️', 'Cân bé, tính liều theo cân'],
                         ['🍫', 'Cấp cứu ngộ độc, tắc tiểu'], ['🩹', 'Mổ: nhịn ăn đủ giờ']],
                   meet=[['🩺', 'Bác sĩ Thảo'], ['📒', 'Chị Duyên trợ lý'], ['🐶', 'Cô Ba Mập và bé Lu']],
                   stars=[['📏', 'Số liệu theo sổ tay phòng khám'], ['🌀', 'Chủ nuôi oái oăm: nói thật, không chiều sai']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    sk.validate_slip(t, original, FIXED, _quality, _bonus, LINES, 'ca khám')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ phòng khám sai.')
    kit.need(type(d['intro']) is bool, 'Sổ phòng khám sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), 'Thống kê phòng khám sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số ca đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], C.DESK)
    sk.svc_validate(d, SERVICES, svc_job)


SPEC = dict(
    id=ID, prefix=PREFIX, category='service', people=PEOPLE,
    meta=dict(short='Bác sĩ thú y', place=C.PLACE, tagline='Cân trước, tính liều sau, nói thật với chủ.', icon='heart',
              color='#2f8f7a', light='#dff3ee', weather='Mùi cồn sát trùng và tiếng mèo kêu meo meo', work='Phiếu khám', station='Bàn khám và tủ vắc xin',
              greeting='Nghe chủ kể, cân bé, chốt bệnh, chốt với chủ những điều oái oăm rồi mới làm.',
              caption='Bé khỏe, chủ yên tâm', map_label='THÚ Y CỎ MAY'),
    staff=[('Bác sĩ Thảo', 'doctor', 'Trưởng phòng khám, kèm bạn những ca đầu.', 86, 92), ('Chị Duyên', 'assist', 'Trợ lý: cân bé, giữ sổ tiêm, ôm bé.', 80, 86)],
    roles={'doctor': 'Bác sĩ', 'assist': 'Trợ lý'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    activity=('🩺', 'Một ca ở Cỏ May', [('Tiêm', 'Đo nhiệt trước'), ('Liều', 'Theo cân nặng'), ('Cấp cứu', 'Làm ngay'), ('Mổ', 'Nhịn ăn 8 tiếng')],
              ['Nghe chủ kể, chốt bệnh', 'Chốt với chủ', 'Cân, đo, làm từng bước', 'Dặn chủ, trả đúng bé']),
    stories=[('Chiếc ống nghe của bác sĩ Thảo', ('Bác sĩ Thảo đưa chiếc ống nghe cũ, dây đã ngả màu.', 'Bạn áp lên ngực bé Mướp, nghe tim đập lộp bộp như mưa.',
                                                 'Bác sĩ Thảo cười: “Nghe đủ một phút, đừng vội, bé nào cũng cần một phút của mình.”'))],
    review_asides=['Bác sĩ cân bé, tính thuốc kỹ lắm.', 'Nói thật bệnh tình, không bán thuốc thừa.', 'Trợ lý ôm bé nhẹ nhàng, bé không sợ.'],
    situations=[],
    more_line='Thêm một bé vừa được bế vào phòng khám.', open_line='Bác sĩ Thảo bật đèn bàn khám; tủ vắc xin, cân và sổ tiêm đã sẵn.',
    guide='Nghe chủ kể, chốt bệnh → chốt với chủ điều oái oăm → cân, đo, làm từng bước theo sổ tay (liều, dịch truyền, thứ tự) → '
          'dặn chủ → trả đúng bé theo phiếu chuồng. Sai thì làm lại bước đó, thưởng giảm theo chất lượng.',
    employment=dict(postings=[dict(id='vet-comay', org='Phòng khám Thú y Cỏ May', kind='company', title='Bác sĩ thú y',
                                   salary=(56, 72), probation_days=3, wants=['careful', 'patience', 'communication'],
                                   perks=['Bác sĩ Thảo kèm những ca đầu', 'Thưởng chất lượng mỗi ca', 'Lương ca theo hợp đồng'],
                                   culture='Cân trước, tính liều sau; không bán thuốc thừa, không ký sổ khống; ca cấp cứu được ưu tiên.',
                                   questions=['mistake', 'conflict'], reference=False)], questions={}),
)
