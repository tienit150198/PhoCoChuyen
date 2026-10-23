"""🍱 Căn tin trường Tiểu học Phố Mây: the school canteen counter (player #482 "bán căn tin trường học"; owner 22/10
"UI như kiểu của trà sữa, show hết ra người ta chọn như game bán hàng ấy, cho mở toàn bộ game nhé").

The whole counter is on screen at once (public/js/careers/canteen.js on counter_kit.js): four shelves (đồ ăn sáng, nước
uống, ăn vặt, cơm phần trưa) with their stock, the customer's bubble and the tray. A customer is one order
(game/careers/counterkit.py): tap the goods into the tray, then Giao. The day follows a school day by slot:
  sang     slots 0–3, the morning rush before the 7 o'clock bell: xôi, bánh mì, mì ly, cơm nắm and a drink;
  ra_choi  slots 4–7 (and the rest of day 1), the twenty minutes of recess: drinks and snacks, a group buying for friends;
  trua     slots 8–11 from day 2, the class teacher's lunch order: N trays of cơm, a main (or the vegetarian tofu),
           rau and canh. The day's food sample (🧪 Lưu mẫu, once a day) is kept before the first tray leaves.
A student pays from pocket money (`budget`), may have an allergy or a vegetarian day (`avoid`); the rush customers go
back to class at the bell (counterkit.ring). Prices are the board the school approved: fixed, never tuned.

Open to every player from the start (journey.LATE_UNLOCKS 1); like every late career it joins `unlocked` only once
worked, so a save rolled back to a release without it still loads (scripts/strip_new_careers.py).
"""
from __future__ import annotations

from . import counterkit as ck
from . import canteen_content as C
from . import kit

ID = 'canteen'
CERT_ID = 'canteen_basics'
PREFIX = 'ct_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', 'kind', 'phase')
ACTIONS = ('ct_intro', 'ct_add', 'ct_remove', 'ct_clear', 'ct_serve', 'ct_sample', 'ct_desk')
PHYSICAL = ('ct_add', 'ct_remove', 'ct_clear', 'ct_serve', 'ct_sample')
FREE = ('ct_intro',)
NO_TICK = ('ct_intro', 'ct_desk', 'ct_remove', 'ct_clear')
SHOP = ck.Shop(ID, PREFIX, C.GOODS, C.GROUPS, 'Cô Sáu Mận', C.WRONG_COST, C.QUALITY_FLOOR)
ITEMS = ck.inventory_items(SHOP)
STUDENT_WORDS = 'Học trò'
SAMPLE_GOODS = tuple(k for k, g in C.GOODS.items() if g['group'] == 'trua')


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, C.MODS)


def phase(day: int, slot: int) -> str:
    if slot >= 8 and day >= C.MILESTONES[0]:
        return 'trua'
    return 'ra_choi' if slot >= 4 else 'sang'


def _who(npc: int) -> str:
    return C.PEOPLE[npc][0]


def _n(q: int, say: str) -> str:
    return f'{C.NUM.get(q, q)} {say}'


def _list(parts: list) -> str:
    return parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' với ' + parts[-1]


