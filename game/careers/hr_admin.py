"""Công ty CP Cánh Diều — an employed HR & admin officer (plugin career).

Real desk work of a small company's HR office, checked by hand: sort a stack of CVs against the
posting (lies the social insurance record gives away, a director's nephew, a biased note in the
margin), go through the week's timesheet cell by cell against leave forms and the gate camera,
proof-read a labour contract against the offer letter and ID card, fit interviews into rooms and
people's free hours, and answer the hard conversations (a foreman who wants someone fired on the
spot, a pregnant colleague the director does not want to renew).

The dossier mechanics are shared with the other Cánh Diều desks (office_work.py); the office day,
deadlines, the boss's trust and colleagues come from office.py and the corp_accounting care helpers.
Every rule here is a simplified GAME rule, not legal advice.
"""
from __future__ import annotations

from . import kit
from . import office_work as ow

ID = 'hr_admin'
P = 'hc_'

PEOPLE = [
    ('Chị Huyền', 'Trưởng phòng Hành chính – Nhân sự', 'Nói nhẹ nhưng soát kỹ; ghét nhất hồ sơ thiếu chữ ký.', 'picky'),
    ('Anh Quân', 'Giám đốc Công ty Cánh Diều', 'Quyết nhanh, đổi ý còn nhanh hơn.', 'bossy'),
    ('Linh', 'Nhân viên kinh doanh', 'Nhanh nhảu, hay quên quẹt thẻ chấm công.', 'genz'),
    ('Chú Lâm', 'Tổ trưởng xưởng may balo', 'Thương thợ, ghét giấy tờ, nóng như lò hơi.', 'warm'),
    ('Cô Hằng', 'Kế toán trưởng', 'Chỉ tin giấy có dấu đỏ.', 'sour'),
    ('Anh Dũng', 'Thợ may lâu năm', 'Ít nói, tay nghề giỏi nhất tổ.', 'quiet'),
]
BOSS = 'Chị Huyền'

# ================================================================ dossier 1: sorting CVs
POSTS = [
    dict(id='kho', title='Nhân viên kho', exp=1, where='làm kho', skill='Excel cơ bản', extra=('kiểm đếm hàng', 'xếp pallet'),
         cert=None, lo=6500, hi=8000),
    dict(id='may', title='Thợ may mẫu', exp=2, where='may mẫu', skill='máy may công nghiệp', extra=('đọc rập', 'may khóa kéo'),
         cert=None, lo=7500, hi=9500),
    dict(id='online', title='Nhân viên bán hàng online', exp=1, where='bán hàng online', skill='chụp ảnh sản phẩm',
         extra=('livestream', 'trả lời tin nhắn khách'), cert=None, lo=6000, hi=8000),
    dict(id='xe', title='Tài xế giao hàng', exp=2, where='lái xe tải', skill='thuộc đường nội thành', extra=('bốc xếp hàng', 'giao nhận chứng từ'),
         cert='bằng lái xe hạng C', lo=8000, hi=10000),
    dict(id='ketoan', title='Kế toán kho', exp=1, where='kế toán', skill='phần mềm kế toán', extra=('Excel nâng cao', 'đối chiếu công nợ'),
         cert='bằng cao đẳng kế toán', lo=7000, hi=9000),
]
OTHER_SKILLS = ('tiếng Anh giao tiếp', 'Photoshop', 'nấu ăn', 'đàn guitar', 'cờ tướng', 'chạy bộ', 'trồng cây')
CV_BINS = [dict(id='invite', label='Mời phỏng vấn', emoji='✅'), dict(id='verify', label='Cần xác minh', emoji='🔎'),
           dict(id='reject', label='Không mời', emoji='✖️')]
EMAILS = ('heocon.2k1', 'boy.lanh.lung99', 'congchua.ngu.quen', 'sieunhan.do', 'meomeo.kute')
BIAS = [
    (True, '“Mới cưới, chắc sắp sinh con. Loại đi em.” — Anh Quân'),
    (None, '“Quê xa thế, làm vài tháng lại về quê thôi.” — Linh'),
    (None, '“Lớn tuổi rồi, khó bảo lắm.” — Chú Lâm'),
    (True, '“Con gái chân yếu tay mềm, làm sao bê nổi.” — Chú Lâm'),
]


def _cv_card(rng, i: int, post: dict, kind: str, used: set) -> dict:
    bias = BIAS[rng.randrange(len(BIAS))] if kind == 'bias' else None
    name, female = ow.person(rng, used, bias[0] if bias and bias[0] is not None else None)
    need = post['exp']
    years = need + rng.choice((0, 1, 2, 3))
    skills = [post['skill'], rng.choice(post['extra']), rng.choice(OTHER_SKILLS)]
    cert = f'Có {post["cert"]}' if post['cert'] else rng.choice(('Tốt nghiệp THPT', 'Trung cấp nghề', 'Cao đẳng'))
    pay = rng.randrange(post['lo'], post['hi'] + 1, 250)
    age = rng.randrange(22, 38)
    town = rng.choice(ow.HOMETOWNS)
    note, extra = None, []
    out = dict(bin='invite', why='Đủ kinh nghiệm, kỹ năng và bằng cấp theo yêu cầu.', sev=2, code='cv_fit')
    if kind == 'fit' and rng.random() < 0.5:
        extra.append(f'📎 Tra cứu BHXH: đóng {years * 12} tháng ở chỗ làm cũ.')
    elif kind in ('no_exp', 'nephew_out'):
        years = rng.randrange(0, need)
        out.update(bin='reject', why=f'Vị trí cần ít nhất {need} năm kinh nghiệm, hồ sơ mới có {years or "chưa có"}{" năm" if years else ""}.',
                   sev=1, code='cv_exp')
    elif kind == 'no_skill':
        skills = [rng.choice(post['extra'])] + rng.sample(OTHER_SKILLS, 2)
        out.update(bin='reject', why=f'Thiếu kỹ năng bắt buộc: {post["skill"]}.', sev=1, code='cv_skill')
    elif kind == 'no_cert':
        cert = f'Chưa có {post["cert"]}'
        out.update(bin='reject', why=f'Vị trí bắt buộc có {post["cert"]}.', sev=1, code='cv_cert')
    elif kind == 'gap_paper':
        cert = f'Có {post["cert"]} (chưa gửi bản sao)'
        out.update(bin='verify', why='Bằng là yêu cầu bắt buộc mà chưa có bản sao — xin bổ sung rồi mới mời.', sev=1, code='cv_paper')
    elif kind == 'bhxh_lie':
        years = need + rng.choice((1, 2, 3))
        months = rng.randrange(3, max(4, need * 12 - 2))
        extra.append(f'📎 Tra cứu BHXH: chỉ đóng {months} tháng.')
        out.update(bin='verify', why=f'CV ghi {years} năm mà BHXH chỉ có {months} tháng — gọi xác minh chỗ làm cũ trước.', sev=2, code='cv_lie')
    elif kind == 'high_pay':
        pay = post['hi'] + rng.choice((5, 10, 15, 20)) * 100
        out.update(why='Lương mong muốn cao hơn khung chỉ cần thương lượng; đủ điều kiện thì vẫn mời.', sev=1, code='cv_pay')
    elif kind == 'odd_email':
        extra.append(f'Email: {rng.choice(EMAILS)}@gmail.com')
        note = '“Email gì mà trẻ con thế, loại cho nhanh.” — Linh'
        out.update(why='Địa chỉ email ngộ nghĩnh không phải lý do để loại người đủ điều kiện.', sev=2, code='cv_email')
    elif kind == 'bias':
        note = bias[1]
        if 'Lớn tuổi' in note:
            age = rng.randrange(44, 52)
        out.update(why='Không loại vì giới tính, hôn nhân, quê quán hay tuổi tác — chỉ xét yêu cầu công việc.', sev=3, code='cv_bias')
    if kind in ('nephew_in', 'nephew_out'):
        note = '“Cháu anh đấy, cho vào thẳng nhé.” — Anh Quân'
        if kind == 'nephew_in':
            out.update(why='Người quen giới thiệu vẫn phỏng vấn như mọi người; hồ sơ đủ điều kiện.', sev=2, code='cv_nephew')
        else:
            out.update(why=f'Người quen giới thiệu vẫn xét như mọi người: chưa đủ {need} năm kinh nghiệm.', sev=2, code='cv_nephew')
    lines = [f'Kinh nghiệm: {years} năm {post["where"]}' if years else 'Kinh nghiệm: chưa đi làm',
             f'Kỹ năng: {", ".join(skills)}', f'Bằng cấp: {cert}', f'Lương mong muốn: {ow.xu(pay)} xu/tháng'] + extra
    return dict(id=f'c{i}', title=name, sub=f'{age} tuổi · {town}', lines=lines, note=note,
                _bin=out['bin'], _why=out['why'], _sev=out['sev'], _code=out['code'], _years=years)


