"""🎤 Phòng trà Mây Chiều: a salaried singer at the town's tea room, one turn on stage at a time (players #471 "diễn
viên, đi hát", #472 "làm diễn viên ca sĩ"; owner 21/10 "nghề mới thì làm đi").

A set is one evening's room (who sits there, what they ask for: bolero, old songs, a love song for a proposal, a
birthday, a year-end party…) with one or two awkward demands (singer_content.DEMANDS: mime to a recording, hand the mic
to a tipsy guest, drink with a big spender, impersonate a famous voice, film the whole set for a paid channel…). It is a
list of server-graded steps (game/careers/stepkit.py), worked one at a time: read the room and name the set → settle the
demands → warm up in order → pick the song from the tea room's own songbook (every title invented; a famous hit nobody
licensed is the trap) → the sound check with the engineer → [the minutes left in the turn] → [a request slip from the
floor] → [an incident on stage: a dead mic, a forgotten line, a blackout] → the encore → the dedication to the right
table. A wrong answer stays open to redo and costs quality. The tea room pays a salary (employment posting) and a small
quality bonus per set, like 🩺 the vet. Between sets the tea room has its surprises (kit.desk, singer_content.DESK),
some of which come back days later (marks).
"""
from __future__ import annotations

from copy import deepcopy

from . import kit
from . import singer_content as C
from . import stepkit as sk

ID = 'singer'
PREFIX = 'cs_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('cs_step',)
FREE = ('cs_intro',)
NO_TICK = ('cs_intro', 'cs_desk')
LINES = 24
TRUST = ('khach', 'su_co')   # step jobs where a redo is felt by the whole room: it weighs double in the review


# ---------------------------------------------------------------- building a set (pure: day, slot)
def _song(r, name: str) -> tuple:
    """The song for the room, from the tea room's songbook: (step, answer)."""
    right = r.choice(C.SETS[name]['songs'])
    others = r.sample([k for k in C.SET_ORDER if k != name], 2)
    rows = [('right', f'“{right}” · {C.SETS[name]["name"].lower()}')]
    rows += [(f'o{i}', f'“{r.choice(C.SETS[k]["songs"])}” · {C.SETS[k]["name"].lower()}') for i, k in enumerate(others)]
    rows.append(('trap', C.SONG_TRAP))
    opts, ids = sk.lettered(r, rows)
    return sk.step('so', 'bai', 'choice', 'Chọn bài trong sổ hợp âm', 'Khán phòng đang chờ. Bài nào hợp với họ?', opts), ids['right']


def _minutes(r) -> tuple:
    turn = r.choice(C.SET_MINUTES)
    a, b, talk = r.choice((4, 5, 6)), r.choice((4, 5, 6)), r.choice((2, 3))
    return (sk.step('gio', 'con_lai', 'number', 'Tính giờ còn lại của lượt',
                    f'Lượt của bạn {turn} phút. Đã hát một bài {a} phút, một bài {b} phút, chào và giới thiệu mất {talk} phút. '
                    'Còn bao nhiêu phút?', unit='phút'), turn - a - b - talk)


def _set_steps(r, name: str, level: int) -> list:
    """[(step, answer)] of the set's own hands-on work, from the warm-up to the encore."""
    out = [sk.ordered(r, 'giong', 'khoi_dong', 'Khởi động giọng đúng thứ tự', 'Bấm lần lượt các việc khởi động trước khi lên.', C.STEPS['khoi_dong']),
           _song(r, name),
           sk.scenario(r, 'am_thanh', 'chinh', 'Thử âm với anh Tâm', r.choice(C.SOUND_CHECK))]
    if level >= 1:
        out.append(_minutes(r))
        out.append(sk.scenario(r, 'xin_bai', 'giay', 'Giấy xin bài', r.choice(C.REQUESTS)))
    if level >= 2:
        out.append(sk.scenario(r, 'su_co', 'xu_ly', 'Sự cố trên sân khấu', r.choice(C.INCIDENTS)))
    out.append(sk.scenario(r, 'het_luot', 'encore', 'Hết lượt', r.choice(C.ENCORE)))
    return out


