"""👗 Tiệm Áo Chỉ Mây ở nước ngoài: the clothes shop in 🌏 Làm việc ở nước ngoài (feedback #306, owner OK 09/10).

"trong cái đi nước ngoài xuất khẩu lao động không có shop quần áo": only hired jobs could go abroad, and the clothes
shop is not a hired job. Now Chị Vy sends you to a partner shop in one of the four cities abroad (game/abroad.py
DESTS) once you have served SERVED_NEED customers at home. It is the same shop game (game/careers/clothing.py), with
the city's own customers:

* sizes in the local system: Korean 55/66/77 and 90/95/100, Japanese 7号/9号 and M/L/LL/3L (men's run one smaller),
  French EU 36/38 and 46/48, Australian AU 8/10 and chest inches; shoes in mm, cm, EU or AU; kids by Korean age
  (one year older), height or AU size. A 📏 chart sits on the counter; the rack keeps the shop's own labels;
* a local habit (ask) on most counter customers, answered before the bill: "service" in Seoul, the fitting room face
  cover and the change on a tray in Osaka, "Bonjour" first and no plastic bags in Lyon, sun safety and "change of
  mind" in Melbourne… Each answer is good, ok or bad; 'mood' answers depend on the customer's hidden temper (seeded
  by the task id). A bad answer is a slip like any other (consequences.slip): stars and reviews follow;
* local names, a greeting, the city's addresses for the online orders.

Task generation does not change (scripts/check_task_compat.py): the dressing is task state, rolled once when the
customer walks in (clothing.on_task), like the wishes. t['abroad'] = {to, ask, ans, ok} (to: destination id; ask: the
habit id or None; ans: the option chosen or None; ok: 'good' | 'ok' | 'bad' | None). Everything the page shows is
computed from it at projection time (public_task). An older build keeps the key and ignores it.

The contract is journey['abroad']['work'] as for a hired job, with career 'clothing', emp None, hd 0 and fee 0 (Chị
Vy pays the ticket, so a rollback that ends the contract costs no money). A worked day (at least one customer served)
pays a commission of `pct` % of the day's counter sales into the shop fund, counts the day and brings a line from the
city and a letter from home; the last one brings you home.
"""
from __future__ import annotations

from . import abroad_content as AC

CAREER = 'clothing'
SERVED_NEED = 12              # customers served at home before Chị Vy sends you (the shop's "Phòng thử có rèm" look)
ASK_CHANCE = 0.75             # counter customers with a local habit
KINDS = ('fit', 'outfit', 'room', 'return', 'online', 'alter')   # customers from the city (sale/display: the branch manager)
ASK_KINDS = ('fit', 'outfit')
GRADES = ('good', 'ok', 'bad')
PATIENCE = dict(good=5, bad=-8)
MALE = (2,)                   # clothing.TUAN: the student

# ---------------------------------------------------------------- the four partner shops
SHOPS = {
    'han_quoc': dict(name='Chỉ Mây Seoul', area='Hongdae', days=4, pct=20, style='Oversize, màu trung tính, đồ đôi',
                     hi='Annyeong haseyo!', address=('Mapo-gu, Seoul', 'Ký túc xá Sinchon, phòng 508', 'Gangnam-gu, tầng 12'),
                     names=('Chị Ji-eun', 'Chị Seo-yeon', 'Min-jun', 'Chị Hye-jin', 'Bà Park', 'Cô Kim', 'Chị Yuna', 'Bà Choi'),
                     lines=('Hongdae tối nào cũng có nhóm nhảy ngay trước tiệm.',
                            'Chị Ji-eun dạy bạn gấp áo kiểu Hàn: vuông như hộp quà.',
                            'Khách trẻ chụp ảnh ở gương lớn nhiều hơn mua.',
                            'Tan ca, cả tiệm đi ăn gà rán, uống trà lúa mạch.')),
    'nhat_ban': dict(name='Chỉ Mây Osaka', area='Shinsaibashi', days=5, pct=25, style='Gọn gàng, kín đáo, gói quà thật kỹ',
                     hi='Irasshaimase!', address=('Namba, Osaka', 'Tenma, Osaka', 'Umeda, tầng 7')),
    'phap': dict(name='Chỉ Mây Lyon', area='Presqu’île', days=5, pct=25, style='Thanh lịch, chất liệu tự nhiên',
                 hi='Bonjour !', address=('Croix-Rousse, Lyon', 'Rue de la République, Lyon', 'Vieux Lyon, tầng 3')),
    'uc': dict(name='Chỉ Mây Melbourne', area='Fitzroy', days=6, pct=30, style='Thoải mái, chống nắng, mặc nhiều lớp',
               hi='G’day!', address=('Fitzroy, Melbourne', 'St Kilda, Melbourne', 'Footscray, Melbourne')),
}
SHOPS['nhat_ban'].update(
    names=('Chị Aoi', 'Chị Sato', 'Haruto', 'Chị Yumi', 'Bà Tanaka', 'Cô Nakamura', 'Chị Rina', 'Bà Mori'),
    lines=('Sáng nào cả tiệm cũng cúi chào khách đầu tiên thật sâu.',
           'Chị Aoi gói một món quà mất đúng 40 giây, không thừa băng keo.',
           'Trưa ăn takoyaki ở Dōtonbori, nóng bỏng lưỡi.',
           'Khách xếp hàng ngay ngắn trước phòng thử, không ai chen.',
           'Tối về ký túc xá, bạn ghi sổ: “9号 = M, LL = L”.'))
