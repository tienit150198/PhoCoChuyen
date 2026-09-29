"""Dịch vụ Thuế & Tiền lương Minh Bạch — an employed payroll & tax clerk (plugin career).

Real work of the job, step by step and checked like a spreadsheet: read the
contract and timesheet → classify overtime → gross pay → employee insurance →
personal income tax with family deductions → net pay → send the payslip
privately; cross-check the bank transfer file against approved payslips; sort
valid and invalid purchase invoices for the quarterly VAT return; keep the
filing calendar (holidays, late interest); answer an employee's "why is my pay
lower?"; prepare year-end PIT finalisation.

Every rate, bracket and deadline here is a simplified GAME rule written in xu,
not tax or legal advice. The legacy `accounting` career reconciles source
documents against transactions; this one computes payroll and tax filings.
"""
from __future__ import annotations
import copy
import unicodedata
from . import kit, office
from .corp_accounting import (care_can_overtime, care_close, care_ensure, care_handle, care_public, care_rel, care_slow, care_start,
                              care_validate, care_validate_task)
from .. import consequences as cq
from .. import procedures
from .. import archive as ar

ID = 'tax_payroll'

# ------------------------------------------------------------------ game rules
STD_DAYS, STD_HOURS = 26, 8
OT_RATES = {'r150': 150, 'r200': 200, 'r300': 300}
INS = dict(bhxh=80, bhyt=15, bhtn=10)            # per mille of the contract insurance salary
PERSONAL, DEPENDENT, LUNCH_CAP = 5000, 2000, 700
BRACKETS = [(2000, 5), (5000, 10), (10000, 15), (None, 20)]   # monthly, ×12 for a year
LATE_PER_DAY = 3                                   # per 10.000 (0,03%/ngày)
CASH_LIMIT = 200

RULES = [
    dict(group='Lương', emoji='🕒', lines=[
        'Công chuẩn: 26 ngày × 8 giờ. Lương ngày = lương giờ × 8.',
        'Nghỉ phép năm có duyệt vẫn hưởng lương; chỉ nghỉ không lương mới bị trừ.',
        'Tăng ca = lương giờ × số giờ × hệ số: ngày thường 150%, ngày nghỉ hằng tuần (Chủ nhật) 200%, ngày lễ 300%.',
        'Tổng thu nhập = lương cơ bản − nghỉ không lương + phụ cấp + tăng ca.']),
    dict(group='Bảo hiểm (phần người lao động)', emoji='🛡️', lines=[
        'Tính trên “lương đóng bảo hiểm” ghi trong hợp đồng, không phải tổng thu nhập.',
        'BHXH 8% · BHYT 1,5% · BHTN 1%.']),
    dict(group='Thuế TNCN', emoji='🧾', lines=[
        'Thu nhập tính thuế = tổng thu nhập − ăn trưa được miễn (tối đa 700) − bảo hiểm − giảm trừ bản thân 5.000 − 2.000 × người phụ thuộc ĐÃ đăng ký.',
        'Biểu lũy tiến tháng: tới 2.000 → 5% · 2.000–5.000 → 10% · 5.000–10.000 → 15% · trên 10.000 → 20%. Quyết toán năm: nhân mốc × 12.',
        'Thực lĩnh = tổng thu nhập − bảo hiểm − thuế. Mọi phép chia làm tròn xuống tới xu.']),
    dict(group='Thuế GTGT', emoji='🧮', lines=[
        'Thuế phải nộp = thuế đầu ra − thuế đầu vào hợp lệ.',
        'Không khấu trừ: hóa đơn thiếu mã của cơ quan thuế, chi cho việc riêng, nhà cung cấp đã ngừng hoạt động trước ngày hóa đơn, hóa đơn từ 200 xu trở lên trả tiền mặt.']),
    dict(group='Hạn nộp', emoji='📅', lines=[
        'Thuế TNCN khai theo tháng: ngày 20 tháng sau · GTGT theo quý: ngày cuối của tháng đầu quý sau.',
        'Bảo hiểm: cuối tháng · Lệ phí môn bài: 30/1 · Quyết toán năm: 31/3 năm sau.',
        'Hạn rơi vào ngày nghỉ lễ → lùi sang ngày làm việc đầu tiên sau kỳ nghỉ.',
        'Nộp tiền chậm: lãi 0,03% mỗi ngày trên số thuế chậm nộp, làm tròn xuống.']),
]
DISCLAIMER = 'Mọi số tiền tính bằng xu.'


def pit(x: int, months: int = 1) -> int:
    """Progressive personal income tax (game table), rounded down."""
    tax100, low = 0, 0
    for top, rate in BRACKETS:
        high = None if top is None else top * months
        if x <= low:
            break
        tax100 += ((x if high is None else min(x, high)) - low) * rate
        if high is None:
            break
        low = high
    return tax100 // 100


