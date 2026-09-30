"""Tiệm Áo Chỉ Mây — a small neighbourhood clothes shop (plugin career `clothing`).

Chị Vy reopened her mother's old tailoring shop ("Tiệm May Bà Tư") as a modern
clothes shop. Bà Tư still sews at the old machine in the room next door. You
work the floor for Vy: the regulars come back day after day and their small
stories go on (Tuấn's first job interview, Bà Năm's daughter's wedding…), and
the shop itself grows (new sign, a mannequin, a real fitting room, a window
full of lights) as you serve more people.

Real work of the day (task kinds):
* fit      find the right size and colour. The customer says "chị mặc M",
           "cao 1m70 nặng 62 ký", "bên kia em mặc M" (our shirts run small),
           "eo 79 phân" or "bé 6 tuổi". Pick from the stock grid (stock per
           size), let them try it in the fitting room if unsure, then bill.
           A wrong size is found at home: they come back to swap next day.
* outfit   advise an outfit for an occasion (ăn cưới, phỏng vấn, đi biển,
           Tết) within a budget. Hits and misses feed the review.
* alter    alterations (lai quần, bóp eo): measure, then sew it yourself (a
           tiny timed task: stop the machine on the mark) or send it next door
           to Bà Tư, who takes 40% of the fee.
* room     the fitting-room queue: give each customer a numbered tag for the
           items they carry, count what comes out. Something missing: check the
           room first, then ask kindly; accusing an innocent customer is rude,
           letting a hidden item walk out is a loss.
* return   returns and exchanges within the policy: tags on, receipt, sale
           items not returnable, 7 days, the shop's own defects always.
           Some customers try to return worn clothes.
* sale     Vy's end-of-season sale sheet: print the sale tags. A tag too low
           loses money, a tag too high brings complaints.
* online   Zalo/Facebook orders: pack the right size and colour, print the
           label (COD = the packed bill), seal it, hand it to the shipper.
* display  steam and dress the mannequin for the week's theme; a good window
           brings patient customers and a few walk-in sales at closing.

Money: every counter job ends at a real till. The bill lists every line (item,
size, colour, unit price), the customer hands over notes (game/careers/till.py),
you count the change from denominations. Wrong change or a wrong total has
natural consequences (a careful customer counts it on the spot, a short change
found at home brings a 1–2★ review and maybe a report, excess change is kept by
some people). "Khỏi thối" tips follow the tip contract (t['tip_given'], 'tip').
Every mistake goes through consequences.slip + react, scaled by severity.
Everything random is seeded from (day, slot) or the task id and stored once.
"""
from __future__ import annotations

import copy

from . import kit, till
from .. import consequences as cq

ID = 'clothing'
PREFIX = 'ao_'

# ---------------------------------------------------------------- the stock
ITEMS = [
    dict(id='tee', name='Áo thun cotton', emoji='👕', group='top', unit='cái', cost=55, start=16),
    dict(id='shirt', name='Sơ mi công sở', emoji='👔', group='top', unit='cái', cost=100, start=12),
    dict(id='jeans', name='Quần jean', emoji='👖', group='bottom', unit='cái', cost=130, start=15),
    dict(id='dress', name='Váy liền', emoji='👗', group='one', unit='cái', cost=115, start=9),
    dict(id='aodai', name='Áo dài cách tân', emoji='🥻', group='one', unit='bộ', cost=190, start=8),
    dict(id='pajama', name='Đồ bộ mặc nhà', emoji='🌙', group='one', unit='bộ', cost=60, start=9),
    dict(id='kids', name='Đồ bộ trẻ em', emoji='🧒', group='kids', unit='bộ', cost=45, start=12),
    dict(id='hat', name='Nón vành', emoji='👒', group='acc', unit='cái', cost=30, start=6),
    dict(id='belt', name='Thắt lưng da', emoji='🪢', group='acc', unit='sợi', cost=35, start=6),
    dict(id='socks', name='Tất cổ ngắn', emoji='🧦', group='acc', unit='đôi', cost=8, start=12),
]
ITEM = {x['id']: x for x in ITEMS}
GROUP = {x['id']: x['group'] for x in ITEMS}
PRICES = {'tee': 115, 'shirt': 220, 'jeans': 280, 'dress': 265, 'aodai': 420, 'pajama': 145, 'kids': 105,
          'hat': 85, 'belt': 95, 'socks': 25}
SIZES = {'tee': ('S', 'M', 'L', 'XL'), 'shirt': ('S', 'M', 'L', 'XL'), 'jeans': ('28', '29', '30', '31', '32'),
         'dress': ('S', 'M', 'L'), 'aodai': ('S', 'M', 'L'), 'pajama': ('M', 'L', 'XL'), 'kids': ('3T', '5T', '7T', '9T'),
         'hat': ('F',), 'belt': ('F',), 'socks': ('F',)}
# New goods fill the sizes that sell most first (M before S before XL…).
FILL = {'tee': ('M', 'L', 'S', 'XL'), 'shirt': ('M', 'L', 'S', 'XL'), 'jeans': ('29', '30', '28', '31', '32'),
        'dress': ('M', 'S', 'L'), 'aodai': ('M', 'S', 'L'), 'pajama': ('L', 'M', 'XL'), 'kids': ('5T', '7T', '3T', '9T'),
        'hat': ('F',), 'belt': ('F',), 'socks': ('F',)}
COLOURS = {'tee': ('trắng', 'đen', 'xanh than', 'be'), 'shirt': ('trắng', 'xanh nhạt', 'hồng phấn', 'đen'),
           'jeans': ('xanh đậm', 'xanh nhạt', 'đen'), 'dress': ('hoa nhí', 'đỏ đô', 'xanh mint', 'trắng'),
           'aodai': ('đỏ', 'vàng', 'trắng', 'xanh ngọc'), 'pajama': ('hồng', 'xanh', 'caro'),
           'kids': ('vàng', 'xanh', 'hồng'), 'hat': ('cói', 'be', 'đen'), 'belt': ('nâu', 'đen'), 'socks': ('trắng', 'đen', 'sọc')}
SWATCH = {'trắng': '#f7f5ef', 'đen': '#2d2a2e', 'xanh than': '#2f3f63', 'be': '#dcc7a4', 'xanh nhạt': '#a9c9e8',
          'hồng phấn': '#f2c1cf', 'xanh đậm': '#2f4f86', 'hoa nhí': '#f3d4dc', 'đỏ đô': '#8e2437', 'xanh mint': '#a6dcc8',
          'đỏ': '#d23b3b', 'vàng': '#f0c23b', 'xanh ngọc': '#3aa6a0', 'hồng': '#f4a7bb', 'xanh': '#6fa3d6',
          'caro': '#c9a27e', 'cói': '#d9bb7c', 'nâu': '#8a5a3b', 'sọc': '#9aa3b5'}
# Size charts (the shop's own labels).
TOP_CHART = (('S', 150, 157, 40, 47), ('M', 158, 164, 48, 55), ('L', 165, 171, 56, 64), ('XL', 172, 180, 65, 75))
JEANS_WAIST = {'28': 71, '29': 74, '30': 76, '31': 79, '32': 81}
KIDS_AGE = {'3T': (2, 3), '5T': (4, 5), '7T': (6, 7), '9T': (8, 9)}
RUNS_SMALL = {'shirt': 1}   # our office shirts are cut slim: one size up from other shops
LETTERS = ('S', 'M', 'L', 'XL')
CAPACITY = 30
MAX_PICKS = 5

# ---------------------------------------------------------------- rules of the house
RETURN_DAYS = 7
HAGGLE_SMALL = 5            # percent Vy allows for a regular ("bớt chút lấy hên")
HAGGLE_BIG = 20
ALTER_FEES = {'hem': 40, 'waist': 60}
TAILOR_SHARE = 40           # percent of the fee Bà Tư takes
TAILOR_TURNS = 2            # beats before Bà Tư hands the piece back
SEW_SECONDS = 4.0           # the needle runs from the start of the seam to the end in this long
SEW_ZONE = (0.70, 0.92)     # stop the machine inside this part of the seam
SEW_ZONE_EASY = (0.55, 0.97)
SALE_UNITS = 3              # how many units a wrong sale tag sells before anyone notices
SALE_PAY = 25
DISPLAY_PAY = 25
SHIP_FEE = 15
DISPLAY_FRESH = 2           # days a good mannequin keeps drawing people in
RETURN_PAY = 10             # Vy's small bonus for handling a return by the book
POLICY = ['Đổi trả trong 7 ngày, đồ còn tem mác, chưa mặc.',
          'Có hóa đơn thì hoàn tiền; mất hóa đơn thì chỉ đổi sang món khác.',
          'Hàng sale không đổi trả (hóa đơn có đóng dấu SALE).',
          'Lỗi của tiệm (bung chỉ, lỗi vải): luôn đổi hoặc hoàn tiền, kể cả đã giặt.']

OCCASIONS = {
    'wedding': dict(name='Đi ăn cưới', emoji='💒', mains=(('dress',), ('aodai',), ('shirt', 'jeans')),
                    bad=('trắng', 'đen'), bad_on=('one',), colours={}, need=(), plus=('belt',), odd=('pajama', 'kids', 'hat'),
                    tips=['Váy, áo dài hoặc sơ mi với quần tối màu đều lịch sự.', 'Không mặc váy trắng (trùng cô dâu) hay đồ đen.',
                          'Thắt lưng da giúp bộ đồ gọn gàng hơn.']),
    'interview': dict(name='Đi phỏng vấn', emoji='💼', mains=(('shirt', 'jeans'),), bad=(), bad_on=(),
                      colours={'shirt': ('trắng', 'xanh nhạt'), 'jeans': ('xanh đậm', 'đen')}, need=(), plus=('belt',),
                      odd=('hat', 'pajama', 'kids', 'aodai'),
                      tips=['Sơ mi sáng màu (trắng, xanh nhạt) với quần tối màu.', 'Thêm thắt lưng cho gọn gàng.',
                            'Không đội nón, không đồ quá sặc sỡ.']),
    'beach': dict(name='Đi biển', emoji='🏖️', mains=(('dress',), ('tee', 'jeans')), bad=(), bad_on=(), colours={},
                  need=('hat',), plus=('hat',), odd=('aodai', 'shirt', 'belt', 'pajama'),
                  tips=['Váy liền hoặc áo thun cho mát.', 'Phải có nón vành che nắng.', 'Sơ mi, áo dài để ở nhà.']),
    'tet': dict(name='Du xuân ngày Tết', emoji='🧧', mains=(('aodai',), ('dress',)), bad=('đen', 'trắng'), bad_on=('one', 'top'),
                colours={'aodai': ('đỏ', 'vàng'), 'dress': ('đỏ đô', 'hoa nhí')}, need=(), plus=('hat',), odd=('pajama',),
                tips=['Áo dài đỏ hoặc vàng là đẹp nhất ngày Tết.', 'Tết kiêng đồ đen, đồ trắng.', 'Nón vành đi chụp ảnh xuân rất hợp.']),
}
KIND_NAMES = {'fit': 'Tìm size', 'outfit': 'Phối đồ', 'alter': 'Sửa đồ', 'room': 'Phòng thử', 'return': 'Đổi trả',
              'sale': 'Tem sale', 'online': 'Đơn online', 'display': 'Ma-nơ-canh'}
KINDS = tuple(KIND_NAMES)

# ---------------------------------------------------------------- people
PEOPLE = [
    ('Chị Vy', 'Chủ tiệm', 'Mở lại tiệm may của mẹ thành tiệm áo xinh, mê phối đồ, nói nhanh như gió.', 'bossy'),
    ('Chị Diễm', 'Nhân viên văn phòng', 'Khó tính, soi từng đường chỉ, nhưng mặc vừa ý là quay lại liền.', 'picky'),
    ('Tuấn', 'Sinh viên năm cuối', 'Ví mỏng, sắp đi phỏng vấn việc đầu tiên, hỏi giá trước khi hỏi size.', 'genz'),
    ('Chị Hằng', 'Mẹ hai bé', 'Lúc nào cũng vội, tay dắt con, tay cầm danh sách đồ cho tụi nhỏ.', 'warm'),
    ('Bà Năm', 'Mẹ cô dâu', 'Lo cưới cho con gái út từ đám hỏi tới tiệc rước dâu, cái gì cũng phải “đẹp mặt”.', 'bossy'),
    ('Dì Sáu', 'Bán nước mía đầu hẻm', 'Trả giá có nghề, mua xong còn xin thêm đôi tất “lấy hên”.', 'sour'),
    ('Chị Kiều', 'Khách sành điệu', 'Đi tiệc liên miên, mua đồ rồi hay “đổi ý” khi đã mặc qua một lần.', 'bossy'),
    ('Bà Tư', 'Thợ may, mẹ chị Vy', 'Ngồi bên máy may cũ ở gian kế bên, mắt còn tinh hơn thước dây.', 'quiet'),
]
VY, DIEM, TUAN, HANG, BA_NAM, DI_SAU, KIEU, BA_TU = range(8)
REGULARS = (DIEM, TUAN, HANG, BA_NAM, DI_SAU, KIEU)
BODY = {DIEM: 'M', TUAN: 'M', HANG: 'M', BA_NAM: 'L', DI_SAU: 'L', KIEU: 'S'}          # tops / dresses
WAIST = {DIEM: '28', TUAN: '29', HANG: '29', BA_NAM: '31', DI_SAU: '31', KIEU: '28'}   # jeans
LOOKS = (
    dict(served=0, name='Tiệm may cũ của Bà Tư', text='Bảng hiệu cũ còn chữ “May đo”, một giá treo và chiếc máy may đạp chân.'),
    dict(served=4, name='Bảng hiệu mới', text='Chị Vy treo bảng “Tiệm Áo Chỉ Mây”, thêm một ma-nơ-canh cạnh cửa.'),
    dict(served=12, name='Phòng thử có rèm', text='Thêm giá treo thứ hai, phòng thử có rèm vải và đèn vàng ấm.'),
    dict(served=24, name='Tiệm áo xinh nhất hẻm', text='Cửa kính trưng đồ, dây đèn nhỏ, chậu cây — khách đi ngang cũng ghé chụp ảnh.'),
)

# ---------------------------------------------------------------- day moods
MODS = [
    dict(id='calm', emoji='🌤️', name='Ngày thường', text='Khách ghé lai rai, có thời gian tư vấn kỹ từng người.', weight=3, min_day=1),
    dict(id='wedding', emoji='💒', name='Mùa cưới', text='Cả hẻm đi ăn cưới: khách hỏi đồ dự tiệc, áo dài, sửa đồ gấp.', weight=2, min_day=2),
    dict(id='payday', emoji='💸', name='Ngày lãnh lương', text='Dân văn phòng tan ca ghé mua sắm, phòng thử kín chỗ.', weight=2, min_day=2),
    dict(id='rain', emoji='🌧️', name='Mưa dầm', text='Ít khách ghé, tin nhắn đặt hàng online nhảy liên tục.', weight=2, min_day=2),
    dict(id='sale', emoji='🏷️', name='Đợt sale cuối mùa', text='Chị Vy xả hàng cuối mùa: dán tem sale cho đúng, khách đổi trả nhiều hơn.', weight=2, min_day=3),
    dict(id='tet', emoji='🧧', name='Gió Tết về', text='Khách tìm áo dài đỏ vàng, mua đồ mới cho con đi chúc Tết.', weight=1, min_day=6),
]
MOD_INDEX = {m['id']: m for m in MODS}
KIND_W = {
    'calm': dict(fit=4, outfit=3, alter=2, room=2, ret=1, online=1, display=1),
    'wedding': dict(fit=2, outfit=5, alter=3, room=1, ret=1, online=1, display=1),
    'payday': dict(fit=4, outfit=2, alter=1, room=3, ret=1, online=1, display=1),
    'rain': dict(fit=2, outfit=1, alter=2, room=0, ret=1, online=5, display=1),
    'sale': dict(fit=3, outfit=1, alter=1, room=2, ret=3, online=1, display=0),
    'tet': dict(fit=3, outfit=4, alter=2, room=1, ret=0, online=1, display=1),
}
FIRST_DAY = ('fit', 'outfit', 'fit', 'alter', 'online', 'fit', 'room', 'outfit', 'fit', 'alter', 'fit', 'outfit')


def _sz(size) -> str:
    """'size M', or 'Free size' for one-size items (never 'size F')."""
    return 'Free size' if size == 'F' else f'size {size}'


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _deck(day: int, mod: str) -> list:
    """Today's kinds, shuffled once per day (slot n takes the n-th card, the deck repeats)."""
    tier = kit.tier(day)
    w = dict(KIND_W[mod])
    if day < 3:
        w['ret'] = 0
    if day < 2:
        w['display'] = 0
    if tier == 0:
        w['room'] = min(w['room'], 1)
    cards = [('return' if k == 'ret' else k) for k, n in w.items() for _ in range(n)]
    rng = kit.rng(ID, 'deck', day)
    rng.shuffle(cards)
    return cards


def _kind(day: int, slot: int) -> str:
    if day == 1:
        return FIRST_DAY[slot % len(FIRST_DAY)]
    mod = mod_of(day)['id']
    if mod == 'sale' and slot == (1 if (day, 0) in STORY else 0):
        return 'sale'
    deck = _deck(day, mod)
    if slot == 0:   # the day opens with a customer at the counter
        return next(k for k in deck if k in ('fit', 'outfit', 'alter', 'room', 'return'))
    return deck[slot % len(deck)]


# ---------------------------------------------------------------- task factory
def _lines_say(lines: list) -> str:
    return ' '.join(x['say'] for x in lines)


