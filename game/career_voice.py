"""Each career's own words for the screens every career shares (the owner, 06/10: "nghề mỗi nghề mỗi khác, ví dụ
như nhà sư mà nó bảo shop"; "sửa mấy cách trò chuyện").

The shared shell (confirming a step, closing the day, the team sheet, promotion lines, the daily push, friends'
visits, the review reply strip) was written for a shop: "Xác nhận việc của tiệm", "Sổ tiệm", "Đội của tiệm",
"Khách quen boa thêm % doanh thu", "Quán đang chờ bạn mở cửa", "Chủ tiệm phục vụ", "Dạ tiệm cảm ơn bạn…". A monk, a
nurse or a police officer read the same words. Here every career has a row of terms (TERMS) and the non-shop careers
get their own review-reply texts (tone_rows). Shops keep exactly today's words (SHOP).

Wording only: tone ids (feedback_voices.TONE_ORDER), offer ids (feedback.OFFERS), persona ids, task generation and the
save shape stay the same. The pagoda keeps its own review voice (pagoda_voice.py) and the teacher its parent set.
`terms(career)` goes to the client in the catalogue (content.public_content: catalogue[i]['terms']), read by
public/js/v4/terms.js; its SHOP default there must equal SHOP here (tests/test_career_words.py).
"""
from __future__ import annotations

import re

# Words a non-shop career's shared text never uses (tests/test_career_words.py runs every rendered line through it).
SHOP_WORDS = re.compile(r'(?<!\w)(tiệm|quán|shop|cửa hàng|chủ quán|khách hàng|phục vụ|dịch vụ|doanh thu|voucher|'
                        r'hoàn tiền|ủng hộ quán|mới mở)(?!\w)', re.I)
# In-world words a career may still use (its own clients are shops, or the word is the job's own).
ALLOW = {
    'customer_care': ('khách hàng', 'voucher', 'hoàn tiền', 'dịch vụ'),   # a shop's call centre: those are its words
    'accounting': ('tiệm', 'dịch vụ'),                                     # keeps the books of small shops
    'tax_payroll': ('dịch vụ',),                                           # "Dịch vụ Thuế & Tiền lương Minh Bạch"
    'delivery': ('quán', 'tiệm', 'cửa hàng'),                              # picks up from the street's shops
}

# What a shop says (today's words). Every career starts from this row; a non-shop career overrides it.
SHOP = dict(
    commerce=True,
    place='tiệm', self='tiệm', people='khách', who='bạn', owner='chủ tiệm',
    served='khách đã phục vụ', record='phiếu', review='đánh giá', reply='trả lời',
    books='Sổ tiệm', rail_in='Trong tiệm', confirm='Xác nhận việc của tiệm',
    end_title='Khép ca hôm nay?', end_text='Lương, điện nước và tiền thuê ghi vào sổ tiệm để bạn trả sau.',
    team='Đội của tiệm', hire_board='Bảng tìm người phụ tiệm', hire='Mời về tiệm', calm='Hiên tiệm đang yên.',
    security='Chăm chút an ninh của tiệm', revenue='Doanh thu nghề', income='doanh thu', tip='Khách quen boa thêm', fund='Quỹ tiệm',
    daily='Quán đang chờ bạn mở cửa, khách quen đang chờ. Mở ca hôm nay nhé!',
    host='Chủ tiệm', by_owner='Chủ tiệm phục vụ', by_staff='Nhân viên phục vụ', rate='Chấm quán',
    invite_label='Mời quay lại', sorry_label='Xin lỗi + bù đắp', offer_field='Bù đắp',
    placeholder='Cảm ơn, xin lỗi nếu cần, và nói rõ tiệm sẽ làm gì…',
    offers=dict(drink='Quà nhỏ · 6 xu', gift='Voucher · 10 xu', refund='Hoàn 20 xu'),
)

