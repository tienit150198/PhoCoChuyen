"""Nội trợ nhà chị Thảo: the data for game/careers/homemaker.py.

A job (variant) is a short chain of steps the player works through in order. Raw steps keep the
verdicts next to what the player sees; homemaker.make_task splits them into the public step (needs)
and the hidden key (_key). Step kinds:

  pick     tap the things to take / do (market goods with a price, prep habits, pills from the box);
           ok=True must be taken, ok=False must not, ok=None either way;
  sort     put every item into one bin (laundry loads, fridge shelves, cleaners per surface, portions);
  order    tap the items in the order they are done; `rules` (a, b, sev, why, cat) say a comes before b,
           an item with `bad` is something that should not be done at all;
  choose   one answer, each with its quality and outcome;
  haggle   the seller names a price; buy at it or name your own (the seller decides from hidden traits);
  receipt  the market book: write what was spent and hand back the change.

`when=[step, item]` makes a step happen only when that item was picked (or that option chosen) in an
earlier step; otherwise it is skipped with `skip`. A slip is (sev 1..3, why, cat, safety): cat is
cr (khéo tay), sf (an toàn, sức khỏe), hn (trung thực), mn (cư xử).
"""
from __future__ import annotations


# ================================================================ builders
def I(iid, emoji, name, look='', ok=None, why='', sev=0, cat='cr', safety=False, price=0, say=''):
    """A pick item."""
    return dict(id=iid, emoji=emoji, name=name, look=look, ok=ok, why=why, sev=sev, cat=cat, safety=safety, price=price, say=say)


def S(iid, emoji, name, right, look='', why='', sev=1, cat='cr', wrong=None):
    """A sort item: right = bin ids that are fine; wrong = {bin: (sev, why, cat, safety)} for the bad ones
    that need their own words; every other bin gets (sev, why, cat)."""
    return dict(id=iid, emoji=emoji, name=name, look=look, right=list(right), why=why, sev=sev, cat=cat, wrong=dict(wrong or {}))


def O(iid, emoji, name, bad=None):
    """An order item; bad = (sev, why, cat, safety) when it should not be done at all."""
    return dict(id=iid, emoji=emoji, name=name, bad=bad)


def C(oid, label, q, out, sev=0, why='', cat='cr', safety=False, hint=''):
    """A choose option: q is good / ok / bad; a slip (sev, why, cat) when sev > 0."""
    return dict(id=oid, label=label, q=q, out=out, sev=sev, why=why, cat=cat, safety=safety, hint=hint)


def pick(sid, title, go, items, lead='', when=None, skip='', done='Xong, không có gì phải nói.'):
    return dict(type='pick', id=sid, title=title, go=go, lead=lead, items=items, when=when, skip=skip, done=done)


def sort(sid, title, go, bins, items, lead='', when=None, skip='', done='Đâu ra đấy.'):
    return dict(type='sort', id=sid, title=title, go=go, lead=lead, bins=[dict(id=b[0], emoji=b[1], label=b[2]) for b in bins],
                items=items, when=when, skip=skip, done=done)


def order(sid, title, go, items, rules, lead='', when=None, skip='', done='Trơn tru, đúng thứ tự.'):
    return dict(type='order', id=sid, title=title, go=go, lead=lead, items=items, rules=[list(r) for r in rules], when=when, skip=skip, done=done)


def choose(sid, title, text, options, lead='', when=None, skip=''):
    return dict(type='choose', id=sid, title=title, text=text, options=options, lead=lead, when=when, skip=skip)


def haggle(sid, title, seller, goods, quote, fair, lead='', when=None, skip=''):
    return dict(type='haggle', id=sid, title=title, seller=seller, goods=goods, quote=quote, fair=fair, lead=lead, when=when, skip=skip)


def receipt(sid='so', title='Ghi sổ chợ, trả tiền thừa', lead='Chị Thảo giữ sổ chợ từng khoản. Ghi đúng số đã tiêu, tiền thừa trả lại chị.'):
    return dict(type='receipt', id=sid, title=title, lead=lead, when=None, skip='')


def V(vid, kind, npc, title, opening, steps, note='', mods=None, min_day=1, weight=1, budget=0, shop=None):
    """A job: shop = the market list (what to buy) for a market trip."""
    return dict(id=vid, kind=kind, npc=npc, title=title, opening=opening, steps=steps, note=note, mods=mods, min_day=min_day,
                weight=weight, budget=budget, shop=list(shop or []))


# ================================================================ the people (index = PEOPLE row)
PEOPLE = [
    ('Chị Thảo', 'Chủ nhà, kế toán', 'Kế toán công ty may, giữ sổ chợ từng xu, dặn một việc ba lần.', 'picky'),
    ('Bà Lành', 'Mẹ chồng chị Thảo, 76 tuổi', 'Huyết áp cao, tiểu đường, nấu ăn giỏi nhất nhà và chê cũng giỏi nhất nhà.', 'sour'),
    ('Anh Dũng', 'Chồng chị Thảo, kỹ sư công trình', 'Ăn cay, hay đau dạ dày, về nhà muộn, rất dễ tính.', 'warm'),
    ('Bé Su', 'Con gái lớn, học lớp 2', 'Dị ứng tôm, ghét rau, mê điện thoại, nói nhiều như sáo.', 'genz'),
    ('Cô Năm', 'Bán rau đầu chợ Mây', 'Bán rau ba mươi năm, hay cho thêm nắm hành, rau nào tươi cô nói thật.', 'warm'),
    ('Bà Tư', 'Hàng xóm sát vách', 'Ngày nào cũng sang “hỏi thăm”, chuyện nhà ai bà cũng biết.', 'bossy'),
    ('Chú Thịnh', 'Hàng thịt cá chợ Mây', 'Nói giá nhanh như gió, cân nhanh hơn, thỉnh thoảng thiếu vài lạng.', 'bossy'),
]
FAMILY = (0, 1, 2, 3)

# The family note on the fridge (Sổ tay nhà chị Thảo): what everyone eats, takes and needs.
NOTEBOOK = [
    ('👵', 'Bà Lành, 76 tuổi', 'Huyết áp cao, tiểu đường: ăn nhạt, không đường, cơm mềm. 8 giờ sáng, sau ăn: 1 viên trắng tròn (huyết áp) và 1 viên trắng dài (tiểu đường). Viên hồng nhỏ là thuốc ngủ, chỉ buổi tối.'),
    ('👨', 'Anh Dũng', 'Ăn cay, ớt để riêng. Hay đau dạ dày.'),
    ('👩', 'Chị Thảo', 'Giữ sổ chợ, ghi đúng từng khoản. Tối ăn ít cơm.'),
    ('👧', 'Bé Su, 7 tuổi', 'DỊ ỨNG TÔM. Ăn cá phải gỡ xương. Tan học 16:30 ở cổng trường Hoa Sữa; chỉ giao bé cho bố, mẹ hoặc bà.'),
    ('👶', 'Bé Cốm, 18 tháng', 'Ăn cháo nhuyễn. Sữa: 1 muỗng gạt cho 30 ml nước 40–70 °C. Ngủ trưa từ 12 giờ.'),
    ('🏠', 'Nhà', 'Phòng khách sàn gỗ, bếp mặt đá. Bàn thờ: bát hương chỉ bà và chị Thảo động vào.'),
]

# ================================================================ shared bins and steps
PORTIONS = (('nhat', '🥣', 'Phần nhạt, không đường'), ('thuong', '🍚', 'Phần thường'), ('ot', '🌶️', 'Phần thường, ớt để riêng'),
            ('xuong', '🐟', 'Phần thường, gỡ sạch xương'), ('khong_tom', '🚫', 'Phần riêng, không tôm'), ('chao', '🍼', 'Cháo nhuyễn'))
_EAT_BA = ('Bà Lành ăn mặn, ngọt: tối huyết áp, đường huyết lên.', 2, 'sf')
_EAT_COM = ('Bé Cốm mười tám tháng nhai sao nổi cơm thường, ọe ra cả.', 2, 'sf')


def _portions(sid, fish=False, shrimp=False, stomach=False, guest=False):
    """Chia phần theo người ăn: who gets which bowl for this menu."""
    su_right = ('khong_tom',) if shrimp else ('xuong',) if fish else ('thuong', 'xuong')
    su_why = ('Bé Su ăn phải tôm: môi sưng, nổi mẩn khắp người!' if shrimp else 'Cá còn xương mà đưa bé Su, bé hóc một cái xương dăm.' if fish else 'Bé Su chỉ cần phần thường.')
    items = [
        S('ba', '👵', 'Bà Lành', ('nhat',), 'huyết áp cao, tiểu đường', why=_EAT_BA[0], sev=_EAT_BA[1], cat=_EAT_BA[2]),
        S('dung', '👨', 'Anh Dũng', ('thuong',) if stomach else ('ot', 'thuong'), 'hôm nay đau dạ dày' if stomach else 'ăn cay',
          why='Anh Dũng đang đau dạ dày mà có ớt, tối lại ôm bụng.' if stomach else 'Anh Dũng chỉ cần phần thường.', sev=1, cat='sf' if stomach else 'cr'),
        S('thao', '👩', 'Chị Thảo', ('thuong',), 'ăn bình thường', why='Chị Thảo ăn phần thường thôi.', sev=1),
        S('su', '👧', 'Bé Su', su_right, 'dị ứng tôm' if shrimp else '7 tuổi', why=su_why, sev=3 if shrimp else 2,
          cat='sf', wrong={b: (3, su_why, 'sf', True) for b in ('nhat', 'thuong', 'ot', 'xuong', 'chao')} if shrimp else None),
        S('com', '👶', 'Bé Cốm', ('chao',), '18 tháng', why=_EAT_COM[0], sev=_EAT_COM[1], cat=_EAT_COM[2]),
    ]
    if guest:
        items.append(S('khach', '🧳', 'Cô chú dưới quê', ('thuong', 'ot'), 'khách', why='Khách ăn phần thường.', sev=1))
    return sort(sid, 'Chia phần theo người ăn', '🍽️ Bày mâm', PORTIONS, items,
                lead='Mỗi người một phần hợp với mình. Quên thì mở Sổ tay nhà.')


def _rice(kind):
    """Nấu cơm: the rice in the bag decides the water."""
    if kind == 'moi':
        text = 'Bao gạo mới mở: gạo tám vụ mới, hạt còn dẻo, thơm. Thường nhà đong nước ngập một đốt ngón tay.'
        return choose('com', 'Vo gạo, đong nước', text, [
            C('less', 'Gạo mới: bớt nước một chút', 'good', 'Cơm chín dẻo, hạt nào ra hạt nấy.'),
            C('same', 'Đong ngập một đốt tay như mọi khi', 'bad', 'Cơm hơi nhão.', 1, 'Gạo mới mà nước như gạo cũ, cơm nhão như cháo.'),
            C('more', 'Thêm nước cho bà dễ ăn', 'bad', 'Nồi cơm nát bét.', 1, 'Gạo mới còn thêm nước: cơm nát, bà còn chê.')])
    if kind == 'cu':
        text = 'Gạo khang dân để từ tháng trước, hạt khô, cứng. Thường nhà đong nước ngập một đốt ngón tay.'
        return choose('com', 'Vo gạo, đong nước', text, [
            C('more', 'Gạo cũ: thêm chút nước', 'good', 'Cơm chín mềm, bà ăn khen.'),
            C('same', 'Đong ngập một đốt tay như mọi khi', 'bad', 'Cơm hơi khô.', 1, 'Gạo cũ hút nước, cơm khô cứng, bà nhai không nổi.'),
            C('less', 'Bớt nước cho cơm tơi', 'bad', 'Cơm sượng hạt.', 1, 'Gạo cũ còn bớt nước: cơm sượng, ăn lạo xạo.')])
    text = 'Gạo thường nhà vẫn ăn. Nồi cơm điện có vạch nước bên trong.'
    return choose('com', 'Vo gạo, đong nước', text, [
        C('line', 'Vo hai nước, đong đúng vạch', 'good', 'Cơm chín đều, vừa dẻo.'),
        C('rinse', 'Vo thật kỹ năm sáu nước cho trắng', 'ok', 'Cơm chín nhưng nhạt vị.', 1, 'Vo quá kỹ trôi hết chất, cơm nhạt thếch.'),
        C('guess', 'Đổ nước ước chừng bằng mắt', 'bad', 'Cơm chỗ nhão chỗ khô.', 1, 'Đổ nước bằng mắt, nồi cơm nửa nhão nửa sống.')])


def _prep(sid='so_che'):
    """Sơ chế: the kitchen habits that keep a family well."""
    return pick(sid, 'Sơ chế cho sạch', '🔪 Vào bếp', [
        I('tay', '🧼', 'Rửa tay bằng xà phòng', 'trước khi động vào đồ ăn', True, 'Không rửa tay mà sờ đồ ăn, chị Thảo thấy nhắc ngay.', 1, 'sf'),
        I('ngam', '🥬', 'Rửa rau dưới vòi, ngâm nước muối loãng, rửa lại', 'rau mua ngoài chợ', True, 'Rau chỉ tráng sơ, còn cả đất cát.', 1, 'sf'),
        I('thot', '🪵', 'Thớt riêng cho đồ sống và đồ chín', 'nhà có hai thớt', True, 'Dùng chung một thớt cho thịt sống và đồ chín.', 1, 'sf'),
        I('nong', '♨️', 'Rã đông thịt bằng nước nóng cho nhanh', 'thịt trong ngăn đá', False, 'Rã đông bằng nước nóng: ngoài chín tái, trong vẫn đá, dễ hỏng.', 1, 'sf'),
        I('song', '🥗', 'Thái rau sống luôn trên thớt vừa làm cá', 'cho đỡ phải rửa', False, 'Thớt tanh cá dùng thái rau sống: cả nhà đau bụng.', 2, 'sf'),
        I('muoi', '🥄', 'Nếm canh bằng muôi rồi thả lại vào nồi', 'nhanh tay', False, 'Nếm bằng muôi rồi thả lại nồi, bà Lành nhìn thấy nhăn mặt.', 1, 'mn'),
    ], lead='Chọn những việc sẽ làm, rồi vào bếp.', done='Bếp sạch, tay sạch, đồ sống đồ chín riêng.')


def _talk_back(sid, title, text, good, ok, bad_soft, bad_hard, cat_soft='sf'):
    """A family member asks for something that hurts them: the kind way, a half way, giving in, snapping."""
    return choose(sid, title, text, [
        C('kind', good[0], 'good', good[1]),
        C('half', ok[0], 'ok', ok[1], 1, ok[2], cat_soft),
        C('give', bad_soft[0], 'bad', bad_soft[1], 2, bad_soft[2], cat_soft),
        C('snap', bad_hard[0], 'bad', bad_hard[1], 1, bad_hard[2], 'mn')])


