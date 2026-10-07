"""Static content of the ZPOP album shop (game/careers/zpop.py): Tiệm album Mây Pop, chị Thơ's little shop of
albums and fan goods on Phố chợ.

Everything here is fiction. The groups are light parodies of the idol world, never real people: BLANKPINK (a
four-member girl group whose members are named after snacks), 7GIÓ (seven boys named after Vietnam's winds) and the
rookies KIWIZ (five sour fruits). Album titles, the "Búa hồng" lightstick, the BLINKY fandom, the Bảng Zchart sales
board, the distributor and the other stores are made up. Art is emoji and canvas shapes only.

What the player meets: album versions with random inclusions (photocard of one member, poster, a lucky draw) and the
one version whose card is sure; customers who want a member's card, a sealed copy, the poster rolled, the receipt
scanned for Zchart, a fansign entry, the shop's pre-order benefit (POB), a lightstick with the right batteries; and the
annoying ones: the card trader who wants to open albums before paying, the parent who does not know the group, the
chart buyer who wants only receipts, the reseller after every limited copy, the refund for the "wrong" member, the
queue on comeback day, a pre-order picked up under another name, the lightstick that will not pair, a fake lightstick
"under warranty", bootleg albums offered on consignment, and the fan who asks you to promise a fansign win.
"""
from __future__ import annotations

# ---------------------------------------------------------------- the groups (fictional)
GROUPS = {
    'bp': dict(name='BLANKPINK', emoji='🩷', fandom='BLINKY', label='nhóm nữ 4 thành viên', stick='Búa hồng'),
    'g7': dict(name='7GIÓ', emoji='🌬️', fandom='Diều', label='nhóm nam 7 thành viên'),
    'kw': dict(name='KIWIZ', emoji='🥝', fandom='Kiwi Kiwi', label='nhóm nữ tân binh 5 thành viên'),
}
MEMBERS = {
    'bp': (('bori', 'Bơ-Ri', '🥑'), ('manji', 'Mận-Ji', '🍑'), ('suaah', 'Sữa-Ah', '🥛'), ('hongbi', 'Hồng-Bi', '🌷')),
    'g7': (('bac', 'Bấc', '❄️'), ('nom', 'Nồm', '💧'), ('heomay', 'Heo May', '🍂'), ('lao', 'Lào', '🔥'), ('chuong', 'Chướng', '🌊'),
           ('mua', 'Mùa', '🌧️'), ('loc', 'Lốc', '🌀')),
    'kw': (('kiwi', 'Kiwi', '🥝'), ('chanh', 'Chanh', '🍋'), ('me', 'Me', '🫘'), ('coc', 'Cóc', '🟢'), ('sau', 'Sấu', '🍏')),
}
ALBUMS = {
    'ps': dict(group='bp', name='PINK STATIC', kind='mini album thứ 3', emoji='💿', fansign=True),
    'kb': dict(group='bp', name='Kẹo Bông', kind='single album cũ', emoji='🍭'),
    'gm': dict(group='g7', name='Gió Mùa', kind='full album', emoji='🌬️'),
    'cc': dict(group='kw', name='Chua Chua', kind='album debut', emoji='🥝', fansign=True),
}
STORE = 'Mây Pop'                  # this shop
OTHER_STORES = ('Ziniverse', 'Kpo Kho', 'Sao Băng Record')
DISTRIBUTOR = 'nhà phân phối Sóng Âm'
CHART = 'Bảng Zchart'
FANSIGN_SLOTS = 30                 # winners of a fansign draw


def _sku(id, name, short, emoji, group, unit, cost, price, start, **kw):
    return dict(id=id, name=name, short=short, emoji=emoji, group=group, unit=unit, cost=cost, price=price, start=start, **kw)


# Every product is an inventory item (game/inventory.py: bought in the Kho at `cost`, sold at `price`, never expires).
SKUS = [
    _sku('ps_pink', 'PINK STATIC · Pink ver', 'Pink ver', '💗', 'album', 'bản', 14, 20, 10, album='ps', poster=True,
         tag='Pink', inside='CD · 1 card ngẫu nhiên (1/4) · poster gập'),
    _sku('ps_blank', 'PINK STATIC · Blank ver', 'Blank ver', '🤍', 'album', 'bản', 14, 20, 10, album='ps', poster=True,
         tag='Blank', inside='CD · 1 card ngẫu nhiên (1/4) · poster gập'),
    _sku('ps_jewel', 'PINK STATIC · Jewel case', 'Jewel case', '💎', 'album', 'bản', 10, 15, 6, album='ps', limited=True,
         tag='Jewel', inside='Hộp nhựa · bìa 1 thành viên ngẫu nhiên · 1 card ngẫu nhiên'),
    _sku('ps_digi_bori', 'PINK STATIC · Digipack Bơ-Ri', 'Digipack Bơ-Ri', '🥑', 'album', 'bản', 9, 13, 3, album='ps', member='bori',
         tag='Bơ-Ri', inside='Bìa Bơ-Ri · card Bơ-Ri chắc chắn'),
    _sku('ps_digi_manji', 'PINK STATIC · Digipack Mận-Ji', 'Digipack Mận-Ji', '🍑', 'album', 'bản', 9, 13, 3, album='ps', member='manji',
         tag='Mận-Ji', inside='Bìa Mận-Ji · card Mận-Ji chắc chắn'),
    _sku('ps_digi_suaah', 'PINK STATIC · Digipack Sữa-Ah', 'Digipack Sữa-Ah', '🥛', 'album', 'bản', 9, 13, 3, album='ps', member='suaah',
         tag='Sữa-Ah', inside='Bìa Sữa-Ah · card Sữa-Ah chắc chắn'),
    _sku('ps_digi_hongbi', 'PINK STATIC · Digipack Hồng-Bi', 'Digipack Hồng-Bi', '🌷', 'album', 'bản', 9, 13, 3, album='ps', member='hongbi',
         tag='Hồng-Bi', inside='Bìa Hồng-Bi · card Hồng-Bi chắc chắn'),
    _sku('ps_open', 'PINK STATIC · hàng trưng bày đã khui', 'Đã khui (trưng bày)', '📭', 'album', 'bản', 14, 12, 2, album='ps', opened=True,
         tag='Khui', inside='Đã khui · đủ CD và card · không còn poster'),
    _sku('kb_std', 'Kẹo Bông · single cũ', 'Kẹo Bông', '🍭', 'album', 'bản', 10, 15, 3, album='kb', tag='', inside='CD · 1 card ngẫu nhiên'),
    _sku('gm_sang', 'Gió Mùa · Sáng ver', 'Sáng ver', '🌅', 'album', 'bản', 14, 20, 5, album='gm', tag='Sáng', inside='CD · photobook · 1 card (1/7)'),
    _sku('gm_dem', 'Gió Mùa · Đêm ver', 'Đêm ver', '🌙', 'album', 'bản', 14, 20, 5, album='gm', tag='Đêm', inside='CD · photobook · 1 card (1/7)'),
    _sku('gm_kit', 'Gió Mùa · Kit ver', 'Kit ver', '🔑', 'album', 'bản', 9, 14, 4, album='gm', nocd=True,
         tag='Kit', inside='Thẻ QR tải nhạc · KHÔNG có đĩa CD · 1 card'),
    _sku('cc_std', 'Chua Chua · album debut', 'Chua Chua', '🥝', 'album', 'bản', 12, 17, 6, album='cc', tag='', inside='CD · 1 card (1/5) · sticker'),
    _sku('bua1', 'Búa hồng ver.1', 'Búa ver.1', '🔨', 'stick', 'cây', 30, 42, 3, pin='pin_aaa', tag='Ver.1', inside='Ăn 3 pin AAA (không kèm) · không Bluetooth'),
    _sku('bua2', 'Búa hồng ver.2', 'Búa ver.2', '📶', 'stick', 'cây', 45, 62, 3, pin='pin_aa', bt=True,
         tag='Ver.2', inside='Ăn 3 pin AA (không kèm) · Bluetooth ghép ghế concert'),
    _sku('pin_aaa', 'Vỉ 3 pin AAA', 'Pin AAA', '🔋', 'phukien', 'vỉ', 1, 3, 10, tag='AAA', inside='Pin nhỏ, cho Búa ver.1'),
    _sku('pin_aa', 'Vỉ 3 pin AA', 'Pin AA', '🔋', 'phukien', 'vỉ', 1, 3, 10, tag='AA', inside='Pin to, cho Búa ver.2'),
    _sku('binder', 'Sổ đựng card A5', 'Binder', '📒', 'phukien', 'cuốn', 10, 16, 4, tag='Binder', inside='20 trang, 4 ô một trang'),
    _sku('toploader', 'Bọc card cứng (gói 5)', 'Toploader', '🪟', 'phukien', 'gói', 2, 4, 12, tag='Toploader', inside='Gói 5 bọc nhựa cứng'),
    _sku('slogan', 'Slogan vải BLANKPINK', 'Slogan', '🎀', 'phukien', 'cái', 6, 10, 4, tag='Slogan', inside='Hàng chính hãng, có tem'),
    _sku('ong_poster', 'Ống cuộn poster', 'Ống poster', '🧻', 'phukien', 'ống', 1, 0, 10, service=True,
         tag='Ống', inside='Cuộn poster cho khách, tiệm tặng'),
]
SKU = {x['id']: x for x in SKUS}
SELL = tuple(x['id'] for x in SKUS if not x.get('service'))      # what the shelves show and the till charges
PRICES = {x['id']: x['price'] for x in SKUS if x['price']}

