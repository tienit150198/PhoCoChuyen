"""🏫 Trường học: the catalogue of game/school.py (pure data).

Owner 23/10: "du lịch trải nghiệm thật thì bạn làm cho nó đi học thật nữa nhé, nhiều ngành cũng thế xử lý luôn".
Player feedback #315 ("thêm du học ở Trung Quốc") and #322 ("trường học có nhiều môn học ... học đại học nhiều ngành").

* 🎓 Đại học Phố Mây (made up): MAJORS, each two học kỳ of three subjects, a tuition per học kỳ.
* ✈️ Du học một học kỳ: TERMS, one học kỳ abroad of three subjects (the language, the culture, one trade), a visa fee,
  culture events and a part-time job. Every school named here is made up; light flavour, no politics.
Subjects, their lessons and questions live in the banks game/school_bank_*.py (shapes: game/school_q.py).
`fee` / `visa` are base prices (game/school.py indexes them, game/price_index.py).

Ids are stored in saves (journey['school']): never rename or remove one.
"""
from __future__ import annotations

from . import school_bank_abroad as _abroad
from . import school_bank_health as _health
from . import school_bank_kinhte as _kinhte
from . import school_bank_land as _land
from . import school_bank_law as _law
from . import school_bank_media as _media
from . import school_bank_style as _style
from . import school_bank_tech as _tech

SUBJECTS = {**_kinhte.SUBJECTS, **_tech.SUBJECTS, **_health.SUBJECTS, **_law.SUBJECTS, **_style.SUBJECTS,
            **_land.SUBJECTS, **_media.SUBJECTS, **_abroad.SUBJECTS}

UNI = dict(name='Đại học Phố Mây', short='ĐH Phố Mây', emoji='🏫')


def _m(id, name, emoji, blurb, sems, careers, fee=150):
    return dict(id=id, kind='uni', name=name, emoji=emoji, blurb=blurb, sems=tuple(tuple(x) for x in sems),
                careers=tuple(careers), fee=fee)


