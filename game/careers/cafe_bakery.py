"""Tiệm Bánh & Cà Phê Sớm Mai — espresso bar + bakery oven (plugin career).

The shop day (shared with the other small shops in food_service): a luck of
the day that bends the orders (heat → iced drinks, office Monday → trays to
go…), surprises that wait for a real decision, guests with personalities,
walk-in buyers who shop straight from the display case (so the case must be
kept stocked with today's bakes), a streak bonus and an end-of-day grade.
Order styles: classic tickets, "mood" orders where the guest only says how
they feel and the barista must pick the right drink (hidden until guessed),
and trays of 2–3 drinks made cup by cup and served together.

Real work of the job, at two stations:

* Quầy pha (espresso bar): take the right cup (sứ / thủy tinh / giấy mang về),
  grind the ordered beans fine, dose ~18 g, pull the shot and stop it inside
  the extraction window (real seconds: early → sour, 25–30 s → balanced, late →
  bitter; a coarse grind or a light dose makes the water rush through), steam
  milk to 55–68 °C with thin or thick foam (or pour cold over ice), swap to oat
  milk for lactose intolerance, pour latte art, lid takeaway cups.
* Lò bánh (bakery): shape croissant / bánh mì dough and let it proof (game
  turns), bake trays with real-time oven windows, stock the display case,
  handle yesterday's bread by food-safety rules (mark down or donate dry bakes
  ≤ 1 day old, never anything with sauce kept overnight), bake and cool
  sponges for birthday-cake pre-orders, frost them and write the name exactly
  as ordered.

Care from one day to the next (docs/superpowers/specs/2026-09-29-cafe-bakery-care-design.md):
Bé Men, the sourdough starter fed once a day, sets how fast the bánh mì dough
rises and whether it comes out dense; shaped dough can proof overnight in the
fridge for tomorrow (warm dough does not survive the night); the care list
names yesterday's pastries each morning; the regulars' notes card remembers
what each guest always wants.

Imperfect drinks and pastries can still be served, and the guest reacts to what
they actually got (consequences: grumble, money back, send it back, or leave;
the review names the mistake). The wrong drink, an undercooked sponge or a
misspelt cake name is handed back at once. Lactose for an intolerant customer,
caffeine for a decaf order, nuts for an allergy or milk from a sour batch that
reach the guest are safety mistakes (1 star, no pay, a complaint, an inspection).
"""
from __future__ import annotations
import copy
from ..jsoncopy import tree_copy
import unicodedata
from . import kit
from . import food_service as FS
from .. import consequences as cq

ID = 'cafe_bakery'

def _one_of(value, options, message: str):
    """kit.one_of, but a list/dict payload is a clean GameError instead of a TypeError."""
    kit.need(isinstance(value, str) and value in options, message)
    return value


# --- Espresso bar -------------------------------------------------------------
# Effective extraction seconds: <20 sour, 20–25 bright, 25–30 balanced,
# 30–35 strong, >35 bitter. Grind and dose change how fast water flows.
EXTRACT = dict(sour=20, bright=25, balanced=30, strong=35)
SHOT_CLASSES = ('sour', 'bright', 'balanced', 'strong', 'bitter')
SHOT_LABEL = dict(sour='chua gắt (chiết thiếu)', bright='hơi chua', balanced='cân bằng', strong='hơi đậm', bitter='đắng khét (chiết quá)')
GRIND = dict(fine=1.0, medium=1.6, coarse=2.4)
GRIND_LABEL = dict(fine='Mịn (espresso)', medium='Vừa (phin/pour-over)', coarse='Thô (cold brew)')
DOSE_TARGET = 18
DOSE_MIN, DOSE_MAX = 12, 24
# Milk temperature: 5 °C + 4.2 °C per second on the steam wand.
STEAM = dict(base=5.0, rate=4.2, cool=55, silky=68, hot=76)
MILK_TEX = ('cool', 'silky', 'hot', 'scalded')
MILK_TEX_LABEL = dict(cool='còn nguội', silky='mịn, 55–68 °C', hot='quá nóng, mất vị ngọt', scalded='khét sữa')
MAX_GROUPS = 2      # two group heads on the machine
MAX_WANDS = 1       # one steam wand
# Onboarding (v0.7), day one only: the machine's timer does the timing. A pull or a steam
# sent with auto=true ends at once at these marks (grind, beans, milk kind and foam still
# count as chosen). From day 2 the barista stops every shot and jug by hand.
AUTO_DAYS = 1
AUTO_SHOT = 27.5    # effective seconds, the middle of the balanced window
AUTO_MILK = 62.0    # °C, the middle of the silky window

BEANS = [
    dict(id='house', item='beans_house', name='Arabica Đồi Mây', emoji='🫘', note='Chua thanh, hậu vị sô-cô-la', unlock=1),
    dict(id='robusta', item='beans_robusta', name='Robusta Lá Chè', emoji='🟤', note='Đậm, nhiều caffeine, crema dày', unlock=1),
    dict(id='decaf', item='beans_decaf', name='Decaf Sương Sớm', emoji='🌙', note='Đã tách caffeine — cho khách kiêng', unlock=2),
]
BEAN_INDEX = {x['id']: x for x in BEANS}
MILKS = {
    'milk': dict(id='milk', item='milk', name='Sữa tươi', emoji='🥛', lactose=True, steam=True, unlock=1),
    'oat': dict(id='oat', item='oat', name='Sữa yến mạch', emoji='🌾', lactose=False, steam=True, unlock=1),
    'condensed': dict(id='condensed', item='condensed', name='Sữa đặc', emoji='🥫', lactose=True, steam=False, unlock=3),
}
DRINKS = {
    'espresso': dict(id='espresso', name='Espresso', emoji='☕', milk=False, water=False, hot_only=True, iced_only=False, foam=None, unlock=1),
    'americano': dict(id='americano', name='Americano', emoji='🥃', milk=False, water=True, hot_only=False, iced_only=False, foam=None, unlock=1),
    'latte': dict(id='latte', name='Latte', emoji='🥛', milk=True, water=False, hot_only=False, iced_only=False, foam='thin', unlock=1),
    'cappuccino': dict(id='cappuccino', name='Cappuccino', emoji='☁️', milk=True, water=False, hot_only=True, iced_only=False, foam='thick', unlock=1),
    'bacxiu': dict(id='bacxiu', name='Bạc xỉu', emoji='🧋', milk=True, water=False, hot_only=False, iced_only=True, foam=None, unlock=3),
}
CONTAINERS = {
    'mug': dict(id='mug', name='Tách sứ', emoji='☕', note='Uống nóng tại quán'),
    'glass': dict(id='glass', name='Ly thủy tinh', emoji='🥃', note='Uống đá tại quán'),
    'paper': dict(id='paper', name='Ly giấy + nắp', emoji='🥤', note='Mang về (lấy từ kho)'),
}
ARTS = [
    dict(id='heart', name='Trái tim', emoji='🤍', unlock=1),
    dict(id='rosetta', name='Lá dương xỉ', emoji='🌿', unlock=2),
    dict(id='tulip', name='Hoa tulip', emoji='🌷', unlock=3),
]
ART_INDEX = {x['id']: x for x in ARTS}

# --- Bakery -------------------------------------------------------------------
PROOF_TURNS = 3      # ready when turn >= shaped turn + 3 (two other actions in between)
OVERPROOF = 6        # baked later than ready + 6 turns → flat
COOL_TURNS = 2       # a sponge needs one quiet beat before frosting
CASE_MAX = 30        # pieces of one kind in the display case
HOT_OVEN = 3         # "the oven runs hot" surprise: every window comes 3 s sooner
BAKES = {
    'croissant': dict(id='croissant', name='Croissant bơ', emoji='🥐', proof=True, qty=6, window=(14, 20, 25),
                      recipe={'flour': 1, 'butter': 2, 'egg': 1}, allergens=['gluten', 'lactose'], fresh=0, max_age=1, donate=True, unlock=1),
    'banhmi': dict(id='banhmi', name='Bánh mì que', emoji='🥖', proof=True, qty=6, window=(12, 18, 23),
                   recipe={'flour': 2}, allergens=['gluten'], fresh=0, max_age=1, donate=True, unlock=1, starter=True),
    'cookie': dict(id='cookie', name='Cookie hạnh nhân', emoji='🍪', proof=False, qty=8, window=(8, 12, 16),
                   recipe={'flour': 1, 'butter': 1, 'sugar': 1, 'egg': 1, 'almond': 1}, allergens=['gluten', 'nuts', 'lactose'], fresh=2, max_age=3, donate=True, unlock=1),
    'bonglan': dict(id='bonglan', name='Bông lan trứng muối', emoji='🍰', proof=False, qty=6, window=(16, 22, 27),
                    recipe={'flour': 1, 'egg': 2, 'sugar': 1, 'butter': 1}, allergens=['gluten', 'lactose'], fresh=0, max_age=0, donate=False, unlock=2,
                    rule='Có sốt bơ trứng: chỉ bán trong ngày, không để qua đêm, không tặng.'),
    'sponge': dict(id='sponge', name='Cốt bông lan bánh kem', emoji='🎂', proof=False, qty=1, window=(18, 24, 30),
                   recipe={'flour': 1, 'egg': 3, 'sugar': 1}, allergens=['gluten'], fresh=0, max_age=0, donate=False, unlock=1, cake=True),
}
CASE_ITEMS = ('croissant', 'banhmi', 'cookie', 'bonglan')
DONENESS = ('pale', 'golden', 'dark', 'burnt')
LOT_Q = ('golden', 'dark', 'pale', 'flat', 'dense')
LOT_Q_LABEL = dict(golden='vàng đều', dark='hơi sậm', pale='nhạt màu', flat='xẹp vì ủ quá lâu', dense='đặc ruột vì men đói')
LOT_Q_SCORE = dict(golden=5, dark=4, pale=3, flat=3, dense=3)

# --- Care from one day to the next ----------------------------------------------
# Bé Men, the sourdough starter: fed once a day; its strength sets how fast the
# bánh mì dough rises and whether the bread comes out dense. It never dies.
STARTER_START, STARTER_MIN, STARTER_MAX = 70, 10, 100
FEED_GAIN, FEED_GAIN_HUNGRY = 20, 30     # +30 when it is hungry (< 40)
NIGHT_FED, NIGHT_UNFED = 5, 25           # overnight loss
STARTER_BANDS = [   # (from strength, id, emoji, label, proof beats, what it does)
    (80, 'strong', '💪', 'Sung sức', 2, 'bột bánh mì nở nhanh: ủ 2 nhịp'),
    (40, 'ok', '🙂', 'Ổn', 3, 'bột bánh mì nở bình thường: ủ 3 nhịp'),
    (0, 'hungry', '😴', 'Đói', 5, 'bột bánh mì nở chậm (5 nhịp), bánh ra lò đặc ruột'),
]
COLD_MAX = 2         # fridge shelves for overnight dough
COLD_NIGHTS = 2      # a chilled tray keeps for two nights
# The regulars' notes card: note 1 after the first served order, note 2 after the third.
NOTE_AT = (1, 3)
NOTES = {
    0: [dict(id='lam_shot', icon='☕', text='Espresso không đường, chiết đúng 25–30 giây — chú nếm là biết liền.'),
        dict(id='lam_mug', icon='🔥', text='Thích tách sứ hâm nóng, đứng uống ngay tại quầy rồi mới đi.')],
    1: [dict(id='thao_oat', icon='⚠️', text='Không dung nạp lactose: chỉ sữa yến mạch, tráng ca đánh sữa trước.', tone='danger'),
        dict(id='thao_time', icon='⏰', text='Rất đúng giờ, hay mang về phòng họp — đậy nắp, ghi tên lên ly.')],
    2: [dict(id='mo_sale', icon='🏷️', text='Săn bánh hôm qua −50% cuối ngày, sinh viên cuối tháng.'),
        dict(id='mo_kitchen', icon='💛', text='Hay xin bánh dư cho Bếp Cơm 0 Đồng — nhớ dán nhãn ngày ra lò.')],
    3: [dict(id='diep_foam', icon='☁️', text='Thích bọt sữa dày và hình trái tim để chụp gửi cháu.'),
        dict(id='diep_names', icon='🎂', text='Đặt bánh kem cho cả họ: đọc lại tên có dấu với cô trước khi viết.')],
    4: [dict(id='khoa_double', icon='🥃', text='Hay gọi americano ly lớn rồi ngồi làm việc cả buổi — hôm deadline là xin hai shot.'),
        dict(id='khoa_seat', icon='🔌', text='Thích ghế quầy bar sát ổ cắm, ngại gọi thêm khi đang tiết kiệm.')],
    5: [dict(id='sau_decaf', icon='⚠️', text='Bị tim: không caffeine, chỉ pha hạt decaf.', tone='danger'),
        dict(id='sau_soft', icon='🥖', text='Răng yếu: bánh mì phải mới ra lò, bánh hôm qua là bà chê.')],
    6: [dict(id='tung_rush', icon='🛵', text='Lúc nào cũng vội: đồ mang về, đậy nắp kỹ vì chạy xe.'),
        dict(id='tung_change', icon='💵', text='Hay quên tiền thừa — cất phong bì ghi tên chờ anh quay lại.')],
}
CREAMS = {
    'whipped': dict(id='whipped', name='Kem tươi', emoji='🍦', recipe={'cream': 1}),
    'butter': dict(id='butter', name='Kem bơ', emoji='🧈', recipe={'butter': 2, 'sugar': 1}),
}
COLORS = {
    'white': dict(id='white', name='Trắng sữa', hex='#fbf7ef'),
    'pink': dict(id='pink', name='Hồng phấn', hex='#f4b8c8'),
    'blue': dict(id='blue', name='Xanh da trời', hex='#a9cdea'),
    'yellow': dict(id='yellow', name='Vàng bơ', hex='#f5dc8a'),
    'mint': dict(id='mint', name='Xanh bạc hà', hex='#b9e4cf'),
}
ALLERGEN_LABEL = dict(gluten='gluten', nuts='hạt', lactose='lactose')

ITEMS = [
    dict(id='beans_house', name='Hạt Arabica Đồi Mây', emoji='🫘', group='coffee', unit='liều 18 g', cost=3, life=20, start=20),
    dict(id='beans_robusta', name='Hạt Robusta Lá Chè', emoji='🟤', group='coffee', unit='liều 18 g', cost=2, life=20, start=14),
    dict(id='beans_decaf', name='Hạt Decaf Sương Sớm', emoji='🌙', group='coffee', unit='liều 18 g', cost=4, life=20, start=6, unlock=2),
    dict(id='milk', name='Sữa tươi', emoji='🥛', group='milk', unit='ca 200 ml', cost=2, life=2, start=12, allergen='lactose'),
    dict(id='oat', name='Sữa yến mạch', emoji='🌾', group='milk', unit='ca 200 ml', cost=3, life=6, start=6),
    dict(id='condensed', name='Sữa đặc', emoji='🥫', group='milk', unit='phần', cost=1, life=30, start=6, unlock=3, allergen='lactose'),
    dict(id='cream', name='Kem tươi (whipping)', emoji='🍦', group='milk', unit='hộp', cost=5, life=3, start=4, allergen='lactose'),
    dict(id='flour', name='Bột mì', emoji='🌾', group='dry', unit='mẻ 500 g', cost=2, life=40, start=12, allergen='gluten'),
    dict(id='butter', name='Bơ lạt', emoji='🧈', group='fridge', unit='khối 100 g', cost=4, life=6, start=12, allergen='lactose'),
    dict(id='egg', name='Trứng gà', emoji='🥚', group='fridge', unit='quả', cost=1, life=8, start=18),
    dict(id='sugar', name='Đường', emoji='🍬', group='dry', unit='mẻ 100 g', cost=1, life=90, start=10),
    dict(id='almond', name='Hạnh nhân lát', emoji='🌰', group='dry', unit='phần', cost=3, life=30, start=4, allergen='nuts'),
    dict(id='cup', name='Ly giấy + nắp', emoji='🥤', group='pack', unit='bộ', cost=1, start=20),
    dict(id='bag', name='Túi giấy', emoji='🛍️', group='pack', unit='cái', cost=1, start=16),
    dict(id='cake_box', name='Hộp bánh kem + nến', emoji='📦', group='pack', unit='bộ', cost=3, start=4),
]
ITEM_INDEX = {x['id']: x for x in ITEMS}

PEOPLE = [
    ('Chú Lâm', 'Khách quen buổi sáng', 'Uống espresso không đường, nếm là đoán được shot chiết bao nhiêu giây.', 'picky'),
    ('Chị Thảo', 'Nhân viên văn phòng', 'Không dung nạp lactose, luôn gọi sữa yến mạch, rất đúng giờ.', 'bossy'),
    ('Mơ', 'Sinh viên tình nguyện', 'Săn bánh giảm giá cuối ngày, hay xin bánh cho Bếp Cơm 0 Đồng Ngõ Mây.', 'genz'),
    ('Cô Diệp', 'Hàng xóm', 'Đặt bánh kem cho cả họ, nhớ sinh nhật từng đứa cháu.', 'warm'),
    ('Anh Khoa', 'Freelancer', 'Mang laptop tới ngồi, gọi americano hai shot.', 'quiet'),
    ('Bà Sáu', 'Khách lớn tuổi', 'Mua bánh mì mỗi sáng, bánh cứng là chê liền.', 'sour'),
    ('Anh Tùng', 'Tài xế giao hàng', 'Lúc nào cũng vội, gọi đồ mang về, nói to.', 'bossy'),
]


def _o(**k):
    return k


# Deterministic order book. `day` = first game day the order can appear.
ORDERS = [
    _o(npc=0, kind='drink', title='Espresso buổi sáng của chú Lâm', drink='espresso', beans='house', size='S', iced=False, takeaway=False, milk=None, art=None, shots=1,
       note='Một shot thôi, chiết cho chuẩn nha cháu. Chú uống là biết liền.', day=1),
    _o(npc=1, kind='drink', title='Latte yến mạch nóng mang về', drink='latte', beans='house', size='L', iced=False, takeaway=True, milk='oat', lactose=True, art=None, shots=1,
       note='Chị không uống được sữa bò đâu nha, bụng chị biểu tình liền.', day=1),
    _o(npc=4, kind='drink', title='Americano đá hai shot', drink='americano', beans='robusta', size='L', iced=True, takeaway=True, milk=None, art=None, shots=2,
       note='Hai shot cho tỉnh, hôm nay anh chạy deadline.', day=1),
    _o(npc=3, kind='drink', title='Cappuccino vẽ tim và một croissant', drink='cappuccino', beans='house', size='S', iced=False, takeaway=False, milk='milk', art='heart', shots=1,
       pastry={'croissant': 1}, note='Bọt dày dày cô mới thích. Vẽ cho cô trái tim nha.', day=1),
    _o(npc=6, kind='drink', title='Latte đá mang về gấp', drink='latte', beans='robusta', size='L', iced=True, takeaway=True, milk='milk', art=None, shots=1,
       note='Anh đang chạy đơn, làm lẹ giúp anh nha.', day=1),
    _o(npc=5, kind='pastry', title='Hai ổ bánh mì mới ra lò', items={'banhmi': 2}, takeaway=True, day_old_ok=False, allergy=None,
       note='Bánh mì mới nướng nha con, bà răng yếu, bánh cứng là bà nhai không nổi.', day=1),
    _o(npc=3, kind='pastry', title='Túi cookie cho cháu nội', items={'cookie': 3}, takeaway=True, day_old_ok=False, allergy=None,
       note='Cháu cô mê cookie hạnh nhân lắm, lấy cô ba cái.', day=1),
    _o(npc=0, kind='drink', title='Espresso double của chú Lâm', drink='espresso', beans='robusta', size='S', iced=False, takeaway=False, milk=None, art=None, shots=2,
       note='Hôm nay chú mệt, cho chú hai shot Robusta.', day=2),
    _o(npc=2, kind='pastry', title='Croissant hôm qua giảm giá', items={'croissant': 2}, takeaway=True, day_old_ok=True, allergy=None,
       note='Còn croissant hôm qua giảm giá không ạ? Sinh viên cuối tháng á 🥲', day=2),
    _o(npc=4, kind='pastry', title='Hộp bánh họp nhóm, một bạn dị ứng hạt', items={'croissant': 2, 'banhmi': 2}, takeaway=True, day_old_ok=False, allergy='nuts',
       note='Nhóm anh có một bạn dị ứng hạt, đừng để dính cookie hạnh nhân nhé.', day=2),
    _o(npc=3, kind='cake', title='Bánh kem sinh nhật bé Bảo Ngọc', text='Mừng sinh nhật Bảo Ngọc', cream='whipped', color='pink',
       note='Cháu cô tên Bảo Ngọc — Ngọc có dấu nặng nha, đừng viết thiếu dấu.', day=2),
    _o(npc=5, kind='drink', title='Latte nóng không caffeine', drink='latte', beans='decaf', size='S', iced=False, takeaway=False, milk='milk', art='heart', shots=1,
       decaf=True, note='Bà bị tim, bác sĩ dặn không caffeine đó con. Đừng nhầm nha.', day=3),
    _o(npc=1, kind='cake', title='Bánh kem chúc mừng anh Hưởng', text='Chúc mừng anh Hưởng', cream='butter', color='blue',
       note='Sếp chị tên Hưởng, dấu hỏi nha em — viết thành “Hương” là chị hết đường về công ty.', day=3),
    _o(npc=1, kind='drink', title='Cappuccino yến mạch vẽ lá', drink='cappuccino', beans='house', size='S', iced=False, takeaway=False, milk='oat', lactose=True, art='rosetta', shots=1,
       note='Như cũ nha em: yến mạch, bọt dày, vẽ lá cho chị chụp hình.', day=4),
    _o(npc=6, kind='cake', title='Bánh kem kỷ niệm 5 năm cưới', text='Kỷ niệm 5 năm Tùng và Quyên', cream='whipped', color='white',
       note='Viết giúp anh “Kỷ niệm 5 năm Tùng và Quyên”, vợ anh mà thấy sai tên là anh ngủ sofa.', day=4),
    _o(npc=2, kind='drink', title='Bạc xỉu đá mang về', drink='bacxiu', beans='robusta', size='L', iced=True, takeaway=True, milk='condensed', art=None, shots=1,
       pastry={'cookie': 1}, note='Bạc xỉu ngọt ngọt với một cookie nha, học bài tới khuya luôn.', day=5),
    _o(npc=2, kind='cake', title='Bánh kem cho bạn cùng phòng Nguyệt', text='Happy birthday Nguyệt', cream='whipped', color='yellow',
       note='“Happy birthday Nguyệt” — Nguyệt có dấu nặng nha, tụi em góp tiền mua đó.', day=5),
    _o(npc=5, kind='pastry', title='Bông lan trứng muối cho hội dưỡng sinh', items={'bonglan': 3}, takeaway=True, day_old_ok=False, allergy=None,
       note='Hội dưỡng sinh của bà ăn xế, lấy ba miếng bông lan trứng muối.', day=4),
]
OPENINGS = dict(drink='Cho mình gọi đồ uống nha!', pastry='Hôm nay tủ bánh có gì ngon vậy?', cake='Mình tới hỏi bánh kem đã đặt nè.',
                mood='Hôm nay mình chưa biết gọi gì… để mình tả cho nghe nha!')
NPC_GUEST = {0: 'regular', 1: 'rush', 2: 'chatty', 3: 'generous', 4: 'plain', 5: 'picky', 6: 'rush'}
GEN = 2          # task generator version (older saved tasks are regenerated once)


def _drink(drink: str, beans: str, size: str, iced: bool, takeaway: bool, milk: str | None, art: str | None = None,
           shots: int = 1, lactose: bool = False, decaf: bool = False) -> dict:
    d = DRINKS[drink]
    return dict(drink=drink, beans=beans, size=size, iced=iced, takeaway=takeaway, milk=milk,
                foam=d['foam'] if (d['milk'] and not iced) else None, art=art, shots=shots, lactose=lactose, decaf=decaf)