SHOPS['phap'].update(
    names=('Chị Camille', 'Chị Claire', 'Lucas', 'Chị Amélie', 'Bà Dubois', 'Cô Martine', 'Chị Inès', 'Bà Hélène'),
    lines=('Khách nào bước vào cũng chờ một câu “Bonjour” trước.',
           'Chị Camille sờ vải là biết lanh hay cotton.',
           'Trưa ăn bánh mì kẹp bên bờ sông Saône.',
           'Một bà cụ thử sáu cái khăn rồi kể chuyện Paris năm xưa.',
           'Chợ phiên chủ nhật, bạn mua một hũ mứt làm quà.'))
SHOPS['uc'].update(
    names=('Chị Chloe', 'Chị Emma', 'Jack', 'Chị Olivia', 'Bà Margaret', 'Cô Bev', 'Chị Mia', 'Bà Jean'),
    lines=('Sáng nắng, trưa mưa, chiều gió: khách hỏi áo khoác liên tục.',
           'Đồng nghiệp gọi bạn là “mate”, ai cũng xuề xòa.',
           'Giờ nghỉ, ly flat white ngon nhất đời.',
           'Khách đi chân đất từ biển vào thử đồ, chị Chloe cười: “Bình thường thôi.”',
           'Cuối tuần ra St Kilda ngắm chim cánh cụt về tổ.',
           'Tối gọi video về hẻm, Bà Tám hỏi “bên đó mặc size gì?”'))

# ---------------------------------------------------------------- 📏 sizes: shop label → what the customer says
# Tops and dresses (S/M/L/XL), by the customer: women, men.
TOP = {
    'han_quoc': (dict(S='55', M='66', L='77', XL='88'), dict(S='90', M='95', L='100', XL='105')),
    'nhat_ban': (dict(S='7号', M='9号', L='11号', XL='13号'), dict(S='M', M='L', L='LL', XL='3L')),
    'phap': (dict(S='EU 36', M='EU 38', L='EU 40', XL='EU 42'), dict(S='EU 46', M='EU 48', L='EU 50', XL='EU 52')),
    'uc': (dict(S='AU 8', M='AU 10', L='AU 12', XL='AU 14'), dict(S='ngực 36 inch', M='ngực 38 inch', L='ngực 40 inch', XL='ngực 42 inch')),
}
WAIST = {   # jeans, trousers: 28..32 (the shop's inch labels)
    'han_quoc': {s: f'{s} inch' for s in ('28', '29', '30', '31', '32')},
    'nhat_ban': {'28': '71 cm', '29': '74 cm', '30': '76 cm', '31': '79 cm', '32': '81 cm'},
    'phap': {'28': 'FR 36', '29': 'FR 38', '30': 'FR 40', '31': 'FR 42', '32': 'FR 44'},
    'uc': {'28': 'AU 8', '29': 'AU 10', '30': 'AU 12', '31': 'AU 14', '32': 'AU 16'},
}
FEET = {    # shoes: EU 35..41 on the box
    'han_quoc': {'35': '225 mm', '36': '230 mm', '37': '235 mm', '38': '240 mm', '39': '245 mm', '40': '250 mm', '41': '255 mm'},
    'nhat_ban': {'35': '22.5 cm', '36': '23 cm', '37': '23.5 cm', '38': '24 cm', '39': '24.5 cm', '40': '25 cm', '41': '25.5 cm'},
    'phap': {s: f'EU {s}' for s in ('35', '36', '37', '38', '39', '40', '41')},
    'uc': {'35': 'AU 4', '36': 'AU 5', '37': 'AU 6', '38': 'AU 7', '39': 'AU 8', '40': 'AU 9', '41': 'AU 10'},
}
KIDS_H = {'3T': 100, '5T': 110, '7T': 120, '9T': 130}   # Osaka: the child's height
TOLD = {'han_quoc': ('waist',), 'phap': ('foot',)}       # the local word is the label itself: the counter flags a mismatch
CHART_NOTE = {'han_quoc': 'Tuổi Hàn = tuổi thật + 1.', 'nhat_ban': 'Áo nam Nhật nhỏ hơn 1 size: LL = L.',
              'phap': 'Giày ghi EU như hộp.', 'uc': 'Áo nam đo vòng ngực.'}


