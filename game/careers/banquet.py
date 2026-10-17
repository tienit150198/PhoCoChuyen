"""Nhà hàng tiệc Hồng Mây: a salaried shift in a banquet restaurant, on one of two tracks chosen at the start of a shift.

🍳 Bếp. Everyone starts as Phụ bếp (probation): sơ chế, a simple salad, preparing the tools. After PROBATION good kitchen
shifts the player becomes Đầu bếp (check the delivery, cook, plate and garnish) and may pick either kitchen role, or the
hall, every shift. A kitchen shift opens with hygiene (rửa tay, sát khuẩn, mũ, bao tay, kiểm bếp) and closes with cleaning
and switching off every appliance; a ward food-safety inspection drops in on some days and checks the opening. Leaving
without the closing check risks a small kitchen fire that night: a bounded compensation from the wallet.

🎀 Sảnh sự kiện. A client's event (wedding, birthday, company party…): count the tables, pick the hall size, the concept,
the set menu and drinks, the decoration, test sound and light, walk the electrics, then handle an incident.

Every task step is graded on the server; a wrong step stays open to fix in place and lowers the quality (and so the small
bonus). Pay is the employment contract's salary at closing. A job's content is a pure function of (day, slot, role), like
the hotel's seasonal brief, so the stored task stays as made and a save validates on any date. Holiday rush days follow the
real Vietnam date (UTC+7): one more job, bonus ×1.5 and a bigger quality cost per slip.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
import math

from . import kit
from . import banquet_content as bc
from .. import consequences as cq

ID = 'banquet'
GEN = 1
PEOPLE = bc.PEOPLE
ROLES = tuple(bc.ROLES)
JOB_IDS = tuple(bc.JOBS)
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('bq_step', 'bq_shift')
FREE = ('bq_intro', 'bq_role')
NO_TICK = ('bq_intro', 'bq_role', 'bq_desk')
RUSH_IDS = ('none',) + tuple(bc.RUSH)
VN = timezone(timedelta(hours=7))
TYPES = ('choice', 'number', 'order', 'multi')
LINES = 24


# ---------------------------------------------------------------- rush days (pure, real Vietnam date)
def rush_of(d: date) -> str | None:
    """The holiday rush on the Vietnam calendar date `d`, or None."""
    for t in (bc.TET.get(d.year), bc.TET.get(d.year + 1)):
        if t and t - bc.TET_BEFORE <= d <= t + bc.TET_AFTER:
            return 'tet'
    return bc.RUSH_DATES.get((d.month, d.day))


def today_vn() -> date:
    return datetime.fromtimestamp(kit.now(), VN).date()


def rush_now() -> str:
    return rush_of(today_vn()) or 'none'


def rush_view(rid: str | None = None) -> dict | None:
    rid = rush_now() if rid is None else rid
    if rid not in bc.RUSH:
        return None
    label, emoji = bc.RUSH[rid]
    return dict(id=rid, label=label, emoji=emoji, bonus=bc.RUSH_BONUS, cost=bc.RUSH_WRONG_COST,
                note='Ngày lễ đông khách: thêm phiếu việc, thưởng ×1.5; sai một bước trừ chất lượng nhiều hơn.')


# ---------------------------------------------------------------- task building
def _opts(r, rows, shuffle=True):
    out = [dict(id=k, label=v) for k, v in rows]
    if shuffle:
        r.shuffle(out)
    return out


def _step(job, name, typ, title, evidence, options=None, unit=''):
    st = dict(id=f'{job}.{name}', type=typ, title=title, evidence=evidence)
    if options is not None:
        st['options'] = options
    if unit:
        st['unit'] = unit
    return st


def _pick(r, rows, n):
    return r.sample(list(rows), n)


def _prep(r, day, slot):
    ing = r.choice(bc.INGREDIENTS)
    iid, label, group, grams, dish = ing
    frozen = group != 'veg' and r.random() < 0.5
    portions = r.randint(3, 12) * 4
    clean = 'soak' if group == 'veg' else 'thaw' if frozen else 'trim' if group == 'meat' else 'ice'
    state = ('Hàng đông lạnh lấy từ tủ đông.' if frozen else 'Hàng tươi vừa nhận sáng nay.') if group != 'veg' else 'Rau vừa nhận sáng nay.'
    steps = [
        _step('prep', 'board', 'choice', 'Chọn thớt đúng màu', f'Sơ chế {label.lower()} cho món {dish}. {state}', _opts(r, bc.BOARDS)),
        _step('prep', 'clean', 'choice', 'Làm sạch, rã đông đúng cách', f'{label}: {state.lower()}', _opts(r, bc.CLEAN)),
        _step('prep', 'grams', 'number', 'Cân đủ lượng cần sơ chế', f'Ca tối có {portions} suất {dish}, mỗi suất cần {grams} g {label.lower()}.', unit='g'),
        _step('prep', 'store', 'choice', 'Cất vào tủ chờ nấu', 'Sơ chế xong, cất chờ ca nấu.', _opts(r, bc.STORE)),
    ]
    key = {'prep.board': bc.BOARD_OF[group], 'prep.clean': clean, 'prep.grams': portions * grams,
           'prep.store': 'top' if group == 'veg' else 'bottom'}
    brief = dict(ingredient=label, group=group, frozen=frozen, portions=portions, grams=grams, dish=dish, steps=steps)
    return brief, key, f'Sơ chế {label.lower()}', f'Chú Tâm giao: sơ chế {label.lower()} cho {portions} suất {dish}. Đúng thớt, đúng tủ.', 0


def _sauce(name):
    """'Sốt mayonnaise' -> 'sốt mayonnaise', 'Sữa chua' -> 'sốt sữa chua' (never 'sốt sốt')."""
    low = name.lower()
    return low if low.startswith('sốt') else 'sốt ' + low


def _salad(r, day, slot):
    sid, name, tops, sauce, grams = r.choice(bc.SALADS)
    notes = [n for n in bc.SALAD_NOTES if any(x in tops for x in n[2])]
    note = r.choice(notes) if notes and r.random() < 0.75 else None
    swap = r.random() < 0.3
    sauce_want = r.choice([s for s, _ in bc.SAUCES if s != sauce]) if swap else sauce
    sauce_name = dict(bc.SAUCES)
    plates = r.randint(2, 6)
    others = [k for k in bc.TOPPINGS if k not in tops]
    shown = list(tops) + _pick(r, others, 3)
    r.shuffle(shown)
    removed = set(note[2]) if note else set()
    card = f'Công thức {name}: ' + ', '.join(bc.TOPPINGS[x].lower() for x in tops) + '; ' + _sauce(sauce_name[sauce]) + '.'
    ask = (note[1] if note else 'Không có lưu ý riêng.') + (f' Khách xin đổi sang {sauce_name[sauce_want].lower()}.' if swap else '')
    steps = [
        _step('salad', 'wash', 'order', 'Sắp thứ tự sơ chế rau', 'Bấm các việc theo đúng thứ tự trong sổ bếp.', _opts(r, bc.SALAD_STEPS)),
        _step('salad', 'toppings', 'multi', 'Chọn nguyên liệu cho đĩa', f'{card} Phiếu bàn: {ask}',
              [dict(id=x, label=bc.TOPPINGS[x]) for x in shown]),
        _step('salad', 'sauce', 'choice', 'Chọn sốt', f'{card} Phiếu bàn: {ask}', _opts(r, bc.SAUCES)),
        _step('salad', 'grams', 'number', 'Cân rau trộn cho cả phiếu', f'Phiếu {plates} đĩa {name.lower()}, mỗi đĩa {grams} g.', unit='g'),
    ]
    key = {'salad.wash': [k for k, _ in bc.SALAD_STEPS], 'salad.toppings': sorted(x for x in tops if x not in removed),
           'salad.sauce': sauce_want, 'salad.grams': plates * grams}
    brief = dict(salad=name, card=card, ask=ask, plates=plates, steps=steps)
    return brief, key, f'{plates} đĩa {name.lower()}', f'Phiếu bàn vừa vào: {plates} đĩa {name.lower()}. {ask}', 0


def _tools(r, day, slot):
    a, b = _pick(r, bc.STATION, 2)
    need = sorted(set(a[2]) | set(b[2]))
    others = [k for k in bc.TOOLS if k not in need]
    shown = need + _pick(r, others, 3)
    r.shuffle(shown)
    dish = r.choice((a, b))
    n = r.randint(2, 8) * 5
    knife = r.choice(bc.KNIVES)
    steps = [
        _step('tools', 'tools', 'multi', 'Lấy đủ dụng cụ cho bảng ca', f'Bảng ca hôm nay: {a[1].lower()} và {b[1].lower()}. Chọn đủ dụng cụ cho cả hai món, không lấy thừa.',
              [dict(id=x, label=bc.TOOLS[x]) for x in shown]),
        _step('tools', 'vessels', 'number', f'Đếm {dish[3]} cho {dish[1].lower()}', f'{dish[1]}: {n} suất. Chuẩn bị đúng số suất cộng 10% dự phòng, làm tròn lên.', unit=dish[4]),
        _step('tools', 'knife', 'choice', 'Kiểm dao trước ca', knife[1], _opts(r, bc.KNIFE_ACTS)),
        _step('tools', 'wash', 'choice', 'Làm sạch dụng cụ trước khi dùng', 'Dụng cụ lấy từ kệ còn vương bụi và nước đọng.', _opts(r, bc.WASH)),
    ]
    key = {'tools.tools': need, 'tools.vessels': math.ceil(n * 11 / 10), 'tools.knife': knife[2], 'tools.wash': 'proper'}
    brief = dict(dishes=[a[1], b[1]], steps=steps)
    return brief, key, f'Dụng cụ cho {a[1].lower()} và {b[1].lower()}', 'Chú Tâm dặn: dụng cụ đủ, sạch, dao an toàn rồi mới vào ca.', 0


def _check(r, day, slot):
    rows = _pick(r, bc.DELIVERY, 5)
    bad_n = r.choice((1, 1, 2))
    bad = set(x[0] for x in _pick(r, rows, bad_n))
    items, kg = [], {}
    for iid, label, kind in rows:
        ok, faulty = bc.READINGS[kind]
        reading = r.choice(faulty if iid in bad else ok)
        kg[iid] = r.randint(2, 12)
        items.append(dict(id=iid, label=f'{label} · {kg[iid]} kg · {reading}', kind=kind))
    steps = [
        _step('check', 'reject', 'multi', 'Chọn hàng phải trả lại', 'Kiểm nhiệt độ, cảm quan, bao bì và hạn dùng từng món trên phiếu giao.',
              [dict(id=x['id'], label=x['label']) for x in items]),
        _step('check', 'kg', 'number', 'Ghi tổng kg thực nhận', 'Chỉ cộng các món nhận vào kho, không tính món trả lại.', unit='kg'),
        _step('check', 'record', 'choice', 'Xử lý hàng không đạt', 'Người giao hàng đang chờ ký phiếu.', _opts(r, bc.RECORD)),
        _step('check', 'putaway', 'choice', 'Cất hàng vào kho', 'Hàng nhận đã cân xong, xếp vào kho thế nào?', _opts(r, bc.PUTAWAY)),
    ]
    key = {'check.reject': sorted(bad), 'check.kg': sum(v for k, v in kg.items() if k not in bad), 'check.record': 'return', 'check.putaway': 'cold'}
    brief = dict(items=items, steps=steps)
    return brief, key, 'Kiểm lô hàng sáng', 'Xe hàng vừa tới cửa bếp. Kiểm kỹ từng món rồi mới ký nhận.', 0


def _cook(r, day, slot):
    did = sorted(bc.DISHES)[r.randrange(len(bc.DISHES))]
    name, order, done, wrongs, _, _ = bc.DISHES[did]
    tables, per, extra = r.randint(2, 8), r.choice((1, 2)), r.randint(0, 6)
    steps = [
        _step('cook', 'order', 'order', f'Làm {name.lower()} đúng thứ tự', 'Bấm từng công đoạn theo công thức của bếp.', _opts(r, order)),
        _step('cook', 'done', 'choice', 'Kiểm độ chín', f'{name}: dấu hiệu nào chắc chắn món đã đạt?',
              _opts(r, [('right', done), ('w1', wrongs[0]), ('w2', wrongs[1]), ('taste', bc.DONE_GENERIC)])),
        _step('cook', 'taste', 'choice', 'Nêm nếm', 'Nêm lần cuối trước khi tắt bếp.', _opts(r, bc.TASTE)),
        _step('cook', 'portions', 'number', 'Tính số phần phải nấu', f'Phiếu bếp: {tables} bàn tiệc, mỗi bàn {per} phần {name.lower()}, thêm {extra} phần gọi lẻ.', unit='phần'),
    ]
    key = {'cook.order': [k for k, _ in order], 'cook.done': 'right', 'cook.taste': 'spoon', 'cook.portions': tables * per + extra}
    brief = dict(dish=name, steps=steps)
    return brief, key, f'Nấu {name.lower()}', f'Phiếu bếp: {name.lower()} cho {tables} bàn tiệc. Đúng công thức, chín chắc, nêm sạch.', 0


def _plate(r, day, slot):
    did = sorted(bc.DISHES)[r.randrange(len(bc.DISHES))]
    name, _, _, _, vessel, garnish = bc.DISHES[did]
    notes = [n for n in bc.PLATE_NOTES if not n[2] or any(x in garnish for x in n[2])]
    note = r.choice(notes)
    others = [k for k in bc.GARNISH if k not in garnish]
    shown = list(garnish) + _pick(r, others, 3)
    r.shuffle(shown)
    vessels = [v for v in bc.VESSELS if v != vessel]
    wait = r.choice((5, 10, 20, 40, 90, 150))
    temp = r.choice((72, 66, 61)) if wait <= 20 and r.random() < 0.7 else r.choice((55, 48, 40)) if wait <= 120 else r.choice((38, 30))
    pas = 'discard' if wait > 120 else 'serve' if temp >= 60 else 'reheat'
    garn_card = f'Trang trí chuẩn của {name.lower()}: ' + ', '.join(bc.GARNISH[x].lower() for x in garnish) + '.'
    steps = [
        _step('plate', 'vessel', 'choice', 'Chọn dụng cụ bày món', f'{name} bày theo chuẩn của bếp.',
              _opts(r, [(vessel, bc.VESSELS[vessel])] + [(v, bc.VESSELS[v]) for v in r.sample(vessels, 3)])),
        _step('plate', 'garnish', 'multi', 'Trang trí món', f'{garn_card} Phiếu bàn: {note[1]}', [dict(id=x, label=bc.GARNISH[x]) for x in shown]),
        _step('plate', 'rim', 'choice', 'Hoàn thiện mép đĩa', 'Mép đĩa còn dính một vệt sốt.', _opts(r, bc.RIM)),
        _step('plate', 'pass', 'choice', 'Kiểm nhiệt trước khi ra món', f'Món đã nằm ở quầy ra món {wait} phút, nhiệt kế đo {temp}°C.', _opts(r, bc.PASS)),
    ]
    key = {'plate.vessel': vessel, 'plate.garnish': sorted(x for x in garnish if x not in note[2]), 'plate.rim': 'wipe', 'plate.pass': pas}
    brief = dict(dish=name, note=note[1], steps=steps)
    return brief, key, f'Ra món {name.lower()}', f'Món {name.lower()} chờ ở quầy ra món. Bày đúng chuẩn, trang trí đúng phiếu.', 0


def _event(r, day, slot):
    ev = bc.EVENT_ORDER[(day + slot) % len(bc.EVENT_ORDER)]
    ename, emoji, (lo, hi), reserve, concepts = bc.EVENTS[ev]
    client = r.choice(bc.CLIENTS[ev])
    guests = r.randint(lo // 5, hi // 5) * 5
    tables = math.ceil(guests / bc.SEATS) + reserve
    hall = next(h for h in bc.HALLS if h[2] >= tables)
    concept = r.choice(concepts)
    rest = [c for c in bc.CONCEPTS if c != concept]
    # Set menu: the dearest one that keeps the client's rule, within the budget per table.
    rule = r.choice([k for k in bc.MENU_RULES if k != 'none'] + ['none'])
    ok = sorted((m for m in bc.MENUS if bc.MENU_RULES[rule][1](m[4])), key=lambda m: m[2])
    target = r.choice(ok)
    higher = [m[2] for m in ok if m[2] > target[2]]
    budget = target[2] + r.randint(0, min(4, (min(higher) - target[2] - 1) if higher else 4))
    menu = max((m for m in ok if m[2] <= budget), key=lambda m: m[2])
    shown_menus = [menu] + r.sample([m for m in bc.MENUS if m is not menu], 3)
    r.shuffle(shown_menus)
    wish, drink = r.choice(bc.DRINK_WISHES[ev])
    fits = [d for d in bc.DECOR if ev in d[3] and (not d[4] or concept in d[4])]
    cats = {d[2] for d in fits}
    limits = ['none'] + (['pollen'] if 'fresh' in cats else []) + (['balloon'] if 'balloon' in cats else [])
    limit = r.choice(limits)
    good = [d for d in fits if d[2] != 'flame' and not (d[2] == 'fresh' and limit == 'pollen')
            and not (d[2] == 'silk' and limit != 'pollen') and not (d[2] == 'balloon' and limit == 'balloon')]
    others = [d for d in bc.DECOR if d not in fits]
    shown = fits + r.sample(others, 3)
    r.shuffle(shown)
    av = r.choice(bc.AV)
    obs = r.sample(bc.POWER, 5)
    if not any(o[2] for o in obs):
        obs[0] = r.choice([o for o in bc.POWER if o[2]])
    if all(o[2] for o in obs):
        obs[-1] = r.choice([o for o in bc.POWER if not o[2]])
    inc = r.choice(bc.INCIDENTS)
    hall_name = {h[0]: h[1] for h in bc.HALLS}
    said = f'{client}: “{ename} của nhà mình khoảng {guests} khách.”'
    steps = [
        _step('event', 'tables', 'number', 'Hỏi khách, tính số bàn', said + f' Nhà hàng xếp {bc.SEATS} khách một bàn, làm tròn lên'
              + ('; tiệc cưới thêm 2 bàn dự phòng.' if reserve else '.'), unit='bàn'),
        _step('event', 'hall', 'choice', 'Chọn phòng tiệc', 'Chọn phòng nhỏ nhất đủ số bàn: phòng càng lớn giá thuê càng cao.',
              _opts(r, [(h[0], f'{h[1]} · tối đa {h[2]} bàn · thuê {h[3]} xu') for h in bc.HALLS], shuffle=False)),
        _step('event', 'concept', 'choice', 'Hỏi chủ đề, chốt concept', f'{client}: “{bc.CONCEPTS[concept][1]}”',
              _opts(r, [(c, bc.CONCEPTS[c][0]) for c in [concept] + r.sample(rest, 3)])),
        _step('event', 'menu', 'choice', 'Chọn thực đơn', f'Ngân sách {budget} xu mỗi bàn. {bc.MENU_RULES[rule][0]} Nhà muốn tiệc đầy đặn nhất trong tầm tiền.',
              [dict(id=m[0], label=f'{m[1]} · {m[2]} xu/bàn · {m[3]}') for m in shown_menus]),
        _step('event', 'drinks', 'choice', 'Chọn đồ uống', f'{client}: “{wish}”', _opts(r, bc.DRINKS)),
        _step('event', 'decor', 'multi', 'Trang trí theo yêu cầu', f'{ename}, chủ đề {bc.CONCEPTS[concept][0].lower()}. {bc.DECOR_LIMITS[limit]} Chọn mọi món hợp dịp và hợp chủ đề.',
              [dict(id=d[0], label=d[1]) for d in shown]),
        _step('event', 'av', 'choice', 'Thử âm thanh, ánh sáng', f'Anh Khoa chạy thử: {av[1]}',
              _opts(r, [x for x in bc.AV_FIX if x[0] == av[2]] + r.sample([x for x in bc.AV_FIX if x[0] != av[2]], 3))),
        _step('event', 'power', 'multi', 'Đi một vòng kiểm điện', 'Chọn mọi chỗ phải xử lý trước giờ đón khách.', [dict(id=o[0], label=o[1]) for o in obs]),
        _step('event', 'incident', 'choice', 'Xử lý tình huống trong tiệc', inc[1],
              _opts(r, [('right', inc[2]), ('w1', inc[3][0]), ('w2', inc[3][1])])),
    ]
    key = {'event.tables': tables, 'event.hall': hall[0], 'event.concept': concept, 'event.menu': menu[0], 'event.drinks': drink,
           'event.decor': sorted(d[0] for d in good), 'event.av': av[2], 'event.power': sorted(o[0] for o in obs if o[2]),
           'event.incident': 'right'}
    brief = dict(event=ev, event_name=ename, emoji=emoji, client=client, guests=guests, concept_wish=bc.CONCEPTS[concept][1],
                 budget=budget, rule=bc.MENU_RULES[rule][0], drink_wish=wish, limit=bc.DECOR_LIMITS[limit],
                 halls=[dict(id=h[0], label=h[1], tables=h[2], rent=h[3]) for h in bc.HALLS], steps=steps)
    title = f'{ename} · {client}'
    return brief, key, title, f'Chị Loan chuyển phiếu: {ename.lower()} của {client}, khoảng {guests} khách. Hỏi kỹ, bày đúng ý, chạy tiệc suôn sẻ.', \
        bc.CLIENT_NPC[ev]


BUILD = dict(prep=_prep, salad=_salad, tools=_tools, check=_check, cook=_cook, plate=_plate, event=_event)


def job_of(day: int, slot: int, role: str) -> str:
    """The job of (day, slot) for `role`: each role rotates through its own jobs."""
    jobs = bc.ROLE_JOBS[role]
    return jobs[(day - 1 + slot) % len(jobs)]


def brief(day: int, slot: int, role: str) -> tuple[dict, list, dict, str, str, int, str]:
    """(brief with its steps, steps, answer key, title, opening, npc index, job) of (day, slot) for `role`. Pure."""
    job = job_of(day, slot, role)
    b, key, title, opening, npc = BUILD[job](kit.rng(ID, job, day, slot), day, slot)
    return b, b['steps'], key, title, opening, npc, job


def make_task(day: int, slot: int, serial: int) -> dict:
    """The stored slip is the same for every role (the role is chosen when the shift starts): its brief is built on read."""
    return kit.base_task(ID, day, slot, serial, bc.MANAGER, 'Phiếu việc nhà hàng tiệc', 'Chị Loan đưa phiếu việc của ca.',
                         gen=GEN, kind='shift', needs={}, _key={}, role='prep', rush='none',
                         at=0, work={}, errors=[], wrong=0, quality=100, paid=0, lines=[], stage='work')


def _slot(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def _role(t: dict) -> str:
    return t.get('role') if t.get('role') in ROLES else 'prep'


def _active(t: dict) -> tuple[dict, list, dict]:
    """(brief, steps, key) in force for the task's role."""
    b, steps, key, *_ = brief(t['day'], _slot(t), _role(t))
    return b, steps, key


