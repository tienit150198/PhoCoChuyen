"""Chức vụ & cấp bậc: the content of every org ladder (game/org.py is the engine). Data only.

An org has two separate tracks (owner spec 06/10):
* **grades** (cấp bậc hàm / hạng): rise with worked days in the grade, the ★ of the last days and a clean record, up
  to the post's ceiling (`max`). A grade may ask for a course (a two-question exam) or a clean record first.
* **posts** (chức vụ): change only by appointment (bổ nhiệm): the post's `min` grade (or one below it, promoted on
  appointment), days in the current post, ★, no open warning, a vacancy and a short interview.

Insignia (`ins`) are drawn by public/js/v4/insignia.js, generic for every org:
  base 'nco' | 'officer' | 'general' | 'cadet'   the board's colour (owner spec 11/10: red #EE0000, the general #DD0000,
                                                 yellow marks; 'cadet' the plain board of a Học viên)
  v  chevrons (vạch chữ V)          h  straight stripes (vạch ngang)
  b  long bars (1 cấp úy, 2 cấp tá) s  stars                big  one big star (cấp tướng)
Another org may later add its own shape keys (the pilot keeps promotion_content.INSIGNIA for now).

Everything is fictional: Công an phường Mây, Phòng PC06 Công an Thành phố and its people are invented.
"""
from __future__ import annotations


def _g(gid, name, ins, days, need, gate=None, coef=None):
    """A grade. days: worked days in it before the next; need: the ★ (tenths) of the last days for the next."""
    return dict(id=gid, name=name, ins=ins, days=days, need=need, gate=gate, coef=coef)


def _p(pid, name, short, level, lo, hi, days=0, need=38, frm=(), olv=None, bonus=0, chain='ward', extra=None, npc=None):
    """A post. lo: the grade it needs (hàm chuẩn), hi: its ceiling (trần); days: worked days in it before the next
    appointment; need: ★ (tenths) for the appointment; frm: the posts it is appointed from; olv: the management office
    level (None: no office); bonus: % on the pay; extra: more gates (good evals, no integrity mark)."""
    return dict(id=pid, name=name, short=short, level=level, lo=lo, hi=hi, days=days, need=need, frm=tuple(frm), olv=olv,
                bonus=bonus, chain=chain, extra=extra or {}, npc=npc)


NCO, OFFICER, GENERAL = 'nco', 'officer', 'general'   # the game's palette (v4/insignia.js), not the real colours

CAND_GRADES = (
    _g('binh_nhi', 'Binh nhì', dict(base=NCO, v=1), 3, 30, coef=3.0),
    _g('binh_nhat', 'Binh nhất', dict(base=NCO, v=2), 3, 30, coef=3.1),
    _g('ha_si', 'Hạ sĩ', dict(base=NCO, h=1), 4, 32, coef=3.2),
    _g('trung_si', 'Trung sĩ', dict(base=NCO, h=2), 4, 35, coef=3.5),
    _g('thuong_si', 'Thượng sĩ', dict(base=NCO, h=3), 5, 35, 'course:chuyen_loai', coef=3.8),
    _g('thieu_uy', 'Thiếu úy', dict(base=OFFICER, b=1, s=1), 6, 38, coef=4.2),
    _g('trung_uy', 'Trung úy', dict(base=OFFICER, b=1, s=2), 6, 38, coef=4.6),
    _g('thuong_uy', 'Thượng úy', dict(base=OFFICER, b=1, s=3), 8, 40, coef=5.0),
    _g('dai_uy', 'Đại úy', dict(base=OFFICER, b=1, s=4), 8, 40, 'course:chi_huy_co_so', coef=5.4),
    _g('thieu_ta', 'Thiếu tá', dict(base=OFFICER, b=2, s=1), 10, 42, coef=6.0),
    _g('trung_ta', 'Trung tá', dict(base=OFFICER, b=2, s=2), 10, 43, 'course:chi_huy_tp', coef=6.6),
    _g('thuong_ta', 'Thượng tá', dict(base=OFFICER, b=2, s=3), 12, 45, 'clean', coef=7.3),
    # Đại tá → Thiếu tướng (owner spec 11/10): only as Giám đốc CATP, 10 worked days at Đại tá, and 30 worked days in a
    # row without any violation (the 20 days as PGĐ before the appointment and these 10).
    _g('dai_ta', 'Đại tá', dict(base=OFFICER, b=2, s=4), 10, 45, 'clean:30', coef=8.0),
    _g('thieu_tuong', 'Thiếu tướng', dict(base=GENERAL, s=1), None, None, coef=9.0),     # the Giám đốc CATP's ceiling
)
# 🎓 Học viên (owner spec 11/10): a Thượng sĩ who passed the officer course shows a plain red board until the
# commission (the next day's close: Thiếu úy). A display only: the record keeps the grade Thượng sĩ.
CADET = dict(id='hoc_vien', name='Học viên', ins=dict(base='cadet'), course='chuyen_loai', grade='thuong_si')