# ================================================================ the jobs
MARKET = [
    V('m_canh', 'market', 0, 'Đi chợ sáng', '“Em đi chợ giúp chị nhé: trưa nay canh chua cá, rau muống xào. Chị đưa 40 xu.”', [
        pick('rau', 'Sạp rau cô Năm', '🛒 Trả tiền rau', [
            I('rm_a', '🥬', 'Rau muống bó này', 'ngọn non, cuống giòn bẻ là gãy, vài lá có lỗ sâu', True, 'Quên mua rau muống.', 1, price=3),
            I('rm_b', '🥬', 'Rau muống bó kia', 'xanh bóng lưỡng, to bất thường, không một lỗ sâu', False, 'Rau xanh bóng bất thường: nghi phun thuốc kích thích.', 2, 'sf', price=3),
            I('ct_a', '🍅', 'Cà chua rổ này', 'đỏ đều, cuống còn xanh, cầm chắc tay', True, 'Quên mua cà chua nấu canh.', 1, price=4),
            I('ct_b', '🍅', 'Cà chua rổ kia', 'đỏ mọng, có quả nứt, nhũn một bên', False, 'Cà chua nhũn, để một hôm đã hỏng.', 1, price=3),
            I('dua', '🍍', 'Nửa quả dứa', 'mắt to, thơm nhẹ, cho canh chua', True, 'Canh chua mà quên dứa.', 1, price=3),
            I('cai', '🥦', 'Cải ngọt', 'tươi, nhưng không có trong danh sách', False, 'Mua thêm cải ngọt không có trong danh sách.', 1, price=3),
            I('hanh', '🌿', 'Hành lá, rau thơm', 'cô Năm cho thêm, không lấy tiền', None, price=0, say='Cô Năm dúi thêm nắm hành lá, rau thơm.'),
        ], lead='Chọn đúng thứ trong danh sách, đúng loại tươi.', done='Rau tươi, đủ danh sách.'),
        pick('ca', 'Hàng cá chú Thịnh', '🐟 Lấy con này', [
            I('ca_a', '🐟', 'Cá diêu hồng chậu nước', 'mắt trong, mang đỏ tươi, ấn vào thịt đàn hồi', True, 'Không mua cá thì lấy gì nấu canh chua.', 2),
            I('ca_b', '🐟', 'Cá diêu hồng khay đá', 'mắt đục, mang thâm, ấn vào lõm không lên', False, 'Cá ươn: nấu lên tanh, ăn dễ đau bụng.', 2, 'sf'),
            I('tom', '🦐', 'Tôm sú', 'tươi rói, chú Thịnh mời mãi', False, 'Mua tôm về nhà có bé Su dị ứng, chị Thảo phải đem cho hàng xóm.', 1),
        ], lead='Chọn một con cá cho nồi canh chua.', done='Con cá còn quẫy trong túi.'),
        haggle('gia', 'Trả giá con cá', 6, 'Con cá diêu hồng vừa chọn', 16, 13, lead='Chú Thịnh nói giá. Mua luôn, hay trả giá?',
               when=['ca', ['ca_a', 'ca_b']], skip='Không mua cá nên chẳng phải trả giá.'),
        choose('can', 'Cân lại cho chắc', 'Chú Thịnh cân nhanh như gió: “Tám lạng nhé!” Đầu chợ có cái cân đối chứng của ban quản lý chợ.', [
            C('check', 'Mang ra cân đối chứng', 'good', 'Cân đối chứng chỉ bảy lạng. Chú Thịnh gãi đầu, bù thêm cho đủ.'),
            C('trust', 'Thôi, chú bán lâu năm rồi', 'ok', 'Về nhà chị Thảo cân lại.', 1, 'Về nhà cân lại thiếu một lạng: “Bị cân điêu rồi em ơi.”'),
            C('scold', 'Mắng chú Thịnh ăn gian giữa chợ', 'bad', 'Cả dãy hàng cá quay sang nhìn.', 1, 'Chưa cân lại đã mắng người ta ăn gian giữa chợ.', 'mn')]),
        receipt(),
    ], note='Danh sách: rau muống, cà chua, nửa quả dứa, một con cá. Chọn đồ tươi, trả giá vừa phải, cân lại, ghi sổ đúng.',
        budget=40, shop=['1 bó rau muống', '3 quả cà chua', 'Nửa quả dứa', '1 con cá diêu hồng']),
    V('m_khach', 'market', 0, 'Đi chợ đãi khách', '“Trưa nay cô chú dưới quê lên. Mua con gà ta luộc, cân thịt ba chỉ, rau cải với chanh ớt. Chị đưa 90 xu.”', [
        pick('rau', 'Sạp rau cô Năm', '🛒 Trả tiền rau', [
            I('cai_a', '🥬', 'Rau cải ngọt bó này', 'lá xanh, cuống mập, gốc còn đất', True, 'Quên mua rau cải.', 1, price=4),
            I('cai_b', '🥬', 'Rau cải bó kia', 'lá úa vàng, gốc thâm, ngâm nước cho tươi', False, 'Rau cải ngâm nước cho tươi, về tới nhà đã nhũn.', 1, price=3),
            I('chanh', '🍋', 'Chanh, ớt', 'chanh vỏ mỏng, mọng nước', True, 'Gà luộc mà quên chanh ớt chấm muối.', 1, price=2),
            I('la_chanh', '🌿', 'Lá chanh', 'cô Năm cho thêm, thái chỉ rắc gà', None, say='Cô Năm cho nắm lá chanh: “Gà luộc thiếu lá chanh là mất ngon.”'),
            I('nam', '🍄', 'Nấm hương khô', 'đắt, không có trong danh sách', False, 'Mua nấm hương đắt tiền không có trong danh sách.', 1, price=8),
        ], lead='Chọn đúng thứ trong danh sách, đúng loại tươi.', done='Rau tươi, chanh mọng.'),
        pick('ga', 'Hàng gà, hàng thịt', '🍗 Lấy hàng', [
            I('ga_a', '🐔', 'Gà ta lồng này', 'chân nhỏ vàng nhạt, da mỏng, mào đỏ tươi', True, 'Đãi khách mà không có gà.', 2),
            I('ga_b', '🐔', 'Gà làm sẵn da vàng óng', 'da vàng bóng bất thường, chà tay ra màu', False, 'Gà nhuộm màu bán làm gà ta.', 2, 'sf'),
            I('thit_a', '🥓', 'Ba chỉ miếng này', 'hồng tươi, mỡ trắng, ấn vào đàn hồi', True, 'Quên mua thịt ba chỉ.', 1),
            I('thit_b', '🥓', 'Ba chỉ miếng kia', 'thâm, mặt nhớt, có mùi lạ, rẻ hơn hẳn', False, 'Thịt để từ hôm qua, mặt nhớt.', 2, 'sf'),
        ], lead='Chọn con gà và miếng thịt.', done='Gà ta, thịt tươi.'),
        haggle('gia', 'Trả giá con gà', 6, 'Con gà ta và cân thịt ba chỉ', 52, 44, lead='Chú Thịnh hét giá. Khách sắp tới, mua nhanh hay trả giá?'),
        receipt(),
    ], note='Danh sách: rau cải, chanh ớt, một con gà ta, một cân ba chỉ.', mods=('guests',), min_day=2, weight=2,
        budget=90, shop=['1 bó rau cải', 'Chanh, ớt', '1 con gà ta', '1 cân thịt ba chỉ']),
    V('m_om', 'market', 1, 'Chợ cho người ốm', 'Bà Lành mệt, chị Thảo nhắn: “Mua thịt thăn về nấu cháo cho bà, bí đỏ với cà rốt cho bé Cốm, chục trứng. Chị gửi 45 xu ở hộp.”', [
        pick('rau', 'Sạp rau cô Năm', '🛒 Trả tiền rau', [
            I('bi', '🎃', 'Bí đỏ', 'cuống khô, vỏ cứng, nặng tay', True, 'Quên bí đỏ cho bé Cốm.', 1, price=3),
            I('carot_a', '🥕', 'Cà rốt bó này', 'củ chắc, đỏ cam, không mọc rễ', True, 'Quên cà rốt.', 1, price=2),
            I('carot_b', '🥕', 'Cà rốt bó kia', 'mềm oặt, mọc rễ tua tủa', False, 'Cà rốt héo mềm, nấu cho bé không ngọt.', 1, price=2),
            I('trung_a', '🥚', 'Chục trứng gà ta', 'vỏ nhám, soi đèn trong, không vết rạn', True, 'Quên mua trứng.', 1, price=8),
            I('trung_b', '🥚', 'Chục trứng rẻ', 'vỏ bóng, lắc nghe óc ách', False, 'Trứng để lâu, lắc óc ách, đập ra lòng lỏng.', 1, 'sf', price=6),
            I('keo', '🍭', 'Kẹo mút cho bé Su', 'bé Su dặn mua', False, 'Lấy tiền chợ mua kẹo cho bé Su, chị Thảo đã dặn không.', 1, 'hn', price=2),
        ], lead='Đồ cho người ốm và em bé: chọn thật kỹ.', done='Rau củ tươi, trứng mới.'),
        pick('thit', 'Hàng thịt chú Thịnh', '🥩 Lấy thịt', [
            I('than', '🥩', 'Thịt thăn, nhờ xay ngay trước mặt', 'đỏ hồng, chú Thịnh xay tại chỗ', True, 'Không có thịt nấu cháo cho bà.', 2),
            I('xay_san', '🥩', 'Thịt xay sẵn trong khay', 'màu thâm, không biết xay từ bao giờ', False, 'Thịt xay sẵn không rõ từ bao giờ, nấu cho người ốm và em bé.', 2, 'sf'),
        ], lead='Thịt nấu cháo cho bà, cho bé.', done='Thịt thăn xay tươi.'),
        haggle('gia', 'Trả giá thịt thăn', 6, 'Ba lạng thịt thăn xay', 15, 12),
        receipt(),
    ], note='Danh sách: bí đỏ, cà rốt, chục trứng, ba lạng thịt thăn.', mods=('sick',), min_day=3, weight=2,
        budget=45, shop=['1 quả bí đỏ', '1 bó cà rốt', '1 chục trứng', '3 lạng thịt thăn']),
    V('m_ram', 'market', 1, 'Đồ cúng rằm', 'Bà Lành dặn: “Mai rằm. Mua bó cúc vàng, nải chuối xanh với quả bưởi. Hoa phải tươi. Bà đưa 35 xu.”', [
        pick('hoa', 'Hàng hoa, hàng quả', '💐 Lấy hàng', [
            I('cuc_a', '🌼', 'Bó cúc vàng này', 'cánh cứng, nhụy vàng, cuống còn nhựa', True, 'Quên mua hoa cúc.', 1),
            I('cuc_b', '🌼', 'Bó cúc vàng kia', 'nở bung, cuống thâm đen, ngâm nước thuốc', False, 'Hoa ngâm thuốc, cắm một hôm đã rũ, bà chê.', 1),
            I('ly', '💮', 'Hoa ly', 'thơm nồng, đắt', False, 'Bà Lành không ưa mùi hoa ly trên bàn thờ.', 1, price=12),
            I('chuoi_a', '🍌', 'Nải chuối xanh', 'xanh đều, quả mập, cuống tươi', True, 'Mâm cúng thiếu nải chuối.', 1, price=6),
            I('chuoi_b', '🍌', 'Nải chuối chín vàng', 'chín nẫu, có quả dập', False, 'Chuối chín nẫu, để lên bàn thờ hai hôm đã đen.', 1, price=4),
            I('buoi', '🟢', 'Quả bưởi', 'tròn đều, vỏ căng, nặng tay', True, 'Quên quả bưởi.', 1, price=7),
        ], lead='Đồ cúng: tươi, đẹp, đúng ý bà.', done='Hoa tươi, quả đẹp.'),
        haggle('gia', 'Trả giá bó cúc', 4, 'Bó cúc vàng mười bông', 10, 8, lead='Cô Năm bán hoa giúp chị gái. Mua luôn, hay trả giá?'),
        receipt(),
    ], note='Danh sách: bó cúc vàng, nải chuối xanh, quả bưởi.', min_day=3,
        budget=35, shop=['1 bó cúc vàng', '1 nải chuối xanh', '1 quả bưởi']),
    V('m_sieu_thi', 'market', 0, 'Đi siêu thị', '“Em ghé siêu thị mua giúp chị hộp sữa tươi không đường cho Cốm, chai nước mắm, gói giấy vệ sinh với vỉ trứng. Chị đưa 50 xu.”', [
        pick('ke', 'Kệ hàng siêu thị', '🛒 Ra quầy', [
            I('sua_a', '🥛', 'Sữa tươi không đường', 'hạn dùng còn mười ngày', True, 'Quên sữa cho bé Cốm.', 1, price=9),
            I('sua_b', '🥛', 'Sữa tươi không đường, giảm nửa giá', 'hạn dùng: hôm nay', False, 'Sữa hết hạn ngay hôm nay, sáng mai mở ra đã chua.', 2, 'sf', price=5),
            I('sua_c', '🧃', 'Sữa dâu có đường', 'bé Su thích, không có trong danh sách', False, 'Mua sữa có đường, chị dặn sữa không đường cho Cốm.', 1, price=9),
            I('mam', '🍶', 'Nước mắm nhãn quen của nhà', 'chai thủy tinh, 40 độ đạm', True, 'Quên mua nước mắm.', 1, price=12),
            I('giay', '🧻', 'Giấy vệ sinh 10 cuộn', 'loại nhà vẫn dùng', True, 'Quên giấy vệ sinh.', 1, price=10),
            I('km', '🎁', 'Thêm gói giấy thứ hai “mua 2 tặng 1”', 'tủ còn đầy giấy', False, 'Ham khuyến mãi, mua thêm thứ nhà chưa cần.', 1, price=10),
            I('trung', '🥚', 'Vỉ trứng gà mười quả', 'mở hộp xem, không quả nào nứt', True, 'Quên mua trứng.', 1, price=7),
        ], lead='Xem hạn dùng, đúng danh sách. Khuyến mãi chưa chắc đã lợi.', done='Đủ danh sách, hạn dùng còn dài.'),
        choose('quay', 'Quầy thu ngân', 'Hóa đơn in ra, bạn liếc thấy hộp sữa bị tính hai lần. Hàng người phía sau đang giục.', [
            C('xem', 'Nhờ thu ngân kiểm lại, bỏ món tính trùng', 'good', 'Chị thu ngân xin lỗi, bấm lại hóa đơn.'),
            C('ke', 'Thôi, người sau đang giục', 'bad', 'Về nhà chị Thảo xem hóa đơn mới thấy.', 1, 'Không xem lại hóa đơn, mất oan tiền một hộp sữa.'),
            C('cai', 'Nói to cho cả hàng nghe là siêu thị ăn gian', 'bad', 'Quản lý phải ra xin lỗi, cả hàng ngoái nhìn.', 1, 'Chưa hỏi đã to tiếng với thu ngân.', 'mn')]),
        receipt(),
    ], note='Danh sách: sữa tươi không đường, nước mắm, giấy vệ sinh, vỉ trứng. Xem hạn dùng, đừng ham khuyến mãi, đọc lại hóa đơn.',
        min_day=2, budget=50, shop=['1 hộp sữa tươi không đường', '1 chai nước mắm', '1 gói giấy vệ sinh', '1 vỉ trứng gà']),
]

COOK = [
    V('c_trua', 'cook', 0, 'Nấu bữa trưa', '“Trưa nay canh chua cá, rau muống xào nhé em. Mười một rưỡi cả nhà ăn.”', [
        'RICE',
        _prep(),
        _portions('chia', fish=True),
        order('nau', 'Nấu cho kịp 11:30', '🍳 Nấu', [
            O('com', '🍚', 'Cắm nồi cơm'), O('canh', '🍲', 'Nấu canh chua cá'), O('nhat', '🥬', 'Nhặt, rửa rau muống'),
            O('xao', '🔥', 'Xào rau muống'), O('mam', '🍽️', 'Dọn mâm, mời cả nhà'),
            O('mo', '🫗', 'Đổ mỡ thừa xuống bồn rửa', (1, 'Đổ mỡ xuống bồn rửa: mai lại phải gọi chú Hai thông cống.', 'cr', False)),
        ], [('com', 'xao', 1, 'Cắm cơm muộn: rau xào xong cả nhà còn ngồi chờ cơm chín.', 'cr'),
            ('canh', 'xao', 1, 'Món lâu chín phải bắc bếp trước, rau xào để cuối cho nóng giòn.', 'cr'),
            ('nhat', 'xao', 1, 'Chưa nhặt rau sao xào được.', 'cr'),
            ('xao', 'mam', 1, 'Dọn mâm từ sớm, tới lúc ăn rau xào đã nguội ngắt.', 'cr')],
            lead='Bấm theo thứ tự sẽ làm. Bấm nhầm thì bấm lại món cuối để bỏ.'),
        _talk_back('nem', 'Bà nếm canh', 'Bà Lành nếm thìa canh: “Nhạt như nước ốc! Cho thêm thìa muối vào nồi.”',
                   ('Múc riêng bát của bà, nói khéo bác sĩ dặn ăn nhạt, để bát nước mắm cho cả nhà', 'Bà lườm một cái rồi cũng ăn. Cả nhà tự chấm thêm.'),
                   ('Thêm chút nước mắm vào bát của bà thôi', 'Bà ăn ngon miệng.', 'Bà đang kiêng mặn mà vẫn thêm nước mắm.'),
                   ('Nêm thêm muối cả nồi cho bà vui', 'Cả nồi mặn chát.', 'Chiều bà nêm mặn: tối huyết áp bà lên 160.'),
                   ('“Bác sĩ cấm rồi, bà đừng đòi”', 'Bà dỗi, bỏ nửa bát.', 'Nói cộc với bà, bà dỗi bỏ bữa.')),
    ], note='Thực đơn: canh chua cá, rau muống xào. Bà ăn nhạt; bé Su ăn cá phải gỡ xương; bé Cốm ăn cháo.'),
    V('c_tom', 'cook', 0, 'Bữa tối có tôm rim', '“Tối nay tôm rim với canh bí, rau cải luộc. Nhớ phần bé Su nhé em, bé dị ứng tôm đấy.”', [
        'RICE',
        _portions('chia', shrimp=True),
        pick('rieng', 'Nấu phần không tôm cho bé Su', '🍳 Nấu xong', [
            I('chao_rieng', '🍳', 'Dùng chảo riêng rán trứng cho bé Su', 'chảo sạch, chưa dính tôm', True, 'Rán trứng cho bé Su bằng chảo vừa rim tôm.', 2, 'sf'),
            I('rua_tay', '🧼', 'Rửa tay sau khi bóc tôm', 'trước khi động vào đồ của bé', True, 'Tay dính tôm cầm sang bát của bé Su.', 2, 'sf'),
            I('dua_chung', '🥢', 'Dùng luôn đôi đũa gắp tôm để gắp trứng', 'cho đỡ rửa', False, 'Đũa dính tôm gắp sang đĩa của bé Su, bé ngứa môi.', 2, 'sf'),
            I('xa', '🍽️', 'Để đĩa trứng của bé xa đĩa tôm', 'bé hay với', True, 'Đĩa tôm sát chỗ bé Su ngồi, bé với lấy một con.', 2, 'sf'),
            I('nem_ngot', '🍬', 'Thêm thìa đường vào canh bí cho ngọt', 'bé Su thích ngọt', False, 'Cả nồi canh có đường, bà Lành tiểu đường ăn phải.', 1, 'sf'),
        ], lead='Chọn những việc sẽ làm cho bữa tối an toàn.', done='Phần của bé Su sạch tôm, tách riêng.'),
        choose('nhan', 'Tin nhắn lúc sáu giờ', 'Anh Dũng nhắn: “Anh đau dạ dày quá, tối nay em nấu cho anh bát cháo trắng nhé.” Cơm sắp chín, tôm đang rim.', [
            C('chao', 'Nấu thêm nồi cháo nhỏ, phần anh không ớt', 'good', 'Anh Dũng húp bát cháo nóng, cảm ơn rối rít.'),
            C('mem', 'Nhắn lại: em dở tay, anh ăn cơm mềm với canh nhé', 'ok', 'Anh Dũng ăn tạm bát cơm chan canh.'),
            C('lo', 'Đang bận, lờ tin nhắn đi', 'bad', 'Anh Dũng về thấy không có cháo, lẳng lặng úp mì.', 1, 'Nhắn mà không ai trả lời, tối úp mì gói.', 'mn')]),
    ], note='Thực đơn: tôm rim, canh bí, rau cải luộc. Bé Su dị ứng tôm: phần riêng, chảo riêng, đũa riêng.', min_day=2),
    V('c_chao', 'cook', 1, 'Cháo cho bà', 'Bà Lành sốt nhẹ, mệt: “Bà chẳng muốn ăn gì cả.” Chị Thảo dặn nấu cháo thịt băm cho bà.', [
        choose('nau', 'Nấu cháo', 'Gạo, thịt thăn băm, hành lá có sẵn. Mười một giờ bà phải ăn để uống thuốc.', [
            C('ninh', 'Rang gạo cho thơm, ninh nhừ với thịt băm', 'good', 'Nồi cháo thơm, sánh, nhừ.'),
            C('goi', 'Pha gói cháo ăn liền cho nhanh', 'bad', 'Cháo gói mặn chát.', 1, 'Cháo gói mặn, bà khát nước cả buổi.', 'sf'),
            C('com', 'Nấu cơm nát với nước canh cho nhanh', 'ok', 'Bà ăn được vài thìa.', 1, 'Cơm nát chan canh, bà ăn chẳng thấy ngon.')]),
        pick('bat', 'Bát cháo của bà', '🥣 Mang cháo lên', [
            I('hanh', '🌿', 'Hành lá thái nhỏ', 'cho thơm', None, say='Rắc chút hành lá cho thơm.'),
            I('gung', '🫚', 'Vài sợi gừng thái chỉ', 'cho ấm bụng', None, say='Mấy sợi gừng cho ấm bụng.'),
            I('duong', '🍬', 'Thìa đường cho bà dễ ăn', 'bà thích ngọt', False, 'Bà tiểu đường mà cháo bỏ đường.', 2, 'sf'),
            I('mam', '🧂', 'Thìa nước mắm cho đậm', 'bà chê nhạt', False, 'Bà đang ốm, huyết áp cao mà cháo nêm đậm.', 1, 'sf'),
        ], lead='Cho gì vào bát cháo của bà?', done='Bát cháo nhạt, thơm.'),
        order('an', 'Cho bà ăn', '🥄 Xong bữa', [
            O('do', '🛏️', 'Đỡ bà ngồi dậy, kê gối sau lưng'), O('thoi', '🌬️', 'Thổi nguội, thử ở môi trên mu bàn tay'),
            O('dut', '🥄', 'Đút từng thìa nhỏ, chậm'), O('nuoc', '🥛', 'Cho bà uống ngụm nước ấm'),
            O('nam', '🛌', 'Cho bà ăn khi còn nằm ngửa', (2, 'Bón cháo lúc bà còn nằm ngửa: bà sặc, ho mãi.', 'sf', False)),
        ], [('do', 'dut', 2, 'Bà còn nằm đã bón: bà sặc cháo.', 'sf'), ('thoi', 'dut', 1, 'Cháo còn nóng đã bón, bà bỏng lưỡi.', 'sf'),
            ('dut', 'nuoc', 1, 'Chưa ăn đã cho uống no nước, bà ăn được hai thìa.', 'cr')]),
        _talk_back('doi', 'Bà đòi bún riêu', 'Bà đẩy bát: “Cháo nhạt thế ai ăn. Ra đầu ngõ mua bát bún riêu cho bà, nhiều mắm tôm vào.”',
                   ('Ngồi cạnh, kể chuyện, hứa khỏi ốm sẽ đưa bà đi ăn bún riêu', 'Bà nguýt một cái rồi cũng ăn hết nửa bát.'),
                   ('Xin bà ăn thêm ba thìa rồi tính', 'Bà ăn được ba thìa.', 'Bà ăn được ít quá.'),
                   ('Chạy đi mua bún riêu nhiều mắm tôm', 'Bà ăn ngon lành.', 'Người ốm, huyết áp cao ăn bát bún mắm tôm mặn chát.'),
                   ('“Ốm thì ăn cháo, đòi gì nữa bà”', 'Bà quay mặt vào tường.', 'Nói với người ốm như quát.')),
    ], note='Bà ốm: cháo nhừ, nhạt, không đường. Đỡ bà ngồi dậy trước khi ăn.', mods=('sick',), min_day=3, weight=2),
    V('c_hop', 'cook', 2, 'Cơm hộp cho anh Dũng', '“Mai anh ra công trường cả ngày, em làm giúp anh hộp cơm nhé. Anh đau dạ dày, đừng cho cay.”', [
        pick('mon', 'Món cho hộp cơm', '🍱 Xếp hộp', [
            I('rau', '🥦', 'Rau cải luộc', 'xanh, để được lâu', True, 'Hộp cơm không có miếng rau nào.', 1),
            I('thit', '🍖', 'Thịt rang cháy cạnh', 'khô, mang đi không chảy nước', True, 'Hộp cơm thiếu món mặn.', 1),
            I('trung', '🥚', 'Trứng ốp lòng đào', 'anh thích', False, 'Trứng lòng đào để nửa ngày ngoài công trường, dễ hỏng.', 1, 'sf'),
            I('canh', '🍲', 'Canh chua nhiều nước', 'cho đỡ khô', False, 'Canh đổ lênh láng ra cặp anh Dũng.', 1),
            I('ot', '🌶️', 'Ớt tươi thái sẵn', 'anh vẫn ăn cay', False, 'Anh dặn đau dạ dày, đừng cho cay.', 1, 'sf'),
        ], lead='Hộp cơm mang đi cả ngày: món nào hợp?', done='Hộp cơm khô ráo, không cay.'),
        order('xep', 'Đóng hộp', '🍱 Cất hộp', [
            O('nguoi', '🌬️', 'Để thức ăn nguội bớt'), O('xep', '🍱', 'Xếp cơm, thức ăn vào hộp'),
            O('day', '🔒', 'Đậy nắp kín'), O('cat', '🧊', 'Cất ngăn mát chờ anh lấy'),
        ], [('nguoi', 'day', 1, 'Đậy nắp lúc còn nóng: hơi nước đọng lại, trưa cơm thiu.', 'sf'), ('xep', 'day', 1, 'Đậy nắp rồi mới xếp à?', 'cr'),
            ('day', 'cat', 1, 'Cất tủ khi chưa đậy nắp, cơm khô cong mùi tủ lạnh.', 'cr')]),
        choose('them', 'Chị Thảo dặn thêm', 'Chị Thảo ló đầu vào bếp: “Làm thêm hộp cho chị nhé. Chị đang giảm cân, không ăn cơm trắng.”', [
            C('khoai', 'Thay cơm bằng khoai lang luộc, nhiều rau', 'good', 'Chị Thảo khen hộp cơm “chuẩn ăn kiêng”.'),
            C('it', 'Bớt nửa cơm, thêm rau', 'ok', 'Chị Thảo bảo vẫn nhiều cơm.', 1, 'Dặn không cơm trắng mà vẫn có cơm.'),
            C('quen', 'Xếp y hộp của anh Dũng cho nhanh', 'bad', 'Chị Thảo mở hộp, thở dài.', 1, 'Dặn ăn kiêng mà hộp đầy cơm trắng.', 'mn')]),
    ], note='Hộp cơm mang đi: món khô, không cay; để nguội rồi mới đậy nắp.', min_day=3),
    V('c_khach', 'cook', 0, 'Mâm cơm đãi khách', '“Cô chú dưới quê lên chơi. Gà luộc, thịt rang, canh cải. Mười hai giờ ăn em nhé.”', [
        'RICE',
        _prep(),
        _portions('chia', guest=True),
        order('nau', 'Nấu cho kịp 12:00', '🍳 Nấu', [
            O('luoc', '🐔', 'Luộc gà (nước lạnh, lửa vừa)'), O('com', '🍚', 'Cắm nồi cơm'), O('rang', '🍖', 'Rang thịt'),
            O('canh', '🥬', 'Nấu canh cải'), O('chat', '🔪', 'Chặt gà, bày đĩa'), O('mam', '🍽️', 'Dọn mâm, mời khách'),
        ], [('luoc', 'chat', 1, 'Gà chưa luộc đã chặt?', 'cr'), ('luoc', 'rang', 1, 'Gà luộc lâu nhất, phải bắc trước tiên.', 'cr'),
            ('com', 'mam', 1, 'Cắm cơm sau cùng: khách ngồi chờ cơm.', 'cr'), ('chat', 'mam', 1, 'Mời khách rồi mới chặt gà.', 'cr'),
            ('canh', 'mam', 1, 'Canh nấu sau khi dọn mâm, nguội ngắt cả mâm.', 'cr')]),
        choose('khach', 'Cô chú vào bếp', 'Cô dưới quê vào tận bếp: “Gà luộc thế này là chưa tới. Ở quê cô luộc phải để nguyên con, nhúng nước đá cho da giòn. Làm lại đi cháu.”', [
            C('hoc', 'Cảm ơn cô, nhờ cô chỉ cách nhúng nước đá cho da giòn', 'good', 'Cô vui ra mặt, đứng chỉ từng bước. Da gà vàng giòn.'),
            C('im', 'Dạ dạ cho qua, vẫn làm như cũ', 'ok', 'Cô lắc đầu đi ra.', 1, 'Cô chỉ mà cháu cứ dạ dạ rồi làm theo ý mình.', 'mn'),
            C('cai', '“Nhà này nấu kiểu nhà này cô ạ”', 'bad', 'Cô đỏ mặt đi ra phòng khách.', 2, 'Cãi tay đôi với khách của chủ nhà.', 'mn')]),
    ], note='Mâm có khách: gà luộc, thịt rang, canh cải. Bà vẫn ăn nhạt, bé Cốm ăn cháo.', mods=('guests',), min_day=2, weight=2),
]

