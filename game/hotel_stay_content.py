"""🏨 Phòng cho người chơi (game/hotel_stay.py): the words and numbers of the stays, apart from the rules.

Owner 01/10 (standing rule): every career needs MANY awkward, annoying, strange demands. A stay is a short chain of
them for the host: the arrival quirk (check-in), the situations of the night (some come by themselves, some the
guest player sends), and the check-out quirk. Each one is a small decision: 2–4 options, each with
  (id, label, mood, cost, effect, reply)
* mood: the guest's satisfaction moves by this much (0–100, the stay starts at hotel_stay.MOOD_START);
* cost: xu the HOST pays from their wallet (then account) for that choice, burned (a key card, a fan, a tray of
  fruit: a money sink, never paid to anyone, never more than COST_MAX);
* effect: '' | 'late' (the stay ends LATE_MIN later) | 'upgrade' (the room becomes "nâng hạng");
* reply: what the guest reads in their stay card ("Lễ tân mang quạt lên ngay").
Nothing here prints money: the guest's benefit is rest (hotel_stay.REST), at most once a Vietnam day.
"""
from __future__ import annotations

COST_MAX = 6

# ---------------------------------------------------------------- rooms (picked at check-in)
# tags: double (giường đôi), twin (2 giường đơn), quiet, view, bath, stairs, suite (costs SUITE_COST to make up)
ROOMS = {
    'homestay': (
        dict(id='thong', name='Đồi Thông', icon='🌲', note='Giường đôi · cuối vườn, yên tĩnh', tags=('double', 'quiet')),
        dict(id='suong', name='Sương Sớm', icon='🌁', note='Hai giường đơn · cạnh bếp', tags=('twin',)),
        dict(id='gac', name='Gác Mái', icon='🛖', note='Giường đôi · cầu thang gỗ dốc', tags=('double', 'stairs')),
        dict(id='ho', name='Ban Công Hồ', icon='🌅', note='Giường đôi · bồn tắm · nhìn ra hồ', tags=('double', 'view', 'bath')),
    ),
    'hotel': (
        dict(id='p101', name='Phòng 101', icon='🛏️', note='Giường đôi · sát thang máy', tags=('double',)),
        dict(id='p205', name='Phòng 205', icon='🌙', note='Hai giường đơn · cuối hành lang, yên tĩnh', tags=('twin', 'quiet')),
        dict(id='p308', name='Phòng 308', icon='🌆', note='Giường đôi · cửa sổ lớn hướng phố', tags=('double', 'view')),
        dict(id='p501', name='Suite 501', icon='👑', note='Giường king · bồn tắm · yên tĩnh (dọn suite: 3 xu)',
             tags=('double', 'view', 'quiet', 'bath', 'suite')),
    ),
}
SUITE_COST = 3

# what the guest asked for when booking (one per stay, drawn from the order): the right room pleases, the wrong one not
WISHES = {
    'quiet': dict(icon='🤫', text='Cho mình phòng yên tĩnh nha, mình ngủ tỉnh lắm, muỗi bay cũng dậy.', tag='quiet'),
    'view': dict(icon='📸', text='Phòng nào view đẹp đẹp cho mình sống ảo với, không cần to.', tag='view'),
    'bath': dict(icon='🛁', text='Có bồn tắm không? Mình mang theo cả túi muối tắm rồi.', tag='bath'),
    'nostairs': dict(icon='🧳', text='Vali mình 30 ký, đừng bắt mình leo cầu thang nha.', tag='-stairs'),
}

# the guest's temperament (drawn from the order; the host sees a hint): kho_tinh makes every bad choice 1.5× worse,
# de_tinh halves it, lam_chuyen brings one more situation in the night
TEMPERS = {
    'de_tinh': dict(icon='😊', hint='Khách xởi lởi, dễ chịu.', bad=0.5, extra=0),
    'kho_tinh': dict(icon='🧐', hint='Khách có vẻ khó tính, soi từng chút.', bad=1.5, extra=0),
    'lam_chuyen': dict(icon='🗣️', hint='Khách nói nhiều, chắc sẽ gọi lễ tân hoài.', bad=1.0, extra=1),
}

