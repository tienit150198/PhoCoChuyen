"""Chùa Gió Lành: the data for game/careers/pagoda.py.

The pagoda by the river landing (the same Chùa Gió Lành the tour guide's trips stop at: the bronze bell the
village cast together, dented in an old storm; the well behind the hall; the row of areca palms at the
three-entrance gate). The player is a young monk under the abbot, thầy Huệ Minh.

A job (variant) is a short chain of steps, built with the step builders of the homemaker's content
(homemaker_content: pick / sort / order / choose, see its docstring) plus one step of this place:

  tally    count a donation (the bills are on the table) and write the exact amount in the sổ công đức.

A slip is (sev 1..3, why, cat, safety): cat is cr (chu đáo, đúng cách), sf (an toàn), hn (minh bạch,
ngay thẳng), mn (hòa nhã, lắng nghe). Everyday temple life only: no doctrine, no fortune-telling, nobody
is ever asked for money; serious trouble goes to a doctor (115), the police (113) or the child hotline (111).
"""
from __future__ import annotations

from .homemaker_content import C, I, O, S, V, choose, order, pick, sort


def tally(sid, title, who, bills, lead='Đếm trước mặt người gửi, ghi đúng từng xu vào sổ công đức.', when=None, skip=''):
    """Count a donation: `bills` lie on the table, the player writes the total."""
    return dict(type='tally', id=sid, title=title, who=who, bills=list(bills), lead=lead, when=when, skip=skip)


# ================================================================ the people (index = PEOPLE row)
PEOPLE = [
    ('Thầy Huệ Minh', 'Thầy trụ trì chùa Gió Lành', 'Ngoài bảy mươi tuổi, nói chậm, dặn ít mà việc gì cũng thấy.', 'warm'),
    ('Bà Nhạn', 'Phật tử, trưởng ban trai soạn', 'Nấu cơm chay cho chùa hai mươi năm, giọng to, thương người.', 'bossy'),
    ('Cô Hạnh', 'Phật tử, kế toán về hưu', 'Cuối tuần lên chùa cùng đếm hòm công đức, kỹ từng con số.', 'picky'),
    ('Anh Toàn', 'Thợ điện, làm công quả', 'Lo loa đài, đèn đóm mỗi mùa lễ. Ít nói, tay nghề chắc.', 'quiet'),
    ('Bé Na', 'Học sinh lớp 4, theo bà đi chùa', 'Hay hỏi “vì sao”, mê cho cá ăn ở hồ sen.', 'genz'),
    ('Chị Quyên', 'Người hay ngồi ở hiên chùa', 'Chiều nào cũng ghé, ngồi lâu, ít khi nói.', 'quiet'),
    ('Ông Bảy Đò', 'Cụ ông 86 tuổi, chèo đò bến sông ngày trước', 'Rằm nào cũng chống gậy lên chùa, chân yếu mà lòng vui.', 'warm'),
    ('Chị Linh', 'Hướng dẫn viên, dẫn đoàn ghé chùa', 'Dẫn khách tham quan bến sông, lần nào cũng ghé chùa.', 'bossy'),
    ('Anh Phát', 'Chủ tiệm điện thoại dưới phố', 'Mới mở tiệm, tin chuyện ngày đẹp ngày xấu, hay lo.', 'genz'),
]

# The board by the kitchen door (Bảng nội quy & thời khóa): what everyone at the pagoda keeps to.
NOTEBOOK = [
    ('🔔', 'Thời khóa', '4:00 thức chúng, thỉnh chuông · 4:30 công phu sáng · 6:00 điểm tâm, quét sân · 11:00 cúng ngọ, thọ trai · 18:00 công phu chiều.'),
    ('🪔', 'Hương đèn', 'Khách thắp hương ở lư hương lớn ngoài sân. Trong chánh điện chỉ một nén, xa rèm, xa phướn. Đèn cầy phải có chụp kính.'),
    ('👕', 'Trang phục', 'Quần áo kín đáo. Ai mặc quần đùi, áo hai dây thì mượn khăn choàng treo ở cổng; nói nhẹ nhàng, không làm khách ngượng.'),
    ('🤫', 'Giữ yên lặng', 'Chánh điện, nhà tổ, tăng xá: nói nhỏ, không đèn flash, không gọi điện. Khách không vào tăng xá.'),
    ('🥬', 'Bếp chay', 'Không thịt cá, nước mắm cá, mắm tôm, mỡ heo, hạt nêm gà. Bếp chùa không dùng hành, hẹ, tỏi, kiệu, nén.'),
    ('📒', 'Công đức', 'Hai người cùng mở hòm, đếm trước mặt người gửi, ghi đúng từng xu, viết giấy công đức. Không xin tiền ai, không nhận tiền “giải hạn”, “xem số”.'),
    ('🆘', 'Khi có chuyện', 'Người ngất, khó thở, đau ngực: gọi 115. Có người bị đánh, bị đe dọa: 113. Trẻ em bị bạo hành: 111. Ở lại bên họ, đừng để ai một mình.'),
]

# ================================================================ the jobs
YARD = [
    V('y_quet', 'yard', 0, 'Quét sân buổi sáng', '“Con quét sân giúp thầy. Lá bàng rụng nhiều, có người còn để lại vỏ chai.”', [
        order('quet', 'Quét sân chùa', '🧹 Quét xong', [
            O('nhat', '🍾', 'Nhặt vỏ chai, giấy, túi ni-lông'),
            O('quet', '🧹', 'Quét lá từ hiên ra phía cổng'),
            O('hot', '🧺', 'Hốt lá vào sọt'),
            O('tuoi', '💧', 'Tưới hàng cau, chậu kiểng'),
            O('dot', '🔥', 'Gom lá đốt ngay góc sân cho gọn', bad=(2, 'Đốt lá giữa sân chùa: khói bay vào chánh điện, tàn lửa bay gần mái.', 'sf', True)),
        ], [('nhat', 'quet', 1, 'Chưa nhặt rác lớn mà quét: chổi kéo lê vỏ chai, giấy rách tung tóe.', 'cr'),
            ('quet', 'hot', 1, 'Hốt trước khi quét xong: lá còn vương khắp sân.', 'cr')],
            lead='Bấm theo thứ tự sẽ làm. Bấm lại việc cuối để bỏ.', done='Sân sạch lá, hàng cau xanh mướt.'),
        sort('rac', 'Lá và rác đi đâu', '🗑️ Đổ rác', (('u', '🌱', 'Hố ủ phân sau vườn'), ('tai', '♻️', 'Bao đồ tái chế'), ('rac', '🗑️', 'Thùng rác thường')), [
            S('la', '🍂', 'Lá bàng khô', ('u',), 'cả một sọt', why='Lá khô bỏ hố ủ, thành phân cho vườn.'),
            S('hoa', '🥀', 'Hoa cúng đã héo', ('u',), 'thay ra từ bàn Phật', why='Hoa héo cũng ủ thành phân được.'),
            S('chai', '🍾', 'Chai nhựa, lon nước', ('tai',), 'khách để lại', why='Chai lon gom riêng, bán ve chai góp quỹ từ thiện.'),
            S('xop', '🥡', 'Hộp xốp đựng xôi', ('rac',), 'còn dính đồ ăn', why='Hộp xốp dính đồ ăn không tái chế được.'),
        ], lead='Mỗi thứ một chỗ.', done='Lá về hố ủ, chai lon gom riêng.'),
    ], note='Nhặt rác lớn trước, quét từ trong ra ngoài, không đốt lá trong sân.'),
    V('y_sen', 'yard', 4, 'Chăm hồ sen', 'Bé Na kéo áo bạn: “Thầy ơi, hồ sen có lá vàng, cá bơi lờ đờ kìa!”', [
        pick('ho', 'Dọn hồ sen', '🪷 Dọn xong', [
            I('vot', '🍃', 'Vớt lá úa, hoa tàn trên mặt hồ', 'bằng vợt cán dài', True, 'Để lá úa thối dưới hồ, nước đục, cá ngộp.', 1),
            I('nuoc', '💧', 'Thay bớt một phần nước, châm nước giếng', 'nước hồ hơi đục', True, 'Nước đục không thay, cá bơi lờ đờ.', 1),
            I('ca_lang', '🐟', 'Thả thêm cá bảy màu ăn lăng quăng', 'hồ có muỗi', True, 'Hồ có lăng quăng mà không có cá ăn, muỗi sinh sôi.', 1),
            I('ca_tre', '🐠', 'Thả bao cá trê lai người ta gửi “phóng sinh”', 'cá to, háu ăn', False, 'Thả cá trê lai vào hồ: cá ăn hết cá nhỏ, nước đục ngầu.', 2),
            I('thuoc', '🧪', 'Rải thuốc diệt muỗi xuống hồ', 'cho nhanh', False, 'Rải thuốc diệt muỗi xuống hồ: cá chết nổi trắng.', 2, 'sf'),
            I('rua', '🧼', 'Đổ nước rửa bát xuống hồ cho đỡ phí', 'nước có xà phòng', False, 'Nước rửa bát làm váng bọt khắp hồ, sen vàng lá.', 1),
        ], lead='Chọn những việc sẽ làm.', done='Mặt hồ trong, cá đớp mồi lăng xăng.'),
        choose('na', 'Bé Na cho cá ăn', 'Bé Na ôm cả túi bánh mì: “Con cho cá ăn hết nha thầy!” Bé đứng sát mép hồ, nhón chân.', [
            C('it', 'Cho bé đứng lùi khỏi mép, rải một nắm nhỏ; dặn cá ăn no là thôi', 'good', 'Bé Na rải từng chút, đếm được mười hai con cá đỏ.'),
            C('het', 'Để bé rải tùy thích', 'ok', 'Bánh mì nổi lềnh bềnh.', 1, 'Bánh mì thừa thối dưới hồ, chiều nước bốc mùi.'),
            C('quat', 'Quát bé đi chỗ khác chơi', 'bad', 'Bé Na mếu máo chạy đi tìm bà.', 1, 'Quát trẻ con ngay giữa sân chùa.', 'mn')]),
    ], note='Hồ sen là chỗ cả xóm ngồi ngắm: vớt lá úa, giữ nước trong, không thả cá lạ.'),
    V('y_canh', 'yard', 0, 'Tỉa cây cảnh', '“Cây sanh trước nhà tổ mọc chen nhiều cành quá. Con tỉa giúp thầy, nhẹ tay thôi.”', [
        pick('tia', 'Tỉa cây sanh', '✂️ Tỉa xong', [
            I('con', '🧴', 'Lau kéo bằng cồn trước khi cắt', 'kéo dính nhựa cây cũ', True, 'Kéo bẩn cắt cành, vết cắt dễ thối.', 1),
            I('kho', '🌿', 'Cắt cành khô, cành mọc chen vào giữa', 'nhìn từ xa trước rồi mới cắt', True, 'Cành khô còn nguyên, cây rối như tổ chim.', 1),
            I('tui', '🍂', 'Tỉa trụi lá cho gọn gàng', 'nhìn cho sạch mắt', False, 'Tỉa trụi lá: cây sanh trăm tuổi suy cả một mùa.', 2),
            I('sang', '💧', 'Tưới vào gốc lúc sáng sớm', 'trời còn mát', True, 'Quên tưới, lá héo rũ buổi trưa.', 1),
            I('trua', '☀️', 'Tưới đẫm lên lá lúc trưa nắng', 'cho mát cây', False, 'Tưới lên lá giữa trưa: lá cháy đốm.', 1),
            I('phun', '🧪', 'Phun thuốc sâu lúc khách đang lễ trong sân', 'tranh thủ', False, 'Phun thuốc sâu giữa lúc đông người: có cụ ho sặc sụa.', 2, 'sf'),
        ], lead='Chọn những việc sẽ làm.', done='Cây sanh gọn dáng, tán xanh vẫn đủ che hiên.'),
        choose('xin', 'Khách xin chậu lan', 'Một chị khách ngắm chậu lan trước hiên: “Chậu này đẹp quá, cho chị xin đem về nhé, chùa nhiều cây mà.”', [
            C('hoi', 'Cười, nói cây của chùa do Phật tử chăm; mời chị lần sau xin cây con thầy trụ trì hay tách cho khách', 'good', 'Chị khách gật gù, hẹn rằm sau lên xin cây con.'),
            C('cho', 'Cho luôn cho chị vui', 'bad', 'Chị khách ôm chậu lan về.', 1, 'Đem cây của chùa cho người lạ khi chưa hỏi thầy trụ trì.', 'hn'),
            C('gat', '“Không được, đồ của chùa!”', 'ok', 'Chị khách ngượng, đi ra.', 1, 'Từ chối cộc lốc, khách ngượng đỏ mặt.', 'mn')]),
    ], note='Cây trong chùa trồng mấy chục năm: tỉa ít, tưới sớm, đồ của chùa không tự ý cho.'),
]