# ---------------------------------------------------------------- the people
PEOPLE = [
    ('Chị Thơ', 'Chủ tiệm Mây Pop', 'Từng làm trưởng fanclub mười năm rồi mở tiệm album; thuộc lịch comeback của mọi nhóm.', 'warm'),
    ('Na', 'BLINKY bảy năm, bias Mận-Ji', 'Để dành tiền ăn sáng mua album, đòi poster cuộn, quét Zchart từng bản.', 'genz'),
    ('Cô Hạnh', 'Mẹ của bé Bống lớp 6', 'Mua quà cho con mà không phân biệt nổi nhóm này với nhóm kia.', 'quiet'),
    ('Tuấn Card', 'Dân trao đổi photocard', 'Mê khui album tại chỗ, thuộc giá từng tấm card hơn thuộc bài.', 'picky'),
    ('Anh Dũng', 'Trưởng nhóm đẩy chart', 'Mua sỉ cho Bảng Zchart, nói chuyện bằng số liệu.', 'bossy'),
    ('Chị Kiều', 'Hay “mua giùm em gái”', 'Điện thoại ba sim, chuyên gom bản giới hạn đem bán lại.', 'sour'),
    ('Mít', 'Học sinh lớp 9, fan 7GIÓ', 'Fan cứng 7GIÓ, mê lightstick, hỏi mười câu mới mua một món.', 'genz'),
]


# ---------------------------------------------------------------- the orders
def _l(any_, qty, label, code=''):
    """One thing the customer wants: any of these products, how many, in the customer's words; `code` names the trap
    (bias: only one version has the member's card for sure, cd, battery, cheap)."""
    return dict(any=list(any_) if isinstance(any_, (tuple, list)) else [any_], qty=qty, label=label, code=code)


def _o(npc, title, say, lines, *, note='', zchart=False, tube=False, raffle=False, pob=False, tw=None, tw_w=None,
       min_day=1, mod=None, weight=1, upto=False, guess=None, book=None):
    return dict(npc=npc, title=title, say=say, lines=lines, note=note, zchart=zchart, tube=tube, raffle=raffle, pob=pob,
                tw=tw, tw_w=tw_w, min_day=min_day, mod=mod, weight=weight, upto=upto, guess=guess, book=book)


ORDERS = [
    # day 1: plain asks, each with one trap
    _o(1, 'Na săn card Mận-Ji', 'Chị ơi PINK STATIC, em cần CHẮC CHẮN có card Mận-Ji nha!',
       [_l('ps_digi_manji', 1, 'PINK STATIC chắc card Mận-Ji', 'bias')], zchart=True,
       note='Na: “Quét Zchart giùm em, bias em phải lên top!”'),
    _o(6, 'Mít mua quà cho ba', 'Album Gió Mùa bản nào có đĩa CD vậy chị? Ba em chỉ nghe đĩa trên xe.',
       [_l(('gm_sang', 'gm_dem'), 1, 'Gió Mùa có đĩa CD', 'cd')], note='Mít: “Sáng hay Đêm gì cũng được, miễn có CD.”'),
    _o(2, 'Cô Hạnh mua quà cho bé Bống', 'Con gái cô dặn mua album gì đó màu hồng… cô không rành, con coi giùm.',
       [_l('ps_pink', 1, 'PINK STATIC bản Pink'), _l('toploader', 2, '2 gói bọc card')], tw='parent', guess='ps_open',
       note='Giấy nhắn của Bống: “PINK STATIC Pink ver + 2 gói toploader. Mẹ đừng lấy bản đã khui nha!”'),
    # later
    _o(6, 'Mít sưu tầm card 7GIÓ', 'Chị ơi một binder với ba gói toploader, em xếp card 7GIÓ.',
       [_l('binder', 1, '1 binder'), _l('toploader', 3, '3 gói bọc card')], min_day=2),
    _o(1, 'Na đi concert tối nay', 'Em lấy Búa hồng bản có Bluetooth, lắp pin sẵn giùm em!',
       [_l('bua2', 1, 'Búa hồng có Bluetooth', 'bt'), _l('pin_aa', 1, 'Pin vừa cây búa đó', 'battery')], min_day=2,
       note='Na: “Tối nay concert, ghép ghế B12 luôn!”'),
    _o(6, 'Mít mua búa loại rẻ', 'Búa hồng loại rẻ thôi chị, kèm pin luôn nha.',
       [_l('bua1', 1, 'Búa hồng loại rẻ', 'cheap'), _l('pin_aaa', 1, 'Pin vừa cây búa đó', 'battery')], min_day=2),
    _o(1, 'Na thiếu một bản', 'Kẹo Bông bản cũ còn không chị? Em thiếu đúng bản này trong bộ sưu tập.',
       [_l('kb_std', 1, 'Kẹo Bông (single cũ)')], min_day=2, note='Na: “Có là em mừng xỉu luôn á.”'),
    _o(6, 'Mít hết tiền tiêu vặt', 'PINK STATIC bản nào rẻ nhất chị, khui rồi cũng được.',
       [_l('ps_open', 1, 'PINK STATIC rẻ nhất, khui rồi cũng được', 'cheap')], min_day=2),
    _o(6, 'Mít mê nhóm tân binh', 'Chua Chua của KIWIZ, hai bản, ghi phiếu fansign debut cho em!',
       [_l('cc_std', 2, '2 bản Chua Chua')], raffle=True, min_day=2),
    _o(4, 'Anh Dũng mua đúng tuần chart', 'Bốn bản Blank, quét Zchart từng bản, in hóa đơn đầy đủ để anh báo nhóm.',
       [_l('ps_blank', 4, '4 bản Blank')], zchart=True, min_day=2),
    _o(3, 'Tuấn mua đúng luật', 'Hai bản Jewel, đúng giới hạn chưa em? Anh mua đúng luật nha.',
       [_l('ps_jewel', 2, '2 bản Jewel (giới hạn)')], min_day=2),
    _o(1, 'Na mua giùm bạn', 'Bạn em bias Hồng-Bi, chắc chắn có card Hồng-Bi nha chị. Quét Zchart luôn!',
       [_l('ps_digi_hongbi', 1, 'PINK STATIC chắc card Hồng-Bi', 'bias')], zchart=True, min_day=3),
    _o(1, 'Na giữ poster', 'Hai bản Pink, poster cuộn giùm em, gập một nếp là em khóc đó!',
       [_l('ps_pink', 2, '2 bản Pink')], tube=True, min_day=2, note='Na: “Poster để dán tường phòng, không được có nếp!”'),
    # the annoying ones
    _o(3, 'Tuấn đòi khui tại quầy', 'Cho anh ba bản Pink, khui luôn ở đây coi card nha.',
       [_l('ps_pink', 3, '3 bản Pink')], tw='trader', min_day=2),
    _o(4, 'Anh Dũng đẩy chart', 'Tuần chart rồi em. Anh lấy hết Pink với Blank, tối đa 30 bản, quét Zchart từng bản.',
       [_l(('ps_pink', 'ps_blank'), 30, 'Pink/Blank, còn bao nhiêu lấy bấy nhiêu (tối đa 30)')], tw='bulk', zchart=True, upto=True,
       min_day=4),
    _o(5, 'Chị Kiều gom bản giới hạn', 'Lấy chị mười bản Jewel case, chị mua giùm em gái.',
       [_l('ps_jewel', 10, '10 bản Jewel (giới hạn)')], tw='reseller', min_day=3),
    _o(2, 'Cô Hạnh mua búa cho Bống', 'Bống đòi cái búa phát sáng đi xem ca nhạc, loại ghép được ghế đó con.',
       [_l('bua2', 1, 'Búa hồng có Bluetooth', 'bt'), _l('pin_aa', 1, 'Pin vừa cây búa đó', 'battery')], tw='parent', guess='bua1',
       note='Bống nhắn: “Búa hồng ver.2 kèm pin AA nha mẹ. KHÔNG mua slogan!”', min_day=3),
    _o(2, 'Cô Hạnh nhầm nhóm', 'Bống thích nhóm gì có gió gió… mà cô thấy cái hồng này đẹp hơn.',
       [_l('gm_dem', 1, 'Gió Mùa bản Đêm')], tw='parent', guess='ps_pink',
       note='Bống nhắn: “Gió Mùa bản Đêm của 7GIÓ nha mẹ, KHÔNG phải BLANKPINK!”', min_day=4),
    _o(6, 'Mít lấy hàng đặt trước giùm', 'Em lấy hai bản Jewel đặt trước của chị Thảo nha, chị nhờ em.',
       [_l('ps_jewel', 2, '2 Jewel đặt trước của Thảo')], tw='pickup', tw_w={'friend': 3, 'stranger': 1}, pob=True, min_day=4,
       book=dict(name='Nguyễn Thị Thảo', phone='4821', code='MP-117', qty=2)),
    _o(5, 'Chị Kiều lấy hàng đặt trước', 'Hàng đặt trước của Thảo đó em, hai bản Jewel. Chị là chị họ nó.',
       [_l('ps_jewel', 2, '2 Jewel đặt trước của Thảo')], tw='pickup', tw_w={'friend': 1, 'stranger': 3}, pob=True, min_day=5,
       book=dict(name='Nguyễn Thị Thảo', phone='4821', code='MP-117', qty=2)),
    _o(1, 'Na hỏi tỉ lệ fansign', 'Chị ơi mua năm bản Pink thì chắc trúng fansign không? Chị nói thật đi.',
       [_l(('ps_pink', 'ps_blank'), 5, '5 bản Pink hoặc Blank')], tw='odds', raffle=True, min_day=3),
    _o(3, 'Tuấn đòi POB tiệm khác', 'Bản Blank, kèm POB bên Ziniverse nha, anh thích bộ card đó hơn.',
       [_l('ps_blank', 1, '1 bản Blank')], tw='pob_other', min_day=3),
    # day kinds
    _o(1, 'Na nộp phiếu fansign', 'Comeback rồi chị ơi! Ba bản Jewel, ghi phiếu fansign, quét Zchart, cho em POB nữa!',
       [_l('ps_jewel', 3, '3 bản Jewel (giới hạn)')], zchart=True, raffle=True, pob=True, mod='comeback', min_day=3),
    _o(1, 'Na xếp hàng từ sáu giờ', 'Xếp từ sáu giờ sáng đó chị! Hai Pink, hai Blank, quét Zchart, poster cuộn giùm em.',
       [_l('ps_pink', 2, '2 bản Pink'), _l('ps_blank', 2, '2 bản Blank')], tw='queue_cut', zchart=True, tube=True, pob=True,
       mod='comeback', min_day=3),
    _o(3, 'Tuấn canh comeback', 'Hai Jewel, hai Digipack Sữa-Ah. POB nhớ đưa đủ nha.',
       [_l('ps_jewel', 2, '2 bản Jewel (giới hạn)'), _l('ps_digi_suaah', 2, '2 Digipack Sữa-Ah')], pob=True, mod='comeback', min_day=3),
    _o(6, 'Mít cosplay Hồng-Bi', 'Em cosplay Hồng-Bi nè! Cho em slogan với Búa hồng ver.2, pin lắp sẵn.',
       [_l('slogan', 1, '1 slogan'), _l('bua2', 1, 'Búa hồng ver.2', 'bt'), _l('pin_aa', 1, 'Pin vừa cây búa đó', 'battery')],
       mod='cosplay', min_day=3),
    _o(1, 'Na cosplay Mận-Ji', 'Hôm nay em là Mận-Ji! Một Digipack Mận-Ji với một slogan, quét Zchart.',
       [_l('ps_digi_manji', 1, 'Digipack Mận-Ji'), _l('slogan', 1, '1 slogan')], zchart=True, mod='cosplay', min_day=3),
    _o(4, 'Anh Dũng chốt đơn nhóm', 'Nhóm anh góp tiền mua sáu bản Blank, quét Zchart, poster cuộn hết nha.',
       [_l('ps_blank', 6, '6 bản Blank')], zchart=True, tube=True, mod='chot', min_day=2),
]