# ---------------------------------------------------------------- arrival (check-in)
CHECKIN = {
    'som': dict(icon='⏰', text='Khách tới sớm 3 tiếng, kéo vali đứng giữa sảnh đòi nhận phòng ngay. Phòng chưa dọn kịp.', opts=(
        ('tra', 'Mời ngồi uống trà, giữ vali, dọn xong báo liền', 4, 0, '', 'Lễ tân mời bạn ly trà nóng, giữ vali giúp trong lúc dọn phòng.'),
        ('gap', 'Gọi thêm người dọn gấp cho nhận luôn (4 xu)', 8, 4, '', 'Lễ tân gọi thêm người dọn gấp: bạn nhận phòng luôn.'),
        ('cung', 'Nói thẳng: đúng giờ mới nhận phòng', -8, 0, '', 'Lễ tân bảo đúng giờ mới nhận phòng. Bạn ngồi chờ ở sảnh.'),
    )),
    'nick': dict(icon='🪪', text='Đặt phòng ghi tên "Hoàng Tử Bóng Đêm", giấy tờ thì là "Nguyễn Văn Tèo". Khách bảo: "Là em đó anh."', opts=(
        ('ma', 'Lịch sự đối chiếu mã đặt phòng và số điện thoại', 5, 0, '', 'Lễ tân đối chiếu mã đặt phòng nhẹ nhàng, không làm khó bạn.'),
        ('cuoi', 'Cười xòa cho vào luôn, ai chẳng có nickname', 0, 0, '', 'Lễ tân cười xòa cho bạn vào luôn.'),
        ('chup', 'Đòi chụp căn cước gửi vào nhóm chat nhân viên', -12, 0, '', 'Lễ tân đòi chụp giấy tờ của bạn gửi nhóm chat. Bạn không vui chút nào.'),
    )),
    'thachsung': dict(icon='🦎', text='Khách đòi giảm giá vì "lần trước ở đây có con thạch sùng nhìn em suốt đêm".', opts=(
        ('nuoc', 'Không giảm, tặng hai chai nước mát (2 xu)', 4, 2, '', 'Không giảm giá, nhưng lễ tân tặng bạn hai chai nước mát.'),
        ('hua', 'Xin lỗi, hứa phòng lần này đã đuổi hết thạch sùng', 2, 0, '', 'Lễ tân xin lỗi, hứa phòng đã sạch bóng thạch sùng.'),
        ('linhvat', 'Bảo đó là linh vật của nhà, nhìn ai là người đó may', -4, 0, '', 'Lễ tân bảo thạch sùng là linh vật. Bạn không thấy buồn cười lắm.'),
    )),
    'bien': dict(icon='🌊', text='Khách hỏi: "Phòng em đặt nhìn ra biển đúng không ạ?" Phố Mây không có biển.', opts=(
        ('ho', 'Giới thiệu hồ sau phố: cũng xanh, cũng có gió', 5, 0, '', 'Lễ tân giới thiệu hồ sau phố, chiều có gió mát.'),
        ('tranh', 'Treo tạm bức tranh biển thật to trong phòng (3 xu)', 6, 3, '', 'Lễ tân treo bức tranh biển thật to trong phòng cho bạn.'),
        ('that', 'Nói thật: phố mình không có biển, chắc chị nhầm app', -3, 0, '', 'Lễ tân bảo phố không có biển, chắc bạn nhầm app.'),
    )),
    'chau': dict(icon='🧍', text='Khách dắt theo "đứa cháu" cao 1m8, râu lún phún, bảo trẻ con thì ở miễn phí.', opts=(
        ('nem', 'Kê thêm nệm phụ, coi như quà của nhà (3 xu)', 6, 3, '', 'Lễ tân kê thêm nệm phụ cho "cháu", không tính tiền.'),
        ('tuoi', 'Hỏi tuổi cháu, cười cho qua chuyện', 2, 0, '', 'Lễ tân hỏi tuổi "cháu" rồi cười cho qua.'),
        ('cam', 'Không cho "cháu" lên phòng', -10, 0, '', 'Lễ tân không cho "cháu" lên phòng. Cả nhà bạn mặt nặng mày nhẹ.'),
    )),
    'giaydep': dict(icon='🥿', text='Khách nhất định không cởi giày vì "dép của nhà mình dính đầy vi khuẩn", đi giày bùn lên sàn gỗ.', opts=(
        ('moi', 'Đưa đôi dép mới còn nguyên bao (1 xu)', 5, 1, '', 'Lễ tân đưa bạn đôi dép mới còn nguyên bao.'),
        ('lau', 'Thôi kệ, lát lau sàn sau', 1, 0, '', 'Lễ tân để bạn đi giày lên phòng.'),
        ('quat', 'Quát khách cởi giày ngay', -9, 0, '', 'Lễ tân quát bạn cởi giày giữa sảnh. Ngại muốn độn thổ.'),
    )),
}

