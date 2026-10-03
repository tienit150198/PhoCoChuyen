"""Truyện nghề: every workplace has its own little story arc.

Next to the neighbourhood journey (game/journey.py), each of the 20 careers
has one arc of five beats with a small recurring cast: a shy pupil who sings
at the year-end show, a stormy rainy season on the farm, an old woman waiting
for letters from abroad, a fake invoice in the office…

* Beats are strictly ordered. A beat becomes due when the real save of that
  workplace reaches its `when` (tasks served, days closed, level, an optional
  metric, and a minimum gap in workplace days since the previous beat).
* `after()` runs after every career action and queues the acting workplace's
  next beat into a small queue; the client shows it as a scene and answers with
  `st_seen` (plain beat) or `st_choose` (beat with a two-option choice).
* Choices are flavour only: reply lines, a small relationship bump with a
  linked NPC and at most a few coins. Arcs never gate the journey or the work.

State lives in the root `s['stories']` (setdefault in `migrate`, checked by
`validate`), like `s['journey']`. See docs/superpowers/specs/2026-09-29-career-stories-design.md.
"""
from __future__ import annotations

import copy
from .jsoncopy import tree_copy

from .content import CAREERS, CAREER_META, NPC_INDEX

VERSION = 1
QUEUE_MAX = 40
MAX_COINS = 10
REL_BUMP = 6
TOKENS = {
    'anh': dict(male='anh', female='chị', none='bạn'),
    'Anh': dict(male='Anh', female='Chị', none='Bạn'),
    'thay': dict(male='thầy', female='cô', none='cô'),
    'Thay': dict(male='Thầy', female='Cô', none='Cô'),
}
# Default rhythm of the five beats: first finished task, then ~days 2, 4, 6, 9.
WHEN = (dict(served=1), dict(days=2, gap=1), dict(days=4, served=8, gap=1),
        dict(days=6, served=14, gap=1), dict(days=9, served=22, gap=2))


def _p(name, emoji, role, npc=None):
    return dict(name=name, emoji=emoji, role=role, npc=npc)


def _o(oid, label, reply, rel=None, coins=0):
    return dict(id=oid, label=label, reply=list(reply), rel=rel, coins=coins)


def _b(title, emoji, hint, lines, choice=None, **when):
    return dict(title=title, emoji=emoji, hint=hint, lines=list(lines), choice=choice, when=when)


def _c(prompt, a, b):
    return dict(prompt=prompt, options=[a, b])


