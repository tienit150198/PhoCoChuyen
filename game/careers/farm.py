"""Nông Trại Đồi Gió — a small vegetable and chicken farm (plugin career).

Real work of the job:
* Six plots persist across tasks and days (stored in ext data). Crops grow
  every game turn ("nhịp") depending on soil moisture, weeds and pests, and
  overnight. The day's weather sets evaporation: sun dries the soil, rain can
  waterlog it (dig a drainage channel), so watering is a decision, not a chore.
* Plant from seed stock, water, weed, scout for pests (pests stay hidden until
  you walk the plot), treat with a biological spray or a chemical pesticide,
  fertilise with compost or chemical NPK. Chemical inputs make the crop cycle
  non-organic and start a pre-harvest interval (thời gian cách ly): produce
  harvested before it ends is unsafe and can never be sold.
* Harvest at the right ripeness: young → small grade-B yield, ripe → grade A,
  old → grade B, rotten → only compost. Produce goes to the cold room as dated
  lots with a short life. Feed the hens and collect eggs every day.
* Orders: restaurant contracts (grade A, carton, sometimes organic) and market
  walk-ins (any grade, paper bag). Pack lots into the crate, choose an honest
  label and deliver. Organic labels carry a QR code linked to the farm diary:
  a false organic claim is refused on the spot. Short deliveries are accepted
  and paid for what arrived, with a lower review.

v0.5:
* Seasons (4 days each): the season favours some crops (+1 growth per beat,
  cheaper at the wholesale market because everyone has them) and punishes
  others (−1 growth, dearer). Winter nights halve overnight growth. Weather is
  drawn from the season's own mix; later days bring more extremes.
* Chợ đầu mối: a daily price board (deterministic per day, a price shock per
  day from day 3, a trader's rumour about tomorrow that is right 4 times in 5).
  `fa_sell` sells surplus cold-room lots at ~60% of the shop price; every few
  units sold knock the price down and the market only takes so much per crop.
* HTX pledges: a surprise may ask the farm to supply N units of grade A before
  closing at a fixed good price (`fa_pledge`); a shortfall is fined per unit.
* Surprises (kit desk): pump failure, storm, pest wave, organic audit (and its
  return visit), HTX pledge, fox in the hen house, goats, seed pedlar, heat
  wave, beekeeper (no chemical spray while bees are near), trader buy-out.
* `fa_hen` restocks a lost hen. Order generator 2 adds new orders and larger
  quantities with the day; old saves keep their tasks (kit legacy band).

Care loop (docs/superpowers/specs/2026-09-29-farm-care-design.md):
* Daily growth budget (`cap` per crop, `plot.grown`): crops take 2–3 nights from
  seed to harvest; ripe produce ages at half budget, so the harvest window is a day.
* Soil fertility per bed (`soil`): crops feed on it overnight, empty beds rest,
  compost/NPK add to it (compost also on an empty bed: bón lót); depleted soil
  slows growth. Rotation (`prev`): other family +soil, same crop brings pests back.
* Pests at level 2+ spread to neighbouring beds overnight unless sprayed today (`guard`).
* Night drying follows tomorrow's sky; a 3-day outlook and a planning tip are shown.
* Hen mood (`coop.mood`, `fa_clean`): food, a clean coop and heat move it; eggs follow it.
All deterministic, no new randomness; older saves are migrated in validate_data.
"""
from __future__ import annotations
import copy
from ..jsoncopy import tree_copy
from . import kit
from .. import consequences as cq
from .. import archive as ar

ID = 'farm'
PLOT_IDS = ('P1', 'P2', 'P3', 'P4', 'P5', 'P6')
YOUNG, RIPE, OVER, ROTTEN, GROWTH_MAX = 70, 100, 140, 180, 220
MOIST_DRY, MOIST_LOW, MOIST_HIGH, MOIST_WET = 25, 40, 80, 90
WATER_ONE, WATER_ALL, DRAIN = 35, 22, 25
NIGHT_GROWTH = 20
PHI = dict(npk=15, chem=20, bio=2)
COLD_CAP, MAX_LOTS = 160, 30
NEST_MAX = 40
# Care loop (sub-project 3): growth budget per day, soil fertility, rotation, hen mood.
SOIL_START, SOIL_LOW, SOIL_REST, SOIL_ROTATE, SOIL_LEACH = 60, 25, 8, 8, 4
SOIL_ADD = dict(compost=20, npk=30)
CAP_BONUS = dict(compost=4, npk=8)
LOW_CAP = 60              # % of the day's budget on depleted soil
NIGHT_DRY = dict(sun=12, hot=18, wind=15, cloud=8, rain=-13)   # overnight moisture loss by tomorrow's sky
MOOD_START, MOOD_MIN = 80, 20
MOOD = dict(fed=8, hungry=-15, clean=6, dirty=-8, heat=-5, fox=-15)
OUTLOOK_DAYS = 3

CROPS = [
    dict(id='muong', name='Rau muống', emoji='🥬', seed='seed_muong', unit='bó', rate=4, thirst=0, yield_=8, life=2, unlock=1, start=0, value=1, cap=34, feed=8, family='leafy'),
    dict(id='lettuce', name='Xà lách', emoji='🥗', seed='seed_lettuce', unit='cây', rate=3, thirst=0, yield_=8, life=2, unlock=1, start=0, value=1, cap=32, feed=8, family='leafy'),
    dict(id='tomato', name='Cà chua', emoji='🍅', seed='seed_tomato', unit='kg', rate=2, thirst=1, yield_=6, life=4, unlock=1, start=15, value=2, cap=18, feed=12, family='fruit'),
    dict(id='cucumber', name='Dưa leo', emoji='🥒', seed='seed_cucumber', unit='kg', rate=3, thirst=1, yield_=6, life=3, unlock=2, start=0, value=2, cap=26, feed=10, family='fruit'),
    dict(id='herbs', name='Rau thơm', emoji='🌿', seed='seed_herbs', unit='bó', rate=3, thirst=0, yield_=10, life=2, unlock=3, start=0, value=1, cap=30, feed=6, family='leafy'),
]
CROP_INDEX = {x['id']: x for x in CROPS}
EGG = dict(id='egg', name='Trứng gà', emoji='🥚', unit='quả', life=10, value=1)
PRODUCE = {**{x['id']: x for x in CROPS}, 'egg': EGG}
HENS = 10
HEN_COST = 12
GEN = 2
SEASON_DAYS = 4
SEASONS = [
    dict(id='spring', name='Mùa xuân', emoji='🌸', good=('muong', 'lettuce'), bad=(), night=100,
         weather=dict(sun=3, cloud=2, rain=1, wind=1, hot=0), text='Nắng ấm, mưa phùn: rau ăn lá lên nhanh, ai cũng có nên rau lá rẻ.'),
    dict(id='summer', name='Mùa hạ', emoji='🌞', good=('tomato', 'cucumber'), bad=('lettuce',), night=100,
         weather=dict(hot=3, sun=2, rain=2, cloud=1, wind=0), text='Nắng gắt, giông chiều: cà chua, dưa leo vào mùa; xà lách dễ trổ ngồng nên khan và đắt.'),
    dict(id='autumn', name='Mùa thu', emoji='🍂', good=('herbs', 'muong'), bad=(), night=100,
         weather=dict(wind=2, cloud=2, sun=2, rain=1, hot=0), text='Gió heo may: rau thơm đậm vị, gió làm đất mau khô.'),
    dict(id='winter', name='Mùa đông', emoji='❄️', good=('lettuce', 'herbs'), bad=('tomato', 'cucumber'), night=50,
         weather=dict(cloud=3, wind=2, sun=1, rain=1, hot=0), text='Đêm lạnh, cây lớn chậm qua đêm; cà chua, dưa leo trái vụ nên được giá.'),
]
WHOLESALE = 60            # % of the usual price the wholesale market pays
DEPTH = dict(muong=14, lettuce=12, tomato=12, cucumber=12, herbs=14, egg=30)
SLIP = 4                  # every SLIP units sold today take 10% off the next ones (floor 50%)
PLEDGE_FINE = 2           # xu per unit promised to the HTX and not supplied
BEE_FINE = 15

WEATHER = [
    dict(id='sun', name='Nắng nhẹ', emoji='🌤️', evap=3, tip='Đất khô vừa phải, tưới khi độ ẩm dưới 40%.'),
    dict(id='hot', name='Nắng gắt', emoji='☀️', evap=5, tip='Đất khô rất nhanh; cà chua, dưa leo khát nước hơn.'),
    dict(id='cloud', name='Trời râm', emoji='⛅', evap=2, tip='Ít bốc hơi, tưới ít thôi kẻo úng.'),
    dict(id='rain', name='Mưa rào', emoji='🌧️', evap=-3, tip='Không cần tưới. Đất quá 90% là úng rễ: khơi rãnh thoát nước.'),
    dict(id='wind', name='Gió lộng', emoji='🍃', evap=4, tip='Gió làm lá mất nước, để ý luống rau lá.'),
]
WEATHER_INDEX = {x['id']: x for x in WEATHER}

ITEMS = [
    dict(id='seed_muong', name='Hạt rau muống', emoji='🌱', group='seed', unit='gói', cost=3, start=4),
    dict(id='seed_lettuce', name='Hạt xà lách', emoji='🌱', group='seed', unit='gói', cost=3, start=3),
    dict(id='seed_tomato', name='Cây giống cà chua', emoji='🌱', group='seed', unit='khay', cost=6, start=2),
    dict(id='seed_cucumber', name='Hạt dưa leo', emoji='🌱', group='seed', unit='gói', cost=4, unlock=2),
    dict(id='seed_herbs', name='Hạt rau thơm', emoji='🌱', group='seed', unit='gói', cost=3, unlock=3),
    dict(id='compost', name='Phân compost ủ hoai', emoji='🟫', group='supply', unit='bao', cost=4, start=6),
    dict(id='npk', name='Phân NPK (hóa học)', emoji='🧪', group='supply', unit='bao', cost=5, start=3),
    dict(id='bio_spray', name='Chế phẩm neem sinh học', emoji='🌿', group='supply', unit='chai', cost=6, start=3),
    dict(id='chem_spray', name='Thuốc trừ sâu hóa học', emoji='☠️', group='supply', unit='chai', cost=5, start=2),
    dict(id='feed', name='Cám gà', emoji='🌾', group='feed', unit='bao/ngày', cost=4, start=5),
    dict(id='bag', name='Túi giấy đi chợ', emoji='🛍️', group='pack', unit='túi', cost=1, start=20),
    dict(id='carton', name='Thùng carton lót giấy', emoji='📦', group='pack', unit='thùng', cost=2, start=10),
    dict(id='egg_tray', name='Khay trứng 10 ô', emoji='🥚', group='pack', unit='khay', cost=1, start=10),
]
PRICES = {'muong': 6, 'lettuce': 7, 'tomato': 12, 'cucumber': 10, 'herbs': 5, 'egg': 3}
B_PERCENT, ORGANIC_PERCENT = 70, 130

PEOPLE = [
    ('Chú Tám', 'Tổ trưởng HTX rau', 'Làm rau ba mươi năm, nhìn lá là biết đất khát hay no.', 'bossy'),
    ('Chị Hạnh', 'Bếp trưởng nhà hàng Bếp Mây', 'Nhận hàng có cân, có checklist, trễ mười phút là gọi.', 'picky'),
    ('Cô Hai', 'Khách quen ở sạp chợ', 'Mua ít mà mua hoài, câu cửa miệng “rau này có xịt thuốc không?”.', 'warm'),
    ('Anh Tuấn', 'Thương lái', 'Ép giá có nghề, nhưng trả tiền mặt ngay.', 'sour'),
    ('Bé Mít', 'Học sinh lớp 5', 'Mê gà, hỏi một trăm câu một phút.', 'genz'),
    ('Bà Năm', 'Chủ lò bánh flan đầu chợ', 'Chỉ lấy trứng mới, soi từng quả dưới đèn.', 'quiet'),
    ('Anh Phong', 'Chủ quán chay Lá Xanh', 'Menu ghi “rau hữu cơ”, nên hỏi kỹ từng lô.', 'picky'),
]

# (npc, kind, title, opening, items, organic, note, min_day)
ORDERS = [
    (1, 'contract', 'Rau muống cho Bếp Mây', 'Chị Hạnh gọi: “Trưa nay chị làm rau muống xào tỏi, giao sớm giùm chị!”', {'muong': 6}, False, 'Loại A, lá xanh, không dập.', 1),
    (2, 'market', 'Cô Hai đi chợ sớm', 'Cô Hai ghé sạp: “Con ơi, bán cô ít rau với chục trứng nha!”', {'muong': 2, 'tomato': 1, 'egg': 10}, False, 'Rau này có xịt thuốc không con?', 1),
    (5, 'contract', 'Trứng cho mẻ bánh flan', 'Bà Năm nhắn: “Mai bà làm hai trăm cái flan, cần trứng mới.”', {'egg': 20}, False, 'Trứng sạch, không nứt, xếp khay giùm bà.', 1),
    (6, 'contract', 'Xà lách hữu cơ cho quán chay', 'Anh Phong gọi: “Anh cần xà lách hữu cơ cho món salad, có QR nhật ký nha.”', {'lettuce': 4}, True, 'Menu quán ghi rõ “rau hữu cơ” đó em.', 1),
    (1, 'contract', 'Cà chua cho nồi sốt', 'Chị Hạnh: “Chiều nay chị nấu sốt cà, cần cà chín đỏ loại A.”', {'tomato': 4}, False, 'Trái chín đều, không nứt.', 1),
    (4, 'market', 'Mít mua trứng cho mẹ', 'Bé Mít chạy qua: “Mẹ con dặn mua chục trứng mới đẻ!”', {'egg': 10}, False, 'Con coi gà đẻ trứng luôn được hông?', 1),
    (3, 'market', 'Thương lái gom hàng', 'Anh Tuấn đậu xe tải nhỏ: “Có gì bán nấy, loại B cũng lấy nha.”', {'muong': 6, 'tomato': 3}, False, 'Loại nào cũng được, miễn nhanh.', 2),
    (6, 'contract', 'Rau muống hữu cơ cho quán chay', 'Anh Phong: “Tuần này quán làm rau muống xào chay, cần hàng hữu cơ.”', {'muong': 5}, True, 'Nhớ dán tem QR truy xuất nha.', 2),
    (1, 'contract', 'Dưa leo cho món gỏi', 'Chị Hạnh: “Cần dưa leo giòn cho gỏi, trái thẳng đẹp.”', {'cucumber': 4}, False, 'Loại A, không đắng.', 3),
    (0, 'contract', 'HTX gom rau cho siêu thị', 'Chú Tám: “Siêu thị đặt HTX một lô rau, nông trại mình góp phần nha con.”', {'lettuce': 4, 'muong': 4}, False, 'Hàng siêu thị: đồng đều, loại A.', 3),
    (5, 'contract', 'Trứng cho bánh bông lan', 'Bà Năm: “Tiệc cưới đặt bánh bông lan, bà cần thêm trứng.”', {'egg': 20}, False, 'Không lấy trứng để qua đêm ngoài chuồng.', 3),
    (2, 'market', 'Cô Hai mua rau thơm', 'Cô Hai: “Bán cô ít rau thơm với xà lách cuốn bánh tráng.”', {'herbs': 3, 'lettuce': 2}, False, 'Rau thơm nhiều lá nha con.', 5),
    (6, 'contract', 'Rau thơm hữu cơ', 'Anh Phong: “Món gỏi cuốn chay cần rau thơm hữu cơ.”', {'herbs': 4}, True, 'QR nhật ký phải sạch nha em.', 5),
]
# Generator 2 adds these (old saves keep generator 1 through the kit legacy band).
ORDERS_NEW = [
    (0, 'contract', 'HTX gom rau cho chợ đầu mối', 'Chú Tám: “Sáng mai xe HTX chạy chợ đầu mối, nông trại góp một phần rau lá nha con.”', {'muong': 5, 'lettuce': 3}, False, 'Rau bó gọn, không dập lá.', 2),
    (2, 'market', 'Chợ phiên cuối tuần', 'Cô Hai rủ: “Chợ phiên đông lắm, con mang rau với trứng ra sạp cô bán chung nha!”', {'muong': 3, 'lettuce': 2, 'egg': 10}, False, 'Chợ phiên ai cũng hỏi rau sạch.', 3),
    (4, 'market', 'Lớp của Mít bán bánh gây quỹ', 'Bé Mít: “Lớp con làm bánh bán gây quỹ, cô giáo nhờ mua một chục trứng!”', {'egg': 10}, False, 'Con muốn tự xếp trứng vô khay!', 3),
    (1, 'contract', 'Tiệc cưới đặt salad', 'Chị Hạnh: “Cuối tuần có tiệc cưới ba chục bàn, chị cần xà lách với cà chua loại A.”', {'lettuce': 5, 'tomato': 4}, False, 'Tiệc lớn, hàng phải đồng đều.', 4),
    (3, 'market', 'Thương lái gom cà chua', 'Anh Tuấn: “Cà chua đang có giá, có bao nhiêu anh lấy bấy nhiêu, loại B cũng được.”', {'tomato': 5}, False, 'Trả tiền mặt ngay, không kỳ kèo.', 4),
    (5, 'contract', 'Bếp ăn trường mầm non', 'Bà Năm giới thiệu: “Bếp trường mầm non cần trứng mới với rau muống cho bữa trưa các bé.”', {'egg': 10, 'muong': 4}, False, 'Trẻ nhỏ ăn, hàng phải sạch và mới.', 5),
    (1, 'contract', 'Dưa leo cho món dưa góp', 'Chị Hạnh: “Bếp làm dưa góp cho cả tuần, cần dưa leo giòn, trái đều.”', {'cucumber': 5}, False, 'Loại A, trái thẳng, không cong queo.', 5),
    (6, 'contract', 'Lẩu nấm chay cần rau thơm hữu cơ', 'Anh Phong: “Tối nay quán ra món lẩu nấm, anh cần rau thơm với xà lách hữu cơ.”', {'herbs': 3, 'lettuce': 3}, True, 'QR phải khớp nhật ký từng luống nha em.', 6),
]
ORDERS_V2 = ORDERS + ORDERS_NEW


def _lvl(day: int) -> int:
    return 1 + (day - 1) // 2


def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        return _make_v1(day, slot, serial)
    return _make_v2(day, slot, serial)


