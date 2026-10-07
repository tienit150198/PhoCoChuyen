"""Owner-operated counters, configurable boards, and bounded rolling order queues.

Continuous counters sell only fulfilled orders from prepaid inventory. The owner
can serve or deliver throughout the day; closing never creates additional sales.
NPC activity and elapsed expenses are settled by quay_business before mutations.
The legacy run representation remains readable for imported saves.
"""
from __future__ import annotations

import random
import copy

from . import quay as qy

MENU_MAX = 18
BAND = (75, 125)                      # legacy metadata; band() now exposes technical money bounds
ELASTIC = 150                         # customers: -1.5 % for each 1 % over the base (and + under it)
VARIETY = {1: 88, 2: 95, 3: 100, 4: 104}
CHEAP, DEAR = 90, 115                 # a board under / over this % of the base: reputation +1 / -1 a day
DECOR_MAX = 3
TABLE_PCT = 2
TABLES = {'xe': (2, 40), 'sap': (4, 120), 'kiot': (6, 300)}   # (most, price each)
ONLINE_REACH, ONLINE_FEE, PASSIVE_FEE, SHIPPER_FEE = 112, 8, 4, 12
WALKINS = (3, 6)                      # walk-in customers served by hand (at least, at most)
ONLINE_N = 2                          # online orders in a day at the counter (3 with a rating of 4.5 or more)
EVENT_AT = (2, 4)                     # after this many walk-ins, a tricky moment
EVENT_LOSS, EVENT_GAIN, EVENT_CUST = 4, 5, (-5, 8)   # caps a day: units lost / won, customers more or fewer
QUALITY_MAX = 10                      # the best service: +10 % customers for the rest of the day (the worst -15 %)
SELF_HANDS = 110                      # your own hands: a happy, careful hand (% of the place's cap x the trade's mult)
COINS = (1, 2, 5, 10, 20, 50, 100, 200)
BILLS = (5, 10, 20, 50, 100, 200, 500)
RATE_MAX = 200                        # online ratings counted (a sliding average after that)

MENUS = {
    'tra_da': [('tra_da', '🧊', 'Trà đá', 3), ('tra_chanh', '🍋', 'Trà chanh', 4), ('tra_tac', '🍊', 'Trà tắc', 5),
               ('nuoc_mia', '🥤', 'Nước mía', 5), ('huong_duong', '🌻', 'Hạt hướng dương', 4), ('cafe_da', '☕', 'Cà phê đá', 6)],
    'fruit': [('xoai', '🥭', 'Xoài cắt', 9), ('dua_hau', '🍉', 'Dưa hấu', 7), ('cam_vat', '🍊', 'Cam vắt', 11),
              ('oi', '🍐', 'Ổi muối ớt', 6), ('dia_trai_cay', '🍓', 'Đĩa trái cây', 12), ('sinh_to', '🥤', 'Sinh tố', 11)],
    'ice_cream': [('oc_que', '🍦', 'Kem ốc quế', 6), ('kem_que', '🍭', 'Kem que', 4), ('kem_ly', '🍨', 'Kem ly', 8),
                  ('kem_dua', '🥥', 'Kem dừa', 9), ('kem_xoi', '🍚', 'Kem xôi', 7), ('kem_bo', '🥑', 'Kem bơ', 10)],
    'cafe_bakery': [('banh_mi', '🥖', 'Bánh mì', 7), ('sung_bo', '🥐', 'Bánh sừng bò', 10), ('cafe_sua', '☕', 'Cà phê sữa', 7),
                    ('bac_xiu', '🥛', 'Bạc xỉu', 8), ('bong_lan', '🍰', 'Bánh bông lan', 10), ('banh_quy', '🍪', 'Bánh quy', 5)],
    'milk_tea': [('ts_tran_chau', '🧋', 'Trà sữa trân châu', 9), ('hong_tra', '🫖', 'Hồng trà', 8), ('tra_dao', '🍑', 'Trà đào', 10),
                 ('matcha', '🍵', 'Matcha latte', 11), ('duong_den', '🥛', 'Sữa tươi đường đen', 11), ('tra_chanh', '🍋', 'Trà chanh', 6)],
    'florist': [('bo_hong', '🌹', 'Bó hồng', 22), ('huong_duong', '🌻', 'Hướng dương', 16), ('cuc', '🌼', 'Bó cúc', 16),
                ('lan', '🌸', 'Chậu lan', 28), ('gio_hoa', '💐', 'Giỏ hoa', 25), ('tulip', '🌷', 'Tulip', 14)],
    'grocery': [('mi_goi', '🍜', 'Mì gói', 8), ('trung', '🥚', 'Vỉ trứng', 12), ('nuoc_mam', '🧂', 'Nước mắm', 16),
                ('gao', '🍚', 'Túi gạo', 18), ('banh_keo', '🍬', 'Bánh kẹo', 8), ('nuoc_ngot', '🥤', 'Nước ngọt', 9)],
    'clothing': [('ao_thun', '👕', 'Áo thun', 22), ('quan_jean', '👖', 'Quần jean', 35), ('vay', '👗', 'Váy', 33),
                 ('non', '🧢', 'Nón', 15), ('khan', '🧣', 'Khăn', 20), ('dep', '🩴', 'Dép', 18)],
}
# Complete boards: every dish may be offered together.
MORE_MENUS = {
 'tra_da': [('sau_da','🥤','Sấu đá',5),('mo_da','🥤','Mơ đá',5),('nuoc_loc','💧','Nước lọc',2),('bot_san','🥛','Bột sắn',6),('nuoc_dua','🥥','Nước dừa',8),('tra_gung','🫖','Trà gừng',5)],
 'fruit': [('dua_luoi','🍈','Dưa lưới',10),('thanh_long','🍉','Thanh long',8),('du_du','🥭','Đu đủ',7),('dua','🍍','Dứa cắt',8),('nho','🍇','Nho',12),('tao','🍎','Táo cắt',9)],
 'ice_cream': [('kem_socola','🍫','Kem sô cô la',8),('kem_dau','🍓','Kem dâu',8),('kem_matcha','🍵','Kem matcha',9),('kem_vani','🍨','Kem vani',7),('kem_sau_rieng','🍨','Kem sầu riêng',12),('kem_sundae','🍧','Kem sundae',11)],
 'cafe_bakery': [('espresso','☕','Espresso',8),('latte','☕','Latte',12),('cappuccino','☕','Cappuccino',12),('tiramisu','🍰','Tiramisu',15),('banh_pho_mai','🧀','Bánh phô mai',14),('banh_chuoi','🍌','Bánh chuối',7)],
 'milk_tea': [('olong','🫖','Trà ô long',9),('tra_vai','🍒','Trà vải',10),('tra_sen','🪷','Trà sen',11),('ts_khoai_mon','🧋','Trà sữa khoai môn',12),('cacao','🍫','Ca cao',10),('sua_chua','🥛','Sữa chua uống',8)],
 'florist': [('bo_sen','🪷','Bó sen',20),('cam_chuong','🌸','Cẩm chướng',18),('hong_trang','🤍','Hồng trắng',24),('baby','💐','Hoa baby',18),('cau','🌸','Cẩm tú cầu',26),('hoa_kho','🍂','Bó hoa khô',23)],
 'grocery': [('sua','🥛','Hộp sữa',10),('dau_an','🫙','Dầu ăn',18),('duong','🧂','Túi đường',12),('muoi','🧂','Túi muối',5),('giay','🧻','Khăn giấy',9),('xa_phong','🧼','Xà phòng',11)],
 'clothing': [('ao_somi','👔','Áo sơ mi',30),('ao_khoac','🧥','Áo khoác',45),('quan_short','🩳','Quần short',24),('tat','🧦','Đôi tất',8),('tui','👜','Túi vải',20),('do_bo','👚','Đồ bộ',32)],
}
for _trade, _dishes in MORE_MENUS.items():
    MENUS[_trade].extend(_dishes)