ARCS = {
    # ------------------------------------------------------------ chương 1
    'milk_tea': dict(
        title='Ly trà mùa thi', emoji='📚',
        keepsake=dict(emoji='🧋', name='Công thức “Trà Mùa Thi”', desc='Món mới trên bảng menu, đặt theo tên mùa thi của Linh.'),
        cast={'linh': _p('Linh', '🎒', 'Khách quen, ôn thi đại học', 'milk_tea_npc_01'),
              'nhi': _p('Nhi', '🧑‍🍳', 'Bạn phụ quầy', 'milk_tea_npc_06'),
              'bac_tu': _p('Bác Tư', '👴', 'Hàng xóm', 'milk_tea_npc_02'),
              'miu': _p('Miu', '📸', 'Bạn thân của Linh', 'milk_tea_npc_03')},
        beats=[
            _b('Vị khách giờ tan học', '🎒', 'Có một bạn học sinh hay ngồi bàn cạnh cửa sổ tới tận giờ đóng cửa.', [
                ('linh', '{Anh} ơi, cho em một ly trà sữa ít đá, ba phần đường nha.'),
                ('nhi', 'Bạn đó ngày nào cũng ngồi bàn cửa sổ, ôm cuốn sách dày cộm tới lúc tiệm đóng cửa.'),
                ('linh', 'Em ôn thi đại học. Còn bốn mươi ngày nữa thôi…'),
                ('me', 'Vậy ly này tiệm pha thật êm cho em nhé. Cần gì cứ gọi.')]),
            _b('Bốn mươi ngày', '⏳', 'Linh trông mệt hơn mọi hôm.', [
                ('bac_tu', 'Con bé học khuya quá. Sáng nào bác đi tập thể dục cũng thấy đèn phòng nó còn sáng.'),
                ('linh', 'Em uống trà sữa cho tỉnh, mà uống nhiều đường xong lại buồn ngủ hơn.'),
                ('nhi', 'Hay mình làm cho bạn ấy món gì nhẹ bụng hơn ha?')],
                _c('Tối nay làm gì cho Linh?',
                   _o('a', 'Pha tặng một ly trà gừng ấm', [('linh', 'Ấm bụng ghê. Cảm ơn {anh}, em học thêm được một chương nữa rồi.')], rel='linh'),
                   _o('b', 'Viết một câu cổ vũ lên nắp ly', [('linh', '“Từng trang một thôi.” Em chụp lại làm hình nền điện thoại luôn nè.')], rel='linh'))),
            _b('Công thức mới', '🍵', 'Nhi đang nghĩ một món mới cho người thức khuya.', [
                ('nhi', 'Ô long, sữa tươi, ít ngọt, thêm thạch nha đam. Món cho người thức khuya mà không muốn say đường!'),
                ('me', 'Để mình canh lại lượng trà cho khỏi đắng.'),
                ('linh', 'Uống xong thấy đầu nhẹ hẳn. {Anh} đặt tên món này đi!'),
                ('nhi', 'Chưa được. Đợi bạn thi xong rồi mới đặt tên.')]),
            _b('Ngày thi', '✏️', 'Mấy hôm nay bàn cửa sổ bỏ trống.', [
                ('miu', 'Linh đi thi rồi {anh} ơi. Bạn ấy nhờ em mua mang vào ly quen, ít đá, ba phần đường.'),
                ('bac_tu', 'Hèn chi mấy bữa nay bàn cửa sổ trống trơn.'),
                ('me', 'Để mình pha thật cẩn thận. Nhắn Linh: làm từng câu một thôi.'),
                ('miu', 'Em chụp ly này gửi Linh liền. Chắc bạn ấy vui lắm.')]),
            _b('Trà Mùa Thi', '🎓', 'Sắp có tin vui từ bàn cửa sổ.', [
                ('linh', '{Anh} ơi! Em đậu rồi! Đậu nguyện vọng một luôn!'),
                ('bac_tu', 'Bác biết mà. Con bé học chăm vậy thì phải đậu chứ.'),
                ('linh', 'Em muốn món trà ô long đó có tên. Để mấy bạn khóa sau cũng được uống.'),
                ('nhi', 'Vậy thì ghi lên bảng menu nha: “Trà Mùa Thi”.'),
                ('me', 'Mùa thi năm sau, bàn cửa sổ vẫn để dành cho người cần.')]),
        ]),
    'grocery': dict(
        title='Cuốn sổ ghi nợ', emoji='📗',
        keepsake=dict(emoji='🔑', name='Chìa khóa tiệm Cô Ba', desc='Cô Ba giao chìa khóa tiệm cho bạn trông mấy hôm cô về quê.'),
        cast={'co_ba': _p('Cô Ba', '👩‍🦳', 'Chủ tiệm', 'grocery_npc_01'),
              'chi_lan': _p('Chị Lan', '🧵', 'Công nhân may', 'grocery_npc_03'),
              'be_ti': _p('Bé Tí', '👦', 'Học sinh lớp 9', 'grocery_npc_04'),
              'chu_bay': _p('Chú Bảy', '🛵', 'Xe ôm đầu hẻm', 'grocery_npc_02')},
        beats=[
            _b('Cuốn sổ bìa xanh', '📗', 'Dưới quầy có một cuốn sổ cũ mà Cô Ba giữ rất kỹ.', [
                ('co_ba', 'Con thấy cuốn sổ bìa xanh này không? Sổ ghi nợ của cả hẻm, hai chục năm rồi đó.'),
                ('co_ba', 'Ai khó thì cô cho ghi, tới kỳ lương thì trả. Hàng xóm với nhau mà con.'),
                ('chu_bay', 'Hồi xe chú hư máy, chú cũng ghi sổ Cô Ba cả tháng trời.'),
                ('me', 'Dạ, vậy con giữ sổ này cẩn thận giùm cô.')]),
            _b('Chị Lan mua chịu', '🧺', 'Hình như ở xưởng may có chuyện chậm lương.', [
                ('chi_lan', 'Tháng này xưởng chậm lương. Em cho chị ghi sổ gói mì với hộp sữa cho con nha.'),
                ('chi_lan', 'Chị ngại lắm, mà thằng nhỏ đang sốt, phải có sữa.'),
                ('co_ba', 'Con lo giùm cô nha, cô đang cân gạo.')],
                _c('Ghi sổ cho Chị Lan thế nào?',
                   _o('a', 'Ghi rõ ràng, hẹn ngày trả nhẹ nhàng', [('chi_lan', 'Có ngày hẹn rõ vậy chị yên tâm hơn. Lãnh lương là chị ghé liền.')], rel='chi_lan'),
                   _o('b', 'Ghi sổ và gửi thêm gói cháo cho bé', [('co_ba', 'Gói cháo đó cô tặng. Con bệnh thì ăn cháo cho mau khỏe.')], rel='co_ba'))),
            _b('Sổ mới cho tiệm', '✍️', 'Cuốn sổ bìa xanh sắp hết trang.', [
                ('me', 'Cô ơi, con chép lại sổ thành từng cột nha: tên, ngày, món, số tiền, đã trả chưa.'),
                ('be_ti', 'Để em kẻ thước cho! Thước của em thẳng nhất lớp đó.'),
                ('co_ba', 'Nhìn vô là biết ai còn bao nhiêu, khỏi phải lật tới lật lui.'),
                ('co_ba', 'Sổ cũ cô vẫn giữ nha. Trong đó có chữ của bao nhiêu người.')]),
            _b('Tiền trả đủ', '💵', 'Xưởng may sắp phát lương.', [
                ('chi_lan', 'Lương về rồi em! Tiền mì, tiền sữa, chị trả đủ nè.'),
                ('chi_lan', 'Còn mấy cái tạp dề này xưởng may dư, chị xin về tặng tiệm.'),
                ('me', 'Để con gạch dòng này trong sổ. Chữ “đã trả” đẹp nhất sổ luôn.'),
                ('co_ba', 'Mặc tạp dề mới vô, nhìn tiệm sáng hẳn.')]),
            _b('Chùm chìa khóa', '🔑', 'Cô Ba nói cuối tuần này muốn về quê thăm con gái.', [
                ('co_ba', 'Cuối tuần cô về quê thăm con gái hai bữa. Tiệm này cô giao con trông.'),
                ('co_ba', 'Chìa khóa đây. Cô tin con, vì con giữ sổ còn kỹ hơn cô.'),
                ('chu_bay', 'Có gì cứ kêu chú, chú đứng đầu hẻm cả ngày mà.'),
                ('be_ti', dict(male='Anh trông tiệm thì em ghé mua kẹo mỗi ngày luôn!',
                               female='Chị trông tiệm thì em ghé mua kẹo mỗi ngày luôn!',
                               none='Vậy em ghé mua kẹo mỗi ngày luôn!'))]),
        ]),
    'delivery': dict(
        title='Lá thư từ phương xa', emoji='✉️',
        keepsake=dict(emoji='🗼', name='Tấm bưu thiếp Osaka', desc='Tín gửi tặng “người đưa thư tốt bụng của bà”.'),
        cast={'ba_nguyet': _p('Bà Nguyệt', '👵', 'Bà cụ ở cuối hẻm'),
              'chi_hanh': _p('Chị Hạnh', '📋', 'Điều phối viên bưu cục', 'delivery_npc_07'),
              'ba_ut': _p('Bà Út', '🧓', 'Chủ tạp hóa trong hẻm', 'delivery_npc_04'),
              'tin': _p('Tín', '🎓', 'Cháu bà Nguyệt, du học ở Nhật')},
        beats=[
            _b('Bà hỏi thư', '👵', 'Có một bà cụ hay đứng chờ ở cổng cuối hẻm.', [
                ('ba_nguyet', 'Con ơi, hôm nay có thư của thằng Tín không con? Nó đi du học bên Nhật.'),
                ('me', 'Dạ hôm nay chưa có bà ơi. Có là con mang tới liền.'),
                ('chi_hanh', 'Bà Nguyệt đó, tuần nào cũng hỏi. Tuần nào có thư là bà vui cả tuần.')]),
            _b('Chưa có thư', '📭', 'Mấy tuần rồi chưa có thư từ Nhật.', [
                ('ba_nguyet', 'Hôm nay cũng chưa có hả con… Chắc nó bận học.'),
                ('ba_ut', 'Bà ngồi đây từ sáng. Ai chạy xe ngang cũng hỏi.'),
                ('ba_nguyet', 'Nó hiền lắm, hồi nhỏ ngày nào cũng xin bà kể chuyện mới chịu ngủ.')],
                _c('Bạn làm gì?',
                   _o('a', 'Dừng xe, ngồi nghe bà kể về Tín một lúc', [('ba_nguyet', 'Lâu lắm mới có người nghe bà kể trọn một câu chuyện. Con đi đường cẩn thận nghe.')]),
                   _o('b', 'Hứa hễ có thư là mang tới bà đầu tiên', [('ba_nguyet', 'Ừ, bà tin con. Bà để dành cho con trái ổi ngọt nhất trên cây.')]))),
            _b('Bưu kiện nhỏ từ Osaka', '📦', 'Bưu cục vừa nhận một kiện hàng quốc tế.', [
                ('chi_hanh', 'Có kiện từ Osaka gửi bà Nguyệt nè! Em giao đi, chị biết em mong kiện này lắm.'),
                ('ba_nguyet', 'Của thằng Tín! Mà mắt bà kém rồi, con đọc thư giùm bà nghe.'),
                ('tin', '“Bà ơi, con học tốt. Con làm thêm ở tiệm bánh, tối nào cũng nhớ canh chua của bà.”'),
                ('ba_nguyet', 'Cái thằng… Còn gửi cái khăn len nữa. Trời ở đây nóng muốn chết mà.')]),
            _b('Thư hồi âm', '✍️', 'Bà Nguyệt muốn gửi thư trả lời.', [
                ('ba_nguyet', 'Con viết giùm bà lá thư trả lời nha. Bà đọc, con viết.'),
                ('ba_nguyet', '“Tín ơi, bà khỏe. Cây ổi năm nay sai trái. Con nhớ ăn cơm cho đủ.”'),
                ('me', 'Dạ, con viết chữ to, thẳng hàng cho Tín dễ đọc.')],
                _c('Cuối thư, bạn…',
                   _o('a', 'Ghi đúng từng lời bà đọc, không thêm gì', [('ba_nguyet', 'Đúng giọng bà rồi. Nó đọc là biết bà nói liền.')]),
                   _o('b', 'Xin bà cho ghi thêm một dòng: “Bà vẫn khỏe, người đưa thư làm chứng”', [('ba_nguyet', 'Ghi đi con. Cho nó yên tâm mà học.')]))),
            _b('Tết này con về', '🎍', 'Hình như sắp có thư mới từ Nhật.', [
                ('chi_hanh', 'Thêm một thư từ Osaka! Lần này dày lắm nha.'),
                ('tin', '“Bà ơi, Tết này con về. Con đã mua vé rồi. Con cảm ơn người đưa thư đã đọc thư cho bà.”'),
                ('ba_nguyet', 'Nó về! Nó về ăn Tết với bà!'),
                ('ba_nguyet', 'Trong thư có tấm bưu thiếp, nó dặn gửi cho người đưa thư tốt bụng. Của con đó.'),
                ('ba_ut', 'Từ nay bà khỏi ngồi cổng chờ nữa rồi ha.')]),
        ]),
    # ------------------------------------------------------------ chương 2
    'cafe_bakery': dict(
        title='Hũ men của Chú Lâm', emoji='🫙',
        keepsake=dict(emoji='🫙', name='Hũ men cái “Bé Men”', desc='Chú Lâm nuôi hai mươi năm, nay giao lại cho bạn.'),
        cast={'chu_lam': _p('Chú Lâm', '👴', 'Khách quen 6 giờ sáng', 'cafe_bakery_npc_01'),
              'mo': _p('Mơ', '🧑‍🎓', 'Sinh viên tình nguyện', 'cafe_bakery_npc_03'),
              'ba_sau': _p('Bà Sáu', '👵', 'Khách lớn tuổi', 'cafe_bakery_npc_06')},
        beats=[
            _b('Người khách 6 giờ', '☕', 'Sáng nào cũng có một ông khách tới đúng 6 giờ.', [
                ('chu_lam', 'Cà phê đen, không đường. Bánh sừng bò nướng thêm nửa phút nữa.'),
                ('chu_lam', 'Vỏ phải kêu “rộp” khi cắn. Không kêu là chưa tới.'),
                ('mo', 'Chú Lâm đó. Sáng nào cũng đúng 6 giờ, trễ một phút là tiệm chưa mở, chú đứng chờ luôn.')]),
            _b('Vỏ bánh kêu rộp', '🥐', 'Chú Lâm hình như rất rành chuyện làm bánh.', [
                ('chu_lam', 'Hồi trẻ chú làm thợ bánh ba chục năm ở một lò bánh mì cũ ngoài phố.'),
                ('chu_lam', 'Bột mà vội là bánh biết liền. Nó xẹp cho mình coi.'),
                ('mo', 'Chú chỉ tụi con vài chiêu đi chú!')],
                _c('Bạn muốn…',
                   _o('a', 'Xin chú chỉ cách gấp bơ cho bánh nhiều lớp', [('chu_lam', 'Gấp ba, nghỉ lạnh, rồi gấp nữa. Nhớ tay lạnh, lòng không vội.')], rel='chu_lam'),
                   _o('b', 'Mời chú thêm ly cà phê, ngồi nghe chú kể chuyện lò bánh', [('chu_lam', 'Lâu rồi mới có người chịu nghe ông già này kể. Mai chú mang cái này cho coi.')], rel='chu_lam'))),
            _b('Hũ men cái', '🫙', 'Chú Lâm hứa mang một thứ đặc biệt tới tiệm.', [
                ('chu_lam', 'Hũ men cái chú nuôi hai chục năm. Làm bánh mì chua là phải có nó.'),
                ('chu_lam', 'Nuôi nó như nuôi mèo. Mỗi sáng cho ăn một muỗng bột, một muỗng nước.'),
                ('mo', 'Vậy mình đặt tên nó là “Bé Men” đi!'),
                ('me', 'Con hứa ngày nào cũng cho Bé Men ăn đúng giờ.')]),
            _b('Chú Lâm vắng mặt', '🏥', 'Sáng nay đã 6 giờ 15 mà chưa thấy Chú Lâm.', [
                ('mo', 'Ba bữa rồi không thấy Chú Lâm. Em lo quá.'),
                ('ba_sau', 'Ông Lâm đi mổ đầu gối, nằm viện rồi con. Ổng dặn đừng ai lo.'),
                ('me', 'Bé Men lên men đều lắm. Phải cho chú biết mới được.')],
                _c('Gửi gì vào viện cho Chú Lâm?',
                   _o('a', 'Ổ bánh mì chua đầu tiên từ Bé Men', [('ba_sau', 'Bà mang vô cho. Ổng cầm ổ bánh lên ngửi mà cười hoài.')], rel='chu_lam'),
                   _o('b', 'Một tấm ảnh Bé Men sủi bọt, kèm lời hỏi thăm', [('mo', 'Chú nhắn lại: “Bọt vậy là khỏe. Nhớ đừng để nó đói.”')], rel='chu_lam'))),
            _b('Ổ bánh đầu tiên', '🍞', 'Nghe nói Chú Lâm sắp xuất viện.', [
                ('chu_lam', 'Chú về rồi đây. Chống gậy thôi, chứ mũi thì vẫn thính.'),
                ('chu_lam', 'Vỏ giòn, ruột dai, chua vừa. Được rồi.'),
                ('chu_lam', 'Hũ men này giờ là của con. Chú già rồi, sáng chỉ muốn ngồi uống cà phê thôi.'),
                ('mo', 'Vậy mỗi sáng 6 giờ mình để dành cho chú một lát bánh nha!')]),
        ]),
    'florist': dict(
        title='Cành hướng dương thứ Sáu', emoji='🌻',
        keepsake=dict(emoji='🌻', name='Gói hạt giống hướng dương', desc='Hạt từ khu vườn nhỏ của Chú Phúc và Cô Hiền.'),
        cast={'chu_phuc': _p('Chú Phúc', '👴', 'Tài xế về hưu', 'florist_npc_06'),
              'co_hien': _p('Cô Hiền', '👵', 'Vợ Chú Phúc'),
              'ba_tam': _p('Bà Tám', '🧓', 'Hàng xóm lâu năm', 'florist_npc_07')},
        beats=[
            _b('Một cành hướng dương', '🌻', 'Có một ông khách chỉ mua đúng một cành hoa.', [
                ('chu_phuc', 'Cho chú một cành hướng dương. Một cành thôi con.'),
                ('chu_phuc', 'Gói giấy báo cũng được, miễn cành tươi.'),
                ('me', 'Dạ, con chọn cành bông to nhất cho chú.')]),
            _b('Vì sao là hướng dương', '💛', 'Thứ Sáu nào Chú Phúc cũng ghé.', [
                ('chu_phuc', 'Vợ chú, Cô Hiền, giờ hay quên lắm. Có bữa quên cả tên chú.'),
                ('chu_phuc', 'Mà hễ thấy hướng dương là bả cười. Hồi đám cưới bả cầm hướng dương.'),
                ('ba_tam', 'Hiền đó hả? Hồi xưa bán rau cạnh sạp tôi ngoài chợ. Cười đẹp nhất chợ.')],
                _c('Tuần này gói hoa thế nào?',
                   _o('a', 'Chọn cành tươi nhất, cắt chéo gốc cho lâu tàn', [('chu_phuc', 'Cành này để được cả tuần. Bả ngó nó hoài.')], rel='chu_phuc'),
                   _o('b', 'Kẹp thêm tấm thiệp nhỏ vẽ ông mặt trời', [('chu_phuc', 'Bả cầm tấm thiệp ngó hoài, rồi nói “ông mặt trời của tui”.')], rel='chu_phuc'))),
            _b('Cô Hiền ghé tiệm', '👵', 'Chú Phúc nói sẽ dẫn Cô Hiền đi dạo ngang tiệm.', [
                ('co_hien', 'Tiệm hoa đẹp quá. Mình vô đây lần nào chưa ông?'),
                ('chu_phuc', 'Tuần nào tui cũng vô mua hoa cho bà đó.'),
                ('ba_tam', 'Hiền! Nhớ tui không? Sạp rau ngoài chợ nè.'),
                ('co_hien', 'Chị Tám… Tay chị vẫn đeo cái vòng bạc đó hả?'),
                ('ba_tam', 'Còn nhớ! Còn nhớ cái vòng!')]),
            _b('Bốn mươi năm', '💐', 'Sắp tới một ngày kỷ niệm quan trọng.', [
                ('chu_phuc', 'Tuần sau là bốn chục năm ngày cưới. Chú muốn một bó giống hồi đó.'),
                ('chu_phuc', 'Hướng dương với cúc trắng. Hồi đó nghèo, bó có năm cành à.'),
                ('me', 'Để con làm bó thật giống ngày xưa.')],
                _c('Bó hoa kỷ niệm',
                   _o('a', 'Gói giấy kiếng, buộc nơ đỏ như ảnh cưới xưa', [('chu_phuc', 'Y chang! Y chang cái bó trong hình cưới.')], rel='chu_phuc'),
                   _o('b', 'Năm cành hướng dương, bốn mươi bông cúc trắng nhỏ', [('chu_phuc', 'Bốn mươi bông cúc, bốn mươi năm. Con khéo quá.')], rel='chu_phuc'))),
            _b('Tấm ảnh cưới', '📷', 'Chú Phúc hẹn ghé kể chuyện ngày kỷ niệm.', [
                ('chu_phuc', 'Hôm đó bả ôm bó hoa, rồi gọi tên chú. Gọi đúng tên luôn con.'),
                ('chu_phuc', 'Chú chụp lại rồi nè. Coi nè, bả cười y hồi bốn chục năm trước.'),
                ('co_hien', 'Ông Phúc nói tiệm này gói hoa đẹp nhất phố. Cô cảm ơn con.'),
                ('chu_phuc', 'Hạt hướng dương trong vườn nhà chú. Con trồng một chậu trước tiệm nghe.')]),
        ]),
    'mother_baby': dict(
        title='Chờ bé Bơ chào đời', emoji='🍼',
        keepsake=dict(emoji='🧸', name='Tấm ảnh bé Bơ đầy tháng', desc='Mai dán ảnh bé Bơ lên tường tiệm, cạnh kệ gấu bông.'),
        cast={'mai': _p('Mai', '🤰', 'Khách thường ghé', 'mother_baby_npc_03'),
              'an': _p('An', '🧑', 'Phụ việc', 'mother_baby_npc_04'),
              'linh': _p('Linh', '🎀', 'Bạn thân của Mai', 'mother_baby_npc_01'),
              'bac_tu': _p('Bác Tư', '👴', 'Hàng xóm', 'mother_baby_npc_02')},
        beats=[
            _b('Danh sách dài ngoằng', '📝', 'Có một chị khách đang cầm danh sách dài cả mét.', [
                ('mai', 'Mình mới có bầu tháng thứ năm. Đọc trên mạng thấy cái gì cũng cần hết trơn.'),
                ('mai', 'Máy hâm sữa, máy tiệt trùng, máy ru ngủ… Có cần hết không {anh}?'),
                ('an', 'Danh sách này dài hơn cả kệ hàng tiệm mình luôn.')]),
            _b('Món nào thật cần', '🍼', 'Mai quay lại, vẫn còn bối rối với danh sách.', [
                ('mai', 'Tối qua mình trằn trọc hoài. Sợ thiếu món gì cho con.'),
                ('me', 'Mình ngồi đọc lại danh sách từ từ nha. Món nào cần trước, món nào đợi được.'),
                ('an', 'Em pha trà cho chị Mai nha. Đọc danh sách dài vậy phải có trà.')],
                _c('Bạn giúp Mai thế nào?',
                   _o('a', 'Cùng Mai gạch bớt những món chưa cần', [('mai', 'Gạch xong nhẹ cả người. Tiền đó mình để dành mua sữa.')], rel='mai'),
                   _o('b', 'Chia danh sách mua dần theo từng tháng', [('mai', 'Chia tháng vậy dễ thở ghê. Mình dán lên tủ lạnh luôn.')], rel='mai'))),
            _b('Tiệc chờ bé', '🎈', 'Bạn bè của Mai muốn làm một bữa tiệc chờ bé.', [
                ('linh', 'Tụi mình làm tiệc chờ bé cho Mai. Tiệm gói giùm một giỏ quà thật xinh nha.'),
                ('an', 'Khăn sữa, bình nước, gấu bông, thêm tấm thiệp viết tay!'),
                ('linh', 'Mai nói bé tên ở nhà là Bơ. Vì Mai thèm bơ suốt mấy tháng nay.'),
                ('me', 'Vậy thiệp vẽ trái bơ luôn cho hợp.')]),
            _b('Tin nhắn lúc nửa đêm', '🌙', 'Ngày dự sinh của Mai đã tới gần.', [
                ('an', 'Có tin nhắn! Chồng chị Mai nhắn: bé Bơ chào đời rồi, ba ký hai, mẹ tròn con vuông!'),
                ('bac_tu', 'Mừng quá! Hẻm mình có thêm một đứa nhỏ.'),
                ('me', 'Mình gửi gì vào viện mừng Mai đây ta?')],
                _c('Món quà mừng',
                   _o('a', 'Một bộ quà nhỏ: khăn sữa và mũ len', [('an', 'Chị Mai gửi hình bé đội mũ len rồi nè. Dễ thương xỉu.')], rel='mai'),
                   _o('b', 'Một tấm thiệp cả tiệm cùng ký tên', [('an', 'Chị Mai nói sẽ dán tấm thiệp vào album đầu đời của bé.')], rel='mai'))),
            _b('Bé Bơ đầy tháng', '👶', 'Có người sắp bế bé tới thăm tiệm.', [
                ('mai', 'Bé Bơ đầy tháng rồi! Mình bế bé ghé chào tiệm nè.'),
                ('mai', 'Hồi đó không có {anh} chắc mình mua cả đống đồ không xài tới.'),
                ('linh', 'Chụp chung một tấm đi! Cả tiệm luôn!'),
                ('mai', 'Tấm này tặng tiệm. Để bé Bơ lúc nào cũng ở đây.')]),
        ]),
    'restaurant': dict(
        title='Tô mì cấp 0', emoji='🌶️',
        keepsake=dict(emoji='🍜', name='Món “Mì cấp 0 Cần Thơ”', desc='Món mới trên menu, nấu theo vị canh quê của mẹ Minh Béo.'),
        cast={'minh_beo': _p('Minh Béo', '🧑‍🎓', 'Sinh viên', 'restaurant_npc_05'),
              'anh_son': _p('Anh Sơn', '🧔', 'Khách quen', 'restaurant_npc_01'),
              'ba_hoa': _p('Bà Hoa', '👵', 'Khách lớn tuổi', 'restaurant_npc_06'),
              'me_minh': _p('Cô Út', '👩', 'Mẹ Minh Béo, ở Cần Thơ')},
        beats=[
            _b('Thử thách cấp 7', '🔥', 'Một cậu sinh viên đang dựng điện thoại lên quay video.', [
                ('minh_beo', 'Cho em một tô cấp 7! Em quay video “thử thách mì cay” đăng mạng.'),
                ('anh_son', 'Cấp 7 hả? Tui ăn cấp 3 thôi mà còn chảy nước mắt đó nhóc.'),
                ('minh_beo', 'Không sao! Em ăn cay giỏi lắm!')]),
            _b('Nước mắt và ly trà đá', '😭', 'Minh Béo quay lại, lần này đi một mình.', [
                ('minh_beo', 'Hôm bữa em bỏ dở tô cấp 7… Video bị chọc quá trời.'),
                ('anh_son', 'Ăn cay đâu phải để chứng minh gì đâu nhóc.'),
                ('minh_beo', 'Mà em lỡ hứa với cả lớp là ăn hết rồi…')],
                _c('Bạn nói gì với Minh?',
                   _o('a', 'Rót ly sữa lạnh, cười: “Cay là để ngon, không phải để thắng”', [('minh_beo', 'Nghe {anh} nói vậy em thấy nhẹ nhõm. Hôm nay em ăn cấp 2 thôi.')], rel='minh_beo'),
                   _o('b', 'Gợi ý bắt đầu lại từ cấp 3, tăng dần mỗi tuần', [('minh_beo', 'Tập từ từ ha. Vậy tuần sau em lên cấp 4!')], rel='minh_beo'))),
            _b('Nhớ nhà', '🏠', 'Tối muộn, Minh Béo ngồi lại lâu hơn mọi khi.', [
                ('minh_beo', 'Thiệt ra em không mê cay lắm. Em ở Cần Thơ lên, nhớ nhà quá nên kiếm cái gì mạnh mạnh ăn cho quên.'),
                ('minh_beo', 'Em nhớ canh chua bông điên điển của má.'),
                ('ba_hoa', 'Nhớ nhà thì ăn món nhà, con à. Cay quá lại càng nhớ.'),
                ('me', 'Để mình thử nấu một tô cho em. Không cay, mà có vị quê.')]),
            _b('Tô mì cấp 0', '🍜', 'Bếp đang thử một nồi nước dùng mới.', [
                ('me', 'Nước dùng xương hầm ngọt, chút me chua, rau ăn kèm kiểu miền Tây.'),
                ('minh_beo', 'Trời… giống canh của má em quá.'),
                ('anh_son', 'Cho tui một tô cấp 0 luôn. Nhìn ngon quá trời.')],
                _c('Rau ăn kèm cho tô cấp 0',
                   _o('a', 'Bông điên điển và rau đắng như ở quê Minh', [('minh_beo', 'Có bông điên điển luôn! Em chụp gửi má liền.')], rel='minh_beo'),
                   _o('b', 'Rau muống bào và giá, ai ăn cũng quen', [('ba_hoa', 'Món này bà ăn được nè. Không cay mà đậm đà.')], rel='ba_hoa'))),
            _b('Má lên thăm', '👩', 'Nghe nói mẹ của Minh Béo sắp lên thành phố.', [
                ('minh_beo', 'Má em lên thăm nè! Em dẫn má tới ăn thử tô cấp 0.'),
                ('me_minh', 'Nước dùng này có hồn đó con. Nấu kiểu người thương người ăn.'),
                ('me_minh', 'Cảm ơn con đã cho thằng Minh chỗ để nhớ nhà mà không buồn.'),
                ('minh_beo', 'Bảng menu ghi tên món đi {anh}: “Mì cấp 0 Cần Thơ”!')]),
        ]),
    # ------------------------------------------------------------ chương 3
    'pet_care': dict(
        title='Chú chó tên Mực', emoji='🐕',
        keepsake=dict(emoji='🦴', name='Vòng cổ nhỏ của Mực', desc='Bé Na tặng lại chiếc vòng cổ đầu tiên của Mực.'),
        cast={'chi_may': _p('Chị Mây', '🧡', 'Nhóm cứu hộ thú lạc', 'pet_care_npc_16'),
              'bs_hoa': _p('Bác sĩ Hòa', '🩺', 'Thú y phường', 'pet_care_npc_14'),
              'be_na': _p('Bé Na', '👧', 'Cô bé 9 tuổi', 'pet_care_npc_05'),
              'muc': _p('Mực', '🐕', 'Chó lạc được cứu')},
        beats=[
            _b('Bé chó run rẩy', '🐕', 'Nhóm cứu hộ vừa tìm thấy một chú chó dưới gầm cầu.', [
                ('chi_may', 'Tụi chị mới tìm được bé này dưới gầm cầu. Đen thui nên đặt tên là Mực.'),
                ('chi_may', 'Nó sợ nước lắm. Tắm giúp chị mà nhẹ tay nha.'),
                ('muc', 'Ư… ư…'),
                ('me', 'Không sao đâu Mực. Ở đây không ai làm em đau đâu.')]),
            _b('Không ép', '🫧', 'Mực vẫn trốn vào góc mỗi khi thấy vòi nước.', [
                ('chi_may', 'Mực cứ thấy vòi nước là chui vào góc run lẩy bẩy.'),
                ('me', 'Mình không ép. Để từ từ Mực tự quen.'),
                ('muc', 'Ư…')],
                _c('Làm quen với Mực',
                   _o('a', 'Ngồi xuống sàn, để Mực tự lại gần', [('chi_may', 'Mười phút sau nó dụi đầu vào tay em luôn. Chị suýt khóc.')], rel='chi_may'),
                   _o('b', 'Lau người bằng khăn ấm thay vì tắm vòi', [('chi_may', 'Khăn ấm thì nó chịu nằm yên. Còn ngủ gục luôn nữa.')], rel='chi_may'))),
            _b('Bác sĩ Hòa khám', '🩺', 'Đến ngày đưa Mực đi khám tổng quát.', [
                ('bs_hoa', 'Mực khỏe. Hơi gầy, cần tiêm ngừa đủ mũi, ăn đều là lên cân.'),
                ('muc', 'Gâu!'),
                ('bs_hoa', 'Lần đầu thấy nó vẫy đuôi đó. Nó chọn người rồi.'),
                ('chi_may', 'Giờ chỉ còn tìm cho Mực một mái nhà.')]),
            _b('Bé Na và Mực', '👧', 'Có một cô bé cứ đứng ngoài cửa kính nhìn vào.', [
                ('be_na', 'Mẹ ơi, con muốn nuôi Mực! Con hứa cho Mực ăn mỗi ngày!'),
                ('be_na', dict(male='Anh ơi, Mực có thích con không?', female='Chị ơi, Mực có thích con không?', none='Mực có thích con không?')),
                ('me', 'Mẹ Na còn lo, nuôi chó là chuyện cả nhà mà.')],
                _c('Giúp mẹ Na yên tâm',
                   _o('a', 'Kể cho mẹ Na nghe cách chăm Mực mỗi ngày', [('be_na', 'Mẹ nói nghe rõ vậy thì mẹ yên tâm rồi!')], rel='be_na'),
                   _o('b', 'Mời hai mẹ con ghé chơi với Mực thêm vài lần', [('be_na', 'Tuần này con ghé ba lần luôn! Mực nhớ tên con rồi.')], rel='be_na'))),
            _b('Về nhà mới', '🏡', 'Chị Mây nói giấy nhận nuôi đã sẵn sàng.', [
                ('chi_may', 'Giấy nhận nuôi ký rồi. Mực có nhà rồi em ơi!'),
                ('be_na', 'Đây là vòng cổ đầu tiên của Mực. Con tặng lại tiệm để nhớ Mực nha.'),
                ('muc', 'Gâu! Gâu!'),
                ('me', 'Nhớ đưa Mực ghé tắm nha. Lần này có vòi nước cũng không sợ nữa.')]),
        ]),
    'salon': dict(
        title='Mái tóc bạc ngày cưới', emoji='💇',
        keepsake=dict(emoji='📸', name='Ảnh cưới ba thế hệ', desc='Cô Ngọc, con gái và cô dâu Trâm, ai cũng làm tóc ở Salon Tóc Gió.'),
        cast={'co_ngoc': _p('Cô Ngọc', '👩‍🦳', 'Giáo viên về hưu', 'salon_npc_03'),
              'ba_luu': _p('Bà Lựu', '🧓', 'Khách quen lắm chuyện', 'salon_npc_05'),
              'tram': _p('Cô dâu Trâm', '👰', 'Cháu gái Cô Ngọc', 'salon_npc_10')},
        beats=[
            _b('Chiếc mũ len', '🧶', 'Một cô khách lớn tuổi đội mũ len giữa trời nắng.', [
                ('co_ngoc', 'Tóc cô mới mọc lại sau đợt điều trị. Lởm chởm lắm con.'),
                ('co_ngoc', 'Cô đội mũ hoài, mà trời nắng quá.'),
                ('me', 'Tóc mới mọc mềm lắm cô. Để con xem thử, không làm gì cô chưa muốn đâu.')]),
            _b('Cắt cho gọn', '✂️', 'Cô Ngọc quay lại, lần này bỏ mũ ra.', [
                ('co_ngoc', 'Hôm nay cô dám bỏ mũ ra rồi. Con làm sao cho gọn giùm cô.'),
                ('ba_luu', 'Ngọc đó hả? Cô giáo dạy văn của nửa cái phố này đó!'),
                ('me', 'Dạ, cô cứ ngồi thoải mái. Mình từ từ thôi cô.')],
                _c('Kiểu tóc cho Cô Ngọc',
                   _o('a', 'Tỉa nhẹ cho đều, giữ nguyên độ dài', [('co_ngoc', 'Đều rồi, nhìn hiền hẳn. Mai cô đi chợ không đội mũ nữa.')], rel='co_ngoc'),
                   _o('b', 'Gợi ý kiểu tém ngắn khỏe khoắn', [('co_ngoc', 'Trời, cô trẻ ra chục tuổi! Hồi con gái cô cũng để tóc tém.')], rel='co_ngoc'))),
            _b('Chuyện trong ghế gội', '💬', 'Bà Lựu đang kể chuyện rôm rả ở ghế gội.', [
                ('ba_luu', 'Hồi đó Ngọc dạy thằng con tui đọc thơ. Giờ nó làm nhà báo đó.'),
                ('co_ngoc', 'Thằng Tuấn hả? Viết văn hay mà hay đi học trễ.'),
                ('ba_luu', 'Còn nhớ luôn! Bà này nhớ dai hơn tui nữa.'),
                ('co_ngoc', 'Làm tóc ở đây vui, cô ghé thường hơn.')]),
            _b('Đám cưới cháu gái', '💍', 'Salon nhận lịch hẹn làm tóc cho một đám cưới.', [
                ('tram', 'Em là Trâm, cháu ngoại của bà Ngọc. Bà giới thiệu em tới làm tóc cưới.'),
                ('co_ngoc', 'Ngày cưới con Trâm, cô cũng muốn làm tóc đàng hoàng.'),
                ('tram', 'Bà có mái tóc bạc đẹp lắm. Em muốn bà nổi bật hơn cả em luôn!')],
                _c('Tóc cưới cho Cô Ngọc',
                   _o('a', 'Giữ màu bạc tự nhiên, cài một nhành hoa nhỏ', [('tram', 'Bà giống bà tiên trong truyện cổ tích luôn!')], rel='co_ngoc'),
                   _o('b', 'Uốn phồng nhẹ cho đồng bộ với tóc cô dâu', [('co_ngoc', 'Hai bà cháu tóc giống nhau, chụp hình đẹp nghe con.')], rel='tram'))),
            _b('Ảnh cưới ba thế hệ', '📸', 'Có người mang ảnh cưới tới khoe.', [
                ('tram', 'Ảnh cưới nè! Tấm đẹp nhất là tấm có bà.'),
                ('co_ngoc', 'Cả nhà khen tóc cô. Có đứa còn hỏi cô đi làm ở đâu.'),
                ('co_ngoc', 'Cô nói: ở tiệm có đứa nhỏ hỏi kỹ lắm rồi mới dám cắt.'),
                ('ba_luu', 'Treo tấm này lên tường đi, cho khách coi.')]),
        ]),
    'clothing': dict(
        title='Tiệm may của mẹ', emoji='🧵',
        keepsake=dict(emoji='🪡', name='Cây kéo cắt vải của Bà Tư', desc='Bà Tư trao cây kéo cũ khi tiệm mới treo bảng hiệu “Tiệm Áo Chỉ Mây”.'),
        cast={'vy': _p('Chị Vy', '👩', 'Chủ tiệm', 'clothing_npc_01'),
              'batu': _p('Bà Tư', '👵', 'Thợ may, mẹ chị Vy', 'clothing_npc_08'),
              'tuan': _p('Tuấn', '🧑‍🎓', 'Sinh viên năm cuối', 'clothing_npc_03')},
        beats=[
            _b('Chìa khóa tiệm cũ', '🗝️', 'Chị Vy đứng trước tấm bảng “May đo” đã bạc màu.', [
                ('vy', 'Hồi nhỏ chị ngủ trưa dưới cái bàn cắt vải này đó {anh}.'),
                ('batu', 'Mẹ may ở đây ba chục năm. Giờ con Vy muốn bán đồ may sẵn.'),
                ('vy', 'Con giữ cái máy may của mẹ ở gian bên. Tiệm mới mà vẫn là tiệm mình.'),
                ('me', 'Để em phụ chị. Có gì cần sửa đồ mình còn có Bà Tư.')]),
            _b('Bài học thước dây', '📏', 'Bà Tư ngoắc bạn vào gian bên.', [
                ('batu', 'Lại đây bà chỉ. Đo vai, đo ngực, đo eo, đo hai lần.'),
                ('batu', 'Khách nói size gì cũng nghe, nhưng tin cái thước dây.'),
                ('me', 'Dạ, đo hai lần, cắt một lần.')],
                _c('Bà Tư đưa thước dây',
                   _o('a', 'Xin bà dạy thêm cách lên lai quần', [('batu', 'Được. Gấp mép hai lần, may mũi nhỏ, ủi cho phẳng.')], rel='batu'),
                   _o('b', 'Nhờ bà đo thử cho mình một lần', [('batu', 'Vai con lệch chút xíu. Người ta ai cũng có chỗ lệch, áo phải chiều người.')], rel='batu'))),
            _b('Chiếc sơ mi đầu tiên', '👔', 'Tuấn ghé tiệm, ôm tập hồ sơ xin việc.', [
                ('tuan', 'Chị ơi, em sắp phỏng vấn mà chỉ có áo thun thôi.'),
                ('vy', 'Tuấn đưa cái ví coi, mình chọn cái vừa túi tiền trước.'),
                ('me', 'Sơ mi trắng, vừa vai là đủ tự tin rồi.')],
                _c('Tuấn còn thiếu cà vạt',
                   _o('a', 'Mượn cà vạt cũ của Bà Tư', [('batu', 'Cà vạt ông nhà bà để dành, đeo đi cho may mắn nghe con.')], rel='tuan'),
                   _o('b', 'Thắt lưng tiệm tặng kèm', [('vy', 'Coi như quà tiệm mừng Tuấn đi làm. Nhớ quay lại khoe nha!')], rel='tuan'))),
            _b('Bảng hiệu mới', '🪧', 'Có tiếng khoan tường trước cửa tiệm.', [
                ('vy', 'Bảng “Tiệm Áo Chỉ Mây” lên rồi nè! Chỉ là sợi chỉ, Mây là tên mẹ hồi con gái.'),
                ('batu', 'Con Vy này… đặt tên mà không hỏi mẹ.'),
                ('batu', 'Đẹp. Mà vẫn là tiệm của mình.'),
                ('tuan', 'Chị ơi em đậu rồi! Em qua khoe nè!')]),
            _b('Cây kéo của Bà Tư', '🪡', 'Bà Tư gói một thứ trong khăn vải.', [
                ('batu', 'Cây kéo này theo bà từ hồi mới học may.'),
                ('batu', 'Bà già rồi, tay run. Con giữ đi, nhớ đo hai lần.'),
                ('vy', 'Mẹ chưa từng cho ai đụng vô cây kéo đó đâu {anh}.'),
                ('me', 'Con cảm ơn bà. Con sẽ giữ tiệm cho đàng hoàng.')]),
        ]),
    'pet_shop': dict(
        title='Tiệm thú nhỏ đổi nếp', emoji='🐠',
        keepsake=dict(emoji='🪧', name='Tấm biển “Hỏi kỹ rồi mới bán”', desc='Chú Út tự tay viết, treo ngay trên quầy tính tiền.'),
        cast={'nha': _p('Nhã', '🩺', 'Cháu gái chú Út, sinh viên thú y', 'pet_shop_npc_01'),
              'chu_ut': _p('Chú Út', '👴', 'Chủ tiệm cũ', 'pet_shop_npc_02'),
              'bin': _p('Bé Bin', '🧒', 'Cậu bé lớp 4 mê hamster', 'pet_shop_npc_05'),
              'khanh': _p('Anh Khánh', '🧡', 'Nhóm cứu hộ Chân Nhỏ', 'pet_shop_npc_07')},
        beats=[
            _b('Tiệm cũ của chú Út', '🐟', 'Nhã đứng lau từng tấm kính bể cá đục mờ.', [
                ('nha', 'Tiệm này chú Út mở ba mươi năm rồi đó {anh}. Hồi nhỏ em ngồi đây coi cá cả buổi.'),
                ('chu_ut', 'Khách hỏi gì thì bán nấy. Hỏi han chi cho mất khách.'),
                ('nha', 'Em thì muốn khác: bán cho đúng bé, giao cho đúng người.'),
                ('me', 'Vậy mình làm từng chút một. Bắt đầu từ mấy cái bể này.')]),
            _b('Cái rổ giảm giá', '🥫', 'Chú Út đang xếp thêm mấy lon pate vào cái rổ trước quầy.', [
                ('chu_ut', 'Lon nào cận ngày thì thả vô đây, bán rẻ, khách mê lắm.'),
                ('nha', 'Chú ơi, có lon quá hạn cả tuần rồi, lon còn phồng nữa.'),
                ('chu_ut', 'Thì… bán rẻ mà.')],
                _c('Làm gì với cái rổ?',
                   _o('a', 'Dán nhãn ngày lên từng lon, bỏ riêng lon quá hạn', [('chu_ut', 'Ờ… có nhãn nhìn cũng đàng hoàng hơn.')], rel='chu_ut'),
                   _o('b', 'Kể chú nghe chuyện con mèo ăn pate quá hạn phải đi cấp cứu', [('chu_ut', 'Trời đất. Thôi, cái rổ đó để chú dẹp.')], rel='chu_ut'))),
            _b('Con heo đất của Bin', '🐹', 'Một cậu bé ôm con heo đất đứng trước chuồng hamster.', [
                ('bin', 'Con để dành cả năm đó! Con muốn mua một bé hamster.'),
                ('nha', 'Mẹ Bin biết chưa nè?'),
                ('bin', 'Dạ… chưa. Con định làm mẹ bất ngờ.')],
                _c('Nói gì với Bin?',
                   _o('a', 'Hẹn Bin về hỏi mẹ, mai hai mẹ con cùng ghé', [('bin', 'Mai con dẫn mẹ tới! Anh chị giữ bé hamster má phính giùm con nha!')], rel='bin'),
                   _o('b', 'Cho Bin cầm thử hamster, dặn cách chăm để về kể mẹ', [('bin', 'Nó mềm quá trời! Con về kể mẹ liền.')], rel='bin'))),
            _b('Góc nhận nuôi', '🏡', 'Anh Khánh chở tới một lồng mèo con và một tấm bảng gỗ.', [
                ('khanh', 'Nhóm Chân Nhỏ xin một góc nhỏ trong tiệm. Mèo con, cún con về nhà mới qua đây.'),
                ('chu_ut', 'Cho không thì tiệm lời gì?'),
                ('nha', 'Người nhận nuôi sẽ mua hạt, mua cát, mua vòng cổ ở tiệm mình. Mà quan trọng là các bé có nhà.'),
                ('chu_ut', 'Thôi được. Kê cái góc cạnh cửa sổ, chỗ đó mát.')]),
            _b('Ngày hội nhận nuôi', '🎉', 'Băng rôn treo trước cửa, cả xóm kéo tới.', [
                ('khanh', 'Bốn bé có nhà mới trong một buổi sáng! Chưa bao giờ nhóm làm được vậy.'),
                ('bin', 'Bánh Bao nhà con cũng tới dự nè!'),
                ('chu_ut', 'Chú viết tấm biển này treo trên quầy: “Hỏi kỹ rồi mới bán.”'),
                ('nha', 'Chú Út mà cũng chịu đổi nếp. {Anh} thấy chưa?'),
                ('me', 'Tiệm vẫn là tiệm của chú, chỉ là các bé được thương đúng cách hơn.')]),
        ]),
    'repair': dict(
        title='Chiếc radio của Ông Bảy', emoji='📻',
        keepsake=dict(emoji='💡', name='Bóng đèn radio cũ', desc='Chiếc đèn điện tử cháy, Ông Bảy tặng lại làm kỷ niệm.'),
        cast={'ong_bay': _p('Ông Bảy', '👴', 'Hưu trí, hàng xóm', 'repair_npc_02'),
              'chu_tu': _p('Chú Tư', '👨‍🔧', 'Chủ tiệm'),
              'be_ngan': _p('Bé Ngân', '👩‍🎓', 'Sinh viên năm hai', 'repair_npc_03'),
              'lam': _p('Lâm Linh Kiện', '📦', 'Mối buôn linh kiện', 'repair_npc_07')},
        beats=[
            _b('Cái radio gỗ', '📻', 'Có một ông cụ ôm một chiếc hộp gỗ vào tiệm.', [
                ('ong_bay', 'Cái radio này của bà nhà tôi. Bà mất rồi.'),
                ('ong_bay', 'Chiều nào tôi cũng muốn nghe cải lương, như hồi bà còn ngồi đây.'),
                ('chu_tu', 'Đồ xưa quá. Để lại đây, tụi này coi thử.')]),
            _b('Chú Tư lắc đầu', '🔧', 'Chú Tư đã mở nắp chiếc radio ra xem.', [
                ('chu_tu', 'Đèn điện tử cháy rồi. Loại này giờ hiếm lắm.'),
                ('ong_bay', 'Vậy là… không nghe được nữa hả con?'),
                ('chu_tu', 'Chú không hứa bừa đâu. Con nói với ông đi, con là người nhận đồ mà.')],
                _c('Bạn nói với Ông Bảy…',
                   _o('a', '“Con hứa sẽ đi tìm linh kiện cho ông.”', [('ong_bay', 'Ừ. Ông chờ được. Bà nhà ông cũng hay chờ ông vậy đó.')], rel='ong_bay'),
                   _o('b', '“Nói thật là khó ông ạ, nhưng tiệm sẽ thử hết cách.”', [('ong_bay', 'Nói thật vậy ông thích. Thợ nói thật là thợ tốt.')], rel='ong_bay'))),
            _b('Chợ linh kiện', '🔎', 'Tiệm đang đi tìm một bóng đèn điện tử đời cũ.', [
                ('lam', 'Kiếm được rồi! Đèn cũ tháo máy, còn tốt. Mười năm mới gặp một cái.'),
                ('be_ngan', 'Em tìm được sơ đồ mạch trên diễn đàn nước ngoài. In ra rồi nè.'),
                ('chu_tu', 'Có sơ đồ, có đèn. Giờ tới tay nghề.')]),
            _b('Tiếng rè đầu tiên', '⚡', 'Chiếc radio sắp được hàn lại.', [
                ('me', 'Hàn xong mối cuối rồi. Chú Tư, con bật thử nha.'),
                ('chu_tu', 'Bật đi. Tay run là tại hồi hộp thôi.'),
                ('be_ngan', 'Nó rè rè kìa! Có tiếng rồi!'),
                ('chu_tu', 'Được đó. Giờ thì chú tin con làm được nghề này rồi.')]),
            _b('Vọng cổ buổi chiều', '🎶', 'Đến lúc trả radio cho Ông Bảy.', [
                ('ong_bay', 'Đúng đài này. Chiều nào bà cũng mở đài này.'),
                ('ong_bay', 'Nghe như bà còn ngồi đây.'),
                ('ong_bay', 'Bóng đèn cũ cháy đó, con giữ đi. Nó chở bài hát của bà nhà ông mấy chục năm.'),
                ('chu_tu', 'Món này sửa không lấy tiền công. Tiệm mình nhận vậy đủ rồi.')]),
        ]),
    'farm': dict(
        title='Mùa mưa trên Đồi Gió', emoji='⛈️',
        keepsake=dict(emoji='📜', name='Giấy chứng nhận hữu cơ đầu tiên', desc='Lồng khung treo trong kho, cạnh áo mưa của Chú Tám.'),
        cast={'chu_tam': _p('Chú Tám', '👨‍🌾', 'Tổ trưởng HTX rau', 'farm_npc_01'),
              'chi_hanh': _p('Chị Hạnh', '👩‍🍳', 'Bếp trưởng Bếp Mây', 'farm_npc_02'),
              'be_mit': _p('Bé Mít', '👧', 'Học sinh lớp 5', 'farm_npc_05'),
              'anh_tuan': _p('Anh Tuấn', '🚚', 'Thương lái', 'farm_npc_04')},
        beats=[
            _b('Đất đồi', '🌱', 'Chú Tám có chuyện muốn nói về luống đất.', [
                ('chu_tam', 'Đất đồi này bạc màu lâu rồi. Làm hữu cơ thì chậm, nhưng đất nó nhớ ơn.'),
                ('chu_tam', 'Phủ rơm, ủ phân, trồng xen. Ba mùa mới thấy khác.'),
                ('be_mit', 'Con thấy giun đất nè! Chú Tám nói có giun là đất khỏe.'),
                ('me', 'Vậy mình làm từng luống một, chú chỉ con nha.')]),
            _b('Tin bão', '🌧️', 'Đài báo sắp có mưa lớn kéo dài.', [
                ('chu_tam', 'Đài báo tuần này mưa to, gió giật. Rau non chịu không nổi đâu.'),
                ('chu_tam', 'Còn hai ngày. Con tính làm gì trước?'),
                ('be_mit', 'Con phụ được! Con khiêng cọc tre được đó!')],
                _c('Chuẩn bị cho cơn bão',
                   _o('a', 'Dựng mái che lưới cho luống rau non', [('chu_tam', 'Mái che vững đó. Gió lớn cỡ nào rau cũng còn chỗ núp.')], rel='chu_tam'),
                   _o('b', 'Đào rãnh thoát nước quanh các luống', [('chu_tam', 'Đất đồi mà ngập là thối rễ. Đào rãnh là khôn đó con.')], rel='chu_tam'))),
            _b('Đêm mưa gió', '⛈️', 'Mây đen đã kéo tới Đồi Gió.', [
                ('be_mit', 'Gà sổ chuồng hết rồi! Con phụ lùa gà vô nha!'),
                ('chu_tam', 'Mái che còn đứng, rau non vẫn sống. May quá.', ('farm_2', 'a')),
                ('chu_tam', 'Nước thoát hết theo rãnh, không luống nào ngập. May quá.', ('farm_2', 'b')),
                ('chu_tam', 'Mất mấy luống cải ngoài bìa. Không sao, gieo lại được.'),
                ('me', 'Sáng mai con gieo lại liền. Đất còn là còn rau.')]),
            _b('Thương lái ép giá', '⚖️', 'Có xe tải của thương lái đậu dưới chân đồi.', [
                ('anh_tuan', 'Sau bão rau khan. Anh mua hết, giá rẻ thôi, dán nhãn “rau hữu cơ” bán cho lẹ.'),
                ('me', 'Rau của con chưa có chứng nhận, anh ạ. Dán nhãn vậy là nói sai.'),
                ('chi_hanh', 'Bếp Mây cũng đang cần rau đó em. Chị lấy đúng giá, ghi đúng là rau nhà trồng.')],
                _c('Bán rau sau bão',
                   _o('a', 'Giữ rau cho bếp của Chị Hạnh, ghi đúng nhãn', [('chi_hanh', 'Rau này chị ghi hẳn lên menu: “Rau Đồi Gió, nhà trồng”.')], rel='chi_hanh'),
                   _o('b', 'Bán bớt cho Anh Tuấn, nhưng ghi rõ “chưa chứng nhận”', [('anh_tuan', 'Ờ… ghi vậy cũng được. Nói thật thì mối lâu. Anh gửi tiền cọc đây.')], rel='chu_tam', coins=8)),
                days=6, served=14, gap=1),
            _b('Giấy chứng nhận đầu tiên', '📜', 'Đoàn kiểm tra hữu cơ sắp lên đồi.', [
                ('chu_tam', 'Đoàn kiểm tra xem đất, xem sổ ghi chép, xem cả chuồng gà. Đạt hết!'),
                ('chu_tam', 'Giấy chứng nhận đầu tiên của Đồi Gió. Ba mùa, một cơn bão, đất nhớ ơn thật.'),
                ('chi_hanh', 'Tuần sau Bếp Mây in chữ “Rau hữu cơ Đồi Gió” lên menu.'),
                ('be_mit', 'Con viết bài văn “Nông trại của em” được mười điểm đó!')],
                days=10, served=24, gap=2),
        ]),
    'homestay': dict(
        title='Căn phòng số 3', emoji='🗝️',
        keepsake=dict(emoji='📖', name='Trang sổ khách phòng số 3', desc='Mười hai năm, mười hai dòng chữ của Cô Diệp và Chú Khang.'),
        cast={'co_diep': _p('Cô Diệp', '👵', 'Khách lớn tuổi', 'homestay_npc_03'),
              'chu_khang': _p('Chú Khang', '👴', 'Chồng Cô Diệp'),
              'ong_lam': _p('Ông Lâm', '🧓', 'Hàng xóm kiêm khách quen', 'homestay_npc_06')},
        beats=[
            _b('Khách cũ của phòng 3', '🗝️', 'Ông Lâm nói tuần này có hai vị khách rất đặc biệt.', [
                ('ong_lam', 'Tuần này đôi vợ chồng già lại lên đó. Năm nào cũng xin phòng số 3, cửa sổ nhìn đồi thông.'),
                ('co_diep', 'Năm thứ mười hai rồi đó con. Phòng số 3 còn trống không?'),
                ('chu_khang', 'Bà nhà tôi nói ngủ phòng khác là không ngủ được.'),
                ('me', 'Dạ còn. Phòng số 3 để dành cho cô chú mà.')]),
            _b('Tấm ảnh trên bậu cửa', '🖼️', 'Cô Diệp đặt một tấm ảnh cũ lên bậu cửa sổ.', [
                ('co_diep', 'Ảnh này chụp ở đúng cửa sổ này, mười hai năm trước. Hồi đó tụi cô mới cưới.'),
                ('chu_khang', 'Cưới muộn lắm con. Sáu chục tuổi mới cưới. Nên năm nào cũng phải đi trăng mật bù.'),
                ('ong_lam', 'Năm nào tôi cũng qua uống trà với hai ông bà. Thành lệ rồi.')],
                _c('Chuẩn bị gì cho phòng số 3?',
                   _o('a', 'Cắm bình hoa dã quỳ trên bậu cửa', [('co_diep', 'Dã quỳ! Năm đầu tiên ngoài đồi cũng vàng rực vậy đó.')], rel='co_diep'),
                   _o('b', 'Pha sẵn ấm trà atiso nóng lúc tối', [('chu_khang', 'Trà nóng mà ngồi ngó đồi thông. Còn gì bằng.')], rel='co_diep'))),
            _b('Chú Khang ốm', '🤒', 'Đêm qua trời trở lạnh bất ngờ.', [
                ('co_diep', 'Ông nhà cô cảm lạnh rồi. Ho cả đêm.'),
                ('ong_lam', 'Để tôi đem qua chai dầu gừng. Người Đà Lạt ai cũng có.'),
                ('me', 'Con nấu nồi cháo gừng, lát bưng lên phòng cho chú.'),
                ('chu_khang', 'Chén cháo này ngon hơn khách sạn năm sao đó.')]),
            _b('Bốn mươi năm quen nhau', '🎂', 'Cô Diệp thì thầm nhờ một việc bí mật.', [
                ('co_diep', 'Mai là bốn chục năm ngày cô với ông quen nhau. Ông quên rồi, cô muốn làm ông bất ngờ.'),
                ('ong_lam', 'Bất ngờ thì phải có tôi. Tôi đàn được bài “Còn chút gì để nhớ”.'),
                ('me', 'Dạ, con lo phần còn lại. Chú Khang sẽ không đoán ra đâu.')],
                _c('Bất ngờ cho Chú Khang',
                   _o('a', 'Bày bàn trà nhỏ dưới gốc thông, có bánh kem', [('chu_khang', 'Bà còn nhớ hả? Tôi tưởng mình tôi nhớ…')], rel='co_diep'),
                   _o('b', 'Treo dây đèn vàng quanh cửa sổ phòng 3', [('chu_khang', 'Cửa sổ này sáng y như đêm đầu tiên.')], rel='co_diep'))),
            _b('Hẹn năm sau', '📅', 'Cô chú sắp trả phòng.', [
                ('co_diep', 'Tụi cô đặt luôn phòng số 3 cho năm sau nha con.'),
                ('chu_khang', 'Năm nào còn đi được là còn lên.'),
                ('co_diep', 'Cô viết vô sổ khách rồi. Trang này mười hai năm, chữ cô chữ ông xen nhau.'),
                ('ong_lam', 'Homestay có khách quen vậy là có nhà rồi đó.')]),
        ]),
    # ------------------------------------------------------------ chương 4
    'customer_care': dict(
        title='Người khách hay gọi', emoji='☎️',
        keepsake=dict(emoji='💌', name='Lá thư cảm ơn của anh Phúc', desc='Chị Mai dán lá thư ở bảng tin của trạm.'),
        cast={'phuc': _p('Anh Phúc', '😠', 'Khách đang bức xúc', 'customer_care_npc_02'),
              'chi_mai': _p('Chị Mai', '🎧', 'Trưởng ca', 'customer_care_npc_06'),
              'duy': _p('Duy', '📦', 'Đầu mối kho', 'customer_care_npc_04')},
        beats=[
            _b('Cuộc gọi thứ năm', '☎️', 'Có một số điện thoại gọi tới trạm rất thường xuyên.', [
                ('phuc', 'Lại là tôi đây! Lần thứ năm rồi! Đơn của tôi đâu?'),
                ('chi_mai', 'Anh Phúc đó. Tuần nào cũng gọi, ai nghe cũng ngại.'),
                ('me', 'Dạ em nghe đây anh. Anh cứ nói, em ghi lại hết.')]),
            _b('Nghe cho hết câu', '👂', 'Anh Phúc lại gọi, giọng còn gắt hơn.', [
                ('phuc', 'Đó là máy đo đường huyết cho má tôi! Không phải món đồ chơi!'),
                ('phuc', 'Má tôi phải đo mỗi sáng mà mượn máy hàng xóm cả tuần nay.'),
                ('chi_mai', 'Em cứ bình tĩnh. Người nóng là vì đang lo.')],
                _c('Bạn trả lời thế nào?',
                   _o('a', 'Để anh nói hết, rồi tóm tắt lại từng ý', [('phuc', '…Ừ, đúng vậy. Lần đầu có người nhắc lại đúng chuyện của tôi.')], rel='phuc'),
                   _o('b', 'Xin lỗi trước, hứa gọi lại trong một giờ', [('phuc', 'Một giờ. Tôi chờ. Mà nhớ gọi đó nha.')], rel='phuc'))),
            _b('Kiện hàng thất lạc', '📦', 'Bạn đã nhờ kho tìm lại đơn của anh Phúc.', [
                ('duy', 'Tìm ra rồi! Kiện bị dán nhầm mã, nằm ở kho quận bên kia hai tuần.'),
                ('chi_mai', 'Lỗi của mình thì mình nhận. Em gọi báo anh Phúc đi.'),
                ('me', 'Em báo rõ: hàng ở đâu, bao giờ tới, và vì sao trễ.')]),
            _b('Giao tận tay', '🤝', 'Chiếc máy đo đã sẵn sàng để giao lại.', [
                ('duy', 'Mai kiện tới. Em muốn giao kiểu nào?'),
                ('chi_mai', 'Khách chờ lâu rồi. Làm sao cho anh ấy thấy mình để tâm thật.'),
                ('me', 'Dạ, em nghĩ tới má của anh Phúc trước.')],
                _c('Giao máy cho anh Phúc',
                   _o('a', 'Gọi báo trước giờ giao chính xác, xin lỗi thêm một lần', [('phuc', 'Giao đúng giờ luôn. Má tôi đo sáng nay rồi, chỉ số ổn.')], rel='phuc'),
                   _o('b', 'Nhờ Duy giao kèm tờ hướng dẫn chữ to cho mẹ anh', [('phuc', 'Tờ hướng dẫn chữ to đó… má tôi tự đo được luôn. Cảm ơn.')], rel='duy'))),
            _b('Lá thư cảm ơn', '💌', 'Trạm vừa nhận được một phong bì viết tay.', [
                ('chi_mai', 'Thư tay gửi trạm nè. Của anh Phúc.'),
                ('phuc', '“Cảm ơn người đã nghe tôi nói hết câu. Tôi đã nóng, mà mọi người vẫn tử tế.”'),
                ('chi_mai', 'Từ tuần sau, em kèm hai bạn mới vào ca nha. Dạy tụi nó cách nghe như vậy.'),
                ('me', 'Dạ. Em sẽ dạy điều đầu tiên: nghe cho hết câu đã.')]),
        ]),
    'pharmacy': dict(
        title='Hộp thuốc của Bác Năm', emoji='💊',
        keepsake=dict(emoji='🍋', name='Túi chanh vườn Bác Năm', desc='Chanh không phun thuốc, Bác Năm hái tặng quầy.'),
        cast={'bac_nam': _p('Bác Năm', '👴', 'Khách quen', 'pharmacy_npc_02'),
              'co_thu': _p('Cô Thu', '👩‍⚕️', 'Người phụ trách', 'pharmacy_npc_01'),
              'lan': _p('Lan', '👩', 'Cháu gái Bác Năm', 'pharmacy_npc_03'),
              'khoa': _p('Khoa', '🧑‍⚕️', 'Nhân viên mới', 'pharmacy_npc_04')},
        beats=[
            _b('Túi thuốc lộn xộn', '💊', 'Bác Năm đổ cả túi thuốc ra quầy.', [
                ('bac_nam', 'Thuốc đường, thuốc huyết áp, bác uống lộn hoài. Có bữa uống hai lần, có bữa quên.'),
                ('co_thu', 'Người lớn tuổi hay vậy lắm. Mình phải giúp bác cho gọn.'),
                ('me', 'Bác để con xem từng vỉ, ghi lại cho bác nha.')]),
            _b('Hộp chia thuốc', '🗓️', 'Quầy có sẵn loại hộp chia thuốc theo ngày.', [
                ('co_thu', 'Lấy hộp chia thuốc bảy ngày, sáng tối riêng. Mình soạn mẫu cho bác một tuần.'),
                ('bac_nam', 'Mắt bác kém, chữ nhỏ là chịu.'),
                ('me', 'Vậy mình làm sao cho bác nhìn là biết, khỏi cần đọc.')],
                _c('Làm sao cho Bác Năm dễ nhìn?',
                   _o('a', 'Vẽ mặt trời, mặt trăng lên từng ngăn', [('bac_nam', 'Mặt trời là sáng, mặt trăng là tối. Vậy bác nhớ liền!')], rel='bac_nam'),
                   _o('b', 'Ghi chữ thật to, dán hai màu sáng và tối', [('bac_nam', 'Màu vàng buổi sáng, màu xanh buổi tối. Dễ ợt!')], rel='bac_nam'))),
            _b('Lan mua hộ', '👩', 'Hôm nay người tới quầy không phải Bác Năm.', [
                ('lan', 'Em là cháu Bác Năm. Ông bận đi tập dưỡng sinh, nhờ em mua thuốc giùm.'),
                ('me', 'Để mình chỉ em cách soạn hộp thuốc cho ông mỗi tuần.'),
                ('lan', 'Vậy em soạn chủ nhật. Ông khỏi lo quên nữa.'),
                ('co_thu', 'Có người nhà cùng lo là yên tâm nhất.')]),
            _b('Câu hỏi khó', '🤔', 'Bác Năm muốn mua thêm một loại thuốc giảm đau.', [
                ('bac_nam', 'Bác đau lưng, bán cho bác vỉ thuốc giảm đau loại mạnh nha.'),
                ('khoa', 'Dạ để em lấy liền…'),
                ('me', 'Khoan đã Khoa. Thuốc này dùng chung với thuốc huyết áp của bác phải hỏi kỹ.')],
                _c('Bạn xử lý thế nào?',
                   _o('a', 'Giải thích cho Bác Năm vì sao cần hỏi bác sĩ trước', [('bac_nam', 'Vậy mai bác đi khám luôn. May mà con nói.')], rel='bac_nam'),
                   _o('b', 'Mời Cô Thu cùng xem, để Khoa học luôn', [('co_thu', 'Khoa nhớ nha: hỏi thuốc đang dùng trước khi bán thêm thuốc nào.')], rel='khoa'))),
            _b('Chỉ số đẹp', '📈', 'Bác Năm vừa đi tái khám.', [
                ('bac_nam', 'Tái khám rồi! Đường huyết đẹp, huyết áp đều. Bác sĩ khen quá trời.'),
                ('lan', 'Tuần nào em cũng soạn hộp thuốc. Ông còn đi bộ mỗi sáng nữa.'),
                ('bac_nam', 'Chanh vườn nhà bác, không phun thuốc. Cả quầy lấy pha nước uống.'),
                ('co_thu', 'Quầy mình nhận chanh, còn Bác Năm nhận lời khen của bác sĩ. Hòa cả làng.')]),
        ]),
    'tour_guide': dict(
        title='Chuyến đi của Bác Bình', emoji='🗺️',
        keepsake=dict(emoji='🏺', name='Cái chén gốm méo', desc='Bác Bình nặn ở làng gốm, tặng người dẫn đoàn.'),
        cast={'bac_binh': _p('Bác Bình', '👴', 'Du khách', 'tour_guide_npc_02'),
              'truc': _p('Trúc', '📷', 'Người mê ảnh', 'tour_guide_npc_03'),
              'co_gom': _p('Cô Gốm', '🏺', 'Chủ xưởng gốm', 'tour_guide_npc_05'),
              'hai': _p('Hải', '📋', 'Điều phối', 'tour_guide_npc_06')},
        beats=[
            _b('Tấm bản đồ cũ', '🗺️', 'Có một bác lớn tuổi mang theo tấm bản đồ đã ố vàng.', [
                ('bac_binh', 'Tấm bản đồ này bác vẽ tay năm mười tám tuổi, hồi đi thanh niên xung phong.'),
                ('bac_binh', 'Giờ bác muốn đi lại mấy chỗ đó một lần.'),
                ('hai', 'Đoàn tuần sau có Bác Bình. Em lo lộ trình kỹ giùm anh nha.')]),
            _b('Lộ trình riêng', '🧭', 'Bạn đang soạn lịch trình cho đoàn có Bác Bình.', [
                ('hai', 'Lịch trình chung thì kín rồi. Em muốn thêm gì cho Bác Bình?'),
                ('bac_binh', 'Bác đi chậm. Đầu gối không còn như hồi mười tám.'),
                ('truc', 'Đi chậm thì con chụp được nhiều hơn. Con thích vậy!')],
                _c('Thêm gì vào lịch trình?',
                   _o('a', 'Một điểm dừng ở bến đò cũ trên bản đồ', [('bac_binh', 'Bến đò đó… bác chờ năm chục năm rồi.')], rel='bac_binh'),
                   _o('b', 'Đi chậm lại, thêm giờ nghỉ ở mỗi điểm', [('bac_binh', 'Đi chậm mới thấy hết. Cảm ơn con đã nghĩ cho người già.')], rel='bac_binh'))),
            _b('Làng gốm', '🏺', 'Đoàn dừng chân ở xưởng gốm của Cô Gốm.', [
                ('co_gom', 'Bác thử nặn một cái chén đi. Méo cũng là của mình.'),
                ('bac_binh', 'Méo xẹo rồi. Mà nhìn cũng thương.'),
                ('truc', 'Để con chụp bàn tay bác dính đất. Tấm này đẹp lắm.'),
                ('co_gom', 'Nung xong tôi gửi theo đoàn về.')]),
            _b('Bến đò năm xưa', '⛴️', 'Theo bản đồ, sắp tới chỗ bến đò cũ.', [
                ('bac_binh', 'Bến đò đây mà. Giờ thành cây cầu rồi.'),
                ('bac_binh', 'Năm đó bác chèo đò chở bạn qua sông, bạn bác giờ không còn nữa.'),
                ('truc', 'Con chụp bác đứng trên cầu, phía sau là chỗ bến cũ nha.'),
                ('me', 'Mình đứng đây thêm một lát. Đoàn không vội đâu bác.')]),
            _b('Cuốn album', '📷', 'Trúc hẹn gửi ảnh chuyến đi.', [
                ('truc', 'Album in xong rồi! Tấm đầu tiên là bàn tay bác dính đất.'),
                ('bac_binh', 'Bác đưa cho mấy đứa cháu coi. Tụi nó hỏi ông đi với ai mà vui vậy.'),
                ('bac_binh', 'Cái chén méo này bác tặng con. Người dẫn đường giỏi phải có cái chén uống trà.'),
                ('hai', 'Khách viết đánh giá dài ba trang luôn. Em đọc chưa?')]),
        ]),
    'teacher': dict(
        title='Tiếng hát của Minh', emoji='🎤',
        keepsake=dict(emoji='🎨', name='Bức vẽ của Minh', desc='Minh vẽ cả lớp đứng hát, người đứng giữa là bạn.'),
        cast={'minh': _p('Minh', '🙈', 'Học sinh bàn cuối', 'teacher_npc_02'),
              'co_ha': _p('Cô Hạ', '👩‍🏫', 'Đồng nghiệp', 'teacher_npc_01'),
              'co_lan': _p('Cô Lan', '👩', 'Mẹ của Minh', 'teacher_npc_06'),
              'vy': _p('Vy', '👧', 'Bạn cùng bàn của Minh', 'teacher_npc_04')},
        beats=[
            _b('Cậu bé bàn cuối', '🙈', 'Có một cậu bé bàn cuối biết bài mà không giơ tay.', [
                ('co_ha', 'Em để ý bé Minh bàn cuối chưa? Biết bài mà không bao giờ giơ tay.'),
                ('minh', '…'),
                ('me', 'Minh viết đáp án vào góc vở rồi lấy tay che lại. Mà đáp án đúng hết.'),
                ('co_ha', 'Nó nhút nhát từ hồi lớp một. Chắc cần một người kiên nhẫn.')]),
            _b('Tờ giấy nhỏ', '✉️', 'Trên bàn giáo viên có một mẩu giấy gấp tư.', [
                ('minh', '“{Thay} ơi, con biết câu hai. Mà con sợ nói sai các bạn cười.”'),
                ('vy', 'Minh viết đó. Minh không dám nói.'),
                ('co_ha', 'Mẩu giấy này là cả một bước dài của Minh đó em.')],
                _c('Bạn giúp Minh thế nào?',
                   _o('a', 'Cho Minh trả lời bằng cách viết lên bảng', [('minh', 'Con viết đúng rồi hả {thay}? Cả lớp vỗ tay cho con…')], rel='minh'),
                   _o('b', 'Khen riêng Minh sau giờ học', [('minh', 'Mai con thử giơ tay một lần. Chỉ một lần thôi nha {thay}.')], rel='minh'))),
            _b('Giọng hát giờ ra chơi', '🎵', 'Giờ ra chơi, sau dãy lớp có tiếng ai đó hát.', [
                ('co_ha', 'Em nghe không? Minh ngồi hát một mình sau gốc phượng đó.'),
                ('me', 'Giọng trong quá. Không giống cậu bé chẳng dám giơ tay chút nào.'),
                ('co_lan', 'Ở nhà Minh hát suốt. Mà ra ngoài là im thin thít.'),
                ('co_ha', 'Cuối năm trường có đêm văn nghệ. Hay mình thử?')]),
            _b('Buổi tập văn nghệ', '🎤', 'Lớp bắt đầu tập tiết mục cho đêm văn nghệ.', [
                ('minh', 'Con đứng hàng cuối được không {thay}? Hàng cuối không ai nhìn.'),
                ('vy', 'Minh hát hay nhất lớp đó! Tụi con nghe lén rồi.'),
                ('co_ha', 'Không ép nha. Cho Minh một chỗ đứng mà Minh thấy an toàn.')],
                _c('Cho Minh tập thế nào?',
                   _o('a', 'Để Minh đứng cạnh Vy, hát cùng bạn thân', [('minh', 'Có Vy bên cạnh con đỡ run hơn. Con hát to thêm được một chút.')], rel='vy'),
                   _o('b', 'Cho Minh cầm trống lắc trước, hát sau', [('minh', 'Cầm trống lắc thì tay con hết run. Con hát được đoạn điệp khúc rồi!')], rel='minh'))),
            _b('Đêm văn nghệ cuối năm', '🌟', 'Sân trường đã treo đèn cho đêm văn nghệ.', [
                ('co_ha', 'Tới lớp mình rồi! Minh đâu?'),
                ('minh', '{Thay} ơi… con hát đoạn đơn ca được không? Một đoạn thôi.'),
                ('co_lan', 'Trời ơi, thằng Minh nhà tôi hát trên sân khấu… Tôi khóc mất.'),
                ('minh', 'Con tặng {thay} bức vẽ nè. Cả lớp đứng hát, người đứng giữa là {thay}.')]),
        ]),
    'accounting': dict(
        title='Sổ của Cô Hoa', emoji='📒',
        keepsake=dict(emoji='🗝️', name='Chìa khóa tủ hồ sơ', desc='Chị Vân giao bạn tủ hồ sơ của ba khách quen.'),
        cast={'chi_van': _p('Chị Vân', '👩‍💼', 'Người quản lý', 'accounting_npc_02'),
              'co_hoa': _p('Cô Hoa', '🍜', 'Chủ tiệm bánh cuốn, khách thuê làm sổ', 'accounting_npc_03'),
              'tram': _p('Trâm', '🔍', 'Người kiểm tra nội bộ', 'accounting_npc_06'),
              'nam': _p('Nam', '🛒', 'Bộ phận mua hàng', 'accounting_npc_04'),
              'huy': _p('Huy', '🧑‍💻', 'Đồng nghiệp mới', 'accounting_npc_01')},
        beats=[
            _b('Hộp giày đầy hóa đơn', '👟', 'Có một vị khách ôm hộp giày vào văn phòng.', [
                ('co_hoa', 'Hóa đơn cả năm của tiệm bánh cuốn cô nằm hết trong hộp giày này.'),
                ('co_hoa', 'Cô bán bánh thì giỏi, chứ sổ sách thì thua.'),
                ('chi_van', 'Em nhận sổ của Cô Hoa nha. Làm từ đầu, làm cho gọn.')]),
            _b('Nhặt từng tờ', '🧾', 'Hộp giày đã được đổ ra bàn.', [
                ('huy', 'Hóa đơn gạo, hóa đơn điện, có tờ viết trên giấy lịch luôn…'),
                ('me', 'Tờ nào cũng là tiền thật của Cô Hoa. Mình xếp cho đàng hoàng.'),
                ('co_hoa', 'Tờ giấy lịch đó là tiền mua than hồi Tết. Cô nhớ mà.')],
                _c('Xếp hóa đơn của Cô Hoa',
                   _o('a', 'Xếp theo ngày, dán số thứ tự từng tờ', [('co_hoa', 'Có số thứ tự rồi, cô tìm tờ nào cũng ra.')], rel='co_hoa'),
                   _o('b', 'Chia theo loại: nguyên liệu, điện nước, tiền công', [('co_hoa', 'Giờ cô mới biết tiền gạo chiếm nửa chi phí!')], rel='co_hoa'))),
            _b('Lần kiểm tra đầu tiên', '🔍', 'Bộ phận kiểm tra nội bộ muốn xem sổ của Cô Hoa.', [
                ('tram', 'Chị kiểm ngẫu nhiên mười chứng từ trong sổ Cô Hoa nha.'),
                ('tram', 'Chín tờ khớp. Còn một tờ tiền ga thiếu hóa đơn gốc.'),
                ('me', 'Em gọi Cô Hoa xin lại bản gốc liền. Em ghi chú ngay dòng đó.'),
                ('tram', 'Lần đầu mà vậy là tốt. Chỗ thiếu thì ghi chú rõ, đừng giấu.')]),
            _b('Tờ hóa đơn lạ', '⚠️', 'Nam bên mua hàng đang đứng chờ ở bàn bạn.', [
                ('nam', 'Em ghi giùm anh tờ hóa đơn này nha. Số tiền cao hơn thực tế chút xíu, cho sổ đẹp.'),
                ('nam', 'Ai mà để ý. Có mấy trăm nghìn thôi.'),
                ('me', 'Sổ đẹp mà sai thì không phải sổ đẹp đâu anh.')],
                _c('Bạn làm gì?',
                   _o('a', 'Từ chối, xin anh Nam hóa đơn đúng số tiền', [('nam', '…Ừ, anh lấy lại hóa đơn đúng. Thôi, làm cho đàng hoàng.')]),
                   _o('b', 'Báo Chị Vân để cùng xử lý cho rõ', [('chi_van', 'Em làm đúng. Chị nói chuyện với Nam. Sổ này có tên em, phải sạch.')], rel='chi_van'))),
            _b('Chìa khóa tủ hồ sơ', '🗝️', 'Chị Vân hẹn gặp riêng cuối ngày.', [
                ('chi_van', 'Sổ Cô Hoa gọn nhất văn phòng. Kiểm tra không sót, hóa đơn lạ cũng không lọt.'),
                ('chi_van', 'Từ tháng sau em phụ trách sổ của Cô Hoa và hai tiệm nữa. Chìa khóa tủ hồ sơ đây.'),
                ('co_hoa', 'Cô giới thiệu thêm tiệm chè của em gái cô nữa đó!'),
                ('huy', 'Chỉ em cách xếp hộp giày với nha.')],
                days=9, served=22, gap=2, level=4),
        ]),
    # ------------------------------------------------------------ văn phòng
    'corp_accounting': dict(
        title='Năm đầu ở Mây Tre Xanh', emoji='🧮',
        keepsake=dict(emoji='📄', name='Quyết định bổ nhiệm', desc='Kế toán tổng hợp, ký tên Anh Tùng và Chị Hạnh.'),
        cast={'chi_hanh': _p('Chị Hạnh', '👩‍💼', 'Kế toán trưởng', 'corp_accounting_npc_01'),
              'anh_tung': _p('Anh Tùng', '👔', 'Giám đốc', 'corp_accounting_npc_02'),
              'anh_khai': _p('Anh Khải', '🔍', 'Kiểm toán viên', 'corp_accounting_npc_05'),
              'ba_sau': _p('Bà Sáu', '🧺', 'Chủ HTX Mây Tre', 'corp_accounting_npc_06'),
              'na': _p('Na', '🧑‍🎓', 'Thực tập sinh kế toán', 'corp_accounting_npc_08')},
        beats=[
            _b('Chiếc bàn gần cửa sổ', '🪪', 'Ngày đầu có thẻ nhân viên ở Mây Tre Xanh.', [
                ('chi_hanh', 'Bàn của em đây. Mật khẩu phần mềm, tủ chứng từ, lịch khóa sổ, chị dán hết lên bảng rồi.'),
                ('chi_hanh', 'Ở đây chị chỉ cần một điều: số nào cũng có chứng từ.'),
                ('na', 'Em là Na, thực tập. Có gì em hỏi {anh} nha!')]),
            _b('Hóa đơn viết tay của HTX', '🧺', 'Bà Sáu bên HTX Mây Tre ghé công ty.', [
                ('ba_sau', 'Bà giao hàng mây tre ba chục năm, toàn viết hóa đơn tay. Giờ người ta bắt hóa đơn điện tử.'),
                ('ba_sau', 'Bà mù chữ máy tính con ơi.'),
                ('chi_hanh', 'HTX là nhà cung cấp lâu năm. Em giúp bà một tay nha.')],
                _c('Giúp Bà Sáu',
                   _o('a', 'Ngồi hướng dẫn Bà Sáu lập hóa đơn điện tử từng bước', [('ba_sau', 'Bà bấm được rồi! Để bà về chỉ lại cho mấy đứa trong HTX.')], rel='ba_sau'),
                   _o('b', 'Viết cho bà một tờ hướng dẫn chữ to, có hình', [('ba_sau', 'Tờ này bà dán lên tường xưởng luôn. Cảm ơn con.')], rel='ba_sau'))),
            _b('Đợt kiểm toán đầu tiên', '🔍', 'Công ty kiểm toán sắp tới làm việc.', [
                ('anh_khai', 'Tôi chọn mẫu ba mươi chứng từ quý ba. Chị Hạnh nói em giữ tủ chứng từ?'),
                ('me', 'Dạ, em đánh số theo bút toán. Anh chọn tờ nào em lấy tờ đó.'),
                ('anh_khai', 'Hai mươi chín tờ khớp, một tờ lệch ngày ghi sổ. Ghi chú rõ rồi, được.'),
                ('chi_hanh', 'Lần đầu gặp kiểm toán mà không run. Được đó em.')]),
            _b('Lời nhờ của Giám đốc', '⚠️', 'Anh Tùng gọi bạn vào phòng, đóng cửa lại.', [
                ('anh_tung', 'Em đưa vào chi phí giùm anh hóa đơn tiếp khách này. Bữa đó không có thật, nhưng giảm được thuế.'),
                ('anh_tung', 'Công ty nhỏ, cuối năm kẹt lắm. Em hiểu mà.'),
                ('me', 'Em hiểu công ty đang kẹt. Nhưng hóa đơn không có thật thì em không ghi được.')],
                _c('Bạn nói tiếp…',
                   _o('a', 'Nói thẳng và đề xuất cách giảm thuế hợp lệ', [('anh_tung', '…Khấu hao đúng hạn, ưu đãi cho HTX. Ừ, vậy mà giảm được thật. Thôi, bỏ tờ kia.')], rel='anh_tung'),
                   _o('b', 'Xin gặp Chị Hạnh để ba người cùng bàn', [('chi_hanh', 'Anh Tùng, em nó đúng. Công ty mình làm ăn thật thì sổ phải thật.')], rel='chi_hanh')),
                days=6, served=14, gap=1),
            _b('Tờ quyết định', '📄', 'Cuối năm, phòng kế toán có một cuộc họp nhỏ.', [
                ('anh_tung', 'Năm nay sổ sạch, kiểm toán không ý kiến. Anh cảm ơn em chuyện hôm đó.'),
                ('chi_hanh', 'Từ tháng sau em làm kế toán tổng hợp. Na sẽ theo em học việc.'),
                ('na', 'Em sẽ học cách “số nào cũng có chứng từ”!'),
                ('ba_sau', 'Bà gửi cái giỏ mây này mừng con lên chức. HTX tự đan đó.')],
                days=9, served=22, gap=2, level=4),
        ]),
    'tax_payroll': dict(
        title='Phiếu lương của Diệu', emoji='🧾',
        keepsake=dict(emoji='🧵', name='Chiếc khăn tay thêu', desc='Diệu thêu tặng, góc khăn có hình cây bút và cuốn sổ.'),
        cast={'chi_hong': _p('Chị Hồng', '👩‍💼', 'Kế toán trưởng', 'tax_payroll_npc_01'),
              'dieu': _p('Em Diệu', '🧵', 'Công nhân may', 'tax_payroll_npc_03'),
              'anh_phat': _p('Anh Phát', '👔', 'Giám đốc Xưởng may Chỉ Vàng', 'tax_payroll_npc_02'),
              'chi_hoa': _p('Chị Hoa', '📋', 'Tổ trưởng chuyền may', 'tax_payroll_npc_07'),
              'co_lua': _p('Cô Lụa', '🏛️', 'Cán bộ thuế phường', 'tax_payroll_npc_06')},
        beats=[
            _b('Tờ phiếu lương nhàu', '🧾', 'Một cô công nhân cầm tờ phiếu lương đứng ngoài cửa.', [
                ('dieu', 'Em không hiểu phiếu lương. Tháng này sao ít hơn tháng trước?'),
                ('dieu', 'Em hỏi tổ trưởng, tổ trưởng nói hỏi kế toán.'),
                ('chi_hong', 'Em ngồi giải thích từng dòng cho Diệu nha. Người lao động có quyền hiểu lương mình.')]),
            _b('Giờ tăng ca bị sót', '⏱️', 'Bạn đang đối chiếu bảng chấm công của Diệu.', [
                ('me', 'Bảng chấm công ghi Diệu tăng ca sáu buổi, mà bảng lương chỉ tính bốn.'),
                ('chi_hoa', 'Hai buổi đó chị ghi tay vô sổ tổ, chắc chưa nhập máy.'),
                ('chi_hong', 'Sai của mình thì sửa ngay. Lương là công sức người ta.')],
                _c('Sửa sai sót',
                   _o('a', 'Làm phiếu điều chỉnh, trả bù ngay kỳ lương này', [('dieu', 'Em nhận đủ rồi! Hai buổi đó em thức khuya lắm đó.')], rel='dieu'),
                   _o('b', 'Rà lại cả chuyền may xem còn ai bị sót không', [('chi_hoa', 'Còn ba bạn nữa bị sót. Cả tổ cảm ơn em.')], rel='chi_hoa'))),
            _b('Mùa quyết toán', '📅', 'Hạn quyết toán thuế thu nhập cá nhân đã tới gần.', [
                ('co_lua', 'Năm nay phường nhắc sớm: quyết toán đúng hạn, hồ sơ đủ người phụ thuộc.'),
                ('dieu', 'Em có nuôi mẹ già. Vậy có được giảm trừ không {anh}?'),
                ('me', 'Được, nếu mẹ em không có thu nhập. Mình làm hồ sơ đăng ký nha.'),
                ('chi_hong', 'Hồ sơ đủ, nộp sớm hai tuần. Năm nay đỡ chạy.')]),
            _b('Lương hai sổ', '⚠️', 'Anh Phát bên xưởng may muốn gặp riêng.', [
                ('anh_phat', 'Em chia lương công nhân ra: một phần lương, một phần “phụ cấp tiền mặt” ngoài sổ.'),
                ('anh_phat', 'Đóng bảo hiểm ít đi, công nhân cũng được cầm tiền nhiều hơn. Ai cũng lợi.'),
                ('me', 'Vậy là công nhân mất bảo hiểm khi ốm đau, về già. Diệu và cả chuyền may đó anh.')],
                _c('Bạn trả lời Anh Phát',
                   _o('a', 'Từ chối và tính cho anh xem chi phí thật nếu bị phát hiện', [('anh_phat', 'Tính ra còn lỗ hơn… Thôi, giữ như cũ. Em nói có lý.')], rel='anh_phat'),
                   _o('b', 'Mời Chị Hồng cùng giải thích quyền lợi của người lao động', [('chi_hong', 'Minh Bạch làm dịch vụ cho người đàng hoàng. Anh Phát hiểu mà.')], rel='chi_hong')),
                days=6, served=14, gap=1),
            _b('Chiếc khăn tay thêu', '🧵', 'Cuối năm, có người gửi quà tới văn phòng.', [
                ('dieu', 'Em thêu tặng {anh} cái khăn. Góc khăn là cây bút với cuốn sổ.'),
                ('dieu', 'Nhờ {anh} mà em hiểu từng dòng lương. Giờ em chỉ lại cho mấy bạn mới vô.'),
                ('chi_hong', 'Năm sau em phụ trách luôn hồ sơ của Xưởng Chỉ Vàng. Chị tin em.'),
                ('anh_phat', 'Công nhân ít nghỉ việc hẳn. Tôi cũng không ngờ.')],
                days=9, served=22, gap=2, level=4),
        ]),
    'group_accounting': dict(
        title='Mùa hợp nhất đầu tiên', emoji='🏢',
        keepsake=dict(emoji='🪪', name='Thẻ trưởng nhóm hợp nhất', desc='Tầng 12, Sông Hồng Group. Thẻ có tên bạn.'),
        cast={'mai_anh': _p('Chị Mai Anh', '👩‍💼', 'Giám đốc tài chính tập đoàn', 'group_accounting_npc_01'),
              'ong_dai': _p('Ông Đại', '👨‍⚖️', 'Chủ tịch HĐQT', 'group_accounting_npc_02'),
              'anh_kien': _p('Anh Kiên', '📈', 'Giám đốc tài chính SH Nami', 'group_accounting_npc_05'),
              'chi_thao': _p('Chị Thảo', '🔍', 'Trưởng nhóm kiểm toán', 'group_accounting_npc_06'),
              'linh': _p('Linh', '🧑‍💻', 'Kế toán mới ở SH Pack', 'group_accounting_npc_07')},
        beats=[
            _b('Bốn công ty, một bộ sổ', '🏢', 'Ngày đầu ở tầng 12 của Sông Hồng Group.', [
                ('mai_anh', 'Bốn công ty con, bán cho nhau đủ thứ. Việc của em là để bộ báo cáo chung không đếm trùng đồng nào.'),
                ('mai_anh', 'Loại trừ đúng, hợp nhất khớp. Lệch một đồng chị cũng hỏi.'),
                ('me', 'Dạ. Em vẽ sơ đồ giao dịch nội bộ trước rồi mới vào số.')]),
            _b('Linh lạc giữa các con số', '🤝', 'Có một kế toán mới ngồi thở dài ở bàn bên.', [
                ('linh', 'Em mới vào SH Pack. Công nợ nội bộ lệch với SH Logistics mà em không biết tìm ở đâu.'),
                ('linh', 'Em sợ hỏi nhiều người ta chê.'),
                ('me', 'Hồi mới vào mình cũng vậy. Hỏi là cách học nhanh nhất đó.')],
                _c('Bạn giúp Linh',
                   _o('a', 'Ngồi cùng Linh đối chiếu từng hóa đơn nội bộ', [('linh', 'Lệch do một hóa đơn ghi hai lần! Cảm ơn {anh}, em hiểu cách dò rồi.')], rel='linh'),
                   _o('b', 'Chỉ Linh cách lập bảng đối chiếu, để Linh tự dò', [('linh', 'Em tự tìm ra rồi! Lần sau em tự làm được.')], rel='linh'))),
            _b('Kiểm toán năm', '🔍', 'Nhóm kiểm toán đã dọn vào phòng họp nhỏ.', [
                ('chi_thao', 'Chị cần bảng loại trừ doanh thu nội bộ và lãi chưa thực hiện trong hàng tồn kho.'),
                ('me', 'Dạ, em có bảng đối chiếu cho từng cặp công ty, kèm chứng từ gốc.'),
                ('chi_thao', 'Đầy đủ vậy là nhóm chị về sớm hai ngày đó.'),
                ('mai_anh', 'Lần đầu làm kiểm toán năm mà vậy là tốt lắm.')]),
            _b('Doanh thu nội bộ', '⚠️', 'Trước buổi họp HĐQT, Anh Kiên ghé bàn bạn.', [
                ('anh_kien', 'Lô hàng SH Nami bán cho SH Food cuối quý, em đừng loại trừ nha. Doanh thu đẹp trước buổi họp.'),
                ('anh_kien', 'Quý sau mình điều chỉnh lại. Không ai thiệt đâu.'),
                ('me', 'Bán cho nhau trong tập đoàn thì không phải doanh thu thật, anh ạ. Báo cáo sẽ sai.')],
                _c('Bạn làm gì?',
                   _o('a', 'Giữ bút toán loại trừ, giải thích bằng số liệu cho Anh Kiên', [('anh_kien', 'Ừ… nhìn bảng thì rõ thật. Để anh tự trình bày doanh thu thật với HĐQT.')], rel='anh_kien'),
                   _o('b', 'Báo Chị Mai Anh trước buổi họp', [('mai_anh', 'Cảm ơn em đã nói sớm. Báo cáo của tập đoàn phải nói thật, kể cả khi số không đẹp.')], rel='mai_anh')),
                days=6, served=14, gap=1),
            _b('Phòng họp tầng 12', '🏙️', 'Bạn được mời vào buổi họp HĐQT.', [
                ('ong_dai', 'Năm nay báo cáo hợp nhất ra sớm, kiểm toán không ngoại trừ. Người lập là ai?'),
                ('mai_anh', 'Dạ, là bạn này. Và bạn đã giữ cho báo cáo nói thật.'),
                ('ong_dai', 'Tập đoàn cần người như vậy. Từ quý sau, cháu làm trưởng nhóm hợp nhất.'),
                ('linh', 'Em xin vào nhóm của {anh} đầu tiên!')],
                days=9, served=22, gap=2, level=4),
        ]),
    'tra_da': dict(
        title='Chiếc ghế xanh gốc bàng', emoji='🪑',
        keepsake=dict(emoji='📒', name='Cuốn sổ bìa xanh của bà Lựu', desc='Hai mươi năm tên khách quen, gạch nợ bằng bút bi. Giờ đến lượt bạn ghi.'),
        cast={'ba_luu': _p('Bà Lựu', '👵', 'Chủ quán trà đá', 'tra_da_npc_01'),
              'tuong': _p('Chú Tường', '🛵', 'Xe ôm đầu ngõ', 'tra_da_npc_02'),
              'linh': _p('Linh', '🎒', 'Học sinh lớp 11', 'tra_da_npc_05'),
              'hoa': _p('Cô Hoa', '🍙', 'Bán xôi đầu ngõ', 'tra_da_npc_06')},
        beats=[
            _b('Chiếc ghế xanh', '🪑', 'Có một ông khách cứ nhất định ngồi đúng một chiếc ghế.', [
                ('tuong', 'Cái ghế xanh sát gốc bàng là của chú đấy nhé. Hai chục năm nay rồi.'),
                ('ba_luu', 'Ông ấy ngồi đấy từ hồi còn chạy xe Cub, giờ xe cũng già như người.'),
                ('tuong', 'Cốc trà đá, không đường. Ghi sổ, cuối tuần chú trả.'),
                ('me', 'Dạ, cháu nhớ rồi. Ghế xanh, trà đá, ghi sổ.')]),
            _b('Cuốc xe ế', '🛵', 'Chú Tường ngồi lâu hơn mọi hôm, điện thoại úp trên đùi.', [
                ('tuong', 'Bây giờ người ta bấm điện thoại gọi xe hết. Cả sáng chú chưa được cuốc nào.'),
                ('hoa', 'Ông Tường cứ ngồi đây than, sao không cài cái ứng dụng như tụi thanh niên?'),
                ('tuong', 'Chữ trên đấy bé tí, chú đọc không ra.')],
                _c('Chiều nay giúp chú Tường thế nào?',
                   _o('a', 'Viết số điện thoại chú lên tấm bảng phấn', [('tuong', 'Ơ, ba người gọi rồi đấy! Cái bảng phấn còn nhanh hơn cái điện thoại.')], rel='tuong'),
                   _o('b', 'Ngồi chỉ chú từng bước bật ứng dụng', [('tuong', 'Phóng chữ to lên là chú đọc được. Cuốc đầu tiên trên máy đây rồi!')], rel='tuong'))),
            _b('Bàn học gốc bàng', '📖', 'Linh trải sách vở ra chiếc bàn gỗ thấp.', [
                ('linh', 'Ở nhà đang sửa, ồn quá. Em ngồi đây học nhờ một buổi được không ạ?'),
                ('ba_luu', 'Ngồi đi cháu. Quán này nuôi được mấy lứa học trò rồi đấy.'),
                ('linh', 'Tuần sau em thi học kỳ môn Toán, mà hình không gian khó quá.')],
                _c('Linh ngồi học đến tối',
                   _o('a', 'Giữ riêng một ghế và pha cốc trà chanh cho Linh', [('linh', 'Ngồi đây mát hơn ở nhà nhiều. Em làm xong ba đề rồi!')], rel='linh'),
                   _o('b', 'Nhờ chú Tường giảng hộ, hồi trẻ chú dạy Toán', [('tuong', 'Hồi xưa chú dạy cấp ba đấy, cháu tưởng chú chỉ biết chạy xe à?'), ('linh', 'Chú giảng dễ hiểu hơn cả cô giáo ạ!')], rel='tuong'))),
            _b('Gạch sổ', '✍️', 'Chú Tường tới sớm, tay cầm một xấp tiền lẻ.', [
                ('tuong', 'Tháng này chạy được, chú trả hết sổ. Gạch đi, gạch hết đi cháu.'),
                ('ba_luu', 'Hai chục năm bà chưa thấy ông ấy trả một lần hết sạch thế này.'),
                ('hoa', 'Ông Tường có cháu nội đấy, hôm nay ông khao cả phố xôi.'),
                ('me', 'Cháu gạch rồi đây chú. Mai lại ghi dòng mới nhé.')]),
            _b('Cuốn sổ bìa xanh', '📒', 'Bà Lựu gói một thứ trong túi ni lông, buộc chun cẩn thận.', [
                ('ba_luu', 'Cuốn sổ này bà ghi từ hồi quán mới có hai cái ghế.'),
                ('ba_luu', 'Ai nợ bao nhiêu không quan trọng bằng ai hay ngồi ghế nào. Cháu giữ lấy.'),
                ('linh', 'Em thi được chín điểm Toán! Em mang cả bảng điểm ra khoe quán đây!'),
                ('tuong', 'Quán vẫn là quán của bà Lựu. Chỉ là giờ có người pha trà trẻ hơn.'),
                ('me', 'Cháu sẽ giữ chiếc ghế xanh cho chú, và giữ quán cho cả phố.')]),
        ]),
    # ------------------------------------------------------------ the street trades
    'fruit': dict(
        title='Quả cân đồng của dì Tư', emoji='⚖️',
        keepsake=dict(emoji='⚖️', name='Quả cân đồng một ký', desc='Mòn bóng vì mười lăm năm sáng nào cũng đặt lên cân. Giờ đến lượt bạn thử cân.'),
        cast={'di_tu': _p('Dì Tư', '👩‍🌾', 'Chủ sạp trái cây', 'fruit_npc_01'),
              'co_nam': _p('Cô Năm', '🧺', 'Nội trợ đi chợ sớm', 'fruit_npc_02'),
              'ba_hai': _p('Bà Hai', '⚖️', 'Cụ bà xóm chợ', 'fruit_npc_05'),
              'be_mo': _p('Bé Mơ', '🎒', 'Học sinh lớp 6', 'fruit_npc_08')},
        beats=[
            _b('Sạp đầu chợ', '🧺', 'Bốn giờ sáng, dì Tư đã chất đầy mấy rổ trái lên sạp.', [
                ('di_tu', 'Dì đi chợ đầu mối về là mệt rã. Con trông sạp giúp dì nghe.'),
                ('co_nam', 'Sạp dì Tư bán hai chục năm, chưa ai chê cân thiếu đâu con.'),
                ('di_tu', 'Trái nào xanh để dành, trái nào chín bán liền. Nhìn cuống là biết.'),
                ('me', 'Dạ, con nhớ rồi: xanh để dành, chín bán liền.')]),
            _b('Cái cân của bà Hai', '⚖️', 'Bà Hai đặt cái cân đồng hồ nhỏ xíu lên sạp, nheo mắt nhìn.', [
                ('ba_hai', 'Hồi trước bà mua ở chợ khác, cứ một ký là thiếu cả lạng.'),
                ('ba_hai', 'Từ đó đi đâu bà cũng mang cân theo. Cháu đừng giận nhé.'),
                ('di_tu', 'Bà cân lại thoải mái, sạp này không sợ.')],
                _c('Bà Hai cân lại túi cam',
                   _o('a', 'Mời bà cân trước mặt cả dãy chợ', [('ba_hai', 'Đủ một ký, còn dư chút. Được, từ nay bà mua ở đây.')], rel='ba_hai'),
                   _o('b', 'Chỉ bà cách thử cân bằng quả cân một ký', [('ba_hai', 'À, thử vậy là biết cân nào lệch liền. Bà học được rồi!')], rel='ba_hai'))),
            _b('Mùa xoài', '🥭', 'Xoài cát về đầy chợ, vàng ươm cả dãy sạp.', [
                ('co_nam', 'Xoài chín cây thì cuống thơm, vỏ vàng không đều. Xoài ủ thuốc vàng đều như sơn.'),
                ('di_tu', 'Mình chỉ lấy xoài xanh về tự để chín. Chậm một hôm mà ăn ngọt thật.'),
                ('co_nam', 'Cô mua ở đây vì ăn yên tâm.')],
                _c('Có người chào bán thuốc ủ chín',
                   _o('a', 'Từ chối, kể cho cô Năm nghe', [('co_nam', 'Đúng rồi con. Giữ tiếng còn hơn giữ tiền.')], rel='co_nam'),
                   _o('b', 'Hỏi rõ nguồn gốc rồi mới từ chối', [('di_tu', 'Hỏi cho biết cũng được. Không giấy tờ là mình không đụng.')], rel='di_tu'))),
            _b('Giỏ trái cho mẹ', '🍊', 'Bé Mơ đứng trước sạp, tay cầm tờ giấy mẹ ghi.', [
                ('be_mo', 'Mẹ con nằm viện mấy hôm rồi. Con muốn mua trái cây ngon nhất cho mẹ.'),
                ('be_mo', 'Con có mười xu thôi ạ.'),
                ('me', 'Để cô lựa cho con mấy trái cam ngọt, trái chuối vừa chín.')],
                _c('Giỏ trái cho mẹ bé Mơ',
                   _o('a', 'Lựa trái ngon, tính đúng giá, bớt cho bé chút', [('be_mo', 'Mẹ con khen cam ngọt lắm ạ!')], rel='be_mo'),
                   _o('b', 'Tặng thêm trái bưởi nhỏ “cho mẹ mau khỏe”', [('be_mo', 'Con cảm ơn cô! Mẹ con bảo khỏe rồi sẽ ra cảm ơn.')], rel='be_mo', coins=0))),
            _b('Quả cân đồng', '⚖️', 'Dì Tư lau quả cân đồng bằng khăn ướt, đặt vào tay bạn.', [
                ('di_tu', 'Quả cân này dì dùng mười lăm năm, sáng nào cũng thử cân bằng nó.'),
                ('di_tu', 'Cân đúng thì bán được lâu. Giờ con giữ.'),
                ('ba_hai', 'Bà bỏ cân ở nhà rồi đấy. Tin sạp này.'),
                ('be_mo', 'Mẹ con ra viện rồi ạ! Mẹ gửi cô hộp bánh.'),
                ('me', 'Con sẽ thử cân mỗi sáng, như dì.')]),
        ]),
    'garbage': dict(
        title='Chiếc xe đẩy ba ngăn', emoji='🛒',
        keepsake=dict(emoji='🦺', name='Chiếc áo phản quang cũ của chị Hạnh', desc='Sờn vai, bạc màu, mười hai năm đi qua từng ngõ. Chị bảo mặc nó thì xe nào cũng thấy.'),
        cast={'hanh': _p('Chị Hạnh', '🧹', 'Tổ trưởng tổ thu gom', 'garbage_npc_01'),
              'bac_tam': _p('Bác Tâm', '📒', 'Tổ trưởng dân phố ngõ 12', 'garbage_npc_02'),
              'co_tam': _p('Cô Tám', '♻️', 'Thu mua ve chai', 'garbage_npc_05'),
              'be_na': _p('Bé Na', '🎒', 'Học sinh lớp 8', 'garbage_npc_07')},
        beats=[
            _b('Tiếng xe đầu ngõ', '🛒', 'Sáu giờ chiều, tiếng lọc xọc của xe đẩy vang lên đầu ngõ 12.', [
                ('hanh', 'Nghe tiếng xe là cả ngõ mang rác ra. Mình mà trễ là mèo bới tung.'),
                ('bac_tam', 'Tổ thu gom mới có người à? Nhớ giờ ngõ này nhé cháu.'),
                ('hanh', 'Túi nào lạ thì mở xem. Pin với kim tiêm là không đùa được đâu.'),
                ('me', 'Dạ, em nhớ rồi.')]),
            _b('Túi vàng của cô Tám', '♻️', 'Cô Tám dựng xe ba gác ở điểm tập kết, cân từng bao lon.', [
                ('co_tam', 'Túi vàng sạch là cô mua. Lẫn cơm canh vào là bán không ai lấy.'),
                ('hanh', 'Tiền ve chai tổ để dành, cuối năm cả tổ đi Vũng Tàu.'),
                ('co_tam', 'Mà giờ nhiều nhà vẫn đổ chung lắm.')],
                _c('Làm sao cho túi vàng sạch hơn?',
                   _o('a', 'Nhắc từng nhà, nói nhẹ nhàng', [('co_tam', 'Tuần này túi vàng sạch hẳn. Cô trả thêm cho tổ nè.')], rel='co_tam'),
                   _o('b', 'Rủ bé Na vẽ tờ hướng dẫn dán đầu ngõ', [('be_na', 'Em vẽ ba cái thùng có mặt cười nha!')], rel='be_na'))),
            _b('Tờ hướng dẫn của bé Na', '🖍️', 'Bé Na chạy theo xe, tay cầm xấp giấy vẽ.', [
                ('be_na', '{Anh} ơi, em vẽ tờ hướng dẫn phân loại rác nè. Dán ở đâu được ạ?'),
                ('bac_tam', 'Dán ở bảng tin đầu ngõ, bác cho phép.'),
                ('hanh', 'Tụi nhỏ mà nhắc thì người lớn nghe hơn mình nhắc.')],
                _c('Dán tờ hướng dẫn của bé Na',
                   _o('a', 'Dán cạnh bảng giờ thu gom', [('bac_tam', 'Đẹp đấy. Để bác nhắc thêm trong buổi họp tổ.')], rel='bac_tam'),
                   _o('b', 'Dán lên chính chiếc xe đẩy', [('be_na', 'Xe đi tới đâu tờ hướng dẫn đi tới đó luôn!')], rel='be_na'))),
            _b('Đêm mưa', '🌧️', 'Mưa như trút, nước ngập ngang mắt cá, túi rác trôi lềnh bềnh.', [
                ('hanh', 'Vớt rác chặn miệng cống trước đã, không thì ngập cả ngõ.'),
                ('bac_tam', 'Bác cầm đèn pin soi cho hai chị em.'),
                ('me', 'Nước rút rồi chị ơi!'),
                ('hanh', 'Ướt hết rồi, về uống bát gừng cho ấm.')]),
            _b('Chiếc áo phản quang', '🦺', 'Chị Hạnh cởi chiếc áo phản quang cũ, gấp lại cẩn thận.', [
                ('hanh', 'Tháng sau chị chuyển lên làm tổ trưởng khu. Tuyến này chị giao em.'),
                ('hanh', 'Áo này mười hai năm rồi. Mặc nó thì xe nào cũng thấy mình.'),
                ('bac_tam', 'Ngõ 12 sạch nhất phường, cả tổ được khen trước phường.'),
                ('be_na', 'Em được giải báo tường nhờ bài viết về xe rác đó!'),
                ('me', 'Em sẽ giữ ngõ sạch như chị đã giữ.')]),
        ]),
    'drain': dict(
        title='Cuộn dây lò xo của chú Hai', emoji='🌀',
        keepsake=dict(emoji='🌀', name='Cuộn dây lò xo mòn tay cầm', desc='Hai mươi năm đi qua không biết bao nhiêu đường ống. Tay cầm bóng lên vì mồ hôi.'),
        cast={'chu_hai': _p('Chú Hai', '🧰', 'Thợ thông cống lâu năm', 'drain_npc_01'),
              'chi_hong': _p('Chị Hồng', '🍲', 'Chủ quán bún bò', 'drain_npc_02'),
              'ba_ngoc': _p('Bà Ngọc', '🏚️', 'Nhà phố cổ ống gang', 'drain_npc_03'),
              'ong_loc': _p('Ông Lộc', '📒', 'Tổ trưởng dân phố', 'drain_npc_06')},
        beats=[
            _b('Nghe tiếng nước', '💧', 'Chú Hai đặt tai sát miệng ống, ra hiệu cho bạn im lặng.', [
                ('chu_hai', 'Nghe không? Ọc ọc là thiếu hơi. Ì ạch là tắc xa. Rít rít là tắc gần.'),
                ('chu_hai', 'Chưa biết bệnh thì đừng cầm đồ nghề.'),
                ('me', 'Dạ, hỏi, nhìn, xả nước thử rồi mới làm.')]),
            _b('Bồn rửa quán bún', '🍲', 'Bốn giờ sáng, chị Hồng gọi điện, giọng run run.', [
                ('chi_hong', 'Nồi nước lèo sắp xong mà bồn rửa ngập mỡ. Cứu chị với!'),
                ('chu_hai', 'Mỡ đông thì phải phun, thông tạm bằng lò xo vài hôm lại tắc.'),
                ('chi_hong', 'Mà chị sắp bán rồi…')],
                _c('Bồn rửa quán chị Hồng',
                   _o('a', 'Nói rõ, xin thêm hai mươi phút phun tận gốc', [('chi_hong', 'Trễ chút mà cả tháng khỏi lo. Cảm ơn em!')], rel='chi_hong'),
                   _o('b', 'Thông tạm cho kịp bán, hẹn chiều quay lại phun', [('chi_hong', 'Chiều em nhớ quay lại nha, chị để phần tô bún.')], rel='chi_hong'))),
            _b('Ống gang nhà bà Ngọc', '🏚️', 'Bà Ngọc đứng chờ ở cửa, tay cầm gói bột thông cống.', [
                ('ba_ngoc', 'Đổ cái này cho nhanh, thợ trước cũng đổ.'),
                ('chu_hai', 'Ống gang cũ gỉ rồi, đổ xút vào là thủng như chơi.'),
                ('ba_ngoc', 'Thế thì làm sao bây giờ?')],
                _c('Ống nhà bà Ngọc',
                   _o('a', 'Soi camera cho bà xem tận mắt', [('ba_ngoc', 'Trời, rễ cây chui cả vào ống. Bà tin cháu rồi.')], rel='ba_ngoc'),
                   _o('b', 'Giải thích kỹ, dùng máy lò xo cắt rễ', [('ba_ngoc', 'Nước rút rồi! Gói bột này bà cất đi.')], rel='ba_ngoc'))),
            _b('Hố ga đầu ngõ', '⚫', 'Trời sắp mưa, ông Lộc giục tổ thợ xuống hố ga.', [
                ('ong_loc', 'Xuống múc luôn đi cháu, đo đạc gì cho mất thời gian!'),
                ('chu_hai', 'Không đo khí thì không ai xuống. Mười phút thôi ông ạ.'),
                ('ong_loc', 'Ừ… năm ngoái phường bên có chuyện, tôi quên mất.'),
                ('me', 'Khí an toàn rồi chú. Cháu xuống, chú canh trên này.')]),
            _b('Cuộn dây lò xo', '🌀', 'Chú Hai tháo cuộn dây lò xo cũ khỏi xe, buộc lên xe của bạn.', [
                ('chu_hai', 'Hai mươi năm chú đi với cuộn dây này. Giờ chú về trông cháu nội.'),
                ('chu_hai', 'Nhớ: đúng bệnh, đúng đồ nghề, đúng giá.'),
                ('chi_hong', 'Từ nay bếp quán chị có chuyện là gọi em đó.'),
                ('ong_loc', 'Phường giao hố ga cả khu cho tổ thợ của cháu.'),
                ('me', 'Cháu sẽ giữ bảng giá của chú, không đổi theo mặt khách.')]),
        ]),
    'homemaker': dict(
        title='Cuốn sổ chợ bìa xanh', emoji='📒',
        keepsake=dict(emoji='📒', name='Cuốn sổ chợ bìa xanh', desc='Năm năm chị Thảo ghi từng khoản tiền chợ. Trang cuối có thêm nét chữ của bạn.'),
        cast={'thao': _p('Chị Thảo', '👩', 'Chủ nhà, giữ sổ chợ', 'homemaker_npc_01'),
              'ba_lanh': _p('Bà Lành', '👵', 'Bà nội, 76 tuổi', 'homemaker_npc_02'),
              'be_su': _p('Bé Su', '👧', 'Học lớp 2, dị ứng tôm', 'homemaker_npc_04'),
              'co_nam': _p('Cô Năm', '🥬', 'Bán rau chợ Mây', 'homemaker_npc_05')},
        beats=[
            _b('Tờ giấy trên tủ lạnh', '📝', 'Chị Thảo dán tờ “Sổ tay nhà” lên tủ lạnh, gõ ngón tay vào dòng chữ đỏ.', [
                ('thao', 'Nhà chị ai cũng có một điều phải nhớ. Su dị ứng tôm, bà ăn nhạt, Cốm ăn cháo.'),
                ('thao', 'Quên gì thì nhìn tủ lạnh, đừng đoán.'),
                ('me', 'Dạ, em chép vào điện thoại luôn ạ.')]),
            _b('Rau xanh bóng lưỡng', '🥬', 'Ở chợ Mây, cô Năm kéo bạn lại, chỉ sang mẹt rau bên cạnh.', [
                ('co_nam', 'Rau muống xanh bóng, to bất thường, không một lỗ sâu: phun thuốc đấy cháu.'),
                ('co_nam', 'Rau nhà cô có lỗ sâu, nhưng ăn yên tâm.'),
                ('me', 'Thế mà cháu cứ tưởng rau đẹp là rau ngon.')]),
            _b('Nồi canh của bà', '🍲', 'Bà Lành nếm thìa canh, đặt mạnh xuống bàn.', [
                ('ba_lanh', 'Nhạt như nước ốc! Ngày xưa bà nấu canh, cả xóm ngửi thấy.'),
                ('thao', 'Bác sĩ dặn mẹ ăn nhạt mà…'),
                ('ba_lanh', 'Bác sĩ có phải ăn đâu!')],
                _c('Bát canh của bà',
                   _o('a', 'Múc riêng bát nhạt cho bà, rắc thêm nắm rau thơm cho dậy mùi', [('ba_lanh', 'Ừ… thơm thì cũng đỡ nhạt.')], rel='ba_lanh'),
                   _o('b', 'Nhờ bà dạy cách nấu canh ngày xưa, nấu cùng bà', [('ba_lanh', 'Ngày xưa bà nấu canh cua mồng tơi, nhớ không quên.')], rel='ba_lanh'))),
            _b('Cổng trường lúc bốn rưỡi', '🏫', 'Một người lạ nắm tay bé Su ở cổng trường.', [
                ('be_su', 'Chị ơi, chú này bảo là bạn của bố em.'),
                ('me', 'Su đứng cạnh chị nhé. Chị gọi mẹ đã.'),
                ('thao', 'Chị không nhờ ai cả! Em giữ con giúp chị, chị về ngay!'),
                ('be_su', 'Chị giỏi thế, như công an luôn.')]),
            _b('Trang cuối cuốn sổ', '📒', 'Chị Thảo đưa bạn cuốn sổ chợ bìa xanh, trang cuối còn trống.', [
                ('thao', 'Năm năm nay chị tự ghi. Từ tháng sau em ghi giúp chị nhé.'),
                ('thao', 'Sổ khớp từng xu thì không ai phải nghi ai.'),
                ('ba_lanh', 'Con bé này thật thà, giao được.'),
                ('be_su', 'Chị ơi, em vẽ chị vào tranh cả nhà rồi!'),
                ('me', 'Em sẽ giữ sổ như chị đã giữ.')]),
        ]),
    'ice_cream': dict(
        title='Cái muỗng của cô Hiền', emoji='🍨',
        keepsake=dict(emoji='🥄', name='Cái muỗng múc kem cán gỗ', desc='Ba mươi năm trong tay cô Hiền, cán gỗ mòn đúng chỗ ngón cái. Viên nào múc bằng nó cũng tròn.'),
        cast={'hien': _p('Cô Hiền', '👩‍🍳', 'Chủ tiệm kem', 'ice_cream_npc_01'),
              'chip': _p('Bé Chíp', '🎒', 'Học sinh lớp 2A', 'ice_cream_npc_02'),
              'ong_tam': _p('Ông Tám', '🥥', 'Khách ruột kem trái dừa', 'ice_cream_npc_03'),
              'mai_anh': _p('Chị Mai Anh', '🎂', 'Trưởng ban phụ huynh lớp 2A', 'ice_cream_npc_04')},
        beats=[
            _b('Tiếng trống tan học', '🔔', 'Bốn giờ rưỡi, trống trường vừa điểm, học sinh ùa ra cổng như ong vỡ tổ.', [
                ('hien', 'Giờ này là giờ của tiệm. Con múc nhanh mà viên nào cũng phải tròn nghe.'),
                ('chip', 'Cô ơi, con lấy ốc quế dâu! Con có đủ tiền rồi nè, con đếm ba lần rồi!'),
                ('hien', 'Đồng nào của tụi nhỏ cũng là tiền để dành. Thối cho đúng.'),
                ('me', 'Dạ, con đếm lại từng đồng trước mặt bé luôn ạ.')]),
            _b('Ông Tám và cái muỗng', '🥥', 'Ông Tám kéo ghế đẩu ra dưới gốc phượng, đặt trái dừa lên đùi.', [
                ('ong_tam', 'Hồi trẻ ông chở kem bằng xe đạp, rao khắp xóm. Một viên kem là sáu mươi lăm gam, không hơn không kém.'),
                ('ong_tam', 'Viên nhỏ là ông biết liền. Không phải ông keo, mà người bán kem phải có cái tâm.'),
                ('hien', 'Ông Tám là thầy dạy múc kem của cô đó con.')],
                _c('Ông Tám nhìn muỗng kem của bạn',
                   _o('a', 'Đặt từng viên lên cân cho ông xem', [('ong_tam', 'Sáu mươi tám gam. Được! Đứa nhỏ này múc có tâm.')], rel='ong_tam'),
                   _o('b', 'Nhờ ông chỉ cách kéo muỗng cho viên tròn', [('ong_tam', 'Kéo một vòng sâu, xoay cổ tay, vo tròn. Đó, thấy chưa? Dễ mà.')], rel='ong_tam'))),
            _b('Đêm cúp điện', '🔌', 'Tối qua cả phố cúp điện ba tiếng. Sáng ra cô Hiền đã đứng chờ bên tủ kem.', [
                ('hien', 'Cô phủ chăn bông lên tủ cả đêm, dặn không ai được mở nắp.'),
                ('hien', 'Giờ mình soi từng hộp. Hộp nào mặt kem lổn nhổn đá là kem đã chảy rồi đông lại.'),
                ('me', 'Bỏ cả hộp hả cô? Tiếc quá…')],
                _c('Hộp kem dâu đông đá lại',
                   _o('a', 'Bỏ hộp kem, ghi vào sổ hao hụt', [('hien', 'Đúng rồi con. Một hộp kem không bằng cái bụng tụi nhỏ.')], rel='hien'),
                   _o('b', 'Hỏi cô cách giữ tủ lạnh lâu khi cúp điện', [('hien', 'Đóng chặt nắp, phủ chăn, bán kem que trước. Ba tiếng vẫn còn cứng.')], rel='hien'))),
            _b('Sinh nhật lớp 2A', '🎂', 'Chị Mai Anh đặt khay kem sinh nhật cho cả lớp, bé Chíp đứng sau lưng háo hức.', [
                ('mai_anh', 'Sáu ly, mỗi ly một viên. Lên tới lớp mất mười phút đó em.'),
                ('chip', 'Hôm nay sinh nhật bạn Bông! Cả lớp hát xong là ăn kem!'),
                ('me', 'Em xếp vào thùng xốp, lót đá gel, lên tới lớp kem vẫn còn cứng.'),
                ('mai_anh', 'Cô chủ nhiệm khen kem ngon, tụi nhỏ ngoan cả buổi chiều.')]),
            _b('Cái muỗng cán gỗ', '🥄', 'Cô Hiền rửa cái muỗng cán gỗ, lau khô rồi đặt vào tay bạn.', [
                ('hien', 'Cái muỗng này cô dùng ba mươi năm. Cán mòn đúng chỗ ngón tay cái.'),
                ('hien', 'Mai cô về quê ít bữa. Tiệm giao con, muỗng cũng giao con.'),
                ('ong_tam', 'Giao đúng người rồi. Viên nào nó múc cũng đủ gam.'),
                ('chip', 'Con vẽ tiệm kem dán lên tủ rồi nè! Có cô với có {anh} luôn!'),
                ('me', 'Con sẽ múc viên nào cũng tròn, như cô.')]),
        ]),
    'com': dict(
        title='Chén nước mắm của dì Bảy', emoji='🍚',
        keepsake=dict(emoji='🫙', name='Cái cối đá giã tỏi ớt', desc='Cối đá của bà ngoại dì Bảy. Tỏi ớt giã tay trong cối này, chén nước mắm mới thơm đúng vị quán.'),
        cast={'bay': _p('Dì Bảy', '👩‍🍳', 'Chủ quán cơm', 'com_npc_01'),
              'binh': _p('Chú Bình', '🛵', 'Xe ôm đầu hẻm', 'com_npc_02'),
              'ngan': _p('Chị Ngân', '🧾', 'Kế toán công ty gần chợ', 'com_npc_03'),
              'suong': _p('Bà Sương', '📿', 'Khách ăn chay ngày rằm', 'com_npc_06')},
        beats=[
            _b('Bốn giờ sáng', '🔥', 'Trời còn tối, dì Bảy đã nhóm xong bếp than, hai nồi cơm reo trên xe.', [
                ('bay', 'Gạo tấm hút ít nước, con đổ lưng đốt tay thôi. Đổ một đốt là nhão cả nồi.'),
                ('bay', 'Nồi cơm trắng thì một đốt. Cơm mà hỏng là cả buổi sáng hỏng theo.'),
                ('me', 'Dạ, con đặt ngón tay đo từng nồi.')]),
            _b('Miếng sườn cháy cạnh', '🍖', 'Chú Bình dựng xe ôm, ngồi xuống ghế nhựa quen thuộc đầu bàn.', [
                ('binh', 'Cơm tấm ngon là miếng sườn hơi cháy cạnh, thơm mùi than.'),
                ('bay', 'Cháy cạnh khác cháy khét nghe con. Mỗi mặt chừng tám tới mười sáu giây, trở một lần.'),
                ('binh', 'Mà giữa miếng thịt không được hồng. Chú ăn sườn quán này mười năm rồi.')],
                _c('Chú Bình hỏi bí quyết nướng sườn',
                   _o('a', 'Đếm giây từng mặt, trở đúng một lần', [('binh', 'Vậy là ra nghề rồi đó con.')], rel='binh'),
                   _o('b', 'Hỏi chú thích sườn nướng kỹ hay vừa', [('binh', 'Chín tới, cháy cạnh chút xíu. Vậy là chú ăn hết dĩa.')], rel='binh'))),
            _b('Mười hai giờ trưa', '🧾', 'Chị Ngân gửi danh sách bốn hộp cơm cho cả phòng, ghi từng dòng.', [
                ('ngan', 'Hộp nào nước mắm cũng để riêng nha em, rưới vô là về tới nơi cơm nhão hết.'),
                ('ngan', 'Có một hộp chay của chị Hà: không hành mỡ, nước tương nha.'),
                ('me', 'Dạ, em ghi tên từng hộp lên nắp luôn.')]),
            _b('Ngày rằm', '🌕', 'Bà Sương ghé quán, tay lần tràng hạt.', [
                ('suong', 'Mỡ hành quán phi bằng mỡ heo phải không con? Bà ăn chay nên dặn trước.'),
                ('bay', 'Dạ, dĩa chay thì muỗng chén riêng, nước tương, không mỡ hành, không canh tôm.'),
                ('suong', 'Quán nhớ bà ăn chay, bà mừng lắm.')],
                _c('Bà Sương hỏi canh có chay không',
                   _o('a', 'Nói thật: canh nấu tôm khô, bà dùng trà đá nha', [('suong', 'Thật thà vậy bà mới yên tâm.')], rel='suong'),
                   _o('b', 'Luộc riêng cho bà chén canh rau', [('suong', 'Con chu đáo quá. Bà cảm ơn nghe.')], rel='suong'))),
            _b('Cái cối đá', '🫙', 'Tối dọn quán, dì Bảy rửa cái cối đá, lau khô rồi đặt vào tay bạn.', [
                ('bay', 'Cối này của bà ngoại dì. Nước mắm quán ngon là nhờ giã tay trong cối này.'),
                ('bay', 'Mai dì đi tái khám ở bệnh viện. Quán giao con, cối cũng giao con.'),
                ('binh', 'Giao đúng người rồi. Dĩa nào nó xới cũng đủ cơm.'),
                ('ngan', 'Cả phòng chị vẫn đặt cơm quán mình nha {anh}!'),
                ('me', 'Con sẽ nếm từng chén nước mắm, như dì.')]),
        ]),
    'nail': dict(
        title='Cây dũa của chị Diệp', emoji='💅',
        keepsake=dict(emoji='🪮', name='Cây dũa thủy tinh của chị Diệp', desc='Chị Diệp mua từ hồi mới học nghề ở spa. Rửa là sạch, hấp là dùng lại, dũa bao nhiêu móng vẫn mịn.'),
        cast={'diep': _p('Chị Diệp', '💅', 'Chủ tiệm nail', 'nail_npc_01'),
              'thao_vy': _p('Chị Thảo Vy', '👰', 'Cô dâu tháng này', 'nail_npc_02'),
              'ba_nam': _p('Bà Năm', '👵', 'Khách ruột, hưu trí', 'nail_npc_05'),
              'co_lan': _p('Cô Lan', '🧺', 'Bán vải ngoài chợ', 'nail_npc_07')},
        beats=[
            _b('Cái bàn bên cửa sổ', '🪟', 'Chị Diệp kê thêm cái bàn nhỏ cạnh cửa sổ, lau sạch, đặt lên đó cái đèn hơ gel.', [
                ('diep', 'Hồi ở spa chị làm cho người ta mười năm. Giờ mở tiệm nhỏ, chị muốn khách ngồi đây thấy yên tâm.'),
                ('diep', 'Yên tâm là sao? Là dụng cụ hấp sạch, dũa mới bóc trước mặt, đèn sáng nào cũng thử.'),
                ('me', 'Dạ, em nhớ: thử đèn, hấp dụng cụ, rồi mới mở cửa.')]),
            _b('Bà Năm và lời dặn', '👵', 'Bà Năm ngồi xuống, xòe hai bàn tay gầy, gân xanh nổi lên.', [
                ('ba_nam', 'Bà uống thuốc loãng máu, trầy một chút là chảy hoài. Con làm nhẹ thôi nghe.'),
                ('diep', 'Khách nào dặn vậy thì mình chỉ đẩy da, không cắt.'),
                ('me', 'Dạ, con làm thật nhẹ, bà cứ ngồi nghỉ nha.')],
                _c('Khóe móng bà Năm có chút da thừa',
                   _o('a', 'Chỉ đẩy da nhẹ, thoa dầu dưỡng', [('ba_nam', 'Nhẹ tay ghê. Bà ngồi mà muốn ngủ luôn.')], rel='ba_nam'),
                   _o('b', 'Hỏi chị Diệp cách nhặt da cho an toàn', [('diep', 'Ngâm nước ấm cho mềm, nhặt phần da chết thôi, không chạm da sống.')], rel='diep'))),
            _b('Cái móng của cô Lan', '🧺', 'Cô Lan chìa bàn tay, giấu ngón trỏ vàng đục dưới mấy ngón kia.', [
                ('co_lan', 'Con sơn gel đen phủ kín giùm cô. Đi bác sĩ cô ngại lắm.'),
                ('diep', 'Cô ơi, móng này phải đi khám trước. Sơn phủ lên là nặng thêm, dụng cụ còn mang nấm qua khách khác.'),
                ('me', 'Phòng khám da liễu phường mở tới năm giờ. Khỏi rồi cô ghé, con làm móng đẹp cho cô.')],
                _c('Cô Lan ngập ngừng',
                   _o('a', 'Viết giùm cô địa chỉ phòng khám', [('co_lan', 'Ừ, để cô đi. Người ta nói thật vậy cô mới tin.')], rel='co_lan'),
                   _o('b', 'Thoa dầu dưỡng tay cho cô, không lấy tiền', [('co_lan', 'Con dễ thương quá. Mai cô đi khám liền.')], rel='co_lan'))),
            _b('Đêm trước đám cưới', '👰', 'Tám giờ tối, chị Thảo Vy chạy tới với cái điện thoại có ảnh mẫu.', [
                ('thao_vy', 'Sáng mai chị cưới! Nối móng, gel nude, đính đá ngón áp út, y như ảnh nha em.'),
                ('diep', 'Lớp nào hơ đủ giờ lớp nấy. Cô dâu cầm hoa, móng bong là cả album thấy.'),
                ('me', 'Em đính đá trước rồi mới phủ top, hơ thêm một lượt cho chắc.'),
                ('thao_vy', 'Trời ơi xinh quá! Mai chị chụp tay cầm hoa cho em coi.')]),
            _b('Cây dũa thủy tinh', '🪮', 'Chị Diệp rửa cây dũa thủy tinh, cho vào tủ hấp, rồi đặt vào tay bạn.', [
                ('diep', 'Cây này theo chị từ hồi học nghề. Rửa là sạch, hấp là dùng lại, dũa êm như lụa.'),
                ('diep', 'Mai chị đi học thêm lớp vẽ móng mấy bữa. Bàn này giao em nghe.'),
                ('ba_nam', 'Giao đúng người rồi. Con nhỏ này nhẹ tay, lại thật thà.'),
                ('co_lan', 'Cô đi khám rồi, móng đỡ nhiều. Bữa nào khỏi hẳn cô ghé {anh} làm móng!'),
                ('me', 'Em sẽ giữ bàn này sạch như chị đã giữ.')]),
        ]),
    'pagoda': dict(
        title='Tiếng chuông chùa Gió Lành', emoji='🔔',
        keepsake=dict(emoji='🪵', name='Cái dùi chuông gỗ mít', desc='Thầy Huệ Minh dùng mấy chục năm, chỗ tay cầm nhẵn bóng. Đánh bằng nó, tiếng chuông trầm và ngân dài.'),
        cast={'thay': _p('Thầy Huệ Minh', '🙏', 'Thầy trụ trì', 'pagoda_npc_01'),
              'nhan': _p('Bà Nhạn', '🍲', 'Trưởng ban trai soạn', 'pagoda_npc_02'),
              'na': _p('Bé Na', '👧', 'Học sinh lớp 4', 'pagoda_npc_05'),
              'ong_bay': _p('Ông Bảy Đò', '👴', 'Chèo đò bến sông ngày trước', 'pagoda_npc_07')},
        beats=[
            _b('Tiếng chuông đầu ngày', '🔔', 'Bốn giờ sáng, sương còn đọng trên hàng cau. Thầy Huệ Minh dắt bạn lên gác chuông.', [
                ('thay', 'Chuông này cả làng góp đồng mà đúc. Năm bão, cành đa quật lõm một góc, từ đó tiếng nó trầm hơn.'),
                ('thay', 'Thỉnh chuông không cần mạnh tay. Chậm, đều, chờ tiếng ngân tắt hẳn rồi mới đánh tiếng sau.'),
                ('me', 'Dạ, con nghe tiếng ngân rồi mới đánh tiếp ạ.')]),
            _b('Ông Bảy dưới bến', '🛶', 'Rằm, ông Bảy Đò chống gậy lên chùa, ngồi nghỉ ở bậc thềm thứ sáu.', [
                ('ong_bay', 'Hồi ông chèo đò, sáng nào nghe chuông chùa là biết sắp tới bến.'),
                ('ong_bay', 'Năm bão đó, cả làng khiêng chuông lên gác, ông cũng ghé vai vô.'),
                ('me', 'Ông kể con nghe nữa đi ông.')],
                _c('Ông Bảy muốn lên tận gác chuông',
                   _o('a', 'Đỡ ông đi từng bậc, nghỉ ở chiếu nghỉ', [('ong_bay', 'Thầy đi chậm như ông. Lên tới nơi rồi, ông sờ được quả chuông rồi.')], rel='ong_bay'),
                   _o('b', 'Mời ông ngồi dưới hiên, con đánh ba tiếng cho ông nghe', [('ong_bay', 'Đó, tiếng đó đó. Y như ngày xưa.')], rel='ong_bay'))),
            _b('Nồi canh của bà Nhạn', '🍲', 'Trưa rằm, bếp chùa nghi ngút khói. Bà Nhạn đưa bạn cái vá.', [
                ('nhan', 'Canh chay ngọt là nhờ nấm với củ cải, chứ không nhờ bột ngọt, càng không nhờ nước mắm.'),
                ('nhan', 'Người ta tin bếp chùa mà ăn. Mình giữ cái tin đó.'),
                ('me', 'Dạ, con nếm bằng chén riêng, không nêm gì ngoài đồ chay ạ.')],
                _c('Bà Nhạn hỏi bạn nêm thế nào',
                   _o('a', 'Thêm chút đường phèn, chút muối', [('nhan', 'Được. Vừa miệng rồi đó.')], rel='nhan'),
                   _o('b', 'Hỏi bà bí quyết nấu nước dùng', [('nhan', 'Củ cải nướng sơ, nấm đông cô ngâm từ sáng, lửa liu riu. Vậy thôi.')], rel='nhan'))),
            _b('Bé Na và hồ sen', '🪷', 'Bé Na chạy lên khoe tờ giấy đặt tên cho mười hai con cá đỏ trong hồ.', [
                ('na', 'Con đặt tên hết rồi! Con to nhất là Chuông, vì nó bơi chậm như tiếng chuông!'),
                ('me', 'Vậy con nhỏ nhất tên gì?'),
                ('na', 'Tên Gió Lành! Con viết bài văn về chùa mình, cô giáo khen lắm.')]),
            _b('Cái dùi chuông', '🪵', 'Sáng nay thầy Huệ Minh không lên gác chuông. Thầy đặt cái dùi gỗ mít vào tay bạn.', [
                ('thay', 'Dùi này thầy dùng ba mươi năm. Tay cầm nhẵn đúng chỗ.'),
                ('thay', 'Từ mai con thỉnh chuông sáng. Không cần hay, chỉ cần đều.'),
                ('ong_bay', 'Dưới bến ông nghe rồi. Tiếng chuông trầm y như ngày xưa.'),
                ('na', 'Thầy ơi, con viết về thầy trong bài văn luôn rồi!'),
                ('me', 'Con sẽ thỉnh chuông chậm và đều, như thầy.')]),
        ]),
    # ------------------------------------------------------------ ✈️ Hãng bay Cánh Cò
    'pilot': dict(
        title='Đường bay ra đảo', emoji='🛩️',
        keepsake=dict(emoji='🧭', name='Chiếc la bàn cũ của chị Vân', desc='La bàn đồng theo chị Vân từ chuyến bay đầu tiên. Kim vẫn chỉ đúng hướng về nhà.'),
        cast={'van': _p('Cơ trưởng Vân', '🧑‍✈️', 'Cơ trưởng, người kèm bạn bay', 'pilot_npc_01'),
              'man': _p('Chú Mẫn', '🔧', 'Thợ máy trưởng', 'pilot_npc_04'),
              'thu': _p('Chị Thu', '💁', 'Tiếp viên trưởng', 'pilot_npc_03'),
              'na': _p('Bé Na', '👧', 'Học sinh lớp 6 mơ làm phi công', 'pilot_npc_07')},
        beats=[
            _b('Chậm mà không sót', '✅', 'Chị Vân nhìn bạn đọc checklist rất lâu.', [
                ('van', 'Em đọc checklist chậm quá.'),
                ('me', 'Dạ, em sợ bỏ sót dòng nào.'),
                ('van', 'Chậm mà không sót thì chị chịu. Nhanh mà sót thì chị không chịu.')]),
            _b('Vệt dầu dưới cánh', '🔧', 'Chú Mẫn gọi bạn ra sân đỗ trước giờ bay.', [
                ('man', 'Cháu nhìn cái vệt này xem, dầu hay nước mưa?'),
                ('me', 'Dạ… cháu không chắc.'),
                ('man', 'Không chắc thì hỏi. Hỏi không mất gì, bay mà sai thì mất nhiều.')],
               _c('Học phân biệt vệt dầu',
                  _o('a', 'Xin chú Mẫn dạy cách quệt tay, ngửi mùi', [('man', 'Dầu máy bay mùi hắc, sờ vào trơn tay. Nước mưa thì không. Nhớ đời nhé.')], rel='man'),
                  _o('b', 'Chụp ảnh gửi chị Vân hỏi luôn', [('van', 'Hỏi đúng người rồi. Nhưng lần sau ra đó với chú Mẫn, học tận tay.')], rel='van'))),
            _b('Lá thư của Bé Na', '✉️', 'Có một lá thư gửi “tổ bay Cánh Cò”.', [
                ('thu', 'Bé Na viết thư về hãng, chị mang tới cho em đây.'),
                ('na', 'Con muốn làm phi công. Nhưng con học Toán dở lắm.'),
                ('me', 'Phải trả lời Na cho thật lòng mới được.')],
               _c('Viết gì cho Na?',
                  _o('a', 'Kể thật: phải học Toán, học tiếng Anh, và đừng ngại hỏi', [('na', 'Con dán thư lên bàn học rồi, ngày nào con cũng đọc!')], rel='na'),
                  _o('b', 'Gửi Na tấm ảnh buồng lái có chữ ký cả tổ bay', [('na', 'Con khoe cả lớp! Cô giáo bảo muốn lái máy bay thì học giỏi Toán.')], rel='na'))),
            _b('Giông trên đảo', '⛈️', 'Giông kéo tới đảo sớm hơn dự báo.', [
                ('van', 'Radar đỏ hết phía trước rồi. Em tính sao?'),
                ('me', 'Mình còn dầu chờ hai mươi phút, sân bay dự bị là Cần Thơ.'),
                ('thu', 'Khoang khách thắt dây hết rồi, hai đứa cứ quyết.'),
                ('van', 'Nói tiếp đi. Chị nghe.')],
               _c('Quyết định cuối cùng',
                  _o('a', 'Bay chờ mười lăm phút, không tan thì đi Cần Thơ', [('van', 'Có mốc giờ, có đường lui. Đó là cách nghĩ của một cơ trưởng.')], rel='van'),
                  _o('b', 'Đi Cần Thơ luôn, không chờ', [('van', 'Chắc ăn. Khách về muộn, nhưng về đủ. Chị ký.')], rel='van'))),
            _b('Chiếc la bàn', '🧭', 'Chị Vân gói một vật nhỏ trong khăn tay.', [
                ('van', 'Chị bay chặng cuối trước khi lên làm huấn luyện.'),
                ('van', 'La bàn này theo chị từ chuyến đầu tiên. Giờ nó theo em.'),
                ('man', 'Chú đứng dưới sân đỗ mười lăm năm, lần đầu thấy chị Vân rưng rưng đấy.'),
                ('me', 'Em sẽ bay như chị dạy: chậm mà không sót.')]),
        ]),
    'flight_attendant': dict(
        title='Khoang khách nhỏ', emoji='💺',
        keepsake=dict(emoji='📌', name='Chiếc ghim cài hình con cò', desc='Ghim cài của chị Thu từ hồi mới bay. Cánh cò đã bạc màu vì nắng đảo.'),
        cast={'thu': _p('Chị Thu', '💁', 'Tiếp viên trưởng', 'flight_attendant_npc_01'),
              'chin': _p('Bà Chín', '👵', 'Hành khách lần đầu đi máy bay', 'flight_attendant_npc_03'),
              'mai': _p('Chị Mai', '👩', 'Mẹ của bé Bơ', 'flight_attendant_npc_05'),
              'tu': _p('Ông Tư', '👴', 'Cựu chiến binh về thăm đảo', 'flight_attendant_npc_04')},
        beats=[
            _b('Nụ cười ở cửa tàu', '🚪', 'Chị Thu đứng cạnh bạn ở cửa, nhìn bạn chào khách.', [
                ('thu', 'Em chào khách như chào người lạ. Chào như chào hàng xóm xem.'),
                ('me', 'Dạ… “Con chào bà, bà ra đảo thăm cháu hả bà?”'),
                ('chin', 'Ừ, thăm thằng cháu đích tôn! Cô tiếp viên dễ thương ghê.')]),
            _b('Túi xoài của bà Chín', '🥭', 'Bà Chín ôm túi xoài, không chịu cất lên hộc.', [
                ('chin', 'Xoài chín cây, để trên đó dập hết cô ơi.'),
                ('thu', 'Túi này để dưới gầm ghế phía trước được, miễn không chắn lối đi.'),
                ('me', 'Để con xếp cho bà nhé.')],
               _c('Cất túi xoài',
                  _o('a', 'Xếp túi dưới gầm ghế, dặn bà gác chân cho thoải mái', [('chin', 'Vậy mà bà cứ lo. Tới đảo bà biếu cô hai trái.')], rel='chin'),
                  _o('b', 'Nhờ chị Thu tìm chỗ trong tủ bếp', [('thu', 'Tủ bếp để vừa một túi. Lần này thôi nhé bà.')], rel='thu'))),
            _b('Bé Bơ đau tai', '👶', 'Tàu hạ độ cao, bé Bơ khóc thét.', [
                ('mai', 'Chị xin lỗi mọi người, bé đau tai…'),
                ('me', 'Chị cho bé bú hoặc uống từng ngụm nước lúc này nhé.'),
                ('mai', 'Nín rồi! Sao em biết hay vậy?'),
                ('thu', 'Tiếp viên nào cũng thuộc bài này. Giờ em thuộc rồi đấy.')]),
            _b('Tấm ảnh cũ của ông Tư', '📷', 'Ông Tư nhìn ra cửa sổ rất lâu.', [
                ('tu', 'Ngày xưa ông ra đảo bằng tàu thủy, say sóng ba ngày.'),
                ('tu', 'Giờ bay năm mươi phút. Đồng đội ông không ai được đi thế này.'),
                ('me', 'Ông kể thêm cho con nghe được không ạ?')],
               _c('Ông Tư muốn gửi lời',
                  _o('a', 'Xin chị Thu đọc lời chào mừng ông trên loa', [('thu', '“Tổ bay hân hạnh đưa bác Tư về thăm đảo.” Cả khoang vỗ tay.'),
                                                                        ('tu', 'Ông đi bao nhiêu chuyến, lần đầu có người gọi tên ông.')], rel='tu'),
                  _o('b', 'Ngồi ghế phụ cạnh ông, nghe ông kể tới lúc hạ cánh', [('tu', 'Kể được với người trẻ, ông thấy nhẹ lòng.')], rel='tu'))),
            _b('Chiếc ghim con cò', '📌', 'Chị Thu tháo chiếc ghim trên ngực áo.', [
                ('thu', 'Chị chuyển lên làm huấn luyện tiếp viên mới rồi.'),
                ('thu', 'Ghim này của chị từ ngày đầu đi bay. Giờ em cài nhé.'),
                ('chin', 'Lần sau bà bay, bà vẫn tìm cô tiếp viên này.'),
                ('me', 'Em sẽ giữ khoang khách như chị giữ: nhỏ nhẹ mà chắc chắn.')]),
        ]),
    # ------------------------------------------------------------ Công ty CP Cánh Diều (chương 5)
    'hr_admin': dict(
        title='Người giữ hồ sơ', emoji='🗂️',
        keepsake=dict(emoji='🗝️', name='Chìa khóa tủ hồ sơ nhân sự', desc='Tủ sắt màu xám ở phòng nhân sự Cánh Diều. Chị Huyền giao lại cho bạn.'),
        cast={'huyen': _p('Chị Huyền', '👩‍💼', 'Trưởng phòng Hành chính – Nhân sự', 'hr_admin_npc_01'),
              'quan': _p('Anh Quân', '👨‍💼', 'Giám đốc Cánh Diều', 'hr_admin_npc_02'),
              'linh': _p('Linh', '🧑‍💻', 'Nhân viên kinh doanh', 'hr_admin_npc_03'),
              'lam': _p('Chú Lâm', '🧵', 'Tổ trưởng xưởng may', 'hr_admin_npc_04'),
              'dung': _p('Anh Dũng', '🪡', 'Thợ may lâu năm', 'hr_admin_npc_06')},
        beats=[
            _b('Tủ hồ sơ màu xám', '🗂️', 'Ngày đầu ở phòng nhân sự Cánh Diều.', [
                ('huyen', 'Bốn mươi người, bốn mươi bộ hồ sơ. Mỗi tờ giấy ở đây là chuyện cơm áo của một nhà đấy em.'),
                ('huyen', 'Sai một ngày công là người ta thiếu tiền đong gạo.'),
                ('me', 'Dạ, em soát từng ô, chỗ nào chưa chắc em hỏi chị.')]),
            _b('Linh quên quẹt thẻ', '🕗', 'Có người đứng chờ trước cửa phòng nhân sự.', [
                ('linh', 'Tuần này em quên quẹt thẻ ba lần, bảng công ghi em thiếu giờ. Em đi gặp khách thật mà!'),
                ('linh', 'Bị trừ lương thì tháng này em hết tiền trọ.'),
                ('me', 'Mình xem lịch gặp khách với tin nhắn của Linh nhé.')],
                _c('Bạn giúp Linh',
                   _o('a', 'Đối chiếu lịch gặp khách, làm giấy xác nhận công cho Linh', [('linh', 'Có giấy xác nhận rồi! Từ mai em đặt báo thức quẹt thẻ.')], rel='linh'),
                   _o('b', 'Chỉ Linh viết đơn giải trình gửi chị Huyền', [('huyen', 'Đơn viết rõ ràng thế này thì chị duyệt ngay.')], rel='huyen'))),
            _b('Xưởng thiếu người', '🧵', 'Chú Lâm sang phòng nhân sự, tay còn cầm thước dây.', [
                ('lam', 'Đơn balo cho trường học dồn về, tổ chú thiếu ba thợ. Tuyển gấp giùm chú!'),
                ('me', 'Dạ, chiều nay cháu đăng tin, mai lọc hồ sơ, ngày kia mời thử tay nghề.'),
                ('lam', 'Nhanh vậy thì chú mời cả phòng ly chè.')]),
            _b('Cháu của giám đốc', '⚠️', 'Anh Quân ghé bàn bạn, tay cầm một bộ hồ sơ.', [
                ('quan', 'Cháu anh nộp vào vị trí kế toán kho. Khỏi phỏng vấn, làm hợp đồng luôn cho anh.'),
                ('quan', 'Người nhà cả, tin được.'),
                ('me', 'Dạ, hồ sơ của bạn ấy còn thiếu bằng kế toán. Em xin xếp bạn phỏng vấn như mọi người ạ.')],
                _c('Bạn làm gì?',
                   _o('a', 'Xếp lịch phỏng vấn, nói rõ quy trình công bằng cho mọi người', [('quan', 'Ừ… quy trình anh ký mà anh lại phá thì kỳ. Cứ phỏng vấn đi.')], rel='quan'),
                   _o('b', 'Báo chị Huyền để chị nói chuyện với giám đốc', [('huyen', 'Em làm đúng. Chuyện này để chị nói, em yên tâm.')], rel='huyen')),
                days=6, served=14, gap=1),
            _b('Bảng công không sai một ô', '🏅', 'Cuối năm, cả công ty họp ở xưởng.', [
                ('quan', 'Năm nay không ai khiếu nại lương, không ai bị trừ oan một ngày công.'),
                ('dung', 'Hồi con tôi nằm viện, phòng nhân sự xếp ca cho tôi. Tôi nhớ mãi.'),
                ('huyen', 'Từ tháng sau, em giữ chìa khóa tủ hồ sơ nhé. Chị tin em.'),
                ('me', 'Dạ, em sẽ giữ cẩn thận từng tờ.')],
                days=9, served=22, gap=2, level=4),
        ]),
    'secretary': dict(
        title='Cuốn sổ lịch bìa đỏ', emoji='📅',
        keepsake=dict(emoji='📓', name='Cuốn sổ lịch bìa đỏ', desc='Sổ lịch của Anh Quân. Trang nào cũng có nét chữ của bạn.'),
        cast={'quan': _p('Anh Quân', '👨‍💼', 'Giám đốc Cánh Diều', 'secretary_npc_01'),
              'khue': _p('Chị Khuê', '🌸', 'Trợ lý cũ, nay ở phòng kinh doanh', 'secretary_npc_02'),
              'luc': _p('Ông Lực', '🧔', 'Chủ xưởng vải Lực Thành', 'secretary_npc_03'),
              'nhi': _p('Nhi', '💁', 'Lễ tân', 'secretary_npc_06')},
        beats=[
            _b('Chiếc bàn trước cửa phòng giám đốc', '📅', 'Ngày đầu ngồi bàn thư ký.', [
                ('khue', 'Bàn này chị ngồi năm năm. Sếp quyết nhanh, đổi ý còn nhanh hơn, em nhớ ghi bút chì.'),
                ('quan', 'Lịch của anh là của em. Anh chỉ cần biết mấy giờ đi đâu.'),
                ('me', 'Dạ, em ghi hết vào sổ, có gì đổi em báo anh liền.')]),
            _b('Nhi run tay', '📞', 'Quầy lễ tân có tiếng to tiếng nhỏ.', [
                ('nhi', 'Có ông khách quát em vì không cho gặp giám đốc. Em run quá, không dám nghe máy nữa.'),
                ('nhi', 'Chị Khuê chuyển phòng rồi, em không biết hỏi ai.'),
                ('me', 'Không sao, mình cùng soạn mấy câu trả lời khách khó nhé.')],
                _c('Bạn giúp Nhi',
                   _o('a', 'Ngồi cạnh Nhi nghe máy một buổi, viết sẵn mấy câu trả lời', [('nhi', 'Có tờ giấy này em đọc theo được rồi. Hết run luôn!')], rel='nhi'),
                   _o('b', 'Hẹn chị Khuê ghé dạy Nhi giờ nghỉ trưa', [('khue', 'Chị dạy Nhi mẹo cũ của chị rồi. Hai đứa giỏi lắm.')], rel='khue'))),
            _b('Ông Lực đòi gặp', '🧔', 'Ông Lực tới mà không hẹn trước.', [
                ('luc', 'Tôi chờ tiền vải ba tuần rồi! Hôm nay không gặp được giám đốc thì tôi ngồi đây luôn.'),
                ('me', 'Dạ, cháu mời bác ly trà. Anh Quân họp tới 10 giờ, cháu xếp bác gặp lúc 10 giờ 15 được không ạ?'),
                ('luc', 'Ờ… có giờ hẹn rõ ràng vậy thì tôi chờ.')]),
            _b('Tờ báo giá trên bàn sếp', '⚠️', 'Ông Lực hạ giọng hỏi bạn trong phòng chờ.', [
                ('luc', 'Báo giá của xưởng bên kia nằm trên bàn giám đốc đúng không? Cháu chụp giùm bác một tấm.'),
                ('luc', 'Bác giảm giá cho Cánh Diều mà. Bác cháu mình với nhau, ai biết đâu.'),
                ('me', 'Dạ, giấy tờ trên bàn giám đốc cháu không được đưa ai xem ạ.')],
                _c('Bạn làm gì?',
                   _o('a', 'Từ chối nhẹ nhàng, mời ông gửi báo giá mới để công ty so công bằng', [('luc', 'Cô cậu này kín miệng thật. Thôi, tôi về làm báo giá cho tử tế.')], rel='luc'),
                   _o('b', 'Báo Anh Quân chuyện Ông Lực hỏi', [('quan', 'Cảm ơn em. Anh cất báo giá vào tủ, rồi nói chuyện thẳng với ông ấy.')], rel='quan')),
                days=6, served=14, gap=1),
            _b('Hội nghị khách hàng', '🎉', 'Hội trường tầng 3, một trăm khách mời.', [
                ('quan', 'Một trăm khách, không ai lạc chỗ ngồi, không ai phải chờ. Em lo hết đấy à?'),
                ('nhi', 'Cả quầy lễ tân làm theo bảng phân công của chị đó ạ.'),
                ('quan', 'Từ tháng sau em làm trợ lý giám đốc. Cuốn sổ lịch này giao em giữ.'),
                ('me', 'Dạ, em sẽ giữ lịch của anh cẩn thận từng phút.')],
                days=9, served=22, gap=2, level=4),
        ]),
    'it_helpdesk': dict(
        title='Sao lưu trước, sửa sau', emoji='🖥️',
        keepsake=dict(emoji='🔑', name='Chìa khóa phòng máy chủ', desc='Phòng máy nhỏ cạnh kho Cánh Diều. Anh Long dán tên bạn lên cửa.'),
        cast={'long': _p('Anh Long', '🧑‍💻', 'Trưởng nhóm IT', 'it_helpdesk_npc_01'),
              'quan': _p('Anh Quân', '👨‍💼', 'Giám đốc Cánh Diều', 'it_helpdesk_npc_02'),
              'hang': _p('Cô Hằng', '📒', 'Kế toán trưởng', 'it_helpdesk_npc_03'),
              'lam': _p('Chú Lâm', '🧵', 'Tổ trưởng xưởng may', 'it_helpdesk_npc_05'),
              'nhi': _p('Nhi', '💁', 'Lễ tân', 'it_helpdesk_npc_06')},
        beats=[
            _b('Ba mươi cái máy, một cái tua vít', '🖥️', 'Ngày đầu ở bàn IT.', [
                ('long', 'Ba mươi máy tính, hai máy in, một cục wifi hay dỗi. Đây là cả vương quốc của mình.'),
                ('long', 'Luật đầu tiên: sao lưu trước, sửa sau.'),
                ('me', 'Dạ, em ghi to lên giấy dán màn hình luôn.')]),
            _b('Máy in tem của xưởng', '🖨️', 'Chú Lâm bê nguyên cái máy in sang bàn bạn.', [
                ('lam', 'Con máy in tem này kẹt giấy từ sáng, xưởng không in được tem balo. Cứu chú!'),
                ('lam', 'Chú lỡ lấy dao rọc giấy khều ra, giờ nó kêu rè rè.'),
                ('me', 'Chú để cháu xem. Lần sau chú gọi cháu trước khi khều nha.')],
                _c('Sửa xong rồi, bạn làm gì thêm?',
                   _o('a', 'Dán tờ hướng dẫn gỡ giấy kẹt ngay cạnh máy', [('lam', 'Có tờ hướng dẫn này, thằng Dũng tự gỡ được luôn. Giỏi!')], rel='lam'),
                   _o('b', 'Dạy Chú Lâm gỡ giấy tận tay một lần', [('lam', 'Chú làm được rồi! Lần sau chú tự làm, không khều bằng dao nữa.')], rel='lam'))),
            _b('Cô Hằng lưu đè file', '📒', 'Cô Hằng ngồi im, mặt tái mét.', [
                ('hang', 'Cô lỡ lưu đè file sổ quỹ cả quý. Mai kiểm toán tới rồi!'),
                ('me', 'Cô đừng lo, ổ chung tối nào cũng sao lưu. Mình lấy lại bản tối qua nhé.'),
                ('hang', 'Trời ơi, cô sợ mất số liệu hơn sợ ma. Cảm ơn con.')]),
            _b('Phần mềm đọc tin nhắn', '⚠️', 'Anh Quân gọi bạn vào phòng, đóng cửa lại.', [
                ('quan', 'Em cài cho anh phần mềm đọc tin nhắn của nhân viên. Anh muốn biết ai nói xấu công ty.'),
                ('quan', 'Máy công ty mà, anh có quyền chứ.'),
                ('me', 'Dạ, đọc tin nhắn riêng của người ta là xâm phạm đời tư, công ty có thể bị kiện ạ.')],
                _c('Bạn làm gì?',
                   _o('a', 'Từ chối, đề xuất hộp thư góp ý ẩn danh cho nhân viên', [('quan', 'Hộp góp ý… ừ, nghe được thật lòng mà không ai bị soi. Làm đi em.')], rel='quan'),
                   _o('b', 'Nhờ Anh Long cùng giải thích quy định cho giám đốc', [('long', 'Em làm đúng. Có việc kỹ thuật làm được nhưng không được làm.')], rel='long')),
                days=6, served=14, gap=1),
            _b('Đêm mưa bão', '⛈️', 'Mưa to, mất điện cả khu.', [
                ('long', 'Mất điện ba tiếng mà máy chủ vẫn sống, dữ liệu không mất một dòng.'),
                ('nhi', 'Sáng nay cả công ty mở máy lên là chạy, như chưa có gì xảy ra luôn ạ.'),
                ('quan', 'Bộ lưu điện em đề xuất hồi tháng trước cứu cả công ty đấy.'),
                ('long', 'Chìa khóa phòng máy chủ, từ giờ em giữ một chiếc.')],
                days=9, served=22, gap=2, level=4),
        ]),
}


