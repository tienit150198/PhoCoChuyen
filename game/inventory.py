"""Stock, suppliers and purchase orders for plugin trade careers (v0.4).

Money is paid when an order is placed. Goods enter stock only after the player
counts the delivery. A short delivery can be claimed back once; every supplier
order can be rated, and the supplier answers in its own voice. Lots expire by
game day at closing time: the value is recorded as waste, never charged twice.

Deliveries run on the shop's clock, not on beats: every supplier promises a
window in time of day (15–30 minutes, the next of four van runs, the market's
afternoon run or tomorrow before opening, one or two days for special goods).
`clock()` turns the career's turn counter into that time of day. See
docs/superpowers/specs/2026-09-29-supplier-lead-times.md (§8: waits halved).

Đơn gộp (merged orders): every order pays its supplier's shipping fee once (free from
`free_from` xu of goods), and a line of `bulk` units or more gets the wholesale price. A
per-supplier draft (`inv['cart']`) collects lines; `inv_order_cart` places them as ONE order:
one payment and one row in the books, one van, one arrival, one crate. Each line is stored as
an ordinary order sharing a `group` id, so counting, claims and older code keep working line by
line. Suppliers push back (minimum order, one line out of stock, a merged load that rides a
later run) and can be asked for a discount on a big order: they answer from hidden traits,
deterministic from the career, the supplier, the day and the order id. Orders placed before
this carry no `ship` key: they paid no fee.
"""
from __future__ import annotations
import copy
import math
import random
import zlib
from .jsoncopy import tree_copy
from . import archive as ar

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
    'tra_da': (6 * 60 + 30, 19 * 60 + 30),  # the tea stall opens with the morning traffic
    'fruit': (6 * 60, 18 * 60),         # the market's morning crowd
    'garbage': (17 * 60, 23 * 60),      # the evening rubbish round
    'drain': (7 * 60 + 30, 19 * 60 + 30),
    'homemaker': (6 * 60 + 30, 18 * 60 + 30),   # the market at dawn, dinner cooked before going home
    'ice_cream': (11 * 60, 21 * 60),    # after lunch, the school run at 16:30, the evening walk
    'com': (6 * 60, 19 * 60),           # cơm tấm for breakfast, rice plates at noon, boxes till evening
    'nail': (9 * 60, 21 * 60),          # office lunch breaks, evening and weekend bookings
    'pho': (5 * 60 + 30, 14 * 60),      # breakfast from 5:30, the pot runs low after lunch
    'pagoda': (5 * 60, 19 * 60),        # the gate opens after morning chanting, closes after the evening one
    'photobooth': (11 * 60, 22 * 60),   # after lunch, the school run at 17:00, the night market
    'naucom': (6 * 60 + 30, 19 * 60),   # the market at dawn, the family's dinner on the table before going home
}
EARLY = 30  # goods due after closing wait at the door this many minutes before the next opening
# How much later than its window a late delivery comes (minutes), by supplier kind; a
# supplier may set its own `delay`. A supplier without one (a table from before the
# halved waits, e.g. milk tea's own) keeps the old delays: see _schedule.
DELAY = {'rush': (10, 15), 'runs': (30, 60), 'next': (30, 60), 'days': (240, 360)}
RUN_WORD = {1: 'Một', 2: 'Hai', 3: 'Ba', 4: 'Bốn', 5: 'Năm', 6: 'Sáu'}


def hours(career: str) -> tuple[int, int]:
    return HOURS.get(career, DEFAULT_HOURS)


