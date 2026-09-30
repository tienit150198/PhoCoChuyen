"""Quán Mì Cay Mây — a noodle-shop kitchen (reference plugin career).

Real work of the job: read the order ticket, choose a dine-in bowl or a takeaway
box, drop noodles into one of two boiling baskets and lift them at the right
moment (real seconds), ladle broth from the pots, add toppings from stock,
pump chili to the ordered level, close the lid for takeaway, serve — or dump a
wrong bowl. Pots run out and must be re-cooked from broth packs; stock is
bought from suppliers, counted on arrival and can expire.

Every day is a little different (see food_service): the luck of the day (rain,
a lunch rush, a cold wind…), one or two surprises that need a decision, guests
with personalities, walk-ins, a streak bonus and an end-of-day grade. Orders
come in four styles:

* classic — a full ticket;
* usual — a regular says “như mọi khi”: look it up in the regulars' notebook
  (once you have served them) or ask again (they wait longer, and remember);
* open — “tô tùy quán”: a few wishes and a budget; you compose the bowl and
  the guest pays for what is in it, up to the budget;
* picture — a visitor points at the menu pictures; the ticket has no words.

Imperfect bowls can still be served, and the guest reacts to what was actually
in the bowl (consequences: grumble, money back, send it back to fix, or leave).
A wrong broth, meat for a vegetarian or a too-spicy bowl for a child is handed
back at once; an allergen or spoiled beef that reaches the guest is a safety
mistake (1 star, no pay, a complaint and an inspection).
"""
from __future__ import annotations
import copy
from . import kit
from . import food_service as FS
from .. import consequences as cq
from .. import archive as ar

ID = 'restaurant'
BOIL = dict(raw=7, perfect=13, soft=19)          # seconds: <7 raw, 7–13 perfect, 13–19 soft, >19 mushy
WEAK_FIRE = 4                                     # low gas: every boil window moves 4 s later
BROTHS = [
    dict(id='kimchi', name='Kim chi', emoji='🥬', color='#e0553d', unlock=1, pack='pack_kimchi'),
    dict(id='tomyum', name='Tomyum', emoji='🍋', color='#f08a2c', unlock=1, pack='pack_tomyum', allergen='seafood'),
    dict(id='blackbean', name='Tương đen', emoji='🫘', color='#4d3a2a', unlock=1, pack='pack_blackbean'),
    dict(id='cheese', name='Sữa phô mai', emoji='🧀', color='#f3cf6b', unlock=3, pack='pack_cheese'),
]
BROTH_INDEX = {x['id']: x for x in BROTHS}
TOPPINGS = ['beef', 'sausage', 'kimchi_side', 'egg', 'mushroom', 'fishball', 'cheese_slice', 'ricecake', 'seafood', 'tofu', 'fried_egg']
MEAT = ('beef', 'sausage', 'fishball', 'seafood')
POT_MAX = 12
POT_BATCH = 6
DIRTY_MAX = 3                                     # no dishwasher today: wash after 3 dine-in bowls
# Care across days (docs/superpowers/specs/2026-09-29-restaurant-care-design.md)
KEEP_NIGHTS = 2          # broth keeps two nights in the fridge; on the third morning it must be poured out
PREP_MAX = 2             # pots that can simmer overnight for tomorrow
PREP_PACKS = 2           # broth packs for one full pot (POT_MAX portions)
BOND_MAX = 5
BOND_TIP_AT = 3          # a regular with this bond adds a small thank-you on a clean visit
BOND_TIP = 2
NOTE_AT = (1, 3)         # a regular's first habit is learned after the 1st served visit, the second after the 3rd
HLOG_DAYS = 7            # the hygiene book looks at the last seven shifts
HYGIENE_A, HYGIENE_B = 85, 60

ITEMS = [
    dict(id='noodle', name='Mì tươi', emoji='🍜', group='base', unit='vắt', cost=3, life=3, start=20),
    dict(id='box', name='Hộp mang về', emoji='🥡', group='pack', unit='hộp', cost=2, start=12),
    dict(id='chili', name='Sốt ớt', emoji='🌶️', group='sauce', unit='lượt bơm', cost=1, life=6, start=30),
    dict(id='pack_kimchi', name='Gói nước dùng kim chi', emoji='🥬', group='broth', unit='gói', cost=9, life=5, start=2),
    dict(id='pack_tomyum', name='Gói nước dùng tomyum', emoji='🍋', group='broth', unit='gói', cost=10, life=5, start=2),
    dict(id='pack_blackbean', name='Gói tương đen', emoji='🫘', group='broth', unit='gói', cost=9, life=5, start=2),
    dict(id='pack_cheese', name='Gói sữa phô mai', emoji='🧀', group='broth', unit='gói', cost=12, life=3, unlock=3),
    dict(id='beef', name='Bò Mỹ', emoji='🥩', group='topping', unit='phần', cost=6, price=15, life=2, start=6),
    dict(id='sausage', name='Xúc xích', emoji='🌭', group='topping', unit='phần', cost=3, price=8, life=4, start=8),
    dict(id='kimchi_side', name='Kim chi', emoji='🥬', group='topping', unit='phần', cost=2, price=6, life=5, start=8),
    dict(id='egg', name='Trứng', emoji='🥚', group='topping', unit='quả', cost=2, price=6, life=5, start=10),
    dict(id='mushroom', name='Nấm', emoji='🍄', group='topping', unit='phần', cost=2, price=7, life=3, start=8),
    dict(id='fishball', name='Cá viên', emoji='🍥', group='topping', unit='phần', cost=3, price=8, life=4, start=8, allergen='seafood'),
    dict(id='cheese_slice', name='Phô mai lát', emoji='🧀', group='topping', unit='lát', cost=3, price=8, life=5, start=6),
    dict(id='ricecake', name='Bánh gạo', emoji='🍡', group='topping', unit='phần', cost=3, price=9, life=4, unlock=2),
    dict(id='seafood', name='Hải sản', emoji='🦐', group='topping', unit='phần', cost=8, price=18, life=2, unlock=4, allergen='seafood'),
    dict(id='tofu', name='Đậu hũ chiên', emoji='🧈', group='topping', unit='phần', cost=2, price=7, life=3, unlock=2),
    dict(id='fried_egg', name='Trứng ốp', emoji='🍳', group='topping', unit='quả', cost=3, price=8, life=4, unlock=3),
]
ITEM_INDEX = {x['id']: x for x in ITEMS}

PEOPLE = [
    ('Anh Sơn', 'Khách quen', 'Ăn cay giỏi, hay gọi thêm xúc xích.', 'bossy'),
    ('Chị Hằng', 'Nhân viên văn phòng', 'Hay gọi mang về, cần nhanh.', 'picky'),
    ('Bé Na', 'Học sinh', 'Thích phô mai, sợ cay.', 'genz'),
    ('Cô Tư', 'Hàng xóm', 'Hay kể chuyện, ăn ít cay.', 'warm'),
    ('Minh Béo', 'Sinh viên', 'Ăn khỏe, hay xin thêm mì.', 'genz'),
    ('Bà Hoa', 'Khách lớn tuổi', 'Nói thẳng, rất để ý vệ sinh.', 'sour'),
    ('Anh Quân', 'Tài xế công nghệ', 'Ăn vội giữa hai cuốc xe.', 'quiet'),
    ('Chú Bảy', 'Thợ sửa xe đầu hẻm', 'Ăn chay ngày rằm, thích đậu hũ chiên.', 'warm'),
    ('Mira', 'Du khách', 'Chưa đọc được thực đơn, gọi món bằng hình.', 'genz'),
]
NPC_GUEST = {0: 'generous', 1: 'rush', 2: 'kid', 3: 'chatty', 4: 'plain', 5: 'picky', 6: 'rush', 7: 'elder', 8: 'tourist'}
OPENINGS = {
    'plain': ('Cho mình gọi món nha!', 'Cho mình một phần mang về nhé!'),
    'rush': ('Làm nhanh giúp mình nhé, mình đang vội!', 'Một phần mang về, gấp giúp mình nha!'),
    'kid': ('Cho con gọi món với ạ!', 'Cho con một hộp mang về ạ!'),
    'chatty': ('Hôm nay quán đông ha! Cho cô gọi món nè.', 'Gói giúp cô một phần mang về, cô kể chuyện này nghe…'),
    'picky': ('Làm cẩn thận giúp tôi nhé.', 'Mang về, đậy kỹ giúp tôi.'),
    'elder': ('Cho chú một tô, từ từ cũng được.', 'Gói giúp chú một phần mang về nhé.'),
    'generous': ('Đói quá! Làm ngon là có thưởng nha!', 'Mang về một phần, ngon là anh ghé hoài!'),
    'tourist': ('Xin chào! Cái này… 👉', 'Xin chào! Mang đi… 👉 🥡'),
}

# (npc, title, broth, toppings, spice, takeaway, extra_noodle, allergy, note, min_day)
ORDERS = [
    (0, 'Mì tương đen cay thêm xúc xích', 'blackbean', {'sausage': 2, 'egg': 1}, 4, False, False, None, 'Cấp 4 nhé, đừng hơn.', 1),
    (1, 'Một hộp kim chi mang về', 'kimchi', {'beef': 1, 'kimchi_side': 1}, 2, True, False, None, 'Mang về văn phòng, đậy kỹ giúp chị.', 1),
    (2, 'Mì phô mai không cay', 'kimchi', {'cheese_slice': 2, 'sausage': 1}, 0, False, False, None, 'Em không ăn cay được đâu ạ.', 1),
    (3, 'Tô tomyum ít cay', 'tomyum', {'mushroom': 1, 'egg': 1}, 1, False, False, None, 'Cô ăn cay kém lắm.', 1),
    (4, 'Mì kim chi thêm mì', 'kimchi', {'beef': 1, 'egg': 1, 'sausage': 1}, 3, False, True, None, 'Cho em thêm một vắt mì nha.', 1),
    (5, 'Tô tương đen, không hải sản', 'blackbean', {'mushroom': 1, 'egg': 1}, 2, False, False, 'seafood', 'Bà dị ứng hải sản, cẩn thận giùm bà.', 1),
    (6, 'Hộp tomyum ăn vội', 'tomyum', {'fishball': 2}, 3, True, False, None, 'Anh có 10 phút thôi.', 1),
    (7, 'Tô tương đen ít cay cho chú', 'blackbean', {'egg': 1, 'mushroom': 1}, 1, False, False, None, 'Chú ăn nhẹ thôi, nhiều nấm.', 1),
    (0, 'Kim chi cấp 6 thử thách', 'kimchi', {'beef': 2, 'kimchi_side': 1}, 6, False, False, None, 'Cấp 6, dám không?', 2),
    (1, 'Hai vắt kim chi mang về', 'kimchi', {'beef': 1, 'egg': 1}, 2, True, True, None, 'Chị ăn trưa với đồng nghiệp, cho thêm vắt nha.', 2),
    (4, 'Tomyum cá viên cấp 4', 'tomyum', {'fishball': 2, 'mushroom': 1}, 4, False, False, None, 'Nhiều cá viên nha.', 2),
    (3, 'Mì tương đen mang về cho cháu', 'blackbean', {'sausage': 1, 'cheese_slice': 1}, 0, True, False, None, 'Cháu nhỏ ăn, đừng cho cay.', 2),
    (2, 'Bánh gạo phô mai', 'kimchi', {'ricecake': 1, 'cheese_slice': 1}, 1, False, False, None, 'Nhiều bánh gạo nha.', 3),
    (0, 'Bò Mỹ gấp đôi, cấp 5', 'kimchi', {'beef': 2, 'egg': 1}, 5, False, False, None, 'Hôm nay anh muốn nhiều thịt.', 3),
    (7, 'Tô đậu hũ nấm cho chú', 'blackbean', {'tofu': 1, 'mushroom': 1}, 0, False, False, None, 'Chú thích đậu hũ chiên giòn.', 3),
    (6, 'Hộp tương đen gấp', 'blackbean', {'beef': 1}, 4, True, True, None, 'Giao lẹ giúp anh.', 3),
    (5, 'Tô kim chi ít cay, không hải sản', 'kimchi', {'egg': 1, 'mushroom': 1}, 1, False, False, 'seafood', 'Nhớ là bà dị ứng đồ biển.', 4),
    (4, 'Kim chi trứng ốp thêm mì', 'kimchi', {'fried_egg': 2, 'kimchi_side': 1}, 2, False, True, None, 'Trứng ốp lòng đào nha!', 5),
    (1, 'Sữa phô mai bò Mỹ', 'cheese', {'beef': 1, 'mushroom': 1}, 2, False, False, None, 'Món mới hả, cho chị thử.', 5),
    (2, 'Hộp phô mai bánh gạo', 'cheese', {'ricecake': 1, 'cheese_slice': 1}, 0, True, False, None, 'Mang lên lớp học thêm ăn ạ.', 6),
    (4, 'Hải sản cấp 5 thêm mì', 'tomyum', {'seafood': 1, 'fishball': 1}, 5, False, True, None, 'Đói lắm rồi!', 7),
    (6, 'Hộp hải sản cay mang về', 'tomyum', {'seafood': 1, 'fishball': 1}, 4, True, False, None, 'Khách trên app đang chờ.', 8),
]

# Regulars' usual bowl: (broth, toppings, spice, takeaway, extra_noodle, allergy)
USUALS = {
    0: ('blackbean', {'sausage': 2, 'egg': 1}, 4, False, False, None),
    3: ('blackbean', {'mushroom': 1, 'egg': 1}, 1, False, False, None),
    6: ('tomyum', {'fishball': 2}, 3, True, False, None),
    4: ('kimchi', {'beef': 1, 'egg': 1, 'sausage': 1}, 3, False, True, None),
}
USUAL_NAME = {0: 'anh Sơn', 3: 'cô Tư', 6: 'anh Quân', 4: 'Minh'}
# Little habits of the regulars ("Sổ khách quen"): learned one by one, honoured with rs_touch.
TOUCHES = {
    'tea': ('🧊', 'Rót ly nước mát'),
    'side': ('🌶️', 'Chén ớt tươi để riêng'),
    'bag': ('🛍️', 'Gói đũa muỗng riêng'),
    'cut': ('✂️', 'Cắt sợi mì ngắn'),
    'soup': ('🥣', 'Thêm chén nước dùng'),
    'chat': ('💬', 'Hỏi thăm vài câu'),
    'scald': ('♨️', 'Tráng đũa nước sôi'),
    'wipe': ('🧻', 'Đưa khăn ướt'),
}
HABITS = {
    0: (('tea', 'Chạy bộ xong mới ghé, khát lắm: rót sẵn ly trà đá.'), ('side', 'Thích chén ớt tươi để riêng, tự nêm thêm.')),
    1: (('bag', 'Ăn ở văn phòng: gói riêng đũa muỗng, khăn giấy.'), ('side', 'Để ớt tươi riêng, chị tự cho vào sau.')),
    2: (('cut', 'Cắt sợi mì ngắn cho bé dễ gắp.'), ('tea', 'Rót sẵn ly nước mát, bé hay khát.')),
    3: (('soup', 'Thích húp thêm một chén nước dùng nóng.'), ('chat', 'Hỏi thăm con trai cô đang làm xa.')),
    4: (('tea', 'Ăn cay xong là xin ngay ly trà đá.'), ('soup', 'Hay xin thêm nước dùng để chan mì.')),
    5: (('scald', 'Bà muốn đũa muỗng được tráng nước sôi trước mặt.'), ('wipe', 'Đưa bà chiếc khăn ướt sạch.')),
    6: (('bag', 'Treo túi lên xe: gói riêng đũa muỗng.'), ('wipe', 'Tay dính dầu xe: đưa khăn ướt.')),
    7: (('wipe', 'Vừa sửa xe xong: đưa khăn ướt lau tay.'), ('chat', 'Hỏi thăm tiệm sửa xe đầu hẻm.')),
}
GUEST_IDS = {f'{ID}_npc_{i + 1:02d}': i for i in HABITS}
REGULAR_STORY = {
    0: ('Anh Sơn: “Người mới hả? Nhớ mặt anh nha, tuần nào anh cũng ghé.”',
        'Anh Sơn kể đang tập chạy bộ: “Ăn cay cho ra mồ hôi!”',
        'Anh Sơn khoe vừa chạy xong 10 cây số đầu tiên, còn đỏ mặt.',
        'Anh Sơn rủ cả nhóm chạy bộ ghé quán sáng Chủ nhật.'),
    3: ('Cô Tư dặn người mới vào làm nhớ ăn đủ bữa.',
        'Cô Tư kể con trai sắp về thăm nhà sau hai năm làm xa.',
        'Cô Tư mang cho quán một hũ dưa cải tự muối.',
        'Cô Tư dắt con trai ra quán: “Đây là đứa nấu mì khéo nhất xóm!”'),
    6: ('Anh Quân dựng xe ngay cửa: “Nhanh giùm anh, khách đang chờ.”',
        'Anh Quân kể app vừa tăng chuyến, chạy không kịp thở.',
        'Anh Quân lên hạng tài xế năm sao, khoe ảnh chụp màn hình.',
        'Anh Quân giới thiệu quán cho cả nhóm tài xế đầu hẻm.'),
    4: ('Minh mới dọn tới khu trọ gần quán, hỏi quán mở tới mấy giờ.',
        'Minh đang ôn thi cuối kỳ: “Ăn no mới học vô.”',
        'Minh thi xong môn khó nhất, đòi thêm vắt mì ăn mừng.',
        'Minh được học bổng, dẫn bạn cùng phòng tới giới thiệu quán.'),
}