# Cases: someone comes back with a problem; no basket, a decision.
CASES = [
    dict(npc=6, title='Mít đòi trả album', tw='refund', min_day=2, weight=2,
         say='Card Sữa-Ah! Em muốn Mận-Ji cơ. Chị trả tiền lại cho em đi.'),
    dict(npc=6, title='Búa hồng mua trên mạng', tw='fake_ls', min_day=3, weight=2,
         say='Búa hồng em mua trên mạng không sáng nữa, tiệm bảo hành giùm em nha.'),
    dict(npc=1, title='Búa ver.2 không ghép ghế', tw='pairing', min_day=3, weight=2,
         say='Búa ver.2 em mua hôm qua không ghép ghế được, tối nay concert rồi chị ơi!'),
    dict(npc=3, title='Lô album gửi bán', tw='bootleg', min_day=3, weight=1,
         say='Anh có một lô hàng, gửi tiệm bán ăn chia nha, rẻ mà đẹp.'),
]

# ---------------------------------------------------------------- the annoying ones: decisions with hidden traits
# A twist: probes the player may ask (each reveals a fact, worded by the hidden trait), answers (q: good / ok / bad,
# by trait; `need`: a good answer without any of these probes counts as ok, a lucky guess), what happens (out) and
# the effects (eff, by trait or for all): sale 'go' or 'end', disc (% off the bill), waste {product: n}, refund (the
# price of one album back), money (a cost), zban (days the shop cannot scan for Zchart), retry (a wrong fix, try again).
# push: a pushy trait comes back once after one of these answers. probe_only: no answer, a reveal ends it (the parent).
def _a(id, label, q, out, eff=None, need=(), **kw):
    return dict(id=id, label=label, q=q, out=out, eff=eff or {}, need=list(need), **kw)


