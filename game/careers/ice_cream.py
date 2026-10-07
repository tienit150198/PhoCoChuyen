"""Tiệm kem Góc Phượng: cô Hiền's ice-cream corner by the primary-school gate (plugin career).

Cô Hiền has kept the shop under the flame tree for thirty years and cooks the coconut ice cream
herself every night; the player minds the counter. What the job is:

* the morning (``setup`` task): read the freezer thermometer and set the knob back to 4 (−18 °C)
  when someone turned it overnight, look in the tubs for one that melted and froze again (ice
  crystals: never sold, thrown out), change the water in the scoop well, then open;
* the freezer lid: scooping opens it, and every move with the lid open warms the chest. Close it
  between scoops. Too warm and the ice cream goes soft (scoops come out heavy and melt fast); a
  warm afternoon leaves a tub frozen again for tomorrow morning;
* scooping by weight: every scoop is weighed on the counter scale. How hard you press, how cold
  the tub is and the flavour decide the grams; a good scoop is 60–70 g. Scrape a little off or add
  a little (three touches a scoop). A thin scoop draws a complaint (Ông Tám watches the spoon),
  a fat one is the shop's loss in cô Hiền's evening note;
* the order: a paper cup, a cone (two scoops at most), a fresh coconut shell, a take-away tub
  weighed by the 100 g (zero the empty box first), or a stick from the drawer; toppings; and an
  allergy said once at the counter (a peanut allergy is a safety mistake);
* the melt clock: from the first scoop the order melts in real seconds (faster on a hot day or
  from a warm freezer). The birthday tray for class 2A goes in a foam box with ice packs;
* cash with the shared till (game/careers/till.py): Bé Chíp pays with a pile of coins from his
  piggy bank;
* house batches (``kem_mk_*``): one batch a day from cô Hiền's recipe card (coconut, avocado, and
  taro once the "Chứng chỉ làm kem" craft certificate is held, or from day 5 in sandbox). Measure
  (the card says cans and spoons, the jug says ml and grams), cook to 76–88 °C without boiling,
  cool in an ice bath, churn for the right minutes, freeze into a tub that sells from tomorrow.
  Mistakes leave the tub soft, icy or grainy; a burnt pot is thrown away. A good house scoop
  earns +1 xu and customers notice it;
* the apprenticeship: for the first three customers cô Hiền stands beside the player and catches
  each mistake once before the cup leaves the counter (nothing recorded, no desk surprises).

Mistakes go through consequences (cq.slip / cq.react); money only through the engine's money().
Everything random is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from . import till
from .. import consequences as cq

ID = 'ice_cream'
GEN = 1

TUB_G = 1200              # grams in a tub of ice cream
BOX_TARE = 25             # the empty take-away box on the scale
PRESS = {'nhe': 48, 'vua': 64, 'day': 80}   # grams of a scoop at −18 °C, by how hard you press
PRESS_LABEL = {'nhe': 'Múc nhẹ tay', 'vua': 'Múc vừa tay', 'day': 'Múc đầy tay'}
GOOD_G = (60, 70)         # a good scoop
THIN = 55                 # under this the customer says the scoop is small
FAT = 76                  # over this the shop gives ice cream away
ADJ_G = 10                # one scrape / one top-up
ADJ_MAX = 3
KNOB_T = {1: -10, 2: -13, 3: -16, 4: -18, 5: -21, 6: -24}
KNOB_OK = 4
SOFT_AT = -12             # from here the ice cream is soft: heavier scoops, faster melt
MUSHY_AT = -9             # scooped this warm, it is mush in the cup
REFREEZE_AT = -8          # a peak this warm leaves a tub frozen again for tomorrow
WELL_MAX = 12             # scoops before the well water is cloudy
TUB_DAYS = 5              # an open tub is thrown out after this many days
CUP_MAX = 8
SCOOP_MAX = 12            # scoops in one cup (a take-away box)
MELT_BASE = 40            # seconds before an order starts to melt
MELT_UNIT = 10            # more per scoop or stick
MELT_TRAY = 50            # the tray is carried in a box
MELT_MOD = {'hot': 75, 'rain': 125}

FLAVOURS = [
    dict(id='dua', name='Kem dừa cô Hiền', short='dừa', emoji='🥥', soft=106, cost=16, life=4, start=2),
    dict(id='dau', name='Kem dâu', short='dâu', emoji='🍓', soft=100, cost=15, life=8, start=2),
    dict(id='socola', name='Kem sô-cô-la', short='sô-cô-la', emoji='🍫', soft=94, cost=15, life=8, start=2),
    dict(id='bo', name='Kem bơ Đà Lạt', short='bơ', emoji='🥑', soft=108, cost=20, life=5, start=1),
    dict(id='khoai_mon', name='Kem khoai môn', short='khoai môn', emoji='🟣', soft=102, cost=15, life=8, start=1),
    dict(id='vani', name='Kem vani', short='vani', emoji='🍦', soft=100, cost=14, life=10, start=2),
]
FLAVOUR = {x['id']: x for x in FLAVOURS}
# Vessels: name, emoji, most scoops (None = by weight / no scoop), the stock it takes, price key.
VESSELS = {
    'ly': dict(name='Ly giấy', emoji='🥤', max=3, item=None, price=None),
    'oc': dict(name='Ốc quế', emoji='🍦', max=2, item='oc', price='oc'),
    'dua_trai': dict(name='Trái dừa', emoji='🥥', max=3, item='trai_dua', price='dua_trai'),
    'hop': dict(name='Hộp mang về', emoji='📦', max=SCOOP_MAX, item=None, price=None),
    'que': dict(name='Kem que đậu xanh', emoji='🍡', max=0, item='que', price='que'),
}
TOPPINGS = {
    'dau_phong': dict(name='Đậu phộng rang', emoji='🥜'),
    'dua_soi': dict(name='Dừa sợi', emoji='🤍'),
    'sot_socola': dict(name='Sốt sô-cô-la', emoji='🟤'),
    'banh_que': dict(name='Bánh quế vụn', emoji='🧇'),
}
ALLERGENS = {'dau_phong': 'đậu phộng'}
PACKS = {'xop': 'Thùng xốp + túi đá gel', 'tui': 'Túi ni-lông', 'da_kho': 'Thả đá khô vào khay'}

ITEMS = [dict(id=x['id'], name=x['name'] + ' (hộp)', emoji=x['emoji'], group='kem', unit='hộp', cost=x['cost'], life=x['life'],
              start=x['start']) for x in FLAVOURS] + [
    dict(id='que', name='Kem que đậu xanh', emoji='🍡', group='que', unit='cây', cost=2, life=12, start=16),
    dict(id='oc', name='Bánh ốc quế', emoji='🍦', group='vo', unit='cái', cost=1, life=30, start=30),
    dict(id='trai_dua', name='Trái dừa xiêm', emoji='🥥', group='vo', unit='trái', cost=4, life=5, start=6),
]
PRICES = dict(vien=6, vien_bo=7, oc=2, dua_trai=10, que=5, top=2, hop=5)   # hop: xu per 100 g

# ---------------------------------------------------------------- kem nhà làm: a house batch
# One batch a day, in the morning or a quiet moment: measure from cô Hiền's notebook (the card says it in
# cans and spoons, the jug and the scale in ml and g), cook the custard to 76–88 °C without boiling it,
# cool it in an ice bath, churn it for the right time, then pour it into a tub that freezes overnight.
# A good tub sells a little higher ("kem nhà làm"); a slip gives a soft, icy or grainy tub; a scorched
# pot is poured away. The ready-made tubs from the stock room stay on sale as before.
HOME_PLUS = 1             # xu more per scoop from a good house tub
HOME_MAX = 3              # house tubs waiting in the freezer
COOK_OK = (76, 88)        # the custard thickens; under it the starch is raw (icy), over it it boils
BOIL_AT = 89              # boiling: the coconut milk splits (grainy)
BURNT_AT = 96             # the pot scorches: pour the batch away
COOL_OK = 10              # churn only once the mix is this cold
CHURN_MIN = (15, 20, 25, 30, 35, 40, 45)
FIRE = {'nho': 7, 'lon': 14}
QUALITY = ('ok', 'soft', 'icy', 'grainy', 'burnt')
DEFECT_RANK = {'burnt': 4, 'grainy': 3, 'icy': 2, 'soft': 1}
DEFECT_NOTE = {'soft': 'mềm, mau chảy', 'icy': 'nhiều dăm đá', 'grainy': 'lợn cợn, không mịn', 'burnt': 'khét đáy nồi'}
STEP_LABEL = {'steam': 'Hấp khoai', 'measure': 'Đong nguyên liệu', 'cook': 'Nấu hỗn hợp', 'cool': 'Làm nguội',
              'blend': 'Xay nhuyễn', 'churn': 'Chạy máy đánh kem', 'freeze': 'Đổ hộp, cho vào tủ'}


def _ing(iid, name, unit, opts, right, card, low, high):
    return dict(id=iid, name=name, unit=unit, opts=list(opts), right=right, card=card, low=low, high=high)


RECIPES = {
    'dua': dict(name='Kem dừa cô Hiền', emoji='🥥', cost=7, cert=False,
                steps=('measure', 'cook', 'cool', 'churn', 'freeze'), churn=(25, 30), steam=0, blend=0,
                note='Công thức cô Hiền chép trong cuốn sổ bìa xanh.',
                ings=[_ing('cot_dua', 'Nước cốt dừa', 'ml', (200, 400, 600), 400, '2 lon (lon 200 ml)', 'icy', 'soft'),
                      _ing('sua', 'Sữa tươi', 'ml', (100, 200, 300), 200, '1 ly đầy (200 ml)', 'icy', 'icy'),
                      _ing('duong', 'Đường', 'g', (60, 100, 160), 100, '5 muỗng canh (muỗng 20 g)', 'icy', 'soft'),
                      _ing('bot', 'Bột năng', 'g', (5, 10, 30), 10, '2 muỗng cà phê (muỗng 5 g)', 'icy', 'grainy'),
                      _ing('dua_soi', 'Dừa sợi', 'g', (0, 30, 90), 30, '1 nắm tay (30 g)', None, 'grainy')]),
    'bo': dict(name='Kem bơ Đà Lạt', emoji='🥑', cost=9, cert=False,
               steps=('measure', 'blend', 'churn', 'freeze'), churn=(20, 25), steam=0, blend=2,
               note='Bơ sáp chín mềm, không nấu: xay thật mịn rồi đánh kem.',
               ings=[_ing('bo_sap', 'Thịt bơ sáp', 'g', (150, 300, 450), 300, '2 trái bơ (trái 150 g thịt)', 'icy', 'grainy'),
                     _ing('sua_dac', 'Sữa đặc', 'ml', (50, 100, 200), 100, '1 lon nhỏ (100 ml)', 'icy', 'soft'),
                     _ing('whipping', 'Kem tươi whipping', 'ml', (100, 200, 400), 200, '1 hộp nhỏ (200 ml)', 'icy', 'grainy'),
                     _ing('duong', 'Đường', 'g', (0, 40, 100), 40, '2 muỗng canh (muỗng 20 g)', None, 'soft')]),
    'khoai_mon': dict(name='Kem khoai môn', emoji='🟣', cost=8, cert=True,
                      steps=('steam', 'measure', 'cook', 'cool', 'churn', 'freeze'), churn=(30, 35), steam=3, blend=0,
                      note='Công thức khó của cô Hiền: khoai hấp chín bở, nghiền mịn rồi mới nấu.',
                      ings=[_ing('khoai', 'Khoai môn hấp', 'g', (200, 400, 600), 400, '2 củ vừa (củ 200 g)', 'icy', 'grainy'),
                            _ing('sua', 'Sữa tươi', 'ml', (200, 400, 600), 400, '2 ly đầy (ly 200 ml)', 'grainy', 'icy'),
                            _ing('duong', 'Đường', 'g', (60, 100, 160), 100, '5 muỗng canh (muỗng 20 g)', 'icy', 'soft'),
                            _ing('cot_dua', 'Nước cốt dừa', 'ml', (0, 100, 300), 100, 'nửa lon (lon 200 ml)', None, 'soft')]),
}
CERT_ID = 'ice_cream_craft'    # certificate_content.GROUPS: holding it opens the khoai môn recipe
CERT_FREE_DAY = 5              # outside the story (no certificates there) the hard recipe opens on this day

# ---------------------------------------------------------------- học nghề: the first customers with cô Hiền
APPRENTICE = 3
LESSONS = [
    ('Bài 1 · Viên kem trên cân', 'Cô Hiền đứng cạnh: “Múc một viên, nhìn số trên cân. 60 tới 70 gam là đẹp. Thiếu thì múc thêm, dư thì gạt bớt.”'),
    ('Bài 2 · Nắp tủ và kem chảy', 'Cô Hiền dặn: “Múc xong đậy nắp liền tay. Kem bắt đầu chảy từ viên đầu tiên, làm gọn rồi đưa khách.”'),
    ('Bài 3 · Lời dặn và tiền thối', 'Cô Hiền nhắc: “Khách dặn gì thì nhớ, nhất là dị ứng. Đưa kem xong đếm tiền khách đưa, thối đủ từng xu.”'),
]
CATCH = {
    'thin': 'Khoan đã con, viên này còn nhẹ. Bấm múc thêm cho đủ 60 gam rồi hẵng đưa.',
    'missing': 'Khoan, chưa đúng món khách gọi. Coi lại phiếu, ly nào sai thì bỏ ra làm lại.',
    'extra': 'Có món khách đâu có gọi. Bỏ ly dư ra đã con.',
    'top': 'Topping chưa đúng lời khách dặn kìa con. Coi lại phiếu rồi rắc cho đúng.',
    'allergy': 'Dừng! Khách dặn dị ứng đậu phộng. Bỏ topping đó ra, rắc cái khác cho khách.',
    'lid_open': 'Đậy nắp tủ lại đã con, để mở là kem mềm hết.',
    'well': 'Nước ngâm muỗng đục rồi. Thay nước, bỏ ly đó múc lại cho sạch.',
    'refrozen': 'Viên này lạo xạo đá, hộp đó hỏng rồi. Bỏ ly, bỏ hộp đó, múc hộp khác.',
    'mushy': 'Kem nhão rồi, tủ ấm quá. Đậy nắp chờ tủ lạnh lại rồi múc ly mới nghe.',
    'short': 'Hộp còn thiếu cân, múc thêm cho đủ số gam khách lấy.',
    'cheat_tare': 'Chưa trừ bì hộp kìa. Bỏ hộp đó, đặt hộp rỗng lên cân trừ bì rồi múc lại.',
    'icy': 'Kem hộp này không mịn, đừng bán cho khách. Bỏ ly, lấy vị khác hoặc hộp khác.',
    'grainy': 'Kem hộp này lợn cợn, đừng bán cho khách. Bỏ ly, lấy vị khác hoặc hộp khác.',
    'pack_bag': 'Khay kem phải xếp thùng xốp với đá gel, túi ni-lông là chảy hết.',
    'dry_ice': 'Không được để đá khô cạnh ly kem, tụi nhỏ bỏng tay đó. Xếp thùng xốp với đá gel.',
}

PEOPLE = [
    ('Cô Hiền', 'Chủ tiệm kem', 'Bán kem ở góc cổng trường ba mươi năm, đêm nào cũng nấu kem dừa.', 'warm'),
    ('Bé Chíp', 'Học sinh lớp 2A', 'Đập ống heo mua kem, đếm từng đồng xu trên quầy.', 'genz'),
    ('Ông Tám', 'Hưu trí, khách ruột kem trái dừa', 'Chiều nào cũng ngồi ghế đẩu ăn kem, nhìn cái muỗng kỹ lắm.', 'picky'),
    ('Chị Mai Anh', 'Trưởng ban phụ huynh lớp 2A', 'Hay đặt kem cho cả lớp, dặn dò rất kỹ.', 'bossy'),
    ('Anh Khang', 'Shipper giao đồ ăn', 'Ghé mua vội giữa hai đơn, xe vẫn nổ máy ngoài lề đường.', 'quiet'),
    ('Tú', 'Sinh viên năm hai', 'Hay dẫn bạn gái Mít đi ăn kem, một ly hai muỗng.', 'genz'),
]
KID_NPC = 1

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Tan học là học sinh ùa ra, khách đều tay.', weight=3),
    dict(id='hot', emoji='🥵', label='Nắng gắt', hint='Kem chảy nhanh hơn: múc gọn, đậy nắp tủ liền tay.', min_day=2, weight=2),
    dict(id='rain', emoji='🌧️', label='Mưa chiều', hint='Ít khách hơn, kem lâu chảy; người ta mua hộp mang về.', min_day=2, weight=2),
    dict(id='weekend', emoji='🛍️', label='Cuối tuần', hint='Sinh viên rủ nhau đi ăn kem, gọi nhiều ly một lúc.', min_day=2, weight=2),
    dict(id='outage', emoji='🔌', label='Lịch cúp điện', hint='Phường báo cúp điện buổi trưa: giữ nắp tủ đóng kín.', min_day=3, weight=1),
]
MOD = {m['id']: m for m in MODS}


def _l(v, *f, top=()):
    return dict(v=v, f=list(f), top=list(top), g=None)


def _h(f, g):
    return dict(v='hop', f=[f], top=[], g=g)


# (npc, kind, title, opening, lines, note, min_day, mod, flags)
ORDERS = [
    (1, 'serve', 'Bé Chíp mua ốc quế', 'Cô ơi, con lấy một cây ốc quế kem dâu ạ!', [_l('oc', 'dau')],
     'Bé Chíp dốc ống heo ra quầy, toàn đồng xu lẻ.', 1, None, dict(coins=True)),
    (2, 'serve', 'Ông Tám ăn kem trái dừa', 'Cho ông một trái dừa, hai viên kem dừa, rắc dừa sợi nghe.', [_l('dua_trai', 'dua', 'dua', top=('dua_soi',))],
     'Ông Tám nhìn chằm chằm cái muỗng: viên nhỏ là ông biết liền.', 1, None, dict(check=True)),
    (4, 'serve', 'Anh Khang mua kem que', 'Hai cây kem que đậu xanh, nhanh giùm anh, nắng quá!', [_l('que'), _l('que')],
     'Anh Khang để xe nổ máy ngoài lề đường.', 1, None, {}),
    (5, 'serve', 'Tú với Mít chia ly kem', 'Một ly hai viên, sô-cô-la với bơ, thêm topping giòn giòn nha anh.',
     [_l('ly', 'socola', 'bo', top=('banh_que', 'dau_phong'))], 'Tú dặn nhỏ: “Mít dị ứng đậu phộng đó nha.”', 2, None, dict(allergy='dau_phong')),
    (3, 'serve', 'Chị Mai Anh mua cho con', 'Một ly khoai môn một viên, một ốc quế vani rưới sô-cô-la cho bé.',
     [_l('ly', 'khoai_mon'), _l('oc', 'vani', top=('sot_socola',))], 'Chị Mai Anh vừa đón bé ở cổng trường.', 2, None, {}),
    (2, 'hop', 'Ông Tám mua kem về cho bà', 'Nửa ký kem dừa mang về, bà nhà ông thích lắm. Cân cho đủ nghe.', [_h('dua', 500)],
     'Ông Tám đứng nhìn cái cân điện tử.', 2, None, dict(check=True)),
    (4, 'serve', 'Anh Khang mua kem bơ', 'Ly kem bơ hai viên, rắc dừa sợi. Chạy đơn nãy giờ khát khô.', [_l('ly', 'bo', 'bo', top=('dua_soi',))],
     'Anh Khang tranh thủ ngồi xuống bậc thềm.', 2, None, {}),
    (2, 'serve', 'Ông Tám ngồi kể chuyện', 'Một ly kem dừa, một viên thôi, ông ngồi đây ăn.', [_l('ly', 'dua')],
     'Ông Tám kéo ghế đẩu ra dưới gốc phượng.', 2, None, dict(check=True)),
    (1, 'serve', 'Bé Chíp tan học', 'Cô ơi, một cây kem que, con còn có mấy đồng à.', [_l('que')],
     'Bé Chíp đếm xu trên lòng bàn tay.', 2, None, dict(coins=True)),
    (1, 'serve', 'Bé Chíp mua cho em', 'Cô ơi hai cây ốc quế, một dâu một sô-cô-la, rắc gì ngon ngon cũng được ạ.',
     [_l('oc', 'dau', top=('dua_soi', 'sot_socola', 'banh_que')), _l('oc', 'socola', top=('dua_soi', 'sot_socola', 'banh_que'))],
     'Bé Chíp nói thêm: “Em con dị ứng đậu phộng, mẹ dặn kỹ lắm ạ.”', 3, None, dict(coins=True, allergy='dau_phong')),
    (4, 'hop', 'Anh Khang mua hộp sô-cô-la', 'Hộp kem sô-cô-la ba lạng, anh mang về cho con gái.', [_h('socola', 300)],
     'Anh Khang vừa xong ca, áo ướt mồ hôi.', 3, None, {}),
    (5, 'serve', 'Tú khao cả nhóm', 'Ba ly một viên: dâu, khoai môn, dừa. Ly dừa thêm đậu phộng nha!',
     [_l('ly', 'dau'), _l('ly', 'khoai_mon'), _l('ly', 'dua', top=('dau_phong',))], 'Cả nhóm vừa thi xong, cười nói ầm ĩ.', 2, 'weekend', {}),
    (5, 'serve', 'Tú trú nắng', 'Hai ly kem dâu một viên, nắng quá trời luôn!', [_l('ly', 'dau'), _l('ly', 'dau')],
     'Tú với Mít che chung một cái nón.', 2, 'hot', {}),
    (3, 'hop', 'Chị Mai Anh trú mưa', 'Mưa quá, chị lấy hộp kem vani ba lạng về nhà.', [_h('vani', 300)],
     'Chị Mai Anh rũ nước trên áo mưa.', 2, 'rain', {}),
    (2, 'serve', 'Ông Tám ngày cúp điện', 'Cúp điện mà ông vẫn ghé. Một trái dừa một viên dừa, kem còn cứng không con?',
     [_l('dua_trai', 'dua')], 'Ông Tám phe phẩy cái quạt nan.', 3, 'outage', dict(check=True)),
]
TRAY = (3, 'tray', 'Khay kem sinh nhật lớp 2A', 'Sáu ly một viên: hai dâu, hai sô-cô-la, hai vani. Chị mang lên lớp liền, tiệc sắp bắt đầu!',
        [_l('ly', 'dau'), _l('ly', 'dau'), _l('ly', 'socola'), _l('ly', 'socola'), _l('ly', 'vani'), _l('ly', 'vani')],
        'Hôm nay sinh nhật bé Bông lớp 2A. Lên tới lớp mất mười phút.', 3, None, {})
KINDS = ('setup', 'serve', 'hop', 'tray')
STAGES = ('prep', 'pay', 'done')

# Regulars' small stories: one line per finished visit, on and on across days.
REG_STORY = {
    1: ('Bé Chíp: “Con để dành cả tuần mới đủ tiền đó cô!”', 'Bé Chíp khoe được cô giáo cho cắm cờ đỏ vì đi học đúng giờ.',
        'Bé Chíp vẽ tặng tiệm cây kem ốc quế bằng bút sáp, dán lên tủ kem.', 'Bé Chíp tập đếm tiền thối cùng bạn, không sai đồng nào.'),
    2: ('Ông Tám: “Kem dừa phải để trong trái dừa mới ra vị.”', 'Ông Tám kể hồi trẻ ông chở kem bằng xe đạp, rao khắp xóm.',
        'Ông Tám gật gù: “Viên kem tròn đều, đủ gam. Được.”', 'Ông Tám mang tặng tiệm cái ghế đẩu ông tự đóng.'),
    3: ('Chị Mai Anh: “Lớp 2A mà ăn kem ở đây là ngoan cả buổi.”', 'Chị Mai Anh gửi lời khen của cô chủ nhiệm lớp 2A.',
        'Chị Mai Anh bảo cả nhóm phụ huynh giờ chỉ đặt kem ở tiệm mình.'),
    4: ('Anh Khang: “Cây kem que là bữa trưa của anh đó.”', 'Anh Khang được thưởng tài xế chăm chỉ của tháng.',
        'Anh Khang giới thiệu tiệm lên nhóm shipper của phường.'),
    5: ('Tú: “Ly hai muỗng là vừa đủ cho hai đứa.”', 'Tú kể Mít đã nhận lời làm người yêu sau ly kem bơ.',
        'Tú với Mít chụp ảnh dưới gốc phượng, tag tiệm luôn.'),
}

INTRO = dict(
    title='Giới thiệu nghề: bán kem',
    lead='Một tủ kem nắp kính, cái cân điện tử và mấy hũ topping dưới gốc phượng trước cổng trường tiểu học. '
         'Cô Hiền nấu kem dừa từ đêm, sáng ra bạn trông tiệm giúp cô.',
    work=[('🌡️', 'Xem nhiệt kế tủ kem, vặn nút về số 4 (−18 °C)'), ('🧊', 'Soi hộp kem: hộp đông đá lại thì bỏ, không bán'),
          ('💧', 'Thay nước ngâm muỗng mỗi sáng'), ('🍨', 'Múc kem lên cân: mỗi viên 60–70 gam'),
          ('🧊', 'Múc xong đậy nắp tủ liền tay, kẻo kem mềm nhão'), ('⏱️', 'Đưa kem trước khi chảy'),
          ('🥜', 'Nghe kỹ dị ứng: đậu phộng là không được rắc'), ('💵', 'Thu tiền, đếm xu lẻ, thối đúng')],
    meet=[('🎒', 'Bé Chíp: trả bằng xu ống heo'), ('🥥', 'Ông Tám: kem trái dừa, nhìn muỗng rất kỹ'),
          ('🎂', 'Chị Mai Anh: khay kem sinh nhật lớp 2A'), ('🛵', 'Anh Khang: mua vội kem que'),
          ('💑', 'Tú và Mít: một ly hai muỗng'), ('🔌', 'Nắng gắt, mưa chiều, cúp điện giữa trưa')],
    stars=[('🍨', 'Viên kem tròn, đủ gam'), ('🧊', 'Kem lạnh, không chảy, không sạn đá'), ('🥜', 'Đúng topping, nhớ dị ứng'),
           ('💧', 'Muỗng sạch, nước ngâm trong'), ('⏱️', 'Nhanh gọn'), ('💵', 'Thối đúng tiền')],
)

# ---------------------------------------------------------------- surprises (kit desk scripts)
DESK = [
    dict(id='power_cut', title='Cúp điện giữa trưa', emoji='🔌', npc=0, min_day=2, tone='tense', at='between', weight=4, mods=('outage',),
         text='Phụt một cái, quạt tắt, đèn tủ kem tắt. Cả dãy phố cúp điện, chưa biết bao giờ có lại.',
         options=[dict(id='shut', label='Đóng chặt nắp, phủ chăn bông lên tủ, bán kem que trước', hint='Khách chờ lâu hơn chút',
                       effects=dict(patience=-4, fz=2, xp=3), good=True,
                       outcome='Tủ kín hơi, chăn bông giữ lạnh. Hai tiếng sau có điện, kem vẫn còn cứng.'),
                  dict(id='sell', label='Bán rẻ kem dừa cho nhanh hết', hint='Được ít tiền, tủ ấm lên', effects=dict(money=6, fz=5), good=None,
                       outcome='Học sinh xúm lại mua kem rẻ. Hộp kem dừa vơi nhanh nhưng tủ cũng ấm dần.'),
                  dict(id='as_usual', label='Cứ mở tủ bán như thường', hint='', effects=dict(fz=9), good=False,
                       outcome='Nắp tủ mở ra đóng vào liên tục. Có điện lại thì kem đã nhão cả mặt hộp.')],
         default='as_usual'),
    dict(id='dropped_cone', title='Bé làm rớt cây kem', emoji='😭', npc=1, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Một bé lớp 1 vừa cầm cây ốc quế đã vấp chân, viên kem rớt xuống đất. Bé đứng khóc, tay còn cầm cái vỏ ốc quế.',
         options=[dict(id='new', label='Múc cho bé viên khác, dặn cầm hai tay', hint='Mất một viên kem', effects=dict(money=-1, xp=4), good=True,
                       outcome='Bé nín khóc ngay, cầm cây kem bằng hai tay đi từng bước. Mẹ bé cảm ơn mãi.'),
                  dict(id='half', label='Bán nửa giá viên mới', hint='', effects=dict(money=3), good=None,
                       outcome='Mẹ bé trả tiền, hơi tiếc nhưng cũng cảm ơn.'),
                  dict(id='nothing', label='“Rớt thì thôi con”', hint='', effects=dict(review=[3, 'Con nít làm rớt kem khóc ngất mà tiệm cũng kệ.']),
                       good=False, outcome='Bé khóc to hơn. Mấy phụ huynh đứng đó nhìn nhau.')],
         default='half'),
    dict(id='gate_guard', title='Bảo vệ trường nhắc chỗ đứng', emoji='🏫', npc=0, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='Chú bảo vệ trường ra nhắc: “Giờ tan học xe đón đông lắm, tiệm kê ghế đẩu lấn ra cổng là kẹt xe đó nha.”',
         options=[dict(id='move', label='Dọn ghế vào sát vỉa hè, chừa lối cho phụ huynh', hint='', effects=dict(xp=3), good=True,
                       outcome='Lối đi thông thoáng. Chú bảo vệ còn dặn học sinh xếp hàng mua kem cho trật tự.'),
                  dict(id='later', label='Dạ, lát con dọn', hint='', effects=dict(patience=-3), good=None,
                       outcome='Tan học xe đón chen nhau, mấy khách đứng chờ phải lùi ra lùi vào.'),
                  dict(id='argue', label='“Vỉa hè chung mà chú”', hint='', effects=dict(review=[2, 'Tiệm kem kê ghế chắn cổng trường, xe đón con không vào được.']),
                       good=False, outcome='Chú bảo vệ báo phường. Chiều đó có người tới nhắc nhở.')],
         default='later'),
    dict(id='dry_ice_man', title='Người mời mua đá khô', emoji='🌫️', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một người chở thùng đá khô ghé: “Đá khô giữ kem cả ngày, giá rẻ. Bỏ thẳng vào ly kem cho bốc khói, con nít thích lắm!”',
         options=[dict(id='no', label='Không lấy: đá khô làm bỏng lạnh, không cho vào đồ ăn', hint='', effects=dict(xp=4), good=True,
                       outcome='Người đó đi tiếp. Cô Hiền nghe kể: “Đá khô chỉ để trong thùng kín, có găng tay, không bao giờ vào ly.”'),
                  dict(id='box', label='Mua một ít để trong thùng giữ lạnh, dán chữ “không chạm”', hint='8 xu', effects=dict(money=-8, xp=2), good=None,
                       outcome='Thùng đá khô để dưới gầm tủ, có dán giấy cảnh báo. Ít khi dùng tới.'),
                  dict(id='smoke', label='Lấy, thả vào ly cho bốc khói câu khách', hint='Câu khách…',
                       effects=dict(money=-8, review=[1, 'Tiệm kem thả đá khô vào ly, bé nhà tôi chạm vào bị bỏng lạnh đỏ cả ngón tay!']),
                       good=False, outcome='Ly kem bốc khói thật, đến chiều có bé bị bỏng lạnh ở ngón tay.')],
         default='no'),
    dict(id='taster', title='Khách đòi nếm đủ sáu vị', emoji='🥄', npc=5, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một nhóm sinh viên xin nếm thử cả sáu vị kem, mỗi người một muỗng, rồi mới chọn.',
         options=[dict(id='spoon', label='Mời nếm bằng muỗng nhựa nhỏ, mỗi người hai vị', hint='', effects=dict(xp=3, money=4), good=True,
                       outcome='Cả nhóm nếm xong gọi bốn ly. Muỗng nếm bỏ riêng, không nhúng lại vào hộp.'),
                  dict(id='all', label='Cho nếm hết, muỗng nào cũng được', hint='', effects=dict(patience=-5), good=None,
                       outcome='Nếm hết sáu vị, khách sau chờ dài cổ. Nhóm đó mua đúng hai ly.'),
                  dict(id='same_spoon', label='Đưa một muỗng chung, nếm xong nhúng lại hộp', hint='',
                       effects=dict(review=[2, 'Muỗng nếm thử ngậm xong lại nhúng vào hộp kem, mất vệ sinh ghê.']), good=False,
                       outcome='Một chị đứng sau thấy cảnh đó, lắc đầu bỏ đi.')],
         default='all'),
    dict(id='wasp', title='Ong bu quanh hũ topping', emoji='🐝', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=('hot', 'normal', 'weekend'),
         text='Trời nắng, mấy con ong bay vo ve quanh hũ sốt sô-cô-la để mở nắp. Học sinh xếp hàng sợ rúm người.',
         options=[dict(id='cover', label='Đậy nắp mọi hũ topping, lau sạch vệt sốt', hint='', effects=dict(xp=3), good=True,
                       outcome='Không còn mùi ngọt, ong bay đi. Hàng học sinh trật tự lại.'),
                  dict(id='swat', label='Lấy quạt nan đập ong', hint='', luck=dict(p=0.5,
                       win=dict(effects={}, good=None, outcome='Ong bay đi, may không ai bị đốt.'),
                       lose=dict(effects=dict(review=[2, 'Tiệm đập ong ngay chỗ con nít đứng, bé nhà tôi bị đốt sưng tay.']), good=False,
                                 outcome='Con ong nổi giận, đốt một bé đứng gần quầy.')), effects={}),
                  dict(id='ignore', label='Kệ, ong không làm gì đâu', hint='', effects=dict(patience=-4), good=None,
                       outcome='Mấy bé sợ quá đứng xa, hàng chờ lộn xộn.')],
         default='cover'),
    dict(id='reviewer', title='Người quay clip đòi ăn miễn phí', emoji='📱', npc=5, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Một anh cầm gậy tự sướng: “Anh review quán, mấy chục nghìn người theo dõi. Cho anh ba ly free, anh lên clip khen.”',
         options=[dict(id='price', label='Mời mua đúng giá, tặng thêm muỗng nếm vị dừa', hint='', effects=dict(xp=3, money=6), good=True,
                       outcome='Anh ấy trả tiền, nếm kem dừa xong khen thật lòng trong clip.'),
                  dict(id='free', label='Cho ba ly free cho được việc', hint='Mất ba ly', effects=dict(money=-3), good=None,
                       outcome='Clip lên, nói vài câu rồi chuyển sang quán khác.'),
                  dict(id='shoo', label='“Muốn ăn free thì đi chỗ khác”', hint='', effects=dict(review=[2, 'Hỏi có một câu mà chủ tiệm kem cà khịa, né nha mọi người.']),
                       good=False, outcome='Anh ấy quay luôn cảnh bị đuổi, đăng lên mạng.')],
         default='price'),
    dict(id='rain_awning', title='Mưa tạt vào quầy', emoji='🌧️', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=('rain',),
         text='Mưa chiều hắt xéo, nước tạt vào hũ bánh quế và mặt quầy, gió lật cả tấm bạt.',
         options=[dict(id='awning', label='Kéo bạt xuống, đậy hũ, lau quầy', hint='Mất chút thời gian', effects=dict(patience=-3, xp=3), good=True,
                       outcome='Quầy khô ráo, bánh quế vẫn giòn. Khách trú mưa mua thêm hộp kem về.'),
                  dict(id='later', label='Để tạnh rồi lau', hint='', effects=dict(money=-2), good=None,
                       outcome='Hũ bánh quế ướt nhão phải bỏ.')],
         default='later'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='KM-S01', title='Viên kem bé xíu', npc=2, tone='tense', min_day=1,
         opening='Ông Tám đặt ly kem lên cân của tiệm: “Viên kem này có năm chục gam, hôm trước bảy chục. Tiệm bớt xén hả con?”',
         swap='Bạn là ông Tám, ăn kem ở đây hai mươi năm, nhìn cái muỗng là biết viên to hay nhỏ.',
         facts=[dict(id='scale', title='Cái cân', source='Quầy', text='Cân điện tử chỉ 51 gam: thiếu cả chục gam so với viên chuẩn.'),
                dict(id='hard', title='Tủ kem', source='Nhiệt kế', text='Sáng nay nút tủ bị vặn lên số 6, kem cứng như đá, muỗng múc không sâu.'),
                dict(id='rule', title='Lời cô Hiền', source='Cô Hiền', text='Cô dặn: viên nào cũng lên cân, thiếu thì múc thêm, đừng để khách phải nói.')],
         options=[dict(id='fix', label='Xin lỗi ông, múc thêm cho đủ, vặn tủ về số 4', requires=['scale', 'hard'], quality='good', stars=5,
                       review='Viên kem thiếu thật nhưng tiệm nhận ngay, múc bù đủ, còn chỉnh lại tủ. Thật thà.',
                       outcome='Ông Tám gật gù, ăn hết ly kem rồi kể chuyện xe kem ngày xưa.',
                       perspectives=[dict(who='Ông Tám', emoji='🥥', text='Thiếu mà nhận thì còn ăn được lâu.'),
                                     dict(who='Cô Hiền', emoji='👩‍🍳', text='Kem cứng thì múc sâu tay, cân lại là biết.')]),
                  dict(id='free', label='Tặng ông thêm một viên cho vui', requires=['scale'], quality='ok', stars=4,
                       review='Có bù, nhưng tủ vẫn lạnh cóng, mấy viên sau cũng bé.',
                       outcome='Ông Tám nhận viên kem, dặn: “Chỉnh cái tủ đi con.”',
                       perspectives=[dict(who='Ông Tám', emoji='🤨', text='Bù cho ông, còn mấy đứa nhỏ thì sao?'),
                                     dict(who='Bé Chíp', emoji='🎒', text='Cây ốc quế của con cũng bé xíu à.')]),
                  dict(id='deny', label='“Cân ông chắc lệch, viên đó chuẩn mà”', quality='bad', stars=1,
                       review='Viên kem thiếu rành rành còn cãi. Hai mươi năm ăn ở đây mà buồn.',
                       outcome='Ông Tám đặt ly kem xuống, chiều hôm sau không thấy ông ra ghế đẩu nữa.',
                       perspectives=[dict(who='Ông Tám', emoji='😞', text='Cân của tiệm chứ đâu phải cân của ông.'),
                                     dict(who='Cô Hiền', emoji='👩‍🍳', text='Mất một ông khách ruột vì mười gam kem.')])],
         lesson='Viên kem nào cũng lên cân; tủ quá lạnh thì kem cứng, viên bé. Thiếu thì nhận, múc bù, chỉnh tủ.'),
    dict(id='KM-S02', title='Hộp kem đông đá lại', npc=0, tone='tense', min_day=2,
         opening='Tối qua cúp điện hai tiếng. Sáng nay hộp kem dâu sờ vào cứng đá, mặt kem lổn nhổn tinh thể đá. Bỏ thì tiếc cả hộp.',
         facts=[dict(id='ice', title='Mặt hộp kem', source='Soi kỹ', text='Mặt kem có lớp đá vụn, múc lên nghe lạo xạo: kem đã chảy rồi đông lại.'),
                dict(id='risk', title='Vì sao không bán', source='Cô Hiền', text='Kem chảy rồi đông lại thì vi khuẩn có dịp sinh sôi, ăn dễ đau bụng.'),
                dict(id='kids', title='Ai ăn', source='Quầy', text='Khách chủ yếu là học sinh lớp 1, lớp 2.')],
         options=[dict(id='bin', label='Bỏ hộp kem, ghi sổ hao hụt, báo cô Hiền', requires=['ice', 'risk'], quality='good', stars=5,
                       review='Tiệm thấy kem không đạt là bỏ, không tiếc. Cho con ăn yên tâm.',
                       outcome='Mất một hộp kem, nhưng cô Hiền nhắn: “Làm đúng rồi con.”',
                       perspectives=[dict(who='Chị Mai Anh', emoji='🎂', text='Biết vậy càng yên tâm đặt kem cho lớp.'),
                                     dict(who='Cô Hiền', emoji='👩‍🍳', text='Một hộp kem không bằng cái bụng của tụi nhỏ.')]),
                  dict(id='cheap', label='Bán rẻ cho người lớn, nói rõ là kem đông lại', requires=['ice'], quality='ok', stars=3,
                       review='Có nói thật, nhưng kem lạo xạo ăn không ngon.',
                       outcome='Bán được vài ly rẻ, khách ăn xong chê sạn.',
                       perspectives=[dict(who='Anh Khang', emoji='🛵', text='Rẻ thì rẻ, nhưng ăn như ăn đá bào.'),
                                     dict(who='Cô Hiền', emoji='👩‍🍳', text='Nói thật là tốt, nhưng kem này đừng bán.')]),
                  dict(id='sell', label='Múc phần dưới đáy, bán bình thường', quality='bad', stars=1,
                       review='Kem lạo xạo đá, tối về con đau bụng. Không dám mua nữa.',
                       outcome='Tối đó có phụ huynh gọi điện phản ánh.',
                       perspectives=[dict(who='Bé Chíp', emoji='🎒', text='Kem hôm nay ăn lạo xạo kỳ kỳ…'),
                                     dict(who='Chị Mai Anh', emoji='🎂', text='Bán cho con nít mà vậy thì không được.')])],
         lesson='Kem chảy rồi đông lại có tinh thể đá: không bán, kể cả bán rẻ. Sáng nào cũng soi hộp kem.'),
    dict(id='KM-S03', title='Ly kem có đậu phộng', npc=5, tone='tense', min_day=2,
         opening='Tú quay lại quầy, mặt tái: “Anh ơi, ly của Mít có vụn gì giòn giòn… Mít bắt đầu ngứa cổ rồi!”',
         facts=[dict(id='jar', title='Hũ topping', source='Quầy', text='Hũ bánh quế vụn nằm sát hũ đậu phộng, muỗng xúc dùng chung.'),
                dict(id='allergy', title='Lời dặn', source='Tú', text='Lúc gọi kem Tú đã dặn Mít dị ứng đậu phộng.'),
                dict(id='call', title='Số khẩn cấp', source='Bảng ở quầy', text='Dị ứng nặng gọi 115; Mít đang tỉnh, nói được, môi hơi sưng.')],
         options=[dict(id='help', label='Hỏi Mít có thuốc dị ứng không, gọi 115, nhận lỗi, tách muỗng riêng từng hũ',
                       requires=['allergy', 'call'], quality='good', stars=4,
                       review='Tiệm có lỗi nhưng xử lý nhanh, gọi cấp cứu ngay, từ đó mỗi hũ topping một muỗng riêng.',
                       outcome='Mít uống thuốc mang theo, xe cấp cứu tới kiểm tra, may không sao.',
                       perspectives=[dict(who='Tú', emoji='💑', text='Sợ muốn xỉu, may tiệm bình tĩnh gọi cấp cứu.'),
                                     dict(who='Cô Hiền', emoji='👩‍🍳', text='Từ nay muỗng ai nấy giữ, hũ nào muỗng đó.')]),
                  dict(id='water', label='Đưa ly nước, bảo ngồi nghỉ chút là hết', requires=['jar'], quality='bad', stars=2,
                       review='Bạn em dị ứng mà tiệm bảo uống nước là hết. Hú hồn.',
                       outcome='Mười phút sau môi Mít sưng to, Tú phải tự chở đi trạm y tế.',
                       perspectives=[dict(who='Tú', emoji='😨', text='Dị ứng đâu phải chuyện đùa.'),
                                     dict(who='Bác sĩ', emoji='🩺', text='Phản ứng dị ứng phải xử lý sớm.')]),
                  dict(id='deny', label='“Tiệm có rắc đậu phộng đâu”', quality='bad', stars=1,
                       review='Muỗng xúc chung hũ đậu phộng mà còn chối. Tệ.',
                       outcome='Tú đăng bài kể chuyện, kèm ảnh hai hũ topping chung một muỗng.',
                       perspectives=[dict(who='Tú', emoji='😠', text='Dặn kỹ rồi mà còn chối.'),
                                     dict(who='Chị Mai Anh', emoji='🎂', text='Lớp 2A có hai bé dị ứng đậu phộng đó.')])],
         lesson='Khách dặn dị ứng thì nhớ cả muỗng xúc: hũ nào muỗng đó. Có phản ứng thì hỏi thuốc mang theo, gọi 115.'),
]


# ================================================================ small helpers
def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Khách'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _p(c: dict, key: str) -> int:
    return max(1, int(kit.price(c, key, PRICES[key])))


def line_text(ln: dict) -> str:
    v = VESSELS[ln['v']]
    if ln['v'] == 'que':
        return 'một cây kem que đậu xanh'
    if ln['v'] == 'hop':
        return f'hộp {FLAVOUR[ln["f"][0]]["short"]} {ln["g"]} gam'
    names = ' + '.join(FLAVOUR[f]['short'] for f in ln['f'])
    top = (' · rắc ' + ' hoặc '.join(_lower(TOPPINGS[x]['name']) for x in ln['top'])) if ln['top'] else ''
    return f'{_lower(v["name"])} {len(ln["f"])} viên ({names}){top}'


# ================================================================ tasks
def _kind(day: int, slot: int) -> str:
    if slot == 0:
        return 'setup'
    if day >= 3 and day % 3 == 0 and slot == 2:
        return 'tray'
    return 'serve'


def _pick(day: int, slot: int, mod: str) -> tuple:
    if day == 1:
        return ORDERS[min(2, slot - 1)] if slot <= 3 else ORDERS[(slot - 1) % 3]
    pool = [o for o in ORDERS if o[6] <= day and o[7] in (None, mod)]
    weighted = [o for o in pool for _ in range(3 if o[7] else 1)]
    return weighted[kit.rng(ID, day, slot).randrange(len(weighted))]


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot)
    common = dict(gen=GEN, stage='prep', cups=[], seq=0, tare=False, pack=None, melt=None, price=None, cash=None, cost=0,
                  choice=None, story=None)
    if kind == 'setup':
        needs = dict(setup=True, knob=KNOB_OK, note={'hot': 'Nắng gắt: kiểm tủ thật kỹ, kem dễ mềm.', 'outage': 'Phường báo cúp điện buổi trưa.',
                                                     'rain': 'Mưa chiều: kéo bạt che quầy.'}.get(mod, 'Xem nhiệt kế, soi hộp kem, thay nước muỗng rồi mở tiệm.'))
        return kit.base_task(ID, day, slot, serial, 0, 'Mở tiệm kem đầu ngày',
                             'Cô Hiền nhắn: “Cô đi chợ mua dừa. Con xem nhiệt kế tủ, soi mấy hộp kem, thay nước ngâm muỗng rồi hẵng bán nghe.”',
                             kind='setup', needs=needs, **common)
    npc, k, title, opening, lines, note, _, _, flags = TRAY if kind == 'tray' else _pick(day, slot, mod)
    needs = dict(lines=copy.deepcopy(lines), note=note, check=bool(flags.get('check')), coins=bool(flags.get('coins')),
                 allergy=flags.get('allergy'))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=k, needs=needs, **common)


FIXED = ('needs',)


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the shop's data
def _fresh_shop(day: int) -> dict:
    return dict(day=day, open=False, checked=False, well=False)


def _fresh_today(day: int) -> dict:
    return dict(day=day, scoops=0, customers=0, over_g=0, thin=0, melted=0, binned=0, peak=-18, batches=0, hm=0)


def initial() -> dict:
    return dict(v=1, intro=False, shop=_fresh_shop(0), fz=dict(temp=-18, knob=KNOB_OK, lid=False, read=False), well=dict(n=0, fresh=True),
                tubs={}, refrozen=None, warm_night=False, regulars={}, today=_fresh_today(0),
                stats=dict(scoops=0, customers=0, over_g=0, thin=0, melted=0, binned=0, fair=0, batches=0, hm=0), desk=kit.desk_initial(),
                batch=None, home=[], learn=dict(task=None, codes=[], done=False))


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'shop', 'fz', 'well', 'learn'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


def knob_of(day: int) -> int:
    """Where the knob is in the morning (someone turned it overnight on some days)."""
    if day == 1:
        return 2          # the first morning teaches the thermometer
    r = kit.rng(ID, 'knob', day).randrange(100)
    return KNOB_OK if r < 55 else (2, 3, 5, 6)[r % 4]


# ================================================================ the freezer
def target(d: dict) -> int:
    return KNOB_T[d['fz']['knob']]


def soft_of(temp: int) -> str:
    return 'mushy' if temp >= MUSHY_AT else 'soft' if temp >= SOFT_AT else 'hard' if temp <= -22 else 'ok'


def _fz_tick(d: dict, name: str, was_open: bool = True) -> None:
    """Time passes with one move at the counter: an open lid lets the cold out, a closed one brings it back.
    A scoop into a lid that was left open costs twice what a scoop from a freshly opened lid does."""
    fz = d['fz']
    if fz['lid']:
        fz['temp'] = min(0, fz['temp'] + (2 if name == 'kem_scoop' and was_open else 1))
    else:
        goal = target(d)
        fz['temp'] += max(-2, min(2, goal - fz['temp']))
    d['today']['peak'] = max(d['today']['peak'], fz['temp'])


# Moves that take no time at the freezer (a scrape or a topping is part of the scoop's moment).
FZ_STILL = ('kem_intro', 'kem_lid', 'kem_thermo', 'kem_desk', 'kem_short', 'kem_knob', 'kem_adjust', 'kem_top', 'kem_tare',
            'kem_mk_start', 'kem_mk_add', 'kem_mk_next', 'kem_mk_bin', 'kem_mk_toss')


def scoop_grams(d: dict, t: dict, flavour: str, press: str) -> int:
    temp = d['fz']['temp']
    hard = max(72, min(135, 100 + (temp + 18) * 35 // 10))
    base = PRESS[press] * hard * FLAVOUR[flavour]['soft'] // 10000
    jitter = _hash('kem-g', t['id'], t['seq']) % 17 - 8
    return max(20, base + jitter)


# ================================================================ the actions
FREE = ('kem_intro',)
NO_TICK = ('kem_intro', 'kem_lid', 'kem_thermo', 'kem_knob', 'kem_check', 'kem_vessel', 'kem_scoop', 'kem_adjust', 'kem_top',
           'kem_que', 'kem_tare', 'kem_drop', 'kem_pay', 'kem_short', 'kem_desk',
           'kem_mk_start', 'kem_mk_add', 'kem_mk_next', 'kem_mk_bin', 'kem_mk_toss')
PHYSICAL = ('kem_scoop', 'kem_que', 'kem_well', 'kem_discard', 'kem_pack',
            'kem_mk_steam', 'kem_mk_heat', 'kem_mk_cool', 'kem_mk_blend', 'kem_mk_churn', 'kem_mk_freeze')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'kem_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Tủ kem đang chờ dưới gốc phượng.')
    desk = d['desk']
    if name == 'kem_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'), hook=_desk_hook)
    if name == 'kem_lid':
        return _lid(s, c, d, p)
    kit.desk_block(desk, 'Có chuyện ở tiệm, quyết xong rồi bán tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở tiệm kem.')
    was_open = d['fz']['lid']
    result = fn(s, c, d, p)
    if name not in FZ_STILL:
        _fz_tick(d, name, was_open)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    if learning(d):
        return             # no surprises while cô Hiền is still teaching
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm kem.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _need_open(d: dict) -> None:
    _open_rules(d)


def _open_rules(d: dict, setup=None, need=kit.need) -> None:
    """The shop must be open before any customer's work (live 04-06/10: refusals on the first tap of a customer
    picked before “Mở tiệm”). public_data sends it as can.open, with a fix that brings up the morning set-up."""
    need(d['shop']['open'], 'Chưa mở tiệm: xem nhiệt kế, soi hộp kem, thay nước muỗng rồi bấm “Mở tiệm” nhé.',
         fix=dict(cmd='task_select', payload=dict(task=setup), label='🏪 Mở tiệm') if setup else None)


def _setup_id(c: dict):
    """Today's open set-up task (the morning chores), if any."""
    return next((t['id'] for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup'
                 and t.get('status') not in ('completed', 'referred', 'cancelled')), None)


