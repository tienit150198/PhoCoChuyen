"""Gợi ý cho Học kế toán: hints only, the player does the work.

Two hints ride with every unsolved practice question and every opened company voucher
(`help`): 1) where to look in the source document, 2) which account groups apply and how
they behave (tăng ghi Nợ/Có). They never name an account code, a side or an amount of the
answer. A wrong answer gets a third, targeted hint built from what the player entered
(which line, which side, or that the amount does not match). Nothing here is shown during
a graded exam.
"""
from __future__ import annotations

GROUPS = {
    '1': 'Loại 1 – tài sản ngắn hạn', '2': 'Loại 2 – tài sản dài hạn', '3': 'Loại 3 – nợ phải trả',
    '4': 'Loại 4 – vốn chủ sở hữu', '5': 'Loại 5 – doanh thu', '6': 'Loại 6 – chi phí sản xuất, kinh doanh',
    '7': 'Loại 7 – thu nhập khác', '8': 'Loại 8 – chi phí khác và thuế TNDN', '9': 'Loại 9 – xác định kết quả kinh doanh',
}
ASSET = 'tăng ghi Nợ, giảm ghi Có'
CREDIT = 'tăng ghi Có, giảm ghi Nợ'
SPECIAL = {
    '131': 'phải thu: tăng ghi Nợ, giảm ghi Có; theo dõi từng khách, khách trả trước tạo dư Có',
    '331': 'phải trả: tăng ghi Có, giảm ghi Nợ; theo dõi từng người bán, ứng trước tạo dư Nợ',
    '214': 'điều chỉnh giảm tài sản: hao mòn tăng ghi Có, giảm ghi Nợ',
    '229': 'điều chỉnh giảm tài sản: dự phòng tăng ghi Có, hoàn nhập ghi Nợ',
    '419': 'điều chỉnh giảm vốn: mua lại ghi Nợ',
    '412': 'chênh lệch: tăng ghi Có, giảm ghi Nợ; có thể dư hai bên',
    '413': 'chênh lệch: lãi ghi Có, lỗ ghi Nợ; có thể dư hai bên',
    '421': 'lợi nhuận chưa phân phối: lãi ghi Có, lỗ và phân phối ghi Nợ',
    '521': 'giảm trừ doanh thu: phát sinh ghi Nợ, cuối kỳ kết chuyển sang 511',
    '911': 'khóa sổ: chi phí kết chuyển vào bên Nợ, doanh thu vào bên Có; không có số dư',
    '154': 'tập hợp chi phí sản xuất: nhận kết chuyển bên Nợ, giá thành hoàn thành ghi Có',
}


def nature(code: str) -> str:
    """How an account moves (tăng ghi Nợ/Có), from its code."""
    for n in (4, 3):
        if code[:n] in SPECIAL: return SPECIAL[code[:n]]
    d = code[:1]
    if d in '12': return 'tài sản: ' + ASSET
    if d == '3': return 'nợ phải trả: ' + CREDIT
    if d == '4': return 'vốn chủ sở hữu: ' + CREDIT
    if d in '57': return 'doanh thu, thu nhập: phát sinh ghi Có, cuối kỳ kết chuyển sang 911'
    if code[:2] == '62': return 'chi phí sản xuất: phát sinh ghi Nợ, cuối kỳ kết chuyển sang 154'
    if d in '68': return 'chi phí: phát sinh ghi Nợ, cuối kỳ kết chuyển sang 911'
    return 'xem hướng dẫn tài khoản trong Phụ lục II'


def glossary() -> list:
    """Tra cứu TT99: every account the course and the practice company use."""
    from .accounting_content import ACCOUNT_CHART
    from .accounting_company import CHART
    names = dict(ACCOUNT_CHART)
    for code, name in CHART.items(): names.setdefault(code, name)
    return [dict(code=c, name=names[c], group=GROUPS.get(c[:1], ''), nature=nature(c)) for c in sorted(names)]


def _rows(key) -> list:
    return [(x['debit'], x['credit'], x['amount']) if isinstance(x, dict) else tuple(x) for x in key]


GROUP_NATURE = {'1': ASSET, '2': ASSET, '3': CREDIT, '4': CREDIT, '5': 'phát sinh ghi Có', '7': 'phát sinh ghi Có',
                '6': 'phát sinh ghi Nợ', '8': 'phát sinh ghi Nợ', '9': 'chỉ dùng khi khóa sổ'}


