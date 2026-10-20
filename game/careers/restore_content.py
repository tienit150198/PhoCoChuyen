"""🧰 Xưởng phục chế Hồn Xưa: the words and tables of the restoration workshop (game/careers/restore.py).

Every table is static: a ticket is a pure function of (day, slot), so validate_state can regenerate it. The owner's
standing rule (06/10, "nghề nào cũng phải có nhiều yêu cầu oái oăm"): each ticket carries one or two awkward customer
demands (DEMANDS) the player must settle at the counter before touching the piece, and some of them change what the
right finish or the right part is.
"""
from __future__ import annotations

PLACE = 'Xưởng phục chế Hồn Xưa'
OWNER = 'Chú Khải'

PEOPLE = [('Chú Khải', 'Chủ xưởng phục chế', 'Ba chục năm phục chế đồ xưa, dặn kỹ: giữ hồn món đồ trước đã.'),
          ('Bà Sáu', 'Hàng xóm đầu hẻm', 'Mang đồ của bà ngoại để lại, nhớ từng vết xước.'),
          ('Anh Toàn', 'Dân sưu tầm đồ cổ', 'Hay khoe đồ trăm năm, mặc cả từng đồng.'),
          ('Chị Hạnh', 'Cô dâu sắp cưới', 'Muốn đồ hồi môn của mẹ kịp ngày cưới.'),
          ('Bé Na và ba', 'Hai ba con', 'Mang đồ chơi, xe đạp cũ của ông nội tới.'),
          ('Ông Tư', 'Thầy giáo về hưu', 'Giữ gia phả, đồng hồ và cái đài từ thời đi học.')]

