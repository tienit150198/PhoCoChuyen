"""✏️ Tiệm văn phòng phẩm Bút Mây: the stationery shop across from the school gate (player #483 "tiệm văn phòng phẩm";
owner 22/10 "UI như kiểu của trà sữa, show hết ra người ta chọn như game bán hàng ấy, cho mở toàn bộ game nhé").

The whole shop is on screen at once (public/js/careers/stationery.js on counter_kit.js): notebooks, pens, school tools,
bags and the service board (bọc vở, dán nhãn, photo) with their stock, the customer's bubble and the basket. A
customer is one order (game/careers/counterkit.py): tap the goods into the basket, then Giao. The kinds:
  le      a walk-in: one to three things named outright;
  budget  a student with pocket money: a notebook and a pen that fit it;
  list    a parent reading the class list (from day 2): "vở" is the class's notebook (lớp 1–5 ô li, lớp 6+ kẻ ngang),
          from day 4 often covered and labelled too (one sheet of giấy bọc, one nhãn per notebook);
  boc     notebooks brought from home to cover and label (from day 4);
  photo   a teacher's revision sheets: so many sets of so many pages, counted in lượt of 10 pages (one xấp A4 each).
Prices are the cover prices and the shop's posted service board: fixed, never tuned.

Open to every player from the start (journey.LATE_UNLOCKS 1); like every late career it joins `unlocked` only once
worked, so a save rolled back to a release without it still loads (scripts/strip_new_careers.py).
"""
from __future__ import annotations

from . import counterkit as ck
from . import kit
from . import stationery_content as C

ID = 'stationery'
CERT_ID = 'stationery_basics'
PREFIX = 'vp_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', 'kind')
ACTIONS = ('vp_intro', 'vp_add', 'vp_remove', 'vp_clear', 'vp_serve', 'vp_desk')
PHYSICAL = ('vp_add', 'vp_remove', 'vp_clear', 'vp_serve')
FREE = ('vp_intro',)
NO_TICK = ('vp_intro', 'vp_desk', 'vp_remove', 'vp_clear')
WORDS = dict(
    budget='{who}: “Con chỉ có {budget} xu thôi à.” Giỏ đang {bill} xu.',
    empty='Giỏ còn trống: chạm món trên kệ để lấy cho khách.',
    served='Giao đủ cho {who}. Thu {bill} xu.',
)
SHOP = ck.Shop(ID, PREFIX, C.GOODS, C.GROUPS, 'Chú Hai Bút', C.WRONG_COST, C.QUALITY_FLOOR, WORDS)
ITEMS = ck.inventory_items(SHOP)


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, C.MODS)


def notebook(grade: int) -> str:
    """The notebook a grade writes in: vở ô li for lớp 1–5, vở kẻ ngang from lớp 6."""
    return 'vp_vo_oli' if grade <= 5 else 'vp_vo_ke'


def _who(npc: int) -> str:
    return C.PEOPLE[npc][0]


def _n(q: int, say: str) -> str:
    return f'{C.NUM.get(q, q)} {say}'


def _list(parts: list) -> str:
    return parts[0] if len(parts) == 1 else ', '.join(parts[:-1]) + ' với ' + parts[-1]


# ---------------------------------------------------------------- the orders (pure: day, slot)
def _le(r, level: int) -> tuple:
    npc = r.choice((4, 5, 7))
    picks = r.sample(C.WALK_IN, r.randint(1, 3 if level else 2))
    lines, parts = [], []
    for i, k in enumerate(picks):
        q = r.randint(1, 3) if C.GOODS[k]['price'] <= 5 else 1
        lines.append(ck.line(i + 1, (k,), q, C.SAY[k]))
        parts.append(_n(q, C.SAY[k]))
    who = 'con' if npc in C.STUDENTS else 'anh'
    return npc, ck.needs('le', lines), f'Bán cho {who} {_list(parts)} nha.'


