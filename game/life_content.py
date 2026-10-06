"""Chuyện đời thường & tình làng nghĩa xóm: authored content only (rules in game/life.py).

Hard days (bị ăn hiếp chỗ làm, phụ huynh làm khó, khách chửi, bị lừa, thất tình,
chuyện xui, bị đặt điều), how the neighbours respond (COMFORT, góp tiền, quà),
ways to blow off steam (COPE), neighbours in trouble you can help (ASK), small
joys, and the low-spirit events (impulse buys, a sick day).

Text tokens, filled from the journey gender and the day:
  {anh}/{Anh}  how a younger person / a customer calls you (anh · chị · bạn)
  {ay}/{Ay}    your (ex-)partner (cô ấy · anh ấy · người ấy)
  {place}      the workplace of the day that just closed
  {mate}       a workmate there (WORK)
  {gossip}     the neighbour spreading the rumour (GOSSIPS)
A text may also be dict(male=…, female=…, none=…). Amounts never appear in the
text: the card shows the real numbers from the state (losses are capped by the wallet).
"""
from __future__ import annotations

from .incident_content import ALL, EMPLOYEE, RETAIL

EMPLOYED = ('pharmacy', 'customer_care', 'teacher', 'tour_guide', 'repair', 'delivery', 'pet_care', 'salon',
            'corp_accounting', 'tax_payroll', 'group_accounting', 'garbage', 'homemaker', 'naucom', 'babysitter', 'library', 'pilot', 'flight_attendant', 'oil',
            'hr_admin', 'secretary', 'it_helpdesk', 'giupviec', 'railway', 'nurse', 'lighthouse', 'rescue')
OFFICE = ('accounting', 'customer_care', 'corp_accounting', 'tax_payroll', 'group_accounting', 'hr_admin', 'secretary', 'it_helpdesk')
FACING = RETAIL + ('homestay', 'delivery', 'tour_guide', 'customer_care', 'fruit', 'drain', 'ice_cream', 'nail', 'pho', 'com', 'photobooth', 'giupviec', 'library')
CALLING = ('pagoda',)      # a monk: no boss, no shop, no rent; the pagoda is not a place for a karaoke night
OWNERS = tuple(c for c in ALL if c not in EMPLOYED + CALLING)
STOCKED = RETAIL + ('farm',)

CATS = {
    'an_hiep': ('😣', 'Bị ăn hiếp chỗ làm'),
    'phu_huynh': ('📱', 'Phụ huynh làm khó'),
    'khach': ('😤', 'Khách làm khó'),
    'lua': ('🎣', 'Bị lừa'),
    'that_tinh': ('💔', 'Thất tình'),
    'xui': ('🌧️', 'Chuyện xui'),
    'dat_dieu': ('🗣️', 'Bị đặt điều'),
    'xom': ('🏮', 'Hàng xóm gặp chuyện'),
    'vui': ('🌼', 'Chuyện vui nho nhỏ'),
    'buon': ('🛍️', 'Buồn quá tiêu tiền'),
    'om': ('🤒', 'Mệt quá ốm một hôm'),
    'ru': ('🍻', 'Hàng xóm rủ đi chơi'),
    'xa': ('🎈', 'Xả stress'),
    'ktx': ('🛏️', 'Chuyện phòng ký túc xá'),
}

TOKENS = {
    'anh': dict(male='anh', female='chị', none='bạn'),
    'Anh': dict(male='Anh', female='Chị', none='Bạn'),
    'ay': dict(male='cô ấy', female='anh ấy', none='người ấy'),
    'Ay': dict(male='Cô ấy', female='Anh ấy', none='Người ấy'),
}

# Neighbours: the journey CAST (game/journey.py) plus the street's "camera chạy bằng cơm".
GOSSIPS = {
    'co_hai_loa': dict(name='Cô Hai Loa', emoji='🗣️', role='Đầu hẻm, chuyện gì cũng biết'),
    'thim_bay': dict(name='Thím Bảy', emoji='👀', role='Ngồi hóng mát đầu ngõ cả ngày'),
    'chi_tu_zalo': dict(name='Chị Tư Zalo', emoji='📲', role='Admin nhóm Zalo khu phố'),
}
FRIENDS = dict(name='Nhóm bạn thân', emoji='👯', role='Bạn từ hồi mới lên phố')

# A friendly workmate per workplace (for "cả nhóm rủ đi karaoke").
WORK = {
    'milk_tea': ('Linh với mấy bạn khách quen', '🎒'),
    'grocery': ('Cô Ba với tụi nhỏ phụ quán', '👩‍🦳'),
    'delivery': ('Mấy anh em shipper cùng tuyến', '🛵'),
    'cafe_bakery': ('Chú Lâm với ca sáng', '👴'),
    'florist': ('Chị Hoa ở tiệm bên', '💐'),
    'mother_baby': ('Nhi với Bình ở tiệm', '🧸'),
    'restaurant': ('Minh Béo với bếp mì', '🧑‍🍳'),
    'pet_care': ('Chị Mây nhóm cứu hộ', '🐶'),
    'salon': ('Mấy thợ trong salon', '💇'),
    'repair': ('Chú Tư với thằng Cu', '👨‍🔧'),
    'farm': ('Chú Tám với HTX rau', '👨‍🌾'),
    'homestay': ('Chị lễ tân với anh bảo vệ', '🛎️'),
    'customer_care': ('Cả tổ trực tổng đài', '🎧'),
    'pharmacy': ('Ngân với Khoa ở quầy', '💊'),
    'tour_guide': ('Anh tài xế với chị hướng dẫn cùng đoàn', '🚌'),
    'teacher': ('Cô Hiền lớp bên', '👩‍🏫'),
    'accounting': ('Chị Vân với mấy bạn kế toán', '📒'),
    'corp_accounting': ('Phòng kế toán Mây Tre Xanh', '🧮'),
    'tax_payroll': ('Nhóm tính lương Minh Bạch', '🧾'),
    'group_accounting': ('Team hợp nhất Sông Hồng', '🏢'),
    'hr_admin': ('Chị Huyền với phòng nhân sự Cánh Diều', '🗂️'),
    'secretary': ('Chị Khuê với Nhi ở quầy lễ tân', '📅'),
    'it_helpdesk': ('Anh Long với tổ IT Cánh Diều', '🖥️'),
    'clothing': ('Chị Vy với Mai ở tiệm áo', '🧵'),
    'tra_da': ('Chú Tường với ông Khang ở quán trà', '🍵'),
    'pet_shop': ('Nhã với nhóm cứu hộ Chân Nhỏ', '🐾'),
    'fruit': ('Dì Tư với mấy sạp bên cạnh', '🍊'),
    'garbage': ('Chị Hạnh với tổ thu gom', '🛒'),
    'drain': ('Chú Hai với tổ thợ', '🧰'),
    'homemaker': ('Chị Thảo với bà Lành', '🏠'),
    'ice_cream': ('Cô Hiền với chú bảo vệ trường', '🍨'),
    'com': ('Dì Bảy với bạn hàng ngoài chợ', '🍚'),
    'nail': ('Chị Diệp với mấy khách ruột', '💅'),
    'pagoda': ('Thầy trụ trì với bà Nhạn', '🛕'),
    'pho': ('Bác Lâm với mấy khách quen', '🍜'),
    'photobooth': ('Chị Lam với hội bạn 11A1', '📸'),
    'giupviec': ('Cô Mai với tổ Nhà Thơm', '🧹'),
    'naucom': ('Cô Hạnh với mấy nhà quen', '🍲'),
    'babysitter': ('Cô Tâm với bé Bin', '👶'),
    'library': ('Cô Nguyệt với ông Thạc', '📚'),
    'pilot': ('Chị Vân với tổ bay Cánh Cò', '🧑‍✈️'),
    'flight_attendant': ('Chị Thu với các bạn tiếp viên', '💁'),
    'oil': ('Chú Toàn với ca trực giàn Hải Âu', '🛢️'),
    'railway': ('Chú Sáu với ca gác Bến Mây', '🚦'),
    'nurse': ('Chị Hoa với các bạn khoa Nội', '🏥'),
    'lighthouse': ('Chú Bảy với trạm đèn Hòn Gió', '🗼'),
    'rescue': ('Chị Thảo với ca trực tổng đài', '📞'),
}


def C(cid: str, label: str, text: str, spirit: int = 0, money: int = 0, bond: int = 0, default: bool = False,
      **kw) -> dict:
    """A choice. money < 0 is a cost (needs the wallet), money > 0 comes in. bond: warmth with the card's neighbour."""
    return dict(id=cid, label=label, text=text, spirit=spirit, money=money, bond=bond, default=default, **kw)


def H(hid: str, cat: str, emoji: str, title: str, lines: list, choices: list, hit: int = -15, loss: int = 0,
      careers=None, mild: bool = False, fact: str | None = None) -> dict:
    """A hard day. `hit` lands on the spirit when it happens, `loss` leaves the wallet (capped at what is there)."""
    return dict(id=hid, cat=cat, emoji=emoji, title=title, lines=list(lines), choices=list(choices), hit=hit,
                loss=loss, careers=tuple(careers) if careers else None, mild=mild, fact=fact)


VENT = C('vent', 'Ra quán cóc ngồi một mình cho nguôi', 'Ly trà đá, gió chiều. Lòng nhẹ đi một chút.', spirit=5, money=-8)