# “Tô tùy quán”: (npc, title, opening, wishes, note, min_day)
OPEN = [
    (4, 'Tô nào no nhất 70 xu?', 'Em có 70 xu, làm giúp em tô nào no nhất nha!',
     dict(broths=None, spice=[2, 5], must=[], avoid=[], veg=False, min_tops=3, budget=70, takeaway=False, allergy=None), 'Miễn no là được, cay vừa vừa.', 3),
    (7, 'Tô chay ngày rằm', 'Rằm rồi, chú ăn chay. Quán nấu giúp chú một tô nha.',
     dict(broths=['kimchi', 'blackbean', 'cheese'], spice=[0, 2], must=['mushroom'], avoid=[], veg=True, min_tops=2, budget=50, takeaway=False, allergy=None),
     'Không thịt, không cá, không đồ biển. Có nấm là chú vui.', 3),
    (2, 'Tô không cay có phô mai', 'Con muốn một tô có phô mai, mà không cay chút nào ạ.',
     dict(broths=None, spice=[0, 0], must=['cheese_slice'], avoid=[], veg=False, min_tops=2, budget=50, takeaway=False, allergy=None), 'Không cay xíu nào nha.', 3),
    (5, 'Tô gì cũng được, miễn không đồ biển', 'Quán nấu gì cũng được, nhưng bà dị ứng đồ biển.',
     dict(broths=['kimchi', 'blackbean', 'cheese'], spice=[0, 2], must=[], avoid=[], veg=False, min_tops=2, budget=55, takeaway=False, allergy='seafood'),
     'Ít cay thôi, và nhớ kỹ chuyện dị ứng.', 3),
    (0, 'Tô cay nhất quán', 'Tô nào cay nhất quán? Làm anh một tô, có bò nha!',
     dict(broths=['kimchi', 'tomyum'], spice=[6, 8], must=['beef'], avoid=[], veg=False, min_tops=2, budget=70, takeaway=False, allergy=None),
     'Không đủ cay là anh không trả tiền đâu nha!', 4),
    (1, 'Hộp nhẹ bụng mang về', 'Chị đang ăn kiêng, làm giúp chị một hộp nhẹ bụng mang về nhé.',
     dict(broths=['tomyum', 'kimchi'], spice=[1, 3], must=[], avoid=['sausage', 'cheese_slice'], veg=False, min_tops=2, budget=55, takeaway=True, allergy=None),
     'Đừng bỏ xúc xích với phô mai nha.', 4),
    (8, 'Món đặc trưng của quán', 'Xin chào! Món… đặc biệt nhất? 👉 ✨',
     dict(broths=None, spice=[2, 4], must=['kimchi_side'], avoid=[], veg=False, min_tops=3, budget=65, takeaway=False, allergy=None), 'Muốn thử vị Hàn, có kim chi.', 5),
    (6, 'Có bò là được', 'Hộp nào có bò là anh chịu, lẹ giúp anh!',
     dict(broths=None, spice=[2, 4], must=['beef'], avoid=[], veg=False, min_tops=2, budget=60, takeaway=True, allergy=None), 'Có bò, cay vừa, mang về.', 4),
]

# Tables that order several bowls at once: (npc, title, opening, note, min_day, max size)
GROUPS = [
    (4, 'Nhóm bạn trọ của Minh', 'Cho em {n} tô một lượt nha! Em đọc từng tô nè…', 'Tụi em ngồi bàn trong, mang ra một lượt là được.', 2, 3),
    (2, 'Bé Na rủ bạn cùng lớp', 'Cho con với bạn con {n} tô ạ!', 'Tô 1 của con không cay nha, tô của bạn con cay được.', 2, 3),
    (3, 'Cô Tư dẫn con trai ra quán', 'Hai mẹ con ăn {n} tô nha, mỗi đứa một kiểu.', 'Con trai cô ăn cay giỏi lắm.', 3, 2),
    (0, 'Nhóm chạy bộ của anh Sơn', 'Cả nhóm chạy bộ tới rồi! Cho anh {n} tô nha.', 'Chạy xong đói lắm, ra một lượt giúp anh.', 4, 3),
]
GEN = 2          # task generator version (older saved tasks are regenerated once)

MODS = [
    dict(id='normal', emoji='🍜', label='Ngày thường', hint='Nhịp quán vừa phải, hợp để làm quen tay.', weight=3),
    dict(id='students', emoji='🎒', label='Học sinh tan học', hint='Nhiều khách nhí: ít cay, thích phô mai, hay đi theo nhóm.', min_day=2, weight=2, walkin=0.25),
    dict(id='rain', emoji='🌧️', label='Trời mưa', hint='Khách gọi mang về nhiều. Hộp đậy kín được thưởng thêm.', min_day=2, weight=2, walkin=0.1),
    dict(id='quiet', emoji='🍃', label='Phố vắng', hint='Ít khách, ai cũng thong thả. Tranh thủ nấu nồi, dọn bếp.', min_day=2, weight=1, patience=-1),
    dict(id='cold', emoji='🥶', label='Gió lạnh về', hint='Khách ăn cay hơn một cấp và xin nhiều nước: mỗi tô tốn 2 phần nồi.', min_day=3, weight=2),
    dict(id='lunch_rush', emoji='⏰', label='Giờ trưa cao điểm', hint='Khách vào liên tục, nhiều người đang vội.', min_day=3, weight=2, walkin=0.45, patience=1),
    dict(id='beef_day', emoji='🥩', label='Bò Mỹ về hàng', hint='Nhà cung cấp tặng 4 phần bò. Ai cũng muốn thêm bò.', min_day=4, weight=1),
    dict(id='festival', emoji='🏮', label='Phố có hội', hint='Giá bán +10%. Khách đi nhóm, hay gọi thêm mì.', min_day=5, weight=1, walkin=0.3, patience=1),
]
MOD_INDEX = {m['id']: m for m in MODS}


def _level_hint(day: int) -> int:
    return 1 + (day - 1) // 2


def _unlocked(item: str, day: int) -> bool:
    return ITEM_INDEX[item].get('unlock', 1) <= _level_hint(day)


def _style(day: int, slot: int, r, mod: str = 'normal') -> str:
    """Kinds of order through the day: a shuffled deck per day, so every day
    from day 2 mixes regulars, tables of friends and (later) open and picture orders."""
    if day <= 1 or slot == 0:
        return 'classic'
    deck = ['classic', 'usual', 'group']
    if day >= 3:
        deck += ['open']
    if day >= 4:
        deck += ['picture', 'classic']
    if day >= 6:
        deck += ['open', 'classic']
    if mod in ('festival', 'students'):
        deck += ['group']
    elif mod in ('quiet', 'rain'):
        deck = ['classic' if s == 'group' else s for s in deck]
    kit.rng(ID, 'styles', day).shuffle(deck)
    return deck[(slot - 1) % len(deck)]


def _group(day: int, r, mod: str) -> tuple:
    """A table of friends: 2–3 dine-in bowls, each with its own recipe."""
    pool = [g for g in GROUPS if g[4] <= day]
    npc, title, opening, note, _, most = pool[r.randrange(len(pool))]
    size = min(most, 2 if day < 4 else 3)
    kind = NPC_GUEST[npc]
    dishes = [o for o in ORDERS if o[9] <= day and not o[5] and not o[7]]
    party = []
    for i, o in enumerate(r.sample(dishes, size)):
        tops = {k: v for k, v in o[3].items() if _unlocked(k, day)} or {'egg': 1}
        broth = o[2] if BROTH_INDEX[o[2]]['unlock'] <= _level_hint(day) else 'kimchi'
        spice = o[4]
        if kind == 'kid' and i == 0:
            spice = min(spice, 1)
        elif mod == 'cold' and spice:
            spice = min(7, spice + 1)
        party.append(dict(broth=broth, toppings=tops, spice=spice, extra_noodle=o[6]))
    return npc, title, opening.format(n=size), note, kind, party


def _classic(day: int, slot: int, mod: str) -> tuple:
    pool = [o for o in ORDERS if o[9] <= day]

    def weight(o) -> int:
        w = 2
        if mod == 'rain' and o[5]:
            w += 4
        if mod == 'students' and o[4] <= 1:
            w += 3
        if mod == 'beef_day' and 'beef' in o[3]:
            w += 4
        if mod == 'festival' and o[6]:
            w += 3
        return w
    deck = [o for o in pool for _ in range(weight(o))]
    kit.rng(ID, 'deck', day).shuffle(deck)
    seen, uniq = set(), []
    for o in deck:
        if o[1] not in seen:
            seen.add(o[1])
            uniq.append(o)
    return uniq[slot % len(uniq)]


def make_task(day: int, slot: int, serial: int) -> dict:
    r = kit.rng(ID, day, slot)
    mod = FS.pick_mod(ID, day, MODS)['id']
    style = _style(day, slot, r, mod)
    wishes = None
    party = []
    if style == 'group':
        npc, title, opening, note, kind, party = _group(day, r, mod)
        first = party[0]
        broth, toppings, spice, extra = first['broth'], dict(first['toppings']), first['spice'], first['extra_noodle']
        takeaway, allergy = False, None
    elif style == 'usual':
        npc = list(USUALS)[(day + slot) % len(USUALS)]
        broth, toppings, spice, takeaway, extra, allergy = USUALS[npc]
        toppings = dict(toppings)
        title, opening, note = f'Như mọi khi của {USUAL_NAME[npc]}', 'Như mọi khi nhé!', 'Khách quen gọi món quen.'
        kind = 'regular'
    elif style == 'open':
        pool = [o for o in OPEN if o[5] <= day]
        npc, title, opening, wishes, note, _ = pool[r.randrange(len(pool))]
        wishes = copy.deepcopy(wishes)
        if mod == 'festival':
            wishes['budget'] = round(wishes['budget'] * 1.1)
        wishes['must'] = [k for k in wishes['must'] if _unlocked(k, day)]
        if wishes['broths']:
            wishes['broths'] = [b for b in wishes['broths'] if BROTH_INDEX[b]['unlock'] <= _level_hint(day)]
        broth, toppings, spice, takeaway, extra, allergy = None, {}, None, wishes['takeaway'], False, wishes['allergy']
        kind = NPC_GUEST[npc]
    else:
        npc, title, broth, toppings, spice, takeaway, extra, allergy, note, _ = _classic(day, slot, mod)
        toppings = {k: v for k, v in toppings.items() if _unlocked(k, day)} or {'egg': 1}
        if BROTH_INDEX[broth]['unlock'] > _level_hint(day):
            broth = 'kimchi'
        kind = NPC_GUEST[npc]
        if style == 'picture':
            npc, kind, title = 8, 'tourist', 'Khách chỉ vào hình trên thực đơn'
        elif mod == 'lunch_rush' and kind not in ('kid', 'elder') and r.random() < 0.5:
            kind = 'rush'
        opening = OPENINGS[kind][1 if takeaway else 0]
        if mod == 'cold' and spice and kind != 'kid':
            spice = min(7, spice + 1)
    needs = dict(style=style, broth=broth, toppings=toppings, spice=spice, takeaway=takeaway, extra_noodle=extra,
                 allergy=allergy, note=note, open=wishes, party=party)
    # Takeaway orders that arrive through the delivery app carry an order code.
    app = None
    if takeaway and style in ('classic', 'open') and npc != 8:
        app = '#' + str(kit.rng(ID, 'app', day, slot).randrange(1000, 10000))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, needs=needs, guest=FS.guest(kind), app=app, gen=GEN,
                         bowl=_empty_bowl(), cur=0, plates=[None] * max(1, len(party)), quoted_price=None, subs={}, served=None,
                         refused=0, recalled=False, reasked=False, vip=None, story=None, over_budget=False,
                         regular=None, touches=[], broth_age=0)


FIXED = ('needs', 'guest', 'app')
TASK_EXTRA = dict(recalled=False, reasked=False, vip=None, story=None, over_budget=False, regular=None, touches=[], broth_age=0)


def _specs(n: dict) -> list[dict]:
    """One recipe per bowl: a table's party list, or the order itself."""
    return n.get('party') or [dict(broth=n['broth'], toppings=n['toppings'], spice=n['spice'], extra_noodle=n['extra_noodle'])]


def _spec(t: dict, i: int | None = None) -> dict:
    """The order as seen from one bowl (the active one by default)."""
    n = t['needs']
    party = n.get('party') or []
    if not party:
        return n
    i = t.get('cur', 0) if i is None else i
    return {**n, **party[i]}


def _bowls_total(t: dict) -> int:
    return len(_specs(t['needs']))


def _empty_bowl() -> dict:
    return dict(container=None, broth=None, noodles=[], boiling=None, toppings={}, chili=0, lid=False, cost=0)


def initial() -> dict:
    return dict(pots={'kimchi': 6, 'tomyum': 6, 'blackbean': 6, 'cheese': 0}, bowls_served=0, dumped=0, clean_checked_day=0,
                notebook=[], regulars={}, grades=[], ev_hist=[], pot_lots={'kimchi': [[6, 0]], 'tomyum': [[6, 0]], 'blackbean': [[6, 0]], 'cheese': []},
                pot_warm={b: True for b in BROTH_INDEX}, prep=[], guests={}, hlog=[])


# ------------------------------------------------------------------ old saves
def _upgrade_task(t: dict, c: dict | None) -> None:
    """A task saved by an older order generator: regenerate its fixed facts once."""
    slot = int(t['id'].rsplit('-', 1)[1])
    fresh = make_task(t['day'], slot, t['created_turn'])
    for k in ('npc', 'title', 'opening', 'kind', 'needs', 'guest', 'app', 'gen'):
        t[k] = copy.deepcopy(fresh[k])
    for k, v in fresh.items():
        t.setdefault(k, copy.deepcopy(v))
    t['cur'] = 0
    t['plates'] = [None] * _bowls_total(t)
    if t['status'] not in FS.DONE:
        t.update(bowl=_empty_bowl(), subs={}, refused=0)
        t['quoted_price'] = quote(c, t['needs']) if c is not None and t['needs']['style'] != 'open' else None


def _migrate(c: dict) -> dict:
    d = FS.migrate(c)
    d.setdefault('notebook', [])
    # Care across days: old saves treat the broth they hold as cooked today and still hot.
    warm = d.setdefault('pot_warm', {})
    lots = d.setdefault('pot_lots', {})
    if isinstance(warm, dict) and isinstance(lots, dict) and isinstance(d.get('pots'), dict):
        for b in BROTH_INDEX:
            warm.setdefault(b, True)
            if isinstance(lots.setdefault(b, []), list) and isinstance(d['pots'].get(b), int):
                _sync_lots(d, b)
    for key, v in (('prep', []), ('guests', {}), ('hlog', [])):
        d.setdefault(key, v)
    for t in c['tasks']:
        if t['career'] == ID and t.get('gen') != GEN:
            _upgrade_task(t, c)
        if t['career'] == ID:
            for k, v in TASK_EXTRA.items():
                t.setdefault(k, copy.deepcopy(v))
    return d


def _plan(c: dict) -> dict:
    return FS.plan(c, ID, MODS, EVENTS)


def _peek_plan(c: dict) -> dict:
    """Read-only view of today's plan (public projection must not write)."""
    p = kit.data(c).get('plan')
    if isinstance(p, dict) and p.get('day') == c['day']:
        return p
    return FS.new_plan(ID, c['day'], MODS, EVENTS)


def _mod(c: dict) -> dict:
    return MOD_INDEX[FS.pick_mod(ID, c['day'], MODS)['id']]


def _portions(pl: dict) -> int:
    return 2 if pl['mod'] == 'cold' else 1


def _price_mult(pl: dict) -> float:
    return 1.1 if pl['mod'] == 'festival' else 1.0


def _npc_index(t: dict) -> int:
    return int(t['npc'].rsplit('_', 1)[1]) - 1


# ------------------------------------------------------------------ care: broth overnight
def _sync_lots(d: dict, broth: str) -> None:
    """Keep the batches in a pot in step with its portion count (the count is what the kitchen uses)."""
    raw = d['pot_lots'][broth]
    if not all(isinstance(x, list) and len(x) == 2 and all(type(v) is int for v in x) for x in raw):
        return                                         # malformed: leave it for validate_data to reject
    lots = [list(x) for x in raw if x[0] > 0]
    have, want = sum(q for q, _ in lots), max(0, d['pots'][broth])
    while have > want and lots:                       # used from the oldest batch first
        take = min(lots[0][0], have - want)
        lots[0][0] -= take
        have -= take
        if not lots[0][0]:
            lots.pop(0)
    if have < want:                                    # more broth than batches: it was cooked today
        if lots and lots[-1][1] == 0:
            lots[-1][0] += want - have
        else:
            lots.append([want - have, 0])
    d['pot_lots'][broth] = lots


def _pot_age(d: dict, broth: str) -> int:
    """Nights spent by the oldest broth in the pot (0 when empty or fresh)."""
    lots = d.get('pot_lots', {}).get(broth) or []
    return lots[0][1] if lots and d['pots'].get(broth) else 0


def _pot_state(d: dict, broth: str) -> str:
    """empty · hot (ready to ladle) · cold (kept overnight, reheat first) · stale (too old, pour out)."""
    if not d['pots'].get(broth):
        return 'empty'
    if _pot_age(d, broth) > KEEP_NIGHTS:
        return 'stale'
    return 'hot' if d.get('pot_warm', {}).get(broth, True) else 'cold'


def _need_pot(d: dict, broth: str) -> None:
    name = BROTH_INDEX[broth]['name']
    st = _pot_state(d, broth)
    kit.need(st != 'stale', f'Nồi {name} còn phần nước dùng quá {KEEP_NIGHTS} đêm. Đổ phần cũ (🗑️) rồi chan tiếp nhé.')
    kit.need(st != 'cold', f'Nồi {name} để qua đêm còn nguội. Đun sôi lại trước (🔥 Đun lại).')


def _use_pot(d: dict, broth: str, n: int) -> int:
    """Ladle n portions, oldest batch first; returns the oldest age ladled (for the review)."""
    lots = d['pot_lots'][broth]
    age = lots[0][1] if lots else 0
    d['pots'][broth] -= n
    _sync_lots(d, broth)
    return age


def _cook(d: dict, broth: str, portions: int) -> bool:
    """Add a fresh batch; returns True when older broth is still in the pot (it is ladled first)."""
    older = any(age > 0 for _, age in d['pot_lots'][broth])
    d['pots'][broth] = min(POT_MAX, d['pots'][broth] + portions)
    _sync_lots(d, broth)
    d['pot_warm'][broth] = True
    return older


def _lots_text(lots: list) -> str:
    return ' + '.join(f'{q} phần {"mới" if not age else f"để {age} đêm"}' for q, age in lots)