def _clue(rng, item: str, size: str, easy: bool) -> tuple[str, str]:
    """(clue kind, what the customer says about the size) that leads to `size` for `item`."""
    if item == 'jeans':
        return 'waist', f'Eo mình {JEANS_WAIST[size]} phân.'
    if item == 'kids':
        lo, hi = KIDS_AGE[size]
        return 'age', f'Cho bé {rng.choice((lo, hi))} tuổi.'
    if item in ('hat', 'belt', 'socks'):
        return 'free', 'Loại free size.'
    if easy:
        kind = 'label'
    elif item in RUNS_SMALL and LETTERS.index(size) >= RUNS_SMALL[item]:
        kind = rng.choice(('label', 'body', 'brand'))
    else:
        kind = rng.choice(('label', 'body', 'body'))
    if kind == 'body':
        row = next(r for r in TOP_CHART if r[0] == size)
        return 'body', f'Mình cao {rng.randint(row[1], row[2])} phân, nặng {rng.randint(row[3], row[4])} ký.'
    if kind == 'brand':
        other = LETTERS[LETTERS.index(size) - RUNS_SMALL[item]]
        return 'brand', f'Bên shop khác mình mặc size {other}.'
    return 'label', f'Mình mặc {_sz(size)}.'


def _pick_size(rng, item: str, npc: int) -> str:
    if item == 'jeans':
        return WAIST.get(npc) or rng.choice(SIZES['jeans'])
    if item in ('hat', 'belt', 'socks'):
        return 'F'
    if item == 'kids':
        return rng.choice(SIZES['kids'])
    base = BODY.get(npc) or rng.choice(('S', 'M', 'L'))
    if base not in SIZES[item]:
        base = SIZES[item][min(len(SIZES[item]) - 1, 1)]
    return base


def _line(rng, item: str, npc: int, easy: bool, size: str | None = None) -> dict:
    size = size or _pick_size(rng, item, npc)
    colour = rng.choice(COLOURS[item])
    clue, said = _clue(rng, item, size, easy)
    return dict(item=item, colour=colour, clue=clue, say=f'{ITEM[item]["name"]} màu {colour}. {said}', _size=size)


FIT_SCRIPTS = [
    # (npc, title, opening, items, min_day)
    (DIEM, 'Sơ mi đi làm', 'Em ơi, chị cần một cái sơ mi mặc đi làm, vải đừng mỏng quá nha.', ('shirt',), 1),
    (TUAN, 'Áo thun đi học', 'Anh ơi… à chị ơi, cho em xem áo thun, loại nào bền mà rẻ ạ?', ('tee',), 1),
    (HANG, 'Đồ bộ cho tụi nhỏ', 'Em ơi lấy giùm chị đồ bộ cho hai đứa nhỏ, lẹ giùm chị nha!', ('kids', 'kids'), 1),
    (DI_SAU, 'Đồ bộ mặc nhà', 'Con ơi, dì lấy bộ đồ bộ mặc bán nước cho mát.', ('pajama',), 1),
    (DIEM, 'Quần jean cuối tuần', 'Cuối tuần chị đi cà phê, lấy giùm chị cái quần jean.', ('jeans',), 1),
    (KIEU, 'Váy đi tiệc tối', 'Tối nay chị có tiệc, cần cái váy liền xinh xinh.', ('dress',), 2),
    (HANG, 'Áo thun cho chồng', 'Ông xã chị cần áo thun mặc nhà, em lấy giùm.', ('tee',), 1),
    (TUAN, 'Quần jean đi thực tập', 'Em sắp đi thực tập, cần cái quần jean nhìn cho đàng hoàng.', ('jeans', 'belt'), 2),
    (BA_NAM, 'Áo dài đi chùa', 'Mùng một bà đi chùa, lấy cho bà cái áo dài.', ('aodai',), 3),
    (DI_SAU, 'Tất với nón', 'Dì cần cái nón che nắng với đôi tất, bán rẻ rẻ cho dì nha.', ('hat', 'socks'), 1),
]
OUTFIT_SCRIPTS = [
    # (npc, occasion, title, opening, budget, min_day)
    (TUAN, 'interview', 'Bộ đồ đi phỏng vấn', 'Tuần sau em phỏng vấn công ty đầu tiên, chị phối giùm em một bộ, em có ít tiền thôi.', 560, 1),
    (DIEM, 'wedding', 'Đồ đi đám cưới đồng nghiệp', 'Thứ bảy chị đi đám cưới đồng nghiệp, chọn giúp chị một bộ cho lịch sự.', 520, 1),
    (HANG, 'beach', 'Cả nhà đi biển', 'Nhà chị đi biển Vũng Tàu cuối tuần, chọn cho chị một bộ mát mát.', 400, 1),
    (KIEU, 'wedding', 'Tiệc cưới bạn thân', 'Bạn thân chị cưới, chị phải đẹp nhưng không được lấn cô dâu nha.', 560, 2),
    (BA_NAM, 'tet', 'Áo mới du xuân', 'Tết này bà muốn một bộ thật tươi để đi chúc Tết họ hàng.', 600, 2),
    (DIEM, 'interview', 'Phỏng vấn chỗ làm mới', 'Chị đang đổi việc, mai đi phỏng vấn, chọn giùm chị bộ nào nhìn chuyên nghiệp.', 600, 3),
    (TUAN, 'beach', 'Đi biển với lớp', 'Lớp em đi biển chia tay, em cần một bộ mặc chụp ảnh cho đẹp.', 460, 2),
    (DI_SAU, 'tet', 'Đồ Tết cho dì', 'Tết này dì cũng phải có bộ mới chứ con, lựa giùm dì.', 480, 2),
]
ALTER_SCRIPTS = [
    # (npc, garment, job, title, opening, min_day)
    (TUAN, 'jeans', 'hem', 'Lai quần jean', 'Quần em mua dài quá, chị lai giùm em chấm mắt cá nha.', 1),
    (DIEM, 'dress', 'waist', 'Bóp eo váy', 'Váy này rộng eo quá, bóp giùm chị cho ôm vừa.', 1),
    (HANG, 'jeans', 'hem', 'Lai quần cho ông xã', 'Quần ông xã chị dài lết đất, lai giùm chị nha.', 1),
    (BA_NAM, 'aodai', 'waist', 'Bóp eo áo dài', 'Áo dài này bà mặc hơi rộng eo, bóp lại cho bà mặc đi đám.', 2),
    (KIEU, 'dress', 'waist', 'Váy tiệc bóp eo gấp', 'Tối nay chị mặc rồi, bóp eo giùm chị gấp nha em.', 2),
]
RETURN_CASES = {
    # case: (npc, item, title, opening, want)
    'size_swap': [(DIEM, 'shirt', 'Đổi size sơ mi', 'Hôm qua chị lấy sơ mi mà mặc hơi chật, đổi giùm chị size lớn hơn nha.', 'exchange'),
                  (TUAN, 'tee', 'Đổi size áo thun', 'Em lấy áo thun hơi rộng, còn đổi size được không chị?', 'exchange')],
    'defect': [(HANG, 'kids', 'Đồ bộ bung chỉ', 'Đồ bộ của bé mới giặt một lần mà bung chỉ nách rồi em ơi.', 'refund'),
               (DIEM, 'dress', 'Váy tuột đường may', 'Váy chị mặc lần đầu mà đường may sau lưng tuột rồi.', 'refund')],
    'worn': [(KIEU, 'dress', 'Trả váy dự tiệc', 'Váy này chị không ưng, trả lại lấy tiền nha. Chị chưa mặc đâu.', 'refund'),
             (KIEU, 'aodai', 'Trả áo dài', 'Áo dài không hợp dáng chị, em hoàn tiền giùm nha.', 'refund')],
    'sale': [(DI_SAU, 'pajama', 'Trả đồ bộ đợt sale', 'Bộ này dì mua đợt sale mà về mặc không ưng, trả lại dì lấy tiền.', 'refund')],
    'late': [(BA_NAM, 'shirt', 'Trả sơ mi mua lâu', 'Bà mua cái sơ mi này cho ông nhà mà ổng không mặc, trả lại được hông con?', 'refund')],
    'no_receipt': [(TUAN, 'jeans', 'Đổi quần mất hóa đơn', 'Em lỡ làm mất hóa đơn rồi, quần còn tem nè, em đổi size nhỏ hơn được không chị?', 'exchange')],
}
CASE_ORDER = ('size_swap', 'defect', 'worn', 'size_swap', 'sale', 'late', 'no_receipt', 'worn')
ONLINE_SCRIPTS = [
    # (npc, channel, title, opening, lines [(item, qty)], pay)
    (DIEM, 'zalo', 'Đơn Zalo của chị Diễm', 'Em ơi chị đặt qua Zalo nha, gửi về công ty giùm chị.', (('shirt', 1), ('belt', 1)), 'paid'),
    (HANG, 'facebook', 'Đơn Facebook cho tụi nhỏ', 'Chị đặt trên trang Facebook của tiệm, ship về nhà, nhận hàng chị trả tiền.', (('kids', 2),), 'cod'),
    (KIEU, 'facebook', 'Đơn váy tiệc qua Facebook', 'Chị chuyển khoản rồi, gửi hỏa tốc giùm chị nha.', (('dress', 1), ('hat', 1)), 'paid'),
    (TUAN, 'zalo', 'Đơn Zalo của Tuấn', 'Chị ơi em đặt qua Zalo, ship tới ký túc xá, em trả tiền khi nhận.', (('tee', 2),), 'cod'),
    (BA_NAM, 'zalo', 'Đơn Zalo nhà cô dâu', 'Bà nhờ đứa cháu nhắn Zalo đặt đồ cho cả nhà, gửi về giùm bà.', (('shirt', 1), ('jeans', 1)), 'cod'),
]
ADDRESSES = ('Hẻm 7, Phường Mây', 'Chung cư Nắng Sớm, tầng 4', 'Ký túc xá Đại học Mây, phòng 312', 'Số 18 đường Chỉ Hồng',
             'Công ty Mây Tre Xanh, lễ tân tầng 2')

# Story days: the regulars' small stories go on (deterministic by day).
STORY = {
    (2, 0): dict(kind='outfit', npc=TUAN, occasion='interview', budget=560, title='Buổi phỏng vấn đầu tiên',
                 opening='Chị ơi, em có hẹn phỏng vấn việc đầu tiên rồi! Em chưa có bộ nào ra hồn, chị phối giùm em nha.'),
    (3, 0): dict(kind='outfit', npc=BA_NAM, occasion='wedding', budget=700, title='Đám hỏi con gái út',
                 opening='Tuần sau đám hỏi con Út nhà bà. Bà cần một bộ thật đẹp mặt để đón nhà trai.'),
    (5, 0): dict(kind='fit', npc=TUAN, items=('shirt', 'shirt'), title='Tuấn đậu phỏng vấn!',
                 opening='Chị ơi em đậu rồi! Tuần sau đi làm, em mua thêm hai cái sơ mi mặc thay đổi nha.'),
    (7, 0): dict(kind='alter', npc=BA_NAM, garment='aodai', job='waist', title='Áo dài cho ngày cưới',
                 opening='Mai rước dâu rồi mà áo dài bà mặc rộng eo, bóp giùm bà kịp nha con.'),
    (9, 0): dict(kind='outfit', npc=BA_NAM, occasion='wedding', budget=640, title='Đồ cho đứa cháu đi đám cưới',
                 opening='Cảm ơn tiệm, đám cưới con Út đẹp lắm! Giờ bà dẫn đứa cháu tới, chọn giùm nó bộ đi đám cưới bạn.'),
}


def make_task(day: int, slot: int, serial: int) -> dict:
    rng = kit.rng(ID, day, slot)
    st = STORY.get((day, slot))
    if st:
        return _story(day, slot, serial, rng, st)
    kind = _kind(day, slot)
    return BUILD[kind](day, slot, serial, rng)


def _story(day, slot, serial, rng, st: dict) -> dict:
    if st['kind'] == 'outfit':
        return _outfit_task(day, slot, serial, rng, (st['npc'], st['occasion'], st['title'], st['opening'], st['budget'], 1))
    if st['kind'] == 'fit':
        return _fit_task(day, slot, serial, rng, (st['npc'], st['title'], st['opening'], st['items'], 1))
    return _alter_task(day, slot, serial, rng, (st['npc'], st['garment'], st['job'], st['title'], st['opening'], 1))


def _common(**kw) -> dict:
    base = dict(stage='pick', picks=[], tried=[], bill=None, cash=None, haggle=None, result=None, gen=1)
    base.update(kw)
    return base


def _pool(rows, day, col):
    pool = [r for r in rows if r[col] <= day]
    return pool or rows[:1]


def _make_fit(day, slot, serial, rng):
    pool = _pool(FIT_SCRIPTS, day, 4)
    return _fit_task(day, slot, serial, rng, pool[(day * 5 + slot * 3 + rng.randrange(len(pool))) % len(pool)])


def _fit_task(day, slot, serial, rng, script):
    npc, title, opening, items, _ = script
    easy = kit.tier(day) == 0
    lines = []
    used = set()
    for item in items:
        size = None
        if item == 'kids' and used:
            size = rng.choice([s for s in SIZES['kids'] if s not in used])
        ln = _line(rng, item, npc, easy, size=size)
        used.add(ln['_size'])
        lines.append(ln)
    needs = dict(lines=lines, note=_lines_say(lines), haggle=npc == DI_SAU)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='fit', needs=needs, **_common())


def _make_outfit(day, slot, serial, rng):
    pool = _pool(OUTFIT_SCRIPTS, day, 5)
    mod = mod_of(day)['id'] if day > 1 else 'calm'
    want = {'wedding': 'wedding', 'tet': 'tet'}.get(mod)
    if want and rng.random() < 0.7:
        pool = [r for r in pool if r[1] == want] or pool
    return _outfit_task(day, slot, serial, rng, pool[(day * 7 + slot + rng.randrange(len(pool))) % len(pool)])


def _outfit_task(day, slot, serial, rng, script):
    npc, occ, title, opening, budget, _ = script
    top = BODY.get(npc, 'M')
    waist = WAIST.get(npc, '29')
    o = OCCASIONS[occ]
    sizes = f'Áo {top}, quần jean {waist}' + (f', váy/áo dài {top if top in SIZES["dress"] else "L"}' if occ != 'interview' else '')
    needs = dict(occasion=occ, budget=budget, top=top, waist=waist,
                 note=f'{o["emoji"]} {o["name"]} · ngân sách {budget} xu · {sizes}.', haggle=npc == DI_SAU)
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='outfit', needs=needs, **_common())


def _make_alter(day, slot, serial, rng):
    pool = _pool(ALTER_SCRIPTS, day, 5)
    return _alter_task(day, slot, serial, rng, pool[(day * 3 + slot * 2 + rng.randrange(len(pool))) % len(pool)])


def _alter_task(day, slot, serial, rng, script):
    npc, garment, job, title, opening, _ = script
    cm = rng.randint(3, 6) if job == 'hem' else rng.randint(2, 4)
    fee = ALTER_FEES[job]
    needs = dict(garment=garment, job=job, fee=fee, _cm=cm,
                 note=('Lai quần: khách muốn gấu quần chấm mắt cá chân.' if job == 'hem' else 'Bóp eo: khách muốn vừa ôm, vẫn thở được.'))
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='alter', needs=needs,
                         alt=dict(measured=False, cm=None, mode=None, cut=None, start=None, seam=None, sent=None),
                         **_common(stage='measure'))


def _make_room(day, slot, serial, rng):
    easy = kit.tier(day) == 0
    who = [DIEM, KIEU, TUAN, HANG, DI_SAU, BA_NAM]
    rng.shuffle(who)
    queue = []
    outs = ['ok', 'left', 'hidden'] if not easy else ['ok', 'left', 'ok']
    rng.shuffle(outs)
    for i in range(3):
        what = rng.choice(('tee', 'shirt', 'dress', 'jeans'))
        queue.append(dict(npc=who[i], items=rng.randint(2, 4), _out=outs[i], _what=what))
    buyer = queue[-1]['npc']
    item = rng.choice(('tee', 'shirt', 'dress', 'jeans'))
    size = _pick_size(rng, item, buyer)
    colour = rng.choice(COLOURS[item])
    buy = dict(item=item, colour=colour, size=size,
               say=f'{ITEM[item]["name"]} {_sz(size)} màu {colour} này vừa nè, tính tiền giùm chị.')
    needs = dict(queue=queue, buy=buy, note='Ba khách xếp hàng vào phòng thử. Đưa thẻ số theo số món khách cầm vào, đếm lại lúc ra.')
    title = 'Phòng thử giờ tan tầm'
    opening = 'Phòng thử có ba người chờ, em trông giùm chị nha! Thẻ số treo ở móc cạnh rèm đó.'
    return kit.base_task(ID, day, slot, serial, buyer, title, opening, kind='room', needs=needs,
                         room=dict(i=0, tags={}, outs={}, checked=[], res={}), **_common(stage='room'))


def _make_return(day, slot, serial, rng):
    case = CASE_ORDER[(day * 3 + slot + rng.randrange(len(CASE_ORDER))) % len(CASE_ORDER)]
    if kit.tier(day) == 0 and case in ('worn', 'late', 'sale'):
        case = 'size_swap'
    npc, item, title, opening, want = rng.choice(RETURN_CASES[case])
    size = _pick_size(rng, item, npc)
    colour = rng.choice(COLOURS[item])
    sizes = SIZES[item]
    new_size = None
    if want == 'exchange':
        i = sizes.index(size)
        new_size = sizes[i + 1] if case == 'size_swap' and npc == DIEM and i + 1 < len(sizes) else sizes[i - 1] if i > 0 else sizes[min(i + 1, len(sizes) - 1)]
    days_ago = {'late': rng.randint(10, 16)}.get(case, rng.randint(1, 4))
    price = PRICES[item] * (70 if case == 'sale' else 100) // 100
    needs = dict(item=item, size=size, colour=colour, price=price, days_ago=days_ago, want=want, new_size=new_size,
                 note=f'{ITEM[item]["name"]} {_sz(size)}, màu {colour}, mua {days_ago} ngày trước, giá {price} xu.',
                 _case=case, _tag=case not in ('worn',), _receipt=case != 'no_receipt', _sale=case == 'sale',
                 _worn=case == 'worn', _defect=case == 'defect')
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='return', needs=needs,
                         ret=dict(seen=[], choice=None, tone=None, new_size=None), **_common(stage='check'))