HARD = [
    # ================================================================ bị ăn hiếp chỗ làm
    H('ah_blame', 'an_hiep', '😠', 'Sếp đổ lỗi oan', [
        'Báo cáo sai số liệu, sếp mắng thẳng mặt giữa phòng.',
        'Lỗi của người khác, nhưng không ai lên tiếng.',
        'Cả buổi chiều bạn nghẹn không nói nên lời.'], [
        C('proof', 'Nhắn sếp riêng, gửi kèm bằng chứng', 'Sếp đọc xong im lặng, cuối ngày nhắn: “Hôm nay tôi hơi nóng.” Vậy cũng đủ.', spirit=8, default=True),
        C('swallow', 'Nuốt cục tức, làm tiếp', 'Xong việc rồi mà ngực vẫn nặng trĩu.', spirit=-4),
        VENT], careers=EMPLOYED + ('accounting',), hit=-16),
    H('ah_dump', 'an_hiep', '📚', 'Tiền bối dồn việc', [
        '5 giờ chiều, tiền bối đặt chồng hồ sơ lên bàn bạn.',
        '“Em làm giúp chị nhé, mai chị nghỉ.”',
        'Tuần này là lần thứ ba rồi.'], [
        C('no', 'Từ chối khéo: “Em đang kẹt việc của em”', 'Chị ấy hơi phật ý, nhưng từ mai biết bạn cũng có giới hạn.', spirit=6, default=True),
        C('do', 'Ôm hết, về trễ', 'Về tới nhà thì hẻm đã tắt đèn. Mệt rã rời.', spirit=-6),
        C('split', 'Làm phần gấp, phần còn lại ghi chú trả lại', 'Công bằng, rõ ràng. Không ai nói được gì.', spirit=3)], careers=EMPLOYED + ('accounting',)),
    H('ah_chat', 'an_hiep', '💬', 'Bị gạt khỏi nhóm chat', [
        'Cả phòng đi ăn trưa, không ai rủ bạn.',
        'Hóa ra có nhóm chat riêng, thiếu mỗi bạn.',
        'Ảnh check-in quán lẩu hiện lên story.'], [
        C('ask', 'Hỏi thẳng một bạn thân trong phòng', '“Tưởng bạn không thích ồn ào.” Hóa ra hiểu lầm. Mai bạn được rủ.', spirit=7, default=True),
        C('alone', 'Kệ, trưa ăn cơm hộp một mình', 'Hộp cơm nguội, điện thoại im re.', spirit=-5),
        C('treat', 'Mai mua trà sữa cả phòng làm quen', 'Cả phòng cảm ơn rối rít, có người rủ bạn vào nhóm luôn.', spirit=8, money=-20)], careers=EMPLOYED + ('accounting',), hit=-12, mild=True),
    H('ah_dock', 'an_hiep', '💸', 'Bị trừ lương vô lý', [
        'Phiếu lương có dòng “trừ đi muộn”.',
        'Hôm đó bạn đến sớm, có cả tin nhắn chấm công.',
        'Kế toán bảo: “Sếp duyệt rồi, em chịu khó.”'], [
        C('hr', 'Gửi ảnh chấm công, xin xem lại', 'Hai hôm sau có tin: “Xin lỗi, bảng nhập nhầm dòng”. Được trả lại.', spirit=6, money=12, default=True),
        C('let', 'Thôi bỏ qua cho yên chuyện', 'Mất tiền, mất luôn hứng đi làm.', spirit=-5)], careers=EMPLOYED, hit=-14, loss=12),
    H('ah_credit', 'an_hiep', '🏆', 'Bị giành công', [
        'Ý tưởng của bạn, trong cuộc họp thành của người khác.',
        'Sếp khen người ta nức nở.',
        'Bạn ngồi đó, cười không nổi.'], [
        C('mail', 'Gửi mail tóm tắt kèm bản nháp cũ', 'Sếp nhắn riêng: “Lần sau em trình bày nhé.”', spirit=7, default=True),
        C('quiet', 'Im lặng cho qua', 'Tối về cứ nghĩ mãi.', spirit=-4),
        VENT], careers=EMPLOYED + ('accounting',)),
    H('ah_yell', 'an_hiep', '📞', 'Bị quát qua điện thoại', [
        'Quản lý gọi lúc 9 giờ tối.',
        'Giọng gắt: “Làm ăn kiểu gì vậy?”',
        'Chuyện nhỏ xíu, mai sửa là xong.'], [
        C('calm', 'Bình tĩnh: “Mai 8 giờ em sửa xong ạ”', 'Đầu dây bên kia dịu xuống. Bạn tắt máy, thở ra một hơi dài.', spirit=4, default=True),
        C('cry', 'Tắt máy, khóc một trận', 'Khóc xong thấy nhẹ hơn, dù mắt sưng.', spirit=2),
        C('mute', 'Tắt thông báo sau giờ làm', 'Tối nay yên tĩnh lạ.', spirit=5)], careers=EMPLOYED, hit=-13, mild=True),
    H('ah_shift', 'an_hiep', '🗓️', 'Bị xếp ca xấu cả tuần', [
        'Lịch mới: bạn trực toàn ca tối, cả cuối tuần.',
        'Người mới vào thì được ca đẹp.',
        'Hỏi thì bảo: “Em chịu khó, em trẻ mà.”'], [
        C('swap', 'Nói chuyện với quản lý, xin chia đều', 'Được đổi hai ca. Chưa công bằng hẳn nhưng đỡ.', spirit=5, default=True),
        C('take', 'Nhận hết, không nói gì', 'Tuần này coi như không có tối nào cho mình.', spirit=-5)], careers=EMPLOYED),
    H('ah_teacher', 'an_hiep', '🗂️', 'Tổ trưởng giao thêm việc không tên', [
        'Tổ trưởng giao thêm: sổ sách, trang trí lớp, dự giờ.',
        '“Giáo viên trẻ phải xung phong chứ em.”',
        'Giáo án tuần sau vẫn chưa soạn.'], [
        C('list', 'Ghi rõ việc nào kịp, việc nào xin lùi', 'Tổ trưởng gật gù, bớt cho bạn hai việc.', spirit=6, default=True),
        C('night', 'Thức tới 1 giờ làm cho xong', 'Xong hết. Sáng ra mắt thâm quầng.', spirit=-6)], careers=('teacher',)),
    H('ah_rent', 'an_hiep', '🏠', 'Chủ mặt bằng dọa tăng giá', [
        'Chủ mặt bằng ghé tiệm, nói lớn trước mặt khách.',
        '“Tháng sau tăng giá, không chịu thì dọn.”',
        'Hợp đồng còn nửa năm.'], [
        C('contract', 'Đưa hợp đồng ra, nói chuyện nhỏ nhẹ', 'Ông ấy đọc lại, lầm bầm “để tính sau”.', spirit=6, default=True),
        C('worry', 'Cả đêm tính toán lo lắng', 'Máy tính bấm tới khuya, càng bấm càng rối.', spirit=-5)], careers=OWNERS, hit=-13),
    # ================================================================ phụ huynh làm khó
    H('ph_group', 'phu_huynh', '📱', 'Phụ huynh làm ầm trong nhóm lớp', [
        'Tin nhắn dài 30 dòng trong nhóm Zalo lớp.',
        '“Cô dạy kiểu gì mà con tôi bị điểm 6?”',
        'Mấy chục phụ huynh đã xem.'], [
        C('call', 'Gọi riêng, mời lên trường nói chuyện', 'Gặp nhau rồi mới vỡ lẽ: bé làm bài vội. Phụ huynh xin lỗi nhỏ.', spirit=7, default=True),
        C('reply', 'Trả lời công khai trong nhóm', 'Nhóm càng lúc càng ồn. Bạn mệt lả.', spirit=-4),
        C('boss', 'Nhờ ban giám hiệu hỗ trợ', 'Cô hiệu phó nhắn nhóm một câu. Mọi thứ lắng xuống.', spirit=4)], careers=('teacher',), hit=-17),
    H('ph_report', 'phu_huynh', '📝', 'Bị dọa “lên Sở”', [
        'Phụ huynh đứng chắn cửa lớp.',
        '“Tôi sẽ viết đơn lên Sở!”',
        'Chỉ vì bé bị nhắc không làm bài tập.'], [
        C('calm', 'Mời vào phòng, pha trà, nghe cho hết', 'Nói xong, chị ấy dịu hẳn: “Tôi cũng lo cho con thôi cô.”', spirit=6, default=True),
        C('record', 'Ghi lại, báo ban giám hiệu', 'Trường nắm chuyện. Bạn thấy có người đứng sau mình.', spirit=4)], careers=('teacher',), hit=-16),
    H('ph_marks', 'phu_huynh', '💯', 'Đòi nâng điểm', [
        'Phụ huynh nhắn: “Cô nâng lên 8 giúp, có quà cảm ơn.”',
        'Rồi thêm: “Không thì đừng trách.”',
        'Bạn đọc đi đọc lại, run tay.'], [
        C('no', 'Từ chối rõ ràng, giữ tin nhắn', 'Không ai làm gì được bạn. Tối ngủ ngon vì mình làm đúng.', spirit=8, default=True),
        C('extra', 'Đề nghị kèm thêm cho bé, không lấy tiền', 'Phụ huynh ngượng, cảm ơn. Bé tiến bộ thật.', spirit=6)], careers=('teacher',), hit=-12, mild=True),
    H('ph_film', 'phu_huynh', '🎥', 'Bị quay clip đăng mạng', [
        'Một phụ huynh quay lúc bạn nhắc học sinh.',
        'Clip cắt đúng đoạn bạn nói to.',
        'Tối đó clip có mấy trăm lượt xem.'], [
        C('full', 'Nhờ trường đăng đủ ngữ cảnh', 'Clip đầy đủ lên, bình luận quay xe bênh cô.', spirit=8, default=True),
        C('read', 'Ngồi đọc hết bình luận', 'Càng đọc càng đau. Tắt máy lúc 2 giờ sáng.', spirit=-7)], careers=('teacher',), hit=-20),
    H('ph_midnight', 'phu_huynh', '🌙', 'Tin nhắn lúc nửa đêm', [
        '23 giờ 40: “Cô ơi mai con tôi mặc áo gì?”',
        '23 giờ 52: “Cô đọc mà không trả lời à?”',
        '00 giờ 10: gọi thẳng.'], [
        C('rule', 'Sáng mai nhắn nhóm giờ liên lạc', 'Cả lớp đồng ý. Tối nay đỡ hơn nhiều.', spirit=6, default=True),
        C('answer', 'Nghe máy cho xong', 'Hết buồn ngủ luôn.', spirit=-3)], careers=('teacher',), hit=-10, mild=True),
    H('ph_gift', 'phu_huynh', '🎁', 'Bị nói xấu vì không nhận quà', [
        'Bạn trả lại phong bì của một phụ huynh.',
        'Hôm sau nhóm phụ huynh xì xào: “Cô chê ít”.',
        'Cô hiệu trưởng gọi hỏi.'], [
        C('explain', 'Kể thật với cô hiệu trưởng', 'Cô vỗ vai: “Em làm đúng.”', spirit=7, default=True),
        C('silent', 'Không giải thích gì', 'Tin đồn tự tắt, nhưng mất mấy hôm.', spirit=-3)], careers=('teacher',), hit=-14),
    H('ph_compare', 'phu_huynh', '📊', 'Bị so với cô lớp bên', [
        '“Cô lớp bên dạy hay hơn, sao cô không học hỏi?”',
        'Phụ huynh nói ngay trước mặt học sinh.',
        'Bé con của chị ấy cúi gằm mặt.'], [
        C('meet', 'Hẹn gặp riêng sau giờ học', 'Nói chuyện tử tế thì ai cũng dịu lại.', spirit=5, default=True),
        C('ask', 'Rủ cô lớp bên trao đổi giáo án', 'Cô Hiền vui vẻ chia sẻ. Hai cô thân nhau hơn.', spirit=7)], careers=('teacher',), hit=-11, mild=True),
    # ================================================================ khách / đối tác làm khó
    H('kh_scream', 'khach', '😤', 'Khách quát tháo giữa quầy', [
        'Khách đập tay xuống quầy.',
        '“Làm ăn kiểu gì vậy hả?”',
        'Cả hàng người quay lại nhìn bạn.'], [
        C('calm', 'Hạ giọng, xin lỗi, xử lý nhanh', 'Khách nguôi dần, lúc về còn gật đầu.', spirit=4, default=True),
        C('back', 'Nói lại cho ra lẽ', 'Hai bên to tiếng. Ai cũng mệt.', spirit=-5),
        C('break', 'Nhờ người khác trực, ra sau hít thở', 'Năm phút ngoài hiên, tim đập chậm lại.', spirit=3)], careers=FACING, hit=-14, mild=True),
    H('kh_review', 'khach', '⭐', 'Đánh giá 1 sao bịa đặt', [
        'Một tài khoản lạ chấm 1 sao.',
        '“Nhân viên thái độ, đồ bẩn.” Hôm đó họ không hề tới.',
        'Đã có người thả “haha”.'], [
        C('reply', 'Trả lời lịch sự, kèm giờ mở cửa hôm đó', 'Khách quen vào bênh. Đánh giá giả bị gỡ.', spirit=7, default=True),
        C('stew', 'Đọc đi đọc lại mà tức', 'Mất ngủ vì một người không quen.', spirit=-5)], careers=FACING, hit=-12, mild=True),
    H('kh_nopay', 'khach', '🧾', 'Khách quỵt tiền còn chửi', [
        'Khách ăn xong, bảo “dở vậy mà cũng tính tiền”.',
        'Rồi bỏ đi, không trả.',
        'Còn ngoái lại chửi thêm.'], [
        C('let', 'Cho qua, coi như xui', 'Tiếc tiền, nhưng giữ được bình yên.', spirit=1, default=True),
        C('post', 'Kể lên nhóm chủ quán khu phố', 'Mọi người nhắn cảm thông, dặn nhau để ý.', spirit=4)], careers=RETAIL + ('homestay', 'tra_da'), hit=-14, loss=15),
    H('kh_parcel', 'khach', '📦', 'Khách bom hàng, chửi shipper', [
        'Giao tới nơi, khách bảo “không đặt”.',
        'Rồi mắng: “Giao chậm như rùa”.',
        'Tiền xăng đi đứt.'], [
        C('report', 'Báo tổng đài, chụp ảnh làm chứng', 'Tổng đài ghi nhận, khách bị đánh dấu.', spirit=4, default=True),
        C('sit', 'Ghé vỉa hè ngồi uống chai nước', 'Nắng gắt. Nhưng ngồi chút cũng đỡ.', spirit=2)], careers=('delivery',), hit=-13, loss=8, mild=True),
    H('kh_call', 'khach', '🎧', 'Cuộc gọi 40 phút toàn chửi', [
        'Khách gọi tới, chưa nói gì đã chửi.',
        'Bốn mươi phút. Bạn không được cúp máy.',
        'Cúp xong, tay vẫn còn run.'], [
        C('tea', 'Xin trưởng ca nghỉ 10 phút', 'Trưởng ca gật đầu, còn đưa ly trà gừng.', spirit=6, default=True),
        C('next', 'Nhận cuộc gọi kế tiếp luôn', 'Giọng bạn hơi run suốt buổi chiều.', spirit=-4)], careers=('customer_care',), hit=-15),
    H('kh_tour', 'khach', '🚌', 'Khách tour làm mình làm mẩy', [
        'Khách đòi đổi phòng, đổi món, đổi cả lịch trình.',
        'Không vừa ý là dọa “đánh giá cho biết tay”.',
        'Cả đoàn phải chờ.'], [
        C('firm', 'Nhẹ nhàng nhưng giữ đúng lịch', 'Cả đoàn vỗ tay khi xe lăn bánh đúng giờ.', spirit=6, default=True),
        C('bend', 'Chiều hết cho yên', 'Khách vẫn chê. Bạn thì kiệt sức.', spirit=-5)], careers=('tour_guide', 'homestay'), hit=-13),
    H('kh_pet', 'khach', '🐾', 'Chủ thú cưng mắng xối xả', [
        'Bé cún về nhà hắt hơi hai cái.',
        'Chủ nó gọi tới mắng như tát nước.',
        'Hồ sơ ghi rõ bé bị từ trước.'], [
        C('file', 'Gửi lại phiếu khám lúc nhận', 'Chủ nó im một lúc, rồi nhắn “xin lỗi em”.', spirit=6, default=True),
        C('sorry', 'Xin lỗi cho qua', 'Chuyện qua, nhưng bạn thấy ấm ức.', spirit=-3)], careers=('pet_care', 'salon'), hit=-12, mild=True),
    H('kh_supplier', 'khach', '🚚', 'Đối tác nói nặng lời', [
        'Nhà cung cấp giao trễ ba ngày.',
        'Hỏi thì họ gắt: “Không mua thì thôi!”',
        'Khách đang chờ hàng.'], [
        C('other', 'Tìm nhà cung cấp khác', 'Chỗ mới lịch sự hơn hẳn. Nhẹ cả người.', spirit=6, default=True),
        C('beg', 'Nhún nhường năn nỉ', 'Hàng về. Nhưng lòng thì không vui.', spirit=-2)], careers=OWNERS, hit=-11, mild=True),
    H('kh_viral', 'khach', '📣', 'Bị bóc phốt trên mạng', [
        'Khách đăng bài “bóc phốt” tiệm bạn.',
        'Ảnh chụp mờ, chuyện kể một nửa.',
        'Bài có mấy trăm lượt chia sẻ.'], [
        C('truth', 'Đăng giải thích ngắn, kèm hóa đơn', 'Khách quen vào làm chứng. Bài phốt tự chìm.', spirit=7, default=True),
        C('hide', 'Đóng trang mấy hôm', 'Yên tĩnh. Nhưng khách cũng thưa đi.', spirit=-4)], careers=FACING, hit=-18),
    # ================================================================ bị lừa (đã lỡ rồi)
    H('lu_ship', 'lua', '📦', 'Lừa phí giao hàng', [
        '“Shipper” gọi: có đơn thu hộ, chuyển trước phí ship.',
        'Bạn đang bận nên chuyển luôn.',
        'Đơn không bao giờ tới. Số kia chặn bạn.'], [
        C('report', 'Báo ngân hàng và công an phường', 'Cán bộ ghi nhận, dặn cả phường cảnh giác số này.', spirit=5, default=True),
        C('tell', 'Kể cho cả hẻm để ai cũng biết', 'Bà Tám bảo: “Hôm qua nó gọi bà y chang!”', spirit=4, bond=2),
        C('blame', 'Tự trách mình suốt tối', 'Càng nghĩ càng giận mình.', spirit=-5)], hit=-15, loss=30, mild=True),
    H('lu_bank', 'lua', '🏦', 'Giả nhân viên ngân hàng', [
        '“Ngân hàng” gọi: tài khoản bị khóa, đọc mã OTP để mở.',
        'Giọng rất chuyên nghiệp.',
        'Đọc xong mã, tài khoản bị rút tiền.'], [
        C('lock', 'Gọi tổng đài thật, khóa thẻ ngay', 'Chặn kịp một phần. Phần đã mất thì chịu.', spirit=4, default=True),
        C('blame', 'Ngồi thẫn thờ', 'Ngồi mãi tới tối.', spirit=-5)], hit=-18, loss=45),
    H('lu_prize', 'lua', '🎁', '“Trúng thưởng” xe máy', [
        'Tin nhắn: trúng xe máy, nộp phí trước.',
        'Bạn nộp. Họ đòi thêm “thuế”.',
        'Tới lúc hiểu ra thì đã muộn.'], [
        C('report', 'Chụp màn hình, trình báo', 'Công an phường nói nhóm này lừa nhiều người lắm rồi.', spirit=4, default=True),
        C('laugh', 'Tự cười mình một trận', 'Cười xong thấy đỡ. Coi như học phí.', spirit=3)], hit=-14, loss=25, mild=True),
    H('lu_fb', 'lua', '👤', 'Facebook bạn thân bị hack', [
        'Bạn thân nhắn: “Cho mượn gấp, tối trả.”',
        'Bạn chuyển liền, vì là bạn thân mà.',
        'Tối đó nó đăng: “Mình bị hack nick!”'], [
        C('call', 'Gọi cho bạn, cùng báo Facebook', 'Hai đứa ngồi an ủi nhau. Bạn thân còn áy náy hơn cả bạn.', spirit=5, default=True),
        C('warn', 'Đăng cảnh báo cho mọi người', 'Mấy người suýt chuyển cũng dừng kịp.', spirit=6, bond=1)], hit=-16, loss=35),
    H('lu_job', 'lua', '💼', 'Việc làm thêm “nhẹ lương cao”', [
        'Việc “like dạo nhận tiền”. Làm vài lần được trả thật.',
        'Rồi họ bảo nạp tiền để nhận “nhiệm vụ lớn”.',
        'Nạp xong, nhóm giải tán.'], [
        C('report', 'Trình báo, gửi lại toàn bộ tin nhắn', 'Cán bộ cảm ơn, nói sẽ lần theo tài khoản.', spirit=4, default=True),
        C('hide', 'Xấu hổ, không kể ai', 'Giấu một mình thì càng nặng.', spirit=-6)], hit=-17, loss=40),
    H('lu_rent', 'lua', '🔑', 'Đặt cọc phòng ảo', [
        'Thấy phòng đẹp giá rẻ trên mạng, bạn cọc trước.',
        'Tới nơi: địa chỉ là một bãi đất trống.',
        'Số điện thoại đã khóa.'], [
        C('report', 'Trình báo, cảnh báo nhóm thuê trọ', 'Bài cảnh báo có cả trăm lượt chia sẻ.', spirit=5, default=True),
        C('walk', 'Đi bộ về, lòng nặng trĩu', 'Đường về dài hơn mọi ngày.', spirit=-4)], hit=-16, loss=40),
    H('lu_invest', 'lua', '📈', 'Nhóm “chuyên gia” chứng khoán', [
        '“Chuyên gia” trong nhóm chat hướng dẫn nạp tiền.',
        'Màn hình báo lãi đẹp lắm.',
        'Tới lúc rút thì app biến mất.'], [
        C('report', 'Trình báo, giữ lại bằng chứng', 'Được hướng dẫn tận tình. Tiền thì khó lấy lại.', spirit=4, default=True),
        C('blame', 'Giận mình tham', 'Ngồi thừ trên gác tới khuya.', spirit=-5)], hit=-18, loss=50),
    H('lu_charity', 'lua', '🙏', 'Quyên góp giả', [
        'Bài đăng xin giúp bé bệnh nặng, ảnh rất thương.',
        'Bạn chuyển khoản ngay.',
        'Hôm sau báo đưa tin: ảnh bị lấy cắp, tài khoản lừa đảo.'], [
        C('keep', 'Vẫn giữ lòng tốt, lần sau kiểm kỹ hơn', 'Mất tiền, nhưng không mất lòng tốt.', spirit=5, default=True),
        C('bitter', 'Từ nay không tin ai nữa', 'Nghĩ vậy lòng lạnh đi một chút.', spirit=-4)], hit=-13, loss=20, mild=True),
    # ================================================================ thất tình
    H('tt_break', 'that_tinh', '💔', 'Bị chia tay', [
        '{Ay} nhắn: “Mình dừng lại nhé.”',
        'Không giải thích gì thêm.',
        'Ba năm, kết thúc trong một tin nhắn.'], [
        C('cry', 'Khóc cho đã rồi ngủ', 'Gối ướt một mảng. Sáng ra thấy trống, nhưng thở được.', spirit=4, default=True),
        C('text', 'Nhắn lại hỏi cho ra lẽ', '{Ay} xem rồi không trả lời. Đau thêm chút.', spirit=-5),
        C('mum', 'Gọi về cho mẹ', 'Mẹ không hỏi nhiều, chỉ bảo: “Về nhà ăn cơm với mẹ.”', spirit=7)], hit=-24),
    H('tt_ghost', 'that_tinh', '👻', 'Bị “ghost”', [
        'Nhắn tin đang vui thì {ay} im bặt.',
        'Ba ngày không trả lời.',
        'Story vẫn đăng đều.'], [
        C('delete', 'Xóa đoạn chat, thôi không chờ', 'Nhẹ hơn tưởng tượng.', spirit=6, default=True),
        C('wait', 'Vẫn ngồi chờ tin nhắn', 'Điện thoại sáng lên, nhưng là tin quảng cáo.', spirit=-5)], hit=-15, mild=True),
    H('tt_engaged', 'that_tinh', '💍', 'Crush đính hôn', [
        'Crush thầm bao lâu vừa khoe nhẫn đính hôn.',
        'Bạn thả tim, rồi úp điện thoại xuống bàn.',
        'Chưa kịp nói gì mà đã hết.'], [
        C('wish', 'Nhắn chúc mừng thật lòng', 'Chúc xong thấy mình lớn hơn một chút.', spirit=6, default=True),
        C('scroll', 'Lướt hết ảnh cưới hỏi', 'Tới tấm thứ hai mươi thì thôi.', spirit=-4)], hit=-17, mild=True),
    H('tt_far', 'that_tinh', '✈️', 'Yêu xa, đành buông', [
        '{Ay} nhận việc ở nước ngoài, ít nhất năm năm.',
        'Hai đứa ngồi ở quán quen lần cuối.',
        'Không ai sai cả.'], [
        C('hug', 'Ôm một cái, chúc {ay} đi bình an', 'Buồn, mà nhẹ. Như mưa tạnh.', spirit=5, default=True),
        C('stay', 'Níu thêm, hứa sẽ chờ', 'Nói xong cả hai đều im.', spirit=-3)], hit=-20),
    H('tt_third', 'that_tinh', '🥀', 'Phát hiện bị “cắm sừng”', [
        'Bạn thấy {ay} đi cùng người khác ở phố đi bộ.',
        'Hai người nắm tay.',
        dict(male='Tối đó {ay} vẫn nhắn “nhớ anh”.', female='Tối đó {ay} vẫn nhắn “nhớ em”.', none='Tối đó {ay} vẫn nhắn “nhớ lắm”.')], [
        C('end', 'Chấm dứt, block hết', 'Đau, nhưng dứt khoát. Bạn tự hào về mình.', spirit=7, default=True),
        C('confront', 'Hẹn gặp nói cho ra lẽ', 'Toàn lời bào chữa. Về càng mệt.', spirit=-4)], hit=-26),
    H('tt_birthday', 'that_tinh', '🎂', '{Ay} quên sinh nhật bạn', [
        'Sinh nhật bạn, {ay} quên.',
        'Tối mới nhắn “sorry, bận quá”.',
        'Hai đứa cãi nhau, rồi chia tay luôn.'], [
        C('cake', 'Tự mua bánh nhỏ, thổi nến một mình', 'Một mình mà vẫn ấm. Tuổi mới, mình thương mình.', spirit=5, money=-10, default=True),
        C('sleep', 'Tắt đèn đi ngủ sớm', 'Ngủ không được, nhưng nằm yên cũng đỡ.', spirit=1)], hit=-18),
    H('tt_blind', 'that_tinh', '☕', 'Buổi mai mối thảm họa', [
        'Cô Lụa giới thiệu người quen, hẹn cà phê.',
        'Người ta hỏi lương, hỏi nhà, rồi chê nghề của bạn.',
        'Về tới hẻm thì cô Lụa đang đứng chờ hỏi han.'], [
        C('laugh', 'Kể cô Lụa nghe, hai cô cháu cười bò', 'Cô Lụa hứa lần sau lựa người tử tế hơn.', spirit=6, bond=2, default=True),
        C('sulk', 'Về phòng đóng cửa', 'Thấy mình bị đánh giá thấp.', spirit=-3)], hit=-11, mild=True),
    # ================================================================ chuyện xui
    H('xu_phone', 'xui', '📵', 'Mất điện thoại trên xe buýt', [
        'Xuống xe buýt, sờ túi: trống trơn.',
        'Ảnh, danh bạ, tin nhắn của mẹ… mất hết.',
        'Mai còn phải đi làm.'], [
        C('lock', 'Mượn máy khóa tài khoản ngay', 'Kịp khóa hết. Mất máy, không mất tiền trong tài khoản.', spirit=4, default=True),
        C('cry', 'Ngồi bệt ở trạm mà khóc', 'Bác bán vé số đưa khăn giấy.', spirit=2)], hit=-18, loss=40, mild=True),
    H('xu_rain', 'xui', '🛵', 'Xe chết máy giữa mưa', [
        'Mưa trắng trời, xe tắt máy giữa đường ngập.',
        'Dắt bộ hai cây số.',
        'Ướt từ đầu tới chân.'], [
        C('fix', 'Ghé tiệm sửa ven đường', 'Anh thợ sửa nhanh, còn cho mượn áo mưa.', spirit=3, default=True),
        C('walk', 'Dắt về nhà, mai tính', 'Về tới gác thì run cầm cập.', spirit=-4)], hit=-13, loss=18, mild=True),
    H('xu_home', 'xui', '🏥', 'Người nhà ốm, cần tiền', [
        'Mẹ gọi: ba nhập viện, mổ gấp.',
        'Giọng mẹ cố tỏ ra bình thường.',
        'Bạn ở xa, chỉ gửi được tiền về.'], [
        C('send', 'Gửi một khoản lớn về nhà', 'Mẹ nhắn: “Ba mổ xong rồi, con yên tâm.” Bạn thở phào.', spirit=8, money=-40, default=False),
        C('some', 'Gửi một ít, hứa gửi thêm', 'Mẹ bảo đủ rồi, đừng lo. Bạn biết mẹ nói vậy thôi.', spirit=4, money=-15, default=True),
        C('call', 'Gọi video hỏi thăm ba', 'Ba cười yếu ớt: “Ba khỏe mà.” Nghe mà thương.', spirit=2)], hit=-16),
    H('xu_flood', 'xui', '🌊', 'Nước ngập vào phòng trọ', [
        'Mưa lớn, nước tràn vào gác dưới.',
        'Đồ đạc ướt sũng, laptop tắt ngúm.',
        'Nửa đêm tát nước một mình.'], [
        C('dry', 'Phơi đồ, mang máy đi sấy', 'Máy sống lại. Đồ thì còn mùi ẩm.', spirit=3, default=True),
        C('sit', 'Ngồi nhìn nước mà nản', 'Đêm dài lê thê.', spirit=-4)], hit=-15, loss=22),
    H('xu_wallet', 'xui', '👛', 'Rơi ví ở chợ', [
        'Đi chợ về, ví không còn trong túi.',
        'Tiền mặt, thẻ xe, căn cước.',
        'Quay lại tìm thì chợ đã tan.'], [
        C('post', 'Đăng lên nhóm khu phố', 'Một cô bán rau nhặt được giấy tờ, nhắn bạn tới lấy.', spirit=5, default=True),
        C('papers', 'Đi làm lại giấy tờ luôn', 'Xếp hàng cả buổi sáng. Mệt mà xong.', spirit=1)], hit=-14, loss=25, mild=True),
    H('xu_sick_pet', 'xui', '🐈', 'Mèo nhà bị ốm', [
        'Mèo nhỏ bỏ ăn hai hôm.',
        'Nằm co ro dưới gầm giường.',
        'Bạn lo tới mất ngủ.'], [
        C('vet', 'Đưa đi thú y', 'Bác sĩ bảo bé chỉ bị cảm. Về nhà bé đòi ăn liền.', spirit=8, money=-25, default=False),
        C('home', 'Tự chăm ở nhà, theo dõi', 'Tới chiều bé chịu ăn chút pate. Hú hồn.', spirit=3, default=True)], hit=-12),
    H('xu_fine', 'xui', '🚦', 'Bị phạt vì lỗi không đáng', [
        'Quên bật xi-nhan khi rẽ.',
        'Biên bản, tiền phạt.',
        'Đúng hôm đang trễ giờ.'], [
        C('ok', 'Nộp phạt, rút kinh nghiệm', 'Từ nay rẽ đâu cũng bật xi-nhan.', spirit=2, default=True),
        C('grumble', 'Cằn nhằn cả ngày', 'Chẳng thay đổi được gì.', spirit=-3)], hit=-10, loss=15, mild=True),
    H('xu_laptop', 'xui', '💻', 'Đổ cà phê vào laptop', [
        'Ly cà phê đổ ụp lên bàn phím.',
        'Màn hình tắt phụt.',
        'Bài làm dở chưa lưu.'], [
        C('repair', 'Mang ra tiệm chú Tư', 'Chú Tư lau từng phím, tính giá rẻ.', spirit=4, bond=2, default=True),
        C('redo', 'Mượn máy làm lại từ đầu', 'Làm lại tới khuya. Nhưng xong.', spirit=-2)], hit=-14, loss=20),
    # ================================================================ bị đặt điều (dựa trên chuyện thật)
    H('dd_late_1', 'dat_dieu', '🌙', '“Đêm nào cũng về khuya…”', [
        'Hôm qua bạn làm tới tối mịt ở {place}.',
        '{gossip} nói với cả dãy: “Đêm nào cũng về khuya, chắc làm ăn gì…”',
        'Câu nói bỏ lửng. Ai nghe cũng hiểu kiểu khác.'], [
        C('ignore', 'Kệ, người ngay không sợ bóng', 'Vài hôm người ta chán, chuyển sang chuyện khác.', spirit=0, default=True),
        C('talk', 'Ghé nói chuyện nhỏ nhẹ với {gossip}', '“Cô nghe người ta nói vậy thôi mà.” Nói xong ai cũng ngượng.', spirit=5),
        C('ba_sau', 'Nhờ Bà Sáu nói giúp một câu', 'Bà Sáu nói trước cả dãy: “Con nó đi làm tới tối, tui biết.”', spirit=7, who='ba_sau', bond=3)],
      hit=-12, fact='late'),
    H('dd_late_2', 'dat_dieu', '🏍️', '“Chạy mấy chỗ một lúc, lạ ghê”', [
        'Mấy hôm nay bạn làm ở vài nơi khác nhau.',
        'Nhóm khu phố có tin: “Sáng chỗ này chiều chỗ kia, không biết làm gì mà lắm tiền.”',
        '{gossip} còn thêm mấy dấu chấm lửng.'], [
        C('post', 'Đăng lên nhóm: “Em làm ở mấy tiệm trong hẻm ạ”', 'Cô Ba vào thả tim: “Đúng rồi, nó phụ tiệm cô.”', spirit=5, default=True),
        C('ignore', 'Không trả lời', 'Tin nhắn trôi dần.', spirit=-1),
        C('coffee', 'Mời {gossip} ly cà phê cho vui vẻ', 'Uống xong, {gossip} quay ra bênh bạn chằm chặp.', spirit=6, money=-10)],
      hit=-11, fact='late'),
    H('dd_money_1', 'dat_dieu', '💰', '“Tiêu hoang thế, chắc làm gì mờ ám”', [
        'Bạn vừa chi một khoản lớn.',
        '{gossip}: “Mới lên phố mà tiêu như nước, chắc làm ăn gì mờ ám.”',
        'Bà bán xôi nhìn bạn khác khác.'], [
        C('talk', 'Nói thẳng mà nhẹ: tiền mồ hôi của mình', '{gossip} ậm ừ, nói trớ sang chuyện thời tiết.', spirit=5, default=True),
        C('ignore', 'Kệ, sống thật là được', 'Người hiểu thì hiểu. Vậy cũng đủ.', spirit=1),
        C('co_lua', 'Nhờ cô Lụa nhắc chung trong tổ', 'Cô Lụa nhắc khéo: “Đừng nói chuyện không biết rõ nghe.”', spirit=6, who='co_lua', bond=3)],
      hit=-12, fact='spend'),
    H('dd_money_2', 'dat_dieu', '🧧', '“Rút tiền liên tục, chắc nợ nần”', [
        'Bạn vừa rút tiền lời về ví.',
        '{gossip} đồn: “Nó rút sạch quỹ, chắc đang nợ ai đó.”',
        'Có người hỏi bạn có cần mượn tiền không.'], [
        C('laugh', 'Cười xòa: “Em rút về trả tiền phòng thôi”', 'Người hỏi cười theo. Tin đồn xẹp.', spirit=5, default=True),
        C('ignore', 'Không giải thích', 'Mấy hôm sau vẫn còn người nhìn.', spirit=-2)],
      hit=-10, fact='draw'),
    H('dd_love_1', 'dat_dieu', '👀', 'Tin đồn “có gì với nhau”', [
        'Tối qua bạn đi ăn với {who_name}.',
        '{gossip}: “Hai người đó đi riêng, chắc có gì rồi…”',
        'Sáng nay cả hẻm nhìn hai người cười cười.'], [
        C('laugh', 'Cười cho qua cùng {who_name}', 'Hai người cười xòa. Tin đồn không có đất sống.', spirit=5, default=True),
        C('post', 'Nói rõ: “Hàng xóm rủ nhau ăn thôi ạ”', 'Nói rõ rồi thì chẳng ai bàn nữa.', spirit=3),
        C('avoid', 'Tránh mặt nhau mấy hôm', 'Thấy tiếc buổi tối vui hôm qua.', spirit=-4)],
      hit=-10, fact='seen'),
    H('dd_love_2', 'dat_dieu', '💬', '“Nghe nói bị bỏ vì…”', [
        'Chuyện buồn của bạn thành đề tài đầu hẻm.',
        '{gossip} thêm thắt: “Chắc tính khó nên người ta bỏ.”',
        'Bạn nghe được, đau thêm một lần.'], [
        C('ba_sau', 'Kể Bà Sáu nghe', 'Bà Sáu sang đầu hẻm nói một câu. Từ đó im re.', spirit=7, who='ba_sau', bond=3, default=True),
        C('ignore', 'Kệ, chuyện mình mình biết', 'Nói thì dễ, nhưng bạn đang làm được.', spirit=1)],
      hit=-13, fact='breakup'),
    H('dd_stock_1', 'dat_dieu', '📦', '“Hàng về tối ngày, buôn gì lậu?”', [
        'Hàng vừa về {place}, thùng lớn thùng nhỏ.',
        '{gossip}: “Hàng về tối ngày, không biết buôn gì…”',
        'Có người chụp ảnh gửi nhóm.'], [
        C('invoice', 'Đăng ảnh hóa đơn nhập hàng', 'Mọi người thả tim. {gossip} im luôn.', spirit=5, default=True),
        C('gift', 'Mời {gossip} ghé tiệm, tặng món nhỏ', 'Ghé xem tận mắt rồi thì hết nghi.', spirit=6, money=-8),
        C('ignore', 'Kệ, làm ăn đàng hoàng', 'Bạn làm tiếp. Người tinh ý tự hiểu.', spirit=0)],
      hit=-11, fact='stock', careers=STOCKED),
    H('dd_stock_2', 'dat_dieu', '🚚', '“Xe tải đỗ trước tiệm hoài”', [
        'Xe giao hàng đỗ trước {place} mấy lần trong tuần.',
        '{gossip}: “Chắc hàng trôi nổi, rẻ bất thường.”',
        'Có khách hỏi thẳng bạn hàng có thật không.'], [
        C('show', 'Mở thùng cho khách xem tem nhãn', 'Khách gật gù, mua thêm hai món.', spirit=6, default=True),
        C('co_lua', 'Nhờ cô Lụa xác nhận giấy tờ tiệm', 'Cô Lụa nói gọn: “Giấy tờ tiệm này đủ hết.”', spirit=5, who='co_lua', bond=2)],
      hit=-12, fact='stock', careers=STOCKED),
    # ================================================================ the street trades' own hard days
    H('kh_fruit_scale', 'khach', '⚖️', 'Bị nói cân điêu giữa chợ', [
        'Một bà khách lạ cân lại túi cam ở sạp bên, la lên: “Cân thiếu!”',
        'Cân của sạp bên lệch, nhưng cả dãy chợ đã quay sang nhìn.',
        'Bạn đứng đó, mặt nóng bừng.'], [
        C('weigh', 'Mời cân lại bằng quả cân 1 ký trước mặt mọi người', 'Kim chỉ đúng 1 ký. Bà khách ngượng, cả chợ gật gù.', spirit=7, default=True),
        C('argue', 'Cãi lại cho ra lẽ', 'Cãi thắng, nhưng cả buổi chẳng ai ghé sạp.', spirit=-4)], careers=('fruit',), hit=-13, mild=True),
    H('an_garbage_look', 'an_hiep', '🧤', 'Bị coi thường vì đi gom rác', [
        'Một người đi qua bịt mũi, kéo con tránh xa: “Học không giỏi thì làm như cô kia đấy.”',
        'Đứa bé ngoái lại nhìn bạn.',
        'Tay bạn vẫn đang buộc túi rác nhà họ.'], [
        C('smile', 'Mỉm cười với đứa bé, làm tiếp', 'Đứa bé vẫy tay chào. Chị Hạnh vỗ vai: “Nghề nào cũng đáng.”', spirit=6, default=True),
        C('stew', 'Về nhà nghĩ mãi', 'Cả tối ấm ức, ngủ không yên.', spirit=-5)], careers=('garbage',), hit=-14),
    H('kh_drain_quack', 'khach', '📞', 'Khách chê đắt, gọi thợ dạo', [
        'Khách nghe báo giá xong bảo thợ dán số ngoài cột điện rẻ hơn một nửa.',
        'Hôm sau khách gọi lại: thợ dạo đổ hóa chất, ống rò nước ra tường.',
        'Giờ khách nhờ bạn sửa, còn cằn nhằn.'], [
        C('help', 'Tới xem, sửa đúng giá, không trách', 'Khách im lặng trả tiền, cuối tuần giới thiệu thêm hai nhà.', spirit=6, default=True),
        C('told', 'Nói “Đã bảo rồi mà”', 'Nói đúng, nhưng khách giận không gọi nữa.', spirit=-3)], careers=('drain',), hit=-12, mild=True),
    H('kh_chua_shawl', 'khach', '🧣', 'Mời mượn khăn choàng, bị quay clip', [
        'Bạn nhẹ nhàng mời chị khách mặc váy ngắn mượn khăn choàng ở cổng.',
        'Chị khách giơ điện thoại quay: “Chùa gì mà đuổi khách!”',
        'Tối đó clip có mấy trăm lượt xem.'], [
        C('calm', 'Không cãi, nhờ thầy trụ trì đăng lại bảng nội quy cho mọi người', 'Mấy hôm sau có người bình luận: “Thầy nói nhẹ nhàng mà.” Chuyện lắng xuống.', spirit=5, default=True),
        C('read', 'Ngồi đọc hết bình luận', 'Càng đọc càng buồn. Tắt máy lúc nửa đêm.', spirit=-5)], careers=CALLING, hit=-13),
    H('an_chua_young', 'an_hiep', '🙏', 'Bị nói “trẻ vậy mà đi tu”', [
        'Một anh khách nhìn bạn từ đầu tới chân: “Trẻ vậy mà vô chùa, chắc trốn việc nhà.”',
        'Mấy người đứng gần cười khẩy.',
        'Bạn đang ôm chồng chén vừa rửa.'], [
        C('smile', 'Mỉm cười chào anh, làm tiếp', 'Anh khách ngượng, lát sau tự phụ bạn bưng chén ra bếp.', spirit=6, default=True),
        C('stew', 'Về phòng nghĩ mãi', 'Cả buổi chiều thấy nặng lòng.', spirit=-4)], careers=CALLING, hit=-12, mild=True),
    H('kh_chua_donation', 'khach', '📒', 'Người đòi lại tiền công đức', [
        'Một chú khách đứng giữa sân nói to: “Tiền tôi bỏ hòm tuần trước chắc vô túi ai rồi!”',
        'Người đi lễ quay lại nhìn.',
        'Cô Hạnh cầm cuốn sổ đỏ đứng sau lưng bạn.'], [
        C('book', 'Mời chú vào nhà khách, mở sổ và giấy công đức cho chú xem', 'Tên chú có trong sổ, đúng ngày, đúng số. Chú gãi đầu xin lỗi.', spirit=6, default=True),
        C('argue', 'Cãi lại ngay giữa sân', 'Hai bên to tiếng. Người đi lễ lắc đầu bỏ về.', spirit=-4)], careers=CALLING, hit=-14),
    # ================================================================ ✈️ Hãng bay Cánh Cò (pilot, flight_attendant)
    H('air_cancel', 'khach', '😤', 'Chuyến bay hủy, khách trút giận', [
        'Giông cả buổi chiều, chuyến cuối bị hủy.',
        'Một khách chỉ thẳng mặt bạn: “Hãng gì mà làm ăn như vậy!”',
        'Bạn chỉ là người mặc đồng phục đứng gần nhất.'], [
        C('calm', 'Xin lỗi, chỉ khách tới quầy đổi chuyến, rồi ra ngoài thở một chút', 'Khách đi rồi, tay bạn còn run. Nhưng bạn đã làm đúng.',
          spirit=4, default=True),
        C('talk', 'Tối về kể với tổ bay trong nhóm chat', 'Ai cũng từng bị như vậy. Một câu “thương nha” đỡ hơn nhiều.', spirit=6)],
      careers=('pilot', 'flight_attendant'), hit=-13, mild=True),
    H('air_redeye', 'xui', '🌙', 'Bị gọi bay thay ca tối', [
        'Đang ăn cơm với bà Tám thì điện thoại reo.',
        'Tổ bay dự bị ốm, hãng gọi bạn bay thay chuyến tối.',
        'Về tới hẻm đã gần nửa đêm, chân mỏi rã rời.'], [
        C('sleep', 'Tắt điện thoại, ngủ một giấc thật sâu', 'Sáng dậy người nhẹ hẳn.', spirit=5, default=True),
        C('soup', 'Ghé quán cháo đầu hẻm còn mở', 'Bát cháo nóng lúc nửa đêm, ấm cả bụng.', spirit=6, money=-6)],
      careers=('pilot', 'flight_attendant'), hit=-12, mild=True),
    H('air_missed', 'xui', '🎂', 'Lỡ bữa sinh nhật bà Tám', [
        'Hôm nay sinh nhật bà Tám, cả hẻm góp tiền đặt bánh.',
        'Chuyến về trễ hai tiếng vì thời tiết.',
        'Về tới nơi bánh đã cắt, mọi người đã về gần hết.'], [
        C('sorry', 'Gõ cửa phòng bà, xin lỗi và ngồi nghe bà kể chuyện', 'Bà cười: “Đi làm vì người ta, bà hiểu mà.”', spirit=6,
          who='ba_tam', bond=3, default=True),
        C('gift', 'Mai mang quà từ đảo về biếu bà', 'Túi hải sản khô từ đảo, bà khoe với cả hẻm.', spirit=5, money=-10, who='ba_tam', bond=2)],
      careers=('pilot', 'flight_attendant'), hit=-11, mild=True),
    # ================================================================ 🚦 Gác chắn đường ngang Bến Mây (railway)
    H('rw_clip', 'khach', '📱', 'Bị quay clip “gác chắn hách dịch”', [
        'Chiều nay giữ chắn cho một anh không chịu chờ.',
        'Tối về mở điện thoại: clip “gác chắn hách dịch” đã có mấy nghìn lượt xem.',
        'Đoạn tàu lao qua ngay sau đó thì bị cắt mất.'], [
        C('ignore', 'Tắt điện thoại, kể với chú Sáu rồi đi ngủ sớm', 'Chú Sáu cười: “Mình giữ được người ta sống, clip thì kệ clip.”', spirit=5, default=True),
        C('read', 'Ngồi đọc hết bình luận', 'Có người chửi, nhưng cũng nhiều người bênh: “Người ta làm đúng mà.”', spirit=2)],
      careers=('railway',), hit=-13, mild=True),
    H('rw_night', 'xui', '🌙', 'Ca đêm dài như không có sáng', [
        'Ba ca đêm liền, tàu hàng chậm hết chuyến này tới chuyến khác.',
        'Về tới hẻm thì trời đã sáng, chim kêu inh ỏi.',
        'Mắt mở không lên, đầu ong ong.'], [
        C('sleep', 'Kéo rèm, tắt chuông điện thoại, ngủ một mạch', 'Chiều dậy người nhẹ hẳn.', spirit=5, default=True),
        C('pho', 'Ghé quán phở đầu hẻm ăn tô nóng rồi mới ngủ', 'Tô phở nóng lúc sáng sớm, ấm cả bụng.', spirit=6, money=-6)],
      careers=('railway',), hit=-12, mild=True),
    H('rw_scare', 'xui', '😨', 'Thót tim vì cậu thanh niên chui chắn', [
        'Cậu thanh niên lách qua cần chắn đúng lúc còi tàu rúc lên.',
        'Bạn kéo được cậu ta ra, chỉ cách đầu tàu vài chục mét.',
        'Tối về tay vẫn còn run.'], [
        C('talk', 'Gọi cho chú Sáu kể lại', 'Chú Sáu nghe hết rồi bảo: “Con làm đúng. Ngủ đi, mai còn gác.”', spirit=6, default=True),
        C('walk', 'Đi bộ một vòng bờ sông cho bình tâm', 'Gió sông mát rượi, lòng nhẹ dần.', spirit=5)],
      careers=('railway',), hit=-14, mild=True),
    # ================================================================ 🗼 Đèn biển Hòn Gió (lighthouse)
    H('hd_lonely', 'xui', '🏝️', 'Nhớ nhà trên đảo', [
        'Ba tuần liền trên đảo, tàu tiếp tế lỡ chuyến vì biển động.',
        'Mì gói hết, rau vườn chưa kịp lên, sóng điện thoại chập chờn.',
        'Đêm nằm nghe sóng vỗ, nhớ cơm má nấu tới cay mắt.'], [
        C('call', 'Leo lên mỏm đá bắt sóng, gọi video về nhà', 'Má cười, em gái khoe điểm thi. Nghe tiếng nhà là thấy đủ.', spirit=6, default=True),
        C('mun', 'Ôm mèo Mun ngồi đếm sao với chú Bảy', 'Chú Bảy kể chuyện ba mươi năm trên đảo. Mun ngủ quên trong lòng.', spirit=5)],
      careers=('lighthouse',), hit=-13, mild=True),
    H('hd_stormnight', 'xui', '⛈️', 'Đêm bão thức trắng', [
        'Gió giật cấp 8 suốt đêm, mưa quất vào kính phòng đèn như ai ném sỏi.',
        'Bạn canh bộ đàm tới sáng, nghe tàu này gọi tàu kia.',
        'Trời hửng thì mắt đã cay xè, đầu ong ong.'], [
        C('sleep', 'Kéo rèm, ngủ một mạch tới trưa, chú Bảy trực thay', 'Dậy thì biển đã lặng, nắng vàng rực.', spirit=5, default=True),
        C('tea', 'Pha ấm trà nóng ngồi ngắm biển sau bão', 'Biển xanh trong vắt như chưa có gì xảy ra.', spirit=6)],
      careers=('lighthouse',), hit=-12, mild=True),
    H('hd_clip', 'khach', '📱', 'Bị quay clip “gác đèn khó tính”', [
        'Chiều nay từ chối một nhóm khách đòi lên phòng đèn.',
        'Tối mở điện thoại: clip “anh gác đèn làm giá” có mấy nghìn lượt xem.',
        'Đoạn bạn mời họ chụp ảnh ở sân trạm thì bị cắt mất.'], [
        C('ignore', 'Tắt điện thoại, kể với chú Bảy rồi đi ngủ sớm', 'Chú Bảy cười: “Mình giữ đèn cho tàu về, clip thì kệ clip.”', spirit=5, default=True),
        C('read', 'Ngồi đọc hết bình luận', 'Có người chửi, nhưng nhiều người bênh: “Nội quy là nội quy mà.”', spirit=2)],
      careers=('lighthouse',), hit=-13, mild=True),
]

