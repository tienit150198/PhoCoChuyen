"""💒 Dịch vụ cưới từ người chơi: the services, the couple's choices, the provider's work and its "oái ăm" demands
(game/wed_services.py holds the rules; this file only words, ids and the shared credit query).

Pure data and pure functions (no database, no save): live/wedding.py imports it too, to show the credits in the party.

A provider's job (one per order) is a fixed list of steps rolled once from the order id (game/wed_services.plan_of):
  b1, b2  two craft steps that must follow the couple's brief (the right pick is the brief's value)
  k       one craft-knowledge step (one of KNOW[svc], the right pick is 'a')
  d × 3   three oái ăm demands: the service's CHANGE demand (the brief changes when the provider agrees) and two of
          DEMANDS[svc]; each option is worth 2 (khéo léo), 1 (tạm ổn) or 0 (hỏng việc)
  final   the last check before the ceremony: the right pick is the brief's value NOW (after a change, the new one)
The points add up to at most MAX_SCORE; the stars come from STARS.
"""
from __future__ import annotations

from . import wedding_content as W

# ---------------------------------------------------------------- the services
# key: dict(career, service, icon, name, short (the credit's label), credit (the line at the wedding), desc, unit,
#           qty_max, extra (the NPC extra it stands for in the wedding's mood), brief: [(field, label, [(id, name, emoji)])],
#           change: the brief field the CHANGE demand moves, final: the question of the last check)
MENU_OPTS = [(m['id'], m['name'], '🍽️') for m in W.MENUS]
SVC = {
    'tiec': dict(career='banquet', service='tiec_cuoi', icon='🍽️', name='Tiệc cưới: nấu & phục vụ', short='Tiệc cưới',
                 credit='Tiệc do {n} phục vụ', unit='bàn', qty_max=30, extra=None,
                 desc='Đầu bếp người chơi lên thực đơn, nấu và phục vụ cỗ cưới tận bàn.',
                 brief=[('menu', 'Thực đơn', MENU_OPTS),
                        ('mon', 'Món chính', [('ga', 'Gà hấp lá chanh', '🍗'), ('tom', 'Tôm hấp nước dừa', '🦐'),
                                              ('bo', 'Bò lúc lắc', '🥩'), ('lau', 'Lẩu Thái hải sản', '🍲'), ('xoi', 'Xôi gấc', '🍙')])],
                 change='tables', final='Giờ khai tiệc: dọn bao nhiêu bàn?'),
    'hoa': dict(career='florist', service='hoa_cuoi', icon='💐', name='Hoa cưới: cổng hoa, bàn tiệc, hoa cầm tay', short='Hoa cưới',
                credit='Hoa do {n} cắm', unit='bộ', qty_max=1, extra='flowers',
                desc='Cổng hoa, bàn gia tiên, hoa bàn tiệc và bó hoa cầm tay của cô dâu.',
                brief=[('mau', 'Tông màu', [('hong', 'Hồng phấn', '🩷'), ('trang', 'Trắng tinh khôi', '🤍'), ('do', 'Đỏ rực', '❤️'),
                                            ('tim', 'Tím mộng mơ', '💜'), ('vang', 'Vàng nắng', '💛')]),
                       ('loai', 'Hoa chính', [('hong', 'Hoa hồng', '🌹'), ('cam_tu_cau', 'Cẩm tú cầu', '💠'), ('baby', 'Baby trắng', '🤍'),
                                              ('tulip', 'Tulip', '🌷'), ('ly', 'Hoa ly', '🌸')])],
                change='mau', final='Trước giờ làm lễ, kiểm lần cuối: cổng hoa phải tông màu gì?'),
    'vay': dict(career='clothing', service='vay_cuoi', icon='👰', name='Váy cưới & vest chú rể', short='Váy & vest',
                credit='Váy & vest do {n} chuẩn bị', unit='bộ', qty_max=1, extra='dress',
                desc='Chọn mẫu, sửa số đo, là hơi và mang váy, vest tới tận nhà.',
                brief=[('kieu', 'Váy cô dâu', [('xoe', 'Váy xòe công chúa', '👗'), ('duoi_ca', 'Váy đuôi cá', '🧜'),
                                               ('ao_dai', 'Áo dài cưới đỏ', '🏮'), ('suong', 'Váy suông tối giản', '🤍')]),
                       ('vest', 'Đồ chú rể', [('den', 'Vest đen', '🖤'), ('trang', 'Vest trắng', '🤍'), ('xanh', 'Vest xanh navy', '💙'),
                                              ('ao_dai', 'Áo dài the nam', '🧧')])],
                change='kieu', final='Treo váy lên xe hoa: mẫu nào?'),
    'makeup': dict(career='salon', service='trang_diem_cuoi', icon='💄', name='Trang điểm & làm tóc cô dâu', short='Trang điểm',
                   credit='Trang điểm do {n}', unit='lượt', qty_max=1, extra='makeup',
                   desc='Trang điểm, làm tóc cho cô dâu từ sáng sớm, dặm lại giữa tiệc.',
                   brief=[('style', 'Kiểu trang điểm', [('trong', 'Trong trẻo', '🌸'), ('han', 'Kiểu Hàn', '🫧'), ('sac', 'Sắc sảo', '💋'),
                                                       ('co_dien', 'Cổ điển', '🎞️')]),
                          ('toc', 'Kiểu tóc', [('bui', 'Búi thấp', '🎀'), ('xoan', 'Xoăn lơi', '🌊'), ('tet', 'Tết nửa đầu', '🌾'),
                                               ('thang', 'Xõa thẳng', '💇')])],
                   change='style', final='Chụp ảnh trước giờ rước dâu: lớp trang điểm cuối cùng là kiểu nào?'),
}
ORDER = ('tiec', 'hoa', 'vay', 'makeup')
# 📸 Ảnh cưới: game/photo_studio.py's own 'doi' package (Ảnh đôi · cưới), not a second service
PHOTO = dict(key='anh', icon='📸', short='Ảnh cưới', credit='Ảnh cưới do {n} chụp', pkg='doi', extra='album', career='photobooth')
SERVICES = frozenset(SVC[k]['service'] for k in ORDER)
PAIRS = {(SVC[k]['career'], SVC[k]['service']): k for k in ORDER}