HALL = [
    V('h_hoa', 'hall', 0, 'Thay hoa, bày trái cây', '“Hoa trên bàn Phật héo rồi con. Phật tử mới gửi hoa với trái cây, con bày giúp thầy.”', [
        pick('hoa', 'Bày bàn Phật', '🪷 Bày xong', [
            I('sen', '🪷', 'Hoa sen, hoa cúc tươi', 'Phật tử mới gửi', True, 'Bàn Phật để hoa héo nguyên.', 1),
            I('nuoc', '💧', 'Thay nước bình hoa, rửa bình', 'nước cũ đã đục', True, 'Bình hoa nước đục, bốc mùi.', 1),
            I('trai', '🍊', 'Trái cây tươi, rửa sạch, lau khô', 'cam, chuối, thanh long', True, 'Mâm trái cây trống trơn.', 1),
            I('dap', '🍌', 'Nải chuối dập nát, rỉ nước', 'để từ hôm kia', False, 'Chuối dập để trên bàn Phật, ruồi bu.', 1),
            I('nhua', '🌸', 'Bình hoa nhựa phủ bụi', 'cắm từ Tết năm ngoái', False, 'Hoa nhựa bám bụi để trên bàn Phật.', 1),
        ], lead='Chọn những thứ sẽ bày.', done='Bàn Phật thơm mùi sen, trái cây tươi mát.'),
        choose('man', 'Mâm cúng mặn', 'Một cô Phật tử lần đầu lên chùa bưng tới đĩa gà luộc: “Thầy đặt lên bàn Phật giúp con, con cúng cho mẹ con.”', [
            C('nhe', 'Cảm ơn cô, nhẹ nhàng nói bàn Phật chỉ cúng hoa quả, đồ chay; mời cô thắp hương, mang đĩa gà về cúng ở nhà', 'good',
              'Cô cảm ơn, nói lần sau sẽ mang hoa sen.'),
            C('hien', 'Đặt tạm ra bàn ngoài hiên cho cô khỏi buồn', 'ok', 'Đĩa gà nằm ngoài hiên cả buổi.', 1, 'Đĩa gà để ngoài hiên chùa, khách khác nhìn lạ.'),
            C('to', 'Nói to: “Chùa ai cúng gà bao giờ!”', 'bad', 'Cô Phật tử đỏ mặt, bưng đĩa gà đi ra.', 2, 'Nói to làm người mới đi chùa xấu hổ.', 'mn')]),
    ], note='Bàn Phật: hoa tươi, trái cây sạch, đồ chay. Ai chưa biết thì chỉ nhẹ nhàng.'),
    V('h_huong', 'hall', 3, 'Hương đèn trong chánh điện', 'Anh Toàn vừa thay bóng đèn: “Thầy xem lại hương đèn giúp em, gió lùa vào chánh điện mạnh lắm.”', [
        sort('cho', 'Đặt đúng chỗ', '🪔 Xếp xong', (('lu', '🏺', 'Lư hương lớn ngoài sân'), ('ban', '🛕', 'Bàn Phật trong chánh điện'), ('cat', '📦', 'Cất đi, không dùng')), [
            S('bo', '🧧', 'Cả bó nhang khách mang tới', ('lu',), 'khách muốn thắp cả bó', why='Thắp cả bó trong chánh điện: khói mù mịt, tàn rơi đầy.',
              wrong={'ban': (2, 'Cắm cả bó nhang trên bàn Phật: khói mịt mù, tàn rơi xuống khăn trải.', 'sf', True)}),
            S('mot', '🪔', 'Một nén nhang thầy thắp buổi sáng', ('ban',), 'thắp ở lư nhỏ trên bàn Phật', why='Một nén nhang buổi sáng thắp ở bàn Phật.'),
            S('vong', '🌀', 'Nhang vòng to treo trần', ('lu',), 'cháy cả tuần', why='Nhang vòng treo ngoài hiên, gần lư hương lớn.',
              wrong={'ban': (2, 'Nhang vòng treo ngay dưới rèm, tàn rơi xuống vải.', 'sf', True)}),
            S('chup', '🕯️', 'Đèn cầy trong chụp kính', ('ban',), 'chụp kính cao', why='Đèn cầy có chụp kính để trên bàn Phật được.'),
            S('tran', '🕯️', 'Đèn cầy cắm trần, không chụp', ('cat',), 'gió thổi là nghiêng', why='Đèn cầy không chụp: gió thổi là lửa bén rèm.',
              wrong={'ban': (3, 'Đèn cầy trần trong chánh điện lộng gió, lửa liếm sát rèm.', 'sf', True)}),
            S('xit', '🧴', 'Bình xịt muỗi', ('cat',), 'ai để quên', why='Bình xịt là đồ dễ cháy, để xa lửa.',
              wrong={'ban': (3, 'Bình xịt muỗi để sát đèn cầy: nóng lên là nổ.', 'sf', True)}),
        ], lead='Mỗi thứ một chỗ. Nhớ: rèm, phướn là vải, gió lùa mạnh.', done='Hương đèn đúng chỗ, xa rèm, xa phướn.'),
        choose('rem', 'Rèm bay sát đèn', 'Một cơn gió lùa qua cửa hông, tấm rèm vàng bay phần phật sát chân đèn cầy.', [
            C('buoc', 'Buộc gọn rèm, dời đèn ra xa, xem lại bình chữa cháy ở góc điện', 'good', 'Rèm buộc gọn, bình chữa cháy còn hạn. Anh Toàn gật đầu.'),
            C('tat', 'Thổi tắt đèn cầy cho chắc', 'ok', 'Chánh điện tối hơn một chút, nhưng an toàn.'),
            C('ke', 'Để đó, lát gió sẽ dừng', 'bad', 'Mép rèm sém đen một vệt.', 3, 'Rèm bay sát lửa mà để đó: suýt cháy chánh điện.', 'sf', True)]),
    ], note='Nhang cả bó thắp ngoài sân. Trong điện chỉ một nén, đèn có chụp, xa rèm.'),
    V('h_lau', 'hall', 0, 'Lau bàn thờ, tượng Phật', '“Mai rằm rồi. Con lau bàn thờ, lau tượng giúp thầy. Tượng gỗ sơn son, lau nhẹ tay.”', [
        order('lau', 'Lau bàn thờ', '🧽 Lau xong', [
            O('xa', '🙏', 'Chắp tay xá trước khi lau'),
            O('doi', '🪔', 'Dời đèn cầy, lư nhỏ sang bàn bên'),
            O('kho', '🪶', 'Phủi bụi từ trên xuống bằng chổi lông, khăn khô'),
            O('am', '🧽', 'Lau lại bằng khăn ẩm vắt thật kiệt'),
            O('bay', '🌸', 'Bày lại hoa, đèn như cũ'),
            O('tay', '🧴', 'Xịt nước tẩy rửa lên tượng cho sáng', bad=(2, 'Nước tẩy làm bong lớp sơn son thếp vàng trên tượng.', 'cr')),
            O('treo', '🪜', 'Đứng lên bàn thờ cho với tới', bad=(2, 'Trèo lên bàn thờ: vừa thất lễ vừa dễ ngã.', 'sf', True)),
        ], [('xa', 'doi', 1, 'Lau bàn thờ mà quên xá trước.', 'mn'),
            ('doi', 'kho', 1, 'Lau mà đèn cầy còn cháy ngay bên cạnh.', 'sf'),
            ('kho', 'am', 1, 'Lau ướt trước khi phủi bụi: bụi thành vệt bùn.', 'cr'),
            ('am', 'bay', 1, 'Bày lại khi mặt bàn còn ướt.', 'cr')],
            lead='Bấm theo thứ tự sẽ làm. Bấm lại việc cuối để bỏ.', done='Bàn thờ sạch bóng, tượng không trầy một vết.'),
    ], note='Bàn thờ, tượng sơn son: lau khô trước, khăn ẩm sau, không hóa chất, không trèo lên bàn.'),
]