# ---------------------------------------------------------------- neighbours come round
# who: a journey CAST id, 'work' (WORK[career]) or 'friends'. cats: which hard days it fits.
# The card offers `yes` (cost/spirit/bond below), `self` (blow off steam on your own) and `no`.


def K(kid: str, who: str, cats: tuple, lines: list, label: str, text: str, spirit: int, cost: int = 0, bond: int = 4,
      money: int = 0, advice: bool = False) -> dict:
    return dict(id=kid, who=who, cats=tuple(cats), lines=list(lines), label=label, text=text, spirit=spirit, cost=cost,
                bond=bond, money=money, advice=advice)


_ANY = ('an_hiep', 'phu_huynh', 'khach', 'lua', 'that_tinh', 'xui', 'om', 'ru')
COMFORT = [
    K('ba_sau_che', 'ba_sau', _ANY + ('dat_dieu',), [
        'Con ơi, bà nấu nồi chè đậu đen, qua ăn với bà.',
        'Chuyện gì rồi cũng qua. Ăn cho ngọt miệng cái đã.'],
      'Qua nhà Bà Sáu ăn chè', 'Chén chè mát lạnh, bà ngồi quạt cho. Nghe bà kể chuyện ngày xưa mà nhẹ cả lòng.', 18),
    K('khoa_bia', 'anh_khoa', ('an_hiep', 'khach', 'that_tinh', 'xui', 'lua', 'ru'), [
        'Ê, nhìn mặt là biết hôm nay tệ rồi.',
        'Ra đầu hẻm làm vài cốc bia hơi, anh bao!'],
      'Đi bia hơi với Anh Khoa', 'Hai anh em ngồi vỉa hè, nói đủ thứ chuyện trên trời dưới đất. Anh Khoa giành trả tiền.', 20),
    K('work_karaoke', 'work', ('an_hiep', 'khach', 'phu_huynh', 'ru'), [
        'Nghe chuyện rồi. Tối nay cả nhóm đi karaoke nha!',
        'Chia tiền phòng thôi, không ai được từ chối.'],
      'Đi karaoke với cả nhóm', 'Hát tới khàn giọng. Có đứa hát “Nơi này có anh” lệch tông cả bài, cười muốn xỉu.', 25, cost=10, bond=0),
    K('ba_tam_chao', 'ba_tam', ('xui', 'om', 'lua', 'that_tinh', 'an_hiep'), [
        'Bà nấu nồi cháo gà, để phần cháu một tô.',
        'Ăn nóng rồi đi ngủ sớm, nghe chưa.'],
      'Xuống ăn cháo với Bà Tám', 'Tô cháo nóng, thêm hành phi. Ăn xong người ấm hẳn lên.', 16),
    K('co_ba_qua', 'co_ba', ('khach', 'xui', 'lua', 'phu_huynh', 'dat_dieu'), [
        'Cô gói cho ít trái cây với bịch bánh.',
        'Làm ăn thì ai cũng có ngày xui con ạ.'],
      'Nhận quà của Cô Ba', 'Bịch bánh còn ấm. Cô Ba dặn mai ghé tiệm ngồi chơi.', 12),
    K('be_ti_tranh', 'be_ti', ('an_hiep', 'phu_huynh', 'khach', 'that_tinh', 'xui', 'ru'), [
        dict(male='Anh ơi, em vẽ tặng anh nè!', female='Chị ơi, em vẽ tặng chị nè!', none='Em vẽ tặng nè!'),
        'Tranh có mặt trời to đùng, ghi “CỐ LÊN”.'],
      'Nhận tranh của Bé Tí', 'Bạn dán tranh lên tường gác. Nhìn là muốn cười.', 12),
    K('chu_tu_tra', 'chu_tu', ('an_hiep', 'xui', 'khach', 'lua'), [
        'Ghé tiệm chú uống ấm trà.',
        'Đồ hư thì sửa, lòng buồn thì ngồi đây một lát.'],
      'Ngồi trà với Chú Tư', 'Chú Tư vừa sửa quạt vừa kể chuyện nghề. Tiếng tua vít đều đều mà dễ chịu lạ.', 14),
    K('co_lua_phuong', 'co_lua', ('lua',), [
        'Để cô đi cùng cháu lên phường trình báo.',
        'Bị lừa không phải lỗi của mình. Lỗi là của kẻ lừa.'],
      'Đi cùng Cô Lụa lên phường', 'Có cô Lụa bên cạnh, bạn kể rành mạch hơn. Cán bộ hứa theo dõi vụ việc.', 14),
    K('friends_bien', 'friends', ('that_tinh',), [
        'Không nói nhiều, cuối tuần đi biển!',
        'Xe đã thuê, chỉ việc xách balo lên.'],
      'Đi biển với nhóm bạn', 'Gió biển, cát, ốc nướng. Hét một tiếng thật to ngoài bãi, xong thấy mình ổn hơn.', 32, cost=20, bond=0),
    K('friends_pho', 'friends', ('that_tinh', 'an_hiep', 'xui'), [
        'Tối nay đi ăn phở, tụi tao bao.',
        'Ai buồn thì được thêm trứng.'],
      'Đi ăn phở với nhóm bạn', 'Tô phở nghi ngút, ba đứa tranh nhau kể chuyện dở hơi. Cười tới chảy nước mắt.', 18, bond=0),
    K('friends_phim', 'friends', ('that_tinh', 'ru'), [
        'Có phim hài mới chiếu, đi không?',
        'Bắp nước chia đôi nha.'],
      'Đi xem phim với nhóm bạn', 'Phim dở tệ nhưng cả rạp cười. Về tới nhà vẫn còn cười.', 20, cost=8, bond=0),
    K('ba_sau_khuyen', 'ba_sau', ('dat_dieu',), [
        'Miệng người ta, mình đâu có khâu lại được.',
        'Kệ người ta con. Sống thật là được.'],
      'Ngồi nghe Bà Sáu khuyên', 'Bà Sáu nắm tay bạn một lúc lâu. Tự nhiên thấy chuyện kia nhỏ xíu.', 16, advice=True),
    K('co_lua_khuyen', 'co_lua', ('dat_dieu',), [
        'Cô sống ở hẻm này ba chục năm, tin đồn nào rồi cũng tắt.',
        'Người tử tế thì cả hẻm biết. Cháu cứ làm việc của cháu.'],
      'Nghe Cô Lụa nói chuyện', 'Cô Lụa rót ly trà, kể mấy tin đồn hồi xưa giờ ai cũng quên. Bạn bật cười.', 14, advice=True),
    K('khoa_khuyen', 'anh_khoa', ('dat_dieu',), [
        'Hồi anh mới dọn tới cũng bị đồn là “trốn nợ”.',
        'Kệ đi. Tối rảnh đi ăn ốc với anh.'],
      'Đi ăn ốc với Anh Khoa', 'Ốc len xào dừa, Anh Khoa kể vụ “trốn nợ” năm xưa. Cười rũ rượi.', 18, advice=True),
    K('ba_tam_khuyen', 'ba_tam', ('dat_dieu', 'that_tinh'), [
        'Người ta nói gì kệ người ta, bà biết cháu mà.',
        'Ăn miếng bánh bò rồi ngủ một giấc.'],
      'Ăn bánh bò với Bà Tám', 'Bà Tám bảo: “Bà ở đây, không ai bắt nạt cháu được.” Ấm lòng.', 15, advice=True),
    K('co_ba_khuyen', 'co_ba', ('dat_dieu',), [
        'Người ta nói ra nói vào, mình làm ăn đàng hoàng là được.',
        'Tối nay ghé cô ăn cơm, có canh chua.'],
      'Ăn cơm tối với Cô Ba', 'Bữa cơm có canh chua, cá kho. Cô Ba không nhắc chuyện kia câu nào.', 16, advice=True),
]