# Short keys, one row per non-shop career. Missing keys are derived from `place` in _row().
_ROWS = {
    'accounting': dict(place='Góc Sổ Xinh', self='bên mình', people='khách thuê sổ', who='anh chị', owner='kế toán',
                       served='bộ sổ đã soát', record='chứng từ', review='nhận xét', books='Sổ văn phòng',
                       rail_in='Trong văn phòng', confirm='Xác nhận việc sổ sách', tip='Khách thuê sổ thưởng thêm',
                       daily='Chồng chứng từ đang chờ trên bàn. Vào ca soát sổ nhé!', invite_label='Mời trao đổi',
                       offers=dict(drink='Soát thêm một sổ · 6 xu', gift=None, refund='Giảm phí 20 xu'),
                       invite='Dạ {who} ghé văn phòng buổi chiều, mình ngồi soát lại từng chứng từ cho rõ ạ.',
                       process='Dạ bên mình soát theo thứ tự: chứng từ gốc, sổ chi, sao kê rồi mới ký. Hôm đó {fact} ạ.'),
    'customer_care': dict(place='tổng đài CSKH', self='bên mình', people='khách hàng', who='bạn', owner='nhân viên CSKH',
                          served='cuộc gọi đã nghe', record='lịch sử cuộc gọi', review='đánh giá CSKH', books='Sổ trực tổng đài',
                          rail_in='Ở tổng đài', confirm='Xác nhận việc ở tổng đài', invite_label='Mời liên hệ lại',
                          daily='Tổng đài sắp đổ chuông. Vào ca nghe máy nhé!',
                          offers=dict(drink='Quà nhỏ · 6 xu', gift='Voucher · 10 xu', refund='Hoàn tiền 20 xu'),
                          invite='Dạ {who} gọi lại tổng đài, đọc mã đơn là bên mình xử lý tiếp ngay ạ.',
                          process='Dạ bên mình đối soát mã đơn, ghi âm cuộc gọi rồi mới trả lời. Hôm đó {fact} ạ.'),
    'tour_guide': dict(place='đoàn', self='đoàn mình', people='khách đoàn', who='anh chị', owner='hướng dẫn viên',
                       served='khách đã dẫn', record='lịch trình', review='nhận xét chuyến đi', books='Sổ đoàn',
                       rail_in='Trên đường', confirm='Xác nhận việc của đoàn', tip='Khách đoàn gửi thêm tip',
                       daily='Đoàn khách sắp tới điểm hẹn. Xuất phát hôm nay nhé!', invite_label='Mời đi chuyến sau',
                       offers=dict(drink='Nước suối · 6 xu', gift='Ảnh tặng · 10 xu', refund=None),
                       invite='Chuyến sau {who} đi cùng, mình xin giữ chỗ đẹp và kể kỹ hơn ở điểm {who} thích ạ.',
                       process='Dạ đoàn đi theo lịch trình đã gửi, mỗi điểm có giờ tập trung. Hôm đó {fact} ạ.'),
    'delivery': dict(place='chuyến giao', self='mình', people='người nhận', who='anh chị', owner='tài xế',
                     served='đơn đã giao', record='ảnh giao hàng', review='đánh giá tài xế', books='Sổ chuyến',
                     rail_in='Trên đường', confirm='Xác nhận việc trên chuyến', tip='Người nhận bo thêm',
                     daily='Đơn mới đang chờ ở bưu cục. Lên xe chạy nhé!', invite_label='Hẹn giao lại',
                     offers=dict(drink=None, gift=None, refund='Hoàn phí ship 20 xu'),
                     invite='Lần sau {who} nhắn trước giờ nhận, mình canh giao đúng giờ đó ạ.',
                     process='Dạ mình giao theo thứ tự trên bản đồ tuyến, tới nơi là chụp ảnh lưu lại. Hôm đó {fact} ạ.'),
    'corp_accounting': dict(place='phòng kế toán', self='phòng mình', people='sếp và đối tác', who='anh chị',
                            owner='kế toán', served='hồ sơ đã xử lý', record='biên bản đối chiếu', review='nhận xét nội bộ',
                            books='Sổ công việc', rail_in='Trong văn phòng', confirm='Xác nhận việc của phòng',
                            daily='Hồ sơ mới đang chờ trên bàn. Vào ca nhé!', invite_label='Mời trao đổi',
                            offers=dict(drink='Mời cà phê · 6 xu', gift=None, refund=None),
                            invite='Dạ chiều nay {who} rảnh, em mang biên bản qua trao đổi trực tiếp cho rõ ạ.',
                            process='Dạ phòng làm theo quy trình: chứng từ gốc, đối chiếu, trình ký. Hôm đó {fact} ạ.'),
    'tax_payroll': dict(place='phòng lương', self='bên mình', people='người lao động', who='anh chị', owner='kế toán lương',
                        served='phiếu lương đã làm', record='bảng chấm công', review='phản ánh', books='Sổ công việc',
                        rail_in='Trong văn phòng', confirm='Xác nhận việc lương, thuế',
                        daily='Bảng chấm công mới đang chờ. Vào ca nhé!', invite_label='Mời trao đổi',
                        offers=dict(drink='Mời cà phê · 6 xu', gift=None, refund=None),
                        invite='Dạ {who} ghé phòng lương giờ hành chính, em mở bảng chấm công giải thích từng dòng ạ.',
                        process='Dạ lương tính từ bảng chấm công, trừ bảo hiểm và thuế rồi mới ra phiếu. Hôm đó {fact} ạ.'),
    'group_accounting': dict(place='ban hợp nhất', self='ban mình', people='công ty con và kiểm toán', who='anh chị',
                             owner='kế toán tập đoàn', served='hồ sơ đã xử lý', record='biên bản đối chiếu',
                             review='nhận xét nội bộ', books='Sổ công việc', rail_in='Trong văn phòng',
                             confirm='Xác nhận việc của ban', daily='Kỳ báo cáo đang chờ. Vào ca nhé!',
                             invite_label='Mời trao đổi', offers=dict(drink='Mời cà phê · 6 xu', gift=None, refund=None),
                             invite='Dạ {who} cho em xin lịch họp ngắn, mình rà lại bút toán loại trừ cùng nhau ạ.',
                             process='Dạ ban làm theo thứ tự: nhận số công ty con, đối chiếu nội bộ, loại trừ rồi mới hợp nhất. Hôm đó {fact} ạ.'),
    'garbage': dict(place='tổ thu gom', self='tổ', people='bà con', who='cô chú', owner='tổ trưởng',
                    served='hộ đã thu gom', record='sổ tuyến', review='phản ánh', reply='giải trình', books='Sổ tuyến',
                    rail_in='Trên tuyến', confirm='Xác nhận việc trên tuyến', tip='Bà con gửi thêm',
                    daily='Xe đẩy đã sẵn, ngõ sau đang chờ. Vào ca nhé!', invite_label='Hẹn thu bổ sung',
                    offers=dict(drink='Thu thêm một bao · 6 xu', gift=None, refund='Bớt 20 xu phí rác'),
                    invite='Dạ sáng mai tổ ghé sớm thu bổ sung, cô chú cứ để túi trước cửa ạ.',
                    process='Dạ tổ thu theo lịch từng ngõ, rác nguy hại để riêng, ghi vào sổ tuyến. Hôm đó {fact} ạ.'),
    'drain': dict(place='đội thợ chú Hai', self='thợ', people='chủ nhà', who='anh chị', owner='thợ',
                  served='nhà đã thông', record='sổ hẹn', review='lời chủ nhà', books='Sổ hẹn', rail_in='Trên xe đồ nghề',
                  confirm='Xác nhận việc thông cống', tip='Chủ nhà bo thêm',
                  daily='Điện thoại sắp reo, có nhà gọi thông cống. Nhận việc nhé!', invite_label='Hẹn quay lại',
                  offers=dict(drink=None, gift='Bảo hành thêm · 10 xu', refund='Bớt 20 xu tiền công'),
                  invite='Dạ còn nghẹt là {who} gọi, chú Hai với con quay lại thông tiếp, không tính thêm ạ.',
                  process='Dạ thợ báo giá trước, thông xong xả nước thử rồi mới nhận tiền. Hôm đó {fact} ạ.'),
    'homemaker': dict(place='nhà chị Thảo', self='con', people='cả nhà', who='chị', owner='người giúp việc',
                      served='việc nhà đã làm', record='sổ chợ', review='lời trong nhà', books='Sổ chợ',
                      rail_in='Trong nhà', confirm='Xác nhận việc nhà', tip='Chị Thảo thưởng thêm',
                      daily='Chị Thảo sắp dặn việc sáng nay. Vào làm nhé!', invite_label='Hỏi lại ý nhà',
                      offers=dict(drink='Chè tráng miệng · 6 xu', gift=None, refund=None),
                      invite='Dạ tối nay chị rảnh, con xin hỏi lại ý cả nhà để mai làm cho đúng ạ.',
                      process='Dạ con làm theo sổ tay nhà: đi chợ, nấu, dọn rồi ghi sổ chợ từng khoản. Hôm đó {fact} ạ.'),
    'giupviec': dict(place='tổ Nhà Thơm', self='em', people='gia chủ', who='anh chị', owner='người giúp việc',
                     served='nhà đã dọn', record='ảnh em gửi', review='nhận xét gia chủ', reply='nhắn lại', books='Sổ tổ',
                     rail_in='Ở tổ', confirm='Xác nhận việc dọn nhà', tip='Gia chủ bo thêm',
                     daily='Lịch hẹn dọn nhà sắp tới giờ. Lên đường nhé!', invite_label='Hẹn buổi sau',
                     offers=dict(drink='Làm thêm 15 phút · 6 xu', gift=None, refund='Bớt 20 xu tiền công'),
                     invite='Dạ {who} đặt lịch tuần sau, em xin làm góc {who} dặn trước tiên ạ.',
                     process='Dạ tổ Nhà Thơm dọn từ trên xuống, khô trước ướt sau, nên nhà tắm luôn để cuối ạ.'),
    'naucom': dict(place='bếp nhà khách quen', self='con', people='gia đình', who='cô chú', owner='người nấu',
                   served='bữa cơm đã nấu', record='sổ chợ', review='lời nhà', books='Sổ chợ', rail_in='Trong bếp',
                   confirm='Xác nhận việc bếp', tip='Các nhà quen bo thêm',
                   daily='Cô Hạnh nhắn thực đơn hôm nay. Vào bếp nhé!', invite_label='Hỏi lại thực đơn',
                   offers=dict(drink='Món tráng miệng · 6 xu', gift=None, refund=None),
                   invite='Dạ mai con ghé sớm, cô chú dặn món gì con nấu đúng món đó ạ.',
                   process='Dạ con đi chợ theo thực đơn nhà dặn, giữ hóa đơn, nấu xong nếm lại mới dọn ạ. Hôm đó {fact} ạ.'),
    'babysitter': dict(place='tổ Mèo Con', self='cô', people='ba mẹ bé', who='anh chị', owner='cô bảo mẫu',
                       served='buổi trông bé', record='nhật ký bé', review='nhận xét phụ huynh', books='Sổ trông bé',
                       rail_in='Trong nhà', confirm='Xác nhận việc trông bé', tip='Ba mẹ bé gửi thêm',
                       daily='Ba mẹ bé sắp tới gửi bé. Vào trông bé nhé!', invite_label='Mời trao đổi',
                       offers=dict(drink='Kể thêm truyện · 6 xu', gift=None, refund='Bớt 20 xu tiền công'),
                       invite='Dạ chiều nay anh chị đón bé sớm chút, cô kể kỹ từng việc trong ngày của bé ạ.',
                       process='Dạ cô làm theo giấy dặn của ba mẹ, việc gì cũng ghi vào nhật ký bé. Hôm đó {fact} ạ.'),
    'library': dict(place='thư viện', self='thư viện', people='bạn đọc', who='bạn', owner='thủ thư',
                    served='lượt bạn đọc', record='sổ mượn trả', review='góp ý của bạn đọc', reply='phản hồi',
                    books='Sổ thư viện', rail_in='Trong thư viện', confirm='Xác nhận việc thư viện',
                    tip='Phường thưởng thêm', daily='Ông Thạc đã đứng chờ ngoài cửa. Mở cửa thư viện nhé!',
                    invite_label='Mời ghé đọc', offers=dict(drink='Gia hạn miễn phí · 6 xu', gift='Sách tặng · 10 xu', refund=None),
                    invite='Mời {who} ghé phòng đọc, thủ thư giữ sẵn cuốn {who} cần ở quầy mượn trả ạ.',
                    process='Dạ thư viện làm theo nội quy: thẻ đọc, sổ mượn trả, sách về là xếp đúng ký hiệu. Hôm đó {fact} ạ.'),
    'pilot': dict(place='tổ bay', self='tổ bay', people='hành khách', who='quý khách', owner='cơ trưởng',
                  served='chặng đã bay', record='nhật ký bay', review='nhận xét sau chuyến', reply='phản hồi',
                  books='Sổ bay', rail_in='Ở sân bay', confirm='Xác nhận trước khi làm',
                  daily='Chặng bay đầu ngày sắp tới giờ. Báo danh nhé!', invite_label='Mời bay chuyến sau',
                  offers=dict(drink=None, gift=None, refund=None),
                  invite='Tổ bay mong được đón {who} ở chuyến sau, êm hơn chuyến này ạ.',
                  process='Dạ tổ bay làm theo bảng kiểm từng bước, an toàn đặt trước giờ giấc. Hôm đó {fact} ạ.'),
    'flight_attendant': dict(place='khoang khách', self='tổ tiếp viên', people='hành khách', who='quý khách',
                             owner='tiếp viên', served='hành khách đã chăm', record='phiếu suất ăn',
                             review='nhận xét sau chuyến', reply='phản hồi', books='Sổ tiếp viên', rail_in='Ở sân bay',
                             confirm='Xác nhận trước khi làm', daily='Khách chuyến sau đang xếp hàng ở cổng. Vào ca nhé!',
                             invite_label='Mời bay chuyến sau', offers=dict(drink=None, gift=None, refund=None),
                             invite='Tổ tiếp viên mong được chăm {who} ở chuyến sau chu đáo hơn ạ.',
                             process='Dạ tổ tiếp viên làm theo quy định hãng, kiểm chéo trước khi cất cánh. Hôm đó {fact} ạ.'),
    'oil': dict(place='giàn', self='tổ ca', people='đồng nghiệp trên giàn', who='anh', owner='thợ trong tổ ca',
                served='ca đã làm', record='sổ ca', review='đánh giá ca', reply='phản hồi', books='Sổ lương',
                rail_in='Trên giàn', confirm='Xác nhận trước khi làm', daily='Họp an toàn đầu ca sắp bắt đầu. Vào ca nhé!',
                invite_label='Mời họp ca', offers=dict(drink=None, gift=None, refund=None),
                invite='Đầu ca sau mời {who} ngồi họp an toàn cùng, mình nói rõ việc hôm đó.',
                process='Dạ tổ ca làm theo giấy phép làm việc, thử khí xong mới bắt tay vào. Hôm đó {fact} ạ.'),
    'hr_admin': dict(place='phòng HC-NS', self='phòng mình', people='nhân viên và ứng viên', who='anh chị',
                     owner='nhân sự', served='hồ sơ đã xử lý', record='hồ sơ nhân sự', review='phản ánh nội bộ',
                     reply='phản hồi', books='Sổ công việc', rail_in='Trong văn phòng', confirm='Xác nhận việc của phòng',
                     daily='Hồ sơ mới đang chờ trên bàn. Vào ca nhé!', invite_label='Mời trao đổi',
                     offers=dict(drink='Mời cà phê · 6 xu', gift=None, refund=None),
                     invite='Dạ {who} ghé phòng HC-NS giờ nghỉ trưa, em mở hồ sơ trao đổi riêng ạ.',
                     process='Dạ hồ sơ đi qua ba bước: nhận đủ giấy tờ, kiểm, trình ký. Hôm đó {fact} ạ.'),
    'secretary': dict(place='văn phòng giám đốc', self='em', people='sếp và khách của sếp', who='anh chị',
                      owner='thư ký', served='việc đã xong', record='sổ ghi điện thoại', review='nhận xét của sếp',
                      reply='phản hồi', books='Sổ công việc', rail_in='Trong văn phòng', confirm='Xác nhận việc văn phòng',
                      daily='Lịch họp hôm nay đang chờ. Vào ca nhé!', invite_label='Mời trao đổi',
                      offers=dict(drink='Mời cà phê · 6 xu', gift=None, refund=None),
                      invite='Dạ nếu {who} tiện, bốn giờ chiều em xin năm phút trao đổi trực tiếp cho đúng ý ạ.',
                      process='Dạ thư đi đều qua hai bước: em soát chính tả, rồi trình ký; nên có lúc chậm nửa buổi ạ.'),
    'it_helpdesk': dict(place='phòng IT', self='bên IT', people='người dùng', who='anh chị', owner='kỹ thuật IT',
                        served='phiếu đã xử lý', record='lịch sử phiếu', review='đánh giá phiếu', reply='phản hồi',
                        books='Sổ công việc', rail_in='Trong văn phòng', confirm='Xác nhận việc IT',
                        daily='Phiếu hỗ trợ mới đang chờ. Vào ca nhé!', invite_label='Hẹn hỗ trợ lại',
                        offers=dict(drink='Mời cà phê · 6 xu', gift=None, refund=None),
                        invite='Dạ {who} mở phiếu mới, bên IT qua tận bàn xem lại máy cho {who} ạ.',
                        process='Dạ bên IT xử lý theo phiếu: ghi lỗi, thử khởi động lại, sao lưu rồi mới sửa. Hôm đó {fact} ạ.'),
    'railway': dict(place='đường ngang', self='gác chắn', people='người đi đường', who='anh chị', owner='nhân viên gác chắn',
                    served='chuyến tàu đã gác', record='sổ nhật ký', review='phản ánh', reply='giải trình', books='Sổ nhật ký',
                    rail_in='Ở chòi gác', confirm='Xác nhận việc gác chắn', daily='Bộ đàm sắp reo, nhận ca gác nhé!',
                    invite_label='Mời gặp ở chòi gác', offers=dict(drink='Chai nước · 6 xu', gift=None, refund=None),
                    invite='Mời {who} ghé chòi gác ngoài giờ tàu, gác chắn mở sổ nhật ký nói rõ ạ.',
                    process='Dạ có lệnh tàu là đóng chắn, kiểm đường thông rồi mới báo ga; chờ vài phút là để an toàn. Hôm đó {fact} ạ.'),
    'nurse': dict(place='khoa', self='khoa', people='người bệnh', who='bác', owner='điều dưỡng trực',
                  served='người bệnh đã chăm', record='phiếu chăm sóc', review='góp ý vào sổ của khoa', reply='phản hồi',
                  books='Sổ khoa', rail_in='Trong khoa', confirm='Xác nhận việc trong ca trực', team='Tổ phụ việc của khoa',
                  daily='Ca trực sáng sắp bắt đầu 🩺 Khoa đang chờ bạn nhận ca.', invite_label='Mời gặp',
                  sorry_label='Xin lỗi + sửa sai', offers=dict(drink='Chai nước ấm · 6 xu', gift='Hộp sữa thăm · 10 xu', refund=None)),
    'lighthouse': dict(place='trạm đèn', self='trạm', people='ngư dân', who='anh', owner='người gác đèn',
                       served='lượt tàu qua', record='nhật ký đèn', review='lời qua radio', reply='phản hồi', books='Sổ lương',
                       rail_in='Trên đảo', confirm='Xác nhận trước khi làm', daily='Đèn đang chờ giờ thắp. Vào ca nhé!',
                       invite_label='Mời ghé đảo', offers=dict(drink='Ấm trà · 6 xu', gift='Cá khô · 10 xu', refund=None),
                       invite='Tàu {who} ghé Hòn Gió, trạm mời lên uống ấm trà, nói chuyện cho rõ.',
                       process='Dạ trạm thắp đèn theo giờ, ghi nhật ký đèn và phát bản tin gió đúng kênh. Hôm đó {fact} ạ.'),
    'rescue': dict(place='tổng đài cứu hộ', self='tổng đài', people='người gọi', who='anh chị', owner='điều phối viên',
                   served='cuộc gọi đã nhận', record='ghi âm cuộc gọi', review='phản ánh', reply='phản hồi',
                   books='Sổ nhật ký', rail_in='Trong phòng trực', confirm='Xác nhận việc trong ca trực',
                   daily='Ca trực tổng đài sắp bắt đầu 🚑 Nhận ca nhé!', invite_label='Mời gọi lại',
                   offers=dict(drink=None, gift=None, refund=None),
                   invite='Khi cần, {who} gọi lại tổng đài, đọc rõ địa chỉ là xe được điều ngay ạ.',
                   process='Dạ tổng đài hỏi đủ địa chỉ, tình trạng, số gọi lại rồi mới điều xe; hỏi kỹ là để xe tới đúng chỗ. Hôm đó {fact} ạ.'),
    'lifeguard': dict(place='hồ bơi', self='đội cứu hộ', people='người bơi', who='bạn', owner='nhân viên cứu hộ',
                      served='lượt bơi đã trông', record='sổ trực', review='góp ý', reply='phản hồi', books='Sổ trực',
                      rail_in='Ở hồ bơi', confirm='Xác nhận việc ở hồ bơi', daily='Hồ bơi sắp mở cửa. Vào ca trực nhé!',
                      invite_label='Mời ghé bơi', offers=dict(drink='Chai nước · 6 xu', gift='Vé bơi tặng · 10 xu', refund=None),
                      invite='Lần tới {who} ghé bơi, đội cứu hộ hướng dẫn kỹ nội quy từ cổng ạ.',
                      process='Dạ đội cứu hộ thổi còi theo nội quy hồ, ai chưa biết bơi thì ở làn cạn. Hôm đó {fact} ạ.'),
    'police': dict(place='trụ sở', self='bên phường', people='người dân', who='anh chị', owner='cán bộ trực',
                   served='lượt tiếp dân', record='sổ trực ban', review='phản ánh của người dân', reply='phản hồi',
                   books='Sổ trực ban', rail_in='Trong trụ sở', confirm='Xác nhận việc trực ban',
                   team='Tổ hỗ trợ của trụ sở', daily='Ca trực ban sắp bắt đầu 👮 Nhận ca nhé!',
                   invite_label='Mời làm việc', sorry_label='Nhận thiếu sót', offer_field='',
                   offers=dict(drink=None, gift=None, refund=None)),
}