# The signs written on the ticket and the damage they point to (the inspect stage: pick the damage of each sign).
DAMAGES = {
    'crack': ('Nứt', 'có đường nứt chân chim chạy dọc'),
    'rust': ('Gỉ sét', 'lấm tấm gỉ nâu đỏ ở mép kim loại'),
    'worm': ('Mọt', 'lỗ li ti, gõ nhẹ rơi bột gỗ vàng'),
    'flake': ('Bong sơn', 'lớp sơn phồng lên, bong thành vảy'),
    'joint': ('Lỏng mộng', 'lắc nhẹ là kêu cót két, mộng hở'),
    'tear': ('Rách', 'rách một đường, sợi xơ tưa ra'),
    'seized': ('Kẹt máy', 'bộ máy kẹt cứng, vặn không nhúc nhích'),
    'chip': ('Mẻ', 'mẻ một miếng nhỏ ở miệng'),
    'loose': ('Tuột sợi', 'sợi đan tuột, mặt đan lỏng lẻo'),
    'wire': ('Hỏng dây điện', 'dây điện chảy nhựa, bật lên chập chờn'),
    'stain': ('Ố mốc', 'lấm tấm đốm ố vàng, có mùi ẩm mốc'),
}
# The right technique for each damage (the fix stage) and the tempting wrong ones.
FIXES = {
    'crack': 'glue_clamp', 'rust': 'derust', 'worm': 'worm_fill', 'flake': 'consolidate', 'joint': 'tenon',
    'tear': 'patch', 'seized': 'service', 'chip': 'fill_paint', 'loose': 'reweave', 'wire': 'rewire', 'stain': 'spot_clean',
}
FIX_OPTIONS = [
    ('glue_clamp', 'Keo chuyên dụng, kẹp giữ 24 giờ'), ('derust', 'Tẩy gỉ nhẹ, phủ dầu chống gỉ'),
    ('worm_fill', 'Bơm thuốc trị mọt, trám bột gỗ'), ('consolidate', 'Gia cố lớp sơn bong, dặm màu chỗ mất'),
    ('tenon', 'Làm lại mộng gỗ, không bắn đinh'), ('patch', 'Vá lót mặt sau, khâu chỉ cùng màu'),
    ('service', 'Tháo máy, lau sạch, tra dầu'), ('fill_paint', 'Trám keo sứ, vẽ dặm men'),
    ('reweave', 'Đan lại sợi tuột theo lối cũ'), ('rewire', 'Thay dây điện mới, giữ vỏ cũ'),
    ('spot_clean', 'Hong khô chỗ râm, chấm khử ố từng đốm, không ngâm nước'),
    ('nails', 'Bắn đinh cho nhanh'), ('superglue', 'Đổ keo 502 cho chắc'), ('tape', 'Quấn băng keo cho kín'),
]
# Cleaning by material (the clean stage).
MATERIALS = {
    'wood': ('Gỗ', 'oil_wipe'), 'metal': ('Kim loại', 'soft_brush'), 'ceramic': ('Gốm sứ', 'warm_soap'),
    'fabric': ('Vải', 'vacuum'), 'paper': ('Giấy', 'dry_brush'), 'leather': ('Da', 'saddle_soap'),
    'rattan': ('Mây tre', 'damp_brush'),
}
CLEAN_OPTIONS = [
    ('oil_wipe', 'Khăn ẩm vắt kiệt rồi lau dầu gỗ'), ('soft_brush', 'Chải bàn chải mềm, lau dầu khoáng'),
    ('warm_soap', 'Nước ấm pha xà phòng trung tính'), ('vacuum', 'Hút bụi nhẹ qua lưới, chấm khăn ẩm'),
    ('dry_brush', 'Chổi lông mềm, bông khô, không nước'), ('saddle_soap', 'Xà phòng da, lau khô ngay'),
    ('damp_brush', 'Chải ẩm theo thớ, phơi râm'),
    ('pressure', 'Xịt nước áp lực cho sạch hẳn'), ('sand', 'Chà nhám thật mạnh cho trắng gỗ'), ('bleach', 'Ngâm thuốc tẩy qua đêm'),
]
FINISH_OPTIONS = [
    ('wax', 'Phủ sáp ong, giữ dấu thời gian'), ('touch', 'Dặm màu chỗ bong, giữ nước gốc'),
    ('oil', 'Lau dầu bảo vệ mỏng'), ('archive', 'Ép phẳng, cất hộp giấy không axit'),
    ('keep_scar', 'Phủ sáp, chừa nguyên vết xước kỷ niệm'), ('renew', 'Sơn lại, đánh bóng như mới'),
]
# A part the piece needs: from the workshop's drawer, made again from the same material, or (never) taken off
# another customer's piece / left out.
PART_OPTIONS = [
    ('stock', 'Lấy từ ngăn linh kiện của xưởng'), ('make', 'Chế lại từ vật liệu cùng loại, ghi phiếu'),
    ('borrow', 'Tháo tạm từ đồ của khách khác'), ('skip', 'Lắp thiếu, trả đồ trước đã'),
]
CHECKS = (('stable', 'Món đồ chắc, không lung lay'), ('photo', 'Chụp ảnh trước và sau phục chế'),
          ('note', 'Ghi đúng tuổi đồ và hạng mục lên phiếu'), ('care', 'Dặn khách cách giữ gìn'))

