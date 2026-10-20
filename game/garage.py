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
* 🏎️ Xe bản giới hạn (owner 16/10): the auction house's limited editions (game/auction_content.py kind 'vehicle', LIMITED
  here) join VEHICLES with `limited`, their base model's group, ride, fuel, trip and price (the upkeep's basis, stored
  as `p`) and a special paint (SPECIAL_PAINTS, only for them). Never in the shop, never sold back (the xu were burned at
  the auction: nothing to refund); winning one (grant_limited) parks it in the garage like a purchase.
* 🔨 Biển đẹp (owner 16/10): a plate won at the auction (journey.uniq.own kind 'plate', journey.uniq_x.own kinds 'reg'
  and 'hull') is attached to one vehicle of a fitting group (auction_content.PLATE_FIT; jr_garage_plate {item, id|None}),
  moved at will, one plate a vehicle; the attachments live in journey.uniq_x.on (game/auction.py: the strict garage
  block never changes). Before the first attachment, the dearest road plate rides on the road vehicle in use (how
  plates showed until 16/10). The vehicle ridden (`ride`) that carries one adds +x % to each shift's career income
  (bonus_now, auction_content.PLATE_PCT, 3-10 %), locked at the shift's start (journey.plate_lock, lock_shift /
  shift_pct): game/journey.py _end_of_day pays it.

State `s['journey']['garage']` (absent until the first purchase; older builds never read it: journey.validate allows
extra keys), see initial():
    v      VERSION
    cars   {vehicle id: {c: paint id, n: plate text ('' = none), d: life day bought, p: price paid}}
    ride   the vehicle id shown as "đang đi", or None
    trip   the life day of the last ride out (0: never)
    stats  {bought, sold, trips}