# Full reply packs (§9 of the voice audit), on top of the shared non-shop rows.
_PACKS = {
    'nurse': dict(
        warm=['Dạ khoa cảm ơn {who} đã góp ý. Cháu đọc kỹ rồi, mong {who} mau khỏe ạ.'],
        funny=['Dạ cháu tự ghi mình vào sổ “cần cố gắng” mục {label} rồi ạ 😅 Ca sau cháu bù ngay.'],
        sassy=['Dạ sổ khoa ghi {fact} ạ. Chắc lúc đó {who} đang ngủ say nên không nghe cháu gọi 😌'],
        facts=['Dạ, phiếu chăm sóc ghi: {fact}. Cháu gửi để {who} và gia đình xem lại cho yên tâm ạ.'],
        sorry=['Cháu xin lỗi {who} về {label}. Từ ca sau cháu báo trước từng việc rồi mới làm ạ.'],
        invite=['Chiều nay điều dưỡng trưởng có mặt, mời gia đình ghé phòng trực trao đổi ạ.'],
        process=['Dạ trước mỗi lần dùng thuốc khoa hỏi tên, năm sinh và dị ứng, nên có lúc lâu một chút ạ.'],
        genz=['Dạ em ghi vào sổ khoa rồi nha, ca sau em check kỹ gấp đôi luôn ạ 🩺'],
        silent=['Dạ khoa đã ghi nhận ạ.'],
        harsh=['Không vừa ý thì xin chuyển viện.']),
    'police': dict(
        warm=['Cảm ơn {who} đã phản ánh. Bên phường đã ghi vào sổ tiếp dân ạ.'],
        funny=['Bên phường xin nhận một điểm trừ mục {label} 😅 Cán bộ trực đã được “ôn bài” lại rồi ạ.'],
        sassy=['Sổ trực ban ghi {fact} ạ. Lần sau {who} mang đủ giấy tờ là xong trong năm phút thôi 🙂'],
        facts=['Theo sổ trực ban hôm đó: {fact}. {Who} cần đối chiếu, mời ghé trụ sở giờ hành chính ạ.'],
        sorry=['Bên phường nhận thiếu sót ở {label}. Cán bộ trực đã được nhắc lại quy trình tiếp dân.'],
        invite=['Mời {who} sáng thứ Hai ghé gặp cán bộ phụ trách để giải quyết dứt điểm ạ.'],
        process=['Việc xác nhận cần đủ giấy tờ theo quy định nên có lúc phải hẹn lại; hồ sơ không bị giữ quá hạn ạ.'],
        genz=['Bên phường đã note phản ánh rồi nha, xử lý đúng quy trình, không “bơ” đâu ạ 👮'],
        silent=['Bên phường đã tiếp nhận.'],
        harsh=['Không vừa ý thì đi khiếu nại.']),
    'secretary': dict(
        warm=['Dạ em cảm ơn {who} đã góp ý, em ghi vào sổ việc để lần sau làm chu đáo hơn ạ.'],
        funny=['Dạ em xin nhận một điểm “cần cố gắng” ở mục {label} 😅 Mai em nộp bản “xịn” hơn ạ.'],
        sassy=['Dạ theo lịch đã gửi thì {fact} ạ. Chắc email hôm đó trôi giữa 200 cái khác thôi ạ 🙂'],
        facts=['Dạ, theo lịch họp và sổ ghi điện thoại hôm đó: {fact}. Em gửi {who} bản chụp để đối chiếu ạ.'],
        sorry=['Dạ em nhận thiếu sót ở {label}. Từ mai em đọc lại tên và số người gọi trước khi gác máy ạ.'],
        genz=['Dạ em note liền nha, lần sau chuẩn chỉnh từng dấu phẩy luôn ạ ✍️'],
        silent=['Dạ em đã đọc ạ.'],
        harsh=['Không vừa ý thì anh tự nghe điện thoại.']),
    'giupviec': dict(
        warm=['Dạ em cảm ơn {who} đã nhắn, lần sau em nhớ kỹ góc đó ạ 💛'],
        funny=['Dạ em xin nhận một vé “lau lại” cho {label} 😅 Lần sau góc đó bóng loáng luôn ạ!'],
        sassy=['Dạ ảnh em gửi lúc dọn xong có chụp {fact} đó ạ, chắc Mướp nghịch sau khi em về 😌'],
        facts=['Dạ ảnh em gửi hôm đó có chụp: {fact}. {Who} xem lại giúp em ạ.'],
        sorry=['Em xin lỗi {who} về {label}. Buổi tới em ghé sớm 15 phút làm lại góc đó, không tính thêm ạ.'],
        genz=['Dạ lần sau nhà {who} sạch bóng như có filter luôn nha ✨'],
        silent=['Dạ em đã đọc ạ.'],
        harsh=['Chê thì chị tự dọn.']),
}

