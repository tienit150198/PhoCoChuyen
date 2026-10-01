"""Tạp Hoá Cô Ba — a neighbourhood mini-mart (plugin career).

Real work of the job:
* Cashier: the customer puts a basket on the counter. Scan unit goods, weigh
  loose produce on the scale (pick the right PLU, press tare for the
  customer's own basket), apply the weekly promotions, ask for ID before
  selling beer, lock the bill, then take payment: cash (check the note, count
  the change from real denominations), bank transfer (check the shop's bank
  notification, not the customer's screen) or "ghi sổ" (credit in the
  neighbourhood debt ledger, within a limit and without overdue debt).
* Shelves: rotate a shelf FIFO (older lots in front), read every date, pull
  expired / expiring-today lots, put a markdown sticker on lots with 1–2 days
  left, and reprint tags that do not match the price list.
* Ledger: neighbours repay on their payday or the morning after a polite
  reminder. Stock is bought through the shared inventory suppliers.

Customers review what they see. They catch overcharges and short change;
only honest customers point out undercharges or give back extra change. The
checkout refuses to sell beer to a minor and blocks beer until age is checked.
Money is always recomputed on the server from the cart; client numbers are
never trusted.

v0.5 (generator 2, older saved tasks keep generator 1):
* Luck of the day: a daily mood (heat wave, rain, payday, exam season, Mây
  Mart sale, wedding season) shapes baskets, queues and surprises.
* Price war: Mây Mart posts a flyer with cheaper prices. Price tags can be
  changed during the shift; price-sensitive neighbours haggle at the till
  (match the flyer or hold the price and maybe lose the sale).
* Rush hour: a queue of quick cash customers with turn deadlines.
* Bulk orders (wedding, death anniversary, office picnic): quote a price,
  take a deposit, restock in time and deliver before closing.
* Surprises at the counter (market inspection with a fine decision,
  shoplifter, wholesale deals, counterfeit goods, fridge failure, rats…).
* Stock on open bills is reserved, so two bills never sell the same unit.
"""
from __future__ import annotations
from ..jsoncopy import tree_copy
import functools
from . import kit
from .. import consequences as cq
from .. import archive as ar
from .. import patience as pt

ID = 'grocery'
DENOMS = (1, 2, 5, 10, 20, 50, 100, 200, 500)
NOTE_SIZES = (10, 20, 50, 100, 200, 500)
WEIGHED = {'rice': 1000, 'greens': 100, 'tomato': 100}   # grams per stock unit
AGE_LIMITED = ('beer',)
SHELF_PAY = 16
OVERDUE_DAYS = 5
MARKDOWN = 30   # percent, policy shown to the player

# ---- care loop (see docs/superpowers/specs/2026-09-29-grocery-care-design.md)
BAD_DAYS = 12                          # a debt this old, with trust ≤ 1 and no plan, is written off
TRUST_START = {1: 2, 2: 4, 4: 4, 6: 3}
TRUST_LIMIT = (0, 60, 80, 100, 120, 140)   # percent of the base limit per trust level
TRUST_NAMES = ('Ngưng ghi sổ', 'Dè dặt', 'Tạm tin', 'Tin', 'Tin cậy', 'Như người nhà')
PLAN_PARTS = (2, 3)
PLAN_GAP = 2                           # days between instalments
HARD_FROM = 4                          # no lean days in the first days of the game
HARD_BLOCK = 6                         # at most one lean spell per neighbour in each block of days
FIRST_HARD = {1: (5, 2)}               # Chú Bảy's scooter breaks down in the first week: (first day, days)
# Lean days: chance per block (percent) and what the alley says about it.
HARD = {1: (65, ('Xe ôm của chú hư bộ nồi, mấy bữa nay chạy được ít cuốc.', 'Chú vừa đóng tiền học cho thằng Út, trong túi còn mấy đồng.')),
        2: (40, ('Bé út nhà chị Lan sốt, chị nghỉ làm ở nhà trông con.', 'Xưởng may cắt ca tăng ca, lương về ít hơn mọi tháng.')),
        4: (35, ('Lương hưu của bà về trễ mấy ngày.', 'Bà vừa đi khám mắt, tốn khoản thuốc men.')),
        6: (45, ('Quán cơm tấm vắng khách cả tuần vì đào đường trước quán.', 'Chị Diệu vừa sửa lại cái tủ đông của quán.'))}
ROTATE = ('milk', 'egg', 'bread', 'greens', 'tomato')   # dated goods whose shelf order matters
# Weekly lists: pickup when day % 7 == wd (from day LIST_FROM), items in stock units.
LIST_FROM = 3
LISTS = {4: dict(wd=3, pay='cash', items=(('rice', 2), ('egg', 10), ('greens', 3), ('tomato', 2)),
                 say='Chiều bà ghé lấy giỏ như mọi tuần nghe cháu. Rau với cà lựa giùm bà tươi tươi.'),
         6: dict(wd=4, pay='transfer', items=(('rice', 5), ('oil', 1), ('fishsauce', 1), ('egg', 20)),
                 say='Đồ tuần cho quán nha em, chiều chị cho đứa nhỏ qua lấy, chị chuyển khoản.'),
         2: dict(wd=6, pay='credit', items=(('milk', 8), ('egg', 10), ('noodle', 5), ('bread', 2)),
                 say='Giỏ sữa tuần cho tụi nhỏ, em ghi sổ giùm chị như mọi khi nha.'),
         5: dict(wd=0, pay='transfer', items=(('milk', 4), ('soda', 6), ('snack', 3), ('bread', 2)),
                 say='Đồ ăn sáng cả tuần, tan làm anh ghé lấy, anh chuyển khoản.')}
BOND_START = 2
BOND_NAMES = ('Giận tiệm', 'Mới quen', 'Quen mặt', 'Khách quen', 'Thân thiết', 'Khách ruột')
BOND_CALM = 4                          # from this bond the regular stops bringing the Mây Mart flyer
FORECAST_SLOTS = 3                     # a day opens with three customers
FORECAST_SPARE = 20                    # percent kept in reserve for walk-ins and carried-over work

ITEMS = [
    dict(id='rice', name='Gạo Tám Thơm', emoji='🍚', group='goods', unit='kg', cost=14, life=None, start=25),
    dict(id='egg', name='Trứng gà', emoji='🥚', group='ingredient', unit='quả', cost=2, life=10, start=40),
    dict(id='noodle', name='Mì gói Hảo Vị', emoji='🍜', group='goods', unit='gói', cost=3, start=40),
    dict(id='fishsauce', name='Nước mắm Cá Cơm Vàng', emoji='🐟', group='goods', unit='chai', cost=26, start=8),
    dict(id='oil', name='Dầu ăn Hướng Dương', emoji='🌻', group='goods', unit='chai', cost=40, start=6),
    dict(id='milk', name='Sữa hộp Mây Trắng', emoji='🥛', group='drink', unit='hộp', cost=6, life=3, start=24),
    dict(id='bread', name='Bánh mì ổ', emoji='🥖', group='ingredient', unit='ổ', cost=3, life=3, start=12),   # fresh day + day-old day
    dict(id='greens', name='Rau cải xanh', emoji='🥬', group='ingredient', unit='lạng (100 g)', cost=2, life=3, start=30),
    dict(id='tomato', name='Cà chua', emoji='🍅', group='ingredient', unit='lạng (100 g)', cost=2, life=4, start=30),
    dict(id='soap', name='Xà bông Thơm Mát', emoji='🧼', group='care', unit='bánh', cost=12, start=10),
    dict(id='snack', name='Snack Khoai Giòn', emoji='🍟', group='goods', unit='gói', cost=5, start=20),
    dict(id='soda', name='Nước ngọt Bọt Biển', emoji='🥤', group='drink', unit='lon', cost=7, start=24),
    dict(id='beer', name='Bia Sông Mây', emoji='🍺', group='drink', unit='lon', cost=11, start=24, age=18),
    dict(id='gas', name='Phiếu đổi bình gas', emoji='🔥', group='supply', unit='phiếu', cost=310, start=2, unlock=2),
]
ITEM_INDEX = {x['id']: x for x in ITEMS}
# Price list (per unit; per kg for weighed goods). Players may tune ±25% before a shift.
PRICES = {'rice': 18, 'egg': 3, 'noodle': 4, 'fishsauce': 35, 'oil': 52, 'milk': 8, 'bread': 5, 'greens': 30,
          'tomato': 25, 'soap': 18, 'snack': 7, 'soda': 10, 'beer': 15, 'gas': 330}

PROMOS = [
    dict(id='noodle5', item='noodle', kind='bundle', every=5, free=1, label='Mì Hảo Vị: mua 5 gói tính tiền 4'),
    dict(id='milk4', item='milk', kind='step', every=4, off=4, label='Sữa Mây Trắng: lốc 4 hộp giảm 4 xu'),
    dict(id='soda6', item='soda', kind='step', every=6, off=6, label='Nước ngọt Bọt Biển: 6 lon giảm 6 xu'),
    dict(id='oil5', item='oil', kind='each', off=5, label='Dầu ăn Hướng Dương: giảm 5 xu mỗi chai'),
]
PROMO_INDEX = {x['id']: x for x in PROMOS}

PEOPLE = [
    ('Cô Ba', 'Chủ tiệm', 'Tính nhẩm nhanh hơn máy, nhớ ai nợ bao nhiêu từ năm ngoái.', 'bossy'),
    ('Chú Bảy', 'Xe ôm đầu hẻm', 'Vui tính, chiều hay mua bia, câu cửa miệng “cuối tuần chú trả”.', 'warm'),
    ('Chị Lan', 'Công nhân may', 'Ít nói, tính kỹ từng đồng cho hai đứa nhỏ.', 'quiet'),
    ('Bé Tí', 'Học sinh lớp 9', 'Lanh lợi, hay bị ba sai đi mua đồ.', 'genz'),
    ('Bà Sáu', 'Hàng xóm lớn tuổi', 'Đi chợ bằng rổ nhựa, đếm tiền thối hai lần.', 'sour'),
    ('Anh Khoa', 'Nhân viên văn phòng', 'Luôn chuyển khoản, soi hóa đơn từng dòng.', 'picky'),
    ('Chị Diệu', 'Chủ quán cơm tấm', 'Mua sỉ, lúc nào cũng vội.', 'bossy'),
]
# Who points out an undercharge or gives back extra change (true to character).
HONEST = {0: True, 1: True, 2: False, 3: False, 4: True, 5: True, 6: False}
AGE = {0: 58, 1: 54, 2: 34, 3: 15, 4: 71, 5: 29, 6: 45}
# How likely (percent) each neighbour counts the change and reads the till screen right at the
# counter. Rolled once per customer and bill (seeded), never re-rolled.
COUNTS = {0: 100, 1: 40, 2: 100, 3: 30, 4: 100, 5: 100, 6: 25}
# How likely a customer who got the right change quickly says “khỏi thối, giữ uống nước” and leaves
# the small change (at most KEEP_MAX xu) on the counter. Luck, seeded like COUNTS.
KEEP = {0: 0, 1: 55, 2: 5, 3: 15, 4: 5, 5: 30, 6: 45}
KEEP_MAX = 10
KEEP_SAY = {1: 'Mấy đồng lẻ khỏi thối, cháu giữ uống nước nghen!', 2: 'Thôi mấy đồng lẻ em giữ uống nước nha.',
            3: 'Dạ khỏi thối ạ, giữ uống nước nha!', 4: 'Mấy đồng lẻ bà cho cháu uống nước.',
            5: 'Khỏi thối, em giữ uống nước nha.', 6: 'Khỏi thối khỏi thối, em giữ uống nước, chị đi đây!'}
# Neighbours allowed to buy on credit: limit, payday cycle (days), share repaid (percent).
NEIGHBOURS = {1: dict(limit=150, cycle=4, share=50), 2: dict(limit=250, cycle=5, share=100),
              4: dict(limit=100, cycle=3, share=100), 6: dict(limit=300, cycle=6, share=100)}
OPENING_DEBT = {1: 90, 2: 60, 4: 0, 6: 0}

# (npc, title, opening, lines, pay, tender style, note, extras, min_day)
# line: (item, qty) or (item, 'w', grams, container grams)
CHECKOUTS = [
    (4, 'Bà Sáu đi chợ sáng', 'Cháu ơi, cân giùm bà mớ rau với ít cà chua nha!',
     [('greens', 'w', 480, 150), ('tomato', 'w', 350, 150), ('egg', 10)], 'cash', 'big', 'Rau với cà bà để chung trong cái rổ nhựa của bà đó.', {}, 1),
    (1, 'Chú Bảy mua mồi chiều', 'Chiều nay đội xe ôm ngồi chơi, bán chú ít đồ nha!',
     [('beer', 6), ('snack', 2), ('soda', 2)], 'cash', 'round', 'Sáu lon Sông Mây, lấy lon mát giùm chú.', {}, 1),
    (5, 'Bữa sáng mang đi', 'Tính giùm anh nhanh nha, anh chuyển khoản.',
     [('milk', 4), ('bread', 2)], 'transfer', None, 'Lốc 4 hộp sữa có khuyến mãi đúng không em?', dict(transfer='ok'), 1),
    (2, 'Chị Lan ghi sổ cuối tháng', 'Em ơi, ghi sổ giùm chị, lãnh lương chị trả liền.',
     [('rice', 'w', 5000, 0), ('fishsauce', 1), ('oil', 1), ('noodle', 5)], 'credit', 'round', 'Gạo 5 ký, mì lấy 5 gói cho đủ khuyến mãi.', {}, 1),
    (3, 'Tí đi mua giùm ba', 'Dạ ba con sai con đi mua đồ ạ!',
     [('snack', 1), ('beer', 2), ('soda', 1)], 'cash', 'round', 'Ba con dặn mua 2 lon bia với gói snack cho em con.', dict(age=True), 1),
    (6, 'Quán cơm nhập gấp', 'Lẹ giùm chị nha, trưa nay quán đông lắm!',
     [('rice', 'w', 10000, 0), ('oil', 2), ('fishsauce', 2), ('egg', 20)], 'transfer', None, 'Chị chuyển khoản liền nè, coi giùm chị.', dict(transfer='typo'), 1),
    (3, 'Tí mua quà vặt sau giờ học', 'Chị ơi em mua đồ ăn vặt!',
     [('snack', 3), ('soda', 1), ('milk', 1)], 'cash', 'exact', 'Em đưa đủ tiền lẻ luôn nè, khỏi thối.', {}, 1),
    (1, 'Chú Bảy trả bằng tờ 200', 'Hôm nay chú chạy được cuốc xa, trả tiền mặt nè!',
     [('noodle', 5), ('egg', 10), ('fishsauce', 1)], 'cash', 'big', 'Chú chỉ còn tờ 200, thối giùm chú.', dict(fake=True), 2),
    (5, 'Đồ cho buổi họp nhóm', 'Anh chuyển khoản rồi đó, em kiểm giùm anh.',
     [('soda', 6), ('snack', 3), ('soap', 2)], 'transfer', None, 'Sáu lon nước ngọt có giảm giá đúng không?', dict(transfer='pending'), 2),
    (2, 'Sữa cho hai đứa nhỏ', 'Chị lấy sữa cho tụi nhỏ, tính giùm chị.',
     [('milk', 8), ('egg', 10), ('greens', 'w', 300, 0)], 'cash', 'round', 'Hai lốc sữa, rau cải chị bỏ túi nilon của tiệm.', {}, 2),
    (4, 'Bà Sáu đổi phiếu gas', 'Bình gas nhà bà hết rồi, bán bà phiếu đổi gas nha cháu.',
     [('gas', 1), ('soap', 1)], 'cash', 'mix', 'Bà đưa tiền chẵn, cháu thối lại cho đúng nghe.', {}, 3),
    (6, 'Chị Diệu lấy thêm rau', 'Hết rau giữa trưa, cân giùm chị lẹ lẹ!',
     [('greens', 'w', 1200, 0), ('tomato', 'w', 900, 0), ('rice', 'w', 3000, 0)], 'cash', 'round', 'Rau với cà đựng túi của tiệm, khỏi trừ bì.', {}, 3),
    (1, 'Chú Bảy ghi sổ thêm', 'Ghi sổ giùm chú, cuối tuần chú trả luôn một lần!',
     [('noodle', 10), ('egg', 10), ('beer', 4)], 'credit', 'round', 'Sổ của chú còn trang mà, ha?', {}, 3),
    (4, 'Bà Sáu ghi sổ bó rau', 'Bà quên ví ở nhà, ghi sổ giùm bà nha cháu.',
     [('greens', 'w', 400, 150), ('egg', 6), ('bread', 1)], 'credit', 'round', 'Chiều bà gửi thằng cháu mang tiền qua.', {}, 2),
]
# (title, opening, item, min_day)
SHELVES = [
    ('Xoay kệ sữa buổi sáng', 'Xe sữa vừa giao thùng mới. Cháu xếp kệ sữa giùm cô, nhớ đọc hạn từng lốc nha!', 'milk', 1),
    ('Kiểm kệ mì gói', 'Kệ mì lâu rồi chưa ai lật lên coi. Gói nào hết hạn là rút ra liền nghe.', 'noodle', 1),
    ('Kệ bánh mì sáng sớm', 'Bánh mì mới giao. Ổ hôm qua coi còn bán được không, rồi xếp lại giùm cô.', 'bread', 2),
    ('Tủ trứng gà', 'Thùng trứng mới về. Trứng cũ để ra trước, quả nào quá hạn thì bỏ.', 'egg', 2),
]
SHELF_RANGES = {'milk': ((-2, 0), (1, 2), (3, 5), (4, 7), 9), 'noodle': ((-20, -1), (1, 2), (15, 40), (30, 90), 150),
                'bread': ((-1, 0), (1, 1), (1, 2), (2, 2), 3), 'egg': ((-3, 0), (1, 2), (4, 8), (6, 10), 14)}


def _lvl(day: int) -> int:
    return 1 + (day - 1) // 2


def make_task(day: int, slot: int, serial: int) -> dict:
    # Tasks saved before v0.5 carry a serial in the legacy band and keep generator 1.
    if type(serial) is int and serial >= LEGACY:
        return _make_v1(day, slot, serial)
    return _make_v2(day, slot, serial)


def _make_v1(day: int, slot: int, serial: int) -> dict:
    rng = kit.rng(ID, day, slot)
    shelves = [x for x in SHELVES if x[3] <= day]
    if (day * 3 + slot) % 4 == 1 and shelves:
        title, opening, item, _ = shelves[(day + slot + rng.randrange(2)) % len(shelves)]
        return _make_shelf(day, slot, serial, rng, title, opening, item)
    pool = [x for x in CHECKOUTS if x[8] <= day]
    return _checkout(day, slot, serial, rng, pool[((day - 1) * 3 + slot + rng.randrange(3)) % len(pool)][:8])


def _checkout(day: int, slot: int, serial: int, rng, script, neutral: bool = False) -> dict:
    npc, title, opening, lines, pay, style, note, extras = script
    if neutral:
        opening, note = NEUTRAL.get(opening, opening), NEUTRAL.get(note, note)
    level = _lvl(day)
    rows = []
    for row in lines:
        item = row[0]
        if ITEM_INDEX[item].get('unlock', 1) > level:
            continue
        if len(row) == 4:
            grams = row[2] if item == 'rice' else max(100, row[2] + 10 * rng.randrange(-4, 5))
            rows.append(dict(item=item, weighed=True, container=row[3], _grams=grams))
        else:
            rows.append(dict(item=item, qty=row[1]))
    if not rows:
        rows = [dict(item='noodle', qty=2)]
    has_age = any(r['item'] in AGE_LIMITED for r in rows)
    needs = dict(lines=rows, pay=pay, style=style or 'round', note=note,
                 _age=AGE[npc] if has_age else None, _fake=bool(extras.get('fake')), _transfer=extras.get('transfer'))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='checkout', needs=needs,
                         scanned={}, weighed={}, promos=[], age=None, stage='basket', total=None,
                         pay=_empty_pay(), flags=_empty_flags(), result=None, quoted_price=None)


def _make_shelf(day: int, slot: int, serial: int, rng, title: str, opening: str, item: str) -> dict:
    r = SHELF_RANGES[item]
    offsets = [rng.randint(*r[0]), rng.randint(*r[1]), rng.randint(*r[2]), rng.randint(*r[3])]
    if rng.random() < 0.25:
        offsets.pop(1)   # not every shelf has a near-expiry lot
    ids = 'ABCD'[:len(offsets)]
    lots = [dict(id=i, qty=rng.randint(2, 6)) for i in ids]
    order = list(ids)
    rng.shuffle(order)
    if order == sorted(order, key=lambda i: offsets[ids.index(i)]):
        order.reverse()
    exps = {i: offsets[k] for k, i in enumerate(ids)}
    exps['N'] = max(offsets) + r[4] // 3 + 2
    needs = dict(item=item, lots=lots, new=dict(id='N', qty=rng.randint(4, 8)), start=order,
                 _exps=exps, _tag_error=rng.choice((0, 0, 2, -1, 3)))
    shelf = dict(order=list(order), cart=['N'], checked=[], pulled=[], marked=[], tag=None, retagged=False, placed=False)
    return kit.base_task(ID, day, slot, serial, 0, title, opening, kind='shelf', needs=needs, shelf=shelf, result=None)


FIXED = ('needs',)


def _empty_pay() -> dict:
    return dict(tender=[], checked=False, swapped=False, change=[], screen=None, verified=False, bank=None,
                fixed=False, ready=0, declined=False)


def _empty_flags() -> dict:
    return dict(overcharge=0, undercharge=0, short_change=0, excess=0, fake=0, unverified=0, transfer_loss=0,
                credit_risky=0, credit_harsh=0, credit_ok=0, missing=0, out=0, minor_refused=0)


def initial() -> dict:
    ledger = {str(k): dict(limit=v['limit'], balance=OPENING_DEBT[k], since=0 if not OPENING_DEBT[k] else 1, reminded=0, paid=0)
              for k, v in NEIGHBOURS.items()}
    d = dict(ledger=ledger, sales=0, customers=0, shelves=0, day_sales=0, repaid=0)
    _extend(d)
    return d


def _extend(d: dict) -> dict:
    """v0.5 fields; old saves get them here (setdefault keeps what is there)."""
    d.setdefault('desk', kit.desk_initial())
    d.setdefault('today', dict(day=0, mod='normal', calm=False))
    d.setdefault('fine', None)
    d.setdefault('cleared', [])
    stats = d.setdefault('stats', {})
    for k in STAT_KEYS:
        stats.setdefault(k, 0)
    # care loop: trust and plans on the credit book, shelf order, weekly lists
    for key, row in d.get('ledger', {}).items():
        if isinstance(row, dict):
            row.setdefault('trust', TRUST_START.get(int(key), 3) if str(key).isdigit() else 3)
            row.setdefault('late', False)
            row.setdefault('plan', None)
            row.setdefault('written', 0)
    d.setdefault('rot', {})
    lists = d.setdefault('lists', {})
    if isinstance(lists, dict):
        for k in LISTS:
            lists.setdefault(str(k), dict(bond=BOND_START, packed={}, stale=0, day=0, done=0, missed=0))
    return d


def _data(c: dict) -> dict:
    return _extend(kit.data(c))


# ---------------------------------------------------------------- pricing
def _price(c: dict, item: str) -> int:
    return kit.price(c, item, PRICES[item])


def _weighed_amount(price_kg: int, grams: int) -> int:
    return (grams * price_kg + 500) // 1000