def _letters(item: str, sizes) -> bool:
    return all(z in ('S', 'M', 'L', 'XL') for z in sizes)


def local_size(to: str, item: str, size: str, npc: int, rng) -> tuple[str, str, str | None]:
    """(what the customer says, the order card's short note, the label they named or None) for a shop size."""
    from .careers import clothing as K
    male = npc in MALE
    if item in K.WAIST_ITEMS:
        w = WAIST[to][size]
        told = size if 'waist' in TOLD.get(to, ()) else None
        if w[-1].isalpha() and w[0].isdigit():   # a measure: 29 inch, 74 cm
            return f'Eo mình {w}.', f'eo {w}', told
        return f'Quần mình mặc {w}.', f'quần {w}', told
    if item in K.SHOES:
        f = FEET[to][size]
        return f'Chân mình {f}.', f'chân {f}', size if 'foot' in TOLD.get(to, ()) else None
    if K.SIZES[item] == ('F',) or item in ('hat', 'belt', 'socks'):
        return 'Loại free size.', 'free size', None
    if item == 'kids':
        lo, hi = K.KIDS_AGE[size]
        age = rng.choice((lo, hi))
        if to == 'han_quoc':
            return f'Cho bé {age + 1} tuổi Hàn.', f'bé {age + 1} tuổi Hàn', None
        if to == 'nhat_ban':
            return f'Bé cao {KIDS_H[size]} cm.', f'bé cao {KIDS_H[size]} cm', None
        if to == 'phap':
            return f'Cho bé {age} ans ({age} tuổi).', f'bé {age} tuổi', None
        return f'Kids size {size[:-1]}.', f'kids {size[:-1]}', None
    if _letters(item, K.SIZES[item]):
        k = TOP[to][1 if male else 0][size]
        return f'Mình mặc {k}.', k, None
    return f'Mình mặc size {size}.', f'size {size}', size


def chart(to: str, keys=('women', 'men', 'waist', 'feet', 'kids')) -> list:
    """The 📏 card on the counter: the rows `keys` asks for, each {label, cells: [[shop label, local], ...]}."""
    w, m = TOP[to]
    rows = dict(women=['👚 Nữ', [[k, v] for k, v in w.items()]], men=['👔 Nam', [[k, v] for k, v in m.items()]],
                waist=['👖 Quần', [[k, v] for k, v in WAIST[to].items()]], feet=['👟 Giày', [[k, v] for k, v in FEET[to].items()]])
    if to == 'nhat_ban':
        rows['kids'] = ['🧒 Bé', [[k, f'{v} cm'] for k, v in KIDS_H.items()]]
    elif to == 'uc':
        rows['kids'] = ['🧒 Bé', [[k, k[:-1]] for k in KIDS_H]]
    elif to == 'han_quoc':
        rows['kids'] = ['🧒 Bé', [[k, f'{a + 1}–{b + 1} tuổi Hàn'] for k, (a, b) in _kids_age().items()]]
    return [dict(label=rows[k][0], cells=rows[k][1]) for k in keys if k in rows]


def _kids_age() -> dict:
    from .careers import clothing as K
    return K.KIDS_AGE


def chart_keys(t: dict) -> tuple:
    """The chart rows a task needs: the kinds of goods the customer asks for (fit), a top and trousers (outfit)."""
    from .careers import clothing as K
    top = 'men' if K._npc_index(t) in MALE else 'women'
    if t.get('kind') == 'outfit':
        return (top, 'waist')
    keys = []
    for ln in (t.get('needs') or {}).get('lines') or ():
        item = ln.get('item')
        k = ('waist' if item in K.WAIST_ITEMS else 'feet' if item in K.SHOES else 'kids' if item == 'kids'
             else top if item in K.SIZES and _letters(item, K.SIZES[item]) else None)
        if k and k not in keys:
            keys.append(k)
    return tuple(keys)


NOTE_FOR = {'han_quoc': 'kids', 'nhat_ban': 'men', 'phap': 'feet', 'uc': 'men'}   # the row CHART_NOTE explains