# 🎓 The majors, in the order the page lists them. `careers`: the workplaces the degree helps (game/school.py perks).
MAJORS = (
    _m('kinh_te', 'Kinh tế', '📈', 'Hiểu giá cả, khách hàng và cách làm ăn nhỏ mà chắc.',
       (('kt_vimo', 'kt_marketing', 'kt_banhang'), ('kt_taichinh', 'kt_khoinghiep', 'kt_tmdt')),
       ('grocery', 'fruit', 'car_dealer', 'teller', 'jewelry')),
    _m('ke_toan', 'Kế toán', '🧮', 'Sổ sách gọn, chứng từ đủ, lương thuế rõ ràng.',
       (('ktn_nguyenly', 'ktn_chungtu', 'ktn_excel'), ('ktn_thue', 'ktn_luong', 'ktn_baocao')),
       ('accounting', 'corp_accounting', 'tax_payroll', 'group_accounting')),
    _m('cntt', 'Công nghệ thông tin', '💻', 'Máy tính, mạng, web và giữ an toàn dữ liệu.',
       (('it_maytinh', 'it_laptrinh', 'it_mang'), ('it_csdl', 'it_web', 'it_baomat')),
       ('it_helpdesk', 'kol', 'research'), fee=170),
    _m('y_duoc', 'Y dược – Điều dưỡng', '🩺', 'Chăm người bệnh, sơ cứu, đọc nhãn thuốc cẩn thận.',
       (('yd_cothe', 'yd_dieuduong', 'yd_socuu'), ('yd_duoc', 'yd_dinhduong', 'yd_giaotiep')),
       ('nurse', 'pharmacy', 'vet', 'babysitter'), fee=180),
    _m('su_pham', 'Sư phạm', '🍎', 'Hiểu trẻ, dạy vui, lớp học nề nếp.',
       (('sp_tamly', 'sp_phuongphap', 'sp_lophoc'), ('sp_danhgia', 'sp_kynang', 'sp_thuctap')),
       ('teacher', 'babysitter', 'library'), fee=100),
    _m('luat', 'Luật', '⚖️', 'Quyền, nghĩa vụ, hợp đồng và tư vấn dễ hiểu.',
       (('lu_daicuong', 'lu_hopdong', 'lu_laodong'), ('lu_kinhdoanh', 'lu_giaothong', 'lu_tuvan')),
       ('lawyer', 'police', 'customs', 'hr_admin'), fee=170),
    _m('kien_truc', 'Kiến trúc', '🏛️', 'Vẽ nhà, chọn vật liệu, giữ hồn công trình xưa.',
       (('ktr_vekythuat', 'ktr_lichsu', 'ktr_vatlieu'), ('ktr_noithat', 'ktr_nhao', 'ktr_xanh')),
       ('restore', 'art_studio', 'homestay'), fee=180),
    _m('thoi_trang', 'Thiết kế thời trang', '👗', 'Vải, màu, đường kim và một bộ sưu tập của riêng bạn.',
       (('tt_hinhhoa', 'tt_chatlieu', 'tt_catmay'), ('tt_phoimau', 'tt_suutap', 'tt_kinhdoanh')),
       ('clothing', 'nail', 'salon', 'photobooth'), fee=160),
    _m('du_lich', 'Du lịch – Khách sạn', '🛎️', 'Đón khách, dẫn đoàn, phòng sạch, tiệc chu đáo.',
       (('dl_tongquan', 'dl_letan', 'dl_huongdan'), ('dl_buongphong', 'dl_nhahang', 'dl_diali')),
       ('hotel', 'reception', 'tour_guide', 'homestay', 'banquet')),
    _m('nong_nghiep', 'Nông nghiệp', '🌾', 'Đất tốt, cây khỏe, gà vui, nông sản sạch.',
       (('nn_trongtrot', 'nn_dat', 'nn_channuoi'), ('nn_sauhai', 'nn_huuco', 'nn_tieuthu')),
       ('farm', 'florist', 'fruit', 'pet_shop'), fee=120),
    _m('ngon_ngu', 'Ngôn ngữ Anh', '🗣️', 'Nói, viết, dịch tiếng Anh cho công việc mỗi ngày.',
       (('nna_giaotiep', 'nna_nguphap', 'nna_tuvung'), ('nna_email', 'nna_dich', 'nna_vanhoa')),
       ('tour_guide', 'customer_care', 'reception', 'flight_attendant', 'secretary')),
    _m('truyen_thong', 'Báo chí – Truyền thông', '🎙️', 'Kể chuyện thật, nói tự tin, quay chụp đẹp.',
       (('bc_nhapmon', 'bc_viettin', 'bc_thuyettrinh'), ('bc_quayphim', 'bc_mxh', 'bc_daoduc')),
       ('radio', 'kol', 'actor', 'singer')),
    _m('co_khi', 'Cơ khí – Động lực', '🔧', 'Động cơ, điện, dụng cụ và an toàn trong xưởng.',
       (('ck_antoan', 'ck_dongco', 'ck_dien'), ('ck_xemay', 'ck_dungcu', 'ck_baoduong')),
       ('moto', 'tuning', 'repair', 'oil', 'railway'), fee=140),
)


def _ev(id, emoji, title, scene, options):
    return dict(id=id, emoji=emoji, title=title, scene=scene, options=tuple(options))


def _job(scene, q, options, ok, why):
    return dict(scene=scene, q=q, options=tuple(options), ok=ok, why=why)