DISHES = [
    V('d_trua', 'dishes', 1, 'Rửa bát sau bữa trưa', 'Cả nhà ăn xong. Chồng bát đĩa, nồi chảo, bình sữa của bé Cốm chất đầy bồn.', [
        order('rua', 'Thứ tự rửa', '🧽 Rửa', [
            O('vet', '🗑️', 'Vét thức ăn thừa vào thùng rác'), O('ly', '🥛', 'Rửa ly cốc'), O('bat', '🍽️', 'Rửa bát đĩa'),
            O('noi', '🍳', 'Rửa nồi chảo dầu mỡ'), O('trang', '💧', 'Tráng lại bằng nước sạch'), O('up', '🧺', 'Úp ráo lên giá'),
            O('mo', '🫗', 'Đổ mỡ thừa xuống bồn rửa', (1, 'Mỡ đổ xuống bồn đông lại trong ống, mai bồn tắc.', 'cr', False)),
        ], [('vet', 'bat', 1, 'Chưa vét thức ăn thừa đã rửa: cặn trôi xuống bồn.', 'cr'), ('ly', 'noi', 1, 'Rửa nồi mỡ trước rồi mới rửa ly: ly nào cũng váng mỡ.', 'cr'),
            ('bat', 'noi', 1, 'Rửa nồi chảo trước: nước rửa đầy mỡ, bát đĩa trơn nhờn.', 'cr'), ('noi', 'trang', 1, 'Tráng rồi mới rửa nồi, phải tráng lại lần nữa.', 'cr'),
            ('trang', 'up', 1, 'Úp bát khi còn bọt xà phòng.', 'sf')], lead='Sạch trước, bẩn sau.'),
        sort('dung_cu', 'Rửa món nào bằng gì', '🧴 Xong', (
            ('mem', '🧽', 'Miếng bọt biển mềm'), ('sat', '🪨', 'Búi sắt cọ mạnh'), ('ngam', '🫧', 'Ngâm nước ấm, baking soda'),
            ('ngay', '🔪', 'Rửa riêng ngay, lau khô, cất'), ('tiet', '🍼', 'Cọ riêng, tráng, tiệt trùng')), [
            S('chao', '🍳', 'Chảo chống dính', ('mem',), 'lớp chống dính đã hơi mòn', 'Cọ chảo chống dính bằng búi sắt: tróc cả lớp chống dính.', 2),
            S('noi_chay', '🍲', 'Nồi kho cá cháy đáy', ('ngam', 'sat'), 'cháy một lớp đen', 'Nồi cháy chỉ quệt qua, còn nguyên lớp đen.', 1),
            S('dao', '🔪', 'Dao bếp vừa mài', ('ngay',), 'rất sắc', 'Dao sắc ngâm lẫn trong chậu, thò tay vào suýt đứt.', 2, 'sf'),
            S('binh', '🍼', 'Bình sữa của bé Cốm', ('tiet',), 'còn cặn sữa', 'Bình sữa của bé chỉ tráng qua như bát đĩa.', 2, 'sf'),
            S('ly_tt', '🥂', 'Ly thủy tinh', ('mem',), 'mỏng', 'Ly thủy tinh cọ búi sắt xước mờ cả.', 1),
        ], lead='Mỗi món một cách rửa.'),
        choose('me', 'Chiếc bát men lam', 'Đang rửa thì chiếc bát men lam của bà Lành, của hồi môn bà mang về nhà chồng, va vào vòi nước, mẻ một miếng.', [
            C('noi', 'Để riêng, nói thật với bà khi bà ngủ dậy', 'good', 'Bà tiếc lắm, nhưng bảo: “Nói thật thế là được.” Chị Thảo đem đi gắn sơn mài.'),
            C('giau', 'Úp tận đáy chồng bát, ai thấy thì thấy', 'bad', 'Một tuần sau bà tìm ra.', 2, 'Giấu bát mẻ của bà, bà tìm ra còn buồn hơn.', 'hn'),
            C('do', 'Bảo tại bé Su nghịch', 'bad', 'Bé Su bị mắng oan, khóc cả tối.', 3, 'Đổ cho bé Su làm mẻ bát, bé bị mắng oan.', 'hn')]),
    ], note='Rửa bát: vét thức ăn thừa, sạch trước bẩn sau, đồ của bé riêng, dao rửa ngay.'),
    V('d_tiec', 'dishes', 0, 'Dọn rửa sau bữa có khách', 'Khách về. Hai mâm bát đĩa, xoong nồi, ly bia, khay hoa quả bày la liệt.', [
        order('rua', 'Thứ tự dọn', '🧽 Rửa', [
            O('gom', '🗑️', 'Gom thức ăn thừa, phân loại rác'), O('ly', '🍺', 'Rửa ly bia, cốc nước'), O('bat', '🍽️', 'Rửa bát đĩa'),
            O('noi', '🍲', 'Rửa xoong nồi'), O('lau', '🧽', 'Lau bàn, quét sàn'),
            O('bo', '🗑️', 'Bỏ cả đĩa gà luộc còn nguyên vào thùng rác', (1, 'Đĩa gà còn nguyên bỏ đi, bà Lành tiếc đứt ruột.', 'cr', False)),
        ], [('gom', 'bat', 1, 'Chưa gom đồ thừa đã rửa, cặn trôi tắc bồn.', 'cr'), ('ly', 'noi', 1, 'Rửa xoong mỡ trước rồi mới rửa ly.', 'cr'),
            ('bat', 'noi', 1, 'Rửa xoong trước, bát đĩa trơn nhờn.', 'cr'), ('noi', 'lau', 1, 'Lau sàn xong rồi mới rửa xoong, nước bắn bẩn sàn lại.', 'cr')]),
        choose('thua', 'Đồ ăn thừa', 'Bà Lành: “Giữ lại hết, mai hâm lại ăn.” Chị Thảo: “Bỏ hết đi, ăn đồ hâm đi hâm lại không tốt.” Hai người cùng nhìn bạn.', [
            C('hop', 'Xin ý chị Thảo trước mặt bà: món còn ngon chia hộp cất tủ, món đã hỏng mới bỏ', 'good', 'Bà gật gù, chị Thảo cũng ưng. Không ai mất lòng.'),
            C('ba', 'Nghe bà, cất hết vào tủ', 'ok', 'Chị Thảo nhìn tủ lạnh chật cứng, thở dài.', 1, 'Tủ lạnh nhét đầy đồ thừa không đậy.', 'cr'),
            C('chi', 'Nghe chị Thảo, đổ hết', 'ok', 'Bà Lành dỗi cả tối.', 1, 'Đổ hết đồ ăn còn ngon trước mặt bà.', 'mn'),
            C('ke', '“Hai người thống nhất đi rồi bảo cháu”', 'bad', 'Bà và chị Thảo cùng lườm.', 1, 'Đẩy chuyện lại cho hai người trước mặt nhau.', 'mn')]),
    ], note='Sau bữa khách: gom đồ thừa, sạch trước bẩn sau, khéo chuyện đồ ăn thừa.', mods=('guests',), min_day=2, weight=2),
]

LAUNDRY = [
    V('l_ca_nha', 'laundry', 0, 'Giặt đồ cả nhà', '“Giỏ đồ đầy rồi em ơi. Áo sơ mi của anh Dũng mai đi họp, áo lụa của chị giặt tay nhé.”', [
        sort('loai', 'Phân loại đồ giặt', '🧺 Chia mẻ', (
            ('trang', '⚪', 'Máy – mẻ trắng'), ('mau', '🟤', 'Máy – mẻ màu'), ('tay', '🫧', 'Giặt tay nhẹ, riêng'), ('be', '👶', 'Đồ em bé riêng')), [
            S('so_mi', '👔', 'Sơ mi trắng của anh Dũng', ('trang',), 'cổ áo hơi ố', 'Sơ mi trắng giặt chung đồ màu, ngả xám.', 1),
            S('ao_do', '👕', 'Áo phông đỏ mới mua của bé Su', ('tay',), 'mới, lần đầu giặt', 'Áo đỏ mới ra màu loang sang đồ khác.', 1,
              wrong={'trang': (3, 'Áo đỏ mới vào mẻ trắng: sơ mi của anh Dũng loang hồng cả!', 'cr', False)}),
            S('jean', '👖', 'Quần jean của chị Thảo', ('mau',), 'màu xanh đậm', 'Quần jean ra màu xanh vào mẻ khác.', 2),
            S('lua', '👚', 'Áo lụa của chị Thảo', ('tay',), 'nhãn: giặt tay, nước lạnh', 'Áo lụa vào máy vắt, nhăn nhúm, sờn vải.', 2),
            S('be', '🧸', 'Quần áo bé Cốm', ('be',), 'da bé dễ mẩn', 'Đồ bé giặt chung nước giặt mạnh, bé mẩn ngứa.', 1, 'sf'),
            S('khan', '🧻', 'Khăn tắm', ('mau', 'trang'), 'khăn màu kem', 'Khăn tắm giặt tay mỏi nhừ cả tay.', 1),
        ], lead='Chạm từng món rồi chọn mẻ.'),
        pick('truoc', 'Trước khi cho vào máy', '🔄 Bật máy giặt', [
            I('tui', '👖', 'Móc hết túi quần áo', 'quần của anh Dũng hơi cộm', True, 'Không móc túi: tờ giấy trong túi quần anh Dũng nát bươm, dính đầy máy.', 2,
              say='Trong túi quần anh Dũng có thứ gì đó…'),
            I('khoa', '🤐', 'Kéo khóa, cài cúc', 'cho đỡ móc vào đồ khác', True, 'Khóa quần móc rách áo lụa.', 1),
            I('lon', '🔃', 'Lộn trái quần jean, áo in hình', 'cho đỡ bạc màu', True, 'Áo in hình bong tróc chữ.', 1),
            I('tay_trang', '🧴', 'Đổ thêm thuốc tẩy cho trắng hết', 'cả mẻ màu', False, 'Thuốc tẩy vào mẻ màu: quần áo loang lổ từng mảng.', 2),
            I('nhoi', '🧺', 'Nhồi đầy lồng giặt cho đỡ tốn điện', 'còn nửa giỏ', False, 'Lồng giặt nhồi chặt, đồ không sạch, máy rung bần bật.', 1),
        ], lead='Chọn những việc sẽ làm.', done='Máy chạy êm.'),
        choose('tim', 'Thứ trong túi quần', 'Trong túi quần anh Dũng có một chiếc nhẫn vàng nhỏ và tờ giấy hẹn khám ở bệnh viện.', [
            C('ban', 'Để lên bàn chị Thảo, nhắn tin báo ngay', 'good', 'Anh Dũng thở phào: “Anh tìm cả tuần nay, nhẫn cưới đấy!”'),
            C('ngan', 'Cất tạm vào ngăn kéo, tối nhớ thì nói', 'ok', 'Tối quên nói, hai vợ chồng lục tung nhà.', 1, 'Thấy nhẫn mà cất đi không nói, cả nhà tìm mãi.', 'hn'),
            C('giu', 'Rơi trong máy giặt ai biết, giữ luôn', 'bad', 'Anh Dũng nhớ ra nhẫn ở túi quần, hỏi thẳng.', 3, 'Giữ chiếc nhẫn cưới tìm được khi giặt đồ.', 'hn'),
        ], when=['truoc', 'tui'], skip='Không móc túi nên chẳng thấy gì. Tờ giấy hẹn khám nát trong máy.'),
        choose('phoi', 'Phơi đồ', 'Trưa nắng gắt 36 độ. Sân thượng có chỗ nắng, chỗ râm.', [
            C('ram', 'Lộn trái đồ màu, phơi chỗ râm thoáng; áo lụa phơi trong bóng mát', 'good', 'Chiều đồ khô, màu vẫn tươi.'),
            C('nang', 'Phơi hết ra nắng cho nhanh khô', 'ok', 'Đồ khô nhanh.', 1, 'Đồ màu phơi nắng gắt bạc cả mặt phải.'),
            C('may', 'Để trong máy tới chiều phơi một thể', 'bad', 'Chiều mở máy ra mùi ẩm mốc.', 2, 'Đồ ướt ủ trong máy nửa ngày, hôi mùi mốc.')]),
    ], note='Giặt: chia mẻ trắng, màu, giặt tay, đồ bé; móc túi trước khi giặt.'),
    V('l_vay', 'laundry', 0, 'Váy lụa đi đám cưới', '“Tối mai chị đi đám cưới. Em giặt giúp chị cái váy lụa, nhẹ tay thôi nhé, váy đắt lắm.”', [
        pick('nhan', 'Đọc nhãn, chuẩn bị', '🫧 Giặt', [
            I('doc', '🏷️', 'Đọc nhãn mác trên váy', 'giặt tay, nước lạnh, không vắt, không sấy', True, 'Không đọc nhãn mác mà giặt theo ý mình.', 1),
            I('lanh', '💧', 'Chậu nước lạnh, nước giặt dịu nhẹ', 'nước giặt cho đồ lụa', True, 'Giặt lụa bằng nước giặt thường.', 1),
            I('nong', '♨️', 'Ngâm nước ấm cho sạch nhanh', 'nước ấm tay', False, 'Nước ấm làm lụa co, phai màu.', 2),
            I('vo', '✊', 'Vò mạnh cổ áo cho sạch', 'cổ có vết phấn', False, 'Vò mạnh, lụa xước sờn cả cổ.', 1),
        ], lead='Chọn những việc sẽ làm.', done='Váy giặt nhẹ nhàng, sạch.'),
        choose('son', 'Vết son trên cổ váy', 'Cổ váy có vệt son môi hồng.', [
            C('cham', 'Chấm nhẹ nước rửa tẩy trang lên khăn trắng, thấm từ ngoài vào', 'good', 'Vết son nhạt dần rồi mất hẳn.'),
            C('tay', 'Đổ thuốc tẩy vào chỗ vết son', 'bad', 'Vệt son mất, kéo theo cả màu váy.', 3, 'Thuốc tẩy ăn mất màu váy lụa.'),
            C('ke', 'Để nguyên, giặt mãi cũng không ra', 'ok', 'Vệt son mờ đi chút ít.', 1, 'Vết son vẫn còn trên cổ váy.')]),
        choose('la', 'Là váy', 'Váy khô, hơi nhăn. Bàn là có nấc nhiệt cho lụa.', [
            C('thap', 'Là mặt trái, nấc lụa, lót khăn mỏng', 'good', 'Váy phẳng, bóng mượt.'),
            C('nong', 'Là nóng cho phẳng nhanh', 'bad', 'Một mảng lụa bóng lên, cháy xém.', 2, 'Bàn là nóng làm cháy bóng váy lụa.'),
            C('treo', 'Treo trong nhà tắm lúc chị Thảo tắm cho hơi nước làm phẳng', 'ok', 'Váy đỡ nhăn phần nào.', 1, 'Váy vẫn còn nếp nhăn.')]),
    ], note='Váy lụa: đọc nhãn, nước lạnh, không vắt, là nhiệt thấp mặt trái.', min_day=2),
    V('l_nom', 'laundry', 1, 'Mùa nồm', 'Trời nồm, tường sàn đổ mồ hôi. Chăn của bà ẩm, đồ phơi ba hôm chưa khô, sàn trơn như đổ dầu.', [
        choose('phoi', 'Phơi đồ ngày nồm', 'Ngoài trời ẩm ướt, không có nắng. Nhà có quạt, có điều hòa chế độ khô.', [
            C('trong', 'Phơi trong phòng đóng cửa, bật điều hòa chế độ khô, quạt thổi', 'good', 'Tối đồ đã khô.'),
            C('ngoai', 'Cứ phơi ngoài sân, kiểu gì chả khô', 'bad', 'Ba hôm đồ vẫn ướt, ám mùi.', 1, 'Đồ phơi ngoài trời nồm ba hôm vẫn hôi.'),
            C('chat', 'Phơi chật kín trên một sào cho gọn', 'ok', 'Đồ khô chậm.', 1, 'Đồ phơi sát nhau, chỗ khô chỗ ẩm.')]),
        pick('chong', 'Chống nồm trong nhà', '🏠 Xong', [
            I('dong', '🚪', 'Đóng kín cửa khi trời nồm', 'hơi ẩm từ ngoài vào', True, 'Mở toang cửa ngày nồm, hơi ẩm tràn vào nhà.', 1),
            I('kho', '🧽', 'Lau sàn bằng khăn khô, lau hai lượt', 'sàn trơn', True, 'Sàn trơn không lau khô, bà Lành suýt ngã.', 2, 'sf'),
            I('mo', '🌬️', 'Mở toang cửa cho thoáng', 'cho bay mùi', False, 'Mở cửa giữa trời nồm, cả nhà ướt nhẹp.', 1),
            I('tham', '🧴', 'Trải thảm chống trơn ở cửa nhà tắm', 'chỗ bà hay đi', True, 'Không trải thảm chống trơn chỗ bà đi.', 1, 'sf'),
            I('ban', '👵', 'Dìu bà khi bà đi lại trong nhà', 'sàn trơn', None, say='Bạn dìu bà đi vệ sinh, bà gật gù.'),
        ], lead='Chọn những việc sẽ làm.', done='Nhà khô ráo hơn hẳn.'),
        choose('chan', 'Chăn của bà', 'Chăn bông của bà Lành ẩm, có mùi.', [
            C('say', 'Mang ra tiệm giặt sấy đầu ngõ, xin tiền chị Thảo trước', 'good', 'Tối bà đắp chăn khô thơm.'),
            C('trai', 'Trải chăn trên giường, bật quạt cho khô', 'ok', 'Chăn vẫn hơi ẩm.', 1, 'Chăn bà đắp vẫn ẩm, bà ho.', 'sf'),
            C('ke', 'Để thế, bà đắp mãi quen rồi', 'bad', 'Bà đắp chăn ẩm, sáng dậy ho sù sụ.', 2, 'Để bà đắp chăn ẩm mốc.', 'sf')]),
    ], note='Ngày nồm: phơi trong nhà có máy, đóng cửa, lau sàn khô, chống trơn cho bà.', mods=('rain',), min_day=2, weight=2),
    V('l_gap', 'laundry', 0, 'Gấp, cất quần áo', 'Rổ đồ khô to đùng trên sofa. Chị Thảo dặn: “Cất đúng tủ giúp chị, sáng nào cũng tìm áo mỏi mắt.”', [
        sort('cat', 'Cất vào tủ nào', '🗄️ Xong', (
            ('ba', '👵', 'Tủ của bà'), ('vc', '👫', 'Tủ anh chị'), ('su', '👧', 'Tủ bé Su'), ('com', '👶', 'Ngăn đồ bé Cốm'), ('khan', '🧻', 'Tủ khăn')), [
            S('ao_ba', '🧥', 'Áo bà ba lụa nâu', ('ba',), 'áo của bà', 'Áo bà ba của bà cất nhầm sang tủ khác, bà tìm cả sáng.', 1),
            S('so_mi', '👔', 'Sơ mi trắng', ('vc',), 'của anh Dũng', 'Sơ mi anh Dũng nằm trong tủ bà.', 1),
            S('vay_su', '👗', 'Váy kẻ ô', ('su',), 'đồng phục thứ hai của bé Su', 'Sáng thứ hai cả nhà lục tung tìm váy đồng phục.', 1),
            S('yem', '🧷', 'Yếm ăn, khăn sữa', ('com',), 'của bé Cốm', 'Khăn sữa của bé cất lẫn khăn lau bếp.', 1, 'sf'),
            S('khan_tam', '🧻', 'Khăn tắm', ('khan',), 'màu kem', 'Khăn tắm nhét vào tủ quần áo, ẩm cả tủ.', 1),
        ], lead='Gấp gọn rồi cất đúng tủ.'),
        choose('lot', 'Đồ lót của anh chị', 'Còn mấy bộ đồ lót của anh chị trong rổ. Tủ anh chị có ngăn kéo riêng.', [
            C('ngan', 'Gấp gọn, cất đúng ngăn kéo, không bình luận gì', 'good', 'Gọn gàng, kín đáo.'),
            C('de', 'Để nguyên trong rổ trên giường anh chị', 'ok', 'Chị Thảo tự cất.', 0),
            C('dua', 'Giơ lên trêu: “Anh Dũng mặc hình hoạt hình cơ à?”', 'bad', 'Anh Dũng đỏ mặt, chị Thảo không vui.', 2, 'Đem đồ riêng của chủ nhà ra trêu.', 'mn')]),
    ], note='Gấp, cất: mỗi người một tủ, đồ bé riêng, đồ riêng tư kín đáo.', min_day=2),
]