# "Mood" orders: the guest only says how they feel. The drink stays hidden
# until the barista picks the right one from three (a wrong pick costs
# patience and brings a clue; after two misses the guest just says it).
MOODS = [
    dict(npc=4, day=2, title='Ly “cứu deadline” của anh Khoa',
         text='Đêm qua anh thức tới 3 giờ sáng. Cho anh thứ gì tỉnh thật nhanh, không sữa, mà ngồi nhâm nhi được cả buổi.',
         options=['espresso', 'americano', 'latte'], clue='Espresso một ngụm là hết, anh cần ly to uống cả buổi cơ. Mà không sữa nha.',
         order=_drink('americano', 'robusta', 'L', True, False, None, shots=2), note='Ly lớn, đá nhiều, hai shot cho tỉnh.'),
    dict(npc=1, day=2, title='Chị Thảo muốn “ấm bụng”',
         text='Sáng nay mưa lạnh, chị muốn gì ấm ấm, béo nhẹ, mà bụng chị không biểu tình nha.',
         options=['americano', 'latte', 'espresso'], clue='Chị muốn béo nhẹ mà — có sữa, nhưng nhớ bụng chị kén sữa bò.',
         order=_drink('latte', 'house', 'S', False, False, 'oat', lactose=True), note='Sữa yến mạch nha em, chị không dung nạp lactose.'),
    dict(npc=3, day=2, title='Ly có “mây” cho cô Diệp',
         text='Cô muốn ly nào bọt sữa dày như mây, nóng hổi, có hình vẽ xinh xinh để cô chụp gửi cháu.',
         options=['latte', 'cappuccino', 'americano'], clue='Latte bọt mỏng quá con, cô thích bọt dày cơ.',
         order=_drink('cappuccino', 'house', 'S', False, False, 'milk', art='heart'), note='Vẽ trái tim cho cô nha.'),
    dict(npc=0, day=2, title='Một ngụm của chú Lâm',
         text='Chú chỉ cần một ngụm thật đậm, thật ngắn. Không đá, không sữa, không pha nước.',
         options=['americano', 'espresso', 'cappuccino'], clue='Americano là pha thêm nước rồi cháu, chú dặn không nước mà.',
         order=_drink('espresso', 'house', 'S', False, False, None), note='Chiết chuẩn nha cháu, chú uống là biết.'),
    dict(npc=6, day=2, title='Anh Tùng giữa trưa nắng',
         text='Nắng muốn xỉu! Cho anh ly gì mát lạnh, nhiều sữa, mang đi liền nha.',
         options=['cappuccino', 'latte', 'espresso'], clue='Cappuccino chỉ uống nóng thôi em, anh cần mát lạnh.',
         order=_drink('latte', 'robusta', 'L', True, True, 'milk'), note='Mang về, đậy nắp kỹ, anh chạy xe.'),
    dict(npc=5, day=3, title='Bà Sáu thèm mùi cà phê',
         text='Bà bị tim, không uống cà phê thật được, mà thèm ly sữa nóng thơm mùi cà phê quá con.',
         options=['espresso', 'bacxiu', 'latte'], clue='Bạc xỉu thì uống đá, bà muốn sữa nóng cơ.',
         order=_drink('latte', 'decaf', 'S', False, False, 'milk', decaf=True), note='Nhớ đừng có caffeine nha con, bác sĩ dặn đó.'),
    dict(npc=2, day=3, title='Mơ ôn thi tới khuya',
         text='Tối nay em ôn thi, muốn gì ngọt ngọt mát mát, có cà phê chút xíu thôi á.',
         options=['americano', 'cappuccino', 'bacxiu'], clue='Americano đắng lắm, em muốn ngọt ngọt mát mát cơ.',
         order=_drink('bacxiu', 'robusta', 'L', True, True, 'condensed'), note='Mang về nha, em học ở thư viện.'),
]
MOOD_TIP = 3     # the guest tips when the first pick is right

# Trays: several drinks for one table, made cup by cup and served together.
TRAYS = [
    dict(npc=1, day=3, title='Khay 2 ly cho phòng họp', opening='Cho chị 2 ly mang lên phòng họp nha: ly 1 của chị, ly 2 của sếp.',
         note='Ly của chị là yến mạch nha, sếp chị uống americano đá hai shot.',
         party=[_drink('latte', 'house', 'L', False, True, 'oat', lactose=True), _drink('americano', 'robusta', 'L', True, True, None, shots=2)]),
    dict(npc=4, day=3, title='Hai ly cho bàn làm việc nhóm', opening='Nhóm anh ngồi bàn trong, cho anh 2 ly một lượt nha.',
         note='Một americano đá cho anh, một cappuccino vẽ tim cho bạn anh.',
         party=[_drink('americano', 'house', 'L', True, False, None), _drink('cappuccino', 'house', 'S', False, False, 'milk', art='heart')]),
    dict(npc=3, day=4, title='Cô Diệp dẫn cháu đi uống nước', opening='Hai bà cháu ngồi đây nha, mỗi người một ly.',
         note='Cháu cô mới 12 tuổi, ly của cháu không có caffeine nhé.',
         party=[_drink('cappuccino', 'house', 'S', False, False, 'milk', art='heart'), _drink('latte', 'decaf', 'S', False, False, 'milk', decaf=True)]),
    dict(npc=2, day=5, title='Mơ rủ bạn cùng phòng', opening='Cho tụi em 2 ly mang về kí túc xá ạ!',
         note='Em bạc xỉu, bạn em latte đá.',
         party=[_drink('bacxiu', 'robusta', 'L', True, True, 'condensed'), _drink('latte', 'house', 'L', True, True, 'milk')]),
    dict(npc=6, day=6, title='Khay 3 ly cho anh em giao hàng', opening='Cho anh 3 ly mang ra cho anh em đứng đợi đơn nha!',
         note='Hai latte đá với một americano đá hai shot, lẹ giúp anh nha.',
         party=[_drink('latte', 'robusta', 'L', True, True, 'milk'), _drink('latte', 'robusta', 'L', True, True, 'milk'),
                _drink('americano', 'robusta', 'L', True, True, None, shots=2)]),
]

MODS = [
    dict(id='normal', emoji='☀️', label='Sáng thường ngày', hint='Nhịp tiệm vừa phải, hợp để làm quen tay.', weight=3),
    dict(id='rain', emoji='🌧️', label='Mưa sáng', hint='Ai cũng muốn đồ nóng. Người trú mưa hay ghé vào gọi thêm.', min_day=2, weight=2, walkin=0.2),
    dict(id='heat', emoji='🥵', label='Nắng gắt', hint='Món nào pha đá được là khách xin đá hết.', min_day=2, weight=2),
    dict(id='exam', emoji='📚', label='Mùa thi', hint='Sinh viên ôn bài: espresso, americano đều gọi hai shot; hay mua bánh lẻ.', min_day=2, weight=2, walkin=0.2, buyers=2),
    dict(id='quiet', emoji='🍃', label='Phố vắng', hint='Ít khách, ai cũng thong thả. Tranh thủ nướng mẻ mới.', min_day=2, weight=1, patience=-1, buyers=0),
    dict(id='market', emoji='🧺', label='Chợ phiên đầu hẻm', hint='Người đi chợ ghé mua bánh lẻ liên tục — giữ tủ kính đầy bánh mới!', min_day=3, weight=2, walkin=0.15, buyers=3),
    dict(id='office', emoji='💼', label='Sáng thứ Hai văn phòng', hint='Ai cũng mang đi, hay đặt cả khay nhiều ly. Khách vội hơn.', min_day=3, weight=2, walkin=0.35, patience=1),
    dict(id='festival', emoji='🎉', label='Cuối tuần có hội', hint='Giá bán +10%. Nhiều bánh kem đặt trước, khách đi theo nhóm.', min_day=5, weight=1, walkin=0.3, patience=1, buyers=2),
]
MOD_INDEX = {m['id']: m for m in MODS}
BUYER_WANTS = dict(croissant=3, banhmi=3, cookie=2, bonglan=2)   # what walk-in buyers ask for at the case


def _level_hint(day: int) -> int:
    return 1 + (day - 1) // 2


def _style(day: int, slot: int, mod: str) -> str:
    """Which kind of order this slot is (day 1 and the first guest are plain tickets)."""
    if day <= 1 or slot == 0:
        return 'classic'
    deck = ['classic', 'classic', 'mood']
    if day >= 3:
        deck.append('tray')
    if day >= 5:
        deck += ['mood', 'classic']
    if day >= 7:
        deck.append('tray')
    if mod in ('office', 'festival') and day >= 3:
        deck.append('tray')
    if mod == 'quiet':
        deck = ['classic' if x == 'tray' else x for x in deck]
    kit.rng(ID, 'styles', day).shuffle(deck)
    return deck[(slot - 1) % len(deck)]


def _classic(day: int, slot: int, mod: str) -> dict:
    rng = kit.rng(ID, day, slot)
    pool = [o for o in ORDERS if o['day'] <= day]
    if day > 1:
        pool = pool + [o for o in pool if (mod == 'festival' and o['kind'] == 'cake') or (mod == 'market' and o['kind'] == 'pastry')
                       or (mod == 'exam' and o['npc'] == 2) or (mod == 'office' and o['kind'] == 'drink' and o['takeaway'])]
    return pool[((day - 1) * 3 + slot + rng.randrange(3)) % len(pool)]


def _twist(n: dict, title: str, mod: str) -> tuple[dict, str]:
    """The luck of the day bends a plain drink ticket a little."""
    n = dict(n)
    d = DRINKS[n['drink']]
    if mod == 'heat' and not n['iced'] and not d['hot_only']:
        n['iced'] = True
        title = title.replace('nóng', 'đá')
    elif mod == 'rain' and n['iced'] and not d['iced_only']:
        n['iced'] = False
        title = title.replace('đá', 'nóng')
    elif mod == 'exam' and n['drink'] in ('espresso', 'americano'):
        n['shots'] = 2
    elif mod == 'office':
        n['takeaway'] = True
    n['foam'] = d['foam'] if (d['milk'] and not n['iced']) else None
    return n, title


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = FS.pick_mod(ID, day, MODS)['id']
    style = _style(day, slot, mod)
    if style == 'mood':
        pool = [m for m in MOODS if m['day'] <= day]
        m = pool[kit.rng(ID, 'mood', day, slot).randrange(len(pool))]
        needs = dict(kind='drink', style='mood', **m['order'], pastry={}, note=m['note'],
                     mood=dict(text=m['text'], options=list(m['options']), clue=m['clue']))
        npc, title, opening = m['npc'], m['title'], OPENINGS['mood']
    elif style == 'tray':
        pool = [x for x in TRAYS if x['day'] <= day]
        tr = pool[kit.rng(ID, 'tray', day, slot).randrange(len(pool))]
        party = [dict(x) for x in tr['party']]
        needs = dict(kind='drink', style='tray', **party[0], pastry={}, note=tr['note'], party=party)
        npc, title, opening = tr['npc'], tr['title'], tr['opening']
    else:
        o = _classic(day, slot, mod)
        npc, title, opening = o['npc'], o['title'], OPENINGS[o['kind']]
        if o['kind'] == 'drink':
            d = DRINKS[o['drink']]
            needs = dict(kind='drink', drink=o['drink'], beans=o['beans'], size=o['size'], iced=o['iced'], takeaway=o['takeaway'],
                         milk=o['milk'], foam=d['foam'] if (d['milk'] and not o['iced']) else None, art=o['art'], shots=o['shots'],
                         lactose=bool(o.get('lactose')), decaf=bool(o.get('decaf')), pastry=dict(o.get('pastry') or {}), note=o['note'])
            if day > 1:
                needs, title = _twist(needs, title, mod)
        elif o['kind'] == 'pastry':
            needs = dict(kind='pastry', items=dict(o['items']), takeaway=o['takeaway'], day_old_ok=o['day_old_ok'], allergy=o['allergy'], note=o['note'])
        else:
            needs = dict(kind='cake', text=o['text'], cream=o['cream'], color=o['color'], note=o['note'])
        needs['style'] = 'classic'
    cups = len(needs.get('party') or [None])
    return kit.base_task(ID, day, slot, serial, npc, title, opening, needs=needs, guest=FS.guest(NPC_GUEST[npc]), gen=GEN,
                         drink=_empty_drink(), bag=_empty_bag(), cake=_empty_cake(), quoted_price=None, served=None, refused=0,
                         guessed=False, guesses=[], cur=0, cups=[None] * cups)


FIXED = ('needs', 'guest')
CORE_KEYS = ('kind', 'drink', 'beans', 'size', 'iced', 'takeaway', 'milk', 'foam', 'art', 'shots', 'lactose', 'decaf', 'pastry',
             'items', 'day_old_ok', 'allergy', 'text', 'cream', 'color')


def _specs(n: dict) -> list[dict]:
    """One recipe per cup: a tray's party list, or the order itself."""
    return n.get('party') or [n]


def _spec(t: dict, i: int | None = None) -> dict:
    """The order as seen from one cup (the active one by default)."""
    n = t['needs']
    party = n.get('party')
    if not party:
        return n
    i = t.get('cur', 0) if i is None else i
    return {**n, **party[i]}


def _tray(t: dict) -> bool:
    return bool(t['needs'].get('party'))


def _cups_total(t: dict) -> int:
    return len(_specs(t['needs']))


def _hidden(t: dict) -> bool:
    """A mood order whose drink the barista has not found yet."""
    return t['needs'].get('style') == 'mood' and not t.get('guessed')


def _empty_drink() -> dict:
    return dict(container=None, size=None, ice=False, water=False, dose=None, pulling=None, shots=[], milk=None,
                steaming=None, steam=None, art=None, lid=False, cost=0)


def _empty_bag() -> dict:
    return dict(items=[], bagged=False, has_bag=False, cost=0)


def _empty_cake() -> dict:
    return dict(baking=False, sponge=None, cool_turn=0, cream=None, color=None, melted=False, text=None, scraped=0, boxed=False, cost=0)


def initial() -> dict:
    # The 5 a.m. bake is already in the case when the first shift opens.
    case = [dict(id='open-croissant', item='croissant', qty=6, day=1, q='golden', sale=False, cost=0),
            dict(id='open-banhmi', item='banhmi', qty=8, day=1, q='golden', sale=False, cost=0),
            dict(id='open-cookie', item='cookie', qty=8, day=1, q='golden', sale=False, cost=0)]
    return dict(proof=[], oven=[], case=case, drinks=0, pastries=0, cakes=0, donated=0, markdown_sold=0, discarded=0, clean_day=0,
                counter_sold=0, regulars={}, grades=[], ev_hist=[], **_care_initial())


def _care_initial() -> dict:
    return dict(starter=dict(strength=STARTER_START, fed=0, feeds=0), cold=[], book={}, night=None)


# --- old saves & the day plan -------------------------------------------------

def _core(n) -> dict:
    return {k: n.get(k) for k in CORE_KEYS} if isinstance(n, dict) else {}


def _upgrade_task(t: dict, c: dict | None) -> None:
    """A task saved by an older order generator: regenerate its fixed facts once.
    Work in progress is kept when the order itself did not change."""
    slot = int(t['id'].rsplit('-', 1)[1])
    fresh = make_task(t['day'], slot, t['created_turn'])
    same = _core(t.get('needs')) == _core(fresh['needs']) and not fresh['needs'].get('party') and fresh['needs']['style'] != 'mood'
    for k in ('npc', 'title', 'opening', 'kind', 'needs', 'guest', 'gen'):
        t[k] = copy.deepcopy(fresh[k])
    for k, v in fresh.items():
        t.setdefault(k, copy.deepcopy(v))
    t['cur'] = 0
    t['cups'] = [None] * _cups_total(t)
    t['guessed'] = False
    t['guesses'] = []
    if t['status'] not in FS.DONE and not same:
        t.update(drink=_empty_drink(), bag=_empty_bag(), cake=_empty_cake(), refused=0)
        t['quoted_price'] = quote(c, t['needs']) if c is not None else None


def _migrate(c: dict) -> dict:
    d = FS.migrate(c)
    d.setdefault('counter_sold', 0)
    for k, v in _care_initial().items():
        d.setdefault(k, v)
    for x in d['proof'] if isinstance(d.get('proof'), list) else []:
        if isinstance(x, dict):
            x.setdefault('dense', False)
    for t in c['tasks']:
        if t['career'] == ID and t.get('gen') != GEN:
            _upgrade_task(t, c)
    return d


def _plan(c: dict) -> dict:
    return FS.plan(c, ID, MODS, EVENTS)


def _peek_plan(c: dict) -> dict:
    """Read-only view of today's plan (the public projection must not write)."""
    p = kit.data(c).get('plan')
    if isinstance(p, dict) and p.get('day') == c['day']:
        return p
    return FS.new_plan(ID, c['day'], MODS, EVENTS)


def _mult(c: dict) -> float:
    return 1.1 if FS.pick_mod(ID, c['day'], MODS)['id'] == 'festival' else 1.0


def _walkin_chance(c: dict, pl: dict) -> float:
    base = MOD_INDEX[pl['mod']].get('walkin', 0.0)
    if base and c['day'] >= 4:
        base += min(0.2, 0.02 * c['day'])
    return base


SIZE_BASE = 2      # one drink with one pastry (kit.size_factor: a bigger order waits longer)
SHOP_ACTIONS = ('cb_event', 'cb_box_send', 'cb_clean', 'cb_shape', 'cb_bake', 'cb_unload', 'cb_markdown', 'cb_donate',
                'cb_discard', 'cb_feed', 'cb_chill')   # work for the shop, not for the guest on the bench


def _units(t: dict) -> int:
    """How big an order is: drinks (every cup of a tray), pastries, and a cake counts as four."""
    n = t['needs']
    if n['kind'] == 'cake':
        return 4
    if n['kind'] == 'pastry':
        return sum(n['items'].values())
    return max(1, len(n.get('party') or [])) + sum(n.get('pastry', {}).values())


def _patience_extra(c: dict, pl: dict) -> int:
    m = MOD_INDEX[pl['mod']]
    return m.get('patience', 0) + (1 if c['day'] >= 6 and m['id'] != 'quiet' else 0)


def _drain_patience(c: dict, amount: int, keep: str | None = None) -> None:
    """Waiting guests lose patience (something took the barista's time)."""
    if c['life'].get('mode') == 'calm':
        return
    for t in FS.open_tasks(c, ID):
        if t['id'] != keep:
            t['patience'] = max(25, t.get('patience', 100) - amount)


# --- pricing ------------------------------------------------------------------

def _drink_price(c: dict, n: dict) -> int:
    p = lambda k: kit.price(c, k, SPEC['prices'][k])
    return p(n['drink']) + (8 if n['size'] == 'L' else 0) + (6 if n['milk'] == 'oat' else 0) + (8 if n['shots'] == 2 else 0)