def day_hours(c: dict, career: str) -> tuple[int, int]:
    """Today's hours: the career's own, closing later on an extended evening (dayclock.LATE_DAYS)."""
    op, cl = hours(career)
    from . import dayclock
    late = dayclock.late_close(c, career)
    return op, max(cl, late or cl)


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
    op, cl = day_hours(c, career)
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
    'Sáng ngày kia 07:15' / 'Còn 3 ngày · 10:30' (past: 'Ngày 7 · 10:30')."""
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
    # Further out: counted from today, not as a shop-day number (the HUD counts life days in the story).
    return f'Còn {diff} ngày · {time}'


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
                 late='Xe giao của Hạt Nắng kẹt ở cầu Mây, bên em báo trễ chừng nửa tiếng tới một tiếng ạ.')
V_EXPRESS = dict(good='Mây Xanh luôn sẵn sàng khi quán cần gấp!',
                 bad='Xin lỗi quý khách, tài xế sẽ được nhắc lại quy trình.',
                 claim='Đã hoàn tiền phần thiếu ngay.',
                 late='Tài xế phải vòng tránh đoạn đường ngập, tới trễ chừng mười lăm phút ạ.')
V_FAR = dict(good='Kho ghi nhận, cảm ơn quý khách đã tin hàng đi xa.',
             bad='Hàng đi đường dài, bên em sẽ đóng thùng kỹ hơn.',
             claim='Kho đã lập phiếu bù cho phần thiếu.',
             late='Xe tuyến kẹt ở trạm nên về trễ mấy tiếng, kho xin lỗi quý khách.')
V_MAKER = dict(good='Cảm ơn tiệm, mẻ sau vẫn làm kỹ như vậy!',
               bad='Xưởng xin nhận góp ý, mẻ sau kiểm lại từng túi.',
               claim='Xưởng gửi bù phần thiếu vào đơn sau, trả tiền trước nha.',
               late='Mẻ hôm nay ra lò muộn, xưởng giao trễ hơn hẹn ạ.')
V_GARDEN = dict(good='Nhà vườn cảm ơn nha, hoa mới cắt sáng nay đó!',
                bad='Đường đèo xóc quá, lần sau vườn lót thêm giấy báo.',
                claim='Cành gãy thì vườn bù tiền liền, đừng lo.',
                late='Xe từ Đà Lạt xuống bị sương mù đèo Mây, tới trễ chừng một tiếng.')
V_COOP = dict(good='Hợp tác xã cảm ơn bà con, vụ sau lại ủng hộ nha!',
              bad='Kho hợp tác xã sẽ cân lại kỹ hơn.',
              claim='Thiếu bao nào hợp tác xã trả lại tiền bao đó.',
              late='Xe công nông của hợp tác xã hỏng giữa đường, tới trễ một chút.')

# `next`: `day_run` (cut-off, from, to) is the same-day run for morning orders; any
# later order rides the night run to the next morning (`cutoff` None = until closing).
MARKET = dict(id='market', name='Chợ đầu mối Mây', emoji='🧺', kind='next', cutoff=None, at=(-75, -35),
              day_run=(13 * 60, 15 * 60, 16 * 60), delay=DELAY['next'],
              factor=0.85, short=22, late=10,
              note='Rẻ nhất. Đặt trước 13:00, hàng tới chiều nay; đặt sau, hàng tới sáng mai trước giờ mở cửa. '
                   'Thỉnh thoảng giao thiếu, cần đếm kỹ.',
              voice=V_MARKET)
# Four van runs a day, (cut-off, from, to): the goods come about an hour after each cut-off.
PARTNER = dict(id='partner', name='Nhà phân phối Hạt Nắng', emoji='🚚', kind='runs',
               runs=((9 * 60, 10 * 60, 10 * 60 + 30), (12 * 60, 13 * 60, 13 * 60 + 30),
                     (15 * 60, 16 * 60, 16 * 60 + 30), (18 * 60, 19 * 60, 19 * 60 + 30)),
               delay=DELAY['runs'], factor=1.0, short=6, late=8,
               note='Giá niêm yết, có phiếu giao rõ ràng. Xe chạy bốn chuyến: đặt trước 09:00, 12:00, 15:00 hoặc 18:00, '
                    'hàng tới sau đó khoảng một tiếng.',
               voice=V_PARTNER)
EXPRESS = dict(id='express', name='Giao hỏa tốc Mây Xanh', emoji='⚡', kind='rush', mins=(15, 30), delay=DELAY['rush'],
               factor=1.35, short=0, late=12,
               note='Đắt nhất nhưng tới trong 15–30 phút. Dùng khi cháy hàng giữa ca.', voice=V_EXPRESS)
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
        dict(id='import', name='Kho hàng nhập Kim Mây', emoji='✈️', kind='days', days=(1, 2), at=(30, 90),
             factor=0.72, short=4, late=15, voice=V_FAR,
             items=['pack_kimchi', 'pack_tomyum', 'pack_blackbean', 'pack_cheese', 'kimchi_side', 'cheese_slice',
                    'ricecake', 'fishball', 'sausage', 'beef'],
             note='Gói nước dùng, phô mai, bánh gạo, bò Mỹ nhập thẳng: rẻ hơn hẳn nhưng 1–2 ngày mới tới. Đặt sớm cho cả tuần.'),
    ],
    'cafe_bakery': [
        _s(MARKET, items=['milk', 'oat', 'condensed', 'cream', 'flour', 'butter', 'egg', 'sugar', 'almond']),
        PARTNER, EXPRESS,
        dict(id='roaster', name='Xưởng rang Đồi Mây', emoji='☕', kind='next', cutoff=None, at=(90, 120),
             day_run=(11 * 60, 14 * 60, 15 * 60),
             factor=0.8, short=3, late=8, voice=V_MAKER, items=['beans_house', 'beans_robusta', 'beans_decaf'],
             note='Rang theo đơn hai mẻ mỗi ngày. Đặt trước 11:00, hạt mới rang tới chiều nay; đặt sau, sáng mai có. '
                  'Rẻ và thơm hơn.'),
    ],
    'florist': [
        _s(MARKET, name='Chợ hoa đêm Sương Mai', emoji='💐', day_run=(15 * 60, 16 * 60, 17 * 60), factor=0.85, short=25,
           items=['rose_red', 'rose_pink', 'rose_white', 'rose_yellow', 'lily', 'mum_white', 'sunflower', 'carnation',
                  'orchid', 'babys_breath', 'eucalyptus'],
           note='Chợ hoa họp đêm, ban ngày còn sạp sỉ: đặt trước 15:00, hoa tới chiều nay; đặt sau, hoa tới sáng mai '
                'trước giờ mở cửa. Rẻ, nhưng hay gãy hoặc thiếu vài cành.',
           voice=dict(V_MARKET, good='Cảm ơn tiệm nha, đêm mai chị lựa bó đẹp nhất!',
                      late='Chợ hoa đêm nay đông quá, xe chị ra muộn một chút.')),
        dict(id='dalat', name='Nhà vườn Đà Lạt', emoji='🌄', kind='next', cutoff=None, at=(30, 75),
             day_run=(9 * 60, 15 * 60, 16 * 60 + 30),
             factor=0.7, short=10, late=15, fresh=1, voice=V_GARDEN,
             items=['rose_red', 'rose_pink', 'rose_white', 'rose_yellow', 'lily', 'mum_white', 'carnation',
                    'babys_breath', 'eucalyptus'],
             note='Hoa cắt tại vườn: đặt trước 09:00, vườn gửi xe khách, chiều nay tới; đặt sau, hoa đi xe đêm, sáng mai tới. '
                  'Rẻ nhất và tươi thêm 1 ngày, nhưng xe đèo hay trễ.'),
        PARTNER, _s(EXPRESS, factor=1.4),
    ],
    'grocery': [
        _s(MARKET, items=['egg', 'milk', 'bread', 'greens', 'tomato']),
        PARTNER, EXPRESS,
        dict(id='wholesale', name='Tổng kho sỉ Mây Xanh', emoji='🏭', kind='days', days=(1, 1), at=(60, 120),
             factor=0.8, short=5, late=10, voice=V_FAR,
             items=['rice', 'noodle', 'fishsauce', 'oil', 'soap', 'snack', 'soda', 'beer'],
             note='Hàng khô, nước, bia theo thùng: giá sỉ, sáng mai giao. Hợp để trữ hàng không hạn.'),
    ],
    'repair': [
        _s(MARKET, name='Chợ linh kiện Mây', emoji='🔌', factor=0.8, short=15,
           items=['screen_c', 'battery_c', 'port', 'cap_c', 'fuse', 'terminal', 'tube', 'rimtape', 'chain', 'brake',
                  'hp_battery', 'driver', 'solder', 'paste', 'oil', 'shrink', 'screen_u', 'battery_u', 'motor_u', 'ipa'],
           note='Linh kiện tương thích và đồ tháo máy giá mềm. Đặt trước 13:00, chiều nay có; đặt sau, sáng mai có. '
                'Đôi khi thiếu, đếm kỹ.',
           voice=dict(V_MARKET, good='Cảm ơn anh chị thợ, mai sạp để hàng tốt!',
                      late='Sạp đóng hàng muộn, xe ôm chở trễ chút nha.')),
        PARTNER, EXPRESS,
        dict(id='genuine', name='Kho linh kiện chính hãng', emoji='✈️', kind='days', days=(1, 2), at=(30, 120),
             factor=0.85, short=0, late=15, voice=V_FAR,
             items=['screen_g', 'battery_g', 'cap_g', 'fan_motor', 'heater', 'ssd'],
             note='Hàng hãng có tem bảo hành, gửi từ kho miền: 1–2 ngày. Rẻ hơn đại lý nhưng phải hẹn khách trước.'),
    ],
    'farm': [
        dict(id='coop', name='HTX Nông nghiệp Mây', emoji='🌾', kind='next', cutoff=None, at=(30, 60),
             day_run=(11 * 60, 13 * 60, 14 * 60),
             factor=0.8, short=10, late=8, voice=V_COOP,
             items=['seed_muong', 'seed_lettuce', 'seed_tomato', 'seed_cucumber', 'seed_herbs', 'compost', 'npk',
                    'bio_spray', 'chem_spray', 'feed', 'bag', 'carton', 'egg_tray'],
             note='Giá xã viên. Đặt trước 11:00, xe hợp tác xã chở tới chiều nay; đặt sau, sáng mai có. '
                  'Thỉnh thoảng thiếu một bao.'),
        _s(PARTNER, name='Đại lý vật tư Hạt Nắng'),
        _s(EXPRESS, name='Xe ba gác hỏa tốc', note='Chở gấp trong 15–30 phút, đắt. Dùng khi gà sắp hết cám.'),
        dict(id='nursery', name='Trại giống Đồng Xanh', emoji='🌱', kind='days', days=(1, 2), at=(45, 120),
             factor=0.7, short=0, late=12, voice=V_MAKER, items=['seed_tomato', 'seed_cucumber', 'seed_herbs'],
             note='Cây giống ươm theo đơn: rẻ nhất nhưng 1–2 ngày mới có.'),
    ],
    'delivery': [
        _s(MARKET, name='Chợ bao bì Mây', emoji='📦', at=(-240, -120), day_run=(20 * 60, 21 * 60, 22 * 60),
           factor=0.8, short=12,
           note='Giá sỉ bao bì. Đặt trước 20:00, tối nay có; đặt sau, chiều mai có trước giờ vào ca. Đôi khi thiếu, đếm kỹ.'),
        _s(PARTNER, name='Kho vật tư Hạt Nắng', kind='rush', mins=(60, 120), runs=None, delay=DELAY['rush'],
           note='Giá niêm yết, xe tải nhỏ giao trong 1–2 giờ. Quá giờ tan ca thì hàng chờ sẵn trước ca mai.',
           voice=dict(V_PARTNER, late='Xe tải của kho kẹt ở cầu Mây, bên em báo trễ chừng mười lăm phút ạ.')),
        EXPRESS,
    ],
    'homestay': [
        _s(MARKET, name='Chợ sáng Mây', items=['bread', 'egg', 'milk', 'water', 'coffee', 'noodles', 'snack'],
           note='Đồ ăn sáng và minibar giá chợ. Đặt trước 13:00, chiều nay có; đặt sau, sáng mai có trước giờ khách dậy. '
                'Hay thiếu vài món.'),
        PARTNER, EXPRESS,
        dict(id='textile', name='Xưởng dệt Hòa Mây', emoji='🧵', kind='days', days=(1, 2), at=(60, 150),
             factor=0.7, short=3, late=10, voice=V_MAKER, items=['linen', 'towel', 'soap_kit'],
             note='Ga gối, khăn, bộ đồ tắm từ xưởng: rẻ nhất, 1–2 ngày mới giao. Đặt trước mùa đông khách.'),
    ],
    'pet_care': [
        _s(MARKET, id='wholesale', name='Kho sỉ thú cưng Mây', emoji='🐾', factor=0.82, short=12,
           items=['sh_normal', 'sh_puppy', 'towel', 'cotton', 'poop_bag', 'dog_food', 'cat_food', 'treat'],
           note='Giá sỉ cho tiệm. Đặt trước 13:00, chiều nay có; đặt sau, sáng mai có trước giờ mở cửa. '
                'Thỉnh thoảng thiếu, đếm kỹ.'),
        PARTNER, EXPRESS,
        dict(id='import', name='Hàng nhập Nhật Mây', emoji='✈️', kind='days', days=(1, 2), at=(30, 120),
             factor=0.8, short=0, late=15, voice=V_FAR, items=['sh_sensitive', 'conditioner', 'styptic'],
             note='Sữa tắm da nhạy cảm, dầu xả, bột cầm máu hàng nhập: rẻ hơn đại lý, 1–2 ngày mới tới.'),
    ],
    'salon': [
        _s(MARKET, name='Chợ sỉ vật tư tóc', emoji='🧴', factor=0.85, short=15,
           items=['shampoo', 'conditioner', 'towel', 'foil', 'gloves', 'rt_colorsafe', 'rt_mask', 'rt_heat', 'rt_purple'],
           note='Dầu gội, khăn, găng, giấy bạc giá sỉ. Đặt trước 13:00, chiều nay có; đặt sau, sáng mai có. '
                'Hay thiếu vài món.'),
        PARTNER, EXPRESS,
        dict(id='brand', name='Kho hãng màu nhuộm', emoji='✈️', kind='days', days=(1, 2), at=(30, 120),
             factor=0.75, short=0, late=12, voice=V_FAR,
             items=['dye_3_0', 'dye_4_6', 'dye_5_0', 'dye_6_1', 'dye_7_3', 'dye_8_1', 'dev_10', 'dev_20', 'dev_30',
                    'dev_40', 'bleach', 'toner_silver', 'toner_beige', 'keratin'],
             note='Thuốc nhuộm, oxy, toner, keratin chính hãng từ kho hãng: rẻ nhất, 1–2 ngày. Đặt trước khi hết tuýp.'),
    ],
}
# Shipping, wholesale tiers and push-back for every supplier (đơn gộp): by id, else by kind.
# ship: fee per order (xu); free_from: goods total (xu) that ships free; bulk: ((units, % off), …)
# per line; oos: chance (%) that one line of a merged order is out of stock; min_order: the
# smallest merged order (xu of goods) the supplier will run a van for.
TERMS = {
    'market': dict(ship=2, free_from=40, bulk=((10, 5), (20, 10)), oos=15, min_order=0),
    'partner': dict(ship=3, free_from=60, bulk=((10, 4), (20, 8)), oos=6, min_order=0),
    'express': dict(ship=5, free_from=120, bulk=((20, 3),), oos=4, min_order=0),
}
KIND_TERMS = {
    'next': dict(ship=2, free_from=40, bulk=((10, 5), (20, 10)), oos=10, min_order=0),
    'days': dict(ship=4, free_from=80, bulk=((10, 6), (20, 12)), oos=10, min_order=30),
    'runs': TERMS['partner'], 'rush': TERMS['express'],
}
ALL_SUPPLIERS = {}
for _list in [DEFAULT_SUPPLIERS, *SUPPLIERS.values()]:
    for _x in _list:
        _x.setdefault('delay', DELAY[_x['kind']])  # every supplier here runs on the halved waits
        for _k, _v in (TERMS.get(_x['id']) or KIND_TERMS[_x['kind']]).items():
            _x.setdefault(_k, _v)
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
    op, cl = hours(career)
    k = sup['kind']
    if k == 'rush':
        a, b = sup['mins']
        return f'{a}–{b} phút' if b < 90 else f'{a // 60}–{b // 60} giờ'
    if k == 'runs':
        times = [hm(r[1]) for r in sup['runs']]
        listed = ', '.join(times[:-1]) + ' & ' + times[-1] if len(times) > 1 else times[0]
        return f'{RUN_WORD.get(len(times), len(times))} chuyến/ngày · {listed}'
    if k == 'next':
        morning = f'{_part(op + sup["at"][0])} mai'
        cut, run = sup.get('cutoff'), sup.get('day_run')
        if run and run[0] > op:
            later = f', sau đó {morning}' if cut is None or cut >= cl else f', trước {hm(cut)} thì {morning}'
            return f'{_part(run[1]).capitalize()} nay nếu đặt trước {hm(run[0])}{later}'
        return morning.capitalize() + (f' · đặt trước {hm(cut)}' if cut is not None else '')
    a, b = sup['days']
    return f'{a} ngày' if a == b else f'{a}–{b} ngày'


def _lead_turns(sup: dict) -> int:
    """Rough wait in turns, kept only for older clients that still read `lead`."""
    k = sup['kind']
    if k == 'rush':
        return math.ceil(sup['mins'][1] / STEP)
    return {'runs': 3, 'next': 9}.get(k, 36 * sup.get('days', (1, 1))[0])


def _static(sup: dict, career: str | None = None) -> dict:
    v = {k: v for k, v in sup.items() if k not in ('runs', 'mins', 'at', 'days', 'cutoff', 'day_run', 'delay')}
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
        run, cut = sup.get('day_run'), sup.get('cutoff')
        if run and minute < run[0]:
            # Ordered before the same-day run leaves: here this afternoon.
            lo, hi = day * DAY_MIN + run[1], day * DAY_MIN + run[2]
        else:
            d = day + (1 if cut is None or minute < cut else 2)
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
        a, b = sup['days']
        d0, d1 = (now // DAY_MIN) + a, (now // DAY_MIN) + b
        days = f'ngày {d0}' if a == b else f'ngày {d0}–{d1}'
        label = f'{_window_label(sup, career)} · {days}'
        return dict(label=label, eta_label=days.capitalize(), lo=lo, hi=hi, day=d0, time=hm(hours(career)[0] + sup['at'][0]))
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
        # Same chance of a delay as before the waits were halved; the delay itself is halved too.
        k = sup['kind']
        if sup.get('delay'):
            extra = rnd.randint(*sup['delay'])
        else:  # a supplier table from before the halved waits keeps its old delays
            extra = DAY_MIN if k == 'days' else rnd.randint(15, 30) if k == 'rush' else rnd.randint(60, 120)
        at = _after_hours(_r5(hi + extra), career)
        late = sup['voice'].get('late') or 'Xe giao tới trễ hơn hẹn.'
    return dict(placed=now, lo=lo, hi=hi, at=max(at, hi + 5) if late else at, late=late)


# ---------------------------------------------------------------- prices, carts and haggling
CART_LINES = 8      # lines in one supplier's draft
FIT_LINES = 40      # lines one inv_cart `fit` call may list (the rest past CART_LINES stays out)
TRANSIT_LINES = 30  # order lines on the way at once (the order book keeps 40)
ASKS = (5, 10, 15)  # discounts a player can ask for on a big order (%)


def haggle_from(sup: dict) -> int:
    """A draft this big (xu of goods) is worth bargaining over: half the free-shipping line."""
    return max(1, sup.get('free_from', 0) // 2)


def _h(text: str) -> int:
    """A stable hash (Python's own hash() changes between processes)."""
    return zlib.crc32(text.encode('utf-8'))


def bulk_pct(sup: dict, qty: int) -> int:
    return max([p for n, p in sup.get('bulk') or () if qty >= n], default=0)


def line_price(it: dict, qty: int, sup: dict) -> dict:
    """One line: goods cost (wholesale tier applied), unit cost and the next tier to reach.
    `full` is the price every order paid before wholesale tiers; a tier takes its share off,
    rounded, and always at least 1 xu (public/js/v4/views.js lineQuote mirrors this)."""
    pct = bulk_pct(sup, qty)
    full = max(1, math.ceil(it['cost'] * qty * sup['factor']))
    off = max(1, (full * pct + 50) // 100) if pct else 0
    cost = max(1, full - off)
    unit = math.ceil(it['cost'] * sup['factor']) if not pct else max(1, -(-cost // qty))
    nxt = next(([n, p] for n, p in sorted(sup.get('bulk') or ()) if qty < n), None)
    return dict(cost=cost, unit_cost=unit, bulk=pct, full=full, next_tier=nxt)


def ship_fee(sup: dict, goods: int) -> int:
    return 0 if goods >= sup.get('free_from', 0) else sup.get('ship', 0)


def _spread(costs: list[int], off: int) -> list[int]:
    """Share an order-level discount over its lines (exactly `off` in total, biggest lines first)."""
    total = sum(costs)
    if not off or not total:
        return list(costs)
    shares = [c * off // total for c in costs]
    rest = off - sum(shares)
    for i in sorted(range(len(costs)), key=lambda i: -costs[i]):
        if not rest:
            break
        if shares[i] < costs[i]:
            shares[i] += 1
            rest -= 1
    return [c - s for c, s in zip(costs, shares)]


def _deal_ok(deal: dict | None, day: int, goods: int, honor: bool = False) -> bool:
    return bool(deal) and deal.get('day') == day and (honor or goods >= deal.get('sub', 0))


def cart_price(career: str, sup: dict, lines: list[dict], deal: dict | None, day: int, honor: bool = False) -> dict:
    """What a draft costs: lines at their wholesale tier, the haggled discount, the shipping fee."""
    rows = []
    for l in lines:
        it = item(career, l['item'])
        rows.append(dict(item=it['id'], qty=l['qty'], **line_price(it, l['qty'], sup)))
    goods = sum(r['cost'] for r in rows)
    ok = _deal_ok(deal, day, goods, honor)
    pct = deal['pct'] if ok else 0
    off = goods * pct // 100
    ship_base = ship_fee(sup, goods)
    ship = 0 if ok and deal.get('free_ship') else ship_base
    return dict(rows=rows, full=sum(r['full'] for r in rows), goods=goods, bulk_off=sum(r['full'] for r in rows) - goods,
                pct=pct, off=off, ship=ship, ship_base=ship_base, total=goods - off + ship, deal_ok=ok,
                deal_lost=bool(deal) and deal.get('day') == day and not ok and deal.get('mood') in ('ok', 'counter', 'ship'))


def _casual(sup: dict) -> bool:
    """Market stalls, gardens and small makers talk like people; distributors talk like a counter."""
    return sup['id'] == 'market' or sup['kind'] == 'next'


def _traits(career: str, sup: dict) -> dict:
    """Hidden, fixed per career and supplier: how much room there is to bargain and how touchy they are."""
    h = _h(f'trait:{career}:{sup["id"]}')
    base = 9 if sup['id'] == 'market' else 1 if sup['kind'] == 'rush' else 3 if sup['kind'] == 'runs' else 7 if sup['kind'] == 'days' else 6
    return dict(room=max(0, base + h % 4 - 1), touchy=(h >> 4) % 3 == 0,
                ship_instead=sup['id'] == 'partner' or (h >> 6) % 2 == 0)


HAGGLE_TALK = {
    True: dict(ok='Thôi được, lấy nhiều thì bớt {p}% cho em.', counter='{p}% thôi em ơi, bớt nữa là lỗ vốn.',
               ship='Giá sát lắm rồi, chở miễn phí cho em là được.', no='Bớt vậy lấy gì ăn em? Giá này là chót rồi.',
               sour='Trả giá kiểu này thì em qua sạp khác đi!'),
    False: dict(ok='Bên em áp dụng chiết khấu {p}% cho đơn này ạ.', counter='Bên em chỉ duyệt được {p}% thôi ạ, mong quý khách thông cảm.',
                ship='Giá niêm yết không giảm được ạ, bên em xin miễn phí giao cho đơn này.',
                no='Giá đã là giá niêm yết, bên em không giảm thêm được ạ.',
                sour='Yêu cầu đã được ghi nhận. Lần sau quý khách vui lòng đặt theo bảng giá.'),
}
RUSH_NO = 'Hỏa tốc tính theo cuốc xe, bên em không giảm ạ.'


def haggle(career: str, sup: dict, day: int, ask: int, goods: int) -> dict:
    """The supplier's answer to "bớt {ask}% nhé?" on `goods` xu: accept, counter, free shipping
    instead, or no (a touchy one says it rudely). Deterministic: same career, supplier, day and ask,
    same answer; a big order (twice the free-shipping line) gets two points more room."""
    t = _traits(career, sup)
    mood = _h(f'mood:{career}:{sup["id"]}:{day}') % 5 - 2
    room = max(0, t['room'] + mood + (2 if goods >= 2 * sup.get('free_from', 0) else 0))
    talk = HAGGLE_TALK[_casual(sup)]
    deal = dict(day=day, ask=ask, sub=goods, pct=0, free_ship=False)
    if ask <= room:
        deal.update(mood='ok', pct=ask)
    elif room >= 2 and ask <= 2 * room:
        deal.update(mood='counter', pct=room)
    elif t['ship_instead'] and ship_fee(sup, goods):
        deal.update(mood='ship', free_ship=True)
    else:
        deal.update(mood='sour' if t['touchy'] and ask >= 2 * max(1, room) else 'no')
    said = talk[deal['mood']].format(p=deal['pct'])
    if sup['kind'] == 'rush' and deal['mood'] in ('no', 'sour'):
        said = RUSH_NO
    deal['said'] = said
    return deal


def _merge_later(sup: dict, career: str, now: int) -> int | None:
    """A merged load that misses its van: the placing time whose promise is the next window."""
    day, minute = divmod(now, DAY_MIN)
    k = sup['kind']
    if k == 'runs':
        run = next((r for r in sup['runs'] if minute < r[0]), None)
        later = day * DAY_MIN + run[0] if run else (day + 1) * DAY_MIN + sup['runs'][0][0]
    elif k == 'next' and sup.get('day_run') and minute < sup['day_run'][0]:
        later = day * DAY_MIN + sup['day_run'][0]
    elif k == 'rush':
        later = now + 30
    else:
        return None
    return later if _promise(sup, career, later)[0] > _promise(sup, career, now)[0] else None


def cart_view(c: dict, career: str, x: dict) -> list[dict]:
    """The drafts for the stock room: lines, subtotal, wholesale savings, shipping, haggled
    discount, total, what the fund lacks, and what the supplier said."""
    out = []
    day = c['day']
    level = 1 + c['xp'] // 90
    placing = None
    for sid, cart in (x.get('cart') or {}).items():
        sup = supplier(career, sid)
        if not sup or not cart.get('lines'):
            continue
        live = [l for l in cart['lines'] if l.get('oos') != day]
        q = cart_price(career, sup, live, cart.get('deal'), day)
        rows = {r['item']: r for r in q['rows']}
        lines = []
        for l in cart['lines']:
            it = item(career, l['item'])
            r = rows.get(l['item']) or dict(line_price(it, l['qty'], sup), item=it['id'], qty=l['qty'])
            room = max(0, capacity(career) - count(c, it['id']) - _in_transit(x, it['id']))
            lines.append(dict(r, oos=l.get('oos') == day, room=room, locked=it.get('unlock', 1) > level))
        deal = cart.get('deal') if (cart.get('deal') or {}).get('day') == day else None
        asked = (x.get('haggle') or {}).get(sid) == day
        if placing is None:
            placing = clock(c, career, c['turn'] + 1)['abs']
        out.append(dict(supplier=sid, lines=lines, n=len(live), goods=q['goods'], full=q['full'], bulk_off=q['bulk_off'],
                        pct=q['pct'], off=q['off'], ship=q['ship'], ship_base=q['ship_base'], free_from=sup.get('free_from', 0),
                        to_free=max(0, sup.get('free_from', 0) - q['goods']) if q['ship_base'] else 0,
                        min_order=sup.get('min_order', 0), below_min=max(0, sup.get('min_order', 0) - q['goods']) if live else 0,
                        total=q['total'], short=max(0, q['total'] - c['money']),
                        deal=dict(deal, lost=q['deal_lost']) if deal else None,
                        can_haggle=bool(live) and not asked and q['goods'] >= haggle_from(sup),
                        haggle_from=haggle_from(sup), asked=asked, asks=list(ASKS),
                        quote=quote(sup, career, placing)))
    return out


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


TRANSIT_CAP = 8  # orders on the way at once (inv_order); the stock screens show it before ordering


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


def _refund(order: dict) -> int:
    """What a claim gives back: the paid share of the missing units (rounded), never more than was paid."""
    missing = order['qty'] - order['actual']
    return max(1, (2 * order['cost'] * missing + order['qty']) // (2 * order['qty']))


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
        need(_shipments(x) < TRANSIT_CAP, 'Đang có nhiều đơn chờ giao. Nhận bớt rồi đặt tiếp nhé.')
        need(_transit_lines(x) < TRANSIT_LINES, 'Đang có nhiều hàng chờ giao. Nhận bớt rồi đặt tiếp nhé.')
        price = line_price(it, qty, sup)
        cost, fee = price['cost'], ship_fee(sup, price['cost'])
        x['seq'] += 1
        oid = f'po-{x["seq"]}'
        e.money(s, c, -(cost + fee), f'Nhập {qty} {it.get("unit", "phần")} {it["name"]} · {sup["name"]}' + (f' · ship {fee} xu' if fee else ''),
                oid, category='stock')
        roll = (c['day'] * 37 + x['seq'] * 11 + sum(map(ord, it['id']))) % 100
        short = min(qty - 1, 1 + roll % 3) if qty > 1 and roll < sup['short'] else 0
        clk = clock(c, career)
        when_ = _schedule(sup, career, clk['abs'], f'{career}:{c["day"]}:{x["seq"]}:{it["id"]}:{sup["id"]}')
        o = dict(id=oid, item=it['id'], qty=qty, actual=qty - short, supplier=sup['id'], cost=cost,
                 unit_cost=price['unit_cost'], status='in_transit', day=c['day'],
                 claimed=False, rating=None, reply=None, ship=fee, **when_)
        x['orders'].append(o)
        _trim_orders(x)
        x['day_bought'] += cost + fee
        e.metric(c, 'purchases')
        eta = _eta(o, clk['abs'], c, career, clk)
        promise = eta['window'] if o['lo'] != o['hi'] else eta['arrives_time']
        paid = f'{cost + fee} xu' + (f' (ship {fee} xu)' if fee else '')
        return dict(message=f'Đã đặt {qty} {it.get("unit", "phần")} {it["name"]} · {paid}. {sup["name"]} giao '
                            f'{eta["eta_label"][0].lower() + eta["eta_label"][1:]} ({promise}); đếm rồi mới nhập kho.',
                    eta=dict(eta, order=oid))
    if name == 'inv_cart':
        return _cart_edit(c, career, x, p, level)
    if name == 'inv_haggle':
        sup = supplier(career, p.get('supplier'))
        need(sup, 'Nhà cung cấp không tồn tại.')
        ask = e.integer(p.get('pct'), 1, 50)
        need(ask in ASKS, 'Chọn mức xin bớt có sẵn nhé.')
        cart = (x.get('cart') or {}).get(sup['id'])
        live = [l for l in (cart or {}).get('lines', []) if l.get('oos') != c['day']]
        need(live, 'Thêm hàng vào đơn trước rồi mới trả giá nhé.')
        asked = x.setdefault('haggle', {})
        need(asked.get(sup['id']) != c['day'], f'{sup["name"]} đã trả lời hôm nay rồi. Mai hỏi lại nhé.')
        goods = cart_price(career, sup, live, None, c['day'])['goods']
        need(goods >= haggle_from(sup), f'Đơn từ {haggle_from(sup)} xu mới xin bớt được (đang {goods} xu).')
        deal = haggle(career, sup, c['day'], ask, goods)
        for k in [k for k, d in asked.items() if d != c['day']]:
            del asked[k]  # one answer per supplier per day: yesterday's marks go
        asked[sup['id']] = c['day']
        cart['deal'] = deal
        got = f' · bớt {deal["pct"]}%' if deal['pct'] else ' · miễn ship' if deal['free_ship'] else ''
        return dict(message=f'{sup["name"]}: “{deal["said"]}”{got}', deal=deal)
    if name == 'inv_order_cart':
        return _cart_place(s, c, career, x, p, level)
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
    if p.get('group') is not None and name in ('inv_receive', 'inv_claim', 'inv_rate'):
        return _group_action(s, c, career, x, name, p)
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
            # Said where the claim is (player feedback: "khiếu nại thiếu hoa ở đâu?"): the stock room shows
            # the button right under its status strip; `short` lets a client point at it.
            missing, refund = order['qty'] - order['actual'], _refund(order)
            msg += (f' Thiếu {missing} {it.get("unit", "phần")} so với đơn: bấm “Khiếu nại phần thiếu” '
                    f'ngay trong kho để được hoàn {refund} xu.')
            return dict(message=msg, short=dict(order=order['id'], missing=missing, refund=refund))
        return dict(message=msg)
    if name == 'inv_claim':
        need(order and order['status'] == 'received', 'Chỉ khiếu nại sau khi đã kiểm nhận.')
        need(order['actual'] < order['qty'] and not order['claimed'], 'Đơn này giao đủ hoặc đã được giải quyết.')
        refund = _refund(order)
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
        c['life']['waste'] = ar.last(c['life']['waste'] + [dict(day=c['day'], item=lot['item'], qty=min(60, lot['qty']), value=value, reason='Bỏ lô không đạt')], 120, 'life.waste', c)
        x['lots'] = [l for l in x['lots'] if l['id'] != lot['id']]
        return dict(message='Đã bỏ lô hàng và ghi hao hụt.')
    raise e.GameError('Thao tác kho chưa được hỗ trợ.')


def _shipments(x: dict) -> int:
    """Deliveries on the way: a merged order is one van however many lines it has."""
    return len({o.get('group') or o['id'] for o in x['orders'] if o['status'] == 'in_transit'})


def _transit_lines(x: dict) -> int:
    return sum(1 for o in x['orders'] if o['status'] == 'in_transit')


def _cart_edit(c: dict, career: str, x: dict, p: dict, level: int) -> dict:
    """inv_cart: add lines to a supplier's draft (op add, `item`+`qty` or `lines`; `fit` trims
    to the room left), change a quantity (set; 0 removes), remove a line, or clear the draft."""
    from . import engine as e
    need = e.need
    sup = supplier(career, p.get('supplier'))
    need(sup, 'Nhà cung cấp không tồn tại.')
    op = p.get('op', 'add')
    need(op in ('add', 'set', 'remove', 'clear'), 'Thao tác đơn gộp không hợp lệ.')
    carts = x.setdefault('cart', {})
    cart = carts.setdefault(sup['id'], dict(lines=[]))
    lines = cart['lines']
    cap = capacity(career)

    def room(it: dict) -> int:
        return max(0, cap - count(c, it['id']) - _in_transit(x, it['id']))

    msg = ''
    if op == 'clear':
        lines.clear()
        msg = f'Đã bỏ đơn {sup["name"]}.'
    elif op == 'add':
        want = p.get('lines') if p.get('lines') is not None else [dict(item=p.get('item'), qty=p.get('qty'))]
        fit = p.get('fit') is True
        # `fit` (the stock room's "Gộp N món" step) may list more than one draft holds: a shop with many
        # items low (the nail shop has 20) sent them all, and the whole batch was refused. The lines past
        # CART_LINES now stay out like any other `fit` overflow; the list is still bounded.
        need(isinstance(want, list) and 0 < len(want) <= (FIT_LINES if fit else CART_LINES), 'Danh sách hàng không hợp lệ.')
        added = 0
        left_out = 0  # `fit`: new lines past CART_LINES stay out (the message says so) instead of refusing the batch
        for w in want:
            need(isinstance(w, dict), 'Danh sách hàng không hợp lệ.')
            it = item(career, w.get('item'))
            qty = e.integer(w.get('qty'), 1, 30)
            need(sells(sup, it['id']), f'{sup["name"]} không bán {it["name"]}. Chọn nhà cung cấp khác nhé.')
            need(it.get('unlock', 1) <= level, f'Mở khóa {it["name"]} ở cấp {it.get("unlock", 1)}.')
            row = next((l for l in lines if l['item'] == it['id']), None)
            have = row['qty'] if row else 0
            if fit:
                qty = min(qty, 30 - have, room(it) - have)
                if qty <= 0:
                    continue
            new = have + qty
            need(new <= 30, f'Mỗi món tối đa 30 {it.get("unit", "phần")} một đơn.')
            need(new <= room(it), f'Kệ {it["name"]} chỉ còn chỗ cho {room(it)} {it.get("unit", "phần")} (tính cả hàng đang giao).')
            if row:
                row['qty'] = new
            else:
                if fit and len(lines) >= CART_LINES:
                    left_out += 1
                    continue
                need(len(lines) < CART_LINES, f'Một đơn tối đa {CART_LINES} món. Đặt đơn này trước nhé.')
                lines.append(dict(item=it['id'], qty=new))
            added += 1
        need(added or not left_out, f'Đơn {sup["name"]} đủ {CART_LINES} món. Đặt đơn này trước rồi thêm tiếp nhé.')
        need(added, 'Kệ đã đủ hàng, không cần nhập thêm.')
        msg = f'Đã thêm vào đơn {sup["name"]} · {len(lines)} món.'
        if left_out:
            msg += f' Đơn đủ {CART_LINES} món: còn {left_out} món chưa thêm, đặt đơn này rồi thêm tiếp.'
    else:
        it = item(career, p.get('item'))
        row = next((l for l in lines if l['item'] == it['id']), None)
        need(row, 'Món này chưa có trong đơn.')
        qty = 0 if op == 'remove' else e.integer(p.get('qty'), 0, 30)
        if qty:
            need(qty <= room(it), f'Kệ {it["name"]} chỉ còn chỗ cho {room(it)} {it.get("unit", "phần")} (tính cả hàng đang giao).')
            row['qty'] = qty
            msg = f'{it["name"]}: {qty} {it.get("unit", "phần")}.'
        else:
            lines.remove(row)
            msg = f'Đã bỏ {it["name"]} khỏi đơn.'
    if not lines:
        carts.pop(sup['id'], None)
    if not carts:
        x.pop('cart', None)
    return dict(message=msg)


def _cart_place(s: dict, c: dict, career: str, x: dict, p: dict, level: int) -> dict:
    """inv_order_cart: the supplier's draft as ONE order (one payment, one van, one crate)."""
    from . import engine as e
    need = e.need
    sup = supplier(career, p.get('supplier'))
    need(sup, 'Nhà cung cấp không tồn tại.')
    need(p.get('confirm') is True, 'Xác nhận đơn gộp và số tiền trước nhé.')
    cart = (x.get('cart') or {}).get(sup['id'])
    need(cart and cart.get('lines'), 'Đơn đang trống. Thêm hàng vào đơn trước nhé.')
    day = c['day']
    held = [l for l in cart['lines'] if l.get('oos') == day]
    lines = [l for l in cart['lines'] if l.get('oos') != day]
    need(lines, f'Hôm nay {sup["name"]} hết {", ".join(item(career, l["item"])["name"] for l in held)}. Bỏ khỏi đơn hoặc chọn nơi khác nhé.')
    cap = capacity(career)
    for l in lines:
        it = item(career, l['item'])
        need(sells(sup, it['id']), f'{sup["name"]} không bán {it["name"]}. Bỏ khỏi đơn nhé.')
        need(it.get('unlock', 1) <= level, f'Mở khóa {it["name"]} ở cấp {it.get("unlock", 1)}.')
        need(count(c, it['id']) + _in_transit(x, it['id']) + l['qty'] <= cap,
             f'Kệ {it["name"]} không đủ chỗ cho {l["qty"]} {it.get("unit", "phần")} (tính cả hàng đang giao). Bớt lại nhé.')
    need(_shipments(x) < TRANSIT_CAP, 'Đang có nhiều đơn chờ giao. Nhận bớt rồi đặt tiếp nhé.')
    need(_transit_lines(x) + len(lines) <= TRANSIT_LINES, 'Đang có nhiều hàng chờ giao. Nhận bớt rồi đặt tiếp nhé.')
    deal = cart.get('deal')
    q = cart_price(career, sup, lines, deal, day)
    if sup.get('min_order') and q['goods'] < sup['min_order']:
        said = (f'Đơn dưới {sup["min_order"]} xu chị không chạy xe đâu em.' if _casual(sup)
                else f'Bên em chỉ nhận đơn gộp từ {sup["min_order"]} xu ạ.')
        need(False, f'{sup["name"]}: “{said}” Thêm hàng hoặc đặt lẻ từng món nhé.')
    need(c['money'] >= q['total'], f'Thiếu {q["total"] - c["money"]} xu để đặt đơn này.')
    x['seq'] += 1
    gid = f'po-{x["seq"]}'
    h = _h(f'{career}:{gid}:{day}:{sup["id"]}')
    notes = []
    # Push-back 1: one line is out of stock today. It stays in the draft, nothing is charged for it,
    # and the haggled price and the shipping quoted still hold (the supplier's fault, not yours).
    gone = None
    if len(lines) >= 2 and h % 100 < sup.get('oos', 0):
        gone = lines[(h // 100) % len(lines)]
        lines = [l for l in lines if l is not gone]
        q2 = cart_price(career, sup, lines, deal, day, honor=q['deal_ok'])
        q = dict(q2, ship=min(q['ship'], q2['ship']))
        q['total'] = q['goods'] - q['off'] + q['ship']
        name = item(career, gone['item'])['name']
        notes.append(f'{sup["name"]}: “' + (f'Hết {name.lower()} rồi em, giao trước mấy món kia nha.' if _casual(sup)
                                            else f'Kho tạm hết {name.lower()}, bên em giao trước phần còn lại ạ.') +
                     f'” Không tính tiền {name.lower()}.')
    clk = clock(c, career)
    now = clk['abs']
    placing = now
    # Push-back 2: a big merged load is packed separately and rides a later van.
    if len(lines) >= 3 and (h // 7) % 100 < 30:
        later = _merge_later(sup, career, now)
        if later is not None:
            placing = later
    when_ = _schedule(sup, career, placing, f'{career}:{day}:{x["seq"]}:{gid}:{sup["id"]}')
    when_['placed'] = now
    if placing != now:
        label = when(_r5((when_['lo'] + when_['hi']) / 2), now, approx=True, quote=True)
        label = label[0].lower() + label[1:]
        notes.append(f'{sup["name"]}: “' + (f'Gộp {len(lines)} món soạn không kịp chuyến, {label} mới tới nha em.' if _casual(sup)
                                            else f'Đơn gộp {len(lines)} món cần soạn riêng, {label} mới giao được ạ.') + '”')
    paid = f'{q["total"]} xu' + (f' (ship {q["ship"]} xu)' if q['ship'] else ' (miễn ship)')
    e.money(s, c, -q['total'], f'Nhập gộp {len(lines)} món · {sup["name"]}' + (f' · ship {q["ship"]} xu' if q['ship'] else ''),
            gid, category='stock')
    costs = _spread([r['cost'] for r in q['rows']], q['off'])
    first = None
    for k, (l, r, cost) in enumerate(zip(lines, q['rows'], costs)):
        roll = (day * 37 + x['seq'] * 11 + sum(map(ord, l['item'])) + k * 17) % 100
        short = min(l['qty'] - 1, 1 + roll % 3) if l['qty'] > 1 and roll < sup['short'] else 0
        o = dict(id=f'{gid}-{k + 1}', group=gid, item=l['item'], qty=l['qty'], actual=l['qty'] - short, supplier=sup['id'],
                 cost=cost, unit_cost=r['unit_cost'], status='in_transit', day=day, claimed=False, rating=None, reply=None,
                 **when_)
        if first is None:
            o.update(ship=q['ship'], off=q['off'])
            first = o
        x['orders'].append(o)
    _trim_orders(x)
    x['day_bought'] += q['total']
    e.metric(c, 'purchases')
    # The draft keeps only what could not ship today.
    keep = held + ([dict(gone, oos=day)] if gone else [])
    if keep:
        x['cart'][sup['id']] = dict(lines=[dict(item=l['item'], qty=l['qty'], oos=day) for l in keep])
    else:
        x['cart'].pop(sup['id'], None)
        if not x['cart']:
            x.pop('cart', None)
    eta = _eta(first, now, c, career, clk)
    promise = eta['window'] if first['lo'] != first['hi'] else eta['arrives_time']
    msg = f'Đã đặt đơn gộp {len(lines)} món · {paid}.'
    if placing == now:
        msg += f' {sup["name"]} giao một chuyến {eta["eta_label"][0].lower() + eta["eta_label"][1:]} ({promise}).'
    return dict(message=' '.join([msg, *notes]), eta=dict(eta, order=first['id'], group=gid),
                oos=gone['item'] if gone else None, later=placing != now)


def _group_action(s: dict, c: dict, career: str, x: dict, name: str, p: dict) -> dict:
    """inv_receive / inv_claim / inv_rate on a whole merged order (`group`)."""
    from . import engine as e
    need = e.need
    gid = p.get('group')
    lines = [o for o in x['orders'] if isinstance(gid, str) and o.get('group') == gid]
    need(lines, 'Đơn không tồn tại.')
    sup = _known(career, lines[0]['supplier'])
    if name == 'inv_receive':
        lines = [o for o in lines if o['status'] == 'in_transit']
        need(lines, 'Đơn đã nhận hoặc không tồn tại.')
        door = clock(c, career, turn=c['turn'] - 1)
        if door['abs'] < min(o['at'] for o in lines):
            eta = _eta(lines[0], door['abs'], c, career, door)
            need(False, f'Hàng chưa tới. Dự kiến {eta["eta_label"]} — làm việc khác trong lúc chờ nhé.')
        counts = p.get('counts')
        need(isinstance(counts, dict), 'Đếm từng món trong thùng trước nhé.')
        for o in lines:
            it = item(career, o['item'])
            counted = e.integer(counts.get(o['id']), 0, 60)
            need(counted == o['actual'], f'Số đếm {it["name"]} chưa khớp số hàng thực có trong thùng. Đếm lại nhé.')
            room = capacity(career) - count(c, it['id'])
            need(o['actual'] <= room, f'Kệ {it["name"]} chỉ còn chỗ cho {max(0, room)} {it.get("unit", "phần")}. '
                 'Bán hoặc bỏ bớt lô cũ rồi nhận thùng này nhé.')
        got, short = [], []
        for o in lines:
            it = item(career, o['item'])
            if o['actual']:
                life = _life(it) + (sup.get('fresh', 0) if it.get('life') else 0)
                add_lot(c, it['id'], o['actual'], o['unit_cost'], life, o['supplier'])
            o['status'] = 'received'
            e.metric(c, 'restocked')
            got.append(f'{o["actual"]}/{o["qty"]} {it["name"]}')
            if o['actual'] < o['qty']:
                short.append(dict(order=o['id'], item=it['id'], missing=o['qty'] - o['actual'], refund=_refund(o)))
        e.log(s, c, 'stock', f'Kiểm nhận đơn gộp từ {sup["name"]}: {", ".join(got)}.', ref=gid)
        msg = f'Đã nhập kho cả thùng: {", ".join(got)}.'
        if short:
            refund = sum(v['refund'] for v in short)
            msg += f' Giao thiếu {len(short)} món: bấm “Khiếu nại phần thiếu” ngay trong kho để được hoàn {refund} xu.'
            return dict(message=msg, short=dict(group=gid, order=short[0]['order'], lines=short,
                                                missing=sum(v['missing'] for v in short), refund=refund))
        return dict(message=msg)
    if name == 'inv_claim':
        due = [o for o in lines if o['status'] == 'received' and o['actual'] < o['qty'] and not o['claimed']]
        need(due, 'Đơn này giao đủ hoặc đã được giải quyết.')
        refund = sum(_refund(o) for o in due)
        for o in due:
            o['claimed'] = True
            o['reply'] = sup['voice']['claim']
        e.money(s, c, refund, f'Hoàn tiền giao thiếu · {sup["name"]}', gid, category='refund')
        return dict(message=f'{sup["name"]}: “{sup["voice"]["claim"]}” · +{refund} xu.')
    need(all(o['status'] == 'received' for o in lines) and all(o['rating'] is None for o in lines),
         'Chỉ đánh giá một lần sau khi nhận hàng.')
    stars = e.integer(p.get('stars'), 1, 5)
    note = e.clean_text(p.get('note', ''), 200, 0)
    reply = sup['voice']['good' if stars >= 4 else 'bad']
    for o in lines:
        o.update(rating=stars, note=note, reply=reply)
    rated = x['supplier_ratings'].setdefault(sup['id'], dict(total=0, count=0))
    rated['total'] += stars
    rated['count'] += 1
    e.metric(c, 'supplier_reviews')
    return dict(message=f'{sup["name"]} phản hồi: “{reply}”')


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
            c['life']['waste'] = ar.last(c['life']['waste'] + [dict(day=c['day'], item=lot['item'], qty=min(60, lot['qty']), value=value, reason='Hết hạn sử dụng')], 120, 'life.waste', c)
        else:
            keep.append(lot)
    x['lots'] = ar.last(keep, 300, 'stock.lots', c)
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
    v['transit_cap'], v['transit_lines'] = TRANSIT_CAP, TRANSIT_LINES
    v['cart_lines'] = CART_LINES  # lines in one draft (inv_cart refuses one more)
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
    # Drafts (đơn gộp), priced by the server; the raw draft and the haggle marks stay inside.
    v.pop('cart', None)
    v.pop('haggle', None)
    v['carts'] = cart_view(c, career, x)
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
        if 'group' in o:  # a line of a merged order (đơn gộp)
            need(isinstance(o['group'], str) and o['group'].startswith('po-') and len(o['group']) <= 40
                 and str(o.get('id', '')).startswith(o['group'] + '-'), 'Đơn gộp sai mã.')
        for k in ('ship', 'off'):  # shipping paid and the haggled discount (orders from 0.9.20 on)
            if k in o:
                integer(o[k], 0, 10**6)
        need(type(o.get('claimed')) is bool and o.get('rating') in (None, 1, 2, 3, 4, 5), 'Đánh giá đơn nhập sai.')
    need(isinstance(x['supplier_ratings'], dict) and all(k in ALL_SUPPLIERS for k in x['supplier_ratings']), 'Đánh giá nhà cung cấp sai.')
    if 'cart' in x:
        sold = {sp['id'] for sp in suppliers(career)}
        need(isinstance(x['cart'], dict) and len(x['cart']) <= len(sold), 'Đơn gộp không hợp lệ.')
        for sid, cart in x['cart'].items():
            need(sid in sold and isinstance(cart, dict) and set(cart) <= {'lines', 'deal'}, 'Đơn gộp không hợp lệ.')
            lines = cart.get('lines')
            need(isinstance(lines, list) and 0 < len(lines) <= CART_LINES, 'Đơn gộp không hợp lệ.')
            for l in lines:
                need(isinstance(l, dict) and set(l) <= {'item', 'qty', 'oos'} and l.get('item') in ids, 'Dòng đơn gộp sai.')
                integer(l.get('qty'), 1, 30)
                if 'oos' in l:
                    integer(l['oos'], 1, 10**7)
            need(len({l['item'] for l in lines}) == len(lines), 'Đơn gộp trùng món.')
            deal = cart.get('deal')
            if deal is not None:
                need(isinstance(deal, dict) and set(deal) == {'day', 'ask', 'sub', 'pct', 'free_ship', 'mood', 'said'}, 'Giá thương lượng sai.')
                integer(deal['day'], 1, 10**7)
                integer(deal['ask'], 1, 50)
                integer(deal['sub'], 0, 10**6)
                integer(deal['pct'], 0, 50)
                need(type(deal['free_ship']) is bool and deal['mood'] in ('ok', 'counter', 'ship', 'no', 'sour'), 'Giá thương lượng sai.')
                clean_text(deal['said'], 300)
    if 'haggle' in x:
        need(isinstance(x['haggle'], dict) and len(x['haggle']) <= 12 and all(k in ALL_SUPPLIERS for k in x['haggle']), 'Trả giá sai.')
        for d in x['haggle'].values():
            integer(d, 1, 10**7)


def content() -> dict:
    from .careers import PLUGINS
    stocked = {cid: mod.SPEC['inventory']['items'] for cid, mod in PLUGINS.items() if mod.SPEC.get('inventory')}
    return dict(suppliers=[_static(sp) for sp in DEFAULT_SUPPLIERS], items=stocked, step=STEP,
                by_career={cid: [_static(sp, cid) for sp in suppliers(cid)] for cid in stocked},
                hours={cid: dict(open=hm(hours(cid)[0]), close=hm(hours(cid)[1])) for cid in stocked})
