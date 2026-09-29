"""Stock, suppliers and purchase orders for plugin trade careers (v0.4).

Money is paid when an order is placed. Goods enter stock only after the player
counts the delivery. A short delivery can be claimed back once; every supplier
order can be rated, and the supplier answers in its own voice. Lots expire by
game day at closing time: the value is recorded as waste, never charged twice.

Deliveries run on the shop's clock, not on beats: every supplier promises a
window in time of day (30–60 minutes, this afternoon's run, tomorrow before
opening, two or three days for special goods). `clock()` turns the career's
turn counter into that time of day. See
docs/superpowers/specs/2026-09-29-supplier-lead-times.md.
"""
from __future__ import annotations
import copy
import math
import random
from .jsoncopy import tree_copy

# ---------------------------------------------------------------- the shop clock
DAY_MIN = 24 * 60
STEP = 20  # minutes of shop time for one ticking action
DEFAULT_HOURS = (8 * 60, 20 * 60)
HOURS = {
    'restaurant': (10 * 60, 22 * 60),
    'cafe_bakery': (7 * 60, 19 * 60),
    'florist': (7 * 60 + 30, 19 * 60 + 30),
    'grocery': (6 * 60 + 30, 21 * 60 + 30),
    'repair': (8 * 60, 19 * 60),
    'farm': (5 * 60 + 30, 17 * 60 + 30),
    'delivery': (17 * 60, 23 * 60),  # evening shift, like the courier's own route clock
    'homestay': (7 * 60, 22 * 60),
    'pet_care': (8 * 60, 19 * 60),
    'salon': (8 * 60 + 30, 20 * 60),
}
EARLY = 30  # goods due after closing wait at the door this many minutes before the next opening


def hours(career: str) -> tuple[int, int]:
    return HOURS.get(career, DEFAULT_HOURS)


def hm(minute: int) -> str:
    m = int(minute) % DAY_MIN
    return f'{m // 60:02d}:{m % 60:02d}'


def _turn0(c: dict) -> int | None:
    """Turn of this day's start_day: stored by on_open or the first stock
    action of the day, else read from the 'Mở ca ngày N.' journal row."""
    x = (c.get('ext') or {}).get('inv') or {}
    opened = x.get('opened')
    if isinstance(opened, dict) and opened.get('day') == c['day']:
        return opened.get('turn')
    for row in reversed(c.get('journal') or []):
        d = row.get('day', 0) if isinstance(row, dict) else 0
        if d < c['day']:
            break
        if row.get('kind') == 'day' and d == c['day'] and str(row.get('text', '')).startswith('Mở ca'):
            return row.get('turn')
    return None


def clock(c: dict, career: str, turn: int | None = None) -> dict:
    """Time of day for any career. Open: opening time + STEP minutes per turn
    since start_day (or the career's own `clock_minutes(c)` hook), capped at
    closing. Closed: the evening of the day that just closed, at closing time,
    so goods due before the next opening are at the door when the day starts."""
    op, cl = hours(career)
    day = c['day']
    if c.get('open'):
        minute = None
        from .careers import PLUGINS
        hook = getattr(PLUGINS.get(career), 'clock_minutes', None)
        if hook:
            try:
                minute = hook(c)
            except Exception:  # a career clock is optional and never blocks stock
                minute = None
        if not isinstance(minute, int):
            t = c['turn'] if turn is None else turn
            t0 = _turn0(c)
            minute = op + max(0, t - (t if t0 is None else t0)) * STEP
        minute = max(op, min(cl, minute))
    else:
        day, minute = day - 1, cl
    return dict(day=day, minute=minute, abs=day * DAY_MIN + minute, open=op, close=cl, step=STEP,
                is_open=bool(c.get('open')))


def _part(minute: int) -> str:
    m = minute % DAY_MIN
    return 'sáng' if m < 11 * 60 else 'trưa' if m < 13 * 60 else 'chiều' if m < 18 * 60 else 'tối'


def when(t: int, now: int, approx: bool = False, quote: bool = False) -> str:
    """'16:45 hôm nay' / 'Chiều nay ~16:45' (quote) / 'Sáng mai 07:15' /
    'Sáng ngày kia 07:15' / 'Ngày 7 · 10:30'."""
    d, m = divmod(t, DAY_MIN)
    diff = d - now // DAY_MIN
    time = ('~' if approx else '') + hm(m)
    if diff < 0:
        return f'Ngày {d} · {time}'
    if diff == 0:
        return f'{_part(m).capitalize()} nay {time}' if quote else f'{time} hôm nay'
    if diff == 1:
        return f'{_part(m).capitalize()} mai {time}'
    if diff == 2:
        return f'{_part(m).capitalize()} ngày kia {time}'
    return f'Ngày {d} · {time}'


def _duration(minutes: int) -> str:
    minutes = max(5, int(math.ceil(minutes / 5.0)) * 5)
    if minutes < 60:
        return f'~{minutes} phút'
    h, m = divmod(minutes, 60)
    return f'~{h} giờ' + (f' {m} phút' if m else '')


def _r5(minute: float) -> int:
    return int(round(minute / 5.0)) * 5


def _after_hours(t: int, career: str) -> int:
    """A drop after closing time waits at the door before the next opening."""
    op, cl = hours(career)
    d, m = divmod(t, DAY_MIN)
    if m > cl:
        return (d + 1) * DAY_MIN + op - EARLY
    return t


# ---------------------------------------------------------------- suppliers
V_MARKET = dict(good='Cảm ơn quán nha, mai chị để hàng đẹp cho!',
                bad='Ờ chợ đông quá chị đếm sót, lần sau chị ghi phiếu kỹ hơn.',
                claim='Thiếu thì chị bù tiền, mình buôn bán lâu dài mà.',
                late='Xe ba gác của chị kẹt ở đầu chợ, tới trễ chút nha em.')
V_PARTNER = dict(good='Hạt Nắng ghi nhận đánh giá, cảm ơn quý khách.',
                 bad='Bên em đã chuyển phản hồi cho bộ phận kho để kiểm lại quy trình.',
                 claim='Đã lập phiếu hoàn cho phần thiếu theo biên bản giao nhận.',
                 late='Xe giao của Hạt Nắng kẹt ở cầu Mây, bên em báo trễ khoảng một tiếng ạ.')
