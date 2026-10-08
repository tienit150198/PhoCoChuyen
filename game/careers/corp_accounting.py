"""Kế toán doanh nghiệp · Công ty CP Mây Tre Xanh (plugin career, employed job).

The monthly cycle of a mid-size rattan & bamboo maker-trader, one dossier at a
time: check purchase invoices against the goods-received note and the supplier
register (three-way match) and accept or send them back; issue sales invoices
and book revenue + cost of sales; post the day's business transactions; match
the bank statement with the cash-at-bank book; age customer debts and draft a
debt-confirmation letter; count the petty cash; compute straight-line
depreciation; reconcile a stock count; hunt the error in a trial balance that
does not balance; and close the month in the right order.

Every dossier is generated from (day, slot) only. Documents must be opened
before the steps that rely on them; answers live in procedures `_key` fields.
Correct journal entries are posted to the player's own running ledger (a trial
balance that always balances); closing the month closes that ledger to 421.

Chart of accounts, VAT rates and rules are SIMPLIFIED GAME RULES inspired by
Vietnamese practice — not professional or tax advice. All people, companies,
tax codes and amounts are fictional; currency is "xu".
"""
from __future__ import annotations
import copy
from ..jsoncopy import tree_copy, strip_copy
from . import kit, office
from .. import consequences as cq
from .. import procedures
from .. import archive as ar

ID = 'corp_accounting'
PREFIX = 'ca_'
COMPANY = 'Công ty CP Mây Tre Xanh'
COMPANY_ADDR = 'Làng nghề Phú Vinh'
MST_OWN = '0109246810'
BANK = 'Ngân hàng Sông Xanh'

ACCOUNTS = [
    ('111', 'Tiền mặt'), ('112', 'Tiền gửi ngân hàng'), ('131', 'Phải thu khách hàng'),
    ('133', 'Thuế GTGT được khấu trừ'), ('1381', 'Tài sản thiếu chờ xử lý'), ('152', 'Nguyên liệu, vật liệu'),
    ('156', 'Hàng hóa'), ('211', 'TSCĐ hữu hình'), ('214', 'Hao mòn TSCĐ'), ('331', 'Phải trả người bán'),
    ('3331', 'Thuế GTGT phải nộp'), ('334', 'Phải trả người lao động'), ('335', 'Chi phí phải trả'),
    ('3381', 'Tài sản thừa chờ giải quyết'), ('411', 'Vốn góp của chủ sở hữu'), ('421', 'Lợi nhuận chưa phân phối'),
    ('511', 'Doanh thu bán hàng'), ('632', 'Giá vốn hàng bán'), ('641', 'Chi phí bán hàng'),
    ('642', 'Chi phí quản lý doanh nghiệp'), ('911', 'Xác định kết quả kinh doanh'),
]
ACCOUNT_IDS = [a for a, _ in ACCOUNTS]
ACCOUNT_NAME = dict(ACCOUNTS)
PL_ACCOUNTS = ('511', '632', '641', '642', '911')

KINDS = {
    'journal': dict(name='Định khoản nghiệp vụ', emoji='✍️', milestone='docs'),
    'invoice_in': dict(name='Kiểm hóa đơn đầu vào', emoji='🧾', milestone='docs'),
    'invoice_out': dict(name='Xuất hóa đơn & ghi doanh thu', emoji='📤', milestone='docs'),
    'bank_rec': dict(name='Đối chiếu ngân hàng', emoji='🏦', milestone='bank'),
    'ageing': dict(name='Tuổi nợ & thư xác nhận công nợ', emoji='📬', milestone='debts'),
    'petty_cash': dict(name='Kiểm quỹ tiền mặt', emoji='💵', milestone='cash'),
    'inventory_count': dict(name='Kiểm kê kho', emoji='📦', milestone='cash'),
    'depreciation': dict(name='Khấu hao tài sản cố định', emoji='🪑', milestone='fixed'),
    'trial_balance': dict(name='Bảng cân đối thử & kết quả kinh doanh', emoji='⚖️', milestone='close'),
    'month_close': dict(name='Khóa sổ cuối tháng', emoji='🔒', milestone='close'),
}
MILESTONES = [('docs', 'Chứng từ & hóa đơn'), ('bank', 'Ngân hàng'), ('debts', 'Công nợ'),
              ('cash', 'Quỹ & kho'), ('fixed', 'Tài sản cố định'), ('close', 'Khóa sổ & báo cáo')]
MILESTONE_IDS = [m for m, _ in MILESTONES]
# Saves made before the document desk existed keep their dossiers: kit.mark_legacy moves those
# tasks into the legacy serial band and make_task rebuilds them from this old schedule.
LEGACY_SCHEDULE = [
    ['journal', 'invoice_in', 'invoice_out', 'petty_cash'],
    ['invoice_in', 'bank_rec', 'journal', 'ageing'],
    ['inventory_count', 'invoice_out', 'ageing', 'petty_cash'],
    ['depreciation', 'bank_rec', 'trial_balance', 'invoice_in'],
    ['month_close', 'trial_balance', 'depreciation', 'bank_rec'],
]
LEGACY_KIND_IDS = ['journal', 'invoice_in', 'invoice_out', 'bank_rec', 'ageing', 'petty_cash', 'inventory_count',
                   'depreciation', 'trial_balance', 'month_close']
KINDS['desk'] = dict(name='Khay chứng từ', emoji='🗂️', milestone='docs')
# Five game days make one fictional month: early month → month-end close. The desk comes every day.
SCHEDULE = [
    ['desk', 'journal', 'invoice_out', 'petty_cash'],
    ['invoice_in', 'desk', 'bank_rec', 'ageing'],
    ['desk', 'inventory_count', 'invoice_out', 'petty_cash'],
    ['depreciation', 'desk', 'bank_rec', 'trial_balance'],
    ['month_close', 'desk', 'trial_balance', 'depreciation'],
]
KIND_IDS = list(KINDS)
HANDOVER = ('specific', 'short', 'none')
GEN = 2
FIXED = ('proc', 'docs', 'brief', 'variant', '_handover', '_value', 'cases', 'gen')

PEOPLE = [
    ('Chị Hạnh', 'Kế toán trưởng', 'Kỹ từng dấu phẩy, thương người mới nhưng không bỏ qua sai sót.', 'picky'),
    ('Anh Tùng', 'Giám đốc', 'Nói nhanh, nghĩ về doanh số, hay “cho anh con số đẹp”.', 'bossy'),
    ('Cô Lụa', 'Thủ quỹ', 'Đếm tiền nhanh như gió, sợ nhất là lệch quỹ.', 'warm'),
    ('Bảo', 'Nhân viên kinh doanh', 'Chốt đơn giỏi, nộp chứng từ chậm, hay gửi ảnh chụp mờ.', 'genz'),
    ('Anh Khải', 'Kiểm toán viên · Kiểm toán Sao Mai', 'Ít nói, hỏi đúng chỗ đau.', 'quiet'),
    ('Bà Sáu', 'Chủ HTX Mây Tre (nhà cung cấp)', 'Bán mây sợi ba mươi năm, nói thẳng, ghét bị hẹn trả tiền.', 'sour'),
    ('Chú Toàn', 'Thủ kho', 'Nhớ từng bó mây trong kho, ghét giấy tờ.', 'warm'),
    ('Na', 'Thực tập sinh kế toán', 'Nhiệt tình, cộng nhanh, hay quên kiểm lại lần cuối.', 'genz'),
]

SUPPLIERS = [
    dict(id='sau', name='HTX Mây Tre Bà Sáu', abbr='BS', mst='0107531246', addr='Xóm Bãi, Phú Vinh', item='Mây sợi nguyên liệu',
         unit='kg', acct='152', vat=5, prices=[20, 40], qty=[50, 100, 150], extra=[10, 20], goods=True, npc=5),
    dict(id='son', name='Công ty TNHH Sơn Lá Tre', abbr='LT', mst='0106318527', addr='KCN Sông Mây', item='Sơn phủ gốc nước',
         unit='thùng', acct='152', vat=10, prices=[60, 80, 120], qty=[5, 10, 15], extra=[2, 5], goods=True, npc=6),
    dict(id='moc', name='Công ty Bao Bì Giấy Mộc', abbr='GM', mst='0108975310', addr='Phố Giấy, Hà Đông Mây', item='Thùng carton 5 lớp',
         unit='cái', acct='152', vat=10, prices=[5, 6, 8], qty=[100, 200, 300], extra=[50, 100], goods=True, npc=6),
    dict(id='hp', name='Xưởng Đan Lát Hạnh Phúc', abbr='HP', mst='0105642097', addr='Làng Chuông Mây', item='Giỏ mây đan sẵn (mua về bán)',
         unit='chiếc', acct='156', vat=10, prices=[40, 60, 80], qty=[10, 20, 30], extra=[2, 5], goods=True, npc=6),
    dict(id='cs', name='Công ty Quảng Cáo Chim Sẻ', abbr='CS', mst='0104280615', addr='Tầng 3, Tòa Mây Trắng', item='Gói quảng cáo mạng xã hội',
         unit='gói', acct='641', vat=10, prices=[300, 500], qty=[1], extra=[1], goods=False, npc=3),
]
CUSTOMERS = [
    dict(name='Cửa hàng Nhà Xinh Phố Cổ', mst='0102468013'), dict(name='Chuỗi Homestay Mây Chiều', mst='0103579024'),
    dict(name='Siêu thị Làng Việt', mst='0101357913'), dict(name='Công ty Quà Tặng Gió Nam', mst='0109753186'),
]
PRODUCTS = [
    dict(name='Giỏ mây đan tay', unit='chiếc', prices=[60, 80], costs=[42, 55], qty=[10, 20, 30, 40]),
    dict(name='Đèn tre thắp sáng', unit='chiếc', prices=[120, 150], costs=[85, 100], qty=[10, 20, 30]),
    dict(name='Khay mây chữ nhật', unit='chiếc', prices=[40, 50], costs=[26, 30], qty=[20, 40, 50]),
    dict(name='Ghế mây thư giãn', unit='chiếc', prices=[400, 500], costs=[290, 350], qty=[2, 4, 5]),
]
ERRORS = [
    ('mst', 'MST người bán khác danh bạ nhà cung cấp'), ('buyer', 'Tên/MST người mua không phải của Mây Tre Xanh'),
    ('qty', 'Số lượng khác phiếu nhập kho/nghiệm thu'), ('vat', 'Tiền thuế GTGT tính sai'),
    ('total', 'Tổng tiền thanh toán cộng sai'), ('sign', 'Chưa có chữ ký số của người bán'),
    ('dup', 'Trùng hóa đơn đã ghi sổ'), ('none', 'Hóa đơn hợp lệ — không phát hiện lỗi'),
]
ERROR_LABEL = dict(ERRORS)
PATTERNS = [[], ['vat'], ['dup'], [], ['mst'], ['qty'], ['total'], ['sign'], ['buyer'], ['vat', 'sign'], ['mst', 'qty'], []]


# ---------------------------------------------------------------- helpers
def _n(v: int) -> str:
    return f'{v:,}'.replace(',', '.')


def _mst(v: str) -> str:
    return f'{v[:4]} {v[4:7]} {v[7:]}'


def _swap(code: str, i: int) -> str:
    j = i + 1
    while code[i] == code[j]:
        i, j = i + 1, j + 1
    return code[:i] + code[j] + code[i] + code[j + 1:]


def _period(day: int) -> tuple[int, int, int]:
    phase = (day - 1) % 5
    return (day - 1) // 5 % 12 + 1, phase, (5, 12, 19, 26, 30)[phase]


def _d(dd: int, m: int) -> str:
    return f'{dd:02d}/{m:02d}'