# ---------------------------------------------------------------- the freezer and the morning
def _lid(s, c, d, p):
    fz = d['fz']
    want = p.get('open')
    fz['lid'] = bool(want) if want is not None else not fz['lid']
    return dict(message='🧊 Mở nắp tủ kem.' if fz['lid'] else '🧊 Đậy nắp tủ kem lại, giữ hơi lạnh.')


def _thermo(s, c, d, p):
    fz = d['fz']
    fz['read'] = True
    state = {'mushy': 'kem nhão rồi!', 'soft': 'kem đang mềm.', 'hard': 'lạnh quá, kem cứng như đá.', 'ok': 'vừa đẹp.'}[soft_of(fz['temp'])]
    knob = '' if fz['knob'] == KNOB_OK else f' Nút vặn đang ở số {fz["knob"]} (chuẩn là số {KNOB_OK}).'
    return dict(message=f'🌡️ Nhiệt kế tủ: {fz["temp"]} °C, {state}{knob}')


def _knob(s, c, d, p):
    knob = kit.integer(p.get('knob'), 1, 6)
    d['fz']['knob'] = knob
    goal = KNOB_T[knob]
    line = 'đúng mức cô Hiền dặn.' if knob == KNOB_OK else 'ấm quá, kem sẽ mềm.' if goal > -18 else 'lạnh quá, kem cứng, múc khó.'
    return dict(message=f'🎛️ Vặn nút về số {knob}: tủ sẽ về {goal} °C, {line}')