# 🎉 Hoạt động ở trường (đại học): no wrong answer, each choice is a memory.
UNI_EVENTS = (
    _ev('hoi_thao', '🏸', 'Hội thao khoa', 'Khoa tổ chức hội thao, lớp bạn thiếu một người chơi cầu lông.',
        (('Xung phong ra sân', 'Bạn thua sát nút mà cả lớp hò reo như vô địch.'),
         ('Làm cổ động viên', 'Bạn vẽ băng rôn “Cố lên!”, cả khán đài cười rần.'))),
    _ev('van_nghe', '🎤', 'Đêm văn nghệ', 'Đêm văn nghệ chào tân sinh viên dưới sân trường.',
        (('Hát song ca với bạn cùng phòng', 'Lạc tông một chút mà ai cũng vỗ tay.'),
         ('Phụ hậu trường', 'Bạn giữ đèn pin cho cả đoàn múa, đỉnh của chóp.'))),
    _ev('viec_lam', '💼', 'Ngày hội việc làm', 'Các nơi trong phố mang gian hàng tới trường tìm thực tập sinh.',
        (('Ghé từng gian hỏi chuyện', 'Một chị quản lý ghi tên bạn: “Ra trường nhớ ghé chị nha.”'),
         ('Nộp thử một bản CV', 'Bạn được góp ý sửa CV, về sửa liền cho đẹp.'))),
    _ev('thu_vien', '📚', 'Đêm thư viện', 'Mùa thi, thư viện mở tới khuya, có trà gừng miễn phí.',
        (('Ôn bài với nhóm', 'Cả nhóm thay nhau giảng, ai cũng hiểu thêm một chút.'),
         ('Ngồi góc cửa sổ học một mình', 'Yên tĩnh, ấm trà, đọc được cả chương.'))),
)


def _t(id, flag, country, city, school, sems, careers, fee, visa, fly, events, jobs, visa_q, home):
    return dict(id=id, kind='abroad', flag=flag, country=country, city=city, school=school, name=f'Du học {country}',
                sems=tuple(tuple(x) for x in sems), careers=tuple(careers), fee=fee, visa=visa, fly=tuple(fly),
                events=tuple(events), jobs=tuple(jobs), visa_q=visa_q, home=home)


