"""Công ty CP Cánh Diều — the in-house IT helpdesk (plugin career).

Real desk work of the one-person IT corner of a small company, checked by hand: triage the morning's
tickets (the director's "URGENT!!!" flickering screen is not more urgent than a ransomware note on a
sales laptop), fix things in an order that works without the harmful shortcuts (pulling jammed paper
against the feed, paying a ransom, blow-drying a coffee-soaked laptop), patch the wall sockets into
the right network from the seating chart, go through the access list against leavers and approved
requests, enter a new laptop into the asset book, and say no to the "phone company" asking for an OTP.

The dossier mechanics are shared with the other Cánh Diều desks (office_work.py). Every rule here is a
simplified GAME rule.
"""
from __future__ import annotations

from . import office_work as ow

ID = 'it_helpdesk'
P = 'it_'

PEOPLE = [
    ('Anh Long', 'Trưởng nhóm IT', 'Nói ít, ghét nhất câu “em chưa làm gì mà nó tự hỏng”.', 'picky'),
    ('Anh Quân', 'Giám đốc Công ty Cánh Diều', 'Cái gì cũng “GẤP”.', 'bossy'),
    ('Cô Hằng', 'Kế toán trưởng', 'Sợ mất số liệu hơn sợ ma.', 'sour'),
    ('Linh', 'Nhân viên kinh doanh', 'Cài đủ thứ tiện ích, quên mật khẩu như cơm bữa.', 'genz'),
    ('Chú Lâm', 'Tổ trưởng xưởng may', 'Coi máy in xưởng như người nhà.', 'warm'),
    ('Nhi', 'Lễ tân', 'Hiền, bấm gì cũng hỏi trước.', 'quiet'),
]
BOSS = 'Anh Long'

# ================================================================ dossier 1: ticket triage
TICKET_BINS = [dict(id='urgent', label='Khẩn — làm ngay', emoji='🔥'), dict(id='today', label='Trong ngày', emoji='🕐'),
               dict(id='plan', label='Xếp lịch', emoji='📅'), dict(id='notit', label='Không phải việc IT', emoji='🙅')]
TICKETS = [
    # (key, bin, from, title, text, why, sev, code, tier)
    ('netacct', 'urgent', 'Cô Hằng', 'Cả phòng kế toán mất mạng', 'Không ai vào được phần mềm kế toán, chiều nay chốt lương.',
     'Nhiều người dừng việc: khẩn.', 2, 'tk_net', 0),
    ('ransom', 'urgent', 'Linh', 'Máy hiện thông báo đòi tiền chuộc', 'File nào cũng đổi đuôi lạ, màn hình đỏ đòi chuyển tiền.',
     'Nghi mã độc tống tiền: khẩn, cách ly ngay kẻo lây cả mạng.', 3, 'tk_ransom', 0),
    ('pos', 'urgent', 'Cửa hàng mặt phố', 'Máy tính tiền không in được hóa đơn', 'Khách đang xếp hàng dài.',
     'Máy bán hàng ngừng, khách đang chờ: khẩn.', 2, 'tk_pos', 0),
    ('phished', 'urgent', 'Nhi', 'Em lỡ nhập mật khẩu email vào trang lạ', 'Trang đó giống hệt trang đăng nhập công ty.',
     'Lộ mật khẩu: khẩn, đổi mật khẩu và kiểm tra ngay.', 3, 'tk_phish', 1),
    ('server', 'urgent', 'Chị Huyền', 'Không ai mở được thư mục chung', 'Cả công ty báo lỗi “không tìm thấy máy chủ”.',
     'Cả công ty dừng việc: khẩn.', 2, 'tk_server', 1),
    ('bossscreen', 'today', 'Anh Quân', 'Màn hình nhấp nháy — GẤP!!!', 'Vẫn làm việc được nhưng khó chịu lắm.',
     'Một người, vẫn làm được việc: trong ngày — dù ai gửi, chữ GẤP không đổi mức ưu tiên.', 1, 'tk_boss', 0),
    ('mouse', 'today', 'Nhi', 'Chuột không bấm được', 'Em đang dùng bàn phím tạm.', 'Một người vướng nhẹ: trong ngày.', 1, 'tk_mouse', 0),
    ('pwd', 'today', 'Linh', 'Quên mật khẩu email (lần thứ ba tháng này)', 'Đang dùng điện thoại xem thư tạm.',
     'Một người, có cách tạm: trong ngày.', 1, 'tk_pwd', 0),
    ('printer2', 'today', 'Chú Lâm', 'Máy in tầng 2 kẹt giấy', 'Máy tầng 1 vẫn in bình thường.', 'Còn máy khác in được: trong ngày.', 1, 'tk_print', 0),
    ('excel', 'today', 'Cô Hằng', 'File Excel lớn mở rất chậm', 'Mở được nhưng mất cả phút.', 'Chậm nhưng vẫn làm được: trong ngày.', 1, 'tk_excel', 1),
    ('screen2', 'plan', 'Linh', 'Xin thêm màn hình thứ hai', 'Cho dễ làm báo giá.', 'Mua thêm thiết bị: xếp lịch theo kế hoạch.', 1, 'tk_more', 0),
    ('ram', 'plan', 'Phòng thiết kế', 'Nâng cấp RAM máy thiết kế', 'Máy chạy phần mềm vẽ hơi ì.', 'Nâng cấp: xếp lịch.', 1, 'tk_ram', 0),
    ('newhire', 'plan', 'Chị Huyền', 'Chuẩn bị máy cho nhân viên mới tháng sau', 'Hai bạn kinh doanh mới vào ngày 1.',
     'Việc có hạn xa: xếp lịch.', 1, 'tk_newhire', 0),
    ('wifi', 'plan', 'Anh Quân', 'Đổi wifi phòng họp cho nhanh hơn', 'Họp online hay bị giật.', 'Nâng cấp hạ tầng: xếp lịch.', 1, 'tk_wifi', 1),
    ('aircon', 'notit', 'Phòng họp lớn', 'Điều hòa chảy nước', 'Nước nhỏ giọt xuống bàn họp.', 'Điều hòa: báo hành chính gọi thợ.', 1, 'tk_ac', 0),
    ('bulb', 'notit', 'Nhi', 'Bóng đèn hành lang chập chờn', 'Tối đi về sợ lắm.', 'Điện chiếu sáng: hành chính lo.', 1, 'tk_bulb', 0),
    ('phone', 'notit', 'Linh', 'Sửa giúp điện thoại cá nhân bị vỡ màn', 'Anh IT khéo tay mà.', 'Đồ cá nhân không phải việc IT công ty.', 1, 'tk_phone', 0),
    ('game', 'notit', 'Anh Quân', 'Cài game cho con anh trên laptop công ty', 'Cuối tuần cháu mượn chơi.',
     'Máy công ty không cài phần mềm cá nhân: từ chối khéo.', 2, 'tk_game', 1),
    ('chair', 'notit', 'Cô Hằng', 'Ghế xoay gãy bánh xe', 'Ngồi nghiêng một bên.', 'Bàn ghế: hành chính lo.', 1, 'tk_chair', 0),
]