# ---------------------------------------------------------------- the orders (pure: day, slot)
def _sang(day: int, r, level: int, mod: str) -> tuple:
    bell = C.BELL['sang'] - (2 if mod == 'monday' else 0)
    roll = r.random()
    drink = 'ct_nuoc_suoi' if mod == 'exam' else r.choice(C.DRINKS)
    if level >= 2 and roll < 0.18:   # Bé Bông: no milk
        npc = 5
        food = r.choice(('ct_xoi', 'ct_com_nam', 'ct_mi_ly'))
        lines = [ck.line(1, (food,), 1, C.SAY[food]), ck.line(2, C.DRINKS, 1, 'món uống không có sữa')]
        say = f'Cô bán cho con {_n(1, C.SAY[food])} với một món uống gì cũng được. Mà con bị dị ứng sữa nha cô, mẹ dặn kỹ lắm.'
        return npc, ck.needs('allergy', lines, avoid=('milk',), bell=bell), say
    if level >= 1 and roll < 0.30:   # Minh: a vegetarian day
        npc = 6
        lines = [ck.line(1, C.FOODS, 1, 'món ăn sáng chay'), ck.line(2, (drink,), 1, C.SAY[drink])]
        say = f'Hôm nay rằm, nhà con ăn chay. Cô bán cho con một món ăn sáng chay với {_n(1, C.SAY[drink])} nha.'
        return npc, ck.needs('chay', lines, avoid=('meat', 'egg'), bell=bell), say
    if level >= 1 and roll < 0.55:   # pocket money: the cheapest pair, or one a little dearer
        npc = r.choice((2, 3, 4))
        lines = [ck.line(1, C.FOODS, 1, 'món ăn sáng'), ck.line(2, C.DRINKS, 1, 'món uống')]
        budget = ck.cheapest(SHOP, lines) + r.choice((0, 1, 2, 3))
        say = f'Con có {budget} xu à. Cô bán cho con một món ăn sáng với một món uống, sao cho đủ tiền nha cô.'
        return npc, ck.needs('budget', lines, budget=budget, bell=bell), say
    npc = r.choice((2, 3, 4))
    foods = r.sample(C.FOODS, 2 if r.random() < 0.3 else 1)
    lines, parts = [], []
    for i, k in enumerate(foods):
        q = 2 if len(foods) == 1 and r.random() < 0.3 else 1
        lines.append(ck.line(i + 1, (k,), q, C.SAY[k]))
        parts.append(_n(q, C.SAY[k]))
    if r.random() < 0.6:
        lines.append(ck.line(len(lines) + 1, (drink,), 1, C.SAY[drink]))
        parts.append(_n(1, C.SAY[drink]))
    extra = ' Con mua cho em con một phần nữa.' if any(ln['qty'] == 2 for ln in lines) else ''
    return npc, ck.needs('order', lines, bell=bell), f'Cô ơi, bán cho con {_list(parts)}.{extra}'


def _ra_choi(day: int, r, level: int, mod: str) -> tuple:
    bell = C.BELL['ra_choi']
    roll = r.random()
    if level >= 2 and roll < 0.2:   # a group with a friend allergic to peanuts
        n = r.choice((2, 3))
        friend = r.choice(('bạn Khoa', 'bạn Lan', 'bạn Tú'))
        lines = [ck.line(1, C.SNACKS, n, 'món ăn vặt không có đậu phộng')]
        say = f'Cô bán cho nhóm con {_n(n, "món ăn vặt")}, gì cũng được, mà {friend} dị ứng đậu phộng nha cô.'
        return 3, ck.needs('allergy', lines, avoid=('peanut',), bell=bell), say
    if level >= 2 and roll < 0.32:   # Bé Bông at recess
        lines = [ck.line(1, C.SNACKS, 1, 'món ăn vặt không có sữa'), ck.line(2, ('ct_nuoc_suoi', 'ct_tra_tac'), 1, 'chai nước hoặc ly trà tắc')]
        say = 'Con lấy một món ăn vặt gì cũng được với một chai nước suối hay ly trà tắc cũng được. Con dị ứng sữa nha cô.'
        return 5, ck.needs('allergy', lines, avoid=('milk',), bell=bell), say
    if level >= 1 and roll < 0.55:
        npc = r.choice((2, 4, 6))
        lines = [ck.line(1, C.SNACKS, 1, 'món ăn vặt'), ck.line(2, C.DRINKS, 1, 'món uống')]
        budget = ck.cheapest(SHOP, lines) + r.choice((0, 1, 2, 3))
        say = f'Con còn {budget} xu. Cô bán cho con một món ăn vặt với một món uống cho vừa tiền nha.'
        return npc, ck.needs('budget', lines, budget=budget, bell=bell), say
    if roll < 0.8:   # Tí buys for the đá cầu group
        d, sn = r.choice(C.DRINKS[:3]), r.choice(C.SNACKS)
        qd, qs = r.randint(2, 4), r.randint(1, 3)
        lines = [ck.line(1, (d,), qd, C.SAY[d]), ck.line(2, (sn,), qs, C.SAY[sn])]
        say = f'Cô ơi lẹ lẹ giùm con: {_n(qd, C.SAY[d])} với {_n(qs, C.SAY[sn])}, cho cả nhóm đá cầu!'
        return 3, ck.needs('group', lines, bell=bell), say
    npc = r.choice((2, 4, 6))
    sn, d = r.choice(C.SNACKS), r.choice(C.DRINKS)
    lines = [ck.line(1, (sn,), 1, C.SAY[sn]), ck.line(2, (d,), 1, C.SAY[d])]
    return npc, ck.needs('order', lines, bell=bell), f'Cô bán cho con {_n(1, C.SAY[sn])} với {_n(1, C.SAY[d])} nha.'


