"""Nấu cơm gia đình: a hired home cook, one family's meal a day (plugin career).

Cô Hạnh, who cooked for weddings for twenty years, now finds home cooks for the families of the ward.
Each day she sends the player to one family (a young couple with a five-year-old, an old teacher who
eats soft and low-salt, a man on a diet, a big family on a tight budget; the same families come back).
What the job is:

* the request (``meal`` task, slot 0): how many eat, the market money, what the family likes and the one
  thing to watch (the child, the elder, the diet). The player plans a proper home meal: one canh, one
  món mặn, one món xào, one dish of rau, every dish checked against the family (a spicy dish for the
  child, a salty or chewy one for the elder, a fried or fatty one for the diet is a clear mistake) and
  the estimate kept inside the money;
* the market (two stalls): for every ingredient, look at it closely (a dull-eyed fish, a sticky cut, wilted
  greens), ask for another one when it is not fresh, buy enough portions (one phần feeds two), haggle a
  little if you like, and ask each stall for its receipt;
* the kitchen: the rice cooker with the water line (com's three lines: an elder eats it soft), the table
  (bowls and chopsticks for everyone, the bowl of nước mắm tasted and fixed with com's own rules), and every
  dish by hand: wash, cut (small for a child or an elder), season (light for an elder, rich when the family
  likes it), the right flame, and a real-time stop on the stove gauge (raw, done, overdone, burnt). Two
  burners: the slow dishes go on first so everything reaches the table together (a dish left more than
  WARM_S seconds goes cold; it can be warmed up again);
* the money: file each receipt in the family's market book and give back the change. A stall without a
  receipt is written from memory (the family notices).

Then the family pays the day (more for a bigger family, a little more each time they ask for you again),
sometimes tips, and later in the day may ask for one more dish (``extra`` tasks: a pot of cháo for the
elder, steamed egg for the child, chè after dinner…) from what is in their kitchen.

Mistakes go through consequences (cq.slip, cq.decide); money only through the engine's money().
The family's market money never touches the player's wallet: it lives on the task (purse).
Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
import itertools

from ..jsoncopy import tree_copy
from . import kit
from . import com
from .. import consequences as cq

ID = 'naucom'
GEN = 1

# ---------------------------------------------------------------- the meal
GROUPS = {
    'canh': dict(name='Canh', emoji='🍲'),
    'man': dict(name='Món mặn', emoji='🍖'),
    'xao': dict(name='Món xào', emoji='🍳'),
    'rau': dict(name='Rau', emoji='🥬'),
}
GROUP_ORDER = ('canh', 'man', 'xao', 'rau')
STALLS = {
    'thit': dict(name='Sạp thịt cá cô Ba', short='sạp thịt cá', emoji='🐟', who='Cô Ba'),
    'rau': dict(name='Sạp rau chị Tám', short='sạp rau', emoji='🥬', who='Chị Tám'),
}
# xu for one phần (enough for two people). 'home': already in the family's kitchen (extras only).
INGS = {
    'ca_loc': dict(name='Cá lóc', emoji='🐟', stall='thit', price=4, kind='fish'),
    'ca_basa': dict(name='Cá basa cắt khúc', emoji='🐟', stall='thit', price=3, kind='fish'),
    'ca_dieu_hong': dict(name='Cá diêu hồng', emoji='🐠', stall='thit', price=4, kind='fish'),
    'thit_bam': dict(name='Thịt heo bằm', emoji='🥩', stall='thit', price=2, kind='meat'),
    'thit_ba_roi': dict(name='Thịt ba rọi', emoji='🥓', stall='thit', price=3, kind='meat'),
    'ga': dict(name='Thịt gà', emoji='🍗', stall='thit', price=3, kind='meat'),
    'bo': dict(name='Thịt bò', emoji='🥩', stall='thit', price=5, kind='meat'),
    'muc': dict(name='Mực ống', emoji='🦑', stall='thit', price=4, kind='fish'),
    'tom': dict(name='Tôm sú', emoji='🦐', stall='thit', price=5, kind='fish'),
    'trung': dict(name='Trứng gà', emoji='🥚', stall='rau', price=1, kind='egg'),
    'dau_hu': dict(name='Đậu hũ non', emoji='🧈', stall='rau', price=1, kind='tofu'),
    'rau_chua': dict(name='Cà chua, thơm, bạc hà', emoji='🍅', stall='rau', price=1, kind='veg'),
    'bi_do': dict(name='Bí đỏ', emoji='🎃', stall='rau', price=1, kind='veg'),
    'rau_ngot': dict(name='Rau ngót', emoji='🌿', stall='rau', price=1, kind='veg'),
    'kho_qua': dict(name='Khổ qua', emoji='🥒', stall='rau', price=1, kind='veg'),
    'hanh_tay': dict(name='Hành tây', emoji='🧅', stall='rau', price=1, kind='veg'),
    'bi_xanh': dict(name='Bí xanh', emoji='🥒', stall='rau', price=1, kind='veg'),
    'su_su': dict(name='Su su, cà rốt', emoji='🥕', stall='rau', price=1, kind='veg'),
    'rau_muong': dict(name='Rau muống', emoji='🥬', stall='rau', price=1, kind='veg'),
    'cai_ngot': dict(name='Cải ngọt', emoji='🥬', stall='rau', price=1, kind='veg'),
    'bap_cai': dict(name='Bắp cải', emoji='🥬', stall='rau', price=1, kind='veg'),
    'dua_leo': dict(name='Dưa leo, rau sống', emoji='🥒', stall='rau', price=1, kind='veg'),
}
RAIN_UP = 1               # a rainy morning: greens cost one xu more a phần
TAGS = {'cay': '🌶️ cay', 'man': '🧂 mặn', 'beo': '🥓 nhiều mỡ', 'chien': '🍳 chiên', 'dai': '🦴 dai', 'cung': '🪨 cứng',
        'xuong': '🐟 nhiều xương', 'chua': '🍋 chua', 'mem': '🥄 mềm'}


def _d(name, group, emoji, ings, method, heat, tags=()):
    return dict(name=name, group=group, emoji=emoji, ings=list(ings), method=method, heat=heat, tags=list(tags))


DISHES = {
    'canh_chua': _d('Canh chua cá lóc', 'canh', '🍲', ('ca_loc', 'rau_chua'), 'nau', 'vua', ('chua',)),
    'canh_bi': _d('Canh bí đỏ thịt bằm', 'canh', '🎃', ('bi_do', 'thit_bam'), 'nau', 'vua', ('mem',)),
    'canh_rau_ngot': _d('Canh rau ngót thịt bằm', 'canh', '🌿', ('rau_ngot', 'thit_bam'), 'nau', 'vua', ('mem',)),
    'canh_kho_qua': _d('Canh khổ qua nhồi thịt', 'canh', '🥒', ('kho_qua', 'thit_bam'), 'nau', 'vua'),
    'thit_kho': _d('Thịt kho trứng', 'man', '🍖', ('thit_ba_roi', 'trung'), 'kho', 'nho', ('man', 'beo')),
    'ca_kho': _d('Cá kho tộ', 'man', '🐟', ('ca_basa',), 'kho', 'nho', ('man', 'xuong')),
    'ga_chien': _d('Gà chiên nước mắm', 'man', '🍗', ('ga',), 'chien', 'vua', ('chien', 'cung')),
    'dau_hu_sot': _d('Đậu hũ nhồi thịt sốt cà', 'man', '🍅', ('dau_hu', 'thit_bam'), 'nau', 'vua', ('mem',)),
    'ca_hap': _d('Cá diêu hồng hấp gừng', 'man', '🐠', ('ca_dieu_hong',), 'hap', 'vua', ('mem', 'xuong')),
    'tom_rim': _d('Tôm rim mặn ngọt', 'man', '🦐', ('tom',), 'kho', 'vua', ('man',)),
    'trung_hap': _d('Trứng hấp thịt bằm', 'man', '🥚', ('trung', 'thit_bam'), 'hap', 'vua', ('mem',)),
    'bo_xao': _d('Bò xào hành tây', 'xao', '🥩', ('bo', 'hanh_tay'), 'xao', 'lon', ('dai',)),
    'muc_xao': _d('Mực xào sả ớt', 'xao', '🦑', ('muc',), 'xao', 'lon', ('dai', 'cay')),
    'ga_xao_sa': _d('Gà xào sả ớt', 'xao', '🌶️', ('ga',), 'xao', 'lon', ('cay',)),
    'bi_xao': _d('Bí xanh xào tỏi', 'xao', '🥒', ('bi_xanh',), 'xao', 'lon', ('mem',)),
    'su_su_xao': _d('Su su, cà rốt xào', 'xao', '🥕', ('su_su',), 'xao', 'lon'),
    'rau_muong_luoc': _d('Rau muống luộc', 'rau', '🥬', ('rau_muong',), 'luoc', 'lon'),
    'cai_luoc': _d('Cải ngọt luộc', 'rau', '🥬', ('cai_ngot',), 'luoc', 'lon', ('mem',)),
    'bap_cai_luoc': _d('Bắp cải luộc', 'rau', '🥬', ('bap_cai',), 'luoc', 'lon', ('mem',)),
    'dua_leo': _d('Dưa leo, rau sống', 'rau', '🥒', ('dua_leo',), 'song', None, ('cung',)),
    # extras only: made from what is in the family's kitchen
    'chao': _d('Cháo thịt bằm', 'them', '🥣', (), 'nau', 'nho', ('mem',)),
    'che': _d('Chè đậu xanh', 'them', '🍮', (), 'nau', 'nho', ('mem',)),
}
MENU_DISHES = tuple(k for k, v in DISHES.items() if v['group'] in GROUPS)
METHODS = {   # (done from, done to) seconds on the right flame; past `burn` it catches
    'nau': dict(name='nấu', ok=(10, 20), burn=28),
    'kho': dict(name='kho', ok=(14, 26), burn=34),
    'chien': dict(name='chiên', ok=(8, 14), burn=20),
    'xao': dict(name='xào', ok=(6, 12), burn=18),
    'luoc': dict(name='luộc', ok=(5, 10), burn=15),
    'hap': dict(name='hấp', ok=(10, 18), burn=26),
    'song': dict(name='ăn sống', ok=(0, 0), burn=0),
}
DONE_Q = ('song', 'ok', 'qua', 'chay')
DONE_NOTE = {'song': 'chưa chín tới', 'ok': 'chín tới, thơm', 'qua': 'hơi quá lửa', 'chay': 'cháy, khét'}
CUTS = {'vua': 'Cắt vừa ăn', 'nho': 'Cắt nhỏ, thái mỏng'}
NEMS = {'nhat': 'Nêm nhạt', 'vua': 'Nêm vừa', 'dam': 'Nêm đậm'}
HEATS = {'nho': 'Lửa nhỏ', 'vua': 'Lửa vừa', 'lon': 'Lửa lớn'}
WATER = com.WATER         # the rice cooker's water line, as at dì Bảy's stall
RICE_S = 12               # real seconds before the rice is cooked
WARM_S = 90               # a dish left longer than this before the meal has gone cold
BURNERS = 2
BUY_MAX = 4               # phần of one ingredient in one go
BOWLS_MAX = 12

CONS = {
    'kid': dict(emoji='🧒', label='Có bé nhỏ', rule='Bé không ăn cay, sợ xương cá. Đồ ăn cắt nhỏ cho bé.',
                avoid=('cay', 'xuong'), cut='nho', nem=None, water='mot'),
    'elder': dict(emoji='👴', label='Có người già', rule='Ông ăn mềm, nhạt muối: tránh món mặn, món dai, món cứng. Cắt nhỏ, cơm nấu mềm.',
                  avoid=('man', 'dai', 'cung'), cut='nho', nem='nhat', water='ruoi'),
    'diet': dict(emoji='🥗', label='Có người ăn kiêng', rule='Anh Khoa đang giảm cân: không món chiên, không món nhiều mỡ.',
                 avoid=('chien', 'beo'), cut=None, nem=None, water='mot'),
    'dong': dict(emoji='👨‍👩‍👧‍👦', label='Nhà đông người', rule='Nhà đông miệng ăn: mua đủ phần cho cả nhà, tiền chợ tính từng đồng.',
                 avoid=(), cut=None, nem=None, water='mot'),
}
TASTES = {
    'chua': dict(label='Cả nhà mê canh chua', tag='chua', nem=None),
    'cay': dict(label='Anh Khoa thích có một món cay', tag='cay', nem=None),
    'dam': dict(label='Nhà ăn đậm đà', tag=None, nem='dam'),
    'thanh': dict(label='Nhà ăn thanh, nhạt', tag=None, nem='nhat'),
}
SALTY_HURTS = ('elder',)  # a salty dish here is a clear mistake (high blood pressure)

PEOPLE = [
    ('Cô Hạnh', 'Giới thiệu người nấu cơm nhà', 'Hai mươi năm nấu cỗ, giờ nhận lời tìm người nấu cơm cho các nhà quen trong phường.', 'warm'),
    ('Chị Mai', 'Mẹ bé Bin, nhân viên ngân hàng', 'Hai vợ chồng đi làm tới tối, bé Bin năm tuổi ăn gì cũng phải cắt nhỏ, không cay.', 'warm'),
    ('Ông Toàn', 'Thầy giáo về hưu, tám mươi hai tuổi', 'Răng yếu, huyết áp cao: ăn mềm, nhạt muối. Bà Toàn thì nhớ từng món ông ăn được.', 'picky'),
    ('Anh Khoa', 'Lập trình viên đang giảm cân', 'Chạy bộ mỗi sáng, đếm từng muỗng dầu. Không chiên, không mỡ, nhưng mê đồ cay.', 'genz'),
    ('Cô Lệ', 'Bán tạp hóa, nhà bảy miệng ăn', 'Con cháu ở chung một nhà, ăn đậm đà, tiền chợ tính từng đồng.', 'bossy'),
]
FAMILIES = [
    dict(id='mai', npc=1, name='Nhà chị Mai', emoji='👩‍👧', n=3, con='kid', taste='chua', min_day=1, weight=3,
         note='Bé Bin đi học về là đòi ăn liền.'),
    dict(id='toan', npc=2, name='Nhà ông Toàn', emoji='👴', n=3, con='elder', taste='thanh', min_day=2, weight=3,
         note='Bà Toàn dặn: ông vừa đi tái khám huyết áp về.'),
    dict(id='khoa', npc=3, name='Nhà anh Khoa', emoji='🏃', n=2, con='diet', taste='cay', min_day=2, weight=2,
         note='Anh Khoa với chị Vy ăn tối sau giờ chạy bộ.'),
    dict(id='le', npc=4, name='Nhà cô Lệ', emoji='👨‍👩‍👧‍👦', n=6, con='dong', taste='dam', min_day=3, weight=2,
         note='Mấy đứa cháu đi học về là đói meo.'),
]
FAM = {f['id']: f for f in FAMILIES}

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Chợ phường đông vừa, đồ tươi đủ cả.', weight=3),
    dict(id='mua', emoji='🌧️', label='Mưa sáng', hint='Mưa sáng, chợ vắng: rau đắt hơn một xu mỗi phần.', min_day=2, weight=2),
    dict(id='khach', emoji='🎉', label='Nhà có khách', hint='Nhà có khách tới chơi: thêm hai người ăn, tiền chợ cũng nhiều hơn.', min_day=2, weight=2),
    dict(id='cuoi_thang', emoji='📅', label='Cuối tháng', hint='Cuối tháng, tiền chợ eo hẹp: chọn món vừa túi tiền.', min_day=3, weight=1),
]
MOD = {m['id']: m for m in MODS}

# The pay: the day (more for a bigger family), a little more each time a family asks for you again.
WAGE_BASE = 30
WAGE_PER = 4
LOYAL_STEP = 2
LOYAL_MAX = 6
EXTRA_PAY = 10
# What the family takes off when the meal went wrong (consequences.decide → kind); a family never walks out.
CUT = dict(accept=0, grumble=0, discount=25, refund=50, walkout=50, refuse=50, remake=0)
REACT = dict(
    accept=('“Ngon quá, cả nhà ăn sạch nồi!”', '“Cơm nhà đúng nghĩa luôn đó.”'),
    grumble=('“Lần sau để ý giúp chị chút nhé.”', '“Cũng được, mà chưa được như lần trước.”'),
    discount=('“Hôm nay chị bớt chút công nhé, sai thế là phải chịu.”', '“Chị trừ một ít, coi như nhắc em.”'),
    refund=('“Bữa này chị chỉ tính nửa công thôi.”', '“Làm thế này chị chỉ trả được một nửa.”'),
)

# One more dish later in the day, from the family's kitchen: (family, dish, title, opening, note)
EXTRAS = [
    ('mai', 'trung_hap', 'Bé Bin ăn xế', 'Bé Bin ngủ trưa dậy đòi ăn. Em hấp giúp chị chén trứng thịt bằm, cắt nhỏ cho bé nha.', 'Trứng, thịt bằm trong tủ lạnh.'),
    ('mai', 'che', 'Chè cho cả nhà', 'Tối nay cả nhà xem phim, em nấu giúp chị nồi chè đậu xanh, ngọt vừa thôi.', 'Đậu xanh ngâm sẵn từ sáng.'),
    ('toan', 'chao', 'Cháo cho ông', 'Ông ăn cơm không quen, con nấu giúp bà nồi cháo thịt bằm thật nhừ, nhạt muối nghe.', 'Gạo, thịt bằm có sẵn trong bếp.'),
    ('toan', 'che', 'Chè đậu xanh cho bà', 'Bà thèm chén chè đậu xanh, con nấu ít đường thôi nghe, bà kiêng ngọt.', 'Đậu xanh trong hũ trên kệ.'),
    ('khoa', 'bi_xao', 'Thêm đĩa rau xào', 'Bạn anh ghé ăn ké, em xào thêm đĩa bí xanh nha, ít dầu thôi.', 'Bí xanh còn trong tủ lạnh.'),
    ('khoa', 'rau_muong_luoc', 'Rau luộc ăn tối', 'Tối anh chỉ ăn rau, em luộc giúp anh đĩa rau muống nha.', 'Rau muống còn một bó.'),
    ('le', 'rau_muong_luoc', 'Thêm đĩa rau cho cháu', 'Mấy đứa cháu ăn hết rau rồi, con luộc thêm đĩa nữa nghe, nêm đậm chút.', 'Rau muống mua dư hôm qua.'),
    ('le', 'chao', 'Nồi cháo cho đứa út', 'Thằng út hơi sốt, con nấu giúp cô nồi cháo thịt bằm, băm nhỏ nghe.', 'Gạo, thịt bằm có sẵn.'),
]
EXTRA_DISH_CUT = {'trung_hap': 'nho', 'chao': 'nho'}         # always small, whoever eats it
EXTRA_NEM = {('toan', 'che'): 'nhat', ('mai', 'che'): 'vua', ('le', 'rau_muong_luoc'): 'dam', ('khoa', 'bi_xao'): 'vua'}

KINDS = ('meal', 'extra')
STAGES = ('plan', 'market', 'cook', 'settle', 'done')

# What the families say on the way out, one line per visit, on and on across days.
REG_STORY = {
    1: ('Chị Mai: “Bé Bin hỏi hoài: mai cô nấu cơm có tới nữa không mẹ?”', 'Chị Mai được lên trưởng phòng, nhắn cảm ơn vì tối nào cũng có cơm nóng.',
        'Bé Bin vẽ tặng bức tranh cả nhà ngồi quanh mâm cơm, có cả bạn đeo tạp dề.', 'Chị Mai giới thiệu bạn cho mấy nhà trong chung cư.'),
    2: ('Ông Toàn: “Cá hấp mềm, ông ăn được hết chén cơm.”', 'Bà Toàn khoe huyết áp ông tháng này ổn hơn hẳn.',
        'Ông Toàn chép tặng bạn một bài thơ về bữa cơm nhà.'),
    3: ('Anh Khoa: “Ăn kiêng mà vẫn thấy ngon, lạ ghê.”', 'Anh Khoa xuống được ba ký, rủ bạn chạy bộ cuối tuần.',
        'Anh Khoa với chị Vy mời bạn dự đám cưới nhỏ ở quê.'),
    4: ('Cô Lệ: “Tiền chợ dư ra, cô để dành mua sữa cho mấy đứa nhỏ.”', 'Cô Lệ dúi cho bạn bịch khô cá nhà làm.',
        'Cô Lệ nói cả xóm ai cần người nấu cơm cũng chỉ tới bạn.'),
}

INTRO = dict(
    title='Giới thiệu nghề: nấu cơm gia đình',
    lead='Cô Hạnh giới thiệu bạn tới nấu cơm cho các nhà quen trong phường. Mỗi ngày một nhà: nghe dặn, '
         'lên thực đơn, đi chợ vừa túi tiền, về nấu cho kịp bữa rồi tính sổ chợ rõ ràng.',
    work=[('📝', 'Lên thực đơn: một canh, một mặn, một xào, một rau'), ('🧒', 'Nhớ người trong nhà: bé nhỏ, ông bà, người ăn kiêng'),
          ('🛒', 'Đi chợ: xem kỹ đồ tươi, mua đủ phần, xin hóa đơn'), ('🔪', 'Rửa, cắt, nêm, canh lửa từng món'),
          ('⏱️', 'Món lâu bắc trước, các món lên mâm cùng lúc'), ('📒', 'Ghi sổ chợ, gửi lại tiền thừa')],
    meet=[('👩‍👧', 'Chị Mai: bé Bin năm tuổi'), ('👴', 'Ông Toàn: ăn mềm, nhạt muối'),
          ('🏃', 'Anh Khoa: ăn kiêng mà mê cay'), ('👨‍👩‍👧‍👦', 'Cô Lệ: nhà bảy người, tiền chợ eo hẹp'),
          ('🌧️', 'Mưa sáng, nhà có khách, cuối tháng')],
    stars=[('🥗', 'Thực đơn hợp cả nhà'), ('🐟', 'Đồ tươi, đủ ăn'), ('🍲', 'Chín tới, vừa miệng'),
           ('♨️', 'Món nào lên mâm cũng nóng'), ('📒', 'Sổ chợ rõ từng xu')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='call', title='Chủ nhà gọi điện dặn thêm', emoji='📱', npc=1, min_day=2, tone='gentle', at='open', weight=3, mods=None,
         text='Điện thoại rung: “Em ơi, bữa nay bé Bin hơi ho, nhớ đừng cho đá vào nước nha, rau luộc chín kỹ giúp chị.”',
         options=[dict(id='note', label='Ghi lại lời dặn, dán lên cửa tủ lạnh', hint='', effects=dict(xp=3), good=True,
                       outcome='Tờ giấy dán ngay cửa tủ lạnh, nấu tới đâu nhìn tới đó.'),
                  dict(id='remember', label='Dạ, em nhớ rồi', hint='', effects=dict(), good=None,
                       outcome='Chị Mai cúp máy. Hy vọng là nhớ thật.')],
         default='remember'),
    dict(id='gas', title='Bình ga sắp hết', emoji='🔥', npc=0, min_day=2, tone='tense', at='open', weight=2, mods=None,
         text='Lửa bếp ga cứ phập phù, nghiêng bình nghe nhẹ tênh. Bình này chắc chỉ còn đủ một món.',
         options=[dict(id='call', label='Gọi đại lý đổi bình ngay, ứng tiền rồi xin hóa đơn', hint='Chủ nhà trả lại sau', effects=dict(patience=-2, xp=4), good=True,
                       outcome='Mười lăm phút sau có bình mới. Hóa đơn kẹp vào sổ chợ, chủ nhà gửi lại tiền đủ.'),
                  dict(id='risk', label='Cứ nấu, hết thì tính', hint='', effects=dict(patience=-4), good=None,
                       outcome='Đang kho dở thì tắt lửa, phải chạy đi đổi bình, cả nhà chờ cơm hơi lâu.')],
         default='risk'),
    dict(id='cat', title='Con mèo nhà rình cá', emoji='🐈', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Con mèo mướp của nhà ngồi chễm chệ trên ghế, mắt dán vào rổ cá vừa mua về.',
         options=[dict(id='cover', label='Đậy lồng bàn, cất cá vào tủ lạnh', hint='', effects=dict(xp=3), good=True,
                       outcome='Mèo ngáp một cái rồi bỏ đi tìm chỗ nằm.'),
                  dict(id='shoo', label='Xua mèo ra sân', hint='', effects=dict(), good=None,
                       outcome='Mèo ra sân được một lúc rồi lại lẻn vào.'),
                  dict(id='feed', label='Cho mèo miếng cá cho xong', hint='', effects=dict(review=[2, 'Người nấu cơm cho mèo ăn cá của nhà, không hỏi một câu.']), good=False,
                       outcome='Mèo ăn xong còn đòi thêm. Chủ nhà nhìn rổ cá vơi đi, không nói gì.')],
         default='shoo'),
    dict(id='neighbor', title='Hàng xóm sang hỏi mượn', emoji='🙋', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Bà hàng xóm ló đầu qua cửa: “Con ơi, cho bà mượn cái nồi áp suất của nhà một bữa nghe.”',
         options=[dict(id='ask', label='Dạ để con nhắn hỏi chủ nhà đã', hint='', effects=dict(xp=3), good=True,
                       outcome='Chủ nhà nhắn lại: “Cho bà mượn đi em.” Bà hàng xóm cảm ơn rối rít.'),
                  dict(id='lend', label='Đưa luôn cho bà', hint='', effects=dict(review=[3, 'Người nấu cơm tự cho hàng xóm mượn đồ, không hỏi chủ nhà.']), good=False,
                       outcome='Tối chủ nhà tìm nồi áp suất không thấy, hơi phật ý.'),
                  dict(id='no', label='Dạ con không dám', hint='', effects=dict(), good=None,
                       outcome='Bà hàng xóm gật gù rồi về.')],
         default='no'),
    dict(id='rain_market', title='Mưa ướt hết giỏ chợ', emoji='🌧️', npc=0, min_day=2, tone='gentle', at='open', weight=3, mods=('mua',),
         text='Mưa xối xả lúc ra chợ, giỏ đi chợ với tờ danh sách món ướt sũng.',
         options=[dict(id='bag', label='Mượn túi nilon bọc giỏ, chép lại danh sách', hint='', effects=dict(xp=3), good=True,
                       outcome='Giỏ khô ráo, danh sách rõ ràng, đi chợ không sót món nào.'),
                  dict(id='go', label='Cứ đi, về rồi tính', hint='', effects=dict(patience=-2), good=None,
                       outcome='Về tới nhà, mấy bó rau dập nát vì nước mưa.')],
         default='go'),
    dict(id='guest_extra', title='Khách tới sớm hơn hẹn', emoji='🎉', npc=0, min_day=2, tone='tense', at='open', weight=3, mods=('khach',),
         text='Khách của nhà tới sớm cả tiếng, ngồi chờ ở phòng khách. Chủ nhà nhắn: “Em pha giúp ấm trà mời khách nha.”',
         options=[dict(id='tea', label='Pha ấm trà, bưng đĩa trái cây ra mời', hint='', effects=dict(xp=4), good=True,
                       outcome='Khách vui vẻ ngồi chờ, khen nhà có người nấu cơm chu đáo.'),
                  dict(id='later', label='Nấu xong rồi pha', hint='', effects=dict(patience=-3), good=None,
                       outcome='Khách ngồi bấm điện thoại, chủ nhà hơi ngại.')],
         default='later'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='NC-S01', title='Canh hơi mặn với ông', npc=2, tone='tense', min_day=2,
         opening='Bà Toàn múc thử chén canh, nhăn mặt: “Con ơi, canh này ông ăn không được đâu, mặn quá, ông đang uống thuốc huyết áp.”',
         swap='Bạn là bà Toàn, ngày nào cũng canh từng bữa ăn cho ông.',
         facts=[dict(id='salt', title='Nêm nếm', source='Bếp', text='Nồi canh nêm vừa theo khẩu vị người trẻ, chưa nêm nhạt cho ông.'),
                dict(id='rule', title='Lời dặn', source='Bà Toàn', text='Ông huyết áp cao, bác sĩ dặn ăn nhạt muối.'),
                dict(id='water', title='Nồi canh', source='Bếp', text='Trong nồi còn nhiều nước dùng, bí còn sống, thêm nước được.')],
         options=[dict(id='fix', label='Xin lỗi bà, múc riêng cho ông, thêm nước nấu lại cho nhạt', requires=['salt', 'rule'], quality='good', stars=5,
                       review='Canh hơi mặn nhưng người nấu sửa ngay, nấu riêng cho ông. Chu đáo.',
                       outcome='Ông Toàn ăn hết chén canh, gật gù: “Vừa rồi đó.”',
                       perspectives=[dict(who='Bà Toàn', emoji='👵', text='Biết lỗi, sửa liền là được.'),
                                     dict(who='Cô Hạnh', emoji='👩‍🍳', text='Nhà có người già thì nêm nhạt trước, ai ăn đậm thì chấm thêm.')]),
                  dict(id='sauce', label='Dặn ông ăn ít canh thôi', requires=['rule'], quality='ok', stars=3,
                       review='Bảo ông ăn ít canh thì ông ăn gì.',
                       outcome='Ông Toàn ăn cơm với rau luộc, chén canh để nguyên.',
                       perspectives=[dict(who='Ông Toàn', emoji='👴', text='Thèm chén canh nóng mà không dám ăn.'),
                                     dict(who='Bà Toàn', emoji='👵', text='Nấu cho ông mà ông không ăn được.')]),
                  dict(id='deny', label='“Con nêm có chút xíu à bà”', quality='bad', stars=1,
                       review='Ông đang uống thuốc huyết áp mà còn cãi là có chút xíu.',
                       outcome='Bà Toàn lặng lẽ đổ chén canh, nấu gói mì cho ông.',
                       perspectives=[dict(who='Bà Toàn', emoji='😞', text='Sức khỏe của ông đâu phải chuyện chút xíu.'),
                                     dict(who='Cô Hạnh', emoji='👩‍🍳', text='Mất một nhà quen vì một muỗng muối.')])],
         lesson='Nhà có người già, huyết áp cao: nêm nhạt từ đầu, ai ăn đậm thì chấm thêm nước mắm.'),
    dict(id='NC-S02', title='Sổ chợ lệch hai xu', npc=4, tone='tense', min_day=3,
         opening='Cô Lệ cộng lại sổ chợ, gõ bút xuống bàn: “Tiền đưa ba mươi lăm, hóa đơn ba mươi mốt, sao trả lại cô có hai xu?”',
         facts=[dict(id='bill', title='Hóa đơn', source='Sổ chợ', text='Sạp rau không có hóa đơn, bạn ghi tay theo trí nhớ.'),
                dict(id='coins', title='Túi tiền', source='Giỏ chợ', text='Trong túi áo còn hai xu lẻ chưa bỏ vào ví tiền chợ.'),
                dict(id='price', title='Giá rau', source='Chị Tám', text='Chị Tám bán rau xác nhận: bó rau muống hai xu chứ không phải bốn.')],
         options=[dict(id='check', label='Lục lại túi, gửi đủ hai xu, nhờ chị Tám nhắn giá cho cô', requires=['coins', 'price'], quality='good', stars=5,
                       review='Sổ chợ lệch chút xíu nhưng người nấu kiểm lại đàng hoàng, gửi đủ từng xu.',
                       outcome='Cô Lệ cười: “Vậy mới yên tâm giao tiền chợ chớ.”',
                       perspectives=[dict(who='Cô Lệ', emoji='🧮', text='Tiền chợ là tiền cả nhà, phải rõ.'),
                                     dict(who='Cô Hạnh', emoji='👩‍🍳', text='Sạp nào cũng xin hóa đơn thì khỏi lo.')]),
                  dict(id='pay', label='Bù hai xu tiền túi cho xong', requires=['bill'], quality='ok', stars=3,
                       review='Bù tiền thì được, nhưng sổ vẫn không rõ đi đâu.',
                       outcome='Cô Lệ cầm hai xu, vẫn còn nhíu mày.',
                       perspectives=[dict(who='Cô Lệ', emoji='🤨', text='Cô cần biết tiền đi đâu, đâu cần con bù.'),
                                     dict(who='Chị Tám', emoji='🥬', text='Lần sau ghé sạp chị ghi hóa đơn cho.')]),
                  dict(id='deny', label='“Con nhớ là đúng mà cô”', quality='bad', stars=1,
                       review='Tiền chợ lệch mà còn nói nhớ đúng. Không giao tiền nữa.',
                       outcome='Cô Lệ cất sổ, mấy hôm sau nhờ người khác đi chợ.',
                       perspectives=[dict(who='Cô Lệ', emoji='😠', text='Tiền lệch mà không chịu xem lại.'),
                                     dict(who='Cô Hạnh', emoji='👩‍🍳', text='Mất lòng tin vì hai xu thì tiếc lắm.')])],
         lesson='Sạp nào cũng xin hóa đơn, tiền thừa để riêng một túi. Lệch thì kiểm lại trước mặt chủ nhà.'),
    dict(id='NC-S03', title='Bé Bin không chịu ăn rau', npc=1, tone='gentle', min_day=2,
         opening='Bé Bin đẩy chén rau ra: “Con hông ăn rau đâu, rau dai nhách à!” Chị Mai nhìn bạn, cười trừ.',
         facts=[dict(id='cut', title='Đĩa rau', source='Mâm cơm', text='Rau cắt khúc dài, bé năm tuổi khó nhai.'),
                dict(id='kid', title='Bé Bin', source='Chị Mai', text='Bé thích ăn rau chan nước canh, cắt nhỏ.'),
                dict(id='left', title='Trong bếp', source='Bếp', text='Rau còn trong rổ, cắt nhỏ chan canh được.')],
         options=[dict(id='redo', label='Cắt nhỏ chén rau, chan chút nước canh cho bé', requires=['cut', 'kid'], quality='good', stars=5,
                       review='Bé nhà tôi không chịu ăn rau mà người nấu dỗ được, cắt nhỏ chan canh. Khéo quá.',
                       outcome='Bé Bin ăn hết chén, còn xin thêm.',
                       perspectives=[dict(who='Chị Mai', emoji='👩', text='Bé chịu ăn rau là mừng rồi.'),
                                     dict(who='Bé Bin', emoji='🧒', text='Rau mềm, ngon!')]),
                  dict(id='candy', label='Hứa cho bé kẹo nếu ăn hết', requires=['kid'], quality='ok', stars=3,
                       review='Dỗ bằng kẹo thì bé ăn, mà mẹ không thích lắm.',
                       outcome='Bé Bin ăn vội mấy cọng rồi chìa tay xin kẹo.',
                       perspectives=[dict(who='Chị Mai', emoji='😅', text='Chị đang tập cho bé bớt ăn kẹo.')]),
                  dict(id='force', label='“Ăn đi, rau tốt cho con mà”', quality='bad', stars=2,
                       review='Ép bé ăn, bé khóc cả bữa.',
                       outcome='Bé Bin mếu máo, chị Mai phải bế ra dỗ.',
                       perspectives=[dict(who='Bé Bin', emoji='😭', text='Con hông thích!'),
                                     dict(who='Chị Mai', emoji='😟', text='Bé năm tuổi, phải dỗ chứ đừng ép.')])],
         lesson='Nhà có bé nhỏ: cắt nhỏ, nấu mềm, không cay. Bé không chịu ăn thì dỗ, đừng ép.'),
]


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def family_of(day: int) -> dict:
    """Which family asks for you on this day (never the same one two days running when another can)."""
    return kit.daily(ID + '-fam', day, FAMILIES)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def portions(n: int) -> int:
    """Phần to buy of each ingredient: one phần feeds two."""
    return (int(n) + 1) // 2


def unit_price(ing: str, mod: str) -> int:
    x = INGS[ing]
    return x['price'] + (RAIN_UP if mod == 'mua' and x['stall'] == 'rau' else 0)


def needs_of(menu: dict, n: int) -> dict:
    """{ingredient: phần to buy} for a menu (an ingredient in two dishes is bought for both)."""
    out = {}
    for g in GROUP_ORDER:
        k = menu.get(g)
        for ing in DISHES[k]['ings'] if k else ():
            out[ing] = out.get(ing, 0) + portions(n)
    return out


def menu_cost(menu: dict, n: int, mod: str) -> int:
    return sum(unit_price(i, mod) * q for i, q in needs_of(menu, n).items())


def clashes(dish: str, con: str) -> list:
    return [g for g in DISHES[dish]['tags'] if g in CONS[con]['avoid']]


def _fits(menu: dict, con: str, taste: str) -> bool:
    tag = TASTES[taste]['tag']
    return (all(not clashes(k, con) for k in menu.values())
            and (tag is None or any(tag in DISHES[k]['tags'] for k in menu.values())))


_BUDGET: dict = {}


def cheapest(n: int, con: str, taste: str, mod: str) -> int:
    """The cost of the cheapest meal that suits the family (the budget is built on it)."""
    key = (n, con, taste, mod)
    if key not in _BUDGET:
        groups = [[k for k in MENU_DISHES if DISHES[k]['group'] == g] for g in GROUP_ORDER]
        best = None
        for combo in itertools.product(*groups):
            menu = dict(zip(GROUP_ORDER, combo))
            if _fits(menu, con, taste):
                v = menu_cost(menu, n, mod)
                best = v if best is None or v < best else best
        _BUDGET[key] = best
    return _BUDGET[key]


def budget_for(n: int, con: str, taste: str, mod: str) -> int:
    low = cheapest(n, con, taste, mod)
    rate = 118 if mod == 'cuoi_thang' else 135
    b = low * rate // 100 + 2
    return max(low + 1, -(-b // 5) * 5)


def want_nem(needs: dict, dish: str | None = None) -> str:
    x = needs.get('x')
    if x and (needs['fam'], x) in EXTRA_NEM:
        return EXTRA_NEM[(needs['fam'], x)]
    return CONS[needs['con']]['nem'] or TASTES[needs['taste']]['nem'] or 'vua'


def want_cut(needs: dict, dish: str) -> str | None:
    if needs.get('x') in EXTRA_DISH_CUT:
        return EXTRA_DISH_CUT[needs['x']]
    return CONS[needs['con']]['cut']


def judge(method: str, secs: float) -> str:
    m = METHODS[method]
    lo, hi = m['ok']
    return 'song' if secs < lo else 'ok' if secs <= hi else 'qua' if secs <= m['burn'] else 'chay'


def dish_ready(st: dict) -> bool:
    return st.get('done') is not None


# ================================================================ tasks
def _kind(day: int, slot: int) -> str:
    return 'meal' if slot == 0 else 'extra'


def _hidden(day: int, slot: int, tid: str) -> dict:
    """What the player finds out by doing: the market's lots, the sellers' mood, last night's bowl of nước mắm."""
    lots = {}
    for ing, x in INGS.items():
        if day == 1:
            lots[ing] = 'uon' if ing == 'ca_loc' else 'tuoi'      # the first market teaches the fish's eye
        else:
            r = kit.rng(ID, 'lot', tid, ing).randrange(100)
            lots[ing] = 'uon' if r < (12 if x['kind'] in ('egg', 'tofu') else 26) else 'tuoi'
    haggle = {k: kit.rng(ID, 'haggle', tid, k).randrange(100) < 60 for k in STALLS}
    if day == 1:
        mam = 'man'
    else:
        r = kit.rng(ID, 'mam', tid).randrange(100)
        mam = 'ok' if r < 45 else ('man', 'lat', 'ngot', 'chua')[r % 4]
    return dict(lots=lots, haggle=haggle, mam=mam)


