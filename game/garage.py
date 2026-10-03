"""🚗 Xe & phương tiện: bicycles, motorbikes, cars, yachts and private planes, bought outright with xu (story mode).

Owner (02/10): "thêm cả cái xe, máy bay, du thuyền cho mọi người mua nhé".

* One catalogue (VEHICLES), four groups shown as the shop's tabs: Cửa hàng xe (two wheels), Showroom Phố (cars),
  Bến du thuyền (boats) and Sân bay tư nhân (planes). A bicycle is a few days of pay; the cars sit around the
  apartments' prices; the boats and the planes are long-term goals next to the villas (game/housing.py HOMES).
* Paid in full, never a loan, never the credit card: the cash in the wallet first, then the bank account
  (like a home's down payment). A wallet in debt buys nothing until the debt is repaid, so the wallet never goes
  below 0 here. One of each model at most.
* Cosmetic: a paint colour (PAINTS, free to change) and a short plate or boat name the owner writes ("biển tên",
  shown only to the owner).
* "Đang đi": the vehicle shown on the profile, by the house and on the player's card in Phố nghề (social.snapshot).
* One perk, honest and capped: a ride out (đi dạo một vòng, ra khơi, bay ngắm phố), once per life day across every
  vehicle, adds a little tinh thần (TRIP spirit, journey.life.spirit). Fuel is a few xu, shown on the button and paid
  from the wallet only when the player taps it.
* 🧾 Phí giữ xe & bảo dưỡng (owner 03/10, the xu sinks): every vehicle but a bicycle costs a small share of its price
  a tháng (game/upkeep.py CAR_BP: xe máy 0,5 %, ô tô 0,75 %, du thuyền 1 %, máy bay 1,25 %), billed with the month's
  other bills, shown on the listing, the buy page and each vehicle you own (`upkeep`, xu a tháng). Until 03/10 there
  was none ("no upkeep, no parking fee"); nothing is billed for the days before (upkeep.since).
* 03/10: three dearer models for the street's richest (Siêu xe Tia Chớp, Trực thăng riêng, Siêu du thuyền Ngọc Trai).
* Selling back: SELL_PCT % of the price paid (rounded down to 10 xu), into the wallet, after a confirm.

State `s['journey']['garage']` (absent until the first purchase; older builds never read it: journey.validate allows
extra keys), see initial():
    v      VERSION
    cars   {vehicle id: {c: paint id, n: plate text ('' = none), d: life day bought, p: price paid}}
    ride   the vehicle id shown as "đang đi", or None
    trip   the life day of the last ride out (0: never)
    stats  {bought, sold, trips}
Ids are stored in saves: never rename or remove one. A vehicle or paint id this build does not know (a newer build
wrote it) is kept untouched and simply not shown, so a rollback never loses anything.
Commands (through journey.action, so journey.after and validate_state run): jr_garage_buy {id, color, plate?, confirm},
jr_garage_paint {id, color?, plate?}, jr_garage_ride {id | None}, jr_garage_trip {id}, jr_garage_sell {id, confirm}.
Deterministic: the only draw (the ride's line) is seeded by the journey seed, the life day and the vehicle.
"""
from __future__ import annotations

import hashlib
import re

from . import bank as bk
from . import upkeep as up   # 🧾 phí giữ xe & bảo dưỡng a tháng

VERSION = 1
KIND = 'life'                     # journey wallet history kind (an existing one: older builds validate the row)
LABEL = 'Mua xe'                  # wallet row: "Mua xe · Xe số Cub"
SELL_PCT = 70                     # selling back: 70 % of the price paid
PLATE_MAX = 10
STATS = ('bought', 'sold', 'trips')
BLOCK_KEYS = frozenset({'v', 'cars', 'ride', 'trip', 'stats'})
CAR_KEYS = frozenset({'c', 'n', 'd', 'p'})
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
COMMANDS = ('jr_garage_buy', 'jr_garage_paint', 'jr_garage_ride', 'jr_garage_trip', 'jr_garage_sell')

# The shop's tabs: (id, emoji, name, where the player buys, tile colour in the UI).
GROUPS = (('bike', '🛵', 'Xe hai bánh', 'Cửa hàng xe Đầu Hẻm', '#e0a93b'),
          ('car', '🚗', 'Ô tô', 'Showroom Phố', '#4f9fd1'),
          ('boat', '🛥️', 'Du thuyền', 'Bến du thuyền', '#3f9a9a'),
          ('plane', '✈️', 'Máy bay riêng', 'Sân bay tư nhân', '#8d76bb'))
