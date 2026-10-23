"""🎬 Hãng phim Bến Mây: a salaried actor on the studio's TV series, one scene at a time (players #471 "diễn viên, đi
hát", #472 "làm diễn viên ca sĩ"; owner 21/10 "nghề mới thì làm đi").

A scene is one page of the script (a quarrel, a farewell, a reunion, a night scare, a stunt, a scene with the child
actor, a rain scene, or the premiere's press call) with one or two awkward demands from the set (actor_content.DEMANDS:
a real slap, a leaked script page, a fake dating rumour, unpaid overtime, a stunt without mats, a child kept past bedtime,
a wet cable in the rain…). It is a list of server-graded steps (game/careers/stepkit.py), worked one at a time: read the
page and name the scene → settle the demands → say the lines in the script's order → stand on the mark → [match the
last shot's continuity photo] → take the director's note → [the good takes still to shoot] → [the stunt's safety
order] → hang the costume back on the right hook. The premiere swaps the set for a press call: the speech's order, a
reporter's question, [what may be posted]. A wrong answer stays open to redo and costs quality. The studio pays a salary
(employment posting) and a small quality bonus per scene, like 🩺 the vet. Between scenes the studio has its surprises
(kit.desk, actor_content.DESK), some of which come back days later (marks).
"""
from __future__ import annotations

from copy import deepcopy

from . import actor_content as C
from . import kit
from . import stepkit as sk

ID = 'actor'
PREFIX = 'dn_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('dn_step',)
FREE = ('dn_intro',)
NO_TICK = ('dn_intro', 'dn_desk')
LINES = 24
SAFETY = ('doan', 'an_toan')   # step jobs where a redo is a safety or honesty matter: it weighs double in the review


# ---------------------------------------------------------------- building a scene (pure: day, slot)
def _set_steps(r, name: str, K: dict, level: int) -> list:
    """[(step, answer)] of a scene shot on set."""
    out = [sk.ordered(r, 'thoai', 'thu_tu', 'Nói thoại đúng thứ tự', 'Bấm lần lượt các câu theo kịch bản.', K['lines']),
           sk.scenario(r, 'vi_tri', 'dau', 'Đứng đúng vị trí', r.choice(C.BLOCKING))]
    if level >= 1:
        out.append(sk.scenario(r, 'noi_canh', 'khop', 'Nối cảnh cho khớp', r.choice(C.CONTINUITY)))
    out.append(sk.scenario(r, 'dao_dien', 'chi_dao', 'Nghe đạo diễn chỉ đạo', r.choice(C.DIRECTIONS)))
    if level >= 1:
        angles, each = r.choice(C.RETAKE), r.choice((2, 3))
        done = r.randint(1, angles * each - 1)
        out.append((sk.step('quay_lai', 'luot', 'number', 'Đếm lượt còn phải quay',
                            f'Cảnh có {angles} góc máy, mỗi góc cần {each} lượt đạt. Đã quay đạt {done} lượt. Còn bao nhiêu lượt đạt nữa?',
                            unit='lượt'), angles * each - done))
    if name == 'hanh_dong':
        out.append(sk.ordered(r, 'an_toan', 'thu_tu', 'Tập cảnh hành động an toàn', 'Bấm lần lượt các việc với anh Lực.', C.STEPS['an_toan']))
    return out


def _press_steps(r, K: dict, level: int) -> list:
    """[(step, answer)] of the premiere's press call."""
    out = [sk.ordered(r, 'thoai', 'thu_tu', 'Phát biểu đúng thứ tự', 'Bấm lần lượt các câu phát biểu.', K['lines']),
           sk.scenario(r, 'hop_bao', 'tra_loi', 'Trả lời phóng viên', r.choice(C.PRESS))]
    if level >= 1:
        out.append(sk.picks(r, 'hop_bao', 'dang', 'Đăng gì quảng bá phim', 'Anh Tùng hỏi đăng gì lên trang của bạn. Chọn những gì được đăng.',
                            C.PROMO_GOOD, C.PROMO_BAD))
    return out