def _pot_rows(c: dict, d: dict, tomorrow: bool = False) -> list[dict]:
    """Every unlocked pot as the player should see it (tonight's view with tomorrow=True)."""
    rows = []
    prep = d.get('prep', []) if tomorrow else []
    for b in BROTHS:
        if b['unlock'] > kit.level(c):
            continue
        q = d['pots'].get(b['id'], 0)
        lots = [[n, a + (1 if tomorrow else 0)] for n, a in (d.get('pot_lots', {}).get(b['id']) or [])] if q else []
        age = lots[0][1] if lots else 0
        if b['id'] in prep:
            q, age, st, lots = POT_MAX, 0, 'prep', [[POT_MAX, 0]]
        elif not q:
            st = 'empty'
        elif age > KEEP_NIGHTS:
            st = 'stale'
        elif tomorrow:
            st = 'cold'
        else:
            st = _pot_state(d, b['id'])
        stale = sum(n for n, a in lots if a > KEEP_NIGHTS)
        rows.append(dict(id=b['id'], name=b['name'], emoji=b['emoji'], portions=q, age=age if q else 0, state=st,
                         lots=lots, stale=stale, packs=kit.stock(c, b['pack'])))
    return rows


def _reheat(d: dict, broth: str | None = None) -> list[str]:
    cold = [b for b in BROTH_INDEX if _pot_state(d, b) == 'cold' and (broth is None or b == broth)]
    for b in cold:
        d['pot_warm'][b] = True
    return cold


def _apply_prep(s: dict, c: dict, d: dict) -> list[str]:
    """Dawn: pots simmered overnight open full and fresh."""
    lines = []
    for b in d.get('prep') or []:
        if b not in BROTH_INDEX:
            continue
        left = d['pots'][b]
        d['pots'][b] = POT_MAX
        d['pot_lots'][b] = [[POT_MAX, 0]]
        d['pot_warm'][b] = True
        name = BROTH_INDEX[b]['name']
        lines.append(f'🍲 Nồi {name} hầm từ tối qua đã sẵn sàng: {POT_MAX} phần nóng hổi.'
                     + (f' {left} phần cũ dành nấu bữa cơm nhân viên.' if left else ''))
    d['prep'] = []
    for line in lines:
        kit.log(s, c, 'stock', line)
    return lines


# ------------------------------------------------------------------ care: hygiene book
def _hygiene_today(c: dict, d: dict) -> dict:
    rules = _plan_rules(c)
    return dict(day=c['day'], clean=d['clean_checked_day'] == c['day'], dishes=not rules.get('dirty'),
                pots=not any(_pot_state(d, b) == 'stale' for b in BROTH_INDEX))


def _points(row: dict) -> int:
    return 2 * bool(row['clean']) + bool(row['dishes']) + bool(row['pots'])


def hygiene(d: dict) -> int:
    """Score of the last seven shifts (0–100). Days not written yet count as half marks."""
    rows = (d.get('hlog') or [])[-HLOG_DAYS:]
    pts = sum(_points(r) for r in rows) + 2 * (HLOG_DAYS - len(rows))
    return round(100 * pts / (4 * HLOG_DAYS))


def hygiene_grade(score: int) -> str:
    return 'A' if score >= HYGIENE_A else 'B' if score >= HYGIENE_B else 'C'


def _hygiene_public(c: dict, d: dict) -> dict:
    score = hygiene(d)
    rows = [dict(r, points=_points(r)) for r in (d.get('hlog') or [])[-HLOG_DAYS:]]
    today = _hygiene_today(c, d)
    return dict(score=score, grade=hygiene_grade(score), days=rows, logged=len(d.get('hlog') or []),
                today=dict(today, points=_points(today)), a=HYGIENE_A, b=HYGIENE_B)


# ------------------------------------------------------------------ care: regulars' habits
def _learned(g: dict | None) -> int:
    visits = (g or {}).get('visits', 0)
    return sum(1 for at in NOTE_AT if visits >= at)


def _regular_snapshot(d: dict, t: dict) -> dict | None:
    i = _npc_index(t)
    if i not in HABITS:
        return None
    g = d.get('guests', {}).get(t['npc'])
    n = _learned(g)
    if not n:
        return None
    return dict(bond=g['bond'], notes=[h[0] for h in HABITS[i][:n]])


def _usual_text(i: int) -> str:
    broth, tops, spice, takeaway, extra, _ = USUALS[i]
    parts = [f'{BROTH_INDEX[broth]["name"]} cấp {spice}'] + [f'{q} {ITEM_INDEX[k]["name"].lower()}' for k, q in tops.items()]
    if extra:
        parts.append('thêm 1 vắt')
    if takeaway:
        parts.append('mang về')
    return ', '.join(parts)


def _book(c: dict, d: dict) -> list[dict]:
    rows = []
    for npc, i in GUEST_IDS.items():
        g = d.get('guests', {}).get(npc) or dict(visits=0, bond=0)
        n = _learned(g)
        nxt = next((at for at in NOTE_AT if g['visits'] < at), None)
        rows.append(dict(npc=npc, name=PEOPLE[i][0], role=PEOPLE[i][1], about=PEOPLE[i][2], visits=g['visits'], bond=g['bond'],
                         notes=[dict(touch=k, emoji=TOUCHES[k][0], label=TOUCHES[k][1], text=text) for k, text in HABITS[i][:n]],
                         locked=len(HABITS[i]) - n, next_in=(nxt - g['visits']) if nxt else None,
                         usual=_usual_text(i) if i in USUALS and npc in d.get('notebook', []) else None,
                         tip=BOND_TIP if g['bond'] >= BOND_TIP_AT else 0))
    rows.sort(key=lambda r: (-r['bond'], -r['visits'], r['name']))
    return rows


def _guest_after(s: dict, c: dict, d: dict, t: dict) -> list[str]:
    """After a served order: the regular remembers the visit (and you learn their habits)."""
    i = _npc_index(t)
    if i not in HABITS:
        return []
    g = d['guests'].setdefault(t['npc'], dict(visits=0, bond=0))
    before = _learned(g)
    g['visits'] = min(999, g['visits'] + 1)
    snap = t.get('regular') or {}
    forgot = [k for k in snap.get('notes', []) if k not in t.get('touches', [])]
    name = PEOPLE[i][0]
    lines = []
    if t['refused'] or cq.safety(t):
        if g['bond']:
            g['bond'] -= 1
            lines.append(f'💔 {name} hơi buồn vì tô hôm nay (thân thiết {g["bond"]}/{BOND_MAX}).')
    elif not cq.slips(t) and not forgot:
        g['bond'] = min(BOND_MAX, g['bond'] + 1)
        if g['bond'] >= BOND_TIP_AT:
            kit.money(s, c, BOND_TIP, 'Khách quen gửi thêm tiền trà', t['id'], category='tip')
            lines.append(f'💛 {name} gửi thêm {BOND_TIP} xu tiền trà.')
    for k, text in HABITS[i][before:_learned(g)]:
        lines.append(f'📒 {name} dặn: “{text}” (đã ghi sổ khách quen)')
    return lines


# ------------------------------------------------------------------ care: tomorrow
def _outlook(c: dict, d: dict, closing: bool = False) -> dict:
    nxt = c['day'] + 1
    m = FS.pick_mod(ID, nxt, MODS)
    advice = []
    rows = _pot_rows(c, d, tomorrow=True)
    stale = [r['name'] for r in rows if r['state'] == 'stale']
    cold = [r['name'] for r in rows if r['state'] == 'cold']
    if stale:
        advice.append(f'Nồi {", ".join(stale)} sẽ quá {KEEP_NIGHTS} đêm vào sáng mai: dùng hết tối nay, hoặc hầm sẵn nồi mới.')
    if cold:
        advice.append(f'Sáng mai nhớ đun lại nồi {", ".join(cold)} trước khi chan (một lượt cho mọi nồi).')
    ready = sum(r['portions'] for r in rows if r['state'] in ('cold', 'prep'))
    if m['id'] == 'cold':
        advice.append(f'Gió lạnh: mỗi tô tốn 2 phần nồi, mai mới có {ready} phần — nên hầm sẵn 1–2 nồi tối nay.')
    elif m['id'] in ('lunch_rush', 'festival') and ready < 18:
        advice.append(f'Mai khách đông: hầm sẵn nồi tối nay để khỏi nấu giữa giờ (mai mới có {ready} phần).')
    if m['id'] == 'rain' and kit.stock(c, 'box') < 8:
        advice.append(f'Trời mưa, khách mang về nhiều: kho còn {kit.stock(c, "box")} hộp — nhập thêm hộp.')
    if m['id'] == 'students' and kit.stock(c, 'cheese_slice') < 6:
        advice.append(f'Học sinh thích phô mai: kho còn {kit.stock(c, "cheese_slice")} lát.')
    if m['id'] == 'beef_day':
        advice.append('Bò Mỹ về hàng: nhà cung cấp tặng 4 phần bò, khách hay gọi thêm bò.')
    if not closing and c['open'] and d['clean_checked_day'] != c['day']:
        advice.append('Sổ vệ sinh hôm nay còn trống: bấm “🧽 Kiểm vệ sinh bếp” trước khi khép ca.')
    return dict(day=nxt, emoji=m['emoji'], label=m['label'], hint=m['hint'], advice=advice[:5])


# ------------------------------------------------------------------ prices
def quote(c: dict, needs: dict) -> int:
    price = 0
    for b in _specs(needs):
        price += kit.price(c, b['broth'], SPEC['prices'][b['broth']])
        price += sum(ITEM_INDEX[k]['price'] * q for k, q in b['toppings'].items())
        price += (10 if b['extra_noodle'] else 0) + (3 if needs['takeaway'] else 0)
    return max(1, round(price * (1.1 if _mod(c)['id'] == 'festival' else 1.0)))


def bowl_price(c: dict, bowl: dict) -> int:
    """What the bowl as made is worth on the menu (open orders pay this, up to the budget)."""
    if not bowl['broth']:
        return 0
    price = kit.price(c, bowl['broth'], SPEC['prices'][bowl['broth']])
    price += sum(ITEM_INDEX[k]['price'] * q for k, q in bowl['toppings'].items())
    price += 10 * max(0, len(bowl['noodles']) - 1) + (3 if bowl['container'] == 'box' else 0)
    return max(1, round(price * (1.1 if _mod(c)['id'] == 'festival' else 1.0)))


def on_task(s: dict, c: dict, t: dict) -> None:
    if t.get('gen') != GEN:
        _upgrade_task(t, c)
    if t.get('quoted_price') is None and t['needs']['style'] != 'open':
        t['quoted_price'] = quote(c, t['needs'])
    if t['status'] not in FS.DONE and t.get('regular') is None:
        t['regular'] = _regular_snapshot(kit.data(c), t)
    if t['guest']['kind'] == 'regular' and t.get('story') is None:
        i = _npc_index(t)
        if i in REGULAR_STORY:
            visits = kit.data(c).get('regulars', {}).get(t['npc'], 0)
            t['story'] = REGULAR_STORY[i][min(visits, len(REGULAR_STORY[i]) - 1)]
    pl = _plan(c)
    if pl['rules'].get('critic_next') and t['status'] not in FS.DONE and t.get('vip') is None:
        t['vip'] = 'critic'
        pl['rules']['critic_next'] = False
        pl['rules']['critic'] = t['id']


def on_start(s: dict, c: dict) -> None:
    d = _migrate(c)
    pl = _plan(c)
    lines = _apply_prep(s, c, d)
    cold = [BROTH_INDEX[b]['name'] for b in BROTH_INDEX if _pot_state(d, b) == 'cold']
    stale = [BROTH_INDEX[b]['name'] for b in BROTH_INDEX if _pot_state(d, b) == 'stale']
    if stale:
        FS.flash(pl, 'bad', f'🗑️ Nồi {", ".join(stale)} có phần để quá {KEEP_NIGHTS} đêm: đổ phần cũ trước khi chan.'
                 + (f' Nồi {", ".join(cold)} cần đun lại.' if cold else ''))
    elif cold:
        FS.flash(pl, 'info', f'🔥 Nồi {", ".join(cold)} để qua đêm: đun sôi lại trước khi chan (một lượt cho mọi nồi).')
    elif lines:
        FS.flash(pl, 'good', lines[0])
    for t in c['tasks']:
        if t['career'] == ID and t['status'] not in FS.DONE:
            on_task(s, c, t)
    if pl['mod'] == 'beef_day' and not pl['rules'].get('beef_gift'):
        pl['rules']['beef_gift'] = True
        if kit.stock(c, 'beef') + 4 <= SPEC['inventory']['capacity']:
            kit.add_lot(c, 'beef', 4, 0, 2, 'gift')
            kit.log(s, c, 'stock', 'Nhà cung cấp tặng 4 phần bò Mỹ mừng hàng mới về.')
            FS.flash(pl, 'good', '🥩 Nhà cung cấp tặng 4 phần bò Mỹ mừng hàng mới về.')


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if n.get('party'):
        rows = []
        for i, b in enumerate(n['party'], 1):
            tops = ', '.join(f'{q} {ITEM_INDEX[k]["name"].lower()}' for k, q in b['toppings'].items())
            rows.append(f'tô {i} là {BROTH_INDEX[b["broth"]]["name"].lower()} cấp {b["spice"]}, {tops}' + (', thêm 1 vắt' if b['extra_noodle'] else ''))
        return f'{len(n["party"])} tô ăn tại quán: ' + '; '.join(rows) + '. ' + n['note']
    if n['style'] == 'usual' and not t.get('recalled'):
        return 'Như mọi khi nhé! (Tra sổ khách quen hoặc hỏi lại món.)'
    if n['style'] == 'open':
        o = n['open']
        parts = [f'Tô tùy quán · ngân sách {o["budget"]} xu · cay cấp {o["spice"][0]}–{o["spice"][1]}']
        if o['broths']:
            parts.append('nước dùng: ' + ' hoặc '.join(BROTH_INDEX[b]['name'].lower() for b in o['broths']))
        if o['must']:
            parts.append('phải có ' + ', '.join(ITEM_INDEX[k]['name'].lower() for k in o['must']))
        if o['avoid']:
            parts.append('không ' + ', '.join(ITEM_INDEX[k]['name'].lower() for k in o['avoid']))
        if o['veg']:
            parts.append('ăn chay')
        parts.append(f'ít nhất {o["min_tops"]} phần topping')
        if o['takeaway']:
            parts.append('mang về')
        text = ' · '.join(parts)
        if o['allergy']:
            text += '. ⚠️ Dị ứng hải sản'
        return text + '. ' + n['note']
    if n['style'] == 'picture':
        tops = ' '.join(ITEM_INDEX[k]['emoji'] * q for k, q in n['toppings'].items())
        return f'👉 {BROTH_INDEX[n["broth"]]["emoji"]} · 🌶️×{n["spice"]} · {tops}' + (' · 🍜🍜' if n['extra_noodle'] else '') + (' · 🥡' if n['takeaway'] else '')
    tops = ', '.join(f'{q} {ITEM_INDEX[k]["name"].lower()}' for k, q in n['toppings'].items())
    text = f'{"1 hộp mang về" if n["takeaway"] else "1 tô"} mì {BROTH_INDEX[n["broth"]]["name"].lower()}, cấp cay {n["spice"]}, topping: {tops}'
    if n['extra_noodle']:
        text += ', thêm 1 vắt mì'
    if n['allergy']:
        text += '. ⚠️ Dị ứng hải sản'
    return text + '. ' + n['note']


def _wanted_noodles(n: dict) -> int:
    return 2 if n['extra_noodle'] else 1


def _spice_range(n: dict) -> tuple[int, int]:
    if n['style'] == 'open':
        return n['open']['spice'][0], n['open']['spice'][1]
    return n['spice'], n['spice']


def _boiling(c: dict) -> list[dict]:
    return [t for t in c['tasks'] if t['career'] == ID and t['status'] not in FS.DONE and t['bowl']['boiling']]


def _doneness(seconds: float) -> str:
    if seconds < BOIL['raw']:
        return 'raw'
    if seconds <= BOIL['perfect']:
        return 'perfect'
    if seconds <= BOIL['soft']:
        return 'soft'
    return 'mushy'


def _drain_patience(c: dict, amount: int, keep: str | None = None) -> None:
    """Waiting guests lose patience (an event took the kitchen's time)."""
    if c['life'].get('mode') == 'calm':
        return
    for t in FS.open_tasks(c, ID):
        if t['id'] != keep:
            t['patience'] = max(25, t.get('patience', 100) - amount)


def _hard_problem(t: dict, bowl: dict, i: int | None = None) -> str | None:
    """Why the guest hands the bowl back (None = they accept it)."""
    n = _spec(t, i)
    o = n['open'] or {}
    if o.get('veg') and (any(k in MEAT for k in bowl['toppings']) or BROTH_INDEX[bowl['broth']].get('allergen')):
        return 'khách ăn chay mà tô có thịt, cá hoặc nước dùng hải sản. Đổ tô và làm lại.'
    if n['style'] == 'open':
        if o.get('broths') and bowl['broth'] not in o['broths']:
            names = ' hoặc '.join(BROTH_INDEX[b]['name'].lower() for b in o['broths'])
            return f'khách chỉ ăn nước dùng {names}. Đổ tô và làm lại.'
    elif bowl['broth'] != n['broth']:
        return f'khách gọi {BROTH_INDEX[n["broth"]]["name"].lower()}. Đổ tô và làm lại.'
    if t['guest']['kind'] == 'kid' and bowl['chili'] > _spice_range(n)[1]:
        return 'bé chê cay quá, không ăn được. Đổ tô và làm lại.'
    return None


PHYSICAL = ('rs_boil', 'rs_broth', 'rs_topping', 'rs_serve', 'rs_dump', 'rs_batch', 'rs_wash', 'rs_plate', 'rs_reheat', 'rs_toss', 'rs_prep')
APP_DRAIN = 1      # a delivery driver is waiting at the door: app orders lose patience a little faster
BOWL_ACTIONS = ('rs_container', 'rs_boil', 'rs_broth', 'rs_topping', 'rs_chili', 'rs_lid')


def _walkin_chance(c: dict, pl: dict) -> float:
    m = MOD_INDEX[pl['mod']]
    base = m.get('walkin', 0.0)
    if base and c['day'] >= 4:
        base += min(0.2, 0.02 * c['day'])
    return base


SIZE_BASE = 4      # boil + broth + 2 toppings: one usual bowl (kit.size_factor: a bigger table waits longer)
MAX_SCOOP = 4      # topping portions one tap can add (the +/− steps on a topping tile)


def _units(t: dict) -> int:
    """How big an order is: per bowl, boiling and broth plus every topping portion."""
    return sum(2 + sum(b['toppings'].values()) for b in _specs(t['needs']))