# the florist's colours as the party draws them (bouquet, arch): petals and the ribbon
FLOWER_HEX = dict(hong=('#f6a8bd', '#f28c9e', '#fbe3ea'), trang=('#ffffff', '#f3efe6', '#e9f3e3'), do=('#e0334f', '#ff6f6f', '#b8182e'),
                  tim=('#b18be0', '#9563dc', '#e3d3f6'), vang=('#ffd45e', '#f5b83d', '#fff1b8'))

# ---------------------------------------------------------------- the provider's work
# craft steps that follow the brief (b1 → the brief's first field, b2 → its second)
CRAFT = {
    'tiec': ('🛒 Chợ đầu mối 3 giờ sáng: định lượng mâm theo thực đơn nào?', '🔪 Bếp chính lên món chủ lực: món nào?'),
    'hoa': ('🎨 Phối ruy băng và hoa phụ tông màu nào?', '🌅 Chợ hoa đầu mối 4 giờ sáng: lấy hoa chính nào cho cổng hoa?'),
    'vay': ('📏 Lấy mẫu váy trong kho ra sửa số đo: mẫu nào?', '🤵 Là hơi bộ đồ chú rể: bộ nào?'),
    'makeup': ('🧴 Chuẩn bị bảng màu trang điểm: kiểu nào?', '💇 Uốn, kẹp tóc cô dâu: kiểu nào?'),
}
# one knowledge step per job: (id, question, [(option id, text)], why) — the right option is always 'a' (shown shuffled)
KNOW = {
    'tiec': [
        ('ra_dong', '🦐 Rã đông 20 ký tôm cho tiệc tối mai cách nào?',
         [('a', 'Để ngăn mát qua đêm, nấu trong ngày'), ('b', 'Ngâm nước nóng cho nhanh'), ('c', 'Để ngoài sân cho tự tan')],
         'Rã đông trong ngăn mát giữ tôm tươi, không sinh vi khuẩn.'),
        ('ga_vang', '🍗 Gà luộc xong, giữ da vàng giòn thế nào?',
         [('a', 'Ngâm ngay vào nước đá rồi quét mỡ nghệ'), ('b', 'Để nguội trong nồi nước luộc'), ('c', 'Treo ngoài gió cho khô')],
         'Nước đá làm da săn lại, mỡ nghệ cho màu vàng đẹp.'),
        ('nuoc_lau', '🍲 Nồi nước lẩu cho cả tiệc nấu khi nào?',
         [('a', 'Ninh xương từ sáng, nêm sát giờ khai tiệc'), ('b', 'Nấu từ hôm trước, để ngoài bếp'), ('c', 'Pha gói gia vị lúc khách ngồi')],
         'Nước ninh trong ngày ngọt và an toàn; nêm sát giờ thì vừa miệng.'),
    ],
    'hoa': [
        ('ru_dau', '🌹 Hoa hồng nhập về bị rũ đầu. Làm sao cho tươi lại?',
         [('a', 'Cắt xéo gốc trong nước, ngâm nước mát hai tiếng'), ('b', 'Phơi nắng cho cứng cành'), ('c', 'Xịt nước hoa cho thơm')],
         'Cắt gốc trong nước để không lọt khí vào cuống, hoa hút nước lại.'),
        ('nang_gat', '☀️ Cổng hoa ngoài trời, nắng gắt. Giữ hoa thế nào?',
         [('a', 'Cắm xốp ướt, phun sương, dựng cổng sát giờ'), ('b', 'Dựng từ tối hôm trước cho kịp'), ('c', 'Thay hết bằng hoa giả')],
         'Xốp ướt và phun sương giữ hoa tươi suốt buổi lễ.'),
        ('cuong', '💐 Bó hoa cầm tay của cô dâu: quấn cuống thế nào?',
         [('a', 'Quấn băng keo hoa rồi ruy băng lụa, chừa đầu cuống'), ('b', 'Buộc dây thun là được'), ('c', 'Quấn giấy báo cho chắc')],
         'Băng keo hoa giữ dáng bó, ruy băng lụa cho cô dâu cầm êm tay.'),
    ],
    'vay': [
        ('so_do', '📏 Đo số đo cô dâu khi nào chuẩn nhất?',
         [('a', 'Đo lại một tuần trước cưới, mặc đúng đồ lót hôm cưới'), ('b', 'Dùng số đo ba tháng trước'), ('c', 'Ước chừng bằng mắt')],
         'Số đo đổi theo từng tuần; đo lại sát ngày thì váy vừa in.'),
        ('la_lua', '🧵 Váy lụa trắng nhăn nhẹ, là thế nào?',
         [('a', 'Là hơi nước, nhiệt thấp, lót khăn mỏng'), ('b', 'Là nhiệt cao trực tiếp cho phẳng nhanh'), ('c', 'Phơi nắng cho thẳng')],
         'Lụa trắng cháy vàng ở nhiệt cao; hơi nước nhẹ làm phẳng mà không hỏng.'),
        ('cho_vay', '📦 Mang váy tới nhà cô dâu thế nào?',
         [('a', 'Treo móc, trùm túi vải, đặt phẳng ở ghế sau'), ('b', 'Gấp gọn bỏ vào thùng carton'), ('c', 'Cuộn tròn nhét cốp xe')],
         'Treo và trùm túi vải để váy không nhăn, không bám bụi.'),
    ],
    'makeup': [
        ('nen', '🧴 Bước đầu tiên trước khi đánh nền?',
         [('a', 'Làm sạch, dưỡng ẩm, thoa kem lót'), ('b', 'Đánh nền luôn cho nhanh'), ('c', 'Phủ phấn trước')],
         'Da sạch và đủ ẩm thì lớp nền mỏng, bám lâu.'),
        ('co', '🖌️ Cọ trang điểm cho cô dâu thế nào?',
         [('a', 'Cọ đã vệ sinh, sát khuẩn riêng từng người'), ('b', 'Dùng chung cọ của khách trước'), ('c', 'Thổi phù cho sạch')],
         'Cọ sạch riêng từng người, không lây mụn, không kích ứng.'),
        ('tong', '💡 Chọn tông nền theo gì?',
         [('a', 'Thử ở đường hàm, dưới ánh sáng tự nhiên'), ('b', 'Chọn tông trắng nhất cho sáng ảnh'), ('c', 'Thử trên mu bàn tay dưới đèn vàng')],
         'Đường hàm nối mặt với cổ; ánh sáng tự nhiên cho màu thật.'),
    ],
}
# the CHANGE demand of each service: {new} / {old} the brief's names, {n} extra tables. Option 'a' agrees (the brief
# changes), 'b' keeps it kindly, 'c' refuses rudely. (points, reply)
CHANGE = {
    'tiec': ('them_ban', '📞 Nhà trai báo thêm {n} bàn họ hàng dưới quê lên, giờ mới nói!',
             [('a', 'Nhận, gọi thêm phụ bếp, chia lại món cho đủ {total} bàn', 2, 'Cả nhà trai cảm ơn rối rít, không ai phải đứng.'),
              ('b', 'Ghép khách vào các bàn còn ghế trống', 1, 'Hơi chật nhưng ai cũng có chỗ.'),
              ('c', 'Từ chối thẳng: hợp đồng chốt số bàn rồi', 0, 'Họ hàng đứng ngoài rạp, mẹ chồng giận đỏ mặt.')]),
    'hoa': ('doi_mau', '📱 5 giờ sáng cô dâu nhắn: “Em đổi ý rồi, chuyển hết sang {new} được không chị?”',
            [('a', 'Đổi theo cô dâu: gọi chợ hoa giao gấp, làm lại hoa phụ', 2, 'Cô dâu gửi một tràng icon trái tim.'),
             ('b', 'Giữ {old}, khéo léo khuyên cô dâu (đổi giờ chót dễ hỏng)', 1, 'Cô dâu hơi tiếc nhưng nghe ra.'),
             ('c', 'Nhắn lại: “Hợp đồng ghi rồi, không đổi!”', 0, 'Cô dâu khóc, cả nhà gái nhìn bạn như kẻ thù.')]),
    'vay': ('doi_kieu', '👰 Thử váy lần cuối, cô dâu bỗng muốn đổi sang {new}!',
            [('a', 'Lấy mẫu {new} trong kho, sửa eo gấp trong ngày', 2, 'Cô dâu xoay một vòng trước gương, cười tít mắt.'),
             ('b', 'Giữ {old}, thêm khăn voan và thắt lưng cho mới lạ', 1, 'Cô dâu gật gù: cũng được.'),
             ('c', 'Bảo cô dâu: “Váy này đẹp rồi, đừng đòi nữa”', 0, 'Cô dâu dỗi, mặc váy mà mặt xị cả buổi.')]),
    'makeup': ('doi_style', '💄 Mẹ chồng ngó vào: “Trang điểm {old} quá, làm kiểu {new} cho mẹ!”',
               [('a', 'Hỏi ý cô dâu, chuyển sang {new} nhẹ nhàng cho vừa lòng cả hai', 2, 'Mẹ chồng gật đầu, cô dâu thở phào.'),
                ('b', 'Giữ kiểu cô dâu chọn, mời mẹ ra ngồi uống trà', 1, 'Mẹ chồng hơi phật ý nhưng cho qua.'),
                ('c', 'Nói thẳng: “Cô dâu là khách của con, mẹ đừng xen vào”', 0, 'Mẹ chồng bỏ ra ngoài, cả nhà mất vui.')]),
}
EXTRA_TABLES = (2, 3, 4)
# the other demands: (id, text, [(option, text, points, reply)]); two of them per job
DEMANDS = {
    'tiec': [
        ('me_chong_che', '👵 Mẹ chồng nếm thử, chê canh măng nhạt, đòi nêm lại cả nồi.',
         [('a', 'Nêm lại vừa phải, múc chén nhỏ mời bà nếm lần nữa', 2, 'Bà gật gù: “Thế này mới được.”'),
          ('b', 'Chiều bà, đổ thêm muối cho cả nồi', 1, 'Bà vừa lòng, nhưng bàn bên kêu mặn.'),
          ('c', 'Bảo bà: “Con nấu chục năm rồi bà ơi”', 0, 'Bà dỗi, kể với cả họ là cỗ dở.')]),
        ('chay', '🥬 Họ nhà gái có sáu người ăn chay, giờ mới báo.',
         [('a', 'Làm riêng một mâm chay từ rau củ, đậu hũ có sẵn', 2, 'Sáu bác cảm ơn mãi, khen bếp chu đáo.'),
          ('b', 'Mời họ ăn tạm rau xào với cơm', 1, 'No bụng nhưng hơi tủi.'),
          ('c', '“Không có món chay đâu, ráng ăn đi”', 0, 'Sáu bác bỏ về giữa tiệc.')]),
        ('bia', '🍺 Bạn chú rể đòi “thêm mười két bia, tính vào tiệc luôn đi anh”.',
         [('a', 'Báo rõ bia ngoài hợp đồng, hỏi ý cô dâu chú rể trước', 2, 'Chú rể gật đầu, tự trả phần bia thêm.'),
          ('b', 'Mang thêm vài két cho êm chuyện', 1, 'Êm chuyện, nhưng bạn tự bù tiền bia.'),
          ('c', 'Mang hết ra, không hỏi ai', 0, 'Cuối tiệc hai nhà cãi nhau ai trả tiền bia.')]),
        ('mat_dien', '⚡ Cúp điện đúng lúc đang hấp gà!',
         [('a', 'Chuyển sang bếp gas dự phòng, đóng kín tủ mát', 2, 'Món ra đúng giờ, không ai biết vừa cúp điện.'),
          ('b', 'Ngồi chờ có điện lại', 1, 'Món ra trễ hai mươi phút.'),
          ('c', 'Mở tủ mát lấy hết đồ ra cho thoáng', 0, 'Đồ tươi ôi mất một nửa.')]),
        ('doi_gio', '⏰ Thầy xem ngày bảo khai tiệc sớm ba mươi phút.',
         [('a', 'Ra món nguội trước, đẩy nhanh món nóng', 2, 'Khách vừa ngồi đã có món, nóng sau cũng kịp.'),
          ('b', 'Giữ lịch cũ, khách chờ thì chờ', 1, 'Khách ngồi nhìn bàn trống, hơi sốt ruột.'),
          ('c', 'Ra hết món một lượt cho xong', 0, 'Món nóng nguội ngắt.')]),
        ('chu_say', '🥴 Hai ông chú say, đòi đổi sang bàn sát sân khấu.',
         [('a', 'Mời trà gừng, xếp hai chú vào bàn trống gần đó', 2, 'Hai chú hát karaoke vui vẻ, không ai phiền.'),
          ('b', 'Kệ, để hai chú tự tìm chỗ', 1, 'Hai chú đứng giữa lối đi cả buổi.'),
          ('c', 'Cãi tay đôi với hai chú', 0, 'Suýt đổ cả mâm cỗ.')]),
    ],
    'hoa': [
        ('hoa_ly', '👵 Mẹ chồng chê hoa ly nặng mùi: “Nhức đầu quá!”',
         [('a', 'Rút hoa ly khỏi bàn gia tiên, thay cúc trắng', 2, 'Bà cười: “Đấy, thế có phải nhẹ nhõm không.”'),
          ('b', 'Xịt chút nước cho bớt mùi', 1, 'Đỡ được một lúc.'),
          ('c', 'Bảo bà ngồi xa ra', 0, 'Bà giận, cả họ xì xào.')]),
        ('gio_to', '🌬️ Gió to quật nghiêng cổng hoa ngoài sân!',
         [('a', 'Chằng dây, chèn bao cát chân cổng, cắm lại hoa rơi', 2, 'Cổng hoa đứng vững tới cuối tiệc.'),
          ('b', 'Dựa cổng vào tường cho đỡ', 1, 'Cổng đứng được nhưng hơi lệch trong ảnh.'),
          ('c', 'Bỏ luôn cổng hoa', 0, 'Cô dâu bước vào mà không có cổng hoa.')]),
        ('them_binh', '📞 Nhà trai đòi thêm bốn bình hoa bàn tiệc, “không thêm tiền nha”.',
         [('a', 'Chia nhỏ hoa dư làm thêm bốn bình mini', 2, 'Bàn nào cũng có hoa, chẳng ai so bì.'),
          ('b', 'Lấy bớt hoa cổng ra cắm bàn', 1, 'Cổng hoa trông thưa hẳn.'),
          ('c', 'Từ chối, cãi nhau to', 0, 'Nhà trai kể khắp phố là tiệm hoa keo kiệt.')]),
        ('di_ung', '🤧 Cô dâu phụ dị ứng phấn hoa, hắt hơi liên tục.',
         [('a', 'Đổi hoa cầm tay của cô dâu phụ sang hoa lụa', 2, 'Hết hắt hơi, ảnh chụp đẹp.'),
          ('b', 'Đưa cô ấy khẩu trang', 1, 'Ảnh nào cũng có một cái khẩu trang.'),
          ('c', 'Kệ, chụp ảnh xong là hết', 0, 'Mắt đỏ hoe cả buổi lễ.')]),
        ('hoa_dap', '🥀 Một xô hồng bị dập lúc chở tới.',
         [('a', 'Tỉa cánh dập làm hoa phụ, gọi giao thêm hồng', 2, 'Không ai nhận ra có xô hoa dập.'),
          ('b', 'Cắm luôn, nhìn xa không thấy', 1, 'Lại gần thì thấy cánh thâm.'),
          ('c', 'Vứt hết, cổng hoa thiếu một mảng', 0, 'Cổng hoa lủng một lỗ to.')]),
        ('tho_anh', '📸 Thợ ảnh đòi dời cổng hoa ra chỗ có nắng.',
         [('a', 'Dời cổng lúc chụp, kê lại đúng chỗ trước giờ lễ', 2, 'Ảnh đẹp, lễ vẫn đúng chỗ.'),
          ('b', 'Bảo thợ ảnh tự xoay xở', 1, 'Ảnh hơi tối.'),
          ('c', 'Không cho ai đụng vào cổng hoa', 0, 'Thợ ảnh và tiệm hoa cãi nhau trước mặt khách.')]),
    ],
    'vay': [
        ('tang_can', '😅 Cô dâu tăng hai ký, khóa kéo không lên!',
         [('a', 'Nới đường may hông, thêm dây rút lưng', 2, 'Váy vừa in, cô dâu thở được.'),
          ('b', 'Bảo cô dâu hóp bụng cả buổi', 1, 'Cô dâu không dám ăn miếng nào.'),
          ('c', 'Nói: “Ai bảo ăn nhiều”', 0, 'Cô dâu khóc, lớp trang điểm trôi mất.')]),
        ('ho_vai', '👵 Mẹ chồng chê váy hở vai: “Ra đường người ta cười!”',
         [('a', 'Thêm áo choàng ren mỏng cho lễ gia tiên, vào tiệc thì cởi', 2, 'Bà hài lòng, cô dâu vẫn đẹp lúc vào tiệc.'),
          ('b', 'Bảo cô dâu khoác tạm áo khoác', 1, 'Ảnh lễ gia tiên có cái áo khoác lạc tông.'),
          ('c', 'Mặc kệ ý bà', 0, 'Bà ngồi quay lưng suốt buổi lễ.')]),
        ('vest_chat', '🤵 Vest chú rể chật vai, giơ tay là kêu “rẹt”.',
         [('a', 'Lấy size lớn hơn, lên lai quần ngay tại chỗ', 2, 'Chú rể nâng ly thoải mái.'),
          ('b', 'Dặn chú rể đừng giơ tay cao', 1, 'Chú rể nâng ly như robot.'),
          ('c', 'Cứ mặc, rách thì thôi', 0, 'Đường may toạc giữa lúc rót tháp ly.')]),
        ('ca_phe', '☕ Phù dâu làm đổ cà phê lên tà váy cưới!',
         [('a', 'Thấm ngay bằng khăn lạnh, xịt tẩy vết cho vải lụa', 2, 'Vết sạch bong trước giờ rước dâu.'),
          ('b', 'Lấy khăn giấy chà thật mạnh', 1, 'Vết loang to hơn một chút.'),
          ('c', 'Xoay vết ra sau lưng', 0, 'Ảnh nào cũng thấy vết nâu.')]),
        ('giay_cao', '👠 Cô dâu đòi giày cao mười hai phân, đi không vững.',
         [('a', 'Đưa thêm đôi giày bệt cùng màu để thay lúc tiệc', 2, 'Cô dâu nhảy cả buổi không mỏi chân.'),
          ('b', 'Dặn cô dâu đi chậm thôi', 1, 'Cô dâu đi từng bước một.'),
          ('c', 'Chiều cô dâu, ngã thì chịu', 0, 'Cô dâu trẹo chân ngay bậc sân khấu.')]),
        ('voan', '🧕 Cô dâu muốn khăn voan dài ba mét kéo lê.',
         [('a', 'Làm voan ba mét có móc gài, tháo ra lúc vào tiệc', 2, 'Lúc lễ lộng lẫy, lúc tiệc gọn gàng.'),
          ('b', 'Làm ba mét, ai dẫm thì thôi', 1, 'Bị dẫm hai lần.'),
          ('c', 'Cắt còn một mét, không hỏi', 0, 'Cô dâu giận tím mặt.')]),
    ],
    'makeup': [
        ('mun', '😣 Sáng cưới cô dâu nổi mụn ngay cằm.',
         [('a', 'Chấm kem trị mụn, che khuyết điểm mỏng từng lớp', 2, 'Lên ảnh mịn màng, không ai thấy mụn.'),
          ('b', 'Đánh nền thật dày cho kín', 1, 'Mặt cứng như mặt nạ trong ảnh.'),
          ('c', 'Nặn mụn cho nhanh', 0, 'Cằm sưng đỏ cả buổi.')]),
        ('khoc', '😭 Lễ gia tiên, cô dâu khóc lem hết mascara.',
         [('a', 'Mang sẵn mascara chống nước, dặm lại mắt trong năm phút', 2, 'Mắt lại long lanh trước giờ rước dâu.'),
          ('b', 'Lau đại bằng khăn giấy', 1, 'Còn vệt đen dưới mắt.'),
          ('c', 'Bảo cô dâu đừng khóc nữa', 0, 'Cô dâu khóc to hơn.')]),
        ('tre_gio', '⏰ Cô dâu dậy muộn, chỉ còn ba mươi phút trước giờ rước dâu.',
         [('a', 'Làm nền nhanh, ưu tiên mắt môi, búi tóc gọn', 2, 'Kịp giờ, vẫn xinh.'),
          ('b', 'Làm đầy đủ như cũ, nhà trai chờ thì chờ', 1, 'Nhà trai đứng ngoài ngõ bốn mươi phút.'),
          ('c', 'Bỏ trang điểm, chỉ tô son', 0, 'Cô dâu tái nhợt trong ảnh cưới.')]),
        ('chi_gai', '👯 Chị gái cô dâu chen vào đòi trang điểm trước.',
         [('a', 'Làm nhanh cho chị một lớp nhẹ sau khi xong cô dâu', 2, 'Hai chị em đều vui.'),
          ('b', 'Làm cho chị trước, cô dâu chờ', 1, 'Cô dâu sốt ruột nhìn đồng hồ.'),
          ('c', 'Mời chị ra ngoài', 0, 'Hai chị em giận nhau cả ngày cưới.')]),
        ('nong', '🥵 Rạp cưới nóng, mồ hôi làm trôi lớp nền.',
         [('a', 'Dặm phấn phủ kiềm dầu, xịt khóa nền, kê quạt', 2, 'Lớp nền giữ tới cuối tiệc.'),
          ('b', 'Đánh thêm một lớp nền nữa', 1, 'Dày và bí da.'),
          ('c', 'Kệ, chụp ảnh có filter', 0, 'Ảnh cưới bóng dầu loáng.')]),
        ('mi_gia', '👁️ Cô dâu đòi mi giả thật dày, mắt bị kích ứng đỏ.',
         [('a', 'Gỡ ngay, rửa mắt, đổi sang mi lẻ mỏng', 2, 'Mắt hết đỏ, vẫn to tròn.'),
          ('b', 'Nhỏ thuốc rồi đeo tiếp', 1, 'Chảy nước mắt cả buổi.'),
          ('c', 'Bảo cô dâu chịu khó', 0, 'Mắt sưng húp trong ảnh cưới.')]),
    ],
}
DEMANDS_PER_JOB = 2
STEP_NAMES = dict(b1='Làm theo yêu cầu', b2='Làm theo yêu cầu', k='Tay nghề', d='Oái ăm', final='Kiểm lần cuối')
MAX_SCORE = 14                 # b1 2 + b2 2 + k 2 + three demands 6 + final 2
STARS = ((13, 5), (10, 4), (7, 3), (4, 2), (0, 1))   # (score at least, stars)
FEEDBACK = {2: 'Khéo léo', 1: 'Tạm ổn', 0: 'Hỏng việc'}


