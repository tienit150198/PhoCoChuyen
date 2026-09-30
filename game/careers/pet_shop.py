"""Tiệm Thú Nhỏ Chú Út (pet_shop): the pet shop on the street, next door to Pet Care Mèo Mập.

Chú Út ran this shop for thirty years the old way ("khách hỏi gì bán nấy"). His niece Nhã,
a third-year vet student, now runs it after class and wants it done right: healthy animals,
honest advice, and kittens and puppies only through the adoption corner that Nhóm cứu hộ
Chân Nhỏ runs in the shop. You are the new hand at the counter.

Seven kinds of work (t['job']):

* food    advise dry food by species, age, size and allergy; check the dates on what the
          customer grabbed from the old discount basket.
* tank    set up a fish tank: litres per fish, a filter, water conditioner, fish that get
          along (a betta alone, no fin-nippers with long fins, no goldfish with tropicals).
* screen  sell a small animal or hand over an adoptee: ask first, then sell, ask them to come
          back later (with a parent, after asking the landlord…) or say no kindly.
* care    the shop's own animals: feed the right portion, clean the right way, read the water
          temperature and fix the heater, find the sick one and move it to quarantine.
* ret     returns: receipt, seal, batch, date and defect decide refund, exchange or no.
* lost    the lost-pet board: write the notice (keep one secret mark off it), pin it, then
          sort the calls: the real one, a different animal, and the "chuyển tiền trước" scam.
* ship    heavy orders by a shipper: confirm the address, pack the order, pick bike or van,
          type the COD amount.

Every sale goes through a real till: the player scans each product (t['bill']) against what
is on the counter (t['cart']), locks the total, takes the customer's notes and counts the
change from real denominations (game/careers/till.py). A wrong total or wrong change is never
fixed silently: a careful customer catches it at the counter, anyone else finds it at home.
Mistakes are recorded with consequences.slip (welfare and safety ones with safety=True) and
settled by consequences.react, which scales the customer's reaction and the reviews.

Everything a task needs is decided by make_task(day, slot) (seeded); state lives in the task
and in c['ext']['data'] (animals, pens, the story book, the shop's stage).
"""
from __future__ import annotations

import copy

from .. import consequences as cq
from . import kit, till

ID = 'pet_shop'
VET = 'Phòng khám Thú y Cỏ May'
SPA = 'Pet Care Mèo Mập'
RESCUE = 'Nhóm cứu hộ Chân Nhỏ'
SHOP = 'Tiệm Thú Nhỏ Chú Út'
V = 1
# A welfare or safety mistake brings a visit from the ward's vet the next day (chain incident).
INSPECT = 'slip_welfare_inspect'
cq.INSPECTION.setdefault(ID, INSPECT)

# ---------------------------------------------------------------- the shelves
ITEMS = [
    # thức ăn khô (life: game days)
    dict(id='dog_puppy', name='Hạt cún con (vị gà)', emoji='🐶', group='Thức ăn chó', unit='túi 1,5 kg', cost=28, price=45, life=30, start=5),
    dict(id='dog_adult', name='Hạt chó trưởng thành (vị gà)', emoji='🍗', group='Thức ăn chó', unit='túi 3 kg', cost=26, price=42, life=30, start=5),
    dict(id='dog_large', name='Hạt chó giống lớn (vị bò)', emoji='🐕', group='Thức ăn chó', unit='bao 5 kg', cost=60, price=95, life=40, start=3),
    dict(id='dog_lamb', name='Hạt chó không gà (vị cừu)', emoji='🐑', group='Thức ăn chó', unit='túi 3 kg', cost=38, price=60, life=40, start=4),
    dict(id='cat_kitten', name='Hạt mèo con', emoji='🐱', group='Thức ăn mèo', unit='túi 1,5 kg', cost=25, price=40, life=30, start=5),
    dict(id='cat_adult', name='Hạt mèo trưởng thành (vị cá)', emoji='🐟', group='Thức ăn mèo', unit='túi 2 kg', cost=22, price=36, life=30, start=5),
    dict(id='cat_senior', name='Hạt mèo lớn tuổi 7+', emoji='👵', group='Thức ăn mèo', unit='túi 1,5 kg', cost=30, price=48, life=30, start=3),
    dict(id='cat_sensitive', name='Hạt mèo không cá (gà tây)', emoji='🦃', group='Thức ăn mèo', unit='túi 1,5 kg', cost=32, price=52, life=30, start=3),
    dict(id='pate_cat', name='Pate mèo (lon)', emoji='🥫', group='Pate', unit='lon', cost=5, price=9, life=20, start=12),
    dict(id='pate_dog', name='Pate chó (lon)', emoji='🥫', group='Pate', unit='lon', cost=6, price=10, life=20, start=10),
    dict(id='fish_food', name='Cám cá nhiệt đới', emoji='🐠', group='Thức ăn cá, chim, hamster', unit='hộp', cost=7, price=12, life=60, start=8),
    dict(id='goldfish_food', name='Cám cá vàng', emoji='🐡', group='Thức ăn cá, chim, hamster', unit='hộp', cost=7, price=12, life=60, start=6),
    dict(id='bird_seed', name='Hạt kê cho chim', emoji='🌾', group='Thức ăn cá, chim, hamster', unit='túi', cost=8, price=15, life=45, start=6),
    dict(id='hamster_food', name='Thức ăn hamster', emoji='🌰', group='Thức ăn cá, chim, hamster', unit='túi', cost=8, price=15, life=45, start=6),
    # đồ dùng
    dict(id='litter', name='Cát vệ sinh mèo', emoji='🪣', group='Đồ dùng', unit='bao 8 kg', cost=18, price=30, start=6),
    dict(id='leash', name='Dây dắt', emoji='🦮', group='Đồ dùng', unit='sợi', cost=14, price=25, start=6),
    dict(id='collar', name='Vòng cổ có thẻ tên', emoji='📛', group='Đồ dùng', unit='cái', cost=8, price=15, start=6),
    dict(id='toy', name='Đồ chơi gặm', emoji='🧸', group='Đồ dùng', unit='cái', cost=5, price=10, start=10),
    dict(id='bedding', name='Mùn lót chuồng', emoji='🍂', group='Đồ dùng', unit='túi', cost=10, price=18, start=6),
    # bể & lồng
    dict(id='cage_hamster', name='Lồng hamster có bánh xe', emoji='🎡', group='Bể & lồng', unit='cái', cost=55, price=90, start=3),
    dict(id='cage_bird', name='Lồng chim', emoji='🪺', group='Bể & lồng', unit='cái', cost=65, price=110, start=2),
    dict(id='tank_10', name='Bể kính 10 lít', emoji='🫙', group='Bể & lồng', unit='bể', cost=35, price=60, start=4),
    dict(id='tank_30', name='Bể kính 30 lít', emoji='🐟', group='Bể & lồng', unit='bể', cost=70, price=120, start=3),
    dict(id='tank_60', name='Bể kính 60 lít', emoji='🏞️', group='Bể & lồng', unit='bể', cost=130, price=220, start=2),
    dict(id='filter', name='Lọc thác mini', emoji='🌀', group='Bể & lồng', unit='cái', cost=26, price=45, start=5),
    dict(id='heater', name='Sưởi bể 25 W', emoji='🌡️', group='Bể & lồng', unit='cái', cost=20, price=35, start=4),
    dict(id='conditioner', name='Dung dịch khử clo', emoji='💧', group='Bể & lồng', unit='chai', cost=8, price=15, start=8),
]
ITEM = {x['id']: x for x in ITEMS}
# Weight in tenths of a kilo (for the shipper) and the glass tanks a motorbike must not carry.
KG10 = dict(dog_puppy=15, dog_adult=30, dog_large=50, dog_lamb=30, cat_kitten=15, cat_adult=20, cat_senior=15, cat_sensitive=15,
            pate_cat=2, pate_dog=2, fish_food=1, goldfish_food=1, bird_seed=5, hamster_food=5, litter=80, leash=2, collar=1,
            toy=1, bedding=10, cage_hamster=30, cage_bird=40, tank_10=30, tank_30=80, tank_60=180, filter=5, heater=2, conditioner=2)
BIG_GLASS = ('tank_30', 'tank_60')
BIKE_MAX10 = 200

# What each food is for (the label on the bag).
FOODS = {
    'dog_puppy': dict(species='dog', stage='young', size='any', protein='chicken', label='Chó dưới 12 tháng · có gà'),
    'dog_adult': dict(species='dog', stage='adult', size='small', protein='chicken', label='Chó trưởng thành dưới 20 kg · có gà'),
    'dog_large': dict(species='dog', stage='adult', size='large', protein='beef', label='Chó trưởng thành từ 20 kg · vị bò'),
    'dog_lamb': dict(species='dog', stage='adult', size='small', protein='lamb', label='Chó trưởng thành dưới 20 kg · không gà'),
    'cat_kitten': dict(species='cat', stage='young', size='any', protein='chicken', label='Mèo dưới 12 tháng · có gà'),
    'cat_adult': dict(species='cat', stage='adult', size='any', protein='fish', label='Mèo 1–7 tuổi · vị cá'),
    'cat_senior': dict(species='cat', stage='senior', size='any', protein='chicken', label='Mèo từ 7 tuổi · có gà'),
    'cat_sensitive': dict(species='cat', stage='adult', size='any', protein='turkey', label='Mèo 1–7 tuổi · không cá'),
    'fish_food': dict(species='tropical', stage='any', size='any', protein='fish', label='Cá nhiệt đới: betta, bảy màu, tứ vân'),
    'goldfish_food': dict(species='goldfish', stage='any', size='any', protein='fish', label='Cá vàng (nước mát)'),
    'bird_seed': dict(species='bird', stage='any', size='any', protein='seed', label='Chim: yến phụng, vẹt nhỏ'),
    'hamster_food': dict(species='hamster', stage='any', size='any', protein='seed', label='Hamster: hạt, rau củ sấy'),
}
MAIN_FOODS = tuple(FOODS)
PROTEIN = dict(chicken='thịt gà', fish='cá', beef='thịt bò', lamb='thịt cừu', turkey='gà tây', seed='hạt ngũ cốc')
SPECIES = dict(dog='Chó', cat='Mèo', tropical='Cá nhiệt đới', goldfish='Cá vàng', bird='Chim', hamster='Hamster')
STAGE = dict(young='Con non (dưới 12 tháng)', adult='Trưởng thành', senior='Lớn tuổi')

# The shop's own animals (not warehouse stock): they live in data['animals'] and the pens.
ANIMALS = {
    'guppy': dict(name='Cá bảy màu', emoji='🐟', price=5, cost=2, litres=2, water='tropical', target=24, note='Hiền, thích bơi đàn, nước ấm'),
    'betta': dict(name='Cá betta', emoji='🐠', price=25, cost=10, litres=5, water='tropical', target=6, note='Đuôi dài, thích ở một mình, nước ấm'),
    'barb': dict(name='Cá tứ vân', emoji='🐡', price=6, cost=2, litres=4, water='tropical', target=14, note='Lanh lẹ, hay rỉa vây cá đuôi dài'),
    'goldfish': dict(name='Cá vàng', emoji='🐟', price=10, cost=4, litres=10, water='cool', target=10, note='Ưa nước mát 20–25°C, ăn nhiều'),
    'hamster': dict(name='Hamster', emoji='🐹', price=40, cost=18, litres=0, water='', target=4, note='Cần lồng có bánh xe, mùn lót'),
    'budgie': dict(name='Vẹt yến phụng', emoji='🦜', price=60, cost=28, litres=0, water='', target=4, note='Cần lồng rộng, hạt kê, có bạn càng vui'),
}
FISH = ('guppy', 'betta', 'barb', 'goldfish')
TANKS = dict(tank_10=10, tank_30=30, tank_60=60)
# Adoptees of the corner (kittens and puppies are never sold: they go home through Chân Nhỏ).
ADOPTEES = {
    'vang': dict(name='Vàng', emoji='🐕', kind='dog', coat='yellow', text='Chó ta 6 tuổi, hiền, đã triệt sản, thích nằm hiên.'),
    'sua': dict(name='Sữa', emoji='🐈', kind='cat', coat='white', text='Mèo con 3 tháng, lông trắng, hơi nhát.'),
    'muop': dict(name='Mướp Con', emoji='🐈', kind='cat', coat='tabby', text='Mèo con 4 tháng, lông mướp, lém lỉnh, đã tiêm mũi 1.'),
    'dau': dict(name='Đậu', emoji='🐶', kind='dog', coat='spot', text='Cún con 2 tháng, lông đốm nâu trắng, ham ăn.'),
    'than': dict(name='Than', emoji='🐈‍⬛', kind='cat', coat='black', text='Mèo con 3 tháng, đen tuyền, mắt vàng, mê ngủ trong hộp giấy.'),
    'bap': dict(name='Bắp', emoji='🐈', kind='cat', coat='calico', text='Mèo con 5 tháng, tam thể, hay đòi bế.'),
}

# ---------------------------------------------------------------- colours
# (id, name, main colour, second colour or '' for a solid coat, extra price for a rare colour)
COATS = {
    'betta': [('red', 'Đỏ', '#d93b3b', '', 0), ('blue', 'Xanh dương', '#3b6fd9', '', 0), ('purple', 'Tím', '#8a4fd0', '', 0),
              ('white', 'Trắng', '#f1eee6', '#e8d9d0', 15), ('multi', 'Đa sắc', '#e5484d', '#3b6fd9', 15)],
    'goldfish': [('orange', 'Cam', '#f28a2e', '', 0), ('redwhite', 'Trắng đỏ', '#f4f1ea', '#e5484d', 0), ('black', 'Đen', '#2a2a30', '', 5)],
    'guppy': [('fire', 'Đuôi lửa', '#f2c94c', '#e5484d', 0), ('leopard', 'Da báo', '#e8d5a0', '#3a3a3a', 0),
              ('metal', 'Xanh ánh kim', '#7fb2ea', '#3b6fd9', 0), ('cobra', 'Rắn hổ mang', '#9bd46a', '#2f7a3a', 3)],
    'barb': [('tiger', 'Sọc vằn', '#f2b84c', '#2a2a30', 0), ('moss', 'Xanh rêu', '#6f9a4c', '#2a2a30', 3)],
    'hamster': [('cream', 'Vàng kem', '#f0d2a0', '', 0), ('grey', 'Xám', '#a9a9b0', '', 0), ('white', 'Trắng', '#f7f5ef', '', 0),
                ('spot', 'Đốm', '#f7f5ef', '#b07a4a', 10)],
    'budgie': [('green', 'Xanh lá', '#7fd36a', '#f4e04d', 0), ('blue', 'Xanh dương', '#6fb8ef', '#ffffff', 0),
               ('yellow', 'Vàng', '#f4e04d', '#f7ec9a', 0), ('white', 'Trắng', '#f4f4f0', '#cfe7f7', 20)],
}
# The rescue's kittens and puppies (their coat is part of who they are, not a price).
FUR = {
    'cat': [('tabby', 'Mướp', '#b89a74', '#6e5a44', 0), ('black', 'Đen', '#2d2a2e', '', 0), ('white', 'Trắng', '#f4f2ee', '', 0),
            ('calico', 'Tam thể', '#f4f2ee', '#e39a4a', 0)],
    'dog': [('yellow', 'Vàng', '#e8b36a', '', 0), ('black', 'Đen', '#2d2a2e', '', 0), ('spot', 'Đốm', '#f4f2ee', '#8a5a3b', 0)],
}
COAT = {k: {c[0]: c for c in rows} for k, rows in COATS.items()}
SHOW = 6   # animals of each kind drawn in the scene and on the cards


def coat_name(kind: str, coat: str | None) -> str:
    return COAT[kind][coat][1] if coat in COAT.get(kind, {}) else ''


def show_coats(day: int, kind: str) -> list:
    """The colours of the animals on show today (seeded by day: rare colours turn up less often)."""
    r = kit.rng(ID, 'coats', day, kind)
    rows = COATS[kind]
    return [_weighted(rows, r.random(), lambda c: 1 if c[4] else 4)[0] for _ in range(SHOW)]


# ---------------------------------------------------------------- the shop's paint
# Palettes for the scene and the workbench accents; free once the shop reaches `stage`, else bought once.
THEMES = [
    dict(id='ngoc', name='Xanh ngọc san hô', emoji='🐠', cost=0, stage=0,
         colors=dict(wall='#dff3ef', wall_d='#a9d8cf', tile_a='#e7f7f3', tile_b='#d6efe9', main='#2f9e8f', main_d='#1f6f66',
                     accent='#f08a6c', accent_l='#f7b9a3', sand='#f3e3c4', sand_d='#d9c29a')),
    dict(id='hong', name='Hồng pastel', emoji='🌸', cost=40, stage=1,
         colors=dict(wall='#fbe6ee', wall_d='#efb8cb', tile_a='#fdf0f5', tile_b='#f7dde7', main='#d4668f', main_d='#9e3f64',
                     accent='#5fb3a6', accent_l='#bfe4dd', sand='#f7e6dc', sand_d='#dcc0ae')),
    dict(id='nang', name='Vàng nắng', emoji='🌻', cost=40, stage=2,
         colors=dict(wall='#fdf1cf', wall_d='#f0d27a', tile_a='#fff7de', tile_b='#fbe9b6', main='#c98a12', main_d='#7f5406',
                     accent='#3f8fcf', accent_l='#a9d0ef', sand='#f4e4c0', sand_d='#d8bd84')),
    dict(id='rung', name='Xanh lá rừng', emoji='🌿', cost=60, stage=2,
         colors=dict(wall='#e3efdc', wall_d='#a9c89a', tile_a='#edf5e8', tile_b='#dbead2', main='#3f8a4f', main_d='#28603a',
                     accent='#e0a13a', accent_l='#f2cf8d', sand='#eadfc6', sand_d='#cbb88f')),
    dict(id='lavender', name='Tím lavender', emoji='💜', cost=60, stage=3,
         colors=dict(wall='#ece6f7', wall_d='#c9bde6', tile_a='#f4f0fb', tile_b='#e4dcf3', main='#7a64b8', main_d='#52408a',
                     accent='#f2a65a', accent_l='#f8cfa2', sand='#efe6d8', sand_d='#d4c5ad')),
    dict(id='go', name='Gỗ mộc', emoji='🪵', cost=80, stage=3,
         colors=dict(wall='#f1e4d0', wall_d='#cfae86', tile_a='#f6ecdd', tile_b='#ead9c0', main='#8a5a3b', main_d='#5e3b24',
                     accent='#5f9e84', accent_l='#a9d3c1', sand='#eadcc2', sand_d='#c9ad85')),
]
THEME = {x['id']: x for x in THEMES}
DEFAULT_THEME = 'ngoc'
# Ink for the words on the shop sign ('auto' follows the paint).
INKS = dict(auto=('Theo màu sơn', ''), coral=('Đỏ san hô', '#d9573b'), wood=('Nâu gỗ', '#6b4a2e'), navy=('Xanh than', '#24406b'),
            charcoal=('Đen than', '#33363a'))
PRICES = {x['id']: x['price'] for x in ITEMS}
PRICES.update({k: v['price'] for k, v in ANIMALS.items()})
PRICES.update(adopt=30, care=12, ship_bike=10, ship_van=30)
FEE_NAME = dict(adopt='Phí nhận nuôi (tiêm, triệt sản)', care='Công chăm thú', ship_bike='Phí ship xe máy', ship_van='Phí ship xe tải nhỏ')
CART_KEYS = tuple(ITEM) + tuple(ANIMALS) + ('adopt',)
KIT = dict(hamster=('cage_hamster', 'hamster_food', 'bedding'), budgie=('cage_bird', 'bird_seed'))