GROUP_IDS = tuple(g[0] for g in GROUPS)

# Paint colours (the art: `hex`, drawn as the vehicle's tile in public/js/v4/garage.js).
PAINTS = (
    ('do', 'Đỏ son', '#d9534f'), ('cam', 'Cam đào', '#f0955a'), ('vang', 'Vàng chanh', '#e8c547'),
    ('xanh_la', 'Xanh bạc hà', '#5cbf9a'), ('xanh', 'Xanh biển', '#4f8fd1'), ('navy', 'Xanh navy', '#2f4a7a'),
    ('tim', 'Tím lavender', '#9d86c9'), ('hong', 'Hồng phấn', '#ef9bb8'), ('trang', 'Trắng ngọc', '#f3f0e8'),
    ('bac', 'Bạc ánh kim', '#b8bec6'), ('den', 'Đen bóng', '#2b2b30'),
)
PAINT_INDEX = {p[0]: dict(id=p[0], name=p[1], hex=p[2]) for p in PAINTS}


def _v(vid, group, emoji, name, price, desc, spirit, fuel, trip, paint='do'):
    """spirit: tinh thần from one ride out; fuel: its xu (0: free); trip: the button's words; paint: the default."""
    return vid, dict(id=vid, group=group, emoji=emoji, name=name, price=price, desc=desc, spirit=spirit, fuel=fuel,
                     trip=trip, paint=paint)


# Cheapest first within each group. Prices against a day's pay (employment 50–90 xu, minus 10–20 living):
# a bicycle is ~2 days, a motorbike ~2 weeks, a small car ~ a small apartment, a jet ~ 1.5 riverside villas.
VEHICLES = dict((
    _v('xe_dap', 'bike', '🚲', 'Xe đạp phố', 120, 'Khung thép, giỏ mây đằng trước, chuông kêu leng keng. Chở được một bó hoa.',
       2, 0, 'Đạp một vòng', 'xanh_la'),
    _v('xe_dap_dien', 'bike', '🚲', 'Xe đạp điện', 300, 'Sạc một đêm chạy cả ngày, lên dốc cầu nhẹ tênh.',
       2, 0, 'Chạy một vòng', 'trang'),
    _v('xe_so', 'bike', '🏍️', 'Xe số Cub', 600, 'Bền như trâu, đổ xăng một lần chạy cả tuần. Ai trong hẻm cũng biết sửa.',
       3, 2, 'Chạy một vòng phố', 'do'),
    _v('xe_ga', 'bike', '🛵', 'Xe tay ga cổ điển', 1000, 'Dáng tròn, yên da nâu, cốp rộng để vừa áo mưa và hộp cơm.',
       3, 2, 'Chạy một vòng phố', 'xanh'),
    _v('o_to_mini', 'car', '🚗', 'Ô tô mini 4 chỗ', 3000, 'Nhỏ gọn, len hẻm xe hơi dễ dàng, máy lạnh mát rượi ngày nắng.',
       4, 5, 'Lái xe hóng gió', 'hong'),
    _v('o_to_suv', 'car', '🚙', 'SUV 7 chỗ', 6600, 'Gầm cao, cốp rộng, đủ chỗ chở cả nhà về quê dịp lễ.',
       4, 6, 'Chở cả nhà đi chơi', 'bac'),
    _v('mui_tran', 'car', '🏎️', 'Xe mui trần cổ', 12000, 'Sơn bóng loáng, vô lăng gỗ, mở mui ra là cả phố ngoái nhìn.',
       5, 8, 'Mở mui dạo phố', 'do'),
    _v('sieu_xe', 'car', '🚘', 'Siêu xe Tia Chớp', 30000, 'Động cơ đặt giữa, cửa mở cánh chim. Đỗ trước chợ là cả hẻm kéo ra chụp hình.',
       6, 20, 'Chạy một vòng cao tốc', 'vang'),
    _v('thuyen_buom', 'boat', '⛵', 'Thuyền buồm nhỏ', 15000, 'Hai cánh buồm trắng, cabin nhỏ đủ pha ấm trà. Đậu ở bến cuối đê.',
       5, 6, 'Giương buồm ra sông', 'trang'),
    _v('du_thuyen', 'boat', '🛥️', 'Du thuyền Hoàng Hôn', 45000, 'Boong gỗ rộng, phòng ngủ dưới khoang, sân thượng ngắm hoàng hôn trên vịnh.',
       6, 15, 'Ra khơi ngắm hoàng hôn', 'navy'),
    _v('sieu_du_thuyen', 'boat', '🛳️', 'Siêu du thuyền Ngọc Trai', 150000, 'Ba tầng boong, bể bơi trên mũi, bếp riêng có đầu bếp. Neo ngoài vịnh là cả bến ngoái nhìn.',
       7, 30, 'Mở tiệc trên boong', 'trang'),
    _v('may_bay_nho', 'plane', '🛩️', 'Máy bay cánh quạt', 30000, 'Hai chỗ ngồi, cánh cao, cất cánh từ đường băng cỏ ngoài sân bay tư nhân.',
       6, 15, 'Bay ngắm phố', 'vang'),
    _v('truc_thang', 'plane', '🚁', 'Trực thăng riêng', 60000, 'Bốn ghế, đáp được trên sân thượng. Sáng uống cà phê ở phố, trưa đã ngắm biển.',
       6, 20, 'Bay một vòng ngắm sông', 'navy'),
    _v('phan_luc', 'plane', '✈️', 'Phản lực riêng', 90000, 'Tám ghế da, bay êm như ngồi phòng khách. Cuối tuần ra đảo ăn hải sản rồi về.',
       7, 30, 'Bay ra đảo cuối tuần', 'trang'),
))
ORDER = tuple(VEHICLES)