GUIDE = [
    V('g_cong', 'guide', 7, 'Đoàn khách ở cổng tam quan', 'Chị Linh dẫn đoàn tới cổng: “Thầy ơi, đoàn em mười người, nhờ thầy chỉ giúp đi đâu, thắp hương ở đâu.”', [
        choose('ao', 'Trang phục ở cổng', 'Anh Nam trong đoàn mặc quần đùi, áo ba lỗ, đang bước qua cổng tam quan. Người trong đoàn nhìn nhau.', [
            C('khan', 'Chào anh, mời mượn khăn choàng treo ở cổng, nói nhẹ nhàng lý do', 'good', 'Anh Nam quấn khăn, cười: “Vậy mà tôi không biết.”'),
            C('cho', 'Để anh đứng ngoài chờ đoàn', 'ok', 'Anh Nam đứng ngoài cổng một mình.', 1, 'Khách đứng chờ một mình ngoài cổng, cả đoàn ái ngại.', 'mn'),
            C('chan', 'Chặn lại, nói to “Ăn mặc thế này không được vào”', 'bad', 'Anh Nam đỏ mặt, cả đoàn im lặng.', 2, 'Nói to làm khách ngượng ngay ở cổng chùa.', 'mn')]),
        sort('dan', 'Chỉ dẫn cho khách', '🧭 Chỉ dẫn xong', (('duoc', '✅', 'Được, chỉ chỗ'), ('nhe', '🤫', 'Được, nhắc nhẹ cách làm'), ('khong', '🙏', 'Xin khách đừng làm')), [
            S('huong', '🏺', 'Thắp hương ở lư lớn ngoài sân', ('duoc',), 'mỗi người một nén', why='Lư lớn ngoài sân là chỗ thắp hương cho khách.'),
            S('anh', '📷', 'Chụp ảnh cổng tam quan, hàng cau', ('duoc',), 'ngoài sân', why='Chụp ảnh ngoài sân thì thoải mái.'),
            S('le', '🛕', 'Vào chánh điện lễ Phật', ('nhe',), 'cả đoàn', why='Vào chánh điện: bỏ dép, nói nhỏ, không đèn flash.'),
            S('tien', '🪙', 'Đặt tiền lẻ lên tay tượng', ('nhe',), 'thấy người khác làm', why='Nhắc nhẹ khách đừng đặt tiền lên tượng; nếu muốn gửi thì có hòm công đức.'),
            S('tang', '🚪', 'Vào tăng xá xem chỗ các thầy ở', ('khong',), 'tò mò', why='Tăng xá là chỗ ở, khách không vào.'),
            S('sen', '🪷', 'Hái hoa sen trong hồ mang về', ('khong',), 'hoa đẹp quá', why='Hoa sen để cả xóm ngắm, không hái.'),
            S('bo', '🧧', 'Cắm cả bó nhang lên bàn Phật', ('khong',), 'cho thành tâm', why='Cả bó nhang trên bàn Phật: khói mù, dễ cháy.',
              wrong={'duoc': (2, 'Để khách cắm cả bó nhang trên bàn Phật, khói mù mịt.', 'sf', True)}),
        ], lead='Khách hỏi gì, bạn trả lời sao?', done='Cả đoàn đi lễ nhẹ nhàng, đúng chỗ.'),
        choose('chuong', 'Khách hỏi chuyện quả chuông', 'Tom, vị khách nước ngoài, chỉ quả chuông lớn: “Why is there a dent?” Chị Linh nhờ bạn kể.', [
            C('ke', 'Kể chuông do dân làng góp đồng đúc, vết lõm từ trận bão năm xưa nên tiếng trầm hơn', 'good', 'Tom gật gù, ghi vào sổ tay. Cả đoàn chụp ảnh quả chuông.'),
            C('hoi', 'Nhờ chị Linh kể giúp', 'ok', 'Chị Linh kể thay, đoàn nghe chăm chú.'),
            C('bia', 'Bịa rằng chuông linh lắm, gõ một tiếng là trúng số', 'bad', 'Mấy người trong đoàn đòi gõ chuông.', 2,
              'Bịa chuyện chuông linh, xui người ta mê tín.', 'hn')]),
    ], note='Khách ở cổng: trang phục, chỗ thắp hương, chỗ cần yên lặng. Nói nhẹ nhàng, không làm ai ngượng.', mods=(None, 'tour'), weight=2),
    V('g_han', 'guide', 8, 'Khách nhờ “giải hạn”', 'Anh Phát dúi vào tay bạn một phong bì: “Thầy xem giúp em năm nay sao xấu, giải hạn hết bao nhiêu em cũng chịu. Em mới mở tiệm.”', [
        choose('han', 'Trả lời anh Phát', 'Anh Phát lo lắng thật, tay còn cầm tờ lịch ghi “ngày xấu”.', [
            C('that', 'Nhẹ nhàng nói chùa không xem số, không thu tiền, không hứa giải được hạn; mời anh ngồi uống trà, nghe anh lo chuyện gì', 'good',
              'Anh Phát kể chuyện vay tiền mở tiệm. Nói ra rồi, anh thở phào.'),
            C('thay', 'Hẹn anh hỏi thầy trụ trì rồi trả lời', 'ok', 'Anh Phát ngồi chờ. Thầy Huệ Minh ra, nói chuyện với anh rất lâu.'),
            C('nhan', 'Nhận phong bì, hứa đọc vài câu là giải được hạn', 'bad', 'Anh Phát về, tin rằng đã “giải” xong.', 3,
              'Thu tiền, hứa giải được hạn cho người đang lo sợ.', 'hn'),
            C('che', 'Cười, bảo anh mê tín quá', 'bad', 'Anh Phát cúi mặt, đứng dậy đi về.', 1, 'Chê người đang lo là mê tín.', 'mn')]),
        choose('phong_bi', 'Phong bì trên bàn', 'Lúc về, anh Phát vẫn để lại phong bì: “Em gửi chùa, thầy cầm giúp em.”', [
            C('hom', 'Mời anh tự bỏ vào hòm công đức nếu anh muốn, rồi ghi sổ, viết giấy cho anh; không ai bắt', 'good',
              'Anh Phát bỏ vào hòm, cầm tờ giấy công đức ghi đúng tên, đúng số.'),
            C('tra', 'Trả lại anh, nói chùa không cần', 'ok', 'Anh Phát cất phong bì, hơi ngại.'),
            C('tui', 'Cầm phong bì, cất vào túi áo', 'bad', 'Phong bì nằm trong túi áo bạn.', 3, 'Tiền gửi chùa cầm tay, không vào hòm, không vào sổ.', 'hn')],
            when=['han', ['that', 'thay', 'che']], skip='Phong bì đã nằm trong túi áo bạn.'),
    ], note='Chùa không xem số, không thu tiền, không hứa giải được hạn cho ai. Tiền công đức chỉ vào hòm và vào sổ.', min_day=2),
]