# ---------------------------------------------------------------- the night (they come by themselves)
EVENTS = {
    'karaoke': dict(icon='🎤', text='Khách gọi xuống: phòng bên hát "Em của ngày hôm qua" lần thứ 7, giọng lạc cả tông.', opts=(
        ('nhac', 'Sang gõ cửa nhắc phòng bên nhỏ tiếng', 5, 0, '', 'Lễ tân sang nhắc phòng bên. Yên hẳn.'),
        ('nut', 'Mang lên đôi nút bịt tai và ly sữa ấm (1 xu)', 3, 1, '', 'Lễ tân mang lên nút bịt tai và ly sữa ấm.'),
        ('lo', 'Giả vờ không nghe máy', -10, 0, '', 'Gọi mãi không ai bắt máy. Phòng bên hát tới bài thứ 9.'),
    )),
    'theto': dict(icon='🔑', text='Khách làm mất thẻ phòng, đứng ngoài hành lang quấn mỗi cái khăn tắm.', opts=(
        ('mo', 'Chạy lên mở cửa ngay, làm thẻ mới (3 xu)', 6, 3, '', 'Lễ tân chạy lên mở cửa ngay, đưa thẻ mới.'),
        ('phat', 'Mở cửa, nhưng ghi phạt 50 xu vào hóa đơn', -8, 0, '', 'Lễ tân mở cửa rồi dọa phạt 50 xu. Bạn tức anh ách.'),
        ('cho', 'Bảo khách chờ chút, đang dở tập phim', -12, 0, '', 'Bạn đứng ngoài hành lang bằng cái khăn tắm 20 phút.'),
    )),
    'maylanh': dict(icon='❄️', text='Máy lạnh kêu như máy cày, còn nhỏ nước tong tỏng xuống gối.', opts=(
        ('tho', 'Gọi thợ lên sửa ngay (5 xu)', 7, 5, '', 'Thợ lên sửa máy lạnh ngay trong đêm.'),
        ('quat', 'Mang quạt cây lên dùng tạm', 3, 0, '', 'Lễ tân mang quạt cây lên dùng tạm.'),
        ('ontrang', 'Bảo khách tiếng ồn trắng giúp ngủ ngon', -6, 0, '', 'Lễ tân bảo tiếng máy lạnh là "tiếng ồn trắng". Bạn trằn trọc.'),
    )),
    'gian': dict(icon='🪳', text='Khách hét thất thanh: có con gián to bằng ngón cái đang nhìn mình từ trên rèm.', opts=(
        ('bat', 'Lên bắt gián, xịt thuốc, xin lỗi rối rít', 6, 0, '', 'Lễ tân lên bắt gián, xịt thuốc, xin lỗi rối rít.'),
        ('doi', 'Đổi ngay sang phòng khác', 4, 0, '', 'Lễ tân đổi bạn sang phòng khác.'),
        ('canh', 'Bảo đó là "gián cảnh", nuôi cho có không khí', -8, 0, '', 'Lễ tân bảo đó là gián cảnh. Bạn ngủ ôm dép.'),
    )),
    'wifi': dict(icon='📶', text='Khách than wifi chậm, đang livestream bán quần áo thì đứng hình, khách hàng bỏ đi hết.', opts=(
        ('modem', 'Khởi động lại modem, đưa mật khẩu mạng tầng trên', 5, 0, '', 'Lễ tân khởi động lại modem, mạng chạy vù vù.'),
        ('4g', 'Tặng gói 4G một ngày (2 xu)', 6, 2, '', 'Lễ tân tặng bạn gói 4G một ngày.'),
        ('sach', 'Khuyên khách đọc sách cho thư giãn', -4, 0, '', 'Lễ tân khuyên bạn đọc sách. Đơn hàng bay hết.'),
    )),
    'shipper': dict(icon='🛵', text='Shipper giao 3 túi trà sữa cho khách lúc khách đang ngủ, bấm chuông inh ỏi cả dãy.', opts=(
        ('nhan', 'Nhận hộ, cất tủ lạnh, nhắn khách', 6, 0, '', 'Lễ tân nhận trà sữa hộ, cất tủ lạnh cho bạn.'),
        ('goi', 'Gõ cửa gọi khách dậy nhận', -3, 0, '', 'Lễ tân gõ cửa gọi bạn dậy nhận trà sữa.'),
        ('tra', 'Bảo shipper mang về', -6, 0, '', 'Shipper mang trà sữa về. Sáng dậy bạn thấy mất đơn.'),
    )),
    'nuoclanh': dict(icon='🚿', text='Vòi sen chỉ ra nước lạnh, khách run cầm cập gọi xuống, giọng như sắp khóc.', opts=(
        ('binh', 'Bật lại bình nóng lạnh, xin lỗi', 5, 0, '', 'Lễ tân bật lại bình nóng lạnh, nước ấm ngay.'),
        ('xach', 'Đun nước nóng xách lên tận phòng (1 xu)', 7, 1, '', 'Lễ tân xách hẳn xô nước nóng lên tận phòng.'),
        ('khoe', 'Bảo tắm nước lạnh tốt cho sức khỏe', -8, 0, '', 'Lễ tân bảo tắm lạnh tốt cho sức khỏe. Bạn hắt hơi cả đêm.'),
    )),
    'saurieng': dict(icon='🍈', text='Khách phàn nàn cả tầng thơm mùi sầu riêng: phòng bên vừa mang về nguyên trái.', opts=(
        ('thom', 'Mở cửa sổ, xịt thơm, mang ấm trà gừng (1 xu)', 5, 1, '', 'Lễ tân mở cửa sổ, xịt thơm, mang ấm trà gừng.'),
        ('cat', 'Nhắc phòng bên cất sầu riêng ra ngoài', 4, 0, '', 'Lễ tân nhắc phòng bên mang sầu riêng ra ngoài.'),
        ('an', 'Rủ khách sang ăn chung cho vui', -3, 0, '', 'Lễ tân rủ bạn sang ăn sầu riêng chung. Bạn ghét sầu riêng.'),
    )),
    'mat_dien': dict(icon='🕯️', text='Cúp điện cả dãy lúc 11 giờ đêm, khách gọi hỏi "nhà mình có máy phát không?"', opts=(
        ('den', 'Mang đèn sạc và quạt tay lên từng phòng (2 xu)', 6, 2, '', 'Lễ tân mang đèn sạc và quạt tay lên tận phòng.'),
        ('bao', 'Gọi điện lực, báo khách giờ có điện lại', 3, 0, '', 'Lễ tân gọi điện lực và báo giờ có điện lại.'),
        ('tat', 'Tắt máy đi ngủ luôn', -9, 0, '', 'Không ai trả lời. Bạn ngồi trong bóng tối quạt bằng dép.'),
    )),
    'cai_nhau': dict(icon='💢', couple=True, text='Hai vị khách phòng đôi cãi nhau to vì "ai quên mang sạc", phòng bên gọi phàn nàn.', opts=(
        ('trag', 'Mang lên hai ly trà gừng, nói nhỏ nhẹ (1 xu)', 6, 1, '', 'Lễ tân mang lên hai ly trà gừng, nói nhỏ nhẹ. Hai bạn làm hòa.'),
        ('sac', 'Cho mượn luôn cục sạc của quầy', 5, 0, '', 'Lễ tân cho mượn cục sạc. Hết cãi.'),
        ('duoi', 'Dọa mời cả hai ra khỏi phòng', -10, 0, '', 'Lễ tân dọa mời hai bạn ra khỏi phòng. Cả hai cùng giận… lễ tân.'),
    )),
    'hoa_hong': dict(icon='🌹', couple=True, text='Khách nhắn: "Tối nay kỷ niệm, rải giúp mình cánh hoa hồng lên giường được không?" Đang 12 giờ đêm.', opts=(
        ('rai', 'Chạy đi mua hoa, rải thành hình trái tim (4 xu)', 8, 4, '', 'Lễ tân rải cánh hoa hồng thành hình trái tim trên giường.'),
        ('khan', 'Gấp khăn tắm thành hai con thiên nga', 5, 0, '', 'Lễ tân gấp khăn thành đôi thiên nga. Dễ thương ghê.'),
        ('khong', 'Bảo giờ này hết hoa rồi', -4, 0, '', 'Lễ tân bảo hết hoa rồi. Hơi tiếc.'),
    )),
}