def _job(t: dict) -> str:
    return job_of(t['day'], _slot(t), _role(t))


def _cost(t: dict) -> int:
    return bc.RUSH_WRONG_COST if t.get('rush') in bc.RUSH else bc.WRONG_COST


def _quality(wrong: int, cost: int = bc.WRONG_COST) -> int:
    return max(bc.QUALITY_FLOOR, 100 - cost * wrong)


def _quality_ok(t: dict, wrong: int) -> bool:
    """The quality of `wrong` slips: the current rule, or the one before 17/10 (a task slipped then and not since)."""
    old = bc.OLD_RUSH_WRONG_COST if t.get('rush') in bc.RUSH else bc.OLD_WRONG_COST
    return t.get('quality') in (_quality(wrong, _cost(t)), max(bc.OLD_FLOOR, 100 - old * wrong))


# The way to work out a number step, said on its first slip (17/10: "dễ chơi hơn"); the second slip shows the answer.
HOW = {
    'prep.grams': 'Lấy số suất nhân số gam mỗi suất.',
    'salad.grams': 'Lấy số đĩa nhân số gam mỗi đĩa.',
    'tools.vessels': 'Lấy số suất cộng thêm 10% rồi làm tròn lên (ví dụ 30 suất → 33).',
    'check.kg': 'Cộng số kg của các món nhận vào kho, bỏ các món đã chọn trả lại.',
    'cook.portions': 'Số bàn nhân số phần mỗi bàn, cộng thêm phần gọi lẻ.',
    'event.tables': f'Lấy số khách chia {bc.SEATS}, có lẻ thì làm tròn lên (ví dụ 155 khách → 16 bàn); tiệc cưới cộng thêm 2 bàn dự phòng.',
}