V_EXPRESS = dict(good='Mây Xanh luôn sẵn sàng khi quán cần gấp!',
                 bad='Xin lỗi quý khách, tài xế sẽ được nhắc lại quy trình.',
                 claim='Đã hoàn tiền phần thiếu ngay.',
                 late='Tài xế phải vòng tránh đoạn đường ngập, tới trễ vài chục phút ạ.')
V_FAR = dict(good='Kho ghi nhận, cảm ơn quý khách đã tin hàng đi xa.',
             bad='Hàng đi đường dài, bên em sẽ đóng thùng kỹ hơn.',
             claim='Kho đã lập phiếu bù cho phần thiếu.',
             late='Xe tuyến về trễ một ngày vì kẹt ở trạm, kho xin lỗi quý khách.')
V_MAKER = dict(good='Cảm ơn tiệm, mẻ sau vẫn làm kỹ như vậy!',
               bad='Xưởng xin nhận góp ý, mẻ sau kiểm lại từng túi.',
               claim='Xưởng gửi bù phần thiếu vào đơn sau, trả tiền trước nha.',
               late='Mẻ hôm nay ra lò muộn, xưởng giao trễ một chút ạ.')
V_GARDEN = dict(good='Nhà vườn cảm ơn nha, hoa mới cắt sáng nay đó!',
                bad='Đường đèo xóc quá, lần sau vườn lót thêm giấy báo.',
                claim='Cành gãy thì vườn bù tiền liền, đừng lo.',
                late='Xe đêm từ Đà Lạt xuống bị sương mù đèo Mây, tới trễ vài tiếng.')
V_COOP = dict(good='Hợp tác xã cảm ơn bà con, vụ sau lại ủng hộ nha!',
              bad='Kho hợp tác xã sẽ cân lại kỹ hơn.',
              claim='Thiếu bao nào hợp tác xã trả lại tiền bao đó.',
              late='Xe công nông của hợp tác xã hỏng giữa đường, tới trễ một chút.')

MARKET = dict(id='market', name='Chợ đầu mối Mây', emoji='🧺', kind='next', cutoff=17 * 60, at=(-75, -35),
              factor=0.85, short=22, late=10,
              note='Rẻ nhất. Đặt trước 17:00, hàng tới sáng mai trước giờ mở cửa. Thỉnh thoảng giao thiếu, cần đếm kỹ.',
              voice=V_MARKET)
PARTNER = dict(id='partner', name='Nhà phân phối Hạt Nắng', emoji='🚚', kind='runs',
               runs=((11 * 60, 13 * 60, 14 * 60), (15 * 60, 16 * 60 + 30, 17 * 60 + 30)),
               factor=1.0, short=6, late=8,
               note='Giá niêm yết, có phiếu giao rõ ràng. Xe chạy hai chuyến: đặt trước 11:00 tới trưa, trước 15:00 tới chiều.',
               voice=V_PARTNER)
EXPRESS = dict(id='express', name='Giao hỏa tốc Mây Xanh', emoji='⚡', kind='rush', mins=(30, 60),
               factor=1.35, short=0, late=12,
               note='Đắt nhất nhưng tới trong 30–60 phút. Dùng khi cháy hàng giữa ca.', voice=V_EXPRESS)
DEFAULT_SUPPLIERS = [MARKET, PARTNER, EXPRESS]
SUPPLIER_INDEX = {x['id']: x for x in DEFAULT_SUPPLIERS}


def _s(base: dict, **kw) -> dict:
    d = copy.deepcopy(base)
    d.update(kw)
    return d