# ------------------------------------------------------------------ build
def _build() -> dict:
    """Give every beat its id, default trigger and normalised lines."""
    for cid, arc in ARCS.items():
        for i, beat in enumerate(arc['beats']):
            beat['id'] = f'{cid}_{i + 1}'
            when = dict(served=0, days=0, level=1, gap=0, metric=None)
            when.update(WHEN[min(i, len(WHEN) - 1)])
            when.update(beat['when'])
            beat['when'] = when
            beat['lines'] = [_norm(x) for x in beat['lines']]
            if beat['choice']:
                for opt in beat['choice']['options']:
                    opt['reply'] = [_norm(x) for x in opt['reply']]
    return {cid: {b['id']: i for i, b in enumerate(arc['beats'])} for cid, arc in ARCS.items()}


def _norm(line) -> dict:
    who, text = line[0], line[1]
    need = tuple(line[2]) if len(line) > 2 else None
    return dict(who=who, text=text, need=need)


BEAT_INDEX = _build()


# ------------------------------------------------------------------ helpers
def _core():
    from . import engine
    return engine


def _gender(s: dict) -> str:
    j = s.get('journey') if isinstance(s.get('journey'), dict) else {}
    g = j.get('gender')
    return g if g in ('male', 'female') else 'none'


def resolve(text, gender: str, name: str = '') -> str:
    """Pick the gender variant, then fill {anh} {Anh} {thay} {Thay} {name}."""
    if isinstance(text, dict):
        text = text.get(gender) or text['none']
    for key, forms in TOKENS.items():
        text = text.replace('{' + key + '}', forms[gender])
    return text.replace('{name}', name or 'bạn')