def _check(s, c, d, p):
    d['shop']['checked'] = True
    rf = d['refrozen']
    if rf:
        f = FLAVOUR[rf]
        return dict(message=f'🔍 {f["emoji"]} Hộp {_lower(f["name"])} cứng đá, mặt kem lổn nhổn tinh thể đá: kem đã chảy rồi đông lại. Bỏ, không bán.')
    return dict(message='🔍 Mấy hộp kem mịn, mặt phẳng, không có đá vụn. Bán được.')


def _discard(s, c, d, p):
    rf = d['refrozen']
    kit.need(rf, 'Không có hộp kem nào hỏng.')
    tub = d['tubs'].pop(rf, None)
    value = FLAVOUR[rf]['cost'] * (tub['g'] if tub else TUB_G) // TUB_G
    kit.waste(c, rf, 1, value, 'Kem chảy rồi đông lại')
    d['refrozen'] = None
    d['shop']['checked'] = True
    d['today']['binned'] += 1
    d['stats']['binned'] += 1
    return dict(message=f'🗑️ Bỏ hộp {_lower(FLAVOUR[rf]["name"])} đông đá lại, ghi sổ hao hụt.')


def _well(s, c, d, p):
    d['well'] = dict(n=0, fresh=True)
    d['shop']['well'] = True
    return dict(message='💧 Đổ nước cũ, rửa khay, thay nước sạch ngâm muỗng múc kem.')


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    fz, sh = d['fz'], d['shop']
    kit.need(not sh['open'], 'Tiệm mở rồi.')
    if not fz['read']:
        t['mistakes'] += 1
        cq.slip(t, 'no_thermo', 1, 'Chưa xem nhiệt kế đã bán, tủ ấm lạnh thế nào cũng không biết.', 'chưa xem nhiệt kế')
    if fz['knob'] != KNOB_OK:
        t['mistakes'] += 1
        warm = KNOB_T[fz['knob']] > KNOB_T[KNOB_OK]
        cq.slip(t, 'knob', 1, 'Tủ để ấm quá, kem mềm nhão cả ngày.' if warm else 'Tủ để lạnh quá, kem cứng, viên nào cũng bé.', 'nút tủ chưa đúng số')
    if d['refrozen']:
        t['mistakes'] += 1
        cq.slip(t, 'refrozen_left', 2, 'Còn hộp kem chảy rồi đông lại nằm trong tủ, lỡ múc bán cho khách.', 'chưa bỏ hộp kem hỏng')
    if not d['well']['fresh']:
        t['mistakes'] += 1
        cq.slip(t, 'well_old', 1, 'Nước ngâm muỗng từ hôm qua còn để nguyên.', 'chưa thay nước ngâm muỗng')
    sh['open'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Xem tủ, soi hộp kem, thay nước muỗng.')
    return dict(message='🍨 Mở tiệm! ' + ('Cô Hiền nhắn: “Giỏi lắm con, bán đắt nghe!”' if ok else 'Cô Hiền nhắn: “Mở đi con, mai nhớ kỹ hơn nghe.”'),
                celebrate=ok)


# ---------------------------------------------------------------- building an order
def _need_prep(t: dict) -> None:
    kit.need(t['known'], 'Hỏi khách gọi gì đã nhé.')
    kit.need(t['stage'] == 'prep', 'Đơn này đã tính tiền rồi.')


def _cup(t: dict) -> dict:
    kit.need(t['cups'], 'Chọn ly, ốc quế hay trái dừa trước đã.')
    return t['cups'][-1]


def _start_melt(d: dict, t: dict) -> None:
    if t['melt']:
        return
    units = sum(ln['g'] // 60 if ln['v'] == 'hop' else len(ln['f']) or 1 for ln in t['needs']['lines'])
    limit = MELT_BASE + MELT_UNIT * units + (MELT_TRAY if t['kind'] == 'tray' else 0)
    limit = limit * MELT_MOD.get(mod_of(t['day'])['id'], 100) // 100
    if d['fz']['temp'] >= SOFT_AT:
        limit = limit * 80 // 100
    t['melt'] = dict(start=round(kit.now(), 3), limit=int(limit), end=None)


def _vessel(s, c, d, p):
    t = _task(c, p, ('serve', 'hop', 'tray'))
    _need_open(d)
    _need_prep(t)
    v = kit.one_of(p.get('v'), [k for k in VESSELS if k != 'que'], 'Ly, ốc quế, trái dừa hay hộp?')
    kit.need(len(t['cups']) < CUP_MAX, 'Quầy hết chỗ đặt ly rồi.')
    x = VESSELS[v]
    cost = 0
    if x['item']:
        kit.need(kit.stock(c, x['item']) > 0, f'Hết {_lower(x["name"])} rồi. Nhập thêm ở kho, hoặc chọn cái khác.')
        cost = kit.take(c, x['item'], 1)
    t['cups'].append(dict(v=v, sc=[], top=None, c=cost))
    t['cost'] += cost
    kit.start_work(t)
    return dict(message=f'{x["emoji"]} Đặt {_lower(x["name"])} lên cân.' + (' Cân trừ bì hộp trước khi múc nhé.' if v == 'hop' and not t['tare'] else ''))


def _open_tub(c: dict, d: dict, f: str) -> dict:
    tub = d['tubs'].get(f)
    if tub and tub['g'] > 0:
        return tub
    home = next((i for i, h in enumerate(d['home']) if h['f'] == f and h['day'] < c['day']), None)
    if home is not None:       # a house tub that froze overnight goes first
        h = d['home'].pop(home)
        tub = dict(g=TUB_G, c=h['c'], day=c['day'], rf=False, hm=h['q'])
    else:
        kit.need(kit.stock(c, f) > 0, f'Hết {_lower(FLAVOUR[f]["name"])} rồi. Nói thật với khách, hoặc nhập thêm ở kho.')
        cost = kit.take(c, f, 1)
        tub = dict(g=TUB_G, c=cost, day=c['day'], rf=False, hm=None)
    d['tubs'][f] = tub
    return tub


def has_tub(c: dict, d: dict, f: str) -> bool:
    tub = d['tubs'].get(f)
    return bool(tub and tub['g'] > 0) or kit.stock(c, f) > 0 or any(h['f'] == f and h['day'] < c['day'] for h in d['home'])


def _scoop(s, c, d, p):
    t = _task(c, p, ('serve', 'hop', 'tray'))
    _need_open(d)
    _need_prep(t)
    cup = _cup(t)
    f = kit.one_of(p.get('f'), FLAVOUR, 'Tiệm không có vị này.')
    press = kit.one_of(p.get('press', 'vua'), PRESS, 'Múc nhẹ, vừa hay đầy tay?')
    x = VESSELS[cup['v']]
    kit.need(cup['v'] != 'que', 'Kem que lấy trong ngăn kéo, không múc.')
    kit.need(len(cup['sc']) < x['max'], f'{x["name"]} chỉ đựng {x["max"]} viên thôi.')
    tub = _open_tub(c, d, f)
    t['seq'] += 1
    g = scoop_grams(d, t, f, press)
    g = min(g, tub['g'])
    tub['g'] -= g
    flags = []
    if tub['rf']:
        flags.append('rf')
    hm = tub.get('hm')
    if d['fz']['temp'] >= MUSHY_AT or hm == 'soft':
        flags.append('mushy')
    if hm == 'ok':
        flags.append('hm')
    elif hm in ('icy', 'grainy'):
        flags.append(hm)
    w = d['well']
    w['n'] = min(999, w['n'] + 1)
    if not w['fresh'] or w['n'] > WELL_MAX:
        flags.append('dirty')
    cup['sc'].append(dict(f=f, g=g, a=0, x=flags))
    cost = tub['c'] * g // TUB_G
    cup['c'] += cost
    t['cost'] += cost
    if tub['g'] <= 0:
        d['tubs'].pop(f, None)
        if d['refrozen'] == f:
            d['refrozen'] = None
    d['fz']['lid'] = True
    d['today']['scoops'] += 1
    d['stats']['scoops'] += 1
    _start_melt(d, t)
    kit.start_work(t)
    fl = FLAVOUR[f]
    size = 'viên nhỏ, múc thêm chút' if g < GOOD_G[0] else 'viên to quá, gạt bớt' if g > GOOD_G[1] + 4 else 'viên tròn đẹp'
    warn = (' ⚠️ Kem lạo xạo đá!' if 'rf' in flags else ' ⚠️ Kem nhão chảy!' if 'mushy' in flags else
            ' ⚠️ Kem có dăm đá li ti.' if 'icy' in flags else ' ⚠️ Kem lợn cợn, không mịn.' if 'grainy' in flags else
            ' 🏠 Kem nhà làm, mịn thơm.' if 'hm' in flags else '')
    return dict(message=f'{fl["emoji"]} {PRESS_LABEL[press]} một viên {fl["short"]}: cân {g} gam, {size}.{warn}')


def _adjust(s, c, d, p):
    t = _task(c, p, ('serve', 'hop', 'tray'))
    _need_prep(t)
    cup = _cup(t)
    kit.need(cup['sc'], 'Chưa có viên kem nào để chỉnh.')
    sc = cup['sc'][-1]
    delta = kit.one_of(p.get('delta'), (1, -1), 'Thêm hay bớt?')
    kit.need(sc['a'] < ADJ_MAX, 'Viên này chỉnh đủ rồi, chỉnh nữa là nát viên kem.')
    tub = d['tubs'].get(sc['f'])
    if delta > 0:
        kit.need(tub and tub['g'] >= ADJ_G, 'Hộp kem này hết rồi.')
        tub['g'] -= ADJ_G
        sc['g'] += ADJ_G
        cost = tub['c'] * ADJ_G // TUB_G
        cup['c'] += cost
        t['cost'] += cost
    else:
        kit.need(sc['g'] > ADJ_G * 2, 'Viên kem nhỏ quá rồi.')
        sc['g'] -= ADJ_G
        if tub:
            tub['g'] += ADJ_G
    sc['a'] += 1
    return dict(message=f'🥄 {"Múc thêm" if delta > 0 else "Gạt bớt"} {ADJ_G} gam: viên kem còn {sc["g"]} gam.')


def _top(s, c, d, p):
    t = _task(c, p, ('serve', 'hop', 'tray'))
    _need_prep(t)
    cup = _cup(t)
    if p.get('cup') is not None:
        cup = t['cups'][kit.integer(p.get('cup'), 0, len(t['cups']) - 1)]
    kit.need(cup['v'] not in ('que', 'hop'), 'Kem que với hộp mang về không rắc topping.')
    top = p.get('top')
    if top in (None, '', 'none'):
        cup['top'] = None
        return dict(message='Bỏ topping ra.')
    top = kit.one_of(top, TOPPINGS, 'Topping không có.')
    cup['top'] = top
    return dict(message=f'{TOPPINGS[top]["emoji"]} Rắc {_lower(TOPPINGS[top]["name"])}.')


def _que(s, c, d, p):
    t = _task(c, p, ('serve',))
    _need_open(d)
    _need_prep(t)
    kit.need(len(t['cups']) < CUP_MAX, 'Quầy hết chỗ rồi.')
    kit.need(kit.stock(c, 'que') > 0, 'Hết kem que rồi. Nhập thêm ở kho nhé.')
    cost = kit.take(c, 'que', 1)
    t['cups'].append(dict(v='que', sc=[], top=None, c=cost))
    t['cost'] += cost
    d['fz']['lid'] = True
    _start_melt(d, t)
    kit.start_work(t)
    return dict(message='🍡 Lấy một cây kem que đậu xanh trong ngăn tủ.')


def _tare(s, c, d, p):
    t = _task(c, p, ('hop',))
    _need_prep(t)
    kit.need(not t['tare'], 'Đã trừ bì rồi.')
    kit.need(not any(cp['sc'] for cp in t['cups'] if cp['v'] == 'hop'), 'Kem đã vào hộp rồi: trừ bì phải làm lúc hộp còn rỗng.')
    t['tare'] = True
    return dict(message=f'⚖️ Đặt hộp rỗng lên cân, bấm TARE: cân về 0 (hộp nặng {BOX_TARE} gam).')


def _drop(s, c, d, p):
    """Throw away the cup on the counter (a wrong flavour, a melted cup)."""
    t = _task(c, p, ('serve', 'hop', 'tray'))
    _need_prep(t)
    cup = _cup(t)
    t['cups'].pop()
    t['cost'] = max(0, t['cost'] - cup['c'])
    if cup['c']:
        kit.waste(c, _waste_item(cup), 1, cup['c'], 'Ly kem làm lại')
    return dict(message=f'🗑️ Bỏ {_lower(VESSELS[cup["v"]]["name"])} vừa làm, làm lại cái khác.')


def _waste_item(cup: dict) -> str:
    """The stock item a thrown-away cup is booked under (its scoops' tub, or the cone / coconut / stick)."""
    if cup['sc']:
        return cup['sc'][0]['f']
    return VESSELS[cup['v']]['item'] or 'vani'


def _pack(s, c, d, p):
    t = _task(c, p, ('tray',))
    _need_prep(t)
    kit.need(t['cups'], 'Chưa có ly kem nào để xếp.')
    pack = kit.one_of(p.get('pack'), PACKS, 'Xếp kem vào gì?')
    t['pack'] = pack
    if t['melt'] and t['melt']['end'] is None:
        t['melt']['end'] = round(kit.now(), 3)
    return dict(message={'xop': '📦 Xếp sáu ly vào thùng xốp, lót túi đá gel, đậy kín nắp.',
                         'tui': '🛍️ Bỏ mấy ly kem vào túi ni-lông.',
                         'da_kho': '🌫️ Thả mấy cục đá khô vào khay, khói bốc trắng xóa.'}[pack])


# ---------------------------------------------------------------- handing it over
def hop_shown(t: dict, cup: dict) -> int:
    return sum(x['g'] for x in cup['sc']) + (0 if t['tare'] else BOX_TARE)


def cup_price(c: dict, t: dict, cup: dict) -> int:
    if cup['v'] == 'que':
        return _p(c, 'que')
    if cup['v'] == 'hop':
        return max(1, (hop_shown(t, cup) * _p(c, 'hop') + 50) // 100)
    v = sum((_p(c, 'vien_bo') if x['f'] == 'bo' else _p(c, 'vien')) + (HOME_PLUS if 'hm' in x['x'] else 0) for x in cup['sc'])
    if VESSELS[cup['v']]['price']:
        v += _p(c, VESSELS[cup['v']]['price'])
    if cup['top']:
        v += _p(c, 'top')
    return v


def _match(t: dict) -> tuple[list, list, list]:
    """Pair the cups on the counter with the lines of the order: (pairs, lines left, cups left)."""
    cups = list(range(len(t['cups'])))
    pairs, left = [], []
    for li, ln in enumerate(t['needs']['lines']):
        want = sorted(ln['f'])
        hit = next((ci for ci in cups if t['cups'][ci]['v'] == ln['v'] and sorted(x['f'] for x in t['cups'][ci]['sc']) == want), None)
        if hit is None and ln['v'] == 'hop':
            hit = next((ci for ci in cups if t['cups'][ci]['v'] == 'hop' and t['cups'][ci]['sc']
                        and {x['f'] for x in t['cups'][ci]['sc']} == set(ln['f'])), None)
        if hit is None:
            left.append(li)
        else:
            cups.remove(hit)
            pairs.append((li, hit))
    return pairs, left, cups


def _checks(c: dict, d: dict, t: dict, pairs: list, left: list, extra: list) -> None:
    """Record what the customer will notice at the hand-over."""
    n = t['needs']
    who = _who(t)
    if left:
        t['mistakes'] += 1
        ln = n['lines'][left[0]]
        cq.slip(t, 'missing', 2, f'Tôi gọi {line_text(ln)} mà không thấy, sai vị hay thiếu món rồi.', 'thiếu món, sai vị')
    if extra:
        t['mistakes'] += 1
        cq.slip(t, 'extra', 1, 'Có món tôi đâu có gọi.', 'đưa thừa món')
    scoops = [x for cp in t['cups'] for x in cp['sc'] if cp['v'] != 'hop']
    thin = [x for x in scoops if x['g'] < THIN]
    if thin:
        t['mistakes'] += 1
        d['today']['thin'] += len(thin)
        d['stats']['thin'] += len(thin)
        cq.slip(t, 'thin', 2 if n.get('check') else 1, f'Viên kem có {thin[0]["g"]} gam, bé xíu à.' if n.get('check') else 'Viên kem bé xíu à.',
                'viên kem thiếu gam')
    over = sum(max(0, x['g'] - GOOD_G[1]) for x in scoops if x['g'] >= FAT)
    d['today']['over_g'] += over
    d['stats']['over_g'] += over
    flags = {f for cp in t['cups'] for x in cp['sc'] for f in x['x']}
    if 'rf' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'refrozen', 2, 'Kem lạo xạo toàn đá, kem chảy rồi đông lại phải không?', 'bán kem đông đá lại', safety=True)
    if 'mushy' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'mushy', 1, 'Kem nhão nhoẹt như vừa múc từ nồi ra.', 'tủ để ấm, kem nhão')
    if 'dirty' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'well', 1, 'Muỗng nhúng thau nước đục ngầu rồi múc kem cho tôi.', 'nước ngâm muỗng bẩn')
    if 'grainy' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'grainy', 2, 'Kem lợn cợn, ăn không mịn chút nào.', 'mẻ kem nhà làm bị lợn cợn')
    elif 'icy' in flags:
        t['mistakes'] += 1
        cq.slip(t, 'icy', 1, 'Kem có dăm đá li ti, nhai sột soạt.', 'mẻ kem nhà làm bị dăm đá')
    allergen = n.get('allergy')
    if allergen and any(cp['top'] == allergen for cp in t['cups']):
        t['mistakes'] += 1
        cq.slip(t, 'allergy', 3, f'Đã dặn dị ứng {ALLERGENS.get(allergen, allergen)} mà vẫn rắc vào!', 'rắc topping khách dị ứng', safety=True)
    for li, ci in pairs:
        ln, cp = n['lines'][li], t['cups'][ci]
        if ln['top'] and cp['top'] not in ln['top']:
            t['mistakes'] += 1
            cq.slip(t, 'top_' + str(li), 1, 'Tôi dặn rắc topping mà quên mất rồi.' if not cp['top'] else 'Rắc nhầm topping rồi.', 'sai topping')
        elif not ln['top'] and cp['top']:
            t['mistakes'] += 1
            cq.slip(t, 'top_' + str(li), 1, 'Tôi đâu có kêu rắc gì.', 'rắc topping khách không gọi')
        if ln['v'] == 'hop':
            real = sum(x['g'] for x in cp['sc'])
            if real * 100 < ln['g'] * 95:
                t['mistakes'] += 1
                cq.slip(t, 'short', 1, f'Tôi lấy {ln["g"]} gam mà hộp có {real} gam.', 'hộp kem thiếu cân')
            if not t['tare'] and n.get('check'):
                t['mistakes'] += 1
                cq.slip(t, 'cheat_tare', 2, f'Cân luôn cái hộp {BOX_TARE} gam vào tiền kem à? Phải trừ bì chứ.', 'chưa trừ bì hộp')
    if d['fz']['lid']:
        t['mistakes'] += 1
        cq.slip(t, 'lid_open', 1, f'{who} chỉ cái tủ kem mở toang: “Đậy nắp lại kẻo kem chảy hết kìa!”', 'để nắp tủ mở')
    if t['kind'] == 'tray':
        if t['pack'] == 'tui':
            t['mistakes'] += 1
            cq.slip(t, 'pack_bag', 2, 'Mang lên tới lớp kem chảy hết nửa ly.', 'không xếp thùng giữ lạnh')
        elif t['pack'] == 'da_kho':
            t['mistakes'] += 1
            cq.slip(t, 'dry_ice', 2, 'Đá khô nằm ngay cạnh ly, tụi nhỏ thò tay vào là bỏng lạnh!', 'để đá khô cạnh ly kem', safety=True)
    m = t['melt']
    if m:
        el = (m['end'] if m['end'] is not None else kit.now()) - m['start']
        if el > m['limit'] * 3 / 2:
            t['mistakes'] += 1
            d['today']['melted'] += 1
            d['stats']['melted'] += 1
            cq.slip(t, 'melted', 2, 'Kem chảy tràn ra tay, nhỏ giọt xuống áo luôn.', 'đưa kem quá chậm, kem chảy')
        elif el > m['limit']:
            t['mistakes'] += 1
            cq.slip(t, 'melting', 1, 'Kem bắt đầu chảy rồi.', 'đưa kem hơi chậm')