KITCHEN = [
    V('k_trua', 'kitchen', 1, 'Nấu cơm trưa chay cùng bà Nhạn', 'Bà Nhạn xắn tay áo: “Trưa nay hai mươi người ăn. Có người gửi đồ vào bếp mà lẫn đồ mặn, thầy xem giúp bà.”', [
        sort('thay', 'Đồ trong bếp', '🥬 Vào bếp', (('dung', '✅', 'Dùng được'), ('thay', '🔄', 'Thay bằng đồ chay'), ('rieng', '🚫', 'Để riêng, gửi trả')), [
            S('dau', '🧈', 'Đậu hũ non', ('dung',), 'mới mua sáng nay', why='Đậu hũ là món chính của bếp chay.'),
            S('nam', '🍄', 'Nấm rơm, nấm đông cô', ('dung',), 'Phật tử gửi', why='Nấm dùng được.'),
            S('mam', '🐟', 'Nước mắm cá', ('thay', 'rieng'), 'chai mới', why='Nước mắm cá: thay bằng nước tương hoặc nước mắm chay.',
              wrong={'dung': (3, 'Nêm nước mắm cá vào món chay: người ăn chay trường ăn phải mà không biết.', 'hn', False)}),
            S('nem', '🧂', 'Hạt nêm gà', ('thay', 'rieng'), 'gói to', why='Hạt nêm gà làm từ gà: thay bằng hạt nêm nấm.',
              wrong={'dung': (3, 'Nêm hạt nêm gà vào món chay: không còn là đồ chay.', 'hn', False)}),
            S('mo', '🥓', 'Hũ mỡ heo', ('thay', 'rieng'), 'để xào cho thơm', why='Mỡ heo: thay bằng dầu ăn.',
              wrong={'dung': (3, 'Xào rau bằng mỡ heo trong bếp chùa.', 'hn', False)}),
            S('toi', '🧄', 'Tỏi, hành phi', ('rieng',), 'để phi thơm', why='Bếp chùa không dùng hành tỏi.',
              wrong={'dung': (1, 'Bếp chùa không dùng hành tỏi, bà Nhạn nhắc ngay.', 'cr', False),
                     'thay': (1, 'Hành tỏi không cần thay gì, cứ để riêng.', 'cr', False)}),
        ], lead='Đọc kỹ từng thứ. Có thứ có đồ chay thay được, có thứ để riêng.', done='Bếp toàn đồ chay, nêm bằng nước tương, hạt nêm nấm.'),
        choose('nem', 'Nêm nồi canh', 'Nồi canh nấm đậu hũ nhạt. Bà Nhạn đang bận chiên chả, bảo bạn nêm.', [
            C('dung', 'Nêm muối, chút đường phèn, nước tương; múc ra chén riêng để nếm', 'good', 'Canh ngọt thanh. Bà Nhạn nếm, gật đầu.'),
            C('nhat', 'Để nhạt vậy, ai ăn mặn tự thêm', 'ok', 'Canh nhạt thếch.', 1, 'Nồi canh nhạt thếch, cả bàn phải xin thêm muối.'),
            C('len', 'Lén thêm chút nước mắm cá cho đậm', 'bad', 'Canh đậm hơn, nhưng không còn chay.', 3,
              'Lén nêm nước mắm cá vào nồi chay: người ta tin bếp chùa mà ăn phải.', 'hn')]),
        sort('phan', 'Chia phần cơm', '🍱 Dọn cơm', (('thuong', '🍚', 'Phần thường'), ('mem', '🥣', 'Cháo, rau mềm'), ('rieng', '🚫', 'Phần riêng, không đậu phộng')), [
            S('bay', '👴', 'Ông Bảy Đò', ('mem',), '86 tuổi, răng yếu', why='Ông Bảy răng yếu, ăn cháo, rau mềm cho dễ.', sev=1, cat='sf'),
            S('lan', '👩', 'Cô Lan, Phật tử mới', ('rieng',), 'dị ứng đậu phộng', why='Muối mè đậu phộng: cô Lan dị ứng.',
              wrong={b: (3, 'Cô Lan dị ứng đậu phộng mà phần cơm có muối mè đậu phộng.', 'sf', True) for b in ('thuong', 'mem')}),
            S('toan', '👷', 'Anh Toàn', ('thuong',), 'làm công quả cả sáng', why='Anh Toàn ăn phần thường.'),
            S('na', '👧', 'Bé Na', ('thuong', 'mem'), 'lớp 4', why='Bé Na ăn phần thường.'),
        ], lead='Mỗi người một phần hợp với mình.', done='Ai cũng có phần hợp với mình, không ai ăn phải thứ kiêng.'),
    ], note='Bếp chay: thứ gì từ thịt cá thì thay hoặc để riêng. Nhớ người dị ứng, người răng yếu.'),
    V('k_ram', 'kitchen', 1, 'Phát cơm chay ngày rằm', 'Bà Nhạn khệ nệ bê nồi cơm: “Rằm nào chùa cũng phát cơm cho cô chú bán vé số, chạy xe ôm. Thầy phát giúp bà.”', [
        order('phat', 'Phát cơm', '🍱 Phát xong', [
            O('tay', '🧼', 'Rửa tay, đeo khẩu trang'),
            O('hang', '🧍', 'Mời mọi người xếp hàng, cụ già và trẻ nhỏ lên trước'),
            O('suat', '🍱', 'Phát từng suất, hai tay đưa'),
            O('nuoc', '🥤', 'Mời thêm ly nước, chỉ chỗ ngồi trong bóng mát'),
            O('chup', '📸', 'Chụp ảnh từng người nhận cơm đăng lên mạng', bad=(1, 'Chụp ảnh người nhận cơm đăng mạng, có cô kéo nón che mặt.', 'mn')),
        ], [('tay', 'suat', 1, 'Phát cơm khi chưa rửa tay.', 'sf'), ('hang', 'suat', 1, 'Chưa xếp hàng đã phát: chen lấn, cụ già bị xô.', 'sf')],
            lead='Bấm theo thứ tự sẽ làm.', done='Ai cũng có suất cơm nóng, không ai phải chen.'),
        choose('nhieu', 'Một người lấy nhiều suất', 'Một cô ôm năm hộp cơm định đi. Phía sau còn hơn chục người chờ.', [
            C('hoi', 'Hỏi nhẹ: nhà cô mấy người, phía sau còn nhiều người chờ; chia đủ phần cho nhà cô', 'good',
              'Cô nói nhà có ba đứa nhỏ, lấy ba suất, cảm ơn rối rít.'),
            C('ke', 'Kệ, ai lấy bao nhiêu thì lấy', 'ok', 'Cuối hàng có người không còn suất.', 1, 'Cuối hàng hai cụ không còn cơm.', 'cr'),
            C('duoi', 'Giật lại hộp cơm, đuổi cô đi', 'bad', 'Cô bỏ đi, mắt đỏ hoe.', 2, 'Giật hộp cơm, đuổi người ta trước mặt mọi người.', 'mn')]),
        choose('du', 'Cơm dư cuối buổi', 'Phát xong còn dư mười hộp cơm.', [
            C('cho', 'Mang ra cổng mời mấy cô chú xe ôm, bán vé số còn ở đó', 'good', 'Mười hộp cơm hết trong năm phút.'),
            C('tu', 'Cất tủ lạnh, mai hâm lại cho cả chùa ăn', 'ok', 'Mai cả chùa ăn cơm hâm.'),
            C('bo', 'Đổ bỏ cho gọn bếp', 'bad', 'Mười hộp cơm vào thùng rác.', 1, 'Đổ bỏ cơm còn ngon trong khi ngoài cổng còn người đói.', 'cr')]),
    ], note='Phát cơm: sạch tay, xếp hàng, người già trẻ nhỏ trước, không ai bị bỏ sót.', mods=('ram',), min_day=2, weight=2),
]

BOOK = [
    V('b_hom', 'book', 2, 'Mở hòm công đức', 'Cô Hạnh đeo kính, mở cuốn sổ bìa đỏ: “Cuối tuần rồi, mình mở hòm công đức thầy nhé.”', [
        choose('mo', 'Ai mở hòm', 'Chìa khóa hòm công đức thầy trụ trì giao cho bạn.', [
            C('hai', 'Mời cô Hạnh cùng mở, cùng đếm, hai người ký sổ', 'good', 'Cô Hạnh gật đầu: “Hai người cùng làm thì ai nhìn vào cũng yên tâm.”'),
            C('mot', 'Đếm một mình cho nhanh, chụp ảnh gửi thầy', 'ok', 'Đếm xong một mình.', 1, 'Mở hòm một mình, lỡ lệch không ai làm chứng.', 'hn'),
            C('tron', 'Đếm một mình, làm tròn số cho gọn sổ', 'bad', 'Sổ ghi số tròn.', 2, 'Làm tròn tiền công đức: sổ không còn đúng từng xu.', 'hn')]),
        tally('dem', 'Đếm tiền trong hòm', 'Hòm công đức tuần này', (50, 20, 20, 10, 10, 5, 5, 2, 2, 1, 1, 1)),
        choose('roi', 'Tờ tiền dưới gầm bàn', 'Ghi sổ xong, quét gầm bàn thấy một tờ 10 xu rơi ra lúc đổ hòm.', [
            C('ghi', 'Báo cô Hạnh, ghi thêm một dòng vào sổ, bỏ chung vào quỹ', 'good', 'Cô Hạnh ghi thêm: “+10 xu, nhặt dưới gầm bàn.” Sổ khớp.'),
            C('tuan', 'Bỏ lại vào hòm, tuần sau tính', 'ok', 'Tờ tiền nằm lại trong hòm.', 1, 'Tiền tuần này dồn sang tuần sau, sổ lệch hai tuần.', 'cr'),
            C('tui', 'Cất vào túi, sổ ghi xong rồi', 'bad', 'Tờ tiền nằm trong túi áo bạn.', 3, 'Lấy tiền công đức bỏ túi.', 'hn')]),
    ], note='Hai người cùng mở hòm, đếm từng tờ, ghi đúng từng xu.'),
    V('b_giay', 'book', 8, 'Viết giấy công đức', 'Anh Phát quay lại chùa: “Em gửi chùa ít tiền sửa mái tây. Thầy viết giấy giúp em.”', [
        tally('dem', 'Đếm tiền anh Phát gửi', 'Anh Phát', (20, 20, 5, 2, 2, 1), lead='Đếm trước mặt anh Phát, rồi ghi đúng số vào sổ.'),
        choose('ghi', 'Anh Phát nhờ ghi', 'Anh Phát nói nhỏ: “Thầy ghi giấy giúp em năm trăm xu nhé, em chụp đăng lên mạng cho tiệm có tiếng.”', [
            C('dung', 'Ghi đúng số anh gửi, tên anh, ngày; nói nhẹ: giấy công đức ghi đúng số đã gửi', 'good',
              'Anh Phát gãi đầu: “Thầy nói phải.” Anh cầm giấy, cảm ơn.'),
            C('im', 'Ghi đúng số, không nói gì thêm', 'ok', 'Anh Phát cầm giấy, hơi tiu nghỉu.'),
            C('khong', 'Ghi năm trăm xu cho anh vui', 'bad', 'Tờ giấy ghi năm trăm xu.', 3, 'Giấy công đức ghi khống gấp mười: sổ chùa không khớp, người ta mang đi khoe.', 'hn')]),
        choose('an', 'Bà cụ gửi ẩn danh', 'Một bà cụ lặng lẽ đặt 5 xu lên bàn: “Đừng ghi tên bà, ít lắm, thầy ạ.”', [
            C('an', 'Ghi “Phật tử ẩn danh”, đủ 5 xu, cảm ơn bà', 'good', 'Bà cụ cười móm mém, chắp tay rồi đi.'),
            C('bo', 'Ít quá, khỏi ghi vào sổ', 'bad', 'Năm xu không có trong sổ.', 2, 'Không ghi khoản công đức nhỏ: sổ không còn đúng.', 'hn'),
            C('ten', 'Hỏi tên bà cho bằng được để ghi', 'ok', 'Bà cụ ngại ngần nói tên.', 1, 'Người ta xin ẩn danh mà cứ hỏi tên.', 'mn')]),
    ], note='Giấy công đức ghi đúng tên, đúng số. Ai xin ẩn danh thì ghi ẩn danh, đủ số.', min_day=2),
]