def _budget(r, level: int) -> tuple:
    npc = r.choice(C.STUDENTS)
    lines = [ck.line(1, C.NOTEBOOKS, 1, 'quyển vở'), ck.line(2, C.PENS, 1, 'cây bút')]
    budget = ck.cheapest(SHOP, lines) + r.choice((0, 1, 2, 3, 5))
    return npc, ck.needs('budget', lines, budget=budget), f'Con có {budget} xu. Chú bán cho con một quyển vở với một cây bút, vừa đủ tiền nha.'


def _class_list(r, level: int, mod: str) -> tuple:
    npc = r.choice(C.PARENTS)
    grade = 1 if npc == 1 else r.randint(2, 5) if npc == 6 else r.randint(6, 9)
    vo = notebook(grade)
    lines, parts = [], []
    n_vo = 0
    for i, (k, (lo, hi)) in enumerate(C.LISTS[grade]):
        q = r.randint(lo, hi)
        if k == 'vo':
            n_vo = q
            lines.append(ck.line(i + 1, (vo,), q, f'{C.SAY[vo]} (lớp {grade})'))
            parts.append(_n(q, 'quyển vở'))
        else:
            lines.append(ck.line(i + 1, (k,), q, C.SAY[k]))
            parts.append(_n(q, C.SAY[k]))
    cover = level >= 2 and r.random() < (0.6 if mod == 'school_year' else 0.35)
    extra = ''
    if cover:
        lines += [ck.line(8, ('vp_boc',), n_vo, 'quyển cần bọc'), ck.line(9, ('vp_dan_nhan',), n_vo, 'quyển cần dán nhãn')]
        extra = ' Bọc với dán nhãn ghi tên hết số vở giùm luôn nha.'
    who = {1: 'Con chị', 6: 'Cháu bà', 2: 'Con anh'}[npc]
    say = f'{who} vào lớp {grade}. Danh sách cô giáo phát: {_list(parts)}.{extra}'
    return npc, ck.needs('list', lines, grade=grade, cover=cover), say


def _boc(r, level: int) -> tuple:
    npc = r.choice(C.PARENTS)
    n = r.randint(4, 10)
    label = r.random() < 0.7
    lines = [ck.line(1, ('vp_boc',), n, 'quyển cần bọc')]
    if label:
        lines.append(ck.line(2, ('vp_dan_nhan',), n, 'quyển cần dán nhãn'))
    what = 'bọc với dán nhãn ghi tên' if label else 'bọc'
    return npc, ck.needs('boc', lines), f'Nhà có sẵn {_n(n, "quyển vở")} rồi, nhờ tiệm {what} giùm cho bé đi học.'