# ---------------------------------------------------------------- pens (the care job)
PENS = {
    'guppy': dict(name='Bể bảy màu', emoji='🐟', kind='fish', water='tropical'),
    'betta': dict(name='Dãy hũ betta', emoji='🐠', kind='fish', water='tropical'),
    'barb': dict(name='Bể tứ vân', emoji='🐡', kind='fish', water='tropical'),
    'goldfish': dict(name='Bể cá vàng', emoji='🐟', kind='fish', water='cool'),
    'hamster': dict(name='Chuồng hamster', emoji='🐹', kind='cage', water=''),
    'budgie': dict(name='Lồng yến phụng', emoji='🦜', kind='cage', water=''),
    'corner': dict(name='Góc nhận nuôi', emoji='🏡', kind='cage', water=''),
}
TEMP_OK = dict(tropical=(26, 28), cool=(20, 25))
TEMP_NORMAL = dict(tropical=27, cool=23)
PORTIONS = dict(pinch='Một nhúm nhỏ', normal='Một chén vừa', heap='Đổ thật nhiều')
CLEANS = dict(part='Thay 1/3 nước / lau góc bẩn', all='Thay sạch toàn bộ')

# ---------------------------------------------------------------- questions per job
TOPICS = {
    'food': dict(age=('🎂', 'Bé mấy tuổi?'), weight=('⚖️', 'Bé nặng bao nhiêu?'), allergy=('🤧', 'Bé có dị ứng gì không?'),
                 now=('🥣', 'Bé đang ăn gì?')),
    'screen': dict(who=('🙋', 'Ai sẽ chăm bé?'), parent=('👨‍👩‍👦', 'Người lớn trong nhà đồng ý chưa?'), home=('🏠', 'Nhà ở thế nào?'),
                   time=('⏰', 'Mỗi ngày ở nhà bao lâu?'), others=('🐾', 'Nhà đang nuôi con gì?'), allergy=('🤧', 'Có ai dị ứng lông?')),
    'ret': dict(receipt=('🧾', 'Xem hóa đơn'), seal=('🔒', 'Xem seal bao bì'), batch=('🏷️', 'Dò mã lô'), date=('📅', 'Xem hạn dùng'),
                defect=('🔍', 'Xem món có lỗi không')),
    'lost': dict(look=('👀', 'Bé trông thế nào?'), where=('📍', 'Lạc ở đâu?'), when=('🕘', 'Lạc lúc nào?'), phone=('📞', 'Số liên lạc?'),
                 habit=('🙈', 'Bé hay trốn đâu?'), mark=('🤫', 'Có dấu riêng nào không?')),
    'ship': dict(confirm=('📍', 'Gọi xác nhận địa chỉ'), time=('🕒', 'Hỏi giờ nhận hàng')),
    'tank': {}, 'care': {},
}
VERDICTS = dict(sell='Đồng ý giao bé', later='Hẹn quay lại sau', refuse='Từ chối nhẹ nhàng, gợi ý cách khác')
SIGNS = dict(vax='Giao sổ tiêm, dặn lịch mũi tiếp', follow='Hẹn nhóm Chân Nhỏ ghé thăm sau 2 tuần',
             back='Cam kết: không nuôi được thì trả về nhóm, không bán cho ai')
TIPS = dict(float=('✅', 'Ngâm túi cá 15 phút cho quen nhiệt rồi mới thả'),
            part=('✅', 'Mỗi tuần thay 1/3 nước, nhớ khử clo'),
            pinch=('✅', 'Cho ăn một nhúm, cá ăn hết trong 2 phút'),
            full=('❌', 'Mỗi tuần thay sạch toàn bộ nước cho trong'),
            feed=('❌', 'Cho ăn thật nhiều cho cá mau lớn'),
            sun=('❌', 'Để bể chỗ nắng cho cá khỏe'))
GOOD_TIPS = ('float', 'part', 'pinch')
DECISIONS = dict(refund='Hoàn tiền', exchange='Đổi món mới', refuse='Không nhận, giải thích quy định')
POLICY = 'Đổi trả trong 7 ngày: có hóa đơn của tiệm, bao còn nguyên seal. Hàng lỗi thì đổi mới. Hàng tiệm bán sai hoặc quá hạn thì hoàn tiền.'
FIELDS = dict(photo=('📷', 'Ảnh rõ mặt'), look=('👀', 'Đặc điểm dễ thấy'), where=('📍', 'Nơi lạc'), when=('🕘', 'Giờ lạc'),
              phone=('📞', 'Số điện thoại'), mark=('🤫', 'Dấu riêng'), address=('🏠', 'Địa chỉ nhà'), reward=('💰', 'Số tiền thưởng'))
NOTICE_NEED = ('look', 'where', 'when', 'phone')
CALL_MOVES = ('check', 'send', 'block')
SHIPPERS = dict(bike=('🛵', 'Xe máy · tối đa 20 kg, không chở bể kính lớn'), van=('🚚', 'Xe tải nhỏ · hàng nặng, bể kính'))

JOB_NAMES = dict(food='Tư vấn thức ăn', tank='Setup bể cá', screen='Bán thú & nhận nuôi', care='Chăm thú trong tiệm',
                 ret='Đổi trả hàng', lost='Bảng tìm thú lạc', ship='Giao hàng nặng')
JOB_EMOJI = dict(food='🥣', tank='🐠', screen='🏡', care='🧽', ret='🔁', lost='📌', ship='🛵')
JOBS = tuple(JOB_NAMES)
TILL_JOBS = ('food', 'tank', 'screen')

PEOPLE = [
    ('Nhã', 'Cháu gái chú Út, sinh viên thú y năm ba', 'Trông tiệm sau giờ học, muốn tiệm bán có tâm: thú khỏe, khách hiểu, không bán bừa.', 'warm'),
    ('Chú Út', 'Chủ tiệm cũ', 'Ba mươi năm buôn bán, quen “khách hỏi gì bán nấy”, thương thú mà ngại đổi nếp.', 'bossy'),
    ('Chú Sáu', 'Dân chơi cá cảnh trong hẻm', 'Chiều nào cũng ghé ngó bể, soi từng cái vây.', 'picky'),
    ('Bà Hai', 'Hàng xóm nuôi năm con mèo', 'Trả giá từng xu, rất mê rổ giảm giá, nhưng mèo ốm là chạy qua đầu tiên.', 'sour'),
    ('Bé Bin', 'Cậu bé lớp 4 mê hamster', 'Đập heo đất để dành cả năm, mơ nuôi một bé hamster.', 'genz'),
    ('Uyên', 'Sinh viên ở trọ', 'Phòng trọ nhỏ, chủ trọ khó, muốn có góc xanh cho đỡ nhớ nhà.', 'quiet'),
    ('Anh Khánh', 'Tình nguyện viên nhóm cứu hộ Chân Nhỏ', 'Yên xe lúc nào cũng có một lồng mèo con.', 'warm'),
    ('Anh Quân', 'Chủ bé corgi Tofu', 'Đọc kỹ từng dòng trên bao hạt. Tofu dị ứng thịt gà.', 'picky'),
]
NAMES = [p[0] for p in PEOPLE]

# ---------------------------------------------------------------- variants
def _v(vid, npc, title, opening, needs, x, min_day=1, weight=2, script=False):
    return dict(id=vid, npc=npc, title=title, opening=opening, needs=needs, x=x, min_day=min_day, weight=weight, script=script)


