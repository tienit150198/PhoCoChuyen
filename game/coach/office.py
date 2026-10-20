"""🧭 Coach steps of the offices (see game/coach/__init__.py): no stock here; the loop is take the file or the case,
open and check its papers, mark / match / decide, then submit or close it, in each desk's own words."""
from . import S, V, stock  # noqa: F401

# ------------------------------------------------------------------ shared bits of the Cánh Diều / office-kit desks
DOC_TAB = V('Mở tab Hồ sơ trước.', s=['[data-action="car:tab"][data-tab="doc"]'])


def _rules(g: int, t: str) -> dict:
    return S('📑', t, s=['[data-action="car:tab"][data-tab="rules"]'], g=g)


def _overtime(p: str, g: int) -> dict:
    """The overtime button of the status row (from 16:30), only when it is there."""
    # The Cánh Diều desks build the command from their prefix (c.p+'overtime'): matched by its ending there.
    sel = f'[data-op="{p}overtime"]' if p in ('ca_', 'tp_', 'ga_') else '.career-job.ow [data-op$="_overtime"]'
    return S('🌙', 'Còn việc dở sau 16:30: bấm Đăng ký tăng ca.', ['Đăng ký tăng ca', 'Ở lại tăng ca'], [sel], g=g, o=True)


# The confirm button of each step kind (office_kit.procSteps: CONFIRM of corp_accounting.js / group_accounting.js).
CONFIRM = ('multi', 'num', 'order', 'match', 'fields', 'entry')


def _proc(pre: str, g_step: int, g_hint: int, g_file: int) -> list[dict]:
    """A step-by-step dossier (corp & group accounting, office_kit.procSteps): open its papers, do the step and
    confirm it at the bottom bar, then the handover note and the hand-in."""
    return [
        S('📂', 'Mở chứng từ mà bước này cần.', s=['[data-action="car:open"]'], g=g_step, o=True),
        S('🧮', 'Làm bước đang mở rồi bấm nút xác nhận ở dưới.',
          s=[f'.{pre}-options', f'.{pre}-order', *(f'.ok-bar [data-action="car:{a}"]' for a in ('coach', *CONFIRM))], g=g_step,
          w='Nút ở thanh dưới, khi bạn mở hồ sơ tiếp theo.'),
        S('💡', 'Bí quá thì bấm Xin gợi ý: mất 5 phút mỗi lần.', g=g_hint, x=True),
        S('📝', 'Bước cuối: chọn ghi chú có số liệu, bấm Nộp hồ sơ.', s=['[data-action="car:submit"]'],
          g=g_file, w='Làm hết các bước, nút Nộp hồ sơ hiện ở thanh dưới.'),
    ]


def _office_work(p: str) -> list[dict]:
    """hr_admin, secretary, it_helpdesk (office_work.js): one dossier of one kind (sort, mark, slots, fields, seq,
    case): only the steps of that kind show up."""
    return [
        S('📥', 'Bấm Nhận hồ sơ để đọc yêu cầu.', s=['[data-command="ask"]'], g=0),
        S('🗃️', 'Đọc giấy tờ kèm theo, chạm để mở từng tờ.', s=['.ow-papers'], g=1, o=True),
        S('🗂️', 'Đọc thẻ, chạm khay đúng cho nó.', s=['.ow-bins'], o=True),
        S('🔍', 'Chạm chỗ sai trên giấy để sửa.', s=['.ow-doc'], o=True),
        S('✏️', 'Chọn cách sửa đúng cho chỗ này.', s=['.ow-picker .ow-choices'], o=True),
        S('🗓️', 'Chạm một ô trống hợp lệ để xếp việc đang chọn.', s=['.ow-grid'], o=True),
        S('📝', 'Đọc lời người nói, gõ đủ từng ô.', s=['.ow-form'], o=True),
        S('🧭', 'Chạm các bước theo thứ tự sẽ làm.', s=['.ow-pool'], o=True),
        S('🔎', 'Bấm tìm hiểu từng chuyện trước khi trả lời.', s=['.ow-facts'], o=True),
        S('💬', 'Chọn cách trả lời hợp với chuyện đã biết.', s=['.ow-answers'], o=True),
        S('📞', 'Có tin “Vừa đổi”: sửa theo tin mới rồi nộp.', s=['.ow-twist'], g=2, o=True),
        S('📤', 'Làm xong hết thì bấm Nộp hồ sơ.', s=['.career-job.ow [data-op$="_file"]', '[data-action="car:hand"]'], g=4,
          w='Làm hết hồ sơ, nút Nộp hiện ở thanh dưới.'),
        _overtime(p, 5),
    ]