def _cal(idx: int) -> str:
    """Game calendar: every month has 30 days (game rule)."""
    idx = (idx - 1) % 360
    return _d(idx % 30 + 1, idx // 30 + 1)


def _doc(did: str, kind: str, title: str, source: str, **content) -> dict:
    return dict(id=did, type=kind, title=title, source=source, **content)


def _acct_opts() -> list:
    return [dict(id=a, name=f'{a} · {n}') for a, n in ACCOUNTS]


def _step(sid, kind, title, prompt, key, docs=(), hints=(), explain='', **extra):
    return procedures.step(sid, kind, title, prompt, key, docs=list(docs), hints=list(hints), explain=explain, **extra)


def _choice(sid, title, prompt, options, key, rng, **kw):
    opts = [dict(id=i, label=label) for i, label in options]
    rng.shuffle(opts)
    return _step(sid, 'choice', title, prompt, key, options=opts, **kw)


def _multi(sid, title, prompt, options, key, **kw):
    return _step(sid, 'multi', title, prompt, sorted(key), options=[dict(id=i, label=label) for i, label in options], **kw)


def _number(sid, title, prompt, key, unit='xu', **kw):
    return _step(sid, 'number', title, prompt, int(key), unit=unit, **kw)


def _order(sid, title, prompt, items, rng, **kw):
    key = [i for i, _ in items]
    shown = [dict(id=i, label=label) for i, label in items]
    rng.shuffle(shown)
    if [x['id'] for x in shown] == key:
        shown = shown[1:] + shown[:1]
    return _step(sid, 'order', title, prompt, key, items=shown, **kw)


def _match(sid, title, prompt, left, right, key, **kw):
    return _step(sid, 'match', title, prompt, dict(key), left=[dict(id=i, label=label) for i, label in left],
                 right=[dict(id=i, label=label) for i, label in right], **kw)


def _fields(sid, title, prompt, fields, key, **kw):
    return _step(sid, 'fields', title, prompt, dict(key), fields=fields, **kw)


def _entry(sid, title, prompt, lines, post=True, **kw):
    return _step(sid, 'entry', title, prompt, [[d, c, int(a)] for d, c, a in lines], accounts=_acct_opts(), post=post, **kw)


def _lines_text(lines) -> str:
    return '; '.join(f'Nợ {d} / Có {c}: {_n(a)}' for d, c, a in lines)


# ---------------------------------------------------------------- dossier generators
def g_invoice_in(rng, day, slot):
    m, _, dom = _period(day)
    sup = SUPPLIERS[rng.randrange(len(SUPPLIERS))]
    errs = list(rng.choice([[], ['vat'], ['dup']] if day == 1 else PATTERNS))
    qty = rng.choice(sup['qty'])
    price = rng.choice(sup['prices'])
    inv_qty = qty + (rng.choice(sup['extra']) if 'qty' in errs else 0)
    base = inv_qty * price
    vat_true = base * sup['vat'] // 100
    vat = vat_true
    if 'vat' in errs:
        vat = base * 10 // 100 if sup['vat'] == 5 else vat_true + rng.choice([20, 30, 50])
    total = base + vat
    if 'total' in errs:
        total += rng.choice([90, 900])
    mst = _swap(sup['mst'], 4) if 'mst' in errs else sup['mst']
    buyer = 'Công ty CP Mây Tre Xinh' if 'buyer' in errs else COMPANY
    number = f'{rng.randrange(150, 990):07d}'
    symbol = f'1C26T{sup["abbr"]}'
    dd = max(1, dom - rng.choice([3, 4])) if 'dup' in errs else dom
    grn = f'PN-{m:02d}{rng.randrange(10, 99)}'
    others = [x for x in SUPPLIERS if x['id'] != sup['id']]
    rng.shuffle(others)
    book = []
    for i, o in enumerate(others[:2]):
        book.append([_d(max(1, dd - 2 - i), m), f'1C26T{o["abbr"]}-{rng.randrange(100, 990):07d}', o['name'], _n(rng.randrange(20, 90) * 20), 'Đã ghi sổ'])
    if 'dup' in errs:
        book.append([_d(dd, m), f'{symbol}-{number}', sup['name'], _n(total), f'Đã ghi sổ · đã trả UNC-{rng.randrange(100, 999)}'])
    book.sort(key=lambda r: r[0])
    docs = [
        _doc('inv', 'invoice', 'Hóa đơn GTGT điện tử', sup['name'], symbol=symbol, number=number, date=_d(dd, m),
             seller=dict(name=sup['name'], mst=_mst(mst), addr=sup['addr']), buyer=dict(name=buyer, mst=_mst(MST_OWN), addr=COMPANY_ADDR),
             lines=[[sup['item'], sup['unit'], inv_qty, price, base]], base=base, rate=sup['vat'], vat=vat, total=total,
             signed='sign' not in errs, signer=sup['name'] if 'sign' not in errs else ''),
        _doc('grn', 'kv', ('Phiếu nhập kho ' + grn) if sup['goods'] else 'Biên bản nghiệm thu dịch vụ', 'Chú Toàn · Thủ kho' if sup['goods'] else 'Bảo · Phòng kinh doanh',
             rows=[['Ngày', _d(dd, m)], ['Nhà cung cấp', sup['name']], ['Nội dung', sup['item']],
                   ['Số lượng thực nhận' if sup['goods'] else 'Khối lượng nghiệm thu', f'{qty} {sup["unit"]}'],
                   ['Đơn giá theo đơn đặt hàng', f'{_n(price)} xu/{sup["unit"]}'], ['Chữ ký', 'Đủ chữ ký hai bên']]),
        _doc('reg', 'table', 'Danh bạ nhà cung cấp', 'Phần mềm kế toán', cols=['Đơn vị', 'Mã số thuế'],
             rows=[[COMPANY + ' (bên mua — chính mình)', _mst(MST_OWN)], [sup['name'], _mst(sup['mst'])]] + [[o['name'], _mst(o['mst'])] for o in others[:2]]),
        _doc('book', 'table', f'Sổ hóa đơn đầu vào tháng {m}', 'Phần mềm kế toán', cols=['Ngày', 'Ký hiệu – Số', 'Nhà cung cấp', 'Tổng tiền', 'Tình trạng'], rows=book),
    ]
    detail = {'vat': f' Thuế đúng phải là {_n(base)} × {sup["vat"]}% = {_n(vat_true)} xu.', 'total': f' Tổng đúng phải là {_n(base)} + {_n(vat)} = {_n(base + vat)} xu.',
              'qty': f' Kho/nghiệm thu chỉ ghi {qty} {sup["unit"]}, hóa đơn tính {inv_qty}.', 'mst': f' MST trong danh bạ là {_mst(sup["mst"])}, hóa đơn in {_mst(mst)}.',
              'buyer': ' Tên người mua in sai thành “Mây Tre Xinh”.', 'sign': ' Hóa đơn điện tử chưa ký số thì chưa hợp lệ.',
              'dup': f' Số {number} đã ghi sổ ngày {_d(dd, m)} và đã thanh toán.'}
    issues = '; '.join(ERROR_LABEL[e].lower() for e in errs)
    decision = 'dup' if 'dup' in errs else 'fix' if errs else 'accept'
    steps = [
        _multi('flags', 'Soi hóa đơn', 'Đối chiếu hóa đơn với phiếu nhập kho, danh bạ NCC và sổ hóa đơn đã ghi. Đánh dấu mọi lỗi (hoặc “hợp lệ”).',
               ERRORS, sorted(errs) or ['none'], docs=['inv', 'grn', 'reg', 'book'],
               hints=['So từng ô: MST người bán ↔ danh bạ, số lượng ↔ phiếu nhập, số hóa đơn ↔ sổ đã ghi, dòng chữ ký số.',
                      'Tính lại: thành tiền × thuế suất = tiền thuế; tiền hàng + tiền thuế = tổng cộng.'],
               explain=('Hóa đơn khớp cả ba nguồn: đúng MST, đúng số lượng, thuế và tổng cộng đúng, đã ký số.' if not errs
                        else 'Lỗi: ' + issues + '.' + ''.join(detail[e] for e in errs))),
        _choice('decision', 'Quyết định', 'Với kết quả kiểm tra này, xử lý hóa đơn thế nào?',
                [('accept', 'Chấp nhận: ghi sổ và chuyển thanh toán theo hạn'), ('fix', 'Chưa ghi sổ: đề nghị NCC lập hóa đơn điều chỉnh/thay thế'),
                 ('dup', 'Không ghi sổ: báo NCC đây là hóa đơn trùng'), ('force', 'Cứ ghi theo hóa đơn, chỗ sai tự sửa tay cho khớp')], decision, rng,
                hints=['Người mua không được tự sửa số trên hóa đơn của người bán.', 'Một nghiệp vụ chỉ được ghi sổ một lần.'],
                explain={'accept': 'Hóa đơn hợp lệ: ghi nhận giá trị mua, thuế được khấu trừ và công nợ chờ trả.',
                         'fix': 'Bên mua không tự sửa hóa đơn; người bán lập hóa đơn điều chỉnh hoặc thay thế rồi mới ghi sổ.',
                         'dup': 'Hóa đơn gửi lại không phải nghiệp vụ mới — ghi lần hai là trả tiền hai lần.'}[decision]),
    ]
    if decision == 'accept':
        lines = [[sup['acct'], '331', base], ['133', '331', vat]]
        steps.append(_entry('post', 'Ghi sổ', f'Định khoản hóa đơn {symbol}-{number} (chưa thanh toán).', lines,
                            hints=['Mua chịu: bên Có là 331 Phải trả người bán.', f'Tách thuế sang 133; giá trị chưa thuế vào TK {sup["acct"]} ({ACCOUNT_NAME[sup["acct"]]}).'],
                            explain=f'Nợ {sup["acct"]} {_n(base)} + Nợ 133 {_n(vat)} / Có 331 {_n(total)}.'))
        hand = f'HĐ {symbol}-{number} hợp lệ (đủ 3 nguồn). Đã ghi {_lines_text(lines)}; kẹp {"phiếu nhập " + grn if sup["goods"] else "biên bản nghiệm thu"}.'
    else:
        if decision == 'dup':
            replies = [('specific', f'“HĐ {symbol}-{number} bên em đã nhận ngày {_d(dd, m)}, ghi sổ và thanh toán rồi ạ — gửi kèm ủy nhiệm chi. Bản gửi lại này em không ghi sổ nữa.”'),
                       ('pay', '“Em chuyển khoản luôn cho chắc, nếu thừa thì bên chị trả lại sau nhé.”'),
                       ('silent', 'Không trả lời, kéo email vào thư mục rác.'),
                       ('accuse', '“Bên chị cố tình đòi tiền hai lần à?”')]
        else:
            replies = [('specific', f'“HĐ {symbol}-{number} ngày {_d(dd, m)} có lỗi: {issues}. Nhờ bên mình lập hóa đơn điều chỉnh/thay thế; nhận được là bên em ghi sổ và thanh toán đúng hạn. Cảm ơn ạ!”'),
                       ('vague', '“Hóa đơn bị sai, bên mình xem lại giúp em nha.”'),
                       ('self', '“Em sửa tay lại số trên bản in rồi, bên mình khỏi làm lại.”'),
                       ('blame', '“Làm ăn cẩu thả vậy, tháng sau bên em đổi nhà cung cấp.”')]
        steps.append(_choice('reply', 'Trả lời nhà cung cấp', f'Chọn email gửi {sup["name"]}.', replies, 'specific', rng,
                             hints=['Email tốt nêu đúng số hóa đơn, đúng lỗi và bước tiếp theo.', 'Giữ quan hệ: lịch sự, cụ thể, có hạn xử lý.'],
                             explain='Email cụ thể giúp nhà cung cấp sửa ngay một lần, không ai phải đoán.'))
        hand = f'HĐ {symbol}-{number}: chưa ghi sổ vì {issues}. Đã gửi email cụ thể cho {sup["name"]}; chờ hóa đơn xử lý.'
    npc = sup['npc']
    opening = {5: 'Mây giao đủ rồi nhé, hóa đơn đây. Cuối tháng nhớ trả tiền cho bà đúng hẹn!',
               6: 'Hàng về kho rồi, hóa đơn kẹp trong thùng. Cháu kiểm giùm chú rồi ký cho xong.',
               3: 'Chiến dịch quảng cáo chạy xong rồi, bên agency gửi hóa đơn nè, kiểm giúp em với!'}[npc]
    if 'dup' in errs:
        opening = 'Email mới: nhà cung cấp gửi lại hóa đơn, dòng tiêu đề ghi “GẤP — thanh toán giúp em”.'
    return dict(npc=npc, title=f'Hóa đơn {sup["item"].lower()} · {sup["name"]}', opening=opening,
                brief=f'{sup["name"]} gửi hóa đơn {sup["item"].lower()}. Đối chiếu 3 nguồn (hóa đơn – phiếu nhập/nghiệm thu – danh bạ & sổ đã ghi), rồi quyết định ghi sổ hay trả lại.',
                docs=docs, steps=steps, handover=hand, value=total)


def g_invoice_out(rng, day, slot):
    m, _, dom = _period(day)
    cus = CUSTOMERS[rng.randrange(len(CUSTOMERS))]
    pi = rng.randrange(len(PRODUCTS))
    pr = PRODUCTS[pi]
    order = rng.choice(pr['qty'])
    k = rng.randrange(len(pr['prices']))
    price, cost = pr['prices'][k], pr['costs'][k]
    partial = rng.random() < .45 and order >= 4
    delivered = order - (max(1, order // rng.choice([4, 5, 10])) if partial else 0)
    base = delivered * price
    vat = base // 10
    total = base + vat
    bank = rng.random() < .4
    dr = '112' if bank else '131'
    so = f'ĐH-{m:02d}{rng.randrange(10, 99)}'
    docs = [
        _doc('so', 'kv', 'Đơn đặt hàng ' + so, cus['name'], rows=[['Khách hàng', cus['name']], ['MST khách', _mst(cus['mst'])], ['Mặt hàng', pr['name']],
                                                                   ['Số lượng đặt', f'{order} {pr["unit"]}'], ['Đơn giá chưa thuế', f'{_n(price)} xu'], ['Thuế GTGT', '10%']]),
        _doc('dn', 'kv', 'Biên bản giao nhận hàng', 'Bảo · Phòng kinh doanh', rows=[['Ngày giao', _d(dom, m)], ['Số lượng thực giao', f'{delivered} {pr["unit"]}'],
                                                                                   ['Ghi chú', ('Thiếu hàng trong kho, giao bù đợt sau.' if partial else 'Giao đủ, khách kiểm đếm.')],
                                                                                   ['Xác nhận', 'Khách hàng đã ký nhận']]),
        _doc('pay', 'note', 'Giấy báo có ngân hàng' if bank else 'Điều khoản thanh toán', BANK if bank else 'Hợp đồng khung',
             text=(f'{cus["name"]} đã chuyển khoản đủ tiền cho lô hàng ngay khi nhận.' if bank else 'Thanh toán trong 30 ngày kể từ ngày giao hàng, chuyển khoản.')),
        _doc('card', 'kv', 'Thẻ kho · ' + pr['name'], 'Chú Toàn · Thủ kho', rows=[['Phương pháp giá vốn', 'Bình quân'], ['Giá vốn đơn vị', f'{_n(cost)} xu/{pr["unit"]}'],
                                                                               ['Tồn trước khi giao', f'{order + 20} {pr["unit"]}']]),
    ]
    rev = [[dr, '511', base], [dr, '3331', vat]]
    cogs = [['632', '156', delivered * cost]]
    steps = [
        _fields('calc', 'Tính hóa đơn', 'Lập hóa đơn GTGT cho số hàng đã giao thực tế.',
                [dict(id='base', label='Tiền hàng chưa thuế', unit='xu'), dict(id='vat', label='Thuế GTGT 10%', unit='xu'), dict(id='total', label='Tổng thanh toán', unit='xu')],
                dict(base=base, vat=vat, total=total), docs=['so', 'dn'],
                hints=['Hóa đơn tính theo số lượng thực giao trên biên bản, không theo số đặt.', 'Thuế = tiền hàng × 10%; tổng = tiền hàng + thuế.'],
                explain=f'{delivered} × {_n(price)} = {_n(base)}; thuế {_n(vat)}; tổng {_n(total)} xu.'),
        _entry('revenue', 'Ghi doanh thu', 'Định khoản doanh thu và thuế GTGT đầu ra.', rev, docs=['pay'],
               hints=['Khách trả ngay qua ngân hàng → Nợ 112; bán chịu → Nợ 131.', 'Thuế đầu ra ghi Có 3331, tiền hàng ghi Có 511.'],
               explain=f'{_lines_text(rev)}.'),
        _entry('cogs', 'Ghi giá vốn', 'Xuất kho hàng bán: ghi giá vốn theo thẻ kho.', cogs, docs=['card'],
               hints=['Giá vốn = số lượng thực giao × giá vốn đơn vị.', 'Hàng rời kho: Có 156; chi phí giá vốn: Nợ 632.'],
               explain=f'Nợ 632 / Có 156: {delivered} × {_n(cost)} = {_n(delivered * cost)} xu.'),
    ]
    return dict(npc=3, title=f'Xuất hóa đơn {pr["name"].lower()} · {cus["name"]}',
                opening=f'Chốt đơn {order} {pr["name"].lower()} cho {cus["name"]} rồi nè! Xuất hóa đơn giúp em trước 5 giờ nha.',
                brief=f'Lập hóa đơn bán {pr["name"].lower()} cho {cus["name"]}, ghi doanh thu, thuế đầu ra và giá vốn.',
                docs=docs, steps=steps, value=total,
                handover=f'Xuất HĐ cho {delivered}/{order} {pr["unit"]} (theo biên bản giao): {_n(base)} + VAT {_n(vat)} = {_n(total)}. Đã ghi {_lines_text(rev + cogs)}.')


def _txn_templates(rng):
    def buy_raw():
        q = rng.choice([50, 100, 150])
        b = q * 20
        v = b * 5 // 100
        return ('Hóa đơn GTGT + phiếu nhập kho', f'Mua {q} kg mây sợi của HTX Mây Tre Bà Sáu: giá chưa thuế {_n(b)} xu, thuế GTGT 5% là {_n(v)} xu, chưa thanh toán.',
                [['152', '331', b], ['133', '331', v]], 'Nguyên liệu vào kho → Nợ 152; thuế → Nợ 133; nợ nhà cung cấp → Có 331.')

    def pay_supplier():
        a = rng.randrange(6, 30) * 50
        return ('Ủy nhiệm chi', f'Chuyển khoản trả nợ Công ty TNHH Sơn Lá Tre {_n(a)} xu.', [['331', '112', a]], 'Nợ phải trả giảm → Nợ 331; tiền trong tài khoản giảm → Có 112.')

    def collect():
        a = rng.randrange(6, 30) * 50
        return ('Phiếu thu', f'Chuỗi Homestay Mây Chiều trả nợ tiền hàng tháng trước {_n(a)} xu bằng tiền mặt.', [['111', '131', a]], 'Tiền mặt tăng → Nợ 111; khoản phải thu giảm → Có 131.')

    def withdraw():
        a = rng.randrange(4, 20) * 100
        return ('Séc rút tiền + phiếu thu', f'Rút tiền gửi ngân hàng về nhập quỹ tiền mặt {_n(a)} xu.', [['111', '112', a]], 'Tiền chỉ chuyển từ ngân hàng về quỹ: Nợ 111 / Có 112.')

    def payroll():
        s, a = rng.randrange(10, 30) * 50, rng.randrange(10, 30) * 50
        return ('Bảng thanh toán lương', f'Tính lương tháng phải trả: bộ phận bán hàng {_n(s)} xu, bộ phận quản lý {_n(a)} xu.',
                [['641', '334', s], ['642', '334', a]], 'Lương là chi phí của từng bộ phận (641, 642); công ty nợ người lao động → Có 334.')

    def pay_salary():
        a = rng.randrange(20, 60) * 50
        return ('Ủy nhiệm chi trả lương', f'Chuyển khoản trả lương cho người lao động {_n(a)} xu.', [['334', '112', a]], 'Trả nợ người lao động: Nợ 334 / Có 112.')

    def stationery():
        b = rng.randrange(4, 20) * 10
        v = b // 10
        return ('Phiếu chi + hóa đơn', f'Chi tiền mặt mua văn phòng phẩm dùng ngay cho phòng kế toán: {_n(b)} xu, thuế GTGT 10% là {_n(v)} xu.',
                [['642', '111', b], ['133', '111', v]], 'Văn phòng phẩm dùng ngay là chi phí quản lý (642); thuế → 133; chi tiền mặt → Có 111.')

    def capital():
        a = rng.randrange(10, 50) * 100
        return ('Giấy báo có', f'Chủ sở hữu góp thêm vốn bằng chuyển khoản {_n(a)} xu.', [['112', '411', a]], 'Tiền vào tài khoản → Nợ 112; vốn chủ tăng → Có 411.')

    def buy_asset():
        b = rng.randrange(12, 37) * 100
        v = b // 10
        return ('Hóa đơn + biên bản giao nhận TSCĐ', f'Mua một máy chẻ mây mới: giá chưa thuế {_n(b)} xu, thuế GTGT 10% là {_n(v)} xu, trả bằng chuyển khoản.',
                [['211', '112', b], ['133', '112', v]], 'Máy dùng nhiều năm là TSCĐ → Nợ 211; thuế → 133; trả qua ngân hàng → Có 112.')

    def ads():
        b = rng.randrange(10, 40) * 10
        v = b // 10
        return ('Hóa đơn dịch vụ', f'Nhận hóa đơn quảng cáo gian hàng hội chợ {_n(b)} xu, thuế GTGT 10% là {_n(v)} xu, chưa trả tiền.',
                [['641', '331', b], ['133', '331', v]], 'Quảng cáo là chi phí bán hàng (641); chưa trả tiền → Có 331.')

    def retail():
        b = rng.randrange(10, 40) * 10
        v = b // 10
        return ('Hóa đơn bán lẻ + phiếu thu', f'Bán lẻ tại showroom, thu tiền mặt: tiền hàng {_n(b)} xu, thuế GTGT 10% là {_n(v)} xu.',
                [['111', '511', b], ['111', '3331', v]], 'Thu tiền mặt → Nợ 111; doanh thu → Có 511; thuế đầu ra → Có 3331.')
    return [buy_raw, pay_supplier, collect, withdraw, payroll, pay_salary, stationery, capital, buy_asset, ads, retail]


def g_journal(rng, day, slot):
    m, _, dom = _period(day)
    pool = _txn_templates(rng)
    picks = [pool[i] for i in ([2, 1, 6] if day == 1 and slot == 0 else rng.sample(range(len(pool)), 3))]
    docs, steps, allines = [], [], []
    for i, fn in enumerate(picks):
        title, text, lines, why = fn()
        did = f't{i + 1}'
        docs.append(_doc(did, 'note', f'Chứng từ {i + 1}: {title}', f'Ngày {_d(dom, m)}', text=text))
        steps.append(_entry(f'e{i + 1}', f'Nghiệp vụ {i + 1}', text, lines, docs=[did],
                            hints=['Hỏi: tài sản/chi phí nào TĂNG (ghi Nợ)? nguồn/nợ nào TĂNG hay tài sản nào GIẢM (ghi Có)?', why],
                            explain=f'{_lines_text(lines)}. {why}'))
        allines += lines
    return dict(npc=0, title=f'Định khoản chứng từ ngày {_d(dom, m)}', opening='Chị để ba chứng từ trên bàn em. Định khoản cho chuẩn nhé — sai một dòng là cuối tháng cả phòng thức đêm đấy.',
                brief='Đọc ba chứng từ phát sinh trong ngày và lập bút toán Nợ/Có cho từng nghiệp vụ. Tổng Nợ phải bằng tổng Có.',
                docs=docs, steps=steps, value=sum(a for _, _, a in allines), handover=f'Đã ghi 3 chứng từ ngày {_d(dom, m)}: {_lines_text(allines)}.')


def g_bank_rec(rng, day, slot):
    m, _, dom = _period(day)
    nxt = m % 12 + 1
    opening = rng.randrange(300, 800) * 10
    pool = [('Nhà Xinh Phố Cổ chuyển khoản trả nợ', 1), ('UNC trả HTX Mây Tre Bà Sáu', -1), ('UNC nộp thuế GTGT tháng trước', -1),
            ('Homestay Mây Chiều chuyển khoản', 1), ('UNC trả tiền điện', -1)]
    matched = []
    for i, (label, sign) in enumerate(rng.sample(pool, 3)):
        matched.append((_d(min(28, 3 + i * 7 + rng.randrange(3)), m), label, sign * rng.randrange(10, 150) * 10))
    items = []   # (id, side, code, label, amount signed from the company's view, class)
    fee = rng.randrange(11, 34)
    items.append(('fee', 'bank', f'FT{rng.randrange(1000, 9999)}', 'Phí quản lý tài khoản & SMS Banking', -fee, 'record'))
    outpay = ('outpay', 'book', f'UNC-{rng.randrange(100, 999)}', 'Trả Công ty Bao Bì Giấy Mộc (lập chiều 30)', -rng.randrange(20, 90) * 10, 'timing')
    deposit = ('deposit', 'book', f'GNT-{rng.randrange(10, 99)}', 'Nộp tiền mặt vào tài khoản lúc 16h50', rng.randrange(20, 90) * 10, 'timing')
    if rng.random() < .5:
        items.append(outpay)
        if rng.random() < .5:
            items.append(deposit)
    else:
        items.append(deposit)
    if rng.random() < .65 or len(items) < 3:
        items.append(('receipt', 'bank', f'FT{rng.randrange(1000, 9999)}', 'Siêu thị Làng Việt chuyển khoản trả nợ', rng.randrange(20, 120) * 10, 'record'))
    if len(items) < 4 and rng.random() < .5:
        items.append(('bankerr', 'bank', f'FT{rng.randrange(1000, 9999)}', 'Phí chuyển tiền hộ (không rõ yêu cầu)', -rng.randrange(5, 30) * 10, 'bank'))
    book_rows, bank_rows, options = [], [], []

    def money_cols(a):
        return [_n(a) if a > 0 else '', _n(-a) if a < 0 else '']
    for i, (dt, label, amt) in enumerate(matched):
        code = f'FT{rng.randrange(1000, 9999)}'
        book_rows.append((f'b{i}', [dt, f'GBC/UNC-{rng.randrange(100, 999)}' if amt < 0 else f'GBC-{rng.randrange(100, 999)}', label] + money_cols(amt)))
        bank_rows.append((f's{i}', [dt, code, label.upper()[:44]] + money_cols(amt)))
    for iid, side, code, label, amt, _ in items:
        row = (iid, [_d(30, m), code, label.upper()[:44] if side == 'bank' else label] + money_cols(amt))
        (book_rows if side == 'book' else bank_rows).append(row)
    rng.shuffle(bank_rows)
    book_end = opening + sum(a for _, _, a in matched) + sum(it[4] for it in items if it[1] == 'book')
    bank_end = opening + sum(a for _, _, a in matched) + sum(it[4] for it in items if it[1] == 'bank')
    adjusted = book_end + sum(it[4] for it in items if it[1] == 'bank' and it[5] == 'record')
    for rid, row in book_rows:
        options.append((rid, f'Sổ · {row[0]} · {row[2]} · {row[3] or "−" + row[4]}'))
    for rid, row in bank_rows:
        options.append((rid, f'Sao kê · {row[0]} · {row[2]} · {row[3] or "−" + row[4]}'))
    book_rows = [r for _, r in book_rows]
    bank_rows = [r for _, r in bank_rows]
    lines = []
    for iid, side, code, label, amt, cls in items:
        if cls == 'record':
            lines.append(['642', '112', -amt] if iid == 'fee' else ['112', '131', amt])
    docs = [
        _doc('book', 'table', 'Sổ tiền gửi ngân hàng (TK 112)', 'Phần mềm kế toán', cols=['Ngày', 'Chứng từ', 'Diễn giải', 'Thu', 'Chi'], rows=book_rows,
             foot=[['', '', 'Số dư đầu kỳ', _n(opening), ''], ['', '', 'Số dư cuối kỳ theo sổ', _n(book_end), '']]),
        _doc('stmt', 'table', f'Sao kê tháng {m} · {BANK}', 'Ngân hàng', cols=['Ngày', 'Mã GD', 'Nội dung', 'Ghi có (tiền vào)', 'Ghi nợ (tiền ra)'], rows=bank_rows,
             foot=[['', '', 'Số dư đầu kỳ', _n(opening), ''], ['', '', 'Số dư cuối kỳ theo ngân hàng', _n(bank_end), '']],
             note='Góc nhìn ngân hàng: “Ghi có” là tiền vào tài khoản của công ty, “ghi nợ” là tiền ra.'),
        _doc('memo', 'note', 'Ghi chú từ ngân hàng & thủ quỹ', 'Cô Lụa', text=f'Tiền nộp chiều 30 và các UNC lập cuối ngày 30 ngân hàng xử lý vào sáng {_d(1, nxt)}. '
             'Tổng đài ngân hàng xác nhận: khoản phí “chuyển tiền hộ” nào không có yêu cầu của công ty thì ngân hàng sẽ hoàn lại.'),
    ]
    steps = [
        _multi('find', 'Tìm dòng lệch', 'Tick các dòng CHỈ có ở một bên (sổ công ty hoặc sao kê).', options, [x[0] for x in items], docs=['book', 'stmt'],
               hints=['Dò từng dòng: cùng số tiền, cùng chiều tiền, cùng nội dung là dòng khớp.', 'Có dòng chỉ nằm trong sổ, có dòng chỉ nằm trên sao kê.'],
               explain='Các dòng lệch: ' + '; '.join(f'{code} {label}' for _, _, code, label, _, _ in items) + '.'),
        _match('classify', 'Phân loại chênh lệch', 'Mỗi dòng lệch thuộc loại nào?', [(iid, f'{code} · {label} · {_n(amt)}') for iid, _, code, label, amt, _ in items],
               [('record', 'Ghi bổ sung vào sổ công ty'), ('timing', 'Chênh lệch thời gian — không ghi, theo dõi'), ('bank', 'Ngân hàng sai — đề nghị ngân hàng sửa')],
               {iid: cls for iid, _, _, _, _, cls in items}, docs=['memo'],
               hints=['Khoản ngân hàng đã làm mà công ty chưa biết (phí, tiền khách chuyển) → công ty ghi bổ sung.', 'Khoản công ty đã làm cuối ngày mà ngân hàng chưa xử lý → chênh lệch thời gian.'],
               explain='Phí và tiền khách chuyển: ghi sổ. UNC/nộp tiền cuối ngày: chờ ngân hàng. Trừ nhầm: ngân hàng tự sửa.'),
        _number('adjusted', 'Số dư sau điều chỉnh', 'Số dư TK 112 theo sổ SAU khi ghi bổ sung các khoản cần ghi là bao nhiêu?', adjusted, docs=['book', 'stmt'],
                hints=['Bắt đầu từ số dư cuối kỳ theo sổ, cộng tiền vào/trừ tiền ra của các khoản “ghi bổ sung”.', 'Kiểm chéo: số dư ngân hàng ± chênh lệch thời gian ± sai sót ngân hàng phải ra cùng một số.'],
                explain=f'Sổ {_n(book_end)} → sau điều chỉnh {_n(adjusted)}; khớp với ngân hàng {_n(bank_end)} sau khi tính chênh lệch thời gian và khoản trừ nhầm.'),
        _entry('entry', 'Ghi bổ sung', 'Lập bút toán cho các khoản cần ghi bổ sung.', lines,
               hints=['Phí ngân hàng là chi phí quản lý: Nợ 642 / Có 112.', 'Khách chuyển khoản trả nợ: Nợ 112 / Có 131.'], explain=f'{_lines_text(lines)}.'),
    ]
    return dict(npc=1, title=f'Đối chiếu ngân hàng tháng {m}', opening='Ngân hàng báo số dư khác sổ mình, sao vậy em? Chiều nay anh cần con số chính xác để duyệt chi.',
                brief=f'So sổ tiền gửi TK 112 với sao kê {BANK}: tìm dòng lệch, phân loại, tính số dư đúng và ghi bổ sung.',
                docs=docs, steps=steps, value=adjusted,
                handover=f'Đối chiếu TK 112 tháng {m}: sổ {_n(book_end)}, ngân hàng {_n(bank_end)}, số dư đúng {_n(adjusted)}. Đã ghi {_lines_text(lines)}; các khoản còn lại theo dõi/đề nghị ngân hàng.')


BUCKETS = [('current', 'Chưa đến hạn'), ('d30', 'Quá hạn 1–30 ngày'), ('d60', 'Quá hạn 31–60 ngày'), ('d90', 'Quá hạn trên 60 ngày'), ('paid', 'Đã thu đủ')]


def g_ageing(rng, day, slot):
    m, _, _ = _period(day)
    cus = CUSTOMERS[rng.randrange(len(CUSTOMERS))]
    asof = m * 30
    plan = [('current', rng.randrange(3, 20)), ('d30', -rng.randrange(5, 26)), ('d60', -rng.randrange(35, 56)), ('d90', -rng.randrange(65, 90)), ('paid', -rng.randrange(20, 50))]
    rng.shuffle(plan)
    rows, left, key, balance, due90 = [], [], {}, 0, None
    for i, (bucket, offset) in enumerate(sorted(plan, key=lambda x: x[1])):
        due = asof + offset
        amount = rng.randrange(20, 120) * 10
        paid = amount if bucket == 'paid' else (amount // 2 // 10 * 10 if bucket == 'd60' else 0)
        no = f'HĐ-{rng.randrange(100, 999)}'
        rows.append([no, _cal(due - 30), _cal(due), _n(amount), _n(paid), _n(amount - paid)])
        left.append((no, f'{no} · hạn {_cal(due)} · còn {_n(amount - paid)}'))
        key[no] = bucket
        balance += amount - paid
        if bucket == 'd90':
            due90 = (no, amount - paid)
    overdue = sum(int(r[5].replace('.', '')) for r in rows if key[r[0]] in ('d30', 'd60', 'd90'))
    gross = sum(int(r[3].replace('.', '')) for r in rows)
    docs = [
        _doc('ar', 'table', f'Sổ chi tiết công nợ 131 · {cus["name"]}', 'Phần mềm kế toán', cols=['Số HĐ', 'Ngày HĐ', 'Hạn thanh toán', 'Số tiền', 'Đã thu', 'Còn phải thu'], rows=rows),
        _doc('terms', 'note', 'Hợp đồng & lịch thanh toán', 'Hợp đồng khung', text=f'Thời hạn thanh toán 30 ngày kể từ ngày hóa đơn. Ngày chốt công nợ: {_cal(asof)}. Mỗi tháng tính 30 ngày.'),
        _doc('call', 'note', 'Ghi chú cuộc gọi của Bảo', 'Bảo', text=f'Kế toán bên {cus["name"]} nói “bên chị chưa thấy hóa đơn {due90[0]}”, hẹn kiểm lại. Khách vẫn đặt hàng đều mỗi tháng.'),
    ]
    letters = [('ok', f'“Tính đến {_cal(asof)}, Quý công ty còn nợ Mây Tre Xanh {_n(balance)} xu (bảng kê hóa đơn đính kèm). Nếu số liệu khác, xin phản hồi trong 7 ngày.”'),
               ('overdue', f'“Tính đến {_cal(asof)}, Quý công ty còn nợ {_n(overdue)} xu.” (chỉ ghi phần quá hạn)'),
               ('gross', f'“Tính đến {_cal(asof)}, Quý công ty còn nợ {_n(gross)} xu.” (cộng cả hóa đơn đã thu)')]
    steps = [
        _match('buckets', 'Xếp tuổi nợ', f'Xếp từng hóa đơn vào nhóm tuổi nợ tại ngày chốt {_cal(asof)}.', left, BUCKETS, key, docs=['ar', 'terms'],
               hints=['Số ngày quá hạn = ngày chốt − hạn thanh toán (mỗi tháng 30 ngày).', 'Hóa đơn “còn phải thu” bằng 0 là đã thu đủ; hạn sau ngày chốt là chưa đến hạn.'],
               explain='Tính số ngày từ hạn thanh toán tới ngày chốt rồi xếp nhóm.'),
        _number('balance', 'Tổng còn phải thu', 'Tổng số khách còn nợ tại ngày chốt (tất cả hóa đơn chưa thu đủ)?', balance, docs=['ar'],
                hints=['Cộng cột “Còn phải thu”.', 'Hóa đơn đã thu một phần chỉ tính phần còn lại.'], explain=f'Tổng còn phải thu {_n(balance)} xu.'),
        _choice('letter', 'Thư xác nhận công nợ', 'Chọn nội dung thư xác nhận gửi khách.', letters, 'ok', rng,
                hints=['Thư xác nhận ghi TOÀN BỘ số dư còn nợ, kèm bảng kê, có hạn phản hồi.'], explain='Thư xác nhận đúng số dư giúp hai bên phát hiện chênh lệch sớm.'),
        _choice('action', 'Khoản quá hạn trên 60 ngày', f'Hóa đơn {due90[0]} còn {_n(due90[1])} xu đã quá hạn hơn 60 ngày. Việc nên làm?',
                [('confirm', 'Gửi lại bản sao hóa đơn kèm thư xác nhận, gọi kế toán khách, báo kinh doanh cân nhắc tạm dừng bán chịu'),
                 ('writeoff', 'Xóa nợ luôn cho gọn sổ'), ('ignore', 'Để khách tự nhớ mà trả'), ('threat', 'Gửi ngay thư dọa khởi kiện')], 'confirm', rng, docs=['call'],
                hints=['Ghi chú cuộc gọi cho biết khách có thể chưa nhận hóa đơn.'], explain='Khách vẫn giao dịch đều: gửi lại chứng từ và xác nhận trước, chưa xóa nợ, chưa dọa kiện.'),
    ]
    return dict(npc=3, title=f'Tuổi nợ & thư xác nhận · {cus["name"]}',
                opening=f'Sếp bảo em đi đòi nợ {cus["name"]} mà em không biết họ nợ bao nhiêu… Làm giúp em bảng tuổi nợ với thư xác nhận nha!',
                brief=f'Phân tích tuổi nợ của {cus["name"]}, lập thư xác nhận số dư và đề xuất xử lý khoản quá hạn.',
                docs=docs, steps=steps, value=balance,
                handover=f'{cus["name"]} còn nợ {_n(balance)} xu tại {_cal(asof)}; đã gửi thư xác nhận. {due90[0]} quá hạn >60 ngày: gửi lại hóa đơn, gọi kế toán khách.')


DENOMS = [500, 200, 100, 50, 20, 10]


def g_petty_cash(rng, day, slot):
    m, _, dom = _period(day)
    opening = rng.randrange(150, 300) * 10
    receipts = [('PT-01', 'Thu bán lẻ showroom', rng.randrange(20, 80) * 10)]
    if rng.random() < .5:
        receipts.append(('PT-02', 'Rút tiền gửi ngân hàng nhập quỹ', rng.randrange(20, 60) * 10))
    payments = [('PC-01', 'Mua văn phòng phẩm', rng.randrange(3, 12) * 10), ('PC-02', 'Tạm ứng công tác phí cho Bảo', rng.randrange(10, 30) * 10)]
    if rng.random() < .5:
        payments.append(('PC-03', 'Trả tiền nước uống văn phòng', rng.randrange(2, 8) * 10))
    book = opening + sum(a for _, _, a in receipts) - sum(a for _, _, a in payments)
    variant = rng.choice(['ok', 'voucher', 'short', 'over'] if day > 1 else ['ok', 'voucher'])
    gap = rng.randrange(5, 21) * 10
    counted = {'ok': book, 'voucher': book - gap, 'short': book - gap, 'over': book + gap}[variant]
    counts, rest = [], counted
    for dn in DENOMS:
        c = rest // dn
        if dn != 10 and c:
            c = rng.randrange(max(0, c - 2), c + 1)
        counts.append([f'{dn} xu', c])
        rest -= c * dn
    counts[-1][1] += rest // 10
    drawer = {'voucher': f'Kẹp dưới khay tiền: phiếu chi PC-04 “Mua băng keo, dây buộc hàng” {_n(gap)} xu — đã ký nhận, CHƯA vào sổ quỹ.',
              'short': 'Ngăn kéo chỉ có kẹp giấy và hai viên kẹo gừng. Cô Lụa kể chiều nay đông khách lẻ, trả lại tiền thừa nhiều lần.',
              'over': 'Ngăn kéo có mẩu giấy: “Khách mua 1 khay mây trả tiền, chưa viết phiếu thu?” — chưa ai xác nhận.',
              'ok': 'Ngăn kéo gọn gàng, các phiếu thu/chi đều đã vào sổ.'}[variant]
    lines = {'ok': [], 'voucher': [['642', '111', gap]], 'short': [['1381', '111', gap]], 'over': [['111', '3381', gap]]}[variant]
    docs = [
        _doc('count', 'cash', 'Bảng kiểm đếm tiền mặt', 'Cô Lụa & bạn cùng đếm', denoms=counts),
        _doc('cashbook', 'table', f'Sổ quỹ tiền mặt ngày {_d(dom, m)}', 'Phần mềm kế toán', cols=['Chứng từ', 'Diễn giải', 'Thu', 'Chi'],
             rows=[[n, lbl, _n(a), ''] for n, lbl, a in receipts] + [[n, lbl, '', _n(a)] for n, lbl, a in payments],
             foot=[['', 'Tồn quỹ đầu ngày', _n(opening), '']]),
        _doc('drawer', 'note', 'Ngăn kéo quỹ', 'Kiểm tra tại chỗ', text=drawer),
    ]
    steps = [
        _number('count', 'Tiền thực đếm', 'Cộng số tiền thực tế trong két theo bảng kiểm đếm.', counted, docs=['count'],
                hints=['Mỗi dòng: mệnh giá × số tờ, rồi cộng lại.'], explain=f'Tiền thực đếm: {_n(counted)} xu.'),
        _number('book', 'Tồn quỹ theo sổ', 'Tồn quỹ cuối ngày theo sổ = tồn đầu + thu − chi.', book, docs=['cashbook'],
                hints=['Lấy tồn đầu ngày, cộng các phiếu thu, trừ các phiếu chi.'], explain=f'Tồn theo sổ: {_n(book)} xu.'),
        _choice('handle', 'Xử lý chênh lệch', 'So tiền đếm với sổ và xem ngăn kéo. Xử lý thế nào?',
                [('ok', 'Khớp: hai bên ký biên bản kiểm kê quỹ'), ('voucher', 'Ghi bổ sung phiếu chi còn sót, rồi đối chiếu lại'),
                 ('short', 'Lập biên bản thiếu quỹ, treo chờ xử lý, báo kế toán trưởng'), ('over', 'Lập biên bản thừa quỹ, treo chờ giải quyết, tìm người nộp'),
                 ('cover', 'Thủ quỹ tự bù/lấy bớt cho khớp, khỏi biên bản')], variant, rng, docs=['drawer'],
                hints=['Chênh lệch có chứng từ giải thích thì ghi chứng từ; không giải thích được thì lập biên bản và treo tài khoản chờ xử lý.'],
                explain={'ok': 'Khớp thì vẫn ký biên bản — đó là bằng chứng quỹ được kiểm.', 'voucher': 'Phiếu chi hợp lệ bị sót: ghi vào sổ, chênh lệch biến mất.',
                         'short': 'Thiếu không rõ lý do: biên bản + TK 1381 chờ xử lý, không đổ lỗi, không tự bù.',
                         'over': 'Thừa chưa rõ nguồn: biên bản + TK 3381 chờ giải quyết.'}[variant]),
    ]
    if lines:
        steps.append(_entry('entry', 'Bút toán quỹ', 'Ghi bút toán cho phần chênh lệch đã xác định.', lines,
                            hints=['Tiền mặt giảm → Có 111; tiền mặt tăng → Nợ 111.', 'Thiếu chờ xử lý: 1381; thừa chờ giải quyết: 3381; phiếu chi văn phòng: 642.'],
                            explain=f'{_lines_text(lines)}.'))
    return dict(npc=2, title=f'Kiểm quỹ tiền mặt ngày {_d(dom, m)}', opening='Cuối ngày rồi, mình kiểm quỹ nhé cháu. Cô đếm ba lần mà tim vẫn đập thình thịch.',
                brief='Đếm tiền trong két theo mệnh giá, tính tồn quỹ theo sổ, tìm nguyên nhân chênh lệch và ghi nhận đúng.',
                docs=docs, steps=steps, value=book,
                handover=f'Kiểm quỹ {_d(dom, m)}: đếm {_n(counted)}, sổ {_n(book)}. ' + ({'ok': 'Khớp, đã ký biên bản.'}.get(variant) or f'Đã xử lý: {_lines_text(lines)}; có biên bản kèm.'))


ASSETS = [('Xe tải nhỏ giao hàng', '641'), ('Kệ trưng bày showroom', '641'), ('Xe máy giao hàng', '641'),
          ('Máy tính phòng kế toán', '642'), ('Máy photocopy', '642'), ('Điều hòa phòng họp', '642')]


def g_depreciation(rng, day, slot):
    m, _, _ = _period(day)
    sales = [a for a in ASSETS if a[1] == '641']
    admin = [a for a in ASSETS if a[1] == '642']
    picks = [rng.choice(sales), rng.choice(admin)]
    rest = [a for a in ASSETS if a not in picks]
    picks.append(rng.choice(rest))
    status = ['normal', 'normal', rng.choice(['full', 'new', 'normal'])]
    rows, fields, key, sums, nbv = [], [], {}, {'641': 0, '642': 0}, None
    for i, ((name, acct), st) in enumerate(zip(picks, status)):
        years = rng.choice([3, 4, 5, 6, 8])
        monthly = rng.choice([5, 10, 15, 20, 25, 30, 40, 50])
        cost = monthly * years * 12
        if st == 'full':
            acc, use, dep = cost, f'{years + 1} năm trước', 0
        elif st == 'new':
            acc, use, dep = 0, f'15/{m:02d} (tháng này)', 0
        else:
            k = rng.randrange(3, years * 12 - 3)
            acc, use, dep = monthly * k, f'{k} tháng trước', monthly
            if nbv is None:
                nbv = (name, cost - acc - monthly)
        fid = f'a{i + 1}'
        rows.append([name, 'Bán hàng (641)' if acct == '641' else 'Quản lý (642)', _n(cost), f'{years} năm', use, _n(acc)])
        fields.append(dict(id=fid, label=name, unit='xu/tháng'))
        key[fid] = dep
        sums[acct] += dep
    lines = [[a, '214', v] for a, v in sums.items() if v]
    docs = [
        _doc('register', 'table', 'Sổ tài sản cố định', 'Phần mềm kế toán', cols=['Tài sản', 'Bộ phận', 'Nguyên giá', 'Thời gian dùng', 'Đưa vào dùng', 'Hao mòn lũy kế'], rows=rows),
        _doc('policy', 'note', 'Chính sách khấu hao', 'Chị Hạnh', text='Khấu hao đường thẳng: mức tháng = nguyên giá ÷ (số năm × 12). '
             'Tài sản đưa vào dùng trong tháng thì bắt đầu trích từ tháng sau. Tài sản đã khấu hao hết (hao mòn lũy kế = nguyên giá) thì thôi trích. '
             'Chi phí khấu hao ghi theo bộ phận sử dụng.'),
    ]
    steps = [
        _fields('monthly', 'Mức khấu hao tháng', f'Tính khấu hao tháng {m} cho từng tài sản.', fields, key, docs=['register', 'policy'],
                hints=['Nguyên giá ÷ (số năm × 12).', 'Đọc cột “Đưa vào dùng” và “Hao mòn lũy kế”: có tài sản không cần trích tháng này.'],
                explain='; '.join(f'{f["label"]}: {_n(key[f["id"]])}' for f in fields) + '.'),
        _entry('entry', 'Bút toán khấu hao', 'Ghi chi phí khấu hao theo bộ phận sử dụng.', lines,
               hints=['Hao mòn tăng → Có 214.', 'Tài sản của bán hàng → Nợ 641; của quản lý → Nợ 642. Gộp theo bộ phận.'], explain=f'{_lines_text(lines)}.'),
        _number('nbv', 'Giá trị còn lại', f'Giá trị còn lại của “{nbv[0]}” sau khi trích tháng này?', nbv[1], docs=['register'],
                hints=['Giá trị còn lại = nguyên giá − hao mòn lũy kế (đã cộng tháng này).'], explain=f'Giá trị còn lại: {_n(nbv[1])} xu.'),
    ]
    return dict(npc=1, title=f'Trích khấu hao TSCĐ tháng {m}', opening='Anh cần số khấu hao tháng này để tính giá chào hàng. Đừng trích thiếu, cũng đừng trích dư nha em.',
                brief='Tính khấu hao đường thẳng cho từng tài sản, ghi chi phí theo bộ phận và cập nhật giá trị còn lại.',
                docs=docs, steps=steps, value=sum(sums.values()), handover=f'Khấu hao tháng {m}: {_lines_text(lines)}. Tài sản hết khấu hao/mới đưa vào dùng không trích.')


STOCK = [('may', 'Mây sợi', 'kg', '152', 12), ('son', 'Sơn phủ gốc nước', 'thùng', '152', 70), ('gio', 'Giỏ mây cỡ M', 'chiếc', '156', 45),
         ('den', 'Đèn tre', 'chiếc', '156', 90), ('thung', 'Thùng carton', 'cái', '152', 6)]


def g_inventory_count(rng, day, slot):
    m, _, dom = _period(day)
    variant = rng.choice(['unissued', 'norm', 'unknown'])
    items = [STOCK[0]] + rng.sample(STOCK[1:], 3)
    target = items[0] if variant == 'norm' else rng.choice([x for x in items if x[3] == '156'] or items[1:])
    rows_card, rows_count, fields, key = [], [], [], {}
    short = 0
    for sid, name, unit, acct, cost in items:
        qty = rng.randrange(40, 50) * 10 if sid == 'may' else rng.randrange(20, 90)
        diff = 0
        if sid == target[0]:
            diff = -(rng.choice([4, 6, 8]) if variant == 'norm' else rng.randrange(2, 7))
            short = -diff
        rows_card.append([name, unit, _n(cost), str(qty)])
        rows_count.append([name, unit, str(qty + diff)])
        fields.append(dict(id=sid, label=name, unit=unit))
        key[sid] = diff
    value = short * target[4]
    notes = {'unissued': f'Chú Toàn: “À, sáng {_d(dom, m)} Bảo lấy {short} {target[2]} {target[1].lower()} giao gấp cho khách, phiếu xuất PX-{rng.randrange(10, 99)} khách đã ký, '
                         'hóa đơn bán đã ghi doanh thu rồi — chỉ quên chuyển phiếu xuất cho kế toán.”',
             'norm': 'Chú Toàn: “Mùa nồm, mây sợi hút ẩm rồi khô lại nên hụt cân.” Định mức hao hụt mây sợi trong kho: tối đa 2% số tồn.',
             'unknown': 'Chú Toàn: “Chú rà hết phiếu xuất rồi, không sót phiếu nào. Tuần này camera kho hỏng, khóa cửa phụ cũng lỏng.”'}[variant]
    lines = {'unissued': [['632', '156', value]], 'norm': [['632', '152', value]], 'unknown': [['1381', target[3], value]]}[variant]
    docs = [
        _doc('card', 'table', 'Thẻ kho (số liệu sổ sách)', 'Phần mềm kế toán', cols=['Vật tư/hàng hóa', 'ĐVT', 'Đơn giá vốn', 'Tồn theo sổ'], rows=rows_card),
        _doc('count', 'table', f'Biên bản kiểm kê ngày {_d(dom, m)}', 'Tổ kiểm kê (3 chữ ký)', cols=['Vật tư/hàng hóa', 'ĐVT', 'Thực đếm'], rows=rows_count),
        _doc('notes', 'note', 'Giải trình của thủ kho', 'Chú Toàn', text=notes),
    ]
    steps = [
        _fields('diff', 'Chênh lệch từng mã', 'Chênh lệch = thực đếm − sổ sách (âm là thiếu).', fields, key, docs=['card', 'count'],
                hints=['So từng dòng thẻ kho với biên bản kiểm kê.', 'Thiếu thì ghi số âm, khớp thì ghi 0.'], explain=f'Chỉ {target[1].lower()} lệch: thiếu {short} {target[2]}.'),
        _number('value', 'Giá trị hàng thiếu', 'Giá trị phần thiếu theo giá vốn?', value, docs=['card'],
                hints=['Số lượng thiếu × đơn giá vốn.'], explain=f'{short} × {_n(target[4])} = {_n(value)} xu.'),
        _choice('cause', 'Nguyên nhân & cách xử lý', 'Đọc giải trình của thủ kho. Kết luận thế nào?',
                [('unissued', 'Hàng đã xuất bán nhưng thiếu phiếu xuất: ghi bổ sung giá vốn'), ('norm', 'Hao hụt trong định mức: tính vào giá vốn'),
                 ('unknown', 'Thiếu chưa rõ nguyên nhân: biên bản, treo 1381 chờ xử lý'), ('fixcard', 'Sửa thẻ kho cho khớp số đếm, khỏi báo cáo')], variant, rng, docs=['notes'],
                hints=['Có chứng từ giải thích → ghi theo chứng từ. Không giải thích được → treo chờ xử lý, không tự “sửa cho khớp”.'],
                explain={'unissued': 'Hàng đã giao khách có chữ ký: bổ sung phiếu xuất, ghi giá vốn.', 'norm': 'Hụt trong định mức 2%: tính vào giá vốn.',
                         'unknown': 'Không rõ nguyên nhân: 1381 chờ quyết định xử lý (bồi thường/ghi chi phí), tăng cường kiểm soát kho.'}[variant]),
        _entry('entry', 'Ghi sổ chênh lệch', 'Ghi bút toán cho phần hàng thiếu.', lines,
               hints=['Hàng rời kho → Có 152/156 đúng loại.', 'Bên Nợ là 632 (giá vốn) hoặc 1381 (chờ xử lý) tùy kết luận.'], explain=f'{_lines_text(lines)}.'),
    ]
    return dict(npc=6, title=f'Kiểm kê kho ngày {_d(dom, m)}', opening='Đếm xong rồi đây, có một mã lệch. Cháu xem giúp chú, chú không muốn bị nghi oan đâu nhé.',
                brief='So biên bản kiểm kê với thẻ kho, tính giá trị hàng thiếu, kết luận nguyên nhân và ghi sổ đúng bản chất.',
                docs=docs, steps=steps, value=value, handover=f'Kiểm kê {_d(dom, m)}: thiếu {short} {target[2]} {target[1].lower()} = {_n(value)} xu. Đã ghi {_lines_text(lines)}.')


def g_month_close(rng, day, slot):
    m, _, _ = _period(day)
    rev = rng.randrange(40, 80) * 100
    cogs = rev * rng.choice([55, 60, 65]) // 100
    sell = rev * rng.choice([6, 8, 10]) // 1000 * 10
    admin = rev * rng.choice([7, 9, 11]) // 1000 * 10
    accr = rng.randrange(3, 10) * 10
    vout = rev // 10
    vin = min(rng.randrange(20, 45) * 10, vout - 50)
    profit = rev - cogs - sell - admin - accr
    docs = [
        _doc('balances', 'table', f'Số dư tài khoản trước khóa sổ · tháng {m}', 'Phần mềm kế toán', cols=['TK', 'Tên', 'Phát sinh trong tháng'],
             rows=[['511', ACCOUNT_NAME['511'], _n(rev)], ['632', ACCOUNT_NAME['632'], _n(cogs)], ['641', ACCOUNT_NAME['641'], _n(sell)],
                   ['642', ACCOUNT_NAME['642'] + ' (chưa gồm tiền điện)', _n(admin)], ['133', ACCOUNT_NAME['133'], _n(vin)], ['3331', ACCOUNT_NAME['3331'], _n(vout)]]),
        _doc('bill', 'note', 'Thông báo tiền điện', 'Công ty Điện Lực Sáng', text=f'Chỉ số công tơ văn phòng tháng {m}: ước tính {_n(accr)} xu. Hóa đơn sẽ phát hành ngày 05 tháng sau.'),
        _doc('checklist', 'note', 'Quy chế khóa sổ của công ty', 'Chị Hạnh', text='Chỉ kết chuyển khi mọi chi phí của tháng đã nằm trong sổ, kể cả chi phí chưa có hóa đơn (trích trước) và khấu hao. '
             'Thuế GTGT đầu vào được khấu trừ với thuế đầu ra trước khi lập tờ khai. Doanh thu, chi phí kết chuyển sang 911; lãi/lỗ của 911 kết chuyển sang 421.'),
    ]
    close = [['511', '911', rev], ['911', '632', cogs], ['911', '641', sell], ['911', '642', admin + accr]]
    steps = [
        _order('order', 'Thứ tự khóa sổ', 'Sắp xếp các bước khóa sổ tháng theo đúng thứ tự.',
               [('accrual', 'Trích trước chi phí chưa có hóa đơn'), ('deprec', 'Kiểm tra bút toán khấu hao tháng'), ('vat', 'Khấu trừ thuế GTGT (133 ↔ 3331)'),
                ('close_rev', 'Kết chuyển doanh thu sang 911'), ('close_exp', 'Kết chuyển giá vốn & chi phí sang 911'), ('profit', 'Kết chuyển lãi/lỗ từ 911 sang 421')], rng,
               docs=['checklist'], hints=['Chi phí phải đủ trước khi kết chuyển.', 'Bước cuối cùng luôn là kết chuyển 911 → 421.'],
               explain='Ghi nhận đủ (trích trước, khấu hao) → thuế → kết chuyển doanh thu, chi phí → lãi/lỗ.'),
        _entry('accrual', 'Trích trước tiền điện', 'Ghi chi phí điện tháng này dù hóa đơn tháng sau mới về.', [['642', '335', accr]], post=False, docs=['bill'],
               hints=['Chi phí của tháng này nhưng chưa trả, chưa có hóa đơn → Có 335 Chi phí phải trả.'], explain=f'Nợ 642 / Có 335: {_n(accr)}.'),
        _entry('vat', 'Khấu trừ thuế GTGT', 'Bù trừ thuế đầu vào với thuế đầu ra.', [['3331', '133', vin]], post=False, docs=['balances'],
               hints=['Số được khấu trừ là số nhỏ hơn giữa 133 và 3331.', 'Giảm thuế phải nộp → Nợ 3331; giảm thuế được khấu trừ → Có 133.'],
               explain=f'Nợ 3331 / Có 133: {_n(vin)}.'),
        _number('vat_pay', 'Thuế GTGT còn phải nộp', 'Sau khi khấu trừ, thuế GTGT phải nộp tháng này là bao nhiêu?', vout - vin,
                hints=['Thuế đầu ra − thuế đầu vào đã khấu trừ.'], explain=f'{_n(vout)} − {_n(vin)} = {_n(vout - vin)} xu.'),
        _entry('close', 'Kết chuyển sang 911', 'Kết chuyển doanh thu và toàn bộ chi phí (đã gồm tiền điện trích trước) sang 911.', close, post=False,
               hints=['Doanh thu có số dư Có → kết chuyển: Nợ 511 / Có 911.', 'Chi phí có số dư Nợ → kết chuyển: Nợ 911 / Có 632, 641, 642. Nhớ cộng tiền điện vào 642.'],
               explain=f'{_lines_text(close)}.'),
        _entry('profit', 'Kết chuyển lãi', 'Kết chuyển kết quả kinh doanh tháng sang 421.', [['911', '421', profit]], post=False,
               hints=['Lãi = doanh thu − giá vốn − chi phí bán hàng − chi phí quản lý (đã gồm trích trước).', 'Lãi: Nợ 911 / Có 421.'],
               explain=f'Lãi tháng {m}: {_n(profit)} xu → Nợ 911 / Có 421.'),
    ]
    return dict(npc=0, title=f'Khóa sổ tháng {m}', opening=f'Hôm nay khóa sổ tháng {m}. Làm đúng thứ tự, đừng kết chuyển khi còn chi phí chưa ghi nhé.',
                brief=f'Khóa sổ tháng {m}: trích trước, khấu trừ thuế GTGT, kết chuyển doanh thu – chi phí sang 911 và lãi sang 421. Sổ cái của bạn cũng được kết chuyển khi nộp.',
                docs=docs, steps=steps, value=profit,
                handover=f'Khóa sổ tháng {m}: trích trước điện {_n(accr)}, khấu trừ VAT {_n(vin)}, VAT phải nộp {_n(vout - vin)}, lãi {_n(profit)} kết chuyển 421.')


def g_trial_balance(rng, day, slot):
    m, _, _ = _period(day)
    debit = {'111': rng.randrange(50, 150) * 10, '112': rng.randrange(300, 900) * 10, '131': rng.randrange(100, 400) * 10, '152': rng.randrange(80, 250) * 10,
             '156': rng.randrange(100, 300) * 10, '211': rng.randrange(600, 1200) * 10, '632': rng.randrange(300, 600) * 10,
             '641': rng.randrange(40, 120) * 10, '642': rng.randrange(60, 150) * 10}
    credit = {'214': rng.randrange(100, 400) * 10, '331': rng.randrange(100, 300) * 10, '3331': rng.randrange(10, 60) * 10, '421': rng.randrange(50, 200) * 10}
    credit['511'] = debit['632'] + debit['641'] + debit['642'] + rng.randrange(50, 200) * 10
    cap = sum(debit.values()) - sum(credit.values())
    if cap < 2000:
        debit['112'] += 2000 - cap + 500
        cap = sum(debit.values()) - sum(credit.values())
    credit['411'] = cap
    order = ['111', '112', '131', '152', '156', '211', '214', '331', '3331', '411', '421', '511', '632', '641', '642']
    variant = rng.choice(['transpose', 'side'])

    def swappable(v):
        s = str(v)
        return len(s) >= 3 and s[-3] != s[-2]
    cands = [a for a in order if a != '411' and (variant == 'side' or swappable(debit.get(a) or credit.get(a)))]
    if not cands:
        variant = 'side'
        cands = [a for a in order if a != '411']
    bad = rng.choice(cands)
    rows, td, tc = [], 0, 0
    for a in order:
        v = debit.get(a) or credit.get(a)
        on_debit = a in debit
        shown = v
        if a == bad:
            if variant == 'transpose':
                s = str(v)
                shown = int(s[:-3] + s[-2] + s[-3] + s[-1])
            else:
                on_debit = not on_debit
        rows.append([a, ACCOUNT_NAME[a], _n(shown) if on_debit else '', '' if on_debit else _n(shown)])
        td += shown if on_debit else 0
        tc += 0 if on_debit else shown
    diff = abs(td - tc)
    gross = credit['511'] - debit['632']
    pbt = gross - debit['641'] - debit['642']
    docs = [
        _doc('tb', 'table', f'Bảng cân đối thử tháng {m} (bản nháp)', 'Bạn nhập tay từ sổ cái', cols=['TK', 'Tên tài khoản', 'Dư Nợ', 'Dư Có'], rows=rows,
             foot=[['', 'Tổng cộng', _n(td), _n(tc)]]),
        _doc('ledger', 'table', f'Sổ cái — số dư cuối tháng {m}', 'Phần mềm kế toán', cols=['TK', 'Số dư', 'Bên'],
             rows=[[a, _n(debit.get(a) or credit.get(a)), 'Nợ' if a in debit else 'Có'] for a in sorted(order)]),
        _doc('tips', 'note', 'Mẹo dò lỗi của anh Khải', 'Anh Khải', text='Chênh lệch chia hết cho 9 thường là đảo chữ số khi chép (ví dụ 540 ↔ 450). '
             'Chênh lệch bằng đúng hai lần một số dư thường là chép nhầm bên Nợ/Có. Cuối cùng, so từng dòng với sổ cái.'),
    ]
    steps = [
        _number('diff', 'Chênh lệch', 'Tổng Dư Nợ và tổng Dư Có lệch nhau bao nhiêu?', diff, docs=['tb'],
                hints=['Lấy tổng lớn trừ tổng nhỏ.'], explain=f'|{_n(td)} − {_n(tc)}| = {_n(diff)} xu.'),
        _choice('culprit', 'Dòng chép sai', 'Dòng nào trong bảng bị chép sai?', [(a, f'TK {a} · {ACCOUNT_NAME[a]}') for a in order], bad, rng, docs=['ledger', 'tips'],
                hints=['Chênh lệch chia hết cho 9 → tìm số bị đảo chữ số; bằng hai lần một số dư → tìm số nằm sai cột.',
                       'Tài khoản tài sản, chi phí thường dư Nợ; nợ phải trả, vốn, doanh thu, hao mòn thường dư Có.'],
               explain=f'TK {bad}: ' + ('đảo chữ số khi chép.' if variant == 'transpose' else 'ghi nhầm sang cột bên kia.')),
        _fields('is', 'Báo cáo kết quả kinh doanh', 'Sau khi sửa dòng sai, lập nhanh các chỉ tiêu tháng.',
                [dict(id='rev', label='Doanh thu thuần (511)', unit='xu'), dict(id='gross', label='Lợi nhuận gộp', unit='xu'), dict(id='pbt', label='Lợi nhuận trước thuế', unit='xu')],
                dict(rev=credit['511'], gross=gross, pbt=pbt), docs=['ledger'],
                hints=['Lợi nhuận gộp = doanh thu − giá vốn.', 'Lợi nhuận trước thuế = lợi nhuận gộp − chi phí bán hàng − chi phí quản lý. Dùng số đã sửa!'],
                explain=f'Doanh thu {_n(credit["511"])}; gộp {_n(gross)}; trước thuế {_n(pbt)} xu.'),
    ]
    return dict(npc=4, title=f'Bảng cân đối thử tháng {m} không cân', opening='Bảng cân đối thử em gửi lệch. Tìm lỗi rồi gửi lại báo cáo kết quả kinh doanh giúp anh.',
                brief='Dò lỗi làm bảng cân đối thử không cân, sửa, rồi lập các chỉ tiêu kết quả kinh doanh.', docs=docs, steps=steps, value=pbt,
                handover=f'BCĐ thử tháng {m}: lệch {_n(diff)} do TK {bad} chép sai; đã sửa. Doanh thu {_n(credit["511"])}, LN gộp {_n(gross)}, LNTT {_n(pbt)}.')


GENERATORS = dict(journal=g_journal, invoice_in=g_invoice_in, invoice_out=g_invoice_out, bank_rec=g_bank_rec, ageing=g_ageing,
                  petty_cash=g_petty_cash, inventory_count=g_inventory_count, depreciation=g_depreciation,
                  trial_balance=g_trial_balance, month_close=g_month_close)


def _legacy_kind(day: int, slot: int) -> str:
    row = LEGACY_SCHEDULE[(day - 1) % 5]
    return row[slot] if slot < len(row) else LEGACY_KIND_IDS[(day * 7 + slot * 3) % len(LEGACY_KIND_IDS)]


def _kind(day: int, slot: int) -> str:
    row = SCHEDULE[(day - 1) % 5]
    if slot < len(row):
        return row[slot]
    return 'desk' if slot % 2 == 0 else LEGACY_KIND_IDS[(day * 7 + slot * 3) % len(LEGACY_KIND_IDS)]


# ---------------------------------------------------------------- the day: luck, rules that shift by month
MODS = [
    dict(id='normal', min_day=1, weight=3, emoji='☀️', name='Ngày bình thường',
         text='Khay chứng từ, vài hồ sơ, chị Hạnh ngồi bàn bên.'),
    dict(id='audit', min_day=2, weight=2, emoji='🔎', name='Kiểm toán ghé',
         text='Cuối ngày anh Khải rút mẫu các bộ chứng từ bạn đã đóng dấu: sạch thì có thưởng, sót thì bị phạt thêm.'),
    dict(id='lag', min_day=2, weight=2, emoji='🐢', name='Phần mềm chậm',
         text='Mạng nội bộ ì ạch: mở chứng từ, tra sổ tốn gấp đôi thời gian.'),
    dict(id='intern', min_day=2, weight=2, emoji='🧑‍🎓', name='Thực tập sinh vào làm',
         text='Em Na lập thêm phiếu chi nháp — nhiệt tình nhưng hay cộng nhầm.'),
    dict(id='boss_away', min_day=3, weight=2, emoji='✈️', name='Chị Hạnh đi công tác',
         text='Xin gợi ý phải nhắn tin, chờ 15 phút. Có người sẽ “mượn lời sếp” để chi gấp.'),
    dict(id='rush', min_day=3, weight=1, emoji='📦', name='Hàng về dồn dập',
         text='Nhà cung cấp giao dồn: khay chứng từ dày thêm một bộ.'),
    dict(id='crunch', forced_only=True, emoji='🔥', name='Ngày khóa sổ',
         text='Cuối tháng: hạn sớm hơn 30 phút, khay dày hơn. Ở lại tăng ca được thêm phụ cấp và sếp ghi nhận.'),
]
MOD_INDEX = {x['id']: x for x in MODS}
FORCED = {4: 'crunch'}
INTRO = {2: 'intern', 3: 'audit', 4: 'boss_away'}
LIMITS = (500, 300, 400, 250)
VERDICTS = ('approve', 'escalate', 'reject')
VERDICT_LABEL = dict(approve='DUYỆT', escalate='TRÌNH SẾP', reject='TRẢ LẠI')
MAX_CIRCLES = 3
EXTRA_SUP = [
    dict(id='gio', abbr='GL', name='Công ty TNHH Gió Lạ', mst='0106420871', bank='0341 7720 5566', item='Bảo trì máy lạnh văn phòng'),
    dict(id='nhanh', abbr='IN', name='Cơ sở In Ấn Nhanh', mst='0107953102', bank='0508 1163 2290', item='In catalogue sản phẩm'),
    dict(id='keo', abbr='PA', name='Xưởng Keo Dán Phúc An', mst='0105318864', bank='0612 4478 9031', item='Keo dán tre'),
    dict(id='chop', abbr='TC', name='Công ty Vận Tải Tia Chớp', mst='0108264719', bank='0725 9031 4462', item='Cước xe tải giao hàng'),
]
UTILITIES = [dict(id='dien', name='Công ty Điện Lực Sáng', mst='0100110022', bank='0101 0000 1188', item='Tiền điện văn phòng & xưởng'),
             dict(id='net', name='Công ty Mạng Sao Việt', mst='0109988776', bank='0202 3344 5566', item='Cước Internet cáp quang')]
BANKS = dict(sau='0114 2256 7788', son='0231 5540 1276', moc='0356 7781 0042', hp='0418 6620 3395', cs='0529 1134 8870')


def _mod(day: int) -> dict:
    return office.mod_of(ID, day, MODS, FORCED, INTRO)


def _rules_raw(day: int) -> dict:
    k = (day - 1) // 5
    m, phase, dom = _period(day)
    return dict(k=k, m=m, phase=phase, dom=dom, prev=(m - 2) % 12 + 1, limit=LIMITS[k % len(LIMITS)],
                blocked=EXTRA_SUP[k % len(EXTRA_SUP)]['id'], vat_cut=k % 3 == 1, split=day >= 4, cash=day >= 3)


def _rule_cards(day: int) -> list:
    r = _rules_raw(day)
    blk = next(x for x in EXTRA_SUP if x['id'] == r['blocked'])
    cards = [dict(id='stamps', emoji='🟢', title='Ba con dấu', text='DUYỆT: hợp lệ · TRẢ LẠI: sai, thiếu, giả · TRÌNH SẾP: vượt thẩm quyền hoặc có nghi vấn.'),
             dict(id='limit', emoji='✍️', title='Hạn mức ký duyệt', text=f'Kế toán trưởng ký tới {_n(r["limit"])} xu. Lớn hơn → trình Giám đốc.'),
             dict(id='blocked', emoji='⛔', title='Ngừng giao dịch', text=f'{blk["name"]} ngừng hoạt động từ 01/{r["m"]:02d}: hóa đơn từ ngày đó không hợp lệ.'),
             dict(id='bank', emoji='🏦', title='Đổi tài khoản nhận tiền', text='Chỉ theo công văn có dấu và gọi lại số đã đăng ký. Email đòi đổi tài khoản → trả lại.'),
             dict(id='lock', emoji='🔒', title=f'Sổ tháng {r["prev"]} đã khóa', text='Không lập, không ghi chứng từ lùi ngày về tháng trước.'),
             dict(id='personal', emoji='🙅', title='Chi phí cá nhân', text='Không thanh toán khoản không phục vụ công việc.')]
    if r['cash']:
        cards.append(dict(id='cash', emoji='💵', title='Chi từ 200 xu', text='Phải chuyển khoản, không chi tiền mặt.'))
    if r['split']:
        cards.append(dict(id='split', emoji='🧩', title='Không chia nhỏ khoản chi', text='Cùng người nhận, cùng ngày, tách nhỏ cho lọt hạn mức → trình Giám đốc.'))
    if r['vat_cut']:
        cards.append(dict(id='vat', emoji='🧾', title='Thuế GTGT điện, Internet', text=f'Còn 8% cho hóa đơn lập từ 15/{r["m"]:02d}; trước ngày đó vẫn 10%.'))
    return cards


def rules(day: int) -> list:
    """Rule cards for the day; a card is 'new' when it did not read the same yesterday."""
    today = _rule_cards(day)
    before = {x['id']: x['text'] + x['title'] for x in _rule_cards(day - 1)} if day > 1 else None
    for x in today:
        x['new'] = before is not None and before.get(x['id']) != x['text'] + x['title']
    return today


# ---------------------------------------------------------------- the document desk (Papers, Please style)
def _row(z, k, v, strong=False):
    return dict(z=z, k=k, v=v, strong=strong)


def _inv_paper(name, mst, symbol, number, date, lines, rate, signed=True, vat=None, total=None, note=None, buyer=COMPANY):
    base = sum(q * p for _, q, p in lines)
    vat = base * rate // 100 if vat is None else vat
    total = base + vat if total is None else total
    return dict(kind='invoice', title='HÓA ĐƠN GIÁ TRỊ GIA TĂNG', sub='Bản thể hiện của hóa đơn điện tử',
                rows=[_row('number', 'Ký hiệu · Số', f'{symbol} · {number}'), _row('date', 'Ngày lập', date),
                      _row('seller', 'Đơn vị bán', f'{name}\nMST {_mst(mst)}'), _row('buyer', 'Đơn vị mua', f'{buyer}\nMST {_mst(MST_OWN)}')],
                table=dict(z='lines', cols=['Hàng hóa, dịch vụ', 'SL', 'Đơn giá', 'Thành tiền'],
                           rows=[[it, str(q), _n(p), _n(q * p)] for it, q, p in lines]),
                foot=[_row('base', 'Cộng tiền hàng', _n(base)), _row('vat', f'Thuế GTGT {rate}%', _n(vat)),
                      _row('total', 'Tổng thanh toán', _n(total), True),
                      _row('sign', 'Chữ ký số', ('✔ Đã ký số · ' + name) if signed else '✖ Chưa có chữ ký số')],
                note=dict(z='note', text=note) if note else None)


def _req_paper(no, date, requester, payee, bank, lines, method, attach, signs, note=None, title='GIẤY ĐỀ NGHỊ THANH TOÁN'):
    amount = sum(a for _, a in lines)
    return dict(kind='payreq', title=title, sub=f'Số {no}',
                rows=[_row('number', 'Số', no), _row('date', 'Ngày', date), _row(None, 'Người đề nghị', requester),
                      _row('payee', 'Người nhận tiền', payee), _row('bank', 'Tài khoản nhận', bank)],
                table=dict(z='lines', cols=['Nội dung', 'Số tiền'], rows=[[t, _n(a)] for t, a in lines]),
                foot=[_row('amount', 'Số tiền đề nghị', _n(amount), True), _row('method', 'Hình thức', method),
                      _row('attach', 'Chứng từ kèm theo', attach), _row('sign', 'Ký duyệt', signs)],
                note=dict(z='note', text=note) if note else None)


def _signs(director=False, ktt='Hạnh ✔', requester='Bảo ✔'):
    return f'Người đề nghị: {requester}\nKế toán trưởng: {ktt}\nGiám đốc: {"Tùng ✔" if director else "—"}'


def _case(doc, who, quote, paper, kind, verdict, zones, why, fine=0, oops=''):
    return dict(doc=doc, who=who, quote=quote, paper=paper, _k=kind,
                _truth=dict(v=verdict, z=list(zones), why=why, fine=fine, oops=oops))


def _goods_sup(rng, r):
    return rng.choice([x for x in SUPPLIERS if x['id'] != 'cs'])


def _inv_lines(rng, sup):
    q = rng.choice(sup['qty'])
    p = rng.choice(sup['prices'])
    return [(sup['item'], q, p)]


def c_ok_inv(rng, ctx):
    sup = _goods_sup(rng, ctx['r'])
    number = ctx['num'](rng)
    dd = rng.randrange(max(1, ctx['r']['dom'] - 4), ctx['r']['dom'] + 1)
    paper = _inv_paper(sup['name'], sup['mst'], f'1C26T{sup["abbr"]}', number, _d(dd, ctx['r']['m']), _inv_lines(rng, sup), sup['vat'])
    return _case('invoice', 'Chú Toàn · Thủ kho', 'Hàng về đủ rồi, hóa đơn đây. Cháu soát giùm rồi đóng dấu nhé.', paper, 'ok_inv', 'approve', [],
                 'Khớp danh bạ, đã ký số, tính đúng, chưa ghi sổ lần nào — duyệt là đúng.')


def c_dup(rng, ctx):
    sup = _goods_sup(rng, ctx['r'])
    number = ctx['num'](rng)
    m, dom = ctx['r']['m'], ctx['r']['dom']
    first = max(1, dom - rng.choice([3, 4, 6]))
    lines = _inv_lines(rng, sup)
    paper = _inv_paper(sup['name'], sup['mst'], f'1C26T{sup["abbr"]}', number, _d(first, m), lines, sup['vat'])
    total = paper['foot'][2]['v']
    ctx['book'].append([_d(first, m), f'1C26T{sup["abbr"]}-{number}', sup['name'], total, f'Đã ghi sổ · đã trả UNC-{rng.randrange(100, 999)}'])
    return _case('invoice', 'Hộp thư kế toán', f'Email “GẤP — thanh toán giúp”: {sup["name"]} gửi lại một hóa đơn.', paper, 'dup', 'reject', ['number'],
                 f'Số {number} đã ghi sổ ngày {_d(first, m)} và đã thanh toán. Ghi lần hai là trả tiền hai lần.', 25,
                 f'Công ty trả trùng {total} xu cho {sup["name"]}; đòi lại mất ba tháng.')


def c_fake_mst(rng, ctx):
    sup = _goods_sup(rng, ctx['r'])
    fake = _swap(sup['mst'], rng.choice([3, 5, 7]))
    dd = rng.randrange(max(1, ctx['r']['dom'] - 3), ctx['r']['dom'] + 1)
    paper = _inv_paper(sup['name'], fake, f'1C26T{sup["abbr"]}', ctx['num'](rng), _d(dd, ctx['r']['m']), _inv_lines(rng, sup), sup['vat'])
    return _case('invoice', 'Bảo · Kinh doanh', 'Bên bán gửi qua Zalo cho em, anh chị duyệt nhanh giùm nha.', paper, 'fake_mst', 'reject', ['seller'],
                 f'MST trên hóa đơn là {_mst(fake)}, danh bạ ghi {_mst(sup["mst"])} — hóa đơn không phải của người bán thật.', 25,
                 'Hóa đơn giả bị cơ quan thuế loại: mất tiền thuế được khấu trừ, công ty bị phạt.')


def c_nosign(rng, ctx):
    sup = _goods_sup(rng, ctx['r'])
    dd = rng.randrange(max(1, ctx['r']['dom'] - 3), ctx['r']['dom'] + 1)
    paper = _inv_paper(sup['name'], sup['mst'], f'1C26T{sup["abbr"]}', ctx['num'](rng), _d(dd, ctx['r']['m']), _inv_lines(rng, sup), sup['vat'], signed=False)
    return _case('invoice', 'Chú Toàn · Thủ kho', 'Hóa đơn in từ email, chú kẹp vào phiếu nhập rồi.', paper, 'nosign', 'reject', ['sign'],
                 'Hóa đơn điện tử chưa có chữ ký số của người bán thì chưa hợp lệ.', 10,
                 'Hóa đơn chưa ký bị loại khi quyết toán; phải xin người bán ký lại.')


def c_math(rng, ctx):
    m, dom = ctx['r']['m'], ctx['r']['dom']
    items = rng.sample([('Mua băng keo, dây buộc hàng', 30, 90), ('Nước uống văn phòng', 20, 60), ('Mực in máy văn phòng', 60, 120),
                        ('Gửi hàng mẫu qua bưu điện', 20, 70), ('Sửa khóa cửa kho', 40, 90)], 3)
    lines = [(t, rng.randrange(lo // 10, hi // 10 + 1) * 10) for t, lo, hi in items]
    true = sum(a for _, a in lines)
    shown = true + rng.choice([-100, -90, 90, 100])
    paper = dict(kind='voucher', title='PHIẾU CHI (NHÁP)', sub=f'Số PC-{rng.randrange(100, 999)}',
                 rows=[_row('date', 'Ngày', _d(dom, m)), _row('payee', 'Người nhận tiền', 'Cô Lụa (thủ quỹ chi hộ)')],
                 table=dict(z='lines', cols=['Nội dung', 'Số tiền'], rows=[[t, _n(a)] for t, a in lines]),
                 foot=[_row('total', 'Cộng', _n(shown), True), _row('sign', 'Ký', 'Người lập: Na (thực tập) ✔\nKế toán trưởng: —')], note=None)
    return _case('voucher', 'Em Na · Thực tập', 'Em lập phiếu chi rồi ạ, em cộng hai lần luôn á!', paper, 'math', 'reject', ['total'],
                 f'Cộng ba dòng ra {_n(true)} xu, phiếu ghi {_n(shown)}. Trả lại để Na sửa — sai tổng là lệch quỹ.', 10,
                 'Quỹ lệch đúng khoản cộng nhầm; cuối ngày cả phòng ngồi đếm lại tiền.')


PERSONAL = [('Karaoke Hát Vui (tối Chủ nhật)', 240), ('Bánh sinh nhật bé Su', 90), ('Mỹ phẩm Hàn Quốc', 150), ('Vé xem phim gia đình', 120),
            ('Đồ chơi lắp ráp cho con', 110)]


def c_personal(rng, ctx):
    m, dom = ctx['r']['m'], ctx['r']['dom']
    ok = [('Taxi đi gặp khách Nhà Xinh', rng.randrange(4, 9) * 10), ('Cơm trưa tiếp khách (3 người)', rng.randrange(12, 20) * 10)]
    bad = rng.choice(PERSONAL)
    lines = ok + [bad]
    rng.shuffle(lines)
    paper = _req_paper(f'ĐNTT-{m:02d}{rng.randrange(10, 99)}', _d(dom, m), 'Bảo · Kinh doanh', 'Bảo (hoàn ứng)', 'TK lương của Bảo',
                       lines, 'Chuyển khoản', 'Hóa đơn bán lẻ (3 tờ)', _signs(ktt='—'), title='ĐỀ NGHỊ THANH TOÁN CHI PHÍ')
    return _case('claim', 'Bảo · Kinh doanh', 'Tiếp khách tuần này mệt xỉu, anh chị duyệt giùm em cái nha 🙏', paper, 'personal', 'reject', ['lines'],
                 f'“{bad[0]}” là chi phí cá nhân, không phục vụ công việc. Trả lại để Bảo bỏ dòng đó.', 15,
                 'Kiểm tra chi phí cuối quý loại khoản cá nhân; bạn bị nhắc nhở và trừ thưởng.')


def _payee(rng, ctx, exclude=()):
    pool = [x for x in SUPPLIERS if x['id'] not in exclude]
    s = rng.choice(pool)
    return s['name'], BANKS[s['id']], s


def c_ok_req(rng, ctx):
    r = ctx['r']
    name, bank, sup = _payee(rng, ctx)
    amount = rng.randrange(max(6, r['limit'] // 40), r['limit'] // 10 - 3) * 10
    method = 'Chuyển khoản'
    paper = _req_paper(f'ĐNTT-{r["m"]:02d}{rng.randrange(10, 99)}', _d(r['dom'], r['m']), 'Chú Toàn · Kho', name, bank,
                       [(f'Thanh toán {sup["item"].lower()}', amount)], method, 'Hóa đơn GTGT + phiếu nhập kho', _signs(requester='Toàn ✔'))
    return _case('payreq', 'Chú Toàn · Thủ kho', 'Trả tiền mây cho người ta đúng hẹn nhé cháu.', paper, 'ok_req', 'approve', [],
                 f'Trong hạn mức {_n(r["limit"])} xu, kế toán trưởng đã ký, đúng tài khoản trong danh bạ, đủ chứng từ — duyệt.')


def c_limit(rng, ctx):
    r = ctx['r']
    name, bank, sup = _payee(rng, ctx)
    amount = r['limit'] + rng.randrange(5, 40) * 10
    paper = _req_paper(f'ĐNTT-{r["m"]:02d}{rng.randrange(10, 99)}', _d(r['dom'], r['m']), 'Bảo · Kinh doanh', name, bank,
                       [(f'Thanh toán {sup["item"].lower()}', amount)], 'Chuyển khoản', 'Hóa đơn GTGT + biên bản nghiệm thu', _signs())
    return _case('payreq', 'Bảo · Kinh doanh', 'Chị Hạnh ký rồi đó, chuyển liền giùm em nha!', paper, 'limit', 'escalate', ['amount', 'sign'],
                 f'{_n(amount)} xu vượt hạn mức {_n(r["limit"])} xu của kế toán trưởng — cần Giám đốc ký. Trình sếp.', 15,
                 'Khoản chi vượt thẩm quyền bị kiểm toán nêu; bạn phải giải trình vì sao duyệt.')


def c_badsign(rng, ctx):
    r = ctx['r']
    name, bank, sup = _payee(rng, ctx)
    amount = rng.randrange(6, max(7, r['limit'] // 10 - 3)) * 10
    paper = _req_paper(f'ĐNTT-{r["m"]:02d}{rng.randrange(10, 99)}', _d(r['dom'], r['m']), 'Bảo · Kinh doanh', name, bank,
                       [(f'Thanh toán {sup["item"].lower()}', amount)], 'Chuyển khoản', 'Hóa đơn GTGT', _signs(ktt='Bảo ✔ (ký thay)'))
    return _case('payreq', 'Bảo · Kinh doanh', 'Chị Hạnh bận, em ký thay luôn cho nhanh nha.', paper, 'badsign', 'reject', ['sign'],
                 'Bảo không có tên trong “Mẫu chữ ký” để ký duyệt chi. Trả lại, chờ người có thẩm quyền ký.', 10,
                 'Khoản chi không đúng thẩm quyền bị kiểm toán nêu tên; bạn bị nhắc nhở.')


def c_noattach(rng, ctx):
    r = ctx['r']
    name, bank, sup = _payee(rng, ctx)
    amount = rng.randrange(6, max(7, r['limit'] // 10 - 3)) * 10
    paper = _req_paper(f'ĐNTT-{r["m"]:02d}{rng.randrange(10, 99)}', _d(r['dom'], r['m']), 'Bảo · Kinh doanh', name, bank,
                       [(f'Tạm trả trước {sup["item"].lower()}', amount)], 'Chuyển khoản', '(không có)', _signs())
    return _case('payreq', 'Bảo · Kinh doanh', 'Hóa đơn họ gửi sau, anh chị cứ chuyển trước giùm em.', paper, 'noattach', 'reject', ['attach'],
                 'Không có hóa đơn hay biên bản nào kèm theo — chưa có căn cứ để chi. Trả lại.', 10,
                 'Chi tiền không chứng từ: cuối tháng không ai giải thích được khoản này.')


def c_cash(rng, ctx):
    r = ctx['r']
    name, bank, sup = _payee(rng, ctx)
    amount = rng.randrange(21, max(22, min(r['limit'] // 10, 45))) * 10
    paper = _req_paper(f'ĐNTT-{r["m"]:02d}{rng.randrange(10, 99)}', _d(r['dom'], r['m']), 'Cô Lụa · Thủ quỹ', name, '(nhận tiền mặt tại quỹ)',
                       [(f'Thanh toán {sup["item"].lower()}', amount)], 'Tiền mặt', 'Hóa đơn GTGT', _signs(requester='Lụa ✔'))
    return _case('payreq', 'Cô Lụa · Thủ quỹ', 'Người ta đứng chờ ở quầy, chi tiền mặt cho nhanh cháu ạ.', paper, 'cash', 'reject', ['method'],
                 f'{_n(amount)} xu từ 200 xu trở lên — phải chuyển khoản, không chi tiền mặt.', 10,
                 'Khoản chi tiền mặt lớn không được khấu trừ thuế; công ty mất phần thuế GTGT.')


def c_blocked(rng, ctx):
    r = ctx['r']
    sup = next(x for x in EXTRA_SUP if x['id'] == r['blocked'])
    dd = rng.randrange(max(2, r['dom'] - 3), r['dom'] + 1)
    q, p = rng.choice([1, 2, 3]), rng.randrange(8, 20) * 10
    paper = _inv_paper(sup['name'], sup['mst'], f'1C26T{sup["abbr"]}', ctx['num'](rng), _d(dd, r['m']), [(sup['item'], q, p)], 10)
    return _case('invoice', 'Hộp thư kế toán', f'{sup["name"]} gửi hóa đơn kèm lời nhắn “thanh toán sớm giúp”.', paper, 'blocked', 'reject', ['seller'],
                 f'{sup["name"]} đã ngừng hoạt động từ 01/{r["m"]:02d}; hóa đơn lập ngày {_d(dd, r["m"])} không hợp lệ.', 15,
                 'Hóa đơn của đơn vị đã ngừng hoạt động bị loại; công ty mất khoản thuế được khấu trừ.')


def c_phish(rng, ctx):
    r = ctx['r']
    sup = rng.choice([x for x in SUPPLIERS if x['id'] in ('sau', 'son', 'moc')])
    fake = f'{rng.randrange(1000, 9999)} {rng.randrange(1000, 9999)} {rng.randrange(1000, 9999)}'
    domain = {'sau': 'maytre-basau.co', 'son': 'sonlatre-vn.co', 'moc': 'baobimoc.net.co'}[sup['id']]
    paper = dict(kind='email', title='EMAIL', sub=f'Chủ đề: THÔNG BÁO ĐỔI TÀI KHOẢN NHẬN TIỀN',
                 rows=[_row('sender', 'Từ', f'{sup["name"]} <ketoan@{domain}>'), _row(None, 'Tới', 'ketoan@maytrexanh.vn'),
                       _row('body', 'Nội dung', 'Từ hôm nay bên em nhận tiền qua tài khoản mới dưới đây. Công nợ tháng này chuyển gấp trong hôm nay giúp em, '
                            'tài khoản cũ đang bảo trì. Đừng gọi điện, bên em đang họp cả ngày.'),
                       _row('bank', 'Tài khoản mới', fake)],
                 table=None, foot=[], note=None)
    return _case('email', 'Hộp thư kế toán', 'Email mới lúc 16:40, gắn cờ “Quan trọng”.', paper, 'phish', 'reject', ['sender', 'bank', 'body'],
                 f'Tên miền lạ ({domain}), đòi chuyển gấp, cấm gọi lại, tài khoản khác danh bạ ({BANKS[sup["id"]]}) — lừa đảo. Không đổi, báo IT.', 40,
                 'Tiền chạy vào tài khoản lạ; ngân hàng chỉ phong tỏa lại được một phần.')


def c_split(rng, ctx):
    r = ctx['r']
    name, bank, sup = _payee(rng, ctx, exclude=('sau',))
    base = rng.randrange(80, 95)
    a1 = r['limit'] * base // 1000 * 10
    a2 = r['limit'] * (base - rng.randrange(3, 8)) // 1000 * 10
    n1 = rng.randrange(10, 90)
    out = []
    for i, amount in enumerate((a1, a2)):
        paper = _req_paper(f'ĐNTT-{r["m"]:02d}{n1 + i}', _d(r['dom'], r['m']), 'Bảo · Kinh doanh', name, bank,
                           [(f'Thanh toán {sup["item"].lower()} (đợt {i + 1})', amount)], 'Chuyển khoản', 'Hóa đơn GTGT', _signs())
        out.append(_case('payreq', 'Bảo · Kinh doanh', 'Đợt hai của cùng lô đó ạ, duyệt luôn giùm em.' if i else 'Tờ này nhỏ thôi, chị Hạnh ký là đủ nè.',
                         paper, 'split', 'escalate', ['amount', 'number', 'payee'],
                         f'Hai đề nghị liền số, cùng người nhận, cùng ngày: {_n(a1)} + {_n(a2)} = {_n(a1 + a2)} xu > hạn mức {_n(r["limit"])} — chia nhỏ để né duyệt. Trình Giám đốc.',
                         15, 'Chia nhỏ khoản chi để lọt hạn mức bị kiểm toán phát hiện; bạn bị nhắc tên trong biên bản.'))
    return out


def c_backdate(rng, ctx):
    r = ctx['r']
    cus = rng.choice(CUSTOMERS)
    pr = rng.choice(PRODUCTS)
    q = rng.choice(pr['qty'])
    price = pr['prices'][0]
    paper = dict(kind='payreq', title='ĐỀ NGHỊ XUẤT HÓA ĐƠN BÁN HÀNG', sub=f'Khách: {cus["name"]}',
                 rows=[_row(None, 'Người đề nghị', 'Anh Tùng · Giám đốc'), _row('delivery', 'Ngày giao hàng', f'03/{r["m"]:02d} (đã giao)'),
                       _row('date', 'Ngày ghi trên hóa đơn', f'30/{r["prev"]:02d}')],
                 table=dict(z='lines', cols=['Hàng hóa', 'SL', 'Đơn giá'], rows=[[pr['name'], str(q), _n(price)]]),
                 foot=[_row('amount', 'Tiền hàng chưa thuế', _n(q * price), True)],
                 note=dict(z='note', text='Ghi ngày 30 tháng trước giúp anh cho đủ doanh số tháng, có gì anh chịu. — T.'))
    return _case('payreq', 'Anh Tùng · Giám đốc', 'Việc nhỏ thôi em, ghi lùi mấy ngày cho đẹp số tháng trước.', paper, 'backdate', 'reject', ['date', 'note', 'delivery'],
                 f'Hàng giao ngày 03/{r["m"]:02d} thì hóa đơn lập ngày giao; sổ tháng {r["prev"]} đã khóa. Không lùi ngày — trả lại, đề xuất báo cáo “đơn chờ giao” riêng.', 20,
                 'Kiểm toán phát hiện doanh thu sai kỳ; báo cáo tháng trước phải điều chỉnh và bạn viết giải trình.')


def c_vat(rng, ctx, wrong=True):
    r = ctx['r']
    u = rng.choice(UTILITIES)
    if wrong:
        dd, rate = rng.randrange(15, r['dom'] + 1), 10
    else:
        dd, rate = rng.choice([(rng.randrange(8, 15), 10), (rng.randrange(15, r['dom'] + 1), 8)])
    amt = rng.randrange(20, 60) * 10
    paper = _inv_paper(u['name'], u['mst'], '1C26TDV', ctx['num'](rng), _d(dd, r['m']), [(u['item'], 1, amt)], rate)
    if wrong:
        return _case('invoice', 'Hộp thư kế toán', f'{u["name"]} gửi hóa đơn tháng này.', paper, 'vat', 'reject', ['vat'],
                     f'Hóa đơn lập {_d(dd, r["m"])} — từ 15/{r["m"]:02d} thuế điện, Internet chỉ còn 8%, hóa đơn ghi 10%. Trả lại để lập hóa đơn điều chỉnh.', 10,
                     'Khấu trừ theo thuế suất sai: tờ khai tháng phải khai bổ sung.')
    when = 'trước 15/' + f'{r["m"]:02d}' + ' nên vẫn 10%' if rate == 10 else 'từ 15/' + f'{r["m"]:02d}' + ' và đã ghi 8%'
    return _case('invoice', 'Hộp thư kế toán', f'{u["name"]} gửi hóa đơn tháng này.', paper, 'vat_ok', 'approve', [],
                 f'Hóa đơn lập {_d(dd, r["m"])}, {when} — đúng quy định mới. Duyệt.')


def c_whistle(rng, ctx):
    r = ctx['r']
    pick = rng.choice(['moc', 'hp'])
    sup = next(x for x in SUPPLIERS if x['id'] == pick)
    dd = rng.randrange(max(1, r['dom'] - 3), r['dom'] + 1)
    lines = _inv_lines(rng, sup)
    paper = _inv_paper(sup['name'], sup['mst'], f'1C26T{sup["abbr"]}', ctx['num'](rng), _d(dd, r['m']), lines, sup['vat'],
                       note='Mảnh giấy không tên kẹp trong hồ sơ: “Xưởng này của em rể trưởng phòng mua hàng. Giá cao gấp rưỡi chỗ khác. Kiểm tra đi.”')
    return _case('invoice', 'Chú Toàn · Thủ kho', 'Hàng nhận đủ. Mà có tờ giấy ai kẹp vào đây, chú không biết.', paper, 'whistle', 'escalate', ['note'],
                 'Hóa đơn đúng hình thức, nhưng có tố giác xung đột lợi ích. Không tự kết luận, không bỏ qua: trình sếp để kiểm tra giá.', 15,
                 'Ba tháng sau vụ nâng giá vỡ lở; hồ sơ có dấu duyệt của bạn dù đã có người cảnh báo.')


def c_oral(rng, ctx):
    r = ctx['r']
    name, bank, sup = _payee(rng, ctx)
    amount = r['limit'] + rng.randrange(10, 50) * 10
    paper = _req_paper(f'ĐNTT-{r["m"]:02d}{rng.randrange(10, 99)}', _d(r['dom'], r['m']), 'Bảo · Kinh doanh', name, bank,
                       [(f'Thanh toán gấp {sup["item"].lower()}', amount)], 'Chuyển khoản', 'Hóa đơn GTGT', _signs(ktt='—'),
                       note='Anh Tùng OK qua điện thoại rồi nha, chuyển gấp trước 5 giờ giúp em!!! — Bảo')
    return _case('payreq', 'Bảo · Kinh doanh', 'Sếp duyệt miệng rồi mà, chị Hạnh đi vắng thì mình chuyển trước!', paper, 'oral', 'escalate', ['sign', 'note', 'amount'],
                 'Duyệt miệng không phải chữ ký; lại vượt hạn mức. Trình sếp khi có chữ ký thật — không chi theo lời kể.', 15,
                 'Anh Tùng nói chưa hề đồng ý khoản này; bạn phải đòi lại tiền từ nhà cung cấp.')


CASES = [  # kind, builder, min_day, weight
    ('ok_inv', c_ok_inv, 1), ('ok_req', c_ok_req, 1), ('dup', c_dup, 1), ('nosign', c_nosign, 1), ('fake_mst', c_fake_mst, 1),
    ('math', c_math, 2), ('personal', c_personal, 2), ('limit', c_limit, 2), ('badsign', c_badsign, 3), ('noattach', c_noattach, 3),
    ('cash', c_cash, 3), ('blocked', c_blocked, 3), ('phish', c_phish, 4), ('split', c_split, 4), ('vat', c_vat, 4),
    ('backdate', c_backdate, 5), ('whistle', c_whistle, 5), ('oral', c_oral, 3),
]
CASE_KINDS = [k for k, _, _ in CASES] + ['vat_ok']
GOOD_KINDS = ('ok_inv', 'ok_req')


def desk_size(day: int, mod_id: str) -> int:
    n = 3 if day <= 2 else 4 if day <= 5 else 5 if day <= 9 else 6
    return n + (1 if mod_id in ('crunch', 'rush', 'intern') else 0)


def g_desk(rng, day, slot):
    r = _rules_raw(day)
    mod = _mod(day)
    m, dom = r['m'], r['dom']
    book = []
    used = set()

    def num(g):
        while True:
            v = f'{g.randrange(150, 990):07d}'
            if v not in used:
                used.add(v)
                return v
    ctx = dict(r=r, book=book, num=num)
    builders = {k: (f, lo) for k, f, lo in CASES}
    n = desk_size(day, mod['id'])
    # Bad kinds unlocked by the day; the rules of the month decide a few.
    bad = [k for k, _, lo in CASES if lo <= day and k not in GOOD_KINDS and k != 'oral'
           and (k != 'vat' or (r['vat_cut'] and r['phase'] >= 2)) and (k != 'split' or r['split']) and (k != 'cash' or r['cash'])]
    must = []
    if mod['id'] == 'boss_away':
        must.append('oral')
    if mod['id'] == 'intern':
        must.append('math')
    goods = 1 if n <= 4 else 2
    rest = [k for k in bad if k not in must]
    rng.shuffle(rest)
    picks = list(must)
    slots = n - goods
    for k in rest:
        need_slots = 2 if k == 'split' else 1
        if sum(2 if x == 'split' else 1 for x in picks) + need_slots <= slots:
            picks.append(k)
    good_kinds = [rng.choice(GOOD_KINDS) for _ in range(goods)]
    if r['vat_cut'] and r['phase'] >= 2 and day >= 4 and 'vat' in picks and rng.random() < .6:
        good_kinds[0] = 'vat_ok'
    cases = []
    for k in picks + good_kinds:
        if k == 'vat_ok':
            built = c_vat(rng, ctx, wrong=False)
        else:
            built = builders[k][0](rng, ctx)
        cases += built if isinstance(built, list) else [built]
    rng.shuffle(cases)
    for i, x in enumerate(cases):
        x['id'] = f'c{i + 1}'
        zones = [row['z'] for row in x['paper']['rows'] + x['paper']['foot'] if row['z']]
        if x['paper'].get('table'):
            zones.append(x['paper']['table']['z'])
        if x['paper'].get('note'):
            zones.append('note')
        x['zones'] = list(dict.fromkeys(zones))
    # Reference binder: supplier register, invoices already booked, who may sign.
    blk = next(x for x in EXTRA_SUP if x['id'] == r['blocked'])
    reg = [[s['name'], _mst(s['mst']), BANKS[s['id']], 'Đang giao dịch'] for s in SUPPLIERS]
    reg += [[s['name'], _mst(s['mst']), s['bank'], f'Ngừng hoạt động từ 01/{m:02d}' if s is blk else 'Đang giao dịch'] for s in EXTRA_SUP]
    reg += [[u['name'], _mst(u['mst']), u['bank'], 'Đang giao dịch'] for u in UTILITIES]
    others = [x for x in SUPPLIERS]
    for i in range(3):
        o = others[(day + i * 2) % len(others)]
        book.append([_d(max(1, dom - 5 - i), m), f'1C26T{o["abbr"]}-{rng.randrange(100, 990):07d}', o['name'], _n(rng.randrange(20, 90) * 20), 'Đã ghi sổ'])
    book.sort(key=lambda row: row[0])
    docs = [
        _doc('reg', 'table', 'Danh bạ nhà cung cấp', 'Phần mềm kế toán', cols=['Đơn vị', 'MST', 'Tài khoản nhận', 'Tình trạng'], rows=reg),
        _doc('book', 'table', f'Sổ hóa đơn đã ghi · tháng {m}', 'Phần mềm kế toán', cols=['Ngày', 'Ký hiệu – Số', 'Đơn vị bán', 'Tổng tiền', 'Tình trạng'], rows=book),
        _doc('sig', 'table', 'Mẫu chữ ký & thẩm quyền', 'Chị Hạnh', cols=['Người', 'Chức vụ', 'Được ký duyệt chi'],
             rows=[['Tùng', 'Giám đốc', 'Mọi khoản chi'], ['Hạnh', 'Kế toán trưởng', f'Tới {_n(r["limit"])} xu'],
                   ['Lụa', 'Thủ quỹ', 'Không (chỉ ký nhận/chi tiền)'], ['Bảo', 'Kinh doanh', 'Không (chỉ ký đề nghị)'],
                   ['Toàn', 'Thủ kho', 'Không (chỉ ký đề nghị)'], ['Na', 'Thực tập sinh', 'Không']]),
    ]
    bad_n = sum(1 for x in cases if x['_truth']['v'] != 'approve')
    title = f'Khay chứng từ ngày {_d(dom, m)}' + (f' · đợt {slot + 1}' if slot >= 2 else '')
    opening = {'boss_away': f'Chị đi công tác, khay có {len(cases)} bộ. Việc nào vượt quyền thì để chị về ký — đừng chi theo lời kể nhé.',
               'audit': f'Chiều nay anh Khải rút mẫu đấy. {len(cases)} bộ chứng từ, soi kỹ từng dấu.',
               'crunch': f'Ngày khóa sổ, khay dày {len(cases)} bộ. Nhanh mà chắc nhé em.',
               'intern': f'Na lập giúp mấy phiếu chi nháp. Khay có {len(cases)} bộ, em soát giúp chị.'}.get(
        mod['id'], f'Khay hôm nay có {len(cases)} bộ chứng từ. Soi theo quy định tháng này rồi đóng dấu từng bộ nhé.')
    return dict(npc=0, title=title, opening=opening,
                brief='Soi từng bộ chứng từ theo quy định đang áp dụng rồi đóng dấu: DUYỆT, TRẢ LẠI hoặc TRÌNH SẾP. Trả lại hay trình thì khoanh chỗ làm căn cứ trước.',
                docs=docs, cases=cases, handover=f'Khay {_d(dom, m)}: {len(cases)} bộ, {bad_n} bộ có vấn đề.')


# ---------------------------------------------------------------- task factory
def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        kind = _legacy_kind(day, slot)
        g = GENERATORS[kind](kit.rng(ID, day, slot, kind), day, slot)
        return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], variant=kind, brief=g['brief'], docs=g['docs'],
                             proc=g['steps'], proc_state=procedures.initial_state(), tips=[], handover=None,
                             _handover=g['handover'], _value=int(g.get('value', 0)))
    kind = _kind(day, slot)
    rng = kit.rng(ID, day, slot, kind)
    if kind == 'desk':
        g = g_desk(rng, day, slot)
        return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], variant='desk', brief=g['brief'], docs=g['docs'],
                             proc=[], proc_state=procedures.initial_state(), tips=[], handover=None, _handover=g['handover'],
                             _value=len(g['cases']), cases=g['cases'], circles={}, stamps={}, results={}, gen=GEN)
    g = GENERATORS[kind](rng, day, slot)
    return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], variant=kind, brief=g['brief'], docs=g['docs'],
                         proc=g['steps'], proc_state=procedures.initial_state(), tips=[], handover=None,
                         _handover=g['handover'], _value=int(g.get('value', 0)), gen=GEN)


def initial() -> dict:
    return dict(ledger={}, entries=[], milestones=[], posted=0, closes=0, rejected=0, done=0, day_posted=0, day_done=0,
                office=office.initial(), stamps=0, catches=0, slips=0, desks=0, day_stamps=[])


def _data(c: dict) -> dict:
    """Career data with every field of this version (older saves get the new ones here)."""
    d = kit.data(c)
    for k, v in initial().items():
        if k not in d:
            d[k] = copy.deepcopy(v)
    office.ensure(d)
    _care(c, d)
    return d


# ---------------------------------------------------------------- actions
def _current(t: dict) -> dict | None:
    at = t['proc_state']['at']
    return t['proc'][at] if at < len(t['proc']) else None


def _totals(rows) -> tuple[dict, dict]:
    deb, cre = {}, {}
    for d, c, a in rows:
        deb[d] = deb.get(d, 0) + a
        cre[c] = cre.get(c, 0) + a
    return deb, cre


def _entry_answer(st: dict, answer) -> tuple[list, str]:
    """Accept pairs [{debit, credit, amount}] or a compound voucher {debit:[{account, amount}], credit:[…]}.
    Returns the canonical answer (the key itself) when every account gets the right debit/credit
    totals, otherwise a well-formed wrong answer plus a diagnostic that never reveals the key."""
    accts = {a['id'] for a in st['accounts']}
    bad = 'Mỗi dòng cần một tài khoản trong danh mục và số tiền nguyên dương.'
    deb, cre = {}, {}
    if isinstance(answer, dict):
        rows_d, rows_c = answer.get('debit'), answer.get('credit')
        kit.need(isinstance(rows_d, list) and isinstance(rows_c, list) and 1 <= len(rows_d) <= 6 and 1 <= len(rows_c) <= 6,
                 'Chứng từ cần ít nhất 1 dòng Nợ và 1 dòng Có (tối đa 6 dòng mỗi bên).')
        for rows, side in ((rows_d, deb), (rows_c, cre)):
            for r in rows:
                kit.need(isinstance(r, dict) and r.get('account') in accts and type(r.get('amount')) is int and 0 < r['amount'] <= 10**8, bad)
                side[r['account']] = side.get(r['account'], 0) + r['amount']
    else:
        kit.need(isinstance(answer, list) and 1 <= len(answer) <= 8, 'Bút toán có từ 1 đến 8 dòng.')
        for r in answer:
            kit.need(isinstance(r, dict) and r.get('debit') in accts and r.get('credit') in accts and r['debit'] != r['credit']
                     and type(r.get('amount')) is int and 0 < r['amount'] <= 10**8, bad)
            deb[r['debit']] = deb.get(r['debit'], 0) + r['amount']
            cre[r['credit']] = cre.get(r['credit'], 0) + r['amount']
    td, tc = sum(deb.values()), sum(cre.values())
    kit.need(td == tc, f'Chứng từ chưa cân: Tổng Nợ {_n(td)} ≠ Tổng Có {_n(tc)}. Phần mềm không cho lưu bút toán lệch.')
    kd, kc = _totals(st['_key'])
    if deb == kd and cre == kc:
        return [dict(debit=d, credit=c, amount=a) for d, c, a in st['_key']], ''
    if set(deb) == set(kd) and set(cre) == set(kc):
        diag = 'Tài khoản đã đúng, nhưng số tiền chưa khớp chứng từ.'
    elif set(deb) == set(kd):
        diag = 'Bên Nợ chọn đúng tài khoản; xem lại tài khoản bên Có.'
    elif set(cre) == set(kc):
        diag = 'Bên Có chọn đúng tài khoản; xem lại tài khoản bên Nợ.'
    elif td == sum(kd.values()):
        diag = 'Tổng số tiền đúng rồi; xem lại tài khoản ghi Nợ và ghi Có.'
    else:
        diag = ''
    ids = [a['id'] for a in st['accounts']]
    wrong = [dict(debit=ids[0], credit=ids[1], amount=1)]
    if procedures.check(st, wrong):
        wrong[0]['amount'] = 2
    return wrong, diag


def _post(c: dict, t: dict, st: dict) -> None:
    d = kit.data(c)
    led = d['ledger']
    for dr, cr, a in st['_key']:
        led[dr] = led.get(dr, 0) + a
        led[cr] = led.get(cr, 0) - a
    d['ledger'] = {k: v for k, v in led.items() if v}
    d['entries'] = ar.last(d['entries'] + [dict(day=c['day'], task=t['id'], title=st['title'], lines=[list(x) for x in st['_key']])], 12, 'office.entries', c)
    d['posted'] += 1
    d['day_posted'] += 1


def _close_ledger(d: dict) -> int:
    """Close the running ledger's revenue/expense accounts through 911 into 421. Returns profit."""
    led = d['ledger']
    net = sum(led.pop(a, 0) for a in PL_ACCOUNTS)
    if net:
        led['421'] = led.get('421', 0) + net
    d['ledger'] = {k: v for k, v in led.items() if v}
    return -net


DESK_HINTS = dict(
    ok_inv='So MST với danh bạ, tra sổ đã ghi, xem chữ ký số và phép cộng.', ok_req='So số tiền với hạn mức, xem ai đã ký và tài khoản nhận.',
    dup='Tra “Sổ hóa đơn đã ghi”: số hóa đơn này đã xuất hiện chưa?', fake_mst='Đối chiếu từng chữ số MST với “Danh bạ nhà cung cấp”.',
    nosign='Nhìn dòng chữ ký số ở cuối hóa đơn.', math='Tự cộng lại các dòng xem có ra đúng tổng không.',
    personal='Đọc từng dòng chi: khoản nào không phục vụ công việc?', limit='So số tiền với thẻ “Hạn mức ký duyệt”, rồi xem ai đã ký.',
    badsign='Tra “Mẫu chữ ký”: người ký duyệt có thẩm quyền không?', noattach='Đề nghị chi cần chứng từ gốc kèm theo.',
    cash='Xem hình thức thanh toán và thẻ “Chi từ 200 xu”.', blocked='Đọc thẻ “Ngừng giao dịch” và cột tình trạng trong danh bạ.',
    phish='Soi địa chỉ người gửi và so tài khoản với danh bạ.', split='Có tờ nào khác cùng người nhận, cùng ngày không? Cộng lại thử.',
    vat='Ngày lập hóa đơn là trước hay sau mốc đổi thuế suất?', vat_ok='Ngày lập hóa đơn là trước hay sau mốc đổi thuế suất?',
    backdate='So ngày giao hàng với ngày ghi trên hóa đơn và thẻ “Sổ đã khóa”.', whistle='Hóa đơn đúng hình thức — còn tờ giấy kẹp kèm thì sao?',
    oral='Lời kể “sếp OK rồi” có thay được chữ ký không? So số tiền với hạn mức.')
RESULTS = ('ok', 'reason', 'wrong')


def _find_case(t: dict, cid) -> dict:
    case = next((x for x in t.get('cases') or [] if x['id'] == cid), None)
    kit.need(case, 'Khay không có bộ chứng từ này.')
    return case


def _circle(o: dict, t: dict, p: dict) -> dict:
    kit.need(t.get('variant') == 'desk', 'Hồ sơ này không có khay chứng từ.')
    case = _find_case(t, p.get('case'))
    kit.need(case['id'] not in t['stamps'], 'Bộ này đã đóng dấu, không khoanh thêm được.')
    zone = kit.one_of(p.get('zone'), case['zones'], 'Chỗ này không có trên chứng từ.')
    marks = t['circles'].setdefault(case['id'], [])
    if zone in marks:
        marks.remove(zone)
        if not marks:
            t['circles'].pop(case['id'])
        return dict(message='', circled=False)
    kit.need(len(marks) < MAX_CIRCLES, f'Khoanh tối đa {MAX_CIRCLES} chỗ — bỏ bớt một chỗ trước nhé.')
    office.spend(o, office.COST['circle'])
    marks.append(zone)
    kit.start_work(t)
    return dict(message='', circled=True)


def _stamp(s: dict, c: dict, d: dict, o: dict, t: dict, p: dict) -> dict:
    kit.need(t.get('variant') == 'desk', 'Hồ sơ này không có khay chứng từ.')
    case = _find_case(t, p.get('case'))
    kit.need(case['id'] not in t['stamps'], 'Bộ chứng từ này đã đóng dấu rồi.')
    verdict = kit.one_of(p.get('verdict'), VERDICTS, 'Chọn một con dấu: DUYỆT, TRÌNH SẾP hoặc TRẢ LẠI.')
    marks = t['circles'].get(case['id'], [])
    if verdict != 'approve':
        kit.need(marks, 'Khoanh ít nhất một chỗ làm căn cứ trước khi trả lại hoặc trình sếp.')
    lunch = office.spend(o, office.COST['stamp'])
    kit.start_work(t)
    truth = case['_truth']
    bad = truth['v'] != 'approve'
    t['stamps'][case['id']] = verdict
    d['stamps'] += 1
    if verdict == truth['v']:
        if bad and not set(marks) & set(truth['z']):
            result = 'reason'
            t['mistakes'] += 1
            msg = f'Đúng dấu {VERDICT_LABEL[verdict]}, nhưng chỗ khoanh chưa phải căn cứ. {truth["why"]}'
        else:
            result = 'ok'
            if bad:
                d['catches'] += 1
                office.trust(o, 1)
                kit.metric(c, 'ca_catches')
            msg = '✓ ' + truth['why']
    else:
        result = 'wrong'
        t['mistakes'] += 1
        if verdict == 'approve':
            d['slips'] += 1
            office.trust(o, -4)
            paid = office.fine(s, c, o, truth['fine'], 'Trừ thưởng: duyệt nhầm chứng từ', t['id'])
            msg = f'✗ Duyệt nhầm. {truth["oops"]}' + (f' Bạn bị trừ {paid} xu.' if paid else '') + f' {truth["why"]}'
            office.note(o, c['day'], f'Duyệt nhầm một bộ chứng từ (−{paid} xu).', 'fine')
        elif not bad:
            office.trust(o, -2)
            msg = f'✗ Bộ này hợp lệ — trả oan làm người nộp phải chạy lại từ đầu. {truth["why"]}'
        else:
            office.trust(o, -1)
            msg = f'✗ Cần {VERDICT_LABEL[truth["v"]]}, không phải {VERDICT_LABEL[verdict]}. {truth["why"]}'
    t['results'][case['id']] = result
    d['day_stamps'] = ar.last(d['day_stamps'] + [dict(task=t['id'], case=case['id'], ok=result == 'ok', slip=result == 'wrong' and verdict == 'approve')], 40, 'office.stamps', c)
    left = sum(1 for x in t['cases'] if x['id'] not in t['stamps'])
    tail = f'Còn {left} bộ.' if left else ''
    return dict(message=' '.join(x for x in (msg, lunch, tail) if x), correct=result == 'ok', result=result, stamp=verdict)


def _desk_slips(t: dict) -> None:
    """Wrong stamps in a handed-in tray, as chị Hạnh will bring them up (the fine at the stamp stays)."""
    for x in t['cases']:
        if t['results'].get(x['id']) != 'wrong':
            continue
        tr, v = x['_truth'], t['stamps'][x['id']]
        if v == 'approve':
            text = tr['oops'] or 'Em duyệt một bộ chứng từ có vấn đề, chị phải gọi thu hồi lại.'
            cq.slip(t, f'approve_{x["id"]}', 3 if tr['fine'] >= 25 else 2, text, 'duyệt nhầm chứng từ có vấn đề')
        elif tr['v'] == 'approve':
            cq.slip(t, f'reject_{x["id"]}', 1, 'Bộ chứng từ hợp lệ bị trả lại, người nộp phải chạy lại từ đầu.', 'trả lại chứng từ hợp lệ')
        else:
            cq.slip(t, f'route_{x["id"]}', 1, 'Bộ chứng từ có vấn đề mà đóng nhầm loại dấu, chị phải chuyển lại cho đúng chỗ.', 'đóng nhầm loại dấu')


def _finish(s: dict, c: dict, d: dict, o: dict, t: dict, base: int, extra: str = '') -> dict:
    lunch = office.spend(o, office.COST['submit'] + office.review_cost(o))
    late, adj, note = office.settle(o, t, c['day'], office.rookie(d))
    t['late'] = late
    info = KINDS[t['variant']]
    if info['milestone'] not in d['milestones']:
        d['milestones'].append(info['milestone'])
    plan = _close_tick(c, d['care'], t, info['milestone'])
    d['done'] += 1
    d['day_done'] += 1
    reward = max(0, base + adj)
    kit.metric(c, 'ca_dossiers')
    if t['mistakes'] == 0:
        kit.metric(c, 'ca_clean_dossiers')
    # Wrong stamps handed in: chị Hạnh takes it out of the bonus (and reports serious ones).
    reaction = cq.react(s, c, t, reward, who='Chị Hạnh')
    reward = reaction['pay']
    kit.complete(s, c, t, reward, f'Bạn đã hoàn tất hồ sơ “{t["title"]}”' + (' nhưng trễ hạn.' if late else '.'))
    parts = [f'Đã nộp hồ sơ · thưởng hiệu suất +{reward} xu.', note, extra, plan, reaction['message'], lunch]
    return dict(message=' '.join(x for x in parts if x), celebrate=not late and not cq.slips(t))


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    o = d['office']
    office.sync(o, c['day'])
    before = o['clock']
    res = care_handle(s, c, d, o, CARE, name, p)
    if res is None:
        res = _handle(s, c, name, p)
    slow = care_slow(d['care'], o, before)
    if slow:
        res['message'] = ' '.join(x for x in (res.get('message', ''), slow) if x)
    return res


def _handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    o = d['office']
    mod = _mod(c['day'])
    if name == 'ca_overtime':
        care_can_overtime(d['care'], CARE)
        kit.confirm(p, 'Xác nhận ở lại tăng ca tới 20:00.')
        return dict(message=office.overtime(s, c, o, 18 if mod['id'] == 'crunch' else 12, mod['id'] == 'crunch'))
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Hồ sơ không thuộc phòng kế toán Mây Tre Xanh.')
    kit.need(t['known'], 'Nhận hồ sơ trước đã (bấm “Nhận hồ sơ”).')
    desk = t.get('variant') == 'desk'
    if name == 'ca_open':
        doc = next((x for x in t['docs'] if x['id'] == p.get('doc')), None)
        kit.need(doc, 'Hồ sơ không có chứng từ này.')
        extra = ''
        if doc['id'] not in t['inspected']:
            cost = office.COST['ref' if desk else 'open'] * (2 if mod['id'] == 'lag' else 1)
            lunch = office.spend(o, cost)
            t['inspected'].append(doc['id'])
            extra = f' (+{cost} phút)' + (' ' + lunch if lunch else '')
        kit.start_work(t)
        return dict(message=f'Đã mở: {doc["title"]}.{extra}')
    if name == 'ca_hint':
        away = mod['id'] == 'boss_away'
        who = 'Chị Hạnh nhắn lại sau 15 phút: ' if away else 'Chị Hạnh gợi ý: '
        if desk:
            case = _find_case(t, p.get('case'))
            kit.need(case['id'] not in t['stamps'], 'Bộ này đã đóng dấu rồi.')
            office.spend(o, 15 if away else office.COST['hint'])
            if case['id'] not in t['tips']:
                t['tips'].append(case['id'])
            return dict(message=who + DESK_HINTS.get(case['_k'], 'Đối chiếu với quy định và sổ tra cứu.'))
        st = _current(t)
        kit.need(st, 'Hồ sơ đã xong mọi bước.')
        office.spend(o, 15 if away else office.COST['hint'])
        if st['id'] not in t['tips']:
            t['tips'].append(st['id'])
        return dict(message=who + (st.get('hints') or ['Đọc lại chứng từ gốc.'])[0])
    if name == 'ca_circle':
        return _circle(o, t, p)
    if name == 'ca_stamp':
        return _stamp(s, c, d, o, t, p)
    if name == 'ca_step':
        kit.need(not desk, 'Khay chứng từ dùng con dấu, không có bước tính.')
        st = _current(t)
        kit.need(st, 'Hồ sơ đã xong mọi bước. Chọn ghi chú bàn giao rồi nộp nhé.')
        kit.need(p.get('step') == st['id'], 'Làm theo thứ tự các bước của hồ sơ nhé.')
        missing = [x['title'] for x in t['docs'] if x['id'] in st.get('docs', []) and x['id'] not in t['inspected']]
        kit.need(not missing, 'Mở chứng từ trước khi kết luận: ' + ', '.join(missing) + '.')
        office.need_open(o)
        answer, diag = p.get('answer'), ''
        if st['kind'] == 'entry':
            answer, diag = _entry_answer(st, answer)
        kit.start_work(t)
        ok, msg = procedures.submit(t, st['id'], answer)
        lunch = office.spend(o, office.COST['step'] + (0 if ok else office.wrong_min(d)))
        if not ok:
            # Which boxes of a calculation are off (never their values): the client marks them.
            bad = [f['id'] for f in st['fields'] if answer.get(f['id']) != st['_key'][f['id']]] if st['kind'] == 'fields' else []
            return dict(message=' '.join(x for x in (diag, msg, lunch) if x), correct=False, bad=bad)
        if st['kind'] == 'entry' and st.get('post', True):
            _post(c, t, st)
        if procedures.done(t):
            msg += ' Đủ bước rồi — chọn ghi chú bàn giao và nộp hồ sơ.'
        return dict(message=' '.join(x for x in (msg, lunch) if x), correct=True)
    if name == 'ca_submit':
        if desk:
            left = [x['id'] for x in t['cases'] if x['id'] not in t['stamps']]
            kit.need(not left, f'Còn {len(left)} bộ chưa đóng dấu.')
            kit.confirm(p, 'Xác nhận chốt khay và nộp báo cáo cho chị Hạnh.')
            office.need_open(o)
            t['handover'] = 'specific'
            d['desks'] += 1
            wrong = sum(1 for v in t['results'].values() if v != 'ok')
            caught = sum(1 for x in t['cases'] if x['_truth']['v'] != 'approve' and t['results'].get(x['id']) == 'ok')
            bad = sum(1 for x in t['cases'] if x['_truth']['v'] != 'approve')
            _desk_slips(t)
            reasons = sum(1 for v in t['results'].values() if v == 'reason')
            return _finish(s, c, d, o, t, office.pay(30, reasons, office.rookie(d), slip=5), f'Bắt đúng {caught}/{bad} bộ có vấn đề' + (f', {wrong} dấu cần xem lại.' if wrong else ' — sạch khay!'))
        kit.need(procedures.done(t), 'Hồ sơ còn bước chưa làm xong.')
        note = kit.one_of(p.get('note'), HANDOVER, 'Chọn một ghi chú bàn giao.')
        kit.confirm(p, 'Xác nhận nộp hồ sơ cho người giao việc.')
        office.need_open(o)
        t['handover'] = note
        extra = ''
        if t['variant'] == 'invoice_in' and t['proc_state']['answers'].get('decision') != 'accept':
            d['rejected'] += 1
        if t['variant'] == 'month_close':
            profit = _close_ledger(d)
            d['closes'] += 1
            extra = f'Sổ cái của bạn cũng đã kết chuyển: kết quả {_n(profit)} xu vào 421.'
        m = t['mistakes']
        return _finish(s, c, d, o, t, office.pay(30, 0, False) if m == 0 else office.pay(24, m, office.rookie(d)), extra)
    raise kit.eng().GameError('Thao tác kế toán không hợp lệ.')


# ---------------------------------------------------------------- deadlines (feedback #265, #269 · 08/10)
# "3 hồ sơ không cái nào kịp dù không sai gì": deadlines went by the dossier's place in the day (10:30 · 12:00 · 15:00)
# whatever its length — a month-end close needs 145 office minutes even when every answer is right — and every
# leftover was due at 10:00 the next morning, so one unfinished day made the next ones late too. Now each dossier gets
# PACE times the office minutes a clean hand-in of it takes (room for a hint and a wrong try or two), rounded up to a
# quarter hour; the day's dossiers follow one another from the opening (leftovers first, lunch skipped), never earlier
# than the old time for that place in the day and never after 17:30. The crunch day stays 30 minutes earlier.
PACE = 2
QUARTER = 15
DONE = ('completed', 'referred', 'cancelled')


def clean_minutes(t: dict, lag: bool = False) -> int:
    """Office minutes a clean hand-in of what is left of this dossier takes (no hint, no wrong try)."""
    desk = t.get('variant') == 'desk'
    read = office.COST['ref' if desk else 'open'] * (2 if lag else 1)
    m = read * sum(1 for x in t.get('docs') or [] if x['id'] not in t.get('inspected', [])) + office.COST['submit']
    if desk:
        stamped = t.get('stamps') or {}
        for x in t.get('cases') or []:
            if x['id'] not in stamped:
                m += office.COST['stamp'] + (office.COST['circle'] if x['_truth']['v'] != 'approve' else 0)
    else:
        m += office.COST['step'] * max(0, len(t.get('proc') or []) - (t.get('proc_state') or {}).get('at', 0))
    return m


def allowance(t: dict, lag: bool = False) -> int:
    m = clean_minutes(t, lag) * PACE
    return -(-m // QUARTER) * QUARTER


def _after(clock: int, minutes: int) -> int:
    """The office clock `minutes` of work after `clock` (the lunch hour does not count, as in office.spend)."""
    end = clock + minutes
    return end + office.LUNCH_MIN if clock < office.LUNCH <= end else end


def _slot(t: dict) -> int:
    return int(str(t['id']).rsplit('-', 1)[-1])


def _queue(c: dict, day: int, extra: dict | None = None) -> list:
    """Open dossiers in the order they are worked: leftovers first, then today's by arrival."""
    rows = [t for t in c['tasks'] if t.get('career') == ID and t['status'] not in DONE and t['day'] <= day
            and (t.get('gen') or type(t.get('due')) is int)]
    if extra is not None and all(x is not extra for x in rows):
        rows.append(extra)
    return sorted(rows, key=lambda t: (t['day'], _slot(t)))


def _day_start(o: dict, day: int) -> int:
    return office.OPEN + (office.TIRED_MIN if o['tired'] == day else 0)


def plan_dues(rows: list, day: int, start: int) -> list:
    """Deadlines of `rows` (in working order) for a day whose work starts at `start`."""
    mod = _mod(day)['id']
    clock, out = start, []
    for i, t in enumerate(rows):
        clock = _after(clock, allowance(t, mod == 'lag'))
        due = min(office.CLOSE, max(office.DUE[i] if i < len(office.DUE) else office.CLOSE, clock))
        out.append(max(office.OPEN + 60, due - 30) if mod == 'crunch' else due)
    return out


def plan_day(c: dict, o: dict) -> None:
    """Spread the deadlines of every open dossier over the day (at the start of the day, before any work)."""
    day = c['day']
    rows = _queue(c, day)
    for t, due in zip(rows, plan_dues(rows, day, _day_start(o, day))):
        t['due'], t['due_day'] = due, day


def on_task(s: dict, c: dict, t: dict) -> None:
    if not t.get('gen'):
        return
    o = _data(c)['office']
    day = c['day']
    office.sync(o, day)
    lag = _mod(day)['id'] == 'lag'
    if o['day'] == day and c.get('open') and o['clock'] > office.OPEN + office.TIRED_MIN:
        # Taken mid-day: 2.5 hours later as before, or the time its own work needs when that is longer.
        office.set_due(c, t, o)
        t['due'] = max(t['due'], min(office.LOCK, _after(o['clock'], allowance(t, lag))))
        if _mod(t['day'])['id'] == 'crunch':
            t['due'] = max(office.OPEN + 60, t['due'] - 30)
        return
    # Early in the day: planned after the dossiers before it; the ones already planned keep their deadlines,
    # so it also starts no earlier than the last of those is due.
    rows = _queue(c, day, t)
    i = next(k for k, x in enumerate(rows) if x is t)
    due = plan_dues(rows[:i + 1], day, _day_start(o, day))[-1]
    planned = [x['due'] for x in rows[:i] if x.get('due_day') == day and type(x.get('due')) is int]
    if planned:
        due = max(due, min(office.CLOSE, _after(max(planned), allowance(t, lag))))
    t['due'], t['due_day'] = due, day


def carry_due(c: dict, o: dict) -> str | None:
    """At the close: when tomorrow's first leftover will be due (the day summary says it), or None."""
    rows = _queue(c, c['day'])
    if not rows:
        return None
    day = c['day'] + 1
    return office.hhmm(plan_dues(rows[:1], day, _day_start(o, day))[0])


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    o = d['office']
    mod = _mod(c['day'])
    office.begin(o, c['day'])
    office.carry(c, ID, o)
    plan_day(c, o)
    d['day_stamps'] = []
    care_start(d['care'], CARE, c['day'])
    _close_plan(d['care'], c['day'])
    if mod['id'] != 'normal':
        kit.log(s, c, 'surprise', f'{mod["emoji"]} Hôm nay: {mod["name"]}. {mod["text"]}', kit.npc_id(ID, 0))


# ---------------------------------------------------------------- views & validation
def _strip(v):
    if isinstance(v, dict):
        return {k: _strip(x) for k, x in v.items() if not k.startswith('_')}
    if isinstance(v, list):
        return [_strip(x) for x in v]
    return v


def _public_desk(t: dict, v: dict) -> dict:
    stamps, results = t.get('stamps') or {}, t.get('results') or {}
    rows = []
    for x, row in zip(t['cases'], v['cases']):  # v['cases']: strip_copy of each case, made by public_task
        row['circles'] = list((t.get('circles') or {}).get(x['id'], []))
        row['stamp'] = stamps.get(x['id'])
        row['hinted'] = x['id'] in t['tips']
        row['tip'] = DESK_HINTS.get(x['_k']) if row['hinted'] else None
        if row['stamp']:
            tr = x['_truth']
            row.update(result=results.get(x['id']), truth=dict(v=tr['v'], z=list(tr['z']), why=tr['why']))
        rows.append(row)
    v['cases'] = rows
    v['tray'] = dict(total=len(rows), stamped=len(stamps), ok=sum(1 for r in results.values() if r == 'ok'),
                     ready=len(stamps) == len(rows))
    v['handover_options'] = None
    return v


def public_task(t: dict) -> dict:
    # strip_copy(t), except what is replaced below (None keeps its place in the key order)
    skip = ('docs', 'proc', 'proc_state', 'circles', 'results') + (('cases',) if not t['known'] else ())
    v = {k: (None if k in skip else strip_copy(val)) for k, val in t.items() if not k.startswith('_')}
    v['kind_info'] = dict(KINDS[t['variant']])
    v.pop('circles', None)
    v.pop('results', None)
    if not t['known']:
        v.update(docs=None, proc=None, proc_state=None, brief=None, cases=None)
        return v
    v['docs'] = [strip_copy(x) if x['id'] in t['inspected'] else dict(id=x['id'], type=x['type'], title=x['title'], source=x['source'], closed=True)
                 for x in t['docs']]
    if t.get('variant') == 'desk':
        v.update(proc=[], proc_state=None)
        return _public_desk(t, v)
    steps, state = procedures.public(t)
    rows = []
    for st in steps:
        st.pop('hints', None)
        # Requested tips come from the original step (public hints unlock per mistake).
        hints = next((x.get('hints') or [] for x in t['proc'] if x['id'] == st['id']), [])
        if st['state'] == 'locked':
            rows.append(dict(id=st['id'], kind=st['kind'], title=st['title'], state='locked'))
            continue
        st['tip'] = hints[0] if st['id'] in t['tips'] and hints else None
        rows.append(st)
    v['proc'] = rows
    v['proc_state'] = state
    v['handover_options'] = ([dict(id='specific', label=t['_handover']), dict(id='short', label='“Em xong hồ sơ rồi ạ.”'),
                              dict(id='none', label='Không để lại ghi chú')] if procedures.done(t) else None)
    return v


def _validate_desk(t: dict) -> None:
    cases = {x['id']: x for x in t['cases']}
    kit.need(isinstance(t.get('circles'), dict) and isinstance(t.get('stamps'), dict) and isinstance(t.get('results'), dict), 'Khay chứng từ thiếu dữ liệu.')
    for cid, marks in t['circles'].items():
        kit.need(cid in cases and isinstance(marks, list) and 1 <= len(marks) <= MAX_CIRCLES and len(set(marks)) == len(marks)
                 and all(z in cases[cid]['zones'] for z in marks), 'Chỗ khoanh trên chứng từ sai.')
    kit.need(set(t['results']) == set(t['stamps']) and set(t['stamps']) <= set(cases), 'Dấu trên khay chứng từ sai.')
    for cid, verdict in t['stamps'].items():
        kit.need(verdict in VERDICTS and t['results'][cid] in RESULTS, 'Dấu trên khay chứng từ sai.')
        tr = cases[cid]['_truth']
        if verdict == tr['v']:
            kit.need(t['results'][cid] != 'wrong', 'Kết quả đóng dấu sai.')
            if t['results'][cid] == 'ok' and tr['v'] != 'approve':
                kit.need(set(t['circles'].get(cid, [])) & set(tr['z']), 'Kết quả đóng dấu sai.')
        else:
            kit.need(t['results'][cid] == 'wrong', 'Kết quả đóng dấu sai.')
    kit.need(isinstance(t['inspected'], list) and len(set(t['inspected'])) == len(t['inspected'])
             and all(x in [d['id'] for d in t['docs']] for x in t['inspected']), 'Danh sách sổ tra cứu đã mở sai.')
    kit.need(isinstance(t.get('tips'), list) and len(set(t['tips'])) == len(t['tips']) and all(x in cases for x in t['tips']), 'Gợi ý đã xem sai.')
    kit.need(t.get('handover') in (None, 'specific'), 'Báo cáo khay sai.')
    kit.need(t.get('late') in (None, True, False), 'Cờ trễ hạn sai.')
    if t['status'] == 'completed':
        kit.need(len(t['stamps']) == len(cases) and t['handover'] == 'specific', 'Khay chốt khi chưa đóng dấu đủ.')


def validate_task(t: dict, original: dict) -> None:
    office.validate_task(t)
    care_validate_task(t, CARE)
    if t.get('variant') == 'desk':
        _validate_desk(t)
        return
    procedures.validate(t, original)
    ids = [x['id'] for x in t['docs']]
    kit.need(isinstance(t['inspected'], list) and len(set(t['inspected'])) == len(t['inspected']) and all(x in ids for x in t['inspected']),
             'Danh sách chứng từ đã mở sai.')
    steps = [st['id'] for st in t['proc']]
    kit.need(isinstance(t.get('tips'), list) and len(set(t['tips'])) == len(t['tips']) and all(x in steps for x in t['tips']), 'Gợi ý đã xem sai.')
    kit.need(t.get('handover') in (None, *HANDOVER), 'Ghi chú bàn giao sai.')
    kit.need(t.get('late') in (None, True, False), 'Cờ trễ hạn sai.')
    if t['status'] == 'completed':
        kit.need(procedures.done(t) and t['handover'], 'Hồ sơ hoàn tất nhưng chưa đủ bước.')


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.mark_legacy(c, ID)
    kit.need(set(initial()) <= set(d), 'Sổ kế toán thiếu dữ liệu.')
    led = d['ledger']
    kit.need(isinstance(led, dict) and all(k in ACCOUNT_NAME for k in led), 'Sổ cái có tài khoản lạ.')
    for v in led.values():
        kit.integer(v, -10**10, 10**10)
    kit.need(sum(led.values()) == 0, 'Sổ cái không cân: tổng Nợ khác tổng Có.')
    kit.need(isinstance(d['entries'], list) and len(d['entries']) <= 12, 'Nhật ký bút toán sai.')
    for e in d['entries']:
        kit.need(isinstance(e, dict) and isinstance(e.get('lines'), list) and 1 <= len(e['lines']) <= 8, 'Bút toán lưu sai.')
        kit.integer(e.get('day'), 1, 10**7)
        kit.text(e.get('task'), 80)
        kit.text(e.get('title'), 120)
        for row in e['lines']:
            kit.need(isinstance(row, list) and len(row) == 3 and row[0] in ACCOUNT_NAME and row[1] in ACCOUNT_NAME, 'Dòng bút toán sai.')
            kit.integer(row[2], 1, 10**9)
    kit.need(isinstance(d['milestones'], list) and len(set(d['milestones'])) == len(d['milestones']) and all(x in MILESTONE_IDS for x in d['milestones']),
             'Tiến độ khóa sổ sai.')
    for k in ('posted', 'closes', 'rejected', 'done', 'day_posted', 'day_done', 'stamps', 'catches', 'slips', 'desks'):
        kit.integer(d.get(k), 0, 10**9)
    office.validate(d['office'])
    care_validate(d['care'], CARE)
    _validate_close(d['care'])
    kit.need(isinstance(d['day_stamps'], list) and len(d['day_stamps']) <= 40, 'Sổ đóng dấu trong ngày sai.')
    for x in d['day_stamps']:
        kit.need(isinstance(x, dict) and set(x) == {'task', 'case', 'ok', 'slip'} and type(x['ok']) is bool and type(x['slip']) is bool, 'Sổ đóng dấu trong ngày sai.')
        kit.text(x['task'], 80)
        kit.text(x['case'], 20)


def public_data(c: dict) -> dict:
    d = tree_copy(kit.data(c))
    for k, v in initial().items():
        d.setdefault(k, tree_copy(v))
    o = office.ensure(d)
    m, phase, dom = _period(c['day'])
    d['period'] = dict(month=m, phase=phase, date=_d(dom, m), label=['Đầu tháng', 'Giữa tháng', 'Kiểm kê', 'Chuẩn bị khóa sổ', 'Ngày khóa sổ'][phase])
    d['balanced'] = sum(d['ledger'].values()) == 0
    mod = _mod(c['day'])
    d['today'] = dict(mod=dict(id=mod['id'], emoji=mod['emoji'], name=mod['name'], text=mod['text']), rules=rules(c['day']),
                      limit=_rules_raw(c['day'])['limit'])
    d['office'] = office.public(o, c['day'])
    d['milestone_names'] = [n for i, n in MILESTONES if i in d['milestones']]
    d.pop('day_stamps', None)
    cr = _care(c, d)
    view = care_public(cr, CARE, c, o)
    view.update(calendar=_calendar(c, cr), plan=_plan_view(c, cr))
    d['care'] = view
    d['coach'] = office.coach(c, ID, _coach)
    return d


def _coach(t: dict) -> dict | None:
    """First dossier only (office.coach): the right stamp and a zone that justifies it, or the step's key."""
    if t.get('variant') == 'desk':
        return dict(cases={x['id']: dict(v=x['_truth']['v'], z=list(x['_truth']['z'])) for x in t['cases'] if x['id'] not in t['stamps']})
    return office.coach_step(t)


def known_request(c: dict, t: dict) -> str:
    if t.get('variant') == 'desk':
        return f'Khay có {len(t["cases"])} bộ chứng từ — soi từng bộ rồi đóng dấu.'
    return f'Hồ sơ có {len(t["docs"])} chứng từ — làm lần lượt từng bước.'


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    o = d['office']
    office.sync(o, c['day'])
    mod = _mod(c['day'])
    stamps = d['day_stamps']
    out = dict(posted=d['day_posted'], dossiers=d['day_done'], milestones=[n for i, n in MILESTONES if i in d['milestones']],
               balanced=sum(d['ledger'].values()) == 0, mod=dict(emoji=mod['emoji'], name=mod['name']),
               desk=dict(stamped=len(stamps), ok=sum(1 for x in stamps if x['ok']), slips=sum(1 for x in stamps if x['slip'])))
    if mod['id'] == 'audit' and stamps:
        slips = sum(1 for x in stamps if x['slip'])
        if slips:
            paid = office.fine(s, c, o, 10 * slips, 'Kiểm toán rút mẫu: chứng từ duyệt sai')
            office.trust(o, -3 * min(3, slips))
            out['audit'] = dict(ok=False, amount=paid, text=f'Anh Khải rút mẫu, tìm ra {slips} bộ duyệt sai. Trừ thêm {paid} xu, chị Hạnh buồn ra mặt.')
        else:
            kit.money(s, c, 10, 'Thưởng: kiểm toán rút mẫu không thấy sai sót', None, 'audit_bonus')
            office.trust(o, 3)
            kit.review(s, c, kit.npc_id(ID, 4), 5, 'Rút mẫu chứng từ hôm nay: không có con dấu nào sai. Làm việc có căn cứ.', f'audit-{c["day"]}')
            out['audit'] = dict(ok=True, amount=10, text='Anh Khải rút mẫu cả khay: không có dấu nào sai. Thưởng 10 xu, chị Hạnh cười tít mắt.')
    ok, why = _reliable(d, o)
    close = _close_grade(s, c, d['care'], o)
    if close:
        out['close'] = close
    out['office'] = office.close_day(c, ID, o)
    first = carry_due(c, o)
    if first:
        out['office']['carry_due'] = first
    out['care'] = care_close(s, c, d['care'], CARE, o, ok, why)
    d['day_posted'] = 0
    d['day_done'] = 0
    d['day_stamps'] = []
    if c['day'] % 5 == 0:
        out['month_done'] = len(d['milestones'])
        d['milestones'] = []
    return out


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if not t or t['career'] != ID or not t['known']:
        return None
    if e['role'] == 'ca_filing':
        doc = next((x for x in t['docs'] if x['id'] not in t['inspected']), None)
        if doc:
            t['inspected'].append(doc['id'])
            return f'Đã rút “{doc["title"]}” ra bàn. Kết luận vẫn là của bạn.'
        return 'Đã kẹp chứng từ theo số thứ tự và dán nhãn tháng.'
    if e['role'] == 'ca_checker':
        if t.get('variant') == 'desk':
            return 'Nhắc nhỏ: trả lại hay trình sếp thì khoanh đúng chỗ làm căn cứ — đừng đóng dấu theo cảm giác.'
        st = _current(t)
        if st and st['kind'] == 'entry':
            return 'Nhắc nhỏ: mỗi chứng từ phải có tổng Nợ bằng tổng Có, và tài khoản đúng bản chất nghiệp vụ.'
        return 'Đã soát lại các bút toán đã ghi hôm nay: đều cân.'
    if e['role'] == 'ca_cash':
        return 'Đã xếp tiền trong két theo mệnh giá để lúc kiểm quỹ đếm nhanh hơn.'
    return None


def hint(c: dict, t: dict) -> str:
    if t.get('variant') == 'desk':
        return 'Xem quy định tháng này → soi từng bộ, mở sổ tra cứu khi cần → khoanh chỗ sai → đóng dấu → chốt khay.'
    return 'Mở đủ chứng từ → làm từng bước theo thứ tự (sai sẽ có gợi ý) → chọn ghi chú bàn giao → nộp hồ sơ.'


def _speed(t: dict) -> tuple[int, str]:
    if t.get('late') is True:
        return 2, 'nộp sau hạn'
    if type(t.get('due')) is int:
        return 5, 'kịp hạn ' + office.hhmm(t['due'])
    patience = t.get('patience', 100)
    return (5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2), f'người giao việc còn kiên nhẫn {patience}%'


def feedback(c: dict, t: dict) -> dict:
    speed, speed_note = _speed(t)
    if t.get('variant') == 'desk':
        res = t.get('results') or {}
        wrong = sum(1 for v in res.values() if v == 'wrong')
        reason = sum(1 for v in res.values() if v == 'reason')
        bad = [x for x in t['cases'] if x['_truth']['v'] != 'approve']
        caught = sum(1 for x in bad if res.get(x['id']) == 'ok')
        acc = 5 if wrong == 0 else 4 if wrong == 1 else 3 if wrong == 2 else 2
        vig = 5 if caught == len(bad) else 4 if caught >= len(bad) - 1 else 3 if caught * 2 >= len(bad) else 2
        grounds = 5 if reason == 0 else 4 if reason == 1 else 3
        return dict(criteria=[
            dict(key='accuracy', label='Đóng dấu chính xác', score=acc, note='mọi con dấu đều đúng' if not wrong else f'{wrong} dấu sai'),
            dict(key='vigilance', label='Tinh mắt bắt lỗi', score=vig, note=f'bắt đúng {caught}/{len(bad)} bộ có vấn đề'),
            dict(key='grounds', label='Có căn cứ rõ ràng', score=grounds, note='khoanh đúng chỗ sai' if not reason else f'{reason} lần khoanh chưa đúng căn cứ'),
            dict(key='speed', label='Đúng hạn', score=speed, note=speed_note)])
    m = t['mistakes']
    acc = 5 if m == 0 else 4 if m == 1 else 3 if m <= 3 else 2 if m <= 5 else 1
    tips = len(t['tips'])
    indep = 5 if tips == 0 else 4 if tips == 1 else 3
    hand = {'specific': 5, 'short': 3, 'none': 2}[t.get('handover') or 'none']
    return dict(criteria=[
        dict(key='accuracy', label='Chính xác số liệu', score=acc, note='không sai bước nào' if m == 0 else f'sai {m} lần trước khi đúng'),
        dict(key='independence', label='Tự lực', score=indep, note='tự làm, không cần gợi ý' if not tips else f'xin gợi ý {tips} lần'),
        dict(key='speed', label='Đúng hạn', score=speed, note=speed_note),
        dict(key='handover', label='Bàn giao rõ ràng', score=hand, note={5: 'ghi chú có số liệu và chứng từ', 3: 'ghi chú quá ngắn', 2: 'không để lại ghi chú'}[hand]),
    ])


def content() -> dict:
    return dict(accounts=[dict(id=a, name=n) for a, n in ACCOUNTS], kinds=KINDS, milestones=[dict(id=i, name=n) for i, n in MILESTONES],
                company=dict(name=COMPANY, mst=_mst(MST_OWN), bank=BANK), verdicts=[dict(id=v, label=VERDICT_LABEL[v]) for v in VERDICTS],
                boss=dict(name='Chị Hạnh', npc=kit.npc_id(ID, 0)), max_circles=MAX_CIRCLES,
                rules=['Thuế suất GTGT: 10% (hàng thông thường), 5% (mây sợi nguyên liệu).',
                       'Chỉ dùng các tài khoản có trong danh mục của công ty.',
                       'Mỗi tháng có 30 ngày; cứ 5 ngày làm việc là trọn một tháng kế toán.'])


# ================================================================ office care (shared)
# The day-to-day care loop of the three office careers: energy ("sức bền"), colleagues who ask for
# help and cover you later, reliable days feeding a mentor / promotion track, and helpers for the
# five-day calendar strip. office.py is shared by the three careers but outside this change, so the
# helpers live here; tax_payroll and group_accounting import them. Each career passes its CARE dict:
#   id, prefix, boss (the mentor), ranks (4 titles), lines (mentor note at ranks 1..3),
#   mates [dict(id, name, role, npc (PEOPLE index or None), emoji, asks [(text, minutes)], thanks, no, cover)].
# Every roll is kit.rng(career, …, day); nothing here reads player state inside make_task.
ENERGY_START, ENERGY_REST, ENERGY_OT, ENERGY_MIN = 80, 15, 25, 5
ENERGY_LOW, ENERGY_TIRED, ENERGY_FRESH = 35, 60, 80      # < 35 kiệt sức · < 60 hơi mệt · ≥ 80 tỉnh táo
BREAK_MIN, BREAK_GAIN, BREAK_GAIN_R1 = 15, 6, 10
SLOW_DIV = 5                                             # exhausted: every piece of work takes 1/5 longer
COVER_MIN = 60
ASK_FROM, ASK_CHANCE = 2, .75
BOND_MAX = 5
RANK_NEEDS = ((0, 0), (3, 0), (6, 55), (10, 70))         # (reliable days, boss trust) for ranks 0..3
RANK_PAY = (0, 0, 4, 8)                                  # xu on each reliable day at that rank
TRACK_DAYS = 7
CARE_OPEN = ('new', 'understood', 'in_progress', 'proposed', 'executing', 'awaiting_confirmation')


def care_initial(cfg: dict) -> dict:
    return dict(v=1, energy=ENERGY_START, rest=0, mates={m['id']: dict(bond=0, owes=0, helped=0) for m in cfg['mates']},
                ask=None, reliable=0, streak=0, rank=0, days=[])


def care_ensure(d: dict, cfg: dict) -> dict:
    """The care sub-state of a career's data (created for saves made before it existed)."""
    cr = d.get('care')
    if not isinstance(cr, dict):
        cr = d['care'] = care_initial(cfg)
    for k, v in care_initial(cfg).items():
        cr.setdefault(k, copy.deepcopy(v))
    if isinstance(cr['mates'], dict):
        for m in cfg['mates']:
            cr['mates'].setdefault(m['id'], dict(bond=0, owes=0, helped=0))
    return cr


def care_mate(cfg: dict, mid) -> dict | None:
    return next((m for m in cfg['mates'] if m['id'] == mid), None)


def care_energy_label(v: int) -> tuple[str, str]:
    if v < ENERGY_LOW:
        return 'Kiệt sức', 'bad'
    if v < ENERGY_TIRED:
        return 'Hơi mệt', 'warn'
    return ('Tỉnh táo', 'good') if v >= ENERGY_FRESH else ('Ổn', '')


def care_owe_cap(st: dict) -> int:
    return 2 if st['bond'] >= 3 else 1


_ASK_CHAIN: dict = {}


def _roll_ask(cfg: dict, day: int, prev: dict | None) -> dict | None:
    if day < ASK_FROM:
        return None
    r = kit.rng(cfg['id'], 'care-ask', day)
    if r.random() >= ASK_CHANCE:
        return None
    m = r.choice([x for x in cfg['mates'] if not prev or x['id'] != prev['mate']])
    return dict(day=day, mate=m['id'], i=r.randrange(len(m['asks'])))


def care_roll_ask(cfg: dict, day: int) -> dict | None:
    """Who asks for a hand today: seeded by the day, about three days in four from day 2, never the same
    colleague two days running (a deterministic chain, cached like office.mod_of)."""
    chain = _ASK_CHAIN.setdefault(cfg['id'], [None])
    day = max(0, int(day))
    while len(chain) <= day:
        chain.append(_roll_ask(cfg, len(chain), chain[-1]))
    return dict(chain[day], state='open') if chain[day] else None


def care_start(cr: dict, cfg: dict, day: int) -> None:
    cr['ask'] = care_roll_ask(cfg, day)


def care_ask_today(cr: dict, day: int) -> dict | None:
    a = cr.get('ask')
    return a if isinstance(a, dict) and a.get('day') == day and a.get('state') == 'open' else None


def care_rel(i: int) -> str:
    return 'Hôm nay' if i == 0 else 'Mai' if i == 1 else 'Ngày kia' if i == 2 else f'{i} ngày nữa'


def care_clock(o: dict, day: int) -> int:
    return o['clock'] if o['day'] == day else office.OPEN + (office.TIRED_MIN if o['tired'] == day else 0)


def care_cover_block(t: dict, o: dict, day: int) -> str:
    """Why a favour cannot push this dossier's deadline ('' when it can)."""
    if t.get('status') not in CARE_OPEN:
        return 'Hồ sơ này đã xong.'
    if type(t.get('due')) is not int:
        return 'Hồ sơ này không có giờ hạn.'
    if t.get('cover'):
        return 'Hồ sơ này đã được đỡ một lần rồi.'
    if t.get('due_day', day) != day or care_clock(o, day) > t['due']:
        return 'Hồ sơ đã trễ hạn — nhờ đỡ không kịp nữa.'
    if t['due'] >= office.LOCK:
        return 'Hạn đã sát giờ khóa cửa, không lùi thêm được.'
    return ''


def care_can_overtime(cr: dict, cfg: dict) -> None:
    kit.need(cr['energy'] >= ENERGY_LOW, f'Sức bền còn {cr["energy"]}/100 — {cfg["boss"]} bảo bạn về nghỉ, hôm nay không cho tăng ca. '
             'Một ngày về đúng giờ là hồi lại.')


def care_slow(cr: dict, o: dict, before: int) -> str:
    """Exhausted: the work just done took a fifth longer on the office clock."""
    if cr['energy'] >= ENERGY_LOW or o['clock'] <= before:
        return ''
    spent = o['clock'] - before - (office.LUNCH_MIN if before < office.LUNCH <= o['clock'] else 0)
    extra = max(0, spent) // SLOW_DIV
    if not extra:
        return ''
    o['clock'] = min(office.LOCK, o['clock'] + extra)
    return f'😮‍💨 Mệt nên làm chậm hơn: +{extra} phút.'


def _care_help(s: dict, c: dict, cr: dict, cfg: dict, o: dict, p: dict) -> dict:
    a = care_ask_today(cr, c['day'])
    kit.need(a, 'Hôm nay chưa ai nhờ bạn việc gì — hoặc bạn đã trả lời rồi.')
    kit.need(p.get('mate') == a['mate'], 'Người này không nhờ bạn hôm nay.')
    answer = kit.one_of(p.get('answer', 'yes'), ('yes', 'no'), 'Chọn giúp một tay hoặc để hôm khác.')
    m = care_mate(cfg, a['mate'])
    st = cr['mates'][m['id']]
    if answer == 'no':
        a['state'] = 'no'
        return dict(message=f'Bạn nói khéo là hôm nay kín việc. {m["no"]}')
    text, minutes = m['asks'][a['i']]
    lunch = office.spend(o, minutes)
    a['state'] = 'done'
    st['bond'] = min(BOND_MAX, st['bond'] + 1)
    st['helped'] += 1
    owed = st['owes']
    st['owes'] = min(care_owe_cap(st), st['owes'] + 1)
    if m.get('npc') is not None:
        kit.remember(s, c, kit.npc_id(cfg['id'], m['npc']), f'Bạn dành {minutes} phút giúp {m["name"]}. {m["thanks"]}')
    kit.metric(c, cfg['prefix'] + 'helped')
    tail = (f'Khi cần, {m["name"]} sẽ đỡ bạn một lần (đang nợ bạn {st["owes"]}).' if st['owes'] > owed else
            f'{m["name"]} quý bạn thêm một chút (thân thiết {st["bond"]}/{BOND_MAX}).')
    msg = f'🤝 Bạn giúp {m["name"]} ({minutes} phút). {m["thanks"]} {tail}'
    return dict(message=' '.join(x for x in (msg, lunch) if x))


def _care_cover(s: dict, c: dict, cr: dict, cfg: dict, o: dict, p: dict, can_cover=None) -> dict:
    m = care_mate(cfg, p.get('mate'))
    kit.need(m, 'Không có đồng nghiệp này.')
    st = cr['mates'][m['id']]
    kit.need(st['owes'] > 0, f'{m["name"]} chưa nợ bạn lần giúp nào — khi {m["name"]} nhờ, giúp một tay trước đã.')
    t = kit.task(c, p)
    kit.need(t['career'] == cfg['id'], 'Hồ sơ không thuộc phòng này.')
    why = care_cover_block(t, o, c['day']) or (can_cover(t, c['day']) if can_cover else '')
    kit.need(not why, why)
    office.need_open(o)
    t['due'] = min(office.LOCK, t['due'] + COVER_MIN)
    t['cover'] = m['id']
    st['owes'] -= 1
    office.note(o, c['day'], f'{m["name"]} đỡ một tay: “{t["title"]}” lùi hạn tới {office.hhmm(t["due"])}.', 'care')
    return dict(message=f'🙏 {m["cover"]} “{t["title"]}” giờ hạn {office.hhmm(t["due"])}.')


def _care_break(cr: dict, o: dict, day: int) -> dict:
    kit.need(cr['rest'] != day, 'Hôm nay bạn đã nghỉ giải lao rồi.')
    kit.need(cr['energy'] < 100, 'Sức bền đang đầy — chưa cần nghỉ đâu.')
    lunch = office.spend(o, BREAK_MIN)
    gain = BREAK_GAIN_R1 if cr['rank'] >= 1 else BREAK_GAIN
    before = cr['energy']
    cr['energy'] = min(100, before + gain)
    cr['rest'] = day
    msg = f'☕ Bạn pha ấm trà, đứng vươn vai bên cửa sổ 15 phút. Sức bền +{cr["energy"] - before} ({cr["energy"]}/100).'
    return dict(message=' '.join(x for x in (msg, lunch) if x))


def care_handle(s: dict, c: dict, d: dict, o: dict, cfg: dict, name: str, p: dict, can_cover=None) -> dict | None:
    """The shared care commands (<prefix>help / cover / break); None for any other command."""
    cr = care_ensure(d, cfg)
    if name == cfg['prefix'] + 'help':
        return _care_help(s, c, cr, cfg, o, p)
    if name == cfg['prefix'] + 'cover':
        return _care_cover(s, c, cr, cfg, o, p, can_cover)
    if name == cfg['prefix'] + 'break':
        return _care_break(cr, o, c['day'])
    return None


def care_close(s: dict, c: dict, cr: dict, cfg: dict, o: dict, ok: bool, why: str) -> dict:
    """End of day: energy, the reliable-day strip and the mentor track. Returns the summary part."""
    day = c['day']
    before = cr['energy']
    cr['energy'] = max(ENERGY_MIN, min(100, before + (-ENERGY_OT if o['ot'] else ENERGY_REST)))
    if ok:
        cr['reliable'] += 1
        cr['streak'] += 1
    else:
        cr['streak'] = 0
    cr['days'] = ar.last(cr['days'] + [dict(day=day, ok=bool(ok), why=str(why)[:120])], TRACK_DAYS, 'office.days', c)
    up = None
    while cr['rank'] < 3 and cr['reliable'] >= RANK_NEEDS[cr['rank'] + 1][0] and o['trust'] >= RANK_NEEDS[cr['rank'] + 1][1]:
        cr['rank'] += 1
        up = cfg['ranks'][cr['rank']]
        line = cfg['lines'][cr['rank'] - 1]
        office.note(o, day, f'{cfg["boss"]}: “{line}”', 'care')
        kit.log(s, c, 'surprise', f'🧭 Lộ trình: {up}. {cfg["boss"]}: “{line}”', kit.npc_id(cfg['id'], 0))
    pay = RANK_PAY[cr['rank']] if ok else 0
    if pay:
        kit.money(s, c, pay, 'Phụ cấp trách nhiệm: một ngày làm chắc tay', None, 'office_bonus')
    label, tone = care_energy_label(cr['energy'])
    if o['ot'] and cr['energy'] < ENERGY_LOW:
        office.note(o, day, f'Sức bền còn {cr["energy"]}/100 — mai về đúng giờ cho lại sức nhé.', 'care')
    return dict(energy=cr['energy'], energy_change=cr['energy'] - before, energy_label=label, energy_tone=tone,
                reliable=bool(ok), why=str(why)[:120], streak=cr['streak'], total=cr['reliable'], rank=cfg['ranks'][cr['rank']],
                rank_up=up, pay=pay)


def care_public(cr: dict, cfg: dict, c: dict, o: dict, can_cover=None) -> dict:
    day = c['day']
    a = care_ask_today(cr, day)
    mates = []
    for m in cfg['mates']:
        st = cr['mates'][m['id']]
        ask = None
        if a and a['mate'] == m['id']:
            text, minutes = m['asks'][a['i']]
            ask = dict(text=text, minutes=minutes)
        mates.append(dict(id=m['id'], name=m['name'], role=m['role'], emoji=m['emoji'],
                          npc=kit.npc_id(cfg['id'], m['npc']) if m.get('npc') is not None else None,
                          bond=st['bond'], owes=st['owes'], cap=care_owe_cap(st), helped=st['helped'], ask=ask, cover=m['cover']))
    label, tone = care_energy_label(cr['energy'])
    r = cr['rank']
    nxt = None
    if r < 3:
        need_days, need_trust = RANK_NEEDS[r + 1]
        nxt = dict(title=cfg['ranks'][r + 1], days=need_days, left=max(0, need_days - cr['reliable']), trust=need_trust,
                   trust_ok=o['trust'] >= need_trust)
    perks = ['☕ Nghỉ giải lao hồi +10 sức bền', '💰 +4 xu mỗi ngày làm chắc tay', '💰 +8 xu mỗi ngày làm chắc tay']
    cover = [t['id'] for t in c['tasks'] if t.get('career') == cfg['id'] and not care_cover_block(t, o, day)
             and not (can_cover and can_cover(t, day))]
    return dict(
        energy=dict(value=cr['energy'], label=label, tone=tone, low=cr['energy'] < ENERGY_LOW, can_break=bool(c.get('open')) and cr['rest'] != day and cr['energy'] < 100,
                    gain=BREAK_GAIN_R1 if r >= 1 else BREAK_GAIN, rest=ENERGY_REST, ot=ENERGY_OT, line=ENERGY_LOW),
        mates=mates, asked=bool(a), coverable=cover, mentor=cfg['boss'],
        track=dict(rank=r, title=cfg['ranks'][r], ranks=list(cfg['ranks']), reliable=cr['reliable'], streak=cr['streak'],
                   days=tree_copy(cr['days']), next=nxt, perks=[dict(rank=i + 1, text=x, on=r >= i + 1) for i, x in enumerate(perks)]))


def care_validate(cr, cfg: dict) -> None:
    kit.need(isinstance(cr, dict) and set(care_initial(cfg)) <= set(cr), 'Sổ đời sống văn phòng thiếu dữ liệu.')
    kit.integer(cr['v'], 1, 1)
    kit.integer(cr['energy'], 0, 100)
    kit.integer(cr['rest'], 0, 10 ** 7)
    ids = [m['id'] for m in cfg['mates']]
    kit.need(isinstance(cr['mates'], dict) and set(cr['mates']) == set(ids), 'Sổ đồng nghiệp sai.')
    for st in cr['mates'].values():
        kit.need(isinstance(st, dict) and set(st) == {'bond', 'owes', 'helped'}, 'Sổ đồng nghiệp sai.')
        kit.integer(st['bond'], 0, BOND_MAX)
        kit.integer(st['helped'], 0, 10 ** 6)
        kit.integer(st['owes'], 0, care_owe_cap(st))
    a = cr['ask']
    if a is not None:
        kit.need(isinstance(a, dict) and set(a) == {'day', 'mate', 'i', 'state'} and a['mate'] in ids
                 and a['state'] in ('open', 'done', 'no'), 'Lời nhờ của đồng nghiệp sai.')
        kit.integer(a['day'], 1, 10 ** 7)
        kit.integer(a['i'], 0, len(care_mate(cfg, a['mate'])['asks']) - 1)
    kit.integer(cr['reliable'], 0, 10 ** 6)
    kit.integer(cr['streak'], 0, cr['reliable'])
    kit.integer(cr['rank'], 0, 3)
    kit.need(cr['reliable'] >= RANK_NEEDS[cr['rank']][0], 'Lộ trình thăng tiến sai.')
    kit.need(isinstance(cr['days'], list) and len(cr['days']) <= TRACK_DAYS, 'Sổ ngày làm việc sai.')
    for x in cr['days']:
        kit.need(isinstance(x, dict) and set(x) == {'day', 'ok', 'why'} and type(x['ok']) is bool, 'Sổ ngày làm việc sai.')
        kit.integer(x['day'], 1, 10 ** 7)
        kit.text(x['why'], 120)


def care_validate_task(t: dict, cfg: dict) -> None:
    if t.get('cover') is not None:
        kit.need(t['cover'] in [m['id'] for m in cfg['mates']] and type(t.get('due')) is int, 'Lần nhờ đỡ hạn sai.')


# ---------------------------------------------------------------- corp care: colleagues, mentor, month-end close plan
CARE = dict(
    id=ID, prefix=PREFIX, boss='Chị Hạnh',
    ranks=('Thử việc', 'Kế toán viên chính thức', 'Giữ tủ chứng từ ngân hàng', 'Được đề cử kế toán tổng hợp'),
    lines=('Ba ngày chắc tay rồi. Từ mai em là người của phòng mình.',
           'Chị giao em giữ ngăn chứng từ ngân hàng. Số nào cũng phải có chứng từ nhé.',
           'Chị đã đề xuất em lên kế toán tổng hợp. Giờ chờ anh Tùng ký thôi.'),
    mates=[
        dict(id='na', name='Na', role='Thực tập sinh kế toán', npc=7, emoji='🧑‍🎓',
             asks=[('Soát giúp em phiếu chi nháp này với, em cộng ba lần ra ba số 😭', 20),
                   ('Định khoản hàng mua đang đi đường là sao ạ? Chỉ em năm phút thôi!', 15),
                   ('Mai em trình bày với chị Hạnh, nghe em tập thử một lượt được không?', 25)],
             thanks='Na cười tít mắt: “Em nhớ đó nha!”', no='Na gật đầu: “Không sao, em hỏi Nguyên vậy.”',
             cover='Na chạy trình ký và photo giúp —'),
        dict(id='lua', name='Cô Lụa', role='Thủ quỹ', npc=2, emoji='💵',
             asks=[('Két lệch 20 xu, con đếm lại cùng cô cho chắc nhé?', 20),
                   ('Phiếu thu sáng nay nhòe mực, con ghi lại sổ quỹ giúp cô?', 15)],
             thanks='Cô Lụa dúi cho bạn gói ô mai: “Cô ghi nhớ.”', no='Cô Lụa xua tay: “Ừ, con bận thì thôi, cô tự đếm.”',
             cover='Cô Lụa sang nói đỡ với chị Hạnh —'),
        dict(id='bao', name='Bảo', role='Nhân viên kinh doanh', npc=3, emoji='🧑‍💼',
             asks=[('Khách đòi hóa đơn gấp mà em không biết ghi tên hàng sao cho đúng. Cứu em!', 20),
                   ('Xấp chứng từ công tác phí của em lộn xộn quá, xếp giúp em theo ngày với?', 25)],
             thanks='Bảo chắp tay: “Lần sau có gì em chạy giúp liền.”', no='Bảo cười: “Ok, để em tự mò, có gì hỏi sau.”',
             cover='Bảo chạy xe qua ngân hàng lấy sổ phụ giúp —'),
    ])
CLOSE_PLAN = [('docs', '🧾', 'Chốt chứng từ & hóa đơn', 1, 'Khay chứng từ, hóa đơn hoặc định khoản'),
              ('cash', '💵', 'Kiểm quỹ & kho', 2, 'Kiểm quỹ tiền mặt hoặc kiểm kê kho'),
              ('bank', '🏦', 'Đối chiếu ngân hàng', 3, 'Hồ sơ đối chiếu ngân hàng'),
              ('fixed', '🪑', 'Khấu hao TSCĐ', 3, 'Hồ sơ khấu hao tài sản cố định'),
              ('close', '🔒', 'Khóa sổ & báo cáo', 4, 'Cân đối thử hoặc khóa sổ cuối tháng')]
CLOSE_IDS = [x[0] for x in CLOSE_PLAN]
CLOSE_SHORT = dict(docs='Chốt chứng từ', cash='Quỹ & kho', bank='Ngân hàng', fixed='Khấu hao', close='Khóa sổ')
CLOSE_DUE = {x[0]: x[3] for x in CLOSE_PLAN}
CLOSE_BONUS, CLOSE_MISS = 12, 2


def _month(day: int) -> int:
    return (max(1, day) - 1) // 5


def _close_plan(cr: dict, day: int) -> dict:
    """This month's close plan (a new month starts empty)."""
    cp = cr.get('close')
    if not isinstance(cp, dict) or cp.get('month') != _month(day):
        cp = cr['close'] = dict(month=_month(day), done={}, missed=[])
    return cp


def _care(c: dict, d: dict) -> dict:
    cr = care_ensure(d, CARE)
    if 'close' not in cr:                      # saves made before the close plan: what is done this month counts, on time
        start = c['day'] - (c['day'] - 1) % 5
        cr['close'] = dict(month=_month(c['day']), done={m: start for m in d.get('milestones', []) if m in CLOSE_IDS}, missed=[])
    return cr


def _close_tick(c: dict, cr: dict, t: dict, ms: str) -> str:
    cp = _close_plan(cr, c['day'])
    if ms not in CLOSE_IDS or ms in cp['done'] or _month(t['day']) != cp['month']:
        return ''
    cp['done'][ms] = c['day']
    name = next(x[2] for x in CLOSE_PLAN if x[0] == ms)
    late = (c['day'] - 1) % 5 > CLOSE_DUE[ms]
    return f'📅 Kế hoạch khóa sổ: ✓ {name}' + (' (trễ mốc).' if late else ' — kịp mốc.')


def _close_grade(s: dict, c: dict, cr: dict, o: dict) -> dict | None:
    day = c['day']
    cp = _close_plan(cr, day)
    phase = (day - 1) % 5
    missed = []
    for i, e, name, due, _ in CLOSE_PLAN:
        if due == phase and i not in cp['done'] and i not in cp['missed']:
            cp['missed'].append(i)
            office.trust(o, -CLOSE_MISS)
            office.note(o, day, f'Trễ mốc khóa sổ: {name}. Chị Hạnh nhắc làm cho xong.', 'late')
            missed.append(name)
    if phase != 4:
        return dict(missed=missed) if missed else None
    on_time = [i for i in CLOSE_IDS if i in cp['done'] and (cp['done'][i] - 1) % 5 <= CLOSE_DUE[i]]
    bonus = 0
    if len(on_time) == len(CLOSE_IDS):
        bonus = CLOSE_BONUS
        kit.money(s, c, bonus, 'Thưởng khóa sổ đúng hạn', None, 'office_bonus')
        office.trust(o, 3)
    left = [x[2] for x in CLOSE_PLAN if x[0] not in cp['done']]
    return dict(missed=missed, on_time=len(on_time), total=len(CLOSE_IDS), bonus=bonus, left=left, month_end=True)


def _reliable(d: dict, o: dict) -> tuple[bool, str]:
    if not d['day_done']:
        return False, 'Chưa nộp hồ sơ nào'
    if o['day_late']:
        return False, f'{o["day_late"]} hồ sơ nộp trễ hạn'
    if any(x['slip'] for x in d['day_stamps']):
        return False, 'Có chứng từ bị duyệt nhầm'
    return True, f'{d["day_done"]} hồ sơ kịp hạn, không duyệt nhầm'


def _calendar(c: dict, cr: dict) -> list:
    day = c['day']
    cp = _close_plan(copy.deepcopy(cr), day)
    phase = (day - 1) % 5
    cells = []
    for i in range(5):
        dd = day + i
        ph, same = (dd - 1) % 5, _month(dd) == cp['month']
        m, _, dom = _period(dd)
        items = []
        if i == 0:
            items += [dict(emoji=e, text=CLOSE_SHORT[k], state='late') for k, e, name, due, _ in CLOSE_PLAN if due < phase and k not in cp['done']]
        for k, e, name, due, _ in CLOSE_PLAN:
            if due == ph:
                items.append(dict(emoji=e, text=CLOSE_SHORT[k], state='done' if same and k in cp['done'] else 'due' if i == 0 else 'todo'))
        mod = _mod(dd)
        cells.append(dict(day=dd, date=_d(dom, m), rel=care_rel(i), mod=None if mod['id'] == 'normal' else dict(emoji=mod['emoji'], name=mod['name']),
                          items=items))
    return cells


def _plan_view(c: dict, cr: dict) -> dict:
    day = c['day']
    cp = _close_plan(cr, day)
    phase = (day - 1) % 5
    m, _, _ = _period(day)
    start = day - phase
    items = []
    for k, e, name, due, how in CLOSE_PLAN:
        done = cp['done'].get(k)
        state = ('done' if (done - 1) % 5 <= due else 'late_done') if done else 'late' if due < phase else 'due' if due == phase else 'todo'
        dm, _, ddom = _period(start + due)
        items.append(dict(id=k, emoji=e, name=name, how=how, date=_d(ddom, dm), rel=care_rel(due - phase) if due >= phase else 'Đã qua',
                          state=state))
    return dict(kind='close', title=f'Kế hoạch khóa sổ tháng {m}', items=items, bonus=CLOSE_BONUS,
                done=sum(1 for x in items if x['state'] in ('done', 'late_done')), total=len(items))


def _validate_close(cr: dict) -> None:
    cp = cr.get('close')
    kit.need(isinstance(cp, dict) and set(cp) == {'month', 'done', 'missed'}, 'Kế hoạch khóa sổ sai.')
    kit.integer(cp['month'], 0, 10 ** 6)
    kit.need(isinstance(cp['done'], dict) and set(cp['done']) <= set(CLOSE_IDS), 'Kế hoạch khóa sổ sai.')
    for v in cp['done'].values():
        kit.integer(v, 1, 10 ** 7)
        kit.need(_month(v) == cp['month'], 'Kế hoạch khóa sổ sai.')
    kit.need(isinstance(cp['missed'], list) and len(set(cp['missed'])) == len(cp['missed']) and set(cp['missed']) <= set(CLOSE_IDS),
             'Kế hoạch khóa sổ sai.')


# ---------------------------------------------------------------- situations
SITUATIONS = [
    dict(id='CA-S01', title='Giám đốc nhờ “lùi ngày” hóa đơn', npc=1, tone='tense', min_day=1,
         opening='Anh Tùng ghé bàn: “Lô ghế giao ngày 2 tháng sau, em xuất hóa đơn ngày 30 tháng này giúp anh nhé. Doanh số tháng này thiếu chút xíu thôi.”',
         swap='Bạn là giám đốc: chỉ tiêu tháng thiếu 5%, ngân hàng sắp xem báo cáo.',
         facts=[dict(id='dn', title='Biên bản giao hàng', source='Kho', text='Lịch giao ghế là ngày 02 tháng sau; hàng vẫn nằm trong kho, khách chưa nhận.'),
                dict(id='rule', title='Quy chế kế toán', source='Chị Hạnh', text='Doanh thu ghi nhận khi hàng đã giao và khách chấp nhận. Hóa đơn lập theo ngày giao hàng.'),
                dict(id='bank', title='Hợp đồng vay', source='Ngân hàng', text='Ngân hàng xem doanh thu theo quý, không phải từng tháng; số liệu sai kỳ có thể làm báo cáo bị kiểm toán điều chỉnh.')],
         options=[dict(id='explain', label='Từ chối lùi ngày, giải thích quy tắc và đề xuất báo cáo riêng “đơn đã ký chờ giao” cho giám đốc', requires=['dn', 'rule'], quality='good', stars=5, reward=20,
                       review='Em ấy không chiều anh, nhưng đưa anh một bảng “đơn chờ giao” còn đẹp hơn con số lùi ngày. Được!',
                       outcome='Anh Tùng cầm bảng đơn chờ giao đi họp; ngân hàng khen quản trị đơn hàng rõ ràng. Doanh thu ghi đúng kỳ.',
                       perspectives=[dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Lúc đầu hơi cụt hứng, nhưng bảng đơn chờ giao làm anh tự tin hơn khi nói chuyện với ngân hàng.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Người mới biết nói “không” kèm một giải pháp — đó là kế toán giỏi.'),
                                     dict(who='Anh Khải · Kiểm toán', emoji='🔎', text='Cắt kỳ đúng thì quý sau tôi không phải đề nghị điều chỉnh.')]),
                  dict(id='comply', label='Chiều giám đốc: xuất hóa đơn ngày 30', quality='bad', stars=2, cost=30,
                       review='Lúc đó anh vui, nhưng kiểm toán bắt được thì anh là người phải giải trình. Lần sau nhắc anh nhé.',
                       outcome='Quý sau kiểm toán phát hiện sai kỳ, đề nghị điều chỉnh giảm doanh thu; bạn bị trừ thưởng và mất một tối viết giải trình.',
                       perspectives=[dict(who='Anh Khải · Kiểm toán', emoji='🔎', text='Hàng chưa rời kho mà đã có doanh thu — đây là lỗi cắt kỳ kinh điển.'),
                                     dict(who='Cán bộ thuế', emoji='🏛️', text='Hóa đơn lập sai thời điểm là vi phạm về hóa đơn, dù số tiền không đổi.')]),
                  dict(id='escalate', label='Không làm, chuyển ngay cho kế toán trưởng quyết', requires=['rule'], quality='ok',
                       outcome='Chị Hạnh từ chối thay bạn. Doanh thu đúng kỳ, nhưng anh Tùng nghĩ bạn “đẩy việc”.',
                       perspectives=[dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Hỏi ý chị là đúng, nhưng lần sau em tự giải thích được mà.'),
                                     dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Hỏi một câu mà phải đi qua hai người.')])],
         lesson='Ghi đúng kỳ là nguyên tắc; nói “không” thì mang theo một cách khác để đạt mục tiêu thật.'),
    dict(id='CA-S02', title='Đồng nghiệp nhờ “gửi” hóa đơn ăn tối gia đình', npc=3, tone='gentle', min_day=2,
         opening='Bảo đưa hóa đơn nhà hàng 180 xu: “Tiếp khách thôi mà anh chị, cho em vào chi phí công ty nha. Ai mà kiểm tra.”',
         facts=[dict(id='bill', title='Hóa đơn', source='Nhà hàng Lẩu Nấm', text='Hóa đơn tối Chủ nhật, 4 suất trẻ em, 2 suất người lớn, có bánh sinh nhật.'),
                dict(id='policy', title='Quy chế chi tiêu', source='Phòng hành chính', text='Chi tiếp khách cần tên khách, mục đích, được trưởng phòng duyệt trước.'),
                dict(id='bao', title='Chuyện của Bảo', source='Cô Lụa', text='Cô Lụa kể: tháng này Bảo vừa chuyển nhà, đang kẹt tiền.')],
         options=[dict(id='kind_no', label='Từ chối nhẹ nhàng, giải thích quy chế; gợi ý Bảo hỏi chế độ tạm ứng lương', requires=['bill', 'policy'], quality='good', stars=5,
                       review='Bị từ chối mà em không thấy quê, còn được chỉ cách tạm ứng lương. Ok luôn 🫡',
                       outcome='Bảo xé hóa đơn, làm đơn tạm ứng. Cuối năm quy chế chi tiêu được nhắc lại cho cả công ty.',
                       perspectives=[dict(who='Bảo · Kinh doanh', emoji='🙈', text='Em biết là sai, chỉ đang cố. Được chỉ lối khác làm em đỡ xấu hổ.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Chi phí không có thật làm sai lợi nhuận và sai cả thuế. Giữ được là giỏi.'),
                                     dict(who='Cô Lụa · Thủ quỹ', emoji='💵', text='Từ chối mà vẫn giữ tình đồng nghiệp — khó mà làm được.')]),
                  dict(id='accept', label='Nhận luôn, “lần này thôi”', quality='bad', stars=3, cost=20,
                       review='Được duyệt vui ghê… nhưng hôm sau chị Hạnh hỏi em chuyện này, em run quá.',
                       outcome='Kiểm tra chi phí cuối quý phát hiện hóa đơn sinh nhật gia đình; bạn và Bảo cùng bị nhắc nhở, trừ thưởng.',
                       perspectives=[dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='“Lần này thôi” là câu mở đầu của mọi vụ gian lận chi phí.'),
                                     dict(who='Anh Khải · Kiểm toán', emoji='🔎', text='Chi phí không phục vụ kinh doanh sẽ bị loại khi quyết toán.')]),
                  dict(id='report', label='Báo ngay giám đốc trong nhóm chat chung', requires=['bill'], quality='ok',
                       outcome='Chi phí không vào sổ, nhưng Bảo bị bêu tên trước cả phòng và giận bạn cả tuần.',
                       perspectives=[dict(who='Bảo · Kinh doanh', emoji='😞', text='Sai thì em chịu, nhưng sao không nói riêng với em trước?'),
                                     dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Đúng việc, sai chỗ. Chuyện này nói riêng là đủ.')])],
         lesson='Không ghi chi phí không có thật; từ chối riêng tư, kèm một lối ra hợp lệ.'),
    dict(id='CA-S03', title='Nhà cung cấp gửi cùng một hóa đơn hai lần', npc=5, tone='gentle', min_day=1,
         opening='Bà Sáu gọi: “Hóa đơn tháng trước sao chưa trả bà? Bà gửi email lại rồi đó, trả gấp giùm!”',
         facts=[dict(id='book', title='Sổ hóa đơn đầu vào', source='Phần mềm kế toán', text='Hóa đơn cùng ký hiệu, cùng số, cùng số tiền đã ghi sổ ngày 12.'),
                dict(id='unc', title='Ủy nhiệm chi', source='Ngân hàng', text='Ngày 20 đã chuyển khoản đủ tiền cho HTX Mây Tre Bà Sáu, ngân hàng báo thành công.'),
                dict(id='hr', title='Chuyện ở HTX', source='Bà Sáu', text='Kế toán cũ của HTX vừa nghỉ, người mới chưa quen đối chiếu sao kê.')],
         options=[dict(id='proof', label='Gửi bà Sáu ủy nhiệm chi, chỉ dòng tiền trên sao kê; không ghi sổ hóa đơn gửi lại', requires=['book', 'unc'], quality='good', stars=5,
                       review='Ừ, tiền về từ ngày 20 thật. Con bé kế toán mới nhà bà không biết dò sao kê. Cảm ơn cháu nhé.',
                       outcome='Bà Sáu dặn kế toán mới cách dò sao kê. Hai bên không ai mất tiền, quan hệ còn tốt hơn.',
                       perspectives=[dict(who='Bà Sáu · Nhà cung cấp', emoji='🧺', text='Già rồi, thấy số là lo. Có giấy tờ rõ ràng là bà yên tâm.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Không trả hai lần, không làm mất lòng — chuẩn.')]),
                  dict(id='pay', label='Chuyển khoản lần nữa cho bà vui, “thừa thì trả lại sau”', quality='bad', cost=40,
                       outcome='Công ty trả trùng; ba tháng sau mới đòi lại được, bạn bị trừ thưởng vì sai sót thanh toán.',
                       perspectives=[dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Tiền ra khỏi công ty thì đòi lại rất mệt.'),
                                     dict(who='Bà Sáu · Nhà cung cấp', emoji='🧺', text='Bà cũng ngại, có ai muốn cầm tiền không phải của mình đâu.')]),
                  dict(id='ignore', label='Không trả lời, chờ bà tự kiểm', quality='bad', stars=2,
                       review='Gọi mãi không ai nghe. Cửa hàng lớn mà làm việc vậy à?',
                       outcome='Bà Sáu hoãn giao lô mây kế tiếp vì nghĩ công ty nợ tiền.',
                       perspectives=[dict(who='Chú Toàn · Thủ kho', emoji='📦', text='Không có mây thì xưởng đứng, lúc đó mới khổ.'), dict(who='Bà Sáu · Nhà cung cấp', emoji='🧺', text='Tôi gửi lại vì sợ thất lạc. Không ai nói gì thì tôi cứ tưởng bên ấy chưa nhận.')])],
         lesson='Đối chiếu trước khi trả: mỗi nghiệp vụ chỉ ghi và chỉ trả một lần — và nói chuyện bằng chứng từ.'),
    dict(id='CA-S04', title='Kiểm toán hỏi chứng từ không tìm thấy', npc=4, tone='tense', min_day=3,
         opening='Anh Khải: “Anh cần bản gốc phiếu chi PC-117 tháng 3, 950 xu trả tiền sửa máy.” Bạn lục cả tủ mà không thấy.',
         facts=[dict(id='bank', title='Sao kê', source='Ngân hàng', text='Khoản 950 xu chuyển khoản cho Xưởng Cơ Khí Bình Minh ngày 14/03, nội dung “sửa máy chẻ mây”.'),
                dict(id='repair', title='Biên bản sửa chữa', source='Chú Toàn', text='Chú Toàn còn giữ bản sao biên bản nghiệm thu sửa máy, có chữ ký hai bên.'),
                dict(id='temptation', title='Lời gợi ý', source='Đồng nghiệp', text='Một đồng nghiệp thì thầm: “Viết lại cái phiếu chi, ký tên là xong, ai biết.”')],
         options=[dict(id='honest', label='Nói thật là thất lạc bản gốc; cung cấp sao kê, biên bản sửa chữa, xin xưởng bản sao hóa đơn và ghi nhận sự cố lưu trữ',
                       requires=['bank', 'repair'], quality='good', stars=5, reward=15,
                       review='Thiếu một tờ giấy nhưng đủ bằng chứng thay thế, và không ai bịa gì cả. Ghi nhận.',
                       outcome='Kiểm toán chấp nhận bằng chứng thay thế, chỉ nêu khuyến nghị về lưu trữ. Công ty mua thêm tủ hồ sơ có khóa.',
                       perspectives=[dict(who='Anh Khải · Kiểm toán', emoji='🔎', text='Mất chứng từ là chuyện xảy ra; làm giả mới là chuyện lớn.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Tiện dịp sửa luôn quy trình lưu trữ. Cảm ơn em đã trung thực.')]),
                  dict(id='forge', label='Viết lại phiếu chi mới, ký thay cho nhanh', requires=['temptation'], quality='bad', stars=1, cost=60,
                       review='Chữ ký trên phiếu khác hẳn mẫu chữ ký đăng ký. Tôi buộc phải báo cáo ban giám đốc.',
                       outcome='Kiểm toán phát hiện chứng từ lập lại, cả bộ hồ sơ năm bị soi kỹ hơn; bạn bị kỷ luật.',
                       perspectives=[dict(who='Anh Khải · Kiểm toán', emoji='🔎', text='Một chứng từ giả làm tôi mất niềm tin vào mọi chứng từ còn lại.'),
                                     dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Tôi thà nghe “em làm mất” còn hơn.')]),
                  dict(id='stall', label='Hẹn “để em tìm tiếp”, rồi im lặng', quality='ok', stars=3,
                       review='Hẹn rồi im. Tôi phải hỏi lại ba lần.',
                       outcome='Kiểm toán ghi “chưa đủ bằng chứng” cho khoản này, báo cáo chậm một tuần.',
                       perspectives=[dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Im lặng làm chuyện nhỏ thành chuyện lớn.'), dict(who='Anh Khải · Kiểm toán', emoji='🔎', text='Chứng từ mất thì có cách xử lý. Không trả lời thì tôi phải ghi là hạn chế phạm vi.')])],
         lesson='Thiếu chứng từ thì tìm bằng chứng thay thế và nói thật — không bao giờ lập lại chứng từ.'),
    dict(id='CA-S05', title='Quỹ thiếu 40 xu', npc=2, tone='tense', min_day=2,
         opening='Kiểm quỹ cuối ngày thiếu đúng 40 xu. Cô Lụa mặt tái mét: “Cô không lấy đâu, thề đấy…”',
         facts=[dict(id='recount', title='Đếm lại', source='Hai người đếm', text='Đếm lại lần hai, có người chứng kiến: vẫn thiếu 40 xu.'),
                dict(id='voucher', title='Khay chứng từ', source='Bàn thủ quỹ', text='Trong kẹp hồ sơ có phiếu chi tạm ứng 40 xu cho Bảo đi công tác, Bảo đã ký nhận, chưa nhập sổ.'),
                dict(id='rumor', title='Lời đồn', source='Phòng bên', text='Có người bảo “chắc thủ quỹ cầm về rồi”.')],
         options=[dict(id='process', label='Đếm lại có người chứng kiến, rà chứng từ, tìm ra phiếu tạm ứng, nhập sổ và lập biên bản', requires=['recount', 'voucher'], quality='good', stars=5, reward=15,
                       review='Cảm ơn cháu đã tin cô và rà từng tờ. Hóa ra phiếu tạm ứng kẹp nhầm chỗ.',
                       outcome='Quỹ khớp sau khi nhập phiếu tạm ứng. Phòng kế toán thêm bước “quét khay chứng từ” trước khi kiểm quỹ.',
                       perspectives=[dict(who='Cô Lụa · Thủ quỹ', emoji='💵', text='Cô sợ nhất là bị nghi oan. Có quy trình thì ai cũng được bảo vệ.'),
                                     dict(who='Bảo · Kinh doanh', emoji='🙈', text='Em ký phiếu xong chạy đi luôn, quên đưa kế toán. Lỗi em.')]),
                  dict(id='cover', label='Tự bỏ 40 xu vào két cho khớp, khỏi rắc rối', quality='bad', cost=40,
                       outcome='Quỹ “khớp” nhưng phiếu tạm ứng không được ghi: cuối tháng khoản tạm ứng của Bảo biến mất khỏi sổ, số liệu sai hai chỗ.',
                       perspectives=[dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Bù tiền túi là che mất nguyên nhân — lần sau lệch lớn hơn thì sao?'),
                                     dict(who='Cô Lụa · Thủ quỹ', emoji='💵', text='Cô biết cháu tốt bụng, nhưng cô vẫn chưa biết tiền đi đâu.')]),
                  dict(id='accuse', label='Báo giám đốc là thủ quỹ làm mất', requires=['rumor'], quality='bad', stars=1,
                       review='Chưa kiểm gì đã quy cho cô. Buồn lắm.',
                       outcome='Hai ngày sau tìm ra phiếu tạm ứng; cô Lụa xin chuyển bộ phận vì bị nghi oan.',
                       perspectives=[dict(who='Cô Lụa · Thủ quỹ', emoji='😢', text='Hai mươi năm giữ quỹ, lần đầu bị nói vậy.'),
                                     dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Tôi đã suýt quyết định sai vì một thông tin chưa kiểm.')])],
         lesson='Lệch quỹ: đếm lại có chứng kiến, rà chứng từ, lập biên bản — không tự bù, không đổ lỗi khi chưa có bằng chứng.'),
    dict(id='CA-S06', title='Phòng kinh doanh ép ghi doanh thu sớm', npc=3, tone='gentle', min_day=3,
         opening='Ngày 30, Bảo năn nỉ: “Hợp đồng 2.000 xu ký rồi, hàng tuần sau mới giao. Ghi doanh thu hôm nay cho team em đạt KPI đi mà!”',
         facts=[dict(id='contract', title='Hợp đồng', source='Phòng kinh doanh', text='Hàng giao ngày 05 tháng sau; khách được trả lại nếu hàng lỗi khi nhận.'),
                dict(id='kpi', title='Cách tính KPI', source='Nhân sự', text='KPI tính theo doanh thu kế toán đã ghi nhận trong tháng.'),
                dict(id='hr', title='Ý kiến chị Hạnh', source='Chị Hạnh', text='Có thể đề xuất ban giám đốc tính KPI theo “hợp đồng đã ký” riêng, không đụng sổ sách.')],
         options=[dict(id='kpi_fix', label='Giữ doanh thu đúng kỳ; cùng Bảo đề xuất tính thêm chỉ tiêu “hợp đồng đã ký” cho KPI', requires=['contract', 'hr'], quality='good', stars=5,
                       review='Không được ghi sớm, nhưng từ tháng sau team em có KPI hợp đồng ký mới. Win-win luôn ✨',
                       outcome='Ban giám đốc duyệt thêm chỉ tiêu hợp đồng ký mới; sổ sách giữ đúng thời điểm ghi nhận.',
                       perspectives=[dict(who='Bảo · Kinh doanh', emoji='📈', text='Tưởng bị từ chối là xong, ai ngờ được sửa cả cách tính KPI.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Kế toán không chỉ giữ sổ, còn góp ý để quy trình công bằng hơn.')]),
                  dict(id='book', label='Ghi doanh thu hôm nay cho vui cả nhà', quality='bad', stars=4, cost=30,
                       review='Tuyệt vời luôn!!! (tháng sau kiểm toán gọi lên thì… hơi toang 😬)',
                       outcome='Tháng sau khách trả lại một phần hàng lỗi; doanh thu tháng trước phải điều chỉnh, báo cáo bị kiểm toán lưu ý.',
                       perspectives=[dict(who='Anh Khải · Kiểm toán', emoji='🔎', text='Ghi doanh thu trước khi giao hàng là làm đẹp số liệu.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Vui một tháng, mệt cả quý.')]),
                  dict(id='refuse', label='Từ chối thẳng: “Không là không.”', requires=['contract'], quality='ok', stars=3,
                       review='Đúng là không được, nhưng nghe câu đó em hơi cụt hứng.',
                       outcome='Doanh thu đúng kỳ; team kinh doanh không hiểu vì sao và tiếp tục xin lần sau.',
                       perspectives=[dict(who='Bảo · Kinh doanh', emoji='😶', text='Em cần biết vì sao, không chỉ nghe chữ “không”.'), dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Đúng nguyên tắc rồi, nhưng thêm một câu giải thích và một phương án thì phòng kinh doanh đã thành đồng minh.')])],
         lesson='Doanh thu theo thời điểm giao hàng, không theo áp lực chỉ tiêu; áp lực thật thì sửa cách đo, không sửa sổ.'),
    dict(id='CA-S07', title='Email “từ CEO” đòi chuyển khoản gấp', npc=1, tone='tense', min_day=2,
         opening='16h55, email từ “anh.tung.ceo@maytrexanh-vn.co”: “Em chuyển gấp 3.000 xu cho nhà cung cấp mới, số tài khoản dưới đây. Đang họp, đừng gọi. Giữ bí mật.”',
         facts=[dict(id='domain', title='Địa chỉ email', source='Hộp thư', text='Tên miền thật của công ty là maytrexanh.vn; email này dùng “maytrexanh-vn.co”.'),
                dict(id='vendor', title='Danh bạ nhà cung cấp', source='Phần mềm kế toán', text='Không có nhà cung cấp nào với số tài khoản này; chưa có hợp đồng hay đề nghị thanh toán.'),
                dict(id='policy', title='Quy trình chi', source='Quy chế tài chính', text='Mọi khoản chi trên 1.000 xu cần đề nghị thanh toán có chữ ký và xác minh qua số điện thoại đã đăng ký.')],
         options=[dict(id='verify', label='Không chuyển; gọi anh Tùng qua số đã đăng ký, báo IT, chuyển email vào mục lừa đảo', requires=['domain', 'policy'], quality='good', stars=5, reward=30,
                       review='Anh đang ngồi quán cà phê chứ họp hành gì! Email giả đấy. Cảm ơn em đã giữ được 3.000 xu của công ty.',
                       outcome='IT chặn tên miền giả và gửi cảnh báo toàn công ty. Hai phòng khác cũng nhận email tương tự nhưng đã được cảnh báo kịp.',
                       perspectives=[dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Tôi không bao giờ bảo ai “đừng gọi” khi chuyển tiền. Nhớ nhé.'),
                                     dict(who='Bộ phận IT', emoji='🛡️', text='Một cuộc gọi xác minh rẻ hơn mọi phần mềm chống lừa đảo.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Quy trình chi tồn tại chính là cho những lúc bị hối như thế này.')]),
                  dict(id='transfer', label='Chuyển ngay, sếp đang gấp mà', quality='bad', stars=1, cost=80,
                       review='Anh chưa từng gửi email đó. Công ty mất 3.000 xu, và em bỏ qua mọi bước kiểm tra.',
                       outcome='Tiền đi vào tài khoản lừa đảo; ngân hàng chỉ phong tỏa lại được một phần. Bạn bị kỷ luật và trừ thưởng.',
                       perspectives=[dict(who='Ngân hàng', emoji='🏦', text='Lệnh hợp lệ từ tài khoản của khách, ngân hàng chỉ hỗ trợ tra soát sau đó.'),
                                     dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Tôi giận kẻ lừa đảo, nhưng cũng giận việc bỏ qua quy trình.')]),
                  dict(id='reply', label='Trả lời email hỏi “anh chắc chứ ạ?”', requires=['domain'], quality='ok',
                       outcome='Kẻ gian trả lời ngay “chắc chắn, nhanh lên”. May mà bạn chần chừ đến sáng và hỏi trực tiếp anh Tùng.',
                       perspectives=[dict(who='Bộ phận IT', emoji='🛡️', text='Hỏi lại qua chính email giả là hỏi kẻ lừa đảo. Hãy dùng kênh đã đăng ký.'), dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Tôi không bao giờ đòi chuyển tiền qua email. Lần sau cứ gọi thẳng số của tôi.')])],
         lesson='Yêu cầu chuyển tiền gấp + bí mật + kênh lạ = dấu hiệu lừa đảo. Luôn xác minh qua kênh đã đăng ký và theo quy trình chi.'),
    dict(id='CA-S08', title='Thực tập sinh làm đổ cà phê lên chứng từ gốc', npc=7, tone='gentle', min_day=2,
         opening='Na mếu máo: “Em lỡ tay đổ cà phê lên xấp hóa đơn gốc tháng này… mấy tờ nhòe hết số rồi ạ.”',
         swap='Bạn là thực tập sinh tuần đầu, sợ bị đuổi hơn sợ bất cứ thứ gì.',
         facts=[dict(id='damage', title='Xem xấp hóa đơn', source='Bàn của Na', text='Ba hóa đơn giấy bị nhòe phần số tiền; bản điện tử của hai tờ vẫn còn trên cổng tra cứu.'),
                dict(id='rule', title='Quy chế lưu trữ', source='Chị Hạnh', text='Chứng từ hư hỏng: lập biên bản, xin bản sao có xác nhận của bên phát hành, kẹp cùng bản gốc.'),
                dict(id='na', title='Chuyện của Na', source='Cô Lụa', text='Na ngồi ăn trưa tại bàn vì sợ về trễ, cốc cà phê để sát hồ sơ.')],
         options=[dict(id='process', label='Lập biên bản hư hỏng, tải lại bản điện tử, xin nhà cung cấp bản sao có xác nhận; chỉ Na chỗ để đồ uống và cách cất hồ sơ',
                       requires=['damage', 'rule'], quality='good', stars=5, reward=10,
                       review='Em tưởng tiêu rồi, ai ngờ có quy trình hẳn hoi. Từ nay cốc cà phê của em ở bàn bên kia 😅',
                       outcome='Đủ chứng từ thay thế trong hai ngày. Phòng kế toán dán thêm tấm biển “Khu hồ sơ — không đồ uống”.',
                       perspectives=[dict(who='Na · Thực tập', emoji='🧑‍🎓', text='Được chỉ cách sửa thay vì bị mắng, em nhớ bài học này lâu lắm.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Sự cố nhỏ xử lý đúng quy trình thì không thành chuyện lớn.')]),
                  dict(id='copy', label='Tự viết lại mấy tờ mới cho giống, khỏi phiền nhà cung cấp', quality='bad', stars=2, cost=30,
                       review='Chị Hạnh phát hiện chữ trên tờ viết lại khác hẳn hóa đơn điện tử. Cả hai đứa bị nhắc nhở.',
                       outcome='Chứng từ “viết lại” không có giá trị; phải xin lại bản sao từ đầu và giải trình thêm.',
                       perspectives=[dict(who='Anh Khải · Kiểm toán', emoji='🔎', text='Chứng từ lập lại là chuyện nghiêm trọng hơn chứng từ bị nhòe.'),
                                     dict(who='Na · Thực tập', emoji='😰', text='Em tưởng được giúp, hóa ra làm mọi chuyện rối hơn.')]),
                  dict(id='scold', label='Mắng Na trước cả phòng rồi tự đi xin lại bản sao', requires=['damage'], quality='ok', stars=3,
                       review='Chứng từ thì xong rồi, nhưng em không dám hỏi ai điều gì nữa.',
                       outcome='Hồ sơ được bổ sung, nhưng Na giấu luôn lỗi cộng nhầm tuần sau vì sợ bị mắng.',
                       perspectives=[dict(who='Na · Thực tập', emoji='😔', text='Em biết em sai, nhưng bị nói trước mọi người em chỉ muốn trốn.'),
                                     dict(who='Cô Lụa · Thủ quỹ', emoji='💵', text='Người mới sợ quá thì lỗi sau sẽ bị giấu đi.')])],
         lesson='Chứng từ hư hỏng thì lập biên bản và xin bản sao có xác nhận — không viết lại; và dạy người mới bằng quy trình, không bằng nỗi sợ.'),
    dict(id='CA-S09', title='Phong bì “cảm ơn” trong giỏ quà nhà cung cấp', npc=5, tone='tense', min_day=3,
         opening='Giỏ quà của một xưởng đan gửi “phòng kế toán”, dưới đáy có phong bì 300 xu ghi: “Nhờ em đẩy nhanh thanh toán tháng này.”',
         facts=[dict(id='env', title='Mở giỏ quà', source='Bàn bạn', text='Giỏ có trà, bánh và một phong bì ghi tên bạn, kèm danh thiếp giám đốc xưởng.'),
                dict(id='policy', title='Quy định quà tặng', source='Phòng hành chính', text='Quà dưới 100 xu dùng chung được; tiền mặt, quà lớn phải trả lại và báo trưởng phòng.'),
                dict(id='pay', title='Lịch thanh toán', source='Phần mềm kế toán', text='Hóa đơn của xưởng này đến hạn ngày 25, đã xếp lịch trả đúng hạn.')],
         options=[dict(id='return', label='Trả lại phong bì kèm lời cảm ơn, báo chị Hạnh; giỏ trà bánh để cả phòng dùng chung, thanh toán vẫn theo lịch',
                       requires=['env', 'policy'], quality='good', stars=5, reward=15,
                       review='Nhận lại phong bì kèm lời nhắn rất lịch sự. Lần sau bên tôi chỉ gửi trà thôi, hẹn trả đúng ngày là quý rồi.',
                       outcome='Xưởng hiểu chuyện, quan hệ vẫn tốt. Chị Hạnh kể chuyện này trong buổi họp như một ví dụ đẹp.',
                       perspectives=[dict(who='Chủ xưởng đan', emoji='🧺', text='Tôi chỉ sợ bị trả chậm. Biết lịch rõ ràng thì chẳng cần phong bì.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Người giữ tiền mà nhận phong bì thì lịch thanh toán không còn công bằng.'),
                                     dict(who='Cô Lụa · Thủ quỹ', emoji='💵', text='Bánh ngon, cả phòng được chung vui mà lòng không áy náy.')]),
                  dict(id='keep', label='Giữ phong bì, dù sao cũng trả đúng hạn mà', quality='bad', stars=2, cost=60,
                       review='Nhận rồi thì tháng sau phải “ưu tiên” tiếp chứ nhỉ?',
                       outcome='Tháng sau xưởng đòi được trả trước hạn “như đã thỏa thuận”. Chuyện lộ ra, bạn bị kỷ luật và phải nộp lại tiền.',
                       perspectives=[dict(who='Anh Tùng · Giám đốc', emoji='👔', text='Tôi không cần biết bao nhiêu tiền — chỉ cần biết đã nhận.'),
                                     dict(who='Nhà cung cấp khác', emoji='😤', text='Hóa ra muốn được trả nhanh phải có phong bì.')]),
                  dict(id='refuse', label='Trả lại cả giỏ quà, gọi điện nói thẳng “bên em không nhận”', requires=['env'], quality='ok', stars=3,
                       review='Đúng là không nên, nhưng trả cả hộp trà bánh thì hơi phũ.',
                       outcome='Không ai nhận tiền; xưởng hơi ngượng và dè dặt khi làm việc với phòng kế toán.',
                       perspectives=[dict(who='Chủ xưởng đan', emoji='😶', text='Tôi sai khi gửi phong bì, nhưng hộp trà là tấm lòng thật.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Giữ nguyên tắc là đúng, thêm chút mềm mỏng thì trọn vẹn.')])],
         lesson='Tiền mặt, quà lớn từ nhà cung cấp: trả lại, báo cấp trên, và giữ lịch thanh toán công bằng cho mọi người.'),
    dict(id='CA-S10', title='Đồng nghiệp xin mượn tài khoản phần mềm kế toán', npc=3, tone='gentle', min_day=2,
         opening='Bảo: “Cho em mượn tài khoản phần mềm kế toán xíu thôi, em tự in công nợ khách, đỡ phải chờ anh chị.”',
         facts=[dict(id='rights', title='Quyền trong phần mềm', source='Phần mềm kế toán', text='Tài khoản của bạn sửa được bút toán, duyệt chi và xem bảng lương.'),
                dict(id='need', title='Bảo cần gì', source='Bảo', text='Bảo chỉ cần danh sách công nợ của 4 khách để đi thu tiền chiều nay.'),
                dict(id='it', title='Quy định của IT', source='Bộ phận IT', text='Không dùng chung mật khẩu. Nhân viên kinh doanh có thể được cấp quyền “chỉ xem công nợ”.')],
         options=[dict(id='report', label='Không đưa mật khẩu; in ngay báo cáo công nợ 4 khách cho Bảo và đề nghị IT cấp quyền “chỉ xem” cho phòng kinh doanh',
                       requires=['rights', 'need'], quality='good', stars=5,
                       review='Không mượn được tài khoản nhưng có báo cáo liền, tuần sau em còn có quyền xem riêng. Đỉnh!',
                       outcome='Bảo đi thu nợ đúng giờ; phòng kinh doanh được cấp quyền xem công nợ, phòng kế toán bớt hẳn việc in hộ.',
                       perspectives=[dict(who='Bảo · Kinh doanh', emoji='📈', text='Em chỉ cần số, không cần quyền duyệt chi. Giờ em hiểu vì sao.'),
                                     dict(who='Bộ phận IT', emoji='🛡️', text='Mỗi người một tài khoản thì mọi thao tác đều có chủ.')]),
                  dict(id='lend', label='Đưa mật khẩu cho nhanh, tin Bảo mà', quality='bad', stars=3, cost=25,
                       review='Em chỉ in công nợ thôi… mà lỡ bấm vào đâu đó, phiếu chi bị sửa ngày. Em xin lỗi!',
                       outcome='Một phiếu chi bị sửa nhầm dưới tên bạn; mất nửa ngày truy vết và giải trình với chị Hạnh.',
                       perspectives=[dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Nhật ký phần mềm ghi tên em, không ghi tên Bảo.'),
                                     dict(who='Bảo · Kinh doanh', emoji='🙈', text='Em không cố ý, nhưng đáng lẽ em không nên được bấm vào đó.')]),
                  dict(id='no', label='“Không được, quy định rồi.”', quality='ok', stars=3,
                       review='Ok không được thì thôi… nhưng chiều nay em lấy số ở đâu đi thu nợ?',
                       outcome='Mật khẩu an toàn, nhưng Bảo đi thu nợ tay trắng và khách hẹn sang tuần.',
                       perspectives=[dict(who='Bảo · Kinh doanh', emoji='😶', text='Em cần một cách khác, không chỉ một chữ “không”.'),
                                     dict(who='Chị Hạnh · Kế toán trưởng', emoji='🧮', text='Đúng nguyên tắc, nhưng in giúp một bản báo cáo đâu mất bao lâu.')])],
         lesson='Không dùng chung mật khẩu; đáp đúng nhu cầu thật của đồng nghiệp bằng báo cáo hoặc quyền phù hợp.'),
    dict(id='CA-S11', title='Giám đốc xin ứng quỹ mua quà sinh nhật', npc=1, tone='gentle', min_day=2,
         opening='Anh Tùng ghé phòng kế toán: “Cô Lụa ứng anh 300 xu mua quà sinh nhật vợ nhé, cuối tháng anh trả. Cứ ghi tạm là tiếp khách.”',
         swap='Bạn là giám đốc, quên ví ở nhà mà tối nay là sinh nhật vợ.',
         facts=[dict(id='rule', title='Quy chế quỹ', source='Quy chế tài chính', text='Tạm ứng cá nhân phải có giấy đề nghị ghi đúng mục đích, giám đốc ký và hoàn ứng trong 30 ngày.'),
                dict(id='cash', title='Hỏi cô Lụa', source='Cô Lụa', text='Quỹ đủ tiền, nhưng ghi “tiếp khách” thì cuối tháng không có hóa đơn nào để khớp.'),
                dict(id='form', title='Mẫu giấy tạm ứng', source='Tủ biểu mẫu', text='Mẫu giấy đề nghị tạm ứng có sẵn, điền mất hai phút.')],
         options=[dict(id='paper', label='Đưa anh Tùng giấy đề nghị tạm ứng cá nhân, ghi đúng “quà sinh nhật”, hẹn hoàn ứng cuối tháng',
                  requires=['rule', 'form'], quality='good', stars=5,
                  review='Hai phút điền giấy mà sổ sạch, cuối tháng khỏi ai hỏi han.',
                  outcome='Cô Lụa chi đúng quy trình; cuối tháng anh Tùng hoàn ứng, sổ quỹ khớp từng xu.',
                  perspectives=[dict(who='Anh Tùng · Giám đốc', emoji='🎁', text='Ghi đúng tên thì mình cũng yên tâm, khỏi ai nói ra nói vào.'),
                                dict(who='Cô Lụa · Thủ quỹ', emoji='💵', text='Có giấy là tôi chi ngay, không sợ lệch quỹ.'),
                                dict(who='Chị Hạnh · Kế toán trưởng', emoji='📒', text='Sếp cũng ứng như mọi người, thế mới công bằng.')]),
                  dict(id='guest', label='Ghi là tiếp khách cho nhanh, sếp mà',
                  quality='bad', stars=1,
                  review='Cuối năm kiểm toán hỏi hóa đơn tiếp khách, chẳng ai trả lời được.',
                  outcome='Khoản chi không có chứng từ bị loại khỏi chi phí; công ty nộp thêm thuế và bị nhắc nhở.',
                  perspectives=[dict(who='Anh Khải · Kiểm toán', emoji='🔍', text='Chi tiếp khách không có hóa đơn là thứ tôi tìm đầu tiên.'),
                                dict(who='Cô Lụa · Thủ quỹ', emoji='😟', text='Tôi ký sổ quỹ mà không biết giải thích sao.')]),
                  dict(id='refuse', label='Từ chối: “Quỹ công ty không cho mượn ạ”',
                  quality='ok', stars=3,
                  review='Đúng là không ghi bừa được, nhưng có cách hợp lệ sao không chỉ anh?',
                  outcome='Anh Tùng tự đi rút tiền, hơi phật ý với phòng kế toán.',
                  perspectives=[dict(who='Anh Tùng · Giám đốc', emoji='😤', text='Tôi đâu có định lấy không.'),
                                dict(who='Chị Hạnh · Kế toán trưởng', emoji='🤔', text='Từ chối thì dễ, chỉ cách làm đúng mới khó.')])],
         lesson='Giám đốc cũng tạm ứng bằng giấy, ghi đúng mục đích — sổ sạch thì ai cũng yên tâm.'),
    dict(id='CA-S12', title='Xin “xóa giùm” hóa đơn đã gửi khách', npc=3, tone='gentle', min_day=3,
         opening='Bảo chạy sang: “Khách đổi ý không lấy 20 giỏ mây nữa, chị xóa giùm em cái hóa đơn hôm qua nhé, coi như chưa có.”',
         swap='Bạn là nhân viên kinh doanh, sợ bị trừ doanh số vì đơn hủy.',
         facts=[dict(id='rule', title='Quy định hóa đơn điện tử', source='Sổ tay thuế', text='Hóa đơn đã gửi khách thì không xóa được; phải lập biên bản với khách và xuất hóa đơn điều chỉnh.'),
                dict(id='mail', title='Email của khách', source='Hộp thư', text='Khách xác nhận trả lại 20 giỏ, đồng ý ký biên bản.'),
                dict(id='stock', title='Hỏi chú Toàn', source='Kho', text='Hàng chưa rời kho, 20 giỏ vẫn còn nguyên trên kệ.')],
         options=[dict(id='adjust', label='Lập biên bản với khách, xuất hóa đơn điều chỉnh giảm, báo chú Toàn giữ hàng trong kho',
                  requires=['rule', 'mail'], quality='good', stars=5,
                  review='Giấy tờ rõ ràng, khách ký một lần là xong, em yên tâm.',
                  outcome='Doanh thu ghi đúng, kho khớp, cuối tháng không ai phải giải trình.',
                  perspectives=[dict(who='Bảo · Kinh doanh', emoji='🧺', text='Hóa ra không mất doanh số, chỉ cần làm đúng thủ tục.'),
                                dict(who='Chú Toàn · Thủ kho', emoji='📦', text='Hàng trên kệ, sổ kho cũng khớp. Tốt.'),
                                dict(who='Chị Hạnh · Kế toán trưởng', emoji='📒', text='Hóa đơn đã gửi thì không ai xóa được, nhớ nhé.')]),
                  dict(id='delete', label='Tìm cách xóa hóa đơn trên phần mềm, coi như chưa có',
                  quality='bad', stars=1,
                  review='Số hóa đơn nhảy cóc, cơ quan thuế hỏi thì cả phòng toát mồ hôi.',
                  outcome='Dãy số hóa đơn bị hụt; công ty phải giải trình với cơ quan thuế.',
                  perspectives=[dict(who='Chị Hạnh · Kế toán trưởng', emoji='😠', text='Hóa đơn đã gửi là đã nằm trên hệ thống thuế, xóa sao được.'),
                                dict(who='Anh Khải · Kiểm toán', emoji='🔍', text='Số hóa đơn nhảy cóc là chỗ tôi soi đầu tiên.')]),
                  dict(id='later', label='Bảo Bảo cứ để đó, cuối tháng tính',
                  quality='ok', stars=3,
                  review='Để lâu khách quên ký biên bản, em lại phải chạy đi xin.',
                  outcome='Cuối tháng mới xử lý, mất thêm hai ngày đi xin chữ ký.',
                  perspectives=[dict(who='Bảo · Kinh doanh', emoji='😅', text='Em tưởng xong rồi, ai ngờ còn phải chạy lại.'),
                                dict(who='Chị Hạnh · Kế toán trưởng', emoji='🕰️', text='Việc nhỏ dồn cuối tháng là thành việc lớn.')])],
         lesson='Hóa đơn đã gửi khách không xóa: lập biên bản, xuất hóa đơn điều chỉnh, để kho và sổ cùng khớp.'),
]

SPEC = dict(
    id=ID, prefix=PREFIX, category='office',
    meta=dict(short='Kế toán doanh nghiệp', place='Công ty CP Mây Tre Xanh', tagline='Từ tờ hóa đơn đến ngày khóa sổ — mọi con số đều có chứng từ.',
              icon='calculator', color='#3f8f6b', light='#e5f4ec', weather='Nắng nhẹ qua giàn mây', work='Hồ sơ', station='Bàn kế toán',
              greeting='Mỗi sáng có một khay chứng từ chờ đóng dấu và vài hồ sơ có hạn. Soi theo quy định tháng này — quy định đổi theo tháng đấy.',
              caption='Nợ bên trái, Có bên phải, sự thật ở giữa', map_label='11 · MÂY TRE XANH'),
    people=PEOPLE,
    staff=[('Nguyên', 'ca_filing', 'Xếp chứng từ theo số, chưa bao giờ để lạc phiếu.', 78, 88),
           ('Thư', 'ca_checker', 'Soát bút toán hai lần trước khi đưa bạn ký.', 70, 94),
           ('Phát', 'ca_filing', 'Scan hóa đơn nhanh như chớp, đôi khi quên kẹp phiếu nhập.', 86, 76),
           ('Mận', 'ca_cash', 'Thủ quỹ phụ, xếp tiền theo mệnh giá rất gọn.', 74, 90)],
    roles={'ca_filing': 'Thư ký chứng từ', 'ca_checker': 'Kiểm soát bút toán', 'ca_cash': 'Thủ quỹ phụ'},
    tip=0,
    physical=('ca_step', 'ca_submit', 'ca_stamp'),
    free_actions=(),
    no_tick=('ca_open', 'ca_hint', 'ca_circle', 'ca_overtime', 'ca_help', 'ca_cover', 'ca_break'),
    activity=('🧾', 'Bàn kế toán Mây Tre', [('Tiền gửi ngân hàng', 'Tài sản'), ('Phải trả người bán', 'Nguồn vốn'),
                                            ('Hàng hóa trong kho', 'Tài sản'), ('Vốn góp chủ sở hữu', 'Nguồn vốn')],
              ['Nhận & kiểm chứng từ', 'Định khoản Nợ/Có', 'Đối chiếu ngân hàng', 'Khóa sổ cuối tháng']),
    stories=[('Tủ hồ sơ của chị Hạnh', ('Chị Hạnh mở chiếc tủ gỗ cũ: “Chứng từ mười năm của công ty ở đây. Em biết vì sao chị giữ kỹ vậy không?”',
                                        'Sau một hồ sơ nữa, chị kể lần kiểm toán đầu tiên của công ty: một tờ phiếu chi thất lạc làm cả phòng thức ba đêm.',
                                        'Chị trao bạn chìa khóa tủ phụ: “Từ nay em giữ ngăn chứng từ ngân hàng.” Một lời tin tưởng nhỏ.')),
             ('Bà Sáu và bảng sao kê', ('Bà Sáu hỏi nhỏ: “Cháu chỉ bà cách dò sao kê được không? Kế toán nhà bà mới vào.”',
                                        'Bạn hoàn thành thêm một hồ sơ rồi ngồi cùng bà dò từng dòng: ngày, số tiền, nội dung chuyển khoản.',
                                        'Bà Sáu gửi tặng phòng kế toán một giỏ mây đan tay: “Để đựng hóa đơn cho khỏi lạc.”')),
             ('Tháng đầu tiên khóa sổ', ('Anh Tùng hỏi: “Khóa sổ là khóa cái gì? Anh tưởng là khóa tủ.”',
                                         'Bạn làm thêm một hồ sơ rồi vẽ cho anh sơ đồ: doanh thu, chi phí chảy vào 911, lãi chảy về 421.',
                                         'Anh Tùng dán sơ đồ lên tường phòng họp: “Tháng nào cũng vậy, không ai được đi tắt.”'))],
    review_asides=['Nợ Có rõ ràng, nhìn là muốn ký ngay.', 'Chứng từ kẹp gọn, số khớp tới từng xu.', 'Bàn giao có số liệu, người sau đọc là hiểu.',
                   'Sổ cân đẹp như bảng cửu chương.'],
    situations=SITUATIONS,
    employment=dict(
        postings=[
            dict(id='ca-hq', org='Công ty CP Mây Tre Xanh · Văn phòng chính', kind='company', title='Kế toán tổng hợp',
                 salary=(75, 100), probation_days=3, wants=['careful', 'numbers', 'tech'],
                 perks=['Thưởng khóa sổ đúng hạn', 'Kế toán trưởng kèm cặp', 'Ăn trưa cùng xưởng'],
                 culture='Doanh nghiệp sản xuất – thương mại 120 người, quy trình rõ, cuối tháng bận rộn nhưng không ai bị bỏ lại một mình.',
                 questions=['ca_invoice', 'ca_cutoff', 'ca_cash', 'mistake'], reference=True),
            dict(id='ca-workshop', org='Xưởng Mây Tre Xanh Phú Vinh · Chi nhánh sản xuất', kind='branch', title='Kế toán kho & giá thành',
                 salary=(65, 85), probation_days=2, wants=['careful', 'patience', 'calm'],
                 perks=['Gần làng nghề', 'Được học kiểm kê thực tế', 'Bụi mây hơi nhiều'],
                 culture='Xưởng 60 thợ đan, kho mây ẩm theo mùa; kế toán vừa ở bàn giấy vừa xuống kho đếm hàng.',
                 questions=['ca_cash', 'ca_tool', 'conflict'], reference=True),
            dict(id='ca-outsource', org='Dịch vụ Kế toán Sổ Sạch (nhận làm sổ cho Mây Tre Xanh)', kind='service', title='Kế toán dịch vụ',
                 salary=(55, 75), probation_days=1, wants=['learning', 'tech'],
                 perks=['Nhận việc ngay', 'Làm theo mẫu có sẵn', 'Lương thấp hơn'],
                 culture='Công ty dịch vụ nhỏ phụ trách sổ sách của nhiều khách hàng; Mây Tre Xanh là khách lớn nhất.',
                 questions=['ca_invoice'], reference=False),
        ],
        questions={
            'ca_invoice': dict(text='Hóa đơn đầu vào có tiền thuế GTGT tính sai 20 xu. Bạn làm gì?', options=[
                dict(id='request', label='Chưa ghi sổ, đề nghị nhà cung cấp lập hóa đơn điều chỉnh/thay thế', score=3, note='Chị Hạnh gật đầu: đúng quy trình, không tự sửa chứng từ của người khác.'),
                dict(id='edit', label='Tự sửa số trên bản in cho đúng rồi ghi sổ', score=0, note='Không ai được sửa hóa đơn của người bán.'),
                dict(id='ignore', label='20 xu thôi, bỏ qua cho nhanh', score=1, note='Nhỏ nhưng sai là sai; thuế khấu trừ sẽ lệch.')]),
            'ca_cutoff': dict(text='Ngày 30, sếp kinh doanh muốn ghi doanh thu cho lô hàng giao ngày 03 tháng sau.', options=[
                dict(id='period', label='Ghi doanh thu khi giao hàng; đề xuất báo cáo riêng “đơn đã ký chờ giao”', score=3, note='Đúng kỳ, lại có giải pháp cho người hỏi.'),
                dict(id='yes', label='Ghi luôn, dù sao cũng chỉ lệch vài ngày', score=0, note='Đây là lỗi cắt kỳ kiểm toán hay bắt nhất.'),
                dict(id='no', label='Từ chối, không giải thích', score=1, note='Đúng nguyên tắc nhưng khó hợp tác lâu dài.')]),
            'ca_cash': dict(text='Kiểm quỹ thấy thiếu tiền. Bước đầu tiên của bạn?', options=[
                dict(id='recount', label='Đếm lại có người chứng kiến, rà chứng từ chưa nhập, lập biên bản', score=3, note='Quy trình bảo vệ cả thủ quỹ lẫn công ty.'),
                dict(id='cover', label='Tự bù cho khớp để khỏi rắc rối', score=0, note='Che mất nguyên nhân thật.'),
                dict(id='blame', label='Báo ngay là thủ quỹ làm mất', score=0, note='Kết luận khi chưa có bằng chứng.')]),
            'ca_tool': dict(text='Bạn đối chiếu sổ tiền gửi với sao kê ngân hàng thế nào?', options=[
                dict(id='method', label='Dò theo ngày – số tiền – nội dung, liệt kê khoản lệch và phân loại', score=3, note='Có phương pháp, người khác kiểm lại được.'),
                dict(id='eye', label='Nhìn qua số dư cuối, gần bằng là được', score=1, note='Chênh lệch nhỏ thường giấu vấn đề lớn.'),
                dict(id='plug', label='Chỉnh sổ cho bằng số ngân hàng', score=0, note='Sổ phải phản ánh nghiệp vụ, không phải chép lại ngân hàng.')]),
        }),
    guide='Khay chứng từ: soi từng bộ theo quy định tháng này → khoanh chỗ sai → đóng dấu DUYỆT / TRÌNH SẾP / TRẢ LẠI → chốt khay. Hồ sơ: mở chứng từ → làm từng bước → bàn giao → nộp trước hạn. Đồng hồ chạy theo từng việc; 17:30 hết giờ.',
)