# ---------------------------------------------------------------- the occasions, the city's way
OCCASION_OPEN = {
    'han_quoc': dict(wedding='Cuối tuần mình đi đám cưới đồng nghiệp ở Gangnam, chọn giúp một bộ lịch sự.',
                     interview='Mai mình phỏng vấn công ty lớn, cần bộ thật chỉn chu.',
                     beach='Cuối tuần đi biển Busan, phối giúp bộ mát mà vẫn xinh.',
                     tet='Seollal này về quê ngoại chúc Tết, cần bộ thật tươi.'),
    'nhat_ban': dict(wedding='Mình được mời dự tiệc cưới, phải thật trang nhã.',
                     interview='Mình đi phỏng vấn ở Umeda, cần bộ gọn gàng, kín đáo.',
                     beach='Hè này đi biển Shirahama, chọn giúp bộ mát.',
                     tet='Đầu năm đi lễ đền, cần bộ thật tươi.'),
    'phap': dict(wedding='Em gái mình cưới ở vùng nho Beaujolais, cần bộ thanh lịch.',
                 interview='Mình phỏng vấn ở một văn phòng luật, cần bộ thật chuẩn.',
                 beach='Tuần sau mình đi biển Nice, chọn giúp bộ nhẹ nhàng.',
                 tet='Hội Tết của người Việt ở Lyon, mình muốn mặc thật tươi.'),
    'uc': dict(wedding='Bạn mình cưới ở vườn nho Yarra Valley, chọn giúp một bộ nha.',
               interview='Mai mình phỏng vấn ở khu CBD, cần bộ thật “smart”.',
               beach='Cuối tuần đi biển St Kilda, phối giúp bộ mát.',
               tet='Lễ hội Tết ở Footscray, mình muốn diện thật tươi.'),
}


# ---------------------------------------------------------------- the city's habits (asks)
def _a(aid, say, *opts):
    return dict(id=aid, say=say, opts=tuple(dict(id=o[0], label=o[1], grade=o[2], reply=o[3]) for o in opts))