def _speaker(arc: dict, who: str, s: dict) -> tuple[str, str]:
    if who == 'me':
        return (s.get('name') or 'Bạn'), '🙂'
    p = arc['cast'][who]
    return p['name'], p['emoji']


def _lines(s: dict, cid: str, rows: list, picks: dict) -> list[dict]:
    arc, g, name = ARCS[cid], _gender(s), s.get('name') or ''
    out = []
    for row in rows:
        if row['need'] and picks.get(row['need'][0]) != row['need'][1]:
            continue
        nm, emoji = _speaker(arc, row['who'], s)
        out.append(dict(who=row['who'], name=nm, emoji=emoji, text=resolve(row['text'], g, name)))
    return out


def _place(cid: str) -> str:
    return CAREER_META.get(cid, {}).get('place', cid)


def _level(c: dict) -> int:
    return 1 + int(c.get('xp', 0)) // 90


def initial() -> dict:
    return dict(version=VERSION, seq=0, queue=[], arcs={})


def _arc_state(st: dict, cid: str) -> dict:
    return st['arcs'].setdefault(cid, dict(seen=[], picks={}, last=0))


def migrate(s: dict) -> dict:
    """Saves from before career stories get an empty book (setdefault only)."""
    st = s.get('stories')
    if not isinstance(st, dict):
        s['stories'] = st = initial()
    for k, v in initial().items():
        st.setdefault(k, copy.deepcopy(v))
    return st