def _patience_extra(c: dict, pl: dict) -> int:
    m = MOD_INDEX[pl['mod']]
    return m.get('patience', 0) + (1 if c['day'] >= 9 and m['id'] != 'quiet' else 0)


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _migrate(c)
    pl = _plan(c)
    out = _handle(s, c, d, pl, name, p)
    active = p.get('task') or c.get('active_task')
    if name in PHYSICAL:
        FS.patience_tick(c, ID, active, _patience_extra(c, pl), lambda t: kit.size_factor(_units(t), SIZE_BASE))
        if c['open'] and c['life'].get('mode') != 'calm':
            for t in FS.open_tasks(c, ID):
                if t.get('app') and t['id'] != active and not t.get('deferred'):
                    t['patience'] = max(25, t.get('patience', 100) - APP_DRAIN)
    if name.startswith('rs_') and name not in ('rs_pot', 'rs_event', 'rs_batch', 'rs_wash'):
        kit.worked(c, active)
    return out


def _handle(s: dict, c: dict, d: dict, pl: dict, name: str, p: dict) -> dict:
    rules = pl['rules']
    if name == 'rs_pot':
        broth = kit.one_of(p.get('broth'), BROTH_INDEX, 'Nồi nước dùng không tồn tại.')
        b = BROTH_INDEX[broth]
        kit.need(b['unlock'] <= kit.level(c), f'Nồi {b["name"]} mở ở cấp {b["unlock"]}.')
        kit.need(_pot_state(d, broth) != 'stale', f'Nồi {b["name"]} còn phần nước dùng quá {KEEP_NIGHTS} đêm. Đổ phần cũ (🗑️) rồi mới nấu mẻ mới.')
        kit.need(d['pots'][broth] + POT_BATCH <= POT_MAX, 'Nồi còn nhiều, chưa cần nấu thêm.')
        cost = kit.take(c, b['pack'], 1)
        mixed = _cook(d, broth, POT_BATCH)
        kit.metric(c, 'pots_cooked')
        extra = f' Trong nồi: {_lots_text(d["pot_lots"][broth])} — phần cũ được chan trước.' if mixed else ''
        return dict(message=f'Đã nấu thêm nồi {b["name"]}: +{POT_BATCH} phần nước dùng.{extra}', cost=cost)
    if name == 'rs_reheat':
        broth = None if p.get('broth') in (None, '') else kit.one_of(p.get('broth'), BROTH_INDEX, 'Nồi nước dùng không tồn tại.')
        done = _reheat(d, broth)
        kit.need(done, 'Không có nồi nào nguội cần đun lại.')
        kit.metric(c, 'pots_reheated', len(done))
        names = ', '.join(BROTH_INDEX[x]['name'] for x in done)
        return dict(message=f'🔥 Đã đun sôi lại nồi {names}. Nước dùng nóng, chan được cả ngày hôm nay.')
    if name == 'rs_toss':
        kit.confirm(p, 'Xác nhận đổ bỏ nồi nước dùng; phần còn lại ghi vào hao hụt.')
        broth = kit.one_of(p.get('broth'), BROTH_INDEX, 'Nồi nước dùng không tồn tại.')
        b = BROTH_INDEX[broth]
        kit.need(d['pots'][broth] > 0, 'Nồi đang trống.')
        old = [x for x in d['pot_lots'][broth] if x[1] > KEEP_NIGHTS]
        kit.need(old, f'Nồi {b["name"]} chưa có phần nào quá {KEEP_NIGHTS} đêm, vẫn dùng được.')
        q = sum(n for n, _ in old)
        value = max(1, round(q * ITEM_INDEX[b['pack']]['cost'] / POT_BATCH))
        kit.waste(c, b['pack'], 1, value, f'Đổ {q} phần nước dùng {b["name"].lower()} để quá {KEEP_NIGHTS} đêm')
        d['pots'][broth] -= q
        _sync_lots(d, broth)
        kit.metric(c, 'pots_tossed')
        left = d['pots'][broth]
        return dict(message=f'🗑️ Đã đổ {q} phần nước dùng {b["name"].lower()} quá hạn.' + (f' Còn {left} phần mới hơn trong nồi.' if left else ' Nồi đã rửa sạch, nấu mẻ mới khi cần nhé.'))
    if name == 'rs_prep':
        kit.confirm(p, 'Xác nhận hầm sẵn nồi cho ngày mai.')
        broth = kit.one_of(p.get('broth'), BROTH_INDEX, 'Nồi nước dùng không tồn tại.')
        b = BROTH_INDEX[broth]
        kit.need(b['unlock'] <= kit.level(c), f'Nồi {b["name"]} mở ở cấp {b["unlock"]}.')
        kit.need(broth not in d['prep'], f'Nồi {b["name"]} đã được hầm sẵn cho mai rồi.')
        kit.need(len(d['prep']) < PREP_MAX, f'Bếp chỉ có {PREP_MAX} bếp riu riu để hầm qua đêm.')
        kit.need(kit.stock(c, b['pack']) >= PREP_PACKS, f'Cần {PREP_PACKS} {ITEM_INDEX[b["pack"]]["name"].lower()} để hầm một nồi đầy.')
        cost = kit.take(c, b['pack'], PREP_PACKS)
        d['prep'].append(broth)
        kit.metric(c, 'pots_prepped')
        return dict(message=f'🌙 Đã bắc nồi {b["name"]} lên bếp riu riu. Sáng mai mở ca là có {POT_MAX} phần nóng hổi.', cost=cost)
    if name == 'rs_clean':
        kit.need(d['clean_checked_day'] != c['day'], 'Hôm nay đã kiểm vệ sinh bếp rồi.')
        d['clean_checked_day'] = c['day']
        kit.metric(c, 'hygiene_checks')
        return dict(message='Đã lau bếp, thay nước rửa, kiểm tủ lạnh và ghi sổ vệ sinh ca.')
    if name == 'rs_event':
        return FS.resolve(s, c, pl, EVENT_INDEX, p)
    if name == 'rs_wash':
        kit.need(rules.get('dirty', 0) > 0, 'Chưa có tô bẩn nào cần rửa.')
        n = rules['dirty']
        rules['dirty'] = 0
        kit.metric(c, 'bowls_washed', n)
        return dict(message=f'Đã rửa {n} tô, úp lên giá cho ráo.')
    if name == 'rs_batch':
        return _batch(s, c, d, pl)
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Công việc không thuộc quán mì.')
    kit.need(t['known'], 'Đọc phiếu order của khách trước nhé (bấm “Nhận order”).')
    if t.get('quoted_price') is None and t['needs']['style'] != 'open':
        on_task(s, c, t)
    bowl = t['bowl']
    n = t['needs']
    sp = _spec(t)
    msg = 'Đã cập nhật tô mì.'
    if name in BOWL_ACTIONS and n.get('party'):
        kit.need(t['plates'][t['cur']] is None, 'Các tô đều đã lên khay. Giao món, hoặc chọn một tô để sửa.')
    if name == 'rs_plate':
        kit.need(n.get('party'), 'Đơn này chỉ có một tô.')
        kit.need(bowl['container'] and bowl['broth'] and bowl['noodles'], f'Tô {t["cur"] + 1} cần có mì và nước dùng trước.')
        kit.need(not bowl['boiling'], 'Còn mì đang luộc trong rổ của tô này.')
        kit.need(bowl['container'] != 'box' or bowl['lid'], 'Đậy nắp hộp trước khi đặt lên khay.')
        done = t['cur']
        t['plates'][done] = bowl
        t['bowl'] = _empty_bowl()
        left = [i for i, x in enumerate(t['plates']) if x is None]
        if left:
            t['cur'] = left[0]
            return dict(message=f'Tô {done + 1} xong, đặt lên khay. Giờ làm tô {left[0] + 1} nhé.')
        return dict(message=f'Đủ {len(t["plates"])} tô trên khay. Giao món thôi!')
    if name == 'rs_tab':
        kit.need(n.get('party'), 'Đơn này chỉ có một tô.')
        i = kit.integer(p.get('index'), 0, len(t['plates']) - 1)
        kit.need(i != t['cur'] or t['plates'][i] is not None, 'Bạn đang làm tô này rồi.')
        idle = not (bowl['container'] or bowl['noodles'] or bowl['boiling'])
        kit.need(idle or t['plates'][t['cur']] is not None, f'Tô {t["cur"] + 1} đang làm dở. Làm xong (bấm “Xong tô”) hoặc đổ tô rồi mới chuyển nhé.')
        t['cur'] = i
        if t['plates'][i] is not None:
            t['bowl'] = t['plates'][i]
            t['plates'][i] = None
            return dict(message=f'Đã lấy tô {i + 1} xuống khỏi khay để sửa.')
        return dict(message=f'Chuyển sang tô {i + 1}.')
    if name == 'rs_recall':
        kit.need(n['style'] == 'usual', 'Đây không phải món quen.')
        kit.need(not t['recalled'], 'Đã mở sổ món quen của khách này rồi.')
        kit.need(t['npc'] in d['notebook'], 'Sổ khách quen chưa ghi món của người này. Hỏi lại khách nhé.')
        t['recalled'] = True
        return dict(message='📒 Đã tra sổ khách quen: món của khách hiện trên phiếu order.')  # the ticket lists it; no second copy in a toast
    if name == 'rs_reask':
        kit.need(n['style'] == 'usual', 'Đây không phải món quen.')
        kit.need(not t['recalled'], 'Bạn đã biết món quen của khách rồi.')
        t['recalled'] = True
        t['reasked'] = True
        if c['life'].get('mode') != 'calm':
            t['patience'] = max(25, t.get('patience', 100) - 15)
        if t['npc'] not in d['notebook']:
            d['notebook'].append(t['npc'])
        who = USUAL_NAME.get(_npc_index(t), 'Khách')
        return dict(message=f'{who[:1].upper() + who[1:]} hơi chững lại: “Quên rồi hả?” Món đã hiện trên phiếu order và được ghi vào sổ khách quen.')
    if name == 'rs_container':
        kind = kit.one_of(p.get('kind'), ('bowl', 'box'), 'Chọn tô hoặc hộp.')
        kit.need(bowl['container'] is None, 'Đã có tô/hộp. Đổ tô nếu muốn làm lại.')
        if kind == 'bowl':
            kit.need(rules.get('dirty', 0) < DIRTY_MAX, 'Hết tô sạch rồi! Rửa chồng tô bẩn trước nhé.')
        if kind == 'box':
            bowl['cost'] += kit.take(c, 'box', 1)
        bowl['container'] = kind
        kit.start_work(t)
        msg = 'Đã lấy ' + ('hộp mang về.' if kind == 'box' else 'tô ăn tại quán.')
    elif name == 'rs_boil':
        kit.need(bowl['container'], 'Lấy tô hoặc hộp trước.')
        kit.need(not bowl['boiling'], 'Rổ mì của đơn này đang luộc.')
        kit.need(len(bowl['noodles']) < 2, 'Tô đã đủ mì.')
        kit.need(len(_boiling(c)) < 2, 'Cả hai rổ luộc đang bận. Vớt một rổ trước nhé.')
        bowl['cost'] += kit.take(c, 'noodle', 1)
        bowl['boiling'] = round(kit.now(), 3)
        kit.start_work(t)
        shift = WEAK_FIRE if rules.get('weak_fire') else 0
        msg = f'Đã thả mì. Vớt khi thanh luộc vào vùng xanh ({BOIL["raw"] + shift}–{BOIL["perfect"] + shift} giây).'
    elif name == 'rs_drain':
        kit.need(bowl['boiling'], 'Mì đã vớt ra tô rồi, làm bước tiếp theo nhé.' if bowl['noodles'] else 'Chưa thả mì vào rổ. Bấm “🍜 Thả mì” trước nhé.')
        seconds = max(0.0, kit.now() - bowl['boiling'])
        shift = WEAK_FIRE if rules.get('weak_fire') else 0
        done = _doneness(max(0.0, seconds - shift))
        bowl['noodles'].append(done)
        bowl['boiling'] = None
        msg = {'raw': 'Mì còn sống, sợi cứng.', 'perfect': 'Mì chín tới, sợi dai vừa!', 'soft': 'Mì hơi mềm nhưng vẫn ăn được.', 'mushy': 'Mì bị nát rồi…'}[done] + f' ({seconds:.1f} giây)'
        if done in ('raw', 'mushy'):
            t['mistakes'] += 1
    elif name == 'rs_broth':
        kit.need(bowl['container'], 'Lấy tô hoặc hộp trước.')
        kit.need(bowl['broth'] is None, 'Tô đã có nước dùng.')
        broth = kit.one_of(p.get('broth'), BROTH_INDEX, 'Nồi nước dùng không tồn tại.')
        portions = _portions(pl)
        if d['pots'][broth]:
            _need_pot(d, broth)
        kit.need(d['pots'][broth] >= portions, f'Nồi {BROTH_INDEX[broth]["name"]} không đủ nước dùng. Nấu thêm từ gói nước dùng.')
        t['broth_age'] = max(t.get('broth_age', 0), min(KEEP_NIGHTS, _use_pot(d, broth, portions)))
        bowl['broth'] = broth
        if (n['style'] != 'open' and sp['broth'] and broth != sp['broth']) or (n['style'] == 'open' and n['open']['broths'] and broth not in n['open']['broths']):
            t['mistakes'] += 1
        msg = 'Đã chan nước dùng ' + BROTH_INDEX[broth]['name'].lower() + ('. Trời lạnh, khách xin chan đầy: tốn 2 phần nồi.' if portions > 1 else '.')
    elif name == 'rs_topping':
        kit.need(bowl['container'], 'Lấy tô hoặc hộp trước.')
        item = kit.one_of(p.get('item'), TOPPINGS, 'Topping không tồn tại.')
        qty = 1 if p.get('n') is None else kit.integer(p.get('n'), 1, MAX_SCOOP)
        kit.need(ITEM_INDEX[item].get('unlock', 1) <= kit.level(c), f'Mở khóa {ITEM_INDEX[item]["name"]} ở cấp {ITEM_INDEX[item].get("unlock", 1)}.')
        kit.need(sum(bowl['toppings'].values()) < 8, 'Tô đầy topping rồi.')
        kit.need(sum(bowl['toppings'].values()) + qty <= 8, f'Tô chỉ còn chỗ cho {8 - sum(bowl["toppings"].values())} phần topping.')
        for _ in range(qty):
            bowl['cost'] += kit.take(c, item, 1)
            bowl['toppings'][item] = bowl['toppings'].get(item, 0) + 1
            if n['style'] == 'open':
                o = n['open']
                if item in o['avoid'] or (o['veg'] and item in MEAT) or (n['allergy'] and ITEM_INDEX[item].get('allergen') == n['allergy']):
                    t['mistakes'] += 1
            else:
                wanted = (0 if item in t['subs'] else sp['toppings'].get(item, 0)) + sum(sp['toppings'].get(k, 0) for k, v in t['subs'].items() if v == item)
                if bowl['toppings'][item] > wanted and rules.get('pamper') != t['id']:
                    t['mistakes'] += 1
        msg = 'Thêm ' + (f'{qty} phần ' if qty > 1 else '') + ITEM_INDEX[item]['name'] + '.'
    elif name == 'rs_chili':
        kit.need(bowl['container'], 'Lấy tô hoặc hộp trước.')
        kit.need(bowl['chili'] < 10, 'Đủ cay rồi!')
        bowl['cost'] += kit.take(c, 'chili', 1)
        bowl['chili'] += 1
        low, high = _spice_range(sp)
        if bowl['chili'] > high:
            t['mistakes'] += 1
        msg = f'Bơm sốt ớt: {bowl["chili"]}/{high if low == high else f"{low}–{high}"} lượt.'
    elif name == 'rs_lid':
        kit.need(bowl['container'] == 'box', 'Chỉ hộp mang về mới cần nắp.')
        kit.need(not bowl['lid'], 'Đã đậy nắp.')
        bowl['lid'] = True
        msg = 'Đã đậy nắp, dán tem niêm phong.'
    elif name == 'rs_sub':
        # Out of a topping: offer a substitute; the customer decides by personality.
        want = {}
        for b in _specs(n):
            for k, q in b['toppings'].items():
                want[k] = want.get(k, 0) + q
        item = kit.one_of(p.get('item'), want, 'Món này không có trong order.')
        sub = kit.one_of(p.get('substitute'), TOPPINGS, 'Món thay không tồn tại.')
        kit.need(item not in t['subs'], 'Đã hỏi khách đổi món này rồi.')
        kit.need(kit.stock(c, item) < want[item] or (item == 'beef' and rules.get('bad_beef')), 'Kho vẫn còn món này, không cần đổi.')
        kit.need(sub != item and not (n['allergy'] and ITEM_INDEX[sub].get('allergen') == n['allergy']), 'Món thay không phù hợp với khách.')
        t['subs'][item] = sub
        msg = f'Khách đồng ý đổi {ITEM_INDEX[item]["name"]} sang {ITEM_INDEX[sub]["name"]}, giá tô giữ nguyên.'
    elif name == 'rs_dump':
        kit.confirm(p, 'Xác nhận đổ tô; nguyên liệu đã dùng ghi vào hao hụt.')
        kit.need(bowl['container'] or bowl['noodles'] or bowl['boiling'], 'Tô đang trống.')
        kit.waste(c, 'bowl', 1, bowl['cost'], 'Đổ tô làm lại')
        t['bowl'] = _empty_bowl()
        t['mistakes'] += 1
        d['dumped'] += 1
        kit.metric(c, 'bowls_dumped')
        msg = 'Đã đổ tô. Làm lại từ đầu nhé.'
    elif name == 'rs_touch':
        return _touch(c, d, t, p)
    elif name == 'rs_serve':
        return _serve(s, c, d, pl, t, p)
    else:
        raise kit.eng().GameError('Thao tác bếp không hợp lệ.')
    return dict(message=msg)