Siblings in the journey (optional; older builds keep them without reading): garage_trips {vehicle id: life day} and
plate_lock {career id: percent locked when its shift started}.
Ids are stored in saves: never rename or remove one. A vehicle or paint id this build does not know (a newer build
wrote it) is kept untouched and simply not shown, so a rollback never loses anything.
Commands (through journey.action, so journey.after and validate_state run): jr_garage_buy {id, color, plate?, confirm},
jr_garage_paint {id, color?, plate?}, jr_garage_ride {id | None}, jr_garage_trip {id}, jr_garage_sell {id, confirm},
jr_garage_plate {item, id | None}.
Deterministic: the only draw (the ride's line) is seeded by the journey seed, the life day and the vehicle.
"""
from __future__ import annotations

import hashlib
import re

from . import auction_content as AC   # 🏎️ limited editions and 🔨 plates (data only)
from . import bank as bk
from . import price_index as pi   # 💹 07/10: prices below are the base; the catalogue holds the indexed ones
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
COMMANDS = ('jr_garage_buy', 'jr_garage_paint', 'jr_garage_ride', 'jr_garage_trip', 'jr_garage_sell', 'jr_garage_plate')
LOCK_KEY = 'plate_lock'           # journey[LOCK_KEY]: {career: percent} locked at the shift's start
LOCK_RE = re.compile(r'[a-z0-9_]{1,40}')

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
# 🏎️ Only the limited editions wear these (game/auction_content.py LIMITED names one each).
SPECIAL_PAINTS = (
    ('vang_kim', 'Vàng kim', '#d4a838'), ('do_ruou', 'Đỏ rượu vang', '#7b2335'), ('ngoc_bich', 'Xanh ngọc bích', '#1f8a7a'),
    ('bach_kim', 'Bạch kim', '#dfe3e6'), ('xanh_dem', 'Xanh đêm', '#1b2a52'), ('kem_co', 'Kem cổ điển', '#efe0bf'),
    # 20/10: the new limited editions' (an older build keeps the id on the car by shape and draws the first paint)
    ('hong_ngoc', 'Hồng ngọc', '#a8203a'), ('ngoc_trai', 'Trắng ngọc trai', '#f4efe6'), ('dong_co', 'Đồng cổ', '#9a6a3a'),
    ('den_nhung', 'Đen nhung', '#1d1a22'), ('cam_hoang_hon', 'Cam hoàng hôn', '#e8743b'),
)
PAINT_INDEX = {p[0]: dict(id=p[0], name=p[1], hex=p[2]) for p in PAINTS}
PAINT_INDEX.update({p[0]: dict(id=p[0], name=p[1], hex=p[2], limited=True) for p in SPECIAL_PAINTS})


def _v(vid, group, emoji, name, price, desc, spirit, fuel, trip, paint='do'):
    """spirit: tinh thần from one ride out; fuel: its xu (0: free); trip: the button's words; paint: the default.
    price and fuel are the base (pre-07/10) prices: the catalogue holds them through game/price_index.py (the luxury
    tiers included). A vehicle keeps the price paid (`p`), which selling back and the upkeep use."""
    return vid, dict(id=vid, group=group, emoji=emoji, name=name, price=pi.price(price), desc=desc, spirit=spirit,
                     fuel=pi.price(fuel, luxury=False),
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


def _limited(it: dict) -> tuple:
    """A limited edition of the auction house: its base model's group, ride, fuel, trip and price (the upkeep's basis
    and `p`), its own name, emoji, paint and number."""
    B = VEHICLES[it['base']]
    return it['id'], dict(id=it['id'], group=B['group'], emoji=it['emoji'], name=it['name'], price=B['price'],
                          desc=it['desc'], spirit=B['spirit'], fuel=B['fuel'], trip=B['trip'], paint=it['paint'],
                          limited=True, base=it['base'], serial=it['serial'], tier=it['tier'])


VEHICLES.update(_limited(it) for it in AC.LIMITED)
ORDER = tuple(VEHICLES)
SHOP = tuple(vid for vid in ORDER if not VEHICLES[vid].get('limited'))   # what the shop sells

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


def _rui():
    from . import rui
    return rui


def _fmt(n: int) -> str:
    return bk._fmt(n)


def lname(name: str) -> str:
    """A name inside a sentence: "Xe đạp phố" -> "xe đạp phố"."""
    return name[:1].lower() + name[1:]


def vname(V: dict) -> str:
    """A vehicle inside a sentence: a shop model in lower case, a limited edition by its own name."""
    return V['name'] if V.get('limited') else lname(V['name'])


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


def used_before(s: dict, vid: str, day: int) -> bool:
    """A real outing yesterday, for one life-day risk roll; displaying a vehicle is cosmetic.
    The optional journey sibling keeps the strict legacy garage block rollback-compatible.
    """
    trips=s.get('journey',{}).get('garage_trips',{})
    return isinstance(trips,dict) and trips.get(vid)==day-1


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
    text = _core().clean_text(raw, PLATE_MAX, 0)
    if text != default:   # 🔨 a vanity plate of the auction house is one of a kind (game/auction.py): never copied
        from .auction import fold_plate, plates
        _core().need(fold_plate(text) not in plates(), 'Biển số này thuộc Nhà đấu giá, chọn biển khác nhé.', 'taken')
    return text


def why_not_buy(s: dict, vid: str) -> str | None:
    """Why `vid` cannot be bought now (None: it can). Shown on the disabled button."""
    j = s['journey']
    if not j.get('story'):
        return 'Mua xe chỉ có trong chế độ hành trình.'
    V = VEHICLES[vid]
    g = get(s)
    if g and vid in g['cars']:
        return f'Bạn đã có {vname(V)} rồi.'
    if V.get('limited'):
        return 'Xe bản giới hạn chỉ có ở Nhà đấu giá.'
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
    if _rui().is_broken(s, 'xe', vid):
        return 'Xe đang hỏng. Sửa xong rồi đi nhé.'
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
    if isinstance(j, dict) and LOCK_KEY in j:   # 🔨 the plate bonus locked at a shift's start (optional)
        lk = j[LOCK_KEY]
        e.need(isinstance(lk, dict) and len(lk) <= 64 and all(isinstance(k, str) and LOCK_RE.fullmatch(k) and type(v) is int
                                                              and 1 <= v <= AC.PCT_CAP for k, v in lk.items()),
               'Nhà xe trong bản lưu không hợp lệ.', 'invalid_save')
    if g is None:
        e.need(not isinstance(j, dict) or j.get('garage') is None, 'Nhà xe trong bản lưu không hợp lệ.', 'invalid_save')
        return
    bad = 'Nhà xe trong bản lưu không hợp lệ.'
    e.need(set(g) == BLOCK_KEYS and g['v'] == VERSION, bad, 'invalid_save')
    cars = g['cars']
    e.need(isinstance(cars, dict) and len(cars) <= 64 and all(_car_ok(k, v) for k, v in cars.items()), bad, 'invalid_save')
    trips=j.get('garage_trips',{})
    e.need(isinstance(trips,dict) and len(trips)<=64 and all(k in cars and type(v) is int and 1<=v<=10**6 for k,v in trips.items()),bad,'invalid_save')
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
    if LOCK_KEY in j:
        lk = j[LOCK_KEY]
        j[LOCK_KEY] = {k: v for k, v in lk.items() if isinstance(k, str) and LOCK_RE.fullmatch(k) and type(v) is int
                       and 1 <= v <= AC.PCT_CAP} if isinstance(lk, dict) else {}
        if not j[LOCK_KEY]:
            j.pop(LOCK_KEY)
    if 'garage_trips' in j:
        trips=j['garage_trips']
        j['garage_trips']={k:v for k,v in trips.items() if k in out['cars'] and type(v) is int and 1<=v<=10**6} if isinstance(trips,dict) else {}


# ---------------------------------------------------------------- commands
def _vid(p: dict, key: str = 'id') -> str:
    vid = p.get(key)
    _core().need(isinstance(vid, str) and vid in VEHICLES, 'Chọn một chiếc xe nhé.')
    return vid


def _paint(p: dict, default: str, vid: str | None = None) -> str:
    c = p.get('color', default)
    _core().need(isinstance(c, str) and c in PAINT_INDEX, 'Màu sơn này không có trong bảng màu.')
    _core().need(not PAINT_INDEX[c].get('limited') or bool(vid and VEHICLES[vid].get('limited')),
                 'Màu này chỉ dành cho xe bản giới hạn.')
    return c


def _mine(s: dict, vid: str) -> dict:
    g = get(s)
    _core().need(g is not None and vid in g['cars'], f'Bạn chưa có {vname(VEHICLES[vid])}.', 'not_owned')
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
        need(not V.get('limited'), 'Xe bản giới hạn chỉ có ở Nhà đấu giá.', 'limited')
        color = _paint(p, V['paint'], vid)
        plate = _plate(p)
        g = get(s)
        if g and vid in g['cars']:   # a second tap: nothing to pay
            return dict(message=f'Bạn đã có {vname(V)} rồi.', duplicate=True)
        need(p.get('confirm') is True, f'Xác nhận mua {vname(V)}.')
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
        return dict(message=f'Đã trả {how} cho {vname(V)} màu {PAINT_INDEX[color]["name"].lower()}.{tail}')
    if name == 'jr_garage_paint':
        need(set(p) <= {'id', 'color', 'plate'} and ('color' in p or 'plate' in p), 'Thông tin sơn xe không hợp lệ.')
        vid = _vid(p)
        g = _mine(s, vid)
        car = g['cars'][vid]
        color = _paint(p, car['c'] if car['c'] in PAINT_INDEX else VEHICLES[vid]['paint'], vid)
        plate = _plate(p, car['n'])
        if color == car['c'] and plate == car['n']:
            return dict(message='Chiếc xe vẫn y như cũ.', duplicate=True)
        car['c'], car['n'] = color, plate
        nm = vname(VEHICLES[vid])
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
        b = bonus_now(s)   # 🔨 its plate's bonus counts from the next shift opened (lock_shift)
        tail = f' Biển đẹp: lợi nhuận +{b["pct"]}% từ ca mở sau.' if b else ''
        return dict(message=f'Giờ bạn đi {vname(VEHICLES[vid])}.{tail}')
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
        j.setdefault('garage_trips',{})[vid]=day
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
        need(not V.get('limited'), 'Xe bản giới hạn là độc bản, không bán lại được.', 'limited')
        need(p.get('confirm') is True, f'Xác nhận bán {vname(V)}.')
        get_back = max(0, sell_price(g['cars'][vid]['p']) - _rui().broken_cost(s, 'xe', vid))   # 🛡️ a broken one: less
        g['cars'].pop(vid)
        if isinstance(j.get('garage_trips'),dict):j['garage_trips'].pop(vid,None)
        if g['ride'] == vid:
            g['ride'] = None
        g['stats']['sold'] = g['stats'].get('sold', 0) + 1
        if get_back:
            _jr()._wallet(j, get_back, KIND, f'Bán xe · {V["name"]}')
        off = _detach_from(s, vid)
        tail = f' Biển “{off}” đã tháo, cất lại trong hộp.' if off else ''
        return dict(message=f'Đã bán {vname(V)}, nhận {_fmt(get_back)} xu vào ví.{tail}')
    if name == 'jr_garage_plate':
        return _plate_action(s, p)
    raise e.GameError('Thao tác nhà xe không hợp lệ.', 'unknown_action')


# ---------------------------------------------------------------- 🏎️ limited editions, 🔨 plates and Biển đẹp +x %
def _auc():
    from . import auction
    return auction


def grant_limited(s: dict, vid: str) -> str:
    """A limited edition won at the auction (game/auction.py apply_fx) parks in the garage: its special paint, no plate,
    `p` its base model's price (the upkeep's basis). The sentence for the win's message ('' when nothing was added)."""
    V = VEHICLES.get(vid)
    if not V or not V.get('limited'):
        return ''
    g = _ensure(s)
    if vid in g['cars'] or len(g['cars']) >= 64:
        return ''
    g['cars'][vid] = dict(c=V['paint'], n='', d=s['journey']['life_day'], p=V['price'])
    if g['ride'] is None:
        g['ride'] = vid
    return ' Xe đã vào nhà xe của bạn.'


