"""🐾 Nuôi thú cưng: the breeds, coats, food, toys, accessories and tricks (game/pets.py has the rules).

Owner 07/10: "ra thêm nhiều dòng mèo chó cute hơn nữa nhé". Every breed is drawn by public/js/v4/pet-art.js from
its `shape` (the body plan) and the coat's colours: base (`b`), markings (`m`), light parts (`l`), eyes (`e`).

Prices are xu, constants for now: when the shared price index lands (branch price-up, PRICE_INDEX), multiply the
shop prices here by it. Local breeds are cheap (and free at the shelter); rare ones cost a small car.
Ids are stored in saves: never rename or remove one (mark it `gone` instead).
"""
from __future__ import annotations


def _c(name, b, m, l, e='#3b2a22'):
    return dict(name=name, b=b, m=m, l=l, e=e)


def _b(bid, kind, name, shape, price, trait, line, coats, *, tier='quen', shelter=False, size='s'):
    return bid, dict(id=bid, kind=kind, name=name, shape=shape, price=price, trait=trait, line=line,
                     coats=list(coats), tier=tier, shelter=shelter, size=size)


# tier: 'ta' (giống ta, cheap), 'quen' (popular), 'hiem' (rare, dear). size: s / m / l (drawn a little bigger).
BREEDS = dict((
    # ---------------------------------------------------------------- chó
    _b('cho_ta', 'dog', 'Chó ta', 'mutt', 300, 'Trung thành', 'Nghe tiếng xe là chạy ra cổng, đuôi quẫy tít.',
       (_c('Vàng', '#e2a65a', '#c4823a', '#fbe3bd'), _c('Mực', '#3d3634', '#28211f', '#8a7d74'), _c('Vện', '#b98a55', '#6e4c2c', '#f1d6ae'),
        _c('Trắng', '#f7f1e6', '#e3d6c3', '#fffaf2')), tier='ta', shelter=True, size='m'),
    _b('poodle', 'dog', 'Poodle', 'poodle', 4500, 'Điệu đà', 'Lông xù như bông gòn, đi đâu cũng nhún nhảy.',
       (_c('Nâu đỏ', '#c8794a', '#a85c33', '#e7a77c'), _c('Trắng', '#fbf6ee', '#e8dccb', '#ffffff'), _c('Xám bạc', '#b6b3b0', '#8f8b88', '#d9d6d2'),
        _c('Đen', '#3a3436', '#262022', '#6d6466'))),
    _b('corgi', 'dog', 'Corgi', 'corgi', 6000, 'Mông to tự tin', 'Chân ngắn nhưng chạy nhanh, cái mông lắc lư làm cả xóm cười.',
       (_c('Vàng cam', '#e79a4f', '#c8763a', '#fff4e6'), _c('Tam thể', '#3f3536', '#c97c45', '#fff4e6')), size='m'),
    _b('shiba', 'dog', 'Shiba', 'shiba', 9000, 'Lầy lội', 'Mặt lúc nào cũng như đang cười khẩy. Gọi tên thì giả điếc.',
       (_c('Đỏ', '#d9873f', '#b86a2c', '#fff1de'), _c('Mè', '#b88a5c', '#5e4630', '#f6e6cf'), _c('Đen vàng', '#3c3433', '#d79a5a', '#f8ead6')), tier='hiem', size='m'),
    _b('pom', 'dog', 'Phốc sóc', 'pom', 5500, 'Bé bỏng', 'Một cục bông biết sủa. Bế lên là ngoan liền.',
       (_c('Cam', '#f0a95a', '#d88a3c', '#ffe2b8'), _c('Kem', '#f6dfb8', '#e6c592', '#fff6e4'), _c('Trắng', '#fbf8f2', '#e9e1d4', '#ffffff'))),
    _b('chihuahua', 'dog', 'Chihuahua', 'chihuahua', 2500, 'Nhỏ mà có võ', 'Nặng hai ký, sủa như chó ngao. Run run lúc trời lạnh.',
       (_c('Kem', '#efc995', '#d9a86c', '#fff1dc'), _c('Sô-cô-la', '#8a5a3c', '#6a4129', '#d6ac86'), _c('Đen vàng', '#2f2a2b', '#d39a5c', '#f2d7b2'))),
    _b('husky', 'dog', 'Husky', 'husky', 8000, 'Ồn ào', 'Mắt xanh hút hồn, nhưng hát “awoo” lúc nửa đêm.',
       (_c('Xám trắng', '#8d939b', '#5d636b', '#fbfbfa', '#5aa9e6'), _c('Đen trắng', '#3a3a40', '#26262b', '#fbfbfa', '#5aa9e6'),
        _c('Đỏ trắng', '#c47c4c', '#9c5b34', '#fbf5ee', '#7a5236')), size='l'),
    _b('golden', 'dog', 'Golden', 'golden', 7000, 'Hiền khô', 'Ai tới cũng vẫy đuôi chào, kể cả ông trộm.',
       (_c('Vàng óng', '#e5ad5c', '#c98d3e', '#f8dca9'), _c('Kem', '#f1d5a4', '#ddb57a', '#fbecd0')), size='l'),
    _b('alaska', 'dog', 'Alaska', 'alaska', 25000, 'Khổng lồ hiền', 'To như con gấu bông, ăn nhiều, ôm thì ấm cả mùa đông.',
       (_c('Xám', '#7f838c', '#555961', '#fbfaf7'), _c('Nâu đỏ', '#a5683f', '#7b4b2b', '#fbf3ea')), tier='hiem', size='l'),
    _b('phu_quoc', 'dog', 'Phú Quốc', 'ridgeback', 30000, 'Gan dạ', 'Xoáy lưng hiếm có, leo cây bơi biển giỏi. Niềm tự hào chó Việt.',
       (_c('Vện', '#a7743e', '#5b3b20', '#d9b07c'), _c('Vàng đỏ', '#cf8a45', '#a3622c', '#e8b47a'), _c('Đen', '#2f2b2b', '#1c1919', '#57504e')), tier='hiem', size='m'),
    _b('bac_ha', 'dog', 'Bắc Hà', 'bacha', 6500, 'Khôn ngoan', 'Chó núi Lào Cai lông dày, đuôi xoè như bông lau. Nhớ đường về nhà.',
       (_c('Vàng', '#d9a35f', '#b57f3f', '#f5dcb3'), _c('Đen', '#36302f', '#211d1d', '#6c6260'), _c('Trắng', '#f7f2ea', '#e2d7c6', '#ffffff')), size='m'),
    _b('pug', 'dog', 'Pug', 'pug', 4000, 'Hài hước', 'Mặt xệ, thở khò khè, nằm đâu ngáy đó. Ai nhìn cũng thương.',
       (_c('Vàng mơ', '#e6c49a', '#3a302c', '#f5e2c8'), _c('Đen', '#3a3436', '#232022', '#625a5b'))),
    _b('samoyed', 'dog', 'Samoyed', 'samoyed', 22000, 'Hay cười', 'Đám mây trắng biết cười. Rụng lông đủ làm thêm một con nữa.',
       (_c('Trắng', '#fdfbf7', '#e9e2d6', '#ffffff'), _c('Kem', '#f6e9d2', '#e3cfae', '#fffaf0')), tier='hiem', size='l'),
    _b('lap_xuong', 'dog', 'Lạp xưởng', 'dachshund', 3500, 'Tò mò', 'Thân dài như cây lạp xưởng, chui gầm giường đi tìm dép.',
       (_c('Nâu đỏ', '#b0643a', '#8a4826', '#d9956a'), _c('Đen vàng', '#2f2a2b', '#c8874c', '#e3ae7a'), _c('Kem', '#e8c08f', '#cf9f66', '#f6dfbd'))),
    # ---------------------------------------------------------------- mèo
    _b('meo_muop', 'cat', 'Mèo mướp ta', 'tabby', 300, 'Lém lỉnh', 'Bắt chuột giỏi, trèo mái nhà như đi chợ.',
       (_c('Mướp xám', '#a9a29a', '#6f675f', '#e9e4dc'), _c('Mướp vàng', '#e8a35c', '#c47a36', '#fbe1bf')), tier='ta', shelter=True),
    _b('tam_the', 'cat', 'Mèo tam thể', 'calico', 400, 'Mang lộc', 'Ba màu may mắn, ông bà bảo nuôi là buôn may bán đắt.',
       (_c('Tam thể', '#fbf6ee', '#e39a52', '#3d3533'), _c('Tam thể nhạt', '#fbf6ee', '#efc08d', '#a8a3ae')), tier='ta', shelter=True),
    _b('meo_mun', 'cat', 'Mèo mun', 'cat', 350, 'Bí ẩn', 'Đen tuyền, mắt vàng như trăng rằm. Thích ngủ trong hộp giấy.',
       (_c('Mun', '#2d2a2e', '#1b191c', '#45404a', '#e8c547'), _c('Mun yếm trắng', '#2d2a2e', '#1b191c', '#fbf8f2', '#9fd36b')), tier='ta', shelter=True),
    _b('aln', 'cat', 'Anh lông ngắn', 'british', 6000, 'Điềm tĩnh', 'Má bánh bao, ngồi như ông chủ. Không thích bị bế lâu.',
       (_c('Xám xanh', '#8e98a6', '#76808e', '#aab3bf', '#e9a23b'), _c('Vàng golden', '#e6c38a', '#c9a066', '#f6e3c1', '#4fa36a'),
        _c('Hai màu', '#8e98a6', '#76808e', '#fbf8f2', '#e9a23b'))),
    _b('ald', 'cat', 'Anh lông dài', 'british_long', 8000, 'Sang chảnh', 'Lông dài mượt như vừa đi gội đầu, đi đâu cũng nhẹ nhàng.',
       (_c('Xám', '#99a1ad', '#7c8592', '#c2c8d1', '#e9a23b'), _c('Kem', '#f1dcb8', '#dcc094', '#fbf0dc', '#c98a3a'), _c('Trắng', '#fdfbf7', '#e7e1d8', '#ffffff', '#5aa9e6'))),
    _b('ba_tu', 'cat', 'Ba Tư', 'persian', 7500, 'Lười biếng', 'Mặt tịt, lông bồng bềnh, mỗi ngày ngủ mười sáu tiếng.',
       (_c('Trắng', '#fdfbf7', '#e7e1d8', '#ffffff', '#5aa9e6'), _c('Kem', '#f3dcb4', '#ddbd8d', '#fbf0dc', '#c98a3a'), _c('Xám khói', '#8d8a90', '#5f5c63', '#b9b6bc', '#e9a23b'))),
    _b('scottish', 'cat', 'Scottish Fold', 'fold', 9000, 'Hiền lành', 'Tai cụp như đội mũ, ngồi kiểu “Phật” nhìn đời.',
       (_c('Xám', '#a1a7b1', '#7f8692', '#d3d7dd', '#e9a23b'), _c('Kem trắng', '#f0d4a6', '#d9b47c', '#fbf8f2', '#c98a3a'), _c('Mướp bạc', '#c9ccd0', '#6f747c', '#f2f3f4', '#4fa36a'))),
    _b('munchkin', 'cat', 'Munchkin', 'munchkin', 10000, 'Lon ton', 'Chân ngắn tũn, chạy như lăn. Đứng hai chân như chuột đồng.',
       (_c('Kem', '#f0d2a2', '#dab27a', '#fbefd9', '#c98a3a'), _c('Xám', '#a1a7b1', '#7f8692', '#d3d7dd', '#e9a23b'), _c('Tam thể', '#fbf6ee', '#e39a52', '#3d3533', '#4fa36a')), tier='hiem'),
    _b('ragdoll', 'cat', 'Ragdoll', 'ragdoll', 14000, 'Mềm như bông', 'Bế lên là thả lỏng như con búp bê vải. Mắt xanh biếc.',
       (_c('Seal point', '#f6eadb', '#6e5446', '#fffaf3', '#4a90e2'), _c('Blue point', '#f2efed', '#8f97a6', '#ffffff', '#4a90e2')), tier='hiem', size='m'),
    _b('bengal', 'cat', 'Bengal', 'bengal', 16000, 'Hiếu động', 'Đốm như báo con, mê nước, mê leo tủ lạnh.',
       (_c('Vàng đốm', '#e2b065', '#6a4a2c', '#f7e4c2', '#4fa36a'), _c('Bạc đốm', '#d7d9dc', '#4f5359', '#f5f6f7', '#4fa36a')), tier='hiem'),
    _b('sphynx', 'cat', 'Sphynx', 'sphynx', 18000, 'Bám người', 'Không lông, da ấm như túi chườm. Đòi đắp chăn chung.',
       (_c('Hồng', '#f3c4b8', '#dd9f92', '#f9dcd4', '#4fa36a'), _c('Xám', '#bcb3b8', '#968d93', '#d8d1d5', '#e9a23b')), tier='hiem'),
    _b('maine_coon', 'cat', 'Maine Coon', 'maine', 20000, 'Gã khổng lồ', 'Tai có chùm lông như linh miêu, to gấp đôi mèo nhà mà hiền khô.',
       (_c('Nâu mướp', '#a77a4f', '#5a3f28', '#e9d3b5', '#4fa36a'), _c('Bạc mướp', '#c4c7cc', '#5d6168', '#f1f2f3', '#e9a23b'), _c('Đen khói', '#4a464b', '#2a272b', '#8d878e', '#e9a23b')), tier='hiem', size='m'),
    _b('xiem', 'cat', 'Mèo Xiêm', 'siamese', 3000, 'Hay “nói”', 'Kêu meo meo cả ngày như kể chuyện. Mặt nạ sô-cô-la, mắt xanh.',
       (_c('Seal point', '#f2e3cf', '#4e3a30', '#fbf4ea', '#4a90e2'), _c('Chocolate point', '#f5ead9', '#8a6248', '#fdf8f0', '#4a90e2'))),
))
ORDER = tuple(BREEDS)
DOGS = tuple(b for b in ORDER if BREEDS[b]['kind'] == 'dog')
CATS = tuple(b for b in ORDER if BREEDS[b]['kind'] == 'cat')
SHELTER = tuple(b for b in ORDER if BREEDS[b]['shelter'])
KIND_NAME = dict(dog='Chó', cat='Mèo')