def g_cv(rng, ctx: dict) -> dict:
    post = rng.choice(POSTS)
    tier = ctx['tier']
    lacking = ['no_exp', 'no_skill'] + (['no_cert'] if post['cert'] else [])
    kinds = ['fit', rng.choice(lacking), 'bhxh_lie']
    pool = ['fit', 'high_pay', 'odd_email', 'no_exp', 'no_skill']
    if tier >= 1:
        pool += ['bias', 'nephew_in', 'nephew_out'] + (['gap_paper'] if post['cert'] else [])
    n = min(8, 5 + (tier >= 1) + (tier >= 3) + ctx['more'])
    while len(kinds) < n:
        k = rng.choice(pool)
        if k in ('bias', 'nephew_in', 'nephew_out', 'odd_email') and any(x == k or (k.startswith('nephew') and x.startswith('nephew')) for x in kinds):
            continue
        kinds.append(k)
    rng.shuffle(kinds)
    used: set = set()
    items = [_cv_card(rng, i, post, k, used) for i, k in enumerate(kinds)]
    tw = None
    if ctx['twist']:
        lie = [it for it, k in zip(items, kinds) if k == 'bhxh_lie']
        fit = [it for it, k in zip(items, kinds) if k == 'fit']
        if lie and rng.random() < 0.6:
            it = lie[0]
            tw = dict(at=n - 2, item=it['id'], bin='invite', sev=1,
                      note=f'Chị Huyền: “{ow.short(it["title"])} vừa gửi sổ BHXH của chỗ làm cũ — đủ {it["_years"]} năm thật đấy em.”',
                      why='Đã có sổ BHXH bổ sung, đủ kinh nghiệm.')
        else:
            it = fit[0]
            tw = dict(at=n - 2, item=it['id'], bin='reject', sev=1,
                      note=f'{ow.short(it["title"])} vừa gọi: đã nhận việc chỗ khác, xin rút hồ sơ.', why='Ứng viên đã rút hồ sơ.')
    for it in items:
        it.pop('_years')
    rules = [f'Kinh nghiệm: ít nhất {post["exp"]} năm {post["where"]}.', f'Kỹ năng bắt buộc: {post["skill"]}.']
    if post['cert']:
        rules.append(f'Bắt buộc có {post["cert"]} (kèm bản sao).')
    rules.append(f'Khung lương: {ow.xu(post["lo"])}–{ow.xu(post["hi"])} xu/tháng (cao hơn thì thương lượng).')
    return dict(npc=0, title=f'Lọc hồ sơ: {post["title"]}',
                opening=f'Chị Huyền đặt chồng hồ sơ lên bàn: “Vị trí {post["title"].lower()} có {n} bạn nộp. Em lọc giúp chị nhé.”',
                brief=f'Lọc {n} hồ sơ ứng tuyển {post["title"].lower()}: xếp mỗi hồ sơ vào một khay, đúng yêu cầu vị trí.',
                papers=[dict(id='post', emoji='📌', title=f'Yêu cầu vị trí: {post["title"]}', lines=rules),
                        dict(id='rule', emoji='⚖️', title='Nguyên tắc lọc hồ sơ', lines=[
                            'Chỉ xét yêu cầu công việc: không loại vì giới tính, hôn nhân, tuổi, quê quán.',
                            'CV và tra cứu BHXH lệch nhau, hoặc thiếu bản sao bằng bắt buộc → Cần xác minh.',
                            'Người quen giới thiệu vẫn xét như mọi người.'])],
                work=dict(type='sort', bins=CV_BINS, items=items, _twist=tw))


# ================================================================ dossier 2: the week's timesheet
WEEK = ('T2', 'T3', 'T4', 'T5', 'T6')
WEEK_NAMES = ('thứ Hai', 'thứ Ba', 'thứ Tư', 'thứ Năm', 'thứ Sáu')
TS_OPTS = ['✓ Đủ công', 'Đi muộn', 'Về sớm', 'Thiếu giờ ra/vào', 'Nghỉ có phép', 'Nghỉ không phép', 'Chấm hộ', 'Đi công tác']
OK, LATE, EARLY, MISS, LEAVE, ABSENT, PROXY, TRIP = range(8)


def _in(rng) -> str:
    return f'07:{rng.randrange(40, 60):02d}'


def _out(rng) -> str:
    return f'17:{rng.randrange(0, 20):02d}'


