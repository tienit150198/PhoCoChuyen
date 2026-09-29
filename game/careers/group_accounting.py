"""Kế toán tập đoàn · Sông Hồng Group (plugin career, employed job).

Consolidation work at the parent company of a small fictional group: SH Food
(100%), SH Logistics (70% — non-controlling interest 30%), SH Pack (100%) and
SH Nami, a foreign subsidiary reporting in "nami" (NM). A quarter-close cycle
of five game days: run the close calendar and chase reporting packages;
reconcile intercompany balances and find why they differ (goods in transit,
unrecorded invoice, cash in transit, FX); eliminate intercompany sales,
balances, unrealised profit in inventory and intercompany dividends; translate
the foreign subsidiary; tie a consolidation worksheet; compute the NCI share;
answer the auditors' PBC list; explain budget-vs-actual variances to the board.

Correct elimination entries go to the player's consolidation journal (a
balanced "sổ bút toán hợp nhất") which starts fresh every quarter — they are
never booked in any subsidiary's own ledger.

Consolidation rules, rates and thresholds are SIMPLIFIED GAME RULES inspired by
Vietnamese/international practice — not professional advice. All companies,
people, countries, currencies and numbers are fictional; money is "xu".
"""
from __future__ import annotations
import copy
from . import kit, office
from .. import procedures

ID = 'group_accounting'
PREFIX = 'ga_'
GROUP = 'Sông Hồng Group'

ACCOUNTS = [
    ('112', 'Tiền gửi ngân hàng'), ('131', 'Phải thu khách hàng'), ('156', 'Hàng tồn kho'), ('221', 'Đầu tư vào công ty con'),
    ('331', 'Phải trả người bán'), ('411', 'Vốn góp của chủ sở hữu'), ('413', 'Chênh lệch tỷ giá hối đoái'),
    ('421', 'Lợi nhuận sau thuế chưa phân phối'), ('429', 'Lợi ích cổ đông không kiểm soát'), ('511', 'Doanh thu bán hàng & dịch vụ'),
    ('515', 'Doanh thu hoạt động tài chính'), ('632', 'Giá vốn hàng bán'), ('635', 'Chi phí tài chính'),
    ('641', 'Chi phí bán hàng'), ('642', 'Chi phí quản lý doanh nghiệp'),
]
ACCOUNT_NAME = dict(ACCOUNTS)
ENTITIES = [
    dict(id='shh', name='Sông Hồng Holdings', short='Công ty mẹ', own=None, cur='xu', emoji='🏛️'),
    dict(id='food', name='Thực phẩm Sông Hồng', short='SH Food', own=100, cur='xu', emoji='🍜'),
    dict(id='logi', name='Vận tải Sông Hồng', short='SH Logistics', own=70, cur='xu', emoji='🚚'),
    dict(id='pack', name='Bao bì Sông Hồng', short='SH Pack', own=100, cur='xu', emoji='📦'),
    dict(id='nami', name='Sông Hồng Nami Ltd. (nước Nami)', short='SH Nami', own=100, cur='NM', emoji='🌏'),
]
ENT = {e['id']: e for e in ENTITIES}
SUBS = ['food', 'logi', 'pack', 'nami']

KINDS = {
    'calendar': dict(name='Lịch khóa sổ & gói báo cáo', emoji='🗓️', milestone='packages'),
    'ic_rec': dict(name='Đối chiếu công nợ nội bộ', emoji='🔁', milestone='ic'),
    'elim_sales': dict(name='Loại trừ doanh thu & công nợ nội bộ', emoji='✂️', milestone='elim'),
    'elim_upi': dict(name='Lãi chưa thực hiện trong hàng tồn kho', emoji='📦', milestone='elim'),
    'elim_div': dict(name='Loại trừ cổ tức nội bộ', emoji='💸', milestone='elim'),
    'fx_translate': dict(name='Chuyển đổi BCTC công ty con nước ngoài', emoji='💱', milestone='fx'),
    'worksheet': dict(name='Bảng tính hợp nhất', emoji='🧮', milestone='consol'),
    'nci': dict(name='Lợi ích cổ đông không kiểm soát', emoji='🧩', milestone='consol'),
    'pbc': dict(name='Danh mục PBC & câu hỏi kiểm toán', emoji='🗂️', milestone='board'),
    'variance': dict(name='Phân tích ngân sách cho HĐQT', emoji='📊', milestone='board'),
}
MILESTONES = [('packages', 'Gói báo cáo'), ('ic', 'Đối chiếu nội bộ'), ('fx', 'Chuyển đổi ngoại tệ'),
              ('elim', 'Bút toán loại trừ'), ('consol', 'Bảng hợp nhất & NCI'), ('board', 'Kiểm toán & HĐQT')]
MILESTONE_IDS = [m for m, _ in MILESTONES]
# Saves made before the matching board existed keep their dossiers: kit.mark_legacy moves those
# tasks into the legacy serial band and make_task rebuilds them from this old schedule.
LEGACY_SCHEDULE = [
    ['calendar', 'ic_rec', 'elim_sales', 'pbc'],
    ['ic_rec', 'fx_translate', 'elim_sales', 'calendar'],
    ['elim_upi', 'elim_div', 'fx_translate', 'ic_rec'],
    ['worksheet', 'nci', 'elim_upi', 'pbc'],
    ['variance', 'pbc', 'worksheet', 'nci'],
]
LEGACY_KIND_IDS = list(KINDS)
KINDS['match'] = dict(name='Bàn đối chiếu nội bộ', emoji='🔁', milestone='ic')
# Five game days make one quarter close. The matching board comes every day.
SCHEDULE = [
    ['match', 'calendar', 'elim_sales', 'pbc'],
    ['fx_translate', 'match', 'elim_sales', 'calendar'],
    ['match', 'elim_upi', 'elim_div', 'fx_translate'],
    ['worksheet', 'match', 'nci', 'pbc'],
    ['match', 'variance', 'worksheet', 'nci'],
]
KIND_IDS = list(KINDS)
HANDOVER = ('specific', 'short', 'none')
GEN = 2
FIXED = ('proc', 'docs', 'brief', 'variant', '_handover', '_value', 'lines', 'ic', 'gen')

PEOPLE = [
    ('Chị Mai Anh', 'Giám đốc tài chính tập đoàn (CFO)', 'Bình tĩnh, thích con số có nguồn, dị ứng với “số đẹp”.', 'picky'),
    ('Ông Đại', 'Chủ tịch HĐQT', 'Nói chuyện bằng biểu đồ, luôn hỏi “ngân hàng sẽ nghĩ gì?”.', 'bossy'),
    ('Anh Phong', 'Kế toán trưởng SH Logistics', 'Rành xe cộ, hay nộp gói báo cáo sát giờ, thích “tối ưu” doanh thu.', 'sour'),
    ('Chị Ngọc', 'Kế toán trưởng SH Food', 'Chu đáo, email lúc nào cũng có file đính kèm đúng tên.', 'warm'),
    ('Anh Kiên', 'Giám đốc tài chính SH Nami', 'Làm việc lệch múi giờ, nói tiếng Việt pha tiếng Nami.', 'genz'),
    ('Chị Thảo', 'Trưởng nhóm kiểm toán · Kiểm toán Sao Mai', 'Hỏi ngắn, cần bằng chứng dài.', 'quiet'),
    ('Linh', 'Kế toán mới ở SH Pack', 'Chăm chỉ nhưng đang quá tải, sai sót khi bị dồn việc.', 'warm'),
]


# ---------------------------------------------------------------- helpers (small duplicates of corp_accounting's)
def _n(v: int) -> str:
    return f'{v:,}'.replace(',', '.')


def _period(day: int) -> tuple[int, int, int]:
    """(quarter, phase 0..4, fiscal year) — five game days per quarter close."""
    return (day - 1) // 5 % 4 + 1, (day - 1) % 5, 2026 + (day - 1) // 20


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


def _short(eid: str) -> str:
    return ENT[eid]['short']


# ---------------------------------------------------------------- dossier generators
def g_calendar(rng, day, slot):
    q, _, year = _period(day)
    states = ['validated', 'received', 'late', 'partial']
    status = {s: rng.choice(states) for s in SUBS}
    if not any(v in ('late', 'partial') for v in status.values()):
        status[rng.choice(SUBS)] = 'late'
    label = {'validated': 'Đã nộp · đã kiểm khớp', 'received': 'Đã nộp · đang kiểm', 'late': 'CHƯA NỘP (quá hạn)', 'partial': 'Nộp thiếu phụ lục công nợ nội bộ'}
    notes = {'food': 'Chị Ngọc gửi đủ file, đặt tên chuẩn.', 'logi': 'Anh Phong hẹn “tối nay em gửi”.', 'pack': 'Linh đang một mình làm cả sổ lẫn thuế.',
             'nami': 'SH Nami chênh 5 múi giờ, đang chờ duyệt tỷ giá.'}
    board = [[_short(s), 'Ngày làm việc thứ 3', label[status[s]], notes[s] if status[s] in ('late', 'partial') else '—'] for s in SUBS]
    late = [s for s in SUBS if status[s] in ('late', 'partial')]
    who = late[0]
    contact = {'food': 'chị Ngọc', 'logi': 'anh Phong', 'pack': 'Linh', 'nami': 'anh Kiên'}[who]
    mailbox = {'food': 'ngoc.ketoan@shfood.example', 'logi': 'phong.kt@shlogistics.example', 'pack': 'linh.kt@shpack.example', 'nami': 'kien.cfo@shnami.example'}[who]
    missing = 'toàn bộ gói báo cáo' if status[who] == 'late' else 'phụ lục công nợ nội bộ'
    docs = [
        _doc('board', 'table', f'Bảng theo dõi gói báo cáo · Quý {q}/{year}', 'Nhóm hợp nhất', cols=['Đơn vị', 'Hạn nộp', 'Trạng thái', 'Ghi chú'], rows=board),
        _doc('policy', 'note', 'Quy chế khóa sổ tập đoàn', 'Chị Mai Anh', text='Công ty con khóa sổ riêng và nộp gói báo cáo (số liệu + phụ lục công nợ, giao dịch nội bộ) trước ngày làm việc thứ 3. '
             'Nhóm hợp nhất chỉ loại trừ khi hai bên đã đối chiếu khớp; bảng hợp nhất phải qua kiểm toán soát xét trước khi trình HĐQT.'),
        _doc('mail', 'email', f'Email từ {_short(who)}', contact[0].upper() + contact[1:], sender=mailbox, subject=f'Re: Gói báo cáo quý {q}',
             text={'food': 'Em đang đối chiếu lại công nợ với SH Pack, có một hóa đơn lệch — cho em thêm chút thời gian ạ.',
                   'logi': 'Anh đang kẹt chốt doanh thu cước, tối gửi. Số thì chắc chắn đẹp, yên tâm!',
                   'pack': 'Em xin lỗi, tuần này em vừa làm thuế vừa làm sổ, phần phụ lục nội bộ em chưa biết lấy số từ đâu…',
                   'nami': 'Bên mình chờ tỷ giá cuối kỳ được duyệt; có tỷ giá là gửi ngay.'}[who]),
    ]
    steps = [
        _order('order', 'Lịch khóa sổ hợp nhất', 'Sắp xếp các mốc khóa sổ quý của tập đoàn.',
               [('cutoff', 'Công ty con khóa sổ riêng'), ('package', 'Nộp gói báo cáo về tập đoàn'), ('ic', 'Đối chiếu công nợ & giao dịch nội bộ'),
                ('elim', 'Lập bút toán loại trừ'), ('consol', 'Lập & kiểm tra bảng hợp nhất'), ('audit', 'Kiểm toán soát xét, trình HĐQT')], rng,
               docs=['policy'], hints=['Không thể loại trừ khi hai bên chưa khớp số.', 'Kiểm toán soát xét trước khi trình HĐQT — bước cuối cùng.'],
               explain='Khóa sổ riêng → nộp gói → đối chiếu nội bộ → loại trừ → bảng hợp nhất → soát xét & trình HĐQT.'),
        _multi('late', 'Ai cần nhắc?', 'Chọn các công ty con cần nhắc nộp/bổ sung gói báo cáo.', [(s, f'{ENT[s]["emoji"]} {_short(s)}') for s in SUBS], late,
               docs=['board'], hints=['Nộp thiếu phụ lục cũng là chưa đủ để hợp nhất.'], explain='Cần nhắc: ' + ', '.join(_short(s) for s in late) + '.'),
        _choice('chase', 'Email nhắc việc', f'Chọn email gửi {contact} ({_short(who)}).',
                [('help', f'“Chào {contact}, gói quý {q} của {_short(who)} còn thiếu {missing}. Hạn chót mới là 17h ngày mai; nếu vướng phần nội bộ, em gửi mẫu và gọi 15 phút gỡ cùng nhé.”'),
                 ('threat', '“17h không có số thì em báo Chủ tịch.”'),
                 ('plug', '“Thôi, em tự ước tính số của bên mình cho kịp hợp nhất.”'),
                 ('wait', '“Cứ từ từ, xong lúc nào gửi lúc đó ạ.”')], 'help', rng, docs=['mail'],
                hints=['Email tốt: nói rõ thiếu gì, hạn mới, và đề nghị giúp.', 'Tự ước tính số của công ty con là tạo số không có chứng từ.'],
                explain='Nhắc rõ – hạn cụ thể – đề nghị hỗ trợ: gói về nhanh mà không ai mất mặt.'),
    ]
    return dict(npc=0, title=f'Khởi động khóa sổ quý {q}/{year}', opening=f'Quý {q} bắt đầu khóa sổ. Kiểm bảng gói báo cáo và nhắc đơn vị chậm giúp chị — lịch sát lắm.',
                brief=f'Chốt lịch khóa sổ hợp nhất quý {q}, xác định đơn vị chưa nộp đủ gói báo cáo và nhắc việc đúng cách.',
                docs=docs, steps=steps, value=len(late),
                handover=f'Quý {q}: lịch khóa sổ đã chốt; cần bổ sung từ {", ".join(_short(s) for s in late)}; đã email {contact} kèm hạn 17h mai và đề nghị hỗ trợ.')


IC_PAIRS = [
    dict(a='pack', b='food', what='thùng carton & màng co', kind='goods', npc=6),
    dict(a='logi', b='food', what='cước vận chuyển', kind='service', npc=2),
    dict(a='shh', b='logi', what='phí quản lý tập đoàn', kind='service', npc=2),
    dict(a='food', b='nami', what='nước mắm xuất khẩu', kind='fx', npc=4),
]
CAUSES = [('transit', 'Hàng đang đi đường: bên bán đã xuất, bên mua chưa nhận'), ('invoice', 'Hóa đơn bên bán đã lập, bên mua chưa ghi sổ'),
          ('cash', 'Tiền đang chuyển: bên mua đã trả, bên bán chưa nhận'), ('fx', 'Chênh lệch tỷ giá khi quy đổi ngoại tệ')]
FIXES = [('b_record', 'Bên mua ghi nhận hàng đang đi đường/hóa đơn còn thiếu'), ('cash_transit', 'Ghi nhận tiền đang chuyển, giảm phải thu tương ứng'),
         ('a_reval', 'Bên bán đánh giá lại khoản phải thu ngoại tệ theo tỷ giá cuối kỳ'), ('split', 'Mỗi bên chỉnh một nửa cho nhanh khớp'),
         ('plug', 'Ghi phần chênh vào “chi phí khác” ở cấp tập đoàn')]