# ------------------------------------------------------------------ triggers
def next_beat(s: dict, cid: str) -> dict | None:
    arc = ARCS.get(cid)
    if not arc:
        return None
    a = s['stories']['arcs'].get(cid) or dict(seen=[])
    n = len(a['seen'])
    return arc['beats'][n] if n < len(arc['beats']) else None


def due(s: dict, cid: str) -> bool:
    """Is the next beat of this workplace due now (and not already queued)?"""
    st = s['stories']
    beat = next_beat(s, cid)
    c = s['careers'].get(cid)
    if not beat or not c or any(q['career'] == cid for q in st['queue']):
        return False
    w = beat['when']
    a = st['arcs'].get(cid) or dict(seen=[], last=0)
    day = int(c.get('day', 1))
    metrics = c.get('metrics', {})
    if int(metrics.get('served', 0)) < w['served'] or day - 1 < w['days'] or _level(c) < w['level']:
        return False
    if w['metric'] and int(metrics.get(w['metric'][0], 0)) < w['metric'][1]:
        return False
    if a['seen'] and w['gap']:
        since = day - a['last'] if day >= a['last'] else 10**6   # reset_career: time has passed
        if since < w['gap']:
            return False
    return True


def check(s: dict, cid: str) -> dict | None:
    """Queue the next beat of `cid` when it is due. Returns the queued item."""
    if cid not in ARCS or not due(s, cid):
        return None
    st = s['stories']
    beat = next_beat(s, cid)
    st['seq'] += 1
    day = int(s['careers'][cid].get('day', 1))
    item = dict(id=f's{st["seq"]}', career=cid, beat=beat['id'], day=day)
    st['queue'].append(item)
    _arc_state(st, cid)['last'] = day
    return item