def stars_of(score: int) -> int:
    return next(s for low, s in STARS if score >= low)


def opt_name(svc: str, field: str, value) -> str:
    for f, _, opts in SVC[svc]['brief']:
        if f == field:
            return next((n for i, n, _ in opts if i == value), str(value))
    return str(value)


def brief_line(svc: str, brief: dict, qty: int | None = None) -> str:
    """'20 bàn · Tiêu chuẩn · Gà hấp lá chanh' (what the order's note and the credits show)."""
    parts = [f'{int(brief.get("tables") or qty or 0)} bàn'] if svc == 'tiec' and (brief.get('tables') or qty) else []
    parts += [opt_name(svc, f, brief.get(f)) for f, _, _ in SVC[svc]['brief'] if brief.get(f) is not None]
    return ' · '.join(parts)


# ---------------------------------------------------------------- credits (who serves a wedding), shared with live/
# Orders of the couple's two players for the four services, newest first; the job row (if any) carries the stars,
# the brief and the couple it was bound to. ? = buyer a, buyer b, since (the couple's start).
CREDITS_SQL = ("SELECT o.id, o.career, o.service, o.provider, o.status, o.qty, o.created_at, a.display AS pname, "
               "j.stars, j.brief, j.status AS jst, j.couple AS jc FROM svc_orders o "
               "LEFT JOIN wedsvc_jobs j ON j.order_id=o.id LEFT JOIN accounts a ON a.sid=o.provider "
               "WHERE o.buyer IN (?, ?) AND o.kind='svc' AND o.status IN ('held','working','delivered','ready','done') "
               "AND o.service IN ('tiec_cuoi','hoa_cuoi','vay_cuoi','trang_diem_cuoi') AND o.created_at>=? "
               "ORDER BY o.created_at DESC LIMIT 40")