LISTEN = [
    V('l_hien', 'listen', 5, 'Người ngồi một mình ở hiên', 'Chị Quyên ngồi ở hiên từ trưa, mắt đỏ hoe. Thấy bạn đi qua, chị cúi mặt.', [
        choose('mo', 'Lại gần', 'Chị Quyên ngồi bó gối, nhìn ra hồ sen.', [
            C('tra', 'Ngồi xuống cách một khoảng, mời chén trà, hỏi nhỏ chị có muốn kể không; không thì cứ ngồi đây', 'good',
              'Chị Quyên nhận chén trà. Một lúc lâu, chị bắt đầu kể.'),
            C('hoi', 'Hỏi ngay: “Chị bị sao vậy?”', 'ok', 'Chị Quyên lắc đầu, rồi cũng kể.', 1, 'Hỏi dồn, chị Quyên co người lại.', 'mn'),
            C('dong', 'Nhắc chị chùa sắp đóng cổng', 'bad', 'Chị Quyên đứng dậy đi về.', 2, 'Người đang buồn ngồi nhờ hiên chùa mà bị nhắc về.', 'mn')]),
        choose('nghe', 'Lắng nghe', 'Chị kể mẹ mất tháng trước, chị đi làm xa không về kịp.', [
            C('nghe', 'Lắng nghe, không ngắt lời; nói: “Chị thương mẹ lắm. Chị muốn thắp cho mẹ một nén hương không?”', 'good',
              'Chị Quyên thắp hương cho mẹ, đứng lặng một lúc. Mặt chị dịu lại.'),
            C('dung', 'Khuyên: “Thôi chị đừng buồn nữa”', 'ok', 'Chị Quyên gật đầu cho qua.', 1, 'Bảo người ta đừng buồn khi họ chưa kể xong.', 'mn'),
            C('ke', 'Kể chuyện nhà mình còn khổ hơn', 'bad', 'Chị Quyên im lặng nghe bạn kể.', 1, 'Lấy chuyện mình chen vào nỗi buồn của người khác.', 'mn')]),
        choose('hen', 'Lúc chị về', 'Trời xế chiều, chị Quyên đứng dậy.', [
            C('hen', 'Nói chùa lúc nào cũng mở cửa, chiều mai chị cứ ghé uống trà', 'good', 'Chị Quyên cười nhẹ: “Mai chị ghé.”'),
            C('chao', 'Chào chị về cẩn thận', 'ok', 'Chị Quyên chào rồi về.')]),
    ], note='Người buồn cần được nghe trước. Không giảng, không vội khuyên.'),
    V('l_nang', 'listen', 5, 'Khi nỗi buồn quá sức', 'Chị Quyên ngồi ở góc vườn sau, tay run: “Dạo này chị không ngủ được. Có lúc chị nghĩ hay đi theo mẹ cho xong.”', [
        choose('o', 'Ở bên chị', 'Chị Quyên nói rất nhỏ, mắt nhìn xuống đất.', [
            C('o', 'Ngồi xuống bên chị, nói “Có em ở đây”, hỏi thẳng mà nhẹ: chị có đang định làm gì hại mình không', 'good',
              'Chị Quyên khóc òa. Chị nói chưa định làm gì, chỉ thấy mệt quá.'),
            C('gat', 'Bảo chị đừng nói bậy, đi rửa mặt cho tỉnh', 'bad', 'Chị Quyên im bặt.', 2, 'Gạt đi lời của người đang nghĩ quẩn: lần sau họ không nói nữa.', 'sf'),
            C('ban', 'Hẹn mai nói chuyện, giờ đang bận', 'bad', 'Chị Quyên ngồi lại một mình.', 3, 'Để người vừa nói muốn chết ngồi một mình.', 'sf', True)]),
        choose('giup', 'Tìm người giúp', 'Chị Quyên xin bạn đừng nói với ai.', [
            C('bacsi', 'Nói em thương chị nên không giữ kín chuyện này; gọi em gái chị tới, cùng chị đi khám bác sĩ; nguy cấp thì gọi 115', 'good',
              'Em gái chị Quyên tới. Hai chị em hẹn bác sĩ ngay chiều nay.'),
            C('mai', 'Khuyên chị mai đi khám', 'ok', 'Chị Quyên gật đầu rồi về một mình.', 1, 'Hẹn mai: đêm nay chị vẫn một mình.', 'sf'),
            C('giu', 'Giữ kín cho chị như chị xin', 'bad', 'Không ai biết chuyện.', 3, 'Giữ kín chuyện chị muốn chết: không ai kịp giúp.', 'sf', True)]),
        choose('sau', 'Mấy hôm sau', 'Chị Quyên quay lại chùa, trông đã ngủ được hơn.', [
            C('hoi', 'Hỏi thăm chị, mời chị ở lại ăn cơm chay với mọi người', 'good', 'Chị Quyên ăn hết bát cơm, còn phụ bà Nhạn rửa chén.'),
            C('thoi', 'Chào chị, không nhắc chuyện cũ', 'ok', 'Chị Quyên ngồi một lúc rồi về.')]),
    ], note='Ai nói muốn chết: ở lại bên họ, không giữ bí mật, gọi người thân, đưa tới bác sĩ; nguy cấp gọi 115.', min_day=4, weight=1),
]

CEREMONY = [
    V('c_cau_an', 'ceremony', 3, 'Chuẩn bị lễ cầu an tối rằm', 'Anh Toàn vác cuộn dây điện: “Tối nay cầu an, chừng trăm người. Thầy xem giúp em xếp chỗ, đèn đóm.”', [
        order('xep', 'Xếp chánh điện', '🛕 Xếp xong', [
            O('lau', '🧹', 'Quét, lau chánh điện'),
            O('chieu', '🟫', 'Trải chiếu, kê ghế cho người già ở hàng đầu'),
            O('loi', '🚶', 'Chừa lối đi giữa và lối ra cửa hông'),
            O('loa', '🔊', 'Thử loa vừa đủ nghe trong sân'),
            O('chan', '🚧', 'Khóa cửa hông cho khỏi ồn', bad=(3, 'Khóa cửa hông khi trăm người trong điện: có chuyện là không lối thoát.', 'sf', True)),
        ], [('lau', 'chieu', 1, 'Trải chiếu khi sàn chưa lau.', 'cr'), ('chieu', 'loi', 1, 'Trải chiếu kín sàn, quên chừa lối đi.', 'sf')],
            lead='Bấm theo thứ tự sẽ làm.', done='Chánh điện sạch, có lối đi, cụ già có ghế ngồi.'),
        sort('den', 'Đèn nào treo đâu', '🏮 Treo đèn', (('san', '🏮', 'Treo ngoài sân'), ('dien', '🛕', 'Trong chánh điện'), ('khong', '🚫', 'Không dùng')), [
            S('vai', '🏮', 'Đèn lồng vải, bóng LED', ('san',), 'cả chục chiếc', why='Đèn lồng LED treo ngoài sân là đẹp và an toàn.'),
            S('giay', '🏮', 'Đèn lồng giấy thắp nến', ('khong',), 'kiểu xưa', why='Đèn giấy thắp nến giữa trăm người: dễ bén lửa.',
              wrong={b: (2, 'Đèn lồng giấy thắp nến treo giữa đám đông, gió thổi là cháy.', 'sf', True) for b in ('san', 'dien')}),
            S('sen', '🪷', 'Đèn hoa sen điện', ('dien',), 'để trên bàn Phật', why='Đèn hoa sen điện để trong chánh điện.'),
            S('day', '🔌', 'Dây đèn nháy nối dây điện trần', ('khong',), 'quấn băng keo', why='Dây điện trần nối tạm: dễ chập, giật người.',
              wrong={b: (3, 'Dây điện trần nối tạm, trời sương xuống là chập.', 'sf', True) for b in ('san', 'dien')}),
            S('troi', '🎈', 'Đèn trời', ('khong',), 'ai đó mang tới', why='Đèn trời bay qua mái ngói, dây điện: dễ cháy.',
              wrong={b: (3, 'Thả đèn trời: lửa bay qua mái ngói, rơi xuống mái nhà dân.', 'sf', True) for b in ('san', 'dien')}),
        ], lead='Mỗi chiếc đèn một chỗ, hoặc không dùng.', done='Sân sáng đèn lồng, không ngọn lửa trần nào.'),
        choose('loa', 'Loa sau giờ lễ', 'Lễ xong, có người muốn mở loa thật to bài niệm Phật tới khuya cho cả xóm cùng nghe.', [
            C('vua', 'Giữ loa vừa đủ trong sân, tắt trước chín giờ rưỡi cho xóm nghỉ', 'good', 'Mười giờ, xóm yên tĩnh. Bà cụ nhà bên nhắn cảm ơn.'),
            C('to', 'Mở hết cỡ tới khuya', 'bad', 'Loa vang tới nửa đêm.', 2, 'Loa chùa vang tới nửa đêm, nhà bên có người ốm, trẻ nhỏ không ngủ được.', 'mn')]),
    ], note='Lễ đông người: lối đi, cửa thoát, không lửa trần, loa vừa đủ.', mods=('ram',), weight=2),
]

CARE = [
    V('a_bac', 'care', 6, 'Đỡ ông Bảy lên chùa', 'Ông Bảy Đò chống gậy dưới chân bậc thềm, mười hai bậc đá rêu: “Thầy ơi, đỡ ông một tay.”', [
        choose('bac', 'Lên bậc thềm', 'Bậc đá còn ướt sương, có chỗ đóng rêu.', [
            C('vin', 'Đi phía ngoài, để ông vịn lan can, bước từng bậc, nghỉ ở chiếu nghỉ', 'good', 'Ông Bảy lên tới sân, cười khà: “Thầy đi chậm như ông, giỏi!”'),
            C('tu', 'Bảo ông cứ từ từ tự đi', 'ok', 'Ông Bảy đi một mình, trượt chân một bậc.', 1, 'Để cụ 86 tuổi tự leo bậc đá rêu.', 'sf'),
            C('xoc', 'Xốc nách kéo ông lên cho nhanh', 'bad', 'Ông Bảy đau vai, thở dốc.', 2, 'Kéo xốc nách người già: đau vai, dễ ngã.', 'sf')]),
        choose('rong', 'Rêu trên bậc', 'Đỡ ông lên xong, bạn nhìn lại mấy bậc đá rêu xanh.', [
            C('co', 'Lấy bàn chải cọ rêu, rắc chút cát, đặt biển “bậc trơn”', 'good', 'Chiều đó không ai trượt chân.'),
            C('mai', 'Để mai rảnh rồi cọ', 'ok', 'Chiều có người trượt chân.', 1, 'Biết bậc đá trơn mà để đó.', 'sf')]),
    ], note='Người già lên chùa: đi chậm cùng họ, cho vịn tay, dọn chỗ trơn.'),
    V('a_lac', 'care', 4, 'Bé lạc bà giữa đêm rằm', 'Giữa sân đông nghịt, bé Na đứng khóc: “Con không thấy bà đâu hết!”', [
        choose('giu', 'Giữ bé an toàn', 'Sân chùa đông người, cổng mở ra bến sông.', [
            C('o', 'Dắt bé tới chỗ sáng cạnh cổng chính, ở cùng bé, nhờ anh Toàn đọc tên bà bé qua loa', 'good', 'Năm phút sau bà bé Na hớt hải chạy tới.'),
            C('gui', 'Gửi bé cho một cô đứng gần trông giúp', 'bad', 'Bé Na đứng với người lạ.', 2, 'Giao trẻ lạc cho người lạ trông.', 'sf'),
            C('tu', 'Bảo bé ra cổng tự tìm bà', 'bad', 'Bé Na đi ra phía bến sông.', 3, 'Để trẻ lạc tự đi tìm giữa đêm, cổng mở ra bến sông.', 'sf', True)]),
        choose('nhan', 'Người tới nhận bé', 'Một người đàn ông tới: “Bé đó cháu tôi, đưa đây.” Bé Na lắc đầu, nép vào bạn.', [
            C('cho', 'Nhẹ nhàng nói chờ bà bé tới; mời anh đứng chờ cùng ở cổng', 'good', 'Người đàn ông lảng đi. Bà bé Na tới, ôm chầm lấy cháu.'),
            C('giao', 'Giao bé cho anh ta cho nhanh', 'bad', 'Bé Na khóc thét.', 3, 'Giao trẻ cho người lạ khi bé không nhận.', 'sf', True)]),
    ], note='Trẻ lạc: ở cùng bé chỗ sáng, đọc loa tìm người nhà, chỉ giao cho người bé nhận ra.', mods=('ram',), min_day=2, weight=2),
    V('a_met', 'care', 6, 'Ông Bảy mệt giữa giờ lễ', 'Đang lễ, ông Bảy Đò ôm ngực, mặt tái, thở dốc.', [
        choose('cuu', 'Ông Bảy mệt', 'Ông thều thào: “Ông tức ngực quá thầy ơi.”', [
            C('goi', 'Đỡ ông ngồi chỗ thoáng, hỏi thuốc ông mang theo, gọi 115, báo con cháu ông', 'good', 'Xe cấp cứu tới sau mười phút. Bác sĩ nói gọi sớm là may.'),
            C('dau', 'Xoa dầu gió, bảo ông nằm nghỉ là hết', 'bad', 'Ông Bảy càng thở dốc.', 3, 'Người già đau ngực mà chỉ xoa dầu gió.', 'sf', True),
            C('nha', 'Gọi con cháu ông tới đón', 'ok', 'Nửa tiếng sau con trai ông mới tới.', 2, 'Đau ngực mà chờ người nhà nửa tiếng.', 'sf')]),
    ], note='Đau ngực, khó thở: gọi 115 trước, báo người nhà sau.', min_day=3),
]