def after(s: dict, career: str | None, action: str, result: dict) -> None:
    """Runs after every successful career action, next to journey.after()."""
    migrate(s)
    if career not in ARCS:
        return
    item = check(s, career)
    if item:
        beat = ARCS[career]['beats'][BEAT_INDEX[career][item['beat']]]
        result['story'] = dict(id=item['id'], career=career, title=beat['title'], emoji=beat['emoji'])


# ------------------------------------------------------------------ commands
def _take(s: dict, qid) -> tuple[dict, dict, dict]:
    e = _core()
    st = s['stories']
    e.need(isinstance(qid, str), 'Câu chuyện không hợp lệ.')
    item = next((q for q in st['queue'] if q['id'] == qid), None)
    e.need(item is not None, 'Câu chuyện này đã khép lại rồi.', 'story_missing')
    beat = ARCS[item['career']]['beats'][BEAT_INDEX[item['career']][item['beat']]]
    return item, beat, _arc_state(st, item['career'])


def _close(s: dict, item: dict, beat: dict, a: dict) -> None:
    st = s['stories']
    st['queue'] = [q for q in st['queue'] if q['id'] != item['id']]
    a['seen'].append(beat['id'])
    c = s['careers'][item['career']]
    _core().log(s, c, 'story', f'Truyện nghề · {beat["title"]}')