FOOD = [
    _v('mun_kitten', 3, 'Bao hạt cho bé Mun',
       'Bà Hai xách cái giỏ nhựa vào, đặt cạnh quầy: “Con mèo mới lượm về đó. Bán bà bao hạt nào rẻ mà tốt!”',
       dict(pet='Mun', species='cat', emoji='🐈', qty=1, request='Một bao hạt cho con mèo mới lượm, rẻ mà tốt.'),
       dict(right='cat_kitten', stage='young', size='any', allergy=None,
            a=dict(age='Chừng năm tháng thôi, răng sữa mới thay xong.', weight='Hai ký rưỡi, nhẹ hều.',
                   allergy='Chưa thấy nó dị ứng gì, cái gì cũng đòi ăn.', now='Bà cho ăn cơm trộn cá, nó ăn được ít lắm.'),
            grab=None), script=True),
    _v('tofu_allergy', 7, 'Hạt cho Tofu', 'Anh Quân bế bé corgi Tofu vào, tay cầm tờ giấy của bác sĩ: “Tofu hết hạt rồi. Em tư vấn giúp anh loại nào hợp nhé.”',
       dict(pet='Tofu', species='dog', emoji='🐕', qty=1, request='Một túi hạt hợp với Tofu, corgi nhà anh.'),
       dict(right='dog_lamb', stage='adult', size='small', allergy='chicken',
            a=dict(age='Tofu ba tuổi rồi em.', weight='Mười hai ký, hơi tròn.',
                   allergy=f'Bác sĩ {VET} dặn Tofu dị ứng thịt gà, ăn vô là ngứa đỏ bụng.', now='Đang ăn hạt vị bò, nhưng tiệm hết loại đó.'),
            grab=None)),
    _v('map_fish', 1, 'Hạt cho con Mập', 'Chú Út chống nạnh trước kệ: “Con Mập của tiệm hết hạt. Lấy bao vị cá như xưa nay, nó mê cá lắm.”',
       dict(pet='Mập', species='cat', emoji='🐈', qty=1, request='Một bao hạt cho con Mập, mèo của tiệm.'),
       dict(right='cat_sensitive', stage='adult', size='any', allergy='fish',
            a=dict(age='Nó sáu tuổi rồi, về tiệm từ hồi còn bé xíu.', weight='Sáu ký, ăn như tằm ăn rỗi.',
                   allergy='Ờ… con Nhã nói con Mập ăn cá là gãi trụi lông cổ, bác sĩ dặn kiêng cá. Chú thì thấy nó vẫn thèm.',
                   now='Hạt vị cá, trộn thêm đầu cá chiên.'),
            grab=None)),
    _v('muop_senior', 3, 'Hạt cho bà Mướp', 'Bà Hai ôm theo rổ giảm giá của tiệm: “Bà lấy thêm hai lon pate trong rổ này, rẻ! Với một bao hạt cho con Mướp.”',
       dict(pet='Mướp', species='cat', emoji='🐈', qty=1, request='Một bao hạt cho con Mướp, với hai lon pate lấy trong rổ giảm giá.',
            extra=dict(item='pate_cat', qty=2)),
       dict(right='cat_senior', stage='senior', size='any', allergy=None,
            a=dict(age='Mười ba tuổi, già hơn cả cái tiệm này.', weight='Ba ký rưỡi, dạo này hơi gầy.',
                   allergy='Nó không dị ứng gì, chỉ kén ăn.', now='Hạt mèo thường, nhai không nổi mấy hạt to.'),
            grab=dict(item='pate_cat', qty=2, expired=True, label='In trên đáy lon: HSD đã qua 3 ngày. Lon hơi phồng.')), min_day=3),
    _v('linh_betta_food', 5, 'Cám cho cá betta', 'Uyên ghé sau giờ học: “Em mua cám cho con betta nha. Cá vàng hay cá gì em cũng không rành lắm.”',
       dict(pet='Mực Xanh', species='tropical', emoji='🐠', qty=1, request='Một hộp cám cho con betta trong phòng trọ.'),
       dict(right='fish_food', stage='any', size='any', allergy=None,
            a=dict(age='Em nuôi được hai tuần rồi.', weight='Bé xíu, dài bằng ngón tay.', allergy='Cá mà dị ứng hả chị?',
                   now='Em cho ăn cơm nguội, bạn cùng phòng bảo không được.'),
            grab=None), min_day=3),
    _v('dau_puppy', 6, 'Hạt cho cún Đậu', 'Anh Khánh dựng xe trước cửa: “Nhóm mới đón bé Đậu hai tháng tuổi. Anh lấy hai túi hạt với ba lon pate trong rổ này nhé.”',
       dict(pet='Đậu', species='dog', emoji='🐶', qty=2, request='Hai túi hạt cho cún Đậu hai tháng tuổi, thêm ba lon pate trong rổ giảm giá.',
            extra=dict(item='pate_dog', qty=3)),
       dict(right='dog_puppy', stage='young', size='any', allergy=None,
            a=dict(age='Hai tháng, mới cai sữa.', weight='Hai ký, lớn tới đâu ăn tới đó.', allergy='Chưa thấy bé dị ứng gì.',
                   now='Đang ăn cháo gan với hạt ngâm mềm.'),
            grab=dict(item='pate_dog', qty=3, expired=True, label='Nhãn ghi HSD tuần trước, ai đó dán đè giá mới lên.')), min_day=4),
    _v('bin_hamster_food', 4, 'Đồ ăn cho Bánh Bao', 'Bé Bin chạy vào, tay nắm chặt mấy tờ tiền: “Bánh Bao nhà con hết đồ ăn rồi! Con mua gói hạt nha!”',
       dict(pet='Bánh Bao', species='hamster', emoji='🐹', qty=1, request='Một gói đồ ăn cho hamster Bánh Bao.'),
       dict(right='hamster_food', stage='any', size='any', allergy=None,
            a=dict(age='Bánh Bao về nhà con được mấy tuần rồi.', weight='Tròn vo, cầm nặng tay lắm.',
                   allergy='Mẹ con dặn không cho ăn sô-cô-la.', now='Hạt với cà rốt mẹ cắt nhỏ.'),
            grab=None), min_day=5),
    _v('vang_large', 2, 'Hạt cho chó Vàng', 'Chú Sáu dắt Vàng vào tới quầy: “Vàng về nhà chú rồi. Bao hạt nào hợp với nó, cháu chọn giùm.”',
       dict(pet='Vàng', species='dog', emoji='🐕', qty=1, request='Một bao hạt cho con Vàng.'),
       dict(right='dog_large', stage='adult', size='large', allergy=None,
            a=dict(age='Sáu tuổi, nhóm Chân Nhỏ ghi trong sổ.', weight='Hai mươi bốn ký, chó ta mà to con.',
                   allergy='Không dị ứng gì, ăn gì cũng ngon.', now='Cơm với thịt luộc, thím nhà chú nấu.'),
            grab=None), min_day=6),
    _v('bong_fish', 3, 'Hạt cho con Bông', 'Bà Hai đứng gãi đầu: “Con Bông nhà bà ngứa quá, bác sĩ Cỏ May nói kiêng cá. Bán bà bao hạt nào đây?”',
       dict(pet='Bông', species='cat', emoji='🐈', qty=1, request='Một bao hạt cho con Bông đang bị ngứa.'),
       dict(right='cat_sensitive', stage='adult', size='any', allergy='fish',
            a=dict(age='Bốn tuổi.', weight='Bốn ký.', allergy='Bác sĩ nói nó dị ứng cá, ăn cá vô là gãi.', now='Hạt vị cá, rẻ nhất tiệm.'),
            grab=None), min_day=7),
]
TANK = [
    _v('linh_betta', 5, 'Góc xanh cho phòng trọ', 'Uyên đứng ngắm dãy hũ betta thật lâu: “Phòng trọ em nhỏ lắm. Em muốn nuôi một con betta màu xanh dương, bể để trên bàn học được không chị?”',
       dict(want=dict(betta=1), keep=dict(betta=1), room='Bàn học trong phòng trọ 12 m²', coat=dict(betta='blue'),
            request='Một con betta xanh dương và một bể nhỏ để trên bàn học.'),
       dict(), script=True),
    _v('sau_community', 2, 'Bể cộng đồng của chú Sáu', 'Chú Sáu vỗ vào cái bể 60 lít: “Chú muốn mười con bảy màu, sáu con tứ vân, thêm một con betta đuôi dài cho đẹp. Làm bể này luôn!”',
       dict(want=dict(guppy=10, barb=6, betta=1), keep=dict(guppy=10), room='Phòng khách nhà chú Sáu, chỗ mát',
            request='Bể 60 lít: mười bảy màu, sáu tứ vân, một betta đuôi dài.'),
       dict(), script=True),
    _v('bin_goldfish', 4, 'Ba con cá vàng', 'Bé Bin dí mũi vào bể cá vàng: “Con muốn ba con cá vàng trắng đỏ trong cái bể nhỏ xíu kia! Để trên bàn học của con.”',
       dict(want=dict(goldfish=3), keep=dict(goldfish=1), room='Bàn học của Bin, mẹ Thảo đồng ý rồi', coat=dict(goldfish='redwhite'),
            request='Ba con cá vàng trắng đỏ và một cái bể để bàn.'),
       dict(), min_day=3),
    _v('quan_office', 7, 'Bể cho bàn làm việc', 'Anh Quân chìa điện thoại: “Anh muốn bể để văn phòng: sáu con bảy màu với hai con cá vàng cho đủ màu. Setup giúp anh.”',
       dict(want=dict(guppy=6, goldfish=2), keep=dict(guppy=6), room='Góc bàn làm việc, có máy lạnh',
            request='Sáu con bảy màu với hai con cá vàng trong một bể.'),
       dict(), min_day=5),
    _v('hai_bettas', 3, 'Hai con betta cho vui', 'Bà Hai chỉ vào hai hũ betta: “Bà lấy hai con này, thả chung một bể cho tụi nó có bạn. Bể nhỏ thôi nghe, bà không có chỗ.”',
       dict(want=dict(betta=2), keep=dict(betta=1), room='Bệ cửa sổ nhà bà Hai',
            request='Hai con betta chung một bể nhỏ.'),
       dict(), min_day=6),
    _v('linh_guppy', 5, 'Đàn bảy màu nho nhỏ', 'Uyên quay lại, mắt sáng rỡ: “Chủ trọ cho em nuôi cá rồi! Em muốn năm con bảy màu rắn hổ mang, loại hiếm hiếm đó chị.”',
       dict(want=dict(guppy=5), keep=dict(guppy=5), room='Kệ sách phòng trọ', coat=dict(guppy='cobra'),
            request='Năm con bảy màu rắn hổ mang trong một bể nhỏ.'),
       dict(), min_day=8),
]
SCREEN = [
    _v('bin_alone', 4, 'Bin muốn nuôi hamster', 'Bé Bin đặt con heo đất lên quầy: “Con muốn mua một bé hamster! Con đập heo rồi nè, đủ tiền luôn!”',
       dict(pet='hamster', kind='sale', request='Một bé hamster.'),
       dict(ok=['later'], key='parent',
            a=dict(who='Con tự nuôi! Con lớp 4 rồi mà.', parent='Mẹ con… chưa biết. Con định làm mẹ bất ngờ!',
                   home='Nhà con ở chung cư tầng năm.', time='Con đi học cả ngày, tối về chơi với nó.',
                   others='Nhà có con mèo Bơ của chị con, nó hay rình con chim sẻ ngoài ban công.', allergy='Không ai dị ứng hết á.')),
       script=True),
    _v('bin_mom', 4, 'Bin quay lại với mẹ', 'Bé Bin kéo tay một cô vào tiệm: “Mẹ con nè! Mẹ đồng ý rồi!” Chị Thảo cười: “Hôm qua tiệm dặn về hỏi mẹ, cô cảm ơn nha.” Bin chỉ vào lồng: “Con lấy bé màu xám!”',
       dict(pet='hamster', kind='sale', coat=dict(hamster='grey'), request='Một bé hamster màu xám, lần này có mẹ đi cùng.'),
       dict(ok=['sell'], key='parent',
            a=dict(who='Bin chăm, cô để mắt tới, dọn chuồng cuối tuần hai mẹ con làm.', parent='Chị Thảo gật đầu: “Cô đồng ý. Cô sẽ để mắt tới.”',
                   home='Chung cư tầng năm, để chuồng trong phòng Bin.', time='Tối nào cũng có người ở nhà.',
                   others='Con mèo Bơ theo chị hai của Bin về quê rồi.', allergy='Không ai dị ứng.')),
       script=True),
    _v('linh_kitten', 5, 'Uyên muốn nhận nuôi mèo', 'Uyên ngồi thụp xuống trước góc nhận nuôi: “Bé Sữa dễ thương quá… Em nhận nuôi bé được không chị?”',
       dict(pet='sua', kind='adopt', request='Nhận nuôi mèo con Sữa ở góc nhận nuôi.'),
       dict(ok=['refuse', 'later'], key='home',
            a=dict(who='Em tự chăm.', parent='Em hai mươi tuổi rồi chị.', home='Phòng trọ 12 m², hợp đồng ghi rõ không nuôi chó mèo, chủ trọ khó lắm.',
                   time='Em học với làm thêm, tối mới về.', others='Em có con betta thôi.', allergy='Không ai dị ứng.')),
       min_day=3),
    _v('quan_budgie', 7, 'Vẹt tặng mẹ', 'Anh Quân chỉ lồng yến phụng: “Anh lấy một con tặng mẹ anh làm quà bất ngờ. Mẹ anh ở một mình, có con chim cho vui.”',
       dict(pet='budgie', kind='sale', request='Một con yến phụng làm quà bất ngờ cho mẹ.'),
       dict(ok=['later'], key='who',
            a=dict(who='Mẹ anh chăm, mà mẹ chưa biết đâu, bất ngờ mà.', parent='Mẹ anh bảy mươi tuổi rồi.',
                   home='Nhà mẹ ở dưới quê, có hiên rộng.', time='Mẹ ở nhà suốt.', others='Không nuôi con gì.',
                   allergy='Mẹ anh hay hen suyễn, sợ lông với bụi lắm.')),
       min_day=4),
    _v('sau_budgie', 2, 'Bạn cho con Xanh', 'Chú Sáu xách cái lồng có con Xanh: “Nó ở một mình buồn, cứ gọi Sáu ơi hoài. Bán chú một con yến phụng xanh dương làm bạn với nó.”',
       dict(pet='budgie', kind='sale', coat=dict(budgie='blue'), request='Một con yến phụng xanh dương làm bạn với con Xanh.'),
       dict(ok=['sell'], key='others',
            a=dict(who='Chú chăm, sáng nào cũng thay nước, thay hạt.', parent='Thím nhà chú mê chim lắm, còn giục chú đi mua.',
                   home='Nhà có hiên rộng, lồng treo chỗ mát, không có mèo.', time='Chú nghỉ hưu, ở nhà cả ngày.',
                   others='Con Xanh, yến phụng hai tuổi, khỏe re.', allergy='Không ai dị ứng.')),
       min_day=6),
    _v('sau_adopt', 2, 'Chú Sáu nhận nuôi Vàng', 'Anh Khánh dắt Vàng vào, chú Sáu đứng chờ sẵn: “Chú để ý con Vàng cả tuần nay rồi. Cho chú rước nó về nhé.”',
       dict(pet='vang', kind='adopt', request='Nhận nuôi chó Vàng ở góc nhận nuôi.'),
       dict(ok=['sell'], key='home',
            a=dict(who='Chú với thím. Thím còn mê chó hơn chú.', parent='Nhà chỉ có hai ông bà già.',
                   home='Nhà có sân sau, rào kín ba phía.', time='Chú nghỉ hưu, ở nhà cả ngày.',
                   others='Ba bể cá thôi, không nuôi chó mèo.', allergy='Không ai dị ứng.')),
       script=True),
    _v('quan_puppy', 7, 'Thêm bạn cho Tofu', 'Anh Quân nhìn bé Đậu: “Tofu ở nhà một mình buồn quá. Anh nhận thêm bé này cho có bạn nhé.”',
       dict(pet='dau', kind='adopt', request='Nhận nuôi cún Đậu cho Tofu có bạn.'),
       dict(ok=['later', 'refuse'], key='time',
            a=dict(who='Anh chăm.', parent='Anh ở một mình.', home='Căn hộ 40 m² tầng mười hai.',
                   time='Anh đi làm từ tám giờ sáng tới tám giờ tối, cuối tuần hay đi công tác.',
                   others='Tofu hay ghen, có chó lạ vào nhà là sủa suốt.', allergy='Không ai dị ứng.')),
       min_day=7),
    _v('hai_kitten', 3, 'Bà Hai nhận nuôi Mướp Con', 'Bà Hai bế Mướp Con lên, giọng dịu hẳn: “Con này giống con Mướp của bà hồi nhỏ. Cho bà rước về.”',
       dict(pet='muop', kind='adopt', request='Nhận nuôi mèo con Mướp Con.'),
       dict(ok=['sell'], key='others',
            a=dict(who='Bà chăm, năm con mèo bà chăm được thì thêm một con cũng được.', parent='Nhà có bà với thằng cháu.',
                   home='Nhà phố, ban công có lưới.', time='Bà ở nhà suốt ngày.',
                   others='Năm con mèo, đứa nào cũng tiêm đủ, triệt sản hết rồi.', allergy='Không ai dị ứng.')),
       min_day=7),
]
CARE = [
    _v('care_first', 2, 'Buổi sáng ở dãy bể', 'Chú Sáu đã đứng trước dãy bể từ sớm: “Cho ăn, dọn chuồng đi cháu. Chú đứng đây coi cho vui.”',
       dict(request='Cho ăn, dọn dẹp và xem sức khỏe các bé trong tiệm.'),
       dict(pens=['guppy', 'betta', 'hamster'], dirty=['hamster'], cold=None, sick=None, sign=''), script=True),
    _v('care_sick_fish', 2, 'Có bé trông lạ lắm', 'Chú Sáu gõ nhẹ vào kính: “Cháu coi lại bể bảy màu giùm chú. Mà sao hôm nay hũ betta lạnh ngắt vậy?”',
       dict(request='Cho ăn, dọn bể, đo nhiệt và soi kỹ từng bể.'),
       dict(pens=['guppy', 'betta', 'goldfish', 'budgie'], dirty=['goldfish'], cold='betta', sick='guppy',
            sign='Một con bảy màu có đốm trắng li ti trên vây, cứ cọ mình vào đá.'), min_day=4),
    _v('care_hamster', 1, 'Chuồng hamster im ắng', 'Chú Út đứng khoanh tay: “Mấy con chuột cảnh sáng nay im re. Cho ăn đi, xong chú coi.”',
       dict(request='Cho ăn, dọn chuồng và xem sức khỏe các bé.'),
       dict(pens=['hamster', 'budgie', 'barb'], dirty=['hamster', 'budgie'], cold=None, sick='hamster',
            sign='Một bé hamster lờ đờ, lông xù, đuôi ướt, không chịu ăn.'), min_day=5),
    _v('care_corner', 6, 'Góc nhận nuôi buổi sáng', 'Anh Khánh ghé sớm mang theo túi cát: “Anh qua coi mấy bé ở góc nhận nuôi. Em cho cả tiệm ăn giúp anh nhé.”',
       dict(request='Cho ăn, dọn chuồng, đo nhiệt, xem các bé ở góc nhận nuôi.'),
       dict(pens=['corner', 'guppy', 'budgie'], dirty=['corner'], cold='guppy', sick='corner',
            sign='Mèo con Sữa hắt hơi liên tục, mắt kèm nhèm.'), min_day=5),
    _v('care_calm', 2, 'Một buổi sáng yên ả', 'Chú Sáu kéo ghế ngồi trước bể cá vàng: “Hôm nay trời mát. Cho ăn, thay nước đi cháu.”',
       dict(request='Cho ăn, dọn dẹp và xem sức khỏe các bé trong tiệm.'),
       dict(pens=['goldfish', 'barb', 'hamster', 'budgie'], dirty=['barb'], cold=None, sick=None, sign=''), min_day=1),
    _v('care_cold', 2, 'Đêm qua cúp điện', 'Chú Sáu thò đầu vào: “Tối qua cúp điện cả khu. Coi mấy cái sưởi với lọc có chạy lại chưa cháu.”',
       dict(request='Cho ăn, dọn bể, đo nhiệt từng bể.'),
       dict(pens=['guppy', 'betta', 'barb'], dirty=['guppy'], cold='barb', sick=None, sign=''), min_day=5),
]
RET = [
    _v('quan_sealed', 7, 'Đổi bao hạt mua nhầm', 'Anh Quân đặt túi hạt lên quầy: “Hôm trước anh mua vội, về mới thấy vị gà. Tofu không ăn được. Đổi giúp anh nhé.”',
       dict(item='dog_adult', request='Trả lại một túi hạt vị gà mua nhầm.'),
       dict(ok=['refund', 'exchange'], legit=True, resell=True, fault=False, a=dict(receipt='Hóa đơn của tiệm, mua ba hôm trước.', seal='Seal còn nguyên, chưa mở.',
                                                           batch='Mã lô trùng lô tiệm nhập tuần này.', date='Còn hạn gần một tháng.',
                                                           defect='Túi nguyên vẹn, không rách.')), min_day=2),
    _v('hai_half', 3, 'Bao hạt ăn dở', 'Bà Hai đặt bao hạt vơi một nửa lên quầy: “Mèo nhà bà không thích. Trả lại tiền cho bà!”',
       dict(item='cat_adult', request='Trả lại bao hạt đã ăn một nửa vì mèo không thích.'),
       dict(ok=['refuse'], legit=False, resell=False, fault=False, a=dict(receipt='Hóa đơn của tiệm, mua mười hai hôm trước.', seal='Đã xé seal, bao còn chừng một nửa.',
                                                batch='Mã lô của tiệm.', date='Còn hạn.', defect='Hạt bình thường, không mốc, không lạ.')),
       min_day=2),
    _v('khanh_leash', 6, 'Dây dắt bung khóa', 'Anh Khánh chìa sợi dây dắt: “Mua hôm kia, mới dắt bé Đậu hai lần thì khóa bung. May mà bé không chạy ra đường.”',
       dict(item='leash', request='Đổi sợi dây dắt bị bung khóa.'),
       dict(ok=['exchange', 'refund'], legit=True, resell=False, fault=False, a=dict(receipt='Hóa đơn của tiệm, mua hai hôm trước.', seal='Dây đã dùng, bao bì còn giữ lại.',
                                                            batch='Hàng nhập từ nhà phân phối của tiệm.', date='Không có hạn dùng.',
                                                            defect='Lò xo trong khóa gãy, bấm không giữ lại được: lỗi của nhà sản xuất.')),
       min_day=4),
    _v('sau_expired', 2, 'Hộp cám quá hạn', 'Chú Sáu đặt hộp cám lên quầy, gõ gõ ngón tay: “Hộp này mua ở đây hôm qua. Cháu coi cái hạn dùm chú.”',
       dict(item='fish_food', request='Trả hộp cám cá mua hôm qua.'),
       dict(ok=['refund', 'exchange'], legit=True, resell=False, fault=True, a=dict(receipt='Hóa đơn của tiệm, mua hôm qua.', seal='Mới mở một lần.',
                                                            batch='Lô cũ trong kho của chú Út, nhập từ năm ngoái.', date='Quá hạn hai tháng. Tiệm đã bán hàng quá hạn.',
                                                            defect='Cám vón cục, có mùi ẩm.')), min_day=5),
    _v('hai_market', 3, 'Bao hạt mua ngoài chợ', 'Bà Hai đặt bao hạt còn nguyên lên quầy: “Bà mua dư, trả lại lấy tiền đi. Giá tiệm con bán đó.”',
       dict(item='cat_adult', request='Trả lại một bao hạt còn nguyên.'),
       dict(ok=['refuse'], legit=False, resell=True, fault=False, a=dict(receipt='Bà không có hóa đơn: “Mất rồi!”', seal='Seal còn nguyên.',
                                                batch='Mã lô không phải lô tiệm nhập, tem dán của một sạp ngoài chợ.', date='Còn hạn.',
                                                defect='Không lỗi gì.')), min_day=6),
]
LOST = [
    _v('mun_lost', 3, 'Mun đi lạc', 'Bà Hai chạy vào, tóc rối bù: “Con Mun mất tích từ tối qua! Tiệm có bảng tìm thú lạc, dán giùm bà tờ tìm mèo!”',
       dict(pet='Mun', emoji='🐈', request='Viết và dán tờ tìm mèo Mun.'),
       dict(a=dict(look='Mèo mướp xám năm tháng, đeo vòng cổ đỏ có chuông.', where='Cửa sau nhà bà, sát bãi xe chợ.',
                   when='Tối qua chừng chín giờ.', phone='Số của bà đây, con ghi vô.', habit='Nó sợ xe máy, hay chui gầm xe.',
                   mark='Chóp đuôi nó gãy một khúc, phải sờ mới thấy.'),
            calls=[dict(id='c1', kind='wrong', text='Một chú gọi: “Đầu hẻm 5 có con mèo mướp, không đeo vòng.”',
                        check='Chú ấy nhìn kỹ: “Đuôi nó thẳng băng, dài thòng.”'),
                   dict(id='c2', kind='scam', text='Một số lạ nhắn: “Tôi nhặt được mèo. Chuyển trước 200 xu tiền giữ giùm rồi tôi mang tới.”',
                        check='Hỏi về cái đuôi thì người đó lảng: “Chuyển tiền đi rồi tính.”'),
                   dict(id='c3', kind='real', text='Chị bán xôi ở bãi xe chợ gọi: “Có con mèo con núp gầm xe từ tối qua, run lắm.”',
                        check='Chị ấy sờ nhẹ: “Chóp đuôi có khúc gãy nè em.”')]), script=True),
    _v('tofu_lost', 7, 'Tofu sổng dây', 'Anh Quân thở hổn hển: “Tofu tuột dây ở công viên! Anh chạy tìm cả tiếng rồi. Em dán giúp anh tờ tìm chó.”',
       dict(pet='Tofu', emoji='🐕', request='Viết và dán tờ tìm chó Tofu.'),
       dict(a=dict(look='Corgi vàng trắng, mông tròn, đeo yếm xanh.', where='Công viên Mây, cổng phía hồ.', when='Sáng nay lúc sáu giờ rưỡi.',
                   phone='Số anh đây em.', habit='Nghe tiếng túi bánh là chạy tới.', mark='Sau gáy có vệt lông trắng hình giọt nước.'),
            calls=[dict(id='c1', kind='real', text='Bác bảo vệ trường tiểu học gọi: “Có con chó chân ngắn nằm dưới gốc phượng, đeo yếm xanh.”',
                        check='Bác nhìn gáy nó: “Có vệt trắng như giọt nước.”'),
                   dict(id='c2', kind='scam', text='Một tin nhắn: “Chó đang ở chỗ tôi. Muốn nhận thì chuyển 300 xu phí chăm sóc.”',
                        check='Hỏi gáy có dấu gì, người đó gửi một tấm ảnh corgi lấy trên mạng.'),
                   dict(id='c3', kind='wrong', text='Một cô gọi: “Có con corgi ở quán cà phê đầu đường, chủ đang ngồi uống cà phê.”',
                        check='Cô nhìn gáy con chó: “Không có vệt trắng nào hết.”')]), min_day=6),
    _v('xanh_lost', 2, 'Con vẹt Xanh bay mất', 'Chú Sáu cầm cái lồng trống: “Con Xanh bay mất lúc chú thay nước! Nó biết nói đó, cháu dán tờ giấy tìm giùm chú.”',
       dict(pet='Xanh', emoji='🦜', request='Viết và dán tờ tìm vẹt Xanh.'),
       dict(a=dict(look='Yến phụng xanh lá, đầu vàng.', where='Hẻm 7, bay về phía chợ.', when='Chiều qua bốn giờ.', phone='Số chú đây.',
                   habit='Hay đậu trên dây phơi đồ.', mark='Nó biết nói “Sáu ơi”, người lạ nói thì nó im.'),
            calls=[dict(id='c1', kind='scam', text='Một số lạ: “Vẹt đang ở nhà tôi, chuyển 150 xu đặt cọc tôi mới giữ.”',
                        check='Hỏi con vẹt biết nói gì, người đó bảo: “Chim thì biết hót chứ nói gì.”'),
                   dict(id='c2', kind='real', text='Cô bán hoa đầu chợ gọi: “Có con yến phụng đậu trên sào phơi đồ nhà tôi.”',
                        check='Cô gọi thử “Sáu ơi”, con chim nghiêng đầu kêu lại “Sáu ơi!”'),
                   dict(id='c3', kind='wrong', text='Một bé gọi: “Nhà con có con vẹt xanh mới mua hôm qua, có phải không?”',
                        check='Mẹ bé nói con vẹt nhà mình mua ở chợ chim, có hóa đơn.')]), min_day=8),
]
SHIP = [
    _v('hai_litter', 3, 'Ba bao cát cho nhà năm mèo', 'Bà Hai gọi điện: “Giao bà ba bao cát với bốn lon pate mèo. Hẻm 12 chợ Mây, nhanh nghe!”',
       dict(order=dict(litter=3, pate_cat=4), address='Hẻm 12 chợ Mây', request='Giao ba bao cát và bốn lon pate mèo.'),
       dict(van=True, a=dict(confirm='Hẻm 12/4, cổng xanh, chứ không phải hẻm 12 nghe con. Hẻm 12 dài lắm.',
                              time='Trước năm giờ chiều, bà còn đi chợ.')), min_day=3),
    _v('quan_food', 7, 'Giao hạt cho Tofu', 'Anh Quân nhắn: “Em giao giúp anh hai túi hạt vị cừu với một đồ chơi gặm. Chung cư Mây Xanh nhé.”',
       dict(order=dict(dog_lamb=2, toy=1), address='Chung cư Mây Xanh', request='Giao hai túi hạt vị cừu và một đồ chơi gặm.'),
       dict(van=False, a=dict(confirm='Block B, tầng 12, gọi anh xuống sảnh. Không phải block A nha em.', time='Sau sáu giờ tối anh mới về.')),
       min_day=5),
    _v('sau_tank60', 2, 'Bể 60 lít về nhà chú Sáu', 'Chú Sáu đặt cọc: “Giao chú một bể 60 lít, một bộ lọc với một cây sưởi. Cuối hẻm 7.”',
       dict(order=dict(tank_60=1, filter=1, heater=1), address='Cuối hẻm 7', request='Giao một bể 60 lít, một lọc và một sưởi.'),
       dict(van=True, a=dict(confirm='Nhà cuối hẻm 7 có giàn bông giấy. Gọi trước mười lăm phút để chú ra phụ khiêng.', time='Sáng mai càng tốt.')),
       min_day=6),
    _v('khanh_rescue', 6, 'Hàng cho trạm cứu hộ', 'Anh Khánh gọi: “Giao giúp anh bốn túi hạt mèo con với hai bao cát về trạm Chân Nhỏ nhé.”',
       dict(order=dict(cat_kitten=4, litter=2), address='Trạm cứu hộ Chân Nhỏ', request='Giao bốn túi hạt mèo con và hai bao cát.'),
       dict(van=True, a=dict(confirm='Trạm nằm sau chùa Mây, đi cổng phụ, cổng chính đang sửa.', time='Giờ nào cũng có người trực.')),
       min_day=8),
]
VARIANTS = dict(food=FOOD, tank=TANK, screen=SCREEN, care=CARE, ret=RET, lost=LOST, ship=SHIP)
VINDEX = {job: {x['id']: x for x in rows} for job, rows in VARIANTS.items()}

# Scripted first days: an easy first day, then one new kind of work at a time.
SCRIPT = {
    1: [('food', 'mun_kitten'), ('care', 'care_first'), ('tank', 'linh_betta')],
    2: [('screen', 'bin_alone'), ('food', 'tofu_allergy'), ('ret', 'quan_sealed')],
    3: [('lost', 'mun_lost'), ('screen', 'bin_mom'), ('ship', 'hai_litter')],
    4: [('care', 'care_sick_fish'), ('tank', 'sau_community'), ('ret', 'hai_half')],
    5: [('screen', 'sau_adopt')],
}
WEIGHTS = dict(food=4, tank=3, screen=2, care=1, ret=2, lost=1, ship=2)
MIN_DAY = dict(food=1, tank=1, screen=2, care=1, ret=2, lost=3, ship=3)
ADOPTION_EVERY = 7