# Ward chain → (transfer) city. Trưởng phòng PC06's ceiling is Thượng tá (owner OK 06/10), so the way to PGĐ works.
CAND_POSTS = (
    _p('to_vien', 'Tổ viên Tổ Tuần tra – Trực ban', 'Tổ viên', 'phuong', 'binh_nhi', 'thieu_uy'),
    _p('to_pho', 'Tổ phó Tổ Tuần tra – Trực ban', 'Tổ phó', 'phuong', 'trung_uy', 'trung_uy', 6, frm=('to_vien',), bonus=3),
    _p('to_truong', 'Tổ trưởng Tổ Tuần tra – Trực ban', 'Tổ trưởng', 'phuong', 'thuong_uy', 'thuong_uy', 8, frm=('to_pho',), olv=1, bonus=5),
    _p('doi_pho', 'Đội phó Đội 113', 'Đội phó', 'phuong', 'dai_uy', 'dai_uy', 8, frm=('to_truong',), olv=2, bonus=6),
    _p('doi_truong', 'Đội trưởng Đội 113', 'Đội trưởng', 'phuong', 'dai_uy', 'dai_uy', 8, frm=('doi_pho',), olv=2, bonus=8),
    _p('pho_truong_ca', 'Phó Trưởng Công an phường Mây', 'Phó Trưởng CA phường', 'phuong', 'thieu_ta', 'thieu_ta', 10,
       frm=('doi_truong',), olv=3, bonus=10),
    _p('truong_ca', 'Trưởng Công an phường Mây', 'Trưởng CA phường', 'phuong', 'trung_ta', 'trung_ta', 10, need=40,
       frm=('pho_truong_ca',), olv=3, bonus=12),
    _p('pho_phong', 'Phó phòng PC06 Công an Thành phố', 'Phó phòng PC06', 'tp', 'thieu_ta', 'trung_ta', 10, need=40,
       frm=('truong_ca', 'pho_truong_ca'), olv=3, bonus=12, chain='city'),
    _p('truong_phong', 'Trưởng phòng PC06 Công an Thành phố', 'Trưởng phòng PC06', 'tp', 'trung_ta', 'thuong_ta', 10, need=42,
       frm=('pho_phong',), olv=3, bonus=15, chain='city'),
    _p('tro_ly', 'Thư ký – Trợ lý Ban Giám đốc', 'Trợ lý BGĐ', 'tp', 'trung_ta', 'thuong_ta', 12, need=42,
       frm=('truong_ca', 'pho_phong', 'truong_phong'), olv=4, bonus=12, chain='aide', extra=dict(good_evals=3, nomark=True)),
    # PGĐ → GĐ: 20 worked days as PGĐ, every one without a violation (owner spec 11/10).
    _p('pgd', 'Phó Giám đốc Công an Thành phố', 'Phó Giám đốc CATP', 'tp', 'thuong_ta', 'dai_ta', 20, need=45,
       frm=('truong_phong', 'tro_ly'), olv=5, bonus=20, chain='city', extra=dict(nomark=True)),
    _p('gd', 'Giám đốc Công an Thành phố', 'Giám đốc CATP', 'tp', 'dai_ta', 'thieu_tuong', 0, need=45,
       frm=('pgd',), olv=5, bonus=25, chain='city', extra=dict(nomark=True, clean=20, viol_max=6)),   # owner spec 14/10: ≤ 6 vi phạm
)
# Seats players may hold at once (owner spec 11/10): a post here is appointed only while fewer players hold it
# (game/cand_roster.py counts them across saves). Thiếu tướng is the Giám đốc's ceiling, so it has one seat too.
SEATS = {'pgd': 5, 'gd': 1}
# After each post: where the next appointment may lead, in order (the first is the default way; the player may aim
# for another one on the rank card).
CAND_NEXT = {
    'to_vien': ('to_pho',), 'to_pho': ('to_truong',), 'to_truong': ('doi_pho',), 'doi_pho': ('doi_truong',),
    'doi_truong': ('pho_truong_ca',), 'pho_truong_ca': ('truong_ca', 'pho_phong'), 'truong_ca': ('pho_phong', 'tro_ly'),
    'pho_phong': ('truong_phong', 'tro_ly'), 'truong_phong': ('pgd', 'tro_ly'), 'tro_ly': ('pgd',), 'pgd': ('gd',), 'gd': (),
}