def action(s: dict, career: str | None, name: str, p: dict) -> tuple[dict, dict]:
    """`st_*` commands. `career` is ignored, like `jr_*`."""
    e = _core()
    need = e.need
    migrate(s)
    result = dict(message='', effects=[])
    if name == 'st_seen':
        need(set(p) <= {'id'}, 'Dữ liệu câu chuyện không hợp lệ.')
        item, beat, a = _take(s, p.get('id'))
        need(not beat['choice'], 'Câu chuyện này đang chờ bạn chọn một cách.', 'story_choice')
        _close(s, item, beat, a)
        result['story'] = dict(id=item['id'], career=item['career'], reply=[], note=None)
    elif name == 'st_choose':
        need(set(p) <= {'id', 'option'}, 'Dữ liệu câu chuyện không hợp lệ.')
        item, beat, a = _take(s, p.get('id'))
        need(bool(beat['choice']), 'Câu chuyện này không có lựa chọn.', 'story_no_choice')
        opt = next((o for o in beat['choice']['options'] if o['id'] == p.get('option')), None)
        need(opt is not None, 'Lựa chọn không hợp lệ.')
        cid = item['career']
        c = s['careers'][cid]
        notes = []
        rel = ARCS[cid]['cast'].get(opt['rel']) if opt['rel'] else None
        if rel and rel.get('npc'):
            c['relationships'][rel['npc']] = min(100, c['relationships'].get(rel['npc'], 0) + REL_BUMP)
            notes.append(f'{rel["name"]} quý bạn thêm một chút.')
        if opt['coins']:
            e.money(s, c, opt['coins'], f'Khép chuyện: {beat["title"]}', category='story_reward')
            notes.append(f'+{opt["coins"]} xu vào quỹ {_place(cid)}.')
        a['picks'][beat['id']] = opt['id']
        _close(s, item, beat, a)
        result['story'] = dict(id=item['id'], career=cid, pick=opt['id'], label=opt['label'],
                               reply=_lines(s, cid, opt['reply'], a['picks']), note=' '.join(notes) or None)
    else:
        raise e.GameError('Thao tác truyện nghề không hợp lệ.', 'unknown_action')
    cid = result['story']['career']
    arc = ARCS[cid]
    if len(s['stories']['arcs'][cid]['seen']) == len(arc['beats']):
        result['story']['keepsake'] = copy.deepcopy(arc['keepsake'])
        result['message'] = f'Trọn truyện “{arc["title"]}”. Kỷ vật: {arc["keepsake"]["name"]}.'
    e.validate_state(s)
    return s, result