# The shelter of Nhóm cứu hộ Chân Nhỏ (the adoption corner at Tiệm Thú Nhỏ Chú Út): adoption is free, a donation is
# welcome. Now and then a purebred someone gave up waits there too (SHELTER_RARE, one in RARE_EVERY days).
SHELTER_NAME = 'Góc nhận nuôi Chân Nhỏ'
SHOP_NAME = 'Tiệm Thú Nhỏ Chú Út'
SHELTER_RARE = ('poodle', 'pug', 'lap_xuong', 'chihuahua', 'aln', 'xiem', 'ba_tu')
RARE_EVERY = 3
SHELTER_SEEN = 3          # animals waiting each life day
DONATE = (0, 20, 50, 100, 200, 500)
DONATE_MAX = 100000
# Names the shelter gave them (the player may rename at adoption).
SHELTER_NAMES = ('Bông', 'Mực', 'Vàng', 'Mướp', 'Bơ', 'Lu', 'Ki', 'Mít', 'Đậu', 'Sữa', 'Na', 'Cốm', 'Bin', 'Tôm', 'Than',
                 'Khoai', 'Bí', 'Mochi', 'Xoài', 'Mèo Con', 'Bắp', 'Gạo', 'Nấm', 'Kem')

# ---------------------------------------------------------------- care
# Needs 0–100: f no bụng, j vui, c sạch sẽ, h sức khỏe. They drop each life day (DECAY); never to death, never away.
DECAY = dict(f=40, j=30, c=12, h=4)
SICK_DECAY = 6            # more health lost a day while hungry or dirty (under LOW)
LOW = 25
START = dict(f=80, j=80, c=80, h=90)
FULL = 92                 # a need this high refuses more of the same ("Bé no căng rồi")

