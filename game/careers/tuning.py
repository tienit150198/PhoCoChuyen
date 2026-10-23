"""🔧 Xưởng độ xe Tư Pít-tông: a tuning shop, one car or motorbike at a time (owner 21/10 "độ xe này kia làm kĩ vào nhé",
player #470 "Thêm độ xe để đua xe đi ad ơi").

A ticket is one customer's vehicle (a model, a colour, a plate) with a goal (tuning_content.GOALS: đi phố êm, triển lãm,
đua drag ở trường đua, đua đường đèo trong ngày đóng đường), a budget for parts and one or two awkward demands. It is a
list of server-graded steps (game/careers/stepkit.py), worked one at a time:
  hear the customer and name the goal → inspect the vehicle [→ match the registration papers] → the build sheet (the
  goal's priority list within the budget, legal parts only) → the parts total → settle the demands → fit the first part
  (its procedure in order) [→ its own reading] → the second part's reading → read the dyno chart (the peak gain, or the
  peak) [→ the AFR line] → [the safety checks] → the noise or CO reading against the notebook's limit → the test drive
  on the shop's own track → the spec card that matches the dyno.
A wrong answer stays open to redo and costs quality. Parts are advanced against the ticket and settled once at hand-back
(net labour = the ticket's labour × quality), so an empty till never strands a car.

⚖️ Legal rules: the build sheet always offers one illegal fit (a straight pipe, the catalytic converter out, flashing
lights, a folding plate frame); the legal demands (khí thải, tiếng ồn, đèn, biển số, giấy tờ, an toàn), the papers check
and the noise / CO reading too. Choosing an illegal answer is still a wrong step (redo it) and on top of that the ward
warns the shop: LEGAL_FINE xu (a 'fine' row) and a warning counted in the shop's data; every WARN_EVERY-th warning sets
the desk mark 'warned', which brings 📋 the inspection team (tuning_content.DESK).

Players' own vehicles are tuned for other players through 🛎️ Phố dịch vụ (game/tuning_service.py): the order is worked
here as a three-step job (dx_svc) whose finish is recorded in this career's data (`svc_ok`), which the market's deliver
hook reads from the provider's save before it pays; the buyer's vehicle then gains the part (game/racing.py).
"""
from __future__ import annotations

from copy import deepcopy
from . import kit
from . import stepkit as sk
from . import tuning_content as C

ID = 'tuning'
CERT_ID = 'tuning_basics'   # certificate_content.GROUPS (hire=False): its perk is 2 xu off the parts of each build
PREFIX = 'dx_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('dx_step', 'dx_svc')
FREE = ('dx_intro',)
NO_TICK = ('dx_intro', 'dx_desk')
LINES = 24
SERVICES = ('do_dong_co', 'do_khung_gam', 'bao_duong_do')
LAW = '!law'          # _key[LAW]: {step id: [illegal letters] | None (every wrong answer is illegal)}
SAFETY = ('phanh', 'an_toan', 'chay_thu', 'luat', 'dyno')


# ---------------------------------------------------------------- building a ticket (pure: day, slot)
def _num(v: int) -> str:
    """Tenths → '12,8'."""
    return f'{v // 10},{v % 10}'


def _thousands(v: int) -> str:
    return f'{v:,}'.replace(',', '.')


def _plate(r) -> str:
    return f'{r.choice(C.PROVINCES)}{r.choice("ABCDEFGHKLMNPSTUVXZ")}-{r.randint(100, 999)}.{r.randint(10, 99)}'


def _frame(r) -> str:
    return f'RL{r.choice("HKMN")}{r.choice("ABCJ")}{r.randint(1000, 9999)}{r.choice("NPRS")}{r.choice("ABCDEFGHJK")}{r.randint(100000, 999999)}'


def _near(frame: str, i: int) -> str:
    """A registration number one slip away from `frame`: two digits swapped (i=0) or one digit changed (i=1)."""
    head, tail = frame[:-6], list(frame[-6:])
    if i == 0:
        k = next((k for k in range(5) if tail[k] != tail[k + 1]), 0)
        tail[k], tail[k + 1] = tail[k + 1], tail[k]
        if ''.join(tail) == frame[-6:]:
            tail[0] = str((int(tail[0]) + 2) % 10)
    else:
        tail[-2] = str((int(tail[-2]) + 3) % 10)
    return head + ''.join(tail)


def lname(text: str) -> str:
    """A name inside a sentence: the first letter in lower case ('Nạp lại bản đồ ECU' → 'nạp lại bản đồ ECU')."""
    return text[:1].lower() + text[1:]