COURSES = {
    'chuyen_loai': '📚 Khóa chuyển loại sĩ quan',
    'chi_huy_co_so': '📚 Khóa chỉ huy cấp cơ sở',
    'chi_huy_tp': '📚 Khóa chỉ huy cấp thành phố',
}

# The four CAND evaluation grades (★ over the last EVAL_WINDOW worked days, tenths).
EVALS = ((45, 'xs', 'Hoàn thành xuất sắc nhiệm vụ'), (38, 'tot', 'Hoàn thành tốt nhiệm vụ'), (30, 'ht', 'Hoàn thành nhiệm vụ'),
         (0, 'kht', 'Không hoàn thành nhiệm vụ'))

# Procedure violations the system detects (each one is a ⚠️ cảnh cáo). Text: the reason, then "📖 Quy trình đúng".
VIOLATIONS = {
    'skip_check': ('Nhận hồ sơ khi chưa xem đủ giấy tờ', 'Xem đủ từng giấy rồi mới nhận hoặc trả.'),
    'unfair': ('Cho người quen chen hàng', 'Ai cũng như ai: lấy số, chờ đúng lượt.'),
    'no_verify': ('Trả đồ, giao người khi chưa xác minh đủ', 'Hỏi ít nhất hai cách, khớp biên bản rồi mới giao.'),
    'privacy': ('Đăng ảnh, thông tin trẻ lên mạng', 'Đọc loa, gọi số trên thẻ; không đăng ảnh trẻ.'),
    'skip_step': ('Bỏ qua nguy hiểm trước mắt', 'Nguy hiểm thì làm cho an toàn trước, rồi mới tính tiếp.'),
    'wrong_penalty': ('Xử lý sai mức', 'Nhắc trước; tái phạm, nguy hiểm mới lập biên bản.'),
    'threat': ('Dọa phạt khi hòa giải', 'Nghe cả hai bên, đề xuất từng điều; không dọa.'),
    'no_callback': ('Bỏ tin báo khi chưa gọi lại', 'Gọi lại kiểm tra trước khi xếp mức ưu tiên.'),
    'false_log': ('Ghi khống sổ trực ban', 'Chỉ ghi việc thật sự xảy ra.'),
    'wrong_discipline': ('Kỷ luật cấp dưới thiếu căn cứ', 'Chỉ xử lý khi có lỗi rõ, đã nhắc từ trước.'),
    'bribe_owned': ('Nhận phong bì rồi tự giác nộp lại', 'Không nhận bất kỳ thứ gì của dân, từ đầu.'),
    'bribe': ('Nhận phong bì', 'Không nhận bất kỳ thứ gì của dân. Lập biên bản hành vi đưa hối lộ.'),
    # Owner spec 14/10 (kỷ luật: game/gov_rules.py; never a ⚠️ warning, the codes name the reason in the log)
    'bail_kin': ('Chuộc người thân đang chấp hành án', 'Cán bộ tuyệt đối không bảo lãnh bạn bè, vợ/chồng, người đính hôn đang chấp hành án.'),
    'gamble': ('Tham gia cá độ, đỏ đen ở chợ đen', 'Cán bộ tuyệt đối không đặt cược bằng xu ở chợ đen.'),
    # 🛃 Hải quan (owner spec 14/10, I. Bổ sung cập nhật nghề Hải quan; game/careers/customs.py, game/hq_ops.py)
    'hq_skip': ('Quyết định khi chưa kiểm đủ theo luồng', 'Luồng vàng: kiểm hồ sơ giấy. Luồng đỏ: kiểm hồ sơ và thực tế hàng, rồi mới quyết định.'),
    'hq_release': ('Cho qua hàng cấm, hàng lậu', 'Hàng cấm, động vật hoang dã, hàng không khai báo: tạm giữ, lập biên bản, bàn giao đúng thẩm quyền.'),
    'hq_dismiss': ('Gỡ phản ánh chính đáng', 'Phản ánh đúng thì ghi nhận, sửa sai và trả lời người phản ánh.'),
    'hq_npc_sue': ('Đưa người phản ánh chính đáng đi truy tố', 'Chỉ chuyển Công an khi có dấu hiệu vi phạm (vu khống, đòi tiền).'),
    'hq_collude': ('Thông đồng, bao che doanh nghiệp gian lận', 'Không bao che bất kỳ ai: khai sai thì xử lý đúng như mọi tờ khai.'),
    'hq_falsify': ('Cố ý làm sai lệch hồ sơ, kết quả kiểm tra', 'Biên bản ghi đúng điều đã thấy; không sửa kết quả theo lời nhờ.'),
    'hq_abuse': ('Lợi dụng chức vụ: hối lộ, chiếm đoạt thuế, tuồn hàng', 'Không nhận gì của ai; tiền thuế, hàng tạm giữ có biên lai, chứng từ.'),
    'hq_wrongcase': ('Đề xuất xử lý sai, chèn ép doanh nghiệp', 'Chỉ đề xuất khi có căn cứ trong hồ sơ kiểm tra, đúng mức.'),
}
SEVERE = ('bribe',)   # an immediate one-grade demotion and a permanent integrity mark (owner 06/10)