def _serve(s: dict, c: dict, d: dict, pl: dict, t: dict, p: dict) -> dict:
    kit.confirm(p, 'Xác nhận giao món cho khách.')
    bowl, n, rules = t['bowl'], t['needs'], pl['rules']
    group = bool(n.get('party'))
    plates, cur = t['plates'], t['cur']
    if not group or plates[cur] is None:
        label = f'Tô {cur + 1}' if group else 'Tô'
        kit.need(bowl['container'] and bowl['broth'] and bowl['noodles'], f'{label} cần có mì và nước dùng.')
        kit.need(not bowl['boiling'], 'Còn mì đang luộc trong rổ của đơn này.')
    if group:
        missing = [str(i + 1) for i, x in enumerate(plates) if x is None and i != cur]
        kit.need(not missing, 'Còn tô ' + ', '.join(missing) + ' chưa xong. Làm xong từng tô rồi giao một lượt nhé.')
    ev = FS.open_event(pl)
    kit.need(not ev, 'Có chuyện cần bạn quyết trước: ' + (EVENT_INDEX[ev['id']]['title'] if ev else '') + '.')
    bowls = [x if x is not None else bowl for x in plates] if group else [bowl]
    for i, b in enumerate(bowls):
        problem = _hard_problem(t, b, i if group else None)
        if problem:
            if group:
                problem = f'tô {i + 1}: {problem}'
                # Put the finished bowls on the tray and bring the returned one back to the counter.
                if plates[cur] is None:
                    plates[cur] = bowl
                t['cur'] = i
                t['bowl'] = plates[i]
                plates[i] = None
            t['refused'] += 1
            t['mistakes'] += 1
            pl['refused'] += 1
            # The guest remembers having to send a bowl back (one small slip after the redo).
            cq.downgrade(t, 'returned', _returned_line(t, b, i if group else None), 'phải trả lại tô')
            kit.log(s, c, 'refused', 'Khách trả lại tô: ' + problem, t['npc'], t['id'])
            FS.flash(pl, 'bad', '↩️ Khách trả lại tô: ' + problem)
            return dict(message='Khách không nhận: ' + problem, refused=True)
    for b in bowls:
        if b['container'] == 'box':
            kit.need(b['lid'], 'Đậy nắp hộp mang về trước khi giao.')
    price = sum(bowl_price(c, b) for b in bowls)
    if n['style'] == 'open':
        pay = min(price, n['open']['budget'])
        t['over_budget'] = price > n['open']['budget']
    else:
        pay = t['quoted_price']
    if rules.get('discount'):
        pay = max(1, round(pay * 0.9))
    faulty = _record_slips(c, t, bowls, rules)
    if cq.slips(t) and not t['mistakes']:
        t['mistakes'] = 1
    if faulty and cq.decide(c, t, remake=True) == 'remake':
        cq.react(s, c, t, pay, remake=True, who=_who(t))
        first = cq.slips(t)[0]['text']
        i = faulty[0] if faulty else 0
        if group:
            if plates[cur] is None:
                plates[cur] = bowl
            t['cur'] = i
            t['bowl'] = plates[i]
            plates[i] = None
        if c['life'].get('mode') != 'calm':
            t['patience'] = max(25, t.get('patience', 100) - 10)
        cq.downgrade(t, 'returned', f'{first} Phải làm lại.', 'phải làm lại')
        kit.log(s, c, 'refused', 'Khách trả lại tô: ' + first, t['npc'], t['id'])
        FS.flash(pl, 'bad', '↩️ Khách trả lại tô: ' + first)
        return dict(message=f'{_who(t)}: “{first}” Khách đẩy tô lại, sửa giúp khách nhé.', refused=True, correct=False)
    r = cq.react(s, c, t, pay, who=_who(t))
    t['quoted_price'] = pay
    pay = r['pay']
    t['served'] = dict(bowl=copy.deepcopy(bowls[0]), bowls=copy.deepcopy(bowls), price=price)
    if group:
        t['plates'] = copy.deepcopy(bowls)
        t['bowl'] = _empty_bowl()
    d['bowls_served'] += len(bowls)
    kit.metric(c, 'bowls_served', len(bowls))
    if 'dirty' in rules:
        rules['dirty'] = min(50, rules['dirty'] + sum(1 for b in bowls if b['container'] == 'bowl'))
    acc = _score(c, t)[0]
    perfect = not t['refused'] and not cq.slips(t) and all(x == 'perfect' for b in bowls for x in b['noodles']) and acc == 5
    if perfect:
        kit.metric(c, 'perfect_bowls')
    if n['style'] == 'open':
        kit.metric(c, 'open_bowls')
    if group:
        kit.metric(c, 'group_tables')
    if t.get('app'):
        kit.metric(c, 'app_orders')
    kit.complete(s, c, t, pay, f'Bạn đã nấu “{t["title"]}” cho khách.')
    lines = FS.after_serve(s, c, ID, pl, t, _walkin_chance(c, pl))
    lines += _guest_after(s, c, d, t)
    if n['style'] == 'usual' and t['npc'] not in d['notebook']:
        d['notebook'].append(t['npc'])
        lines.append('📒 Đã ghi món quen vào sổ khách quen.')
    if pl['mod'] == 'rain' and bowls[0]['container'] == 'box' and bowls[0]['lid'] and t['mistakes'] == 0:
        kit.money(s, c, 2, 'Khách đội mưa khen hộp đậy kín', t['id'], category='tip')
        lines.append('🌧️ Hộp kín, khách đội mưa vẫn cười: +2 xu.')
    if t.get('vip') == 'critic':
        lines.append(_critic_result(s, c, pl, t))
    if rules.get('wallet') == 'kept':
        rules['wallet'] = 'returned'
        kit.money(s, c, 10, 'Chủ ví cảm ơn quán', f'wallet-{c["day"]}', category='other_income')
        lines.append('👛 Cô bé chủ ví quay lại cảm ơn, mẹ bé gửi quán 10 xu tiền nước.')
    b = rules.get('batch')
    if isinstance(b, dict) and b['status'] == 'open' and pl['served'] > b['due'] + 1:
        b['status'] = 'failed'
        _event_outcome(pl, 'catering', False, 'Văn phòng chờ lâu quá nên hủy đơn đặt.')
        lines.append('📦 Văn phòng chờ lâu quá nên hủy đơn đặt.')
    opened = FS.trigger(s, c, pl, EVENT_INDEX)
    if opened:
        lines.append('⚡ ' + EVENT_INDEX[opened['id']]['title'])
    head = f'Đã giao món · +{pay} xu.'
    if r['message']:
        head += ' ' + r['message']
    if not opened:
        FS.flash(pl, 'good' if perfect else 'info', ('⭐ Tô hoàn hảo! ' if perfect else '🍜 Đã giao. ') + ' '.join(lines[:2]))
    return dict(message=head + (' ' + ' '.join(lines) if lines else ' Khách đang ăn và sẽ để lại đánh giá.'), celebrate=True)


def _touch(c: dict, d: dict, t: dict, p: dict) -> dict:
    """A little habit of a regular (no turn): iced tea, a wet towel, scalded chopsticks…"""
    touch = kit.one_of(p.get('touch'), TOUCHES, 'Việc này không có trong sổ khách quen.')
    snap = t.get('regular') or {}
    kit.need(touch in snap.get('notes', []), 'Sổ khách quen chưa ghi thói quen này của khách.')
    kit.need(touch not in t['touches'], 'Đã làm việc này cho khách rồi.')
    msg = TOUCHES[touch][0] + ' ' + TOUCHES[touch][1] + '.'
    if touch == 'soup':
        plates = [x for x in t['plates'] if x is not None]
        broth = t['bowl']['broth'] or next((x['broth'] for x in plates if x['broth']), None)
        kit.need(broth, 'Chan nước dùng vào tô trước, rồi mới múc thêm chén riêng.')
        _need_pot(d, broth)
        kit.need(d['pots'][broth] >= 1, f'Nồi {BROTH_INDEX[broth]["name"]} hết nước dùng rồi.')
        _use_pot(d, broth, 1)
        msg = f'🥣 Múc thêm chén nước dùng {BROTH_INDEX[broth]["name"].lower()} nóng (1 phần nồi).'
    t['touches'].append(touch)
    left = [k for k in snap['notes'] if k not in t['touches']]
    return dict(message=msg + (' Khách quen mỉm cười: “Vẫn nhớ hả!”' if not left else ''))


def _who(t: dict) -> str:
    people = kit.eng().NPC_INDEX
    return people[t['npc']].get('display_name') or 'Khách' if t['npc'] in people else 'Khách'


def _returned_line(t: dict, bowl: dict, i: int | None) -> str:
    """What the guest says about a bowl they had to hand back at once."""
    n = _spec(t, i)
    if n['style'] != 'open' and bowl['broth'] != n['broth']:
        text = f'Gọi mì {BROTH_INDEX[n["broth"]]["name"].lower()} mà ra {BROTH_INDEX[bowl["broth"]]["name"].lower()}, phải chờ làm lại.'
    elif (n.get('open') or {}).get('veg'):
        text = 'Đã nói ăn chay mà tô có thịt cá, phải chờ làm lại.'
    elif t['guest']['kind'] == 'kid' and bowl['chili'] > _spice_range(n)[1]:
        text = 'Bé không ăn cay được mà tô cay quá, phải chờ làm lại.'
    else:
        text = 'Tô không đúng món mình gọi, phải chờ làm lại.'
    return f'Tô {i + 1}: {text}' if i is not None else text


def _slip(t: dict, code: str, i: int | None, sev: int, text: str, note: str) -> None:
    if i is None:
        cq.slip(t, code, sev, text, note)
    else:
        cq.slip(t, f'{code}{i}', sev, f'Tô {i + 1}: {text}', f'tô {i + 1}: {note}')


def _record_slips(c: dict, t: dict, bowls: list[dict], rules: dict) -> list[int]:
    """At the hand-off: what the guest finds in the bowl(s) against what they asked.
    Returns the indexes of bowls with a fixable mistake (for a send-back)."""
    n = t['needs']
    group = bool(n.get('party'))
    pampered = rules.get('pamper') == t['id']
    faulty = []
    for i, bowl in enumerate(bowls):
        at = i if group else None
        sp = _spec(t, at)
        before = len(cq.slips(t))
        allergy = sp['allergy']
        if allergy and (any(ITEM_INDEX[k].get('allergen') == allergy for k in bowl['toppings'])
                        or BROTH_INDEX[bowl['broth']].get('allergen') == allergy):
            cq.slip(t, 'allergen', 3, 'Đã dặn dị ứng hải sản mà tô vẫn có đồ biển. May mà mình nhận ra trước khi ăn!',
                    'khách dị ứng hải sản mà tô có đồ biển', safety=True)
        if rules.get('bad_beef') and bowl['toppings'].get('beef'):
            cq.slip(t, 'spoiled', 3, 'Miếng bò có mùi chua mà quán vẫn nấu cho khách. Ăn xong đau bụng cả buổi.',
                    'nấu bò đã có mùi lạ', safety=True)
        low, high = _spice_range(sp)
        got = bowl['chili']
        off = got - high if got > high else low - got if got < low else 0
        if off:
            want = str(high) if low == high else f'{low}–{high}'
            sev = 1 if off == 1 else 2 if off <= 3 else 3
            if got > high:
                _slip(t, 'spice', at, sev, f'Dặn cay cấp {want} mà ra cấp {got}, cay xé lưỡi.', f'cay cấp {got} thay vì {want}')
            else:
                _slip(t, 'spice', at, sev, f'Dặn cay cấp {want} mà chỉ có cấp {got}, ăn nhạt nhẽo.', f'cay cấp {got} thay vì {want}')
        tops = bowl['toppings']
        if sp['style'] == 'open':
            o = sp['open']
            gone = [k for k in o['must'] if not tops.get(k)]
            if gone:
                name = ITEM_INDEX[gone[0]]['name'].lower()
                _slip(t, 'must', at, 2, f'Dặn phải có {name} mà tô không có.', f'thiếu {name}')
            bad = [k for k in o['avoid'] if tops.get(k)]
            if bad:
                name = ITEM_INDEX[bad[0]]['name'].lower()
                _slip(t, 'avoid', at, 2, f'Dặn đừng bỏ {name} mà quán vẫn bỏ vào.', f'có {name} khách dặn tránh')
            if sum(tops.values()) < o['min_tops']:
                _slip(t, 'thin', at, 1, 'Tô lèo tèo vài miếng topping, ăn không bõ.', 'ít topping quá')
        else:
            want = dict(sp['toppings'])
            for item, sub in t['subs'].items():
                if item in want:
                    want[sub] = want.get(sub, 0) + want.pop(item)
            gone = [k for k, q in want.items() if q and not tops.get(k)]
            short = [k for k, q in want.items() if 0 < tops.get(k, 0) < q]
            extra = [k for k, q in tops.items() if q > want.get(k, 0)]
            if gone:
                name = ITEM_INDEX[gone[0]]['name'].lower()
                _slip(t, 'missing', at, 2, f'Gọi {name} mà trong tô không có miếng nào.', f'thiếu {name}')
            elif short:
                k = short[0]
                name = ITEM_INDEX[k]['name'].lower()
                _slip(t, 'short', at, 1, f'Gọi {want[k]} phần {name} mà chỉ có {tops[k]}.', f'thiếu phần {name}')
            if extra and not pampered:
                name = ITEM_INDEX[extra[0]]['name'].lower()
                _slip(t, 'extra', at, 1, f'Không gọi {name} mà tô lại có, phải gắp ra.', f'có {name} không gọi')
            if len(bowl['noodles']) < _wanted_noodles(sp):
                _slip(t, 'noodle', at, 2, 'Gọi thêm vắt mì mà tô chỉ có một vắt.', 'thiếu vắt mì gọi thêm')
        if 'raw' in bowl['noodles']:
            _slip(t, 'raw', at, 1, 'Sợi mì còn sống, cứng như que.', 'mì còn sống')
        elif 'mushy' in bowl['noodles']:
            _slip(t, 'mushy', at, 1, 'Mì nát bấy, ăn như cháo.', 'mì bị nát')
        if n['takeaway'] and bowl['container'] != 'box' and not rules.get('paper'):
            _slip(t, 'container', at, 2, 'Dặn mang về mà lại múc ra tô, phải xin hộp đổ sang.', 'mang về mà múc ra tô')
        elif not n['takeaway'] and bowl['container'] == 'box':
            _slip(t, 'container', at, 1, 'Ngồi ăn tại quán mà lại đưa hộp mang về.', 'ăn tại quán mà đưa hộp')
        # Something the guest can have fixed at the counter (not the noodles' texture: they eat it and grumble).
        if any(not x['code'].startswith(('raw', 'mushy')) for x in cq.slips(t)[before:]):
            faulty.append(i)
    return faulty


def _review_stars(c: dict, t: dict) -> int:
    post = next((f for f in c['feed'] if f.get('source') == t['id'] and f.get('kind') == 'review'), None)
    return post['stars'] if post else 3


def _event_outcome(pl: dict, eid: str, good: bool | None, note: str) -> None:
    for e in pl['events']:
        if e['id'] == eid and e['status'] == 'done':
            e['good'] = good
            e['note'] = note[:300]


def _critic_result(s: dict, c: dict, pl: dict, t: dict) -> str:
    stars = _review_stars(c, t)
    if stars >= 5:
        kit.money(s, c, 20, 'Bài review khen quán', t['id'], category='other_income')
        _event_outcome(pl, 'critic', True, 'Bài review khen tô mì “chuẩn từng sợi”. Quán được thêm khách mới.')
        return '📝 Người viết review chấm 5 sao! Bài viết kéo thêm khách: +20 xu.'
    if stars <= 3:
        _event_outcome(pl, 'critic', False, 'Bài review chê tô mì chưa tới. Hơi buồn.')
        return '📝 Người viết review chưa hài lòng… bài viết sẽ hơi khó nghe.'
    _event_outcome(pl, 'critic', None, 'Bài review khen vừa phải, không có gì nổi bật.')
    return '📝 Người viết review chấm 4 sao, khen vừa phải.'


def _batch(s: dict, c: dict, d: dict, pl: dict) -> dict:
    b = pl['rules'].get('batch')
    kit.need(isinstance(b, dict) and b['status'] == 'open', 'Không có đơn đặt nào đang làm.')
    portions = _portions(pl)
    if d['pots'][b['broth']]:
        _need_pot(d, b['broth'])
    kit.need(d['pots'][b['broth']] >= portions, f'Nồi {BROTH_INDEX[b["broth"]]["name"]} không đủ. Nấu thêm nồi trước nhé.')
    kit.take(c, 'noodle', 1)
    kit.take(c, 'box', 1)
    kit.take(c, 'chili', b['spice'])
    _use_pot(d, b['broth'], portions)
    b['done'] += 1
    if b['done'] < b['goal']:
        return dict(message=f'📦 Đã đóng hộp {b["done"]}/{b["goal"]} cho văn phòng.')
    b['status'] = 'sent'
    pay = b['goal'] * b['pay']
    kit.money(s, c, pay, 'Đơn đặt của văn phòng đầu hẻm', f'batch-{c["day"]}', category='revenue')
    kit.bank(pay)   # the office pays its order by transfer
    kit.metric(c, 'catering_sent')
    _event_outcome(pl, 'catering', True, f'Giao đủ {b["goal"]} hộp cho văn phòng đúng hẹn.')
    FS.flash(pl, 'good', f'📦 Giao đủ {b["goal"]} hộp cho văn phòng · +{pay} xu!')
    return dict(message=f'📦 Đã giao đủ {b["goal"]} hộp cho văn phòng · +{pay} xu.', celebrate=True)


def _score(c: dict, t: dict) -> tuple[int, str]:
    if t['needs']['style'] == 'open':
        return _open_score(c, t)
    return _accuracy(t, _plan_rules(c).get('pamper') == t['id'])


def _plan_rules(c: dict) -> dict:
    p = kit.data(c).get('plan')
    return p['rules'] if isinstance(p, dict) and p.get('day') == c['day'] else {}


def _served_bowls(t: dict) -> list[dict]:
    sv = t.get('served') or {}
    return sv.get('bowls') or [sv.get('bowl') or t['bowl']]


def _accuracy(t: dict, pampered: bool = False) -> tuple[int, str]:
    specs = _specs(t['needs'])
    worst, notes = 5, []
    for i, (sp, bowl) in enumerate(zip(specs, _served_bowls(t))):
        score, note = _bowl_accuracy(t, sp, bowl, pampered)
        worst = min(worst, score)
        if note:
            notes.append(f'tô {i + 1}: {note}' if len(specs) > 1 else note)
    return worst, '; '.join(notes) or 'đúng order'