def _ki(kind: str) -> int:
    return 0 if kind == 'bike' else 1


def cost_of(mod: str, kind: str) -> int | None:
    M = C.MODS.get(mod) or C.ILLEGAL[mod]
    return M['cost'][_ki(kind)]


def build_of(goal: str, kind: str, budget: int) -> list:
    """The shop's rule: the goal's priority list, a part taken while it still fits the budget, skipped when it does not."""
    out, left = [], budget
    for m in C.GOALS[goal]['prio']:
        c = cost_of(m, kind)
        if c is not None and c <= left:
            out.append(m)
            left -= c
    return out


def _dyno(r, kind: str, hp: int, top: int, build: list, goal: str) -> dict:
    """The dyno sheet: rpm points, power before and after (mã lực), the AFR line at full load (tenths)."""
    step = 1000 if kind == 'bike' else 500
    lo = 3000 if kind == 'bike' else 1500
    rpm = list(range(lo, top + 1, step))
    peak = max(lo + step, round(top * .85 / step) * step)
    gain = sum(C.MODS[m]['hp'] for m in build)
    before, after = [], []
    for x in rpm:
        u = x / peak
        s = 1 - (1 - u) ** 2 * (0.9 if u < 1 else 3.0)
        raw = hp * max(.2, s)
        before.append(round(raw))
        after.append(round(raw * (100 + gain) / 100))
    target = 118 if 'turbo' in build else 132 if goal in ('pho', 'show') else 128
    afr = [target + r.randint(-3, 3) for _ in rpm]
    if r.random() < .45:
        i = r.randrange(len(rpm) * 2 // 3, len(rpm))
        afr[i] = r.randint(137, 145)
    return dict(rpm=rpm, before=before, after=after, afr=afr, unit='mã lực', gain=gain)


def _mod_check(r, mod: str, ctx: dict) -> tuple:
    """The reading or the choice that goes with fitting `mod`: (step, answer)."""
    job = 'do'
    G = C.GOALS[ctx['goal']]
    kind = ctx['kind']
    if mod == 'ecu':
        right = 'turbo' if 'turbo' in ctx['build'] else 'pho' if ctx['goal'] in ('pho', 'show') else 'nat'
        opts, ids = sk.lettered(r, list(C.AFR_OPTIONS))
        turbo = ', có lắp turbo' if 'turbo' in ctx['build'] else ''
        return sk.step(job, mod, 'choice', 'Chọn map xăng ở tải lớn', f'Nạp map cho mục tiêu {G["name"].lower()}{turbo}. Đặt tỉ lệ xăng gió (AFR) ở tải lớn bao nhiêu?', opts), ids[right]
    if mod == 'hut_xa':
        return sk.step(job, mod, 'number', 'Chọn vòng tua đo tiếng ồn',
                       f'Vòng tua tối đa của máy: {_thousands(ctx["top"])} vòng/phút. Sổ tay đo tiếng ồn pô ở nửa vòng tua tối đa. Đo ở bao nhiêu vòng/phút?',
                       unit='vòng/phút'), ctx['top'] // 2
    if mod == 'turbo':
        base, boost = r.choice((10, 12, 14, 16)), r.choice((6, 7, 8, 9))
        return sk.step(job, mod, 'number', 'Lùi góc lửa theo tăng áp',
                       f'Góc lửa gốc của máy {base} độ. Turbo đặt tăng áp {boost} psi; mỗi 1 psi lùi lửa 1 độ. Góc lửa ở tải lớn còn bao nhiêu độ?', unit='độ'), base - boost
    if mod == 'lop':
        tem = r.choice((29, 32, 33, 36) if kind == 'bike' else (32, 33, 35, 36))
        adj = 2 if ctx['goal'] == 'deo' else -4 if ctx['goal'] == 'drag' else 0
        which = 'bánh dẫn động' if ctx['goal'] == 'drag' else 'lốp mới'
        return sk.step(job, mod, 'number', 'Bơm đúng áp suất lốp',
                       f'Tem xe ghi áp lạnh {tem} psi. Mục tiêu: {G["name"].lower()}. Bơm {which} bao nhiêu psi?', unit='psi'), tem + adj
    if mod == 'phanh':
        return sk.scenario(r, job, mod, 'Chọn bộ phanh vừa vành', C.BRAKE_DISC)
    if mod == 'giam_xoc':
        if kind == 'bike':
            travel, pct = r.choice((100, 110, 120, 130, 140)), 30
        else:
            travel, pct = r.choice((120, 140, 160, 180)), 25
        return sk.step(job, mod, 'number', 'Chỉnh độ lún tĩnh của phuộc',
                       f'Hành trình phuộc {travel} mm. Sổ tay: độ lún tĩnh bằng {pct}% hành trình. Chỉnh về bao nhiêu mm?', unit='mm'), travel * pct // 100
    if mod == 'giam_can':
        return sk.picks(r, job, mod, 'Chọn đồ được tháo cho nhẹ', 'Giảm cân cho xe: tháo những món nào?', r.sample(C.DROP_GOOD, 3), r.sample(C.DROP_BAD, 2))
    if mod == 'khi_dong':
        return sk.scenario(r, job, mod, 'Chọn cánh gió đúng luật', C.WING)
    if mod == 'son':
        return sk.scenario(r, job, mod, 'Đổi màu xe đúng luật', C.REPAINT)
    h = r.randrange(60, 90)   # den
    return sk.step(job, mod, 'number', 'Chỉnh góc chiếu đèn',
                   f'Tâm đèn cốt cao {h} cm. Cách tường 10 m, vệt sáng phải thấp hơn tâm đèn 10 cm. Vệt sáng cao bao nhiêu cm?', unit='cm'), h - 10


def ticket(day: int, slot: int) -> dict:
    """The ticket of (day, slot): {steps, key, build, dyno, net, cost, …}. Pure."""
    r = kit.rng(ID, day, slot)
    level = sum(day >= n for n in C.MILESTONES)
    goal = r.choice([g for g in C.GOAL_ORDER if C.GOALS[g]['day'] <= day])
    G = C.GOALS[goal]
    npc = r.choice(C.CUSTOMERS)
    who = C.PEOPLE[npc][0]
    name, kind, hp, kg, top = r.choice(C.VEHICLES)
    color = r.choice(C.COLORS)
    plate = _plate(r)
    steps, key, law = [], {}, {}

    def add(pair, illegal=False):
        st, ans = pair
        steps.append(st)
        key[st['id']] = ans
        if illegal is not False:
            law[st['id']] = illegal

    # 1. the goal, from what the customer says
    say = r.choice(G['say'])
    opts, ids = sk.lettered(r, [(g, f'{C.GOALS[g]["emoji"]} {C.GOALS[g]["name"]}') for g in C.GOAL_ORDER])
    add((sk.step('nghe', 'muc_tieu', 'choice', 'Nghe khách, chốt mục tiêu', f'{who}: “{say}” Khách muốn độ để làm gì?', opts), ids[goal]))
    # 2. inspection [and the papers]
    add(sk.picks(r, 'kiem', 'xe', 'Kiểm xe trước khi độ', f'Chiếc {name.lower()} vừa dắt vào, chưa đụng gì. Kiểm những gì trước?',
                 r.sample(C.INSPECT_GOOD, 3), r.sample(C.INSPECT_BAD, 2)))
    if level >= 1 and r.random() < .5:
        frame = _frame(r)
        opts, ids = sk.lettered(r, [('p0', f'Giấy đăng ký số khung {frame}'), ('p1', f'Giấy đăng ký số khung {_near(frame, 0)}'),
                                    ('p2', f'Giấy đăng ký số khung {_near(frame, 1)}')])
        add((sk.step('kiem', 'giay', 'choice', 'Đối chiếu giấy đăng ký',
                     f'Số khung đóng trên xe: {frame}. Khách đưa ba tờ giấy đăng ký xe của nhà. Tờ nào của chiếc này?', opts), ids['p0']), None)
    # 3. the build sheet: the goal's priority list within the budget, one off-goal part and one illegal fit as traps
    avail = [m for m in G['prio'] if cost_of(m, kind) is not None]
    k = min(len(avail), r.choice((2, 3)) if level < 3 else r.choice((2, 3, 4)))
    budget = sum(cost_of(m, kind) for m in avail[:k])
    budget += r.randrange(cost_of(avail[k], kind)) if k < len(avail) else r.randint(0, 5)
    build = build_of(goal, kind, budget)
    off = [m for m in C.MODS if m not in G['prio'] and cost_of(m, kind) is not None]
    trap_off = r.choice(off)
    trap_bad = r.choice(tuple(C.ILLEGAL))
    rows = [(f'g:{m}', m) for m in build] + [(f'b:{m}', m) for m in avail if m not in build] + [(f'b:{trap_off}', trap_off), (f'x:{trap_bad}', trap_bad)]
    labelled = [(k_, f'{(C.MODS.get(m) or C.ILLEGAL[m])["emoji"]} {(C.MODS.get(m) or C.ILLEGAL[m])["name"]} · {cost_of(m, kind)} xu') for k_, m in rows]
    opts, ids = sk.lettered(r, labelled)
    order = ' → '.join(C.SHORT[m] for m in G['prio'] if cost_of(m, kind) is not None)
    add((sk.step('bang', 'chon', 'multi', 'Lên bảng độ trong ngân sách',
                 f'Mục tiêu: {G["name"].lower()}. Khách để {budget} xu cho phụ tùng. Thứ tự ưu tiên của xưởng: {order}. '
                 'Món nào còn vừa tiền thì lấy, không vừa thì bỏ qua xét món sau. Chọn đủ các món sẽ lắp.', opts),
         sorted(ids[f'g:{m}'] for m in build)), [ids[f'x:{trap_bad}']])
    total = sum(cost_of(m, kind) for m in build)
    names = '; '.join(lname(C.MODS[m]['name']) for m in build)
    add((sk.step('bang', 'tong', 'number', 'Cộng tiền phụ tùng', f'Bảng độ đã chốt: {names}. Tổng tiền phụ tùng bao nhiêu xu?', unit='xu'), total))
    # 4. the awkward demands
    open_demands = [x for x in C.DEMANDS if x[0] <= day and (x[4] is None or goal in x[4])]
    want = 2 if level >= 2 and r.random() < .5 else 1
    demands = r.sample(open_demands, min(want, len(open_demands)))
    for i, d in enumerate(demands):
        add(sk.scenario(r, 'luat', f'd{i + 1}', 'Khách dặn điều oái oăm', d[1:4]), None if d[5] in C.LEGAL_RULES else False)
    # 5. the work: the first part in order [and its reading], the second part's reading
    ctx = dict(goal=goal, kind=kind, top=top, build=build)
    first = build[0]
    add(sk.ordered(r, 'lap', first, C.WORK_TITLE[first], f'{C.MODS[first]["name"]}: bấm lần lượt từng việc theo sổ tay.', C.STEPS[first]))
    if level >= 1 or len(build) == 1:
        pair = _mod_check(r, first, ctx)
        add(pair, None if first in ('khi_dong', 'son') else False)
    if len(build) > 1:
        second = build[1]
        add(_mod_check(r, second, ctx), None if second in ('khi_dong', 'son') else False)
    # 6. the dyno
    dyno = _dyno(r, kind, hp, top, build, goal)
    b0, a0 = max(dyno['before']), max(dyno['after'])
    if dyno['gain']:
        add((sk.step('dyno', 'doc', 'number', 'Đọc biểu đồ dyno', 'Biểu đồ dyno trước và sau khi độ đã in ra. Công suất đỉnh tăng thêm bao nhiêu mã lực?',
                     unit='mã lực'), a0 - b0))
    else:
        add((sk.step('dyno', 'doc', 'number', 'Đọc biểu đồ dyno', 'Biểu đồ dyno đã in ra. Công suất đỉnh sau khi làm là bao nhiêu mã lực?', unit='mã lực'), a0))
    if level >= 1 and ('ecu' in build or 'turbo' in build) and r.random() < .6:
        i = max(range(len(dyno['afr'])), key=lambda n: (dyno['afr'][n], n))
        lean = dyno['afr'][i] > C.AFR_LIMIT
        opts, ids = sk.lettered(r, [('ok', 'Đường AFR ở tải lớn nằm trong giới hạn: đạt'),
                                    ('lean', f'Ở {_thousands(dyno["rpm"][i])} vòng/phút AFR {_num(dyno["afr"][i])}: nghèo xăng, nạp lại map rồi chạy dyno lại'),
                                    ('w0', 'Công suất tăng là được, khỏi xem AFR'), ('w1', 'AFR càng cao máy càng khỏe, để vậy')])
        add((sk.step('dyno', 'afr', 'choice', 'Đọc đường AFR', 'Xem đường AFR (tỉ lệ xăng gió) trên biểu đồ dyno. Sổ tay: nghèo hơn 13,5 khi tải lớn là lỗi.', opts),
             ids['lean' if lean else 'ok']))
    # 7. safety and the legal reading
    if r.random() < (.6 if level >= 3 else .35):
        add(sk.picks(r, 'an_toan', 'kiem', 'Kiểm an toàn trước khi giao', 'Đồ đã lắp xong. Trước khi giao, kiểm những gì?',
                     r.sample(C.SAFETY_GOOD, 3), r.sample(C.SAFETY_BAD, 2)))
    if 'hut_xa' in build or r.random() < .5:
        limit = C.NOISE_LIMIT[kind]
        reading = limit + r.choice((-6, -4, -2, -1, 1, 3))
        ok = reading <= limit
        opts, ids = sk.lettered(r, [('pass', 'Đạt: ghi số đo vào phiếu'), ('fail', 'Không đạt: lắp lại ống tiêu âm rồi đo lại'),
                                    ('w0', 'Vượt chút ít thì cho qua'), ('w1', 'Không đạt: dặn khách chạy đường vắng')])
        add((sk.step('an_toan', 'do', 'choice', 'Đo tiếng ồn',
                     f'Máy đo đặt cách miệng pô 0,5 m, máy ở nửa vòng tua tối đa: {reading} dB. Giới hạn sổ tay cho {C.KIND_NAME[kind]}: {limit} dB. Kết luận?',
                     opts), ids['pass' if ok else 'fail']), None)
    else:
        reading = C.CO_LIMIT + r.choice((-15, -8, -3, 4, 9))
        ok = reading <= C.CO_LIMIT
        opts, ids = sk.lettered(r, [('pass', 'Đạt: ghi số đo vào phiếu'), ('fail', 'Không đạt: kiểm bộ xúc tác, chỉnh lại map không tải rồi đo lại'),
                                    ('w0', 'Gần đạt thì cho qua'), ('w1', 'Không đạt: dặn khách đừng chạy giờ cao điểm')])
        add((sk.step('an_toan', 'do', 'choice', 'Đo khí thải',
                     f'Máy đo khí thải ở không tải: CO {_num(reading)}%. Giới hạn sổ tay: {_num(C.CO_LIMIT)}%. Kết luận?', opts), ids['pass' if ok else 'fail']), None)
    # 8. the test drive, 9. the spec card
    add(sk.scenario(r, 'chay_thu', 'lai', 'Chạy thử ở đường thử', r.choice(C.TEST_DRIVE)))
    short = ', '.join(C.SHORT[m] for m in build)
    big = (a0 * 6 // 5 + 9) // 10 * 10
    opts, ids = sk.lettered(r, [('right', f'{a0} mã lực (trước độ {b0}) · đã độ: {short}'),
                                ('w0', f'{big} mã lực · đã độ: {short}'),
                                ('w1', f'{a0} mã lực (trước độ {b0}) · máy zin, chưa độ gì')])
    add((sk.step('giao', 'the', 'choice', 'Dán thẻ thông số, giao xe',
                 f'Chọn thẻ thông số dán ở cửa xe {plate} cho khách. Đối chiếu với số dyno và bảng độ.', opts), ids['right']))
    key[LAW] = law
    tag = f'TP-{day:03d}{slot:02d}'
    net = G['net'] + 2 * len(demands) + level
    return dict(steps=steps, key=key, goal=goal, goal_name=G['name'], goal_emoji=G['emoji'], vehicle=name, kind=kind, color=color,
                plate=plate, tag=tag, npc=npc, budget=budget, build=build, cost=total, net=net, demands=len(demands), dyno=dyno,
                opening=f'{who} đưa chiếc {name.lower()} màu {color} vào xưởng: “{say}”')


def make_task(day: int, slot: int, serial: int) -> dict:
    tk = ticket(day, slot)
    needs = {k: v for k, v in tk.items() if k not in ('key', 'npc', 'opening')}
    return kit.base_task(ID, day, slot, serial, tk['npc'], f'{tk["vehicle"]} màu {tk["color"]}', tk['opening'],
                         gen=GEN, kind='ticket', needs=needs, _key=tk['key'], at=0, work={}, errors=[], wrong=0,
                         quality=100, paid=0, lines=[], stage='work')


def index_of(t: dict, step_id: str) -> int:
    """Where `step_id` sits on the ticket (len(steps) when absent)."""
    steps = t['needs']['steps']
    return next((i for i, st in enumerate(steps) if st['id'] == step_id), len(steps))


# ---------------------------------------------------------------- player jobs (🛎️ Phố dịch vụ, game/tuning_service.py)
def svc_job(order: str, service: str) -> tuple:
    """(steps, key) of a player's order: the same three steps for one order, always. Pure."""
    r = kit.rng(ID, 'svc', order, service)
    ctx = dict(goal=r.choice(('drag', 'deo')), kind='car', top=r.choice((6000, 6500, 7000)), build=['ecu'])
    safe = sk.picks(r, 'kh', 'an_toan', 'Kiểm an toàn trước khi giao', 'Đồ đã lắp xong. Kiểm những gì?', r.sample(C.SAFETY_GOOD, 3), r.sample(C.SAFETY_BAD, 2))
    if service == 'do_dong_co':
        pairs = (sk.ordered(r, 'kh', 'ecu', C.WORK_TITLE['ecu'], 'Nạp map cho xe của người chơi: bấm lần lượt từng việc.', C.STEPS['ecu']),
                 _mod_check(r, 'ecu', ctx), safe)
    elif service == 'do_khung_gam':
        pairs = (sk.ordered(r, 'kh', 'giam_xoc', C.WORK_TITLE['giam_xoc'], 'Thay phuộc cho xe của người chơi: bấm lần lượt từng việc.', C.STEPS['giam_xoc']),
                 _mod_check(r, 'giam_xoc', ctx), safe)
    else:
        pairs = (sk.picks(r, 'kh', 'kiem', 'Kiểm xe trước khi bảo dưỡng', 'Xe độ của người chơi vừa dắt vào. Kiểm những gì?',
                          r.sample(C.INSPECT_GOOD, 3), r.sample(C.INSPECT_BAD, 2)),
                 sk.ordered(r, 'kh', 'lop', C.WORK_TITLE['lop'], 'Thay lốp mòn: bấm lần lượt từng việc.', C.STEPS['lop']),
                 _mod_check(r, 'lop', ctx))
    return sk.pairs_to_steps(pairs)


def _svc(d: dict, p: dict) -> dict:
    return sk.svc_work(d, p, SERVICES, svc_job, '🔧 Làm xong! Bấm Giao để trả xe cho khách ở 🛎️ Phố dịch vụ.')


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, earned=0)


def initial() -> dict:
    return dict(intro=False, today=_today(0), closed_day=0, stats=dict(jobs=0, good=0, active_days=0, earned=0, svc=0),
                legal=dict(warn=0, fined=0), desk=kit.desk_initial(), svc=[], svc_ok=[])


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _quality(wrong: int) -> int:
    return sk.quality(wrong, C.WRONG_COST, C.QUALITY_FLOOR)


def _severity(step_id: str) -> int:
    """A redone brake, safety, legal or dyno step is a safety matter for the review."""
    head, _, tail = step_id.partition('.')
    return 2 if head in SAFETY or tail == 'phanh' else 1


def _net(t: dict) -> int:
    return max(6, t['needs']['net'] * t['quality'] // 100)


def has_cert(s: dict) -> bool:
    rec = ((s.get('journey') or {}).get('certificates') or {}).get(CERT_ID)
    return isinstance(rec, dict) and rec.get('earned_day') is not None


def parts_cost(s: dict, n: dict) -> int:
    """What the parts of this build cost the shop: the certificate's perk takes 2 xu off (never below 0)."""
    return max(0, n['cost'] - (2 if has_cert(s) else 0))


def illegal_pick(t: dict, step_id: str, value) -> bool:
    """Is this answer an illegal fit or a passed illegal reading (the ward warns the shop)?"""
    law = t['_key'].get(LAW) or {}
    if step_id not in law or sk.same(value, t['_key'][step_id]):
        return False
    bad = law[step_id]
    if bad is None:
        return True
    return bool(set(value if isinstance(value, list) else [value]) & set(bad))


def _warn(s: dict, c: dict, d: dict, t: dict, st: dict) -> str:
    """⚖️ The ward's warning: a small fine to the shop and a count; every WARN_EVERY-th brings the inspection team."""
    legal = d['legal']
    legal['warn'] += 1
    fine = min(C.LEGAL_FINE, max(0, c['money']))
    if fine:
        legal['fined'] += fine
        kit.money(s, c, -fine, f'Phường nhắc nhở: {st["title"].lower()}', t['id'], 'fine')
    if legal['warn'] % C.WARN_EVERY == 0:
        d['desk']['marks']['warned'] = c['day']
    tail = f' Xưởng bị phường nhắc nhở, nộp {fine} xu.' if fine else ' Xưởng bị phường nhắc nhở.'
    return ' ⚖️ Lắp hay cho qua như vậy là trái luật, khách ra đường sẽ bị phạt.' + tail


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('dx_intro', 'dx_step', 'dx_desk', 'dx_svc'), 'Thao tác ở xưởng độ không hợp lệ.')
    d = _data(c)
    if name == 'dx_intro':
        d['intro'] = True
        return dict(message='Anh Tư Pít-tông chỉ tấm bảng trên tường: “Nhanh mà phải dừng được. Đồ trái luật, xưởng này không lắp.”')
    desk = d['desk']
    if name == 'dx_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở xưởng cần quyết, quyết xong rồi làm tiếp nhé.')
    if name == 'dx_svc':
        return _svc(d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Nghe khách nói muốn độ gì trước đã.')
    steps = t['needs']['steps']
    st = steps[t['at']] if t['at'] < len(steps) else None
    illegal = bool(st) and p.get('step') == st['id'] and illegal_pick(t, st['id'], sk.value(st, p.get('value')))
    correct, message, finished = sk.work(t, p, _quality, 'Anh Tư', LINES, _severity)
    if illegal:
        message += _warn(s, c, d, t, st)
        t['lines'] = (t['lines'][:-1] + [message[:480]])[-LINES:]
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
    kit.complete(s, c, t, net + n['cost'], f'Giao {n["vehicle"].lower()} biển {n["plate"]}: {n["goal_name"].lower()}, chất lượng {t["quality"]}%.',
                 bonus_base=net)
    paid_parts = parts_cost(s, n)
    kit.money(s, c, -paid_parts, f'Phụ tùng độ: {n["goal_name"].lower()}', t['id'], 'materials')
    result = dict(message=f'Giao xe đúng phiếu {n["tag"]}. Thu {net + n["cost"]} xu: phụ tùng {n["cost"]} xu, công {net} xu.'
                          + (' 🎓 Đại lý bớt 2 xu phụ tùng nhờ chứng chỉ.' if paid_parts < n['cost'] else ''),
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
    lines = [f'Xưởng Tư Pít-tông giao {today["jobs"]} xe, {today["good"]} xe đạt từ 90%, công sau phụ tùng {today["earned"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, jobs=today['jobs'], clean=today['good'], earned=today['earned'])


def known_request(c: dict, t: dict) -> str:
    extra = ' Khách còn dặn thêm điều oái oăm, chốt với khách trước khi lắp nhé.' if t['needs']['demands'] else ''
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Nghe khách nói muốn độ xe để làm gì.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Xe đã giao; nhận xe tiếp theo.'


def feedback(c, t: dict) -> dict:
    steps = t['needs']['steps']
    n = len(t['errors'])
    law = t['_key'].get(LAW) or {}
    legal = sum(1 for e in t['errors'] if e in law)
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='legal', label='Đúng luật', score=max(1, 5 - 2 * legal), note='Không lắp đồ trái luật, số đo đúng giới hạn.'),
                          dict(key='safe', label='Xe an toàn, thẻ thật', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    """The answers stay on the server: the goal before it is named, the build before the sheet is settled, the dyno sheet
    before the car is on the dyno, and every step after the open one (its words would tell the build)."""
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
        return v
    n, at = v['needs'], t['at']
    if at <= index_of(t, 'nghe.muc_tieu'):
        for k in ('goal', 'goal_name', 'goal_emoji'):
            n.pop(k, None)
    if at <= index_of(t, 'bang.chon'):
        for k in ('build', 'cost'):
            n.pop(k, None)
    if at < index_of(t, 'dyno.doc'):
        n.pop('dyno', None)
    n['steps'] = [st if i <= at else dict(id=f'_{i}', type=st['type'], title='', evidence='') for i, st in enumerate(n['steps'])]
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
        goals=[dict(id=k, name=v['name'], emoji=v['emoji'], day=v['day']) for k, v in C.GOALS.items()],
        mods={k: dict(name=v['name'], emoji=v['emoji']) for k, v in C.MODS.items()},
        limits=dict(noise=C.NOISE_LIMIT, co=C.CO_LIMIT, afr=C.AFR_LIMIT),
        intro=dict(title='Một ngày ở xưởng độ Tư Pít-tông',
                   lead='Xưởng độ xe máy và ô tô. Nghe khách muốn chạy ở đâu, kiểm xe, lên bảng độ trong ngân sách bằng đồ đúng luật, '
                        'lắp từng món, chạy dyno, đo tiếng ồn, chạy thử rồi giao xe kèm thẻ thông số thật. Phụ tùng xưởng ứng, trừ một lần khi giao xe; '
                        'tiền công giảm theo chất lượng.',
                   work=[['📋', 'Bảng độ theo mục tiêu và ngân sách'], ['🔧', 'Lắp ECU, pô, turbo, lốp, phanh, phuộc'],
                         ['📈', 'Đọc biểu đồ dyno, đường AFR'], ['⚖️', 'Đo tiếng ồn, khí thải; không lắp đồ trái luật']],
                   meet=[['🔧', 'Anh Tư Pít-tông chủ xưởng'], ['🛞', 'Mi Lốp thợ phụ'], ['📈', 'Chị Kiều kỹ sư dyno']],
                   stars=[['🏁', 'Nhanh mà phải dừng được: tăng công suất đi cùng phanh'], ['🌀', 'Khách oái oăm: nói thật, đúng luật']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    sk.validate_slip(t, original, FIXED, _quality, _net, LINES, 'phiếu độ xe')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ xưởng độ sai.')
    kit.need(type(d['intro']) is bool, 'Sổ xưởng độ sai.')
    for field in ('today', 'stats', 'legal'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), 'Thống kê xưởng độ sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
    for field in ('today', 'stats'):
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số xe đạt sai.')
    kit.need(d['legal']['fined'] <= d['legal']['warn'] * C.LEGAL_FINE, 'Sổ nhắc nhở của xưởng sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], C.DESK)
    sk.svc_validate(d, SERVICES, svc_job)


SPEC = dict(
    id=ID, prefix=PREFIX, category='shop', people=PEOPLE,
    meta=dict(short='Độ xe', place=C.PLACE, tagline='Nhanh mà phải dừng được.', icon='wrench',
              color='#b8322a', light='#fde4df', weather='Mùi xăng thơm và cao su nóng trên băng thử', work='Phiếu độ xe', station='Băng thử dyno và cầu nâng',
              greeting='Nghe khách muốn chạy ở đâu, lên bảng độ trong ngân sách, lắp đồ đúng luật, chạy dyno rồi mới giao.',
              caption='Xe mạnh, phanh chắc, đúng luật', map_label='XƯỞNG ĐỘ TƯ PÍT-TÔNG'),
    staff=[('Mi Lốp', 'helper', 'Thợ phụ: thay lốp, xả gió phanh, ghi sổ dyno.', 72, 82),
           ('Bảo', 'engine', 'Thợ máy chính: lắp turbo, siết đúng lực, đo lại dyno.', 80, 90),
           ('Khánh', 'electric', 'Đi dây điện, đèn, đo dB pô trước khi giao xe.', 76, 92),
           ('Vy', 'wrap', 'Dán decal, đánh bóng, chụp ảnh xe trước và sau.', 84, 84)],
    roles={'helper': 'Thợ phụ', 'engine': 'Thợ máy – turbo', 'electric': 'Điện – đèn', 'wrap': 'Dán decal – đánh bóng'},
    tip=1, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    activity=('🔧', 'Sổ tay xưởng độ', [('Bảng độ', 'Theo ưu tiên, trong ngân sách'), ('Turbo', 'Phải có phanh đi cùng'),
                                      ('Pô', 'Có tiêu âm, đo dB'), ('Thẻ thông số', 'Đúng số dyno')],
              ['Nghe mục tiêu, kiểm xe', 'Lên bảng độ đúng luật', 'Lắp từng món, chạy dyno', 'Đo, chạy thử, giao thẻ thật']),
    stories=[('Tấm bảng trên tường', ('Anh Tư chỉ tấm bảng gỗ: “Nhanh mà phải dừng được.”', 'Bạn đọc bảng giá: không có dòng nào ghi pô thẳng.',
                                      'Anh Tư cười: “Xưởng này độ cho người ta về nhà an toàn, không độ cho công an viết biên bản.”'))],
    review_asides=['Xưởng nói thật số dyno, không thổi phồng.', 'Độ xong còn đo tiếng ồn đàng hoàng.', 'Khuyên mình làm phanh trước, tăng máy sau.'],
    situations=[],
    more_line='Thêm một chiếc xe vừa lên cầu nâng.', open_line='Anh Tư kéo cửa cuốn; băng thử dyno, cầu nâng và sổ tay xưởng đã sẵn.',
    guide='Nghe mục tiêu → kiểm xe → lên bảng độ theo ưu tiên, trong ngân sách, bỏ đồ trái luật → cộng tiền phụ tùng → chốt với khách điều oái oăm → '
          'lắp từng món theo sổ tay → đọc biểu đồ dyno → đo tiếng ồn hoặc khí thải → chạy thử ở đường thử → dán thẻ thông số thật. '
          'Sai thì làm lại bước đó, tiền công giảm theo chất lượng; chọn đồ trái luật thì xưởng bị nhắc nhở.',
)