TW = {
    'parent': dict(emoji='👩‍👧', title='Mua giùm con, không rành nhóm', traits={'kid': 1}, probe_only=True,
                   probes=[dict(id='note', label='📝 Xin xem giấy nhắn của bé', text='{note}', reveal=True),
                           dict(id='call', label='📱 Gọi video hỏi bé', text='Bé nói qua video: {note}', reveal=True)],
                   answers=[]),
    'trader': dict(emoji='🃏', title='Đòi khui album trước khi trả tiền', traits={'calm': 2, 'pushy': 2},
                   probes=[dict(id='why', label='❓ Hỏi khui để làm gì', text={
                       'calm': 'Tuấn: “Anh chỉ muốn coi card liền, tiện trao đổi với hội.”',
                       'pushy': 'Tuấn: “Không trúng Sữa-Ah thì anh trả lại, có sao đâu, seal dán lại được mà.”'})],
                   answers=[_a('corner', '💳 Trả tiền xong mời ra góc khui, đổi card ở bảng trao đổi', 'good',
                               'Tuấn trả tiền, khui ở góc khui, dán card thừa lên bảng trao đổi. Kệ hàng vẫn nguyên seal.', dict(sale='go')),
                            _a('open_first', '📦 Cho khui trước, không trúng thì trả lại', 'bad',
                               'Tuấn khui ba bản, không trúng Sữa-Ah, đẩy lại cả ba rồi đi. Ba bản đã khui không bán giá mới được nữa.',
                               dict(sale='end', waste={'ps_pink': 3})),
                            _a('shoo', '🙅 “Không mua thì đi chỗ khác”', 'bad', 'Tuấn bỏ đi, lên nhóm trao đổi chê tiệm khó chịu.',
                               dict(sale='end', review=[2, 'Hỏi có một câu mà bị đuổi, tiệm gì khó chịu ghê.']))],
                   push={'pushy': dict(after=['corner'], say='Tuấn: “Khui thử MỘT bản thôi mà, không trúng anh mới trả!”')}),
    'bulk': dict(emoji='📊', title='Mua sỉ chỉ cần hóa đơn', traits={'chart': 1},
                 probes=[dict(id='plan', label='❓ Hỏi album mua xong để đâu', text=
                              'Anh Dũng: “Nhóm anh chỉ cần hóa đơn quét Zchart. Album để lại tiệm, em bán lại cho người khác, bớt anh 30% là được.”')],
                 answers=[_a('full', '🧾 Bán đủ giá, quét từng bản; album anh mang về hoặc gửi hộp quyên góp thư viện', 'good',
                             'Anh Dũng gật gù, chất album lên xe; năm bản gửi hộp quyên góp cho thư viện phường. Doanh số sạch, Zchart tính đủ.',
                             dict(sale='go')),
                          _a('receipt', '🤫 Bớt 30%, chỉ in hóa đơn, giữ album lại bán tiếp', 'bad',
                             'Zchart soi ra một lô album quét hai lần. Tiệm bị khóa quét ba ngày, nhóm fan khác lên mạng bóc.',
                             dict(sale='go', disc=30, zban=3, review=[1, 'Tiệm bán hóa đơn ảo đẩy chart, BLINKY tẩy chay nha.', 1]), happy=True),
                          _a('refuse', '🙅 Không bán sỉ', 'ok', 'Anh Dũng hậm hực qua tiệm khác. Tiệm mất một mối, nhưng sạch sẽ.',
                             dict(sale='end'))]),
    'reseller': dict(emoji='🛒', title='Gom hết bản giới hạn', traits={'reseller': 3, 'family': 1},
                     probes=[dict(id='phone', label='📒 Đối số điện thoại trong sổ', text={
                         'reseller': 'Số này đứng tên ba phiếu đặt trước khác, mỗi phiếu một tên.',
                         'family': 'Số này chưa từng đặt hàng ở tiệm.'}),
                             dict(id='who', label='❓ Hỏi mua cho ai', text={
                                 'reseller': 'Chị Kiều: “Cho em gái… với mấy đứa bạn em gái. Hỏi chi nhiều vậy?”',
                                 'family': 'Chị Kiều: “Ba đứa em gái chị, đứa nào cũng mê Mận-Ji.”'})],
                     answers=[_a('limit', '🚫 Bán đúng giới hạn mỗi người', 'good',
                                 'Chị Kiều cầm đúng số bản giới hạn, càu nhàu. Hàng sau còn phần cho mọi người.', dict(sale='go')),
                              _a('all', '💸 Bán hết cho nhanh', 'bad', 'Chiều đó bản Jewel lên mạng giá gấp đôi. BLINKY xếp hàng sau về tay không.',
                                 dict(sale='go', nolimit=True, review=[1, 'Tiệm bán hết bản giới hạn cho dân buôn, fan thật về tay trắng.', 1]), happy=True),
                              _a('refuse', '🙅 Không bán bản nào', {'reseller': 'ok', 'family': 'bad'}, {
                                  'reseller': 'Chị Kiều bỏ đi. Giới hạn là để chia đều, không phải để đuổi khách.',
                                  'family': 'Ba đứa em chị Kiều không có bản nào, mà giới hạn cho mua mà.'}, dict(sale='end'))],
                     push={'reseller': dict(after=['limit'], say='Chị Kiều nhỏ giọng: “Thêm 20 xu mỗi bản, bán hết cho chị đi em.”')}),
    'pickup': dict(emoji='📦', title='Lấy hàng đặt trước giùm', traits={'friend': 1, 'stranger': 1},
                   probes=[dict(id='code', label='🔢 Hỏi mã đặt trước', text={
                       'friend': 'Đọc đúng mã {code}, còn đưa tin nhắn Thảo nhờ lấy giùm.',
                       'stranger': 'Ấp úng: “Mã gì ta… em quên rồi.”'}),
                           dict(id='phone', label='📱 Đối 4 số cuối điện thoại', text={
                               'friend': 'Gọi được cho Thảo ngay, 4 số cuối {phone} khớp sổ.',
                               'stranger': 'Đọc 4 số cuối 7730, sổ ghi {phone}.'}),
                           dict(id='call', label='☎️ Gọi số trong sổ', text={
                               'friend': 'Thảo nghe máy: “Dạ em nhờ lấy giùm đó chị.”',
                               'stranger': 'Thảo nghe máy: “Em đâu có nhờ ai! Chiều em tự qua lấy.”'})],
                   answers=[_a('give', '✅ Giao hàng đặt trước', {'friend': 'good', 'stranger': 'bad'}, {
                       'friend': 'Hàng tới tay người được nhờ, Thảo nhắn cảm ơn tiệm.',
                       'stranger': 'Chiều Thảo tới lấy thì hàng đã giao cho người khác. Tiệm phải đền.'},
                       {'friend': dict(sale='go'), 'stranger': dict(sale='go', waste={'ps_jewel': 2})},
                       need=('code', 'phone', 'call'), happy=True),
                            _a('hold', '⏸️ Chưa giao, hẹn chính chủ tới', {'friend': 'ok', 'stranger': 'good'}, {
                                'friend': 'Bạn ấy về tay không, Thảo phải chạy qua lấy. Hơi phiền mà đúng quy trình.',
                                'stranger': 'Người kia bỏ đi. Chiều Thảo tới lấy đủ hàng, cảm ơn tiệm giữ kỹ.'}, dict(sale='end'))]),
    'odds': dict(emoji='🎟️', title='Hỏi chắc trúng fansign không', traits={'calm': 2, 'pushy': 1},
                 probes=[],
                 answers=[_a('honest', '📊 Nói thật: {slots} suất / khoảng {entries} phiếu, mỗi phiếu ~{pct}', 'good',
                             'Na suy nghĩ rồi vẫn mua: “Biết tỉ lệ rồi, mua vì thương idol thôi.”', dict(sale='go')),
                          _a('promise', '🤞 “Mua năm bản chắc trúng, mua mười càng chắc”', 'bad',
                             'Ngày công bố không có tên Na. Na đăng bài: tiệm hứa chắc trúng để bán.',
                             dict(sale='go', review=[1, 'Tiệm hứa chắc trúng fansign để bán album, xạo ghê.'])),
                          _a('vague', '🤷 “Chị cũng không biết nữa”', 'ok', 'Na mua mà cứ thấp thỏm, không biết tỉ lệ ra sao.',
                             dict(sale='go'))],
                 push={'pushy': dict(after=['honest'], say='Na: “Thôi chị nói đại là chắc trúng đi, cho em yên tâm mua!”')}),
    'pob_other': dict(emoji='🎁', title='Đòi POB của tiệm khác', traits={'calm': 1},
                      probes=[],
                      answers=[_a('honest', '🙏 Nói thật: tiệm chỉ có POB Mây Pop', 'good',
                                  'Tuấn tặc lưỡi rồi lấy POB Mây Pop: “Bộ này cũng xinh.”', dict(sale='go')),
                               _a('promise', '🤞 Hứa mai về có POB Ziniverse', 'bad', 'Mai không có. Tuấn quay lại làm ầm ở quầy.',
                                  dict(sale='go', review=[2, 'Hứa POB tiệm khác rồi không có, làm ăn không thật.'])),
                               _a('fake', '🎭 Đưa card tiệm mình, bảo là POB Ziniverse', 'bad',
                                  'Tuấn soi logo là biết. Bài “tiệm tráo POB” lên nhóm trao đổi trong năm phút.',
                                  dict(sale='go', review=[1, 'Đưa POB tiệm mình rồi nói là của Ziniverse, tráo trắng trợn.']))]),
    'queue_cut': dict(emoji='🧍', title='Có người chen hàng', traits={'liar': 2, 'true': 1},
                      probes=[dict(id='ticket', label='🎫 Xin coi số thứ tự', text={
                          'liar': 'Bạn kia không có số. Na chỉ: “Em số 7 nè, bạn đó mới tới!”',
                          'true': 'Bạn kia đưa số 6, bạn ra mua nước nhờ Na giữ chỗ.'})],
                      answers=[_a('order', '🎫 Bán đúng số thứ tự trên vé', 'good', {
                          'liar': 'Bạn kia không có số, lủi xuống cuối hàng. Cả hàng vỗ tay.',
                          'true': 'Bạn số 6 mua trước Na một chút, đúng thứ tự, cả hàng gật gù.'}, dict(sale='go'), need=('ticket',)),
                               _a('back', '👉 Đuổi bạn kia xuống cuối hàng, khỏi hỏi', {'liar': 'ok', 'true': 'bad'}, {
                                   'liar': 'Bạn kia lủi xuống cuối hàng, mà chưa ai coi số nên vẫn có người xì xào.',
                                   'true': 'Bạn số 6 bị đuổi oan xuống cuối hàng, Na cũng thấy kỳ.'}, dict(sale='go')),
                               _a('serve', '🤷 Bán cho bạn chen trước cho nhanh', {'liar': 'bad', 'true': 'ok'}, {
                                   'liar': 'Cả hàng nhao nhao. Na đứng chờ thêm mười phút, mặt xị.', 'true': 'Bạn số 6 mua trước, Na chờ thêm chút.'},
                                   dict(sale='go'))]),
    # cases
    'refund': dict(emoji='🔁', title='Đòi trả album vì card', traits={'wrong_member': 3, 'empty': 1},
                   probes=[dict(id='look', label='🔍 Xem album', text={
                       'wrong_member': 'Seal đã xé, card Sữa-Ah còn nguyên trong túi, đủ CD và poster.',
                       'empty': 'Seal đã xé, túi card trống trơn: album thiếu card từ nhà sản xuất.'}),
                           dict(id='bill', label='🧾 Xem hóa đơn', text='Mua ở tiệm hôm qua, một bản Pink ver.')],
                   answers=[_a('policy', '🙏 Album đã khui không đổi trả; chỉ bảng trao đổi card', {'wrong_member': 'good', 'empty': 'bad'}, {
                       'wrong_member': 'Mít xị mặt nhưng dán card Sữa-Ah lên bảng trao đổi. Hai hôm sau đổi được Mận-Ji.',
                       'empty': 'Album lỗi thật mà tiệm không đổi. Mít mếu máo về.'},
                       {'wrong_member': {}, 'empty': dict(review=[1, 'Album thiếu card mà tiệm không đổi cho em.'])}, need=('look',)),
                            _a('swap', '🔄 Đổi bản mới nguyên seal', {'wrong_member': 'bad', 'empty': 'good'}, {
                                'wrong_member': 'Đổi album vì không thích card: bản đã khui coi như bỏ. Lỡ một lần là cả hội kéo tới đòi đổi.',
                                'empty': 'Đổi bản mới, tiệm gửi bản lỗi về nhà phân phối. Mít cười tít.'},
                                {'wrong_member': dict(waste={'ps_pink': 1}), 'empty': dict(swap='ps_pink')}, need=('look',), happy=True),
                            _a('refund', '💸 Hoàn tiền cho xong', 'bad', 'Hoàn tiền một bản đã khui: tiệm lỗ trắng, mà chính sách thì vỡ.',
                               dict(refund='ps_pink'), happy=True),
                            _a('argue', '😤 Cãi: “Ai biểu mua album ngẫu nhiên”', 'bad', 'Mít khóc ngay quầy, mẹ Mít lên mạng kể.',
                               dict(review=[1, 'Nhân viên cãi tay đôi với con nít.']))]),
    'fake_ls': dict(emoji='🔦', title='Bảo hành búa mua ngoài', traits={'fake': 2, 'genuine': 1},
                    probes=[dict(id='holo', label='✨ Soi tem hologram', text={
                        'fake': 'Tem mờ, nghiêng không đổi màu, chữ BLANKPINK lệch nét.',
                        'genuine': 'Tem đổi màu hồng sang tím khi nghiêng.'}),
                            dict(id='serial', label='🔢 Đối số seri thân và hộp', text={
                                'fake': 'Thân búa không có seri. Hộp ghi seri 000000.',
                                'genuine': 'Seri thân và hộp khớp nhau.'}),
                            dict(id='app', label='📱 Thử nhận diện trên app', text={
                                'fake': 'App báo: “Không nhận diện được thiết bị.”',
                                'genuine': 'App nhận búa, còn bảo hành tới tháng sau.'})],
                    answers=[_a('warranty', '🛠️ Nhận gửi bảo hành hãng', {'fake': 'bad', 'genuine': 'good'}, {
                        'fake': 'Nhà phân phối trả về: hàng nhái. Tiệm chịu phí ship hai chiều.',
                        'genuine': 'Gửi hãng, ba hôm sau có búa đổi mới. Mít mừng rơn.'},
                        {'fake': dict(money=4), 'genuine': {}}, need=('holo', 'serial', 'app')),
                             _a('explain', '🙏 Giải thích hàng nhái, chỉ cách nhận biết', {'fake': 'good', 'genuine': 'bad'}, {
                                 'fake': 'Mít buồn nhưng hiểu, hẹn để dành tiền mua búa thật.',
                                 'genuine': 'Búa thật mà bị bảo là hàng nhái. Mít mang qua tiệm khác bảo hành được ngay.'},
                                 {'fake': {}, 'genuine': dict(review=[2, 'Búa thật mà tiệm bảo hàng nhái, không chịu bảo hành.'])},
                                 need=('holo', 'serial', 'app')),
                             _a('swap', '🎁 Đổi luôn cây búa mới cho vui', 'bad', 'Tiệm mất một cây Búa ver.2. Tối đó ba bạn khác mang búa nhái tới đòi đổi.',
                                dict(waste={'bua2': 1}), happy=True)]),
    'pairing': dict(emoji='📶', title='Búa không ghép ghế', traits={'pin': 1, 'app': 1, 'bt': 1, 'seat': 1, 'dead': 1},
                    probes=[dict(id='pin', label='🔋 Mở nắp pin', text={'pin': 'Một viên pin lắp ngược chiều.', 'dead': 'Pin đúng chiều, mới tinh.'},
                                 default='Pin đúng chiều, còn đầy.'),
                            dict(id='app', label='📲 Mở app ghép ghế', text={'app': 'App báo: “Có bản cập nhật bắt buộc.”'},
                                 default='App là bản mới nhất.'),
                            dict(id='phone', label='⚙️ Xem cài đặt điện thoại', text={'bt': 'Bluetooth điện thoại đang tắt.'},
                                 default='Bluetooth đang bật.'),
                            dict(id='seat', label='🎫 Xem vé và app', text={'seat': 'Vé ghế B12, app chưa nhập số ghế.'},
                                 default='App đã nhập ghế B12.')],
                    answers=[_a('flip', '🔋 Lắp lại pin cho đúng chiều', {'pin': 'good'}, {'pin': 'Búa sáng hồng rực, ghép ghế B12 ngon lành.'},
                                {'pin': {}}, retry=True),
                             _a('update', '📲 Cập nhật app rồi ghép lại', {'app': 'good'}, {'app': 'Cập nhật xong, búa nháy theo nhịp ghế B12.'},
                                {'app': {}}, retry=True),
                             _a('bt', '⚙️ Bật Bluetooth điện thoại', {'bt': 'good'}, {'bt': 'Bật Bluetooth lên là ghép được liền, Na cười ngượng.'},
                                {'bt': {}}, retry=True),
                             _a('seat', '🎫 Nhập số ghế vào app', {'seat': 'good'}, {'seat': 'Nhập ghế B12 xong, búa đổi màu theo khu ghế.'},
                                {'seat': {}}, retry=True),
                             _a('swap', '🔄 Đổi búa mới theo bảo hành', {'dead': 'good'}, {
                                 'dead': 'Búa hỏng mạch thật: đổi mới theo bảo hành hãng, Na kịp giờ concert.'},
                                 {'dead': dict(swap='bua2')}, retry=True)]),
    'bootleg': dict(emoji='📦', title='Gửi hàng bán ăn chia', traits={'bootleg': 2, 'fanmade': 1},
                    say={'fanmade': 'Em tự làm slogan với sticker fanmade BLANKPINK, gửi tiệm bán ăn chia nha.'},
                    probes=[dict(id='tem', label='🔍 Soi tem và mã vạch', text={
                        'bootleg': 'Album không tem chính hãng, mã vạch quét ra một hộp sữa.',
                        'fanmade': 'Đồ tự làm, ghi rõ “fanmade, không chính hãng”, không in logo công ty.'}),
                            dict(id='src', label='❓ Hỏi nguồn hàng', text={
                                'bootleg': 'Tuấn: “Hàng xưởng, y chang hàng thật, ai biết đâu.”',
                                'fanmade': 'Bạn ấy: “Tụi em tự vẽ, in ở tiệm in đầu hẻm.”'})],
                    answers=[_a('board', '📌 Fanmade thì dán bảng tặng miễn phí, không bán', {'bootleg': 'bad', 'fanmade': 'good'}, {
                        'bootleg': 'Album nhái lên bảng tiệm. Khách tưởng tiệm bán hàng nhái.',
                        'fanmade': 'Sticker fanmade dán bảng “tặng miễn phí”, fan nhỏ xúm lại xin.'},
                        {'bootleg': dict(review=[1, 'Tiệm treo album nhái, mất uy tín.', 1]), 'fanmade': {}}, need=('tem', 'src')),
                             _a('sell', '💰 Nhận bán, ăn chia', 'bad', 'Hàng không chính hãng bày lên kệ. Nhà phân phối cảnh cáo tiệm.',
                                dict(review=[1, 'Tiệm bán hàng không chính hãng chung kệ với hàng thật.', 4]), happy=True),
                             _a('refuse', '🙅 Từ chối, tiệm chỉ bán hàng chính hãng', {'bootleg': 'good', 'fanmade': 'ok'}, {
                                 'bootleg': 'Tuấn ôm lô hàng đi. Kệ tiệm vẫn sạch.',
                                 'fanmade': 'Bạn ấy buồn. Đồ fanmade tặng miễn phí thì đâu có sao.'}, {}, need=('tem', 'src'))]),
}
SALE_TW = ('parent', 'trader', 'bulk', 'reseller', 'pickup', 'odds', 'pob_other', 'queue_cut')
CASE_TW = ('refund', 'fake_ls', 'pairing', 'bootleg')