def _serve(s, c, d, p):
    t = _task(c, p, ('serve', 'hop', 'tray'))
    _need_open(d)
    _need_prep(t)
    kit.need(t['cups'], 'Chưa có món nào trên quầy.')
    kit.need(all(cp['sc'] or cp['v'] == 'que' for cp in t['cups']), 'Còn ly rỗng trên quầy: múc kem hoặc bỏ ly đó ra.')
    if t['kind'] == 'tray':
        kit.need(t['pack'], 'Khay kem phải xếp vào thùng trước khi đưa chị Mai Anh mang đi.')
    n = t['needs']
    for ln in n['lines']:
        if ln['v'] == 'hop':
            cup = next((cp for cp in t['cups'] if cp['v'] == 'hop'), None)
            if cup and sum(x['g'] for x in cup['sc']) * 100 > ln['g'] * 115:
                return dict(message=f'{_who(t)}: “Nhiều quá, tôi lấy {ln["g"]} gam thôi. Gạt bớt giùm.”', correct=False)
    caught = _catch(c, d, t)
    if caught:
        return caught
    pairs, left, extra = _match(t)
    _checks(c, d, t, pairs, left, extra)
    t['price'] = max(1, sum(cup_price(c, t, t['cups'][ci]) for _, ci in pairs)) if pairs else 1
    hm = sum(1 for cp in t['cups'] for x in cp['sc'] if 'hm' in x['x'])
    if hm:
        d['today']['hm'] += hm
        d['stats']['hm'] += hm
    if t['melt'] and t['melt']['end'] is None:
        t['melt']['end'] = round(kit.now(), 3)
    t['stage'] = 'pay'
    rec = till.new(t['price'], t['id'], c=c, t=t)
    if n.get('coins') and 'sp' not in rec:
        rec['tender'] = coins(t['price'], t['id'])
    t['cash'] = rec
    head = f'🍨 Đưa kem cho {_who(t)} · {t["price"]} xu.'
    if hm and not any(x['code'] in ('grainy', 'icy', 'mushy', 'refrozen') for x in cq.slips(t)):
        head += f' 🏠 {_who(t)} nếm thử: “Kem nhà làm hả? Thơm ghê!”'
    if n.get('coins') and 'sp' not in rec:
        return dict(message=f'{head} Bé đổ ra quầy {len(rec["tender"])} đồng xu lẻ: đếm cho đúng rồi thối lại.')
    return dict(message=f'{head} Khách đưa {sum(rec["tender"])} xu: thối lại cho đúng.')