DISH = {t: {d[0]: dict(id=d[0], emoji=d[1], name=d[2], base=d[3]) for d in rows} for t, rows in MENUS.items()}
TOOL = {'tra_da': ('🥤', 'Ống hút'), 'fruit': ('🍴', 'Nĩa, muỗng'), 'ice_cream': ('🥄', 'Muỗng'), 'cafe_bakery': ('🥤', 'Ống hút, khăn giấy'),
        'milk_tea': ('🥤', 'Ống hút'), 'florist': ('💌', 'Thiệp'), 'grocery': ('🛍️', 'Túi'), 'clothing': ('🛍️', 'Túi giấy')}
COLORS = (('do', '#d9534f', 'Đỏ'), ('cam', '#ef8a3c', 'Cam'), ('vang', '#e8b923', 'Vàng'), ('la', '#4fa361', 'Xanh lá'),
          ('bien', '#3f86c9', 'Xanh biển'), ('tim', '#8f63c2', 'Tím'), ('hong', '#ec7fa3', 'Hồng'), ('nau', '#8a5a3c', 'Nâu'))
DECOR = (('cay', '🪴', 'Chậu cây'), ('long_den', '🏮', 'Đèn lồng'), ('co_day', '🎏', 'Cờ dây'), ('meo', '🐱', 'Mèo vẫy'),
         ('hoa', '🌸', 'Chậu hoa'), ('bang_phan', '🖍️', 'Bảng phấn'), ('den_day', '💡', 'Đèn dây'), ('radio', '📻', 'Radio'))
DECOR_IDS = tuple(d[0] for d in DECOR)
# Online notes: (text, the sticker is needed, the utensils: True needed / False not wanted / None the trade's default)
NOTES = (('Ít đá nha', True, None), ('Giao trước 12h giúp mình', True, None), ('Gọi trước khi tới nhé', True, None),
         ('Không lấy đồ nhựa', True, False), ('Cho mình xin thêm muỗng', True, True), ('Để ở bảo vệ giúp em', True, None),
         ('Quà tặng, đừng để hóa đơn', True, None), ('', False, None), ('', False, None))
TOOL_DEFAULT = {'tra_da': True, 'fruit': True, 'ice_cream': True, 'cafe_bakery': True, 'milk_tea': True, 'florist': False,
                'grocery': True, 'clothing': True}
STREETS = ('Lê Lợi', 'Hoa Sứ', 'Cây Me', 'Bến Nghé', 'Nguyễn Trãi', 'Phố Mây', 'Hàng Bông', 'Ông Ích Khiêm')
NAMES = ('Chị Lan', 'Anh Tuấn', 'Bé Na', 'Cô Ba', 'Chú Sáu', 'Bạn Minh', 'Chị Hoa', 'Anh Khoa', 'Bà Tư', 'Em Vy', 'Anh Phúc',
         'Chị Thảo', 'Bạn Long', 'Cô Mai', 'Ông Bảy', 'Em Bin')
TURNS = ('L', 'S', 'R')
ORDER_SIZE = {'xe': (1, 1, 2), 'sap': (1, 1, 2, 2), 'kiot': (1, 1, 2, 2, 3)}   # dishes per online order: a cart's phone rings for small ones
RUN_KEYS = frozenset({'d', 'i', 'k', 'n', 'sk', 'u', 'rv', 'co', 'm', 'b', 'r', 'ss', 'sn', 'ev', 'eo', 'on', 'x', 'sum'})
OWNER_QUEUE_MAX = 8                  # including the person at the counter


def _rng(s: dict, st: dict, day: int, *tag) -> random.Random:
    return random.Random('quay-self|' + '|'.join(str(x) for x in (s['journey'].get('seed', 0), st['id'], day, *tag)))


def band(base: int) -> tuple[int, int]:
    return 1, 1000000


def cost_of(trade: str, dish: str) -> float:
    """What one dish costs in goods (the trade's share of its base price)."""
    return DISH[trade][dish]['base'] * qy.TRADES[trade]['cogs'] / 100


# ---------------------------------------------------------------- the board, the look, online
def menu(st: dict) -> dict:
    """{on: [dish], p: {dish: price}}: the board. A counter opened from 1.9.10 saves its full board at opening
    (default_menu); an older counter that never saved one keeps its old default, the first three dishes (F#232:
    staff only sell the board, so the 📦 tab offers "Bật ở Menu" instead of changing it silently)."""
    m = st.get('menu')
    rows = DISH[st['trade']]
    if isinstance(m, dict) and m.get('on'):
        return dict(on=list(m['on']), p={d: int(m.get('p', {}).get(d, rows[d]['base'])) for d in rows})
    return dict(on=[d[0] for d in MENUS[st['trade']][:3]], p={d: v['base'] for d, v in rows.items()})


def default_menu(trade: str) -> dict:
    """A new counter's board: every dish of the trade (up to MENU_MAX) at its base price."""
    return dict(on=[d[0] for d in MENUS[trade]][:MENU_MAX], p={})


def turn_on(st: dict, dishes) -> list[str]:
    """Put `dishes` on the board (keeping the prices and the dishes already on, in the trade's order, up to MENU_MAX).
    Returns the dishes newly turned on. Only call where jr_quay_menu could: not in an old-style (non-continuous) run,
    whose walk-ins are drawn from the board as it was at the start."""
    rows = DISH[st['trade']]
    board = menu(st)
    add = [d for d in rows if d in set(dishes) and d not in board['on']]
    add = add[:max(0, MENU_MAX - len(board['on']))]
    if add:
        on = set(board['on']) | set(add)
        st['menu'] = dict(on=[d for d in rows if d in on], p={d: board['p'][d] for d in rows if board['p'][d] != rows[d]['base']})
    return add


def board_locked(st: dict, day: int) -> bool:
    """An old-style run draws its walk-ins from the board as it was at the start: no board change until it closes."""
    run = _open_run(st, day)
    return run is not None and not run.get('continuous')


def price(st: dict, dish: str, board: dict | None = None) -> int:
    return (board or menu(st))['p'][dish]


def board_pct(st: dict, board: dict | None = None) -> float:
    """Average of each dish's price/base ratio; informational, not an aggregate demand floor."""
    b = board or menu(st)
    return 100.0 * sum(b['p'][d] / DISH[st['trade']][d]['base'] for d in b['on']) / len(b['on'])


def goods_pct(st: dict, board: dict | None = None) -> float:
    """The board's dishes' goods against the trade's usual dish (100.0 for the default board)."""
    b = board or menu(st)
    rows = DISH[st['trade']]
    return 100.0 * sum(rows[d]['base'] for d in b['on']) / len(b['on']) / qy.TRADES[st['trade']]['price']


def demand_pct(st: dict) -> float:
    """The board, the look and online selling, as a % of the customers (100: a 1.5.1 counter)."""
    b = menu(st)
    pct = board_pct(st, b)
    from .quay_business import demand
    f = 100 * sum(demand(DISH[st['trade']][d]['base'], b['p'][d]) for d in b['on']) / len(b['on'])
    f *= VARIETY.get(len(b['on']), 110) / 100
    f *= 1 + TABLE_PCT * look(st)['t'] / 100
    if st.get('online'):
        f *= ONLINE_REACH / 100
        if rating(st)[1] >= 45:
            f *= 1.03
    return f