# The shared reply rows of a non-shop career ({self}/{Self}: the player's side, {record}: its own book).
TONES = {
    'warm': ['Cảm ơn {who} đã dành thời gian góp ý. {Self} đọc kỹ từng dòng rồi ạ 💛',
             'Dạ {self} cảm ơn {who} thật lòng. Chuyện {label} {self} đã ghi vào {record} để làm tốt hơn ạ.',
             'Lời {who} viết {self} đọc lại cả buổi. Cảm ơn {who} đã nói thẳng ạ.'],
    'funny': ['Đọc xong {self} đứng hình mất năm giây 😅 Hứa lần sau {label} sẽ khác hẳn ạ!',
              'Dạ {self} xin nhận một điểm “cần cố gắng” ở mục {label} ạ 😅 Lần sau bù ngay!',
              'Góp ý này {self} dán ngay cạnh {record} để sáng nào cũng đọc 😂 Cảm ơn {who} ạ.'],
    'sassy': ['Dạ {record} ghi {fact} đó ạ. Chắc hôm đó {who} vội quá nên chưa kịp thấy thôi 😌',
              'Dạ {self} ghi nhận ạ, riêng vụ {label} thì {fact}, {who} xem lại giúp nha 🙂',
              'Cảm ơn {who} chấm kỹ như đoàn kiểm tra ạ 😄 Lần sau {self} xin “thi lại” mục {label}!'],
    'facts': ['Dạ, theo {record} hôm đó: {fact}. {Self} gửi lại để mình cùng đối chiếu ạ.',
              '{Self} đã xem lại {record}: {fact}. Nếu {who} còn thấy chỗ nào khác, {self} kiểm tra thêm ngay ạ.'],
    'sorry': ['Thành thật xin lỗi {who} vì {label} chưa tốt. {Self} đã xem lại cách làm để lần sau không lặp lại ạ.',
              'Dạ {self} nhận thiếu sót. Chuyện {fact} {self} đã nhắc lại để không lặp lại nữa ạ.',
              '{Self} xin lỗi {who} ạ. Mong {who} cho {self} cơ hội sửa, lần sau cẩn thận hơn ạ.'],
    'invite': ['Cảm ơn {who} đã góp ý. Lần tới {who} cần gì cứ gọi {self}, {self} làm kỹ hơn ạ.'],
    'process': ['Dạ {self} làm theo từng bước và ghi vào {record}. Hôm đó {fact}, {self} đang xem bước nào cần chặt hơn ạ.'],
    'genz': ['Dạ {self} “note” lại liền nha 📝 Lần sau {label} chuẩn chỉnh luôn ạ ✨',
             'Real quá {who} ơi, {self} nhận hết 🫶 Lần sau xịn hơn hẳn nha!'],
    'silent': ['Dạ, {self} đã ghi nhận ạ.', '{Self} đã đọc, cảm ơn {who} 🙏'],
    'harsh': ['Không vừa ý thì đi chỗ khác, ở đây không rảnh nghe.', 'Bạn biết gì mà chê, lo chuyện của bạn đi.',
              'Khó tính vậy thì tự làm lấy cho vừa ý.'],
}
TONES_POS = {
    'warm': ['Đọc lời {who} mà {self} vui cả buổi. Cảm ơn {who} nhiều lắm ạ 💛'],
    'funny': ['Lời khen này {self} xin kẹp vào {record} luôn 😆 Cảm ơn {who} nha!'],
    'sassy': ['Dạ {self} biết mà, nhưng được {who} công nhận vẫn vui ạ 😌'],
    'facts': ['Dạ {record} hôm đó ghi: {fact}. Cảm ơn {who} đã để ý kỹ vậy ạ.'],
    'sorry': ['{Self} vẫn thấy mình còn chậm một chút, cảm ơn {who} đã thông cảm ạ.'],
    'invite': ['Cảm ơn {who} nhiều! Lần tới cần gì cứ gọi {self} nha.'],
    'process': ['Dạ bí quyết là làm từng bước, bước nào cũng kiểm lại. Cảm ơn {who} đã nhận ra ạ.'],
    'genz': ['Được khen xỉu luôn á 🫶 Cảm ơn {who} nha ✨'],
    'silent': ['Dạ, cảm ơn {who} ạ.'],
    'harsh': ['Không cần khen, lo chuyện của bạn đi.'],
}
# Bystanders under a non-shop career's review thread ({place}: the workplace, {host}: the player).
GUEST_TEXT = dict(
    defend=['Tôi biết chỗ này lâu rồi, trả lời vậy là đàng hoàng lắm.', 'Công bằng mà nói, {host} nói có lý đó.',
            'Bình tĩnh nha, giải thích rõ ràng vậy rồi mà 😅', 'Hôm đó tôi cũng có mặt, làm đúng mà.'],
    cheer=['Trả lời có tâm ghê 👏', 'Đọc mà thấy yên tâm hẳn.', 'Rep mặn mà duyên, 10 điểm 😂'],
    troll=['Hóng drama 🍿', 'Ủa rồi ai đúng ai sai, kể tiếp đi 👀', 'Lót dép ngồi hóng 🩴'],
    agree=['Mình cũng từng gặp y chang, không phải mỗi bạn đâu.', 'Trả lời vậy là không được rồi.',
           'Người ta góp ý thì nghe thôi, gắt chi vậy.'],
    fake=['Hình như bạn nhầm chỗ rồi á 😅', 'Tài khoản này mới lập mà ta 🤔', 'Mình tới tuần rồi thấy khác hẳn nha, bạn xem lại thử.'])