FOODS = (   # (id, emoji, name, price, f, j)
    dict(id='com_nha', emoji='🍚', name='Cơm nhà trộn cá', price=0, f=30, j=0, line='Bé ăn sạch bát, liếm mép.'),
    dict(id='hat', emoji='🥣', name='Hạt thường', price=8, f=50, j=2, line='Rột rột rột… hết veo.'),
    dict(id='pate', emoji='🥫', name='Pate cao cấp', price=25, f=70, j=8, line='Bé ăn xong còn đòi liếm hộp.'),
    dict(id='tiec', emoji='🍖', name='Tiệc bò, cá hồi', price=80, f=100, j=20, line='Bé ăn như ngày Tết, xoay vòng vòng.'),
)
PLAY_FREE = 18            # playing by hand
TOYS = (    # uses: 0 = keeps for good. kind: dog / cat / both
    dict(id='bong', emoji='🎾', name='Bóng cao su', price=30, uses=10, j=35, kind='both'),
    dict(id='xuong', emoji='🦴', name='Xương gặm', price=40, uses=10, j=35, kind='dog'),
    dict(id='can_cau', emoji='🪶', name='Cần câu lông vũ', price=45, uses=10, j=40, kind='cat'),
    dict(id='chuot_bong', emoji='🐭', name='Chuột bông', price=35, uses=10, j=35, kind='cat'),
    dict(id='dia_bay', emoji='🥏', name='Đĩa bay', price=120, uses=0, j=40, kind='dog'),
    dict(id='thap_cao', emoji='🗼', name='Trụ cào móng', price=600, uses=0, j=45, kind='cat'),
    dict(id='chuot_robot', emoji='🤖', name='Chuột robot', price=900, uses=0, j=50, kind='both'),
)
BATH = dict(id='tam_nha', emoji='🛁', name='Tắm ở nhà', price=15, c=55, j=-5, line='Bé run run rồi lắc nước tung toé.')
GROOM = dict(id='spa', emoji='✂️', name='Spa Pet Care Mèo Mập', price=120, c=100, j=12, where='Pet Care Mèo Mập',
             line='Chị Mây tắm sấy, cắt móng, xịt thơm. Bé về nhà bồng bềnh.')