SUPPLIERS = {
    'restaurant': [
        _s(MARKET, items=['noodle', 'chili', 'beef', 'sausage', 'kimchi_side', 'egg', 'mushroom', 'fishball', 'tofu',
                          'seafood', 'fried_egg']),
        PARTNER, EXPRESS,
        dict(id='import', name='Kho hàng nhập Kim Mây', emoji='✈️', kind='days', days=(2, 3), at=(60, 180),
             factor=0.72, short=4, late=15, voice=V_FAR,
             items=['pack_kimchi', 'pack_tomyum', 'pack_blackbean', 'pack_cheese', 'kimchi_side', 'cheese_slice',
                    'ricecake', 'fishball', 'sausage', 'beef'],
             note='Gói nước dùng, phô mai, bánh gạo, bò Mỹ nhập thẳng: rẻ hơn hẳn nhưng 2–3 ngày mới tới. Đặt sớm cho cả tuần.'),
    ],
    'cafe_bakery': [
        _s(MARKET, items=['milk', 'oat', 'condensed', 'cream', 'flour', 'butter', 'egg', 'sugar', 'almond']),
        PARTNER, EXPRESS,
        dict(id='roaster', name='Xưởng rang Đồi Mây', emoji='☕', kind='next', cutoff=18 * 60, at=(180, 240),
             factor=0.8, short=3, late=8, voice=V_MAKER, items=['beans_house', 'beans_robusta', 'beans_decaf'],
             note='Rang theo đơn mỗi sáng. Đặt trước 18:00, hạt mới rang tới trưa mai. Rẻ và thơm hơn.'),
    ],
    'florist': [
        _s(MARKET, name='Chợ hoa đêm Sương Mai', emoji='💐', cutoff=22 * 60, factor=0.85, short=25,
           items=['rose_red', 'rose_pink', 'rose_white', 'rose_yellow', 'lily', 'mum_white', 'sunflower', 'carnation',
                  'orchid', 'babys_breath', 'eucalyptus'],
           note='Chợ hoa họp đêm: đặt trước 22:00, hoa tới sáng mai trước giờ mở cửa. Rẻ, nhưng hay gãy hoặc thiếu vài cành.',
           voice=dict(V_MARKET, good='Cảm ơn tiệm nha, đêm mai chị lựa bó đẹp nhất!',
                      late='Chợ hoa đêm nay đông quá, xe chị ra muộn một chút.')),
        dict(id='dalat', name='Nhà vườn Đà Lạt', emoji='🌄', kind='next', cutoff=15 * 60, at=(60, 150),
             factor=0.7, short=10, late=15, fresh=1, voice=V_GARDEN,
             items=['rose_red', 'rose_pink', 'rose_white', 'rose_yellow', 'lily', 'mum_white', 'carnation',
                    'babys_breath', 'eucalyptus'],
             note='Hoa cắt tại vườn, đi xe đêm: đặt trước 15:00, sáng mai tới. Rẻ nhất và tươi thêm 1 ngày, nhưng xe đèo hay trễ.'),
        PARTNER, _s(EXPRESS, factor=1.4),
    ],
    'grocery': [
        _s(MARKET, items=['egg', 'milk', 'bread', 'greens', 'tomato']),
        PARTNER, EXPRESS,
        dict(id='wholesale', name='Tổng kho sỉ Mây Xanh', emoji='🏭', kind='days', days=(1, 2), at=(120, 240),
             factor=0.8, short=5, late=10, voice=V_FAR,
             items=['rice', 'noodle', 'fishsauce', 'oil', 'soap', 'snack', 'soda', 'beer'],
             note='Hàng khô, nước, bia theo thùng: giá sỉ, 1–2 ngày mới giao. Hợp để trữ hàng không hạn.'),
    ],
    'repair': [
        _s(MARKET, name='Chợ linh kiện Mây', emoji='🔌', cutoff=16 * 60, factor=0.8, short=15,
           items=['screen_c', 'battery_c', 'port', 'cap_c', 'fuse', 'terminal', 'tube', 'rimtape', 'chain', 'brake',
                  'hp_battery', 'driver', 'solder', 'paste', 'oil', 'shrink', 'screen_u', 'battery_u', 'motor_u', 'ipa'],
           note='Linh kiện tương thích và đồ tháo máy giá mềm. Đặt trước 16:00, sáng mai có. Đôi khi thiếu, đếm kỹ.',
           voice=dict(V_MARKET, good='Cảm ơn anh chị thợ, mai sạp để hàng tốt!',
                      late='Sạp đóng hàng muộn, xe ôm chở trễ chút nha.')),
        PARTNER, EXPRESS,
        dict(id='genuine', name='Kho linh kiện chính hãng', emoji='✈️', kind='days', days=(2, 3), at=(60, 240),
             factor=0.85, short=0, late=15, voice=V_FAR,
             items=['screen_g', 'battery_g', 'cap_g', 'fan_motor', 'heater', 'ssd'],
             note='Hàng hãng có tem bảo hành, gửi từ kho miền: 2–3 ngày. Rẻ hơn đại lý nhưng phải hẹn khách trước.'),
    ],
    'farm': [
        dict(id='coop', name='HTX Nông nghiệp Mây', emoji='🌾', kind='next', cutoff=16 * 60, at=(60, 120),
             factor=0.8, short=10, late=8, voice=V_COOP,
             items=['seed_muong', 'seed_lettuce', 'seed_tomato', 'seed_cucumber', 'seed_herbs', 'compost', 'npk',
                    'bio_spray', 'chem_spray', 'feed', 'bag', 'carton', 'egg_tray'],
             note='Giá xã viên. Đặt trước 16:00, xe hợp tác xã chở tới sáng mai. Thỉnh thoảng thiếu một bao.'),
        _s(PARTNER, name='Đại lý vật tư Hạt Nắng'),
        _s(EXPRESS, name='Xe ba gác hỏa tốc', note='Chở gấp trong 30–60 phút, đắt. Dùng khi gà sắp hết cám.'),
        dict(id='nursery', name='Trại giống Đồng Xanh', emoji='🌱', kind='days', days=(2, 3), at=(90, 240),
             factor=0.7, short=0, late=12, voice=V_MAKER, items=['seed_tomato', 'seed_cucumber', 'seed_herbs'],
             note='Cây giống ươm theo đơn: rẻ nhất nhưng 2–3 ngày mới có.'),
    ],
    'delivery': [
        _s(MARKET, name='Chợ bao bì Mây', emoji='📦', cutoff=23 * 60 + 30, at=(-240, -120), factor=0.8, short=12,
           note='Giá sỉ bao bì. Đặt trong ca, chiều mai có trước giờ vào ca. Đôi khi thiếu, đếm kỹ.'),
        _s(PARTNER, name='Kho vật tư Hạt Nắng', kind='rush', mins=(120, 240), runs=None,
           note='Giá niêm yết, xe tải nhỏ giao trong 2–4 giờ. Quá giờ tan ca thì để sáng mai.'),
        EXPRESS,
    ],
    'homestay': [
        _s(MARKET, name='Chợ sáng Mây', items=['bread', 'egg', 'milk', 'water', 'coffee', 'noodles', 'snack'],
           note='Đồ ăn sáng và minibar giá chợ. Đặt trước 17:00, sáng mai có trước giờ khách dậy. Hay thiếu vài món.'),
        PARTNER, EXPRESS,
        dict(id='textile', name='Xưởng dệt Hòa Mây', emoji='🧵', kind='days', days=(2, 3), at=(120, 300),
             factor=0.7, short=3, late=10, voice=V_MAKER, items=['linen', 'towel', 'soap_kit'],
             note='Ga gối, khăn, bộ đồ tắm từ xưởng: rẻ nhất, 2–3 ngày mới giao. Đặt trước mùa đông khách.'),
    ],
    'pet_care': [
        _s(MARKET, id='wholesale', name='Kho sỉ thú cưng Mây', emoji='🐾', factor=0.82, short=12,
           items=['sh_normal', 'sh_puppy', 'towel', 'cotton', 'poop_bag', 'dog_food', 'cat_food', 'treat'],
           note='Giá sỉ cho tiệm. Đặt trước 17:00, sáng mai có trước giờ mở cửa. Thỉnh thoảng thiếu, đếm kỹ.'),
        PARTNER, EXPRESS,
        dict(id='import', name='Hàng nhập Nhật Mây', emoji='✈️', kind='days', days=(2, 3), at=(60, 240),
             factor=0.8, short=0, late=15, voice=V_FAR, items=['sh_sensitive', 'conditioner', 'styptic'],
             note='Sữa tắm da nhạy cảm, dầu xả, bột cầm máu hàng nhập: rẻ hơn đại lý, 2–3 ngày mới tới.'),
    ],
    'salon': [
        _s(MARKET, name='Chợ sỉ vật tư tóc', emoji='🧴', factor=0.85, short=15,
           items=['shampoo', 'conditioner', 'towel', 'foil', 'gloves', 'rt_colorsafe', 'rt_mask', 'rt_heat', 'rt_purple'],
           note='Dầu gội, khăn, găng, giấy bạc giá sỉ. Đặt trước 17:00, sáng mai có. Hay thiếu vài món.'),
        PARTNER, EXPRESS,
        dict(id='brand', name='Kho hãng màu nhuộm', emoji='✈️', kind='days', days=(2, 3), at=(60, 240),
             factor=0.75, short=0, late=12, voice=V_FAR,
             items=['dye_3_0', 'dye_4_6', 'dye_5_0', 'dye_6_1', 'dye_7_3', 'dye_8_1', 'dev_10', 'dev_20', 'dev_30',
                    'dev_40', 'bleach', 'toner_silver', 'toner_beige', 'keratin'],
             note='Thuốc nhuộm, oxy, toner, keratin chính hãng từ kho hãng: rẻ nhất, 2–3 ngày. Đặt trước khi hết tuýp.'),
    ],
}
ALL_SUPPLIERS = {}
for _list in [DEFAULT_SUPPLIERS, *SUPPLIERS.values()]:
    for _x in _list:
        ALL_SUPPLIERS.setdefault(_x['id'], _x)