# ---------------------------------------------------------------- what the guest player asks (at most ASK_MAX a stay)
ASKS = {
    'late': dict(icon='🕑', ask='Xin trả phòng muộn 1 tiếng', text='Khách hỏi: "Cho mình trả phòng muộn thêm 1 tiếng nha, mình đang ngủ ngon quá."', opts=(
        ('ok', 'Đồng ý, miễn phí', 6, 0, 'late', 'Chủ nhà đồng ý cho trả phòng muộn 1 tiếng.'),
        ('nhac', 'Đồng ý, nhưng nhắc rõ: đúng giờ là đúng giờ', 3, 0, 'late', 'Chủ nhà cho muộn 1 tiếng, dặn đúng giờ nhé.'),
        ('khong', 'Từ chối: phòng có khách mới', -4, 0, '', 'Chủ nhà từ chối: phòng có khách mới.'),
    )),
    'upgrade': dict(icon='⬆️', ask='Xin nâng hạng phòng miễn phí', text='Khách nài: "Nâng hạng phòng miễn phí đi, mình review 5 sao liền, thề!"', opts=(
        ('nang', 'Nâng hạng miễn phí (dọn phòng xịn: 4 xu)', 8, 4, 'upgrade', 'Chủ nhà nâng hạng phòng cho bạn, miễn phí!'),
        ('traicay', 'Không nâng, tặng đĩa trái cây (2 xu)', 4, 2, '', 'Không nâng hạng, nhưng có đĩa trái cây mát lạnh.'),
        ('khong', 'Từ chối lịch sự', -2, 0, '', 'Chủ nhà từ chối lịch sự.'),
    )),
    'pet': dict(icon='🐶', ask='Xin mang thú cưng vào', text='Khách hỏi: "Cho mình mang bé cún vào nha, bé ngoan lắm." (Bé đang cắn dở chiếc dép của nhà.)', opts=(
        ('cho', 'Cho mang, thêm tấm lót và bát nước', 6, 0, '', 'Chủ nhà cho bé vào, còn có tấm lót và bát nước.'),
        ('san', 'Cho bé ở sân sau có mái che', 3, 0, '', 'Bé được ở sân sau có mái che.'),
        ('cam', 'Không nhận thú cưng', -5, 0, '', 'Chủ nhà không nhận thú cưng. Bé ngồi trong xe cả đêm.'),
    )),
    'goi': dict(icon='🧸', ask='Xin thêm gối, khăn, gấu bông', text='Khách xin thêm 4 cái gối, 3 cái khăn và "một con gấu bông để ôm, ở nhà quen rồi".', opts=(
        ('du', 'Mang đủ lên, kể cả gấu bông (2 xu)', 6, 2, '', 'Chủ nhà mang đủ gối, khăn, kể cả một chú gấu bông.'),
        ('vua', 'Mang gối với khăn, gấu bông thì chịu', 3, 0, '', 'Có thêm gối với khăn, gấu bông thì không.'),
        ('khong', 'Bảo phòng đã đủ đồ rồi', -4, 0, '', 'Chủ nhà bảo phòng đã đủ đồ.'),
    )),
    'mi': dict(icon='🍜', ask='Đói, xin tô mì lúc nửa đêm', text='1 giờ sáng khách gọi: "Có mì tôm không? Cho mình thêm trứng với xúc xích nha."', opts=(
        ('nau', 'Nấu tô mì đặc biệt mang lên (2 xu)', 6, 2, '', 'Chủ nhà nấu tô mì trứng xúc xích mang lên tận phòng.'),
        ('chi', 'Chỉ đường ra tiệm tạp hóa 24 giờ', 1, 0, '', 'Chủ nhà chỉ đường ra tiệm tạp hóa 24 giờ.'),
        ('dong', 'Nói bếp đóng rồi', -4, 0, '', 'Bếp đóng rồi. Bạn ôm bụng đói đi ngủ.'),
    )),
    'on': dict(icon='🔊', ask='Phàn nàn phòng bên ồn', text='Khách nhắn: "Phòng bên đang xem đá banh, cứ 5 phút lại hét VÀOOO!"', opts=(
        ('nhac', 'Sang nhắc phòng bên nhỏ tiếng', 5, 0, '', 'Chủ nhà sang nhắc phòng bên. Yên rồi.'),
        ('doi', 'Đổi khách sang phòng cuối dãy', 6, 0, '', 'Chủ nhà đổi bạn sang phòng cuối dãy yên tĩnh.'),
        ('ke', 'Bảo khách xem cùng cho vui', -6, 0, '', 'Chủ nhà bảo bạn xem đá banh cùng cho vui.'),
    )),
}