# ---------------------------------------------------------------- the day kinds (rule of the distributor: limit per person)
MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Khách lai rai: học sinh tan học, fan ghé xem hàng mới.', weight=3, limit=3),
    dict(id='comeback', emoji='🎤', label='BLANKPINK comeback', hint='Hàng dài từ sớm. Jewel tối đa 2 bản/người, POB tặng kèm PINK STATIC.',
         min_day=3, weight=2, limit=2),
    dict(id='chot', emoji='📒', label='Hạn chốt đặt trước', hint='Sáng nay chốt số Jewel đặt trước với nhà phân phối.', min_day=2, weight=2, limit=3),
    dict(id='cosplay', emoji='🎀', label='Ngày cosplay', hint='Hội cosplay ghé chụp ảnh, hỏi slogan với lightstick.', min_day=3, weight=1, limit=3),
    dict(id='weekend', emoji='🛍️', label='Cuối tuần', hint='Fan đi theo nhóm, hay mua kèm phụ kiện.', min_day=2, weight=2, limit=3),
    dict(id='rain', emoji='🌧️', label='Mưa chiều', hint='Hộp album sợ nước: kê thùng lên cao, lau tay trước khi đưa album.', min_day=2, weight=1, limit=3),
]
LIMIT_OPTIONS = (1, 2, 3, 5, 0)      # the sign's choices (0: no limit)
POB_COMEBACK = 20                    # POB sets the distributor sends on a comeback morning
BOOK_NAMES = ('Thảo', 'Vy', 'Bảo Ngọc', 'Khoa', 'Tường An', 'Hằng', 'Minh Thư', 'Đạt', 'Quỳnh', 'Phúc')