def insurance(ins_sal: int) -> dict:
    return {k: ins_sal * v // 1000 for k, v in INS.items()}


def fmt(n: int) -> str:
    return f'{n:,}'.replace(',', '.')


def xu(n: int) -> str:
    return fmt(n) + ' xu'


def holder(name: str) -> str:
    """Bank account holder style: upper case, no Vietnamese accents."""
    raw = unicodedata.normalize('NFD', name.replace('đ', 'd').replace('Đ', 'D'))
    return ''.join(ch for ch in raw if unicodedata.category(ch) != 'Mn').upper()


def _shuffled(rng, rows: list) -> list:
    rows = list(rows)
    rng.shuffle(rows)
    return rows


WORKERS = [('Nguyễn Thị Diệu', 'Công nhân may'), ('Trần Minh Khôi', 'Kỹ thuật viên bảo trì'), ('Lê Văn Tài', 'Thợ cắt vải'),
           ('Phạm Thị Hoa', 'Tổ trưởng chuyền'), ('Đỗ Quang Vinh', 'Nhân viên kho'), ('Vũ Thị Lan', 'Công nhân là ủi'),
           ('Hoàng Minh Tâm', 'Tài xế giao hàng'), ('Bùi Thu Trang', 'Nhân viên QC')]
STRANGERS = ['Ngô Văn Thịnh', 'Lý Thị Mận', 'Châu Gia Bảo']
OT_WEEKDAY = [('Thứ Ba 10/9 · 18:00–20:00', 2), ('Thứ Năm 12/9 · 17:30–20:30', 3), ('Thứ Sáu 20/9 · 18:00–20:00', 2)]
OT_WEEKEND = [('Chủ nhật 15/9 · 08:00–12:00', 4), ('Chủ nhật 22/9 · 13:00–16:00', 3)]
OT_HOLIDAY = [('Thứ Hai 2/9 (Quốc khánh) · 08:00–11:00', 3), ('Thứ Hai 2/9 (Quốc khánh) · 13:00–15:00', 2)]
RATE_OPTIONS = [dict(id='r150', label='Ngày thường · 150%'), dict(id='r200', label='Ngày nghỉ hằng tuần · 200%'),
                dict(id='r300', label='Ngày lễ · 300%')]


def _pay(h: int, unpaid: int, lunch: int, resp: int, phone: int, deps: int, ot_hours: list) -> dict:
    """Full payslip arithmetic from game rules. ot_hours: [(hours, rate_id), ...]."""
    base, day_rate = h * STD_HOURS * STD_DAYS, h * STD_HOURS
    ins_sal = base - base % 200
    ot = sum(h * hrs * OT_RATES[r] // 100 for hrs, r in ot_hours)
    leave = unpaid * day_rate
    gross = base - leave + lunch + resp + phone + ot
    ins = insurance(ins_sal)
    ins_total = sum(ins.values())
    taxable = max(0, gross - min(lunch, LUNCH_CAP) - ins_total - PERSONAL - DEPENDENT * deps)
    tax = pit(taxable)
    return dict(base=base, day_rate=day_rate, ins_sal=ins_sal, ot=ot, leave=leave, gross=gross, ins=ins, ins_total=ins_total,
                taxable=taxable, pit=tax, net=gross - ins_total - tax)


# ------------------------------------------------------------------ task forms
def _payslip(rng) -> dict:
    name, role = rng.choice(WORKERS)
    first = name.split()[-1]
    h = rng.choice([30, 40, 50, 60])
    unpaid, annual = rng.choice([0, 1, 1, 2]), rng.choice([0, 1])
    lunch, resp, phone = rng.choice([600, 700, 800]), rng.choice([0, 0, 500]), rng.choice([0, 200])
    deps, pending = rng.choice([0, 1, 1, 2]), rng.random() < .6
    lines = _shuffled(rng, [(*rng.choice(OT_WEEKDAY), 'r150'), (*rng.choice(OT_WEEKEND), 'r200'), (*rng.choice(OT_HOLIDAY), 'r300')])
    p = _pay(h, unpaid, lunch, resp, phone, deps, [(hrs, r) for _, hrs, r in lines])
    left = [dict(id=f'ot{i + 1}', label=f'{txt} · {hrs} giờ') for i, (txt, hrs, _) in enumerate(lines)]
    ot_key = {f'ot{i + 1}': r for i, (_, _, r) in enumerate(lines)}
    rows = [['Tháng 9', 'Công chuẩn (thứ Hai – thứ Bảy)', f'{STD_DAYS} ngày']]
    if annual:
        rows.append(['Thứ Tư 18/9', 'Nghỉ phép năm (có lương, đã duyệt)', '1 ngày'])
    for d in ['Thứ Sáu 27/9', 'Thứ Bảy 28/9'][:unpaid]:
        rows.append([d, 'Nghỉ việc riêng KHÔNG lương', '1 ngày'])
    rows += [[txt, 'Tăng ca có phiếu duyệt', f'{hrs} giờ'] for txt, hrs, _ in lines]
    papers = [
        dict(id='contract', title='Hợp đồng lao động (trích)', kind='kv', rows=[
            ['Người lao động', name], ['Vị trí', role], ['Lương giờ', xu(h)],
            ['Lương cơ bản tháng', f'{xu(p["base"])} (26 ngày × 8 giờ)'], ['Lương đóng bảo hiểm', xu(p['ins_sal'])],
            ['Phụ cấp ăn trưa', xu(lunch)], ['Phụ cấp trách nhiệm', xu(resp)], ['Phụ cấp điện thoại', xu(phone)],
            ['Người phụ thuộc đã đăng ký', f'{deps} người']], note='Xưởng may Chỉ Vàng · kỳ lương tháng 9'),
        dict(id='timesheet', title='Bảng chấm công tháng 9', kind='table', head=['Ngày', 'Nội dung', 'Số lượng'], rows=rows,
             note='Tổ trưởng và người lao động đã ký xác nhận.'),
        dict(id='hr', title='Ghi chú nhân sự', kind='kv', rows=[
            ['Người phụ thuộc', f'{first} đang chuẩn bị hồ sơ cho mẹ — CHƯA nộp, chưa được tính.' if pending else 'Không có thay đổi trong tháng.'],
            ['Nhắc việc', 'Phiếu lương là thông tin riêng của từng người.']]),
    ]
    steps = [
        procedures.step('ot', 'match', 'Phân loại giờ tăng ca', 'Xếp từng dòng tăng ca vào đúng hệ số.', ot_key,
                        left=left, right=copy.deepcopy(RATE_OPTIONS),
                        hints=['Thứ Hai – thứ Bảy là ngày làm việc thường; Chủ nhật là ngày nghỉ hằng tuần; dòng có ghi chú lễ là ngày lễ.',
                               'Nhìn kỹ thứ trong tuần và ghi chú trong ngoặc của từng dòng.'],
                        explain='Tăng ca: ' + ' + '.join(f'{hrs} giờ × {h} × {OT_RATES[r]}%' for _, hrs, r in lines) + f' = {xu(p["ot"])}.'),
        procedures.step('gross', 'fields', 'Tổng thu nhập', 'Điền từng ô theo hợp đồng và bảng chấm công (đơn vị xu).',
                        dict(day_rate=p['day_rate'], leave=p['leave'], ot=p['ot'], gross=p['gross']),
                        fields=[dict(id='day_rate', label='Lương 1 ngày'), dict(id='leave', label='Trừ nghỉ không lương'),
                                dict(id='ot', label='Tiền tăng ca'), dict(id='gross', label='Tổng thu nhập')],
                        hints=['Lương ngày = lương giờ × 8. Nghỉ phép năm vẫn có lương; chỉ ngày KHÔNG lương mới trừ.',
                               'Tổng thu nhập = lương cơ bản − nghỉ không lương + ăn trưa + trách nhiệm + điện thoại + tăng ca.'],
                        explain=f'{xu(p["base"])} − {xu(p["leave"])} + {xu(lunch + resp + phone)} phụ cấp + {xu(p["ot"])} tăng ca = {xu(p["gross"])}.'),
        procedures.step('ins', 'fields', 'Bảo hiểm người lao động đóng', 'Tính ba khoản bảo hiểm trừ vào lương.',
                        dict(p['ins']),
                        fields=[dict(id='bhxh', label='BHXH 8%'), dict(id='bhyt', label='BHYT 1,5%'), dict(id='bhtn', label='BHTN 1%')],
                        hints=['Bảo hiểm tính trên “lương đóng bảo hiểm” trong hợp đồng — không phải tổng thu nhập.',
                               'Lấy lương đóng bảo hiểm nhân tỷ lệ; 1,5% nghĩa là × 15 ÷ 1000.'],
                        explain=f'Trên {xu(p["ins_sal"])}: BHXH {fmt(p["ins"]["bhxh"])} + BHYT {fmt(p["ins"]["bhyt"])} + BHTN {fmt(p["ins"]["bhtn"])} = {xu(p["ins_total"])}.'),
        procedures.step('tax', 'fields', 'Thuế thu nhập cá nhân', 'Tính thu nhập tính thuế rồi áp biểu lũy tiến tháng.',
                        dict(taxable=p['taxable'], pit=p['pit']),
                        fields=[dict(id='taxable', label='Thu nhập tính thuế'), dict(id='pit', label='Thuế TNCN')],
                        hints=['Trừ: ăn trưa được miễn (tối đa 700), bảo hiểm, bản thân 5.000, và 2.000 cho mỗi người phụ thuộc ĐÃ đăng ký — hồ sơ chưa nộp chưa được tính.',
                               'Lũy tiến: phần tới 2.000 chịu 5%, phần 2.000–5.000 chịu 10%, phần 5.000–10.000 chịu 15%, phần trên 10.000 chịu 20%. Làm tròn xuống.'],
                        explain=f'{xu(p["gross"])} − {fmt(min(lunch, LUNCH_CAP))} ăn trưa − {fmt(p["ins_total"])} bảo hiểm − {fmt(PERSONAL)} bản thân − {fmt(DEPENDENT * deps)} người phụ thuộc = {xu(p["taxable"])} → thuế {xu(p["pit"])}.'),
        procedures.step('net', 'number', 'Thực lĩnh', f'Số tiền chuyển vào tài khoản của {first} là bao nhiêu?', p['net'],
                        hints=['Thực lĩnh = tổng thu nhập − bảo hiểm − thuế. Phụ cấp đã nằm trong tổng thu nhập rồi, đừng cộng lần nữa.'],
                        explain=f'{xu(p["gross"])} − {xu(p["ins_total"])} − {xu(p["pit"])} = {xu(p["net"])}.'),
        procedures.step('send', 'choice', 'Gửi phiếu lương', f'Gửi phiếu lương tháng 9 cho {first} bằng cách nào?', 'private',
                        options=_shuffled(rng, [dict(id='private', label=f'Gửi riêng vào email công việc của {first}, tệp có mật khẩu'),
                                                dict(id='group', label='Đăng bảng lương cả xưởng lên nhóm chat cho “minh bạch”'),
                                                dict(id='board', label='In dán lên bảng tin ở căng tin')]),
                        hints=['Phiếu lương là thông tin cá nhân: chỉ người nhận (và bộ phận được giao) được xem.'], tag='ethic',
                        explain='Lương là dữ liệu riêng tư. Minh bạch là minh bạch cách tính, không phải công khai lương từng người.'),
    ]
    return dict(npc=1, title=f'Phiếu lương tháng 9 của {first}',
                opening=f'Em tính giùm anh phiếu lương tháng 9 cho {first} nha, chấm công tổ trưởng gửi rồi đó.',
                brief=f'Tính phiếu lương tháng 9 cho {name} ({role.lower()}): tăng ca, tổng thu nhập, bảo hiểm, thuế, thực lĩnh; rồi gửi phiếu đúng cách.',
                papers=papers, steps=steps)


def _transfer(rng) -> dict:
    people = rng.sample(WORKERS, 5)
    staff, gone = people[:4], people[4]
    nets = [rng.randrange(60, 160) * 100 + rng.randrange(0, 100) for _ in staff]
    accounts = [str(rng.randrange(10 ** 9, 10 ** 10)) for _ in people]
    errors = rng.sample(['swap', 'resigned', 'name', 'acct'], 2)
    rows = [dict(holder=holder(n), acct=accounts[i], amount=nets[i], bad=False, why='') for i, (n, _) in enumerate(staff)]
    victims = rng.sample(range(4), 3)
    for e in errors:
        if e == 'swap':
            i = victims.pop()
            r = rows[i]
            s = str(r['amount'])
            j = next((k for k in range(len(s) - 1) if s[k] != s[k + 1]), None)
            r['amount'] = int(s[:j] + s[j + 1] + s[j] + s[j + 2:]) if j is not None else r['amount'] + 9
            r.update(bad=True, why=f'số tiền {fmt(r["amount"])} bị đảo chữ số, bảng lương duyệt là {fmt(nets[i])}')
        elif e == 'name':
            r = rows[victims.pop()]
            r.update(holder=holder(rng.choice(STRANGERS)), bad=True, why='tên chủ tài khoản không phải người lao động')
        elif e == 'acct':
            r = rows[victims.pop()]
            a = r['acct']
            r.update(acct=a[:-2] + a[-1] + a[-2] if a[-1] != a[-2] else a[:-1] + str((int(a[-1]) + 1) % 10), bad=True,
                     why='số tài khoản khác hồ sơ nhân sự')
        else:
            rows.append(dict(holder=holder(gone[0]), acct=accounts[4], amount=rng.randrange(60, 120) * 100, bad=True,
                             why=f'{gone[0]} đã nghỉ việc từ 31/8'))
    rows = _shuffled(rng, rows)
    for i, r in enumerate(rows):
        r['id'] = f'b{i + 1}'
    total = sum(nets)
    papers = [
        dict(id='payroll', title='Bảng lương tháng 9 đã duyệt', kind='table', head=['Họ tên', 'Thực lĩnh'],
             rows=[[n, xu(nets[i])] for i, (n, _) in enumerate(staff)] + [['Tổng cộng', xu(total)]],
             note='Kế toán trưởng Hồng đã ký duyệt.'),
        dict(id='hr', title='Hồ sơ tài khoản nhân sự', kind='table', head=['Họ tên', 'Số tài khoản', 'Tình trạng'],
             rows=[[n, accounts[i], 'Đang làm' if i < 4 else 'Nghỉ việc từ 31/8'] for i, (n, _) in enumerate(people)]),
        dict(id='bank', title='File chuyển lương nháp (ngân hàng)', kind='table', head=['Dòng', 'Chủ tài khoản', 'Số tài khoản', 'Số tiền'],
             rows=[[r['id'].upper(), r['holder'], r['acct'], fmt(r['amount'])] for r in rows],
             note=f'Tổng file nháp: {xu(sum(r["amount"] for r in rows))}'),
    ]
    bad = sorted(r['id'] for r in rows if r['bad'])
    steps = [
        procedures.step('errors', 'multi', 'Soát file chuyển lương', 'Đánh dấu mọi dòng trong file nháp cần sửa hoặc xóa.', bad,
                        options=[dict(id=r['id'], label=f'{r["id"].upper()} · {r["holder"]} · {fmt(r["amount"])}') for r in rows],
                        hints=['Đối chiếu từng dòng với CẢ bảng lương đã duyệt (số tiền) và hồ sơ nhân sự (tên, số tài khoản, tình trạng).',
                               'Có đúng hai dòng lỗi. Soi kỹ chữ số bị đảo và người đã nghỉ việc.'],
                        explain='Dòng lỗi: ' + '; '.join(f'{r["id"].upper()} — {r["why"]}' for r in rows if r['bad']) + '.'),
        procedures.step('total', 'number', 'Tổng tiền chuyển', 'Sau khi sửa, tổng tiền lệnh chuyển lương phải là bao nhiêu?', total,
                        hints=['Tổng lệnh chuyển phải bằng tổng thực lĩnh trên bảng lương ĐÃ DUYỆT, không phải tổng file nháp.'],
                        explain=f'Khớp bảng lương đã duyệt: {xu(total)}.'),
        procedures.step('approve', 'choice', 'Duyệt lệnh chuyển', 'File đã sửa. Bước duyệt tiếp theo là gì?', 'dual',
                        options=_shuffled(rng, [dict(id='dual', label='Gửi file cho kế toán trưởng soát, giám đốc tự ký duyệt trên ngân hàng số'),
                                                dict(id='self', label='Mượn mật khẩu của giám đốc để tự duyệt cho kịp giờ'),
                                                dict(id='chat', label='Gửi file qua tin nhắn cá nhân để giám đốc tự gõ lại từng dòng')]),
                        hints=['Người lập lệnh không tự duyệt lệnh của mình; mật khẩu duyệt chỉ chủ tài khoản giữ.'], tag='ethic',
                        explain='Hai người, hai bước: người lập và người duyệt tách riêng — nguyên tắc chống sai sót và gian lận.'),
    ]
    return dict(npc=0, title='Soát file chuyển lương tháng 9',
                opening='Em soát file chuyển lương giùm chị, chiều nay ngân hàng chốt lệnh rồi. Chị thấy tổng hơi lạ.',
                brief='Đối chiếu file chuyển lương nháp với bảng lương đã duyệt và hồ sơ tài khoản; tìm dòng sai, chốt tổng tiền, chuyển đúng quy trình duyệt.',
                papers=papers, steps=steps)


def _vat(rng) -> dict:
    q = rng.choice([1, 2, 3, 4])
    months = {1: 'tháng 1–3', 2: 'tháng 4–6', 3: 'tháng 7–9', 4: 'tháng 10–12'}[q]
    mo = [3 * (q - 1) + k for k in (1, 2, 3)]
    sales = [dict(no=f'BR-{q}0{k + 1}', what=w, amount=rng.randrange(120, 260) * 100, rate=10)
             for k, w in enumerate(['Doanh thu đồ uống tại quán', 'Doanh thu bánh ngọt', 'Tiệc sinh nhật trọn gói'])]
    valid = [dict(sup='HTX Cà phê Đồi Mây', what='Cà phê hạt rang', amount=rng.randrange(60, 110) * 100, rate=5, pay='Chuyển khoản', note='Mã CQT: có'),
             dict(sup='Công ty Sữa Đồng Xanh', what='Sữa tươi, kem béo', amount=rng.randrange(30, 60) * 100, rate=10, pay='Chuyển khoản', note='Mã CQT: có'),
             dict(sup='Tạp hóa Bà Sáu', what='Ly giấy, ống hút giấy', amount=150, rate=10, pay='Tiền mặt', note='Mã CQT: có · tổng dưới 200')]
    bad_pool = dict(
        no_code=dict(sup='Cửa hàng Điện máy Hòa Bình', what='Quạt treo tường', amount=900, rate=10, pay='Chuyển khoản',
                     note='Mã CQT: (trống)', why='hóa đơn thiếu mã của cơ quan thuế'),
        cash=dict(sup='Công ty Thiết bị Pha Chế Việt', what='Máy xay cà phê', amount=1800, rate=10, pay='Tiền mặt',
                  note='Mã CQT: có', why='từ 200 xu trở lên mà trả tiền mặt'),
        personal=dict(sup='Siêu thị Điện máy Sao Mai', what='Tivi 55 inch — giao tới nhà riêng Chú Bảy', amount=1200, rate=10,
                      pay='Chuyển khoản', note='Mã CQT: có', why='chi cho việc riêng, không phục vụ kinh doanh'),
        closed=dict(sup='Công ty TNHH Gió Lạ', what='Dịch vụ sửa máy lạnh', amount=600, rate=10, pay='Chuyển khoản',
                    note='Tra cứu: ngừng hoạt động trước ngày xuất hóa đơn', why='người bán đã ngừng hoạt động'),
    )
    bad_ids = rng.sample(sorted(bad_pool), 2)
    purchases = _shuffled(rng, [dict(v, bad=False, why='') for v in valid] + [dict(bad_pool[k], bad=True) for k in bad_ids])
    for i, r in enumerate(purchases):
        r['id'] = f'p{i + 1}'
        r['no'] = f'MV-{q}{i + 1:02d}'
        r['vat'] = r['amount'] * r['rate'] // 100
        r['date'] = f'{rng.randrange(3, 27)}/{mo[i % 3]}'
    for s in sales:
        s['vat'] = s['amount'] * s['rate'] // 100
    out_vat = sum(s['vat'] for s in sales)
    in_vat = sum(r['vat'] for r in purchases if not r['bad'])
    deadline = {1: 'd30_4', 2: 'd31_7', 3: 'd31_10', 4: 'd31_1'}[q]
    papers = [
        dict(id='sales', title=f'Hóa đơn bán ra quý {q} ({months})', kind='table', head=['Số HĐ', 'Nội dung', 'Tiền hàng', 'Thuế suất', 'Thuế GTGT'],
             rows=[[s['no'], s['what'], fmt(s['amount']), f'{s["rate"]}%', fmt(s['vat'])] for s in sales]),
        dict(id='purchases', title=f'Hóa đơn mua vào quý {q}', kind='table',
             head=['Dòng', 'Ngày', 'Người bán', 'Hàng hóa', 'Tiền hàng', 'Thuế GTGT', 'Thanh toán', 'Ghi chú'],
             rows=[[r['id'].upper(), r['date'], r['sup'], r['what'], fmt(r['amount']), fmt(r['vat']), r['pay'], r['note']] for r in purchases],
             note='Chú Bảy gom cả hộp hóa đơn, có tờ lẫn cả đồ nhà.'),
    ]
    steps = [
        procedures.step('invalid', 'multi', 'Loại hóa đơn không được khấu trừ', 'Đánh dấu các hóa đơn mua vào KHÔNG được khấu trừ thuế.',
                        sorted(r['id'] for r in purchases if r['bad']),
                        options=[dict(id=r['id'], label=f'{r["id"].upper()} · {r["what"]} · {fmt(r["amount"] + r["vat"])} ({r["pay"].lower()})') for r in purchases],
                        hints=['Soát bốn điều: có mã cơ quan thuế không, phục vụ kinh doanh không, người bán còn hoạt động không, từ 200 xu có trả tiền mặt không.',
                               'Hóa đơn nhỏ dưới 200 xu trả tiền mặt vẫn hợp lệ. Có đúng hai hóa đơn bị loại.'],
                        explain='Bị loại: ' + '; '.join(f'{r["id"].upper()} — {r["why"]}' for r in purchases if r['bad']) + '.'),
        procedures.step('vat', 'fields', 'Thuế đầu ra, đầu vào', 'Cộng thuế GTGT trên hóa đơn (không tính lại tiền hàng).',
                        dict(output=out_vat, input=in_vat),
                        fields=[dict(id='output', label='Thuế GTGT đầu ra'), dict(id='input', label='Thuế GTGT đầu vào được khấu trừ')],
                        hints=['Đầu ra: cộng cột thuế của mọi hóa đơn bán ra. Đầu vào: chỉ cộng các hóa đơn mua vào hợp lệ.'],
                        explain=f'Đầu ra {xu(out_vat)} · đầu vào hợp lệ {xu(in_vat)}.'),
        procedures.step('payable', 'number', 'Thuế GTGT phải nộp', f'Quý {q} Mộc Miên phải nộp bao nhiêu thuế GTGT?', out_vat - in_vat,
                        hints=['Phải nộp = đầu ra − đầu vào hợp lệ.'], explain=f'{xu(out_vat)} − {xu(in_vat)} = {xu(out_vat - in_vat)}.'),
        procedures.step('deadline', 'choice', 'Hạn nộp tờ khai quý', f'Hạn cuối nộp tờ khai và tiền thuế GTGT quý {q} là ngày nào?', deadline,
                        options=[dict(id='d30_4', label='30/4'), dict(id='d31_7', label='31/7'), dict(id='d31_10', label='31/10'),
                                 dict(id='d31_1', label='31/1 năm sau'), dict(id='d20', label=f'20/{mo[2] % 12 + 1}')],
                        hints=['Khai theo quý: hạn là ngày cuối cùng của tháng đầu tiên thuộc quý tiếp theo.'],
                        explain='Quý ' + str(q) + ' → hạn ' + {'d30_4': '30/4', 'd31_7': '31/7', 'd31_10': '31/10', 'd31_1': '31/1 năm sau'}[deadline] + '.'),
    ]
    return dict(npc=3, title=f'Tờ khai GTGT quý {q} của quán Mộc Miên',
                opening='Hóa đơn quý này chú gom hết vô hộp rồi nè con, có tờ chú cũng không nhớ mua cái gì…',
                brief=f'Lập tờ khai thuế GTGT quý {q} cho Công ty TNHH Mộc Miên (quán cà phê của Chú Bảy): loại hóa đơn không hợp lệ, cộng thuế, tính số phải nộp và hạn nộp.',
                papers=papers, steps=steps)


TET = [dict(due='20/2', start='14/2', end='22/2', after='23/2', before='13/2', what='Tờ khai thuế TNCN tháng 1'),
       dict(due='30/1', start='27/1', end='2/2', after='3/2', before='26/1', what='Lệ phí môn bài'),
       dict(due='20/1', start='18/1', end='24/1', after='25/1', before='17/1', what='Tờ khai thuế TNCN tháng 12')]
FILING_STEPS = [dict(id='reconcile', label='Đối chiếu số liệu tờ khai với sổ sách'), dict(id='sign', label='Ký số tờ khai'),
                dict(id='submit', label='Nộp tờ khai qua cổng thuế'), dict(id='receipt', label='Tải và lưu thông báo tiếp nhận'),
                dict(id='pay', label='Nộp tiền thuế trước hạn, lưu chứng từ')]


def _calendar(rng) -> dict:
    m = rng.choice([4, 7, 10])
    last = {4: 30, 7: 31, 10: 31}[m]
    qprev = {4: 'I', 7: 'II', 10: 'III'}[m]
    tet = rng.choice(TET)
    amount, days = rng.choice([12000, 25000, 40000]), rng.choice([5, 10, 12, 20])
    late = amount * LATE_PER_DAY * days // 10000
    left = [dict(id='pit_m', label=f'Tờ khai thuế TNCN tháng {m - 1} (khai theo tháng)'), dict(id='vat_q', label=f'Tờ khai thuế GTGT quý {qprev}'),
            dict(id='lic', label='Lệ phí môn bài năm tới'), dict(id='fin', label='Quyết toán thuế TNCN năm nay (công ty trả lương)')]
    right = [dict(id='d10', label=f'10/{m}'), dict(id='d20', label=f'20/{m}'), dict(id='dlast', label=f'{last}/{m}'),
             dict(id='d30_1', label='30/1 năm sau'), dict(id='d31_3', label='31/3 năm sau')]
    papers = [
        dict(id='wall', title=f'Lịch treo tường tháng {m}', kind='kv', rows=[
            ['Việc đang mở', f'{len(left)} hồ sơ của 3 khách hàng'], ['Kỳ nghỉ Tết', f'Từ {tet["start"]} đến hết {tet["end"]}'],
            ['Khoản chậm nộp', f'{xu(amount)} tiền thuế của Xưởng Chỉ Vàng, nộp trễ {days} ngày']], note='Chị Hồng dán mép lịch bằng băng keo đỏ.'),
        dict(id='memo', title='Sổ tay quy trình nộp hồ sơ', kind='kv', rows=[['Trang 12', 'Quy trình 5 bước — nhòe hết vì đổ cà phê'],
                                                                              ['Chị Hồng dặn', 'Sắp lại rồi chép sang trang mới giùm chị.']]),
    ]
    steps = [
        procedures.step('match', 'match', 'Ghép hồ sơ với hạn nộp', 'Ghi hạn cuối cho từng hồ sơ lên lịch.',
                        dict(pit_m='d20', vat_q='dlast', lic='d30_1', fin='d31_3'), left=left, right=right,
                        hints=['TNCN theo tháng: ngày 20 tháng sau. GTGT theo quý: ngày cuối tháng đầu quý sau.',
                               'Môn bài: 30/1. Quyết toán năm: 31/3 năm sau.'],
                        explain=f'TNCN tháng {m - 1} → 20/{m} · GTGT quý {qprev} → {last}/{m} · môn bài → 30/1 · quyết toán → 31/3.'),
        procedures.step('tet', 'choice', 'Hạn rơi vào Tết', f'{tet["what"]} có hạn {tet["due"]}, nhưng Tết nghỉ từ {tet["start"]} đến hết {tet["end"]}. Hạn cuối là ngày nào?',
                        'after', options=_shuffled(rng, [dict(id='orig', label=tet['due']), dict(id='before', label=tet['before']),
                                                         dict(id='after', label=tet['after']), dict(id='none', label='Không còn hạn, nộp lúc nào cũng được')]),
                        hints=['Hạn rơi vào ngày nghỉ lễ được lùi sang ngày làm việc đầu tiên sau kỳ nghỉ.'],
                        explain=f'Lùi sang {tet["after"]} — nhưng nộp trước Tết vẫn là thói quen an toàn nhất.'),
        procedures.step('late', 'number', 'Tiền chậm nộp', f'Tính tiền chậm nộp: {xu(amount)} × 0,03% × {days} ngày (làm tròn xuống).', late,
                        hints=['0,03% mỗi ngày nghĩa là × 3 ÷ 10.000 cho mỗi ngày trễ.'],
                        explain=f'{fmt(amount)} × 3 × {days} ÷ 10.000 = {xu(late)}.'),
        procedures.step('order', 'order', 'Sắp lại quy trình nộp', 'Sắp các việc theo đúng thứ tự làm một hồ sơ thuế.',
                        [x['id'] for x in FILING_STEPS], items=_shuffled(rng, copy.deepcopy(FILING_STEPS)),
                        hints=['Số liệu đúng trước, rồi mới ký; nộp xong phải giữ bằng chứng đã nộp; tiền thuế nộp trước hạn.'],
                        explain='Đối chiếu → ký số → nộp → lưu thông báo tiếp nhận → nộp tiền, lưu chứng từ.'),
    ]
    return dict(npc=0, title=f'Lịch hạn nộp tháng {m}',
                opening='Tháng này dồn hạn quá em ơi. Em ghi lịch giùm chị, đừng để khách nào bị phạt nha.',
                brief='Ghép từng hồ sơ với hạn nộp, xử lý hạn rơi vào Tết, tính tiền chậm nộp, sắp lại quy trình nộp hồ sơ.',
                papers=papers, steps=steps)


def _question(rng, legacy: bool = False) -> dict:
    npc = rng.choice([2, 4])
    name, role = WORKERS[0] if npc == 2 else WORKERS[1]
    first = name.split()[-1]
    h, lunch, deps = rng.choice([30, 40, 50]), 700, rng.choice([0, 1])
    causes = sorted(rng.sample(['leave', 'ot', 'phone'], rng.choice([2, 3])))
    ot8 = rng.choice([6, 8, 10])
    ot9 = ot8 - rng.choice([3, 4]) if 'ot' in causes else ot8
    a = _pay(h, 0, lunch, 0, 200, deps, [(ot8, 'r150')])
    b = _pay(h, 1 if 'leave' in causes else 0, lunch, 0, 0 if 'phone' in causes else 200, deps, [(ot9, 'r150')])

    def slip(p, month, unpaid, phone, oth):
        return dict(id=f'slip{month}', title=f'Phiếu lương tháng {month} · {name}', kind='kv', rows=[
            ['Lương cơ bản', xu(p['base'])], ['Trừ nghỉ không lương', f'{xu(p["leave"])} ({unpaid} ngày)'],
            ['Tăng ca ngày thường', f'{xu(p["ot"])} ({oth} giờ)'], ['Phụ cấp ăn trưa', xu(lunch)], ['Phụ cấp điện thoại', xu(phone)],
            ['Tổng thu nhập', xu(p['gross'])], ['BHXH + BHYT + BHTN', xu(p['ins_total'])], ['Thuế TNCN', xu(p['pit'])], ['Thực lĩnh', xu(p['net'])]])
    diff = a['net'] - b['net']
    opts = [dict(id='leave', label='Tháng 9 có ngày nghỉ không lương'), dict(id='ot', label='Tháng 9 tăng ca ít giờ hơn'),
            dict(id='phone', label='Tháng 9 không còn phụ cấp điện thoại'), dict(id='ins', label='Tỷ lệ bảo hiểm tháng 9 tăng lên'),
            dict(id='tax', label='Thuế TNCN tháng 9 cao hơn tháng 8'), dict(id='fine', label='Bị trừ tiền phạt đi trễ')]
    hr = dict(id='hr', title='Ghi chú nhân sự tháng 9', kind='kv', rows=[
        ['Điện thoại', 'Từ tháng 9 xưởng cấp sim công ty, thôi phụ cấp điện thoại.' if 'phone' in causes else 'Không thay đổi.'],
        ['Nghỉ', f'{first} xin nghỉ việc riêng 1 ngày, không lương (đã duyệt).' if 'leave' in causes else 'Không có ngày nghỉ không lương.'],
        ['Nội quy', 'Xưởng không phạt tiền đi trễ; nhắc nhở bằng văn bản.']])
    steps = [
        procedures.step('causes', 'multi', 'Tìm nguyên nhân', f'Vì sao thực lĩnh tháng 9 của {first} thấp hơn tháng 8? Chọn MỌI nguyên nhân đúng.', causes,
                        options=_shuffled(rng, opts),
                        hints=['So từng dòng của hai phiếu; dòng nào bằng nhau thì không phải nguyên nhân.',
                               'Thu nhập giảm thì thuế thường giảm theo, không tăng. Nội quy xưởng có nói về tiền phạt.'],
                        explain='Khác biệt nằm ở: ' + ', '.join(o['label'].lower() for o in opts if o['id'] in causes) + '.'),
        procedures.step('diff', 'number', 'Chênh lệch thực lĩnh', 'Thực lĩnh tháng 8 hơn tháng 9 bao nhiêu xu?', diff,
                        hints=['Lấy thực lĩnh tháng 8 trừ thực lĩnh tháng 9.'], explain=f'{xu(a["net"])} − {xu(b["net"])} = {xu(diff)}.'),
        procedures.step('reply', 'choice', 'Trả lời người lao động', f'Bạn trả lời {first} thế nào?', 'explain',
                        options=_shuffled(rng, [dict(id='explain', label=f'Gửi riêng {first} bảng so sánh hai tháng, giải thích từng dòng khác nhau'),
                                                dict(id='compare', label='Gửi kèm phiếu lương của bạn cùng tổ để thấy “ai cũng vậy”'),
                                                dict(id='blame', label='“Phần mềm tự tính, chị cũng không rõ”' if legacy else '“Phần mềm tự tính, mình cũng không rõ”')]),
                        hints=['Chỉ dùng số liệu của chính người hỏi; đừng đổ cho phần mềm.'], tag='ethic',
                        explain='Giải thích bằng chính phiếu của người hỏi: rõ ràng, tôn trọng và giữ bí mật lương người khác.'),
    ]
    return dict(npc=npc, title=f'{first} hỏi: “Sao lương em ít hơn?”',
                opening=f'Anh chị ơi, lương tháng 9 của em thấp hơn tháng 8 tận {fmt(diff)} xu. Có phải tính nhầm không ạ?' if npc == 2 else
                f'Cho tôi hỏi, tháng 9 lương tôi hụt {fmt(diff)} xu so với tháng 8. Nhờ kiểm giúp.',
                brief=f'So sánh phiếu lương tháng 8 và tháng 9 của {name}, tìm nguyên nhân, tính chênh lệch và trả lời đúng mực.',
                papers=[slip(a, 8, 0, 200, ot8), slip(b, 9, 1 if 'leave' in causes else 0, 0 if 'phone' in causes else 200, ot9), hr],
                steps=steps)


def _yearend(rng) -> dict:
    npc = rng.choice([4, 2])
    name = WORKERS[1][0] if npc == 4 else WORKERS[0][0]
    first = name.split()[-1]
    monthly = rng.choice([13000, 15000, 17000, 19000])
    two_jobs = rng.random() < .5
    extra = 4 * 6000 if two_jobs else 0
    ins_sal = monthly - monthly % 200
    b = 12 * sum(insurance(ins_sal).values())
    m = rng.choice([0, 6, 9, 12])
    income = 12 * monthly + extra
    deduct = 12 * PERSONAL + DEPENDENT * m
    taxable = max(0, income - b - deduct)
    due = pit(taxable, 12)
    delta = rng.choice([-600, -300, 400, 900])
    withheld = due + delta
    w2 = rng.choice([300, 500, 800]) if two_jobs else 0
    balance = due - withheld
    papers = [dict(id='cert1', title='Chứng từ khấu trừ thuế · Xưởng may Chỉ Vàng', kind='kv', rows=[
        ['Người nộp thuế', name], ['Thu nhập chịu thuế cả năm', xu(12 * monthly)], ['Bảo hiểm bắt buộc đã trừ', xu(b)],
        ['Thuế đã khấu trừ', xu(withheld - w2)], ['Hợp đồng', 'Lao động không thời hạn, cả 12 tháng']])]
    if two_jobs:
        papers.append(dict(id='cert2', title='Chứng từ khấu trừ thuế · Tiệm Sửa Máy May Kim Chỉ', kind='kv', rows=[
            ['Thu nhập chịu thuế', xu(extra)], ['Thuế đã khấu trừ', xu(w2)], ['Hợp đồng', 'Hợp đồng lao động 4 tháng (tháng 5–8), làm buổi tối']]))
    papers.append(dict(id='dep', title='Người phụ thuộc đã đăng ký', kind='kv', rows=[
        ['Người phụ thuộc', 'Con gái (bé Na)' if m else 'Không có'],
        ['Số tháng được tính trong năm', f'{m} tháng' if m else '0 tháng']]))
    papers.append(dict(id='rule', title='Quy định về quyết toán', kind='kv', rows=[
        ['Chỉ làm ở một nơi cả năm', 'Ủy quyền cho công ty quyết toán thay; nộp giấy ủy quyền.'],
        ['Có hợp đồng lao động từ 3 tháng ở nơi thứ hai', 'Tự quyết toán: tờ khai quyết toán + chứng từ khấu trừ của mọi nơi (+ hồ sơ người phụ thuộc nếu có).'],
        ['Giảm trừ cả năm', f'Bản thân {fmt(12 * PERSONAL)} + {fmt(DEPENDENT)} × số tháng có người phụ thuộc']]))
    route = 'self' if two_jobs else 'company'
    docs = sorted(['decl', 'cert'] + (['dep'] if m else [])) if two_jobs else ['form']
    steps = [
        procedures.step('route', 'choice', 'Ai quyết toán?', f'{first} nên quyết toán thuế TNCN năm nay theo cách nào?', route,
                        options=_shuffled(rng, [dict(id='company', label='Ủy quyền cho công ty quyết toán thay'),
                                                dict(id='self', label='Tự quyết toán với cơ quan thuế'),
                                                dict(id='none', label='Không cần làm gì, công ty đã khấu trừ rồi')]),
                        hints=['Đếm xem trong năm có mấy nơi ký hợp đồng lao động từ 3 tháng trở lên.'],
                        explain='Có thu nhập từ hai nơi ký hợp đồng lao động → tự quyết toán.' if two_jobs else 'Chỉ làm một nơi cả năm → ủy quyền cho công ty.'),
        procedures.step('docs', 'multi', 'Chuẩn bị hồ sơ', 'Chọn đúng và đủ giấy tờ cần nộp cho cách quyết toán đã chọn.', docs,
                        options=_shuffled(rng, [dict(id='form', label='Giấy ủy quyền quyết toán'),
                                                dict(id='decl', label='Tờ khai quyết toán thuế cá nhân'),
                                                dict(id='cert', label='Chứng từ khấu trừ thuế của các nơi trả lương'),
                                                dict(id='dep', label='Hồ sơ người phụ thuộc'), dict(id='rent', label='Hợp đồng thuê nhà'),
                                                dict(id='photo', label='Ảnh thẻ 3×4'), dict(id='bank', label='Sao kê ngân hàng 12 tháng')]),
                        hints=['Ủy quyền: công ty đã giữ sẵn chứng từ và hồ sơ người phụ thuộc. Tự quyết toán: tự nộp đủ tờ khai và chứng từ của mọi nơi.',
                               'Giấy tờ không liên quan tới thu nhập, khấu trừ hay giảm trừ thì không cần.'],
                        explain='Hồ sơ đúng: ' + ', '.join({'form': 'giấy ủy quyền', 'decl': 'tờ khai quyết toán', 'cert': 'chứng từ khấu trừ', 'dep': 'hồ sơ người phụ thuộc'}[d] for d in docs) + '.'),
        procedures.step('calc', 'fields', 'Tính quyết toán', 'Tính cả năm theo biểu lũy tiến năm (mốc tháng × 12).',
                        dict(deduct=deduct, taxable=taxable, due=due, balance=balance),
                        fields=[dict(id='deduct', label='Tổng giảm trừ gia cảnh'), dict(id='taxable', label='Thu nhập tính thuế cả năm'),
                                dict(id='due', label='Thuế phải nộp cả năm'), dict(id='balance', label='Còn phải nộp (+) / được hoàn (−)')],
                        hints=['Thu nhập tính thuế = tổng thu nhập chịu thuế mọi nơi − bảo hiểm − giảm trừ gia cảnh.',
                               'Biểu năm: tới 24.000 → 5%, 24.000–60.000 → 10%, 60.000–120.000 → 15%, trên đó 20%. Chênh lệch = thuế cả năm − tổng thuế đã khấu trừ.'],
                        explain=f'Giảm trừ {xu(deduct)} · tính thuế {xu(taxable)} · thuế năm {xu(due)} · đã khấu trừ {xu(withheld)} → '
                                + (f'nộp thêm {xu(balance)}.' if balance > 0 else f'được hoàn {xu(-balance)}.')),
    ]
    return dict(npc=npc, title=f'Quyết toán thuế năm của {first}',
                opening=f'Cuối năm rồi, {"tôi" if npc == 4 else "em"} phải làm gì với thuế thu nhập vậy? Nghe nói có người còn được hoàn tiền.',
                brief=f'Hướng dẫn {name} quyết toán thuế TNCN năm: chọn cách quyết toán, chuẩn bị hồ sơ, tính số còn phải nộp hoặc được hoàn.',
                papers=papers, steps=steps)


FORMS = [dict(id='payslip', min_day=1, bonus=30, build=_payslip), dict(id='transfer', min_day=1, bonus=20, build=_transfer),
         dict(id='question', min_day=1, bonus=10, build=_question), dict(id='vat', min_day=2, bonus=25, build=_vat),
         dict(id='calendar', min_day=2, bonus=15, build=_calendar), dict(id='yearend', min_day=3, bonus=25, build=_yearend)]
FORM_INDEX = {x['id']: x for x in FORMS}
GEN = 2
GRID_BONUS = 30
FIXED = ('form', 'papers', 'proc', 'brief', 'due_turn', 'bonus', 'rows', 'gen')


# ------------------------------------------------------------------ luck of the day & rules that shift
MODS = [
    dict(id='normal', min_day=1, weight=3, emoji='☀️', name='Ngày bình thường', text='Hồ sơ đều tay, chị Hồng ngồi bàn bên cạnh.'),
    dict(id='cutoff', min_day=2, weight=2, emoji='🏦', name='Ngân hàng chốt lệnh sớm',
         text='Hôm nay ngân hàng chốt lệnh lương lúc 09:30 — bảng lương phải chuyển trước giờ đó.'),
    dict(id='inspector', min_day=2, weight=2, emoji='🗂️', name='Cô Lụa ghé kiểm tra',
         text='Cuối ngày cô Lụa soát bảng lương đã chuyển: sạch thì được khen, sót lỗi thì bị phạt thêm.'),
    dict(id='intern', min_day=2, weight=2, emoji='🐣', name='Bình lập bảng nháp',
         text='Bảng lương nháp hôm nay do Bình mới vào lập: dài hơn, lắm lỗi hơn.'),
    dict(id='crunch', emoji='📆', name='Kỳ lương cuối tháng', forced_only=True,
         text='Ngày trả lương cả xưởng: bảng dài, hạn gấp. Tăng ca hôm nay được trả 18 xu.'),
]
FORCED = {4: 'crunch'}
INTRO = {2: 'intern', 3: 'inspector', 4: 'cutoff'}
FLOORS = (6400, 6600, 6800, 7000)
DEP_CUTS = (15, 10, 20, 12)
NATIONAL = {1: ('1/1', 'Tết Dương lịch'), 4: ('30/4', 'Ngày Giải phóng'), 5: ('1/5', 'Quốc tế Lao động'), 9: ('2/9', 'Quốc khánh')}


def _mod(day: int) -> dict:
    return office.mod_of(ID, day, MODS, FORCED, INTRO)


def _rules_raw(day: int) -> dict:
    k = (max(1, day) - 1) // 5
    m = (k + 8) % 12 + 1                       # the first pay period is September
    hd, hname = NATIONAL.get(m, (f'{(6, 8, 9, 11, 18)[k % 5]}/{m}', 'Ngày hội Xưởng Chỉ Vàng'))
    return dict(k=k, m=m, prev=(m - 2) % 12 + 1, holiday=hd, holiday_name=hname, floor=FLOORS[k % len(FLOORS)], cut=DEP_CUTS[k % len(DEP_CUTS)])


def _rule_cards(day: int) -> list:
    r = _rules_raw(day)
    cards = [dict(id='ot', emoji='🕒', title='Tăng ca', text='Ngày thường 150% · Chủ nhật 200% · Ngày lễ 300%. Chỉ trả giờ có phiếu duyệt.'),
             dict(id='holiday', emoji='🎌', title=f'Ngày lễ kỳ lương tháng {r["m"]}', text=f'{r["holiday"]} ({r["holiday_name"]}): tăng ca tính 300%.'),
             dict(id='leave', emoji='🏖️', title='Ngày công', text='Chuẩn 26 ngày. Phép năm vẫn hưởng lương; chỉ trừ ngày nghỉ KHÔNG lương.'),
             dict(id='adv', emoji='💵', title='Tạm ứng', text='Trừ đúng một lần, đúng số trong sổ tạm ứng.'),
             dict(id='bank', emoji='🏦', title='Tài khoản nhận', text='Chỉ chuyển vào tài khoản trong hồ sơ nhân sự. Tin nhắn xin đổi số không có giá trị.'),
             dict(id='people', emoji='🧑‍🏭', title='Ai được trả', text='Người có hồ sơ, đang làm việc; mỗi người đúng một dòng.')]
    if day >= 1:
        cards.append(dict(id='ins', emoji='🛡️', title='Mức sàn đóng bảo hiểm', text=f'Lương đóng BH tối thiểu {fmt(r["floor"])} xu. Hợp đồng thấp hơn thì đóng theo mức sàn; không tính trên tổng thu nhập.'))
    if day >= 3:
        cards.append(dict(id='deps', emoji='👨‍👩‍👧', title='Người phụ thuộc', text=f'Hồ sơ nộp trước ngày {r["cut"]}/{r["m"]} mới được tính từ kỳ này.'))
    return cards


def rules(day: int) -> list:
    today = _rule_cards(day)
    before = {x['id']: x['title'] + x['text'] for x in _rule_cards(day - 1)} if day > 1 else None
    for x in today:
        x['new'] = before is not None and before.get(x['id']) != x['title'] + x['text']
    return today


# ------------------------------------------------------------------ the payroll grid (Papers, Please for payday)
GRID_COLS = (('name', 'Họ tên'), ('days', 'Ngày công hưởng lương'), ('ot', 'Tăng ca'), ('ins', 'Lương đóng BH'),
             ('deps', 'Người phụ thuộc'), ('adv', 'Trừ tạm ứng'), ('bank', 'Tài khoản nhận'))
EXTRA_WORKERS = [('Mai Thị Hằng', 'Công nhân may'), ('Lâm Văn Đức', 'Thợ đóng gói'), ('Tạ Thu Hà', 'Nhân viên kế hoạch'),
                 ('Kiều Văn Sang', 'Bảo vệ')]
MAX_FLAGS = 3
FLAG_MIN, ROW_MIN, HINT_MIN, PAY_MIN, CLAIM_MIN = 1, 4, 5, 10, 15
GRID_HINTS = dict(
    unpaid='So ngày công với cột “Nghỉ” trong bảng chấm công.', annual='Phép năm có bị trừ công không?',
    ot_rate='Xem ngày của từng dòng tăng ca: Chủ nhật? Ngày lễ kỳ này?', ot_missing='Đếm lại số giờ tăng ca đã duyệt.',
    ot_unapproved='Dòng tăng ca nào chưa có phiếu duyệt?', ins_floor='So lương đóng BH với thẻ “Mức sàn đóng bảo hiểm”.',
    ins_gross='Lương đóng BH lấy theo hợp đồng hay theo tổng thu nhập?', dep_new='Xem ngày nộp hồ sơ người phụ thuộc và mốc của kỳ.',
    dep_missing='Đếm người phụ thuộc đã đăng ký trong hồ sơ nhân sự.', adv_twice='So với sổ tạm ứng: ứng mấy lần?',
    adv_missing='Người này có tên trong sổ tạm ứng không?', bank='So tài khoản với hồ sơ nhân sự và hộp thư.',
    ghost='Người này có hồ sơ nhân sự không?', resigned='Xem cột tình trạng trong hồ sơ nhân sự.', dup='Có dòng nào trùng người, trùng tài khoản?',
    clean='Soát đủ bảy ô với chấm công, hồ sơ nhân sự, sổ tạm ứng và hộp thư.')
ERR_MIN_DAY = dict(unpaid=1, annual=1, ot_missing=1, adv_missing=1, ghost=1, ot_rate=2, dup=2, bank=2,
                   ins_floor=3, dep_missing=3, adv_twice=3, resigned=3, dep_new=4, ot_unapproved=4, ins_gross=4)
ROW_ERRORS = ('unpaid', 'annual', 'ot_missing', 'adv_missing', 'ot_rate', 'bank', 'ins_floor', 'dep_missing', 'adv_twice',
              'dep_new', 'ot_unapproved', 'ins_gross')
PEOPLE_ERRORS = ('ghost', 'dup', 'resigned')


def grid_size(day: int, mod_id: str) -> int:
    return (3 if day <= 1 else 4 if day <= 3 else 5 if day <= 6 else 6) + (1 if mod_id in ('crunch', 'intern') else 0)


def _acct(n: str) -> str:
    return f'{n[:4]} {n[4:8]} {n[8:]}'


def _ot_pay(h: int, entries: list) -> tuple[int, int]:
    rows = [e for e in entries if e['ok']]
    return sum(e['hrs'] for e in rows), sum(h * e['hrs'] * OT_RATES[e['rate']] // 100 for e in rows)


def _employee(rng, name: str, role: str, r: dict) -> dict:
    h = rng.choice([30, 40, 50, 60])
    base = h * STD_HOURS * STD_DAYS
    contract = base - base % 200
    m = r['m']
    ots = [dict(label=f'{rng.choice(["Thứ Ba 10", "Thứ Năm 12", "Thứ Sáu 20"])}/{m}', hrs=rng.choice([2, 3]), rate='r150', ok=True)]
    if rng.random() < .6:
        ots.append(dict(label=f'Chủ nhật {rng.choice([15, 22])}/{m}', hrs=rng.choice([3, 4]), rate='r200', ok=True))
    if rng.random() < .45:
        ots.append(dict(label=f'{r["holiday"]} ({r["holiday_name"]})', hrs=rng.choice([2, 3]), rate='r300', ok=True))
    return dict(name=name, role=role, h=h, contract=contract, ins=max(contract, r['floor']), unpaid=rng.choice([0, 0, 1, 2]),
                annual=rng.choice([0, 0, 1]), ots=ots, deps=rng.choice([0, 0, 1, 2]), pending=None,
                adv=rng.choice([0, 0, 0, 500, 800]), acct=str(rng.randrange(10 ** 9, 10 ** 10)), status='Đang làm', chat=None)


def _can(kind: str, e: dict) -> bool:
    if kind == 'unpaid':
        return e['unpaid'] > 0
    if kind == 'annual':
        return e['annual'] > 0
    if kind == 'ot_rate':
        return any(x['rate'] != 'r150' and x['ok'] for x in e['ots'])
    if kind == 'ot_missing':
        return sum(1 for x in e['ots'] if x['ok']) >= 2
    if kind == 'ins_floor':
        return e['contract'] < e['ins']
    if kind == 'dep_missing':
        return e['deps'] > 0
    if kind in ('adv_twice', 'adv_missing'):
        return e['adv'] > 0
    return True


def _cells(e: dict) -> dict:
    hrs, pay = _ot_pay(e['h'], e['ots'])
    return dict(name=e['name'], days=f'{STD_DAYS - e["unpaid"]} ngày', ot=f'{hrs} giờ · {fmt(pay)} xu' if hrs else '0 giờ',
                ins=f'{fmt(e["ins"])} xu', deps=f'{e["deps_count"]} người', adv=f'{fmt(e["adv"])} xu' if e['adv'] else '0',
                bank=_acct(e['acct']))


def _break(rng, kind: str, e: dict, cells: dict, r: dict) -> dict:
    """Plant one mistake of `kind` in the draft cells. Returns the hidden truth of that mistake."""
    h, name = e['h'], e['name']
    first = name.split()[-1]
    if kind == 'unpaid':
        cells['days'] = f'{STD_DAYS} ngày'
        return dict(z='days', dir='over', fine=8, claim=0, why=f'Chấm công có {e["unpaid"]} ngày nghỉ không lương: chỉ {STD_DAYS - e["unpaid"]} ngày hưởng lương.')
    if kind == 'annual':
        cells['days'] = f'{STD_DAYS - e["unpaid"] - e["annual"]} ngày'
        return dict(z='days', dir='under', fine=0, claim=e['annual'] * h * STD_HOURS,
                    why=f'{first} nghỉ phép năm {e["annual"]} ngày — phép năm vẫn hưởng lương, không được trừ công.')
    if kind == 'ot_rate':
        x = next(x for x in e['ots'] if x['rate'] != 'r150' and x['ok'])
        wrong = [dict(y, rate='r150') if y is x else y for y in e['ots']]
        hrs, pay = _ot_pay(h, wrong)
        _, right = _ot_pay(h, e['ots'])
        cells['ot'] = f'{hrs} giờ · {fmt(pay)} xu'
        return dict(z='ot', dir='under', fine=0, claim=right - pay,
                    why=f'Giờ làm {x["label"]} phải tính {OT_RATES[x["rate"]]}%, bảng nháp tính 150%.')
    if kind == 'ot_missing':
        x = [y for y in e['ots'] if y['ok']][-1]
        hrs, pay = _ot_pay(h, [y for y in e['ots'] if y is not x])
        _, right = _ot_pay(h, e['ots'])
        cells['ot'] = f'{hrs} giờ · {fmt(pay)} xu' if hrs else '0 giờ'
        return dict(z='ot', dir='under', fine=0, claim=right - pay, why=f'Thiếu dòng tăng ca {x["label"]} ({x["hrs"]} giờ) đã có phiếu duyệt.')
    if kind == 'ot_unapproved':
        x = dict(label=f'Thứ Bảy {rng.choice([7, 14, 21])}/{r["m"]}', hrs=rng.choice([3, 4]), rate='r150', ok=False)
        e['ots'].append(x)
        hrs, pay = _ot_pay(h, [dict(y, ok=True) for y in e['ots']])
        cells['ot'] = f'{hrs} giờ · {fmt(pay)} xu'
        return dict(z='ot', dir='over', fine=6, claim=0, why=f'Dòng tăng ca {x["label"]} chưa có phiếu duyệt — chưa được chi.')
    if kind == 'ins_floor':
        cells['ins'] = f'{fmt(e["contract"])} xu'
        return dict(z='ins', dir='risk', fine=0, claim=0, why=f'Hợp đồng ghi {fmt(e["contract"])}, thấp hơn mức sàn {fmt(e["ins"])} của kỳ này — phải đóng theo mức sàn.')
    if kind == 'ins_gross':
        gross = e['contract'] + rng.choice([700, 900, 1200])
        cells['ins'] = f'{fmt(gross)} xu'
        return dict(z='ins', dir='under', fine=0, claim=(gross - e['ins']) * sum(INS.values()) // 1000,
                    why='Bảng nháp tính bảo hiểm trên tổng thu nhập; đúng ra tính trên lương đóng BH theo hợp đồng.')
    if kind == 'dep_missing':
        cells['deps'] = f'{e["deps_count"] - 1} người'
        return dict(z='deps', dir='under', fine=0, claim=DEPENDENT // 10,
                    why=f'Hồ sơ nhân sự có {e["deps"]} người phụ thuộc đã đăng ký; bảng nháp thiếu một người nên trừ thuế cao hơn.')
    if kind == 'dep_new':
        day = rng.choice(range(r['cut'], 28))
        e['pending'] = day
        cells['deps'] = f'{e["deps_count"] + 1} người'
        return dict(z='deps', dir='risk', fine=0, claim=0,
                    why=f'Hồ sơ người phụ thuộc mới nộp ngày {day}/{r["m"]}, sau mốc {r["cut"]}/{r["m"]} — kỳ sau mới được tính.')
    if kind == 'adv_twice':
        cells['adv'] = f'{fmt(2 * e["adv"])} xu'
        return dict(z='adv', dir='under', fine=0, claim=e['adv'], why=f'Sổ tạm ứng chỉ ghi một lần {fmt(e["adv"])} xu — bảng nháp trừ hai lần.')
    if kind == 'adv_missing':
        cells['adv'] = '0'
        return dict(z='adv', dir='over', fine=6, claim=0, why=f'Sổ tạm ứng ghi {first} đã ứng {fmt(e["adv"])} xu; bảng nháp quên trừ.')
    if kind == 'bank':
        other = str(rng.randrange(10 ** 9, 10 ** 10))
        e['chat'] = other
        cells['bank'] = _acct(other)
        return dict(z='bank', dir='over', fine=12, claim=0,
                    why='Số tài khoản lấy từ một tin nhắn xin đổi số, không có đơn ký tên — dễ là lừa đảo. Chỉ chuyển theo hồ sơ nhân sự.')
    raise ValueError(kind)


def g_grid(rng, day: int, slot: int) -> dict:
    r = _rules_raw(day)
    mod = _mod(day)
    n = grid_size(day, mod['id'])
    pool = WORKERS + EXTRA_WORKERS
    staff = rng.sample(pool, n)
    emps = [_employee(rng, name, role, r) for name, role in staff]
    for e in emps:
        if rng.random() < .35 and day >= 3:
            e['pending'] = rng.choice(range(2, r['cut']))          # filed in time: counts this period
        if rng.random() < .3 and day >= 4:                         # a Saturday without a signed slip: correctly left out
            e['ots'].append(dict(label=f'Thứ Bảy {rng.choice([7, 14, 21])}/{r["m"]}', hrs=rng.choice([2, 3]), rate='r150', ok=False))
    kinds = [k for k in ROW_ERRORS if ERR_MIN_DAY[k] <= day]
    people = [k for k in PEOPLE_ERRORS if ERR_MIN_DAY[k] <= day]
    share = .7 if mod['id'] == 'intern' else .5
    bad_n = max(1, min(n - 1, round(n * share)))
    plan = []                                                   # (employee index or None, kind)
    order = list(range(n))
    rng.shuffle(order)
    person_err = rng.choice(people) if people and rng.random() < (.8 if day >= 2 else .6) else None
    if person_err:
        bad_n -= 1
    for i in order:
        if len([p for p in plan if p[0] is not None]) >= bad_n:
            break
        options = [k for k in kinds if _can(k, emps[i]) and k not in [p[1] for p in plan]] or [k for k in kinds if _can(k, emps[i])]
        if options:
            plan.append((i, rng.choice(options)))
    if day >= 8 and plan and rng.random() < .5:
        i, k0 = plan[0]
        z0 = {'unpaid': 'days', 'annual': 'days'}.get(k0, k0.split('_')[0])
        more = [k for k in kinds if _can(k, emps[i]) and k != k0 and {'unpaid': 'days', 'annual': 'days'}.get(k, k.split('_')[0]) != z0
                and not (k.startswith('ot') and k0.startswith('ot'))]
        if more:
            plan.append((i, rng.choice(more)))
    for e in emps:
        e['deps_count'] = e['deps'] + (1 if e['pending'] is not None else 0)
    rows = []
    for i, e in enumerate(emps):
        cells = _cells(e)
        errs = []
        for j, k in plan:
            if j == i:
                if k == 'dep_new' and e['pending'] is not None:
                    e['deps_count'] -= 1                  # the in-time file becomes a late one
                tr = _break(rng, k, e, cells, r)
                tr['kind'] = k
                errs.append(tr)
        rows.append(dict(e=e, cells=cells, errs=errs))
    ghost = None
    if person_err == 'ghost':
        g = rng.choice(STRANGERS)
        ghost = dict(name=g, role='—', h=40, acct=str(rng.randrange(10 ** 9, 10 ** 10)))
        cells = dict(name=g, days=f'{STD_DAYS} ngày', ot='0 giờ', ins=f'{fmt(max(8200, r["floor"]))} xu', deps='0 người', adv='0', bank=_acct(ghost['acct']))
        rows.insert(rng.randrange(1, len(rows) + 1), dict(e=None, cells=cells, errs=[dict(z='name', dir='over', fine=15, claim=0, kind='ghost',
                                                                                        why=f'{g} không có trong hồ sơ nhân sự — “lương ma”.')]))
    elif person_err == 'dup':
        src = rng.choice([x for x in rows if not x['errs']] or rows)
        rows.insert(rows.index(src) + 1 + rng.randrange(0, len(rows) - rows.index(src)),
                    dict(e=None, cells=dict(src['cells']), errs=[dict(z='name', dir='over', fine=12, claim=0, kind='dup',
                                                                     why=f'Trùng dòng với {src["cells"]["name"]} — cùng người, cùng tài khoản, trả hai lần.')]))
    elif person_err == 'resigned':
        name, role = next(x for x in pool if x not in staff)
        e = _employee(rng, name, role, r)
        e['deps_count'] = e['deps']
        e['status'] = f'Nghỉ việc từ 31/{r["prev"]}'
        emps.append(e)
        rows.insert(rng.randrange(0, len(rows) + 1), dict(e=e, cells=_cells(e), errs=[dict(z='name', dir='over', fine=12, claim=0, kind='resigned',
                                                                                     why=f'{name} đã nghỉ việc từ 31/{r["prev"]}, không còn trong kỳ lương này.')]))
    out = []
    for i, row in enumerate(rows):
        cells = [dict(z=z, k=k, v=row['cells'][z]) for z, k in GRID_COLS]
        errs = row['errs']
        out.append(dict(id=f'r{i + 1}', cells=cells,
                        _truth=dict(z=[x['z'] for x in errs], kinds=[x['kind'] for x in errs], why=[x['why'] for x in errs],
                                    dirs=[x['dir'] for x in errs], fines=[x['fine'] for x in errs], claims=[x['claim'] for x in errs])))
    # Reference papers: HR file, timesheet, advances, inbox.
    def deps_txt(e):
        parts = [f'{e["deps"]} đã đăng ký'] if e['deps'] else []
        if e['pending'] is not None:
            parts.append(f'1 hồ sơ nộp {e["pending"]}/{r["m"]}')
        return ' · '.join(parts) or 'Không'
    hr_rows = [[e['name'], f'{e["h"]} xu/giờ', fmt(e['contract']), deps_txt(e), _acct(e['acct']), e['status']] for e in emps]
    hr_rows.sort(key=lambda x: x[0].split()[-1])
    def ot_txt(e):
        return ' · '.join(f'{x["label"]} {x["hrs"]}g {"✔ duyệt" if x["ok"] else "✗ chưa duyệt"}' for x in e['ots']) or '—'
    time_rows = [[e['name'], f'Không lương {e["unpaid"]} · Phép năm {e["annual"]}', ot_txt(e)] for e in emps if e['status'] == 'Đang làm']
    time_rows.sort(key=lambda x: x[0].split()[-1])
    adv_rows = [[e['name'], f'{rng.randrange(3, 16)}/{r["m"]}', fmt(e['adv'])] for e in emps if e['adv']]
    inbox = [[f'Tin nhắn · {e["name"].split()[-1]}', f'“Chị ơi em đổi số tài khoản mới nha: {_acct(e["chat"])}. Kỳ này chuyển vô số mới giúp em, gấp lắm!”']
             for e in emps if e['chat']]
    inbox += rng.sample([['Chị Hồng', 'Nhớ đối chiếu từng ô với hồ sơ gốc. Chuyển lương rồi là khó đòi lại lắm.'],
                         ['Tổ trưởng Hoa', 'Phiếu tăng ca nào chưa ký là chưa duyệt đâu nha.'],
                         ['Phòng nhân sự', 'Hồ sơ người phụ thuộc nộp sau mốc thì tính từ kỳ sau.'],
                         ['Anh Phát', 'Chuyển lương đúng giờ giùm anh, công nhân trông lắm.']], 2)
    papers = [
        dict(id='hr', title='Hồ sơ nhân sự', kind='table', head=['Họ tên', 'Lương giờ', 'Lương đóng BH (HĐ)', 'Người phụ thuộc', 'Tài khoản', 'Tình trạng'],
             rows=hr_rows),
        dict(id='time', title=f'Chấm công & tăng ca tháng {r["m"]}', kind='table', head=['Họ tên', 'Nghỉ (ngày)', 'Tăng ca'], rows=time_rows,
             note='Tổ trưởng đã ký. Chỉ dòng có “✔ duyệt” mới được trả.'),
        dict(id='adv', title='Sổ tạm ứng', kind='table', head=['Họ tên', 'Ngày ứng', 'Số tiền'], rows=adv_rows or [['—', '—', '0']]),
        dict(id='inbox', title='Hộp thư & tin nhắn', kind='kv', rows=inbox),
    ]
    bad = sum(1 for x in out if x['_truth']['z'])
    cut = 'trước 09:30' if mod['id'] == 'cutoff' else 'trước giờ hạn'
    opening = {'intern': f'Bình mới lập bảng nháp {len(out)} người, em soát kỹ giùm chị nha.',
               'crunch': f'Kỳ lương cuối tháng! {len(out)} người đang trông tiền về. Soát nhanh mà chắc em nhé.',
               'cutoff': f'Ngân hàng chốt lệnh 09:30 đó em. Bảng {len(out)} người, chuyển {cut}.',
               'inspector': f'Chiều cô Lụa qua soát bảng lương. {len(out)} người, em làm sạch sẽ giùm chị.'}.get(
        mod['id'], f'Bảng lương nháp kỳ tháng {r["m"]} có {len(out)} người. Em soát từng ô rồi chuyển lương nha.')
    return dict(npc=0, title=f'Soát bảng lương kỳ tháng {r["m"]}' + (f' · đợt {slot // 4 + 1}' if slot >= 4 else ''), opening=opening,
                brief='Soát từng ô của bảng lương nháp với hồ sơ gốc. Chạm vào ô sai để đánh dấu, “✓ Xong dòng” khi soát xong một người, rồi chuyển lương.',
                papers=papers, rows=out, bad=bad)


# ------------------------------------------------------------------ task factory
def _grid_slot(day: int, slot: int) -> bool:
    return slot == 0 or (slot >= 4 and slot % 4 == 0)


def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        pool = [x for x in FORMS if x['min_day'] <= day]
        f = pool[(kit.rng(ID, day).randrange(len(pool)) + slot) % len(pool)]
        g = (_question(kit.rng(ID, day, slot, f['id']), legacy=True) if f['id'] == 'question' else f['build'](kit.rng(ID, day, slot, f['id'])))
        return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], form=f['id'], papers=g['papers'],
                             proc=g['steps'], proc_state=procedures.initial_state(), brief=g['brief'],
                             due_turn=serial - kit.LEGACY_TURN + 40 + 6 * len(g['steps']), bonus=f['bonus'], filed=False, late=False)
    if _grid_slot(day, slot):
        g = g_grid(kit.rng(ID, day, slot, 'grid'), day, slot)
        return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], form='grid', papers=g['papers'], proc=[],
                             proc_state=procedures.initial_state(), brief=g['brief'], due_turn=None, bonus=GRID_BONUS, filed=False,
                             late=False, rows=g['rows'], flags={}, reviewed=[], results={}, tips=[], gen=GEN)
    pool = [x for x in FORMS if x['min_day'] <= day]
    f = pool[(kit.rng(ID, day).randrange(len(pool)) + slot) % len(pool)]
    g = f['build'](kit.rng(ID, day, slot, f['id']))
    return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], form=f['id'], papers=g['papers'],
                         proc=g['steps'], proc_state=procedures.initial_state(), brief=g['brief'],
                         due_turn=None, bonus=f['bonus'], filed=False, late=False, tips=[], gen=GEN)