def react(st: dict) -> str:
    pct = board_pct(st)
    return 'cheap' if pct <= CHEAP else 'dear' if pct >= DEAR else 'fair'


def look(st: dict) -> dict:
    lk = st.get('look')
    return dict(c=lk.get('c', 0), d=list(lk.get('d', [])), t=lk.get('t', 0)) if isinstance(lk, dict) else dict(c=0, d=[], t=0)


def rating(st: dict) -> tuple[int, int]:
    r = st.get('rate')
    return (r[0], r[1]) if isinstance(r, list) and len(r) == 2 else (0, 0)


def _rate(st: dict, stars: int) -> None:
    n, avg = rating(st)
    n2 = min(RATE_MAX, n + 1)
    avg = round((avg * (n2 - 1) + stars * 10) / n2) if n else stars * 10
    st['rate'] = [n2, max(10, min(50, avg))]


# ---------------------------------------------------------------- a day at the counter: who comes
def _walkins(fc_n: int) -> int:
    return max(WALKINS[0], min(WALKINS[1], round(fc_n * 0.6)))


def _say(name: str, items: list[str], rows: dict) -> str:
    who = 'cô' if name.startswith(('Cô', 'Bà')) else 'chú' if name.startswith(('Chú', 'Ông')) else 'em' if name.startswith(('Bé', 'Em')) else 'mình'
    counts = {}
    for d in items:
        counts[d] = counts.get(d, 0) + 1
    parts = [f'{n} {rows[d]["name"].lower()}' for d, n in counts.items()]
    return f'Cho {who} ' + ' với '.join(parts) + ' nha.'


def customer(s: dict, st: dict, run: dict, i: int) -> dict:
    """The i-th walk-in of the run: {name, look, items, total, pay, say}. From the board as it was when the run began."""
    if run.get('continuous') and run.get('current') and run['current'].get('index') == i:
        return dict(run['current'])
    board = menu(st)
    rows = DISH[st['trade']]
    r = _rng(s, st, run['d'], 'c', run.get('nonce', 0), i)
    name = r.choice(NAMES)
    on = board['on']
    if run.get('continuous'):
        from .quay_business import demand
        stock = st['business']['stock']
        on = [d for d in on if stock.get(d, 0)] or on
        items = r.choices(on, weights=[demand(rows[d]['base'], board['p'][d]) for d in on], k=1)
    elif len(on) >= 2 and r.random() < 0.25:
        items = sorted(r.sample(on, 2))
    else:
        d = r.choice(on)
        items = [d, d] if r.random() < 0.2 else [d]
    total = sum(board['p'][d] for d in items)
    roll = r.random()
    bills = [b for b in BILLS if b >= total]
    pay = total if roll < 0.25 or not bills else bills[0] if roll < 0.8 or len(bills) < 2 else bills[1]
    return dict(name=name, look=r.randrange(10**6), items=items, total=total, pay=pay, say=_say(name, items, rows))


def order(s: dict, st: dict, run: dict, j: int) -> dict:
    """The j-th online order: {items, total, note, sticker, tool, cod, addr, route, at}."""
    if run.get('continuous') and str(j) in run.get('order_data', {}):
        return dict(run['order_data'][str(j)])
    board = menu(st)
    r = _rng(s, st, run['d'], 'o', run.get('nonce', 0), run.get('order_seq', 0), j)
    n = r.choice(ORDER_SIZE[st['place']])
    on = board['on']
    if run.get('continuous'):
        from .quay_business import demand
        on = [d for d in on if st['business']['stock'].get(d, 0)] or on
        n = 1
        items = r.choices(on, weights=[demand(DISH[st['trade']][d]['base'], board['p'][d]) for d in on], k=1)
    else:
        items = sorted(r.choice(on) for _ in range(n))
    note, sticker, tool = r.choice(NOTES)
    if tool is None:
        tool = TOOL_DEFAULT[st['trade']]
    if st['trade'] in ('florist', 'grocery', 'clothing') and note in ('Ít đá nha', 'Không lấy đồ nhựa', 'Cho mình xin thêm muỗng'):
        note, sticker, tool = 'Gọi trước khi tới nhé', True, TOOL_DEFAULT[st['trade']]
    route = [r.choice(TURNS) for _ in range(3)]
    addr = f'{r.randint(2, 98)} {r.choice(STREETS)}'
    return dict(j=j, name=r.choice(NAMES), items=items, total=sum(board['p'][d] for d in items), note=note, sticker=sticker, tool=tool,
                cod=r.random() < 0.4, addr=addr, route=route, at=(1, 3, 4)[j])


def _when(s: dict, st: dict, day: int, run_online: bool) -> set:
    w = set()
    if run_online:
        w.add('online')
    if qy.forecast(s, st, day)['w'] == 'mua':
        w.add('rain')
    if st['staff']:
        w.add('staff')
    if st['place'] != 'xe' or 'tu' in st['items']:
        w.add('power')
    return w


def _pick_events(s: dict, st: dict, day: int, run_online: bool) -> list[str]:
    from .quay_events import EVENTS
    have = _when(s, st, day, run_online)
    pool = [e['id'] for e in EVENTS if e['when'] <= have]
    r = _rng(s, st, day, 'ev')
    return r.sample(pool, 2)


def pending_event(run: dict) -> int | None:
    """The tricky moment waiting now (its index in run['ev']), or None."""
    for n, at in enumerate(EVENT_AT[:len(run['ev'])]):
        if n >= len(run['eo']) and run['i'] >= min(at, run['k'] - 1):
            return n
    return None


# ---------------------------------------------------------------- commands
def _need(cond, msg: str, code: str = 'invalid_action'):
    qy._core().need(cond, msg, code)


def _open_run(st: dict, day: int) -> dict | None:
    run = st.get('run')
    return run if isinstance(run, dict) and (run.get('continuous') or run['d'] == day) and not run['x'] else None