GROOM_CAT = 90            # cats: no haircut, a little cheaper
VET = dict(id='kham', emoji='🩺', name='Khám tổng quát', price=150, h=100, where='Phòng khám Thú y Cỏ May',
           line='Bác sĩ Cỏ May khám tai, mắt, răng, nghe tim. Bé khỏe re.')
VACCINE = dict(id='tiem', emoji='💉', name='Tiêm phòng', price=250, h=20, days=30, floor=50,
               line='Tiêm xong được thưởng bánh. Ba mươi ngày không lo ốm vặt.')

# ---------------------------------------------------------------- accessories (kept, one pet wears each copy)
SLOTS = (('neck', '📿', 'Vòng cổ'), ('head', '🎀', 'Nơ, mũ'), ('body', '👕', 'Áo'), ('bed', '🛏️', 'Ổ nằm'))
SLOT_IDS = tuple(s[0] for s in SLOTS)
ACCS = (
    dict(id='vong_chuong', slot='neck', emoji='🔔', name='Vòng chuông đỏ', price=60, color='#e05a4f'),
    dict(id='vong_da', slot='neck', emoji='📛', name='Vòng da khắc tên', price=150, color='#8a5a3a'),
    dict(id='vong_ngoc', slot='neck', emoji='🦪', name='Vòng ngọc trai', price=900, color='#f7f1ea'),
    dict(id='vong_vang', slot='neck', emoji='🥇', name='Vòng vàng 24K', price=6000, color='#e7b93e'),
    dict(id='no_hong', slot='head', emoji='🎀', name='Nơ hồng', price=40, color='#f28fb0'),
    dict(id='no_cham', slot='head', emoji='🎀', name='Nơ chấm bi', price=80, color='#5b8fd9'),
    dict(id='non_la', slot='head', emoji='👒', name='Nón lá mini', price=120, color='#e9cf8c'),
    dict(id='mu_ech', slot='head', emoji='🐸', name='Mũ ếch', price=160, color='#7cc47f'),
    dict(id='vuong_mien', slot='head', emoji='👑', name='Vương miện', price=2500, color='#f2c14e'),
    dict(id='ao_len', slot='body', emoji='🧶', name='Áo len', price=180, color='#e58b7a'),
    dict(id='ao_mua', slot='body', emoji='🧥', name='Áo mưa vàng', price=220, color='#f6cf45'),
    dict(id='ao_vn', slot='body', emoji='🇻🇳', name='Áo đội tuyển', price=300, color='#d8392f'),
    dict(id='ao_khung_long', slot='body', emoji='🦖', name='Hoodie khủng long', price=380, color='#79b86b'),
    dict(id='ao_dai', slot='body', emoji='👘', name='Áo dài mini', price=450, color='#d94f6e'),
    dict(id='vay_cong_chua', slot='body', emoji='👗', name='Váy công chúa', price=700, color='#c8a6ef'),
    dict(id='o_bong', slot='bed', emoji='🧺', name='Ổ bông', price=200, color='#f2b8c6'),
    dict(id='nem_may', slot='bed', emoji='☁️', name='Nệm mây', price=650, color='#cfe6f7'),
    dict(id='nha_go', slot='bed', emoji='🏠', name='Nhà gỗ nhỏ', price=1500, color='#d9a066'),
    dict(id='lau_dai', slot='bed', emoji='🏰', name='Lâu đài thú cưng', price=5000, color='#cdb8f0'),
)
ACC = {a['id']: a for a in ACCS}
TOY = {t['id']: t for t in TOYS}
FOOD = {f['id']: f for f in FOODS}

