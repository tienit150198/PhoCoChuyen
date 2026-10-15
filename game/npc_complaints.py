"""📮 Phản ánh của người dân sau ca (owner spec 14/10, I.1.1.3): after a shift, the people served may write about it.
Reusable by any career (🛃 Hải quan first, game/careers/customs.py): the career keeps the rows in its own data and
passes the texts.

Kinds: 'real' (a slip that really happened in the shift: phản ánh về nghiệp vụ) and three unreasonable ones (KINDS):
'demand' (đòi hỏi ngoài dịch vụ), 'bocphot' (bóc phốt, đòi bắt đền), 'offtopic' (không liên quan đến dịch vụ).
The player reads the text (the kind shows once decided) and answers each (OPS):
* 'accept'  ghi nhận: right for a real one (+0,1★); for an unreasonable one it is a needless mark (−0,1★);
* 'dismiss' gỡ phản ánh: right for an unreasonable one; a real one gone is a ⚠️ violation (VIOL_DISMISS);
* 'sue'     gửi hồ sơ Công an Thành phố truy tố: CATP takes up a 'bocphot' (đòi tiền, dọa bóc phốt: khởi tố) and
            warns the others; a real one sent is a ⚠️ violation (VIOL_SUE: the person was right).
A row: {id, k: kind, npc: index, text, d: career day, st: 'open' | the op chosen, out: outcome text}. Strictly validated.
"""
from __future__ import annotations

KINDS = {'real': 'Phản ánh về nghiệp vụ', 'demand': 'Đòi hỏi ngoài dịch vụ', 'bocphot': 'Bóc phốt, đòi bắt đền',
         'offtopic': 'Không liên quan đến dịch vụ'}
OPS = {'accept': '✅ Ghi nhận, khắc phục', 'dismiss': '🧹 Gỡ phản ánh', 'sue': '⚖️ Gửi Công an Thành phố truy tố'}
VIOL_DISMISS, VIOL_SUE = 'hq_dismiss', 'hq_npc_sue'
MAX_ROWS = 8          # rows kept (the oldest decided ones go first)
MAX_REAL = 2          # real ones a shift
MAX_FAKE = 2          # unreasonable ones a shift
FAKE_P = 0.45         # the chance of each unreasonable one
KEYS = frozenset(('id', 'k', 'npc', 'text', 'd', 'st', 'out'))


def roll(rng, rows: list, seq: int, day: int, real: list, fakes: dict, people: int) -> int:
    """Add the shift's rows: `real` [(npc index, text)] (the day's slips), `fakes` {kind: [texts]}; returns the new seq."""
    add = [('real', n, t) for n, t in real[:MAX_REAL]]
    for _ in range(MAX_FAKE):
        if rng.random() < FAKE_P:
            k = rng.choice(sorted(fakes))
            add.append((k, rng.randrange(people), rng.choice(fakes[k])))
    rng.shuffle(add)
    for k, n, text in add:
        seq += 1
        rows.append(dict(id=seq, k=k, npc=int(n), text=str(text)[:200], d=int(day), st='open', out=''))
    while len(rows) > MAX_ROWS:   # the oldest decided row first, else the oldest
        i = next((i for i, r in enumerate(rows) if r['st'] != 'open'), 0)
        rows.pop(i)
    return seq


def decide(row: dict, op: str) -> dict:
    """{ok: the right call, viol: a violation code or None, adj: ★ tenths, line} and the row updated."""
    real = row['k'] == 'real'
    if op == 'accept':
        out = dict(ok=real, viol=None, adj=1 if real else -1,
                   line='Đã ghi nhận, rút kinh nghiệm và trả lời người phản ánh.' if real else 'Đã ghi nhận một phản ánh không có căn cứ: ghi vào đánh giá ngày.')
    elif op == 'dismiss':
        out = dict(ok=not real, viol=VIOL_DISMISS if real else None, adj=0,
                   line='Đã gỡ: phản ánh không liên quan đến nghiệp vụ.' if not real else 'Gỡ một phản ánh đúng sự thật: bị lãnh đạo nhắc.')
    else:
        if real:
            out = dict(ok=False, viol=VIOL_SUE, adj=0, line='Công an Thành phố trả hồ sơ: người phản ánh nói đúng sự thật, không có dấu hiệu vi phạm.')
        elif row['k'] == 'bocphot':
            out = dict(ok=True, viol=None, adj=1, line='Công an Thành phố khởi tố hành vi đòi tiền, dọa bóc phốt. Phản ánh được gỡ.')
        else:
            out = dict(ok=True, viol=None, adj=0, line='Công an Thành phố tiếp nhận, mời người viết lên nhắc nhở. Phản ánh được gỡ.')
    row['st'], row['out'] = op, out['line'][:200]
    return out


def public(rows: list, people: list) -> list[dict]:
    """The rows for the page: the kind only once decided."""
    out = []
    for r in rows:
        p = people[r['npc']] if 0 <= r['npc'] < len(people) else ('Người dân', '')
        v = dict(id=r['id'], who=p[0], role=p[1], text=r['text'], d=r['d'], st=r['st'], out=r['out'])
        if r['st'] != 'open':
            v['kind'] = KINDS[r['k']]
        out.append(v)
    return out


def open_rows(rows: list) -> int:
    return sum(1 for r in rows if r['st'] == 'open')


def validate(rows, seq, people: int, need, integer, bad: str) -> None:
    need(isinstance(rows, list) and len(rows) <= MAX_ROWS, bad)
    integer(seq, 0, 10**9)
    ids = set()
    for r in rows:
        need(isinstance(r, dict) and set(r) == KEYS and r['k'] in KINDS and r['st'] in ('open', *OPS), bad)
        integer(r['id'], 1, seq)
        need(r['id'] not in ids, bad)
        ids.add(r['id'])
        integer(r['npc'], 0, max(0, people - 1))
        integer(r['d'], 0, 10**9)
        need(isinstance(r['text'], str) and 0 < len(r['text']) <= 200 and isinstance(r['out'], str) and len(r['out']) <= 200, bad)
        need((r['st'] == 'open') == (r['out'] == ''), bad)