def initial() -> dict:
    return dict(filed=0, late=0, log=[], office=office.initial(), claims=[], grids=0, caught=0, missed=0, false_flags=0,
                day_grids=[], claims_paid=0)


def _data(c: dict) -> dict:
    d = kit.data(c)
    for k, v in initial().items():
        d.setdefault(k, copy.deepcopy(v))
    office.ensure(d)
    _care(c, d)
    return d


def _who(t: dict) -> str:
    return PEOPLE[int(t['npc'].rsplit('_', 1)[1]) - 1][0]


# ------------------------------------------------------------------ actions
def _well_typed(kind: str, answer) -> bool:
    """Top-level type guard: procedures.shape_ok uses set membership, which raises
    TypeError (not GameError) on unhashable values such as nested lists."""
    if kind in ('choice',):
        return isinstance(answer, str)
    if kind == 'number':
        return type(answer) is int
    if kind in ('multi', 'order'):
        return isinstance(answer, list) and len(answer) <= 20 and all(isinstance(x, str) for x in answer)
    if kind == 'match':
        return isinstance(answer, dict) and len(answer) <= 20 and all(isinstance(v, str) for v in answer.values())
    if kind == 'fields':
        return isinstance(answer, dict) and len(answer) <= 20 and all(type(v) in (int, str) for v in answer.values())
    return False


