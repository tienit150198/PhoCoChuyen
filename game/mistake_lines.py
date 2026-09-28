"""What customers actually say about a mistake: at the counter, in the review, in a report.

The career writes the concrete complaint when it records a slip
(consequences.slip(t, code, sev, 'Dặn ít đá mà đưa cả ly đá, uống toàn nước.'));
this file wraps it for the reaction, the review and the app report. Whole
sentences, the same patterns everywhere, so the translation pack can match them.
"""
from __future__ import annotations

REACTION = {
    'accept': ('Thôi được rồi, lần sau để ý giúp nhé.', 'Ừ thôi, lấy vậy. Lần sau nhớ giúp mình.'),
    'grumble': ('Lần sau làm cho đúng nhé.', 'Thôi lấy vậy, nhưng mình không vui đâu.', 'Nói rõ rồi mà vẫn sai.'),
    'discount': ('Sai như vậy thì bớt cho mình một phần tiền.', 'Mình trả bớt, coi như bù cho cái sai này.'),
    'refund': ('Trả lại mình một nửa tiền, sai thế này sao trả đủ được.', 'Mình chỉ trả một nửa thôi.'),
    'walkout': ('Thôi khỏi, mình không trả tiền cho thứ này. Đi chỗ khác.', 'Không lấy nữa. Mình về đây.'),
    'refuse': ('Cái này nguy hiểm đấy, mình không nhận và sẽ phản ánh.', 'Sai chuyện này là không đùa được. Mình không trả tiền.'),
    'remake': ('Làm lại giúp mình cho đúng lời dặn nhé.', 'Không phải thế này, làm lại giúp mình đi.'),
}

REPORT = (
    '📣 Báo cáo trên app: {what} Mong quán kiểm tra lại cách làm việc.',
    '📣 Báo cáo trên app: {what} Tôi đã gửi phản ánh để quản lý xử lý.',
)
REPORT_REPEAT = (
    '📣 Báo cáo trên app: Hôm nay quán làm sai liên tục. {what}',
)
REVIEW_TAIL = {
    'refuse': 'Chuyện an toàn mà làm ẩu thế này thì không chấp nhận được.',
    'walkout': 'Tôi bỏ về luôn, không trả đồng nào.',
    'refund': 'Phải đòi lại một nửa tiền mới chịu.',
    'discount': 'Đã phải bớt tiền mà vẫn thấy bực.',
    'remake': 'Phải bắt làm lại mới đúng.',
}


def _pick(rows, seed: int) -> str:
    return rows[seed % len(rows)]


def _texts(t: dict, n: int = 2) -> str:
    rows = sorted(t.get('slips') or [], key=lambda r: -r['sev'])[:n]
    return ' '.join(r['text'] for r in rows if r.get('text'))


def reaction_line(kind: str, t: dict, cut: int) -> str:
    rows = REACTION.get(kind) or REACTION['grumble']
    seed = sum(ord(ch) for ch in t['id'])
    what = _texts(t, 1)
    if kind == 'accept' and not (t.get('slips')):
        return ''
    return f'{what} {_pick(rows, seed)}'.strip()


def report_text(t: dict, repeat: bool = False) -> str:
    seed = sum(ord(ch) for ch in t['id'])
    what = _texts(t, 2) or 'Làm sai điều tôi đã dặn.'
    return _pick(REPORT_REPEAT if repeat else REPORT, seed).format(what=what)[:500]


def weave(text: str, t: dict, seed: int) -> str:
    """Put the concrete mistake into the review right after its opening sentence."""
    what = _texts(t, 2)
    if not what:
        return text
    kind = (t.get('reaction') or {}).get('kind')
    tail = REVIEW_TAIL.get(kind, '')
    add = f'{what} {tail}'.strip()
    cut = -1
    for mark in ('. ', '! ', '? ', '… '):
        i = text.find(mark)
        if i != -1 and (cut == -1 or i < cut):
            cut = i
    if cut == -1:
        return f'{text} {add}'[:600]
    return f'{text[:cut + 1]} {add} {text[cut + 2:]}'.strip()[:600]