# Regulars' small stories: one line per finished visit. Na's is the BLINKY's dedication.
REG_STORY = {
    1: ('Na kể đu BLANKPINK từ hồi lớp 6, tờ lịch comeback dán ngay đầu giường.',
        'Na để dành tiền ăn sáng ba tuần mới đủ mua bản này.',
        'Na khoe binder đủ bộ card Mận-Ji, thiếu đúng một tấm POB năm ngoái.',
        'Na tự thêu slogan tên Mận-Ji, mang tặng tiệm một cái treo quầy.',
        'Na trúng fansign! Chạy vô tiệm khóc, ôm chị Thơ: “Em được nắm tay Mận-Ji rồi!”'),
    2: ('Cô Hạnh kể Bống ôm album ngủ, sáng ra còn chào poster.', 'Cô Hạnh giờ phân biệt được BLANKPINK với 7GIÓ rồi, khoe ghê lắm.',
        'Cô Hạnh mang biếu tiệm hũ mứt gừng: “Nhờ con mà Bống chịu học bài.”'),
    3: ('Tuấn dán ba card thừa lên bảng trao đổi, ghi giá rõ ràng.', 'Tuấn chỉ cho mấy bé mới cách bọc card bằng toploader.',
        'Tuấn: “Tiệm này seal chuẩn, anh giới thiệu cả hội qua.”'),
    4: ('Anh Dũng khoe bảng Zchart tuần này, nhóm lên hạng ba.', 'Anh Dũng gửi năm bản vào hộp quyên góp của thư viện phường.',
        'Anh Dũng: “Đẩy chart sạch mới bền, em làm vậy là đúng.”'),
    5: ('Chị Kiều mua đúng giới hạn, lần này không mặc cả.', 'Chị Kiều thú nhận: “Bán lại lời ít mà mệt, thôi chị nghỉ.”'),
    6: ('Mít khoe ba thích album Gió Mùa, mở trên xe suốt.', 'Mít xếp card 7GIÓ vào binder, nhờ chị Thơ chụp hình.',
        'Mít rủ cả lớp qua tiệm vào ngày cosplay.', 'Mít lên cấp 3, ghé tiệm khoe đậu trường chuyên.'),
}

INTRO = dict(
    title='Giới thiệu nghề: bán album ZPOP',
    lead='Tiệm album Mây Pop ở Phố chợ: kệ album BLANKPINK, 7GIÓ, KIWIZ, Búa hồng phát sáng và góc khui album. '
         'Chị Thơ từng làm trưởng fanclub mười năm, giờ bạn đứng quầy với chị.',
    short=[('💿', 'Đúng phiên bản khách cần'), ('🧾', 'Quét Zchart, phiếu fansign, POB'), ('🚫', 'Giữ giới hạn, nói thật')],
    work=[('🌅', 'Sáng: đếm bản giới hạn, dựng biển giới hạn, thử búa trưng bày'),
          ('👂', 'Nghe khách: album nào, phiên bản nào, card ai, nguyên seal không'),
          ('💿', 'Lấy đúng phiên bản: Digipack mới chắc card một thành viên'),
          ('🔋', 'Búa ver.1 ăn pin AAA, ver.2 pin AA và có Bluetooth'),
          ('🧾', 'Quét Zchart, cuộn poster, phiếu fansign, POB khi khách cần'),
          ('🚫', 'Bản giới hạn đúng số mỗi người; không khui trước khi trả tiền'),
          ('💵', 'Tính tiền, thối đúng')],
    meet=[('🍑', 'Na: BLINKY bảy năm, bias Mận-Ji'), ('👩‍👧', 'Cô Hạnh mua giùm bé Bống, không rành nhóm'),
          ('🃏', 'Tuấn Card: đòi khui album tại quầy'), ('📊', 'Anh Dũng đẩy chart, mua sỉ'),
          ('🛒', 'Chị Kiều gom bản giới hạn'), ('🌬️', 'Mít: fan 7GIÓ, hỏi mười câu')],
    stars=[('💿', 'Đúng album, đúng phiên bản'), ('🧾', 'Zchart, poster, fansign, POB đúng ý'), ('🚫', 'Công bằng với hàng chờ'),
           ('🙏', 'Nói thật về tỉ lệ, hàng nhái, chính sách'), ('⏱️', 'Nhanh gọn'), ('💵', 'Thối đúng tiền')],
)

# ---------------------------------------------------------------- học nghề: the first customers with chị Thơ
APPRENTICE = 3
LESSONS = [
    ('Bài 1 · Phiên bản', 'Chị Thơ chỉ kệ: “Pink, Blank, Jewel card ngẫu nhiên. Muốn chắc card ai thì Digipack của người đó.”'),
    ('Bài 2 · Lời dặn', 'Chị Thơ dặn: “Zchart, poster cuộn, phiếu fansign, POB: khách nói gì làm đó, đừng tự thêm.”'),
    ('Bài 3 · Giới hạn', 'Chị Thơ nhắc: “Bản giới hạn đúng số trên biển. Ai năn nỉ cũng vậy.”'),
]
CATCH = {
    'bias': 'Khoan, khách cần CHẮC CHẮN card một người: chỉ Digipack của người đó mới chắc. Đổi lại đi em.',
    'cd': 'Kit ver không có đĩa CD đâu em. Khách cần CD thì lấy Sáng hay Đêm.',
    'battery': 'Búa ver.1 ăn pin AAA, ver.2 ăn pin AA. Coi lại vỉ pin em.',
    'cheap': 'Khách muốn loại rẻ nhất mà em. Coi lại giá trên kệ.',
    'bt': 'Khách cần Bluetooth: chỉ Búa ver.2 có. Đổi lại em.',
    'version': 'Sai phiên bản rồi em. Đọc lại lời khách dặn.',
    'missing': 'Còn thiếu món khách dặn kìa em.',
    'extra': 'Món này khách đâu có lấy. Bỏ ra đi em.',
    'limit': 'Quá giới hạn trên biển rồi em. Bớt lại cho đúng.',
    'zchart': 'Khách dặn quét Zchart mà em chưa bật.',
    'poster': 'Khách dặn poster cuộn: lấy ống cuộn poster.',
    'raffle': 'Khách dặn ghi phiếu fansign kìa em.',
    'pob': 'Khách đặt POB mà em chưa đưa.',
}
# What the customer says when a mistake reaches the counter.
SLIP_WORDS = {
    'bias': 'Mua để chắc có card bias mà bản này card ngẫu nhiên!',
    'cd': 'Bản Kit không có đĩa, ba nghe bằng gì giờ?',
    'battery': 'Pin không vừa cây búa, về nhà mới biết!',
    'cheap': 'Có loại rẻ hơn mà không nói gì hết.',
    'bt': 'Cây này đâu có Bluetooth, ghép ghế sao được!',
    'version': 'Tôi dặn phiên bản khác mà.',
    'missing': 'Thiếu món tôi dặn rồi.',
    'extra': 'Tôi đâu có lấy món này, tính tiền luôn là sao?',
    'limit': 'Bán quá giới hạn, người xếp hàng sau hết phần.',
    'zchart': 'Không quét Zchart, mấy bản này không được tính lên bảng!',
    'poster': 'Poster bị gập mất rồi, dặn cuộn mà!',
    'raffle': 'Không ghi phiếu fansign cho tôi à?',
    'pob': 'Đặt trước mà không có POB?',
}
SLIP_NOTE = {
    'bias': 'không đúng bản chắc card', 'cd': 'đưa bản không có CD', 'battery': 'sai loại pin', 'cheap': 'không đưa loại rẻ nhất',
    'bt': 'đưa búa không Bluetooth', 'version': 'sai phiên bản', 'missing': 'thiếu món', 'extra': 'tính thêm món khách không lấy',
    'limit': 'bán quá giới hạn', 'zchart': 'quên quét Zchart', 'poster': 'poster bị gập', 'raffle': 'quên phiếu fansign', 'pob': 'thiếu POB',
}