# Meat, fish, snails or beer: never offered to a monk (CALLING), nor is a karaoke night with the 'work' crowd.
NOT_FOR_CALLING = ('khoa_bia', 'ba_tam_chao', 'friends_bien', 'friends_pho', 'khoa_khuyen', 'co_ba_khuyen')

# Gifts after a scam or a loss (instead of money).
GIFTS = {
    'phone': dict(emoji='📱', name='Chiếc điện thoại cũ', text='Anh Khoa đưa chiếc điện thoại cũ còn xài tốt: “Xài tạm nha em.”', who='anh_khoa', spirit=16, money=0),
    'rice': dict(emoji='🍚', name='Bao gạo 10 ký', text='Bà Tám với Cô Ba khiêng lên bao gạo: “Đỡ được mấy bữa cơm.”', who='ba_tam', spirit=14, money=12),
    'flowers': dict(emoji='💐', name='Bó hoa và tấm thiệp', text='Tấm thiệp ký tên cả hẻm: “Có tụi mình ở đây.”', who='co_lua', spirit=16, money=0),
    'food': dict(emoji='🍱', name='Giỏ đồ ăn', text='Giỏ trứng, rau, mì gói, cả hộp bánh của Bé Tí.', who='co_ba', spirit=14, money=10),
}

# ---------------------------------------------------------------- blow off steam (xả stress)
# risk: dict(p=chance of the bad twist, spirit=…, text=…) rolled from the seed.
COPE = [
    dict(id='karaoke', emoji='🎤', label='Karaoke với bạn', cost=25, spirit=22,
         text='Hát tới khàn giọng. Ra về thấy nhẹ tênh.'),
    dict(id='tra_sua', emoji='🧋', label='Trà sữa + dạo shop', cost=15, spirit=12,
         text='Ly trà sữa full topping, cái áo mới. Vui vui.'),
    dict(id='dalat', emoji='🌲', label='Cuối tuần lên Đà Lạt', cost=120, spirit=45,
         text='Sương sớm, đồi thông, ly sữa đậu nóng. Về phố như người mới.'),
    dict(id='vungtau', emoji='🏖️', label='Cuối tuần đi Vũng Tàu', cost=85, spirit=36,
         text='Tắm biển, ăn bánh khọt. Gió biển thổi bay hết mọi thứ.'),
    dict(id='online', emoji='📦', label='Chốt đơn online cho sướng tay', cost=35, spirit=14,
         text='Hàng về đúng ảnh, xinh xỉu. Đáng đồng tiền!',
         risk=dict(p=.5, spirit=3, text='Hàng về… không giống ảnh chút nào. Tiền thì đi rồi.')),
    dict(id='nhau', emoji='🍺', label='Uống một mình', cost=12, spirit=8, hangover=True,
         text='Vài lon bia, một bản nhạc buồn. Mai chắc hơi mệt.'),
    dict(id='ho', emoji='🌊', label='Đi dạo bờ hồ', cost=0, spirit=9,
         text='Gió hồ mát rượi, có ông cụ thả diều. Lòng lắng xuống.'),
    dict(id='ngu', emoji='😴', label='Ngủ nướng một bữa', cost=0, spirit=7,
         text='Ngủ một giấc tới trưa. Dậy thấy đầu nhẹ hẳn.'),
    dict(id='me', emoji='📞', label='Gọi điện cho mẹ', cost=0, spirit=11,
         text='Mẹ kể chuyện con gà ở nhà, rồi dặn ăn uống đầy đủ. Nghe giọng mẹ là đủ.'),
]
COPE_INDEX = {x['id']: x for x in COPE}