# The appointment interview and the course exams: _q rows in the format of game/promotion_content.QUESTIONS.
def _q(qid, text, *opts):
    return dict(id=qid, text=text, options=[dict(id=chr(97 + i), label=lab, score=sc) for i, (lab, sc) in enumerate(opts)])


QUESTIONS = {
    'cand': [
        _q('cd1', 'Tổ viên nhắn riêng: “Anh em mình cả, phần tổ em nương tay nhé.”', ('Kiểm tra đúng quy trình như mọi tổ', 2),
           ('Nương tay một lần', 0), ('Hỏi ý cấp trên rồi tính', 1)),
        _q('cd2', 'Chỉ tiêu tháng thiếu biên bản, cấp trên giục “làm cho đủ”.', ('Báo cáo số thật, kèm lý do và đề xuất', 2),
           ('Lập thêm biên bản cho đủ số', 0), ('Im lặng, chờ tháng sau', 1)),
        _q('cd3', 'Người dân đăng bài chê phường, cán bộ đề nghị mời lên làm việc.', ('Không mời: góp ý không phải vi phạm. Xem phần đúng để sửa', 2),
           ('Mời lên cho “biết điều”', 0), ('Nhắn họ gỡ bài', 0)),
        _q('cd4', 'Tổ tuần tra đêm thứ ba liền xin đổi ca.', ('Xếp người khác, cho nghỉ bù', 2), ('Bảo cố thêm một đêm', 0),
           ('Cho nghỉ nhưng trừ thi đua', 1)),
        _q('cd5', 'Camera ghi hình của tổ tắt giữa lúc xử lý vụ việc.', ('Lập biên bản sự việc, kiểm tra lại toàn bộ', 2),
           ('Bỏ qua, chắc hết pin', 1), ('Dặn mọi người đừng nói ra', 0)),
        _q('cd6', 'Người quen của một lãnh đạo xin làm hồ sơ trước.', ('Mời lấy số như mọi người', 2), ('Làm trước cho êm', 0),
           ('Gọi hỏi lãnh đạo', 1)),
        _q('cd7', 'Phát hiện cán bộ dưới quyền nhận phong bì.', ('Lập biên bản, báo cáo, tạm đình chỉ theo quy định', 2),
           ('Nhắc khéo cho qua', 0), ('Chờ có đơn rồi xử', 1)),
        _q('cd8', 'Trưởng phòng nhờ “xem lại” điểm đánh giá của một người quen.', ('Giữ kết quả theo hồ sơ, nói rõ căn cứ', 2),
           ('Nâng điểm một chút', 0), ('Hỏi thêm ý kiến tổ', 1)),
    ],
}
QUESTIONS['hq'] = [
    _q('hq1', 'Một doanh nghiệp quen nhắn: “Lô này anh em mình, cho qua luồng vàng nhé.”', ('Kiểm đúng theo luồng hệ thống phân, như mọi tờ khai', 2),
       ('Cho qua một lần', 0), ('Hỏi ý lãnh đạo rồi tính', 1)),
    _q('hq2', 'Kiểm thực tế thấy thừa 20 thùng so với tờ khai. Bạn làm gì?', ('Lập biên bản, yêu cầu giải trình, xử lý theo quy định', 2),
       ('Sửa tờ khai cho khớp giúp doanh nghiệp', 0), ('Bỏ qua vì chênh ít', 0)),
    _q('hq3', 'Chỉ tiêu thu ngân sách tháng còn thiếu, cấp trên giục “ấn thuế cho đủ”.', ('Báo cáo số thật, thu đúng, kiến nghị giải pháp', 2),
       ('Áp mức thuế cao hơn cho đủ số', 0), ('Im lặng chờ tháng sau', 1)),
    _q('hq4', 'Hành khách đưa phong bì “cảm ơn” sau khi làm thủ tục nhanh.', ('Từ chối, giải thích, ghi sổ', 2), ('Nhận vì đã làm xong', 0),
       ('Nhận rồi nộp quỹ chung', 0)),
    _q('hq5', 'Hàng tạm giữ là mỹ phẩm đắt tiền, đồng nghiệp rủ “chia nhau dùng thử”.', ('Từ chối, niêm phong, vào sổ đủ biên lai', 2),
       ('Lấy một ít không ai biết', 0), ('Báo lãnh đạo nhưng vẫn để ngoài kho', 1)),
    _q('hq6', 'Một người dân phản ánh bạn tính thuế sai, và họ nói đúng.', ('Ghi nhận, tính lại, trả lời và sửa quy trình', 2),
       ('Gỡ phản ánh cho sạch hồ sơ', 0), ('Chuyển Công an vì “nói xấu cơ quan”', 0)),
    _q('hq7', 'Cấp dưới đề xuất tịch thu hàng của một cửa hàng mà hồ sơ không có căn cứ.', ('Không duyệt, yêu cầu bổ sung căn cứ, nhắc quy trình', 2),
       ('Duyệt cho nhanh', 0), ('Để đó không trả lời', 1)),
    _q('hq8', 'Bạn được mời đi ăn tối bởi doanh nghiệp đang chờ hoàn thuế.', ('Từ chối lịch sự, giữ khoảng cách khi hồ sơ đang xử lý', 2),
       ('Đi cho biết mặt', 0), ('Đi nhưng tự trả tiền', 1)),
]
QUESTION_INDEX = {q['id']: q for rows in QUESTIONS.values() for q in rows}