def g_timesheet(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    used: set = {'Linh', 'Dũng'}
    names = ['Linh (Kinh doanh)', 'Anh Dũng (Xưởng)'] + [f'{ow.person(rng, used)[0]}' for _ in range(1 + (tier >= 1))]
    names = names[:3 + (tier >= 1)]
    rng.shuffle(names)
    kinds = ['late', 'early', 'miss', 'leave', 'absent', 'grace']
    if tier >= 1:
        kinds += ['trip', 'proxy', 'unapproved', 'grace']
    n = min(8, 4 + min(tier, 2) + ctx['more'])
    cells = [(r, d) for r in range(len(names)) for d in range(5)]
    rng.shuffle(cells)
    want = []
    if ctx['twist']:
        want.append('absent')
    while len(want) < n:
        want.append(rng.choice(kinds))
    special = dict(zip(cells[:n], want))
    notes, rows = [], []
    tw = None
    for r, who in enumerate(names):
        row = [who]
        nm = who.split(' (')[0]
        for d in range(5):
            k = special.get((r, d), 'ok')
            sid = f'r{r}d{d}'
            if k == 'ok':
                row.append(ow.cell(sid, f'{_in(rng)}–{_out(rng)}', OK))
            elif k == 'grace':
                row.append(ow.cell(sid, f'08:0{rng.randrange(1, 6)}–{_out(rng)}', OK, 'Trễ trong 5 phút cho phép, vẫn đủ công.', 1, 'ts_grace', True))
            elif k == 'late':
                row.append(ow.cell(sid, f'08:{rng.randrange(10, 50):02d}–{_out(rng)}', LATE, 'Vào sau 08:05 là đi muộn.', 1, 'ts_late'))
            elif k == 'early':
                row.append(ow.cell(sid, f'{_in(rng)}–16:{rng.randrange(5, 50):02d}', EARLY, 'Ra trước 17:00 là về sớm.', 1, 'ts_early'))
            elif k == 'miss':
                row.append(ow.cell(sid, rng.choice((f'{_in(rng)}– ?', f' ? –{_out(rng)}')), MISS, 'Máy chỉ ghi một lần quẹt thẻ.', 1, 'ts_miss'))
            elif k == 'leave':
                notes.append(f'✅ Đơn nghỉ phép ĐÃ DUYỆT: {nm} — {WEEK_NAMES[d]}.')
                row.append(ow.cell(sid, '—', LEAVE, 'Có đơn nghỉ phép đã duyệt.', 2, 'ts_leave'))
            elif k == 'absent':
                row.append(ow.cell(sid, '—', ABSENT, 'Vắng mà không có đơn từ gì.', 1, 'ts_absent'))
                if ctx['twist'] and tw is None:
                    tw = dict(at=max(2, n - 2), seg=sid, ok=LEAVE, sev=2, why='Đơn nghỉ phép được duyệt bổ sung.',
                              note=f'{nm} mang đơn nghỉ phép {WEEK_NAMES[d]} lên — chị Huyền vừa ký duyệt.')
            elif k == 'unapproved':
                notes.append(f'⏳ Đơn nghỉ phép CHƯA DUYỆT: {nm} — {WEEK_NAMES[d]}.')
                row.append(ow.cell(sid, '—', ABSENT, 'Đơn chưa được duyệt thì chưa tính là nghỉ có phép.', 1, 'ts_unapproved'))
            elif k == 'trip':
                notes.append(f'🚚 Lịch công tác: {nm} đi giao hàng mẫu ở Bình Dương — {WEEK_NAMES[d]}.')
                row.append(ow.cell(sid, '—', TRIP, 'Đi công tác có lịch thì vẫn tính công.', 2, 'ts_trip'))
            elif k == 'proxy':
                notes.append(f'📹 Camera cổng: {nm} không đến công ty {WEEK_NAMES[d]}, nhưng máy vẫn ghi giờ quẹt thẻ.')
                row.append(ow.cell(sid, f'{_in(rng)}–{_out(rng)}', PROXY, 'Camera cho thấy không đến mà thẻ vẫn quẹt: có người chấm hộ.', 2, 'ts_proxy'))
        rows.append(row)
    rng.shuffle(notes)
    return dict(npc=0, title='Soát bảng chấm công tuần',
                opening='Chị Huyền gửi file: “Máy chấm công xuất bảng tuần rồi. Em soát từng ô, chiều chị chốt công nhé.”',
                brief=f'Soát bảng chấm công {len(names)} người × 5 ngày: chạm ô nào sai và chọn lý do; ô đúng thì để nguyên.',
                papers=[dict(id='rule', emoji='🕗', title='Giờ làm', lines=['Vào 08:00 (trễ tới 08:05 vẫn đủ công) · Ra 17:00.',
                                                                         'Mỗi ngày phải có đủ giờ vào và giờ ra.',
                                                                         'Nghỉ chỉ được tính có phép khi đơn đã duyệt.']),
                        dict(id='notes', emoji='🗂️', title='Đơn từ & ghi chú trong tuần', lines=notes or ['Tuần này không có đơn từ nào.'])],
                work=dict(type='mark', opts=TS_OPTS, blocks=[dict(k='table', head=['Nhân viên', *WEEK], rows=rows)], _twist=tw))


# ================================================================ dossier 3: proof-reading a labour contract
def _date(d: int, m: int, y: int) -> str:
    return f'{d:02d}/{m:02d}/{y}'


def _swap_digits(rng, s: str) -> str:
    for _ in range(20):
        i = rng.randrange(len(s) - 1)
        if s[i] != s[i + 1]:
            return s[:i] + s[i + 1] + s[i] + s[i + 2:]
    return s[:-1] + str((int(s[-1]) + 1) % 10)


def g_contract(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    used: set = set()
    name, female = ow.person(rng, used)
    post = rng.choice(POSTS)
    other = rng.choice([x for x in POSTS if x['id'] != post['id']])
    dd, mm, yy = rng.randrange(1, 29), rng.randrange(1, 13), rng.randrange(1990, 2004)
    if dd <= 12 and dd != mm and rng.random() < 0.7:
        dob_bad = _date(mm, dd, yy)
    else:
        dob_bad = _date(dd, mm, yy + 1)
    dob = _date(dd, mm, yy)
    cccd = '0' + ''.join(rng.choice('0123456789') for _ in range(11))
    salary = rng.randrange(post['lo'], post['hi'] + 1, 500)
    sd, sm = rng.randrange(1, 21), rng.randrange(1, 13)
    start = _date(sd, sm, 2025)
    prob = rng.choice((30, 60))
    pct = rng.choice((85, 90, 100))
    words = name.split()
    bad_name = ' '.join(words[:1] + [ow.plain_text(words[1])] + words[2:]) if ow.plain_text(words[1]) != words[1] else ow.plain_text(name)
    if bad_name == name:
        bad_name = ' '.join([words[0], rng.choice([m for m in ow.MIDDLE[female] if m != words[1]]), words[2]])
    alt_name = ' '.join(words[:2] + [rng.choice([g for g in ow.GIVEN[female] if g != words[2]])])
    raise_to = salary + 500
    segs = dict(
        name=(bad_name, name, [alt_name], 'Tên phải đúng từng dấu như trên CCCD.', 1, 'ct_name'),
        dob=(dob_bad, dob, [_date(dd, mm, yy - 1)], 'Ngày sinh phải khớp CCCD.', 1, 'ct_dob'),
        cccd=(_swap_digits(rng, cccd), cccd, [cccd[:-1] + str((int(cccd[-1]) + 3) % 10)], 'Số CCCD phải khớp từng chữ số.', 2, 'ct_id'),
        post=(other['title'], post['title'], [rng.choice([x['title'] for x in POSTS if x['id'] not in (post['id'], other['id'])])],
              'Vị trí phải đúng thư mời nhận việc.', 2, 'ct_post'),
        start=(_date(min(28, sd + 7), sm, 2025), start, [_date(sd, sm % 12 + 1, 2025)], 'Ngày bắt đầu theo thư mời nhận việc.', 1, 'ct_start'),
        prob=('90 ngày', f'{prob} ngày', ['45 ngày' if prob == 30 else '30 ngày'], f'Thư mời ghi {prob} ngày; thử việc không quá 60 ngày.', 2, 'ct_prob'),
        pct=('70%', f'{pct}%', ['80%'], f'Thư mời ghi {pct}%; lương thử việc không thấp hơn 85%.', 2, 'ct_pct'),
        salary=(ow.xu(salary + rng.choice((-500, 1000))), ow.xu(salary), [ow.xu(raise_to)], 'Lương phải đúng thư mời nhận việc.', 2, 'ct_pay'),
        ins=('không đóng bảo hiểm, cộng thẳng vào lương', 'đóng BHXH, BHYT, BHTN theo quy định', ['đóng bảo hiểm sau 6 tháng làm việc'],
             'Hợp đồng từ 1 tháng trở lên phải đóng bảo hiểm bắt buộc.', 3, 'ct_ins'),
        sign=('(chưa ký)', 'Mời Bên B ký trước khi lưu', ['Ký thay Bên B cho kịp'], 'Thiếu chữ ký người lao động thì hợp đồng chưa có hiệu lực.', 2, 'ct_sign'),
    )
    n_bad = min(len(segs), 2 + min(tier, 2) + ctx['more'])
    bad = set(rng.sample(sorted(segs), n_bad))
    twist = ctx['twist'] and 'salary' not in bad
    S = {}
    for k, (wrong, right, decoys, why, sev, code) in segs.items():
        if k in bad:
            S[k] = ow.pick(k, wrong, right, decoys, rng, why, sev, code)
        elif k == 'sign':
            S[k] = ow.pick(k, 'Đã ký', 'Đã ký', ['Mời Bên B ký trước khi lưu', 'Ký thay Bên B cho kịp'], rng)
        else:
            S[k] = ow.pick(k, right, right, [wrong] + decoys, rng)
    tw = None
    if twist:
        sg = S['salary']
        tw = dict(at=max(2, n_bad), seg='salary', ok=sg['opts'].index(ow.xu(raise_to)), sev=2,
                  note=f'Anh Quân vừa duyệt: lương chính thức của {ow.short(name)} nâng lên {ow.xu(raise_to)} xu cho giữ chân người giỏi.',
                  why='Giám đốc đã duyệt mức lương mới.')
    def T(text: str) -> dict:
        return dict(t=text)

    blocks = [
        dict(k='h', segs=[T(f'HỢP ĐỒNG LAO ĐỘNG số {rng.randrange(10, 99)}/2025/HĐLĐ-CD')]),
        dict(k='p', segs=[T('Bên A: Công ty CP Cánh Diều, đại diện ông Trần Minh Quân — Giám đốc.')]),
        dict(k='p', segs=[T('Bên B: '), S['name'], T(', sinh ngày '), S['dob'], T(', CCCD số '), S['cccd'], T('.')]),
        dict(k='p', segs=[T('Điều 1. Vị trí: '), S['post'], T(', làm việc tại trụ sở Cánh Diều.')]),
        dict(k='p', segs=[T('Điều 2. Thời hạn 12 tháng, bắt đầu từ ngày '), S['start'], T('.')]),
        dict(k='p', segs=[T('Điều 3. Thử việc '), S['prob'], T(', lương thử việc bằng '), S['pct'], T(' lương chính thức.')]),
        dict(k='p', segs=[T('Điều 4. Lương chính thức '), S['salary'], T(' xu/tháng, trả ngày 10 hằng tháng.')]),
        dict(k='p', segs=[T('Điều 5. Bảo hiểm: Công ty '), S['ins'], T('.')]),
        dict(k='p', segs=[T('Chữ ký — Bên A: đã ký, đóng dấu · Bên B: '), S['sign']]),
    ]
    return dict(npc=0, title=f'Soát hợp đồng: {name}',
                opening=f'Chị Huyền đưa bản nháp: “Hợp đồng của {ow.short(name)} đây. Em soát với thư mời và CCCD rồi đưa chị lưu nhé.”',
                brief='Soát hợp đồng lao động với thư mời nhận việc và CCCD: chạm chỗ sai, chọn cách viết đúng. Chỗ đúng thì để nguyên.',
                papers=[dict(id='offer', emoji='✉️', title='Thư mời nhận việc', lines=[
                            f'Họ tên: {name}', f'Vị trí: {post["title"]}', f'Ngày bắt đầu: {start}', f'Thử việc: {prob} ngày, hưởng {pct}% lương',
                            f'Lương chính thức: {ow.xu(salary)} xu/tháng', 'Đóng BHXH, BHYT, BHTN đầy đủ theo quy định']),
                        dict(id='id', emoji='🪪', title='CCCD (bản chụp)', lines=[f'Họ và tên: {name.upper()}', f'Ngày sinh: {dob}', f'Số: {cccd}']),
                        dict(id='rule', emoji='⚖️', title='Quy định của phòng', lines=[
                            'Thử việc tối đa 60 ngày; lương thử việc ít nhất 85% lương chính thức.',
                            'Hợp đồng từ 1 tháng trở lên: đóng bảo hiểm bắt buộc.', 'Hai bên ký đủ mới lưu hồ sơ. Không ký thay.'])],
                work=dict(type='mark', blocks=blocks, _twist=tw))


# ================================================================ dossier 4: interview schedule
ROOMS = [dict(id='nho', label='Phòng họp nhỏ', cap=3, tags=[]), dict(id='lon', label='Phòng họp lớn', cap=8, tags=['tv']),
         dict(id='xuong', label='Góc thử tay nghề', cap=4, tags=['may'])]
HOURS = [dict(id='h0830', label='08:30', half='am'), dict(id='h0930', label='09:30', half='am'), dict(id='h1030', label='10:30', half='am'),
         dict(id='h1330', label='13:30', half='pm'), dict(id='h1430', label='14:30', half='pm'), dict(id='h1530', label='15:30', half='pm')]
TAGS = dict(tv='màn hình trình chiếu', may='máy may để thử tay nghề')
BUSY_TEXT = {'Chị Huyền': ('họp giao ban', 'đi khám sức khỏe định kỳ'), 'Chú Lâm': ('chạy đơn hàng gấp', 'kiểm hàng xuất'),
             'Anh Quân': ('gặp ngân hàng', 'họp với đối tác'), 'Cô Hằng': ('đi nộp thuế', 'chốt sổ'), 'Linh': ('đi gặp khách', 'livestream bán hàng')}


def g_interview(rng, ctx: dict) -> dict:
    tier = ctx['tier']
    used: set = set()
    cands = [ow.person(rng, used)[0] for _ in range(6)]
    who_of = dict(kho=cands[0], may=cands[1], tk=cands[2], kt=cands[3], xe=cands[4])
    pool = [
        dict(id='kho', title=f'Phỏng vấn {ow.short(cands[0])} · Nhân viên kho', who=['Chị Huyền'], size=2, needs=[]),
        dict(id='may', title=f'Thử tay nghề {ow.short(cands[1])} · Thợ may', who=['Chú Lâm'], size=2, needs=['may']),
        dict(id='tk', title=f'Xem portfolio {ow.short(cands[2])} · Thiết kế balo', who=['Chị Huyền', 'Anh Quân'], size=3, needs=['tv']),
        dict(id='nhom', title='Phỏng vấn nhóm 5 bạn bán hàng', who=['Chị Huyền', 'Linh'], size=7, needs=[]),
        dict(id='kt', title=f'Phỏng vấn {ow.short(cands[3])} · Kế toán kho', who=['Chị Huyền', 'Cô Hằng'], size=3, needs=[]),
        dict(id='xe', title=f'Phỏng vấn {ow.short(cands[4])} · Tài xế', who=['Chú Lâm'], size=2, needs=[]),
    ]
    n = min(6, 3 + (tier >= 1) + (tier >= 2) + ctx['more'])
    items = rng.sample(pool, n)
    before = []
    if tier >= 1 and rng.random() < 0.6:
        first = next((it for it in items if it['id'] in ('kho', 'kt', 'xe')), None)
        if first:
            nm = ow.short(who_of[first['id']])
            v2 = dict(id='v2', title=f'Vòng 2: {nm} gặp giám đốc', who=['Anh Quân'], size=2, needs=[])
            items.append(v2)
            before.append(dict(a=first['id'], b='v2', text=f'Vòng 2 của {nm} phải sau vòng 1.'))
    people = sorted({w for it in items for w in it['who']})
    busy = [dict(who=w, text=rng.choice(BUSY_TEXT[w])) for w in rng.sample(people, min(len(people), 1 + (tier >= 2)))]
    taken = [dict(text='{room} lúc {time} đã có lớp đào tạo an toàn lao động.'), dict(text='Phòng kinh doanh đã đặt {room} lúc {time}.')]
    taken = taken[:1 + (tier >= 1)]
    windows = []
    solo = [it for it in items if it['id'] in ('kho', 'may', 'kt', 'xe', 'tk')]
    if solo and rng.random() < 0.7:
        it = rng.choice(solo)
        nm = ow.short(who_of[it['id']])
        half = rng.choice(('am', 'pm'))
        windows.append(dict(item=it['id'], half=half, text=f'{nm} chỉ đến được buổi {"sáng" if half == "am" else "chiều"} (đang làm ca ở chỗ cũ).'))
    tb = None
    if ctx['twist']:
        who = 'Anh Quân' if 'Anh Quân' in people else 'Chị Huyền'
        tb = dict(who=who, text='đổi lịch đột xuất',
                  note=('Anh Quân đổi ý: “Anh phải đi gặp đối tác, mấy giờ đó anh không ở công ty đâu nhé.”' if who == 'Anh Quân'
                        else 'Chị Huyền vừa bị gọi lên họp ban giám đốc — mấy giờ đó chị không phỏng vấn được.'))
    work = ow.build_slots(rng, ROOMS, HOURS[:5 + (tier >= 1)], TAGS, items, busy, taken, windows, before, tb)
    return dict(npc=0, title=f'Xếp lịch phỏng vấn ({len(items)} buổi)',
                opening='Chị Huyền dán tờ lịch lên bàn: “Mai có mấy buổi phỏng vấn. Em xếp phòng, xếp giờ sao cho không ai bị trùng nhé.”',
                brief=f'Xếp {len(items)} buổi phỏng vấn vào phòng và giờ: không trùng người, đủ chỗ ngồi, đúng thiết bị, tránh giờ người ta bận.',
                papers=[dict(id='rooms', emoji='🚪', title='Phòng', lines=['Phòng họp nhỏ: 3 chỗ', 'Phòng họp lớn: 8 chỗ, có màn hình trình chiếu',
                                                                         'Góc thử tay nghề: 4 chỗ, có máy may'])],
                work=work)


# ================================================================ dossier 5: a hard conversation
CASES = [
    dict(id='fire', npc=3, title='Chú Lâm đòi đuổi việc Anh Dũng',
         opening='Chú Lâm đập tay xuống bàn: “Thằng Dũng tuần này đi muộn ba buổi! Làm quyết định cho nó nghỉ luôn hôm nay!”',
         facts=[dict(id='rule', title='Nội quy kỷ luật', text='Đi muộn: nhắc nhở → lập biên bản → kỷ luật theo quy trình, có họp và cho người lao động trình bày. Không đuổi việc bằng lời.'),
                dict(id='why', title='Hỏi chuyện Anh Dũng', text='Con anh nằm viện nhi, sáng nào anh cũng ghé đưa cơm rồi mới tới xưởng.'),
                dict(id='skill', title='Sổ năng suất tổ', text='Dũng là thợ có tay nghề cao nhất tổ, chưa từng bị nhắc nhở trước đây.')],
         options=[dict(id='talk', label='Gặp riêng Dũng, lập biên bản nhắc nhở theo nội quy, đề xuất chị Huyền cho anh vào ca 08:30 trong hai tuần',
                       requires=['rule', 'why'], _q='good', _out='Dũng xin lỗi, đi đúng giờ ca mới; Chú Lâm giữ được thợ giỏi. Mọi thứ có giấy tờ rõ ràng.'),
                  dict(id='skip', label='Nói Chú Lâm bình tĩnh, bỏ qua lần này không ghi gì', requires=[], _q='ok',
                       _out='Êm chuyện hôm nay, nhưng tuần sau Dũng vẫn muộn và Chú Lâm lại nổi nóng.'),
                  dict(id='fire', label='Soạn quyết định cho thôi việc ngay như Chú Lâm muốn', requires=[], _q='bad', _sev=3,
                       _out='Đuổi việc sai quy trình: Dũng khiếu nại lên phòng lao động, công ty phải nhận lại và bồi thường.')]),
    dict(id='peek', npc=2, title='Linh hỏi lương đồng nghiệp',
         opening='Linh ghé tai: “Chị ơi, bạn mới vào bên kinh doanh lương bao nhiêu thế? Nghe đồn hơn em.”',
         facts=[dict(id='secret', title='Quy định bảo mật', text='Lương từng người là thông tin riêng; chỉ phòng nhân sự và kế toán được xem.'),
                dict(id='scale', title='Thang lương công khai', text='Công ty có thang bậc lương theo vị trí và thâm niên, ai cũng xem được trên bảng tin.'),
                dict(id='review', title='Lịch xét lương', text='Tháng sau đến kỳ xét nâng lương; Linh đủ điều kiện nộp đề xuất.')],
         options=[dict(id='scale', label='Không nói lương người khác; chỉ Linh thang lương công khai và cách nộp đề xuất xét nâng lương',
                       requires=['secret', 'scale'], _q='good', _out='Linh không biết lương bạn kia nhưng biết mình đủ điều kiện đề xuất, về hăng hái hẳn.'),
                  dict(id='no', label='Từ chối gọn: “Bí mật em ạ”', requires=[], _q='ok', _out='Đúng quy định, nhưng Linh về chỗ vẫn ấm ức.'),
                  dict(id='tell', label='Nói nhỏ mức lương cho Linh đỡ tò mò', requires=[], _q='bad', _sev=3,
                       _out='Chuyện lan khắp phòng kinh doanh; bạn mới bị soi, chị Huyền phải giải trình về lộ thông tin lương.')]),
    dict(id='preg', npc=1, title='Giám đốc không muốn gia hạn hợp đồng',
         opening='Anh Quân gọi bạn vào: “Hợp đồng của Hoa bên thiết kế sắp hết. Đang bầu thì thôi, đừng ký tiếp, ghi là cơ cấu lại.”',
         facts=[dict(id='law', title='Quy định bảo vệ lao động nữ', text='Không được lấy lý do mang thai để từ chối giao kết tiếp hay chấm dứt hợp đồng.'),
                dict(id='perf', title='Đánh giá công việc của Hoa', text='Hai năm liền xếp loại tốt; mẫu balo của Hoa bán chạy nhất mùa tựu trường.'),
                dict(id='plan', title='Kế hoạch nhân sự', text='Phòng thiết kế đang thiếu người; nghỉ sinh có thể sắp người hỗ trợ tạm.')],
         options=[dict(id='memo', label='Trình anh Quân bằng văn bản: quy định, đánh giá của Hoa, đề xuất gia hạn và kế hoạch người hỗ trợ khi chị nghỉ sinh',
                       requires=['law', 'perf'], _q='good', _out='Anh Quân đọc xong gật gù: “Ừ, giữ Hoa.” Hoa yên tâm làm việc, công ty tránh được rắc rối.'),
                  dict(id='delay', label='Ậm ừ, để hợp đồng hết hạn rồi tính', requires=[], _q='ok',
                       _out='Hợp đồng quá hạn mà không ai ký — Hoa hoang mang, chị Huyền phải chữa cháy.'),
                  dict(id='obey', label='Soạn thông báo không gia hạn, ghi lý do “cơ cấu lại”', requires=[], _q='bad', _sev=3,
                       _out='Hoa khiếu nại kèm bằng chứng; công ty bị phạt và mang tiếng phân biệt đối xử.')]),
    dict(id='harass', npc=0, title='Lễ tân bị nhắn tin khiếm nhã',
         opening='Nhi (lễ tân) đưa điện thoại, mắt đỏ hoe: “Anh trưởng nhóm kinh doanh tối nào cũng nhắn mấy câu này… em sợ lắm.”',
         facts=[dict(id='proof', title='Ảnh chụp tin nhắn', text='Năm tối liền, nội dung bình phẩm ngoại hình, rủ đi riêng dù Nhi đã từ chối.'),
                dict(id='code', title='Quy chế ứng xử', text='Quấy rối là vi phạm nặng; người tố cáo được giữ kín danh tính và không bị trù dập.'),
                dict(id='star', title='Người bị tố', text='Trưởng nhóm có doanh số cao nhất công ty, được anh Quân quý.')],
         options=[dict(id='file', label='Ghi nhận bằng văn bản, giữ kín, tạm đổi lịch để Nhi không làm việc trực tiếp với người kia, báo chị Huyền mở quy trình xử lý',
                       requires=['proof', 'code'], _q='good', _out='Nhi được bảo vệ, vụ việc được xử lý đúng quy chế; người kia bị kỷ luật dù doanh số cao.'),
                  dict(id='quiet', label='Nhắc khéo trưởng nhóm, không ghi lại gì', requires=['proof'], _q='ok',
                       _out='Tin nhắn dừng vài hôm rồi lại tiếp; không có hồ sơ nên khó xử lý.'),
                  dict(id='joke', label='Bảo Nhi: “Anh ấy đùa thôi, đừng làm to chuyện”', requires=[], _q='bad', _sev=3,
                       _out='Nhi nghỉ việc, đăng chuyện lên mạng. Công ty mất người và mất uy tín.')]),
    dict(id='quit', npc=5, title='Nghỉ việc mà chưa được trả lương',
         opening='Anh Dũng cầm đơn nghỉ việc: “Tôi nghỉ từ cuối tuần. Kế toán bảo cuối tháng sau mới trả nốt lương, giữ sổ bảo hiểm luôn. Vậy có đúng không cô?”',
         facts=[dict(id='rule', title='Quy định thanh toán khi nghỉ', text='Thanh toán đủ trong 14 ngày làm việc; chốt và trả sổ BHXH đúng hạn, không được giữ.'),
                dict(id='hand', title='Biên bản bàn giao', text='Dũng đã bàn giao đủ máy móc, dụng cụ, có chữ ký Chú Lâm.'),
                dict(id='acct', title='Hỏi cô Hằng', text='Cô Hằng: “Cuối tháng làm một thể cho tiện, đợi thêm chút có sao.”')],
         options=[dict(id='plan', label='Lập lịch thanh toán trong 14 ngày, nhờ cô Hằng chốt lương, báo Dũng ngày nhận tiền và sổ BHXH',
                       requires=['rule', 'hand'], _q='good', _out='Dũng nhận đủ lương và sổ đúng hạn, ra về vẫn giới thiệu bạn bè vào làm.'),
                  dict(id='wait', label='Hẹn Dũng cuối tháng sau như cô Hằng nói', requires=['acct'], _q='ok',
                       _out='Chậm hơn quy định; Dũng phải chờ, ấm ức kể với cả tổ.'),
                  dict(id='hold', label='Giữ sổ BHXH đến khi Dũng “bàn giao thêm”', requires=[], _q='bad', _sev=3,
                       _out='Giữ sổ sai quy định: Dũng gửi đơn lên phòng lao động, công ty bị nhắc nhở.')]),
    dict(id='fakedegree', npc=4, title='Bằng cấp không xác minh được',
         opening='Cô Hằng thì thầm: “Trường gửi thư trả lời: không có ai tên Toàn tốt nghiệp năm đó. Nó vào làm kế toán kho hai tháng rồi đấy.”',
         facts=[dict(id='letter', title='Thư trả lời của trường', text='Không có sinh viên tên này trong danh sách tốt nghiệp năm ghi trên bằng.'),
                dict(id='contract', title='Điều khoản hợp đồng', text='Cung cấp thông tin sai khi tuyển dụng là căn cứ xem xét kỷ luật, sau khi nghe người lao động trình bày.'),
                dict(id='work', title='Kết quả làm việc', text='Toàn làm cẩn thận, chưa sai sót gì; được tổ kho khen.')],
         options=[dict(id='meet', label='Gặp riêng Toàn, đưa thư của trường, cho cậu trình bày rồi báo chị Huyền xử lý theo nội quy',
                       requires=['letter', 'contract'], _q='good', _out='Toàn thừa nhận mua bằng; công ty xử lý đúng quy trình, giữ kín chuyện riêng.'),
                  dict(id='ignore', label='Bỏ qua vì cậu ấy làm tốt', requires=['work'], _q='ok',
                       _out='Chuyện lọt ra ngoài; mọi người hỏi sao phòng nhân sự biết mà làm ngơ.'),
                  dict(id='shame', label='Đăng thư của trường vào nhóm chat công ty cho mọi người biết', requires=[], _q='bad', _sev=3,
                       _out='Bêu riếu công khai: Toàn bị xúc phạm, công ty bị kiện vì làm lộ thông tin cá nhân.')]),
]


def g_case(rng, ctx: dict) -> dict:
    return ow.case_work(rng, CASES)


# ================================================================ the office around the dossiers
MODS = [
    dict(id='normal', min_day=1, weight=3, emoji='☀️', name='Ngày bình thường', text='Hồ sơ đều tay, chị Huyền ngồi bàn bên cạnh.'),
    dict(id='hiring', min_day=2, weight=2, emoji='📨', name='Mùa tuyển dụng', text='Tin tuyển dụng vừa đăng: hồ sơ nào cũng dày hơn thường lệ.'),
    dict(id='boss', min_day=2, weight=2, emoji='🔄', name='Anh Quân đổi ý liên tục', text='Giám đốc vừa đi họp về, kế hoạch nào cũng có thể đổi giữa chừng.'),
    dict(id='labor', min_day=2, weight=2, emoji='🗂️', name='Thanh tra lao động ghé', text='Cuối ngày cô Kim soát hồ sơ: sạch thì được khen, sai thì bị phạt.'),
    dict(id='payday', emoji='📆', name='Chốt công cuối tháng', forced_only=True,
         text='Cả công ty chờ chốt công để làm lương: hạn gấp hơn. Tăng ca hôm nay được trả 18 xu.'),
]


def rules(day: int) -> list:
    return [dict(id='hours', emoji='🕗', title='Giờ làm', text='Vào 08:00 (trễ tới 08:05 vẫn đủ công), ra 17:00. Nghỉ có phép phải có đơn đã duyệt.'),
            dict(id='hire', emoji='⚖️', title='Tuyển dụng công bằng', text='Chỉ xét yêu cầu công việc. Người quen giới thiệu vẫn qua phỏng vấn.'),
            dict(id='contract', emoji='📝', title='Hợp đồng', text='Thử việc tối đa 60 ngày, lương thử việc ít nhất 85%. Hai bên ký đủ mới lưu.'),
            dict(id='privacy', emoji='🔒', title='Bảo mật', text='Lương, hồ sơ, chuyện riêng của từng người: chỉ người phụ trách được xem.'),
            dict(id='rooms', emoji='🚪', title='Xếp lịch', text='Không ai ở hai nơi cùng lúc; phòng đủ chỗ, đủ thiết bị; tránh giờ người ta bận.')]


DESK = [
    dict(id='nephew_walkin', title='Cháu giám đốc vào thẳng', emoji='🧑‍💼', npc=1, min_day=2, tone='tense', at='between', weight=3, mods=None,
         text='Anh Quân dẫn một cậu thanh niên vào: “Cháu anh. Mai cho đi làm luôn nhé, khỏi phỏng vấn lằng nhằng.”',
         options=[dict(id='process', label='Nhận hồ sơ, xếp lịch phỏng vấn như mọi người', hint='Anh Quân hơi phật ý', effects=dict(trust=-1, xp=6), good=True,
                       outcome='Cậu cháu phỏng vấn đàng hoàng và đậu thật. Cả phòng thấy công bằng.'),
                  dict(id='yes', label='“Dạ vâng ạ”, cho đi làm luôn', hint='', effects=dict(trust=2, review=[2, 'Phòng nhân sự tuyển người không cần phỏng vấn, miễn là cháu sếp.']),
                       good=False, outcome='Tuần sau cậu ấy bỏ ngang; hai bạn ứng viên đủ chuẩn đã nhận việc chỗ khác.'),
                  dict(id='refuse', label='Từ chối thẳng trước mặt mọi người', hint='', effects=dict(trust=-3), good=None,
                       outcome='Đúng nguyên tắc nhưng Anh Quân mất mặt, cả buổi chiều không nói câu nào.')],
         default='yes'),
    dict(id='fruit_basket', title='Giỏ trái cây của ứng viên', emoji='🧺', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Một ứng viên vừa phỏng vấn sáng nay gửi giỏ trái cây kèm thiệp: “Mong chị nhớ đến em.”',
         options=[dict(id='return', label='Gọi cảm ơn, nhờ xe ôm gửi trả lại lịch sự', hint='Tốn 5 xu ship', effects=dict(money=-5, xp=5), good=True,
                       outcome='Ứng viên hiểu chuyện, còn nhắn xin lỗi vì làm bạn khó xử.'),
                  dict(id='share', label='Bày ra mời cả phòng ăn', hint='', effects=dict(review=[3, 'Nghe nói ở đây gửi quà là dễ đậu?']), good=False,
                       outcome='Ai cũng vui miệng, rồi có người hỏi: “Bạn này đậu chưa?”'),
                  dict(id='leave', label='Để góc phòng, tính sau', hint='', effects={}, good=None, outcome='Ba hôm sau giỏ trái cây bắt đầu có ruồi.')],
         default='leave'),
    dict(id='zalo_quit', title='Nghỉ việc qua tin nhắn', emoji='📱', npc=2, min_day=2, tone='gentle', at='open', weight=2, mods=None,
         text='07:02 sáng, một bạn bán hàng nhắn: “Em nghỉ nha chị, từ hôm nay luôn.” Kèm sticker vẫy tay.',
         options=[dict(id='call', label='Gọi lại hỏi lý do, hướng dẫn làm đơn và bàn giao', hint='Mất 15 phút', effects=dict(time=15, xp=5), good=True,
                       outcome='Bạn ấy đang bị nợ lương thưởng nên giận. Gỡ xong, bạn ấy ở lại thêm hai tuần bàn giao.'),
                  dict(id='ok', label='Thả tim, ghi “nghỉ việc”', hint='', effects=dict(trust=-1), good=False,
                       outcome='Không ai bàn giao danh sách khách; Linh phải gọi lại từng người.'),
                  dict(id='angry', label='Trả lời gắt: “Thế thì khỏi nhận lương”', hint='', effects=dict(trust=-2, review=[1, 'Nghỉ việc thì bị dọa không trả lương.']),
                       good=False, outcome='Ảnh chụp tin nhắn bị đăng lên nhóm tìm việc của khu.')],
         default='ok'),
    dict(id='fridge', title='Tủ lạnh chung bốc mùi', emoji='🧊', npc=4, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Cô Hằng bịt mũi: “Hộp cơm ai để từ tuần trước? Mùi lên tận phòng kế toán rồi!” Ai cũng bảo không phải của mình.',
         options=[dict(id='rule', label='Dán thông báo: chiều thứ Sáu dọn tủ, hộp không ghi tên sẽ bỏ', hint='', effects=dict(xp=4, trust=1), good=True,
                       outcome='Thứ Sáu tủ sạch bong. Cô Hằng gật đầu hài lòng.'),
                  dict(id='self', label='Tự đeo găng dọn hết', hint='Mất 20 phút', effects=dict(time=20), good=None,
                       outcome='Tủ sạch, nhưng tuần sau lại y như cũ.'),
                  dict(id='ignore', label='Kệ, không phải việc của mình', hint='', effects=dict(review=[2, 'Hành chính để tủ lạnh chung hôi rình cả tuần.']), good=False,
                       outcome='Mùi lan ra cả hành lang lúc khách đến.')],
         default='ignore'),
    dict(id='aircon', title='Chiến tranh điều hòa', emoji='🥶', npc=3, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='Phòng kinh doanh để 18 độ, phòng kế toán đòi 26 độ. Chung một cái máy. Hai bên cùng gọi cho bạn.',
         options=[dict(id='mid', label='Chốt 25 độ theo quy định tiết kiệm điện, xếp chỗ ngồi gần cửa gió cho người hay nóng', hint='', effects=dict(xp=5), good=True,
                       outcome='Không ai hoàn toàn vừa ý nhưng không ai cãi nữa; hóa đơn điện giảm hẳn.'),
                  dict(id='sales', label='Theo phòng kinh doanh cho nhanh', hint='', effects=dict(review=[2, 'Kế toán ngồi run cầm cập cả buổi.']), good=False,
                       outcome='Cô Hằng mặc áo khoác ngồi làm, mặt lạnh hơn máy lạnh.'),
                  dict(id='remote', label='Giấu luôn cái điều khiển', hint='', effects=dict(trust=-1), good=None, outcome='Hai phòng chuyển sang giận… bạn.')],
         default='sales'),
    dict(id='proxy_ask', title='Nhờ quẹt thẻ hộ', emoji='💳', npc=2, min_day=2, tone='tense', at='open', weight=3, mods=None,
         text='Linh nhắn: “Chị ơi em kẹt xe, chị quẹt thẻ hộ em cái, thẻ em để ngăn kéo đó. Em mua trà sữa đền!”',
         options=[dict(id='no', label='Từ chối, nhắc Linh làm giải trình đi muộn', hint='', effects=dict(xp=5, trust=1), good=True,
                       outcome='Linh hơi dỗi, nhưng giải trình xong chị Huyền chỉ nhắc nhẹ.'),
                  dict(id='yes', label='Quẹt hộ một lần thôi', hint='', effects=dict(trust=-3), good=False,
                       outcome='Camera cổng ghi lại hết. Cả hai bị lập biên bản chấm hộ.'),
                  dict(id='ignore', label='Không trả lời', hint='', effects={}, good=None, outcome='Linh đến muộn, quên luôn chuyện xin phép.')],
         default='ignore'),
    dict(id='uniform', title='Đồng phục phải có ngay', emoji='👕', npc=3, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Chú Lâm: “Mai đoàn khách Nhật thăm xưởng! Ba mươi bộ đồng phục mới, chiều nay phải có!”',
         options=[dict(id='stock', label='Kiểm kho đồng phục dự phòng, đặt thêm phần thiếu giao sáng mai', hint='Mất 20 phút', effects=dict(time=20, xp=5), good=True,
                       outcome='Kho còn 22 bộ, xưởng in giao nốt 8 bộ lúc 7 giờ sáng. Kịp đón khách.'),
                  dict(id='rush', label='Đặt gấp 30 bộ, trả phí giao hỏa tốc', hint='−25 xu', effects=dict(money=-25), good=None,
                       outcome='Kịp, nhưng kho dự phòng vẫn còn nguyên 22 bộ.'),
                  dict(id='no', label='“Không kịp đâu chú”', hint='', effects=dict(review=[2, 'Có mỗi bộ đồng phục cũng không lo nổi.']), good=False,
                       outcome='Thợ mặc áo cũ bạc màu đón khách. Chú Lâm giận cả tuần.')],
         default='no'),
    dict(id='anon_letter', title='Thư góp ý nặc danh', emoji='✉️', npc=1, min_day=3, tone='tense', at='between', weight=2, mods=None,
         text='Hộp thư góp ý có lá thư nặc danh chê Anh Quân “quyết xong lại đổi”. Anh Quân bảo: “Tìm xem ai viết cho anh.”',
         options=[dict(id='protect', label='Giữ nặc danh; tóm tắt góp ý gửi anh Quân kèm đề xuất họp giao ban rõ kế hoạch', hint='', effects=dict(trust=-1, xp=6), good=True,
                       outcome='Anh Quân càu nhàu nhưng tuần sau họp giao ban chốt kế hoạch hẳn hoi.'),
                  dict(id='hunt', label='So nét chữ đi tìm người viết', hint='', effects=dict(trust=1, review=[1, 'Góp ý nặc danh mà phòng nhân sự đi dò nét chữ.']), good=False,
                       outcome='Cả công ty biết chuyện; từ đó hộp góp ý trống trơn.'),
                  dict(id='bin', label='Vứt thư đi cho yên chuyện', hint='', effects={}, good=None, outcome='Không ai biết góp ý có được đọc không.')],
         default='bin'),
    dict(id='printer40', title='Máy in kẹt giữa 40 bản hợp đồng', emoji='🖨️', npc=0, min_day=2, tone='gentle', at='between', weight=2, mods=None,
         text='In tới bản thứ 17 thì máy kẹt giấy, đèn đỏ nhấp nháy. 2 giờ nữa ký hợp đồng hàng loạt.',
         options=[dict(id='it', label='Gọi IT, trong lúc chờ in nốt ở máy tầng 2', hint='Mất 15 phút', effects=dict(time=15), good=True,
                       outcome='Kịp giờ ký; IT gỡ được mẩu giấy kẹt sâu trong máy.'),
                  dict(id='pull', label='Tự giật mạnh tờ giấy ra', hint='', effects=dict(money=-10), good=False,
                       outcome='Rách trục cuốn giấy, sửa mất 10 xu.'),
                  dict(id='wait', label='Ngồi chờ máy “tự hết”', hint='', effects=dict(time=30), good=None, outcome='Máy không tự hết.')],
         default='wait'),
    dict(id='birthday', title='Sinh nhật bất ngờ trong 30 phút', emoji='🎂', npc=1, min_day=3, tone='gentle', at='between', weight=2, mods=None,
         text='Anh Quân: “Hôm nay sinh nhật cô Hằng! Em lo cái bánh, 3 giờ cả phòng hát chúc mừng nhé.” Bây giờ là 2 giờ 30.',
         options=[dict(id='simple', label='Đặt bánh nhỏ tiệm gần, gom chữ ký cả phòng vào tấm thiệp', hint='−15 xu, mất 15 phút', effects=dict(money=-15, time=15, trust=2), good=True,
                       outcome='Cô Hằng bất ngờ đến rưng rưng; lần đầu thấy cô cười to giữa giờ làm.'),
                  dict(id='big', label='Đặt bánh ba tầng cho hoành tráng', hint='−40 xu', effects=dict(money=-40), good=None,
                       outcome='Bánh tới lúc 4 giờ rưỡi, cô Hằng đã về.'),
                  dict(id='forget', label='Hứa rồi quên mất', hint='', effects=dict(trust=-2), good=False, outcome='3 giờ cả phòng đứng nhìn nhau.')],
         default='forget'),
]

SITUATIONS = [
    dict(id='HC-S01', title='Ứng viên giỏi nhưng đang mang thai', npc=1, tone='tense', min_day=2,
         opening='Anh Quân lật hồ sơ: “Bạn này giỏi đấy, nhưng ghi chú là đang mang thai bốn tháng. Thôi loại đi em, tuyển vào lại nghỉ sinh.”',
         swap='Bạn là giám đốc công ty nhỏ, lo mùa tựu trường đơn hàng dồn dập mà thiếu người.',
         facts=[dict(id='law', title='Quy định tuyển dụng', source='Sổ tay nhân sự', text='Không được từ chối tuyển dụng vì lý do mang thai, giới tính hay hôn nhân.'),
                dict(id='cv', title='Hồ sơ ứng viên', source='CV', text='Năm năm thiết kế túi xách, từng làm mẫu cho hai thương hiệu lớn.'),
                dict(id='plan', title='Kế hoạch mùa tựu trường', source='Phòng kinh doanh', text='Cao điểm là tháng 7–8; ứng viên dự sinh tháng 12.')],
         options=[dict(id='fair', label='Mời phỏng vấn như mọi người, trình anh Quân lịch cao điểm và kế hoạch người hỗ trợ khi chị nghỉ sinh',
                       requires=['law', 'plan'], quality='good', stars=5,
                       review='Được phỏng vấn công bằng, em vào làm kịp mùa cao điểm. Cảm ơn phòng nhân sự 🌷',
                       outcome='Chị ấy vào làm, mẫu balo mới kịp mùa tựu trường; nghỉ sinh có người hỗ trợ sắp sẵn.',
                       perspectives=[dict(who='Ứng viên', emoji='🤰', text='Mình chỉ mong được xét bằng năng lực.'),
                                     dict(who='Anh Quân', emoji='🧑‍💼', text='Hóa ra lịch cao điểm vẫn ổn, anh lo xa quá.')]),
                  dict(id='reject', label='Loại hồ sơ theo ý giám đốc', quality='bad', stars=1,
                       review='Bị loại chỉ vì đang có em bé. Buồn ghê.',
                       outcome='Ứng viên biết lý do thật, đăng lên mạng; công ty bị hỏi thăm vì phân biệt đối xử.',
                       perspectives=[dict(who='Ứng viên', emoji='😔', text='Người ta không nói thẳng, nhưng mình biết.'),
                                     dict(who='Chị Huyền', emoji='📋', text='Đây là chuyện phòng nhân sự phải can ngăn.')]),
                  dict(id='later', label='Hẹn ứng viên “sau sinh quay lại”', quality='ok', stars=3,
                       review='Hẹn sau sinh… nghe lịch sự mà vẫn là loại mình.',
                       outcome='Ứng viên nhận việc chỗ khác; công ty thiếu người thiết kế cả mùa.',
                       perspectives=[dict(who='Linh', emoji='📦', text='Mẫu mới chậm, khách hỏi mãi.')])],
         lesson='Tuyển dụng xét năng lực; lo lắng của sếp thì giải bằng kế hoạch, không bằng loại người.'),
    dict(id='HC-S02', title='Thợ lâu năm sợ mất việc vì máy mới', npc=5, tone='gentle', min_day=3,
         opening='Anh Dũng đứng ngập ngừng: “Nghe nói xưởng mua máy may tự động. Thế… mấy người già như tôi có bị cho nghỉ không cô?”',
         swap='Bạn là thợ may 15 năm, tay nghề giỏi nhưng không rành máy tính.',
         facts=[dict(id='plan', title='Kế hoạch đầu tư', source='Anh Quân', text='Máy mới làm đường may thẳng; mẫu khó vẫn cần thợ tay nghề cao.'),
                dict(id='train', title='Chương trình đào tạo', source='Chị Huyền', text='Công ty có ngân sách cho 5 thợ học vận hành máy, ưu tiên người lâu năm.'),
                dict(id='rumor', title='Tin đồn trong xưởng', source='Chú Lâm', text='Có người bảo mua máy để cắt giảm một nửa tổ.')],
         options=[dict(id='train', label='Nói rõ kế hoạch, mời anh Dũng đăng ký lớp vận hành máy đầu tiên',
                       requires=['plan', 'train'], quality='good', stars=5,
                       review='Tưởng mất việc, ai dè được đi học máy mới. Tôi yên tâm rồi.',
                       outcome='Dũng thành người đứng máy giỏi nhất, còn kèm thợ trẻ.',
                       perspectives=[dict(who='Anh Dũng', emoji='🧵', text='Già rồi vẫn học được, mà còn được ưu tiên.'),
                                     dict(who='Chú Lâm', emoji='🏭', text='Tổ yên ổn, không ai bỏ đi.')]),
                  dict(id='vague', label='“Chưa biết đâu anh, cứ làm đi”', quality='ok', stars=3,
                       review='Hỏi mà không ai nói rõ, lo vẫn hoàn lo.',
                       outcome='Hai thợ giỏi xin nghỉ trước vì tin đồn.',
                       perspectives=[dict(who='Anh Dũng', emoji='😟', text='Không biết thì sợ.')]),
                  dict(id='rumor', label='Xác nhận tin đồn cho anh chuẩn bị tinh thần', quality='bad', stars=1,
                       review='Phòng nhân sự cũng bảo sẽ cắt người. Thôi tôi đi tìm chỗ khác.',
                       outcome='Tin sai lan khắp xưởng; năng suất tụt hẳn cả tháng.',
                       perspectives=[dict(who='Anh Quân', emoji='🧑‍💼', text='Ai nói với thợ là cắt người thế?')])],
         lesson='Tin đồn chỉ dập được bằng thông tin rõ và một con đường cụ thể cho người đang lo.'),
    dict(id='HC-S03', title='Bị mắng trước cả phòng', npc=2, tone='gentle', min_day=2,
         opening='Linh chạy vào phòng nhân sự, mắt đỏ hoe: “Anh Quân quát em trước cả phòng vì báo giá sai. Em muốn nghỉ luôn.”',
         swap='Bạn là nhân viên trẻ, lỗi thì có nhưng bị mắng giữa mọi người thấy nhục.',
         facts=[dict(id='error', title='Báo giá bị sai', source='Phòng kinh doanh', text='Linh gõ nhầm đơn giá, khách phát hiện trước khi ký.'),
                dict(id='code', title='Quy chế ứng xử', source='Sổ tay nhân sự', text='Góp ý công việc làm riêng, tôn trọng; không xúc phạm trước đông người.'),
                dict(id='record', title='Thành tích của Linh', source='Báo cáo doanh số', text='Ba tháng liền vượt chỉ tiêu.')],
         options=[dict(id='both', label='Lắng nghe Linh, cùng lập bảng tự kiểm báo giá; gặp riêng anh Quân góp ý cách nhắc nhở theo quy chế',
                       requires=['error', 'code'], quality='good', stars=5,
                       review='Em vẫn sai thật, nhưng giờ em có checklist, sếp cũng nhẹ giọng hơn rồi 😅',
                       outcome='Linh ở lại, báo giá không sai nữa; anh Quân bắt đầu góp ý riêng.',
                       perspectives=[dict(who='Linh', emoji='📦', text='Được nghe, được chỉ cách sửa.'),
                                     dict(who='Anh Quân', emoji='🧑‍💼', text='Anh nóng quá. Lần sau anh nói riêng.')]),
                  dict(id='pat', label='An ủi Linh rồi thôi', quality='ok', stars=3,
                       review='Được an ủi nhưng mai lại thế thì sao.',
                       outcome='Linh đỡ buồn; tháng sau lại bị quát lần nữa.',
                       perspectives=[dict(who='Linh', emoji='😕', text='Không ai sửa gì cả.')]),
                  dict(id='side', label='Bảo Linh: “Em sai thì bị mắng là đúng rồi”', quality='bad', stars=1,
                       review='Đến nhân sự cũng không bênh. Em nộp đơn rồi.',
                       outcome='Linh nghỉ việc, mang theo ba khách hàng lớn.',
                       perspectives=[dict(who='Chị Huyền', emoji='📋', text='Mình mất một người giỏi vì một câu nói.')])],
         lesson='Lỗi công việc thì sửa bằng cách làm; cách góp ý thì cũng cần được sửa.'),
]

CARE = dict(
    id=ID, prefix=P, boss=BOSS,
    ranks=('Thử việc', 'Chuyên viên nhân sự chính thức', 'Phụ trách tuyển dụng', 'Được đề cử phó phòng nhân sự'),
    lines=('Ba ngày hồ sơ gọn gàng, không sót chữ ký nào. Chị ký chính thức cho em nhé.',
           'Từ nay em phụ trách tuyển dụng. Ứng viên nào cũng phải được đối xử công bằng như em vẫn làm.',
           'Chị đã đề cử em làm phó phòng. Có em, chị đi phép cũng yên tâm.'),
    mates=[
        dict(id='van', name='Vân', role='Chuyên viên tuyển dụng mới', npc=None, emoji='🐣',
             asks=[('Em gọi điện mời phỏng vấn mà run quá, chị nghe em tập một lượt được không?', 20),
                   ('Đơn nghỉ phép nửa ngày thì chấm công thế nào hả chị?', 15)],
             thanks='Vân ghi vội vào sổ: “Hiểu rồi ạ! Cảm ơn chị.”', no='Vân gật đầu: “Dạ, em hỏi chị Huyền vậy.”',
             cover='Vân soát giúp một lượt —'),
        dict(id='lam', name='Chú Lâm', role='Tổ trưởng xưởng may balo', npc=3, emoji='🧵',
             asks=[('Thợ mới hỏi mãi về bảo hiểm, cháu giải thích giúp chú mấy câu?', 20),
                   ('Bảng phân ca tổ chú rối quá, cháu xếp lại giùm chú nhé?', 25)],
             thanks='Chú Lâm cười khà: “Cần thợ thử tay nghề lúc nào cứ gọi chú.”', no='Chú Lâm: “Ừ, để chú tự mò.”',
             cover='Chú Lâm mang bảng công ký sẵn lên tận nơi —'),
        dict(id='nhi', name='Nhi', role='Lễ tân', npc=None, emoji='🛎️',
             asks=[('Có ứng viên đến sớm 1 tiếng, chị ra tiếp giúp em được không?', 15),
                   ('Sổ khách ra vào em ghi sai mấy dòng, chị chỉ em sửa cho đúng?', 15)],
             thanks='Nhi để lên bàn hộp sữa chua: “Em cảm ơn chị!”', no='Nhi: “Dạ không sao, em tự lo được.”',
             cover='Nhi chuyển giúp hồ sơ giữa các phòng —'),
    ])

FORMS = [dict(id='cv', label='Lọc hồ sơ', min_day=1, bonus=25, build=g_cv),
         dict(id='timesheet', label='Bảng chấm công', min_day=1, bonus=25, build=g_timesheet),
         dict(id='contract', label='Soát hợp đồng', min_day=1, bonus=25, build=g_contract),
         dict(id='interview', label='Lịch phỏng vấn', min_day=2, bonus=30, build=g_interview),
         dict(id='case', label='Chuyện nhân sự', min_day=3, bonus=20, build=g_case)]

JOB = ow.OfficeJob(dict(
    id=ID, prefix=P, boss=BOSS, boss_npc=0, forms=FORMS, mods=MODS, forced={4: 'payday'}, intro={2: 'hiring', 3: 'boss', 4: 'labor'},
    more_mods=('hiring',), busy_mod='boss', helpers=('Chị Huyền',), crunch='payday', audit='labor', auditor='Cô Kim (thanh tra lao động)', care=CARE, desk=DESK,
    rules=rules,
    hints=dict(cv='Đọc yêu cầu vị trí → chạm từng hồ sơ, chọn khay. So CV với dòng tra cứu BHXH; ghi chú bên lề không phải tiêu chí.',
               timesheet='Đối chiếu từng ô với giờ làm và tờ đơn từ trong tuần: chạm ô sai, chọn lý do. Ô đúng thì để nguyên.',
               contract='So từng chỗ trong hợp đồng với thư mời nhận việc, CCCD và quy định: chạm chỗ sai, chọn cách viết đúng.',
               interview='Chọn một buổi phỏng vấn → chạm ô phòng/giờ. Xem bảng quy định: ai bận, phòng nào đã có người đặt.',
               case='Tìm hiểu từng chuyện trước, rồi chọn cách trả lời vừa đúng quy định vừa có lối ra.'),
    staff_area={'recruit': ('cv', 'interview'), 'admin': ('timesheet', 'contract')},
))
JOB.bind(globals())

EMPLOYMENT = dict(
    postings=[
        dict(id='hc-canhdieu', org='Công ty CP Cánh Diều', kind='corp', title='Chuyên viên hành chính – nhân sự',
             salary=(55, 80), probation_days=3, wants=['careful', 'communication', 'patience'],
             perks=['Có trưởng phòng kèm', 'Gặp đủ kiểu người', 'Giờ giấc ổn định'],
             culture='Công ty làm balo, cặp sách 80 người; giám đốc quyết nhanh, đổi ý cũng nhanh.',
             questions=['hc_bias', 'hc_privacy', 'conflict'], reference=True),
        dict(id='hc-agency', org='Văn phòng tuyển dụng Cầu Nối', kind='firm', title='Trợ lý tuyển dụng',
             salary=(50, 70), probation_days=2, wants=['communication', 'learning'],
             perks=['Nhận việc nhanh', 'Gọi điện nhiều', 'Thưởng theo hồ sơ'],
             culture='Văn phòng nhỏ tuyển người cho xưởng và cửa hàng quanh khu.',
             questions=['hc_bias', 'mistake'], reference=False),
    ],
    questions={
        'hc_bias': dict(text='Sếp ghi bên lề CV: “Mới cưới, loại.” Ứng viên đủ mọi yêu cầu. Bạn làm gì?', options=[
            dict(id='fair', label='Vẫn mời phỏng vấn, nói riêng với sếp quy định không phân biệt đối xử', score=3, note='Công bằng mà vẫn khéo.'),
            dict(id='obey', label='Loại theo ý sếp', score=0, note='Phân biệt đối xử là lỗi rất nặng của người làm nhân sự.'),
            dict(id='hide', label='Lặng lẽ mời mà không nói gì với sếp', score=1, note='Đúng hướng nhưng né trao đổi.')]),
        'hc_privacy': dict(text='Đồng nghiệp hỏi lương của người khác. Bạn trả lời sao?', options=[
            dict(id='scale', label='Không nói; chỉ thang lương công khai và cách đề nghị xét lương', score=3, note='Bảo mật mà vẫn giúp được.'),
            dict(id='tell', label='Nói nhỏ thôi, chỗ thân quen', score=0, note='Lộ lương là mất lòng tin cả công ty.'),
            dict(id='no', label='“Bí mật” rồi thôi', score=1, note='Đúng nhưng cộc.')]),
    },
)

SPEC = dict(
    id=ID, prefix=P, category='office',
    meta=dict(short='Hành chính – Nhân sự', place='Công ty CP Cánh Diều', tagline='Công bằng từ tờ CV đến tờ hợp đồng.', icon='people',
              color='#7a5c9e', light='#efe8f7', weather='Nắng nhẹ, quạt trần quay đều', work='Hồ sơ', station='Bàn nhân sự',
              greeting='Hồ sơ ứng tuyển, bảng chấm công và hợp đồng hôm nay đã xếp trên bàn. Soát kỹ, công bằng với từng người nhé.',
              caption='Mỗi tờ giấy là một con người', map_label='22 · CÁNH DIỀU · NHÂN SỰ'),
    people=PEOPLE,
    staff=[('Vân', 'recruit', 'Mới vào, gọi điện còn run nhưng rất chịu khó.', 70, 92),
           ('Nhi', 'admin', 'Lễ tân kiêm văn thư, nhớ mặt từng khách.', 74, 90),
           ('Chị Huyền', 'admin', 'Thuộc lòng nội quy, soát một lần là ra lỗi.', 90, 88)],
    roles={'recruit': 'Chuyên viên tuyển dụng', 'admin': 'Hành chính – văn thư'},
    tip=0,
    physical=(),
    free_actions=(),
    no_tick=(P + 'put', P + 'mark', P + 'place', P + 'read', P + 'hint', P + 'desk', P + 'overtime', P + 'help', P + 'cover', P + 'break'),
    employment=EMPLOYMENT,
    activity=('🗂️', 'Bàn nhân sự ngăn nắp', [('CV ứng tuyển', 'Tuyển dụng'), ('Bảng chấm công', 'Tiền lương'),
                                            ('Hợp đồng lao động', 'Hồ sơ'), ('Lịch phỏng vấn', 'Tuyển dụng')],
              ['Lọc hồ sơ', 'Xếp lịch phỏng vấn', 'Soát hợp đồng', 'Chốt công']),
    stories=[('Bạn thợ may đầu tiên', ('Một cô gái quê Nghệ An nộp hồ sơ, CV viết tay, email ngộ nghĩnh.',
                                       'Bạn mời cô thử tay nghề dù Linh bảo “email trẻ con quá”.',
                                       'Ba tháng sau, cô may mẫu balo bán chạy nhất mùa tựu trường.')),
             ('Tờ đơn nghỉ phép', ('Anh Dũng nghỉ không phép ba hôm, chú Lâm đòi đuổi.',
                                   'Bạn hỏi ra chuyện con anh nằm viện, chỉ anh làm đơn nghỉ phép năm.',
                                   'Anh Dũng quay lại làm, tặng cả phòng nhân sự chùm chôm chôm nhà trồng.')),
             ('Lịch phỏng vấn kín mít', ('Mùa tuyển dụng, một ngày 9 buổi phỏng vấn, 3 phòng họp.',
                                         'Bạn xếp lại từng ô, tránh giờ giám đốc đi ngân hàng.',
                                         'Không ứng viên nào phải chờ quá 10 phút.'))],
    review_asides=['Hồ sơ rõ ràng, hỏi là có câu trả lời.', 'Được đối xử công bằng.', 'Chuyện riêng được giữ kín.', 'Lịch hẹn đúng giờ.'],
    situations=SITUATIONS,
    guide='Mỗi hồ sơ là một việc thật: lọc CV vào khay, soát bảng chấm công từng ô, soát hợp đồng, xếp lịch phỏng vấn, trao đổi chuyện khó. Đọc giấy tờ bên cạnh, rồi nộp trước giờ hạn. Thỉnh thoảng sếp đổi ý giữa chừng — đọc kỹ tin báo rồi sửa lại. Lương ngày trả khi khép ca.',
)