def learning(d: dict) -> bool:
    """Học nghề: the first APPRENTICE customers, cô Hiền at your side."""
    return not d['learn']['done'] and d['stats']['customers'] < APPRENTICE


def _catch(c: dict, d: dict, t: dict) -> dict | None:
    """While learning, cô Hiền looks at the order before it goes out: the first time a mistake shows on an
    order she stops you and says how to fix it (nothing is recorded). The same mistake again goes through,
    and a melting order is never held back (time cannot be undone)."""
    if not learning(d):
        return None
    lr = d['learn']
    if lr['task'] != t['id']:
        lr['task'], lr['codes'] = t['id'], []
    tt, dd = copy.deepcopy(t), copy.deepcopy(d)
    pairs, left, extra = _match(tt)
    _checks(c, dd, tt, pairs, left, extra)
    for x in cq.slips(tt):
        code = 'top' if x['code'].startswith('top_') else x['code']
        if code in CATCH and code not in lr['codes']:
            lr['codes'].append(code)
            return dict(message=f'👩‍🍳 Cô Hiền: “{CATCH[code]}”', correct=False, lesson=code)
    return None


def _graduate(s: dict, d: dict) -> str:
    if d['learn']['done'] or d['stats']['customers'] < APPRENTICE:
        return ''
    d['learn'].update(done=True, task=None, codes=[])
    story = bool((s.get('journey') or {}).get('story'))
    tail = ' Muốn học kỹ hơn thì thi Chứng chỉ làm kem nghe.' if story else ''
    return f' 🎓 Học nghề xong! Cô Hiền: “Giờ con tự đứng quầy được rồi. Cô đi nấu kem đây.{tail}”'