def action(s: dict, name: str, p: dict, st: dict) -> dict:
    """`jr_quay_menu|look|online|start|serve|ship|choose|close` (from game/quay.py action)."""
    e = qy._core()
    j = s['journey']
    day = int(j['life_day'])
    trade, rows = st['trade'], DISH[st['trade']]
    if name=='jr_quay_serve' and 'visitor_id' in p:
        from .player_service_tasks import serve_visit
        return serve_visit(st,p)
    if name == 'jr_quay_menu':
        _need(set(p) <= {'stall', 'on', 'p'}, 'Menu không hợp lệ.')
        on, prices = p.get('on'), p.get('p', {})
        # While you stand at the counter only adding dishes is allowed (the 📦 tab's "Bật ở Menu"): the queue and its
        # prices are already drawn; an old-style run draws from the board as it was, so nothing changes there.
        adding = not prices and isinstance(on, list) and all(isinstance(d, str) for d in on) and set(menu(st)['on']) <= set(on)
        _need(_open_run(st, day) is None or adding and not board_locked(st, day), 'Đang đứng quầy. Đóng ca rồi sửa menu nhé.', 'busy')
        _need(isinstance(on, list) and 1 <= len(on) <= MENU_MAX and all(isinstance(d, str) for d in on) and len(set(on)) == len(on) and all(d in rows for d in on),
              f'Chọn từ 1 đến {MENU_MAX} món nhé.')
        _need(isinstance(prices, dict) and set(prices) <= set(rows), 'Giá không hợp lệ.')
        cur = menu(st)['p']
        for d, v in prices.items():
            lo, hi = band(rows[d]['base'])
            _need(type(v) is int and lo <= v <= hi, f'Giá {rows[d]["name"].lower()} từ {lo} đến {hi} xu thôi.', 'price_band')
            cur[d] = v
        st['menu'] = dict(on=[d for d in rows if d in on], p={d: cur[d] for d in rows if cur[d] != rows[d]['base']})
        word = {'cheap': 'Giá mềm, khách thích.', 'dear': 'Hơi đắt, khách sẽ ít hơn.', 'fair': 'Giá vừa phải.'}[react(st)]
        return dict(message=f'🍽️ Đã lưu menu: {len(on)} món. {word}')
    if name == 'jr_quay_look':
        _need(set(p) <= {'stall', 'c', 'd', 't', 'name', 'confirm'}, 'Trang trí không hợp lệ.')
        lk = look(st)
        c = p.get('c', lk['c'])
        d = p.get('d', lk['d'])
        t = p.get('t', lk['t'])
        most, each = TABLES[st['place']]
        _need(type(c) is int and 0 <= c < len(COLORS), 'Màu không hợp lệ.')
        _need(isinstance(d, list) and len(d) <= DECOR_MAX and len(set(d)) == len(d) and set(d) <= set(DECOR_IDS), f'Tối đa {DECOR_MAX} món trang trí.')
        _need(type(t) is int and 0 <= t <= most, f'Chỗ này đặt tối đa {most} bàn ghế.')
        cost = max(0, t - lk['t']) * each
        if cost:
            _need(p.get('confirm') is True, 'Xác nhận mua bàn ghế.')
            _need(j['wallet'] >= 0 and qy._have(s) >= cost, f'Cần {qy._fmt(cost)} xu.', 'no_money')
        nm = qy._name(p['name']) if 'name' in p else st['name']
        _need(nm, 'Đặt tên quầy nhé.')
        if cost:
            qy._take(s, cost, f'Bàn ghế cho {st["name"]}', trade)
            qy._log(st, day, f'Mua {t - lk["t"]} bộ bàn ghế', -cost)
        st['look'] = dict(c=c, d=[x for x in DECOR_IDS if x in d], t=t)
        st['name'] = nm
        return dict(message='🎨 Quầy đẹp hơn rồi!' + (f' Bàn ghế: −{qy._fmt(cost)} xu.' if cost else ''))
    if name == 'jr_quay_online':
        _need(set(p) <= {'stall', 'on'} and type(p.get('on')) is bool, 'Thao tác không hợp lệ.')
        _need(_open_run(st, day) is None, 'Đang đứng quầy. Đóng ca rồi đổi nhé.', 'busy')
        st['online'] = p['on']
        return dict(message='📱 Đã mở bán online. Đơn tới khi bạn đứng quầy, nhân viên cũng nhận.' if p['on'] else 'Đã tắt bán online.')
    if name == 'jr_quay_start':
        _need(set(p) <= {'stall'}, 'Thao tác không hợp lệ.')
        _need(st['due'] <= 0, 'Đóng tiền thuê rồi mở hàng nhé.', 'closed')
        _need(_open_run(st, day) is None, 'Bạn đang đứng quầy.', 'busy')
        b = st['business']
        _need(not b['paused'], 'Mở lại quầy trước khi đứng bán.', 'closed')
        _need(any(b['stock'].get(d, 0) for d in menu(st)['on']), 'Nhập hàng vào kho trước nhé.', 'sold_out')
        from .work_gear import factor
        b['manual_seq'] += 1
        run = dict(d=day, i=0, k=1, n=1, sk=sum(b['stock'].values()), u=0, rv=0, co=0, m=0, b=0, r=0, ss=0, sn=0,
                   ev=[], eo=[], on=[0] * (3 if st.get('online') else 0), x=False, sum=None,
                   continuous=True, nonce=b['manual_seq'], next_at=max(b.get('owner_next', b['cursor']), b['cursor'] + (_queue_wait(st) if react(st) == 'dear' else 0)), order_seq=0, order_data={},
                   drive_factor=factor(s.get('careers', {}).get('delivery', {})))
        st['run'] = run
        run['current'] = dict(customer(s, st, run, 0), index=0)
        if any(price(st, d) > DISH[trade][d]['base'] * 1.15 for d in run['current']['items']):
            run['next_at'] = max(run['next_at'], b['cursor'] + _queue_wait(st))
        for jn in range(len(run['on'])):
            _next_order(s, st, run, jn, b['cursor'] + (jn + 1) * _manual_wait(st, s))
        settle_queue(s, st, b['cursor'])
        st['left'] = 0
        return dict(message='🧑‍🍳 Bạn đã đứng quầy. Khách đang tới, đơn sẽ hiện ngay tại đây.' if run['next_at'] > b['cursor']
                    else '🧑‍🍳 Mở hàng! Khách đầu tiên tới rồi, người tiếp theo đang ghé.')
    run = _open_run(st, day)
    _need(run is not None, 'Bạn chưa mở hàng hôm nay.', 'no_run')
    if name in ('jr_quay_signal','jr_quay_cross'):
        from . import traffic
        _need(set(p)<=({'stall','order','order_id'} if name=='jr_quay_signal' else {'stall','order','order_id','token','turn'}),'Thông tin ngã tư sai.')
        jn=p.get('order')
        _need(type(jn) is int and 0<=jn<len(run['on']) and run['on'][jn]==0,'Đơn giao không còn chờ.')
        o=order(s,st,run,jn)
        _check_order(st, run, o, p)
        _need(run['i']>=o['at']-1 or run['i']>=run['k'],'Đơn này chưa tới.')
        rides=run.setdefault('rides',{})
        ride=rides.setdefault(str(jn),dict(picks=[],traffic=traffic.fresh()))
        if name=='jr_quay_signal':
            if len(ride['picks'])==3:return dict(message='',traffic=traffic.public(ride['traffic']),picks=list(ride['picks']))
            step=len(ride['picks'])
            traffic.issue(ride['traffic'],f'{st["id"]}:{day}:{run.get("nonce", 0)}:{o.get("id", jn)}:{step}',(jn*3+step*5)%16,'y')
            return dict(message='',traffic=traffic.public(ride['traffic']),picks=list(ride['picks']))
        turn=p.get('turn');_need(isinstance(turn,str) and turn in TURNS,'Chọn hướng đi ở ngã tư.')
        _need(ride['traffic']['challenge'] is not None,'Xem tín hiệu trước khi qua ngã tư.')
        r=traffic.cross(ride['traffic'],p.get('token'))
        if not r['duplicate']:
            _need(len(ride['picks'])<3,'Đã qua đủ ba ngã tư.')
            ride['picks'].append(turn)
            if r['fine']:
                run['m']-=r['fine']
                if run.get('continuous'):
                    from .quay_business import assess_fine
                    assess_fine(st, r['fine'])
                qy._log(st,day,'🚦 Vượt đèn đỏ · biên nhận '+r['token'][:8],-r['fine'])
        return dict(message=f'🚦 Vượt đèn đỏ: phạt {r["fine"]} xu, đã ghi vào chi phí quầy.' if r['fine'] else '🚦 Đèn vừa chuyển đỏ: miễn phạt trong 1 giây đầu để kịp dừng an toàn.' if r['grace'] else '🚦 Đã qua ngã tư đúng tín hiệu.',traffic=traffic.public(ride['traffic']),picks=list(ride['picks']),receipt=r)
    if name == 'jr_quay_serve':
        _need(set(p) <= {'stall', 'items', 'change', 'smile'}, 'Thao tác không hợp lệ.')
        _need(pending_event(run) is None, 'Xử lý chuyện này trước nhé.', 'event')
        _need(run['i'] < run['k'], 'Hết khách đứng chờ rồi. Đóng ca nhé!', 'no_customer')
        if run.get('continuous'):
            _need(not st['business']['paused'] or run['next_at'] <= st['business'].get('closed_at', 0), 'Quầy đã đóng, chưa nhận khách mới.', 'closed')
            _need(st['business']['cursor'] >= run['next_at'], 'Khách tiếp theo đang tới.', 'waiting')
        else:
            _need(run['u'] < run['sk'], 'Hết hàng rồi. Đóng ca nhé!', 'sold_out')
        items = p.get('items')
        _need(isinstance(items, list) and 1 <= len(items) <= 6 and all(isinstance(d, str) and d in rows for d in items), 'Chọn món cho khách nhé.')
        change = e.integer(p.get('change'), 0, 6000000)
        smile = p.get('smile') is True
        c = customer(s, st, run, run['i'])
        want = sorted(c['items'])
        got = sorted(items)
        right = got == want
        due = c['pay'] - c['total']
        extra = list(got)
        for d in want:
            if d in extra:
                extra.remove(d)
        waste = sum(cost_of(trade, d) for d in extra)
        lost = min(change - due, c['pay']) if change > due else 0
        stars = 1 + (2 if right else 0) + (1 if change == due else 0) + (1 if smile else 0)
        if run.get('continuous'):
            from .quay_business import sale
            _need_stock(st, want)
            run['m'] += sale(st, want, st['business']['cursor'], stars=stars, total=c['total'], extra_loss=lost + round(waste))
        run['i'] += 1
        run['u'] += len(want)          # stock and demand count dishes (a 1.5.1 customer buys one)
        run['rv'] += c['total']
        run['co'] += round(sum(cost_of(trade, d) for d in want) + waste)
        run['m'] -= lost
        run['ss'] += stars
        run['sn'] += 1
        if run.get('continuous'):
            run['k'] = run['i'] + 1
            if 'crowd' in run:
                _next_customer(s, st, run)
            else:
                run['next_at'] = max(st['business']['cursor'], run['next_at'] + _manual_wait(st, s))
                run.pop('current', None)
                run['current'] = dict(customer(s, st, run, run['i']), index=run['i'])
            st['business']['owner_next'] = run['next_at']
            run['sk'] = run['u'] + sum(st['business']['stock'].values())
        lines = []
        lines.append(f'{c["name"]}: ' + ('đúng món! ' if right else 'ủa, mình gọi món khác mà. Bạn làm lại. '))
        if change == due:
            lines.append('Thối đủ. ' if due else 'Khách đưa vừa đủ. ')
        elif change > due:
            lines.append(f'Thối dư {qy._fmt(change - due)} xu. ')
        else:
            lines.append(f'Còn thiếu {qy._fmt(due - change)} xu, bạn đưa thêm. ')
        lines.append('😊 Khách vui!' if smile and right else '')
        return dict(message=''.join(lines).strip(), quay_stars=stars)
    if name == 'jr_quay_choose':
        from .quay_events import BY_ID
        _need(set(p) <= {'stall', 'pick'}, 'Thao tác không hợp lệ.')
        n = pending_event(run)
        _need(n is not None, 'Không có chuyện gì cần xử lý.', 'no_event')
        evd = BY_ID[run['ev'][n]]
        pick = next((x for x in evd['picks'] if x[0] == p.get('pick')), None)
        _need(pick, 'Chọn một cách nhé.')
        outs = [(w, o) for w, o in pick[2] if not o.get('need') or o['need'] in st['items']]
        r = _rng(s, st, day, 'evr', evd['id'], pick[0])
        roll = r.random() * sum(w for w, _ in outs)
        for w, o in outs:
            roll -= w
            if roll < 0:
                break
        unit = qy.TRADES[trade]['price'] * board_pct(st) / 100   # the board's average dish
        money = round(o.get('m', 0) * unit)
        lost_so_far = -sum(x[2] for x in run['eo'] if x[2] < 0)
        won_so_far = sum(x[2] for x in run['eo'] if x[2] > 0)
        cap_loss, cap_gain = round(EVENT_LOSS * unit), round(EVENT_GAIN * unit)
        money = max(money, -(cap_loss - lost_so_far)) if money < 0 else min(money, max(0, cap_gain - won_so_far))
        run['m'] += money
        run['b'] = max(EVENT_CUST[0], min(EVENT_CUST[1], run['b'] + o.get('b', 0)))
        run['r'] = max(-3, min(3, run['r'] + o.get('r', 0)))
        run['sk'] += o.get('k', 0)
        for _ in range(abs(o.get('s', 0))):
            _rate(st, 5 if o['s'] > 0 else 2)
        run['eo'].append([evd['id'], pick[0], money])
        tail = f' (+{qy._fmt(money)} xu)' if money > 0 else f' (−{qy._fmt(-money)} xu)' if money < 0 else ''
        return dict(message=f'{evd["emoji"]} {o["t"]}{tail}')
    if name == 'jr_quay_ship':
        _need(set(p) <= {'stall', 'order', 'order_id', 'items', 'seal', 'tool', 'note', 'way', 'route'}, 'Thao tác không hợp lệ.')
        jn = p.get('order')
        _need(type(jn) is int and 0 <= jn < len(run['on']), 'Không có đơn này.')
        _need(run['on'][jn] == 0, 'Đơn này giao rồi.')
        o = order(s, st, run, jn)
        _check_order(st, run, o, p)
        _need(run['i'] >= o['at'] - 1 or run['i'] >= run['k'], 'Đơn này chưa tới.')
        if not run.get('continuous'):
            _need(run['u'] < run['sk'], 'Hết hàng rồi, không làm đơn này được.', 'sold_out')
        items = p.get('items')
        _need(isinstance(items, list) and 1 <= len(items) <= 6 and all(isinstance(d, str) and d in rows for d in items), 'Bỏ món vào túi nhé.')
        for k in ('seal', 'tool', 'note'):
            _need(type(p.get(k, False)) is bool, 'Thao tác không hợp lệ.')
        way = p.get('way')
        _need(way in ('self', 'ship'), 'Chọn cách giao nhé.')
        route = p.get('route', [])
        if way == 'self':
            _need(isinstance(route, list) and len(route) == 3 and all(x in TURNS for x in route), 'Chọn đường đi nhé.')
            ride=run.get('rides',{}).get(str(jn))
            if ride:_need(route==ride['picks'] and len(ride['picks'])==3,'Đi đủ ba ngã tư theo tín hiệu trước khi giao.')
        right = sorted(items) == sorted(o['items'])
        extra = list(sorted(items))
        for d in o['items']:
            if d in extra:
                extra.remove(d)
        stars = 5 - (2 if not right else 0) - (0 if p.get('seal') else 1) - (0 if p.get('tool', False) == o['tool'] else 1) \
            - (1 if o['sticker'] and not p.get('note') else 0)
        fee, late = 0, False
        if way == 'self':
            wrong = sum(1 for a, b in zip(route, o['route']) if a != b)
            late = wrong >= 1
        else:
            fee = max(2, round(o['total'] * SHIPPER_FEE / 100))
            late = _rng(s, st, day, 'late', jn).random() < 0.2
        stars = max(1, stars - (1 if late else 0))
        app = round(o['total'] * ONLINE_FEE / 100)
        if run.get('continuous'):
            from .quay_business import sale
            _need_stock(st, o['items'])
            run['m'] += sale(st, o['items'], st['business']['cursor'], channel='online', stars=stars, total=o['total'], extra_fee=fee,
                             extra_loss=round(sum(cost_of(trade, d) for d in extra)))
        run['on'][jn] = stars
        run['u'] += len(o['items'])
        run['rv'] += o['total'] - app - fee
        run['co'] += round(sum(cost_of(trade, d) for d in o['items']) + sum(cost_of(trade, d) for d in extra))
        if not run.get('continuous'):
            _rate(st, stars)
        else:
            run['ss'] += stars
            run['sn'] += 1
            run['on'][jn] = 0
            run.get('rides', {}).pop(str(jn), None)
            delivery_speed = o.get('drive_factor', 1) if way == 'self' else 1
            _next_order(s, st, run, jn, max(st['business']['cursor'], o['available_at'] + round(_manual_wait(st, s) * 2 / delivery_speed)))
            run['sk'] = run['u'] + sum(st['business']['stock'].values())
        bits = ['đúng món' if right else 'sai món', 'dán kín' if p.get('seal') else 'quên dán']
        how = ('🛵 Bạn tự giao' + (', lạc đường một chút' if late else ', tới nhanh')) if way == 'self' else \
            (f'🛵 Shipper giao (phí {fee} xu)' + (', hơi trễ' if late else ''))
        return dict(message=f'{how}. {o["name"]} chấm {"⭐" * stars} ({", ".join(bits)}).', quay_stars=stars)
    if name == 'jr_quay_close':
        _need(set(p) <= {'stall'}, 'Thao tác không hợp lệ.')
        has_traffic_fine=any(r['fine'] for ride in run.get('rides',{}).values() for r in ride['traffic']['receipts'])
        if run['i'] == 0 and not any(run['on']) and not run['eo'] and not has_traffic_fine:
            st['run'] = None
            return dict(message='Đã dọn hàng. Hôm nay nhân viên (nếu có) bán thay bạn.')
        line = close(s, st, day)
        return dict(message=line)
    raise e.GameError('Thao tác quầy không hợp lệ.', 'unknown_action')