# kind, title, introduction day, material, damage pool, the right finish, parts, the price label
ITEMS = (
    ('clock', 'Đồng hồ quả lắc của ông nội', 1, 'wood', ('seized', 'crack', 'flake'), 'wax', ('quả lắc', 'dây cót', 'kim phút')),
    ('chair', 'Ghế mây bà ngồi hóng mát', 1, 'rattan', ('loose', 'joint'), 'oil', ('sợi mây', 'chốt gỗ')),
    ('radio', 'Đài radio đi học xa', 1, 'metal', ('rust', 'wire', 'seized'), 'touch', ('núm vặn', 'bóng đèn tín hiệu')),
    ('sewing', 'Máy khâu con bướm', 4, 'metal', ('rust', 'seized'), 'oil', ('dây curoa', 'chân vịt')),
    ('vase', 'Bình gốm men lam', 4, 'ceramic', ('chip', 'crack'), 'touch', ('đế gỗ',)),
    ('trunk', 'Rương gỗ hồi môn', 4, 'wood', ('worm', 'joint', 'flake'), 'wax', ('bản lề đồng', 'khóa rương')),
    ('suitcase', 'Va li da ngày nhập học', 10, 'leather', ('tear', 'rust'), 'oil', ('khóa số', 'quai xách')),
    ('lamp', 'Đèn dầu thắp đêm mất điện', 10, 'metal', ('rust', 'crack'), 'touch', ('bóng thủy tinh', 'bấc đèn')),
    ('fan', 'Quạt con cóc', 10, 'metal', ('wire', 'seized', 'rust'), 'touch', ('cánh quạt', 'tụ điện')),
    ('genealogy', 'Cuốn gia phả chép tay', 20, 'paper', ('tear', 'stain'), 'archive', ('bìa da',)),
    ('aodai', 'Áo dài cưới của mẹ', 20, 'fabric', ('tear', 'stain'), 'archive', ('khuy bấm', 'chỉ thêu')),
    ('bicycle', 'Xe đạp cọc cạch của ông', 20, 'metal', ('rust', 'seized', 'flake'), 'touch', ('xích', 'chuông', 'yên da')),
    ('altar', 'Tủ thờ gỗ gụ', 40, 'wood', ('worm', 'flake', 'crack'), 'wax', ('tay nắm đồng', 'ván hậu')),
    ('camera', 'Máy ảnh phim của ba', 40, 'metal', ('seized', 'rust'), 'oil', ('lò xo màn trập', 'nắp ống kính')),
)

# The surface of each piece, written on the ticket: what the finish follows (FINISH_BY_SURFACE, one rule in RULES), so the
# right finish is read off the piece and not guessed. surface id: (words on the ticket).
SURFACES = dict(wood='Gỗ mộc, đánh sáp xưa', oiled='Mây tre, da hay bộ máy kim loại trần', painted='Bề mặt sơn màu hay tráng men',
                archive='Giấy, vải: đồ mềm, dễ rách')
FINISH_BY_SURFACE = dict(wood='wax', oiled='oil', painted='touch', archive='archive')
SURFACE = dict(clock=('wood', 'Hộp gỗ đánh sáp, mặt số tráng men'), chair=('oiled', 'Mây tre đan'),
               radio=('painted', 'Vỏ sắt sơn màu kem'), sewing=('oiled', 'Thân gang trần, bộ máy tra dầu'),
               vase=('painted', 'Gốm tráng men lam'), trunk=('wood', 'Gỗ mít mộc, đánh sáp'), suitcase=('oiled', 'Da bò thuộc'),
               lamp=('painted', 'Thân đồng sơn xanh, bóng thủy tinh'), fan=('painted', 'Vỏ sắt sơn xanh ngọc'),
               genealogy=('archive', 'Giấy dó chép tay'), aodai=('archive', 'Lụa tơ tằm thêu tay'),
               bicycle=('painted', 'Khung sắt sơn đen'), altar=('wood', 'Gỗ gụ đánh sáp'), camera=('oiled', 'Thân kim loại trần, bộ máy tinh'))
# Who brings each kind of piece (PEOPLE indices; Chú Khải, the owner, never brings one).
OWNERS = dict(clock=(5, 1), chair=(1,), radio=(5,), sewing=(1, 3), vase=(2, 1), trunk=(3,), suitcase=(4, 5), lamp=(1, 2),
              fan=(4, 1), genealogy=(5,), aodai=(3,), bicycle=(4,), altar=(1, 5), camera=(4, 2))