# ---------------------------------------------------------------- leaving (check-out)
CHECKOUT = {
    'minibar': dict(icon='🥤', text='Khách thề chưa đụng lon nước nào, nhưng minibar trống trơn, vỏ lon nằm đầy thùng rác.', opts=(
        ('qua', 'Bỏ qua, coi như quà của nhà', 4, 0, '', 'Chủ nhà bỏ qua minibar, coi như quà.'),
        ('kiem', 'Nhẹ nhàng mời khách cùng kiểm tra', 1, 0, '', 'Chủ nhà mời bạn cùng kiểm tra minibar.'),
        ('cai', 'Cãi tới cùng giữa sảnh', -8, 0, '', 'Chủ nhà cãi tay đôi với bạn giữa sảnh.'),
    )),
    'khan': dict(icon='🧺', text='Thiếu 2 khăn tắm. Từ vali khách ló ra một góc khăn in tên nhà mình.', opts=(
        ('tang', 'Cười: tặng khách làm kỷ niệm (2 xu)', 4, 2, '', 'Chủ nhà cười, tặng bạn khăn làm kỷ niệm.'),
        ('nhac', 'Nhỏ nhẹ nhắc khách để lại', 2, 0, '', 'Chủ nhà nhắc nhỏ, bạn đỏ mặt trả khăn.'),
        ('la', 'Lớn tiếng giữa sảnh cho mọi người nghe', -8, 0, '', 'Chủ nhà nói to giữa sảnh. Ai cũng quay lại nhìn.'),
    )),
    'vali': dict(icon='🧳', text='Khách xin gửi vali tới tối mới lấy, "tiện thể gửi luôn con mèo".', opts=(
        ('giu', 'Nhận giữ cả vali lẫn mèo, ghi phiếu cẩn thận', 5, 0, '', 'Chủ nhà giữ giúp vali và cả bé mèo.'),
        ('vali', 'Giữ vali, mèo thì xin kiếu', 2, 0, '', 'Chủ nhà giữ vali, mèo thì bạn tự ôm theo.'),
        ('khong', 'Không nhận giữ đồ', -5, 0, '', 'Chủ nhà không nhận giữ đồ.'),
    )),
    'review': dict(icon='⭐', text='Khách hỏi: "Cho 5 sao thì lần sau được giảm giá không anh?"', opts=(
        ('that', 'Cảm ơn, nói thật: không đổi sao lấy giảm giá', 3, 0, '', 'Chủ nhà cảm ơn, nói thật không đổi sao lấy giảm giá.'),
        ('nuoc', 'Hẹn lần sau tặng chai nước', 2, 0, '', 'Chủ nhà hẹn lần sau tặng bạn chai nước.'),
        ('nan', 'Năn nỉ khách cho 5 sao', -3, 0, '', 'Chủ nhà năn nỉ bạn cho 5 sao. Hơi ngại.'),
    )),
    'hoadon': dict(icon='🧾', text='Khách đòi xuất hóa đơn công ty, tên công ty dài 3 dòng, mã số thuế đọc sai 2 lần.', opts=(
        ('ghi', 'Kiên nhẫn ghi lại, đọc to xác nhận từng số', 5, 0, '', 'Chủ nhà kiên nhẫn ghi đúng từng số trên hóa đơn.'),
        ('mail', 'Hẹn gửi qua email sau', 1, 0, '', 'Chủ nhà hẹn gửi hóa đơn qua email.'),
        ('khong', 'Bảo nhà nhỏ không xuất hóa đơn', -5, 0, '', 'Chủ nhà bảo không xuất hóa đơn được.'),
    )),
}

# texts of the stay's moments, shown to both
MISSED = 'Không ai trả lời. Khách chờ mãi.'
AUTO_OUT = 'Không ai làm thủ tục trả phòng, khách tự để thẻ phòng ở quầy rồi đi.'