FAN_TEXT = ['Nghe {author} kể nên tới thử, đúng là chu đáo thật 👍', 'Được {author} giới thiệu, giờ tin chỗ này luôn 😆']

# Careers paid a wage, not shop revenue: no premises rent and no period tax (operations.SALARIED, branch salary-notax,
# 06/10). Their close-day words never mention rent, tax or a shop's book. Mirrored here so this module also stands on
# a tree without that branch; operations.SALARIED wins when it exists (tests/test_career_words.py checks they agree).
_SALARIED = frozenset((
    'pagoda', 'teacher',
    'nurse', 'police', 'rescue', 'lifeguard', 'library', 'railway', 'lighthouse',
    'pilot', 'flight_attendant', 'oil',
    'corp_accounting', 'group_accounting', 'hr_admin', 'secretary', 'it_helpdesk', 'customer_care',
))


def salaried_set() -> frozenset:
    try:
        from . import operations
        return frozenset(getattr(operations, 'SALARIED', _SALARIED))
    except ImportError:  # pragma: no cover
        return _SALARIED


# Keys the client reads (public/js/v4/terms.js); offers is a dict of label-or-None.
KEYS = tuple(SHOP)


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def _row(career: str, kw: dict) -> dict:
    place = kw['place']
    row = dict(SHOP)
    row.update(commerce=False, review='nhận xét',
               books='Sổ ' + place, rail_in='Ở ' + place, confirm='Xác nhận việc ở ' + place,
               team='Đội của ' + place, hire_board='Tìm người phụ việc ở ' + place, hire='Mời về ' + place,
               calm=_cap(place) + ' đang yên.', security='Giữ an ninh ' + place, revenue='Thu nhập nghề',
               income='thu nhập nghề', tip='Thưởng thêm', fund='Quỹ nghề', rate='Chấm chỗ làm của', sorry_label='Xin lỗi + sửa sai')
    row.update({k: v for k, v in kw.items() if k not in ('invite', 'process')})
    row['host'] = _cap(row['owner'])
    row['by_owner'] = _cap(row['owner']) + ' tự làm'
    row['by_staff'] = 'Người phụ việc làm'
    row['end_text'] = (f'Lương ngày vào quỹ lương. Lương phụ việc và điện nước ghi vào {row["books"].lower()} để bạn trả sau.'
                       if career in salaried_set() else
                       f'Lương, điện nước và tiền thuê ghi vào {row["books"].lower()} để bạn trả sau.')
    row['placeholder'] = f'Cảm ơn, xin lỗi nếu cần, và nói rõ {row["self"]} sẽ làm gì…'
    offers = dict(SHOP['offers'])
    offers.update(kw.get('offers') or {})
    row['offers'] = offers
    if not any(offers.values()):
        row['offer_field'] = ''
    return row