def g_ic_rec(rng, day, slot):
    q, _, year = _period(day)
    pair = IC_PAIRS[rng.randrange(len(IC_PAIRS))]
    a, b = pair['a'], pair['b']
    cause = 'fx' if pair['kind'] == 'fx' else rng.choice(['transit', 'invoice', 'cash'] if pair['kind'] == 'goods' else ['invoice', 'cash'])
    inv = [rng.randrange(20, 80) * 10 for _ in range(3)]
    paid = rng.randrange(10, 40) * 10
    evidence = ''
    if cause == 'fx':
        r0, rc = rng.choice([25, 26]), rng.choice([23, 24])
        nm = [x // 10 for x in inv]
        a_rows = [[f'HĐXK-{i + 1:02d}', f'{nm[i]} NM × {r0}', _n(nm[i] * r0), ''] for i in range(3)]
        ra = sum(nm) * r0
        b_rows = [[f'HĐXK-{i + 1:02d}', f'{nm[i]} NM', _n(nm[i] * rc), ''] for i in range(3)]
        rb = sum(nm) * rc
        evidence = f'Tỷ giá lúc xuất hóa đơn: {r0} xu/NM. Tỷ giá cuối kỳ tập đoàn duyệt: {rc} xu/NM. SH Nami ghi nợ phải trả bằng NM; gói báo cáo quy đổi theo tỷ giá cuối kỳ.'
        fix, agreed = 'a_reval', rb
    else:
        a_rows = [[f'HĐ-{i + 1:02d}', f'Hóa đơn {pair["what"]}', _n(inv[i]), ''] for i in range(3)] + [['GBC-01', 'Nhận tiền thanh toán', '', _n(paid)]]
        b_rows = [[f'HĐ-{i + 1:02d}', f'Hóa đơn {pair["what"]}', _n(inv[i]), ''] for i in range(3)] + [['UNC-01', 'Chuyển tiền thanh toán', '', _n(paid)]]
        ra = sum(inv) - paid
        rb = ra
        if cause in ('transit', 'invoice'):
            b_rows = b_rows[:2] + b_rows[3:]
            rb = ra - inv[2]
            fix, agreed = 'b_record', ra
            evidence = (f'Phiếu giao hàng GH-{rng.randrange(100, 999)}: xuất kho {_short(a)} ngày 30, {_short(b)} ký nhận ngày 02 quý sau.' if cause == 'transit'
                        else f'Email hóa đơn HĐ-03 gửi ngày 28 tới địa chỉ cũ của phòng kế toán {_short(b)} — không ai mở.')
        else:
            extra = rng.randrange(1, ra // 20) * 10
            b_rows.append(['UNC-02', 'Chuyển tiền thanh toán (lập ngày 30)', '', _n(extra)])
            rb = ra - extra
            fix, agreed = 'cash_transit', rb
            evidence = f'UNC-02 của {_short(b)} lập 16h ngày 30; sao kê {_short(a)} ghi có ngày 01 quý sau.'
    diff = ra - rb
    docs = [
        _doc('a_led', 'table', f'{_short(a)} · Sổ phải thu {_short(b)}', _short(a), cols=['Chứng từ', 'Diễn giải', 'Phát sinh tăng', 'Đã thu'], rows=a_rows,
             foot=[['', 'Số dư phải thu', _n(ra), '']]),
        _doc('b_led', 'table', f'{_short(b)} · Sổ phải trả {_short(a)}' + (' (đã quy đổi)' if cause == 'fx' else ''), _short(b), cols=['Chứng từ', 'Diễn giải', 'Phát sinh tăng', 'Đã trả'],
             rows=b_rows, foot=[['', 'Số dư phải trả', _n(rb), '']]),
        _doc('evid', 'note', 'Bằng chứng thu thập', 'Nhóm hợp nhất', text=evidence),
    ]
    steps = [
        _number('diff', 'Chênh lệch', f'Phải thu theo {_short(a)} trừ phải trả theo {_short(b)} là bao nhiêu?', diff, docs=['a_led', 'b_led'],
                hints=['Lấy số dư phải thu trừ số dư phải trả.'], explain=f'{_n(ra)} − {_n(rb)} = {_n(diff)} xu.'),
        _choice('cause', 'Nguyên nhân', 'Chênh lệch này đến từ đâu?', CAUSES, cause, rng, docs=['evid'],
                hints=['So từng dòng hai sổ: dòng nào chỉ có một bên? Nếu mọi dòng đều có mà số tiền lệch đều nhau, nghĩ tới tỷ giá.'],
                explain=dict(CAUSES)[cause] + '.'),
        _choice('fix', 'Cách xử lý', 'Bên nào điều chỉnh, điều chỉnh gì?', FIXES, fix, rng,
                hints=['Người sửa là bên còn thiếu nghiệp vụ; không “chia đôi” chênh lệch.'],
                explain={'b_record': 'Bên mua ghi nhận nghiệp vụ còn thiếu theo chứng từ của bên bán.',
                         'cash_transit': 'Tiền đã rời bên mua: ghi nhận tiền đang chuyển để hai bên khớp tại ngày khóa sổ.',
                         'a_reval': 'Khoản phải thu ngoại tệ đánh giá lại theo tỷ giá cuối kỳ; chênh lệch vào lãi/lỗ tỷ giá của bên bán.'}[fix]),
        _number('agreed', 'Số dư thống nhất', 'Sau điều chỉnh, số dư nội bộ hai bên cùng xác nhận là bao nhiêu?', agreed,
                hints=['Là số dư của bên KHÔNG phải điều chỉnh.'], explain=f'Hai bên cùng xác nhận {_n(agreed)} xu — sẵn sàng để loại trừ.'),
    ]
    return dict(npc=pair['npc'], title=f'Đối chiếu nội bộ {_short(a)} ↔ {_short(b)}',
                opening=f'{_short(a)} báo phải thu {_n(ra)}, {_short(b)} chỉ ghi phải trả {_n(rb)}. Tìm giúp lý do trước khi loại trừ nhé!',
                brief=f'Đối chiếu công nợ {pair["what"]} giữa {_short(a)} và {_short(b)} quý {q}: tìm chênh lệch, nguyên nhân, bên điều chỉnh và số dư thống nhất.',
                docs=docs, steps=steps, value=agreed,
                handover=f'{_short(a)}↔{_short(b)}: lệch {_n(diff)} do {dict(CAUSES)[cause].lower()}; {dict(FIXES)[fix].lower()}; số dư thống nhất {_n(agreed)}.')


def g_elim_sales(rng, day, slot):
    q, _, year = _period(day)
    seller = rng.choice(['food', 'pack', 'logi'])
    group_buyers = [s for s in ('shh', 'food', 'pack', 'logi') if s != seller]
    outsiders = ['Công ty TNHH Sông Hồng Xanh', 'Siêu thị Làng Việt', 'HTX Hồng Sông', 'Chuỗi Bếp Nhà Mây']
    rows, ic_ids, total, owed = [], [], 0, 0
    buyers = rng.sample(group_buyers, 2) + rng.sample(outsiders, 3)
    rng.shuffle(buyers)
    for i, buyer in enumerate(buyers):
        amount = rng.randrange(20, 90) * 10
        inside = buyer in ENT
        name = ENT[buyer]['name'] if inside else buyer
        rows.append([f'S{i + 1}', name, _n(amount)])
        if inside:
            if not ic_ids:
                owed = amount // 2 // 10 * 10     # the first group buyer still owes half at quarter end
            ic_ids.append(f'S{i + 1}')
            total += amount
    conf = [[ENT[b]['name'], _n(owed) if i == 0 else '0'] for i, b in enumerate([x for x in buyers if x in ENT])]
    docs = [
        _doc('sales', 'table', f'{_short(seller)} · Sổ chi tiết doanh thu quý {q}', _short(seller), cols=['Mã', 'Khách hàng', 'Doanh thu'], rows=rows),
        _doc('group', 'table', 'Danh sách đơn vị trong tập đoàn', 'Pháp chế', cols=['Đơn vị', 'Tỷ lệ sở hữu của mẹ'],
             rows=[[e['name'], 'Công ty mẹ' if e['own'] is None else f'{e["own"]}%'] for e in ENTITIES]),
        _doc('conf', 'table', 'Xác nhận công nợ nội bộ cuối quý (đã khớp)', 'Nhóm hợp nhất', cols=['Bên mua', f'Còn nợ {_short(seller)}'], rows=conf,
             note='Toàn bộ hàng/dịch vụ mua nội bộ đã được bán ra ngoài hoặc dùng hết trong quý — không có lãi chưa thực hiện.'),
    ]
    steps = [
        _multi('pick', 'Lọc giao dịch nội bộ', 'Tick các dòng doanh thu bán cho đơn vị TRONG tập đoàn.', [(r[0], f'{r[0]} · {r[1]} · {r[2]}') for r in rows], ic_ids,
               docs=['sales', 'group'], hints=['Đối chiếu tên khách với danh sách đơn vị tập đoàn — cẩn thận tên na ná.'],
               explain='Giao dịch nội bộ: ' + ', '.join(ic_ids) + '. “Sông Hồng Xanh” hay “Hồng Sông” không thuộc tập đoàn.'),
        _entry('elim_rev', 'Loại trừ doanh thu – giá vốn', 'Loại doanh thu nội bộ và phần giá vốn tương ứng ở bên mua.', [['511', '632', total]],
               hints=['Tập đoàn không tự bán cho chính mình: giảm doanh thu (Nợ 511) và giảm giá vốn (Có 632) cùng số.'], explain=f'Nợ 511 / Có 632: {_n(total)}.'),
        _entry('elim_bal', 'Loại trừ công nợ nội bộ', 'Loại phải thu – phải trả nội bộ còn lại cuối quý.', [['331', '131', owed]], docs=['conf'],
               hints=['Công nợ nội bộ: Nợ 331 (giảm phải trả) / Có 131 (giảm phải thu).', 'Chỉ lấy số dư đã xác nhận khớp.'], explain=f'Nợ 331 / Có 131: {_n(owed)}.'),
    ]
    return dict(npc=3 if seller == 'food' else 0, title=f'Loại trừ giao dịch nội bộ của {_short(seller)}',
                opening=f'Sổ doanh thu {_short(seller)} đây. Nhớ lọc kỹ, có khách tên na ná tập đoàn mình đấy!',
                brief=f'Lọc doanh thu nội bộ của {_short(seller)} trong quý {q}, rồi lập bút toán loại trừ doanh thu – giá vốn và công nợ nội bộ.',
                docs=docs, steps=steps, value=total,
                handover=f'{_short(seller)} quý {q}: doanh thu nội bộ {_n(total)} ({", ".join(ic_ids)}) → Nợ 511/Có 632; công nợ {_n(owed)} → Nợ 331/Có 131.')


def g_elim_upi(rng, day, slot):
    q, _, year = _period(day)
    seller = rng.choice(['food', 'pack'])
    buyer = rng.choice([s for s in ('food', 'pack', 'logi') if s != seller])
    sale = rng.choice([800, 1000, 1200, 1500, 2000])
    margin = rng.choice([20, 25, 30])
    left = rng.randrange(2, sale // 40) * 20
    upi = left * margin // 100
    docs = [
        _doc('ic', 'kv', f'Giao dịch nội bộ quý {q}', _short(seller), rows=[['Bên bán', ENT[seller]['name']], ['Bên mua', ENT[buyer]['name']],
                                                                          ['Doanh thu nội bộ', f'{_n(sale)} xu'], ['Giá vốn của bên bán', f'{_n(sale * (100 - margin) // 100)} xu'],
                                                                          ['Tỷ suất lãi gộp trên giá bán', f'{margin}%']]),
        _doc('stock', 'kv', f'{_short(buyer)} · Tồn kho cuối quý', _short(buyer), rows=[['Hàng mua từ ' + _short(seller) + ' còn trong kho', f'{_n(left)} xu (theo giá mua nội bộ)'],
                                                                                     ['Phần đã bán ra ngoài', f'{_n(sale - left)} xu']]),
        _doc('rule', 'note', 'Nguyên tắc lãi nội bộ', 'Chị Mai Anh', text='Lãi chỉ “thực hiện” khi hàng đã bán cho khách ngoài tập đoàn. '
             'Phần hàng nội bộ còn tồn cuối kỳ chứa lãi của bên bán: loại khỏi hàng tồn kho và cộng lại vào giá vốn hợp nhất.'),
    ]
    steps = [
        _entry('elim_rev', 'Loại trừ doanh thu nội bộ', 'Loại toàn bộ doanh thu – giá vốn của giao dịch nội bộ.', [['511', '632', sale]], docs=['ic'],
               hints=['Doanh thu nội bộ: Nợ 511 / Có 632 cùng số tiền giao dịch.'], explain=f'Nợ 511 / Có 632: {_n(sale)}.'),
        _number('upi', 'Lãi chưa thực hiện', 'Lãi nội bộ còn nằm trong hàng tồn kho cuối kỳ là bao nhiêu?', upi, docs=['stock', 'rule'],
                hints=['Chỉ tính phần hàng còn tồn, không tính phần đã bán ra ngoài.', 'Lãi chưa thực hiện = hàng tồn theo giá nội bộ × tỷ suất lãi gộp.'],
                explain=f'{_n(left)} × {margin}% = {_n(upi)} xu.'),
        _entry('elim_upi', 'Loại lãi khỏi hàng tồn kho', 'Ghi bút toán loại lãi chưa thực hiện.', [['632', '156', upi]],
               hints=['Hàng tồn kho hợp nhất phải về giá gốc của tập đoàn → Có 156.', 'Lãi chưa thực hiện làm tăng giá vốn hợp nhất → Nợ 632.'],
               explain=f'Nợ 632 / Có 156: {_n(upi)}.'),
        _choice('why', 'Vì sao?', 'Vì sao phải loại khoản lãi này?',
                [('unrealised', 'Hàng vẫn nằm trong tập đoàn — chưa bán cho ai bên ngoài nên lãi chưa thực hiện'),
                 ('tax', 'Để giảm thuế thu nhập doanh nghiệp của tập đoàn'), ('seller', 'Vì bên bán tính giá quá cao'),
                 ('auditor', 'Vì kiểm toán yêu cầu, không có lý do kế toán')], 'unrealised', rng,
                hints=['Nghĩ tập đoàn như một công ty duy nhất: chuyển hàng giữa hai kho thì không có lãi.'], explain='Một thực thể không thể tự tạo lãi khi bán cho chính mình.'),
    ]
    return dict(npc=0, title=f'Lãi chưa thực hiện · {_short(seller)} → {_short(buyer)}',
                opening='Hàng nội bộ vẫn nằm trong kho mà lãi đã báo lên. Tính lại cho chị phần lãi chưa thực hiện nhé.',
                brief=f'Loại doanh thu nội bộ {_short(seller)} bán cho {_short(buyer)} và phần lãi chưa thực hiện còn nằm trong hàng tồn kho cuối quý {q}.',
                docs=docs, steps=steps, value=upi,
                handover=f'{_short(seller)}→{_short(buyer)} quý {q}: loại DT nội bộ {_n(sale)}; lãi chưa thực hiện {_n(left)}×{margin}% = {_n(upi)} → Nợ 632/Có 156.')


def g_elim_div(rng, day, slot):
    q, _, year = _period(day)
    sub = rng.choice(['logi', 'logi', 'food', 'pack'])
    own = ENT[sub]['own']
    div = rng.randrange(3, 15) * 100
    parent = div * own // 100
    nci = div - parent
    lines = [['515', '421', parent]] + ([['429', '421', nci]] if nci else [])
    docs = [
        _doc('res', 'note', f'Nghị quyết chia cổ tức · {_short(sub)}', 'Đại hội đồng cổ đông', text=f'{ENT[sub]["name"]} chia cổ tức bằng tiền tổng cộng {_n(div)} xu cho các cổ đông theo tỷ lệ sở hữu, đã chi trong quý {q}.'),
        _doc('own', 'table', 'Cơ cấu sở hữu', 'Pháp chế', cols=['Đơn vị', 'Công ty mẹ', 'Cổ đông khác'],
             rows=[[e['short'], f'{e["own"]}%', f'{100 - e["own"]}%' + (' (Quỹ đầu tư Cánh Cò)' if e['own'] < 100 else '')] for e in ENTITIES if e['own']]),
        _doc('gl', 'kv', 'Sổ công ty mẹ', 'Sông Hồng Holdings', rows=[['Doanh thu hoạt động tài chính (515) · cổ tức từ ' + _short(sub), f'{_n(parent)} xu'],
                                                                   ['Tiền gửi ngân hàng tăng', f'{_n(parent)} xu']]),
    ]
    steps = [
        _number('parent', 'Phần của công ty mẹ', 'Công ty mẹ nhận bao nhiêu cổ tức?', parent, docs=['res', 'own'],
                hints=['Cổ tức × tỷ lệ sở hữu của mẹ.'], explain=f'{_n(div)} × {own}% = {_n(parent)} xu.'),
        _number('nci', 'Phần cổ đông không kiểm soát', 'Cổ đông ngoài tập đoàn nhận bao nhiêu?', nci, docs=['own'],
                hints=['Phần còn lại của tổng cổ tức. Công ty con 100% thì phần này bằng 0.'], explain=f'{_n(div)} − {_n(parent)} = {_n(nci)} xu.'),
        _entry('elim', 'Bút toán loại trừ cổ tức', 'Loại cổ tức nội bộ khỏi báo cáo hợp nhất.', lines, docs=['gl'],
               hints=['Doanh thu tài chính của mẹ từ cổ tức nội bộ bị loại: Nợ 515.', 'Lợi nhuận chưa phân phối của con được “trả lại” (Có 421); phần của cổ đông ngoài ghi giảm 429.'],
               explain=f'{_lines_text(lines)}.'),
        _choice('why', 'Bản chất', 'Vì sao loại trừ cổ tức nội bộ?',
                [('pocket', 'Tiền chỉ chuyển từ túi này sang túi kia của cùng một tập đoàn'), ('tax', 'Vì cổ tức phải chịu thuế hai lần'),
                 ('small', 'Vì số tiền nhỏ, không trọng yếu'), ('cash', 'Vì tiền chưa về tài khoản')], 'pocket', rng,
                hints=['Nhìn tập đoàn như một công ty duy nhất.'], explain='Lợi nhuận của con đã nằm trong lợi nhuận hợp nhất; ghi thêm cổ tức là đếm hai lần.'),
    ]
    return dict(npc=2 if sub == 'logi' else 0, title=f'Cổ tức nội bộ từ {_short(sub)}',
                opening=f'{_short(sub)} vừa chia cổ tức {_n(div)} xu. Mẹ ghi doanh thu tài chính rồi đấy — hợp nhất xử lý giúp nhé.',
                brief=f'Tính phần cổ tức của mẹ và cổ đông không kiểm soát, lập bút toán loại trừ cổ tức nội bộ quý {q}.',
                docs=docs, steps=steps, value=div,
                handover=f'Cổ tức {_short(sub)} {_n(div)}: mẹ {_n(parent)}, CĐKKS {_n(nci)}. Đã ghi {_lines_text(lines)}.')


def g_fx_translate(rng, day, slot, rates=None):
    q, _, year = _period(day)
    tl = rng.randrange(5, 16) * 20
    cap = rng.randrange(4, 9) * 50
    rev = rng.randrange(15, 31) * 20
    profit = rng.randrange(2, 11) * 10
    exp = rev - profit
    ta = tl + cap + profit
    c = rng.choice([22, 23, 24, 25, 26])
    a = c + rng.choice([-1, 1])
    h = rng.choice([19, 20, 21])
    if rates:                                        # the day's group rate board (FX_HIST is the capital date)
        c, a, h = rates['closing'], rates['average'], FX_HIST
    tx = dict(ta=ta * c, tl=tl * c, rev=rev * a, exp=exp * a)
    diff = tx['ta'] - tx['tl'] - cap * h - (tx['rev'] - tx['exp'])
    docs = [
        _doc('tb', 'table', f'SH Nami · Bảng cân đối thử quý {q} (NM)', 'Anh Kiên', cols=['Chỉ tiêu', 'Số tiền (NM)'],
             rows=[['Tổng tài sản', _n(ta)], ['Nợ phải trả', _n(tl)], ['Vốn góp (góp khi thành lập)', _n(cap)], ['Doanh thu', _n(rev)], ['Chi phí', _n(exp)]]),
        _doc('rates', 'table', 'Tỷ giá tập đoàn duyệt', 'Chị Mai Anh', cols=['Loại tỷ giá', 'xu/NM'],
             rows=[['Tỷ giá cuối kỳ (ngày khóa sổ)', str(c)], ['Tỷ giá bình quân kỳ', str(a)], ['Tỷ giá lịch sử (ngày góp vốn)', str(h)]]),
        _doc('rule', 'note', 'Quy tắc chuyển đổi', 'Quy chế hợp nhất', text='Tài sản và nợ phải trả: tỷ giá cuối kỳ. Doanh thu, chi phí: tỷ giá bình quân kỳ. '
             'Vốn góp: tỷ giá lịch sử. Phần chênh để bảng cân đối cân là chênh lệch tỷ giá do chuyển đổi, trình bày trong vốn chủ sở hữu.'),
    ]
    lines = [('ta', 'Tài sản'), ('tl', 'Nợ phải trả'), ('rev', 'Doanh thu'), ('exp', 'Chi phí'), ('cap', 'Vốn góp')]
    steps = [
        _match('rates', 'Chọn tỷ giá', 'Mỗi chỉ tiêu dùng tỷ giá nào?', lines, [('closing', 'Cuối kỳ'), ('average', 'Bình quân kỳ'), ('historical', 'Lịch sử')],
               dict(ta='closing', tl='closing', rev='average', exp='average', cap='historical'), docs=['rule'],
               hints=['Số dư tại một thời điểm → tỷ giá thời điểm đó; số phát sinh trong kỳ → bình quân.'], explain='TS, nợ: cuối kỳ; DT, CP: bình quân; vốn góp: lịch sử.'),
        _fields('tr', 'Quy đổi', 'Quy đổi sang xu theo tỷ giá đã chọn.', [dict(id=k, label=label, unit='xu') for k, label in lines[:4]], tx, docs=['tb', 'rates'],
                hints=['Nhân số NM với đúng loại tỷ giá.'], explain=f'TS {ta}×{c}={_n(tx["ta"])}; nợ {tl}×{c}={_n(tx["tl"])}; DT {rev}×{a}={_n(tx["rev"])}; CP {exp}×{a}={_n(tx["exp"])}.'),
        _number('diff', 'Chênh lệch chuyển đổi', 'Chênh lệch tỷ giá do chuyển đổi = tài sản − nợ − vốn góp (tỷ giá lịch sử) − lợi nhuận quy đổi. Bao nhiêu? (có thể âm)',
                diff, hints=['Vốn góp quy đổi = vốn góp × tỷ giá lịch sử; lợi nhuận quy đổi = doanh thu − chi phí đã quy đổi.'],
                explain=f'{_n(tx["ta"])} − {_n(tx["tl"])} − {_n(cap * h)} − {_n(tx["rev"] - tx["exp"])} = {_n(diff)} xu.'),
        _choice('where', 'Trình bày', 'Khoản chênh lệch chuyển đổi này nằm ở đâu trên báo cáo hợp nhất?',
                [('equity', 'Vốn chủ sở hữu — chênh lệch tỷ giá hối đoái (413)'), ('pl', 'Lãi/lỗ trong kỳ (515/635)'),
                 ('liab', 'Nợ phải trả khác'), ('drop', 'Bỏ đi, miễn bảng cân đối cân')], 'equity', rng, docs=['rule'],
                hints=['Chênh lệch do chuyển đổi báo cáo, không phải do giao dịch thật phát sinh lãi/lỗ.'], explain='Trình bày trong vốn chủ sở hữu, không qua lãi/lỗ.'),
    ]
    return dict(npc=4, title=f'Chuyển đổi báo cáo SH Nami quý {q}', opening=(f'Báo cáo bên em bằng NM nè. Tỷ giá cuối kỳ hôm nay {c} xu/NM, quy đổi giúp em với 🙏' if rates else 'Báo cáo bên em bằng NM nè. Tỷ giá tháng này nhảy dữ lắm, quy đổi giúp em với 🙏'),
                brief=f'Chuyển đổi bảng cân đối thử của SH Nami từ NM sang xu theo tỷ giá tập đoàn duyệt, tính và trình bày chênh lệch chuyển đổi.',
                docs=docs, steps=steps, value=tx['ta'],
                handover=f'SH Nami quý {q}: TS {_n(tx["ta"])}, nợ {_n(tx["tl"])}, LN quy đổi {_n(tx["rev"] - tx["exp"])}, chênh lệch chuyển đổi {_n(diff)} vào 413.')


def g_worksheet(rng, day, slot):
    q, _, year = _period(day)
    ents = ['shh', 'food', 'pack']
    cap = {'food': rng.randrange(10, 30) * 100, 'pack': rng.randrange(8, 20) * 100}
    cap['shh'] = rng.randrange(60, 90) * 100
    invest = cap['food'] + cap['pack']
    data = {}
    for e in ents:
        cash, ar, stock = rng.randrange(50, 200) * 10, rng.randrange(40, 150) * 10, rng.randrange(40, 200) * 10
        ap = rng.randrange(30, 120) * 10
        inv = invest if e == 'shh' else 0
        rev = rng.randrange(200, 600) * 10
        cogs = rev * rng.choice([60, 65, 70]) // 1000 * 10
        ta = cash + ar + stock + inv
        re_ = ta - ap - cap[e]
        if re_ <= 0:
            cash += 100 - re_
            ta = cash + ar + stock + inv
            re_ = ta - ap - cap[e]
        data[e] = dict(rev=rev, cogs=cogs, cash=cash, ar=ar, stock=stock, inv=inv, ap=ap, cap=cap[e], re=re_, ta=ta)
    x = min(data['pack']['rev'], rng.randrange(40, 120) * 10)
    o = min(data['pack']['ar'], data['food']['ap'], rng.randrange(10, 40) * 10)
    elim = dict(rev=-x, cogs=-x, ar=-o, ap=-o, inv=-invest, cap=-invest)
    rows_def = [('rev', 'Doanh thu'), ('cogs', 'Giá vốn'), ('cash', 'Tiền'), ('ar', 'Phải thu'), ('stock', 'Hàng tồn kho'), ('inv', 'Đầu tư vào công ty con'),
                ('ta', 'TỔNG TÀI SẢN'), ('ap', 'Phải trả'), ('cap', 'Vốn góp'), ('re', 'LNST chưa phân phối')]
    rows = [[label] + [_n(data[e][k]) for e in ents] + [_n(elim[k]) if k in elim else ('?' if k == 'ta' else '')] for k, label in rows_def]
    cons = dict(rev=sum(data[e]['rev'] for e in ents) - x, cogs=sum(data[e]['cogs'] for e in ents) - x,
                ar=sum(data[e]['ar'] for e in ents) - o, cap=cap['shh'])
    ta_cons = sum(data[e]['ta'] for e in ents) - o - invest
    docs = [
        _doc('ws', 'table', f'Bảng tính hợp nhất quý {q}/{year}', 'Nhóm hợp nhất', cols=['Chỉ tiêu', 'Mẹ', 'SH Food', 'SH Pack', 'Loại trừ'], rows=rows, wide=True),
        _doc('elims', 'table', 'Bút toán loại trừ đã duyệt', 'Chị Mai Anh', cols=['Nội dung', 'Nợ', 'Có', 'Số tiền'],
             rows=[['Doanh thu SH Pack bán cho SH Food', '511', '632', _n(x)], ['Công nợ SH Food còn nợ SH Pack', '331', '131', _n(o)],
                   ['Khoản đầu tư của mẹ ↔ vốn góp của con', '411', '221', _n(invest)]]),
        _doc('note', 'note', 'Ghi chú hợp nhất', 'Quy chế', text='SH Food và SH Pack do mẹ góp 100% vốn khi thành lập — không có lợi thế thương mại, không có cổ đông không kiểm soát. '
             'Toàn bộ hàng nội bộ đã bán ra ngoài trong quý.'),
    ]
    steps = [
        _fields('cons', 'Cột hợp nhất', 'Điền số hợp nhất = cộng ba công ty + cột loại trừ.',
                [dict(id='rev', label='Doanh thu hợp nhất', unit='xu'), dict(id='cogs', label='Giá vốn hợp nhất', unit='xu'),
                 dict(id='ar', label='Phải thu hợp nhất', unit='xu'), dict(id='cap', label='Vốn góp hợp nhất', unit='xu')], cons, docs=['ws', 'elims'],
                hints=['Cộng ngang từng dòng rồi cộng cột loại trừ (số âm).', 'Vốn góp của con bị loại hết với khoản đầu tư của mẹ.'],
                explain=f'DT {_n(cons["rev"])}; GV {_n(cons["cogs"])}; phải thu {_n(cons["ar"])}; vốn góp {_n(cons["cap"])} (chỉ còn của mẹ).'),
        _number('ta', 'Tổng tài sản hợp nhất', 'Tổng tài sản hợp nhất là bao nhiêu?', ta_cons, docs=['ws'],
                hints=['Cộng tổng tài sản ba công ty rồi trừ các khoản loại trừ phía tài sản (phải thu nội bộ, khoản đầu tư).'],
                explain=f'{_n(sum(data[e]["ta"] for e in ents))} − {_n(o)} − {_n(invest)} = {_n(ta_cons)} xu.'),
        _choice('tie', 'Kiểm tra “ties”', 'Phép kiểm nào chứng minh bảng hợp nhất đã khớp?',
                [('bs', 'Tổng tài sản hợp nhất = tổng nợ phải trả + vốn chủ hợp nhất, và mỗi bút toán loại trừ có Nợ = Có'),
                 ('rev', 'Doanh thu hợp nhất = tổng doanh thu ba công ty'), ('profit', 'Lợi nhuận hợp nhất lớn hơn lợi nhuận công ty mẹ'),
                 ('cash', 'Tiền hợp nhất khác tổng tiền ba công ty')], 'bs', rng,
                hints=['Loại trừ đúng thì hai vế bảng cân đối vẫn bằng nhau.'], explain='Bảng cân đối hợp nhất cân và các bút toán loại trừ tự cân: bảng tính “ties”.'),
    ]
    return dict(npc=0, title=f'Bảng tính hợp nhất quý {q}/{year}', opening='Các bút toán loại trừ đã duyệt. Em hoàn thiện cột hợp nhất và kiểm tra khớp giúp chị trước 3 giờ nhé.',
                brief='Hoàn thiện bảng tính hợp nhất của mẹ, SH Food và SH Pack: cộng ngang, áp bút toán loại trừ và kiểm tra bảng cân đối khớp.',
                docs=docs, steps=steps, value=ta_cons,
                handover=f'Bảng hợp nhất quý {q}: DT {_n(cons["rev"])}, GV {_n(cons["cogs"])}, phải thu {_n(cons["ar"])}, vốn góp {_n(cons["cap"])}, tổng TS {_n(ta_cons)} — đã kiểm cân.')


def g_nci(rng, day, slot):
    q, _, year = _period(day)
    p = rng.randrange(60, 151) * 10
    e0 = rng.randrange(300, 600) * 10
    dv = rng.choice([0, 200, 300, 500])
    g = rng.randrange(300, 800) * 10 + p
    nci_p = p * 30 // 100
    close = e0 * 30 // 100 + nci_p - dv * 30 // 100
    docs = [
        _doc('logi', 'kv', 'SH Logistics · Số liệu năm', 'Anh Phong', rows=[['Lợi nhuận sau thuế', f'{_n(p)} xu'], ['Vốn chủ sở hữu đầu năm', f'{_n(e0)} xu'],
                                                                         ['Cổ tức đã chia trong năm (cho tất cả cổ đông)', f'{_n(dv)} xu']]),
        _doc('group', 'kv', 'Kết quả hợp nhất', 'Nhóm hợp nhất', rows=[['Lợi nhuận sau thuế hợp nhất (gồm 100% SH Logistics)', f'{_n(g)} xu']]),
        _doc('own', 'note', 'Cơ cấu sở hữu SH Logistics', 'Pháp chế', text='Sông Hồng Holdings sở hữu 70%, Quỹ đầu tư Cánh Cò sở hữu 30%. Mẹ kiểm soát nên hợp nhất toàn bộ.'),
    ]
    steps = [
        _number('nci_profit', 'Lợi nhuận của CĐKKS', 'Phần lợi nhuận năm thuộc cổ đông không kiểm soát?', nci_p, docs=['logi', 'own'],
                hints=['Lợi nhuận của công ty con × tỷ lệ của cổ đông ngoài.'], explain=f'{_n(p)} × 30% = {_n(nci_p)} xu.'),
        _number('parent_profit', 'Lợi nhuận của cổ đông mẹ', 'Lợi nhuận sau thuế hợp nhất thuộc về cổ đông công ty mẹ?', g - nci_p, docs=['group'],
                hints=['Lấy lợi nhuận hợp nhất trừ phần của cổ đông không kiểm soát.'], explain=f'{_n(g)} − {_n(nci_p)} = {_n(g - nci_p)} xu.'),
        _number('nci_close', 'Số dư CĐKKS cuối năm', 'Lợi ích cổ đông không kiểm soát cuối năm = 30% vốn chủ đầu năm + phần lãi − phần cổ tức đã nhận.', close,
                hints=['30% × vốn chủ đầu năm, cộng 30% lãi, trừ 30% cổ tức.'], explain=f'{_n(e0 * 30 // 100)} + {_n(nci_p)} − {_n(dv * 30 // 100)} = {_n(close)} xu.'),
        _choice('present', 'Trình bày', 'Lợi ích cổ đông không kiểm soát trình bày ở đâu trên bảng cân đối hợp nhất?',
                [('equity', 'Trong vốn chủ sở hữu, thành một dòng riêng'), ('liab', 'Trong nợ phải trả'), ('none', 'Không trình bày vì mẹ đã kiểm soát'),
                 ('note', 'Chỉ nêu trong thuyết minh')], 'equity', rng, hints=['Cổ đông thiểu số là chủ sở hữu, không phải chủ nợ.'],
                explain='Một dòng riêng trong vốn chủ sở hữu: tách phần của cổ đông mẹ và phần của cổ đông khác.'),
    ]
    return dict(npc=1, title=f'Phần của cổ đông thiểu số SH Logistics · {year}', opening='Quỹ Cánh Cò hỏi phần lãi của họ ở SH Logistics. Tính cho rõ, tôi không muốn cổ đông nào phàn nàn.',
                brief='Tính phần lợi nhuận và số dư lợi ích cổ đông không kiểm soát (30%) của SH Logistics, và lợi nhuận thuộc cổ đông mẹ.',
                docs=docs, steps=steps, value=close,
                handover=f'SH Logistics: LN CĐKKS {_n(nci_p)}, LN cổ đông mẹ {_n(g - nci_p)}, số dư CĐKKS cuối năm {_n(close)} — trình bày trong vốn chủ sở hữu.')


PBC = [('bank', 'Thư xác nhận số dư ngân hàng'), ('count', 'Biên bản kiểm kê hàng tồn kho cuối kỳ'), ('ic', 'Biên bản đối chiếu công nợ nội bộ'),
       ('loan', 'Hợp đồng vay & lịch trả nợ'), ('fa', 'Sổ TSCĐ & bảng tính khấu hao'), ('div', 'Nghị quyết chia cổ tức của công ty con')]
PROVIDERS = [('bankdirect', 'Ngân hàng gửi thẳng cho kiểm toán (tập đoàn chỉ ký thư đề nghị)'), ('wh', 'Kho & kế toán kho từng công ty con'),
             ('gl', 'Nhóm kế toán hợp nhất (bạn)'), ('legal', 'Phòng pháp chế — lưu hợp đồng gốc'), ('fa', 'Kế toán TSCĐ từng công ty'),
             ('sec', 'Thư ký HĐQT công ty con')]
PBC_KEY = dict(bank='bankdirect', count='wh', ic='gl', loan='legal', fa='fa', div='sec')
QUERIES = [
    ('Vì sao phải thu nội bộ SH Pack → SH Food tăng 40% so với quý trước?',
     'Từ tháng 2 SH Food mua thùng carton theo hợp đồng khung mới với SH Pack; em gửi hợp đồng, bảng kê hóa đơn và biên bản đối chiếu công nợ.'),
    ('Vì sao chi phí vận chuyển của SH Logistics tăng mạnh trong quý?',
     'Giá dầu tăng và thêm tuyến lạnh cho SH Food; em gửi bảng kê nhiên liệu theo tháng và phụ lục hợp đồng tuyến mới.'),
    ('Vì sao lỗ tỷ giá quý này lớn?',
     'Đồng NM mất giá so với xu; em gửi bảng đánh giá lại khoản phải thu ngoại tệ và tỷ giá tập đoàn duyệt từng tháng.'),
]


def g_pbc(rng, day, slot):
    q, _, year = _period(day)
    items = rng.sample(PBC, 4)
    pbt = rng.randrange(200, 600) * 20
    mat = pbt * 5 // 100
    material = rng.random() < .5
    mis = mat + rng.randrange(1, 10) * 10 if material else max(10, mat - rng.randrange(1, 10) * 10)
    query, good = QUERIES[rng.randrange(len(QUERIES))]
    docs = [
        _doc('list', 'table', f'Danh mục PBC quý {q} · Kiểm toán Sao Mai', 'Chị Thảo', cols=['Mã', 'Tài liệu kiểm toán cần'], rows=[[i, label] for i, label in items]),
        _doc('mat', 'note', 'Mức trọng yếu', 'Chị Thảo', text=f'Lợi nhuận trước thuế hợp nhất dự kiến: {_n(pbt)} xu. Mức trọng yếu tổng thể = 5% lợi nhuận trước thuế. '
             f'Sai sót kiểm toán phát hiện: chi phí lãi vay chưa trích trước {_n(mis)} xu.'),
        _doc('query', 'email', 'Câu hỏi của kiểm toán', 'Chị Thảo', sender='thao@kiemtoansaomai.example', subject='Câu hỏi soát xét', text=query),
    ]
    steps = [
        _match('match', 'Ai cung cấp?', 'Mỗi tài liệu PBC lấy từ đâu?', items, PROVIDERS, {i: PBC_KEY[i] for i, _ in items}, docs=['list'],
               hints=['Thư xác nhận ngân hàng phải đi thẳng từ ngân hàng tới kiểm toán để đảm bảo độc lập.', 'Đối chiếu nội bộ do nhóm hợp nhất lập.'],
               explain='; '.join(f'{label} → {dict(PROVIDERS)[PBC_KEY[i]]}' for i, label in items) + '.'),
        _number('mat', 'Mức trọng yếu', 'Mức trọng yếu tổng thể là bao nhiêu?', mat, docs=['mat'], hints=['5% × lợi nhuận trước thuế.'], explain=f'5% × {_n(pbt)} = {_n(mat)} xu.'),
        _choice('material', 'Sai sót có trọng yếu?', f'Sai sót {_n(mis)} xu so với mức trọng yếu thế nào?',
                [('yes', 'Vượt/bằng ngưỡng trọng yếu — phải điều chỉnh trước khi phát hành'), ('no', 'Dưới ngưỡng — ghi vào bảng chênh lệch chưa điều chỉnh, vẫn nên sửa nếu dễ')],
                'yes' if material else 'no', rng, hints=['So sánh trực tiếp với mức trọng yếu vừa tính.'],
                explain=('Sai sót ≥ trọng yếu: điều chỉnh sổ.' if material else 'Dưới trọng yếu: liệt kê vào tổng hợp chênh lệch; HĐQT xác nhận trong thư giải trình.')),
        _choice('reply', 'Trả lời kiểm toán', f'Kiểm toán hỏi: “{query}”',
                [('evidence', f'“{good}”'), ('vague', '“Do kinh doanh tốt hơn thôi ạ.”'), ('deflect', '“Chị hỏi công ty con giúp em nhé.”'),
                 ('later', '“Sau Tết em trả lời ạ.”')], 'evidence', rng, docs=['query'],
                hints=['Câu trả lời tốt có lý do cụ thể và tài liệu chứng minh kèm theo.'], explain='Kiểm toán cần lời giải thích có chứng từ, không cần lời hứa.'),
    ]
    return dict(npc=5, title=f'Danh mục PBC & câu hỏi kiểm toán quý {q}', opening='Gửi danh mục PBC. Cần trước thứ Sáu. Và một câu hỏi.',
                brief='Phân công tài liệu PBC cho đúng nơi cung cấp, tính mức trọng yếu, đánh giá sai sót kiểm toán phát hiện và trả lời câu hỏi soát xét.',
                docs=docs, steps=steps, value=pbt,
                handover=f'PBC quý {q}: đã phân công 4 tài liệu; trọng yếu {_n(mat)}; sai sót {_n(mis)} {"≥" if material else "<"} trọng yếu; đã trả lời kiểm toán kèm chứng từ.')


VAR_LINES = [('rev', 'Doanh thu', 1), ('cogs', 'Giá vốn', -1), ('sell', 'Chi phí bán hàng', -1), ('admin', 'Chi phí quản lý', -1), ('fin', 'Chi phí tài chính (lỗ tỷ giá)', -1)]
DRIVERS = {
    'rev': ('cold', 'Kho lạnh mới của SH Food khai trương trễ 1 tháng, mất một tháng doanh thu hàng đông lạnh'),
    'cogs': ('fuel', 'Giá dầu tăng 12%, chi phí vận chuyển của SH Logistics tăng'),
    'sell': ('ads', 'Chiến dịch quảng cáo Tết của SH Food chạy sớm hơn kế hoạch'),
    'admin': ('repair', 'SH Pack sửa chữa lớn dây chuyền in một lần'),
    'fin': ('fx', 'Đồng NM mất giá, lỗ tỷ giá khi đánh giá lại khoản phải thu SH Nami'),
}


def g_variance(rng, day, slot):
    q, _, year = _period(day)
    shown = ['rev', 'cogs'] + rng.sample(['sell', 'admin', 'fin'], 2)
    big = rng.choice(shown)
    budget, actual, var = {}, {}, {}
    for k, label, sign in VAR_LINES:
        if k not in shown:
            continue
        b = {'rev': rng.randrange(800, 1200) * 10, 'cogs': rng.randrange(450, 700) * 10}.get(k, rng.randrange(60, 150) * 10)
        u = rng.randrange(60, 120) * 10 if k == big else rng.randrange(1, 4) * 10
        v = -u if sign > 0 else u     # actual − budget; unfavourable = less revenue / more cost
        if k != big and rng.random() < .5:
            v = -v
        budget[k], actual[k], var[k] = b, b + v, v
    driver, text = DRIVERS[big]
    others = [DRIVERS[k] for k in shown if k != big]
    decoys = [('accounting', 'Kế toán ghi nhầm, sẽ sửa lại cho khớp ngân sách'), ('season', 'Do mùa vụ, năm nào cũng vậy')]
    label = {k: lbl for k, lbl, _ in VAR_LINES}
    docs = [
        _doc('bva', 'table', f'Ngân sách và thực tế quý {q}/{year}', 'Nhóm hợp nhất', cols=['Chỉ tiêu', 'Ngân sách', 'Thực tế'],
             rows=[[label[k], _n(budget[k]), _n(actual[k])] for k in shown]),
        _doc('notes', 'note', 'Ghi chú từ các công ty con', 'Các giám đốc tài chính', text=' • '.join([text] + [t for _, t in others[:2]])),
    ]
    options = [(driver, text)] + [(d, t) for d, t in others[:2]] + decoys[:1]
    steps = [
        _fields('var', 'Chênh lệch', 'Tính chênh lệch = thực tế − ngân sách (âm nếu thực tế nhỏ hơn).', [dict(id=k, label=label[k], unit='xu') for k in shown], var,
                docs=['bva'], hints=['Thực tế trừ ngân sách, giữ nguyên dấu.'], explain='; '.join(f'{label[k]}: {_n(var[k])}' for k in shown) + '.'),
        _choice('biggest', 'Bất lợi lớn nhất', 'Dòng nào có chênh lệch BẤT LỢI lớn nhất?', [(k, label[k]) for k in shown], big, rng,
                hints=['Bất lợi = doanh thu thấp hơn hoặc chi phí cao hơn ngân sách.', 'So độ lớn của các chênh lệch bất lợi.'],
                explain=f'{label[big]} lệch {_n(var[big])} xu — bất lợi lớn nhất.'),
        _choice('why', 'Giải thích', f'Nguyên nhân chính của chênh lệch {label[big].lower()}?', options, driver, rng, docs=['notes'],
                hints=['Chọn nguyên nhân có ghi chú từ công ty con chứng minh và đúng dòng chỉ tiêu.'], explain=text + '.'),
        _choice('comment', 'Bình luận cho HĐQT', 'Chọn đoạn bình luận trình HĐQT.',
                [('balanced', f'“{label[big]} lệch {_n(abs(var[big]))} xu so với ngân sách, chủ yếu do: {text.lower()}. Ảnh hưởng dự kiến và biện pháp: …; các dòng khác sát kế hoạch.”'),
                 ('spin', '“Kết quả quý vượt kỳ vọng, không có gì đáng lo.”'), ('blame', '“Do các công ty con làm việc yếu kém.”'),
                 ('jargon', '“Biến động phi tuyến tính của cấu trúc chi phí đa tầng trong bối cảnh vĩ mô.”')], 'balanced', rng,
                hints=['HĐQT cần: con số, nguyên nhân, tác động, việc sẽ làm — không tô hồng, không đổ lỗi.'], explain='Ngắn, có số, có nguyên nhân và hành động.'),
    ]
    return dict(npc=1, title=f'Báo cáo ngân sách quý {q} cho HĐQT', opening='Quý này số lệch ngân sách. Tôi cần một trang giải thích rõ ràng — HĐQT không đọc tiểu thuyết đâu.',
                brief=f'Tính chênh lệch ngân sách – thực tế quý {q}, tìm dòng bất lợi lớn nhất, nguyên nhân có căn cứ và viết bình luận cho HĐQT.',
                docs=docs, steps=steps, value=abs(var[big]),
                handover=f'Quý {q}: {label[big].lower()} lệch {_n(var[big])} do {text.lower()}; các dòng khác sát kế hoạch. Đã gửi bình luận cho HĐQT.')


# ---------------------------------------------------------------- the office day: luck, FX board, rules that shift
MODS = [
    dict(id='normal', min_day=1, weight=3, emoji='☀️', name='Ngày bình thường',
         text='Gói báo cáo về đủ, chị Mai Anh ngồi phòng bên cạnh.'),
    dict(id='late_package', min_day=2, weight=2, emoji='📦', name='Gói báo cáo về muộn',
         text='Anh Phong hẹn 10:00 mới gửi gói báo cáo SH Logistics. Làm việc khác trước, hoặc gọi giục.'),
    dict(id='fx_swing', min_day=2, weight=2, emoji='💱', name='Tỷ giá nhảy mạnh',
         text='Đồng NM biến động mạnh: công nợ với SH Nami lệch vì tỷ giá. Soi kỹ bảng tỷ giá hôm nay.'),
    dict(id='audit_visit', min_day=2, weight=2, emoji='🔎', name='Kiểm toán ngồi phòng họp',
         text='Cuối ngày chị Thảo xem giấy làm việc: không vết sửa thì được khen, sửa sai nhiều lần thì có thư quản lý.'),
    dict(id='board_meeting', min_day=3, weight=2, emoji='📊', name='Chị Mai Anh họp HĐQT',
         text='Xin gợi ý phải chờ 15 phút. Xong hết việc trong ngày, gần như không sai thì HĐQT khen.'),
    dict(id='crunch', forced_only=True, emoji='🔥', name='Ngày chốt hợp nhất',
         text='Cuối quý: hạn sớm hơn 30 phút, bảng đối chiếu dài hơn. Tăng ca được 18 xu và chị Mai Anh ghi nhận.'),
]
FORCED = {4: 'crunch'}
INTRO = {2: 'late_package', 3: 'fx_swing', 4: 'audit_visit'}
FX_HIST = 20                     # xu/NM on the day SH Nami's capital was contributed
WAIT_AT = 600                    # 10:00 — a late reporting package
CHASE_MIN = 10


def _mod(day: int) -> dict:
    return office.mod_of(ID, day, MODS, FORCED, INTRO)


def _fx_base(day: int) -> int:
    return 22 + kit.rng(ID, 'fx', max(1, day)).randrange(5)


def _fx_close(day: int) -> int:
    day = max(1, day)
    if _mod(day)['id'] == 'fx_swing':
        b = _fx_base(day - 1)
        return b + 3 if b <= 24 else b - 3
    return _fx_base(day)


def fx_rates(day: int) -> dict:
    """Group-approved NM rates for the day (deterministic): closing, yesterday's closing, average, historical."""
    close = _fx_close(day)
    prev = _fx_close(day - 1) if day > 1 else close
    return dict(closing=close, prev=prev, average=(close + prev) // 2, hist=FX_HIST, delta=close - prev)


TAGS = [('transit', '🚚', 'Hàng đi đường'), ('invoice', '📧', 'Hóa đơn chưa ghi'), ('cash', '💸', 'Tiền đang chuyển'),
        ('dup', '📑', 'Ghi trùng'), ('outside', '🏪', 'Không phải nội bộ')]
TAG_IDS = [x[0] for x in TAGS]
TAG_LABEL = {i: label for i, _, label in TAGS}
TAG_MIN_DAY = dict(transit=1, invoice=1, cash=1, dup=2, outside=3)
CAUSES_PAIR = [('fx', '💱', 'Lệch tỷ giá'), ('typo', '⌨️', 'Gõ nhầm số')]
CAUSE_IDS = [x[0] for x in CAUSES_PAIR]
MATCH_HINTS = dict(
    pair='Tìm dòng ở sổ bên kia cùng số chứng từ (bên mua có thể ghi số hóa đơn trong diễn giải).',
    typo='Cùng chứng từ nhưng hai số tiền đảo chữ số — ai đó gõ nhầm.',
    fx='Dòng bằng NM: so tỷ giá ghi trên hai dòng với bảng tỷ giá hôm nay.',
    transit='Dòng này chỉ có ở một bên. Xem phiếu giao hàng: bên mua nhận hàng ngày nào?',
    invoice='Dòng này chỉ có ở một bên. Xem nhật ký email hóa đơn.',
    cash='Khoản chuyển tiền chỉ có ở sổ bên mua. Xem sao kê ngân hàng của bên bán.',
    dup='Có hai dòng giống hệt nhau ở cùng một sổ không?',
    outside='Đọc diễn giải: người mua có phải công ty trong tập đoàn không?')
OUTSIDERS = ['Siêu thị Làng Việt', 'Chuỗi quán Phở Sông', 'Nhà hàng Bến Cảng', 'Cửa hàng Bếp Nhà Mây']


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _rule_cards(day: int) -> list:
    q, _, year = _period(day)
    singles = ['hàng đi đường', 'hóa đơn bên mua chưa ghi', 'tiền đang chuyển'] + (['ghi trùng'] if day >= 2 else []) + (
        ['không phải nội bộ'] if day >= 3 else [])
    cards = [dict(id='pair', emoji='🔗', title='Ghép cặp', text='Cùng một chứng từ ở hai sổ. Lệch số tiền thì chọn nguyên nhân: tỷ giá hay gõ nhầm.'),
             dict(id='single', emoji='🧩', title='Dòng chỉ có một bên', text=_cap(', '.join(singles)) + '.'),
             dict(id='who', emoji='🛠️', title='Ai điều chỉnh', text='Bên thiếu nghiệp vụ ghi bổ sung; lệch tỷ giá thì bên bán đánh giá lại. Không chia đôi, không ghi bù.'),
             dict(id='cutoff', emoji='📅', title=f'Khóa sổ quý {q}/{year}',
                  text=f'Ngày khóa sổ 30/{q * 3:02d}. Hàng, tiền tới nơi sau ngày này là “đang đi đường”, “đang chuyển”.')]
    if day >= 3:
        cards.append(dict(id='ic', emoji='🏢', title='Công nợ nội bộ', text='Chỉ giữa công ty mẹ và 4 công ty con. Bán cho khách ngoài → phải thu khách hàng, không loại trừ.'))
    if day >= 4:
        cards.append(dict(id='refs', emoji='🔎', title='Số chứng từ bên mua', text='Bên mua ghi theo số phiếu nhập của mình — số hóa đơn nằm trong diễn giải.'))
    return cards


def rules(day: int) -> list:
    """Rule cards for the day; a card is 'new' when it did not read the same yesterday."""
    today = _rule_cards(day)
    before = {x['id']: x['title'] + x['text'] for x in _rule_cards(day - 1)} if day > 1 else None
    for x in today:
        x['new'] = before is not None and before.get(x['id']) != x['title'] + x['text']
    return today


def tags_for(day: int) -> list:
    return [dict(id=i, emoji=e, label=label) for i, e, label in TAGS if TAG_MIN_DAY[i] <= day]


# ---------------------------------------------------------------- the intercompany matching board
def _match_slot(day: int) -> int:
    return SCHEDULE[(day - 1) % 5].index('match')


def _typo_amount(rng) -> int:
    v = rng.choice([x for x in range(21, 90) if x % 10 and x // 10 != x % 10])
    return v * 10


def _swap(v: int) -> int:
    s = str(v)
    return int(s[1] + s[0] + s[2:])


def g_match(rng, day, slot):
    q, _, year = _period(day)
    m = q * 3
    nxt = m % 12 + 1
    mod = _mod(day)['id']
    first = slot == _match_slot(day)
    late = mod == 'late_package' and first
    fxb = (mod == 'fx_swing' and first) or (day >= 4 and not late and rng.random() < 0.25)
    if fxb:
        pair = IC_PAIRS[3]
    elif late:
        pair = IC_PAIRS[1 + rng.randrange(2)]
    else:
        pair = IC_PAIRS[rng.randrange(3)]
    a, b = pair['a'], pair['b']
    A, B = _short(a), _short(b)
    what = pair['what']
    crunch = mod == 'crunch'
    n_pairs = min(6, 3 + (day - 1) // 3) + int(crunch)
    n_pay = max(1, n_pairs // 3)
    pool = [k for k in TAG_IDS if TAG_MIN_DAY[k] <= day and not (k == 'transit' and pair['kind'] == 'service')]
    rng.shuffle(pool)
    fresh = [k for k in pool if TAG_MIN_DAY[k] == day]
    pool = fresh + [k for k in pool if k not in fresh]
    n_single = (1 if day == 1 else 2 if day < 6 else 3) + int(crunch)
    singles = (pool * 2)[:n_single]
    typo = 1 if (day >= 2 and not fxb and (day == 2 or rng.random() < 0.5)) else 0
    rates = fx_rates(day)
    close = rates['closing']
    own_refs = day >= 4
    used = set()

    def num(lo=10, hi=99):
        while True:
            n = rng.randrange(lo, hi)
            if n not in used:
                used.add(n)
                return n

    inv_pfx = 'HĐXK' if fxb else 'HĐ'
    lines, docs = [], []

    def add(side, ref, dd, text, amount, kind, truth):
        lines.append(dict(side=side, ref=ref, date=f'{dd:02d}/{m:02d}', text=text, amount=int(amount), kind=kind, _truth=truth, _dd=dd))

    # --- invoices recorded by both sides
    n_inv = n_pairs - n_pay
    typo_at = rng.randrange(n_inv) if typo else -1
    inv_pairs = []
    for i in range(n_inv):
        ref = f'{inv_pfx}-{num():02d}'
        dd = rng.randrange(3, 26)
        db = min(28, dd + rng.randrange(0, 3))
        bref = f'PN-{num(100, 999)}' if own_refs else ref
        btext = f'Nhập theo {ref} · {what}' if own_refs else f'Hóa đơn {what}'
        if fxb:
            nm = rng.randrange(10, 36)
            r_inv = close + rng.choice([-3, -2, -1, 1, 2, 3])
            amt_a, amt_b = nm * r_inv, nm * close
            atext = f'{nm} NM × {r_inv} (tỷ giá ngày hóa đơn)'
            btext = (f'Nhập theo {ref} · ' if own_refs else '') + f'{nm} NM × {close} (quy đổi cuối kỳ)'
            cause = 'fx'
            why = f'{ref}: {nm} NM — {A} ghi theo tỷ giá ngày hóa đơn {r_inv}, SH Nami quy đổi theo tỷ giá cuối kỳ {close}. Bên bán đánh giá lại.'
        elif i == typo_at:
            amt_a = _typo_amount(rng)
            amt_b = _swap(amt_a)
            atext = f'Hóa đơn {what}'
            cause = 'typo'
            why = f'{ref}: {B} gõ {_n(amt_b)} thay vì {_n(amt_a)} — bên mua sửa theo hóa đơn.'
        else:
            amt_a = amt_b = rng.randrange(20, 90) * 10
            atext = f'Hóa đơn {what}'
            cause = None
            why = f'{ref}: hai bên cùng ghi {_n(amt_a)} xu.'
        inv_pairs.append(dict(ref=ref, dd=dd, amount=amt_a, text=atext, cause=cause))
        add('a', ref, dd, atext, amt_a, 'inv', dict(k='pair', mate=None, cause=cause, why=why, pid=i))
        add('b', bref, db, btext, amt_b, 'inv', dict(k='pair', mate=None, cause=cause, why=why, pid=i))
    # --- singles recorded by the seller only (goods in transit, unrecorded invoice, outside customer)
    extra_inv = 0
    for k, tag in enumerate(singles):
        if tag in ('transit', 'invoice', 'outside'):
            ref = f'{inv_pfx}-{num():02d}'
            amt = rng.randrange(20, 70) * 10
            if fxb:
                nm = rng.randrange(10, 30)
                amt = nm * close
            extra_inv += amt if tag != 'outside' else 0
            if tag == 'transit':
                dd = rng.choice([29, 30])
                gh = num(100, 999)
                add('a', ref, dd, f'Hóa đơn {what} (xuất kho {dd:02d}/{m:02d})', amt, 'inv',
                    dict(k='single', tag='transit', why=f'{ref}: hàng xuất {dd:02d}/{m:02d}, {B} nhận 02/{nxt:02d} → hàng đi đường, {B} ghi nhận bổ sung.'))
                docs.append(dict(title=f'Phiếu giao hàng GH-{gh}', source=A, text=f'Xuất kho {dd:02d}/{m:02d} theo {ref}. {B} ký nhận ngày 02/{nxt:02d}.'))
            elif tag == 'invoice':
                dd = rng.randrange(24, 29)
                add('a', ref, dd, f'Hóa đơn {what}', amt, 'inv',
                    dict(k='single', tag='invoice', why=f'{ref}: hóa đơn gửi nhầm hộp thư cũ → {B} chưa ghi sổ, cần ghi nhận bổ sung.'))
                docs.append(dict(title='Nhật ký email hóa đơn', source=A, text=f'{ref} gửi {dd:02d}/{m:02d} tới địa chỉ cũ của phòng kế toán {B} — chưa ai mở.'))
            else:
                who = OUTSIDERS[rng.randrange(len(OUTSIDERS))]
                dd = rng.randrange(5, 27)
                add('a', ref, dd, f'Hóa đơn bán cho {who}', amt, 'inv',
                    dict(k='single', tag='outside', why=f'{ref}: bán cho {who} — không phải công ty trong tập đoàn → chuyển sang phải thu khách hàng.'))
    # --- a duplicated line (same ref, same amount, recorded twice by one side)
    if 'dup' in singles:
        plain = [p for p in inv_pairs if p['cause'] is None]
        if plain:
            src = plain[rng.randrange(len(plain))]
            side = 'a' if rng.random() < 0.6 else 'b'
            root = next(x for x in lines if x['side'] == side and x['_truth'].get('pid') == inv_pairs.index(src))
            lines.append(dict(side=side, ref=root['ref'], date=root['date'], text=root['text'], amount=root['amount'], kind='inv', _dd=root['_dd'],
                              _truth=dict(k='single', tag='dup', of=None, why=f'{root["ref"]}: cùng số, cùng tiền, ghi hai lần → hủy dòng trùng.', copy=True)))
        else:                                                  # fx boards: every invoice differs, so no duplicate there
            singles = [x if x != 'dup' else 'cash' for x in singles]
    # --- payments (both sides) and cash in transit (buyer only); never more than half of what was invoiced
    total_inv = sum(p['amount'] for p in inv_pairs) + extra_inv
    n_cash = singles.count('cash')
    budget = total_inv // 2
    per = max(10, budget // max(1, n_pay + n_cash) // 10 * 10)
    for i in range(n_pay):
        ref = f'UNC-{num():02d}'
        dd = rng.randrange(8, 27)
        amt = rng.randrange(max(1, per // 20), per // 10 + 1) * 10
        if fxb:
            r_pay = close + rng.choice([-2, -1, 1, 2])
            nm = max(1, amt // r_pay)
            amt = nm * r_pay
            ta, tb = f'Nhận {nm} NM × {r_pay} (tỷ giá ngày nhận tiền)', f'Chuyển {nm} NM × {r_pay} (tỷ giá ngày chuyển)'
        else:
            ta, tb = f'Nhận tiền {B} thanh toán', f'Chuyển tiền cho {A}'
        why = f'{ref}: hai bên cùng ghi {_n(amt)} xu.'
        add('a', ref, dd, ta, amt, 'pay', dict(k='pair', mate=None, cause=None, why=why, pid=100 + i))
        add('b', ref, dd, tb, amt, 'pay', dict(k='pair', mate=None, cause=None, why=why, pid=100 + i))
    for _ in range(n_cash):
        ref = f'UNC-{num():02d}'
        amt = rng.randrange(max(1, per // 20), per // 10 + 1) * 10
        add('b', ref, 30, f'Chuyển tiền cho {A} (lập 16:00)', amt, 'pay',
            dict(k='single', tag='cash', why=f'{ref}: {B} chuyển chiều 30/{m:02d}, {A} nhận 01/{nxt:02d} → tiền đang chuyển, {A} ghi nhận.'))
        docs.append(dict(title=f'Sao kê ngân hàng {A}', source='Ngân hàng', text=f'{ref} của {B} ghi có ngày 01/{nxt:02d}.'))
    # --- a decoy: evidence about an invoice that both sides already recorded in the quarter
    if day >= 3 and inv_pairs:
        src = inv_pairs[rng.randrange(len(inv_pairs))]
        if pair['kind'] == 'service':
            docs.append(dict(title='Nhật ký email hóa đơn', source=A, text=f'{src["ref"]} gửi {src["dd"]:02d}/{m:02d}; {B} đã mở và ghi sổ ngày {min(28, src["dd"] + 1):02d}/{m:02d}.'))
        else:
            docs.append(dict(title=f'Phiếu giao hàng GH-{num(100, 999)}', source=A,
                             text=f'Xuất kho {src["dd"]:02d}/{m:02d} theo {src["ref"]}. {B} ký nhận ngày {min(28, src["dd"] + 2):02d}/{m:02d}.'))
    if fxb:
        docs.append(dict(title='Bảng tỷ giá tập đoàn hôm nay', source='Chị Mai Anh',
                         text=f'Cuối kỳ {close} xu/NM (hôm qua {rates["prev"]}). Gói báo cáo SH Nami quy đổi công nợ theo tỷ giá cuối kỳ.'))
    # --- ids by ledger order, then wire the truth
    out = []
    for side in ('a', 'b'):
        rows = [x for x in lines if x['side'] == side]
        rng.shuffle(rows)
        rows.sort(key=lambda x: x['_dd'])
        for i, x in enumerate(rows):
            x['id'] = f'{side}{i + 1}'
            out.append(x)
    by_pid = {}
    for x in out:
        if x['_truth']['k'] == 'pair':
            by_pid.setdefault(x['_truth']['pid'], {})[x['side']] = x['id']
    for x in out:
        tr = x['_truth']
        if tr['k'] == 'pair':
            tr['mate'] = by_pid[tr['pid']]['b' if x['side'] == 'a' else 'a']
        if tr.get('copy'):
            tr['of'] = next(y['id'] for y in out if y is not x and y['side'] == x['side'] and y['ref'] == x['ref'] and y['amount'] == x['amount']
                            and y['_truth']['k'] == 'pair')
        tr.pop('pid', None)
        tr.pop('copy', None)
        x.pop('_dd')
    out = [dict(id=x['id'], side=x['side'], ref=x['ref'], date=x['date'], text=x['text'], amount=x['amount'], kind=x['kind'], _truth=x['_truth'])
           for x in out]
    rng.shuffle(docs)
    docs = [_doc(f'e{i + 1}', 'note', d['title'], d['source'], text=d['text']) for i, d in enumerate(docs)]
    agreed = _solved_meter(out)['ra2']
    title = f'Đối chiếu nội bộ {A} ↔ {B}'
    opening = {True: f'Gói báo cáo SH Logistics hẹn 10:00 mới về. Có số là soát ngay giúp chị nhé — trưa nay phải loại trừ xong.',
               False: f'Hai sổ {A} và {B} lại lệch nhau. Ghép từng dòng, tìm lý do dòng lẻ, khớp rồi loại trừ giúp chị.'}[late]
    if fxb:
        opening = 'Tỷ giá NM nhảy, sổ SH Food và gói báo cáo SH Nami lệch hẳn. Soát từng dòng với bảng tỷ giá giúp chị nhé.'
    return dict(npc=0, title=title, opening=opening,
                brief=f'Ghép sổ phải thu {what} của {A} với sổ phải trả của {B} quý {q}: dòng khớp thì ghép, dòng lệch chọn nguyên nhân, '
                      f'dòng chỉ có một bên thì chọn lý do. Khớp hết thì loại trừ công nợ nội bộ.',
                docs=docs, lines=out, ic=dict(a=a, b=b, fx=fxb), value=agreed,
                handover=f'{A}↔{B}: {len(out)} dòng, số dư thống nhất {_n(agreed)} xu, đã loại trừ Nợ 331 / Có 131.')


def _sgn(x: dict) -> int:
    return 1 if x['kind'] == 'inv' else -1


def _meter_of(lines: list, board: dict) -> dict:
    """Both balances before and after the adjustments the resolved lines imply."""
    by = {x['id']: x for x in lines}
    ra = sum(_sgn(x) * x['amount'] for x in lines if x['side'] == 'a')
    rb = sum(_sgn(x) * x['amount'] for x in lines if x['side'] == 'b')
    da = db = 0
    for lid, st in board.items():
        x = by[lid]
        if st['k'] == 'pair':
            if x['side'] == 'b' and st['cause'] == 'typo':
                db += _sgn(x) * (by[st['mate']]['amount'] - x['amount'])
            if x['side'] == 'a' and st['cause'] == 'fx':
                da += _sgn(x) * (by[st['mate']]['amount'] - x['amount'])
        elif st['tag'] in ('transit', 'invoice'):
            db += _sgn(x) * x['amount']
        elif st['tag'] == 'cash':
            da += _sgn(x) * x['amount']
        elif x['side'] == 'a':
            da -= _sgn(x) * x['amount']
        else:
            db -= _sgn(x) * x['amount']
    return dict(ra=ra, rb=rb, ra2=ra + da, rb2=rb + db, gap=ra + da - rb - db)


def _truth_board(lines: list) -> dict:
    board = {}
    for x in lines:
        tr = x['_truth']
        board[x['id']] = dict(k='pair', mate=tr['mate'], cause=tr['cause']) if tr['k'] == 'pair' else dict(k='tag', tag=tr['tag'])
    return board


def _solved_meter(lines: list) -> dict:
    return _meter_of(lines, _truth_board(lines))


def _lines(t: dict) -> dict:
    return {x['id']: x for x in t['lines']}


def _group(t: dict, lid: str) -> list:
    """A line and its exact duplicates on the same side (any copy may be the one that gets paired)."""
    by = _lines(t)
    root = by[lid]['_truth'].get('of') or lid
    return [x['id'] for x in t['lines'] if x['id'] == root or x['_truth'].get('of') == root]


def _mate_ok(t: dict, aid: str, bid: str) -> bool:
    by, ga, gb = _lines(t), _group(t, aid), _group(t, bid)
    if any(t['board'].get(x, {}).get('k') == 'pair' for x in ga + gb):
        return False
    return any(by[x]['_truth'].get('mate') in gb for x in ga)


def _pair_root(t: dict, aid: str, bid: str) -> dict:
    by, gb = _lines(t), _group(t, bid)
    return next(by[x] for x in _group(t, aid) if by[x]['_truth'].get('mate') in gb)


def _tag_ok(t: dict, lid: str, tag: str) -> bool:
    g = _group(t, lid)
    if tag == 'dup':
        return len(g) > 1 and sum(1 for y in g if t['board'].get(y, {}).get('tag') == 'dup') < len(g) - 1
    tr = _lines(t)[lid]['_truth']
    return len(g) == 1 and tr['k'] == 'single' and tr['tag'] == tag


def _hint_key(t: dict, x: dict) -> str:
    tr = x['_truth']
    if tr['k'] == 'single':
        return tr['tag']
    if len(_group(t, x['id'])) > 1:
        return 'dup'
    return tr['cause'] or 'pair'


def _line(t: dict, lid) -> dict:
    x = next((y for y in t.get('lines') or [] if y['id'] == lid), None)
    kit.need(x, 'Sổ không có dòng này.')
    return x


def _waiting(t: dict, o: dict) -> bool:
    return type(t.get('wait')) is int and o['clock'] < t['wait']


def _left(t: dict) -> int:
    return sum(1 for x in t['lines'] if x['id'] not in t['board'])


def _miss(d: dict, o: dict, t: dict, text: str) -> dict:
    lunch = office.spend(o, office.COST['pair'] + office.COST['wrong'])
    t['mistakes'] += 1
    office.trust(o, -1)
    d['slips'] += 1
    return dict(message=' '.join(x for x in ('✗ ' + text, '(+20 phút soát lại)', lunch) if x), correct=False)


def _done_msg(t: dict, why: str, lunch: str) -> dict:
    left = _left(t)
    tail = f'Còn {left} dòng.' if left else ''
    return dict(message=' '.join(x for x in ('✓ ' + why, lunch, tail) if x), correct=True)


def _pair(d: dict, o: dict, t: dict, p: dict) -> dict:
    a, b = _line(t, p.get('a')), _line(t, p.get('b'))
    kit.need(a['side'] == 'a' and b['side'] == 'b', 'Chọn một dòng ở sổ bên bán và một dòng ở sổ bên mua.')
    kit.need(a['id'] not in t['board'] and b['id'] not in t['board'], 'Dòng này đã xử lý rồi.')
    cause = None
    if a['amount'] != b['amount']:
        cause = kit.one_of(p.get('cause'), CAUSE_IDS, 'Hai dòng lệch số tiền — chọn nguyên nhân: lệch tỷ giá hay gõ nhầm số.')
    office.need_open(o)
    kit.start_work(t)
    if not _mate_ok(t, a['id'], b['id']):
        return _miss(d, o, t, f'{a["ref"]} và {b["ref"]} không phải cùng một nghiệp vụ. Soát lại số chứng từ và diễn giải.')
    root = _pair_root(t, a['id'], b['id'])
    if cause is not None and cause != root['_truth']['cause']:
        tip = 'So tỷ giá trên hai dòng với bảng tỷ giá.' if root['_truth']['cause'] == 'fx' else 'Nhìn kỹ từng chữ số của hai bên.'
        return _miss(d, o, t, 'Đúng cặp, nhưng nguyên nhân lệch chưa đúng. ' + tip)
    lunch = office.spend(o, office.COST['pair'])
    t['board'][a['id']] = dict(k='pair', mate=b['id'], cause=cause)
    t['board'][b['id']] = dict(k='pair', mate=a['id'], cause=cause)
    d['matched'] += 1
    return _done_msg(t, root['_truth']['why'], lunch)


def _tag(d: dict, o: dict, t: dict, p: dict) -> dict:
    x = _line(t, p.get('line'))
    kit.need(x['id'] not in t['board'], 'Dòng này đã xử lý rồi.')
    tag = kit.one_of(p.get('tag'), TAG_IDS, 'Chọn lý do cho dòng lẻ.')
    office.need_open(o)
    kit.start_work(t)
    if not _tag_ok(t, x['id'], tag):
        if x['_truth']['k'] == 'pair' and len(_group(t, x['id'])) == 1:
            return _miss(d, o, t, f'{x["ref"]} có dòng đối ứng ở sổ bên kia — tìm cùng số chứng từ để ghép.')
        return _miss(d, o, t, f'“{TAG_LABEL[tag]}” chưa đúng với {x["ref"]}. Xem lại bằng chứng và quy định.')
    lunch = office.spend(o, office.COST['tag'])
    t['board'][x['id']] = dict(k='tag', tag=tag)
    d['tagged'] += 1
    why = x['_truth']['why'] if tag != 'dup' else f'{x["ref"]}: cùng số, cùng tiền, ghi hai lần → hủy dòng trùng.'
    return _done_msg(t, why, lunch)


GENERATORS = dict(calendar=g_calendar, ic_rec=g_ic_rec, elim_sales=g_elim_sales, elim_upi=g_elim_upi, elim_div=g_elim_div,
                  fx_translate=g_fx_translate, worksheet=g_worksheet, nci=g_nci, pbc=g_pbc, variance=g_variance)


def _legacy_kind(day: int, slot: int) -> str:
    row = LEGACY_SCHEDULE[(day - 1) % 5]
    return row[slot] if slot < len(row) else LEGACY_KIND_IDS[(day * 7 + slot * 3) % len(LEGACY_KIND_IDS)]


def _kind(day: int, slot: int) -> str:
    row = SCHEDULE[(day - 1) % 5]
    if slot < len(row):
        return row[slot]
    return 'match' if slot % 2 == 0 else LEGACY_KIND_IDS[(day * 7 + slot * 3) % len(LEGACY_KIND_IDS)]


def make_task(day: int, slot: int, serial: int) -> dict:
    if kit.legacy(serial):
        kind = _legacy_kind(day, slot)
        g = GENERATORS[kind](kit.rng(ID, day, slot, kind), day, slot)
        return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], variant=kind, brief=g['brief'], docs=g['docs'],
                             proc=g['steps'], proc_state=procedures.initial_state(), tips=[], handover=None,
                             _handover=g['handover'], _value=int(g.get('value', 0)))
    kind = _kind(day, slot)
    rng = kit.rng(ID, day, slot, kind)
    if kind == 'match':
        g = g_match(rng, day, slot)
        return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], variant='match', brief=g['brief'], docs=g['docs'],
                             proc=[], proc_state=procedures.initial_state(), tips=[], handover=None, _handover=g['handover'],
                             _value=int(g['value']), lines=g['lines'], ic=g['ic'], board={}, wait=None, late=None, gen=GEN)
    g = g_fx_translate(rng, day, slot, fx_rates(day)) if kind == 'fx_translate' else GENERATORS[kind](rng, day, slot)
    return kit.base_task(ID, day, slot, serial, g['npc'], g['title'], g['opening'], variant=kind, brief=g['brief'], docs=g['docs'],
                         proc=g['steps'], proc_state=procedures.initial_state(), tips=[], handover=None,
                         _handover=g['handover'], _value=int(g.get('value', 0)), late=None, gen=GEN)


def initial() -> dict:
    return dict(elim={}, entries=[], milestones=[], posted=0, quarters=0, done=0, day_posted=0, day_done=0,
                office=office.initial(), boards=0, matched=0, tagged=0, slips=0, day_work=[])


def _data(c: dict) -> dict:
    """Career data with every field of this version (older saves get the new ones here)."""
    d = kit.data(c)
    for k, v in initial().items():
        if k not in d:
            d[k] = copy.deepcopy(v)
    office.ensure(d)
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
    """Pairs or a compound voucher; see corp_accounting._entry_answer (duplicated on purpose)."""
    accts = {a['id'] for a in st['accounts']}
    bad = 'Mỗi dòng cần một tài khoản trong danh mục và số tiền nguyên dương.'
    deb, cre = {}, {}
    if isinstance(answer, dict):
        rows_d, rows_c = answer.get('debit'), answer.get('credit')
        kit.need(isinstance(rows_d, list) and isinstance(rows_c, list) and 1 <= len(rows_d) <= 6 and 1 <= len(rows_c) <= 6,
                 'Bút toán cần ít nhất 1 dòng Nợ và 1 dòng Có (tối đa 6 dòng mỗi bên).')
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
    kit.need(td == tc, f'Bút toán chưa cân: Tổng Nợ {_n(td)} ≠ Tổng Có {_n(tc)}.')
    kd, kc = _totals(st['_key'])
    if deb == kd and cre == kc:
        return [dict(debit=d, credit=c, amount=a) for d, c, a in st['_key']], ''
    if set(deb) == set(kd) and set(cre) == set(kc):
        diag = 'Tài khoản đã đúng, nhưng số tiền chưa khớp.'
    elif set(deb) == set(kd):
        diag = 'Bên Nợ đúng tài khoản; xem lại bên Có.'
    elif set(cre) == set(kc):
        diag = 'Bên Có đúng tài khoản; xem lại bên Nợ.'
    elif td == sum(kd.values()):
        diag = 'Tổng số tiền đúng rồi; xem lại tài khoản.'
    else:
        diag = ''
    ids = [a['id'] for a in st['accounts']]
    wrong = [dict(debit=ids[0], credit=ids[1], amount=1)]
    if procedures.check(st, wrong):
        wrong[0]['amount'] = 2
    return wrong, diag


def _post_lines(c: dict, t: dict, title: str, lines) -> None:
    d = kit.data(c)
    led = d['elim']
    for dr, cr, a in lines:
        led[dr] = led.get(dr, 0) + a
        led[cr] = led.get(cr, 0) - a
    d['elim'] = {k: v for k, v in led.items() if v}
    d['entries'] = (d['entries'] + [dict(day=c['day'], task=t['id'], title=title, lines=[list(x) for x in lines])])[-12:]
    d['posted'] += 1
    d['day_posted'] += 1


def _post(c: dict, t: dict, st: dict) -> None:
    _post_lines(c, t, st['title'], st['_key'])


def _finish(s: dict, c: dict, d: dict, o: dict, t: dict, base: int, lead: str = '') -> dict:
    lunch = office.spend(o, office.COST['submit'] + office.review_cost(o))
    late, adj, note = office.settle(o, t, c['day'])
    t['late'] = late
    ms = KINDS[t['variant']]['milestone']
    if ms not in d['milestones']:
        d['milestones'].append(ms)
    d['done'] += 1
    d['day_done'] += 1
    d['day_work'] = (d['day_work'] + [dict(task=t['id'], board=t['variant'] == 'match', mistakes=t['mistakes'], late=late)])[-12:]
    reward = max(0, base + adj)
    kit.metric(c, 'ga_dossiers')
    if t['mistakes'] == 0:
        kit.metric(c, 'ga_clean_dossiers')
    kit.complete(s, c, t, reward, f'Bạn đã hoàn tất hồ sơ “{t["title"]}”' + (' nhưng trễ hạn.' if late else '.'))
    full = len(d['milestones']) == len(MILESTONE_IDS)
    parts = [lead, f'Đã nộp hồ sơ · thưởng hiệu suất +{reward} xu.', note, lunch,
             'Đủ 6 mốc khóa sổ quý — báo cáo hợp nhất sẵn sàng!' if full else '']
    return dict(message=' '.join(x for x in parts if x), celebrate=not late)


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    o = d['office']
    office.sync(o, c['day'])
    mod = _mod(c['day'])
    if name == 'ga_overtime':
        kit.confirm(p, 'Xác nhận ở lại tăng ca tới 20:00.')
        return dict(message=office.overtime(s, c, o, 18 if mod['id'] == 'crunch' else 12, mod['id'] == 'crunch'))
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Hồ sơ không thuộc nhóm hợp nhất Sông Hồng.')
    kit.need(t['known'], 'Nhận hồ sơ trước đã (bấm “Nhận hồ sơ”).')
    kit.need(t['status'] != 'completed', 'Hồ sơ này đã nộp rồi.')
    board = t.get('variant') == 'match'
    if name in ('ga_pair', 'ga_tag', 'ga_chase'):
        kit.need(board, 'Hồ sơ này không có bàn đối chiếu.')
    if name == 'ga_chase':
        kit.need(_waiting(t, o), 'Gói báo cáo đã về rồi.')
        lunch = office.spend(o, CHASE_MIN)
        t['wait'] = None
        return dict(message=' '.join(x for x in ('📞 Bạn gọi giục anh Phong. Mười phút sau gói báo cáo về tới hộp thư.', lunch) if x))
    if board and name in ('ga_pair', 'ga_tag', 'ga_hint', 'ga_submit') and _waiting(t, o):
        kit.need(False, f'Gói báo cáo chưa về (hẹn {office.hhmm(t["wait"])}). Làm hồ sơ khác trước, hoặc gọi giục.')
    if name == 'ga_pair':
        return _pair(d, o, t, p)
    if name == 'ga_tag':
        return _tag(d, o, t, p)
    if name == 'ga_open':
        kit.need(not board, 'Bằng chứng của bàn đối chiếu đã bày sẵn trên bàn.')
        doc = next((x for x in t['docs'] if x['id'] == p.get('doc')), None)
        kit.need(doc, 'Hồ sơ không có tài liệu này.')
        extra = ''
        if doc['id'] not in t['inspected']:
            lunch = office.spend(o, office.COST['open'])
            t['inspected'].append(doc['id'])
            extra = f' (+{office.COST["open"]} phút)' + (' ' + lunch if lunch else '')
        kit.start_work(t)
        return dict(message=f'Đã mở: {doc["title"]}.{extra}')
    if name == 'ga_hint':
        away = mod['id'] == 'board_meeting'
        who = 'Chị Mai Anh nhắn từ phòng họp HĐQT (sau 15 phút): ' if away else 'Chị Mai Anh gợi ý: '
        if board:
            x = _line(t, p.get('line'))
            kit.need(x['id'] not in t['board'], 'Dòng này đã xử lý rồi.')
            lunch = office.spend(o, 15 if away else office.COST['hint'])
            if x['id'] not in t['tips']:
                t['tips'].append(x['id'])
            return dict(message=' '.join(y for y in (who + MATCH_HINTS[_hint_key(t, x)], lunch) if y))
        st = _current(t)
        kit.need(st, 'Hồ sơ đã xong mọi bước.')
        lunch = office.spend(o, 15 if away else office.COST['hint'])
        if st['id'] not in t['tips']:
            t['tips'].append(st['id'])
        return dict(message=' '.join(y for y in (who + (st.get('hints') or ['Đọc lại tài liệu gốc.'])[0], lunch) if y))
    if name == 'ga_step':
        kit.need(not board, 'Bàn đối chiếu làm bằng cách ghép dòng, không có bước tính.')
        st = _current(t)
        kit.need(st, 'Hồ sơ đã xong mọi bước. Chọn ghi chú bàn giao rồi nộp nhé.')
        kit.need(p.get('step') == st['id'], 'Làm theo thứ tự các bước nhé.')
        missing = [x['title'] for x in t['docs'] if x['id'] in st.get('docs', []) and x['id'] not in t['inspected']]
        kit.need(not missing, 'Mở tài liệu trước khi kết luận: ' + ', '.join(missing) + '.')
        office.need_open(o)
        answer, diag = p.get('answer'), ''
        if st['kind'] == 'entry':
            answer, diag = _entry_answer(st, answer)
        kit.start_work(t)
        ok, msg = procedures.submit(t, st['id'], answer)
        lunch = office.spend(o, office.COST['step'] + (0 if ok else office.COST['wrong']))
        if not ok:
            return dict(message=' '.join(x for x in (diag, msg, lunch) if x), correct=False)
        if st['kind'] == 'entry' and st.get('post', True):
            _post(c, t, st)
        if procedures.done(t):
            msg += ' Đủ bước rồi — chọn ghi chú bàn giao và nộp hồ sơ.'
        return dict(message=' '.join(x for x in (msg, lunch) if x), correct=True)
    if name == 'ga_submit':
        if board:
            kit.need(not _left(t), f'Còn {_left(t)} dòng chưa ghép hoặc chưa có lý do.')
            kit.confirm(p, 'Xác nhận chốt đối chiếu và ghi bút toán loại trừ.')
            office.need_open(o)
            agreed = _meter_of(t['lines'], t['board'])['ra2']
            t['handover'] = 'specific'
            A, B = _short(t['ic']['a']), _short(t['ic']['b'])
            _post_lines(c, t, f'Loại trừ công nợ nội bộ {A} ↔ {B}', [('331', '131', agreed)])
            d['boards'] += 1
            return _finish(s, c, d, o, t, max(8, 30 - 4 * t['mistakes']), f'✂️ Hai sổ khớp {_n(agreed)} xu → loại trừ Nợ 331 / Có 131.')
        kit.need(procedures.done(t), 'Hồ sơ còn bước chưa làm xong.')
        note = kit.one_of(p.get('note'), HANDOVER, 'Chọn một ghi chú bàn giao.')
        kit.confirm(p, 'Xác nhận nộp hồ sơ cho người giao việc.')
        office.need_open(o)
        t['handover'] = note
        m = t['mistakes']
        return _finish(s, c, d, o, t, 30 if m == 0 else max(10, 24 - 4 * m))
    raise kit.eng().GameError('Thao tác hợp nhất không hợp lệ.')


# ---------------------------------------------------------------- views & validation
def _strip(v):
    if isinstance(v, dict):
        return {k: _strip(x) for k, x in v.items() if not k.startswith('_')}
    if isinstance(v, list):
        return [_strip(x) for x in v]
    return v


def _public_match(t: dict, v: dict) -> dict:
    board = t.get('board') or {}
    no, n = {}, 0
    for x in t['lines']:
        st = board.get(x['id'])
        if x['side'] == 'a' and st and st['k'] == 'pair':
            n += 1
            no[x['id']] = no[st['mate']] = n
    rows = []
    for x in t['lines']:
        row = dict(id=x['id'], side=x['side'], ref=x['ref'], date=x['date'], text=x['text'], amount=x['amount'], kind=x['kind'],
                   hinted=x['id'] in t['tips'])
        row['tip'] = MATCH_HINTS[_hint_key(t, x)] if row['hinted'] else None
        st = board.get(x['id'])
        if st:
            row['state'] = dict(st, no=no.get(x['id']))
            row['why'] = (f'{x["ref"]}: cùng số, cùng tiền, ghi hai lần → hủy dòng trùng.' if st.get('tag') == 'dup' else
                          _pair_root(t, x['id'], st['mate'])['_truth']['why'] if st['k'] == 'pair' and x['side'] == 'a' else
                          _pair_root(t, st['mate'], x['id'])['_truth']['why'] if st['k'] == 'pair' else x['_truth']['why'])
        rows.append(row)
    left = _left(t)
    m = _meter_of(t['lines'], board)
    v.update(lines=rows, proc=[], proc_state=None, docs=_strip(copy.deepcopy(t['docs'])), tags=tags_for(t['day']),
             causes=[dict(id=i, emoji=e, label=label) for i, e, label in CAUSES_PAIR],
             names=dict(a=_short(t['ic']['a']), b=_short(t['ic']['b']), fx=t['ic']['fx']),
             meter=dict(m, total=len(rows), resolved=len(rows) - left, ready=left == 0, agreed=m['ra2'] if left == 0 else None),
             handover_options=None)
    return v


def public_task(t: dict) -> dict:
    v = _strip(copy.deepcopy(t))
    v['kind_info'] = dict(KINDS[t['variant']])
    v.pop('board', None)
    if not t['known']:
        v.update(docs=None, proc=None, proc_state=None, brief=None, lines=None)
        return v
    if t.get('variant') == 'match':
        return _public_match(t, v)
    v['docs'] = [copy.deepcopy(x) if x['id'] in t['inspected'] else dict(id=x['id'], type=x['type'], title=x['title'], source=x['source'], closed=True)
                 for x in _strip(t['docs'])]
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
    v['handover_options'] = ([dict(id='specific', label=t['_handover']), dict(id='short', label='“Xong rồi ạ.”'),
                              dict(id='none', label='Không để lại ghi chú')] if procedures.done(t) else None)
    return v


def _validate_match(t: dict) -> None:
    by = _lines(t)
    board = t.get('board')
    kit.need(isinstance(board, dict) and set(board) <= set(by), 'Bàn đối chiếu sai.')
    for lid, st in board.items():
        kit.need(isinstance(st, dict), 'Bàn đối chiếu sai.')
        if st.get('k') == 'pair':
            mate = st.get('mate')
            kit.need(set(st) == {'k', 'mate', 'cause'} and mate in by and by[mate]['side'] != by[lid]['side']
                     and board.get(mate) == dict(k='pair', mate=lid, cause=st['cause']), 'Cặp ghép sai.')
            a, b = (lid, mate) if by[lid]['side'] == 'a' else (mate, lid)
            kit.need(any(by[x]['_truth'].get('mate') in _group(t, b) for x in _group(t, a)), 'Cặp ghép sai.')
            root = _pair_root(t, a, b)
            differ = by[a]['amount'] != by[b]['amount']
            kit.need(st['cause'] == (root['_truth']['cause'] if differ else None), 'Nguyên nhân lệch sai.')
        else:
            kit.need(set(st) == {'k', 'tag'} and st.get('k') == 'tag' and st.get('tag') in TAG_IDS, 'Lý do dòng lẻ sai.')
            g = _group(t, lid)
            if st['tag'] == 'dup':
                kit.need(len(g) > 1, 'Lý do dòng lẻ sai.')
            else:
                tr = by[lid]['_truth']
                kit.need(len(g) == 1 and tr['k'] == 'single' and tr['tag'] == st['tag'], 'Lý do dòng lẻ sai.')
    groups = {}
    for lid in by:
        groups.setdefault(tuple(_group(t, lid)), None)
    for g in groups:
        paired = sum(1 for x in g if board.get(x, {}).get('k') == 'pair')
        dups = sum(1 for x in g if board.get(x, {}).get('tag') == 'dup')
        kit.need(paired <= 1 and dups <= len(g) - 1, 'Bàn đối chiếu sai.')
    kit.need(isinstance(t.get('tips'), list) and len(set(t['tips'])) == len(t['tips']) and all(x in by for x in t['tips']), 'Gợi ý đã xem sai.')
    kit.need(t.get('inspected') == [], 'Danh sách tài liệu đã mở sai.')
    kit.need(t.get('wait') is None or (type(t['wait']) is int and office.OPEN <= t['wait'] <= office.LOCK), 'Giờ gói báo cáo về sai.')
    kit.need(t.get('handover') in (None, 'specific'), 'Báo cáo đối chiếu sai.')
    kit.need(t.get('late') in (None, True, False), 'Cờ trễ hạn sai.')
    if t['status'] == 'completed':
        kit.need(len(board) == len(by) and t['handover'] == 'specific', 'Đối chiếu chốt khi còn dòng dở.')


def validate_task(t: dict, original: dict) -> None:
    office.validate_task(t)
    if t.get('variant') == 'match':
        _validate_match(t)
        return
    procedures.validate(t, original)
    ids = [x['id'] for x in t['docs']]
    kit.need(isinstance(t['inspected'], list) and len(set(t['inspected'])) == len(t['inspected']) and all(x in ids for x in t['inspected']),
             'Danh sách tài liệu đã mở sai.')
    steps = [st['id'] for st in t['proc']]
    kit.need(isinstance(t.get('tips'), list) and len(set(t['tips'])) == len(t['tips']) and all(x in steps for x in t['tips']), 'Gợi ý đã xem sai.')
    kit.need(t.get('handover') in (None, *HANDOVER), 'Ghi chú bàn giao sai.')
    kit.need(t.get('late') in (None, True, False), 'Cờ trễ hạn sai.')
    if t['status'] == 'completed':
        kit.need(procedures.done(t) and t['handover'], 'Hồ sơ hoàn tất nhưng chưa đủ bước.')


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.mark_legacy(c, ID)
    kit.need(set(initial()) <= set(d), 'Sổ hợp nhất thiếu dữ liệu.')
    led = d['elim']
    kit.need(isinstance(led, dict) and all(k in ACCOUNT_NAME for k in led), 'Sổ bút toán hợp nhất có tài khoản lạ.')
    for v in led.values():
        kit.integer(v, -10**10, 10**10)
    kit.need(sum(led.values()) == 0, 'Sổ bút toán hợp nhất không cân.')
    kit.need(isinstance(d['entries'], list) and len(d['entries']) <= 12, 'Nhật ký loại trừ sai.')
    for e in d['entries']:
        kit.need(isinstance(e, dict) and isinstance(e.get('lines'), list) and 1 <= len(e['lines']) <= 8, 'Bút toán lưu sai.')
        kit.integer(e.get('day'), 1, 10**7)
        kit.text(e.get('task'), 80)
        kit.text(e.get('title'), 120)
        for row in e['lines']:
            kit.need(isinstance(row, list) and len(row) == 3 and row[0] in ACCOUNT_NAME and row[1] in ACCOUNT_NAME, 'Dòng bút toán sai.')
            kit.integer(row[2], 1, 10**9)
    kit.need(isinstance(d['milestones'], list) and len(set(d['milestones'])) == len(d['milestones']) and all(x in MILESTONE_IDS for x in d['milestones']),
             'Tiến độ khóa sổ quý sai.')
    for k in ('posted', 'quarters', 'done', 'day_posted', 'day_done', 'boards', 'matched', 'tagged', 'slips'):
        kit.integer(d.get(k), 0, 10**9)
    office.validate(d['office'])
    kit.need(isinstance(d['day_work'], list) and len(d['day_work']) <= 12, 'Sổ việc trong ngày sai.')
    for w in d['day_work']:
        kit.need(isinstance(w, dict) and set(w) == {'task', 'board', 'mistakes', 'late'} and type(w['board']) is bool
                 and type(w['late']) is bool, 'Sổ việc trong ngày sai.')
        kit.text(w['task'], 80)
        kit.integer(w['mistakes'], 0, 10**6)


def public_data(c: dict) -> dict:
    d = copy.deepcopy(kit.data(c))
    for k, v in initial().items():
        d.setdefault(k, copy.deepcopy(v))
    o = office.ensure(d)
    q, phase, year = _period(c['day'])
    d['period'] = dict(quarter=q, year=year, phase=phase, label=f'Ngày làm việc thứ {phase + 1}/5 của kỳ khóa sổ quý {q}')
    d['balanced'] = sum(d['elim'].values()) == 0
    mod = _mod(c['day'])
    d['today'] = dict(mod=dict(id=mod['id'], emoji=mod['emoji'], name=mod['name'], text=mod['text']), rules=rules(c['day']),
                      fx=fx_rates(c['day']))
    d['office'] = office.public(o, c['day'])
    d['milestone_names'] = [n for i, n in MILESTONES if i in d['milestones']]
    d.pop('day_work', None)
    return d


def known_request(c: dict, t: dict) -> str:
    if t.get('variant') == 'match':
        return t['brief'] + f' Hai sổ có {len(t["lines"])} dòng; bằng chứng: ' + (', '.join(x['title'] for x in t['docs']) or 'không có') + '.'
    return t['brief'] + ' Tài liệu: ' + ', '.join(x['title'] for x in t['docs']) + '.'


# ---------------------------------------------------------------- day hooks
def on_task(s: dict, c: dict, t: dict) -> None:
    if not t.get('gen'):
        return
    o = _data(c)['office']
    office.sync(o, c['day'])
    office.set_due(c, t, o)
    mod = _mod(t['day'])['id']
    if mod == 'crunch':
        t['due'] = max(office.OPEN + 60, t['due'] - 30)
    if mod == 'late_package' and t['variant'] == 'match' and int(t['id'].rsplit('-', 1)[1]) == _match_slot(t['day']):
        t['wait'] = WAIT_AT
        t['due'] = max(t['due'], WAIT_AT + 90)


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    o = d['office']
    mod = _mod(c['day'])
    office.begin(o, c['day'])
    office.carry(c, ID, o)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('wait') is not None and t['day'] < c['day']:
            t['wait'] = None                                   # yesterday's late package has arrived overnight
    d['day_work'] = []
    if mod['id'] != 'normal':
        kit.log(s, c, 'surprise', f'{mod["emoji"]} Hôm nay: {mod["name"]}. {mod["text"]}', kit.npc_id(ID, 0))


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    o = d['office']
    office.sync(o, c['day'])
    mod = _mod(c['day'])
    work = d['day_work']
    slips = sum(w['mistakes'] for w in work)
    out = dict(posted=d['day_posted'], dossiers=d['day_done'], milestones=[n for i, n in MILESTONES if i in d['milestones']],
               mod=dict(emoji=mod['emoji'], name=mod['name']), boards=sum(1 for w in work if w['board']), slips=slips,
               balanced=sum(d['elim'].values()) == 0)
    if mod['id'] == 'audit_visit' and work:
        if slips == 0:
            kit.money(s, c, 10, 'Thưởng: kiểm toán xem giấy làm việc không có vết sửa', None, 'audit_bonus')
            office.trust(o, 3)
            kit.review(s, c, kit.npc_id(ID, 5), 5, 'Giấy làm việc hôm nay sạch: mỗi dòng có lý do, không một vết sửa. Rất dễ kiểm.', f'audit-{c["day"]}')
            out['audit'] = dict(ok=True, amount=10, text='Chị Thảo xem giấy làm việc: sạch, không một vết sửa. Thưởng 10 xu.')
        elif slips >= 3:
            paid = office.fine(s, c, o, 10, 'Thư quản lý: giấy làm việc sửa sai nhiều lần')
            office.trust(o, -3)
            out['audit'] = dict(ok=False, amount=paid, text=f'Chị Thảo đếm được {slips} lần sửa sai → thư quản lý gửi HĐQT. Trừ {paid} xu.')
        else:
            out['audit'] = dict(ok=True, amount=0, text=f'Chị Thảo xem giấy làm việc: {slips} chỗ sửa, vẫn chấp nhận được.')
    if mod['id'] == 'board_meeting' and work:
        left = [t for t in c['tasks'] if t.get('career') == ID and t['day'] == c['day'] and t['status'] not in ('completed', 'referred', 'cancelled')]
        if not left and slips <= 1:
            kit.money(s, c, 12, 'Thưởng: HĐQT khen số liệu hợp nhất', None, 'board_bonus')
            office.trust(o, 3)
            out['board'] = dict(ok=True, amount=12, text='Chị Mai Anh họp xong nhắn: “HĐQT khen số liệu hôm nay rõ ràng.” Thưởng 12 xu.')
        else:
            office.trust(o, -2)
            out['board'] = dict(ok=False, amount=0, text='HĐQT hỏi dồn vì số liệu hôm nay còn dở hoặc sửa nhiều lần; chị Mai Anh phải xin khất.')
    out['office'] = office.close_day(c, ID, o)
    d['day_posted'] = 0
    d['day_done'] = 0
    d['day_work'] = []
    if c['day'] % 5 == 0:
        # Consolidation entries are redone every period; they never live in a subsidiary's books.
        out['quarter_done'] = len(d['milestones'])
        d['quarters'] += 1
        d['milestones'] = []
        d['elim'] = {}
    return out


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e['role'] == 'ga_fx':
        r = fx_rates(c['day'])
        return f'Tỷ giá cuối kỳ hôm nay {r["closing"]} xu/NM (hôm qua {r["prev"]}), bình quân {r["average"]}. Đã dán lên bảng chung.'
    if not t or t['career'] != ID or not t['known']:
        return None
    if t.get('variant') == 'match':
        if e['role'] == 'ga_analyst':
            m = _meter_of(t['lines'], t['board'])
            return f'Đã cộng lại hai sổ: còn lệch {_n(abs(m["gap"]))} xu chưa có lý do. Phần kết luận vẫn chờ bạn.'
        if e['role'] == 'ga_collect':
            return 'Đã gom phiếu giao hàng, sao kê và email hóa đơn lên bàn đối chiếu.'
        return None
    if e['role'] == 'ga_collect':
        doc = next((x for x in t['docs'] if x['id'] not in t['inspected']), None)
        if doc:
            t['inspected'].append(doc['id'])
            return f'Đã tải “{doc["title"]}” từ cổng gói báo cáo về bàn bạn.'
        return 'Đã đặt lịch nhắc hạn nộp cho các công ty con.'
    if e['role'] == 'ga_analyst':
        return 'Đã đối chiếu nhanh tổng loại trừ: Nợ = Có. Phần kết luận vẫn chờ bạn.'
    return None


def hint(c: dict, t: dict) -> str:
    if t.get('variant') == 'match':
        return 'Chạm một dòng sổ bên bán và một dòng sổ bên mua cùng chứng từ để ghép; dòng chỉ có một bên thì chọn lý do. Khớp hết → loại trừ.'
    return 'Mở đủ tài liệu → làm từng bước (đối chiếu, loại trừ, quy đổi, hợp nhất) → ghi chú bàn giao → nộp.'


def _speed(t: dict) -> tuple[int, str]:
    if t.get('late') is True:
        return 2, 'nộp sau hạn'
    if type(t.get('due')) is int:
        return 5, 'kịp hạn ' + office.hhmm(t['due'])
    patience = t.get('patience', 100)
    return (5 if patience >= 90 else 4 if patience >= 70 else 3 if patience >= 50 else 2), f'người giao việc còn kiên nhẫn {patience}%'


def feedback(c: dict, t: dict) -> dict:
    m = t['mistakes']
    tips = len(t['tips'])
    speed, speed_note = _speed(t)
    indep = 5 if tips == 0 else 4 if tips == 1 else 3
    if t.get('variant') == 'match':
        acc = 5 if m == 0 else 4 if m == 1 else 3 if m <= 3 else 2
        return dict(criteria=[
            dict(key='accuracy', label='Ghép đúng ngay lần đầu', score=acc, note='không sửa lần nào' if m == 0 else f'sửa sai {m} lần'),
            dict(key='independence', label='Tự lực', score=indep, note='tự soát, không cần gợi ý' if not tips else f'xin gợi ý {tips} lần'),
            dict(key='speed', label='Kịp lịch khóa sổ', score=speed, note=speed_note),
            dict(key='handover', label='Có lý do cho từng dòng', score=5, note=f'{len(t["lines"])} dòng đều có kết luận'),
        ])
    acc = 5 if m == 0 else 4 if m == 1 else 3 if m <= 3 else 2 if m <= 5 else 1
    hand = {'specific': 5, 'short': 3, 'none': 2}[t.get('handover') or 'none']
    return dict(criteria=[
        dict(key='accuracy', label='Số liệu hợp nhất chính xác', score=acc, note='không sai bước nào' if m == 0 else f'sai {m} lần trước khi đúng'),
        dict(key='independence', label='Tự lực', score=indep, note='tự làm, không cần gợi ý' if not tips else f'xin gợi ý {tips} lần'),
        dict(key='speed', label='Kịp lịch khóa sổ', score=speed, note=speed_note),
        dict(key='handover', label='Bàn giao rõ ràng', score=hand, note={5: 'ghi chú có số liệu, nguồn', 3: 'ghi chú quá ngắn', 2: 'không để lại ghi chú'}[hand]),
    ])


def content() -> dict:
    return dict(accounts=[dict(id=a, name=n) for a, n in ACCOUNTS], kinds=KINDS, entities=ENTITIES,
                milestones=[dict(id=i, name=n) for i, n in MILESTONES],
                boss=dict(name='Chị Mai Anh', npc=kit.npc_id(ID, 0)),
                tags=[dict(id=i, emoji=e, label=label) for i, e, label in TAGS],
                causes=[dict(id=i, emoji=e, label=label) for i, e, label in CAUSES_PAIR],
                rules=['Quy tắc hợp nhất, tỷ giá và ngưỡng trọng yếu theo quy chế của tập đoàn.',
                       'SH Nami ghi sổ bằng đồng NM của nước Nami. Cứ 5 ngày làm việc là một kỳ khóa sổ quý.'])


# ---------------------------------------------------------------- situations
SITUATIONS = [
    dict(id='GA-S01', title='Công ty con “kéo” doanh thu vào quý này', npc=2, tone='tense', min_day=1,
         opening='Gói báo cáo SH Logistics có 900 xu doanh thu cước cho các chuyến… chạy vào tháng đầu quý sau. Anh Phong: “Hợp đồng ký rồi mà, ghi luôn cho đẹp quý!”',
         swap='Bạn là kế toán trưởng công ty con: thưởng của cả đội phụ thuộc chỉ tiêu quý này.',
         facts=[dict(id='contract', title='Hợp đồng vận chuyển', source='SH Logistics', text='Chuyến xe chạy từ ngày 03 quý sau; khách chỉ trả tiền khi hàng tới nơi.'),
                dict(id='policy', title='Chính sách tập đoàn', source='Quy chế kế toán', text='Doanh thu dịch vụ ghi nhận khi dịch vụ đã hoàn thành.'),
                dict(id='bonus', title='Cơ chế thưởng', source='Nhân sự', text='Thưởng quý của SH Logistics tính theo doanh thu báo cáo.')],
         options=[dict(id='reverse', label='Gọi anh Phong giải thích nguyên tắc, đề nghị chuyển 900 xu sang quý sau; báo CFO về cơ chế thưởng', requires=['contract', 'policy'], quality='good', stars=4, reward=20,
                       review='Nói có lý, tôi sửa. Nhưng cơ chế thưởng kiểu này thì năm nào cũng sẽ có người thử lại đấy.',
                       outcome='Doanh thu về đúng kỳ; CFO đưa việc sửa cơ chế thưởng (tính theo doanh thu đã thực hiện) vào họp quý.',
                       perspectives=[dict(who='Anh Phong · SH Logistics', emoji='🚚', text='Mất mặt với đội một chút, nhưng còn hơn bị kiểm toán gạch trước HĐQT.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='📐', text='Sửa số là một việc; sửa động cơ làm sai mới là việc lớn.'),
                                     dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Cắt kỳ doanh thu là khoản tôi kiểm đầu tiên ở mọi công ty con.')]),
                  dict(id='accept', label='Chấp nhận số của công ty con, “họ tự chịu trách nhiệm”', quality='bad', stars=2, cost=40,
                       review='Nhận hết không hỏi câu nào. Tới lúc kiểm toán gạch thì cả tập đoàn chịu.',
                       outcome='Kiểm toán đề nghị điều chỉnh giảm doanh thu hợp nhất; báo cáo trình ngân hàng phải phát hành lại.',
                       perspectives=[dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Số hợp nhất sai thì trách nhiệm là của công ty mẹ, không phải chỉ công ty con.'),
                                     dict(who='Ông Đại · Chủ tịch', emoji='🏛️', text='Phát hành lại báo cáo trước ngân hàng là điều tôi ghét nhất.')]),
                  dict(id='silent_fix', label='Tự sửa số trong bảng hợp nhất, không nói với ai', requires=['policy'], quality='ok',
                       outcome='Số hợp nhất đúng, nhưng sổ SH Logistics vẫn sai và hai bộ số lệch nhau mỗi quý.',
                       perspectives=[dict(who='Anh Phong · SH Logistics', emoji='🚚', text='Tôi không biết bị sửa, quý sau lại làm y vậy.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='📐', text='Điều chỉnh không có dấu vết là cơn ác mộng của kiểm toán.')])],
         lesson='Doanh thu ghi khi dịch vụ đã hoàn thành; sửa ở gốc và chỉ ra động cơ khiến người ta muốn ghi sớm.'),
    dict(id='GA-S02', title='HĐQT muốn số “đẹp hơn” trước buổi gặp ngân hàng', npc=1, tone='tense', min_day=2,
         opening='Ông Đại: “Mai gặp ngân hàng. Khoản vay đến hạn tháng sau, cậu xếp nó vào nợ dài hạn giúp tôi, cho tỷ lệ thanh toán đẹp.”',
         facts=[dict(id='loan', title='Hợp đồng vay', source='Pháp chế', text='Khoản vay 5.000 xu đáo hạn sau 5 tuần; chưa có văn bản gia hạn.'),
                dict(id='covenant', title='Điều kiện vay', source='Ngân hàng', text='Hệ số thanh toán ngắn hạn phải ≥ 1,2; hiện là 1,1 nếu phân loại đúng.'),
                dict(id='plan', title='Kế hoạch dòng tiền', source='Chị Mai Anh', text='Tập đoàn có thể thu nhanh 1.500 xu công nợ và đang đàm phán gia hạn khoản vay.')],
         options=[dict(id='truth', label='Giữ phân loại đúng; cùng CFO chuẩn bị kế hoạch dòng tiền và đề nghị gia hạn trình ngân hàng', requires=['loan', 'plan'], quality='good', stars=4, reward=25,
                       review='Không chiều tôi, nhưng cái kế hoạch dòng tiền làm ngân hàng tin hơn con số đẹp. Được.',
                       outcome='Ngân hàng đồng ý gia hạn vì tập đoàn chủ động trình bày; hệ số được miễn trừ một kỳ.',
                       perspectives=[dict(who='Ông Đại · Chủ tịch', emoji='🏛️', text='Tôi sợ ngân hàng rút vốn. Hóa ra nói thật kèm kế hoạch lại an toàn hơn.'),
                                     dict(who='Cán bộ tín dụng', emoji='🏦', text='Khách hàng tự nói ra khó khăn và có kế hoạch — tôi đánh giá cao.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='📐', text='Việc của phòng tài chính là tìm lối ra thật, không phải vẽ lối ra trên giấy.')]),
                  dict(id='reclass', label='Xếp khoản vay vào dài hạn như Chủ tịch muốn', quality='bad', stars=3, cost=60,
                       review='Cậu làm đúng ý tôi… cho tới khi ngân hàng đọc hợp đồng vay của chính họ.',
                       outcome='Ngân hàng phát hiện phân loại sai, đánh giá tập đoàn thiếu trung thực, tăng lãi suất và yêu cầu kiểm toán đặc biệt.',
                       perspectives=[dict(who='Cán bộ tín dụng', emoji='🏦', text='Hợp đồng vay nằm trong hồ sơ của chúng tôi. Số “đẹp” đó làm mất niềm tin.'),
                                     dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Phân loại nợ sai là sai sót trọng yếu về trình bày.')]),
                  dict(id='quit', label='Tuyên bố sẽ nghỉ việc nếu bị ép', requires=['loan'], quality='ok',
                       outcome='Chủ tịch rút yêu cầu nhưng không khí căng thẳng; không ai chuẩn bị được giải pháp cho buổi gặp ngân hàng.',
                       perspectives=[dict(who='Ông Đại · Chủ tịch', emoji='🏛️', text='Tôi cần người giúp tôi giải quyết, không cần một tối hậu thư.'), dict(who='Chị Mai Anh · CFO', emoji='📐', text='Giữ nguyên tắc là đúng; nhưng mang theo phương án thì Chủ tịch mới có đường lui.')])],
         lesson='Không “làm đẹp” trình bày; đem sự thật kèm kế hoạch hành động tới bàn đàm phán.'),
    dict(id='GA-S03', title='Kiểm toán đề xuất một bút toán điều chỉnh lớn', npc=5, tone='gentle', min_day=3,
         opening='Chị Thảo: “Đề xuất lập dự phòng giảm giá 600 xu cho lô nước mắm tồn lâu của SH Food.”',
         facts=[dict(id='ageing', title='Tuổi hàng tồn', source='SH Food', text='Lô 1.500 xu tồn 14 tháng, hạn dùng còn 4 tháng.'),
                dict(id='price', title='Giá bán gần đây', source='Phòng kinh doanh', text='Ba tháng qua bán giảm giá 40% mới thanh lý được một phần.'),
                dict(id='ngoc', title='Ý kiến chị Ngọc', source='SH Food', text='“Tết sắp tới có thể bán hết với giá tốt hơn” — chưa có đơn hàng nào.')],
         options=[dict(id='review', label='Xem bằng chứng tuổi hàng và giá bán gần đây với kiểm toán; đồng ý điều chỉnh vì có căn cứ', requires=['ageing', 'price'], quality='good', stars=5,
                       review='Đọc bằng chứng, đồng ý có căn cứ. Làm việc nhanh.',
                       outcome='Dự phòng được ghi nhận; SH Food lên kế hoạch khuyến mại Tết để thanh lý lô hàng.',
                       perspectives=[dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Tranh luận bằng bằng chứng thì hai bên đều nhẹ nhàng.'),
                                     dict(who='Chị Ngọc · SH Food', emoji='🍜', text='Hơi tiếc, nhưng hàng tồn 14 tháng thì đúng là rủi ro thật.')]),
                  dict(id='fight', label='Từ chối, dọa đổi công ty kiểm toán năm sau', quality='bad', stars=1, cost=30,
                       review='Không có bằng chứng phản bác. Chỉ có lời đe dọa. Ghi vào hồ sơ.',
                       outcome='Kiểm toán đưa ý kiến ngoại trừ; HĐQT phải giải trình với cổ đông.',
                       perspectives=[dict(who='Ông Đại · Chủ tịch', emoji='🏛️', text='Ý kiến ngoại trừ còn tốn kém hơn 600 xu dự phòng nhiều.'),
                                     dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Áp lực đổi kiểm toán là dấu hiệu tôi phải kiểm kỹ hơn.')]),
                  dict(id='blind', label='Đồng ý ngay, không cần xem', quality='ok', stars=3,
                       review='Đồng ý nhanh. Nhưng tôi mong nhóm hợp nhất tự đánh giá.',
                       outcome='Số liệu được điều chỉnh, nhưng SH Food thấy bị bỏ qua ý kiến và không hiểu vì sao.',
                       perspectives=[dict(who='Chị Ngọc · SH Food', emoji='🍜', text='Không ai hỏi bên em một câu nào.'), dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Đồng ý nhanh không có nghĩa là đã hiểu rủi ro — năm sau lô hàng khác lại y như vậy.')])],
         lesson='Bút toán kiểm toán đề xuất: xem bằng chứng, hỏi đơn vị liên quan, rồi quyết định — không phản ứng theo cảm xúc.'),
    dict(id='GA-S04', title='Email tố giác về một công ty con', npc=0, tone='tense', min_day=2,
         opening='Hộp thư nhận email ẩn danh: “Trưởng phòng mua hàng SH Pack nhận tiền lại quả từ nhà cung cấp mực in. Có bằng chứng.”',
         facts=[dict(id='policy', title='Chính sách tố giác', source='Quy chế tập đoàn', text='Tố giác được chuyển tới Ủy ban Kiểm toán; bảo mật danh tính người báo; không tự điều tra.'),
                dict(id='prices', title='Giá mực in', source='Sổ mua hàng', text='Giá mực in SH Pack mua cao hơn hai công ty khác trong tập đoàn khoảng 18%.'),
                dict(id='director', title='Quan hệ', source='Nhân sự', text='Giám đốc SH Pack là anh rể của trưởng phòng mua hàng.')],
         options=[dict(id='committee', label='Chuyển nguyên văn cho Ủy ban Kiểm toán theo chính sách, giữ bí mật, lưu nguyên dữ liệu mua hàng', requires=['policy'], quality='good', reward=20,
                       outcome='Ủy ban Kiểm toán thuê bên độc lập rà soát; hợp đồng mực in được đấu thầu lại, tiết kiệm 15%.',
                       perspectives=[dict(who='Người tố giác (ẩn danh)', emoji='🕊️', text='Tôi sợ bị trả thù. Không ai biết tôi là ai — cảm ơn.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='📐', text='Đúng kênh, đúng bảo mật: người tốt được bảo vệ, người sai được xét công bằng.'),
                                     dict(who='Linh · SH Pack', emoji='📦', text='Em chỉ thấy quy trình mua hàng rõ hơn hẳn sau đó.')]),
                  dict(id='director', label='Chuyển email cho giám đốc SH Pack xử lý', requires=['prices'], quality='bad', cost=30,
                       outcome='Email đến tay người có quan hệ gia đình với người bị tố; dữ liệu mua hàng bị “dọn dẹp”, người tố giác bị lộ.',
                       perspectives=[dict(who='Người tố giác (ẩn danh)', emoji='😨', text='Tôi đã tin kênh tố giác. Giờ ai cũng nhìn tôi.'),
                                     dict(who='Ủy ban Kiểm toán', emoji='🏛️', text='Xung đột lợi ích rõ ràng — lẽ ra phải tới chúng tôi.')]),
                  dict(id='confront', label='Tự gọi trưởng phòng mua hàng hỏi thẳng', requires=['prices'], quality='bad',
                       outcome='Người bị tố được “báo trước”; cuộc rà soát sau đó khó thu thập bằng chứng hơn nhiều.',
                       perspectives=[dict(who='Chị Mai Anh · CFO', emoji='📐', text='Thiện chí nhưng sai vai: kế toán không phải điều tra viên.'), dict(who='Người tố giác (ẩn danh)', emoji='😨', text='Chỉ cần một cuộc gọi, ai cũng đoán ra người báo là ai.')])],
         lesson='Tố giác đi đúng kênh, bảo mật người báo, giữ nguyên bằng chứng — không tự điều tra, không chuyển cho người có xung đột lợi ích.'),
    dict(id='GA-S05', title='Giao dịch bên liên quan chưa công bố', npc=3, tone='gentle', min_day=3,
         opening='Rà hợp đồng, bạn thấy SH Food thuê kho của Công ty Bờ Sông — do vợ Chủ tịch làm chủ. Thuyết minh báo cáo không nhắc tới.',
         facts=[dict(id='lease', title='Hợp đồng thuê kho', source='SH Food', text='Tiền thuê 240 xu/tháng, cao hơn giá thị trường khoảng 10%.'),
                dict(id='rule', title='Yêu cầu công bố', source='Chuẩn mực kế toán', text='Giao dịch với bên liên quan phải được công bố trong thuyết minh: bên liên quan, bản chất, giá trị.'),
                dict(id='chair', title='Phản ứng dự kiến', source='Chị Ngọc', text='“Chủ tịch không thích nhắc chuyện gia đình trong báo cáo…”')],
         options=[dict(id='disclose', label='Đưa vào thuyết minh bên liên quan, báo CFO và Ủy ban Kiểm toán xem xét giá thuê', requires=['lease', 'rule'], quality='good', stars=5, reward=15,
                       review='Nói thẳng mà có căn cứ. Công bố rõ ràng thì chẳng ai nghi ngờ gì.',
                       outcome='Thuyết minh đầy đủ; Ủy ban Kiểm toán đề nghị đàm phán lại giá thuê theo giá thị trường.',
                       perspectives=[dict(who='Chị Ngọc · SH Food', emoji='🍜', text='Tưởng sẽ căng, hóa ra công bố xong ai cũng nhẹ người.'),
                                     dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Bên liên quan không công bố là điều kiểm toán sợ nhất.'),
                                     dict(who='Ông Đại · Chủ tịch', emoji='🏛️', text='Tôi không làm gì sai, nhưng giấu đi mới khiến người ta nghĩ tôi sai.')]),
                  dict(id='ignore', label='Bỏ qua cho yên chuyện', quality='bad', stars=2, cost=30,
                       review='Không ai nói với tôi rằng thiếu công bố thì báo cáo bị ngoại trừ.',
                       outcome='Kiểm toán phát hiện, yêu cầu bổ sung thuyết minh sát ngày phát hành; tập đoàn bị nhắc nhở.',
                       perspectives=[dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Giao dịch nhỏ, nhưng thiếu minh bạch là vấn đề lớn.'), dict(who='Chị Ngọc · SH Food', emoji='🍜', text='Em biết mà không dám nói. Giá như có người mở lời trước.')]),
                  dict(id='private', label='Nói riêng với Chủ tịch để “tự xử lý”', requires=['chair'], quality='ok',
                       outcome='Chủ tịch chấm dứt hợp đồng thuê; nhưng các kỳ trước vẫn thiếu công bố.',
                       perspectives=[dict(who='Chị Mai Anh · CFO', emoji='📐', text='Hủy hợp đồng không xóa được nghĩa vụ công bố của kỳ đã qua.'), dict(who='Ông Đại · Chủ tịch', emoji='🏛️', text='Cảm ơn đã nói riêng với tôi. Nhưng đúng là phải công bố — tôi sẽ không ngăn.')])],
         lesson='Giao dịch bên liên quan: công bố đầy đủ và để bên độc lập đánh giá tính hợp lý của giá.'),
    dict(id='GA-S06', title='Kế toán công ty con quá tải và sai liên tục', npc=6, tone='gentle', min_day=1,
         opening='Gói báo cáo SH Pack quý này lại sai phụ lục nội bộ — lần thứ ba liên tiếp. Linh nhắn: “Em xin lỗi… em làm lại ngay ạ.”',
         facts=[dict(id='load', title='Khối lượng việc', source='Nhân sự SH Pack', text='Linh một mình làm sổ, thuế và lương từ khi đồng nghiệp nghỉ sinh.'),
                dict(id='errors', title='Loại lỗi', source='Nhóm hợp nhất', text='Cả ba lần đều sai cùng một chỗ: lấy số dư nội bộ trước khi đối chiếu.'),
                dict(id='template', title='Tài liệu sẵn có', source='Nhóm hợp nhất', text='Nhóm hợp nhất có checklist và mẫu phụ lục nội bộ nhưng chưa từng gửi cho SH Pack.')],
         options=[dict(id='coach', label='Gọi Linh 20 phút, đi qua checklist và mẫu; đề nghị giám đốc SH Pack san bớt việc', requires=['load', 'errors', 'template'], quality='good', stars=5,
                       review='Được chỉ đúng chỗ em hay sai, còn được nói giúp với giám đốc. Quý sau em nộp đúng hạn rồi ạ 🥹',
                       outcome='Quý sau gói SH Pack đúng và sớm một ngày; checklist được gửi cho mọi công ty con.',
                       perspectives=[dict(who='Linh · SH Pack', emoji='📦', text='Em không lười, em chỉ không biết mình sai ở đâu.'),
                                     dict(who='Giám đốc SH Pack', emoji='🏭', text='Tôi không biết Linh đang ôm ba việc. Đã tuyển thêm người.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='📐', text='Sửa một quy trình tốt hơn sửa ba lần số.')]),
                  dict(id='shame', label='Gửi email cả tập đoàn liệt kê lỗi của SH Pack', quality='bad', stars=1,
                       review='Em đã rất cố gắng. Email đó làm em muốn nghỉ việc.',
                       outcome='Linh xin nghỉ; SH Pack mất người duy nhất nắm sổ sách, quý sau gói báo cáo trễ một tuần.',
                       perspectives=[dict(who='Linh · SH Pack', emoji='😢', text='Cả tập đoàn đọc lỗi của em trước khi có ai hỏi em cần gì.'),
                                     dict(who='Chị Ngọc · SH Food', emoji='🍜', text='Đọc email đó ai cũng sợ báo lỗi của mình.')]),
                  dict(id='fix_myself', label='Tự sửa số giúp, không nói gì thêm', quality='ok', stars=4,
                       review='Cảm ơn nhóm hợp nhất đã sửa giúp em ạ. (Quý sau em vẫn chưa biết sửa sao…)',
                       outcome='Quý này kịp, nhưng lỗi lặp lại quý sau và bạn lại thức khuya sửa.',
                       perspectives=[dict(who='Chị Mai Anh · CFO', emoji='📐', text='Làm thay thì nhanh hôm nay, chậm mãi mãi.'), dict(who='Linh · SH Pack', emoji='📦', text='Em thấy số được sửa nhưng không biết mình sai ở đâu, nên quý sau vẫn lo.')])],
         lesson='Lỗi lặp lại là tín hiệu về quy trình và khối lượng việc — hướng dẫn và gỡ nguyên nhân, không bêu tên.'),
    dict(id='GA-S07', title='Hạn hợp nhất trùng Tết', npc=0, tone='gentle', min_day=4,
         opening='Lịch năm nay: hạn nộp báo cáo hợp nhất rơi đúng 28 Tết. Cả nhóm nhìn nhau: vé tàu về quê đã mua từ tháng trước.',
         facts=[dict(id='calendar', title='Lịch khóa sổ', source='Nhóm hợp nhất', text='Nếu các công ty con khóa sổ sớm 3 ngày, gói báo cáo về trước 22 Tết.'),
                dict(id='audit', title='Kiểm toán', source='Chị Thảo', text='Kiểm toán sẵn sàng soát xét sớm nếu nhận đủ PBC trước 20 Tết.'),
                dict(id='team', title='Nhóm', source='Khảo sát nội bộ', text='Hai bạn có con nhỏ, một bạn về quê xa; cả nhóm sẵn sàng tăng ca trước Tết.')],
         options=[dict(id='replan', label='Lên lịch lại từ sớm: khóa sổ con sớm 3 ngày, PBC gửi trước, chia ca trực online; báo HĐQT hạn mới', requires=['calendar', 'audit'], quality='good', reward=20,
                       outcome='Báo cáo xong ngày 25 Tết; cả nhóm về quê đúng vé, một người trực online nửa ngày có phụ cấp.',
                       perspectives=[dict(who='Chị Mai Anh · CFO', emoji='📐', text='Hạn khó thì dời việc lên sớm, không dời Tết của người ta.'),
                                     dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Nhận PBC sớm là món quà Tết tốt nhất cho kiểm toán.'),
                                     dict(who='Anh Kiên · SH Nami', emoji='🌏', text='Bên em không ăn Tết nên nhận trực hộ ngày cuối, vui mà!')]),
                  dict(id='force', label='Yêu cầu cả nhóm ở lại tới 28 Tết', quality='bad', cost=20,
                       outcome='Báo cáo kịp hạn nhưng hai người xin nghỉ việc sau Tết; sai sót tăng vì ai cũng mệt.',
                       perspectives=[dict(who='Thành viên nhóm', emoji='😮‍💨', text='Tôi làm được, nhưng lẽ ra có thể lên kế hoạch từ sớm.'), dict(who='Chị Mai Anh · CFO', emoji='📐', text='Kịp hạn mà mất người thì quý sau còn trễ hơn.')]),
                  dict(id='rush', label='Nộp báo cáo không qua soát xét cho kịp về quê', quality='bad', cost=40,
                       outcome='Ra Giêng phát hiện sai sót loại trừ nội bộ, phải phát hành lại báo cáo.',
                       perspectives=[dict(who='Ông Đại · Chủ tịch', emoji='🏛️', text='Báo cáo sớm mà sai thì không phải là sớm.'), dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Bỏ bước soát xét để kịp tàu — rồi cả hai bên cùng làm lại sau Tết.')])],
         lesson='Hạn cứng gặp ngày lễ: kéo cả lịch lên sớm và thỏa thuận với các bên, đừng bỏ bước kiểm soát.'),
    dict(id='GA-S08', title='Bạn ở ngân hàng hỏi số lợi nhuận chưa công bố', npc=4, tone='gentle', min_day=2,
         opening='Bạn thân làm ngân hàng đầu tư nhắn: “Quý này Sông Hồng lãi bao nhiêu? Kể nhỏ thôi, tớ không nói ai đâu 😉”',
         facts=[dict(id='policy', title='Quy chế bảo mật', source='Pháp chế', text='Thông tin tài chính chưa công bố là thông tin nội bộ; chỉ người được phép mới được tiết lộ.'),
                dict(id='stock', title='Cổ phiếu', source='Thị trường', text='Cổ phiếu Sông Hồng niêm yết trên sàn Mây; kết quả quý công bố tuần sau.')],
         options=[dict(id='decline', label='Từ chối nhẹ nhàng: “Tuần sau công bố, tớ gửi link cho cậu nhé!”', requires=['policy'], quality='good', reward=10,
                       outcome='Bạn thân cười: “Biết ngay mà.” Tuần sau cả hai cùng đọc báo cáo công bố.',
                       perspectives=[dict(who='Người bạn', emoji='🙂', text='Hỏi thử thôi. Thấy bạn giữ nguyên tắc, tớ lại tin bạn hơn.'),
                                     dict(who='Pháp chế', emoji='⚖️', text='Một câu từ chối lịch sự bảo vệ cả hai người.')]),
                  dict(id='hint', label='“Không nói số, nhưng quý này vui lắm” 😉', quality='bad', cost=30,
                       outcome='Người bạn mua cổ phiếu trước ngày công bố; ủy ban chứng khoán mở rà soát giao dịch bất thường.',
                       perspectives=[dict(who='Pháp chế', emoji='⚖️', text='Gợi ý cũng là tiết lộ thông tin nội bộ.'),
                                     dict(who='Người bạn', emoji='😰', text='Tớ tưởng chỉ là câu đùa…')]),
                  dict(id='ghost', label='Không trả lời tin nhắn', quality='ok',
                       outcome='Thông tin an toàn, nhưng người bạn tưởng bạn giận.',
                       perspectives=[dict(who='Người bạn', emoji='🤔', text='Chắc bận… hay giận mình nhỉ?'), dict(who='Pháp chế', emoji='⚖️', text='An toàn, nhưng một lời từ chối rõ ràng vừa giữ bí mật vừa giữ được tình bạn.')])],
         lesson='Thông tin chưa công bố là thông tin nội bộ — từ chối rõ ràng, lịch sự, kể cả với bạn thân.'),
    dict(id='GA-S09', title='Doanh thu “đi vòng” cuối quý', npc=2, tone='tense', min_day=3,
         opening='Soát bàn đối chiếu, bạn thấy ngày 29 SH Logistics bán 20 xe thùng cho SH Pack, ngày 30 SH Pack bán lại đúng 20 xe đó cho SH Logistics — giá cao hơn 15%.',
         swap='Bạn là anh Phong: chỉ tiêu doanh thu quý chỉ còn thiếu một chút, cả đội đang mong thưởng.',
         facts=[dict(id='same', title='Hai hóa đơn', source='Bàn đối chiếu', text='Cùng 20 xe thùng, cùng biển số, bán đi rồi mua lại trong hai ngày; hàng không rời bãi xe.'),
                dict(id='rule', title='Quy chế hợp nhất', source='Chị Mai Anh', text='Giao dịch nội bộ phải loại trừ toàn bộ doanh thu, giá vốn và lãi chưa thực hiện.'),
                dict(id='bonus', title='Cơ chế thưởng', source='Nhân sự', text='Thưởng quý của công ty con tính theo doanh thu trên báo cáo riêng.')],
         options=[dict(id='report', label='Loại trừ cả hai chiều trong báo cáo hợp nhất, báo chị Mai Anh kèm bằng chứng và đề xuất sửa cơ chế thưởng',
                       requires=['same', 'rule'], quality='good', stars=5, reward=15,
                       review='Hai chiều bán mua được loại trừ gọn. Có bằng chứng biển số xe thì ai cũng hết cãi.',
                       outcome='Doanh thu ảo không lọt vào số hợp nhất; HĐQT đổi thưởng sang doanh thu bán cho khách ngoài.',
                       perspectives=[dict(who='Chị Mai Anh · CFO', emoji='📐', text='Bắt được vòng này là nhờ đọc kỹ từng dòng đối chiếu.'),
                                     dict(who='Anh Phong · SH Logistics', emoji='🚚', text='Tôi ngại, nhưng cơ chế mới công bằng hơn cho cả đội.'),
                                     dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Giao dịch vòng tròn cuối kỳ là thứ tôi luôn tìm đầu tiên.')]),
                  dict(id='net', label='Chỉ loại trừ phần chênh 15% cho nhanh', quality='bad', stars=2, cost=30,
                       review='Số hợp nhất vẫn phồng doanh thu hai lần. Kiểm toán gạch lại toàn bộ.',
                       outcome='Kiểm toán yêu cầu loại trừ đủ hai chiều; báo cáo phải sửa sát ngày trình HĐQT.',
                       perspectives=[dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Loại trừ nửa vời còn khó giải thích hơn không loại trừ.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='📐', text='Nhanh mà sai thì phải làm lại hai lần.')]),
                  dict(id='quiet', label='Loại trừ đúng nhưng không báo ai, “số hợp nhất đúng là được”', requires=['rule'], quality='ok', stars=3,
                       review='Số hợp nhất đúng. Nhưng quý sau vòng đó lại xuất hiện, to hơn.',
                       outcome='Báo cáo hợp nhất đúng, nhưng cơ chế thưởng giữ nguyên nên giao dịch vòng tròn lặp lại.',
                       perspectives=[dict(who='Chị Mai Anh · CFO', emoji='📐', text='Sửa số mà không sửa động cơ thì mùa sau lại gặp.'),
                                     dict(who='Anh Phong · SH Logistics', emoji='🚚', text='Không ai nói gì, tôi tưởng vậy là ổn.')])],
         lesson='Giao dịch nội bộ đi vòng không tạo ra doanh thu cho tập đoàn: loại trừ đủ hai chiều và báo cho người sửa được động cơ.'),
    dict(id='GA-S10', title='Anh Kiên muốn dùng tỷ giá “đẹp” hơn', npc=4, tone='gentle', min_day=3,
         opening='Anh Kiên nhắn: “Ngân hàng bên em niêm yết NM cao hơn tỷ giá tập đoàn 2 xu. Dùng số đó thì SH Nami đỡ lỗ tỷ giá, báo cáo đẹp hơn nhiều nè.”',
         swap='Bạn là anh Kiên: quý nào SH Nami cũng bị hỏi vì lỗ tỷ giá, dù không phải lỗi của đội.',
         facts=[dict(id='policy', title='Quy chế tỷ giá', source='Chị Mai Anh', text='Cả tập đoàn dùng một bảng tỷ giá do CFO duyệt mỗi ngày khóa sổ; không công ty con nào tự chọn.'),
                dict(id='bank', title='Tỷ giá ngân hàng SH Nami', source='Anh Kiên', text='Là giá bán ra của một ngân hàng, không phải tỷ giá giao dịch thực tế của công ty.'),
                dict(id='explain', title='Lỗ tỷ giá quý này', source='Bàn hợp nhất', text='Lỗ do đồng NM giảm, không do hoạt động kinh doanh — có thể giải thích riêng trong thuyết minh.')],
         options=[dict(id='explain', label='Giữ tỷ giá tập đoàn; giúp anh Kiên viết thuyết minh tách lỗ tỷ giá khỏi kết quả kinh doanh',
                       requires=['policy', 'explain'], quality='good', stars=5,
                       review='Không được đổi tỷ giá, nhưng giờ HĐQT hiểu lỗ là do đồng NM, không phải do đội mình. Nhẹ cả người.',
                       outcome='Số liệu nhất quán cả tập đoàn; thuyết minh tách riêng ảnh hưởng tỷ giá, SH Nami không bị hỏi oan.',
                       perspectives=[dict(who='Anh Kiên · SH Nami', emoji='🌏', text='Cái em cần là được hiểu đúng, không phải con số đẹp.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='📐', text='Một tập đoàn, một bảng tỷ giá — nhưng lời giải thích thì có thể may đo.')]),
                  dict(id='accept', label='Cho SH Nami dùng tỷ giá ngân hàng của họ', quality='bad', stars=2, cost=25,
                       review='Quý này đẹp, quý sau kiểm toán hỏi sao mỗi công ty một tỷ giá.',
                       outcome='Kiểm toán phát hiện tỷ giá không nhất quán; báo cáo hợp nhất phải chuyển đổi lại.',
                       perspectives=[dict(who='Chị Thảo · Kiểm toán', emoji='🔎', text='Chọn tỷ giá theo kết quả mong muốn là điều tôi phải ghi vào thư quản lý.'),
                                     dict(who='Anh Kiên · SH Nami', emoji='😅', text='Tưởng giúp nhau, hóa ra thêm việc cho cả hai.')]),
                  dict(id='refuse', label='Từ chối cụt: “Quy định là quy định”', requires=['policy'], quality='ok', stars=3,
                       review='Đúng quy chế. Nhưng HĐQT vẫn hỏi đội em về khoản lỗ không phải do bọn em.',
                       outcome='Tỷ giá nhất quán, nhưng SH Nami tiếp tục bị hiểu nhầm là kinh doanh kém.',
                       perspectives=[dict(who='Anh Kiên · SH Nami', emoji='😔', text='Em chỉ muốn có ai hiểu vì sao bọn em lỗ.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='🤔', text='Giữ nguyên tắc rồi thì còn phải giúp người ta được hiểu đúng.')])],
         lesson='Tỷ giá không chọn theo con số mình muốn: giữ một bảng tỷ giá chung, và giải thích rõ phần lỗ do tỷ giá.'),
    dict(id='GA-S11', title='File lương gửi nhầm vào nhóm chat tập đoàn', npc=6, tone='gentle', min_day=2,
         opening='Linh hốt hoảng: “Em gửi nhầm file lương cả SH Pack vào nhóm chat khóa sổ 30 người… em phải làm sao đây?”',
         swap='Bạn là Linh: làm ba việc một lúc, bấm nhầm một cái là cả tập đoàn thấy lương đồng nghiệp.',
         facts=[dict(id='recall', title='Tính năng thu hồi', source='Bộ phận IT', text='Tin nhắn thu hồi được trong 24 giờ; IT có thể xóa bản đã tải trên máy công ty.'),
                dict(id='policy', title='Quy chế dữ liệu cá nhân', source='Pháp chế', text='Lộ dữ liệu lương phải báo IT và nhân sự ngay; người nhận được đề nghị xóa.'),
                dict(id='seen', title='Đã xem', source='Nhóm chat', text='Mới 6 người mở tin nhắn trong 10 phút.')],
         options=[dict(id='contain', label='Bảo Linh thu hồi ngay, báo IT và nhân sự, nhắn nhóm đề nghị xóa file; trấn an Linh rồi cùng rà quy trình gửi file',
                       requires=['recall', 'policy'], quality='good', stars=5,
                       review='Có người chỉ từng bước lúc em hoảng nhất. Mười lăm phút sau mọi thứ được xử lý xong.',
                       outcome='File được thu hồi và xóa trên máy công ty; nhân sự thông báo ngắn gọn, không ai bị bêu tên.',
                       perspectives=[dict(who='Linh · SH Pack', emoji='📦', text='Em cứ tưởng mình sẽ bị đuổi việc.'),
                                     dict(who='Bộ phận IT', emoji='💻', text='Báo sớm mười phút là xóa được gần hết.'),
                                     dict(who='Chị Mai Anh · CFO', emoji='📐', text='Sự cố nào cũng xử lý được nếu người ta dám báo ngay.')]),
                  dict(id='hide', label='Bảo Linh xóa lặng lẽ, “chắc chẳng ai để ý”', quality='bad', stars=2, cost=20,
                       review='Em xóa rồi, nhưng file đã bị chuyển đi tiếp. Giờ ai cũng bàn tán lương của nhau.',
                       outcome='File lan ra ngoài nhóm; nhân sự phải xử lý khiếu nại và bị hỏi vì sao không ai báo.',
                       perspectives=[dict(who='Nhân sự', emoji='🗂️', text='Không báo thì chúng tôi không kịp ngăn file lan tiếp.'),
                                     dict(who='Linh · SH Pack', emoji='😢', text='Giấu đi làm em càng sợ hơn.')]),
                  dict(id='blame', label='Nhắc nhở Linh trong nhóm cho mọi người rút kinh nghiệm', quality='bad', stars=1,
                       review='Cả nhóm 30 người đọc lỗi của em trước khi file được thu hồi.',
                       outcome='Thêm nhiều người mở file vì tò mò; Linh xin nghỉ phép vì xấu hổ.',
                       perspectives=[dict(who='Linh · SH Pack', emoji='😢', text='Em đã tự báo lỗi, vậy mà…'),
                                     dict(who='Bộ phận IT', emoji='💻', text='Tin nhắn nhắc nhở làm file bị chú ý hơn.')])],
         lesson='Lộ dữ liệu: chặn trước, báo đúng người, bảo vệ người đã báo lỗi — rồi mới sửa quy trình.'),
]

SPEC = dict(
    id=ID, prefix=PREFIX, category='office',
    meta=dict(short='Kế toán tập đoàn', place='Sông Hồng Group', tagline='Bốn công ty, một bộ báo cáo — loại trừ đúng, hợp nhất khớp.',
              icon='building', color='#2f6f9f', light='#e3eef8', weather='Gió sông mát', work='Hồ sơ hợp nhất', station='Bàn hợp nhất',
              greeting='Chị Mai Anh mở lịch khóa sổ quý: sáng nào cũng có bàn đối chiếu nội bộ, rồi loại trừ, quy đổi ngoại tệ, trình HĐQT — nhớ nhìn đồng hồ hạn.',
              caption='Một tập đoàn, một sự thật', map_label='13 · SÔNG HỒNG GROUP'),
    people=PEOPLE,
    staff=[('Quân', 'ga_collect', 'Theo dõi cổng gói báo cáo, nhắc hạn không sót đơn vị nào.', 80, 84),
           ('Hà', 'ga_analyst', 'Mê bảng tính, đối chiếu Nợ = Có trước khi ngủ.', 68, 95),
           ('Vy', 'ga_fx', 'Theo dõi tỷ giá mỗi sáng như theo dõi thời tiết.', 76, 88),
           ('Tín', 'ga_collect', 'Nói chuyện được với mọi kế toán trưởng công ty con.', 85, 78)],
    roles={'ga_collect': 'Điều phối gói báo cáo', 'ga_analyst': 'Chuyên viên hợp nhất', 'ga_fx': 'Theo dõi tỷ giá'},
    tip=0,
    physical=('ga_step', 'ga_submit', 'ga_pair', 'ga_tag'),
    free_actions=(),
    no_tick=('ga_open', 'ga_hint', 'ga_overtime', 'ga_chase'),
    activity=('🏢', 'Bàn hợp nhất Sông Hồng', [('Doanh thu bán cho công ty con', 'Loại trừ'), ('Doanh thu bán cho khách ngoài', 'Giữ lại'),
                                             ('Phải thu công ty con', 'Loại trừ'), ('Vay ngân hàng', 'Giữ lại')],
              ['Thu gói báo cáo', 'Đối chiếu nội bộ', 'Loại trừ giao dịch nội bộ', 'Trình HĐQT']),
    stories=[('Checklist cho Linh', ('Linh ở SH Pack hỏi: “Có cách nào để em không sai phụ lục nội bộ nữa không ạ?”',
                                     'Sau một hồ sơ hợp nhất nữa, bạn cùng Linh dựng checklist năm bước, bước nào cũng có ví dụ.',
                                     'Checklist được gửi cho mọi công ty con với tên gọi “Checklist Linh” — Linh ngượng đỏ mặt.')),
             ('Múi giờ của anh Kiên', ('Anh Kiên nhắn lúc nửa đêm: “Bên em mới 7 giờ tối, gửi gói báo cáo được chưa ạ?”',
                                       'Bạn hoàn thành thêm một hồ sơ rồi cùng anh Kiên thống nhất giờ chốt số theo giờ tập đoàn.',
                                       'SH Nami gửi tặng nhóm hợp nhất một hộp trà Nami: “Để thức khuya đỡ buồn ngủ.”')),
             ('Trang giải thích của Chủ tịch', ('Ông Đại hỏi: “Loại trừ là loại cái gì mà doanh thu tập đoàn nhỏ hơn cộng các công ty?”',
                                                'Sau một hồ sơ nữa, bạn vẽ cho ông sơ đồ: hàng đi vòng trong nhà không tạo ra doanh thu.',
                                                'Ông Đại dùng chính sơ đồ đó khi trình bày với cổ đông — và nhắc tên nhóm hợp nhất.'))],
    review_asides=['Bảng hợp nhất khớp tới từng xu, kiểm toán gật gù.', 'Loại trừ gọn gàng, không đếm doanh thu hai lần.',
                   'Ghi chú bàn giao đủ nguồn, người sau đọc là hiểu.', 'Quý này khóa sổ nhẹ như gió sông.'],
    situations=SITUATIONS,
    employment=dict(
        postings=[
            dict(id='ga-holding', org='Sông Hồng Holdings · Ban Tài chính tập đoàn', kind='group', title='Chuyên viên kế toán hợp nhất',
                 salary=(90, 120), probation_days=3, wants=['numbers', 'careful', 'communication'],
                 perks=['Làm việc với HĐQT & kiểm toán', 'Thưởng khóa sổ quý', 'Cao điểm cuối quý rất bận'],
                 culture='Nhóm hợp nhất 5 người ở công ty mẹ, làm việc với 4 công ty con và một công ty nước ngoài; coi trọng số có nguồn và email rõ ràng.',
                 questions=['ga_ic', 'ga_board', 'ga_fx', 'mistake'], reference=True),
            dict(id='ga-food', org='Thực phẩm Sông Hồng · Phòng kế toán', kind='subsidiary', title='Kế toán báo cáo tập đoàn (phía công ty con)',
                 salary=(75, 95), probation_days=2, wants=['careful', 'teamwork', 'calm'],
                 perks=['Được đào tạo hợp nhất', 'Chị Ngọc kèm cặp', 'Gần căng tin nhà máy'],
                 culture='Công ty con lớn nhất tập đoàn; bạn lập gói báo cáo và được luân chuyển sang nhóm hợp nhất ở mẹ.',
                 questions=['ga_ic', 'ga_deadline', 'conflict'], reference=True),
            dict(id='ga-intern', org='Sông Hồng Group · Chương trình thực tập tài chính', kind='internship', title='Thực tập sinh hợp nhất',
                 salary=(50, 65), probation_days=1, wants=['learning', 'tech'],
                 perks=['Nhận ngay', 'Luân chuyển các công ty con', 'Lương thực tập'],
                 culture='Chương trình 3 tháng cho người mới; mỗi tuần một buổi học với CFO.',
                 questions=['ga_deadline'], reference=False),
        ],
        questions={
            'ga_ic': dict(text='Công ty con A ghi phải thu B 500 xu, B ghi phải trả A 470 xu. Bạn làm gì trước tiên?', options=[
                dict(id='trace', label='So từng chứng từ hai bên, tìm khoản chỉ có một bên (hàng đi đường, hóa đơn chưa ghi, tiền đang chuyển, tỷ giá)', score=3, note='CFO gật đầu: đối chiếu từ chứng từ, không từ con số tổng.'),
                dict(id='split', label='Chia đôi chênh lệch, mỗi bên chỉnh 15 xu', score=0, note='Làm số khớp nhưng sai cả hai bên.'),
                dict(id='plug', label='Ghi 30 xu vào chi phí khác ở tập đoàn', score=1, note='Nhanh, nhưng giấu nguyên nhân thật.')]),
            'ga_board': dict(text='Chủ tịch muốn số “đẹp hơn” trước buổi gặp ngân hàng. Bạn phản hồi thế nào?', options=[
                dict(id='plan', label='Giữ số đúng, chuẩn bị giải thích và kế hoạch hành động kèm theo', score=3, note='Trung thực mà vẫn giúp được lãnh đạo.'),
                dict(id='comply', label='Chỉnh trình bày theo ý Chủ tịch', score=0, note='Rủi ro pháp lý và mất niềm tin.'),
                dict(id='refuse', label='Từ chối và không đề xuất gì thêm', score=1, note='Đúng nguyên tắc nhưng chưa giúp giải quyết vấn đề.')]),
            'ga_fx': dict(text='Chuyển đổi báo cáo công ty con nước ngoài: tài sản và doanh thu dùng tỷ giá nào?', options=[
                dict(id='right', label='Tài sản: tỷ giá cuối kỳ; doanh thu: tỷ giá bình quân kỳ', score=3, note='Chuẩn theo quy chế tập đoàn.'),
                dict(id='same', label='Tất cả dùng tỷ giá cuối kỳ cho đơn giản', score=1, note='Đơn giản nhưng sai với doanh thu, chi phí.'),
                dict(id='best', label='Chọn tỷ giá nào cho kết quả đẹp nhất', score=0, note='Không bao giờ chọn tỷ giá theo kết quả mong muốn.')]),
            'ga_deadline': dict(text='Một công ty con trễ hạn nộp gói báo cáo hai ngày. Bạn làm gì?', options=[
                dict(id='help', label='Hỏi họ vướng gì, gửi mẫu/checklist, thống nhất hạn mới cụ thể', score=3, note='Gỡ nguyên nhân, không chỉ nhắc hạn.'),
                dict(id='estimate', label='Tự ước tính số của họ để kịp hợp nhất', score=0, note='Số không có chứng từ là số không đáng tin.'),
                dict(id='escalate', label='Báo ngay Chủ tịch', score=1, note='Quá sớm, làm căng quan hệ.')]),
        }),
    guide='Bàn đối chiếu: chạm một dòng sổ bên bán và một dòng sổ bên mua cùng chứng từ để ghép; dòng chỉ có một bên thì chọn lý do; khớp hết thì loại trừ. '
          'Hồ sơ khác: mở tài liệu → làm từng bước → ghi chú bàn giao → nộp. Mỗi hồ sơ có giờ hạn; đủ 6 mốc là xong quý.',
)