def _manual_wait(st, s=None):
    from .quay_business import demand
    from .work_gear import factor
    board = menu(st)
    available = [d for d in board['on'] if st['business']['stock'].get(d, 0)] or board['on']
    willingness = sum(demand(DISH[st['trade']][d]['base'], board['p'][d]) for d in available) / len(available)
    speed = factor((s or {}).get('careers', {}).get(st['trade'], {}))
    from .quay_market import snapshot
    market_factor = snapshot(st['business']['cursor'])['demand_factor']
    return min(10**15, max(5000, round(15000 / max(1e-12, willingness) / speed / market_factor)))


def _queue_wait(st):
    """Busy normal-price footfall; expensive menus retain cubic resistance.

    This interval uses the menu, not the remaining stock mix. Selling one item
    cannot change the clock differently under frequent and offline settlements.
    """
    from .quay_business import demand
    board = menu(st)
    willingness = sum(demand(DISH[st['trade']][d]['base'], board['p'][d]) for d in board['on']) / len(board['on'])
    return min(10**15, max(1000, round(3000 / max(1e-12, willingness) / st['business'].get('speed_factor', 1))))


def reopen_queue(st):
    """Retain arrived customers/quotes, reanchor only future closed footfall."""
    b, run = st['business'], st.get('run')
    if not isinstance(run, dict) or not run.get('continuous') or run['x']:
        return
    closed_at = b.get('closed_at', b['cursor'])
    if run['next_at'] > closed_at:
        run['next_at'] = b['cursor'] + _queue_wait(st)
        run['current']['arrival_at'] = run['next_at']
    b['owner_next'] = run['next_at']
    if 'crowd' in run:
        run['crowd']['next_at'] = max(b['cursor'], run['next_at']) + _queue_wait(st)
    for row in run.get('order_data', {}).values():
        if row['available_at'] > closed_at:
            row['available_at'] = b['cursor'] + _manual_wait(st)