# The pagoda's shell words (its review thread is pagoda_voice.py's).
_PAGODA = dict(commerce=False, place='chùa', self='chùa', people='khách thập phương', who='bác', owner='thầy',
               served='lượt khách thập phương', record='sổ chùa', review='cảm nhận', reply='hồi đáp',
               books='Sổ chùa', rail_in='Trong chùa', confirm='Xác nhận việc chùa', end_title='Đóng cổng chùa hôm nay?',
               end_text='Tiền công Phật tử phụ việc và điện nước ghi vào sổ chùa, trả sau.',
               team='Ban công quả', hire_board='Mời Phật tử làm công quả', hire='Mời về chùa', calm='Sân chùa đang yên.',
               security='Giữ an ninh sân chùa', revenue='Thu chi công đức', income='công đức',
               tip='Phật tử biếu thêm', fund='Quỹ chùa', daily='Chuông sáng đã điểm, chùa đang chờ thầy ☀️ Mở cổng chùa nhé!',
               host='Thầy', by_owner='Thầy tiếp', by_staff='Phật tử phụ việc', rate='Cảm nhận về chùa của',
               invite_label='Mời ghé lễ', sorry_label='Xin lỗi', offer_field='Chút quà biếu',
               placeholder='A Di Đà Phật, cảm ơn, xin lỗi nếu cần, và nói rõ chùa sẽ làm gì…',
               offers=dict(drink='Mời trà · 6 xu', gift='Quà chay · 10 xu', refund=None))