def _bonus(t: dict) -> int:
    bonus = max(3, round(bc.BONUS[_job(t)] * t['quality'] / 100))
    if t.get('rush') in bc.RUSH:
        bonus = round(bonus * bc.RUSH_BONUS)
    return bonus


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# ---------------------------------------------------------------- shift checklists (pure by day)
def shift_steps(day: int, part: str) -> tuple[list, dict]:
    """The kitchen's opening ('open') or closing ('close') checklist of `day`: (steps, key). Pure."""
    r = kit.rng(ID, 'shift', part, day)
    if part == 'open':
        steps = [_step('open', 'hygiene', 'order', 'Vệ sinh đầu ca', 'Bấm các việc theo đúng thứ tự dán ở cửa bếp. Đoàn kiểm tra có thể ghé bất chợt.',
                       _opts(r, bc.OPEN_STEPS))]
        return steps, {'open.hygiene': [k for k, _ in bc.OPEN_STEPS]}
    rows = []
    for aid, label, on, off in bc.APPLIANCES:
        state = r.choice((on, off))
        rows.append((aid, f'{label}: {state[0]}', state[1]))
    if not any(x[2] for x in rows):
        i = r.randrange(6)   # at least one appliance is left on tonight
        aid, label, on, _ = bc.APPLIANCES[i]
        rows[i] = (aid, f'{label}: {on[0]}', True)
    steps = [_step('close', 'clean', 'order', 'Dọn bếp cuối ca', 'Bấm các việc dọn theo đúng thứ tự trong sổ bếp.', _opts(r, bc.CLOSE_ORDER)),
             _step('close', 'power', 'multi', 'Tắt thiết bị điện, khóa gas', 'Chọn mọi thiết bị phải tắt trước khi về. Tủ mát và tủ đông luôn để chạy.',
                   [dict(id=a, label=lbl) for a, lbl, _ in rows])]
    return steps, {'close.clean': [k for k, _ in bc.CLOSE_ORDER], 'close.power': sorted(a for a, _, need in rows if need)}


