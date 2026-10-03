"""🎲 Quầy của bạn: the tricky moments of a day at your own counter (game/quay_self.py).

Owner 03/10: "nhiều cái oái oăm như các game khác … thêm chỗ đó nhiều vào", with gentle stakes. Each moment has 2-3
choices, none of them a trap: the kind one costs a little and wins the street's heart, the careful one is safe, the
quick one gambles a little. Outcomes are fixed per choice, sometimes with a seeded coin (the same day, the same
counter: the same result). Effects, all small and capped per day by game/quay_self.py:

    m   money in units of the counter's average price (+ sold, − spent or lost)
    b   customers more (or fewer) for the rest of the day (sold only if the stock and the hands allow)
    r   reputation (the counter's 90..110)
    s   online stars: +1 a happy 5-star review, -1 a 2-star one (each unit one review)
    k   goods bought in a hurry: the day's stock grows by k (paid by its m)
    t   the line the player reads

`when`: the day must have it ('online' selling on, 'rain', 'staff' hired, 'power' a stall or a kiosk, 'tu' a fridge).
A pick's outcomes are [(weight, effect)]; an outcome with `need` only counts when the counter has that item.
"""
from __future__ import annotations

E = dict   # an outcome


def ev(id, emoji, title, text, picks, when=()):
    return dict(id=id, emoji=emoji, title=title, text=text, when=frozenset(when), picks=picks)