def _trua(day: int, r, level: int, mod: str) -> tuple:
    npc = 8 if mod == 'sports' and r.random() < 0.6 else 7
    n = r.randint(3, 5) + (1 if level >= 3 else 0)
    chay = r.choice((0, 0, 1)) if n >= 4 else 0
    meat = n - chay
    cls = r.choice(C.CLASSES) if npc == 7 else 'đội bóng'
    lines = [ck.line(1, ('ct_com',), n, 'phần cơm trắng')]
    if level >= 1 and r.random() < 0.35:   # one child cannot eat fish: the mains are named
        fish = r.randint(0, max(0, meat - 1))
        if meat - fish:
            lines.append(ck.line(2, ('ct_ga_kho',), meat - fish, 'phần gà kho'))
        if fish:
            lines.append(ck.line(3, ('ct_ca_chien',), fish, 'phần cá chiên'))
        mains = (f'{meat - fish} phần gà kho' + (f', {fish} phần cá chiên' if fish else '') +
                 ' (có bạn dị ứng cá, đừng lộn nha)')
    else:
        lines.append(ck.line(2, C.MAINS, meat, 'phần món mặn (gà hoặc cá)'))
        mains = f'{meat} phần, gà hay cá cũng được'
    if chay:
        lines.append(ck.line(4, ('ct_dau_hu',), chay, 'phần đậu hũ chay'))
    lines += [ck.line(5, ('ct_rau',), n, 'phần rau'), ck.line(6, ('ct_canh',), n, 'chén canh')]
    who = 'Lớp ' + cls if npc == 7 else 'Đội bóng'
    veg = f', {chay} bạn ăn chay' if chay else ''
    say = (f'{who} hôm nay có {n} bạn ở lại ăn trưa{veg}. Em chia giùm {"cô" if npc == 7 else "thầy"} {n} phần: '
           f'mỗi phần có cơm, rau, canh; món mặn {mains}{"; bạn ăn chay lấy đậu hũ" if chay else ""}.')
    return npc, ck.needs('trua', lines, sample=True, trays=n, cls=cls), say


def order(day: int, slot: int) -> tuple:
    """(phase, npc, needs, words) of (day, slot). Pure."""
    r = kit.rng(ID, day, slot)
    level = sum(day >= x for x in C.MILESTONES)
    ph = phase(day, slot)
    npc, needs, say = {'sang': _sang, 'ra_choi': _ra_choi, 'trua': _trua}[ph](day, r, level, mod_of(day)['id'])
    return ph, npc, needs, say


TITLES = {'sang': '{who} mua đồ ăn sáng', 'ra_choi': '{who} mua giờ ra chơi', 'trua': '{who} đặt cơm trưa'}


def make_task(day: int, slot: int, serial: int) -> dict:
    ph, npc, needs, say = order(day, slot)
    who = _who(npc)
    return kit.base_task(ID, day, slot, serial, npc, TITLES[ph].format(who=who), f'{who}: “{say}”', gen=GEN, kind=needs['kind'],
                         phase=ph, needs=needs, tray={}, stage='work', errors=[], wrong=0, quality=100, paid=0, cogs=0, lines=[])


def daily_task_count(day: int) -> int:
    """The morning queue at the gate: four students before the bell (the engine's default is three)."""
    return 4


# ---------------------------------------------------------------- data
def initial() -> dict:
    return ck.initial(sampled_day=0)


def _data(c: dict) -> dict:
    return ck.book(c)


def _who_of(t: dict) -> str:
    return _who(int(t['npc'].rsplit('_', 1)[1]) - 1)