def _bowl_accuracy(t: dict, n: dict, bowl: dict, pampered: bool) -> tuple[int, str]:
    want = dict(n['toppings'])
    for item, sub in t['subs'].items():
        want[sub] = want.get(sub, 0) + want.pop(item, 0)
    missing = sum(max(0, q - bowl['toppings'].get(k, 0)) for k, q in want.items())
    extra = 0 if pampered else sum(max(0, q - want.get(k, 0)) for k, q in bowl['toppings'].items())
    spice = abs(bowl['chili'] - n['spice'])
    noodles = abs(len(bowl['noodles']) - _wanted_noodles(n))
    score = 5 - missing - (1 if extra else 0) - min(2, spice) - noodles
    notes = []
    if missing:
        notes.append(f'thiếu {missing} phần topping')
    if extra:
        notes.append('có topping không gọi')
    if spice:
        notes.append(f'cay cấp {bowl["chili"]} thay vì {n["spice"]}')
    if noodles:
        notes.append('sai số vắt mì')
    return max(1, score), ', '.join(notes)


def _open_score(c: dict, t: dict) -> tuple[int, str]:
    n, o = t['needs'], t['needs']['open']
    bowl = (t.get('served') or {}).get('bowl') or t['bowl']
    score, notes = 5, []
    low, high = o['spice']
    if not low <= bowl['chili'] <= high:
        score -= min(2, low - bowl['chili'] if bowl['chili'] < low else bowl['chili'] - high)
        notes.append(f'cay cấp {bowl["chili"]}, khách muốn {low}–{high}')
    missing = [k for k in o['must'] if not bowl['toppings'].get(k)]
    if missing:
        score -= len(missing)
        notes.append('thiếu ' + ', '.join(ITEM_INDEX[k]['name'].lower() for k in missing))
    unwanted = [k for k in o['avoid'] if bowl['toppings'].get(k)]
    if unwanted:
        score -= len(unwanted)
        notes.append('có ' + ', '.join(ITEM_INDEX[k]['name'].lower() for k in unwanted) + ' khách không muốn')
    if sum(bowl['toppings'].values()) < o['min_tops']:
        score -= 1
        notes.append(f'ít hơn {o["min_tops"]} phần topping')
    price = (t.get('served') or {}).get('price') or bowl_price(c, bowl)
    if price > o['budget']:
        score -= 1
        notes.append(f'vượt ngân sách ({price}/{o["budget"]} xu)')
    return max(1, score), ', '.join(notes) or 'đúng ý khách'


def feedback(c: dict, t: dict) -> dict:
    bowls = _served_bowls(t)
    n = t['needs']
    rules = _plan_rules(c)
    taste_map = {'perfect': 5, 'soft': 4, 'raw': 2, 'mushy': 2}
    taste = min(taste_map[x] for b in bowls for x in b['noodles'])
    acc, note = _score(c, t)
    patience = t.get('patience', 100)
    speed = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    right_box = all((b['container'] == 'box') == n['takeaway'] for b in bowls) or (rules.get('paper') and not n['takeaway'])
    pres = 5 if right_box else 3
    rows = [dict(key='taste', label='Độ chín sợi mì', score=taste, note={5: 'mì chín tới', 4: 'mì hơi mềm', 2: 'mì sống hoặc nát'}[taste]),
            dict(key='accuracy', label='Đúng ý khách' if n['style'] == 'open' else 'Đúng order', score=acc, note=note),
            dict(key='speed', label='Thời gian chờ', score=speed, note=f'kiên nhẫn còn {patience}%'),
            dict(key='presentation', label='Đóng gói/trình bày', score=pres, note='đúng tô/hộp' if pres == 5 else 'nhầm tô và hộp mang về')]
    if n['style'] == 'open':
        rows.append(dict(key='value', label='Đáng tiền', score=3 if t.get('over_budget') else 5,
                         note=f'khách chỉ trả {t["quoted_price"]} xu theo ngân sách' if t.get('over_budget') else 'vừa túi tiền'))
    if t['refused']:
        rows.append(dict(key='care', label='Cẩn thận', score=2, note='phải trả lại tô một lần'))
    elif t.get('reasked'):
        rows.append(dict(key='care', label='Nhớ khách quen', score=4, note='phải hỏi lại món quen'))
    cap = 5
    kind = t['guest']['kind']
    if kind == 'picky' and (t['mistakes'] or acc < 5):
        cap = 3
    if t.get('vip') == 'critic' and (t['mistakes'] or acc < 5 or taste < 5):
        cap = min(cap, 3)
    if t.get('broth_age', 0) >= 2:
        rows.append(dict(key='broth', label='Nước dùng', score=4, note='nước dùng để 2 đêm, hơi nhạt'))
    snap = t.get('regular') or {}
    if snap.get('notes'):
        forgot = [TOUCHES[k][1].lower() for k in snap['notes'] if k not in t.get('touches', [])]
        rows.append(dict(key='remember', label='Nhớ ý khách', score=4 if forgot else 5,
                         note=('quên: ' + ', '.join(forgot)) if forgot else f'nhớ đủ {len(snap["notes"])} thói quen'))
    d = kit.data(c)
    if _npc_index(t) == 5 and len(d.get('hlog') or []) >= 3:
        g = hygiene_grade(hygiene(d))
        if g != 'B':
            rows.append(dict(key='hygiene', label='Bếp sạch', score=5 if g == 'A' else 3,
                             note='sổ vệ sinh ghi đều từng ngày' if g == 'A' else 'sổ vệ sinh bỏ trống nhiều ngày'))
    if rules.get('bad_beef') and any(b['toppings'].get('beef') for b in bowls):
        rows.append(dict(key='fresh', label='Độ tươi', score=2, note='bò có mùi lạ'))
        cap = min(cap, 2)
    return dict(criteria=rows, cap=cap)


# ------------------------------------------------------------------ surprises
def _stock_all(c: dict, item: str) -> int:
    return kit.stock(c, item)


def _post(s: dict, c: dict, npc: int, text: str) -> None:
    kit.eng().add_feed(s, c, kit.npc_id(ID, npc), text, 'event', None, 'post')


def _ev_wallet(s, c, pl, choice):
    if choice == 'keep':
        pl['rules']['wallet'] = 'kept'
        return 'Bạn cất ví vào ngăn kéo, ghi giờ nhặt được. Chủ ví quay lại sẽ nhận đủ.', True
    if choice == 'group':
        return 'Nhóm khu phố tìm ra chủ ví rất nhanh, nhưng mẹ bé hơi phiền vì ảnh thẻ học sinh bị chia sẻ khắp nơi.', None
    fine = min(20, c['money'])
    if fine:
        kit.money(s, c, -fine, 'Đền tiền ví đưa nhầm người', f'wallet-{c["day"]}', category='compensation')
    return f'Lát sau cô bé chủ ví quay lại. Người kia không phải anh của bé… Quán đền {fine} xu.', False


def _ev_inspection(s, c, pl, choice):
    d = kit.data(c)
    grade = hygiene_grade(hygiene(d))
    if choice == 'show':
        if d['clean_checked_day'] == c['day']:
            pl['rules']['clean_badge'] = True
            kit.metric(c, 'inspections_passed')
            if grade == 'C':
                return 'Sổ hôm nay ghi đủ, bếp sạch. Đoàn dán tem “Bếp sạch” nhưng nhắc: mấy ngày trước sổ còn bỏ trống, giữ đều nhé.', True
            return 'Sổ ghi đủ, bếp sạch. Đoàn dán tem “Bếp sạch” lên cửa, khách nhìn vào thấy yên tâm.', True
        if grade == 'A':
            return 'Hôm nay chưa kịp ghi sổ đầu ca, nhưng sổ 7 ngày qua ghi đều tăm tắp. Đoàn chỉ nhắc nhở, không phạt.', None
        fine = min(30, c['money'])
        if fine:
            kit.money(s, c, -fine, 'Phạt vệ sinh: sổ ca để trống', f'insp-{c["day"]}', category='fine')
        return f'Sổ vệ sinh hôm nay còn trống. Đoàn phạt {fine} xu và dặn kiểm vệ sinh đầu mỗi ca.', False
    if choice == 'tidy':
        _drain_patience(c, 15)
        d['clean_checked_day'] = c['day']
        return 'Bạn lau bếp, ghi sổ ngay trước mặt đoàn. Không bị phạt, nhưng khách chờ lâu hơn một chút.', None
    fine = min(60, c['money'])
    if fine:
        kit.money(s, c, -fine, 'Phạt: đưa phong bì cho đoàn kiểm tra', f'insp-{c["day"]}', category='fine')
    return f'Đoàn trả lại phong bì và lập biên bản. Quán bị phạt {fine} xu, cả xóm biết chuyện.', False


def _ev_bad_beef(s, c, pl, choice):
    n = kit.stock(c, 'beef')
    if choice == 'keep':
        pl['rules']['bad_beef'] = True
        return 'Bạn giữ lô bò lại dùng tiếp. Mong là không ai nhận ra…', False
    if not n:
        return 'Tủ đã hết bò từ trước, không còn gì phải xử lý.', True
    cost = kit.take(c, 'beef', n)
    if choice == 'toss':
        kit.waste(c, 'beef', n, cost, 'Bò có mùi lạ')
        return f'Bạn bỏ {n} phần bò. Đơn nào có bò thì mời khách đổi món khác.', True
    refund = n * ITEM_INDEX['beef']['cost']
    kit.money(s, c, refund, 'Nhà cung cấp hoàn tiền lô bò', f'beef-{c["day"]}', category='refund')
    _drain_patience(c, 10)
    return f'Nhà cung cấp xin lỗi, hoàn {refund} xu. Hôm nay quán tạm hết bò.', True


def _ev_catering(s, c, pl, choice):
    if choice == 'decline':
        return 'Chị trưởng phòng bảo “tiếc ghê, lần sau nhé”. Bếp giữ nhịp như cũ.', None
    goal = 4 if choice == 'all' else 2
    pl['rules']['batch'] = dict(goal=goal, done=0, pay=36, due=pl['served'] + 3, broth='blackbean', spice=2, status='open')
    return f'Đã nhận {goal} hộp tương đen cấp 2. Bấm “Đóng hộp đơn đặt” ở bếp để làm từng hộp, kịp trước khi xong 3 khách nữa.', None


def _ev_critic(s, c, pl, choice):
    if choice == 'ask':
        return 'Vị khách cười trừ, ăn xong lặng lẽ đi. Không có bài review nào cả.', None
    w = FS.spawn_walkin(s, c, ID, 1.0, 'critic')
    target = w or next((t for t in FS.open_tasks(c, ID) if t.get('vip') is None), None)
    if not target:
        pl['rules']['critic_next'] = True
        return 'Vị khách xin chờ gọi món sau. Khách tới lượt tiếp theo chính là bàn góc.', None
    target['vip'] = 'critic'
    pl['rules']['critic'] = target['id']
    if choice == 'pamper':
        pl['rules']['pamper'] = target['id']
        c['active_task'] = target['id']
        target['deferred'] = False
        _drain_patience(c, 10, target['id'])
        return 'Bạn cho tô bàn góc lên trước và thêm topping tùy ý. Vài khách khác bắt đầu nhìn đồng hồ.', None
    return 'Bạn giữ nhịp như mọi ngày. Phiếu của bàn góc có dấu 📝 — làm thật chuẩn nhé.', None


def _ev_noshow(s, c, pl, choice):
    if choice == 'self':
        pl['rules']['dirty'] = 0
        return f'Bạn xắn tay áo. Cứ {DIRTY_MAX} tô ăn tại quán thì nhớ rửa một lượt nhé.', True
    if choice == 'hire':
        kit.money(s, c, -20, 'Thuê người rửa bát thời vụ', f'staff-{c["day"]}', category='staff')
        return 'Bạn thời vụ tới sau 10 phút, bếp chạy êm.', True
    pl['rules']['paper'] = True
    return 'Khách ăn tại quán sẽ dùng hộp giấy. Nhớ để ý số hộp trong kho.', None


def _ev_misdelivered(s, c, pl, choice):
    if choice == 'remake':
        cost = kit.take(c, 'noodle', 1) + kit.take(c, 'box', 1)
        kit.waste(c, 'noodle', 1, cost, 'Giao bù đơn bị giao nhầm')
        _drain_patience(c, 8)
        return 'Hộp mới tới tay khách còn nóng hổi. Khách nhắn: “Quán xử lý có tâm quá!”', True
    if choice == 'refund':
        kit.money(s, c, -35, 'Hoàn tiền đơn bị giao nhầm', f'misdel-{c["day"]}', category='refund')
        return 'Khách nhận lại tiền và lời xin lỗi. Hơi tiếc bữa trưa, nhưng khách vẫn hẹn quay lại.', True
    _post(s, c, 1, 'Đặt mì bị giao nhầm, quán bảo tự đi hỏi tài xế. Thôi khỏi ăn luôn 😮‍💨')
    return 'Khách cúp máy. Tối đó có một bài đăng không vui về quán.', False


def _ev_power(s, c, pl, choice):
    if choice == 'ice':
        kit.money(s, c, -10, 'Mua đá cây giữ lạnh tủ mát', f'power-{c["day"]}', category='other_cost')
        return 'Đá cây giữ tủ mát lạnh tới khi có điện lại. Không hỏng gì.', True
    if choice == 'pause':
        _drain_patience(c, 20)
        return 'Khách ngồi uống trà đá chờ điện. Đồ tươi an toàn, nhưng ai cũng sốt ruột.', None
    lost = 0
    for item in ('beef', 'seafood'):
        n = kit.stock(c, item) // 2
        if n:
            cost = kit.take(c, item, n)
            kit.waste(c, item, n, cost, 'Cúp điện, tủ mát ấm lên')
            lost += n
    if lost:
        return f'Có điện lại sau 20 phút. Bạn phải bỏ {lost} phần đồ tươi bị ấm.', False
    return 'Có điện lại sau 20 phút. May mà tủ không còn đồ tươi.', None


def _complaint_open(s, c, pl):
    done = [t for t in c['tasks'] if t['career'] == ID and t['status'] == 'completed' and t['day'] == c['day'] and t.get('served')]
    last = max(done, key=lambda t: t.get('completed_turn', 0), default=None)
    right = bool(last) and last['mistakes'] == 0 and not last['refused'] and _score(c, last)[0] == 5
    pl['rules']['_complaint'] = right


def _ev_complaint(s, c, pl, choice):
    right = pl['rules'].pop('_complaint', True)
    if choice == 'check':
        _drain_patience(c, 8)
        if right:
            return 'Phiếu order và ảnh tô khớp từng món. Khách gãi đầu: “Chắc tôi nhớ nhầm.”', True
        kit.money(s, c, -min(5, c['money']), 'Phiếu giảm giá xin lỗi khách', f'complaint-{c["day"]}', category='refund')
        return 'Đúng là tô lúc nãy lệch phiếu. Bạn xin lỗi và tặng phiếu giảm 5 xu cho lần sau.', True
    if choice == 'refund':
        kit.money(s, c, -10, 'Hoàn tiền khách phàn nàn', f'complaint-{c["day"]}', category='refund')
        if right:
            return 'Khách vui vẻ nhận tiền. Thật ra tô lúc nãy đúng phiếu, quán mất 10 xu oan.', None
        return 'Khách nhận tiền và lời xin lỗi, không làm to chuyện.', True
    if right:
        return 'Bạn chỉ vào phiếu order. Khách ngượng ngùng bỏ đi, không vui lắm.', None
    _post(s, c, 5, 'Tô mì làm sai mà quán còn cãi. Lần sau chắc không ghé nữa.')
    return 'Tô lúc nãy lệch phiếu thật. Khách bỏ về và đăng bài chê quán “cãi khách”.', False


def _ev_gas(s, c, pl, choice):
    if choice == 'swap':
        kit.money(s, c, -25, 'Đổi bình gas', f'gas-{c["day"]}', category='utilities')
        return 'Bình mới lắp xong, lửa xanh đều trở lại.', True
    pl['rules']['weak_fire'] = True
    return f'Lửa nhỏ: vùng xanh của rổ luộc lùi thêm {WEAK_FIRE} giây tới hết ca.', None


def _ev_students(s, c, pl, choice):
    if choice == 'discount':
        pl['rules']['discount'] = 10
        return 'Bảng “Giảm 10% cho học sinh” được dựng trước cửa. Các bạn reo lên.', None
    extra = 2 if choice == 'share' else 1
    came = sum(1 for _ in range(extra) if FS.spawn_walkin(s, c, ID, 1.0, f'students-{_}'))
    pl['walkins'] += came
    if choice == 'share':
        return f'Bạn gợi ý tô lớn chia chén nhỏ. Thêm {came} phiếu order vào hàng chờ, cả nhóm cười rôm rả.', True
    return f'Các bạn đếm tiền, gọi {came} tô chia nhau. Quán vẫn đủ lời.', None


def _has_noodle_box(s, c, p):
    return None if kit.stock(c, 'noodle') and kit.stock(c, 'box') else 'Hết mì hoặc hộp mang về.'