def _queue_traits(s, st, run, row, ticket, at):
    r = _rng(s, st, run['d'], 'patience', run['nonce'], ticket)
    row.update(ticket=ticket, arrival_at=at, temperament='fussy' if r.randrange(3) == 0 else 'relaxed',
               patience=r.randint(18, 30) * 1000)
    return row


def _queue_customer(s, st, run, ticket, at):
    # The arrival ticket, not the number already served, seeds this customer.
    # Keep the active person's tray and payment stable as other people arrive.
    draft = dict(run, current=None)
    row = customer(s, st, draft, ticket)
    present = {p['name'] for p in [run['current']] + run.get('crowd', {}).get('waiting', [])}
    if row['name'] in present:
        row['name'] = _rng(s, st, run['d'], 'queue-name', run['nonce'], ticket).choice([name for name in NAMES if name not in present])
        row['say'] = _say(row['name'], row['items'], DISH[st['trade']])
    return _queue_traits(s, st, run, row, ticket, at)


def settle_queue(s, st, at):
    """Advance only the bounded owner queue; arrivals never spend or earn xu.

    Called before each NPC stock mutation and at the final business cursor.
    Once full, skip elapsed arrival slots arithmetically, even after years away.
    The person currently being served is never replaced by a poll or migration.
    """
    run = st.get('run')
    if not isinstance(run, dict) or not run.get('continuous') or run['x']:
        return False
    if st['business']['paused']:
        return False
    changed = False
    if 'crowd' not in run:
        _queue_traits(s, st, run, run['current'], 0, run['next_at'])
        run['crowd'] = dict(v=1, next_at=run['next_at'] + _queue_wait(st), seq=1, waiting=[])
        changed = True
    crowd = run['crowd']
    interval = _queue_wait(st)
    stock = st['business']['stock']
    stocked = any(stock.get(d, 0) for d in menu(st)['on'])
    while crowd['next_at'] <= at and stocked and len(crowd['waiting']) < OWNER_QUEUE_MAX - 1:
        crowd['waiting'].append(_queue_customer(s, st, run, crowd['seq'], crowd['next_at']))
        crowd['seq'] += 1
        crowd['next_at'] += interval
        changed = True
    if crowd['next_at'] <= at:
        skipped = (at - crowd['next_at']) // interval + 1
        crowd['seq'] += skipped
        crowd['next_at'] += skipped * interval
        changed = True
    return changed


def _next_customer(s, st, run):
    crowd, stock = run['crowd'], st['business']['stock']
    # Waiting people whose dish just sold out have not paid or reserved goods.
    # Move to a serviceable request before it becomes the active tray.
    crowd['waiting'] = [row for row in crowd['waiting']
                        if all(stock.get(d, 0) >= row['items'].count(d) for d in set(row['items']))]
    if crowd['waiting']:
        row = crowd['waiting'].pop(0)
    else:
        row = _queue_customer(s, st, run, crowd['seq'], crowd['next_at'])
        crowd['seq'] += 1
        crowd['next_at'] += _queue_wait(st)
    run['current'] = dict(row, index=run['i'])
    run['next_at'] = row['arrival_at']


def _customer_mood(row, at):
    waited = max(0, at - row['arrival_at'])
    fussy = row['temperament'] == 'fussy'
    mood = 'angry' if fussy and waited >= row['patience'] * 2 else 'impatient' if fussy and waited >= row['patience'] else 'calm'
    speech = ('Món của tôi đâu rồi? Tôi chờ lâu lắm rồi đấy!' if mood == 'angry' else
              'Nhanh giúp tôi nhé, tôi đang vội!' if mood == 'impatient' else
              'Bạn cứ làm lần lượt nhé, tôi đợi được.' if not fussy else 'Làm nhanh giúp tôi nhé.')
    return dict(ticket=row['ticket'], name=row['name'], look=row['look'], temperament=row['temperament'],
                mood=mood, speech=speech, arrival_at=row['arrival_at'] / 1000)


def _need_stock(st, items):
    stock = st['business']['stock']
    _need(all(stock.get(d, 0) >= items.count(d) for d in set(items)), 'Món trong đơn đã hết. Nhập thêm hàng để phục vụ.', 'sold_out')