def inspection_day(day: int) -> bool:
    return day >= 2 and kit.rng(ID, 'inspect', day).random() < bc.INSPECT_CHANCE


def fire_fine(c: dict) -> int:
    """The compensation a kitchen fire costs (before the wallet cap): FIRE_PCT of the contract salary, FIRE_MIN..FIRE_CAP."""
    salary = (c.get('job') or {}).get('salary') if isinstance(c.get('job'), dict) else None
    salary = salary if type(salary) is int and salary > 0 else 52
    return max(bc.FIRE_MIN, min(bc.FIRE_CAP, round(salary * bc.FIRE_PCT / 100)))


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, bonus=0, counted=0, kitchen=0, kjobs=0, prep_good=0,
                open_at=0, close_at=0, slips=0, insp=0, fire=0)


def initial() -> dict:
    return dict(intro=False, role='prep', promoted=False, today=_today(0), last_active_day=0, last_prep_day=0,
                stats=dict(jobs=0, good=0, active_days=0, bonus=0, rush=0, prep_days=0, insp_pass=0, insp_fail=0,
                           fires=0, fined=0, roles={k: 0 for k in ROLES}),
                desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _open_done(today: dict) -> bool:
    return today['open_at'] >= len(shift_steps(today['day'], 'open')[0])


def _close_done(today: dict) -> bool:
    return today['close_at'] >= len(shift_steps(today['day'], 'close')[0])


# ---------------------------------------------------------------- actions
def _value(st: dict, value):
    typ = st['type']
    if typ == 'choice':
        return kit.one_of(value, [o['id'] for o in st['options']])
    if typ == 'number':
        return kit.integer(value, 0, 100000)
    ids = [o['id'] for o in st['options']]
    got = kit.id_list(value, ids, len(ids))
    if typ == 'order':
        kit.need(len(got) == len(ids), 'Xếp đủ mọi việc theo thứ tự nhé.')
        return list(got)
    return sorted(got)


def _restamp(c: dict, role: str) -> int:
    """Today's unread slips follow the role just chosen; a slip already read keeps its own."""
    n = 0
    for t in c['tasks']:
        if t.get('career') == ID and t.get('status') == 'new' and not t.get('known') and t.get('at') == 0 and t.get('role') != role:
            t['role'] = role
            n += 1
    return n


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('bq_intro', 'bq_role', 'bq_step', 'bq_shift', 'bq_desk'), 'Thao tác nhà hàng không hợp lệ.')
    d = _data(c)
    if name == 'bq_intro':
        d['intro'] = True
        return dict(message='Chị Loan đưa tạp dề: chọn vào bếp hay ra sảnh cho ca này rồi bắt đầu nhé!')
    if name == 'bq_role':
        role = kit.one_of(p.get('role'), ROLES, 'Vị trí không hợp lệ.')
        kit.need(role != 'chef' or d['promoted'], f'Làm Phụ bếp đủ {bc.PROBATION} ca bếp đạt rồi mới lên Đầu bếp nhé.')
        d['role'] = role
        n = _restamp(c, role)
        label = bc.ROLES[role][0]
        return dict(message=f'Ca này bạn làm {label.lower()}.' + (f' {n} phiếu chưa đọc chuyển theo vị trí mới.' if n and c.get('open') else ''))
    desk = d['desk']
    if name == 'bq_desk':
        return kit.desk_choose(s, c, ID, desk, bc.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện cần quyết ở nhà hàng, quyết xong rồi làm tiếp nhé.')
    if name == 'bq_shift':
        return _shift(s, c, d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Đọc phiếu việc trước khi làm nhé.')
    _, steps, key = _active(t)
    kit.need(t['at'] < len(steps), 'Việc này đã xong.')
    kitchen = _role(t) in bc.KITCHEN
    today = d['today']
    kit.need(not (kitchen and _close_done(today)), 'Bếp đã dọn và tắt điện cho ca này. Việc bếp còn lại để ca sau làm tiếp nhé.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    value = _value(st, p.get('value'))
    kit.start_work(t)
    if kitchen:
        today['kitchen'] = 1
    if not _same(value, key[st['id']]):
        if st['id'] not in t['errors']:
            t['errors'].append(st['id'])
            cq.slip(t, st['id'], 1, 'Phải làm lại: ' + st['title'])
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = _quality(t['wrong'], _cost(t))
        again = 'Tính lại cho kỹ nhé.' if st['type'] == 'number' else 'Đọc lại phiếu và sổ bếp rồi làm lại bước này.'
        who = 'Chị Loan' if _role(t) == 'hall' else 'Chú Tâm'
        message = f'Chưa đúng: {st["title"].lower()}. {kit.step_help(t, st, key[st["id"]], HOW.get(st["id"], ""), again, who)}'
        t['lines'] = (t['lines'] + [message[:480]])[-LINES:]
        result = dict(message=message, correct=False)
        _after(s, c, d, result)
        return result
    t['work'][st['id']] = value
    t['at'] += 1
    t['lines'] = (t['lines'] + [f'✓ {st["title"]}.'])[-LINES:]
    if t['at'] < len(steps):
        result = dict(message='Đúng rồi. Tiếp: ' + steps[t['at']]['title'].lower() + '.', correct=True)
        _after(s, c, d, result)
        return result
    bonus = _bonus(t)
    t['paid'] = bonus
    t['stage'] = 'done'
    good = t['quality'] >= 90
    role = _role(t)
    for bucket in (today, d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['bonus'] += bonus
    if good:
        d['stats']['roles'][role] += 1
        if role == 'prep':
            today['prep_good'] = 1
    if t.get('rush') in bc.RUSH:
        d['stats']['rush'] += 1
    job = bc.JOBS[_job(t)]
    kit.complete(s, c, t, bonus, f'Xong việc {job[0].lower()}, chất lượng {t["quality"]}%.')
    extra = ' Thưởng ngày lễ ×1.5.' if t.get('rush') in bc.RUSH else ''
    result = dict(message=f'Xong: {job[0].lower()}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.{extra}', correct=good, celebrate=good)
    if kitchen:
        today['kjobs'] += 1
        _inspect(s, c, d, t, result)
    _after(s, c, d, result)
    return result


def _shift(s: dict, c: dict, d: dict, p: dict) -> dict:
    """One step of the kitchen's opening or closing checklist."""
    today = d['today']
    part = kit.one_of(p.get('part'), ('open', 'close'), 'Chọn việc đầu ca hay cuối ca nhé.')
    steps, key = shift_steps(today['day'], part)
    field = part + '_at'
    at = today[field]
    kit.need(at < len(steps), 'Việc đầu ca đã xong.' if part == 'open' else 'Bếp đã dọn và tắt điện xong.')
    if part == 'close':
        busy = [t for t in c['tasks'] if t.get('career') == ID and t['status'] not in ('completed', 'referred', 'cancelled')
                and t.get('at', 0) > 0 and _role(t) in bc.KITCHEN]
        kit.need(not busy, 'Còn món đang làm dở, xong món rồi mới dọn bếp nhé.')
    st = steps[at]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở nhé.')
    value = _value(st, p.get('value'))
    today['kitchen'] = 1
    if not _same(value, key[st['id']]):
        today['slips'] = min(today['slips'] + 1, 999)
        return dict(message=f'Chưa đúng: {st["title"].lower()}. Xem lại sổ bếp rồi làm lại nhé.', correct=False)
    today[field] = at + 1
    if today[field] < len(steps):
        return dict(message='Đúng rồi. Tiếp: ' + steps[today[field]]['title'].lower() + '.', correct=True)
    if part == 'open':
        return dict(message='🧼 Tay sạch, bao tay, mũ, bếp đã kiểm. Vào ca thôi!', correct=True)
    return dict(message='🔌 Bếp sạch, gas đã khóa, thiết bị đã tắt. Yên tâm về nhé!', correct=True, celebrate=True)


def _inspect(s: dict, c: dict, d: dict, t: dict, result: dict) -> None:
    """🔎 On an inspection day the ward food-safety team arrives after the first finished kitchen job."""
    today = d['today']
    if today['insp'] or today['kjobs'] != 1 or not inspection_day(c['day']):
        return
    ok = _open_done(today)
    today['insp'] = 1 if ok else 2
    npc = kit.npc_id(ID, bc.INSPECTOR)
    if ok:
        d['stats']['insp_pass'] += 1
        c['xp'] += 6
        line = '🔎 Đoàn kiểm tra vệ sinh an toàn thực phẩm ghé bếp: tay đã sát khuẩn, đeo bao tay, đội mũ, bếp gọn. Đạt!'
        kit.log(s, c, 'surprise', line, npc, t['id'])
    else:
        d['stats']['insp_fail'] += 1
        line = '🔎 Đoàn kiểm tra vệ sinh an toàn thực phẩm ghé bếp: chưa sát khuẩn tay, chưa đeo bao tay. Bị lập biên bản nhắc nhở.'
        kit.log(s, c, 'surprise', line, npc, t['id'])
        kit.review(s, c, npc, 2, 'Nhân viên bếp chưa sát khuẩn tay, chưa đeo bao tay khi chế biến. Đã nhắc nhở.', t['id'])
    result['message'] = f'{result.get("message", "")} {line}'.strip()
    result['inspection'] = 'pass' if ok else 'fail'


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, bc.DESK, None)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(bc.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_task(s: dict, c: dict, t: dict) -> None:
    """A new slip takes the role chosen for the shift and today's rush (decided once, by the real Vietnam date)."""
    if t.get('career') == ID and t.get('status') == 'new' and t.get('at') == 0:
        d = _data(c)
        t['role'] = d['role'] if d['role'] in ROLES and (d['role'] != 'chef' or d['promoted']) else 'prep'
        t['rush'] = rush_now()


def _extra_job(s: dict, c: dict) -> None:
    """A rush day opens with one more job, within the engine's own limits."""
    e = kit.eng()
    try:
        from ..promotion import managing
        if managing(s, c, ID):
            return
    except Exception:  # noqa: BLE001 - a manager-shift check never blocks the day
        pass
    active = sum(t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks'])
    slot = e._next_slot(c)
    if active >= e.MORE_ACTIVE or slot >= e.MORE_DAY:
        return
    t = make_task(c['day'], slot, c['turn'])
    c['tasks'].append(t)
    on_task(s, c, t)
    if not c.get('active_task'):
        c['active_task'] = t['id']


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    rush = rush_now()
    if rush != 'none' and c.get('open'):
        _extra_job(s, c)
    kit.desk_start(s, c, ID, d['desk'], bc.DESK, None, c['life'].get('mode') == 'festival' or rush != 'none')


def _fire(s: dict, c: dict, d: dict) -> str | None:
    """🔥 Kitchen work today and no closing check: a fire on FIRE_CHANCE of such nights; the compensation leaves the wallet."""
    today = d['today']
    if not today['kitchen'] or _close_done(today) or today['fire']:
        return None
    seed = int((s.get('journey') or {}).get('seed') or 0) if isinstance(s.get('journey'), dict) else 0
    if kit.rng(ID, 'fire', seed, c['day']).random() >= bc.FIRE_CHANCE:
        return '⚠️ Ca bếp chưa tắt thiết bị điện, may mà đêm nay không sao. Lần sau nhớ kiểm cuối ca nhé.'
    fine = fire_fine(c)
    j = s.get('journey') if isinstance(s.get('journey'), dict) else None
    if j and j.get('story'):
        paid = max(0, min(fine, int(j['wallet'])))
        if paid:
            from .. import journey as jr
            jr._wallet(j, -paid, 'life', '🔥 Đền bù cháy bếp ở Nhà hàng tiệc Hồng Mây')
    else:
        paid = max(0, min(fine, int(c['money'])))
        if paid:
            kit.money(s, c, -paid, 'Đền bù cháy bếp', f'fire-{c["day"]}', 'event_cost')
    today['fire'] = max(1, paid)
    d['stats']['fires'] += 1
    d['stats']['fined'] += paid
    kit.review(s, c, kit.npc_id(ID, 0), 2, 'Cuối ca bếp quên tắt thiết bị điện, đêm qua chập cháy một góc bếp.', f'fire-{c["day"]}')
    return (f'🔥 Đêm qua bếp chập cháy vì cuối ca chưa tắt thiết bị điện. Không ai bị thương; tiền đền bù {paid} xu đã trừ vào ví.'
            if paid else '🔥 Đêm qua bếp chập cháy vì cuối ca chưa tắt thiết bị điện. Không ai bị thương; ví đang trống nên chưa trừ đồng nào.')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], bc.DESK)
    lines = [f'Hồng Mây: {today["jobs"]} việc xong, {today["good"]} việc đạt từ 90%. Thưởng chất lượng: {today["bonus"]} xu.']
    if today['good'] and not today['counted'] and d['last_active_day'] < c['day']:
        d['stats']['active_days'] += 1
        today['counted'] = 1
        d['last_active_day'] = c['day']
    if today['kitchen']:
        lines.append(('🧼 Đầu ca đã sát khuẩn, đeo bao tay.' if _open_done(today) else '🧼 Ca bếp chưa làm vệ sinh đầu ca.')
                     + (' 🔌 Cuối ca đã dọn bếp, tắt điện.' if _close_done(today) else ''))
    fire = _fire(s, c, d)
    if fire:
        lines.append(fire)
    # 🥕 Probation: a good Phụ bếp shift counts once a day (hygiene, a good prep job, the closing check, no warning).
    if (today['prep_good'] and _open_done(today) and _close_done(today) and today['insp'] != 2
            and d['last_prep_day'] < c['day'] and not d['promoted']):
        d['stats']['prep_days'] += 1
        d['last_prep_day'] = c['day']
        left = bc.PROBATION - d['stats']['prep_days']
        if left <= 0:
            d['promoted'] = True
            c['xp'] += 10
            lines.append('👨‍🍳 Hết thử việc! Chú Tâm trao mũ đầu bếp: từ ca sau bạn có thể làm Đầu bếp, hoặc vẫn Phụ bếp, hoặc ra sảnh.')
        else:
            lines.append(f'🥕 Một ca phụ bếp đạt. Còn {left} ca nữa là lên Đầu bếp.')
    if note:
        lines.append(note)
    return dict(lines=lines, note='Lương ca do hợp đồng chi trả. Ngày có việc đạt từ 90% mới ghi vào hành trình nghề.')


def known_request(c: dict, t: dict) -> str:
    b, _, _, title, opening, _, job = brief(t['day'], _slot(t), _role(t))
    j = bc.JOBS[job]
    return f'{j[1]} {j[0]}: {opening}'


def hint(c: dict, t: dict) -> str:
    if not t.get('known'):
        return 'Đọc phiếu việc để biết việc của ca và yêu cầu của khách.'
    _, steps, _ = _active(t)
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Việc đã xong; nhận việc tiếp theo.'


def feedback(c: dict, t: dict) -> dict:
    _, steps, _ = _active(t)
    n = len(t['errors'])
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='care', label='Chất lượng phục vụ', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    b, _, _, title, opening, npc, job = brief(t['day'], _slot(t), _role(t))
    v['title'] = title
    v['opening'] = opening
    v['needs'] = deepcopy(b) if t['known'] else None
    j = bc.JOBS[job]
    r = bc.ROLES[_role(t)]
    v['job'] = dict(id=job, label=j[0], emoji=j[1])
    v['role_info'] = dict(id=_role(t), label=r[0], emoji=r[1], kitchen=_role(t) in bc.KITCHEN)
    v['client_npc'] = kit.npc_id(ID, npc)
    v['rush_info'] = rush_view(t.get('rush', 'none'))
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    stats = d['stats']
    roles = sum(1 for k in ROLES if stats['roles'].get(k, 0) > 0)
    milestones = [dict(m, achieved=stats['good'] >= m['jobs'] and stats['active_days'] >= m['days'] and roles >= m['roles']) for m in bc.MILESTONES]
    d['progress'] = dict(earned=[m['id'] for m in milestones if m['achieved']], milestones=milestones, roles=roles,
                         probation=bc.PROBATION, prep_days=min(stats['prep_days'], bc.PROBATION))
    d['desk'] = kit.desk_public(d['desk'], bc.DESK, ID, c)
    d['rush'] = rush_view()
    today = d['today'] if d['today']['day'] == c['day'] else _today(c['day'])
    shift = {}
    for part in ('open', 'close'):
        steps, _ = shift_steps(c['day'], part)
        at = today[part + '_at']
        shift[part] = dict(at=at, total=len(steps), done=at >= len(steps), step=deepcopy(steps[at]) if at < len(steps) else None)
    shift.update(kitchen=bool(today['kitchen']), insp=('', 'pass', 'fail')[today['insp']], fire=today['fire'])
    d['shift'] = shift
    d['fire_fine'] = fire_fine(c)
    return d


def content() -> dict:
    return dict(
        notebook=bc.NOTEBOOK,
        roles=[dict(id=k, label=v[0], emoji=v[1], work=v[2], kitchen=k in bc.KITCHEN) for k, v in bc.ROLES.items()],
        tracks=[dict(id=k, label=v[0], emoji=v[1]) for k, v in bc.TRACKS.items()],
        jobs=[dict(id=k, label=v[0], emoji=v[1], role=v[2]) for k, v in bc.JOBS.items()],
        rush=[dict(id=k, label=v[0], emoji=v[1]) for k, v in bc.RUSH.items()],
        probation=bc.PROBATION, fire=dict(chance=round(bc.FIRE_CHANCE * 100), pct=bc.FIRE_PCT, min=bc.FIRE_MIN, cap=bc.FIRE_CAP),
        intro=dict(title='Một ca ở Nhà hàng tiệc Hồng Mây',
                   lead='Nhà hàng tiệc cưới, sinh nhật, liên hoan bên chợ. Đầu ca bạn chọn vào bếp hay ra sảnh sự kiện. '
                        f'Vào bếp bắt đầu là phụ bếp thử việc; đủ {bc.PROBATION} ca bếp đạt thì lên đầu bếp. Lương ca theo hợp đồng, thưởng chất lượng nhỏ; ngày lễ đông khách, thưởng ×1.5.',
                   work=[['🔪', 'Phụ bếp: sơ chế, salad, chuẩn bị dụng cụ'], ['👨‍🍳', 'Đầu bếp: kiểm nguyên liệu, nấu, trang trí món'],
                         ['🎀', 'Sảnh: số bàn, phòng, chủ đề, thực đơn, trang trí, âm thanh, điện, sự cố']],
                   meet=[['👨‍🍳', 'Chú Tâm bếp trưởng'], ['🙂', 'Chị Loan quản lý nhà hàng'], ['🎛️', 'Anh Khoa âm thanh ánh sáng']],
                   stars=[['🧼', 'Đầu ca sát khuẩn tay, đeo bao tay'],
                          ['🔌', f'Cuối ca tắt hết thiết bị điện: quên là có thể cháy bếp, đền {bc.FIRE_PCT}% lương ca (tối đa {bc.FIRE_CAP} xu) từ ví']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    for k in FIXED:
        kit.need(_same(t.get(k), original.get(k)), 'Dữ kiện phiếu nhà hàng bị thay đổi: ' + k)
    kit.need(t.get('role') in ROLES, 'Vị trí của phiếu nhà hàng không hợp lệ.')
    kit.need(t.get('rush') in RUSH_IDS, 'Ngày lễ của phiếu không hợp lệ.')
    _, steps, key = _active(t)
    ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), 'Tiến trình phiếu nhà hàng sai.')
    kit.need(at == 0 or t['known'], 'Chưa đọc phiếu việc.')
    work = t.get('work')
    kit.need(isinstance(work, dict) and set(work) == set(ids[:at]), 'Các bước đã làm không liên tục.')
    kit.need(all(_same(work[sid], key[sid]) for sid in ids[:at]), 'Kết quả bước nhà hàng sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) for e in errors), 'Nhật ký lỗi nhà hàng sai.')
    kit.need(len(errors) == len(set(errors)) and set(errors) <= set(ids[:min(at + 1, len(ids))]), 'Nhật ký lỗi nhà hàng sai.')
    wrong = kit.integer(t.get('wrong'), 0, 100000)
    kit.need(len(errors) <= wrong <= t.get('mistakes', 0) and (wrong == 0) == (not errors), 'Số lần làm lại sai.')
    kit.need(_quality_ok(t, wrong), 'Điểm chất lượng nhà hàng không khớp.')
    kit.need(type(t.get('paid')) is int and t['paid'] == (_bonus(t) if at == len(steps) else 0), 'Tiền thưởng nhà hàng không khớp.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= LINES and all(isinstance(x, str) and len(x) < 500 for x in t['lines']),
             'Nhật ký nhà hàng sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') == 'completed'), 'Phiếu nhà hàng chưa xong mà đã hoàn tất.')
    kit.need(at == 0 or t.get('status') != 'new', 'Phiếu nhà hàng sai trạng thái.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ nhà hàng sai.')
    kit.need(type(d['intro']) is bool and type(d['promoted']) is bool, 'Sổ nhà hàng sai.')
    kit.need(d['role'] in ROLES and (d['role'] != 'chef' or d['promoted']), 'Vị trí trong ca sai.')
    kit.integer(d['last_active_day'], 0, 10**7)
    kit.integer(d['last_prep_day'], 0, 10**7)
    today = d['today']
    kit.need(isinstance(today, dict) and set(today) == set(base['today']), 'Số liệu nhà hàng sai.')
    for v in today.values():
        kit.integer(v, 0, 10**9)
    for k in ('counted', 'kitchen', 'prep_good'):
        kit.integer(today[k], 0, 1)
    kit.integer(today['insp'], 0, 2)
    kit.integer(today['fire'], 0, bc.FIRE_CAP)
    kit.integer(today['slips'], 0, 999)
    kit.integer(today['open_at'], 0, len(shift_steps(today['day'], 'open')[0]))
    kit.integer(today['close_at'], 0, len(shift_steps(today['day'], 'close')[0]))
    kit.need(today['good'] <= today['jobs'] and today['kjobs'] <= today['jobs'] and today['prep_good'] <= today['good'], 'Số việc đạt chuẩn sai.')
    st = d['stats']
    kit.need(isinstance(st, dict) and set(st) == set(base['stats']), 'Số liệu nhà hàng sai.')
    for k, v in st.items():
        if k != 'roles':
            kit.integer(v, 0, 10**9)
    kit.need(isinstance(st['roles'], dict) and set(st['roles']) == set(ROLES), 'Số liệu vị trí nhà hàng sai.')
    for v in st['roles'].values():
        kit.integer(v, 0, 10**9)
    kit.need(st['good'] <= st['jobs'] and sum(st['roles'].values()) == st['good'] and st['rush'] <= st['jobs']
             and st['active_days'] <= st['good'] and st['prep_days'] <= st['roles']['prep'], 'Tiến trình nghề nhà hàng sai.')
    kit.need(st['fined'] <= st['fires'] * bc.FIRE_CAP, 'Tiền đền bù nhà hàng sai.')
    kit.need(d['promoted'] == (st['prep_days'] >= bc.PROBATION), 'Thử việc phụ bếp sai.')
    kit.need(all(t.get('role') != 'chef' or d['promoted'] for t in c.get('tasks', []) if t.get('career') == ID), 'Phiếu đầu bếp khi chưa hết thử việc.')
    kit.desk_validate(d['desk'], bc.DESK)


SPEC = dict(
    id=ID, prefix='bq_', category='service', people=PEOPLE,
    meta=dict(short='Nhà hàng tiệc', place='Nhà hàng tiệc Hồng Mây', tagline='Bếp sạch, món chuẩn, tiệc trọn vẹn.', icon='cake',
              color='#b5473a', light='#fbebe6', weather='Mùi nước dùng thơm cả dãy phố', work='Phiếu việc', station='Bếp tiệc & sảnh sự kiện',
              greeting='Chị Loan treo bảng phân ca: chọn vào bếp hay ra sảnh. Bếp thì sát khuẩn đầu ca, tắt điện cuối ca.',
              caption='Một bếp tiệc, bốn phòng sự kiện', map_label='NHÀ HÀNG TIỆC HỒNG MÂY'),
    staff=[('Chú Tâm', 'kitchen', 'Bếp trưởng, dạy phụ bếp từ cách cầm dao.', 82, 90), ('Chị Loan', 'hall', 'Quản lý nhà hàng, nhớ sơ đồ bàn trăm đám cưới.', 86, 88)],
    roles={'kitchen': 'Bếp', 'hall': 'Sảnh sự kiện'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('🍲', 'Một ca ở Hồng Mây', [('Phụ bếp', 'Đúng thớt, đúng tủ'), ('Đầu bếp', 'Chín chắc, nêm sạch'), ('Sảnh', 'Đúng ý khách'),
                                        ('Cuối ca', 'Tắt hết điện')],
              ['Chọn bếp hay sảnh', 'Sát khuẩn đầu ca', 'Làm từng bước theo phiếu', 'Dọn bếp, tắt điện cuối ca']),
    stories=[('Chiếc mũ đầu bếp treo cửa', ('Chiếc mũ trắng của chú Tâm treo ở cửa bếp, mép đã sờn.', 'Bạn đội mũ trùm tóc, rửa tay, sát khuẩn rồi mới bước qua vạch.',
                                             'Chú Tâm gật đầu: “Món ngon bắt đầu từ đôi tay sạch.”'))],
    review_asides=['Món ra nóng, bày đẹp.', 'Sảnh trang trí đúng ý nhà mình.', 'Âm thanh rõ, tiệc chạy đúng giờ.'], situations=[],
    more_line='Chị Loan vừa giao thêm một phiếu việc.', open_line='Chị Loan đã mở nhà hàng; bảng phân ca, sổ bếp và sơ đồ sảnh treo cạnh cửa bếp.',
    guide='Đầu ca chọn Bếp (Phụ bếp, sau thử việc là Đầu bếp) hay Sảnh sự kiện. Bếp: sát khuẩn tay, đeo bao tay đầu ca; dọn bếp, tắt điện cuối ca. '
          'Làm từng bước theo phiếu; sai bước thì sửa ngay, thưởng giảm theo chất lượng. Ngày lễ đông khách, thưởng ×1.5.',
    employment=dict(postings=[dict(id='banquet-hongmay', org='Nhà hàng tiệc Hồng Mây', kind='company', title='Nhân viên nhà hàng tiệc (bếp hoặc sảnh)',
                                   salary=(52, 66), probation_days=3, wants=['careful', 'teamwork', 'patience'],
                                   perks=['Chú Tâm kèm những ca bếp đầu', 'Thưởng chất lượng nhỏ, ngày lễ ×1.5', 'Lương ca theo hợp đồng'],
                                   culture='Tay sạch mới vào bếp, khách dặn gì làm nấy, về thì tắt hết điện.',
                                   questions=['mistake', 'conflict'], reference=False)], questions={}),
)