def _bell(s: dict, c: dict, d: dict) -> tuple:
    """(the words, the ids of the students the bell called back to class)."""
    gone = ck.ring(s, c, SHOP, d, _who_of, 'Trống đánh, chưa mua kịp đã phải chạy vào lớp.')
    if not gone:
        return '', ()
    return f'🥁 Trống trường đã đánh: {", ".join(w for _, w in gone)} chạy vội vào lớp, chưa kịp mua.', tuple(i for i, _ in gone)


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ACTIONS, 'Thao tác ở căn tin không hợp lệ.')
    d = _data(c)
    if name == 'ct_intro':
        d['intro'] = True
        return dict(message='Cô Sáu đưa đôi găng tay: “Rửa tay, hỏi dị ứng, bán đúng giá. Học trò tin mình lắm đó con.”')
    desk = d['desk']
    if name == 'ct_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở căn tin cần quyết, quyết xong rồi bán tiếp nhé.')
    rang, gone = _bell(s, c, d)
    if (p.get('task') or c.get('active_task')) in gone and name != 'ct_sample':   # the student this tap was for has just left
        return _done(s, c, d, dict(message=rang), '')
    if name == 'ct_sample':
        kit.need(d['sampled_day'] != c['day'], 'Hôm nay đã lưu mẫu rồi.')
        d['sampled_day'] = c['day']
        result = dict(message='🧪 Đã lưu mẫu từng món trưa nay vào hộp có nhãn, cất tủ mát 24 giờ. Giờ chia cơm được rồi.')
        return _done(s, c, d, result, rang)
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc căn tin.')
    kit.need(t['status'] not in ck.DONE, 'Bạn này đã về lớp rồi.')
    kit.need(t['known'], 'Hỏi khách cần gì trước đã.')
    if name == 'ct_add':
        result = ck.add(SHOP, c, t, p)
    elif name == 'ct_remove':
        result = ck.remove(SHOP, t, p)
    elif name == 'ct_clear':
        result = ck.clear(t)
    else:
        result = _serve(s, c, d, t)
    return _done(s, c, d, result, rang)


def _serve(s: dict, c: dict, d: dict, t: dict) -> dict:
    who = _who_of(t)
    ok, words = ck.serve(SHOP, s, c, t, who, sampled=d['sampled_day'] == c['day'])
    if not ok:
        return dict(message=words, correct=False)
    n = t['needs']
    what = f'{n["trays"]} phần cơm trưa' if t['phase'] == 'trua' else 'đồ ăn' if t['phase'] == 'sang' else 'đồ ăn vặt'
    ck.finish(s, c, d, t, f'Mua {what} ở căn tin, đúng món, đúng giá.')
    if t['phase'] == 'trua':
        words += ck.cert_tip(s, c, t, CERT_ID, '🎓 Chia cơm trưa có chứng chỉ')
    good = t['quality'] >= 90
    return dict(message=words, correct=good, celebrate=good)


def _done(s: dict, c: dict, d: dict, result: dict, rang: str) -> dict:
    if rang:
        result['message'] = f'{rang} {result.get("message", "")}'.strip()
        result.pop('quiet', None)
    ck.after(s, c, SHOP, d, result, C.DESK, mod_of(c['day'])['id'])
    return result


