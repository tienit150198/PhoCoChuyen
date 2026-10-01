"""Hands-on desk work for the three office positions of Công ty CP Cánh Diều (hr_admin, secretary,
it_helpdesk). Not a career itself (it is not listed in careers.ORDER).

A dossier is one piece of real desk work, built by its career from (day, slot) and checked here
the same way in all three jobs:

* ``sort``   put every card in the right tray (CVs, the director's mail, IT tickets, cables);
* ``mark``   tap a word of a draft and pick the right wording, or a cell of a sheet and say what is
             wrong with it (a contract, a letter, a timesheet, an access list);
* ``slots``  place meetings or interviews on a grid of rooms × hours that keeps every rule on the
             board (who is busy, which room is booked, how many seats, a projector);
* ``fields`` type what a caller said or what a label shows (name, number, time, serial);
* ``seq``    pick the steps that fix it, in an order that works, and leave out the harmful ones;
* ``case``   look into it, then answer a difficult person.

Some dossiers carry a twist (the director changes his mind, a candidate calls to move, a caller
corrects his number). It fires on the n-th change or at the first hand-in, and from then on the
dossier is checked against what is true after it. Hidden facts live under keys that start with
"_" and never leave the server before the dossier is handed in. Everything is rolled from the
day, slot or task id; the player's answers are the only state that moves.

The office day itself (clock, deadlines, the boss's trust, overtime) is office.py; colleagues,
energy and the mentor track are the shared care helpers in corp_accounting.py. `OfficeJob` wires
both to the dossiers so the three careers only write their content.
"""
from __future__ import annotations

import copy
import datetime
import re
import unicodedata

from ..jsoncopy import tree_copy
from . import kit, office
from .corp_accounting import (care_can_overtime, care_close, care_ensure, care_handle, care_public, care_slow, care_start,
                              care_validate, care_validate_task)
from .. import archive as ar
from .. import consequences as cq

COMPANY = 'Công ty CP Cánh Diều'
GEN = 1
FIXED = ('form', 'work', 'papers', 'brief', 'bonus', 'gen')
TYPES = ('sort', 'mark', 'slots', 'fields', 'seq', 'case')
TW_STATES = (None, 'wait', 'fired')
COST = dict(put=4, mark=3, place=5, read=8, hint=10, file=15, reply=15, per_field=2, twist=5)   # minutes on the office clock
HINT_MAX, HINT_CUT = 3, 3           # hints per dossier, xu off the bonus for each
MAX_ERRORS, MAX_LINES = 12, 24
FIELD_MAX = 80
LOG = 12
DONE = ('completed', 'referred', 'cancelled')
AUDIT_PAY = 10
NOTES = dict(sort='xếp nhầm khay', mark='soát văn bản chưa kỹ', slots='lịch bị vướng', fields='ghi sai thông tin',
             seq='làm sai quy trình', case='xử lý chưa khéo')


# ================================================================ building blocks (used by the careers)
FAMILY = ('Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Vũ', 'Đặng', 'Bùi', 'Đỗ', 'Ngô', 'Dương', 'Lý', 'Phan', 'Huỳnh')
MIDDLE = {True: ('Thị', 'Ngọc', 'Thu', 'Mỹ', 'Thanh', 'Bảo'), False: ('Văn', 'Minh', 'Quốc', 'Đức', 'Hữu', 'Gia')}
GIVEN = {True: ('Mai', 'Lan', 'Hoa', 'Trang', 'Hà', 'Vy', 'Nhung', 'Yến', 'Trâm', 'Hương', 'Ngân', 'Quyên'),
         False: ('Nam', 'Hùng', 'Phong', 'Tuấn', 'Khoa', 'Bảo', 'Sơn', 'Thắng', 'Đạt', 'Hiếu', 'Kiên', 'Toàn')}
HOMETOWNS = ('Nam Định', 'Thanh Hóa', 'Nghệ An', 'Huế', 'Quảng Nam', 'Bình Định', 'Đắk Lắk', 'Cần Thơ', 'Long An', 'Bến Tre',
             'Thái Bình', 'Hải Dương')


def person(rng, used: set, female: bool | None = None) -> tuple[str, bool]:
    """A full Vietnamese name not used yet in this dossier (no two people share a given name)."""
    for _ in range(60):
        f = rng.random() < 0.5 if female is None else female
        given = rng.choice(GIVEN[f])
        if given in used:
            continue
        used.add(given)
        return f'{rng.choice(FAMILY)} {rng.choice(MIDDLE[f])} {given}', f
    raise RuntimeError('no free name')


def short(full: str) -> str:
    return full.split()[-1]