def _groups(rows) -> str:
    """'Loại 1 – tài sản ngắn hạn (tăng ghi Nợ, giảm ghi Có); …' for the groups the answer uses (no codes)."""
    codes = {x for d, c, _ in rows for x in (d, c)}
    text = '; '.join(f'{GROUPS[g]} ({GROUP_NATURE[g]})' for g in sorted({x[:1] for x in codes}) if g in GROUPS)
    if any(x[:3] in SPECIAL or x[:4] in SPECIAL for x in codes):
        text += '. Có tài khoản ghi ngược chiều nhóm hoặc theo dõi theo từng đối tượng: xem cột “tính chất” trong Tra cứu TT99'
    return text


def _cues(text: str) -> list:
    """What to look for in a voucher, from its own words (no account names)."""
    t = text.lower()
    out = []
    no_tax = any(x in t for x in ('không có thuế', 'không có gtgt', 'chưa có nghĩa vụ thuế'))
    if ('chưa thuế' in t or 'gtgt' in t or 'thuế đầu' in t) and not no_tax: out.append('tách giá chưa thuế khỏi tiền thuế')
    if 'chưa trả' in t or 'chưa thu' in t or 'chưa thanh toán' in t: out.append('tiền đã đi/về chưa hay còn là công nợ')
    elif any(x in t for x in ('báo có', 'báo nợ', 'phiếu chi', 'phiếu thu', 'tiền mặt', 'chuyển khoản', 'ngân hàng', 'đã trả')): out.append('tiền đi qua quỹ hay qua ngân hàng')
    if 'khach_' in t or 'ncc_' in t: out.append('đối tượng công nợ là ai')
    if 'kết chuyển' in t or 'khóa sổ' in t: out.append('số dư nào phải đưa về 0 khi khóa sổ')
    if 'tỷ giá' in t or 'usd' in t: out.append('tỷ giá dùng cho lần ghi này')
    if any(x in t for x in ('12 kỳ', 'ba kỳ', '3 kỳ', 'kỳ hạn', '6 tháng')): out.append('khoản này thuộc riêng kỳ này hay trải ra nhiều kỳ')
    return out or ['nghiệp vụ gì đã xảy ra và số tiền nào là căn cứ ghi sổ']


def lesson_help(q: dict, lesson: dict) -> list:
    """Hints 1–2 of a practice question."""
    first = f'Đọc lại phần “{lesson["example"]["title"]}” của bài “{lesson["title"]}”: cách làm từng bước giống bài này.'
    kind = q['kind']
    if kind == 'entry':
        rows = _rows(q['_key'])
        second = f'Bút toán dùng tài khoản thuộc: {_groups(rows)}. Mở “Tra cứu TT99” để chọn đúng số hiệu.'
    elif kind in ('number', 'fields'):
        second = 'Viết phép tính ra giấy: lấy đúng số trong đề, tách giá chưa thuế, thuế và tổng; kiểm lại phương trình tài sản = nợ + vốn.'
    elif kind == 'order':
        second = 'Kế toán luôn đi: chứng từ → ghi sổ → đối chiếu → khóa sổ → báo cáo. Đặt từng bước vào đúng chặng đó.'
    else:
        goals = lesson.get('objectives') or []
        second = 'Loại trừ phương án trái với nguyên tắc của bài' + (f': {goals[0].lower()}.' if goals else '.')
    return [first, second]


def company_help(task: dict) -> list:
    """Hints 1–2 of the practice company's current step (shown once its voucher is open)."""
    doc = (task.get('docs') or [{}])[0]
    if task['kind'] == 'entry':
        cues = ['số dư nào phải đưa về 0 khi khóa sổ'] if task.get('closing') else _cues(' '.join(doc.get('lines') or []))
        first = f'Chứng từ cần đọc: “{doc.get("title", task["title"])}”. Tìm trong đó: ' + '; '.join(cues) + '.'
        rows = _rows(task['_key'])
        second = f'Bút toán có {len(rows)} dòng Nợ/Có, dùng tài khoản thuộc: {_groups(rows)}.'
        return [first, second]
    if task['kind'] == 'fields':
        return ['Mở tab “Cân đối phát sinh” và “Sổ chi tiết”: mọi số của báo cáo đều lấy từ sổ đã ghi, không ước lượng.',
                'B01: tài sản = nợ phải trả + vốn chủ, công nợ tách dư Nợ/dư Có theo từng đối tượng. B02: lấy phát sinh trước kết chuyển. '
                'B03: chỉ dòng tiền thật qua 111/112, bỏ chuyển tiền nội bộ.']
    return ['Đọc “Hồ sơ chính sách”: đơn vị tiền, cơ sở lập, cách trình bày công nợ và tiền gửi.',
            'Thuyết minh phải khớp đúng chính sách và số trong sổ; loại phương án bù trừ công nợ hoặc bỏ qua bút toán không bằng tiền.']