# ---------------------------------------------------------------- tricks (bond: one point per kind of care a day)
TRICKS = dict(
    dog=(('ngoi', '🐕', 'Ngồi', 3), ('bat_tay', '🤝', 'Bắt tay', 8), ('nam', '🛌', 'Nằm xuống', 14), ('lan', '🔄', 'Lăn tròn', 22),
         ('dung', '🙏', 'Đứng hai chân xin', 32), ('pang', '🔫', '“Pằng!” giả chết', 44), ('dep', '🩴', 'Tha dép về', 58)),
    cat=(('goi', '📣', 'Gọi là tới', 3), ('dap_tay', '🖐️', 'Đập tay', 8), ('ngoi', '🐈', 'Ngồi ngoan', 14), ('lan', '🔄', 'Lăn ra nũng', 22),
         ('dung', '🙏', 'Đứng hai chân', 32), ('nhay', '⭕', 'Nhảy qua vòng', 44), ('hop', '📦', 'Chui hộp theo lệnh', 58)),
)
# Photo-booth poses (the client draws them; the player's character stands beside).
POSES = (('sit', 'Ngồi ngoan'), ('happy', 'Vui tít'), ('walk', 'Dạo phố'), ('sleep', 'Ngủ say'))
FRAMES = (('nang', '🌼', 'Nắng mai'), ('tim', '💗', 'Tim hồng'), ('tet', '🧧', 'Tết'), ('sao', '⭐', 'Ngôi sao'))

# ---------------------------------------------------------------- limits
MAX_PETS = 3
MAX_FARM = 12
NAME_MAX = 16
SPIRIT = 1                # tinh thần once a life day, from a happy pet greeting you (small, capped)
WEEK_DAY_PTS = 5          # 'Bé cưng của tuần': at most this many points a life day per pet (cosmetic only)