# A line for each ride out (no real names: the street's own people).
TRIP_LINES = {
    'bike': ('Gió bờ kênh mát rượi, bạn ghé mua ly nước mía rồi thong thả về.',
             'Một vòng quanh chợ, cô bán hoa dúi cho cành cúc họa mi bỏ giỏ xe.',
             'Đường chiều vắng, đèn phố vừa lên. Đầu óc nhẹ tênh.'),
    'car': ('Mở cửa kính, bật bài hát quen, chạy dọc đường ven sông tới lúc trời tắt nắng.',
            'Bà Tám đi nhờ ra chợ đầu mối, khen xe êm quá trời.',
            'Ghé quán bánh xèo ngoại ô, ăn xong lái về thong thả.'),
    'boat': ('Neo ngoài vịnh, mặt trời lặn đỏ rực sau rặng núi. Gió mặn mà dễ chịu.',
             'Bầy cá chuồn nhảy quanh mũi thuyền. Bạn thả câu, chẳng cần cá cắn.',
             'Ngồi trên boong pha ấm trà, nghe sóng vỗ lách tách.'),
    'plane': ('Từ trên cao, cả khu phố nhỏ như mô hình: thấy cả mái nhà Bà Tám.',
              'Bay qua dòng sông lúc hoàng hôn, mây hồng trải dài tới chân trời.',
              'Hạ cánh xuống đảo, ăn đĩa ghẹ hấp rồi bay về kịp giờ cơm tối.'),
}


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _fmt(n: int) -> str:
    return bk._fmt(n)


def lname(name: str) -> str:
    """A name inside a sentence: "Xe đạp phố" -> "xe đạp phố"."""
    return name[:1].lower() + name[1:]


def initial() -> dict:
    return dict(v=VERSION, cars={}, ride=None, trip=0, stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    g = j.get('garage') if isinstance(j, dict) else None
    return g if isinstance(g, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('garage'), dict):
        j['garage'] = initial()
    return j['garage']


def _have(s: dict) -> dict:
    """The money a purchase may use: the cash in the wallet (none while it is in debt) and the bank account."""
    j = s['journey']
    b = bk.get(s)
    wallet = max(0, j['wallet'])
    balance = b['balance'] if b else 0
    return dict(wallet=wallet, balance=balance, ready=wallet + balance, bank=b is not None, debt=max(0, -j['wallet']))


def _take(s: dict, amount: int, label: str) -> str:
    """Take `amount` from the wallet first, then the bank account. The caller checked it is there.
    The sentence saying where it came from."""
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _jr()._wallet(j, -cash, KIND, label)
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label, -rest)
    if rest and cash:
        return f'{_fmt(cash)} xu tiền mặt và {_fmt(rest)} xu từ tài khoản'
    return f'{_fmt(amount)} xu từ tài khoản' if rest else f'{_fmt(amount)} xu tiền mặt'