# ------------------------------------------------------------------ views
def _due_view(s: dict, item: dict) -> dict:
    cid = item['career']
    arc = ARCS[cid]
    i = BEAT_INDEX[cid][item['beat']]
    beat = arc['beats'][i]
    picks = s['stories']['arcs'].get(cid, {}).get('picks', {})
    g = _gender(s)
    choice = None
    if beat['choice']:
        choice = dict(prompt=resolve(beat['choice']['prompt'], g, s.get('name')),
                      options=[dict(id=o['id'], label=resolve(o['label'], g, s.get('name'))) for o in beat['choice']['options']])
    last = i == len(arc['beats']) - 1
    return dict(id=item['id'], career=cid, beat=beat['id'], step=i + 1, total=len(arc['beats']), title=beat['title'],
                emoji=beat['emoji'], arc=arc['title'], arc_emoji=arc['emoji'], place=_place(cid),
                lines=_lines(s, cid, beat['lines'], picks), choice=choice, last=last,
                keepsake=tree_copy(arc['keepsake']) if last else None)


def public(s: dict) -> dict:
    st = s.get('stories') if isinstance(s.get('stories'), dict) else initial()
    queued = {q['career']: q['id'] for q in st.get('queue', [])}
    arcs = []
    for cid in CAREERS:
        arc = ARCS.get(cid)
        if not arc:
            continue
        a = st.get('arcs', {}).get(cid) or dict(seen=[], picks={})
        n = len(a['seen'])
        done = n >= len(arc['beats'])
        beats = []
        for bid in a['seen']:
            b = arc['beats'][BEAT_INDEX[cid][bid]]
            pick = a['picks'].get(bid)
            label = next((o['label'] for o in (b['choice'] or {}).get('options', []) if o['id'] == pick), None)
            beats.append(dict(title=b['title'], emoji=b['emoji'], pick=label))
        nxt = None if done else arc['beats'][n]
        arcs.append(dict(career=cid, title=arc['title'], emoji=arc['emoji'], seen=n, total=len(arc['beats']), done=done,
                         hint=nxt['hint'] if nxt else None, pending=queued.get(cid),
                         keepsake=tree_copy(arc['keepsake']) if done else None, beats=beats))
    return dict(due=[_due_view(s, q) for q in st.get('queue', [])], arcs=arcs)


# ------------------------------------------------------------------ validation
def validate(s: dict) -> None:
    e = _core()
    need, integer = e.need, e.integer
    st = s.get('stories')
    need(isinstance(st, dict) and set(initial()) <= set(st), 'Bản lưu thiếu dữ liệu truyện nghề.', 'invalid_save')
    need(st['version'] == VERSION, 'Phiên bản truyện nghề không hợp lệ.', 'invalid_save')
    integer(st['seq'], 0, 10**9)
    need(isinstance(st['arcs'], dict) and set(st['arcs']) <= set(ARCS), 'Truyện nghề không hợp lệ.', 'invalid_save')
    for cid, a in st['arcs'].items():
        need(isinstance(a, dict) and set(a) == {'seen', 'picks', 'last'}, 'Truyện nghề không hợp lệ.', 'invalid_save')
        ids = [b['id'] for b in ARCS[cid]['beats']]
        need(isinstance(a['seen'], list) and a['seen'] == ids[:len(a['seen'])], 'Tiến trình truyện nghề không hợp lệ.', 'invalid_save')
        integer(a['last'], 0, 10**9)
        need(isinstance(a['picks'], dict), 'Lựa chọn truyện nghề không hợp lệ.', 'invalid_save')
        for bid, oid in a['picks'].items():
            need(bid in a['seen'], 'Lựa chọn truyện nghề không hợp lệ.', 'invalid_save')
            beat = ARCS[cid]['beats'][BEAT_INDEX[cid][bid]]
            need(bool(beat['choice']) and oid in [o['id'] for o in beat['choice']['options']],
                 'Lựa chọn truyện nghề không hợp lệ.', 'invalid_save')
    need(isinstance(st['queue'], list) and len(st['queue']) <= QUEUE_MAX, 'Hàng chờ truyện nghề không hợp lệ.', 'invalid_save')
    seen_ids, seen_careers = set(), set()
    for q in st['queue']:
        need(isinstance(q, dict) and set(q) == {'id', 'career', 'beat', 'day'}, 'Hàng chờ truyện nghề không hợp lệ.', 'invalid_save')
        need(isinstance(q['id'], str) and 1 <= len(q['id']) <= 20 and q['id'] not in seen_ids, 'Mã truyện nghề không hợp lệ.', 'invalid_save')
        need(q['career'] in ARCS and q['career'] not in seen_careers, 'Hàng chờ truyện nghề không hợp lệ.', 'invalid_save')
        seen_ids.add(q['id'])
        seen_careers.add(q['career'])
        nxt = len((st['arcs'].get(q['career']) or dict(seen=[]))['seen'])
        beats = ARCS[q['career']]['beats']
        need(nxt < len(beats) and q['beat'] == beats[nxt]['id'], 'Hàng chờ truyện nghề sai thứ tự.', 'invalid_save')
        integer(q['day'], 1, 10**9)