def _row(t: dict, rid) -> dict:
    row = next((x for x in t.get('rows') or [] if x['id'] == rid), None)
    kit.need(row, 'Bảng lương không có dòng này.')
    return row


def grade(t: dict) -> dict:
    """Result of each row from the hidden truth and the player's flags (also used to validate saves)."""
    out = {}
    for row in t['rows']:
        truth, flags = set(row['_truth']['z']), set(t['flags'].get(row['id'], []))
        out[row['id']] = dict(ok=truth == flags, missed=sorted(truth - flags), extra=sorted(flags - truth))
    return out


def _pay_grid(s: dict, c: dict, d: dict, o: dict, t: dict, mod: dict) -> dict:
    lunch = office.spend(o, PAY_MIN + office.review_cost(o))
    res = grade(t)
    t['results'] = res
    t['filed'] = True
    caught = missed = extra = risk = over = 0
    fines, claims, found = 0, [], {}
    for row in t['rows']:
        tr = row['_truth']
        r = res[row['id']]
        extra += len(r['extra'])
        for z, kind, why, dr, fine, claim in zip(tr['z'], tr['kinds'], tr['why'], tr['dirs'], tr['fines'], tr['claims']):
            if z not in r['missed']:
                caught += 1
                continue
            missed += 1
            found.setdefault(dr, []).append(why)
            if dr == 'over':
                over += 1
                fines += fine
            elif dr == 'under':
                name = next(x['v'] for x in row['cells'] if x['z'] == 'name')
                claims.append(dict(id=f'cl-{t["id"]}-{row["id"]}-{z}', day=c['day'], from_day=c['day'] + 1, task=t['id'], name=name,
                                   amount=int(claim), why=why, status='open'))
            else:
                risk += 1
    office.trust(o, min(3, caught) - 3 * over - 2 * risk - min(3, extra) - len(claims))
    paid = office.fine(s, c, o, fines, 'Trừ thưởng: chuyển lương sai', t['id']) if fines else 0
    d['claims'] = ar.last(d['claims'] + claims, 20, 'office.claims', c)
    late, adj, note = office.settle(o, t, c['day'])
    t['late'] = late
    if late:
        office.trust(o, -2)
        office.note(o, c['day'], 'Lỡ giờ chốt lệnh: lương về chậm một ngày, cả xưởng xôn xao.', 'late')
    d['grids'] += 1
    _filings(d['care'], c['day'])['grids'] += 1
    d['caught'] += caught
    d['missed'] += missed
    d['false_flags'] += extra
    d['day_grids'] = ar.last(d['day_grids'] + [dict(task=t['id'], risk=risk + over, clean=missed == 0 and extra == 0)], 10, 'office.day_grids', c)
    d['filed'] += 1
    d['late'] += int(late)
    d['log'] = ar.last(d['log'] + [dict(day=c['day'], title=t['title'], late=late, mistakes=missed + extra)], 12, 'office.log', c)
    t['mistakes'] += missed + extra
    _grid_slips(t, found, fines, extra)
    # The errors that went out with the transfer are taken out of the bonus by chị Hồng (react),
    # instead of the old flat −4 per error; the fines and next-day claims stay as they were.
    reaction = cq.react(s, c, t, max(0, GRID_BONUS + adj), who='Chị Hồng')
    reward = reaction['pay']
    kit.metric(c, 'tp_filed')
    kit.metric(c, 'tp_grids')
    kit.complete(s, c, t, reward, f'Bạn đã chuyển lương “{t["title"]}”' + (' nhưng trễ giờ chốt lệnh.' if late else '.'))
    ok = sum(1 for r in res.values() if r['ok'])
    parts = [f'💸 Đã chuyển lương · {ok}/{len(res)} dòng chuẩn · thưởng +{reward} xu.']
    if missed:
        parts.append(f'Sót {missed} lỗi' + (f' (bị trừ {paid} xu)' if paid else '') + (f'; {len(claims)} người sẽ khiếu nại vào sáng mai' if claims else '') + '.')
    if extra:
        parts.append(f'Đánh dấu nhầm {extra} ô đúng — chị Hồng mất công soát lại.')
    parts += [note, reaction['message'], lunch]
    return dict(message=' '.join(x for x in parts if x), celebrate=not late and not missed and not extra)