def evening(day: int, slot: int) -> dict:
    """The set of (day, slot): {steps, key, bonus, …}. Pure."""
    r = kit.rng(ID, day, slot)
    level = sum(day >= n for n in C.MILESTONES)
    pool = [k for k in C.SET_ORDER if C.SETS[k]['day'] <= day]
    name = r.choice(pool)
    K = C.SETS[name]
    guest = K['guest']
    who = C.PEOPLE[guest][0]
    say, see = r.choice(K['say']), r.choice(K['see'])
    pairs = []
    others = r.sample([k for k in C.SET_ORDER if k != name], 3)
    opts, ids = sk.lettered(r, [(k, C.SETS[k]['name']) for k in [name] + others])
    pairs.append((sk.step('phong', 'kieu', 'choice', 'Nhìn khán phòng, chọn kiểu hát', f'{who}: “{say}” {see}', opts), ids[name]))
    open_demands = [x for x in C.DEMANDS if x[0] <= day and (x[4] is None or name in x[4])]
    want = 2 if level >= 2 and r.random() < 0.5 else 1
    demands = r.sample(open_demands, min(want, len(open_demands)))
    for i, x in enumerate(demands):
        pairs.append(sk.scenario(r, 'khach', f'd{i + 1}', 'Khách dặn điều oái oăm', x[1:4]))
    pairs += _set_steps(r, name, level)
    table = r.randint(1, 9)
    to = r.choice(C.DEDICATEES)
    near = [(table, to), (table % 9 + 1, to), (table, r.choice([x for x in C.DEDICATEES if x != to]))]
    opts, ids = sk.lettered(r, [(f'p{i}', f'Bàn {n} · tặng {x}') for i, (n, x) in enumerate(near)])
    pairs.append((sk.step('loi_chuc', 'ban', 'choice', 'Đọc lời chúc đúng bàn',
                          f'Giấy xin bài ghi: bàn {table}, tặng {to}. Ba tờ giấy giống nhau trên giá micro. Đọc tờ nào?', opts), ids['p0']))
    steps, key = sk.pairs_to_steps(pairs)
    return dict(steps=steps, key=key, set=name, set_name=K['name'], emoji=K['emoji'], guest=who, table=table, to=to,
                npc=guest, opening=f'{who}: “{say}”', bonus=K['bonus'] + len(demands), demands=len(demands))


def make_task(day: int, slot: int, serial: int) -> dict:
    ev = evening(day, slot)
    needs = {k: v for k, v in ev.items() if k not in ('key', 'npc', 'opening')}
    return kit.base_task(ID, day, slot, serial, ev['npc'], f'Bàn {ev["table"]} · {ev["guest"]}', ev['opening'],
                         gen=GEN, kind='set', needs=needs, _key=ev['key'], at=0, work={}, errors=[], wrong=0,
                         quality=100, paid=0, lines=[], stage='work')


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, bonus=0)