# ✈️ The terms abroad. Program ids start with 'dh_'; `dest` is the country id game/abroad_content.py uses (the
# degree counts there as one of the 🎓 degrees of ✈️ Du học, by country).
TERMS = (
    _t('dh_han_quoc', '🇰🇷', 'Hàn Quốc', 'Seoul', 'Học viện Sông Hàn', (('dh_kr_ngu', 'dh_kr_vh', 'dh_kr_dv'),),
       ('customer_care', 'salon', 'milk_tea', 'nail'), 420, 40,
       ('🧳 Bà Tám dúi vào vali một hũ mắm ruốc “ăn cho đỡ nhớ nhà”.', '🛫 Máy bay cất cánh, phố Mây nhỏ dần dưới cánh mây.',
        '🛬 Seoul se lạnh, bạn kéo khóa áo khoác lên tận cằm.', '🏠 Ký túc xá có sưởi sàn, bạn cùng phòng chào: “안녕하세요!”'),
       (_ev('kr_chuseok', '🌕', 'Tết Chuseok', 'Nhà bạn cùng lớp mời về ăn Chuseok, cả nhà làm bánh songpyeon.',
            (('Nặn bánh hình trăng khuyết', 'Bánh của bạn méo xíu, bà nội vẫn khen đẹp.'),
             ('Cúi chào ông bà thật lễ phép', 'Ông gật gù, dúi cho bạn quả hồng ngọt lịm.'))),
        _ev('kr_hanbok', '👘', 'Mặc hanbok dạo cung điện', 'Cuối tuần cả lớp thuê hanbok đi dạo quanh cung điện cổ.',
            (('Chụp ảnh nhóm', 'Tấm ảnh đẹp tới mức cô giáo xin làm ảnh bìa lớp.'),
             ('Nghe hướng dẫn viên kể chuyện', 'Bạn học thêm được mấy từ tiếng Hàn về lịch sử.'))),
        _ev('kr_cho_dem', '🌃', 'Chợ đêm', 'Chợ đêm mùa đông, khói bánh cá nướng bay khắp ngõ.',
            (('Ăn thử tteokbokki', 'Cay xè mà ngon, bạn uống hết hai ly nước.'),
             ('Mua găng tay len', 'Cô bán hàng tặng thêm đôi tất vì bạn nói “감사합니다” rất dễ thương.')))),
       (_job('Ca tối ở cửa hàng tiện lợi gần trường.', 'Khách hỏi nhỏ nhẹ món mì cay để ở đâu.',
             ('Cúi chào, dẫn khách tới kệ mì', 'Chỉ tay đại một hướng', 'Bảo khách tự tìm'), 0, 'Dẫn tận nơi: khách vui, quay lại lần sau.'),
        _job('Phụ bếp quán gà rán gần ga.', 'Đơn gà ra trễ năm phút, khách sốt ruột.',
             ('Im lặng làm tiếp', 'Xin lỗi, báo còn mấy phút, mời ly nước', 'Đổ lỗi cho bếp'), 1, 'Nói rõ thời gian chờ và chăm khách một chút.'),
        _job('Phụ việc ở quán cà phê sách.', 'Có khách để quên điện thoại trên bàn.',
             ('Cất vào quầy, ghi giờ và chỗ ngồi', 'Để nguyên trên bàn', 'Mang về nhà giữ giúp'), 0, 'Giữ ở quầy và ghi lại để trả đúng người.')),
       ('Vì sao bạn chọn du học Hàn Quốc?', ('Để học nghề dịch vụ, rồi về làm ở phố mình', 'Để được gặp thần tượng mỗi ngày', 'Em chưa nghĩ tới'), 0),
       '🛬 Về tới phố Mây, bạn chào cả hẻm bằng một cái cúi người kiểu Hàn.'),
    _t('dh_nhat_ban', '🇯🇵', 'Nhật Bản', 'Osaka', 'Trường Hoa Anh Đào Osaka', (('dh_jp_ngu', 'dh_jp_vh', 'dh_jp_5s'),),
       ('delivery', 'post_office', 'railway', 'laundry'), 460, 45,
       ('🧳 Bạn gấp quần áo thật vuông vào vali để “tập trước” kiểu Nhật.', '🛫 Cất cánh lúc sáng sớm, nắng chiếu lấp lánh cánh máy bay.',
        '🛬 Tàu điện Osaka tới đúng từng phút, bạn suýt chạy theo không kịp.', '🏠 Phòng ký túc nhỏ xinh, gọn gàng, có cả bàn sưởi kotatsu.'),
       (_ev('jp_hanami', '🌸', 'Ngắm hoa anh đào', 'Lớp trải bạt dưới tán anh đào trong công viên.',
            (('Mang cơm nắm mời cả lớp', 'Ai cũng khen cơm nắm của bạn mặn mà.'),
             ('Dọn sạch chỗ ngồi trước khi về', 'Thầy giáo gật đầu: “Đây mới là 5S thật sự.”'))),
        _ev('jp_onsen', '♨️', 'Tắm suối nước nóng', 'Chuyến đi suối nước nóng trên núi cùng bạn cùng phòng.',
            (('Đọc kỹ nội quy trước khi vào', 'Bạn làm đúng hết, bác bảo vệ mỉm cười.'),
             ('Ngắm tuyết rơi ngoài hiên', 'Lần đầu thấy tuyết, bạn quay video gửi Bà Tám.'))),
        _ev('jp_matsuri', '🏮', 'Lễ hội mùa hè', 'Lễ hội đèn lồng, bạn được mượn yukata mặc thử.',
            (('Chơi vớt cá vàng', 'Vớt được một chú, đặt tên là “Mây”.'),
             ('Xem pháo hoa bên sông', 'Pháo hoa nở rực, bạn nhớ đêm giao thừa ở phố.')))),
       (_job('Làm thêm ở tiệm cơm hộp.', 'Khách đặt 5 hộp mang đi, bạn đóng gói thế nào?',
             ('Kiểm đếm đủ hộp, kèm đũa, cúi chào khi đưa', 'Đưa nhanh không kiểm', 'Để khách tự lấy'), 0, 'Kiểm đủ và đưa bằng hai tay là phép lịch sự.'),
        _job('Làm thêm ở kho của một xưởng nhỏ.', 'Kệ dụng cụ bừa bộn, ai cũng mất công tìm.',
             ('Mua thêm kệ mới', 'Bỏ đồ thừa, dán nhãn từng ngăn', 'Để mai tính'), 1, 'Sàng lọc rồi sắp xếp: đúng 5S.'),
        _job('Phát tờ rơi cho tiệm bánh trước ga.', 'Trời mưa, khách vội không nhận tờ rơi.',
             ('Cúi chào, cảm ơn và đứng chỗ có mái che', 'Nhét tờ rơi vào tay khách', 'Bỏ về sớm'), 0, 'Lịch sự và tìm chỗ hợp lý, không làm phiền khách.')),
       ('Vì sao bạn chọn du học Nhật Bản?', ('Chỉ để mua đồ hiệu', 'Để học cách làm việc gọn gàng, đúng giờ', 'Đi cho biết thôi'), 1),
       '🛬 Về tới phố Mây, bạn dọn lại gác trọ Bà Tám theo đúng 5S.'),
    _t('dh_phap', '🇫🇷', 'Pháp', 'Lyon', 'Trường bếp Ánh Sáng Lyon', (('dh_fr_ngu', 'dh_fr_vh', 'dh_fr_bep'),),
       ('cafe_bakery', 'restaurant', 'banquet', 'pho'), 480, 50,
       ('🧳 Cô Ba gói cho bạn ít cà phê phin “để Tây nếm thử”.', '🛫 Chuyến bay dài, bạn xem hết ba bộ phim.',
        '🛬 Lyon sáng sớm thơm mùi bánh mì mới ra lò.', '🏠 Căn gác nhỏ có cửa sổ nhìn ra hai con sông.'),
       (_ev('fr_cho', '🧺', 'Chợ phiên cuối tuần', 'Chợ phiên bên bờ sông, đủ loại phô mai và trái cây.',
            (('Chào “Bonjour!” thật tươi', 'Bà bán phô mai cho bạn nếm thử ba loại.'),
             ('Mua hoa tặng cô chủ nhà', 'Cô chủ nhà cảm động, mời bạn ăn tối.'))),
        _ev('fr_den', '🕯️', 'Lễ hội ánh sáng', 'Cả thành phố đặt nến trên bậu cửa sổ, đường phố lung linh.',
            (('Đặt nến ở cửa sổ phòng mình', 'Ô cửa của bạn cũng sáng cùng cả phố.'),
             ('Dạo phố với bạn cùng lớp', 'Hai đứa đi tới khuya, mỏi chân mà vui.'))),
        _ev('fr_bep', '🥐', 'Thi làm bánh của lớp', 'Lớp thi làm bánh sừng bò, giám khảo là thầy bếp trưởng.',
            (('Cho bột nghỉ đủ giờ', 'Bánh của bạn phồng đều, thầy giơ ngón cái.'),
             ('Thêm chút cà phê phin vào nhân', 'Thầy bất ngờ: “Hương vị Việt Nam, tuyệt lắm!”')))),
       (_job('Phụ bán ở tiệm bánh góc phố.', 'Khách hỏi bánh có hạt không vì bị dị ứng.',
             ('Nói đại là không có', 'Xem đúng thành phần rồi trả lời', 'Bảo khách tự đoán'), 1, 'Dị ứng là chuyện an toàn: kiểm thành phần thật kỹ.'),
        _job('Rửa chén ở quán ăn gia đình.', 'Bếp đông, chén dĩa chất đầy.',
             ('Rửa theo thứ tự: ly, chén, rồi xoong nồi', 'Rửa lộn xộn cho nhanh', 'Để cuối ca rửa một lần'), 0, 'Làm có thứ tự thì nhanh và sạch hơn.'),
        _job('Phục vụ bàn quán cà phê vỉa hè.', 'Khách muốn tính tiền, nói “L’addition, s’il vous plaît”.',
             ('Mang thực đơn ra', 'Mang hóa đơn tới bàn', 'Mang thêm nước'), 1, '“L’addition” là hóa đơn tính tiền.')),
       ('Vì sao bạn chọn du học Pháp?', ('Để học nghề bếp bánh thật giỏi', 'Để chụp ảnh tháp nổi tiếng thôi', 'Bạn bè rủ'), 0),
       '🛬 Về tới phố Mây, bạn làm một mẻ bánh sừng bò mời cả hẻm.'),
    _t('dh_uc', '🇦🇺', 'Úc', 'Melbourne', 'Học viện Cây Keo Vàng', (('dh_au_ngu', 'dh_au_vh', 'dh_au_ks'),),
       ('hotel', 'reception', 'homestay', 'lifeguard'), 500, 50,
       ('🧳 Bạn nhét thêm áo khoác vì nghe nói Melbourne một ngày có bốn mùa.', '🛫 Bay qua đêm, sáng ra đã thấy biển xanh.',
        '🛬 Ra sân bay, một bác tài cười: “G’day, mate!”', '🏠 Nhà trọ chung với ba bạn, sân sau có cây chanh.'),
       (_ev('au_bbq', '🍖', 'Tiệc nướng ngoài trời', 'Hàng xóm mời BBQ ở công viên cuối tuần.',
            (('Mang gỏi cuốn góp vui', 'Đĩa gỏi cuốn hết veo, ai cũng xin công thức.'),
             ('Đứng nướng phụ chú hàng xóm', 'Chú dạy bạn lật xúc xích “đúng kiểu Úc”.'))),
        _ev('au_bien', '🐧', 'Xem chim cánh cụt về tổ', 'Chiều tối ra biển xem chim cánh cụt nhỏ lạch bạch về tổ.',
            (('Ngồi im, không bật đèn chớp', 'Bầy cánh cụt đi ngang qua sát chân bạn.'),
             ('Nghe kiểm lâm kể chuyện', 'Bạn biết thêm cách giữ bãi biển sạch cho chim.'))),
        _ev('au_cafe', '☕', 'Ngày hội cà phê', 'Phố cà phê mở hội, từng quán pha món riêng.',
            (('Thử ly flat white', 'Ly cà phê ngon tới mức bạn chụp gửi Cô Ba.'),
             ('Mời mọi người thử cà phê sữa đá', 'Hàng dài người xếp hàng xin “Vietnamese coffee”.')))),
       (_job('Phụ quầy cà phê sáng sớm.', 'Khách gọi món mà bạn nghe chưa rõ.',
             ('Đoán đại', 'Hỏi lại cho chắc rồi mới làm', 'Làm món mình quen'), 1, 'Hỏi lại một câu đỡ hơn làm sai cả ly.'),
        _job('Dọn phòng ở khách sạn nhỏ.', 'Thấy ví khách để quên dưới gối.',
             ('Báo lễ tân, ghi sổ đồ thất lạc', 'Để nguyên, không nói', 'Cầm về phòng mình'), 0, 'Đồ thất lạc phải báo và ghi sổ ngay.'),
        _job('Phục vụ nhà hàng ven biển.', 'Ca đông khách, cả nhóm đều mệt.',
             ('Bắt làm liền tới cuối', 'Chia ca nghỉ ngắn luân phiên', 'Đóng cửa sớm'), 1, 'Nghỉ ngắn luân phiên: quán vẫn chạy, người vẫn khỏe.')),
       ('Vì sao bạn chọn du học Úc?', ('Để xem kangaroo đấm bốc', 'Không biết, ai đi thì đi', 'Để học quản lý nhà hàng – khách sạn'), 2),
       '🛬 Về tới phố Mây, bạn chào cả hẻm: “G’day!”, ai cũng cười.'),
    _t('dh_trung_quoc', '🇨🇳', 'Trung Quốc', 'Thượng Hải', 'Học viện Trà Xanh Thượng Hải', (('dh_cn_ngu', 'dh_cn_vh', 'dh_cn_tm'),),
       ('customs', 'grocery', 'clothing', 'delivery'), 380, 35,
       ('🧳 Chú Tư dặn: “Qua đó nhớ học cách pha trà cho chuẩn nghe con.”', '🛫 Chuyến bay ngắn, chưa ăn xong hộp cơm đã hạ cánh.',
        '🛬 Thượng Hải đông vui, đèn sáng rực hai bờ sông.', '🏠 Ký túc xá có ấm trà chung, bạn cùng phòng chào: “你好!”'),
       (_ev('cn_trungthu', '🥮', 'Tết Trung thu', 'Lớp làm bánh trung thu và ngắm trăng trên sân thượng.',
            (('Tự nặn bánh nhân đậu đỏ', 'Bánh hơi méo mà thơm phức, cả phòng tranh nhau ăn.'),
             ('Kể chuyện chị Hằng cho bạn nước ngoài', 'Mọi người nghe say sưa, hỏi thêm về Trung thu Việt.'))),
        _ev('cn_tra', '🍵', 'Lớp thưởng trà', 'Thầy dạy cách pha trà và mời trà người lớn.',
            (('Rót trà mời thầy trước', 'Thầy gõ nhẹ hai ngón tay lên bàn thay lời cảm ơn.'),
             ('Hỏi tên từng loại trà', 'Bạn ghi được cả trang sổ, mang về pha cho Bà Tám.'))),
        _ev('cn_tau', '🚄', 'Đi tàu cao tốc', 'Cuối tuần cả lớp đi tàu cao tốc tham quan thành phố bên cạnh.',
            (('Ngắm cảnh qua cửa sổ', 'Ruộng đồng lướt qua vèo vèo, bạn quay một đoạn phim dài.'),
             ('Tập nói tiếng Trung với cô bán vé', 'Cô khen phát âm của bạn “很好!” (rất tốt!).')))),
       (_job('Phụ bán ở tiệm trà sữa gần trường.', 'Khách hỏi “多少钱?” (bao nhiêu tiền?).',
             ('Đưa thực đơn có giá và nói giá', 'Lắc đầu không hiểu', 'Đưa thêm ống hút'), 0, '“多少钱” là hỏi giá: nói giá rõ ràng.'),
        _job('Làm thêm ở kho hàng xuất nhập khẩu.', 'Lô hàng sắp gửi đi, thùng ghi thiếu mã hàng.',
             ('Gửi luôn cho kịp', 'Ghi bổ sung mã, đối chiếu phiếu rồi mới gửi', 'Bỏ thùng đó lại'), 1, 'Kiểm và ghi đủ thông tin trước khi gửi hàng.'),
        _job('Phụ quán sủi cảo.', 'Khách thanh toán bằng điện thoại.',
             ('Đưa mã QR của quán cho khách quét', 'Bảo khách chỉ được trả tiền mặt', 'Lấy điện thoại khách tự bấm'), 0, 'Thanh toán bằng mã QR rất phổ biến ở đó.')),
       ('Vì sao bạn chọn du học Trung Quốc?', ('Để ăn lẩu mỗi ngày', 'Để học tiếng Trung và nghề buôn bán, xuất nhập khẩu', 'Đi theo bạn thân'), 1),
       '🛬 Về tới phố Mây, bạn pha một ấm trà mời cả hẻm, kể chuyện Thượng Hải tới khuya.'),
)

# ✈️ The papers of an application: tick the right ones (any mistake costs nothing, the page says what is off).
DOCS = (
    ('passport', '🛂 Hộ chiếu còn hạn', True),
    ('letter', '✉️ Thư mời nhập học', True),
    ('photo', '🖼️ Ảnh thẻ nền trắng', True),
    ('money', '🏦 Giấy xác nhận tài chính', True),
    ('school', '📜 Học bạ / bằng tốt nghiệp', True),
    ('game', '🎮 Thẻ thành viên tiệm game', False),
    ('cat', '🐱 Ảnh mèo cưng', False),
    ('slippers', '🩴 Đôi dép tổ ong', False),
)