def my_plates(s: dict) -> dict:
    """The auction plates this save owns: {item: {id, k, t, tier, fit}} (tier 1 for an operator-made one)."""
    out = {}
    for item, x in _auc().owned(s).items():
        k = x.get('k')
        if k not in AC.PLATE_KINDS:
            continue
        it = AC.ITEM.get(item)
        tier = it['tier'] if it and it['kind'] == k and it['tier'] in (1, 2, 3) else 1
        out[item] = dict(id=item, k=k, t=x['t'], tier=tier, fit=AC.PLATE_FIT[k])
    return out


def attached(s: dict, plates: dict | None = None) -> dict:
    """{plate item: vehicle id} that hold now: an owned plate on an owned vehicle this build knows, of a fitting
    group, one plate a vehicle (stale entries an older build left, e.g. after selling the car there, are skipped)."""
    g = get(s)
    if not g:
        return {}
    plates = my_plates(s) if plates is None else plates
    out, used = {}, set()
    for item, vid in _auc().plates_on(s).items():
        P = plates.get(item)
        V = VEHICLES.get(vid)
        if not P or not V or vid not in g['cars'] or not fits(P['k'], vid) or vid in used:
            continue
        out[item] = vid
        used.add(vid)
    return out


def fits(kind: str, vid: str) -> bool:
    """A plate of this kind goes on this vehicle: its group (PLATE_FIT), never a pedal bike."""
    V = VEHICLES.get(vid)
    return bool(V) and V['group'] in AC.PLATE_FIT.get(kind, ()) and (V.get('base') or vid) not in AC.NO_PLATE