def on_task(s: dict, c: dict, t: dict) -> None:
    """A new customer comes to the counter: anyone the bell has already called back to class leaves first."""
    if c.get('open'):
        _bell(s, c, _data(c))


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    kit.desk_start(s, c, ID, d['desk'], C.DESK, mod_of(c['day'])['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    return ck.close(s, c, SHOP, _data(c), C.DESK, 'Căn tin')


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    extra = ''
    if n.get('budget') is not None:
        extra = f' Bé có {n["budget"]} xu: tổng khay không được quá số đó.'
    if n.get('sample'):
        extra = ' Nhớ lưu mẫu thức ăn trưa (🧪) trước khi phát phần đầu tiên.'
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Hỏi bạn ấy muốn mua gì.'
    n = t['needs']
    if n.get('sample') and _data(c)['sampled_day'] != c['day']:
        return 'Bấm 🧪 Lưu mẫu trước, rồi chia đủ cơm, món mặn, rau, canh cho từng phần.'
    if n.get('avoid'):
        return 'Bạn này không ăn được ' + ', '.join(ck.TAG_WORDS[x] for x in n['avoid']) + ': chọn món không có thứ đó.'
    if n.get('budget') is not None:
        return f'Cộng giá từng món: tổng khay không quá {n["budget"]} xu.'
    return 'Chạm từng món trên kệ cho đủ số lượng, rồi bấm Giao.'


LABELS = dict(order='Đúng món, đủ phần', safe='An toàn thực phẩm', safe_note='Hỏi dị ứng, lưu mẫu trước khi chia cơm.',
              money='Vừa tiền tiêu vặt')


def feedback(c, t: dict) -> dict:
    return ck.feedback(t, LABELS)


def public_task(t: dict, c: dict | None = None) -> dict:
    return ck.public_task(t, SHOP, c)


def public_data(c: dict) -> dict:
    d = ck.public_book(c, SHOP, C.DESK, C.MASTER, C.EXPERT)
    d['sampled'] = d['sampled_day'] == c['day']
    m = mod_of(max(1, c['day']))
    d['mod'] = dict(id=m['id'], emoji=m['emoji'], label=m['label'], hint=m['hint'])
    d['bells'] = {t['id']: ck.bell_left(c, t) for t in c['tasks'] if t.get('career') == ID and t['status'] not in ck.DONE and t['known']}
    return d


def content() -> dict:
    return dict(rules=C.RULES, shelves=ck.goods_view(SHOP), tags=ck.TAG_WORDS, intro=C.INTRO, sample=True,
                phases=dict(sang='🍙 Trước giờ vào lớp', ra_choi='🔔 Giờ ra chơi', trua='🍱 Cơm trưa bán trú'))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    ck.validate_task(SHOP, t, 'đơn căn tin')


def validate_data(c: dict) -> None:
    ck.validate_book(c, initial(), C.DESK, 'căn tin')
    kit.integer(kit.data(c)['sampled_day'], 0, 10**9)


SPEC = dict(
    id=ID, prefix=PREFIX, category='shop', people=PEOPLE,
    meta=dict(short='Căn tin trường', place=C.PLACE, tagline='Kịp trống vào lớp, đúng món, đúng giá.', icon='com',
              color='#e07a2e', light='#fff1e2', weather='Tiếng trống trường, tiếng học trò ríu rít trước quầy',
              work='Đơn căn tin', station='Quầy căn tin: kệ đồ ăn sáng, tủ nước, khay cơm phần',
              greeting='Rửa tay, đeo găng, hỏi dị ứng. Giao kịp trước khi trống đánh, bán đúng giá niêm yết.',
              caption='Học trò no bụng, phụ huynh yên tâm', map_label='CĂN TIN TRƯỜNG'),
    staff=[('Cô Sáu Mận', 'cook', 'Bếp chính: nấu cơm trưa, lưu mẫu thức ăn, dặn dò học trò.', 70, 80),
           ('Chị Bảy', 'prep', 'Nhặt rau, rửa ba nước, thớt sống thớt chín để riêng.', 80, 88),
           ('Cô Hiền', 'serve', 'Chia phần đều tay, nhớ em nào dị ứng tôm.', 84, 86),
           ('Chú Năm', 'wash', 'Rửa khay, tráng nước sôi, lau sàn trước giờ ra chơi.', 78, 90)],
    roles={'cook': 'Bếp căn tin', 'prep': 'Sơ chế', 'serve': 'Chia cơm – thu tiền', 'wash': 'Rửa khay – vệ sinh'},
    tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    inventory=dict(items=ITEMS, capacity=80),   # inventory.LINE_MAX: every stocked shelf holds 80 (tests/test_stock_limits.py)
    prices={},   # the school's approved board: fixed list prices, never tuned
    activity=('🍱', 'Sổ tay căn tin', [('Trống vào lớp', '7:00'), ('Ra chơi', '20 phút'), ('Một phần cơm', 'cơm + mặn + rau + canh'),
                                     ('Lưu mẫu', '24 giờ, tủ mát')],
              ['Hỏi dị ứng trước khi đưa', 'Đúng giá niêm yết', 'Lưu mẫu trước khi chia cơm', 'Vừa tiền tiêu vặt của bé']),
    stories=[('Cái trống trường', ('Chú Tư Gác lau mặt trống: “Trống này đánh từ hồi cô Sáu còn là học trò.”',
                                   'Bạn nhìn đồng hồ: còn năm phút nữa là bảy giờ, hàng trước quầy vẫn dài.',
                                   'Cô Sáu cười: “Bày sẵn mấy món hay mua, bán nhanh mà vẫn hỏi dị ứng nghe con.”'))],
    review_asides=['Căn tin bán đúng giá, hỏi kỹ dị ứng của bé.', 'Cơm trưa đủ phần, có lưu mẫu đàng hoàng.',
                   'Học trò mua kịp trước giờ vào lớp.'],
    situations=[],
    more_line='Thêm một bạn nhỏ chạy tới quầy căn tin.',
    open_line='Cô Sáu mở cửa căn tin: xôi, bánh mì còn nóng, tủ nước đầy, học trò đã đứng chờ trước quầy.',
    guide='Hỏi bạn nhỏ cần gì → chạm từng món trên kệ vào khay → Giao. Sáng và giờ ra chơi phải kịp trước tiếng trống; '
          'dị ứng sữa, đậu phộng, ngày ăn chay thì chọn món phù hợp; tiền tiêu vặt có hạn thì cộng giá cho vừa. '
          'Trưa: 🧪 Lưu mẫu rồi chia đủ cơm, món mặn, rau, canh theo số bạn của lớp.',
)