def initial() -> dict:
    return dict(intro=False, today=_today(0), closed_day=0, stats=dict(jobs=0, good=0, active_days=0, bonus=0), desk=kit.desk_initial())


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
    """A redone demand or stage incident happened in front of the whole room."""
    return 2 if step_id.split('.')[0] in TRUST else 1


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('cs_intro', 'cs_step', 'cs_desk'), 'Thao tác ở phòng trà không hợp lệ.')
    d = _data(c)
    if name == 'cs_intro':
        d['intro'] = True
        return dict(message='Cô Diệu Hiền chỉnh lại giá micro cho bạn: “Hát cho người ngồi trước mặt mình, không hát cho cái micro nghe con.”')
    desk = d['desk']
    if name == 'cs_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở phòng trà cần quyết, quyết xong rồi hát tiếp nhé.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Nghe khách nói muốn nghe gì trước đã.')
    correct, message, finished = sk.work(t, p, _quality, 'Cô Diệu Hiền', LINES, _severity)
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
    kit.complete(s, c, t, bonus, f'Hát trọn lượt {n["set_name"].lower()}, lời chúc tới đúng bàn {n["table"]}, chất lượng {t["quality"]}%.')
    result = dict(message=f'Cả phòng vỗ tay, lời chúc tới đúng bàn {n["table"]}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.',
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
    lines = [f'Phòng trà Mây Chiều: bạn hát {today["jobs"]} lượt, {today["good"]} lượt đạt từ 90%, thưởng chất lượng {today["bonus"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, jobs=today['jobs'], clean=today['good'], bonus=today['bonus'])


def known_request(c: dict, t: dict) -> str:
    extra = ' Khách còn dặn thêm điều oái oăm, chốt cho khéo trước khi lên hát nhé.' if t['needs']['demands'] else ''
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Nghe khách nói muốn nghe gì.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Đã hết lượt; chuẩn bị lượt tiếp theo.'


def feedback(c, t: dict) -> dict:
    steps = t['needs']['steps']
    n = len(t['errors'])
    room = any(e.split('.')[0] in TRUST for e in t['errors'])
    return dict(criteria=[dict(key='steps', label='Hát đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='talk', label='Hát thật, giữ mực với khách', score=3 if room else 5, note='Không hát nhép, không chiều khách sai.'),
                          dict(key='safe', label='Giọng và sân khấu vững', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    elif t['at'] == 0:   # the first step names it: not before it is answered
        for k in ('set', 'set_name', 'emoji'):
            v['needs'].pop(k, None)
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    st = d['stats']
    d['mastered'] = st['good'] >= C.MASTER[0] and st['active_days'] >= C.MASTER[1]
    d['expert'] = st['good'] >= C.EXPERT[0] and st['active_days'] >= C.EXPERT[1]
    d['desk'] = kit.desk_public(d['desk'], C.DESK, ID, c)
    return d


def content() -> dict:
    return dict(
        rules=C.RULES,
        sets=[dict(id=k, name=v['name'], emoji=v['emoji'], day=v['day']) for k, v in C.SETS.items()],
        intro=dict(title='Một tối ở Phòng trà Mây Chiều',
                   lead='Bạn là ca sĩ của phòng trà. Nhìn khán phòng, chọn bài, khởi động, thử âm rồi mới lên hát. '
                        'Hát thật, giữ mực với khách. Lương theo hợp đồng, thêm thưởng nhỏ theo chất lượng từng lượt hát.',
                   work=[['🌙', 'Nhìn khán phòng, chọn kiểu hát'], ['🎶', 'Khởi động giọng, chọn bài trong sổ hợp âm'],
                         ['🎚️', 'Thử âm, xử lý micro hú'], ['💐', 'Hết lượt, đọc lời chúc đúng bàn']],
                   meet=[['🎤', 'Cô Diệu Hiền chủ phòng trà'], ['🎚️', 'Anh Tâm âm thanh'], ['🎹', 'Chú Bảy ban nhạc']],
                   stars=[['🎙️', 'Hát thật, không hát nhép'], ['🌀', 'Khách oái oăm: mời khéo, giữ cả phòng']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    sk.validate_slip(t, original, FIXED, _quality, _bonus, LINES, 'lượt hát')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ phòng trà sai.')
    kit.need(type(d['intro']) is bool, 'Sổ phòng trà sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), 'Thống kê phòng trà sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số lượt đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], C.DESK)


SPEC = dict(
    id=ID, prefix=PREFIX, category='service', people=PEOPLE,
    meta=dict(short='Ca sĩ phòng trà', place=C.PLACE, tagline='Hát cho người ngồi trước mặt mình.', icon='music',
              color='#b0475f', light='#f8e4e9', weather='Đèn vàng, tiếng piano và mùi trà sen', work='Lượt hát', station='Sân khấu nhỏ và giá micro',
              greeting='Nhìn khán phòng, khởi động giọng, thử âm rồi mới lên hát.',
              caption='Hát thật, cả phòng lặng nghe', map_label='PHÒNG TRÀ MÂY CHIỀU'),
    staff=[('Anh Tâm', 'sound', 'Kỹ thuật âm thanh: micro, loa kiểm âm, micro dự phòng.', 82, 88),
           ('Chú Bảy', 'band', 'Trưởng ban nhạc, đàn piano, đổi tông theo giọng.', 86, 92),
           ('Chị Mơ', 'dress', 'Ủi váy diễn, dặm phấn, treo đồ diễn đúng móc.', 82, 88),
           ('Anh Huy', 'band', 'Tay trống, giữ nhịp chắc, đếm vào bài rõ ràng.', 86, 86)],
    roles={'sound': 'Âm thanh', 'band': 'Ban nhạc', 'dress': 'Phục trang – trang điểm'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    activity=('🎤', 'Một lượt hát ở Mây Chiều', [('Bài', 'Trong sổ hợp âm'), ('Giọng', 'Khởi động trước'), ('Âm thanh', 'Thử với anh Tâm'), ('Lượt', 'Đúng giờ')],
              ['Nhìn khán phòng, chọn kiểu hát', 'Chốt với khách', 'Khởi động, chọn bài, thử âm', 'Hát trọn lượt, đọc lời chúc']),
    stories=[('Giá micro của cô Diệu Hiền', ('Cô Diệu Hiền đưa cây giá micro bằng đồng đã mòn chỗ tay cầm.', 'Bạn hạ giá xuống ngang cằm, hít một hơi thật sâu.',
                                             'Cô gật đầu: “Ba mươi năm cô đứng sau cây giá này. Giờ tới lượt con.”'))],
    review_asides=['Ca sĩ hát thật, nghe mà nổi da gà.', 'Đọc lời chúc đúng tên, mẹ tôi khóc luôn.', 'Micro không hú lần nào, nghe êm tai.'],
    situations=[],
    more_line='Thêm một bàn vừa gửi giấy xin bài.', open_line='Cô Diệu Hiền bật đèn sân khấu; micro, loa kiểm âm và sổ hợp âm đã sẵn.',
    guide='Nhìn khán phòng, chọn kiểu hát → chốt với khách điều oái oăm → khởi động, chọn bài trong sổ hợp âm, thử âm → '
          'giữ giờ, giấy xin bài, sự cố → hết lượt, đọc lời chúc đúng bàn. Sai thì làm lại bước đó, thưởng giảm theo chất lượng.',
    employment=dict(postings=[dict(id='singer-maychieu', org='Phòng trà Mây Chiều', kind='company', title='Ca sĩ phòng trà',
                                   salary=(54, 70), probation_days=3, wants=['creative', 'calm', 'communication'],
                                   perks=['Cô Diệu Hiền kèm những lượt đầu', 'Thưởng chất lượng mỗi lượt hát', 'Lương ca theo hợp đồng'],
                                   culture='Hát thật, không hát nhép; chỉ hát bài đã xin phép; giữ đúng giờ lượt hát; không uống rượu với khách.',
                                   questions=['mistake', 'conflict'], reference=False)], questions={}),
)