def pct_of(vid: str, tier: int) -> int:
    """Biển đẹp +x %: by the vehicle's group and the plate's tier, +1 on a limited edition, never above PCT_CAP."""
    V = VEHICLES[vid]
    row = AC.PLATE_PCT[V['group']]
    n = row[max(1, min(3, tier)) - 1] + (AC.LIMITED_PCT if V.get('limited') else 0)
    return max(0, min(AC.PCT_CAP, n))


def bonus_now(s: dict) -> dict | None:
    """The bonus the vehicle ridden now gives ({pct, id, item, t, k}), or None (no ride, or no plate on it)."""
    g = get(s)
    ride = g.get('ride') if g else None
    if not ride or ride not in VEHICLES or ride not in g['cars']:
        return None
    plates = my_plates(s)
    for item, vid in attached(s, plates).items():
        if vid == ride:
            P = plates[item]
            return dict(pct=pct_of(vid, P['tier']), id=vid, item=item, t=P['t'], k=P['k'])
    return None


def lock_shift(s: dict, career: str) -> None:
    """A shift starts (game/journey.py after start_day): remember the bonus of the vehicle ridden now."""
    j = s['journey']
    b = bonus_now(s)
    lk = j.get(LOCK_KEY) if isinstance(j.get(LOCK_KEY), dict) else {}
    if b and b['pct'] > 0 and LOCK_RE.fullmatch(career):
        lk[career] = b['pct']
    else:
        lk.pop(career, None)
    if lk:
        j[LOCK_KEY] = lk
    else:
        j.pop(LOCK_KEY, None)