CLEAN = [
    V('k_khach', 'clean', 0, 'Dọn phòng khách', '“Chiều nay có khách, em dọn phòng khách giúp chị. Sàn gỗ nhé, đừng để ướt.”', [
        order('thu_tu', 'Thứ tự dọn', '🧹 Dọn', [
            O('mo', '🪟', 'Mở cửa sổ cho thoáng'), O('tran', '🪶', 'Phủi bụi quạt trần, nóc tủ'), O('ban', '🧽', 'Lau bàn ghế, kệ ti vi'),
            O('quet', '🧹', 'Quét nhà'), O('lau', '🫧', 'Lau nhà'),
        ], [('tran', 'ban', 1, 'Lau bàn xong mới phủi quạt trần: bụi rơi đầy bàn lại.', 'cr'), ('ban', 'quet', 1, 'Quét xong rồi mới lau bàn, bụi rơi xuống sàn sạch.', 'cr'),
            ('quet', 'lau', 1, 'Lau nhà khi chưa quét: tóc, bụi bết thành vệt.', 'cr'), ('tran', 'lau', 1, 'Lau nhà rồi mới phủi trần.', 'cr')],
            lead='Trên cao xuống thấp, khô trước ướt sau.'),
        sort('chat_tay', 'Lau chỗ nào bằng gì', '🧴 Xong', (
            ('go', '🪵', 'Khăn vắt kiệt, nước lau sàn gỗ'), ('kinh', '🪟', 'Nước lau kính, khăn mềm'), ('xa_phong', '🧼', 'Nước ấm pha xà phòng nhẹ'),
            ('giam', '🍋', 'Giấm, chanh cho sáng'), ('javel', '🧪', 'Nước tẩy javel')), [
            S('san', '🪵', 'Sàn gỗ phòng khách', ('go',), 'gỗ tự nhiên', 'Lau sàn gỗ đẫm nước: gỗ phồng mép ván.', 2,
              wrong={'javel': (2, 'Javel lên sàn gỗ: bạc màu từng mảng.', 'cr', False)}),
            S('ban_da', '🪨', 'Mặt bàn đá marble', ('xa_phong',), 'đá trắng vân xám', 'Lau đá marble sai cách, mặt đá mờ.', 1,
              wrong={'giam': (2, 'Giấm, chanh ăn mòn đá marble: mặt bàn mờ loang lổ.', 'cr', False)}),
            S('cua_kinh', '🪟', 'Cửa kính ban công', ('kinh',), 'nhiều vết tay', 'Kính lau xong còn vệt loang.', 1),
            S('sofa', '🛋️', 'Sofa da', ('xa_phong',), 'da thật', 'Lau sofa da bằng hóa chất, da khô nứt.', 2),
        ], lead='Mỗi bề mặt một cách lau.'),
        choose('giay', 'Bàn làm việc của anh Dũng', 'Góc phòng là bàn làm việc của anh Dũng: bản vẽ, hợp đồng, giấy tờ để bừa bộn, có tờ ghi “mật”.', [
            C('quanh', 'Lau quanh, không xếp lại, không đọc', 'good', 'Anh Dũng về, giấy tờ nguyên chỗ cũ: “Ổn, cảm ơn em.”'),
            C('xep', 'Xếp gọn lại thành chồng cho đẹp', 'ok', 'Anh Dũng tìm tờ hợp đồng mất nửa tiếng.', 1, 'Tự ý xếp lại giấy tờ trên bàn làm việc.', 'mn'),
            C('doc', 'Tò mò đọc thử tờ ghi “mật”', 'bad', 'Bà Tư bên cửa sổ thấy, đi kể khắp ngõ “con ở nhà Thảo đọc trộm giấy tờ”.', 2, 'Đọc trộm giấy tờ của chủ nhà.', 'hn')]),
    ], note='Phòng khách: trên xuống dưới, khô trước ướt sau, sàn gỗ vắt kiệt khăn, không động vào giấy tờ.'),
    V('k_tam', 'clean', 0, 'Cọ nhà tắm', 'Nhà tắm có vết ố vàng trên sàn, bồn cầu, lavabo. Chị Thảo: “Cọ cho sạch giúp chị, cuối tuần mẹ chị lên.”', [
        order('thu_tu', 'Cọ từ sạch tới bẩn', '🧽 Cọ', [
            O('guong', '🪞', 'Lau gương'), O('lavabo', '🚰', 'Cọ lavabo, vòi nước'), O('sen', '🚿', 'Cọ tường, vòi sen'),
            O('san', '🧱', 'Cọ sàn'), O('bon_cau', '🚽', 'Cọ bồn cầu (khăn, bàn chải riêng)'),
        ], [('guong', 'bon_cau', 1, 'Dùng khăn bồn cầu xong lau sang gương.', 'sf'), ('lavabo', 'bon_cau', 1, 'Cọ bồn cầu trước rồi cọ lavabo bằng tay bẩn.', 'sf'),
            ('sen', 'san', 1, 'Cọ sàn trước, nước bẩn trên tường chảy xuống bẩn lại.', 'cr')], lead='Chỗ sạch trước, bồn cầu sau cùng.'),
        choose('tron', 'Vết ố cứng đầu', 'Vết ố vàng dưới đáy bồn cầu không ra. Có chai tẩy bồn cầu (axit) đang xịt dở và chai nước javel.', [
            C('mot', 'Chỉ dùng một loại, ngâm mười lăm phút, mở cửa thông gió, đeo găng tay', 'good', 'Vết ố mờ hẳn. Nhà tắm thơm mùi sạch.'),
            C('tron', 'Đổ thêm javel lên chỗ vừa xịt tẩy cho mạnh', 'bad', 'Khí cay xộc lên mũi, ho sặc sụa, phải chạy ra ngoài.', 3,
              'Trộn javel với chất tẩy axit sinh khí độc, suýt ngất trong nhà tắm.', 'sf', True),
            C('ke', 'Cọ thêm ít rồi thôi', 'ok', 'Vết ố còn mờ mờ.', 1, 'Vết ố bồn cầu vẫn còn.')]),
        pick('xong', 'Cọ xong', '✅ Xong', [
            I('mo', '🌬️', 'Mở cửa, bật quạt thông gió', 'mùi hóa chất', True, 'Hóa chất đọng lại, cả nhà tắm sau còn cay mắt.', 1, 'sf'),
            I('cat', '🧴', 'Cất chai tẩy lên kệ cao, xa tầm tay bé Cốm', 'bé hay bò vào', True, 'Chai tẩy để dưới sàn, bé Cốm bò vào cầm chơi.', 3, 'sf', True),
            I('kho', '🧽', 'Lau khô sàn', 'bà hay đi', True, 'Sàn nhà tắm ướt, bà Lành trượt chân.', 2, 'sf'),
            I('gang', '🧤', 'Giặt găng tay, phơi khô', 'găng cao su', None, say='Găng tay phơi khô trên móc.'),
        ], lead='Chọn những việc sẽ làm.', done='Nhà tắm khô, sạch, an toàn.'),
    ], note='Nhà tắm: sạch trước bẩn sau, không bao giờ trộn hai chất tẩy, cất hóa chất xa tầm tay trẻ.', min_day=2),
    V('k_bep', 'clean', 1, 'Lau bếp dầu mỡ', 'Máy hút mùi, tường bếp, mặt bếp bám một lớp dầu mỡ vàng. Bà Lành: “Lau cho sạch, bếp là mặt mũi người đàn bà.”', [
        sort('chat_tay', 'Lau chỗ nào bằng gì', '🧴 Xong', (
            ('soda', '🫧', 'Nước ấm, baking soda, nước rửa chén'), ('kinh', '🪟', 'Nước lau kính'), ('sat', '🪨', 'Búi sắt cọ mạnh'),
            ('kho', '🧽', 'Khăn khô, tắt điện trước')), [
            S('hut_mui', '💨', 'Lưới lọc máy hút mùi', ('soda',), 'đặc dầu mỡ', 'Lưới lọc chỉ lau qua, còn nguyên mỡ.', 1),
            S('mat_bep', '🔥', 'Mặt bếp từ bằng kính', ('kinh', 'soda'), 'mặt kính đen bóng', 'Mặt bếp kính lau sai cách còn vệt.', 1,
              wrong={'sat': (2, 'Búi sắt cọ mặt bếp kính: xước chằng chịt.', 'cr', False)}),
            S('o_cam', '🔌', 'Ổ cắm, công tắc trên tường bếp', ('kho',), 'bám dầu', 'Lau ổ điện bằng khăn ướt: tách một cái, nhảy aptomat.', 2,
              wrong={'soda': (3, 'Khăn ướt sũng lau ổ điện đang có điện: giật tê tay.', 'sf', True)}),
            S('tuong', '🧱', 'Tường gạch men sau bếp', ('soda',), 'vệt mỡ vàng', 'Tường gạch còn vệt mỡ.', 1),
        ], lead='Mỗi chỗ một cách lau.'),
        choose('phong_bi', 'Ngăn kéo hé mở', 'Kéo ngăn tủ bếp lấy khăn, bạn thấy một phong bì dày tiền, ghi “tiền học bé Su”.', [
            C('dong', 'Đóng ngăn kéo lại, nhắn chị Thảo cất chỗ kín hơn', 'good', 'Chị Thảo nhắn lại: “Cảm ơn em, chị cất nhầm chỗ.”'),
            C('ke', 'Đóng lại, coi như không thấy', 'ok', 'Không ai biết gì.', 0),
            C('dem', 'Mở ra đếm thử xem bao nhiêu', 'bad', 'Camera phòng bếp quay lại cảnh đó. Chị Thảo hỏi, bạn ấp úng.', 2, 'Tự mở phong bì tiền của chủ nhà ra đếm.', 'hn')]),
    ], note='Bếp: dầu mỡ bằng nước ấm và baking soda, ổ điện lau khô khi tắt điện, không đụng đồ riêng.', min_day=2),
]

ELDER = [
    V('e_thuoc', 'elder', 1, 'Thuốc buổi sáng của bà', 'Đến giờ thuốc sáng của bà. Hộp thuốc chia ngày của bà Lành để trên bàn nước, cạnh vỉ thuốc của anh Dũng.', [
        choose('an', 'Bà chưa ăn sáng', 'Bà Lành: “Bà chưa đói. Đưa thuốc đây bà uống luôn cho xong.”', [
            C('chao', 'Mời bà ăn bát cháo nhỏ trước, rồi uống thuốc', 'good', 'Bà càu nhàu nhưng ăn hết bát cháo.'),
            C('sua', 'Pha cốc sữa không đường cho bà uống kèm', 'ok', 'Bà uống được nửa cốc.', 0),
            C('luon', 'Đưa thuốc cho bà uống luôn', 'bad', 'Mười giờ bà vã mồ hôi, run tay.', 2, 'Uống thuốc tiểu đường lúc bụng đói, bà bị tụt đường huyết.', 'sf')]),
        pick('hop', 'Lấy thuốc sáng', '💊 Đưa bà', [
            I('tron', '⚪', 'Viên trắng tròn', 'ngăn “Sáng”', True, 'Quên viên huyết áp buổi sáng.', 2, 'sf'),
            I('dai', '💊', 'Viên trắng dài', 'ngăn “Sáng”', True, 'Quên viên tiểu đường buổi sáng.', 2, 'sf'),
            I('hong', '🩷', 'Viên hồng nhỏ', 'ngăn “Tối”', False, 'Đưa bà viên thuốc ngủ buổi sáng: bà ngủ li bì cả ngày.', 3, 'sf', True),
            I('vi_dung', '🟦', 'Vỉ thuốc dạ dày của anh Dũng', 'để cạnh hộp của bà', False, 'Đưa bà uống thuốc của người khác.', 3, 'sf', True),
            I('nuoc', '🥛', 'Cốc nước ấm', 'để bà uống thuốc', True, 'Đưa thuốc mà không có cốc nước.', 1),
        ], lead='Sổ tay nhà ghi thuốc của bà. Chọn đúng thứ cần đưa.', done='Đúng thuốc, đúng giờ.'),
        _talk_back('che', 'Bà đòi ăn chè', 'Uống thuốc xong, bà Lành: “Ra đầu ngõ mua bát chè đậu đen cho bà. Ít đường thôi.”',
                   ('Gọt cho bà mấy miếng ổi, hẹn chủ nhật nấu chè không đường', 'Bà lẩm bẩm “khó thế” nhưng ăn ngon lành.'),
                   ('Mua bát nhỏ, xin quán thật ít đường', 'Bà ăn hết.', 'Chè ngoài quán vẫn ngọt.'),
                   ('Mua bát chè to, đừng nói chị Thảo', 'Bà ăn xong khen ngon.', 'Chiều đo đường huyết bà vọt lên, chị Thảo hỏi ra chuyện.'),
                   ('“Tiểu đường mà còn đòi chè, bà ơi”', 'Bà dỗi, cả sáng không nói câu nào.', 'Nói với bà như mắng trẻ con.')),
    ], note='Thuốc của bà: ăn trước rồi uống; viên trắng tròn và viên trắng dài buổi sáng; viên hồng chỉ buổi tối.'),
    V('e_choang', 'elder', 1, 'Bà chóng mặt', 'Bà Lành ngồi xem ti vi bỗng ôm đầu: “Bà chóng mặt quá.”', [
        pick('do', 'Đo huyết áp, nhìn bà', '🩺 Xem kết quả', [
            I('ngoi', '🪑', 'Cho bà ngồi nghỉ năm phút rồi đo', 'máy đo bắp tay', True, 'Bà vừa đi lại đã đo, số đo không đúng.', 1),
            I('may', '🩺', 'Quấn bao đo ngang tim, đo huyết áp', 'máy điện tử', True, 'Không đo huyết áp, chẳng biết bà làm sao.', 1),
            I('mieng', '🙂', 'Nhờ bà cười, giơ hai tay, nói một câu', 'xem méo miệng, yếu tay, nói ngọng', True,
              'Không xem bà có méo miệng, yếu tay không.', 2, 'sf', say='Bà cười, miệng hơi lệch về một bên; tay trái giơ không lên, nói hơi ngọng.'),
        ], lead='Chọn những việc sẽ làm.', done='Máy báo 175/100.'),
        choose('xu_ly', 'Xử lý', 'Máy đo: 175/100. Bà nói hơi ngọng, miệng lệch, tay trái yếu. Bà bảo “nghỉ tí là khỏi”.', [
            C('cuu', 'Gọi 115 ngay, cho bà nằm nghiêng, không cho ăn uống gì, báo chị Thảo', 'good',
              'Xe cấp cứu tới sau mười hai phút. Bác sĩ bảo đưa đi sớm nên bà qua được.'),
            C('hoi', 'Gọi chị Thảo hỏi ý trước đã', 'bad', 'Chị Thảo bảo gọi 115 ngay. Mất mười lăm phút quý.', 2, 'Dấu hiệu đột quỵ mà còn chờ hỏi ý, chậm mười lăm phút.', 'sf'),
            C('thuoc', 'Cho bà uống thêm một viên huyết áp', 'bad', 'Huyết áp tụt, bà lả đi.', 3, 'Tự ý cho bà uống thêm thuốc lúc có dấu hiệu đột quỵ.', 'sf', True),
            C('gio', 'Xoa dầu, cạo gió cho bà', 'bad', 'Nửa tiếng sau bà không nói được nữa.', 3, 'Cạo gió cho người có dấu hiệu đột quỵ, lỡ mất giờ vàng.', 'sf', True)]),
        choose('sau', 'Ở bệnh viện', 'Bà qua cơn nguy. Chị Thảo ở viện cả đêm, nhờ bạn: “Em về trông hai đứa nhỏ giúp chị.”', [
            C('ve', 'Về trông các bé, nấu cháo mang vào viện sáng mai', 'good', 'Chị Thảo rơm rớm: “May mà có em.”'),
            C('ve_thoi', 'Về trông các bé, sáng mai chị tự lo', 'ok', 'Các bé ngủ ngon.', 0),
            C('gio', 'Hết giờ làm rồi, xin phép về', 'bad', 'Chị Thảo phải gửi hai bé sang bà Tư.', 1, 'Chị cần người nhất thì xin về.', 'mn')]),
    ], note='Méo miệng, yếu tay, nói ngọng: đột quỵ. Gọi 115 ngay, không cạo gió, không tự cho thuốc.', mods=('sick',), min_day=3, weight=2),
    V('e_tam', 'elder', 1, 'Dìu bà đi tắm', 'Bà Lành mấy hôm mệt chưa tắm. Chị Thảo dặn: “Em giúp bà tắm nhé, nhà tắm trơn lắm.”', [
        order('chuan_bi', 'Chuẩn bị rồi mới dìu bà', '🛁 Tắm cho bà', [
            O('tham', '🧶', 'Trải thảm chống trơn'), O('nuoc', '♨️', 'Pha nước ấm, thử bằng cổ tay'), O('ghe', '🪑', 'Đặt ghế nhựa trong nhà tắm'),
            O('khan', '🧻', 'Để sẵn khăn, quần áo trong tầm tay'), O('diu', '🚶', 'Dìu bà vào'), O('lau', '🧣', 'Lau khô, mặc ấm ngay'),
            O('khoa', '🔒', 'Để bà tự tắm, khóa cửa trong cho kín', (2, 'Để bà tắm một mình khóa trái cửa: bà trượt chân, không ai vào được.', 'sf', False)),
        ], [('tham', 'diu', 2, 'Dìu bà vào lúc chưa có thảm chống trơn.', 'sf'), ('nuoc', 'diu', 1, 'Bà vào rồi mới pha nước, bà ngồi run cầm cập.', 'sf'),
            ('ghe', 'diu', 1, 'Bà phải đứng tắm vì chưa có ghế.', 'sf'), ('khan', 'lau', 1, 'Tắm xong mới chạy đi tìm khăn, bà lạnh run.', 'sf'),
            ('diu', 'lau', 1, 'Lau khô trước khi tắm?', 'cr')], lead='Mọi thứ sẵn sàng rồi mới dìu bà vào.'),
        _talk_back('ngai', 'Bà ngại', 'Bà Lành đỏ mặt: “Thôi, để bà tự tắm. Cháu ra ngoài, đóng cửa vào.”',
                   ('Quay lưng, đứng ngay cửa khép hờ, bà cần gì gọi là có', 'Bà tự tắm, thỉnh thoảng gọi nhờ kỳ lưng.'),
                   ('Ra ngoài, năm phút gõ cửa hỏi một lần', 'Bà tắm xong an toàn.', 'Đứng xa, có chuyện khó nghe thấy.'),
                   ('Ra ngoài, để bà tự lo', 'Bà tắm xong, ra tới cửa suýt ngã.', 'Để người già yếu tắm một mình trong nhà tắm trơn.'),
                   ('“Bà yếu thế tắm sao được, để cháu làm”', 'Bà cáu, đuổi ra.', 'Nói như bà là người vô dụng.')),
    ], note='Tắm cho người già: thảm chống trơn, nước ấm thử cổ tay, ghế ngồi, khăn sẵn, không để bà một mình khóa cửa.', min_day=2),
    V('e_buon', 'elder', 1, 'Bà buồn', 'Bà Lành ngồi bên cửa sổ, tay cầm ảnh ông: “Cả nhà đi hết, chẳng ai nói chuyện với bà.”', [
        choose('nghe', 'Bà muốn có người nói chuyện', 'Việc nhà còn một đống: giặt, lau, nấu.', [
            C('ngoi', 'Ngồi xuống nghe bà kể chuyện ông mười lăm phút', 'good', 'Bà kể chuyện ông đi bộ đội, mắt sáng lên. Cuối buổi bà cười.'),
            C('tv', 'Bật ti vi kênh cải lương cho bà', 'ok', 'Bà xem một lúc rồi ngủ gật.', 0),
            C('ban', '“Để cháu làm cho xong việc đã bà ạ”', 'bad', 'Bà quay mặt đi.', 1, 'Bà muốn nói chuyện thì bảo bận.', 'mn')]),
        pick('cung', 'Rủ bà làm cùng', '🤝 Làm cùng bà', [
            I('nhat', '🥬', 'Nhờ bà nhặt rau giúp', 'bà ngồi được', None, say='Bà nhặt rau, chỉ cách nhặt rau muống cho khỏi dai.'),
            I('cay', '🪴', 'Rủ bà ra ban công tưới cây', 'nắng nhẹ', None, say='Bà tưới cây, kể chuyện giàn mướp ngày xưa.'),
            I('dien_thoai', '📱', 'Gọi video cho cháu ở xa của bà', 'bà nhớ cháu', None, say='Bà nói chuyện với cháu ở Sài Gòn, cười tít mắt.'),
            I('bo', '🚶', 'Để bà một mình cho bà nghỉ', 'cho yên tĩnh', False, 'Bà lại ngồi một mình cả buổi.', 1, 'mn'),
        ], lead='Chọn việc rủ bà làm cùng.', done='Một buổi sáng bà không thấy cô đơn.'),
    ], note='Người già cần người nghe: dành chút thời gian, rủ bà làm cùng.', min_day=3),
]