# ---------------------------------------------------------------- neighbours in trouble (trả ơn)
# Choices: big (−big xu), small (−small xu), hand (free, a hand), none.
ASK = [
    dict(id='ask_roof', who='ba_sau', emoji='🏚️', title='Mái nhà Bà Sáu bị dột', big=25, small=10,
         lines=['Mưa đêm qua, nhà Bà Sáu dột tứ tung.', 'Cả hẻm đang góp tiền mua tôn.'],
         hand='Qua phụ khiêng tôn, lợp mái'),
    dict(id='ask_theft', who='co_ba', emoji='🔓', title='Tạp hóa Cô Ba bị trộm', big=30, small=10,
         lines=['Đêm qua tạp hóa Cô Ba bị cạy cửa.', 'Mất cả thùng sữa với két tiền lẻ.'],
         hand='Phụ cô dọn dẹp, sắp lại hàng'),
    dict(id='ask_hospital', who='chu_tu', emoji='🏥', title='Chú Tư nhập viện', big=35, small=15,
         lines=['Chú Tư mổ ruột thừa gấp.', 'Tiệm đóng cửa, cả hẻm góp tiền thăm chú.'],
         hand='Vào viện trông chú một buổi'),
    dict(id='ask_school', who='be_ti', emoji='🎒', title='Bé Tí thiếu tiền học thêm', big=20, small=8,
         lines=['Bé Tí sắp thi vào 10.', 'Nhà khó, chưa đủ tiền học thêm.'],
         hand='Kèm Bé Tí học buổi tối'),
    dict(id='ask_job', who='anh_khoa', emoji='📦', title='Anh Khoa bị mất việc', big=25, small=10,
         lines=['Công ty cắt giảm, Anh Khoa mất việc.', 'Anh ấy cười cười, nhưng mắt buồn.'],
         hand='Rủ anh ấy qua ăn cơm, sửa giúp CV'),
    dict(id='ask_scam', who='ba_tam', emoji='📞', title='Bà Tám bị lừa qua điện thoại', big=30, small=12,
         lines=['Bà Tám bị gọi giả “công an”, mất tiền dưỡng già.', 'Bà ngồi thừ ở hiên.'],
         hand='Ngồi với bà, cài chặn số lạ giúp bà'),
    dict(id='ask_trungthu', who='co_lua', emoji='🏮', title='Trung thu cho trẻ con trong hẻm', big=20, small=8,
         lines=['Tổ dân phố làm Trung thu cho tụi nhỏ.', 'Cô Lụa đang gom tiền mua lồng đèn.'],
         hand='Phụ dán lồng đèn, bày mâm cỗ'),
    dict(id='ask_flood', who='co_lua', emoji='🌧️', title='Nhà cuối hẻm bị ngập', big=25, small=10,
         lines=['Nhà bà cụ cuối hẻm ngập tới gối.', 'Đồ đạc hư hết, cả hẻm xúm lại giúp.'],
         hand='Xắn quần qua tát nước, khiêng đồ'),
]