def suppliers(career: str) -> list[dict]:
    return SUPPLIERS.get(career, DEFAULT_SUPPLIERS)


def supplier(career: str, sid: str) -> dict | None:
    """A supplier this career can order from (None if it cannot)."""
    return next((x for x in suppliers(career) if x['id'] == sid), None)


def _known(career: str, sid: str) -> dict:
    """Supplier of an existing order: the career's own, or an older shared one."""
    return supplier(career, sid) or SUPPLIER_INDEX.get(sid) or ALL_SUPPLIERS.get(sid) or PARTNER


def sells(sup: dict, item_id: str) -> bool:
    return sup.get('items') is None or item_id in sup['items']


def _window_label(sup: dict, career: str) -> str:
    op = hours(career)[0]
    k = sup['kind']
    if k == 'rush':
        a, b = sup['mins']
        return f'{a}–{b} phút' if b < 90 else f'{a // 60}–{b // 60} giờ'
    if k == 'runs':
        return 'Hai chuyến/ngày · ' + ' & '.join(hm(r[1]) for r in sup['runs'])
    if k == 'next':
        return f'{_part(op + sup["at"][0]).capitalize()} mai · đặt trước {hm(sup["cutoff"])}'
    return f'{sup["days"][0]}–{sup["days"][1]} ngày'


def _lead_turns(sup: dict) -> int:
    """Rough wait in turns, kept only for older clients that still read `lead`."""
    k = sup['kind']
    if k == 'rush':
        return math.ceil(sup['mins'][1] / STEP)
    return {'runs': 6, 'next': 18}.get(k, 36 * sup.get('days', (1, 1))[0])


def _static(sup: dict, career: str | None = None) -> dict:
    v = {k: v for k, v in sup.items() if k not in ('runs', 'mins', 'at', 'days', 'cutoff')}
    v.update(kind=sup['kind'], window=_window_label(sup, career or ''), lead=_lead_turns(sup),
             items=list(sup['items']) if sup.get('items') is not None else None, fresh=sup.get('fresh', 0))
    return v


def _promise(sup: dict, career: str, now: int) -> tuple[int, int]:
    """The window [lo, hi] (absolute minutes) promised to an order placed at `now`."""
    op = hours(career)[0]
    day, minute = divmod(now, DAY_MIN)
    k = sup['kind']
    if k == 'rush':
        lo, hi = now + sup['mins'][0], now + sup['mins'][1]
    elif k == 'runs':
        run = next((r for r in sup['runs'] if minute < r[0]), None)
        d = day if run else day + 1
        run = run or sup['runs'][0]
        lo, hi = d * DAY_MIN + run[1], d * DAY_MIN + run[2]
    elif k == 'next':
        d = day + (1 if minute < sup['cutoff'] else 2)
        lo, hi = d * DAY_MIN + op + sup['at'][0], d * DAY_MIN + op + sup['at'][1]
    else:
        lo = (day + sup['days'][0]) * DAY_MIN + op + sup['at'][0]
        hi = (day + sup['days'][1]) * DAY_MIN + op + sup['at'][1]
    lo, hi = _r5(lo), _r5(hi)
    cl = hours(career)[1]
    if k == 'rush' and hi > day * DAY_MIN + cl:
        # Nobody is at the counter after closing: the courier drops it before the next opening.
        lo = hi = (day + 1) * DAY_MIN + op - EARLY
    elif hi % DAY_MIN > cl and hi // DAY_MIN == lo // DAY_MIN:
        lo = hi = _after_hours(hi, career)
    return lo, hi