INCIDENT = [
    V('i_dien', 'incident', 3, 'Cúp điện giữa giờ tụng kinh', 'Đang công phu chiều, phụt một cái, cả chánh điện tối om. Loa im bặt.', [
        choose('toi', 'Chánh điện tối om', 'Trong điện có ba mươi người, nhiều cụ già.', [
            C('sac', 'Bật đèn sạc dự phòng, tụng tiếp không loa, mở cửa hông cho thoáng', 'good', 'Tiếng tụng kinh vẫn đều. Hai mươi phút sau có điện lại.'),
            C('nen', 'Thắp thêm thật nhiều nến khắp chánh điện', 'bad', 'Nến cắm khắp nơi, có cây sát mép chiếu.', 2, 'Nến thắp khắp chánh điện đông người, sát chiếu, sát rèm.', 'sf', True),
            C('ve', 'Dừng tụng, mời mọi người về', 'ok', 'Mọi người lục tục ra về trong bóng tối.', 1, 'Cho trăm người ra về trong bóng tối, bậc thềm trơn.', 'sf')]),
    ], note='Mất điện chỗ đông người: đèn sạc, lối đi, không thắp nến tràn lan.'),
    V('i_phuon', 'incident', 3, 'Tàn hương bén góc phướn', 'Gió mạnh, một tàn hương bay vào chân lá phướn treo gần lư. Mép vải bắt đầu bốc khói.', [
        order('dap', 'Dập lửa', '🧯 Xong', [
            O('ho', '📣', 'Hô mọi người lùi ra xa'),
            O('go', '🪢', 'Gỡ lá phướn khỏi móc, kéo xuống đất'),
            O('dap', '🧯', 'Dập bằng bình chữa cháy hoặc khăn ướt'),
            O('xem', '🔍', 'Xem kỹ còn tàn lửa âm ỉ không'),
            O('tat', '🪣', 'Tạt xô nước vào ổ điện bên cạnh cho chắc', bad=(3, 'Tạt nước vào ổ điện: chập điện, điện giật.', 'sf', True)),
        ], [('ho', 'dap', 1, 'Dập lửa khi khách còn đứng sát bên.', 'sf'), ('go', 'dap', 1, 'Dập lửa khi phướn còn treo sát mái.', 'sf'),
            ('dap', 'xem', 1, 'Chưa dập xong đã bỏ đi.', 'sf')],
            lead='Bấm theo thứ tự sẽ làm.', done='Lửa tắt hẳn, không ai bị gì.'),
        choose('sau', 'Sau đó', 'Lá phướn cháy sém một góc.', [
            C('doi', 'Dời lư hương xa phướn, đặt thêm bình chữa cháy, báo thầy trụ trì', 'good', 'Thầy Huệ Minh gật đầu: “Lư dời ra giữa sân là phải.”'),
            C('giau', 'Gấp lá phướn cất đi, không nói với ai', 'bad', 'Lá phướn nằm trong kho.', 2, 'Suýt cháy mà giấu, chỗ nguy hiểm vẫn y nguyên.', 'hn')]),
    ], note='Lửa nhỏ: người ra trước, gỡ đồ dễ cháy, dập rồi kiểm lại. Không tạt nước vào điện.', mods=(None, 'windy'), min_day=2),
    V('i_dot', 'incident', 0, 'Mái tây dột trên tủ kinh', 'Mưa dầm cả đêm. Sáng ra nước nhỏ tong tong từ mái tây xuống ngay tủ kinh sách.', [
        pick('dot', 'Chống dột', '☔ Xong', [
            I('doi', '📚', 'Dời kinh sách sang kệ khô', 'sách cũ, giấy mỏng', True, 'Kinh sách để nguyên dưới chỗ dột, ướt nhòe cả chồng.', 2),
            I('thau', '🪣', 'Đặt thau hứng nước', 'chỗ nước nhỏ xuống', True, 'Nước tràn lênh láng sàn gỗ.', 1),
            I('dien', '🔌', 'Rút điện đèn gần chỗ dột', 'ổ cắm ngay dưới', True, 'Ổ điện ngay chỗ nước nhỏ mà không rút.', 2, 'sf', True),
            I('leo', '🪜', 'Leo lên mái lợp lại ngói ngay lúc mưa to', 'cho xong', False, 'Leo mái ngói ướt giữa trời mưa: trượt một cái là ngã.', 3, 'sf', True),
            I('phoi', '☀️', 'Phơi kinh ướt ngoài nắng gắt', 'cho mau khô', False, 'Phơi giấy cũ ngoài nắng gắt: giấy giòn, mực phai.', 1),
            I('hong', '🍃', 'Hong kinh ướt chỗ mát có gió', 'kẹp giấy thấm từng trang', True, 'Kinh ướt để nguyên, mai mốc meo.', 1),
        ], lead='Chọn những việc sẽ làm.', done='Kinh sách khô ráo. Mai tạnh mưa nhờ thợ lên lợp lại ngói.'),
    ], note='Dột: cứu sách, hứng nước, rút điện. Tạnh mưa mới lên mái.', mods=('rain',), weight=2),
]

VARIANTS = YARD + HALL + GUIDE + KITCHEN + BOOK + LISTEN + CEREMONY + CARE + INCIDENT

# ================================================================ the morning (setup task)
KIND_LABEL = dict(setup='Thời khóa sáng', yard='Sân vườn', hall='Chánh điện', guide='Đón khách', kitchen='Bếp chay', book='Sổ công đức',
                  listen='Lắng nghe', ceremony='Chuẩn bị lễ', care='Giúp người già, trẻ nhỏ', incident='Sự cố')
KIND_EMOJI = dict(setup='🔔', yard='🧹', hall='🛕', guide='🧭', kitchen='🥬', book='📒', listen='🍵', ceremony='🏮', care='🤝', incident='⚠️')

# ================================================================ day modifiers
MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Quét sân, lo hương đèn, đón khách lẻ, bếp chay như mọi ngày.', weight=4),
    dict(id='ram', emoji='🌕', label='Ngày rằm', hint='Phật tử về chùa đông: tối có lễ cầu an, trưa phát cơm chay, sân đông trẻ nhỏ.', min_day=2, weight=2),
    dict(id='rain', emoji='🌧️', label='Mưa dầm', hint='Sân trơn rêu, mái tây hay dột, khách ít.', min_day=2, weight=2),
    dict(id='tour', emoji='🚌', label='Có đoàn tham quan', hint='Đoàn của chị Linh ghé: nhắc trang phục, chỗ thắp hương, chỗ cần yên lặng.', min_day=2, weight=2),
    dict(id='windy', emoji='🍃', label='Gió mùa', hint='Gió mạnh: tàn hương bay, phướn bay sát lư. Để ý lửa.', min_day=3, weight=1),
]

# What thầy Huệ Minh says about the day after breakfast (by the day's mod).
MOD_WORD = dict(
    normal='ngày thường. Quét sân cho sạch, hương đèn để ý gió, khách lẻ tới thì đón cho chu đáo.',
    ram='rằm, Phật tử về đông. Trưa phát cơm, tối cầu an: con lo lối đi, đèn đóm, để ý người già với trẻ nhỏ.',
    rain='mưa dầm. Bậc đá trơn, mái tây hay dột: con xem tủ kinh trước.',
    tour='có đoàn của cô Linh ghé. Nhắc khách trang phục nhẹ nhàng, chỉ chỗ thắp hương, chỗ cần yên lặng.',
    windy='gió mùa về. Tàn hương bay, phướn bay: lư hương phải xa phướn, đèn cầy phải có chụp.',
)

