"""✈️ Du học and 🌏 Làm việc ở nước ngoài: the catalogue of game/abroad.py (pure data).

Player feedback #254 (08/10): "cho được đi du học đi ạ hoặc ra nước ngoài làm việc ạ"; owner: OK, simple and happy.
Four friendly destinations, light flavour only: no politics, no real schools or companies (every school and branch
named here is made up). Prices are the base (pre-07/10) ones; game/abroad.py indexes them (game/price_index.py).

Ids are stored in saves (journey['abroad']): never rename or remove one.
"""

DESTS = (
    dict(id='han_quoc', flag='🇰🇷', name='Hàn Quốc', city='Seoul'),
    dict(id='nhat_ban', flag='🇯🇵', name='Nhật Bản', city='Osaka'),
    dict(id='phap', flag='🇫🇷', name='Pháp', city='Lyon'),
    dict(id='uc', flag='🇦🇺', name='Úc', city='Melbourne'),
)


def _l(scene, q, opts, ok, why):
    return dict(scene=scene, q=q, options=list(opts), ok=ok, why=why)


# ✈️ Du học: one short course per destination, one lesson a life day. `fee`: the base tuition.
PROGRAMS = {
    'han_quoc': dict(school='Học viện Sông Hàn', course='Dịch vụ khách hàng', fee=280, degree='Bằng Dịch vụ khách hàng · Seoul',
                     lessons=(
        _l('Buổi 1: lớp tiếng Hàn giao tiếp, cô giáo dạy cúi chào.', 'Khách bước vào tiệm, chào sao cho lịch sự?',
           ('Mỉm cười, cúi nhẹ, chào trước', 'Đợi khách chào trước', 'Vẫy tay từ xa'), 0, 'Chào trước, cúi nhẹ: khách thấy mình được đón.'),
        _l('Buổi 2: thực hành ở quán gà rán cạnh trường.', 'Món ra chậm, khách bắt đầu sốt ruột.',
           ('Im lặng làm tiếp', 'Báo rõ còn mấy phút, mời ly nước', 'Bảo khách sang quán khác'), 1, 'Nói rõ giờ chờ và chăm khách một chút là khách yên tâm.'),
        _l('Buổi 3: đóng vai xử lý phàn nàn theo nhóm.', 'Khách phàn nàn món đã nguội.',
           ('Giải thích do khách tới muộn', 'Giảm giá mà không hỏi', 'Xin lỗi, làm phần mới ngay'), 2, 'Sửa ngay cái sai trước, giải thích để sau.'),
        _l('Buổi 4: dã ngoại biển Busan, thi cuối khóa trên tàu.', 'Bí quyết giữ chân khách quen là gì?',
           ('Nhớ tên và món quen của khách', 'Giảm giá thật sâu', 'Treo thật nhiều biển hiệu'), 0, 'Khách quay lại vì được nhớ tới.'),
    )),
    'nhat_ban': dict(school='Trường Hoa Anh Đào Osaka', course='Quản lý vận hành (5S, Kaizen)', fee=320,
                     degree='Bằng Quản lý vận hành · Osaka', lessons=(
        _l('Buổi 1: thầy dạy 5S: sàng lọc, sắp xếp, sạch sẽ, săn sóc, sẵn sàng.', 'Bước đầu tiên của 5S là gì?',
           ('Sơn lại tường', 'Bỏ bớt đồ không cần dùng', 'Mua thêm tủ mới'), 1, 'Sàng lọc trước: bớt đồ thừa thì mới sắp xếp được.'),
        _l('Buổi 2: tham quan xưởng bánh, ai cũng tới sớm 5 phút.', 'Một lỗi nhỏ cứ lặp lại mỗi ngày.',
           ('Ghi lại, đề xuất sửa từng chút', 'Kệ, lỗi nhỏ mà', 'Đợi sếp tự thấy'), 0, 'Sửa từng chút mỗi ngày: đó là Kaizen.'),
        _l('Buổi 3: học giao ca bằng sổ, không dặn miệng.', 'Giao ca thế nào cho chắc?',
           ('Dặn miệng cho nhanh', 'Về nhà rồi nhắn tin', 'Ghi sổ đủ việc dở, hai bên cùng ký'), 2, 'Ghi sổ và cùng ký: ca sau không phải đoán.'),
        _l('Buổi 4: ngắm hoa ở công viên, chiều thuyết trình cuối khóa.', 'Kaizen nghĩa là gì?',
           ('Cải tiến nhỏ, đều đặn mỗi ngày', 'Làm thật nhanh', 'Thay hết một lần'), 0, 'Từng bước nhỏ, đều đặn, ai cũng góp ý được.'),
    )),
    'phap': dict(school='Trường bếp Ánh Sáng Lyon', course='Ẩm thực & bánh Pháp', fee=340, degree='Bằng Ẩm thực & bánh · Lyon',
                 lessons=(
        _l('Buổi 1: nhào bột bánh mì từ năm giờ sáng.', 'Bột chưa nở đủ mà đã tới giờ nướng.',
           ('Đợi thêm, ghi lại nhiệt độ phòng', 'Nướng luôn cho kịp', 'Thêm thật nhiều men'), 0, 'Bột cần thời gian; ghi lại để mẻ sau canh giờ chuẩn hơn.'),
        _l('Buổi 2: học bày bếp gọn, dụng cụ nào chỗ nấy trước khi nấu.', 'Vì sao chuẩn bị đủ trước khi nấu?',
           ('Cho đẹp ảnh', 'Nấu nhanh, ít quên, ít sai', 'Để thầy khen'), 1, 'Đủ đồ trong tầm tay thì nấu gọn và ít sai.'),
        _l('Buổi 3: làm bánh sừng bò, gấp bơ từng lớp.', 'Bơ chảy ra khi đang gấp bột.',
           ('Gấp tiếp cho xong', 'Bỏ cả mẻ', 'Cho bột vào tủ mát nghỉ rồi gấp tiếp'), 2, 'Bột nghỉ lạnh thì bơ đông lại, lớp bánh mới tơi.'),
        _l('Buổi 4: chợ phiên cuối tuần, cả lớp bán bánh mình làm.', 'Khách hỏi bánh có hạt không vì bị dị ứng.',
           ('Xem đúng thành phần rồi trả lời', 'Nói chắc là không có', 'Bảo khách tự xem'), 0, 'Dị ứng là chuyện an toàn: kiểm thành phần thật kỹ.'),
    )),
    'uc': dict(school='Học viện Cây Keo Vàng', course='Quản trị nhà hàng – khách sạn', fee=360,
               degree='Bằng Quản trị nhà hàng – khách sạn · Melbourne', lessons=(
        _l('Buổi 1: học pha cà phê ở một quán nhỏ ven phố.', 'Khách gọi món mà bạn nghe chưa rõ.',
           ('Hỏi lại cho chắc rồi mới làm', 'Đoán đại', 'Làm món mình quen'), 0, 'Hỏi lại một câu đỡ hơn làm sai cả ly.'),
        _l('Buổi 2: thực tập lễ tân, đón khách nhận phòng buổi sáng.', 'Phòng khách đặt vẫn chưa dọn xong.',
           ('Bảo khách chờ ngoài sảnh, không nói gì', 'Xin lỗi, giữ hành lý, báo giờ có phòng', 'Đưa phòng khác chưa dọn'), 1, 'Nói thật, chăm khách trong lúc chờ: khách thông cảm.'),
        _l('Buổi 3: học an toàn thực phẩm trong bếp trường.', 'Thịt sống và rau trộn dùng chung thớt được không?',
           ('Không, mỗi loại một thớt', 'Được, rửa sơ là xong', 'Được nếu làm nhanh'), 0, 'Đồ sống và đồ ăn liền luôn tách riêng.'),
        _l('Buổi 4: thăm trang trại cừu ngoại ô, rồi làm bài cuối khóa.', 'Ca đông khách, cả đội đều mệt.',
           ('Bắt làm liền tới cuối', 'Đóng cửa sớm', 'Chia ca nghỉ ngắn luân phiên'), 2, 'Nghỉ ngắn luân phiên: quán vẫn chạy, người vẫn khỏe.'),
    )),
}
GRADES = (('xuat_sac', 'Xuất sắc'), ('gioi', 'Giỏi'), ('kha', 'Khá'))