# grade 'mood': the customer's hidden temper decides; its reply is (calm, cross).
ASKS = {
    'han_quoc': (
        _a('service', 'Unnie, cho em xin “service” (quà kèm) đi, mua nhiều vậy mà!',
           ('pin', '🎁 Tặng kẹp tóc nhỏ', 'good', 'Khách reo “Daebak!”, hứa quay lại.'),
           ('cut', '🏷️ Giảm luôn 20%', 'bad', 'Chị Ji-eun nhíu mày: giảm vậy là lỗ.'),
           ('no', '🙅 “Không có ạ”', 'mood', ('Khách cười xòa, vẫn mua.', 'Khách phụng phịu: “Tiệm gì kỳ.”'))),
        _a('kakao', 'Đợi mình chụp gửi bạn qua Kakao hỏi ý đã nha…',
           ('mirror', '🪞 Mời ra gương lớn có đèn', 'good', 'Ảnh lung linh, bạn khách thả tim liền.'),
           ('wait', '⏳ Đứng chờ', 'ok', 'Chờ hơi lâu nhưng khách vui.'),
           ('rush', '⏩ Giục khách chốt', 'bad', 'Khách khó chịu: “Gấp gì dữ vậy.”')),
        _a('couple', 'Có áo đôi không? Mình muốn mua y vậy cho bạn trai.',
           ('ask', '👫 Hỏi size bạn trai, cùng màu', 'good', 'Khách nhắn bạn trai hỏi size, hẹn mai ghé lấy.'),
           ('guess', '🎲 Lấy đại size L', 'bad', 'Về bạn trai mặc không vừa, khách nhắn trách.'),
           ('no', '“Tiệm không bán đồ đôi”', 'ok', 'Khách hơi tiếc.')),
        _a('quick', 'Giao trong ngày tới nhà mình được không? Mình còn đi cà phê.',
           ('honest', '📦 Báo thật: mai giao, gửi mã đơn', 'good', 'Khách gật: “Rõ ràng vậy là được.”'),
           ('promise', '“Được ạ!” (hứa đại)', 'bad', 'Tối khách chờ hoài, nhắn trách.'),
           ('carry', '🛍️ Gói gọn để khách xách đi', 'ok', 'Khách xách đi luôn.')),
        _a('colors', 'Cho mình thử hết các màu nha!',
           ('yes', '🙆 Mời thử, treo lại ngay', 'good', 'Khách thử xong còn gấp giúp một cái.'),
           ('two', '✌️ Chỉ cho thử hai màu', 'mood', ('Khách hiểu, chọn nhanh.', 'Khách bĩu môi: “Keo ghê.”')),
           ('no', '🙅 Không cho thử', 'bad', 'Khách bỏ dở, suýt không mua.')),
    ),
    'nhat_ban': (
        _a('face', 'Sumimasen… phòng thử có khăn che mặt không ạ?',
           ('cover', '😷 Đưa khăn che mặt mới', 'good', 'Khách cúi chào cảm ơn, áo sạch tinh.'),
           ('none', '“Không cần đâu ạ”', 'bad', 'Áo dính vệt son, phải đem giặt.'),
           ('skip', '🙅 Khuyên khỏi thử', 'mood', ('Khách gật, mua luôn.', 'Khách ngại, lưỡng lự mãi.'))),
        _a('wrap', 'Làm quà nên gói riêng từng món, thêm túi giấy dự phòng nha.',
           ('each', '🎁 Gói riêng + túi dự phòng', 'good', 'Khách cúi chào thật sâu.'),
           ('one', '🛍️ Gói chung một túi', 'bad', 'Khách lịch sự, nhưng thất vọng thấy rõ.'),
           ('bow', '🎀 Dán nơ lên túi thôi', 'ok', 'Tạm được.')),
        _a('taxfree', 'Mình là khách du lịch, mua miễn thuế được không?',
           ('passport', '🛂 Xem hộ chiếu, làm giấy, niêm túi', 'good', 'Đúng thủ tục, khách yên tâm.'),
           ('skip', '✂️ Bỏ thuế luôn, khỏi giấy', 'bad', 'Sai thủ tục, tiệm bị nhắc nhở.'),
           ('no', '“Tiệm không làm ạ”', 'ok', 'Khách vẫn mua, hơi tiếc.')),
        _a('chotto', 'Ưm… chotto… (để mình nghĩ thêm)',
           ('hold', '🙇 “Em giữ món này tới chiều ạ”', 'good', 'Khách nhẹ nhõm, chốt luôn.'),
           ('push', '💬 Nài: “Đẹp lắm, mua đi!”', 'bad', 'Khách ngại, lần sau chắc không ghé.'),
           ('wait', '⏳ Im lặng chờ', 'mood', ('Khách nghĩ xong, mua.', 'Khách bối rối mãi.'))),
        _a('tray', 'Tiền thối đặt lên khay giùm mình nha.',
           ('tray', '🙌 Đặt khay, hai tay, cúi chào', 'good', 'Khách mỉm cười cúi chào lại.'),
           ('hand', '✋ Dúi vào tay', 'bad', 'Khách hơi giật mình.'),
           ('desk', 'Để lên quầy', 'ok', 'Khách tự nhặt.')),
        _a('point', 'Có thẻ tích điểm không ạ?',
           ('card', '💳 Làm thẻ, đóng dấu điểm', 'good', 'Khách cất thẻ cẩn thận vào ví.'),
           ('no', '“Không có ạ”', 'ok', 'Khách gật nhẹ.'),
           ('later', '“Lần sau nha”', 'mood', ('Khách cười: “Hai, lần sau.”', 'Khách hơi phật ý.'))),
    ),
    'phap': (
        _a('bonjour', 'Khách đứng nhìn bạn, chờ… chưa ai nói “Bonjour”.',
           ('bonjour', '👋 “Bonjour madame !”', 'good', 'Khách mỉm cười, mở lời ngay.'),
           ('size', '📏 Hỏi luôn: “Size gì ạ?”', 'bad', 'Khách lạnh nhạt: “Bonjour d’abord.”'),
           ('smile', '🙂 Chỉ mỉm cười', 'mood', ('Khách cười lại.', 'Khách nhướng mày khó chịu.'))),
        _a('fabric', '“C’est quelle matière ?” Vải gì vậy em?',
           ('tag', '🏷️ Lật tem vải, đọc đúng', 'good', 'Khách gật gù: “Parfait.”'),
           ('guess', '🎲 “Cotton chắc vậy”', 'bad', 'Hóa ra polyester, khách phật ý.'),
           ('ask', '“Để em hỏi lại”', 'ok', 'Khách chờ được.')),
        _a('soldes', 'Sao chưa sale? Giảm cho mình 30% đi.',
           ('explain', '📅 Chưa tới mùa soldes, hẹn ngày', 'good', 'Khách ghi lịch, vẫn mua hôm nay.'),
           ('give', '🏷️ Giảm luôn 30%', 'bad', 'Chị Camille nhắc: sale ngoài mùa là sai luật.'),
           ('no', '“Non.”', 'mood', ('Khách nhún vai, vẫn mua.', 'Khách hừ một tiếng.'))),
        _a('slow', 'Khách thong thả thử từng món, kể chuyện Paris năm xưa…',
           ('listen', '☕ Kiên nhẫn nghe, tư vấn', 'good', 'Khách quý bạn ra mặt.'),
           ('rush', '⏩ Nhắc khách nhanh lên', 'bad', 'Khách nghiêm mặt: “Ở đây không ai vội.”'),
           ('leave', 'Để khách tự xem', 'ok', 'Khách tự xem, cũng được.')),
        _a('bag', 'Không lấy túi nilon nha, có túi giấy không?',
           ('paper', '🛍️ Túi giấy', 'good', 'Khách gật: “Merci.”'),
           ('plastic', 'Túi nilon cho chắc', 'bad', 'Khách nhíu mày: “Ở đây bỏ túi nilon lâu rồi.”'),
           ('none', 'Khỏi túi, khách tự cầm', 'ok', 'Khách cầm tay về.')),
    ),
    'uc': (
        _a('change', '“Change of mind” trả lại được không bạn?',
           ('policy', '📜 Còn tem + hóa đơn, trong 7 ngày', 'good', 'Khách gật: “Fair enough.”'),
           ('yes', '“Thoải mái luôn!”', 'bad', 'Hứa quá chính sách, mai khách đem đồ mặc rồi tới trả.'),
           ('no', '“Không trả được đâu”', 'mood', ('Khách nhún vai: “No worries.”', 'Khách cau mày: “Strict!”'))),
        _a('upf', 'Áo này chống nắng UPF 50+ không? Nắng ở đây rát lắm.',
           ('honest', '☀️ Nói thật, gợi ý nón + áo tay dài', 'good', 'Khách cảm ơn vì nói thật.'),
           ('lie', '“Có chứ!”', 'bad', 'Đi biển về cháy nắng, khách quay lại trách.'),
           ('check', '🏷️ Xem tem rồi trả lời', 'ok', 'Tem không ghi, khách tự liệu.')),
        _a('layer', 'Melbourne một ngày bốn mùa, mặc vậy có lạnh không?',
           ('jacket', '🧥 Gợi ý thêm áo khoác mỏng', 'good', 'Khách gật: “Good call.”'),
           ('fine', '“Không sao đâu”', 'mood', ('Hôm đó trời ấm, khách vui.', 'Chiều trở gió, khách lạnh run.')),
           ('skip', 'Không trả lời', 'bad', 'Khách hỏi lại hai lần mới có người nghe.')),
        _a('bigger', 'Có size lớn hơn không? Mình mặc AU 16.',
           ('order', '📋 Kiểm kho, hẹn đặt về', 'good', 'Khách để lại số, vui vẻ.'),
           ('rude', '“Chắc khó tìm cho chị”', 'bad', 'Khách buồn ra mặt.'),
           ('no', '“Hết rồi ạ”', 'ok', 'Khách tiếc.')),
        _a('mate', '“How ya going, mate?” Khách hỏi bạn khỏe không, quê đâu…',
           ('chat', '😄 Vui vẻ nói vài câu', 'good', 'Khách: “Vietnam! Love phở!”'),
           ('short', 'Trả lời cụt, quay đi', 'bad', 'Khách ngượng: “Okay then…”'),
           ('work', '🙂 Cười rồi làm tiếp', 'ok', 'Khách cười lại.')),
    ),
}
ASK_INDEX = {to: {a['id']: a for a in rows} for to, rows in ASKS.items()}
GRADE_SCORE = dict(good=5, ok=4, bad=2)