# The teacher's shell words (its review thread is the parent set of feedback_voices).
_TEACHER = dict(place='lớp', self='lớp', people='phụ huynh', who='phụ huynh', owner='giáo viên', served='buổi dạy',
                record='sổ lớp', review='góp ý của phụ huynh', reply='phản hồi', books='Sổ lớp', rail_in='Trong lớp',
                confirm='Xác nhận việc của lớp', end_title='Tan lớp hôm nay?', team='Đội trợ giảng',
                hire_board='Tìm trợ giảng cho lớp', calm='Lớp đang yên.', security='Giữ an toàn lớp học',
                daily='Học sinh sắp vào lớp 📚 Vào lớp nhé!', invite_label='Mời trao đổi',
                offers=dict(drink='Kèm 1 buổi · 6 xu', gift='Tặng sách · 10 xu', refund='Hoàn 20 xu'))

TERMS: dict[str, dict] = {}


def _build() -> None:
    from .content import CAREERS
    for cid in CAREERS:
        if cid == 'pagoda':
            row = dict(SHOP)
            row.update(_PAGODA)
        elif cid == 'teacher':
            row = _row(cid, _TEACHER)
        elif cid in _ROWS:
            row = _row(cid, _ROWS[cid])
        else:
            row = dict(SHOP)
        TERMS[cid] = row