def scene(day: int, slot: int) -> dict:
    """The scene of (day, slot): {steps, key, bonus, …}. Pure."""
    r = kit.rng(ID, day, slot)
    level = sum(day >= n for n in C.MILESTONES)
    pool = [k for k in C.SCENE_ORDER if C.SCENES[k]['day'] <= day]
    name = r.choice(pool)
    K = C.SCENES[name]
    who = C.PEOPLE[K['npc']][0]
    say, see = r.choice(K['say']), r.choice(K['see'])
    role = r.choice(C.ROLES)
    pairs = []
    others = r.sample([k for k in C.SCENE_ORDER if k != name], 3)
    opts, ids = sk.lettered(r, [(k, C.SCENES[k]['name']) for k in [name] + others])
    pairs.append((sk.step('kich_ban', 'canh', 'choice', 'Đọc kịch bản, chốt cảnh', f'{who}: “{say}” {see}', opts), ids[name]))
    open_demands = [x for x in C.DEMANDS if x[0] <= day and (x[4] is None or name in x[4])]
    want = 2 if level >= 2 and r.random() < 0.5 else 1
    demands = r.sample(open_demands, min(want, len(open_demands)))
    for i, x in enumerate(demands):
        pairs.append(sk.scenario(r, 'doan', f'd{i + 1}', 'Đoàn phim dặn điều oái oăm', x[1:4]))
    pairs += _press_steps(r, K, level) if K['plan'] == 'press' else _set_steps(r, name, K, level)
    hook = r.choice(C.COSTUME_HOOKS)
    near = [(hook, role), (hook + 1, role), (hook, r.choice([x for x in C.ROLES if x != role]))]
    opts, ids = sk.lettered(r, [(f'p{i}', f'Móc {n} · thẻ {x}') for i, (n, x) in enumerate(near)])
    pairs.append((sk.step('phuc_trang', 'moc', 'choice', 'Trả trang phục đúng móc',
                          f'Chị Sa dặn: “Bộ đồ {role} treo móc {hook} nha.” Ba móc giống nhau. Treo vào móc nào?', opts), ids['p0']))
    steps, key = sk.pairs_to_steps(pairs)
    return dict(steps=steps, key=key, scene=name, scene_name=K['name'], emoji=K['emoji'], role=role, hook=hook,
                npc=K['npc'], opening=f'{who}: “{say}”', bonus=K['bonus'] + len(demands), demands=len(demands))