# 📸 the couple's wedding photos (game/photo_studio.py 'doi'): ? = buyer a, buyer b, since
PHOTO_SQL = ("SELECT shooter_name, status, at FROM photo_orders WHERE buyer IN (?, ?) AND pkg='doi' "
             "AND status IN ('open','shoot','done') AND at>=? ORDER BY at DESC LIMIT 6")


def clean_name(name) -> str:
    import re
    text = re.sub(r'[\x00-\x1f\x7f<>&"`]', '', str(name or '')).strip()
    return text[:24] or 'Một người chơi'


def credits_from_rows(rows, photos=(), couple_id=None) -> list:
    """[{key, icon, label, line, name, state ('done' | 'prep'), stars, detail, color?}]: one per service, a delivered
    one first, else the newest in progress; the wedding photographer last."""
    import json
    best = {}
    for r in rows or ():
        key = PAIRS.get((r['career'], r['service']))
        if not key or (r.get('jc') is not None and couple_id is not None and int(r['jc']) != int(couple_id)):
            continue
        done = r.get('jst') == 'delivered' or r['status'] in ('ready', 'done')
        cur = best.get(key)
        if cur and (cur['state'] == 'done' or not done):
            continue
        try:
            brief = json.loads(r['brief']) if r.get('brief') else {}
        except (TypeError, ValueError):
            brief = {}
        brief = brief if isinstance(brief, dict) else {}
        s = SVC[key]
        name = clean_name(r.get('pname'))
        item = dict(key=key, icon=s['icon'], label=s['short'], line=s['credit'].format(n=name), name=name,
                    state='done' if done else 'prep', stars=int(r['stars'] or 0) if done else 0,
                    detail=brief_line(key, brief, int(r.get('qty') or 0)) if brief else '')
        if key == 'hoa' and brief.get('mau') in FLOWER_HEX:
            item['color'] = brief['mau']
        if key == 'tiec' and brief.get('menu'):
            item['menu'] = brief['menu']
        if key == 'tiec':
            item['tables'] = int(brief.get('tables') or r.get('qty') or 0)
        best[key] = item
    out = [best[k] for k in ORDER if k in best]
    for p in sorted(photos or (), key=lambda p: p['status'] != 'done'):
        name = clean_name(p.get('shooter_name'))
        out.append(dict(key='anh', icon=PHOTO['icon'], label=PHOTO['short'], line=PHOTO['credit'].format(n=name), name=name,
                        state='done' if p['status'] == 'done' else 'prep', stars=0, detail=''))
        break
    return out