def sell_price(paid: int) -> int:
    return max(0, int(paid) * SELL_PCT // 100 // 10 * 10)


def _spirit(s: dict, n: int) -> int:
    L = s['journey'].get('life')
    if not isinstance(L, dict) or type(L.get('spirit')) is not int:
        return 0
    before = L['spirit']
    L['spirit'] = max(0, min(100, before + n))
    return L['spirit'] - before


def _line(s: dict, vid: str) -> str:
    j = s['journey']
    lines = TRIP_LINES[VEHICLES[vid]['group']]
    h = hashlib.sha1(f'{j.get("seed", 0)}|{j["life_day"]}|{vid}'.encode()).digest()
    return lines[h[0] % len(lines)]


def _plate(p: dict, default: str = '') -> str:
    raw = p.get('plate', default)
    if raw is None or raw == '':
        return ''
    return _core().clean_text(raw, PLATE_MAX, 0)


def why_not_buy(s: dict, vid: str) -> str | None:
    """Why `vid` cannot be bought now (None: it can). Shown on the disabled button."""
    j = s['journey']
    if not j.get('story'):
        return 'Mua xe chỉ có trong chế độ hành trình.'
    V = VEHICLES[vid]
    g = get(s)
    if g and vid in g['cars']:
        return f'Bạn đã có {lname(V["name"])} rồi.'
    if j['wallet'] < 0:
        return f'Ví đang nợ {_fmt(-j["wallet"])} xu. Trả nợ xong rồi hãy mua xe nhé.'
    short = V['price'] - _have(s)['ready']
    if short > 0:
        return f'Còn thiếu {_fmt(short)} xu.'
    return None


def why_not_trip(s: dict, vid: str) -> str | None:
    j = s['journey']
    g = get(s)
    if not g or vid not in g['cars'] or vid not in VEHICLES:
        return 'Bạn chưa có chiếc này.'
    if g['trip'] == j['life_day']:
        return 'Hôm nay bạn đã đi chơi một chuyến rồi. Mai đi tiếp nhé.'
    fuel = VEHICLES[vid]['fuel']
    if fuel and j['wallet'] < fuel:
        return f'Ví cần {_fmt(fuel)} xu tiền xăng.'
    return None


# ---------------------------------------------------------------- save
def _plate_ok(n) -> bool:
    return isinstance(n, str) and len(n) <= PLATE_MAX and n == n.strip() and not _core()._CONTROL.search(n)


def _car_ok(vid, car) -> bool:
    return (isinstance(vid, str) and ID_RE.fullmatch(vid) is not None and isinstance(car, dict) and set(car) == CAR_KEYS
            and isinstance(car['c'], str) and ID_RE.fullmatch(car['c']) is not None and _plate_ok(car['n'])
            and type(car['d']) is int and 1 <= car['d'] <= 10**6 and type(car['p']) is int and 1 <= car['p'] <= 10**7)


def validate(s: dict) -> None:
    """``s['journey']['garage']`` (absent in older saves). Unknown ids written by a newer build are allowed by shape.
    Raises GameError like validate_state."""
    e = _core()
    g = get(s)
    j = s.get('journey')
    if g is None:
        e.need(not isinstance(j, dict) or j.get('garage') is None, 'Nhà xe trong bản lưu không hợp lệ.', 'invalid_save')
        return
    bad = 'Nhà xe trong bản lưu không hợp lệ.'
    e.need(set(g) == BLOCK_KEYS and g['v'] == VERSION, bad, 'invalid_save')
    cars = g['cars']
    e.need(isinstance(cars, dict) and len(cars) <= 64 and all(_car_ok(k, v) for k, v in cars.items()), bad, 'invalid_save')
    e.need(g['ride'] is None or g['ride'] in cars, bad, 'invalid_save')
    e.need(type(g['trip']) is int and 0 <= g['trip'] <= 10**6, bad, 'invalid_save')
    st = g['stats']
    e.need(isinstance(st, dict) and set(st) <= set(STATS) and all(type(v) is int and 0 <= v <= 10**9 for v in st.values()),
           bad, 'invalid_save')


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep every vehicle it holds whose
    record still makes sense. Absent stays absent."""
    g = j.get('garage') if isinstance(j, dict) else None
    if g is None or 'garage' not in j:
        return
    if not isinstance(g, dict):
        j['garage'] = initial()
        return
    out = initial()
    cars = g.get('cars') if isinstance(g.get('cars'), dict) else {}
    out['cars'] = {k: v for k, v in cars.items() if _car_ok(k, v)}
    out['ride'] = g.get('ride') if g.get('ride') in out['cars'] else None
    out['trip'] = g['trip'] if type(g.get('trip')) is int and 0 <= g['trip'] <= 10**6 else 0
    st = g.get('stats') if isinstance(g.get('stats'), dict) else {}
    out['stats'] = {k: st[k] if type(st.get(k)) is int and 0 <= st[k] <= 10**9 else 0 for k in STATS}
    if out != g:
        j['garage'] = out


# ---------------------------------------------------------------- commands
def _vid(p: dict, key: str = 'id') -> str:
    vid = p.get(key)
    _core().need(isinstance(vid, str) and vid in VEHICLES, 'Chọn một chiếc xe nhé.')
    return vid


def _paint(p: dict, default: str) -> str:
    c = p.get('color', default)
    _core().need(isinstance(c, str) and c in PAINT_INDEX, 'Màu sơn này không có trong bảng màu.')
    return c


def _mine(s: dict, vid: str) -> dict:
    g = get(s)
    _core().need(g is not None and vid in g['cars'], f'Bạn chưa có {lname(VEHICLES[vid]["name"])}.', 'not_owned')
    return g


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Mua xe chỉ có trong chế độ hành trình.')
    day = j['life_day']
    if name == 'jr_garage_buy':
        need(set(p) <= {'id', 'color', 'plate', 'confirm'}, 'Thông tin mua xe không hợp lệ.')
        vid = _vid(p)
        V = VEHICLES[vid]
        color = _paint(p, V['paint'])
        plate = _plate(p)
        g = get(s)
        if g and vid in g['cars']:   # a second tap: nothing to pay
            return dict(message=f'Bạn đã có {lname(V["name"])} rồi.', duplicate=True)
        need(p.get('confirm') is True, f'Xác nhận mua {lname(V["name"])}.')
        why = why_not_buy(s, vid)
        need(why is None, why or '', 'not_enough')
        how = _take(s, V['price'], f'{LABEL} · {V["name"]}')
        g = _ensure(s)
        g['cars'][vid] = dict(c=color, n=plate, d=day, p=V['price'])
        g['stats']['bought'] = g['stats'].get('bought', 0) + 1
        ride = g['ride'] is None
        if ride:
            g['ride'] = vid
        tail = ' Đang đi chiếc này.' if ride else ' Đã cất vào nhà xe.'
        return dict(message=f'Đã trả {how} cho {lname(V["name"])} màu {PAINT_INDEX[color]["name"].lower()}.{tail}')
    if name == 'jr_garage_paint':
        need(set(p) <= {'id', 'color', 'plate'} and ('color' in p or 'plate' in p), 'Thông tin sơn xe không hợp lệ.')
        vid = _vid(p)
        g = _mine(s, vid)
        car = g['cars'][vid]
        color = _paint(p, car['c'] if car['c'] in PAINT_INDEX else VEHICLES[vid]['paint'])
        plate = _plate(p, car['n'])
        if color == car['c'] and plate == car['n']:
            return dict(message='Chiếc xe vẫn y như cũ.', duplicate=True)
        car['c'], car['n'] = color, plate
        nm = lname(VEHICLES[vid]['name'])
        return dict(message=f'{VEHICLES[vid]["emoji"]} {nm[:1].upper() + nm[1:]} giờ màu {PAINT_INDEX[color]["name"].lower()}'
                            + (f', biển tên “{plate}”.' if plate else '.'))
    if name == 'jr_garage_ride':
        need(set(p) <= {'id'}, 'Thông tin không hợp lệ.')
        g = get(s)
        if p.get('id') is None:
            if g:
                g['ride'] = None
            return dict(message='Không khoe xe nào trên hồ sơ nữa.')
        vid = _vid(p)
        g = _mine(s, vid)
        g['ride'] = vid
        return dict(message=f'Giờ bạn đi {lname(VEHICLES[vid]["name"])}.')
    if name == 'jr_garage_trip':
        need(set(p) <= {'id'}, 'Thông tin không hợp lệ.')
        vid = _vid(p)
        g = _mine(s, vid)
        why = why_not_trip(s, vid)
        need(why is None, why or '', 'already_done' if g['trip'] == day else 'not_enough')
        V = VEHICLES[vid]
        if V['fuel']:
            _jr()._wallet(j, -V['fuel'], KIND, f'Tiền xăng · {V["name"]}')
        g['trip'] = day
        g['stats']['trips'] = g['stats'].get('trips', 0) + 1
        up = _spirit(s, V['spirit'])
        fuel = f' Tiền xăng {_fmt(V["fuel"])} xu.' if V['fuel'] else ''
        return dict(message=f'{V["emoji"]} {_line(s, vid)}{fuel}', spirit=up,
                    effects=[f'😊 Tinh thần +{up}'] if up else [])
    if name == 'jr_garage_sell':
        need(set(p) <= {'id', 'confirm'}, 'Thông tin không hợp lệ.')
        vid = _vid(p)
        g = _mine(s, vid)
        V = VEHICLES[vid]
        need(p.get('confirm') is True, f'Xác nhận bán {lname(V["name"])}.')
        get_back = sell_price(g['cars'][vid]['p'])
        g['cars'].pop(vid)
        if g['ride'] == vid:
            g['ride'] = None
        g['stats']['sold'] = g['stats'].get('sold', 0) + 1
        if get_back:
            _jr()._wallet(j, get_back, KIND, f'Bán xe · {V["name"]}')
        return dict(message=f'Đã bán {lname(V["name"])}, nhận {_fmt(get_back)} xu vào ví.')
    raise e.GameError('Thao tác nhà xe không hợp lệ.', 'unknown_action')


# ---------------------------------------------------------------- views
def ride_view(s: dict) -> dict | None:
    """{id, emoji, name, color} of the vehicle shown as "đang đi" (None: none, or one this build does not know)."""
    g = get(s)
    vid = g.get('ride') if g else None
    if vid not in VEHICLES or vid not in g['cars']:
        return None
    V, car = VEHICLES[vid], g['cars'][vid]
    paint = PAINT_INDEX.get(car['c']) or PAINT_INDEX[V['paint']]
    return dict(id=vid, emoji=V['emoji'], name=V['name'], color=paint['hex'])


def public(s: dict) -> dict:
    j = s['journey']
    g = get(s) or initial()
    cars = []
    for vid in ORDER:
        car = g['cars'].get(vid)
        if not car:
            continue
        cars.append(dict(id=vid, color=car['c'] if car['c'] in PAINT_INDEX else VEHICLES[vid]['paint'], plate=car['n'],
                         day=car['d'], paid=car['p'], sell=sell_price(car['p']), trip_why=why_not_trip(s, vid),
                         upkeep=up.car_month(vid, car['p'])))
    market = [dict(id=vid, why=why_not_buy(s, vid)) for vid in ORDER if vid not in g['cars']]
    out = dict(story=bool(j.get('story')), life_day=j['life_day'], have=_have(s), cars=cars, ride=g['ride'],
               tripped=g['trip'] == j['life_day'], market=market, stats=dict(g['stats']))
    bills = up.public(s) if j.get('story') and cars else None
    if bills and (bills['car'] or bills['due']['car']):   # 🧾 this tháng's bill (absent: nothing to pay; an older server)
        out['upkeep'] = dict(month=bills['car'], next=bills['next'], due=bills['due']['car'])
    return out


def catalogue() -> dict:
    """Static list for the client (bootstrap content, cached)."""
    return dict(groups=[dict(id=g[0], emoji=g[1], name=g[2], where=g[3], color=g[4]) for g in GROUPS],
                vehicles=[dict(VEHICLES[vid], upkeep=up.car_month(vid, VEHICLES[vid]['price'])) for vid in ORDER],
                paints=[dict(x) for x in PAINT_INDEX.values()], sell_pct=SELL_PCT, plate_max=PLATE_MAX)