KIDS = [
    V('t_don', 'kids', 3, 'Đón bé Su', 'Bốn giờ chiều. Chị Thảo nhắn: “Em đón Su giúp chị, chị họp muộn. Nhớ đội mũ bảo hiểm cho bé.”', [
        choose('la', 'Ở cổng trường', 'Tới cổng trường thấy một chú lạ đang cầm tay bé Su: “Chú là bạn của bố, bố nhờ chú đón cháu.” Bé Su không biết chú.', [
            C('giu', 'Giữ bé lại bên mình, gọi chị Thảo xác nhận trước', 'good', 'Chị Thảo bảo không nhờ ai cả. Chú kia lủi mất. Bảo vệ trường ghi lại.'),
            C('hoi', 'Hỏi tên chú, rồi để chú đón', 'bad', 'May mà cô giáo chặn lại.', 3, 'Giao bé Su cho người lạ chỉ vì nghe kể là bạn của bố.', 'sf', True),
            C('mang', 'Quát chú kia một trận, kéo bé về', 'ok', 'Chú kia đi mất, không ai kịp báo bảo vệ.', 1, 'To tiếng mà không báo bảo vệ, không báo chị Thảo.', 'cr')]),
        _talk_back('an_vat', 'Bé đòi ăn vặt', 'Bé Su kéo áo: “Mua xúc xích chiên với trà sữa cho em đi! Bạn nào cũng ăn!”',
                   ('Hẹn bé về nhà ăn hoa quả, khen bé hôm nay ngoan', 'Bé phụng phịu rồi cũng gật, về nhà ăn hết đĩa xoài.'),
                   ('Mua cho bé một hộp sữa chua ở tiệm có nhãn mác', 'Bé vui.', 'Chị Thảo dặn không mua đồ ăn vặt trước bữa tối.'),
                   ('Mua xúc xích chiên vỉa hè cho bé im', 'Bé ăn ngon lành.', 'Đồ chiên vỉa hè dầu đen, tối bé đau bụng.'),
                   ('“Không là không, đòi nữa về mách mẹ”', 'Bé khóc ầm cổng trường.', 'Dọa mách mẹ giữa cổng trường.', 'cr')),
        pick('ve', 'Đưa bé về', '🏠 Về nhà', [
            I('mu', '⛑️', 'Đội mũ bảo hiểm cho bé, cài quai', 'mũ của bé', True, 'Chở bé mà không cài quai mũ.', 2, 'sf'),
            I('ngoi', '🛵', 'Cho bé ngồi sau, ôm eo', 'xe máy', True, 'Bé ngồi không đúng chỗ.', 1, 'sf'),
            I('dung', '🧍', 'Cho bé đứng phía trước cho bé thích', 'bé năn nỉ', False, 'Cho bé đứng trước đầu xe: phanh gấp là bé lao ra.', 3, 'sf', True),
            I('cap', '🎒', 'Đeo cặp của bé phía trước mình', 'cặp nặng', None, say='Bạn đeo cặp phía trước, bé ôm eo ngồi sau.'),
        ], lead='Chọn những việc sẽ làm.', done='Hai cô cháu về tới nhà an toàn.'),
    ], note='Đón bé: chỉ giao bé cho bố, mẹ, bà; người lạ thì gọi chị Thảo; mũ bảo hiểm cài quai.'),
    V('t_com', 'kids', 0, 'Trông bé Cốm ngủ trưa', '“Chị đi làm, em trông Cốm nhé. Mười hai giờ bé ngủ, dậy pha sữa cho bé.”', [
        pick('an_toan', 'Góc chơi an toàn', '🧸 Cho bé chơi', [
            I('o', '🔌', 'Che các ổ điện thấp', 'bé hay chọc tay', True, 'Ổ điện để hở, bé Cốm cầm chìa khóa chọc vào.', 3, 'sf', True),
            I('keo', '✂️', 'Cất kéo, dao, thuốc lên cao', 'bàn nước thấp', True, 'Kéo, vỉ thuốc để trên bàn thấp, bé với lấy.', 2, 'sf'),
            I('xo', '🪣', 'Đậy nắp xô nước nhà tắm, đóng cửa nhà tắm', 'xô đầy nước', True, 'Xô nước để mở: trẻ nhỏ có thể úp mặt vào xô nước.', 3, 'sf', True),
            I('ban_cong', '🚪', 'Khóa cửa ban công', 'ban công tầng ba', True, 'Cửa ban công tầng ba mở toang.', 3, 'sf', True),
            I('dt', '📱', 'Mở hoạt hình trên điện thoại cho bé ngồi im cả buổi', 'cho đỡ mệt', False, 'Bé xem điện thoại cả buổi, tối khóc đòi điện thoại.', 1, 'cr'),
        ], lead='Bé mười tám tháng, bò khắp nhà. Chọn những việc sẽ làm.', done='Nhà an toàn cho bé bò.'),
        order('sua', 'Pha sữa cho bé', '🍼 Cho bé bú', [
            O('tay', '🧼', 'Rửa tay'), O('dun', '♨️', 'Đun sôi nước, để nguội tới 40–70 °C'), O('nuoc', '💧', 'Rót nước vào bình trước, đúng 90 ml'),
            O('bot', '🥄', 'Thêm 3 muỗng sữa gạt ngang'), O('lac', '🔄', 'Lắc đều'), O('thu', '🤲', 'Nhỏ thử lên cổ tay'),
            O('them', '➕', 'Thêm một muỗng cho bé no lâu', (2, 'Thêm muỗng sữa, sữa đặc quá: bé táo bón, nôn trớ.', 'sf', False)),
        ], [('tay', 'bot', 1, 'Không rửa tay mà xúc sữa cho bé.', 'sf'), ('dun', 'nuoc', 1, 'Rót nước chưa đun vào bình.', 'sf'),
            ('nuoc', 'bot', 1, 'Cho sữa trước rồi mới rót nước: sai tỷ lệ.', 'cr'), ('lac', 'thu', 1, 'Thử nhiệt rồi mới lắc, sữa chỗ nóng chỗ nguội.', 'cr'),
            ('bot', 'lac', 1, 'Lắc nước không rồi mới cho sữa?', 'cr')], lead='Sổ tay nhà: 1 muỗng gạt cho 30 ml nước.'),
        _talk_back('khoc', 'Bé khóc không chịu ngủ', 'Mười hai giờ, bé Cốm khóc ré, chỉ tay vào điện thoại của bạn.',
                   ('Bế bé ra chỗ tối, vỗ lưng, ầu ơ', 'Mười phút sau bé ngủ say.'),
                   ('Để bé nằm cũi, ngồi cạnh hát cho bé nghe', 'Bé khóc thêm một lúc rồi ngủ.', 'Bé khóc lâu, hàng xóm sang hỏi.', 'cr'),
                   ('Mở hoạt hình cho bé xem tới khi ngủ', 'Bé xem tới hai giờ mới ngủ.', 'Bé xem điện thoại hai tiếng, lỡ giấc trưa.', 'cr'),
                   ('Mặc bé khóc, đóng cửa ra ngoài', 'Bé khóc tím tái.', 'Để bé khóc một mình trong phòng.', 'sf')),
    ], note='Trông bé: che ổ điện, cất đồ nguy hiểm, đậy xô nước; sữa: nước trước, bột sau, đúng tỷ lệ.', min_day=2),
    V('t_hoc', 'kids', 3, 'Kèm bé Su học bài', 'Bảy giờ tối. Bé Su mếu máo với bài toán đố: “Khó quá, chị làm hộ em đi!”', [
        _talk_back('lam_ho', 'Bài toán khó', 'Bài: “Mẹ có 15 quả cam, cho bà 4 quả, cho bé 3 quả. Mẹ còn mấy quả?” Bé Su khóc: “Chị làm hộ em đi!”',
                   ('Lấy cam thật ra đếm cùng bé, để bé tự viết phép tính', 'Bé Su reo lên: “Mười tám… à không, tám quả!” Rồi tự làm bài sau.'),
                   ('Gợi ý phép tính đầu, bé tự làm phần còn lại', 'Bé làm được.', 'Bé chưa tự nghĩ ra cách làm.', 'cr'),
                   ('Làm hộ cho nhanh còn đi rửa bát', 'Bài đúng hết.', 'Mai cô giáo gọi bé lên bảng, bé đứng im.', 'cr'),
                   ('“Dễ thế mà không biết à”', 'Bé Su úp mặt xuống bàn khóc.', 'Chê bé ngu trước mặt bà.', 'mn')),
        choose('co', 'Tin nhắn cô giáo', 'Cô giáo nhắn vào nhóm lớp, chị Thảo đọc to: “Hôm nay Su xô bạn ngã.” Bé Su kéo tay bạn: “Tại bạn ấy giật tóc em trước.” Chị Thảo hỏi bạn có biết không.', [
            C('ke', 'Kể thật: lúc đón, bé Su có kể chuyện bị giật tóc, quên chưa báo chị', 'good', 'Chị Thảo nhắn cô giáo hỏi rõ hai bên. Bé Su được xin lỗi lại.'),
            C('bao', 'Bênh bé Su chằm chằm: “Bé ngoan lắm, chắc bạn kia hư”', 'ok', 'Chị Thảo nhìn bạn ngờ vực.', 1, 'Bênh bé mà không nói rõ chuyện.', 'hn'),
            C('khong', 'Bảo không biết gì cho khỏi liên lụy', 'bad', 'Hôm sau bé Su kể ra là đã kể với chị giúp việc.', 1, 'Biết chuyện mà bảo không biết.', 'hn')]),
    ], note='Kèm học: để bé tự làm, gợi ý từng bước; chuyện ở trường kể thật với bố mẹ bé.', min_day=3),
    V('t_nga', 'kids', 3, 'Bé Su ngã', 'Bé Su chạy trong sân, vấp bậc thềm, đầu gối trầy rướm máu, khóc ầm lên.', [
        order('so_cuu', 'Sơ cứu vết trầy', '🩹 Băng xong', [
            O('do', '🤗', 'Bế bé ngồi, dỗ bé bình tĩnh'), O('tay', '🧼', 'Rửa tay'), O('rua', '💧', 'Rửa vết trầy dưới vòi nước sạch'),
            O('sat', '🧴', 'Chấm dung dịch sát khuẩn'), O('bang', '🩹', 'Dán băng gạc'),
            O('kem', '🪥', 'Bôi kem đánh răng lên vết thương', (2, 'Bôi kem đánh răng lên vết trầy: rát, dễ nhiễm trùng.', 'sf', False)),
        ], [('tay', 'rua', 1, 'Tay bẩn rửa vết thương cho bé.', 'sf'), ('rua', 'sat', 1, 'Sát khuẩn khi vết thương còn đầy đất cát.', 'sf'),
            ('sat', 'bang', 1, 'Băng lại rồi mới sát khuẩn?', 'cr')], lead='Sơ cứu một vết trầy nhẹ.'),
        choose('bao', 'Báo bố mẹ bé', 'Vết trầy nhẹ, bé đã nín. Chị Thảo đang họp.', [
            C('nhan', 'Nhắn chị Thảo kể rõ, gửi ảnh vết thương đã băng', 'good', 'Chị Thảo nhắn: “Cảm ơn em, chị yên tâm rồi.”'),
            C('toi', 'Tối chị về kể cũng được', 'ok', 'Chị Thảo về thấy băng mới biết.', 1, 'Bé ngã mà không báo, chị Thảo tự phát hiện.', 'hn'),
            C('giau', 'Mặc quần dài cho bé che đi, khỏi bị mắng', 'bad', 'Tối bé Su kể ra. Chị Thảo rất phật lòng.', 2, 'Giấu chuyện bé bị ngã.', 'hn')]),
    ], note='Sơ cứu vết trầy: rửa tay, rửa nước sạch, sát khuẩn, băng; báo bố mẹ bé ngay.', min_day=2),
]

FRIDGE = [
    V('f_cat', 'fridge', 0, 'Cất đồ vào tủ lạnh', 'Túi đồ chợ, đồ ăn thừa bữa trưa, hộp sữa chua… chất trên bàn bếp. Chị Thảo: “Xếp tủ lạnh cho gọn, chị mở ra là tìm thấy ngay nhé.”', [
        sort('xep', 'Xếp vào đâu', '🧊 Đóng tủ', (
            ('dong', '❄️', 'Ngăn đông'), ('duoi', '🥩', 'Ngăn mát dưới cùng, hộp kín'), ('tren', '🍱', 'Ngăn mát trên, hộp đậy'),
            ('rau', '🥬', 'Ngăn rau'), ('canh', '🚪', 'Cánh tủ'), ('bo', '🗑️', 'Bỏ đi')), [
            S('thit', '🥩', 'Thịt ba chỉ ăn tuần sau', ('dong',), 'đã chia túi nhỏ', 'Thịt ăn tuần sau để ngăn mát, ba hôm đã có mùi.', 1, 'sf',
              wrong={'tren': (2, 'Thịt sống để ngăn trên: nước thịt nhỏ xuống đồ chín.', 'sf', False)}),
            S('ca', '🐟', 'Cá nấu tối nay', ('duoi',), 'đã làm sạch', 'Cá nấu tối nay lại cho ngăn đá, tối phải rã đông vội.', 1,
              wrong={'tren': (2, 'Cá sống để ngăn trên, nước tanh nhỏ xuống hộp đồ chín.', 'sf', False)}),
            S('thua', '🍱', 'Thức ăn thừa bữa trưa', ('tren',), 'đã nguội', 'Đồ ăn chín để lẫn với đồ sống.', 1, 'sf'),
            S('rau', '🥬', 'Rau cải, hành lá', ('rau',), 'rau mới mua', 'Rau để chỗ khác, mai đã héo.', 1),
            S('tuong', '🌶️', 'Lọ tương ớt đã mở', ('canh', 'tren'), 'lọ nhỏ', 'Lọ tương ớt để chỗ khác.', 1),
            S('sua_chua', '🥛', 'Hộp sữa chua hết hạn từ 5 hôm trước', ('bo',), 'phồng nắp', 'Sữa chua quá hạn phồng nắp vẫn cất, bé Su ăn phải đau bụng.', 2, 'sf'),
        ], lead='Đồ sống dưới, đồ chín trên, đồ hỏng bỏ đi.'),
        choose('noi', 'Nồi canh còn nóng', 'Nồi canh bí còn bốc khói, chị Thảo dặn cất để tối ăn.', [
            C('nguoi', 'Để nguội bớt, chia hộp nhỏ rồi cất trong vòng hai tiếng', 'good', 'Tối hâm lại canh vẫn ngon.'),
            C('ngay', 'Cho cả nồi nóng vào tủ ngay', 'ok', 'Tủ chạy ù ù, hộp sữa chua bên cạnh ấm lên.', 1, 'Nồi canh nóng cho thẳng vào tủ.'),
            C('ngoai', 'Để ngoài tới tối, đậy vung là được', 'bad', 'Tối canh có vị chua.', 2, 'Canh để ngoài cả buổi trưa nóng, thiu.', 'sf')]),
    ], note='Tủ lạnh: đồ sống ngăn dưới trong hộp kín, đồ chín ngăn trên, đồ quá hạn bỏ đi.'),
    V('f_don', 'fridge', 1, 'Dọn tủ lạnh cuối tuần', 'Tủ lạnh bốc mùi. Bà Lành: “Đồ của bà đừng có vứt đấy nhé.”', [
        pick('bo', 'Bỏ đi những gì', '🗑️ Dọn', [
            I('chao', '🍲', 'Bát cháo từ năm hôm trước', 'mốc lấm tấm', True, 'Bát cháo mốc vẫn để trong tủ.', 1, 'sf'),
            I('dua', '🥒', 'Hũ dưa muối của bà', 'chua thơm, còn ngon', False, 'Vứt hũ dưa muối còn ngon của bà.', 1, 'mn'),
            I('rau_ung', '🥬', 'Túi rau úng nước', 'nhũn, chảy nước', True, 'Túi rau úng vẫn nằm ngăn rau, lây sang rau khác.', 1),
            I('trung', '🥚', 'Hộp trứng mới mua hôm qua', 'còn nguyên', False, 'Vứt hộp trứng mới mua.', 1),
            I('mam', '🧂', 'Lọ mắm tôm của bà đã mở từ tháng trước', 'bà dặn giữ', None, say='Lọ mắm tôm bà dặn giữ, bạn bọc kín thêm lớp ni lông cho đỡ mùi.'),
        ], lead='Chọn những thứ bỏ đi.', done='Tủ lạnh thơm tho, đồ của bà còn nguyên.'),
        order('lau', 'Lau tủ', '🧽 Lau xong', [
            O('rut', '🔌', 'Rút phích điện'), O('lay', '📦', 'Lấy hết đồ ra'), O('lau', '🧽', 'Lau bằng nước ấm pha baking soda'),
            O('kho', '🧻', 'Lau khô'), O('cam', '🔌', 'Cắm điện, cất đồ lại'),
        ], [('rut', 'lau', 2, 'Lau tủ lạnh khi chưa rút điện, tay ướt chạm dây.', 'sf'), ('lay', 'lau', 1, 'Lau khi đồ còn nguyên trong tủ.', 'cr'),
            ('kho', 'cam', 1, 'Cắm điện khi tủ còn ướt nhẹp.', 'sf'), ('lau', 'kho', 1, 'Lau khô rồi mới lau ướt?', 'cr')]),
    ], note='Dọn tủ lạnh: rút điện trước, bỏ đồ hỏng, giữ đồ của bà.', min_day=2),
]