# The shop grows with the work done well.
STAGES = [
    dict(id=0, name='Tiệm cũ của chú Út', text='Bể cá hơi đục, lồng chật, rổ giảm giá lộn xộn trước quầy.', day=1, good=0),
    dict(id=1, name='Góc nhận nuôi', text='Nhã kê góc nhận nuôi cùng nhóm Chân Nhỏ, dán bảng “Mèo con, cún con chỉ về nhà mới qua góc này”.', day=2, good=2),
    dict(id=2, name='Bể trong, có bể cách ly', text='Bể mới trong veo, thêm một bể cách ly cho bé ốm. Chú Út đứng ngắm, gật gù.', day=4, good=6),
    dict(id=3, name='Ngày hội nhận nuôi', text='Băng rôn “Ngày hội nhận nuôi” treo trước cửa. Cả xóm biết: muốn nuôi thú, ghé tiệm hỏi trước.', day=6, good=12),
]
# The regulars' small stories: (book key, days after, emoji, line). Shown once each in Sổ thú quen.
BOOK_NOTES = [
    ('mun', 2, '🐈', 'Bà Hai ghé khoe: Mun ăn hạt mèo con, bụng tròn vo, đêm nào cũng rượt dép.'),
    ('mun_found', 1, '🔔', 'Mun về nhà rồi. Bà Hai đeo cho nó vòng cổ có số điện thoại của tiệm.'),
    ('bin', 2, '🐹', 'Bin ghé khoe Bánh Bao đã biết chạy bánh xe, chạy tới nửa đêm.'),
    ('bin', 6, '📒', 'Bánh Bao lớn gấp đôi. Bin lập hẳn cuốn sổ ghi cân nặng mỗi tuần.'),
    ('linh', 3, '🐠', 'Uyên gửi ảnh con betta xanh dương tên Mực Xanh. Bàn học có một góc xanh.'),
    ('tofu', 3, '🐕', 'Anh Quân nhắn: Tofu hết ngứa bụng, lông mượt hẳn.'),
    ('map', 2, '🐈', 'Con Mập bớt gãi. Chú Út tự tay dẹp rổ giảm giá “hàng cận date”.'),
    ('vang', 2, '🐕', 'Chú Sáu dắt Vàng đi ngang tiệm, đuôi vẫy tít. Thím nhà chú may cho nó cái nệm.'),
    ('adopt', 1, '🏡', 'Nhóm Chân Nhỏ dán ảnh bé vừa về nhà mới lên bảng. Góc nhận nuôi có thêm một trái tim.'),
]
BOOK_KEYS = ('mun', 'mun_found', 'bin', 'linh', 'tofu', 'map', 'vang', 'adopt')
NOTES_MAX = 16

INTRO = dict(
    title='Giới thiệu nghề',
    lead=f'Nhã, cháu gái chú Út và là sinh viên thú y, nhờ bạn phụ {SHOP}. Tiệm bán thức ăn, đồ dùng, cá, hamster, vẹt; '
         'chó mèo chỉ về nhà mới qua góc nhận nuôi của nhóm Chân Nhỏ.',
    jobs=[('🥣', 'Tư vấn thức ăn đúng loài, đúng tuổi, đúng cỡ, tránh đồ bé dị ứng'),
          ('🐠', 'Setup bể cá: bể đủ lít, có lọc, khử clo, cá hợp nhau'),
          ('🏡', 'Bán thú và nhận nuôi: hỏi kỹ rồi mới giao'),
          ('🧽', 'Chăm thú trong tiệm: cho ăn, thay nước, đo nhiệt, cách ly bé ốm'),
          ('🔁', 'Đổi trả theo quy định của tiệm'),
          ('📌', 'Bảng tìm thú lạc cho cả xóm'),
          ('🛵', 'Giao hàng nặng qua shipper'),
          ('💵', 'Quét từng món, tính tiền, thối tiền')],
    meet=[('🐟', 'Bể quá đông, betta bị thả chung với cá rỉa vây'),
          ('🧒', 'Trẻ con đi mua thú một mình'),
          ('🤒', 'Bé ốm lẫn trong bể chung'),
          ('🥫', 'Rổ giảm giá có lon đã quá hạn'),
          ('🎭', 'Khách trả bao hạt ăn dở “vì chó không thích”'),
          ('📵', 'Người lạ báo “nhặt được thú”, đòi chuyển tiền trước')],
    stars=[('❓', 'Hỏi đủ rồi mới chọn'),
           ('🧾', 'Hóa đơn đúng từng món, thối đủ tiền'),
           ('❤️', 'Thú khỏe là trên hết: chưa hợp thì chưa giao')],
)


# ---------------------------------------------------------------- task generation
def _fresh(job: str, day: int, used: set) -> list:
    return [x for x in VARIANTS[job] if not x['script'] and x['min_day'] <= day and x['id'] not in used]


def _weighted(rows: list, roll: float, weight):
    total = sum(weight(x) for x in rows)
    roll *= total
    for x in rows:
        roll -= weight(x)
        if roll < 0:
            return x
    return rows[-1]


_PLANS: dict = {}


def day_plan(day: int) -> list:
    """(job, variant) for the twelve slots of a day: the script first, then seeded draws that do
    not repeat a variant within the day (one care round a day at most)."""
    if day in _PLANS:
        return _PLANS[day]
    rows = list(SCRIPT.get(day, []))
    used = {v for _, v in rows}
    adoption = day >= ADOPTION_EVERY and day % ADOPTION_EVERY == 0
    for slot in range(len(rows), 12):
        r = kit.rng(ID, 'plan', day, slot)
        care = any(j == 'care' for j, _ in rows)
        if day >= 5 and day % 2 and slot == 0 and not care:
            job = 'care'
        elif adoption and slot in (0, 1):
            job = 'screen'
        else:
            jobs = [j for j in JOBS if MIN_DAY[j] <= day and _fresh(j, day, used) and not (j == 'care' and care)]
            jobs = jobs or [j for j in JOBS if MIN_DAY[j] <= day and j != 'care' and _fresh(j, day, set())]
            job = _weighted(jobs, r.random(), lambda j: WEIGHTS[j])
        pool = _fresh(job, day, used) or _fresh(job, day, set()) or [x for x in VARIANTS[job] if x['min_day'] <= day]
        if job == 'screen' and adoption:
            pool = [x for x in pool if x['needs']['kind'] == 'adopt'] or pool
        pick = _weighted(pool, r.random(), lambda x: x['weight'])
        rows.append((job, pick['id']))
        used.add(pick['id'])
    _PLANS[day] = rows
    if len(_PLANS) > 400:
        _PLANS.pop(next(iter(_PLANS)))
    return rows


def plan(day: int, slot: int) -> tuple[str, str]:
    """(job, variant) of a slot."""
    return day_plan(day)[slot] if 0 <= slot < 12 else day_plan(day)[-1]


def _work(job: str) -> dict:
    return dict(food=dict(dated=False, swapped=False), tank=dict(advice=[]), screen=dict(verdict=None, signed=[]),
                care=dict(fed={}, cleaned={}, read=[], heated=[], looked=[], isolated=[]), ret=dict(decision=None),
                lost=dict(notice=[], pinned=False, calls={}, found=False), ship=dict(shipper=None, cod=None))[job]


def make_task(day: int, slot: int, serial: int) -> dict:
    job, vid = plan(day, slot)
    tpl = VINDEX[job][vid]
    cart = {}
    extra = tpl['needs'].get('extra')
    if extra:
        cart[extra['item']] = extra['qty']
    return kit.base_task(ID, day, slot, serial, tpl['npc'], tpl['title'], tpl['opening'],
                         job=job, variant=vid, needs=copy.deepcopy(tpl['needs']), _x=copy.deepcopy(tpl['x']), gen=1,
                         asked=[], cart=cart, units={}, bill={}, billed=False, cash=None, bill_over=0, bill_under=0,
                         bill_caught=0, work=_work(job), result=[], judged=False, cost=0)


FIXED = ('job', 'needs', '_x', 'gen')


# ---------------------------------------------------------------- data
def initial() -> dict:
    return dict(v=V, intro_seen=False, stage=0, good=0, served=0, welfare=0,
                animals={k: a['target'] for k, a in ANIMALS.items()},
                pens={p: dict(health=90, fed=0, cleaned=0) for p in PENS},
                adopted=[], book={}, fired=[], notes=[], today=_today(), theme=DEFAULT_THEME, themes=[DEFAULT_THEME], ink='auto')


def _today() -> dict:
    return dict(sold=0, good=0, loss=0, tips=0, refunds=0, welfare=0)


def _data(c: dict) -> dict:
    """The career's data, upgraded in place for saves made before a field existed."""
    d = kit.data(c)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k, v in base['animals'].items():
        d['animals'].setdefault(k, v)
    for k, v in base['pens'].items():
        d['pens'].setdefault(k, copy.deepcopy(v))
    for k, v in _today().items():
        d['today'].setdefault(k, v)
    return d


# ---------------------------------------------------------------- helpers
def _idx(t: dict) -> int:
    return int(t['npc'].rsplit('_', 1)[1]) - 1


def _who(t: dict) -> str:
    return NAMES[_idx(t)]


def _price(c: dict, key: str) -> int:
    return kit.price(c, key, PRICES[key])


def _name(key: str, t: dict | None = None) -> str:
    if key in ITEM:
        return ITEM[key]['name']
    if key in ANIMALS:
        coat = coat_name(key, ((t or {}).get('coats') or {}).get(key))
        return ANIMALS[key]['name'] + (f' {coat.lower()}' if coat else '')
    if key == 'adopt' and t is not None and t['needs'].get('pet') in ADOPTEES:
        return f'Nhận nuôi {ADOPTEES[t["needs"]["pet"]]["name"]}'
    return FEE_NAME.get(key, key)


def _emoji(key: str) -> str:
    if key in ITEM:
        return ITEM[key]['emoji']
    if key in ANIMALS:
        return ANIMALS[key]['emoji']
    return '🏡' if key == 'adopt' else '🧾'


def _total(t: dict, rows: dict) -> int:
    return sum(t['units'].get(k, 0) * q for k, q in rows.items())


def _unit(c: dict, t: dict, key: str) -> None:
    t['units'].setdefault(key, _price(c, key))


def _have(c: dict, key: str) -> int:
    if key in ITEM:
        return kit.stock(c, key)
    if key in ANIMALS:
        return _data(c)['animals'].get(key, 0)
    return 1 if key == 'adopt' else 0


def _grab(t: dict) -> dict | None:
    return t['_x'].get('grab') if t['job'] == 'food' else None


def _from_stock(t: dict, key: str) -> int:
    """How many of a cart line must come off the shelves (the customer's own basket cans do not)."""
    q = t['cart'].get(key, 0)
    g = _grab(t)
    if g and key == g['item'] and not t['work']['swapped']:
        q = max(0, q - g['qty'])
    return q


def _done(t: dict) -> bool:
    return t['status'] in ('completed', 'referred', 'cancelled')


def _task(c: dict, p: dict) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm thú cưng.')
    return t


def _start(t: dict) -> None:
    kit.need(t['known'], 'Chào khách, nghe khách nói trước đã nhé.')
    kit.start_work(t)


def _job(t: dict, *jobs) -> None:
    kit.need(t['job'] in jobs, 'Việc này không cần bước đó.')


def _open_bill(t: dict) -> None:
    kit.need(not t['billed'], 'Hóa đơn đã chốt. Bấm “Quét lại” nếu cần sửa trước khi thu tiền.')


def _note(t: dict, line: str) -> None:
    t['result'] = (t['result'] + [line[:300]])[-10:]


def _slip(t: dict, code: str, sev: int, text: str, note: str, safety: bool = False) -> None:
    cq.slip(t, code, sev, text, note, safety)


# ---------------------------------------------------------------- the engine hooks
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    return n.get('request') or t['opening']