def wrong(q: dict, answer) -> str:
    """Hint 3: where the entered answer goes wrong, without the right value."""
    kind = q['kind']
    key = q['_key']
    if kind == 'entry':
        want = _rows(key)
        got = [(x.get('debit'), x.get('credit'), x.get('amount')) for x in answer]
        debits, credits = {d for d, _, _ in want}, {c for _, c, _ in want}
        for i, (d, c, a) in enumerate(got, 1):
            if d in credits and c in debits and (d not in debits or c not in credits):
                return f'Dòng {i}: hai bên Nợ/Có đang bị đảo. Tài sản, chi phí tăng ghi Nợ; nợ phải trả, vốn, doanh thu tăng ghi Có.'
            if d not in debits:
                return f'Dòng {i}: bên Nợ chưa đúng. Hỏi lại: tài khoản nào tăng tài sản/chi phí hoặc giảm nợ trong chứng từ này?'
            if c not in credits:
                return f'Dòng {i}: bên Có chưa đúng. Hỏi lại: nguồn tiền hay nghĩa vụ nào đối ứng với bên Nợ?'
        want_d = {}; got_d = {}
        for d, c, a in want: want_d[d] = want_d.get(d, 0) + a
        for d, c, a in got: got_d[d] = got_d.get(d, 0) + a
        if set(want_d) - set(got_d) or len({c for _, c, _ in got}) < len(credits):
            return 'Các dòng đã ghi đúng tài khoản nhưng còn thiếu một dòng: chứng từ có thêm một khoản phải tách riêng (thường là thuế hoặc giá vốn).'
        for i, (d, c, a) in enumerate(got, 1):
            if got_d.get(d) != want_d.get(d):
                return f'Tài khoản đúng, nhưng số tiền ở dòng {i} chưa khớp chứng từ. Đối chiếu lại giá chưa thuế, thuế và tổng.'
        return 'Tài khoản đúng; kiểm lại số tiền từng dòng so với chứng từ.'
    if kind == 'number':
        return 'Kết quả chưa khớp. Viết lại từng bước tính và kiểm đơn vị (đồng, %, kỳ).'
    if kind == 'choice':
        return 'Phương án đã chọn chưa đúng. Đọc lại điều kiện trong đề: phương án đúng phải khớp mọi chi tiết, không chỉ một phần.'
    if kind == 'multi':
        right = set(key)
        picked = set(answer) if isinstance(answer, list) else set()
        parts = []
        if right - picked: parts.append('còn thiếu ít nhất một phương án đúng')
        if picked - right: parts.append('có phương án không nên chọn')
        return 'Bạn ' + ' và '.join(parts or ['chọn chưa đúng']) + '.'
    if kind == 'fields':
        labels = {f['id']: f['label'] for f in q.get('fields', [])}
        off = [labels.get(k, k) for k, v in key.items() if isinstance(answer, dict) and answer.get(k) != v]
        return 'Ô chưa khớp: ' + ', '.join(off) + '. Lấy lại số từ sổ hoặc đề bài.' if off else 'Kiểm lại từng ô.'
    if kind == 'match':
        labels = {x['id']: x['label'] for x in q.get('left', [])}
        off = [labels.get(k, k) for k, v in key.items() if isinstance(answer, dict) and answer.get(k) != v]
        return f'{len(off)} cặp chưa đúng: ' + '; '.join(off) + '.' if off else 'Kiểm lại từng cặp.'
    if kind == 'order':
        from .procedures import orders
        best = 0
        for o in orders(key):
            n = next((i for i, (a, b) in enumerate(zip(answer, o)) if a != b), len(o))
            best = max(best, n)
        return f'Thứ tự đúng tới bước {best}; bước {best + 1} chưa đúng chỗ.' if best else 'Bước đầu tiên chưa đúng: việc gì phải làm trước mọi việc khác?'
    return 'Chưa đúng. Đọc lại đề và thử lại.'