GARDEN = [
    V('g_tuoi', 'garden', 1, 'Tưới cây ban công', 'Bà Lành: “Tưới cây giúp bà. Mà cây nào cũng tưới đẫm là chết hết đấy.”', [
        sort('tuoi', 'Cây nào tưới thế nào', '🚿 Tưới', (
            ('dam', '🚿', 'Tưới đẫm gốc sáng sớm'), ('phun', '🌫️', 'Phun sương nhẹ lên lá, rễ'), ('khong', '🚫', 'Hôm nay không tưới')), [
            S('xuong_rong', '🌵', 'Chậu xương rồng', ('khong',), 'đất còn ẩm, tưới hôm kia', 'Xương rồng tưới đẫm, úng thối gốc.', 1),
            S('lan', '🪷', 'Giò lan hồ điệp', ('phun',), 'rễ trắng bạc, giá thể khô', 'Tưới đẫm giò lan, rễ úng.', 1),
            S('rau_thom', '🌿', 'Chậu rau thơm', ('dam',), 'đất khô nứt, lá rũ', 'Rau thơm khô rũ không được tưới.', 1),
            S('luoi_ho', '🪴', 'Cây lưỡi hổ', ('khong',), 'đất còn ẩm', 'Lưỡi hổ tưới nhiều, thối lá.', 1),
            S('hoa_giay', '🌺', 'Chậu hoa giấy', ('dam',), 'nắng cả ngày, đất khô', 'Hoa giấy khô rụng hết hoa.', 1),
        ], lead='Mỗi cây một kiểu. Xem đất trước khi tưới.'),
        _talk_back('ba_tu', 'Bà Tư bên cạnh', 'Bà Tư thò sang: “Ban công nhà này lắm cây, muỗi bay sang nhà tôi. Nhổ bớt đi! À, mà cắt cho tôi mấy cành hoa giấy về cắm.”',
                   ('Cười, nói để bà Lành quyết chuyện cây, hứa đổ nước đọng đĩa lót chậu cho khỏi muỗi', 'Bà Tư lầm bầm rồi về.'),
                   ('Cắt cho bà Tư hai cành nhỏ', 'Bà Tư cầm cành hoa về.', 'Tự ý cắt cây của bà Lành cho người khác.', 'mn'),
                   ('Nghe bà Tư, nhổ luôn chậu rau thơm', 'Bà Tư hài lòng.', 'Nhổ cây của bà Lành vì hàng xóm bảo.', 'cr'),
                   ('“Muỗi nhà bà chứ muỗi nhà cháu à”', 'Bà Tư đứng chửi đổng cả buổi.', 'Cãi nhau với hàng xóm của chủ nhà.')),
    ], note='Tưới cây: xem đất trước; xương rồng, lưỡi hổ ít nước; lan phun sương; tưới sáng sớm.'),
    V('g_vang', 'garden', 1, 'Chậu trầu bà vàng lá', 'Chậu trầu bà bà Lành quý nhất vàng lá, gốc có mùi hôi.', [
        pick('xem', 'Xem chậu cây', '🔍 Xem xong', [
            I('dat', '👆', 'Ấn tay xem đất', 'đất ướt nhão', True, 'Không xem đất đã đoán bệnh.', 1, say='Đất ướt nhão, sũng nước.'),
            I('lo', '🕳️', 'Nhấc chậu xem lỗ thoát nước', 'đáy chậu', True, 'Không xem lỗ thoát nước dưới đáy chậu.', 1, say='Lỗ thoát nước bị đất bít kín.'),
            I('dia', '🍽️', 'Xem đĩa lót chậu', 'đọng nước', None, say='Đĩa lót đầy nước đọng, có cả lăng quăng.'),
        ], lead='Chọn những gì sẽ xem.', done='Cây bị úng nước.'),
        choose('chua', 'Chữa cho cây', 'Đất úng, lỗ thoát nước bị bít, đĩa lót đọng nước.', [
            C('kho', 'Đổ nước đĩa lót, thông lỗ thoát nước, ngưng tưới, cắt lá vàng', 'good', 'Tuần sau cây ra lá non. Bà Lành vui ra mặt.'),
            C('them', 'Tưới thêm cho cây xanh lại', 'bad', 'Cây vàng thêm.', 1, 'Cây úng còn tưới thêm.'),
            C('phan', 'Bón thật nhiều phân', 'bad', 'Rễ cháy, cây rũ hẳn.', 1, 'Cây úng còn bón phân.')]),
    ], note='Cây vàng lá: xem đất, lỗ thoát nước trước khi tưới thêm.', min_day=3),
]

INCIDENT = [
    V('i_dien', 'incident', 0, 'Mất điện', 'Đang nấu dở thì mất điện cả khu. Nồi cơm điện tắt phụt, bé Cốm khóc thét trong bóng tối.', [
        choose('be', 'Bé Cốm sợ tối', 'Phòng tối om. Nhà có đèn sạc và mấy cây nến.', [
            C('den', 'Bật đèn sạc, bế bé, hát cho bé nín', 'good', 'Bé nín, ôm cổ bạn ngủ gà ngủ gật.'),
            C('nen', 'Thắp nến để trên bàn thấp cho sáng', 'bad', 'Bé với tay vào ngọn nến.', 2, 'Nến để bàn thấp cạnh em bé.', 'sf'),
            C('ke', 'Kệ bé khóc, lo nồi cơm trước', 'ok', 'Bé khóc khản tiếng.', 1, 'Để bé khóc trong bóng tối.', 'mn')]),
        choose('com', 'Nồi cơm dở', 'Nồi cơm điện tắt giữa chừng, gạo mới chín một nửa. Nhà có bếp ga.', [
            C('ga', 'Chuyển sang nồi trên bếp ga, lửa nhỏ, đậy kín', 'good', 'Cơm chín kịp bữa.'),
            C('cho', 'Chờ có điện rồi nấu tiếp', 'ok', 'Có điện thì đã quá trưa.', 1, 'Cả nhà chờ cơm tới một giờ chiều.'),
            C('ngoai', 'Gọi cơm hộp ngoài hàng bằng tiền chợ', 'bad', 'Chị Thảo nhìn hóa đơn, nhíu mày.', 1, 'Nhà có bếp ga mà gọi cơm hàng.', 'hn')]),
        choose('tu', 'Tủ lạnh', 'Điện lực báo bốn tiếng nữa mới có điện. Tủ lạnh đầy đồ.', [
            C('dong', 'Hạn chế mở tủ, ghi giờ mất điện, nấu trước đồ dễ hỏng', 'good', 'Có điện lại, đồ trong tủ vẫn lạnh.'),
            C('mo', 'Cứ chốc chốc mở xem đồ còn lạnh không', 'bad', 'Đá tan chảy nước lênh láng.', 1, 'Mở tủ lạnh liên tục lúc mất điện.'),
            C('nha_ben', 'Mang hết đồ sang gửi tủ nhà bà Tư', 'ok', 'Bà Tư đồng ý, rồi kể với cả ngõ.', 1, 'Mang hết đồ nhà chủ sang nhà hàng xóm khi chưa hỏi.', 'mn')]),
    ], note='Mất điện: đèn sạc chứ không nến cạnh bé, nấu bằng bếp ga, hạn chế mở tủ lạnh.', mods=('rain', None), weight=2, min_day=2),
    V('i_khe', 'incident', 1, 'Nồi cơm khê', 'Mải trông bé, nồi cơm trên bếp ga khê, mùi khét bay khắp nhà. Mười lăm phút nữa ăn trưa.', [
        choose('cuu', 'Cứu nồi cơm', 'Lớp dưới cháy đen, lớp trên còn trắng.', [
            C('xuc', 'Tắt bếp, xúc phần cơm trắng bên trên sang nồi khác, đặt khúc hành lá lên mặt cơm cho bớt mùi', 'good', 'Cơm hết mùi khê. Không ai biết.'),
            C('tron', 'Trộn đều cả nồi cho mất mùi', 'bad', 'Cả nồi cơm ám mùi khét, lổn nhổn cháy.', 2, 'Trộn cả cơm cháy vào, nồi cơm ám khét.'),
            C('moi', 'Nấu nồi mới, trễ hai mươi phút', 'ok', 'Cả nhà ăn trễ.', 1, 'Bữa trưa trễ hai mươi phút.')]),
        choose('hoi', 'Bà hỏi', 'Bà Lành khịt mũi: “Sao nhà có mùi khét thế?”', [
            C('that', 'Nói thật: cháu mải trông bé nên để khê, đã xử lý rồi', 'good', 'Bà gật: “Lần sau để lửa nhỏ, hẹn giờ.”'),
            C('nha_ben', 'Bảo mùi khét từ nhà bên', 'bad', 'Bà ra tận bếp, thấy nồi cháy.', 2, 'Nói dối về nồi cơm khê.', 'hn'),
            C('noi', 'Đổ tại nồi bị hỏng', 'bad', 'Chị Thảo mua nồi mới, nồi cũ vẫn tốt.', 2, 'Đổ cho nồi hỏng để chủ nhà mua nồi mới.', 'hn')]),
    ], note='Cơm khê: xúc phần trên, đặt hành lá; nói thật với chủ nhà.', min_day=2),
    V('i_tac', 'incident', 0, 'Bồn rửa bị tắc', 'Nước trong bồn rửa bát không rút, mùi hôi bốc lên.', [
        order('thong', 'Xử lý', '🪠 Thử xong', [
            O('ngung', '🚱', 'Ngừng xả nước'), O('vot', '🧤', 'Đeo găng, vớt rác ở lưới chắn'), O('pit', '🪠', 'Dùng pít-tông hút đẩy'),
            O('bot', '🧪', 'Đổ cả gói bột thông cống', (2, 'Đổ bột thông cống tay không: bột xút bắn vào tay bỏng rát, ống cũ còn dễ thủng.', 'sf', False)),
        ], [('ngung', 'pit', 1, 'Vừa xả nước vừa thông, nước tràn ra sàn.', 'cr'), ('vot', 'pit', 1, 'Chưa vớt rác lưới chắn đã thông.', 'cr')]),
        choose('van_tac', 'Vẫn tắc', 'Đã thử pít-tông, nước rút được tí rồi lại đứng.', [
            C('tho', 'Báo chị Thảo, xin gọi thợ thông cống chú Hai', 'good', 'Chú Hai tới, lôi ra cả cục mỡ đông: “Đừng đổ mỡ xuống bồn nhé!”'),
            C('thao', 'Tự tháo tung ống xi-phông khi chưa biết làm', 'bad', 'Nước bẩn tràn khắp gầm tủ.', 1, 'Tự tháo ống khi chưa biết, nước bẩn tràn tủ bếp.'),
            C('ke', 'Để đấy, tối anh Dũng về tính', 'ok', 'Tối mới rửa được bát.', 1, 'Bồn tắc cả buổi, không rửa được gì.')]),
    ], note='Bồn tắc: ngừng xả, vớt rác, pít-tông; không đổ hóa chất bừa; tắc nặng thì gọi thợ.', min_day=2),
    V('i_khach', 'incident', 0, 'Khách đến bất ngờ', 'Mười một giờ, hai cô chú họ hàng dưới quê lên không báo trước. Chị Thảo đi làm, mâm cơm trưa chỉ đủ nhà.', [
        pick('don', 'Đón khách', '🫖 Mời khách', [
            I('tra', '🫖', 'Pha ấm trà mới, mời nước', 'khách đi xa', True, 'Khách ngồi khô cổ, không ai mời nước.', 1, 'mn'),
            I('goi', '📞', 'Hỏi tên, gọi chị Thảo báo khách tới', 'chưa quen mặt', True, 'Không báo chị Thảo, chị về mới biết có khách.', 1, 'hn'),
            I('phong', '🛏️', 'Mời khách vào phòng ngủ anh chị nghỉ', 'cho mát', False, 'Cho khách vào phòng ngủ của chủ nhà khi chưa hỏi.', 1, 'mn'),
            I('khoa', '🔑', 'Đưa chìa khóa nhà cho khách tự đi lại', 'cho tiện', False, 'Đưa chìa khóa nhà cho người mình chưa biết.', 2, 'sf'),
        ], lead='Chọn những việc sẽ làm.', done='Khách được mời nước, chị Thảo đã biết.'),
        choose('com', 'Thêm mâm cơm', 'Chị Thảo bảo giữ khách ở lại ăn trưa. Tủ lạnh có trứng, đậu phụ, rau.', [
            C('them', 'Rán thêm trứng, đậu sốt cà chua, luộc thêm rau', 'good', 'Mâm cơm đầy đặn. Cô chú khen “cháu đảm đang”.'),
            C('hang', 'Chạy ra chợ mua hải sản bằng tiền chợ cả tuần', 'bad', 'Bữa trưa sang, tiền chợ tuần cạn.', 1, 'Tiêu hết tiền chợ cả tuần cho một bữa.', 'hn'),
            C('het', 'Nói khéo là nhà hết cơm', 'bad', 'Cô chú ngượng, ra quán ăn.', 2, 'Để khách của chủ nhà ra quán ăn.', 'mn')]),
    ], note='Khách bất ngờ: mời nước, báo chủ nhà, thêm món từ tủ lạnh; không cho vào phòng riêng, không đưa chìa khóa.', mods=('guests', None), weight=2, min_day=2),
    V('i_chay', 'incident', 1, 'Chảo dầu bốc cháy', 'Đang rán cá, chảo dầu bùng lửa cao, lửa liếm lên máy hút mùi.', [
        choose('lua', 'Lửa trên chảo', 'Bà Lành hét: “Dội nước vào! Dội nước vào!”', [
            C('dap', 'Tắt bếp, đậy vung kín (hoặc khăn ướt vắt kiệt), không dội nước', 'good', 'Lửa tắt phụt. Bà Lành run tay vịn bàn.'),
            C('nuoc', 'Dội cả gáo nước vào chảo', 'bad', 'Dầu nổ bùng, lửa bắn tung tóe.', 3, 'Dội nước vào chảo dầu cháy: dầu bắn bùng lửa.', 'sf', True),
            C('be', 'Bê chảo chạy ra sân', 'bad', 'Dầu sóng sánh bỏng cả tay.', 3, 'Bê chảo dầu đang cháy chạy qua nhà.', 'sf', True)]),
        pick('sau', 'Sau khi tắt lửa', '✅ Xong', [
            I('ga', '🔧', 'Khóa van bình ga', 'bếp ga', True, 'Không khóa van ga sau vụ cháy.', 2, 'sf'),
            I('ba', '👵', 'Đưa bà ra phòng khách ngồi, rót nước', 'bà run', True, 'Để bà đứng run trong bếp đầy khói.', 1, 'mn'),
            I('bao', '📞', 'Báo chị Thảo, chụp ảnh máy hút mùi bị ám khói', 'nói thật', True, 'Không báo chủ nhà chuyện cháy chảo.', 1, 'hn'),
            I('mo', '🌬️', 'Mở cửa cho khói ra', 'khói đặc', True, 'Khói đọng trong nhà, bé Cốm ho.', 1, 'sf'),
        ], lead='Chọn những việc sẽ làm.', done='Bếp an toàn, cả nhà bình tĩnh.'),
    ], note='Chảo dầu cháy: tắt bếp, đậy vung; tuyệt đối không dội nước.', min_day=4),
    V('i_ga', 'incident', 0, 'Mùi ga', 'Vừa về tới nhà, bạn ngửi thấy mùi ga nồng nặc trong bếp.', [
        order('ga', 'Xử lý mùi ga', '✅ Xong', [
            O('van', '🔧', 'Khóa van bình ga'), O('cua', '🪟', 'Mở hết cửa cho thoáng'), O('ra', '👨‍👩‍👧', 'Đưa bà và các bé ra ngoài'),
            O('goi', '📞', 'Ra ngoài rồi gọi chị Thảo, gọi cửa hàng ga'),
            O('den', '💡', 'Bật đèn bếp xem chỗ rò', (3, 'Bật công tắc điện lúc nhà đầy ga: một tia lửa là cháy nổ.', 'sf', True)),
            O('quat', '🌀', 'Bật quạt cho bay mùi', (3, 'Bật quạt điện lúc rò ga: tia lửa ở công tắc có thể gây nổ.', 'sf', True)),
        ], [('van', 'goi', 1, 'Gọi điện trong bếp đầy ga trước khi khóa van, ra ngoài.', 'sf'), ('cua', 'goi', 1, 'Chưa mở cửa đã đứng gọi điện.', 'sf'),
            ('ra', 'goi', 1, 'Gọi điện xong mới đưa bà và các bé ra ngoài.', 'sf')], lead='Rò ga: không đụng tới công tắc điện.'),
    ], note='Mùi ga: khóa van, mở cửa, đưa mọi người ra, ra ngoài mới gọi điện; không bật tắt công tắc.', min_day=5),
]

TET = [
    V('x_ban_tho', 'tet', 1, 'Lau dọn bàn thờ', 'Hai mươi lăm tháng Chạp. Bà Lành: “Lau bàn thờ giúp bà. Cẩn thận, đồ thờ của ông bà đấy.”', [
        choose('bat_huong', 'Bát hương', 'Bát hương đầy chân hương, tàn tro.', [
            C('de', 'Để nguyên bát hương, chờ bà và chị Thảo tự bao sái', 'good', 'Bà Lành gật gù: “Cháu biết ý đấy.”'),
            C('rut', 'Tự rút chân hương, đổ bớt tro cho gọn', 'bad', 'Bà Lành tái mặt: “Ai cho cháu động vào bát hương!”', 2, 'Tự ý rút chân hương trên bàn thờ nhà người ta.', 'mn')]),
        order('lau', 'Lau bàn thờ', '🧧 Bày lại', [
            O('chup', '📷', 'Chụp ảnh vị trí đồ thờ'), O('ha', '🙌', 'Hạ đồ thờ xuống (trừ bát hương)'), O('lau', '🧽', 'Lau bàn thờ bằng khăn sạch, nước gừng ấm'),
            O('lau_do', '✨', 'Lau đồ thờ, lau khô'), O('bay', '🏮', 'Bày lại đúng chỗ cũ'),
        ], [('chup', 'ha', 1, 'Hạ đồ xuống rồi mới nhớ ra chưa chụp ảnh, bày lại sai chỗ.', 'cr'), ('ha', 'lau', 1, 'Lau bàn thờ khi đồ còn nguyên trên đó.', 'cr'),
            ('lau_do', 'bay', 1, 'Đồ thờ còn ướt đã bày lên.', 'cr'), ('lau', 'bay', 1, 'Bày đồ lên rồi mới lau bàn?', 'cr')]),
        pick('mam', 'Mâm ngũ quả', '🍊 Bày mâm', [
            I('chuoi', '🍌', 'Nải chuối xanh già', 'đỡ dưới cùng', True, 'Mâm ngũ quả thiếu nải chuối xanh.', 1),
            I('buoi', '🟢', 'Quả bưởi tròn đều', 'đặt giữa', True, 'Mâm thiếu quả bưởi.', 1),
            I('phat_thu', '🖐️', 'Quả phật thủ', 'bà thích', True, 'Bà dặn phật thủ mà quên.', 1),
            I('le_dap', '🍐', 'Quả lê bị dập', 'rẻ', False, 'Đặt quả dập lên bàn thờ.', 1),
        ], lead='Chọn quả bày mâm ngũ quả.', done='Mâm ngũ quả tươi, đẹp.'),
    ], note='Bàn thờ: không động vào bát hương, chụp ảnh trước khi hạ đồ, bày lại đúng chỗ.', mods=('tet',), weight=3, min_day=5),
    V('x_tong', 'tet', 0, 'Tổng vệ sinh đón Tết', 'Chị Thảo: “Tết rồi em ơi. Giặt rèm, lau quạt, dọn gầm tủ. Đồ cũ nào không dùng thì dồn một chỗ.”', [
        pick('lam', 'Việc dọn Tết', '🧹 Dọn', [
            I('rem', '🪟', 'Tháo rèm cửa đi giặt', 'bụi cả năm', True, 'Rèm cửa vẫn bụi đón Tết.', 1),
            I('quat', '🌀', 'Lau quạt trần, cánh quạt', 'đen bụi', True, 'Bật quạt ngày Tết, bụi rơi đầy mâm.', 1),
            I('gam', '📦', 'Dọn gầm tủ, gầm giường', 'đồ chơi của bé lăn vào', True, 'Gầm giường còn đầy bụi.', 1),
            I('thang', '🪜', 'Trèo ghế nhựa chồng lên bàn để lau trần', 'cho nhanh', False, 'Chồng ghế lên bàn trèo lau trần, trượt ngã đau lưng.', 2, 'sf'),
        ], lead='Chọn những việc sẽ làm.', done='Nhà cửa sạch bong đón Tết.'),
        choose('do_cu', 'Đồ cũ của ông', 'Trong gầm tủ có thùng đồ cũ: áo bộ đội, mấy lá thư, chiếc đài bán dẫn của ông đã mất.', [
            C('hoi', 'Lau sạch, để riêng một chỗ, hỏi bà trước', 'good', 'Bà Lành ôm chiếc đài, khóc. Bà giữ lại cả thùng.'),
            C('don', 'Dồn chung với đồ cũ định bỏ', 'bad', 'Suýt nữa đồ của ông theo xe ve chai.', 2, 'Suýt bỏ kỷ vật của ông như đồ bỏ đi.', 'cr'),
            C('ban', 'Bán cho đồng nát lấy tiền mua bánh mứt', 'bad', 'Bà Lành biết chuyện, khóc cả buổi.', 3, 'Bán kỷ vật của người đã mất.', 'hn')]),
        _talk_back('ba_tu', 'Bà Tư sang chơi', 'Bà Tư: “Tết nhất nhà người ta cho người làm về quê từ hai mươi ba rồi đấy. Nhà này bắt làm tới hai mươi tám à? Cháu bảo chị Thảo tăng lương đi!”',
                   ('Cảm ơn bà quan tâm, chuyện công xá cháu tự nói với chị Thảo', 'Bà Tư bĩu môi rồi về.'),
                   ('Ừ hử cho qua chuyện', 'Bà Tư đi kể với cả ngõ.', 'Để bà Tư đi kể chuyện nhà chủ khắp ngõ.', 'mn'),
                   ('Than thở với bà Tư một tràng', 'Chiều đó chị Thảo nghe được qua người khác.', 'Kể xấu chủ nhà với hàng xóm.', 'hn'),
                   ('“Bà lo việc nhà bà đi”', 'Bà Tư đứng chửi giữa ngõ.', 'Cãi nhau với hàng xóm của chủ nhà.')),
    ], note='Dọn Tết: không trèo ghế chồng bàn; đồ cũ của người đã mất phải hỏi bà trước.', mods=('tet',), weight=3, min_day=5),
]