EVENTS = [
    dict(id='wallet', emoji='👛', title='Ví ai bỏ quên dưới bàn', gentle=True, min_day=1,
         text='Lúc dọn bàn số 3, bạn thấy một chiếc ví vải nhỏ. Trong ví có ít tiền và thẻ học sinh của một bé lớp 6.',
         choices=[dict(id='keep', label='Cất vào ngăn kéo, ghi sổ, chờ chủ quay lại', hint='Không mở thêm, không đưa ai.'),
                  dict(id='group', label='Chụp ảnh thẻ, đăng nhóm khu phố tìm chủ', hint='Nhanh, nhưng lộ thông tin của bé.'),
                  dict(id='give', label='Đưa cho người đứng ngoài bảo là “ví của em tôi”', hint='Người đó trông rất vội.')],
         apply=_ev_wallet),
    dict(id='inspection', emoji='📋', title='Đoàn kiểm tra vệ sinh ghé bất ngờ', min_day=2,
         text='Hai cán bộ phường đeo thẻ bước vào bếp, xin xem sổ vệ sinh ca và tủ mát.',
         choices=[dict(id='show', label='Mở cửa bếp, trình sổ vệ sinh hôm nay', hint='Đã “Kiểm vệ sinh bếp” đầu ca thì yên tâm.'),
                  dict(id='tidy', label='Xin 5 phút lau bếp, ghi sổ rồi mời đoàn vào', hint='Khách đang chờ sẽ sốt ruột.'),
                  dict(id='envelope', label='Kẹp một phong bì vào sổ', hint='Nhanh gọn… nhưng có ổn không?')],
         apply=_ev_inspection),
    dict(id='bad_beef', emoji='🥩', title='Lô bò hôm nay có mùi lạ', min_day=2,
         text='Mở túi bò Mỹ vừa giao, bạn ngửi thấy mùi hơi chua. Màu thịt sẫm hơn mọi ngày.',
         choices=[dict(id='toss', label='Bỏ hết lô bò, ghi vào hao hụt', hint='Đơn có bò thì hỏi khách đổi món.'),
                  dict(id='return', label='Gọi nhà cung cấp lấy lại, đòi hoàn tiền', hint='Được hoàn tiền, nhưng khách chờ lâu hơn.'),
                  dict(id='keep', label='Rửa kỹ rồi dùng tiếp', hint='Tiết kiệm… nếu khách không nhận ra.')],
         apply=_ev_bad_beef),
    dict(id='catering', emoji='📦', title='Văn phòng đầu hẻm đặt mì', min_day=3, not_mods=('quiet',),
         text='Chị trưởng phòng gọi: “Cho chị 4 hộp tương đen cấp 2, xong trong lúc quán làm thêm 3 khách nữa nhé. Mỗi hộp 36 xu.”',
         choices=[dict(id='all', label='Nhận cả 4 hộp', hint='Cần 4 vắt mì, 4 hộp, 8 lượt ớt và nồi tương đen.'),
                  dict(id='half', label='Nhận 2 hộp, hẹn phần còn lại hôm khác', hint='Ít tiền hơn, nhẹ bếp hơn.'),
                  dict(id='decline', label='Từ chối khéo vì bếp đang kín việc', hint='')],
         apply=_ev_catering),
    dict(id='critic', emoji='📝', title='Người ở bàn góc chụp từng món', min_day=3,
         text='Một vị khách đeo máy ảnh nhỏ, ghi chép sau mỗi thìa. Mai thì thầm: “Hình như là người viết review ẩm thực.”',
         choices=[dict(id='normal', label='Phục vụ như mọi khách, làm thật chuẩn', hint='Tô 5 sao sẽ được lên bài khen.'),
                  dict(id='pamper', label='Ưu tiên làm trước, thêm topping tùy ý', hint='Khách khác phải chờ lâu hơn.'),
                  dict(id='ask', label='Ra hỏi thẳng có phải người viết review không', hint='')],
         apply=_ev_critic),
    dict(id='noshow', emoji='🤒', title='Bạn rửa bát báo ốm', min_day=2,
         text='Lộc nhắn: “Em sốt rồi, hôm nay xin nghỉ.” Chồng tô bẩn sẽ cao dần nếu không ai rửa.',
         choices=[dict(id='self', label='Tự rửa tô giữa các đơn', hint=f'Cứ {DIRTY_MAX} tô ăn tại quán thì phải rửa một lượt.'),
                  dict(id='hire', label='Gọi bạn làm thời vụ (20 xu)', hint='Bếp chạy êm như mọi ngày.', cost=20),
                  dict(id='paper', label='Dùng hộp giấy cho khách ăn tại quán', hint='Tốn hộp, khách không chê.')],
         apply=_ev_noshow),
    dict(id='misdelivered', emoji='🛵', title='Hộp mì bị giao nhầm nhà', min_day=3,
         text='Một khách gọi điện: “Tôi đặt mì kim chi mà nhận hộp tương đen của ai đó!” Tài xế đã đi mất.',
         choices=[dict(id='remake', label='Làm lại hộp mới, quán tự giao', hint='Tốn 1 vắt mì, 1 hộp và chút thời gian.', check=_has_noodle_box),
                  dict(id='refund', label='Xin lỗi và hoàn tiền (35 xu)', hint='', cost=35),
                  dict(id='blame', label='Bảo khách tự liên hệ tài xế', hint='Không tốn gì…')],
         apply=_ev_misdelivered),
    dict(id='power_cut', emoji='🔌', title='Cúp điện giữa giờ', min_day=4,
         text='Đèn tắt phụt, tủ mát ngừng chạy. Bếp gas vẫn cháy, nhưng bò và hải sản trong tủ sẽ ấm dần.',
         choices=[dict(id='ice', label='Mua đá cây ướp tủ mát (10 xu)', hint='', cost=10),
                  dict(id='wait', label='Đóng kín tủ, nấu tiếp như thường', hint='Có thể hỏng một phần đồ tươi.'),
                  dict(id='pause', label='Tạm ngưng nhận món, mời khách trà đá chờ', hint='Đồ tươi an toàn, khách chờ lâu.')],
         apply=_ev_power),
    dict(id='complaint', emoji='😤', title='Khách quay lại phàn nàn', min_day=2, on_open=_complaint_open,
         text='Vị khách vừa ăn xong quay lại quầy: “Tô lúc nãy làm không đúng như tôi gọi!”',
         choices=[dict(id='check', label='Xem lại phiếu order và ảnh tô rồi mới trả lời', hint='Khách đang chờ phải đợi thêm chút.'),
                  dict(id='refund', label='Xin lỗi, hoàn 10 xu cho nhanh', hint='', cost=10),
                  dict(id='argue', label='Khẳng định quán làm đúng phiếu', hint='Chắc chắn không?')],
         apply=_ev_complaint),
    dict(id='gas_low', emoji='🔥', title='Bình gas yếu dần', min_day=3,
         text='Ngọn lửa dưới nồi luộc nhỏ lại, nước sôi lăn tăn. Mì sẽ chín chậm hơn.',
         choices=[dict(id='swap', label='Gọi đổi bình gas mới (25 xu)', hint='', cost=25),
                  dict(id='weak', label='Nấu tiếp với lửa nhỏ', hint=f'Mì cần thêm {WEAK_FIRE} giây mới chín tới.')],
         apply=_ev_gas),
    dict(id='student_group', emoji='🎒', title='Nhóm học sinh ùa vào', min_day=2, not_mods=('lunch_rush', 'festival'),
         text='Năm bạn học sinh vừa tan lớp đứng chụm trước quầy: “Tụi con góp tiền, được mấy tô ạ?”',
         choices=[dict(id='share', label='Gợi ý 2 tô lớn, chia chén nhỏ', hint='Thêm khách vào hàng chờ.'),
                  dict(id='discount', label='Giảm 10% cho học sinh cả ngày hôm nay', hint='Mọi đơn còn lại thu ít hơn.'),
                  dict(id='plain', label='Bán đúng giá, mời các bạn ngồi chờ', hint='')],
         apply=_ev_students),
]
EVENT_INDEX = {e['id']: e for e in EVENTS}
RULE_KEYS = {'wallet', 'clean_badge', 'bad_beef', 'batch', 'critic', 'critic_next', 'pamper', 'dirty', 'paper', 'weak_fire',
             'discount', 'beef_gift', '_complaint'}


def on_close(s: dict, c: dict) -> dict:
    _migrate(c)
    pl = _plan(c)
    b = pl['rules'].get('batch')
    if isinstance(b, dict) and b['status'] == 'open':
        b['status'] = 'failed'
        _event_outcome(pl, 'catering', False, 'Hết ca mà chưa đóng đủ hộp cho văn phòng.')
    d = kit.data(c)
    out = FS.close(s, c, ID, pl, MODS)
    # The hygiene book gets today's line, then the pots cool down for the night.
    row = _hygiene_today(c, d)
    d['hlog'] = ar.last([r for r in d['hlog'] if r['day'] != c['day']] + [row], HLOG_DAYS, 'kitchen.health_log', c)
    score = hygiene(d)
    outlook = _outlook(c, d, closing=True)
    pots = _pot_rows(c, d, tomorrow=True)
    for b in BROTH_INDEX:
        d['pot_lots'][b] = [[q, min(99, age + 1)] for q, age in d['pot_lots'][b]]
        d['pot_warm'][b] = False
    out['care'] = dict(hygiene=dict(row=dict(row, points=_points(row)), score=score, grade=hygiene_grade(score)),
                       pots=pots, prep=list(d['prep']), outlook=outlook, keep=KEEP_NIGHTS)
    return out


def public_task(t: dict) -> dict:
    v = copy.deepcopy(t)
    if v.get('gen') != GEN:
        _upgrade_task(v, None)
    v['bowls_total'] = _bowls_total(v)
    if not v['known']:
        v['needs'] = None
    elif v['needs']['style'] == 'usual' and not v.get('recalled'):
        v['needs'] = dict(style='usual', masked=True, takeaway=v['needs']['takeaway'])
    v['boil_windows'] = BOIL
    return v


def public_data(c: dict) -> dict:
    d = copy.deepcopy(kit.data(c))
    pl = _peek_plan(c)
    d.pop('plan', None)
    d.pop('ev_hist', None)
    for k, v in (('notebook', []), ('regulars', {}), ('grades', [])):
        d.setdefault(k, v)
    d['day'] = FS.public_plan(c, pl, MODS, EVENT_INDEX)
    d['rules'] = {k: copy.deepcopy(v) for k, v in pl['rules'].items() if not k.startswith('_')}
    d['portions'] = _portions(pl)
    d['boil_shift'] = WEAK_FIRE if pl['rules'].get('weak_fire') else 0
    d['price_mult'] = _price_mult(pl)
    d['baskets'] = [dict(task=t['id'], start=t['bowl']['boiling']) for t in _boiling(c)]
    raw = kit.data(c)
    view = dict(raw, pot_lots={b: raw.get('pot_lots', {}).get(b) or [] for b in BROTH_INDEX},
                pot_warm={b: raw.get('pot_warm', {}).get(b, True) for b in BROTH_INDEX},
                prep=list(raw.get('prep') or []), guests=raw.get('guests') or {}, hlog=raw.get('hlog') or [])
    d.pop('guests', None)
    d['care'] = dict(pots=_pot_rows(c, view), hygiene=_hygiene_public(c, view), prep=view['prep'], prep_max=PREP_MAX,
                     prep_packs=PREP_PACKS, keep=KEEP_NIGHTS, outlook=_outlook(c, view), book=_book(c, view),
                     bond_max=BOND_MAX, bond_tip=BOND_TIP, bond_tip_at=BOND_TIP_AT)
    return d


def _valid_bowl(bowl) -> None:
    kit.need(isinstance(bowl, dict) and set(_empty_bowl()) <= set(bowl), 'Tô mì thiếu dữ liệu.')
    kit.need(bowl['container'] in (None, 'bowl', 'box') and bowl['broth'] in (None, *BROTH_INDEX), 'Tô mì sai.')
    kit.need(isinstance(bowl['noodles'], list) and len(bowl['noodles']) <= 2 and all(x in ('raw', 'perfect', 'soft', 'mushy') for x in bowl['noodles']), 'Mì trong tô sai.')
    kit.need(bowl['boiling'] is None or (isinstance(bowl['boiling'], (int, float)) and 0 <= bowl['boiling'] < 10**11), 'Rổ luộc sai.')
    kit.need(isinstance(bowl['toppings'], dict) and all(k in TOPPINGS for k in bowl['toppings']), 'Topping sai.')
    for q in bowl['toppings'].values():
        kit.integer(q, 1, 8)
    kit.integer(bowl['chili'], 0, 10)
    kit.integer(bowl['cost'], 0, 10000)
    kit.need(type(bowl['lid']) is bool, 'Nắp hộp sai.')


def validate_task(t: dict, original: dict) -> None:
    _valid_bowl(t['bowl'])
    kit.need(t.get('gen') == GEN, 'Phiên bản phiếu order không hợp lệ.')
    total = _bowls_total(t)
    kit.need(isinstance(t.get('plates'), list) and len(t['plates']) == total, 'Khay tô không hợp lệ.')
    kit.integer(t.get('cur'), 0, total - 1)
    for x in t['plates']:
        if x is not None:
            _valid_bowl(x)
            kit.need(x['boiling'] is None, 'Tô trên khay còn đang luộc.')
    kit.integer(t['refused'], 0, 1000)
    kit.need(t['quoted_price'] is None or 1 <= kit.integer(t['quoted_price'], 1, 2000), 'Giá sai.')
    kit.need(isinstance(t['subs'], dict) and all(k in TOPPINGS and v in TOPPINGS for k, v in t['subs'].items()), 'Món thay sai.')
    for k in ('recalled', 'reasked', 'over_budget'):
        kit.need(type(t.get(k)) is bool, 'Trạng thái đơn không hợp lệ.')
    kit.need(t.get('vip') in (None, 'critic'), 'Khách đặc biệt không hợp lệ.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Câu chuyện khách quen không hợp lệ.')
    reg = t.get('regular')
    if reg is not None:
        kit.need(isinstance(reg, dict) and set(reg) == {'bond', 'notes'}, 'Thẻ khách quen không hợp lệ.')
        kit.integer(reg['bond'], 0, BOND_MAX)
        habits = [h[0] for h in HABITS.get(_npc_index(t), ())]
        kit.need(isinstance(reg['notes'], list) and 1 <= len(reg['notes']) <= len(habits) and reg['notes'] == habits[:len(reg['notes'])],
                 'Thói quen khách quen không hợp lệ.')
    touches = t.get('touches', [])
    kit.need(isinstance(touches, list) and len(touches) == len(set(touches)) and all(k in ((reg or {}).get('notes') or []) for k in touches),
             'Việc chăm khách quen không hợp lệ.')
    kit.integer(t.get('broth_age', 0), 0, KEEP_NIGHTS)


def validate_data(c: dict) -> None:
    d = _migrate(c)
    kit.need(isinstance(d.get('pots'), dict) and set(d['pots']) == set(BROTH_INDEX), 'Nồi nước dùng sai.')
    for v in d['pots'].values():
        kit.integer(v, 0, POT_MAX)
    for k in ('bowls_served', 'dumped', 'clean_checked_day'):
        kit.integer(d.get(k), 0, 10**9)
    kit.need(isinstance(d['notebook'], list) and len(d['notebook']) <= 20 and all(isinstance(x, str) and x.startswith(ID + '_npc_') for x in d['notebook']), 'Sổ khách quen không hợp lệ.')
    m = d.get('pot_warm')
    kit.need(isinstance(m, dict) and set(m) == set(BROTH_INDEX) and all(type(v) is bool for v in m.values()), 'Tình trạng nồi nước dùng sai.')
    m = d.get('pot_lots')
    kit.need(isinstance(m, dict) and set(m) == set(BROTH_INDEX), 'Mẻ nước dùng trong nồi sai.')
    for b, lots in m.items():
        kit.need(isinstance(lots, list) and len(lots) <= 8 and all(isinstance(x, list) and len(x) == 2 for x in lots), 'Mẻ nước dùng trong nồi sai.')
        for q, age in lots:
            kit.integer(q, 1, POT_MAX)
            kit.integer(age, 0, 99)
        ages = [age for _, age in lots]
        kit.need(ages == sorted(set(ages), reverse=True) and sum(q for q, _ in lots) == d['pots'][b], 'Mẻ nước dùng trong nồi sai.')
    kit.need(isinstance(d['prep'], list) and len(d['prep']) <= PREP_MAX and len(set(d['prep'])) == len(d['prep'])
             and all(b in BROTH_INDEX for b in d['prep']), 'Nồi hầm sẵn không hợp lệ.')
    g = d['guests']
    kit.need(isinstance(g, dict) and len(g) <= len(GUEST_IDS) and set(g) <= set(GUEST_IDS), 'Sổ khách quen không hợp lệ.')
    for v in g.values():
        kit.need(isinstance(v, dict) and set(v) == {'visits', 'bond'}, 'Sổ khách quen không hợp lệ.')
        kit.integer(v['visits'], 0, 999)
        kit.integer(v['bond'], 0, BOND_MAX)
    kit.need(isinstance(d['hlog'], list) and len(d['hlog']) <= HLOG_DAYS, 'Sổ vệ sinh không hợp lệ.')
    for r in d['hlog']:
        kit.need(isinstance(r, dict) and set(r) == {'day', 'clean', 'dishes', 'pots'}
                 and all(type(r[k]) is bool for k in ('clean', 'dishes', 'pots')), 'Sổ vệ sinh không hợp lệ.')
        kit.integer(r['day'], 0, max(1, c['day']))
    FS.validate(c, MODS, EVENT_INDEX)
    p = d.get('plan')
    if p is not None:
        kit.need(set(p['rules']) <= RULE_KEYS, 'Luật trong ngày không hợp lệ.')
        b = p['rules'].get('batch')
        if b is not None:
            kit.need(isinstance(b, dict) and b.get('status') in ('open', 'sent', 'failed') and b.get('broth') in BROTH_INDEX, 'Đơn đặt không hợp lệ.')
            kit.integer(b.get('goal'), 1, 6)
            kit.integer(b.get('done'), 0, b['goal'])
            for k in ('pay', 'due', 'spice'):
                kit.integer(b.get(k), 0, 1000)
        kit.integer(p['rules'].get('dirty', 0), 0, 50)


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = kit.data(c)
    if e['role'] == 'prep':
        warm = _reheat(d)
        if warm:
            return 'Đã đun sôi lại nồi ' + ', '.join(BROTH_INDEX[b]['name'] for b in warm) + ' để qua đêm.'
        low = next((b for b in BROTHS if b['unlock'] <= kit.level(c) and d['pots'][b['id']] <= 2 and kit.stock(c, b['pack'])
                    and _pot_state(d, b['id']) != 'stale'), None)
        if low:
            kit.take(c, low['pack'], 1)
            _cook(d, low['id'], POT_BATCH)
            return f'Đã nấu thêm nồi {low["name"]} từ gói nước dùng trong kho.'
        return 'Đã sơ chế rau, xếp topping theo ngày nhập (vào trước dùng trước).'
    if not t or t['career'] != ID or not t['known']:
        return None
    if e['role'] == 'server' and t['bowl']['container'] is None and t['plates'][t['cur']] is None:
        kind = 'box' if t['needs']['takeaway'] else 'bowl'
        if kind == 'box' and not kit.stock(c, 'box'):
            return None
        if kind == 'bowl' and _plan_rules(c).get('dirty', 0) >= DIRTY_MAX:
            return None
        if kind == 'box':
            t['bowl']['cost'] += kit.take(c, 'box', 1)
        t['bowl']['container'] = kind
        return 'Đã chuẩn bị ' + ('hộp mang về' if kind == 'box' else 'tô') + ' đúng kiểu cho order đang làm.'
    if e['role'] == 'dish':
        rules = _plan_rules(c)
        if rules.get('dirty'):
            rules['dirty'] = 0
        return 'Đã rửa tô, lau bàn và thay nước rửa.'
    return None