def quote(c: dict, n: dict) -> int:
    p = lambda k: kit.price(c, k, SPEC['prices'][k])
    if n['kind'] == 'drink':
        total = sum(_drink_price(c, x) for x in _specs(n))
        total += sum(p(k) * q for k, q in n['pastry'].items())
    elif n['kind'] == 'pastry':
        total = sum(p(k) * q for k, q in n['items'].items())
        total = max(1, total // 2) if n['day_old_ok'] else total
    else:
        total = p('cake')
    return max(1, round(total * _mult(c)))


def on_task(s: dict, c: dict, t: dict) -> None:
    if t.get('gen') != GEN:
        _upgrade_task(t, c)
    if t.get('quoted_price') is None:
        t['quoted_price'] = quote(c, t['needs'])
    if 'regular' not in t:
        # How much the notes card knew about this guest when they walked in.
        t['regular'] = len(_book(kit.data(c)).get(t['npc'], {}).get('notes', []))
        t['greeted'] = False


def on_start(s: dict, c: dict) -> None:
    _migrate(c)
    _plan(c)
    for t in c['tasks']:
        if t['career'] == ID and t['status'] not in FS.DONE:
            on_task(s, c, t)


def _drink_text(n: dict) -> str:
    d = DRINKS[n['drink']]
    parts = [f'{d["name"]} {"đá" if n["iced"] else "nóng"}', f'ly {"lớn" if n["size"] == "L" else "nhỏ"}',
             'mang về' if n['takeaway'] else 'uống tại quán', f'hạt {BEAN_INDEX[n["beans"]]["name"]}', f'{n["shots"]} shot']
    if n['milk']:
        parts.append(MILKS[n['milk']]['name'].lower() + (' (bọt dày)' if n['foam'] == 'thick' else ' (bọt mỏng)' if n['foam'] == 'thin' else ''))
    if n['art']:
        parts.append('vẽ ' + ART_INDEX[n['art']]['name'].lower())
    text = ', '.join(parts)
    if n['lactose']:
        text += ' (⚠️ không dung nạp lactose — tuyệt đối không sữa bò)'
    if n['decaf']:
        text += ' (⚠️ không được có caffeine)'
    return text


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if n['kind'] == 'drink' and _hidden(t):
        return f'“{n["mood"]["text"]}” Chọn món hợp ý khách nhé.'
    if n['kind'] == 'drink' and n.get('party'):
        cups = '; '.join(f'ly {i + 1} là {_drink_text(x)}' for i, x in enumerate(n['party']))
        return f'{len(n["party"])} ly {"mang về" if n["takeaway"] else "tại quán"}: {cups}. {n["note"]}'
    if n['kind'] == 'drink':
        d = DRINKS[n['drink']]
        parts = [f'{d["name"]} {"đá" if n["iced"] else "nóng"}', f'ly {"lớn" if n["size"] == "L" else "nhỏ"}',
                 'mang về' if n['takeaway'] else 'uống tại quán', f'hạt {BEAN_INDEX[n["beans"]]["name"]}', f'{n["shots"]} shot']
        if n['milk']:
            parts.append(MILKS[n['milk']]['name'].lower() + (' (bọt dày)' if n['foam'] == 'thick' else ' (bọt mỏng)' if n['foam'] == 'thin' else ''))
        if n['art']:
            parts.append('vẽ ' + ART_INDEX[n['art']]['name'].lower())
        if n['pastry']:
            parts.append('kèm ' + ', '.join(f'{q} {BAKES[k]["name"].lower()}' for k, q in n['pastry'].items()))
        text = ', '.join(parts) + '.'
        if n['lactose']:
            text += ' ⚠️ Không dung nạp lactose — tuyệt đối không sữa bò.'
        if n['decaf']:
            text += ' ⚠️ Không được có caffeine.'
        return text + ' ' + n['note']
    if n['kind'] == 'pastry':
        text = ', '.join(f'{q} {BAKES[k]["name"].lower()}' for k, q in n['items'].items())
        text = 'Lấy ' + text + (', cho vào túi mang về' if n['takeaway'] else ', dùng tại quán') + '.'
        if n['day_old_ok']:
            text += ' Khách muốn bánh hôm qua giảm 50%.'
        if n['allergy']:
            text += f' ⚠️ Dị ứng {ALLERGEN_LABEL[n["allergy"]]}.'
        return text + ' ' + n['note']
    return (f'Bánh kem {CREAMS[n["cream"]]["name"].lower()} màu {COLORS[n["color"]]["name"].lower()}, '
            f'chữ trên mặt bánh: “{n["text"]}”. ' + n['note'])


# --- helpers ------------------------------------------------------------------

def _open(t: dict) -> bool:
    return t['career'] == ID and t['status'] not in ('completed', 'cancelled', 'referred')


def _pulling(c: dict) -> list:
    return [t for t in c['tasks'] if _open(t) and t['drink']['pulling']]


def _steaming(c: dict) -> list:
    return [t for t in c['tasks'] if _open(t) and t['drink']['steaming']]


def _usable(c: dict, unlock: int, t: dict | None = None, wanted: bool = False) -> bool:
    """Locked by level, unless this exact order asks for it (the customer ordered it)."""
    return unlock <= kit.level(c) or wanted


def _wanted_anywhere(c: dict, item: str) -> bool:
    """A known open order asks for this bake, so the recipe card is opened for it."""
    return any(_open(t) and t['known'] and item in _wanted_bakes(t['needs']) for t in c['tasks'])


def _auto(c: dict, p: dict) -> bool:
    """The first-day timer (see AUTO_DAYS): asked for, and still the shop's first day."""
    return p.get('auto') is True and c['day'] <= AUTO_DAYS


def _flow(dose: dict) -> float:
    grams = dose['grams']
    return GRIND[dose['grind']] * max(0.7, min(1.4, 1 + (DOSE_TARGET - grams) * 0.06))


def _shot_class(seconds: float, grind: str) -> str:
    if grind != 'fine':
        return 'sour'
    if seconds < EXTRACT['sour']:
        return 'sour'
    if seconds < EXTRACT['bright']:
        return 'bright'
    if seconds <= EXTRACT['balanced']:
        return 'balanced'
    if seconds <= EXTRACT['strong']:
        return 'strong'
    return 'bitter'


def steam_temp(seconds: float) -> float:
    return round(STEAM['base'] + STEAM['rate'] * seconds, 1)


def _milk_tex(temp: float) -> str:
    if temp < STEAM['cool']:
        return 'cool'
    if temp <= STEAM['silky']:
        return 'silky'
    if temp <= STEAM['hot']:
        return 'hot'
    return 'scalded'


def _doneness(item: str, seconds: float) -> str:
    a, b, z = BAKES[item]['window']
    return 'pale' if seconds < a else 'golden' if seconds < b else 'dark' if seconds < z else 'burnt'


def _age(c: dict, day: int) -> int:
    return max(0, c['day'] - day)


def lot_state(c: dict, item: str, day: int) -> str:
    b = BAKES[item]
    age = _age(c, day)
    return 'fresh' if age <= b['fresh'] else 'day_old' if age <= b['max_age'] else 'expired'


def _case_count(d: dict, item: str) -> int:
    return sum(l['qty'] for l in d['case'] if l['item'] == item)


def _add_case(c: dict, item: str, qty: int, day: int, q: str, cost: int) -> None:
    d = kit.data(c)
    lot = next((l for l in d['case'] if l['item'] == item and l['day'] == day and l['q'] == q and not l['sale']), None)
    if lot:
        lot['qty'] += qty
    else:
        d['case'].append(dict(id=kit.next_id(c, 'bk'), item=item, qty=qty, day=day, q=q, sale=False, cost=cost))


def _consume(c: dict, recipe: dict) -> int:
    for k, q in recipe.items():
        kit.need(kit.stock(c, k) >= q, f'Thiếu {ITEM_INDEX[k]["name"]} (cần {q} {ITEM_INDEX[k]["unit"]}). Mở Kho để nhập thêm nhé.')
    return sum(kit.take(c, k, q) for k, q in recipe.items())


def _recipe_ok(c: dict, recipe: dict) -> bool:
    return all(kit.stock(c, k) >= q for k, q in recipe.items())


def _letters(text: str) -> str:
    """Compare cake writing: accents and letters matter, punctuation/case/spaces do not."""
    t = unicodedata.normalize('NFC', text or '').casefold()
    t = ''.join(ch if (ch.isalnum() or ch.isspace()) else ' ' for ch in t)
    return ' '.join(t.split())


def _wanted_bakes(n: dict) -> dict:
    return n['items'] if n['kind'] == 'pastry' else n.get('pastry', {}) if n['kind'] == 'drink' else {}


def _allergen_hit(t: dict) -> str | None:
    n = t['needs']
    if n['kind'] == 'pastry' and n['allergy']:
        for x in t['bag']['items']:
            if n['allergy'] in BAKES[x['item']]['allergens']:
                return n['allergy']
    return None


def _task_for_rack(c: dict, tid: str | None) -> dict | None:
    return next((t for t in c['tasks'] if t['id'] == tid and _open(t)), None) if tid else None


# --- actions ------------------------------------------------------------------

BAR_ACTIONS = ('cb_cup', 'cb_ice', 'cb_water', 'cb_dose', 'cb_pull', 'cb_stop', 'cb_milk', 'cb_milk_stop', 'cb_art', 'cb_lid')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _migrate(c)
    pl = _plan(c)
    out = _handle(s, c, d, pl, name, p)
    active = p.get('task') or c.get('active_task')
    if name in SPEC['physical']:
        FS.patience_tick(c, ID, active, _patience_extra(c, pl), lambda t: kit.size_factor(_units(t), SIZE_BASE))
    if name not in SHOP_ACTIONS:
        kit.worked(c, active)
    return out


def _handle(s: dict, c: dict, d: dict, pl: dict, name: str, p: dict) -> dict:
    if name == 'cb_event':
        return FS.resolve(s, c, pl, EVENT_INDEX, p)
    if name == 'cb_box_send':
        return _box_send(s, c, d, pl)
    if name == 'cb_clean':
        kit.need(d['clean_day'] != c['day'], 'Hôm nay đã vệ sinh máy rồi.')
        d['clean_day'] = c['day']
        kit.metric(c, 'hygiene_checks')
        return dict(message='Đã xả nước nhóm pha, chà tay cầm, lau và xả vòi đánh sữa, ghi sổ vệ sinh ca.')
    if name == 'cb_shape':
        return _shape(s, c, d, p)
    if name == 'cb_bake':
        return _bake(s, c, d, p)
    if name == 'cb_unload':
        return _unload(s, c, d, p)
    if name in ('cb_markdown', 'cb_donate', 'cb_discard'):
        return _case_action(s, c, d, name, p)
    if name == 'cb_feed':
        return _feed(s, c, d)
    if name == 'cb_chill':
        return _chill(s, c, d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Công việc không thuộc tiệm bánh.')
    if name == 'cb_greet':
        return _greet(s, c, d, t)
    kit.need(t['known'], 'Hỏi khách order trước nhé (bấm “Nhận order”).')
    if t.get('quoted_price') is None:
        on_task(s, c, t)
    n = t['needs']
    if name == 'cb_guess':
        return _guess(s, c, pl, t, p)
    if name in ('cb_done', 'cb_tab'):
        kit.need(_tray(t), 'Đơn này chỉ có một ly.')
        return _tray_action(s, c, t, name, p)
    if name in BAR_ACTIONS:
        kit.need(n['kind'] == 'drink', 'Đơn này không có đồ uống.')
        kit.need(not _hidden(t), 'Đoán đúng món khách muốn trước đã nhé.')
        kit.need(not _tray(t) or t['cups'][t['cur']] is None, f'Ly {t["cur"] + 1} đã đặt lên khay. Chọn ly khác để làm tiếp.')
        return _bar(s, c, t, name, p)
    if name in ('cb_pick', 'cb_return', 'cb_bag'):
        kit.need(n['kind'] in ('drink', 'pastry'), 'Đơn bánh kem không lấy bánh ở tủ kính.')
        return _counter(s, c, d, t, name, p)
    if name in ('cb_frost', 'cb_write', 'cb_scrape', 'cb_box'):
        kit.need(n['kind'] == 'cake', 'Đơn này không phải bánh kem.')
        return _decorate(s, c, t, name, p)
    if name == 'cb_dump':
        return _dump(s, c, d, t, p)
    if name == 'cb_serve':
        return _serve(s, c, d, pl, t, p)
    raise kit.eng().GameError('Thao tác tiệm bánh không hợp lệ.')


def _guess(s: dict, c: dict, pl: dict, t: dict, p: dict) -> dict:
    """Mood order: pick the drink that fits what the guest described."""
    n = t['needs']
    kit.need(n.get('style') == 'mood', 'Khách này đã gọi món rõ ràng rồi.')
    kit.need(not t['guessed'], 'Đã hiểu ý khách rồi.')
    pick = _one_of(p.get('drink'), n['mood']['options'], 'Chọn một trong các món gợi ý.')
    kit.need(pick not in t['guesses'], 'Món này khách vừa lắc đầu rồi.')
    t['guesses'].append(pick)
    kit.start_work(t)
    if pick == n['drink']:
        t['guessed'] = True
        extra = ''
        if len(t['guesses']) == 1:
            kit.money(s, c, MOOD_TIP, 'Khách vui vì được hiểu ý', t['id'], category='tip')
            pl['tips'] += MOOD_TIP
            extra = f' Khách vui ra mặt: +{MOOD_TIP} xu.'
        kit.log(s, c, 'fact', known_request(c, t), t['npc'], t['id'])
        FS.flash(pl, 'good', f'💡 Đúng ý khách: {DRINKS[pick]["name"]}!{extra}')
        return dict(message=f'Đúng ý khách: {DRINKS[pick]["name"]}!{extra} ' + known_request(c, t))
    t['patience'] = max(25, t.get('patience', 100) - 12)
    if len(t['guesses']) >= 2:
        t['guessed'] = True
        t['mistakes'] += 1
        kit.log(s, c, 'fact', known_request(c, t), t['npc'], t['id'])
        return dict(message=f'Khách cười trừ rồi nói luôn: “Cho mình {DRINKS[n["drink"]]["name"]} nha.” ' + known_request(c, t))
    return dict(message=f'Khách lắc đầu: “{n["mood"]["clue"]}”')


def _tray_action(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    """Trays: finish cups one by one; switch between cups that are not started."""
    cups, cur, dr = t['cups'], t['cur'], t['drink']
    if name == 'cb_tab':
        i = kit.integer(p.get('index'), 0, len(cups) - 1)
        kit.need(i != cur, 'Đang làm ly này rồi.')
        busy = cups[cur] is None and (dr['container'] or dr['shots'] or dr['dose'] or dr['milk'] or dr['pulling'] or dr['steaming'])
        kit.need(not busy, f'Ly {cur + 1} đang làm dở. Làm xong và đặt lên khay (hoặc đổ ly) rồi mới đổi ly.')
        if cups[i] is not None:
            # Reopen a finished cup: take it back off the tray.
            t['drink'], cups[i] = cups[i], None
        t['cur'] = i
        return dict(message=f'Đang làm ly {i + 1}.')
    kit.need(cups[cur] is None, f'Ly {cur + 1} đã ở trên khay.')
    kit.need(dr['container'] and dr['shots'], f'Ly {cur + 1} cần có ly và espresso trước.')
    kit.need(not dr['pulling'] and not dr['steaming'] and not dr['dose'], 'Còn shot đang chiết hoặc sữa đang đánh.')
    kit.need(dr['container'] != 'paper' or dr['lid'], 'Đậy nắp ly mang về rồi mới đặt lên khay.')
    cups[cur] = dr
    t['drink'] = _empty_drink()
    pending = [i for i, x in enumerate(cups) if x is None]
    if pending:
        t['cur'] = pending[0]
        return dict(message=f'Đã đặt ly {cur + 1} lên khay. Tiếp theo: ly {pending[0] + 1}.')
    return dict(message='Đủ ly trên khay rồi — giao cho khách thôi!')


def _bar(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n = _spec(t)
    dr = t['drink']
    spec = DRINKS[n['drink']]
    if name == 'cb_cup':
        kit.need(dr['container'] is None, 'Đã có ly. Đổ ly nếu muốn làm lại.')
        kind = _one_of(p.get('kind'), CONTAINERS, 'Chọn tách sứ, ly thủy tinh hoặc ly giấy.')
        size = _one_of(p.get('size', 'S'), ('S', 'L'), 'Chọn ly nhỏ hoặc ly lớn.')
        if kind == 'paper':
            dr['cost'] += kit.take(c, 'cup', 1)
        want = 'paper' if n['takeaway'] else 'glass' if n['iced'] else 'mug'
        dr['container'] = kind
        dr['size'] = size
        if kind != want or size != n['size']:
            t['mistakes'] += 1
        kit.start_work(t)
        return dict(message=f'Đã lấy {CONTAINERS[kind]["name"].lower()} cỡ {"lớn" if size == "L" else "nhỏ"}.')
    kit.need(dr['container'], 'Lấy ly trước nhé.')
    if name == 'cb_ice':
        kit.need(not dr['ice'], 'Ly đã có đá.')
        kit.need(dr['container'] != 'mug', 'Tách sứ dùng cho đồ nóng, không bỏ đá vào tách.')
        dr['ice'] = True
        if not n['iced']:
            t['mistakes'] += 1
        return dict(message='Đã múc đá đầy ly.')
    if name == 'cb_water':
        kit.need(not dr['water'], 'Ly đã có nước.')
        dr['water'] = True
        if not spec['water']:
            t['mistakes'] += 1
        return dict(message='Đã thêm nước ' + ('lạnh.' if n['iced'] else 'nóng 90 °C.'))
    if name == 'cb_dose':
        kit.need(not dr['pulling'], 'Tay cầm đang gắn trên máy, chờ chiết xong.')
        kit.need(dr['dose'] is None, 'Đã có bột trong tay cầm. Chiết shot đó trước.')
        kit.need(len(dr['shots']) < 3, 'Ly đủ shot rồi.')
        beans = _one_of(p.get('beans'), BEAN_INDEX, 'Loại hạt không có trong tiệm.')
        b = BEAN_INDEX[beans]
        kit.need(_usable(c, b['unlock'], t, n['beans'] == beans), f'{b["name"]} mở ở cấp {b["unlock"]}.')
        grind = _one_of(p.get('grind'), GRIND, 'Chọn độ xay.')
        grams = kit.integer(p.get('grams'), DOSE_MIN, DOSE_MAX)
        dr['cost'] += kit.take(c, b['item'], 1)
        dr['dose'] = dict(beans=beans, grind=grind, grams=grams)
        if beans != n['beans']:
            t['mistakes'] += 1
        kit.start_work(t)
        extra = '' if grind == 'fine' else ' Lưu ý: espresso cần xay mịn, bột thô nước sẽ chảy ào.'
        return dict(message=f'Đã xay {b["name"]} ({GRIND_LABEL[grind].lower()}), định lượng {grams} g, nén phẳng.{extra}')
    if name == 'cb_pull':
        kit.need(dr['dose'], 'Xay và định lượng bột vào tay cầm trước.')
        kit.need(not dr['pulling'], 'Shot của ly này đang chiết.')
        kit.need(len(_pulling(c)) < MAX_GROUPS, 'Cả hai họng pha đang bận. Dừng một shot trước nhé.')
        if not _auto(c, p):
            dr['pulling'] = round(kit.now(), 3)
            return dict(message=f'Đang chiết… Dừng khi vào vùng cân bằng ({EXTRACT["bright"]}–{EXTRACT["balanced"]} giây).')
    if name in ('cb_pull', 'cb_stop'):
        if name == 'cb_stop':
            kit.need(dr['pulling'], 'Chưa chiết shot nào. Bấm “Chiết shot” trước nhé.')
            eff = max(0.0, kit.tap_now(p) - dr['pulling']) * _flow(dr['dose'])
        else:
            eff = AUTO_SHOT
        x = _shot_class(eff, dr['dose']['grind'])
        dr['shots'].append(dict(beans=dr['dose']['beans'], grind=dr['dose']['grind'], grams=dr['dose']['grams'], x=x, sec=round(min(eff, 999), 1)))
        dr['dose'] = None
        dr['pulling'] = None
        if x in ('sour', 'bitter'):
            t['mistakes'] += 1
        if len(dr['shots']) > n['shots']:
            t['mistakes'] += 1
        auto = 'Máy hẹn giờ ngày đầu tự dừng. ' if name == 'cb_pull' else ''
        return dict(message=f'{auto}Shot {SHOT_LABEL[x]} · {eff:.1f} giây chiết.')
    if name == 'cb_milk':
        kit.need(dr['milk'] is None and not dr['steaming'], 'Ly đã có sữa.')
        kind = _one_of(p.get('milk'), MILKS, 'Loại sữa không có trong tiệm.')
        m = MILKS[kind]
        kit.need(_usable(c, m['unlock'], t, n['milk'] == kind), f'{m["name"]} mở ở cấp {m["unlock"]}.')
        mode = _one_of(p.get('mode'), ('steam', 'cold'), 'Chọn đánh nóng hoặc rót lạnh.')
        if mode == 'steam':
            kit.need(m['steam'], f'{m["name"]} không đánh bằng vòi hơi, chỉ rót lạnh.')
            foam = _one_of(p.get('foam'), ('thin', 'thick'), 'Chọn bọt mỏng (latte) hoặc bọt dày (cappuccino).')
            kit.need(len(_steaming(c)) < MAX_WANDS, 'Vòi đánh sữa đang bận với ly khác.')
            dr['cost'] += kit.take(c, m['item'], 1)
            dr['steaming'] = round(kit.now(), 3)
            dr['steam'] = dict(kind=kind, foam=foam)
            if kind != n['milk'] or n['iced'] or not spec['milk'] or foam != n['foam']:
                t['mistakes'] += 1
            if not _auto(c, p):
                return dict(message=f'Đã cắm vòi hơi vào ca {m["name"].lower()}. Tắt khi nhiệt kế vào vùng {STEAM["cool"]}–{STEAM["silky"]} °C.')
        else:
            dr['cost'] += kit.take(c, m['item'], 1)
            dr['milk'] = dict(kind=kind, mode='cold', foam=None, temp=None, tex=None)
            if kind != n['milk'] or not n['iced'] or not spec['milk']:
                t['mistakes'] += 1
            return dict(message=f'Đã rót {m["name"].lower()} lạnh.')
    if name in ('cb_milk', 'cb_milk_stop'):
        if name == 'cb_milk_stop':
            kit.need(dr['steaming'], 'Vòi hơi chưa bật. Bấm “Đánh nóng” trước nhé.')
            temp = min(99.0, steam_temp(max(0.0, kit.tap_now(p) - dr['steaming'])))
        else:
            temp = AUTO_MILK
        tex = _milk_tex(temp)
        dr['milk'] = dict(kind=dr['steam']['kind'], mode='steam', foam=dr['steam']['foam'], temp=temp, tex=tex)
        dr['steaming'] = None
        dr['steam'] = None
        if tex in ('cool', 'scalded'):
            t['mistakes'] += 1
        auto = 'Vòi hơi hẹn giờ ngày đầu tự tắt. ' if name == 'cb_milk' else ''
        return dict(message=f'{auto}Sữa {MILK_TEX_LABEL[tex]} · {temp:.0f} °C.')
    if name == 'cb_art':
        kit.need(dr['milk'] and dr['milk']['mode'] == 'steam', 'Latte art cần sữa đánh nóng vừa xong.')
        kit.need(dr['shots'], 'Rót sữa lên espresso — chiết shot trước đã.')
        kit.need(dr['art'] is None, 'Ly đã được rót tạo hình.')
        pattern = _one_of(p.get('pattern'), ART_INDEX, 'Hình vẽ không có trong sổ tay.')
        a = ART_INDEX[pattern]
        kit.need(_usable(c, a['unlock'], t, n['art'] == pattern), f'{a["name"]} mở ở cấp {a["unlock"]}.')
        dr['art'] = pattern if dr['milk']['tex'] == 'silky' else 'blob'
        if n['art'] and dr['art'] != n['art']:
            t['mistakes'] += 1
        if dr['art'] == 'blob':
            return dict(message='Bọt sữa không mịn nên hình bị loang thành một đốm… Sữa phải trong khoảng 55–68 °C.')
        return dict(message=f'Rót được hình {a["name"].lower()}!')
    # cb_lid
    kit.need(dr['container'] == 'paper', 'Chỉ ly giấy mang về mới cần nắp.')
    kit.need(not dr['lid'], 'Đã đậy nắp.')
    dr['lid'] = True
    return dict(message='Đã đậy nắp, dán tem tên khách lên ly.')


def _counter(s: dict, c: dict, d: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    bag = t['bag']
    want = _wanted_bakes(n)
    if name == 'cb_pick':
        kit.need(not bag['bagged'], 'Túi đã gấp miệng. Trả một bánh về tủ để mở túi ra nhé.')
        kit.need(len(bag['items']) < 12, 'Khay đầy rồi.')
        lot = next((l for l in d['case'] if l['id'] == p.get('lot')), None)
        kit.need(lot and lot['qty'] > 0, 'Khay bánh này đã hết.')
        state = lot_state(c, lot['item'], lot['day'])
        kit.need(state != 'expired', 'Bánh đã quá hạn bán theo quy định của tiệm. Bỏ khay này nhé.')
        lot['qty'] -= 1
        bag['items'].append(dict(item=lot['item'], day=lot['day'], q=lot['q'], cost=lot['cost']))
        bag['cost'] += lot['cost']
        if lot['qty'] <= 0:
            d['case'] = [l for l in d['case'] if l['id'] != lot['id']]
        taken = sum(1 for x in bag['items'] if x['item'] == lot['item'])
        if taken > want.get(lot['item'], 0):
            t['mistakes'] += 1
        elif state == 'day_old' and not n.get('day_old_ok'):
            t['mistakes'] += 1
        kit.start_work(t)
        b = BAKES[lot['item']]
        tag = ' (bánh hôm qua)' if state == 'day_old' else ''
        return dict(message=f'Đã gắp {b["name"].lower()}{tag} bằng kẹp vào khay.')
    if name == 'cb_return':
        i = kit.integer(p.get('index'), 0, 11)
        kit.need(i < len(bag['items']), 'Không có bánh này trong khay.')
        x = bag['items'].pop(i)
        bag['cost'] = max(0, bag['cost'] - x['cost'])
        kit.need(_case_count(d, x['item']) < CASE_MAX, 'Tủ bánh đầy.')
        _add_case(c, x['item'], 1, x['day'], x['q'], x['cost'])
        opened = ' Đã mở miệng túi ra.' if bag['bagged'] else ''
        bag['bagged'] = False
        return dict(message=f'Đã trả {BAKES[x["item"]]["name"].lower()} về tủ kính.{opened}')
    # cb_bag
    kit.need(bag['items'], 'Chưa có bánh để cho vào túi.')
    kit.need(not bag['bagged'], 'Đã cho vào túi rồi.')
    if not bag['has_bag']:
        bag['cost'] += kit.take(c, 'bag', 1)
        bag['has_bag'] = True
    bag['bagged'] = True
    return dict(message='Đã cho bánh vào túi giấy, gấp miệng túi, dán tem ngày ra lò.')


def _decorate(s: dict, c: dict, t: dict, name: str, p: dict) -> dict:
    n = t['needs']
    ck = t['cake']
    if name == 'cb_frost':
        kit.need(ck['sponge'] in ('golden', 'dark'), 'Cần một cốt bánh nướng đạt trước khi phủ kem.')
        kit.need(ck['cream'] is None, 'Bánh đã phủ kem.')
        cream = _one_of(p.get('cream'), CREAMS, 'Chọn kem tươi hoặc kem bơ.')
        color = _one_of(p.get('color'), COLORS, 'Màu kem không có trong bảng màu.')
        ck['cost'] += _consume(c, CREAMS[cream]['recipe'])
        ck['cream'] = cream
        ck['color'] = color
        ck['melted'] = c['turn'] < ck['cool_turn']
        if cream != n['cream'] or color != n['color']:
            t['mistakes'] += 1
        if ck['melted']:
            t['mistakes'] += 1
            return dict(message='Cốt bánh còn ấm nên kem chảy xệ… Lần sau để bánh nguội hẳn rồi mới phủ kem.')
        return dict(message=f'Đã phủ {CREAMS[cream]["name"].lower()} màu {COLORS[color]["name"].lower()}, láng mặt phẳng.')
    if name == 'cb_write':
        kit.need(ck['cream'], 'Phủ kem trước rồi mới viết chữ.')
        kit.need(ck['text'] is None, 'Mặt bánh đã có chữ. Cạo chữ nếu cần viết lại.')
        text = kit.text(p.get('text'), 40, 2)
        ck['text'] = text
        if _letters(text) != _letters(n['text']):
            t['mistakes'] += 1
        return dict(message=f'Đã bắt bông viết: “{text}”. Đọc lại thật kỹ trước khi đóng hộp nhé.')
    if name == 'cb_scrape':
        kit.confirm(p, 'Xác nhận cạo chữ và láng lại mặt kem.')
        kit.need(ck['text'] is not None, 'Mặt bánh chưa có chữ.')
        kit.need(not ck['boxed'], 'Mở hộp ra trước đã.')
        kit.need(ck['scraped'] < 5, 'Mặt kem đã láng lại quá nhiều lần.')
        ck['text'] = None
        ck['scraped'] += 1
        return dict(message='Đã cạo chữ, láng lại mặt kem. Viết lại cẩn thận nhé.')
    # cb_box
    kit.need(ck['cream'] and ck['text'], 'Hoàn thiện kem và chữ trước khi đóng hộp.')
    kit.need(not ck['boxed'], 'Đã đóng hộp.')
    ck['cost'] += kit.take(c, 'cake_box', 1)
    ck['boxed'] = True
    return dict(message='Đã đặt bánh vào hộp, kèm nến, dao nhựa và thiệp hướng dẫn bảo quản lạnh.')


def _shape(s: dict, c: dict, d: dict, p: dict) -> dict:
    item = _one_of(p.get('item'), [k for k, b in BAKES.items() if b['proof']], 'Chỉ croissant và bánh mì cần ủ bột.')
    b = BAKES[item]
    kit.need(_usable(c, b['unlock'], wanted=_wanted_anywhere(c, item)), f'{b["name"]} mở ở cấp {b["unlock"]}.')
    kit.need(len(d['proof']) < 2, 'Tủ ủ chỉ có 2 ngăn. Nướng bớt một khay trước.')
    cost = _consume(c, b['recipe'])
    beats, dense, extra = PROOF_TURNS, False, ''
    if b.get('starter'):
        band = _band(d['starter']['strength'])
        beats, dense = band[4], band[1] == 'hungry'
        extra = f' Bé Men {band[3].lower()} ({d["starter"]["strength"]}%): {band[5]}.'
    tray = dict(id=kit.next_id(c, 'pf'), item=item, qty=b['qty'], since=c['turn'], ready=c['turn'] + beats, cost=cost, dense=dense)
    d['proof'].append(tray)
    kit.metric(c, 'doughs_shaped')
    return dict(message=f'Đã nhào và tạo hình {b["qty"]} {b["name"].lower()}, cho vào tủ ủ. Bột cần nở thêm vài nhịp.{extra}')


# --- care: Bé Men, the fridge, the regulars ---------------------------------------

def _band(strength: int) -> tuple:
    return next(b for b in STARTER_BANDS if strength >= b[0])


def _feed(s: dict, c: dict, d: dict) -> dict:
    st = d['starter']
    kit.need(st['fed'] != c['day'], 'Hôm nay Bé Men đã được cho ăn rồi. Mai cho ăn tiếp nhé.')
    kit.need(kit.stock(c, 'flour') >= 1, 'Hết bột mì để cho Bé Men ăn. Mở Kho nhập thêm nhé.')
    kit.take(c, 'flour', 1)
    before = st['strength']
    st['strength'] = min(STARTER_MAX, before + (FEED_GAIN_HUNGRY if before < 40 else FEED_GAIN))
    st['fed'] = c['day']
    st['feeds'] += 1
    kit.metric(c, 'starter_feeds')
    band = _band(st['strength'])
    return dict(message=f'Đã bỏ bớt men cũ, cho Bé Men ăn bột mì và nước ấm. Hũ men sủi bọt lên {before}% → {st["strength"]}% '
                        f'({band[2]} {band[3]}: {band[5]}).')


def _chill(s: dict, c: dict, d: dict, p: dict) -> dict:
    tray = next((x for x in d['proof'] if x['id'] == p.get('tray')), None)
    kit.need(tray, 'Không có khay bột này trong tủ ủ.')
    kit.need(len(d['cold']) < COLD_MAX, f'Tủ mát chỉ có {COLD_MAX} ngăn ủ bột, đều đang có khay. Nướng bớt một khay ủ lạnh trước.')
    d['proof'] = [x for x in d['proof'] if x['id'] != tray['id']]
    flat = c['turn'] > tray['ready'] + OVERPROOF
    d['cold'].append(dict(id=tray['id'], item=tray['item'], qty=tray['qty'], day=c['day'], cost=tray['cost'],
                          dense=bool(tray.get('dense')), flat=flat))
    kit.metric(c, 'doughs_chilled')
    b = BAKES[tray['item']]
    return dict(message=f'Đã bọc kín khay {b["name"].lower()}, cất ngăn ủ bột của tủ mát. Bột nở chậm qua đêm — từ mai nướng được ngay, '
                        f'trong vòng {COLD_NIGHTS} ngày.')


def _book(d: dict) -> dict:
    b = d.get('book')
    return b if isinstance(b, dict) else {}


def _learned(npc: int, visits: int) -> list[str]:
    return [n['id'] for n, at in zip(NOTES.get(npc, []), NOTE_AT) if visits >= at]


def _npc_index(npc_id: str) -> int | None:
    return next((i for i in range(len(PEOPLE)) if kit.npc_id(ID, i) == npc_id), None)


def _notes_of(d: dict, npc_id: str) -> list[dict]:
    i = _npc_index(npc_id)
    ids = set(_book(d).get(npc_id, {}).get('notes', []))
    return [n for n in NOTES.get(i, []) if n['id'] in ids] if i is not None else []


def _book_visit(c: dict, d: dict, t: dict) -> str | None:
    """A served order: the guest comes back to the notes card; returns a line when a note is learned."""
    i = _npc_index(t['npc'])
    if i is None:
        return None
    rec = d['book'].setdefault(t['npc'], dict(visits=0, notes=[]))
    rec['visits'] = min(999, rec['visits'] + 1)
    learned = _learned(i, rec['visits'])
    new = [n for n in NOTES[i] if n['id'] in learned and n['id'] not in rec['notes']]
    rec['notes'] = learned
    if not new:
        return None
    return f'📒 Sổ khách quen · {PEOPLE[i][0]}: {new[0]["text"]}'


def _greet(s: dict, c: dict, d: dict, t: dict) -> dict:
    notes = _notes_of(d, t['npc'])
    kit.need(t.get('regular') and notes, 'Tiệm chưa biết gì về khách này. Phục vụ vài lần, sổ khách quen sẽ ghi lại.')
    kit.need(not t.get('greeted'), 'Đã chào hỏi khách rồi.')
    t['greeted'] = True
    t['patience'] = min(100, t.get('patience', 100) + 8)
    who = PEOPLE[_npc_index(t['npc'])][0]
    return dict(message=f'“{who} tới rồi! Như mọi khi hả?” — {notes[0]["text"]} Khách cười tít mắt: “Nhớ dai ghê!” (+8 kiên nhẫn)')


def _bake(s: dict, c: dict, d: dict, p: dict) -> dict:
    item = _one_of(p.get('item'), BAKES, 'Món này không có trong sổ công thức.')
    b = BAKES[item]
    kit.need(len(d['oven']) < 2, 'Lò chỉ có 2 tầng, đều đang nướng.')
    task = None
    flat = dense = chilled = False
    if b.get('cake'):
        task = kit.task(c, p)
        kit.need(task['career'] == ID and task['needs']['kind'] == 'cake', 'Cốt bánh kem chỉ nướng cho đơn bánh kem.')
        kit.need(task['known'], 'Hỏi khách đơn bánh kem trước nhé.')
        kit.need(task['cake']['sponge'] is None and not task['cake']['baking'], 'Đơn này đã có cốt bánh.')
        cost = _consume(c, b['recipe'])
        task['cake']['baking'] = True
        task['cake']['cost'] += cost
        kit.start_work(task)
    else:
        kit.need(_usable(c, b['unlock'], wanted=_wanted_anywhere(c, item)), f'{b["name"]} mở ở cấp {b["unlock"]}.')
        kit.need(_case_count(d, item) + b['qty'] <= CASE_MAX, 'Tủ kính đã đầy loại bánh này.')
        if b['proof']:
            trays = [x for x in d['proof'] if x['item'] == item]
            colds = [x for x in d['cold'] if x['item'] == item]
            want = p.get('tray')
            tray = next((x for x in trays if x['id'] == want), None) if want else (trays[0] if trays else None)
            cold = None
            if not tray:
                cold = next((x for x in colds if x['id'] == want), None) if want else \
                    next((x for x in colds if x['day'] < c['day']), colds[0] if colds else None)
            if cold:
                kit.need(cold['day'] < c['day'], 'Khay này mới cất tủ mát hôm nay — bột cần ủ lạnh qua một đêm. Mai nướng nhé.')
                flat, cost, dense, chilled = bool(cold.get('flat')), cold['cost'], bool(cold.get('dense')), True
                d['cold'] = [x for x in d['cold'] if x['id'] != cold['id']]
            else:
                kit.need(tray, f'Chưa có khay {b["name"].lower()} nào đang ủ. Nhào và tạo hình trước.')
                kit.need(c['turn'] >= tray['ready'], f'Bột chưa nở đủ (còn {tray["ready"] - c["turn"]} nhịp). Nướng non bột sẽ chai cứng.')
                flat = c['turn'] > tray['ready'] + OVERPROOF
                cost, dense = tray['cost'], bool(tray.get('dense'))
                d['proof'] = [x for x in d['proof'] if x['id'] != tray['id']]
        else:
            cost = _consume(c, b['recipe'])
    shift = HOT_OVEN if _plan(c)['rules'].get('hot_oven') else 0
    rack = dict(id=kit.next_id(c, 'ov'), item=item, qty=b['qty'], start=round(kit.now(), 3), task=task['id'] if task else None, cost=cost, flat=flat, shift=shift,
                dense=dense)
    d['oven'].append(rack)
    a, g, z = (max(1, x - shift) for x in b['window'])
    hot = ' Lò đang nóng hơn thường, bánh chín nhanh hơn!' if shift else ''
    cold = ' Bột ủ lạnh qua đêm vào lò luôn, không phải chờ nở.' if chilled else ''
    return dict(message=f'Đã cho {b["name"].lower()} vào lò. Lấy ra khi vàng đều ({a}–{g} giây).{hot}{cold}')


def _unload(s: dict, c: dict, d: dict, p: dict) -> dict:
    rack = next((r for r in d['oven'] if r['id'] == p.get('rack')), None)
    kit.need(rack, 'Tầng lò này đang trống.')
    b = BAKES[rack['item']]
    sec = max(0.0, kit.tap_now(p) - rack['start'])
    done = _doneness(rack['item'], sec + rack.get('shift', 0))
    d['oven'] = [r for r in d['oven'] if r['id'] != rack['id']]
    label = dict(pale='còn nhạt màu, ruột chưa chín', golden='vàng đều, thơm lừng', dark='hơi sậm màu', burnt='cháy đen')[done]
    if rack['task']:
        t = _task_for_rack(c, rack['task'])
        if not t:
            kit.waste(c, 'sponge', 1, rack['cost'], 'Cốt bánh của đơn đã đóng')
            return dict(message='Đơn bánh kem đã đóng, cốt bánh được ghi hao hụt.')
        ck = t['cake']
        ck['baking'] = False
        ck['sponge'] = done
        ck['cool_turn'] = c['turn'] + COOL_TURNS
        if done in ('pale', 'burnt'):
            t['mistakes'] += 1
            return dict(message=f'Cốt bánh {label} ({sec:.1f} giây). Không giao được — đổ bánh và nướng lại nhé.')
        return dict(message=f'Cốt bánh {label} ({sec:.1f} giây). Để nguội một nhịp rồi mới phủ kem.')
    if done == 'burnt':
        kit.waste(c, rack['item'], rack['qty'], rack['cost'], 'Khay bánh cháy')
        d['discarded'] += rack['qty']
        return dict(message=f'Khay {b["name"].lower()} cháy đen ({sec:.1f} giây) — bỏ và ghi hao hụt.')
    dense = bool(rack.get('dense'))
    q = 'pale' if done == 'pale' else 'dense' if dense else 'dark' if done == 'dark' else ('flat' if rack['flat'] else 'golden')
    _add_case(c, rack['item'], rack['qty'], c['day'], q, rack['cost'] // max(1, rack['qty']))
    kit.metric(c, 'trays_baked')
    extra = ' Bé Men đói nên bánh đặc ruột, không nở xốp — cho Bé Men ăn rồi mới nhào mẻ sau.' if q == 'dense' else ' Bột ủ quá lâu nên bánh hơi xẹp.' if rack['flat'] else ''
    return dict(message=f'Ra lò {rack["qty"]} {b["name"].lower()} {label} ({sec:.1f} giây), đã xếp lên tủ kính.{extra}')


def _case_action(s: dict, c: dict, d: dict, name: str, p: dict) -> dict:
    lot = next((l for l in d['case'] if l['id'] == p.get('lot')), None)
    kit.need(lot, 'Không có khay bánh này trong tủ.')
    b = BAKES[lot['item']]
    state = lot_state(c, lot['item'], lot['day'])
    if name == 'cb_markdown':
        kit.need(state == 'day_old', 'Chỉ bánh hôm qua còn trong hạn mới lên rổ giảm giá.')
        kit.need(not lot['sale'], 'Khay này đã ở rổ giảm giá.')
        lot['sale'] = True
        return dict(message=f'Đã chuyển {lot["qty"]} {b["name"].lower()} sang rổ “Bánh hôm qua −50%”, ghi rõ ngày ra lò. Cuối ca sẽ tính số bán được.')
    kit.confirm(p)
    if name == 'cb_donate':
        kit.need(b['donate'], b.get('rule') or 'Món này không được tặng lại.')
        kit.need(state != 'expired', 'Bánh đã quá hạn theo quy định — không tặng, chỉ bỏ.')
        d['case'] = [l for l in d['case'] if l['id'] != lot['id']]
        d['donated'] += lot['qty']
        kit.metric(c, 'donations')
        kit.log(s, c, 'donation', f'Tặng {lot["qty"]} {b["name"].lower()} (ra lò ngày {lot["day"]}) cho Bếp Cơm 0 Đồng Ngõ Mây, kèm nhãn ngày.')
        return dict(message=f'Đã đóng hộp {lot["qty"]} {b["name"].lower()} kèm nhãn ngày ra lò, gửi Bếp Cơm 0 Đồng Ngõ Mây. 💛')
    kit.waste(c, lot['item'], min(60, lot['qty']), lot['qty'] * lot['cost'], 'Bỏ bánh khỏi tủ kính')
    d['case'] = [l for l in d['case'] if l['id'] != lot['id']]
    d['discarded'] += lot['qty']
    return dict(message=f'Đã bỏ {lot["qty"]} {b["name"].lower()} và ghi hao hụt.')


def _dump(s: dict, c: dict, d: dict, t: dict, p: dict) -> dict:
    kit.confirm(p, 'Xác nhận đổ bỏ; nguyên liệu đã dùng được ghi hao hụt.')
    part = _one_of(p.get('part'), ('drink', 'cake'), 'Chọn đổ ly hay bỏ bánh.')
    if part == 'drink':
        dr = t['drink']
        kit.need(dr['container'] or dr['shots'] or dr['dose'] or dr['milk'] or dr['steaming'] or dr['pulling'], 'Ly đang trống.')
        kit.waste(c, 'drink', 1, dr['cost'], 'Đổ ly làm lại')
        t['drink'] = _empty_drink()
    else:
        ck = t['cake']
        kit.need(ck['sponge'] or ck['cream'], 'Chưa có bánh để bỏ.')
        kit.need(not ck['baking'], 'Cốt bánh đang trong lò.')
        kit.waste(c, 'sponge', 1, ck['cost'], 'Bỏ bánh kem làm lại')
        t['cake'] = _empty_cake()
    t['mistakes'] += 1
    kit.metric(c, 'remakes')
    return dict(message='Đã đổ bỏ. Làm lại từ đầu nhé.')


def _refuse(s: dict, c: dict, pl: dict, t: dict, why: str, line: str = '') -> dict:
    t['refused'] += 1
    t['mistakes'] += 1
    pl['refused'] += 1
    # The guest remembers handing it back (one small slip after the redo).
    cq.downgrade(t, 'returned', line or 'Đồ không đúng món mình gọi, phải chờ làm lại.', 'phải trả lại một lần')
    kit.log(s, c, 'refused', 'Khách không nhận: ' + why, t['npc'], t['id'])
    FS.flash(pl, 'bad', '↩️ Khách không nhận: ' + why)
    return dict(message='Khách không nhận: ' + why, refused=True)


def _cup_problem(n: dict, dr: dict) -> str | None:
    """Why the guest hands a drink back (None = they accept it)."""
    spec = DRINKS[n['drink']]
    if spec['milk'] and not dr['milk']:
        return f'{spec["name"]} mà không có sữa. Thêm sữa hoặc làm lại.'
    if not spec['milk'] and dr['milk']:
        return f'khách gọi {spec["name"]}, không phải đồ uống có sữa. Đổ ly và làm lại.'
    if spec['water'] and not dr['water']:
        return 'americano cần thêm nước — đây mới chỉ là espresso.'
    return None


def _serve(s: dict, c: dict, d: dict, pl: dict, t: dict, p: dict) -> dict:
    kit.confirm(p, 'Xác nhận giao cho khách.')
    n = t['needs']
    kind = n['kind']
    made = []
    if kind == 'drink':
        kit.need(not _hidden(t), 'Đoán đúng món khách muốn trước đã nhé.')
        tray = _tray(t)
        cups, cur, dr = t['cups'], t['cur'], t['drink']
        if not tray or cups[cur] is None:
            label = f'Ly {cur + 1}' if tray else 'Ly'
            kit.need(dr['container'], 'Chưa có ly.' if not tray else f'{label} chưa có ly.')
            kit.need(not dr['pulling'] and not dr['steaming'] and not dr['dose'], 'Còn shot đang chiết hoặc sữa đang đánh.')
            kit.need(dr['shots'], f'{label} chưa có espresso.')
        if tray:
            missing = [str(i + 1) for i, x in enumerate(cups) if x is None and i != cur]
            kit.need(not missing, 'Còn ly ' + ', '.join(missing) + ' chưa xong. Làm xong từng ly rồi giao cả khay nhé.')
    ev = FS.open_event(pl)
    kit.need(not ev, 'Có chuyện cần bạn quyết trước: ' + (EVENT_INDEX[ev['id']]['title'] if ev else '') + '.')
    if kind == 'drink':
        made = [x if x is not None else dr for x in cups] if tray else [dr]
        for i, cup in enumerate(made):
            problem = _cup_problem(_spec(t, i), cup)
            if problem:
                line = f'Gọi {DRINKS[_spec(t, i)["drink"]]["name"]} mà đưa ly khác hẳn, phải chờ pha lại.'
                if tray:
                    problem = f'ly {i + 1}: {problem}'
                    line = f'Ly {i + 1}: {line}'
                    # The finished cups stay on the tray; the returned one comes back to the bar.
                    if cups[cur] is None:
                        cups[cur] = dr
                    t['cur'] = i
                    t['drink'] = cups[i]
                    cups[i] = None
                return _refuse(s, c, pl, t, problem, line)
        for i, cup in enumerate(made):
            label = f'Ly {i + 1}: ' if tray else ''
            kit.need(cup['container'] != 'paper' or cup['lid'], label + 'đậy nắp ly mang về trước khi giao.')
        if n['pastry'] and t['bag']['items']:
            kit.need(t['bag']['bagged'] or not n['takeaway'], 'Cho bánh vào túi mang về trước khi giao.')
        back = _settle_or_send_back(s, c, pl, t, made)
        if back:
            return back
        d['drinks'] += len(made)
        kit.metric(c, 'drinks_served', len(made))
        if tray:
            t['cups'] = made
            t['drink'] = _empty_drink()
    elif kind == 'pastry':
        bag = t['bag']
        kit.need(bag['items'], 'Khay chưa có bánh.')
        kit.need(bag['bagged'] or not n['takeaway'], 'Cho bánh vào túi mang về trước khi giao.')
        if any(lot_state(c, x['item'], x['day']) == 'expired' for x in bag['items']):
            return _refuse(s, c, pl, t, 'có bánh đã quá hạn bán. Trả lại và lấy khay khác.',
                           'Trong túi có bánh quá hạn, phải chờ đổi khay khác.')
        back = _settle_or_send_back(s, c, pl, t, [])
        if back:
            return back
        d['pastries'] += len(bag['items'])
        kit.metric(c, 'pastries_sold')
    else:
        ck = t['cake']
        kit.need(ck['sponge'] and not ck['baking'], 'Chưa có cốt bánh.')
        if ck['sponge'] in ('pale', 'burnt'):
            return _refuse(s, c, pl, t, 'cốt bánh ' + ('sống ruột' if ck['sponge'] == 'pale' else 'cháy') + ' — không thể giao. Bỏ bánh và nướng lại.',
                           'Cốt bánh sống ruột, phải chờ nướng lại.' if ck['sponge'] == 'pale' else 'Cốt bánh cháy khét, phải chờ nướng lại.')
        kit.need(ck['cream'] and ck['text'], 'Bánh chưa phủ kem hoặc chưa viết chữ.')
        kit.need(ck['boxed'], 'Đóng hộp bánh trước khi giao.')
        if _letters(ck['text']) != _letters(n['text']):
            return _refuse(s, c, pl, t, f'chữ trên bánh ghi “{ck["text"]}” nhưng phiếu đặt là “{n["text"]}”. Cạo chữ và viết lại.',
                           f'Đặt bánh ghi “{n["text"]}” mà chữ viết sai, phải chờ cạo chữ viết lại.')
        back = _settle_or_send_back(s, c, pl, t, [])
        if back:
            return back
        d['cakes'] += 1
        kit.metric(c, 'cakes_done')
    first = made[0] if made else t['drink']
    t['served'] = dict(drink=copy.deepcopy(first), cups=copy.deepcopy(made), bag=copy.deepcopy(t['bag']), cake=copy.deepcopy(t['cake']), day=c['day'])
    r = cq.react(s, c, t, t['quoted_price'], who=_who(t))
    price = r['pay']
    kit.complete(s, c, t, price, f'Bạn đã làm “{t["title"]}” cho khách.')
    lines = FS.after_serve(s, c, ID, pl, t, _walkin_chance(c, pl))
    learned = _book_visit(c, d, t)
    if learned:
        lines.append(learned)
    lines += _after_rules(s, c, pl, t)
    lines += _counter_buyers(s, c, d, pl)
    opened = FS.trigger(s, c, pl, EVENT_INDEX)
    if opened:
        lines.append('⚡ ' + EVENT_INDEX[opened['id']]['title'])
    else:
        perfect = t['mistakes'] == 0 and not t['refused']
        FS.flash(pl, 'good' if perfect else 'info', ('⭐ Hoàn hảo! ' if perfect else '☕ Đã giao. ') + ' '.join(lines[:2]))
    head = f'Đã giao cho khách · +{price} xu.'
    if r['message']:
        head += ' ' + r['message']
    return dict(message=head + (' ' + ' '.join(lines) if lines else ' Khách đang thưởng thức và sẽ để lại đánh giá.'), celebrate=True)


def _who(t: dict) -> str:
    people = kit.eng().NPC_INDEX
    return people[t['npc']].get('display_name') or 'Khách' if t['npc'] in people else 'Khách'


def _cup_slip(t: dict, code: str, i: int | None, sev: int, text: str, note: str, safety: bool = False) -> None:
    if i is None:
        cq.slip(t, code, sev, text, note, safety)
    else:
        cq.slip(t, f'{code}{i}', sev, f'Ly {i + 1}: {text}', f'ly {i + 1}: {note}', safety)


def _drink_slips(t: dict, i: int | None, sp: dict, cup: dict, rules: dict) -> None:
    """What the guest finds in one cup against what they asked."""
    milk = cup['milk']
    if sp['lactose'] and milk and MILKS[milk['kind']]['lactose']:
        cq.slip(t, 'lactose', 3, 'Đã dặn không uống được sữa bò mà ly vẫn pha sữa bò. Uống xong đau bụng cả buổi.',
                'pha sữa bò cho khách không dung nạp lactose', safety=True)
    if sp['decaf'] and any(x['beans'] != 'decaf' for x in cup['shots']):
        cq.slip(t, 'caffeine', 3, 'Đã dặn phải kiêng caffeine vì bệnh tim mà ly vẫn là cà phê thường. Uống xong tim đập thình thịch.',
                'pha cà phê thường cho khách phải kiêng caffeine', safety=True)
    if rules.get('sour_milk') and milk and milk['kind'] == 'milk':
        cq.slip(t, 'sour_milk', 3, 'Sữa trong ly có mùi chua, uống một ngụm là thấy lợm giọng.', 'dùng sữa đã chua', safety=True)
    if sp['milk'] and milk and milk['kind'] != sp['milk'] and not (sp['lactose'] and MILKS[milk['kind']]['lactose']):
        want, got = MILKS[sp['milk']]['name'].lower(), MILKS[milk['kind']]['name'].lower()
        _cup_slip(t, 'milk', i, 2, f'Gọi {want} mà pha {got}, vị khác hẳn.', f'pha {got} thay vì {want}')
    if cup['ice'] != sp['iced']:
        if sp['iced']:
            _cup_slip(t, 'temp', i, 2, 'Gọi đồ đá mà đưa ly nóng hổi, trời nóng uống không nổi.', 'gọi đá mà đưa ly nóng')
        else:
            _cup_slip(t, 'temp', i, 2, 'Gọi ly nóng mà lại bỏ đá, lạnh ngắt.', 'gọi nóng mà bỏ đá')
    if sp['foam'] and milk and milk['mode'] == 'steam' and milk['foam'] != sp['foam']:
        if sp['foam'] == 'thick':
            _cup_slip(t, 'foam', i, 1, 'Dặn bọt dày mà bọt mỏng dính.', 'bọt mỏng thay vì bọt dày')
        else:
            _cup_slip(t, 'foam', i, 1, 'Dặn bọt mỏng mà bọt dày cộp.', 'bọt dày thay vì bọt mỏng')
    if milk and milk['tex'] == 'scalded':
        _cup_slip(t, 'scalded', i, 1, 'Sữa bị khét, uống mất cả ngon.', 'sữa khét')
    elif milk and milk['tex'] == 'cool':
        _cup_slip(t, 'cool', i, 1, 'Sữa nguội ngắt, không ấm bụng chút nào.', 'sữa còn nguội')
    if cup['size'] != sp['size']:
        if sp['size'] == 'L':
            _cup_slip(t, 'size', i, 2, 'Trả tiền ly lớn mà nhận ly nhỏ xíu.', 'ly nhỏ thay vì ly lớn')
        else:
            _cup_slip(t, 'size', i, 1, 'Gọi ly nhỏ mà đưa ly lớn, uống không hết.', 'ly lớn thay vì ly nhỏ')
    got = len(cup['shots'])
    if got < sp['shots']:
        _cup_slip(t, 'shots', i, 2, f'Dặn {sp["shots"]} shot mà chỉ có {got}, uống nhạt thếch.', f'{got} shot thay vì {sp["shots"]}')
    elif got > sp['shots']:
        _cup_slip(t, 'shots', i, 1, f'Dặn {sp["shots"]} shot mà pha tới {got}, đắng quá.', f'{got} shot thay vì {sp["shots"]}')
    if not sp['decaf'] and any(x['beans'] != sp['beans'] for x in cup['shots']):
        name = BEAN_INDEX[sp['beans']]['name']
        _cup_slip(t, 'beans', i, 1, f'Dặn hạt {name} mà pha hạt khác, vị lạ hẳn.', 'sai loại hạt')
    xs = [x['x'] for x in cup['shots']]
    if 'sour' in xs:
        _cup_slip(t, 'shot', i, 1, 'Cà phê chua gắt, như chiết vội.', 'espresso chiết thiếu')
    elif 'bitter' in xs:
        _cup_slip(t, 'shot', i, 1, 'Cà phê đắng khét, uống không nổi.', 'espresso chiết quá')
    if cup['water'] and not DRINKS[sp['drink']]['water']:
        _cup_slip(t, 'water', i, 2, f'Gọi {DRINKS[sp["drink"]]["name"]} mà bị pha loãng nước.', 'bị pha loãng')
    if sp['art'] and cup['art'] != sp['art']:
        _cup_slip(t, 'art', i, 1, f'Dặn vẽ hình {ART_INDEX[sp["art"]]["name"].lower()} mà ly không có hình như hẹn.', 'không vẽ đúng hình đã hẹn')
    if sp['takeaway'] and cup['container'] != 'paper':
        _cup_slip(t, 'cup', i, 2, 'Dặn mang đi mà rót vào ly dùng tại quán, phải xin ly giấy đổ sang.', 'mang đi mà không rót ly giấy')
    elif not sp['takeaway'] and cup['container'] == 'paper':
        _cup_slip(t, 'cup', i, 1, 'Ngồi uống tại quán mà đưa ly giấy mang về.', 'uống tại quán mà đưa ly giấy')


def _bag_slips(c: dict, t: dict, want: dict, allergy: str | None, day_old_ok: bool) -> None:
    """What the guest finds in the bag of pastries."""
    items = t['bag']['items']
    have = {}
    for x in items:
        have[x['item']] = have.get(x['item'], 0) + 1
    if allergy and any(allergy in BAKES[x['item']]['allergens'] for x in items):
        label = ALLERGEN_LABEL[allergy]
        cq.slip(t, 'allergen', 3, f'Đã dặn có người dị ứng {label} mà túi vẫn có bánh chứa {label}. May mà nhìn thấy trước khi ăn!',
                f'bỏ bánh có {label} cho khách dị ứng', safety=True)
    names = ', '.join(BAKES[k]['name'].lower() for k in want)
    if want and not items:
        cq.slip(t, 'no_bake', 2, f'Gọi kèm {names} mà không thấy bánh đâu.', f'thiếu {names}')
    elif want and not any(have.get(k) for k in want):
        cq.slip(t, 'wrong_bake', 3, f'Mua {names} mà túi toàn bánh khác.', 'đưa nhầm loại bánh')
    else:
        short = [k for k, q in want.items() if have.get(k, 0) < q]
        if short:
            k = short[0]
            cq.slip(t, 'bake_short', 2, f'Mua {want[k]} {BAKES[k]["name"].lower()} mà túi chỉ có {have.get(k, 0)}.', f'thiếu {BAKES[k]["name"].lower()}')
    if not day_old_ok and any(max(0, c['day'] - x['day']) > BAKES[x['item']]['fresh'] for x in items):
        cq.slip(t, 'day_old', 1, 'Dặn bánh mới ra lò mà đưa bánh hôm qua, cứng rồi.', 'đưa bánh hôm qua')
    if any(x['q'] in ('pale', 'flat') for x in items):
        cq.slip(t, 'bake_q', 1, 'Bánh nhạt màu, xẹp lép, nhìn không muốn ăn.', 'bánh nướng chưa đạt')
    elif any(x['q'] == 'dense' for x in items):
        cq.slip(t, 'bake_q', 1, 'Bánh mì đặc ruột, nhai mỏi cả hàm.', 'bánh mì đặc ruột')


def _cake_slips(t: dict) -> None:
    n, ck = t['needs'], t['cake']
    if ck['color'] != n['color']:
        want, got = COLORS[n['color']]['name'].lower(), COLORS[ck['color']]['name'].lower()
        cq.slip(t, 'color', 2, f'Đặt kem màu {want} mà ra màu {got}, không hợp tiệc chút nào.', f'kem màu {got} thay vì {want}')
    if ck['cream'] != n['cream']:
        want, got = CREAMS[n['cream']]['name'].lower(), CREAMS[ck['cream']]['name'].lower()
        cq.slip(t, 'cream', 2, f'Đặt {want} mà làm {got}.', f'{got} thay vì {want}')
    if ck['melted']:
        cq.slip(t, 'melted', 2, 'Kem chảy xệ hết cả, chụp hình không nổi.', 'kem chảy xệ')


def _record_slips(c: dict, t: dict, made: list) -> list[int]:
    """At the hand-off: record what is wrong. Returns the cups to send back (tray index, or 0)."""
    n = t['needs']
    rules = _plan_rules(c)
    faulty = []
    if n['kind'] == 'drink':
        tray = _tray(t)
        for i, cup in enumerate(made):
            before = len(cq.slips(t))
            _drink_slips(t, i if tray else None, _spec(t, i), cup, rules)
            if len(cq.slips(t)) > before:
                faulty.append(i)
        if n['pastry']:
            _bag_slips(c, t, n['pastry'], None, False)
    elif n['kind'] == 'pastry':
        _bag_slips(c, t, n['items'], n['allergy'], n['day_old_ok'])
    else:
        _cake_slips(t)
    return faulty


def _settle_or_send_back(s: dict, c: dict, pl: dict, t: dict, made: list) -> dict | None:
    """Record the mistakes; if the guest sends a drink or the bag back to fix, put it back
    on the counter and return the result (the order stays open). None = hand it over."""
    faulty = _record_slips(c, t, made)
    if not cq.slips(t):
        return None
    if not t['mistakes']:
        t['mistakes'] = 1
    fresh = any(x['code'] != 'returned' for x in cq.slips(t))
    if t['needs']['kind'] == 'cake' or not fresh or cq.decide(c, t, remake=True) != 'remake':
        return None
    cq.react(s, c, t, t['quoted_price'], remake=True, who=_who(t))
    first = cq.slips(t)[0]['text']
    if t['needs']['kind'] == 'drink' and faulty:
        if _tray(t):
            cups, cur = t['cups'], t['cur']
            if cups[cur] is None:
                cups[cur] = t['drink']
            i = faulty[0]
            t['cur'] = i
            t['drink'] = cups[i]
            cups[i] = None
    else:
        t['bag']['bagged'] = False
    if c['life'].get('mode') != 'calm':
        t['patience'] = max(25, t.get('patience', 100) - 10)
    cq.downgrade(t, 'returned', f'{first} Phải làm lại.', 'phải làm lại')
    kit.log(s, c, 'refused', 'Khách trả lại: ' + first, t['npc'], t['id'])
    FS.flash(pl, 'bad', '↩️ Khách trả lại: ' + first)
    return dict(message=f'{_who(t)}: “{first}” Khách đưa lại, sửa giúp khách nhé.', refused=True, correct=False)


def _counter_buyers(s: dict, c: dict, d: dict, pl: dict) -> list[str]:
    """Passers-by buy straight from the display case (fresh first, then the −50% basket)."""
    count = MOD_INDEX[pl['mod']].get('buyers', 1)
    sold, missed, income = {}, [], 0
    mult = 1.1 if pl['mod'] == 'festival' else 1.0
    for i in range(count):
        r = kit.rng(ID, 'buyer', c['day'], pl['served'], i)
        items = [k for k in CASE_ITEMS if BAKES[k]['unlock'] <= kit.level(c) or _case_count(d, k)]
        want = r.choices(items, [BUYER_WANTS[k] for k in items])[0]
        qty = 2 if r.random() < 0.3 else 1
        lots = [l for l in d['case'] if l['item'] == want and l['qty'] > 0]
        fresh = sorted((l for l in lots if lot_state(c, want, l['day']) == 'fresh' and not l['sale']), key=lambda l: l['day'])
        cheap = [l for l in lots if l['sale'] and lot_state(c, want, l['day']) == 'day_old']
        lot = fresh[0] if fresh else cheap[0] if cheap else None
        b = BAKES[want]
        if not lot:
            pl['missed'] += 1
            missed.append(b['name'].lower())
            continue
        q = min(qty, lot['qty'])
        unit = kit.price(c, want, SPEC['prices'][want])
        unit = max(1, unit // 2) if lot['sale'] else unit
        amount = max(1, round(unit * q * mult))
        lot['qty'] -= q
        if lot['qty'] <= 0:
            d['case'] = [l for l in d['case'] if l['id'] != lot['id']]
        kit.money(s, c, amount, f'Khách mua lẻ {q} {b["name"].lower()}' + (' (rổ −50%)' if lot['sale'] else ''), None, 'revenue')
        pl['sales'] += q
        d['counter_sold'] = d.get('counter_sold', 0) + q
        kit.metric(c, 'counter_sales', q)
        income += amount
        sold[want] = sold.get(want, 0) + q
    lines = []
    if sold:
        what = ', '.join(f'{q} {BAKES[k]["emoji"]}' for k, q in sold.items())
        lines.append(f'🛍️ Khách mua lẻ {what} · +{income} xu.')
    if missed:
        lines.append('😕 Khách hỏi ' + ', '.join(dict.fromkeys(missed)) + ' mà tủ hết bánh mới — nướng mẻ mới ở tab Lò nhé.')
    return lines


# --- review -------------------------------------------------------------------

def _speed(t: dict) -> dict:
    patience = t.get('patience', 100)
    score = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    return dict(key='speed', label='Thời gian chờ', score=score, note=f'kiên nhẫn còn {patience}%')


def _pastry_rows(t: dict, want: dict, day: int) -> tuple[int, str, int, str]:
    """(freshness score, note, accuracy penalty, note) for the pastries in the bag."""
    n = t['needs']
    items = t['served']['bag']['items']
    fresh, notes = 5, []
    for x in items:
        age = max(0, day - x['day'])
        b = BAKES[x['item']]
        sc = LOT_Q_SCORE[x['q']]
        if age > b['fresh'] and not n.get('day_old_ok'):
            sc = min(sc, 3)
            notes.append(f'{b["name"].lower()} là bánh hôm qua')
        elif x['q'] != 'golden':
            notes.append(f'{b["name"].lower()} {LOT_Q_LABEL[x["q"]]}')
        fresh = min(fresh, sc)
    have = {}
    for x in items:
        have[x['item']] = have.get(x['item'], 0) + 1
    missing = sum(max(0, q - have.get(k, 0)) for k, q in want.items())
    extra = sum(max(0, q - want.get(k, 0)) for k, q in have.items())
    acc_notes = []
    if missing:
        acc_notes.append(f'thiếu {missing} bánh')
    if extra:
        acc_notes.append(f'thừa {extra} bánh không gọi')
    return fresh, ', '.join(dict.fromkeys(notes)) or 'bánh mới, vàng đều', min(3, missing + (1 if extra else 0)), ', '.join(acc_notes)


SHOT_SCORE = dict(sour=2, bright=4, balanced=5, strong=4, bitter=2)


def _cup_score(n: dict, dr: dict, rules: dict) -> tuple:
    """(taste, note, accuracy penalty, notes, presentation, note) for one served drink."""
    worst = min(dr['shots'], key=lambda x: SHOT_SCORE[x['x']])
    taste, tnote = SHOT_SCORE[worst['x']], 'espresso ' + SHOT_LABEL[worst['x']]
    if any(abs(x['grams'] - DOSE_TARGET) >= 3 for x in dr['shots']):
        taste, tnote = taste - 1, tnote + ', liều bột lệch'
    if dr['milk'] and dr['milk']['mode'] == 'steam':
        ms = dict(cool=3, silky=5, hot=4, scalded=2)[dr['milk']['tex']]
        if ms < taste:
            taste, tnote = ms, 'sữa ' + MILK_TEX_LABEL[dr['milk']['tex']]
    if rules.get('grinder') and taste > 4:
        taste, tnote = 4, 'bột xay không đều, vị hơi gắt'
    if rules.get('sour_milk') and dr['milk'] and dr['milk']['kind'] == 'milk':
        taste, tnote = min(taste, 2), 'sữa có mùi chua'
    pen, notes = 0, []
    if any(x['beans'] != n['beans'] for x in dr['shots']):
        pen, notes = pen + 1, notes + ['sai loại hạt']
    if len(dr['shots']) != n['shots']:
        pen, notes = pen + 1, notes + [f'{len(dr["shots"])} shot thay vì {n["shots"]}']
    if dr['size'] != n['size']:
        pen, notes = pen + 1, notes + ['sai cỡ ly']
    if dr['milk'] and dr['milk']['kind'] != n['milk']:
        pen, notes = pen + 1, notes + ['sai loại sữa']
    if n['foam'] and dr['milk'] and dr['milk']['foam'] != n['foam']:
        pen, notes = pen + 1, notes + ['bọt ' + ('mỏng' if dr['milk']['foam'] == 'thin' else 'dày') + ' không đúng món']
    if dr['ice'] != n['iced']:
        pen, notes = pen + 1, notes + ['đá không đúng yêu cầu']
    if dr['water'] and not DRINKS[n['drink']]['water']:
        pen, notes = pen + 1, notes + ['bị pha loãng']
    want_cup = 'paper' if n['takeaway'] else 'glass' if n['iced'] else 'mug'
    pres, pnote = 5, 'ly đẹp, đúng kiểu'
    if dr['container'] != want_cup:
        pres, pnote = 3, 'sai loại ly'
    if n['art']:
        if dr['art'] == n['art']:
            pnote = 'latte art ' + ART_INDEX[n['art']]['name'].lower() + ' đẹp'
        elif dr['art'] in ART_INDEX:
            pres, pnote = min(pres, 4), 'vẽ hình khác khách dặn'
        else:
            pres, pnote = min(pres, 3), 'không có hình vẽ như đã hẹn' if not dr['art'] else 'hình vẽ bị loang'
    return max(1, taste), tnote, pen, notes, pres, pnote


def _plan_rules(c: dict) -> dict:
    return _peek_plan(c)['rules']


def feedback(c: dict, t: dict) -> dict:
    n = t['needs']
    sv = t['served']
    day = sv.get('day', c['day'])
    rules = _plan_rules(c)
    rows = []
    if n['kind'] == 'drink':
        cups = sv.get('cups') or [sv['drink']]
        tray = len(cups) > 1
        tag = (lambda i: f'ly {i + 1}: ') if tray else (lambda i: '')
        scored = [_cup_score(_spec(t, i), cup, rules) for i, cup in enumerate(cups)]
        ti = min(range(len(scored)), key=lambda i: scored[i][0])
        rows.append(dict(key='taste', label='Hương vị', score=scored[ti][0], note=tag(ti) + scored[ti][1]))
        pen = max(x[2] for x in scored)
        notes = [tag(i) + note for i, x in enumerate(scored) for note in x[3]]
        if n['pastry']:
            fresh, fnote, ppen, pnote = _pastry_rows(t, n['pastry'], day)
            pen += ppen
            if pnote:
                notes.append(pnote)
            if fresh < 5:
                rows.append(dict(key='fresh', label='Bánh kèm', score=fresh, note=fnote))
        rows.append(dict(key='accuracy', label='Đúng order', score=max(1, 5 - pen), note=', '.join(notes) or 'đúng từng chi tiết'))
        pi = min(range(len(scored)), key=lambda i: scored[i][4])
        pnote = scored[pi][5] if scored[pi][4] < 5 or not tray else 'cả khay đẹp, đúng kiểu'
        rows.append(dict(key='presentation', label='Trình bày', score=scored[pi][4], note=(tag(pi) if scored[pi][4] < 5 else '') + pnote))
        if n.get('style') == 'mood':
            g = t.get('guesses') or []
            at = g.index(n['drink']) + 1 if n['drink'] in g else 0
            rows.append(dict(key='mood', label='Hiểu ý khách', score=5 if at == 1 else 4 if at == 2 else 3,
                             note='đoán trúng ngay món khách thèm' if at == 1 else 'đoán lần hai mới trúng' if at == 2 else 'khách phải tự nói ra món'))
    elif n['kind'] == 'pastry':
        fresh, fnote, pen, pnote = _pastry_rows(t, n['items'], day)
        rows.append(dict(key='fresh', label='Độ tươi của bánh', score=fresh, note=fnote))
        rows.append(dict(key='accuracy', label='Đúng món', score=max(1, 5 - pen), note=pnote or 'đúng loại, đủ số'))
        rows.append(dict(key='packing', label='Đóng gói', score=5 if sv['bag']['bagged'] or not n['takeaway'] else 3, note='túi gọn, có tem ngày ra lò'))
    else:
        ck = sv['cake']
        bake = dict(golden=5, dark=4).get(ck['sponge'], 3)
        bnote = 'cốt bánh mềm xốp' if bake == 5 else 'cốt hơi sậm màu'
        if ck['melted']:
            bake, bnote = 2, 'kem chảy xệ vì phủ lúc bánh còn ấm'
        rows.append(dict(key='bake', label='Cốt bánh & kem', score=bake, note=bnote))
        pen, notes = 0, []
        if ck['cream'] != n['cream']:
            pen, notes = pen + 1, notes + ['sai loại kem']
        if ck['color'] != n['color']:
            pen, notes = pen + 1, notes + ['sai màu kem']
        rows.append(dict(key='accuracy', label='Đúng phiếu đặt', score=max(1, 5 - pen), note=', '.join(notes) or 'đúng kem, đúng màu, đúng tên'))
        rows.append(dict(key='presentation', label='Chữ & hộp', score=4 if ck['scraped'] else 5, note='chữ phải viết lại, mặt kem hơi lem' if ck['scraped'] else 'chữ rõ, hộp đẹp'))
    rows.append(_speed(t))
    if t.get('regular'):
        rows.append(dict(key='regular', label='Nhớ khách quen', score=5 if t.get('greeted') else 4,
                         note='được chào đúng món quen, thấy mình được nhớ' if t.get('greeted') else 'tiệm chưa hỏi han món quen'))
    if t['refused']:
        rows.append(dict(key='care', label='Cẩn thận', score=2, note='phải làm lại sau khi khách trả'))
    cap = 5
    if (t.get('guest') or {}).get('kind') == 'picky' and t['mistakes']:
        cap = 3
    if rules.get('sour_milk') and n['kind'] == 'drink' and any(cup['milk'] and cup['milk']['kind'] == 'milk' for cup in (sv.get('cups') or [sv['drink']])):
        cap = min(cap, 2)
    return dict(criteria=rows, cap=cap)


# --- projections & validation ----------------------------------------------------

def public_task(t: dict) -> dict:
    v = tree_copy(t)
    if v.get('gen') != GEN:
        _upgrade_task(v, None)
    v['cups_total'] = _cups_total(v)
    if not v['known']:
        v['needs'] = None
        v['quoted_price'] = None
    elif _hidden(v):
        # Mood order: only the feeling (and a clue after a wrong pick) until the drink is found.
        n = v['needs']
        mood = dict(text=n['mood']['text'], options=list(n['mood']['options']))
        if v.get('guesses'):
            mood['clue'] = n['mood']['clue']
        v['needs'] = dict(kind='drink', style='mood', mood=mood, takeaway=n['takeaway'], pastry={})
        v['quoted_price'] = None
    return v


def public_data(c: dict) -> dict:
    d = tree_copy(kit.data(c))
    for lot in d['case']:
        lot['age'] = _age(c, lot['day'])
        lot['state'] = lot_state(c, lot['item'], lot['day'])
    for tray in d['proof']:
        # Beats still to wait before the bake click itself (which is one beat).
        tray['left'] = max(0, tray['ready'] - (c['turn'] + 1))
        tray['over'] = c['turn'] + 1 > tray['ready'] + OVERPROOF
    d['groups'] = [dict(task=t['id'], start=t['drink']['pulling'], flow=round(_flow(t['drink']['dose']), 3) if t['drink']['dose'] else 1.0) for t in _pulling(c)]
    d['wand'] = [dict(task=t['id'], start=t['drink']['steaming']) for t in _steaming(c)]
    d['cooling'] = {t['id']: max(0, t['cake']['cool_turn'] - (c['turn'] + 1)) for t in c['tasks'] if _open(t) and t['cake']['sponge']}
    for r in d['oven']:
        r.setdefault('shift', 0)
    pl = _peek_plan(c)
    d.pop('plan', None)
    d.pop('ev_hist', None)
    for k, v in (('regulars', {}), ('grades', []), ('counter_sold', 0)):
        d.setdefault(k, v)
    d['day'] = FS.public_plan(c, pl, MODS, EVENT_INDEX)
    d['rules'] = {k: tree_copy(v) for k, v in pl['rules'].items() if not k.startswith('_')}
    d['oven_shift'] = HOT_OVEN if pl['rules'].get('hot_oven') else 0
    d['buyers'] = MOD_INDEX[pl['mod']].get('buyers', 1)
    d['wants'] = [k for k in CASE_ITEMS if BAKES[k]['unlock'] <= kit.level(c)]
    d.update(_public_care(c, kit.data(c)))
    return d


def _tomorrow(c: dict) -> dict:
    m = FS.pick_mod(ID, c['day'] + 1, MODS)
    return dict(emoji=m['emoji'], label=m['label'], hint=m['hint'], busy=m.get('buyers', 1) >= 2)


def _starter_view(c: dict, st: dict) -> dict:
    band = _band(st['strength'])
    return dict(strength=st['strength'], fed_today=st['fed'] == c['day'], feeds=st['feeds'], band=band[1], emoji=band[2], label=band[3],
                effect=band[5], beats=band[4], gain=FEED_GAIN_HUNGRY if st['strength'] < 40 else FEED_GAIN,
                night=NIGHT_FED if st['fed'] == c['day'] else NIGHT_UNFED)


def _public_care(c: dict, raw: dict) -> dict:
    """Read-only projection of the care loop (works on an old, unmigrated save too)."""
    st = raw.get('starter') or _care_initial()['starter']
    starter = _starter_view(c, st)
    cold = [dict(tree_copy(x), nights=c['day'] - x['day'], bakeable=x['day'] < c['day'], last=c['day'] + 1 - x['day'] > COLD_NIGHTS)
            for x in raw.get('cold') or []]
    book = []
    for npc, rec in _book(raw).items():
        i = _npc_index(npc)
        if i is None or not rec.get('visits'):
            continue
        nxt = next((at for at in NOTE_AT if at > rec['visits']), None)
        book.append(dict(npc=npc, name=PEOPLE[i][0], visits=rec['visits'], notes=tree_copy(_notes_of(raw, npc)),
                         next=nxt - rec['visits'] if nxt else None))
    book.sort(key=lambda r: (-len(r['notes']), -r['visits']))
    tm = _tomorrow(c)
    night = raw.get('night')
    return dict(starter=starter, cold=cold, book=book, tomorrow=tm, care=_care_rows(c, raw, starter, cold, tm),
                night=tree_copy(night['lines']) if isinstance(night, dict) and night.get('day') == c['day'] else [])


def _care_rows(c: dict, raw: dict, starter: dict, cold: list, tm: dict) -> list[dict]:
    """Today's care list (rows for ui-kit reqList: ok True/False/None, icon, label, value, note, tone)."""
    rows = []
    if starter['fed_today']:
        rows.append(dict(ok=True, icon='🫙', label='Bé Men đã ăn hôm nay', value=f'{starter["strength"]}%',
                         note=f'{starter["emoji"]} {starter["label"]}: {starter["effect"]}'))
    else:
        rows.append(dict(ok=None, icon='🫙', label='Cho Bé Men ăn (1 bột mì)', value=f'{starter["strength"]}%',
                         note=f'{starter["emoji"]} {starter["label"]}: {starter["effect"]}. Không cho ăn: đêm nay −{NIGHT_UNFED}%.',
                         tone='warn' if starter['band'] == 'hungry' else ''))
    old = [l for l in raw.get('case') or [] if l['qty'] > 0 and lot_state(c, l['item'], l['day']) == 'day_old']
    waiting = sum(l['qty'] for l in old if not l['sale'])
    if waiting:
        rows.append(dict(ok=None, icon='🧺', label=f'{waiting} bánh hôm qua chờ xử lý', note='Lên rổ −50%, tặng bếp cơm (kèm nhãn ngày) hoặc bỏ.'))
    elif old:
        rows.append(dict(ok=True, icon='🧺', label='Bánh hôm qua đã lên rổ −50%', value=str(sum(l['qty'] for l in old))))
    for x in cold:
        b = BAKES[x['item']]
        if x['bakeable']:
            rows.append(dict(ok=None, icon='❄️', label=f'Nướng khay {b["name"].lower()} ủ lạnh', value=f'đêm {x["nights"]}',
                             note='Đêm cuối: nướng hôm nay kẻo bột quá chua.' if x['last'] else '',
                             tone='warn' if x['last'] else ''))
        else:
            rows.append(dict(ok=True, icon='❄️', label=f'{b["name"]} đang ủ lạnh cho ngày mai'))
    warm = raw.get('proof') or []
    if warm:
        rows.append(dict(ok=None, icon='🌡️', label=f'{len(warm)} khay bột đang ủ ấm', note='Nướng trước khi khép ca hoặc cất tủ mát — để qua đêm sẽ hỏng.',
                         tone='warn'))
    if tm['busy']:
        chilled = any(x['day'] == c['day'] for x in cold)
        rows.append(dict(ok=True if chilled else None, icon='📅', label=f'Mai {tm["label"].lower()}: ủ lạnh sẵn 1 khay bột tối nay'))
    return rows


def _valid_ts(v) -> bool:
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 10**11)


def _valid_drink(dr) -> None:
    need = kit.need
    need(isinstance(dr, dict) and set(_empty_drink()) <= set(dr), 'Ly thiếu dữ liệu.')
    need(dr['container'] in (None, *CONTAINERS) and dr['size'] in (None, 'S', 'L'), 'Ly sai.')
    for k in ('ice', 'water', 'lid'):
        need(type(dr[k]) is bool, 'Trạng thái ly sai.')
    need(_valid_ts(dr['pulling']) and _valid_ts(dr['steaming']), 'Đồng hồ máy pha sai.')
    if dr['dose'] is not None:
        need(isinstance(dr['dose'], dict) and dr['dose'].get('beans') in BEAN_INDEX and dr['dose'].get('grind') in GRIND, 'Tay cầm sai.')
        kit.integer(dr['dose'].get('grams'), DOSE_MIN, DOSE_MAX)
    need(dr['pulling'] is None or dr['dose'] is not None, 'Shot đang chiết thiếu bột.')
    need(isinstance(dr['shots'], list) and len(dr['shots']) <= 3, 'Số shot sai.')
    for x in dr['shots']:
        need(isinstance(x, dict) and x.get('beans') in BEAN_INDEX and x.get('grind') in GRIND and x.get('x') in SHOT_CLASSES, 'Shot sai.')
        kit.integer(x.get('grams'), DOSE_MIN, DOSE_MAX)
        need(isinstance(x.get('sec'), (int, float)) and 0 <= x['sec'] <= 999, 'Thời gian chiết sai.')
    if dr['milk'] is not None:
        m = dr['milk']
        need(isinstance(m, dict) and m.get('kind') in MILKS and m.get('mode') in ('steam', 'cold'), 'Sữa sai.')
        if m['mode'] == 'steam':
            need(m.get('foam') in ('thin', 'thick') and m.get('tex') in MILK_TEX and isinstance(m.get('temp'), (int, float)) and 0 <= m['temp'] <= 99, 'Sữa đánh sai.')
        else:
            need(m.get('foam') is None and m.get('tex') is None and m.get('temp') is None, 'Sữa lạnh sai.')
    need((dr['steaming'] is None) == (dr['steam'] is None), 'Vòi hơi sai.')
    if dr['steam'] is not None:
        need(isinstance(dr['steam'], dict) and dr['steam'].get('kind') in MILKS and dr['steam'].get('foam') in ('thin', 'thick'), 'Vòi hơi sai.')
    need(dr['art'] in (None, 'blob', *ART_INDEX), 'Hình vẽ sai.')
    kit.integer(dr['cost'], 0, 10000)


def validate_task(t: dict, original: dict) -> None:
    need = kit.need
    need(t.get('gen') == GEN, 'Đơn cũ chưa được cập nhật.')
    _valid_drink(t['drink'])
    total = _cups_total(t)
    cups = t.get('cups')
    need(isinstance(cups, list) and len(cups) == total, 'Khay ly sai.')
    kit.integer(t.get('cur'), 0, total - 1)
    for x in cups:
        if x is not None:
            _valid_drink(x)
            need(x['pulling'] is None and x['steaming'] is None and x['dose'] is None and x['container'], 'Ly trên khay sai.')
    need(type(t.get('guessed')) is bool, 'Trạng thái đoán món sai.')
    g = t.get('guesses')
    need(isinstance(g, list) and len(g) <= 3 and len(set(g)) == len(g) and all(isinstance(x, str) and x in DRINKS for x in g), 'Lượt đoán món sai.')
    if t['needs'].get('style') != 'mood':
        need(not t['guessed'] and not g, 'Đơn này không cần đoán món.')
    elif not t['guessed']:
        need(not t['drink']['container'] and not t['drink']['shots'], 'Chưa hiểu ý khách mà đã pha.')
    bag = t['bag']
    need(isinstance(bag, dict) and isinstance(bag.get('items'), list) and len(bag['items']) <= 12 and type(bag.get('bagged')) is bool
         and type(bag.get('has_bag')) is bool and (bag['has_bag'] or not bag['bagged']), 'Khay bánh sai.')
    for x in bag['items']:
        need(isinstance(x, dict) and x.get('item') in CASE_ITEMS and x.get('q') in LOT_Q, 'Bánh trong khay sai.')
        kit.integer(x.get('day'), 1, 10**7)
        kit.integer(x.get('cost'), 0, 10000)
    kit.integer(bag.get('cost'), 0, 10000)
    ck = t['cake']
    need(isinstance(ck, dict) and set(_empty_cake()) <= set(ck), 'Bánh kem thiếu dữ liệu.')
    need(type(ck['baking']) is bool and type(ck['melted']) is bool and type(ck['boxed']) is bool, 'Trạng thái bánh kem sai.')
    need(ck['sponge'] in (None, *DONENESS) and ck['cream'] in (None, *CREAMS) and ck['color'] in (None, *COLORS), 'Bánh kem sai.')
    need(ck['text'] is None or isinstance(ck['text'], str), 'Chữ trên bánh sai.')
    if ck['text'] is not None:
        kit.text(ck['text'], 40, 2)
    kit.integer(ck['cool_turn'], 0, 10**9)
    kit.integer(ck['scraped'], 0, 5)
    kit.integer(ck['cost'], 0, 10000)
    kit.integer(t['refused'], 0, 1000)
    need(t['quoted_price'] is None or 1 <= kit.integer(t['quoted_price'], 1, 5000), 'Giá sai.')
    need(t['served'] is None or (isinstance(t['served'], dict) and {'drink', 'bag', 'cake'} <= set(t['served'])), 'Món đã giao sai.')
    # Regulars' notes card (tasks saved before it simply have neither key).
    regular = kit.integer(t.get('regular', 0), 0, 2)
    need(type(t.get('greeted', False)) is bool and (regular or not t.get('greeted')), 'Lời chào khách quen sai.')


def validate_data(c: dict) -> None:
    need = kit.need
    d = _migrate(c)
    for k in ('proof', 'oven', 'case'):
        need(isinstance(d.get(k), list), 'Dữ liệu lò bánh sai.')
    need(len(d['proof']) <= 2 and len(d['oven']) <= 2 and len(d['case']) <= 40, 'Lò hoặc tủ bánh quá tải.')
    for x in d['proof']:
        need(isinstance(x, dict) and x.get('item') in BAKES and BAKES[x['item']]['proof'] and isinstance(x.get('id'), str), 'Khay ủ sai.')
        for k in ('qty', 'since', 'ready', 'cost'):
            kit.integer(x.get(k), 0, 10**9)
    for x in d['proof']:
        need(type(x.get('dense', False)) is bool, 'Khay ủ sai.')
    for x in d['oven']:
        need(isinstance(x, dict) and x.get('item') in BAKES and isinstance(x.get('id'), str) and _valid_ts(x.get('start')) and x['start'] is not None, 'Tầng lò sai.')
        need(x.get('task') is None or isinstance(x['task'], str), 'Tầng lò sai.')
        need(type(x.get('flat')) is bool and type(x.get('dense', False)) is bool, 'Tầng lò sai.')
        kit.integer(x.get('shift', 0), 0, 10)
        kit.integer(x.get('qty'), 1, 12)
        kit.integer(x.get('cost'), 0, 10000)
    for x in d['case']:
        need(isinstance(x, dict) and x.get('item') in CASE_ITEMS and x.get('q') in LOT_Q and isinstance(x.get('id'), str) and type(x.get('sale')) is bool, 'Khay tủ kính sai.')
        kit.integer(x.get('qty'), 0, CASE_MAX)
        kit.integer(x.get('day'), 1, 10**7)
        kit.integer(x.get('cost'), 0, 10000)
    need(len({x['id'] for x in d['case']}) == len(d['case']), 'Trùng mã khay bánh.')
    for item in CASE_ITEMS:
        need(_case_count(d, item) <= CASE_MAX, 'Tủ bánh vượt sức chứa.')
    for k in ('drinks', 'pastries', 'cakes', 'donated', 'markdown_sold', 'discarded', 'clean_day'):
        kit.integer(d.get(k), 0, 10**9)
    kit.integer(d.get('counter_sold', 0), 0, 10**9)
    _validate_care(c, d)
    FS.validate(c, MODS, EVENT_INDEX)
    p = d.get('plan')
    if p is not None:
        need(set(p['rules']) <= RULE_KEYS, 'Luật trong ngày không hợp lệ.')
        box = p['rules'].get('box')
        if box is not None:
            need(isinstance(box, dict) and box.get('status') in ('open', 'sent', 'failed') and box.get('item') in CASE_ITEMS, 'Đơn hộp bánh không hợp lệ.')
            kit.integer(box.get('goal'), 1, 12)
            for k in ('pay', 'due'):
                kit.integer(box.get(k), 0, 1000)


def _validate_care(c: dict, d: dict) -> None:
    need = kit.need
    st = d['starter']
    need(isinstance(st, dict) and set(st) == {'strength', 'fed', 'feeds'}, 'Hũ men sai.')
    kit.integer(st['strength'], STARTER_MIN, STARTER_MAX)
    kit.integer(st['fed'], 0, c['day'])
    kit.integer(st['feeds'], 0, 10**6)
    cold = d['cold']
    need(isinstance(cold, list) and len(cold) <= COLD_MAX, 'Tủ mát ủ bột sai.')
    for x in cold:
        need(isinstance(x, dict) and set(x) == {'id', 'item', 'qty', 'day', 'cost', 'dense', 'flat'}, 'Khay ủ lạnh sai.')
        need(isinstance(x['id'], str) and x['item'] in BAKES and BAKES[x['item']]['proof'], 'Khay ủ lạnh sai.')
        need(type(x['dense']) is bool and type(x['flat']) is bool, 'Khay ủ lạnh sai.')
        kit.integer(x['day'], max(1, c['day'] - COLD_NIGHTS), c['day'])
        kit.integer(x['qty'], 1, 12)
        kit.integer(x['cost'], 0, 10000)
    ids = [x['id'] for x in d['proof']] + [x['id'] for x in cold]
    need(len(set(ids)) == len(ids), 'Trùng mã khay bột.')
    book = d['book']
    need(isinstance(book, dict) and len(book) <= len(PEOPLE), 'Sổ khách quen sai.')
    for npc, rec in book.items():
        i = _npc_index(npc) if isinstance(npc, str) else None
        need(i is not None and isinstance(rec, dict) and set(rec) == {'visits', 'notes'}, 'Sổ khách quen sai.')
        visits = kit.integer(rec['visits'], 0, 999)
        need(rec['notes'] == _learned(i, visits), 'Ghi chú khách quen không khớp số lần ghé.')
    night = d['night']
    if night is not None:
        need(isinstance(night, dict) and set(night) == {'day', 'lines'} and isinstance(night['lines'], list) and len(night['lines']) <= 8, 'Nhật ký qua đêm sai.')
        kit.integer(night['day'], 1, c['day'] + 1)
        for line in night['lines']:
            need(isinstance(line, str) and len(line) <= 300, 'Nhật ký qua đêm sai.')


def _close_care(s: dict, c: dict) -> dict:
    """Overnight: warm dough spoils, old chilled dough spoils, Bé Men gets hungrier."""
    d = kit.data(c)
    lines = []
    lost = 0
    for tray in d['proof']:
        kit.waste(c, tray['item'], tray['qty'], tray['cost'], 'Bột ủ ấm để qua đêm bị chua')
        lost += 1
    if lost:
        lines.append(f'Bỏ {lost} khay bột còn trong tủ ủ ấm — để qua đêm là quá nở, chua. Lần sau nướng kịp hoặc cất vào tủ mát.')
    d['proof'] = []
    keep = []
    for tray in d['cold']:
        if c['day'] + 1 - tray['day'] > COLD_NIGHTS:
            kit.waste(c, tray['item'], tray['qty'], tray['cost'], f'Bột ủ lạnh quá {COLD_NIGHTS} đêm')
            lines.append(f'Khay {BAKES[tray["item"]]["name"].lower()} ủ lạnh đã {COLD_NIGHTS} đêm chưa nướng — bột chua gắt, phải bỏ.')
            lost += 1
        else:
            keep.append(tray)
    d['cold'] = keep
    ready = [BAKES[x['item']]['name'].lower() for x in keep]
    if ready:
        lines.append('Sáng mai ra lò ngay: ' + ', '.join(ready) + ' ủ lạnh qua đêm.')
    st = d['starter']
    fed = st['fed'] == c['day']
    before = st['strength']
    st['strength'] = max(STARTER_MIN, before - (NIGHT_FED if fed else NIGHT_UNFED))
    band = _band(st['strength'])
    if fed:
        lines.append(f'Bé Men được ăn hôm nay, sáng mai còn {st["strength"]}% ({band[2]} {band[3]}).')
    else:
        lines.append(f'Bé Men bị bỏ đói: {before}% → {st["strength"]}% ({band[2]} {band[3]}: {band[5]}). Mai nhớ cho ăn trước khi nhào bột.')
    waiting = sum(l['qty'] for l in d['case'] if l['qty'] and not l['sale'] and c['day'] + 1 - l['day'] > BAKES[l['item']]['fresh'])
    if waiting:
        lines.append(f'Sáng mai: {waiting} bánh hôm qua chờ xử lý (rổ −50%, tặng hoặc bỏ).')
    tm = _tomorrow(c)
    tip = f'Mai {tm["label"].lower()}: khách mua lẻ đông — ủ lạnh sẵn bột tối nay.' if tm['busy'] else ''
    d['night'] = dict(day=c['day'] + 1, lines=lines[:8])
    return dict(care=dict(starter=_starter_view(dict(day=c['day'] + 1), st), lines=lines[:8], dough_lost=lost, tip=tip))


def on_close(s: dict, c: dict) -> dict:
    """Markdown basket sells, overnight rules apply, the oven is switched off;
    then the day is graded (food_service)."""
    _migrate(c)
    pl = _plan(c)
    box = pl['rules'].get('box')
    if isinstance(box, dict) and box['status'] == 'open':
        box['status'] = 'failed'
        _event_outcome(pl, 'box_order', False, 'Hết ca mà chưa gửi hộp bánh cho văn phòng.')
    res = _close_case(s, c)
    care = _close_care(s, c)
    out = FS.close(s, c, ID, pl, MODS)
    out['lines'] = res.pop('lines') + out['lines']
    out.update(res)
    out.update(care)
    return out


def _close_case(s: dict, c: dict) -> dict:
    d = kit.data(c)
    sold = income = discarded = 0
    keep = []
    for lot in d['case']:
        b = BAKES[lot['item']]
        if lot['sale'] and lot['qty']:
            n = min(lot['qty'], (lot['qty'] + 1) // 2 + c['day'] % 2)
            unit = max(1, kit.price(c, lot['item'], SPEC['prices'][lot['item']]) // 2)
            if n:
                kit.money(s, c, n * unit, f'Rổ bánh hôm qua −50%: {n} {b["name"].lower()}', None, 'revenue')
                sold += n
                income += n * unit
                lot['qty'] -= n
        # Tomorrow the lot is one day older: drop what may no longer be sold.
        if lot['qty'] and c['day'] + 1 - lot['day'] > b['max_age']:
            kit.waste(c, lot['item'], min(60, lot['qty']), lot['qty'] * lot['cost'], 'Hết hạn bán theo quy định tủ kính')
            discarded += lot['qty']
            lot['qty'] = 0
        if lot['qty']:
            keep.append(lot)
    d['case'] = keep
    for rack in d['oven']:
        kit.waste(c, rack['item'], min(60, rack['qty']), rack['cost'], 'Lò tắt khi khép ca')
        discarded += rack['qty']
        t = _task_for_rack(c, rack['task'])
        if t:
            t['cake']['baking'] = False
    d['oven'] = []
    d['markdown_sold'] += sold
    d['discarded'] += discarded
    lines = []
    if sold:
        lines.append(f'Rổ giảm giá bán được {sold} bánh · +{income} xu.')
    if discarded:
        lines.append(f'Bỏ {discarded} bánh hết hạn bán hoặc còn trong lò.')
    if lines:
        kit.log(s, c, 'bakery', ' '.join(lines))
    return dict(markdown_sold=sold, markdown_income=income, discarded=discarded, lines=lines)


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    try:
        return _assist(s, c, e, t)
    except kit.eng().GameError:
        return None


def _assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = kit.data(c)
    role = e['role']
    if role == 'baker':
        if d['starter']['fed'] != c['day'] and kit.stock(c, 'flour') >= 1:
            _feed(s, c, d)
            return f'Đã cho Bé Men ăn bột mì và nước ấm, hũ men sủi bọt lên {d["starter"]["strength"]}%.'
        for item in ('croissant', 'banhmi'):
            b = BAKES[item]
            proofing = sum(x['qty'] for x in d['proof'] + d['cold'] if x['item'] == item)
            if _case_count(d, item) + proofing < 4 and len(d['proof']) < 2 and _recipe_ok(c, b['recipe']):
                _shape(s, c, d, dict(item=item))
                return f'Đã nhào và tạo hình một khay {b["name"].lower()}, đang ủ trong tủ. Bạn canh lò khi bột nở.'
        return 'Đã cân sẵn bột, bơ và trứng cho mẻ sau, lau bàn nhồi.'
    if not t or t['career'] != ID or not t['known']:
        return None
    n = _spec(t)
    if role == 'barista' and n['kind'] == 'drink' and _hidden(t):
        return None
    if role == 'barista' and n['kind'] == 'drink' and _tray(t) and t['cups'][t['cur']] is not None:
        return None
    if role == 'barista' and n['kind'] == 'drink' and t['drink']['container'] is None:
        kind = 'paper' if n['takeaway'] else 'glass' if n['iced'] else 'mug'
        if kind == 'paper' and not kit.stock(c, 'cup'):
            return None
        if kind == 'paper':
            t['drink']['cost'] += kit.take(c, 'cup', 1)
        t['drink']['container'] = kind
        t['drink']['size'] = n['size']
        kit.start_work(t)
        return f'Đã chuẩn bị {CONTAINERS[kind]["name"].lower()} đúng cỡ cho order đang làm.'
    if role == 'cashier':
        bag = t['bag']
        if n['kind'] == 'pastry' and n['takeaway'] and not bag['bagged'] and kit.stock(c, 'bag') \
                and bag['items'] and len(bag['items']) == sum(n['items'].values()):
            if not bag['has_bag']:
                bag['cost'] += kit.take(c, 'bag', 1)
                bag['has_bag'] = True
            bag['bagged'] = True
            return 'Đã cho bánh vào túi giấy và dán tem ngày ra lò.'
        return 'Đã lau bàn, thay giấy ăn, nhắc khách gọi món tại quầy.'
    return None


def hint(c: dict, t: dict) -> str:
    n = t.get('needs') if t.get('known') else None
    if n and n['kind'] == 'drink' and _hidden(t):
        return 'Nghe khách tả rồi chọn món hợp ý: nóng hay đá, có sữa không, đậm hay ngọt, có kiêng gì không.'
    if n and n['kind'] == 'drink' and n.get('party'):
        return 'Làm từng ly theo phiếu → “Xong ly” để đặt lên khay → đủ ly thì giao cả khay một lượt.'
    if n and n['kind'] == 'cake':
        return 'Nướng cốt bánh (vàng đều) → chờ nguội một nhịp → phủ đúng kem và màu → viết chữ đúng từng dấu → đóng hộp → giao.'
    if n and n['kind'] == 'pastry':
        return 'Gắp đúng bánh trong tủ kính (bánh hôm nay, trừ khi khách xin bánh hôm qua) → tránh món khách dị ứng → cho vào túi → giao.'
    return 'Lấy đúng ly → xay mịn, 18 g → chiết 25–30 giây → sữa 55–68 °C (hoặc rót lạnh + đá) → vẽ hình nếu khách dặn → đậy nắp mang về → giao.'


def content() -> dict:
    return dict(extract=EXTRACT, shot_label=SHOT_LABEL, grind=GRIND, grind_label=GRIND_LABEL, dose=dict(target=DOSE_TARGET, min=DOSE_MIN, max=DOSE_MAX),
                steam=STEAM, milk_tex_label=MILK_TEX_LABEL, beans=BEANS, milks=list(MILKS.values()), drinks=list(DRINKS.values()),
                containers=list(CONTAINERS.values()), arts=ARTS, bakes=list(BAKES.values()), case_items=list(CASE_ITEMS), lot_q_label=LOT_Q_LABEL,
                creams=list(CREAMS.values()), colors=list(COLORS.values()), allergen_label=ALLERGEN_LABEL,
                proof_turns=PROOF_TURNS, overproof=OVERPROOF, case_max=CASE_MAX, groups=MAX_GROUPS, hot_oven=HOT_OVEN,
                buyer_wants=BUYER_WANTS, mood_tip=MOOD_TIP)


# --- surprises of the day --------------------------------------------------------

def _event_outcome(pl: dict, eid: str, good: bool | None, note: str) -> None:
    for e in pl['events']:
        if e['id'] == eid and e['status'] == 'done':
            e['good'] = good
            e['note'] = note[:300]


def _post(s: dict, c: dict, npc: int, text: str) -> None:
    kit.eng().add_feed(s, c, kit.npc_id(ID, npc), text, 'event', None, 'post')


def _regular_visit(c: dict, npc: int) -> None:
    regs = kit.data(c).setdefault('regulars', {})
    key = kit.npc_id(ID, npc)
    regs[key] = min(99, regs.get(key, 0) + 1)


def _fresh_lots(c: dict, d: dict, item: str) -> list[dict]:
    return sorted((l for l in d['case'] if l['item'] == item and l['qty'] > 0 and not l['sale'] and lot_state(c, item, l['day']) == 'fresh'),
                  key=lambda l: l['day'])


def _after_rules(s: dict, c: dict, pl: dict, t: dict) -> list[str]:
    """Follow-ups of today's surprises that wait for a served order."""
    rules, lines = pl['rules'], []
    if rules.get('influencer') == 'next':
        rules['influencer'] = 'done'
        if t['mistakes'] == 0 and not t['refused']:
            w = FS.spawn_walkin(s, c, ID, 1.0, 'influencer')
            if w:
                pl['walkins'] += 1
            _post(s, c, 2, '📱 Clip pha chế ở Tiệm Sớm Mai đang lên xu hướng: làm chuẩn từng bước, nhìn là thèm!')
            _event_outcome(pl, 'influencer', True, 'Clip ly vừa pha lên xu hướng, khách mới kéo tới tiệm.')
            lines.append('📱 Clip ly vừa pha lên xu hướng!')
        else:
            _event_outcome(pl, 'influencer', False, 'Clip quay đúng lúc ly phải sửa, bình luận chê tiệm lóng ngóng.')
            lines.append('📱 Clip quay đúng lúc ly có lỗi…')
    at = rules.get('overpay')
    if type(at) is int and pl['served'] >= at:
        rules.pop('overpay')
        _regular_visit(c, 6)
        lines.append('💵 Anh Tùng quay lại nhận phong bì tiền thừa, cảm ơn rối rít.')
    box = rules.get('box')
    if isinstance(box, dict) and box['status'] == 'open' and pl['served'] > box['due']:
        box['status'] = 'failed'
        _event_outcome(pl, 'box_order', False, 'Văn phòng chờ lâu quá nên hủy hộp bánh.')
        lines.append('📦 Văn phòng chờ lâu quá nên hủy hộp bánh.')
    return lines


def _box_send(s: dict, c: dict, d: dict, pl: dict) -> dict:
    box = pl['rules'].get('box')
    kit.need(isinstance(box, dict) and box['status'] == 'open', 'Không có hộp bánh nào đang chờ gửi.')
    item = box['item']
    b = BAKES[item]
    lots = _fresh_lots(c, d, item)
    have = sum(l['qty'] for l in lots)
    kit.need(have >= box['goal'], f'Tủ kính mới có {have}/{box["goal"]} {b["name"].lower()} ra lò hôm nay. Nướng thêm mẻ nữa nhé.')
    left = box['goal']
    for l in lots:
        q = min(left, l['qty'])
        l['qty'] -= q
        left -= q
        if not left:
            break
    d['case'] = [l for l in d['case'] if l['qty'] > 0]
    pay = box['goal'] * box['pay']
    kit.money(s, c, pay, f'Hộp {box["goal"]} {b["name"].lower()} cho văn phòng', f'box-{c["day"]}', category='revenue')
    kit.bank(pay)   # the office pays its box by transfer
    box['status'] = 'sent'
    _event_outcome(pl, 'box_order', True, f'Đã gửi {box["goal"]} {b["name"].lower()} cho văn phòng, nhận {pay} xu.')
    kit.metric(c, 'box_orders')
    FS.flash(pl, 'good', f'📦 Đã gửi hộp bánh cho văn phòng · +{pay} xu.')
    return dict(message=f'Đã xếp {box["goal"]} {b["name"].lower()} vào hộp, dán tem ngày ra lò, gửi văn phòng · +{pay} xu.')


def _ev_overpay(s, c, pl, choice):
    if choice == 'keep':
        pl['rules']['overpay'] = pl['served'] + 2
        return 'Bạn cho tiền thừa vào phong bì, ghi “trả anh Tùng”, cất ngăn kéo. Lát nữa anh ấy quay lại sẽ nhận đủ.', True
    if choice == 'chase':
        _drain_patience(c, 10)
        _regular_visit(c, 6)
        return 'Bạn chạy theo tới đầu hẻm trả tiền. Anh Tùng cười: “Tiệm này được!” Khách trong tiệm chờ thêm một chút.', True
    return 'Bạn bỏ tiền thừa vào hũ tip. Chiều anh Tùng quay lại hỏi, cả quầy ngượng chín mặt, phải trả lại và xin lỗi.', False


def _ev_lost_kid(s, c, pl, choice):
    if choice == 'inside':
        _drain_patience(c, 6)
        return 'Bạn mời bé vào ngồi, rót ly nước, gọi công an phường. Mười phút sau mẹ bé chạy tới, rối rít cảm ơn.', True
    if choice == 'post':
        return 'Nhóm khu phố tìm ra mẹ bé rất nhanh, nhưng ảnh bé bị chia sẻ khắp nơi, mẹ bé không vui.', None
    return 'Bé đi lòng vòng rồi khóc to hơn. Một cô bán vé số phải dắt bé đi tìm mẹ giùm.', False


def _ev_inspection(s, c, pl, choice):
    d = kit.data(c)
    if choice == 'show':
        if d['clean_day'] == c['day']:
            pl['rules']['clean_badge'] = True
            kit.metric(c, 'inspections_passed')
            return 'Sổ vệ sinh ghi đủ, vòi đánh sữa sạch bóng. Đoàn dán tem “Quầy sạch” lên tủ kính.', True
        fine = min(30, c['money'])
        if fine:
            kit.money(s, c, -fine, 'Phạt vệ sinh: sổ ca để trống', f'insp-{c["day"]}', category='fine')
        return f'Sổ vệ sinh hôm nay còn trống, vòi hơi còn bám sữa khô. Đoàn phạt {fine} xu và dặn vệ sinh máy đầu mỗi ca.', False
    if choice == 'tidy':
        _drain_patience(c, 12)
        d['clean_day'] = c['day']
        kit.metric(c, 'hygiene_checks')
        return 'Bạn xả nhóm pha, lau vòi hơi, ghi sổ ngay trước mặt đoàn. Không bị phạt, nhưng khách chờ lâu hơn một chút.', None
    fine = min(60, c['money'])
    if fine:
        kit.money(s, c, -fine, 'Phạt: kẹp phong bì cho đoàn kiểm tra', f'insp-{c["day"]}', category='fine')
    return f'Đoàn trả lại phong bì và lập biên bản. Tiệm bị phạt {fine} xu, cả hẻm biết chuyện.', False


def _ev_sour_milk(s, c, pl, choice):
    if choice == 'keep':
        pl['rules']['sour_milk'] = True
        return 'Bạn giữ lô sữa lại dùng tiếp. Ly nào có sữa tươi hôm nay cũng có thể bị chê…', False
    n = kit.stock(c, 'milk')
    if not n:
        return 'Tủ mát đã hết sữa tươi từ trước, không còn gì phải xử lý.', True
    cost = kit.take(c, 'milk', n)
    if choice == 'toss':
        kit.waste(c, 'milk', n, cost, 'Sữa tươi có mùi chua')
        return f'Bạn đổ {n} ca sữa tươi, ghi hao hụt. Ai gọi sữa tươi thì mời đổi sang yến mạch hoặc nhập thêm ở Kho.', True
    refund = n * ITEM_INDEX['milk']['cost']
    kit.money(s, c, refund, 'Nhà cung cấp hoàn tiền lô sữa', f'milk-{c["day"]}', category='refund')
    _drain_patience(c, 8)
    return f'Nhà cung cấp xin lỗi, hoàn {refund} xu và lấy lại {n} ca sữa. Khách chờ thêm chút trong lúc bạn gọi điện.', True


def _ev_influencer(s, c, pl, choice):
    if choice == 'welcome':
        pl['rules']['influencer'] = 'next'
        return 'Bạn mời bạn ấy quay ở quầy. Ly giao tiếp theo sẽ lên hình — làm thật chuẩn nhé!', None
    if choice == 'later':
        return 'Bạn hẹn quay lúc tiệm vắng. Bạn ấy vui vẻ gọi một ly rồi ngồi chờ.', None
    kit.money(s, c, -30, 'Trả tiền quảng cáo không ghi rõ', f'ads-{c["day"]}', category='marketing')
    return 'Clip “review thật” lên sóng, nhưng người xem phát hiện là quảng cáo không ghi rõ. Bình luận chê tiệm thiếu trung thực.', False


def _ev_allergy(s, c, pl, choice):
    if choice == 'cookie':
        return 'Bạn chỉ cookie hạnh nhân… May mà mẹ bé đọc nhãn kịp: có hạt! Mẹ bé cảm ơn nhưng không dám mua gì nữa.', False
    if choice == 'check':
        _drain_patience(c, 5)
        return 'Bạn mở sổ thành phần đọc từng món rồi mới trả lời: croissant và bánh mì que không có hạt. Hơi lâu nhưng chắc chắn.', True
    d = kit.data(c)
    b = BAKES[choice]
    lots = _fresh_lots(c, d, choice)
    if not lots:
        return f'Đúng rồi, {b["name"].lower()} không có hạt — tiếc là tủ vừa hết bánh mới. Mẹ bé hẹn mai quay lại.', True
    lot = lots[0]
    lot['qty'] -= 1
    d['case'] = [l for l in d['case'] if l['qty'] > 0]
    price = kit.price(c, choice, SPEC['prices'][choice])
    kit.money(s, c, price, f'Khách mua lẻ 1 {b["name"].lower()}', None, 'revenue')
    pl['sales'] += 1
    return f'Đúng rồi, {b["name"].lower()} không có hạt. Mẹ bé mua một cái cho bé (+{price} xu), còn hỏi mai tiệm mở mấy giờ.', True


def _ev_grinder(s, c, pl, choice):
    if choice == 'clean':
        _drain_patience(c, 12)
        return 'Bạn tháo cối xay, chải sạch bột cũ, chỉnh lại. Máy êm hẳn, nhưng khách phải chờ thêm một lúc.', True
    if choice == 'tech':
        kit.money(s, c, -20, 'Thợ chỉnh máy xay', f'grind-{c["day"]}', category='repair')
        return 'Thợ tới chỉnh cối xay trong mười phút. Bột ra đều như mới.', True
    pl['rules']['grinder'] = True
    return 'Bạn xay tiếp với máy rè rè. Shot hôm nay sẽ hơi gắt, khách sành là nhận ra.', False


def _ev_oven(s, c, pl, choice):
    if choice == 'repair':
        kit.money(s, c, -25, 'Sửa quạt đối lưu lò nướng', f'oven-{c["day"]}', category='repair')
        return 'Thợ thay quạt đối lưu, lò nóng đều trở lại.', True
    pl['rules']['hot_oven'] = True
    return f'Lò hôm nay nóng hơn thường: mẻ nào cũng chín sớm {HOT_OVEN} giây. Canh thanh thời gian thật kỹ nhé.', None


def _ev_box(s, c, pl, choice):
    if choice == 'decline':
        return 'Chị trưởng phòng bảo “tiếc ghê, lần sau nhé”. Quầy giữ nhịp như cũ.', None
    goal = 6 if choice == 'all' else 3
    unit = kit.price(c, 'croissant', SPEC['prices']['croissant'])
    pl['rules']['box'] = dict(item='croissant', goal=goal, pay=unit, due=pl['served'] + 3, status='open')
    return f'Đã nhận {goal} croissant cho văn phòng. Khi tủ kính đủ bánh mới ra lò, bấm “Gửi hộp bánh” — kịp trước khi phục vụ xong 3 khách nữa.', None


def _ev_rain(s, c, pl, choice):
    if choice == 'invite':
        w = FS.spawn_walkin(s, c, ID, 1.0, 'rain')
        if w:
            pl['walkins'] += 1
            return 'Bạn mời mọi người vào trong, rót trà đá miễn phí. Một người ngồi lại gọi món luôn.', True
        return 'Bạn mời mọi người vào trong, rót trà đá miễn phí. Ai cũng cảm ơn, hẹn hôm khác ghé.', True
    if choice == 'ignore':
        return 'Mọi người đứng nép dưới hiên chờ tạnh mưa rồi đi.', None
    return 'Bạn nhờ mọi người đứng chỗ khác. Có người lầm bầm, ướt sũng bước ra giữa mưa.', False


EVENTS = [
    dict(id='overpay', emoji='💵', title='Khách vội để lại dư tiền', gentle=True, min_day=1,
         text='Anh Tùng đưa tờ 100 xu cho ly 38 xu rồi phóng xe đi mất, chưa kịp nhận tiền thừa.',
         choices=[dict(id='keep', label='Cho tiền thừa vào phong bì ghi tên, cất ngăn kéo chờ anh quay lại', hint='Không ai phải bỏ quầy.'),
                  dict(id='chase', label='Chạy theo trả ngay', hint='Khách trong tiệm phải chờ thêm.'),
                  dict(id='tip', label='Coi như tiền tip cho tiệm', hint='Chắc anh ấy không để ý đâu…')],
         apply=_ev_overpay),
    dict(id='lost_kid', emoji='🧒', title='Bé lạc mẹ đứng khóc trước tiệm', gentle=True, min_day=1,
         text='Một bé chừng năm tuổi đứng khóc trước cửa tiệm, nói mẹ đi chợ mà bé tìm không thấy.',
         choices=[dict(id='inside', label='Mời bé vào ngồi, rót nước, gọi công an phường', hint='Khách đang chờ sẽ đợi thêm chút.'),
                  dict(id='post', label='Chụp ảnh bé đăng nhóm khu phố', hint='Nhanh, nhưng lộ hình của bé.'),
                  dict(id='send', label='Chỉ đường cho bé tự ra chợ tìm mẹ', hint='')],
         apply=_ev_lost_kid),
    dict(id='inspection', emoji='📋', title='Đoàn kiểm tra vệ sinh ghé bất ngờ', min_day=2,
         text='Hai cán bộ phường đeo thẻ bước tới quầy, xin xem sổ vệ sinh ca, vòi đánh sữa và tủ mát.',
         choices=[dict(id='show', label='Mời đoàn vào, trình sổ vệ sinh hôm nay', hint='Đã “Vệ sinh máy pha” đầu ca thì yên tâm.'),
                  dict(id='tidy', label='Xin 5 phút lau máy, ghi sổ rồi mời đoàn vào', hint='Khách đang chờ sẽ sốt ruột.'),
                  dict(id='envelope', label='Kẹp một phong bì vào sổ', hint='Nhanh gọn… nhưng có ổn không?')],
         apply=_ev_inspection),
    dict(id='sour_milk', emoji='🥛', title='Ca sữa tươi vừa mở có mùi chua', min_day=2,
         text='Mở thùng sữa tươi mới giao, bạn ngửi thấy mùi hơi chua. Hạn in trên hộp vẫn còn hai ngày.',
         choices=[dict(id='toss', label='Đổ hết sữa tươi, ghi hao hụt', hint='Đơn sữa tươi thì mời khách đổi yến mạch.'),
                  dict(id='return', label='Gọi nhà cung cấp lấy lại, đòi hoàn tiền', hint='Được hoàn tiền, khách chờ lâu hơn.'),
                  dict(id='keep', label='Đánh nóng kỹ rồi dùng tiếp', hint='Tiết kiệm… nếu khách không nhận ra.')],
         apply=_ev_sour_milk),
    dict(id='influencer', emoji='📱', title='Bạn TikToker xin quay ở quầy', min_day=2,
         text='Một bạn trẻ cầm gậy chống rung hỏi: “Cho em quay cảnh pha chế nha? Kênh em hơn trăm nghìn người theo dõi.”',
         choices=[dict(id='welcome', label='Mời quay, làm ly kế tiếp thật chuẩn', hint='Ly hoàn hảo sẽ kéo khách mới tới.'),
                  dict(id='later', label='Hẹn quay lúc tiệm vắng khách', hint=''),
                  dict(id='paid', label='Trả 30 xu để bạn ấy đăng “review thật” mà không ghi là quảng cáo', hint='Khen chắc, nhưng…', cost=30)],
         apply=_ev_influencer),
    dict(id='allergy_ask', emoji='🥜', title='Mẹ hỏi bánh nào không có hạt', min_day=2,
         text='Một người mẹ dắt bé tới tủ kính: “Bé nhà chị dị ứng hạt. Bánh nào ăn được vậy em?”',
         choices=[dict(id='croissant', label='Croissant bơ', hint=''),
                  dict(id='banhmi', label='Bánh mì que', hint=''),
                  dict(id='cookie', label='Cookie hạnh nhân', hint=''),
                  dict(id='check', label='Xin một phút đọc sổ thành phần rồi trả lời', hint='Chắc chắn, nhưng khách khác chờ thêm.')],
         apply=_ev_allergy),
    dict(id='grinder', emoji='⚙️', title='Máy xay kêu rè rè, bột ra không đều', min_day=3,
         text='Cối xay kêu rè rè, bột lúc mịn lúc thô. Shot vừa chiết chảy lúc nhanh lúc chậm.',
         choices=[dict(id='clean', label='Tháo cối xay vệ sinh ngay', hint='Khách đang chờ phải đợi thêm.'),
                  dict(id='tech', label='Gọi thợ tới chỉnh (20 xu)', hint='', cost=20),
                  dict(id='ignore', label='Kệ, xay tiếp cho kịp khách', hint='Shot hôm nay sẽ hơi gắt.')],
         apply=_ev_grinder),
    dict(id='oven_hot', emoji='🌡️', title='Lò nướng nóng không đều', min_day=3,
         text='Nhiệt kế lò nhảy lên cao hơn mức cài. Hậu nói quạt đối lưu kêu lạ từ sáng.',
         choices=[dict(id='repair', label='Gọi thợ thay quạt (25 xu)', hint='Lò chạy như thường.', cost=25),
                  dict(id='adapt', label='Nướng tiếp, canh thanh thời gian kỹ hơn', hint=f'Mọi mẻ chín sớm {HOT_OVEN} giây.')],
         apply=_ev_oven),
    dict(id='box_order', emoji='📦', title='Văn phòng đầu hẻm đặt hộp croissant', min_day=3, not_mods=('quiet',),
         text='Chị trưởng phòng gọi: “Cho chị hộp croissant mới ra lò cho buổi họp, trong lúc tiệm phục vụ thêm 3 khách nữa nhé. Giá như bán lẻ.”',
         choices=[dict(id='all', label='Nhận 6 croissant', hint='Cần 6 croissant nướng hôm nay trong tủ kính.'),
                  dict(id='half', label='Nhận 3 croissant', hint='Ít tiền hơn, nhẹ việc hơn.'),
                  dict(id='decline', label='Từ chối khéo vì quầy đang kín việc', hint='')],
         apply=_ev_box),
    dict(id='rain_shelter', emoji='☔', title='Mưa lớn, người đi đường đứng trú trước hiên', min_day=2, mods=('rain',),
         text='Mưa ào xuống. Năm sáu người đi đường đứng nép dưới hiên tiệm, có người ướt sũng.',
         choices=[dict(id='invite', label='Mời vào trong, rót trà đá miễn phí', hint='Có thể thêm khách gọi món.'),
                  dict(id='ignore', label='Kệ mọi người đứng chờ tạnh', hint=''),
                  dict(id='shoo', label='Nhờ mọi người đứng chỗ khác cho thoáng cửa', hint='')],
         apply=_ev_rain),
]
EVENT_INDEX = {e['id']: e for e in EVENTS}
RULE_KEYS = {'clean_badge', 'sour_milk', 'grinder', 'hot_oven', 'box', 'influencer', 'overpay'}


SITUATIONS = [
    dict(id='CB-S01', title='Khách chê cà phê đắng, đòi hoàn tiền', npc=6, tone='tense', min_day=1,
         opening='Anh Tùng đặt ly americano xuống quầy: “Đắng như thuốc bắc! Hoàn tiền cho anh, ly này anh không uống.” Hàng người phía sau bắt đầu nhìn.',
         swap='Bạn là khách vội, lần đầu gọi americano vì thấy tên “sang”, tưởng nó ngọt như cà phê sữa đá.',
         facts=[dict(id='log', title='Nhật ký máy pha', source='Máy espresso', text='Shot chiết 27 giây, liều 18 g, hạt Robusta Lá Chè — nằm giữa vùng cân bằng.'),
                dict(id='order', title='Phiếu order', source='Máy tính tiền', text='Anh Tùng tự chọn “Americano Robusta, không đường”. Ly mới vơi một ngụm.'),
                dict(id='habit', title='Thói quen của khách', source='Nhi (thu ngân)', text='Nhi nhớ anh Tùng hay uống cà phê sữa đá thật ngọt ở quán cóc đầu hẻm.')],
         options=[dict(id='swap', label='Mời anh đổi sang bạc xỉu hoặc latte đá, tiệm chịu phần chênh, không bàn lỗi ai', requires=['order', 'habit'], cost=12, quality='good', stars=5,
                       review='Tưởng americano là cà phê sữa kiểu Mỹ 😅 Tiệm đổi cho ly bạc xỉu vui vẻ, ngon hết sảy.',
                       outcome='Anh Tùng nhấp bạc xỉu, gật gù. Hôm sau anh quay lại gọi đúng món đó, còn rủ thêm hai đồng nghiệp.',
                       perspectives=[dict(who='Anh Tùng', emoji='🛵', text='Anh không rành tên món thôi. Được đổi mà không bị nhìn như “quê” là anh quý.'),
                                     dict(who='Vy (pha chế)', emoji='🧑‍🍳', text='Shot của em chuẩn 27 giây, nhưng khách không hợp vị thì đổi là đúng. Em ghi vào sổ: gợi ý món cho khách mới.'),
                                     dict(who='Khách xếp hàng', emoji='👀', text='Xử lý gọn trong một phút, mình yên tâm gọi món lạ.')]),
                  dict(id='explain', label='Giải thích nhẹ nhàng americano vốn đắng; thêm sữa, đường miễn phí cho vừa miệng', requires=['log'], cost=3, quality='good', stars=4,
                       review='Được giải thích americano là gì, thêm chút sữa đường thì uống được. Học thêm một món.',
                       outcome='Anh Tùng thêm sữa đường, uống hết, lần sau hỏi kỹ trước khi gọi.',
                       perspectives=[dict(who='Anh Tùng', emoji='🤔', text='Hóa ra nó đắng là đúng. Thêm sữa vào thì ổn.'),
                                     dict(who='Nhi (thu ngân)', emoji='🧾', text='Em sẽ ghi chú mô tả vị ngay trên menu cho khách mới.')]),
                  dict(id='refund', label='Hoàn tiền ngay, không hỏi thêm', cost=30, quality='ok', stars=3,
                       review='Được hoàn tiền, nhưng mình vẫn đi ra với cái bụng trống.',
                       outcome='Anh Tùng cầm tiền đi, không uống gì. Chuyện êm, nhưng tiệm mất khách lẫn ly cà phê.',
                       perspectives=[dict(who='Anh Tùng', emoji='😐', text='Tiền thì lấy lại rồi, nhưng vẫn chưa biết uống gì ở đây.'),
                                     dict(who='Vy (pha chế)', emoji='😕', text='Ly đó em làm đúng mà đổ bỏ, hơi tiếc.')]),
                  dict(id='argue', label='Chìa nhật ký máy ra: “Shot chuẩn 27 giây, anh uống không quen thì chịu”', requires=['log'], quality='bad', stars=1,
                       review='Chê đắng thì bị đọc số giây vào mặt. Cà phê chuẩn mà thái độ thì đắng hơn.',
                       outcome='Anh Tùng bỏ ly lại quầy, tối đó có một bài đánh giá 1 sao kèm ảnh ly americano.',
                       perspectives=[dict(who='Anh Tùng', emoji='😠', text='Tôi đâu cần biết 27 giây, tôi cần một ly uống được.'),
                                     dict(who='Khách xếp hàng', emoji='😬', text='Đúng kỹ thuật mà cãi tay đôi với khách thì ai dám gọi món lạ nữa.')])],
         lesson='Đúng kỹ thuật chưa chắc đúng khẩu vị: giữ quy trình chuẩn, nhưng giúp khách tìm được ly hợp với mình.'),
    dict(id='CB-S02', title='Một ly americano, sáu tiếng laptop, giờ cao điểm', npc=4, tone='gentle', min_day=2,
         opening='Trưa thứ Sáu, tiệm kín chỗ. Anh Khoa ngồi bàn bốn ghế từ 7 giờ sáng với một ly americano đã tan hết đá, laptop cắm sạc. Một nhóm bốn người đứng chờ ngoài cửa.',
         swap='Bạn là freelancer, nhà cúp mạng từ sáng, chiều có buổi họp online quan trọng với khách hàng.',
         facts=[dict(id='rule', title='Bảng nội quy', source='Cửa tiệm', text='Tiệm chưa từng ghi giới hạn thời gian ngồi; bảng wifi còn ghi “Ngồi thoải mái nhé!”.'),
                dict(id='seats', title='Sơ đồ chỗ ngồi', source='Quầy', text='Quầy bar cạnh cửa sổ còn hai ghế cao trống, có ổ cắm riêng.'),
                dict(id='khoa', title='Anh Khoa kể', source='Anh Khoa', text='Anh nói nhỏ: “Nhà em cúp mạng, chiều em họp với khách. Em ngại gọi thêm vì đang tiết kiệm.”')],
         options=[dict(id='move', label='Hỏi riêng anh Khoa có thể chuyển sang ghế quầy bar có ổ cắm, nhường bàn bốn cho nhóm khách', requires=['seats'], quality='good', stars=5,
                       review='Chủ tiệm hỏi riêng, còn chỉ chỗ có ổ cắm. Đổi chỗ xong mình làm việc còn tập trung hơn.',
                       outcome='Anh Khoa dời sang quầy bar, nhóm bốn người có bàn sau ba phút. Chiều đó anh gọi thêm một ly và một croissant.',
                       perspectives=[dict(who='Anh Khoa', emoji='💻', text='Được hỏi riêng, lại có ổ cắm, mình đổi liền. Không thấy bị đuổi chút nào.'),
                                     dict(who='Nhóm khách', emoji='👥', text='Chờ có chút xíu là có bàn, tiệm xoay xở khéo.'),
                                     dict(who='Nhi (thu ngân)', emoji='🧾', text='Giờ cao điểm mà bàn bốn chỉ có một người thì doanh thu ca trưa hụt hẳn.')]),
                  dict(id='policy', label='Soạn nội quy mới: giờ cao điểm mỗi khách ngồi tối đa 2 tiếng/1 món, dán từ tuần sau cho tất cả', requires=['rule'], quality='ok',
                       outcome='Hôm nay nhóm bốn người bỏ đi, nhưng từ tuần sau ai cũng biết luật trước khi gọi món.',
                       perspectives=[dict(who='Anh Khoa', emoji='🙂', text='Luật rõ ràng thì mình tự canh giờ, không ai khó xử.'),
                                     dict(who='Nhóm khách', emoji='🚶', text='Hôm nay thì tụi mình đi quán khác rồi.')]),
                  dict(id='combo', label='Gợi ý anh Khoa gói “combo làm việc” (đồ uống + bánh, giảm 10%) nếu muốn ngồi tiếp', requires=['khoa'], quality='ok', reward=8,
                       outcome='Anh Khoa mua combo, vẫn ngồi bàn bốn. Tiệm có thêm doanh thu nhưng nhóm khách vẫn phải đi.',
                       perspectives=[dict(who='Anh Khoa', emoji='😅', text='Hợp lý, nhưng nghe hơi giống bị nhắc khéo phải trả tiền ghế.'),
                                     dict(who='Nhóm khách', emoji='🚶', text='Không có chỗ thì đành đi.')]),
                  dict(id='kick', label='Tới rút sạc laptop: “Ngồi vậy tiệm lỗ, anh về đi”', quality='bad', stars=1,
                       review='Bị rút sạc giữa lúc đang làm, không một lời báo trước. Nội quy không có mà đuổi khách như đuổi tà.',
                       outcome='Anh Khoa mất dữ liệu đang soạn, bỏ về. Nhóm khách ngồi vào nhưng cả bàn bên cạnh chứng kiến và thì thầm.',
                       perspectives=[dict(who='Anh Khoa', emoji='😞', text='Nếu có luật thì mình đã theo. Đằng này bị rút điện ngay trước mặt mọi người.'),
                                     dict(who='Khách bàn bên', emoji='😬', text='Mình cũng hay ngồi lâu… chắc lần sau đi chỗ khác.')])],
         lesson='Nội quy phải báo trước và áp dụng như nhau; giữa ca đông, một lời đề nghị riêng tư thường hiệu quả hơn lệnh đuổi.'),
    dict(id='CB-S03', title='Bánh hôm qua: tặng hay bỏ?', npc=2, tone='gentle', min_day=2,
         opening='Sáng sớm, Mơ ghé: “Bếp Cơm 0 Đồng Ngõ Mây xin bánh hôm qua cho bữa sáng của các cô chú bán vé số, tiệm có không ạ?” Trong tủ còn croissant, bánh mì hôm qua và vài lát bông lan trứng muối.',
         facts=[dict(id='label', title='Sổ ra lò', source='Hậu (thợ bánh)', text='Croissant và bánh mì ra lò sáng hôm qua, để hộp kín nhiệt độ phòng. Bông lan trứng muối có sốt bơ trứng, đã để ngoài tủ mát qua đêm.'),
                dict(id='rule', title='Quy định an toàn thực phẩm của tiệm', source='Sổ quy trình', text='Bánh khô ≤ 1 ngày: được giảm giá hoặc tặng, ghi rõ ngày ra lò. Bánh có kem/sốt để ngoài tủ mát qua đêm: bỏ — không bán, không tặng.'),
                dict(id='kitchen', title='Bếp cơm nhận thế nào', source='Mơ', text='Bếp phát bánh ngay trong buổi sáng, có sổ ghi nguồn thực phẩm được tặng và ngày nhận.')],
         options=[dict(id='donate_safe', label='Tặng croissant và bánh mì hôm qua kèm nhãn ngày ra lò; bỏ bông lan trứng muối và ghi hao hụt', requires=['label', 'rule'], quality='good',
                       outcome='Hai mươi cô chú có bánh ăn sáng. Mơ chụp nhãn ngày ra lò dán vào sổ của bếp.',
                       perspectives=[dict(who='Mơ', emoji='🙋‍♀️', text='Có nhãn ngày rõ ràng, bếp tụi em yên tâm phát cho mọi người.'),
                                     dict(who='Cô bán vé số', emoji='🎟️', text='Croissant còn thơm bơ, sáng nay khỏi nhịn đói.'),
                                     dict(who='Hậu (thợ bánh)', emoji='👨‍🍳', text='Bỏ bông lan cũng tiếc, nhưng sốt trứng qua đêm thì không đùa được.')]),
                  dict(id='donate_all', label='Tặng hết cho đỡ phí, kể cả bông lan trứng muối', quality='bad',
                       outcome='Tình nguyện viên ngửi thấy sốt đã chua nên phải bỏ giữa chừng. Bếp bối rối, Mơ lo lắng hỏi lại tiệm từng món.',
                       perspectives=[dict(who='Mơ', emoji='😟', text='Tụi em tin tiệm nên không kiểm từng món. Suýt nữa thì…'),
                                     dict(who='Tình nguyện viên', emoji='🧤', text='Đồ cho người khó khăn càng phải an toàn hơn chứ.')]),
                  dict(id='discard_all', label='Bỏ hết cho chắc, không muốn rắc rối', quality='ok',
                       outcome='An toàn tuyệt đối, nhưng mười mấy chiếc bánh còn tốt vào thùng rác. Mơ về tay không.',
                       perspectives=[dict(who='Mơ', emoji='😔', text='Em hiểu tiệm cẩn thận, chỉ tiếc bánh còn ăn được.'),
                                     dict(who='Nhi (thu ngân)', emoji='🗑️', text='Sổ hao hụt hôm nay dài quá trời.')]),
                  dict(id='sell_fresh', label='Bày lại lên kệ như bánh mới, bán giá thường', quality='bad', cost=0,
                       outcome='Bà Sáu mua phải ổ bánh mì hôm qua, về nhai không nổi, hôm sau ghé quầy hỏi thẳng.',
                       perspectives=[dict(who='Bà Sáu', emoji='👵', text='Bánh cũ thì nói bánh cũ, bà mua rẻ cũng được. Lừa bà làm chi.'),
                                     dict(who='Mơ', emoji='🙁', text='Tiệm không cho mà đem bán như bánh mới… em buồn ghê.')])],
         lesson='Chia sẻ thực phẩm là việc tốt khi còn an toàn: ghi ngày ra lò, loại món có kem/sốt để qua đêm.'),
    dict(id='CB-S04', title='Bơ tăng giá 40%', npc=0, tone='gentle', min_day=3,
         opening='Nhà phân phối Hạt Nắng báo: từ tuần này bơ lạt tăng 40%. Mỗi chiếc croissant tốn thêm khoảng 3 xu nguyên liệu. Chú Lâm mua croissant mỗi sáng đang đứng đọc bảng giá.',
         facts=[dict(id='invoice', title='Hóa đơn mới', source='Hạt Nắng', text='Bơ lạt: 4 → 5,6 xu/khối. Mỗi khay croissant dùng 2 khối.'),
                dict(id='margin', title='Sổ lãi lỗ', source='Sổ tiệm', text='Croissant bán 22 xu; nguyên liệu mới ~9 xu, cộng điện lò, công nhào và khấu hao ~8 xu.'),
                dict(id='alt', title='Hàng thay thế', source='Chợ đầu mối Mây', text='Có bơ thực vật rẻ hơn một nửa; vị, độ xốp và thành phần khác bơ sữa.')],
         options=[dict(id='transparent', label='Tăng croissant thêm 3 xu, dán thông báo lý do ở quầy, giữ nguyên bơ thật', requires=['invoice', 'margin'], quality='good', stars=4,
                       review='Tăng 3 xu mà có ghi rõ lý do, bánh vẫn thơm bơ như cũ. Chú ủng hộ.',
                       outcome='Vài khách hỏi, đọc thông báo rồi gật đầu. Doanh số croissant gần như giữ nguyên.',
                       perspectives=[dict(who='Chú Lâm', emoji='🧓', text='Giá gì cũng lên, miễn bánh vẫn vậy và người ta nói thật.'),
                                     dict(who='Hạt Nắng', emoji='🚚', text='Tiệm vẫn đặt đều, bên em sẽ báo trước nếu giá giảm lại.')]),
                  dict(id='label_swap', label='Chuyển sang bơ thực vật, đổi tên trên bảng thành “croissant bơ thực vật”, giữ giá', requires=['alt'], quality='ok', stars=3,
                       review='Giá không đổi nhưng bánh không còn thơm như trước. Ít ra tiệm ghi rõ.',
                       outcome='Khách trung thành thấy khác vị; một số chuyển sang bánh mì. Tiệm giữ được giá, mất chút hương vị.',
                       perspectives=[dict(who='Chú Lâm', emoji='😕', text='Ghi rõ là tốt, nhưng chú mua croissant vì mùi bơ mà.'),
                                     dict(who='Hậu (thợ bánh)', emoji='👨‍🍳', text='Bơ thực vật cán lớp dễ hơn nhưng bánh không tan trong miệng.')]),
                  dict(id='secret', label='Lén đổi sang bơ thực vật, bảng vẫn ghi “croissant bơ sữa”', quality='bad', stars=1,
                       review='Bảng ghi bơ sữa mà ăn là biết bơ thực vật. Mất niềm tin.',
                       outcome='Một khách làm bánh tại gia nhận ra ngay và đăng bài so sánh. Nhãn thành phần sai còn là chuyện nghiêm trọng với người kiêng sữa hay ăn chay.',
                       perspectives=[dict(who='Chú Lâm', emoji='😤', text='Tăng giá chú chịu được, bị lừa thì không.'),
                                     dict(who='Khách ăn chay', emoji='🥗', text='Ghi sai thành phần thì người ăn kiêng biết tin vào đâu?')]),
                  dict(id='shrink', label='Giữ giá, lặng lẽ làm croissant nhỏ lại 20%', quality='bad', stars=2,
                       review='Hình như croissant teo đi thì phải? Giá vẫn vậy mà bánh nhỏ hẳn.',
                       outcome='Khách quen nhận ra ngay khi cầm bánh. Không ai nói ra, nhưng số người mua mỗi sáng giảm dần.',
                       perspectives=[dict(who='Chú Lâm', emoji='🤨', text='Chú mua ở đây ba năm, cầm lên là biết nhẹ tay.'),
                                     dict(who='Nhi (thu ngân)', emoji='😶', text='Khách hỏi mà em không biết trả lời sao.')])],
         lesson='Khi chi phí tăng, khách chấp nhận giá mới dễ hơn là chấp nhận bị giấu.'),
    dict(id='CB-S05', title='Tên trên bánh sinh nhật bị viết sai', npc=3, tone='tense', min_day=2,
         opening='Cô Diệp mở hộp bánh ngay tại quầy: “Trời ơi, cháu cô tên NGỌC, sao lại viết NGOC? Tiệc bắt đầu lúc 6 giờ rồi!” Đồng hồ chỉ 5 giờ 10.',
         swap='Bạn là người bà đặt bánh cho cháu gái, đã dặn kỹ qua điện thoại, còn nhắn tin xác nhận.',
         facts=[dict(id='slip', title='Phiếu đặt bánh', source='Sổ đặt hàng', text='Phiếu viết tay khi nghe điện thoại ghi “Bao Ngoc” không dấu — hôm đó máy tính bảng hết pin nên ghi vội.'),
                dict(id='msg', title='Tin nhắn xác nhận', source='Điện thoại tiệm', text='Ngay sau cuộc gọi, cô Diệp nhắn đúng tên “Bảo Ngọc” có dấu. Chưa ai đối chiếu lại tin nhắn.'),
                dict(id='time', title='Thời gian sửa', source='Hậu (thợ bánh)', text='Cạo lớp chữ, láng lại kem và viết mới mất khoảng 10 phút.')],
         options=[dict(id='fix_now', label='Nhận lỗi của tiệm, sửa chữ ngay trong 10 phút, tặng thêm hộp nến số và đổi quy trình: đọc lại tên có dấu với khách', requires=['msg', 'time'], cost=6, quality='good', stars=5,
                       review='Tiệm nhận lỗi liền, 10 phút sửa xong, còn tặng nến số. Bé Ngọc thổi nến vui lắm!',
                       outcome='Cô Diệp ngồi uống trà chờ. Bánh đúng tên kịp giờ tiệc, từ hôm sau phiếu đặt bánh có ô “đọc lại tên cho khách”.',
                       perspectives=[dict(who='Cô Diệp', emoji='👵', text='Ai cũng có lúc sai, quan trọng là sửa kịp và không đổ lỗi.'),
                                     dict(who='Hậu (thợ bánh)', emoji='👨‍🍳', text='Có tin nhắn mà không đối chiếu là lỗi quy trình, không phải lỗi của khách.'),
                                     dict(who='Bé Bảo Ngọc', emoji='🎂', text='Tên con có dấu nặng xinh xinh trên bánh!')]),
                  dict(id='blame_slip', label='Đưa phiếu ra: “Cô đọc qua điện thoại không dấu mà”', requires=['slip'], quality='bad', stars=1,
                       review='Tôi đã nhắn tin đúng tên mà tiệm còn đổ cho tôi đọc sai. Không bao giờ đặt nữa.',
                       outcome='Cô Diệp đưa tin nhắn ra. Tiệm vẫn phải sửa, nhưng mất luôn khách đặt bánh cho cả họ.',
                       perspectives=[dict(who='Cô Diệp', emoji='😠', text='Tôi có tin nhắn đây này. Sai thì nhận, cãi làm gì.'),
                                     dict(who='Nhi (thu ngân)', emoji='😣', text='Giá như mình mở tin nhắn ra trước khi nói.')]),
                  dict(id='discount', label='Giảm 30% nhưng không sửa vì sợ không kịp giờ', cost=48, quality='ok', stars=2,
                       review='Được giảm tiền nhưng cả bữa tiệc ai cũng thấy tên cháu tôi bị viết sai.',
                       outcome='Cô Diệp cầm bánh về trong im lặng. Ảnh chụp tiệc sinh nhật có dòng chữ thiếu dấu.',
                       perspectives=[dict(who='Cô Diệp', emoji='😞', text='Tiền giảm đâu thay được tấm ảnh sinh nhật của cháu.'),
                                     dict(who='Hậu (thợ bánh)', emoji='⏱️', text='10 phút là sửa kịp mà…')])],
         lesson='Chữ trên bánh là phần quý nhất với người nhận: xác nhận tên có dấu bằng văn bản trước khi viết.'),
    dict(id='CB-S06', title='Cúp điện khi lò đang nướng dở', npc=1, tone='tense', min_day=3,
         opening='3 giờ chiều, cả dãy phố cúp điện. Khay croissant trong lò mới nướng được một nửa, tủ mát đang giữ kem tươi, và 5 giờ chị Thảo hẹn lấy bánh kem.',
         facts=[dict(id='oven', title='Sổ tay lò nướng', source='Nhà sản xuất lò', text='Không mở cửa lò khi mất điện: nhiệt giữ được khoảng 10 phút. Bánh nướng dở để nguội hàng giờ rồi nướng lại thường xẹp, không đạt.'),
                dict(id='fridge', title='Nhiệt kế tủ mát', source='Tủ mát', text='Đóng kín cửa, tủ giữ dưới 8 °C khoảng 2 tiếng. Kem tươi phải giữ dưới 8 °C.'),
                dict(id='power', title='Thông báo cúp điện', source='Điện lực khu phố', text='Dự kiến có điện lại lúc 5 giờ 30.'),
                dict(id='orders', title='Sổ đơn', source='Sổ đặt hàng', text='Cốt bánh của chị Thảo đã nướng xong từ trưa, chỉ còn phủ kem và viết chữ.')],
         options=[dict(id='plan', label='Giữ kín cửa lò và tủ mát, gọi báo chị Thảo lùi giờ hoặc phủ kem bằng tay ở góc mát; ghi hao hụt khay croissant', requires=['oven', 'fridge', 'orders'], cost=10, quality='good', stars=4,
                       review='Tiệm gọi báo sớm, mình đổi giờ lấy bánh, không bất ngờ gì hết. Chuyên nghiệp.',
                       outcome='Kem tươi an toàn, bánh của chị Thảo xong lúc 5 giờ 40. Khay croissant nướng dở được ghi hao hụt thay vì bán liều.',
                       perspectives=[dict(who='Chị Thảo', emoji='📱', text='Được báo từ 3 giờ nên chị sắp xếp kịp, không phải đứng chờ.'),
                                     dict(who='Hậu (thợ bánh)', emoji='👨‍🍳', text='Tiếc khay croissant, nhưng bánh nửa sống thì không ai dám bán.')]),
                  dict(id='peek', label='Mở lò và tủ mát ra kiểm liên tục cho yên tâm', quality='bad', cost=20,
                       outcome='Mỗi lần mở cửa là mất nhiệt; kem tươi lên quá 8 °C phải bỏ, croissant xẹp hẳn.',
                       perspectives=[dict(who='Hậu (thợ bánh)', emoji='😩', text='Càng mở càng hỏng. Lò với tủ cần được để yên.'),
                                     dict(who='Chị Thảo', emoji='⌛', text='5 giờ tới nơi mới biết bánh chưa xong.')]),
                  dict(id='sell_half', label='Để nguội khay croissant nướng dở rồi bán giảm giá', quality='bad', stars=1,
                       review='Croissant giảm giá mà ruột còn sống nhão. Tiết kiệm kiểu gì vậy?',
                       outcome='Khách mua về phát hiện ruột bột còn sống, quay lại đòi tiền và đăng ảnh lên nhóm khu phố.',
                       perspectives=[dict(who='Chị Thảo', emoji='🤢', text='Ruột bánh còn bột sống, may chị chưa đưa cho con ăn.'),
                                     dict(who='Mơ', emoji='📣', text='Nhóm khu phố đang bàn tán ghê lắm…')]),
                  dict(id='silent', label='Không báo ai, hy vọng có điện kịp', requires=['power'], quality='ok', stars=2,
                       review='Tới đúng hẹn mới biết bánh chưa xong. Báo trước một câu thôi mà.',
                       outcome='Điện có lại 5 giờ 30 như thông báo; chị Thảo phải đứng chờ gần một tiếng.',
                       perspectives=[dict(who='Chị Thảo', emoji='😤', text='Chị không giận cúp điện, chị giận vì không được báo.'),
                                     dict(who='Nhi (thu ngân)', emoji='😬', text='Em cũng không biết nói sao khi chị ấy tới.')])],
         lesson='Sự cố thì ưu tiên an toàn thực phẩm, giữ nhiệt và lạnh đúng cách, và báo khách thật sớm.'),
    dict(id='CB-S07', title='Thực tập sinh làm đổ cà phê lên khách quen', npc=1, tone='tense', min_day=2,
         opening='Tí — thực tập sinh tuần đầu — bưng khay latte nóng thì vấp dây sạc, đổ nửa ly lên tay áo và túi xách của chị Thảo. Cả tiệm im bặt.',
         swap='Bạn là thực tập sinh 18 tuổi, tuần đầu đi làm, vừa làm đổ ly nóng lên người khách quen.',
         facts=[dict(id='burn', title='Chị Thảo', source='Khách', text='Cổ tay chị hơi đỏ, chị nói rát rát.'),
                dict(id='bag', title='Túi xách', source='Khách', text='Túi vải bị loang cà phê; laptop bên trong vẫn khô.'),
                dict(id='cable', title='Camera', source='Camera quầy', text='Dây sạc của khách bàn bên vắt ngang lối đi từ trưa, chưa ai dẹp.')],
         options=[dict(id='care', label='Lo cho chị Thảo trước: xả vết rát dưới nước mát, khăn sạch, làm ly mới, nhận tiền giặt túi; sau đó gom dây sạc và kèm riêng Tí', requires=['burn', 'bag'], cost=20, quality='good', stars=5,
                       review='Bị đổ cà phê mà ra về vẫn thấy được chăm sóc. Tiệm chu đáo từ vết rát tới cái túi.',
                       outcome='Tay chị Thảo dịu lại sau vài phút nước mát. Lối đi được dẹp dây; Tí được kèm cách bưng khay và nhìn lối đi.',
                       perspectives=[dict(who='Chị Thảo', emoji='🙂', text='Chị thấy người ta lo cho mình trước khi lo giữ thể diện, vậy là đủ.'),
                                     dict(who='Tí (thực tập sinh)', emoji='🙇', text='Em tưởng bị đuổi, nhưng chủ tiệm chỉ cho em cách bưng khay và dặn luôn nhìn lối đi.'),
                                     dict(who='Khách bàn bên', emoji='🔌', text='Hóa ra dây sạc của mình… lần sau mình ngồi chỗ có ổ cắm sát tường.')]),
                  dict(id='scold', label='Mắng Tí ngay trước mặt khách cho khách hả giận', quality='bad', stars=2,
                       review='Tay tôi đang rát mà chủ tiệm lo mắng nhân viên. Cả tiệm ngại thay.',
                       outcome='Tí khóc ở kho, chiều đó xin nghỉ. Chị Thảo vẫn chưa được ai đưa nước mát.',
                       perspectives=[dict(who='Chị Thảo', emoji='😣', text='Tôi đâu cần xem mắng người, tôi cần nước mát cho tay.'),
                                     dict(who='Tí (thực tập sinh)', emoji='😢', text='Em biết em sai, nhưng bị mắng trước cả tiệm thì em không dám quay lại.')]),
                  dict(id='voucher', label='Xin lỗi và tặng voucher ly sau, không làm gì thêm', cost=5, quality='ok', stars=3,
                       review='Có xin lỗi, có voucher, nhưng cái túi và cổ tay thì tự lo.',
                       outcome='Chị Thảo nhận voucher, về tự xử lý vết rát. Dây sạc vẫn vắt ngang lối đi.',
                       perspectives=[dict(who='Chị Thảo', emoji='😐', text='Lời xin lỗi thì có, sự chăm sóc thì chưa.'),
                                     dict(who='Tí (thực tập sinh)', emoji='😟', text='Chẳng ai chỉ em cần làm gì khác đi.')]),
                  dict(id='blame_cable', label='Nói với chị Thảo đây là lỗi của khách bàn bên để dây sạc', requires=['cable'], quality='bad', stars=2,
                       review='Ly của tiệm đổ lên người tôi mà tiệm đi đổ lỗi cho khách khác.',
                       outcome='Hai bàn khách lời qua tiếng lại. Không ai được chăm sóc, dây sạc vẫn nằm đó.',
                       perspectives=[dict(who='Khách bàn bên', emoji='😒', text='Tôi để dây đó từ trưa, tiệm đâu có nhắc gì.'),
                                     dict(who='Chị Thảo', emoji='😤', text='Lỗi ai thì tính sau, tay tôi đang rát đây.')])],
         lesson='Khi có sự cố: người bị ảnh hưởng trước, lỗi ai sau; kèm nhân viên mới ở nơi riêng và sửa nguyên nhân gốc.'),
]

SPEC = dict(
    id=ID, prefix='cb_', category='food',
    meta=dict(short='Tiệm bánh & cà phê', place='Tiệm Bánh & Cà Phê Sớm Mai', tagline='Shot chiết đúng giây. Bánh ra lò đúng màu.', icon='cake',
              color='#8a5a3c', light='#fbf1e6', weather='Sáng sớm mát trời', work='Order', station='Quầy & lò',
              greeting='Xay hạt, chiết shot, đánh sữa; canh lò bánh và tủ kính. Ly nào cũng đúng món, bánh nào cũng đúng ngày.',
              caption='Mùi bơ nướng lúc 6 giờ sáng', map_label='09 · TIỆM BÁNH SỚM MAI'),
    people=PEOPLE,
    staff=[('Vy', 'barista', 'Đánh sữa mịn như lụa, vẽ tim chưa bao giờ méo.', 82, 88), ('Hậu', 'baker', 'Dậy từ 4 giờ nhồi bột, thuộc lòng giờ ủ từng mẻ.', 70, 93),
           ('Nhi', 'cashier', 'Nhớ tên và món quen của gần hết khách trong hẻm.', 86, 80), ('Phong', 'barista', 'Tay nhanh giờ cao điểm, đôi khi hơi ẩu.', 90, 72)],
    roles={'barista': 'Pha chế', 'baker': 'Thợ bánh', 'cashier': 'Thu ngân'},
    inventory=dict(items=ITEMS, capacity=40),
    prices={'espresso': 25, 'americano': 30, 'latte': 38, 'cappuccino': 38, 'bacxiu': 32,
            'croissant': 22, 'banhmi': 12, 'cookie': 12, 'bonglan': 20, 'cake': 160},
    tip=3,
    physical=('cb_pull', 'cb_milk', 'cb_pick', 'cb_serve', 'cb_dump', 'cb_bake', 'cb_frost', 'cb_done', 'cb_box_send'),
    wait=True,  # the queue drains in handle (food_service.patience_tick → kit.wait_tick), not the engine's flat -1
    free_actions=(),
    no_tick=('cb_stop', 'cb_milk_stop', 'cb_unload', 'cb_lid', 'cb_ice', 'cb_return', 'cb_tab', 'cb_greet'),
    waste_items=('drink', 'sponge', *CASE_ITEMS),
    activity=('🥐', 'Quầy bánh gọn gàng', [('Sữa tươi', 'Tủ mát'), ('Bột mì', 'Kệ khô'), ('Kem tươi', 'Tủ mát'), ('Hạt cà phê', 'Kệ khô')],
              ['Nhận order', 'Xay mịn và chiết shot', 'Đánh sữa và rót', 'Kiểm ly rồi giao']),
    stories=[('Công thức croissant của bà Sáu', ('Bà Sáu kể hồi trẻ bà làm ở một lò bánh Pháp đầu phố, gấp bột “ba lần ba” bằng tay. Bà muốn xem tiệm gấp bột thế nào.',
                                                  'Bạn mời bà vào bếp lúc 5 giờ sáng. Bà chỉ cách giữ bơ thật lạnh để lớp bột không dính vào nhau.',
                                                  'Mẻ croissant mới xốp hơn hẳn. Tiệm dán tấm ảnh bà Sáu cầm khay bánh lên tường, ghi “Cố vấn bơ lạnh”.')),
             ('Ly yến mạch của chị Thảo', ('Chị Thảo kể nhiều quán không tin chuyện chị không dung nạp lactose, cứ bảo “ít sữa thôi không sao”.',
                                          'Bạn dán nhãn riêng cho ca sữa yến mạch và rửa ca đánh sữa trước mỗi ly không lactose.',
                                          'Chị Thảo rủ cả phòng ban tới, ai kiêng sữa cũng có ly an toàn. Chị gọi tiệm là “chỗ không cần giải thích”.')),
             ('Mơ và Bếp Cơm 0 Đồng', ('Mơ xin bánh hôm qua cho bếp cơm từ thiện, nhưng lo tiệm ngại rắc rối giấy tờ.',
                                      'Bạn cùng Mơ làm mẫu nhãn “ngày ra lò · loại bánh · thành phần dị ứng” cho mỗi hộp bánh tặng.',
                                      'Bếp Cơm 0 Đồng gửi tiệm tấm thiệp vẽ tay: “Cảm ơn những chiếc bánh có ngày sinh rõ ràng”.'))],
    review_asides=['Crema vàng óng, uống xong còn muốn ngửi ly 😌', 'Bánh còn ấm tay, giòn tới vụn cuối cùng.', 'Latte art đẹp tới mức tiếc không nỡ khuấy.', 'Mai lại ghé, giữ cho mình một croissant nha!'],
    situations=SITUATIONS,
    guide='Ly → xay & định lượng → chiết 25–30 giây → sữa/đá/nước → vẽ hình → nắp → giao. Khay nhiều ly: xong từng ly rồi giao cả khay. '
          'Khách tả tâm trạng: chọn đúng món hợp ý. Lò: nhào → ủ → nướng → tủ kính đầy bánh mới cho khách mua lẻ. '
          'Mỗi ngày cho Bé Men ăn; bột chưa kịp nướng thì cất tủ mát cho sáng mai.',
)