VARIANTS = MARKET + COOK + DISHES + LAUNDRY + CLEAN + ELDER + KIDS + FRIDGE + GARDEN + INCIDENT + TET

# ================================================================ the morning (setup task)
KIND_LABEL = dict(setup='Nhận việc', market='Đi chợ', cook='Nấu ăn', dishes='Rửa bát', laundry='Giặt giũ', clean='Lau dọn', elder='Chăm bà',
                  kids='Trông trẻ', fridge='Tủ lạnh', garden='Chăm cây', incident='Sự cố', tet='Dọn Tết')
KIND_EMOJI = dict(setup='📋', market='🛒', cook='🍳', dishes='🍽️', laundry='🧺', clean='🧹', elder='👵', kids='🧸', fridge='🧊', garden='🪴',
                  incident='⚠️', tet='🧧')
# What the morning plan says about each job (the order step of the setup).
PLAN_ITEM = dict(market=('🛒', 'Đi chợ (chợ đông từ 6 giờ, 8 giờ hết cá tươi)'), cook=('🍳', 'Nấu ăn (cả nhà ăn 11:30)'),
                 dishes=('🍽️', 'Rửa bát (sau bữa ăn)'), laundry=('🧺', 'Giặt đồ (máy chạy một tiếng)'), clean=('🧹', 'Lau dọn nhà'),
                 elder=('👵', 'Thuốc cho bà (8 giờ, sau ăn sáng)'), kids=('🧸', 'Trông, đón các bé'), fridge=('🧊', 'Xếp tủ lạnh'),
                 garden=('🪴', 'Tưới cây (sáng sớm)'), tet=('🧧', 'Dọn nhà đón Tết'))
PLAN_RULES = [
    ('laundry', 'market', 1, 'Máy giặt chạy một tiếng: bật trước khi đi chợ cho đỡ phí thời gian.'),
    ('garden', 'market', 1, 'Tưới cây lúc sáng sớm, nắng lên rồi tưới là cây sốc nhiệt.'),
    ('market', 'cook', 1, 'Chưa đi chợ thì lấy gì mà nấu.'),
    ('market', 'fridge', 1, 'Đồ chợ về rồi mới xếp tủ lạnh.'),
    ('elder', 'cook', 1, 'Thuốc của bà 8 giờ sáng, trước giờ nấu trưa.'),
    ('cook', 'dishes', 1, 'Ăn xong mới rửa bát.'),
    ('cook', 'clean', 1, 'Nấu xong rồi lau dọn, đỡ dầu mỡ bắn ra sàn vừa lau.'),
    ('cook', 'kids', 1, 'Bé Su tan học 16:30, nấu trưa trước đã.'),
]
CASH_LINES = [
    (100, (50, 20, 20, 10)), (100, (20, 20, 20, 20, 10, 10)), (80, (50, 20, 10)), (80, (20, 20, 20, 10)), (60, (20, 20, 10, 10)), (60, (50, 10)),
]

# ================================================================ day modifiers
MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Đi chợ, nấu nướng, giặt giũ, lau dọn như mọi ngày.', weight=4),
    dict(id='rain', emoji='🌧️', label='Mưa dầm, nồm ẩm', hint='Đồ phơi lâu khô, sàn trơn, hay mất điện.', min_day=2, weight=2),
    dict(id='guests', emoji='🧳', label='Nhà có khách', hint='Họ hàng dưới quê lên: thêm mâm, thêm bát, thêm việc.', min_day=2, weight=2),
    dict(id='sick', emoji='🤒', label='Bà mệt', hint='Bà Lành trong người không khỏe: để ý thuốc men, cháo nhạt, đỡ bà đi lại.', min_day=3, weight=1),
    dict(id='tet', emoji='🧧', label='Giáp Tết', hint='Dọn nhà đón Tết, bàn thờ, mâm ngũ quả: việc gì cũng phải hỏi bà.', min_day=6, weight=1),
]

# ================================================================ regulars' small stories (by people index)
REG_STORY = {
    0: ('Chị Thảo: “Em ghi sổ chợ rõ ràng, chị đỡ lo hẳn.”', 'Chị Thảo dán thêm tờ “Sổ tay nhà” mới lên tủ lạnh, ghi tên bạn ở góc.',
        'Chị Thảo tặng bạn chiếc tạp dề thêu tên.'),
    1: ('Bà Lành: “Nấu ăn thì phải nếm, mà nếm bằng thìa riêng.”', 'Bà Lành dạy bạn muối dưa cà theo kiểu nhà bà.', 'Bà Lành gọi bạn là “cháu gái thứ ba của bà”.'),
    2: ('Anh Dũng: “Có hộp cơm em làm, cả công trường ghen tị.”', 'Anh Dũng sửa giúp cái xe đạp cũ của bạn.', 'Anh Dũng bảo cả nhà nhớ sinh nhật bạn.'),
    3: ('Bé Su: “Chị ơi mai chị lại đón em nha!”', 'Bé Su vẽ tặng bạn bức tranh “cả nhà em và chị”.', 'Bé Su được điểm mười toán, chạy về khoe bạn đầu tiên.'),
}

INTRO = dict(
    title='Giới thiệu nghề: nội trợ, giúp việc nhà',
    lead='Nhà chị Thảo ba thế hệ ở ngõ Hoa Sữa: bà Lành 76 tuổi, anh chị đi làm cả ngày, bé Su lớp 2 và bé Cốm mười tám tháng. Bạn tới giúp việc theo giờ: đi chợ, cơm nước, giặt giũ, lau dọn, trông trẻ, chăm bà.',
    work=[('📋', 'Sáng: đếm tiền chợ, xếp việc trong ngày'), ('🛒', 'Đi chợ: nhớ danh sách, chọn đồ tươi, trả giá, cân lại'),
          ('📒', 'Ghi sổ chợ đúng từng xu, trả tiền thừa'), ('🍳', 'Nấu theo khẩu vị từng người, nhớ ai dị ứng gì'),
          ('🧺', 'Giặt phân loại màu, móc túi trước khi giặt'), ('🧹', 'Lau dọn trên xuống dưới, đúng chất tẩy'),
          ('👵', 'Thuốc của bà đúng giờ, đúng viên'), ('🧸', 'Trông bé an toàn, đón bé đúng người')],
    meet=[('👩', 'Chị Thảo: giữ sổ chợ, dặn ba lần'), ('👵', 'Bà Lành: huyết áp, tiểu đường, chê giỏi'), ('👨', 'Anh Dũng: dễ tính, đau dạ dày'),
          ('👧', 'Bé Su: dị ứng tôm, mê điện thoại'), ('🥬', 'Cô Năm bán rau, chú Thịnh bán cá hay cân thiếu'), ('👀', 'Bà Tư hàng xóm: cái gì cũng hỏi'),
          ('⚠️', 'Mất điện, cơm khê, bồn tắc, khách đến bất ngờ'), ('🧧', 'Giáp Tết: bàn thờ, mâm ngũ quả')],
    stars=[('🥬', 'Đồ tươi, đúng danh sách'), ('📒', 'Tiền chợ rõ ràng từng xu'), ('🍲', 'Đúng khẩu vị, không ai ăn phải thứ mình kiêng'),
           ('🧯', 'An toàn cho bà và các bé'), ('🤐', 'Kín đáo, không động vào đồ riêng'), ('🙏', 'Làm sai thì nói thật')],
)

# ================================================================ surprises (kit desk scripts): the awkward people around the house
DESK = [
    dict(id='camera', title='Chị Thảo gọi video', emoji='📹', npc=0, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Chị Thảo gọi video lúc mười giờ: “Chị xem camera thấy em ngồi bấm điện thoại mười phút. Nhà chị trả công theo giờ đấy nhé.”',
         options=[dict(id='explain', label='Bình tĩnh nói: em vừa phơi xong, ngồi nghỉ uống nước, giờ em làm tiếp', hint='', effects=dict(xp=3), good=True,
                       outcome='Chị Thảo ừ một tiếng: “Ừ, nghỉ tí thì được. Chị lo quá thôi.”'),
                  dict(id='sorry', label='Xin lỗi rối rít, làm luôn không nghỉ nữa', hint='Mệt cả ngày', effects=dict(patience=-3), good=None,
                       outcome='Cả ngày không dám ngồi, tối về đau lưng.'),
                  dict(id='argue', label='“Chị trả có từng ấy mà còn soi từng phút”', hint='', effects=dict(review=[2, 'Nói một câu mà đáp lại mười câu, thái độ quá.']),
                       good=False, outcome='Chị Thảo tắt máy. Tối về hai bên không nói với nhau câu nào.')],
         default='sorry'),
    dict(id='gossip', title='Bà Tư sang hỏi chuyện', emoji='👀', npc=5, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Bà Tư ghé tai: “Cháu ở đây lâu, nói bà nghe, vợ chồng nhà Thảo dạo này có hay cãi nhau không? Thằng Dũng về muộn thế chắc có gì…”',
         options=[dict(id='dodge', label='Cười, đánh trống lảng sang chuyện giá rau', hint='', effects=dict(xp=3), good=True,
                       outcome='Bà Tư hỏi mãi không được gì, bĩu môi về.'),
                  dict(id='tell', label='Kể nhỏ vài chuyện cho bà vui', hint='', effects=dict(review=[2, 'Người làm nhà Thảo đi kể chuyện nhà chủ khắp ngõ.']), good=False,
                       outcome='Chiều hôm đó cả ngõ bàn tán. Chị Thảo nghe được, mặt lạnh tanh.'),
                  dict(id='shoo', label='“Chuyện nhà người ta bà hỏi làm gì”', hint='', effects={}, good=None,
                       outcome='Bà Tư giận, về nói cháu “láo”. Nhưng chuyện nhà chủ vẫn kín.')],
         default='dodge'),
    dict(id='extra_house', title='Tiện sang dọn nhà em gái', emoji='🏚️', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Chị Thảo: “Tiện em sang dọn giúp nhà em gái chị luôn nhé, cùng ngõ thôi. Nhà nó bé tí, có một tiếng.” Không nói gì tới tiền công.',
         options=[dict(id='ask', label='Vui vẻ nhận, hỏi rõ: việc thêm thì chị tính thêm công giờ nhé', hint='', effects=dict(money=10, xp=2), good=True,
                       outcome='Chị Thảo khựng một chút rồi gật: “Ừ, chị gửi thêm 10 xu.”'),
                  dict(id='free', label='Làm không công cho vui lòng chủ', hint='Mất một tiếng', effects=dict(patience=-6), good=None,
                       outcome='“Một tiếng” thành ba tiếng. Lần sau chị Thảo lại nhờ.'),
                  dict(id='no', label='“Em làm cho nhà chị thôi”', hint='', effects=dict(review=[3, 'Nhờ có tí việc cũng không giúp.']), good=False,
                       outcome='Chị Thảo im lặng, tối nhắn tin gọn lỏn.')],
         default='free'),
    dict(id='leftovers', title='Bữa cơm của người làm', emoji='🍚', npc=1, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Bà Lành gắp bát cơm nguội hôm qua với đĩa rau thừa: “Cháu ăn cái này, mâm trên để phần cả nhà.”',
         options=[dict(id='talk', label='Lễ phép nói chị Thảo đã thỏa thuận cho cháu ăn cùng mâm, xin phép ăn cơm mới', hint='', effects=dict(xp=3), good=True,
                       outcome='Bà Lành ngớ ra, gọi điện hỏi chị Thảo. Từ hôm đó bạn ăn cùng mâm.'),
                  dict(id='eat', label='Ăn cho xong chuyện', hint='', effects=dict(patience=-2), good=None,
                       outcome='Chiều bạn hơi đau bụng. Bà Lành coi đó là chuyện thường.'),
                  dict(id='leave', label='Đặt bát xuống, ra ngoài mua bánh mì ăn', hint='', effects=dict(review=[3, 'Người làm dỗi bỏ bữa, khó chiều.']), good=False,
                       outcome='Bà Lành kể với chị Thảo là cháu “chê cơm nhà”.')],
         default='eat'),
    dict(id='missing_money', title='Chị Thảo mất tiền', emoji='💸', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Chị Thảo lục tung túi xách: “Chị để 200 xu trên bàn sáng nay, giờ đâu rồi? Sáng nay ở nhà chỉ có em thôi đấy.”',
         options=[dict(id='search', label='Bình tĩnh cùng chị nhớ lại, tìm từng chỗ chị hay để', hint='', effects=dict(xp=5), good=True,
                       outcome='Tiền nằm trong túi áo khoác chị mặc sáng nay. Chị Thảo ngượng, xin lỗi bạn.'),
                  dict(id='swear', label='Thề sống thề chết là không lấy', hint='', effects=dict(patience=-4), good=None,
                       outcome='Chị Thảo vẫn nghi. Mãi tối mới tìm thấy tiền trong túi áo khoác.'),
                  dict(id='quit', label='“Nghi thì em nghỉ, chị tìm người khác”', hint='', effects=dict(review=[2, 'Hỏi có một câu mà người làm làm ầm lên đòi nghỉ.']), good=False,
                       outcome='Hai bên to tiếng. Tối tìm thấy tiền, nhưng không ai xin lỗi ai.')],
         default='swear'),
    dict(id='dung_secret', title='Anh Dũng nhờ nói dối', emoji='🤫', npc=2, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Anh Dũng dúi 5 xu: “Lát vợ anh hỏi thì bảo anh về nhà từ bảy giờ nhé. Anh đi nhậu với hội công trình tí thôi.”',
         options=[dict(id='decline', label='Trả lại tiền, nói em không nói dối chị Thảo được, anh tự nói nhé', hint='', effects=dict(xp=4), good=True,
                       outcome='Anh Dũng gãi đầu: “Ừ… thôi anh tự khai.”'),
                  dict(id='take', label='Nhận tiền, gật đầu', hint='', effects=dict(money=5, review=[1, 'Người làm nói dối giúp chồng. Tôi hết tin rồi.']), good=False,
                       outcome='Chị Thảo xem camera thấy anh Dũng mười giờ mới về.'),
                  dict(id='silent', label='Không nhận tiền, không hứa gì', hint='', effects={}, good=None,
                       outcome='Tối chị Thảo không hỏi. Chuyện trôi qua.')],
         default='silent'),
    dict(id='kid_phone', title='Bé Su đòi điện thoại', emoji='📱', npc=3, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Bé Su: “Cho em mượn điện thoại của chị chơi game. Không cho em mách mẹ là chị mắng em!”',
         options=[dict(id='play', label='Từ chối nhẹ nhàng, rủ bé chơi ô ăn quan', hint='', effects=dict(xp=3, patience=-2), good=True,
                       outcome='Bé Su phụng phịu năm phút rồi mê ô ăn quan, thắng bạn ba ván.'),
                  dict(id='lend', label='Cho mượn cho bé im', hint='', effects={}, good=None,
                       outcome='Bé chơi hai tiếng, tối còn khóc đòi điện thoại của mẹ.'),
                  dict(id='threat', label='“Mách đi, chị mách lại chuyện em đánh bạn”', hint='', effects=dict(review=[3, 'Dọa trẻ con như thế không được.']), good=False,
                       outcome='Bé Su khóc chạy đi. Tối hai bên đều mách.')],
         default='lend'),
    dict(id='late_night', title='Tin nhắn mười giờ đêm', emoji='🌙', npc=0, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Chị Thảo nhắn lúc mười giờ đêm: “Mai em sang từ năm giờ sáng luộc gà cúng rằm nhé.” Đã quá giờ nghỉ của bạn.',
         options=[dict(id='deal', label='Nhắn lại: em sang được, sớm hai tiếng chị tính thêm công nhé', hint='', effects=dict(money=8, xp=2), good=True,
                       outcome='Chị Thảo: “Ừ, chị gửi thêm.” Sáng ra luộc gà, chị dúi thêm tiền.'),
                  dict(id='yes', label='Dạ vâng cho xong', hint='Mất ngủ', effects=dict(patience=-5), good=None,
                       outcome='Bốn rưỡi dậy, cả ngày ngáp. Không ai nói tiền công.'),
                  dict(id='ignore', label='Tắt máy đi ngủ, sáng mai tính', hint='', effects=dict(review=[3, 'Nhắn việc gấp không trả lời.']), good=False,
                       outcome='Sáng ra chị Thảo phải tự luộc gà, mặt không vui.')],
         default='yes'),
    dict(id='cut_pay', title='Trừ tiền cái cốc vỡ', emoji='🥛', npc=0, min_day=4, tone='tense', at='between', weight=2, mods=None,
         text='Chị Thảo: “Tháng này chị trừ 10 xu tiền cái cốc thủy tinh vỡ hôm trước nhé.” Hôm đó bé Su làm vỡ, bà Lành cũng thấy.',
         options=[dict(id='calm', label='Nhẹ nhàng kể lại hôm đó bé Su làm vỡ, nhờ chị hỏi bà', hint='', effects=dict(xp=4), good=True,
                       outcome='Bà Lành xác nhận. Chị Thảo bảo thôi không trừ.'),
                  dict(id='pay', label='Chịu trừ cho êm chuyện', hint='Mất 10 xu', effects=dict(money=-10), good=None,
                       outcome='Bạn mất 10 xu cho cái cốc mình không làm vỡ.'),
                  dict(id='loud', label='Cãi to: “Em không làm vỡ!”', hint='', effects=dict(review=[2, 'Hỏi một câu mà người làm quát lại.']), good=False,
                       outcome='Bé Su sợ quá, khóc. Chuyện cái cốc thành chuyện cả nhà.')],
         default='pay'),
    dict(id='sales', title='Bà Tư rủ “làm giàu”', emoji='📦', npc=5, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Bà Tư xách cái nồi “đa năng” sang: “Cháu mua một cái 60 xu, rủ được ba người là hoàn tiền, rủ mười người là có lương tháng!”',
         options=[dict(id='no', label='Cảm ơn bà, cháu không tham gia', hint='', effects=dict(xp=3), good=True,
                       outcome='Bà Tư lắc đầu “dại thế”. Tháng sau công an phường tới hỏi chuyện bà Tư.'),
                  dict(id='buy', label='Mua một cái cho bà vui', hint='Mất 20 xu tiền cọc', effects=dict(money=-20), good=False,
                       outcome='Nồi về được một tuần thì hỏng. Bà Tư bảo “tại cháu không rủ thêm người”.'),
                  dict(id='later', label='Hẹn hôm khác', hint='', effects={}, good=None, outcome='Bà Tư sang hỏi thêm ba lần nữa.')],
         default='later'),
    dict(id='drip', title='Nước quần áo nhỏ sang sân bên', emoji='💧', npc=5, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Bà Tư đứng dưới sân chống nạnh: “Quần áo nhà này nhỏ nước tong tỏng xuống sân tôi! Ướt hết cả mẹt cá khô!”',
         options=[dict(id='fix', label='Xin lỗi, vắt kỹ, dời sào phơi vào trong', hint='', effects=dict(xp=3, patience=-2), good=True,
                       outcome='Bà Tư lầm bầm rồi thôi. Mẹt cá khô của bà khô ráo.'),
                  dict(id='ignore', label='Kệ, nắng lên tự khô', hint='', effects=dict(review=[3, 'Nhà này phơi đồ nhỏ nước sang nhà người ta.']), good=False,
                       outcome='Bà Tư sang tận nhà mách bà Lành.'),
                  dict(id='back', label='“Mẹt cá nhà bà cũng bốc mùi sang đây đấy”', hint='', effects=dict(review=[2, 'Người làm nhà Thảo láo với người già.']), good=False,
                       outcome='Hai bên cãi nhau. Chị Thảo về phải sang xin lỗi bà Tư.')],
         default='ignore'),
    dict(id='relative', title='Họ hàng sai vặt', emoji='🙋', npc=1, min_day=2, tone='tense', at='between', weight=2, mods=('guests',),
         text='Ông cậu của chị Thảo gác chân lên ghế: “Ê con ở, lấy cốc nước! Rồi đấm lưng cho ông tí!”',
         options=[dict(id='polite', label='Mang nước, nhẹ nhàng xin ông gọi cháu bằng tên', hint='', effects=dict(xp=3), good=True,
                       outcome='Ông cậu cười khà khà: “Ừ, cháu Hoa Sữa.” Từ đó gọi tên đàng hoàng.'),
                  dict(id='do', label='Làm hết cho ông vừa lòng', hint='', effects=dict(patience=-4), good=None,
                       outcome='Đấm lưng nửa tiếng, việc nhà dồn lại.'),
                  dict(id='refuse', label='“Cháu là người giúp việc, không phải con ở”', hint='', effects=dict(review=[2, 'Con bé giúp việc nói hỗn với ông.']), good=False,
                       outcome='Ông cậu đỏ mặt. Chị Thảo về phải xin lỗi hai bên.')],
         default='do'),
    dict(id='bag_check', title='Bà khám túi', emoji='👜', npc=1, min_day=4, tone='tense', at='between', weight=1, mods=None,
         text='Lúc bạn về, bà Lành chặn ở cửa: “Mở túi cho bà xem. Nhà dạo này hay mất đồ.”',
         options=[dict(id='open', label='Bình tĩnh mở túi, xin bà lần sau có gì nói trước với chị Thảo', hint='', effects=dict(xp=3), good=True,
                       outcome='Túi chỉ có ví, điện thoại, hộp cơm. Bà Lành ngượng, dúi cho quả chuối.'),
                  dict(id='refuse', label='Không mở, bỏ về', hint='', effects=dict(review=[3, 'Người làm không cho xem túi, đáng ngờ.']), good=None,
                       outcome='Bà Lành kể với chị Thảo. Hôm sau phải giải thích mãi.'),
                  dict(id='quit', label='Ném túi xuống sàn: “Đây, khám đi!”', hint='', effects=dict(review=[1, 'Người làm ném túi trước mặt người già.']), good=False,
                       outcome='Bà Lành run tay. Chị Thảo về, cả nhà im lặng.')],
         default='open'),
]