def coins(price: int, seed: str) -> list[int]:
    """A pile from the piggy bank: small coins, a little more than the price (stored once)."""
    left = price + _hash('kem-coins-x', seed) % 3
    out, i = [], 0
    while left > 0 and len(out) < 20:
        roll = _hash('kem-coin', seed, i) % 10
        coin = 5 if roll < 3 and left >= 5 else 2 if roll < 7 and left >= 2 else 1
        out.append(coin)
        left -= coin
        i += 1
    if left > 0:
        return till.greedy(price)
    return sorted(out, reverse=True)


def _decline(s, c, d, p):
    """Out of what the customer wants: say so honestly."""
    t = _task(c, p, ('serve', 'hop', 'tray'))
    kit.need(t['known'] and t['stage'] == 'prep', 'Không phải lúc này.')
    for cup in t['cups']:
        if cup['c']:
            kit.waste(c, _waste_item(cup), 1, cup['c'], 'Đơn không bán được')
    t['cups'], t['cost'], t['choice'] = [], 0, 'decline'
    kit.start_work(t)
    msg = _finish(s, c, d, t, 0, f'Nói thật với {_who(t)}: tiệm hết vị khách gọi, hẹn hôm sau.')
    return dict(message='🙏 ' + msg)


def _pay(s, c, d, p):
    t = _task(c, p, ('serve', 'hop', 'tray'))
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    who = _who(t)
    rec = t['cash']
    chk = till.check(s, c, t, rec, p.get('change'), who)
    if chk['stop']:
        return dict(message='💵 ' + chk['message'], correct=False)
    react = cq.react(s, c, t, t['price'], who=who)
    st = till.settle(s, c, t, rec, react, who)
    net = react['pay'] - st['loss']
    d['today']['customers'] += 1
    d['stats']['customers'] += 1
    if not cq.slips(t):
        d['stats']['fair'] += 1
    parts = [x for x in (react['message'], st['message']) if x]
    msg = _finish(s, c, d, t, max(0, net), ' '.join(parts))
    if net < 0:
        lost = min(-net, c['money'])
        if lost:
            kit.money(s, c, -lost, f'Thối dư cho khách: {t["title"]}'[:120], t['id'], 'change_loss')
    given = sum(rec['change'])
    head = f'💵 Thu {t["price"]} xu' + (f', thối {given} xu.' if given else '.')
    grad = _graduate(s, d)
    return dict(message=f'{head} {msg}{grad}'.strip(), celebrate=not cq.slips(t) or bool(grad))


def _short(s, c, p):
    t = _task(c, p)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    return till.short_action(s, c, t, t['cash'], p, _who(t))


# ---------------------------------------------------------------- finishing a customer
def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str) -> str:
    i = _npc_index(t)
    story = ''
    if i in REG_STORY and t['kind'] != 'setup':
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        lines = REG_STORY[i]
        story = lines[min(r['visits'], len(lines)) - 1]
        t['story'] = story
    t['stage'] = 'done'
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    return f'{narrative} 💬 {story}'.strip() if story else narrative


def _desk_hook(s: dict, c: dict, key: str, v) -> str | None:
    d = _data(c)
    if key == 'fz':
        d['fz']['temp'] = min(0, d['fz']['temp'] + int(v))
        d['today']['peak'] = max(d['today']['peak'], d['fz']['temp'])
        return f'Tủ kem lên {d["fz"]["temp"]} °C.'
    return None


# ---------------------------------------------------------------- kem nhà làm (a house batch)
def has_cert(s: dict) -> bool:
    j = s.get('journey') or {}
    rec = (j.get('certificates') or {}).get(CERT_ID)
    return isinstance(rec, dict) and rec.get('earned_day') is not None


def recipe_open(s: dict, c: dict, f: str) -> bool:
    if not RECIPES[f]['cert']:
        return True
    if (s.get('journey') or {}).get('story'):
        return has_cert(s)
    return c['day'] >= CERT_FREE_DAY


def _batch(d: dict) -> dict:
    b = d['batch']
    kit.need(b, 'Chưa bắt đầu mẻ kem nào. Chọn công thức trong sổ cô Hiền trước.')
    return b


def _step(b: dict) -> str:
    return RECIPES[b['f']]['steps'][b['step']]


def _at(b: dict, step: str) -> None:
    kit.need('burnt' not in b['q'], 'Nồi khét rồi: mẻ này phải đổ bỏ thôi.')
    kit.need(_step(b) == step, f'Bây giờ là bước “{STEP_LABEL[_step(b)]}”.')


def _mk_start(s, c, d, p):
    kit.need(d['batch'] is None, 'Đang làm dở một mẻ rồi. Làm xong hoặc đổ bỏ mẻ đó trước.')
    kit.need(d['today']['batches'] < 1, 'Máy đánh kem chỉ chạy một mẻ mỗi ngày. Mai làm tiếp nhé.')
    kit.need(len(d['home']) < HOME_MAX, f'Trong tủ đã có {HOME_MAX} hộp kem nhà làm, bán bớt rồi hẵng nấu thêm.')
    f = kit.one_of(p.get('f'), RECIPES, 'Sổ công thức không có món này.')
    r = RECIPES[f]
    kit.need(recipe_open(s, c, f), 'Công thức kem khoai môn cô Hiền chỉ dạy cho người có Chứng chỉ làm kem.'
             if (s.get('journey') or {}).get('story') else f'Công thức kem khoai môn mở từ ngày {CERT_FREE_DAY}.')
    kit.money(s, c, -r['cost'], f'Nguyên liệu: {r["name"]}', f'kem-batch-{c["day"]}', 'materials')
    d['batch'] = dict(f=f, step=0, ing={}, temp=30, n=0, churn=None, q=[], cost=r['cost'], day=c['day'])
    d['today']['batches'] += 1
    d['stats']['batches'] += 1
    return dict(message=f'📒 Mở sổ cô Hiền: {r["name"]}. Mua nguyên liệu hết {r["cost"]} xu. {r["note"]}')


def _mk_steam(s, c, d, p):
    b = _batch(d)
    _at(b, 'steam')
    b['n'] = min(20, b['n'] + 1)
    need = RECIPES[b['f']]['steam']
    left = need - b['n']
    return dict(message='♨️ Hấp khoai thêm một lượt: ' + (f'xiên đũa còn cứng, hấp thêm {left} lượt nữa.' if left > 0 else 'xiên đũa thấy bở, khoai chín rồi.'))


def _mk_add(s, c, d, p):
    b = _batch(d)
    _at(b, 'measure')
    r = RECIPES[b['f']]
    ing = next((x for x in r['ings'] if x['id'] == p.get('ing')), None)
    kit.need(ing, 'Nguyên liệu không có trong công thức.')
    amt = kit.integer(p.get('amt'), 0, 10000)
    kit.need(amt in ing['opts'], 'Lượng đó không có trên vạch đong.')
    b['ing'][ing['id']] = amt
    return dict(message=f'🥣 Đong {_lower(ing["name"])}: {amt} {ing["unit"]}.')