def _grid_slips(t: dict, found: dict, fines: int, extra: int) -> None:
    """What went out wrong with the payroll, in chị Hồng's words (one slip per kind of error)."""
    if found.get('over'):
        n = len(found['over'])
        cq.slip(t, 'pay_over', 3 if n >= 2 or fines >= 20 else 2, f'Lương đã chuyển mà vẫn sót lỗi làm công ty mất tiền: {found["over"][0]}',
                'chuyển lương dư hoặc sai người')
    if found.get('under'):
        cq.slip(t, 'pay_under', 2, f'Có người bị trả thiếu lương: {found["under"][0]}', 'trả thiếu lương')
    if found.get('risk'):
        n = len(found['risk'])
        cq.slip(t, 'pay_risk', 3 if n >= 2 else 2, f'Bảng lương để lọt chỗ sai quy định: {found["risk"][0]}', 'để lọt chỗ sai quy định')
    if extra:
        cq.slip(t, 'pay_hold', 1, 'Giữ lương oan ở những ô vốn đúng, chị phải soát lại từng dòng.', 'đánh dấu nhầm ô đúng')


CLAIM_CHOICES = ('pay_now', 'next', 'deny')


def _claim(s: dict, c: dict, d: dict, o: dict, p: dict) -> dict:
    cl = next((x for x in d['claims'] if x['id'] == p.get('claim')), None)
    kit.need(cl and cl['status'] == 'open' and cl['from_day'] <= c['day'], 'Không có khiếu nại này.')
    choice = kit.one_of(p.get('choice'), CLAIM_CHOICES, 'Chọn cách xử lý khiếu nại.')
    first = cl['name'].split()[-1]
    if choice == 'pay_now':
        lunch = office.spend(o, CLAIM_MIN)
        office.trust(o, 2)
        cl['status'] = 'paid'
        d['claims_paid'] += 1
        kit.metric(c, 'tp_claims_fixed')
        msg = f'Bạn xin lỗi {first}, lập lệnh chi bổ sung {fmt(cl["amount"])} xu ngay trong ngày. {first} cảm ơn, chị Hồng gật đầu.'
        return dict(message=' '.join(x for x in (msg, lunch) if x), celebrate=True)
    if choice == 'next':
        office.trust(o, -1)
        cl['status'] = 'next'
        return dict(message=f'Hẹn {first} cộng {fmt(cl["amount"])} xu vào kỳ sau. {first} không vui nhưng đồng ý.')
    office.trust(o, -4)
    cl['status'] = 'denied'
    office.note(o, c['day'], f'{first} khiếu nại lên công đoàn vì bị từ chối trả bù.', 'fine')
    return dict(message=f'{first} cầm phiếu lương đi thẳng lên công đoàn. Chị Hồng nhìn bạn, thở dài: “Mình sai thì mình sửa chứ em.”', correct=False)


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    o = d['office']
    office.sync(o, c['day'])
    before = o['clock']
    res = care_handle(s, c, d, o, CARE, name, p, _can_cover)
    if res is None:
        res = _declare(s, c, d, o, p) if name == 'tp_declare' else _handle(s, c, name, p)
    slow = care_slow(d['care'], o, before)
    if slow:
        res['message'] = ' '.join(x for x in (res.get('message', ''), slow) if x)
    return res