# NPCs named in messages: who fills a seat a demotion leaves, who signs, who approves.
SEAT_NPC = ('Thiếu tá Đỗ Văn Khang', 'Đại úy Lê Thu Hà', 'Thượng úy Phan Minh', 'Trung úy Vũ Hạnh', 'Thiếu úy Đặng Quý', 'Trung tá Ngô Tường')
BOSS = 'Thiếu tướng Hoàng Trí, Giám đốc Công an Thành phố'   # signs while no player holds the Giám đốc's seat

ORGS = {
    'cand': dict(
        name='Công an nhân dân', unit='Công an phường Mây', grade_word='Cấp bậc hàm', post_word='Chức vụ',
        grades=CAND_GRADES, posts=CAND_POSTS, next=CAND_NEXT, courses=COURSES,
        pay_ref=3.2, eval_window=10, evals=EVALS,
        # Warnings (bút tích đỏ, owner 11/10): the 2nd is a "Không hoàn thành nhiệm vụ" period, the 3rd one grade down
        # and the grade held 20 worked days, the 4th (before 10 clean days) jail, expulsion and a ban from the force.
        warn_max=3, demote_on=3, decay_days=10, susp_days=3, red_kht=2, red_hold=20, red_expel=4, expel_jail=3,
        severe=SEVERE, bar_on_mark=('tro_ly', 'pgd', 'gd', 'dai_ta', 'thieu_tuong'),
        start=('to_vien', 'binh_nhi'),
        # The step the record keeps for builds without org (game/promotion.py rank 0..4; nobody's step goes down there).
        step={'to_vien': 0, 'to_pho': 2, 'to_truong': 3, 'doi_pho': 3, 'doi_truong': 3, 'pho_truong_ca': 4, 'truong_ca': 4,
              'pho_phong': 4, 'truong_phong': 4, 'tro_ly': 4, 'pgd': 4, 'gd': 4},
        # Existing players (never lowered): their step → post and grade.
        migrate=(('to_vien', 'ha_si'), ('to_vien', 'thuong_si'), ('to_pho', 'trung_uy'), ('to_truong', 'thuong_uy'),
                 ('pho_truong_ca', 'thieu_ta')),
        questions='cand', office='cand', badge='cand',
    ),
}
# 🛃 Hải quan (owner spec 14/10): ngạch & bậc (grades) and chức vụ (posts) from the Chi cục Hải quan cửa khẩu Bến Mây up
# to the Cục Hải quan Thành phố and the Tổng cục. Boards: deep green with gold bars and stars (v4/insignia.js GRADES.hq).
# Everything (the units, the people) is invented.
HQ, HQ_SENIOR, HQ_CADET = 'hq', 'hq_senior', 'hq_cadet'
HQ_GRADES = (
    _g('tap_su', 'Người tập sự', dict(base=HQ_CADET), 3, 30, coef=3.2),
    _g('ktv_1', 'Kiểm tra viên bậc 1', dict(base=HQ, b=1, s=1), 5, 34, coef=3.6),
    _g('ktv_2', 'Kiểm tra viên bậc 2', dict(base=HQ, b=1, s=2), 6, 36, coef=4.0),
    _g('ktv_3', 'Kiểm tra viên bậc 3', dict(base=HQ, b=1, s=3), 8, 38, 'course:hq_chinh', coef=4.4),
    _g('ktvc_1', 'Kiểm tra viên chính bậc 1', dict(base=HQ, b=2, s=1), 8, 40, coef=5.0),
    _g('ktvc_2', 'Kiểm tra viên chính bậc 2', dict(base=HQ, b=2, s=2), 10, 42, coef=5.6),
    _g('ktvc_3', 'Kiểm tra viên chính bậc 3', dict(base=HQ, b=2, s=3), 10, 43, 'course:hq_cao_cap', coef=6.2),
    _g('ktvcc_1', 'Kiểm tra viên cao cấp bậc 1', dict(base=HQ_SENIOR, b=2, s=1), 12, 45, coef=7.0),
    _g('ktvcc_2', 'Kiểm tra viên cao cấp bậc 2', dict(base=HQ_SENIOR, b=2, s=2), 12, 45, 'clean:30', coef=7.8),
    _g('ktvcc_3', 'Kiểm tra viên cao cấp bậc 3', dict(base=HQ_SENIOR, b=2, s=3), None, None, coef=8.6),   # the Tổng cục trưởng's ceiling
)
HQ_POSTS = (
    _p('hq_ts', 'Người tập sự công chức Hải quan', 'Tập sự', 'chi_cuc', 'tap_su', 'tap_su', 3),
    _p('hq_ktv', 'Kiểm tra viên Hải quan · Đội Thủ tục hàng hóa', 'Kiểm tra viên', 'chi_cuc', 'ktv_1', 'ktv_3', 8, frm=('hq_ts',), bonus=3),
    _p('hq_ktvc', 'Kiểm tra viên chính Hải quan · Đội Kiểm soát', 'Kiểm tra viên chính', 'chi_cuc', 'ktvc_1', 'ktvc_2', 8, frm=('hq_ktv',), bonus=6),
    _p('hq_doi', 'Đội trưởng Đội Kiểm soát Hải quan', 'Đội trưởng', 'chi_cuc', 'ktvc_2', 'ktvc_3', 10, need=40, frm=('hq_ktvc',), bonus=8),
    _p('hq_ccc', 'Chi cục trưởng Chi cục Hải quan cửa khẩu Bến Mây', 'Chi cục trưởng', 'chi_cuc', 'ktvc_3', 'ktvcc_1', 10, need=42,
       frm=('hq_doi',), bonus=12),
    _p('hq_cuc', 'Cục trưởng Cục Hải quan Thành phố', 'Cục trưởng', 'cuc', 'ktvcc_1', 'ktvcc_2', 15, need=45, frm=('hq_ccc',), bonus=20,
       chain='city', extra=dict(nomark=True)),
    _p('hq_tong', 'Tổng cục trưởng Tổng cục Hải quan', 'Tổng cục trưởng', 'tong_cuc', 'ktvcc_2', 'ktvcc_3', 0, need=45, frm=('hq_cuc',),
       bonus=25, chain='city', extra=dict(nomark=True, clean=20)),
)
HQ_NEXT = {'hq_ts': ('hq_ktv',), 'hq_ktv': ('hq_ktvc',), 'hq_ktvc': ('hq_doi',), 'hq_doi': ('hq_ccc',), 'hq_ccc': ('hq_cuc',),
           'hq_cuc': ('hq_tong',), 'hq_tong': ()}