def make_task(day: int, slot: int, serial: int) -> dict:
    sc = scene(day, slot)
    needs = {k: v for k, v in sc.items() if k not in ('key', 'npc', 'opening')}
    return kit.base_task(ID, day, slot, serial, sc['npc'], f'Phim “{C.SERIES}” · {sc["role"]}', sc['opening'],
                         gen=GEN, kind='scene', needs=needs, _key=sc['key'], at=0, work={}, errors=[], wrong=0,
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
    """A redone demand or stunt step is a safety or honesty matter."""
    return 2 if step_id.split('.')[0] in SAFETY else 1


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('dn_intro', 'dn_step', 'dn_desk'), 'Thao tác ở trường quay không hợp lệ.')
    d = _data(c)
    if name == 'dn_intro':
        d['intro'] = True
        return dict(message='Đạo diễn Minh Triết đưa tập kịch bản: “Diễn ít thôi, sống nhiều vào. Và an toàn trước, đẹp sau nghe em.”')
    desk = d['desk']
    if name == 'dn_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở trường quay cần quyết, quyết xong rồi quay tiếp nhé.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc trang kịch bản trước đã.')
    correct, message, finished = sk.work(t, p, _quality, 'Đạo diễn Minh Triết', LINES, _severity)
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
    kit.complete(s, c, t, bonus, f'Quay xong {n["scene_name"].lower()}, trả đồ {n["role"]} đúng móc {n["hook"]}, chất lượng {t["quality"]}%.')
    result = dict(message=f'“Cắt! Đạt!” Đồ {n["role"]} về đúng móc {n["hook"]}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.',
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
    lines = [f'Hãng phim Bến Mây: bạn quay {today["jobs"]} cảnh, {today["good"]} cảnh đạt từ 90%, thưởng chất lượng {today["bonus"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, jobs=today['jobs'], clean=today['good'], bonus=today['bonus'])


def known_request(c: dict, t: dict) -> str:
    extra = ' Đoàn phim còn dặn thêm điều oái oăm, chốt cho an toàn, thật thà trước khi quay nhé.' if t['needs']['demands'] else ''
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Đọc trang kịch bản.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Đã quay xong; chuẩn bị cảnh tiếp theo.'


def feedback(c, t: dict) -> dict:
    steps = t['needs']['steps']
    n = len(t['errors'])
    risky = any(e.split('.')[0] in SAFETY for e in t['errors'])
    return dict(criteria=[dict(key='steps', label='Diễn đúng kịch bản', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='talk', label='Thật thà với đoàn và báo chí', score=3 if risky else 5, note='Không tin đồn, không lộ kịch bản.'),
                          dict(key='safe', label='An toàn trên trường quay', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    elif t['at'] == 0:   # the first step names it: not before it is answered
        for k in ('scene', 'scene_name', 'emoji'):
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
        scenes=[dict(id=k, name=v['name'], emoji=v['emoji'], day=v['day']) for k, v in C.SCENES.items()],
        intro=dict(title='Một ngày ở Hãng phim Bến Mây',
                   lead=f'Bạn đóng phim truyền hình “{C.SERIES}”. Đọc kịch bản, chốt với đoàn những điều oái oăm, nói thoại đúng thứ tự, '
                        'đứng đúng dấu, nghe đạo diễn rồi mới quay. Lương theo hợp đồng, thêm thưởng nhỏ theo chất lượng từng cảnh.',
                   work=[['📜', 'Đọc kịch bản, xếp thoại'], ['❌', 'Đứng đúng dấu, nối cảnh cho khớp'],
                         ['🎬', 'Nghe đạo diễn, đếm lượt quay'], ['🥋', 'Cảnh hành động: tập với anh Lực trước']],
                   meet=[['🎬', 'Đạo diễn Minh Triết'], ['📋', 'Chị Kiều thư ký trường quay'], ['🥋', 'Anh Lực điều phối hành động']],
                   stars=[['🛡️', 'An toàn trước, đẹp sau'], ['🌀', 'Đoàn phim oái oăm: không tát thật, không tin đồn']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    sk.validate_slip(t, original, FIXED, _quality, _bonus, LINES, 'cảnh quay')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ trường quay sai.')
    kit.need(type(d['intro']) is bool, 'Sổ trường quay sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), 'Thống kê trường quay sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số cảnh đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], C.DESK)


SPEC = dict(
    id=ID, prefix=PREFIX, category='service', people=PEOPLE,
    meta=dict(short='Diễn viên', place=C.PLACE, tagline='Diễn ít thôi, sống nhiều vào.', icon='sparkles',
              color='#c0812b', light='#fbf0de', weather='Đèn quay nóng rực, tiếng bảng clap và lời “Diễn!”', work='Cảnh quay',
              station='Trường quay và phòng phục trang',
              greeting='Đọc kịch bản, chốt với đoàn điều oái oăm, đứng đúng dấu rồi mới quay.',
              caption='An toàn trước, đẹp sau', map_label='HÃNG PHIM BẾN MÂY'),
    staff=[('Chị Kiều', 'script', 'Thư ký trường quay: ảnh nối cảnh, sổ thoại.', 84, 90),
           ('Anh Lực', 'stunt', 'Điều phối hành động: đệm, bảo hộ, tập chậm.', 88, 94),
           ('Chị Nhung', 'makeup', 'Hóa trang, chụp ảnh lớp phấn để nối cảnh.', 80, 90),
           ('Anh Cường', 'props', 'Giữ đạo cụ, đánh dấu vị trí từng món trên bàn.', 84, 88)],
    roles={'script': 'Thư ký trường quay', 'stunt': 'Hành động', 'makeup': 'Hóa trang', 'props': 'Đạo cụ'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    activity=('🎬', 'Một cảnh ở Bến Mây', [('Thoại', 'Đúng kịch bản'), ('Vị trí', 'Đúng dấu'), ('Nối cảnh', 'Theo ảnh'), ('Hành động', 'Tập trước')],
              ['Đọc kịch bản, chốt cảnh', 'Chốt với đoàn', 'Thoại, vị trí, đạo diễn', 'Quay đủ lượt, trả trang phục']),
    stories=[('Tập kịch bản đầu tiên', ('Đạo diễn Minh Triết đưa tập kịch bản còn thơm mùi mực, góc giấy có tên bạn.', 'Bạn đọc to câu thoại đầu, giọng run run.',
                                         'Đạo diễn gật đầu: “Run là tốt. Người không run thì không biết sợ cho nhân vật.”'))],
    review_asides=['Diễn viên thuộc thoại, đứng đúng dấu, quay nhanh lắm.', 'Thật thà với báo chí, không chiêu trò.', 'Cảnh hành động tập kỹ, không ai trầy xước.'],
    situations=[],
    more_line='Chị Kiều vừa đưa thêm một trang kịch bản.', open_line='Đạo diễn Minh Triết ngồi sau màn hình; đèn, máy quay và bảng clap đã sẵn.',
    guide='Đọc kịch bản, chốt cảnh → chốt với đoàn điều oái oăm → nói thoại đúng thứ tự, đứng đúng dấu, nối cảnh → nghe đạo diễn, '
          'đếm lượt quay, tập hành động an toàn → trả trang phục đúng móc. Sai thì làm lại bước đó, thưởng giảm theo chất lượng.',
    employment=dict(postings=[dict(id='actor-benmay', org='Hãng phim Bến Mây', kind='company', title='Diễn viên phim truyền hình',
                                   salary=(58, 76), probation_days=3, wants=['creative', 'patience', 'teamwork'],
                                   perks=['Đạo diễn Minh Triết kèm những cảnh đầu', 'Thưởng chất lượng mỗi cảnh', 'Lương ca theo hợp đồng'],
                                   culture='An toàn trước, đẹp sau; thoại đổi phải hỏi đạo diễn; kịch bản là bí mật; không tin đồn, không chiêu trò.',
                                   questions=['mistake', 'conflict'], reference=False)], questions={}),
)