# ================================================================ small stories (by people index), every third visit
REG_STORY = {
    0: ('Thầy Huệ Minh: “Quét sân cũng là tu, con quét chậm thôi.”', 'Thầy Huệ Minh dạy bạn cách thỉnh chuông cho tiếng ngân dài.',
        'Thầy Huệ Minh giao bạn chìa khóa gác chuông.'),
    1: ('Bà Nhạn: “Canh chay ngọt là nhờ nấm với củ cải, không nhờ bột ngọt.”', 'Bà Nhạn chép tay cho bạn công thức chả chay của bà.',
        'Bà Nhạn bảo cả ban trai soạn nay nghe lời bạn nêm canh.'),
    4: ('Bé Na: “Thầy ơi, cá đỏ có tên không ạ?”', 'Bé Na đặt tên cho cả mười hai con cá trong hồ sen.', 'Bé Na được điểm mười bài văn “Ngôi chùa quê em”.'),
    5: ('Chị Quyên: “Chiều nào ngồi ở hiên chùa, chị cũng thấy nhẹ lòng.”', 'Chị Quyên phụ bà Nhạn rửa chén sau bữa trưa.',
        'Chị Quyên đi làm lại, rằm nào cũng về chùa phát cơm.'),
    6: ('Ông Bảy Đò: “Hồi ông chèo đò, nghe chuông chùa là biết về tới bến.”', 'Ông Bảy kể chuyện năm bão, cả làng khiêng chuông lên gác.',
        'Ông Bảy tặng chùa mái chèo cũ, treo ở nhà khách.'),
}

INTRO = dict(
    title='Giới thiệu nghề: làm thầy ở chùa Gió Lành',
    lead='Chùa Gió Lành bên bến sông, cổng tam quan có hàng cau, quả chuông đồng dân làng góp đúc. Bạn là thầy trẻ trong chùa, '
         'giúp thầy trụ trì lo việc hằng ngày: sân vườn, hương đèn, bếp chay, sổ công đức, đón khách, lắng nghe người buồn.',
    work=[('🔔', 'Sáng: giữ thời khóa, thỉnh chuông, công phu'), ('🧹', 'Quét sân, chăm hồ sen, tỉa cây'),
          ('🪔', 'Hương đèn an toàn: xa rèm, đèn có chụp'), ('🧭', 'Chỉ dẫn khách: trang phục, chỗ thắp hương, chỗ yên lặng'),
          ('🥬', 'Nấu cơm chay: thay đồ mặn bằng đồ chay'), ('📒', 'Sổ công đức: đếm đúng, ghi đúng từng xu'),
          ('🍵', 'Lắng nghe người buồn, khi cần thì tìm bác sĩ, người thân'), ('🏮', 'Lo lễ rằm: lối đi, đèn, loa vừa đủ')],
    meet=[('🙏', 'Thầy Huệ Minh: dặn ít mà thấy hết'), ('🍲', 'Bà Nhạn: bếp chay hai mươi năm'), ('🧮', 'Cô Hạnh: đếm hòm công đức'),
          ('🔌', 'Anh Toàn: loa đài, đèn đóm'), ('👧', 'Bé Na: hay hỏi “vì sao”'), ('🍂', 'Chị Quyên: hay ngồi một mình ở hiên'),
          ('👴', 'Ông Bảy Đò: 86 tuổi, rằm nào cũng lên'), ('🚌', 'Chị Linh dẫn đoàn, anh Phát lo “ngày xấu”')],
    stars=[('🧹', 'Sân sạch, cây tốt, hồ trong'), ('🪔', 'Không ngọn lửa nào sát rèm'), ('🥬', 'Bếp chay đúng là chay'),
           ('📒', 'Sổ công đức khớp từng xu'), ('🍵', 'Lắng nghe trước, khuyên sau'), ('🙏', 'Không xin tiền ai, không xem số')],
)
PAY_NOTE = 'Chùa gửi tiền chi dùng theo việc, đủ trà nước, xà phòng, đồ dùng.'

# ================================================================ surprises (kit desk scripts)
DESK = [
    dict(id='fake_monk', title='Người giả sư đi quyên tiền', emoji='🥣', npc=8, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Anh Phát chạy lên: “Thầy ơi, dưới phố có người mặc áo nhà sư đi từng nhà xin tiền, nói là quyên cho chùa Gió Lành.”',
         options=[dict(id='report', label='Nói rõ chùa không cử ai đi quyên tiền, báo thầy trụ trì và công an phường', hint='', effects=dict(xp=4), good=True,
                       outcome='Công an phường mời người đó về làm việc. Cả phố biết chùa không đi xin tiền ai.'),
                  dict(id='ignore', label='Chuyện ngoài phố, kệ', hint='', effects=dict(patience=-3), good=None,
                       outcome='Mấy hôm sau còn vài nhà bị xin tiền nữa.'),
                  dict(id='chase', label='Chạy xuống giật cái bát của người đó', hint='', effects=dict(review=[2, 'Thầy chùa xô xát giữa phố, ai cũng nhìn.']), good=False,
                       outcome='Hai bên giằng co giữa phố. Người đó bỏ chạy, còn bạn thì bị người qua đường quay clip.')],
         default='ignore'),
    dict(id='live_sell', title='Người livestream bán vòng “trì chú”', emoji='📱', npc=0, min_day=2, tone='tense', at='between', weight=2, mods=None,
         text='Một người đứng giữa sân quay điện thoại: “Vòng tay này được chùa trì chú, đeo vào là tài lộc, chốt đơn nha cả nhà!”',
         options=[dict(id='talk', label='Mời ra ngoài cổng, nói rõ chùa không bán vật phẩm “linh”, không cho mượn tên chùa', hint='', effects=dict(xp=4), good=True,
                       outcome='Người đó tắt máy, đi ra. Chiều thầy trụ trì dán thêm tờ thông báo ở cổng.'),
                  dict(id='let', label='Kệ, miễn không làm ồn', hint='', effects=dict(review=[3, 'Vào chùa thấy người ta bán vòng “trì chú” giữa sân, chùa cũng để.', 7]), good=False,
                       outcome='Buổi live có cả nghìn người xem, ai cũng tưởng chùa bán vòng.'),
                  dict(id='grab', label='Giật điện thoại tắt live', hint='', effects=dict(review=[2, 'Thầy chùa giật điện thoại của khách.', 7]), good=False,
                       outcome='Người đó la lên, quay lại cảnh bị giật điện thoại.')],
         default='let'),
    dict(id='phone', title='Chuông điện thoại giữa giờ tụng kinh', emoji='📳', npc=0, min_day=1, tone='gentle', at='between', weight=3, mods=None,
         text='Đang tụng kinh, điện thoại một bác khách đổ chuông inh ỏi. Bác lúng túng không tắt được.',
         options=[dict(id='help', label='Nhẹ nhàng ra hiệu, mời bác ra hiên nghe máy, chỉ bác cách tắt chuông', hint='', effects=dict(xp=3), good=True,
                       outcome='Bác khách cảm ơn, từ đó vào chùa là để máy im lặng.'),
                  dict(id='wait', label='Tụng tiếp, mặc kệ', hint='', effects=dict(patience=-2), good=None, outcome='Chuông reo ba hồi rồi tắt.'),
                  dict(id='scold', label='Dừng tụng, nhắc to trước mọi người', hint='', effects=dict(review=[3, 'Lỡ quên tắt chuông mà bị nhắc to giữa chánh điện, xấu hổ quá.', 6]), good=False,
                       outcome='Bác khách đỏ mặt, đi ra luôn.')],
         default='wait'),
    dict(id='dog', title='Chó hoang chạy vào sân', emoji='🐕', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một con chó gầy nhom lạc vào sân chùa, mấy đứa nhỏ hét toáng lên.',
         options=[dict(id='feed', label='Bảo các bé đứng yên, dắt chó ra góc cổng, cho bát cơm, nhờ người hỏi chủ', hint='', effects=dict(xp=3), good=True,
                       outcome='Con chó ăn xong nằm yên. Chiều có cậu bé dưới bến tới nhận về.'),
                  dict(id='shoo', label='Lấy gậy đuổi ra', hint='', effects=dict(patience=-3), good=None, outcome='Con chó chạy vòng quanh sân, làm đổ chậu hoa.'),
                  dict(id='leave', label='Kệ nó', hint='', effects=dict(review=[3, 'Chó lạ chạy trong sân chùa, bé Na sợ khóc thét mà không ai lo.', 5]), good=False,
                       outcome='Bé Na sợ quá, khóc thét.')],
         default='shoo'),
    dict(id='gift', title='Phong bì “biếu thầy uống trà”', emoji='✉️', npc=6, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Ông Bảy Đò dúi vào tay bạn một phong bì: “Ông biếu thầy uống trà. Thầy cầm cho ông vui.”',
         options=[dict(id='book', label='Cảm ơn ông, nói con xin gửi vào quỹ chùa, ghi sổ tên ông', hint='', effects=dict(xp=4), good=True,
                       outcome='Ông Bảy gật gù: “Thầy làm vậy ông càng quý.”'),
                  dict(id='back', label='Từ chối, trả lại ông', hint='', effects={}, good=None, outcome='Ông Bảy hơi buồn, cất phong bì vào túi.'),
                  dict(id='keep', label='Cầm, bỏ túi riêng', hint='', effects=dict(review=[3, 'Người già biếu tiền, thầy nhận bỏ túi, chẳng ghi sổ gì.']), good=False,
                       outcome='Bà Nhạn đứng gần thấy hết, lắc đầu.')],
         default='back'),
    dict(id='bell_kid', title='Bé Na đòi đánh chuông lớn', emoji='🔔', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Bé Na leo lên gác chuông, ôm dùi chuông lớn: “Con đánh một cái thôi mà!” Thang gác dốc, lan can thấp.',
         options=[dict(id='down', label='Dỗ bé xuống trước, hẹn mai thỉnh chuông nhỏ cùng thầy', hint='', effects=dict(xp=3), good=True,
                       outcome='Sáng mai bé Na thỉnh ba tiếng chuông nhỏ, mặt nghiêm như người lớn.'),
                  dict(id='let', label='Để bé đánh một cái', hint='', effects=dict(review=[3, 'Để con nít leo gác chuông dốc đứng, hú hồn.', 6]), good=False,
                       outcome='Bé Na hụt chân ở bậc thang, may bạn đỡ kịp.'),
                  dict(id='yell', label='Quát bé xuống ngay', hint='', effects=dict(patience=-2), good=None, outcome='Bé Na giật mình, khóc mếu xuống thang.')],
         default='yell'),
    dict(id='smoke', title='Hàng xóm phàn nàn khói hương', emoji='💨', npc=0, min_day=3, tone='tense', at='between', weight=2, mods=('ram', 'windy'),
         text='Chị nhà bên chùa sang: “Khói hương bay sang nhà em cả ngày, con em bị hen, ho suốt đêm qua.”',
         options=[dict(id='move', label='Xin lỗi chị, dời lư hương vào góc trong, nhắc khách mỗi người một nén', hint='', effects=dict(xp=4), good=True,
                       outcome='Khói ít hẳn. Chị nhà bên mang sang biếu chùa rổ ổi.'),
                  dict(id='sorry', label='Xin lỗi, hứa để ý', hint='', effects=dict(patience=-2), good=None, outcome='Rằm sau khói vẫn bay sang.'),
                  dict(id='argue', label='“Chùa có trước nhà chị mà”', hint='', effects=dict(review=[2, 'Chị nhà bên sang nói chuyện con bị hen, thầy lại bảo chùa có trước. Nghe mà buồn.', 5]), good=False,
                       outcome='Chị nhà bên về, đóng sầm cửa sổ.')],
         default='sorry'),
    dict(id='rain_guests', title='Mưa to, khách trú dưới hiên', emoji='⛈️', npc=7, min_day=2, tone='gentle', at='between', weight=3, mods=('rain', 'tour'),
         text='Mưa đổ ào ào. Đoàn khách của chị Linh đứng nép dưới hiên, quần áo ướt, có cụ run run.',
         options=[dict(id='tea', label='Mời cả đoàn vào nhà khách ngồi, rót trà gừng nóng', hint='', effects=dict(xp=3), good=True,
                       outcome='Cả đoàn ngồi uống trà nghe mưa. Chị Linh bảo đây là đoạn đẹp nhất chuyến đi.'),
                  dict(id='stay', label='Để đoàn đứng hiên, mưa chắc tạnh nhanh', hint='', effects=dict(patience=-3), good=None, outcome='Mưa kéo dài, cụ già hắt hơi liên tục.')],
         default='stay'),
]