def shift_pct(s: dict, career: str) -> tuple[int, dict | None]:
    """A shift closes: (the percent paid, the bonus now). The smaller of the start's lock and the vehicle ridden now:
    switching vehicles, moving the plate or selling mid-shift never raises it; no lock (a shift started before this
    build, or without a plated ride): 0. The lock is used once."""
    j = s['journey']
    lk = j.get(LOCK_KEY) if isinstance(j.get(LOCK_KEY), dict) else {}
    locked = lk.pop(career, 0)
    if not lk:
        j.pop(LOCK_KEY, None)
    now = bonus_now(s)
    if not now or type(locked) is not int:
        return 0, now
    return max(0, min(locked, now['pct'], AC.PCT_CAP)), now


def _detach_from(s: dict, vid: str) -> str:
    """The plate on `vid` back in its box (the vehicle sold): its text, or ''."""
    on = _auc().x_on(s)
    item = next((i for i, v in (on or {}).items() if v == vid), None)
    if item is None:
        return ''
    on.pop(item)
    return my_plates(s).get(item, {}).get('t', '')


FIT_WORDS = {'plate': 'Biển số gắn lên xe máy hoặc ô tô.', 'reg': 'Số đăng ký gắn lên máy bay.',
             'hull': 'Biển tên gắn lên du thuyền.'}


def _plate_action(s: dict, p: dict) -> dict:
    """jr_garage_plate {item, id | None}: attach an auction plate to one of your vehicles (moving it from the one it
    was on; the plate already there goes back to its box), or take it off (id None)."""
    e = _core()
    need = e.need
    need(isinstance(p, dict) and set(p) <= {'item', 'id'} and 'item' in p, 'Thông tin gắn biển không hợp lệ.')
    plates = my_plates(s)
    item = p['item']
    need(isinstance(item, str) and item in plates, 'Bạn chưa có biển này.', 'not_owned')
    P = plates[item]
    now = attached(s, plates)
    if p.get('id') is None:
        if item not in now:
            return dict(message=f'Biển “{P["t"]}” đang cất trong hộp.', duplicate=True)
        _auc().x_ensure(s)['on'].pop(item, None)
        return dict(message=f'Đã tháo biển “{P["t"]}”, cất lại trong hộp.')
    vid = _vid(p)
    _mine(s, vid)
    V = VEHICLES[vid]
    need(fits(P['k'], vid), FIT_WORDS[P['k']], 'wrong_kind')
    if now.get(item) == vid:
        if _auc().x_get(s) is None:   # shown there by the legacy rule (it followed the ride): pinned now
            _auc().x_ensure(s)
            return dict(message=f'Đã gắn biển “{P["t"]}” lên {vname(V)}.')
        return dict(message=f'Biển “{P["t"]}” đang ở trên {vname(V)} rồi.', duplicate=True)
    on = _auc().x_ensure(s)['on']
    prev = next((i for i, v in now.items() if v == vid and i != item), None)
    for i in [i for i, v in on.items() if v == vid or i == item]:
        on.pop(i)
    need(len(on) < _auc().X_ON_MAX, 'Bạn đã gắn quá nhiều biển.', 'limit')
    on[item] = vid
    tail = f' Biển “{plates[prev]["t"]}” cất lại trong hộp.' if prev else ''
    pct = pct_of(vid, P['tier'])
    ride = (get(s) or {}).get('ride') == vid
    perk = f' Đi chiếc này: lợi nhuận mỗi ca +{pct}%.' if not ride else f' Đang đi chiếc này: lợi nhuận mỗi ca +{pct}%.'
    return dict(message=f'Đã gắn biển “{P["t"]}” lên {vname(V)}.{tail}{perk}')


