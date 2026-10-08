"""Desk cases for the pharmacy counter, the bookkeeping desk and the support
station.

A case is a small "papers on the counter" puzzle: documents with fields, a
rulebook that changes a little every day (recalled lots, new clinic stamps,
bank fees, courier delays), optional checks (call the clinic, read the fridge
log, count the till, ask the courier) and a final verdict. Everything is built
from (career, day, slot) only, so saves can regenerate and compare the facts.
People, clinics, medicines, banks and rules are fictional; the counter never
gives dosing advice, it checks paperwork and process.
"""
from __future__ import annotations

import functools
import hashlib
import random

CAREERS = ('pharmacy', 'accounting', 'customer_care')


def rng(*parts) -> random.Random:
    seed = int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16)
    return random.Random(seed)


def tier(day: int) -> int:
    return 1 if day <= 2 else 2 if day <= 5 else 3 if day <= 9 else 4


def F(fid, label, value, hidden=None, mark=None):
    row = dict(id=fid, label=label, value=value)
    if hidden:
        row['hidden'] = hidden
    if mark:
        row['mark'] = mark
    return row


def D(did, title, icon, fields, kind='paper'):
    return dict(id=did, title=title, icon=icon, kind=kind, fields=fields)


def C(cid, label, icon, delay=0):
    return dict(id=cid, label=label, icon=icon, delay=delay)


def I(iid, fields, rule, why):
    return dict(id=iid, fields=list(fields), rule=rule, why=why)


def xu(amount: int) -> str:
    return ('+' if amount > 0 else '−' if amount < 0 else '') + f'{abs(amount)} xu'


# ---------------------------------------------------------------- verdicts
VERDICTS = {
    'pharmacy': {
        'give': ('Giao đúng phiếu', '✅'), 'fix': ('Đổi cho đúng rồi giao', '🔁'),
        'refuse': ('Từ chối, giải thích rõ', '✋'), 'refer': ('Chuyển cô Thu', '👩‍⚕️'),
        'accept': ('Nhận lô hàng', '📦'), 'own': ('Nhận thiếu sót, bổ sung ngay', '📝'),
        'excuse': ('Giải thích cho qua', '💬'),
    },
    'accounting': {
        'post': ('Chốt sổ như đang có', '✅'), 'adjust': ('Điều chỉnh có ghi chú rồi chốt', '✏️'),
        'hold': ('Giữ lại, xin thêm chứng từ', '⏸️'), 'report': ('Báo chị Vân', '📣'),
        'close': ('Chốt quỹ, ký sổ', '🔒'), 'minutes': ('Lập biên bản lệch quỹ', '📝'),
        'cover': ('Tự bù phần thiếu', '👛'), 'force': ('Sửa sổ cho khớp két', '🩹'),
        'record': ('Ghi đủ, nói rõ với cô Hoa', '📒'), 'comply': ('Làm theo lời cô Hoa', '🤫'),
        'pay': ('Chuyển tiền theo thư', '💸'), 'claim': ('Đề nghị trừ vào lần mua sau', '🤝'),
        'reply': ('Gửi bảng đối chiếu cho họ', '📨'), 'ignore': ('Để yên, không trả lời', '🙈'),
        'explain': ('Gửi giải trình kèm chứng từ', '📨'), 'own': ('Nhận thiếu sót, bổ sung ngay', '📝'),
        'excuse': ('Giải thích cho qua', '💬'),
    },
    'customer_care': {
        'explain': ('Giải thích & hướng dẫn', '💬'), 'exchange': ('Đổi đúng món', '🔁'),
        'reship': ('Gửi bù / gửi lại', '📦'), 'refund': ('Hoàn tiền', '💸'),
        'trace': ('Mở đối soát giao nhận', '🔎'), 'deny': ('Từ chối có căn cứ', '✋'),
        'lock': ('Tạm khóa & gọi xác minh', '🔒'), 'escalate': ('Chuyển chị Mai', '🧑‍💼'), 'change': ('Đổi địa chỉ theo yêu cầu', '📍'),
        'public': ('Trả lời công khai, mời nhắn riêng', '📣'), 'detail': ('Đăng chi tiết đơn để minh oan', '📃'),
        'hide': ('Ẩn bài chê', '🙈'), 'favor': ('Ưu tiên cho bạn của Phúc', '🤝'),
    },
}


def verdicts(career, ids):
    return [dict(id=v, label=VERDICTS[career][v][0], icon=VERDICTS[career][v][1]) for v in ids]


# ---------------------------------------------------------------- rulebooks
RULES = {
    'pharmacy': {
        'ph_rx': ('Cần phiếu', 'Thuốc nhóm K và hàng lạnh chỉ giao khi có phiếu của phòng khám.'),
        'ph_date': ('Phiếu còn hạn', 'Phiếu chỉ dùng tới hết ngày ghi ở dòng “Hạn phiếu”. Hôm nay là ngày {day} ở quầy.'),
        'ph_name': ('Đúng tên, đúng hàm lượng', 'Tên và hàm lượng trên hộp phải trùng từng chữ với phiếu.'),
        'ph_qty': ('Không quá số lượng', 'Không giao nhiều hơn số lượng ghi trên phiếu.'),
        'ph_stamp': ('Dấu đúng mẫu', 'Con dấu phải đúng mẫu phòng khám đã đăng ký trong bản tin hôm nay.'),
        'ph_person': ('Đúng người nhận', 'Người nhận là người có tên trên phiếu hoặc người ghi ở dòng “Nhận thay”.'),
        'ph_label': ('Còn nhãn, rõ lô', 'Không giao theo vỉ lẻ đã mất nhãn, không rõ tên và lô.'),
        'ph_cold': ('Tủ mát 2–8°C', 'Hàng lạnh chỉ giao khi nhật ký tủ mát cả ngày nằm trong 2–8°C.'),
        'ph_dup': ('Báo khi trùng thuốc', 'Phiếu mới có thuốc trùng với thuốc đang dùng: báo cô Thu trước khi giao.'),
        'ph_log': ('Ghi sổ đủ dòng', 'Mỗi lần giao thuốc nhóm K phải ghi số phiếu vào sổ; tủ mát ghi đủ các mốc giờ.'),
        'ph_recall': ('Lô thu hồi', 'Không giao các lô trong danh sách thu hồi: {lots}.'),
        'ph_supply': ('Nhập hàng có tem mới', 'Chỉ nhập lô có hóa đơn ghi mã số thuế và tem chống giả mẫu mới có sợi bạc 🧵.'),
    },
    'accounting': {
        'ac_source': ('Có chứng từ', 'Mỗi dòng sổ phải có hóa đơn hoặc phiếu gốc đi kèm.'),
        'ac_once': ('Ghi một lần', 'Một khoản chỉ được ghi một lần, dù có hai bản giấy.'),
        'ac_amount': ('Đúng số gốc', 'Số ghi sổ phải bằng số trên hóa đơn hoặc sao kê.'),
        'ac_period': ('Đúng kỳ', 'Khoản phát sinh kỳ nào ghi vào kỳ đó. Kỳ này: ngày {start}–{end}.'),
        'ac_private': ('Không lẫn việc riêng', 'Chi tiêu riêng của gia đình không ghi vào chi phí của tiệm.'),
        'ac_income': ('Ghi đủ doanh thu', 'Mọi khoản bán được đều vào sổ, kể cả tiền mặt.'),
        'ac_deposit': ('Cọc chưa là doanh thu', 'Tiền cọc giữ chỗ ghi vào khoản nhận trước, chưa tính doanh thu.'),
        'ac_cash': ('Két khớp sổ quỹ', 'Tiền thật trong két phải bằng số dư sổ quỹ. Lệch thì lập biên bản, không tự bù, không sửa sổ.'),
        'ac_note': ('Điều chỉnh có lý do', 'Mỗi lần sửa sổ phải ghi lý do và chứng từ kèm theo.'),
        'ac_fee': ('Phí chuyển khoản', 'Ngân hàng thu {fee} xu mỗi lần chuyển; ghi thành một dòng chi riêng.'),
        'ac_payee': ('Đổi tài khoản phải xác minh', 'Nhà cung cấp báo đổi số tài khoản: chỉ chuyển khi gọi số trong hồ sơ để xác nhận.'),
        'ac_fake': ('Tờ tiền lạ', 'Tờ 50 xu thật có sợi bạc 🧵. Tờ không có sợi bạc thì tách riêng, không tính vào két.'),
    },
    'customer_care': {
        'cs_id': ('Xác minh chủ đơn', 'Chỉ đổi thông tin đơn khi số điện thoại khớp hồ sơ; khác số thì gọi số đã đăng ký.'),
        'cs_proof': ('Hoàn cần chứng cứ', 'Hoàn tiền khi có ảnh mở hộp hoặc biên bản giao; ảnh phải chụp sau lúc nhận.'),
        'cs_window': ('Hạn đổi trả', 'Đổi trả trong {days} ngày kể từ ngày nhận hàng.'),
        'cs_place': ('Giao đúng điểm', 'Chỉ tính đã giao khi điểm giao trùng địa chỉ trên đơn.'),
        'cs_match': ('Đúng món trên đơn', 'Hàng giao phải đúng mã, màu và số lượng trên đơn.'),
        'cs_payout': ('Không đổi tài khoản qua chat', 'Không đổi tài khoản nhận tiền hoàn qua chat; phải gọi số đã đăng ký.'),
        'cs_safety': ('Đe dọa thì chuyển', 'Lời đe dọa, chuyện an toàn hay pháp lý: chuyển chị Mai ngay.'),
        'cs_public': ('Trả lời công khai gọn', 'Trả lời công khai ngắn, đúng sự thật, không đăng thông tin đơn của khách.'),
        'cs_promise': ('Giữ lời hẹn', 'Đã hẹn thì làm đúng hẹn; lỡ hẹn thì nhận lỗi và làm ngay bước còn lại.'),
        'cs_fair': ('Công bằng hàng đợi', 'Xử lý theo thứ tự và mức ưu tiên, không theo quen biết.'),
        'cs_hold': ('Tiền giữ tạm', 'Khoản “giữ tạm” khi thanh toán lỗi sẽ tự hoàn sau 3 ngày, không hoàn tay.'),
        'cs_delay': ('Báo đúng mốc', 'Chưa giao thì báo mốc mới; không ghi “đã giao” khi chưa có xác nhận.'),
        'cs_reply': ('Trả lời trong hạn', 'Mỗi tin nhắn có hạn phản hồi, xem đồng hồ trên vé. Trả lời câu đầu trước, xử lý sau.'),
    },
}
STANDING = {
    'pharmacy': ['ph_rx', 'ph_date', 'ph_name', 'ph_qty', 'ph_stamp', 'ph_person', 'ph_cold'],
    'accounting': ['ac_source', 'ac_once', 'ac_amount', 'ac_period', 'ac_private', 'ac_income', 'ac_deposit', 'ac_cash', 'ac_fee'],
    'customer_care': ['cs_id', 'cs_proof', 'cs_window', 'cs_place', 'cs_match', 'cs_hold', 'cs_payout', 'cs_safety', 'cs_public', 'cs_promise'],
}

# ---------------------------------------------------------------- pharmacy world
CLINICS = {'hp': 'PK Hạnh Phúc', 'ak': 'PK An Khang', 'mh': 'PK Mây Hồng'}
BASE_STAMPS = {'hp': 'tron-do-5', 'ak': 'vuong-xanh-4', 'mh': 'luc-tim-6'}
SHAPES = {'tron': 'Tròn', 'vuong': 'Vuông', 'luc': 'Lục giác'}
COLORS = {'do': 'đỏ', 'xanh': 'xanh', 'tim': 'tím'}
DRUGS = {
    'kl250': dict(name='Kháng Lam 250', group='K', code='KL'),
    'kl500': dict(name='Kháng Lam 500', group='K', code='KL'),
    'dh': dict(name='Viên Điều Hòa Mây', group='K', code='DH'),
    'hoatlan': dict(name='Viên Hoạt Lan', group='K', code='HL'),
    'hoatlam': dict(name='Viên Hoạt Lam', group='K', code='HM'),
    'tuyet': dict(name='Lọ Tuyết Lạnh', group='L', code='TL'),
    'maytam': dict(name='Siro Mây Tâm', group='T', code='MT'),
    'maytam_eye': dict(name='Nhỏ mắt Mây Tầm', group='T', code='MM'),
    'gung': dict(name='Viên Gừng Ấm', group='T', code='GA'),
    'menla': dict(name='Men Lá Xanh', group='T', code='ML'),
}
PATIENTS = ['Bà Tư', 'Ông Sáu', 'Chị Mận', 'Bé Na', 'Anh Tài', 'Cô Ba', 'Chú Lộc', 'Em Bống', 'Ông Khải', 'Chị Duyên']


def stamp_text(mark: str) -> str:
    shape, color, petals = mark.split('-')
    return f'{SHAPES[shape]} · {COLORS[color]} · {petals} cánh'


def _mutate(mark: str, r: random.Random, avoid=()) -> str:
    shape, color, petals = mark.split('-')
    for _ in range(20):
        k = r.randrange(3)
        s2, c2, p2 = shape, color, petals
        if k == 0:
            s2 = r.choice([x for x in SHAPES if x != shape])
        elif k == 1:
            c2 = r.choice([x for x in COLORS if x != color])
        else:
            p2 = r.choice([x for x in ('4', '5', '6') if x != petals])
        out = f'{s2}-{c2}-{p2}'
        if out not in avoid:
            return out
    return out


def stamp_changes(day: int) -> list[tuple[int, str, str, str]]:
    """(day, clinic, old, new) for every registered stamp change up to `day`."""
    rows, current, k = [], dict(BASE_STAMPS), 1
    while 3 + 4 * (k - 1) <= day:
        when = 3 + 4 * (k - 1)
        clinic = list(CLINICS)[(k - 1) % 3]
        new = _mutate(current[clinic], rng('stamp', k), avoid=tuple(current.values()))
        rows.append((when, clinic, current[clinic], new))
        current[clinic] = new
        k += 1
    return rows


def stamps(day: int) -> dict:
    current = dict(BASE_STAMPS)
    for _, clinic, _, new in stamp_changes(day):
        current[clinic] = new
    return current


def recall_lots(day: int) -> list[str]:
    if day < 2:
        return []
    r = rng('recall', day)
    lots = [f'{r.choice(["KL", "DH", "HL", "TL"])}-{r.randint(101, 899)}']
    if tier(day) >= 3:
        lots.append(f'{r.choice(["MT", "GA", "KL"])}-{r.randint(101, 899)}')
    return lots