HQ_COURSES = {'hq_chinh': '📚 Bồi dưỡng ngạch Kiểm tra viên chính', 'hq_cao_cap': '📚 Bồi dưỡng ngạch Kiểm tra viên cao cấp'}
SEATS.update({'hq_ccc': 5, 'hq_cuc': 1, 'hq_tong': 1})   # 🛃 counted from hq_roster (game/cand_roster.py)
ORGS['hq'] = dict(
    name='Hải quan', unit='Chi cục Hải quan cửa khẩu Bến Mây', grade_word='Ngạch, bậc', post_word='Chức vụ',
    grades=HQ_GRADES, posts=HQ_POSTS, next=HQ_NEXT, courses=HQ_COURSES,
    pay_ref=3.2, eval_window=10, evals=EVALS,
    warn_max=3, demote_on=3, decay_days=10, susp_days=3, red_kht=2, red_hold=20, red_expel=4, expel_jail=0,
    severe=SEVERE, bar_on_mark=('hq_cuc', 'hq_tong', 'ktvcc_2', 'ktvcc_3'),
    start=('hq_ts', 'tap_su'),
    step={'hq_ts': 0, 'hq_ktv': 1, 'hq_ktvc': 2, 'hq_doi': 3, 'hq_ccc': 4, 'hq_cuc': 4, 'hq_tong': 4},
    migrate=(('hq_ts', 'tap_su'), ('hq_ktv', 'ktv_1'), ('hq_ktvc', 'ktvc_1'), ('hq_doi', 'ktvc_2'), ('hq_ccc', 'ktvc_3')),
    questions='hq', office=None, badge='hq',
    # Who takes a seat a demotion leaves, who signs while no player holds the top seat, the expulsion's line.
    seat_npc=('Kiểm tra viên chính Lương Hữu Đạt', 'Kiểm tra viên Tạ Minh Châu', 'Kiểm tra viên Kiều Phương', 'Kiểm tra viên chính Âu Gia Bảo'),
    boss='Tổng cục trưởng Nghiêm Quốc Trung (Tổng cục Hải quan)',
    expel_line='🚨 Quyết định khai trừ khỏi ngành Hải quan. Không được xét tuyển vào bất kỳ ngành nghề chính quyền nào.',
)
# Career → (org, the postings that wear it). A part-time posting (Hỗ trợ tiếp dân) keeps the plain ladder.
CAREER_ORG = {'police': ('cand', ('cap-kv',)), 'customs': ('hq', ('hq-ktv',))}