# ---------------------------------------------------------------- surprises between customers (kit desk scripts)
DESK = [
    dict(id='mv_loud', title='Xin bật MV mới thật to', emoji='📺', npc=1, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Một nhóm fan ùa vào: “Chị ơi MV mới ra rồi! Bật loa hết cỡ đi chị, tụi em quẩy!” Nhà bà Tư bên cạnh có em bé đang ngủ trưa.',
         options=[dict(id='tv', label='Bật trên TV vừa nghe, mở phụ đề', hint='', effects=dict(xp=4), good=True,
                       outcome='Cả nhóm hát theo phụ đề, nhún nhảy nhỏ nhỏ. Em bé nhà bà Tư vẫn ngủ ngon.'),
                  dict(id='loud', label='Bật hết cỡ cho máu', hint='',
                       effects=dict(review=[2, 'Tiệm album mở nhạc ầm ầm giữa trưa, con nhỏ hàng xóm giật mình khóc.', 2]), good=False,
                       outcome='Bà Tư qua gõ cửa, mặt hầm hầm. Nhóm fan ngại quá chuồn mất.'),
                  dict(id='no', label='Không bật, tiệm đang bán', hint='', effects=dict(patience=-2), good=None,
                       outcome='Nhóm fan xem chung một cái điện thoại, hơi tiu nghỉu.')],
         default='no'),
    dict(id='dented', title='Thùng album móp góc', emoji='📦', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Shipper giao thùng PINK STATIC, một góc thùng móp, hai bản bên trong cong bìa.',
         options=[dict(id='claim', label='Chụp hình, ghi biên bản, báo nhà phân phối đổi', hint='', effects=dict(xp=4), good=True,
                       outcome='Nhà phân phối hẹn đổi hai bản mới tuần sau. Biên bản ký đủ.'),
                  dict(id='sell', label='Để lẫn vào kệ, ai mua trúng thì thôi', hint='',
                       effects=dict(review=[2, 'Mua album nguyên seal mà bìa cong vênh, buồn ghê.', 1]), good=False,
                       outcome='Na mua trúng bản cong, tiếc đứt ruột.'),
                  dict(id='keep', label='Cất riêng, để bán giá trưng bày', hint='', effects=dict(xp=1), good=None,
                       outcome='Hai bản cong nằm góc kệ trưng bày, chưa ai hỏi.')],
         default='keep'),
    dict(id='lost_card', title='Card rơi dưới quầy', emoji='🃏', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Quét nhà thấy một tấm card Mận-Ji bọc toploader kẹt dưới chân quầy. Card này trên nhóm trao đổi giá cao lắm.',
         options=[dict(id='hold', label='Cất ở quầy, đăng nhóm tìm chủ', hint='', effects=dict(xp=4), good=True,
                       outcome='Chiều một bé chạy vào, mắt đỏ hoe: “Card em!” Bé cảm ơn rối rít.'),
                  dict(id='board', label='Dán lên bảng trao đổi, ai cần thì lấy', hint='', effects=dict(patience=-1), good=None,
                       outcome='Có người lấy mất trước khi chủ quay lại. Bé chủ card buồn so.'),
                  dict(id='sell', label='Bán cho Tuấn, card rơi thì ai nhặt được là của người đó', hint='',
                       effects=dict(review=[1, 'Card em rơi ở tiệm mà tiệm đem bán cho người khác.', 1]), good=False,
                       outcome='Bé chủ card thấy card mình trên nhóm trao đổi, kể hết lên mạng.')],
         default='board'),
    dict(id='camp', title='Fan xin ngủ trước cửa tiệm', emoji='⛺', npc=1, min_day=3, tone='tense', at='between', weight=2, mods=('comeback', 'chot'),
         text='Mấy bạn fan xin trải chiếu ngủ trước cửa tiệm từ tối, để mai comeback xếp đầu hàng.',
         options=[dict(id='ticket', label='Phát số thứ tự từ tối, mời về nhà ngủ, sáng tới đúng số', hint='', effects=dict(xp=5), good=True,
                       outcome='Ai cũng có số, về nhà ngủ ngon. Sáng ra hàng xếp đúng thứ tự, không ai chen.'),
                  dict(id='allow', label='Cho ngủ trước cửa, có gì đâu', hint='', effects=dict(patience=-3), good=None,
                       outcome='Nửa đêm mưa, mấy bạn ướt nhẹp. Bảo vệ phường nhắc tiệm.'),
                  dict(id='chase', label='Đuổi hết về, mai tính', hint='',
                       effects=dict(review=[2, 'Tiệm đuổi fan như đuổi tà, mai chen nhau loạn xạ.', 1]), good=False,
                       outcome='Sáng ra cả đám chen nhau ở cửa, xô ngã kệ standee.')],
         default='allow'),
    dict(id='power', title='Cúp điện, máy quét Zchart tắt', emoji='🔌', npc=4, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Cúp điện cả dãy phố. Máy quét Zchart tắt ngóm, anh Dũng đứng chờ quét bốn bản.',
         options=[dict(id='log', label='Ghi tay mã từng bản, có điện quét bù trong ngày', hint='', effects=dict(xp=4), good=True,
                       outcome='Có điện lại, quét bù đủ bốn bản trước giờ chốt sổ. Anh Dũng gật gù.'),
                  dict(id='fake', label='Nhập đại số liệu cho đủ', hint='',
                       effects=dict(review=[1, 'Tiệm nhập số Zchart bừa, nhóm fan bị trừ điểm oan.', 4]), good=False,
                       outcome='Zchart đối soát lệch số, cả lô bị hủy. Anh Dũng nổi giận.'),
                  dict(id='later', label='Hẹn khách mai quay lại quét', hint='', effects=dict(patience=-3), good=None,
                       outcome='Anh Dũng càu nhàu, mai phải quay lại.')],
         default='later'),
    dict(id='rival', title='Tiệm khác xin danh sách đặt trước', emoji='📋', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Nhân viên tiệm Kpo Kho ghé: “Cho chị xin danh sách khách đặt trước, chị nhắn mời qua bên chị, hoa hồng chia đôi.”',
         options=[dict(id='no', label='Từ chối: thông tin khách là của khách', hint='', effects=dict(xp=5), good=True,
                       outcome='Chị kia đi về. Chị Thơ gật đầu: “Sổ đặt trước là chuyện riêng của khách.”'),
                  dict(id='share', label='Gửi danh sách, lấy hoa hồng', hint='',
                       effects=dict(review=[1, 'Tiệm đem số điện thoại khách cho tiệm khác, tin nhắn rác cả tuần.', 2]), good=False,
                       outcome='Khách đặt trước bị nhắn tin rác cả tuần, ai cũng biết từ đâu ra.')],
         default='no'),
    dict(id='cosplay_door', title='Hội cosplay chụp hình chắn cửa', emoji='📸', npc=6, min_day=3, tone='gentle', at='between', weight=3,
         mods=('cosplay',),
         text='Hội cosplay BLANKPINK đứng chụp hình ngay cửa tiệm, chân máy chắn lối vào, khách phải lách.',
         options=[dict(id='corner', label='Mời vào góc standee trong tiệm chụp, chừa lối đi', hint='', effects=dict(xp=4), good=True,
                       outcome='Góc standee thành điểm check-in. Khách vào ra thoải mái.'),
                  dict(id='leave', label='Kệ, chụp xong tự đi', hint='', effects=dict(patience=-3), good=None,
                       outcome='Khách lách mãi mới vào, một bà cụ suýt vấp chân máy.'),
                  dict(id='chase', label='Đuổi đi chỗ khác chụp', hint='',
                       effects=dict(review=[2, 'Tiệm không thân thiện với cosplayer gì hết.', 6]), good=False,
                       outcome='Cả hội kéo qua tiệm khác, đăng hình check-in ở đó.')],
         default='leave'),
    dict(id='leak', title='Mưa tạt vào kệ album', emoji='🌧️', npc=0, min_day=2, tone='gentle', at='between', weight=3, mods=('rain',),
         text='Mưa tạt xéo qua cửa, nước lăn tăn trên nắp thùng PINK STATIC để sát nền.',
         options=[dict(id='lift', label='Kê thùng lên kệ cao, kéo bạt, lau khô', hint='Khách chờ một chút', effects=dict(patience=-2, xp=3), good=True,
                       outcome='Thùng album khô ráo. Chị Thơ dặn mai mua thêm pallet kê.'),
                  dict(id='later', label='Bán tiếp, tạnh mưa rồi tính', hint='', effects=dict(stock={'ps_blank': -1}), good=False,
                       outcome='Một bản Blank ướt bìa, thành hàng lỗi.')],
         default='later'),
    dict(id='leak_spoiler', title='Fan đòi xem album trước ngày phát hành', emoji='🤐', npc=3, min_day=3, tone='tense', at='between', weight=1,
         mods=('chot',),
         text='Tuấn nhìn thấy thùng album mới về chưa tới ngày bán: “Cho anh chụp ảnh card thôi, đăng trước cho hội, ai biết đâu.”',
         options=[dict(id='no', label='Từ chối: chưa tới ngày phát hành', hint='', effects=dict(xp=4), good=True,
                       outcome='Tuấn tặc lưỡi. Nhà phân phối gọi khen tiệm giữ hàng kỹ.'),
                  dict(id='yes', label='Cho chụp một tấm, chắc không sao', hint='',
                       effects=dict(review=[1, 'Tiệm làm lộ card trước ngày phát hành, công ty truy ra đó.', 4]), good=False,
                       outcome='Ảnh card lan khắp mạng. Nhà phân phối gọi điện, giọng lạnh tanh.')],
         default='no'),
]