EVENTS = [
    ev('thieu_mon', '🧾', 'Khách bảo thiếu món', 'Chị khách quay lại: “Túi thiếu một món nè em.”', [
        ('lam_bu', 'Làm bù ngay', [(1, E(m=-0.5, r=1, s=1, t='Chị cười: “Lần sau chị ghé tiếp.”'))]),
        ('xem_lai', 'Xem lại hóa đơn', [(1, E(r=1, t='Hóa đơn đủ món, chị để quên trên xe. Hai bên cười xòa.')),
                                        (1, E(m=-0.5, t='Thiếu thật. Bạn làm bù, chị vui.'))]),
        ('tu_choi', 'Nói là đã đủ', [(1, E(r=-2, s=-1, t='Chị phụng phịu bỏ đi.'))]),
    ]),
    ev('bom_hang', '📦', 'Bom hàng', 'Đơn trả khi nhận: khách không nghe máy, không nhận hàng.', [
        ('ban_lai', 'Mang về bán lại', [(1, E(m=-0.5, t='Bán lại cho khách đi ngang, lỗ chút phí.'))]),
        ('hen_lai', 'Nhắn khách hẹn giờ khác', [(1, E(t='Khách xin lỗi, hẹn chiều nhận.')), (1, E(m=-1, t='Khách im lặng. Lỗ tiền hàng.'))]),
        ('bao_app', 'Báo app, bỏ qua', [(1, E(m=-1, t='App ghi nhận: khách này lần sau phải trả trước.'))]),
    ], when=('online',)),
    ev('ck_gia', '📱', 'Ảnh chuyển khoản lạ', 'Khách đưa ảnh đã chuyển khoản, mà app ngân hàng chưa báo tiền vào.', [
        ('kiem_tra', 'Mở app kiểm tra', [(1, E(t='Chưa có tiền. Khách lúng túng rồi trả tiền mặt.'))]),
        ('tin', 'Tin khách, đưa hàng', [(1, E(m=-2, t='Ảnh giả rồi. Mất một phần, rút kinh nghiệm.'))]),
        ('tien_mat', 'Nhờ trả tiền mặt', [(1, E(r=-1, t='Khách trả tiền mặt, hơi phật ý.'))]),
    ]),
    ev('mua_dong', '🌧️', 'Mưa to, khách đụt mưa', 'Mưa ào xuống, cả chục người đứng trú trước quầy.', [
        ('ban_them', 'Làm nhanh, mời mua', [(1, E(b=3, t='Bán thêm được cả mớ!'))]),
        ('tang_tra', 'Mời trú, tặng ly trà nóng', [(1, E(m=-1, r=2, b=1, t='Ai cũng nhớ cái quầy dễ thương.'))]),
        ('keo_bat', 'Kéo bạt che cho rộng', [(1, E(b=2, t='Bạt rộng, khách đứng thoải mái, mua luôn.'))]),
    ], when=('rain',)),
    ev('het_hang', '🥡', 'Hết nguyên liệu giữa giờ đông', 'Món bán chạy nhất hết sạch, khách vẫn xếp hàng.', [
        ('chay_cho', 'Chạy chợ mua gấp', [(1, E(m=-1, k=3, t='Kịp mua về, không mất khách nào.'))]),
        ('goi_y', 'Gợi ý món khác', [(1, E(b=-1, t='Đa số khách đổi món vui vẻ.'))]),
        ('treo_bang', 'Treo bảng “tạm hết”', [(1, E(b=-2, t='Vài khách tiếc, hẹn mai quay lại.'))]),
    ]),
    ev('doi_thu', '🏪', 'Quầy mới mở sát bên', 'Quầy bên cạnh dán bảng “giảm 20%”.', [
        ('giu_gia', 'Giữ giá, chăm khách', [(1, E(b=-1, r=1, t='Khách quen vẫn ghé vì bạn cười tươi.'))]),
        ('giam_theo', 'Giảm giá theo', [(1, E(m=-1, b=1, t='Đông hơn chút nhưng lời mỏng.'))]),
        ('tang_kem', 'Tặng kèm món nhỏ', [(1, E(m=-0.5, r=2, t='Khách thích quà nhỏ, khen quầy.'))]),
    ]),
    ev('kiem_tra', '🧑‍⚕️', 'Đoàn kiểm tra vệ sinh', 'Hai cán bộ ghé xem quầy có sạch sẽ, an toàn không.', [
        ('moi_xem', 'Mời xem tự nhiên', [(1, E(need='tu', r=2, t='Tủ mát sạch tinh. Được khen!')),
                                         (2, E(r=1, t='Đạt! Đoàn dặn giữ sạch như vầy.')),
                                         (1, E(m=-1, t='Nhắc nhở nhỏ: mua thêm hộp đậy đồ.'))]),
        ('lau_don', 'Xin 5 phút lau dọn', [(1, E(m=-0.3, r=1, t='Lau xong mời xem. Đạt!'))]),
        ('hen', 'Xin hẹn hôm khác', [(1, E(r=-1, t='Đoàn ghi chú, hẹn lần sau.'))]),
    ]),
    ev('ship_tre', '🛵', 'Shipper tới trễ', 'Shipper nhắn: kẹt xe, trễ 20 phút.', [
        ('tu_giao', 'Tự chạy đi giao', [(1, E(b=-1, s=1, t='Khách nhận còn nóng, cho 5 sao.'))]),
        ('xin_loi', 'Nhắn khách xin lỗi, tặng mã', [(1, E(m=-0.5, t='Khách thông cảm, cảm ơn mã giảm.'))]),
        ('cho', 'Cứ chờ', [(1, E(s=-1, t='Khách chờ lâu, hơi buồn.'))]),
    ], when=('online',)),
    ev('sai_dia_chi', '📍', 'Sai địa chỉ', 'Khách ghi nhầm số nhà, shipper gọi hỏi.', [
        ('goi_khach', 'Gọi khách hỏi lại', [(1, E(t='Hỏi lại xong, giao đúng chỗ.'))]),
        ('giao_cu', 'Giao theo địa chỉ cũ', [(1, E(m=-1, s=-1, t='Giao nhầm nhà. Phải làm lại đơn.'))]),
        ('huy', 'Hủy đơn, hoàn tiền', [(1, E(m=-0.5, t='Hoàn tiền gọn gàng.'))]),
    ], when=('online',)),
    ev('ngoai_menu', '💡', 'Món ngoài menu', 'Khách hỏi: “Làm giúp mình món này được không?”', [
        ('lam_thu', 'Làm thử cho khách', [(7, E(m=1, r=1, t='Khách mê, hẹn quay lại.')), (3, E(m=-0.3, t='Không hợp vị, bạn không lấy tiền.'))]),
        ('goi_y', 'Gợi ý món gần giống', [(1, E(m=0.5, t='Khách chịu liền.'))]),
        ('hen', 'Xin lỗi, hẹn lần sau', [(1, E(t='Khách gật đầu, mua món quen.'))]),
    ]),
    ev('van_phong', '🏢', 'Văn phòng đặt 10 phần', 'Văn phòng gần đó gọi đặt 10 phần cho buổi họp.', [
        ('nhan', 'Nhận ngay', [(1, E(b=5, t='Cả văn phòng khen, hẹn đặt tiếp.'))]),
        ('nhan_tre', 'Nhận, xin giao trễ 30 phút', [(1, E(b=3, r=-1, t='Họ hơi sốt ruột nhưng vẫn vui.'))]),
        ('tu_choi', 'Từ chối lịch sự', [(1, E(t='Họ hiểu, hẹn lần khác.'))]),
    ]),
    ev('review_xau', '⭐', 'Đánh giá 1 sao lạ', 'Một tài khoản mới tạo chê quầy 1 sao. Có vẻ là người của quầy khác.', [
        ('tra_loi', 'Trả lời nhẹ nhàng, kèm ảnh thật', [(1, E(r=1, s=1, t='Khách khác thấy bạn đàng hoàng.'))]),
        ('bao_app', 'Báo app xem xét', [(3, E(t='App gỡ đánh giá giả.')), (2, E(s=-1, t='App chưa gỡ, điểm tụt chút.'))]),
        ('ke', 'Kệ thôi', [(1, E(s=-1, t='Điểm tụt chút xíu.'))]),
    ], when=('online',)),
    ev('ghi_so', '📒', 'Khách quen xin ghi sổ', 'Chú Sáu quên ví: “Ghi sổ giúp chú, chiều chú trả.”', [
        ('ghi', 'Ghi sổ cho chú', [(4, E(m=0.2, r=1, t='Chiều chú trả đủ, còn cho thêm.')), (1, E(m=-1, t='Chú quên mất. Thôi coi như mời.'))]),
        ('moi', 'Mời chú luôn', [(1, E(m=-1, r=2, t='Chú cảm động, kể cả xóm nghe.'))]),
        ('tu_choi', 'Xin lỗi, quầy không ghi sổ', [(1, E(r=-1, t='Chú hơi ngại, đi về.'))]),
    ]),
    ev('lac_me', '🧒', 'Bé đi lạc', 'Một bé đứng khóc ở quầy, tìm không thấy mẹ.', [
        ('giu_be', 'Giữ bé lại, nhờ loa chợ gọi', [(1, E(b=-1, r=3, t='Mẹ bé chạy tới, cảm ơn rối rít.'))]),
        ('bao_ve', 'Nhờ bảo vệ gần đó', [(1, E(r=2, t='Bảo vệ dắt bé đi tìm mẹ.'))]),
        ('cho_nuoc', 'Cho bé ly nước, chờ cùng', [(1, E(m=-0.3, r=3, t='Bé nín khóc, mẹ tới, cả hai cười.'))]),
    ]),
    ev('cup_dien', '🔌', 'Cúp điện', 'Cả dãy phố cúp điện, đèn và tủ mát tắt.', [
        ('ban_nhe', 'Bán món không cần điện', [(1, E(b=-1, t='Vẫn bán được kha khá.'))]),
        ('nghi', 'Nghỉ chút chờ điện', [(1, E(b=-3, t='Một tiếng sau điện có lại.'))]),
        ('may_phat', 'Mượn máy phát hàng xóm', [(1, E(m=-1, t='Có điện chạy tiếp. Cảm ơn hàng xóm!'))]),
    ], when=('power',)),
    ev('hang_hong', '🥀', 'Lô hàng hỏng', 'Mở thùng hàng sáng nay, một phần bị hỏng.', [
        ('bo', 'Bỏ phần hỏng, nhập mới', [(1, E(m=-1.5, r=1, t='Hàng tươi ngon, khách yên tâm.'))]),
        ('loc', 'Lọc kỹ phần còn tốt', [(3, E(m=-0.5, t='Lọc kỹ, vẫn dùng được.')), (1, E(m=-0.5, r=-1, t='Có khách chê hơi kém.'))]),
        ('doi_tra', 'Gọi mối hàng đổi trả', [(3, E(t='Mối hàng đổi ngay, không mất gì.')), (2, E(m=-1, t='Mối hẹn mai đổi, hôm nay thiếu.'))]),
    ]),
    ev('tiktok', '📸', 'Có người quay TikTok', 'Một bạn trẻ quay quầy của bạn. Video lên xu hướng!', [
        ('tao_dang', 'Cười tươi, mời quay tiếp', [(1, E(b=4, r=1, t='Khách kéo tới xếp hàng!'))]),
        ('tang', 'Tặng bạn ấy một phần', [(1, E(m=-0.5, b=5, t='Video có cả món của bạn. Đông nghịt!'))]),
        ('ngai', 'Ngại, xin đừng quay', [(1, E(t='Bạn ấy xin lỗi rồi đi tiếp.'))]),
    ]),
    ev('tien_le', '💵', 'Két hết tiền lẻ', 'Khách đưa tờ tiền lớn, két không còn tiền lẻ.', [
        ('doi', 'Chạy sang quầy bên đổi', [(1, E(b=-1, t='Đổi được, khách chờ chút xíu.'))]),
        ('chuyen_khoan', 'Nhờ khách chuyển khoản', [(1, E(t='Chuyển xong trong vài giây.'))]),
        ('bot', 'Bớt cho khách tròn số', [(1, E(m=-0.3, r=1, t='Khách vui vì được bớt.'))]),
    ]),
    ev('to_tieng', '😤', 'Khách to tiếng đòi giảm', 'Một khách lớn tiếng đòi giảm giá trước hàng người.', [
        ('binh_tinh', 'Bình tĩnh, mời ly nước', [(1, E(r=1, t='Khách dịu lại, mua đúng giá.'))]),
        ('giam', 'Giảm cho xong chuyện', [(1, E(m=-0.5, t='Xong chuyện, mà ai cũng muốn giảm.'))]),
        ('bao_ve', 'Nhờ bảo vệ', [(1, E(b=-1, t='Bảo vệ mời khách đi, hàng người yên.'))]),
    ]),
    ev('nham_don', '🔄', 'Hai đơn bị tráo', 'Shipper giao nhầm hai đơn cho nhau.', [
        ('doi_lai', 'Gọi cả hai, đổi lại', [(1, E(t='Hai bên vui vẻ đổi cho nhau.'))]),
        ('lam_moi', 'Làm lại cả hai đơn', [(1, E(m=-1, s=1, t='Bù nhanh, khách cho 5 sao.'))]),
        ('bo_qua', 'Bỏ qua', [(1, E(s=-2, t='Hai khách chấm thấp.'))]),
    ], when=('online',)),
    ev('meo', '🐱', 'Mèo hoang lên quầy', 'Một chú mèo nhảy lên quầy nằm sưởi nắng.', [
        ('vuot', 'Vuốt mèo, cho ăn', [(1, E(m=-0.2, b=1, r=1, t='Khách chụp ảnh với mèo, vui ghê.'))]),
        ('be_ra', 'Bế ra chỗ mát', [(1, E(t='Mèo ngoan nằm dưới gầm quầy.'))]),
    ]),
    ev('khach_tay', '🌏', 'Khách nước ngoài', 'Một vị khách nước ngoài chỉ vào bảng, hỏi món nào ngon nhất.', [
        ('chi_mon', 'Chỉ món bán chạy, cười', [(1, E(m=1, t='Khách giơ ngón cái: “Very good!”'))]),
        ('app_dich', 'Dùng app dịch giải thích', [(1, E(m=1, r=1, t='Khách mua hai phần, chụp hình kỷ niệm.'))]),
    ]),
    ev('dat_tiec', '🎉', 'Đặt cho tiệc tối nay', 'Khách đặt trước cho buổi tiệc nhỏ tối nay.', [
        ('nhan', 'Nhận, làm kỹ', [(6, E(b=3, t='Tiệc vui, khách hẹn lần sau.')), (1, E(m=-1, t='Tiệc hoãn, khách bùng. Lỗ tiền làm.'))]),
        ('nhan_coc', 'Nhận, xin đặt cọc', [(1, E(b=3, t='Có cọc, yên tâm làm. Tiệc vui!'))]),
        ('tu_choi', 'Hôm nay kín rồi', [(1, E(t='Khách hẹn dịp khác.'))]),
    ]),
    ev('nv_om', '🤒', 'Nhân viên báo ốm', 'Bạn nhân viên nhắn: “Em sốt, xin nghỉ hôm nay.”', [
        ('cho_nghi', 'Cho nghỉ, mình làm thêm', [(1, E(b=-1, r=1, t='Bạn ấy cảm ơn, mai đi làm hăng hái.'))]),
        ('tien_thuoc', 'Cho nghỉ, gửi tiền thuốc', [(1, E(m=-1, r=2, t='Bạn ấy cảm động lắm.'))]),
        ('co_lam', 'Nhờ cố làm buổi sáng', [(1, E(r=-1, t='Bạn ấy làm mệt, hơi buồn.'))]),
    ], when=('staff',)),
    ev('xe_rac', '🚛', 'Xe rác đỗ trước quầy', 'Xe rác dừng ngay trước quầy đúng giờ đông khách.', [
        ('nho_dich', 'Nhờ bác tài dịch chút', [(1, E(m=0.5, t='Bác dịch xe, còn mua một phần.'))]),
        ('cho', 'Chờ xe đi', [(1, E(b=-1, t='Mười phút sau xe đi, khách quay lại.'))]),
    ]),
    ev('quen_vi', '👛', 'Khách bỏ quên ví', 'Khách đi rồi mới thấy cái ví để quên trên quầy.', [
        ('cat_ky', 'Cất kỹ, chờ khách quay lại', [(1, E(m=0.5, r=2, t='Khách quay lại, cảm ơn và mua thêm.'))]),
        ('dang_tin', 'Đăng tin tìm chủ', [(1, E(r=2, t='Chủ ví nhận lại, khen quầy thật thà.'))]),
    ]),
]
BY_ID = {e['id']: e for e in EVENTS}
assert len(BY_ID) == len(EVENTS)