def _next_order(s, st, run, jn, at):
    from .work_gear import factor
    run['order_seq'] += 1
    run['order_data'].pop(str(jn), None)
    o = order(s, st, run, jn)
    o.update(id=f"{run['nonce']}:{run['order_seq']}", available_at=at, at=1,
             drive_factor=factor(s.get('careers', {}).get('delivery', {})))
    run['order_data'][str(jn)] = o


def _check_order(st, run, o, p):
    if run.get('continuous'):
        _need(not st['business']['paused'] or o['available_at'] <= st['business'].get('closed_at', 0), 'Quầy đã đóng, chưa nhận đơn mới.', 'closed')
        _need(st['business']['cursor'] >= o['available_at'], 'Đơn này chưa tới.', 'waiting')
        _need(p.get('order_id', o['id']) == o['id'], 'Đơn này đã thay đổi. Xem đơn mới nhé.', 'stale_order')


def player_hands(st: dict) -> float:
    P, T = qy.PLACES[st['place']], qy.TRADES[st['trade']]
    return P['cap'] * T['mult'] / 100 * SELF_HANDS / 100


def close(s: dict, st: dict, day: int) -> str:
    """Settle the run as the counter's whole life day `day` (also called when the life day ends with it open)."""
    run = st['run']
    if run.get('continuous'):
        run['x'] = True
        st['day'] = max(st['day'], day)
        run['sum'] = dict(n=run['u'], hand=run['i'], on=run['sn']-run['i'], auto=0, rev=run['rv'], net=run['rv']-run['co']+run['m'], st=round(run['ss']*10/max(1,run['sn'])))
        st['left'] = 0
        return f'🏁 Đã kết thúc ca: tự phục vụ {run["u"]} món. Nhân viên tiếp tục bán nếu đủ hàng và vốn.'
    P, T = qy.PLACES[st['place']], qy.TRADES[st['trade']]
    fc = qy.forecast(s, st, day)
    demand = fc['n'] * qy._rng(s, st, day, 'd').uniform(0.8, 1.2)
    rated = run['sn'] + sum(1 for x in run['on'] if x)
    stars = (run['ss'] + sum(run['on'])) / rated if rated else 3.0
    qf = 1 + (QUALITY_MAX * (stars - 3) / 2 if stars >= 3 else 15 * (stars - 3) / 2) / 100
    hands = player_hands(st) + qy._hands(st)
    rest = max(0.0, demand + run['b'] - run['u'])
    auto = 0  # legacy runs book only orders the owner actually fulfilled
    pct = board_pct(st)
    unit = T['price'] * goods_pct(st) / 100 * T['cogs'] / 100
    spoil = T['spoil'] * (0.5 if 'tu' in st['items'] else 1) / 100
    spoiled = max(0, run['sk'] - run['u'] - auto) * spoil
    gain = max(0, run['m'])
    revenue = run['rv'] + round(auto * T['price'] * pct / 100) + gain
    wages = sum(x['wage'] for x in st['staff'])
    cost = run['co'] + round((auto + spoiled) * unit) + wages + P['power'] + max(0, -run['m'])
    st['till'] = min(qy.MONEY_MAX, st['till'] + revenue)
    qy._from_till_fund(st, cost)   # a shortfall past both is waived: never a debt
    net = revenue - cost
    for x in st['staff']:
        t = qy._target_mood(x)
        x['mo'] = min(t, x['mo'] + 10) if x['mo'] < t else max(t, x['mo'] - 10)
        x['d'] = min(10**6, x['d'] + 1)
    rep = st['rep'] + (-2 if demand + run['b'] > run['sk'] + 0.5 else 1) + run['r'] + (1 if stars >= 4.5 else -1 if stars < 2.5 else 0)
    rep += {'cheap': 1, 'dear': -1, 'fair': 0}[react(st)]
    st['rep'] = max(90, min(110, rep))
    sold = run['u'] + auto
    st['hist'] = qy.ar.last(st['hist'] + [dict(d=day, n=sold, rev=revenue, net=net, w=fc['w'], p=fc['pace'], s=1)], qy.HIST_MAX,
                            'quay.hist', qy.ar.JOURNEY)
    run['x'] = True
    run['sum'] = dict(n=sold, hand=run['i'], on=sum(1 for x in run['on'] if x), auto=auto, rev=revenue, net=net, st=round(stars * 10))
    qy._log(st, day, 'Tự đứng quầy', net)
    qy._theft(s, st, day)
    st['day'] = max(st['day'], day)   # this life day has run: its end skips it (this build and the previous one)
    st['left'] = 0
    qy._rent(s, st, day)
    qy._police(s, st, day)
    net = st['hist'][-1]['net']
    sign = '+' if net >= 0 else '−'
    return f'🏁 Đóng ca: {sold} khách, lời {sign}{qy._fmt(abs(net))} xu. Két giữ {qy._fmt(st["till"])} xu.'


# ---------------------------------------------------------------- views
def catalogue() -> dict:
    return dict(menus={t: [dict(id=d[0], emoji=d[1], name=d[2], base=d[3], cost=max(1, __import__('math').ceil(cost_of(t, d[0]))), band=list(band(d[3]))) for d in rows] for t, rows in MENUS.items()},
                tools={t: list(v) for t, v in TOOL.items()}, colors=[list(c) for c in COLORS], decor=[list(d) for d in DECOR],
                tables={k: list(v) for k, v in TABLES.items()}, menu_max=MENU_MAX, decor_max=DECOR_MAX, coins=list(COINS),
                online=dict(fee=ONLINE_FEE, ship=SHIPPER_FEE, reach=ONLINE_REACH), turns=list(TURNS))


def run_view(s: dict, st: dict) -> dict | None:
    run = st.get('run')
    day = int(s['journey']['life_day'])
    if not isinstance(run, dict) or (not run.get('continuous') and run['d'] != day):
        return None
    out = dict(i=run['i'], k=run['k'], u=run['u'], sk=run['sk'], rv=run['rv'], x=run['x'], sum=run['sum'],
               stars=round(10 * (run['ss'] + sum(run['on'])) / max(1, run['sn'] + sum(1 for x in run['on'] if x))) if run['sn'] or any(run['on']) else 0)
    if run['x']:
        return out
    if run.get('continuous'):
        out['next_at'] = run['next_at'] / 1000
        out['drive_factor'] = run.get('drive_factor', 1)
        out['sk'] = run['u'] + sum(st['business']['stock'].values())
        if 'crowd' in run:
            at = st['business']['cursor']
            arrived_by = min(at, st['business'].get('closed_at', 0)) if st['business']['paused'] else at
            out['crowd'] = [_customer_mood(row, at) for row in [run['current']] + run['crowd']['waiting']
                            if row['arrival_at'] <= arrived_by]
            out['voices'] = [row for row in out['crowd'] if row['mood'] != 'calm'][:2]
            relaxed = next((row for row in out['crowd'] if row['temperament'] == 'relaxed'), None)
            if relaxed:
                out['voices'].append(relaxed)
    n = pending_event(run)
    if n is not None:
        from .quay_events import BY_ID
        e = BY_ID[run['ev'][n]]
        out['ev'] = dict(id=e['id'], emoji=e['emoji'], title=e['title'], text=e['text'], picks=[[k, label] for k, label, _ in e['picks']])
    elif run['i'] < run['k'] and (not run.get('continuous') and run['u'] < run['sk'] or run.get('continuous') and (not st['business']['paused'] or run['next_at'] <= st['business'].get('closed_at', 0)) and st['business']['cursor'] >= run['next_at'] and any(st['business']['stock'].get(d, 0) for d in menu(st)['on'])):
        out['cust'] = {k: v for k, v in customer(s, st, run, run['i']).items()}
        out['queue'] = [customer(s, st, run, i)['look'] for i in range(run['i'] + 1, min(run['k'], run['i'] + 4))]
        if 'crowd' in out:
            out['queue'] = [row['look'] for row in out['crowd'][1:]]
            out['cust'].update(_customer_mood(run['current'], st['business']['cursor']))
    out['out'] = not any(st['business']['stock'].get(d, 0) for d in menu(st)['on']) if run.get('continuous') else run['u'] >= run['sk']
    out['done'] = [x[:2] for x in run['eo']]
    out['orders'] = []
    for jn, st_ in enumerate(run['on']):
        o = order(s, st, run, jn)
        if run.get('continuous') and st['business']['paused'] and o.get('available_at', 0) > st['business'].get('closed_at', 0):
            continue
        if (st['business']['cursor'] >= o.get('available_at', 0) if run.get('continuous') else run['i'] >= o['at'] - 1 or run['i'] >= run['k'] or st_):
            out['orders'].append(dict(j=jn, id=o.get('id'), available_at=o.get('available_at', 0)/1000, drive_factor=o.get('drive_factor',1), name=o['name'], items=o['items'], total=o['total'], note=o['note'], cod=o['cod'], addr=o['addr'],
                                      route=o['route'], stars=st_, ride=copy.deepcopy(run.get('rides',{}).get(str(jn)))))
            if out['orders'][-1]['ride']:
                from . import traffic
                ride=out['orders'][-1]['ride'];ride['traffic']=traffic.public(ride['traffic'])
    return out