def xu(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


WEEKDAYS = ('thứ Hai', 'thứ Ba', 'thứ Tư', 'thứ Năm', 'thứ Sáu', 'thứ Bảy', 'Chủ nhật')


def weekday(d: int, m: int, y: int) -> str:
    return WEEKDAYS[datetime.date(y, m, d).weekday()]


def plain_text(text: str) -> str:
    """Accents removed, case kept: how a sloppy draft spells a name."""
    s = unicodedata.normalize('NFD', text).replace('đ', 'd').replace('Đ', 'D')
    return unicodedata.normalize('NFC', ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn'))


def pick(sid: str, shown: str, right: str, decoys, rng, why: str = '', sev: int = 1, code: str = '') -> dict:
    """A tappable word of a draft: up to three wordings (the one shown, the right one, decoys), shuffled."""
    opts = []
    for x in [shown, right, *decoys]:
        if x not in opts:
            opts.append(x)
    opts = opts[:3]
    rng.shuffle(opts)
    return dict(id=sid, t=shown, opts=opts, keep=opts.index(shown), _ok=opts.index(right), _why=why, _sev=sev, _code=code or 'mark')


def cell(sid: str, shown: str, ok: int = 0, why: str = '', sev: int = 1, code: str = '', trap: bool = False) -> dict:
    """A tappable cell of a sheet that uses the work's shared reasons (work['opts'], 0 = all right).
    trap: the cell is right as it stands but tempting to change; changing it costs its own sev and why."""
    c = dict(id=sid, t=shown, keep=0, _ok=int(ok), _why=why, _sev=sev, _code=code or 'mark')
    if trap:
        c['_trap'] = True
    return c


def segs_of(work: dict) -> list:
    """Every tappable segment of a mark work, in reading order."""
    out = []
    for b in work.get('blocks', []):
        if b.get('k') == 'table':
            for row in b['rows']:
                out += [x for x in row if isinstance(x, dict) and 'id' in x]
        else:
            out += [x for x in b.get('segs', []) if 'id' in x]
    return out


def opts_of(work: dict, seg: dict) -> list:
    return seg.get('opts') or work.get('opts') or []


def doc(rng, paras: list, n_bad: int, twist: dict | None = None) -> tuple[list, dict | None]:
    """A draft to proof-read. paras: [(kind, [text | dict(id, right, wrong=[…], why, sev, code)])].
    n_bad of the tappable spots are shown wrong. twist: dict(seg, to, note, why) — the right wording
    of a spot the draft has right changes later (the boss changes his mind)."""
    ids = [x['id'] for _, parts in paras for x in parts if isinstance(x, dict)]
    tw_id = twist['seg'] if twist else None
    pool = [i for i in ids if i != tw_id]
    bad = set(rng.sample(pool, min(n_bad, len(pool))))
    blocks = []
    for kind, parts in paras:
        segs = []
        for x in parts:
            if isinstance(x, str):
                segs.append(dict(t=x))
                continue
            wrong = [w for w in x['wrong'] if w != x['right']]
            if x['id'] in bad:
                shown = rng.choice(wrong)
                segs.append(pick(x['id'], shown, x['right'], [w for w in wrong if w != shown], rng, x.get('why', ''), x.get('sev', 1), x.get('code', '')))
            elif x['id'] == tw_id:
                segs.append(pick(x['id'], x['right'], x['right'], [twist['to']] + wrong, rng))
            else:
                segs.append(pick(x['id'], x['right'], x['right'], wrong, rng))
        blocks.append(dict(k=kind, segs=segs))
    tw = None
    if twist:
        seg = next(s for b in blocks for s in b['segs'] if s.get('id') == tw_id)
        tw = dict(at=max(2, len(bad)), seg=tw_id, ok=seg['opts'].index(twist['to']), sev=twist.get('sev', 2), note=twist['note'],
                  why=twist.get('why', 'Sếp vừa đổi ý.'))
    return blocks, tw


def case_work(rng, cases: list) -> dict:
    """A hard conversation picked from a career's CASES: facts to look into, then three answers."""
    x = copy.deepcopy(rng.choice(cases))
    rng.shuffle(x['options'])
    return dict(npc=x['npc'], title=x['title'], opening=x['opening'],
                brief='Tìm hiểu cho rõ (mỗi chuyện mất chút thời gian), rồi chọn cách trả lời.',
                papers=[], work=dict(type='case', facts=x['facts'], options=x['options'], _twist=None))


def twist_on(rng, day: int, mod_id: str, busy_mod: str | None = None) -> bool:
    """Whether this dossier carries a change of mind: none on the first day, more often later and on
    the day the boss keeps changing plans."""
    if day <= 1:
        return False
    p = (0.25, 0.35, 0.45, 0.5)[kit.tier(day)]
    if busy_mod and mod_id == busy_mod:
        p = 0.8
    return rng.random() < p


# ================================================================ normalising typed answers
def fold(text) -> str:
    """Lower case, no accents, single spaces: how a typed name is compared."""
    s = unicodedata.normalize('NFD', str(text or '')).replace('đ', 'd').replace('Đ', 'D')
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn').lower()
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


def digits(text) -> str:
    return re.sub(r'\D+', '', str(text or ''))


def as_time(text) -> str:
    """'9h30', '09:30', '9.30', '930', '16h' → 'HH:MM'; '' when it is not a time."""
    s = str(text or '').strip().lower().replace('giờ', 'h').replace(' ', '')
    m = re.fullmatch(r'(\d{1,2})(?:[:h.]?(\d{2}))?h?', s)
    if not m:
        return ''
    h, mm = int(m.group(1)), int(m.group(2) or 0)
    return f'{h:02d}:{mm:02d}' if h < 24 and mm < 60 else ''


def as_date(text) -> str:
    """'5/3/2027', '05-03-2027', '5.3.2027' → '05/03/2027'; '' when it is not a date."""
    m = re.fullmatch(r'\s*(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4})\s*', str(text or ''))
    if not m:
        return ''
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f'{d:02d}/{mo:02d}/{y}' if 1 <= d <= 31 and 1 <= mo <= 12 else ''


def code_of(text) -> str:
    """A serial or asset code: letters and digits only, upper case."""
    return re.sub(r'[^A-Z0-9]+', '', fold(text).upper())


def same(kind: str, typed, right) -> bool:
    if kind == 'digits':
        return bool(digits(typed)) and digits(typed) == digits(right)
    if kind == 'time':
        return bool(as_time(typed)) and as_time(typed) == as_time(right)
    if kind == 'date':
        return bool(as_date(typed)) and as_date(typed) == as_date(right)
    if kind == 'code':
        return bool(code_of(typed)) and code_of(typed) == code_of(right)
    if kind == 'pick':
        return typed == right
    return bool(fold(typed)) and fold(typed) == fold(right)


def field_ok(f: dict, typed) -> bool:
    kind = f.get('kind', 'text')
    return same(kind, typed, f['_ok']) or any(same(kind, typed, a) for a in f.get('_alt', []))


# ================================================================ the twist
def twist(t: dict) -> dict | None:
    tw = t['work'].get('_twist')
    return tw if isinstance(tw, dict) else None


def fired(t: dict) -> bool:
    return t.get('tw') == 'fired'


def maybe_fire(t: dict, at_file: bool = False) -> str:
    """The twist fires on its n-th change (at > 0) or at the first hand-in. Returns the news or ''."""
    tw = twist(t)
    if not tw or t.get('tw') != 'wait':
        return ''
    if at_file or (tw.get('at', 0) and t['acts'] >= tw['at']):
        t['tw'] = 'fired'
        return f'📞 {tw["note"]}'
    return ''


def truth(t: dict) -> dict:
    """The work as it is true now (after a fired twist), hidden keys included."""
    w = t['work']
    tw = twist(t)
    if not tw or not fired(t):
        return w
    w = copy.deepcopy(w)
    kind = w['type']
    if kind == 'sort':
        for it in w['items']:
            if it['id'] == tw['item']:
                it['_bin'], it['_why'] = tw['bin'], tw.get('why', it['_why'])
                it['_sev'] = tw.get('sev', it.get('_sev', 1))
    elif kind == 'mark':
        for sg in segs_of(w):
            if sg['id'] == tw['seg']:
                sg['_ok'], sg['_why'] = tw['ok'], tw.get('why', sg.get('_why', ''))
                sg['_sev'] = tw.get('sev', sg.get('_sev', 1))
    elif kind == 'slots':
        w['rules'] = w['rules'] + [tw['rule']]
    elif kind == 'fields':
        for f in w['fields']:
            if f['id'] == tw['field']:
                f['_ok'], f['_alt'], f['_why'] = tw['ok'], tw.get('alt', []), tw.get('why', f.get('_why', ''))
        w['script'] = w['script'] + [tw['line']]
    elif kind == 'seq':
        for st in w['pool']:
            if st['id'] == tw['step']:
                st['_role'], st['_why'] = 'need', tw.get('why', st.get('_why', ''))
        w['_after'] = list(w.get('_after', [])) + [list(x) for x in tw.get('after', [])]
    return w


# ================================================================ slots: building a board that has a solution
def _cell(v) -> tuple[str, str] | None:
    if not isinstance(v, str) or v.count('|') != 1:
        return None
    a, b = v.split('|')
    return a, b


def _fits(it: dict, col: dict) -> bool:
    return it.get('size', 1) <= col.get('cap', 99) and all(x in col.get('tags', []) for x in it.get('needs', []))


def build_slots(rng, cols: list, rows: list, tags: dict, items: list, busy: list, taken: list, windows: list,
                before: list, twist_busy: dict | None) -> dict:
    """A rooms × hours board with a hidden placement that keeps every rule.

    items   dict(id, title, who=[names], size, needs=[tag ids]) — what has to be placed;
    busy    dict(who, text) — a person who is out for one or two hours (rolled to avoid the solution);
    taken   dict(text) — a cell already booked by someone else (rolled on a free cell; '{room}' '{time}');
    windows dict(item, half=('am'|'pm'), text) — an item that can only happen in one half of the day;
    before  dict(a, b, text) — item a must come before item b;
    twist_busy  dict(who, note, text) — the change of mind: that person is out at one or two more hours."""
    half = {r['id']: r['half'] for r in rows}
    rid = [r['id'] for r in rows]
    for _ in range(400):
        sol, used, ok = {}, set(), True
        order = list(items)
        rng.shuffle(order)
        for it in order:
            win = next((w for w in windows if w['item'] == it['id']), None)
            cand = [(c['id'], r) for c in cols for r in rid
                    if (c['id'], r) not in used and _fits(it, c) and (not win or half[r] == win['half'])
                    and not any(r == sol[o['id']][1] and set(o.get('who', [])) & set(it.get('who', [])) for o in items if o['id'] in sol)]
            if not cand:
                ok = False
                break
            sol[it['id']] = rng.choice(cand)
            used.add(sol[it['id']])
        if ok and all(rid.index(sol[b['a']][1]) < rid.index(sol[b['b']][1]) for b in before):
            break
    else:
        raise RuntimeError('slots board without a solution')
    rules = []
    for b in busy:
        mine = {sol[it['id']][1] for it in items if b['who'] in it.get('who', [])}
        free = [r for r in rid if r not in mine]
        hours = sorted(rng.sample(free, min(len(free), rng.choice((1, 2)))), key=rid.index)
        rules.append(dict(kind='busy', who=b['who'], rows=hours, text=b['text']))
    free_cells = [(c['id'], r) for c in cols for r in rid if (c['id'], r) not in used]
    rng.shuffle(free_cells)
    # A booked cell bites most where the items need it: prefer rooms that more items could use.
    free_cells.sort(key=lambda x: -sum(_fits(it, next(c for c in cols if c['id'] == x[0])) for it in items))
    labels = {c['id']: c['label'] for c in cols}
    rlabel = {r['id']: r['label'] for r in rows}
    for tk, (col, row) in zip(taken, free_cells[:len(taken)]):
        rules.append(dict(kind='taken', col=col, row=row, text=tk['text'].format(room=labels[col], time=rlabel[row])))
    for w in windows:
        rules.append(dict(kind='window', item=w['item'], rows=[r for r in rid if half[r] == w['half']], text=w['text']))
    for b in before:
        rules.append(dict(kind='before', a=b['a'], b=b['b'], text=b['text']))
    tw = None
    if twist_busy:
        mine = {sol[it['id']][1] for it in items if twist_busy['who'] in it.get('who', [])}
        already = {r for x in rules if x['kind'] == 'busy' and x['who'] == twist_busy['who'] for r in x['rows']}
        free = [r for r in rid if r not in mine and r not in already]
        if free:
            hours = sorted(rng.sample(free, min(len(free), 2)), key=rid.index)
            tw = dict(at=len(items), note=twist_busy['note'],
                      rule=dict(kind='busy', who=twist_busy['who'], rows=hours, text=twist_busy['text']))
    return dict(type='slots', cols=cols, rows=rows, tags=tags, items=items, rules=rules,
                _sol={k: f'{a}|{b}' for k, (a, b) in sol.items()}, _twist=tw)


def slot_problems(w: dict, ans: dict) -> list:
    """Every rule the placement breaks: list of (code, sev, text, item id)."""
    cols = {x['id']: x for x in w['cols']}
    rows = [x['id'] for x in w['rows']]
    rlabel = {x['id']: x['label'] for x in w['rows']}
    items = {x['id']: x for x in w['items']}
    place = {k: _cell(v) for k, v in ans.items() if k in items and _cell(v)}
    out = []
    for iid, it in items.items():
        if iid not in place:
            out.append(('slot_empty', 2, f'“{it["title"]}” chưa được xếp.', iid))
    taken = {(r['col'], r['row']): r for r in w['rules'] if r['kind'] == 'taken'}
    for iid, (col, row) in place.items():
        it, room = items[iid], cols[col]
        if (col, row) in taken:
            out.append(('slot_taken', 2, f'“{it["title"]}” trùng chỗ đã có người đặt: {taken[(col, row)]["text"]}', iid))
        if it.get('size', 1) > room.get('cap', 99):
            out.append(('slot_cap', 2, f'“{it["title"]}” có {it["size"]} người mà {room["label"]} chỉ {room["cap"]} chỗ.', iid))
        lack = [x for x in it.get('needs', []) if x not in room.get('tags', [])]
        if lack:
            out.append(('slot_tag', 2, f'“{it["title"]}” cần {", ".join(w["tags"].get(x, x) for x in lack)} mà {room["label"]} không có.', iid))
    for r in w['rules']:
        if r['kind'] == 'busy':
            for iid, (col, row) in place.items():
                if r['who'] in items[iid].get('who', []) and row in r['rows']:
                    out.append(('slot_busy', 2, f'{r["who"]} bận lúc {rlabel[row]} ({r["text"]}) mà vẫn xếp “{items[iid]["title"]}”.', iid))
        elif r['kind'] == 'window' and r['item'] in place:
            if place[r['item']][1] not in r['rows']:
                out.append(('slot_window', 2, f'“{items[r["item"]]["title"]}”: {r["text"]}', r['item']))
        elif r['kind'] == 'before' and r['a'] in place and r['b'] in place:
            if rows.index(place[r['a']][1]) >= rows.index(place[r['b']][1]):
                out.append(('slot_order', 2, r['text'], r['b']))
    by_row: dict = {}
    for iid, (col, row) in place.items():
        by_row.setdefault(row, []).append(iid)
    for row, ids in by_row.items():
        seen: dict = {}
        for iid in ids:
            for who in items[iid].get('who', []):
                if who in seen:
                    out.append(('slot_double', 2, f'{who} không thể cùng lúc ở “{items[seen[who]]["title"]}” và “{items[iid]["title"]}” ({rlabel[row]}).', iid))
                else:
                    seen[who] = iid
    return out


# ================================================================ grading
def _err(code: str, sev: int, text: str, ref: str | None = None) -> dict:
    return dict(code=str(code)[:32], sev=max(1, min(3, int(sev))), text=str(text)[:200], ref=ref)


def _pick_label(f: dict, v) -> str:
    if f.get('kind') == 'pick':
        return next((o['label'] for o in f.get('opts', []) if o['id'] == v), str(v))
    return str(v)


def grade(t: dict) -> dict:
    """What is right and wrong in the dossier as it stands (hidden facts read, nothing written).
    Returns dict(ok, total, errors=[{code, sev, text, ref}], lines=[{ref, ok, text}])."""
    w = truth(t)
    ans = t.get('ans') or {}
    kind = w['type']
    errors, lines, ok, total = [], [], 0, 0
    if kind == 'sort':
        bins = {b['id']: b for b in w['bins']}
        for it in w['items']:
            total += 1
            right = ans.get(it['id']) == it['_bin']
            ok += right
            label = bins[it['_bin']]['label']
            if not right:
                errors.append(_err(it.get('_code') or 'sort', it.get('_sev', 1), f'“{it["title"]}” phải vào “{label}”: {it["_why"]}', it['id']))
            lines.append(dict(ref=it['id'], ok=right, text=f'{it["title"]} → {label}. {it["_why"]}'))
    elif kind == 'mark':
        for sg in segs_of(w):
            total += 1
            opts = opts_of(w, sg)
            got = ans.get(sg['id'], sg['keep'])
            right = got == sg['_ok']
            ok += right
            if right:
                if sg['_ok'] != sg['keep']:
                    lines.append(dict(ref=sg['id'], ok=True, text=f'“{sg["t"]}” → “{opts[sg["_ok"]]}”. {sg.get("_why", "")}'.strip()))
                continue
            if sg['_ok'] == sg['keep']:
                trap = sg.get('_trap')
                errors.append(_err(sg.get('_code') if trap else 'mark_changed', sg.get('_sev', 1) if trap else 1,
                                   f'“{sg["t"]}” vốn đúng mà bị đổi thành “{opts[got]}”. {sg.get("_why", "") if trap else ""}'.strip(), sg['id']))
                lines.append(dict(ref=sg['id'], ok=False, text=f'“{sg["t"]}” vốn đúng, không cần sửa. {sg.get("_why", "") if trap else ""}'.strip()))
            else:
                how = 'bị bỏ sót' if got == sg['keep'] else f'sửa thành “{opts[got]}” vẫn chưa đúng'
                errors.append(_err(sg.get('_code') or 'mark', sg.get('_sev', 1),
                                   f'“{sg["t"]}” {how}: đúng là “{opts[sg["_ok"]]}”. {sg.get("_why", "")}'.strip(), sg['id']))
                lines.append(dict(ref=sg['id'], ok=False, text=f'“{sg["t"]}” → đúng là “{opts[sg["_ok"]]}”. {sg.get("_why", "")}'.strip()))
    elif kind == 'slots':
        probs = slot_problems(w, ans)
        bad = {p[3] for p in probs}
        total = len(w['items'])
        ok = total - len(bad)
        for code, sev, text, ref in probs:
            errors.append(_err(code, sev, text, ref))
        for it in w['items']:
            where = _cell(ans.get(it['id']))
            if where:
                col = next(x['label'] for x in w['cols'] if x['id'] == where[0])
                row = next(x['label'] for x in w['rows'] if x['id'] == where[1])
                lines.append(dict(ref=it['id'], ok=it['id'] not in bad, text=f'{it["title"]}: {row} · {col}'))
            else:
                lines.append(dict(ref=it['id'], ok=False, text=f'{it["title"]}: chưa xếp'))
    elif kind == 'fields':
        for f in w['fields']:
            total += 1
            typed = ans.get(f['id'], '')
            right = field_ok(f, typed)
            ok += right
            shown = _pick_label(f, f['_ok'])
            if not right:
                got = _pick_label(f, typed) if typed else 'trống'
                errors.append(_err(f.get('_code') or 'field', f.get('_sev', 1),
                                   f'Ô “{f["label"]}” ghi “{str(got)[:40]}”, đúng là “{shown}”. {f.get("_why", "")}'.strip(), f['id']))
            lines.append(dict(ref=f['id'], ok=right, text=f'{f["label"]}: {shown}'))
    elif kind == 'seq':
        order = [x for x in (ans.get('order') or []) if any(x == s['id'] for s in w['pool'])]
        pool = {s['id']: s for s in w['pool']}
        need = [s['id'] for s in w['pool'] if s['_role'] == 'need']
        total = len(need) + sum(1 for s in w['pool'] if s['_role'] == 'bad')
        for sid in order:
            if pool[sid]['_role'] == 'bad':
                errors.append(_err(pool[sid].get('_code') or 'seq_bad', pool[sid].get('_sev', 2), f'Không được “{pool[sid]["label"]}”: {pool[sid]["_why"]}', sid))
                lines.append(dict(ref=sid, ok=False, text=f'✗ {pool[sid]["label"]}: {pool[sid]["_why"]}'))
        for sid in need:
            if sid not in order:
                errors.append(_err('seq_missing', pool[sid].get('_sev', 1), f'Thiếu bước “{pool[sid]["label"]}”: {pool[sid]["_why"]}', sid))
                lines.append(dict(ref=sid, ok=False, text=f'Thiếu: {pool[sid]["label"]}. {pool[sid]["_why"]}'))
        for a, b, why in w.get('_after', []):
            if a in order and b in order and order.index(a) > order.index(b):
                errors.append(_err('seq_order', 1, f'“{pool[b]["label"]}” phải sau “{pool[a]["label"]}”: {why}', b))
                lines.append(dict(ref=b, ok=False, text=f'Sai thứ tự: “{pool[a]["label"]}” trước rồi mới “{pool[b]["label"]}”. {why}'))
        ok = max(0, total - len({e['ref'] for e in errors}))
        if not errors:
            lines.append(dict(ref=None, ok=True, text='Đủ bước, đúng thứ tự, không bước nào gây hại.'))
    elif kind == 'case':
        opt = next((o for o in w['options'] if o['id'] == ans.get('choice')), None)
        total = 1
        if opt:
            ok = int(opt['_q'] == 'good')
            if opt['_q'] == 'ok':
                errors.append(_err('case_half', 1, opt['_out'], opt['id']))
            elif opt['_q'] == 'bad':
                errors.append(_err('case_bad', opt.get('_sev', 2), opt['_out'], opt['id']))
            lines.append(dict(ref=opt['id'], ok=opt['_q'] == 'good', text=opt['_out']))
            good = next((o for o in w['options'] if o['_q'] == 'good'), None)
            if good and good is not opt:
                lines.append(dict(ref=good['id'], ok=True, text=f'Cách tốt hơn: {good["label"]}.'))
    return dict(ok=int(ok), total=int(total), errors=errors[:MAX_ERRORS], lines=lines[:MAX_LINES])


def ready(t: dict) -> str:
    """'' when the dossier can be handed in, else what is still missing (shown to the player)."""
    w, ans = t['work'], t.get('ans') or {}
    if w['type'] == 'sort':
        left = sum(1 for it in w['items'] if it['id'] not in ans)
        return f'Còn {left} thẻ chưa xếp vào khay.' if left else ''
    if w['type'] == 'slots':
        left = sum(1 for it in w['items'] if it['id'] not in ans)
        return f'Còn {left} việc chưa xếp lịch.' if left else ''
    if w['type'] == 'fields':
        left = [f for f in w['fields'] if not str(ans.get(f['id'], '')).strip()]
        return f'Còn trống ô “{left[0]["label"]}”.' if left else ''
    if w['type'] == 'seq':
        return '' if ans.get('order') else 'Chọn các bước sẽ làm, theo thứ tự.'
    if w['type'] == 'case':
        return '' if ans.get('choice') else 'Chọn cách trả lời.'
    return ''


def hint_text(t: dict) -> str:
    """One thing that is still wrong right now, in a colleague's words."""
    w = truth(t)
    ans = t.get('ans') or {}
    kind = w['type']
    if kind == 'sort':
        for it in w['items']:
            if it['id'] in ans and ans[it['id']] != it['_bin']:
                return f'Xem lại thẻ “{it["title"]}”: chưa đúng khay.'
        left = sum(1 for it in w['items'] if it['id'] not in ans)
        return f'Mấy thẻ đã xếp đều ổn. Còn {left} thẻ chưa xếp.' if left else 'Khay nào cũng đúng rồi, nộp được.'
    if kind == 'mark':
        for sg in segs_of(w):
            if ans.get(sg['id'], sg['keep']) != sg['_ok']:
                return f'Soát lại chỗ “{sg["t"]}”.'
        return 'Soát lại không thấy chỗ nào sai nữa.'
    if kind == 'slots':
        probs = [p for p in slot_problems(w, ans) if p[0] != 'slot_empty']
        if probs:
            return probs[0][2]
        left = sum(1 for it in w['items'] if it['id'] not in ans)
        return f'Lịch đang ổn. Còn {left} việc chưa xếp.' if left else 'Lịch không vướng gì, nộp được.'
    if kind == 'fields':
        for f in w['fields']:
            if f['id'] in ans and not field_ok(f, ans[f['id']]):
                return f'Đọc lại đoạn ghi: ô “{f["label"]}” chưa khớp.'
        return 'Đọc kỹ cả câu cuối: người ta hay sửa lại số hoặc giờ ở đó.'
    if kind == 'seq':
        order = ans.get('order') or []
        for st in w['pool']:
            if st['id'] in order and st['_role'] == 'bad':
                return f'Đừng “{st["label"].lower()}”.'
        miss = [st for st in w['pool'] if st['_role'] == 'need' and st['id'] not in order]
        if miss and order:
            return f'Còn thiếu bước “{miss[0]["label"]}”.'
        first = next((st['label'] for st in w['pool'] if st['_role'] == 'need'), '')
        return f'Có một bước cần làm là “{first}”.' if not order else 'Các bước đủ rồi, xem lại thứ tự.'
    if kind == 'case':
        unread = [f for f in w['facts'] if f['id'] not in (ans.get('read') or [])]
        return f'Tìm hiểu thêm: {unread[0]["title"].lower()}.' if unread else 'Đủ dữ kiện rồi. Chọn cách vừa đúng quy định vừa có lối ra cho người ta.'
    return ''


# ================================================================ the player's moves on a dossier
def _open(t: dict, kinds) -> None:
    kit.need(t['work']['type'] in kinds, 'Thao tác này không dành cho hồ sơ đang mở.')
    kit.need(not t['filed'] and t['status'] not in DONE, 'Hồ sơ này đã nộp.')


def put(t: dict, p: dict) -> str:
    _open(t, ('sort',))
    w = t['work']
    it = next((x for x in w['items'] if x['id'] == p.get('item')), None)
    kit.need(it, 'Không có thẻ này.')
    b = p.get('bin')
    if b is None:
        kit.need(it['id'] in t['ans'], 'Thẻ này chưa xếp.')
        t['ans'].pop(it['id'])
        return f'Bỏ “{it["title"]}” ra khỏi khay.'
    b = kit.one_of(b, [x['id'] for x in w['bins']], 'Không có khay này.')
    t['ans'][it['id']] = b
    t['acts'] += 1
    return f'“{it["title"]}” → {next(x["label"] for x in w["bins"] if x["id"] == b)}.'


def mark(t: dict, p: dict) -> str:
    _open(t, ('mark',))
    w = t['work']
    sg = next((x for x in segs_of(w) if x['id'] == p.get('seg')), None)
    kit.need(sg, 'Không có chỗ này trong văn bản.')
    opts = opts_of(w, sg)
    i = kit.integer(p.get('opt'), 0, len(opts) - 1)
    if i == sg['keep']:
        t['ans'].pop(sg['id'], None)
        return f'Giữ nguyên “{sg["t"]}”.'
    t['ans'][sg['id']] = i
    t['acts'] += 1
    return f'“{sg["t"]}” → “{opts[i]}”.'


def place(t: dict, p: dict) -> str:
    _open(t, ('slots',))
    w = t['work']
    it = next((x for x in w['items'] if x['id'] == p.get('item')), None)
    kit.need(it, 'Không có việc này trên bảng lịch.')
    v = p.get('cell')
    if v is None:
        kit.need(it['id'] in t['ans'], 'Việc này chưa xếp.')
        t['ans'].pop(it['id'])
        return f'Gỡ “{it["title"]}” khỏi bảng lịch.'
    xy = _cell(v)
    kit.need(xy and xy[0] in [c['id'] for c in w['cols']] and xy[1] in [r['id'] for r in w['rows']], 'Ô lịch không có.')
    kit.need(not any(k != it['id'] and _cell(x) == xy for k, x in t['ans'].items()), 'Ô này đã có việc khác. Gỡ việc kia ra trước.')
    t['ans'][it['id']] = f'{xy[0]}|{xy[1]}'
    t['acts'] += 1
    col = next(c['label'] for c in w['cols'] if c['id'] == xy[0])
    row = next(r['label'] for r in w['rows'] if r['id'] == xy[1])
    return f'“{it["title"]}”: {row} · {col}.'


def take_fields(t: dict, p: dict) -> None:
    """The typed boxes arrive with the hand-in; kept even when a twist stops that hand-in."""
    w = t['work']
    got = p.get('fields')
    kit.need(isinstance(got, dict) and len(got) <= len(w['fields']), 'Thiếu các ô cần ghi.')
    ids = {f['id']: f for f in w['fields']}
    out = {}
    for k, v in got.items():
        kit.need(k in ids and isinstance(v, (str, int)) and not isinstance(v, bool), 'Ô ghi chép không hợp lệ.')
        v = str(v).strip()[:FIELD_MAX]
        if ids[k].get('kind') == 'pick' and v:
            kit.need(v in [o['id'] for o in ids[k].get('opts', [])], 'Lựa chọn không có.')
        if v:
            out[k] = v
    if out != t['ans']:
        t['acts'] += 1
    t['ans'] = out


def take_order(t: dict, p: dict) -> None:
    w = t['work']
    order = p.get('order')
    ids = [s['id'] for s in w['pool']]
    kit.need(isinstance(order, list) and 1 <= len(order) <= len(ids) and all(isinstance(x, str) and x in ids for x in order)
             and len(set(order)) == len(order), 'Chọn ít nhất một bước, mỗi bước một lần.')
    if order != t['ans'].get('order'):
        t['acts'] += 1
    t['ans'] = dict(order=list(order))


def read(t: dict, p: dict) -> str:
    _open(t, ('case',))
    f = next((x for x in t['work']['facts'] if x['id'] == p.get('fact')), None)
    kit.need(f, 'Không có chuyện này.')
    rd = t['ans'].setdefault('read', [])
    kit.need(f['id'] not in rd, 'Bạn đã tìm hiểu chuyện này rồi.')
    rd.append(f['id'])
    return f'🔍 {f["title"]}: {f["text"]}'


def choose(t: dict, p: dict) -> dict:
    _open(t, ('case',))
    w = t['work']
    o = next((x for x in w['options'] if x['id'] == p.get('option')), None)
    kit.need(o, 'Chọn cách trả lời.')
    rd = t['ans'].get('read') or []
    missing = [f for f in o.get('requires', ()) if f not in rd]
    kit.need(not missing, 'Tìm hiểu thêm đã: ' + ', '.join(next(x['title'] for x in w['facts'] if x['id'] == m).lower() for m in missing) + '.')
    t['ans']['choice'] = o['id']
    return o


# ================================================================ data, public view and saves
def day_stats(day: int = 0) -> dict:
    return dict(day=day, filed=0, clean=0, late=0, errors=0, heavy=0, hints=0)


def initial() -> dict:
    return dict(v=1, filed=0, late=0, clean=0, log=[], office=office.initial(), desk=kit.desk_initial(), day_stats=day_stats())


def _strip(v):
    if isinstance(v, dict):
        return {k: _strip(x) for k, x in v.items() if not k.startswith('_')}
    if isinstance(v, list):
        return [_strip(x) for x in v]
    return v


def public_task(t: dict) -> dict:
    v = {k: _strip(tree_copy(x)) for k, x in t.items() if not k.startswith('_') and k not in ('work', 'papers', 'result')}
    v['tw'] = 'fired' if fired(t) else None   # a change of mind still to come stays a surprise
    if not t['known']:
        v.update(work=None, papers=None, brief=None, result=None)
        return v
    w = _strip(tree_copy(t['work']))
    tw = twist(t)
    if tw and fired(t):
        x = dict(note=tw['note'])
        kind = w['type']
        if kind == 'sort':
            x['item'] = tw['item']
        elif kind == 'mark':
            x['seg'] = tw['seg']
        elif kind == 'slots':
            w['rules'] = w['rules'] + [dict(_strip(tw['rule']), new=True)]
        elif kind == 'fields':
            x['field'] = tw['field']
            w['script'] = w['script'] + [dict(_strip(tw['line']), new=True)]
        elif kind == 'seq':
            x['step'] = tw['step']
        w['twist'] = x
    if w['type'] == 'case':   # what you have not looked into yet stays unknown
        seen = set(t['ans'].get('read') or [])
        for f in w['facts']:
            if f['id'] not in seen:
                f['text'] = None
    v['work'] = w
    v['papers'] = tree_copy(t['papers'])
    v['result'] = tree_copy(t['result'])
    v['ready'] = ready(t) if not t['filed'] else ''
    v['hints_left'] = max(0, HINT_MAX - len(t['tips']))
    return v


def _vstr_list(x, allowed, n: int, msg: str) -> None:
    kit.need(isinstance(x, list) and len(x) <= n and len(set(x)) == len(x) and all(isinstance(v, str) and v in allowed for v in x), msg)


def validate_task(t: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản hồ sơ văn phòng không hợp lệ.')
    w = t.get('work')
    kit.need(isinstance(w, dict) and w.get('type') in TYPES, 'Hồ sơ văn phòng sai.')
    ans = t.get('ans')
    kit.need(isinstance(ans, dict), 'Bài làm của hồ sơ sai.')
    kind = w['type']
    if kind == 'sort':
        items, bins = {x['id'] for x in w['items']}, {b['id'] for b in w['bins']}
        kit.need(set(ans) <= items and all(isinstance(v, str) and v in bins for v in ans.values()), 'Khay hồ sơ sai.')
    elif kind == 'mark':
        segs = {x['id']: x for x in segs_of(w)}
        kit.need(set(ans) <= set(segs), 'Chỗ sửa trong văn bản sai.')
        for k, v in ans.items():
            kit.need(type(v) is int and 0 <= v < len(opts_of(w, segs[k])) and v != segs[k]['keep'], 'Chỗ sửa trong văn bản sai.')
    elif kind == 'slots':
        items = {x['id'] for x in w['items']}
        cols, rows = {x['id'] for x in w['cols']}, {x['id'] for x in w['rows']}
        kit.need(set(ans) <= items, 'Bảng lịch sai.')
        cells = [_cell(v) for v in ans.values()]
        kit.need(all(xy and xy[0] in cols and xy[1] in rows for xy in cells) and len(set(cells)) == len(cells), 'Bảng lịch sai.')
    elif kind == 'fields':
        kit.need(set(ans) <= {f['id'] for f in w['fields']} and all(isinstance(v, str) and 0 < len(v) <= FIELD_MAX for v in ans.values()),
                 'Ô ghi chép sai.')
    elif kind == 'seq':
        kit.need(set(ans) <= {'order'}, 'Danh sách bước sai.')
        if 'order' in ans:
            _vstr_list(ans['order'], {s['id'] for s in w['pool']}, len(w['pool']), 'Danh sách bước sai.')
    elif kind == 'case':
        kit.need(set(ans) <= {'read', 'choice'}, 'Hồ sơ trao đổi sai.')
        if 'read' in ans:
            _vstr_list(ans['read'], {f['id'] for f in w['facts']}, len(w['facts']), 'Hồ sơ trao đổi sai.')
        kit.need(ans.get('choice') is None or ans['choice'] in {o['id'] for o in w['options']}, 'Hồ sơ trao đổi sai.')
    kit.integer(t.get('acts'), 0, 10 ** 6)
    kit.need(t.get('tw') in TW_STATES and (t['tw'] is None) == (twist(t) is None), 'Chuyện đổi ý của hồ sơ sai.')
    for k in ('filed', 'late'):
        kit.need(type(t.get(k)) is bool, 'Trạng thái hồ sơ sai.')
    kit.need(isinstance(t.get('tips'), list) and len(t['tips']) <= HINT_MAX and all(isinstance(x, str) and len(x) <= 300 for x in t['tips']),
             'Gợi ý hồ sơ sai.')
    r = t.get('result')
    if t['filed']:
        kit.need(isinstance(r, dict) and set(r) == {'ok', 'total', 'errors', 'lines'}, 'Kết quả hồ sơ sai.')
        kit.integer(r['ok'], 0, 1000)
        kit.integer(r['total'], 0, 1000)
        kit.need(isinstance(r['errors'], list) and len(r['errors']) <= MAX_ERRORS and isinstance(r['lines'], list) and len(r['lines']) <= MAX_LINES,
                 'Kết quả hồ sơ sai.')
        for e in r['errors']:
            kit.need(isinstance(e, dict) and set(e) == {'code', 'sev', 'text', 'ref'}, 'Kết quả hồ sơ sai.')
            kit.integer(e['sev'], 1, 3)
            kit.text(e['text'], 200)
        for x in r['lines']:
            kit.need(isinstance(x, dict) and set(x) == {'ref', 'ok', 'text'} and type(x['ok']) is bool, 'Kết quả hồ sơ sai.')
            kit.text(x['text'], 400)
    else:
        kit.need(r is None, 'Kết quả hồ sơ sai.')
        kit.need(t['status'] != 'completed', 'Hồ sơ hoàn tất khi chưa nộp.')
    office.validate_task(t)


def validate_data(d: dict) -> None:
    kit.integer(d.get('v'), 1, 1)
    for k in ('filed', 'late', 'clean'):
        kit.integer(d.get(k), 0, 10 ** 9)
    kit.need(isinstance(d.get('log'), list) and len(d['log']) <= LOG, 'Sổ hồ sơ sai.')
    for row in d['log']:
        kit.need(isinstance(row, dict) and set(row) == {'day', 'title', 'late', 'errors'} and type(row['late']) is bool, 'Sổ hồ sơ sai.')
        kit.integer(row['day'], 1, 10 ** 7)
        kit.integer(row['errors'], 0, 10 ** 6)
        kit.text(row['title'], 200)
    st = d.get('day_stats')
    kit.need(isinstance(st, dict) and set(st) == set(day_stats()), 'Số liệu trong ngày sai.')
    for v in st.values():
        kit.integer(v, 0, 10 ** 7)
    office.validate(d['office'])


# ================================================================ one office job, wired
class OfficeJob:
    """Everything a hands-on office career does with its dossiers; the career module binds these
    methods to its module-level hooks (make_task, handle, on_start, …) and writes only content.

    cfg: id, prefix, boss (name), boss_npc (people index), forms [dict(id, label, min_day, bonus, build)],
    mods (office MODS rows), forced, intro, more_mods (mod ids that add a card), busy_mod (the mod id on
    which plans change most), crunch (forced mod id: tighter deadlines, better overtime), audit (mod id
    with an end-of-day check, or None), auditor (who checks), care (corp_accounting care cfg), desk
    (kit desk scripts), rules(day) → cards, hints {form id: how to work it}, staff_area {role: form ids},
    helpers (who answers a hint).

    build(rng, ctx) → dict(npc, title, opening, brief, papers, work); ctx = day, slot, tier, mod, more,
    twist (put a '_twist' in the work when True)."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.id = cfg['id']
        self.p = cfg['prefix']

    # ---------------------------------------------------------------- generation
    def mod(self, day: int) -> dict:
        return office.mod_of(self.id, day, self.cfg['mods'], self.cfg.get('forced'), self.cfg.get('intro'))

    def form_of(self, day: int, slot: int) -> dict:
        pool = [f for f in self.cfg['forms'] if f['min_day'] <= day]
        return pool[(kit.rng(self.id, day).randrange(len(pool)) + slot) % len(pool)]

    def make_task(self, day: int, slot: int, serial: int) -> dict:
        f = self.form_of(day, slot)
        mod = self.mod(day)
        ctx = dict(day=day, slot=slot, tier=kit.tier(day), mod=mod['id'],
                   more=1 if mod['id'] in self.cfg.get('more_mods', ()) else 0,
                   twist=twist_on(kit.rng(self.id, day, slot, 'twist'), day, mod['id'], self.cfg.get('busy_mod')))
        g = f['build'](kit.rng(self.id, day, slot, f['id']), ctx)
        work = g['work']
        if not ctx['twist'] or not isinstance(work.get('_twist'), dict):
            work['_twist'] = None
        return kit.base_task(self.id, day, slot, serial, g['npc'], g['title'], g['opening'], form=f['id'], work=work,
                             papers=g['papers'], brief=g['brief'], bonus=f['bonus'], gen=GEN, ans={}, acts=0,
                             tw='wait' if work['_twist'] else None, filed=False, late=False, result=None, tips=[])

    # ---------------------------------------------------------------- data
    def data(self, c: dict) -> dict:
        d = kit.data(c)
        for k, v in initial().items():
            d.setdefault(k, copy.deepcopy(v))
        for k, v in kit.desk_initial().items():
            d['desk'].setdefault(k, copy.deepcopy(v))
        for k, v in day_stats().items():
            d['day_stats'].setdefault(k, v)
        office.ensure(d)
        care_ensure(d, self.cfg['care'])
        return d

    def initial(self) -> dict:
        d = initial()
        care_ensure(d, self.cfg['care'])
        return d

    # ---------------------------------------------------------------- commands
    def handle(self, s: dict, c: dict, name: str, p: dict) -> dict:
        d = self.data(c)
        o = d['office']
        office.sync(o, c['day'])
        before = o['clock']
        res = care_handle(s, c, d, o, self.cfg['care'], name, p, self.can_cover)
        if res is None:
            res = self._handle(s, c, d, o, name, p)
        slow = care_slow(d['care'], o, before)
        if slow:
            res['message'] = ' '.join(x for x in (res.get('message', ''), slow) if x)
        return res

    def _handle(self, s: dict, c: dict, d: dict, o: dict, name: str, p: dict) -> dict:
        P = self.p
        mod = self.mod(c['day'])
        if name == P + 'desk':
            return kit.desk_choose(s, c, self.id, d['desk'], self.cfg['desk'], p.get('option'), hook=self._desk_hook(o))
        if name == P + 'overtime':
            care_can_overtime(d['care'], self.cfg['care'])
            kit.confirm(p, 'Xác nhận ở lại tăng ca.')
            crunch = mod['id'] == self.cfg.get('crunch')
            return dict(message=office.overtime(s, c, o, 18 if crunch else 12, crunch))
        kit.desk_block(d['desk'], 'Có chuyện cần bạn quyết trước — xử lý xong rồi làm tiếp nhé.')
        t = kit.task(c, p)
        kit.need(t['career'] == self.id, 'Hồ sơ không thuộc bàn này.')
        kit.need(t['known'], 'Nhận hồ sơ và đọc yêu cầu trước (bấm “Hỏi”).')
        kit.need(t['status'] not in DONE and not t['filed'], 'Hồ sơ này đã xong.')
        office.need_open(o)
        if name in (P + 'put', P + 'mark', P + 'place', P + 'read'):
            act = name[len(P):]
            msg = dict(put=put, mark=mark, place=place, read=read)[act](t, p)
            lunch = office.spend(o, COST[act])
            kit.start_work(t)
            news = maybe_fire(t)
            return dict(message=' '.join(x for x in (news or msg, lunch) if x), twist=bool(news), surprise=bool(news))
        if name == P + 'hint':
            kit.need(len(t['tips']) < HINT_MAX, f'Mỗi hồ sơ chỉ hỏi tối đa {HINT_MAX} lần.')
            lunch = office.spend(o, COST['hint'])
            tip = hint_text(t)
            t['tips'].append(tip[:300])
            d['day_stats']['hints'] += 1
            return dict(message=' '.join(x for x in (f'💡 {self.helper(c)}: {tip}', lunch) if x))
        if name == P + 'reply':
            kit.confirm(p, 'Xác nhận cách trả lời.')
            choose(t, p)
            lunch = office.spend(o, COST['reply'] + office.review_cost(o))
            kit.start_work(t)
            res = self.finish(s, c, d, o, t)
            kit.desk_tick(s, c, self.id, d['desk'], self.cfg['desk'], mod['id'])
            res['message'] = ' '.join(x for x in (res['message'], lunch) if x)
            return res
        if name == P + 'file':
            kit.confirm(p, 'Xác nhận nộp hồ sơ.')
            kind = t['work']['type']
            kit.need(kind != 'case', 'Hồ sơ trao đổi: chọn cách trả lời để khép lại.')
            if kind == 'fields':
                take_fields(t, p)
            elif kind == 'seq':
                take_order(t, p)
            miss = ready(t)
            kit.need(not miss, miss)
            kit.start_work(t)
            news = maybe_fire(t, at_file=True)
            if news:
                lunch = office.spend(o, COST['twist'])
                return dict(message=' '.join(x for x in (news, 'Xem lại hồ sơ rồi hãy nộp.', lunch) if x), twist=True, surprise=True)
            n = len(t['work']['fields']) if kind == 'fields' else len(t['ans'].get('order', [])) if kind == 'seq' else 0
            lunch = office.spend(o, COST['file'] + COST['per_field'] * n + office.review_cost(o))
            res = self.finish(s, c, d, o, t)
            kit.desk_tick(s, c, self.id, d['desk'], self.cfg['desk'], mod['id'])
            res['message'] = ' '.join(x for x in (res['message'], lunch) if x)
            return res
        raise kit.eng().GameError('Thao tác văn phòng không hợp lệ.')

    def helper(self, c: dict) -> str:
        names = self.cfg.get('helpers') or (self.cfg['boss'],)
        return names[c['day'] % len(names)]

    def finish(self, s: dict, c: dict, d: dict, o: dict, t: dict) -> dict:
        """Grade, record the mistakes, settle the deadline, pay through the boss's reaction, complete."""
        res = grade(t)
        t['result'] = res
        t['filed'] = True
        note = NOTES[t['work']['type']]
        for e in res['errors']:
            cq.slip(t, f'{e["code"]}:{e["ref"] or ""}'[:32], e['sev'], e['text'], note)
        heavy = sum(1 for e in res['errors'] if e['sev'] >= 2)
        t['mistakes'] += len(res['errors'])
        office.trust(o, 1 if not res['errors'] else -min(4, heavy + (1 if len(res['errors']) > 2 else 0)))
        late, adj, due_note = office.settle(o, t, c['day'])
        t['late'] = late
        st = d['day_stats']
        if st['day'] != c['day']:
            d['day_stats'] = st = day_stats(c['day'])
        st['filed'] += 1
        st['late'] += int(late)
        st['errors'] += len(res['errors'])
        st['heavy'] += sum(1 for e in res['errors'] if e['sev'] >= 3)
        st['clean'] += int(not res['errors'])
        d['filed'] += 1
        d['late'] += int(late)
        d['clean'] += int(not res['errors'])
        d['log'] = ar.last(d['log'] + [dict(day=c['day'], title=t['title'][:120], late=late, errors=len(res['errors']))], LOG, 'office.log', c)
        # Each wrong card or cell costs a little of the bonus; the boss's reaction can cut what is left.
        price = max(0, t['bonus'] - 3 * len(res['errors']) - 3 * heavy + adj - HINT_CUT * len(t['tips']))
        reaction = cq.react(s, c, t, price, who=self.cfg['boss'])
        reward = reaction['pay']
        kit.metric(c, self.p + 'filed')
        if not res['errors']:
            kit.metric(c, self.p + 'clean')
        kit.complete(s, c, t, reward, f'Bạn đã nộp “{t["title"]}”' + (' nhưng trễ hạn.' if late else '.'))
        head = f'📤 Đã nộp · {res["ok"]}/{res["total"]} đúng · thưởng +{reward} xu.'
        if res['errors']:
            head += f' Sai {len(res["errors"])} chỗ — xem lại bên dưới.'
        return dict(message=' '.join(x for x in (head, due_note, reaction.get('message', '')) if x),
                    celebrate=not late and not res['errors'], correct=not res['errors'])

    def _desk_hook(self, o: dict):
        def hook(s: dict, c: dict, key: str, v) -> str | None:
            if key == 'trust':
                n = office.trust(o, int(v))
                return f'({self.cfg["boss"]}: {"+" if n >= 0 else ""}{n} tin tưởng)' if n else None
            if key == 'time':
                if o['clock'] >= office.limit(o):
                    return None
                return office.spend(o, int(v)) or None
            return None
        return hook

    # ---------------------------------------------------------------- review & helpers
    def feedback(self, c: dict, t: dict) -> dict:
        res = t.get('result') or grade(t)
        n = len(res['errors'])
        worst = max((e['sev'] for e in res['errors']), default=0)
        tips = len(t.get('tips') or [])
        if t['late']:
            speed, sn = 1, 'trễ hạn'
        elif type(t.get('due')) is int:
            speed, sn = 5, 'kịp hạn ' + office.hhmm(t['due'])
        else:
            speed, sn = 4, 'nộp trong ngày'
        return dict(criteria=[
            dict(key='accuracy', label='Chính xác', score=5 if not n else 4 if n == 1 else 3 if n <= 3 else 2,
                 note=f'{res["ok"]}/{res["total"]} đúng' if n else 'không sai chỗ nào'),
            dict(key='quality', label='Tự xử lý', score=5 if not tips else 4 if tips == 1 else 3,
                 note='không phải hỏi ai' if not tips else f'hỏi {tips} lần'),
            dict(key='care', label='Đúng nguyên tắc', score=5 if worst < 3 else 2,
                 note='giữ đúng quy định' if worst < 3 else 'có lỗi làm hại người khác hoặc sai quy định'),
            dict(key='speed', label='Đúng hạn', score=speed, note=sn)])

    def known_request(self, c: dict, t: dict) -> str:
        return t['brief']

    def hint(self, c: dict, t: dict) -> str:
        if not t['known']:
            return 'Nhận hồ sơ, đọc yêu cầu và giấy tờ đính kèm trước.'
        return self.cfg['hints'].get(t['form'], '')

    def assist(self, s: dict, c: dict, e: dict, t: dict | None) -> str | None:
        if not t or t.get('career') != self.id or not t.get('known') or t.get('filed'):
            return None
        if t['form'] in self.cfg.get('staff_area', {}).get(e.get('role'), ()):
            return f'{e.get("name", "Đồng nghiệp")} ghé bàn nhắc: {hint_text(t)}'
        return None

    def can_cover(self, t: dict, day: int) -> str:
        return ''

    def reliable(self, d: dict, o: dict, day: int) -> tuple[bool, str]:
        st = d['day_stats']
        if st['day'] != day or not st['filed']:
            return False, 'Chưa nộp hồ sơ nào'
        if o['day_late']:
            return False, f'{o["day_late"]} hồ sơ trễ hạn'
        if st['heavy']:
            return False, 'Có hồ sơ sai nặng'
        return True, f'{st["filed"]} hồ sơ kịp hạn' + (f', {st["clean"]} hồ sơ không sai chỗ nào' if st['clean'] else '')

    # ---------------------------------------------------------------- day hooks
    def on_task(self, s: dict, c: dict, t: dict) -> None:
        o = self.data(c)['office']
        office.sync(o, c['day'])
        office.set_due(c, t, o)
        if self.mod(t['day'])['id'] == self.cfg.get('crunch'):
            t['due'] = max(office.OPEN + 60, t['due'] - 30)

    def on_start(self, s: dict, c: dict) -> None:
        d = self.data(c)
        o = d['office']
        mod = self.mod(c['day'])
        office.begin(o, c['day'])
        office.carry(c, self.id, o)
        d['day_stats'] = day_stats(c['day'])
        care_start(d['care'], self.cfg['care'], c['day'])
        kit.desk_start(s, c, self.id, d['desk'], self.cfg['desk'], mod['id'])
        office.note(o, c['day'], f'{mod["emoji"]} {mod["name"]}: {mod["text"]}', 'day')

    def on_close(self, s: dict, c: dict) -> dict:
        d = self.data(c)
        o = d['office']
        office.sync(o, c['day'])
        mod = self.mod(c['day'])
        st = d['day_stats'] if d['day_stats']['day'] == c['day'] else day_stats(c['day'])
        out = dict(mod=dict(emoji=mod['emoji'], name=mod['name']), filed=st['filed'], clean=st['clean'], errors=st['errors'])
        desk_note = kit.desk_close(s, c, self.id, d['desk'], self.cfg['desk'], hook=self._desk_hook(o))
        if desk_note:
            out['desk'] = desk_note
        if mod['id'] == self.cfg.get('audit') and st['filed']:
            who = self.cfg['auditor']
            if st['heavy'] or st['errors'] > st['filed']:
                paid = office.fine(s, c, o, AUDIT_PAY, f'{who} soát hồ sơ: còn lỗi')
                office.trust(o, -3)
                out['inspect'] = dict(ok=False, amount=paid, text=f'{who} soát hồ sơ hôm nay, thấy {st["errors"]} chỗ sai. Trừ {paid} xu.')
            else:
                kit.money(s, c, AUDIT_PAY, f'Thưởng: {who} soát hồ sơ không thấy lỗi nặng', None, 'audit_bonus')
                office.trust(o, 3)
                out['inspect'] = dict(ok=True, amount=AUDIT_PAY, text=f'{who} soát hồ sơ hôm nay: gọn gàng, đúng quy định. Thưởng {AUDIT_PAY} xu.')
        ok, why = self.reliable(d, o, c['day'])
        out['office'] = office.close_day(c, self.id, o)
        out['care'] = care_close(s, c, d['care'], self.cfg['care'], o, ok, why)
        return out

    # ---------------------------------------------------------------- views & saves
    def public_task(self, t: dict) -> dict:
        return public_task(t)

    def public_data(self, c: dict) -> dict:
        raw = tree_copy(kit.data(c))
        for k, v in initial().items():
            raw.setdefault(k, tree_copy(v))
        for k, v in kit.desk_initial().items():
            raw['desk'].setdefault(k, tree_copy(v))
        o = office.ensure(raw)
        cr = care_ensure(raw, self.cfg['care'])
        mod = self.mod(c['day'])
        st = raw['day_stats'] if raw['day_stats'].get('day') == c['day'] else day_stats(c['day'])
        return dict(filed=raw['filed'], late=raw['late'], clean=raw['clean'], log=raw['log'], day_stats=st,
                    today=dict(mod=dict(id=mod['id'], emoji=mod['emoji'], name=mod['name'], text=mod['text']), rules=self.cfg['rules'](c['day'])),
                    office=office.public(o, c['day']), care=care_public(cr, self.cfg['care'], c, o, self.can_cover),
                    desk=kit.desk_public(raw['desk'], self.cfg['desk'], self.id), coach={},
                    boss=dict(name=self.cfg['boss'], npc=kit.npc_id(self.id, self.cfg['boss_npc'])))

    def validate_task(self, t: dict, original: dict) -> None:
        care_validate_task(t, self.cfg['care'])
        validate_task(t)

    def validate_data(self, c: dict) -> None:
        d = self.data(c)
        validate_data(d)
        care_validate(d['care'], self.cfg['care'])
        kit.desk_validate(d['desk'], self.cfg['desk'])

    def content(self) -> dict:
        return dict(forms=[dict(id=f['id'], label=f['label'], bonus=f['bonus'], min_day=f['min_day']) for f in self.cfg['forms']],
                    boss=dict(name=self.cfg['boss'], npc=kit.npc_id(self.id, self.cfg['boss_npc'])), hint_max=HINT_MAX, hint_cut=HINT_CUT,
                    helpers=list(self.cfg.get('helpers') or (self.cfg['boss'],)), cost=dict(COST))

    def bind(self, ns: dict) -> None:
        """Expose the hooks as module-level functions of the career module."""
        for name in ('make_task', 'handle', 'feedback', 'known_request', 'public_task', 'validate_task', 'validate_data', 'public_data',
                     'on_task', 'on_start', 'on_close', 'assist', 'hint', 'content', 'initial'):
            ns[name] = getattr(self, name)
        ns['FIXED'] = FIXED