def _mk_heat(s, c, d, p):
    b = _batch(d)
    _at(b, 'cook')
    fire = kit.one_of(p.get('fire', 'nho'), FIRE, 'Lửa nhỏ hay lửa lớn?')
    b['temp'] = min(120, b['temp'] + FIRE[fire] + _hash('kem-heat', b['day'], b['f'], b['n']) % 3)
    b['n'] = min(20, b['n'] + 1)
    t = b['temp']
    if t >= BURNT_AT:
        b['q'].append('burnt')
        return dict(message=f'🔥 {t} °C: sôi trào, khét đáy nồi! Mùi khét bay khắp góc phố. Mẻ này phải đổ bỏ.')
    if t >= BOIL_AT:
        return dict(message=f'🔥 {t} °C: sôi sùng sục, nước cốt bắt đầu tách dầu! Tắt bếp ngay.')
    if t >= COOK_OK[0]:
        return dict(message=f'🔥 {t} °C: hỗn hợp sánh lại, nhấc muỗng thấy phủ đều. Tắt bếp được rồi.')
    return dict(message=f'🔥 {t} °C: khuấy đều tay, hỗn hợp còn loãng.')


def _mk_cool(s, c, d, p):
    b = _batch(d)
    _at(b, 'cool')
    b['temp'] = max(4, b['temp'] - 22)
    t = b['temp']
    return dict(message=f'🧊 Ngâm nồi vào thau nước đá, khuấy: còn {t} °C.' + (' Đủ lạnh để đánh kem.' if t <= COOL_OK else ' Còn ấm, ngâm thêm.'))


def _mk_blend(s, c, d, p):
    b = _batch(d)
    _at(b, 'blend')
    b['n'] = min(20, b['n'] + 1)
    left = RECIPES[b['f']]['blend'] - b['n']
    return dict(message='🌀 Xay một lượt: ' + ('còn lổn nhổn xơ bơ, xay thêm.' if left > 0 else 'hỗn hợp mịn mượt, xanh ngà.'))


def _defects_of(b: dict, step: str) -> list[str]:
    """What the step just finished leaves in the batch (recorded when moving on)."""
    r = RECIPES[b['f']]
    out = []
    if step == 'measure':
        for x in r['ings']:
            amt = b['ing'][x['id']]
            if amt < x['right'] and x['low']:
                out.append(x['low'])
            elif amt > x['right'] and x['high']:
                out.append(x['high'])
    elif step == 'steam' and b['n'] < r['steam']:
        out.append('grainy')
    elif step == 'blend' and b['n'] < r['blend']:
        out.append('grainy')
    elif step == 'cook':
        if b['temp'] < COOK_OK[0]:
            out.append('icy')
        elif b['temp'] >= BOIL_AT:
            out.append('grainy')
    return out


def _mk_next(s, c, d, p):
    b = _batch(d)
    step = _step(b)
    kit.need('burnt' not in b['q'], 'Nồi khét rồi: mẻ này phải đổ bỏ thôi.')
    kit.need(step not in ('churn', 'freeze'), 'Bước này bấm nút riêng.')
    if step == 'measure':
        missing = [x['name'] for x in RECIPES[b['f']]['ings'] if x['id'] not in b['ing']]
        kit.need(not missing, f'Còn chưa đong: {", ".join(_lower(x) for x in missing)}.')
    if step == 'cook':
        kit.need(b['n'] > 0, 'Chưa bắc nồi lên bếp.')
    b['q'] = (b['q'] + _defects_of(b, step))[:10]
    b['step'] += 1
    b['n'] = 0
    words = {'steam': '♨️ Nhấc xửng khoai, nghiền mịn.', 'measure': '🥣 Đong xong, đổ hết vào nồi.',
             'cook': f'🔥 Tắt bếp ở {b["temp"]} °C.', 'cool': f'🧊 Nhấc nồi khỏi thau đá ({b["temp"]} °C).',
             'blend': '🌀 Đổ hỗn hợp ra âu.'}[step]
    return dict(message=f'{words} Tiếp theo: {STEP_LABEL[_step(b)].lower()}.')


def _mk_churn(s, c, d, p):
    b = _batch(d)
    _at(b, 'churn')
    m = kit.one_of(kit.integer(p.get('min'), 1, 120), CHURN_MIN, 'Hẹn giờ máy không có mức đó.')
    lo, hi = RECIPES[b['f']]['churn']
    q = []
    if b['temp'] > COOL_OK:
        q.append('soft')
    if m < lo:
        q.append('soft')
    elif m > hi + 5:
        q.append('grainy')
    b['churn'] = m
    b['q'] = (b['q'] + q)[:10]
    b['step'] += 1
    look = 'kem còn lỏng như sữa chua uống' if m < lo else 'kem bắt đầu kết hạt béo' if m > hi + 5 else 'kem bông mịn, dẻo quánh'
    return dict(message=f'⚙️ Máy đánh kem chạy {m} phút: {look}.')


def quality(b: dict) -> str:
    return max(b['q'], key=lambda x: DEFECT_RANK[x]) if b['q'] else 'ok'


def _mk_freeze(s, c, d, p):
    b = _batch(d)
    _at(b, 'freeze')
    q = quality(b)
    d['home'].append(dict(f=b['f'], q=q, day=c['day'], c=b['cost']))
    d['batch'] = None
    r = RECIPES[b['f']]
    if q == 'ok':
        return dict(message=f'🏠 Đổ {_lower(r["name"])} vào hộp, dán nhãn ngày, cho vào tủ. Đông qua đêm, mai bán được. '
                            f'Cô Hiền nếm thử: “Mịn rồi đó con!”', celebrate=True)
    return dict(message=f'🏠 Đổ {_lower(r["name"])} vào hộp, cho vào tủ. Cô Hiền nếm thử: “Mẻ này {DEFECT_NOTE[q]} rồi con. '
                        f'Bán thì khách chê, đổ bỏ thì tiếc: con tính.”')


def _mk_bin(s, c, d, p):
    b = _batch(d)
    kit.waste(c, b['f'], 1, b['cost'], 'Mẻ kem nhà làm hỏng')
    d['batch'] = None
    return dict(message=f'🗑️ Đổ bỏ mẻ {_lower(RECIPES[b["f"]]["name"])}, rửa nồi. Mai làm lại cẩn thận hơn.')


def _mk_toss(s, c, d, p):
    kit.need(d['home'], 'Không có hộp kem nhà làm nào.')
    i = kit.integer(p.get('i'), 0, len(d['home']) - 1)
    h = d['home'].pop(i)
    kit.waste(c, h['f'], 1, h['c'], 'Hộp kem nhà làm không đạt')
    d['today']['binned'] += 1
    d['stats']['binned'] += 1
    return dict(message=f'🗑️ Bỏ hộp {_lower(RECIPES[h["f"]]["name"])} nhà làm ({DEFECT_NOTE.get(h["q"], "không đạt")}).')