def make_task(day: int, slot: int, serial: int) -> dict:
    fam = family_of(day)
    mod = mod_of(day)['id']
    kind = _kind(day, slot)
    n = fam['n'] + (2 if mod == 'khach' else 0) + (kit.rng(ID, 'n', day).randrange(2) if fam['id'] == 'le' else 0)
    tid = f'{ID}-{day:04d}-{slot:02d}'
    common = dict(gen=GEN, stage='plan' if kind == 'meal' else 'cook', menu={}, cart={}, bills={}, purse=0, rice=None,
                  dishes={}, table=None, filed=[], story=None, _key=_hidden(day, slot, tid))
    if kind == 'meal':
        budget = budget_for(n, fam['con'], fam['taste'], mod)
        needs = dict(fam=fam['id'], n=n, budget=budget, con=fam['con'], taste=fam['taste'], mod=mod, note=fam['note'], x=None)
        title = f'Bữa cơm {_lower(fam["name"])}'
        opening = (f'Cô Hạnh nhắn: “Hôm nay con nấu cho {_lower(fam["name"])} nghe. Chủ nhà để tiền chợ trên bàn, '
                   f'dặn gì con nghe kỹ rồi lên thực đơn.”')
        return kit.base_task(ID, day, slot, serial, fam['npc'], title, opening, kind='meal', needs=needs, **common)
    pool = [e for e in EXTRAS if e[0] == fam['id']]
    off = kit.rng(ID, 'extra', day).randrange(len(pool))
    _, dish, title, opening, note = pool[(off + slot - 1) % len(pool)]
    needs = dict(fam=fam['id'], n=n, budget=0, con=fam['con'], taste=fam['taste'], mod=mod, note=note, x=dish)
    common['stage'] = 'cook'
    return kit.base_task(ID, day, slot, serial, fam['npc'], title, opening, kind='extra', needs=needs, **common)