# Content stubs (owner 06/10: "nhiều cái khác nữa, cũng thế"): the other careers' ladders, design §2.5–2.6. Not wired:
# a stub becomes live by moving it into ORGS with grades/posts in the format above and adding it to CAREER_ORG.
STUBS = {
    'airline': dict(name='Hãng bay Cánh Cò', grades=('Học viên phi công', 'Cơ phó', 'Cơ phó cao cấp', 'Cơ trưởng',
                                                    'Cơ trưởng Huấn luyện', 'Giáo viên kiểm tra'),
                    posts=('Người chỉ huy tàu bay', 'Trưởng nhóm bay', 'Trưởng đội bay ATR', 'Phó GĐ Khối khai thác bay',
                           'GĐ Khối khai thác bay', 'Phó Tổng Giám đốc khai thác'), careers=('pilot',)),
    'cabin': dict(name='Đoàn tiếp viên', grades=('Tiếp viên hạng phổ thông', 'Tiếp viên phó', 'Tiếp viên trưởng'),
                  posts=('Tiếp viên', 'Trưởng ban tiếp viên', 'Phó GĐ Đoàn tiếp viên', 'GĐ Đoàn tiếp viên'), careers=('flight_attendant',)),
    'hospital': dict(name='Bệnh viện', grades=('Điều dưỡng hạng IV', 'Điều dưỡng hạng III', 'Điều dưỡng hạng II', 'Điều dưỡng hạng I'),
                     posts=('Điều dưỡng viên', 'Điều dưỡng trưởng tua', 'Điều dưỡng trưởng khoa', 'Phó phòng Điều dưỡng',
                            'Trưởng phòng Điều dưỡng', 'Phó Giám đốc bệnh viện'), careers=('nurse',)),
    'school': dict(name='Trường học', grades=('Giáo viên hạng III', 'Giáo viên hạng II', 'Giáo viên hạng I'),
                   posts=('Giáo viên', 'Tổ phó', 'Tổ trưởng chuyên môn', 'Phó Hiệu trưởng', 'Hiệu trưởng', 'Trưởng phòng GD&ĐT'),
                   careers=('teacher',)),
    'railway': dict(name='Công ty đường sắt khu vực', grades=tuple(f'Bậc thợ {i}/7' for i in range(1, 8)),
                    posts=('Gác chắn viên', 'Trưởng gác', 'Cung trưởng cung đường', 'Đội trưởng duy tu', 'Phó Giám đốc công ty'),
                    careers=('railway',)),
    'offshore': dict(name='Giàn khoan', grades=('Bậc thợ 1', 'Bậc thợ 2', 'Bậc thợ 3', 'Bậc thợ 4'),
                     posts=('Thợ phụ boong', 'Thợ khoan sàn', 'Thợ tháp', 'Thợ khoan chính', 'Đốc công khoan', 'Giàn trưởng'),
                     careers=('oil',)),
    'finance': dict(name='Kế toán – Ngân hàng', grades=('Kế toán viên trung cấp', 'Kế toán viên', 'Kế toán viên chính', 'Kế toán viên cao cấp'),
                    posts=('Kế toán viên', 'Kế toán tổng hợp', 'Kế toán trưởng', 'Giám đốc tài chính'),
                    careers=('corp_accounting', 'tax_payroll', 'group_accounting')),
    'dispatch': dict(name='Trung tâm điều phối cứu hộ', grades=('Điều phối viên bậc 1', 'Bậc 2', 'Bậc 3', 'Bậc 4'),
                     posts=('Điều phối viên', 'Trưởng ca', 'Phó Giám đốc Trung tâm', 'Giám đốc Trung tâm'), careers=('rescue',)),
    'lighthouse': dict(name='Bảo đảm an toàn hàng hải', grades=tuple(f'Bậc thợ {i}' for i in range(1, 6)),
                       posts=('Nhân viên trạm đèn', 'Trạm phó', 'Trạm trưởng đèn biển', 'Đội trưởng khu vực', 'Phó Giám đốc xí nghiệp'),
                       careers=('lighthouse',)),
    'library': dict(name='Thư viện – Lưu trữ', grades=('Thư viện viên hạng IV', 'Hạng III', 'Hạng II', 'Hạng I'),
                    posts=('Thư viện viên', 'Tổ trưởng', 'Trưởng phòng nghiệp vụ', 'Phó Giám đốc thư viện', 'Giám đốc thư viện'),
                    careers=('library',)),
    'pool': dict(name='Trung tâm thể thao', grades=('Chứng chỉ cứu hộ', 'Huấn luyện viên cứu hộ'),
                 posts=('Nhân viên cứu hộ', 'Trưởng ca cứu hộ', 'Quản lý hồ bơi', 'Giám đốc trung tâm'), careers=('lifeguard',)),
}