ACTIONS = {
    'kem_mk_start': _mk_start, 'kem_mk_steam': _mk_steam, 'kem_mk_add': _mk_add, 'kem_mk_heat': _mk_heat, 'kem_mk_cool': _mk_cool,
    'kem_mk_blend': _mk_blend, 'kem_mk_next': _mk_next, 'kem_mk_churn': _mk_churn, 'kem_mk_freeze': _mk_freeze,
    'kem_mk_bin': _mk_bin, 'kem_mk_toss': _mk_toss,
    'kem_thermo': _thermo, 'kem_knob': _knob, 'kem_check': _check, 'kem_discard': _discard, 'kem_well': _well, 'kem_open': _open,
    'kem_vessel': _vessel, 'kem_scoop': _scoop, 'kem_adjust': _adjust, 'kem_top': _top, 'kem_que': _que, 'kem_tare': _tare,
    'kem_drop': _drop, 'kem_pack': _pack, 'kem_serve': _serve, 'kem_decline': _decline, 'kem_pay': _pay,
    'kem_short': lambda s, c, d, p: _short(s, c, p),
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    knob = knob_of(day)
    fz = d['fz']
    fz.update(knob=knob, lid=False, read=False, temp=KNOB_T[knob] + (2 if knob < KNOB_OK else 0) + (6 if d['warm_night'] else 0))
    d['shop'] = _fresh_shop(day)
    d['today'] = _fresh_today(day)
    d['today']['peak'] = fz['temp']
    d['well'] = dict(n=0, fresh=False)          # last night's water
    # A tub that melted and froze again: after a warm afternoon, or on some mornings (a power cut in the night).
    rf = None
    if day >= 2 and (d['warm_night'] or kit.rng(ID, 'refrozen', day).randrange(100) < 18):
        have = [f['id'] for f in FLAVOURS if d['tubs'].get(f['id']) or kit.stock(c, f['id'])]
        if have:
            rf = have[kit.rng(ID, 'refrozen-f', day).randrange(len(have))]
            tub = d['tubs'].get(rf)
            if not tub:
                cost = kit.take(c, rf, 1)
                tub = d['tubs'][rf] = dict(g=TUB_G, c=cost, day=day, rf=False)
            tub['rf'] = True
    d['refrozen'] = rf
    d['warm_night'] = False
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    setup = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] == day
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if setup is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        setup = make_task(day, 0, c['turn'])
        c['tasks'].append(setup)
        on_task(s, c, setup)
    if setup:
        c['active_task'] = setup['id']
        setup['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK, hook=_desk_hook)
    today = d['today']
    lines = [f'🍨 Múc {today["scoops"]} viên kem cho {today["customers"]} khách.']
    if today['over_g']:
        lines.append(f'⚖️ Cô Hiền dò sổ: hôm nay múc dư {today["over_g"]} gam, gần {max(1, today["over_g"] // 65)} viên kem cho không. '
                     'Mai múc vừa tay, nhìn cân nghe con.')
    elif today['thin']:
        lines.append(f'⚖️ Cô Hiền dặn: có {today["thin"]} viên kem thiếu gam, khách thiệt. Viên nào cũng nhìn cân nghe con.')
    elif today['scoops']:
        lines.append('⚖️ Cô Hiền dò cân: viên nào cũng tròn, đủ gam. Giỏi!')
    if today['melted']:
        lines.append(f'💧 Có {today["melted"]} lần kem chảy trước khi tới tay khách.')
    # Old open tubs are thrown out; a warm afternoon leaves a tub frozen again for tomorrow.
    for f, tub in list(d['tubs'].items()):
        if c['day'] - tub['day'] >= TUB_DAYS:
            kit.waste(c, f, 1, tub['c'] * tub['g'] // TUB_G, 'Hộp kem mở quá lâu')
            d['tubs'].pop(f)
            if d['refrozen'] == f:
                d['refrozen'] = None
    if today['hm']:
        lines.append(f'🏠 Bán {today["hm"]} viên kem nhà làm, khách khen thơm.')
    b = d['batch']
    if b:
        kit.waste(c, b['f'], 1, b['cost'], 'Mẻ kem làm dở cuối ngày')
        d['batch'] = None
        lines.append(f'🥣 Mẻ {_lower(RECIPES[b["f"]]["name"])} làm dở tới tối phải đổ bỏ.')
    for h in list(d['home']):
        if c['day'] - h['day'] >= TUB_DAYS:
            kit.waste(c, h['f'], 1, h['c'], 'Hộp kem nhà làm để quá lâu')
            d['home'].remove(h)
    fresh = [h for h in d['home'] if h['day'] == c['day']]
    if fresh:
        lines.append(f'🏠 {len(fresh)} hộp kem nhà làm đang đông trong tủ, mai bán được.')
    warm = today['peak'] >= REFREEZE_AT
    d['warm_night'] = warm
    if warm:
        lines.append(f'🌡️ Có lúc tủ lên tới {today["peak"]} °C: mai nhớ soi kỹ hộp kem, có hộp sẽ đông đá lại.')
    if desk_note:
        lines.append(desk_note)
    d['shop'].update(open=False, checked=False, well=False)
    d['fz']['lid'] = False
    tubs = sum(kit.stock(c, f['id']) for f in FLAVOURS)
    return dict(lines=lines, note=f'Trong tủ còn {tubs} hộp kem chưa mở, {len(d["tubs"])} hộp đang múc dở.',
                scoops=today['scoops'], customers=today['customers'], over=today['over_g'], peak=today['peak'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        fridge = 5 - len(codes & {'no_thermo', 'knob'})
        clean = 5 - len(codes & {'refrozen_left', 'well_old'}) * 2
        return dict(criteria=[dict(key='fridge', label='Tủ kem đúng nhiệt', score=max(2, fridge), note='xem nhiệt kế, nút số 4' if fridge == 5 else 'tủ chưa đúng mức'),
                              dict(key='clean', label='Hộp kem tốt, muỗng sạch', score=max(1, clean), note='soi hộp, thay nước' if clean == 5 else 'còn sót khâu chuẩn bị')])
    if t.get('choice') == 'decline':
        return dict(criteria=[dict(key='honest', label='Nói thật', score=5, note='hết vị thì nói thật'),
                              dict(key='order', label='Có món đúng ý', score=3, note='lần này chưa có')])
    order = 2 if 'missing' in codes else 4 if codes & {'extra'} or any(k.startswith('top_') for k in codes) else 5
    scoop = 2 if codes & {'cheat_tare', 'grainy'} else 3 if codes & {'thin', 'short', 'icy'} else 5
    cold = 1 if codes & {'refrozen'} else 2 if codes & {'melted', 'pack_bag'} else 3 if codes & {'melting', 'mushy'} else 5
    clean = 1 if codes & {'allergy', 'dry_ice'} else 3 if codes & {'well', 'lid_open'} else 5
    return dict(criteria=[dict(key='order', label='Đúng món', score=order, note='đúng vị, đúng topping' if order == 5 else 'món chưa đúng ý'),
                          dict(key='scoop', label='Viên kem đủ gam, mịn', score=scoop, note='viên tròn, đủ gam' if scoop == 5 else
                               'kem không mịn' if codes & {'grainy', 'icy'} else 'viên kem thiếu'),
                          dict(key='cold', label='Kem lạnh, không chảy', score=cold, note='lạnh vừa, mịn' if cold == 5 else 'kem chảy, nhão'),
                          dict(key='clean', label='Sạch sẽ, an toàn', score=clean, note='muỗng sạch, nhớ dị ứng' if clean == 5 else 'chưa sạch, chưa an toàn'),
                          dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')]
                + ([dict(key='home', label='Kem nhà làm', score=5, note='thơm, mịn, khác kem hộp')]
                   if any('hm' in x['x'] for cp in t.get('cups') or [] for x in cp['sc']) and not codes & {'grainy', 'icy', 'mushy'} else []))


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return 'Cô Hiền dặn: xem nhiệt kế, vặn nút tủ về số 4, soi hộp kem (hộp đông đá lại thì bỏ), thay nước ngâm muỗng rồi mở tiệm. ' + n['note']
    lines = ', '.join(line_text(x) for x in n['lines'])
    tail = ''
    if n.get('allergy'):
        tail += f' ⚠️ Dị ứng {ALLERGENS.get(n["allergy"], n["allergy"])}.'
    if n.get('check'):
        tail += ' Khách nhìn cân rất kỹ.'
    return f'{_who(t)} gọi: {lines}.{tail} {n["note"]}'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
    v['cash'] = till.public(t.get('cash'))
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    fz = d['fz']
    stock = {x['id']: kit.stock(c, x['id']) for x in ITEMS} if c['ext'].get('inv') else {}
    return dict(can=dict(open=kit.check(_open_rules, d, _setup_id(c))), intro=d['intro'], shop=d['shop'], fz=dict(fz, goal=KNOB_T.get(fz.get('knob'), -18), feel=soft_of(fz.get('temp', -18))),
                well=dict(n=d['well']['n'], fresh=d['well']['fresh'], dirty=not d['well']['fresh'] or d['well']['n'] > WELL_MAX),
                tubs={k: dict(g=v['g']) for k, v in d['tubs'].items()}, refrozen=d['refrozen'] if d['shop'].get('checked') else None,
                stock=stock, mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], DESK, ID), batch=_batch_public(d['batch']),
                home=[dict(h, ready=h['day'] < c['day']) for h in d['home']], made_today=d['today'].get('batches', 0) >= 1,
                learn=_learn_public(d))


def _batch_public(b: dict | None) -> dict | None:
    if not b:
        return None
    steps = RECIPES[b['f']]['steps']
    return dict(f=b['f'], step=steps[b['step']] if b['step'] < len(steps) else 'freeze', at=b['step'], of=len(steps), ing=dict(b['ing']),
                temp=b['temp'], n=b['n'], churn=b['churn'], burnt='burnt' in b['q'], cost=b['cost'])


def _learn_public(d: dict) -> dict:
    on = not d['learn']['done'] and d['stats']['customers'] < APPRENTICE
    n = min(d['stats']['customers'], APPRENTICE - 1)
    return dict(on=on, n=d['stats']['customers'], of=APPRENTICE, title=LESSONS[n][0] if on else None, text=LESSONS[n][1] if on else None)


def content() -> dict:
    return dict(flavours=[dict(id=x['id'], name=x['name'], short=x['short'], emoji=x['emoji']) for x in FLAVOURS],
                vessels={k: dict(name=v['name'], emoji=v['emoji'], max=v['max'], item=v['item']) for k, v in VESSELS.items()},
                toppings=TOPPINGS, packs=PACKS, press=PRESS, press_label=PRESS_LABEL, good=list(GOOD_G), thin=THIN, fat=FAT,
                adj=ADJ_G, adj_max=ADJ_MAX, knob_t={str(k): v for k, v in KNOB_T.items()}, knob_ok=KNOB_OK, soft_at=SOFT_AT,
                mushy_at=MUSHY_AT, well_max=WELL_MAX, box_tare=BOX_TARE, tub_g=TUB_G, prices=PRICES, allergens=ALLERGENS,
                denoms=list(till.DENOMS), intro=INTRO, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE],
                recipes={k: dict(name=r['name'], emoji=r['emoji'], cost=r['cost'], cert=r['cert'], steps=list(r['steps']), churn=list(r['churn']),
                                 steam=r['steam'], blend=r['blend'], note=r['note'],
                                 ings=[{kk: x[kk] for kk in ('id', 'name', 'unit', 'opts', 'card')} for x in r['ings']])
                         for k, r in RECIPES.items()},
                fire=FIRE, cook_ok=list(COOK_OK), boil_at=BOIL_AT, cool_ok=COOL_OK, churn_min=list(CHURN_MIN), home_plus=HOME_PLUS,
                home_max=HOME_MAX, cert_id=CERT_ID, cert_free_day=CERT_FREE_DAY, step_label=STEP_LABEL, defect_note=DEFECT_NOTE,
                apprentice=APPRENTICE)


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'setup':
        return 'Xem nhiệt kế → vặn nút về số 4 → soi hộp kem (đông đá thì bỏ) → thay nước muỗng → Mở tiệm.'
    if t.get('kind') == 'hop':
        return 'Hỏi khách → đặt hộp lên cân, trừ bì → múc tới đủ gam → đậy nắp tủ → đưa kem → thu tiền.'
    return 'Hỏi khách → chọn ly / ốc quế → múc từng viên, nhìn cân 60–70 gam → đậy nắp tủ → topping → đưa kem trước khi chảy → thu tiền.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'wash':
        d['well'] = dict(n=0, fresh=True)
        return 'Đã thay nước ngâm muỗng, lau sạch mặt quầy.'
    if e.get('role') == 'call':
        return 'Đã mời học sinh xếp hàng trật tự trước cổng.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu tiệm kem sai.')


def _vnum(x, lo, hi) -> None:
    kit.need(type(x) in (int, float) and lo <= x <= hi, 'Dữ liệu tiệm kem sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc tiệm kem không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc tiệm kem sai.')
    cups = t.get('cups')
    kit.need(isinstance(cups, list) and len(cups) <= CUP_MAX, 'Món trên quầy sai.')
    for cp in cups:
        kit.need(isinstance(cp, dict) and set(cp) == {'v', 'sc', 'top', 'c'} and cp['v'] in VESSELS
                 and (cp['top'] is None or cp['top'] in TOPPINGS), 'Món trên quầy sai.')
        kit.integer(cp['c'], 0, 10000)
        kit.need(isinstance(cp['sc'], list) and len(cp['sc']) <= SCOOP_MAX, 'Viên kem sai.')
        for x in cp['sc']:
            kit.need(isinstance(x, dict) and set(x) == {'f', 'g', 'a', 'x'} and x['f'] in FLAVOUR, 'Viên kem sai.')
            kit.integer(x['g'], 1, 400)
            kit.integer(x['a'], 0, ADJ_MAX)
            kit.need(isinstance(x['x'], list) and set(x['x']) <= {'rf', 'mushy', 'dirty', 'hm', 'icy', 'grainy'} and len(x['x']) <= 4,
                     'Viên kem sai.')
    kit.integer(t.get('seq'), 0, 1000)
    _vbool(t.get('tare'))
    kit.need(t.get('pack') in (None, *PACKS), 'Cách xếp khay sai.')
    m = t.get('melt')
    if m is not None:
        kit.need(isinstance(m, dict) and set(m) == {'start', 'limit', 'end'}, 'Đồng hồ kem chảy sai.')
        _vnum(m['start'], 0, 10 ** 11)
        kit.integer(m['limit'], 1, 1000)
        if m['end'] is not None:
            _vnum(m['end'], 0, 10 ** 11)
    if t.get('price') is not None:
        kit.integer(t['price'], 0, 10 ** 6)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    kit.need(t.get('choice') in (None, 'decline'), 'Cách giải quyết sai.')
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    _vbool(d['warm_night'])
    till.validate_book(c)
    sh = d['shop']
    kit.need(isinstance(sh, dict), 'Tiệm kem sai.')
    kit.integer(sh['day'], 0, 10 ** 7)
    for k in ('open', 'checked', 'well'):
        _vbool(sh[k])
    fz = d['fz']
    kit.need(isinstance(fz, dict) and set(fz) == {'temp', 'knob', 'lid', 'read'}, 'Tủ kem sai.')
    kit.need(type(fz['temp']) is int and -40 <= fz['temp'] <= 10, 'Tủ kem sai.')
    kit.integer(fz['knob'], 1, 6)
    _vbool(fz['lid'])
    _vbool(fz['read'])
    w = d['well']
    kit.need(isinstance(w, dict) and set(w) == {'n', 'fresh'}, 'Nước ngâm muỗng sai.')
    kit.integer(w['n'], 0, 999)
    _vbool(w['fresh'])
    kit.need(isinstance(d['tubs'], dict) and set(d['tubs']) <= set(FLAVOUR), 'Hộp kem đang múc sai.')
    for tub in d['tubs'].values():
        kit.need(isinstance(tub, dict) and set(tub) in ({'g', 'c', 'day', 'rf'}, {'g', 'c', 'day', 'rf', 'hm'}), 'Hộp kem đang múc sai.')
        kit.integer(tub['g'], 0, TUB_G + ADJ_G * ADJ_MAX * SCOOP_MAX)
        kit.integer(tub['c'], 0, 10000)
        kit.integer(tub['day'], 0, 10 ** 7)
        _vbool(tub['rf'])
        kit.need(tub.get('hm') in (None, 'ok', 'soft', 'icy', 'grainy'), 'Hộp kem đang múc sai.')
    home = d['home']
    kit.need(isinstance(home, list) and len(home) <= HOME_MAX, 'Kem nhà làm sai.')
    for h in home:
        kit.need(isinstance(h, dict) and set(h) == {'f', 'q', 'day', 'c'} and h['f'] in RECIPES and h['q'] in QUALITY
                 and h['q'] != 'burnt', 'Kem nhà làm sai.')
        kit.integer(h['day'], 0, 10 ** 7)
        kit.integer(h['c'], 0, 10000)
    b = d['batch']
    if b is not None:
        kit.need(isinstance(b, dict) and set(b) == {'f', 'step', 'ing', 'temp', 'n', 'churn', 'q', 'cost', 'day'} and b['f'] in RECIPES,
                 'Mẻ kem đang làm sai.')
        r = RECIPES[b['f']]
        kit.integer(b['step'], 0, len(r['steps']) - 1)
        kit.need(isinstance(b['ing'], dict) and all(any(x['id'] == k and v in x['opts'] for x in r['ings']) for k, v in b['ing'].items()),
                 'Mẻ kem đang làm sai.')
        kit.integer(b['temp'], 0, 120)
        kit.integer(b['n'], 0, 20)
        kit.need(b['churn'] is None or b['churn'] in CHURN_MIN, 'Mẻ kem đang làm sai.')
        kit.need(isinstance(b['q'], list) and len(b['q']) <= 10 and set(b['q']) <= set(DEFECT_RANK), 'Mẻ kem đang làm sai.')
        kit.integer(b['cost'], 0, 10000)
        kit.integer(b['day'], 0, 10 ** 7)
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'task', 'codes', 'done'}, 'Học nghề sai.')
    kit.need(lr['task'] is None or (isinstance(lr['task'], str) and len(lr['task']) <= 80), 'Học nghề sai.')
    kit.need(isinstance(lr['codes'], list) and len(lr['codes']) <= len(CATCH) and set(lr['codes']) <= set(CATCH), 'Học nghề sai.')
    _vbool(lr['done'])
    kit.need(d['refrozen'] is None or d['refrozen'] in FLAVOUR, 'Hộp kem hỏng sai.')
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu tiệm kem sai.')
        for kk, v in d[k].items():
            if kk == 'peak':
                kit.need(type(v) is int and -40 <= v <= 10, 'Số liệu tiệm kem sai.')
            else:
                kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='kem_', category='food',
    meta=dict(short='Bán kem', place='Tiệm kem Góc Phượng', tagline='Viên kem tròn, lạnh vừa, đủ gam.', icon='cake',
              color='#e0679a', light='#ffe9f2', weather='Nắng trưa cổng trường', work='Khách gọi kem', station='Tủ kem & cân',
              greeting='Xem nhiệt kế tủ, soi hộp kem, thay nước muỗng rồi mở tiệm. Múc viên nào cũng nhìn cân, múc xong đậy nắp tủ liền tay nhé.',
              caption='Viên kem nào cũng lên cân', map_label='23 · TIỆM KEM GÓC PHƯỢNG'),
    people=PEOPLE,
    staff=[('Hà', 'wash', 'Cháu cô Hiền, rửa muỗng, thay nước nhanh thoăn thoắt.', 78, 90),
           ('Bin', 'call', 'Học sinh lớp 9 làm thêm giờ tan học, giọng to rõ.', 84, 74),
           ('Thư', 'wash', 'Sinh viên làm thêm, kỹ từng cái muỗng.', 70, 94),
           ('Lộc', 'call', 'Quen mặt cả trường, phụ huynh nào cũng chào.', 80, 80)],
    roles={'wash': 'Rửa muỗng, thay nước', 'call': 'Xếp hàng, mời khách'},
    inventory=dict(items=ITEMS, capacity=80),
    prices=PRICES,
    tip=1,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🍨', 'Quầy kem gọn gàng', [('Kem dừa', 'Hộp cô Hiền nấu'), ('Kem dâu', 'Hộp trong tủ'), ('Ốc quế', 'Chồng vỏ bánh'), ('Nhiệt kế', 'Góc tủ kem')],
              ['Xem nhiệt kế, vặn nút tủ', 'Thay nước ngâm muỗng', 'Múc kem lên cân', 'Đậy nắp, đưa kem, thu tiền']),
    stories=[('Kem dừa cô Hiền', ('Đêm nào cô Hiền cũng nạo dừa, nấu nước cốt với đường thốt nốt.',
                                 'Cô bảo kem dừa ngon là nhờ dừa xiêm bến Tre và cái nồi gang ba mươi năm.',
                                 'Sáng ra hộp kem dừa trắng mịn, thơm cả góc phố.')),
             ('Viên kem 65 gam', ('Ông Tám chỉ cho bạn cách múc: kéo muỗng một vòng sâu, vo tròn.',
                                  'Kem cứng thì múc sâu tay, kem mềm thì múc nhẹ.',
                                  'Từ đó viên nào bạn cũng đặt lên cân trước khi đưa khách.')),
             ('Đêm cúp điện', ('Tối đó cả phố cúp điện ba tiếng.',
                               'Cô Hiền phủ chăn bông lên tủ, dặn không ai được mở nắp.',
                               'Sáng ra cô soi từng hộp, hộp nào đông đá lại là bỏ, không tiếc.'))],
    review_asides=['Viên kem tròn, đủ gam, lạnh mịn.', 'Muỗng sạch sẽ, đậy nắp tủ cẩn thận.', 'Nhớ cả lời dặn dị ứng của con tôi.',
                   'Đưa kem nhanh, chưa kịp chảy.'],
    situations=SITUATIONS,
    guide='Xem nhiệt kế → vặn nút số 4 → soi hộp kem → thay nước muỗng → mở tiệm. Mỗi khách: hỏi gọi gì → chọn ly → múc từng viên nhìn cân → '
          'đậy nắp tủ → topping → đưa kem → thu tiền.',
)