# 🌀 The awkward demands ("oái oăm"). id: (from day, the customer's words, options [(id, words)], the right option,
# what it changes: finish=<id> the right finish, part='make' a part is missing, only=<materials> the pieces it fits).
DEMANDS = {
    'scratch': (1, 'Khách dặn: “Vết xước này là con tôi cào hồi nhỏ, giữ nguyên cho tôi, nhưng phải đẹp như mới nghen!”',
                [('keep', 'Giữ nguyên vết xước, chỉ phủ sáp bảo vệ quanh nó'), ('sand', 'Chà hết cho mặt gỗ láng'),
                 ('paint', 'Sơn đè một lớp, nhìn vẫn thấy vết là được')], 'keep', dict(finish='keep_scar', only=('wood', 'metal', 'leather', 'rattan', 'ceramic'))),
    'age_lie': (1, 'Khách khoe: “Đồ gia truyền trăm năm đó!”. Nhưng dưới đáy còn tem nhà máy, chừng hai chục năm.',
                [('truth', 'Nói nhẹ nhàng tuổi thật, ghi đúng tuổi lên phiếu, vẫn làm kỹ'), ('flatter', 'Ghi “trăm năm” cho khách vui'),
                 ('refuse', 'Trả đồ, không nhận nữa')], 'truth', {}),
    'haggle': (1, 'Khách mặc cả: “Có mấy vết thôi, bớt nửa giá đi, không thì tôi mang qua tiệm khác.”',
               [('scope', 'Giữ giá công, chỉ bớt hạng mục khách không cần'), ('half', 'Bớt nửa giá rồi làm qua loa'),
                ('chase', 'Nói khách mang đi tiệm khác luôn')], 'scope', {}),
    'grandma_new': (4, 'Khách nói: “Đồ của bà ngoại để lại đó, mà làm mới tinh giùm, bóng loáng như đồ ngoài siêu thị.”',
                    [('sign', 'Nói rõ làm mới sẽ mất lớp gốc; khách vẫn muốn thì ký phiếu rồi làm mới'),
                     ('secret', 'Cứ phủ sáp giữ nước gốc, khỏi nói khách'), ('copy', 'Đổi cho khách một món mới mua ngoài chợ')],
                    'sign', dict(finish='renew', only=('wood', 'metal', 'leather', 'rattan', 'ceramic'))),
    'missing': (4, 'Mở ra mới thấy thiếu hẳn một linh kiện, chợ không còn bán. Khách đòi: “Lắp đủ cho tôi nghen.”',
                [('tell', 'Báo khách, hẹn chế lại linh kiện từ vật liệu cùng loại'), ('silent', 'Lặng lẽ lắp đồ nhựa thay vào'),
                 ('promise', 'Hứa tìm được hàng zin trong ngày')], 'tell', dict(part='make')),
    'rush': (4, 'Khách hối: “Chiều nay đám cưới rồi, làm trong một tiếng nha!” Mà keo phải để khô cả ngày.',
             [('honest', 'Hẹn giờ thật, cho mượn khay trưng tạm cho đám cưới'), ('fast', 'Sấy nóng cho keo mau khô'),
              ('yes', 'Gật đại cho khách vui')], 'honest', {}),
    'diy': (10, 'Khách đã tự dán keo 502 trước, giờ nói: “Tiệm làm hỏng thì tiệm đền nha.”',
            [('record', 'Chụp ảnh và ghi tình trạng có keo cũ lên phiếu trước khi nhận'), ('ignore', 'Nhận luôn, khỏi ghi'),
             ('blame', 'Cãi lại cho ra lẽ')], 'record', {}),
    'two_heirs': (10, 'Hai anh em cùng tới, anh muốn giữ dấu xưa, em muốn làm mới. Ai cũng nói “đồ của tui”.',
                  [('agree', 'Chờ hai người thống nhất, ghi một yêu cầu có cả hai chữ ký'), ('elder', 'Làm theo người anh'),
                   ('split', 'Làm mỗi bên một nửa')], 'agree', {}),
    'letter': (10, 'Trong ngăn bí mật có xấp thư cũ. Khách dặn trước: “Thấy gì trong đó thì bỏ hết giùm.”',
               [('return', 'Giữ nguyên xấp thư, gói lại trả tận tay khách hỏi lại'), ('trash', 'Bỏ hết như khách dặn'),
                ('read', 'Đọc thử xem có gì hay')], 'return', dict(only=('wood', 'leather'))),
    'fake_antique': (20, 'Thương lái nhờ: “Làm cũ đi, đóng dấu đời Nguyễn giùm, tui bán lại có lời chia cho.”',
                     [('decline', 'Từ chối làm giả, chỉ phục chế và ghi đúng tuổi đồ'), ('stamp', 'Đóng dấu giả, chia lời'),
                      ('half', 'Làm cũ thôi, không đóng dấu')], 'decline', {}),
    'smell': (20, 'Khách dặn: “Tủ có mùi long não của bà, đừng khử mùi nghen.” Mà bên trong mốc lấm tấm.',
              [('gentle', 'Lau mốc nhẹ từng chỗ, không xông khử mùi cả tủ'), ('spray', 'Xịt khử mùi cho sạch hẳn'),
               ('leave', 'Để nguyên mốc cho giữ mùi')], 'gentle', dict(only=('wood',))),
    'photo_each': (20, 'Khách đòi: “Làm bước nào chụp gửi Zalo bước đó, mười phút một lần nha.”',
                   [('batch', 'Chụp mỗi công đoạn, gửi gom cuối buổi, báo trước giờ gửi'), ('stop', 'Dừng tay mười phút một lần để chụp'),
                    ('none', 'Không chụp gì cả cho đỡ phiền')], 'batch', {}),
    'lucky_red': (40, 'Thầy phong thủy của khách dặn sơn đỏ chót cả mặt gỗ gụ cho “hợp mệnh”.',
                  [('inside', 'Giữ mặt gỗ, lót nỉ đỏ bên trong cho hợp ý'), ('red', 'Sơn đỏ chót cả mặt ngoài'),
                   ('argue', 'Chê thầy phong thủy')], 'inside', dict(only=('wood',))),
    'museum': (40, 'Bảo tàng phường mượn trưng bày, đòi giấy chứng nhận “nguyên bản trăm phần trăm”.',
               [('report', 'Ghi rõ phần nào gốc, phần nào chế lại trong biên bản phục chế'), ('sign', 'Ký “nguyên bản 100%” cho xong'),
                ('hide', 'Giấu phần chế lại dưới lớp sơn')], 'report', {}),
}
DEMAND_ORDER = tuple(DEMANDS)