# ================================================================ situations (sit_ engine)
SITUATIONS = [
    dict(id='NT-S01', title='Tiền chợ còn thừa', npc=0, tone='gentle', min_day=1,
         opening='Đi chợ về còn thừa 12 xu. Chị Thảo đang họp, không ai biết chính xác hôm nay tiêu bao nhiêu.',
         swap='Bạn là chị Thảo, đi làm cả ngày, phải tin người ở nhà giữ tiền chợ.',
         facts=[dict(id='book', title='Sổ chợ', source='Ngăn kéo bếp', text='Chị Thảo ghi sổ chợ từng khoản từ năm năm nay, cuối tuần cộng lại.'),
                dict(id='price', title='Giá chợ', source='Cô Năm', text='Cô Năm bảo chị Thảo hay hỏi giá rau, giá cá mỗi tuần.'),
                dict(id='old', title='Người làm cũ', source='Bà Tư', text='Bà Tư kể người làm cũ bị cho nghỉ vì ghi khống tiền chợ.')],
         options=[dict(id='true', label='Ghi đúng từng khoản, để 12 xu thừa vào hộp tiền chợ', requires=['book'], quality='good', stars=5,
                       review='Sổ chợ rõ ràng từng xu, tiền thừa để đúng chỗ. Yên tâm giao việc.',
                       outcome='Cuối tuần chị Thảo cộng sổ khớp từng xu, tăng thêm tiền chợ cho thoải mái.',
                       perspectives=[dict(who='Chị Thảo', emoji='👩', text='Người giữ được tiền chợ là người giữ được nhà.'),
                                     dict(who='Cô Năm', emoji='🥬', text='Cô bán bao nhiêu, sổ nhà đấy ghi đúng bấy nhiêu.')]),
                  dict(id='round', label='Ghi tròn số cho dễ, bỏ túi mấy xu lẻ', requires=['price'], quality='bad', stars=2,
                       review='Cộng sổ cứ lệch vài xu mỗi ngày. Chuyện nhỏ mà mất lòng tin.',
                       outcome='Chị Thảo hỏi giá cô Năm, thấy lệch. Không nói gì, nhưng từ đó đưa tiền chợ từng bữa.',
                       perspectives=[dict(who='Chị Thảo', emoji='😕', text='Vài xu thì không sao, cái mất là lòng tin.'),
                                     dict(who='Bà Lành', emoji='👵', text='Ăn bớt từ đồng nhỏ là hỏng từ đồng to.')]),
                  dict(id='keep', label='Không ghi gì, giữ luôn 12 xu', quality='bad', stars=1, review='Tiền chợ thừa mà người làm giữ luôn.',
                       outcome='Cuối tuần sổ thiếu 12 xu. Chị Thảo cho bạn nghỉ một buổi để “suy nghĩ”.',
                       perspectives=[dict(who='Chị Thảo', emoji='😠', text='Hỏi thì không nói, hỏi ra mới biết.'),
                                     dict(who='Bà Tư', emoji='👀', text='Tôi đã bảo mà, người làm bây giờ…')])],
         lesson='Tiền chợ là tiền của nhà chủ: ghi đúng từng khoản, tiền thừa trả lại đúng chỗ.'),
    dict(id='NT-S02', title='Bé Su ăn nhầm tôm', npc=3, tone='tense', min_day=2,
         opening='Ở tiệc sinh nhật bạn cùng lớp, bé Su lỡ ăn miếng bánh có tôm. Mười phút sau môi sưng, nổi mẩn khắp người.',
         facts=[dict(id='sign', title='Dấu hiệu', source='Nhìn bé', text='Môi sưng, mẩn đỏ lan nhanh, bé bắt đầu thở khò khè, kêu khó nuốt.'),
                dict(id='note', title='Sổ tay nhà', source='Tủ lạnh', text='Bé Su dị ứng tôm. Khó thở thì gọi 115 ngay. Trong cặp có thuốc chống dị ứng bác sĩ kê.'),
                dict(id='mom', title='Chị Thảo', source='Điện thoại', text='Chị Thảo đang trên xe buýt, nửa tiếng nữa mới về.')],
         options=[dict(id='call', label='Gọi 115 ngay, cho bé uống thuốc bác sĩ kê trong cặp, báo chị Thảo', requires=['sign', 'note'], quality='good', stars=5,
                       review='Bé khó thở, người giúp việc gọi cấp cứu ngay. Bác sĩ bảo may mà gọi sớm.',
                       outcome='Xe cấp cứu tới, bé được xử trí kịp. Tối bé đã cười lại.',
                       perspectives=[dict(who='Chị Thảo', emoji='👩', text='Chị chạy tới viện, thấy con ngồi ăn cháo mà chân run.'),
                                     dict(who='Bác sĩ', emoji='🩺', text='Dị ứng có khó thở là cấp cứu, gọi sớm là đúng.')]),
                  dict(id='wait', label='Chờ chị Thảo về quyết', requires=['mom'], quality='bad', stars=1,
                       review='Bé khó thở mà ngồi chờ mẹ về nửa tiếng.', outcome='Chị Thảo về thấy bé tím tái, phải tự gọi cấp cứu.',
                       perspectives=[dict(who='Chị Thảo', emoji='😱', text='Nửa tiếng đó chị không dám nghĩ lại.'),
                                     dict(who='Bé Su', emoji='👧', text='(Thở không được, khóc không ra tiếng.)')]),
                  dict(id='home', label='Cho bé uống nhiều nước, nằm nghỉ', quality='bad', stars=1, review='Bé dị ứng nặng mà chỉ cho uống nước.',
                       outcome='Bé mệt lả. Hàng xóm thấy lạ gọi cấp cứu hộ.',
                       perspectives=[dict(who='Hàng xóm', emoji='👀', text='Thấy con bé thở khò khè là tôi gọi luôn.'),
                                     dict(who='Bác sĩ', emoji='🩺', text='Uống nước không chữa được dị ứng.')])],
         lesson='Dị ứng kèm khó thở là cấp cứu: gọi 115 ngay, dùng thuốc bác sĩ đã kê, rồi báo bố mẹ.'),
    dict(id='NT-S03', title='Bà không chịu uống thuốc', npc=1, tone='gentle', min_day=2,
         opening='Bà Lành đẩy hộp thuốc: “Uống mãi chẳng khỏi, bà bỏ thuốc huyết áp từ mai.”',
         facts=[dict(id='doc', title='Lời bác sĩ', source='Sổ khám bệnh', text='Bác sĩ dặn thuốc huyết áp uống đều hằng ngày, không tự ý bỏ.'),
                dict(id='why', title='Vì sao bà chán', source='Bà Lành', text='Bà than viên thuốc to, khó nuốt, uống xong hay khô miệng.'),
                dict(id='son', title='Anh Dũng', source='Gia đình', text='Bà nghe lời anh Dũng nhất nhà.')],
         options=[dict(id='listen', label='Nghe bà than, ghi lại chuyện khó nuốt, khô miệng để chị Thảo hỏi bác sĩ; nhờ anh Dũng nói chuyện với bà', requires=['why', 'son'], quality='good', stars=5,
                       review='Cháu nó chịu nghe bà than, rồi báo bác sĩ. Bác sĩ đổi viên nhỏ hơn.',
                       outcome='Lần khám sau bác sĩ đổi thuốc viên nhỏ. Bà uống đều trở lại.',
                       perspectives=[dict(who='Bà Lành', emoji='👵', text='Có người nghe bà nói là bà dễ chịu rồi.'),
                                     dict(who='Anh Dũng', emoji='👨', text='Mẹ chỉ cần có người hỏi han thôi.')]),
                  dict(id='hide', label='Nghiền thuốc trộn vào cháo cho bà khỏi biết', quality='bad', stars=2,
                       review='Tự ý nghiền thuốc trộn vào cháo, bà biết được giận lắm.', outcome='Bà phát hiện vị đắng, từ đó không ăn cháo cháu nấu.',
                       perspectives=[dict(who='Bà Lành', emoji='😠', text='Lừa bà như lừa trẻ con.'),
                                     dict(who='Dược sĩ', emoji='💊', text='Có thuốc không được nghiền, phải hỏi trước.')]),
                  dict(id='let', label='Bà không uống thì thôi, tùy bà', requires=['why'], quality='bad', stars=1,
                       review='Bỏ thuốc huyết áp ba hôm, bà chóng mặt phải đi viện.', outcome='Ba hôm sau huyết áp bà vọt lên 180.',
                       perspectives=[dict(who='Chị Thảo', emoji='😟', text='Giá em báo chị sớm.'),
                                     dict(who='Bác sĩ', emoji='🩺', text='Thuốc huyết áp tự bỏ là nguy hiểm.')])],
         lesson='Người già bỏ thuốc thường có lý do: lắng nghe, báo gia đình để hỏi bác sĩ, không lừa, không bỏ mặc.'),
    dict(id='NT-S04', title='Làm thêm giờ không công', npc=0, tone='gentle', min_day=3,
         opening='Đã ba tuần chị Thảo nhờ ở lại thêm một hai tiếng mỗi tối mà không nhắc gì tới tiền công.',
         facts=[dict(id='deal', title='Thỏa thuận ban đầu', source='Tin nhắn', text='Lúc nhận việc hai bên nhắn: làm từ 7 tới 17 giờ, công theo việc.'),
                dict(id='hours', title='Sổ giờ', source='Điện thoại của bạn', text='Bạn ghi lại: ba tuần ở lại thêm tổng cộng hai mươi tiếng.'),
                dict(id='busy', title='Nhà chị Thảo', source='Bà Lành', text='Chị Thảo đang mùa quyết toán, ngày nào cũng về muộn.')],
         options=[dict(id='talk', label='Chọn lúc chị rảnh, đưa sổ giờ, đề nghị tính thêm công hoặc đổi ngày nghỉ', requires=['deal', 'hours'], quality='good', stars=5,
                       review='Em nói rõ ràng, có sổ giờ hẳn hoi. Chị sơ ý, đã gửi bù.', outcome='Chị Thảo gửi bù tiền giờ, hứa báo trước khi nhờ ở lại.',
                       perspectives=[dict(who='Chị Thảo', emoji='👩', text='Chị bận quá nên quên mất, em nói là đúng.'),
                                     dict(who='Bà Lành', emoji='👵', text='Sòng phẳng thì mới ở với nhau lâu.')]),
                  dict(id='quiet', label='Thôi, nhà chị đang bận, im lặng làm tiếp', requires=['busy'], quality='ok', stars=4,
                       review='Em chịu khó lắm.', outcome='Chị Thảo vẫn nhờ ở lại mỗi tối. Bạn mệt dần.',
                       perspectives=[dict(who='Chị Thảo', emoji='🙂', text='Có em đỡ quá.'),
                                     dict(who='Bạn', emoji='😮‍💨', text='Không nói thì không ai biết mình mệt.')]),
                  dict(id='quit', label='Nghỉ ngang không báo trước', quality='bad', stars=1, review='Đang mùa bận, người giúp việc nghỉ ngang không một lời.',
                       outcome='Chị Thảo xoay xở mãi, bà Lành phải tự nấu cơm.',
                       perspectives=[dict(who='Chị Thảo', emoji='😣', text='Có gì nói với chị chứ.'),
                                     dict(who='Bé Su', emoji='👧', text='Chị ấy đâu rồi hả mẹ?')])],
         lesson='Làm thêm giờ thì ghi lại, nói rõ đúng lúc; im lặng hay bỏ ngang đều không giải quyết được.'),
    dict(id='NT-S05', title='Thuốc kháng sinh không đơn', npc=0, tone='gentle', min_day=3,
         opening='Bé Cốm sốt nhẹ. Chị Thảo nhắn: “Em ra hiệu thuốc mua cho bé vỉ kháng sinh như lần trước, khỏi đi khám cho mất thời gian.”',
         facts=[dict(id='rx', title='Quy định', source='Hiệu thuốc', text='Kháng sinh là thuốc kê đơn, phải có bác sĩ khám và kê.'),
                dict(id='old', title='Lần trước', source='Sổ khám', text='Lần trước bé bị viêm tai, bác sĩ kê kháng sinh năm ngày theo cân nặng.'),
                dict(id='now', title='Bé hôm nay', source='Nhiệt kế', text='Bé sốt 38 độ, vẫn chơi, ăn được, không ho.')],
         options=[dict(id='doctor', label='Nhắn chị: kháng sinh phải có bác sĩ kê; giờ hạ sốt, lau mát, theo dõi, chiều đưa bé đi khám', requires=['rx', 'now'], quality='good', stars=5,
                       review='Em nói đúng, đi khám mới biết bé chỉ sốt mọc răng.', outcome='Bác sĩ bảo bé sốt do mọc răng, không cần kháng sinh.',
                       perspectives=[dict(who='Chị Thảo', emoji='👩', text='May mà không cho con uống bừa.'),
                                     dict(who='Bác sĩ', emoji='🩺', text='Kháng sinh dùng sai còn hại hơn không dùng.')]),
                  dict(id='buy', label='Ra hiệu thuốc nói khéo để mua cho được', requires=['old'], quality='bad', stars=1,
                       review='Mua kháng sinh không đơn cho bé mười tám tháng.', outcome='Bé uống ba hôm, đi ngoài, mà vẫn sốt.',
                       perspectives=[dict(who='Dược sĩ', emoji='💊', text='Không có đơn thì chúng tôi không bán kháng sinh.'),
                                     dict(who='Bé Cốm', emoji='👶', text='(Quấy khóc cả đêm.)')]),
                  dict(id='leftover', label='Lấy nửa vỉ kháng sinh còn thừa lần trước cho bé uống', quality='bad', stars=1,
                       review='Cho bé uống thuốc thừa lần trước, không hỏi ai.', outcome='Thuốc đã hết hạn. Chị Thảo về thấy vỏ vỉ, tái mặt.',
                       perspectives=[dict(who='Chị Thảo', emoji='😨', text='Chị đâu có bảo dùng thuốc cũ.'),
                                     dict(who='Bác sĩ', emoji='🩺', text='Thuốc thừa, quá hạn, không đúng liều: đừng bao giờ.')])],
         lesson='Kháng sinh phải có bác sĩ kê; sốt nhẹ thì hạ sốt, theo dõi, đưa đi khám.'),
    dict(id='NT-S06', title='Hàng xóm gửi chìa khóa', npc=5, tone='gentle', min_day=2,
         opening='Bà Tư đưa chùm chìa khóa: “Bà về quê ba hôm, cháu giữ giúp, thỉnh thoảng sang tưới cây. Tiện thì xem giúp két sắt có khóa chưa.”',
         facts=[dict(id='boss', title='Chủ nhà', source='Chị Thảo', text='Chị Thảo dặn: giờ làm là của nhà chị, việc ngoài thì báo chị trước.'),
                dict(id='safe', title='Két sắt', source='Bà Tư', text='Nhà bà Tư có két, bà hay nghi người khác lấy đồ.'),
                dict(id='plant', title='Cây nhà bà Tư', source='Ban công', text='Cây nhà bà Tư chỉ cần tưới hai ngày một lần.')],
         options=[dict(id='ok_rules', label='Hỏi chị Thảo trước; nếu nhận thì chỉ tưới cây, không đụng tới két, hẹn bà về giao lại chìa trước mặt người khác', requires=['boss', 'safe'], quality='good', stars=5,
                       review='Cháu giữ chìa khóa cẩn thận, không động vào gì ngoài cây.', outcome='Ba hôm sau bà Tư về, cây xanh tốt, két còn nguyên. Bà Tư thôi nghi ngờ.',
                       perspectives=[dict(who='Bà Tư', emoji='👵', text='Con bé này được.'),
                                     dict(who='Chị Thảo', emoji='👩', text='Em hỏi chị trước là chị yên tâm.')]),
                  dict(id='safe', label='Nhận luôn, tiện xem giúp két sắt', quality='bad', stars=2,
                       review='Nhờ tưới cây mà người ta mở cả két sắt nhà tôi.', outcome='Bà Tư về thấy két bị xê dịch, nghi ngờ đủ điều.',
                       perspectives=[dict(who='Bà Tư', emoji='😒', text='Tôi nhờ xem thôi chứ ai bảo mở.'),
                                     dict(who='Chị Thảo', emoji='😕', text='Việc nhà người ta, đụng vào là rắc rối.')]),
                  dict(id='no', label='Từ chối khéo: cháu bận việc nhà chị Thảo', requires=['boss'], quality='ok', stars=4, review='Không giúp được thì thôi.',
                       outcome='Bà Tư gửi chìa cho tổ trưởng dân phố.',
                       perspectives=[dict(who='Bà Tư', emoji='🙂', text='Thôi bà nhờ người khác.'),
                                     dict(who='Chị Thảo', emoji='👩', text='Em biết giữ mình là tốt.')])],
         lesson='Giữ chìa khóa nhà người khác: báo chủ nhà mình, chỉ làm đúng việc được nhờ, giao nhận rõ ràng.'),
]

# Twists: chị Thảo pays late at the end of a job (the player waits, or asks politely now).
LATE_LINES = (
    '“Chị chưa rút tiền, cuối tuần chị gửi cả thể nhé.”',
    '“Ví chị để ở cơ quan rồi, mai chị chuyển khoản.”',
    '“Tháng này nhà chị nhiều khoản quá, em đợi chị mấy hôm.”',
)
CHASE_LINES = {
    'paid': ('{who}: “Ừ chị quên mất, chị gửi đủ đây.”', '{who} chuyển khoản luôn: “Xin lỗi em, bận quá chị quên.”'),
    'part': ('{who}: “Chị gửi trước một nửa nhé, còn lại cuối tuần.”', '{who} dúi mấy tờ: “Cầm tạm nhé em, chị đang kẹt.”'),
    'later': ('{who}: “Mai, mai chị gửi, chị nhớ mà.”', '{who}: “Cuối tháng có lương là chị gửi luôn.”'),
    'deny': ('{who}: “Ơ chị gửi rồi mà? Em xem lại xem.”', '{who}: “Khoản đấy chị trả rồi chứ nhỉ?”'),
    'angry': ('{who}: “Có mấy đồng mà đòi như đòi nợ thế à?”', '{who} gắt: “Nhà chị có quỵt của ai bao giờ đâu!”'),
}