# ---------------------------------------------------------------- reading a task
def get(t: dict) -> dict | None:
    a = t.get('abroad') if isinstance(t, dict) else None
    return a if isinstance(a, dict) and a.get('to') in SHOPS else None


def name(t: dict, npc: int) -> str | None:
    """The city's name for the shop's person `npc` on a dressed task (None at home)."""
    a = get(t)
    return SHOPS[a['to']]['names'][npc] if a and 0 <= npc < len(SHOPS[a['to']]['names']) else None


def ask_of(t: dict) -> dict | None:
    a = get(t)
    return ASK_INDEX[a['to']].get(a.get('ask')) if a and a.get('ask') else None


def pending(t: dict) -> bool:
    """A habit still waiting for an answer (the bill waits for it)."""
    a = get(t)
    return bool(a and a.get('ask') and a.get('ans') is None)


# ---------------------------------------------------------------- dressing (clothing.on_task / on_start)
def dress(s: dict, t: dict, to: str) -> None:
    """Roll the city's customer for a task that just walked in (deterministic by the task id)."""
    from .careers import kit
    if t.get('kind') not in KINDS or 'abroad' in t:
        return
    ask = None
    if t['kind'] in ASK_KINDS:
        rng = kit.rng(CAREER, 'abroad', to, t['id'])
        if rng.random() < ASK_CHANCE:
            ask = rng.choice(ASKS[to])['id']
    t['abroad'] = dict(to=to, ask=ask, ans=None, ok=None)