# ---------------------------------------------------------------- situations (sit_ engine)
SITUATIONS = [
    dict(id='ZP-S01', title='Album thiếu card, mua đã sáu ngày', npc=1, tone='tense', min_day=1,
         opening='Na cầm album: “Mua tuần trước, hôm nay em mới khui, túi card trống trơn. Tiệm đổi giùm em được không?”',
         swap='Bạn là Na: để dành ba tuần mới mua được, khui ra không có card.',
         facts=[dict(id='policy', title='Chính sách tiệm', source='Bảng ở quầy', text='Album khui rồi không đổi trả; lỗi nhà sản xuất đổi trong 7 ngày.'),
                dict(id='date', title='Hóa đơn', source='Sổ bán', text='Mua đúng 6 ngày trước, bản Pink ver.'),
                dict(id='npp', title='Nhà phân phối', source='Chị Thơ', text='Lỗi thiếu card thì nhà phân phối đổi bản mới cho tiệm.')],
         options=[dict(id='swap', label='Đổi bản mới, gửi bản lỗi về nhà phân phối', requires=['policy', 'date'], quality='good', stars=5,
                       review='Album lỗi mà tiệm đổi liền, không cãi một câu.', outcome='Na ôm bản mới, cười tít.',
                       perspectives=[dict(who='Na', emoji='🍑', text='Biết vậy mua ở đây hoài.'),
                                     dict(who='Chị Thơ', emoji='💿', text='Lỗi nhà sản xuất thì mình đổi, rồi đòi lại nhà phân phối.')]),
                  dict(id='card', label='Tặng một card thừa trên bảng trao đổi thay vì đổi album', requires=['policy'], quality='ok', stars=3,
                       review='Không đổi album nhưng có card bù, tạm được.', outcome='Na nhận card Sữa-Ah, vẫn hơi buồn.',
                       perspectives=[dict(who='Na', emoji='😕', text='Có card mà không phải bias…'),
                                     dict(who='Tuấn', emoji='🃏', text='Card đó trên bảng là của người khác gửi mà.')]),
                  dict(id='no', label='Từ chối: đã khui là không đổi', quality='bad', stars=1,
                       review='Album lỗi nhà sản xuất mà tiệm không đổi, còn nói đã khui.', outcome='Na khóc ở quầy.',
                       perspectives=[dict(who='Na', emoji='😢', text='Ba tuần tiền ăn sáng…'),
                                     dict(who='Chị Thơ', emoji='💿', text='Chính sách không đổi là cho chuyện không thích card, đâu phải album lỗi.')])],
         lesson='Không đổi trả vì không thích card, nhưng album lỗi thì đổi: đọc kỹ chính sách và ngày mua.'),
    dict(id='ZP-S02', title='Đơn đặt trước quá đông', npc=4, tone='tense', min_day=2,
         opening='Nhà phân phối báo chỉ giao được 20 bản Jewel, mà sổ đặt trước ghi 26 bản.',
         facts=[dict(id='book', title='Sổ đặt trước', source='Sổ', text='26 bản, xếp theo giờ đặt; 6 bản cuối đặt sau giờ chốt 10 phút.'),
                dict(id='rule', title='Điều lệ đặt trước', source='Bảng ở quầy', text='Đủ hàng theo thứ tự đặt; thiếu hàng thì hoàn cọc đủ.'),
                dict(id='vip', title='Lời nhờ', source='Anh Dũng', text='Anh Dũng nhắn: “Ưu tiên nhóm anh nha, anh mua nhiều nhất.”')],
         options=[dict(id='order', label='Giao theo thứ tự đặt, nhắn 6 người cuối xin lỗi và hoàn cọc', requires=['book', 'rule'], quality='good', stars=5,
                       review='Thiếu hàng mà tiệm nhắn rõ, hoàn cọc đủ, rất đàng hoàng.', outcome='Sáu người cuối hơi buồn nhưng ai cũng hiểu.',
                       perspectives=[dict(who='Khách đặt muộn', emoji='🙂', text='Đặt sau giờ chốt thì chịu thôi, được hoàn đủ.'),
                                     dict(who='Chị Thơ', emoji='💿', text='Sổ đặt trước là lời hứa, làm đúng thứ tự.')]),
                  dict(id='split', label='Chia đều mỗi người bớt một chút', requires=['book'], quality='ok', stars=3,
                       review='Đặt ba bản được giao hai, không ai hỏi ý mình.', outcome='Ai cũng thiếu một ít, ai cũng hơi khó chịu.',
                       perspectives=[dict(who='Na', emoji='😕', text='Em đặt sớm nhất mà cũng bị bớt.'),
                                     dict(who='Anh Dũng', emoji='📊', text='Chia vậy cũng được.')]),
                  dict(id='vip', label='Ưu tiên nhóm anh Dũng mua nhiều', quality='bad', stars=1,
                       review='Đặt trước từ sớm mà bị cắt cho khách mua nhiều. Bất công.', outcome='Fan đặt sớm lên mạng kể, tiệm mất uy tín.',
                       perspectives=[dict(who='Na', emoji='😠', text='Đặt từ ngày đầu mà không có.'),
                                     dict(who='Anh Dũng', emoji='📊', text='Anh được ưu tiên nhưng nhóm fan khác ghét lây.')])],
         lesson='Đặt trước theo thứ tự đã hứa, thiếu hàng thì báo sớm và hoàn cọc đủ.'),
    dict(id='ZP-S03', title='Phụ huynh đòi trả lightstick con lén mua', npc=2, tone='gentle', min_day=3,
         opening='Cô Hạnh mang Búa hồng ver.2 còn nguyên hộp: “Bống lấy tiền học thêm mua cái này. Cô xin trả lại.”',
         facts=[dict(id='box', title='Hộp búa', source='Soi kỹ', text='Còn nguyên seal, chưa lắp pin, hóa đơn hôm qua.'),
                dict(id='kid', title='Bé Bống', source='Cô Hạnh', text='Bống mới 11 tuổi, tự cầm tiền học thêm đi mua.'),
                dict(id='rule', title='Chính sách tiệm', source='Bảng ở quầy', text='Hàng nguyên seal đổi trả trong 3 ngày, có hóa đơn.')],
         options=[dict(id='refund', label='Nhận lại, hoàn tiền đủ vì còn nguyên seal', requires=['box', 'rule'], quality='good', stars=5,
                       review='Tiệm nhận lại hàng nguyên seal liền, cô rất cảm ơn.', outcome='Cô Hạnh dắt Bống về nói chuyện tiền bạc.',
                       perspectives=[dict(who='Cô Hạnh', emoji='👩‍👧', text='Gặp tiệm biết điều, nhẹ cả người.'),
                                     dict(who='Bống', emoji='🥺', text='Con sẽ để dành tiền thật để mua.')]),
                  dict(id='voucher', label='Chỉ đổi phiếu mua hàng, không hoàn tiền', requires=['box'], quality='ok', stars=3,
                       review='Hàng còn nguyên mà chỉ cho phiếu mua hàng.', outcome='Cô Hạnh cầm phiếu, không biết dùng vào đâu.',
                       perspectives=[dict(who='Cô Hạnh', emoji='😐', text='Cô có rành mấy món này đâu.'),
                                     dict(who='Chị Thơ', emoji='💿', text='Còn seal thì hoàn được mà em.')]),
                  dict(id='no', label='Từ chối: bán rồi thì thôi', quality='bad', stars=1,
                       review='Con nít lấy tiền học mua đồ, hàng còn nguyên mà tiệm không nhận lại.', outcome='Cô Hạnh buồn bã ra về.',
                       perspectives=[dict(who='Cô Hạnh', emoji='😞', text='Tiền học thêm cả tháng của con…'),
                                     dict(who='Bống', emoji='😢', text='Tại con hết.')])],
         lesson='Hàng nguyên seal trong hạn đổi trả thì nhận lại; với trẻ nhỏ, càng cần mềm mỏng.'),
]