# ================================================================ situations (sit_ engine)
SITUATIONS = [
    dict(id='CG-S01', title='Sổ công đức lệch 20 xu', npc=2, tone='tense', min_day=2,
         opening='Cô Hạnh cộng lại sổ công đức tháng này: tiền trong quỹ ít hơn sổ 20 xu.',
         swap='Bạn là cô Hạnh, kế toán về hưu, lên chùa giữ sổ vì tin chùa minh bạch.',
         facts=[dict(id='slip', title='Giấy công đức', source='Ngăn kéo', text='Có một tờ giấy công đức 20 xu viết rồi mà quên ghi vào sổ ngày rằm.'),
                dict(id='count', title='Đếm lại', source='Quỹ chùa', text='Đếm lại tiền trong quỹ, từng tờ, có cô Hạnh ký.'),
                dict(id='rule', title='Lời thầy trụ trì', source='Thầy Huệ Minh', text='Thầy dặn: sổ lệch thì tìm cho ra, không bù, không sửa số.')],
         options=[dict(id='find', label='Cùng cô Hạnh đếm lại, dò từng giấy công đức, tìm ra dòng ghi sót, ghi chú rõ', requires=['slip', 'count'], quality='good', stars=5,
                       review='Sổ lệch thì cùng nhau dò lại, tìm ra chỗ sót, ghi rõ ràng. Rất minh bạch.',
                       outcome='Tìm ra tờ giấy 20 xu quên ghi. Sổ khớp, cô Hạnh ký tên bên cạnh dòng ghi chú.',
                       perspectives=[dict(who='Cô Hạnh', emoji='🧮', text='Lệch thì tìm, tìm được là yên tâm.'),
                                     dict(who='Thầy Huệ Minh', emoji='🙏', text='Sổ đúng thì lòng người mới yên.')]),
                  dict(id='pay', label='Lấy tiền túi bù 20 xu cho khớp, không nói', requires=['count'], quality='ok', stars=3,
                       review='Sổ khớp nhưng không ai biết vì sao lệch.',
                       outcome='Sổ khớp, nhưng tờ giấy ghi sót vẫn nằm trong ngăn kéo.',
                       perspectives=[dict(who='Cô Hạnh', emoji='🤔', text='Khớp mà không biết vì sao khớp thì chưa xong.'),
                                     dict(who='Thầy Huệ Minh', emoji='🙏', text='Tốt bụng, nhưng sổ cần sự thật.')]),
                  dict(id='edit', label='Sửa con số trong sổ cho bằng tiền quỹ', quality='bad', stars=1,
                       review='Sổ công đức mà sửa số cho khớp, ai còn dám gửi.',
                       outcome='Cô Hạnh thấy vết sửa, xin thôi giữ sổ.',
                       perspectives=[dict(who='Cô Hạnh', emoji='😟', text='Sửa số là mất hết lòng tin.'),
                                     dict(who='Anh Phát', emoji='📱', text='Vậy tiền em gửi có vào sổ không thầy?')])],
         lesson='Sổ công đức lệch thì cùng nhau đếm lại, dò từng giấy, ghi chú rõ. Không bù lặng lẽ, không sửa số.'),
    dict(id='CG-S02', title='Cụ ông ngất trong chánh điện', npc=6, tone='tense', min_day=2,
         opening='Giữa giờ lễ rằm, ông Bảy Đò gục xuống chiếu, gọi không trả lời.',
         facts=[dict(id='breath', title='Hơi thở', source='Nhìn kỹ', text='Ông còn thở, nhưng thở yếu, môi tái.'),
                dict(id='board', title='Bảng ở bếp', source='Nội quy chùa', text='Người ngất, khó thở: gọi 115. Giữ thoáng, không cho ăn uống gì.'),
                dict(id='son', title='Con trai ông Bảy', source='Sổ Phật tử', text='Có số điện thoại con trai ông, nhà cách chùa mười phút.')],
         options=[dict(id='call', label='Cho mọi người lùi ra, đặt ông nằm nghiêng chỗ thoáng, gọi 115, gọi con trai ông', requires=['breath', 'board'], quality='good', stars=5,
                       review='Ông cụ ngất, thầy cho mọi người lùi ra, gọi cấp cứu ngay. Bình tĩnh lắm.',
                       outcome='Xe cấp cứu tới sau mười phút. Hôm sau ông Bảy đã ngồi dậy ăn cháo.',
                       perspectives=[dict(who='Bác sĩ', emoji='🩺', text='Gọi sớm, để thoáng, không cho uống gì: làm đúng.'),
                                     dict(who='Con trai ông Bảy', emoji='👨', text='Cảm ơn thầy, may có thầy ở đó.')]),
                  dict(id='water', label='Đỡ ông dậy, cho uống nước đường', quality='bad', stars=1,
                       review='Ông cụ ngất mà cho uống nước, may không sặc.',
                       outcome='Ông Bảy sặc nước, mọi người hoảng hốt gọi cấp cứu.',
                       perspectives=[dict(who='Bác sĩ', emoji='🩺', text='Người đang lơ mơ thì không cho uống gì.'),
                                     dict(who='Bà Nhạn', emoji='🍲', text='Thương thì thương, nhưng phải gọi cấp cứu trước.')]),
                  dict(id='wait', label='Chờ con trai ông tới rồi tính', requires=['son'], quality='bad', stars=1,
                       review='Cụ ngất mà ngồi chờ người nhà.',
                       outcome='Mười phút sau con trai ông tới, phải tự gọi cấp cứu.',
                       perspectives=[dict(who='Con trai ông Bảy', emoji='😰', text='Sao không ai gọi cấp cứu?'),
                                     dict(who='Bác sĩ', emoji='🩺', text='Mười phút đó rất quý.')])],
         lesson='Người ngất: cho thoáng, nằm nghiêng, gọi 115 trước, báo người nhà sau. Không cho ăn uống gì.'),
    dict(id='CG-S03', title='Phật tử muốn cúng lễ “giải sao”', npc=8, tone='gentle', min_day=3,
         opening='Anh Phát mang tới mâm lễ to, xin chùa làm lễ “giải sao hạn”, sẵn sàng gửi bao nhiêu cũng được.',
         facts=[dict(id='worry', title='Anh Phát lo gì', source='Anh Phát', text='Anh vay tiền mở tiệm, đêm nào cũng mất ngủ vì sợ lỗ.'),
                dict(id='way', title='Thầy trụ trì', source='Thầy Huệ Minh', text='Chùa có tụng kinh cầu an chung mỗi rằm, ai cũng dự được, không thu tiền.'),
                dict(id='shop', title='Tiệm của anh Phát', source='Bé Na', text='Bé Na kể tiệm anh Phát bán điện thoại cũ, không ghi giá rõ ràng.')],
         options=[dict(id='listen', label='Mời anh dự lễ cầu an rằm, không thu tiền; ngồi nghe anh lo, gợi ý ghi giá rõ ràng cho khách tin', requires=['worry', 'way'], quality='good', stars=5,
                       review='Chùa không lấy tiền, không hứa giải được hạn, còn ngồi nghe tôi lo. Về tôi ghi giá rõ ràng, khách tin hơn.',
                       outcome='Tháng sau tiệm anh Phát đông khách hơn. Anh lên chùa phát cơm rằm.',
                       perspectives=[dict(who='Anh Phát', emoji='📱', text='Hóa ra cái em cần là có người nghe.'),
                                     dict(who='Thầy Huệ Minh', emoji='🙏', text='Lo lắng thì cần người nghe, không cần lễ to.')]),
                  dict(id='do', label='Nhận phong bì, làm lễ riêng, hứa với anh là giải được hạn', quality='bad', stars=2,
                       review='Gửi bao nhiêu chùa cũng nhận, còn hứa chắc là giải được hạn.',
                       outcome='Anh Phát về yên tâm được ba hôm, rồi lại lo.',
                       perspectives=[dict(who='Cô Hạnh', emoji='🧮', text='Tiền gửi để “giải hạn” thì ghi sổ thế nào đây thầy?'),
                                     dict(who='Anh Phát', emoji='😟', text='Em gửi nhiều rồi mà sao vẫn lo?')]),
                  dict(id='refuse', label='Từ chối, bảo anh mang lễ về', requires=['way'], quality='ok', stars=3,
                       review='Từ chối đúng, nhưng hơi lạnh lùng.',
                       outcome='Anh Phát mang mâm lễ về, buồn thiu.',
                       perspectives=[dict(who='Anh Phát', emoji='😞', text='Em chỉ muốn yên tâm thôi mà.'),
                                     dict(who='Bà Nhạn', emoji='🍲', text='Từ chối thì từ chối, mời người ta chén trà đã chứ.')])],
         lesson='Chùa không thu tiền, không hứa giải được hạn cho ai. Người lo lắng cần được nghe: mời dự lễ cầu an chung, không thu tiền.'),
]