def _make_v2(day: int, slot: int, serial: int) -> dict:
    rng = kit.rng(ID, 'v2', day, slot)
    pool = [o for o in ORDERS_V2 if o[7] <= day]
    order = list(range(len(pool)))
    kit.rng(ID, 'orders2', day).shuffle(order)   # distinct orders within a day
    npc, kind, title, opening, items, organic, note, _ = pool[order[slot % len(pool)]]
    level, tier = _lvl(day), kit.tier(day)
    wanted = {}
    for crop, qty in items.items():
        if crop != 'egg' and CROP_INDEX[crop]['unlock'] > level:
            continue
        wanted[crop] = qty if crop == 'egg' else qty + rng.randrange(2) + rng.randrange(1 + tier)
    if not wanted:
        wanted = {'muong': 4 + tier}
    needs = dict(kind=kind, items=wanted, organic=organic, grade='A' if kind == 'contract' else 'any',
                 pack='carton' if kind == 'contract' else 'bag', note=note)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=kind, needs=needs,
                         crate=[], label=None, refused=0, served=None, quoted_price=None, gen=GEN)


def _make_v1(day: int, slot: int, serial: int) -> dict:
    rng = kit.rng(ID, day, slot)
    pool = [o for o in ORDERS if o[7] <= day]
    order = list(range(len(pool)))
    kit.rng(ID, 'orders', day).shuffle(order)   # distinct orders within a day
    npc, kind, title, opening, items, organic, note, _ = pool[order[slot % len(pool)]]
    level = _lvl(day)
    wanted = {}
    for crop, qty in items.items():
        if crop != 'egg' and CROP_INDEX[crop]['unlock'] > level:
            continue
        wanted[crop] = qty + (rng.randrange(2) if crop != 'egg' else 0)
    if not wanted:
        wanted = {'muong': 4}
    needs = dict(kind=kind, items=wanted, organic=organic, grade='A' if kind == 'contract' else 'any',
                 pack='carton' if kind == 'contract' else 'bag', note=note)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=kind, needs=needs,
                         crate=[], label=None, refused=0, served=None, quoted_price=None)


FIXED = ('needs',)


def _plot(pid: str, crop=None, growth=0, moisture=55, weeds=0, compost=False, soil=SOIL_START) -> dict:
    return dict(id=pid, crop=crop, growth=growth, moisture=moisture, weeds=weeds, pests=0, seen=0, scouted=0,
                compost=compost, npk=False, organic=True, phi=0, stress=0, planted=1 if crop else 0,
                soil=soil, grown=0, prev=None, guard=0)


def _care_fields() -> dict:
    """Plot keys added by the care loop (older saves gain them in validate_data)."""
    return dict(soil=SOIL_START, grown=0, prev=None, guard=0)


def _empty(plot: dict) -> None:
    """Clear a bed after harvest or clearing: the soil, its history and the moisture stay."""
    prev = plot['crop']
    plot.update(_plot(plot['id'], None, 0, plot['moisture'], plot['weeds'], soil=plot['soil']))
    plot['prev'] = prev


def _rotate(plot: dict, crop: dict, prev) -> str:
    """Rotation rule at sowing: the other family feeds the soil, the same crop brings its pests back."""
    if not prev or prev not in CROP_INDEX:
        return ''
    if prev == crop['id']:
        plot['pests'] = max(plot['pests'], 1)
        return f'Vụ trước cũng là {crop["name"].lower()}: sâu bệnh cũ còn trong đất, nhớ thăm sâu sớm.'
    if CROP_INDEX[prev]['family'] != crop['family']:
        plot['soil'] = _clamp(plot['soil'] + SOIL_ROTATE)
        return f'Luân canh sau {CROP_INDEX[prev]["name"].lower()}: đất được bồi thêm màu (+{SOIL_ROTATE}).'
    return ''


def initial() -> dict:
    plots = [_plot('P1', 'muong', 100, 62, 1, soil=58), _plot('P2', 'tomato', 88, 55, 0, True, soil=72), _plot('P3', 'lettuce', 64, 58, 2, soil=55),
             _plot('P4', 'muong', 36, 50, 0, soil=62), _plot('P5', 'tomato', 18, 60, 1, soil=66), _plot('P6', None, 0, 45, 1, soil=40)]
    plots[5]['prev'] = 'muong'
    cold = [dict(id='L1', crop='muong', grade='A', qty=6, day=1, expires=2, organic=True, unsafe=False, plot='P1'),
            dict(id='L2', crop='tomato', grade='A', qty=4, day=1, expires=4, organic=True, unsafe=False, plot='P2'),
            dict(id='L3', crop='egg', grade='A', qty=20, day=1, expires=10, organic=False, unsafe=False, plot='coop')]
    return dict(turn=0, seq=3, plots=plots, cold=cold,
                coop=dict(hens=HENS, fed=0, nest=10, stale=0, mood=MOOD_START, cleaned=0),
                diary=[dict(day=1, plot='P2', text='Nhận lại vườn từ chú Tám: luống 2 đã bón phân compost, chưa dùng hóa chất.')],
                stats=dict(harvested=0, unsafe=0, wasted_spray=0, delivered=0, eggs=0, sold=0, pledged=0),
                **_v2_fields())


def _v2_fields() -> dict:
    return dict(desk=kit.desk_initial(), market=dict(day=0, sold={}, income=0, start=0), pledge=None)