def _handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    o = d['office']
    mod = _mod(c['day'])
    if name == 'tp_overtime':
        care_can_overtime(d['care'], CARE)
        kit.confirm(p, 'Xác nhận ở lại tăng ca.')
        return dict(message=office.overtime(s, c, o, 18 if mod['id'] == 'crunch' else 12, mod['id'] == 'crunch'))
    if name == 'tp_claim':
        return _claim(s, c, d, o, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Hồ sơ không thuộc bàn thuế & lương.')
    kit.need(t['known'], 'Nhận hồ sơ và đọc yêu cầu trước (bấm “Hỏi”).')
    kit.need(t['status'] != 'completed', 'Hồ sơ này đã xong.')
    gen = bool(t.get('gen'))
    grid = t['form'] == 'grid'
    if name in ('tp_flag', 'tp_row', 'tp_hint', 'tp_pay'):
        kit.need(grid, 'Hồ sơ này không có bảng lương để soát.')
    if name == 'tp_flag':
        row = _row(t, p.get('row'))
        kit.need(row['id'] not in t['reviewed'], 'Dòng này đã soát xong, không sửa dấu được nữa.')
        z = kit.one_of(p.get('cell'), [x['z'] for x in row['cells']], 'Ô này không có trong bảng lương.')
        marks = t['flags'].setdefault(row['id'], [])
        if z in marks:
            marks.remove(z)
            if not marks:
                t['flags'].pop(row['id'])
            return dict(message='', flagged=False)
        kit.need(len(marks) < MAX_FLAGS, f'Mỗi dòng đánh dấu tối đa {MAX_FLAGS} ô.')
        office.spend(o, FLAG_MIN)
        marks.append(z)
        kit.start_work(t)
        return dict(message='', flagged=True)
    if name == 'tp_row':
        row = _row(t, p.get('row'))
        kit.need(row['id'] not in t['reviewed'], 'Dòng này đã soát rồi.')
        lunch = office.spend(o, ROW_MIN)
        t['reviewed'].append(row['id'])
        kit.start_work(t)
        n = len(t['flags'].get(row['id'], []))
        left = len(t['rows']) - len(t['reviewed'])
        who = next(x['v'] for x in row['cells'] if x['z'] == 'name').split()[-1]
        msg = f'✓ Xong dòng {who}' + (f' · {n} ô cần sửa' if n else ' · không thấy sai') + '.' + (f' Còn {left} dòng.' if left else '')
        return dict(message=' '.join(x for x in (msg, lunch) if x))
    if name == 'tp_hint':
        row = _row(t, p.get('row'))
        kit.need(row['id'] not in t['reviewed'], 'Dòng này đã soát rồi.')
        lunch = office.spend(o, HINT_MIN)
        if row['id'] not in t['tips']:
            t['tips'].append(row['id'])
        kinds = row['_truth']['kinds'] or ['clean']
        return dict(message=' '.join(x for x in ('Chị Hồng gợi ý: ' + GRID_HINTS[kinds[0]], lunch) if x))
    if name == 'tp_pay':
        kit.confirm(p, 'Xác nhận chuyển lương.')
        kit.need(len(t['reviewed']) == len(t['rows']), 'Soát xong mọi dòng (“✓ Xong dòng”) rồi mới chuyển lương.')
        return _pay_grid(s, c, d, o, t, mod)
    kit.need(not grid, 'Bảng lương soát bằng cách đánh dấu ô sai, rồi chuyển lương.')
    if name == 'tp_submit':
        kit.need(isinstance(p.get('step'), str), 'Thiếu bước cần kiểm.')
        st = _current(t)
        kit.need(st is not None, 'Hồ sơ đã hoàn tất mọi bước.')
        kit.need(_well_typed(st['kind'], p.get('answer')), 'Câu trả lời chưa đúng định dạng của bước này.')
        kit.need(p['step'] == st['id'], 'Làm lần lượt từng bước nhé.')
        lunch = office.spend(o, 20) if gen else ''
        ok, msg = procedures.submit(t, p['step'], p.get('answer'))
        kit.start_work(t)
        if ok:
            kit.metric(c, 'tp_steps')
            return dict(message=' '.join(x for x in ('✓ ' + msg, lunch) if x), correct=True)
        if gen:
            o['clock'] = min(office.LOCK, o['clock'] + 15)
        return dict(message=' '.join(x for x in ('✗ Chưa khớp. ' + msg, lunch) if x), correct=False)
    if name == 'tp_file':
        kit.confirm(p, 'Xác nhận nộp/bàn giao hồ sơ.')
        kit.need(procedures.done(t), 'Hồ sơ còn bước chưa kiểm xong.')
        if gen:
            lunch = office.spend(o, 10 + office.review_cost(o))
            late, adj, note = office.settle(o, t, c['day'])
            reward = max(0, max(10, t['bonus'] - 4 * t['mistakes']) + adj)
        else:
            lunch, note = '', ''
            late = c['turn'] > t['due_turn']
            reward = 0 if late else max(10, t['bonus'] - 4 * t['mistakes'])
        t['filed'] = True
        t['late'] = late
        d['filed'] += 1
        d['late'] += int(late)
        d['log'] = ar.last(d['log'] + [dict(day=c['day'], title=t['title'], late=late, mistakes=t['mistakes'])], 12, 'office.log', c)
        kit.metric(c, 'tp_filed')
        kit.complete(s, c, t, reward, f'Bạn đã hoàn tất hồ sơ “{t["title"]}”' + (' nhưng trễ hạn nội bộ.' if late else ' đúng hạn.'))
        if late and not gen:
            return dict(message='Đã nộp nhưng trễ hạn nội bộ: không có thưởng hồ sơ.')
        head = f'Đã nộp/bàn giao hồ sơ · thưởng {reward} xu.' if gen else f'Đã nộp/bàn giao hồ sơ · thưởng {reward} xu (lương ngày trả khi khép ca).'
        return dict(message=' '.join(x for x in (head, note, lunch) if x), celebrate=not late)
    raise kit.eng().GameError('Thao tác bàn thuế & lương không hợp lệ.')


# ------------------------------------------------------------------ review
def _speed(t: dict) -> tuple[int, str]:
    if t['late']:
        return 1, 'trễ hạn'
    if type(t.get('due')) is int:
        return 5, 'kịp hạn ' + office.hhmm(t['due'])
    patience = t.get('patience', 100)
    return (5 if patience >= 80 else 4 if patience >= 60 else 3), 'nộp trong hạn'


def feedback(c: dict, t: dict) -> dict:
    speed, speed_note = _speed(t)
    if t['form'] == 'grid':
        res = t.get('results') or grade(t)
        missed = sum(len(r['missed']) for r in res.values())
        extra = sum(len(r['extra']) for r in res.values())
        risky = sum(1 for row in t['rows'] for z, dr in zip(row['_truth']['z'], row['_truth']['dirs'])
                    if dr in ('risk', 'over') and z in res[row['id']]['missed'])
        return dict(criteria=[
            dict(key='accuracy', label='Không sót lỗi', score=5 if not missed else 4 if missed == 1 else 3 if missed <= 3 else 2,
                 note='bắt hết lỗi trong bảng nháp' if not missed else f'sót {missed} lỗi'),
            dict(key='quality', label='Không giữ lương oan', score=5 if not extra else 4 if extra == 1 else 3,
                 note='chỉ đánh dấu ô sai thật' if not extra else f'đánh dấu nhầm {extra} ô đúng'),
            dict(key='care', label='Tuân thủ & an toàn', score=5 if not risky else 2,
                 note='không để lọt khoản chi sai, lương ma hay rủi ro bảo hiểm' if not risky else f'{risky} lỗi làm mất tiền hoặc sai quy định'),
            dict(key='speed', label='Đúng giờ chốt lệnh', score=speed, note=speed_note)])
    ps = t['proc_state']
    m = t['mistakes']
    acc = 5 if m == 0 else 4 if m == 1 else 3 if m <= 3 else 2
    ethic = [st['id'] for st in t['proc'] if st.get('tag') == 'ethic']
    care = 5 if all(ps['attempts'].get(x, 0) <= 1 for x in ethic) else 2
    numeric = [st['id'] for st in t['proc'] if st['kind'] in ('fields', 'number')]
    retries = sum(max(0, ps['attempts'].get(x, 0) - 1) for x in numeric)
    quality = 5 if retries == 0 else 4 if retries == 1 else 3 if retries <= 3 else 2
    return dict(criteria=[
        dict(key='accuracy', label='Số liệu chính xác', score=acc, note=f'{m} lần kiểm chưa khớp' if m else 'khớp ngay từ lần đầu'),
        dict(key='quality', label='Bảng tính rõ ràng', score=quality, note='các ô tính đúng ngay' if not retries else f'{retries} lần sửa ô số'),
        dict(key='care', label='Bảo mật & tuân thủ', score=care, note='giữ đúng nguyên tắc' if care == 5 else 'từng chọn cách làm lộ thông tin hoặc bỏ quy trình duyệt'),
        dict(key='speed', label='Đúng hạn', score=speed, note='trễ hạn nội bộ' if t['late'] else speed_note)])


# ------------------------------------------------------------------ projection & validation
def known_request(c: dict, t: dict) -> str:
    if t['form'] == 'grid':
        return f'Bảng lương có {len(t["rows"])} người — soát từng dòng rồi chuyển lương.'
    return f'Hồ sơ có {len(t["proc"])} bước — làm lần lượt.'


def _strip(v):
    if isinstance(v, dict):
        return {k: _strip(x) for k, x in v.items() if not k.startswith('_')}
    if isinstance(v, list):
        return [_strip(x) for x in v]
    return v


def public_task(t: dict) -> dict:
    v = {k: _strip(copy.deepcopy(val)) for k, val in t.items() if not k.startswith('_') and k not in ('proc', 'proc_state', 'rows', 'flags', 'results')}
    if not t['known']:
        v.update(papers=None, brief=None, steps=None, progress=None, rows=None)
        return v
    if t.get('form') == 'grid':
        res, flags, rows = t.get('results') or {}, t.get('flags') or {}, []
        for row in t.get('rows') or []:
            x = dict(id=row['id'], cells=copy.deepcopy(row['cells']), flags=list(flags.get(row['id'], [])),
                     reviewed=row['id'] in (t.get('reviewed') or []), hinted=row['id'] in (t.get('tips') or []))
            x['tip'] = GRID_HINTS[(row['_truth']['kinds'] or ['clean'])[0]] if x['hinted'] else None
            if t.get('filed') and row['id'] in res:
                x['result'] = copy.deepcopy(res[row['id']])
                x['truth'] = dict(z=list(row['_truth']['z']), why=list(row['_truth']['why']))
            rows.append(x)
        v.update(rows=rows, steps=[], progress=None,
                 grid=dict(total=len(rows), reviewed=len(t.get('reviewed') or []), flagged=sum(len(x) for x in flags.values()),
                           ok=sum(1 for r in res.values() if r['ok']) if res else None))
        return v
    v['steps'], v['progress'] = procedures.public(t)
    return v


def _validate_grid(t: dict) -> None:
    rows = {x['id']: x for x in t['rows']}
    kit.need(isinstance(t.get('flags'), dict) and isinstance(t.get('reviewed'), list) and isinstance(t.get('results'), dict)
             and isinstance(t.get('tips'), list), 'Bảng lương thiếu dữ liệu.')
    for rid, marks in t['flags'].items():
        kit.need(rid in rows and isinstance(marks, list) and 1 <= len(marks) <= MAX_FLAGS and len(set(marks)) == len(marks)
                 and all(z in [c['z'] for c in rows[rid]['cells']] for z in marks), 'Dấu trên bảng lương sai.')
    kit.need(len(set(t['reviewed'])) == len(t['reviewed']) and set(t['reviewed']) <= set(rows), 'Dòng đã soát sai.')
    kit.need(set(t['tips']) <= set(rows) and len(set(t['tips'])) == len(t['tips']), 'Gợi ý bảng lương sai.')
    if t['filed']:
        kit.need(set(t['reviewed']) == set(rows) and t['results'] == grade(t), 'Kết quả chuyển lương sai.')
    else:
        kit.need(t['results'] == {}, 'Kết quả chuyển lương sai.')
    kit.need(t['status'] != 'completed' or t['filed'], 'Bảng lương hoàn tất khi chưa chuyển.')


def validate_task(t: dict, original: dict) -> None:
    procedures.validate(t, original)
    care_validate_task(t, CARE)
    kit.need(type(t['filed']) is bool and type(t['late']) is bool, 'Trạng thái hồ sơ sai.')
    kit.need(not t['filed'] or procedures.done(t), 'Hồ sơ nộp khi chưa xong.')
    office.validate_task(t)
    if t.get('gen'):
        kit.need(isinstance(t.get('tips'), list) and len(t['tips']) <= 20 and all(isinstance(x, str) for x in t['tips']), 'Gợi ý hồ sơ sai.')
    if t.get('form') == 'grid':
        _validate_grid(t)


CLAIM_STATUS = ('open', 'paid', 'next', 'denied', 'ignored')


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.mark_legacy(c, ID)
    kit.integer(d.get('filed'), 0, 10 ** 9)
    kit.integer(d.get('late'), 0, 10 ** 9)
    log = d.get('log')
    kit.need(isinstance(log, list) and len(log) <= 12, 'Sổ hồ sơ sai.')
    for row in log:
        kit.need(isinstance(row, dict) and set(row) == {'day', 'title', 'late', 'mistakes'} and type(row['late']) is bool, 'Sổ hồ sơ sai.')
        kit.integer(row['day'], 1, 10 ** 7)
        kit.integer(row['mistakes'], 0, 10 ** 6)
        kit.text(row['title'], 200)
    for k in ('grids', 'caught', 'missed', 'false_flags', 'claims_paid'):
        kit.integer(d[k], 0, 10 ** 9)
    office.validate(d['office'])
    care_validate(d['care'], CARE)
    _validate_filings(d['care'])
    kit.need(isinstance(d['claims'], list) and len(d['claims']) <= 20, 'Sổ khiếu nại sai.')
    for cl in d['claims']:
        kit.need(isinstance(cl, dict) and set(cl) == {'id', 'day', 'from_day', 'task', 'name', 'amount', 'why', 'status'}
                 and cl['status'] in CLAIM_STATUS, 'Sổ khiếu nại sai.')
        for k in ('day', 'from_day'):
            kit.integer(cl[k], 1, 10 ** 7)
        kit.integer(cl['amount'], 0, 10 ** 6)
        for k in ('id', 'task', 'name', 'why'):
            kit.text(cl[k], 300)
    kit.need(len({cl['id'] for cl in d['claims']}) == len(d['claims']), 'Sổ khiếu nại sai.')
    kit.need(isinstance(d['day_grids'], list) and len(d['day_grids']) <= 10 and all(
        isinstance(x, dict) and set(x) == {'task', 'risk', 'clean'} and type(x['clean']) is bool and type(x['risk']) is int for x in d['day_grids']),
        'Sổ bảng lương trong ngày sai.')


def public_data(c: dict) -> dict:
    d = copy.deepcopy(kit.data(c))
    for k, v in initial().items():
        d.setdefault(k, copy.deepcopy(v))
    o = office.ensure(d)
    mod = _mod(c['day'])
    r = _rules_raw(c['day'])
    d['today'] = dict(mod=dict(id=mod['id'], emoji=mod['emoji'], name=mod['name'], text=mod['text']), rules=rules(c['day']), month=r['m'])
    d['office'] = office.public(o, c['day'])
    d['claims'] = [x for x in d['claims'] if x['status'] == 'open' and x['from_day'] <= c['day']]
    d.pop('day_grids', None)
    cr = _care(c, d)
    view = care_public(cr, CARE, c, o, _can_cover)
    view.update(calendar=_calendar(c, cr), plan=_plan_view(c, cr))
    d['care'] = view
    d['coach'] = office.coach(c, ID, _coach)
    return d


def _coach(t: dict) -> dict | None:
    """First dossier only (office.coach): the wrong cells of each row still to check, or the step's key."""
    if t.get('form') == 'grid':
        return dict(rows={r['id']: dict(z=list(r['_truth']['z']), why=list(r['_truth']['why'])) for r in t['rows'] if r['id'] not in t['reviewed']})
    return office.coach_step(t)


# ------------------------------------------------------------------ day hooks
def on_task(s: dict, c: dict, t: dict) -> None:
    if not t.get('gen'):
        return
    o = _data(c)['office']
    office.sync(o, c['day'])
    office.set_due(c, t, o)
    mod = _mod(t['day'])
    if t['form'] == 'grid' and mod['id'] == 'cutoff' and t['id'].endswith('-00'):
        t['due'] = min(t['due'], 570)                         # the bank closes the payroll batch at 09:30
    if mod['id'] == 'crunch':
        t['due'] = max(office.OPEN + 60, t['due'] - 30)


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    o = d['office']
    mod = _mod(c['day'])
    office.begin(o, c['day'])
    office.carry(c, ID, o)
    d['day_grids'] = []
    care_start(d['care'], CARE, c['day'])
    _filings(d['care'], c['day'])
    office.note(o, c['day'], f'{mod["emoji"]} {mod["name"]}: {mod["text"]}', 'day')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    o = d['office']
    office.sync(o, c['day'])
    mod = _mod(c['day'])
    grids = d['day_grids']
    out = dict(mod=dict(emoji=mod['emoji'], name=mod['name']), grids=len(grids), clean=sum(1 for x in grids if x['clean']),
               claims_new=sum(1 for x in d['claims'] if x['day'] == c['day']))
    ignored = [x for x in d['claims'] if x['status'] == 'open' and x['from_day'] <= c['day']]
    for cl in ignored:
        cl['status'] = 'ignored'
    if ignored:
        office.trust(o, -2 * len(ignored))
        out['claims_ignored'] = len(ignored)
    if mod['id'] == 'inspector' and grids:
        risky = sum(x['risk'] for x in grids)
        if risky:
            paid = office.fine(s, c, o, 10, 'Cô Lụa soát bảng lương: có khoản chi sai quy định')
            office.trust(o, -3)
            out['inspect'] = dict(ok=False, amount=paid, text=f'Cô Lụa tìm ra {risky} chỗ sai quy định trong bảng lương đã chuyển. Trừ thêm {paid} xu.')
        else:
            kit.money(s, c, 10, 'Thưởng: cô Lụa soát bảng lương không thấy sai', None, 'audit_bonus')
            office.trust(o, 3)
            kit.review(s, c, kit.npc_id(ID, 5), 5, 'Bảng lương hôm nay sạch: đúng người, đúng công, đúng mức đóng. Hồ sơ gọn gàng.', f'inspect-{c["day"]}')
            out['inspect'] = dict(ok=True, amount=10, text='Cô Lụa soát bảng lương: không chỗ nào sai quy định. Thưởng 10 xu, chị Hồng mừng ra mặt.')
    ok, why = _reliable(c, d, o)
    late = _filings_close(s, c, d['care'], o)
    if late:
        out['filings'] = late
    out['office'] = office.close_day(c, ID, o)
    out['care'] = care_close(s, c, d['care'], CARE, o, ok, why)
    d['day_grids'] = []
    return out


# ------------------------------------------------------------------ staff & hints
def _current(t: dict) -> dict | None:
    ps = t['proc_state']
    return t['proc'][ps['at']] if ps['at'] < len(t['proc']) else None


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    role = e.get('role')
    if role == 'filing':
        return 'Thư đã xếp hồ sơ theo kỳ, dán nhãn hạn nộp và cất bản gốc vào tủ có khóa.'
    if not t or t['career'] != ID or not t['known']:
        return None
    if t['form'] == 'grid':
        if role == 'payroll':
            return f'{e.get("name", "Đồng nghiệp")} ghé bàn nhắc: ' + GRID_HINTS['clean']
        return None
    st = _current(t)
    if not st:
        return f'{e.get("name", "Đồng nghiệp")} soát lại lần cuối: hồ sơ đủ bước, có thể nộp.'
    area = {'payroll': ('payslip', 'transfer', 'question'), 'tax': ('vat', 'calendar', 'yearend')}.get(role, ())
    if t['form'] in area:
        return f'{e.get("name", "Đồng nghiệp")} ghé bàn nhắc: {st["hints"][0]}'
    return None


def hint(c: dict, t: dict) -> str:
    if not t['known']:
        return 'Nhận hồ sơ, đọc yêu cầu và giấy tờ đính kèm trước.'
    if t['form'] == 'grid':
        return 'Xem quy định kỳ này → soát từng người, chạm ô sai để đánh dấu → “✓ Xong dòng” → chuyển lương trước giờ hạn.'
    st = _current(t)
    return st['hints'][0] if st else 'Mọi bước đã khớp — bấm nộp/bàn giao hồ sơ.'


def content() -> dict:
    return dict(rules=RULES, disclaimer=DISCLAIMER, forms=[dict(id=f['id'], bonus=f['bonus'], min_day=f['min_day']) for f in FORMS],
                labels=dict(payslip='Phiếu lương', transfer='Chuyển khoản lương', question='Hỏi đáp phiếu lương', vat='Tờ khai GTGT',
                            calendar='Lịch hạn nộp', yearend='Quyết toán năm', grid='Soát bảng lương'),
                boss=dict(name='Chị Hồng', npc=kit.npc_id(ID, 0)), max_flags=MAX_FLAGS,
                claim_choices=[dict(id='pay_now', label='Xin lỗi, chi bù ngay hôm nay'), dict(id='next', label='Hẹn cộng vào kỳ sau'),
                               dict(id='deny', label='Bảo là phần mềm tính, không sửa')])


# ------------------------------------------------------------------ office care: colleagues, mentor, the filing calendar
# The shared helpers (energy, colleagues, reliable days, mentor track) live in corp_accounting.py.
CARE = dict(
    id=ID, prefix='tp_', boss='Chị Hồng',
    ranks=('Thử việc', 'Chuyên viên lương chính thức', 'Phụ trách hồ sơ Xưởng Chỉ Vàng', 'Được đề cử trưởng nhóm lương'),
    lines=('Ba ngày không sai một dòng lương. Chị ký chính thức cho em nhé.',
           'Từ nay em phụ trách hồ sơ Xưởng Chỉ Vàng. Diệu hỏi gì em trả lời giúp chị.',
           'Chị đã đề cử em làm trưởng nhóm lương. Em làm chị yên tâm lắm.'),
    mates=[
        dict(id='binh', name='Bình', role='Chuyên viên lương mới vào', npc=None, emoji='🐣',
             asks=[('Bảng chấm công tổ 2 em nhập mãi không khớp, soát cùng em một lượt nhé?', 20),
                   ('Người phụ thuộc nộp sau mốc thì tính từ kỳ nào ạ? Em hỏi hơi ngố…', 15)],
             thanks='Bình ghi ngay vào sổ tay: “Hiểu rồi! Cảm ơn nhiều.”', no='Bình gật đầu: “Dạ, em hỏi chị Ngân vậy.”',
             cover='Bình nhập giúp phần số liệu —'),
        dict(id='hoa', name='Chị Hoa', role='Tổ trưởng chuyền may · Xưởng Chỉ Vàng', npc=6, emoji='📋',
             asks=[('Phiếu tăng ca tổ chị viết tay, em xem giúp chị ghi vậy đúng mẫu chưa?', 20),
                   ('Công nhân mới hỏi phiếu lương, em giải thích giúp chị mấy dòng bảo hiểm nha?', 25)],
             thanks='Chị Hoa cười: “Cần chữ ký tổ lúc nào cứ gọi chị.”', no='Chị Hoa: “Ừ, để chị hỏi chị Hồng.”',
             cover='Chị Hoa mang bảng chấm công ký sẵn qua tận nơi —'),
        dict(id='bay', name='Chú Bảy', role='Chủ quán Cà phê Mộc Miên', npc=3, emoji='☕',
             asks=[('Hộp hóa đơn tháng này của chú lộn xộn quá, con phân loại giúp chú?', 25),
                   ('Chú muốn mua máy xay mới: chuyển khoản hay trả tiền mặt thì đúng quy định hả con?', 15)],
             thanks='Chú Bảy mang sang ly cà phê muối: “Chú mời.”', no='Chú Bảy: “Không sao, mai chú ghé.”',
             cover='Chú Bảy tự gom đủ hóa đơn mang tới bàn —'),
    ])
DOM = (5, 12, 19, 26, 30)                     # the five working days of a pay month, as dates
FILINGS = [
    dict(id='pit', emoji='🧾', name='Tờ khai thuế TNCN tháng {prev}', who='Xưởng may Chỉ Vàng', open=0, due=1, minutes=25, needs=None,
         what='Khai phần thuế thu nhập cá nhân đã khấu trừ của công nhân tháng trước.'),
    dict(id='ins', emoji='🛡️', name='Hồ sơ BHXH tháng {m}', who='Xưởng may Chỉ Vàng', open=1, due=2, minutes=20, needs='grid',
         what='Nộp tiền bảo hiểm theo bảng lương đã chuyển trong tháng.'),
    dict(id='vat', emoji='📑', name='Báo cáo sử dụng hóa đơn tháng {prev}', who='Quán Cà phê Mộc Miên', open=1, due=3, minutes=30, needs=None,
         what='Kê số hóa đơn quán Chú Bảy đã dùng, đã hủy trong tháng.'),
]
FILING_INDEX = {f['id']: f for f in FILINGS}
FILING_SHORT = dict(pit='Thuế TNCN', ins='BHXH', vat='Báo cáo HĐ')
FILING_STATES = ('todo', 'filed', 'boss')
LATE_FEE = 3


def _month(day: int) -> int:
    return (max(1, day) - 1) // 5


def _fname(f: dict, day: int) -> str:
    r = _rules_raw(day)
    return f['name'].format(prev=r['prev'], m=r['m'])


def _fdate(day: int, phase: int) -> str:
    return f'{DOM[phase]}/{_rules_raw(day)["m"]}'


def _filings(cr: dict, day: int) -> dict:
    """This pay month's filing calendar (a new month starts with every filing to do)."""
    fl = cr.get('filings')
    if not isinstance(fl, dict) or fl.get('month') != _month(day):
        fl = cr['filings'] = dict(month=_month(day), grids=0, st={f['id']: dict(s='todo', day=0, fee=0) for f in FILINGS})
    return fl


def _care(c: dict, d: dict) -> dict:
    cr = care_ensure(d, CARE)
    if 'filings' not in cr:
        # Saves made before the calendar, in the middle of a month: filings already past due count as handled.
        fl = _filings(cr, c['day'])
        phase = (c['day'] - 1) % 5
        for f in FILINGS:
            if f['due'] < phase:
                fl['st'][f['id']].update(s='filed', day=c['day'] - phase)
        fl['grids'] = sum(1 for x in d.get('log', []) if _month(x['day']) == fl['month'] and x['title'].startswith('Soát bảng lương'))
    return cr


def _declare(s: dict, c: dict, d: dict, o: dict, p: dict) -> dict:
    day = c['day']
    fl = _filings(d['care'], day)
    f = FILING_INDEX.get(p.get('filing')) if isinstance(p.get('filing'), str) else None
    kit.need(f, 'Không có tờ khai này trong lịch nộp.')
    st = fl['st'][f['id']]
    kit.need(st['s'] == 'todo', 'Tờ khai này đã nộp rồi.' if st['s'] == 'filed' else 'Chị Hồng đã nộp thay tờ khai này.')
    phase = (day - 1) % 5
    name = _fname(f, day)
    kit.need(phase >= f['open'], f'Chưa tới kỳ khai {name} — mở từ ngày {_fdate(day, f["open"])}.')
    if f['needs'] == 'grid':
        kit.need(fl['grids'] >= 1, 'Chưa có bảng lương nào được chuyển trong tháng — soát và chuyển lương trước, rồi mới có số để nộp BHXH.')
    kit.confirm(p, f'Xác nhận ký số và nộp {name}.')
    lunch = office.spend(o, f['minutes'])
    st.update(s='filed', day=day)
    kit.metric(c, 'tp_filings')
    late = phase - f['due']
    if late <= 0:
        office.trust(o, 1)
        kit.metric(c, 'tp_filings_on_time')
        msg = f'📨 Đã nộp {name} cho {f["who"]} — đúng hạn {_fdate(day, f["due"])}. Chị Hồng gật đầu.'
    else:
        msg = f'📨 Đã nộp {name}, muộn {late} ngày. Tiền chậm nộp Minh Bạch chịu thay khách: {st["fee"]} xu — từ giờ không tính thêm.'
    return dict(message=' '.join(x for x in (msg, lunch) if x), celebrate=late <= 0)


def _filings_close(s: dict, c: dict, cr: dict, o: dict) -> list:
    """End of day: every filing past its due day costs a late fee; on the last day chị Hồng files what is left."""
    day = c['day']
    fl = _filings(cr, day)
    phase = (day - 1) % 5
    out = []
    for f in FILINGS:
        st = fl['st'][f['id']]
        if st['s'] != 'todo' or phase < f['due']:
            continue
        name = _fname(f, day)
        paid = office.fine(s, c, o, LATE_FEE, f'Tiền chậm nộp: {name}')
        st['fee'] += paid
        if phase == f['due']:
            office.trust(o, -1)
            office.note(o, day, f'Quá hạn {name} — mỗi ngày chậm là {LATE_FEE} xu tiền chậm nộp.', 'late')
        boss = phase == 4
        if boss:
            st.update(s='boss', day=day)
            office.trust(o, -3)
            office.note(o, day, f'Chị Hồng tự nộp thay {name} cho kịp khép tháng.', 'late')
        out.append(dict(name=name, fee=paid, boss=boss))
    return out


def _reliable(c: dict, d: dict, o: dict) -> tuple[bool, str]:
    done = sum(1 for x in d['log'] if x['day'] == c['day'])
    if not done:
        return False, 'Chưa nộp hồ sơ nào'
    if o['day_late']:
        return False, f'{o["day_late"]} hồ sơ trễ hạn'
    if sum(x['risk'] for x in d['day_grids']):
        return False, 'Bảng lương để lọt lỗi sai quy định'
    return True, f'{done} hồ sơ kịp hạn, bảng lương an toàn'


def _can_cover(t: dict, day: int) -> str:
    if t.get('form') == 'grid' and _mod(day)['id'] == 'cutoff':
        return 'Hôm nay ngân hàng chốt lệnh đúng giờ — không ai xin lùi được.'
    return ''


def _filing_state(f: dict, st: dict, phase: int) -> str:
    if st['s'] == 'boss':
        return 'boss'
    if st['s'] == 'filed':
        return 'filed' if (st['day'] - 1) % 5 <= f['due'] else 'late_filed'
    return 'late' if phase > f['due'] else 'due' if phase == f['due'] else 'todo' if phase >= f['open'] else 'locked'


def _calendar(c: dict, cr: dict) -> list:
    day = c['day']
    fl = _filings(copy.deepcopy(cr), day)
    phase = (day - 1) % 5
    cells = []
    for i in range(5):
        dd = day + i
        ph, same = (dd - 1) % 5, _month(dd) == fl['month']
        items = []
        if i == 0:
            items += [dict(emoji=f['emoji'], text=FILING_SHORT[f['id']], state='late') for f in FILINGS if f['due'] < phase and fl['st'][f['id']]['s'] == 'todo']
        for f in FILINGS:
            if f['due'] == ph:
                st = fl['st'][f['id']] if same else dict(s='todo', day=0, fee=0)
                items.append(dict(emoji=f['emoji'], text=FILING_SHORT[f['id']], state='done' if st['s'] != 'todo' else 'due' if i == 0 else 'todo'))
        if ph == 4:
            items.append(dict(emoji='💸', text='Trả lương', state='info'))
        mod = _mod(dd)
        cells.append(dict(day=dd, date=_fdate(dd, ph), rel=care_rel(i), mod=None if mod['id'] == 'normal' else dict(emoji=mod['emoji'], name=mod['name']),
                          items=items))
    return cells


def _plan_view(c: dict, cr: dict) -> dict:
    day = c['day']
    fl = _filings(cr, day)
    phase = (day - 1) % 5
    items = []
    for f in FILINGS:
        st = fl['st'][f['id']]
        state = _filing_state(f, st, phase)
        why = ''
        if state == 'locked':
            why = f'Mở từ ngày {_fdate(day, f["open"])}'
        elif f['needs'] == 'grid' and not fl['grids'] and st['s'] == 'todo':
            why = 'Cần chuyển một bảng lương trong tháng trước'
        items.append(dict(id=f['id'], emoji=f['emoji'], name=_fname(f, day), who=f['who'], what=f['what'], minutes=f['minutes'],
                          date=_fdate(day, f['due']), rel=care_rel(f['due'] - phase) if f['due'] >= phase else f'Trễ {phase - f["due"]} ngày',
                          state=state, fee=st['fee'], can=st['s'] == 'todo' and not why, why=why))
    return dict(kind='filings', title=f'Lịch nộp tháng {_rules_raw(day)["m"]}', items=items, fee=LATE_FEE, payday=_fdate(day, 4),
                grids=fl['grids'], done=sum(1 for x in items if x['state'] in ('filed', 'late_filed', 'boss')), total=len(items))


def _validate_filings(cr: dict) -> None:
    fl = cr.get('filings')
    kit.need(isinstance(fl, dict) and set(fl) == {'month', 'grids', 'st'} and isinstance(fl['st'], dict)
             and set(fl['st']) == set(FILING_INDEX), 'Lịch nộp sai.')
    kit.integer(fl['month'], 0, 10 ** 6)
    kit.integer(fl['grids'], 0, 10 ** 4)
    for st in fl['st'].values():
        kit.need(isinstance(st, dict) and set(st) == {'s', 'day', 'fee'} and st['s'] in FILING_STATES, 'Lịch nộp sai.')
        kit.integer(st['day'], 0 if st['s'] == 'todo' else 1, 0 if st['s'] == 'todo' else 10 ** 7)
        kit.integer(st['fee'], 0, LATE_FEE * 5)


# ------------------------------------------------------------------ people & situations
PEOPLE = [
    ('Chị Hồng', 'Kế toán trưởng', 'Kỹ tính, ghét nhất câu “chắc là đúng”.', 'picky'),
    ('Anh Phát', 'Giám đốc Xưởng may Chỉ Vàng', 'Quý công nhân nhưng hay muốn “linh động” giấy tờ.', 'bossy'),
    ('Em Diệu', 'Công nhân may', 'Mới đi làm năm đầu, soi phiếu lương từng dòng.', 'genz'),
    ('Chú Bảy', 'Chủ quán Cà phê Mộc Miên', 'Hiền, gom hóa đơn vào hộp bánh quy.', 'warm'),
    ('Anh Khôi', 'Kỹ thuật viên bảo trì', 'Ít nói, làm thêm buổi tối ở tiệm sửa máy.', 'quiet'),
    ('Cô Lụa', 'Cán bộ thuế phường', 'Nghiêm, nói ít nhưng câu nào cũng có văn bản.', 'sour'),
    ('Chị Hoa', 'Tổ trưởng chuyền may', 'Thương công nhân, hay muốn “linh động” giấy tờ cho kịp.', 'warm'),
]

SITUATIONS = [
    dict(id='TP-S01', title='Xin nhận tiền mặt để khỏi đóng bảo hiểm', npc=2, tone='gentle', min_day=1,
         opening='Diệu kéo bạn ra góc: “Anh chị ơi, tháng này cho em nhận tiền mặt, đừng trừ bảo hiểm được không? Em đang cần tiền gửi về quê.”',
         swap='Bạn là cô công nhân năm đầu, mẹ ở quê vừa ốm, mỗi trăm xu đều quý.',
         facts=[dict(id='rule', title='Quy định về bảo hiểm', source='Sổ tay lương', text='Bảo hiểm bắt buộc trừ theo hợp đồng lao động; không có lựa chọn “tháng này thôi đóng”.'),
                dict(id='benefit', title='Quyền lợi của Diệu', source='Hồ sơ bảo hiểm', text='Có BHYT, Diệu được chi trả phần lớn tiền khám; có BHXH, sau này có lương hưu, thai sản.'),
                dict(id='advance', title='Quy chế tạm ứng', source='Quy chế xưởng', text='Người lao động được tạm ứng tối đa 30% lương tháng, trừ dần vào kỳ sau.')],
         options=[dict(id='advance', label='Giải thích vì sao không bỏ bảo hiểm được, hướng dẫn Diệu làm đơn tạm ứng lương',
                       requires=['rule', 'advance'], quality='good', stars=5,
                       review='Hông được như em xin, nhưng được chỉ cách tạm ứng liền. Mẹ em đi khám còn được bảo hiểm trả nữa 🥹',
                       outcome='Diệu nhận tạm ứng trong ngày, mẹ đi khám có thẻ BHYT. Không ai phải lách luật.',
                       perspectives=[dict(who='Diệu', emoji='🧵', text='Em tưởng bảo hiểm chỉ là bị trừ tiền, giờ mới biết nó giữ cho mình.'),
                                     dict(who='Chị Hồng', emoji='📒', text='Bảng lương sạch, không có dòng “ngoài sổ”.'),
                                     dict(who='Anh Phát', emoji='🏭', text='Tạm ứng có quy chế, xưởng không bị truy thu sau này.')]),
                  dict(id='cash', label='Thương tình, chi tiền mặt ngoài sổ, không trừ bảo hiểm tháng này', quality='bad', stars=2,
                       review='Nhận đủ tiền mà giờ đi khám thì thẻ bảo hiểm bị báo gián đoạn… Sao hồi đó không ai nói em?',
                       outcome='Thẻ BHYT của Diệu bị gián đoạn; xưởng bị nhắc nợ bảo hiểm và phải nộp bù kèm lãi.',
                       perspectives=[dict(who='Diệu', emoji='😣', text='Lúc đó vui, giờ mới thấy thiệt.'),
                                     dict(who='Cô Lụa', emoji='🗂️', text='Chi lương ngoài sổ là rủi ro cho cả người lao động lẫn doanh nghiệp.')]),
                  dict(id='refuse', label='Từ chối gọn: “Quy định rồi em”', quality='ok', stars=3,
                       review='Đúng quy định nhưng em vẫn chưa biết xoay tiền ở đâu.',
                       outcome='Diệu đi vay bên ngoài với lãi cao.',
                       perspectives=[dict(who='Diệu', emoji='😔', text='Em cần một lối ra, không chỉ một chữ “không”.'),
                                     dict(who='Chị Hồng', emoji='🤔', text='Đúng luật, nhưng mình còn công cụ tạm ứng mà.')])],
         lesson='Nói “không” với việc lách luật, và luôn kèm một lối ra hợp lệ.'),
    dict(id='TP-S02', title='Giám đốc muốn “gửi” lương cho bạn', npc=1, tone='tense', min_day=2,
         opening='Anh Phát nói nhỏ: “Em thêm tên bạn anh vào bảng lương, 8.000 xu mỗi tháng. Cậu ấy không làm ở đây đâu, anh giúp chút thôi.”',
         swap='Bạn là giám đốc xưởng muốn giúp người bạn lúc khó khăn, nghĩ đó là tiền của mình.',
         facts=[dict(id='payroll', title='Bảng chấm công', source='Hồ sơ nhân sự', text='Người bạn không có hợp đồng lao động, không có ngày công nào.'),
                dict(id='rule', title='Quy định về chi phí lương', source='Sổ tay thuế', text='Lương chỉ được tính là chi phí khi có người làm thật, hợp đồng và chấm công.'),
                dict(id='option', title='Cách hợp lệ', source='Chị Hồng', text='Muốn giúp bạn thì anh có thể cho vay cá nhân hoặc thuê làm việc thật, có hợp đồng.')],
         options=[dict(id='written', label='Từ chối thêm “lương ma”, gửi anh Phát email ngắn kèm hai cách giúp hợp lệ',
                       requires=['payroll', 'rule'], quality='good', stars=4,
                       review='Em làm anh hơi quê, nhưng email rõ ràng. Anh chọn cho bạn vay riêng.',
                       outcome='Anh Phát cho bạn vay cá nhân; bảng lương xưởng vẫn sạch.',
                       perspectives=[dict(who='Anh Phát', emoji='🏭', text='Hóa ra có cách giúp mà không kéo xưởng vào rắc rối.'),
                                     dict(who='Bạn (người làm lương)', emoji='🧮', text='Email là bằng chứng mình đã tư vấn đúng.'),
                                     dict(who='Công nhân', emoji='🧵', text='Tiền lương của xưởng chỉ trả cho người làm thật.')]),
                  dict(id='quiet', label='Làm theo cho êm, không ghi lại gì', quality='bad', stars=2,
                       review='Lúc đầu thì êm. Đến khi thanh tra hỏi “người này làm ở bộ phận nào” thì hết êm.',
                       outcome='Kiểm tra phát hiện chi phí lương khống; xưởng bị truy thu và phạt, bạn phải giải trình.',
                       perspectives=[dict(who='Cô Lụa', emoji='🗂️', text='Không có hợp đồng, không chấm công — không thể là chi phí lương.'),
                                     dict(who='Chị Hồng', emoji='😟', text='Người lập bảng lương cũng phải chịu trách nhiệm.')]),
                  dict(id='expose', label='Kể chuyện này cho cả phòng nghe', quality='bad', stars=2,
                       review='Chuyện chưa làm gì mà cả xưởng đồn ầm lên.',
                       outcome='Không khí căng thẳng; anh Phát mất mặt, bạn mất lòng tin của khách hàng.',
                       perspectives=[dict(who='Anh Phát', emoji='😤', text='Có gì thì nói riêng với anh chứ.'),
                                     dict(who='Đồng nghiệp', emoji='👀', text='Chuyện riêng của khách không nên thành chuyện trà dư.')])],
         lesson='Từ chối việc sai bằng văn bản, riêng tư và kèm lựa chọn hợp lệ.'),
    dict(id='TP-S03', title='Đồng nghiệp hỏi lương người khác', npc=4, tone='gentle', min_day=1,
         opening='Anh Khôi ghé bàn: “Tò mò chút, con bé Trang bên QC lương bao nhiêu mà nghe đâu hơn tôi?”',
         swap='Bạn là kỹ thuật viên làm lâu năm, nghe đồn người mới lương cao hơn mình và thấy chạnh lòng.',
         facts=[dict(id='policy', title='Quy định bảo mật', source='Sổ tay nhân sự', text='Lương từng người là thông tin riêng; chỉ người phụ trách được xem.'),
                dict(id='scale', title='Thang lương công khai', source='Bảng tin xưởng', text='Xưởng có thang bậc lương theo vị trí và thâm niên, ai cũng xem được.'),
                dict(id='feel', title='Nghe anh Khôi nói', source='Anh Khôi', text='Anh làm 6 năm, chưa được xét nâng bậc lần nào.')],
         options=[dict(id='grade', label='Không nói lương của Trang; chỉ anh Khôi thang lương công khai và cách đề nghị xét nâng bậc',
                       requires=['policy', 'scale'], quality='good', stars=5,
                       review='Không moi được lương người ta, nhưng biết mình đủ điều kiện xét bậc mới. Được.',
                       outcome='Anh Khôi nộp đề nghị xét nâng bậc và được duyệt ở kỳ sau.',
                       perspectives=[dict(who='Anh Khôi', emoji='🔧', text='Điều tôi cần là được xét công bằng, không phải biết lương người khác.'),
                                     dict(who='Trang', emoji='🔍', text='May mà lương mình không thành chuyện bàn tán.'),
                                     dict(who='Chị Hồng', emoji='📒', text='Minh bạch cách tính, bảo mật con số từng người.')]),
                  dict(id='hint', label='Ra hiệu “cũng hơn anh chút xíu”', quality='bad', stars=2,
                       review='Nghe xong còn bực hơn. Mà sao người làm lương lại đi kể?',
                       outcome='Tin đồn lan ra, Trang bị xa lánh; bạn bị nhắc vì làm lộ thông tin.',
                       perspectives=[dict(who='Trang', emoji='😢', text='Mình không làm gì sai mà bị nói ra nói vào.'),
                                     dict(who='Anh Khôi', emoji='😒', text='Biết rồi cũng chẳng giúp gì tôi.')]),
                  dict(id='report', label='Báo quản lý rằng anh Khôi dò hỏi lương', quality='ok', stars=3,
                       review='Hỏi một câu mà bị báo lên sếp, hơi quá.',
                       outcome='Thông tin được giữ kín, nhưng anh Khôi thấy mình bị “đánh dấu”.',
                       perspectives=[dict(who='Anh Khôi', emoji='😶', text='Tôi chỉ cần một lời giải thích.'),
                                     dict(who='Quản lý', emoji='🤷', text='Chuyện này tự giải thích được mà.')])],
         lesson='Giữ bí mật lương từng người, nhưng giúp người hỏi hiểu con đường công bằng của chính họ.'),
    dict(id='TP-S04', title='Thư của cơ quan thuế: số liệu lệch', npc=5, tone='tense', min_day=3,
         opening='Cô Lụa gửi thư: “Tờ khai TNCN quý trước của Xưởng Chỉ Vàng lệch 350 xu so với dữ liệu chứng từ khấu trừ. Đề nghị giải trình.”',
         swap='Bạn là cán bộ thuế phải đối chiếu hàng trăm hồ sơ, chỉ cần một lời giải thích có chứng từ.',
         facts=[dict(id='ledger', title='Đối chiếu bảng lương', source='Sổ lương', text='Có một khoản thưởng 350 xu ghi nhầm vào tháng sau khi lập tờ khai.'),
                dict(id='deadline', title='Hạn trả lời', source='Thư', text='Hạn giải trình: 10 ngày kể từ ngày nhận thư.'),
                dict(id='fix', title='Cách sửa', source='Sổ tay thuế', text='Nộp tờ khai bổ sung kèm bảng giải trình và chứng từ; tiền chậm nộp (nếu có) tính theo ngày.')],
         options=[dict(id='explain', label='Tìm ra khoản thưởng ghi nhầm, nộp tờ khai bổ sung kèm giải trình trong hạn',
                       requires=['ledger', 'fix'], quality='good', stars=5,
                       review='Giải trình đúng hạn, có chứng từ. Hồ sơ khép lại.',
                       outcome='Hồ sơ được chấp nhận; xưởng chỉ nộp phần chậm nộp nhỏ.',
                       perspectives=[dict(who='Cô Lụa', emoji='🗂️', text='Sai sót được tự phát hiện và sửa luôn thì xử lý nhẹ nhàng.'),
                                     dict(who='Anh Phát', emoji='🏭', text='Tưởng to chuyện, hóa ra một dòng ghi nhầm.'),
                                     dict(who='Chị Hồng', emoji='📒', text='Từ nay khóa sổ lương rồi mới lập tờ khai.')]),
                  dict(id='ignore', label='Để đó, chắc họ quên', quality='bad', stars=1,
                       review='Quá hạn không phản hồi, hồ sơ chuyển sang kiểm tra.',
                       outcome='Xưởng bị kiểm tra, mất cả tuần làm việc cho một lỗi 350 xu.',
                       perspectives=[dict(who='Cô Lụa', emoji='📮', text='Thư không trả lời thì phải làm theo quy trình tiếp theo.'),
                                     dict(who='Anh Phát', emoji='😠', text='Sao không ai báo tôi?')]),
                  dict(id='pay', label='Nộp luôn 350 xu cho xong, không giải trình', quality='ok', stars=3,
                       review='Tiền đã nộp nhưng số liệu vẫn chưa được sửa trên tờ khai.',
                       outcome='Khoản lệch vẫn nằm trên hồ sơ; năm sau lại bị hỏi.',
                       perspectives=[dict(who='Chị Hồng', emoji='😕', text='Nộp tiền không thay được việc sửa số.'),
                                     dict(who='Cô Lụa', emoji='🗂️', text='Cần tờ khai bổ sung để dữ liệu khớp.')])],
         lesson='Thư của cơ quan thuế: tìm nguyên nhân, sửa bằng hồ sơ, trả lời trong hạn.'),
    dict(id='TP-S05', title='Hạn nộp rơi đúng Tết', npc=0, tone='gentle', min_day=2,
         opening='Chị Hồng nhìn lịch: “Hạn tờ khai tháng 1 rơi giữa Tết. Em tính sao, nộp trước hay chờ ra Tết?”',
         swap='Bạn là kế toán trưởng, Tết nào cũng lo khách hàng bị phạt vì quên hạn.',
         facts=[dict(id='rule', title='Quy định về ngày nghỉ', source='Sổ tay thuế', text='Hạn rơi vào ngày nghỉ lễ được lùi sang ngày làm việc đầu tiên sau kỳ nghỉ.'),
                dict(id='data', title='Số liệu đã sẵn', source='Bảng lương', text='Lương tháng 1 đã chốt trước Tết, đủ để lập tờ khai.'),
                dict(id='risk', title='Ra Tết', source='Kinh nghiệm chị Hồng', text='Ngày đầu ra Tết cổng thuế rất đông, mạng hay chậm.')],
         options=[dict(id='early', label='Nộp trước Tết khi số liệu đã chốt, lưu thông báo tiếp nhận', requires=['data'], quality='good', stars=5,
                       review='Nộp trước Tết, ăn Tết yên tâm!', outcome='Tờ khai được tiếp nhận trước kỳ nghỉ; không ai phải trực Tết.',
                       perspectives=[dict(who='Chị Hồng', emoji='🧧', text='Làm sớm một ngày, yên tâm cả tuần.'),
                                     dict(who='Khách hàng', emoji='🏭', text='Không có thư nhắc hạn nào sau Tết.')]),
                  dict(id='after', label='Chờ ra Tết nộp đúng ngày được lùi hạn', requires=['rule'], quality='ok', stars=4,
                       review='Vẫn đúng hạn, nhưng ngày đầu năm hơi hồi hộp.', outcome='Cổng thuế chậm, mãi chiều mới nộp được — vẫn kịp.',
                       perspectives=[dict(who='Chị Hồng', emoji='😅', text='Đúng luật, nhưng suýt nữa thì trễ.'),
                                     dict(who='Bạn', emoji='🧮', text='Hạn lùi là quyền, không phải lời khuyên chờ.')]),
                  dict(id='forget', label='Tết mà, qua Tết tính', quality='bad', stars=2,
                       review='Quên luôn, ra Tết một tuần mới nhớ.', outcome='Nộp trễ, khách hàng chịu tiền chậm nộp.',
                       perspectives=[dict(who='Khách hàng', emoji='😠', text='Thuê dịch vụ là để khỏi lo chuyện này.'),
                                     dict(who='Chị Hồng', emoji='😞', text='Lịch hạn phải được ghi, không được nhớ miệng.')])],
         lesson='Biết luật lùi hạn, nhưng làm sớm khi có thể.'),
    dict(id='TP-S06', title='Chuyển lương dư cho người lao động', npc=2, tone='tense', min_day=2,
         opening='Kiểm sao kê, bạn thấy Diệu được chuyển 6.800 xu thay vì 680 xu tiền thưởng — gõ dư một số 0.',
         swap='Bạn là Diệu, tự nhiên thấy tài khoản dư một khoản lớn, vừa mừng vừa sợ.',
         facts=[dict(id='statement', title='Sao kê ngân hàng', source='Ngân hàng', text='Lệnh thưởng 680 xu bị nhập thành 6.800 xu; dư 6.120 xu.'),
                dict(id='story', title='Hỏi thăm Diệu', source='Diệu', text='Diệu đã lỡ dùng 1.000 xu đóng tiền trọ vì tưởng được thưởng Tết sớm.'),
                dict(id='rule', title='Quy chế xưởng', source='Quy chế', text='Khoản chi nhầm được thỏa thuận hoàn lại; có thể trừ dần nếu người lao động đồng ý bằng văn bản.')],
         options=[dict(id='agree', label='Xin lỗi Diệu vì lỗi của phòng lương, thỏa thuận hoàn 5.120 xu ngay và trừ dần 1.000 xu trong 4 tháng, có văn bản',
                       requires=['statement', 'rule'], quality='good', stars=5,
                       review='Phòng lương xin lỗi đàng hoàng, còn cho em trả dần. Em ký giấy liền.',
                       outcome='Khoản dư được thu hồi đúng quy chế; Diệu không bị sốc tài chính.',
                       perspectives=[dict(who='Diệu', emoji='🧵', text='Lỗi đâu phải của em, được đối xử tử tế nên em hợp tác liền.'),
                                     dict(who='Chị Hồng', emoji='📒', text='Có văn bản thỏa thuận thì sổ sách rõ ràng.'),
                                     dict(who='Anh Phát', emoji='🏭', text='Tiền về đủ, công nhân vẫn quý xưởng.')]),
                  dict(id='deduct', label='Trừ hết 6.120 xu vào lương tháng sau, không cần hỏi', quality='bad', stars=1,
                       review='Tự nhiên lương tháng sau còn có chút xíu, không ai nói gì trước!',
                       outcome='Diệu không đủ tiền sinh hoạt, khiếu nại lên công đoàn.',
                       perspectives=[dict(who='Diệu', emoji='😭', text='Lỗi của phòng lương mà em gánh hết.'),
                                     dict(who='Công đoàn', emoji='📣', text='Khấu trừ phải có thỏa thuận và mức hợp lý.')]),
                  dict(id='ignore', label='Thôi bỏ qua, coi như thưởng thêm', quality='bad', stars=3,
                       review='Vui thì vui, nhưng sao người khác không có?',
                       outcome='Sổ sách lệch 6.120 xu, quỹ lương hụt; đồng nghiệp biết chuyện thấy bất công.',
                       perspectives=[dict(who='Chị Hồng', emoji='😟', text='Tiền của xưởng không phải của phòng lương để cho.'),
                                     dict(who='Đồng nghiệp', emoji='🙄', text='Làm sai mà được thưởng à?')])],
         lesson='Nhận lỗi của mình, thu hồi đúng quy chế, và nghĩ tới hoàn cảnh người nhận.'),
    dict(id='TP-S07', title='Chủ doanh nghiệp nhờ “thêm chi phí”', npc=1, tone='tense', min_day=3,
         opening='Anh Phát đưa xấp hóa đơn: “Em đưa mấy cái này vào chi phí giùm anh cho thuế nhẹ bớt. Có hóa đơn đàng hoàng mà.”',
         swap='Bạn là chủ xưởng thấy thuế nặng, nghe bạn bè mách “mua hóa đơn” cho nhẹ.',
         facts=[dict(id='invoices', title='Soi xấp hóa đơn', source='Hóa đơn', text='Tiệc gia đình, vé du lịch của người nhà và hóa đơn từ một công ty không có giao dịch thật.'),
                dict(id='rule', title='Quy định về chi phí', source='Sổ tay thuế', text='Chi phí được trừ phải phục vụ kinh doanh, có hóa đơn hợp lệ và giao dịch thật.'),
                dict(id='legal', title='Cách giảm thuế hợp lệ', source='Chị Hồng', text='Rà lại chi phí thật còn bỏ sót: sửa máy, đào tạo, bảo hộ lao động có chứng từ.')],
         options=[dict(id='refuse', label='Từ chối đưa hóa đơn khống vào sổ; cùng anh Phát rà các chi phí thật còn sót', requires=['invoices', 'rule'],
                       quality='good', stars=4, review='Không “nhẹ” được như anh muốn, nhưng tìm ra 3 khoản chi thật bị bỏ sót. Được việc.',
                       outcome='Xưởng khai đủ chi phí thật, thuế giảm hợp lệ; sổ sách sạch khi kiểm tra.',
                       perspectives=[dict(who='Anh Phát', emoji='🏭', text='Hóa ra mình bỏ sót chi phí thật mà không biết.'),
                                     dict(who='Cô Lụa', emoji='🗂️', text='Hồ sơ rõ ràng thì kiểm tra rất nhanh.'),
                                     dict(who='Bạn', emoji='🧮', text='Chữ ký của mình trên sổ là uy tín nghề.')]),
                  dict(id='comply', label='Chiều khách, ghi hết vào chi phí', quality='bad', stars=2,
                       review='Năm nay nhẹ thuế, năm sau bị truy thu gấp mấy lần.',
                       outcome='Kiểm tra phát hiện hóa đơn khống; xưởng bị truy thu, phạt, dịch vụ mất uy tín.',
                       perspectives=[dict(who='Anh Phát', emoji='😰', text='Tưởng giúp mình, hóa ra hại mình.'),
                                     dict(who='Chị Hồng', emoji='😞', text='Dịch vụ của mình ký tên trên hồ sơ sai.')]),
                  dict(id='quit', label='Tuyên bố dừng hợp đồng dịch vụ ngay', quality='ok', stars=3,
                       review='Làm căng quá, anh chỉ hỏi thôi mà.', outcome='Mất một khách hàng; anh Phát tìm dịch vụ khác “dễ tính” hơn.',
                       perspectives=[dict(who='Anh Phát', emoji='😤', text='Giải thích cho tôi hiểu đã chứ.'),
                                     dict(who='Chị Hồng', emoji='🤔', text='Giữ nguyên tắc đúng, nhưng còn cách tư vấn tốt hơn.')])],
         lesson='Không đưa chi phí khống vào sổ; giúp khách tìm những khoản giảm thuế hợp lệ.'),
    dict(id='TP-S08', title='Tổ trưởng xin “ký hộ” phiếu tăng ca', npc=6, tone='gentle', min_day=2,
         opening='Chị Hoa chạy lên phòng lương: “Tối qua cả tổ ở lại chạy đơn gấp tới 9 giờ, anh quản đốc đi công tác chưa ký phiếu tăng ca. Em cứ tính luôn nha, chị ký thay cho!”',
         swap='Bạn là tổ trưởng: cả tổ đã thức khuya chạy đơn, giờ sợ mất tiền tăng ca vì một chữ ký.',
         facts=[dict(id='rule', title='Quy chế tăng ca', source='Sổ tay lương', text='Tăng ca chỉ được trả khi có phiếu duyệt của quản đốc; được duyệt bổ sung trong 2 ngày.'),
                dict(id='log', title='Nhật ký cổng', source='Bảo vệ', text='Cả tổ 12 người quét thẻ ra lúc 21:05 tối qua — làm thật, có dữ liệu.'),
                dict(id='boss', title='Quản đốc ở đâu', source='Lịch công tác', text='Anh quản đốc đi công tác nhưng vẫn đọc email và duyệt được trên điện thoại.')],
         options=[dict(id='email', label='Gửi email cho quản đốc kèm nhật ký cổng, xin duyệt bổ sung trong hạn; báo chị Hoa tiền tăng ca vẫn vào kỳ này nếu kịp',
                       requires=['rule', 'log'], quality='good', stars=5,
                       review='Không cho chị ký thay, nhưng tối đó quản đốc duyệt liền. Cả tổ nhận đủ tiền tăng ca, không ai phải lo.',
                       outcome='Phiếu được duyệt bổ sung trong đêm; bảng lương có đủ chữ ký, tổ nhận đúng tiền.',
                       perspectives=[dict(who='Chị Hoa', emoji='🧵', text='Tưởng phải cãi nhau, ai ngờ có đường hợp lệ nhanh vậy.'),
                                     dict(who='Chị Hồng', emoji='📒', text='Có nhật ký cổng làm bằng chứng — hồ sơ tăng ca sạch sẽ.'),
                                     dict(who='Quản đốc', emoji='📱', text='Gửi đủ dữ liệu thì tôi duyệt trong một phút.')]),
                  dict(id='sign', label='Để chị Hoa ký thay cho kịp, tính luôn vào lương', quality='bad', stars=2,
                       review='Kỳ này nhận tiền rồi, mà giờ phòng lương bị hỏi sao phiếu có chữ ký tổ trưởng…',
                       outcome='Kiểm tra nội bộ phát hiện phiếu ký sai thẩm quyền; tiền tăng ca bị treo lại để xác minh.',
                       perspectives=[dict(who='Chị Hồng', emoji='😟', text='Chữ ký thay là lỗ hổng, lần sau ai cũng xin “ký giùm”.'),
                                     dict(who='Chị Hoa', emoji='😣', text='Chị muốn giúp tổ, ai ngờ làm tổ bị treo tiền.')]),
                  dict(id='later', label='Không tính, để kỳ sau có phiếu thì trả', quality='ok', stars=3,
                       review='Đúng quy chế, nhưng cả tổ phải chờ thêm một tháng cho tiền mồ hôi của mình.',
                       outcome='Tiền tăng ca trả chậm một kỳ; tổ may có phần chán nản.',
                       perspectives=[dict(who='Chị Hoa', emoji='😔', text='Còn cách duyệt bổ sung mà sao không ai nói?'),
                                     dict(who='Chị Hồng', emoji='🤔', text='Đúng luật nhưng mình chưa tìm lối ra cho người làm.')])],
         lesson='Không ký thay, không bỏ mặc: tìm đúng người có thẩm quyền, kèm bằng chứng, kịp hạn.'),
    dict(id='TP-S09', title='Xin “ghi cao lên” giấy xác nhận thu nhập', npc=4, tone='tense', min_day=2,
         opening='Anh Khôi đưa mẫu giấy của ngân hàng: “Tôi sắp vay mua nhà. Nhờ phòng lương xác nhận thu nhập giúp — ghi cao lên chút, 20% thôi, cho dễ duyệt.”',
         swap='Bạn làm lâu năm, lương đủ sống nhưng ngân hàng đòi thu nhập cao hơn một chút mới cho vay.',
         facts=[dict(id='payroll', title='Bảng lương 6 tháng', source='Sổ lương', text='Thu nhập thực của anh Khôi đều đặn, cộng thêm thưởng tháng 13 đã có quyết định.'),
                dict(id='rule', title='Quy định xác nhận', source='Chị Hồng', text='Giấy xác nhận thu nhập phải khớp bảng lương; kế toán trưởng ký, công ty chịu trách nhiệm.'),
                dict(id='bonus', title='Quyết định thưởng', source='Ban giám đốc', text='Thưởng tháng 13 đã công bố bằng văn bản — được ghi vào giấy xác nhận như khoản sắp nhận.')],
         options=[dict(id='true', label='Xác nhận đúng số thật, kèm quyết định thưởng tháng 13 để hồ sơ vay đẹp mà vẫn đúng',
                       requires=['payroll', 'rule', 'bonus'], quality='good', stars=5,
                       review='Không “ghi cao” được, nhưng thêm quyết định thưởng vào là ngân hàng duyệt. Cảm ơn phòng lương.',
                       outcome='Hồ sơ vay được duyệt với số liệu thật; công ty không phải ký một con số sai.',
                       perspectives=[dict(who='Anh Khôi', emoji='🔧', text='Tôi không biết thưởng đã công bố cũng được tính.'),
                                     dict(who='Chị Hồng', emoji='📒', text='Chữ ký của công ty trên giấy là lời cam kết, không phải ân huệ.'),
                                     dict(who='Ngân hàng', emoji='🏦', text='Hồ sơ khớp bảng lương thì duyệt nhanh.')]),
                  dict(id='inflate', label='Ghi cao lên 20% cho anh Khôi dễ vay', quality='bad', stars=2,
                       review='Vay được thật, nhưng ngân hàng gọi đối chiếu sao kê thì lộ chuyện.',
                       outcome='Ngân hàng đối chiếu sao kê lương, phát hiện chênh lệch; hồ sơ bị hủy, công ty bị hỏi trách nhiệm.',
                       perspectives=[dict(who='Anh Khôi', emoji='😰', text='Giờ tôi bị ngân hàng đánh dấu, khó vay chỗ khác.'),
                                     dict(who='Chị Hồng', emoji='😞', text='Người ký giấy sai cũng phải giải trình.')]),
                  dict(id='refuse', label='Từ chối cấp giấy, bảo anh tự lo', quality='ok', stars=3,
                       review='Không ghi cao thì thôi, chứ giấy xác nhận đúng số cũng không cấp à?',
                       outcome='Anh Khôi phải chờ thêm hai tuần xin giấy qua giám đốc.',
                       perspectives=[dict(who='Anh Khôi', emoji='😶', text='Tôi chỉ cần một tờ giấy đúng sự thật.'),
                                     dict(who='Chị Hồng', emoji='🤔', text='Từ chối phần sai thôi, phần đúng mình vẫn làm được.')])],
         lesson='Xác nhận đúng sự thật, và tìm những khoản thật còn bỏ sót — không thổi phồng con số.'),
    dict(id='TP-S10', title='Tin nhắn “giám đốc” đòi chuyển tiền gấp', npc=1, tone='tense', min_day=3,
         opening='Một tài khoản mang ảnh anh Phát nhắn: “Em chuyển gấp 15.000 xu tạm ứng cho đối tác vào số này, anh đang họp, đừng gọi. Xong báo anh.”',
         swap='Bạn là giám đốc thật: đang đứng giữa xưởng, không hề biết có ai mượn tên mình.',
         facts=[dict(id='account', title='Số tài khoản lạ', source='Tin nhắn', text='Số tài khoản không có trong danh bạ đối tác; tên chủ tài khoản là một cá nhân lạ.'),
                dict(id='call', title='Gọi số bàn của anh Phát', source='Điện thoại', text='Anh Phát đang ở xưởng, không nhắn gì cả. Tài khoản kia là giả.'),
                dict(id='rule', title='Quy trình chi tiền', source='Quy chế', text='Mọi lệnh chi từ 1.000 xu phải có đề nghị bằng văn bản và giám đốc ký trên ngân hàng số.')],
         options=[dict(id='verify', label='Không chuyển; gọi lại số đã đăng ký của anh Phát, báo chị Hồng và cảnh báo cả phòng',
                       requires=['account', 'call'], quality='good', stars=5,
                       review='May mà em gọi lại. Kẻ gian mượn ảnh anh để lừa. Cả xưởng giờ ai cũng biết mẹo này.',
                       outcome='Không mất đồng nào; công ty báo ngân hàng khóa tài khoản lạ và dán cảnh báo ở phòng kế toán.',
                       perspectives=[dict(who='Anh Phát', emoji='🏭', text='Cảm ơn em đã không “nghe lời” tin nhắn đó.'),
                                     dict(who='Chị Hồng', emoji='📒', text='Quy trình chậm một phút nhưng cứu cả tháng lương.'),
                                     dict(who='Cô Lụa', emoji='🗂️', text='Kiểu lừa này đang nở rộ, phòng kế toán nào cũng nên tập.')]),
                  dict(id='send', label='Chuyển ngay cho kịp, sếp đang cần', quality='bad', stars=1,
                       review='15.000 xu bay mất trong một phút. Lẽ ra chỉ cần một cuộc gọi.',
                       outcome='Tiền chuyển vào tài khoản lừa đảo; công ty trình báo, khó đòi lại.',
                       perspectives=[dict(who='Anh Phát', emoji='😠', text='Tôi chưa bao giờ ra lệnh chi qua tin nhắn.'),
                                     dict(who='Chị Hồng', emoji='😞', text='Quy trình có đó mà bị bỏ qua.')]),
                  dict(id='ignore', label='Không chuyển, lặng lẽ xóa tin nhắn', quality='ok', stars=3,
                       review='Mình không mất tiền, nhưng hôm sau Bình suýt chuyển vì cũng nhận được tin y hệt.',
                       outcome='Kẻ gian nhắn tiếp cho người khác trong phòng; may chị Hồng phát hiện kịp.',
                       perspectives=[dict(who='Bình', emoji='🐣', text='Em không biết có vụ này, suýt nữa thì…'),
                                     dict(who='Chị Hồng', emoji='🤔', text='Tự mình tránh được chưa đủ — phải báo cho cả phòng.')])],
         lesson='Lệnh chi qua tin nhắn: không chuyển, gọi lại số đã đăng ký, báo cho mọi người.'),
]

EMPLOYMENT = dict(
    postings=[
        dict(id='tp-firm', org='Dịch vụ Thuế & Tiền lương Minh Bạch', kind='firm', title='Chuyên viên lương & thuế',
             salary=(60, 85), probation_days=3, wants=['numbers', 'careful', 'communication'],
             perks=['Nhiều khách hàng, học nhanh', 'Có kế toán trưởng kèm', 'Mùa quyết toán bận rộn'],
             culture='Công ty dịch vụ nhỏ, làm lương và thuế cho quán xá, xưởng may, tiệm sửa; nguyên tắc số một: bảo mật.',
             questions=['tp_privacy', 'tp_deadline', 'mistake'], reference=True),
        dict(id='tp-factory', org='Xưởng may Chỉ Vàng', kind='corp', title='Nhân viên tiền lương',
             salary=(55, 75), probation_days=2, wants=['careful', 'patience', 'teamwork'],
             perks=['Lịch ổn định', 'Cơm trưa tại xưởng', 'Công nhân hỏi phiếu lương nhiều'],
             culture='Xưởng 120 công nhân; mỗi tháng một kỳ lương, chấm công giấy lẫn máy.',
             questions=['tp_cash', 'tp_privacy', 'conflict'], reference=True),
        dict(id='tp-agent', org='Đại lý Thuế Cây Bút Chì', kind='private', title='Trợ lý khai thuế',
             salary=(50, 70), probation_days=2, wants=['numbers', 'learning'],
             perks=['Nhận việc nhanh', 'Làm theo mùa hạn nộp', 'Lương khởi điểm thấp hơn'],
             culture='Đại lý khai thuế cho hộ và công ty nhỏ; mùa hạn nộp làm dồn.',
             questions=['tp_deadline', 'tp_error'], reference=False),
    ],
    questions={
        'tp_privacy': dict(text='Một trưởng phòng xin bảng lương cả công ty “để tham khảo”. Bạn làm gì?', options=[
            dict(id='check', label='Hỏi mục đích, chỉ gửi phần dữ liệu người đó được phép xem sau khi có duyệt', score=3,
                 note='Người phỏng vấn gật đầu: bảo mật nhưng không cứng nhắc.'),
            dict(id='send', label='Gửi luôn vì là sếp', score=0, note='Dữ liệu lương bị lộ là lỗi rất nặng.'),
            dict(id='refuse', label='Từ chối, không giải thích', score=1, note='Đúng hướng nhưng thiếu cách làm việc.')]),
        'tp_deadline': dict(text='Chiều nay là hạn nộp, bạn phát hiện số liệu lệch nhỏ. Bạn làm gì?', options=[
            dict(id='fix', label='Báo ngay người phụ trách, tìm nguyên nhân, nộp đúng số; nếu cần thì nộp bổ sung sau', score=3,
                 note='Ưu tiên đúng số và minh bạch.'),
            dict(id='plug', label='Chỉnh một dòng cho khớp rồi nộp', score=0, note='“Cho khớp” là cách sai số lớn lên.'),
            dict(id='wait', label='Để qua hạn cho chắc', score=1, note='Cẩn thận nhưng chịu tiền chậm nộp.')]),
        'tp_cash': dict(text='Công nhân xin nhận lương tiền mặt để khỏi đóng bảo hiểm. Bạn trả lời sao?', options=[
            dict(id='explain', label='Giải thích quyền lợi bảo hiểm và gợi ý tạm ứng theo quy chế', score=3, note='Vừa đúng luật vừa có lòng.'),
            dict(id='yes', label='Đồng ý cho êm', score=0, note='Rủi ro cho cả hai bên.'),
            dict(id='no', label='“Không được” rồi thôi', score=1, note='Đúng nhưng thiếu hỗ trợ.')]),
        'tp_error': dict(text='Bạn phát hiện tháng trước mình tính sai thuế của một người. Bạn làm gì?', options=[
            dict(id='own', label='Báo quản lý, tính lại, điều chỉnh kỳ sau và giải thích với người lao động', score=3, note='Trách nhiệm và minh bạch.'),
            dict(id='hide', label='Lặng lẽ bù vào kỳ sau', score=1, note='Sửa được số nhưng mất lòng tin nếu lộ ra.'),
            dict(id='leave', label='Không sao, cuối năm quyết toán sẽ tự khớp', score=0, note='Đẩy lỗi cho người khác xử lý.')]),
    },
)

SPEC = dict(
    id=ID, prefix='tp_', category='office',
    meta=dict(short='Thuế & tiền lương', place='Dịch vụ Thuế & Tiền lương Minh Bạch', tagline='Từng dòng phiếu lương đều có lý do.', icon='calculator',
              color='#3f7d6e', light='#e3f3ee', weather='Trời trong, quạt trần quay đều', work='Hồ sơ', station='Bàn tính lương',
              greeting='Bảng lương nháp và hồ sơ hôm nay đã xếp trên bàn. Soát từng ô, kịp giờ chốt lệnh ngân hàng nhé.',
              caption='Con số đúng, người nhận yên tâm', map_label='19 · THUẾ & LƯƠNG MINH BẠCH'),
    people=PEOPLE,
    staff=[('Ngân', 'payroll', 'Thuộc lòng các mốc giảm trừ gia cảnh.', 78, 90),
           ('Tuấn', 'tax', 'Tra cứu mã số thuế nhanh như chớp.', 84, 80),
           ('Thư', 'filing', 'Tủ hồ sơ của Thư chưa bao giờ lạc một tờ.', 72, 93),
           ('Bình', 'payroll', 'Mới vào, hay hỏi “vì sao” — câu hỏi tốt.', 70, 92)],
    roles={'payroll': 'Chuyên viên lương', 'tax': 'Chuyên viên thuế', 'filing': 'Văn thư lưu trữ'},
    tip=0,
    physical=(),
    free_actions=(),
    no_tick=('tp_flag', 'tp_hint', 'tp_claim', 'tp_overtime', 'tp_help', 'tp_cover', 'tp_break', 'tp_declare'),
    employment=EMPLOYMENT,
    activity=('🧮', 'Bàn lương ngăn nắp', [('Bảng chấm công', 'Hồ sơ lương'), ('Hóa đơn mua vào', 'Hồ sơ thuế'),
                                         ('Phiếu lương', 'Hồ sơ lương'), ('Tờ khai GTGT', 'Hồ sơ thuế')],
              ['Nhận chấm công', 'Tính lương gộp', 'Trừ bảo hiểm & thuế', 'Gửi phiếu, chuyển khoản']),
    stories=[('Phiếu lương đầu tiên của Diệu', ('Diệu cầm phiếu lương đầu tiên, hỏi từng dòng BHXH, BHYT là gì.',
                                                 'Bạn vẽ cho Diệu sơ đồ: tổng thu nhập → bảo hiểm → thuế → thực lĩnh.',
                                                 'Tháng sau, Diệu tự soát phiếu và còn giải thích lại cho bạn cùng tổ.')),
             ('Chú Bảy và chiếc hộp hóa đơn', ('Chú Bảy mang tới một hộp bánh quy đầy hóa đơn nhàu nát.',
                                               'Bạn chỉ chú cách tách hóa đơn quán với đồ nhà, và vì sao mua lớn nên chuyển khoản.',
                                               'Quý sau, hóa đơn tới trong bìa kẹp có nhãn từng tháng — chú còn dán sticker.')),
             ('Lịch hạn nộp trên tường', ('Chị Hồng giao bạn giữ tấm lịch hạn nộp chung của cả văn phòng.',
                                         'Bạn tô màu từng loại hạn, nhắc trước ba ngày cho mỗi khách.',
                                         'Cả mùa Tết không khách nào bị chậm nộp một ngày.'))],
    review_asides=['Phiếu lương rõ từng dòng, đọc là hiểu.', 'Nộp đúng hạn, không phải lo.', 'Hỏi là được giải thích tận tình.',
                   'Thông tin lương được giữ kín đáo.'],
    situations=SITUATIONS,
    guide='Bảng lương: soát từng người với hồ sơ gốc, chạm ô sai để đánh dấu, “✓ Xong dòng”, rồi chuyển lương trước giờ hạn. Sót lỗi thì hôm sau có người khiếu nại. Hồ sơ khác: kiểm từng bước rồi nộp. Lương ngày trả khi khép ca.',
)