def answer(s: dict, c: dict, t: dict, p: dict) -> dict:
    """ao_local {task, answer}: how you meet the customer's habit."""
    from .careers import kit
    from . import consequences as cq
    a, q = get(t), ask_of(t)
    kit.need(q is not None and a['ans'] is None and t['stage'] in ('pick', 'pay'), 'Khách không hỏi gì thêm.')
    opt = next((o for o in q['opts'] if o['id'] == p.get('answer')), None)
    kit.need(opt is not None, 'Chọn một cách trả lời nhé.')
    grade, reply = opt['grade'], opt['reply']
    if grade == 'mood':   # hidden: the customer's temper today
        calm = kit.rng(CAREER, 'temper', t['id']).random() < 0.5
        grade, reply = ('ok', reply[0]) if calm else ('bad', reply[1])
    a['ans'], a['ok'] = opt['id'], grade
    if grade == 'good':
        t['patience'] = min(100, t.get('patience', 100) + PATIENCE['good'])
    elif grade == 'bad':
        t['mistakes'] += 1
        t['patience'] = max(25, t.get('patience', 100) + PATIENCE['bad'])
        cq.slip(t, 'local_miss', 1, reply, 'chưa hiểu thói quen khách địa phương')
    head = {'good': '✅', 'ok': '🙂', 'bad': '😬'}[grade]
    return dict(message=f'{head} {reply}', local=grade)


# ---------------------------------------------------------------- projection (clothing.public_task)
def project(t: dict, v: dict) -> None:
    """What the page shows for a dressed task: names, greeting, local sizes, the habit. Never the hidden temper."""
    from .careers import clothing as K, kit
    a = get(t)
    if not a:
        return
    to, sh, d = a['to'], SHOPS[a['to']], next(x for x in AC.DESTS if x['id'] == a['to'])
    npc = K._npc_index(t)
    keys = chart_keys(t) if t['known'] else ()
    view = dict(to=to, flag=d['flag'], city=d['city'], shop=sh['name'], who=sh['names'][npc],
                names={kit.npc_id(CAREER, i): n for i, n in enumerate(sh['names'])}, chart=chart(to, keys),
                chart_note=CHART_NOTE[to] if NOTE_FOR[to] in keys else '')
    hi = '' if a.get('ask') == 'bonjour' else sh['hi'] + ' '   # Lyon's habit: they wait for *your* Bonjour
    if t['kind'] == 'outfit':
        v['opening'] = f'{hi}{OCCASION_OPEN[to][t["needs"]["occasion"]]}'
    elif npc != K.VY:
        v['opening'] = f'{hi}{t["opening"]}'
    if (t['day'], int(t['id'].rsplit('-', 1)[1])) in K.STORY:
        v['title'] = K.KIND_NAMES[t['kind']]
    q = ask_of(t)
    if q:
        opts = [dict(id=o['id'], label=o['label']) for o in q['opts']]
        kit.rng(CAREER, 'opts', t['id']).shuffle(opts)   # the good answer is not always the first button
        view['ask'] = dict(id=q['id'], say=q['say'], ans=a['ans'], ok=a['ok'], opts=opts,
                           reply=next((o['reply'] if o['grade'] != 'mood' else None for o in q['opts'] if o['id'] == a['ans']), None))
    v['abroad'] = view
    n = v.get('needs')
    if not isinstance(n, dict):
        return
    if t['kind'] == 'fit':
        lines = []
        for i, (ln, raw) in enumerate(zip(n.get('lines') or (), t['needs']['lines'])):
            said, ask, told = local_size(to, raw['item'], raw['_size'], npc, kit.rng(CAREER, 'size', t['id'], i))
            lines.append(dict(ln, say=f'{K.ITEM[raw["item"]]["name"]} màu {raw["colour"]}. {said}', ask=ask, told=told))
        n['lines'] = lines
        n['note'] = ' '.join(x['say'] for x in lines)
    elif t['kind'] == 'outfit':
        o = K.OCCASIONS[n['occasion']]
        top = local_size(to, 'tee', n['top'], npc, None)[1]
        waist = local_size(to, 'jeans', n['waist'], npc, None)[1]
        n['note'] = f'{o["emoji"]} {o["name"]} · ngân sách {n["budget"]} xu · áo {top} · {waist}.'
    elif t['kind'] == 'online':
        addr = sh['address'][kit.rng(CAREER, 'addr', t['id']).randrange(len(sh['address']))]
        n['address'] = addr
        n['note'] = ('Đã chuyển khoản trước.' if n.get('pay') == 'paid' else 'Thu hộ (COD) khi giao.') + f' Giao tới: {addr}.'