STEPS: dict[str, list[dict]] = {
    # 📒 Built-in bookkeeping desk: the first two files of a day are the reconciliation board (app.js), the next ones
    # the paper desk (desk.js).
    'accounting': [
        S('👁️', 'Bấm Mở gốc từng phiếu để xem số gốc.', s=['[data-command="ac_inspect"]'], g=6),
        S('✏️', 'Phiếu lệch gốc: bấm Sửa theo gốc.', s=['[data-command="ac_correct"]'], g=6, o=True),
        S('🗂️', 'Hai phiếu cùng nguồn: bấm Đánh dấu trùng.', s=['[data-command="ac_duplicate"]:not([disabled])'],
          g=6, o=True),
        S('📨', 'Phiếu thiếu nguồn: bấm Xin nguồn bổ sung.', s=['[data-command="ac_request_source"]'],
          g=6, o=True),
        S('👆', 'Chọn phiếu mang mã HD cần ghép.', s=['[data-action="selectDoc"].gd-pulse', '.dw-col.docs .dw-cards'], g=7,
          v=V('Mở tab Chứng từ.', s=['[data-action="jobTab"][data-tab="acDocs"]'])),
        S('🔗', 'Chọn giao dịch cùng mã HD đó.', s=['[data-action="selectTx"].gd-pulse', '.dw-col.tx .dw-cards'], g=7,
          v=V('Mở tab Giao dịch.', s=['[data-action="jobTab"][data-tab="acTx"]'])),
        S('🔗', 'Hai tổng bằng nhau thì bấm Ghép nhóm.', s=['[data-action="match"]'], g=7),
        S('✅', 'Ghép hết thì bấm Kiểm & bàn giao hồ sơ.', s=['[data-action="completeAC"].primary'],
          g=7, w='Ghép hết thẻ, nút Bàn giao hiện ở thanh dưới.'),
        S('📥', 'Khách mới: bấm Nhận giấy tờ để trải sổ lên bàn.', s=['.dk-start [data-command="ask"]'], g=0),
        S('📖', 'Mở Sổ quy định hôm nay, xem luật MỚI.', s=['.dk-book > summary'], g=1),
        S('👆', 'Chạm dòng sai trên giấy tờ.', s=['.dk-docs'], g=2),
        S('📌', 'Chọn quy định mà dòng đó trái.', s=['.dk-chips'], g=2, o=True),
        S('🧮', 'Có két: chạm từng tờ để đếm.', s=['[data-action="desk:note"]'], g=3, o=True),
        S('💰', 'Đếm xong thì bấm Chốt số đếm.', s=['[data-command="desk_count"]'], g=4, o=True),
        S('🖋️', 'Chọn một con dấu để Đóng dấu hồ sơ.', s=['.dk-stamps .dk-stamp-grid'], g=5,
          w='Con dấu nằm cuối hồ sơ, sau giấy tờ.'),
    ],
    # 🗂️ Minh Bạch accounting office: the morning tray of vouchers, then step-by-step dossiers.
    'corp_accounting': [
        _rules(1, 'Mở tab Quy định: hạn mức duyệt, nhà cung cấp bị chặn.'),
        S('📥', 'Bấm Nhận khay chứng từ để bắt đầu.', s=['[data-command="ask"]'], g=0),
        S('⭕', 'Chạm ô sai trên giấy để khoanh lại.', s=['[data-action="car:circle"].gd-pulse'], g=2, o=True, v=DOC_TAB),
        S('🖋️', 'Bấm DUYỆT, TRẢ LẠI hoặc TRÌNH SẾP cho bộ này.', ['DUYỆT', 'TRẢ LẠI', 'TRÌNH SẾP'], ['.ca-stampbar'], g=2),
        S('➡️', 'Bấm Bộ tiếp theo, soát cho hết khay.', s=['.ok-bar [data-action="car:pick"]'], g=3),
        S('📤', 'Đủ bộ thì bấm Chốt khay để báo chị Hạnh.', s=['[data-op="ca_submit"]'], g=3,
          w='Đóng dấu hết các bộ, nút Chốt khay hiện ở thanh dưới.'),
        *_proc('ca', 4, 5, 6),
        _overtime('ca_', 7),
    ],
    # 🧮 Tax & payroll: the draft payroll person by person, then forms done step by step.
    'tax_payroll': [
        _rules(1, 'Mở tab Quy định: hệ số tăng ca, mức sàn bảo hiểm.'),
        S('📥', 'Bấm Nhận bảng lương nháp để bắt đầu.', s=['[data-command="ask"]'], g=0),
        S('👆', 'So với giấy tờ gốc, chạm ô sai để đánh dấu.', s=['[data-action="car:flag"].gd-pulse', '.tp-person .tp-cells-grid'], g=2,
          v=DOC_TAB),
        S('✅', 'Soát xong người này thì bấm Xong dòng.', s=['[data-command="tp_row"]'], g=4),
        S('➡️', 'Bấm Người tiếp theo, soát đủ cả bảng.', s=['.ok-bar [data-action="car:gpick"]'], g=4, o=True),
        S('💸', 'Đủ người thì bấm Chuyển lương.', s=['[data-op="tp_pay"]'], g=4,
          w='Soát xong hết người, nút Chuyển lương hiện ở thanh dưới.'),
        S('🧮', 'Hồ sơ: làm bước đang mở rồi bấm Kiểm tra.', s=['[data-action="car:check"]', '.ok-bar [data-action="car:coach"]'], g=5,
          w='Nút ở thanh dưới, khi bạn mở hồ sơ tiếp theo.'),
        S('💡', 'Bí thì bấm Gợi ý; trả lời sai mất thêm 15 phút.', g=6, x=True),
        S('📤', 'Xong mọi bước thì bấm Nộp / bàn giao hồ sơ.', s=['[data-op="tp_file"]'], g=7,
          w='Làm hết các bước, nút nộp hiện ở thanh dưới.'),
        S('📨', 'Tới hạn tờ khai: bấm Nộp ở thẻ lịch nộp.', s=['[data-op="tp_declare"]'], g=8, o=True,
          v=V('Mở thẻ Lịch nộp trong Hộp thư.', s=
              ['[data-action="car:fold"][data-fold="plan"]', '[data-action="car:tab"][data-tab="inbox"]'])),
        _overtime('tp_', 8),
    ],
    # 🏢 Group consolidation: two ledgers matched line by line, then step-by-step dossiers.
    'group_accounting': [
        S('📥', 'Bấm Nhận hai sổ đối chiếu để bắt đầu.', s=['[data-command="ask"]'], g=0),
        S('👆', 'Chạm một dòng bên bán (cột 📤).', s=['[data-action="car:msel"].gd-pulse', '.ga-cols'], g=1),
        S('👆', 'Chạm dòng cùng chứng từ bên mua (cột 📥).', s=['[data-action="car:msel"].gd-pulse', '.ga-cols'],
          g=1),
        S('🔗', 'Cùng số tiền: bấm Ghép cặp này.', s=['.ga-dopair'], g=1, o=True),
        S('💱', 'Số lệch nhau: chọn Lệch tỷ giá hay Gõ nhầm số.', s=['.ga-cause-fx', '.ga-cause-typo'],
          g=2, o=True),
        S('🏷️', 'Dòng chỉ có một bên: chọn nó, rồi chọn lý do ở dưới.', g=3, x=True),
        S('📑', 'Có nhãn mới: Ghi trùng, Không phải nội bộ.', s=['.ga-tag-dup', '.ga-tag-outside'],
          g=4, o=True),
        S('✂️', 'Hai sổ khớp thì bấm Loại trừ để ghi bút toán.', s=['[data-op="ga_submit"]'], g=5,
          w='Ghép hết các dòng, nút Loại trừ hiện ở thanh dưới.'),
        *_proc('ga', 6, 7, 8),
        _overtime('ga_', 9),
    ],
    # 🗂️ Cánh Diều desks (office_work.js).
    'hr_admin': _office_work('hc_'),
    'secretary': _office_work('tk_'),
    'it_helpdesk': _office_work('it_'),
    # 🎧 Built-in support desk: the first two cases of a day are the six-step support case (app.js), the next ones the
    # message desk (desk.js).
    'customer_care': [
        S('🔐', 'Bấm Xác minh mã đơn trước khi xem hồ sơ.', s=['[data-command="cs_identity"]'], g=6),
        S('📂', 'Mở từng chứng cứ, tìm dòng 📌 Căn cứ.', s=['[data-command="cs_evidence"]'], g=6),
        S('🧩', 'Chọn phương án khớp dòng 📌 Căn cứ.', s=['.dw-choice.gd-pulse', '.dw-now .dw-choices'], g=6),
        S('➡️', 'Bấm Gửi việc cho đầu mối.', s=['[data-action="executeCS"]'], g=7),
        S('⏳', 'Đầu mối đang làm: bấm Chờ thêm 20 phút.', s=['.dw-cs [data-command="advance"]'], o=True),
        S('🔍', 'Kết quả về: bấm Kiểm kết quả với khách.', s=['[data-command="cs_confirm"]'], g=7,
          w='Chờ đầu mối làm xong, có khi tới sáng mai. Làm việc khác trước.'),
        S('✅', 'Bấm Hoàn tất & đóng vụ để nhận tiền.', s=['[data-action="closeCS"]'], g=7),
        S('💬', 'Tin nhắn mới: chọn câu trả lời ân cần, đúng việc.', s=['.dk-replies'], g=0,
          w='Tới tin nhắn tiếp theo, câu trả lời hiện ở đầu.'),
        S('📥', 'Bấm Mở hồ sơ đơn để xem đơn và lịch sử.', s=['.dk-start [data-command="ask"]'], g=1),
        S('📖', 'Mở Sổ quy định hôm nay: hạn đổi trả, luật MỚI.', s=['.dk-book > summary'], g=2),
        S('👆', 'Chạm dòng có vấn đề trên đơn.', s=['.dk-docs'], g=3),
        S('📌', 'Chọn quy định mà dòng đó trái.', s=['.dk-chips'], g=3, o=True),
        S('🔍', 'Bấm bước kiểm, như Gọi số đã đăng ký.', s=['[data-command="desk_check"]'], g=4, o=True),
        S('⏳', 'Phải chờ kết quả thì bấm Chờ một nhịp.', s=['.dk-checks [data-command="advance"]'], g=4, o=True),
        S('🖋️', 'Chọn một con dấu để Đóng dấu hồ sơ.', s=['.dk-stamps .dk-stamp-grid'], g=5,
          w='Con dấu nằm cuối hồ sơ, sau giấy tờ.'),
    ],
    # ⚖️ Văn phòng Bình An: one dossier, step by step (the order the server lays them out).
    'lawyer': [
        S('🗣️', 'Bấm Hỏi khách và mở hồ sơ.', s=['.sk-ask'], g=0),
        S('📚', 'Đọc thỏa thuận, biên bản, lời kể và quy tắc bên dưới.', g=0, x=True),
        S('🔗', 'Chạm hai tài liệu làm căn cứ chính.', s=[".lw-controls:has([data-key$=':evidence'])"], g=1, o=True),
        S('📎', 'Chọn đủ hai thì bấm Gắn cặp chứng cứ.', s=[".lw-controls:has([data-key$=':evidence']) [data-action=\"car:submit\"]"], g=1, o=True),
        S('📅', 'Chạm ba sự kiện theo ngày, sớm trước.', s=[".lw-controls:has([data-key$=':timeline'])"], g=1, o=True),
        S('🗓️', 'Xếp xong thì bấm Chốt dòng thời gian.', s=[".lw-controls:has([data-key$=':timeline']) [data-action=\"car:submit\"]"], g=1, o=True),
        S('❓', 'Chọn điểm mâu thuẫn cần làm rõ.', s=[".lw-controls:has([data-payload*='\"step\":\"discrepancy\"'])"], g=3, o=True),
        S('🧮', 'Cộng chứng từ gốc, trừ tiền đã nhận, gõ số.', s=['[data-action="car:lawAmount"]'], g=2,
          o=True),
        S('📝', 'Chọn phương án bám đúng thỏa thuận.', s=[".lw-controls:has([data-payload*='\"step\":\"filing\"'])"], g=3,
          w='Làm các bước trước, bước soạn phương án sẽ mở.'),
        S('🗣️', 'Buổi đối chiếu: chọn cách có căn cứ.', s=[".lw-controls:has([data-payload*='\"step\":\"hearing\"'])"], g=3,
          o=True),
    ],
    # 🛃 Cửa khẩu Bến Mây: the lane the system gave decides the checks; the decision is final.
    'customs': [
        S('🛃', 'Đọc giới thiệu rồi bấm Vào ca thôi!', s=['[data-command="hq_intro"]'], o=True),
        S('📄', 'Bấm Đọc hồ sơ để mở tờ khai.', s=['.sk-ask'], g=0),
        S('🚦', 'Đọc tờ khai và luồng, chọn đúng việc cần làm.',
          s=[f".hq-step .sk-opts:has([data-payload*='\"step\":\"{k}\"'])" for k in ('route', 'scan', 'rate', 'profile')], g=0),
        S('🔎', 'Kiểm đúng việc luồng yêu cầu, chọn theo điều thấy.',
          s=[f".hq-step .sk-opts:has([data-payload*='\"step\":\"{k}\"'])" for k in ('docs', 'goods', 'identify', 'method')], g=1,
          o=True),
        S('🧮', 'Tính thuế, gõ số xu rồi bấm Ghi vào tờ khai.', s=['.hq-step [data-command="hq_step"].primary'], g=1, o=True),
        S('🤫', 'Có người đưa phong bì: từ chối và báo cấp trên.', s=['.hq-tempt .sk-opts'], g=3, o=True),
        S('⚖️', 'Chốt quyết định theo điều thật sự thấy.',
          s=[f".hq-step .sk-opts:has([data-payload*='\"step\":\"{k}\"'])" for k in ('decide', 'policy')], g=2,
          w='Làm hết các bước kiểm, ô Quyết định sẽ mở.'),
    ],
    # ✉️ Bưu điện Cánh Thư: eight steps per parcel, in the order the slip lays them out.
    'post_office': [
        S('✉️', 'Đọc giới thiệu rồi bấm Vào việc thôi!', s=['[data-command="post_intro"]'], o=True),
        S('📄', 'Bấm Đọc phiếu bưu gửi.', s=['.sk-ask'], g=0),
        S('🪪', 'So tên trên giấy với phiếu và mã kiện.', s=[".post-options:has([data-payload*='.identity\"'])"], g=0),
        S('🏷️', 'So nhãn với địa chỉ đã xác minh.', s=[".post-options:has([data-payload*='.address\"'])"], g=0),
        S('⚖️', 'Gõ số cân thực tế rồi bấm Ghi số cân.', s=[".post-step:has([data-extra*='.weight\"']) .sk-amt-go"], g=1),
        S('📦', 'Chọn bao gói theo món và cạnh dài.', s=[".post-options:has([data-payload*='.pack\"'])"], g=1),
        S('🚚', 'Chọn dịch vụ rẻ nhất mà vẫn kịp hạn.', s=[".post-options:has([data-payload*='.service\"'])"], g=2),
        S('🧮', 'Tính cước theo bảng, bấm Ghi cước vào phiếu.', s=[".post-step:has([data-extra*='.tariff\"']) .sk-amt-go"], g=2),
        S('🗺️', 'Chia tuyến đúng mã kiện và vùng.', s=[".post-options:has([data-payload*='.route\"'])"], g=3),
        S('🧾', 'Lưu đúng giấy bàn giao để khép phiếu.', s=[".post-options:has([data-payload*='.proof\"'])"], g=3),
    ],
    # 🏦 Quầy số 3, Ngân hàng Phố: học việc and the exam first, the float, five steps per customer, the handover.
    'teller': [
        S('🏦', 'Đọc giới thiệu rồi bấm Vào việc thôi!', s=['[data-command="tl_intro"]'], o=True),
        S('🎓', 'Học ba bài ngắn: đọc rồi chọn đáp án đúng.', s=['.tl-learn .tl-options'], g=('prep', 0), o=True),
        S('📝', 'Bấm Bắt đầu thi thực hành, làm đủ ba phần.', ['Bắt đầu thi thực hành'], ['.tl-exam-go'], g=('prep', 0), o=True),
        S('💼', 'Đầu ca: đếm quỹ rồi so với sổ bàn giao.', s=['.tl-shift'], g=0, o=True),
        S('🙋', 'Bấm Nhận yêu cầu để mời khách.', ['Nhận yêu cầu'], ['.sk-ask', '[data-command="ask"]'], g=1,
          w='Nút hiện khi có khách mới.'),
        S('🧾', 'Đọc phiếu, làm từng bước trên thẻ.', s=['.tl-step'], g=1),
        S('💵', 'Kéo hoặc chạm tờ tiền vào khay cho đúng số.', s=['.tl-tray'], g=2, o=True),
        S('✅', 'Khay khớp phiếu thì bấm Xác nhận khay tiền.', ['Xác nhận khay tiền'], ['.tl-tray-send'], g=2, o=True),
        S('🧾', 'Cuối ca: bàn giao quỹ, khớp từng biên nhận.', s=['.tl-close > summary'], g=3, x=True),
    ],
}