def _units(item: str, grams: int) -> int:
    return -(-grams // WEIGHED[item])


def _discount(promo: dict, qty: int, unit_price: int) -> int:
    if promo['kind'] == 'bundle':
        return (qty // promo['every']) * promo['free'] * unit_price
    if promo['kind'] == 'step':
        return (qty // promo['every']) * promo['off']
    return qty * promo['off']


def _minor(t: dict) -> bool:
    age = t['needs'].get('_age')
    return age is not None and age < 18


def _held(c: dict, item: str, t: dict | None) -> int:
    """Units already rung up on other open bills (not yet handed over)."""
    held = 0
    for o in c['tasks']:
        if (o.get('career') == ID and o.get('kind') == 'rush' and (t is None or o['id'] != t['id'])
                and o['status'] not in ('completed', 'referred', 'cancelled')):
            # Rung up on the rush till but not yet paid for (stock leaves the shelf when the till totals).
            off = (o.get('rush') or {}).get('offer')   # read only (an old-format offer has no 'scanned')
            if isinstance(off, dict) and off.get('charged') is None:
                held += (off.get('scanned') or {}).get(item, 0)
            continue
        if (o.get('career') != ID or o.get('kind') != 'checkout' or (t is not None and o['id'] == t['id'])
                or o['status'] in ('completed', 'referred', 'cancelled') or o.get('stage') not in ('basket', 'pay')):
            continue
        held += o['scanned'].get(item, 0)
        if item in WEIGHED:
            for key in o['weighed']:
                line = o['needs']['lines'][int(key)]
                if line['item'] == item:
                    held += _units(item, line['_grams'])
    return held


def _available(c: dict, item: str, t: dict | None = None) -> int:
    """Units on the shelf that no other open bill has claimed."""
    return max(0, kit.stock(c, item) - _held(c, item, t))


def _physical_grams(c: dict, t: dict | None, item: str, grams: int) -> int:
    return min(grams, _available(c, item, t) * WEIGHED[item])


def _dropped(t: dict, item: str) -> bool:
    h = t.get('haggle')
    return bool(h) and h['state'] == 'dropped' and h['item'] == item


def _unit(c: dict, t: dict, item: str) -> int:
    """Unit price on this bill: the flyer price when the till matched Mây Mart."""
    h = t.get('haggle')
    if h and h['state'] == 'match' and h['item'] == item:
        return h['theirs']
    return _price(c, item)


def _expected(c: dict, t: dict) -> tuple[dict, dict]:
    """What the customer can really take home: basket limited by shelf stock and by law."""
    units, weighed = {}, {}
    for i, line in enumerate(t['needs']['lines']):
        item = line['item']
        if line.get('weighed'):
            g = _physical_grams(c, t, item, line['_grams'])
            if g > 0:
                weighed[i] = g
        elif not (item in AGE_LIMITED and _minor(t) and not _minor_beer(t)) and not _dropped(t, item):
            q = min(line['qty'], _available(c, item, t) - units.get(item, 0))
            if item in AGE_LIMITED and _minor(t):
                q = min(q, t['scanned'].get(item, 0) - units.get(item, 0))
            if q > 0:
                units[item] = units.get(item, 0) + q
    return units, weighed


def _minor_beer(t: dict) -> bool:
    """Beer rung up for a minor without asking for ID: it leaves the shop with them."""
    return _minor(t) and t['age'] is None and any(t['scanned'].get(i) for i in AGE_LIMITED)


def _full_total(c: dict, needs: dict) -> int:
    """Price of the whole basket as the customer imagines it (used for the money they bring)."""
    units = {}
    total = 0
    for line in needs['lines']:
        if line.get('weighed'):
            total += _weighed_amount(_price(c, line['item']), line['_grams'])
        else:
            units[line['item']] = units.get(line['item'], 0) + line['qty']
    total += sum(_price(c, k) * q for k, q in units.items())
    total -= sum(_discount(p, units.get(p['item'], 0), _price(c, p['item'])) for p in PROMOS)
    return max(1, total)


def _cart_amount(c: dict, t: dict) -> int:
    total = sum(_unit(c, t, k) * q for k, q in t['scanned'].items())
    total += sum(_weighed_amount(_price(c, w['plu']), w['grams']) for w in t['weighed'].values())
    total -= sum(_discount(PROMO_INDEX[p], t['scanned'].get(PROMO_INDEX[p]['item'], 0), _unit(c, t, PROMO_INDEX[p]['item'])) for p in t['promos'])
    return max(0, total)


def _greedy(amount: int) -> list[int]:
    notes = []
    for d in reversed(DENOMS):
        while amount >= d and len(notes) < 20:
            notes.append(d)
            amount -= d
    return notes


def _tender(total: int, style: str) -> list[int]:
    if style == 'exact':
        return _greedy(total)
    if style == 'mix':
        return _greedy(-(-total // 50) * 50)
    note = next((n for n in NOTE_SIZES if n >= total), None)
    if note is None:
        return [500] * min(20, -(-total // 500))
    if style == 'big':
        bigger = next((n for n in NOTE_SIZES if n > note), None)
        return [bigger] if bigger else [note]
    return [note]


def quote(c: dict, t: dict) -> None:
    if t['kind'] == 'shelf':
        if t['shelf']['tag'] is None:
            t['shelf']['tag'] = max(1, _price(c, t['needs']['item']) + t['needs']['_tag_error'])
        return
    if t['kind'] == 'rush':
        _rush_offer(c, t)
        return
    if t['kind'] != 'checkout' or t['stage'] != 'basket':
        return
    t['quoted_price'] = _full_total(c, t['needs'])
    if t['needs']['pay'] == 'cash':
        t['pay']['tender'] = _tender(t['quoted_price'], t['needs']['style'])


def on_task(s: dict, c: dict, t: dict) -> None:
    if (t['kind'] == 'shelf' and t['shelf']['tag'] is None or t['kind'] == 'checkout' and t['quoted_price'] is None
            or t['kind'] == 'rush' and t['rush']['offer'] is None):
        quote(c, t)


def on_stock(s: dict, c: dict, action: str) -> None:
    """After a stock-room action (a crate counted onto the shelf, a lot thrown out): the rush
    customer at the counter sees the shelf as it is now, unless their money is already on the counter."""
    if action not in ('inv_receive', 'inv_discard'):
        return
    for t in c['tasks']:
        if (t.get('career') == ID and t.get('kind') == 'rush' and t['status'] not in ('completed', 'cancelled', 'referred')
                and t['rush']['start'] is not None and not (t['rush']['offer'] and t['rush']['offer']['charged'] is not None)):
            _rush_offer(c, t)


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    mod = mod_of(c['day'])
    d['today'] = dict(day=c['day'], mod=mod['id'], calm=False)
    d['cleared'] = []
    for t in c['tasks']:
        if t['career'] == ID and t['status'] not in ('completed', 'cancelled', 'referred'):
            if t['kind'] in ('checkout', 'rush'):
                quote(c, t)   # prices may have been retuned between shifts
            else:
                on_task(s, c, t)
    _sync_rot(c)
    _repayments(s, c)
    kit.log(s, c, 'day', f'{mod["emoji"]} Hôm nay: {mod["name"]} — {mod["text"]}')
    for key, spec in LISTS.items():
        if _list_for(key, c['day']):
            kit.log(s, c, 'list', f'🧺 Chiều nay {PEOPLE[key][0]} ghé lấy giỏ quen hàng tuần — soạn sẵn trước khi đóng ca.', kit.npc_id(ID, key))
    flyer = rival(c['day'])
    if flyer:
        kit.log(s, c, 'rival', 'Tờ rơi Mây Mart hôm nay: ' + ', '.join(f'{ITEM_INDEX[k]["name"]} {v} xu' for k, v in flyer.items()) + '.')
    kit.desk_start(s, c, ID, d['desk'], EVENTS, mod['id'], festival=c['life'].get('mode') == 'festival')


def _repayments(s: dict, c: dict) -> None:
    """The morning count of the credit book: plans, paydays, reminders, lean days,
    overdue debts and (rarely) a debt Cô Ba has to write off."""
    d = _data(c)
    day = c['day']
    salary = mod_of(day)['id'] == 'payday'
    for key, row in d['ledger'].items():
        if row['balance'] <= 0:
            row['plan'] = None
            continue
        i = int(key)
        rule = NEIGHBOURS[i]
        npc = kit.npc_id(ID, i)
        name = PEOPLE[i][0]
        plan = row['plan']
        if plan:
            if day >= plan['next']:
                amount = min(plan['each'], row['balance'])
                plan['left'] -= 1
                plan['next'] = day + PLAN_GAP
                _repay(s, c, d, key, row, amount, f'{name} trả góp theo lịch')
                if not row['balance']:
                    row['trust'] = min(5, row['trust'] + 1)
                    kit.log(s, c, 'ledger', f'{name} trả đủ theo lịch giãn nợ — lòng tin lên “{TRUST_NAMES[row["trust"]]}”.', npc)
                    row['plan'] = None
                elif plan['left'] <= 0:
                    row['plan'] = None
            continue
        age = day - max(1, row['since'])
        payday = age > 0 and age % rule['cycle'] == 0 or salary and age > 0
        reminded = row['reminded'] and row['reminded'] == day - 1
        hard = _hard(i, day)
        if (payday or reminded) and hard:
            kit.log(s, c, 'ledger', f'{name} ghé xin khất: “{hard}” Còn nợ {row["balance"]} xu.', npc)
        elif payday or reminded:
            amount = row['balance'] if rule['share'] >= 100 else max(1, row['balance'] * rule['share'] // 100)
            _repay(s, c, d, key, row, amount, f'{name} trả nợ sổ')
            if not row['balance']:
                continue
        if age > OVERDUE_DAYS and not row['late']:
            row['late'] = True
            row['trust'] = max(0, row['trust'] - 1)
            kit.log(s, c, 'ledger', f'Khoản nợ {row["balance"]} xu của {name} đã quá {OVERDUE_DAYS} ngày — lòng tin còn “{TRUST_NAMES[row["trust"]]}”. '
                    'Nhắc khéo hoặc giãn nợ trước khi quá muộn.', npc)
        if age > BAD_DAYS and row['trust'] <= 1:
            lost = row['balance']
            row['written'] = min(10**9, row['written'] + lost)
            row['balance'] = 0
            row['since'] = 0
            row['late'] = False
            row['trust'] = max(1, row['trust'])
            d['stats']['bad_debt'] += lost
            kit.metric(c, 'gr_bad_debt', lost)
            kit.log(s, c, 'loss', f'Cô Ba thở dài gạch sổ: {name} không trả nổi khoản {lost} xu đã nợ {age} ngày. Mất trắng.', npc)


def _repay(s: dict, c: dict, d: dict, key: str, row: dict, amount: int, reason: str) -> None:
    i = int(key)
    row['balance'] -= amount
    row['paid'] += amount
    d['repaid'] += amount
    if row['balance'] == 0:
        if not row['late'] and not row['plan']:
            row['trust'] = min(5, row['trust'] + 1)
        row['since'] = 0
        row['late'] = False
    kit.money(s, c, amount, reason, f'ledger-{key}-{c["day"]}', 'debt_repaid')
    kit.log(s, c, 'ledger', f'{PEOPLE[i][0]} ghé trả {amount} xu tiền sổ' + (' — đã gạch hết nợ.' if not row['balance'] else f', còn nợ {row["balance"]} xu.'), kit.npc_id(ID, i))


def _hard(i: int, day: int) -> str | None:
    """A neighbour's lean days: decided by the neighbour and the 8-day block alone."""
    if i not in HARD or day < HARD_FROM:
        return None
    chance, reasons = HARD[i]
    first = FIRST_HARD.get(i)
    if first and first[0] <= day < first[0] + first[1]:
        return reasons[0]
    block = (day - 1) // HARD_BLOCK
    r = kit.rng(ID, 'hard', i, block)
    if r.randrange(100) >= chance:
        return None
    start = block * HARD_BLOCK + 1 + r.randrange(HARD_BLOCK - 1)
    length = 2 + r.randrange(2)
    reason = reasons[r.randrange(len(reasons))]
    return reason if start <= day < start + length and start >= HARD_FROM else None


def _limit(key, row: dict) -> int:
    return NEIGHBOURS[int(key)]['limit'] * TRUST_LIMIT[max(0, min(5, row.get('trust', 3)))] // 100


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'rush':
        r = t['rush']
        if r['start'] is None:   # the queue forms the moment the doors are opened to it
            r['start'] = c['turn']
            _rush_offer(c, t)
        return (f'Hàng chờ {len(n["queue"])} khách tan ca. Mỗi người mua vài món, trả tiền mặt: quét từng món, bấm “Tính tiền”, '
                f'đếm tiền thối vào khay rồi giao hàng. Ai mua bia thì kiểm tuổi. Để khách chờ quá lâu là khách bỏ về.')
    if t['kind'] == 'bulk':
        parts = [f'{x["qty"]} {ITEM_INDEX[x["item"]]["unit"]} {ITEM_INDEX[x["item"]]["name"]}' for x in n['lines']]
        return (f'Đơn sỉ: {", ".join(parts)}. Báo giá (có thể bớt 5–15%), nhận cọc {n["deposit"]}%, '
                f'soạn đủ hàng rồi giao trước khi đóng ca. “{n["note"]}”')
    if t['kind'] == 'shelf':
        it = ITEM_INDEX[n['item']]
        return (f'Kệ {it["name"]}: {len(n["lots"])} lô đang bày + 1 thùng mới giao ({n["new"]["qty"]} {it["unit"]}). '
                f'Đọc hạn từng lô, rút hàng quá hạn/hết hạn hôm nay, dán tem giảm {MARKDOWN}% cho lô còn 1–2 ngày, '
                f'xếp lô cũ ra trước, lô mới ra sau, và đối chiếu tem giá với bảng giá.')
    parts = []
    for line in n['lines']:
        it = ITEM_INDEX[line['item']]
        if line.get('weighed'):
            parts.append(f'1 túi {it["name"].lower()} (cân ký)' + (' trong rổ riêng của khách' if line['container'] else ''))
        else:
            parts.append(f'{line["qty"]} {it["unit"]} {it["name"]}')
    how = {'cash': 'trả tiền mặt', 'transfer': 'chuyển khoản', 'credit': 'xin ghi sổ'}[n['pay']]
    return 'Khách đặt lên quầy: ' + ', '.join(parts) + f'. Khách {how}. “{n["note"]}”'


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    _sync_rot(c)
    if name == 'gr_decide':
        return _decide(s, c, p)
    kit.desk_block(d['desk'], 'Có chuyện bất ngờ ở tiệm — quyết xong rồi làm tiếp nhé.')
    result = _handle(s, c, name, p)
    kit.desk_tick(s, c, ID, d['desk'], EVENTS, mod_of(c['day'])['id'])
    ev = d['desk']['ev']
    if ev:
        x = kit.desk_script(EVENTS, ev['script'])
        result = dict(result, message=f'{result.get("message", "")} · {x["emoji"]} {x["title"]}!'.strip(' ·'))
    return result


def _handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = kit.data(c)
    if name in SHOP_ACTIONS:
        return SHOP_ACTIONS[name](s, c, p)
    if name == 'gr_remind':
        key = _ledger_key(p.get('npc'))
        row = d['ledger'][key]
        kit.need(row['balance'] > 0, 'Người này không còn nợ trong sổ.')
        kit.need(row['reminded'] != c['day'], 'Hôm nay đã nhắc rồi. Nhắc nhiều quá dễ mất lòng hàng xóm.')
        kit.need(not row['plan'], 'Đang trả góp theo lịch đã hẹn — không cần nhắc, cứ chờ tới kỳ.')
        row['reminded'] = c['day']
        kit.metric(c, 'ledger_reminders')
        who = PEOPLE[int(key)]
        hard = _hard(int(key), c['day'])
        if hard:
            row['trust'] = max(0, row['trust'] - 1)
            return dict(message=f'Bạn nhắc {who[0]} về khoản {row["balance"]} xu đúng lúc nhà đang kẹt. {who[0]} cúi mặt: “{hard} Cho khất ít bữa…” '
                                f'Lòng tin còn “{TRUST_NAMES[row["trust"]]}”. Lúc này nên đề nghị giãn nợ.', refused=True)
        reply = {'warm': 'Ờ ờ, chú nhớ mà! Mai chú ghé trả liền nghen.', 'quiet': 'Dạ… mai chị gửi.',
                 'sour': 'Bà nhớ chứ, bà có quỵt của ai bao giờ đâu. Mai bà đưa.', 'bossy': 'Rồi rồi, mai chị chuyển, nhắc chi kỹ vậy.'}.get(who[3], 'Mai mình trả nhé.')
        return dict(message=f'Bạn nhắc khéo {who[0]} về khoản {row["balance"]} xu trong sổ. {who[0]}: “{reply}”')
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Công việc không thuộc tạp hóa.')
    kit.need(t['known'], 'Mời khách đặt hàng lên quầy trước nhé (bấm “Nhận khách”).')
    if t['kind'] == 'shelf':
        return _shelf_action(s, c, t, name, p)
    if t['kind'] == 'rush':
        return _rush_action(s, c, t, name, p)
    if t['kind'] == 'bulk':
        return _bulk_action(s, c, t, name, p)
    return _checkout_action(s, c, t, name, p)


def _ledger_key(npc) -> str:
    kit.need(isinstance(npc, str) and npc.startswith(ID + '_npc_'), 'Không có người này trong sổ.')
    try:
        index = int(npc.rsplit('_', 1)[1]) - 1
    except ValueError:
        index = -1
    kit.need(index in NEIGHBOURS, 'Không có người này trong sổ.')
    return str(index)


def _ledger_ok(c: dict, npc_index: int, amount: int) -> tuple[bool, str]:
    row = _data(c)['ledger'].get(str(npc_index))
    if row is None:
        return False, 'không có trong sổ ghi nợ'
    if row['trust'] <= 0:
        return False, 'sổ đã ngưng ghi thêm vì mất lòng tin'
    if row['plan'] and row['balance']:
        return False, 'đang trả góp theo lịch giãn nợ, chưa ghi thêm'
    if row['balance'] and c['day'] - max(1, row['since']) > OVERDUE_DAYS:
        return False, f'đang có nợ cũ quá {OVERDUE_DAYS} ngày'
    limit = _limit(npc_index, row)
    if row['balance'] + amount > limit:
        return False, f'vượt hạn mức {limit} xu (đang nợ {row["balance"]})'
    return True, 'còn trong hạn mức, không có nợ quá hạn'


def _plan(s: dict, c: dict, p: dict) -> dict:
    """Giãn nợ: split a debt into 2–3 instalments, one every PLAN_GAP days."""
    d = _data(c)
    key = _ledger_key(p.get('npc'))
    row = d['ledger'][key]
    parts = p.get('parts')
    kit.need(type(parts) is int and parts in PLAN_PARTS, 'Chia 2 hoặc 3 kỳ trả.')
    kit.need(row['balance'] >= parts, 'Người này không còn khoản nợ nào để giãn.')
    kit.need(not row['plan'], 'Đã có lịch giãn nợ đang chạy.')
    each = -(-row['balance'] // parts)
    row['plan'] = dict(each=each, left=parts, next=c['day'] + PLAN_GAP)
    row['since'] = c['day']
    row['late'] = False
    d['stats']['plans'] += 1
    kit.metric(c, 'gr_plans')
    who = PEOPLE[int(key)]
    kit.log(s, c, 'ledger', f'Giãn nợ cho {who[0]}: {parts} kỳ × {each} xu, kỳ đầu ngày {c["day"] + PLAN_GAP}.', kit.npc_id(ID, int(key)))
    return dict(message=f'Bạn ngồi riêng với {who[0]}, chia khoản {row["balance"]} xu thành {parts} kỳ, mỗi kỳ {each} xu, cách {PLAN_GAP} ngày. '
                        f'{who[0]}: “Vậy thì chị/chú trả được, cảm ơn nhiều nha!” Trong lúc trả góp, sổ chưa ghi thêm.', celebrate=bool(_hard(int(key), c['day'])))


def _checkout_action(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    if t['quoted_price'] is None:
        quote(c, t)
    basket = name in ('gr_scan', 'gr_void', 'gr_weigh', 'gr_promo', 'gr_id', 'gr_total')
    if basket:
        kit.need(t['stage'] == 'basket', 'Bill đã chốt. Đang ở bước thanh toán.')
        kit.start_work(t)
    if name == 'gr_scan':
        item = kit.one_of(p.get('item'), ITEM_INDEX, 'Mặt hàng không có trong tiệm.')
        kit.need(item not in WEIGHED, 'Hàng cân ký: đặt lên cân và chọn đúng mã PLU.')
        qty = kit.integer(p.get('qty', 1), 1, 30)
        if item in AGE_LIMITED and t['age'] is not None:
            kit.need(t['age'] >= 18, 'Khách chưa đủ 18 tuổi: không bán bia. Để lon bia lại kệ.')
        kit.need(not _dropped(t, item), f'{_who(t)} đã bỏ món này, không mua ở tiệm nữa.')
        have = _available(c, item, t)
        held = _held(c, item, t)
        kit.need(t['scanned'].get(item, 0) + qty <= have,
                 f'Kệ chỉ còn {have} {ITEM_INDEX[item]["unit"]} {ITEM_INDEX[item]["name"]}' + (f' ({held} đã tính cho bill khác)' if held else '') + '.')
        kit.need(sum(t['scanned'].values()) + qty <= 60, 'Hóa đơn dài quá rồi.')
        t['scanned'][item] = t['scanned'].get(item, 0) + qty
        message = f'Bíp! {ITEM_INDEX[item]["name"]} ×{qty} · {_unit(c, t, item) * qty} xu.'
        talk = _maybe_haggle(c, t, item)
        return dict(message=message + (' ' + talk if talk else ''))
    if name == 'gr_haggle':
        return _haggle(s, c, t, p)
    if name == 'gr_void':
        if p.get('line') is not None:
            key = str(kit.integer(p.get('line'), 0, 20))
            kit.need(key in t['weighed'], 'Dòng cân này chưa có trên hóa đơn.')
            t['weighed'].pop(key)
            return dict(message='Đã xóa dòng hàng cân khỏi hóa đơn.')
        item = kit.one_of(p.get('item'), t['scanned'], 'Món này chưa có trên hóa đơn.')
        t['scanned'].pop(item)
        return dict(message=f'Đã xóa {ITEM_INDEX[item]["name"]} khỏi hóa đơn.')
    if name == 'gr_weigh':
        index = kit.integer(p.get('line'), 0, len(n['lines']) - 1)
        line = n['lines'][index]
        kit.need(line.get('weighed'), 'Món này tính theo cái, không cần cân.')
        plu = kit.one_of(p.get('plu'), WEIGHED, 'Mã PLU không có trên cân.')
        tare = p.get('tare')
        kit.need(type(tare) is bool, 'Chọn có trừ bì hay không.')
        grams = _physical_grams(c, t, line['item'], line['_grams'])
        kit.need(grams > 0, f'Quầy {ITEM_INDEX[line["item"]]["name"].lower()} đã hết hàng, khách không lấy được món này.')
        reading = grams + (0 if tare else line['container'])
        t['weighed'][str(index)] = dict(plu=plu, grams=reading, tare=tare)
        amount = _weighed_amount(_price(c, plu), reading)
        return dict(message=f'Cân: {reading} g · mã {ITEM_INDEX[plu]["name"]} {_price(c, plu)} xu/kg → {amount} xu.' + (' (Đã trừ bì.)' if tare and line['container'] else ''))
    if name == 'gr_promo':
        promo = PROMO_INDEX.get(p.get('promo'))
        kit.need(promo, 'Khuyến mãi không tồn tại.')
        kit.need(promo['id'] not in t['promos'], 'Đã áp khuyến mãi này rồi.')
        kit.need(_discount(promo, t['scanned'].get(promo['item'], 0), _unit(c, t, promo['item'])) > 0,
                 f'Hóa đơn chưa đủ điều kiện: {promo["label"]}.')
        t['promos'].append(promo['id'])
        return dict(message=f'Đã áp: {promo["label"]}.')
    if name == 'gr_id':
        kit.need(any(line['item'] in AGE_LIMITED for line in n['lines']), 'Khách không mua hàng giới hạn tuổi, không cần (và không nên) xem giấy tờ.')
        kit.need(t['age'] is None, 'Đã kiểm tuổi rồi.')
        t['age'] = n['_age']
        kit.metric(c, 'id_checks')
        if t['age'] < 18:
            t['flags']['minor_refused'] = 1
            return dict(message=f'Thẻ học sinh ghi {t["age"]} tuổi. Chưa đủ 18: không bán bia — nói nhẹ nhàng và để bia lại kệ.')
        return dict(message=f'Khách khoảng {t["age"]} tuổi, đủ 18. Máy cho phép bán bia.')
    if name == 'gr_total':
        return _lock_bill(s, c, t)
    # ---- payment
    kit.need(t['stage'] == 'pay', 'Chốt bill trước khi thanh toán.')
    pay = t['pay']
    method = _method(t)
    if name == 'gr_check_note':
        kit.need(method == 'cash', 'Khách không trả tiền mặt.')
        kit.need(not pay['checked'], 'Đã soi tiền rồi.')
        pay['checked'] = True
        kit.metric(c, 'notes_checked')
        if _fake_live(t):
            return dict(message=f'Soi đèn: tờ {max(pay["tender"])} không có hình bóng chìm, sợi bảo an in lên mặt giấy, sờ thấy trơn láng. Tiền giả!')
        return dict(message='Soi đèn thấy hình bóng chìm, sợi bảo an, cửa sổ trong suốt; sờ thấy chữ nổi. Tiền thật.')
    if name == 'gr_reject_note':
        kit.need(method == 'cash' and pay['checked'] and _fake_live(t), 'Không có tờ tiền nào cần trả lại.')
        pay['swapped'] = True
        return dict(message=f'Bạn nói nhỏ nhẹ, không làm khách mất mặt. {_who(t)} ngạc nhiên: “Chắc tờ này người ta thối cho ở chợ…” rồi đổi tờ khác.')
    if name == 'gr_change':
        kit.need(method == 'cash', 'Khách không trả tiền mặt.')
        denom = p.get('denom')
        kit.need(type(denom) is int and denom in DENOMS, 'Mệnh giá không có trong két.')
        kit.need(len(pay['change']) < 40, 'Khay thối tiền đầy rồi.')
        pay['change'].append(denom)
        return dict(message=f'Đặt {denom} xu vào khay thối · đang thối {sum(pay["change"])} xu.')
    if name == 'gr_change_undo':
        kit.need(pay['change'], 'Khay thối tiền đang trống.')
        pay['change'] = [] if p.get('all') is True else pay['change'][:-1]
        return dict(message='Đã cất lại tiền vào két.')
    if name == 'gr_verify':
        kit.need(method == 'transfer', 'Khách không chuyển khoản.')
        pay['verified'] = True
        kit.metric(c, 'transfers_checked')
        arrived = _bank_amount(c, t)
        if arrived and not pay['bank']:
            kit.bank(arrived)   # the shop's speaker reads the transfer out once, when it lands
        pay['bank'] = arrived
        if arrived == 0:
            return dict(message='Loa chưa báo, app ngân hàng của tiệm chưa thấy tiền. Nhờ khách chờ một chút rồi kiểm lại, đừng tin ảnh chụp màn hình.')
        if arrived < t['total']:
            return dict(message=f'App ngân hàng báo nhận +{arrived} xu, thiếu {t["total"] - arrived} xu so với hóa đơn.')
        return dict(message=f'Loa báo: “Tạp Hoá Cô Ba đã nhận {arrived} xu.” Khớp hóa đơn.')
    if name == 'gr_transfer_fix':
        kit.need(method == 'transfer' and pay['verified'] and n['_transfer'] == 'typo' and not pay['fixed'] and (pay['bank'] or 0) < t['total'],
                 'Không có khoản thiếu nào cần nhờ khách chuyển bù.')
        pay['fixed'] = True
        kit.bank(t['total'] - (pay['bank'] or 0))
        pay['bank'] = t['total']
        return dict(message=f'{_who(t)} coi lại điện thoại: “Trời, chị gõ thiếu!” rồi chuyển thêm {t["total"] - pay["screen"]["amount"]} xu. Loa đã báo đủ.')
    if name == 'gr_decline_credit':
        kit.need(method == 'credit', 'Khách không xin ghi sổ.')
        ok, why = _ledger_ok(c, _npc_index(t), t['total'])
        pay['declined'] = True
        pay['tender'] = _tender(t['total'], 'round')
        if ok:
            t['flags']['credit_harsh'] = 1
            row = _data(c)['ledger'][str(_npc_index(t))]
            row['trust'] = max(0, row['trust'] - 1)
            return dict(message=f'Bạn từ chối ghi sổ dù {why}. {_who(t)} hơi chạnh lòng, đưa tiền mặt. Lòng tin còn “{TRUST_NAMES[row["trust"]]}”.')
        t['flags']['credit_ok'] = 1
        return dict(message=f'Bạn giải thích khéo: sổ {why}, tiệm nhỏ nên phải giữ nguyên tắc. {_who(t)} gật đầu, trả tiền mặt.')
    if name == 'gr_pay':
        kit.confirm(p, 'Xác nhận thu tiền và giao hàng cho khách.')
        return _finish(s, c, t)
    raise kit.eng().GameError('Thao tác quầy tạp hóa không hợp lệ.')


def _npc_index(t: dict) -> int:
    return int(t['npc'].rsplit('_', 1)[1]) - 1


def _who(t: dict) -> str:
    return PEOPLE[_npc_index(t)][0]


def _method(t: dict) -> str:
    pay = t['needs']['pay']
    if pay == 'credit' and t['pay']['declined']:
        return 'cash'
    return pay


def _fake_live(t: dict) -> bool:
    return t['needs']['_fake'] and not t['pay']['swapped']


def _bank_amount(c: dict, t: dict) -> int:
    kind = t['needs']['_transfer'] or 'ok'
    pay = t['pay']
    if kind == 'pending' and c['turn'] < pay['ready']:
        return 0
    if kind == 'typo' and not pay['fixed']:
        return pay['screen']['amount']
    return t['total']


def _issues(c: dict, t: dict) -> tuple[list[str], list[str], int]:
    n = t['needs']
    units, weighed = _expected(c, t)
    over, under = [], []
    for item, q in t['scanned'].items():
        want = units.get(item, 0)
        if q > want:
            over.append(f'dư {q - want} {ITEM_INDEX[item]["name"].lower()}')
    for key, w in t['weighed'].items():
        i = int(key)
        real = n['lines'][i]['item']
        if i not in weighed:
            over.append(f'tính tiền {ITEM_INDEX[real]["name"].lower()} mà tiệm hết hàng')
        elif w['plu'] != real:
            over.append(f'hóa đơn ghi {ITEM_INDEX[w["plu"]]["name"].lower()} mà khách mua {ITEM_INDEX[real]["name"].lower()}')
        elif w['grams'] > weighed[i]:
            over.append(f'cân luôn cái rổ {w["grams"] - weighed[i]} g của khách')
    for promo in PROMOS:
        if promo['id'] not in t['promos'] and _discount(promo, t['scanned'].get(promo['item'], 0), _unit(c, t, promo['item'])) > 0:
            over.append(f'chưa trừ khuyến mãi “{promo["label"]}”')
    missing = 0
    for item, q in units.items():
        have = t['scanned'].get(item, 0)
        if have < q:
            under.append(f'chưa tính {q - have} {ITEM_INDEX[item]["name"].lower()}')
            missing += q - have
    for i in weighed:
        if str(i) not in t['weighed']:
            item = n['lines'][i]['item']
            under.append(f'chưa cân {ITEM_INDEX[item]["name"].lower()}')
            missing += _units(item, weighed[i])
    return over, under, missing


def _lock_bill(s: dict, c: dict, t: dict) -> dict:
    n = t['needs']
    kit.need(t['scanned'] or t['weighed'], 'Hóa đơn đang trống. Quét hoặc cân hàng trước.')
    kit.need(not (t.get('haggle') and t['haggle']['state'] == 'ask'), f'{_who(t)} đang chờ bạn trả lời chuyện giá Mây Mart.')
    over, under, missing = _issues(c, t)
    who = _who(t)
    if over:
        t['mistakes'] += 1
        t['flags']['overcharge'] += 1
        return dict(message=f'{who} cầm hóa đơn soi: “Ủa, {"; ".join(over)}?” Sửa lại hóa đơn rồi chốt nhé.', refused=True)
    if under and HONEST.get(_npc_index(t)):
        t['mistakes'] += 1
        t['flags']['undercharge'] += 1
        return dict(message=f'{who} nhắc: “Cháu ơi, {"; ".join(under)} kìa. Tính đủ đi, tiệm nhỏ lời bao nhiêu đâu.”', refused=True)
    t['flags']['missing'] = missing
    t['flags']['out'] = _out_of_stock(c, t)
    t['total'] = _cart_amount(c, t)
    t['stage'] = 'pay'
    pay = t['pay']
    method = _method(t)
    if method == 'cash':
        if sum(pay['tender']) < t['total']:
            pay['tender'] = _tender(t['total'], 'round')
        note = f'{who} đưa {" + ".join(str(x) for x in pay["tender"])} xu.'
        if sum(pay['tender']) == t['total']:
            note += ' Vừa đủ, không cần thối.'
    elif method == 'transfer':
        kind = n['_transfer'] or 'ok'
        amount = t['total'] - (t['total'] % 10 or 10) if kind == 'typo' and t['total'] > 10 else t['total']
        if kind == 'typo' and amount >= t['total']:
            amount = max(0, t['total'] - 1)
        # The sender's app always says "success"; only the shop's bank tells the truth.
        pay['screen'] = dict(amount=amount, status='success', to='TAP HOA CO BA · 0909 ••• 339', memo=f'{who} ck mua hang')
        pay['ready'] = c['turn'] + 2
        note = f'{who} giơ điện thoại: “Chuyển tiền thành công · {amount} xu”. Kiểm loa/app ngân hàng của tiệm trước khi giao hàng.'
    else:
        note = f'{who}: “Ghi sổ giùm nha.” Mở sổ ghi nợ coi hạn mức trước khi quyết.'
    return dict(message=f'Đã chốt bill {t["total"]} xu. ' + note)


def _out_of_stock(c: dict, t: dict) -> int:
    out = 0
    for line in t['needs']['lines']:
        if line.get('weighed'):
            out += 1 if _physical_grams(c, t, line['item'], line['_grams']) < line['_grams'] else 0
        elif not (line['item'] in AGE_LIMITED and _minor(t)) and not _dropped(t, line['item']):
            out += max(0, line['qty'] - _available(c, line['item'], t))
    return out


def _take_upto(c: dict, item: str, qty: int) -> int:
    qty = min(qty, kit.stock(c, item))
    return _take(c, item, qty) if qty > 0 else 0


def _reopen_if_gone(c: dict, t: dict) -> dict | None:
    """Stock can vanish between locking and handing over (a surprise, a discarded lot).
    The customer never pays for goods that are not there: the bill is reopened."""
    units, weighed = _expected(c, t)
    gone = {k: q - units.get(k, 0) for k, q in t['scanned'].items() if q > units.get(k, 0)}
    lines = [k for k in t['weighed'] if int(k) not in weighed]
    if not gone and not lines:
        return None
    for k, extra in gone.items():
        t['scanned'][k] -= extra
        if t['scanned'][k] <= 0:
            t['scanned'].pop(k)
    for k in lines:
        t['weighed'].pop(k)
    t['promos'] = [p for p in t['promos'] if _discount(PROMO_INDEX[p], t['scanned'].get(PROMO_INDEX[p]['item'], 0), _unit(c, t, PROMO_INDEX[p]['item'])) > 0]
    tender = t['pay']['tender']
    t['pay'] = _empty_pay()
    t['pay']['tender'] = tender if t['needs']['pay'] == 'cash' else []
    t['stage'] = 'basket'
    t['total'] = None
    names = ', '.join(ITEM_INDEX[k]['name'] for k in gone) or 'hàng cân'
    return dict(message=f'Kệ vừa hết {names} — bill được mở lại, đã bớt phần không còn hàng. Kiểm lại rồi chốt bill nhé.', refused=True)


def _finish(s: dict, c: dict, t: dict) -> dict:
    reopened = _reopen_if_gone(c, t)
    if reopened:
        return reopened
    pay = t['pay']
    flags = t['flags']
    method = _method(t)
    total = t['total']
    who = _who(t)
    loss = 0
    notes = []
    npc = _npc_index(t)
    due = sum(pay['tender']) - total if method == 'cash' else 0
    given = sum(pay['change']) if method == 'cash' else 0
    if method == 'cash' and given < due and (flags['short_change'] or _careful(t, 'bill', npc)):
        # A careful customer counts the change right here (and, once they have, keeps counting).
        t['mistakes'] += 1
        flags['short_change'] += 1
        return dict(message=f'{who} đếm lại: “Thối thiếu {due - given} xu rồi cháu.” Thêm tiền vào khay thối rồi giao lại.', refused=True)
    # The hand-over: what the customer notices now decides how they take it.
    units, weighed = _expected(c, t)
    _checkout_slips(c, t, units)
    react = cq.react(s, c, t, total, who=who)
    cut = react['cut']
    if react['kind'] in ('refuse', 'walkout'):
        # The customer takes their money back and leaves the basket on the counter.
        t['result'] = dict(method=method, total=total, net=0, loss=0, cost=0)
        t['stage'] = 'done'
        kit.data(c)['customers'] += 1
        kit.complete(s, c, t, 0, f'{who} để lại giỏ hàng, không mua nữa: “{t["title"]}”.')
        return dict(message=f'{who} để lại giỏ hàng trên quầy, không mua nữa. {react["message"]}'.strip())
    short = tip = 0
    if method == 'cash':
        if given < due:
            # Nobody counted at the counter: the customer finds it at home and says so.
            short = due - given
            t['mistakes'] += 1
            cq.slip(t, 'short_home', 2 if short < 10 else 3, f'Về nhà đếm lại mới thấy tiệm thối thiếu {short} xu.',
                    f'thối thiếu {short} xu, khách về nhà mới thấy')
            notes.append(f'{who} nhét tiền thối vào túi rồi đi luôn, không đếm lại — thối thiếu {short} xu.')
            notes.extend(cq._escalate(s, c, t))
        elif given == due and due > 0 and not t['mistakes'] and not cq.slips(t) and react['kind'] == 'accept' and t.get('patience', 100) >= 70:
            tip = _keep(t, 'bill', npc, due)
            if tip:
                # "Khỏi thối": the small change stays on the counter — the customer's own tip, paid once here.
                kit.money(s, c, tip, f'Khách để lại tiền lẻ: {who}', t['id'], 'tip')
                t['tip_given'] = t.get('tip_given', 0) + tip
                notes.append(f'{who} xua tay: “{KEEP_SAY.get(npc, "Khỏi thối, giữ uống nước nha.")}” · +{tip} xu tiền lẻ.')
        if given > due:
            extra = given - due
            t['mistakes'] += 1
            flags['excess'] = extra
            if HONEST.get(npc):
                # Handed back on the spot: a small slip for the review, no money off on top.
                cq.slip(t, 'excess', 1, f'Thối dư {extra} xu, tôi phải đưa trả lại.', f'thối dư {extra} xu')
                notes.append(f'{who} trả lại {extra} xu thối dư: “Cháu thối dư nè, coi chừng lỗ!”')
            else:
                loss += extra
                notes.append(f'Tối kiểm két mới thấy thối dư {extra} xu.')
        if _fake_live(t):
            fake = max(pay['tender'])
            loss += fake
            flags['fake'] = fake
            t['mistakes'] += 1
            notes.append(f'Tối kiểm két: tờ {fake} xu là tiền giả, mất trắng.')
            kit.log(s, c, 'loss', f'Nhận phải tờ {fake} xu giả khi bán cho {who}.', t['npc'], t['id'])
    elif method == 'transfer':
        if not pay['verified'] or not pay['bank']:
            t['mistakes'] += 1
            flags['unverified'] = 1
            notes.append('Chưa thấy tiền về app ngân hàng của tiệm mà đã cho khách đi — may rủi.')
        received = _bank_amount(c, dict(t, pay=dict(pay, ready=0)))
        if not pay['verified'] or not pay['bank']:
            kit.bank(received)   # not heard at the till yet: the speaker reads it now
        if received < total:
            loss += total - received
            flags['transfer_loss'] = total - received
            t['mistakes'] += 1
            notes.append(f'Cuối ngày đối soát: khách chuyển thiếu {total - received} xu.')
    else:
        ok, why = _ledger_ok(c, _npc_index(t), total)
        row = kit.data(c)['ledger'][str(_npc_index(t))]
        if not row['balance']:
            row['since'] = c['day']
        row['balance'] = min(10**6, row['balance'] + total - cut)
        if ok:
            flags['credit_ok'] = 1
            notes.append(f'Ghi sổ {total - cut} xu cho {who} ({why}).')
        else:
            flags['credit_risky'] = 1
            t['mistakes'] += 1
            notes.append(f'Ghi sổ dù {why} — Cô Ba mà biết chắc cằn nhằn.')
        kit.log(s, c, 'ledger', f'Ghi sổ {who}: +{total - cut} xu, tổng nợ {row["balance"]} xu.', t['npc'], t['id'])
    # Goods leave the shop: whatever the customer really took, scanned or not.
    cost = 0
    shrink = 0
    for item, q in units.items():
        taken = _take_upto(c, item, q)
        cost += taken
        unpaid = max(0, q - t['scanned'].get(item, 0))
        if unpaid:
            shrink += unpaid
            kit.waste(c, item, min(60, unpaid), unpaid * ITEM_INDEX[item]['cost'], 'Quét sót — khách mang về chưa tính tiền')
    for i, g in weighed.items():
        item = t['needs']['lines'][i]['item']
        cost += _take_upto(c, item, _units(item, g))
    if shrink:
        notes.append(f'{shrink} món khách mang về mà chưa được tính tiền.')
    net = total - cut - loss + short if method != 'credit' else 0   # short change stays in the drawer
    d = kit.data(c)
    d['sales'] += total - cut
    d['day_sales'] += total - cut
    d['customers'] += 1
    kit.metric(c, 'gr_checkouts')
    if method == 'credit':
        kit.metric(c, 'gr_credit_sales')
    c['life']['consumed_cost'] += cost
    t['result'] = dict(method=method, total=total, net=net, loss=loss, cost=cost)
    if short:
        t['result']['short'] = short
    if tip:
        t['result']['tip'] = tip
    t['stage'] = 'done'
    reward = max(0, net)
    kit.complete(s, c, t, reward, f'Bạn đã tính tiền cho {who}: “{t["title"]}”.')
    if net < 0 and min(-net, c['money']) > 0:
        kit.money(s, c, -min(-net, c['money']), 'Thất thoát tại quầy: ' + t['title'], t['id'], 'loss')
    head = {'cash': f'Đã thu tiền mặt · +{reward} xu', 'transfer': f'Đã nhận chuyển khoản · +{reward} xu', 'credit': f'Đã ghi sổ {total - cut} xu'}[method]
    if react['message']:
        notes.insert(0, react['message'])
    return dict(message=head + '. ' + ' '.join(notes), celebrate=not t['mistakes'] and not cq.slips(t))


DATED = ('milk', 'egg', 'bread')   # goods with a printed use-by date the customer reads at home


def _expired_sold(c: dict, units: dict) -> list[str]:
    """Dated goods the customer takes home from a lot whose date is today (FIFO sells those first)."""
    out = []
    for item, q in units.items():
        if item in DATED and q > 0 and _today_in_pick(c, item, q):
            out.append(ITEM_INDEX[item]['name'])
    return out


def _checkout_slips(c: dict, t: dict, units: dict) -> None:
    """Mistakes the customer noticed at this till, in their own words (recorded at the hand-over)."""
    f = t['flags']
    if _minor_beer(t):
        cq.slip(t, 'minor_beer', 3, f'Ba con la quá trời: con mới {t["needs"]["_age"]} tuổi mà tiệm vẫn bán bia, không hỏi giấy tờ gì hết.',
                'bán bia cho người chưa đủ 18 tuổi', safety=True)
    old = _expired_sold(c, units)
    if old:
        cq.slip(t, 'expired', 3, f'{old[0]} ghi hạn dùng đúng hôm nay mà tiệm vẫn bán cho tôi.',
                f'bán {old[0].lower()} hết hạn hôm nay', safety=True)
    if f['short_change']:
        cq.slip(t, 'short_change', 2, 'Thối thiếu tiền, tôi phải đếm lại mới thấy.', 'thối thiếu tiền')
    if f['overcharge']:
        cq.slip(t, 'overcharge', 1 if f['overcharge'] == 1 else 2, 'Hóa đơn tính dư, tôi phải tự soi ra mới được sửa lại.',
                'hóa đơn tính dư, khách phải tự soi')
    if f['undercharge']:
        cq.slip(t, 'undercharge', 1, 'Tính thiếu tiền, tôi phải nhắc mới tính lại cho đủ.', 'tính thiếu, khách phải nhắc')


# ---------------------------------------------------------------- shelf
def _shelf_ids(t: dict) -> list[str]:
    return [x['id'] for x in t['needs']['lots']] + [t['needs']['new']['id']]


def _lot_qty(t: dict, lot: str) -> int:
    n = t['needs']
    return n['new']['qty'] if lot == n['new']['id'] else next(x['qty'] for x in n['lots'] if x['id'] == lot)


def _left(c: dict, t: dict, lot: str) -> int:
    return t['day'] + t['needs']['_exps'][lot] - c['day']


def _shelf_action(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    sh = t['shelf']
    if sh['tag'] is None:
        quote(c, t)
    item = ITEM_INDEX[n['item']]
    kit.start_work(t)
    if name == 'gr_check':
        lot = kit.one_of(p.get('lot'), sh['order'] + sh['cart'], 'Lô này không còn trên kệ.')
        kit.need(lot not in sh['checked'], 'Đã đọc hạn lô này.')
        sh['checked'].append(lot)
        left = _left(c, t, lot)
        state = 'đã QUÁ HẠN' if left < 0 else 'hết hạn HÔM NAY' if left == 0 else f'còn {left} ngày'
        return dict(message=f'Lô {lot}: HSD ngày {t["day"] + n["_exps"][lot]} — {state}.')
    if name == 'gr_pull':
        lot = kit.one_of(p.get('lot'), sh['order'], 'Chỉ rút được lô đang bày trên kệ.')
        kit.need(lot in sh['checked'], 'Đọc hạn lô này trước khi rút.')
        sh['order'].remove(lot)
        sh['pulled'].append(lot)
        if lot in sh['marked']:
            sh['marked'].remove(lot)
        qty = _lot_qty(t, lot)
        left = _left(c, t, lot)
        kit.waste(c, n['item'], min(60, qty), qty * item['cost'], 'Rút khỏi kệ: hết hạn' if left <= 0 else 'Rút nhầm hàng còn hạn')
        if left > 0:
            t['mistakes'] += 1
            return dict(message=f'Rút lô {lot} dù còn {left} ngày — hàng tốt bị bỏ, ghi hao hụt.')
        return dict(message=f'Đã rút lô {lot} ({qty} {item["unit"]}) khỏi kệ, ghi hao hụt. Không bán hàng hết hạn!')
    if name == 'gr_mark':
        lot = kit.one_of(p.get('lot'), sh['order'] + sh['cart'], 'Lô này không còn trên kệ.')
        kit.need(lot in sh['checked'], 'Đọc hạn lô này trước khi dán tem giảm giá.')
        kit.need(lot not in sh['marked'], 'Lô này đã có tem giảm giá.')
        sh['marked'].append(lot)
        left = _left(c, t, lot)
        if not 1 <= left <= 2:
            t['mistakes'] += 1
            return dict(message=f'Dán tem giảm {MARKDOWN}% cho lô {lot} (còn {left} ngày) — không đúng quy định của tiệm.')
        return dict(message=f'Dán tem “Giảm {MARKDOWN}% · cận date” cho lô {lot}.')
    if name == 'gr_place':
        order = p.get('order')
        allowed = sh['order'] + sh['cart']
        kit.need(isinstance(order, list) and len(order) == len(allowed) and all(isinstance(x, str) for x in order)
                 and sorted(order) == sorted(allowed), 'Xếp đủ mọi lô còn lại lên kệ, mỗi lô một lần.')
        sh['order'] = list(order)
        sh['cart'] = []
        sh['placed'] = True
        return dict(message='Đã xếp kệ: ' + ' → '.join(order) + ' (trước → sau).')
    if name == 'gr_retag':
        price = _price(c, n['item'])
        kit.need(sh['tag'] != price, 'Tem giá đang khớp bảng giá, không cần in lại.')
        sh['tag'] = price
        sh['retagged'] = True
        return dict(message=f'In lại tem giá: {price} xu/{item["unit"]}.')
    if name == 'gr_shelf_done':
        kit.confirm(p, 'Xác nhận đã xếp xong kệ.')
        kit.need(sh['placed'] and not sh['cart'], 'Xếp thùng hàng mới lên kệ trước (bấm “Xếp kệ theo thứ tự”).')
        problems = _shelf_problems(c, t)
        t['mistakes'] += sum(len(v) for v in problems.values())
        t['result'] = {k: len(v) for k, v in problems.items()}
        kit.data(c)['shelves'] += 1
        kit.metric(c, 'gr_shelves')
        rotated = not problems['fifo'] and _unrotated(c, n['item'])
        if rotated:
            _rotate(c, n['item'])   # the real shelf of this item is put in order too
        if problems['expired']:
            cq.slip(t, 'shelf_expired', 2, 'Lô hết hạn vẫn nằm trên kệ, khách mà mua phải thì tiệm mang tiếng.', 'hàng hết hạn còn trên kệ')
        if problems['price']:
            cq.slip(t, 'shelf_price', 1, 'Tem giá trên kệ lệch bảng giá, khách hỏi là kẹt.', 'tem giá lệch bảng giá')
        react = cq.react(s, c, t, SHELF_PAY, who=PEOPLE[0][0])
        kit.complete(s, c, t, react['pay'], f'Bạn đã xếp {t["title"].lower()} giúp Cô Ba.')
        issues = [x for v in problems.values() for x in v]
        return dict(message=f'Cô Ba đi một vòng kiểm kệ · +{react["pay"]} xu. ' + ('Kệ đẹp, đúng hạn, đúng giá!' if not issues else 'Cô nhắc: ' + '; '.join(issues) + '.')
                    + (f' Kệ {item["name"]} ngoài tiệm cũng đã xoay: lô cũ ra trước.' if rotated else '')
                    + (' ' + react['message'] if react['message'] else ''), celebrate=not issues)
    raise kit.eng().GameError('Thao tác kệ hàng không hợp lệ.')


def _shelf_problems(c: dict, t: dict) -> dict:
    sh = t['shelf']
    n = t['needs']
    out = dict(expired=[], markdown=[], fifo=[], price=[])
    for lot in sh['order']:
        left = _left(c, t, lot)
        if left <= 0:
            out['expired'].append(f'lô {lot} hết hạn vẫn nằm trên kệ')
        elif left <= 2 and lot not in sh['marked']:
            out['markdown'].append(f'lô {lot} cận date chưa dán tem giảm giá')
    exps = [n['_exps'][lot] for lot in sh['order']]
    if exps != sorted(exps):
        out['fifo'].append('lô mới đang nằm trước lô cũ')
    if sh['tag'] != _price(c, n['item']):
        out['price'].append(f'tem giá {sh["tag"]} xu không khớp bảng giá {_price(c, n["item"])} xu')
    return out


# ======================================================================== v0.5 · generator 2
GEN = 2
LEGACY = 10 ** 8          # same band as kit.LEGACY_TURN: serials of tasks saved before generator 2
RIVAL_DAY = 3             # Mây Mart hands out its first flyer on this day
BULK_OFFERS = (0, 5, 10, 15)
BULK_DEPOSIT = 30         # percent paid when the price is agreed
CLEAR_PERCENT = 70        # near-date clearance price, percent of the tag
STAT_KEYS = ('rush', 'bulk', 'haggles', 'matched', 'fines', 'inspections', 'cleared', 'walkouts',
             'bad_debt', 'plans', 'rotated', 'lists', 'lists_missed')

# Generator 2 speaks to the player without assuming gender (generator 1 keeps its saved text).
NEUTRAL = {'Chị ơi em mua đồ ăn vặt!': 'Cho em mua đồ ăn vặt với ạ!'}

MODS = [
    dict(id='normal', emoji='🏪', name='Ngày thường', text='Xóm đi chợ như mọi ngày.', weight=3),
    dict(id='hot', emoji='🥵', name='Nắng nóng 37°C', text='Nước ngọt, bia, sữa bán chạy; tủ mát chạy hết công suất.', weight=2, min_day=2),
    dict(id='rain', emoji='🌧️', name='Mưa dầm cả ngày', text='Ít ai chạy qua Mây Mart; ai ghé cũng mua mì, trứng để trữ.', weight=2, min_day=2),
    dict(id='exam', emoji='📚', name='Mùa thi học kỳ', text='Học sinh ghé mua sữa, bánh mì, snack từ sáng sớm.', weight=1, min_day=2),
    dict(id='payday', emoji='💰', name='Ngày lãnh lương xưởng may', text='Giỏ hàng to hơn, hàng xóm ghé trả sổ nợ.', weight=2, min_day=3),
    dict(id='sale', emoji='📣', name='Mây Mart xả hàng', text='Siêu thị đầu hẻm giảm sâu vài món, khách nào cũng so giá.', weight=2, min_day=RIVAL_DAY),
    dict(id='wedding', emoji='💒', name='Mùa cưới trong hẻm', text='Nhà nào cũng có đám, dễ có đơn sỉ bia nước.', weight=1, min_day=3),
]
MOD_INDEX = {m['id']: m for m in MODS}
RIVAL_ITEMS = ('noodle', 'soda', 'beer', 'milk', 'snack', 'oil', 'fishsauce', 'soap')
# Neighbours who bring up the Mây Mart flyer (percent chance) and who still buy when the price is held.
SENSITIVE = {2: 55, 3: 45, 4: 70, 5: 80, 6: 60}
LOYAL = {2: 40, 3: 20, 4: 65, 5: 25, 6: 45}
HAGGLE_ASK = {
    2: 'Mây Mart bán {item} có {theirs} xu thôi. Em bớt cho chị bằng giá đó được không?',
    3: 'Ủa bên Mây Mart {item} có {theirs} xu hà. Bớt cho em đi mà!',
    4: 'Tờ rơi siêu thị ghi {item} {theirs} xu kìa cháu. Bà mua ở đây thì bớt cho bà chứ?',
    5: 'Mây Mart đang bán {item} {theirs} xu. Tiệm để {ours} xu là cao đó em.',
    6: 'Bên Mây Mart {item} {theirs} xu, chị lấy thường xuyên, em để giá đó luôn nha.',
}
# (npc, title, opening, lines, pay, tender style, note, extras) — baskets that only happen on that kind of day.
MOD_CHECKOUTS = {
    'hot': [(1, 'Đội thợ hồ giải khát', 'Nắng muốn xỉu, bán chú nước cho anh em thợ hồ!', [('soda', 12), ('beer', 6)], 'cash', 'big', 'Lấy lon nào mát nhất giùm chú.', {}),
            (5, 'Nắng quá mua sữa lạnh', 'Anh lấy sữa lạnh với nước ngọt, chuyển khoản nha.', [('milk', 4), ('soda', 4)], 'transfer', None, 'Lốc sữa có khuyến mãi đúng không em?', dict(transfer='ok'))],
    'rain': [(2, 'Mưa dầm trữ đồ ăn', 'Mưa hoài, chị trữ ít mì với trứng cho mấy đứa nhỏ.', [('noodle', 10), ('egg', 10)], 'cash', 'round', 'Mì lấy chẵn 10 gói cho được khuyến mãi.', {}),
             (4, 'Bà Sáu đội mưa ra tiệm', 'Mưa ướt hết, cháu bán bà gói mì với ít rau.', [('noodle', 3), ('greens', 'w', 300, 150)], 'cash', 'round', 'Rau bà để trong rổ nè.', {})],
    'exam': [(3, 'Tí ôn thi cả đêm', 'Cho em mua đồ ăn khuya ôn thi với!', [('milk', 2), ('bread', 1), ('snack', 2)], 'cash', 'exact', 'Em đưa đủ tiền lẻ nè.', {}),
             (2, 'Bữa sáng ngày thi', 'Con chị thi sáng nay, chị lấy sữa với bánh mì.', [('milk', 4), ('bread', 2), ('egg', 2)], 'cash', 'round', 'Lốc sữa 4 hộp có giảm giá đúng không em?', {})],
    'payday': [(2, 'Lãnh lương đi chợ lớn', 'Lãnh lương rồi, chị mua đồ cả tuần luôn!', [('rice', 'w', 5000, 0), ('oil', 2), ('fishsauce', 1), ('egg', 10), ('milk', 4)], 'cash', 'round', 'Gạo 5 ký, sữa lấy nguyên lốc.', {}),
               (6, 'Quán cơm nhập đầu tuần', 'Chị lấy đồ cho quán, chuyển khoản liền.', [('rice', 'w', 8000, 0), ('oil', 3), ('egg', 20)], 'transfer', None, 'Chuyển rồi đó em coi giùm.', dict(transfer='pending'))],
    'sale': [(5, 'Anh Khoa so giá từng món', 'Mây Mart đang giảm giá đó nha, tính kỹ giùm anh.', [('noodle', 5), ('soda', 6), ('snack', 2)], 'transfer', None, 'Anh có tờ rơi Mây Mart đây nè.', dict(transfer='ok'))],
    'wedding': [(1, 'Chú Bảy mua quà mừng cưới', 'Đi đám cưới cháu, chú mua ít đồ làm quà.', [('oil', 2), ('fishsauce', 2), ('soap', 2)], 'cash', 'round', 'Gói gọn gàng giùm chú nha.', {})],
}
# Rush-hour customers: (npc, items, tender style, what they say).
RUSH = [
    (5, (('milk', 1), ('bread', 1)), 'exact', 'Hộp sữa với ổ bánh mì, lẹ giùm anh nha.'),
    (3, (('snack', 2), ('soda', 1)), 'round', 'Em mua lẹ rồi còn chạy đi học thêm!'),
    (2, (('egg', 6), ('noodle', 2)), 'round', 'Nửa chục trứng với 2 gói mì nha em.'),
    (1, (('beer', 2), ('snack', 1)), 'big', 'Hai lon bia mát, chú trả tờ lớn nghen.'),
    (4, (('soap', 1), ('egg', 4)), 'round', 'Bà lấy cục xà bông với 4 quả trứng.'),
    (6, (('fishsauce', 1), ('noodle', 3)), 'round', 'Chai mắm với 3 gói mì, lẹ lẹ giùm chị!'),
    (3, (('beer', 2), ('soda', 1)), 'round', 'Ba con sai mua 2 lon bia với lon nước ngọt ạ.'),
    (5, (('soda', 2), ('snack', 1)), 'exact', 'Anh đưa đủ tiền lẻ luôn nè.'),
    (2, (('milk', 2), ('bread', 2)), 'round', 'Sữa với bánh mì cho tụi nhỏ nha em.'),
    (1, (('noodle', 2), ('egg', 2)), 'round', 'Chú ăn mì trứng cho lẹ, tính giùm chú.'),
]
RUSH_TITLES = {
    'normal': ('Giờ tan tầm', 'Năm giờ chiều, công nhân tan ca ùa vào tiệm. Tính nhanh, thối đúng — ai chờ lâu quá sẽ bỏ về.'),
    'hot': ('Trưa nắng, ai cũng khát', 'Nắng như đổ lửa, cả hẻm ghé mua nước. Hàng chờ dài tới cửa!'),
    'exam': ('Học trò ghé trước giờ thi', 'Chuông sắp reng, đám học trò chen nhau mua đồ ăn sáng. Lẹ tay nào!'),
    'payday': ('Chiều lãnh lương', 'Xưởng may vừa phát lương, ai cũng ghé tiệm mua đồ. Hàng chờ kéo dài!'),
    'rain': ('Tạnh mưa, khách ùa vào', 'Mưa vừa ngớt, mọi người tranh thủ ghé mua đồ trước cơn mưa tới.'),
}
# Bulk orders: (npc, title, opening, lines, note, min_day).
BULKS = [
    (1, 'Đám cưới con gái chú Bảy', 'Chủ nhật chú gả con gái! Đặt bia nước ở tiệm mình cho tiện, tính giá sỉ giùm chú nha.',
     (('beer', 48), ('soda', 24)), 'Chiều nay chú cho xe ba gác qua chở.', 2),
    (6, 'Quán cơm tấm nhập hàng tuần', 'Chị lấy sỉ cho quán: gạo, dầu, mắm, trứng. Báo giá sỉ giùm chị.',
     (('rice', 20), ('oil', 4), ('fishsauce', 4), ('egg', 40)), 'Giao trước giờ cơm chiều nha em.', 2),
    (2, 'Đám giỗ ba chị Lan', 'Mai giỗ ba chị, chị đặt trước đồ nấu với nước mời khách.',
     (('soda', 24), ('noodle', 20), ('fishsauce', 2), ('oil', 2)), 'Chị gửi cọc trước, chiều chị qua lấy.', 3),
    (5, 'Công ty anh Khoa đi dã ngoại', 'Team anh đi picnic cuối tuần, cần nước với đồ ăn vặt. Có giá sỉ không em?',
     (('soda', 36), ('snack', 20), ('milk', 12)), 'Anh chuyển khoản, nhớ ghi phiếu giao hàng nha.', 3),
    (4, 'Mâm cơm rằm của bà Sáu', 'Rằm này bà làm mâm cúng, cháu soạn giùm bà đủ món nha.',
     (('rice', 5), ('egg', 20), ('oil', 1), ('fishsauce', 1), ('soda', 12)), 'Chiều thằng cháu bà chạy qua lấy.', 2),
]


def _tier(day: int) -> int:
    return 0 if day <= 2 else 1 if day <= 5 else 2 if day <= 9 else 3


def _mod_raw(day: int) -> dict:
    pool = [m for m in MODS if m.get('min_day', 1) <= day]
    x = kit.rng(ID, 'mood', day).random() * sum(m['weight'] for m in pool)
    for m in pool:
        x -= m['weight']
        if x < 0:
            return m
    return pool[-1]


def mod_of(day: int) -> dict:
    """The luck of the day — decided by the day alone, so a reload never rerolls it."""
    if day <= 1:
        return MODS[0]
    m = _mod_raw(day)
    if m['id'] != 'normal' and _mod_raw(day - 1)['id'] == m['id']:
        return MODS[0]   # the same special day never comes twice in a row
    return m


def _floor_price(item: str) -> int:
    return round(PRICES[item] * .75)


def _cap_price(item: str) -> int:
    return round(PRICES[item] * 1.25)


def rival(day: int) -> dict:
    """Today's Mây Mart flyer: {item: price}. Never below what the shop may charge."""
    if day < RIVAL_DAY:
        return {}
    sale = mod_of(day)['id'] == 'sale'
    r = kit.rng(ID, 'rival', day)
    out = {}
    for item in r.sample(RIVAL_ITEMS, 3 if sale else 2):
        pct = r.choice((75, 80, 85) if sale else (80, 85, 90))
        out[item] = max(_floor_price(item), PRICES[item] * pct // 100)
    return out


def _bulk_slot(day: int, mod: str):
    if day < 2:
        return None
    if mod == 'wedding':
        return 1
    if day >= 4 and kit.rng(ID, 'bulk-day', day).random() < 0.3 + 0.05 * _tier(day):
        return 1
    return None


RUSH_MODS = ('hot', 'exam', 'payday', 'rain')


def _kind(day: int, slot: int, mod: str) -> str:
    if slot == _bulk_slot(day, mod):
        return 'bulk'
    if day >= 2 and (slot == 2 and (mod in RUSH_MODS or kit.rng(ID, 'rush-day', day).random() < 0.5)
                     or slot == 5 and mod in RUSH_MODS):
        return 'rush'
    if (day * 3 + slot) % 4 == 1:
        return 'shelf'
    return 'checkout'


def _nth(day: int, slot: int, mod: str, kind: str) -> int:
    """How many tasks of this kind the day already dealt before this slot."""
    return sum(1 for x in range(slot) if _kind(day, x, mod) == kind)


def _deck(tag: str, day: int, n: int) -> list[int]:
    """A per-day shuffled order, so one day never repeats a customer or a shelf."""
    order = list(range(n))
    kit.rng(ID, 'deck', tag, day).shuffle(order)
    return order


def _checkout_script(day: int, slot: int, mod: str):
    pool = [x[:8] for x in CHECKOUTS if x[8] <= day]
    deck = [pool[i] for i in _deck('checkout', day, len(pool))]
    for k, extra in enumerate(MOD_CHECKOUTS.get(mod, [])):
        deck.insert(min(len(deck), 2 * k), extra)   # the day's mood shows at the 1st and 3rd customer
    return deck[_nth(day, slot, mod, 'checkout') % len(deck)]


def _make_v2(day: int, slot: int, serial: int) -> dict:
    rng = kit.rng(ID, 'v2', day, slot)
    mod = mod_of(day)['id']
    kind = _kind(day, slot, mod)
    if kind == 'rush':
        t = _make_rush(day, slot, serial, rng, mod, second=_nth(day, slot, mod, 'rush') > 0)
    elif kind == 'bulk':
        t = _make_bulk(day, slot, serial, rng, mod)
    elif kind == 'shelf':
        shelves = [x for x in SHELVES if x[3] <= day]
        order = _deck('shelf', day, len(shelves))
        title, opening, item, _ = shelves[order[_nth(day, slot, mod, 'shelf') % len(shelves)]]
        t = _make_shelf(day, slot, serial, rng, title, opening, item)
    else:
        t = _checkout(day, slot, serial, rng, _checkout_script(day, slot, mod), neutral=True)
        _add_haggle(t, day, rng, mod)
    t['gen'] = GEN
    return t


def _add_haggle(t: dict, day: int, rng, mod: str) -> None:
    t['haggle'] = None
    flyer = rival(day)
    npc = _npc_index(t)
    if not flyer or npc not in SENSITIVE:
        return
    items = [x['item'] for x in t['needs']['lines'] if not x.get('weighed') and x['item'] in flyer
             and not (x['item'] in AGE_LIMITED and AGE[npc] < 18)]
    if not items:
        return
    chance = 100 if mod == 'sale' else SENSITIVE[npc] // (2 if mod == 'rain' else 1)
    if rng.randrange(100) < chance:
        t['needs']['_haggle'] = items[0]
        t['needs']['_loyal'] = rng.randrange(100) < LOYAL[npc]


# ---------------------------------------------------------------- price war at the till
def _maybe_haggle(c: dict, t: dict, item: str) -> str:
    n = t['needs']
    if n.get('_haggle') != item or t.get('haggle') is not None:
        return ''
    theirs = rival(c['day']).get(item)
    today = _data(c)['today']
    if theirs is None or today['calm'] and today['day'] == c['day']:
        return ''
    bond = _data(c)['lists'].get(str(_npc_index(t)))
    if bond and bond['bond'] >= BOND_CALM:
        return ''   # a close regular no longer brings the flyer to the till
    ours, who = _price(c, item), _who(t)
    if ours <= theirs:
        t['haggle'] = dict(item=item, ours=ours, theirs=theirs, state='fair')
        return f'{who} liếc tờ rơi Mây Mart rồi gật gù: “Giá ngang siêu thị, mua ở đây cho gần.”'
    t['haggle'] = dict(item=item, ours=ours, theirs=theirs, state='ask')
    _data(c)['stats']['haggles'] += 1
    return f'{who}: “' + HAGGLE_ASK[_npc_index(t)].format(item=ITEM_INDEX[item]['name'].lower(), theirs=theirs, ours=ours) + '”'


def _haggle(s: dict, c: dict, t: dict, p: dict) -> dict:
    h = t.get('haggle')
    kit.need(h and h['state'] == 'ask', 'Khách không hỏi gì về giá.')
    answer = kit.one_of(p.get('answer'), ('match', 'hold'), 'Chọn bớt bằng giá Mây Mart hoặc giữ giá.')
    who, name = _who(t), ITEM_INDEX[h['item']]['name'].lower()
    if answer == 'match':
        h['state'] = 'match'
        _data(c)['stats']['matched'] += 1
        return dict(message=f'Bạn bớt {name} xuống {h["theirs"]} xu cho {who}. {who}: “Vậy mới được chứ, lần sau ghé tiếp!”')
    if t['needs'].get('_loyal'):
        h['state'] = 'hold'
        return dict(message=f'Bạn giữ giá {h["ours"]} xu. {who} thở dài: “Thôi lỡ ra tới đây rồi, lấy luôn.”')
    h['state'] = 'dropped'
    t['scanned'].pop(h['item'], None)
    t['promos'] = [x for x in t['promos'] if PROMO_INDEX[x]['item'] != h['item']]
    return dict(message=f'Bạn giữ giá {h["ours"]} xu. {who}: “Vậy thôi, lát ghé Mây Mart mua {name}.” Món này bị bỏ khỏi giỏ.')


# ---------------------------------------------------------------- rush hour queue
# The queue is the normal counter, only faster: ring each basket line up on the till (the till adds
# it up), the customer hands over cash, count the change out of the drawer into the tray and hand
# it over. A mistake lands on the customer it happened to, the way that person takes it: careful
# people count the change and read the till screen at the counter (COUNTS), honest ones hand back
# extra change (HONEST), the others find out at home and say so in their own review.
OFFER_KEYS = ('i', 'units', 'scanned', 'charged', 'tender', 'change', 'miss', 'counted', 'extra')
LOG_KEYS = ('i', 'status', 'paid', 'tip', 'stars', 'note', '_later')
# What went wrong with the customer at the counter: an overcharge or an undercharge they pointed
# out, short change they counted, goods they took home without paying (nobody said a word).
MISS = ('over', 'under', 'short', 'quiet')


def _empty_rush() -> dict:
    return dict(i=0, start=None, served=0, left=0, cash=0, loss=0, ages={}, offer=None, log=[],
                flags=dict(over=0, under=0, short=0, excess=0, minor=0))


def _new_offer(i: int, units: dict, scanned: dict | None = None, miss: list | None = None) -> dict:
    return dict(i=i, units=dict(units), scanned=dict(scanned or {}), charged=None, tender=[], change=[],
                miss=list(miss or []), counted=0, extra=0)


def _row(i: int, status: str, paid: int = 0, tip: int = 0, stars=None, note: str = '', later: str = '') -> dict:
    """One customer of the queue: served / left / empty, what stayed in the till, the small change
    they left as a tip, their own rating line, and the review they write once home (hidden)."""
    return dict(i=i, status=status, paid=paid, tip=tip, stars=stars, note=note[:200], _later=later[:300])


def _rush_ready(t: dict) -> dict | None:
    """Old saves (v0.9: pick one of three totals, then one of three change amounts) move to the
    till-and-tray format in place, once. A customer whose total was already picked keeps it: the
    goods left the shelf then and the money is on the counter; the change is now counted from the tray."""
    r = t.get('rush')
    if not isinstance(r, dict):
        return r
    for x in r.get('log') or []:
        if isinstance(x, dict) and 'tip' not in x:
            x.update(tip=0, stars=5 if x.get('status') == 'served' else None, note='', _later='')
    o = r.get('offer')
    if isinstance(o, dict) and 'totals' in o:
        charged = o.get('charged')
        new = _new_offer(o.get('i', r.get('i', 0)), o.get('units') or {}, o.get('units') if charged is not None else None)
        if charged is not None:
            new.update(charged=charged, tender=list(o.get('tender') or []))
        r['offer'] = new
    return r


def _make_rush(day: int, slot: int, serial: int, rng, mod: str, second: bool = False) -> dict:
    tier = _tier(day)
    n = 3 + (1 if tier >= 2 else 0) + (1 if mod in ('hot', 'exam', 'payday') else 0)
    pool = [r for r in RUSH if tier >= 1 or not (AGE[r[0]] < 18 and any(i in AGE_LIMITED for i, _ in r[1]))]
    queue = []
    for k in rng.sample(range(len(pool)), min(n, len(pool))):
        npc, items, style, note = pool[k]
        beer = any(i in AGE_LIMITED for i, _ in items)
        queue.append(dict(npc=npc, items=[[i, q] for i, q in items], style=style, note=note, _age=AGE[npc] if beer else None))
    title, opening = RUSH_TITLES['normal'] if second else RUSH_TITLES.get(mod, RUSH_TITLES['normal'])
    needs = dict(queue=queue, pace=3 if tier == 0 else 2, slack=2)
    return kit.base_task(ID, day, slot, serial, 0, title, opening, kind='rush', needs=needs, rush=_empty_rush(), result=None)


def _deadline(t: dict, i: int) -> int:
    n = t['needs']
    return t['rush']['start'] + pt.longer(n['pace'] * (i + 1) + n['slack'])  # PATIENCE_FACTOR: each place in the queue waits a bit longer


def _rush_units(c: dict, t: dict, i: int) -> dict:
    """What customer i can take home now: their basket, limited by the shelf and by the ID check."""
    q = t['needs']['queue'][i]
    seen = t['rush']['ages'].get(str(i))
    units = {}
    for item, qty in q['items']:
        if item in AGE_LIMITED and seen is not None and seen < 18:
            continue
        u = min(qty, _available(c, item, t) - units.get(item, 0))
        if u > 0:
            units[item] = units.get(item, 0) + u
    return units


def _till(c: dict, scanned: dict) -> int:
    """What the till adds up: every line rung up at the price on the shelf tag. (No promotions:
    a rush basket never reaches a promotion's quantity.)"""
    return sum(_price(c, k) * q for k, q in scanned.items())


def _careful(t: dict, key, npc: int) -> bool:
    """Does this customer count the change and read the till screen at the counter? Seeded by the
    task (and the place in the queue), so the same person always does the same: never re-rolled."""
    return kit.rng(ID, t['id'], 'count', key).randrange(100) < COUNTS.get(npc, 50)


def _keep(t: dict, key, npc: int, due: int) -> int:
    """The small change a customer leaves on the counter (“khỏi thối”), or 0. Seeded like _careful."""
    small = due if due <= KEEP_MAX else due % 10
    if small <= 0 or kit.rng(ID, t['id'], 'keep', key).randrange(100) >= KEEP.get(npc, 0):
        return 0
    return small


def _rush_offer(c: dict, t: dict) -> None:
    """The basket of the customer at the counter, as the shelf and the ID check allow right now.
    Recomputed when the shelf changes; what is already rung up stays on the till, and once the
    money is on the counter nothing moves."""
    _rush_ready(t)
    r, queue = t['rush'], t['needs']['queue']
    if r['start'] is None or r['i'] >= len(queue):
        r['offer'] = None
        return
    o = r['offer']
    same = isinstance(o, dict) and o.get('i') == r['i']
    if same and o['charged'] is not None:
        return   # money already on the counter: keep the numbers
    r['offer'] = _new_offer(r['i'], _rush_units(c, t, r['i']), o['scanned'] if same else None, o['miss'] if same else None)


def _rush_expire(c: dict, t: dict) -> int:
    r, queue = t['rush'], t['needs']['queue']
    gone = 0
    while (r['start'] is not None and r['i'] < len(queue) and c['turn'] > _deadline(t, r['i'])
           and not (r['offer'] and r['offer']['i'] == r['i'] and r['offer']['charged'] is not None)):
        r['left'] += 1
        r['log'].append(_row(r['i'], 'left'))
        r['i'] += 1
        r['offer'] = None
        gone += 1
    if gone:
        _rush_offer(c, t)
    return gone


def _miss(o: dict, code: str) -> None:
    if code not in o['miss']:
        o['miss'].append(code)


def _rush_action(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    _rush_ready(t)
    r, queue = t['rush'], t['needs']['queue']
    if r['start'] is None:
        r['start'] = c['turn']
    kit.start_work(t)
    gone = _rush_expire(c, t)
    note = f'{gone} khách chờ lâu quá đã bỏ về. ' if gone else ''
    if r['i'] >= len(queue):
        return dict(message=note + _rush_finish(s, c, t), refused=bool(gone))
    if gone:
        # The tap was meant for someone who has just walked out: the next customer steps up first.
        return dict(message=note + f'Mời {PEOPLE[queue[r["i"]]["npc"]][0]}!', refused=True)
    if r['offer'] is None or r['offer']['i'] != r['i']:
        _rush_offer(c, t)
    i, o, q = r['i'], r['offer'], queue[r['i']]
    who = PEOPLE[q['npc']][0]
    if name == 'gr_rush_id':
        kit.need(any(k in AGE_LIMITED for k, _ in q['items']), f'{who} không mua bia, không cần xem giấy tờ.')
        kit.need(str(i) not in r['ages'], 'Đã kiểm tuổi khách này rồi.')
        kit.need(o['charged'] is None, 'Đã tính tiền khách này rồi.')
        age = q['_age']
        r['ages'][str(i)] = age
        kit.metric(c, 'id_checks')
        if age < 18:
            r['flags']['minor'] += 1
            _rush_offer(c, t)
            rung = r['offer']['scanned'].get('beer')
            return dict(message=f'{who} mới {age} tuổi: không bán bia. Bạn nói nhỏ nhẹ, chỉ bán phần còn lại.'
                        + (f' Xóa {rung} lon bia khỏi máy tính tiền nhé.' if rung else ''))
        return dict(message=f'{who} {age} tuổi, đủ tuổi mua bia.')
    if name == 'gr_rush_scan':
        kit.need(o['charged'] is None, 'Đã tính tiền khách này rồi: thối tiền rồi giao hàng.')
        item = kit.one_of(p.get('item'), ITEM_INDEX, 'Mặt hàng không có trong tiệm.')
        kit.need(item not in WEIGHED, 'Giờ cao điểm chỉ bán hàng đóng gói, không cân ký.')
        qty = kit.integer(p.get('qty', 1), 1, 30)
        seen = r['ages'].get(str(i))
        kit.need(not (item in AGE_LIMITED and seen is not None and seen < 18), f'{who} chưa đủ 18 tuổi: không bán bia. Để lon bia lại kệ.')
        it = ITEM_INDEX[item]
        have = _available(c, item, t)
        kit.need(o['scanned'].get(item, 0) + qty <= have, f'Kệ chỉ còn {have} {it["unit"]} {it["name"]}.')
        kit.need(sum(o['scanned'].values()) + qty <= 60, 'Hóa đơn dài quá rồi.')
        o['scanned'][item] = o['scanned'].get(item, 0) + qty
        return dict(message=f'Bíp! {it["name"]} ×{qty} · {_price(c, item) * qty} xu. Máy tính tiền: {_till(c, o["scanned"])} xu.')
    if name == 'gr_rush_void':
        kit.need(o['charged'] is None, 'Đã tính tiền khách này rồi: thối tiền rồi giao hàng.')
        item = kit.one_of(p.get('item'), o['scanned'], 'Món này chưa có trên máy tính tiền.')
        o['scanned'].pop(item)
        return dict(message=f'Đã xóa {ITEM_INDEX[item]["name"]} khỏi máy tính tiền.')
    if name == 'gr_rush_total':
        return _rush_lock(s, c, t, who)
    if name == 'gr_rush_change':
        kit.need(o['charged'] is not None, 'Bấm “Tính tiền” trước: khách đưa tiền rồi mới thối.')
        denom = p.get('denom')
        kit.need(type(denom) is int and denom in DENOMS, 'Mệnh giá không có trong két.')
        kit.need(len(o['change']) < 40, 'Khay thối tiền đầy rồi.')
        o['change'].append(denom)
        return dict(message=f'Đặt {denom} xu vào khay thối · đang thối {sum(o["change"])} xu.')
    if name == 'gr_rush_undo':
        kit.need(o['change'], 'Khay thối tiền đang trống.')
        o['change'] = [] if p.get('all') is True else o['change'][:-1]
        return dict(message='Đã cất lại tiền vào két.')
    if name == 'gr_rush_pay':
        return _rush_pay(s, c, t, who)
    raise kit.eng().GameError('Thao tác quầy giờ cao điểm không hợp lệ.')


def _rush_lock(s: dict, c: dict, t: dict, who: str) -> dict:
    """“Tính tiền”: the till totals what was rung up and the customer reads the screen. A mistake
    is pointed out only by someone who notices (see COUNTS / HONEST); otherwise it goes home with them."""
    r, queue = t['rush'], t['needs']['queue']
    i, o, q = r['i'], r['offer'], queue[r['i']]
    kit.need(o['charged'] is None, 'Đã tính tiền khách này rồi: thối tiền rồi giao hàng.')
    units = _rush_units(c, t, i)
    if not units and not o['units'] and not o['scanned']:
        # Nothing of theirs left on the shelf: apologise, there is nothing to ring up.
        r['log'].append(_row(i, 'empty'))
        return _rush_next(s, c, t, f'Kệ hết món {who} cần, khách đành về tay không.')
    if units != o['units']:
        _rush_offer(c, t)
        return dict(message='Kệ vừa thay đổi — nhìn lại giỏ của khách rồi tính tiền nhé.', refused=True)
    scanned = o['scanned']
    kit.need(scanned, 'Máy tính tiền đang trống. Quét hàng trong giỏ trước đã.')
    name = lambda k: ITEM_INDEX[k]['name'].lower()
    unit = lambda k: ITEM_INDEX[k]['unit']
    extra = [k for k in scanned if not units.get(k)]
    more = {k: v - units[k] for k, v in scanned.items() if units.get(k) and v > units[k]}
    less = {k: u - scanned.get(k, 0) for k, u in units.items() if scanned.get(k, 0) < u}
    if extra or more and _careful(t, i, q['npc']):
        t['mistakes'] += 1
        r['flags']['over'] += 1
        _miss(o, 'over')
        parts = [f'sao tính cả {name(k)}' for k in extra] + [f'{units[k]} {unit(k)} {name(k)} mà tính {scanned[k]}' for k in more]
        return dict(message=f'{who} chỉ vào màn hình máy tính tiền: “Ủa, {"; ".join(parts)}?” Xóa phần dư rồi tính tiền lại nhé.', refused=True)
    if less and HONEST.get(q['npc']):
        t['mistakes'] += 1
        r['flags']['under'] += 1
        _miss(o, 'under')
        parts = [f'{v} {unit(k)} {name(k)}' for k, v in less.items()]
        return dict(message=f'{who} nhắc: “Còn {", ".join(parts)} chưa tính kìa.” Quét đủ rồi tính tiền lại nhé.', refused=True)
    if 'beer' in units and str(i) not in r['ages'] and q['_age'] is not None and q['_age'] < 18:
        # Rung up without asking for ID: the beer leaves with a minor.
        cq.slip(t, 'minor_beer', 3, f'Giờ đông mà cháu bán bia cho {who} mới {q["_age"]} tuổi, không hỏi giấy tờ gì hết.',
                'bán bia cho người chưa đủ 18 tuổi', safety=True)
    # Into the customer's bag goes what they take home, rung up or not.
    c['life']['consumed_cost'] += sum(_take(c, k, v) for k, v in units.items())
    if more:                   # nobody read the screen: they pay the extra and find it at home
        o['extra'] = sum(_price(c, k) * v for k, v in more.items())
        t['mistakes'] += 1
        r['flags']['over'] += 1
    if less:                   # an undercharge nobody mentioned: the goods leave unpaid
        t['mistakes'] += 1
        r['flags']['under'] += 1
        _miss(o, 'quiet')
        for k, v in less.items():
            kit.waste(c, k, min(60, v), v * ITEM_INDEX[k]['cost'], 'Quét sót — khách mang về chưa tính tiền')
    total = _till(c, scanned)
    o['charged'] = total
    o['tender'] = _tender(total, q['style'])
    due = sum(o['tender']) - total
    head = f'Máy tính tiền: {total} xu. {who} đưa {" + ".join(str(v) for v in o["tender"])} xu'
    return dict(message=head + (' — vừa đủ, không cần thối.' if due <= 0 else f' — cần thối {due} xu. Đếm tiền thối từ két vào khay.'))


def _rush_pay(s: dict, c: dict, t: dict, who: str) -> dict:
    """“Thối tiền & giao hàng”: the change in the tray goes to the customer. Nothing is fixed behind
    the player's back: short change is counted at the counter only by a careful customer (who then
    waits for the rest and grumbles); anyone else finds it at home."""
    r, queue = t['rush'], t['needs']['queue']
    i, o, q = r['i'], r['offer'], queue[r['i']]
    kit.need(o['charged'] is not None, 'Bấm “Tính tiền” trước: khách đưa tiền rồi mới thối.')
    npc = q['npc']
    due = sum(o['tender']) - o['charged']
    given = sum(o['change'])
    if given < due and _careful(t, i, npc):
        short = due - given
        if not o['counted']:
            t['mistakes'] += 1
            r['flags']['short'] += 1
            _miss(o, 'short')
        o['counted'] = max(o['counted'], short)
        return dict(message=f'{who} đếm lại ngay tại quầy: “Thối thiếu {short} xu rồi.” Đặt thêm {short} xu vào khay rồi đưa lại.', refused=True)
    stars, notes, later = 5, [], ''

    def hit(n: int, text: str) -> None:
        nonlocal stars
        stars = min(stars, n)
        notes.append(text)

    paid, tip = sum(o['tender']) - given, 0
    if 'over' in o['miss']:
        hit(4, 'bấm dư tiền, khách phải soi ra')
        cq.slip(t, f'bill{i}', 1, f'Bấm dư tiền, {who} phải tự soi màn hình mới sửa.', 'bấm dư tiền, khách phải tự soi')
    if 'under' in o['miss']:
        hit(4, 'tính thiếu, khách phải nhắc')
        cq.slip(t, f'under{i}', 1, f'Tính thiếu, {who} phải nhắc mới tính đủ.', 'tính thiếu, khách phải nhắc')
    if o['extra']:
        x = o['extra']
        hit(2 if x < 10 else 1, f'về nhà coi lại mới thấy bị tính dư {x} xu')
        later = f'Về nhà coi lại mới thấy tiệm tính dư {x} xu. Mua có mấy món mà cũng bấm sai.'
    if 'quiet' in o['miss']:
        notes.append('quét sót món, khách mang về chưa tính tiền')
    if 'beer' in o['units'] and str(i) not in r['ages'] and q['_age'] is not None and q['_age'] < 18:
        hit(1, f'bán bia cho {who} mới {q["_age"]} tuổi')
    if given < due:
        short = due - given
        t['mistakes'] += 1
        r['flags']['short'] += 1
        hit(2 if short < 10 else 1, f'về nhà đếm lại mới thấy thối thiếu {short} xu')
        later = f'Tối về đếm lại tiền mới thấy tiệm thối thiếu {short} xu. Giờ đông cũng phải đếm cho kỹ chứ.'
        say = f'{who} nhét tiền thối vào túi rồi đi luôn, không đếm lại.'
    elif given > due:
        extra = given - due
        t['mistakes'] += 1
        r['flags']['excess'] += 1
        if HONEST.get(npc):
            paid = o['charged']
            hit(4, f'thối dư {extra} xu, khách trả lại')
            cq.slip(t, f'excess{i}', 1, f'Thối dư {extra} xu, {who} phải đưa trả lại.', f'thối dư {extra} xu')
            say = f'{who} đếm lại rồi trả {extra} xu: “Thối dư rồi nè, coi chừng lỗ!”'
        else:
            r['loss'] += extra
            notes.append(f'thối dư {extra} xu, khách cầm đi luôn')
            say = f'{who} cầm tiền thối đi luôn — thối dư {extra} xu, tối kiểm két sẽ thiếu.'
    elif o['counted']:
        hit(3, f'thối thiếu {o["counted"]} xu, khách đếm lại mới đủ')
        cq.slip(t, f'short{i}', 1, f'Thối thiếu {o["counted"]} xu, {who} phải đếm lại tại quầy mới đủ.',
                f'thối thiếu {o["counted"]} xu, khách đếm lại mới đủ')
        say = f'{who} nhận đủ tiền thối nhưng vẫn cằn nhằn: “Đông cỡ nào cũng phải đếm cho kỹ chứ.”'
    else:
        say = f'Thối {due} xu, {who} gật đầu cảm ơn.' if due > 0 else f'{who} đưa vừa đủ tiền, xách giỏ đi.'
        if due > 0 and not o['miss'] and not o['extra'] and stars == 5 and _deadline(t, i) - c['turn'] >= 1:
            tip = _keep(t, i, npc, due)
        if tip:
            # "Khỏi thối": the small change stays on the counter — the customer's own tip, paid once here.
            kit.money(s, c, tip, f'Khách để lại tiền lẻ: {who}', t['id'], 'tip')
            t['tip_given'] = t.get('tip_given', 0) + tip
            notes.append(f'khỏi thối, để lại {tip} xu uống nước')
            say = f'Thối {due} xu. {who} xua tay: “{KEEP_SAY.get(npc, "Khỏi thối, giữ uống nước nha.")}” · +{tip} xu tiền lẻ.'
    if paid < 0:
        # More change than the customer paid: the rest comes out of the shop's own money.
        take = min(-paid, c['money'])
        if take:
            kit.money(s, c, -take, f'Thối dư tại quầy giờ cao điểm: {who}', t['id'], 'loss')
        paid = 0
    r['log'].append(_row(i, 'served', paid, tip, stars, '; '.join(notes) or 'tính nhanh, thối đúng', later))
    _rush_serve(c, t, paid)
    return _rush_next(s, c, t, say)


def _rush_serve(c: dict, t: dict, paid: int) -> None:
    r = t['rush']
    r['cash'] += paid
    r['served'] += 1
    d = _data(c)
    d['sales'] += paid
    d['day_sales'] += paid
    d['customers'] += 1


def _rush_next(s: dict, c: dict, t: dict, message: str) -> dict:
    r, queue = t['rush'], t['needs']['queue']
    r['i'] += 1
    r['offer'] = None
    if r['i'] >= len(queue):
        return dict(message=message + ' ' + _rush_finish(s, c, t), celebrate=not t['mistakes'] and not r['left'])
    _rush_offer(c, t)
    return dict(message=message + f' Mời {PEOPLE[queue[r["i"]]["npc"]][0]}!')


def _rush_finish(s: dict, c: dict, t: dict, closing: bool = False) -> str:
    _rush_ready(t)
    r, queue = t['rush'], t['needs']['queue']
    notes = []
    if closing:
        o = r['offer']
        if r['i'] < len(queue) and o and o['i'] == r['i'] and o['charged'] is not None:
            # Money on the counter when the shutters come down: Cô Ba counts the change out herself.
            who = PEOPLE[queue[r['i']]['npc']][0]
            r['log'].append(_row(r['i'], 'served', o['charged'], 0, 3, 'chờ tiền thối tới lúc đóng cửa'))
            _rush_serve(c, t, o['charged'])
            r['i'] += 1
            notes.append(f'Cô Ba thối nốt tiền cho {who}.')
        while r['i'] < len(queue):
            r['left'] += 1
            r['log'].append(_row(r['i'], 'left'))
            r['i'] += 1
    r['offer'] = None
    d = _data(c)
    d['stats']['rush'] += 1
    d['stats']['walkouts'] += r['left']
    tips = sum(x['tip'] for x in r['log'])
    t['result'] = dict(served=r['served'], left=r['left'], cash=r['cash'], loss=r['loss'], tips=tips)
    kit.metric(c, 'gr_rush')
    served = [x for x in r['log'] if x['status'] == 'served']
    # The customer who was wronged the most is the one who comes back about it: the reaction is
    # settled on their bill (money moves once, in consequences.react).
    # Only what someone noticed at the counter is settled now (money moves once, in consequences.react).
    counter = [x for x in served if not x['_later']]
    worst = min(counter, key=lambda x: (x['stars'] or 5, -x['paid']), default=None)
    react = cq.react(s, c, t, worst['paid'] if worst else 0, who=PEOPLE[queue[worst['i']]['npc']][0] if worst else PEOPLE[0][0])
    cash = max(0, r['cash'] - react['cut'])
    home = [x for x in served if x['_later']]
    for x in home:
        # Found at home, after the queue has gone: it still counts against the shift's rating.
        cq.slip(t, f'home{x["i"]}', 3 if (x['stars'] or 1) <= 1 else 2, x['_later'], x['note'])
    if home:
        notes.extend(cq._escalate(s, c, t))   # a big enough gap gets reported on the app (once per task)
    kit.complete(s, c, t, cash, f'Bạn đã đứng quầy giờ cao điểm: {r["served"]} khách được tính tiền.')
    for x in home:
        # ... and they say it in their own review.
        npc = queue[x['i']]['npc']
        kit.review(s, c, kit.npc_id(ID, npc), x['stars'] or 1, x['_later'], f'{t["id"]}-{x["i"]}')
        notes.insert(0, f'{PEOPLE[npc][0]} về nhà rồi để lại đánh giá {x["stars"] or 1}★.')
        x['_later'] = ''
    out = f'Hết hàng chờ: {r["served"]} khách xong, {r["left"]} khách bỏ về · +{cash} xu.'
    if tips:
        out += f' Khách để lại {tips} xu tiền lẻ.'
    if react['message']:
        out += ' ' + react['message']
    return ' '.join([out] + notes)


def _rush_feedback(t: dict) -> dict:
    """The queue's rating: the till work as a whole, the wait, and one line per customer served
    (their own stars and what they say)."""
    _rush_ready(t)
    r, queue = t['rush'], t['needs']['queue']
    f = r['flags']
    served = [x for x in r['log'] if x['status'] == 'served']
    empty = sum(1 for x in r['log'] if x['status'] == 'empty')
    wrong = (['có lúc bấm sai tiền hàng'] if f['over'] or f['under'] else []) + ([f'thối thiếu {f["short"]} lần'] if f['short'] else []) \
        + ([f'thối dư {f["excess"]} lần'] if f['excess'] else [])
    rows = [dict(key='accuracy', label='Tính tiền & thối tiền', score=max(1, 5 - 2 * f['over'] - f['under'] - 2 * f['short'] - f['excess']),
                 note='; '.join(wrong) or 'tính đúng, thối đúng từng khách'),
            dict(key='queue', label='Hàng chờ', score=5 if not r['left'] else 3 if r['left'] == 1 else 1,
                 note='không ai phải bỏ về' if not r['left'] else f'{r["left"]} khách chờ lâu bỏ về')]
    for x in served:
        rows.append(dict(key=f'c{x["i"]}', label=f'Tính tiền cho {PEOPLE[queue[x["i"]]["npc"]][0]}', score=x['stars'] or 5,
                         note=x['note'] or 'đã tính tiền'))
    if empty:
        rows.append(dict(key='stock', label='Đủ hàng', score=2, note=f'{empty} khách không mua được gì vì kệ trống'))
    if f['minor']:
        rows.append(dict(key='rules', label='Đúng quy định', score=5, note='không bán bia cho người dưới 18 tuổi'))
    return dict(criteria=rows[:8])


def _validate_rush(t: dict, original: dict) -> None:
    _rush_ready(t)
    r = t.get('rush')
    queue = original['needs']['queue']
    kit.need(isinstance(r, dict) and set(r) == set(_empty_rush()), 'Hàng chờ thiếu dữ liệu.')
    kit.integer(r['i'], 0, len(queue))
    for k in ('served', 'left'):
        kit.integer(r[k], 0, len(queue))
    kit.need(r['served'] + r['left'] <= r['i'], 'Đếm khách sai.')
    kit.integer(r['cash'], 0, 10**6)
    kit.integer(r['loss'], 0, 10**6)
    kit.need(r['start'] is None or kit.integer(r['start'], 0, 10**9) >= 0, 'Giờ mở hàng chờ sai.')
    kit.need(isinstance(r['ages'], dict) and all(k.isdigit() and int(k) < len(queue) and v == queue[int(k)]['_age'] for k, v in r['ages'].items()),
             'Tuổi khách sai.')
    kit.need(isinstance(r['log'], list) and len(r['log']) <= len(queue), 'Nhật ký hàng chờ sai.')
    for x in r['log']:
        kit.need(isinstance(x, dict) and set(x) == set(LOG_KEYS) and x['status'] in ('served', 'left', 'empty'), 'Nhật ký hàng chờ sai.')
        kit.integer(x['i'], 0, len(queue) - 1)
        kit.integer(x['paid'], 0, 10**6)
        kit.integer(x['tip'], 0, 10**4)
        kit.need(x['stars'] is None or kit.integer(x['stars'], 1, 5) > 0, 'Đánh giá của khách sai.')
        kit.text(x['note'], 200, 0)
        kit.text(x['_later'], 300, 0)
    kit.need(isinstance(r['flags'], dict) and set(r['flags']) == set(_empty_rush()['flags']), 'Ghi nhận hàng chờ sai.')
    _ints(r['flags'].values(), 0, 100)
    o = r['offer']
    if o is not None:
        kit.need(isinstance(o, dict) and set(o) == set(OFFER_KEYS) and o['i'] == r['i'] < len(queue), 'Giỏ giờ cao điểm sai.')
        for k in ('units', 'scanned'):
            kit.need(isinstance(o[k], dict) and all(x in ITEM_INDEX and x not in WEIGHED for x in o[k]), 'Giỏ giờ cao điểm sai.')
            _ints(o[k].values(), 1, 60)
        kit.need(isinstance(o['tender'], list) and len(o['tender']) <= 20 and all(type(x) is int and x in DENOMS for x in o['tender']), 'Tiền khách đưa sai.')
        kit.need(isinstance(o['change'], list) and len(o['change']) <= 40 and all(type(x) is int and x in DENOMS for x in o['change']), 'Khay thối tiền sai.')
        kit.need(o['charged'] is None or kit.integer(o['charged'], 0, 10**6) >= 0, 'Tiền đã tính sai.')
        kit.need(o['charged'] is not None or not (o['tender'] or o['change']), 'Chưa tính tiền mà đã có tiền trên quầy.')
        kit.need(isinstance(o['miss'], list) and len(set(o['miss'])) == len(o['miss']) and set(o['miss']) <= set(MISS), 'Ghi nhận khách sai.')
        kit.integer(o['counted'], 0, 10**6)
        kit.integer(o['extra'], 0, 10**6)


# ---------------------------------------------------------------- bulk orders
def _make_bulk(day: int, slot: int, serial: int, rng, mod: str) -> dict:
    pool = [b for b in BULKS if b[5] <= day]
    npc, title, opening, lines, note, _ = BULKS[0] if mod == 'wedding' else pool[rng.randrange(len(pool))]
    tier = _tier(day)
    scale = (100, 100, 125, 150)[tier]
    rows = [dict(item=i, qty=min(60, max(1, q * scale // 100))) for i, q in lines]
    top = rng.choice(((95, 100, 100), (90, 95, 100), (88, 92, 96), (85, 90, 95))[tier])
    needs = dict(lines=rows, note=note, deposit=BULK_DEPOSIT, _max=top)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='bulk', needs=needs,
                         bulk=dict(stage='quote', offers=[], price=None, deposit=0, delivered={}), result=None)


def _bulk_list(c: dict, t: dict, base: bool = False) -> int:
    return sum((PRICES[x['item']] if base else _price(c, x['item'])) * x['qty'] for x in t['needs']['lines'])


def _bulk_action(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    b, n, who = t['bulk'], t['needs'], _who(t)
    kit.start_work(t)
    if name == 'gr_bulk_quote':
        kit.need(b['stage'] == 'quote', 'Đơn này đã chốt giá rồi.')
        off = kit.integer(p.get('off'), 0, 100)
        kit.need(off in BULK_OFFERS, 'Mức bớt không có trong bảng giá sỉ.')
        # The deepest discount turned down leaves nothing lower to offer: the customer walks (a bill stuck
        # there before this, offers == [15], ends on the next tap instead of refusing every price).
        if not b['offers'] or b['offers'][-1] < BULK_OFFERS[-1]:
            kit.need(not b['offers'] or off > b['offers'][-1], 'Lần báo giá sau phải bớt nhiều hơn lần trước.')
            b['offers'].append(off)
        # Bulk quotes start from the standard price list, not the shop's own shelf prices: a customer buying in bulk
        # compares with other shops' list. Quoting from raised shelf prices made every bulk order impossible (01/10,
        # feedback #49/#52: rice 20 instead of 18, eggs 4 instead of 3 → even −15% stayed above what they would pay).
        price = _bulk_list(c, t, base=True) * (100 - b['offers'][-1]) // 100
        if b['offers'][-1] == off and price * 100 <= _bulk_list(c, t, base=True) * n['_max']:
            b['stage'] = 'deliver'
            b['price'] = price
            b['deposit'] = -(-price * n['deposit'] // 100)
            kit.money(s, c, b['deposit'], f'Tiền cọc đơn sỉ: {t["title"]}', t['id'], 'revenue')
            d = _data(c)
            d['sales'] += b['deposit']
            d['day_sales'] += b['deposit']
            return dict(message=f'{who} gật đầu: “Chốt {price} xu nha!” Nhận cọc {b["deposit"]} xu. Soạn đủ hàng rồi giao trước khi đóng ca.', celebrate=True)
        if len(b['offers']) >= 2 or b['offers'][-1] == BULK_OFFERS[-1]:
            b['stage'] = 'lost'
            t['result'] = dict(price=0, lost=1)
            kit.metric(c, 'gr_bulk_lost')
            kit.complete(s, c, t, 0, f'{who} không đặt đơn sỉ ở tiệm vì giá chưa hợp.')
            return dict(message=f'{who}: “Thôi để hỏi thêm bên Mây Mart.” Đơn sỉ không thành.', refused=True)
        return dict(message=f'{who} nhíu mày: “{price} xu hả? Hơi cao so với chỗ khác đó.” Còn một lần báo giá.', refused=True)
    if name == 'gr_bulk_deliver':
        kit.need(b['stage'] == 'deliver', 'Chốt giá với khách trước đã.')
        kit.confirm(p, 'Xác nhận soạn hàng và giao đơn sỉ.')
        short = {x['item']: x['qty'] - _available(c, x['item'], t) for x in n['lines'] if _available(c, x['item'], t) < x['qty']}
        if short and p.get('partial') is not True:
            raise kit.eng().GameError('Chưa đủ hàng: ' + ', '.join(f'thiếu {q} {ITEM_INDEX[k]["unit"]} {ITEM_INDEX[k]["name"]}' for k, q in short.items())
                                      + '. Nhập thêm ở “Kho & giá” (hỏa tốc có ngay) hoặc giao phần đang có.')
        delivered, cost = {}, 0
        for x in n['lines']:
            q = min(x['qty'], _available(c, x['item'], t))
            if q > 0:
                cost += _take(c, x['item'], q)
                delivered[x['item']] = q
        kit.need(delivered, 'Kệ không còn món nào của đơn này để giao.')
        c['life']['consumed_cost'] += cost
        full = _bulk_list(c, t, base=True)
        value = b['price'] * sum(PRICES[k] * q for k, q in delivered.items()) // full
        rest = value - b['deposit']
        b['delivered'] = delivered
        b['stage'] = 'done'
        if rest < 0:
            kit.money(s, c, -min(-rest, c['money']), f'Trả lại tiền cọc phần thiếu: {t["title"]}', t['id'], 'refund')
        d = _data(c)
        d['stats']['bulk'] += 1
        d['sales'] += max(0, rest)
        d['day_sales'] += max(0, rest)
        d['customers'] += 1
        missing = sum(short.values())
        if missing:
            t['mistakes'] += 1
            want = sum(x['qty'] for x in n['lines'])
            sev = 1 if missing * 5 <= want else 2 if missing * 2 <= want else 3
            cq.slip(t, 'short', sev, f'Hẹn đủ hàng mà giao thiếu {missing} món, nhà tôi phải chạy đi mua thêm chỗ khác.', f'giao thiếu {missing} món')
        t['result'] = dict(price=value, cost=cost, short=missing)
        kit.metric(c, 'gr_bulk')
        react = cq.react(s, c, t, max(0, rest), who=who)
        d['sales'] -= react['cut']
        d['day_sales'] -= react['cut']
        kit.complete(s, c, t, react['pay'], f'Bạn đã giao đơn sỉ “{t["title"]}”.')
        if missing:
            return dict(message=f'Giao thiếu {missing} món, chỉ thu {value - react["cut"]} xu. ' + (react['message'] or f'{who} không vui: “Hẹn đủ mà giao thiếu, kẹt quá.”'))
        return dict(message=f'Xe ba gác chở đủ hàng đi · thu nốt {max(0, rest)} xu (tổng {value} xu). {who}: “Tiệm làm ăn chắc tay!”', celebrate=True)
    raise kit.eng().GameError('Thao tác đơn sỉ không hợp lệ.')


def _bulk_cancel(s: dict, c: dict, t: dict) -> str:
    b = t['bulk']
    refund = min(b['deposit'], c['money'])
    if refund:
        kit.money(s, c, -refund, f'Hoàn cọc đơn sỉ không giao kịp: {t["title"]}', t['id'], 'refund')
    d = _data(c)
    d['sales'] = max(0, d['sales'] - refund)
    d['day_sales'] = max(0, d['day_sales'] - refund)
    b['stage'] = 'cancelled'
    t['mistakes'] += 1
    t['result'] = dict(price=0, refund=refund)
    cq.slip(t, 'no_show', 3, 'Nhận cọc rồi mà tới tối không thấy giao hàng, nhà tôi phải chạy đi mua chỗ khác.', 'nhận cọc mà không giao hàng')
    cq.react(s, c, t, 0, who=_who(t))
    kit.complete(s, c, t, 0, f'Đơn sỉ “{t["title"]}” không giao kịp, tiệm phải hoàn cọc.', status='cancelled')
    return f'Đơn sỉ “{t["title"]}” không giao kịp trong ngày: hoàn cọc {refund} xu.'


def _bulk_feedback(t: dict, speed: int, patience: int) -> dict:
    b, r = t['bulk'], t['result'] or {}
    if b['stage'] == 'lost':
        rows = [dict(key='deal', label='Báo giá', score=2, note='giá sỉ chưa hợp, khách đặt chỗ khác')]
    elif b['stage'] == 'cancelled':
        rows = [dict(key='deal', label='Giữ lời hẹn', score=1, note='nhận cọc mà không giao kịp')]
    else:
        off = b['offers'][-1] if b['offers'] else 0
        rows = [dict(key='deal', label='Giá sỉ', score=5 if off >= 5 else 4, note=f'được bớt {off}%' if off else 'giá niêm yết'),
                dict(key='delivery', label='Giao đủ hàng', score=2 if r.get('short') else 5,
                     note=f'thiếu {r["short"]} món so với đơn' if r.get('short') else 'đủ từng món')]
    rows.append(dict(key='speed', label='Thời gian chờ', score=speed, note=f'kiên nhẫn còn {patience}%'))
    return dict(criteria=rows)


def _validate_bulk(t: dict, original: dict) -> None:
    b = t.get('bulk')
    kit.need(isinstance(b, dict) and set(b) == {'stage', 'offers', 'price', 'deposit', 'delivered'}
             and b['stage'] in ('quote', 'deliver', 'done', 'lost', 'cancelled'), 'Đơn sỉ sai.')
    kit.need(isinstance(b['offers'], list) and len(b['offers']) <= 2 and all(x in BULK_OFFERS for x in b['offers'])
             and b['offers'] == sorted(set(b['offers'])), 'Báo giá sỉ sai.')
    kit.need(b['price'] is None or kit.integer(b['price'], 0, 10**6) >= 0, 'Giá sỉ sai.')
    kit.integer(b['deposit'], 0, 10**6)
    kit.need(b['stage'] in ('quote', 'lost') or b['price'] is not None, 'Đơn sỉ chưa chốt giá.')
    want = {x['item']: x['qty'] for x in original['needs']['lines']}
    kit.need(isinstance(b['delivered'], dict) and all(k in want for k in b['delivered']), 'Hàng giao sỉ sai.')
    for k, q in b['delivered'].items():
        kit.integer(q, 1, want[k])


# ---------------------------------------------------------------- stock & price tags (no customer needed)
def _inv_lots(c: dict) -> list:
    x = c.get('ext', {}).get('inv')
    return x['lots'] if x else []


# ---- shelf order (care loop): new stock put in front of older stock is a real state of the shelf
def _live(c: dict, item: str) -> list:
    return [l for l in _inv_lots(c) if l['item'] == item and l['qty'] > 0 and l['expires'] >= c['day']]


def _split(c: dict, item: str) -> tuple[list, list]:
    """(old, new): lots put in order at the last rotation, and lots added since."""
    known = kit.data(c).get('rot', {}).get(item)
    live = _live(c, item)
    if known is None:
        return live, []
    return [l for l in live if l['id'] in known], [l for l in live if l['id'] not in known]


def _unrotated(c: dict, item: str) -> bool:
    if item not in ROTATE:
        return False
    old, new = _split(c, item)
    return bool(old and new and max(l['expires'] for l in new) > min(l['expires'] for l in old))


def _sync_rot(c: dict) -> None:
    """Seed the shelf order from the lots on the shelf (old saves start rotated), forget sold
    lots and quietly accept new stock that is not fresher than what is already there."""
    if not c.get('ext', {}).get('inv'):
        return
    rot = _data(c)['rot']
    for item in ROTATE:
        live = _live(c, item)
        if item not in rot or not isinstance(rot[item], list):
            rot[item] = [l['id'] for l in live][-40:]
            continue
        if not _unrotated(c, item):
            rot[item] = [l['id'] for l in live][-40:]
        else:
            ids = {l['id'] for l in live}
            rot[item] = [x for x in rot[item] if x in ids][-40:]


def _pick_lots(c: dict, item: str) -> list:
    """The order customers take units in: oldest first on a rotated shelf, the new lots
    first (they sit at the front) on an unrotated one."""
    fifo = lambda ls: sorted(ls, key=lambda l: (l['expires'], l['received']))
    if _unrotated(c, item):
        old, new = _split(c, item)
        return sorted(new, key=lambda l: (-l['received'], -l['expires'])) + fifo(old)
    return fifo(_live(c, item))


def _today_in_pick(c: dict, item: str, qty: int) -> int:
    """How many of the next `qty` units picked are dated today."""
    n = 0
    for lot in _pick_lots(c, item):
        if qty <= 0:
            break
        used = min(qty, lot['qty'])
        if lot['expires'] <= c['day']:
            n += used
        qty -= used
    return n


def _take(c: dict, item: str, qty: int) -> int:
    """Sell `qty` units in the shelf's real pick order. Returns their recorded cost."""
    if item not in ROTATE or not _unrotated(c, item):
        return kit.take(c, item, qty)
    kit.need(kit.stock(c, item) >= qty, f'Hết {ITEM_INDEX[item]["name"]}. Mở Kho để nhập thêm nhé.')
    cost = 0
    for lot in _pick_lots(c, item):
        if qty <= 0:
            break
        used = min(qty, lot['qty'])
        lot['qty'] -= used
        qty -= used
        cost += used * lot['unit_cost']
    x = c['ext']['inv']
    x['lots'] = [l for l in x['lots'] if l['qty'] > 0]
    return cost


def _rotate(c: dict, item: str) -> None:
    _data(c)['rot'][item] = [l['id'] for l in _live(c, item)][-40:]
    _data(c)['stats']['rotated'] += 1


def _rotate_action(s: dict, c: dict, p: dict) -> dict:
    item = kit.one_of(p.get('item'), ROTATE, 'Món này không cần xoay kệ theo hạn.')
    it = ITEM_INDEX[item]
    kit.need(_unrotated(c, item), f'Kệ {it["name"]} đang đúng thứ tự: hạn gần ở trước.')
    old, new = _split(c, item)
    back = min(l['expires'] for l in old)
    _rotate(c, item)
    kit.metric(c, 'gr_rotated')
    return dict(message=f'Xoay kệ {it["name"]}: lô HSD ngày {back} ra mặt kệ, hàng mới (HSD ngày {max(l["expires"] for l in new)}) xếp vào trong. '
                        'Khách sẽ lấy lô cũ trước.', celebrate=True)


def _rotation_view(c: dict) -> list:
    out = []
    for item in ROTATE:
        if _unrotated(c, item):
            old, new = _split(c, item)
            out.append(dict(item=item, back=min(l['expires'] for l in old), back_qty=sum(l['qty'] for l in old),
                            front=max(l['expires'] for l in new), front_qty=sum(l['qty'] for l in new)))
    return out


# ---- weekly regular lists (care loop)
def _list_for(key: int, day: int) -> dict | None:
    """The regular's shopping list if `day` is their pickup day (seeded per week, never player state)."""
    spec = LISTS.get(key)
    if not spec or day < LIST_FROM or day % 7 != spec['wd']:
        return None
    items = {k: q for k, q in spec['items']}
    r = kit.rng(ID, 'list', key, day // 7)
    extra = spec['items'][r.randrange(len(spec['items']))][0]
    items[extra] += r.choice((0, 1, 1, 2)) * max(1, items[extra] // 4)
    return items


def _list_value(c: dict, units: dict) -> int:
    total = sum(_shelf_unit_price(c, k) * q for k, q in units.items())
    total -= sum(_discount(p, units.get(p['item'], 0), _price(c, p['item'])) for p in PROMOS if p['item'] not in WEIGHED)
    return max(0, total)


def _pack(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    npc = p.get('npc')
    kit.need(isinstance(npc, str) and npc.startswith(ID + '_npc_'), 'Không có khách quen này.')
    try:
        key = int(npc.rsplit('_', 1)[1]) - 1
    except ValueError:
        key = -1
    kit.need(key in LISTS, 'Không có khách quen này.')
    want = _list_for(key, c['day'])
    kit.need(want, f'Hôm nay {PEOPLE[key][0]} không ghé lấy giỏ. Soạn đúng ngày cho hàng tươi nhé.')
    row = d['lists'][str(key)]
    if row['day'] != c['day']:
        row.update(day=c['day'], packed={}, stale=0)
    got, cost, stale = [], 0, 0
    for item, q in want.items():
        gap = q - row['packed'].get(item, 0)
        n = min(gap, _available(c, item, None))
        if n <= 0:
            continue
        if item in ROTATE:
            stale += _today_in_pick(c, item, n)
        cost += _take(c, item, n)
        row['packed'][item] = row['packed'].get(item, 0) + n
        got.append(f'{n} {ITEM_INDEX[item]["unit"]} {ITEM_INDEX[item]["name"]}')
    kit.need(got, 'Giỏ đã đủ, hoặc kệ không còn món nào trong danh sách. Nhập thêm ở “Kho & giá”.')
    c['life']['consumed_cost'] += cost
    row['stale'] += stale
    missing = {k: q - row['packed'].get(k, 0) for k, q in want.items() if row['packed'].get(k, 0) < q}
    note = ('Giỏ đủ món, chờ khách ghé lấy lúc chiều.' if not missing else
            'Còn thiếu ' + ', '.join(f'{q} {ITEM_INDEX[k]["unit"]} {ITEM_INDEX[k]["name"]}' for k, q in missing.items()) + ' — nhập thêm rồi soạn tiếp.')
    if stale:
        note += f' ⚠ {stale} món trong giỏ hết hạn hôm nay — khách sẽ phàn nàn.'
    kit.metric(c, 'gr_packed')
    return dict(message=f'Soạn giỏ cho {PEOPLE[key][0]}: ' + ', '.join(got) + '. ' + note, celebrate=not missing and not stale)


def _pickups(s: dict, c: dict, d: dict) -> list[str]:
    """Regulars come by at closing for their packed bag."""
    lines = []
    for key in LISTS:
        want = _list_for(key, c['day'])
        if not want:
            continue
        row = d['lists'][str(key)]
        name = PEOPLE[key][0]
        npc = kit.npc_id(ID, key)
        packed = row['packed'] if row['day'] == c['day'] else {}
        stale = row['stale'] if row['day'] == c['day'] else 0
        if not packed:
            row['bond'] = max(0, row['bond'] - 1)
            row['missed'] += 1
            d['stats']['lists_missed'] += 1
            lines.append(f'🧺 {name} ghé lấy giỏ mà tiệm chưa soạn — {name} sang Mây Mart mua (thân tình còn “{BOND_NAMES[row["bond"]]}”).')
            kit.log(s, c, 'list', lines[-1], npc)
            continue
        value = _list_value(c, packed)
        full = all(packed.get(k, 0) >= q for k, q in want.items())
        method = LISTS[key]['pay']
        if method == 'credit':
            ok, _why = _ledger_ok(c, key, value)
            method = 'credit' if ok else 'cash'
        if method == 'credit':
            lrow = d['ledger'][str(key)]
            if not lrow['balance']:
                lrow['since'] = c['day']
            lrow['balance'] = min(10**6, lrow['balance'] + value)
            paid = f'ghi sổ {value} xu'
        else:
            kit.money(s, c, value, f'{name} lấy giỏ quen hàng tuần', f'list-{key}-{c["day"]}', 'revenue')
            if method == 'transfer':
                kit.bank(value)
            d['sales'] += value
            d['day_sales'] += value
            paid = f'{"chuyển khoản" if method == "transfer" else "trả tiền mặt"} {value} xu'
        d['customers'] += 1
        d['stats']['lists'] += 1
        if stale:
            row['bond'] = max(0, row['bond'] - 1)
            how = f'có {stale} món hết hạn hôm nay trong giỏ, {name} không vui'
        elif full:
            row['bond'] = min(5, row['bond'] + 1)
            row['done'] += 1
            how = 'đủ món, tươi ngon'
        else:
            how = 'giỏ còn thiếu ' + ', '.join(f'{q - packed.get(k, 0)} {ITEM_INDEX[k]["unit"]} {ITEM_INDEX[k]["name"].lower()}'
                                               for k, q in want.items() if packed.get(k, 0) < q)
        tip = 4 if row['bond'] >= 5 and full and not stale else 2 if row['bond'] >= 3 and full and not stale else 0
        if tip:
            kit.money(s, c, tip, f'{name} gửi thêm tiền bồi dưỡng', f'list-tip-{key}-{c["day"]}', 'tip')
        lines.append(f'🧺 {name} lấy giỏ: {how} · {paid}' + (f' · boa {tip} xu' if tip else '') + f' (thân tình: {BOND_NAMES[row["bond"]]}).')
        kit.log(s, c, 'list', lines[-1], npc)
        row.update(packed={}, stale=0)
    return lines


# ---- tomorrow's forecast (care loop)
@functools.lru_cache(maxsize=64)
def _demand(day: int) -> tuple:
    """What the first customers of `day` will ask for (as the day's own generator deals them)
    plus the regular lists collected that day, in stock units."""
    want = {}
    add = lambda k, q: want.__setitem__(k, want.get(k, 0) + q)
    for slot in range(FORECAST_SLOTS):
        t = _make_v2(day, slot, 0)
        n = t['needs']
        if t['kind'] == 'checkout':
            for line in n['lines']:
                add(line['item'], _units(line['item'], line['_grams']) if line.get('weighed') else line['qty'])
        elif t['kind'] == 'rush':
            for q in n['queue']:
                for item, qty in q['items']:
                    add(item, qty)
        elif t['kind'] == 'bulk':
            for line in n['lines']:
                add(line['item'], line['qty'])
    for key in LISTS:
        for k, q in (_list_for(key, day) or {}).items():
            add(k, q)
    return tuple(sorted(want.items()))


def _about(n: int) -> int:
    return n if n < 5 else -(-n // 5) * 5


def _forecast(c: dict) -> dict:
    day = c['day'] + 1
    x = c.get('ext', {}).get('inv') or {}
    level = kit.level(c) if 'xp' in c else 1
    needs = []
    for item, raw in _demand(day):
        if ITEM_INDEX[item].get('unlock', 1) > level:
            continue
        want = -(-raw * (100 + FORECAST_SPARE) // 100)
        # Units still sellable tomorrow: a lot on its last day tomorrow must come off the shelf that morning.
        good = sum(l['qty'] for l in _inv_lots(c) if l['item'] == item and l['expires'] > day)
        coming = sum(o['qty'] for o in x.get('orders', []) if o['item'] == item and o['status'] == 'in_transit')
        have = good + coming
        needs.append(dict(item=item, want=_about(want), have=have, short=max(0, want - have)))
    needs.sort(key=lambda r: (-r['short'], r['item']))
    m, m2 = mod_of(day), mod_of(day + 1)
    lists = [dict(npc=kit.npc_id(ID, k), name=PEOPLE[k][0]) for k in LISTS if _list_for(k, day)]
    pay = []
    for key, row in _data(c)['ledger'].items():
        if row['balance'] <= 0:
            continue
        i = int(key)
        if row['plan']:
            if row['plan']['next'] <= day:
                pay.append(dict(name=PEOPLE[i][0], amount=min(row['plan']['each'], row['balance']), how='plan'))
            continue
        age = day - max(1, row['since'])
        if age > 0 and (age % NEIGHBOURS[i]['cycle'] == 0 or m['id'] == 'payday') or row['reminded'] == c['day']:
            pay.append(dict(name=PEOPLE[i][0], amount=row['balance'] if NEIGHBOURS[i]['share'] >= 100 else max(1, row['balance'] * NEIGHBOURS[i]['share'] // 100), how='due'))
    short = [r for r in needs if r['short'] > 0]
    tip = (f'Nhập thêm {", ".join(ITEM_INDEX[r["item"]]["name"] for r in short[:3])} trước khi đóng ca.' if short
           else 'Kho đủ cho mấy lượt khách đầu ngày mai.')
    return dict(day=day, mod=dict(id=m['id'], emoji=m['emoji'], name=m['name'], text=m['text']),
                after=dict(id=m2['id'], emoji=m2['emoji'], name=m2['name']), needs=needs[:8], short=len(short),
                lists=lists, pay=pay, tip=tip)


# ---- today's care checklist
def _care(c: dict) -> list:
    d = _data(c)
    rows = []
    for item in ITEM_INDEX:
        n = _today_units(c, item)
        if n:
            rows.append(dict(ok=False, icon='🗑️', label=f'Rút {n} {ITEM_INDEX[item]["unit"]} {ITEM_INDEX[item]["name"]} hết hạn hôm nay',
                             note='đoàn kiểm tra phạt nếu còn trên kệ', tone='danger', do=dict(cmd='gr_pull_today', item=item)))
    for r in _rotation_view(c):
        it = ITEM_INDEX[r['item']]
        rows.append(dict(ok=None, icon='🔄', label=f'Xoay kệ {it["name"]}', tone='warn',
                         note=f'hàng mới HSD {r["front"]} đang nằm trước {r["back_qty"]} {it["unit"]} HSD {r["back"]}', do=dict(cmd='gr_rotate', item=r['item'])))
    for key in LISTS:
        want = _list_for(key, c['day'])
        if not want:
            continue
        row = d['lists'][str(key)]
        packed = row['packed'] if row['day'] == c['day'] else {}
        full = all(packed.get(k, 0) >= q for k, q in want.items())
        rows.append(dict(ok=True if full else None, icon='🧺', label=f'Soạn giỏ quen cho {PEOPLE[key][0]}',
                         note='đủ món, chờ khách ghé' if full else f'{sum(packed.values())}/{sum(want.values())} món · khách ghé lúc đóng ca',
                         do=None if full else dict(cmd='gr_pack', npc=kit.npc_id(ID, key))))
    for key, row in sorted(d['ledger'].items()):
        if row['balance'] <= 0:
            continue
        i = int(key)
        name = PEOPLE[i][0]
        hard = _hard(i, c['day'])
        age = c['day'] - max(1, row['since'])
        if row['plan']:
            continue
        if hard:
            rows.append(dict(ok=None, icon='🙁', label=f'{name} đang kẹt tiền', note=f'đừng nhắc nợ lúc này — giãn nợ {row["balance"]} xu', tone='warn',
                             do=dict(tab='ledger')))
        elif age > OVERDUE_DAYS and row['reminded'] != c['day']:
            rows.append(dict(ok=False, icon='📒', label=f'Nhắc khéo {name}', note=f'nợ {row["balance"]} xu đã {age} ngày' + (' — sắp mất trắng' if age >= BAD_DAYS - 2 and row['trust'] <= 2 else ''),
                             tone='danger' if age >= BAD_DAYS - 2 else 'warn', do=dict(cmd='gr_remind', npc=kit.npc_id(ID, i))))
    near = [x['id'] for x in ITEMS if _near_units(c, x['id']) and not _today_units(c, x['id']) and x['id'] not in d['cleared']]
    if near:
        rows.append(dict(ok=None, icon='🏷️', label='Xả giá hàng HSD ngày mai', note=', '.join(ITEM_INDEX[k]['name'] for k in near[:3]),
                         do=dict(tab='stock')))
    f = _forecast(c)
    if f['short']:
        rows.append(dict(ok=None, icon='📅', label=f'Chuẩn bị cho ngày mai ({f["mod"]["name"]})', note=f['tip'], tone='warn', do=dict(tab='stock')))
    return rows


def _near_units(c: dict, item: str) -> int:
    """Units in their last selling day (HSD tomorrow): tomorrow they must come off the shelf."""
    return sum(l['qty'] for l in _inv_lots(c) if l['item'] == item and l['expires'] == c['day'] + 1)


def _today_units(c: dict, item: str) -> int:
    return sum(l['qty'] for l in _inv_lots(c) if l['item'] == item and l['expires'] <= c['day'])


def _shelf_unit_price(c: dict, item: str) -> int:
    return _weighed_amount(_price(c, item), WEIGHED[item]) if item in WEIGHED else _price(c, item)


def _tag(s: dict, c: dict, p: dict) -> dict:
    item = kit.one_of(p.get('item'), PRICES, 'Món không có trong bảng giá.')
    it = ITEM_INDEX[item]
    value = kit.integer(p.get('price'), 1, 1000)
    low, high = _floor_price(item), _cap_price(item)
    kit.need(low <= value <= high, f'Giá {it["name"]} trong khoảng {low}–{high} xu (75%–125% giá gốc).')
    kit.need(value != _price(c, item), 'Tem giá đang đúng số này rồi.')
    x = c['life']
    x['prices'][item] = value
    x['price_history'] = ar.last(x['price_history'] + [dict(day=c['day'], item=item, price=value)], 100, 'life.prices', c)
    for t in c['tasks']:
        if t.get('career') == ID and t['status'] not in ('completed', 'referred', 'cancelled') and t['known']:
            if t['kind'] == 'checkout' and t['stage'] == 'basket' or t['kind'] == 'rush':
                quote(c, t)
    theirs = rival(c['day']).get(item)
    unit = 'kg' if item in WEIGHED else it['unit']
    note = '' if theirs is None else ' Rẻ hơn Mây Mart!' if value < theirs else ' Ngang giá Mây Mart.' if value == theirs else f' Mây Mart đang bán {theirs} xu.'
    return dict(message=f'In tem mới: {it["name"]} {value} xu/{unit}.' + note)


def _clear(s: dict, c: dict, p: dict) -> dict:
    item = kit.one_of(p.get('item'), ITEM_INDEX, 'Không có món này.')
    it = ITEM_INDEX[item]
    d = _data(c)
    kit.need(item not in d['cleared'], 'Hôm nay đã bán xả món này rồi.')
    kit.need(not _today_units(c, item), 'Rút hàng hết hạn hôm nay của món này trước đã — không bán hàng hết hạn.')
    qty = min(_near_units(c, item), _available(c, item, None), 12)
    kit.need(qty > 0, 'Món này không có hàng cận date (HSD ngày mai) để bán xả.')
    each = max(1, -(-_shelf_unit_price(c, item) * CLEAR_PERCENT // 100))
    c['life']['consumed_cost'] += kit.take(c, item, qty)
    amount = qty * each
    kit.money(s, c, amount, f'Bán xả cận date: {qty} {it["unit"]} {it["name"]}', f'clear-{item}-{c["day"]}', 'revenue')
    d['cleared'].append(item)
    d['stats']['cleared'] += qty
    d['sales'] += amount
    d['day_sales'] += amount
    kit.metric(c, 'gr_cleared', qty)
    return dict(message=f'Dán tem “Giảm {100 - CLEAR_PERCENT}%”: khách săn giảm giá mua hết {qty} {it["unit"]} {it["name"]} · +{amount} xu.', celebrate=True)


def _pull_today(s: dict, c: dict, p: dict) -> dict:
    from .. import inventory
    item = kit.one_of(p.get('item'), ITEM_INDEX, 'Không có món này.')
    kit.confirm(p, 'Xác nhận rút hàng hết hạn hôm nay.')
    lots = [l for l in _inv_lots(c) if l['item'] == item and l['qty'] > 0 and l['expires'] <= c['day']]
    kit.need(lots, 'Món này không có lô nào hết hạn hôm nay.')
    qty = sum(l['qty'] for l in lots)
    for lot in lots:
        inventory.action(s, c, ID, 'inv_discard', dict(lot=lot['id'], confirm=True))
    kit.metric(c, 'gr_pulled_today', qty)
    it = ITEM_INDEX[item]
    return dict(message=f'Đã rút {qty} {it["unit"]} {it["name"]} hết hạn hôm nay khỏi kệ, ghi hao hụt. Kệ sạch hạn!')


SHOP_ACTIONS = {'gr_tag': _tag, 'gr_clear': _clear, 'gr_pull_today': _pull_today,
                'gr_rotate': _rotate_action, 'gr_pack': _pack, 'gr_plan': _plan}


# ---------------------------------------------------------------- surprises at the shop
EVENTS = [
    dict(id='GE-INSPECT', title='Quản lý thị trường ghé kiểm tra', emoji='🧑‍⚖️', npc=0, min_day=3, tone='tense', at='any', weight=2,
         text='Hai cán bộ quản lý thị trường đưa thẻ ngành: “Kiểm tra định kỳ. Cho xem kho, hạn dùng và hóa đơn nhập hàng.”',
         options=[dict(id='open', label='Mở kho, xuất trình hóa đơn nhập hàng',
                       hint='Hàng hết hạn hôm nay, hàng không hóa đơn, kho có chuột đều bị ghi vào biên bản.',
                       effects=dict(inspect='open'), outcome='Đoàn kiểm tra đi một vòng kho và quầy.'),
                  dict(id='bribe', label='Dúi phong bì 30 xu “uống cà phê” cho nhanh', hint='Có thể cho qua… hoặc thành chuyện lớn.',
                       effects=dict(money=-30), good=False,
                       luck=dict(p=0.3, win=dict(outcome='Họ nhìn nhau, cầm phong bì rồi đi. Cô Ba lắc đầu: “Mở đường kiểu này, lần sau họ lại ghé.”',
                                                 good=False, effects=dict(mark='bribed')),
                                 lose=dict(outcome='Trưởng đoàn trả lại phong bì và lập biên bản hành vi đưa tiền: phạt thêm 40 xu, cả hẻm đều biết.', good=False,
                                           effects=dict(money=-40, review=[1, 'Nghe nói tiệm bị lập biên bản vì dúi phong bì cho đoàn kiểm tra…'], mark='fined'))))],
         default='open'),
    dict(id='GE-REINSPECT', title='Đoàn kiểm tra quay lại tái kiểm', emoji='📋', npc=0, min_day=3, tone='tense', at='any', weight=4, need_mark='reinspect',
         text='Đoàn quản lý thị trường quay lại như đã hẹn trong biên bản cam kết: “Xem tiệm khắc phục tới đâu rồi.”',
         options=[dict(id='open', label='Mở kho cho đoàn tái kiểm', hint='Kho sạch thì được xóa cam kết.',
                       effects=dict(inspect='recheck'), outcome='Đoàn tái kiểm từng kệ.'),
                  dict(id='hide', label='Giấu thùng hàng lỗi ra sau nhà trước khi mở kho', hint='Nếu bị phát hiện thì nặng hơn nhiều.',
                       good=False, luck=dict(p=0.4, win=dict(outcome='Đoàn không lục sau nhà, ký biên bản cho qua. Cô Ba vẫn thấy chột dạ.', good=False,
                                                              effects=dict(unmark='reinspect')),
                                             lose=dict(outcome='Đoàn phát hiện thùng hàng giấu sau nhà: phạt 60 xu vì gian dối.', good=False,
                                                       effects=dict(money=-60, mark='fined', review=[1, 'Tiệm bị bắt quả tang giấu hàng khi kiểm tra. Hết tin nổi!']))))],
         default='open'),
    dict(id='GE-FINE', title='Quyết định xử phạt', emoji='⚖️', npc=0, min_day=1, tone='tense', at='chain',
         text='Biên bản kiểm tra ghi nhận vi phạm.',
         options=[dict(id='pay', label='Nộp phạt', hint='Nộp đủ, hàng vi phạm bị tiêu hủy.', effects=dict(fine='pay'), outcome='Tiệm nhận quyết định xử phạt.'),
                  dict(id='half', label='Tiêu hủy hàng lỗi, ký cam kết khắc phục', hint='Giảm nửa tiền phạt, đóng quầy một lúc để dọn, đoàn sẽ quay lại tái kiểm.',
                       effects=dict(fine='half', patience=-15), outcome='Tiệm ký cam kết khắc phục.'),
                  dict(id='appeal', label='Xin nhắc nhở vì lần đầu vi phạm', hint='Chỉ được xem xét nếu tiệm chưa từng bị phạt hay nhắc nhở.',
                       effects=dict(fine='appeal'), outcome='Bạn trình bày với trưởng đoàn.')],
         default='pay'),
    dict(id='GE-THIEF', title='Cậu nhóc lạ nhét snack vào áo', emoji='🧢', npc=0, min_day=2, tone='tense', weight=2,
         text='Một cậu nhóc lạ mặt đứng lâu ở kệ snack, rồi nhét hai gói vào trong áo khoác, đi thẳng ra cửa.',
         options=[dict(id='stop', label='Bước ra chắn cửa, nói nhỏ: “Em trả tiền hay để lại kệ nha”', hint='Giữ thể diện cho cậu bé.',
                       luck=dict(p=0.7, win=dict(outcome='Cậu nhóc đỏ mặt, trả tiền hai gói rồi lí nhí xin lỗi.', good=True, effects=dict(catch=14, xp=5)),
                                 lose=dict(outcome='Cậu nhóc vùng chạy mất, làm rơi lại một gói.', good=None, effects=dict(stock={'snack': -1})))),
                  dict(id='shout', label='Hô to “Bắt thằng ăn cắp!”', hint='Cả tiệm sẽ quay lại nhìn.',
                       effects=dict(stock={'snack': -2}, patience=-10, review=[2, 'Đang mua đồ thì tiệm la ầm ĩ, hết hồn luôn.']), good=False,
                       outcome='Cậu nhóc bỏ chạy, khách trong tiệm giật mình, hàng chờ rối tung.'),
                  dict(id='ignore', label='Kệ, hai gói snack thôi mà', effects=dict(stock={'snack': -2}, mark='thief'), good=False,
                       outcome='Hai gói snack đi mất. Có vẻ cậu nhóc sẽ còn quay lại.')],
         default='ignore'),
    dict(id='GE-THIEF2', title='Cậu nhóc hôm trước quay lại, dắt theo bạn', emoji='👥', npc=0, min_day=3, tone='tense', weight=3, need_mark='thief',
         text='Cậu nhóc lấy snack hôm trước quay lại, lần này đi cùng hai đứa bạn, tản ra ba góc kệ.',
         options=[dict(id='talk', label='Ra đứng cạnh kệ, chào hỏi từng đứa, chỉ lên camera', hint='Cho tụi nhỏ biết tiệm để ý, không làm to chuyện.',
                       effects=dict(unmark='thief', xp=5), good=True, outcome='Ba đứa nhìn camera, lúng túng mua ba chai nước rồi đi. Từ đó không thấy quay lại lấy đồ.'),
                  dict(id='police', label='Gọi công an khu vực tới nói chuyện', hint='Chắc ăn nhưng làm quầy đình trệ một lúc.',
                       effects=dict(unmark='thief', patience=-15), good=None, outcome='Công an khu vực tới nhắc nhở, báo phụ huynh. Hàng chờ phải đợi một lúc.'),
                  dict(id='ignore', label='Mặc kệ, chắc không sao', effects=dict(stock={'snack': -4, 'soda': -2}), good=False,
                       outcome='Tụi nhỏ ôm đi 4 gói snack và 2 lon nước.')],
         default='ignore'),
    dict(id='GE-DEAL-BEER', title='Hạt Nắng dư lô bia cuối tháng', emoji='🚚', npc=0, min_day=2, tone='gentle', weight=2,
         text='Xe Nhà phân phối Hạt Nắng ghé: “Dư 24 lon Bia Sông Mây, để tiệm 8 xu/lon (giá nhập 11) nếu lấy nguyên thùng ngay bây giờ.”',
         options=[dict(id='all', label='Lấy cả 24 lon', hint='Lời to nếu bán hết, nhưng chiếm chỗ kho và cầm tiền mặt.', show_cost=192,
                       effects=dict(deal=['beer', 24, 8, 0]), good=True, outcome='Thùng bia được khiêng vào kho.'),
                  dict(id='half', label='Lấy 12 lon thôi', show_cost=96, effects=dict(deal=['beer', 12, 8, 0]), good=True, outcome='Tài xế để lại 12 lon.'),
                  dict(id='no', label='Cảm ơn, kho còn đủ', effects={}, good=None, outcome='Xe Hạt Nắng chạy tiếp sang tiệm khác.')],
         default='no'),
    dict(id='GE-DEAL-MILK', title='Sữa cận date giá rẻ', emoji='🥛', npc=0, min_day=3, tone='gentle',
         text='Xe sữa Mây Trắng thanh lý 20 hộp chỉ còn 2 ngày hạn, giá 3 xu/hộp (giá nhập 6). “Lấy hết thì chú bớt thêm cho!”',
         options=[dict(id='all', label='Lấy cả 20 hộp', hint='Rẻ thật, nhưng 2 ngày có bán kịp 20 hộp không?', show_cost=60,
                       effects=dict(deal=['milk', 20, 3, 2]), good=None, outcome='20 hộp sữa cận date vào tủ mát.'),
                  dict(id='half', label='Lấy 8 hộp vừa sức bán', show_cost=24, effects=dict(deal=['milk', 8, 3, 2]), good=True, outcome='8 hộp sữa được xếp lên đầu kệ.'),
                  dict(id='no', label='Không lấy hàng cận date', effects={}, good=None, outcome='Xe sữa chạy đi.')],
         default='no'),
    dict(id='GE-FAKE', title='Nước mắm “xách tay” giá nửa tiền', emoji='🕶️', npc=0, min_day=3, tone='tense',
         text='Một người lạ chở thùng Nước mắm Cá Cơm Vàng, chai y hệt nhưng chỉ 13 xu/chai: “Hàng xách tay, không có hóa đơn đâu em.”',
         options=[dict(id='buy', label='Lấy 10 chai', hint='Lời gấp đôi… nếu không ai phát hiện.', show_cost=130,
                       effects=dict(fake=10, mark='fake'), good=False, outcome='10 chai nước mắm không hóa đơn nằm trong kho.'),
                  dict(id='refuse', label='Từ chối, chỉ nhập hàng có hóa đơn', effects=dict(xp=4), good=True, outcome='Người lạ nhún vai, chở thùng hàng đi.'),
                  dict(id='report', label='Ghi biển số xe, báo quản lý thị trường', hint='Mất chút thời gian đứng quầy.',
                       effects=dict(patience=-5, xp=8, review=[5, 'Tiệm tố giác hàng giả, xóm mình yên tâm mua đồ ở đây.']), good=True,
                       outcome='Tuần sau đoàn liên ngành bắt được xe hàng giả ở chợ đầu mối.')],
         default='refuse'),
    dict(id='GE-FAKE-SICK', title='Khách phàn nàn chai nước mắm lạ mùi', emoji='🤢', npc=6, min_day=4, tone='tense', weight=3, need_mark='fake',
         text='Chị Diệu cầm chai nước mắm quay lại: “Mắm gì mà mùi hắc, nấu nồi canh phải đổ bỏ luôn!”',
         options=[dict(id='recall', label='Xin lỗi, hoàn tiền nồi canh, thu hồi hết chai không hóa đơn', hint='Mất tiền và hàng, giữ được lòng tin.',
                       effects=dict(money=-20, recall=True, unmark='fake', review=[4, 'Tiệm nhận lỗi, hoàn tiền, dẹp hết mắm lạ. Vậy còn chấp nhận được.']), good=True,
                       outcome='Toàn bộ chai không hóa đơn bị dẹp khỏi kệ.'),
                  dict(id='deny', label='“Mắm của tiệm là hàng chính hãng mà chị”', effects=dict(review=[1, 'Bán mắm giả còn cãi. Cả xóm cẩn thận nha!']), good=False,
                       outcome='Chị Diệu đăng ảnh chai mắm lên nhóm cư dân.')],
         default='deny'),
    dict(id='GE-FRIDGE', title='Tủ mát kêu rè rè rồi tắt ngóm', emoji='🧊', npc=0, min_day=3, tone='tense',
         text='Tủ mát đựng sữa và trứng tắt giữa trưa. Thợ ở đầu hẻm báo sửa mất 25 xu, chờ thêm một lúc.',
         options=[dict(id='fix', label='Gọi thợ sửa ngay', effects=dict(money=-25), good=True, outcome='Thợ thay tụ điện, tủ chạy lại êm ru.'),
                  dict(id='flash', label='Bán xả sữa giảm 50% ngay trước khi hỏng', hint='Thu được chút tiền, tủ vẫn hỏng tới tối.',
                       effects=dict(flash=['milk', 50], spoil={'egg': 30}), good=None, outcome='Hàng xóm ùa vào mua sữa giảm nửa giá.'),
                  dict(id='wait', label='Đóng cửa tủ, chờ có thợ rảnh', effects=dict(spoil={'milk': 50, 'egg': 30}), good=False,
                       outcome='Tới tối thợ mới tới. Nửa tủ sữa và một phần trứng phải bỏ.')],
         default='wait'),
    dict(id='GE-RATS', title='Chuột cắn thủng bao gạo trong kho', emoji='🐀', npc=0, min_day=2, tone='gentle',
         text='Sáng mở kho thấy gạo vương đầy sàn, bao snack bị cắn thủng. Dấu chuột khắp góc kho.',
         options=[dict(id='trap', label='Mua bẫy, dọn kho, bịt lỗ tường', effects=dict(money=-12, stock={'rice': -1}, unmark='rats'), good=True,
                       outcome='Kho sạch sẽ, bịt kín lỗ hổng. Đêm đó bẫy dính hai con.'),
                  dict(id='cat', label='Mượn con mèo mướp nhà bà Sáu', hint='Không tốn xu… nếu con mèo chịu bắt chuột.',
                       luck=dict(p=0.5, win=dict(outcome='Mèo bà Sáu trực một đêm, sáng ra kho sạch bóng chuột.', good=True, effects=dict(unmark='rats')),
                                 lose=dict(outcome='Mèo không bắt chuột mà nhảy lên kệ làm vỡ 6 quả trứng.', good=False, effects=dict(stock={'egg': -6}, mark='rats')))),
                  dict(id='ignore', label='Quét gạo, để đó tính sau', effects=dict(stock={'rice': -3, 'snack': -2}, mark='rats'), good=False,
                       outcome='Mất ít gạo và snack. Chuột vẫn còn trong kho.')],
         default='ignore'),
    dict(id='GE-RETURN', title='Khách mang hộp sữa phồng quay lại', emoji='📦', npc=5, min_day=2, tone='gentle',
         text='Anh Khoa đặt hộp sữa phồng lên quầy: “Mới mua sáng nay, về mở ra thấy phồng.”',
         options=[dict(id='swap', label='Xin lỗi, đổi hộp mới và kiểm lại lô đó', effects=dict(stock={'milk': -1}, review=[5, 'Đổi sữa nhanh gọn, không làm khó khách. Ok!']), good=True,
                       outcome='Anh Khoa nhận hộp mới, còn nhắc tiệm để ý lô sữa đó.'),
                  dict(id='refund', label='Hoàn lại 8 xu', effects=dict(money=-8, review=[4, 'Hoàn tiền liền, tiệm cũng được.']), good=True,
                       outcome='Anh Khoa cầm tiền, gật đầu.'),
                  dict(id='refuse', label='“Chắc anh để ngoài nắng nên phồng”', effects=dict(review=[1, 'Hàng lỗi mà đổ cho khách. Không quay lại.']), good=False,
                       outcome='Anh Khoa bỏ về, viết review một sao.')],
         default='refuse'),
    dict(id='GE-FUNERAL', title='Nhà chị Diệu có tang', emoji='🕯️', npc=6, min_day=3, tone='gentle',
         text='Người nhà chị Diệu ghé, mắt đỏ hoe: “Nhà có tang, cho lấy 12 lon nước ngọt với 10 gói mì, ghi sổ giùm, xong đám chị trả.”',
         options=[dict(id='credit', label='Ghi sổ đặc cách, soạn hàng mang qua', hint='Sổ nợ chị Diệu sẽ vượt hạn mức một thời gian.',
                       effects=dict(funeral='credit'), good=True, outcome='Bạn soạn hàng mang qua nhà chị Diệu.'),
                  dict(id='cost', label='Bán giá vốn, nhận tiền mặt', effects=dict(funeral='cost'), good=True, outcome='Chị Diệu cảm ơn, gửi tiền mặt.'),
                  dict(id='gift', label='Biếu một két nước ngọt đi viếng', hint='Mất 12 lon nước, được lòng cả xóm.',
                       effects=dict(funeral='gift', review=[5, 'Tiệm đi viếng còn biếu két nước. Tình làng nghĩa xóm!']), good=True,
                       outcome='Bạn mang két nước qua thắp nén nhang.'),
                  dict(id='refuse', label='Xin lỗi, sổ không ghi thêm được', effects=dict(review=[2, 'Nhà có chuyện mà tiệm cũng không linh động chút nào.']), good=False,
                       outcome='Người nhà chị Diệu lặng lẽ sang Mây Mart.')],
         default='refuse'),
    dict(id='GE-RIVAL', title='Mây Mart phát tờ rơi ngay trước cửa tiệm', emoji='📣', npc=0, min_day=RIVAL_DAY, tone='gentle', weight=3, mods=('sale',),
         text='Nhân viên Mây Mart đứng ngay đầu hẻm phát tờ rơi “Giảm sốc hôm nay”. Khách vào tiệm ai cũng cầm một tờ.',
         options=[dict(id='match', label='Hạ giá các món đang xả bằng Mây Mart hôm nay', hint='Hết bị trả giá, nhưng mỏng lời.',
                       effects=dict(rival='match'), good=None, outcome='Bạn in lại tem giá mấy món trên tờ rơi.'),
                  dict(id='service', label='Dán bảng “Giao tận nhà trong hẻm · cân từng lạng”', hint='Tốn 5 xu in bảng, khách quen hôm nay không so giá nữa.',
                       effects=dict(money=-5, rival='service'), good=True, outcome='Tấm bảng đỏ treo ngay cửa, bà Sáu gật gù khen.'),
                  dict(id='ignore', label='Mặc kệ, giữ giá', effects={}, good=None, outcome='Khách vào tiệm cầm theo tờ rơi so giá.')],
         default='ignore'),
    dict(id='GE-EGGS', title='Bé con làm đổ khay trứng', emoji='🥚', npc=2, min_day=2, tone='gentle',
         text='Con của chị Lan chạy giỡn, đụng đổ khay trứng: 10 quả vỡ tan. Chị Lan tái mặt.',
         options=[dict(id='forgive', label='Cười xòa, dọn dẹp, không bắt đền', effects=dict(stock={'egg': -10}, review=[5, 'Con chị làm vỡ trứng mà tiệm còn an ủi. Cảm ơn nhiều!']), good=True,
                       outcome='Chị Lan cảm ơn rối rít, bé con lí nhí xin lỗi.'),
                  dict(id='charge', label='Nhờ chị Lan đền 30 xu', effects=dict(stock={'egg': -10}, money=30, review=[2, 'Biết là phải đền, nhưng tiệm nói thẳng giữa đông người, ngại ghê.']), good=None,
                       outcome='Chị Lan móc ví đền, mặt buồn so.'),
                  dict(id='cheap', label='Gom trứng dập bán rẻ cho quán cơm chị Diệu', hint='Quán cơm dùng trứng dập làm trứng chiên.',
                       effects=dict(broken=10), good=True, outcome='Chị Diệu lấy hết trứng dập làm trứng chiên cho quán.')],
         default='forgive'),
]


def _hook(s: dict, c: dict, key: str, v, flags: dict):
    d = _data(c)
    if key == 'inspect':
        return _inspect(s, c, flags)
    if key == 'fine':
        return _fine(s, c, v, flags)
    if key == 'deal':
        return _deal(s, c, v, 'partner')
    if key == 'fake':
        return _deal(s, c, ['fishsauce', v, 13, 0], 'noinvoice')
    if key == 'recall':
        lots = [l['id'] for l in _inv_lots(c) if l.get('supplier') == 'noinvoice']
        n = _destroy(c, lots, 'Thu hồi hàng không hóa đơn')
        return f'Thu hồi {n} chai không hóa đơn.' if n else None
    if key == 'catch':
        kit.money(s, c, int(v), 'Khách nhỏ trả tiền snack', f'catch-{c["day"]}', 'revenue')
        return None
    if key == 'flash':
        item, pct = v
        q = _available(c, item, None)
        if not q:
            return 'Tủ không còn sữa để bán xả.'
        each = max(1, _price(c, item) * pct // 100)
        c['life']['consumed_cost'] += kit.take(c, item, q)
        kit.money(s, c, q * each, f'Bán xả {q} {ITEM_INDEX[item]["unit"]} {ITEM_INDEX[item]["name"]} khi tủ hỏng', f'flash-{c["day"]}', 'revenue')
        d['sales'] += q * each
        d['day_sales'] += q * each
        return f'Bán xả {q} {ITEM_INDEX[item]["unit"]} · +{q * each} xu.'
    if key == 'spoil':
        lost = []
        for item, pct in v.items():
            q = kit.stock(c, item) * pct // 100
            if q:
                kit.waste(c, item, q, kit.take(c, item, q), 'Tủ mát hỏng')
                lost.append(f'{q} {ITEM_INDEX[item]["unit"]} {ITEM_INDEX[item]["name"].lower()}')
        return ('Hỏng: ' + ', '.join(lost) + '.') if lost else None
    if key == 'funeral':
        return _funeral(s, c, v)
    if key == 'rival':
        if v == 'service':
            d['today'].update(day=c['day'], calm=True)
            return 'Hôm nay khách quen không so giá với Mây Mart nữa.'
        changed = []
        x = c['life']
        for item, theirs in rival(c['day']).items():
            if _price(c, item) > theirs:
                x['prices'][item] = theirs
                x['price_history'] = ar.last(x['price_history'] + [dict(day=c['day'], item=item, price=theirs)], 100, 'life.prices', c)
                changed.append(f'{ITEM_INDEX[item]["name"]} {theirs} xu')
        for t in c['tasks']:
            if t.get('career') == ID and t['status'] not in ('completed', 'referred', 'cancelled') and t['known'] and t['kind'] in ('checkout', 'rush'):
                quote(c, t)
        return ('Tem mới: ' + ', '.join(changed) + '.') if changed else 'Giá tiệm đã ngang Mây Mart sẵn rồi.'
    if key == 'broken':
        q = min(int(v), kit.stock(c, 'egg'))
        if not q:
            return None
        c['life']['consumed_cost'] += kit.take(c, 'egg', q)
        each = max(1, _price(c, 'egg') // 2)
        kit.money(s, c, q * each, 'Bán trứng dập cho quán cơm', f'eggs-{c["day"]}', 'revenue')
        return f'Bán {q} quả trứng dập · +{q * each} xu.'
    return None


def _deal(s: dict, c: dict, v, supplier: str) -> str:
    item, qty, unit, life = v
    it = ITEM_INDEX[item]
    x = c['ext']['inv']
    from .. import inventory
    transit = sum(o['qty'] for o in x['orders'] if o['item'] == item and o['status'] == 'in_transit')
    q = min(qty, max(0, inventory.capacity(ID) - kit.stock(c, item) - transit))
    kit.need(q > 0, f'Kho hết chỗ chứa {it["name"]} rồi (tính cả hàng đang giao).')
    cost = q * unit
    kit.need(c['money'] >= cost, f'Chưa đủ {cost} xu để lấy lô này. Chọn cách khác nhé.')
    kit.money(s, c, -cost, f'Nhập lô giá hời: {q} {it["unit"]} {it["name"]}', f'deal-{c["day"]}-{item}', 'stock')
    kit.add_lot(c, item, q, unit, life or it.get('life') or 999, supplier)
    kit.metric(c, 'purchases')
    return f'Nhập kho {q} {it["unit"]} {it["name"]} · {cost} xu.' + (f' Kho chỉ còn chỗ cho {q}.' if q < qty else '')


def _destroy(c: dict, ids: list, reason: str) -> int:
    x = c.get('ext', {}).get('inv')
    if not x or not ids:
        return 0
    n = 0
    for lot in x['lots']:
        if lot['id'] in ids and lot['qty'] > 0:
            kit.waste(c, lot['item'], min(60, lot['qty']), lot['qty'] * lot['unit_cost'], reason)
            n += lot['qty']
    x['lots'] = [l for l in x['lots'] if l['id'] not in ids]
    return n


def _inspect(s: dict, c: dict, flags: dict) -> str:
    d = _data(c)
    desk = d['desk']
    lines, lots, amount = [], [], 0
    today = [l for l in _inv_lots(c) if l['qty'] > 0 and l['expires'] <= c['day']]
    if today:
        lines.append(f'{sum(l["qty"] for l in today)} phần hàng hết hạn hôm nay vẫn còn trên kệ')
        lots += [l['id'] for l in today]
        amount += 20
    fake = [l for l in _inv_lots(c) if l['qty'] > 0 and l.get('supplier') == 'noinvoice' and l['id'] not in lots]
    if fake:
        lines.append(f'{sum(l["qty"] for l in fake)} chai nước mắm không hóa đơn, không rõ nguồn gốc')
        lots += [l['id'] for l in fake]
        amount += 40
    if 'rats' in desk['marks']:
        lines.append('kho có dấu chuột cắn bao gạo')
        amount += 15
    d['stats']['inspections'] += 1
    if not lines:
        flags['good'] = True
        desk['marks'].pop('reinspect', None)
        kit.review(s, c, kit.npc_id(ID, 0), 5, 'Đoàn kiểm tra khen kho gọn, hạn dùng rõ ràng, hóa đơn nhập hàng đầy đủ.', f'inspect-{c["day"]}')
        c['xp'] += 10
        return 'Biên bản ghi: không có vi phạm. Cô Ba thở phào, pha trà mời đoàn.'
    if 'fined' in desk['marks']:
        amount = amount * 3 // 2   # repeat offence
    d['fine'] = dict(amount=amount, lines=lines, lots=lots)
    flags['good'] = False
    flags['fine'] = True
    return 'Biên bản ghi: ' + '; '.join(lines) + f'. Mức phạt: {amount} xu.'


def _fine(s: dict, c: dict, mode: str, flags: dict) -> str:
    d = _data(c)
    f = d['fine']
    kit.need(f, 'Không có biên bản phạt nào đang chờ.')
    marks = d['desk']['marks']
    first = not any(m in marks for m in ('fined', 'warned', 'bribed'))
    if mode == 'appeal':
        if first:
            amount, msg = 0, 'Trưởng đoàn cân nhắc: tiệm vi phạm lần đầu nên chỉ lập biên bản nhắc nhở. Hàng lỗi phải tiêu hủy ngay.'
            flags['good'] = True
            marks['warned'] = c['day']
        else:
            amount, msg = f['amount'] + 10, 'Tiệm đã từng bị xử lý nên không được xem xét: phạt đủ, cộng 10 xu vì trì hoãn.'
            flags['good'] = False
    elif mode == 'half':
        amount, msg = f['amount'] // 2, 'Bạn ký cam kết khắc phục, tiêu hủy toàn bộ hàng lỗi. Đoàn giảm nửa mức phạt và hẹn ngày tái kiểm.'
        marks['reinspect'] = c['day']
    else:
        amount, msg = f['amount'], f'Bạn nộp phạt {f["amount"]} xu. Hàng vi phạm bị niêm phong mang đi.'
    if mode != 'appeal' and not flags.get('auto'):
        kit.need(c['money'] >= amount, f'Chưa đủ {amount} xu để nộp. Chọn cách khác nhé.')
    pay = min(amount, c['money'])
    if pay:
        kit.money(s, c, -pay, 'Nộp phạt quản lý thị trường', f'fine-{c["day"]}', 'fine')
        marks['fined'] = c['day']
    if pay < amount:
        msg += f' Két chỉ còn {pay} xu, nộp hết số đó.'
    _destroy(c, f['lots'], 'Tiêu hủy theo biên bản kiểm tra')
    marks.pop('rats', None) if mode == 'half' else None
    d['stats']['fines'] += pay
    d['fine'] = None
    return msg


def _funeral(s: dict, c: dict, mode: str) -> str | None:
    d = _data(c)
    want = {'soda': 12} if mode == 'gift' else {} if mode == 'refuse' else {'soda': 12, 'noodle': 10}
    got = {k: min(q, _available(c, k, None)) for k, q in want.items()}
    got = {k: q for k, q in got.items() if q > 0}
    if want and not got:
        return 'Kệ không còn nước ngọt hay mì để soạn.'
    cost = sum(_take(c, k, q) for k, q in got.items())
    c['life']['consumed_cost'] += cost
    value = sum(_price(c, k) * q for k, q in got.items())
    base = sum(ITEM_INDEX[k]['cost'] * q for k, q in got.items())
    if mode == 'credit':
        row = d['ledger']['6']
        if not row['balance']:
            row['since'] = c['day']
        row['balance'] = min(10**6, row['balance'] + value)
        kit.log(s, c, 'ledger', f'Ghi sổ đặc cách cho nhà chị Diệu: +{value} xu, tổng nợ {row["balance"]} xu.', kit.npc_id(ID, 6))
        return f'Ghi sổ {value} xu cho chị Diệu (sổ đang nợ {row["balance"]}/{row["limit"]} xu).'
    if mode == 'cost':
        kit.money(s, c, base, 'Bán giá vốn cho nhà có tang', f'funeral-{c["day"]}', 'revenue')
        return f'Thu giá vốn {base} xu.'
    return None


def _decide(s: dict, c: dict, p: dict) -> dict:
    d = _data(c)
    desk = d['desk']
    kit.need(desk['ev'] is not None, 'Không có chuyện nào đang chờ quyết.')
    flags = {}
    r = kit.desk_choose(s, c, ID, desk, EVENTS, p.get('option'), hook=lambda s_, c_, k, v: _hook(s_, c_, k, v, flags))
    if 'good' in flags:
        desk['last']['good'] = flags['good']
        desk['log'][-1]['good'] = flags['good']
        r['celebrate'] = flags['good'] is True
    if flags.get('fine'):
        _open_fine(s, c, d)
        r['message'] += ' Đoàn ra quyết định xử phạt.'
    return r


def _open_fine(s: dict, c: dict, d: dict) -> None:
    desk = d['desk']
    desk['seq'] += 1
    desk['ev'] = dict(id=f'desk-{desk["seq"]}', script='GE-FINE', day=c['day'], at='between')
    kit.log(s, c, 'surprise', f'⚖️ Quyết định xử phạt: {"; ".join(d["fine"]["lines"])} — {d["fine"]["amount"]} xu.', kit.npc_id(ID, 0), desk['ev']['id'])


def _close_desk(s: dict, c: dict, d: dict) -> str | None:
    desk = d['desk']
    if desk['ev'] is None:
        return None
    flags = {'auto': True}
    hook = lambda s_, c_, k, v: _hook(s_, c_, k, v, flags)
    note = kit.desk_close(s, c, ID, desk, EVENTS, hook)
    if flags.get('fine') and d['fine']:
        _open_fine(s, c, d)
        note = (note or '') + ' ' + (kit.desk_close(s, c, ID, desk, EVENTS, hook) or '')
    if d['fine'] and desk['ev'] is None:
        d['fine'] = None
    return note.strip() if note else None


def _desk_view(c: dict, raw: dict) -> dict:
    desk = raw.get('desk') or kit.desk_initial()
    view = kit.desk_public(desk, EVENTS, ID)
    ev = view['ev']
    if ev:
        x = kit.desk_script(EVENTS, ev['script'])
        for o, src in zip(ev['options'], x['options']):
            if 'show_cost' in src:
                o['cost'] = src['show_cost']
        f = raw.get('fine')
        if ev['script'] == 'GE-FINE' and f:
            ev['text'] = 'Biên bản ghi: ' + '; '.join(f['lines']) + f'. Mức phạt: {f["amount"]} xu.'
            for o in ev['options']:
                if o['id'] == 'pay':
                    o['label'], o['cost'] = f'Nộp phạt {f["amount"]} xu', f['amount']
                elif o['id'] == 'half':
                    o['label'], o['cost'] = f'Tiêu hủy hàng lỗi, ký cam kết · nộp {f["amount"] // 2} xu', f['amount'] // 2
    return view


# ---------------------------------------------------------------- feedback
def feedback(c: dict, t: dict) -> dict:
    patience = t.get('patience', 100)
    speed = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    if t['kind'] == 'rush':
        return _rush_feedback(t)
    if t['kind'] == 'bulk':
        return _bulk_feedback(t, speed, patience)
    if t['kind'] == 'shelf':
        r = t['result'] or {}
        waste = sum(1 for lot in t['shelf']['pulled'] if _left(c, t, lot) > 0)
        return dict(criteria=[
            dict(key='dates', label='Hạn dùng', score=5 - 2 * r.get('expired', 0), note='không còn hàng hết hạn trên kệ' if not r.get('expired') else f'{r["expired"]} lô hết hạn còn trên kệ'),
            dict(key='fifo', label='Xoay hàng FIFO', score=5 if not r.get('fifo') else 3, note='lô cũ trước, lô mới sau' if not r.get('fifo') else 'lô mới đặt trước lô cũ'),
            dict(key='price', label='Tem giá', score=5 if not r.get('price') else 2, note='khớp bảng giá' if not r.get('price') else 'tem giá sai bảng giá'),
            dict(key='care', label='Cận date & hao hụt', score=max(1, 5 - r.get('markdown', 0) - 2 * waste),
                 note='dán tem giảm giá đúng lô' if not (r.get('markdown') or waste) else 'thiếu tem giảm giá hoặc bỏ nhầm hàng tốt')])
    f = t['flags']
    method = (t['result'] or {}).get('method', t['needs']['pay'])
    rows = [dict(key='accuracy', label='Tính tiền đúng', score=max(1, 5 - 2 * f['overcharge'] - f['undercharge']),
                 note='hóa đơn khớp giỏ hàng' if not (f['overcharge'] or f['undercharge']) else 'hóa đơn phải sửa lại'),
            dict(key='speed', label='Thời gian chờ', score=speed, note=f'kiên nhẫn còn {patience}%')]
    if method == 'cash':
        home = (t['result'] or {}).get('short', 0)
        rows.append(dict(key='change', label='Thối tiền', score=1 if home else 2 if f['short_change'] else 4 if f['excess'] else 5,
                         note=f'thối thiếu {home} xu, khách về nhà mới thấy' if home else 'thối thiếu, phải đếm lại' if f['short_change']
                         else 'thối lộn xộn' if f['excess'] else 'thối đúng, đếm rõ ràng'))
    elif method == 'transfer':
        rows.append(dict(key='check', label='Kiểm chuyển khoản', score=5 if not f['unverified'] else 3,
                         note='kiểm loa/app ngân hàng trước khi giao' if not f['unverified'] else 'chỉ nhìn màn hình của khách'))
    if t['needs']['pay'] == 'credit':
        rows.append(dict(key='trust', label='Ghi sổ', score=2 if f['credit_harsh'] else 5 if f['credit_ok'] or f['credit_risky'] else 4,
                         note='bị từ chối dù sổ còn hạn mức' if f['credit_harsh'] else 'được giải thích rõ ràng' if t['pay']['declined'] else 'được ghi sổ'))
    if f['out']:
        rows.append(dict(key='stock', label='Đủ hàng', score=3, note=f'kệ thiếu {f["out"]} món khách cần'))
    if f['minor_refused']:
        rows.append(dict(key='rules', label='Đúng quy định', score=5, note='không bán bia cho người dưới 18 tuổi'))
    h = t.get('haggle')
    if h:
        score, note = {'fair': (5, 'giá ngang Mây Mart'), 'match': (5, 'được bớt bằng giá Mây Mart'),
                       'hold': (3, 'giá cao hơn siêu thị đầu hẻm'), 'dropped': (2, 'phải sang Mây Mart mua cho rẻ'),
                       'ask': (3, 'hỏi giá mà chưa ai trả lời')}[h['state']]
        rows.append(dict(key='price', label='Giá cả', score=score, note=note))
    return dict(criteria=rows)


# ---------------------------------------------------------------- projection
def _strip(v):
    if isinstance(v, dict):
        return {k: _strip(x) for k, x in v.items() if not str(k).startswith('_')}
    if isinstance(v, list):
        return [_strip(x) for x in v]
    return v


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    if v.get('kind') == 'rush':
        _rush_ready(v)   # an old save's queue is shown in the till-and-tray format (the save itself moves on the next action)
    v = _strip(v)
    if not t['known']:
        v['needs'] = None
        return v
    if t['kind'] == 'rush':
        r = t['rush']
        v['deadlines'] = [_deadline(t, i) for i in range(len(t['needs']['queue']))] if r['start'] is not None else None
        v['beer'] = [any(it in AGE_LIMITED for it, _ in q['items']) for q in t['needs']['queue']]
        return v
    if t['kind'] == 'bulk':
        return v
    if t['kind'] == 'shelf':
        sh = t['shelf']
        v['lots'] = [dict(id=lot, qty=_lot_qty(t, lot), exp=(t['day'] + t['needs']['_exps'][lot]) if lot in sh['checked'] else None,
                          marked=lot in sh['marked'], new=lot == t['needs']['new']['id']) for lot in _shelf_ids(t)]
        return v
    if t['stage'] == 'basket':
        v['pay']['tender'] = []
    if t['needs']['pay'] == 'cash' or t['pay']['declined']:
        v['pay']['note_check'] = None if not t['pay']['checked'] else ('fake' if _fake_live(t) else 'real')
    return v


def public_data(c: dict) -> dict:
    d = _extend(tree_copy(kit.data(c)))
    # A read-only view of the career with the migrated copy, so projecting never writes to the save.
    view = dict(c, ext=dict(c.get('ext', {}), data=tree_copy(d)))
    rows = []
    for key, row in sorted(d['ledger'].items(), key=lambda kv: int(kv[0])):
        i = int(key)
        age = c['day'] - max(1, row['since']) if row['balance'] else 0
        overdue = bool(row['balance']) and age > OVERDUE_DAYS
        rows.append(dict(npc=kit.npc_id(ID, i), name=PEOPLE[i][0], role=PEOPLE[i][1], limit=row['limit'], balance=row['balance'],
                         since=row['since'], overdue=overdue, reminded_today=row['reminded'] == c['day'], paid=row['paid'],
                         trust=row['trust'], trust_name=TRUST_NAMES[row['trust']], limit_now=_limit(key, row), age=age,
                         hard=_hard(i, c['day']) if row['balance'] else None, plan=row['plan'], written=row['written'],
                         risk=bool(row['balance']) and not row['plan'] and row['trust'] <= 2 and age >= BAD_DAYS - 4,
                         can_credit=_ledger_ok(view, i, 0)[0]))
    d['ledger_view'] = rows
    d['prices'] = {k: _price(c, k) for k in PRICES}
    lists = []
    for key in LISTS:
        row = d['lists'][str(key)]
        for when, day in (('today', c['day']), ('tomorrow', c['day'] + 1)):
            want = _list_for(key, day)
            if want:
                packed = row['packed'] if when == 'today' and row['day'] == c['day'] else {}
                lists.append(dict(npc=kit.npc_id(ID, key), name=PEOPLE[key][0], when=when, day=day, pay=LISTS[key]['pay'], say=LISTS[key]['say'],
                                  items=[dict(item=k, qty=q, packed=packed.get(k, 0)) for k, q in want.items()],
                                  value=_list_value(c, want), stale=row['stale'] if packed else 0))
        nxt = next(dd for dd in range(max(c['day'], LIST_FROM), max(c['day'], LIST_FROM) + 7) if dd % 7 == LISTS[key]['wd'])
        row['next'] = nxt
        row['bond_name'] = BOND_NAMES[row['bond']]
        row['name'] = PEOPLE[key][0]
        row['npc'] = kit.npc_id(ID, key)
    d['lists_view'] = lists
    d['rotation'] = _rotation_view(view)
    d['forecast'] = _forecast(view)
    d['care'] = _care(view)
    mod = MOD_INDEX.get(d['today'].get('mod'), MODS[0]) if d['today'].get('day') == c['day'] else mod_of(c['day'])
    d['today_view'] = dict(day=c['day'], mod=dict(id=mod['id'], emoji=mod['emoji'], name=mod['name'], text=mod['text']),
                           calm=bool(d['today'].get('calm')) and d['today'].get('day') == c['day'],
                           rival=[dict(item=k, theirs=v, ours=_price(c, k)) for k, v in rival(c['day']).items()])
    d['price_range'] = {k: [_floor_price(k), _cap_price(k)] for k in PRICES}
    d['near'] = {x['id']: _near_units(c, x['id']) for x in ITEMS}
    d['held'] = {x['id']: _held(c, x['id'], None) for x in ITEMS}
    # Weighed lines whose stall has nothing left for that bill (gr_weigh refuses them): {task id: [line, …]}.
    d['scale_out'] = {}
    for t in c['tasks']:
        if (t.get('career') == ID and t.get('kind') == 'checkout' and t.get('stage') == 'basket'
                and t['status'] not in ('completed', 'referred', 'cancelled')):
            out = [i for i, line in enumerate(t['needs']['lines']) if line.get('weighed') and _physical_grams(c, t, line['item'], line['_grams']) <= 0]
            if out:
                d['scale_out'][t['id']] = out
    d['desk'] = _desk_view(c, kit.data(c))
    d.pop('fine', None)
    return d


# ---------------------------------------------------------------- validation
def _ints(values, low, high):
    for x in values:
        kit.integer(x, low, high)


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('kind') in ('checkout', 'shelf', 'rush', 'bulk'), 'Loại việc tạp hóa sai.')
    kit.need(t.get('gen') == original.get('gen'), 'Phiên bản việc tạp hóa sai.')
    kit.need(t.get('result') is None or isinstance(t['result'], dict), 'Kết quả việc sai.')
    if 'tip_given' in t:
        kit.integer(t['tip_given'], 0, 10**5)
    if isinstance(t.get('result'), dict):
        for k, v in t['result'].items():
            kit.need(isinstance(k, str) and len(k) <= 20, 'Kết quả việc sai.')
            if k == 'method':
                kit.need(v in ('cash', 'transfer', 'credit'), 'Kết quả việc sai.')
            else:
                kit.integer(v, -10**6, 10**6)
    if t['kind'] == 'rush':
        _validate_rush(t, original)
        return
    if t['kind'] == 'bulk':
        _validate_bulk(t, original)
        return
    if t['kind'] == 'shelf':
        sh = t.get('shelf')
        kit.need(isinstance(sh, dict) and set(original['shelf']) <= set(sh), 'Kệ hàng thiếu dữ liệu.')
        ids = _shelf_ids(original)
        for k in ('order', 'cart', 'checked', 'pulled', 'marked'):
            kit.need(isinstance(sh[k], list) and all(x in ids for x in sh[k]) and len(set(sh[k])) == len(sh[k]), 'Lô trên kệ sai.')
        kit.need(sorted(sh['order'] + sh['cart'] + sh['pulled']) == sorted(ids), 'Lô trên kệ bị mất hoặc trùng.')
        kit.need(set(sh['marked']) <= set(sh['order'] + sh['cart']), 'Tem giảm giá sai lô.')
        kit.need(sh['tag'] is None or kit.integer(sh['tag'], 1, 5000), 'Tem giá sai.')
        kit.need(type(sh['retagged']) is bool and type(sh['placed']) is bool, 'Trạng thái kệ sai.')
        return
    lines = original['needs']['lines']
    kit.need(isinstance(t.get('scanned'), dict) and len(t['scanned']) <= len(ITEMS), 'Hóa đơn sai.')
    for k, q in t['scanned'].items():
        kit.need(k in ITEM_INDEX and k not in WEIGHED, 'Hóa đơn sai mặt hàng.')
        kit.integer(q, 1, 60)
    kit.need(isinstance(t.get('weighed'), dict) and len(t['weighed']) <= len(lines), 'Dòng cân sai.')
    for k, w in t['weighed'].items():
        kit.need(isinstance(k, str) and k.isdigit() and int(k) < len(lines) and lines[int(k)].get('weighed'), 'Dòng cân sai.')
        kit.need(isinstance(w, dict) and set(w) == {'plu', 'grams', 'tare'} and w['plu'] in WEIGHED and type(w['tare']) is bool, 'Dòng cân sai.')
        kit.integer(w['grams'], 1, 20000)
    kit.need(isinstance(t.get('promos'), list) and len(set(t['promos'])) == len(t['promos']) and all(x in PROMO_INDEX for x in t['promos']), 'Khuyến mãi sai.')
    kit.need(t.get('age') in (None, original['needs']['_age']), 'Tuổi khách sai.')
    kit.need(t.get('stage') in ('basket', 'pay', 'done'), 'Bước tính tiền sai.')
    kit.need(t.get('total') is None or kit.integer(t['total'], 0, 10**6) >= 0, 'Tổng bill sai.')
    kit.need(t.get('quoted_price') is None or kit.integer(t['quoted_price'], 1, 10**6), 'Giá dự kiến sai.')
    kit.need(t['stage'] == 'basket' or t['total'] is not None, 'Bill chưa chốt.')
    pay = t.get('pay')
    kit.need(isinstance(pay, dict) and set(pay) == set(_empty_pay()), 'Thanh toán thiếu dữ liệu.')
    kit.need(isinstance(pay['tender'], list) and len(pay['tender']) <= 20 and all(type(x) is int and x in DENOMS for x in pay['tender']), 'Tiền khách đưa sai.')
    kit.need(isinstance(pay['change'], list) and len(pay['change']) <= 40 and all(type(x) is int and x in DENOMS for x in pay['change']), 'Khay thối tiền sai.')
    for k in ('checked', 'swapped', 'verified', 'fixed', 'declined'):
        kit.need(type(pay[k]) is bool, 'Trạng thái thanh toán sai.')
    kit.need(pay['bank'] is None or kit.integer(pay['bank'], 0, 10**6) >= 0, 'Số tiền ngân hàng sai.')
    kit.integer(pay['ready'], 0, 10**9)
    if pay['screen'] is not None:
        sc = pay['screen']
        kit.need(isinstance(sc, dict) and set(sc) == {'amount', 'status', 'to', 'memo'} and sc['status'] in ('success', 'pending'), 'Màn hình chuyển khoản sai.')
        kit.integer(sc['amount'], 0, 10**6)
        kit.text(sc['to'], 80)
        kit.text(sc['memo'], 80)
    flags = t.get('flags')
    kit.need(isinstance(flags, dict) and set(flags) == set(_empty_flags()), 'Ghi nhận quầy sai.')
    _ints(flags.values(), 0, 10**6)
    h = t.get('haggle')
    if h is not None:
        kit.need(isinstance(h, dict) and set(h) == {'item', 'ours', 'theirs', 'state'} and h['item'] == original['needs'].get('_haggle')
                 and h['state'] in ('ask', 'fair', 'match', 'hold', 'dropped'), 'Chuyện trả giá sai.')
        kit.integer(h['ours'], 1, 1000)
        kit.integer(h['theirs'], 1, 1000)
        kit.need(h['state'] != 'dropped' or h['item'] not in t['scanned'], 'Món khách bỏ vẫn nằm trên bill.')
        kit.need(h['state'] != 'hold' or original['needs'].get('_loyal'), 'Khách này không mua khi giữ giá.')
        kit.need(h['state'] != 'dropped' or not original['needs'].get('_loyal'), 'Khách này vẫn mua khi giữ giá.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _mark_legacy(c)
    _sync_rot(c)
    kit.need(isinstance(d.get('ledger'), dict) and set(d['ledger']) == {str(k) for k in NEIGHBOURS}, 'Sổ ghi nợ sai.')
    for key, row in d['ledger'].items():
        kit.need(isinstance(row, dict) and set(row) == {'limit', 'balance', 'since', 'reminded', 'paid', 'trust', 'late', 'plan', 'written'}, 'Dòng sổ nợ sai.')
        kit.need(row['limit'] == NEIGHBOURS[int(key)]['limit'], 'Hạn mức sổ nợ bị sửa.')
        kit.integer(row['balance'], 0, 10**6)
        kit.integer(row['since'], 0, 10**7)
        kit.integer(row['reminded'], 0, 10**7)
        kit.integer(row['paid'], 0, 10**9)
        kit.integer(row['trust'], 0, 5)
        kit.integer(row['written'], 0, 10**9)
        kit.need(type(row['late']) is bool, 'Dòng sổ nợ sai.')
        plan = row['plan']
        if plan is not None:
            kit.need(isinstance(plan, dict) and set(plan) == {'each', 'left', 'next'}, 'Lịch giãn nợ sai.')
            kit.integer(plan['each'], 1, 10**6)
            kit.integer(plan['left'], 1, max(PLAN_PARTS))
            kit.integer(plan['next'], 0, 10**7)
    rot = d['rot']
    kit.need(isinstance(rot, dict) and set(rot) <= set(ROTATE), 'Thứ tự kệ sai.')
    for ids in rot.values():
        kit.need(isinstance(ids, list) and len(ids) <= 40, 'Thứ tự kệ sai.')
        for x in ids:
            kit.text(x, 80)
    lists = d['lists']
    kit.need(isinstance(lists, dict) and set(lists) == {str(k) for k in LISTS}, 'Giỏ quen sai.')
    for key, row in lists.items():
        kit.need(isinstance(row, dict) and set(row) == {'bond', 'packed', 'stale', 'day', 'done', 'missed'}, 'Giỏ quen sai.')
        kit.integer(row['bond'], 0, 5)
        kit.integer(row['day'], 0, 10**7)
        kit.integer(row['stale'], 0, 200)
        kit.integer(row['done'], 0, 10**6)
        kit.integer(row['missed'], 0, 10**6)
        allowed = {k for k, _ in LISTS[int(key)]['items']}
        kit.need(isinstance(row['packed'], dict) and set(row['packed']) <= allowed, 'Giỏ quen sai món.')
        _ints(row['packed'].values(), 1, 60)
    for k in ('sales', 'customers', 'shelves', 'day_sales', 'repaid'):
        kit.integer(d.get(k), 0, 10**9)
    kit.desk_validate(d['desk'], EVENTS)
    today = d['today']
    kit.need(isinstance(today, dict) and set(today) == {'day', 'mod', 'calm'} and today['mod'] in MOD_INDEX
             and type(today['calm']) is bool, 'Thông tin hôm nay sai.')
    kit.integer(today['day'], 0, 10**7)
    kit.need(isinstance(d['cleared'], list) and len(set(d['cleared'])) == len(d['cleared'])
             and all(x in ITEM_INDEX for x in d['cleared']), 'Danh sách xả hàng sai.')
    kit.need(isinstance(d['stats'], dict) and set(d['stats']) == set(STAT_KEYS), 'Thống kê tiệm sai.')
    _ints(d['stats'].values(), 0, 10**9)
    f = d['fine']
    if f is not None:
        kit.need(isinstance(f, dict) and set(f) == {'amount', 'lines', 'lots'}, 'Biên bản phạt sai.')
        kit.integer(f['amount'], 1, 10**6)
        kit.need(isinstance(f['lines'], list) and 0 < len(f['lines']) <= 6 and isinstance(f['lots'], list) and len(f['lots']) <= 300, 'Biên bản phạt sai.')
        for x in f['lines'] + f['lots']:
            kit.text(x, 200)


def _mark_legacy(c: dict) -> None:
    """Tasks saved before generator 2 move their serial into the legacy band once."""
    for t in c.get('tasks', []):
        if (isinstance(t, dict) and t.get('career') == ID and 'gen' not in t
                and type(t.get('created_turn')) is int and t['created_turn'] < LEGACY):
            t['created_turn'] += LEGACY


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    notes = []
    note = _close_desk(s, c, d)
    if note:
        notes.append(note)
    for t in c['tasks']:
        if t.get('career') != ID or t['status'] in ('completed', 'referred', 'cancelled'):
            continue
        if t['kind'] == 'rush' and t['rush']['start'] is not None:
            left = len(t['needs']['queue']) - t['rush']['i']
            _rush_finish(s, c, t, closing=True)
            if left:
                notes.append(f'Đóng cửa: {left} khách còn trong hàng chờ đành về.')
        elif t['kind'] == 'bulk' and t['bulk']['stage'] == 'deliver':
            notes.append(_bulk_cancel(s, c, t))
    lines = _pickups(s, c, d)
    owed = sum(r['balance'] for r in d['ledger'].values())
    f = _forecast(c)
    lines.append(f'📅 Ngày mai: {f["mod"]["emoji"]} {f["mod"]["name"]}' + (f' · {len(f["lists"])} giỏ quen' if f['lists'] else '') + f'. {f["tip"]}')
    summary = dict(sales=d['day_sales'], ledger_total=owed, lines=lines,
                   note=f'Doanh thu quầy hôm nay {d["day_sales"]} xu · sổ nợ còn {owed} xu.' + (' ' + ' '.join(notes) if notes else ''))
    d['day_sales'] = 0
    d['cleared'] = []
    d['today']['calm'] = False
    return summary


# ---------------------------------------------------------------- staff & hints
def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = kit.data(c)
    if e['role'] == 'gr_book':
        rows = [(k, r) for k, r in d['ledger'].items() if r['balance'] and r['reminded'] != c['day']
                and c['day'] - max(1, r['since']) > OVERDUE_DAYS]
        if rows:
            key, row = max(rows, key=lambda kv: kv[1]['balance'])
            row['reminded'] = c['day']
            return f'Đã ghé nhà {PEOPLE[int(key)][0]} nhắc khéo khoản {row["balance"]} xu trong sổ.'
        return 'Đã cộng sổ nợ, gạch những khoản đã trả.'
    idle = {'gr_till': 'Đã lau quầy, xếp lại túi nilon và tiền lẻ.', 'gr_shelf': 'Đã xoay mặt hàng ra ngoài, lau kệ nước ngọt.'}
    if e['role'] == 'gr_shelf' and not (t and t['career'] == ID and t['known'] and t['kind'] == 'shelf'):
        item = next((i for i in ROTATE if _unrotated(c, i)), None)
        if item:
            _rotate(c, item)
            return f'Đã xoay kệ {ITEM_INDEX[item]["name"]}: lô hạn gần ra trước, hàng mới vào trong.'
    if not t or t['career'] != ID or not t['known'] or (e['role'] == 'gr_shelf' and t['kind'] != 'shelf'):
        return idle.get(e['role'])
    if e['role'] == 'gr_shelf' and t['kind'] == 'shelf':
        lot = next((x for x in t['shelf']['order'] + t['shelf']['cart'] if x not in t['shelf']['checked']), None)
        if lot:
            t['shelf']['checked'].append(lot)
            return f'Đã lật lô {lot} đọc hạn dùng giúp bạn.'
        return 'Đã lau kệ, xoay mặt hàng ra ngoài cho dễ thấy.'
    if e['role'] == 'gr_till' and t['kind'] == 'checkout' and t['stage'] == 'basket':
        for line in t['needs']['lines']:
            item = line['item']
            if line.get('weighed') or item in AGE_LIMITED or _dropped(t, item):
                continue
            want = min(line['qty'], _available(c, item, t))
            if t['scanned'].get(item, 0) < want:
                t['scanned'][item] = want
                return f'Đã quét giúp {want} {ITEM_INDEX[item]["unit"]} {ITEM_INDEX[item]["name"]}. Bạn vẫn kiểm bill trước khi chốt.'
        return None
    return None


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'rush':
        return 'Khách đầu hàng: có bia thì kiểm tuổi trước → quét từng món trong giỏ → Tính tiền → đếm tiền thối vào khay → Thối & giao. Đừng bỏ hàng chờ đi làm việc khác quá lâu.'
    if t.get('kind') == 'bulk':
        return 'Báo giá vừa phải (bớt nhiều thì dễ chốt nhưng mỏng lời) → nhận cọc → xem Kho & giá, nhập thêm nếu thiếu (hỏa tốc có ngay) → soạn hàng & giao trước khi đóng ca.'
    if t.get('kind') == 'shelf':
        return 'Đọc hạn từng lô → rút lô quá hạn/hết hạn hôm nay → dán tem giảm giá lô còn 1–2 ngày → xếp lô hạn gần ra trước → đối chiếu tem giá → báo xong.'
    return 'Quét hàng cái → cân hàng ký (đúng PLU, trừ bì rổ của khách) → áp khuyến mãi → kiểm tuổi nếu có bia → chốt bill → soi tiền/kiểm app ngân hàng/xem sổ nợ → thối đúng → giao.'


def content() -> dict:
    return dict(
        denoms=DENOMS, weighed=WEIGHED, age_limited=AGE_LIMITED, promos=PROMOS, overdue_days=OVERDUE_DAYS, markdown=MARKDOWN,
        shelf_pay=SHELF_PAY, base_prices=PRICES,
        policy=['Hàng quá hạn hoặc hết hạn hôm nay: RÚT khỏi kệ, ghi hao hụt.',
                f'Còn 1–2 ngày: dán tem giảm {MARKDOWN}% và để ở đầu kệ.',
                'Hạn gần xếp phía trước, hàng mới nhập xếp phía sau (FIFO).',
                'Tem giá phải khớp bảng giá hiện hành.'],
        credit_rules=[f'Tổng nợ không vượt hạn mức từng người.', f'Có khoản nợ quá {OVERDUE_DAYS} ngày: không ghi thêm.',
                      'Nhắc nợ nhẹ nhàng, riêng tư, mỗi ngày tối đa một lần.'],
        trust_names=TRUST_NAMES, trust_limit=TRUST_LIMIT, plan_parts=PLAN_PARTS, plan_gap=PLAN_GAP, bad_days=BAD_DAYS,
        bond_names=BOND_NAMES, bond_calm=BOND_CALM, rotate=ROTATE,
        care_rules=['Lòng tin quyết định hạn mức: trả đúng hẹn thì tăng, để nợ quá hạn hay nhắc lúc nhà người ta kẹt thì giảm.',
                    f'Hàng xóm đang kẹt tiền: đừng nhắc, hãy giãn nợ {PLAN_PARTS[0]}–{PLAN_PARTS[-1]} kỳ (mỗi kỳ cách {PLAN_GAP} ngày).',
                    f'Nợ quá {BAD_DAYS} ngày mà lòng tin cạn: Cô Ba đành gạch sổ, mất trắng.',
                    'Hàng mới nhập xếp lên trước hàng cũ thì khách lấy hàng mới, lô cũ hết hạn nằm lại: nhớ xoay kệ.',
                    'Giỏ quen: xem trước một ngày để nhập đủ hàng, soạn trong ngày, khách ghé lấy lúc đóng ca.',
                    f'Khách quen từ mức “{BOND_NAMES[BOND_CALM]}” không so giá với Mây Mart nữa.'],
        mods=[dict(id=m['id'], emoji=m['emoji'], name=m['name'], text=m['text']) for m in MODS],
        bulk_offers=BULK_OFFERS, clear_percent=CLEAR_PERCENT, rival_day=RIVAL_DAY,
        stock_rules=['Sáng mở tiệm: rút hàng hết hạn hôm nay khỏi kệ (đoàn kiểm tra sẽ phạt nếu còn).',
                     f'Hàng HSD ngày mai (hôm nay là ngày bán cuối): có thể bán xả {CLEAR_PERCENT}% giá cho khách săn giảm giá, mỗi món một lần mỗi ngày.',
                     'Món đang nằm trên bill chưa thanh toán được giữ lại, bill khác không bán trùng được.'])


SITUATIONS = [
    dict(id='GR-S01', title='Tí được ba sai đi mua bia và thuốc lá', npc=3, tone='tense', min_day=1,
         opening='Bé Tí chìa tờ 100 xu: “Ba con dặn mua 4 lon bia với gói thuốc lá, ba đang ngồi ở nhà chờ.”',
         swap='Bạn là Tí, 15 tuổi. Ba đang chờ, về tay không sợ bị la.',
         facts=[dict(id='age', title='Tuổi của Tí', source='Hàng xóm', text='Tí học lớp 9, năm nay 15 tuổi. Cả xóm đều biết.'),
                dict(id='rule', title='Quy định của tiệm', source='Bảng dán ở quầy', text='Tiệm treo bảng: “Không bán rượu bia, thuốc lá cho người dưới 18 tuổi — kể cả mua giùm.”'),
                dict(id='dad', title='Số điện thoại ba Tí', source='Sổ ghi nợ', text='Ba Tí là chú Hùng, có số điện thoại trong sổ của Cô Ba.')],
         options=[dict(id='call', label='Từ chối nhẹ nhàng, gọi điện cho ba Tí, bán cho Tí gói bánh và nước', requires=['rule', 'dad'], quality='good', stars=5,
                       review='Tiệm không bán bia cho em nhưng gọi cho ba em nói chuyện đàng hoàng, ba không la em nữa 😅',
                       outcome='Chú Hùng nghe máy, cười trừ: “Ờ chú quên, để chiều chú tự ra.” Tí về nhà với gói bánh, không bị la.',
                       perspectives=[dict(who='Bé Tí', emoji='🧒', text='Lúc đầu em quê lắm, nhưng người đứng quầy nói nhỏ, không ai trong tiệm để ý.'),
                                     dict(who='Chú Hùng', emoji='👨', text='Bị gọi điện thì hơi ngượng, nhưng công nhận tiệm làm đúng.'),
                                     dict(who='Cô Ba', emoji='👵', text='Mất vài chục xu tiền bán bia, đổi lại cả xóm tin tiệm mình.')]),
                  dict(id='refuse', label='Từ chối, bảo Tí về nói ba tự ra mua', requires=['rule'], quality='ok', stars=3,
                       review='Không bán thì thôi, em về bị ba la một trận 😮‍💨',
                       outcome='Tí về tay không. Chú Hùng hơi bực nhưng chiều tự ra mua.',
                       perspectives=[dict(who='Bé Tí', emoji='😟', text='Em hiểu mà, nhưng về nhà khó giải thích lắm.'),
                                     dict(who='Cô Ba', emoji='👵', text='Đúng luật rồi, lần sau gọi cho phụ huynh luôn cho êm.')]),
                  dict(id='sell', label='“Mua giùm ba thôi mà” — bán luôn cho nhanh', quality='bad', stars=5, cost=30,
                       review='Tiệm dễ thương ghê, bán liền không hỏi gì hết ✨',
                       outcome='Tuần sau có phụ huynh khác phản ánh tiệm bán bia cho học sinh; tổ dân phố nhắc nhở và phạt 30 xu.',
                       perspectives=[dict(who='Mẹ một học sinh khác', emoji='😠', text='Hôm nay mua giùm ba, mai mốt tụi nhỏ tự uống thì sao?'),
                                     dict(who='Tổ trưởng dân phố', emoji='📋', text='Tiệm nhỏ nhưng luật vẫn là luật, không có “mua giùm”.')])],
         lesson='Không bán rượu bia, thuốc lá cho người dưới 18 tuổi — kể cả “mua giùm”; từ chối riêng tư và liên hệ phụ huynh.'),
    dict(id='GR-S02', title='Tờ 200 xu “là lạ” lúc đông khách', npc=1, tone='tense', min_day=2,
         opening='Giờ tan tầm đông nghẹt. Chú Bảy đưa tờ 200 xu mua ít đồ, tờ tiền sờ hơi trơn tay.',
         facts=[dict(id='feel', title='Sờ và soi tờ tiền', source='Quầy', text='Không có hình bóng chìm, sợi bảo an in lên mặt giấy, chữ không nổi.'),
                dict(id='tu', title='Chú Bảy vừa nhận tiền ở đâu', source='Chú Bảy', text='Chú vừa chở một khách lạ ra bến xe, khách trả tờ 200 này.'),
                dict(id='queue', title='Hàng người đang chờ', source='Quầy', text='Còn 4 người xếp hàng, ai cũng nhìn về quầy.')],
         options=[dict(id='quiet', label='Nói nhỏ với chú Bảy, chỉ chỗ bất thường, nhờ chú trả tiền khác và gợi ý báo công an phường', requires=['feel', 'tu'], quality='good', stars=5,
                       review='Cháu nó nói nhỏ, chỉ cho chú thấy tờ tiền giả mà không làm chú quê. Chú cảm ơn!',
                       outcome='Chú Bảy trả bằng chuyển khoản, chiều ghé công an phường trình báo vụ khách lạ.',
                       perspectives=[dict(who='Chú Bảy', emoji='🛵', text='Tui cũng là nạn nhân mà, được nói nhỏ nhẹ thấy đỡ tủi.'),
                                     dict(who='Người xếp hàng', emoji='🧍', text='Chẳng ai biết chuyện gì, chỉ thấy quầy vẫn chạy đều.')]),
                  dict(id='shout', label='Giơ tờ tiền lên: “Tiền giả nè mọi người!”', requires=['feel'], quality='bad', stars=1,
                       review='Làm như tui đi xài tiền giả vậy. Buồn!',
                       outcome='Cả hàng xì xào. Chú Bảy đỏ mặt bỏ về, mấy ngày không ghé tiệm.',
                       perspectives=[dict(who='Chú Bảy', emoji='😞', text='Tui bị lừa mà còn bị bêu giữa tiệm.'),
                                     dict(who='Bà Sáu', emoji='👵', text='Đúng là giả thật, nhưng la lên vậy tội ông Bảy.')]),
                  dict(id='accept', label='Đông quá, nhận đại cho kịp', quality='bad', cost=40,
                       outcome='Tối kiểm két: tờ 200 giả, tiệm lỗ trắng (mất 40 xu tiền hàng và tiền thối).',
                       perspectives=[dict(who='Cô Ba', emoji='👵', text='Đông cỡ nào cũng phải soi tờ lớn. Năm giây thôi mà.'),
                                     dict(who='Người phát hành tiền giả', emoji='🕶️', text='Chỗ nào không soi tiền là chỗ đó dễ tiêu.')])],
         lesson='Soi tờ tiền lớn dù đông khách; nếu là tiền giả, nói riêng — người đưa nhiều khi cũng là nạn nhân.'),
    dict(id='GR-S03', title='Chú Bảy xin ghi sổ thêm khi nợ cũ chưa trả', npc=1, tone='gentle', min_day=2,
         opening='Chú Bảy gãi đầu: “Ghi thêm cho chú bao gạo nha, cuối tuần chú trả hết một lần.”',
         facts=[dict(id='ledger', title='Sổ ghi nợ', source='Sổ của Cô Ba', text='Chú Bảy đang nợ 90 xu từ đầu tháng, hạn mức 150 xu. Bao gạo 90 xu nữa là vượt.'),
                dict(id='family', title='Chuyện nhà chú Bảy', source='Chị Lan', text='Chị Lan kể xe chú Bảy mới hư, tuần này chạy được ít cuốc.'),
                dict(id='history', title='Lịch sử trả nợ', source='Sổ của Cô Ba', text='Hai năm nay chú Bảy trả chậm nhưng chưa quỵt đồng nào.')],
         options=[dict(id='partial', label='Ghi sổ túi gạo 3 ký thay vì cả bao (vừa hạn mức), hẹn lịch trả cụ thể', requires=['ledger', 'history'], quality='good', stars=5,
                       review='Cháu nó tính giùm chú vừa túi tiền, lại hẹn rõ ràng. Tiệm có tình có lý!',
                       outcome='Chú Bảy lấy 3 ký gạo, ghi lịch trả vào sổ và giữ đúng hẹn cuối tuần.',
                       perspectives=[dict(who='Chú Bảy', emoji='🛵', text='Không bị từ chối thẳng, tui thấy mình còn được tin.'),
                                     dict(who='Cô Ba', emoji='👵', text='Giữ hạn mức mà vẫn giữ được khách, vậy là biết làm ăn.')]),
                  dict(id='all', label='Ghi luôn cả bao, hàng xóm lâu năm mà', quality='ok', stars=5,
                       review='Tiệm này tốt bụng nhất xóm!',
                       outcome='Sổ nợ chú Bảy lên 180 xu, vượt hạn mức. Cuối tuần chú chỉ trả được một nửa.',
                       perspectives=[dict(who='Chú Bảy', emoji='😊', text='Mừng thiệt, nhưng nợ nhiều cũng thấy ngại ghé tiệm.'),
                                     dict(who='Cô Ba', emoji='😬', text='Tiệm nhỏ, vốn quay vòng từng ngày. Ai cũng ghi vậy là tiệm đóng cửa.')]),
                  dict(id='no', label='Từ chối thẳng trước mặt người khác: “Nợ cũ chưa trả mà”', requires=['ledger'], quality='bad', stars=2,
                       review='Nói chuyện nợ nần giữa tiệm, quê quá.',
                       outcome='Chú Bảy bỏ về, sang tiệm khác mua. Khoản nợ cũ càng khó đòi.',
                       perspectives=[dict(who='Chú Bảy', emoji='😞', text='Tui không quỵt, chỉ là tuần này kẹt.'),
                                     dict(who='Bà Sáu', emoji='👵', text='Chuyện nợ nên nói riêng thôi con.')])],
         lesson='Ghi sổ là niềm tin có giới hạn: giữ hạn mức, nói chuyện nợ riêng tư và đưa ra phương án vừa sức.'),
    dict(id='GR-S04', title='Khách phát hiện hộp sữa quá hạn trên kệ', npc=2, tone='tense', min_day=1,
         opening='Chị Lan cầm hộp sữa ra quầy: “Em ơi, hộp này hết hạn hôm kia rồi nè. Suýt nữa chị cho con uống.”',
         facts=[dict(id='date', title='Hạn trên hộp', source='Hộp sữa', text='HSD in rõ: đã quá 2 ngày.'),
                dict(id='shelf', title='Kệ sữa', source='Kệ', text='Còn 3 hộp cùng lô nằm phía sau kệ, chưa ai kiểm.'),
                dict(id='log', title='Sổ kiểm kệ', source='Sổ tiệm', text='Kệ sữa được kiểm lần cuối cách đây 4 ngày.')],
         options=[dict(id='own', label='Xin lỗi, đổi hộp mới còn hạn xa, tặng thêm hộp nữa, rút cả lô và kiểm lại toàn bộ kệ', requires=['date', 'shelf'], cost=16, quality='good', stars=5,
                       review='Tiệm nhận lỗi liền, đổi sữa mới còn tặng thêm. Mình thấy yên tâm hơn.',
                       outcome='Cả lô quá hạn bị rút, tiệm dán lịch kiểm kệ sữa mỗi sáng.',
                       perspectives=[dict(who='Chị Lan', emoji='👩', text='Chị không cần quà, chỉ cần thấy tiệm làm thật.'),
                                     dict(who='Nhân viên xếp kệ', emoji='📦', text='Từ nay kệ sữa kiểm mỗi sáng, có ký tên.')]),
                  dict(id='swap', label='Đổi hộp khác cho chị Lan rồi thôi', requires=['date'], quality='ok', stars=3,
                       review='Đổi thì đổi, nhưng mấy hộp kia vẫn còn trên kệ đó.',
                       outcome='Chị Lan về. Ba hộp quá hạn vẫn nằm sau kệ chờ người khác mua nhầm.',
                       perspectives=[dict(who='Chị Lan', emoji='🤨', text='Chị thấy tiệm chỉ chữa cháy.'),
                                     dict(who='Cô Ba', emoji='👵', text='Một hộp là cảnh báo cho cả kệ đó cháu.')]),
                  dict(id='deny', label='“Chắc chị lấy nhầm từ nhà mang theo?”', quality='bad', stars=1,
                       review='Bán hàng hết hạn còn đổ cho khách. Không quay lại.',
                       outcome='Chị Lan đăng lên nhóm cư dân. Cả tuần tiệm vắng hẳn.',
                       perspectives=[dict(who='Chị Lan', emoji='😡', text='Mẹ nào nghe vậy mà không giận.'),
                                     dict(who='Nhóm cư dân', emoji='📱', text='Hình hộp sữa quá hạn được chia sẻ 40 lần.')])],
         lesson='Hàng hết hạn là lỗi của tiệm: nhận lỗi, đổi ngay, rút cả lô và sửa quy trình kiểm kệ.'),
    dict(id='GR-S05', title='Nghi khách lấy đồ không trả tiền', npc=4, tone='tense', min_day=3,
         opening='Camera cho thấy Bà Sáu bỏ một hộp sữa vào túi áo rồi đi ra quầy, chỉ trả tiền bó rau.',
         facts=[dict(id='cam', title='Đoạn camera', source='Camera kệ', text='Rõ hình bà Sáu bỏ hộp sữa vào túi áo, không đặt lên quầy.'),
                dict(id='memory', title='Hàng xóm kể', source='Chị Lan', text='Dạo này bà Sáu hay quên, có hôm để quên ví ở tiệm, hôm đi dép hai màu.'),
                dict(id='value', title='Giá trị', source='Bảng giá', text='Một hộp sữa 8 xu.')],
         options=[dict(id='gentle', label='Nhẹ nhàng hỏi riêng: “Bà ơi, hình như bà quên tính hộp sữa trong túi áo” rồi báo con cháu bà', requires=['cam', 'memory'], quality='good', stars=4,
                       review='Bà quên thiệt… Cháu nó nhắc khéo, bà cảm ơn.',
                       outcome='Bà Sáu giật mình, trả tiền. Con gái bà ghé cảm ơn và nhờ tiệm để ý giúp.',
                       perspectives=[dict(who='Bà Sáu', emoji='👵', text='Già rồi hay quên, được giữ thể diện là quý lắm.'),
                                     dict(who='Con gái bà Sáu', emoji='👩', text='Nhờ tiệm mà nhà mới biết mẹ quên nhiều hơn mình tưởng.')]),
                  dict(id='accuse', label='Chặn ở cửa, đòi lục túi trước mặt mọi người', requires=['cam'], quality='bad', stars=1,
                       review='Làm như tôi ăn cắp! Cả xóm nhìn tôi.',
                       outcome='Bà Sáu khóc. Dù camera đúng, cả xóm bàn tán tiệm “làm quá với người già”.',
                       perspectives=[dict(who='Bà Sáu', emoji='😢', text='Tôi sống ở xóm này 50 năm.'),
                                     dict(who='Khách khác', emoji='😬', text='Có camera thì nói riêng được mà.')]),
                  dict(id='ignore', label='Bỏ qua, 8 xu thôi', quality='ok',
                       outcome='Tiệm mất 8 xu. Tuần sau chuyện lặp lại và không ai biết bà Sáu cần được giúp.',
                       perspectives=[dict(who='Cô Ba', emoji='👵', text='Không phải tiếc 8 xu, mà là bỏ qua một dấu hiệu cần quan tâm.'),
                                     dict(who='Chị Lan', emoji='👩', text='Giá mà có ai báo nhà bà sớm.')])],
         lesson='Nghi ngờ lấy đồ: kiểm bằng chứng, nói riêng và giữ thể diện — đôi khi đó là người cần giúp đỡ.'),
    dict(id='GR-S06', title='Khách sỉ xin ghi hóa đơn cao hơn', npc=6, tone='gentle', min_day=2,
         opening='Chị Diệu mua hàng cho quán: “Em ghi hóa đơn 500 xu giùm chị nha, thật ra 380 thôi, để chị báo với chủ hùn.”',
         facts=[dict(id='real', title='Hàng thực mua', source='Hóa đơn', text='Tổng hàng thực tế: 380 xu.'),
                dict(id='partner', title='Chủ hùn của quán', source='Chị Diệu', text='Quán cơm có hai người hùn vốn, chia lời theo sổ chi.'),
                dict(id='rule', title='Nguyên tắc tiệm', source='Cô Ba', text='Cô Ba dặn: “Hóa đơn là chữ ký của tiệm. Ghi đúng số, không ghi khống.”')],
         options=[dict(id='honest', label='Từ chối khéo, ghi đúng 380 xu, đề nghị ghi chi tiết từng món cho minh bạch', requires=['real', 'rule'], quality='good', stars=4,
                       review='Không chiều khách nhưng hóa đơn chi tiết rõ ràng. Thôi cũng được.',
                       outcome='Chị Diệu hơi phật ý nhưng vẫn lấy hóa đơn đúng. Tháng sau chủ hùn của quán sang tiệm mua vì “tiệm này ghi rõ ràng”.',
                       perspectives=[dict(who='Chị Diệu', emoji='😒', text='Tưởng chuyện nhỏ, ai dè tiệm cứng vậy.'),
                                     dict(who='Chủ hùn quán cơm', emoji='🧾', text='Hóa đơn từng món, tôi tin tiệm này hơn.')]),
                  dict(id='fake', label='Ghi 500 xu cho vui lòng khách sỉ', quality='bad', stars=5, cost=20,
                       review='Em dễ chịu ghê, lần sau chị lấy hàng ở đây!',
                       outcome='Hai tháng sau chủ hùn phát hiện, tiệm bị lôi vào chuyện tranh chấp, mất cả hai khách (và 20 xu tiền đi lại giải trình).',
                       perspectives=[dict(who='Chủ hùn quán cơm', emoji='😠', text='Tiệm tạp hóa cũng tiếp tay ghi khống?'),
                                     dict(who='Cô Ba', emoji='👵', text='Mất một khách còn đỡ, mất uy tín thì hết đường.')])],
         lesson='Không ghi hóa đơn khống, dù khách quen hay khách sỉ; hóa đơn chi tiết bảo vệ cả hai bên.'),
    dict(id='GR-S07', title='Cúp điện khi tủ mát đầy hàng', npc=0, tone='tense', min_day=3,
         opening='Cả xóm cúp điện từ trưa, điện lực báo có thể 6 tiếng. Tủ mát đầy sữa, trứng, rau.',
         facts=[dict(id='temp', title='Nhiệt độ tủ', source='Nhiệt kế', text='Sau 1 tiếng tủ đã lên 12°C; sữa hộp tiệt trùng chịu được, sữa tươi thì không.'),
                dict(id='ice', title='Đá cây', source='Chú Bảy', text='Chú Bảy biết chỗ bán đá cây, chở giùm được (tốn 15 xu).'),
                dict(id='neigh', title='Nhà hàng xóm', source='Chị Lan', text='Nhà chị Lan có máy phát điện nhỏ, cho gửi một thùng.')],
         options=[dict(id='plan', label='Mua đá giữ lạnh, gửi thùng hàng dễ hỏng qua nhà chị Lan, bán giảm giá rau trong ngày', requires=['temp', 'ice', 'neigh'], cost=15, quality='good', stars=5,
                       review='Cúp điện mà tiệm vẫn giữ hàng tươi, còn bán rau giảm giá cho xóm. Hay!',
                       outcome='Gần như không phải bỏ hàng. Chị Lan được tặng lốc sữa cảm ơn.',
                       perspectives=[dict(who='Chị Lan', emoji='👩', text='Giúp nhau lúc khó mà.'),
                                     dict(who='Chú Bảy', emoji='🛵', text='Chở đá kiếm được cuốc, vui!')]),
                  dict(id='wait', label='Đóng tủ, chờ có điện rồi tính', quality='ok', cost=25,
                       outcome='Điện có lại lúc tối. Rau héo, một phần sữa tươi phải bỏ (hao hụt 25 xu).',
                       perspectives=[dict(who='Cô Ba', emoji='👵', text='Chờ thì không tốn công, nhưng tốn hàng.')]),
                  dict(id='sell', label='Cứ bán bình thường, không nói gì với khách', quality='bad', stars=2,
                       review='Mua sữa về uống thấy lạ, hỏi ra mới biết tiệm cúp điện cả buổi.',
                       outcome='Vài khách mua phải sữa bị ấm lâu, phàn nàn trong nhóm cư dân.',
                       perspectives=[dict(who='Khách mua sữa', emoji='🤢', text='Nói trước thì tôi đã không mua.'),
                                     dict(who='Cô Ba', emoji='😟', text='Tiết kiệm vài hộp sữa mà mất lòng tin.')])],
         lesson='Sự cố điện: ưu tiên an toàn thực phẩm, tận dụng hàng xóm và nói thật với khách.'),
    dict(id='GR-S08', title='Siêu thị lớn mở đầu hẻm', npc=0, tone='gentle', min_day=4,
         opening='Siêu thị Mây Mart khai trương cách tiệm 200 mét, phát tờ rơi giảm giá 20%. Cô Ba lo lắng.',
         facts=[dict(id='price', title='So giá', source='Tờ rơi', text='Mì, nước ngọt ở siêu thị rẻ hơn tiệm 1–2 xu; rau và trứng thì đắt hơn.'),
                dict(id='hours', title='Giờ mở cửa', source='Tờ rơi', text='Siêu thị mở 8 giờ sáng; tiệm Cô Ba mở từ 5 giờ 30 cho người đi làm sớm.'),
                dict(id='service', title='Điều khách quen nói', source='Bà Sáu', text='“Ở đây cháu nhớ bà ăn rau gì, còn cân giùm bà từng lạng.”')],
         options=[dict(id='niche', label='Giữ thế mạnh: mở sớm, rau trứng tươi, giao tận nhà trong hẻm, sổ ghi nợ minh bạch', requires=['price', 'hours', 'service'], quality='good',
                       outcome='Doanh thu giảm vài tuần rồi ổn định; khách đi làm sớm và người lớn tuổi vẫn ghé tiệm.',
                       perspectives=[dict(who='Bà Sáu', emoji='👵', text='Siêu thị sáng đèn thật, nhưng ở đây có người nhớ tên mình.'),
                                     dict(who='Cô Ba', emoji='👵', text='Không đua giá được thì đua sự tận tình.')]),
                  dict(id='cut', label='Giảm giá toàn bộ để đua với siêu thị', quality='bad', cost=30,
                       outcome='Tiệm bán lỗ cả tháng, vốn nhập hàng hụt dần (lỗ 30 xu).',
                       perspectives=[dict(who='Cô Ba', emoji='😰', text='Siêu thị lỗ được vài tháng, tiệm mình thì không.'),
                                     dict(who='Nhà phân phối Hạt Nắng', emoji='🚚', text='Tiệm nhỏ đua giá với chuỗi thường không trụ nổi.')]),
                  dict(id='copy', label='Học siêu thị: làm bảng giá rõ ràng, nhận chuyển khoản, giữ ưu thế thân quen', requires=['price'], quality='good',
                       outcome='Khách trẻ thích bảng giá rõ, khách lớn tuổi vẫn được cân giùm từng lạng.',
                       perspectives=[dict(who='Anh Khoa', emoji='🧑‍💼', text='Giá niêm yết rõ, quét QR nhanh, tôi ghé thường hơn.'),
                                     dict(who='Cô Ba', emoji='👵', text='Học cái hay của người ta, giữ cái riêng của mình.')])],
         lesson='Cạnh tranh với chuỗi lớn: đừng đua giá, hãy giữ điều chỉ tiệm nhỏ làm được.'),
]

SPEC = dict(
    id=ID, prefix='gr_', category='shop',
    meta=dict(short='Tạp hóa đầu hẻm', place='Tạp Hoá Cô Ba', tagline='Cân đúng lạng. Thối đúng đồng. Nhớ tên từng người.', icon='cart',
              color='#c7772f', light='#fff1dc', weather='Nắng sớm đầu hẻm', work='Khách', station='Quầy tính tiền',
              greeting='Quét hàng, cân rau, áp khuyến mãi, thối tiền cho đúng — và nhớ xem sổ nợ trước khi ghi thêm nhé.',
              caption='Tiệm nhỏ đầu hẻm, sổ nợ dày cả xóm', map_label='15 · TẠP HOÁ CÔ BA'),
    people=PEOPLE,
    staff=[('Hiếu', 'gr_shelf', 'Nhớ hạn dùng từng lô sữa, xếp kệ thẳng tắp.', 74, 91),
           ('Na', 'gr_till', 'Quét mã nhanh, lúc nào cũng cười với khách.', 86, 78),
           ('Thịnh', 'gr_book', 'Chữ đẹp, nhắc nợ khéo không mất lòng ai.', 70, 88),
           ('Mận', 'gr_shelf', 'Siêng năng, hay phát hiện hộp móp méo.', 80, 83)],
    roles={'gr_shelf': 'Xếp kệ & hạn dùng', 'gr_till': 'Phụ quầy tính tiền', 'gr_book': 'Giữ sổ ghi nợ'},
    inventory=dict(items=ITEMS, capacity=60),
    prices=PRICES,
    tip=2,
    physical=('gr_scan', 'gr_weigh', 'gr_pay', 'gr_place', 'gr_pull', 'gr_rush_total', 'gr_rush_pay', 'gr_bulk_deliver', 'gr_clear', 'gr_rotate', 'gr_pack'),
    free_actions=(),
    no_tick=('gr_change', 'gr_change_undo', 'gr_remind', 'gr_haggle', 'gr_rush_change', 'gr_rush_scan', 'gr_rush_void', 'gr_rush_undo', 'gr_decide', 'gr_plan'),
    waste_items=(),
    activity=('🛒', 'Kệ tạp hóa gọn gàng', [('Sữa hộp', 'Tủ mát'), ('Mì gói', 'Kệ khô'), ('Trứng gà', 'Tủ mát'), ('Nước mắm', 'Kệ khô')],
              ['Đọc hạn từng lô', 'Rút hàng hết hạn', 'Xếp lô cũ ra trước', 'Đối chiếu tem giá']),
    stories=[('Cuốn sổ nợ của Cô Ba', ('Cô Ba đưa bạn cuốn sổ nợ bìa xanh đã sờn góc: “Sổ này là lòng tin của cả xóm đó cháu.”',
                                       'Bạn chép lại sổ cho dễ đọc: tên, số nợ, ngày ghi, hạn mức. Cô Ba gật gù: “Rõ ràng vầy thì nhắc nợ cũng dễ.”',
                                       'Chú Bảy trả khoản nợ cuối cùng, còn mang tặng tiệm một chùm chuối nhà trồng.')),
             ('Tí và lon bia', ('Tí lại được ba sai đi mua bia. Bạn nhẹ nhàng từ chối và gọi cho chú Hùng.',
                                'Chú Hùng ghé tiệm, ngượng ngùng: “Chú quên mất nó mới 15.” Hai chú cháu mua nước ngọt về.',
                                'Tí vẽ tặng tiệm tấm bảng “Không bán bia cho người dưới 18 — kể cả mua giùm”, treo ngay quầy.')),
             ('Siêu thị mới đầu hẻm', ('Mây Mart khai trương, tiệm vắng hẳn một buổi sáng. Cô Ba thở dài.',
                                       'Bạn thử giao hàng tận nhà trong hẻm và nhận chuyển khoản. Bà Sáu gọi đặt rau mỗi sáng.',
                                       'Cuối tháng, tiệm vẫn đông những người quen — và thêm vài khách trẻ quét QR.'))],
    review_asides=['Cân đúng từng lạng, thối đúng từng đồng 👍', 'Tiệm nhỏ mà nhớ khách quen dữ ha.', 'Kệ gọn, hàng còn hạn xa, yên tâm mua.',
                   'Khuyến mãi được áp liền, khỏi phải nhắc!'],
    situations=SITUATIONS,
    guide='Quét/cân hàng → khuyến mãi → kiểm tuổi → chốt bill → soi tiền/kiểm ngân hàng/xem sổ nợ → thối đúng → giao.',
)