def _make_sale(day, slot, serial, rng):
    items = ['tee', 'shirt', 'jeans', 'dress', 'pajama', 'hat']
    rng.shuffle(items)
    pcts = [rng.choice((10, 20, 30)), rng.choice((20, 30, 40)), rng.choice((30, 50))]
    lines = [dict(item=items[i], pct=pcts[i]) for i in range(3)]
    needs = dict(lines=lines, note='Tờ sale của chị Vy: ' + ', '.join(f'{ITEM[x["item"]]["name"]} giảm {x["pct"]}%' for x in lines) + '.')
    opening = 'Đợt sale cuối mùa nè! Em in tem giá sale cho ba món này giùm chị nha, tính cho đúng, làm tròn xuống.'
    return kit.base_task(ID, day, slot, serial, VY, 'Dán tem sale cuối mùa', opening, kind='sale', needs=needs,
                         sale=dict(base={}, options=[], tags={}), **_common(stage='tag'))


def _make_online(day, slot, serial, rng):
    npc, channel, title, opening, rows, pay = ONLINE_SCRIPTS[(day * 2 + slot + rng.randrange(len(ONLINE_SCRIPTS))) % len(ONLINE_SCRIPTS)]
    lines = []
    for item, qty in rows:
        for _ in range(qty):
            size = _pick_size(rng, item, npc) if item != 'kids' else rng.choice(SIZES['kids'])
            lines.append(dict(item=item, size=size, colour=rng.choice(COLOURS[item])))
    address = ADDRESSES[rng.randrange(len(ADDRESSES))]
    needs = dict(channel=channel, lines=lines, pay=pay, address=address,
                 note=('Đã chuyển khoản trước.' if pay == 'paid' else 'Thu hộ (COD) khi giao.') + f' Giao tới: {address}.')
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='online', needs=needs,
                         parcel=dict(items=[], label=None, sealed=False), **_common(stage='pack'))


def _make_display(day, slot, serial, rng):
    mod = mod_of(day)['id']
    theme = {'wedding': 'wedding', 'tet': 'tet', 'payday': 'interview'}.get(mod) or rng.choice(('wedding', 'interview', 'beach', 'tet'))
    o = OCCASIONS[theme]
    needs = dict(theme=theme, note=f'Chủ đề tuần này: {o["emoji"]} {o["name"]}. Hấp phẳng từng món rồi mặc cho ma-nơ-canh.')
    opening = f'Tuần này mình trưng chủ đề “{o["name"]}” nha em. Ủi hơi cho phẳng rồi mặc cho ma-nơ-canh cạnh cửa giùm chị.'
    return kit.base_task(ID, day, slot, serial, VY, 'Thay đồ ma-nơ-canh', opening, kind='display', needs=needs,
                         disp=dict(pieces=[], steamed=[]), **_common(stage='dress'))


BUILD = {'fit': _make_fit, 'outfit': _make_outfit, 'alter': _make_alter, 'room': _make_room, 'return': _make_return,
         'sale': _make_sale, 'online': _make_online, 'display': _make_display}
FIXED = ('needs',)


# ---------------------------------------------------------------- data
STAT_KEYS = ('sales', 'customers', 'swaps', 'room_saved', 'room_lost', 'frauds', 'refunds', 'walkins', 'haggle_off', 'accused')


def initial() -> dict:
    d = dict(grid={})
    _extend(d)
    for it in ITEMS:
        row = {s: 0 for s in SIZES[it['id']]}
        _fill(row, it['id'], it['start'])
        d['grid'][it['id']] = row
    return d


def _extend(d: dict) -> dict:
    """Fields added over time; old saves get them here (setdefault keeps what is there)."""
    d.setdefault('grid', {})
    d.setdefault('swaps', [])
    d.setdefault('book', {})
    d.setdefault('sale', None)
    d.setdefault('display', None)
    d.setdefault('intro', False)
    d.setdefault('notes', [])
    d.setdefault('seq', 0)
    d.setdefault('day_sales', 0)
    st = d.setdefault('stats', {})
    for k in STAT_KEYS:
        st.setdefault(k, 0)
    return d


def _data(c: dict) -> dict:
    return _extend(kit.data(c))


def _weight(item: str, size: str) -> int:
    """Shelf share of a size: the sizes that sell most get more pieces."""
    order = FILL[item]
    return len(order) - order.index(size) + 1


def _fill(row: dict, item: str, n: int) -> None:
    for _ in range(max(0, n)):
        order = FILL[item]
        s = min(order, key=lambda z: ((row[z] + 1) / _weight(item, z), order.index(z)))
        row[s] += 1


def _drain(row: dict, item: str, n: int) -> None:
    for _ in range(max(0, n)):
        order = FILL[item]
        s = max(order, key=lambda z: (row[z] / _weight(item, z), -order.index(z)))
        if row[s] <= 0:
            return
        row[s] -= 1


def _sync(c: dict) -> None:
    """Keep the per-size grid equal to the shared stock count of each item (goods that
    arrived fill the sizes that sell most; goods lost elsewhere leave the fullest size)."""
    d = _data(c)
    g = d['grid']
    for it in ITEMS:
        sizes = SIZES[it['id']]
        row = g.get(it['id'])
        if not isinstance(row, dict):
            row = g[it['id']] = {}
        for s in list(row):
            if s not in sizes:
                row.pop(s)
        for s in sizes:
            if type(row.get(s)) is not int or row[s] < 0:
                row[s] = 0
        have = kit.stock(c, it['id'])
        cur = sum(row.values())
        if cur < have:
            _fill(row, it['id'], have - cur)
        elif cur > have:
            _drain(row, it['id'], cur - have)


def _open(t: dict) -> bool:
    return t.get('career') == ID and t['status'] not in ('completed', 'referred', 'cancelled')


def _held(c: dict, item: str, size: str, but: dict | None = None) -> int:
    """Units already on another open bill or parcel."""
    n = 0
    for t in c['tasks']:
        if not _open(t) or (but is not None and t['id'] == but['id']):
            continue
        for p in t.get('picks') or []:
            if p['item'] == item and p['size'] == size:
                n += 1
        for p in (t.get('parcel') or {}).get('items') or []:
            if p['item'] == item and p['size'] == size:
                n += 1
    return n


def _free(c: dict, item: str, size: str, t: dict | None = None) -> int:
    return _data(c)['grid'].get(item, {}).get(size, 0) - _held(c, item, size, t)


def _sell(c: dict, item: str, size: str) -> int:
    d = _data(c)
    row = d['grid'][item]
    kit.need(row.get(size, 0) > 0, f'Kệ vừa hết {ITEM[item]["name"].lower()} {_sz(size)}.')
    cost = kit.take(c, item, 1)
    row[size] -= 1
    c['life']['consumed_cost'] += cost
    return cost


def _restock_one(c: dict, item: str, size: str) -> None:
    """A returned piece that can be sold again goes back on the rack in its size."""
    if kit.stock(c, item) >= CAPACITY:
        return
    kit.add_lot(c, item, 1, ITEM[item]['cost'], 999, 'return')
    _data(c)['grid'][item][size] = _data(c)['grid'][item].get(size, 0) + 1


def _price(c: dict, item: str) -> int:
    d = _data(c)
    sale = d.get('sale')
    if isinstance(sale, dict) and sale.get('day') == c['day'] and item in sale.get('tags', {}):
        return sale['tags'][item]
    return kit.price(c, item, PRICES[item])


def _npc_index(t: dict) -> int:
    return int(t['npc'].rsplit('_', 1)[1]) - 1


def _who(t: dict) -> str:
    return PEOPLE[_npc_index(t)][0]


def _note(c: dict, text: str) -> None:
    d = _data(c)
    d['notes'] = (d['notes'] + [dict(day=c['day'], text=text[:200])])[-12:]


def _look(c: dict) -> int:
    served = int(c.get('metrics', {}).get('served', 0))
    return max(i for i, x in enumerate(LOOKS) if served >= x['served'])


# ---------------------------------------------------------------- engine hooks
def on_task(s: dict, c: dict, t: dict) -> None:
    if t.get('career') != ID:
        return
    if t['kind'] == 'sale' and not t['sale']['base']:
        base, options = {}, []
        for ln in t['needs']['lines']:
            price = kit.price(c, ln['item'], PRICES[ln['item']])
            base[ln['item']] = price
            options.append(_sale_options(price, ln['pct']))
        t['sale']['base'] = base
        t['sale']['options'] = options
    disp = _data(c).get('display')
    if isinstance(disp, dict) and disp.get('score', 0) >= 4 and 0 <= c['day'] - disp.get('day', -99) <= DISPLAY_FRESH and 'patience' in t:
        t['patience'] = min(100, t['patience'] + 10)