# ---------------------------------------------------------------- views
def ride_view(s: dict) -> dict | None:
    """{id, emoji, name, color} of the vehicle shown as "đang đi" (None: none, or one this build does not know)."""
    g = get(s)
    vid = g.get('ride') if g else None
    if vid not in VEHICLES or vid not in g['cars']:
        return None
    V, car = VEHICLES[vid], g['cars'][vid]
    paint = PAINT_INDEX.get(car['c']) or PAINT_INDEX[V['paint']]
    out = dict(id=vid, emoji=V['emoji'], name=V['name'], color=paint['hex'])
    b = bonus_now(s)
    if b:   # 🔨 an auction plate on it (gold wherever it shows)
        out['plate'] = b['t']
    if V.get('limited'):
        out['limited'] = V['serial']
    return out


def public(s: dict) -> dict:
    j = s['journey']
    g = get(s) or initial()
    cars = []
    plates = my_plates(s)
    on = attached(s, plates)
    by_car = {vid: item for item, vid in on.items()}
    for vid in ORDER:
        car = g['cars'].get(vid)
        if not car:
            continue
        fix = _rui().broken_cost(s, 'xe', vid) if _rui().is_broken(s, 'xe', vid) else None
        limited = bool(VEHICLES[vid].get('limited'))
        row = dict(id=vid, color=car['c'] if car['c'] in PAINT_INDEX else VEHICLES[vid]['paint'], plate=car['n'],
                   day=car['d'], paid=car['p'], sell=0 if limited else max(0, sell_price(car['p']) - (fix or 0)),
                   trip_why=why_not_trip(s, vid), upkeep=up.car_month(vid, car['p']), **({'broken': fix} if fix is not None else {}))
        if limited:
            row['limited'] = True
        item = by_car.get(vid)
        if item:   # 🔨 the auction plate on it, gold, and the percent it gives while ridden
            P = plates[item]
            row['uq'] = dict(item=item, t=P['t'], k=P['k'], pct=pct_of(vid, P['tier']))
        cars.append(row)
    market = [dict(id=vid, why=why_not_buy(s, vid)) for vid in SHOP if vid not in g['cars']]
    out = dict(story=bool(j.get('story')), life_day=j['life_day'], have=_have(s), cars=cars, ride=g['ride'],
               tripped=g['trip'] == j['life_day'], market=market, stats=dict(g['stats']))
    if plates:   # 🔨 the auction plates owned, where each one is (None: in its box)
        out['plates'] = [dict(P, fit=list(P['fit']), on=on.get(item)) for item, P in plates.items()]
    b = bonus_now(s)
    if b:
        out['bonus'] = b
    trips = j.get('garage_trips')
    if out['tripped'] and isinstance(trips, dict):   # ✈️ the vehicle taken out today (the island town flies a plane over)
        tid = next((vid for vid, d in trips.items() if d == j['life_day'] and vid in g['cars']), None)
        if tid:
            out['trip_id'] = tid
    bills = up.public(s) if j.get('story') and cars else None
    if bills and (bills['car'] or bills['due']['car']):   # 🧾 this tháng's bill (absent: nothing to pay; an older server)
        out['upkeep'] = dict(month=bills['car'], next=bills['next'], due=bills['due']['car'])
    return out


def catalogue() -> dict:
    """Static list for the client (bootstrap content, cached)."""
    return dict(groups=[dict(id=g[0], emoji=g[1], name=g[2], where=g[3], color=g[4]) for g in GROUPS],
                vehicles=[dict(VEHICLES[vid], upkeep=up.car_month(vid, VEHICLES[vid]['price'])) for vid in ORDER],
                paints=[dict(x) for x in PAINT_INDEX.values()], sell_pct=SELL_PCT, plate_max=PLATE_MAX,
                plate_pct=dict(table={k: list(v) for k, v in AC.PLATE_PCT.items()}, limited=AC.LIMITED_PCT, cap=AC.PCT_CAP,
                               shift_cap=AC.BONUS_CAP, fit={k: list(v) for k, v in AC.PLATE_FIT.items()}))