# ---------------------------------------------------------------- simulation
def season(day: int) -> dict:
    return SEASONS[((max(1, day) - 1) // SEASON_DAYS) % len(SEASONS)]


def _season_day(day: int) -> int:
    return (max(1, day) - 1) % SEASON_DAYS + 1


def _fit(day: int, crop: str) -> int:
    x = season(day)
    return 1 if crop in x['good'] else -1 if crop in x['bad'] else 0


def _weather(day: int) -> dict:
    """The season's own weather mix; from day 6 storms and heat come more often."""
    if day <= 1:
        return WEATHER[0]
    w = dict(season(day)['weather'])
    if kit.tier(day) >= 2:
        w['hot'] += 1
        w['rain'] += 1
    r = kit.rng(ID, 'weather', day).random() * sum(w.values())
    for x in WEATHER:
        r -= w.get(x['id'], 0)
        if r < 0:
            return x
    return WEATHER[0]


def market(day: int) -> dict:
    """Wholesale price index per produce (percent of the usual price) for the day."""
    x = season(day)
    r = kit.rng(ID, 'market', day)
    spread = 20 + 5 * kit.tier(day)
    out = {}
    for k in PRICES:
        base = 80 if k in x['good'] else 135 if k in x['bad'] else 100
        out[k] = base + r.randint(-spread, spread)
    if day >= 3:                         # one shock a day: a glut or a shortage
        k = list(PRICES)[r.randrange(len(PRICES))]
        out[k] += -35 if r.random() < 0.5 else 45
    return {k: max(45, min(190, v)) for k, v in out.items()}


def rumour(day: int) -> dict:
    """What the trader whispers about tomorrow: right four times in five."""
    today, nxt = market(day), market(day + 1)
    crop = max(PRICES, key=lambda k: (abs(nxt[k] - today[k]), k))
    up = nxt[crop] > today[crop]
    if kit.rng(ID, 'rumour', day).random() < 0.2:
        up = not up
    return dict(crop=crop, up=up)


def _tenths(day: int, crop: str, grade: str, sold: int) -> int:
    """Wholesale price of the next unit in tenths of a xu."""
    v = PRICES[crop] * market(day)[crop] * WHOLESALE // 1000
    if grade == 'B':
        v = v * B_PERCENT // 100
    return max(1, v * max(50, 100 - 10 * (sold // SLIP)) // 100)


def _sale(day: int, crop: str, grade: str, sold: int, qty: int) -> int:
    return max(1, (sum(_tenths(day, crop, grade, sold + i) for i in range(qty)) + 5) // 10)


def _mkt(c: dict, d: dict) -> dict:
    m = d['market']
    if m['day'] != c['day']:
        m.update(day=c['day'], sold={}, income=0, start=c['turn'])
    return m


def _clamp(x: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, x))


def _cap(p: dict) -> int:
    """How much the crop on this bed can still grow in one day's work (its daily budget)."""
    crop = CROP_INDEX[p['crop']]
    cap = crop['cap'] + CAP_BONUS['compost'] * int(p['compost']) + CAP_BONUS['npk'] * int(p['npk'])
    if p['soil'] < SOIL_LOW:
        cap = cap * LOW_CAP // 100
    return cap if p['growth'] < RIPE else cap // 2    # ripe produce ages slower than it grows


def _night_growth(p: dict, day: int) -> int:
    g = NIGHT_GROWTH * season(day)['night'] // 100
    return g // 2 if p['soil'] < SOIL_LOW else g


def _step(d: dict, turn: int, weather: dict, day: int) -> None:
    onset = 97 - 12 * kit.tier(day)      # pests find the farm more often as days go by
    for i, p in enumerate(d['plots']):
        crop = CROP_INDEX.get(p['crop'])
        evap = weather['evap'] + (crop['thirst'] if crop and weather['evap'] > 0 else 0)
        p['moisture'] = _clamp(p['moisture'] - evap)
        if (turn + i * 4) % 12 == 0:
            p['weeds'] = min(3, p['weeds'] + 1)
        if not crop:
            continue
        if p['pests'] == 0:
            if p['growth'] >= 20 and (turn * 7 + i * 13 + day * 5) % onset == 0:
                p['pests'] = 1
        elif (turn + i) % 10 == 0:
            p['pests'] = min(3, p['pests'] + 1)
        if p['moisture'] < MOIST_DRY:
            p['stress'] = min(50, p['stress'] + 1)
            continue
        room = _cap(p) - p['grown']
        if room <= 0:                     # today's budget is used: the rest happens overnight
            continue
        # The season speeds up (or slows) growing; once ripe, crops age at their own pace.
        g = crop['rate'] + (_fit(day, crop['id']) if p['growth'] < RIPE else 0) + int(p['compost']) + int(p['npk']) - int(p['weeds'] >= 2) - int(p['pests'] >= 2)
        g = max(1, g)
        if p['moisture'] > MOIST_WET:
            g = max(1, g // 2)
        g = min(g, room)
        before = p['growth']
        p['growth'] = min(GROWTH_MAX, before + g)
        p['grown'] = min(GROWTH_MAX, p['grown'] + p['growth'] - before)


def _day_gain(growth: int, grown: int, cap: int) -> int:
    """Growth reached by the end of a day with full care (mirrors _step's budget)."""
    g = growth
    if g < RIPE:
        if g + max(0, cap - grown) < RIPE:
            return g + max(0, cap - grown)
        grown += RIPE - g
        g = RIPE
    return min(GROWTH_MAX, g + max(0, cap // 2 - grown))


def _eta(p: dict, day: int) -> tuple:
    """Days until ripe and until over-ripe with full care (0 = today). None beyond a week."""
    if not p['crop']:
        return None, None
    base = dict(p, growth=0)
    full = _cap(base)                                   # the budget below ripeness
    g, grown = p['growth'], p['grown']
    ripe = over = None
    for k in range(8):
        g = _day_gain(g, grown, full)
        if ripe is None and g >= RIPE:
            ripe = k
        if over is None and g >= OVER:
            over = k
            break
        g = min(GROWTH_MAX, g + _night_growth(p, day + k))
        grown = 0
    return ripe, over


def _advance(d: dict, turn: int, day: int, is_open: bool) -> None:
    """Catch the farm up to the current game turn (deterministic, bounded)."""
    if not is_open:
        return
    steps = min(80, max(0, turn - d['turn']))
    weather = _weather(day)
    for k in range(steps):
        _step(d, turn - steps + k + 1, weather, day)
    d['turn'] = max(d['turn'], turn)


def _sync(c: dict) -> dict:
    d = kit.data(c)
    _advance(d, c['turn'], c['day'], c['open'])
    return d


def _stage(p: dict) -> str:
    if not p['crop']:
        return 'empty'
    g = p['growth']
    if g < 30:
        return 'sprout'
    if g < YOUNG:
        return 'young'
    if g < RIPE:
        return 'almost'
    if g < OVER:
        return 'ripe'
    if g < ROTTEN:
        return 'over'
    return 'rotten'


def _plot_of(d: dict, pid) -> dict:
    kit.need(pid in PLOT_IDS, 'Luống không tồn tại.')
    return d['plots'][PLOT_IDS.index(pid)]


def _diary(d: dict, c: dict, pid: str, text: str) -> None:
    d['diary'] = ar.last(d['diary'] + [dict(day=c['day'], plot=pid, text=text[:200])], 40, 'farm.diary', c)


def _price(c: dict, crop: str) -> int:
    return kit.price(c, crop, PRICES[crop])


def _cold_units(d: dict) -> int:
    return sum(l['qty'] for l in d['cold'])


def _add_lot(c: dict, d: dict, crop: str, grade: str, qty: int, organic: bool, unsafe: bool, plot: str) -> dict:
    d['seq'] += 1
    lot = dict(id=f'L{d["seq"]}', crop=crop, grade=grade, qty=qty, day=c['day'], expires=c['day'] + PRODUCE[crop]['life'] - 1,
               organic=organic, unsafe=unsafe, plot=plot)
    d['cold'].append(lot)
    return lot


def _room_for(d: dict, qty: int, lots: int) -> None:
    kit.need(_cold_units(d) + qty <= COLD_CAP and len(d['cold']) + lots <= MAX_LOTS,
             f'Kho mát đầy ({_cold_units(d)}/{COLD_CAP} đơn vị). Giao bớt đơn hoặc bỏ lô hư trước nhé.')


def _harvest_yield(p: dict) -> tuple[int, int, str]:
    crop = CROP_INDEX[p['crop']]
    g = p['growth']
    ripeness = 'young' if g < RIPE else 'ripe' if g < OVER else 'over'
    mult = {'young': 55, 'ripe': 100, 'over': 75}[ripeness] - 10 * p['weeds'] - min(40, 4 * p['stress']) - (20 if p['pests'] >= 3 else 0)
    total = max(1, crop['yield_'] * max(10, mult) // 100)
    if ripeness != 'ripe':
        return 0, total, ripeness
    b_share = {0: 0, 1: 25, 2: 50, 3: 80}[p['pests']] + (20 if p['stress'] > 8 else 0)
    b = min(total, total * b_share // 100)
    return total - b, b, ripeness


# ---------------------------------------------------------------- tasks
def _quote(c: dict, needs: dict) -> int:
    total = sum(_price(c, k) * q for k, q in needs['items'].items())
    return total * ORGANIC_PERCENT // 100 if needs['organic'] else total


def on_task(s: dict, c: dict, t: dict) -> None:
    if t.get('quoted_price') is None:
        t['quoted_price'] = _quote(c, t['needs'])


def on_start(s: dict, c: dict) -> None:
    d = kit.data(c)
    d['turn'] = c['turn']   # night growth was simulated at close; closed-shop turns do not count
    for t in c['tasks']:
        if t['career'] == ID and t['status'] not in ('completed', 'cancelled', 'referred'):
            on_task(s, c, t)
    w = _weather(c['day'])
    kit.log(s, c, 'weather', f'Thời tiết Đồi Gió hôm nay: {w["emoji"]} {w["name"]}. {w["tip"]}')
    x = season(c['day'])
    idx = market(c['day'])
    hi, lo = max(PRICES, key=lambda k: (idx[k], k)), min(PRICES, key=lambda k: (idx[k], k))
    kit.log(s, c, 'note', f'{x["emoji"]} {x["name"]} (ngày {_season_day(c["day"])}/{SEASON_DAYS}). Chợ đầu mối: '
            f'{PRODUCE[hi]["name"].lower()} được giá, {PRODUCE[lo]["name"].lower()} rớt giá.')
    if d['pledge'] is not None and d['pledge']['day'] != c['day']:
        d['pledge'] = None
    d['market'].update(day=c['day'], sold={}, income=0, start=c['turn'])
    kit.desk_start(s, c, ID, d['desk'], EVENTS, w['id'], festival=c['life'].get('mode') == 'festival')
    if d['desk']['ev'] is not None:
        _attach(c, d)


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    items = ', '.join(f'{q} {PRODUCE[k]["unit"]} {PRODUCE[k]["name"].lower()}' for k, q in n['items'].items())
    kind = 'Hợp đồng nhà hàng: chỉ nhận loại A, đóng thùng carton' if n['kind'] == 'contract' else 'Khách chợ: loại A hay B đều được (B giá mềm), đựng túi giấy'
    eggs = n['items'].get('egg', 0)
    extra = f' Trứng xếp khay 10 ô ({-(-eggs // 10)} khay).' if eggs else ''
    organic = ' Bắt buộc nhãn HỮU CƠ có QR nhật ký canh tác.' if n['organic'] else ''
    return f'Đơn: {items}. {kind}.{organic}{extra} “{n["note"]}”'


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _sync(c)
    if name == 'fa_decide':
        return _decide(s, c, p)
    kit.desk_block(d['desk'], 'Có chuyện bất ngờ ở trại — quyết xong rồi làm tiếp nhé.')
    out = _handle(s, c, name, p)
    kit.desk_tick(s, c, ID, d['desk'], EVENTS, _weather(c['day'])['id'])
    _field_tick(s, c, d)
    if d['desk']['ev'] is None and name == 'fa_harvest':
        _maybe_trader(s, c, d)
    ev = d['desk']['ev']
    if ev is not None:
        _attach(c, d)
        x = kit.desk_script(EVENTS, ev['script'])
        out['message'] = (out.get('message') or '') + f' {x["emoji"]} {x["title"]}!'
    return out


def _field_tick(s: dict, c: dict, d: dict) -> None:
    """A farm day is mostly field work, not finished orders: after a dozen beats of work
    the day's first surprise comes even if no order has been delivered yet."""
    desk = d['desk']
    if c['day'] < 2 or desk['ev'] is not None or desk['fired'] or desk['day'] != c['day'] or not desk['plan']:
        return
    m = d['market']
    if m['day'] == c['day'] and c['turn'] - m['start'] >= 12:
        kit.desk_fire(s, c, ID, desk, EVENTS, 'between', _weather(c['day'])['id'])


def _lot(d: dict, lid) -> dict:
    lot = next((l for l in d['cold'] if l['id'] == lid), None)
    kit.need(lot, 'Lô không còn trong kho mát.')
    return lot


def _sellable(c: dict, lot: dict) -> None:
    kit.need(not lot['unsafe'], 'Lô này thu hoạch khi chưa hết thời gian cách ly thuốc — không được bán. Hãy hủy lô.')
    kit.need(lot['expires'] >= c['day'], 'Lô đã quá hạn tươi, không bán được. Hủy lô và ghi hao hụt.')


def _bees(c: dict, d: dict) -> bool:
    day = d['desk']['marks'].get('bees')
    return day is not None and 0 <= c['day'] - day <= 1


def _handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _sync(c)
    level = kit.level(c)
    if name == 'fa_sell':
        kit.confirm(p, 'Xác nhận bán sỉ cho chợ đầu mối.')
        lot = _lot(d, p.get('lot'))
        _sellable(c, lot)
        qty = kit.integer(p.get('qty', lot['qty']), 1, 60 * 12)
        kit.need(qty <= lot['qty'], f'Lô {lot["id"]} chỉ còn {lot["qty"]}.')
        m = _mkt(c, d)
        crop = PRODUCE[lot['crop']]
        sold = m['sold'].get(lot['crop'], 0)
        room = DEPTH[lot['crop']] - sold
        kit.need(room > 0, f'Chợ đầu mối hôm nay đã đủ {crop["name"].lower()}, mai quay lại nhé.')
        kit.need(qty <= room, f'Chợ đầu mối chỉ nhận thêm {room} {crop["unit"]} {crop["name"].lower()} hôm nay.')
        total = _sale(c['day'], lot['crop'], lot['grade'], sold, qty)
        lot['qty'] -= qty
        if not lot['qty']:
            d['cold'].remove(lot)
        m['sold'][lot['crop']] = sold + qty
        m['income'] += total
        d['stats']['sold'] += qty
        kit.metric(c, 'fa_market_sales')
        kit.money(s, c, total, f'Bán sỉ {qty} {crop["unit"]} {crop["name"].lower()} loại {lot["grade"]}', lot['id'], 'revenue')
        left = room - qty
        return dict(message=f'Chợ đầu mối nhận {qty} {crop["unit"]} {crop["name"].lower()} loại {lot["grade"]} · +{total} xu.'
                    + (f' Hôm nay chợ còn nhận {left} {crop["unit"]}, giá xuống dần.' if left else ' Chợ đã đủ mặt hàng này hôm nay.'))
    if name == 'fa_pledge':
        pl = d['pledge']
        kit.need(pl is not None and pl['day'] == c['day'], 'Không có phần góp HTX nào đang chờ.')
        left = pl['qty'] - pl['done']
        kit.need(left > 0, 'Đã góp đủ phần cho HTX rồi.')
        lot = _lot(d, p.get('lot'))
        crop = CROP_INDEX[pl['crop']]
        kit.need(lot['crop'] == pl['crop'], f'HTX chỉ gom {crop["name"].lower()} hôm nay.')
        kit.need(lot['grade'] == 'A', 'Siêu thị chỉ nhận hàng loại A.')
        _sellable(c, lot)
        qty = kit.integer(p.get('qty', min(left, lot['qty'])), 1, 60)
        kit.need(qty <= lot['qty'], f'Lô {lot["id"]} chỉ còn {lot["qty"]}.')
        kit.need(qty <= left, f'HTX chỉ cần thêm {left} {crop["unit"]}.')
        lot['qty'] -= qty
        if not lot['qty']:
            d['cold'].remove(lot)
        pl['done'] += qty
        pay = qty * pl['price']
        pl['paid'] += pay
        d['stats']['pledged'] += qty
        kit.metric(c, 'fa_pledged')
        kit.money(s, c, pay, f'HTX thu mua {qty} {crop["unit"]} {crop["name"].lower()}', lot['id'], 'revenue')
        if pl['done'] >= pl['qty']:
            return dict(message=f'Góp đủ {pl["qty"]} {crop["unit"]} {crop["name"].lower()} cho HTX · +{pay} xu. Chú Tám: “Vậy mới là xã viên chứ!”', celebrate=True)
        return dict(message=f'Góp {qty} {crop["unit"]} cho HTX · +{pay} xu. Còn thiếu {pl["qty"] - pl["done"]} trước khi khép ca.')
    if name == 'fa_hen':
        kit.confirm(p, 'Xác nhận mua một gà mái đẻ.')
        coop = d['coop']
        kit.need(coop['hens'] < HENS, f'Chuồng đã đủ {HENS} mái rồi.')
        kit.need(c['money'] >= HEN_COST, f'Cần {HEN_COST} xu để mua một gà mái đẻ.')
        kit.money(s, c, -HEN_COST, 'Mua gà mái đẻ', 'coop', 'stock')
        coop['hens'] += 1
        return dict(message=f'Mua thêm một gà mái đẻ ({HEN_COST} xu). Chuồng giờ có {coop["hens"]} mái.')
    if name == 'fa_plant':
        plot = _plot_of(d, p.get('plot'))
        crop = CROP_INDEX.get(p.get('crop'))
        kit.need(crop, 'Chưa có giống cây này.')
        kit.need(crop['unlock'] <= level, f'{crop["name"]} mở ở cấp {crop["unlock"]}.')
        kit.need(plot['crop'] is None, 'Luống đang có cây. Thu hoạch hoặc dọn luống trước.')
        kit.take(c, crop['seed'], 1)
        prev, soil, lined = plot['prev'], plot['soil'], plot['compost']
        plot.update(_plot(plot['id'], crop['id'], crop['start'], plot['moisture'], 0, lined, soil))
        plot['prev'] = prev
        plot['planted'] = c['day']
        rotation = _rotate(plot, crop, prev)
        _diary(d, c, plot['id'], f'Làm đất, nhổ sạch cỏ, gieo {crop["name"].lower()}.' + (f' {rotation}' if rotation else ''))
        kit.metric(c, 'fa_planted')
        ripe, _ = _eta(plot, c['day'])
        when = '' if ripe is None else f' Chăm đủ thì khoảng {ripe} ngày nữa tới lứa.'
        return dict(message=f'Đã làm đất và gieo {crop["name"].lower()} ở luống {plot["id"]}. Giữ ẩm {MOIST_LOW}–{MOIST_HIGH}% để cây lên đều.'
                    + when + (f' {rotation}' if rotation else ''))
    if name == 'fa_water':
        w = _weather(c['day'])
        if p.get('plot') == 'all':
            kit.need(d['desk']['marks'].get('nopump') != c['day'],
                     'Trạm bơm đang cúp nước: van tưới cả vườn không chạy. Tưới từng luống bằng nước giếng nhé.')
            for plot in d['plots']:
                plot['moisture'] = _clamp(plot['moisture'] + WATER_ALL)
            wet = [x['id'] for x in d['plots'] if x['moisture'] > MOIST_WET]
            return dict(message=f'Mở van tưới cả vườn: mỗi luống +{WATER_ALL}% độ ẩm.' + (f' Coi chừng úng: {", ".join(wet)}.' if wet else '')
                        + (' Trời đang mưa mà vẫn tưới…' if w['id'] == 'rain' else ''))
        plot = _plot_of(d, p.get('plot'))
        before = plot['moisture']
        plot['moisture'] = _clamp(before + WATER_ONE)
        warn = ' Đất vốn đã ẩm, tưới thêm dễ úng rễ.' if before > MOIST_HIGH else ''
        return dict(message=f'Tưới luống {plot["id"]}: độ ẩm {before}% → {plot["moisture"]}%.' + warn)
    if name == 'fa_drain':
        plot = _plot_of(d, p.get('plot'))
        kit.need(plot['moisture'] > MOIST_HIGH, 'Đất chưa úng, không cần khơi rãnh.')
        plot['moisture'] = _clamp(plot['moisture'] - DRAIN)
        return dict(message=f'Khơi rãnh thoát nước luống {plot["id"]}: độ ẩm còn {plot["moisture"]}%.')
    if name == 'fa_weed':
        plot = _plot_of(d, p.get('plot'))
        kit.need(plot['weeds'] > 0, 'Luống sạch cỏ rồi.')
        plot['weeds'] = 0
        kit.metric(c, 'fa_weeded')
        return dict(message=f'Nhổ sạch cỏ luống {plot["id"]}. Cỏ để lâu sẽ giành nước và dinh dưỡng của rau.')
    if name == 'fa_scout':
        plot = _plot_of(d, p.get('plot'))
        kit.need(plot['crop'], 'Luống trống, không có gì để thăm.')
        plot['seen'] = plot['pests']
        plot['scouted'] = c['turn']
        kit.metric(c, 'fa_scouted')
        text = {0: 'Lật mặt dưới lá: sạch, chưa thấy sâu.', 1: 'Thấy vài con sâu non và lỗ lá nhỏ — mới chớm.',
                2: 'Sâu ăn lá nhiều, lá thủng lỗ chỗ. Cần xử lý.', 3: 'Sâu phá nặng, lá xơ xác! Xử lý ngay kẻo mất mùa.'}[plot['pests']]
        return dict(message=f'Thăm luống {plot["id"]}: {text}')
    if name == 'fa_fertilize':
        plot = _plot_of(d, p.get('plot'))
        kind = kit.one_of(p.get('kind'), ('compost', 'npk'), 'Chọn phân compost hoặc NPK.')
        if kind == 'compost' and not plot['crop']:      # bón lót: feed an empty bed before sowing
            kit.need(not plot['compost'], 'Luống này đã bón lót compost, gieo cây thôi.')
            kit.take(c, 'compost', 1)
            plot['compost'] = True
            before = plot['soil']
            plot['soil'] = _clamp(before + SOIL_ADD['compost'])
            _diary(d, c, plot['id'], 'Bón lót phân compost ủ hoai trước khi gieo (hữu cơ).')
            return dict(message=f'Bón lót compost luống {plot["id"]}: đất màu {before} → {plot["soil"]}. Vụ tới cây lớn khỏe hơn.')
        kit.need(plot['crop'], 'Luống trống, gieo cây trước rồi hẵng bón NPK.')
        kit.need(plot['growth'] < OVER, 'Cây đã tới lứa thu, bón thêm vô ích.')
        if kind == 'compost':
            kit.need(not plot['compost'], 'Luống này đã bón compost trong vụ.')
            kit.take(c, 'compost', 1)
            plot['compost'] = True
            plot['growth'] = min(GROWTH_MAX, plot['growth'] + 5)
            before = plot['soil']
            plot['soil'] = _clamp(before + SOIL_ADD['compost'])
            _diary(d, c, plot['id'], 'Bón phân compost ủ hoai (hữu cơ).')
            return dict(message=f'Bón compost luống {plot["id"]}: đất màu {before} → {plot["soil"]}, cây lớn đều hơn. Vẫn giữ được chuẩn hữu cơ.')
        kit.need(not plot['npk'], 'Luống này đã bón NPK trong vụ.')
        kit.take(c, 'npk', 1)
        plot['npk'] = True
        plot['organic'] = False
        plot['growth'] = min(GROWTH_MAX, plot['growth'] + 15)
        plot['soil'] = _clamp(plot['soil'] + SOIL_ADD['npk'])
        plot['phi'] = max(plot['phi'], c['turn'] + PHI['npk'])
        _diary(d, c, plot['id'], f'Bón phân NPK hóa học. Cách ly {PHI["npk"]} nhịp trước thu hoạch.')
        return dict(message=f'Bón NPK luống {plot["id"]}: cây lên nhanh. Từ giờ lô này KHÔNG còn là hữu cơ và phải cách ly {PHI["npk"]} nhịp trước khi thu.')
    if name == 'fa_spray':
        plot = _plot_of(d, p.get('plot'))
        kind = kit.one_of(p.get('kind'), ('bio', 'chem'), 'Chọn chế phẩm sinh học hoặc thuốc hóa học.')
        kit.need(plot['crop'], 'Luống trống, không cần phun.')
        before = plot['pests']
        bee_note = ''

        if kind == 'bio':
            kit.take(c, 'bio_spray', 1)
            plot['pests'] = max(0, plot['pests'] - 2)
            plot['phi'] = max(plot['phi'], c['turn'] + PHI['bio'])
            _diary(d, c, plot['id'], f'Phun chế phẩm neem sinh học. Cách ly {PHI["bio"]} nhịp.')
        else:
            kit.take(c, 'chem_spray', 1)
            plot['pests'] = 0
            plot['organic'] = False
            plot['phi'] = max(plot['phi'], c['turn'] + PHI['chem'])
            _diary(d, c, plot['id'], f'Phun thuốc trừ sâu hóa học. Cách ly {PHI["chem"]} nhịp trước thu hoạch.')
            if _bees(c, d):
                bee_note = _kill_bees(s, c, d, plot['id'])
        plot['seen'] = plot['pests']
        plot['scouted'] = c['turn']
        plot['guard'] = c['day']          # a bed sprayed today does not catch its neighbours' pests tonight
        if before == 0:
            d['stats']['wasted_spray'] += 1
            return dict(message=f'Phun luống {plot["id"]} khi không có sâu: tốn thuốc, hại cả ong và thiên địch. Thăm đồng trước khi phun nhé.' + bee_note)
        return dict(message=f'Đã phun luống {plot["id"]}: sâu còn mức {plot["pests"]}/3.' + (f' Nhớ: cách ly {PHI["chem"]} nhịp, lô này không còn hữu cơ.' if kind == 'chem' else '') + bee_note)
    if name == 'fa_harvest':
        kit.confirm(p, 'Xác nhận thu hoạch luống này.')
        plot = _plot_of(d, p.get('plot'))
        kit.need(plot['crop'], 'Luống trống.')
        crop = CROP_INDEX[plot['crop']]
        kit.need(plot['growth'] >= YOUNG, f'{crop["name"]} còn non quá (độ lớn {plot["growth"]}/{RIPE}), chưa thu được.')
        kit.need(plot['growth'] < ROTTEN, 'Luống đã quá lứa, hỏng hết. Dọn luống làm phân thôi.')
        a, b, ripeness = _harvest_yield(plot)
        _room_for(d, a + b, int(a > 0) + int(b > 0))
        unsafe = c['turn'] < plot['phi']
        lots = []
        if a:
            lots.append(_add_lot(c, d, crop['id'], 'A', a, plot['organic'], unsafe, plot['id']))
        if b:
            lots.append(_add_lot(c, d, crop['id'], 'B', b, plot['organic'], unsafe, plot['id']))
        d['stats']['harvested'] += a + b
        kit.metric(c, 'fa_harvests')
        label = {'young': 'còn non: trái/lá nhỏ, chỉ đạt loại B', 'ripe': 'đúng độ chín', 'over': 'già quá lứa: xơ, chỉ đạt loại B'}[ripeness]
        _diary(d, c, plot['id'], f'Thu hoạch {a + b} {crop["unit"]} {crop["name"].lower()} ({label}).' + (' VI PHẠM thời gian cách ly!' if unsafe else ''))
        msg = f'Thu hoạch luống {plot["id"]}: {crop["name"]} {label}. Loại A: {a}, loại B: {b} {crop["unit"]} → kho mát.'
        if plot['pests'] and ripeness == 'ripe':
            msg += ' Sâu làm một phần bị xuống loại B.'
        if unsafe:
            d['stats']['unsafe'] += 1
            kit.log(s, c, 'safety', f'Thu hoạch luống {plot["id"]} khi chưa hết thời gian cách ly — lô không được bán.')
            msg += f' ⛔ Chưa hết thời gian cách ly (còn {plot["phi"] - c["turn"]} nhịp): lô này KHÔNG được bán, phải hủy.'
        _empty(plot)
        return dict(message=msg, celebrate=bool(a) and not unsafe)
    if name == 'fa_clear':
        kit.confirm(p, 'Xác nhận nhổ bỏ cây trên luống này.')
        plot = _plot_of(d, p.get('plot'))
        kit.need(plot['crop'], 'Luống đã trống.')
        crop = CROP_INDEX[plot['crop']]
        _diary(d, c, plot['id'], f'Nhổ bỏ {crop["name"].lower()} ({_stage(plot)}), ủ làm phân.')
        _empty(plot)
        return dict(message=f'Đã dọn luống {plot["id"]}, thân lá đem ủ phân. Luống sẵn sàng gieo vụ mới.')
    if name == 'fa_discard':
        kit.confirm(p, 'Xác nhận bỏ lô này; ghi vào hao hụt.')
        lot = next((l for l in d['cold'] if l['id'] == p.get('lot')), None)
        kit.need(lot, 'Lô không còn trong kho mát.')
        d['cold'].remove(lot)
        kit.waste(c, lot['crop'], min(60, lot['qty']), lot['qty'] * PRODUCE[lot['crop']]['value'], 'Hủy lô không đạt' + (' (chưa hết cách ly)' if lot['unsafe'] else ''))
        return dict(message=f'Đã hủy lô {lot["id"]} ({lot["qty"]} {PRODUCE[lot["crop"]]["unit"]} {PRODUCE[lot["crop"]]["name"].lower()}), ghi hao hụt.')
    if name == 'fa_feed':
        coop = d['coop']
        kit.need(coop['fed'] != c['day'], 'Hôm nay gà đã được cho ăn.')
        kit.take(c, 'feed', 1)
        coop['fed'] = c['day']
        kit.metric(c, 'fa_fed')
        return dict(message=f'Rải cám, thay nước sạch cho {coop["hens"]} con gà. Gà no thì mai đẻ đủ.')
    if name == 'fa_clean':
        coop = d['coop']
        kit.need(coop['cleaned'] != c['day'], 'Hôm nay chuồng đã dọn sạch rồi.')
        coop['cleaned'] = c['day']
        kit.metric(c, 'fa_cleaned')
        return dict(message='Cào phân, thay rơm ổ đẻ, rửa máng và thay nước mát. Gà vui thì đẻ đều.')
    if name == 'fa_collect':
        coop = d['coop']
        kit.need(coop['nest'] > 0, 'Ổ đang trống, gà chưa đẻ thêm.')
        n = coop['nest']
        stale = min(coop['stale'], n)
        cracked = n // 9
        fresh = max(0, n - stale - cracked)
        _room_for(d, fresh + stale, int(fresh > 0) + int(stale > 0))
        if fresh:
            _add_lot(c, d, 'egg', 'A', fresh, False, False, 'coop')
        if stale:
            _add_lot(c, d, 'egg', 'B', stale, False, False, 'coop')
        if cracked:
            kit.waste(c, 'egg', cracked, cracked, 'Trứng nứt khi nhặt')
        coop['nest'] = 0
        coop['stale'] = 0
        d['stats']['eggs'] += fresh + stale
        kit.metric(c, 'fa_eggs')
        return dict(message=f'Nhặt {n} quả: {fresh} quả sạch loại A' + (f', {stale} quả để qua đêm (loại B)' if stale else '')
                    + (f', {cracked} quả nứt để dùng trong nhà' if cracked else '') + '. Lau khô, không rửa nước để giữ lớp màng bảo vệ.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Công việc không thuộc nông trại.')
    kit.need(t['known'], 'Nghe khách đặt hàng trước nhé (bấm “Nhận đơn”).')
    if t.get('quoted_price') is None:
        on_task(s, c, t)
    return _order_action(s, c, d, t, name, p)


def _order_action(s: dict, c: dict, d: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    if name == 'fa_pack':
        lot = next((l for l in d['cold'] if l['id'] == p.get('lot')), None)
        kit.need(lot, 'Lô không còn trong kho mát.')
        qty = kit.integer(p.get('qty', 1), 1, 60)
        kit.need(qty <= lot['qty'], f'Lô {lot["id"]} chỉ còn {lot["qty"]}.')
        kit.need(lot['expires'] >= c['day'], 'Lô đã quá hạn tươi, không bán được. Hủy lô và ghi hao hụt.')
        kit.need(lot['crop'] in n['items'], f'Đơn này không đặt {PRODUCE[lot["crop"]]["name"].lower()}.')
        packed = sum(e['qty'] for e in t['crate'] if e['crop'] == lot['crop'])
        kit.need(packed + qty <= n['items'][lot['crop']] + 2, 'Thùng đã đủ số lượng khách đặt (tặng thêm tối đa 2).')
        kit.need(len(t['crate']) < 12, 'Thùng đã xếp quá nhiều lô nhỏ.')
        entry = next((e for e in t['crate'] if e['lot'] == lot['id']), None)
        if entry:
            entry['qty'] += qty
        else:
            t['crate'].append(dict(lot=lot['id'], crop=lot['crop'], grade=lot['grade'], qty=qty, day=lot['day'], expires=lot['expires'],
                                   organic=lot['organic'], unsafe=lot['unsafe']))
        lot['qty'] -= qty
        if not lot['qty']:
            d['cold'].remove(lot)
        kit.start_work(t)
        return dict(message=f'Xếp {qty} {PRODUCE[lot["crop"]]["unit"]} {PRODUCE[lot["crop"]]["name"].lower()} loại {lot["grade"]} (lô {lot["id"]}) vào thùng.')
    if name == 'fa_unpack':
        entry = next((e for e in t['crate'] if e['lot'] == p.get('lot')), None)
        kit.need(entry, 'Lô này không có trong thùng.')
        t['crate'].remove(entry)
        _return_entry(d, entry)
        return dict(message=f'Đã trả lô {entry["lot"]} về kho mát.')
    if name == 'fa_label':
        label = kit.one_of(p.get('label'), ('plain', 'organic'), 'Chọn nhãn thường hoặc nhãn hữu cơ.')
        t['label'] = label
        return dict(message='Dán nhãn thường: tên nông trại, ngày thu hoạch.' if label == 'plain'
                    else 'Dán nhãn HỮU CƠ kèm QR: khách quét sẽ xem được nhật ký canh tác của từng lô.')
    if name == 'fa_deliver':
        kit.confirm(p, 'Xác nhận giao hàng cho khách.')
        kit.need(t['crate'], 'Thùng đang trống. Xếp hàng từ kho mát trước.')
        kit.need(t['label'], 'Dán nhãn cho thùng hàng trước khi giao.')
        who = PEOPLE[int(t['npc'].rsplit('_', 1)[1]) - 1][0]
        if t['label'] == 'organic':
            bad = [e for e in t['crate'] if not e['organic']]
            if bad:
                t['refused'] += 1
                t['mistakes'] += 1
                e = bad[0]
                why = 'gà ăn cám công nghiệp, trứng không phải hữu cơ' if e['crop'] == 'egg' else f'nhật ký ghi luống của lô {e["lot"]} có dùng hóa chất trong vụ'
                kit.log(s, c, 'refused', f'{who} quét QR: {why}. Nhãn hữu cơ không đúng.', t['npc'], t['id'])
                cq.slip(t, 'label', 2, 'Dán nhãn hữu cơ mà nhật ký không khớp, tôi quét QR mới phát hiện.', 'nhãn hữu cơ không đúng sự thật')
                return dict(message=f'{who} quét QR trên nhãn: {why}. “Nhãn hữu cơ sai thì chị không nhận được.” Đổi nhãn thường hoặc thay lô.', refused=True)
        if n['organic'] and t['label'] != 'organic':
            t['refused'] += 1
            t['mistakes'] += 1
            cq.slip(t, 'label_plain', 1, 'Hợp đồng ghi rau hữu cơ mà thùng dán nhãn thường, phải đổi lại mới nhận.', 'thiếu nhãn hữu cơ theo hợp đồng')
            return dict(message=f'{who}: “Hợp đồng ghi rau hữu cơ có QR truy xuất. Thùng nhãn thường thì quán không dùng được.”', refused=True)
        eggs = sum(e['qty'] for e in t['crate'] if e['crop'] == 'egg')
        veg = any(e['crop'] != 'egg' for e in t['crate'])
        needs = {}
        if n['kind'] == 'contract':
            needs['carton'] = 1
        elif veg:
            needs['bag'] = 1
        if eggs:
            needs['egg_tray'] = -(-eggs // 10)
        for item, q in needs.items():
            kit.need(kit.stock(c, item) >= q, f'Hết {kit.item(ID, item)["name"].lower()} (cần {q}). Mở Kho để nhập thêm.')
        for item, q in needs.items():
            kit.take(c, item, q)
        served = _evaluate(c, t)
        t['served'] = served
        d['stats']['delivered'] += 1
        kit.metric(c, 'fa_deliveries')
        if served['a'] + served['b'] >= sum(n['items'].values()) and not served['b'] and n['kind'] == 'contract':
            kit.metric(c, 'fa_perfect_contracts')
        _slips(c, t)
        if cq.slips(t) and not t['mistakes']:
            t['mistakes'] = 1        # a complaint is never a clean job (streak, perfect count)
        bill = _bill(c, t)
        react = cq.react(s, c, t, served['pay'], who=who)
        crate, t['crate'] = t['crate'], []
        if react['kind'] in ('refuse', 'walkout'):
            # The buyer sends the crate back: clean produce returns to the cold room, the rest is destroyed.
            for e in crate:
                if e.get('unsafe'):
                    kit.waste(c, e['crop'], min(60, e['qty']), e['qty'] * PRODUCE[e['crop']]['value'], 'Khách trả lại: lô chưa hết cách ly')
                else:
                    _return_entry(d, e)
        kit.complete(s, c, t, react['pay'], f'Bạn đã giao “{t["title"]}” cho {who}.')
        note = []
        if served['missing']:
            note.append(f'thiếu {served["missing"]} so với đơn')
        if served['b'] and n['kind'] == 'contract':
            note.append(f'{served["b"]} đơn vị loại B bị tính giá loại B')
        msg = f'Đã giao hàng · +{react["pay"]} xu' + (f' ({bill} = {served["pay"]} xu).' if bill else '.') + (' Khách ghi chú: ' + ', '.join(note) + '.' if note else ' Đủ, đúng loại, nhãn trung thực!' if not cq.slips(t) else '')
        if react['message']:
            msg += ' ' + react['message']
        return dict(message=msg, celebrate=not note and not cq.slips(t))
    raise kit.eng().GameError('Thao tác nông trại không hợp lệ.')


def _slips(c: dict, t: dict) -> None:
    """What the buyer finds when they open the crate (recorded at the hand-over only)."""
    n, sv, crate = t['needs'], t['served'], t['crate']
    bad = next((e for e in crate if e.get('unsafe')), None)
    if bad:
        name = PRODUCE[bad['crop']]['name'].lower()
        cq.slip(t, 'pesticide', 3, f'Lô {name} còn trong thời gian cách ly thuốc trừ sâu mà vẫn giao cho tôi, ai dám nấu!',
                'giao rau chưa hết thời gian cách ly thuốc', safety=True)
    want = sum(n['items'].values())
    if sv['missing']:
        crop = next(k for k, q in n['items'].items() if sum(e['qty'] for e in crate if e['crop'] == k) < q)
        got = sum(e['qty'] for e in crate if e['crop'] == crop)
        p = PRODUCE[crop]
        sev = 1 if sv['missing'] * 5 <= want else 2 if sv['missing'] * 2 <= want else 3
        cq.slip(t, 'short', sev, f'Đặt {n["items"][crop]} {p["unit"]} {p["name"].lower()} mà chỉ giao {got}, bếp phải chạy đi mua thêm.',
                f'giao thiếu {sv["missing"]} so với đơn')
    if sv['b'] and n['kind'] == 'contract':
        cq.slip(t, 'grade', 1 if sv['b'] * 2 <= sv['a'] + sv['b'] else 2, f'Hợp đồng ghi loại A mà giao lẫn {sv["b"]} phần loại B.',
                f'{sv["b"]} phần loại B trong hợp đồng loại A')
    if sv['expiring']:
        cq.slip(t, 'fresh', 1, 'Hàng hết hạn tươi ngay trong ngày, phải nấu liền kẻo hỏng.', 'hàng hết hạn trong ngày')


def _return_entry(d: dict, entry: dict) -> None:
    lot = next((l for l in d['cold'] if l['id'] == entry['lot']), None)
    if lot:
        lot['qty'] += entry['qty']
    else:
        d['cold'].append(dict(id=entry['lot'], crop=entry['crop'], grade=entry['grade'], qty=entry['qty'], day=entry['day'],
                              expires=entry['expires'], organic=entry['organic'], unsafe=bool(entry.get('unsafe')), plot='crate'))


def _bill(c: dict, t: dict) -> str:
    """The pay as line math, as the buyer counts it: each crop × its price, grade B at 70%,
    then the organic premium (same rules as _evaluate)."""
    n, parts = t['needs'], []
    for crop, want in n['items'].items():
        a = min(want, sum(e['qty'] for e in t['crate'] if e['crop'] == crop and e['grade'] == 'A'))
        b = min(want - a, sum(e['qty'] for e in t['crate'] if e['crop'] == crop and e['grade'] == 'B'))
        name, price = PRODUCE[crop]['name'].lower(), _price(c, crop)
        if a:
            parts.append(f'{a} {name} × {price}')
        if b:
            parts.append(f'{b} {name} loại B × {price * B_PERCENT // 100}')
    if not parts:
        return ''
    text = ' + '.join(parts)
    if t['label'] == 'organic' and (n['organic'] or n['kind'] == 'market'):
        text = f'({text}) × {ORGANIC_PERCENT}% nhãn hữu cơ'
    return text


def _evaluate(c: dict, t: dict) -> dict:
    n = t['needs']
    pay = a_total = b_total = missing = 0
    for crop, want in n['items'].items():
        a = sum(e['qty'] for e in t['crate'] if e['crop'] == crop and e['grade'] == 'A')
        b = sum(e['qty'] for e in t['crate'] if e['crop'] == crop and e['grade'] == 'B')
        pa = min(a, want)
        pb = min(b, want - pa)
        price = _price(c, crop)
        pay += pa * price + pb * (price * B_PERCENT // 100)
        a_total += pa
        b_total += pb
        missing += want - pa - pb
    organic = t['label'] == 'organic'
    if organic and (n['organic'] or n['kind'] == 'market'):
        pay = pay * ORGANIC_PERCENT // 100
    oldest = max((c['day'] - e['day'] for e in t['crate']), default=0)
    expiring = any(e['expires'] <= c['day'] for e in t['crate'] if e['crop'] != 'egg')
    return dict(pay=pay, a=a_total, b=b_total, missing=missing, age=oldest, expiring=expiring, label=t['label'], organic=organic)


# ---------------------------------------------------------------- feedback
def feedback(c: dict, t: dict) -> dict:
    sv = t['served']
    n = t['needs']
    want = sum(n['items'].values())
    patience = t.get('patience', 100)
    speed = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    qty = 5 if not sv['missing'] else max(1, 5 - -(-sv['missing'] * 4 // want))
    if n['kind'] == 'contract':
        grade = 5 if not sv['b'] else 3 if sv['b'] * 2 <= sv['a'] + sv['b'] else 2
        grade_note = 'toàn bộ loại A' if not sv['b'] else f'{sv["b"]} đơn vị loại B trong hợp đồng loại A'
    else:
        grade = 5 if not sv['b'] else 4
        grade_note = 'hàng đẹp' if not sv['b'] else 'có hàng loại B, giá mềm'
    fresh = 2 if sv['expiring'] else 5 if sv['age'] == 0 else 4 if sv['age'] == 1 else 3
    fresh_note = 'hàng hết hạn trong ngày' if sv['expiring'] else 'thu hoạch trong ngày' if sv['age'] == 0 else f'thu hoạch {sv["age"]} ngày trước'
    honest = 2 if t['refused'] else 5
    honest_note = 'bị phát hiện nhãn/hàng không đúng hợp đồng' if t['refused'] else ('nhãn hữu cơ có QR nhật ký rõ ràng' if sv['organic'] else 'nhãn đúng sự thật')
    rows = [dict(key='quantity', label='Đủ số lượng', score=qty, note='đủ như đơn' if not sv['missing'] else f'thiếu {sv["missing"]} so với đơn'),
            dict(key='quality', label='Đúng loại hàng', score=grade, note=grade_note),
            dict(key='fresh', label='Độ tươi', score=fresh, note=fresh_note),
            dict(key='honest', label='Nhãn trung thực', score=honest, note=honest_note),
            dict(key='speed', label='Giao đúng hẹn', score=speed, note=f'kiên nhẫn còn {patience}%')]
    return dict(criteria=rows)


# ---------------------------------------------------------------- projection
def public_task(t: dict) -> dict:
    v = tree_copy(t)
    if not t['known']:
        v['needs'] = None
    return v


def public_data(c: dict) -> dict:
    d = tree_copy(kit.data(c))
    _advance(d, c['turn'], c['day'], c['open'])
    start = d['market']['start'] if d['market']['day'] == c['day'] else c['turn']
    care = _care(c, d, start)
    for p in d['plots']:
        p['stage'] = _stage(p)
        p['safe_in'] = max(0, p['phi'] - c['turn'])
        p['scouted_ago'] = (c['turn'] - p['scouted']) if p['scouted'] else None
        p['scouted_today'] = bool(p['scouted']) and p['scouted'] >= start
        p['eta'], p['over_in'] = _eta(p, c['day'])
        p['cap'] = _cap(p) if p['crop'] else 0
        p['day_no'] = c['day'] - p['planted'] + 1 if p['crop'] else 0
        p['rotation'] = {k['id']: _rotation_hint(p, k) for k in CROPS} if not p['crop'] else {}
        p.pop('pests', None)   # pests are only known by walking the plot
    for lot in d['cold']:
        lot['left'] = lot['expires'] - c['day']
    w, tomorrow = _weather(c['day']), _weather(c['day'] + 1)
    d['weather'] = w
    d['forecast'] = tomorrow
    d['outlook'] = _outlook(c['day'])
    d['plan'] = _plan(c, d, tomorrow)
    d['care'] = care
    coop = d['coop']
    d['coop'] = dict(coop, lay_pct=_lay_pct(coop['mood']), cleaned_today=coop['cleaned'] == c['day'], mood_ok=MOOD_OK)
    d['cold_units'] = _cold_units(d)
    d['fed_today'] = d['coop']['fed'] == c['day']
    d['prices'] = {k: _price(c, k) for k in PRICES}
    day = c['day']
    x, nxt = season(day), season(day + SEASON_DAYS - _season_day(day) + 1)
    names = lambda ids: [CROP_INDEX[k]['name'] for k in ids]
    d['season'] = dict(id=x['id'], name=x['name'], emoji=x['emoji'], text=x['text'], good=names(x['good']), bad=names(x['bad']),
                       day=_season_day(day), days=SEASON_DAYS, next=dict(name=nxt['name'], emoji=nxt['emoji']))
    m = d['market'] if d['market']['day'] == day else dict(day=day, sold={}, income=0)
    idx = market(day)
    rows = []
    for k in PRICES:
        sold = m['sold'].get(k, 0)
        rows.append(dict(crop=k, index=idx[k], a=_tenths(day, k, 'A', 0), b=_tenths(day, k, 'B', 0), next_a=_tenths(day, k, 'A', sold),
                         sold=sold, depth=DEPTH[k], fit=_fit(day, k) if k in CROP_INDEX else 0))
    d['market'] = dict(day=day, rows=rows, income=m['income'], rumour=rumour(day), wholesale=WHOLESALE, slip=SLIP)
    pl = d['pledge']
    d['pledge'] = pl if pl and pl['day'] == day else None
    d['nopump'] = d['desk']['marks'].get('nopump') == day
    d['bees'] = _bees(c, d)
    d['desk'] = _desk_view(c)
    return d


def _rotation_hint(p: dict, crop: dict) -> str | None:
    prev = p['prev']
    if not prev or prev not in CROP_INDEX:
        return None
    if prev == crop['id']:
        return 'same'
    return 'rotate' if CROP_INDEX[prev]['family'] != crop['family'] else None


def _outlook(day: int) -> list:
    """The next days' sky from the commune radio (the weather is fixed per day, so it is exact)."""
    rows = []
    for k in range(1, OUTLOOK_DAYS + 1):
        w, x = _weather(day + k), season(day + k)
        rows.append(dict(day=day + k, id=w['id'], emoji=w['emoji'], name=w['name'], night=-NIGHT_DRY[w['id']],
                         season=x['name'] if x['id'] != season(day + k - 1)['id'] else None, season_emoji=x['emoji']))
    return rows


def _plan(c: dict, d: dict, tomorrow: dict) -> str:
    """One planning tip for tonight, from tomorrow's sky and the beds."""
    planted = [p for p in d['plots'] if p['crop']]
    wet = [p['id'] for p in planted if p['moisture'] > MOIST_HIGH - 10]
    if tomorrow['id'] == 'rain':
        return ('Mai mưa: đêm nay đất tự ẩm thêm, đừng tưới đẫm.' + (f' Luống {", ".join(wet)} đã ẩm, khơi rãnh sẵn kẻo úng và trôi phân.' if wet else ''))
    need = -NIGHT_DRY[tomorrow['id']]
    dry = [p['id'] for p in planted if p['moisture'] + need < MOIST_LOW]
    sky = {'hot': 'Mai nắng gắt', 'wind': 'Mai gió lộng', 'sun': 'Mai nắng nhẹ', 'cloud': 'Mai trời râm'}[tomorrow['id']]
    if dry:
        return f'{sky}: đêm nay đất khô thêm {abs(need)}%. Tưới luống {", ".join(dry)} trước khi khép ca.'
    return f'{sky}: đêm nay đất khô thêm {abs(need)}%. Các luống đủ ẩm qua đêm.'


def _care(c: dict, d: dict, start: int) -> list:
    """Today's care checklist (computed on the server, shown with ui-kit reqList)."""
    day = c['day']
    planted = [p for p in d['plots'] if p['crop']]
    ids = lambda rows: ', '.join(p['id'] for p in rows)
    rows = []
    dry = [p for p in planted if p['moisture'] < MOIST_LOW]
    wet = [p for p in planted if p['moisture'] > MOIST_HIGH]
    if dry or wet:
        rows.append(dict(ok=False, icon='💧', label='Giữ ẩm ' + ' · '.join(x for x in (f'tưới {ids(dry)}' if dry else '', f'khơi rãnh {ids(wet)}' if wet else '') if x),
                         tone='danger' if any(p['moisture'] < MOIST_DRY for p in dry) else None))
    else:
        rows.append(dict(ok=True, icon='💧', label='Độ ẩm các luống vừa đủ'))
    pests = [p for p in planted if p['seen'] >= 1 and p['scouted'] >= start]
    walk = [p for p in planted if not (p['scouted'] and p['scouted'] >= start)]
    if pests:
        rows.append(dict(ok=False, icon='🐛', label=f'Xử lý sâu {ids(pests)}', note='Sâu mức 2 trở lên sẽ lan sang luống bên cạnh qua đêm.',
                         tone='danger' if any(p['seen'] >= 2 for p in pests) else 'warn'))
    rows.append(dict(ok=True if not walk else None, icon='🔍', label='Thăm sâu mọi luống' if not walk else f'Thăm sâu {ids(walk)}', note=None))
    weedy = [p for p in d['plots'] if p['weeds'] >= 2]
    if weedy:
        rows.append(dict(ok=False, icon='🌾', label=f'Nhổ cỏ {ids(weedy)}'))
    poor = [p for p in d['plots'] if p['soil'] < SOIL_LOW]
    if poor:
        rows.append(dict(ok=False, icon='🟫', label=f'Đất bạc màu {ids(poor)}', note='bón compost, hoặc để luống trống nghỉ qua đêm', tone='warn'))
    ripe = [p for p in planted if RIPE <= p['growth'] < ROTTEN]
    if ripe:
        rows.append(dict(ok=False, icon='🧺', label=f'Thu hoạch {ids(ripe)}', note='quá lứa thì chỉ còn loại B' if any(p['growth'] >= OVER for p in ripe) else None))
    coop = d['coop']
    rows.append(dict(ok=coop['fed'] == day, icon='🌾', label='Cho gà ăn & thay nước'))
    rows.append(dict(ok=coop['cleaned'] == day, icon='🧹', label='Dọn chuồng gà'))
    if coop['nest']:
        rows.append(dict(ok=None, icon='🥚', label=f'Nhặt {coop["nest"]} trứng trong ổ', note='để qua đêm thì chỉ còn loại B'))
    return rows


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == original.get('gen'), 'Phiên bản đơn hàng sai.')
    items = original['needs']['items']
    kit.need(isinstance(t.get('crate'), list) and len(t['crate']) <= 12, 'Thùng hàng sai.')
    for e in t['crate']:
        keys = {'lot', 'crop', 'grade', 'qty', 'day', 'expires', 'organic'}
        kit.need(isinstance(e, dict) and set(e) in (keys, keys | {'unsafe'}), 'Lô trong thùng sai.')   # older saves have no 'unsafe'
        kit.need(e['crop'] in items and e['grade'] in ('A', 'B') and type(e['organic']) is bool and type(e.get('unsafe', False)) is bool, 'Lô trong thùng sai.')
        kit.text(e['lot'], 20)
        kit.integer(e['qty'], 1, 60)
        kit.integer(e['day'], 1, 10**7)
        kit.integer(e['expires'], 0, 10**7)
    kit.need(len({e['lot'] for e in t['crate']}) == len(t['crate']), 'Trùng lô trong thùng.')
    kit.need(t.get('label') in (None, 'plain', 'organic'), 'Nhãn thùng sai.')
    kit.integer(t.get('refused'), 0, 1000)
    kit.need(t.get('quoted_price') is None or kit.integer(t['quoted_price'], 1, 10**6), 'Giá đơn sai.')
    sv = t.get('served')
    if sv is not None:
        kit.need(isinstance(sv, dict) and set(sv) == {'pay', 'a', 'b', 'missing', 'age', 'expiring', 'label', 'organic'}, 'Kết quả giao hàng sai.')
        for k in ('pay', 'a', 'b', 'missing', 'age'):
            kit.integer(sv[k], 0, 10**6)
        kit.need(type(sv['expiring']) is bool and type(sv['organic']) is bool and sv['label'] in ('plain', 'organic'), 'Kết quả giao hàng sai.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    kit.need(isinstance(d, dict) and isinstance(d.get('stats'), dict), 'Dữ liệu nông trại sai.')
    # v0.5 migration: older saves gain the market, pledge and surprise desk.
    kit.mark_legacy(c, ID, 'gen')
    for k, v in _v2_fields().items():
        d.setdefault(k, v)
    for k in ('sold', 'pledged'):
        d['stats'].setdefault(k, 0)
    # Care loop migration: soil, the day's growth budget, rotation memory and hen mood.
    for p in d['plots'] if isinstance(d.get('plots'), list) else []:
        if isinstance(p, dict):
            for k, v in _care_fields().items():
                p.setdefault(k, v)
    if isinstance(d.get('coop'), dict):
        d['coop'].setdefault('mood', MOOD_START)
        d['coop'].setdefault('cleaned', max(0, c['day'] - 1))
    if isinstance(d['market'], dict):
        d['market'].setdefault('start', 0)
    kit.need(set(d) == {'turn', 'seq', 'plots', 'cold', 'coop', 'diary', 'stats', 'desk', 'market', 'pledge'}, 'Dữ liệu nông trại sai.')
    _validate_v2(c, d)
    kit.integer(d['turn'], 0, c['turn'])
    kit.integer(d['seq'], 0, 10**9)
    kit.need(isinstance(d['plots'], list) and [p.get('id') for p in d['plots'] if isinstance(p, dict)] == list(PLOT_IDS), 'Luống sai.')
    keys = set(_plot('P1'))
    for p in d['plots']:
        kit.need(set(p) == keys and (p['crop'] is None or p['crop'] in CROP_INDEX), 'Luống sai.')
        kit.integer(p['growth'], 0, GROWTH_MAX)
        kit.integer(p['moisture'], 0, 100)
        kit.integer(p['weeds'], 0, 3)
        kit.integer(p['pests'], 0, 3)
        kit.integer(p['seen'], 0, 3)
        kit.integer(p['stress'], 0, 50)
        for k in ('scouted', 'phi', 'planted'):
            kit.integer(p[k], 0, 10**9)
        kit.integer(p['soil'], 0, 100)
        kit.integer(p['grown'], 0, GROWTH_MAX)
        kit.integer(p['guard'], 0, 10**7)
        kit.need(p['prev'] is None or p['prev'] in CROP_INDEX, 'Luống sai.')
        for k in ('compost', 'npk', 'organic'):
            kit.need(type(p[k]) is bool, 'Luống sai.')
        kit.need(p['organic'] or p['crop'], 'Luống trống không thể mất chuẩn hữu cơ.')
    kit.need(isinstance(d['cold'], list) and len(d['cold']) <= MAX_LOTS + 12, 'Kho mát sai.')
    ids = set()
    for lot in d['cold']:
        kit.need(isinstance(lot, dict) and set(lot) == {'id', 'crop', 'grade', 'qty', 'day', 'expires', 'organic', 'unsafe', 'plot'}, 'Lô kho mát sai.')
        kit.need(lot['crop'] in PRODUCE and lot['grade'] in ('A', 'B') and type(lot['organic']) is bool and type(lot['unsafe']) is bool, 'Lô kho mát sai.')
        kit.need(lot['plot'] in (*PLOT_IDS, 'coop', 'crate') and lot['id'] not in ids, 'Lô kho mát sai.')
        ids.add(lot['id'])
        kit.text(lot['id'], 20)
        kit.integer(lot['qty'], 1, 60 * 12)
        kit.integer(lot['day'], 1, 10**7)
        kit.integer(lot['expires'], 0, 10**7)
    coop = d['coop']
    kit.need(isinstance(coop, dict) and set(coop) == {'hens', 'fed', 'nest', 'stale', 'mood', 'cleaned'}, 'Chuồng gà sai.')
    kit.integer(coop['mood'], MOOD_MIN, 100)
    kit.integer(coop['cleaned'], 0, max(0, c['day']))
    kit.integer(coop['hens'], 0, HENS)
    kit.integer(coop['fed'], 0, 10**7)
    kit.integer(coop['nest'], 0, NEST_MAX)
    kit.integer(coop['stale'], 0, coop['nest'])
    kit.need(isinstance(d['diary'], list) and len(d['diary']) <= 40, 'Nhật ký canh tác sai.')
    for row in d['diary']:
        kit.need(isinstance(row, dict) and set(row) == {'day', 'plot', 'text'} and row['plot'] in PLOT_IDS, 'Nhật ký canh tác sai.')
        kit.integer(row['day'], 1, 10**7)
        kit.text(row['text'], 200)
    kit.need(isinstance(d['stats'], dict) and set(d['stats']) == {'harvested', 'unsafe', 'wasted_spray', 'delivered', 'eggs', 'sold', 'pledged'}, 'Thống kê nông trại sai.')
    for v in d['stats'].values():
        kit.integer(v, 0, 10**9)


def _validate_v2(c: dict, d: dict) -> None:
    kit.desk_validate(d['desk'], EVENTS)
    ev = d['desk']['ev']
    if ev is not None and 'offer' in ev:
        off = ev['offer']
        if ev['script'] == 'FE-HTX':
            kit.need(isinstance(off, dict) and set(off) == {'crop', 'qty', 'price'} and off['crop'] in CROP_INDEX, 'Đề nghị HTX sai.')
            kit.integer(off['qty'], 1, 20)
            kit.need(off['price'] == PRICES[off['crop']], 'Đề nghị HTX sai.')
        else:
            kit.need(ev['script'] == 'FE-TRADER' and isinstance(off, dict) and set(off) == {'units'}, 'Đề nghị thu mua sai.')
            kit.integer(off['units'], 0, 60 * 12 * 30)
    m = d['market']
    kit.need(isinstance(m, dict) and set(m) == {'day', 'sold', 'income', 'start'} and isinstance(m['sold'], dict), 'Sổ chợ đầu mối sai.')
    kit.integer(m['day'], 0, max(0, c['day']))
    kit.integer(m['start'], 0, c['turn'])
    kit.integer(m['income'], 0, 10 ** 6)
    for k, v in m['sold'].items():
        kit.need(k in DEPTH, 'Sổ chợ đầu mối sai.')
        kit.integer(v, 0, DEPTH[k])
    pl = d['pledge']
    if pl is not None:
        kit.need(isinstance(pl, dict) and set(pl) == {'day', 'crop', 'qty', 'done', 'price', 'paid'} and pl['crop'] in CROP_INDEX, 'Phần góp HTX sai.')
        kit.integer(pl['day'], 1, max(1, c['day']))
        kit.integer(pl['qty'], 1, 20)
        kit.integer(pl['done'], 0, pl['qty'])
        kit.need(pl['price'] == PRICES[pl['crop']] and pl['paid'] == pl['done'] * pl['price'], 'Phần góp HTX sai.')


# ---------------------------------------------------------------- day cycle
def on_close(s: dict, c: dict) -> dict:
    d = _sync(c)
    surprise = kit.desk_close(s, c, ID, d['desk'], EVENTS, _hook)
    pledge = _settle_pledge(s, c, d)
    # Packed crates go back to the cold room overnight.
    for t in c['tasks']:
        if t['career'] == ID and t['status'] not in ('completed', 'cancelled', 'referred') and t['crate']:
            for entry in t['crate']:
                _return_entry(d, entry)
            t['crate'] = []
    expired = 0
    keep = []
    for lot in d['cold']:
        if lot['expires'] <= c['day']:
            expired += lot['qty']
            kit.waste(c, lot['crop'], min(60, lot['qty']), lot['qty'] * PRODUCE[lot['crop']]['value'], 'Hết hạn trong kho mát')
        else:
            keep.append(lot)
    d['cold'] = keep
    tomorrow = _weather(c['day'] + 1)
    night = _night(c, d, tomorrow)
    coop = d['coop']
    mood0 = coop['mood']
    laid = _hens_night(c, coop)
    ripe = [p['id'] for p in d['plots'] if p['crop'] and RIPE <= p['growth'] < OVER]
    m = d['market']
    income = m['income'] if m['day'] == c['day'] else 0
    lines = []
    if income:
        lines.append(f'📈 Bán sỉ ở chợ đầu mối: +{income} xu')
    if pledge:
        lines.append(pledge)
    now, nxt = season(c['day']), season(c['day'] + 1)
    if nxt['id'] != now['id']:
        lines.append(f'{nxt["emoji"]} Mai sang {nxt["name"].lower()}: {nxt["text"]}')
    if surprise:
        lines.append(f'⚡ {surprise}')
    if night['spread']:
        lines.append(f'🐛 Đêm qua sâu bò sang {night["spread"]} luống bên cạnh luống đang có sâu nặng. Sáng mai thăm đồng (🔍) từng luống.')
    if night['low']:
        lines.append(f'🟫 Đất bạc màu ở luống {", ".join(night["low"])}: cây lớn chậm. Bón compost, hoặc thu xong để luống nghỉ, luân canh.')
    if coop['mood'] < MOOD_OK <= mood0 or coop['mood'] < 35:
        lines.append(f'🐔 Đàn gà kém vui ({coop["mood"]}/100): mai chỉ đẻ {laid} quả. Cho ăn đủ, dọn chuồng mỗi ngày là gà vui lại.')
    return dict(expired_units=expired, eggs_tomorrow=coop['nest'], hungry_hens=coop['fed'] != c['day'], ripe_tomorrow=ripe,
                market_income=income, lines=lines, hen_mood=coop['mood'], pest_spread=night['spread'], low_soil=night['low'],
                note=f'Mai trời {tomorrow["name"].lower()}. ' + (f'Luống chín: {", ".join(ripe)}. ' if ripe else '') +
                ('Gà chưa được cho ăn nên mai đẻ ít. ' if coop['fed'] != c['day'] else '') + (f'{expired} đơn vị hàng hết hạn trong kho mát.' if expired else ''))


NEIGHBOURS = {pid: [PLOT_IDS[j] for j in range(len(PLOT_IDS))
                   if (abs(i - j) == 1 and i // 3 == j // 3) or abs(i - j) == 3] for i, pid in enumerate(PLOT_IDS)}
MOOD_OK = 60


def _night(c: dict, d: dict, tomorrow: dict) -> dict:
    """Overnight on the beds: drying by tomorrow's sky, pests spread, crops grow and feed on the soil,
    empty beds rest. Deterministic; the day's growth budget starts again."""
    day = c['day']
    plots = {p['id']: p for p in d['plots']}
    caught = sorted({n for p in d['plots'] if p['crop'] and p['pests'] >= 2 for n in NEIGHBOURS[p['id']]
                     if plots[n]['crop'] and plots[n]['pests'] == 0 and plots[n]['guard'] != day})
    low = []
    for i, p in enumerate(d['plots']):
        p['moisture'] = _clamp(p['moisture'] - NIGHT_DRY[tomorrow['id']])
        if (day + i) % 2 == 0:
            p['weeds'] = min(3, p['weeds'] + 1)
        p['grown'] = 0
        if not p['crop']:
            p['soil'] = _clamp(p['soil'] + SOIL_REST)        # a resting bed recovers
            continue
        if p['pests']:
            p['pests'] = min(3, p['pests'] + 1)
        if p['moisture'] >= MOIST_DRY:
            p['growth'] = min(GROWTH_MAX, p['growth'] + _night_growth(p, day))
        else:
            p['stress'] = min(50, p['stress'] + 3)
        leach = SOIL_LEACH if tomorrow['id'] == 'rain' and p['moisture'] > MOIST_HIGH else 0
        p['soil'] = _clamp(p['soil'] - CROP_INDEX[p['crop']]['feed'] - leach)
        if p['soil'] < SOIL_LOW:
            low.append(p['id'])
    for pid in caught:
        plots[pid]['pests'] = 1
    return dict(spread=len(caught), low=low)


def _lay_pct(mood: int) -> int:
    return 100 if mood >= MOOD_OK else 80 if mood >= 35 else 60


def _hens_night(c: dict, coop: dict) -> int:
    """The flock's mood follows the day's care; tomorrow's eggs follow food and mood."""
    day = c['day']
    fed = coop['fed'] == day
    mood = coop['mood'] + (MOOD['fed'] if fed else MOOD['hungry'])
    if coop['cleaned'] == day:
        mood += MOOD['clean']
    else:
        if day - coop['cleaned'] >= 2:
            mood += MOOD['dirty']
        if _weather(day)['id'] == 'hot':
            mood += MOOD['heat']
    coop['mood'] = max(MOOD_MIN, min(100, mood))
    laid = (coop['hens'] if fed else coop['hens'] // 2) * _lay_pct(coop['mood']) // 100
    coop['stale'] = coop['nest']
    coop['nest'] = min(NEST_MAX, coop['nest'] + laid)
    coop['stale'] = min(coop['stale'], coop['nest'])
    return laid


# ---------------------------------------------------------------- staff & hints
def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _sync(c)
    if e['role'] == 'fa_field':
        if _weather(c['day'])['id'] != 'rain':
            dry = min((p for p in d['plots'] if p['crop']), key=lambda p: p['moisture'], default=None)
            if dry and dry['moisture'] < MOIST_LOW:
                dry['moisture'] = _clamp(dry['moisture'] + WATER_ONE)
                return f'Đã tưới luống {dry["id"]} đang khô (độ ẩm lên {dry["moisture"]}%).'
        weedy = max(d['plots'], key=lambda p: p['weeds'])
        if weedy['weeds'] >= 2:
            weedy['weeds'] = 0
            return f'Đã nhổ cỏ luống {weedy["id"]}.'
        return 'Đã đi một vòng vườn, dựng lại cọc cà chua bị gió nghiêng.'
    if e['role'] == 'fa_coop':
        coop = d['coop']
        if coop['fed'] != c['day'] and kit.stock(c, 'feed') > 0:
            kit.take(c, 'feed', 1)
            coop['fed'] = c['day']
            return 'Đã cho gà ăn, thay nước máng.'
        if coop['cleaned'] != c['day']:
            coop['cleaned'] = c['day']
            return 'Đã dọn chuồng, thay rơm ổ đẻ, rửa máng.'
        return 'Đã đi một vòng chuồng, gà khỏe cả.'
    if e['role'] == 'fa_pack':
        return 'Đã rửa khay, lót giấy thùng carton, viết sẵn tem ngày thu hoạch.'
    return None


def hint(c: dict, t: dict) -> str:
    return ('Thu hoạch luống chín (vùng xanh) → hàng vào kho mát → xếp đúng loại, đủ số vào thùng → nhãn trung thực '
            '(chỉ dán hữu cơ khi lô không dùng hóa chất) → giao. Giữa các đơn: tưới theo dự báo, nhổ cỏ, thăm sâu (sâu nặng lan sang luống bên qua đêm), '
            'bón compost khi đất bạc màu, đổi nhóm cây khi gieo lại, cho gà ăn, dọn chuồng, nhặt trứng. '
            'Hàng dư sắp hết hạn: bán sỉ ở tab 📈 Chợ, chọn lúc được giá.')


def content() -> dict:
    return dict(crops=CROPS, egg=EGG, weather=WEATHER, plots=PLOT_IDS, prices=PRICES,
                thresholds=dict(young=YOUNG, ripe=RIPE, over=OVER, rotten=ROTTEN, max=GROWTH_MAX),
                moisture=dict(dry=MOIST_DRY, low=MOIST_LOW, high=MOIST_HIGH, wet=MOIST_WET),
                water=dict(one=WATER_ONE, all=WATER_ALL, drain=DRAIN), phi=PHI, cold_cap=COLD_CAP,
                b_percent=B_PERCENT, organic_percent=ORGANIC_PERCENT, hens=HENS, hen_cost=HEN_COST,
                seasons=[dict(id=x['id'], name=x['name'], emoji=x['emoji'], text=x['text'], good=list(x['good']), bad=list(x['bad'])) for x in SEASONS],
                season_days=SEASON_DAYS, wholesale=WHOLESALE, depth=DEPTH, slip=SLIP, pledge_fine=PLEDGE_FINE, bee_fine=BEE_FINE,
                soil=dict(low=SOIL_LOW, add=SOIL_ADD, rest=SOIL_REST, rotate=SOIL_ROTATE), mood=dict(ok=MOOD_OK, low=35), families={'leafy': 'Rau lá', 'fruit': 'Cây trái'})


SITUATIONS = [
    dict(id='FA-S01', title='Thương lái ép giá lúc rau rộ', npc=3, tone='gentle', min_day=2,
         opening='Rau muống cả vùng vào lứa cùng lúc. Anh Tuấn đứng đầu bờ: “Bán hết cho anh, 2 xu một bó, không thì để nó già.”',
         facts=[dict(id='price', title='Giá thị trường', source='Chợ đầu mối', text='Giá chợ đầu mối hôm nay 4 xu/bó; ngày thường 6 xu.'),
                dict(id='life', title='Rau để được bao lâu', source='Kho mát', text='Rau muống chỉ giữ tươi 2 ngày trong kho mát.'),
                dict(id='coop', title='HTX của chú Tám', source='Chú Tám', text='HTX đang gom rau cho siêu thị với giá 5 xu/bó, cần hàng loại A, giao sáng mai.')],
         options=[dict(id='split', label='Bán loại A cho HTX giá 5 xu, loại B cho anh Tuấn giá 3 xu, giữ quan hệ cả hai', requires=['price', 'coop'], reward=30, quality='good', stars=4,
                       review='Chủ vườn biết tính, không bán hết cho tôi nhưng giá B cũng hợp lý. Lần sau vẫn ghé.',
                       outcome='Rau không bị bỏ ngoài đồng, thu về giá tốt hơn và anh Tuấn vẫn có hàng.',
                       perspectives=[dict(who='Anh Tuấn', emoji='🚚', text='Ép không được thì mua hàng B, tui cũng có lời chút đỉnh.'),
                                     dict(who='Chú Tám', emoji='👨‍🌾', text='Nông trại góp hàng đẹp cho HTX, cả tổ được siêu thị tin.')]),
                  dict(id='all', label='Bán hết cho anh Tuấn 2 xu cho xong', requires=['life'], reward=16, quality='ok', stars=5,
                       review='Chủ vườn dễ chịu, hàng nhiều, giá tốt!',
                       outcome='Bán nhanh nhưng lỗ công; mấy vườn khác than giá bị kéo xuống theo.',
                       perspectives=[dict(who='Anh Tuấn', emoji='😏', text='Mùa rộ ai cũng phải bán, tui chỉ trả giá thị trường… của tui.'),
                                     dict(who='Hàng xóm trồng rau', emoji='😟', text='Một vườn bán 2 xu là thương lái lấy giá đó ép cả xóm.')]),
                  dict(id='hold', label='Không bán, để rau ngoài đồng chờ giá lên', quality='bad',
                       outcome='Hai ngày sau rau già, xơ, chỉ còn làm phân. Giá cũng không lên.',
                       perspectives=[dict(who='Chú Tám', emoji='👨‍🌾', text='Rau đâu phải lúa, không giữ lâu được con ơi.')])],
         lesson='Nông sản mau hỏng: đừng chờ giá, hãy chia kênh bán (HTX, chợ, thương lái) theo phân loại.'),
    dict(id='FA-S02', title='Thuốc sâu bay từ ruộng bên cạnh', npc=0, tone='tense', min_day=2,
         opening='Sáng nay ruộng bên phun thuốc trừ sâu lúc gió lộng. Mùi thuốc bay qua cả luống xà lách hữu cơ của bạn.',
         facts=[dict(id='wind', title='Hướng gió', source='Quan sát', text='Gió thổi thẳng từ ruộng bên sang luống 3, lá xà lách có vệt thuốc.'),
                dict(id='label', title='Nhãn thuốc', source='Vỏ chai bỏ ở bờ', text='Thuốc hóa học, thời gian cách ly 7 ngày.'),
                dict(id='contract', title='Hợp đồng quán chay', source='Anh Phong', text='Quán chay nhận rau hữu cơ có QR nhật ký từng luống.')],
         options=[dict(id='record', label='Ghi nhật ký, tách luống 3 khỏi hàng hữu cơ tuần này, báo quán chay, nói chuyện với hàng xóm về giờ phun', requires=['wind', 'label', 'contract'], cost=20, quality='good', stars=5,
                       review='Nông trại chủ động báo trước lô bị ảnh hưởng. Đó là lý do quán tin họ.',
                       outcome='Quán chay dời một đơn; hàng xóm hứa phun lúc lặng gió và báo trước. Nhãn hữu cơ vẫn giữ được uy tín.',
                       perspectives=[dict(who='Anh Phong', emoji='🥗', text='Thà thiếu một đơn còn hơn menu ghi sai.'),
                                     dict(who='Chủ ruộng bên', emoji='👨‍🌾', text='Tui không để ý gió, lần sau phun sáng sớm, báo trước.')]),
                  dict(id='quiet', label='Coi như không có gì, vẫn bán luống 3 là hữu cơ', quality='bad', stars=1, cost=40,
                       review='Quét QR thấy sạch nhưng khách của quán phản ánh rau có mùi thuốc. Mất niềm tin.',
                       outcome='Quán chay gửi mẫu kiểm tra: có dư lượng thuốc. Hợp đồng bị tạm dừng, phạt 40 xu.',
                       perspectives=[dict(who='Anh Phong', emoji='😠', text='Một lần nói dối là mất cả hợp đồng.'),
                                     dict(who='Khách ăn chay', emoji='🤢', text='Tôi chọn quán vì chữ “hữu cơ”.')]),
                  dict(id='fight', label='Sang cãi nhau với hàng xóm, đòi bồi thường ngay', requires=['wind'], quality='ok',
                       outcome='Hàng xóm xin lỗi nhưng hai nhà căng thẳng; luống 3 vẫn phải tách khỏi hàng hữu cơ.',
                       perspectives=[dict(who='Chủ ruộng bên', emoji='😤', text='Nói đàng hoàng thì tui đã nghe.'),
                                     dict(who='Chú Tám', emoji='👨‍🌾', text='Làm nông phải sống chung với hàng xóm lâu dài.')])],
         lesson='Nhãn hữu cơ dựa trên sự thật của từng luống: ghi nhật ký, tách lô bị ảnh hưởng và nói rõ với khách.'),
    dict(id='FA-S03', title='Quán chay muốn nhãn hữu cơ, nhưng tuần này đã bón NPK', npc=6, tone='tense', min_day=3,
         opening='Anh Phong gọi gấp: “Mai quán có đoàn khách, em giao 10 bó rau muống hữu cơ nha, dán QR như mọi khi.”',
         facts=[dict(id='diary', title='Nhật ký canh tác', source='Sổ nông trại', text='Ba ngày trước luống rau muống đã bón NPK vì cây còi — nhật ký ghi rõ.'),
                dict(id='other', title='Luống khác', source='Vườn', text='Chỉ còn 4 bó rau muống hữu cơ từ luống chưa dùng hóa chất.'),
                dict(id='partner', title='Nông trại bạn', source='Chú Tám', text='HTX có một vườn hữu cơ được chứng nhận, còn 6 bó.')],
         options=[dict(id='truth', label='Nói thật: chỉ có 4 bó hữu cơ, gom thêm 6 bó từ vườn hữu cơ của HTX (ghi rõ nguồn)', requires=['diary', 'other', 'partner'], cost=10, quality='good', stars=5,
                       review='Nông trại nói thật và còn tìm nguồn hữu cơ thay thế có ghi nguồn. Đối tác đáng tin.',
                       outcome='Đoàn khách có đủ rau, QR ghi rõ hai nguồn. Anh Phong ký thêm hợp đồng tháng sau.',
                       perspectives=[dict(who='Anh Phong', emoji='🥗', text='Tôi cần nhà vườn nói thật hơn là nói “có”.'),
                                     dict(who='Chú Tám', emoji='👨‍🌾', text='HTX là để đỡ nhau những lúc thế này.')]),
                  dict(id='lie', label='Dán nhãn hữu cơ cho cả 10 bó, “ai mà biết”', quality='bad', stars=1, cost=30,
                       review='QR nhật ký ghi bón NPK mà nhãn ghi hữu cơ. Chấm dứt hợp đồng.',
                       outcome='Khách của quán quét QR thấy dòng “bón NPK”. Quán trả hàng, nông trại mất hợp đồng (phạt 30 xu).',
                       perspectives=[dict(who='Anh Phong', emoji='😡', text='QR là để khách tin, không phải để trang trí.'),
                                     dict(who='Khách của quán', emoji='📱', text='Quét QR mới thấy ghi bón phân hóa học. Thất vọng.')]),
                  dict(id='plain', label='Giao 10 bó nhãn thường, giảm giá, để quán tự quyết', requires=['diary'], quality='ok', stars=3,
                       review='Nói thật là tốt, nhưng tôi cần rau hữu cơ chứ không cần rau rẻ.',
                       outcome='Quán dùng 4 bó hữu cơ cho món chính, rau thường cho nhân viên ăn.',
                       perspectives=[dict(who='Anh Phong', emoji='😐', text='Ít ra em không lừa anh.')])],
         lesson='Nhãn hữu cơ phải khớp nhật ký canh tác; thiếu hàng thì nói thật và tìm nguồn có ghi rõ.'),
    dict(id='FA-S04', title='Bão sắp vào: thu sớm hay chờ?', npc=0, tone='tense', min_day=3,
         opening='Đài báo áp thấp nhiệt đới, tối mai mưa to gió giật. Cà chua còn 2 ngày nữa mới chín đỏ.',
         facts=[dict(id='forecast', title='Dự báo', source='Đài phát thanh xã', text='Mưa 100–150 mm, gió giật cấp 7 từ tối mai.'),
                dict(id='tomato', title='Tình trạng cà chua', source='Vườn', text='Trái đã chuyển hồng; hái sớm vẫn chín tiếp trong nhà nhưng xuống loại B.'),
                dict(id='net', title='Lưới che và cọc', source='Kho', text='Có đủ cọc tre và lưới để gia cố hai luống.')],
         options=[dict(id='mix', label='Hái trái đã chuyển màu, gia cố cọc và khơi rãnh cho phần còn lại', requires=['forecast', 'tomato', 'net'], cost=10, quality='good',
                       outcome='Sau bão, luống gia cố đứng vững; trái hái sớm chín trong nhà, bán loại B nhưng không mất trắng.',
                       perspectives=[dict(who='Chú Tám', emoji='👨‍🌾', text='Không ai thắng được bão, chỉ giảm thiệt hại thôi.'),
                                     dict(who='Lực (phụ vườn)', emoji='💪', text='Khơi rãnh cả chiều mệt nhưng sáng ra đất không úng.')]),
                  dict(id='all', label='Hái sạch cả vườn, kể cả trái xanh', requires=['forecast'], quality='ok',
                       outcome='Không sợ bão nhưng nửa số trái xanh không chín được, phải bỏ.',
                       perspectives=[dict(who='Chị Hạnh', emoji='👩‍🍳', text='Cà chua xanh thì bếp tôi không dùng được.')]),
                  dict(id='wait', label='Tin là bão đổi hướng, không làm gì', quality='bad', cost=30,
                       outcome='Gió quật đổ giàn, cà chua rụng dập, luống úng nước (thiệt hại 30 xu).',
                       perspectives=[dict(who='Chú Tám', emoji='😔', text='Nhà nông mà không nghe dự báo là liều.')])],
         lesson='Trước thời tiết xấu: thu phần đủ điều kiện, gia cố phần còn lại, lo thoát nước.'),
    dict(id='FA-S05', title='Mùa thu hoạch mà không thuê được người', npc=0, tone='gentle', min_day=4,
         opening='Ba luống chín cùng lúc, hai người làm thời vụ quen xin nghỉ đi làm khu công nghiệp.',
         facts=[dict(id='wage', title='Tiền công', source='Chú Tám', text='Khu công nghiệp trả lương tháng ổn định; công hái rau thì theo ngày, lúc có lúc không.'),
                dict(id='students', title='Sinh viên nông nghiệp', source='Trường gần đó', text='Khoa nông học cần chỗ thực tập, sinh viên muốn học thật việc vườn.'),
                dict(id='share', title='Đổi công', source='HTX', text='HTX có nhóm “đổi công”: hôm nay giúp vườn này, mai vườn kia giúp lại.')],
         options=[dict(id='swap', label='Tham gia đổi công với HTX và nhận hai sinh viên thực tập có hướng dẫn, trả công đàng hoàng', requires=['share', 'students'], cost=20, quality='good',
                       outcome='Rau được thu kịp; sinh viên học được cách phân loại và ghi nhật ký.',
                       perspectives=[dict(who='Sinh viên thực tập', emoji='🎓', text='Được làm thật, được trả công và được chỉ dạy.'),
                                     dict(who='Chú Tám', emoji='👨‍🌾', text='Đổi công là cách ông bà mình làm từ xưa.')]),
                  dict(id='unpaid', label='Nhận sinh viên “thực tập” không trả công, bắt làm cả ngày', requires=['students'], quality='bad',
                       outcome='Sinh viên nghỉ sau hai ngày, trường gạch tên nông trại khỏi danh sách thực tập.',
                       perspectives=[dict(who='Sinh viên thực tập', emoji='😓', text='Tụi em đi học chứ không phải làm không công.'),
                                     dict(who='Giáo viên hướng dẫn', emoji='📋', text='Thực tập phải có người hướng dẫn và chế độ rõ ràng.')]),
                  dict(id='alone', label='Tự làm, bỏ bớt một luống', quality='ok',
                       outcome='Kịp hai luống, luống thứ ba già quá lứa phải dọn làm phân.',
                       perspectives=[dict(who='Bạn', emoji='😮‍💨', text='Một người không thể làm việc của ba người.')])],
         lesson='Thiếu người mùa vụ: hợp tác, đổi công và đối xử công bằng với người làm cùng.'),
    dict(id='FA-S06', title='Có nên vào hợp tác xã?', npc=0, tone='gentle', min_day=4,
         opening='Chú Tám mời nông trại vào HTX rau an toàn: có hợp đồng siêu thị, nhưng phải theo quy trình chung và ghi nhật ký chuẩn.',
         facts=[dict(id='benefit', title='Lợi ích', source='Chú Tám', text='HTX mua chung hạt giống, phân bón giá sỉ; có đầu ra siêu thị ổn định.'),
                dict(id='rule', title='Quy định', source='Điều lệ HTX', text='Mỗi thành viên phải ghi nhật ký, chịu kiểm tra ngẫu nhiên; vi phạm là cả tổ mất hợp đồng.'),
                dict(id='fee', title='Phí', source='Điều lệ HTX', text='Góp vốn 30 xu, trích 5% doanh thu qua HTX cho quỹ chung.')],
         options=[dict(id='join', label='Tham gia, cam kết ghi nhật ký chuẩn và góp vốn', requires=['benefit', 'rule', 'fee'], cost=30, reward=20, quality='good',
                       outcome='Nông trại có đầu ra ổn định; lần đầu được siêu thị kiểm tra, nhật ký đầy đủ nên đạt.',
                       perspectives=[dict(who='Chú Tám', emoji='👨‍🌾', text='Một cây làm chẳng nên non.'),
                                     dict(who='Siêu thị', emoji='🏬', text='Chúng tôi cần nguồn hàng có hồ sơ, ổn định cả năm.')]),
                  dict(id='free', label='Vào HTX nhưng tính “làm cho có”, không ghi nhật ký', requires=['benefit'], cost=30, quality='bad',
                       outcome='Lần kiểm tra đầu tiên nông trại thiếu nhật ký, cả tổ bị nhắc nhở. Mất lòng các thành viên.',
                       perspectives=[dict(who='Thành viên HTX', emoji='😠', text='Một người làm ẩu, cả tổ chịu chung.')]),
                  dict(id='stay', label='Chưa vào, giữ bán lẻ tự do', quality='ok',
                       outcome='Tự do quyết giá, nhưng mùa rộ vẫn bị thương lái ép.',
                       perspectives=[dict(who='Anh Tuấn', emoji='🚚', text='Vườn lẻ thì dễ mua giá mềm.')])],
         lesson='Hợp tác xã mạnh khi từng thành viên giữ quy trình chung; lợi ích đi kèm trách nhiệm.'),
    dict(id='FA-S07', title='Lớp của bé Mít tới tham quan', npc=4, tone='gentle', min_day=2,
         opening='Cô giáo dẫn 20 bạn nhỏ lớp bé Mít tới tham quan nông trại. Ai cũng muốn ôm gà và hái cà chua.',
         swap='Bạn là Mít: lần đầu thấy gà đẻ trứng, muốn cầm con gà mái to nhất.',
         facts=[dict(id='chem', title='Kho thuốc', source='Kho', text='Tủ thuốc trừ sâu hóa học có khóa, nhưng hôm qua vừa phun luống 4.'),
                dict(id='hens', title='Đàn gà', source='Chuồng', text='Gà mái dễ hoảng khi bị rượt; trẻ cần rửa tay sau khi chạm gà.'),
                dict(id='time', title='Thời gian', source='Cô giáo', text='Đoàn ở 90 phút, các bạn thích được tự tay làm.')],
         options=[dict(id='safe', label='Chia nhóm, rào luống vừa phun, cho các bạn gieo hạt, nhặt trứng có hướng dẫn và rửa tay', requires=['chem', 'hens'], cost=8, quality='good', stars=5,
                       review='Con được tự gieo hạt rau muống và nhặt trứng!!! Nông trại xịn xò nhất 🐔✨',
                       outcome='Các bạn mang về chậu rau tự gieo. Phụ huynh gửi lời cảm ơn vì an toàn và bổ ích.',
                       perspectives=[dict(who='Bé Mít', emoji='🧒', text='Con biết trứng phải lau khô chứ không rửa nước nha!'),
                                     dict(who='Cô giáo', emoji='👩‍🏫', text='Chia nhóm, có rào chắn, có rửa tay — tôi yên tâm.'),
                                     dict(who='Đàn gà', emoji='🐔', text='Cục tác! Không ai rượt tụi tui, cảm ơn.')]),
                  dict(id='free', label='Cho các bạn tự do chạy khắp vườn cho vui', quality='bad', stars=2,
                       review='Vui nhưng một bạn chạy vào luống mới phun thuốc, cô giáo lo quá.',
                       outcome='Một bạn giẫm vào luống vừa phun, phải rửa tay chân và về sớm. Gà hoảng, mai đẻ ít.',
                       perspectives=[dict(who='Cô giáo', emoji='😰', text='Nông trại cần khu vực an toàn cho trẻ.'),
                                     dict(who='Bé Mít', emoji='😢', text='Bạn con bị mắng, cả lớp về sớm.')]),
                  dict(id='talk', label='Chỉ đứng giới thiệu, không cho các bạn chạm vào gì', quality='ok', stars=3,
                       review='An toàn nhưng tụi con chỉ đứng nghe thôi, hơi chán 🥲',
                       outcome='Buổi tham quan an toàn nhưng các bạn nhỏ không nhớ được gì nhiều.',
                       perspectives=[dict(who='Cô giáo', emoji='👩‍🏫', text='An toàn rồi, giá mà các con được làm thử.')])],
         lesson='Đón trẻ em: an toàn trước (khu vực thuốc, vệ sinh), rồi cho các em tự tay trải nghiệm.'),
    dict(id='FA-S08', title='Một con gà ủ rũ, bỏ ăn', npc=5, tone='tense', min_day=3,
         opening='Sáng nay một con gà mái đứng ủ rũ, xù lông, bỏ ăn. Bà Năm đang chờ lấy 30 trứng.',
         facts=[dict(id='sign', title='Triệu chứng', source='Chuồng', text='Gà xù lông, mắt lim dim, phân loãng; các con khác vẫn ăn bình thường.'),
                dict(id='vet', title='Thú y xã', source='Chú Tám', text='Cán bộ thú y xã có thể ghé khám trong buổi chiều (phí 12 xu).'),
                dict(id='eggs', title='Trứng hôm nay', source='Ổ đẻ', text='Trứng của con gà bệnh nằm chung ổ với các con khác.')],
         options=[dict(id='isolate', label='Cách ly con gà bệnh, gọi thú y, sát trùng chuồng, báo bà Năm giao trễ một ngày', requires=['sign', 'vet', 'eggs'], cost=12, quality='good', stars=4,
                       review='Giao trễ một ngày nhưng nói rõ lý do, trứng sạch. Được.',
                       outcome='Thú y xác định gà bị tiêu chảy do thức ăn ẩm; cả đàn khỏe lại sau ba ngày.',
                       perspectives=[dict(who='Bà Năm', emoji='👵', text='Trễ một ngày còn hơn trứng không sạch.'),
                                     dict(who='Cán bộ thú y', emoji='🩺', text='Cách ly sớm là cách tốt nhất để cả đàn không lây.')]),
                  dict(id='sell', label='Cứ giao trứng như bình thường, chắc không sao', quality='bad', stars=2, cost=20,
                       review='Mấy quả trứng dính bẩn, lòng đỏ lạ. Tôi không yên tâm.',
                       outcome='Bệnh lan sang ba con khác, trứng giảm hẳn một tuần (thiệt hại 20 xu).',
                       perspectives=[dict(who='Bà Năm', emoji='😟', text='Làm bánh cho người ta ăn, tôi cần nguồn trứng sạch.'),
                                     dict(who='Đàn gà', emoji='🐔', text='Khụ khụ…')]),
                  dict(id='drug', label='Tự mua kháng sinh trộn vào cám cả đàn', requires=['sign'], cost=8, quality='ok', stars=3,
                       review='Nghe nói gà đang uống thuốc, trứng có an toàn không?',
                       outcome='Gà đỡ bệnh, nhưng trứng phải bỏ trong thời gian ngừng thuốc; Bà Năm tìm nguồn khác vài hôm.',
                       perspectives=[dict(who='Cán bộ thú y', emoji='🩺', text='Dùng thuốc phải có chỉ định và tuân thủ thời gian ngừng thuốc trước khi bán trứng.')])],
         lesson='Vật nuôi bệnh: cách ly, hỏi thú y, sát trùng — và nói thật với khách về đơn hàng bị ảnh hưởng.'),
]

# ---------------------------------------------------------------- v0.5 surprises
# People: 0 Chú Tám, 1 Chị Hạnh, 2 Cô Hai, 3 Anh Tuấn, 4 Bé Mít, 5 Bà Năm, 6 Anh Phong.
EVENTS = [
    dict(id='FE-PUMP', title='Trạm bơm HTX cúp nước', emoji='🚱', npc=0, min_day=2, at='any', mods=('sun', 'hot', 'wind', 'cloud'),
         text='Chú Tám gọi: “Trạm bơm cháy mô-tơ rồi con, hôm nay van tưới cả vườn không có nước đâu. Tính sao?”',
         options=[dict(id='truck', label='Gọi xe bồn chở nước tới', hint='Mỗi luống +20% độ ẩm ngay.',
                       effects=dict(money=-12, moist=20, mark='nopump'), good=True, outcome='Xe bồn xả nước vào bể, cả vườn được một trận tưới đẫm.'),
                  dict(id='bucket', label='Gánh nước giếng tưới từng luống', hint='Mỏi vai, khách chờ lâu hơn; tưới từng luống vẫn được.',
                       effects=dict(patience=-8, mark='nopump'), good=None, outcome='Vai mỏi nhừ, nhưng luống nào khô cũng sẽ có nước giếng.'),
                  dict(id='wait', label='Chờ sửa bơm, để đất tự lo', effects=dict(moist=-10, mark='nopump'), good=False,
                       outcome='Nắng hút ẩm, mấy luống bắt đầu héo lá.')],
         default='wait'),
    dict(id='FE-STORM', title='Giông lốc kéo tới', emoji='⛈️', npc=0, min_day=3, tone='tense', mods=('hot', 'rain', 'wind', 'cloud'),
         text='Trời tối sầm, loa xã báo giông lốc trong một giờ tới. Giàn cà chua, dưa leo cao là dễ đổ nhất.',
         options=[dict(id='stake', label='Chằng cọc, căng lưới chắn gió', hint='Tốn tiền lưới và công, giữ được giàn.',
                       effects=dict(money=-10, patience=-5, moist=15), good=True, outcome='Giông qua, giàn vẫn đứng vững; chỉ rách vài lá.'),
                  dict(id='drain', label='Khơi rãnh sẵn, chấp nhận giàn nghiêng', hint='Không tốn xu, thiệt hại vừa phải.',
                       effects=dict(patience=-5, storm=1), good=None, outcome='Rãnh thoát nước kịp khơi xong trước cơn giông.'),
                  dict(id='pray', label='Mặc kệ, chắc giông tạt qua thôi',
                       luck=dict(p=0.35, win=dict(outcome='Giông tạt qua xã bên. Hú hồn!', good=None),
                                 lose=dict(effects=dict(storm=2), outcome='Giông quật thẳng qua vườn.', good=False)))],
         default='pray'),
    dict(id='FE-PESTS', title='Sâu khoang bùng phát khắp xóm', emoji='🐛', npc=0, min_day=2,
         text='Chú Tám: “Mấy vườn quanh đây sâu khoang nở rộ, đêm qua bướm bay vô đèn cả đàn. Vườn mình chắc cũng dính.”',
         options=[dict(id='trap', label='Treo bẫy đèn, bẫy pheromone quanh vườn', hint='Chặn bướm đẻ trứng từ đầu.',
                       effects=dict(money=-8), good=True, outcome='Bẫy bắt được cả đàn bướm, sâu non không kịp nở.'),
                  dict(id='scout', label='Thăm từng luống, sâu tới đâu xử lý tới đó', hint='Không tốn xu, nhưng phải đi thăm đồng.',
                       effects=dict(pests=1), good=None, outcome='Sâu đã lẻn vào vườn.'),
                  dict(id='chem', label='Phun thuốc hóa học ngừa cả vườn cho chắc', hint='Sạch sâu, nhưng mất chuẩn hữu cơ và phải cách ly.',
                       effects=dict(money=-6, chemall=True), good=False, outcome='Cả vườn sạch sâu.')],
         default='scout'),
    dict(id='FE-AUDIT', title='Đoàn kiểm tra hữu cơ đột xuất', emoji='📋', npc=0, min_day=3, tone='tense', no_mark='audit_due',
         text='Hai cán bộ chứng nhận hữu cơ tới không báo trước: “Cho chúng tôi xem nhật ký canh tác và kho mát.”',
         options=[dict(id='open', label='Mở sổ nhật ký, dẫn đoàn đi xem kho mát', hint='Kho còn lô chưa hết cách ly là bị lập biên bản.',
                       effects=dict(audit=True), good=True, outcome='Đoàn đối chiếu nhật ký với từng luống.'),
                  dict(id='later', label='Xin hẹn hôm khác vì đang bận giao hàng',
                       effects=dict(mark='audit_due', review=[3, 'Nông trại xin hoãn kiểm tra. Hữu cơ thật thì cứ mở cửa cho kiểm.']), good=None,
                       outcome='Đoàn ghi “cơ sở xin hoãn” và sẽ quay lại bất ngờ.'),
                  dict(id='gift', label='Dúi phong bì “bồi dưỡng” cho đoàn',
                       effects=dict(fine=20, mark='audit_due', review=[1, 'Nông trại đưa phong bì cho đoàn kiểm tra. Nhãn hữu cơ kiểu này ai dám tin.']),
                       good=False, outcome='Đoàn trả lại phong bì, lập biên bản hành vi đưa tiền và hẹn kiểm tra lại.')],
         default='later'),
    dict(id='FE-AUDIT2', title='Đoàn kiểm tra quay lại', emoji='📋', npc=0, min_day=4, tone='tense', need_mark='audit_due', weight=3,
         text='Đoàn chứng nhận hữu cơ quay lại như đã hẹn: “Lần này mời nông trại mở sổ và kho mát.”',
         options=[dict(id='open', label='Mở sổ, dẫn đoàn đi xem kho mát', effects=dict(audit=True, unmark='audit_due'), good=True,
                       outcome='Đoàn đối chiếu nhật ký với từng luống.'),
                  dict(id='refuse', label='Từ chối cho kiểm tra',
                       effects=dict(fine=15, unmark='audit_due', review=[1, 'Từ chối kiểm tra hai lần. Tạm treo giấy chứng nhận hữu cơ.']),
                       good=False, outcome='Đoàn lập biên bản từ chối kiểm tra.')],
         default='refuse'),
    dict(id='FE-HTX', title='HTX cần hàng gấp cho siêu thị', emoji='🤝', npc=0, min_day=2, weight=2,
         text='Chú Tám gọi: “Siêu thị đặt gấp một lô rau loại A, HTX đang thiếu. Nông trại góp một phần trước khi khép ca nha.”',
         options=[dict(id='full', label='Nhận đủ phần góp', effects=dict(pledge=1), good=True,
                       outcome='Đã hứa với HTX. Vào tab 📈 Chợ để giao phần góp trước khi khép ca.'),
                  dict(id='half', label='Nhận một nửa cho chắc', effects=dict(pledge=2), good=None,
                       outcome='Đã hứa góp một nửa. Vào tab 📈 Chợ để giao trước khi khép ca.'),
                  dict(id='no', label='Hẹn dịp khác', effects={}, good=None, outcome='Chú Tám gọi vườn khác.')],
         default='no'),
    dict(id='FE-FOX', title='Chồn mò vào chuồng gà', emoji='🦊', npc=0, min_day=3, at='any', tone='tense', no_mark='fence',
         text='Sáng ra thấy lông gà vương vãi, lưới chuồng bị khoét một lỗ to. Đêm nay chồn chắc chắn quay lại.',
         options=[dict(id='fence', label='Vá lưới, gắn đèn cảm biến', hint='Chắc ăn, dùng được lâu dài.',
                       effects=dict(money=-10, mark='fence'), good=True, outcome='Đêm đó chồn lảng vảng rồi bỏ đi. Chuồng giờ kín.'),
                  dict(id='trap', label='Đặt lồng bẫy mồi trứng',
                       luck=dict(p=0.5, win=dict(outcome='Bẫy được con chồn, nhờ kiểm lâm thả về rừng xa.', good=True),
                                 lose=dict(effects=dict(fox=1), outcome='Chồn ăn mồi rồi chui lỗ cũ.', good=False))),
                  dict(id='later', label='Để tối rồi tính', effects=dict(fox=1), good=False, outcome='Đêm đó chồn quay lại thật.')],
         default='later'),
    dict(id='FE-GOATS', title='Dê nhà bên sổng chuồng', emoji='🐐', npc=0, min_day=2,
         text='Ba con dê nhà ông Sáu phá rào, đang gặm ngon lành luống rau lá của bạn!',
         options=[dict(id='lead', label='Lùa dê về, nhờ ông Sáu sửa chuồng', hint='Mất chút thời gian, giữ hòa khí.',
                       effects=dict(patience=-5, goat=10, money=6), good=True, outcome='Ông Sáu rối rít xin lỗi, gửi 6 xu tiền rau.'),
                  dict(id='claim', label='Giữ dê lại, đòi đền cho đủ',
                       luck=dict(p=0.5, win=dict(effects=dict(goat=10, money=15), outcome='Ông Sáu đền sòng phẳng 15 xu.', good=True),
                                 lose=dict(effects=dict(goat=10, review=[2, 'Hàng xóm với nhau mà giữ dê đòi tiền, căng quá.']),
                                           outcome='Hai nhà to tiếng, ông Sáu không đền đồng nào.', good=False))),
                  dict(id='shoo', label='Đuổi đại cho nhanh', effects=dict(goat=25), good=False, outcome='Dê hoảng, chạy loạn khắp vườn rồi mới chịu ra.')],
         default='shoo'),
    dict(id='FE-SEEDS', title='Người bán giống dạo', emoji='🎒', npc=0, min_day=2,
         text='Một người chạy xe máy chở bao hạt giống: “Rau muống lai F1 siêu nhanh, gói 2 xu thôi, ngoài tiệm 3 xu!” Bao bì không nhãn, không ngày.',
         options=[dict(id='buy', label='Mua 3 gói cho rẻ', effects=dict(money=-6),
                       luck=dict(p=0.3, win=dict(effects=dict(stock={'seed_muong': 3}), outcome='May quá, hạt nảy mầm đều!', good=None),
                                 lose=dict(outcome='Hạt lép, gieo thử không lên cây nào. Mất tiền còn mất công.', good=False))),
                  dict(id='ask', label='Gọi hỏi chú Tám trước', effects=dict(patience=-3, xp=6), good=True,
                       outcome='Chú Tám: “Giống không nhãn mác là giống trôi nổi, đừng ham rẻ.” Người bán vội chạy đi.'),
                  dict(id='no', label='Không mua', effects={}, good=None, outcome='Người bán chạy sang vườn khác.')],
         default='no'),
    dict(id='FE-HEAT', title='Nắng nóng bất thường', emoji='🥵', npc=0, min_day=2, mods=('hot', 'sun'),
         text='Mới 10 giờ, nhiệt kế ngoài hiên đã chỉ 38°C. Lá rau bắt đầu rũ xuống.',
         options=[dict(id='net', label='Căng lưới cắt nắng', effects=dict(money=-8), good=True, outcome='Dưới lưới mát hẳn, rau đứng lá lại.'),
                  dict(id='soak', label='Tưới đẫm cả vườn ngay', effects=dict(patience=-5, moist=10), good=None, outcome='Đất đẫm nước, trưa nắng vẫn hút bớt.'),
                  dict(id='none', label='Để vậy, chiều tưới bù', effects=dict(moist=-15, stress=4), good=False, outcome='Rau héo rũ tới chiều, cây chững lại.')],
         default='none'),
    dict(id='FE-BEES', title='Người nuôi ong xin đặt thùng', emoji='🐝', npc=0, min_day=3,
         text='Anh Lâm nuôi ong xin đặt năm thùng ong cạnh vườn hai hôm: “Ong thụ phấn cho cà chua, dưa leo đậu trái. Chỉ xin đừng phun thuốc hóa học.”',
         options=[dict(id='yes', label='Đồng ý, hứa không phun thuốc hóa học', hint=f'Phun thuốc lúc ong ở đây là phải đền {BEE_FINE} xu.',
                       effects=dict(pollinate=10, mark='bees'), good=True, outcome='Ong bay rì rào quanh vườn.'),
                  dict(id='fee', label='Đồng ý nếu anh trả 6 xu tiền đất', effects=dict(money=6, pollinate=10, mark='bees'), good=None,
                       outcome='Anh Lâm hơi ngần ngừ rồi cũng trả.'),
                  dict(id='no', label='Từ chối, vườn còn cần phun thuốc', effects={}, good=None, outcome='Anh Lâm chở thùng ong sang đồi bên.')],
         default='no'),
    dict(id='FE-TRADER', title='Thương lái hỏi mua sạch kho mát', emoji='🚚', npc=3, min_day=3, need_mark='ctx',
         text='Anh Tuấn: “Rau trong kho mát em có bao nhiêu anh lấy hết, trả tiền mặt liền!”',
         options=[dict(id='all', label='Bán hết cho nhanh', hint='55% giá chợ lẻ, kho trống ngay.', effects=dict(bulk=55), good=None,
                       outcome='Anh Tuấn khuân rau lên xe.'),
                  dict(id='haggle', label='Trả giá lên 70%',
                       luck=dict(p=0.45, win=dict(effects=dict(bulk=70), outcome='Anh Tuấn gãi đầu rồi gật.', good=True),
                                 lose=dict(outcome='Anh Tuấn lắc đầu: “Chỗ khác bán rẻ hơn.” rồi chạy đi.', good=None))),
                  dict(id='no', label='Giữ hàng cho khách quen', effects={}, good=None, outcome='Anh Tuấn chạy sang vườn bên.')],
         default='no'),
]
TALL = ('tomato', 'cucumber')
LEAFY = ('muong', 'lettuce', 'herbs')


def _planted(d: dict) -> list:
    return [p for p in d['plots'] if p['crop']]


def _htx_offer(c: dict, d: dict) -> dict:
    """The crop the farm can best supply today (cold-room grade A + plots at harvest)."""
    level = kit.level(c)
    best = None
    for crop in CROPS:
        if crop['unlock'] > level:
            continue
        have = sum(l['qty'] for l in d['cold'] if l['crop'] == crop['id'] and l['grade'] == 'A' and not l['unsafe'] and l['expires'] >= c['day'])
        soon = sum(crop['yield_'] for p in d['plots'] if p['crop'] == crop['id'] and YOUNG <= p['growth'] < OVER)
        if best is None or have + soon > best[0]:
            best = (have + soon, crop)
    units, crop = best
    return dict(crop=crop['id'], qty=max(4, min(10, units)), price=PRICES[crop['id']])


def _trader_units(c: dict, d: dict) -> int:
    return sum(l['qty'] for l in d['cold'] if l['crop'] != 'egg' and not l['unsafe'] and l['expires'] >= c['day'])


def _attach(c: dict, d: dict) -> None:
    ev = d['desk']['ev']
    if ev is None or 'offer' in ev:
        return
    if ev['script'] == 'FE-HTX':
        ev['offer'] = _htx_offer(c, d)
    elif ev['script'] == 'FE-TRADER':
        ev['offer'] = dict(units=_trader_units(c, d))


def _maybe_trader(s: dict, c: dict, d: dict) -> None:
    """A full cold room after a harvest may bring the trader round (once a day)."""
    if c['day'] < 3 or _trader_units(c, d) < 16:
        return
    if any(h['script'] == 'FE-TRADER' and h['day'] == c['day'] for h in d['desk']['log']):
        return
    if kit.rng(ID, 'trader', c['day'], c['turn']).random() >= 0.35:
        return
    desk = d['desk']
    x = kit.desk_script(EVENTS, 'FE-TRADER')
    desk['seq'] += 1
    desk['ev'] = dict(id=f'desk-{desk["seq"]}', script='FE-TRADER', day=c['day'], at='between')
    kit.log(s, c, 'surprise', f'{x["emoji"]} {x["title"]}', kit.npc_id(ID, x['npc']), desk['ev']['id'])


def _kill_bees(s: dict, c: dict, d: dict, pid: str) -> str:
    d['desk']['marks'].pop('bees', None)
    fine = min(BEE_FINE, c['money'])
    if fine:
        kit.money(s, c, -fine, 'Đền thùng ong chết vì thuốc', pid, 'fine')
    kit.review(s, c, kit.npc_id(ID, 0), 1, 'Đã hứa với người nuôi ong mà vẫn phun thuốc hóa học, ong chết cả đàn. Làm nông phải giữ chữ tín.', pid)
    return f' 🐝 Ong của anh Lâm chết hàng loạt: đền {fine} xu, anh ấy dọn thùng đi ngay.'


def _settle_pledge(s: dict, c: dict, d: dict) -> str | None:
    pl = d['pledge']
    if pl is None:
        return None
    d['pledge'] = None
    if pl['day'] != c['day']:
        return None
    crop = CROP_INDEX[pl['crop']]
    missing = pl['qty'] - pl['done']
    if not missing:
        kit.review(s, c, kit.npc_id(ID, 0), 5, f'Nông trại góp đủ {pl["qty"]} {crop["unit"]} {crop["name"].lower()} loại A cho siêu thị. Xã viên đáng tin!', 'htx')
        c['xp'] += 6
        return f'🤝 HTX: góp đủ {pl["qty"]}/{pl["qty"]} {crop["unit"]} {crop["name"].lower()} · +{pl["paid"]} xu'
    fine = min(missing * PLEDGE_FINE, c['money'])
    if fine:
        kit.money(s, c, -fine, f'HTX phạt thiếu {missing} {crop["unit"]} {crop["name"].lower()}', 'htx', 'fine')
    kit.review(s, c, kit.npc_id(ID, 0), 2, f'Hứa góp {pl["qty"]} {crop["unit"]} mà chỉ giao {pl["done"]}. Siêu thị trách cả HTX.', 'htx')
    return f'🤝 HTX: chỉ góp {pl["done"]}/{pl["qty"]} {crop["unit"]} {crop["name"].lower()} · phạt {fine} xu'


def _hook(s: dict, c: dict, key: str, v) -> str | None:
    d = kit.data(c)
    if key == 'moist':
        for p in d['plots']:
            p['moisture'] = _clamp(p['moisture'] + int(v))
        return f'Độ ẩm mỗi luống {"+" if v > 0 else "−"}{abs(int(v))}%.'
    if key == 'stress':
        for p in _planted(d):
            p['stress'] = min(50, p['stress'] + int(v))
        return None
    if key == 'fine':
        fine = min(int(v), c['money'])
        if fine:
            kit.money(s, c, -fine, 'Nộp phạt theo biên bản', None, 'fine')
        return f'Phạt {fine} xu.'
    if key == 'storm':
        hit = []
        for p in d['plots']:
            p['moisture'] = _clamp(p['moisture'] + 15 * int(v))
            if p['crop'] in TALL:
                p['growth'] = max(0, p['growth'] - 12 * int(v))
                p['stress'] = min(50, p['stress'] + 2 * int(v))
                hit.append(p['id'])
        return (f'Giàn ở luống {", ".join(hit)} bị quật, cây chững lại.' if hit else 'May mà vườn không có giàn cao.') + ' Đất ướt sũng, coi chừng úng.'
    if key == 'pests':
        n = 0
        for p in _planted(d):
            if p['growth'] >= 10:
                p['pests'] = min(3, p['pests'] + int(v))
                n += 1
        return f'Sâu đã vào {n} luống — thăm từng luống (🔍) để biết chỗ nào nặng rồi xử lý.' if n else 'Vườn chưa có cây lớn, sâu chưa có gì để ăn.'
    if key == 'chemall':
        n = 0
        for p in _planted(d):
            p['pests'] = p['seen'] = 0
            p['scouted'] = c['turn']
            p['organic'] = False
            p['phi'] = max(p['phi'], c['turn'] + PHI['chem'])
            _diary(d, c, p['id'], f'Phun thuốc trừ sâu hóa học phòng dịch cả vườn. Cách ly {PHI["chem"]} nhịp.')
            n += 1
        note = f'{n} luống mất chuẩn hữu cơ và phải cách ly {PHI["chem"]} nhịp.'
        if _bees(c, d):
            note += _kill_bees(s, c, d, 'P1')
        return note
    if key == 'audit':
        bad = [l for l in d['cold'] if l['unsafe']]
        early = [r for r in d['diary'] if 'VI PHẠM' in r['text'] and 0 <= c['day'] - r['day'] <= 7]
        n = len(bad) + len(early)
        if n:
            for l in bad:
                d['cold'].remove(l)
                kit.waste(c, l['crop'], min(60, l['qty']), l['qty'] * PRODUCE[l['crop']]['value'], 'Tiêu hủy theo biên bản kiểm tra')
            fine = min(40, 10 * n, c['money'])
            if fine:
                kit.money(s, c, -fine, 'Phạt vi phạm thời gian cách ly', None, 'fine')
            kit.review(s, c, kit.npc_id(ID, 0), 2, 'Đoàn kiểm tra lập biên bản: có lô thu hoạch khi chưa hết cách ly thuốc.', 'audit')
            return f'⚠️ Biên bản {n} vi phạm (lô chưa hết cách ly / thu hoạch sớm): phạt {fine} xu, lô vi phạm bị tiêu hủy.'
        kit.money(s, c, 12, 'Hỗ trợ nông trại đạt kiểm tra hữu cơ', None, 'event_income')
        kit.review(s, c, kit.npc_id(ID, 0), 5, 'Đoàn kiểm tra khen: nhật ký khớp từng luống, kho mát sạch sẽ.', 'audit')
        c['xp'] += 10
        return 'Nhật ký khớp từng luống, kho mát sạch: đoàn khen và hỗ trợ 12 xu.'
    if key == 'pledge':
        ev = d['desk']['ev'] or {}
        off = ev.get('offer') or _htx_offer(c, d)
        crop = CROP_INDEX[off['crop']]
        if d['pledge'] is not None and d['pledge']['day'] == c['day'] and d['pledge']['done'] < d['pledge']['qty']:
            return 'Phần góp trước còn chưa xong nên HTX không giao thêm.'
        qty = off['qty'] if int(v) == 1 else max(2, off['qty'] // 2)
        d['pledge'] = dict(day=c['day'], crop=crop['id'], qty=qty, done=0, price=off['price'], paid=0)
        return f'Hẹn góp {qty} {crop["unit"]} {crop["name"].lower()} loại A, {off["price"]} xu/{crop["unit"]}.'
    if key == 'fox':
        coop = d['coop']
        lost = int(coop['hens'] > 1)
        coop['hens'] -= lost
        coop['mood'] = max(MOOD_MIN, coop['mood'] + MOOD['fox'])
        coop['nest'] //= 2
        coop['stale'] = min(coop['stale'], coop['nest'])
        return (f'Mất {lost} gà mái và nửa ổ trứng. ' if lost else 'Mất nửa ổ trứng. ') + f'Có thể mua gà mái mới ({HEN_COST} xu) ở chuồng.'
    if key == 'goat':
        leafy = [p for p in d['plots'] if p['crop'] in LEAFY]
        if not leafy:
            return 'May mà vườn không có rau lá để gặm.'
        p = max(leafy, key=lambda q: (q['growth'], q['id']))
        p['growth'] = max(0, p['growth'] - int(v))
        return f'Luống {p["id"]} bị ' + ('gặm và giẫm nát cả mảng' if int(v) > 15 else 'gặm mất một khúc') + f' (độ lớn −{int(v)}).'
    if key == 'pollinate':
        tall = [p for p in d['plots'] if p['crop'] in TALL]
        for p in tall:
            p['growth'] = min(GROWTH_MAX, p['growth'] + int(v))
        return f'Hoa ở luống {", ".join(p["id"] for p in tall)} đậu trái đều hơn.' if tall else 'Vườn chưa có cà chua, dưa leo nên ong chỉ ghé chơi.'
    if key == 'bulk':
        lots = [l for l in d['cold'] if l['crop'] != 'egg' and not l['unsafe'] and l['expires'] >= c['day']]
        if not lots:
            return 'Kho mát chẳng còn rau, anh Tuấn đi tay không.'
        tenths = sum(PRICES[l['crop']] * int(v) * (B_PERCENT if l['grade'] == 'B' else 100) // 1000 * l['qty'] for l in lots)
        units = sum(l['qty'] for l in lots)
        for l in lots:
            d['cold'].remove(l)
        total = max(1, (tenths + 5) // 10)
        d['stats']['sold'] += units
        kit.money(s, c, total, f'Anh Tuấn mua sạch {units} đơn vị rau', None, 'revenue')
        return f'Bán {units} đơn vị rau · +{total} xu.'
    return None


def _decide(s: dict, c: dict, p: dict) -> dict:
    d = kit.data(c)
    kit.need(d['desk']['ev'] is not None, 'Không có chuyện nào đang chờ quyết.')
    r = kit.desk_choose(s, c, ID, d['desk'], EVENTS, p.get('option'), hook=_hook)
    last = d['desk']['last']
    if last and '⚠️' in last['outcome']:          # an honest audit can still find a violation
        last['good'] = False
        d['desk']['log'][-1]['good'] = False
        r['celebrate'] = False
    return r


def _desk_view(c: dict) -> dict:
    d = kit.data(c)
    view = kit.desk_public(d['desk'], EVENTS, ID)
    ev, raw = view['ev'], d['desk']['ev']
    off = (raw or {}).get('offer')
    if ev and off and ev['script'] == 'FE-HTX':
        crop = CROP_INDEX[off['crop']]
        half = max(2, off['qty'] // 2)
        low = _tenths(c['day'], crop['id'], 'A', 0)
        ev['text'] = (f'Chú Tám gọi: “Siêu thị đặt gấp {crop["name"].lower()} loại A, HTX đang thiếu. Nông trại góp {off["qty"]} {crop["unit"]} '
                      f'trước khi khép ca nha, giá chốt {off["price"]} xu/{crop["unit"]} (chợ sỉ hôm nay chỉ {low // 10},{low % 10}). '
                      f'Hứa rồi mà thiếu thì HTX phạt {PLEDGE_FINE} xu mỗi {crop["unit"]} đó con.”')
        for o in ev['options']:
            if o['id'] == 'full':
                o['label'], o['hint'] = f'Nhận góp {off["qty"]} {crop["unit"]} {crop["name"].lower()}', f'+{off["qty"] * off["price"]} xu nếu giao đủ'
            elif o['id'] == 'half':
                o['label'], o['hint'] = f'Nhận {half} {crop["unit"]} cho chắc', f'+{half * off["price"]} xu nếu giao đủ'
    elif ev and off and ev['script'] == 'FE-TRADER':
        ev['text'] = f'Anh Tuấn đậu xe trước cổng: “Kho mát em còn {off["units"]} đơn vị rau đúng không? Anh lấy hết, trả tiền mặt liền!”'
    return view


SPEC = dict(
    id=ID, prefix='fa_', category='outdoor',
    meta=dict(short='Nông trại rau & gà', place='Nông Trại Đồi Gió', tagline='Đất ẩm vừa tay. Rau hái đúng lứa. Nhãn nói thật.', icon='tractor',
              color='#5f8f3e', light='#eef6e0', weather='Gió đồi buổi sớm', work='Đơn hàng', station='Vườn & kho mát',
              greeting='Xem thời tiết, tưới đúng lúc, thu hoạch đúng độ chín, cho gà ăn — rồi đóng thùng giao đơn với nhãn thật lòng nhé.',
              caption='Sáu luống rau, mười con gà, một cuốn nhật ký', map_label='16 · NÔNG TRẠI ĐỒI GIÓ'),
    people=PEOPLE,
    staff=[('Lực', 'fa_field', 'Tay to, tưới đều, nhìn đất là biết khô hay ướt.', 78, 86),
           ('Xuân', 'fa_coop', 'Gà nghe tiếng là chạy lại, nhặt trứng không bể quả nào.', 72, 93),
           ('Đạt', 'fa_field', 'Nhổ cỏ nhanh như gió, có điều hơi ẩu.', 88, 74),
           ('Thu', 'fa_pack', 'Rửa, phân loại, lót thùng gọn gàng.', 75, 90)],
    roles={'fa_field': 'Phụ vườn (tưới, làm cỏ)', 'fa_coop': 'Chăm gà', 'fa_pack': 'Sơ chế & đóng thùng'},
    inventory=dict(items=ITEMS, capacity=40),
    prices=PRICES,
    tip=2,
    physical=('fa_harvest', 'fa_plant', 'fa_pack', 'fa_deliver'),
    free_actions=(),
    no_tick=('fa_label', 'fa_unpack', 'fa_decide'),
    waste_items=('muong', 'lettuce', 'tomato', 'cucumber', 'herbs', 'egg'),
    activity=('🌱', 'Vườn rau Đồi Gió', [('Phân compost', 'Hữu cơ'), ('Phân NPK', 'Hóa học · ghi nhật ký'), ('Chế phẩm neem', 'Hữu cơ'), ('Thuốc trừ sâu', 'Hóa học · ghi nhật ký')],
              ['Gieo hạt, giữ ẩm', 'Nhổ cỏ, thăm sâu', 'Thu hoạch đúng độ chín', 'Phân loại, dán nhãn thật']),
    stories=[('Luống rau của chú Tám', ('Chú Tám đứng đầu bờ, bốc nắm đất bóp thử: “Đất nói cho mình biết nó khát hay no đó con.”',
                                        'Bạn thử tưới theo độ ẩm thay vì theo giờ. Luống rau muống lên đều, không còn chỗ vàng chỗ xanh.',
                                        'Chú Tám mang tặng một bao phân compost chú tự ủ: “Đất tốt thì khỏi cần hóa chất nhiều.”')),
             ('Chuyến tham quan của lớp Mít', ('Bé Mít xin dẫn cả lớp tới coi gà đẻ trứng. Bạn rào lại luống vừa phun và chuẩn bị chỗ rửa tay.',
                                               'Hai mươi bạn nhỏ tự gieo hạt vào chậu, nhặt trứng bằng hai tay như ôm báu vật.',
                                               'Lớp gửi tặng nông trại tấm tranh vẽ đàn gà, treo ngay cửa kho mát.')),
             ('Tem QR đầu tiên', ('Anh Phong hỏi nông trại có dám in QR nhật ký lên thùng rau không.',
                                  'Bạn ghi nhật ký kỹ từng lần bón, lần phun, thời gian cách ly. Có luống phải bỏ nhãn hữu cơ vì đã dùng NPK.',
                                  'Khách của quán chay quét QR, để lại lời nhắn: “Cảm ơn vì đã nói thật cả những lần không hữu cơ.”'))],
    review_asides=['Rau còn đọng sương, giòn tan 🥬', 'Trứng sạch, không một quả nứt.', 'Nhãn QR ghi rõ từng lần bón phân, tin được!',
                   'Cà chua chín cây, thơm cả bếp.'],
    situations=SITUATIONS,
    guide='Tưới theo thời tiết → nhổ cỏ, thăm sâu → thu hoạch đúng độ chín → xếp thùng → nhãn trung thực → giao. Hàng dư đem bán sỉ ở chợ đầu mối lúc được giá.',
)