def _sale_options(price: int, pct: int) -> list:
    right = price * (100 - pct) // 100
    out = [right]
    for v in (price * pct // 100, price - pct, price * (100 - pct - 10) // 100, price * (100 - pct + 10) // 100, right + 10, right - 10):
        if v > 0 and v not in out and v != price:
            out.append(v)
        if len(out) == 4:
            break
    return sorted(out)


def on_stock(s: dict, c: dict, action: str) -> None:
    _sync(c)


def on_start(s: dict, c: dict) -> None:
    _sync(c)
    d = _data(c)
    d['day_sales'] = 0
    d['swaps'] = [x for x in d['swaps'] if x['day'] >= c['day']]


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    k = t['kind']
    if k == 'fit':
        return n['note']
    if k == 'outfit':
        o = OCCASIONS[n['occasion']]
        return f'{o["emoji"]} {o["name"]}. Ngân sách tối đa {n["budget"]} xu. Áo size {n["top"]}, quần jean {n["waist"]}.'
    if k == 'alter':
        return n['note'] + f' Công sửa {n["fee"]} xu.'
    if k == 'room':
        return n['note']
    if k == 'return':
        return n['note'] + (' Khách muốn đổi sang size ' + n['new_size'] + '.' if n['want'] == 'exchange' else ' Khách muốn trả lấy tiền.')
    if k == 'sale':
        return n['note']
    if k == 'online':
        return 'Đơn: ' + ', '.join(f'{ITEM[x["item"]]["name"]} {_sz(x["size"])} màu {x["colour"]}' for x in n['lines']) + '. ' + n['note']
    return n['note']


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    _sync(c)
    if name == 'ao_intro':
        d['intro'] = bool(p.get('seen', True))
        return dict(message='Chị Vy cười: “Vậy là em nắm việc rồi đó, vô ca thôi!”')
    if name == 'ao_swap':
        return _swap(s, c, p)
    if name == 'ao_short':   # khách đưa thiếu tiền (game/short_pay.py via the till)
        t = kit.task(c, p)
        kit.need(t['career'] == ID and t.get('cash'), 'Khách chưa đưa tiền mặt.')
        return till.short_action(s, c, t, t['cash'], p, _who(t))
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm áo.')
    kit.need(t['known'], 'Chào khách và nghe khách nói trước nhé (bấm “Nghe khách”).')
    kit.need(t['stage'] != 'done', 'Việc này đã xong rồi.')
    k = t['kind']
    if k in ('fit', 'outfit'):
        return _counter(s, c, t, name, p)
    if k == 'alter':
        return _alter(s, c, t, name, p)
    if k == 'room':
        return _room(s, c, t, name, p)
    if k == 'return':
        return _return(s, c, t, name, p)
    if k == 'sale':
        return _sale(s, c, t, name, p)
    if k == 'online':
        return _online(s, c, t, name, p)
    return _display(s, c, t, name, p)


def _item_arg(p: dict) -> str:
    return kit.one_of(p.get('item'), ITEM, 'Tiệm không có món này.')


def _size_arg(item: str, value) -> str:
    return kit.one_of(value, SIZES[item], 'Món này không có size đó.')


def _colour_arg(item: str, value) -> str:
    return kit.one_of(value, COLOURS[item], 'Món này không có màu đó.')


# ---- the counter: picking, fitting room, bill, till (fit / outfit / room buyer / alter)
def _counter(s, c, t, name, p):
    if name in ('ao_pick', 'ao_unpick', 'ao_try'):
        kit.need(t['stage'] == 'pick', 'Bill đã chốt. Mở lại bill nếu muốn đổi món.')
        kit.start_work(t)
    if name == 'ao_pick':
        item = _item_arg(p)
        size = _size_arg(item, p.get('size'))
        colour = _colour_arg(item, p.get('colour'))
        kit.need(len(t['picks']) < MAX_PICKS, 'Quầy đầy rồi, bớt món ra trước nhé.')
        free = _free(c, item, size, t) - sum(1 for x in t['picks'] if x['item'] == item and x['size'] == size)
        kit.need(free > 0, f'Giá treo hết {ITEM[item]["name"].lower()} {_sz(size)}. Nhập thêm hoặc chọn size khác.')
        t['picks'].append(dict(item=item, size=size, colour=colour))
        t['tried'].append(None)
        return dict(message=f'Lấy ra quầy: {ITEM[item]["emoji"]} {ITEM[item]["name"]} {_sz(size)}, màu {colour} · {_price(c, item)} xu.')
    if name == 'ao_unpick':
        i = kit.integer(p.get('index'), 0, len(t['picks']) - 1) if t['picks'] else kit.need(False, 'Quầy đang trống.')
        x = t['picks'].pop(i)
        t['tried'].pop(i)
        return dict(message=f'Đã treo lại {ITEM[x["item"]]["name"].lower()} {_sz(x["size"])}.')
    if name == 'ao_try':
        kit.need(t['picks'], 'Lấy đồ ra trước rồi mới mời khách thử.')
        i = kit.integer(p.get('index'), 0, len(t['picks']) - 1)
        x = t['picks'][i]
        kit.need(x['item'] not in ('hat', 'belt', 'socks'), 'Phụ kiện free size, khỏi cần thử.')
        kit.need(t['tried'][i] is None, 'Khách thử món này rồi.')
        right = _want_size(t, x)
        verdict = 'ok' if right is None or x['size'] == right else ('small' if _smaller(x['item'], x['size'], right) else 'big')
        t['tried'][i] = verdict
        t['patience'] = max(25, t.get('patience', 100) - 6)
        kit.metric(c, 'ao_tries')
        who = _who(t)
        if verdict == 'ok':
            return dict(message=f'{who} bước ra khỏi phòng thử, xoay một vòng: “Vừa khít luôn!”')
        return dict(message=f'{who} ló đầu ra khỏi rèm: “{"Chật quá, lấy lớn hơn giùm" if verdict == "small" else "Rộng thùng thình, lấy nhỏ hơn giùm"} nha.” Đổi size rồi mời thử lại.')
    if name == 'ao_bill':
        return _lock_bill(s, c, t)
    if name == 'ao_unbill':
        kit.need(t['stage'] == 'pay' and (t['cash'] is None or t['cash']['outcome'] is None), 'Chưa có bill để mở lại.')
        t['stage'] = 'ready' if t['kind'] == 'alter' else 'pick'
        t['bill'] = None
        t['cash'] = None
        t['haggle'] = None
        return dict(message='Đã mở lại bill.')
    if name == 'ao_haggle':
        return _haggle(s, c, t, p)
    if name == 'ao_pay':
        kit.confirm(p, 'Xác nhận giao đồ và tiền thối cho khách.')
        return _pay(s, c, t, p)
    raise kit.eng().GameError('Thao tác ở quầy tiệm áo không hợp lệ.')


def _smaller(item: str, size: str, right: str) -> bool:
    sizes = SIZES[item]
    return sizes.index(size) < sizes.index(right)


def _want_size(t: dict, x: dict) -> str | None:
    """The size that fits this customer for this pick (None when anything goes)."""
    item = x['item']
    if item in ('hat', 'belt', 'socks'):
        return None
    n = t['needs']
    if t['kind'] == 'fit':
        for ln in n['lines']:
            if ln['item'] == item and ln['colour'] == x['colour']:
                return ln['_size']
        ln = next((ln for ln in n['lines'] if ln['item'] == item), None)
        return ln['_size'] if ln else None
    if t['kind'] == 'room':
        return n['buy']['size'] if item == n['buy']['item'] else None
    if t['kind'] == 'outfit':
        if item == 'jeans':
            return n['waist']
        if item == 'kids':
            return None
        top = n['top']
        sizes = SIZES[item]
        return top if top in sizes else sizes[-1] if LETTERS.index(top) > LETTERS.index(sizes[-1]) else sizes[0]
    return None


def _pairing(t: dict) -> tuple[list, list, list]:
    """Fit/room: match picks to what was asked (item + colour). Returns (missing lines, wrong-colour picks, extra picks)."""
    n = t['needs']
    wanted = list(n['lines']) if t['kind'] == 'fit' else [n['buy']]
    left = list(range(len(t['picks'])))
    missing, wrong = [], []
    for ln in wanted:
        hit = next((i for i in left if t['picks'][i]['item'] == ln['item'] and t['picks'][i]['colour'] == ln['colour']), None)
        if hit is None:
            same = next((i for i in left if t['picks'][i]['item'] == ln['item']), None)
            if same is not None:
                wrong.append((same, ln))
                left.remove(same)
            else:
                missing.append(ln)
        else:
            left.remove(hit)
    return missing, wrong, left


def _is_set(items: list) -> bool:
    return any(GROUP[i] == 'one' for i in items) or (any(GROUP[i] == 'top' for i in items) and any(GROUP[i] == 'bottom' for i in items))


def _lock_bill(s, c, t):
    who = _who(t)
    if t['kind'] == 'alter':
        kit.need(t['stage'] == 'ready', 'Sửa xong đồ rồi mới tính tiền.')
        n = t['needs']
        lines = [dict(label=f'Công {"lai quần" if n["job"] == "hem" else "bóp eo"} ({ITEM[n["garment"]]["name"].lower()})',
                      item=None, size='', colour='', unit=n['fee'], qty=1, amount=n['fee'])]
        return _open_bill(c, t, lines)
    kit.need(t['stage'] == 'pick', 'Bill đã chốt rồi.')
    kit.need(t['picks'], 'Quầy chưa có món nào. Lấy đồ trên giá treo trước nhé.')
    bad = [i for i, v in enumerate(t['tried']) if v in ('small', 'big')]
    kit.need(not bad, f'{who}: “Món này chị thử không vừa mà, đổi size giùm đã.”')
    if t['kind'] in ('fit', 'room'):
        missing, wrong, extra = _pairing(t)
        if wrong:
            i, ln = wrong[0]
            t['mistakes'] += 1
            cq.slip(t, 'wrong_colour', 1, f'Tôi dặn màu {ln["colour"]} mà tiệm lấy màu {t["picks"][i]["colour"]}, may mà tôi nhìn kỹ.', 'lấy sai màu')
            return dict(message=f'{who} nhíu mày: “Chị dặn màu {ln["colour"]} mà em, đây là màu {t["picks"][i]["colour"]}.” Đổi lại đúng màu rồi tính tiền.', refused=True)
        if extra:
            x = t['picks'][extra[0]]
            t['mistakes'] += 1
            cq.slip(t, 'extra', 1, 'Bill có thêm món tôi không lấy, phải nhắc mới bỏ ra.', 'tính dư món')
            return dict(message=f'{who}: “Ủa, {ITEM[x["item"]]["name"].lower()} này đâu phải của chị?” Bỏ món dư ra rồi tính lại.', refused=True)
        kit.need(not missing, f'{who}: “Còn thiếu {ITEM[missing[0]["item"]]["name"].lower()} màu {missing[0]["colour"]} nữa em.”' if missing else '')
    else:
        items = [x['item'] for x in t['picks']]
        kit.need(_is_set(items), f'{who}: “Vậy chưa thành một bộ em ơi — cần váy/áo dài, hoặc áo với quần.”')
        total = sum(_price(c, x['item']) for x in t['picks'])
        if total > t['needs']['budget']:
            t['mistakes'] += 1
            cq.slip(t, 'over_budget', 1, 'Tôi đã nói ngân sách rồi mà vẫn chọn đồ vượt tiền.', 'vượt ngân sách khách dặn')
            return dict(message=f'{who} nhìn tem giá: “{total} xu lận hả? Chị nói tối đa {t["needs"]["budget"]} xu mà.” Chọn lại cho vừa túi tiền.', refused=True)
    lines = [dict(label=ITEM[x['item']]['name'], item=x['item'], size=x['size'], colour=x['colour'],
                  unit=_price(c, x['item']), qty=1, amount=_price(c, x['item'])) for x in t['picks']]
    return _open_bill(c, t, lines)


def _open_bill(c, t, lines):
    sub = sum(x['amount'] for x in lines)
    t['bill'] = dict(lines=lines, sub=sub, off=0, total=sub, sale=bool(any(
        isinstance(_data(c).get('sale'), dict) and _data(c)['sale'].get('day') == c['day'] and x['item'] in _data(c)['sale'].get('tags', {})
        for x in lines)))
    t['stage'] = 'pay'
    who = _who(t)
    if t['needs'].get('haggle') and t['kind'] in ('fit', 'outfit') and t['haggle'] is None:
        t['haggle'] = 'ask'
        return dict(message=f'Bill {sub} xu. {who} chống nạnh: “Khách quen mà con, bớt cho dì chút đi!”')
    t['cash'] = till.new(sub, t['id'], c=c, t=t)
    return dict(message=f'Bill {sub} xu. {who} đưa {" + ".join(str(v) for v in t["cash"]["tender"])} xu.' + (' Vừa đủ, khỏi thối.' if not till.due(t['cash']) else ''))


def _haggle(s, c, t, p):
    kit.need(t['haggle'] == 'ask' and t['stage'] == 'pay', 'Không ai đang trả giá.')
    answer = kit.one_of(p.get('answer'), ('hold', 'small', 'big'), 'Chọn giữ giá, bớt chút hoặc bớt nhiều.')
    b = t['bill']
    off = {'hold': 0, 'small': b['sub'] * HAGGLE_SMALL // 100, 'big': b['sub'] * HAGGLE_BIG // 100}[answer]
    b['off'] = off
    b['total'] = b['sub'] - off
    t['haggle'] = answer
    d = _data(c)
    if answer == 'big':
        d['stats']['haggle_off'] += off
        _note(c, f'Bớt cho {_who(t)} {off} xu, quá mức {HAGGLE_SMALL}% chị Vy dặn.')
    t['cash'] = till.new(b['total'], t['id'], c=c, t=t)
    who = _who(t)
    line = {'hold': f'Bạn cười: “Giá tiệm để sát rồi dì ơi, con tặng dì câu chúc mua may bán đắt!” {who} bĩu môi nhưng vẫn móc tiền.',
            'small': f'Bạn bớt {off} xu “lấy hên”. {who} cười tít: “Vậy mới là khách quen chứ!”',
            'big': f'Bạn bớt luôn {off} xu. {who} hớn hở — chị Vy đứng trong nhìn ra, hơi nhíu mày.'}[answer]
    return dict(message=f'{line} Còn {b["total"]} xu. {who} đưa {" + ".join(str(v) for v in t["cash"]["tender"])} xu.')


def _pay(s, c, t, p):
    kit.need(t['stage'] == 'pay' and t['bill'], 'Chốt bill trước khi thu tiền.')
    kit.need(t['haggle'] != 'ask', f'{_who(t)} đang chờ bạn trả lời chuyện bớt giá.')
    kit.need(t['cash'] is not None, 'Chưa có tiền khách đưa.')
    # The goods must still be on the rack (a happening or another bill may have taken them).
    need = {}
    for x in t['bill']['lines']:
        if x['item']:
            need[(x['item'], x['size'])] = need.get((x['item'], x['size']), 0) + 1
    for (item, size), q in need.items():
        if _data(c)['grid'][item].get(size, 0) < q:
            t['stage'] = 'pick'
            t['bill'] = None
            t['cash'] = None
            t['haggle'] = None
            return dict(message=f'Giá treo vừa hết {ITEM[item]["name"].lower()} {_sz(size)}. Bill được mở lại, chọn lại giùm khách nhé.', refused=True)
    who = _who(t)
    chk = till.check(s, c, t, t['cash'], p.get('change'), who)
    if chk['stop']:
        return dict(message=chk['message'], refused=True)
    return _finish(s, c, t)


def _finish(s, c, t):
    who = _who(t)
    d = _data(c)
    total = t['bill']['total']
    wrong = _size_slips(t) if t['kind'] in ('fit', 'outfit', 'room') else []
    if t['kind'] == 'outfit':
        _judge_slips(t, OCCASIONS[t['needs']['occasion']], [(x['item'], x['colour']) for x in t['picks']])
    if t['kind'] == 'alter':
        _alter_slips(t)
    react = cq.react(s, c, t, total, who=who)
    money = till.settle(s, c, t, t['cash'], react, who)
    notes = [x for x in (react['message'], money['message']) if x]
    if react['kind'] in ('refuse', 'walkout'):
        t['stage'] = 'done'
        t['result'] = dict(total=total, net=0, loss=0, tip=0)
        d['stats']['customers'] += 1
        kit.complete(s, c, t, 0, f'{who} để đồ lại trên quầy, không mua nữa: “{t["title"]}”.')
        return dict(message=f'{who} để đồ lại, không lấy nữa. ' + ' '.join(notes))
    for x in t['bill']['lines']:
        if x['item']:
            _sell(c, x['item'], x['size'])
    for x, right in wrong:
        d['seq'] += 1
        d['swaps'] = (d['swaps'] + [dict(id=f'sw-{d["seq"]}', npc=t['npc'], item=x['item'], colour=x['colour'], wrong=x['size'],
                                         right=right, price=_line_price(t, x), day=c['day'] + 1, task=t['id'])])[-12:]
    if not wrong and t['kind'] in ('fit', 'outfit') and _npc_index(t) in REGULARS:
        _remember_sizes(c, t)
    share = t['needs']['fee'] * TAILOR_SHARE // 100 if t['kind'] == 'alter' and t['alt']['mode'] == 'send' else 0
    net = react['pay'] - money['loss']
    t['stage'] = 'done'
    t['result'] = dict(total=total, net=net, loss=money['loss'], tip=money['tip'])
    d['stats']['sales'] += max(0, react['pay'])
    d['stats']['customers'] += 1
    d['day_sales'] += max(0, react['pay'])
    kit.metric(c, 'ao_sales')
    kit.complete(s, c, t, max(0, net), f'Bạn đã phục vụ {who}: “{t["title"]}”.')
    if net < 0 and min(-net, c['money']) > 0:
        kit.money(s, c, -min(-net, c['money']), 'Thất thoát ở quầy: ' + t['title'], t['id'], 'loss')
    if share and c['money'] > 0:
        kit.money(s, c, -min(share, c['money']), 'Trả công Bà Tư sửa đồ', t['id'], 'service')
        notes.append(f'Gửi Bà Tư {share} xu tiền công.')
    head = f'Đã thu {total} xu · +{max(0, net)} xu.'
    if wrong:
        notes.append('Khách về nhà mặc thử mới biết không vừa — mai sẽ quay lại đổi size.')
    return dict(message=head + (' ' + ' '.join(notes) if notes else ''), celebrate=not cq.slips(t) and not t['mistakes'])


def _line_price(t: dict, x: dict) -> int:
    for ln in (t['bill'] or {}).get('lines', []):
        if ln['item'] == x['item'] and ln['size'] == x['size']:
            return ln['unit']
    return PRICES[x['item']]


def _size_slips(t: dict) -> list:
    """Wrong sizes are found at home: a clear slip and a comeback swap tomorrow."""
    wrong = []
    for i, x in enumerate(t['picks']):
        right = _want_size(t, x)
        if right is not None and x['size'] != right and t['tried'][i] != 'ok':
            wrong.append((x, right))
    if wrong:
        x, right = wrong[0]
        feel = 'chật' if _smaller(x['item'], x['size'], right) else 'rộng'
        t['mistakes'] += 1
        cq.slip(t, 'wrong_size', 2, f'Về nhà mặc thử mới thấy {feel}, phải quay lại tiệm đổi size.', f'lấy sai size ({x["size"]} thay vì {right})')
    return wrong


def _judge(o: dict, pieces: list) -> list:
    """Occasion rules: [(code, sev, text, note)]."""
    items = [p[0] for p in pieces]
    out = []
    main = next((m for m in o['mains'] if all(i in items for i in m)), None)
    if not main:
        out.append(('occasion_miss', 2, f'Đi {o["name"].lower()} mà bộ này lạc quẻ, tới nơi mới thấy không hợp dịp.', 'bộ đồ không hợp dịp'))
    else:
        for it, col in pieces:
            if it not in main:
                continue
            if col in o['bad'] and GROUP[it] in o['bad_on']:
                out.append(('colour_taboo', 2, f'{o["name"]} mà mặc màu {col}, người ta nhìn mình quá trời.', f'chọn màu {col} kiêng kỵ'))
                break
            if it in o['colours'] and col not in o['colours'][it]:
                out.append(('colour_off', 1, f'Màu {col} hơi lệch với dịp {o["name"].lower()}, nhưng thôi cũng tạm.', f'màu {col} chưa hợp dịp'))
                break
    for need in o['need']:
        if need not in items:
            out.append(('missing_acc', 1, f'{o["name"]} mà thiếu {ITEM[need]["name"].lower()}, tiếc ghê.', f'thiếu {ITEM[need]["name"].lower()}'))
    odd = [i for i in items if i in o['odd']]
    if odd:
        out.append(('odd_piece', 1, f'Tiệm bỏ thêm {ITEM[odd[0]]["name"].lower()} vào bộ đi {o["name"].lower()}, chẳng biết mặc lúc nào.',
                    f'thêm {ITEM[odd[0]]["name"].lower()} không hợp dịp'))
    return out


def _judge_slips(t: dict, o: dict, pieces: list) -> None:
    for code, sev, text, note in _judge(o, pieces):
        t['mistakes'] += 1
        cq.slip(t, code, sev, text, note)


def _remember_sizes(c: dict, t: dict) -> None:
    d = _data(c)
    key = str(_npc_index(t))
    row = d['book'].setdefault(key, dict(top=None, waist=None, kid=[], visits=0))
    row['visits'] = min(999, row['visits'] + 1)
    for x in t['picks']:
        right = _want_size(t, x)
        if right is None:
            continue
        if x['item'] == 'jeans':
            row['waist'] = right
        elif x['item'] == 'kids':
            if right not in row['kid']:
                row['kid'] = (row['kid'] + [right])[-3:]
        elif right in LETTERS:
            row['top'] = right


# ---- alterations
def _alter(s, c, t, name, p):
    a = t['alt']
    n = t['needs']
    who = _who(t)
    if name == 'ao_measure':
        kit.need(t['stage'] == 'measure', 'Đã đo rồi.')
        kit.start_work(t)
        a['measured'] = True
        a['cm'] = n['_cm']
        if n['job'] == 'hem':
            return dict(message=f'Bạn cho {who} mặc thử, ghim kim ở mắt cá: cần cắt lên {a["cm"]} cm.')
        return dict(message=f'Bạn quấn thước dây quanh eo, ghim hai bên hông: cần bóp vào {a["cm"]} cm.')
    if name == 'ao_alter_self':
        kit.need(t['stage'] == 'measure', 'Đồ đang được sửa rồi.')
        kit.start_work(t)
        cut = kit.integer(p.get('cm'), 1, 10)
        a.update(mode='self', cut=cut)
        t['stage'] = 'sew'
        return dict(message=f'Bạn phấn một đường {cut} cm rồi ngồi vào máy may. Đạp máy, dừng đúng vạch nha!')
    if name == 'ao_alter_send':
        kit.need(t['stage'] == 'measure', 'Đồ đang được sửa rồi.')
        kit.start_work(t)
        a.update(mode='send', sent=c['turn'])
        t['stage'] = 'wait'
        share = n['fee'] * TAILOR_SHARE // 100
        return dict(message=f'Bạn mang đồ sang gian bên cho Bà Tư. Bà đeo kính lên: “Để đó, chút xíu là xong.” (công {share} xu)')
    if name == 'ao_alter_collect':
        kit.need(t['stage'] == 'wait', 'Không có đồ nào đang gửi Bà Tư.')
        left = a['sent'] + TAILOR_TURNS - c['turn']
        kit.need(left <= 0, f'Bà Tư còn đang may, chờ thêm chút nha (khoảng {left} nhịp).')
        a.update(cut=n['_cm'], seam='good', measured=True, cm=n['_cm'])
        t['stage'] = 'ready'
        return dict(message='Bà Tư đưa lại đồ, đường may thẳng tắp: “Của khách đây, gửi lời hỏi thăm giùm bà.”')
    if name == 'ao_sew_start':
        kit.need(t['stage'] == 'sew', 'Chưa tới bước may.')
        kit.need(a['start'] is None, 'Máy đang chạy rồi, canh vạch mà dừng.')
        a['start'] = kit.now()
        return dict(message='Rè rè rè… kim chạy dọc đường phấn. Dừng khi kim tới vạch xanh!', start=a['start'])
    if name == 'ao_sew_stop':
        kit.need(t['stage'] == 'sew' and a['start'] is not None, 'Máy chưa chạy.')
        prog = (kit.now() - a['start']) / SEW_SECONDS
        lo, hi = SEW_ZONE_EASY if kit.tier(c['day']) == 0 else SEW_ZONE
        if prog < lo:
            return dict(message='Kim chưa tới vạch, đạp thêm chút nữa rồi dừng.', refused=True)
        a['seam'] = 'good' if prog <= hi else 'crooked'
        a['start'] = None
        t['stage'] = 'ready'
        if a['seam'] == 'good':
            return dict(message='Dừng ngay vạch! Đường may thẳng băng, lại mũi gọn gàng.')
        return dict(message='Hơi lố vạch, cuối đường may bị xiên một chút. Thôi, tính tiền cho khách.')
    return _counter(s, c, t, name, p)


def _alter_slips(t: dict) -> None:
    a = t['alt']
    need = t['needs']['_cm']
    job = t['needs']['job']
    if a['cut'] is None:
        return
    if a['cut'] > need:
        t['mistakes'] += 1
        cq.slip(t, 'cut_short', 3 if a['cut'] - need >= 2 else 2,
                'Cắt lố tay, quần giờ cao tới mắt cá, mặc như quần lửng.' if job == 'hem' else 'Bóp lố tay, giờ mặc vào nín thở không nổi.',
                f'cắt lố {a["cut"] - need} cm')
    elif a['cut'] < need:
        t['mistakes'] += 1
        cq.slip(t, 'alter_short', 1, 'Sửa rồi mà vẫn còn dài, chắc phải mang lại lần nữa.' if job == 'hem' else 'Bóp rồi mà eo vẫn còn rộng.',
                f'sửa thiếu {need - a["cut"]} cm')
    if a['seam'] == 'crooked':
        t['mistakes'] += 1
        cq.slip(t, 'seam', 1, 'Đường may hơi xiên, nhìn kỹ là thấy.', 'đường may bị xiên')


# ---- fitting room
def _room(s, c, t, name, p):
    r = t['room']
    q = t['needs']['queue']
    if t['stage'] != 'room':
        return _counter(s, c, t, name, p)
    kit.start_work(t)
    i = r['i']
    kit.need(i < len(q), 'Phòng thử đã vãn khách.')
    cur = q[i]
    key = str(i)
    who = PEOPLE[cur['npc']][0]
    if name == 'ao_room_tag':
        kit.need(key not in r['tags'] and key not in r['outs'], f'{who} đã có thẻ rồi.')
        n = kit.integer(p.get('count'), 1, 6)
        r['tags'][key] = n
        if n != cur['items']:
            t['mistakes'] += 1
        return dict(message=f'Bạn đưa {who} thẻ số {n} món. {who} kéo rèm bước vào.')
    if name == 'ao_room_out':
        kit.need(key not in r['outs'], f'{who} ra rồi.')
        back = cur['items'] - (1 if cur['_out'] in ('left', 'hidden') else 0)
        r['outs'][key] = back
        tag = r['tags'].get(key)
        if tag is None:
            # No tag: nobody can tell. A hidden piece walks out.
            _room_close(c, t, i, 'lost' if cur['_out'] == 'hidden' else 'found' if cur['_out'] == 'left' else 'ok')
            extra = ' Không có thẻ số nên chẳng biết khách mang vào mấy món.'
            return dict(message=f'{who} bước ra, trả {back} món rồi đi luôn.{extra}')
        if back >= tag:
            _room_close(c, t, i, 'ok')
            return dict(message=f'{who} trả lại đủ {back}/{tag} món, cảm ơn rồi đi. Mời người kế tiếp.')
        return dict(message=f'{who} trả lại {back} món, thẻ ghi {tag}. Thiếu {tag - back} món! Kiểm phòng thử hoặc hỏi khéo khách.')
    if name in ('ao_room_check', 'ao_room_ask', 'ao_room_let'):
        kit.need(key in r['outs'] and key not in r['res'], 'Chưa có ai cần kiểm.')
        if name == 'ao_room_check':
            kit.need(i not in r['checked'], 'Đã kiểm phòng rồi.')
            r['checked'].append(i)
            if cur['_out'] == 'left':
                _room_close(c, t, i, 'found')
                _data(c)['stats']['room_saved'] += 1
                return dict(message=f'Trên móc trong phòng còn treo một chiếc {ITEM[cur["_what"]]["name"].lower()} — {who} quên thôi. Treo lại lên giá.')
            return dict(message='Phòng thử trống trơn, không còn món nào trên móc.')
        if name == 'ao_room_ask':
            if cur['_out'] == 'hidden':
                _room_close(c, t, i, 'returned')
                _data(c)['stats']['room_saved'] += 1
                return dict(message=f'Bạn nói nhỏ: “Chị ơi hình như còn một món chưa trả…” {who} đỏ mặt, lấy chiếc {ITEM[cur["_what"]]["name"].lower()} mặc bên trong ra: “À… chị quên.”')
            t['mistakes'] += 1
            cq.slip(t, 'accuse', 2, 'Tiệm nghi oan khách ngay trước phòng thử, tôi đứng ngoài mà ngại giùm.', 'nghi oan khách ở phòng thử')
            _data(c)['stats']['accused'] += 1
            _room_close(c, t, i, 'accused')
            return dict(message=f'{who} đỏ mặt, dốc cả túi xách ra: “Chị không lấy gì hết!” rồi bỏ đi. Mấy khách đang chờ nhìn nhau.', refused=True)
        # let go
        _room_close(c, t, i, 'lost' if cur['_out'] == 'hidden' else 'found' if cur['_out'] == 'left' else 'ok')
        return dict(message=f'Bạn để {who} đi.' + (' Tối kiểm hàng mới biết mất một món.' if cur['_out'] == 'hidden' else ''))
    raise kit.eng().GameError('Việc phòng thử không hợp lệ.')


def _room_close(c: dict, t: dict, i: int, res: str) -> None:
    r = t['room']
    q = t['needs']['queue']
    r['res'][str(i)] = res
    if res == 'lost':
        item = q[i]['_what']
        d = _data(c)
        d['stats']['room_lost'] += 1
        t['mistakes'] += 1
        cq.slip(t, 'room_loss', 1, 'Phòng thử lộn xộn, đồ vào ra không ai đếm.', 'để mất đồ ở phòng thử')
        if kit.stock(c, item) > 0:
            row = d['grid'][item]
            size = max(row, key=lambda z: row[z])
            if row[size] > 0:
                cost = kit.take(c, item, 1)
                row[size] -= 1
                kit.waste(c, item, 1, cost or ITEM[item]['cost'], 'Mất ở phòng thử')
        _note(c, f'Mất một {ITEM[item]["name"].lower()} ở phòng thử.')
    r['i'] = i + 1
    if r['i'] >= len(q):
        t['stage'] = 'pick'


# ---- returns and exchanges
FACTS = ('tag', 'receipt', 'wear')


def _return(s, c, t, name, p):
    r = t['ret']
    n = t['needs']
    who = _who(t)
    if name == 'ao_inspect':
        what = kit.one_of(p.get('what'), FACTS, 'Kiểm tem, hóa đơn hoặc tình trạng đồ.')
        kit.start_work(t)
        if what not in r['seen']:
            r['seen'].append(what)
        return dict(message=_fact(n, what))
    if name == 'ao_return_do':
        kit.confirm(p, 'Xác nhận cách xử lý đổi trả.')
        choice = kit.one_of(p.get('choice'), ('refund', 'exchange', 'refuse'), 'Chọn hoàn tiền, đổi hàng hoặc từ chối.')
        tone = kit.one_of(p.get('tone', 'calm'), ('calm', 'blunt'), 'Cách nói không hợp lệ.')
        new_size = None
        if choice == 'exchange':
            new_size = _size_arg(n['item'], p.get('new_size') or n['new_size'] or n['size'])
            kit.need(_free(c, n['item'], new_size, t) > 0, f'Giá treo hết size {new_size}. Hoàn tiền hoặc hẹn khách khi hàng về.')
        kit.start_work(t)
        r.update(choice=choice, tone=tone if choice == 'refuse' else None, new_size=new_size)
        return _return_finish(s, c, t)
    raise kit.eng().GameError('Thao tác đổi trả không hợp lệ.')


def _fact(n: dict, what: str) -> str:
    if what == 'tag':
        return 'Tem mác còn nguyên, bấm chỉ chắc chắn.' if n['_tag'] else 'Tem mác đã bị cắt, chỉ còn lỗ bấm.'
    if what == 'receipt':
        if not n['_receipt']:
            return 'Khách không có hóa đơn: “Chị lỡ làm mất rồi.”'
        return (f'Hóa đơn ngày {n["days_ago"]} ngày trước, giá {n["price"]} xu' + (', có dấu đỏ “SALE — không đổi trả”.' if n['_sale'] else '.'))
    if n['_defect']:
        return 'Đường may bị bung một đoạn — lỗi may của xưởng, không phải do khách.'
    if n['_worn']:
        return 'Cổ áo có vệt phấn, nách còn mùi nước hoa, vải hơi xù — đồ đã mặc rồi.'
    return 'Vải còn mới tinh, gấp nếp nguyên như lúc mua.'


def _return_ok(n: dict) -> dict:
    """What the policy allows for this case: {choice: 'good'|'ok'|'bad'}."""
    case = n['_case']
    if case == 'defect':
        return dict(refund='good', exchange='good', refuse='bad')
    if case == 'size_swap':
        return dict(refund='ok', exchange='good', refuse='bad')
    if case == 'no_receipt':
        return dict(refund='bad', exchange='good', refuse='ok')
    return dict(refund='bad', exchange='bad', refuse='good')   # worn / sale / late


def _return_finish(s, c, t):
    n = t['needs']
    r = t['ret']
    d = _data(c)
    who = _who(t)
    case = n['_case']
    grade = _return_ok(n)[r['choice']]
    lines = []
    if r['choice'] == 'refuse':
        if grade == 'bad':
            t['mistakes'] += 1
            if case == 'defect':
                cq.slip(t, 'refuse_defect', 3, 'Áo bung chỉ sau một lần mặc mà tiệm còn chối, không nhận lỗi.', 'từ chối đổi đồ lỗi của tiệm')
            else:
                cq.slip(t, 'refuse_valid', 2, 'Đồ còn tem, có hóa đơn, đúng hạn mà tiệm không cho đổi.', 'từ chối đổi trả đúng chính sách')
        if r['tone'] == 'blunt':
            t['mistakes'] += 1
            cq.slip(t, 'rude', 2, 'Tôi hỏi đổi trả thôi mà nhân viên nói chuyện như đuổi khách.', 'nói chuyện cộc lốc với khách')
        why = {'worn': 'đồ đã mặc, tem đã cắt', 'sale': 'hàng sale không đổi trả', 'late': f'đã quá {RETURN_DAYS} ngày',
               'no_receipt': 'không có hóa đơn nên chỉ đổi hàng được thôi'}.get(case, 'theo chính sách')
        lines.append(f'Bạn {"chỉ vào bảng chính sách, nhẹ nhàng giải thích" if r["tone"] == "calm" else "nói thẳng"}: {why}.')
    else:
        resell = n['_tag'] and not n['_worn'] and not n['_defect']
        if r['choice'] == 'refund':
            back = min(n['price'], c['money'])
            if back:
                kit.money(s, c, -back, f'Hoàn tiền đổi trả: {t["title"]}'[:120], t['id'], 'refund')
            d['stats']['refunds'] += 1
            lines.append(f'Hoàn lại {back} xu cho {who}.')
        else:
            _sell(c, n['item'], r['new_size'])
            lines.append(f'Đổi cho {who} {ITEM[n["item"]]["name"].lower()} size {r["new_size"]}.')
        if resell:
            _restock_one(c, n['item'], n['size'])
            lines.append('Món cũ còn tem, treo lại lên giá.')
        else:
            kit.waste(c, n['item'], 1, ITEM[n['item']]['cost'], 'Đồ đổi trả không bán lại được')
            lines.append('Món cũ không bán lại được nữa.')
        if grade == 'bad':
            t['mistakes'] += 1
            if case == 'worn':
                d['stats']['frauds'] += 1
                cq.slip(t, 'fraud_ok', 2, 'Tiệm dễ dãi thật, đồ mặc đi tiệc rồi vẫn nhận lại.', 'nhận lại đồ đã mặc')
                _note(c, f'Nhận lại đồ đã mặc của {who} — lỗ nguyên món.')
            elif case == 'no_receipt':
                cq.slip(t, 'cash_no_receipt', 1, 'Mất hóa đơn mà tiệm vẫn hoàn tiền mặt, dễ ghê.', 'hoàn tiền khi không có hóa đơn')
            else:
                cq.slip(t, 'policy_broken', 1, 'Tưởng không đổi được, ai dè tiệm vẫn nhận. Dễ vậy lần sau tôi đổi hoài.', 'đổi trả sai chính sách')
                _note(c, f'Nhận đổi trả trái chính sách cho {who}.')
    react = cq.react(s, c, t, RETURN_PAY if grade != 'bad' else 0, who=who)
    t['stage'] = 'done'
    t['result'] = dict(choice=r['choice'], grade=grade)
    pay = react['pay'] if grade != 'bad' else 0
    kit.complete(s, c, t, pay, f'Bạn xử lý đổi trả cho {who}: “{t["title"]}”.')
    if react['message']:
        lines.append(react['message'])
    return dict(message=' '.join(lines), celebrate=grade == 'good' and not cq.slips(t))


# ---- sale tags
def _sale(s, c, t, name, p):
    sl = t['sale']
    lines = t['needs']['lines']
    if name == 'ao_tag':
        i = kit.integer(p.get('line'), 0, len(lines) - 1)
        price = p.get('price')
        kit.need(type(price) is int and price in sl['options'][i], 'Giá tem không có trong máy in.')
        kit.start_work(t)
        sl['tags'][str(i)] = price
        return dict(message=f'In tem: {ITEM[lines[i]["item"]]["name"]} · {price} xu.')
    if name == 'ao_sale_done':
        kit.confirm(p, 'Treo tem sale lên giá?')
        kit.need(len(sl['tags']) == len(lines), 'Còn món chưa in tem sale.')
        d = _data(c)
        loss, high = 0, []
        for i, ln in enumerate(lines):
            base = sl['base'][ln['item']]
            right = base * (100 - ln['pct']) // 100
            tag = sl['tags'][str(i)]
            if tag < right:
                loss += (right - tag) * SALE_UNITS
            elif tag > right:
                high.append((ln, tag, right))
        if loss:
            t['mistakes'] += 1
            cq.slip(t, 'sale_low', 2 if loss >= 60 else 1, 'Tem sale ghi thấp hơn bảng, khách mua hời mà tiệm lỗ.', f'tem sale thấp, lỗ {loss} xu')
        if high:
            ln, tag, right = high[0]
            t['mistakes'] += 1
            cq.slip(t, 'sale_high', 2, f'Khách phàn nàn: bảng ghi giảm {ln["pct"]}% mà tem tính chưa tới.', 'tem sale cao hơn bảng giảm giá')
        d['sale'] = dict(day=c['day'], tags={ln['item']: sl['tags'][str(i)] for i, ln in enumerate(lines)},
                         pct={ln['item']: ln['pct'] for ln in lines})
        react = cq.react(s, c, t, SALE_PAY, who=PEOPLE[VY][0])
        t['stage'] = 'done'
        t['result'] = dict(loss=loss, high=len(high))
        kit.complete(s, c, t, react['pay'], 'Bạn treo tem sale cuối mùa cho chị Vy.')
        msg = ['Tem sale đã lên giá, khách ghé lựa rần rần.']
        if loss:
            kit.money(s, c, -min(loss, c['money']), 'Tem sale ghi thấp hơn bảng', t['id'], 'loss')
            msg.append(f'Tối cộng sổ: tem thấp làm tiệm hụt {loss} xu.')
        if high:
            msg.append('Có khách cầm tem ra quầy hỏi sao giảm không đúng bảng.')
        if react['message']:
            msg.append(react['message'])
        return dict(message=' '.join(msg), celebrate=not loss and not high)
    raise kit.eng().GameError('Thao tác tem sale không hợp lệ.')


# ---- online orders
def _online(s, c, t, name, p):
    pc = t['parcel']
    who = _who(t)
    if name == 'ao_pack':
        kit.need(not pc['sealed'], 'Gói đã dán băng keo rồi.')
        item = _item_arg(p)
        size = _size_arg(item, p.get('size'))
        colour = _colour_arg(item, p.get('colour'))
        kit.need(len(pc['items']) < MAX_PICKS, 'Gói đầy rồi.')
        kit.need(_free(c, item, size, t) - sum(1 for x in pc['items'] if x['item'] == item and x['size'] == size) > 0,
                 f'Giá treo hết {ITEM[item]["name"].lower()} {_sz(size)}.')
        kit.start_work(t)
        pc['items'].append(dict(item=item, size=size, colour=colour))
        pc['label'] = None
        return dict(message=f'Gấp {ITEM[item]["name"].lower()} {_sz(size)} màu {colour} bỏ vào túi zip.')
    if name == 'ao_unpack':
        kit.need(not pc['sealed'] and pc['items'], 'Không có gì để lấy ra.')
        i = kit.integer(p.get('index'), 0, len(pc['items']) - 1)
        pc['items'].pop(i)
        pc['label'] = None
        return dict(message='Đã lấy món đó ra khỏi gói.')
    if name == 'ao_label':
        kit.need(pc['items'], 'Gói còn trống.')
        kit.need(not pc['sealed'], 'Gói đã dán rồi.')
        total = sum(_price(c, x['item']) for x in pc['items'])
        cod = total if t['needs']['pay'] == 'cod' else 0
        pc['label'] = dict(total=total, cod=cod)
        return dict(message=f'In phiếu giao: {who} · {t["needs"]["address"]} · ' + (f'thu hộ {cod} xu.' if cod else 'đã thanh toán, không thu hộ.'))
    if name == 'ao_seal':
        kit.need(pc['label'], 'In phiếu giao trước rồi dán gói.')
        kit.need(not pc['sealed'], 'Gói đã dán rồi.')
        pc['sealed'] = True
        return dict(message='Dán băng keo hai vòng, dán phiếu lên mặt gói. Sẵn sàng giao!')
    if name == 'ao_ship':
        kit.confirm(p, 'Giao gói hàng cho shipper?')
        kit.need(pc['label'], 'In phiếu giao trước đã.')
        return _ship(s, c, t)
    raise kit.eng().GameError('Thao tác đơn online không hợp lệ.')


def _parcel_diff(t: dict) -> tuple[list, list, list]:
    want = [dict(x) for x in t['needs']['lines']]
    left = []
    for x in t['parcel']['items']:
        hit = next((w for w in want if w['item'] == x['item'] and w['size'] == x['size'] and w['colour'] == x['colour']), None)
        if hit:
            want.remove(hit)
        else:
            left.append(x)
    wrong, extra = [], []
    for x in left:
        same = next((w for w in want if w['item'] == x['item']), None)
        if same:
            want.remove(same)
            wrong.append((x, same))
        else:
            extra.append(x)
    return want, wrong, extra


def _ship(s, c, t):
    pc = t['parcel']
    d = _data(c)
    who = _who(t)
    for x in pc['items']:
        kit.need(d['grid'][x['item']].get(x['size'], 0) > 0, f'Giá treo vừa hết {ITEM[x["item"]]["name"].lower()} {_sz(x["size"])}.')
    missing, wrong, extra = _parcel_diff(t)
    loss = 0
    if wrong:
        x, w = wrong[0]
        t['mistakes'] += 1
        cq.slip(t, 'wrong_parcel', 2, f'Đặt {ITEM[w["item"]]["name"].lower()} size {w["size"]} màu {w["colour"]} mà nhận {_sz(x["size"])} màu {x["colour"]}, phải gửi trả lại.',
                'gửi sai size/màu')
        loss += SHIP_FEE * 2
    if missing:
        t['mistakes'] += 1
        cq.slip(t, 'missing_item', 2, f'Mở gói ra thiếu {ITEM[missing[0]["item"]]["name"].lower()}, nhắn tiệm mãi mới trả lời.', 'gửi thiếu món')
    if extra:
        t['mistakes'] += 1
        cq.slip(t, 'extra_parcel', 1, 'Gói hàng có thêm món tôi không đặt, lại phải gửi trả.', 'gửi dư món')
        loss += SHIP_FEE
    if not pc['sealed']:
        t['mistakes'] += 1
        cq.slip(t, 'unsealed', 1, 'Gói hàng tới nơi bung băng keo, đồ lấm bụi.', 'gói hàng không dán kỹ')
    total = pc['label']['total']
    react = cq.react(s, c, t, total, who=who)
    for x in pc['items']:
        _sell(c, x['item'], x['size'])
    pay = react['pay']
    if pay:
        kit.bank(pay)
    net = pay - SHIP_FEE - loss
    t['stage'] = 'done'
    t['result'] = dict(total=total, net=net, loss=loss)
    d['stats']['sales'] += max(0, pay)
    d['day_sales'] += max(0, pay)
    kit.metric(c, 'ao_online')
    kit.complete(s, c, t, max(0, net), f'Bạn gửi đơn online cho {who}.')
    if net < 0 and c['money'] > 0:
        kit.money(s, c, -min(-net, c['money']), 'Phí ship đơn online', t['id'], 'loss')
    received = pay
    msg = f'Shipper chạy đi rồi! {"Tiền chuyển khoản" if t["needs"]["pay"] == "paid" else "Tiền thu hộ"} {received} xu · trừ ship {SHIP_FEE} xu.'
    if loss:
        msg += f' Gửi sai phải chịu thêm {loss} xu phí ship hai chiều.'
    if react['message']:
        msg += ' ' + react['message']
    return dict(message=msg, celebrate=not cq.slips(t))


# ---- the mannequin
def _display(s, c, t, name, p):
    dp = t['disp']
    if name == 'ao_dress':
        item = _item_arg(p)
        colour = _colour_arg(item, p.get('colour'))
        kit.need(len(dp['pieces']) < 4, 'Ma-nơ-canh mặc đủ rồi, bớt món ra trước.')
        kit.need(kit.stock(c, item) > 0, f'Kho hết {ITEM[item]["name"].lower()}.')
        kit.start_work(t)
        dp['pieces'].append(dict(item=item, colour=colour))
        return dict(message=f'Mặc cho ma-nơ-canh: {ITEM[item]["emoji"]} {ITEM[item]["name"].lower()} màu {colour}. Nhớ hấp cho phẳng.')
    if name == 'ao_undress':
        kit.need(dp['pieces'], 'Ma-nơ-canh đang trống.')
        i = kit.integer(p.get('index'), 0, len(dp['pieces']) - 1)
        dp['pieces'].pop(i)
        dp['steamed'] = [j - (1 if j > i else 0) for j in dp['steamed'] if j != i]
        return dict(message='Đã cởi món đó ra.')
    if name == 'ao_steam':
        kit.need(dp['pieces'], 'Mặc đồ lên ma-nơ-canh trước rồi hấp.')
        i = kit.integer(p.get('index'), 0, len(dp['pieces']) - 1)
        kit.need(i not in dp['steamed'], 'Món này phẳng rồi.')
        dp['steamed'].append(i)
        return dict(message='Xì xì… hơi nước phả ra, nếp nhăn biến mất.')
    if name == 'ao_display_done':
        kit.confirm(p, 'Trưng bày bộ này?')
        kit.need(dp['pieces'], 'Ma-nơ-canh còn trống.')
        return _display_finish(s, c, t)
    raise kit.eng().GameError('Thao tác trưng bày không hợp lệ.')


def _display_finish(s, c, t):
    dp = t['disp']
    o = OCCASIONS[t['needs']['theme']]
    pieces = [(x['item'], x['colour']) for x in dp['pieces']]
    rows = _judge(o, pieces)
    wrinkled = len(dp['pieces']) - len(dp['steamed'])
    for code, sev, text, note in rows:
        t['mistakes'] += 1
        cq.slip(t, code, sev, text.replace('người ta nhìn mình', 'khách đi ngang ngó rồi lắc đầu'), note)
    if wrinkled:
        t['mistakes'] += 1
        cq.slip(t, 'wrinkled', 1, 'Đồ trên ma-nơ-canh còn nhăn nhúm, nhìn kém sang.', f'{wrinkled} món chưa hấp')
    score = max(1, 5 - sum(r[1] for r in rows) - (1 if wrinkled else 0))
    plus = any(i in o['plus'] for i, _ in pieces)
    d = _data(c)
    d['display'] = dict(day=c['day'], score=score, theme=t['needs']['theme'], pieces=[dict(x) for x in dp['pieces']], plus=plus)
    react = cq.react(s, c, t, DISPLAY_PAY, who=PEOPLE[VY][0])
    t['stage'] = 'done'
    t['result'] = dict(score=score)
    kit.complete(s, c, t, react['pay'], 'Bạn thay đồ cho ma-nơ-canh cạnh cửa.')
    msg = {5: 'Bộ đồ đẹp tới mức mấy chị đi ngang dừng xe chụp ảnh!', 4: 'Ma-nơ-canh nhìn tươi hẳn, khách ghé hỏi giá.',
           3: 'Cũng được, nhưng chưa ai dừng lại ngắm.'}.get(score, 'Bộ đồ lạc chủ đề, chị Vy lắc đầu.')
    return dict(message=msg + (' ' + react['message'] if react['message'] else ''), celebrate=score >= 4)


# ---- comeback swaps (a wrong size found at home)
def _swap(s, c, p):
    d = _data(c)
    sid = p.get('id')
    row = next((x for x in d['swaps'] if x['id'] == sid and x['day'] <= c['day']), None)
    kit.need(row, 'Không có khách nào đang chờ đổi size.')
    kit.need(c.get('open'), 'Mở cửa tiệm trước nhé.')
    mode = kit.one_of(p.get('mode', 'swap'), ('swap', 'refund'), 'Đổi size hoặc hoàn tiền.')
    who = PEOPLE[int(row['npc'].rsplit('_', 1)[1]) - 1][0]
    if mode == 'swap':
        kit.need(_free(c, row['item'], row['right']) > 0, f'Giá treo hết size {row["right"]}. Nhập thêm hoặc hoàn tiền cho khách.')
        _sell(c, row['item'], row['right'])
        msg = f'Đổi cho {who} size {row["right"]}. {who}: “Lần này chắc vừa rồi ha.”'
    else:
        back = min(row['price'], c['money'])
        if back:
            kit.money(s, c, -back, f'Hoàn tiền đổi size cho {who}'[:120], row['task'], 'refund')
        msg = f'Hoàn {back} xu cho {who}.'
    _restock_one(c, row['item'], row['wrong'])
    d['swaps'] = [x for x in d['swaps'] if x['id'] != sid]
    d['stats']['swaps'] += 1
    kit.metric(c, 'ao_swaps')
    return dict(message=msg + ' Món cũ còn tem, treo lại lên giá.')


# ---------------------------------------------------------------- close
def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    lines = []
    for row in [x for x in d['swaps'] if x['day'] <= c['day']]:
        who = PEOPLE[int(row['npc'].rsplit('_', 1)[1]) - 1][0]
        kit.review(s, c, row['npc'], 1, f'Quay lại đổi size {ITEM[row["item"]]["name"].lower()} mà chờ tới tối cũng không ai lo. Thôi khỏi.', row['task'])
        lines.append(f'😞 {who} chờ đổi size mà không ai lo, để lại 1★.')
    d['swaps'] = [x for x in d['swaps'] if x['day'] > c['day']]
    disp = d.get('display')
    walk = 0
    if isinstance(disp, dict) and disp.get('score', 0) >= 4 and 0 <= c['day'] - disp['day'] <= DISPLAY_FRESH:
        want = 2 if disp['score'] >= 5 else 1
        for item in ('hat', 'socks', 'belt'):
            if walk >= want:
                break
            size = 'F'
            if _free(c, item, size) > 0:
                _sell(c, item, size)
                price = _price(c, item)
                kit.money(s, c, price, f'Khách ghé vì ma-nơ-canh: {ITEM[item]["name"]}', None, 'revenue')
                d['day_sales'] += price
                d['stats']['sales'] += price
                walk += 1
        if walk:
            d['stats']['walkins'] += walk
            lines.append(f'🧍‍♀️ {walk} khách đi ngang thấy ma-nơ-canh xinh quá, ghé mua phụ kiện.')
    d['sale'] = None        # the sale tags come down at closing
    look = LOOKS[_look(c)]
    nxt = next((x for x in LOOKS if x['served'] > int(c.get('metrics', {}).get('served', 0))), None)
    if nxt:
        lines.append(f'🪡 Tiệm: {look["name"]}. Phục vụ thêm {nxt["served"] - int(c["metrics"].get("served", 0))} khách nữa là chị Vy sửa sang: {nxt["name"]}.')
    else:
        lines.append(f'🪡 Tiệm: {look["name"]}.')
    tomorrow = mod_of(c['day'] + 1)
    lines.append(f'📅 Ngày mai: {tomorrow["emoji"]} {tomorrow["name"]}.')
    summary = dict(sales=d['day_sales'], lines=lines, note=f'Doanh thu quầy hôm nay {d["day_sales"]} xu.')
    d['day_sales'] = 0
    return summary


# ---------------------------------------------------------------- staff, hints
def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    role = e['role']
    if role == 'ao_steam':
        if t and t.get('career') == ID and t['kind'] == 'display' and t['known']:
            dp = t['disp']
            i = next((j for j in range(len(dp['pieces'])) if j not in dp['steamed']), None)
            if i is not None:
                dp['steamed'].append(i)
                return 'Đã ủi hơi giúp một món trên ma-nơ-canh.'
        return 'Đã ủi hơi mấy chiếc sơ mi trên giá cho phẳng phiu.'
    if role == 'ao_pack':
        if t and t.get('career') == ID and t['kind'] == 'online' and t['known'] and not t['parcel']['sealed']:
            missing, wrong, extra = _parcel_diff(t)
            if missing and not wrong and not extra:
                x = missing[0]
                if _free(c, x['item'], x['size'], t) - sum(1 for y in t['parcel']['items'] if y['item'] == x['item'] and y['size'] == x['size']) > 0:
                    t['parcel']['items'].append(dict(item=x['item'], size=x['size'], colour=x['colour']))
                    t['parcel']['label'] = None
                    return f'Đã gấp giúp {ITEM[x["item"]]["name"].lower()} {_sz(x["size"])} bỏ vào gói. Bạn vẫn in phiếu và kiểm lại.'
        return 'Đã xếp túi zip, cuộn băng keo và phiếu giao cho gọn.'
    if t and t.get('career') == ID and t['kind'] == 'room' and t['known'] and t['stage'] == 'room':
        r = t['room']
        i = r['i']
        q = t['needs']['queue']
        if i < len(q) and str(i) not in r['tags']:
            r['tags'][str(i)] = q[i]['items']
            return f'Đã đếm và đưa thẻ số {q[i]["items"]} món cho {PEOPLE[q[i]["npc"]][0]}.'
    return 'Đã gấp lại đồ khách thử, treo lên giá đúng size.'


def hint(c: dict, t: dict) -> str:
    return {
        'fit': 'Nghe khách tả → xem bảng size (form sơ mi ôm: lấy lớn hơn một size so với shop khác) → lấy đúng món, đúng màu → chưa chắc thì mời thử → tính tiền, thối đúng.',
        'outfit': 'Xem dịp và ngân sách → chọn váy/áo dài hoặc áo + quần, đúng size khách nói → tránh màu kiêng → thêm phụ kiện hợp dịp → tính tiền.',
        'alter': 'Đo trước → tự may (dừng máy đúng vạch xanh) hoặc gửi Bà Tư (chắc ăn, mất 40% công) → tính tiền công.',
        'room': 'Đếm số món khách cầm vào → đưa thẻ số → khách ra thì đếm lại → thiếu: kiểm phòng trước, rồi hỏi khéo → tính tiền cho khách mua.',
        'return': 'Xem tem, hóa đơn, tình trạng đồ → đối chiếu chính sách → hoàn tiền, đổi hoặc từ chối nhẹ nhàng.',
        'sale': 'Giá sale = giá gốc × (100 − % giảm) ÷ 100, làm tròn xuống → in đúng tem → treo lên giá.',
        'online': 'Đọc tin nhắn → bỏ đúng món, size, màu vào gói → in phiếu (COD = tiền gói) → dán gói → giao shipper.',
        'display': 'Chọn bộ hợp chủ đề → hấp phẳng từng món → trưng bày.',
    }.get(t.get('kind'), 'Làm từng bước và kiểm lại trước khi giao nhé.')


# ---------------------------------------------------------------- feedback
def feedback(c: dict, t: dict) -> dict:
    patience = t.get('patience', 100)
    speed = 5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2
    k = t['kind']
    rows = [dict(key='speed', label='Thời gian chờ', score=speed, note=f'kiên nhẫn còn {patience}%')]
    codes = {x['code'] for x in cq.slips(t)}
    if k in ('fit', 'outfit', 'room'):
        size_ok = 'wrong_size' not in codes
        rows.insert(0, dict(key='accuracy', label='Đúng size, đúng màu', score=5 if size_ok and 'wrong_colour' not in codes else 3,
                            note='mặc vừa như đo' if size_ok else 'phải quay lại đổi size'))
        if k == 'outfit':
            miss = codes & {'occasion_miss', 'colour_taboo', 'colour_off', 'missing_acc', 'odd_piece'}
            plus = any(x['item'] in OCCASIONS[t['needs']['occasion']]['plus'] for x in t['picks'])
            rows.append(dict(key='style', label='Gu phối đồ', score=2 if miss & {'occasion_miss', 'colour_taboo'} else 4 if miss or not plus else 5,
                             note='hợp dịp, có điểm nhấn' if not miss and plus else 'hợp dịp' if not miss else 'chưa hợp dịp'))
        if k == 'room':
            rows.append(dict(key='care', label='Phòng thử', score=2 if 'accuse' in codes else 4 if 'room_loss' in codes else 5,
                             note='gọn gàng, lịch sự' if not codes & {'accuse', 'room_loss'} else 'lộn xộn'))
    elif k == 'alter':
        rows.insert(0, dict(key='accuracy', label='Đường may', score=5 if not codes else 3, note='vừa như đo' if not codes else 'chưa chuẩn'))
    elif k == 'return':
        grade = (t.get('result') or {}).get('grade')
        rows.insert(0, dict(key='accuracy', label='Đúng chính sách', score={'good': 5, 'ok': 4}.get(grade, 2),
                            note={'good': 'xử lý rõ ràng', 'ok': 'tạm được'}.get(grade, 'chưa đúng chính sách')))
        rows.append(dict(key='manner', label='Thái độ', score=2 if 'rude' in codes else 5, note='nhẹ nhàng' if 'rude' not in codes else 'cộc lốc'))
    elif k == 'online':
        rows.insert(0, dict(key='accuracy', label='Đúng đơn', score=5 if not codes else 3, note='đúng món, đúng size' if not codes else 'gói sai'))
    elif k in ('sale', 'display'):
        rows.insert(0, dict(key='accuracy', label='Làm đúng lời dặn', score=5 if not codes else 3, note='chị Vy ưng' if not codes else 'còn sai sót'))
    cash = t.get('cash')
    if isinstance(cash, dict) and cash.get('outcome') not in (None, 'void'):
        oc = cash['outcome']
        rows.append(dict(key='change', label='Thối tiền', score=2 if oc == 'missed' else 3 if cash.get('asked') else 4 if oc in ('returned', 'kept') else 5,
                         note={'missed': 'thối thiếu', 'returned': 'thối dư', 'kept': 'thối dư'}.get(oc, 'thối đúng, đếm rõ ràng')))
    return dict(criteria=rows)


# ---------------------------------------------------------------- projection
def _strip(v):
    if isinstance(v, dict):
        return {k: _strip(x) for k, x in v.items() if not str(k).startswith('_')}
    if isinstance(v, list):
        return [_strip(x) for x in v]
    return v


def public_task(t: dict) -> dict:
    v = _strip(copy.deepcopy(t))
    if not t['known']:
        v['needs'] = None
        return v
    v['cash'] = till.public(t.get('cash'))
    if t['kind'] == 'return':
        v['facts'] = {w: _fact(t['needs'], w) for w in t['ret']['seen']}
    if t['kind'] == 'room':
        r = t['room']
        v['room_view'] = [dict(npc=kit.npc_id(ID, q['npc']), items=q['items'], what=q['_what'] if str(i) in r['res'] and r['res'][str(i)] in ('found', 'returned') else None)
                          for i, q in enumerate(t['needs']['queue'])]
    if t['kind'] == 'alter':
        v['sew'] = dict(seconds=SEW_SECONDS, zone=list(SEW_ZONE_EASY if kit.tier(t['day']) == 0 else SEW_ZONE))
        v['ready_turn'] = t['alt']['sent'] + TAILOR_TURNS if t['alt']['sent'] is not None else None
    return v


def public_data(c: dict) -> dict:
    d = _extend(copy.deepcopy(kit.data(c)))
    view = dict(c, ext=dict(c.get('ext', {}), data=d))
    _sync(view)
    held = {}
    for it in ITEMS:
        for s in SIZES[it['id']]:
            h = _held(c, it['id'], s)
            if h:
                held[f'{it["id"]}:{s}'] = h
    d['held'] = held
    d['prices'] = {k: _price(c, k) for k in PRICES}
    sale = d.get('sale')
    d['sale_today'] = sale if isinstance(sale, dict) and sale.get('day') == c['day'] else None
    d['swaps_due'] = [dict(x, name=PEOPLE[int(x['npc'].rsplit('_', 1)[1]) - 1][0],
                           can_swap=_free(view, x['item'], x['right']) > 0) for x in d['swaps'] if x['day'] <= c['day']]
    d['book_view'] = [dict(npc=kit.npc_id(ID, int(k)), name=PEOPLE[int(k)][0], **v) for k, v in sorted(d['book'].items(), key=lambda kv: int(kv[0]))]
    li = _look(c)
    served = int(c.get('metrics', {}).get('served', 0))
    nxt = LOOKS[li + 1] if li + 1 < len(LOOKS) else None
    d['look'] = li
    d['look_view'] = dict(stage=li, name=LOOKS[li]['name'], text=LOOKS[li]['text'],
                          next=dict(name=nxt['name'], left=nxt['served'] - served) if nxt else None)
    m = mod_of(c['day'])
    d['today'] = dict(day=c['day'], id=m['id'], emoji=m['emoji'], name=m['name'], text=m['text'])
    disp = d.get('display')
    fresh = isinstance(disp, dict) and 0 <= c['day'] - disp['day'] <= DISPLAY_FRESH
    d['display_view'] = dict(disp, fresh=fresh, age=c['day'] - disp['day']) if isinstance(disp, dict) else None
    care = []
    if d['swaps_due']:
        care.append(dict(icon='🔁', label=f'{len(d["swaps_due"])} khách quay lại đổi size', ok=False))
    if not fresh:
        care.append(dict(icon='🧍‍♀️', label='Ma-nơ-canh cần thay bộ mới', ok=None))
    empty = [f'{ITEM[i]["name"]} {s}' for i, row in d['grid'].items() for s, n in row.items() if n <= 0 and ITEM[i].get('unlock', 1) <= kit.level(c)]
    if empty:
        care.append(dict(icon='📦', label='Hết size: ' + ', '.join(empty[:4]) + (f' +{len(empty) - 4}' if len(empty) > 4 else ''), ok=None))
    d['care'] = care
    return d


# ---------------------------------------------------------------- validation
def _ints(values, low, high):
    for x in values:
        kit.integer(x, low, high)


def _valid_pick(x) -> None:
    kit.need(isinstance(x, dict) and set(x) == {'item', 'size', 'colour'} and x['item'] in ITEM
             and x['size'] in SIZES[x['item']] and x['colour'] in COLOURS[x['item']], 'Món trên quầy sai.')


STAGES = {'fit': ('pick', 'pay', 'done'), 'outfit': ('pick', 'pay', 'done'), 'alter': ('measure', 'sew', 'wait', 'ready', 'pay', 'done'),
          'room': ('room', 'pick', 'pay', 'done'), 'return': ('check', 'done'), 'sale': ('tag', 'done'), 'online': ('pack', 'done'),
          'display': ('dress', 'done')}


def validate_task(t: dict, original: dict) -> None:
    k = t.get('kind')
    kit.need(k in KINDS and t.get('gen') == original.get('gen'), 'Loại việc tiệm áo sai.')
    kit.need(t.get('stage') in STAGES[k], 'Bước làm việc sai.')
    kit.need(isinstance(t.get('picks'), list) and len(t['picks']) <= MAX_PICKS, 'Quầy sai.')
    for x in t['picks']:
        _valid_pick(x)
    kit.need(isinstance(t.get('tried'), list) and len(t['tried']) == len(t['picks'])
             and all(v in (None, 'ok', 'small', 'big') for v in t['tried']), 'Kết quả thử đồ sai.')
    kit.need(t.get('haggle') in (None, 'ask', 'hold', 'small', 'big'), 'Chuyện trả giá sai.')
    kit.need(t['haggle'] is None or original['needs'].get('haggle'), 'Khách này không trả giá.')
    b = t.get('bill')
    if b is not None:
        kit.need(isinstance(b, dict) and set(b) == {'lines', 'sub', 'off', 'total', 'sale'} and type(b['sale']) is bool, 'Bill sai.')
        kit.need(isinstance(b['lines'], list) and 1 <= len(b['lines']) <= MAX_PICKS, 'Bill sai.')
        for x in b['lines']:
            kit.need(isinstance(x, dict) and set(x) == {'label', 'item', 'size', 'colour', 'unit', 'qty', 'amount'}, 'Dòng bill sai.')
            kit.need(x['item'] is None or (x['item'] in ITEM and x['size'] in SIZES[x['item']] and x['colour'] in COLOURS[x['item']]), 'Dòng bill sai.')
            kit.text(x['label'], 80)
            kit.integer(x['unit'], 1, 10 ** 5)
            kit.integer(x['qty'], 1, 1)
            kit.need(x['amount'] == x['unit'] * x['qty'], 'Dòng bill sai.')
        kit.need(b['sub'] == sum(x['amount'] for x in b['lines']), 'Tổng bill sai.')
        kit.integer(b['off'], 0, b['sub'])
        kit.need(b['total'] == b['sub'] - b['off'], 'Tổng bill sai.')
    kit.need(t['stage'] != 'pay' or b is not None, 'Bill chưa chốt.')
    cash = t.get('cash')
    till.validate(cash, t)
    if cash is not None:
        kit.need(b is not None and cash['price'] == b['total'], 'Tiền khách đưa không khớp bill.')
    r = t.get('result')
    if r is not None:
        kit.need(isinstance(r, dict) and len(r) <= 6, 'Kết quả việc sai.')
        for key, v in r.items():
            kit.need(isinstance(key, str) and len(key) <= 12, 'Kết quả việc sai.')
            if key in ('choice', 'grade'):
                kit.need(v in ('refund', 'exchange', 'refuse', 'good', 'ok', 'bad'), 'Kết quả việc sai.')
            else:
                kit.integer(v, -10 ** 6, 10 ** 6)
    if k == 'alter':
        a = t.get('alt')
        kit.need(isinstance(a, dict) and set(a) == {'measured', 'cm', 'mode', 'cut', 'start', 'seam', 'sent'}, 'Phiếu sửa đồ sai.')
        kit.need(type(a['measured']) is bool and a['mode'] in (None, 'self', 'send') and a['seam'] in (None, 'good', 'crooked'), 'Phiếu sửa đồ sai.')
        kit.need(a['cm'] in (None, original['needs']['_cm']), 'Số đo bị sửa.')
        kit.need(a['cut'] is None or kit.integer(a['cut'], 1, 10), 'Số cm sai.')
        kit.need(a['start'] is None or (isinstance(a['start'], (int, float)) and not isinstance(a['start'], bool)), 'Giờ may sai.')
        kit.need(a['sent'] is None or kit.integer(a['sent'], 0, 10 ** 9) >= 0, 'Giờ gửi may sai.')
    if k == 'room':
        r = t.get('room')
        n = len(original['needs']['queue'])
        kit.need(isinstance(r, dict) and set(r) == {'i', 'tags', 'outs', 'checked', 'res'}, 'Phòng thử sai.')
        kit.integer(r['i'], 0, n)
        for key in ('tags', 'outs', 'res'):
            kit.need(isinstance(r[key], dict) and all(isinstance(x, str) and x.isdigit() and int(x) < n for x in r[key]), 'Phòng thử sai.')
        _ints(r['tags'].values(), 1, 6)
        _ints(r['outs'].values(), 0, 6)
        kit.need(all(v in ('ok', 'found', 'returned', 'lost', 'accused') for v in r['res'].values()), 'Phòng thử sai.')
        kit.need(isinstance(r['checked'], list) and all(type(x) is int and 0 <= x < n for x in r['checked']), 'Phòng thử sai.')
    if k == 'return':
        r = t.get('ret')
        kit.need(isinstance(r, dict) and set(r) == {'seen', 'choice', 'tone', 'new_size'}, 'Phiếu đổi trả sai.')
        kit.need(isinstance(r['seen'], list) and len(set(r['seen'])) == len(r['seen']) and all(x in FACTS for x in r['seen']), 'Phiếu đổi trả sai.')
        kit.need(r['choice'] in (None, 'refund', 'exchange', 'refuse') and r['tone'] in (None, 'calm', 'blunt'), 'Phiếu đổi trả sai.')
        kit.need(r['new_size'] is None or r['new_size'] in SIZES[original['needs']['item']], 'Size đổi sai.')
    if k == 'sale':
        sl = t.get('sale')
        n = len(original['needs']['lines'])
        kit.need(isinstance(sl, dict) and set(sl) == {'base', 'options', 'tags'}, 'Tờ sale sai.')
        kit.need(isinstance(sl['base'], dict) and set(sl['base']) <= {x['item'] for x in original['needs']['lines']}, 'Giá gốc sai.')
        _ints(sl['base'].values(), 1, 10 ** 5)
        kit.need(isinstance(sl['options'], list) and len(sl['options']) in (0, n), 'Giá tem sai.')
        for row in sl['options']:
            kit.need(isinstance(row, list) and 1 <= len(row) <= 4, 'Giá tem sai.')
            _ints(row, 1, 10 ** 5)
        kit.need(isinstance(sl['tags'], dict) and all(isinstance(x, str) and x.isdigit() and int(x) < n for x in sl['tags']), 'Tem sale sai.')
        for key, v in sl['tags'].items():
            kit.need(sl['options'] and v in sl['options'][int(key)], 'Tem sale sai.')
    if k == 'online':
        pc = t.get('parcel')
        kit.need(isinstance(pc, dict) and set(pc) == {'items', 'label', 'sealed'} and type(pc['sealed']) is bool, 'Gói hàng sai.')
        kit.need(isinstance(pc['items'], list) and len(pc['items']) <= MAX_PICKS, 'Gói hàng sai.')
        for x in pc['items']:
            _valid_pick(x)
        lb = pc['label']
        if lb is not None:
            kit.need(isinstance(lb, dict) and set(lb) == {'total', 'cod'}, 'Phiếu giao sai.')
            kit.integer(lb['total'], 0, 10 ** 6)
            kit.integer(lb['cod'], 0, 10 ** 6)
        kit.need(not pc['sealed'] or lb is not None, 'Gói dán khi chưa có phiếu.')
    if k == 'display':
        dp = t.get('disp')
        kit.need(isinstance(dp, dict) and set(dp) == {'pieces', 'steamed'}, 'Ma-nơ-canh sai.')
        kit.need(isinstance(dp['pieces'], list) and len(dp['pieces']) <= 4, 'Ma-nơ-canh sai.')
        for x in dp['pieces']:
            kit.need(isinstance(x, dict) and set(x) == {'item', 'colour'} and x['item'] in ITEM and x['colour'] in COLOURS[x['item']], 'Ma-nơ-canh sai.')
        kit.need(isinstance(dp['steamed'], list) and len(set(dp['steamed'])) == len(dp['steamed'])
                 and all(type(i) is int and 0 <= i < len(dp['pieces']) for i in dp['steamed']), 'Ma-nơ-canh sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _sync(c)
    till.validate_book(c)
    g = d['grid']
    kit.need(isinstance(g, dict) and set(g) == set(ITEM), 'Giá treo sai.')
    for item, row in g.items():
        kit.need(isinstance(row, dict) and set(row) == set(SIZES[item]), 'Giá treo sai size.')
        _ints(row.values(), 0, 10 ** 4)
    kit.need(isinstance(d['swaps'], list) and len(d['swaps']) <= 12, 'Danh sách đổi size sai.')
    for x in d['swaps']:
        kit.need(isinstance(x, dict) and set(x) == {'id', 'npc', 'item', 'colour', 'wrong', 'right', 'price', 'day', 'task'}, 'Đổi size sai.')
        kit.need(x['item'] in ITEM and x['wrong'] in SIZES[x['item']] and x['right'] in SIZES[x['item']] and x['colour'] in COLOURS[x['item']], 'Đổi size sai.')
        kit.need(isinstance(x['npc'], str) and x['npc'].startswith(ID + '_npc_'), 'Đổi size sai.')
        kit.text(x['id'], 20)
        kit.text(x['task'], 60)
        kit.integer(x['price'], 0, 10 ** 5)
        kit.integer(x['day'], 1, 10 ** 7)
    kit.need(isinstance(d['book'], dict) and len(d['book']) <= len(PEOPLE), 'Sổ khách quen sai.')
    for key, row in d['book'].items():
        kit.need(key.isdigit() and int(key) < len(PEOPLE) and isinstance(row, dict) and set(row) == {'top', 'waist', 'kid', 'visits'}, 'Sổ khách quen sai.')
        kit.need(row['top'] in (None, *LETTERS) and row['waist'] in (None, *SIZES['jeans']), 'Sổ khách quen sai.')
        kit.need(isinstance(row['kid'], list) and len(row['kid']) <= 3 and all(x in SIZES['kids'] for x in row['kid']), 'Sổ khách quen sai.')
        kit.integer(row['visits'], 0, 999)
    sale = d['sale']
    if sale is not None:
        kit.need(isinstance(sale, dict) and set(sale) == {'day', 'tags', 'pct'}, 'Đợt sale sai.')
        kit.integer(sale['day'], 1, 10 ** 7)
        kit.need(isinstance(sale['tags'], dict) and set(sale['tags']) <= set(ITEM) and isinstance(sale['pct'], dict) and set(sale['pct']) <= set(ITEM), 'Đợt sale sai.')
        _ints(sale['tags'].values(), 1, 10 ** 5)
        _ints(sale['pct'].values(), 1, 90)
    disp = d['display']
    if disp is not None:
        kit.need(isinstance(disp, dict) and set(disp) == {'day', 'score', 'theme', 'pieces', 'plus'} and disp['theme'] in OCCASIONS
                 and type(disp['plus']) is bool, 'Ma-nơ-canh sai.')
        kit.integer(disp['day'], 1, 10 ** 7)
        kit.integer(disp['score'], 1, 5)
        kit.need(isinstance(disp['pieces'], list) and len(disp['pieces']) <= 4, 'Ma-nơ-canh sai.')
        for x in disp['pieces']:
            kit.need(isinstance(x, dict) and set(x) == {'item', 'colour'} and x['item'] in ITEM and x['colour'] in COLOURS[x['item']], 'Ma-nơ-canh sai.')
    kit.need(type(d['intro']) is bool, 'Giới thiệu nghề sai.')
    kit.need(isinstance(d['notes'], list) and len(d['notes']) <= 12, 'Ghi chú sai.')
    for x in d['notes']:
        kit.need(isinstance(x, dict) and set(x) == {'day', 'text'}, 'Ghi chú sai.')
        kit.integer(x['day'], 0, 10 ** 7)
        kit.text(x['text'], 200)
    kit.integer(d['seq'], 0, 10 ** 9)
    kit.integer(d['day_sales'], 0, 10 ** 9)
    kit.need(isinstance(d['stats'], dict) and set(d['stats']) == set(STAT_KEYS), 'Thống kê tiệm sai.')
    _ints(d['stats'].values(), 0, 10 ** 9)


# ---------------------------------------------------------------- content for the browser
INTRO = dict(
    title='Tiệm Áo Chỉ Mây',
    story='Chị Vy mở lại tiệm may cũ của mẹ — Bà Tư — thành tiệm áo xinh xắn đầu hẻm. Bà Tư vẫn ngồi máy may ở gian bên. Chị cần thêm một người đứng tiệm: là bạn đó!',
    does=[('📏', 'Tìm đúng size, đúng màu theo lời khách tả'), ('👗', 'Phối đồ đi cưới, phỏng vấn, đi biển, du xuân'),
          ('🚪', 'Trông phòng thử: đưa thẻ số, đếm đồ vào ra'), ('✂️', 'Sửa đồ: lai quần, bóp eo, hoặc gửi Bà Tư'),
          ('🔁', 'Đổi trả đúng chính sách'), ('📦', 'Gói đơn Zalo/Facebook cho shipper'),
          ('🧍‍♀️', 'Hấp đồ, thay bộ cho ma-nơ-canh'), ('💵', 'Tính tiền, thối tiền cho đúng')],
    meets=[('🥷', 'Đồ “biến mất” trong phòng thử'), ('🎭', 'Khách mặc rồi mới đem trả'), ('🏷️', 'Mùa sale: tem giá phải tính cho đúng'),
           ('🧾', 'Dì Sáu trả giá, khách đếm lại tiền thối'), ('🔁', 'Lấy sai size: khách quay lại đổi')],
    stars=[('⭐', 'Vừa size ngay lần đầu, đúng màu khách dặn'), ('⭐', 'Bộ đồ hợp dịp, có điểm nhấn'),
           ('⭐', 'Thối tiền đúng, bill rõ từng dòng'), ('⭐', 'Nhẹ nhàng cả khi phải từ chối')],
)


def content() -> dict:
    return dict(
        sizes=SIZES, colours=COLOURS, swatch=SWATCH, groups=GROUP, base_prices=PRICES, denoms=till.DENOMS,
        top_chart=[list(r) for r in TOP_CHART], jeans_waist=JEANS_WAIST, kids_age={k: list(v) for k, v in KIDS_AGE.items()},
        runs_small=RUNS_SMALL, occasions={k: dict(name=v['name'], emoji=v['emoji'], tips=v['tips']) for k, v in OCCASIONS.items()},
        policy=POLICY, return_days=RETURN_DAYS, haggle=dict(small=HAGGLE_SMALL, big=HAGGLE_BIG), alter_fees=ALTER_FEES,
        tailor_share=TAILOR_SHARE, tailor_turns=TAILOR_TURNS, kinds=KIND_NAMES, looks=[dict(x) for x in LOOKS],
        intro=INTRO, ship_fee=SHIP_FEE, mods=[dict(id=m['id'], emoji=m['emoji'], name=m['name'], text=m['text']) for m in MODS])


SITUATIONS = [
    dict(id='AO-S01', title='Chiếc váy “chưa mặc lần nào”', npc=KIEU, tone='tense', min_day=3,
         opening='Chị Kiều đặt chiếc váy lên quầy: “Chị chưa mặc đâu, trả lại lấy tiền nha.” Cổ váy thoang thoảng mùi nước hoa.',
         swap='Bạn là chị Kiều: tiệc tối qua xong rồi, váy chỉ mặc có một lần thôi mà…',
         facts=[dict(id='tag', title='Tem mác', source='Quầy', text='Tem đã cắt, chỉ còn lỗ bấm.'),
                dict(id='smell', title='Tình trạng váy', source='Quầy', text='Cổ váy có vệt phấn, còn mùi nước hoa.'),
                dict(id='policy', title='Chính sách tiệm', source='Bảng dán ở quầy', text='Đổi trả trong 7 ngày, còn tem, chưa mặc.')],
         options=[dict(id='explain', label='Chỉ bảng chính sách, nhẹ nhàng từ chối, gợi ý dịch vụ giặt hấp giá rẻ', requires=['tag', 'policy'], quality='good', stars=4,
                       review='Không trả được nhưng em nói chuyện dễ chịu, còn chỉ chỗ giặt hấp. Thôi được.',
                       outcome='Chị Kiều hơi phụng phịu nhưng không cãi. Tuần sau chị quay lại mua váy mới.',
                       perspectives=[dict(who='Chị Kiều', emoji='💅', text='Bị bắt bài nhưng không bị làm quê, cũng nể.'),
                                     dict(who='Chị Vy', emoji='👩', text='Giữ chính sách mà vẫn giữ được khách, chuẩn.')]),
                  dict(id='accept', label='Thôi nhận lại cho êm chuyện', quality='bad', cost=40, stars=5,
                       review='Tiệm dễ thương ghê, đổi trả không làm khó 😘',
                       outcome='Váy có mùi nước hoa không bán được nữa. Tiệm lỗ nguyên chiếc.',
                       perspectives=[dict(who='Chị Vy', emoji='😮‍💨', text='Một lần là thành lệ, chị ấy sẽ còn “mượn” nữa.'),
                                     dict(who='Bà Tư', emoji='🧵', text='Vải mặc rồi thì hết là đồ mới con à.')]),
                  dict(id='shame', label='Nói to: “Đồ mặc rồi còn đem trả!”', quality='bad', stars=1,
                       review='Nhân viên tiệm này la khách giữa tiệm. Không bao giờ quay lại.',
                       outcome='Mấy khách đang lựa đồ ngại ngùng bỏ ra ngoài.',
                       perspectives=[dict(who='Chị Diễm', emoji='😬', text='Đúng là chị ấy sai, nhưng nghe la vậy tôi cũng ngại.'),
                                     dict(who='Chị Kiều', emoji='😤', text='Bị làm nhục trước bao nhiêu người!')])],
         lesson='Giữ đúng chính sách đổi trả, nhưng từ chối riêng tư và nhẹ nhàng.'),
    dict(id='AO-S02', title='Tuấn chỉ đủ tiền cho nửa bộ', npc=TUAN, tone='gentle', min_day=2,
         opening='Tuấn đếm tiền trong ví: “Em chỉ còn 400 xu mà mai phỏng vấn rồi…”',
         facts=[dict(id='budget', title='Ví của Tuấn', source='Tuấn', text='Còn 400 xu, tuần sau mới có lương thực tập.'),
                dict(id='need', title='Bộ tối thiểu', source='Bảng giá', text='Sơ mi 220 xu, quần jean 280 xu. Tuấn đã có quần tây đen ở nhà.'),
                dict(id='lend', title='Góc cho mượn của Bà Tư', source='Bà Tư', text='Bà Tư có mấy chiếc cà vạt cũ, sạch sẽ, sẵn lòng cho mượn.')],
         options=[dict(id='shirt', label='Chỉ bán sơ mi, phối với quần tây sẵn có, mượn cà vạt của Bà Tư', requires=['need', 'lend'], quality='good', stars=5,
                       review='Chị tư vấn đúng cái em cần, không ép mua thêm. Em đậu rồi nè! 🎉',
                       outcome='Tuấn mặc sơ mi mới với quần tây ở nhà, đeo cà vạt của Bà Tư. Tuần sau cậu quay lại khoe đậu phỏng vấn.',
                       perspectives=[dict(who='Tuấn', emoji='🧑‍🎓', text='Đỡ lo tiền, tự tin hẳn.'),
                                     dict(who='Bà Tư', emoji='🧵', text='Cà vạt nằm tủ mấy năm, giờ có người đeo đi làm.')]),
                  dict(id='credit', label='Bán cả bộ, cho Tuấn ghi nợ phần thiếu', requires=['budget'], quality='ok', stars=4, cost=0,
                       review='Chị cho em nợ, em cảm động lắm, lãnh lương em trả liền.',
                       outcome='Tuấn trả đủ sau hai tuần. Chị Vy dặn: lần sau ghi sổ rõ ràng.',
                       perspectives=[dict(who='Chị Vy', emoji='👩', text='Tin người là tốt, nhưng tiệm nhỏ cũng phải có sổ.')]),
                  dict(id='upsell', label='Khuyên Tuấn mua cả bộ mới cho “chuẩn”', quality='bad', stars=2,
                       review='Em hết tiền ăn cả tuần vì mua bộ đồ này…',
                       outcome='Tuấn mua cả bộ, cả tuần ăn mì gói.',
                       perspectives=[dict(who='Tuấn', emoji='😔', text='Đẹp thật, nhưng em đói.'), dict(who='Chị Hằng', emoji='👩‍👧', text='Tư vấn là phải nhìn túi tiền của người ta chứ.')])],
         lesson='Tư vấn tốt là giúp khách đủ dùng, không phải bán được nhiều nhất.'),
    dict(id='AO-S03', title='Áo dài cưới rộng eo lúc nửa đêm', npc=BA_NAM, tone='tense', min_day=5,
         opening='Chín giờ tối, Bà Năm gọi: “Mai rước dâu mà áo dài con Út rộng eo, tiệm cứu bà với!”',
         facts=[dict(id='time', title='Thời gian', source='Đồng hồ', text='Tiệm đã đóng cửa, sáng mai 7 giờ nhà trai tới.'),
                dict(id='tu', title='Bà Tư', source='Gian bên', text='Bà Tư còn thức, nhưng mắt mỏi, sửa khuya dễ sai.'),
                dict(id='measure', title='Số đo', source='Bà Năm', text='Bà Năm không nhớ số đo, chỉ nói “bóp chút xíu”.')],
         options=[dict(id='early', label='Hẹn 5 giờ sáng, cô dâu ghé mặc thử, đo tại chỗ rồi bóp', requires=['measure', 'time'], quality='good', stars=5,
                       review='Tiệm mở cửa từ 5 giờ sáng để sửa áo cho con gái tôi. Cả nhà biết ơn!',
                       outcome='Cô dâu mặc thử, Bà Tư ghim hai bên hông, bạn may. Áo vừa như in trước giờ rước dâu.',
                       perspectives=[dict(who='Bà Năm', emoji='👵', text='Bà cảm động muốn khóc.'), dict(who='Bà Tư', emoji='🧵', text='Đo tận người mới may chuẩn được.')]),
                  dict(id='guess', label='Bóp đại 3 phân ngay trong đêm', quality='bad', stars=2,
                       review='Bóp chật quá, con tôi mặc mà nín thở suốt buổi.',
                       outcome='Không đo nên bóp quá tay. Sáng ra phải nới vội.',
                       perspectives=[dict(who='Cô Út', emoji='👰', text='Đẹp mà thở không nổi.')]),
                  dict(id='no', label='Từ chối vì tiệm đã đóng cửa', quality='ok', stars=3,
                       review='Tiệm đóng cửa thì thôi, nhà tôi tự xoay xở.',
                       outcome='Bà Năm nhờ người khác, áo hơi rộng nhưng vẫn mặc được.',
                       perspectives=[dict(who='Chị Vy', emoji='👩', text='Đúng giờ giấc, nhưng tiếc một khách quen.')])],
         lesson='Sửa đồ phải đo trên người mặc; gấp mấy cũng đừng đoán số đo.'),
    dict(id='AO-S04', title='Khách chụp ảnh áo rồi đặt shop online rẻ hơn', npc=DIEM, tone='gentle', min_day=3,
         opening='Chị Diễm thử ba cái sơ mi, chụp tem giá rồi nói: “Trên mạng có cái y chang, rẻ hơn 50 xu.”',
         facts=[dict(id='fabric', title='Chất vải', source='Tem vải', text='Sơ mi của tiệm là cotton lụa, đường may kỹ, bảo hành bung chỉ.'),
                dict(id='alter', title='Dịch vụ tiệm', source='Chị Vy', text='Mua ở tiệm được sửa lai, bóp eo miễn phí lần đầu.'),
                dict(id='online', title='Hàng trên mạng', source='Điện thoại chị Diễm', text='Ảnh mẫu giống, không ghi chất vải, đổi trả tốn phí ship.')],
         options=[dict(id='value', label='Cho chị sờ vải, nói về sửa miễn phí và bảo hành, không hạ giá', requires=['fabric', 'alter'], quality='good', stars=5,
                       review='Nhân viên giải thích kỹ, được sửa miễn phí nên tôi mua luôn ở tiệm.',
                       outcome='Chị Diễm mua hai cái, còn nhờ bóp eo một cái.',
                       perspectives=[dict(who='Chị Diễm', emoji='👩‍💼', text='Mua đồ mặc đi làm, vừa người là quan trọng nhất.')]),
                  dict(id='cut', label='Hạ giá bằng trên mạng cho chốt đơn', quality='ok', stars=4, cost=50,
                       review='Được giảm giá, vui.', outcome='Bán được nhưng gần như không lời.',
                       perspectives=[dict(who='Chị Vy', emoji='😮‍💨', text='Đua giá với mạng thì tiệm nhỏ thua chắc.')]),
                  dict(id='sulk', label='Nói “Vậy chị lên mạng mà mua”', quality='bad', stars=1,
                       review='Hỏi giá thôi mà bị đuổi khéo. Thôi mua mạng cho rồi.',
                       outcome='Chị Diễm bỏ đi, còn kể cho cả phòng.',
                       perspectives=[dict(who='Chị Diễm', emoji='😒', text='Tôi chỉ muốn được thuyết phục thôi mà.')])],
         lesson='Cạnh tranh bằng giá trị: chất liệu, sửa đồ, đổi trả dễ — không phải bằng hạ giá.'),
    dict(id='AO-S05', title='Mẹ con chị Hằng làm đổ ly trà sữa lên váy mới', npc=HANG, tone='gentle', min_day=2,
         opening='Bé út nhà chị Hằng cầm ly trà sữa chạy quanh tiệm, vấp ngã, trà sữa văng lên chiếc váy trắng đang treo.',
         facts=[dict(id='stain', title='Vết bẩn', source='Giá treo', text='Váy trắng dính trà sữa, còn tem. Giặt ngay có thể sạch.'),
                dict(id='hang', title='Chị Hằng', source='Chị Hằng', text='Chị rối rít xin lỗi, bé đang khóc vì sợ.'),
                dict(id='price', title='Giá váy', source='Tem', text='Váy 260 xu, giá vốn 115 xu.')],
         options=[dict(id='calm', label='Dỗ bé trước, giặt ngay vết bẩn, chỉ nhờ chị Hằng góp tiền giặt hấp nếu không sạch', requires=['stain', 'hang'], quality='good', stars=5,
                       review='Bé nhà tôi làm bẩn váy mà tiệm dỗ bé trước, không làm lớn chuyện. Cảm ơn tiệm!',
                       outcome='Vết bẩn ra hết. Chị Hằng mua thêm hai bộ đồ cho tụi nhỏ.',
                       perspectives=[dict(who='Chị Hằng', emoji='👩‍👧', text='Tôi ngại muốn độn thổ, may mà tiệm dễ thương.'), dict(who='Bà Tư', emoji='🧵', text='Vết trà sữa giặt liền là sạch.')]),
                  dict(id='full', label='Bắt đền nguyên giá chiếc váy', quality='ok', stars=2, reward=0,
                       review='Làm bẩn thì đền, đúng. Nhưng chưa giặt thử đã bắt đền nguyên giá…',
                       outcome='Chị Hằng đền, nhưng từ đó ít ghé.',
                       perspectives=[dict(who='Chị Hằng', emoji='😔', text='Đền thì đền, mà buồn.')]),
                  dict(id='ignore', label='Kệ, treo váy lại bán tiếp', quality='bad', stars=2,
                       review='Mua váy về mới thấy vết ố ở vạt sau.',
                       outcome='Khách khác mua phải váy dính vết ố, quay lại trả.',
                       perspectives=[dict(who='Chị Vy', emoji='😠', text='Bán đồ bẩn cho khách là mất uy tín.')])],
         lesson='Sự cố nhỏ: lo cho người trước, xử lý vết bẩn ngay, chỉ đòi bồi thường khi thật sự hư hỏng.'),
]

SPEC = dict(
    id=ID, prefix=PREFIX, category='shop',
    meta=dict(short='Shop quần áo', place='Tiệm Áo Chỉ Mây', tagline='Đúng size. Đúng dáng. Đúng dịp.', icon='bag',
              color='#6a58a6', light='#f1edfa', weather='Nắng nhẹ qua cửa kính', work='Khách', station='Giá treo & quầy',
              greeting='Tìm đúng size, phối đúng dịp, trông phòng thử và thối tiền cho đúng nhé.',
              caption='Tiệm may cũ của mẹ, khoác áo mới', map_label='21 · TIỆM ÁO CHỈ MÂY'),
    people=PEOPLE,
    staff=[('Mai', 'ao_floor', 'Nhớ size từng khách quen, gấp áo nhanh như máy.', 82, 84),
           ('Khoa', 'ao_pack', 'Đóng gói đơn online gọn gàng, ghi phiếu không sót chữ nào.', 78, 90),
           ('Thư', 'ao_steam', 'Cầm bàn ủi hơi như cầm cọ vẽ, phối ma-nơ-canh có gu.', 74, 88),
           ('Lộc', 'ao_floor', 'Vui tính, khách vào là có người đon đả.', 88, 76)],
    roles={'ao_floor': 'Phụ bán & phòng thử', 'ao_pack': 'Đóng gói đơn online', 'ao_steam': 'Ủi hơi & trưng bày'},
    inventory=dict(items=ITEMS, capacity=CAPACITY),
    prices=PRICES,
    tip=2,
    physical=('ao_pick', 'ao_try', 'ao_pay', 'ao_measure', 'ao_sew_start', 'ao_steam', 'ao_pack', 'ao_ship', 'ao_room_check',
              'ao_return_do', 'ao_dress', 'ao_swap'),
    free_actions=('ao_intro',),
    no_tick=('ao_intro', 'ao_short', 'ao_haggle', 'ao_unpick', 'ao_sew_stop', 'ao_tag', 'ao_unpack', 'ao_undress', 'ao_unbill', 'ao_inspect'),
    waste_items=(),
    activity=('🧵', 'Giá treo gọn gàng', [('Áo thun', 'Giá áo'), ('Quần jean', 'Kệ quần'), ('Váy liền', 'Giá váy'), ('Nón vành', 'Kệ phụ kiện')],
              ['Đo số đo khách', 'Chọn đúng size', 'Mời khách thử', 'Tính tiền, thối đúng']),
    stories=[('Tiệm may của mẹ', ('Chị Vy đưa bạn chìa khóa tiệm: “Hồi nhỏ chị ngủ trưa dưới cái bàn cắt vải này đó.”',
                                  'Bà Tư lau chiếc máy may đạp chân, dặn: “Đo hai lần, cắt một lần nghe con.”',
                                  'Bảng hiệu mới treo lên, Bà Tư đứng ngắm lâu thật lâu rồi cười: “Đẹp. Mà vẫn là tiệm của mình.”')),
             ('Bộ đồ phỏng vấn của Tuấn', ('Tuấn đếm từng đồng trong ví, bạn chọn cho cậu một chiếc sơ mi vừa túi tiền.',
                                           'Tuấn chạy vào tiệm, thở hổn hển: “Em đậu rồi chị ơi!”',
                                           'Tháng lương đầu, Tuấn mua tặng Bà Tư hộp kim chỉ mới.')),
             ('Đám cưới con Út', ('Bà Năm dắt cả nhà tới chọn đồ đám hỏi, cái gì cũng phải “đẹp mặt”.',
                                  'Đêm trước ngày cưới, áo dài cô dâu rộng eo, cả tiệm thức khuya sửa.',
                                  'Bà Năm mang tới một hộp bánh cưới: “Cả xóm khen áo đẹp, bà cảm ơn tiệm.”'))],
    review_asides=['Mặc vừa như may đo 👌', 'Tiệm nhỏ mà tư vấn có gu ghê.', 'Bill rõ từng dòng, thối tiền đếm kỹ.',
                   'Phòng thử sạch, có thẻ số đàng hoàng.'],
    situations=SITUATIONS,
    guide='Nghe khách → chọn đúng size, màu, hợp dịp → mời thử khi chưa chắc → chốt bill → thối đúng tiền.',
)