EN: dict[str, str] = {
    # shared
    'Mở tab Hồ sơ trước.': 'Open the File tab first.',
    'Còn việc dở sau 16:30: bấm Đăng ký tăng ca.': 'Work left after 16:30: tap Sign up for overtime.',
    'Mở chứng từ mà bước này cần.': 'Open the papers this step needs.',
    'Làm bước đang mở rồi bấm nút xác nhận ở dưới.': 'Do the open step, then tap the confirm button below.',
    'Nút ở thanh dưới, khi bạn mở hồ sơ tiếp theo.': 'The button is on the bottom bar once you open the next file.',
    'Bí quá thì bấm Xin gợi ý: mất 5 phút mỗi lần.': 'Stuck? Tap Ask for a hint: 5 minutes each time.',
    'Bước cuối: chọn ghi chú có số liệu, bấm Nộp hồ sơ.': 'Last step: pick the note with real figures, tap Submit file.',
    'Làm hết các bước, nút Nộp hồ sơ hiện ở thanh dưới.': 'Finish every step and Submit file shows on the bottom bar.',
    # office_work
    'Bấm Nhận hồ sơ để đọc yêu cầu.': 'Tap Take the file to read the request.',
    'Đọc giấy tờ kèm theo, chạm để mở từng tờ.': 'Read the attached papers, tap to open each one.',
    'Đọc thẻ, chạm khay đúng cho nó.': 'Read the card, tap the right tray for it.',
    'Chạm chỗ sai trên giấy để sửa.': 'Tap the wrong spot on the paper to fix it.',
    'Chọn cách sửa đúng cho chỗ này.': 'Pick the right fix for this spot.',
    'Chạm một ô trống hợp lệ để xếp việc đang chọn.': 'Tap a free, allowed slot to place the chosen item.',
    'Đọc lời người nói, gõ đủ từng ô.': 'Read what was said, fill in every box.',
    'Chạm các bước theo thứ tự sẽ làm.': 'Tap the steps in the order you will do them.',
    'Bấm tìm hiểu từng chuyện trước khi trả lời.': 'Look into each matter before you answer.',
    'Chọn cách trả lời hợp với chuyện đã biết.': 'Pick the answer that fits what you found.',
    'Có tin “Vừa đổi”: sửa theo tin mới rồi nộp.': 'A “Just changed” note: follow the new news, then submit.',
    'Làm xong hết thì bấm Nộp hồ sơ.': 'When everything is done, tap Submit file.',
    'Làm hết hồ sơ, nút Nộp hiện ở thanh dưới.': 'Finish the file and Submit shows on the bottom bar.',
    # accounting
    'Bấm Mở gốc từng phiếu để xem số gốc.': 'Tap Open original on each slip to see the real figure.',
    'Phiếu lệch gốc: bấm Sửa theo gốc.': 'Slip differs from the original: tap Fix to original.',
    'Hai phiếu cùng nguồn: bấm Đánh dấu trùng.': 'Two slips from one source: tap Mark duplicate.',
    'Phiếu thiếu nguồn: bấm Xin nguồn bổ sung.': 'Slip missing its source: tap Ask for the source.',
    'Chọn phiếu mang mã HD cần ghép.': 'Pick the slip with the invoice code to match.',
    'Mở tab Chứng từ.': 'Open the Documents tab.',
    'Chọn giao dịch cùng mã HD đó.': 'Pick the transaction with that same invoice code.',
    'Mở tab Giao dịch.': 'Open the Transactions tab.',
    'Hai tổng bằng nhau thì bấm Ghép nhóm.': 'When both totals match, tap Match group.',
    'Ghép hết thì bấm Kiểm & bàn giao hồ sơ.': 'All matched: tap Check & hand over.',
    'Ghép hết thẻ, nút Bàn giao hiện ở thanh dưới.': 'Match every card and Hand over shows on the bottom bar.',
    'Khách mới: bấm Nhận giấy tờ để trải sổ lên bàn.': 'New client: tap Take the papers to lay them out.',
    'Mở Sổ quy định hôm nay, xem luật MỚI.': "Open Today's rulebook, check the NEW rules.",
    'Chạm dòng sai trên giấy tờ.': 'Tap the wrong line on the papers.',
    'Chọn quy định mà dòng đó trái.': 'Pick the rule that line breaks.',
    'Có két: chạm từng tờ để đếm.': 'Cash box: tap each note to count it.',
    'Đếm xong thì bấm Chốt số đếm.': 'Done counting: tap Confirm count.',
    'Chọn một con dấu để Đóng dấu hồ sơ.': 'Pick one stamp to Stamp the file.',
    'Con dấu nằm cuối hồ sơ, sau giấy tờ.': 'The stamps are at the end of the file, after the papers.',
    # corp_accounting
    'Bấm Nhận khay chứng từ để bắt đầu.': 'Tap Take the voucher tray to start.',
    'Mở tab Quy định: hạn mức duyệt, nhà cung cấp bị chặn.': 'Open the Rules tab: approval limits, blocked suppliers.',
    'Chạm ô sai trên giấy để khoanh lại.': 'Tap the wrong box on the paper to circle it.',
    'Bấm DUYỆT, TRẢ LẠI hoặc TRÌNH SẾP cho bộ này.': 'Tap APPROVE, RETURN or TO THE BOSS for this set.',
    'Bấm Bộ tiếp theo, soát cho hết khay.': 'Tap Next set and check the whole tray.',
    'Đủ bộ thì bấm Chốt khay để báo chị Hạnh.': 'All sets done: tap Close tray to report to Ms Hạnh.',
    'Đóng dấu hết các bộ, nút Chốt khay hiện ở thanh dưới.': 'Stamp every set and Close tray shows on the bottom bar.',
    # tax_payroll
    'Bấm Nhận bảng lương nháp để bắt đầu.': 'Tap Take the draft payroll to start.',
    'Mở tab Quy định: hệ số tăng ca, mức sàn bảo hiểm.': 'Open the Rules tab: overtime rates, insurance floor.',
    'So với giấy tờ gốc, chạm ô sai để đánh dấu.': 'Compare with the source papers, tap a wrong box to flag it.',
    'Soát xong người này thì bấm Xong dòng.': 'Done with this person: tap Row done.',
    'Bấm Người tiếp theo, soát đủ cả bảng.': 'Tap Next person and check the whole sheet.',
    'Đủ người thì bấm Chuyển lương.': 'Everyone checked: tap Pay salaries.',
    'Soát xong hết người, nút Chuyển lương hiện ở thanh dưới.': 'Check everyone and Pay salaries shows on the bottom bar.',
    'Hồ sơ: làm bước đang mở rồi bấm Kiểm tra.': 'Files: do the open step, then tap Check.',
    'Bí thì bấm Gợi ý; trả lời sai mất thêm 15 phút.': 'Stuck? Tap Hint; a wrong answer costs 15 more minutes.',
    'Xong mọi bước thì bấm Nộp / bàn giao hồ sơ.': 'All steps done: tap Submit / hand over file.',
    'Làm hết các bước, nút nộp hiện ở thanh dưới.': 'Finish every step and the submit button shows on the bottom bar.',
    'Tới hạn tờ khai: bấm Nộp ở thẻ lịch nộp.': 'A return is due: tap File on the filing calendar card.',
    'Mở thẻ Lịch nộp trong Hộp thư.': 'Open the Filing calendar card in the Inbox.',
    # group_accounting
    'Bấm Nhận hai sổ đối chiếu để bắt đầu.': 'Tap Take the two ledgers to start.',
    'Chạm một dòng bên bán (cột 📤).': "Tap a line on the seller's side (📤 column).",
    'Chạm dòng cùng chứng từ bên mua (cột 📥).': "Tap the buyer's line with the same document (📥 column).",
    'Cùng số tiền: bấm Ghép cặp này.': 'Same amount: tap Pair these.',
    'Số lệch nhau: chọn Lệch tỷ giá hay Gõ nhầm số.': 'Amounts differ: pick Exchange-rate gap or Typo.',
    'Dòng chỉ có một bên: chọn nó, rồi chọn lý do ở dưới.': 'A line on one side only: select it, then pick a reason below.',
    'Có nhãn mới: Ghi trùng, Không phải nội bộ.': 'New labels: Booked twice, Not intra-group.',
    'Hai sổ khớp thì bấm Loại trừ để ghi bút toán.': 'Ledgers agree: tap Eliminate to post the entry.',
    'Ghép hết các dòng, nút Loại trừ hiện ở thanh dưới.': 'Settle every line and Eliminate shows on the bottom bar.',
    # customer_care
    'Bấm Xác minh mã đơn trước khi xem hồ sơ.': 'Tap Verify order code before opening the file.',
    'Mở từng chứng cứ, tìm dòng 📌 Căn cứ.': 'Open each piece of evidence, find the 📌 Basis line.',
    'Chọn phương án khớp dòng 📌 Căn cứ.': 'Pick the fix that matches the 📌 Basis line.',
    'Bấm Gửi việc cho đầu mối.': 'Tap Send to the contact person.',
    'Đầu mối đang làm: bấm Chờ thêm 20 phút.': 'They are on it: tap Wait 20 more minutes.',
    'Kết quả về: bấm Kiểm kết quả với khách.': 'Result is in: tap Check result with the customer.',
    'Bấm Hoàn tất & đóng vụ để nhận tiền.': 'Tap Finish & close the case to get paid.',
    'Chờ đầu mối làm xong, có khi tới sáng mai. Làm việc khác trước.': 'Wait for the contact to finish, maybe till tomorrow. Do other work first.',
    'Tin nhắn mới: chọn câu trả lời ân cần, đúng việc.': 'New message: pick a kind reply that fits the problem.',
    'Tới tin nhắn tiếp theo, câu trả lời hiện ở đầu.': 'On the next message, the replies show at the top.',
    'Bấm Mở hồ sơ đơn để xem đơn và lịch sử.': 'Tap Open order file to see the order and its history.',
    'Mở Sổ quy định hôm nay: hạn đổi trả, luật MỚI.': "Open Today's rulebook: return window, NEW rules.",
    'Chạm dòng có vấn đề trên đơn.': 'Tap the line with a problem on the order.',
    'Bấm bước kiểm, như Gọi số đã đăng ký.': 'Tap a check, like Call the registered number.',
    'Phải chờ kết quả thì bấm Chờ một nhịp.': 'Waiting for a result: tap Wait a beat.',
    # lawyer
    'Bấm Hỏi khách và mở hồ sơ.': 'Tap Ask the client and open the file.',
    'Đọc thỏa thuận, biên bản, lời kể và quy tắc bên dưới.': 'Read the agreement, record, account and rules below.',
    'Chạm hai tài liệu làm căn cứ chính.': 'Tap the two documents that are the main evidence.',
    'Chọn đủ hai thì bấm Gắn cặp chứng cứ.': 'With two picked, tap Pair the evidence.',
    'Chạm ba sự kiện theo ngày, sớm trước.': 'Tap the three events by date, earliest first.',
    'Xếp xong thì bấm Chốt dòng thời gian.': 'Once ordered, tap Lock the timeline.',
    'Chọn điểm mâu thuẫn cần làm rõ.': 'Pick the contradiction to clear up.',
    'Cộng chứng từ gốc, trừ tiền đã nhận, gõ số.': 'Add the original receipts, subtract what was paid, type it in.',
    'Chọn phương án bám đúng thỏa thuận.': 'Pick the plan that sticks to the agreement.',
    'Làm các bước trước, bước soạn phương án sẽ mở.': 'Do the earlier steps and the plan step opens.',
    'Buổi đối chiếu: chọn cách có căn cứ.': 'At the hearing: pick the answer backed by evidence.',
    # customs
    'Đọc giới thiệu rồi bấm Vào ca thôi!': "Read the intro, then tap Let's start the shift!",
    'Bấm Đọc hồ sơ để mở tờ khai.': 'Tap Read the file to open the declaration.',
    'Đọc tờ khai và luồng, chọn đúng việc cần làm.': 'Read the declaration and its lane, pick the right action.',
    'Kiểm đúng việc luồng yêu cầu, chọn theo điều thấy.': 'Check what the lane asks for, answer by what you see.',
    'Tính thuế, gõ số xu rồi bấm Ghi vào tờ khai.': 'Work out the tax, type the coins, tap Write on the declaration.',
    'Có người đưa phong bì: từ chối và báo cấp trên.': 'Someone offers an envelope: refuse and report it.',
    'Chốt quyết định theo điều thật sự thấy.': 'Make the decision by what you really found.',
    'Làm hết các bước kiểm, ô Quyết định sẽ mở.': 'Finish every check and the Decision box opens.',
    # post_office
    'Đọc giới thiệu rồi bấm Vào việc thôi!': "Read the intro, then tap Let's get to work!",
    'Bấm Đọc phiếu bưu gửi.': 'Tap Read the parcel slip.',
    'So tên trên giấy với phiếu và mã kiện.': 'Match the name on the ID with the slip and parcel code.',
    'So nhãn với địa chỉ đã xác minh.': 'Match the label with the verified address.',
    'Gõ số cân thực tế rồi bấm Ghi số cân.': 'Type the real scale weight, then tap Record weight.',
    'Chọn bao gói theo món và cạnh dài.': 'Pick packing for the item and its longest side.',
    'Chọn dịch vụ rẻ nhất mà vẫn kịp hạn.': 'Pick the cheapest service that still meets the deadline.',
    'Tính cước theo bảng, bấm Ghi cước vào phiếu.': 'Work out postage from the table, tap Write postage on slip.',
    'Chia tuyến đúng mã kiện và vùng.': 'Route it by parcel code and zone.',
    'Lưu đúng giấy bàn giao để khép phiếu.': 'File the right handover proof to close the slip.',
    # teller
    'Học ba bài ngắn: đọc rồi chọn đáp án đúng.': 'Three short lessons: read, then pick the right answer.',
    'Bấm Bắt đầu thi thực hành, làm đủ ba phần.': 'Tap Start the practical exam and do all three parts.',
    'Đầu ca: đếm quỹ rồi so với sổ bàn giao.': 'Start of shift: count the float, then check the handover book.',
    'Bấm Nhận yêu cầu để mời khách.': 'Tap Take the request to call the customer.',
    'Nút hiện khi có khách mới.': 'The button shows when a new customer comes.',
    'Đọc phiếu, làm từng bước trên thẻ.': 'Read the slip, do each step on the card.',
    'Kéo hoặc chạm tờ tiền vào khay cho đúng số.': 'Drag or tap notes into the tray to the exact amount.',
    'Khay khớp phiếu thì bấm Xác nhận khay tiền.': 'When the tray matches the slip, tap Confirm the tray.',
    'Cuối ca: bàn giao quỹ, khớp từng biên nhận.': 'End of shift: hand over the drawer, match every receipt.',
}