# ---------------------------------------------------------------- small joys
JOYS = [
    dict(id='joy_drawing', who='be_ti', emoji='🖍️', spirit=7,
         lines=[dict(male='Bé Tí vẽ anh đang làm việc, tóc dựng đứng.', female='Bé Tí vẽ chị đang làm việc, tóc bay phấp phới.', none='Bé Tí vẽ bạn đang làm việc.'), 'Dưới tranh ghi: “Người giỏi nhất hẻm”.'],
         title='Bức tranh của Bé Tí'),
    dict(id='joy_soup', who='ba_tam', emoji='🍲', spirit=6, title='Nồi canh chua của Bà Tám',
         lines=['Bà Tám để phần tô canh chua cá lóc.', 'Mảnh giấy dán nắp: “Ăn nóng nghe cháu.”']),
    dict(id='joy_kitten', who='ba_sau', emoji='🐱', spirit=8, title='Mèo nhà Bà Sáu đẻ',
         lines=['Mèo nhà Bà Sáu đẻ bốn con.', 'Bà cho bạn đặt tên một đứa.']),
    dict(id='joy_rain', who=None, emoji='🌦️', spirit=5, title='Mưa đầu mùa',
         lines=['Mưa đầu mùa, cả hẻm thơm mùi đất.', 'Bạn ngồi bên cửa sổ, nghe mưa.']),
    dict(id='joy_thanks', who=None, emoji='💌', spirit=7, title='Tin nhắn cảm ơn bất ngờ',
         lines=['Một khách cũ nhắn cảm ơn.', '“Nhờ hôm đó mà nhà em vui cả tuần.”']),
    dict(id='joy_mum', who=None, emoji='📦', spirit=8, title='Thùng quà quê của mẹ',
         lines=['Mẹ gửi lên thùng quà quê.', 'Mắm, bánh tráng, bịch me, và lá thư nhỏ.']),
    dict(id='joy_tea', who='co_ba', emoji='🍵', spirit=5, title='Ấm trà đầu hẻm',
         lines=['Cô Ba gọi vào uống trà.', 'Hai cô cháu ngồi ngắm người qua lại.']),
    dict(id='joy_fix', who='chu_tu', emoji='🔧', spirit=6, title='Chú Tư sửa giúp quạt',
         lines=['Cái quạt kêu rè rè cả tuần.', 'Chú Tư ghé sửa, không lấy tiền.']),
    dict(id='joy_sunset', who=None, emoji='🌇', spirit=5, title='Hoàng hôn trên sân thượng',
         lines=['Chiều nay trời đỏ rực.', 'Cả dãy trọ lên sân thượng chụp ảnh.']),
    dict(id='joy_khoa', who='anh_khoa', emoji='🥤', spirit=6, title='Anh Khoa mua dư ly nước',
         lines=['“Mua dư một ly, em uống giùm anh.”', 'Ly nước mía mát lạnh.']),
]