def stall_view(s: dict, st: dict) -> dict:
    b = menu(st)
    out = dict(menu=b, look=look(st), online=bool(st.get('online')), rate=list(rating(st)), react=react(st), pct=round(board_pct(st, b)))
    rv = run_view(s, st)
    if rv:
        out['run'] = rv
    return out


# ---------------------------------------------------------------- validation (journey.validate through game/quay.py)
def validate(st: dict, need, _int, _text) -> None:
    rows = DISH.get(st['trade'], {})
    if 'menu' in st and st['menu'] is not None:
        m = st['menu']
        need(isinstance(m, dict) and isinstance(m.get('on'), list) and 1 <= len(m['on']) <= MENU_MAX and all(isinstance(d, str) for d in m['on']) and len(set(m['on'])) == len(m['on'])
             and set(m['on']) <= set(rows) and isinstance(m.get('p', {}), dict))
        for d, v in m.get('p', {}).items():
            need(d in rows and _int(v, *band(rows[d]['base'])))
    if 'look' in st and st['look'] is not None:
        lk = st['look']
        need(isinstance(lk, dict) and _int(lk.get('c', 0), 0, len(COLORS) - 1) and isinstance(lk.get('d', []), list)
             and len(lk.get('d', [])) <= DECOR_MAX and set(lk.get('d', [])) <= set(DECOR_IDS) and _int(lk.get('t', 0), 0, TABLES[st['place']][0]))
    if 'online' in st:
        need(type(st['online']) is bool)
    if 'rate' in st and st['rate'] is not None:
        r = st['rate']
        need(isinstance(r, list) and len(r) == 2 and _int(r[0], 0, RATE_MAX) and (_int(r[1], 10, 50) or (r[0] == 0 and r[1] == 0)))
    run = st.get('run')
    if run is not None:
        need(isinstance(run, dict) and RUN_KEYS <= set(run))
        for k in ('d', 'i', 'k', 'n', 'sk', 'u', 'sn', 'ss'):
            need(_int(run[k], 0, 10**6))
        for k in ('rv', 'co', 'm', 'b', 'r'):
            need(_int(run[k], -qy.MONEY_MAX, qy.MONEY_MAX))
        need(isinstance(run['ev'], list) and len(run['ev']) <= 2 and isinstance(run['eo'], list) and len(run['eo']) <= 2)
        need(isinstance(run['on'], list) and len(run['on']) <= 3 and all(_int(x, 0, 5) for x in run['on']) and type(run['x']) is bool)
        need(run['sum'] is None or isinstance(run['sum'], dict))
        if 'continuous' in run:
            need(run['continuous'] is True and isinstance(st.get('business'), dict))
            need(all(_int(run.get(k), 0, 10**18) for k in ('nonce', 'next_at', 'order_seq')))
            need(type(run.get('drive_factor', 1)) in (int, float) and run.get('drive_factor', 1) in (1, 1.15, 1.35, 1.6))
            need(isinstance(run.get('order_data'), dict) and set(run['order_data']) == {str(i) for i in range(len(run['on']))})
            cur = run.get('current')
            need(isinstance(cur, dict) and _int(cur.get('index'), 0, 10**6))
            records = [cur] + list(run['order_data'].values())
            if 'crowd' in run:
                crowd = run['crowd']
                need(isinstance(crowd, dict) and set(crowd) == {'v', 'next_at', 'seq', 'waiting'} and type(crowd['v']) is int and crowd['v'] == 1)
                need(_int(crowd['next_at'], 0, 10**18) and _int(crowd['seq'], 1, 10**18))
                need(isinstance(crowd['waiting'], list) and len(crowd['waiting']) < OWNER_QUEUE_MAX)
                people = [cur] + crowd['waiting']
                for row in people:
                    need(isinstance(row, dict) and _int(row.get('ticket'), 0, crowd['seq'] - 1))
                    need(_int(row.get('arrival_at'), 0, crowd['next_at']) and row.get('temperament') in ('fussy', 'relaxed'))
                    need(_int(row.get('patience'), 18000, 30000) and _int(row.get('look'), 0, 10**6) and _text(row.get('say'), 1000))
                    need(_int(row.get('total'), 1, 6000000))
                    need(_int(row.get('pay'), row['total'], 6000000))
                need(len({row['ticket'] for row in people}) == len(people))
                need([row['arrival_at'] for row in people] == sorted(row['arrival_at'] for row in people))
                records += crowd['waiting']
            for record in records:
                need(isinstance(record, dict) and isinstance(record.get('items'), list) and 1 <= len(record['items']) <= 6)
                need(all(isinstance(d, str) and d in rows for d in record['items']))
                need(_int(record.get('total'), 1, 6000000) and _text(record.get('name'), 40))
                if not run['x']:
                    need(record['total'] == sum(price(st, d) for d in record['items']))
            need(_int(cur.get('pay'), cur['total'], 6000000))
            for key, record in run['order_data'].items():
                need(_text(record.get('id'), 80) and _int(record.get('available_at'), 0, 10**18))
                need(type(record.get('drive_factor', 1)) in (int, float) and record.get('drive_factor', 1) in (1, 1.15, 1.35, 1.6))
                need(record.get('j') == int(key) and _int(record.get('at'), 0, 10**6))
                need(isinstance(record.get('route'), list) and len(record['route']) == 3 and all(x in TURNS for x in record['route']))
                need(_text(record.get('addr'), 100) and _text(record.get('note'), 100))
                need(all(type(record.get(k)) is bool for k in ('cod', 'tool', 'sticker')))
        if 'rides' in run:
            from . import traffic
            need(isinstance(run['rides'],dict) and len(run['rides'])<=len(run['on']))
            for key,ride in run['rides'].items():
                need(key in {str(i) for i in range(len(run['on']))} and isinstance(ride,dict) and set(ride)=={'picks','traffic'})
                need(isinstance(ride['picks'],list) and len(ride['picks'])<=3 and all(isinstance(x,str) and x in TURNS for x in ride['picks']))
                traffic.validate(ride['traffic'])
                need(len(ride['picks'])==len(ride['traffic']['receipts']))