RULES = [
    'Đọc dấu hiệu trên phiếu rồi gọi đúng tên từng hư hỏng: nứt, gỉ, mọt, bong sơn, lỏng mộng, rách, kẹt máy, mẻ, tuột sợi, hỏng dây điện, ố mốc.',
    'Chốt yêu cầu oái oăm của khách trước khi đụng vào đồ: nói thật, ghi phiếu, không làm giả, không giấu khách.',
    'Linh kiện: còn trong ngăn thì lấy, thiếu thì chế lại từ vật liệu cùng loại và ghi phiếu. Không bao giờ tháo đồ của khách khác.',
    'Làm sạch theo chất liệu: gỗ lau dầu, kim loại chải mềm, gốm nước ấm, vải hút bụi nhẹ, giấy chổi khô, da xà phòng da, mây chải ẩm.',
    'Mỗi hư hỏng một cách phục hồi đúng; đinh, keo 502 và băng keo làm hỏng hồn món đồ.',
    'Hoàn thiện theo bề mặt ghi trên phiếu: gỗ mộc phủ sáp ong; mây tre, da và máy kim loại trần lau dầu mỏng; đồ sơn màu hay tráng men dặm màu, giữ nước gốc; giấy, vải ép phẳng cất hộp không axit. Khách đã chốt khác thì theo khách: giữ vết xước kỷ niệm, hay ký phiếu làm mới.',
    'Chương 1 ngày 1: đồng hồ, ghế mây, đài; ngày 4: máy khâu, bình gốm, rương; ngày 10: va li, đèn dầu, quạt; ngày 20: gia phả, áo dài, xe đạp; ngày 40: tủ thờ, máy ảnh phim.',
    'Thợ phục chế vững tay: 100 phiếu đạt từ 90% và 30 ngày có trả đồ. Nghệ nhân Hồn Xưa: 180 phiếu đạt và 45 ngày. Ca rỗng không được tính.',
]