def _photo(r, level: int) -> tuple:
    npc = C.TEACHER if r.random() < 0.7 else C.OFFICE
    pages = r.choice((10, 20, 30) if level >= 1 else (10, 20))
    sets = r.randint(2, max(2, min(10, 20 // (pages // 10))))
    units = sets * pages // 10
    lines = [ck.line(1, ('vp_photo',), units, 'lượt photo 10 trang')]
    what = 'đề cương ôn tập' if npc == C.TEACHER else 'hồ sơ'
    say = f'Photo giùm {"cô" if npc == C.TEACHER else "anh"} {sets} bộ {what}, mỗi bộ {pages} trang nha.'
    return npc, ck.needs('photo', lines, sets=sets, pages=pages), say


def order(day: int, slot: int) -> tuple:
    """(npc, needs, words) of (day, slot). Pure."""
    r = kit.rng(ID, day, slot)
    level = sum(day >= x for x in C.MILESTONES)
    mod = mod_of(day)['id']
    roll = r.random()
    lists = 0.45 if mod == 'school_year' else 0.25
    photos = 0.30 if mod == 'exams' else 0.15
    if level >= 1 and roll < lists:
        return _class_list(r, level, mod)
    roll -= lists if level >= 1 else 0
    if roll < photos:
        return _photo(r, level)
    roll -= photos
    if level >= 2 and roll < 0.12:
        return _boc(r, level)
    if level >= 1 and roll < 0.32:
        return _budget(r, level)
    return _le(r, level)


TITLES = {'le': '{who} mua đồ dùng', 'budget': '{who} mua vở, bút', 'list': '{who} mua đồ theo danh sách lớp',
          'boc': '{who} nhờ bọc vở', 'photo': '{who} nhờ photo'}


def make_task(day: int, slot: int, serial: int) -> dict:
    npc, needs, say = order(day, slot)
    who = _who(npc)
    return kit.base_task(ID, day, slot, serial, npc, TITLES[needs['kind']].format(who=who), f'{who}: “{say}”', gen=GEN,
                         kind=needs['kind'], needs=needs, tray={}, stage='work', errors=[], wrong=0, quality=100, paid=0, cogs=0, lines=[])


# ---------------------------------------------------------------- data
def initial() -> dict:
    return ck.initial()


def _data(c: dict) -> dict:
    return ck.book(c)


def _who_of(t: dict) -> str:
    return _who(int(t['npc'].rsplit('_', 1)[1]) - 1)


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ACTIONS, 'Thao tác ở tiệm văn phòng phẩm không hợp lệ.')
    d = _data(c)
    if name == 'vp_intro':
        d['intro'] = True
        return dict(message='Chú Hai đưa cây bút chì gọt sẵn: “Nghe kỹ khách cần gì, đếm lại trước mặt khách. Vậy là giữ được mối.”')
    desk = d['desk']
    if name == 'vp_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở tiệm cần quyết, quyết xong rồi bán tiếp nhé.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm văn phòng phẩm.')
    kit.need(t['known'], 'Hỏi khách cần gì trước đã.')
    if name == 'vp_add':
        result = ck.add(SHOP, c, t, p)
    elif name == 'vp_remove':
        result = ck.remove(SHOP, t, p)
    elif name == 'vp_clear':
        result = ck.clear(t)
    else:
        result = _serve(s, c, d, t)
    ck.after(s, c, SHOP, d, result, C.DESK, mod_of(c['day'])['id'])
    return result


NARRATIVE = {'le': 'Mua đồ dùng học tập, đủ món, đúng giá.', 'budget': 'Mua vở, bút vừa tiền mang theo.',
             'list': 'Mua đủ đồ theo danh sách lớp, đúng loại vở.', 'boc': 'Bọc vở, dán nhãn ghi tên đủ số quyển.',
             'photo': 'Photo đủ bộ, đủ trang.'}


def _serve(s: dict, c: dict, d: dict, t: dict) -> dict:
    ok, words = ck.serve(SHOP, s, c, t, _who_of(t))
    if not ok:
        return dict(message=words, correct=False)
    ck.finish(s, c, d, t, NARRATIVE[t['kind']])
    if t['kind'] == 'list':
        words += ck.cert_tip(s, c, t, CERT_ID, '🎓 Soạn danh sách lớp có chứng chỉ')
    good = t['quality'] >= 90
    return dict(message=words, correct=good, celebrate=good)


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    kit.desk_start(s, c, ID, d['desk'], C.DESK, mod_of(c['day'])['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    return ck.close(s, c, SHOP, _data(c), C.DESK, 'Tiệm văn phòng phẩm')


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    extra = ''
    if n.get('budget') is not None:
        extra = f' Bé có {n["budget"]} xu: tổng giỏ không được quá số đó.'
    elif n['kind'] == 'photo':
        extra = ' Photo tính theo lượt 10 trang.'
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Hỏi khách cần gì.'
    n = t['needs']
    if n['kind'] == 'list':
        return 'Lớp 1–5 dùng vở ô li, từ lớp 6 dùng vở kẻ ngang. Gom đủ từng dòng trong danh sách.'
    if n['kind'] == 'photo':
        return 'Số lượt = số bộ × số trang mỗi bộ ÷ 10.'
    if n.get('budget') is not None:
        return f'Cộng giá từng món: tổng giỏ không quá {n["budget"]} xu.'
    return 'Chạm từng món trên kệ cho đủ số lượng, rồi bấm Giao.'


LABELS = dict(order='Đủ món, đúng loại', safe='Đúng danh sách lớp', safe_note='Đúng loại vở, đủ món cô giáo dặn.', money='Vừa tiền mang theo')


def feedback(c, t: dict) -> dict:
    return ck.feedback(t, LABELS)


def public_task(t: dict, c: dict | None = None) -> dict:
    return ck.public_task(t, SHOP, c)


def public_data(c: dict) -> dict:
    d = ck.public_book(c, SHOP, C.DESK, C.MASTER, C.EXPERT)
    m = mod_of(max(1, c['day']))
    d['mod'] = dict(id=m['id'], emoji=m['emoji'], label=m['label'], hint=m['hint'])
    return d


def content() -> dict:
    return dict(rules=C.RULES, shelves=ck.goods_view(SHOP), tags=ck.TAG_WORDS, intro=C.INTRO, sample=False)


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    ck.validate_task(SHOP, t, 'đơn tiệm văn phòng phẩm')


def validate_data(c: dict) -> None:
    ck.validate_book(c, initial(), C.DESK, 'tiệm văn phòng phẩm')


SPEC = dict(
    id=ID, prefix=PREFIX, category='shop', people=PEOPLE,
    meta=dict(short='Văn phòng phẩm', place=C.PLACE, tagline='Đủ món, đúng loại vở, đếm trước mặt khách.', icon='book',
              color='#2f6fb3', light='#e6f0fb', weather='Mùi giấy mới, tiếng máy photo rè rè',
              work='Đơn văn phòng phẩm', station='Kệ vở, tủ bút, máy photo và bàn bọc vở',
              greeting='Nghe kỹ khách cần gì, đưa đúng loại vở của lớp, đếm lại trước mặt khách.',
              caption='Đồ dùng đủ, đầu năm học vui', map_label='VĂN PHÒNG PHẨM BÚT MÂY'),
    staff=[('Chú Hai Bút', 'clerk', 'Chủ tiệm: coi máy photo, bọc vở, nhớ danh sách đồ dùng từng lớp.', 70, 80)], roles={'clerk': 'Bán hàng văn phòng phẩm'},
    tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    inventory=dict(items=ITEMS, capacity=80),   # inventory.LINE_MAX: every stocked shelf holds 80 (tests/test_stock_limits.py)
    prices={},   # the cover prices and the posted service board: fixed, never tuned
    activity=('✏️', 'Sổ tay tiệm văn phòng phẩm', [('Lớp 1–5', 'vở ô li'), ('Lớp 6+', 'vở kẻ ngang'), ('Photo', 'lượt 10 trang'),
                                                  ('Bọc vở', '1 tờ giấy bọc / quyển')],
              ['Đúng loại vở của lớp', 'Đủ từng dòng danh sách', 'Tính đúng lượt photo', 'Bán đúng giá in trên bao bì']),
    stories=[('Tờ danh sách đầu năm', ('Chú Hai lấy ra xấp danh sách đồ dùng các năm: “Năm nào cô giáo cũng dặn gần giống nhau.”',
                                       'Bạn nhìn dòng chữ “vở ô li 5 ô vuông” gạch chân hai lần.',
                                       'Chú Hai cười: “Phụ huynh lần đầu hay mua nhầm vở. Mình chỉ đúng một lần, họ nhớ mình cả năm.”'))],
    review_asides=['Tiệm đưa đúng loại vở cho lớp của con.', 'Bọc vở thẳng thớm, nhãn ghi tên rõ ràng.', 'Photo đủ bộ, đếm kỹ từng xấp.'],
    situations=[],
    more_line='Thêm một vị khách ghé tiệm văn phòng phẩm.',
    open_line='Chú Hai kéo cửa cuốn: kệ vở mới thơm mùi giấy, máy photo đã nóng, cuộn giấy bọc sẵn trên bàn.',
    guide='Hỏi khách cần gì → chạm từng món trên kệ vào giỏ → Giao. Danh sách lớp: lớp 1–5 vở ô li, từ lớp 6 vở kẻ ngang; '
          'bọc vở, dán nhãn mỗi quyển một tờ, một nhãn; photo tính lượt 10 trang (bộ × trang ÷ 10); tiền tiêu vặt có hạn thì cộng giá cho vừa.',
)