# ---------------------------------------------------------------- low spirit
IMPULSE = [
    dict(id='imp_cart', emoji='🛒', title='1 giờ sáng, giỏ hàng đầy',
         lines=['Không ngủ được, lướt sàn tới 1 giờ.', 'Giỏ hàng: 6 món, món nào cũng “cần”.'], big=45, small=15),
    dict(id='imp_live', emoji='📺', title='Livestream “xả kho”',
         lines=['Chị bán hàng hét: “Còn 3 cái cuối!”', 'Tay bạn run run trên nút “Mua”.'], big=40, small=12),
    dict(id='imp_boba', emoji='🧋', title='Ba ly trà sữa một ngày',
         lines=['Buồn quá, ly thứ nhất.', 'Ly thứ hai, rồi ly thứ ba size L.'], big=30, small=10),
    dict(id='imp_sale', emoji='🏷️', title='Sale 12.12 rầm rộ',
         lines=['Thông báo nổ liên tục: “Giảm 70%!”', 'Bạn đâu cần gì… nhưng rẻ quá.'], big=50, small=15),
    dict(id='imp_food', emoji='🍗', title='Gọi đồ ăn đêm liên tục',
         lines=['Ba tối liền gọi gà rán lúc nửa đêm.', 'Tủ lạnh chật hộp xốp.'], big=35, small=12),
]
SICK = [
    dict(id='sick_fever', emoji='🤒', title='Sốt một trận', cost=15,
         lines=['Sáng dậy người nóng ran.', 'Đầu nặng như đeo đá. Phải mua thuốc.']),
    dict(id='sick_throat', emoji='😷', title='Viêm họng mất tiếng', cost=12,
         lines=['Họng đau rát, nói không ra tiếng.', 'Mua thuốc ngậm với siro.']),
    dict(id='sick_stomach', emoji='🤢', title='Đau bao tử', cost=14,
         lines=['Mấy hôm ăn uống thất thường.', 'Tối qua đau quặn cả bụng.']),
]