def hint(c: dict, t: dict) -> str:
    style = (t.get('needs') or {}).get('style')
    if style == 'group':
        return 'Bàn nhiều tô: làm từng tô theo thẻ Tô 1, Tô 2… → bấm “Xong tô” để đặt lên khay → đủ tô thì giao một lượt.'
    if style == 'usual':
        return 'Món quen: mở sổ khách quen (hoặc hỏi lại) → nấu đúng như mọi khi → giao.'
    if style == 'open':
        return 'Tô tùy quán: chọn nước dùng hợp ý, đủ topping khách muốn, cay trong khoảng, giữ giá trong ngân sách.'
    return 'Tô/hộp → thả mì (vớt trong vùng xanh) → chan đúng nước dùng → topping theo phiếu → bơm ớt đúng cấp → đậy nắp nếu mang về → giao.'


def content() -> dict:
    return dict(broths=BROTHS, toppings=TOPPINGS, boil=BOIL, weak_fire=WEAK_FIRE, pot_max=POT_MAX, pot_batch=POT_BATCH,
                dirty_max=DIRTY_MAX, meat=list(MEAT), prices=SPEC['prices'], keep_nights=KEEP_NIGHTS,
                touches={k: dict(emoji=e, label=label) for k, (e, label) in TOUCHES.items()},
                items=[dict(id=i['id'], name=i['name'], emoji=i['emoji'], price=i.get('price', 0), unlock=i.get('unlock', 1),
                            allergen=i.get('allergen')) for i in ITEMS if i['group'] == 'topping'])


SITUATIONS = [
    dict(id='RS-S01', title='Sợi tóc trong tô mì', npc=5, tone='tense', min_day=1,
         opening='Bà Hoa gọi to: “Trong tô có sợi tóc! Quán ăn uống kiểu gì vậy?” Cả quán quay lại nhìn.',
         swap='Bạn là khách lớn tuổi, rất kỹ vệ sinh, vừa thấy một sợi tóc trong tô.',
         facts=[dict(id='hair', title='Nhìn sợi tóc', source='Tô mì', text='Sợi tóc dài, màu bạc — tóc của nhân viên bếp hôm nay đều ngắn và đội mũ trùm.'),
                dict(id='camera', title='Camera bếp', source='Camera', text='Camera cho thấy bếp đội mũ trùm suốt ca; tô được đậy khi mang ra.'),
                dict(id='others', title='Khách bàn bên', source='Anh Quân', text='Anh Quân nói nhỏ: “Lúc nãy bà xõa tóc chải ngay trên bàn.”')],
         options=[dict(id='remake', label='Xin lỗi vì trải nghiệm không vui, làm tô mới ngay, không tranh cãi', cost=12, quality='good', stars=4,
                       review='Quán xử lý nhanh, làm tô mới không một lời cãi. Được.',
                       outcome='Bà Hoa ăn tô mới, lúc về còn dặn “lần sau vẫn ghé”. Không ai trong quán phải nghe cãi vã.',
                       perspectives=[dict(who='Bà Hoa', emoji='👵', text='Có khi đúng là tóc tôi thật… nhưng quán không làm tôi mất mặt.'),
                                     dict(who='Nhân viên bếp', emoji='🧑‍🍳', text='Tụi em đội mũ cả ca, hơi tủi. Nhưng chủ quán tin tụi em, vậy là đủ.'),
                                     dict(who='Khách bàn bên', emoji='👀', text='Quán xử lý êm, mình thấy yên tâm ăn tiếp.')]),
                  dict(id='prove', label='Cho bà xem camera, nói rõ tóc không phải của bếp', requires=['hair', 'camera'], quality='ok', stars=3,
                       review='Quán đúng là có camera, nhưng nói chuyện với người lớn tuổi như vậy thì tôi không thích.',
                       outcome='Bà Hoa im lặng, trả tiền rồi đi. Chuyện đúng sai rõ ràng nhưng không ai vui.',
                       perspectives=[dict(who='Bà Hoa', emoji='😤', text='Đúng là tóc tôi, nhưng bị chỉ ra trước cả quán thì ngượng lắm.'),
                                     dict(who='Anh Quân', emoji='🤐', text='Quán đúng, nhưng giá như nói riêng.')]),
                  dict(id='private', label='Mời bà ra bàn riêng, làm tô mới, sau đó nhẹ nhàng nói về camera', requires=['camera', 'others'], cost=12, quality='good', stars=5,
                       review='Chủ quán tế nhị, làm tô mới rồi mới nói chuyện riêng với tôi. Tôi phục.',
                       outcome='Bà Hoa cười xòa: “Chắc tóc tôi thật.” Bà giới thiệu quán cho hội dưỡng sinh.',
                       perspectives=[dict(who='Bà Hoa', emoji='😊', text='Được nói riêng, tôi thấy mình được tôn trọng.'),
                                     dict(who='Nhân viên bếp', emoji='🧑‍🍳', text='Camera bảo vệ tụi em mà không cần làm khách xấu hổ.')]),
                  dict(id='deny', label='Nói lớn: “Quán tôi không bao giờ có tóc!”', quality='bad', stars=1,
                       review='Chủ quán quát khách. Không bao giờ quay lại.',
                       outcome='Bà Hoa bỏ về. Tối đó có review 1 sao và vài bình luận hùa theo.',
                       perspectives=[dict(who='Khách bàn bên', emoji='😬', text='Dù đúng thì cách nói đó làm cả quán mất vui.')])],
         lesson='Giải quyết cảm xúc trước, dữ kiện sau — và nói dữ kiện ở nơi riêng tư.'),
    dict(id='RS-S02', title='Khách hỏi món có tôm không', npc=5, tone='tense', min_day=2,
         opening='Bà Hoa hỏi: “Nước tomyum có tôm không cháu? Bà dị ứng đồ biển.”',
         facts=[dict(id='recipe', title='Công thức gốc', source='Thẻ công thức', text='Gói tomyum có bột tôm và nước mắm cá.'),
                dict(id='supplier', title='Nhãn nhà cung cấp', source='Bao bì', text='Nhãn ghi: “Có thể chứa giáp xác”.')],
         options=[dict(id='truth', label='Nói thật có thành phần hải sản, gợi ý nước kim chi hoặc tương đen', requires=['recipe'], quality='good', stars=5,
                       review='Quán biết rõ thành phần món, tôi yên tâm.',
                       outcome='Bà Hoa đổi sang tương đen và cảm ơn vì được nói rõ.',
                       perspectives=[dict(who='Bà Hoa', emoji='🙏', text='Hỏi nhiều quán họ cứ bảo “không sao đâu”, ở đây thì khác.'),
                                     dict(who='Bếp', emoji='📋', text='Thẻ công thức dán cạnh nồi chính là để trả lời những câu này.')]),
                  dict(id='guess', label='“Chắc không có đâu bà, ít thôi mà”', quality='bad', stars=1,
                       review='Hỏi kỹ rồi mà quán vẫn nói bừa. Nguy hiểm!',
                       outcome='May mà bà Hoa đọc được nhãn trên kệ nên không ăn. Bà rất giận.',
                       perspectives=[dict(who='Bà Hoa', emoji='😠', text='Với người dị ứng, “ít thôi” là chuyện sống chết.')])],
         lesson='Với dị ứng: không đoán — đọc công thức, đọc nhãn, nói thật.'),
    dict(id='RS-S03', title='Đoàn 10 người tới không báo trước', npc=4, tone='tense', min_day=2,
         opening='Minh Béo dẫn cả đội bóng 10 người tới lúc 12 giờ: “Cho tụi em 10 tô, nhanh nha!”',
         facts=[dict(id='capacity', title='Sức bếp', source='Bếp', text='Bếp có 2 rổ luộc, mỗi tô cần ~12 giây luộc + chan + topping.'),
                dict(id='stock', title='Kho', source='Kho', text='Mì tươi đủ cho khoảng 12 tô; bò Mỹ chỉ còn 4 phần.'),
                dict(id='queue', title='Khách đang chờ', source='Quầy', text='Đang có 3 khách lẻ chờ trước.')],
         options=[dict(id='plan', label='Báo thời gian chờ thật, mời gọi món chung ít lựa chọn, phục vụ khách lẻ trước', requires=['capacity', 'queue'], quality='good', stars=5,
                       review='Quán nói thật phải chờ 25 phút, gợi ý món để làm nhanh. Chuyên nghiệp!',
                       outcome='Đội bóng gọi 2 loại mì cho nhanh, uống trà đá chờ. Khách lẻ không bị bỏ quên.',
                       perspectives=[dict(who='Minh Béo', emoji='⚽', text='Biết chờ bao lâu thì tụi em chờ được.'),
                                     dict(who='Khách lẻ', emoji='🧍', text='Tôi tới trước, quán vẫn giữ lượt cho tôi.')]),
                  dict(id='all', label='Nhận hết, ai gọi gì làm nấy', quality='bad', stars=2,
                       review='Chờ 50 phút, bò Mỹ hết giữa chừng, lộn xộn quá.',
                       outcome='Bếp rối, hết bò Mỹ, ba khách lẻ bỏ về.',
                       perspectives=[dict(who='Phụ bếp', emoji='😵', text='Mười order khác nhau cùng lúc, em không nhớ nổi.')]),
                  dict(id='refuse', label='Từ chối vì bếp không kịp', quality='ok',
                       outcome='Đội bóng sang quán khác. Bếp nhẹ nhưng quán mất một đơn lớn.',
                       perspectives=[dict(who='Minh Béo', emoji='😕', text='Tiếc ghê, tụi em thích quán này.')])],
         lesson='Nói thật về thời gian chờ và giữ công bằng cho người đến trước.'),
    dict(id='RS-S04', title='Khách chê cay dù gọi cấp 7', npc=0, tone='gentle', min_day=3,
         opening='Anh Sơn uống hết ly nước thứ ba: “Cay quá! Quán cho ớt kiểu gì vậy?”',
         facts=[dict(id='ticket', title='Phiếu order', source='Máy order', text='Phiếu ghi: “cấp 6 — tự chọn”.'),
                dict(id='pump', title='Nhật ký bếp', source='Bếp', text='Bếp bơm đúng 6 lượt sốt ớt.')],
         options=[dict(id='care', label='Mang thêm nước lạnh, sữa chua giải cay, đùa vui về “thử thách cấp 6”', requires=['ticket'], cost=4, quality='good', stars=5,
                       review='Cay xé lưỡi nhưng quán mang sữa chua giải cay, dễ thương. Lần sau cấp 4 thôi 😂',
                       outcome='Anh Sơn cười chảy nước mắt, chụp ảnh check-in “sống sót cấp 6”.',
                       perspectives=[dict(who='Anh Sơn', emoji='🥵', text='Tự gọi mà, nhưng được chăm vậy thì vui.'),
                                     dict(who='Bếp', emoji='🌶️', text='Bơm đúng 6 lượt, có nhật ký hẳn hoi.')]),
                  dict(id='blame', label='“Anh tự gọi cấp 6 mà”', requires=['ticket'], quality='ok', stars=3,
                       review='Ừ thì tôi gọi, nhưng nói kiểu đó mất vui.',
                       outcome='Anh Sơn không cãi được nhưng không vui.',
                       perspectives=[dict(who='Anh Sơn', emoji='😑', text='Đúng, nhưng không cần nói vậy.')])],
         lesson='Khách đúng hay sai không quan trọng bằng việc họ rời quán với cảm giác được quan tâm.'),
    dict(id='RS-S05', title='Tài xế đến lấy đơn online quá sớm', npc=6, tone='gentle', min_day=1,
         opening='Anh Quân (tài xế) tới lấy đơn online: “Đơn của khách xong chưa? App báo tôi trễ rồi.”',
         facts=[dict(id='app', title='Ứng dụng', source='Máy tính bảng', text='Đơn mới nhận 2 phút trước, ước tính cần 6 phút.'),
                dict(id='driver', title='Tài xế', source='Anh Quân', text='Anh Quân còn một cuốc chờ sau đơn này.')],
         options=[dict(id='water', label='Mời ngồi uống nước, báo thời gian chính xác, làm đơn đó trước nếu kịp', requires=['app'], quality='good',
                       outcome='Anh Quân chờ 5 phút, đơn đi kèm tem niêm phong đầy đủ.',
                       perspectives=[dict(who='Anh Quân', emoji='🛵', text='Có chỗ ngồi và biết giờ chính xác là tôi đỡ sốt ruột.'),
                                     dict(who='Khách online', emoji='📱', text='Nhận mì còn nóng, nắp dán kín.')]),
                  dict(id='rush', label='Làm vội cho kịp', quality='bad',
                       outcome='Mì chưa chín tới, quên đậy nắp chắc; khách online nhận hộp bị đổ.',
                       perspectives=[dict(who='Khách online', emoji='😖', text='Mì đổ lênh láng trong túi.')])],
         lesson='Nhanh mà ẩu sẽ chậm hơn: báo thời gian thật và giữ chất lượng.'),
    dict(id='RS-S06', title='Kiểm tra vệ sinh an toàn thực phẩm', npc=3, tone='tense', min_day=4,
         opening='Đoàn kiểm tra vệ sinh an toàn thực phẩm của phường ghé bất ngờ.',
         facts=[dict(id='log', title='Sổ vệ sinh', source='Sổ bếp', text='Sổ vệ sinh ghi đủ các ca gần đây nếu bạn bấm “Kiểm vệ sinh” mỗi ngày.'),
                dict(id='fridge', title='Tủ lạnh', source='Kho', text='Có một lô topping để quá hạn trong tủ nếu chưa bỏ.'),
                dict(id='papers', title='Giấy tờ', source='Tủ hồ sơ', text='Giấy khám sức khỏe của nhân viên còn hạn.')],
         options=[dict(id='open', label='Mở cửa bếp, trình sổ, tự chỉ ra lô quá hạn và bỏ ngay', requires=['log', 'fridge'], quality='good',
                       outcome='Đoàn ghi nhận quán tự giác, nhắc nhở và không lập biên bản.',
                       perspectives=[dict(who='Cán bộ kiểm tra', emoji='📋', text='Tự phát hiện và xử lý cho thấy quán có quy trình.'),
                                     dict(who='Nhân viên', emoji='🧑‍🍳', text='May mà mình ghi sổ đều.')]),
                  dict(id='hide', label='Giấu lô quá hạn vào thùng xe', quality='bad', cost=40,
                       outcome='Đoàn phát hiện, lập biên bản nhắc nhở và phạt hành chính.',
                       perspectives=[dict(who='Cán bộ kiểm tra', emoji='🧐', text='Giấu diếm nghiêm trọng hơn nhiều so với một lô quá hạn.')])],
         lesson='Minh bạch và có sổ sách là cách tốt nhất để đi qua kiểm tra.'),
]

SPEC = dict(
    id=ID, prefix='rs_', category='food',
    meta=dict(short='Quán mì cay', place='Quán Mì Cay Mây', tagline='Nồi nước dùng sôi. Tô mì đúng cấp độ cay.', icon='bowl',
              color='#d9573b', light='#fff0e6', weather='Trời se lạnh', work='Order', station='Bếp mì',
              greeting='Đọc phiếu order, thả mì, chan nước dùng, thêm topping rồi bơm ớt đúng cấp. Mỗi ngày quán một khác, để ý bảng “Hôm nay” nhé.',
              caption='Một tô mì nóng, một câu chuyện nhỏ', map_label='08 · QUÁN MÌ CAY MÂY'),
    people=PEOPLE,
    staff=[('Tú', 'prep', 'Nấu nồi nước dùng rất đều tay.', 76, 88), ('Mai', 'server', 'Nhớ khách nào mang về, khách nào ăn tại quán.', 84, 80),
           ('Lộc', 'dish', 'Rửa bát nhanh, bếp luôn sạch.', 80, 85), ('Hiền', 'prep', 'Sơ chế cẩn thận, nhớ hạn dùng.', 70, 93)],
    roles={'prep': 'Phụ bếp', 'server': 'Chạy bàn', 'dish': 'Rửa bát'},
    inventory=dict(items=ITEMS, capacity=40),
    prices={'kimchi': 35, 'tomyum': 40, 'blackbean': 35, 'cheese': 45},
    tip=3,
    physical=PHYSICAL,
    wait=True,  # the queue drains in handle (food_service.patience_tick → kit.wait_tick), not the engine's flat -1
    free_actions=(),
    no_tick=('rs_lid', 'rs_chili', 'rs_drain', 'rs_recall', 'rs_tab', 'rs_touch'),
    waste_items=('bowl',),
    activity=('🍜', 'Bếp mì gọn gàng', [('Bò Mỹ', 'Tủ mát'), ('Gói tương đen', 'Kệ khô'), ('Trứng', 'Tủ mát'), ('Hộp mang về', 'Kệ khô')],
              ['Đọc phiếu order', 'Luộc mì chín tới', 'Chan nước dùng và topping', 'Bơm ớt, đậy nắp, giao']),
    stories=[('Công thức tương đen của cô Tư', ('Cô Tư kể ngày xưa cô nấu tương đen bằng tương tự ủ. Cô muốn nếm thử nồi của quán.',
                                                 'Bạn nấu một nồi mới và mời cô nếm sau ca. Cô góp ý bớt ngọt một chút.',
                                                 'Quán thêm dòng “Tương đen kiểu cô Tư” vào thực đơn thử nghiệm.')),
             ('Anh Quân và cuốc xe trễ', ('Anh Quân hay bị app phạt vì đơn ra chậm. Anh hỏi quán có cách nào báo trước không.',
                                          'Bạn thử ghi thời gian dự kiến lên phiếu mang về cho từng đơn.',
                                          'Anh Quân gửi quán một tấm thiệp: “Cảm ơn vì giờ báo luôn đúng.”')),
             ('Bé Na và cấp độ 0', ('Bé Na thích mì nhưng sợ cay. Bé hỏi có món nào “cay mà không cay” không.',
                                    'Bạn thử làm một tô phô mai cấp 0 với chút tiêu thay ớt.',
                                    'Bé Na vẽ tặng quán một tô mì mặt cười treo cạnh quầy.'))],
    review_asides=['Mì chín tới, ăn tới sợi cuối vẫn dai 😋', 'Cay đúng cấp mình chọn, không hơn không kém.', 'Nước dùng đậm, húp tới giọt cuối.', 'Lần sau sẽ thử thách cấp cao hơn!'],
    situations=SITUATIONS,
    guide='Tô/hộp → thả mì → chan nước dùng → topping → sốt ớt → nắp (mang về) → giao. Món quen: tra sổ. Tô tùy quán: đúng ý, đúng ngân sách. Bàn nhiều tô: xong từng tô rồi giao một lượt.',
)