FIXED = ('needs', '_key')


def on_task(s: dict, c: dict, t: dict) -> None:
    return None


# ================================================================ the career's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, meals=0, extras=0, spent=0, budget=0, back=0, cold=0, swaps=0)


def initial() -> dict:
    return dict(v=1, intro=False, families={}, today=_fresh_today(0),
                stats=dict(meals=0, extras=0, clean=0, cold=0, raw=0, swaps=0, receipts=0), desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


# ================================================================ the actions
FREE = ('nc_intro',)
TICKING = ('nc_plan', 'nc_home', 'nc_fire', 'nc_serve', 'nc_done', 'nc_bring')
PHYSICAL = ()             # nobody queues at a family's kitchen: waiting costs no patience


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'nc_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Cô Hạnh vừa nhắn địa chỉ nhà hôm nay.')
    desk = d['desk']
    if name == 'nc_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện trong nhà, quyết xong rồi làm tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có trong việc nấu cơm nhà.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, stages=None, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc việc nấu cơm nhà.')
    kit.need(t['known'], 'Nghe chủ nhà dặn đã nhé.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    if stages:
        kit.need(t['stage'] in stages, {'plan': 'Lên thực đơn xong đã nhé.', 'market': 'Việc này làm ở chợ.',
                                        'cook': 'Việc này làm trong bếp.', 'settle': 'Dọn cơm xong mới tính sổ chợ.',
                                        'done': 'Bữa này xong rồi.'}.get(stages[0], 'Chưa tới bước này.'))
    return t


def _slip(t: dict, code: str, sev: int, text: str, note: str = '', safety: bool = False) -> None:
    """One mistake of each kind on a task (the family names it once, however many dishes it touches)."""
    if not any(r['code'] == code for r in cq.slips(t)):
        t['mistakes'] += 1
    cq.slip(t, code, sev, text, note, safety)


def _fam(t: dict) -> dict:
    return FAM[t['needs']['fam']]


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Chủ nhà'


# ---------------------------------------------------------------- the plan
def _pick(s, c, d, p):
    t = _task(c, p, ('plan',), ('meal',))
    g = kit.one_of(p.get('group'), GROUPS, 'Chọn món cho nhóm nào?')
    k = kit.one_of(p.get('dish'), [x for x in MENU_DISHES if DISHES[x]['group'] == g], 'Món này không có trong nhóm.')
    kit.start_work(t)
    if t['menu'].get(g) == k:
        t['menu'].pop(g)
        return dict(message=f'Bỏ {_lower(DISHES[k]["name"])} ra khỏi thực đơn.')
    t['menu'][g] = k
    n = t['needs']
    est = menu_cost(t['menu'], n['n'], n['mod'])
    return dict(message=f'{DISHES[k]["emoji"]} {DISHES[k]["name"]} vào thực đơn · dự tính {est}/{n["budget"]} xu.')


def _plan(s, c, d, p):
    t = _task(c, p, ('plan',), ('meal',))
    n = t['needs']
    miss = [GROUPS[g]['name'] for g in GROUP_ORDER if g not in t['menu']]
    kit.need(not miss, f'Thực đơn còn thiếu: {", ".join(miss).lower()}.')
    est = menu_cost(t['menu'], n['n'], n['mod'])
    kit.need(est <= n['budget'], f'Thực đơn dự tính {est} xu, quá tiền chợ {est - n["budget"]} xu: đổi món rẻ hơn nhé.')
    con = CONS[n['con']]
    bad = [(k, clashes(k, n['con'])) for k in t['menu'].values()]
    bad = [(k, tags) for k, tags in bad if tags]
    if bad:
        k, tags = bad[0]
        what = ', '.join(TAGS[x].split(' ', 1)[1] for x in tags)
        _slip(t, 'clash', 2, f'{DISHES[k]["name"]} {what}, nhà tôi đã dặn rồi mà. {con["rule"]}', 'món không hợp người trong nhà')
    tag = TASTES[n['taste']]['tag']
    if tag and not any(tag in DISHES[k]['tags'] for k in t['menu'].values()):
        _slip(t, 'taste', 1, f'Đã dặn {_lower(TASTES[n["taste"]]["label"])} mà bữa nay không có.', 'quên khẩu vị nhà')
    needs = needs_of(t['menu'], n['n'])
    t['cart'] = {ing: dict(seen=False, swap=False, n=0, paid=0) for ing in needs}
    t['bills'] = {st: dict(paid=0, off=0, haggle=None, receipt=False) for st in STALLS if any(INGS[i]['stall'] == st for i in needs)}
    t['purse'] = n['budget']
    t['stage'] = 'market'
    kit.start_work(t)
    return dict(message=f'📝 Chốt thực đơn: {", ".join(_lower(DISHES[t["menu"][g]]["name"]) for g in GROUP_ORDER)}. '
                        f'Cầm {n["budget"]} xu tiền chợ, xách giỏ ra chợ thôi.')


# ---------------------------------------------------------------- the market
LOOK = {
    'fish': ('Mắt trong, mang đỏ tươi, ấn vào thịt đàn hồi.', 'Mắt đục, mang thâm, ấn vào thịt lõm không lên.'),
    'meat': ('Thịt hồng tươi, mỡ trắng, sờ khô ráo.', 'Thịt tái màu, sờ nhớt tay, hơi có mùi.'),
    'veg': ('Lá xanh mướt, cuống giòn, bẻ nghe tách.', 'Lá úa vàng, cuống dập, héo rũ.'),
    'egg': ('Vỏ trứng nhám, lắc nhẹ không nghe óc ách.', 'Lắc nhẹ nghe óc ách, vỏ bóng láng.'),
    'tofu': ('Đậu trắng mịn, thơm mùi đậu nành.', 'Đậu ngả vàng, sờ nhớt, hơi chua.'),
}


def _lot(t: dict, ing: str) -> str:
    row = t['cart'].get(ing) or {}
    return 'tuoi' if row.get('swap') else t['_key']['lots'][ing]


def _ing(t: dict, p: dict) -> str:
    return kit.one_of(p.get('ing'), t['cart'], 'Món này không có trong danh sách đi chợ.')


def _look(s, c, d, p):
    t = _task(c, p, ('market',), ('meal',))
    ing = _ing(t, p)
    row = t['cart'][ing]
    row['seen'] = True
    q = _lot(t, ing)
    x = INGS[ing]
    return dict(message=f'👀 {x["emoji"]} {x["name"]}: {LOOK[x["kind"]][0 if q == "tuoi" else 1]}')


def _swap(s, c, d, p):
    t = _task(c, p, ('market',), ('meal',))
    ing = _ing(t, p)
    row = t['cart'][ing]
    kit.need(row['n'] == 0, 'Mua rồi. Trả lại trước rồi hẵng đổi.')
    kit.need(not row['swap'], 'Người bán đã lựa cho phần ngon nhất rồi.')
    row.update(swap=True, seen=True)
    x = INGS[ing]
    who = STALLS[x['stall']]['who']
    if t['_key']['lots'][ing] == 'uon':
        d['today']['swaps'] += 1
        d['stats']['swaps'] += 1
    return dict(message=f'🔄 {who} lựa phần khác: {LOOK[x["kind"]][0]}')


def _buy(s, c, d, p):
    t = _task(c, p, ('market',), ('meal',))
    ing = _ing(t, p)
    row = t['cart'][ing]
    kit.need(row['n'] == 0, f'{INGS[ing]["name"]} mua rồi. Muốn đổi số phần thì trả lại trước.')
    n = kit.integer(p.get('n'), 1, BUY_MAX)
    price = unit_price(ing, t['needs']['mod']) * n
    kit.need(t['purse'] >= price, f'Ví tiền chợ còn {t["purse"]} xu, không đủ {price} xu.')
    x = INGS[ing]
    bill = t['bills'][x['stall']]
    t['purse'] -= price
    row.update(n=n, paid=price, q=_lot(t, ing))
    again = bill['receipt']
    bill['paid'] += price
    bill['receipt'] = False
    kit.start_work(t)
    tail = ' Hóa đơn cũ không tính món này: xin ghi lại nhé.' if again else ''
    return dict(message=f'🛒 Mua {n} phần {_lower(x["name"])} · {price} xu. Ví tiền chợ còn {t["purse"]} xu.{tail}')


def _return(s, c, d, p):
    t = _task(c, p, ('market',), ('meal',))
    ing = _ing(t, p)
    row = t['cart'][ing]
    kit.need(row['n'] > 0, 'Món này chưa mua.')
    bill = t['bills'][INGS[ing]['stall']]
    kit.need(bill['haggle'] != 'ok', 'Đã xin bớt ở sạp này rồi, trả lại thì ngại lắm.')
    back = row['paid']
    t['purse'] += back
    bill['paid'] -= back
    bill['receipt'] = False
    row.update(n=0, paid=0)
    row.pop('q', None)
    return dict(message=f'↩️ Trả lại {_lower(INGS[ing]["name"])}, nhận lại {back} xu.')


def _stall(t: dict, p: dict) -> str:
    return kit.one_of(p.get('stall'), t['bills'], 'Hôm nay không mua gì ở sạp này.')


def _haggle(s, c, d, p):
    t = _task(c, p, ('market',), ('meal',))
    st = _stall(t, p)
    bill = t['bills'][st]
    kit.need(bill['paid'] >= 3, 'Mua ít quá, xin bớt người ta cười cho.')
    kit.need(bill['haggle'] is None, 'Xin bớt một lần thôi, người ta còn buôn bán.')
    who = STALLS[st]['who']
    if t['_key']['haggle'][st]:
        off = min(bill['paid'] - 1, 2 if bill['paid'] >= 10 else 1)
        bill.update(haggle='ok', off=off)
        bill['paid'] -= off
        t['purse'] += off
        bill['receipt'] = False
        return dict(message=f'🙏 {who} cười: “Thôi bớt cho con {off} xu, mai ghé nữa nghen.”', celebrate=True)
    bill['haggle'] = 'no'
    return dict(message=f'🙏 {who} lắc đầu: “Giá này rẻ rồi con, cô bán đúng giá mà.”')


def _receipt(s, c, d, p):
    t = _task(c, p, ('market',), ('meal',))
    st = _stall(t, p)
    bill = t['bills'][st]
    kit.need(bill['paid'] > 0, 'Chưa mua gì ở sạp này.')
    kit.need(not bill['receipt'], 'Đã có hóa đơn rồi.')
    bill['receipt'] = True
    return dict(message=f'🧾 {STALLS[st]["who"]} ghi hóa đơn: {bill["paid"]} xu, ký tên rõ ràng.')


def _home(s, c, d, p):
    t = _task(c, p, ('market',), ('meal',))
    left = [INGS[i]['name'] for i, row in t['cart'].items() if row['n'] <= 0]
    kit.need(not left, f'Còn chưa mua: {", ".join(_lower(x) for x in left)}.')
    t['stage'] = 'cook'
    t['dishes'] = {t['menu'][g]: _fresh_dish() for g in GROUP_ORDER}
    t['table'] = dict(bowls=0, mam=t['_key']['mam'], tasted=False)
    spent = t['needs']['budget'] - t['purse']
    return dict(message=f'🏠 Xách giỏ về nhà: chợ hết {spent} xu, ví tiền chợ còn {t["purse"]} xu. Vo gạo bắc nồi cơm trước nhé.')


# ---------------------------------------------------------------- the kitchen
def _fresh_dish() -> dict:
    return dict(wash=False, cut=None, nem=None, heat=None, start=None, done=None, q=None, warm=0)


def _dish(t: dict, p: dict) -> tuple[str, dict]:
    k = kit.one_of(p.get('dish'), t['dishes'], 'Món này không có trong bữa nay.')
    return k, t['dishes'][k]


def _cooking(c: dict) -> int:
    return sum(1 for t in c['tasks'] if t.get('career') == ID and t['status'] not in ('completed', 'referred', 'cancelled')
               for st in (t.get('dishes') or {}).values() if st.get('start') is not None and st.get('done') is None)


def _need_meal_served(c: dict, t: dict) -> None:
    if t['kind'] != 'extra':
        return
    meal = next((x for x in c['tasks'] if x.get('career') == ID and x['day'] == t['day'] and x.get('kind') == 'meal'
                 and x['status'] not in ('referred', 'cancelled')), None)
    kit.need(meal is None or meal['stage'] in ('settle', 'done'), 'Dọn bữa chính xong đã rồi nấu thêm nhé.')


def _ensure_extra(c: dict, t: dict) -> None:
    if t['kind'] == 'extra' and not t['dishes']:
        t['dishes'] = {t['needs']['x']: _fresh_dish()}


def _rice(s, c, d, p):
    t = _task(c, p, ('cook',), ('meal',))
    w = kit.one_of(p.get('water'), WATER, 'Đổ nước tới đâu?')
    kit.need(t['rice'] is None, 'Nồi cơm đang nấu rồi.')
    t['rice'] = dict(w=w, at=round(kit.now() + RICE_S, 3))
    return dict(message=f'🍚 Vo gạo hai nước, đổ nước {_lower(WATER[w])}, bấm nút nồi cơm. Chừng {RICE_S} giây nữa cơm chín.')


def _bowls(s, c, d, p):
    t = _task(c, p, ('cook',), ('meal',))
    n = kit.integer(p.get('n'), 1, BOWLS_MAX)
    t['table']['bowls'] = n
    return dict(message=f'🥢 Bày {n} bộ chén đũa quanh mâm.')


def _taste(s, c, d, p):
    t = _task(c, p, ('cook',), ('meal',))
    m = t['table']
    m['tasted'] = True
    return dict(message=f'🥄 Chấm đầu đũa nếm chén nước mắm: {com.TASTE[m["mam"]]}')


def _fix(s, c, d, p):
    t = _task(c, p, ('cook',), ('meal',))
    add = kit.one_of(p.get('add'), com.FIX, 'Thêm gì vào chén nước mắm?')
    m = t['table']
    kit.need(m['tasted'], 'Nếm thử trước đã rồi hẵng pha thêm.')
    before = m['mam']
    if before == 'ok':
        m['mam'] = com.SPOIL[add]
        tail = f'Nếm lại: {com.TASTE[m["mam"]]} Lỡ tay rồi, chỉnh lại cho vừa.'
    elif com.FIX[add] == before:
        m['mam'] = 'ok'
        tail = f'Nếm lại: {com.TASTE["ok"]}'
    else:
        tail = f'Nếm lại: vẫn {com.TASTE[before]}'
    return dict(message=f'🫙 {com.ADD_LABEL[add]}, khuấy đều. {tail}')


def _wash(s, c, d, p):
    t = _task(c, p, ('cook',))
    _need_meal_served(c, t)
    _ensure_extra(c, t)
    k, st = _dish(t, p)
    kit.need(not st['wash'], 'Rửa sạch rồi.')
    st['wash'] = True
    kit.start_work(t)
    return dict(message=f'🚿 Rửa sạch đồ làm {_lower(DISHES[k]["name"])}' + (', để ráo.' if DISHES[k]['ings'] else ', ngâm nước muối loãng.'))


def _cut(s, c, d, p):
    t = _task(c, p, ('cook',))
    _need_meal_served(c, t)
    _ensure_extra(c, t)
    k, st = _dish(t, p)
    how = kit.one_of(p.get('cut'), CUTS, 'Cắt thế nào?')
    kit.need(st['start'] is None, 'Món đang trên bếp rồi.')
    st['cut'] = how
    if DISHES[k]['method'] == 'song':
        st['done'] = round(kit.now(), 3)
        st['q'] = 'ok'
    kit.start_work(t)
    return dict(message=f'🔪 {CUTS[how]}: {_lower(DISHES[k]["name"])}' + (', bày ra đĩa.' if DISHES[k]['method'] == 'song' else '.'))


def _nem(s, c, d, p):
    t = _task(c, p, ('cook',))
    _need_meal_served(c, t)
    _ensure_extra(c, t)
    k, st = _dish(t, p)
    how = kit.one_of(p.get('nem'), NEMS, 'Nêm thế nào?')
    kit.need(DISHES[k]['method'] != 'song', 'Món ăn sống, chấm nước mắm là được.')
    kit.need(st['done'] is None, 'Món đã tắt bếp rồi.')
    st['nem'] = how
    return dict(message=f'🧂 {NEMS[how]} {_lower(DISHES[k]["name"])}.')


def _fire(s, c, d, p):
    t = _task(c, p, ('cook',))
    _need_meal_served(c, t)
    _ensure_extra(c, t)
    k, st = _dish(t, p)
    D = DISHES[k]
    heat = kit.one_of(p.get('heat'), HEATS, 'Lửa nhỏ, vừa hay lớn?')
    kit.need(D['method'] != 'song', 'Món này ăn sống, không cần bắc bếp.')
    kit.need(st['cut'], 'Sơ chế, cắt xong đã rồi hẵng bắc lên bếp.')
    kit.need(st['start'] is None, 'Món này nấu rồi.')
    kit.need(_cooking(c) < BURNERS, f'Cả {BURNERS} bếp đều đang bận. Tắt một bếp đã nhé.')
    st['start'] = round(kit.now(), 3)
    st['heat'] = heat
    kit.start_work(t)
    lo, hi = METHODS[D['method']]['ok']
    return dict(message=f'🔥 Bắc {_lower(D["name"])} lên bếp, {_lower(HEATS[heat])}. Canh chừng {lo}–{hi} giây rồi tắt bếp.')


def _off(s, c, d, p):
    t = _task(c, p, ('cook',))
    k, st = _dish(t, p)
    kit.need(st['start'] is not None and st['done'] is None, 'Món này chưa bắc lên bếp.')
    at = max(st['start'], kit.tap_now(p))
    secs = at - st['start']
    q = judge(DISHES[k]['method'], secs)
    st.update(done=round(at, 3), q=q)
    return dict(message=f'✋ Tắt bếp {_lower(DISHES[k]["name"])} sau {secs:.0f} giây: {DONE_NOTE[q]}.', celebrate=q == 'ok')


def _reheat(s, c, d, p):
    t = _task(c, p, ('cook',))
    k, st = _dish(t, p)
    kit.need(DISHES[k]['method'] != 'song', 'Món ăn sống, không cần hâm.')
    kit.need(st['done'] is not None, 'Món này chưa nấu xong.')
    kit.need(kit.now() - st['done'] > WARM_S * 2 / 3, 'Món còn nóng mà.')
    kit.need(_cooking(c) < BURNERS, f'Cả {BURNERS} bếp đều đang bận.')
    st['done'] = round(kit.now(), 3)
    st['warm'] = min(9, st['warm'] + 1)
    return dict(message=f'♨️ Hâm nóng lại {_lower(DISHES[k]["name"])}.')


def _dish_slips(t: dict, d: dict, now: float) -> None:
    """What the family notices in the food: one slip of each kind, named after the first dish it happens to."""
    n = t['needs']
    for k, st in t['dishes'].items():
        D = DISHES[k]
        name = D['name']
        raw = any(INGS[i]['kind'] in ('fish', 'meat', 'egg') for i in D['ings']) or k in ('chao',)
        if not st['wash']:
            _slip(t, 'dirty', 2, f'{name} còn sạn, chưa rửa kỹ.', 'chưa rửa sạch')
        if D['method'] != 'song':
            q = st['q']
            if q == 'song':
                if raw:
                    d['stats']['raw'] += 1
                    _slip(t, 'raw', 3, f'{name} chưa chín, ăn vô đau bụng!', 'đồ ăn chưa chín', safety=True)
                else:
                    _slip(t, 'soft', 1, f'{name} còn sống sượng.', 'chưa chín tới')
            elif q == 'qua':
                _slip(t, 'over', 1, f'{name} hơi quá lửa, nhừ mất ngon.', 'quá lửa')
            elif q == 'chay':
                _slip(t, 'burnt', 2, f'{name} cháy khét cả nồi.', 'nấu cháy')
            if st['heat'] != D['heat']:
                _slip(t, 'heat', 1, f'{name} để {_lower(HEATS[st["heat"]])} nên ăn không ngon.', 'sai lửa')
            want = want_nem(n, k)
            if st['nem'] is None:
                _slip(t, 'nonem', 1, f'{name} nhạt thếch, quên nêm.', 'quên nêm')
            elif st['nem'] != want:
                hurt = want == 'nhat' and n['con'] in SALTY_HURTS
                _slip(t, 'salt', 2 if hurt else 1,
                        f'{name} mặn quá, ông đang kiêng muối.' if hurt else f'{name} {"nhạt" if st["nem"] == "nhat" else "mặn"} quá so với khẩu vị nhà.',
                        'nêm sai khẩu vị')
            if now - st['done'] > WARM_S:
                d['today']['cold'] += 1
                d['stats']['cold'] += 1
                _slip(t, 'cold', 1, f'{name} nguội ngắt rồi.', 'đồ ăn nguội')
        cut = want_cut(n, k)
        if cut == 'nho' and st['cut'] != 'nho':
            _slip(t, 'cut', 1, f'{name} cắt to quá, {"bé" if n["con"] == "kid" else "ông"} nhai không nổi.', 'cắt chưa nhỏ')


def _serve(s, c, d, p):
    t = _task(c, p, ('cook',), ('meal',))
    r = t['rice']
    kit.need(r is not None, 'Chưa nấu cơm.')
    left = r['at'] - kit.now()
    kit.need(left <= 0, f'Cơm chưa chín, chờ chừng {max(1, round(left))} giây nữa.')
    raw = [DISHES[k]['name'] for k, st in t['dishes'].items() if st['done'] is None]
    kit.need(not raw, f'Còn món chưa xong: {", ".join(_lower(x) for x in raw)}.')
    tb = t['table']
    kit.need(tb['bowls'] > 0, 'Bày chén đũa đã nhé.')
    n = t['needs']
    now = kit.now()
    # The market comes to the table: a stale catch, too little for everyone.
    for ing, row in t['cart'].items():
        if row.get('q') == 'uon':
            kind = INGS[ing]['kind']
            _slip(t, 'stale', 2, f'{INGS[ing]["name"]} không tươi, ngửi là biết.', 'mua đồ không tươi', safety=kind in ('fish', 'meat'))
    need = needs_of(t['menu'], n['n'])
    if any(t['cart'][i]['n'] < q for i, q in need.items()):
        _slip(t, 'short', 2, 'Đồ ăn ít quá, cả nhà gắp hai lượt là hết.', 'mua thiếu phần')
    _dish_slips(t, d, now)
    want = CONS[n['con']]['water']
    if r['w'] != want:
        soft = {'lung': 'cứng', 'mot': 'hơi cứng', 'ruoi': 'nhão'}[r['w']]
        _slip(t, 'rice', 2 if n['con'] == 'elder' else 1, f'Cơm {soft}, ông nhai không nổi.' if n['con'] == 'elder' else f'Cơm {soft} quá.', 'nấu cơm sai nước')
    if tb['bowls'] != n['n']:
        _slip(t, 'bowls', 1, 'Thiếu chén đũa, có người phải ngồi chờ.' if tb['bowls'] < n['n'] else 'Bày dư chén đũa, nhà có bấy nhiêu người.', 'bày sai số chén')
    if not tb['tasted'] or tb['mam'] != 'ok':
        _slip(t, 'mam', 1, 'Chén nước mắm chấm chưa vừa.', 'chưa nếm nước mắm')
    t['stage'] = 'settle'
    t['served_at'] = round(now, 3)
    good = not cq.slips(t)
    who = _who(t)
    line = 'Cả nhà quây quần, gắp lia lịa.' if good else 'Cả nhà ngồi vào mâm, có người nhíu mày.'
    return dict(message=f'🍚 Dọn mâm cơm {n["n"]} người. {line} Giờ ghi sổ chợ, gửi lại tiền thừa cho {_lower(who)} nhé.', celebrate=good)


# ---------------------------------------------------------------- the market book and the pay
def _file(s, c, d, p):
    t = _task(c, p, ('settle',), ('meal',))
    st = _stall(t, p)
    bill = t['bills'][st]
    kit.need(bill['paid'] > 0, 'Sạp này không mua gì.')
    kit.need(st not in t['filed'], 'Đã ghi vào sổ rồi.')
    t['filed'].append(st)
    if bill['receipt']:
        d['stats']['receipts'] += 1
        return dict(message=f'📒 Kẹp hóa đơn {STALLS[st]["short"]} vào sổ chợ: {bill["paid"]} xu.')
    _slip(t, 'receipt', 1, f'Tiền {STALLS[st]["short"]} không có hóa đơn, ghi tay theo trí nhớ.', 'thiếu hóa đơn')
    return dict(message=f'✍️ Không có hóa đơn {STALLS[st]["short"]}: ghi tay {bill["paid"]} xu theo trí nhớ.')


def wage(t: dict, visits: int) -> int:
    return WAGE_BASE + WAGE_PER * int(t['needs']['n']) + min(LOYAL_MAX, LOYAL_STEP * max(0, int(visits)))


def _react(c: dict, t: dict, price: int) -> tuple[int, str]:
    """How the family takes the job (decided once from the slips) and what it pays."""
    old = t.get('reaction')
    if isinstance(old, dict):
        return max(0, price - old['cut']), ''
    kind = cq.decide(c, t) if cq.slips(t) else 'accept'
    if kind == 'remake':
        kind = 'discount'
    cut = price * CUT[kind] // 100
    rows = REACT.get('refund' if kind in ('walkout', 'refuse') else kind) or REACT['grumble']
    line = rows[kit.rng(ID, 'react', t['id']).randrange(len(rows))]
    t['reaction'] = dict(kind=kind, cut=cut, line=line, day=c['day'])
    said = f'{_who(t)}: {line}' + (f' (−{cut} xu)' if cut else '')
    return price - cut, said


def _done(s, c, d, p):
    t = _task(c, p, ('settle',), ('meal',))
    left = [STALLS[st]['short'] for st, b in t['bills'].items() if b['paid'] > 0 and st not in t['filed']]
    kit.need(not left, f'Ghi sổ chợ đã: {", ".join(left)}.')
    n = t['needs']
    back = t['purse']
    spent = n['budget'] - back
    fam = d['families'].setdefault(n['fam'], dict(visits=0))
    pay, said = _react(c, t, wage(t, fam['visits']))
    fam['visits'] = min(999, fam['visits'] + 1)
    today, stats = d['today'], d['stats']
    today.update(meals=today['meals'] + 1, spent=today['spent'] + spent, budget=today['budget'] + n['budget'], back=today['back'] + back)
    stats['meals'] += 1
    if not cq.slips(t):
        stats['clean'] += 1
    lines = REG_STORY.get(_npc_index(t), ())
    story = lines[min(fam['visits'], len(lines)) - 1] if lines else ''
    t['story'] = story or None
    t['stage'] = 'done'
    head = f'💵 Gửi lại {back} xu tiền thừa cùng sổ chợ ({spent} xu tiền chợ).'
    kit.complete(s, c, t, pay, f'{head} {said}'.strip()[:300])
    # The pay first: a toast shows its first note only (chat 03/10 "không có tiền hả").
    msg = f'💰 Công bữa nay {pay} xu. {head} {said}'.strip()
    return dict(message=f'{msg} 💬 {story}' if story else msg, celebrate=not cq.slips(t))


def _bring(s, c, d, p):
    t = _task(c, p, ('cook',), ('extra',))
    _ensure_extra(c, t)
    k, st = next(iter(t['dishes'].items()))
    kit.need(st['done'] is not None, f'{DISHES[k]["name"]} chưa xong.')
    _dish_slips(t, d, kit.now())
    pay, said = _react(c, t, EXTRA_PAY)
    t['stage'] = 'done'
    d['today']['extras'] += 1
    d['stats']['extras'] += 1
    head = f'🍽️ Mang {_lower(DISHES[k]["name"])} ra cho {_lower(_who(t))}.'
    kit.complete(s, c, t, pay, f'{head} {said}'.strip()[:300])
    return dict(message=f'💰 Nhận {pay} xu. {head} {said}'.strip(), celebrate=not cq.slips(t))


ACTIONS = {
    'nc_pick': _pick, 'nc_plan': _plan,
    'nc_look': _look, 'nc_swap': _swap, 'nc_buy': _buy, 'nc_return': _return, 'nc_haggle': _haggle, 'nc_receipt': _receipt, 'nc_home': _home,
    'nc_rice': _rice, 'nc_bowls': _bowls, 'nc_taste': _taste, 'nc_fix': _fix,
    'nc_wash': _wash, 'nc_cut': _cut, 'nc_nem': _nem, 'nc_fire': _fire, 'nc_off': _off, 'nc_reheat': _reheat,
    'nc_serve': _serve, 'nc_file': _file, 'nc_done': _done, 'nc_bring': _bring,
}
NO_TICK = tuple(sorted({'nc_intro', 'nc_desk', *ACTIONS} - set(TICKING)))


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['today'] = _fresh_today(day)
    # Yesterday's family has eaten: what was left undone there is not carried to another house.
    for t in c['tasks']:
        if t.get('career') == ID and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    meal = next((t for t in c['tasks'] if t.get('career') == ID and t['day'] == day and t.get('kind') == 'meal'), None)
    if meal is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        meal = make_task(day, 0, c['turn'])
        c['tasks'].append(meal)
    if meal and meal['status'] not in ('completed', 'referred', 'cancelled'):
        c['active_task'] = meal['id']
        meal['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    today = d['today']
    fam = family_of(c['day'])
    lines = []
    earned = max(0, int(c.get('earnings') or 0))
    if today['meals']:
        lines.append(f'🍲 Nấu bữa cơm cho {_lower(fam["name"])}' + (f', thêm {today["extras"]} món' if today['extras'] else '') + '.')
        if earned:
            lines.append(kit.earned_line(s, earned))
        lines.append(f'📒 Tiền chợ {today["budget"]} xu: tiêu {today["spent"]} xu, gửi lại {today["back"]} xu.')
    else:
        lines.append(f'🍲 Bữa cơm {_lower(fam["name"])} hôm nay chưa xong.')
        if earned:
            lines.append(kit.earned_line(s, earned))
    if today['cold']:
        lines.append(f'♨️ Có {today["cold"]} món nguội trên mâm: món lâu chín bắc trước, món nhanh để sau.')
    if desk_note:
        lines.append(desk_note)
    for t in c['tasks']:
        # Dishes on a stove still burning at closing: the gas is turned off, the pot comes off.
        if t.get('career') == ID:
            for st in (t.get('dishes') or {}).values():
                if st.get('start') is not None and st.get('done') is None:
                    st.update(done=round(kit.now(), 3), q='chay')
    tm, tf = mod_of(c['day'] + 1), family_of(c['day'] + 1)
    return dict(lines=lines, earned=earned, meals=today['meals'], extras=today['extras'], spent=today['spent'], budget=today['budget'], back=today['back'],
                cold=today['cold'], family=dict(name=fam['name'], emoji=fam['emoji']),
                tomorrow=dict(emoji=tm['emoji'], label=tm['label'], hint=tm['hint'], family=tf['name'], fam_emoji=tf['emoji']))


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    codes = {x['code'] for x in cq.slips(t)}
    taste = 1 if 'raw' in codes else 2 if codes & {'burnt', 'dirty'} else 3 if codes & {'soft', 'over', 'heat', 'nonem', 'salt', 'mam', 'rice'} else 5
    care = 2 if codes & {'clash', 'salt'} else 4 if codes & {'cut', 'taste'} else 5
    if t.get('kind') == 'extra':
        return dict(criteria=[dict(key='taste', label='Chín tới, vừa miệng', score=taste, note='ngon, vừa miệng' if taste == 5 else 'chưa vừa miệng'),
                              dict(key='care', label='Nhớ lời dặn', score=care, note='nhớ người trong nhà' if care == 5 else 'quên lời dặn')])
    menu = 2 if 'clash' in codes else 4 if 'taste' in codes else 5
    fresh = 2 if 'stale' in codes else 3 if 'short' in codes else 5
    warm = 3 if 'cold' in codes else 4 if 'bowls' in codes else 5
    money = 4 if 'receipt' in codes else 5
    return dict(criteria=[dict(key='menu', label='Thực đơn hợp nhà', score=menu, note='hợp cả nhà' if menu == 5 else 'chưa hợp người trong nhà'),
                          dict(key='fresh', label='Đồ tươi, đủ ăn', score=fresh, note='tươi ngon, đủ phần' if fresh == 5 else 'chợ chưa khéo'),
                          dict(key='taste', label='Chín tới, vừa miệng', score=min(taste, care + 1), note='ngon, vừa miệng' if taste == 5 else 'chưa vừa miệng'),
                          dict(key='warm', label='Lên mâm nóng hổi', score=warm, note='món nào cũng nóng' if warm == 5 else 'có món nguội'),
                          dict(key='money', label='Sổ chợ rõ ràng', score=money, note='rõ từng xu' if money == 5 else 'thiếu hóa đơn')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    fam = FAM[n['fam']]
    con = CONS[n['con']]
    if t['kind'] == 'extra':
        return f'{_who(t)} nhờ: {t["opening"]} {n["note"]}'
    return (f'{fam["name"]}: {n["n"]} người ăn, tiền chợ {n["budget"]} xu. {con["emoji"]} {con["rule"]} '
            f'{TASTES[n["taste"]]["label"]}. {n["note"]}')


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
    # Only what the player has looked at (or bought) shows how fresh it is; the bowl of nước mắm once tasted.
    for ing, row in (v.get('cart') or {}).items():
        if row.get('seen') or row.get('swap'):
            row['look'] = _lot(t, ing)
    if isinstance(v.get('table'), dict) and not v['table'].get('tasted'):
        v['table']['mam'] = None
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    fam = family_of(c['day'])
    return dict(intro=d['intro'], mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                family=dict(id=fam['id'], name=fam['name'], emoji=fam['emoji']), families={k: dict(v) for k, v in d['families'].items()},
                today=d['today'], stats=d['stats'], cooking=_cooking(c), desk=kit.desk_public(d['desk'], DESK, ID))


def content() -> dict:
    return dict(groups=GROUPS, group_order=list(GROUP_ORDER), stalls=STALLS, ings=INGS, dishes=DISHES, tags=TAGS, methods=METHODS,
                done_note=DONE_NOTE, cuts=CUTS, nems=NEMS, heats=HEATS, water=WATER, fix=com.ADD_LABEL, fix_for=com.FIX, taste=com.TASTE,
                cons=CONS, tastes=TASTES, rain_up=RAIN_UP, rice_s=RICE_S, warm_s=WARM_S, burners=BURNERS, buy_max=BUY_MAX,
                bowls_max=BOWLS_MAX, look=LOOK, extra_cut=EXTRA_DISH_CUT, extra_nem={f'{a}|{b}': v for (a, b), v in EXTRA_NEM.items()},
                wage=dict(base=WAGE_BASE, per=WAGE_PER, step=LOYAL_STEP, max=LOYAL_MAX, extra=EXTRA_PAY), intro=INTRO,
                families=[dict(id=f['id'], name=f['name'], emoji=f['emoji']) for f in FAMILIES],
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'extra':
        return 'Rửa → cắt → bắc bếp đúng lửa, nêm theo nhà → tắt bếp khi chín tới → mang ra.'
    return ('Nghe dặn → chọn một canh, một mặn, một xào, một rau hợp cả nhà → đi chợ: xem kỹ, mua đủ phần, xin hóa đơn → '
            'nấu cơm, bày chén, nếm nước mắm → món lâu bắc trước → dọn cơm → ghi sổ, gửi tiền thừa.')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'prep':
        return 'Đã nhặt rau, gọt củ, rửa rổ rá sẵn sàng.'
    if e.get('role') == 'wash':
        return 'Đã rửa chén bát, lau bếp sạch sẽ.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu nấu cơm nhà sai.')


def _vnum(x, lo, hi) -> None:
    kit.need(type(x) in (int, float) and lo <= x <= hi, 'Dữ liệu nấu cơm nhà sai.')


def _vdish(k: str, st) -> None:
    kit.need(k in DISHES and isinstance(st, dict) and set(st) == {'wash', 'cut', 'nem', 'heat', 'start', 'done', 'q', 'warm'}, 'Món trong bếp sai.')
    _vbool(st['wash'])
    kit.need(st['cut'] in (None, *CUTS) and st['nem'] in (None, *NEMS) and st['heat'] in (None, *HEATS) and st['q'] in (None, *DONE_Q), 'Món trong bếp sai.')
    for x in ('start', 'done'):
        if st[x] is not None:
            _vnum(st[x], 0, 10 ** 11)
    kit.integer(st['warm'], 0, 9)


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc nấu cơm nhà không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc nấu cơm nhà sai.')
    n = t['needs']
    menu = t.get('menu')
    kit.need(isinstance(menu, dict) and set(menu) <= set(GROUPS) and all(menu[g] in MENU_DISHES and DISHES[menu[g]]['group'] == g for g in menu),
             'Thực đơn sai.')
    cart = t.get('cart')
    kit.need(isinstance(cart, dict) and set(cart) <= set(INGS), 'Giỏ chợ sai.')
    if t['stage'] != 'plan' and t['kind'] == 'meal':
        kit.need(set(menu) == set(GROUPS) and set(cart) == set(needs_of(menu, n['n'])), 'Giỏ chợ không khớp thực đơn.')
    for ing, row in cart.items():
        kit.need(isinstance(row, dict) and set(row) in ({'seen', 'swap', 'n', 'paid'}, {'seen', 'swap', 'n', 'paid', 'q'}), 'Giỏ chợ sai.')
        _vbool(row['seen'])
        _vbool(row['swap'])
        kit.integer(row['n'], 0, BUY_MAX)
        kit.need(row['paid'] == unit_price(ing, n['mod']) * row['n'], 'Tiền chợ sai.')
        kit.need(('q' in row) == (row['n'] > 0), 'Giỏ chợ sai.')
        kit.need(row.get('q') in (None, 'tuoi', t['_key']['lots'][ing]), 'Giỏ chợ sai.')
    bills = t.get('bills')
    kit.need(isinstance(bills, dict) and set(bills) <= set(STALLS), 'Hóa đơn sai.')
    for st, b in bills.items():
        kit.need(isinstance(b, dict) and set(b) == {'paid', 'off', 'haggle', 'receipt'} and b['haggle'] in (None, 'ok', 'no'), 'Hóa đơn sai.')
        kit.integer(b['off'], 0, 2)
        kit.need(b['off'] == 0 or b['haggle'] == 'ok', 'Hóa đơn sai.')
        _vbool(b['receipt'])
        kit.need(b['paid'] == sum(r['paid'] for i, r in cart.items() if INGS[i]['stall'] == st) - b['off'], 'Hóa đơn sai.')
    shopping = t['kind'] == 'meal' and t['stage'] != 'plan'
    kit.need(type(t.get('purse')) is int and t['purse'] == (n['budget'] - sum(b['paid'] for b in bills.values()) if shopping else 0),
             'Ví tiền chợ sai.')
    r = t.get('rice')
    if r is not None:
        kit.need(isinstance(r, dict) and set(r) == {'w', 'at'} and r['w'] in WATER, 'Nồi cơm sai.')
        _vnum(r['at'], 0, 10 ** 11)
    dishes = t.get('dishes')
    kit.need(isinstance(dishes, dict) and len(dishes) <= 4, 'Món trong bếp sai.')
    if t['kind'] == 'meal':
        kit.need(not dishes or set(dishes) == set(menu.values()), 'Món trong bếp không khớp thực đơn.')
    else:
        kit.need(set(dishes) <= {n['x']}, 'Món trong bếp sai.')
    for k, st in dishes.items():
        _vdish(k, st)
    tb = t.get('table')
    if tb is not None:
        kit.need(isinstance(tb, dict) and set(tb) == {'bowls', 'mam', 'tasted'} and tb['mam'] in com.MAM_Q, 'Mâm cơm sai.')
        kit.integer(tb['bowls'], 0, BOWLS_MAX)
        _vbool(tb['tasted'])
    filed = t.get('filed')
    kit.need(isinstance(filed, list) and len(set(filed)) == len(filed) and set(filed) <= set(bills), 'Sổ chợ sai.')
    if 'served_at' in t:
        _vnum(t['served_at'], 0, 10 ** 11)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện nhà khách sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    kit.need(isinstance(d['families'], dict) and set(d['families']) <= set(FAM), 'Sổ nhà quen sai.')
    for v in d['families'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ nhà quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu nấu cơm nhà sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='nc_', category='food',
    meta=dict(short='Nấu cơm gia đình', place='Bếp nhà khách quen', tagline='Đi chợ vừa túi tiền, cơm nhà nóng hổi.', icon='com',
              color='#5e8c46', light='#eef6e4', weather='Sáng mát, chợ phường đông vui', work='Bữa cơm nhà', station='Bếp nhà khách',
              greeting='Nghe chủ nhà dặn, lên thực đơn hợp cả nhà, đi chợ vừa túi tiền rồi nấu cho kịp bữa. Món lâu chín bắc trước nhé.',
              caption='Bữa cơm nhà người ta, nấu như cho nhà mình', map_label='27 · BẾP NHÀ KHÁCH QUEN'),
    people=PEOPLE,
    staff=[('Xuân', 'prep', 'Nhặt rau, gọt củ nhanh thoăn thoắt.', 78, 86),
           ('Thắm', 'wash', 'Rửa chén lau bếp sạch bong, gọn gàng.', 82, 80),
           ('Hậu', 'prep', 'Từng phụ bếp đám cỗ, thái hành đều tăm tắp.', 72, 90),
           ('Nga', 'wash', 'Khỏe, chịu khó, nhà nào qua tay cũng sạch.', 86, 76)],
    roles={'prep': 'Phụ sơ chế', 'wash': 'Rửa chén, lau bếp'},
    tip=1,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🧺', 'Giỏ đi chợ', [('Canh', 'Một nồi'), ('Món mặn', 'Một đĩa'), ('Món xào', 'Một đĩa'), ('Rau', 'Một đĩa')],
              ['Lên thực đơn hợp nhà', 'Đi chợ vừa tiền', 'Món lâu bắc trước', 'Ghi sổ chợ rõ ràng']),
    stories=[('Cuốn sổ chợ', ('Cô Hạnh tặng bạn cuốn sổ chợ bìa xanh ngày đầu đi làm.',
                              'Cô dặn: “Sạp nào cũng xin hóa đơn, tiền thừa để riêng một túi.”',
                              'Cuối tháng, nhà nào cũng cộng sổ khớp từng xu.')),
             ('Chén canh nhạt của ông', ('Ông Toàn huyết áp cao, ăn gì cũng phải nhạt.',
                                          'Bạn múc riêng chén canh cho ông trước khi nêm cho cả nhà.',
                                          'Bà Toàn nói: “Con nấu mà ông ăn được, bà mừng.”')),
             ('Bức tranh của bé Bin', ('Bé Bin vẽ cả nhà ngồi quanh mâm cơm.',
                                       'Trong tranh có thêm một người đeo tạp dề, tay bưng nồi canh chua.',
                                       'Chị Mai dán bức tranh lên cửa tủ lạnh.'))],
    review_asides=['Cơm nhà nóng hổi, vừa miệng cả nhà.', 'Đi chợ khéo, tiền chợ còn dư.', 'Nhớ từng người trong nhà ăn gì kiêng gì.',
                   'Sổ chợ rõ ràng từng xu.'],
    situations=SITUATIONS,
    more_line='Chủ nhà nhờ nấu thêm một món.',
    guide='Nghe chủ nhà dặn → chọn một canh, một mặn, một xào, một rau hợp cả nhà, trong tiền chợ → đi chợ: xem kỹ, mua đủ phần '
          '(mỗi phần hai người), xin hóa đơn → nấu cơm, bày chén, nếm nước mắm → rửa, cắt, nêm, bắc bếp đúng lửa, món lâu bắc trước → '
          'dọn cơm → ghi sổ chợ, gửi lại tiền thừa.',
)