# Invites when you are low (no hard day needed).
INVITE_CATS = ('ru',)
FACTS = ('late', 'spend', 'draw', 'seen', 'breakup', 'stock')

# ---------------------------------------------------------------- 🛏️ Ký túc xá Hẻm 7 (game/housing.py DORM)
# The three roommates of the bunk room (four beds; the player's is the bottom bed by the window). People a card may
# name (life._people), not neighbours with a bond. `look`: wardrobe item ids for the portrait (public/js/v4/look.js),
# `bed`: where the room drawing puts them. Ids are stored in saves (life card and log `who`): never rename one.
ROOMMATES = {
    'ktx_quan': dict(name='Quân', emoji='🎓', role='Sinh viên năm cuối, đang làm đồ án', gender='male', bed='left_top',
                     look=dict(hair='toc_ngan', shade='mau_den', skin='da_trung', top='ao_so_mi', bottom='quan_jean',
                               shoes='giay_trang', acc='kinh_tron')),
    'ktx_tuan': dict(name='Anh Tuấn', emoji='🛵', role='Shipper chạy ca đêm, ngủ ban ngày', gender='male', bed='left_bottom',
                     look=dict(hair='toc_xoan', shade='mau_nau', skin='da_ngam', top='ao_hoodie', bottom='quan_xam',
                               shoes='dep_lao', acc='pk_khong')),
    'ktx_my': dict(name='My', emoji='📦', role='Cô bé bán hàng online, tối nào cũng livestream', gender='female', bed='right_top',
                   look=dict(hair='toc_duoi_ngua', shade='mau_hong', skin='da_hong', top='ao_hoa', bottom='vay_xoe',
                             shoes='giay_do', acc='pk_khong')),
}

# Small everyday moments in the bunk room: a card on some days while the player lives there (life._roll).
# Each choice moves tinh thần by at most 3 and the wallet by a few xu; the default (taken when the card is left
# undecided) never costs xu. `also`: the other roommates in the scene.
DORM = [
    dict(id='ktx_sac', who='ktx_quan', emoji='🔌', title='Quân mượn sạc',
         lines=['Gần nửa đêm, Quân ló đầu khỏi rèm giường trên.',
                '“Cho mình mượn cục sạc chút, mai nộp đồ án mà laptop sắp tắt…”'],
         choices=[C('lend', 'Cho mượn', 'Sáng ra cục sạc nằm gọn trên gối bạn, kèm gói bánh quy và mảnh giấy “cảm ơn nha”.',
                    spirit=2, default=True),
                  C('later', 'Thôi để mai, máy mình cũng sắp hết pin', 'Quân gật gù rồi đi gõ cửa phòng bên. Bạn hơi áy náy.',
                    spirit=-1)]),
    dict(id='ktx_mi', who='ktx_tuan', emoji='🍜', title='Nồi mì chung lúc khuya',
         lines=['Anh Tuấn chạy ca đêm về sớm, giơ hai gói mì với quả trứng.', '“Ai góp thêm gì thì nấu nồi bự ăn chung nè.”'],
         choices=[C('chip', 'Góp mớ rau với quả trứng', 'Nồi mì bốc khói, bốn đứa ngồi bệt dưới sàn húp sùm sụp. Ngon hơn nhà hàng.',
                    spirit=3, money=-3),
                  C('sleep', 'Thôi để mai, mình buồn ngủ quá', 'Bạn kéo rèm ngủ trước. Mùi mì thơm lừng vẫn len vào giấc mơ.',
                    spirit=1, default=True)]),
    dict(id='ktx_on', who='ktx_my', emoji='📣', title='My livestream lúc khuya',
         lines=['Mười một giờ đêm, My vẫn live: “Chốt đơn nha cả nhà, áo này còn ba cái thôi!”',
                'Bạn trằn trọc, mai còn đi làm sớm.'],
         choices=[C('ask', 'Nhắn nhẹ nhờ My nói nhỏ lại', 'My gửi liền cái sticker xin lỗi: “Từ mai em ra hành lang live nha!” Phòng im phăng phắc.',
                    spirit=1, default=True),
                  C('plug', 'Đeo nút tai, trùm chăn ngủ', 'Ngủ được, mà chập chờn. Sáng dậy mắt hơi thâm.', spirit=-2)]),
    dict(id='ktx_que', who='ktx_tuan', emoji='🐟', title='Đồ ăn quê gửi lên',
         lines=['Mẹ Anh Tuấn gửi xe khách lên một thùng: cá khô, mắm ruốc, bánh tráng.', '“Ăn đi mấy đứa, nhà gửi nhiều lắm.”'],
         choices=[C('take', 'Nhận một phần, cảm ơn rối rít', 'Tối đó cơm với cá khô mà ngon lạ, đỡ được hộp cơm mua ngoài. Bạn nhớ nhà một chút.',
                    spirit=2, money=3, default=True),
                  C('swap', 'Đổi lại gói kẹo mua chiều nay', 'Anh Tuấn cười khà khà. Cả phòng đổi qua đổi lại, rôm rả như hồi ở quê.',
                    spirit=3, money=-2)]),
    dict(id='ktx_dien', who='ktx_my', emoji='💡', title='My nhắc đóng tiền điện',
         lines=['My dán tờ giấy lên cửa tủ lạnh: “Tiền điện máy lạnh tuần này, mỗi người góp chút nha 🥺”'],
         choices=[C('pay', 'Chuyển khoản liền', 'My thả tim tin nhắn. Phòng mình chẳng ai phải nhắc ai lần hai.', spirit=1, money=-4),
                  C('later', 'Thôi để mai nhé', 'My gật đầu, nhưng tờ giấy trên tủ lạnh có thêm tên bạn được gạch chân.',
                    spirit=-1, default=True)]),
    dict(id='ktx_ao', who='ktx_quan', emoji='👔', title='Quân mượn áo đi phỏng vấn',
         lines=['Sáng mai Quân phỏng vấn thực tập ở một công ty xây dựng, mà áo sơ mi nào cũng nhàu.',
                '“Cho mình mượn cái áo tử tế được không? Mình giặt ủi trả liền.”'],
         choices=[C('lend', 'Cho mượn, ủi giùm luôn', 'Chiều Quân về, khoe đậu vòng một, mua trà sữa đãi cả phòng.', spirit=3, default=True),
                  C('no', 'Áo mình cũng nhàu hết rồi', 'Quân chạy sang phòng bên mượn. Tối về vẫn cười: “Không sao đâu!”')]),
    dict(id='ktx_khuya', who='ktx_tuan', emoji='🌙', title='Anh Tuấn về lúc hai giờ sáng',
         lines=['Hai giờ sáng, Anh Tuấn giao đơn khuya về, lỡ tay làm rớt cái mũ bảo hiểm cái cộp.'],
         choices=[C('water', 'Ngồi dậy rót cho anh ly nước', 'Anh kể vụ khách đặt mười ly trà sữa rồi tắt máy. Hai người cười khúc khích, sợ cả phòng thức.',
                    spirit=1),
                  C('sleep', 'Lầm bầm rồi ngủ tiếp', 'Bạn trùm chăn ngủ lại, giấc ngủ đứt quãng tới sáng.', spirit=-2, default=True)]),
    dict(id='ktx_doan', who='ktx_quan', emoji='📐', title='Đồ án dí deadline',
         lines=['Quân thức trắng in bản vẽ, tiệm photo dưới hẻm đòi thêm tiền in màu.',
                '“Ai cho mình mượn ít xu, bảo vệ xong mình khao bún bò!”'],
         choices=[C('lend', 'Cho mượn ít xu', 'Bản vẽ in kịp giờ. Quân ôm cuộn giấy chạy đi, ngoái lại giơ ngón cái.', spirit=2, money=-4),
                  C('no', 'Ví mình cũng mỏng lắm', 'Quân gật đầu: “Không sao, để mình hỏi Anh Tuấn.”', default=True)]),
    dict(id='ktx_don', who='ktx_my', emoji='🧹', title='Tổng vệ sinh phòng',
         lines=['Sáng nay My hô cả phòng: “Ai lau sàn, ai đổ rác, ai giặt rèm nè?”'],
         choices=[C('help', 'Xắn tay áo lau sàn', 'Phòng thơm mùi nước lau sàn. Bốn cái giường tầng gọn như khách sạn.', spirit=2, default=True),
                  C('later', 'Thôi để mai mình làm bù nha', 'Cả phòng dọn xong trước. Bạn hơi ngại, hứa tuần sau đổ rác cả tuần.', spirit=-1)]),
    dict(id='ktx_cup_dien', who='ktx_quan', also=('ktx_tuan', 'ktx_my'), emoji='🕯️', title='Cúp điện, kể chuyện ma',
         lines=['Mưa to, cúp điện cả dãy. Bốn đứa nằm trên giường tầng, soi đèn điện thoại.', 'Quân đề nghị: “Kể chuyện ma đi!”'],
         choices=[C('tell', 'Kể chuyện ma quê mình', 'My hét lên trốn vào chăn, Anh Tuấn cười sằng sặc. Đêm đó cả phòng thân thêm chút.', spirit=3),
                  C('sleep', 'Thôi ngủ sớm cho khỏe', 'Bạn nằm nghe tiếng mưa với tiếng cả phòng thì thầm, ngủ lúc nào không hay.',
                    spirit=1, default=True)]),
]

# A roommate's line of the day on the home card (housing.public: picked from the journey seed and the life day).
DORM_LINES = {
    'ktx_quan': ['Còn mấy hôm nữa bảo vệ đồ án. Ai thấy mình ngủ gục thì đắp chăn giùm nha.',
                 'Mai mình dậy sớm chạy bộ quanh hồ, ai đi chung không?',
                 'Wifi chậm quá, chắc phòng bên lại đang coi phim.'],
    'ktx_tuan': ['Đêm qua chạy được hai chục đơn, mệt mà vui.',
                 'Ai ăn bánh mì không? Khách hủy đơn, anh mang về nè.',
                 'Anh ngủ ngày, mấy đứa về nhớ đóng cửa nhẹ nhẹ giùm nha.'],
    'ktx_my': ['Tối nay em live tám giờ, cả phòng vào thả tim giùm em nha!',
               'Nồi cơm điện em nấu dư, ai đói thì xới nha.',
               'Tuần này phòng mình đóng điện đúng hẹn, chủ nhà khen quá trời.'],
}