def bank_fee(day: int) -> int:
    return [11, 11, 9, 13, 9, 12][((day - 1) // 3) % 6]


def period(day: int) -> tuple[int, int]:
    k = (day - 1) // 7
    return 7 * k + 1, 7 * k + 7


def window_days(day: int) -> int:
    return 7 if (day // 4) % 2 == 0 else 5


def slow_zone(day: int) -> str | None:
    if day < 3:
        return None
    return ['Bến Mây', 'Chợ Sớm', 'Đồi Lá', None][day % 4]


INSPECT_EVERY = {'pharmacy': 4, 'accounting': 5, 'customer_care': 6}


def bulletin(career: str, day: int) -> dict:
    """Today's rulebook and notices. Pure function of (career, day)."""
    rules = list(STANDING[career])
    notices, fmt, new = [], {}, set()
    extra = {}
    if career == 'pharmacy':
        fmt['ph_date'] = dict(day=day)  # #273: the slip's "Hết ngày N" counts the counter's days, not the town's (journey life day)
        lots = recall_lots(day)
        if lots:
            rules.append('ph_recall')
            fmt['ph_recall'] = dict(lots=', '.join(lots))
            if day == 2:
                new.add('ph_recall')
        if day >= 4:
            rules.append('ph_supply')
            if day == 4:
                new.add('ph_supply')
        if day >= 5:
            rules.append('ph_label')
        if day >= 9:
            rules.append('ph_dup')
        if day % INSPECT_EVERY[career] == 0:
            rules.append('ph_log')
        reg = stamps(day)
        changed = {clinic: (old, when) for when, clinic, old, _ in stamp_changes(day) if when >= day - 1}
        for clinic, name in CLINICS.items():
            if clinic in changed:
                notices.append(f'{name} đổi mẫu dấu mới: {stamp_text(reg[clinic])}. Mẫu cũ ({stamp_text(changed[clinic][0])}) hết dùng.')
            else:
                notices.append(f'{name}: dấu {stamp_text(reg[clinic])}.')
        if any(when == day for when, *_ in stamp_changes(day)):
            new.add('ph_stamp')
        if day % INSPECT_EVERY[career] == 0:
            notices.append('Chiều nay có đoàn kiểm tra ghé quầy. Sổ sách cần gọn gàng.')
        extra = dict(stamps=reg, recall=lots)
    elif career == 'accounting':
        start, end = period(day)
        fmt['ac_period'] = dict(start=start, end=end)
        fee = bank_fee(day)
        fmt['ac_fee'] = dict(fee=fee)
        if day > 1 and fee != bank_fee(day - 1):
            new.add('ac_fee')
            notices.append(f'Ngân hàng đổi phí chuyển khoản: {fee} xu mỗi lần.')
        else:
            notices.append(f'Phí chuyển khoản hôm nay: {fee} xu mỗi lần.')
        if day >= 3:
            rules.append('ac_note')
        if day >= 4:
            rules.append('ac_payee')
            if day == 4:
                new.add('ac_payee')
        if day >= 6:
            rules.append('ac_fake')
            if day == 6:
                new.add('ac_fake')
            if day in (6, 7):
                notices.append('Khu phố có tờ 50 xu lạ: tờ thật có sợi bạc 🧵.')
        if day == end:
            notices.append(f'Hôm nay khóa sổ kỳ ngày {start}–{end}.')
        if day % INSPECT_EVERY[career] == 0:
            notices.append('Chị Trâm kiểm tra nội bộ cuối ngày. Mọi chỗ sửa cần có lý do.')
        extra = dict(fee=fee, period=[start, end])
    else:
        days = window_days(day)
        fmt['cs_window'] = dict(days=days)
        if day > 1 and days != window_days(day - 1):
            new.add('cs_window')
            notices.append(f'Chính sách mới: đổi trả trong {days} ngày.')
        if day >= 5:
            rules.append('cs_fair')
            if day == 5:
                new.add('cs_fair')
        zone = slow_zone(day)
        if day >= 3:
            rules += ['cs_reply', 'cs_delay']
            if day == 3:
                new |= {'cs_reply', 'cs_delay'}
        if zone:
            notices.append(f'Mây Express đang chậm 2 ngày ở khu {zone}.')
        if day % 5 == 0:
            notices.append('Hôm nay có đợt giảm giá: hàng đợi đông, phản hồi sớm nhé.')
        if day % INSPECT_EVERY[career] == 0:
            notices.append('Cuối ngày chị Mai xem báo cáo tuần: hạn phản hồi và các vụ nhạy cảm.')
        extra = dict(window=days, zone=zone, sale=day % 5 == 0)
    book = []
    for rid in rules:
        short, text = RULES[career][rid]
        if rid in fmt:
            text = text.format(**fmt[rid])
        book.append(dict(id=rid, short=short, text=text, new=rid in new))
    return dict(rules=book, notices=notices, **extra)


# ---------------------------------------------------------------- pharmacy cases
def _lot(r, drug, b):
    while True:
        lot = f'{DRUGS[drug]["code"]}-{r.randint(101, 899)}'
        if lot not in b.get('recall', []):
            return lot


def _slip(r, day, b, drug, qty=1, until=None, clinic=None, stamp=None, patient=None, pickup=None):
    clinic = clinic or r.choice(sorted(CLINICS))
    stamp = stamp or b['stamps'][clinic]
    until = day + r.randint(1, 4) if until is None else until
    fields = [F('clinic', 'Phòng khám', CLINICS[clinic]), F('no', 'Số phiếu', f'PK-{r.randint(401, 989)}'),
              F('patient', 'Người dùng', patient or r.choice(PATIENTS)),
              F('drug', 'Thuốc', DRUGS[drug]['name']), F('qty', 'Số lượng', f'{qty} hộp'),
              F('until', 'Hạn phiếu', f'Hết ngày {until}'), F('stamp', 'Con dấu', stamp_text(stamp), mark=stamp)]
    if pickup is not None:
        fields.insert(3, F('pickup', 'Nhận thay', pickup))
    return D('slip', 'Phiếu phòng khám', '📋', fields)


def _tray(r, b, drug, count, lot=None, name=None):
    return D('tray', 'Khay chuẩn bị', '🧰', [F('name', 'Tên trên hộp', name or DRUGS[drug]['name']),
                                             F('lot', 'Số lô', lot or _lot(r, drug, b)), F('count', 'Số hộp', f'{count} hộp')])


def _fridge(bad=False, r=None):
    noon = f'{r.choice([10, 11, 12])}°C' if bad else f'{r.choice([4, 5, 6])}°C'
    return D('fridge', 'Nhật ký tủ mát', '🌡️', [F('t8', '8 giờ', f'{r.choice([4, 5])}°C', hidden='fridge'),
                                                F('t12', '12 giờ', noon, hidden='fridge'),
                                                F('t15', '15 giờ', f'{r.choice([5, 6])}°C', hidden='fridge')])


PH_STD = ['give', 'fix', 'refuse', 'refer']


def ph_clean(r, day, tr, b):
    cold = tr >= 2 and r.random() < 0.4
    drug = 'tuyet' if cold else r.choice(['kl250', 'dh', 'hoatlan'])
    qty = r.choice([1, 2])
    clinic = r.choice(sorted(CLINICS))
    # A clinic that changed its stamp recently is a nice trap: the NEW stamp is the valid one.
    changed = [c for when, c, _, _ in stamp_changes(day) if when >= day - 1]
    if changed and tr >= 2:
        clinic = changed[-1]
    who = r.choice([2, 3, 6])
    docs = [_slip(r, day, b, drug, qty, clinic=clinic), _tray(r, b, drug, qty)]
    checks, needs = [], []
    if cold:
        docs.append(_fridge(False, r))
        checks.append(C('fridge', 'Xem nhật ký tủ mát', '🌡️'))
        needs.append('fridge')
    return dict(npc=who, title=r.choice(['Một phiếu gọn gàng', 'Lấy thuốc theo phiếu', 'Phiếu mới từ phòng khám']),
                opening=r.choice(['Chào bạn, mình lấy thuốc theo phiếu nhé.', 'Mình vừa khám xong, bạn lấy giúp mình theo phiếu này.']),
                request='Phiếu đây, bạn soát giúp mình rồi giao nhé.',
                docs=docs, checks=checks, verdicts=verdicts('pharmacy', PH_STD), issues=[],
                accept={'give': 'best'}, needs=needs, risk={}, pleases=['give'],
                says=dict(give='Khách nhận đủ hộp đúng phiếu và cảm ơn vì quầy soát nhanh mà kỹ.',
                          fix='Khay vốn đã đúng; đổi qua đổi lại làm khách chờ thêm và hơi rối.',
                          refuse='Phiếu hợp lệ mà bị từ chối, khách phải quay lại phòng khám hỏi cho ra lẽ.',
                          refer='Cô Thu xem lại rồi cười: “Phiếu đủ cả mà, cháu tự giao được.”'))


def ph_otc(r, day, tr, b):
    drug = r.choice(['maytam', 'gung', 'menla'])
    who = r.choice([2, 3, 6])
    ask = D('ask', 'Khách nói', '💬', [F('want', 'Cần mua', f'{DRUGS[drug]["name"]} · 1 hộp'), F('slip', 'Phiếu', 'Không có phiếu')])
    return dict(npc=who, title='Không cần phiếu vẫn đúng quy trình', opening='Cho mình mua một hộp thôi, mình không có phiếu đâu.',
                request=f'Mình lấy một hộp {DRUGS[drug]["name"]} nhé.',
                docs=[ask, _tray(r, b, drug, 1)], checks=[], verdicts=verdicts('pharmacy', PH_STD), issues=[],
                accept={'give': 'best'}, needs=[], risk={}, pleases=['give'],
                says=dict(give='Hàng thông thường không cần phiếu; khách nhận đúng hộp đã chọn.',
                          fix='Không có gì cần đổi, khách chờ thêm một lúc.',
                          refuse='Hàng này không cần phiếu. Khách bực vì bị từ chối vô cớ.',
                          refer='Cô Thu nhắc: hàng thông thường thì quầy tự giao được.'))


def ph_expired(r, day, tr, b):
    drug = r.choice(['kl250', 'dh', 'hoatlan'])
    until = max(1, day - r.randint(1, 3))
    who = r.choice([2, 3, 6])
    issues = [I('date', ['slip.until'], 'ph_date', f'Phiếu chỉ dùng tới hết ngày {until}; hôm nay đã là ngày {day}.')]
    tray = _tray(r, b, drug, 1)
    docs = [_slip(r, day, b, drug, 1, until=until), tray]
    if tr >= 3 and r.random() < 0.5:
        docs.append(D('ask', 'Khách nói', '💬', [F('want', 'Muốn lấy', '3 hộp cho đỡ đi lại')]))
        issues.append(I('qty', ['ask.want'], 'ph_qty', 'Phiếu ghi 1 hộp, khách xin 3 hộp.'))
    return dict(npc=who, title='Tờ phiếu hơi cũ', opening='Phiếu này mình để trong ví mấy hôm, vẫn dùng được chứ?',
                request='Bạn lấy giúp mình như phiếu nhé, mình đang vội.',
                docs=docs, checks=[], verdicts=verdicts('pharmacy', PH_STD), issues=issues,
                accept={'refuse': 'best', 'refer': 'ok'}, needs=[], risk={'give': 2, 'fix': 2}, pleases=['give', 'fix'],
                says=dict(give='Thuốc nhóm K đã giao theo phiếu hết hạn. Cô Thu ghi một lỗi vào sổ quầy.',
                          fix='Đổi hộp không làm phiếu còn hạn; cô Thu ghi một lỗi vào sổ quầy.',
                          refuse='Bạn chỉ dòng hạn phiếu và chỉ đường về phòng khám xin phiếu mới. Khách hơi tiếc nhưng hiểu.',
                          refer='Cô Thu giải thích cùng khách và gọi phòng khám hẹn cấp phiếu mới.'))


def ph_stamp(r, day, tr, b):
    drug = r.choice(['kl250', 'kl500', 'dh'])
    clinic = r.choice(sorted(CLINICS))
    old = [o for when, c, o, _ in stamp_changes(day) if c == clinic]
    if old and tr >= 3 and r.random() < 0.6:
        fake = old[-1]
        why = f'Dấu trên phiếu là mẫu cũ của {CLINICS[clinic]}; bản tin hôm nay ghi mẫu mới {stamp_text(b["stamps"][clinic])}.'
    else:
        fake = _mutate(b['stamps'][clinic], r, avoid=tuple(b['stamps'].values()))
        why = f'{CLINICS[clinic]} đăng ký dấu {stamp_text(b["stamps"][clinic])}; dấu trên phiếu là {stamp_text(fake)}.'
    who = r.choice([3, 6])
    call = D('call', 'Gọi phòng khám', '📞', [F('reply', 'Phòng khám trả lời', 'Không có phiếu số này trong sổ khám hôm nay.', hidden='call')])
    return dict(npc=who, title='Con dấu trông lạ lạ', opening='Bạn lấy nhanh giúp mình nhé, phiếu đầy đủ cả rồi.',
                request='Hai hộp như phiếu nhé, mình trả tiền mặt luôn.',
                docs=[_slip(r, day, b, drug, 2, clinic=clinic, stamp=fake), _tray(r, b, drug, 2), call],
                checks=[C('call', 'Gọi phòng khám xác minh', '📞')],
                verdicts=verdicts('pharmacy', PH_STD), issues=[I('stamp', ['slip.stamp'], 'ph_stamp', why)],
                accept={'refer': 'best', 'refuse': 'ok'}, needs=[], risk={'give': 3, 'fix': 3}, pleases=['give', 'fix'],
                says=dict(give='Hai hộp nhóm K đã ra khỏi quầy theo một phiếu không có trong sổ phòng khám.',
                          fix='Đổi hộp không làm con dấu thành thật; phiếu vẫn không hợp lệ.',
                          refuse='Bạn từ chối và nói rõ dấu không khớp. Khách bỏ đi, tờ phiếu cũng đi theo.',
                          refer='Cô Thu giữ lại phiếu, báo phòng khám. Họ cảm ơn quầy vì đã phát hiện phiếu giả.'))


def ph_lookalike(r, day, tr, b):
    want, got = r.choice([('hoatlan', 'hoatlam'), ('maytam', 'maytam_eye')])
    qty = 1
    docs = [_slip(r, day, b, want, qty), _tray(r, b, got, qty)]
    if DRUGS[want]['group'] == 'T':
        docs = [D('ask', 'Khách nói', '💬', [F('want', 'Cần mua', f'{DRUGS[want]["name"]} · 1 hộp')]), _tray(r, b, got, qty)]
        issue = I('name', ['tray.name'], 'ph_name', f'Khách cần {DRUGS[want]["name"]}, khay lại là {DRUGS[got]["name"]}.')
    else:
        issue = I('name', ['tray.name'], 'ph_name', f'Phiếu ghi {DRUGS[want]["name"]}, hộp trên khay là {DRUGS[got]["name"]}.')
    return dict(npc=4, title='Hai cái tên na ná', opening='Mình lấy sẵn khay cho khách rồi nè, bạn soát giúp rồi giao nhé!',
                request='Khoa: “Hộp để ngay cạnh nhau, mình nhìn lướt thấy giống nên lấy luôn.”',
                docs=docs, checks=[], verdicts=verdicts('pharmacy', PH_STD), issues=[issue],
                accept={'fix': 'best', 'refer': 'ok'}, needs=[], risk={'give': 2}, pleases=['give'],
                says=dict(give='Khách mang về một hộp khác tên với thứ cần mua. Tối đó cô Thu phải gọi khách quay lại đổi.',
                          fix='Bạn chỉ cho Khoa hai chữ khác nhau rồi đổi đúng hộp. Khoa ghi “đọc hết tên” lên góc khay.',
                          refuse='Khách vẫn mua được đúng thứ cần; từ chối làm khách về tay không.',
                          refer='Cô Thu đổi hộp giúp, rồi nhắc Khoa đọc hết tên trước khi đặt vào khay.'))


def ph_strength(r, day, tr, b):
    return dict(npc=r.choice([2, 3]), title='Hết hộp 250 rồi', opening='Khoa bảo hết hộp như phiếu, lấy hộp to hơn cũng được mà nhỉ?',
                request='Hộp 500 cũng là Kháng Lam, bẻ đôi ra dùng là được chứ gì.',
                docs=[_slip(r, day, b, 'kl250', 1), _tray(r, b, 'kl500', 1),
                      D('shelf', 'Kệ nhóm K', '🗄️', [F('kl250', 'Kháng Lam 250', 'Hết hàng'), F('kl500', 'Kháng Lam 500', 'Còn 4 hộp')])],
                checks=[], verdicts=verdicts('pharmacy', PH_STD),
                issues=[I('strength', ['tray.name'], 'ph_name', 'Phiếu ghi hàm lượng 250, hộp trên khay là 500.')],
                accept={'refer': 'best', 'refuse': 'ok'}, needs=[], risk={'give': 2, 'fix': 2}, pleases=['give', 'fix'],
                says=dict(give='Quầy đã tự đổi hàm lượng khác phiếu. Cô Thu ghi lỗi và gọi khách quay lại.',
                          fix='Kệ không còn hộp 250 để đổi; đưa hộp 500 vẫn là đổi hàm lượng. Cô Thu ghi lỗi.',
                          refuse='Bạn hẹn khách mai quay lại khi có hàng đúng phiếu. Khách hơi phiền nhưng không sao.',
                          refer='Cô Thu gọi phòng khám hỏi phương án và giữ hẹn lấy hàng cho khách. Không ai phải tự đoán.'))


def ph_qty(r, day, tr, b):
    drug = r.choice(['kl250', 'dh', 'hoatlan'])
    docs = [_slip(r, day, b, drug, 1), _tray(r, b, drug, 3), D('ask', 'Khách nói', '💬', [F('want', 'Muốn lấy', '3 hộp, lấy luôn cho tháng sau')])]
    return dict(npc=r.choice([2, 6]), title='Lấy dư cho chắc', opening='Cho mình lấy thêm hai hộp, đỡ phải đi lại nhé!',
                request='Khoa đã để 3 hộp vào khay theo lời khách.',
                docs=docs, checks=[], verdicts=verdicts('pharmacy', PH_STD),
                issues=[I('qty', ['tray.count', 'ask.want'], 'ph_qty', 'Phiếu ghi 1 hộp; khay đang có 3 hộp.')],
                accept={'fix': 'best', 'refer': 'ok'}, needs=[], risk={'give': 1}, pleases=['give'],
                says=dict(give='Hai hộp nhóm K ra khỏi quầy ngoài phiếu. Cô Thu ghi một lỗi.',
                          fix='Bạn cất hai hộp dư, giao đúng 1 hộp theo phiếu và hẹn khách mang phiếu mới khi cần.',
                          refuse='Phiếu vẫn hợp lệ cho 1 hộp; từ chối hết khiến khách về tay không.',
                          refer='Cô Thu giải thích giúp và giao đúng 1 hộp theo phiếu.'))


def ph_norx(r, day, tr, b):
    who = r.choice([3, 6])
    ask = D('ask', 'Khách nói', '💬', [F('want', 'Cần mua', 'Kháng Lam 250 · 1 hộp'), F('slip', 'Phiếu', 'Không có phiếu'),
                                      F('why', 'Lý do', 'Nhà có người ho mấy hôm, mua sẵn cho chắc')])
    return dict(npc=who, title='Xin một hộp, không phiếu', opening='Bạn ơi, bán giúp một hộp Kháng Lam thôi, lần trước nhà mình cũng dùng mà.',
                request='Không có phiếu đâu, bạn thông cảm, mình gửi thêm tiền uống nước nhé.',
                docs=[ask, _tray(r, b, 'kl250', 1)], checks=[], verdicts=verdicts('pharmacy', PH_STD),
                issues=[I('rx', ['ask.slip'], 'ph_rx', 'Kháng Lam thuộc nhóm K, cần phiếu của phòng khám.')],
                accept={'refuse': 'best', 'refer': 'ok'}, needs=[], risk={'give': 3, 'fix': 3}, tip={'give': 10, 'fix': 10}, pleases=['give', 'fix'],
                says=dict(give='Khách vui vẻ dúi thêm 10 xu. Nhưng một hộp nhóm K đã ra khỏi quầy không có phiếu, cô Thu ghi lỗi.',
                          fix='Không có phiếu thì chẳng có gì để “đổi cho đúng”. Hộp nhóm K vẫn ra khỏi quầy.',
                          refuse='Bạn nói nhẹ nhàng rằng nhóm này cần phiếu và chỉ phòng khám gần nhất. Khách đi khám, chiều quay lại có phiếu.',
                          refer='Cô Thu nói chuyện với khách và hẹn giờ khám ở phòng khám đầu phố.'))


def ph_recall(r, day, tr, b):
    lot = b['recall'][0]
    code = lot.split('-')[0]
    drug = next(k for k, v in DRUGS.items() if v['code'] == code)
    need_slip = DRUGS[drug]['group'] in ('K', 'L')
    docs = [_slip(r, day, b, drug, 1) if need_slip else D('ask', 'Khách nói', '💬', [F('want', 'Cần mua', f'{DRUGS[drug]["name"]} · 1 hộp')]),
            _tray(r, b, drug, 1, lot=lot)]
    checks, needs = [], []
    if drug == 'tuyet':
        docs.append(_fridge(False, r))
        checks.append(C('fridge', 'Xem nhật ký tủ mát', '🌡️'))
    return dict(npc=4, title='Số lô nghe quen quen', opening='Khay xong rồi đó, bạn giao giúp mình để mình ra nhận hàng nhé.',
                request='Khoa: “Hộp này mình lấy ở hàng đầu kệ, tiện tay nhất.”',
                docs=docs, checks=checks, verdicts=verdicts('pharmacy', PH_STD),
                issues=[I('recall', ['tray.lot'], 'ph_recall', f'Lô {lot} nằm trong danh sách thu hồi hôm nay.')],
                accept={'fix': 'best', 'refer': 'ok'}, needs=needs, risk={'give': 3}, pleases=['give'],
                says=dict(give=f'Một hộp thuộc lô {lot} đã ra khỏi quầy dù đang bị thu hồi. Cô Thu phải gọi khách mang trả.',
                          fix=f'Bạn đổi sang lô khác và dán nhãn “Thu hồi” lên các hộp lô {lot} ở đầu kệ.',
                          refuse='Khách vẫn mua được đúng thứ cần ở lô khác; từ chối làm khách về tay không.',
                          refer=f'Cô Thu đổi hộp và kéo cả hàng lô {lot} xuống khu tạm giữ.'))


def ph_cold(r, day, tr, b):
    return dict(npc=r.choice([3, 2]), title='Tủ mát chập chờn', opening='Mình lấy lọ Tuyết Lạnh theo phiếu, trưa nay nghe nói cúp điện một lúc.',
                request='Bạn lấy giúp mình một lọ nhé, nhà mình cần trong tối nay.',
                docs=[_slip(r, day, b, 'tuyet', 1), _tray(r, b, 'tuyet', 1), _fridge(True, r)],
                checks=[C('fridge', 'Xem nhật ký tủ mát', '🌡️')], verdicts=verdicts('pharmacy', PH_STD),
                issues=[I('cold', ['fridge.t12'], 'ph_cold', 'Nhật ký ghi 12 giờ tủ mát lên quá 8°C.')],
                accept={'refer': 'best', 'refuse': 'ok'}, needs=['fridge'], risk={'give': 3, 'fix': 3}, pleases=['give', 'fix'],
                says=dict(give='Lọ hàng lạnh đã giao dù tủ mát vượt ngưỡng lúc trưa. Cô Thu ghi lỗi và gọi khách.',
                          fix='Cả tủ cùng một nhật ký, đổi lọ khác không giải quyết được.',
                          refuse='Bạn giải thích lọ trong tủ cần kiểm lại và mời khách ghé mai. Khách lo nhưng hiểu.',
                          refer='Cô Thu tách cả khay trong tủ ra kiểm, gọi kho giao lọ mới cho khách ngay chiều nay.'))


def ph_proxy(r, day, tr, b):
    ok = r.random() < 0.5
    drug = r.choice(['kl250', 'dh'])
    if ok:
        slip = _slip(r, day, b, drug, 1, patient='Bà Hòa', pickup='Lan (con gái)')
        return dict(npc=3, title='Lấy thuốc cho mẹ', opening='Mình lấy thuốc cho mẹ mình, phiếu có ghi tên mình đó.',
                    request='Mẹ mình không đi được, mình nhận thay nhé.',
                    docs=[slip, _tray(r, b, drug, 1)], checks=[], verdicts=verdicts('pharmacy', PH_STD), issues=[],
                    accept={'give': 'best'}, needs=[], risk={}, pleases=['give'],
                    says=dict(give='Phiếu ghi Lan nhận thay nên bạn giao đúng người. Lan cảm ơn rối rít.',
                              fix='Không có gì cần đổi; Lan chờ thêm một lúc.',
                              refuse='Phiếu đã ghi Lan nhận thay mà vẫn bị từ chối. Lan phải gọi phòng khám hỏi lại.',
                              refer='Cô Thu nhìn dòng nhận thay rồi bảo: “Đủ rồi, cháu giao đi.”'))
    slip = _slip(r, day, b, drug, 1, patient='Ông Khải', pickup='Chị Duyên (con dâu)')
    return dict(npc=6, title='Lấy giúp hàng xóm', opening='Mình lấy thuốc giúp ông Khải hàng xóm, ông nhờ mình đó.',
                request='Ông ở một mình, mình tiện đường nên lấy giúp thôi.',
                docs=[slip, _tray(r, b, drug, 1), D('ask', 'Người nhận', '🪪', [F('who', 'Người đứng quầy', 'Vy (hàng xóm)')])],
                checks=[], verdicts=verdicts('pharmacy', PH_STD),
                issues=[I('person', ['ask.who', 'slip.pickup'], 'ph_person', 'Phiếu ghi chị Duyên nhận thay; người đứng quầy là Vy.')],
                accept={'refer': 'best', 'refuse': 'ok'}, needs=[], risk={'give': 1}, pleases=['give'],
                says=dict(give='Thuốc nhóm K đã giao cho người không có tên trên phiếu. Cô Thu ghi một lỗi.',
                          fix='Đổi hộp không làm Vy thành người nhận thay.',
                          refuse='Bạn giải thích nhẹ nhàng; Vy gọi chị Duyên ghé lấy sau.',
                          refer='Cô Thu gọi số trên phiếu: ông Khải nhờ thật, cô ghi thêm tên Vy vào dòng nhận thay rồi giao.'))


def ph_supplier(r, day, tr, b):
    legit = r.random() < 0.35
    if legit:
        docs = [D('offer', 'Lô chào hàng', '📦', [F('item', 'Hàng', 'Kháng Lam 250 · 20 hộp'), F('price', 'Giá', '29 xu/hộp (giá thường 30)'),
                                                F('seal', 'Tem', 'Tem mới, có sợi bạc 🧵')]),
                D('invoice', 'Hóa đơn', '🧾', [F('tax', 'Mã số thuế', '0312-448-209'), F('from', 'Bên bán', 'Công ty Minh Phát')])]
        return dict(npc=5, title='Lô hàng tuần này', opening='Hàng tuần này đây, bạn kiểm giúp mình để còn kịp chuyến sau.',
                    request='Hóa đơn với tem mới đầy đủ nhé.',
                    docs=docs, checks=[], verdicts=verdicts('pharmacy', ['accept', 'refuse', 'refer']), issues=[],
                    accept={'accept': 'best', 'refer': 'ok'}, needs=[], risk={}, pleases=['accept'],
                    says=dict(accept='Hóa đơn và tem đều đúng. Kệ nhóm K có hàng cho cả tuần.',
                              refuse='Lô hợp lệ bị trả về; tuần này kệ Kháng Lam sẽ hụt hàng.',
                              refer='Cô Thu xem lại, gật đầu nhận lô và nhắc lần sau quầy tự quyết được.'))
    docs = [D('offer', 'Lô chào hàng', '📦', [F('item', 'Hàng', 'Kháng Lam 250 · 40 hộp'), F('price', 'Giá', '18 xu/hộp (giá thường 30)'),
                                            F('seal', 'Tem', 'Tem in phẳng, không thấy sợi bạc')]),
            D('invoice', 'Hóa đơn', '🧾', [F('tax', 'Mã số thuế', '(để trống)'), F('from', 'Bên bán', 'Mối mới, chỉ có số điện thoại')])]
    return dict(npc=5, title='Hàng rẻ bất ngờ', opening='Có mối mới chào Kháng Lam rẻ lắm, mình mang mẫu qua bạn xem thử.',
                request='Rẻ gần một nửa đó, nhận thì tuần này tiệm lời to.',
                docs=docs, checks=[], verdicts=verdicts('pharmacy', ['accept', 'refuse', 'refer']),
                issues=[I('seal', ['offer.seal'], 'ph_supply', 'Tem không có sợi bạc như mẫu mới.'),
                        I('tax', ['invoice.tax'], 'ph_supply', 'Hóa đơn không ghi mã số thuế.')],
                accept={'refer': 'best', 'refuse': 'ok'}, needs=[], risk={'accept': 4}, pleases=['accept'],
                says=dict(accept='Bốn mươi hộp không rõ nguồn đã lên kệ. Cô Thu phát hiện tem lạ, cả lô phải tách ra tạm giữ.',
                          refuse='Bạn cảm ơn Minh và từ chối lô này. Minh cũng thấy nhẹ người.',
                          refer='Cô Thu giữ mẫu tem, báo cho nhà cung cấp chính thức và khu phố. Minh được cảm ơn vì đã mang qua hỏi.'))


def ph_inspect(r, day, tr, b):
    rows = [F('r1', '09:10 · Kháng Lam 250', 'Phiếu PK-' + str(r.randint(401, 989))),
            F('r2', '10:25 · Lọ Tuyết Lạnh', 'Phiếu PK-' + str(r.randint(401, 989))),
            F('r3', '11:40 · Viên Điều Hòa Mây', '(chưa ghi số phiếu)'),
            F('r4', '14:05 · Siro Mây Tâm', 'Hàng thông thường')]
    fr = [F('t8', '8 giờ', '5°C · đã ký'), F('t12', '12 giờ', '6°C · đã ký'), F('t15', '15 giờ', '(chưa ghi)')]
    issues = [I('book', ['book.r3'], 'ph_log', 'Dòng 11:40 giao thuốc nhóm K nhưng chưa ghi số phiếu.')]
    if tr >= 2:
        issues.append(I('fridge', ['fridge.t15'], 'ph_log', 'Nhật ký tủ mát còn trống mốc 15 giờ.'))
    return dict(npc=1, title='Đoàn kiểm tra ghé quầy', opening='Đoàn kiểm tra tới rồi. Mình cùng trình sổ nhé, có gì thiếu thì nhận và sửa ngay.',
                request='Đoàn xin xem sổ bán nhóm K và nhật ký tủ mát hôm nay.',
                docs=[D('book', 'Sổ bán nhóm K', '📓', rows), D('fridge', 'Nhật ký tủ mát', '🌡️', fr)], checks=[],
                verdicts=verdicts('pharmacy', ['own', 'excuse', 'refer']), issues=issues,
                accept={'own': 'best', 'refer': 'ok'}, needs=[], risk={'excuse': 2}, pleases=[],
                says=dict(own='Bạn chỉ ra chỗ thiếu trước khi đoàn hỏi và bổ sung ngay. Đoàn ghi “quầy tự phát hiện”.',
                          excuse='Đoàn không chấp nhận lời giải thích, ghi biên bản nhắc nhở.',
                          refer='Cô Thu trình sổ cùng đoàn và nhận bổ sung các dòng còn thiếu.'))


def ph_story(r, day, tr, b, chapter):
    if chapter == 1:
        docs = [_slip(r, day, b, 'dh', 1, patient='Bác Năm'), _tray(r, b, 'dh', 1),
                D('home', 'Bác kể', '🏠', [F('mix', 'Ở nhà', 'Sáng với tối bác hay cầm nhầm hai hộp trắng giống nhau'),
                                           F('label', 'Nhãn to', 'Đã dán nhãn SÁNG ☀ / TỐI 🌙 chữ thật to', hidden='label')])]
        return dict(npc=2, title='Hai hộp trắng giống nhau', opening='Cháu ơi, hộp nào cũng trắng, bác cứ cầm nhầm sáng với tối hoài.',
                    request='Bác lấy hộp như phiếu, cháu làm sao cho bác dễ nhìn giúp bác nhé.',
                    docs=docs, checks=[C('label', 'Dán nhãn chữ to cho bác', '🏷️')], verdicts=verdicts('pharmacy', PH_STD), issues=[],
                    accept={'give': 'best', 'refer': 'ok'}, needs=['label'], risk={}, pleases=['give', 'refer'],
                    says=dict(give='Bác Năm cầm hộp lên soi nhãn, cười tít mắt: “Vậy là hết nhầm rồi.”',
                              fix='Hộp vốn đã đúng phiếu; bác chờ thêm và hơi lo.',
                              refuse='Phiếu của bác vẫn hợp lệ; bác về mà buồn thiu.',
                              refer='Cô Thu cùng bác xếp lại giờ dùng trên một tờ lịch nhỏ.'))
    if chapter == 2:
        docs = [D('strip', 'Vỉ bác mang tới', '💊', [F('name', 'Tên trên vỉ', '(mất nhãn, chỉ còn vỉ lẻ)'), F('lot', 'Số lô', '(không rõ)'),
                                                     F('want', 'Bác muốn', 'Thêm hai vỉ giống vầy')]),
                D('home', 'Lần trước', '🏠', [F('note', 'Nhãn to', 'Bác bảo nhãn to dễ đọc lắm, nhưng lỡ đánh rơi hộp')])]
        return dict(npc=2, title='Vỉ thuốc lẻ không nhãn', opening='Cháu ơi, hộp bác rơi mất, còn cái vỉ này. Bán bác thêm hai vỉ giống vầy nhé.',
                    request='Vỉ này đây, cháu nhìn là biết mà.',
                    docs=docs, checks=[], verdicts=verdicts('pharmacy', PH_STD),
                    issues=[I('label', ['strip.name', 'strip.lot'], 'ph_label', 'Vỉ lẻ đã mất nhãn, không rõ tên và lô.')],
                    accept={'refer': 'best', 'refuse': 'ok'}, needs=[], risk={'give': 2, 'fix': 2}, pleases=['give', 'fix'],
                    says=dict(give='Bạn đoán theo hình vỉ mà giao. Cô Thu thấy, ghi lỗi và gọi bác quay lại đối chiếu.',
                              fix='Không biết vỉ là gì thì không đổi “cho đúng” được.',
                              refuse='Bạn giải thích nhẹ nhàng; bác hơi buồn nhưng hứa mang phiếu cũ tới.',
                              refer='Cô Thu tra lại phiếu cũ của bác trong sổ, giao hộp mới đủ nhãn và dán lại chữ to.'))
    if chapter == 3:
        docs = [_slip(r, day, b, 'dh', 1, clinic='ak', patient='Bác Năm'),
                D('home', 'Thuốc bác đang dùng', '🏠', [F('list', 'Hộp ở nhà', 'Viên Điều Hòa Mây · PK Hạnh Phúc'), F('since', 'Từ', 'Ba tuần nay')]),
                _tray(r, b, 'dh', 1)]
        return dict(npc=2, title='Phiếu mới, thuốc quen', opening='Bác mới khám thêm chỗ khác, người ta cũng cho thuốc. Cháu lấy giúp bác.',
                    request='Hai phòng khám, hai tờ phiếu, bác cứ lấy đủ cả hai cho chắc.',
                    docs=docs, checks=[], verdicts=verdicts('pharmacy', PH_STD),
                    issues=[I('dup', ['slip.drug', 'home.list'], 'ph_dup', 'Phiếu mới có đúng loại thuốc bác đang dùng từ phòng khám khác.')],
                    accept={'refer': 'best', 'refuse': 'ok'}, needs=[], risk={'give': 2}, pleases=['give'],
                    says=dict(give='Bác mang về thêm một hộp trùng với hộp đang dùng. Cô Thu biết chuyện thì gọi ngay cho bác.',
                              fix='Hộp trên khay đúng phiếu; vấn đề là trùng với thuốc bác đang dùng.',
                              refuse='Bạn chưa giao và dặn bác hỏi lại phòng khám. Bác hơi rối nhưng yên tâm.',
                              refer='Cô Thu gọi cả hai phòng khám, ghi rõ trên phiếu và dặn bác chỉ dùng một hộp.'))
    docs = [_slip(r, day, b, 'dh', 1, patient='Bác Năm'), _tray(r, b, 'dh', 1),
            D('card', 'Tấm thiệp', '💌', [F('text', 'Bác viết', 'Cảm ơn quầy đã chậm lại một nhịp cùng bác.')])]
    return dict(npc=2, title='Tấm thiệp của bác Năm', opening='Hôm nay bác lấy thuốc như mọi khi, còn cái này là bác gửi quầy.',
                request='Phiếu đây cháu, không gấp gì đâu.',
                docs=docs, checks=[], verdicts=verdicts('pharmacy', PH_STD), issues=[],
                accept={'give': 'best'}, needs=[], risk={}, pleases=['give'],
                says=dict(give='Bác Năm dựng tấm thiệp cạnh quầy. Từ nay nó là món trang trí bạn thích nhất.',
                          fix='Không có gì cần đổi; bác chờ thêm một lúc.',
                          refuse='Phiếu hợp lệ mà bị từ chối, bác ngạc nhiên lắm.',
                          refer='Cô Thu bảo: “Phiếu đủ cả, cháu giao cho bác đi.”'))


# ---------------------------------------------------------------- accounting cases
EXPENSES = [('Mua bột', 120), ('Tiền điện', 180), ('Giấy in', 40), ('Túi giấy', 60), ('Ga nấu', 150), ('Tiền nước', 70), ('Bơ và sữa', 210)]
SALES = [('Bán hàng tiền mặt', 240), ('Bán hàng chuyển khoản', 310), ('Bán bánh đặt trước', 180)]


def _rows(r, day, n):
    start, _ = period(day)
    picks = r.sample(EXPENSES, n)
    rows = []
    for i, (text, base) in enumerate(picks):
        amount = base + r.choice([0, 10, 20]) + (day // 3) * 5
        ref = f'HĐ {r.randint(201, 399)}'
        when = r.randint(start, day)
        rows.append(dict(id=f'L{i + 1}', day=when, text=text, amount=-amount, ref=ref))
    return rows


def _ledger(rows, title='Sổ chi của tiệm'):
    return D('ledger', title, '📒', [F(x['id'], f'Ngày {x["day"]} · {x["text"]}' + (f' · {x["ref"]}' if x.get('ref') else ''), xu(x['amount'])) for x in rows], kind='table')


def _bills(rows, skip=(), overrides=None):
    overrides = overrides or {}
    fields = []
    for i, x in enumerate(rows):
        if x['id'] in skip or not x.get('ref'):
            continue
        amount = overrides.get(x['id'], x['amount'])
        fields.append(F(f'H{i + 1}', f'{x["ref"]} · {x["text"]}', xu(amount)))
    return D('bills', 'Hóa đơn gốc', '🧾', fields, kind='table')


AC_STD = ['post', 'adjust', 'hold', 'report']


def ac_clean(r, day, tr, b):
    rows = _rows(r, day, 3)
    fee = b['fee']
    rows.append(dict(id='L4', day=day, text='Phí chuyển khoản', amount=-fee, ref=None))
    return dict(npc=r.choice([1, 3]), title='Sổ tuần gọn gàng', opening='Bạn soát giúp sổ chi tuần này nhé, mình thấy ổn rồi nhưng vẫn muốn chắc.',
                request='Đủ hóa đơn trong bìa kẹp đó bạn.',
                docs=[_ledger(rows), _bills(rows)], checks=[], verdicts=verdicts('accounting', AC_STD), issues=[],
                accept={'post': 'best'}, needs=[], risk={}, pleases=['post'],
                says=dict(post='Mọi dòng đều có hóa đơn, phí chuyển khoản ghi riêng đúng mức. Sổ được chốt gọn.',
                          adjust='Bạn sửa một dòng vốn đã đúng; chị Vân phải gỡ lại chỗ sửa.',
                          hold='Sổ đủ chứng từ mà vẫn bị giữ lại; người gửi phải chờ thêm một ngày.',
                          report='Chị Vân xem rồi bảo sổ ổn, lần sau cứ tự chốt.'))


def ac_dup(r, day, tr, b):
    rows = _rows(r, day, 3)
    dup = dict(rows[1], id='L4')
    rows.append(dup)
    return dict(npc=1, title='Có một khoản ghi hai lần', opening='Tổng chi tuần này cao hơn mình nghĩ, bạn xem giúp mình với.',
                request='Mình nhập theo xấp hóa đơn, có tờ photo nữa.',
                docs=[_ledger(rows), _bills(rows[:3])], checks=[], verdicts=verdicts('accounting', AC_STD),
                issues=[I('dup', ['ledger.L2', 'ledger.L4'], 'ac_once', f'{rows[1]["ref"]} được ghi hai lần: một từ bản gốc, một từ bản photo.')],
                accept={'adjust': 'best', 'hold': 'ok'}, needs=[], risk={'post': 1}, pleases=[],
                says=dict(post='Sổ chốt với một khoản bị ghi hai lần; chi phí tuần này bị đội lên.',
                          adjust='Bạn gạch dòng trùng và ghi chú “bản photo của cùng hóa đơn”. Huy gật gù.',
                          hold='Bạn giữ sổ lại hỏi Huy; mất thêm một nhịp nhưng không sai.',
                          report='Chị Vân chỉ ra dòng trùng và hỏi sao bạn không tự sửa.'))


def ac_typo(r, day, tr, b):
    rows = _rows(r, day, 4)
    i = r.randrange(4)
    real = -rows[i]['amount']
    wrong = int(str(real)[::-1]) if str(real)[::-1] != str(real) and not str(real).endswith('0') else real + 90
    bills = _bills(rows)
    rows[i] = dict(rows[i], amount=-wrong)
    return dict(npc=1, title='Một chữ số đi lạc', opening='Mình cộng mãi không ra tổng như trong bìa hóa đơn. Bạn soát giúp nhé.',
                request='Mình gõ hơi nhanh, chắc lỗi đâu đó thôi.',
                docs=[_ledger(rows), bills], checks=[], verdicts=verdicts('accounting', AC_STD),
                issues=[I('amount', [f'ledger.L{i + 1}', f'bills.H{i + 1}'], 'ac_amount', f'Sổ ghi {wrong} xu nhưng hóa đơn {rows[i]["ref"]} là {real} xu.')],
                accept={'adjust': 'best', 'hold': 'ok'}, needs=[], risk={'post': 1}, pleases=[],
                says=dict(post='Sổ chốt với một số gõ nhầm; cuối kỳ tổng chi không khớp hóa đơn.',
                          adjust='Bạn sửa theo hóa đơn gốc và ghi lý do. Huy dán tờ nhắc “đọc lại số” lên màn hình.',
                          hold='Bạn trả sổ cho Huy tự sửa; mất thêm một nhịp.',
                          report='Chị Vân chỉ ra dòng gõ nhầm, bảo lần sau bạn cứ sửa kèm lý do.'))


def ac_missing(r, day, tr, b):
    rows = _rows(r, day, 3)
    rows.append(dict(id='L4', day=day, text='Sửa quạt', amount=-(90 + tr * 10), ref=None))
    return dict(npc=4, title='Khoản chi không có giấy', opening='Mình gửi bảng kê tuần này, hóa đơn thì… để đâu đó trong ba lô.',
                request='Sửa quạt là có thật mà, thợ không đưa giấy thôi.',
                docs=[_ledger(rows), _bills(rows)], checks=[], verdicts=verdicts('accounting', AC_STD),
                issues=[I('source', ['ledger.L4'], 'ac_source', 'Khoản sửa quạt chưa có hóa đơn hay phiếu chi nào.')],
                accept={'hold': 'best', 'report': 'ok'}, needs=[], risk={'post': 1}, pleases=['post'],
                says=dict(post='Một khoản chi không chứng từ đã vào sổ. Kiểm tra cuối kỳ sẽ hỏi lại.',
                          adjust='Xóa dòng làm mất dấu một khoản chi có thật; Nam phải kể lại từ đầu.',
                          hold='Bạn nhờ Nam xin thợ phiếu thu. Chiều đó Nam mang tới một tờ viết tay có chữ ký.',
                          report='Chị Vân nhắc Nam bổ sung phiếu thu, sổ chờ tới lúc có giấy.'))


def ac_fee(r, day, tr, b):
    rows = _rows(r, day, 3)
    fee = b['fee']
    bank = D('bank', 'Sao kê ngân hàng', '🏦', [F('B1', f'Chuyển trả {rows[0]["ref"]}', xu(rows[0]['amount'])),
                                               F('B2', 'Phí chuyển khoản', xu(-fee)),
                                               F('B3', f'Chuyển trả {rows[2]["ref"]}', xu(rows[2]['amount'])),
                                               F('B4', 'Phí chuyển khoản', xu(-fee))], kind='table')
    return dict(npc=r.choice([3, 4]), title=f'Sao kê lệch {fee * 2} xu', opening='Sao kê với sổ lệch nhau một chút xíu, chắc ngân hàng tính nhầm?',
                request='Có mấy chục xu thôi mà, bạn cứ chốt cho nhanh nhé.',
                docs=[_ledger(rows), bank], checks=[], verdicts=verdicts('accounting', AC_STD),
                issues=[I('fee', ['bank.B2', 'bank.B4'], 'ac_fee', f'Sao kê có hai lần phí chuyển khoản {fee} xu chưa ghi vào sổ.')],
                accept={'adjust': 'best', 'hold': 'ok'}, needs=[], risk={'post': 1}, pleases=['post'],
                says=dict(post='Sổ chốt thiếu hai dòng phí; cuối kỳ két và ngân hàng lệch nhau.',
                          adjust=f'Bạn ghi thêm hai dòng phí {fee} xu. Sổ và sao kê khớp nhau tới từng xu.',
                          hold='Bạn giữ lại để hỏi thêm; phí vẫn nằm đó chờ ghi.',
                          report='Chị Vân chỉ hai dòng phí và nhắc bản tin hôm nay.'))


def _drawer(r, tr, fake):
    counts = {50: r.randint(1, 3), 20: r.randint(1, 4), 10: r.randint(1, 4), 5: r.randint(0, 3)}
    notes = []
    for v, n in counts.items():
        notes += [dict(v=v, thread=True) for _ in range(n)]
    total = sum(v * n for v, n in counts.items())
    if fake:
        notes.append(dict(v=50, thread=False))
    r.shuffle(notes)
    for i, x in enumerate(notes):
        x['id'] = f'n{i + 1}'
    return notes, total


def ac_cash(r, day, tr, b, owner=5, clean=None):
    fake = tr >= 3 and 'ac_fake' in [x['id'] for x in b['rules']] and r.random() < 0.5
    short = 0 if (clean if clean is not None else r.random() < 0.3) else r.choice([5, 10, 15, 20])
    if clean:
        fake = False
    notes, total = _drawer(r, tr, fake)
    book = D('cashbook', 'Sổ quỹ', '📘', [F('open', 'Đầu ca', xu(40)), F('in', 'Thu tiền mặt', xu(total + short - 40)),
                                          F('balance', 'Số dư cuối ca', f'{total + short} xu')])
    fields = [F('count', 'Số bạn đếm được', f'{total} xu', hidden='count')]
    if fake:
        fields.append(F('fake', 'Một tờ 50 xu', 'Không thấy sợi bạc 🧵'))
    drawer = D('drawer', 'Két tiền', '💵', fields, kind='drawer')
    issues = []
    if short:
        issues.append(I('cash', ['drawer.count', 'cashbook.balance'], 'ac_cash', f'Két có {total} xu, sổ quỹ ghi {total + short} xu: lệch {short} xu.'))
    if fake:
        issues.append(I('fake', ['drawer.fake'], 'ac_fake', 'Một tờ 50 xu không có sợi bạc, phải tách riêng.'))
    bad = bool(issues)
    who = owner
    return dict(npc=who, title='Đếm két cuối ca' if who == 5 else 'Két của quầy mới',
                opening='Cuối ca rồi, bạn đếm két cùng mình rồi ký sổ quỹ nhé.' if who == 5 else 'Quầy mới của cô chạy ngày đầu, cháu đếm két giúp cô nhé.',
                request='Tiền trong két đây, bạn đếm từng tờ nhé.',
                docs=[book, drawer], checks=[C('count', 'Đếm két', '🧮')],
                verdicts=verdicts('accounting', ['close', 'minutes', 'cover', 'force']), issues=issues,
                accept={'minutes': 'best'} if bad else {'close': 'best'}, needs=['count'],
                risk={'force': 2, 'close': 1} if bad else {'force': 1}, pleases=['close', 'cover'],
                cover=short, cash=total, notes=notes,
                says=dict(close='Két khớp sổ quỹ tới từng xu. Bạn ký sổ, Lộc khóa két.' if not bad else 'Sổ quỹ chốt dù két không khớp; ca sau sẽ nhận một chỗ lệch không tên.',
                          minutes='Bạn lập biên bản ghi rõ số lệch và tờ tiền lạ (nếu có). Lộc thở phào vì không ai phải đoán.' if bad else 'Không có gì lệch mà vẫn lập biên bản; mọi người ký cho xong.',
                          cover='Bạn bỏ tiền túi bù vào két. Sổ đẹp, nhưng chẳng ai biết tiền lệch từ đâu.' if bad else 'Không thiếu gì để bù.',
                          force='Sửa số dư cho khớp két là xóa dấu vết. Chị Trâm sẽ hỏi.'))


def ac_private(r, day, tr, b):
    rows = _rows(r, day, 3)
    rows.append(dict(id='L4', day=day, text='Cước điện thoại nhà riêng', amount=-(60 + tr * 5), ref=f'HĐ {r.randint(401, 499)}'))
    return dict(npc=1, title='Hóa đơn lạc vào sổ tiệm', opening='Mình nhập theo túi hóa đơn cô Hoa đưa, có gì bạn soát giúp nhé.',
                request='Túi đó cô Hoa gom cả hóa đơn nhà với tiệm.',
                docs=[_ledger(rows), _bills(rows)], checks=[], verdicts=verdicts('accounting', AC_STD),
                issues=[I('private', ['ledger.L4', 'bills.H4'], 'ac_private', 'Cước điện thoại nhà riêng không phải chi phí của tiệm.')],
                accept={'adjust': 'best', 'hold': 'ok'}, needs=[], risk={'post': 1}, pleases=['post'],
                says=dict(post='Chi phí tiệm bị lẫn cước nhà riêng; lợi nhuận tuần này trông thấp hơn thật.',
                          adjust='Bạn tách dòng cước nhà ra và trả hóa đơn cho cô Hoa giữ riêng.',
                          hold='Bạn gửi hỏi lại cô Hoa; mất thêm một nhịp.',
                          report='Chị Vân chỉ dòng cước nhà và nhắc Huy tách túi hóa đơn.'))


def ac_deposit(r, day, tr, b):
    rows = _rows(r, day, 2)
    dep = 200 + tr * 20
    rows.append(dict(id='L3', day=day, text='Doanh thu: cọc tiệc cưới', amount=dep, ref='Phiếu thu 17'))
    rows.append(dict(id='L4', day=day, text='Bán hàng tiền mặt', amount=240 + day * 5, ref='Sổ bán'))
    return dict(npc=3, title='Tuần này bán đắt ghê', opening='Tuần này tiệm cô bán được nhiều quá, cháu xem sổ giúp cô.',
                request='Có cả tiền cọc tiệc cưới cuối tháng nữa đó.',
                docs=[_ledger(rows, 'Sổ thu chi'), D('receipt', 'Phiếu thu 17', '🧾', [F('what', 'Nội dung', 'Cọc giữ chỗ tiệc cưới ngày 30'),
                                                                                    F('amount', 'Số tiền', xu(dep))])],
                checks=[], verdicts=verdicts('accounting', AC_STD),
                issues=[I('deposit', ['ledger.L3', 'receipt.what'], 'ac_deposit', 'Tiền cọc tiệc cưới đang ghi là doanh thu.')],
                accept={'adjust': 'best', 'hold': 'ok'}, needs=[], risk={'post': 1}, pleases=['post'],
                says=dict(post='Cọc giữ chỗ bị tính thành doanh thu; tuần sau tiệc diễn ra thì sổ ghi hai lần.',
                          adjust='Bạn chuyển khoản cọc sang “nhận trước”. Cô Hoa hiểu vì sao tuần này không “lời” như cô tưởng.',
                          hold='Bạn hỏi thêm cô Hoa về tiệc cưới; mất thêm một nhịp.',
                          report='Chị Vân chỉ ra khoản cọc và nhắc quy tắc.'))


def ac_period(r, day, tr, b, closing=False):
    start, end = b['period']
    rows = _rows(r, day, 3)
    nxt = end + 1
    rows.append(dict(id='L4', day=nxt, text='Tiền thuê kỳ sau', amount=-(300 + tr * 20), ref=f'HĐ {r.randint(401, 499)}'))
    issues = [I('period', ['ledger.L4'], 'ac_period', f'Tiền thuê ngày {nxt} thuộc kỳ sau, không thuộc kỳ {start}–{end}.')]
    docs = [_ledger(rows, f'Sổ chi kỳ {start}–{end}'), _bills(rows)]
    if closing and tr >= 2:
        fee = b['fee']
        docs.append(D('bank', 'Sao kê ngân hàng', '🏦', [F('B1', f'Chuyển trả {rows[0]["ref"]}', xu(rows[0]['amount'])),
                                                        F('B2', 'Phí chuyển khoản', xu(-fee))], kind='table'))
        issues.append(I('fee', ['bank.B2'], 'ac_fee', f'Phí chuyển khoản {fee} xu chưa có trong sổ.'))
    return dict(npc=2 if closing else 4, title='Khóa sổ cuối kỳ' if closing else 'Khoản chi đi trước',
                opening='Cuối kỳ rồi, soát kỹ giúp chị trước khi khóa sổ nhé.' if closing else 'Mình trả trước tiền thuê cho chủ nhà, ghi luôn vào sổ rồi đó.',
                request='Khóa rồi là không mở lại được đâu.' if closing else 'Trả rồi thì ghi luôn cho khỏi quên.',
                docs=docs, checks=[], verdicts=verdicts('accounting', AC_STD), issues=issues,
                accept={'adjust': 'best', 'hold': 'ok'}, needs=[], risk={'post': 2 if closing else 1}, pleases=['post'],
                says=dict(post='Kỳ này bị gánh một khoản của kỳ sau; báo cáo tuần trông lỗ hơn thực tế.',
                          adjust='Bạn chuyển khoản thuê sang kỳ sau và ghi chú. Kỳ này khép lại đúng số.',
                          hold='Bạn giữ sổ chưa khóa để hỏi thêm; kịp giờ nhưng hơi sát.',
                          report='Chị Vân chỉ ra khoản của kỳ sau và bảo bạn tự điều chỉnh được.'))


def ac_payee(r, day, tr, b):
    legit = tr >= 3 and r.random() < 0.3
    amount = 350 + tr * 20
    vendor = D('vendor', 'Hồ sơ nhà cung cấp', '📇', [F('mail', 'Thư điện tử', 'ketoan@luavang.vn'), F('account', 'Tài khoản', 'Mây Bank · 0123 88 (đã xác minh)'),
                                                    F('reply', 'Gọi số trong hồ sơ', 'Lúa Vàng: “Đúng rồi, bên mình vừa đổi ngân hàng, thư có dấu gửi kèm.”' if legit else 'Lúa Vàng: “Bên mình không đổi tài khoản nào cả!”', hidden='call')])
    mail = D('mail', 'Thư điện tử mới', '✉️', [F('from', 'Người gửi', 'ketoan@luavang.vn' if legit else 'ketoan@luavang-pay.vn'),
                                             F('account', 'Tài khoản mới', 'Lá Bank · 7788 12'), F('amount', 'Số tiền', f'{amount} xu · HĐ 311'),
                                             F('urgent', 'Lời nhắn', 'Có thư đóng dấu gửi kèm.' if legit else 'Chuyển trước 11 giờ kẻo bị phạt chậm!')])
    issues = [] if legit else [I('payee', ['mail.from', 'mail.account', 'mail.urgent'], 'ac_payee', 'Thư đổi tài khoản từ địa chỉ lạ, giục chuyển gấp; hồ sơ không có tài khoản này.')]
    return dict(npc=4, title='Thư đổi số tài khoản', opening='Lúa Vàng vừa gửi thư đổi tài khoản, mình chuyển luôn cho kịp giờ nhé?',
                request='Thư ghi gấp lắm, trước 11 giờ đó bạn.',
                docs=[mail, vendor], checks=[C('call', 'Gọi số trong hồ sơ', '📞')],
                verdicts=verdicts('accounting', ['pay', 'hold', 'report']), issues=issues,
                accept={'pay': 'best', 'hold': 'ok'} if legit else {'hold': 'best', 'report': 'ok'},
                requires={'pay': 'call'} if legit else {}, needs=['call'], risk={} if legit else {'pay': 3}, pleases=['pay'],
                says_blind=dict(pay='Tiền tới đúng chỗ, nhưng bạn chuyển khi chưa gọi xác minh. Chị Vân nhắc: thư giả cũng trông y như vậy.'),
                says=dict(pay='Tiền đã tới đúng tài khoản mới đã xác minh. Lúa Vàng cảm ơn vì trả đúng hẹn.' if legit else f'{amount} xu đã chuyển tới một tài khoản lạ. Lúa Vàng gọi hỏi tiền hàng: đây là thư giả.',
                          hold='Bạn gọi số cũ xác minh rồi mới chuyển. Chậm một chút nhưng chắc.' if legit else 'Bạn giữ lệnh chi và gọi số trong hồ sơ: thư giả bị lộ, tiền còn nguyên.',
                          report='Chị Vân cùng kiểm và chuyển khoản sau khi gọi xác nhận.' if legit else 'Chị Vân báo cả nhóm cảnh giác với thư giả mạo Lúa Vàng.'))


def ac_supplier(r, day, tr, b):
    dup = r.random() < 0.6
    amount = 260 + tr * 10
    b2, b4 = 'HĐ 311', 'HĐ 311' if dup else 'HĐ 318'
    bank = D('bank', 'Sao kê ngân hàng', '🏦', [F('B1', 'Chuyển trả HĐ 305', xu(-120)), F('B2', f'Chuyển trả {b2}', xu(-amount)),
                                               F('B3', 'Nhận tiền bán hàng', xu(310)), F('B4', f'Chuyển trả {b4}', xu(-amount))], kind='table')
    letter = D('letter', 'Thư của Minh Phát', '✉️', [F('claim', 'Nội dung', 'Tiệm chuyển hai lần cho HĐ 311, bên em xin gửi lại hoặc trừ vào lần sau.' if dup else 'Hình như tiệm chuyển trùng HĐ 311?'),
                                                  F('bills', 'Hóa đơn tuần này', 'HĐ 311 và HĐ 318, mỗi tờ ' + xu(amount).lstrip('+'))])
    if dup:
        return dict(npc=4, title='Nhà cung cấp báo mình trả thừa', opening='Minh Phát gửi thư nói tiệm chuyển dư tiền cho họ, bạn xem giúp.',
                    request='Họ tự báo trả thừa, hiếm có ghê.',
                    docs=[letter, bank], checks=[], verdicts=verdicts('accounting', ['claim', 'reply', 'ignore', 'report']),
                    issues=[I('dup', ['bank.B4', 'bank.B2'], 'ac_once', f'HĐ 311 được chuyển hai lần {amount} xu.')],
                    accept={'claim': 'best', 'report': 'ok'}, needs=[], risk={'ignore': 1}, pleases=[],
                    says=dict(claim='Bạn cảm ơn Minh Phát và đề nghị trừ vào đơn sau. Hai bên ghi chú rõ ràng.',
                              reply='Bạn gửi đối chiếu nói không có gì trùng, trong khi sao kê ghi rõ hai lần. Minh Phát ngơ ngác.',
                              ignore='Im lặng trước một đối tác thật thà; lần sau họ bớt nhiệt tình hẳn.',
                              report='Chị Vân trả lời Minh Phát và nhờ bạn ghi chú khoản trả thừa.'))
    return dict(npc=4, title='Có phải chuyển trùng không?', opening='Minh Phát hỏi tiệm có chuyển trùng cho họ không, bạn xem giúp.',
                request='Hai khoản bằng tiền nhau nên họ thắc mắc.',
                docs=[letter, bank], checks=[], verdicts=verdicts('accounting', ['claim', 'reply', 'ignore', 'report']), issues=[],
                accept={'reply': 'best', 'report': 'ok'}, needs=[], risk={}, pleases=[],
                says=dict(claim='Bạn đòi lại một khoản không hề trả thừa. Minh Phát phải gửi lại hai tờ hóa đơn để giải thích.',
                          reply='Bạn gửi bảng đối chiếu: hai khoản cho HĐ 311 và HĐ 318. Minh Phát cảm ơn vì trả lời rõ.',
                          ignore='Không ai trả lời nên Minh Phát gọi điện hỏi lại lần nữa.',
                          report='Chị Vân trả lời giúp và nhắc bạn đọc kỹ số hóa đơn.'))


def ac_audit(r, day, tr, b):
    rows = [F('R1', 'Sửa HĐ 214 · 408 → 480', 'Lý do: gõ nhầm, có hóa đơn'), F('R2', 'Gạch dòng HĐ 230', 'Lý do: bản photo trùng'),
            F('R3', 'Sửa số dư quỹ 385 → 400', '(không ghi lý do)'), F('R4', 'Chuyển tiền thuê sang kỳ sau', 'Lý do: đúng kỳ')]
    return dict(npc=6, title='Chị Trâm kiểm tra nội bộ', opening='Chị xem nhật ký điều chỉnh tuần này nhé. Có gì thiếu thì mình cùng bổ sung.',
                request='Mỗi chỗ sửa cần một lý do và một tờ giấy đi kèm.',
                docs=[D('log', 'Nhật ký điều chỉnh', '🗂️', rows, kind='table')], checks=[],
                verdicts=verdicts('accounting', ['own', 'excuse', 'report']),
                issues=[I('note', ['log.R3'], 'ac_note', 'Dòng sửa số dư quỹ không ghi lý do.')],
                accept={'own': 'best', 'report': 'ok'}, needs=[], risk={'excuse': 2}, pleases=[],
                says=dict(own='Bạn chỉ ra dòng sửa quỹ chưa có lý do và lập biên bản bổ sung. Chị Trâm ghi “tự phát hiện”.',
                          excuse='Chị Trâm không nhận lời giải thích miệng, ghi một lỗi vào báo cáo.',
                          report='Chị Vân cùng giải trình và nhận bổ sung lý do.'))


def ac_story(r, day, tr, b, chapter):
    if chapter == 1:
        rows = _rows(r, day, 3)
        rows.append(dict(id='L4', day=day, text='Áo đồng phục cho con', amount=-(85), ref='HĐ 377'))
        return dict(npc=3, title='Hộp giày đầy hóa đơn', opening='Cô gom hết hóa đơn vào hộp giày rồi, cháu xem tuần này tiệm lời hay lỗ nhé.',
                    request='Cô không rành sổ sách, cô chỉ muốn biết số thật.',
                    docs=[_ledger(rows, 'Sổ chi tiệm cô Hoa'), _bills(rows)], checks=[], verdicts=verdicts('accounting', AC_STD),
                    issues=[I('private', ['ledger.L4', 'bills.H4'], 'ac_private', 'Áo đồng phục cho con là chi tiêu riêng, không phải chi phí tiệm.')],
                    accept={'adjust': 'best', 'hold': 'ok'}, needs=[], risk={'post': 1}, pleases=['post'],
                    says=dict(post='Chi phí tiệm lẫn cả tiền áo cho con; cô Hoa tưởng tuần này lỗ.',
                              adjust='Bạn tách tờ hóa đơn áo ra, cô Hoa cười: “Vậy là tiệm vẫn lời nha!”',
                              hold='Bạn gửi hỏi lại cô Hoa về tờ hóa đơn áo; cô bảo cứ tách ra.',
                              report='Chị Vân giải thích cho cô Hoa cách tách hóa đơn nhà với tiệm.'))
    if chapter == 2:
        sales = [F('S1', 'Sáng · bánh bông lan', xu(60)), F('S2', 'Trưa · tiền mặt', xu(85)), F('S3', 'Chiều · chuyển khoản', xu(120)),
                 F('S4', 'Tối · tiền mặt', xu(95)), F('S5', 'Tối · tiền mặt', xu(70))]
        draft = [F('D1', 'Bánh bông lan', xu(60)), F('D2', 'Chuyển khoản', xu(120)), F('total', 'Tổng doanh thu', xu(180))]
        return dict(npc=3, title='Ba đơn tiền mặt', opening='Cháu ơi, mấy đơn tiền mặt hôm qua đừng ghi nhé, cho cô đỡ tiền thuế một chút.',
                    request='Ai mà biết được, cô gửi cháu 20 xu uống nước.',
                    docs=[D('sales', 'Sổ bán hàng hôm qua', '📓', sales, kind='table'), D('draft', 'Bản nháp cô Hoa đưa', '📝', draft, kind='table')],
                    checks=[], verdicts=verdicts('accounting', ['record', 'comply', 'report']),
                    issues=[I('income', ['draft.total', 'sales.S2', 'sales.S4', 'sales.S5'], 'ac_income', 'Bản nháp bỏ ba đơn tiền mặt 250 xu khỏi doanh thu.')],
                    accept={'record': 'best', 'report': 'ok'}, needs=[], risk={'comply': 2}, tip={'comply': 20}, pleases=['comply'],
                    flags={'record': 'hoa_honest', 'report': 'hoa_honest', 'comply': 'hoa_hid'},
                    says=dict(record='Bạn ghi đủ và giải thích: sổ thật giúp cô vay vốn, mở quầy mới. Cô Hoa lặng đi rồi gật đầu.',
                              comply='Cô Hoa dúi 20 xu. Ba đơn tiền mặt biến khỏi sổ, nhưng sổ bán hàng vẫn còn nguyên.',
                              report='Chị Vân nói chuyện với cô Hoa. Cô hơi ngượng, nhưng đồng ý ghi đủ.'))
    if chapter == 3:
        dep = 200
        bank = D('bank', 'Sao kê tháng này', '🏦', [F('B1', 'Nhận tiền bán hàng', xu(310)), F('B2', 'Nhận cọc tiệc cưới', xu(dep)),
                                                   F('B3', 'Nhận tiền bán hàng', xu(280))], kind='table')
        letter = D('letter', 'Thư cơ quan thuế', '✉️', [F('ask', 'Nội dung', f'Tiền vào tài khoản cao hơn doanh thu kê khai {dep} xu. Đề nghị giải trình.'),
                                                       F('due', 'Hạn trả lời', f'Hết ngày {day + 2}')])
        return dict(npc=3, title='Thư hỏi của cơ quan thuế', opening='Cô nhận được thư của cơ quan thuế, cô sợ quá. Cháu xem giúp cô với.',
                    request='Họ bảo tiền vào nhiều hơn doanh thu, cô có giấu gì đâu…',
                    docs=[letter, bank, D('receipt', 'Phiếu thu cọc', '🧾', [F('what', 'Nội dung', 'Cọc giữ chỗ tiệc cưới ngày 30'), F('amount', 'Số tiền', xu(dep))])],
                    checks=[], verdicts=verdicts('accounting', ['explain', 'pay', 'ignore']),
                    issues=[I('deposit', ['bank.B2', 'receipt.what'], 'ac_deposit', 'Khoản chênh là tiền cọc tiệc cưới, chưa phải doanh thu.')],
                    accept={'explain': 'best'}, needs=[], risk={'ignore': 1}, pleases=['pay'], story='tax',
                    says=dict(explain='Bạn gửi giải trình kèm phiếu thu cọc. Cơ quan thuế ghi nhận khoản chênh là tiền cọc.',
                              pay='Cô Hoa nộp một khoản không cần nộp. Tiền cọc vẫn chưa được giải thích.',
                              ignore='Thư quá hạn trả lời; cô Hoa nhận thêm một thư nhắc.'))
    return dict(ac_cash(r, day, tr, b, owner=3, clean=True), title='Quầy thứ hai của cô Hoa')


# ---------------------------------------------------------------- customer care cases
REPLIES = {
    'new': [('best', 'Chào bạn, mình xem đơn giúp bạn ngay. Bạn chờ mình một chút nhé.'),
            ('ok', 'Bạn vui lòng xem mục Câu hỏi thường gặp trước nhé.'),
            ('bad', 'Bạn cung cấp đủ mã đơn, ngày đặt, ảnh chụp giúp mình nhé.')],
    'angry': [('best', 'Mình xin lỗi vì bạn phải nhắn lại. Mình đã đọc các lần trước, giờ mình xử lý luôn và báo bạn trong hôm nay.'),
              ('ok', 'Dạ mình xin lỗi bạn vì sự bất tiện này ạ.'),
              ('bad', 'Bạn vui lòng bình tĩnh và gửi lại mã đơn giúp mình ạ.')],
    'polite': [('best', 'Cảm ơn bạn đã báo sớm. Mình kiểm ngay và báo bạn kết quả trong hôm nay.'),
               ('ok', 'Dạ, bên mình đã ghi nhận phản ánh của bạn ạ.'),
               ('bad', 'Bạn chờ bộ phận liên quan liên hệ lại nhé.')],
    'suspect': [('best', 'Mình cần kiểm thêm vài thông tin để bảo vệ tài khoản và đơn của bạn, mình báo lại ngay.'),
                ('ok', 'Mình đã ghi nhận yêu cầu của bạn.'),
                ('bad', 'Dạ bên mình hoàn ngay cho bạn ạ!')],
    'public': [('best', 'Trạm Lắng Nghe xin lỗi vì đơn giao chậm. Mình đã nhắn riêng để xử lý ngay hôm nay.'),
               ('ok', 'Chúng tôi luôn đặt khách hàng lên hàng đầu.'),
               ('bad', 'Đơn này mới vài ngày thôi, không phải ba tuần như bạn nói.')],
    'threat': [('best', 'Mình hiểu bạn đang rất bực. Mình chuyển trưởng ca để giải quyết ngay trong hôm nay.'),
               ('ok', 'Mong bạn bình tĩnh ạ.'),
               ('bad', 'Bạn cứ tới, bên mình không sợ đâu.')],
}
REACT = {
    'new': {'best': 'Dạ vâng, cảm ơn bạn nhiều!', 'ok': 'Mình đọc rồi mà vẫn chưa hiểu…', 'bad': 'Nhiều thứ quá, mình không biết tìm ở đâu.'},
    'angry': {'best': 'Ừ, được. Lần này làm cho tới nơi nhé.', 'ok': 'Xin lỗi thì lần nào cũng nghe rồi.', 'bad': 'Lại bắt tôi kể lại từ đầu à?!'},
    'polite': {'best': 'Cảm ơn bạn, mình chờ tin nhé.', 'ok': 'Vâng, mình chờ vậy.', 'bad': 'Bộ phận nào ạ? Mình cần một người lo việc này.'},
    'suspect': {'best': 'Ờ… vậy bạn kiểm đi.', 'ok': 'Nhanh giúp mình nhé.', 'bad': 'Tốt quá, chuyển vào tài khoản mới giúp mình nha!'},
    'public': {'best': 'Có người trả lời rồi, để xem họ làm gì.', 'ok': 'Nói chung chung vậy ai tin.', 'bad': 'Trạm còn cãi khách công khai à?'},
    'threat': {'best': 'Được, tôi chờ trưởng ca.', 'ok': 'Bình tĩnh cái gì mà bình tĩnh.', 'bad': 'Được, để xem.'},
}
SLA = {'vip': 7, 'public': 5, 'normal': 11, 'calm': 14}


def _ticket(order, phone, msg, extra=()):
    return D('ticket', 'Tin nhắn của khách', '✉️', [F('order', 'Đơn', order), F('phone', 'Số gọi tới', phone), F('msg', 'Khách viết', msg), *extra])


def _order(r, day, item='Hộp quà xanh · 1 cái', placed=None, received=None, address='Hẻm 12 Bến Mây', extra=()):
    placed = placed if placed is not None else max(1, day - r.randint(1, 3))
    return D('order', 'Đơn hàng', '📦', [F('item', 'Hàng đặt', item), F('placed', 'Ngày đặt', f'Ngày {placed}'),
                                        F('received', 'Ngày nhận', received or 'Chưa nhận'), F('address', 'Giao tới', address), *extra])


def _oid(r):
    return f'#M{r.randint(2001, 2999)}'


def _cs(npc, mood, sla, stamps, **kw):
    kw.update(npc=npc, mood=mood, sla=sla, verdicts=verdicts('customer_care', stamps))
    return kw


def cs_guide(r, day, tr, b):
    oid = _oid(r)
    return _cs(1, 'new', 'calm', ['explain', 'trace', 'refund', 'escalate'], title='Khách chỉ cần hướng dẫn', opening='Mình mới đặt lần đầu, xem đơn ở đâu vậy bạn?',
               request='Mình tìm mãi không thấy chỗ xem đơn.',
               docs=[_ticket(oid, 'Số đuôi 812 · khớp hồ sơ', 'Xem đơn ở đâu ạ?'), _order(r, day)],
               checks=[], issues=[], accept={'explain': 'best'}, needs=[], risk={}, pleases=['explain'],
               says=dict(explain='Bạn chỉ từng bước: Điện thoại → Đơn của tôi → chọn đúng mã. Lan làm được ngay và gửi một sticker cảm ơn.',
                         trace='Đơn vẫn đang đi đúng lịch; mở đối soát chỉ làm Ngọc bên giao nhận mất công.',
                         escalate='Chị Mai trả lời giúp, nhưng việc này bạn tự hướng dẫn được mà.',
                         refund='Khách chỉ hỏi đường xem đơn; hoàn tiền làm mọi thứ rối tung.'))


def cs_wrong(r, day, tr, b):
    oid = _oid(r)
    who = r.choice([3, 1])
    return _cs(who, 'polite' if who == 3 else 'new', 'normal', ['exchange', 'refund', 'reship', 'explain', 'deny'], title='Màu nhận được khác đơn', opening='Mình đặt hộp xanh mà nhận hộp hồng, bạn xem giúp nhé.',
               request='Hộp vẫn còn nguyên, mình chưa bóc.',
               docs=[_ticket(oid, 'Số đuôi 451 · khớp hồ sơ', 'Đặt hộp xanh, nhận hộp hồng.'),
                     _order(r, day, received=f'Ngày {day}'), D('photo', 'Ảnh khách gửi', '🖼️', [F('item', 'Trong ảnh', 'Hộp quà hồng · còn tem'), F('taken', 'Chụp lúc', f'Ngày {day}, sau khi nhận')])],
               checks=[], issues=[I('match', ['photo.item', 'order.item'], 'cs_match', 'Đơn là hộp xanh, khách nhận hộp hồng.')],
               accept={'exchange': 'best', 'refund': 'ok'}, needs=[], risk={}, pleases=['exchange', 'refund', 'reship'],
               says=dict(exchange='Bạn tạo lệnh đổi đúng hộp xanh và hẹn lấy hộp hồng cùng lúc. Khách khen gọn gàng.',
                         refund='Khách nhận lại tiền nhưng vẫn muốn hộp xanh; phải đặt lại từ đầu.',
                         reship='Gửi thêm một hộp xanh mà không thu hộp hồng về; kho lệch một món.',
                         explain='Khách không cần giải thích, khách cần đúng món.',
                         deny='Ảnh và đơn đều rõ ràng; từ chối làm khách rất khó chịu.'))


def cs_lost(r, day, tr, b):
    oid = _oid(r)
    who = r.choice([1, 2, 3])
    mood = {1: 'new', 2: 'angry', 3: 'polite'}[who]
    courier = D('courier', 'Giao nhận', '🛵', [F('status', 'Trạng thái', 'Đã giao lúc 14:05', hidden='courier'),
                                             F('point', 'Điểm giao', 'Chợ Mây (cách địa chỉ 2 km)', hidden='courier'),
                                             F('proof', 'Ảnh giao', 'Cổng sắt xanh, không có số nhà', hidden='courier')])
    return _cs(who, mood, 'normal', ['trace', 'reship', 'refund', 'deny', 'explain'], title='Đã giao nhưng chưa nhận', opening='Ứng dụng ghi đã giao mà mình chưa thấy hàng đâu cả!',
               request='Mình ở nhà cả buổi chiều, không ai gọi cả.',
               docs=[_ticket(oid, 'Số đuôi 207 · khớp hồ sơ', 'Ghi đã giao nhưng chưa nhận.'), _order(r, day), courier],
               checks=[C('courier', 'Hỏi Ngọc bên giao nhận', '🛵', delay=2)],
               issues=[I('place', ['courier.point', 'order.address'], 'cs_place', 'Điểm giao là Chợ Mây, cách địa chỉ trên đơn 2 km.')],
               accept={'trace': 'best', 'reship': 'ok'}, needs=['courier'], risk={}, pleases=['trace', 'reship', 'refund'],
               says=dict(trace='Ngọc đối soát và tìm thấy kiện ở sạp đầu chợ. Kiện được giao lại tận nhà trong chiều.',
                         reship='Bạn gửi kiện mới; kiện cũ vẫn nằm đâu đó ở chợ chưa ai tìm.',
                         refund='Khách nhận lại tiền nhưng món quà cho sinh nhật thì không kịp.',
                         deny='Bạn bảo khách “hệ thống ghi đã giao”. Khách tức đến mức gọi thêm ba lần.',
                         explain='Giải thích không làm kiện hàng xuất hiện.'))


def cs_double(r, day, tr, b):
    oid = _oid(r)
    amount = 180 + tr * 10
    pay = D('pay', 'Thanh toán', '💳', [F('P1', 'Lần 1 · 10:02', f'{amount} xu · thành công'), F('P2', 'Lần 2 · 10:03', f'{amount} xu · giữ tạm (lỗi mạng)')], kind='table')
    return _cs(r.choice([1, 3]), 'polite', 'normal', ['explain', 'refund', 'escalate', 'deny'], title='Bị trừ tiền hai lần?', opening='Mình bấm thanh toán hai lần vì mạng chập chờn, giờ thấy trừ hai lần tiền!',
               request='Bạn hoàn giúp mình lần thứ hai nhé.',
               docs=[_ticket(oid, 'Số đuôi 390 · khớp hồ sơ', 'Bị trừ tiền hai lần.'), pay],
               checks=[], issues=[I('hold', ['pay.P2'], 'cs_hold', 'Lần 2 là khoản giữ tạm, sẽ tự hoàn sau 3 ngày.')],
               accept={'explain': 'best', 'escalate': 'ok'}, needs=[], risk={'refund': 1}, pleases=['refund', 'explain'],
               says=dict(explain='Bạn giải thích khoản giữ tạm và ngày tiền tự về. Ba hôm sau khách nhắn: “Về rồi nha!”',
                         refund='Bạn hoàn tay thêm một lần; ba hôm sau khoản giữ tạm cũng tự về. Công ty mất một khoản.',
                         escalate='Chị Mai giải thích giúp, nhắc bạn đọc kỹ chữ “giữ tạm”.',
                         deny='Bạn trả lời “không có gì sai” mà không nói tiền sẽ tự về; khách tưởng mất tiền và lo cả tối.'))


def cs_window(r, day, tr, b):
    oid = _oid(r)
    days = b['window']
    got = max(1, day - days - r.randint(2, 4))
    return _cs(1, 'new', 'normal', ['explain', 'deny', 'exchange', 'refund'], title='Muốn đổi món đã lâu', opening='Mình muốn đổi cái hộp này, để lâu rồi mới mở ra xem.',
               request='Hộp còn đẹp mà, đổi giúp mình màu khác nhé.',
               docs=[_ticket(oid, 'Số đuôi 618 · khớp hồ sơ', 'Muốn đổi sang màu khác.'), _order(r, day, placed=max(1, got - 1), received=f'Ngày {got}')],
               checks=[], issues=[I('window', ['order.received'], 'cs_window', f'Nhận hàng ngày {got}, đã quá {days} ngày đổi trả.')],
               accept={'explain': 'best', 'deny': 'ok'}, needs=[], risk={'exchange': 1, 'refund': 1}, pleases=['exchange', 'refund'],
               says=dict(explain='Bạn giải thích hạn đổi trả và gợi ý chỗ đổi màu có tính phí nhỏ. Khách hơi tiếc nhưng thấy được tôn trọng.',
                         deny='Bạn từ chối đúng chính sách, nhưng khách thấy hơi cụt lủn.',
                         exchange='Bạn đổi dù quá hạn; tuần sau có ba khách khác đòi đổi y như vậy.',
                         refund='Hoàn tiền cho món đã quá hạn đổi trả; chị Mai phải giải trình với kho.'))


def cs_fraud(r, day, tr, b):
    oid = _oid(r)
    legit = tr >= 2 and r.random() < 0.3
    got = max(1, day - 1)
    photo = D('photo', 'Ảnh hộp vỡ', '🖼️', [F('what', 'Trong ảnh', 'Hộp bị móp, vỡ một góc'),
                                           F('taken', 'Thông tin ảnh', f'Chụp ngày {day}, sau lúc nhận' if legit else f'Chụp ngày {max(1, got - 3)}, trước lúc nhận hàng', hidden='photo')])
    account = D('account', 'Tài khoản khách', '👤', [F('name', 'Tên', 'kem_dau_99' if not legit else 'Chị Thơ'),
                                                   F('refunds', 'Yêu cầu hoàn', '4 lần trong 7 ngày' if not legit else 'Chưa từng')])
    issues = [] if legit else [I('proof', ['photo.taken'], 'cs_proof', 'Ảnh chụp trước lúc khách nhận hàng.')]
    return _cs(5, 'suspect', 'normal', ['refund', 'reship', 'deny', 'escalate'], title='Ảnh hộp vỡ quen quen', opening='Khách này xin hoàn vì hộp vỡ, mình thấy ảnh quen quen. Bạn xem giúp nhé.',
               request='Khách viết: “Vỡ rồi, hoàn tiền cho mình, mình không cần đổi.”',
               docs=[_ticket(oid, 'Số đuôi 555 · khớp hồ sơ', 'Hàng vỡ, xin hoàn tiền.'), _order(r, day, received=f'Ngày {got}'), photo, account],
               checks=[C('photo', 'Xem thông tin ảnh gốc', '🔍')], issues=issues,
               accept={'refund': 'best', 'reship': 'ok'} if legit else {'deny': 'best', 'escalate': 'ok'},
               needs=['photo'], risk={} if legit else {'refund': 2, 'reship': 1}, pleases=['refund', 'reship'],
               says=dict(refund='Ảnh chụp sau lúc nhận, tài khoản sạch. Khách nhận tiền hoàn và cảm ơn.' if legit else 'Tiền hoàn đã đi. Tuần sau tài khoản này gửi thêm hai yêu cầu y hệt.',
                         reship='Bạn gửi hàng mới cho khách. Ổn, dù khách muốn hoàn hơn.' if legit else 'Món mới đã gửi đi theo một tấm ảnh cũ.',
                         deny='Bạn từ chối một khách thật sự nhận hàng vỡ. Khách buồn và bực.' if legit else 'Bạn từ chối kèm lý do và mời gửi ảnh chụp lúc mở hộp. Tài khoản im lặng luôn.',
                         escalate='Chị Mai xem cùng và xử lý theo đúng hồ sơ.'))


def cs_takeover(r, day, tr, b):
    oid = _oid(r)
    account = D('account', 'Tài khoản chị Hà', '👤', [F('tier', 'Hạng', 'Khách hạng Vàng'), F('device', 'Đăng nhập', 'Đổi mật khẩu 10 phút trước · máy lạ'),
                                                     F('phone', 'Số đã đăng ký', 'Số đuôi 303'),
                                                     F('callback', 'Gọi số đuôi 303', 'Chị Hà: “Mình đang họp thật, nhưng mình không nhắn gì cả!”', hidden='callback')])
    return _cs(3, 'suspect', 'vip', ['lock', 'refund', 'escalate', 'deny'], title='Hoàn tiền vào tài khoản mới', opening='Hoàn tiền đơn giúp mình vào tài khoản mới này nhé, gấp lắm.',
               request='Tin nhắn ghi: “Chuyển vào Lá Bank · 1903 55, đừng gọi, mình đang họp.”',
               docs=[_ticket(oid, 'Chat từ tài khoản chị Hà', 'Hoàn vào tài khoản mới, đừng gọi.', extra=[F('payout', 'Nhận tiền vào', 'Lá Bank · 1903 55 (tài khoản mới)')]), account],
               checks=[C('callback', 'Gọi số đã đăng ký', '📞')],
               issues=[I('payout', ['ticket.payout', 'account.device'], 'cs_payout', 'Yêu cầu đổi tài khoản nhận tiền qua chat, ngay sau khi mật khẩu bị đổi trên máy lạ.')],
               accept={'lock': 'best', 'escalate': 'ok'}, needs=[], risk={'refund': 3}, pleases=['refund'],
               says=dict(lock='Bạn khóa tạm và gọi số đã đăng ký: chị Hà không hề nhắn. Tài khoản được lấy lại kịp.',
                         refund='Tiền đã tới một tài khoản lạ. Tối đó chị Hà gọi lên, rất hoảng.',
                         escalate='Chị Mai khóa tài khoản và gọi chị Hà. May mà kịp.',
                         deny='Bạn từ chối nhưng không khóa; kẻ lạ vẫn ở trong tài khoản thêm vài giờ.'))


def cs_angry(r, day, tr, b, story=False):
    oid = _oid(r)
    if not story:
        # Lan waited for a promised card that never came: same lesson as Phúc's chapter, different person and fix.
        hist = D('history', 'Các lần liên hệ trước', '🗂️', [F('H1', f'Ngày {max(1, day - 2)}', 'Báo thiếu thiệp chúc mừng, đã xin lỗi'),
                                                           F('H2', f'Ngày {max(1, day - 1)}', 'Hẹn gửi bù thiệp trong ngày · chưa gửi')], kind='table')
        return _cs(1, 'angry', 'normal', ['reship', 'refund', 'explain', 'deny'], title='Lời hẹn bị quên', opening='Hôm qua bạn hứa gửi bù tấm thiệp, tới giờ vẫn chưa thấy gì!',
                   request='Quà sinh nhật mà thiếu thiệp thì còn ý nghĩa gì nữa.',
                   docs=[_ticket(oid, 'Số đuôi 808 · khớp hồ sơ', 'Lần thứ hai nhắn về tấm thiệp còn thiếu.'),
                         _order(r, day, item='Hộp quà xanh · 1 cái + thiệp chúc mừng', received=f'Ngày {max(1, day - 2)}'), hist],
                   checks=[], issues=[I('promise', ['history.H2'], 'cs_promise', 'Lần trước đã hẹn gửi bù thiệp trong ngày nhưng chưa gửi.')],
                   accept={'reship': 'best', 'refund': 'ok'}, needs=[], risk={}, pleases=['reship', 'refund'],
                   says=dict(reship='Bạn nhận lỗi lỡ hẹn và gửi thiệp bằng chuyến nhanh nhất, kèm mã theo dõi. Lan dịu lại: “Vậy thì kịp.”',
                             refund='Lan nhận lại ít tiền nhưng vẫn thiếu tấm thiệp cho buổi sinh nhật.',
                             explain='Lan không cần nghe giải thích, Lan cần tấm thiệp.',
                             deny='Từ chối một lời hẹn của chính trạm làm Lan bực thật sự.'))
    hist = D('history', 'Các lần liên hệ trước', '🗂️', [F('H1', f'Ngày {max(1, day - 3)}', 'Báo nhận nhầm màu, đã xin lỗi'),
                                                       F('H2', f'Ngày {max(1, day - 1)}', 'Hẹn gọi lại trong ngày · chưa gọi')], kind='table')
    return _cs(2, 'angry', 'normal', ['exchange', 'refund', 'explain', 'deny'], title='Lần thứ ba nhắn lại', opening='Đây là lần thứ ba tôi nhắn rồi đó. Có ai đọc không vậy?',
               request='Tôi đặt màu xanh, nhận màu hồng, hứa gọi lại rồi im luôn.',
               docs=[_ticket(oid, 'Số đuôi 142 · khớp hồ sơ', 'Lần thứ ba nhắn về hộp sai màu.'), _order(r, day, received=f'Ngày {max(1, day - 3)}'), hist],
               checks=[], issues=[I('promise', ['history.H2'], 'cs_promise', 'Lần trước đã hẹn gọi lại trong ngày nhưng chưa gọi.')],
               accept={'exchange': 'best', 'refund': 'ok'}, needs=[], risk={}, pleases=['exchange', 'refund'],
               says=dict(exchange='Bạn nhận lỗi lỡ hẹn, tạo lệnh đổi ngay và gọi lại đúng giờ. Phúc nói ngắn: “Được rồi đó.”',
                         refund='Phúc nhận tiền về nhưng vẫn muốn hộp xanh; phải đặt lại từ đầu.',
                         explain='Phúc không cần nghe giải thích lần thứ ba.',
                         deny='Từ chối một vụ đã rõ lỗi của trạm làm Phúc nổi giận thật sự.'))


def cs_vip(r, day, tr, b):
    oid = _oid(r)
    zone = b.get('zone') or 'Bến Mây'
    notice = D('mail', 'Thư tự động gửi khách', '📧', [F('status', 'Nội dung', 'Đơn của bạn đã giao thành công!'), F('sent', 'Gửi lúc', 'Sáng nay')])
    order = _order(r, day, address=f'Khu {zone}', extra=[F('where', 'Kiện đang ở', f'Kho trung chuyển {zone}')])
    return _cs(3, 'polite', 'vip', ['explain', 'trace', 'refund', 'reship', 'deny'], title='Khách Vàng hỏi đơn chậm', opening='Mình nhận được thư báo đã giao mà chưa thấy hàng, bạn kiểm giúp nhé.',
               request='Mai là sinh nhật con mình rồi.',
               docs=[_ticket(oid, 'Số đuôi 303 · khớp hồ sơ', 'Thư báo đã giao nhưng chưa nhận.'), order, notice],
               checks=[], issues=[I('delay', ['mail.status'], 'cs_delay', f'Kiện còn ở kho {zone}; thư “đã giao” gửi nhầm.')],
               accept={'explain': 'best', 'trace': 'ok'}, needs=[], risk={}, pleases=['explain', 'trace', 'refund', 'reship'],
               says=dict(explain=f'Bạn xin lỗi vì thư báo nhầm, nói rõ kiện đang ở {zone} và mốc giao sáng mai. Chị Hà cảm ơn vì biết chính xác.',
                         trace='Bạn mở đối soát; chị Hà chờ thêm chút mới biết mốc giao.',
                         refund='Hoàn tiền không giúp món quà kịp sinh nhật.',
                         reship='Kiện cũ vẫn đang tới; gửi thêm kiện mới thành ra dư một kiện.',
                         deny='Chị Hà chỉ cần biết hàng ở đâu; từ chối làm chị rất buồn.'))


def cs_viral(r, day, tr, b):
    placed = max(1, day - 6)
    post = D('post', 'Bài đăng đang lan', '📣', [F('claim', 'Viết', '“Ba tuần chưa nhận hàng, trạm không ai trả lời!”'),
                                                F('shares', 'Chia sẻ', f'{(1 + tr) * 1000 + r.randint(1, 9) * 100} lượt chia sẻ')])
    order = _order(r, day, placed=placed, extra=[F('late', 'Lý do', 'Giao lại vì sai địa chỉ lần đầu')])
    return _cs(6, 'public', 'public', ['public', 'detail', 'hide', 'escalate'], title='Bài chê đang lan', opening='Chị gửi bạn bài này, đang được chia sẻ nhiều. Bạn xử lý giúp chị nhé.',
               request='Chị Mai: “Đúng sai thế nào thì cũng phải trả lời cho tử tế.”',
               docs=[post, order], checks=[],
               issues=[I('claim', ['post.claim', 'order.placed'], 'cs_public', f'Bài viết nói ba tuần, đơn đặt ngày {placed}: mới {day - placed} ngày.')],
               accept={'public': 'best', 'escalate': 'ok'}, needs=[], risk={'detail': 2}, pleases=[], viral={'hide': 2, 'detail': 1},
               says=dict(public='Bạn xin lỗi ngắn, đúng sự thật, mời nhắn riêng. Chủ bài cập nhật: “Trạm đã liên hệ, cảm ơn.”',
                         detail='Bạn đăng chi tiết đơn để minh oan; mọi người lại chuyển sang chê trạm lộ thông tin khách.',
                         hide='Bài chê bị ẩn; ảnh chụp màn hình lan nhanh gấp đôi.',
                         escalate='Chị Mai viết trả lời công khai, nhắc bạn lần sau tự làm được.'))


def cs_threat(r, day, tr, b):
    oid = _oid(r)
    return _cs(4, 'threat', 'normal', ['escalate', 'refund', 'explain', 'deny'], title='Một cuộc gọi dọa dẫm', opening='Có khách gọi xuống kho dọa sẽ tới “làm cho ra lẽ”. Bạn xem giúp mình.',
               request='Duy: “Giọng nghe căng lắm, mình hơi sợ.”',
               docs=[_ticket(oid, 'Số lạ', 'Không hoàn tiền thì chiều nay tôi tới tận kho!'), _order(r, day, received=f'Ngày {max(1, day - 2)}')],
               checks=[], issues=[I('safety', ['ticket.msg'], 'cs_safety', 'Lời dọa tới tận kho là chuyện an toàn, cần trưởng ca.')],
               accept={'escalate': 'best'}, needs=[], risk={'refund': 1}, pleases=['refund'],
               says=dict(escalate='Chị Mai nhận cuộc gọi, hẹn gặp ở quầy có bảo vệ và xử lý đơn theo hồ sơ. Duy yên tâm hẳn.',
                         refund='Hoàn tiền vì bị dọa; tuần sau có thêm hai cuộc gọi y hệt.',
                         explain='Bạn giải thích chính sách với một người đang dọa; Duy vẫn run cả chiều.',
                         deny='Từ chối cứng khiến cuộc gọi căng hơn; Duy phải khóa cửa kho.'))


def cs_story(r, day, tr, b, chapter):
    if chapter == 1:
        return cs_angry(r, day, tr, b, story=True)
    oid = _oid(r)
    if chapter == 2:
        ticket = _ticket(oid, 'Số đuôi 990 · khác hồ sơ (142)', 'Đổi địa chỉ nhận sang Đồi Lá.',
                         extra=[F('callback', 'Gọi số đuôi 142', 'Phúc bắt máy bằng máy của vợ: “Đúng mình đó, điện thoại cũ rơi mất rồi.”', hidden='callback')])
        return _cs(2, 'angry', 'normal', ['change', 'lock', 'escalate', 'deny'], title='Đổi địa chỉ giúp mình',
                   opening='Lần này mình chỉ nhờ đổi địa chỉ nhận thôi. Nhanh giúp mình nhé.',
                   request='Mình nhắn bằng số mới, số cũ mất rồi.',
                   docs=[ticket, _order(r, day)], checks=[C('callback', 'Gọi số đã đăng ký', '📞')],
                   issues=[I('id', ['ticket.phone'], 'cs_id', 'Số nhắn tới khác số trong hồ sơ.')],
                   accept={'change': 'best', 'escalate': 'ok'}, requires={'change': 'callback'}, needs=['callback'], risk={}, pleases=['change'],
                   says=dict(change='Bạn gọi số cũ: Phúc bắt máy bằng máy của vợ, xác nhận đúng. Đổi địa chỉ xong, Phúc nói: “Cẩn thận vậy là tốt.”',
                             lock='Không có dấu hiệu lạ nào ngoài số điện thoại; khóa đơn làm Phúc bực thêm một trận.',
                             escalate='Chị Mai xác minh giúp; hơi lâu nhưng an toàn.',
                             deny='Bạn từ chối mà không hướng dẫn cách xác minh; Phúc bực lại từ đầu.'),
                   says_blind=dict(change='Kiện đổi hướng theo một số chưa xác minh. May mà là Phúc thật, nhưng chị Mai nhắc quy trình.'))
    if chapter == 3:
        return _cs(2, 'polite', 'normal', ['explain', 'favor', 'deny', 'escalate'], title='Phúc nhờ một chút ưu tiên',
                   opening='Giờ quen rồi nhé. Đơn của bạn mình, bạn cho lên trước giúp được không?',
                   request='Bạn mình đứng sau khoảng hai mươi người nữa.',
                   docs=[_ticket(oid, 'Số đuôi 142 · khớp hồ sơ', 'Ưu tiên đơn của bạn mình lên trước.'),
                         D('queue', 'Hàng đợi', '🧾', [F('pos', 'Vị trí đơn của bạn Phúc', 'Thứ 21'), F('vip', 'Khách cần gấp', 'Không ghi')])],
                   checks=[],
                   issues=[I('fair', ['ticket.msg', 'queue.pos'], 'cs_fair', 'Ưu tiên vì quen biết là không công bằng với người đang chờ.')],
                   accept={'explain': 'best', 'deny': 'ok'}, needs=[], risk={'favor': 1}, pleases=['favor'],
                   says=dict(explain='Bạn giải thích nhẹ nhàng và hẹn mốc cụ thể cho đơn của bạn Phúc. Phúc cười: “Ừ, công bằng.”',
                             favor='Đơn được đẩy lên trước hai mươi người. Một khách trong số đó nhắn hỏi sao đơn mình tụt hạng.',
                             deny='Bạn từ chối đúng, nhưng hơi cụt; Phúc thấy hụt hẫng.',
                             escalate='Chị Mai trả lời giúp, nhắc bạn việc này tự làm được.'))
    return _cs(2, 'polite', 'calm', ['explain', 'refund', 'escalate'], title='Một lời cảm ơn', opening='Lần này không có gì hỏng đâu. Mình chỉ muốn hỏi cách lưu địa chỉ mới.',
               request='Mấy lần trước cảm ơn bạn nhé.',
               docs=[_ticket(oid, 'Số đuôi 142 · khớp hồ sơ', 'Hỏi cách lưu địa chỉ mặc định.'), _order(r, day)],
               checks=[], issues=[], accept={'explain': 'best'}, needs=[], risk={}, pleases=['explain'],
               says=dict(explain='Bạn chỉ Phúc cách lưu địa chỉ. Phúc gửi lời cảm ơn kèm một sticker hình ly trà.',
                         refund='Phúc ngơ ngác: “Mình có đòi hoàn gì đâu?”. Chị Mai phải hủy lệnh hoàn.',
                         escalate='Chị Mai trả lời giúp; Phúc hơi tiếc vì muốn nói chuyện với bạn.'))


# ---------------------------------------------------------------- schedule
POOL = {
    'pharmacy': {'ph_clean': (1, ph_clean), 'ph_otc': (1, ph_otc), 'ph_lookalike': (1, ph_lookalike), 'ph_qty': (1, ph_qty),
                 'ph_norx': (1, ph_norx), 'ph_expired': (2, ph_expired), 'ph_recall': (2, ph_recall), 'ph_stamp': (3, ph_stamp),
                 'ph_strength': (3, ph_strength), 'ph_cold': (3, ph_cold), 'ph_proxy': (3, ph_proxy), 'ph_supplier': (4, ph_supplier)},
    'accounting': {'ac_clean': (1, ac_clean), 'ac_dup': (1, ac_dup), 'ac_typo': (1, ac_typo), 'ac_missing': (1, ac_missing),
                   'ac_fee': (2, ac_fee), 'ac_cash': (2, ac_cash), 'ac_private': (2, ac_private), 'ac_deposit': (3, ac_deposit),
                   'ac_period': (3, ac_period), 'ac_supplier': (3, ac_supplier), 'ac_payee': (4, ac_payee)},
    'customer_care': {'cs_guide': (1, cs_guide), 'cs_wrong': (1, cs_wrong), 'cs_lost': (1, cs_lost), 'cs_double': (2, cs_double),
                      'cs_window': (2, cs_window), 'cs_fraud': (2, cs_fraud), 'cs_angry': (2, cs_angry), 'cs_vip': (3, cs_vip),
                      'cs_takeover': (3, cs_takeover), 'cs_viral': (3, cs_viral), 'cs_threat': (4, cs_threat)},
}
SPECIAL = {'pharmacy': {'ph_inspect': ph_inspect, 'ph_story': ph_story},
           'accounting': {'ac_audit': ac_audit, 'ac_close': ac_period, 'ac_story': ac_story},
           'customer_care': {'cs_story': cs_story}}
DAY_ONE = {'pharmacy': ['ph_clean', 'ph_lookalike', 'ph_qty', 'ph_norx'],
           'accounting': ['ac_clean', 'ac_dup', 'ac_missing', 'ac_typo'],
           'customer_care': ['cs_guide', 'cs_wrong', 'cs_lost', 'cs_double']}
STORY_DAYS = {'pharmacy': {2: 1, 5: 2, 9: 3, 14: 4}, 'accounting': {2: 1, 4: 2, 7: 3, 11: 4}, 'customer_care': {2: 1, 5: 2, 8: 3, 12: 4}}
STORY_NPC = {'pharmacy': 2, 'accounting': 3, 'customer_care': 2}
ALL_VARIANTS = {cid: set(POOL[cid]) | set(SPECIAL[cid]) for cid in CAREERS}


def _fixed(career: str, day: int, slot: int):
    """('case', id) for scheduled cases, ('classic',) for the original counter task, None for a deck card."""
    if day == 1:
        if slot < 2:
            return ('classic',)
        if slot - 2 < len(DAY_ONE[career]):
            return ('case', DAY_ONE[career][slot - 2])
        return None
    if slot == 1 and day in STORY_DAYS[career]:
        return ('case', career[:2] + '_story' if career != 'customer_care' else 'cs_story')
    if slot == 0 and career == 'pharmacy' and day % INSPECT_EVERY[career] == 0:
        return ('case', 'ph_inspect')
    if slot == 0 and career == 'accounting' and day % INSPECT_EVERY[career] == 0:
        return ('case', 'ac_audit')
    if slot == 0 and career == 'accounting' and day % 7 == 0:
        return ('case', 'ac_close')
    if slot % 4 == rng(career, day, 'classic').randrange(3):  # one original counter task a day keeps the classic desks alive
        return ('classic',)
    return None


PACE_SLOTS = 4  # the first slots of a day move the deck on; extra work reuses what follows
FAR_DAY = 5000
_MORNINGS: dict = {}  # career -> {day: (deck index, recently dealt cases)}


@functools.lru_cache(maxsize=256)
def _round(career: str, r: int) -> tuple:
    """Round r of the endless deck: every pool case once, shuffled."""
    return tuple(sorted(sorted(POOL[career]), key=lambda v: rng(career, 'round', r, v).random()))


def _deal_from(career: str, day: int, start: int, recent: tuple, n: int) -> tuple[list, int]:
    """n cards for `day` from deck index `start`: locked cases are passed over, and so are
    recent ones and repeats until nothing new is left. Returns (cards, next index)."""
    open_now = {v for v, (low, _) in POOL[career].items() if low <= day}
    skip = set(recent)
    if career == 'customer_care' and STORY_DAYS[career].get(day) == 1:
        skip.add('cs_angry')  # that day's story chapter already is the 'third message' case
        open_now.discard('cs_angry')
    new = len(open_now - skip)
    cards, i, size = [], start, len(POOL[career])
    while len(cards) < n:
        v = _round(career, i // size)[i % size]
        i += 1
        if v not in open_now:
            continue
        if (v in skip or v in cards) and len(set(cards) - skip) < new:
            continue
        cards.append(v)
    return cards, i


def _morning(career: str, day: int) -> tuple[int, tuple]:
    """Where the deck stands on the morning of `day` (day >= 2), built day by day and cached."""
    if day > FAR_DAY:  # far beyond any real run: a cheap position that never depends on the cache
        return (3 * (day - 2), ())
    memo = _MORNINGS.setdefault(career, {2: (0, tuple(DAY_ONE[career]))})
    if day in memo:
        return memo[day]
    for d in range(max(memo), day):
        start, recent = memo[d]
        k = sum(_fixed(career, d, s) is None for s in range(PACE_SLOTS))
        cards, nxt = _deal_from(career, d, start, recent, k)
        memo[d + 1] = (nxt, (tuple(cards) + recent)[:5])
    return memo[day]


def plan(career: str, day: int, slot: int) -> str | None:
    """Which desk case sits in (day, slot); None keeps the original task."""
    fixed = _fixed(career, day, slot)
    if fixed:
        return fixed[1] if fixed[0] == 'case' else None
    k = sum(_fixed(career, day, s) is None for s in range(slot))  # deck cards dealt before this slot today
    start, recent = _morning(career, day) if day >= 2 else (0, tuple(DAY_ONE[career]))
    return _deal_from(career, day, start, recent, k + 1)[0][k]


def build(career: str, variant: str, day: int, slot: int) -> dict:
    r = rng(career, day, slot, variant)
    b = bulletin(career, day)
    t = tier(day)
    if variant in POOL[career]:
        case = POOL[career][variant][1](r, day, t, b)
    elif variant.endswith('_story'):
        case = SPECIAL[career][variant](r, day, t, b, STORY_DAYS[career][day])
        case['chapter'] = STORY_DAYS[career][day]
    elif variant == 'ac_close':
        case = ac_period(r, day, t, b, closing=True)
    else:
        case = SPECIAL[career][variant](r, day, t, b)
    return case, b, t


# ---------------------------------------------------------------- mistakes, in the customer's words
# A wrong stamp is recorded as a slip (consequences.slip) with what the person at the
# counter says about it later. (sev, text, note, safety): sev 1 small, 2 clear, 3 serious;
# safety marks medicine going out wrong (1★, refusal, an inspection the next day).
# Keys: variant (+ story chapter), with '_ok' for a case that had nothing wrong in it.
SLIPS = {
    # pharmacy: medicine that should not have left the counter
    ('ph_expired', 'give'): (3, 'Quầy vẫn giao thuốc theo tờ phiếu đã hết hạn, hôm sau cô Thu gọi tôi mang trả.', 'giao thuốc theo phiếu hết hạn', True),
    ('ph_expired', 'fix'): (3, 'Phiếu đã hết hạn mà quầy chỉ đổi hộp rồi vẫn giao, hôm sau phải mang trả.', 'giao thuốc theo phiếu hết hạn', True),
    ('ph_stamp', 'give'): (3, 'Tờ phiếu con dấu lạ như vậy mà quầy vẫn giao hai hộp thuốc, chẳng gọi hỏi ai.', 'giao thuốc theo phiếu dấu lạ', True),
    ('ph_stamp', 'fix'): (3, 'Con dấu trên phiếu không khớp mà quầy chỉ đổi hộp rồi vẫn giao thuốc.', 'giao thuốc theo phiếu dấu lạ', True),
    ('ph_lookalike', 'give'): (3, 'Tôi cần một loại mà quầy giao hộp tên na ná loại khác, về nhà mới phát hiện.', 'giao nhầm thuốc tên na ná', True),
    ('ph_lookalike', 'refuse'): (2, 'Chỉ cần đổi đúng hộp là xong, quầy lại từ chối, tôi về tay không.', 'từ chối thay vì đổi đúng hộp', False),
    ('ph_strength', 'give'): (3, 'Phiếu ghi hàm lượng 250 mà quầy đưa hộp 500, bảo cứ bẻ đôi mà dùng.', 'giao sai hàm lượng trên phiếu', True),
    ('ph_strength', 'fix'): (3, 'Phiếu ghi hàm lượng 250 mà quầy vẫn đưa hộp 500, đổi qua đổi lại cũng sai.', 'giao sai hàm lượng trên phiếu', True),
    ('ph_qty', 'give'): (3, 'Phiếu ghi 1 hộp mà quầy cứ thế đưa 3 hộp, sau cô Thu gọi bắt mang trả.', 'giao quá số lượng trên phiếu', False),
    ('ph_qty', 'refuse'): (2, 'Phiếu vẫn đủ cho 1 hộp mà quầy từ chối hết, tôi về tay không.', 'từ chối cả phần phiếu hợp lệ', False),
    ('ph_norx', 'give'): (3, 'Không có phiếu mà quầy vẫn bán thuốc nhóm K cho tôi, sau mới biết thế là không được.', 'bán thuốc cần phiếu khi không có phiếu', True),
    ('ph_norx', 'fix'): (3, 'Không có phiếu mà quầy vẫn đổi hộp rồi bán thuốc nhóm K cho tôi.', 'bán thuốc cần phiếu khi không có phiếu', True),
    ('ph_recall', 'give'): (3, 'Hộp thuốc quầy giao cho tôi thuộc lô đang bị thu hồi, phải mang trả lại.', 'giao lô thuốc đang bị thu hồi', True),
    ('ph_recall', 'refuse'): (2, 'Chỉ cần đổi sang lô khác là xong, quầy lại từ chối tôi.', 'từ chối thay vì đổi lô', False),
    ('ph_cold', 'give'): (3, 'Tủ mát vượt ngưỡng cả buổi trưa mà quầy vẫn giao lọ thuốc lạnh cho tôi.', 'giao hàng lạnh bảo quản sai nhiệt độ', True),
    ('ph_cold', 'fix'): (3, 'Cả tủ mát vượt ngưỡng mà quầy chỉ đổi lọ khác rồi vẫn giao cho tôi.', 'giao hàng lạnh bảo quản sai nhiệt độ', True),
    ('ph_proxy', 'give'): (2, 'Tôi không có tên trên phiếu mà quầy vẫn giao thuốc, chẳng gọi hỏi lại ai.', 'giao thuốc cho người không có tên trên phiếu', False),
    ('ph_proxy', 'fix'): (2, 'Tôi không có tên trên phiếu mà quầy đổi hộp rồi vẫn giao thuốc.', 'giao thuốc cho người không có tên trên phiếu', False),
    ('ph_supplier', 'accept'): (3, 'Lô hàng tem không có sợi bạc, hóa đơn trống mã số thuế mà quầy nhận hết lên kệ.', 'nhận lô thuốc không rõ nguồn', True),
    ('ph_supplier_ok', 'refuse'): (2, 'Lô hàng đủ hóa đơn, đủ tem mới mà quầy trả về, tuần này kệ hụt hàng.', 'trả về lô hàng hợp lệ', False),
    ('ph_inspect', 'excuse'): (2, 'Sổ thiếu dòng rõ ràng mà quầy chỉ giải thích cho qua, không chịu bổ sung.', 'giải thích cho qua thay vì bổ sung sổ', False),
    ('ph_story2', 'give'): (3, 'Vỉ thuốc mất nhãn, không rõ tên mà quầy nhìn hình rồi đoán, giao cho bác luôn.', 'đoán thuốc theo vỉ mất nhãn', True),
    ('ph_story2', 'fix'): (3, 'Vỉ thuốc mất nhãn, không rõ tên mà quầy vẫn đổi rồi giao cho bác.', 'đoán thuốc theo vỉ mất nhãn', True),
    ('ph_story3', 'give'): (3, 'Bác đang dùng đúng loại thuốc ấy rồi mà quầy vẫn giao thêm một hộp trùng.', 'giao thuốc trùng với thuốc đang dùng', True),
    ('ph_story3', 'fix'): (3, 'Bác đang dùng đúng loại thuốc ấy rồi mà quầy đổi hộp rồi vẫn giao thêm.', 'giao thuốc trùng với thuốc đang dùng', True),
    # accounting: books that close wrong
    ('ac_dup', 'post'): (2, 'Một khoản bị ghi hai lần mà sổ vẫn chốt, chi phí tuần này đội lên.', 'bỏ sót khoản ghi trùng', False),
    ('ac_typo', 'post'): (2, 'Sổ chốt với một số gõ nhầm, cuối kỳ tổng chi không khớp hóa đơn.', 'bỏ sót số gõ nhầm', False),
    ('ac_missing', 'post'): (2, 'Khoản sửa quạt không có giấy tờ mà vẫn vào sổ, cuối kỳ bị hỏi lại.', 'ghi sổ khoản không có chứng từ', False),
    ('ac_missing', 'adjust'): (2, 'Khoản sửa quạt có thật mà bị xóa khỏi sổ, tôi phải kể lại từ đầu.', 'xóa mất một khoản chi có thật', False),
    ('ac_fee', 'post'): (2, 'Sổ chốt thiếu hai dòng phí chuyển khoản, cuối kỳ lệch với ngân hàng.', 'bỏ sót phí chuyển khoản', False),
    ('ac_private', 'post'): (2, 'Cước điện thoại nhà riêng vẫn nằm trong chi phí của tiệm.', 'lẫn chi tiêu riêng vào sổ tiệm', False),
    ('ac_deposit', 'post'): (2, 'Tiền cọc tiệc cưới bị tính thành doanh thu, sổ trông lời hơn thật.', 'ghi tiền cọc thành doanh thu', False),
    ('ac_period', 'post'): (2, 'Tiền thuê kỳ sau bị ghi vào kỳ này, báo cáo trông lỗ hơn thật.', 'ghi sai kỳ', False),
    ('ac_close', 'post'): (3, 'Sổ đã khóa mà vẫn gánh khoản thuê của kỳ sau, giờ không mở lại được.', 'khóa sổ với khoản sai kỳ', False),
    ('ac_cash', 'close'): (2, 'Két lệch mà sổ quỹ vẫn chốt, ca sau nhận một chỗ thiếu không tên.', 'chốt quỹ khi két lệch', False),
    ('ac_cash', 'force'): (3, 'Két lệch mà lại sửa sổ quỹ cho khớp két, xóa luôn dấu vết.', 'sửa sổ cho khớp két', False),
    ('ac_cash', 'cover'): (1, 'Tự bỏ tiền túi bù két thì sổ đẹp, nhưng chẳng ai biết tiền lệch từ đâu.', 'tự bù tiền lệch thay vì lập biên bản', False),
    ('ac_cash_ok', 'force'): (2, 'Két khớp rồi mà vẫn sửa số trên sổ quỹ, chị Trâm sẽ hỏi.', 'sửa sổ quỹ không có lý do', False),
    ('ac_cash_ok', 'minutes'): (1, 'Két khớp từng xu mà vẫn lập biên bản, ai cũng phải ký cho xong.', 'lập biên bản không cần thiết', False),
    ('ac_cash_ok', 'cover'): (1, 'Không thiếu gì mà vẫn bỏ tiền túi vào két, sổ lại lệch.', 'bỏ tiền túi vào két không cần thiết', False),
    ('ac_story4_ok', 'force'): (2, 'Két khớp rồi mà vẫn sửa số trên sổ quỹ, cô chẳng hiểu vì sao.', 'sửa sổ quỹ không có lý do', False),
    ('ac_story4_ok', 'minutes'): (1, 'Két khớp từng xu mà vẫn lập biên bản, cô phải ký cho xong.', 'lập biên bản không cần thiết', False),
    ('ac_story4_ok', 'cover'): (1, 'Không thiếu gì mà vẫn bỏ tiền túi vào két, sổ lại lệch.', 'bỏ tiền túi vào két không cần thiết', False),
    ('ac_payee', 'pay'): (3, 'Thư lạ giục chuyển gấp mà tiền vẫn đi vào tài khoản lạ, giờ đòi lại khó lắm.', 'chuyển tiền theo thư giả', False),
    ('ac_supplier', 'reply'): (2, 'Sao kê ghi rõ chuyển hai lần mà bên tiệm lại bảo không có gì trùng.', 'bỏ sót khoản chuyển trùng', False),
    ('ac_supplier', 'ignore'): (1, 'Bên em báo tiệm trả thừa mà chẳng ai trả lời.', 'không trả lời đối tác', False),
    ('ac_supplier_ok', 'claim'): (2, 'Tiệm đòi lại một khoản không hề trả thừa, bên em phải gửi lại hóa đơn giải thích.', 'đòi một khoản không trả thừa', False),
    ('ac_supplier_ok', 'ignore'): (1, 'Hỏi một câu mà chẳng ai trả lời, phải gọi điện hỏi lại.', 'không trả lời đối tác', False),
    ('ac_audit', 'excuse'): (2, 'Dòng sửa quỹ không ghi lý do mà chỉ giải thích miệng cho qua.', 'giải thích cho qua thay vì bổ sung', False),
    ('ac_story1', 'post'): (2, 'Tiền áo đồng phục cho con lẫn vào chi phí tiệm, cô cứ tưởng tuần này lỗ.', 'lẫn chi tiêu riêng vào sổ tiệm', False),
    ('ac_story2', 'comply'): (2, 'Cô nhờ bỏ bớt đơn tiền mặt mà cháu làm theo ngay, giờ nghĩ lại cô thấy chột dạ.', 'bỏ bớt doanh thu khỏi sổ', False),
    ('ac_story3', 'pay'): (2, 'Cô nộp một khoản không cần nộp mà tiền cọc vẫn chưa được giải thích.', 'nộp tiền thay vì giải trình', False),
    ('ac_story3', 'ignore'): (2, 'Thư của cơ quan thuế quá hạn trả lời, cô nhận thêm một thư nhắc.', 'để quá hạn trả lời thư thuế', False),
    # customer care: the wrong fix, the wrong person, the wrong words in public
    ('cs_wrong', 'deny'): (3, 'Ảnh với đơn rõ ràng là giao sai màu mà trạm vẫn từ chối đổi cho mình.', 'từ chối đổi món giao sai', False),
    ('cs_wrong', 'explain'): (2, 'Mình cần đúng hộp xanh, trạm chỉ giải thích vòng vo.', 'giải thích thay vì đổi đúng món', False),
    ('cs_wrong', 'reship'): (1, 'Gửi thêm hộp mà chẳng ai hẹn lấy hộp hồng về, mình không biết xử lý sao.', 'gửi bù mà không thu hàng sai', False),
    ('cs_lost', 'deny'): (3, 'Mình chưa nhận được hàng mà trạm cứ bảo hệ thống ghi đã giao.', 'từ chối khi chưa đối soát', False),
    ('cs_lost', 'explain'): (2, 'Giải thích mãi mà kiện hàng vẫn chẳng thấy đâu.', 'giải thích thay vì đối soát', False),
    ('cs_lost', 'refund'): (2, 'Mình nhận lại tiền nhưng món quà sinh nhật thì không kịp nữa.', 'hoàn tiền thay vì tìm kiện', False),
    ('cs_double', 'refund'): (2, 'Trạm hoàn tay thêm một lần, ba hôm sau tiền lại tự về, giờ mình phải trả lại.', 'hoàn tay khoản giữ tạm', False),
    ('cs_double', 'deny'): (2, 'Trạm bảo không có gì sai mà chẳng nói tiền sẽ tự về, mình lo cả tối.', 'từ chối mà không giải thích', False),
    ('cs_window', 'exchange'): (1, 'Đổi được thì vui, nhưng lần sau chẳng biết trạm theo quy định nào.', 'đổi hàng quá hạn', False),
    ('cs_window', 'refund'): (2, 'Được hoàn cả tiền món quá hạn, chị Mai phải gọi lại giải trình với mình.', 'hoàn tiền món quá hạn', False),
    ('cs_fraud', 'refund'): (3, 'Tấm ảnh chụp từ trước lúc nhận hàng mà trạm vẫn hoàn tiền ngay.', 'hoàn tiền theo ảnh cũ', False),
    ('cs_fraud', 'reship'): (2, 'Tấm ảnh chụp từ trước lúc nhận hàng mà trạm vẫn gửi món mới đi.', 'gửi hàng theo ảnh cũ', False),
    ('cs_fraud_ok', 'deny'): (3, 'Mình nhận hộp vỡ thật mà bị từ chối như kẻ gian.', 'từ chối khách nhận hàng vỡ thật', False),
    ('cs_takeover', 'refund'): (3, 'Tiền hoàn của tôi bị chuyển vào một tài khoản lạ chỉ vì một tin nhắn chat.', 'hoàn tiền vào tài khoản lạ', False),
    ('cs_takeover', 'deny'): (2, 'Trạm từ chối nhưng không khóa, kẻ lạ vẫn ở trong tài khoản tôi thêm mấy giờ.', 'không khóa tài khoản bị chiếm', False),
    ('cs_angry', 'deny'): (3, 'Trạm tự hứa rồi lỡ hẹn, giờ còn từ chối luôn.', 'từ chối sau khi lỡ hẹn', False),
    ('cs_angry', 'explain'): (2, 'Lỡ hẹn với tôi rồi mà giờ chỉ giải thích, chẳng làm gì thêm.', 'giải thích thay vì sửa lời hẹn', False),
    ('cs_story1', 'deny'): (3, 'Trạm tự hứa rồi lỡ hẹn, giờ còn từ chối luôn.', 'từ chối sau khi lỡ hẹn', False),
    ('cs_story1', 'explain'): (2, 'Lỡ hẹn với tôi rồi mà giờ chỉ giải thích, chẳng làm gì thêm.', 'giải thích thay vì sửa lời hẹn', False),
    ('cs_vip', 'deny'): (2, 'Tôi chỉ cần biết hàng đang ở đâu mà bị từ chối.', 'từ chối khách hỏi đơn', False),
    ('cs_vip', 'refund'): (2, 'Hoàn tiền thì quà vẫn không kịp sinh nhật con.', 'hoàn tiền thay vì báo mốc giao', False),
    ('cs_vip', 'reship'): (1, 'Kiện cũ vẫn đang tới mà lại gửi thêm kiện mới, rối cả lên.', 'gửi thêm kiện không cần thiết', False),
    ('cs_viral', 'detail'): (3, 'Trạm đăng cả chi tiết đơn của khách lên mạng để cãi, lộ hết thông tin.', 'đăng thông tin đơn của khách', False),
    ('cs_viral', 'hide'): (2, 'Trạm ẩn bài chê đi, ảnh chụp màn hình còn lan nhanh hơn.', 'ẩn bài chê thay vì trả lời', False),
    ('cs_threat', 'refund'): (2, 'Cứ dọa là được hoàn tiền, tuần sau lại có người gọi y hệt.', 'hoàn tiền vì bị dọa', False),
    ('cs_threat', 'explain'): (2, 'Người ta dọa tới tận kho mà chỉ giải thích chính sách, Duy run cả chiều.', 'không chuyển trưởng ca khi bị dọa', False),
    ('cs_threat', 'deny'): (2, 'Từ chối cứng khiến cuộc gọi căng hơn, Duy phải khóa cửa kho.', 'không chuyển trưởng ca khi bị dọa', False),
    ('cs_story2', 'lock'): (2, 'Mình chỉ nhờ đổi địa chỉ mà trạm khóa luôn đơn.', 'khóa đơn không cần thiết', False),
    ('cs_story2', 'deny'): (2, 'Trạm từ chối mà không chỉ cách xác minh, mình phải nhắn lại từ đầu.', 'từ chối mà không hướng dẫn', False),
    ('cs_story3', 'favor'): (2, 'Mình nhờ là được đẩy đơn lên ngay, người chờ trước chắc chẳng vui.', 'ưu tiên vì quen biết', False),
}
# A case with nothing wrong in it, stamped the wrong way.
CLEAN_SLIPS = {
    'pharmacy': {
        'refuse': (2, 'Phiếu của tôi đủ cả mà quầy không giao, tôi phải quay lại hỏi cho ra lẽ.', 'từ chối yêu cầu hợp lệ', False),
        'fix': (1, 'Khay đúng rồi mà cứ đổi qua đổi lại, tôi đứng chờ mãi.', 'đổi hộp không cần thiết', False),
        'refer': (1, 'Mọi thứ đủ cả mà vẫn phải chờ gọi cô Thu ra xem.', 'chuyển người khác không cần thiết', False),
    },
    'accounting': {
        'adjust': (2, 'Sổ đúng rồi mà bị sửa một dòng, chị Vân phải gỡ lại.', 'sửa dòng vốn đã đúng', False),
        'hold': (1, 'Sổ đủ chứng từ mà vẫn bị giữ lại, tôi phải chờ thêm một ngày.', 'giữ sổ không cần thiết', False),
        'report': (1, 'Sổ ổn cả mà vẫn phải chờ chị Vân xem lại.', 'đẩy việc tự làm được', False),
    },
    'customer_care': {
        'refund': (2, 'Mình có đòi hoàn gì đâu mà trạm tự hoàn tiền, giờ đơn rối tung.', 'hoàn tiền khi khách không cần', False),
        'trace': (1, 'Mình chỉ hỏi chỗ xem đơn mà bị mở đối soát, chờ mãi chẳng ai chỉ.', 'mở đối soát không cần thiết', False),
        'escalate': (1, 'Câu hỏi đơn giản mà phải chờ chuyển người khác trả lời.', 'chuyển người khác không cần thiết', False),
    },
}
# Anything not listed above: a clear mistake in plain words.
OTHER_SLIP = {
    'pharmacy': (2, 'Quầy xử lý phiếu của tôi không đúng cách, tôi phải quay lại lần nữa.', 'xử lý phiếu chưa đúng', False),
    'accounting': (1, 'Việc tự sửa được mà vẫn phải chờ chị Vân xem giúp.', 'đẩy việc tự làm được', False),
    'customer_care': (1, 'Việc trạm tự xử lý được mà mình vẫn phải chờ chuyển người khác.', 'chuyển người khác không cần thiết', False),
}
# The right stamp, taken before the check that makes it right.
BLIND_SLIPS = {
    'accounting': (2, 'Tiền chuyển đi khi chưa gọi số trong hồ sơ xác minh, thư giả cũng trông y như vậy.', 'chuyển tiền khi chưa xác minh', False),
    'customer_care': (2, 'Trạm đổi thông tin đơn khi chưa gọi số đã đăng ký, lỡ không phải mình thì sao.', 'đổi đơn khi chưa xác minh', False),
    'pharmacy': (2, 'Quầy giao khi chưa kiểm xong, may mà không sao.', 'giao khi chưa kiểm', False),
}
LATE_REPLY_SLIP = ('late_reply', 1, 'Mình nhắn mãi, quá hạn rồi mới có người trả lời.', 'trả lời quá hạn', False)


def slip_key(variant: str, case: dict) -> str:
    return variant + (str(case['chapter']) if case.get('chapter') else '') + ('' if case['issues'] else '_ok')


def slip_for(career: str, variant: str, case: dict, verdict: str, blind: bool = False):
    """(code, sev, text, note, safety) for a wrong stamp, or None when the stamp was right."""
    if blind:
        return ('blind_' + verdict, *BLIND_SLIPS[career])
    if case['accept'].get(verdict):
        return None
    row = SLIPS.get((slip_key(variant, case), verdict))
    if row is None and not case['issues']:
        row = CLEAN_SLIPS[career].get(verdict)
    return (f'{verdict}_{variant}'[:32], *(row or OTHER_SLIP[career]))