def terms(career: str | None) -> dict:
    """The career's words (SHOP for an unknown id); the catalogue sends them to the client."""
    if not TERMS:
        _build()
    return TERMS.get(career or '', SHOP)


def term(career: str | None, key: str, default=None):
    v = terms(career).get(key)
    return default if v is None else v


def commerce(career: str | None) -> bool:
    return bool(terms(career)['commerce'])


def shop_words(career: str | None, text: str) -> list[str]:
    """Shop words in `text` that `career` should not use (always [] for a shop)."""
    if commerce(career):
        return []
    allow = ALLOW.get(career or '', ())
    return [m.group(0) for m in SHOP_WORDS.finditer(text or '') if m.group(0).lower() not in allow]


def offer_ok(career: str | None, offer: str) -> bool:
    """A bù đắp the career may give (police never gives anything of value)."""
    return offer == 'none' or bool((terms(career).get('offers') or {}).get(offer))


def own_replies(career: str | None) -> bool:
    """A non-shop career that answers reviews with the rows below (pagoda and teacher have their own sets)."""
    return bool(career) and not commerce(career) and career not in ('pagoda', 'teacher')


def tone_rows(career: str, tone: str, happy: bool) -> list[str]:
    """The reply rows of one tone for a non-shop career: its pack, its own invite/process line, the shared rows."""
    if happy:
        return TONES_POS[tone]
    rows = list(_PACKS.get(career, {}).get(tone, ()))
    own = (_ROWS.get(career) or {}).get(tone)
    if own:
        rows.append(own)
    return rows + TONES[tone]


def fill_args(career: str, who: str) -> dict:
    t = terms(career)
    return dict(self=t['self'], Self=_cap(t['self']), record=t['record'], people=t['people'], who=who, Who=_cap(who))


def who_for(career: str, persona: str) -> str:
    return 'bạn' if persona in ('genz', 'troll') else term(career, 'who', 'bạn')


def tone_label(career: str, tone: str, default: str) -> str:
    if not own_replies(career):
        return default
    if tone == 'invite':
        return term(career, 'invite_label', default)
    if tone == 'sorry':
        return term(career, 'sorry_label', default)
    return default


def daily_line(career: str | None) -> str:
    return term(career, 'daily', SHOP['daily'])


def promotion_line(career: str | None, name: str, pct: int) -> str:
    """The promotion toast of an owner-track career ("Khách quen boa thêm X% doanh thu" for a shop)."""
    t = terms(career)
    return f'🎉 Bạn thành {name}! {t["tip"]} {pct}% {t["income"]}.'