def quote(sup: dict, career: str, now: int) -> dict:
    """What the supplier promises for an order placed at `now`, in plain words."""
    lo, hi = _promise(sup, career, now)
    k = sup['kind']
    if k == 'days':
        d0, d1 = (now // DAY_MIN) + sup['days'][0], (now // DAY_MIN) + sup['days'][1]
        label = f'{sup["days"][0]}–{sup["days"][1]} ngày · ngày {d0}–{d1}'
        return dict(label=label, eta_label=f'Ngày {d0}–{d1}', lo=lo, hi=hi, day=d0, time=hm(hours(career)[0] + sup['at'][0]))
    mid = _r5((lo + hi) / 2)
    if k == 'rush' and mid // DAY_MIN == now // DAY_MIN:
        a, b = sup['mins']
        label = f'{a}–{b} phút · tới ~{hm(mid)}' if b < 90 else f'{a // 60}–{b // 60} giờ · tới ~{hm(mid)}'
    else:
        label = when(mid, now, approx=True, quote=True)
    return dict(label=label, eta_label=when(mid, now, approx=True), lo=lo, hi=hi, day=mid // DAY_MIN, time=hm(mid))


def _schedule(sup: dict, career: str, now: int, seed: str) -> dict:
    """Pick the real arrival inside the promised window; sometimes late, never lost."""
    rnd = random.Random(seed)
    lo, hi = _promise(sup, career, now)
    if sup['kind'] == 'days':
        # The order is promised one concrete day inside the supplier's range.
        op = hours(career)[0]
        d = now // DAY_MIN + rnd.randint(*sup['days'])
        lo, hi = _r5(d * DAY_MIN + op + sup['at'][0]), _r5(d * DAY_MIN + op + sup['at'][1])
    at = min(hi, max(lo, _r5(rnd.randint(lo, hi))))
    late = None
    if rnd.randrange(100) < sup.get('late', 0):
        k = sup['kind']
        extra = DAY_MIN if k == 'days' else rnd.randint(15, 30) if k == 'rush' else rnd.randint(60, 120)
        at = _after_hours(_r5(hi + extra), career)
        late = sup['voice'].get('late') or 'Xe giao tới trễ hơn hẹn.'
    return dict(placed=now, lo=lo, hi=hi, at=max(at, hi + 5) if late else at, late=late)


# ---------------------------------------------------------------- catalogue and lots
def _spec(career: str) -> dict | None:
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    return mod.SPEC.get('inventory') if mod else None


def catalogue(career: str) -> list[dict]:
    spec = _spec(career)
    return spec['items'] if spec else []


def item(career: str, item_id: str) -> dict:
    from .engine import need
    found = next((x for x in catalogue(career) if x['id'] == item_id), None)
    need(found, 'Không có mặt hàng này trong kho của nghề.')
    return found


def capacity(career: str) -> int:
    spec = _spec(career)
    return spec.get('capacity', 40) if spec else 0


def initial(career: str) -> dict | None:
    spec = _spec(career)
    if not spec:
        return None
    lots = []
    for i, x in enumerate(spec['items']):
        qty = x.get('start', 8 if x.get('unlock', 1) <= 1 else 0)
        if qty:
            lots.append(dict(id=f'opening-{x["id"]}', item=x['id'], qty=qty, unit_cost=0,
                             expires=_life(x), received=1, supplier='opening'))
    return dict(lots=lots, orders=[], supplier_ratings={}, seq=0, day_bought=0)


def _life(x: dict) -> int:
    # Non-perishable goods get a long, finite game-day horizon.
    return x.get('life') or 999


def inv(c: dict) -> dict:
    from .engine import need
    x = c.get('ext', {}).get('inv')
    need(x is not None, 'Nghề này không dùng kho nguyên liệu.')
    return x


def count(c: dict, item_id: str) -> int:
    x = c.get('ext', {}).get('inv')
    if not x:
        return 0
    return sum(l['qty'] for l in x['lots'] if l['item'] == item_id and l['expires'] >= c['day'])


def take(c: dict, item_id: str, qty: int = 1) -> int:
    from .engine import need
    x = inv(c)
    name = item_name(item_id)
    need(count(c, item_id) >= qty, f'Hết {name}. Mở Kho để nhập thêm nhé.')
    cost = 0
    for lot in sorted((l for l in x['lots'] if l['item'] == item_id and l['expires'] >= c['day'] and l['qty'] > 0),
                      key=lambda l: (l['expires'], l['received'])):
        used = min(qty, lot['qty'])
        lot['qty'] -= used
        qty -= used
        cost += used * lot['unit_cost']
        if not qty:
            break
    x['lots'] = [l for l in x['lots'] if l['qty'] > 0]
    return cost


def add_lot(c: dict, item_id: str, qty: int, unit_cost: int, life_left: int, supplier: str) -> dict:
    x = inv(c)
    x['seq'] += 1
    lot = dict(id=f'lot-{x["seq"]}', item=item_id, qty=qty, unit_cost=unit_cost,
               expires=c['day'] + max(1, life_left) - 1, received=c['day'], supplier=supplier)
    x['lots'].append(lot)
    return lot


def item_name(item_id: str) -> str:
    from .careers import PLUGINS
    for mod in PLUGINS.values():
        for x in (mod.SPEC.get('inventory') or {}).get('items', []):
            if x['id'] == item_id:
                return x['name']
    return item_id


def _in_transit(x: dict, item_id: str) -> int:
    return sum(o['qty'] for o in x['orders'] if o['item'] == item_id and o['status'] == 'in_transit')


def _trim_orders(x: dict, limit: int = 40) -> None:
    """Keep the order book short without ever dropping a paid order still on
    the way: only the oldest received orders are forgotten."""
    extra = len(x['orders']) - limit
    if extra <= 0:
        return
    drop = set()
    for o in x['orders']:
        if len(drop) >= extra:
            break
        if o['status'] == 'received':
            drop.add(id(o))
    x['orders'] = [o for o in x['orders'] if id(o) not in drop]


# ---------------------------------------------------------------- old saves
def _upgrade_orders(x: dict, c: dict, career: str) -> None:
    """Orders from before clock deliveries carry `ready` (a turn). Turn the
    turns still to wait into shop minutes from now."""
    now = None
    for o in x.get('orders') or []:
        if not isinstance(o, dict) or 'ready' not in o or 'at' in o or type(o['ready']) is not int:
            continue
        if now is None:
            now = clock(c, career)['abs']
        ready = o.pop('ready')
        left = max(0, ready - c['turn']) if o.get('status') == 'in_transit' else 0
        at = _after_hours(now + left * STEP, career) if left else now
        o.update(placed=now, lo=at, hi=at, at=at, late=None)


def migrate(s: dict) -> None:
    """Engine hook for migrate_state (optional; everything also upgrades lazily)."""
    for cid, c in (s.get('careers') or {}).items():
        x = (c.get('ext') or {}).get('inv') if isinstance(c, dict) else None
        if isinstance(x, dict) and isinstance(c.get('day'), int) and isinstance(c.get('turn'), int):
            _upgrade_orders(x, c, cid)


def on_open(s: dict, c: dict, career: str) -> None:
    """Engine hook for start_day (optional): remember the opening turn."""
    x = c.get('ext', {}).get('inv')
    if x is not None:
        x['opened'] = dict(day=c['day'], turn=c['turn'])


def _anchor(x: dict, c: dict) -> None:
    if c.get('open') and (x.get('opened') or {}).get('day') != c['day']:
        t0 = _turn0(c)
        x['opened'] = dict(day=c['day'], turn=min(c['turn'], t0 if t0 is not None else max(0, c['turn'] - 1)))


# ---------------------------------------------------------------- orders
def _eta(o: dict, now: int, c: dict, career: str, clk: dict) -> dict:
    """Public ETA of an order; the real arrival and a delay stay hidden until due."""
    ready = o['status'] == 'in_transit' and now >= o['at']
    late_due = bool(o.get('late')) and now >= o['hi']
    target = o['at'] if (ready or late_due or o['status'] != 'in_transit') else _r5((o['lo'] + o['hi']) / 2)
    op = hours(career)[0]
    same = o['lo'] // DAY_MIN == o['hi'] // DAY_MIN
    if o['lo'] == o['hi']:
        window = hm(o['lo']) if o['lo'] // DAY_MIN == now // DAY_MIN else f'ngày {o["lo"] // DAY_MIN} · {hm(o["lo"])}'
    elif same:
        window = f'{hm(o["lo"])}–{hm(o["hi"])}' + ('' if o['lo'] // DAY_MIN == now // DAY_MIN else f' · ngày {o["lo"] // DAY_MIN}')
    else:
        window = f'ngày {o["lo"] // DAY_MIN}–{o["hi"] // DAY_MIN}'
    left = target - now
    tday, tmin = divmod(target, DAY_MIN)
    diff = tday - now // DAY_MIN
    if o['status'] != 'in_transit':
        left_label = ''
    elif ready:
        left_label = 'Đã tới'
    elif diff <= 0:
        left_label = f'còn {_duration(left)}'
    elif diff == 1 and tmin <= op:
        left_label = 'có ngay khi mở cửa sáng mai' if clk['is_open'] else 'có ngay khi mở cửa'
    elif diff == 1:
        left_label = 'ngày mai'
    else:
        left_label = f'còn {diff} ngày'
    span = max(1, target - o['placed'])
    arrives_turn = None
    if not ready and o['status'] == 'in_transit' and clk['is_open'] and diff <= 0 and tmin <= clk['close']:
        arrives_turn = c['turn'] + math.ceil(left / STEP)
    return dict(eta_label=when(target, now, approx=not (ready or late_due)), window=window,
                arrives_day=tday, arrives_time=hm(tmin), arrives_turn=arrives_turn, left_label=left_label,
                left_min=max(0, left), progress=1.0 if ready else round(max(0.0, min(1.0, (now - o['placed']) / span)), 3),
                late_note=o['late'] if late_due and o['status'] == 'in_transit' else None)


def action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    """inv_order / inv_receive / inv_wait / inv_claim / inv_rate / inv_discard."""
    from . import engine as e
    need = e.need
    x = inv(c)
    _upgrade_orders(x, c, career)
    _anchor(x, c)
    level = 1 + c['xp'] // 90
    if name == 'inv_order':
        it = item(career, p.get('item'))
        qty = e.integer(p.get('qty'), 1, 30)
        sup = supplier(career, p.get('supplier', 'partner'))
        need(sup, 'Nhà cung cấp không tồn tại.')
        need(sells(sup, it['id']), f'{sup["name"]} không bán {it["name"]}. Chọn nhà cung cấp khác nhé.')
        need(it.get('unlock', 1) <= level, f'Mở khóa {it["name"]} ở cấp {it.get("unlock", 1)}.')
        need(p.get('confirm') is True, 'Xác nhận đơn nhập và số tiền trước nhé.')
        cap = capacity(career)
        need(count(c, it['id']) + _in_transit(x, it['id']) + qty <= cap,
             f'Kho chứa tối đa {cap} phần mỗi loại (tính cả hàng đang giao).')
        need(len([o for o in x['orders'] if o['status'] == 'in_transit']) < 8, 'Đang có nhiều đơn chờ giao. Nhận bớt rồi đặt tiếp nhé.')
        cost = max(1, math.ceil(it['cost'] * qty * sup['factor']))
        x['seq'] += 1
        oid = f'po-{x["seq"]}'
        e.money(s, c, -cost, f'Nhập {qty} {it.get("unit", "phần")} {it["name"]} · {sup["name"]}', oid, category='stock')
        roll = (c['day'] * 37 + x['seq'] * 11 + sum(map(ord, it['id']))) % 100
        short = min(qty - 1, 1 + roll % 3) if qty > 1 and roll < sup['short'] else 0
        clk = clock(c, career)
        when_ = _schedule(sup, career, clk['abs'], f'{career}:{c["day"]}:{x["seq"]}:{it["id"]}:{sup["id"]}')
        o = dict(id=oid, item=it['id'], qty=qty, actual=qty - short, supplier=sup['id'], cost=cost,
                 unit_cost=math.ceil(it['cost'] * sup['factor']), status='in_transit', day=c['day'],
                 claimed=False, rating=None, reply=None, **when_)
        x['orders'].append(o)
        _trim_orders(x)
        x['day_bought'] += cost
        e.metric(c, 'purchases')
        eta = _eta(o, clk['abs'], c, career, clk)
        promise = eta['window'] if o['lo'] != o['hi'] else eta['arrives_time']
        return dict(message=f'Đã đặt {qty} {it.get("unit", "phần")} {it["name"]} · {cost} xu. {sup["name"]} giao '
                            f'{eta["eta_label"][0].lower() + eta["eta_label"][1:]} ({promise}); đếm rồi mới nhập kho.',
                    eta=dict(eta, order=oid))
    if name == 'inv_wait':
        need(c.get('open'), 'Tiệm đang đóng cửa. Mở cửa ngày mới, hàng tới trước giờ mở sẽ chờ sẵn ở cửa.')
        clk = clock(c, career)
        waiting = sorted((o for o in x['orders'] if o['status'] == 'in_transit'), key=lambda o: o['at'])
        here = [o for o in waiting if o['at'] <= clk['abs']]
        msg = f'⏳ {STEP} phút trôi qua, bây giờ {hm(clk["minute"])}.'
        if here:
            msg += f' Có {len(here)} thùng hàng đã tới, mở ra đếm nhé.'
        elif waiting:
            nxt = _eta(waiting[0], clk['abs'], c, career, clk)
            msg += f' {item_name(waiting[0]["item"])}: dự kiến {nxt["eta_label"]}.'
        return dict(message=msg)
    order = next((o for o in x['orders'] if o['id'] == p.get('order')), None)
    if name == 'inv_receive':
        need(order and order['status'] == 'in_transit', 'Đơn đã nhận hoặc không tồn tại.')
        # The engine has already counted this action's own 20 minutes; what is at
        # the door is what had arrived before it, matching public()'s ready_now.
        door = clock(c, career, turn=c['turn'] - 1)
        if door['abs'] < order['at']:
            eta = _eta(order, door['abs'], c, career, door)
            need(False, f'Hàng chưa tới. Dự kiến {eta["eta_label"]} — làm việc khác trong lúc chờ nhé.')
        counted = e.integer(p.get('count'), 0, 60)
        need(counted == order['actual'], 'Số đếm chưa khớp số hàng thực có trong thùng. Đếm lại nhé.')
        it = item(career, order['item'])
        # Stock can grow after ordering (market buys, returns, gifts); say so
        # plainly instead of failing on the generic capacity check.
        room = capacity(career) - count(c, it['id'])
        need(order['actual'] <= room, f'Kệ {it["name"]} chỉ còn chỗ cho {max(0, room)} {it.get("unit", "phần")}. '
             'Bán hoặc bỏ bớt lô cũ rồi nhận thùng này nhé.')
        sup = _known(career, order['supplier'])
        if order['actual']:
            life = _life(it) + (sup.get('fresh', 0) if it.get('life') else 0)
            add_lot(c, it['id'], order['actual'], order['unit_cost'], life, order['supplier'])
        order['status'] = 'received'
        e.metric(c, 'restocked')
        e.log(s, c, 'stock', f'Kiểm nhận {order["actual"]}/{order["qty"]} {it["name"]} từ {sup["name"]}.', ref=order['id'])
        msg = f'Đã nhập kho {order["actual"]} {it.get("unit", "phần")} {it["name"]}.'
        if order['actual'] < order['qty']:
            msg += f' Thiếu {order["qty"] - order["actual"]} so với đơn — có thể khiếu nại nhà cung cấp.'
        return dict(message=msg)
    if name == 'inv_claim':
        need(order and order['status'] == 'received', 'Chỉ khiếu nại sau khi đã kiểm nhận.')
        need(order['actual'] < order['qty'] and not order['claimed'], 'Đơn này giao đủ hoặc đã được giải quyết.')
        # Refund the paid share of the missing units (rounded), never more than was paid.
        missing = order['qty'] - order['actual']
        refund = max(1, (2 * order['cost'] * missing + order['qty']) // (2 * order['qty']))
        order['claimed'] = True
        sup = _known(career, order['supplier'])
        e.money(s, c, refund, f'Hoàn tiền giao thiếu · {sup["name"]}', order['id'], category='refund')
        order['reply'] = sup['voice']['claim']
        return dict(message=f'{sup["name"]}: “{sup["voice"]["claim"]}” · +{refund} xu.')
    if name == 'inv_rate':
        need(order and order['status'] == 'received' and order['rating'] is None, 'Chỉ đánh giá một lần sau khi nhận hàng.')
        stars = e.integer(p.get('stars'), 1, 5)
        note = e.clean_text(p.get('note', ''), 200, 0)
        order['rating'] = stars
        order['note'] = note
        sup = _known(career, order['supplier'])
        order['reply'] = sup['voice']['good' if stars >= 4 else 'bad']
        rated = x['supplier_ratings'].setdefault(sup['id'], dict(total=0, count=0))
        rated['total'] += stars
        rated['count'] += 1
        e.metric(c, 'supplier_reviews')
        return dict(message=f'{sup["name"]} phản hồi: “{order["reply"]}”')
    if name == 'inv_discard':
        lot = next((l for l in x['lots'] if l['id'] == p.get('lot')), None)
        need(lot, 'Lô hàng không còn trong kho.')
        need(p.get('confirm') is True, 'Xác nhận bỏ lô này; giá trị được ghi là hao hụt.')
        value = lot['qty'] * lot['unit_cost']
        c['life']['day_waste'] += value
        c['life']['waste'] = (c['life']['waste'] + [dict(day=c['day'], item=lot['item'], qty=min(60, lot['qty']), value=value, reason='Bỏ lô không đạt')])[-120:]
        x['lots'] = [l for l in x['lots'] if l['id'] != lot['id']]
        return dict(message='Đã bỏ lô hàng và ghi hao hụt.')
    raise e.GameError('Thao tác kho chưa được hỗ trợ.')


def on_close(s: dict, c: dict, career: str) -> int:
    """Expire lots at the end of the game day. Returns wasted value."""
    x = c.get('ext', {}).get('inv')
    if not x:
        return 0
    _upgrade_orders(x, c, career)
    wasted = 0
    keep = []
    for lot in x['lots']:
        if lot['expires'] <= c['day'] and lot['qty']:
            value = lot['qty'] * lot['unit_cost']
            wasted += value
            c['life']['waste'] = (c['life']['waste'] + [dict(day=c['day'], item=lot['item'], qty=min(60, lot['qty']), value=value, reason='Hết hạn sử dụng')])[-120:]
        else:
            keep.append(lot)
    x['lots'] = keep[-300:]
    x['day_bought'] = 0
    c['life']['day_waste'] += wasted
    return wasted


def public(c: dict, career: str) -> dict | None:
    x = c.get('ext', {}).get('inv')
    if x is None:
        return None
    v = tree_copy(x)
    _upgrade_orders(v, c, career)
    level = 1 + c['xp'] // 90
    v['stock'] = {i['id']: count(c, i['id']) for i in catalogue(career)}
    v['expiring'] = {i['id']: sum(l['qty'] for l in x['lots'] if l['item'] == i['id'] and l['expires'] == c['day']) for i in catalogue(career)}
    v['locked'] = [i['id'] for i in catalogue(career) if i.get('unlock', 1) > level]
    v['capacity'] = capacity(career)
    # Derived numbers for the stock screen: what is on the way, room left on
    # each shelf and how many game days the oldest lot still has.
    v['arriving'] = {i['id']: _in_transit(x, i['id']) for i in catalogue(career)}
    v['room'] = {k: max(0, v['capacity'] - v['stock'][k] - v['arriving'][k]) for k in v['stock']}
    v['expiring_soon'] = {i['id']: sum(l['qty'] for l in x['lots'] if l['item'] == i['id'] and c['day'] <= l['expires'] <= c['day'] + 1)
                          for i in catalogue(career)}
    v['days_left'] = {}
    for l in x['lots']:
        if l['expires'] >= c['day'] and l['qty'] > 0:
            left = l['expires'] - c['day'] + 1
            v['days_left'][l['item']] = min(left, v['days_left'].get(l['item'], left))
    clk = clock(c, career)
    now = clk['abs']
    v['clock'] = dict(clk, time=hm(clk['minute']), open_time=hm(clk['open']), close_time=hm(clk['close']),
                      label=(f'Bây giờ {hm(clk["minute"])}' + (' · đã tới giờ đóng cửa' if clk['minute'] >= clk['close'] else ''))
                      if clk['is_open'] else f'Đã đóng cửa · mở lại {hm(clk["open"])} ngày {c["day"]}')
    for o in v['orders']:
        if 'at' not in o:
            continue
        o.update(_eta(o, now, c, career, clk))
        o['ready_now'] = o['status'] == 'in_transit' and now >= o['at']
        # The count is discovered by opening the box, as with v0.2 shipments;
        # the real arrival and a delay are discovered when they happen.
        o['count_hint'] = o['actual'] if o['ready_now'] else None
        if o['status'] == 'in_transit':
            o.pop('actual', None)
            if not o['ready_now']:
                o.pop('at', None)
            o.pop('late', None)
    ratings = x['supplier_ratings']
    placing = clock(c, career, c['turn'] + 1)['abs']  # an order ticks the clock once before it is placed
    v['suppliers'] = [dict(_static(sp, career), quote=quote(sp, career, placing),
                           rating=(round(ratings[sp['id']]['total'] / ratings[sp['id']]['count'], 1)
                                   if ratings.get(sp['id'], {}).get('count') else None)) for sp in suppliers(career)]
    return v


def validate(c: dict, career: str) -> None:
    from .engine import need, integer, clean_text
    x = c['ext'].get('inv')
    spec = _spec(career)
    if not spec:
        need(x is None, 'Nghề này không có kho nguyên liệu.')
        return
    need(isinstance(x, dict) and all(k in x for k in ('lots', 'orders', 'supplier_ratings', 'seq', 'day_bought')), 'Kho thiếu dữ liệu.')
    integer(x['seq'], 0, 10**9)
    integer(x['day_bought'], 0, 10**9)
    if 'opened' in x:
        need(isinstance(x['opened'], dict) and set(x['opened']) == {'day', 'turn'}, 'Giờ mở ca của kho sai.')
        integer(x['opened']['day'], 1, 10**7)
        integer(x['opened']['turn'], 0, c['turn'])
    ids = {i['id'] for i in spec['items']}
    need(isinstance(x['lots'], list) and len(x['lots']) <= 300, 'Danh sách lô không hợp lệ.')
    for lot in x['lots']:
        need(isinstance(lot, dict) and lot.get('item') in ids, 'Lô hàng lạ.')
        clean_text(lot.get('id'), 80)
        integer(lot.get('qty'), 0, 999)
        integer(lot.get('unit_cost'), 0, 10000)
        integer(lot.get('expires'), 0, 10**7)
        integer(lot.get('received'), 1, 10**7)
    need(len({l['id'] for l in x['lots']}) == len(x['lots']), 'Trùng mã lô.')
    cap = capacity(career)
    for i in ids:
        need(count(c, i) <= cap, 'Tồn vượt sức chứa.')
    known = {sp['id'] for sp in suppliers(career)} | set(SUPPLIER_INDEX)
    new_keys = ('placed', 'lo', 'hi', 'at', 'late')
    need(isinstance(x['orders'], list) and len(x['orders']) <= 40, 'Đơn nhập không hợp lệ.')
    for o in x['orders']:
        need(isinstance(o, dict) and o.get('item') in ids and o.get('supplier') in known, 'Đơn nhập sai.')
        integer(o.get('qty'), 1, 30)
        integer(o.get('actual'), 0, o['qty'])
        integer(o.get('cost'), 0, 10**6)
        integer(o.get('unit_cost'), 0, 10000)
        if 'ready' in o:
            # A save from before clock deliveries: upgraded on its next use.
            integer(o['ready'], 0, 10**9)
            need(not any(k in o for k in new_keys), 'Đơn nhập trộn hai kiểu giờ giao.')
        else:
            placed = integer(o.get('placed'), 0, 10**9)
            lo = integer(o.get('lo'), placed, 10**9)
            hi = integer(o.get('hi'), lo, lo + 4 * DAY_MIN)
            at = integer(o.get('at'), lo, hi + 2 * DAY_MIN)
            late = o.get('late')
            need(late is None or (isinstance(late, str) and 0 < len(late) <= 300), 'Ghi chú giao trễ sai.')
            need((late is not None) == (at > hi), 'Giờ giao trễ không khớp.')
        need(o.get('status') in ('in_transit', 'received'), 'Trạng thái đơn nhập sai.')
        need(type(o.get('claimed')) is bool and o.get('rating') in (None, 1, 2, 3, 4, 5), 'Đánh giá đơn nhập sai.')
    need(isinstance(x['supplier_ratings'], dict) and all(k in ALL_SUPPLIERS for k in x['supplier_ratings']), 'Đánh giá nhà cung cấp sai.')


def content() -> dict:
    from .careers import PLUGINS
    stocked = {cid: mod.SPEC['inventory']['items'] for cid, mod in PLUGINS.items() if mod.SPEC.get('inventory')}
    return dict(suppliers=[_static(sp) for sp in DEFAULT_SUPPLIERS], items=stocked, step=STEP,
                by_career={cid: [_static(sp, cid) for sp in suppliers(cid)] for cid in stocked},
                hours={cid: dict(open=hm(hours(cid)[0]), close=hm(hours(cid)[1])) for cid in stocked})