# 🌏 Làm việc ở nước ngoài: the company sends you to its branch for `days` worked days at `pct` % more pay.
# `fee`: the base cost of the ticket and the work visa, paid up front and refunded when the contract is done.
WORK = {
    'han_quoc': dict(days=4, pct=50, fee=80, lines=(
        'Sáng Seoul se lạnh, đồng nghiệp rủ bạn ăn canh nóng gần chỗ làm.',
        'Tan ca, cả nhóm đi dạo bờ sông Hàn, ai cũng mỏi chân mà vui.',
        'Chị trưởng ca khen bạn chào khách rất dễ thương.',
        'Cuối tuần bạn học được thêm mấy câu tiếng Hàn từ bà chủ nhà.')),
    'nhat_ban': dict(days=5, pct=60, fee=100, lines=(
        'Tàu điện Osaka đúng giờ tới từng phút, bạn tới sớm năm phút như mọi người.',
        'Đồng nghiệp chỉ bạn cách gấp khăn thật vuông, thật thẳng.',
        'Bữa trưa cơm hộp đơn giản mà ngon, bạn chụp gửi về cho Bà Tám.',
        'Sếp dán tờ “cảm ơn” nhỏ lên bàn bạn vì làm việc gọn gàng.',
        'Tối về ký túc xá, cả phòng ngồi gấp hạc giấy.')),
    'phap': dict(days=5, pct=60, fee=110, lines=(
        'Sáng sớm ở Lyon thơm mùi bánh mì mới ra lò.',
        'Đồng nghiệp dạy bạn chào “bonjour” thật tươi mỗi lần khách vào.',
        'Trưa ngồi bên bờ sông, ăn miếng bánh kẹp phô mai.',
        'Ông khách quen người Pháp khen bạn làm việc rất tỉ mỉ.',
        'Chiều chủ nhật bạn đi chợ phiên, mua một hũ mứt về làm quà.')),
    'uc': dict(days=6, pct=70, fee=120, lines=(
        'Melbourne một ngày có đủ bốn mùa, bạn luôn mang theo áo khoác.',
        'Đồng nghiệp người Úc gọi bạn là “mate”, ai cũng thân thiện.',
        'Giờ nghỉ, bạn uống ly cà phê sữa ngon nhất từ trước tới giờ.',
        'Sếp tặng bạn tấm thiệp cảm ơn vì giúp cả ca lúc đông khách.',
        'Cuối tuần bạn ra biển ngắm chim cánh cụt nhỏ về tổ.',
        'Tối gọi video về nhà, cả hẻm xúm lại vẫy tay chào.')),
}
# Letters from home while you are away: the neighbourhood you miss.
LETTERS = (
    'Bà Tám nhắn: “Gác trọ bà để nguyên, về nhớ ghé ăn canh chua nghe.”',
    'Bé Tí gửi ảnh: “Em được 9 điểm toán nè!”',
    'Cô Ba nhắn: “Tạp hóa mới về mứt gừng, cô để dành cho con một hũ.”',
    'Chú Tư nhắn: “Hẻm mình mới sơn lại cổng, về là thấy liền.”',
    'Cô Lụa nhắn: “Tổ dân phố họp, ai cũng hỏi thăm con.”',
    'Bà Sáu nhắn: “Con mèo nhà bà cứ ra đầu hẻm ngóng con.”',
)