def on_task(s: dict, c: dict, t: dict) -> None:
    for key in t['cart']:
        _unit(c, t, key)


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    d['today'] = _today()
    day = c['day']
    # The partner farm tops up the fish, hamsters and budgies before opening (paid at cost).
    bought, cost = [], 0
    for k, a in ANIMALS.items():
        have = d['animals'].get(k, 0)
        if have * 2 < a['target']:
            n = a['target'] - have
            if cost + n * a['cost'] > c['money']:
                n = max(0, (c['money'] - cost) // a['cost'])
            if n:
                d['animals'][k] = have + n
                cost += n * a['cost']
                bought.append(f'{n} {a["name"].lower()}')
    if cost:
        kit.money(s, c, -cost, 'Trại cá Bến Mây giao cá, chim, hamster', None, 'stock')
        _add_note(d, day, '🚚', 'Trại Bến Mây giao thêm: ' + ', '.join(bought) + f' ({cost} xu).')
    # The shop grows with the work done well.
    for st in STAGES:
        if st['id'] > d['stage'] and day >= st['day'] and d['good'] >= st['good'] and d['welfare'] <= st['id'] * 2:
            d['stage'] = st['id']
            _add_note(d, day, '✨', st['name'] + ': ' + st['text'])
            kit.log(s, c, 'story', st['text'])
    # The regulars' small stories carry on.
    for key, after, emoji, line in BOOK_NOTES:
        tag = f'{key}+{after}'
        when = d['book'].get(key)
        if when and day >= when + after and tag not in d['fired']:
            d['fired'] = (d['fired'] + [tag])[-40:]
            _add_note(d, day, emoji, line)


def _add_note(d: dict, day: int, emoji: str, text: str) -> None:
    d['notes'] = (d['notes'] + [dict(day=day, emoji=emoji, text=text[:240])])[-NOTES_MAX:]


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    lines = []
    for t in c['tasks']:
        if t.get('career') != ID or t.get('job') != 'care' or _done(t) or t['day'] != c['day']:
            continue
        # Nobody finished the rounds: the animals wait until tomorrow.
        for pen in t['_x']['pens']:
            if pen not in t['work']['fed']:
                d['pens'][pen]['health'] = max(0, d['pens'][pen]['health'] - 15)
        sick = t['_x']['sick']
        if sick and sick not in t['work']['isolated']:
            d['welfare'] += 1
            d['today']['welfare'] += 1
            d['pens'][sick]['health'] = max(0, d['pens'][sick]['health'] - 25)
            lines.append(f'Bé ốm ở {PENS[sick]["name"].lower()} chưa được cách ly qua đêm. Mai có thể có người tới kiểm tra.')
            box = c.get('incidents')
            if isinstance(box, dict) and isinstance(box.get('follow'), list):
                from .. import incidents as incs
                incs._schedule(box, (INSPECT, 1), c['day'], t['id'])
        else:
            lines.append('Vòng chăm thú hôm nay chưa xong, các bé đói bụng chờ tới mai.')
    x = d['today']
    if x['sold']:
        lines.append(f'Bán được {x["sold"]} đơn, {x["good"]} đơn trọn vẹn.')
    if x['loss']:
        lines.append(f'Chú Út kiểm két: hụt {x["loss"]} xu vì tính thiếu, thối dư hoặc nhận đổi trả không đúng.')
    if x['tips']:
        lines.append(f'Khách thương, cho thêm {x["tips"]} xu.')
    if x['welfare']:
        lines.append('Nhã dặn: thú khỏe là trên hết. Ngày mai soi kỹ từng bể nhé.')
    return dict(lines=lines, note=STAGES[d['stage']]['name'])


# ---------------------------------------------------------------- actions
FREE = ('ps_intro', 'ps_paint', 'ps_ink')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'ps_intro':
        d['intro_seen'] = True
        return dict(message='Nhã cười: “Có gì chưa rõ cứ hỏi chị nha!”')
    if name == 'ps_paint':
        return _paint(s, c, d, p)
    if name == 'ps_ink':
        ink = kit.one_of(p.get('ink'), tuple(INKS), 'Chọn một màu chữ cho biển hiệu nhé.')
        d['ink'] = ink
        return dict(message=f'Chữ trên biển hiệu đổi sang {INKS[ink][0].lower()}.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở tiệm thú cưng.')
    t = _task(c, p)
    kit.need(not _done(t), 'Việc này đã xong.')
    return fn(s, c, t, p)


def _paint(s, c, d, p):
    theme = kit.one_of(p.get('theme'), tuple(THEME), 'Chọn một màu sơn trong bảng nhé.')
    kit.need(theme != d['theme'], 'Tiệm đang sơn màu này rồi.')
    x = THEME[theme]
    paid = 0
    if theme not in d['themes'] and x['stage'] > d['stage']:
        paid = x['cost']
        kit.need(c['money'] >= paid, f'Sơn “{x["name"]}” cần {paid} xu, quỹ tiệm chưa đủ.')
        kit.money(s, c, -paid, f'Mua sơn “{x["name"]}” cho tiệm', None, 'upgrade')
    if theme not in d['themes']:
        d['themes'] = (d['themes'] + [theme])[-len(THEMES):]
    d['theme'] = theme
    tail = f' Hết {paid} xu tiền sơn.' if paid else ''
    return dict(message=f'Chú Út với Nhã sơn lại tiệm màu {x["name"].lower()}.{tail}')


def _coat(s, c, t, p):
    _start(t)
    _job(t, 'tank', 'screen')
    _open_bill(t)
    kind = kit.one_of(p.get('kind'), tuple(COATS), 'Con này không có màu để chọn.')
    kit.need(t['cart'].get(kind), f'Đặt {ANIMALS[kind]["name"].lower()} lên quầy trước rồi chọn màu nhé.')
    coat = kit.one_of(p.get('coat'), tuple(COAT[kind]), 'Màu này tiệm không có.')
    t.setdefault('coats', {})[kind] = coat
    t['units'][kind] = _price(c, kind) + COAT[kind][coat][4]
    extra = COAT[kind][coat][4]
    return dict(message=f'Vớt {ANIMALS[kind]["name"].lower()} màu {COAT[kind][coat][1].lower()}' + (f' (màu hiếm, thêm {extra} xu mỗi con).' if extra else '.'))


def _coat_slips(t: dict) -> None:
    """The customer asked for a colour: the wrong one (or one grabbed at random) is a mild complaint."""
    for kind, want in (t['needs'].get('coat') or {}).items():
        if not t['cart'].get(kind):
            continue
        got = (t.get('coats') or {}).get(kind)
        if got != want:
            what = ANIMALS[kind]['name'].lower()
            given = f'con màu {COAT[kind][got][1].lower()}' if got else 'con nào vớt được thì đưa'
            _slip(t, 'wrong_coat', 1, f'Tôi dặn {what} màu {COAT[kind][want][1].lower()} mà tiệm đưa {given}.', 'sai màu khách dặn')


def _ask(s, c, t, p):
    _start(t)
    topics = TOPICS[t['job']]
    topic = kit.one_of(p.get('topic'), tuple(topics), 'Câu hỏi này không hợp với việc đang làm.')
    kit.need(topic not in t['asked'], 'Đã hỏi điều này rồi.')
    t['asked'].append(topic)
    t['inspected'] = (t['inspected'] + [topic])[-12:]
    answer = t['_x']['a'][topic]
    if t['job'] == 'ret':
        return dict(message=f'{topics[topic][1]}: {answer}')
    return dict(message=f'{_who(t)}: “{answer}”')


# ----- cart & bill (the till)
def _cart(s, c, t, p):
    _start(t)
    _open_bill(t)
    key = kit.one_of(p.get('key'), CART_KEYS, 'Món này tiệm không bán.')
    qty = kit.integer(p.get('qty'), 0, 20)
    kit.need(key != 'adopt' or (t['job'] == 'screen' and t['needs']['kind'] == 'adopt'), 'Chỉ nhận nuôi qua góc nhận nuôi.')
    kit.need(key not in ANIMALS or t['job'] in ('tank', 'screen'), 'Bán cá, chim, hamster ở phần setup bể hoặc bán thú nhé.')
    if t['job'] == 'screen':
        kit.need(t['work']['verdict'] == 'sell', 'Hỏi kỹ rồi quyết định có giao bé hay không trước đã.')
    g = _grab(t)
    base = g['qty'] if g and key == g['item'] and not t['work']['swapped'] else 0
    kit.need(qty >= base or qty == 0, 'Mấy lon khách tự lấy trong rổ: kiểm hạn rồi đổi lon mới, hoặc bỏ ra hẳn.')
    if qty == 0 and base:
        t['work']['swapped'] = True   # the basket cans go back to the basket
    if qty - base > 0:
        kit.need(_have(c, key) >= qty - base, f'Hết {_name(key, t).lower()} rồi. Mở Kho nhập thêm nhé.')
    if qty:
        t['cart'][key] = qty
        _unit(c, t, key)
    else:
        t['cart'].pop(key, None)
    return dict(message=f'{_name(key, t)}: {qty}' if qty else f'Đã bỏ {_name(key, t).lower()} khỏi quầy.')


def _food(s, c, t, p):
    _start(t)
    _job(t, 'food')
    _open_bill(t)
    item = kit.one_of(p.get('item'), MAIN_FOODS, 'Chọn một loại thức ăn trên kệ nhé.')
    qty = t['needs']['qty']
    kit.need(kit.stock(c, item) >= qty, f'Kệ hết {ITEM[item]["name"].lower()}. Mở Kho nhập thêm nhé.')
    for k in [k for k in t['cart'] if k in MAIN_FOODS]:
        t['cart'].pop(k)
    t['cart'][item] = qty
    _unit(c, t, item)
    return dict(message=f'Đặt lên quầy: {qty} × {ITEM[item]["name"]} ({FOODS[item]["label"]}).')


def _date(s, c, t, p):
    _start(t)
    g = _grab(t)
    kit.need(g, 'Khách không lấy gì trong rổ giảm giá.')
    kit.need(not t['work']['dated'], 'Đã xem hạn rồi.')
    t['work']['dated'] = True
    return dict(message=g['label'])


def _swap(s, c, t, p):
    _start(t)
    _open_bill(t)
    g = _grab(t)
    kit.need(g and not t['work']['swapped'], 'Không có lon nào cần đổi.')
    kit.need(kit.stock(c, g['item']) >= g['qty'], f'Kệ không đủ {ITEM[g["item"]]["name"].lower()} mới để đổi. Mở Kho nhập thêm nhé.')
    t['work']['swapped'] = True
    t['cart'][g['item']] = max(t['cart'].get(g['item'], 0), g['qty'])
    _unit(c, t, g['item'])
    value = g['qty'] * ITEM[g['item']]['cost']
    kit.waste(c, g['item'], g['qty'], value, 'Lon quá hạn trong rổ giảm giá')
    return dict(message=f'Bạn cất mấy lon quá hạn, lấy {g["qty"]} lon mới trên kệ. {_who(t)} gật gù: “Vậy mới yên tâm.”')


def _tank(s, c, t, p):
    _start(t)
    _job(t, 'tank')
    _open_bill(t)
    size = kit.one_of(p.get('size'), tuple(TANKS), 'Chọn một cỡ bể nhé.')
    kit.need(kit.stock(c, size) >= 1, f'Hết {ITEM[size]["name"].lower()}. Mở Kho nhập thêm nhé.')
    for k in TANKS:
        t['cart'].pop(k, None)
    t['cart'][size] = 1
    _unit(c, t, size)
    return dict(message=f'Chọn {ITEM[size]["name"].lower()}.')


def _advice(s, c, t, p):
    _start(t)
    _job(t, 'tank')
    tips = kit.id_list(p.get('tips'), tuple(TIPS), 6, 'Chọn lời dặn trong danh sách nhé.')
    t['work']['advice'] = tips
    return dict(message='Đã dặn khách: ' + '; '.join(TIPS[x][1].lower() for x in tips) + '.' if tips else 'Chưa dặn gì.')


def _scan(s, c, t, p):
    _start(t)
    _job(t, *TILL_JOBS, 'ship')
    _open_bill(t)
    key = kit.one_of(p.get('key'), CART_KEYS, 'Mã này không có trong máy tính tiền.')
    qty = kit.integer(p.get('qty', 1), 1, 20)
    kit.need(t['bill'].get(key, 0) + qty <= 40, 'Hóa đơn quá dài rồi.')
    t['bill'][key] = t['bill'].get(key, 0) + qty
    _unit(c, t, key)
    return dict(message=f'Tít! {qty} × {_name(key, t)} · {t["units"][key] * qty} xu. Tạm tính {_total(t, t["bill"])} xu.')


def _void(s, c, t, p):
    _start(t)
    _open_bill(t)
    key = kit.one_of(p.get('key'), tuple(t['bill']), 'Dòng này chưa có trên hóa đơn.')
    t['bill'][key] -= 1
    if not t['bill'][key]:
        del t['bill'][key]
    return dict(message=f'Bớt một {_name(key, t).lower()}. Tạm tính {_total(t, t["bill"])} xu.')


def _ready(c: dict, t: dict) -> None:
    """What must be on the counter before the total."""
    kit.need(t['cart'], 'Trên quầy chưa có món nào.')
    if t['job'] == 'food':
        kit.need(any(k in MAIN_FOODS for k in t['cart']), 'Chọn một loại thức ăn cho bé trước đã.')
    if t['job'] == 'tank':
        kit.need(any(k in TANKS for k in t['cart']), 'Chọn cỡ bể trước đã.')
        kit.need(any(k in FISH for k in t['cart']), 'Chọn cá cho bể trước đã.')
    if t['job'] == 'screen':
        kit.need(t['work']['verdict'] == 'sell', 'Chỉ tính tiền khi đã đồng ý giao bé.')
        pet = t['needs']['pet']
        kit.need(t['cart'].get('adopt' if t['needs']['kind'] == 'adopt' else pet, 0) == 1, 'Đặt bé lên quầy trước đã (một bé thôi).')
        if t['needs']['kind'] == 'adopt':
            kit.need(t['work']['signed'], 'Làm giấy nhận nuôi với nhóm Chân Nhỏ trước đã.')
    for k in t['cart']:
        n = _from_stock(t, k)
        if n:
            kit.need(_have(c, k) >= n, f'Không đủ {_name(k, t).lower()} trên kệ. Mở Kho nhập thêm nhé.')


def _total_act(s, c, t, p):
    _start(t)
    _job(t, *TILL_JOBS, 'ship')
    _open_bill(t)
    _ready(c, t)
    kit.need(t['bill'], 'Quét từng món trên quầy vào hóa đơn trước đã.')
    billed, due = _total(t, t['bill']), _total(t, t['cart'])
    who = _who(t)
    present = t['job'] != 'ship'
    if billed > due:
        over = billed - due
        if present and (till._persona(c, t) in till.CAREFUL or kit.rng(ID, 'bill-check', t['id'], t['bill_caught']).random() < 0.5):
            t['bill_caught'] += 1
            t['mistakes'] += 1
            return dict(message=f'{who} dò lại hóa đơn: “Sao tính {billed} xu? Trên quầy chỉ có {due} xu hàng thôi mà.” Quét lại cho đúng nhé.',
                        correct=False)
        t['bill_over'] = over
    elif billed < due:
        if present and till.honest(c, t) and not t['bill_under']:
            t['mistakes'] += 1
            t['bill_under'] = -1   # already pointed out once
            return dict(message=f'{who} nhìn hóa đơn: “Ủa, còn món chưa tính nè, {billed} xu là thiếu đó.” Quét lại cho đủ nhé.', correct=False)
        t['bill_under'] = due - billed
    else:
        t['bill_under'] = 0 if t['bill_under'] == -1 else t['bill_under']
    t['billed'] = True
    if t['job'] == 'ship':
        return dict(message=f'Chốt hóa đơn {billed} xu. Giờ chọn shipper và ghi tiền thu hộ.')
    t['cash'] = till.new(billed, t['id'], c=c, t=t)
    paid = sum(t['cash']['tender'])
    return dict(message=f'Chốt hóa đơn {billed} xu. {who} đưa {paid} xu.')


def _rescan(s, c, t, p):
    _start(t)
    kit.need(t['billed'], 'Hóa đơn chưa chốt.')
    kit.need(t['cash'] is None or (t['cash']['outcome'] is None and not t['cash']['asked']), 'Tiền đã đưa qua lại rồi, không quét lại được nữa.')
    kit.need(t['job'] != 'ship' or t['work']['cod'] is None, 'Đã ghi tiền thu hộ rồi.')
    t['billed'] = False
    t['cash'] = None
    t['bill_over'] = 0
    t['bill_under'] = 0 if t['bill_under'] >= 0 else -1
    return dict(message=f'“Dạ để em quét lại cho chắc.” {_who(t)} gật đầu chờ.')


def _handover(s, c, t, p):
    _start(t)
    _job(t, *TILL_JOBS)
    kit.need(t['billed'] and t['cash'], 'Chốt hóa đơn trước khi nhận tiền nhé.')
    rec, who = t['cash'], _who(t)
    chk = till.check(s, c, t, rec, p.get('change', []), who)
    if chk['stop']:
        return dict(message=chk['message'], correct=False)
    _judge(c, t)
    r = cq.react(s, c, t, rec['price'], who=who)
    st = till.settle(s, c, t, rec, r, who)
    _sell(c, t, r['kind'] in ('refuse', 'walkout'))
    loss = st['loss'] + max(0, t['bill_under'])
    pay = max(0, r['pay'] - st['loss'])
    return _finish(s, c, t, pay, r, extra=st['message'], loss=loss, later=True)


def _finish(s, c, t, pay: int, r: dict, extra: str = '', loss: int = 0, tip: int = 0, later: bool = False) -> dict:
    d = _data(c)
    who = _who(t)
    parts = []
    if cq.slips(t) and r.get('message'):
        parts.append(('Mấy hôm sau, ' if later else '') + r['message'])
    if t['bill_over']:
        parts.append(f'Hóa đơn tính dư {t["bill_over"]} xu so với hàng khách lấy.')
    if t['bill_under'] > 0:
        parts.append(f'Tối kiểm két: quét sót {t["bill_under"]} xu hàng, tiệm chịu.')
    if extra:
        parts.append(extra)
    good = not cq.slips(t) and not t['bill_over'] and t['bill_under'] <= 0
    if good:
        d['good'] += 1
        d['today']['good'] += 1
        parts.insert(0, OK_LINES[t['job']].format(who=who, pet=t['needs'].get('pet', '')))
    d['served'] += 1
    if t['job'] in TILL_JOBS or t['job'] == 'ship':
        d['today']['sold'] += 1
    d['today']['loss'] += loss
    d['today']['tips'] += t.get('tip_given', 0) or tip
    if cq.safety(t):
        d['welfare'] += 1
        d['today']['welfare'] += 1
    _book(c, t, good)
    msg = ' '.join(x for x in parts if x).strip() or 'Xong việc.'
    for line in parts:
        _note(t, line)
    t['judged'] = True
    kit.complete(s, c, t, pay, f'{JOB_NAMES[t["job"]]} cho {who}: ' + ('trọn vẹn.' if good else 'còn sai sót.'))
    return dict(message=msg, celebrate=good)


OK_LINES = dict(
    food='{who} ôm túi hạt ra cửa: “Vậy mà trước giờ cứ mua đại!”',
    tank='{who} ngắm bể mới: “Đẹp mà nhìn biết là cá sống khỏe.”',
    screen='{who} ra về, vui mà yên tâm.',
    care='Các bé no bụng, bể trong, chuồng thơm. {who} gật gù.',
    ret='{who} hiểu chuyện, ra về không cằn nhằn.',
    lost='Tờ tìm thú làm đúng cách. {who} cảm ơn rối rít.',
    ship='Hàng tới đúng chỗ, đúng giờ, đúng tiền. {who} nhắn cảm ơn.',
)


def _sell(c: dict, t: dict, back: bool) -> None:
    """The goods leave the shop. If the customer brought them back, animals return to their pens
    and opened goods are thrown away."""
    d = _data(c)
    for k, q in t['cart'].items():
        n = _from_stock(t, k)
        if not n:
            continue
        if k in ITEM:
            cost = kit.take(c, k, n)
            t['cost'] += cost
            if back:   # opening stock carries no recorded cost, so count what the item is worth
                kit.waste(c, k, n, cost or ITEM[k]['cost'] * n, 'Khách mang trả, hàng đã mở')
        elif k in ANIMALS:
            if not back:
                d['animals'][k] = max(0, d['animals'][k] - n)
        elif k == 'adopt' and not back:
            d['adopted'] = (d['adopted'] + [dict(pet=t['needs']['pet'], day=c['day'])])[-20:]


def _book(c: dict, t: dict, good: bool) -> None:
    d = _data(c)
    if not good:
        return
    day = c['day']
    v = t['variant']
    key = dict(mun_kitten='mun', bin_mom='bin', linh_betta='linh', tofu_allergy='tofu', map_fish='map', sau_adopt='vang').get(v)
    if key and key not in d['book']:
        d['book'][key] = day
    if t['job'] == 'screen' and t['needs']['kind'] == 'adopt' and t['work']['verdict'] == 'sell':
        d['book']['adopt'] = day
    if v == 'mun_lost' and t['work']['found']:
        d['book']['mun_found'] = day


# ----- judging (once, at the hand-over)
def _judge(c: dict, t: dict) -> None:
    if t['judged']:
        return
    t['judged'] = True
    {'food': _judge_food, 'tank': _judge_tank, 'screen': _judge_screen, 'ship': _judge_ship}.get(t['job'], lambda c, t: None)(c, t)
    if t['bill_over']:
        _slip(t, 'overcharged', 2, f'Về nhà xem lại hóa đơn mới thấy bị tính dư {t["bill_over"]} xu.', f'tính dư {t["bill_over"]} xu')
    if t['bill_caught']:
        _slip(t, 'bill_caught', 1, 'Hóa đơn tính sai, tôi phải dò lại mới ra.', 'tính tiền sai, khách phải nhắc')


def _judge_food(c: dict, t: dict) -> None:
    n, x = t['needs'], t['_x']
    pet = n['pet']
    mains = [k for k in t['cart'] if k in MAIN_FOODS]
    for k in mains:
        f = FOODS[k]
        if x['allergy'] and f['protein'] == x['allergy']:
            _slip(t, 'allergy', 3, f'{pet} ăn {ITEM[k]["name"].lower()} về là ngứa đỏ, phải chạy qua {VET}. Tôi đã nói bé dị ứng {PROTEIN[x["allergy"]]} mà!',
                  f'bán đồ có {PROTEIN[x["allergy"]]} cho bé dị ứng', True)
        elif f['species'] != n['species']:
            _slip(t, 'species', 3, f'Thức ăn cho {SPECIES[f["species"]].lower()} mà bán cho {pet}. Bé ăn vô đau bụng mấy hôm.',
                  f'bán nhầm thức ăn của {SPECIES[f["species"]].lower()}')
        elif f['stage'] != 'any' and f['stage'] != x['stage']:
            _slip(t, 'stage', 2, f'Hạt không hợp tuổi của {pet}, về ăn không hợp, lại phải mua bao khác.',
                  f'sai lứa tuổi: {STAGE[f["stage"]].lower()} cho bé {STAGE[x["stage"]].lower()}')
        elif f['size'] != 'any' and x['size'] != 'any' and f['size'] != x['size']:
            _slip(t, 'size', 1, f'Hạt không hợp cỡ người của {pet}, bé nhai hơi cực.', 'sai cỡ chó')
        if len(mains) > 1:
            break
    if mains and t['cart'][mains[0]] != n['qty']:
        _slip(t, 'qty', 1, f'Tôi dặn {n["qty"]} túi mà tiệm đưa {t["cart"][mains[0]]}.', 'sai số lượng')
    g = x.get('grab')
    if g and t['cart'].get(g['item']) and not t['work']['swapped'] and g['expired']:
        _slip(t, 'expired', 3, f'Mấy lon {ITEM[g["item"]]["name"].lower()} trong rổ giảm giá đã quá hạn, lon còn phồng. Bé ăn vô ói cả đêm.',
              'bán lon pate quá hạn', True)


def tank_problems(cart: dict) -> list:
    """What is wrong with a tank on the counter (shared with the client's load meter)."""
    out = []
    size = next((k for k in TANKS if cart.get(k)), None)
    fish = {k: cart.get(k, 0) for k in FISH if cart.get(k)}
    if not size or not fish:
        return out
    load = sum(ANIMALS[k]['litres'] * q for k, q in fish.items())
    if load > TANKS[size]:
        out.append(('crowded', 3, True, f'Bể {TANKS[size]} lít mà thả cá cần {load} lít nước. Mấy hôm sau cá nổi đầu, chết mất mấy con.',
                    f'bể quá tải: {load}/{TANKS[size]} lít'))
    if fish.get('betta', 0) >= 2:
        out.append(('betta_fight', 3, True, 'Hai con betta thả chung, sáng ra con nào cũng rách vây.', 'thả hai betta chung bể'))
    if fish.get('betta') and fish.get('barb'):
        out.append(('fin_nip', 3, True, 'Betta đuôi dài thả chung cá tứ vân, mấy hôm đuôi bị rỉa tả tơi.', 'betta chung cá rỉa vây'))
    if fish.get('goldfish') and any(fish.get(k) for k in ('guppy', 'betta', 'barb')):
        out.append(('temp_mix', 3, True, 'Cá vàng ưa nước mát lại thả chung cá nhiệt đới, bể nào cũng có con bệnh.', 'cá vàng chung cá nhiệt đới'))
    if (fish.get('goldfish') or TANKS[size] >= 30) and not cart.get('filter'):
        out.append(('no_filter', 2, False, 'Bể không có lọc, ba hôm nước đục ngầu, cá thở hổn hển.', 'bể thiếu lọc'))
    if not cart.get('conditioner'):
        out.append(('chlorine', 2, False, 'Về đổ nước máy vào bể, cá lờ đờ cả buổi. Không ai dặn khử clo.', 'không có dung dịch khử clo'))
    return out


def _judge_tank(c: dict, t: dict) -> None:
    for code, sev, safety, text, note in tank_problems(t['cart']):
        _slip(t, code, sev, text, note, safety)
    keep = t['needs']['keep']
    if any(t['cart'].get(k, 0) < q for k, q in keep.items()):
        _slip(t, 'not_wanted', 2, 'Tôi muốn nuôi con đó nhất mà tiệm lại không bán.', 'bỏ mất con cá khách muốn nhất')
    _coat_slips(t)
    adv = t['work']['advice']
    if any(x not in GOOD_TIPS for x in adv):
        _slip(t, 'bad_advice', 2, 'Tiệm dặn sai cách chăm, làm theo mà cá yếu hẳn.', 'dặn sai cách chăm cá')
    elif not {'float', 'part'} <= set(adv):
        _slip(t, 'no_advice', 1, 'Không ai dặn cách thả cá với thay nước, tôi phải lên mạng hỏi.', 'không dặn cách thả cá, thay nước')


def _judge_screen(c: dict, t: dict) -> None:
    n, x, w = t['needs'], t['_x'], t['work']
    if w['verdict'] not in x['ok']:
        if w['verdict'] == 'sell':
            _slip(t, 'careless_sale', 3, SALE_REGRET.get(t['variant'], 'Tiệm giao bé mà không hỏi han gì. Mấy hôm sau phải mang trả lại.'),
                  'giao thú cho người chưa sẵn sàng', True)
        else:
            _slip(t, 'turned_away', 2, 'Nhà có chỗ, có người ở nhà cả ngày mà tiệm không cho nhận.', 'từ chối người đủ điều kiện')
        return
    if w['verdict'] != 'sell':
        return
    if n['kind'] == 'sale':
        _coat_slips(t)
        missing = [k for k in KIT.get(n['pet'], ()) if not t['cart'].get(k)]
        if missing:
            _slip(t, 'no_kit', 2, f'Về tới nhà mới biết thiếu {", ".join(ITEM[k]["name"].lower() for k in missing)}. Bé phải ở tạm trong thùng giấy.',
                  'thiếu đồ dùng cho bé')
    elif set(w['signed']) != set(SIGNS):
        _slip(t, 'papers', 1, 'Giấy nhận nuôi làm vội, về mới biết chưa có lịch tiêm tiếp theo.', 'giấy nhận nuôi thiếu mục')


SALE_REGRET = dict(
    bin_alone='Mấy hôm sau mẹ Bin mang lồng trả lại: nhà chưa ai đồng ý, con mèo Bơ rình chuồng suốt đêm.',
    linh_kitten='Chủ trọ phát hiện có mèo, bắt Uyên mang trả bé trong ngày. Bé Sữa về lại góc nhận nuôi, sợ người hơn trước.',
    quan_budgie='Mẹ anh Quân lên cơn hen vì lông chim, con vẹt phải gửi lại tiệm.',
    quan_puppy='Đậu ở nhà một mình mười hai tiếng, Tofu gầm gừ suốt. Hàng xóm báo tổ dân phố vì chó sủa cả ngày.',
)


def _judge_ship(c: dict, t: dict) -> None:
    n, x, w = t['needs'], t['_x'], t['work']
    if t['cart'] != n['order']:
        _slip(t, 'wrong_items', 2, 'Hàng giao tới thiếu món, dư món, không đúng như tôi đặt.', 'đóng sai đơn')
    if 'confirm' not in t['asked']:
        _slip(t, 'wrong_address', 2, 'Shipper chạy lòng vòng cả tiếng vì sai địa chỉ, tôi đứng chờ ngoài hẻm.', 'không xác nhận địa chỉ')
    kg10 = sum(KG10.get(k, 0) * q for k, q in t['cart'].items())
    glass = any(t['cart'].get(k) for k in BIG_GLASS)
    if w['shipper'] == 'bike':
        if glass:
            _slip(t, 'tank_broke', 3, 'Bể kính chở xe máy, tới nơi nứt một đường. Tiệm phải giao lại cái khác.', 'chở bể kính lớn bằng xe máy')
        elif kg10 > BIKE_MAX10:
            _slip(t, 'bike_heavy', 2, f'Xe máy chở {_kg(kg10)} ký, bao rách giữa đường, đồ đổ tè le.', 'xe máy chở quá nặng')
    elif w['shipper'] == 'van' and not glass and kg10 <= BIKE_MAX10:
        _slip(t, 'van_costly', 1, 'Có mấy món nhẹ mà gọi xe tải, phí ship đắt gấp ba.', 'gọi xe tải cho đơn nhẹ')


# ----- screening
def _verdict(s, c, t, p):
    _start(t)
    _job(t, 'screen')
    w = t['work']
    kit.need(w['verdict'] is None, 'Đã quyết định rồi.')
    v = kit.one_of(p.get('verdict'), tuple(VERDICTS), 'Chọn: giao bé, hẹn quay lại, hoặc từ chối.')
    w['verdict'] = v
    if t['_x']['key'] not in t['asked']:
        t['mistakes'] += 1   # decided before hearing what mattered most
    if v == 'sell':
        pet = t['needs']['pet']
        if t['needs']['kind'] == 'adopt':
            return dict(message=f'Đồng ý giao bé {ADOPTEES[pet]["name"]}. Làm giấy nhận nuôi với nhóm Chân Nhỏ rồi tính phí nhé.')
        return dict(message=f'Đồng ý bán {ANIMALS[pet]["name"].lower()}. Đặt bé và đồ dùng cần thiết lên quầy nhé.')
    t['judged'] = True
    _judge_screen(c, t)
    r = cq.react(s, c, t, 0, who=_who(t))
    line = LATER_LINES.get(t['variant'], 'Khách gật đầu, hẹn hôm khác quay lại.') if v in t['_x']['ok'] else ''
    return _finish(s, c, t, 0, r, extra=line)


LATER_LINES = dict(
    bin_alone='Bin xụ mặt, rồi gật đầu: “Mai con dẫn mẹ tới!”',
    linh_kitten='Uyên ngồi ngắm bé Sữa thêm chút nữa: “Em xin ảnh bé nha. Mai em ghé coi bể cá.”',
    quan_budgie='Anh Quân gãi đầu: “Ừ ha, mẹ anh bị hen. Để anh hỏi mẹ đã.”',
    quan_puppy='Anh Quân thở dài: “Em nói đúng, Tofu ở nhà một mình đã buồn rồi. Anh sẽ về sớm hơn.”',
)


def _sign(s, c, t, p):
    _start(t)
    _job(t, 'screen')
    kit.need(t['needs']['kind'] == 'adopt' and t['work']['verdict'] == 'sell', 'Chỉ làm giấy khi đã đồng ý giao bé nhận nuôi.')
    _open_bill(t)
    checks = kit.id_list(p.get('checks'), tuple(SIGNS), 3, 'Chọn các mục trong giấy nhận nuôi nhé.')
    kit.need(checks, 'Đánh dấu ít nhất một mục.')
    t['work']['signed'] = checks
    if 'adopt' not in t['cart']:
        t['cart']['adopt'] = 1
        _unit(c, t, 'adopt')
    return dict(message=f'Ký giấy nhận nuôi ({len(checks)}/{len(SIGNS)} mục). Anh Khánh chụp ảnh gửi nhóm.')


# ----- care rounds
def _pen(t: dict, p: dict) -> str:
    return kit.one_of(p.get('pen'), tuple(t['_x']['pens']), 'Chuồng, bể này không có trong vòng chăm hôm nay.')


def _feed(s, c, t, p):
    _start(t)
    _job(t, 'care')
    pen = _pen(t, p)
    portion = kit.one_of(p.get('portion'), tuple(PORTIONS), 'Chọn khẩu phần nhé.')
    kit.need(pen not in t['work']['fed'], 'Đã cho ăn rồi.')
    t['work']['fed'][pen] = portion
    return dict(message=f'{PENS[pen]["name"]}: {PORTIONS[portion].lower()}.')


def _clean(s, c, t, p):
    _start(t)
    _job(t, 'care')
    pen = _pen(t, p)
    how = kit.one_of(p.get('how'), tuple(CLEANS), 'Chọn cách dọn nhé.')
    kit.need(pen not in t['work']['cleaned'], 'Đã dọn rồi.')
    t['work']['cleaned'][pen] = how
    if PENS[pen]['kind'] == 'cage' and how == 'all' and kit.stock(c, 'bedding'):
        t['cost'] += kit.take(c, 'bedding', 1)   # fresh bedding from the shop's shelf
    return dict(message=f'{PENS[pen]["name"]}: {CLEANS[how].lower()}.')


def _temp(s, c, t, p):
    _start(t)
    _job(t, 'care')
    pen = _pen(t, p)
    kit.need(PENS[pen]['kind'] == 'fish', 'Chỉ đo nhiệt độ nước ở bể cá.')
    kit.need(pen not in t['work']['read'], 'Đã đo rồi.')
    t['work']['read'].append(pen)
    return dict(message=f'{PENS[pen]["name"]}: {_temp_of(t, pen)}°C.')


def _temp_of(t: dict, pen: str) -> int:
    water = PENS[pen]['water']
    if pen in t['work']['heated']:
        return TEMP_NORMAL[water] if pen == t['_x']['cold'] else TEMP_NORMAL[water] + (4 if water == 'cool' else 1)
    return 22 if pen == t['_x']['cold'] else TEMP_NORMAL[water]


def _heat(s, c, t, p):
    _start(t)
    _job(t, 'care')
    pen = _pen(t, p)
    kit.need(PENS[pen]['kind'] == 'fish', 'Chỉ bể cá mới có sưởi.')
    kit.need(pen not in t['work']['heated'], 'Đã chỉnh sưởi rồi.')
    t['work']['heated'].append(pen)
    return dict(message=f'Bật lại sưởi {PENS[pen]["name"].lower()}, chỉnh nấc 27°C.')


def _look(s, c, t, p):
    _start(t)
    _job(t, 'care')
    pen = _pen(t, p)
    kit.need(pen not in t['work']['looked'], 'Đã soi kỹ rồi.')
    t['work']['looked'].append(pen)
    return dict(message=f'{PENS[pen]["name"]}: {_sign_of(t, pen)}')


def _sign_of(t: dict, pen: str) -> str:
    if pen == t['_x']['sick']:
        return t['_x']['sign']
    return 'Bơi lội, ăn uống bình thường.' if PENS[pen]['kind'] == 'fish' else 'Lanh lợi, mắt sáng, lông mượt.'


def _isolate(s, c, t, p):
    _start(t)
    _job(t, 'care')
    pen = _pen(t, p)
    kit.need(pen not in t['work']['isolated'], 'Đã cách ly rồi.')
    t['work']['isolated'].append(pen)
    where = 'bể cách ly' if PENS[pen]['kind'] == 'fish' else 'lồng cách ly'
    return dict(message=f'Chuyển bé ở {PENS[pen]["name"].lower()} sang {where}, ghi sổ nhờ Nhã xem, cần thì đưa qua {VET}.')


def _care_done(s, c, t, p):
    _start(t)
    _job(t, 'care')
    x, w = t['_x'], t['work']
    kit.need(w['fed'] or w['cleaned'], 'Chưa làm việc nào trong vòng chăm.')
    t['judged'] = True
    fish_heap = [pen for pen, v in w['fed'].items() if PENS[pen]['kind'] == 'fish' and v == 'heap']
    cage_low = [pen for pen, v in w['fed'].items() if PENS[pen]['kind'] == 'cage' and v != 'normal']
    unfed = [pen for pen in x['pens'] if pen not in w['fed']]
    if unfed:
        _slip(t, 'unfed', 2, f'{", ".join(PENS[q]["name"] for q in unfed)} chưa ai cho ăn, mấy bé đói meo.', 'bỏ đói ' + ', '.join(PENS[q]['name'].lower() for q in unfed))
    if fish_heap:
        _slip(t, 'overfeed', 1, 'Đổ cám cả nắm, thức ăn thừa làm nước đục ngầu.', 'cho cá ăn quá nhiều')
    if cage_low:
        _slip(t, 'wrong_portion', 1, 'Khẩu phần không đúng, bé ăn không đủ no.', 'sai khẩu phần')
    dirty = [pen for pen in x['dirty'] if pen not in w['cleaned']]
    if dirty:
        _slip(t, 'dirty', 1, f'{", ".join(PENS[q]["name"] for q in dirty)} bẩn mà không ai dọn, mùi tới tận cửa.', 'để chuồng, bể bẩn')
    shock = [pen for pen, v in w['cleaned'].items() if PENS[pen]['kind'] == 'fish' and v == 'all']
    if shock:
        _slip(t, 'water_shock', 2, 'Thay sạch trơn nước một lần, cá sốc nước nằm im dưới đáy.', 'thay toàn bộ nước bể cá')
    half = [pen for pen, v in w['cleaned'].items() if PENS[pen]['kind'] == 'cage' and v == 'part']
    if half:
        _slip(t, 'half_clean', 1, 'Chuồng chỉ lau qua loa, lót cũ vẫn ẩm.', 'dọn chuồng qua loa')
    if x['cold'] and x['cold'] not in w['heated']:
        _slip(t, 'cold', 2, f'{PENS[x["cold"]]["name"]} lạnh ngắt 22°C mà không ai bật lại sưởi, cá co vây nằm một góc.', 'để nước lạnh, không chỉnh sưởi')
    if any(PENS[q]['water'] == 'cool' for q in w['heated']):
        _slip(t, 'too_warm', 1, 'Bể cá vàng bị bật sưởi, nước ấm quá cá thở gấp.', 'bật sưởi cho bể cá vàng')
    if x['sick'] and x['sick'] not in w['isolated']:
        _slip(t, 'sick_left', 3, f'{x["sign"]} Vậy mà vẫn để chung với cả đàn, không cách ly.', 'không cách ly bé ốm', True)
    wrong = [q for q in w['isolated'] if q != x['sick']]
    if wrong:
        _slip(t, 'wrong_isolate', 1, 'Tách nhầm bé đang khỏe ra khỏi đàn, bé hoảng cả buổi.', 'cách ly nhầm bé khỏe')
    d = _data(c)
    for pen in x['pens']:
        h = d['pens'][pen]
        if pen in w['fed']:
            h['fed'] = c['day']
        if pen in w['cleaned']:
            h['cleaned'] = c['day']
        h['health'] = max(0, min(100, h['health'] + (8 if pen in w['fed'] else -10)))
    if x['sick'] and x['sick'] in w['isolated']:
        d['pens'][x['sick']]['health'] = min(100, d['pens'][x['sick']]['health'] + 5)
    r = cq.react(s, c, t, _price(c, 'care'), who=_who(t))
    return _finish(s, c, t, r['pay'], r)


# ----- returns
def _return(s, c, t, p):
    _start(t)
    _job(t, 'ret')
    decision = kit.one_of(p.get('decision'), tuple(DECISIONS), 'Chọn: hoàn tiền, đổi món mới, hoặc không nhận.')
    x, n = t['_x'], t['needs']
    item = n['item']
    t['work']['decision'] = decision
    t['judged'] = True
    price = _price(c, item)
    lines, loss = [], 0
    d = _data(c)
    if decision == 'exchange':
        kit.need(kit.stock(c, item) >= 1, f'Hết {ITEM[item]["name"].lower()} để đổi. Mở Kho nhập thêm, hoặc chọn cách khác.')
        t['cost'] += kit.take(c, item, 1)
    if decision == 'refund':
        amount = min(price, c['money'])
        if amount:
            kit.money(s, c, -amount, f'Hoàn tiền đổi trả: {ITEM[item]["name"]}', t['id'], 'refund')
        d['today']['refunds'] += 1
    if decision in ('refund', 'exchange'):
        if x['resell']:
            kit.add_lot(c, item, 1, ITEM[item]['cost'], ITEM[item].get('life', 999), 'return')
            lines.append('Món còn nguyên seal, xếp lại lên kệ.')
        else:
            kit.waste(c, item, 1, ITEM[item]['cost'], 'Hàng đổi trả không bán lại được')
        if not x['legit']:
            loss = price if decision == 'refund' else ITEM[item]['cost']
            t['mistakes'] += 1
            lines.append(f'Chú Út lắc đầu: “Nhận lại món này là tiệm lỗ {loss} xu, lại tập cho khách cái thói.”')
    if decision not in x['ok']:
        if x['legit'] and decision == 'refuse':
            _slip(t, 'refused_fair', 3 if x['fault'] else 2,
                  'Có hóa đơn, lỗi rõ ràng mà tiệm nhất quyết không đổi.', 'từ chối đổi trả đúng quy định')
    lines.append(POLICY_LINE[decision])
    r = cq.react(s, c, t, 0, who=_who(t))
    return _finish(s, c, t, 0, r, extra=' '.join(lines), loss=loss)


POLICY_LINE = dict(refund='Bạn hoàn tiền, ghi sổ đổi trả.', exchange='Bạn đổi món mới, ghi sổ đổi trả.',
                   refuse='Bạn chỉ tấm bảng quy định đổi trả, giải thích nhẹ nhàng.')


# ----- lost-pet board
def _notice(s, c, t, p):
    _start(t)
    _job(t, 'lost')
    kit.need(not t['work']['pinned'], 'Tờ tìm thú đã dán lên bảng rồi.')
    fields = kit.id_list(p.get('fields'), tuple(FIELDS), len(FIELDS), 'Chọn các dòng trên tờ tìm thú nhé.')
    kit.need(fields, 'Tờ tìm thú cần ít nhất một dòng.')
    t['work']['notice'] = fields
    return dict(message='Tờ tìm thú gồm: ' + ', '.join(FIELDS[f][1].lower() for f in fields) + '.')


def _pin(s, c, t, p):
    _start(t)
    _job(t, 'lost')
    w = t['work']
    kit.need(w['notice'], 'Viết tờ tìm thú trước đã.')
    kit.need(not w['pinned'], 'Đã dán rồi.')
    w['pinned'] = True
    return dict(message=f'Dán tờ tìm {t["needs"]["pet"]} lên bảng trước cửa, chụp ảnh gửi nhóm Zalo khu phố. Chiều đó điện thoại tiệm reo…')


def _call(s, c, t, p):
    _start(t)
    _job(t, 'lost')
    w = t['work']
    kit.need(w['pinned'], 'Dán tờ tìm thú lên bảng trước đã.')
    calls = {x['id']: x for x in t['_x']['calls']}
    cid = kit.one_of(p.get('call'), tuple(calls), 'Không có cuộc gọi này.')
    move = kit.one_of(p.get('move'), CALL_MOVES, 'Chọn: hỏi dấu riêng, báo chủ đi gặp, hoặc cảm ơn rồi thôi.')
    state = w['calls'].get(cid)
    kit.need(state in (None, 'checked'), 'Cuộc gọi này đã xử lý xong.')
    call = calls[cid]
    if move == 'check':
        kit.need(state is None, 'Đã hỏi rồi.')
        w['calls'][cid] = 'checked'
        if call['kind'] == 'scam' and 'mark' in w['notice']:
            return dict(message=f'Người đó đọc vanh vách: “{t["_x"]["a"]["mark"]}” Y như trên tờ giấy dán ngoài bảng…')
        return dict(message=call['check'])
    w['calls'][cid] = 'sent' if move == 'send' else 'blocked'
    if move == 'send' and call['kind'] == 'real':
        w['found'] = True
        return dict(message=f'{_who(t)} chạy tới nơi. Đúng là {t["needs"]["pet"]} rồi!')
    if move == 'send' and call['kind'] == 'scam':
        return dict(message=f'{_who(t)} nhắn lại: người kia đòi chuyển tiền trước, chuyển xong thì chặn số.')
    if move == 'send':
        return dict(message=f'{_who(t)} chạy tới nơi rồi quay về: “Không phải bé nhà mình.”')
    return dict(message='Bạn cảm ơn rồi gác máy.')


def _lost_done(s, c, t, p):
    _start(t)
    _job(t, 'lost')
    w, x = t['work'], t['_x']
    kit.need(w['pinned'], 'Dán tờ tìm thú lên bảng trước đã.')
    open_calls = [k['id'] for k in x['calls'] if w['calls'].get(k['id']) not in ('sent', 'blocked')]
    kit.need(w['found'] or not open_calls, 'Còn cuộc gọi chưa trả lời.')
    t['judged'] = True
    pet = t['needs']['pet']
    missing = [f for f in NOTICE_NEED if f not in w['notice']]
    if 'phone' in missing:
        _slip(t, 'no_phone', 2, 'Tờ tìm thú không có số điện thoại, ai thấy cũng không biết gọi ai.', 'tờ tìm thú thiếu số điện thoại')
    elif missing:
        _slip(t, 'thin_notice', 1, 'Tờ tìm thú thiếu thông tin, người ta hỏi đi hỏi lại.', 'tờ tìm thú thiếu thông tin')
    if 'address' in w['notice']:
        _slip(t, 'privacy', 1, 'Dán cả địa chỉ nhà tôi lên bảng, người lạ cứ lảng vảng trước cổng.', 'công khai địa chỉ nhà')
    if 'reward' in w['notice']:
        _slip(t, 'reward_bait', 1, 'Ghi rõ tiền thưởng, điện thoại réo suốt toàn người hỏi tiền.', 'ghi số tiền thưởng')
    if 'mark' in w['notice']:
        _slip(t, 'mark_public', 1, 'Dấu riêng của bé in hết lên giấy, kẻ gian đọc theo mà lừa.', 'công khai dấu riêng')
    kinds = {k['id']: k['kind'] for k in x['calls']}
    if any(kinds[k] == 'scam' and v == 'sent' for k, v in w['calls'].items()):
        _slip(t, 'scam_sent', 3, 'Tiệm bảo tôi liên lạc với người ta, tôi chuyển tiền rồi bị chặn số.', 'để chủ nuôi bị lừa chuyển tiền')
    if any(kinds[k] == 'real' and v == 'blocked' for k, v in w['calls'].items()):
        _slip(t, 'missed_real', 2, f'Có người thấy {pet} thật mà tiệm lại gác máy.', 'bỏ qua tin báo thật')
    if any(kinds[k] == 'wrong' and v == 'sent' for k, v in w['calls'].items()):
        _slip(t, 'wasted_trip', 1, 'Chạy tới nơi mới biết không phải bé nhà mình, mất cả buổi.', 'báo nhầm bé khác')
    r = cq.react(s, c, t, 0, who=_who(t))
    tip, extra = 0, ''
    if w['found'] and r['kind'] == 'accept' and not cq.slips(t) and not t.get('tip_given'):
        tip = 20 if till._persona(c, t) != 'sour' else 10
        kit.money(s, c, tip, f'Tiền cảm ơn: tìm được {pet}', t['id'], 'tip')
        t['tip_given'] = tip
        extra = f'{_who(t)} dúi vào tay bạn {tip} xu: “Cầm uống nước, không lấy là giận đó!”'
    elif w['found']:
        extra = f'{pet} đã về nhà.'
    else:
        extra = f'Tờ tìm {pet} vẫn dán trên bảng. Mong bé sớm về.'
    return _finish(s, c, t, 0, r, extra=extra, tip=tip)


# ----- shipping
def _shipper(s, c, t, p):
    _start(t)
    _job(t, 'ship')
    kit.need(t['work']['cod'] is None, 'Đã ghi tiền thu hộ, không đổi shipper được nữa.')
    kind = kit.one_of(p.get('kind'), tuple(SHIPPERS), 'Chọn xe máy hoặc xe tải nhỏ.')
    t['work']['shipper'] = kind
    fee = _price(c, 'ship_' + kind)
    t['units']['ship_' + kind] = fee
    kg10 = sum(KG10.get(k, 0) * q for k, q in t['cart'].items())
    return dict(message=f'{SHIPPERS[kind][0]} Gọi shipper, phí {fee} xu. Đơn nặng khoảng {_kg(kg10)} ký.')


def _kg(kg10: int) -> str:
    return str(kg10 // 10) + (f',{kg10 % 10}' if kg10 % 10 else '')


def _cod(s, c, t, p):
    _start(t)
    _job(t, 'ship')
    w = t['work']
    kit.need(t['billed'], 'Chốt hóa đơn trước đã.')
    kit.need(w['shipper'], 'Chọn shipper trước đã.')
    amount = kit.integer(p.get('amount'), 0, 5000)
    w['cod'] = amount
    return dict(message=f'Ghi phiếu thu hộ: {amount} xu.')


def _ship(s, c, t, p):
    _start(t)
    _job(t, 'ship')
    w = t['work']
    kit.need(t['billed'] and w['shipper'] and w['cod'] is not None, 'Chốt hóa đơn, chọn shipper và ghi tiền thu hộ trước đã.')
    _ready(c, t)
    _judge(c, t)
    goods = _total(t, t['bill'])
    fee = t['units']['ship_' + w['shipper']]
    due = goods + fee
    cod = w['cod']
    loss = 0
    extra = ''
    if cod > due:
        _slip(t, 'cod_over', 2, f'Shipper thu của tôi {cod} xu, về cộng lại hóa đơn với phí ship chỉ có {due} xu.', f'thu hộ dư {cod - due} xu')
    elif cod < due:
        loss = due - cod
        extra = f'Tối đối soát: thu hộ thiếu {loss} xu, tiệm chịu.'
    r = cq.react(s, c, t, goods, who=_who(t))
    broke = any(x['code'] == 'tank_broke' for x in cq.slips(t))
    _sell(c, t, r['kind'] in ('refuse', 'walkout') or broke)
    got = max(0, min(cod, due) - fee)
    pay = max(0, got - r['cut'])
    return _finish(s, c, t, pay, r, extra=extra, loss=loss + max(0, t['bill_under']), later=True)


ACTIONS = dict(
    ps_ask=_ask, ps_cart=_cart, ps_coat=_coat, ps_food=_food, ps_date=_date, ps_swap=_swap, ps_tank=_tank, ps_advice=_advice,
    ps_scan=_scan, ps_void=_void, ps_total=_total_act, ps_rescan=_rescan, ps_handover=_handover,
    ps_verdict=_verdict, ps_sign=_sign,
    ps_feed=_feed, ps_clean=_clean, ps_temp=_temp, ps_heat=_heat, ps_look=_look, ps_isolate=_isolate, ps_care_done=_care_done,
    ps_return=_return, ps_notice=_notice, ps_pin=_pin, ps_call=_call, ps_lost_done=_lost_done,
    ps_shipper=_shipper, ps_cod=_cod, ps_ship=_ship,
    ps_short=lambda s, c, t, p: till.short_action(s, c, t, t.get('cash'), p, _who(t)),   # khách đưa thiếu tiền
)


# ---------------------------------------------------------------- reviews
def _speed(t: dict) -> dict:
    p = t.get('patience', 100)
    return dict(key='speed', label='Thời gian chờ', score=5 if p >= 90 else 4 if p >= 70 else 3 if p >= 50 else 2, note=f'kiên nhẫn còn {p}%')


JOB_ROW = dict(food=('advice', 'Tư vấn đúng bé'), tank=('setup', 'Bể đúng cách'), screen=('care', 'Hỏi han, giao đúng người'),
               care=('care', 'Chăm thú chu đáo'), ret=('policy', 'Đổi trả rõ ràng'), lost=('notice', 'Tờ tìm thú'), ship=('delivery', 'Giao đúng hàng'))


def feedback(c: dict, t: dict) -> dict:
    key, label = JOB_ROW[t['job']]
    rows = []
    own = [x for x in cq.slips(t) if x['code'] not in ('overcharged', 'bill_caught', 'change_short', 'change_home', 'cod_over')]
    pts = sum(x['sev'] for x in own)
    worst = max(own, key=lambda x: x['sev'])['note'] if own else ''
    good_note = dict(food='đúng loại, đúng tuổi, hỏi kỹ dị ứng', tank='bể đủ nước, cá hợp nhau', screen='hỏi kỹ trước khi giao',
                     care='ăn đủ, sạch sẽ, để ý bé ốm', ret='nói rõ quy định', lost='tờ tìm thú rõ ràng, lọc tin kỹ',
                     ship='đúng địa chỉ, đúng xe')[t['job']]
    rows.append(dict(key=key, label=label, score=max(1, 5 - pts), note=worst or good_note))
    if t['job'] in TILL_JOBS or t['job'] == 'ship':
        bad = t['bill_over'] or t['bill_caught']
        rows.append(dict(key='bill', label='Hóa đơn', score=3 if bad else 5, note='tính sai tiền' if bad else 'tính đúng từng món'))
    topics = TOPICS[t['job']]
    if topics:
        n = len(t['asked'])
        rows.append(dict(key='ask', label='Hỏi han', score=5 if n >= 2 else 4 if n else 3,
                         note=f'hỏi {n} điều' if n else 'không hỏi gì'))
    rows.append(_speed(t))
    cap = 5
    if t['job'] == 'ret' and not t['_x']['legit'] and t['work']['decision'] == 'refuse':
        cap = 4   # the customer did not get what they came for, fair as it was
    return dict(criteria=rows, cap=cap)


# ---------------------------------------------------------------- projection
def public_task(t: dict) -> dict:
    v = copy.deepcopy(t)
    x = v.pop('_x', {})
    job = t['job']
    if not t['known']:
        v['needs'] = {}
        v['cart'] = {}
        return v
    a = x.get('a', {})
    v['answers'] = {k: a[k] for k in t['asked'] if k in a}
    v['cart_total'] = _total(t, t['cart'])
    v['bill_total'] = _total(t, t['bill'])
    v['cash'] = till.public(t.get('cash'))
    if job == 'food':
        g = x.get('grab')
        v['grab'] = dict(item=g['item'], qty=g['qty'], label=g['label'] if t['work']['dated'] else '') if g else None
    elif job == 'tank':
        v['problems'] = [dict(code=p[0], note=p[4]) for p in tank_problems(t['cart'])] if t['judged'] else []
        size = next((k for k in TANKS if t['cart'].get(k)), None)
        v['load'] = dict(litres=sum(ANIMALS[k]['litres'] * t['cart'].get(k, 0) for k in FISH), size=TANKS[size] if size else 0)
    elif job == 'care':
        v['pens'] = [dict(id=p, temp=_temp_of(t, p) if p in t['work']['read'] else None,
                          sign=_sign_of(t, p) if p in t['work']['looked'] else '', dirty=p in x['dirty']) for p in x['pens']]
    elif job == 'lost':
        w = t['work']
        v['calls'] = [dict(id=k['id'], text=k['text'], state=w['calls'].get(k['id']),
                           check=(k['check'] if not (k['kind'] == 'scam' and 'mark' in w['notice']) else f'Người đó đọc vanh vách: “{a.get("mark", "")}”')
                           if w['calls'].get(k['id']) else '') for k in x.get('calls', [])] if w['pinned'] else []
    elif job == 'ship':
        v['kg10'] = sum(KG10.get(k, 0) * q for k, q in t['cart'].items())
        fee = t['units'].get('ship_' + t['work']['shipper'], 0) if t['work']['shipper'] else 0
        v['fee'] = fee
    return v


def public_data(c: dict) -> dict:
    d = copy.deepcopy(_data(c))
    day = c['day']
    d['stage_name'] = STAGES[d['stage']]['name']
    d['corner'] = [k for k in ADOPTEES if not any(x['pet'] == k and day - x['day'] < 3 for x in d['adopted'])]
    d['coats'] = {k: show_coats(day, k) for k in COATS}
    # Colours for the scene: [main, second] per animal on show, and the fur of the corner's adoptees.
    d['coat_colors'] = {k: [[COAT[k][x][2], COAT[k][x][3] or COAT[k][x][2]] for x in v] for k, v in d['coats'].items()}
    d['corner_fur'] = []
    for k in d['corner']:
        a = ADOPTEES[k]
        f = next(x for x in FUR[a['kind']] if x[0] == a['coat'])
        d['corner_fur'].append([a['kind'], f[2], f[3] or f[2]])
    ink = INKS.get(d['ink'], INKS['auto'])[1]
    d['palette'] = dict(THEME.get(d['theme'], THEME[DEFAULT_THEME])['colors'], ink=ink)
    return d


# ---------------------------------------------------------------- saves
def _bool(v) -> None:
    kit.need(type(v) is bool, 'Dữ liệu tiệm thú cưng không hợp lệ.', 'invalid_save')


def _ids(v, allowed, n) -> None:
    kit.need(isinstance(v, list) and len(v) <= n and len(set(v)) == len(v) and all(isinstance(x, str) and x in allowed for x in v),
             'Danh sách trong việc không hợp lệ.', 'invalid_save')


def _qtys(v, high) -> None:
    kit.need(isinstance(v, dict) and len(v) <= 16 and all(k in CART_KEYS for k in v), 'Giỏ hàng không hợp lệ.', 'invalid_save')
    for q in v.values():
        kit.integer(q, 1, high)


def validate_task(t: dict, original: dict) -> None:
    job = t.get('job')
    kit.need(job in JOBS and job == original.get('job') and t.get('variant') in VINDEX[job], 'Việc không hợp lệ.', 'invalid_save')
    _ids(t.get('asked'), tuple(TOPICS[job]), 8)
    _qtys(t.get('cart'), 20)
    _qtys(t.get('bill'), 40)
    u = t.get('units')
    kit.need(isinstance(u, dict) and len(u) <= 24 and all(k in PRICES for k in u), 'Bảng giá của việc không hợp lệ.', 'invalid_save')
    for q in u.values():
        kit.integer(q, 0, 5000)
    _bool(t.get('billed'))
    _bool(t.get('judged'))
    if 'coats' in t:
        co = t['coats']
        kit.need(isinstance(co, dict) and all(k in COAT and v in COAT[k] for k, v in co.items()), 'Màu thú trong việc không hợp lệ.', 'invalid_save')
    till.validate(t.get('cash'), t)
    till.validate_tip(t)
    kit.integer(t.get('bill_over'), 0, 10 ** 5)
    kit.integer(t.get('bill_under'), -1, 10 ** 5)
    kit.integer(t.get('bill_caught'), 0, 50)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    r = t.get('result')
    kit.need(isinstance(r, list) and len(r) <= 10 and all(isinstance(x, str) and len(x) <= 300 for x in r), 'Kết quả việc không hợp lệ.', 'invalid_save')
    w = t.get('work')
    kit.need(isinstance(w, dict) and set(w) == set(_work(job)), 'Bàn làm việc không hợp lệ.', 'invalid_save')
    if job == 'food':
        _bool(w['dated'])
        _bool(w['swapped'])
    elif job == 'tank':
        _ids(w['advice'], tuple(TIPS), 6)
    elif job == 'screen':
        kit.need(w['verdict'] is None or w['verdict'] in VERDICTS, 'Quyết định không hợp lệ.', 'invalid_save')
        _ids(w['signed'], tuple(SIGNS), 3)
    elif job == 'care':
        pens = tuple(t['_x']['pens'])
        kit.need(isinstance(w['fed'], dict) and all(k in pens and v in PORTIONS for k, v in w['fed'].items()), 'Sổ cho ăn không hợp lệ.', 'invalid_save')
        kit.need(isinstance(w['cleaned'], dict) and all(k in pens and v in CLEANS for k, v in w['cleaned'].items()), 'Sổ dọn dẹp không hợp lệ.', 'invalid_save')
        for k in ('read', 'heated', 'looked', 'isolated'):
            _ids(w[k], pens, 8)
    elif job == 'ret':
        kit.need(w['decision'] is None or w['decision'] in DECISIONS, 'Quyết định đổi trả không hợp lệ.', 'invalid_save')
    elif job == 'lost':
        _ids(w['notice'], tuple(FIELDS), len(FIELDS))
        _bool(w['pinned'])
        _bool(w['found'])
        ids = {x['id'] for x in t['_x']['calls']}
        kit.need(isinstance(w['calls'], dict) and all(k in ids and v in ('checked', 'sent', 'blocked') for k, v in w['calls'].items()),
                 'Sổ cuộc gọi không hợp lệ.', 'invalid_save')
    elif job == 'ship':
        kit.need(w['shipper'] is None or w['shipper'] in SHIPPERS, 'Shipper không hợp lệ.', 'invalid_save')
        if w['cod'] is not None:
            kit.integer(w['cod'], 0, 5000)


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.need(d.get('v') == V, 'Dữ liệu tiệm thú cưng không hợp lệ.', 'invalid_save')
    till.validate_book(c)
    _bool(d['intro_seen'])
    kit.integer(d['stage'], 0, len(STAGES) - 1)
    for k in ('good', 'served', 'welfare'):
        kit.integer(d[k], 0, 10 ** 7)
    kit.need(isinstance(d['animals'], dict) and set(d['animals']) == set(ANIMALS), 'Đàn thú trong tiệm không hợp lệ.', 'invalid_save')
    for v in d['animals'].values():
        kit.integer(v, 0, 999)
    kit.need(isinstance(d['pens'], dict) and set(d['pens']) == set(PENS), 'Chuồng trại không hợp lệ.', 'invalid_save')
    for pen in d['pens'].values():
        kit.need(isinstance(pen, dict) and set(pen) == {'health', 'fed', 'cleaned'}, 'Chuồng trại không hợp lệ.', 'invalid_save')
        kit.integer(pen['health'], 0, 100)
        kit.integer(pen['fed'], 0, 10 ** 6)
        kit.integer(pen['cleaned'], 0, 10 ** 6)
    kit.need(isinstance(d['adopted'], list) and len(d['adopted']) <= 20, 'Sổ nhận nuôi không hợp lệ.', 'invalid_save')
    for x in d['adopted']:
        kit.need(isinstance(x, dict) and x.get('pet') in ADOPTEES and set(x) == {'pet', 'day'}, 'Sổ nhận nuôi không hợp lệ.', 'invalid_save')
        kit.integer(x['day'], 0, 10 ** 6)
    kit.need(isinstance(d['book'], dict) and all(k in BOOK_KEYS for k in d['book']), 'Sổ thú quen không hợp lệ.', 'invalid_save')
    for v in d['book'].values():
        kit.integer(v, 0, 10 ** 6)
    kit.need(isinstance(d['fired'], list) and len(d['fired']) <= 40 and all(isinstance(x, str) and len(x) <= 40 for x in d['fired']),
             'Sổ thú quen không hợp lệ.', 'invalid_save')
    kit.need(isinstance(d['notes'], list) and len(d['notes']) <= NOTES_MAX, 'Sổ thú quen không hợp lệ.', 'invalid_save')
    for x in d['notes']:
        kit.need(isinstance(x, dict) and set(x) == {'day', 'emoji', 'text'}, 'Sổ thú quen không hợp lệ.', 'invalid_save')
        kit.integer(x['day'], 0, 10 ** 6)
        kit.text(x['emoji'], 16)
        kit.text(x['text'], 240)
    kit.need(isinstance(d['today'], dict) and set(d['today']) == set(_today()), 'Sổ trong ngày không hợp lệ.', 'invalid_save')
    kit.need(isinstance(d['themes'], list) and len(d['themes']) <= len(THEMES) and len(set(d['themes'])) == len(d['themes'])
             and all(x in THEME for x in d['themes']) and DEFAULT_THEME in d['themes'], 'Màu sơn của tiệm không hợp lệ.', 'invalid_save')
    kit.need(d['theme'] in d['themes'], 'Màu sơn của tiệm không hợp lệ.', 'invalid_save')
    kit.need(d['ink'] in INKS, 'Màu chữ biển hiệu không hợp lệ.', 'invalid_save')
    for v in d['today'].values():
        kit.integer(v, 0, 10 ** 6)


# ---------------------------------------------------------------- helpers for staff and hints
def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    role = e['role']
    ok = t and t['career'] == ID and t['known'] and not _done(t)
    if role == 'keeper':
        d = _data(c)
        low = min(d['pens'], key=lambda k: d['pens'][k]['health'])
        d['pens'][low]['health'] = min(100, d['pens'][low]['health'] + 5)
        return f'Đã lau {PENS[low]["name"].lower()}, thay nước uống, thêm mùn lót.'
    if not ok:
        return None
    if role == 'aqua' and t['job'] == 'care':
        for pen in t['_x']['pens']:
            if PENS[pen]['kind'] == 'fish' and pen not in t['work']['read']:
                t['work']['read'].append(pen)
                return f'Em đo {PENS[pen]["name"].lower()}: {_temp_of(t, pen)}°C.'
    if role == 'counter' and t['job'] in TILL_JOBS + ('ship',) and not t['billed'] and t['cart'] and not t['bill']:
        for k, q in t['cart'].items():
            t['bill'][k] = q
            _unit(c, t, k)
        return f'Em quét giúp các món trên quầy: tạm tính {_total(t, t["bill"])} xu. Mình dò lại rồi chốt nhé.'
    return None


def hint(c: dict, t: dict) -> str:
    return dict(
        food='Hỏi tuổi, cân nặng, dị ứng → đọc nhãn bao: đúng loài, đúng tuổi, đúng cỡ, tránh đồ bé dị ứng → món khách tự lấy trong rổ thì xem hạn → quét từng món, chốt, thối tiền.',
        tank='Chọn bể đủ lít (bảy màu 2 L, tứ vân 4 L, betta 5 L, cá vàng 10 L mỗi con) → betta ở một mình, không chung cá rỉa vây, cá vàng không chung cá nhiệt đới → lọc, khử clo → dặn cách thả cá, thay nước → tính tiền.',
        screen='Hỏi ai chăm, người lớn đồng ý chưa, nhà ở, thời gian, thú đang nuôi, dị ứng → chưa hợp thì hẹn lại hoặc từ chối nhẹ nhàng → hợp thì giao bé kèm đủ đồ, nhận nuôi thì làm đủ giấy.',
        care='Cho ăn đúng khẩu phần (cá một nhúm, chuồng một chén) → bể cá thay 1/3 nước, chuồng thay lót → đo nhiệt, lạnh thì bật sưởi (cá vàng không cần) → soi từng bể, bé ốm thì cách ly.',
        ret=POLICY + ' Xem hóa đơn, seal, mã lô, hạn, lỗi rồi mới quyết.',
        lost='Hỏi đặc điểm, nơi lạc, giờ lạc, số điện thoại, dấu riêng → tờ tìm thú giữ kín dấu riêng và địa chỉ nhà → dán bảng → người gọi tới thì hỏi dấu riêng, ai đòi chuyển tiền trước là lừa.',
        ship='Gọi xác nhận địa chỉ → đóng đúng đơn → quét, chốt hóa đơn → xe máy tối đa 20 kg và không chở bể kính lớn → thu hộ = hóa đơn + phí ship.',
    )[t['job']]


def content() -> dict:
    return dict(
        items={k: dict(name=v['name'], emoji=v['emoji'], group=v['group'], unit=v['unit']) for k, v in ITEM.items()},
        foods=FOODS, protein=PROTEIN, species=SPECIES, ages=STAGE, animals=ANIMALS, fish=list(FISH), tanks=TANKS,
        adoptees=ADOPTEES, kit=KIT, pens=PENS, temp_ok=TEMP_OK, portions=PORTIONS, cleans=CLEANS, topics=TOPICS,
        verdicts=VERDICTS, signs=SIGNS, tips=TIPS, good_tips=list(GOOD_TIPS), decisions=DECISIONS, policy=POLICY,
        fields=FIELDS, notice_need=list(NOTICE_NEED), shippers=SHIPPERS, bike_max10=BIKE_MAX10, big_glass=list(BIG_GLASS),
        kg10=KG10, jobs=JOB_NAMES, job_emoji=JOB_EMOJI, fee_names=FEE_NAME, stages=STAGES, intro=INTRO, vet=VET, spa=SPA,
        rescue=RESCUE, prices=PRICES, till_jobs=list(TILL_JOBS),
        coats={k: [dict(id=c[0], name=c[1], hex=c[2], hex2=c[3], extra=c[4]) for c in rows] for k, rows in COATS.items()},
        fur={k: [dict(id=c[0], name=c[1], hex=c[2], hex2=c[3]) for c in rows] for k, rows in FUR.items()},
        themes=[dict(id=x['id'], name=x['name'], emoji=x['emoji'], cost=x['cost'], stage=x['stage'], colors=x['colors']) for x in THEMES],
        inks=[dict(id=k, name=v[0], hex=v[1]) for k, v in INKS.items()],
    )


# ---------------------------------------------------------------- situations and stories
def _p(who, emoji, text):
    return dict(who=who, emoji=emoji, text=text)


SITUATIONS = [
    dict(id='PS-S01', title='Chó con giá rẻ trên xe tải', npc=1, tone='tense', min_day=2,
         opening='Một người đậu xe tải trước tiệm, mở thùng: mười mấy con chó con chen chúc. “Bán sỉ cho tiệm, giá rẻ như cho!” Chú Út có vẻ xiêu lòng.',
         swap='Bạn là chú Út: ba mươi năm trước tiệm nào cũng lấy chó con như vậy mà bán.',
         facts=[dict(id='papers', title='Giấy tờ', source='Hỏi người bán', text='Không có sổ tiêm, không biết mẹ các bé ở đâu. “Giấy tờ làm chi cho mệt.”'),
                dict(id='health', title='Nhã xem qua', source='Nhã (sinh viên thú y)', text='Vài bé tiêu chảy, mắt kèm nhèm. Chó con chưa tiêm mà nhốt chung dễ lây bệnh nặng.'),
                dict(id='rule', title='Nếp mới của tiệm', source='Bảng ở góc nhận nuôi', text='Chó mèo chỉ về nhà mới qua góc nhận nuôi của nhóm Chân Nhỏ.')],
         options=[dict(id='refuse', label='Từ chối, gọi nhóm Chân Nhỏ và thú y phường tới xem các bé', requires=['health', 'rule'], quality='good', stars=5,
                       review='Tiệm không nhận chó con trôi nổi mà còn gọi người cứu mấy bé. Nể thật.',
                       outcome='Nhóm Chân Nhỏ nhận chữa bốn bé yếu nhất. Người bán lái xe đi, chú Út lặng thinh một lúc rồi gật đầu.',
                       perspectives=[_p('Chú Út', '👴', 'Hồi xưa chú bán vậy hoài. Giờ nhìn mấy đứa nhỏ run run mới thấy tội.'),
                                     _p('Anh Khánh', '🧡', 'Mấy bé này mà vào tiệm là cả góc nhận nuôi lây bệnh.'),
                                     _p('Nhã', '🩺', 'Bán rẻ thì có lời, nhưng khách mua về một bé ốm thì mất cả lòng tin.')]),
                  dict(id='buy', label='Lấy vài con cho vui lòng chú Út', quality='bad', stars=2, cost=40,
                       review='Mua chó con ở tiệm, về hai hôm là ốm, phải chạy thú y hết mấy trăm.',
                       outcome='Hai bé bệnh nặng, cả góc nhận nuôi phải khử trùng. Tiệm bỏ tiền chữa.',
                       perspectives=[_p('Khách mua', '😢', 'Tôi tưởng tiệm quen thì yên tâm.'), _p('Nhã', '😞', 'Đây đúng là điều cháu sợ nhất.')]),
                  dict(id='ignore', label='Từ chối cho xong, không báo ai', requires=['rule'], quality='ok', stars=4,
                       review='Tiệm không bán chó mèo trôi nổi. Được.',
                       outcome='Người bán lái xe sang tiệm khác. Mấy bé chó con không ai biết đi đâu.',
                       perspectives=[_p('Chú Út', '🤷', 'Thôi không lấy là được rồi.'), _p('Anh Khánh', '😔', 'Giá mà em gọi anh một tiếng.')])],
         lesson='Tiệm có tâm không nhận thú trôi nổi, và nếu được thì giúp các bé tới chỗ có người chăm.'),
    dict(id='PS-S02', title='Vẹt bắt ngoài rừng', npc=2, tone='tense', min_day=3,
         opening='Một anh bịt khẩu trang đưa lồng vẹt xanh lạ mắt: “Hàng hiếm, bắt ngoài rừng, tiệm lấy về bán giá cao.” Chú Sáu đứng cạnh, mắt sáng rỡ.',
         facts=[dict(id='law', title='Quy định', source='Tờ hướng dẫn của thú y phường', text='Chim hoang dã bắt ngoài tự nhiên không được mua bán. Tiệm chỉ bán chim nuôi sinh sản có nguồn gốc.'),
                dict(id='bird', title='Con chim', source='Nhã xem', text='Lông xơ xác, chân có vết dây buộc, sợ người.'),
                dict(id='farm', title='Nguồn chim của tiệm', source='Sổ nhập hàng', text='Yến phụng của tiệm nhập từ trại Bến Mây, có giấy nguồn gốc.')],
         options=[dict(id='report', label='Không mua, báo kiểm lâm và thú y phường', requires=['law', 'bird'], quality='good', stars=5,
                       review='Tiệm từ chối mua chim rừng, còn báo người có trách nhiệm. Đáng tin.',
                       outcome='Kiểm lâm tới nhận con vẹt về trạm cứu hộ. Chú Sáu tiếc hùi hụi nhưng khen tiệm làm đúng.',
                       perspectives=[_p('Chú Sáu', '🧓', 'Đẹp thì đẹp thật, mà bắt ngoài rừng thì thôi.'),
                                     _p('Cán bộ kiểm lâm', '🌳', 'Nhờ tiệm báo sớm, con chim còn cơ hội về rừng.')]),
                  dict(id='buy', label='Mua lại bán cho chú Sáu, lời to', quality='bad', stars=1, cost=60,
                       review='Tiệm bán chim rừng không giấy tờ. Bị phạt là đáng.',
                       outcome='Đoàn kiểm tra phát hiện, tịch thu con vẹt và lập biên bản cả tiệm lẫn chú Sáu.',
                       perspectives=[_p('Chú Sáu', '😣', 'Tôi mang tiếng lây.'), _p('Nhã', '😞', 'Một lần ham lời, cả năm gây dựng đổ sông.')]),
                  dict(id='shoo', label='Không mua, đuổi đi cho xong', requires=['law'], quality='ok', stars=4,
                       review='Tiệm không bán chim rừng.',
                       outcome='Người bán đi mất. Con vẹt chắc lại bị bán ở đâu đó.',
                       perspectives=[_p('Chú Sáu', '😐', 'Không mua là phải.'), _p('Nhã', '🤔', 'Lần sau mình gọi kiểm lâm luôn.')])],
         lesson='Chỉ bán thú có nguồn gốc. Gặp thú hoang dã bị buôn bán thì báo người có trách nhiệm.'),
    dict(id='PS-S03', title='“Bán rẻ cho tôi lon sắp hết hạn”', npc=3, tone='gentle', min_day=2,
         opening='Bà Hai lục rổ giảm giá của chú Út: “Mấy lon này sắp hết hạn, bán bà nửa giá đi!” Trong rổ lẫn vài lon đã quá hạn.',
         facts=[dict(id='dates', title='Hạn dùng', source='Đáy lon', text='Ba lon còn hạn 5 ngày, hai lon đã quá hạn tuần trước, một lon phồng.'),
                dict(id='rule', title='Quy định của tiệm', source='Nhã dán ở quầy', text='Hàng cận hạn được giảm giá và dán nhãn rõ. Hàng quá hạn thì hủy, không bán.')],
         options=[dict(id='sort', label='Lọc rổ: bán rẻ ba lon còn hạn, dán nhãn ngày, hủy mấy lon quá hạn', requires=['dates', 'rule'], quality='good', stars=5,
                       review='Mua được pate rẻ mà còn hạn rõ ràng. Tiệm thật thà.',
                       outcome='Bà Hai mua ba lon, còn khen “con nhỏ này kỹ”. Rổ giảm giá từ nay có nhãn ngày.',
                       perspectives=[_p('Bà Hai', '👵', 'Rẻ mà yên tâm, vậy mới là mua bán.'), _p('Chú Út', '👴', 'Ờ, cái rổ đó của chú bày lâu rồi.')]),
                  dict(id='all', label='Bán hết rổ nửa giá cho nhanh', quality='bad', stars=1,
                       review='Mua pate rổ giảm giá, về mèo ói cả đêm. Lon đã quá hạn!',
                       outcome='Hai con mèo nhà bà Hai ói mửa, phải qua phòng khám. Bà kể khắp xóm.',
                       perspectives=[_p('Bà Hai', '😠', 'Tham rẻ mà khổ mấy con mèo.'), _p('Nhã', '😣', 'Đó là lý do phải xem hạn từng lon.')]),
                  dict(id='none', label='Không bán gì trong rổ hết', requires=['dates'], quality='ok', stars=3,
                       review='Muốn mua đồ giảm giá mà tiệm không bán.',
                       outcome='Ba lon còn hạn cũng thành hàng hủy.',
                       perspectives=[_p('Bà Hai', '😤', 'Còn hạn mà không bán là sao?'), _p('Chú Út', '💸', 'Uổng quá.')])],
         lesson='Hàng cận hạn bán rẻ và ghi rõ ngày; hàng quá hạn thì hủy.'),
    dict(id='PS-S04', title='Bể cá bị cúp điện qua đêm', npc=2, tone='tense', min_day=3,
         opening='Sáng ra cả khu mất điện từ nửa đêm. Lọc và sưởi tắt hết, bể bảy màu nước lạnh, vài con nằm im dưới đáy. Chú Sáu đứng ngoài cửa kính.',
         facts=[dict(id='air', title='Sơ cứu bể', source='Sổ tay của Nhã', text='Mất điện: sục khí bằng máy chạy pin, thay 1/4 nước cùng nhiệt, đừng cho ăn cho tới khi lọc chạy lại.'),
                dict(id='gen', title='Máy phát điện', source='Chú Sáu', text='Nhà chú Sáu có bình sục khí chạy pin, cho mượn được.')],
         options=[dict(id='rescue', label='Mượn bình sục khí của chú Sáu, thay ít nước cùng nhiệt, tạm ngưng cho ăn', requires=['air', 'gen'], quality='good', stars=5,
                       review='Tiệm cứu được gần hết đàn cá sau đêm mất điện. Chuyên nghiệp.',
                       outcome='Tới trưa có điện lại, chỉ mất một con cá. Chú Sáu tự hào như vừa cứu cả biển.',
                       perspectives=[_p('Chú Sáu', '🧓', 'Chơi cá mấy chục năm, gặp tiệm biết việc là chú mê.'),
                                     _p('Nhã', '🩺', 'Sơ cứu đúng thì cá chịu được lâu hơn mình nghĩ.')]),
                  dict(id='feed', label='Cho ăn thật nhiều cho cá khỏe lại', quality='bad', stars=2, cost=20,
                       review='Bể cá của tiệm chết gần nửa sau đêm mất điện.',
                       outcome='Thức ăn thừa làm nước càng đục, thêm mấy con nữa không qua khỏi.',
                       perspectives=[_p('Chú Sáu', '😣', 'Nước đã thiếu khí mà còn đổ cám vô.'), _p('Chú Út', '😔', 'Lỗ cả bể cá.')]),
                  dict(id='wait', label='Chờ có điện rồi tính', requires=['air'], quality='ok', stars=3,
                       review='Cá trong tiệm hôm nay trông yếu quá.',
                       outcome='Điện có lại lúc trưa, mất vài con cá.',
                       perspectives=[_p('Chú Sáu', '😐', 'Chờ thì cũng qua, nhưng mất mấy con.'), _p('Nhã', '🤔', 'Lần sau mình chuẩn bị sẵn máy sục pin.')])],
         lesson='Sự cố điện ở tiệm cá: giữ oxy trước, thay ít nước cùng nhiệt, ngưng cho ăn.'),
    dict(id='PS-S05', title='Ngày hội nhận nuôi đầu tiên', npc=6, tone='gentle', min_day=5,
         opening='Nhóm Chân Nhỏ muốn làm ngày hội nhận nuôi ngay trước tiệm. Chú Út lo mất chỗ bán hàng, anh Khánh nhìn bạn chờ câu trả lời.',
         facts=[dict(id='space', title='Mặt tiền', source='Đo thử', text='Dẹp rổ giảm giá và kệ cát là đủ chỗ cho sáu lồng.'),
                dict(id='rule', title='Cách làm của nhóm', source='Anh Khánh', text='Ai muốn nhận phải qua phỏng vấn, ký giấy, nhóm ghé thăm sau hai tuần.'),
                dict(id='neighbor', title='Hàng xóm', source='Bà Hai', text='Bà Hai hứa trông lồng mèo giúp buổi sáng.')],
         options=[dict(id='host', label='Làm ngày hội, dẹp rổ giảm giá, nhờ bà Hai phụ, phỏng vấn kỹ từng người', requires=['space', 'rule'], quality='good', stars=5,
                       review='Ngày hội nhận nuôi trước tiệm vui quá! Hỏi han kỹ mà không làm khó.',
                       outcome='Bốn bé có nhà mới. Tiệm bán thêm được đồ dùng cho các gia đình mới. Chú Út đứng cười suốt buổi.',
                       perspectives=[_p('Anh Khánh', '🧡', 'Lần đầu nhóm làm ở tiệm mà đông vậy.'), _p('Chú Út', '👴', 'Bán ít chỗ mà được tiếng thơm.'),
                                     _p('Bà Hai', '👵', 'Trông mèo thì bà rành nhất xóm.')]),
                  dict(id='quick', label='Làm ngày hội nhưng giao nhanh cho ai muốn nhận, khỏi phỏng vấn', requires=['space'], quality='bad', stars=2,
                       review='Nghe nói có bé nhận nuôi ở tiệm bị trả lại sau ba hôm.',
                       outcome='Hai bé bị trả lại trong tuần. Nhóm Chân Nhỏ buồn, lần sau muốn làm chỗ khác.',
                       perspectives=[_p('Anh Khánh', '😔', 'Nhận nuôi là cả một đời của bé, không vội được.'), _p('Nhã', '😞', 'Mình làm hỏng tấm lòng của nhóm.')]),
                  dict(id='no', label='Thôi, tiệm chật lắm', quality='ok', stars=3,
                       review='Tiệm từ chối cho nhóm cứu hộ làm ngày hội.',
                       outcome='Nhóm làm ở công viên, ít người ghé hơn.',
                       perspectives=[_p('Anh Khánh', '🙂', 'Không sao, lần sau nha.'), _p('Chú Út', '😶', 'Cũng tiếc.')])],
         lesson='Nhận nuôi là cam kết lâu dài: làm vui nhưng vẫn hỏi kỹ, ký giấy, theo dõi sau.'),
]

SPEC = dict(
    id=ID, prefix='ps_', category='shop',
    meta=dict(short='Shop thú cưng', place=SHOP, tagline='Bán cho đúng bé, giao cho đúng người.', icon='fish',
              color='#2f9e8f', light='#e6f6f2', weather='Nắng nhẹ 28°C', work='Việc ở tiệm', station='Quầy & dãy bể',
              greeting='Nhã vẫy tay: “Hỏi kỹ rồi hãy bán nha. Thú khỏe là trên hết!”',
              caption='Tiếng lọc bể róc rách, vẹt yến phụng líu lo trước cửa', map_label='15 · THÚ NHỎ CHÚ ÚT'),
    people=PEOPLE,
    staff=[('Chị Nguyệt', 'counter', 'Tính tiền nhanh, nhớ giá từng món, hay cho khách kẹo.', 84, 90),
           ('Tú', 'aqua', 'Mê cá từ nhỏ, nhìn màu nước là biết bể có chuyện.', 80, 92),
           ('Bé Hân', 'keeper', 'Thương hamster, dọn chuồng sạch bong.', 86, 84),
           ('Anh Phát', 'counter', 'Khỏe, khuân bao cát không cần xe đẩy.', 90, 76)],
    roles={'counter': 'Đứng quầy', 'aqua': 'Chăm bể cá', 'keeper': 'Chăm chuồng'},
    inventory=dict(items=ITEMS, capacity=40),
    prices=PRICES,
    tip=2,
    physical=('ps_clean', 'ps_heat', 'ps_isolate', 'ps_ship'),
    free_actions=FREE,
    no_tick=('ps_intro', 'ps_short', 'ps_scan', 'ps_void', 'ps_date', 'ps_advice', 'ps_notice', 'ps_coat', 'ps_paint', 'ps_ink'),
    waste_items=(),
    activity=('🐠', 'Tiệm thú nhỏ ngăn nắp', [('Hạt mèo con', 'Kệ thức ăn mèo'), ('Dung dịch khử clo', 'Kệ bể cá'),
                                             ('Mùn lót chuồng', 'Góc hamster'), ('Vòng cổ có thẻ tên', 'Móc dây dắt')],
              ['Cho cá ăn một nhúm', 'Thay 1/3 nước bể', 'Thay lót chuồng hamster', 'Soi từng bể tìm bé ốm']),
    stories=[('Cái rổ giảm giá của chú Út', ('Ba mươi năm, trước quầy luôn có cái rổ “hàng giảm giá”. Lon nào cận hạn, quá hạn, chú Út đều thả vào.',
                                               'Nhã lặng lẽ dán nhãn ngày lên từng lon, lon quá hạn thì bỏ riêng một thùng.',
                                               'Một sáng, chú Út tự tay bưng cái rổ vào kho: “Thôi, từ nay bán cái gì cũng phải nhìn cái hạn.”')),
             ('Bánh Bao của Bin', ('Bin đập heo đất, chạy một mạch tới tiệm đòi mua hamster, mẹ chưa hề biết.',
                                  'Tiệm hẹn Bin về hỏi mẹ. Hôm sau hai mẹ con cùng tới, chọn lồng, mua lót, học cách cầm hamster.',
                                  'Bánh Bao lớn tròn vo. Bin lập sổ cân nặng, tuần nào cũng ghé khoe.')),
             ('Góc nhận nuôi', ('Nhóm Chân Nhỏ xin một góc nhỏ trong tiệm. Chú Út càu nhàu: “Chó mèo cho không thì lời gì?”',
                               'Người tới nhận nuôi mua thêm hạt, cát, vòng cổ. Ai về cũng nhớ tiệm.',
                               'Ngày hội nhận nuôi đầu tiên, chú Út đứng phát kẹo cho con nít, cười không ngớt.'))],
    review_asides=['Tiệm hỏi kỹ từng chút, như bác sĩ khám cho bé nhà tôi vậy 🐾', 'Bể cá trong tiệm trong veo, nhìn là muốn nuôi.',
                   'Hóa đơn ghi rõ từng món, thối tiền đủ từng xu.', 'Không bán bừa, không nói quá. Tôi sẽ quay lại.'],
    situations=SITUATIONS,
    guide='Hỏi kỹ → chọn đúng cho bé → quét từng món, chốt hóa đơn → thối tiền đủ → thú khỏe là trên hết.',
)