def request(t: dict) -> str | None:
    """clothing.known_request for a dressed fit / outfit customer (the "Nghe khách" line)."""
    from .careers import kit
    a = get(t)
    if not a or t['kind'] not in ('fit', 'outfit', 'online'):
        return None
    from .jsoncopy import strip_copy
    v = dict(needs=strip_copy(t['needs']), opening=t['opening'])
    project(t, v)
    if t['kind'] == 'online':
        from .careers import clothing as K
        return 'Đơn: ' + ', '.join(f'{K.ITEM[x["item"]]["name"]} {K._sz(x["size"])} màu {x["colour"]}' for x in t['needs']['lines']) + '. ' + v['needs']['note']
    q = ask_of(t)
    return v['needs']['note'] + (f' {q["say"]}' if q else '')


def feedback_row(t: dict) -> dict | None:
    a = get(t)
    if not a or not a.get('ok'):
        return None
    return dict(key='local', label='Hiểu khách địa phương', score=GRADE_SCORE[a['ok']],
                note={'good': 'đúng ý khách', 'ok': 'tạm ổn', 'bad': 'khách phật ý'}[a['ok']])


# ---------------------------------------------------------------- the contract (game/abroad.py)
def why_not(s: dict) -> str | None:
    """Why Chị Vy cannot send you yet, or None."""
    c = (s.get('careers') or {}).get(CAREER)
    j = s.get('journey') or {}
    if not isinstance(c, dict) or CAREER not in (j.get('unlocked') or ()):
        return 'Mở Tiệm Áo Chỉ Mây và đứng tiệm vài ngày trước đã.'
    served = int((c.get('metrics') or {}).get('served', 0))
    if served < SERVED_NEED:
        return f'Phục vụ đủ {SERVED_NEED} khách ở Tiệm Áo Chỉ Mây thì chị Vy mới cử đi (còn {SERVED_NEED - served}).'
    return None


def on_close(s: dict, c: dict, sales: int) -> list[str]:
    """clothing.on_close while on the contract: the commission, the day counted, the city, a letter; the last day home."""
    from . import abroad as ab
    from .careers import kit
    w = ab.contract(s)
    if not w or w['career'] != CAREER or c.get('day_completed', 0) < 1:
        return []
    to, sh = w['to'], SHOPS[w['to']]
    d = next(x for x in AC.DESTS if x['id'] == to)
    lines = []
    bonus = max(0, sales) * w['pct'] // 100
    if bonus > 0:
        kit.money(s, c, bonus, f'🌏 Hoa hồng chi nhánh {d["city"]} (+{w["pct"]}% doanh thu)', None, 'revenue')
        lines.append(f'🌏 Hoa hồng {sh["name"]}: +{bonus} xu ({w["pct"]}% doanh thu hôm nay).')
    w['n'] += 1
    seed = int(s['journey'].get('seed') or 0)
    lines.append(f'{d["flag"]} Ngày {w["n"]}/{w["need"]} ở {d["city"]}: {sh["lines"][(w["n"] - 1) % len(sh["lines"])]}')
    lines.append(f'✉️ {AC.LETTERS[(seed + w["n"] + len(to)) % len(AC.LETTERS)]}')
    if w['n'] >= w['need']:
        b = ab._block(s)
        b['work'] = None
        b['back'] = int(s['journey'].get('life_day') or 1)
        b['done'][to] = min(10 ** 6, int(b['done'].get(to) or 0) + 1)
        lines.append(f'🏠 Hết hợp đồng ở {d["city"]}! Chị Vy gọi video: “Giỏi lắm, về tiệm kể chị nghe khách bên đó mặc size gì nha.”')
    return lines


def catalogue() -> dict:
    return {to: dict(name=sh['name'], area=sh['area'], days=sh['days'], pct=sh['pct'], style=sh['style']) for to, sh in SHOPS.items()}


def validate_task(t: dict) -> None:
    """clothing.validate_task: t['abroad'] (optional)."""
    from .careers import kit
    a = t.get('abroad')
    if a is None:
        return
    kit.need(isinstance(a, dict) and set(a) == {'to', 'ask', 'ans', 'ok'} and a['to'] in SHOPS and t.get('kind') in KINDS, 'Khách ở chi nhánh sai.')
    q = ASK_INDEX[a['to']].get(a['ask']) if a['ask'] is not None else None
    kit.need(a['ask'] is None or (q is not None and t['kind'] in ASK_KINDS), 'Khách ở chi nhánh sai.')
    kit.need(a['ans'] is None or (q is not None and any(o['id'] == a['ans'] for o in q['opts'])), 'Khách ở chi nhánh sai.')
    kit.need((a['ok'] is None) == (a['ans'] is None) and a['ok'] in (None, *GRADES), 'Khách ở chi nhánh sai.')