def g_tickets(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    rows = [r for r in TICKETS if r[8] <= min(1, tier)]
    by_bin: dict = {}
    for r in rows:
        by_bin.setdefault(r[1], []).append(r)
    pick = [rng.choice(by_bin[b['id']]) for b in TICKET_BINS]
    n = min(9, 6 + (tier >= 1) + (tier >= 2) + ctx['more'])
    pick += rng.sample([r for r in rows if r not in pick], n - len(pick))
    rng.shuffle(pick)
    items = [dict(id=f't{i}', title=r[3], sub=r[2], lines=[r[4]], note=None, _bin=r[1], _why=r[5], _sev=r[6], _code=r[7], _key=r[0])
             for i, r in enumerate(pick)]
    tw = None
    if ctx['twist']:
        keys = {it['_key']: it for it in items}
        if 'netacct' in keys:
            tw = dict(item=keys['netacct']['id'], bin='today', why='Mạng đã có lại, chỉ còn một máy.', sev=1,
                      note='Cô Hằng gọi lại: “Mạng có lại rồi, chỉ còn máy của cô chưa vào được thôi.”')
        elif 'printer2' in keys:
            tw = dict(item=keys['printer2']['id'], bin='urgent', why='Không còn máy nào in được phiếu xuất kho.', sev=2,
                      note='Chú Lâm hớt hải: “Máy tầng 1 cũng vừa hỏng! Cả công ty không in được phiếu xuất kho!”')
        elif 'mouse' in keys:
            tw = dict(item=keys['mouse']['id'], bin='urgent', why='Máy lễ tân là máy duy nhất mở cổng cho xe hàng.', sev=1,
                      note='Nhi: “Anh ơi, máy em là máy duy nhất mở cổng cho xe hàng, xe đang chờ ngoài cổng!”')
        if tw:
            tw['at'] = n - 2
    for it in items:
        it.pop('_key')
    return dict(npc=0, title=f'Phân loại phiếu hỗ trợ ({n} phiếu)',
                opening='Anh Long đẩy màn hình sang: “Sáng nay bao nhiêu phiếu này. Em phân loại, cái nào làm trước cái nào để sau.”',
                brief=f'Xếp {n} phiếu hỗ trợ vào bốn khay theo mức độ: khẩn, trong ngày, xếp lịch, không phải việc IT.',
                papers=[dict(id='rule', emoji='🚦', title='Mức độ ưu tiên', lines=[
                    'Khẩn: nhiều người dừng việc; nghi mã độc, lừa đảo, lộ mật khẩu; máy bán hàng ngừng.',
                    'Trong ngày: một người vướng nhưng còn làm được việc khác.',
                    'Xếp lịch: mua thêm, nâng cấp, chuẩn bị cho việc tháng sau.',
                    'Không phải việc IT: điện, điều hòa, bàn ghế, đồ cá nhân, phần mềm cá nhân.',
                    'Ai gửi, viết “GẤP” bao nhiêu lần cũng không đổi mức độ.'])],
                work=dict(type='sort', bins=TICKET_BINS, items=items, _twist=tw))


# ================================================================ dossier 2: fix it, step by step
FIXES = [
    dict(id='jam', title='Gỡ kẹt giấy máy in kế toán', npc=2,
         opening='Cô Hằng gọi: “Máy in kẹt giấy rồi! Đèn đỏ nhấp nháy, cô không dám đụng vào.”',
         steps=[('code', 'Đọc mã lỗi trên màn hình máy in', 'need', 'Mã lỗi chỉ đúng chỗ kẹt.'),
                ('off', 'Tắt máy, rút điện', 'need', 'Không thò tay vào máy đang chạy.'),
                ('open', 'Mở nắp sau', 'need', 'Giấy kẹt ở khay sau.'),
                ('pull', 'Kéo giấy ra từ từ theo chiều giấy chạy', 'need', 'Kéo ngược chiều làm rách giấy, kẹt sâu hơn.'),
                ('bits', 'Soi đèn kiểm tra mẩu giấy vụn', 'need', 'Mẩu vụn còn sót sẽ kẹt lại ngay.'),
                ('test', 'Bật lại, in trang thử', 'need', 'Thử xong mới trả máy.'),
                ('pry', 'Dùng kéo cạy tờ giấy kẹt', 'bad', 'Làm xước trục, hỏng máy.', 2),
                ('yank', 'Giật mạnh tờ giấy ngược chiều', 'bad', 'Rách giấy, vụn kẹt sâu trong máy.', 2),
                ('spray', 'Xịt nước lau kính vào trống mực', 'bad', 'Hỏng trống mực.', 2),
                ('sign', 'Dán giấy “Đang sửa” lên máy', 'opt', ''),
                ('tell', 'Báo cô Hằng trước khi tắt máy', 'opt', '')],
         after=[('off', 'open', 'Tắt máy rồi mới mở nắp.'), ('open', 'pull', 'Mở nắp rồi mới kéo giấy.'), ('pull', 'bits', 'Kéo giấy ra rồi mới soi vụn.'),
                ('bits', 'test', 'Hết vụn mới in thử.'), ('code', 'open', 'Đọc mã lỗi trước để biết mở nắp nào.')],
         twist=dict(step='tell', note='Anh Long nhắn: “Máy đó kế toán đang in dở bảng lương — báo cô Hằng trước khi tắt nhé.”',
                    why='Đang in dở bảng lương, tắt ngang là mất lệnh in.', after=[('tell', 'off', 'Báo trước rồi mới tắt.')])),
    dict(id='ransom', title='Máy của Linh dính mã độc tống tiền', npc=3,
         opening='Linh hét lên: “Anh ơi màn hình em đỏ lòm, đòi chuyển tiền chuộc file! Em có bấm vào cái hóa đơn lạ lúc sáng…”',
         steps=[('cut', 'Rút dây mạng, tắt wifi máy đó ngay', 'need', 'Cách ly để mã độc không lây sang máy khác.'),
                ('report', 'Báo anh Long', 'need', 'Sự cố an ninh phải báo trưởng nhóm.'),
                ('photo', 'Chụp màn hình thông báo bằng điện thoại', 'need', 'Giữ bằng chứng để xử lý.'),
                ('scan', 'Kiểm tra các máy cùng phòng', 'need', 'Xem có lây sang máy khác không.'),
                ('restore', 'Cài lại máy, chép dữ liệu từ bản sao lưu đêm qua', 'need', 'Có bản sao lưu thì không cần trả tiền.'),
                ('pwd', 'Đổi mật khẩu các tài khoản Linh đã đăng nhập', 'need', 'Mã độc có thể đã lấy mật khẩu.'),
                ('pay', 'Chuyển tiền chuộc cho nhanh', 'bad', 'Trả tiền không chắc lấy lại file, còn bị nhắm tiếp.', 3),
                ('usb', 'Cắm ổ sao lưu vào máy nhiễm để chép file ra', 'bad', 'Mã độc mã hóa luôn bản sao lưu.', 3),
                ('share', 'Gửi file lạ cho cả phòng hỏi ai biết', 'bad', 'Lây cho người khác.', 2),
                ('remind', 'Nhắc cả công ty không mở hóa đơn lạ', 'opt', ''),
                ('tea', 'Pha cho Linh cốc trà', 'opt', '')],
         after=[('cut', 'scan', 'Cách ly trước rồi mới kiểm tra máy khác.'), ('cut', 'restore', 'Cách ly trước rồi mới khôi phục.'),
                ('scan', 'restore', 'Biết hết máy nhiễm rồi mới khôi phục.'), ('photo', 'restore', 'Chụp bằng chứng trước khi xóa máy.')],
         twist=dict(step='remind', note='Anh Long: “Kế toán cũng vừa nhận đúng cái hóa đơn lạ đó. Nhắc cả công ty ngay!”',
                    why='Cùng email độc đang gửi tới nhiều người.', after=[('cut', 'remind', 'Cách ly máy nhiễm trước.')])),
    dict(id='coffee', title='Laptop của sếp đổ cà phê', npc=1,
         opening='Anh Quân giơ chiếc laptop nhỏ nước tong tỏng: “Cà phê sữa! Họp lúc 2 giờ, em cứu nó giúp anh!”',
         steps=[('off', 'Tắt nguồn ngay (giữ nút nguồn)', 'need', 'Điện chạy qua mạch ướt là chập.'),
                ('unplug', 'Rút sạc, tháo chuột, USB', 'need', 'Ngắt hết nguồn điện.'),
                ('flip', 'Úp ngược laptop hình chữ V cho nước chảy ra', 'need', 'Để nước không đọng trong máy.'),
                ('wipe', 'Lau khô bên ngoài bằng khăn mềm', 'need', 'Lau nhẹ, không ấn.'),
                ('lend', 'Cho sếp mượn máy dự phòng để họp', 'need', 'Họp 2 giờ vẫn phải có máy.'),
                ('shop', 'Gửi tiệm kiểm tra, không bật lại trong 48 giờ', 'need', 'Mạch phải khô hẳn.'),
                ('turnon', 'Bật lên xem còn chạy không', 'bad', 'Chập mạch, hỏng hẳn.', 2),
                ('dryer', 'Sấy bằng máy sấy tóc nóng', 'bad', 'Nhiệt cao làm cong mạch, chảy linh kiện.', 2),
                ('shake', 'Lắc mạnh cho nước ra', 'bad', 'Nước lan sâu hơn vào máy.', 1),
                ('rice', 'Vùi vào thùng gạo', 'opt', ''),
                ('backup', 'Hỏi sếp có file nào chưa sao lưu', 'opt', '')],
         after=[('off', 'flip', 'Tắt nguồn trước.'), ('unplug', 'flip', 'Rút sạc trước khi úp máy.'), ('flip', 'shop', 'Cho nước chảy ra trước rồi mới gửi đi.')],
         twist=dict(step='backup', note='Anh Quân: “Chết! Bài trình bày lúc 2 giờ chỉ có trong máy đó!”', why='File họp chưa có bản sao.',
                    after=[('backup', 'lend', 'Biết cần file gì rồi mới chuẩn bị máy dự phòng.')])),
    dict(id='overwrite', title='Cô Hằng lỡ lưu đè file báo cáo', npc=2,
         opening='Cô Hằng tái mặt: “Cô lỡ lưu đè file báo cáo quý bằng bản nháp! Chiều nay nộp sếp rồi…”',
         steps=[('stop', 'Đóng file, không lưu thêm lần nào', 'need', 'Lưu thêm là đè mất thêm phiên bản cũ.'),
                ('history', 'Mở “Phiên bản trước” của file', 'need', 'Máy tự giữ các phiên bản cũ.'),
                ('backup', 'Tìm bản sao lưu đêm qua trên máy chủ', 'need', 'Phòng khi phiên bản trước không có.'),
                ('newfile', 'Khôi phục ra file mới, không đè file đang dùng', 'need', 'Giữ cả hai bản để so.'),
                ('check', 'Nhờ cô Hằng kiểm lại số liệu', 'need', 'Chỉ người làm mới biết bản nào đúng.'),
                ('crack', 'Tải phần mềm khôi phục bẻ khóa trên mạng', 'bad', 'Phần mềm lậu hay kèm mã độc.', 3),
                ('format', 'Định dạng lại ổ đĩa cho “sạch”', 'bad', 'Mất sạch dữ liệu.', 3),
                ('blame', 'Bảo cô Hằng làm lại từ đầu cho nhanh', 'bad', 'Có cách khôi phục, làm lại là phí công.', 1),
                ('autosave', 'Bật tự động lưu cho máy cô Hằng', 'opt', ''),
                ('coffee', 'Mời cô Hằng ly nước cho bình tĩnh', 'opt', '')],
         after=[('stop', 'history', 'Đóng file trước khi mở phiên bản cũ.'), ('history', 'newfile', 'Có bản cũ mới khôi phục được.'),
                ('newfile', 'check', 'Khôi phục xong mới kiểm số.')],
         twist=dict(step='autosave', note='Anh Long: “Tuần này là lần thứ hai rồi. Bật tự động lưu cho cô ấy luôn.”', why='Tránh lặp lại lần sau.',
                    after=[('check', 'autosave', 'Xong việc gấp rồi mới chỉnh cài đặt.')])),
    dict(id='wifi', title='Wifi phòng họp chập chờn trước giờ đón khách', npc=1,
         opening='Anh Quân: “30 phút nữa khách tới họp online với Nhật mà wifi phòng họp cứ rớt! Làm gì đi em!”',
         steps=[('count', 'Xem bộ phát đang có bao nhiêu máy kết nối', 'need', 'Quá tải thì phải tách mạng.'),
                ('reboot', 'Khởi động lại bộ phát wifi phòng họp', 'need', 'Bộ phát treo là hay rớt mạng.'),
                ('cable', 'Cắm dây mạng cho máy trình chiếu', 'need', 'Máy chính dùng dây cho chắc.'),
                ('guest', 'Bật mạng khách riêng cho khách', 'need', 'Khách không dùng mạng nội bộ.'),
                ('test', 'Gọi thử một cuộc họp online', 'need', 'Thử trước khi khách tới.'),
                ('share', 'Đưa khách mật khẩu wifi nội bộ', 'bad', 'Khách vào được mạng nội bộ, lộ dữ liệu.', 2),
                ('killall', 'Tắt wifi cả tầng để “reset”', 'bad', 'Cả tầng mất mạng giữa giờ làm.', 2),
                ('ban', 'Cấm mọi người dùng điện thoại cả ngày', 'bad', 'Không cần thiết, ai cũng bực.', 1),
                ('sign', 'Dán mật khẩu mạng khách lên bàn họp', 'opt', ''),
                ('spare', 'Chuẩn bị bộ phát 4G dự phòng', 'opt', '')],
         after=[('count', 'reboot', 'Xem trước rồi mới khởi động lại.'), ('reboot', 'test', 'Khởi động xong mới thử.'), ('cable', 'test', 'Cắm dây xong mới thử.')],
         twist=dict(step='spare', note='Anh Long: “Bên tòa nhà báo 3 giờ cắt mạng cáp quang để sửa đường dây!”', why='Mạng chính sắp bị cắt.',
                    after=[('spare', 'test', 'Có bộ phát dự phòng rồi thử luôn.')])),
]


def g_fix(rng, ctx: dict) -> dict:
    x = rng.choice(FIXES)
    pool = [dict(id=s[0], label=s[1], _role=s[2], _why=s[3], _sev=s[4] if len(s) > 4 else 1) for s in x['steps']]
    rng.shuffle(pool)
    tw = dict(x['twist'], at=0, after=[list(a) for a in x['twist']['after']]) if ctx['twist'] else None
    return dict(npc=x['npc'], title=x['title'], opening=x['opening'],
                brief='Chọn các bước sẽ làm, theo đúng thứ tự; bỏ ra những bước gây hại. Bước không cần thì làm hay không cũng được.',
                papers=[dict(id='rule', emoji='🧯', title='Nguyên tắc sửa chữa', lines=['An toàn điện trước: tắt máy, rút điện rồi mới mở.',
                                                                                     'Sự cố an ninh: cách ly trước, báo anh Long, giữ bằng chứng.',
                                                                                     'Không dùng phần mềm lậu, không trả tiền chuộc.'])],
                work=dict(type='seq', pool=pool, _after=[list(a) for a in x['after']], _twist=tw))


# ================================================================ dossier 3: patch panel
NET_BINS = [dict(id='staff', label='Mạng nhân viên', emoji='💼'), dict(id='acct', label='Mạng kế toán', emoji='🔐'),
            dict(id='guest', label='Mạng khách', emoji='🙋'), dict(id='cam', label='Mạng camera & thiết bị', emoji='📹')]


def g_patch(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    used: set = {'Linh'}
    acc, _ = ow.person(rng, used)
    sales, _ = ow.person(rng, used)
    intern, _ = ow.person(rng, used)
    rows = [
        ('A-01', 'Cô Hằng — Kế toán', 'acct', 'Kế toán vào mạng kế toán.', 1, 'pt_acct'),
        ('A-02', f'{acc} — Kế toán', 'acct', 'Kế toán vào mạng kế toán.', 1, 'pt_acct'),
        ('A-03', 'Linh — Kinh doanh (ngồi tạm tuần này)', 'staff', 'Ngồi bàn kế toán nhưng là nhân viên kinh doanh: theo người, không theo bàn.', 2, 'pt_seat'),
        ('B-04', f'{sales} — Kinh doanh', 'staff', 'Nhân viên vào mạng nhân viên.', 1, 'pt_staff'),
        ('B-05', f'{intern} — Thực tập sinh', 'guest', 'Thực tập sinh dùng mạng khách.', 2, 'pt_intern'),
        ('P-01', 'Phòng họp lớn — ổ trên bàn', 'guest', 'Ổ phòng họp khách hay cắm: mạng khách.', 2, 'pt_room'),
        ('C-01', 'Camera cổng xưởng', 'cam', 'Camera vào mạng camera.', 1, 'pt_cam'),
        ('C-02', 'Máy chấm công', 'cam', 'Máy chấm công là thiết bị: mạng camera & thiết bị.', 1, 'pt_clock'),
        ('B-09', 'Máy in chung tầng 2', 'staff', 'Máy in chung cho nhân viên: mạng nhân viên.', 1, 'pt_printer'),
        ('A-09', 'Máy in phòng kế toán (in bảng lương)', 'acct', 'In bảng lương: mạng kế toán.', 2, 'pt_payprint'),
        ('D-02', 'Anh Quân — Giám đốc', 'staff', 'Mạng kế toán chỉ cho phòng kế toán; giám đốc xem báo cáo qua phần mềm có phân quyền.', 2, 'pt_boss'),
    ]
    must = ['A-01', 'A-03', 'B-05', 'C-01']
    n = min(9, 6 + (tier >= 1) + (tier >= 2) + ctx['more'])
    chosen = [r for r in rows if r[0] in must] + rng.sample([r for r in rows if r[0] not in must], n - len(must))
    rng.shuffle(chosen)
    items = []
    for i, r in enumerate(chosen):
        note = '“Cho anh vào mạng kế toán luôn cho tiện xem số.” — Anh Quân' if r[0] == 'D-02' else None
        items.append(dict(id=f'p{i}', title=f'Ổ {r[0]}', sub=r[1], lines=[], note=note, _bin=r[2], _why=r[3], _sev=r[4], _code=r[5], _key=r[0]))
    tw = None
    if ctx['twist']:
        keys = {it['_key']: it for it in items}
        if rng.random() < 0.5:
            tw = dict(item=keys['A-03']['id'], bin='acct', why='Linh đã chuyển sang làm kế toán kho.', sev=2,
                      note='Chị Huyền báo: “Linh chuyển hẳn sang làm kế toán kho từ hôm nay rồi nhé.”')
        else:
            tw = dict(item=keys['B-05']['id'], bin='staff', why='Đã ký hợp đồng chính thức.', sev=1,
                      note=f'Chị Huyền báo: “Bạn {ow.short(intern)} vừa ký hợp đồng chính thức sáng nay.”')
        tw['at'] = n - 2
    for it in items:
        it.pop('_key')
    return dict(npc=0, title=f'Đấu dây tủ mạng ({n} ổ)',
                opening='Anh Long mở tủ mạng, dây chằng chịt: “Sau đợt chuyển chỗ ngồi, em đấu lại từng ổ vào đúng mạng nhé.”',
                brief=f'Đấu {n} ổ mạng vào đúng mạng: nhân viên, kế toán, khách hay camera & thiết bị.',
                papers=[dict(id='rule', emoji='🔌', title='Quy định mạng', lines=[
                    'Mạng kế toán: chỉ người phòng kế toán và máy in bảng lương.',
                    'Mạng nhân viên: nhân viên chính thức, máy in chung.',
                    'Mạng khách: khách, thực tập sinh, ổ trong phòng họp.',
                    'Mạng camera & thiết bị: camera, máy chấm công.',
                    'Xếp theo người đang dùng, không theo bàn.'])],
                work=dict(type='sort', bins=NET_BINS, items=items, _twist=tw))


# ================================================================ dossier 4: access review
SYSTEMS = ('Email', 'Phần mềm kế toán', 'Thư mục Nhân sự', 'VPN')
ACC_OPTS = ['Giữ nguyên', 'Cấp quyền', 'Thu hồi']
KEEP, GRANT, REVOKE = range(3)


def g_access(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    used: set = {'Linh', 'Hằng'}
    leaver, _ = ow.person(rng, used)
    intern, _ = ow.person(rng, used)
    mover, _ = ow.person(rng, used)
    trav, _ = ow.person(rng, used)
    # Each person: (label, current access [E, K, N, V], right decision per system, why per system, notes)
    people = [
        dict(key='hang', label='Cô Hằng · Kế toán', has=[1, 1, 0, 0], ok=[0, 0, 0, 0], why=['', '', '', '']),
        dict(key='leaver', label=f'{leaver} · Kinh doanh', has=[1, 1, 0, 1], ok=[REVOKE, REVOKE, 0, REVOKE],
             why=['Đã nghỉ việc: thu hồi hết.'] * 2 + [''] + ['Đã nghỉ việc: thu hồi hết.'],
             note=f'📤 Danh sách nghỉ việc: {leaver} nghỉ từ thứ Hai.', sev=3),
        dict(key='intern', label=f'{intern} · Thực tập sinh', has=[1, 0, 1, 0], ok=[0, 0, REVOKE, 0],
             why=['', '', 'Thực tập sinh không được vào thư mục Nhân sự.', ''], sev=2),
        dict(key='linh', label='Linh · Kinh doanh', has=[1, 0, 0, 0], ok=[0, 0, 0, 0],
             why=['', 'Phiếu xin quyền phần mềm kế toán CHƯA được duyệt: giữ nguyên.', '', ''],
             note='⏳ Phiếu yêu cầu CHƯA DUYỆT: Linh xin quyền Phần mềm kế toán.', sev=2),
        dict(key='mover', label=f'{mover} · Kinh doanh (mới chuyển từ Kế toán)', has=[1, 1, 0, 0], ok=[0, REVOKE, 0, 0],
             why=['', 'Đã chuyển khỏi phòng kế toán: thu hồi phần mềm kế toán.', '', ''],
             note=f'🔁 {mover} chuyển từ Kế toán sang Kinh doanh từ tuần này.', sev=2),
        dict(key='trav', label=f'{trav} · Kinh doanh', has=[1, 0, 0, 0], ok=[0, 0, 0, GRANT],
             why=['', '', '', 'Có phiếu cấp VPN đã duyệt.'], note=f'✅ Phiếu yêu cầu ĐÃ DUYỆT: cấp VPN cho {trav} đi công tác.', sev=1),
    ]
    n = min(6, 4 + (tier >= 1) + (tier >= 2) + ctx['more'])
    must = ['leaver', 'intern', 'trav'] if ctx['twist'] else ['leaver', 'intern']
    chosen = [p for p in people if p['key'] in must]
    chosen += rng.sample([p for p in people if p['key'] not in must], n - len(chosen))
    rng.shuffle(chosen)
    rows, notes, tw = [], [], None
    for r, p in enumerate(chosen):
        row = [p['label']]
        for k in range(4):
            sid = f'r{r}s{k}'
            trap = p['ok'][k] == KEEP and bool(p['why'][k])
            row.append(ow.cell(sid, '✓' if p['has'][k] else '—', p['ok'][k], p['why'][k] or 'Đúng quyền hiện có.', p.get('sev', 1), f'ac_{p["key"]}', trap))
            if p['key'] == 'trav' and k == 3 and ctx['twist']:
                tw = dict(at=3, seg=sid, ok=KEEP, sev=1, why='Phiếu cấp VPN đã bị hủy.',
                          note=f'Anh Long: “Phiếu VPN của {ow.short(trav)} hủy rồi — chuyến công tác bị hoãn.”')
        rows.append(row)
        if p.get('note'):
            notes.append(p['note'])
    rng.shuffle(notes)
    return dict(npc=0, title='Rà soát quyền truy cập tháng này',
                opening='Anh Long: “Cuối tháng rồi. Em rà lại bảng quyền truy cập với danh sách nghỉ việc và các phiếu yêu cầu nhé.”',
                brief=f'Rà {len(chosen)} người × 4 hệ thống: chạm ô cần đổi, chọn cấp quyền hoặc thu hồi. Ô đúng thì để nguyên.',
                papers=[dict(id='rule', emoji='🔐', title='Quy định quyền truy cập', lines=[
                            'Nghỉ việc: thu hồi tất cả ngay.', 'Phần mềm kế toán: chỉ người phòng kế toán.',
                            'Thư mục Nhân sự: chỉ phòng nhân sự; thực tập sinh không bao giờ.',
                            'Chỉ cấp quyền khi phiếu yêu cầu ĐÃ DUYỆT.']),
                        dict(id='notes', emoji='🗂️', title='Danh sách & phiếu trong tháng', lines=notes or ['Không có thay đổi nào.'])],
                work=dict(type='mark', opts=ACC_OPTS, blocks=[dict(k='table', head=['Người dùng', *SYSTEMS], rows=rows)], _twist=tw))


# ================================================================ dossier 5: the asset book
KINDS = [dict(id='LT', name='Laptop', models=('ThinkBook 14 G6', 'Vivobook 15', 'Latitude 3440'), months=24),
         dict(id='MH', name='Màn hình', models=('Dell P2422H', 'LG 24MP400'), months=36),
         dict(id='MI', name='Máy in', models=('Brother HL-L2321D', 'Canon LBP2900'), months=12)]
DEPTS = [dict(id='kd', label='Kinh doanh'), dict(id='kt', label='Kế toán'), dict(id='ns', label='Nhân sự'), dict(id='xg', label='Xưởng may')]
SERIAL = 'ABCDEFGHJKLMNPRSTUVWXYZ23456789'


def _add_months(d: int, m: int, y: int, months: int) -> tuple[int, int, int]:
    m2 = m - 1 + months
    return d, m2 % 12 + 1, y + m2 // 12


def g_asset(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    used: set = set()
    k = rng.choice(KINDS)
    model = rng.choice(k['models'])
    serial = ''.join(rng.choice(SERIAL) for _ in range(8))
    last = rng.randrange(20, 140)
    owner, _ = ow.person(rng, used)
    other, _ = ow.person(rng, used)
    dept = rng.choice(DEPTS)
    d, m, y = rng.randrange(1, 29), rng.randrange(1, 13), 2025
    wd, wm, wy = _add_months(d, m, y, k['months'])
    asset = f'CD-{k["id"]}-{last + 1:04d}'
    script = [dict(who='📷 Tem dán trên máy', text=f'{k["name"]} {model} · S/N: {serial[:4]} {serial[4:]}'),
              dict(who='🧾 Hóa đơn mua', text=f'Ngày mua {d:02d}/{m:02d}/{y} · bảo hành {k["months"]} tháng'),
              dict(who='📒 Sổ tài sản', text=f'Mã {k["name"].lower()} gần nhất: CD-{k["id"]}-{last:04d}'),
              dict(who='📝 Phiếu bàn giao', text=f'Giao cho {owner} — phòng {dept["label"]}')]
    if tier >= 1:
        script.insert(1, dict(who='📦 Hộp máy', text=f'Mã vạch hộp: 8 9 3 {rng.randrange(1000000, 9999999)} (không phải số serial)'))
    fields = [dict(id='serial', label='Số serial (S/N)', kind='code', _ok=serial, _why='Chép đúng S/N trên tem máy, không lấy mã vạch hộp.', _sev=2,
                   _code='as_serial'),
              dict(id='asset', label='Mã tài sản mới', kind='code', _ok=asset, _why=f'Mã tiếp theo sau CD-{k["id"]}-{last:04d}.', _sev=1, _code='as_tag'),
              dict(id='owner', label='Người nhận', kind='text', _ok=owner, _why='Theo phiếu bàn giao.', _sev=1, _code='as_owner'),
              dict(id='dept', label='Phòng', kind='pick', opts=DEPTS, _ok=dept['id'], _why='Theo phiếu bàn giao.', _sev=1, _code='as_dept'),
              dict(id='warranty', label='Hết bảo hành (dd/mm/yyyy)', kind='date', _ok=f'{wd:02d}/{wm:02d}/{wy}',
                   _why=f'Ngày mua cộng {k["months"]} tháng.', _sev=1, _code='as_warranty')]
    tw = None
    if ctx['twist']:
        tw = dict(at=0, field='owner', ok=other, why='Phòng đã đổi người nhận máy.', note='Trưởng phòng gọi xuống: đổi người nhận máy!',
                  line=dict(who='📞 Trưởng phòng gọi', text=f'Máy này giao cho {other}, không phải {ow.short(owner)} nhé, em sửa phiếu giúp anh.'))
    return dict(npc=0, title=f'Nhập sổ tài sản: {k["name"].lower()} mới',
                opening=f'Anh Long đặt thùng {k["name"].lower()} lên bàn: “Máy mới về. Em nhập sổ tài sản rồi mới giao người dùng nhé.”',
                brief='Đọc tem máy, hóa đơn, sổ tài sản và phiếu bàn giao; ghi đủ năm ô của sổ tài sản.',
                papers=[dict(id='rule', emoji='🏷️', title='Cách ghi sổ', lines=['Mã tài sản: CD-<loại>-<số tiếp theo, 4 chữ số>.',
                                                                              'S/N chép trên tem máy, không lấy mã vạch hộp.',
                                                                              'Hết bảo hành = ngày mua + số tháng bảo hành.'])],
                work=dict(type='fields', script=script, fields=fields, _twist=tw))


# ================================================================ dossier 6: social engineering
CASES = [
    dict(id='otp', npc=5, title='“Nhà mạng” xin mã OTP',
         opening='Nhi chuyển máy: “Anh ơi, bên nhà mạng gọi, bảo nâng cấp sim công ty, xin mã OTP vừa gửi về điện thoại của sếp.”',
         facts=[dict(id='rule', title='Quy định bảo mật', text='Không ai được hỏi mã OTP. Nhà mạng thật không bao giờ xin OTP.'),
                dict(id='number', title='Số gọi đến', text='Số di động lạ, không phải tổng đài nhà mạng.'),
                dict(id='sim', title='Sim của sếp', text='Sim đó nhận mã OTP của tài khoản ngân hàng công ty.')],
         options=[dict(id='hang', label='Từ chối, cúp máy, gọi tổng đài chính thức để kiểm tra; báo sếp và cả công ty',
                       requires=['rule', 'number'], _q='good', _out='Tổng đài xác nhận không có đợt nâng cấp nào. Cả công ty được cảnh báo kịp.'),
                  dict(id='ask', label='Hỏi lại tên, mã nhân viên của người gọi rồi tính', requires=[], _q='ok',
                       _out='Kẻ gian đọc tên, mã rất trơn tru. May mà bạn chưa đưa mã.'),
                  dict(id='give', label='Xin mã từ sếp rồi đọc cho họ', requires=['sim'], _q='bad', _sev=3,
                       _out='Tài khoản ngân hàng công ty bị chiếm; cô Hằng phải phong tỏa gấp.')]),
    dict(id='zalo', npc=1, title='“Anh Quân” nhắn xin mật khẩu quản trị',
         opening='Zalo mới tên “Anh Quân (số mới)” nhắn: “Anh đổi số. Gửi anh mật khẩu quản trị email công ty, anh đang ở sân bay cần gấp.”',
         facts=[dict(id='old', title='Gọi số cũ của sếp', text='Anh Quân nghe máy, đang ngồi họp ở tầng 3, không đổi số nào.'),
                dict(id='rule', title='Quy định', text='Mật khẩu quản trị không gửi qua tin nhắn cho bất kỳ ai.'),
                dict(id='photo', title='Ảnh đại diện', text='Ảnh lấy từ trang công ty.')],
         options=[dict(id='verify', label='Gọi số cũ xác minh, báo tài khoản giả, cảnh báo cả công ty', requires=['old', 'rule'], _q='good',
                       _out='Tài khoản giả bị báo cáo; ba người khác cũng vừa nhận tin y hệt và đã được cảnh báo.'),
                  dict(id='ignore', label='Lờ đi, không nói ai', requires=[], _q='ok', _out='Bạn không mất gì, nhưng Linh suýt gửi mật khẩu email của mình.'),
                  dict(id='send', label='Gửi mật khẩu vì sếp đang gấp', requires=[], _q='bad', _sev=3,
                       _out='Kẻ gian vào được email cả công ty, gửi hóa đơn giả cho khách hàng.')]),
    dict(id='tech', npc=5, title='Thợ lạ đến “bảo trì camera”',
         opening='Một người mặc áo đồng phục đến quầy: “Anh bên bảo trì camera, có lịch hôm nay, cho anh vào phòng máy chủ nhé.”',
         facts=[dict(id='sched', title='Lịch bảo trì', text='Không có lịch bảo trì nào hôm nay; đơn vị bảo trì thật đến vào thứ Năm cuối tháng.'),
                dict(id='call', title='Gọi đơn vị bảo trì', text='Họ không cử ai đến hôm nay.'),
                dict(id='badge', title='Thẻ nhân viên', text='Thẻ in giấy thường, không có ảnh.')],
         options=[dict(id='stop', label='Lịch sự mời chờ ở sảnh, gọi đơn vị bảo trì xác minh, không cho vào phòng máy chủ',
                       requires=['sched', 'call'], _q='good', _out='Người lạ viện cớ bỏ đi. Camera ghi lại mặt, báo bảo vệ khu.'),
                  dict(id='escort', label='Cho vào nhưng đi kèm từng bước', requires=[], _q='ok', _out='Hắn lén cắm một thiết bị lạ, may anh Long phát hiện tối đó.'),
                  dict(id='let', label='Cho vào phòng máy chủ, mình về chỗ làm tiếp', requires=['badge'], _q='bad', _sev=3,
                       _out='Ổ cứng sao lưu biến mất; dữ liệu khách hàng bị đem bán.')]),
    dict(id='reset', npc=3, title='Xin đổi mật khẩu email người khác',
         opening='Linh: “Anh reset mật khẩu email chị Khuê giúp em, em cần xem đơn hàng chị ấy đang theo. Chị ấy nghỉ phép rồi.”',
         facts=[dict(id='rule', title='Quy định', text='Chỉ đổi mật khẩu khi chính chủ yêu cầu; trưởng phòng có thể xin chuyển tiếp thư công việc.'),
                dict(id='boss', title='Hỏi trưởng phòng kinh doanh', text='Trưởng phòng đồng ý chuyển tiếp thư của khách đó sang Linh trong tuần chị Khuê nghỉ.'),
                dict(id='why', title='Lý do của Linh', text='Khách đang hỏi tiến độ đơn hàng, Linh cần trả lời trong hôm nay.')],
         options=[dict(id='forward', label='Không đổi mật khẩu; thiết lập chuyển tiếp thư của khách đó sang Linh theo duyệt của trưởng phòng',
                       requires=['rule', 'boss'], _q='good', _out='Linh trả lời khách kịp; hộp thư riêng của chị Khuê vẫn được tôn trọng.'),
                  dict(id='no', label='Từ chối, bảo Linh chờ chị Khuê về', requires=[], _q='ok', _out='Khách chờ ba ngày không ai trả lời.'),
                  dict(id='reset', label='Đổi mật khẩu đưa Linh cho nhanh', requires=['why'], _q='bad', _sev=3,
                       _out='Chị Khuê về thấy thư riêng đã bị đọc; bạn bị lập biên bản vi phạm bảo mật.')]),
    dict(id='readmail', npc=1, title='Giám đốc muốn đọc email nhân viên sắp nghỉ',
         opening='Anh Quân: “Thằng Tuấn kinh doanh sắp nghỉ. Em mở hộp thư của nó cho anh đọc hết xem nó có mang khách đi không.”',
         facts=[dict(id='rule', title='Quy chế sử dụng email', text='Email công ty có thể được kiểm tra khi có lý do, bằng quyết định văn bản, có nhân sự chứng kiến.'),
                dict(id='hr', title='Hỏi chị Huyền', text='Chị Huyền đề nghị làm theo quy chế: quyết định, biên bản, chỉ xem thư công việc.'),
                dict(id='private', title='Hộp thư của Tuấn', text='Có cả thư từ gia đình, ngân hàng cá nhân.')],
         options=[dict(id='proper', label='Đề nghị anh Quân ra quyết định văn bản, có chị Huyền chứng kiến, chỉ xem thư công việc',
                       requires=['rule', 'hr'], _q='good', _out='Việc kiểm tra đúng quy chế; tìm ra hai thư chuyển báo giá ra ngoài, xử lý có căn cứ.'),
                  dict(id='refuse', label='Từ chối thẳng: “Không được đâu anh”', requires=[], _q='ok', _out='Anh Quân bực, nhờ người khác làm lén.'),
                  dict(id='open', label='Mở hết hộp thư cho anh Quân đọc', requires=['private'], _q='bad', _sev=3,
                       _out='Đọc cả thư riêng; Tuấn biết chuyện, công ty bị khiếu nại vi phạm đời tư.')]),
    dict(id='usb', npc=4, title='USB nhặt ở bãi xe',
         opening='Chú Lâm cầm một chiếc USB: “Nhặt ở bãi xe, ngoài ghi ‘Lương 2025 – Mật’. Cắm vào máy xem của ai để trả nhé?”',
         facts=[dict(id='rule', title='Quy định thiết bị lạ', text='Không cắm thiết bị lạ vào máy công ty; giao IT kiểm tra trên máy cách ly.'),
                dict(id='trick', title='Anh Long kể', text='Rải USB có nhãn hấp dẫn là chiêu quen của kẻ gian để cài mã độc.'),
                dict(id='label', title='Nhãn USB', text='Chữ in, không có tên người hay phòng ban nào.')],
         options=[dict(id='isolate', label='Không cắm; niêm phong, giao anh Long kiểm tra trên máy cách ly, nhắc cả xưởng',
                       requires=['rule', 'trick'], _q='good', _out='USB chứa mã độc thật. Cả xưởng được nhắc, không ai cắm nữa.'),
                  dict(id='bin', label='Vứt luôn vào thùng rác', requires=[], _q='ok', _out='An toàn cho máy, nhưng không ai biết có kẻ đang rải USB.'),
                  dict(id='plug', label='Cắm thử vào máy kế toán xem của ai', requires=['label'], _q='bad', _sev=3,
                       _out='Mã độc chạy ngay, máy kế toán bị khóa cả ngày chốt lương.')]),
]


def g_case(rng, ctx: dict) -> dict:
    return ow.case_work(rng, CASES)


# ================================================================ the office around the dossiers
MODS = [
    dict(id='normal', min_day=1, weight=3, emoji='☀️', name='Ngày bình thường', text='Phiếu hỗ trợ đều đều, anh Long ngồi góc phòng máy.'),
    dict(id='outage', min_day=2, weight=2, emoji='⚡', name='Mất điện sáng nay', text='Điện vừa có lại: máy nào cũng có chuyện, phiếu dày hơn.'),
    dict(id='drill', min_day=2, weight=2, emoji='🎣', name='Tuần diễn tập lừa đảo', text='Anh Long âm thầm thử cả công ty — mọi thứ có thể đổi bất ngờ.'),
    dict(id='audit', min_day=2, weight=2, emoji='🔍', name='Kiểm tra an toàn thông tin', text='Cuối ngày anh Long soát lại việc bạn làm.'),
    dict(id='move', emoji='🚚', name='Chuyển máy chủ cuối tháng', forced_only=True,
         text='Đêm nay chuyển máy chủ sang tủ mới: hạn gấp. Tăng ca hôm nay được trả 18 xu.'),
]


def rules(day: int) -> list:
    return [dict(id='prio', emoji='🚦', title='Ưu tiên', text='Nhiều người dừng việc hoặc sự cố an ninh: làm ngay. Chữ “GẤP” không đổi mức độ.'),
            dict(id='safe', emoji='🧯', title='An toàn', text='Tắt máy, rút điện rồi mới mở. Sự cố an ninh: cách ly trước.'),
            dict(id='net', emoji='🔌', title='Mạng', text='Kế toán riêng, khách riêng, camera riêng. Xếp theo người, không theo bàn.'),
            dict(id='access', emoji='🔐', title='Quyền truy cập', text='Nghỉ việc thu hồi ngay; chỉ cấp khi phiếu đã duyệt.'),
            dict(id='secret', emoji='🤐', title='Bí mật', text='Không ai được hỏi OTP hay mật khẩu. Không cắm thiết bị lạ.')]


DESK = [
    dict(id='postit', title='Mật khẩu dán trên màn hình', emoji='🗒️', npc=1, min_day=2, tone='gentle', at='between', weight=3, mods=None,
         text='Anh Quân dán mật khẩu email ngay mép màn hình, khách ra vào phòng ai cũng thấy.',
         options=[dict(id='manager', label='Cài trình quản lý mật khẩu cho sếp, gỡ tờ giấy', hint='Mất 15 phút', effects=dict(time=15, xp=6), good=True,
                       outcome='Sếp càu nhàu năm phút rồi khen: “Tiện thật, khỏi nhớ.”'),
                  dict(id='hide', label='Bảo sếp dán vào mặt dưới bàn phím', hint='', effects={}, good=None, outcome='Tờ giấy chuyển chỗ, vẫn là tờ giấy.'),
                  dict(id='ignore', label='Kệ, việc của sếp', hint='', effects=dict(trust=-2), good=False, outcome='Tuần sau khách chụp ảnh màn hình sếp, mật khẩu lọt vào khung hình.')],
         default='ignore'),
    dict(id='kick', title='Chú Lâm đá máy in', emoji='🦶', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Máy in xưởng kẹt, Chú Lâm đá một phát “cho nó tỉnh”. Máy kêu rè rè.',
         options=[dict(id='show', label='Chỉ chú cách gỡ kẹt giấy, dán hướng dẫn cạnh máy', hint='Mất 15 phút', effects=dict(time=15, xp=5), good=True,
                       outcome='Lần sau chú tự gỡ được, còn dạy lại thợ trẻ.'),
                  dict(id='fix', label='Tự sửa, không nói gì', hint='Mất 10 phút', effects=dict(time=10), good=None, outcome='Tuần sau máy lại bị đá.'),
                  dict(id='scold', label='Mắng chú trước cả xưởng', hint='', effects=dict(review=[2, 'Cậu IT mắng tôi như mắng con.']), good=False,
                       outcome='Chú Lâm giận, từ đó máy hỏng cũng không báo.')],
         default='fix'),
    dict(id='guestwifi', title='Khách xin wifi nội bộ', emoji='📶', npc=5, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Khách của sếp xin mật khẩu wifi “cái mạnh nhất ấy”, tức là mạng nội bộ.',
         options=[dict(id='guest', label='Đưa mật khẩu mạng khách, xin lỗi vì quy định', hint='', effects=dict(xp=4), good=True,
                       outcome='Khách gật gù: “Công ty nhỏ mà bảo mật kỹ nhỉ.”'),
                  dict(id='give', label='Đưa mạng nội bộ cho khách vui', hint='', effects=dict(trust=-3), good=False,
                       outcome='Máy khách có mã độc, quét khắp mạng nội bộ cả buổi chiều.'),
                  dict(id='none', label='Bảo wifi hỏng', hint='', effects=dict(review=[3, 'Hỏi wifi thì bảo hỏng, ngồi họp không mạng.']), good=None,
                       outcome='Khách dùng 4G, họp hơi giật.')],
         default='none'),
    dict(id='gamelap', title='Laptop sếp cho con chơi game', emoji='🎮', npc=1, min_day=3, tone='gentle', at='open', weight=2, mods=None,
         text='Thứ Hai, laptop của sếp đầy game lạ, máy chạy ì ạch: cuối tuần con sếp mượn chơi.',
         options=[dict(id='talk', label='Gỡ game, quét máy, xin sếp đừng cho mượn máy công ty; gợi ý tài khoản riêng cho bé', hint='Mất 20 phút', effects=dict(time=20, xp=6),
                       good=True, outcome='Có một game kèm phần mềm theo dõi; gỡ kịp. Sếp hứa mua máy riêng cho con.'),
                  dict(id='silent', label='Lặng lẽ gỡ game', hint='Mất 15 phút', effects=dict(time=15), good=None, outcome='Tuần sau game lại về đầy máy.'),
                  dict(id='leave', label='Để nguyên, máy sếp mà', hint='', effects=dict(trust=-2), good=False, outcome='Máy sếp bị cài phần mềm quảng cáo, bật lên là nhảy trang lạ.')],
         default='leave'),
    dict(id='phonefix', title='Nhờ sửa điện thoại cá nhân', emoji='📱', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Linh đặt điện thoại vỡ màn lên bàn: “Anh IT khéo tay, sửa giúp em đi mà!” Hàng phiếu hỗ trợ còn dài.',
         options=[dict(id='shop', label='Từ chối khéo, giới thiệu tiệm sửa uy tín gần công ty', hint='', effects=dict(xp=3), good=True,
                       outcome='Linh hơi tiu nghỉu nhưng tiệm sửa nhanh, rẻ.'),
                  dict(id='fix', label='Sửa giúp trong giờ làm', hint='Mất 30 phút', effects=dict(time=30, trust=-1), good=False,
                       outcome='Phiếu hỗ trợ dồn ứ; anh Long nhìn đồng hồ.'),
                  dict(id='later', label='Hẹn giờ nghỉ trưa xem thử', hint='', effects={}, good=None, outcome='Mất bữa trưa, màn vẫn vỡ.')],
         default='later'),
    dict(id='sharedpwd', title='Cả phòng dùng chung một mật khẩu', emoji='🔑', npc=2, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Bạn phát hiện cả phòng kế toán dùng chung một tài khoản phần mềm, mật khẩu là “123456”. Cô Hằng: “Cho tiện, xưa nay vẫn vậy.”',
         options=[dict(id='each', label='Tạo tài khoản riêng từng người, hướng dẫn đặt mật khẩu mạnh', hint='Mất 25 phút', effects=dict(time=25, xp=6, trust=1), good=True,
                       outcome='Lần đầu tiên biết ai sửa số liệu nào. Cô Hằng thừa nhận: “Rõ ràng hơn thật.”'),
                  dict(id='change', label='Chỉ đổi mật khẩu chung cho mạnh hơn', hint='', effects={}, good=None, outcome='Mạnh hơn, nhưng vẫn không biết ai làm gì.'),
                  dict(id='leave', label='Thôi, cô Hằng khó tính lắm', hint='', effects=dict(trust=-2), good=False, outcome='Ba tháng sau số liệu bị sửa sai, không ai biết là ai.')],
         default='leave'),
    dict(id='midnight', title='Sếp gọi 10 giờ tối', emoji='🌙', npc=1, min_day=3, tone='gentle', at='open', weight=2, mods=None,
         text='Sáng nay mở điện thoại: tối qua 10 giờ sếp gọi năm cuộc, nhắn “Wifi nhà anh hỏng!!!”.',
         options=[dict(id='kind', label='Gọi lại, hướng dẫn sếp khởi động lại bộ phát nhà; nhẹ nhàng nói giờ hỗ trợ', hint='', effects=dict(xp=4), good=True,
                       outcome='Sếp cười: “Ừ, việc nhà anh tự lo. Cảm ơn em.”'),
                  dict(id='rush', label='Hứa tối nay qua nhà sếp sửa', hint='', effects=dict(trust=1), good=None, outcome='Mất buổi tối, và từ đó tối nào cũng có cuộc gọi.'),
                  dict(id='ignore', label='Lờ đi coi như không thấy', hint='', effects=dict(trust=-2), good=False, outcome='Sếp hỏi: “Tối qua em đi đâu?”')],
         default='ignore'),
    dict(id='cables', title='Dây điện chằng chịt dưới bàn', emoji='🔌', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Dưới bàn kinh doanh, ổ điện cắm nối ổ điện, nóng ran. Linh vừa cắm thêm ấm siêu tốc.',
         options=[dict(id='fix', label='Rút ấm siêu tốc, gom dây, xin thêm ổ điện an toàn', hint='Mất 15 phút', effects=dict(time=15, xp=6), good=True,
                       outcome='Ổ điện nguội hẳn. Anh Long gật đầu: “Suýt cháy đấy.”'),
                  dict(id='later', label='Ghi vào kế hoạch tuần sau', hint='', effects={}, good=None, outcome='Tuần đó ổ điện bốc mùi khét, may phát hiện kịp.'),
                  dict(id='ignore', label='Không phải việc IT', hint='', effects=dict(trust=-2), good=False, outcome='Nhảy aptomat cả tầng giữa buổi họp online.')],
         default='later'),
    dict(id='blame', title='“Em chưa làm gì mà nó tự hỏng”', emoji='🤷', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Máy Linh không lên. Linh thề chưa làm gì, nhưng lịch sử máy ghi rõ: tối qua cài ba phần mềm lạ.',
         options=[dict(id='teach', label='Sửa máy, chỉ Linh xem lịch sử cài đặt, nhắc nhẹ quy định', hint='Mất 15 phút', effects=dict(time=15, xp=5), good=True,
                       outcome='Linh đỏ mặt: “Em xin lỗi, em sẽ hỏi trước khi cài.”'),
                  dict(id='report', label='Báo thẳng lên sếp', hint='', effects=dict(review=[2, 'Có chút chuyện cũng mách sếp.']), good=False,
                       outcome='Linh bị nhắc nhở, từ đó máy hỏng cũng giấu.'),
                  dict(id='fix', label='Sửa xong, không nói gì', hint='Mất 10 phút', effects=dict(time=10), good=None, outcome='Tuần sau máy lại hỏng y hệt.')],
         default='fix'),
]

SITUATIONS = [
    dict(id='IT-S01', title='Sếp muốn xem màn hình nhân viên', npc=1, tone='tense', min_day=2,
         opening='Anh Quân: “Em cài phần mềm theo dõi màn hình cả phòng kinh doanh cho anh. Anh muốn biết ai lướt mạng giờ làm.”',
         swap='Bạn là giám đốc lo doanh số tụt, nghi nhân viên làm việc riêng.',
         facts=[dict(id='rule', title='Quy chế', source='Chị Huyền', text='Giám sát máy công ty phải thông báo rõ cho nhân viên, có mục đích cụ thể.'),
                dict(id='data', title='Số liệu', source='Báo cáo kinh doanh', text='Doanh số tụt từ khi mất hai khách lớn, không phải do lướt mạng.'),
                dict(id='trust', title='Không khí phòng', source='Linh', text='Nhân viên đang lo lắng vì tin đồn cắt giảm.')],
         options=[dict(id='open', label='Đề xuất công khai chính sách sử dụng máy, chỉ ghi nhật ký truy cập web, kèm báo cáo doanh số thật',
                       requires=['rule', 'data'], quality='good', stars=5, review='Có quy định rõ ràng thì ai cũng yên tâm làm.',
                       outcome='Sếp thấy lý do thật của doanh số tụt; phòng kinh doanh tập trung lấy lại khách.',
                       perspectives=[dict(who='Linh', emoji='📦', text='Quy định rõ, không ai bị rình.'),
                                     dict(who='Anh Quân', emoji='🧑‍💼', text='Hóa ra vấn đề ở khách hàng.')]),
                  dict(id='secret', label='Cài lén như sếp bảo', quality='bad', stars=1, review='Phát hiện máy bị theo dõi lén. Mất hết tin tưởng.',
                       outcome='Nhân viên phát hiện, hai người nghỉ việc, không khí đi xuống.',
                       perspectives=[dict(who='Linh', emoji='😠', text='Bị rình như kẻ trộm.')]),
                  dict(id='refuse', label='Từ chối, không đề xuất gì', quality='ok', stars=3, review='Không cài, nhưng sếp vẫn nghi ngờ mọi người.',
                       outcome='Sếp nhờ người ngoài cài.', perspectives=[dict(who='Anh Long', emoji='🖥️', text='Từ chối thôi chưa đủ, phải có cách khác.')])],
         lesson='Bảo mật và tôn trọng đi cùng nhau: minh bạch trước khi giám sát.'),
    dict(id='IT-S02', title='Đồng nghiệp lớn tuổi sợ phần mềm mới', npc=2, tone='gentle', min_day=2,
         opening='Cô Hằng thở dài: “Phần mềm kế toán mới nhiều nút quá. Cô làm 20 năm rồi, giờ thành người mù chữ.”',
         swap='Bạn là kế toán trưởng giỏi nghề, nhưng sợ thành chậm chạp trước người trẻ.',
         facts=[dict(id='guide', title='Tài liệu', source='Nhà cung cấp', text='Có video hướng dẫn 10 phút cho từng nghiệp vụ.'),
                dict(id='time', title='Lịch chốt sổ', source='Kế toán', text='Còn hai tuần nữa mới chốt quý.'),
                dict(id='old', title='Phần mềm cũ', source='Anh Long', text='Có thể chạy song song phần mềm cũ thêm hai tuần.')],
         options=[dict(id='pair', label='Ngồi cùng cô 30 phút mỗi chiều, làm thử nghiệp vụ thật, chạy song song phần mềm cũ hai tuần',
                       requires=['time', 'old'], quality='good', stars=5, review='Cậu IT kiên nhẫn ghê. Hai tuần là cô thạo.',
                       outcome='Cô Hằng thạo phần mềm mới, còn chỉ lại cho kế toán trẻ.',
                       perspectives=[dict(who='Cô Hằng', emoji='📒', text='Không ai bỏ cô lại phía sau.')]),
                  dict(id='video', label='Gửi link video hướng dẫn', quality='ok', stars=3, review='Video nhanh quá, cô xem không kịp.',
                       outcome='Cô Hằng tự mò, chốt sổ trễ một ngày.', perspectives=[dict(who='Cô Hằng', emoji='😓', text='Cần người chỉ tận tay.')]),
                  dict(id='rush', label='Bảo cô cố lên, ai cũng phải học', quality='bad', stars=2, review='Nói thì dễ.',
                       outcome='Cô Hằng nhờ kế toán trẻ làm hộ, sai số liệu.', perspectives=[dict(who='Anh Long', emoji='🖥️', text='Thay đổi cần người đồng hành.')])],
         lesson='Công nghệ mới thành công khi người dùng cũ được đồng hành.'),
    dict(id='IT-S03', title='Lỗi của chính mình', npc=0, tone='gentle', min_day=3,
         opening='Sáng nay bạn đổi cấu hình máy chủ, lỡ chặn luôn máy in kế toán. Cô Hằng đang ầm ĩ: “Ai phá máy in của tôi?”',
         swap='Bạn là trưởng nhóm IT, muốn người mới dám nhận lỗi.',
         facts=[dict(id='log', title='Nhật ký thay đổi', source='Máy chủ', text='Thay đổi lúc 07:45 bởi tài khoản của bạn.'),
                dict(id='fix', title='Cách sửa', source='Anh Long', text='Hoàn tác thay đổi mất 5 phút.'),
                dict(id='impact', title='Ảnh hưởng', source='Kế toán', text='Kế toán chậm in phiếu chi một tiếng.')],
         options=[dict(id='own', label='Nhận lỗi với cô Hằng, hoàn tác ngay, ghi nhật ký và đề xuất thử cấu hình trước khi áp dụng',
                       requires=['log', 'fix'], quality='good', stars=5, review='Cậu ấy nhận lỗi ngay, sửa nhanh. Đáng tin.',
                       outcome='Máy in chạy lại sau 5 phút; nhóm IT có thêm quy trình thử trước.',
                       perspectives=[dict(who='Anh Long', emoji='🖥️', text='Ai cũng có lúc sai, quan trọng là sửa và rút kinh nghiệm.')]),
                  dict(id='quiet', label='Lặng lẽ sửa, không nói gì', quality='ok', stars=3, review='Tự dưng máy in chạy lại, chẳng ai giải thích.',
                       outcome='Cô Hằng vẫn nghi có người phá máy.', perspectives=[dict(who='Cô Hằng', emoji='🤨', text='Có gì mờ ám chăng?')]),
                  dict(id='blame', label='Đổ cho máy in cũ', quality='bad', stars=1, review='Bảo máy in cũ, rồi lại tự chạy lại sau khi cậu ấy ngồi vào máy chủ…',
                       outcome='Anh Long xem nhật ký, biết sự thật; lòng tin sứt mẻ.', perspectives=[dict(who='Anh Long', emoji='😞', text='Nhật ký không biết nói dối.')])],
         lesson='Nhật ký ghi lại mọi thứ — nhận lỗi sớm là cách nhanh nhất để được tin.'),
]

CARE = dict(
    id=ID, prefix=P, boss=BOSS,
    ranks=('Thử việc', 'Kỹ thuật viên chính thức', 'Phụ trách an toàn thông tin', 'Được đề cử phó nhóm IT'),
    lines=('Ba ngày không để sót phiếu khẩn nào. Anh ký chính thức cho em.',
           'Từ nay em phụ trách an toàn thông tin. Ai hỏi mật khẩu cứ chỉ sang em.',
           'Anh đề cử em làm phó nhóm. Anh nghỉ phép cũng yên tâm.'),
    mates=[
        dict(id='khoa', name='Khoa', role='Thực tập sinh IT', npc=None, emoji='🐣',
             asks=[('Anh chỉ em cách bấm đầu dây mạng với, em bấm hỏng ba đầu rồi…', 20),
                   ('Phiếu này ghi “máy chạy chậm”, em nên hỏi người ta thêm gì ạ?', 15)],
             thanks='Khoa ghi vội vào sổ: “Hiểu rồi ạ!”', no='Khoa gật đầu: “Dạ, em xem video vậy.”', cover='Khoa chạy đi lấy linh kiện giúp —'),
        dict(id='hang', name='Cô Hằng', role='Kế toán trưởng', npc=2, emoji='📒',
             asks=[('Máy cô hiện thông báo cập nhật, có bấm được không cháu?', 10),
                   ('Cháu sao lưu giúp cô thư mục báo cáo quý nhé, cô lo lắm.', 20)],
             thanks='Cô Hằng hiếm hoi mỉm cười: “Cháu được việc đấy.”', no='Cô Hằng: “Ừ, để mai vậy.”', cover='Cô Hằng tự gom sẵn máy cần sửa —'),
        dict(id='nhi', name='Nhi', role='Lễ tân', npc=5, emoji='🛎️',
             asks=[('Máy in thẻ khách bị lệch chữ, anh xem giúp em?', 15),
                   ('Khách hỏi wifi, em nên đưa mạng nào ạ?', 10)],
             thanks='Nhi để lên bàn hộp sữa chua: “Em cảm ơn anh!”', no='Nhi: “Dạ, em hỏi anh Long vậy.”', cover='Nhi chặn bớt khách hỏi vặt giúp —'),
    ])

FORMS = [dict(id='tickets', label='Phiếu hỗ trợ', min_day=1, bonus=25, build=g_tickets),
         dict(id='fix', label='Sửa sự cố', min_day=1, bonus=20, build=g_fix),
         dict(id='asset', label='Sổ tài sản', min_day=1, bonus=20, build=g_asset),
         dict(id='patch', label='Tủ mạng', min_day=2, bonus=25, build=g_patch),
         dict(id='access', label='Quyền truy cập', min_day=2, bonus=25, build=g_access),
         dict(id='case', label='Chiêu lừa', min_day=3, bonus=20, build=g_case)]

JOB = ow.OfficeJob(dict(
    id=ID, prefix=P, boss=BOSS, boss_npc=0, forms=FORMS, mods=MODS, forced={4: 'move'}, intro={2: 'outage', 3: 'drill', 4: 'audit'},
    more_mods=('outage',), busy_mod='drill', crunch='move', audit='audit', auditor='Anh Long', helpers=('Anh Long',), care=CARE, desk=DESK,
    rules=rules,
    hints=dict(tickets='Đọc bảng ưu tiên → chạm từng phiếu, chọn khay. Hỏi: bao nhiêu người dừng việc? có dính an ninh không?',
               fix='Chạm từng bước để thêm vào danh sách theo thứ tự; bước gây hại thì bỏ ra. An toàn điện và cách ly trước.',
               patch='Đọc quy định mạng → chạm từng ổ, chọn mạng. Xếp theo người đang dùng, không theo bàn.',
               access='Đối chiếu từng ô với danh sách nghỉ việc và phiếu yêu cầu: chạm ô cần đổi, chọn cấp hoặc thu hồi.',
               asset='Đọc tem máy, hóa đơn, sổ tài sản và phiếu bàn giao rồi ghi đủ các ô. S/N lấy trên tem máy.',
               case='Tìm hiểu từng chuyện trước, rồi chọn cách vừa an toàn vừa không làm khó người ta.'),
    staff_area={'support': ('tickets', 'fix', 'asset'), 'network': ('patch', 'access')},
))
JOB.bind(globals())

EMPLOYMENT = dict(
    postings=[
        dict(id='it-canhdieu', org='Công ty CP Cánh Diều', kind='corp', title='Kỹ thuật viên IT hỗ trợ',
             salary=(55, 80), probation_days=3, wants=['tech', 'careful', 'patience'],
             perks=['Có trưởng nhóm kèm', 'Đủ loại sự cố', 'Hay bị gọi “GẤP”'],
             culture='Công ty 80 người, một tủ mạng, một máy chủ và rất nhiều máy in kẹt giấy.',
             questions=['it_otp', 'it_priority', 'mistake'], reference=True),
        dict(id='it-shop', org='Tiệm máy tính Bit Xanh', kind='private', title='Thợ sửa máy tính',
             salary=(50, 70), probation_days=2, wants=['tech', 'learning'],
             perks=['Học nghề nhanh', 'Khách lẻ đông', 'Làm cả cuối tuần'],
             culture='Tiệm nhỏ sửa máy, cài phần mềm, cứu dữ liệu cho khách quanh khu.',
             questions=['it_otp', 'conflict'], reference=False),
    ],
    questions={
        'it_otp': dict(text='Một người tự xưng nhà mạng gọi xin mã OTP để “nâng cấp sim”. Bạn làm gì?', options=[
            dict(id='hang', label='Từ chối, cúp máy, gọi tổng đài chính thức kiểm tra, cảnh báo mọi người', score=3, note='Đúng phản xạ an ninh.'),
            dict(id='ask', label='Hỏi tên, mã nhân viên rồi mới đưa', score=0, note='Kẻ gian luôn có sẵn tên và mã giả.'),
            dict(id='wait', label='Bảo họ gọi lại sau', score=1, note='Chưa mất gì nhưng chưa cảnh báo ai.')]),
        'it_priority': dict(text='Giám đốc báo màn hình nhấp nháy “GẤP”, cùng lúc cả phòng kế toán mất mạng. Bạn làm gì trước?', options=[
            dict(id='acct', label='Xử lý mạng kế toán trước, nhắn sếp giờ sẽ qua', score=3, note='Ưu tiên theo mức ảnh hưởng.'),
            dict(id='boss', label='Sếp trước, sếp mà', score=0, note='Cả phòng dừng việc vì chờ một màn hình nhấp nháy.'),
            dict(id='both', label='Chạy qua lại cả hai', score=1, note='Cái nào cũng dở dang.')]),
    },
)

SPEC = dict(
    id=ID, prefix=P, category='office',
    meta=dict(short='IT hỗ trợ', place='Công ty CP Cánh Diều', tagline='Máy chạy êm, dữ liệu an toàn, không ai bị lừa.', icon='settings',
              color='#2f6f9f', light='#e3eff8', weather='Phòng máy mát lạnh, quạt máy chủ rì rầm', work='Phiếu', station='Góc IT',
              greeting='Phiếu hỗ trợ sáng nay đã xếp hàng. Việc gấp thật làm trước, và đừng tin ai xin mật khẩu nhé.',
              caption='Sửa máy là sửa cả ngày làm của người khác', map_label='22 · CÁNH DIỀU · IT'),
    people=PEOPLE,
    staff=[('Khoa', 'support', 'Thực tập sinh, bấm đầu dây mạng còn run.', 68, 94),
           ('Anh Long', 'network', 'Thuộc từng sợi dây trong tủ mạng.', 92, 88),
           ('Nhi', 'support', 'Lễ tân, báo lỗi rất rõ ràng.', 70, 92)],
    roles={'support': 'Hỗ trợ người dùng', 'network': 'Mạng & bảo mật'},
    tip=0,
    physical=(),
    free_actions=(),
    no_tick=(P + 'put', P + 'mark', P + 'place', P + 'read', P + 'hint', P + 'desk', P + 'overtime', P + 'help', P + 'cover', P + 'break'),
    employment=EMPLOYMENT,
    activity=('🖥️', 'Góc IT gọn gàng', [('Phiếu hỗ trợ', 'Hàng chờ'), ('Dây mạng', 'Tủ mạng'), ('Laptop mới', 'Sổ tài sản'), ('Quyền truy cập', 'Bảo mật')],
              ['Phân loại phiếu', 'Sửa sự cố', 'Đấu dây mạng', 'Rà quyền truy cập']),
    stories=[('Màn hình đỏ của Linh', ('Linh mở hóa đơn lạ, màn hình đỏ đòi tiền chuộc.',
                                       'Bạn rút dây mạng ngay, khôi phục từ bản sao lưu đêm trước.',
                                       'Không mất một file nào; cả công ty học được bài “hóa đơn lạ”.')),
             ('Chiếc USB ở bãi xe', ('Chú Lâm nhặt được USB ghi “Lương 2025 – Mật”.',
                                     'Bạn kiểm tra trên máy cách ly: mã độc thật.',
                                     'Chú Lâm kể chuyện cho cả xưởng, từ đó không ai cắm đồ lạ.')),
             ('Máy in xưởng', ('Máy in xưởng kẹt giấy mỗi ngày, Chú Lâm đá cho “tỉnh”.',
                               'Bạn chỉ chú cách gỡ kẹt, dán hướng dẫn cạnh máy.',
                               'Một tháng không có phiếu máy in xưởng nào.'))],
    review_asides=['Sửa nhanh, giải thích dễ hiểu.', 'Không làm mất dữ liệu.', 'Kiên nhẫn với người không rành máy.', 'Cẩn thận với mật khẩu.'],
    situations=SITUATIONS,
    guide='Mỗi phiếu là một việc thật: phân loại phiếu hỗ trợ, sửa sự cố từng bước, đấu dây tủ mạng, rà quyền truy cập, nhập sổ tài sản, nói “không” với chiêu lừa. Đọc giấy tờ bên cạnh, rồi nộp trước giờ hạn. Mọi thứ có thể đổi giữa chừng — đọc kỹ tin báo rồi sửa lại. Lương ngày trả khi khép ca.',
)
