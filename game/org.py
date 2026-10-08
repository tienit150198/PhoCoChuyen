"""Chức vụ & cấp bậc: one reusable org ladder (owner spec 06/10), police first. Content: game/org_content.py.

Rank (cấp bậc hàm) and post (chức vụ) are two separate tracks:
* the grade rises at the day's close with worked days in the grade, the ★ of the last days and no open warning, up to
  the post's ceiling; a grade may first ask for a course (a two-question exam the next morning) or a clean record;
* the post changes only by appointment: the target post's grade (or one below it: promoted on appointment), days in
  the current post, ★, no open warning, a vacancy (seeded; at most one wait of 3 worked days) and an interview of two
  questions the next morning. A transfer never lowers the grade.

Warnings (shared by every ranked career): a procedure violation the career detects is a ⚠️ cảnh cáo (`violation`).
The 4th demotes one grade and resets the count; 10 worked days in a row without a violation clear them all (the
discipline is served: player feedback #251/#253/#258, 07/10), and an end-of-period "Hoàn thành xuất sắc nhiệm vụ"
clears one. At the entry grade the 4th is a 3-day tạm đình chỉ (no salary). An accepted
bribe (`bribe`) demotes one grade at once and writes a permanent integrity mark (it bars Trợ lý BGĐ, PGĐ and Đại tá
for good); owning up in the same shift (`own`) turns the demotion into a normal warning, the mark stays. A grade
below the post's own drops the player to the highest post the new grade allows (the NPC who takes the seat is named).
The management office (game/promotion_office.py, key OFFICE[org]) opens from the posts with an office level; it
acts on NPC subordinates only. The Trợ lý BGĐ's office is the kiểm tra điều lệnh (inspection) workflow below.

State: journey['promo'][career]['org'] (optional; builds without it ignore the record's extra keys and keep the plain
step in record['rank'], which this module keeps in step with the post for them, never above 4). Existing players are
put on the ladder lazily from their step (never lower, the pay never below today's). Everything random is rolled
from (seed, career, day, …).
"""
from __future__ import annotations

import random

from . import org_content as OC

V = 1
ST_MAX = 10       # day stars kept (the evaluation window)
WLOG_MAX = 20
HIST_MAX = 20
EVALS_MAX = 6
VT_MAX = 24
RETRY = 3
VAC_WAIT = 3
LIEM_MAX = 999
KEYS = frozenset(('v', 'org', 'g', 'p', 'tig', 'tip', 'st', 'warns', 'wlog', 'clean', 'mark', 'liem', 'evals', 'evn', 'hist',
                  'courses', 'due', 'wait', 'vac', 'aim', 'susp', 'floor', 'bt', 'adj', 'vt', 'office', 'insp'))


def _rng(*parts) -> random.Random:
    return random.Random('|'.join(map(str, parts)))


# ------------------------------------------------------------------------------------- content lookups
def org_of(career: str) -> dict | None:
    x = OC.CAREER_ORG.get(career)
    return OC.ORGS[x[0]] if x else None


def org_id(career: str) -> str | None:
    x = OC.CAREER_ORG.get(career)
    return x[0] if x else None


def _gi(o: dict, gid: str) -> int:
    return next(i for i, g in enumerate(o['grades']) if g['id'] == gid)


def _post(o: dict, pid: str) -> dict:
    return next(p for p in o['posts'] if p['id'] == pid)


def _pi(o: dict, pid: str) -> int:
    return next(i for i, p in enumerate(o['posts']) if p['id'] == pid)


def wears(career: str, c: dict) -> bool:
    """This contract is on the org ladder (the career has one and the posting wears it)."""
    x = OC.CAREER_ORG.get(career)
    job = c.get('job') or {}
    return bool(x) and job.get('status') == 'hired' and job.get('employer') in x[1]


def get(rec: dict | None) -> dict | None:
    o = rec.get('org') if isinstance(rec, dict) else None
    return o if isinstance(o, dict) else None


def active(career: str, c: dict, rec: dict | None) -> dict | None:
    """The record's org block when it applies to this contract now."""
    o = get(rec)
    return o if o is not None and wears(career, c) and o.get('org') == org_id(career) else None


# ------------------------------------------------------------------------------------- creation and migration
def new(oid: str, post: str, grade: str, floor: int = 0, keep: dict | None = None) -> dict:
    o = OC.ORGS[oid]
    x = dict(v=V, org=oid, g=_gi(o, grade), p=post, tig=0, tip=0, st=[], warns=[], wlog=[], clean=0, mark=dict(b=None, s=False),
             liem=0, evals=[], evn=0, hist=[], courses=[], due=None, wait=0, vac=None, aim=None, susp=0, floor=max(0, min(100, floor)),
             bt=None, adj=0, vt=dict(d=0, k=[]), office=None, insp=None)
    if keep:   # a new contract: the integrity mark and Liêm chính are a person's, not a contract's
        x['mark'] = dict(keep.get('mark') or x['mark'])
        x['liem'] = int(keep.get('liem') or 0)
        x['wlog'] = list(keep.get('wlog') or [])[-WLOG_MAX:]
    return x


def ensure(s: dict, c: dict, career: str, rec: dict | None, step: int = -1, pct: int = 0) -> dict | None:
    """Put the contract on the ladder (lazy migration): a fresh hire (step -1) at the entry post and grade; an existing
    player from their step 0..4 (never lower; the pay kept at least at today's raise `pct`)."""
    if rec is None or not wears(career, c):
        return None
    cur = get(rec)
    oid = org_id(career)
    if cur is not None and cur.get('org') == oid:
        return cur
    o = OC.ORGS[oid]
    if step < 0:   # a new hire
        post, grade = o['start']
    else:
        post, grade = o['migrate'][max(0, min(len(o['migrate']) - 1, step))]
    rec['org'] = new(oid, post, grade, pct, keep=cur)
    rec['due'] = None   # an older build's review of the plain step: the ladder takes over
    return rec['org']


# ------------------------------------------------------------------------------------- reading
def grade(x: dict) -> dict:
    return OC.ORGS[x['org']]['grades'][x['g']]


def post(x: dict) -> dict:
    return _post(OC.ORGS[x['org']], x['p'])


def title(x: dict) -> str:
    return f'{grade(x)["name"]} · {post(x)["short"]}'


def stars(x: dict) -> int | None:
    rows = x['st'][-ST_MAX:]
    return round(sum(rows) / len(rows)) if rows else None


def raise_pct(x: dict) -> int:
    """% on the contract salary: grade coefficient / reference × (1 + the post's bonus), never below the floor."""
    o = OC.ORGS[x['org']]
    coef = grade(x)['coef'] or o['grades'][-2]['coef']
    pct = round(100 * coef / o['pay_ref'] * (100 + post(x)['bonus']) / 100) - 100
    return max(x['floor'], pct, 0)


def step(x: dict) -> int:
    return OC.ORGS[x['org']]['step'][x['p']]


def suspended(x: dict | None) -> bool:
    return bool(x) and x['susp'] > 0


def barred(x: dict, what: str) -> bool:
    return x['mark']['b'] is not None and what in OC.ORGS[x['org']]['bar_on_mark']


def _good_evals(x: dict) -> int:
    return sum(1 for e in x['evals'] if e['g'] in ('tot', 'xs'))


def _log(x: dict, d: int, k: str, code: str) -> None:
    x['wlog'] = (x['wlog'] + [dict(d=d, k=k, c=code)])[-WLOG_MAX:]


def _hist(x: dict, d: int, k: str, fr: str, to: str, why: str) -> None:
    x['hist'] = (x['hist'] + [dict(d=d, k=k, fr=fr, to=to, why=why)])[-HIST_MAX:]


def _day(s: dict) -> int:
    return int((s.get('journey') or {}).get('life_day') or 1)


def _seed(s: dict) -> int:
    return int((s.get('journey') or {}).get('seed') or 0)


# ------------------------------------------------------------------------------------- grade rows (what the next needs)
def clean_row(x: dict) -> dict:
    """No open warning; while there is one, how far the 10 days without a violation that clear them are."""
    if not x['warns']:
        return dict(id='clean', met=True, label='Không còn cảnh cáo')
    n = OC.ORGS[x['org']]['decay_days']
    return dict(id='clean', met=False, label=f'Xóa cảnh cáo: {min(x["clean"], n)}/{n} ngày làm không vi phạm')


def waits(x: dict) -> list[dict]:
    """What holds the next step back besides its requirements (for the screens only, never a requirement itself):
    a suspension, a retry after a failed interview, the seat of the next post not free yet."""
    rows = []
    if x['susp'] > 0:
        rows.append(dict(id='susp', met=False, label=f'Hết tạm đình chỉ: còn {x["susp"]} ngày'))
    if next_grade(x) is None and target(x):
        if x['wait'] > 0:
            rows.append(dict(id='wait', met=False, label=f'Hẹn xét lại sau {x["wait"]} ngày làm'))
        if x['vac']:
            rows.append(dict(id='seat', met=False, label=f'Chờ ghế {_post(OC.ORGS[x["org"]], target(x))["short"]} trống: {x["vac"]} ngày làm nữa'))
    return rows


_BREAK = ('warn', 'demote', 'susp', 'bribe', 'own')   # wlog kinds that end a run of days without a violation


def streak(x: dict) -> int:
    """Worked days in a row without a violation. Builds up to 1.9.19 cleared one warning per 10 such days and started
    the count again each time: every 'expire' logged since the last violation stands for those 10 days."""
    n = x['clean']
    for w in reversed(x['wlog']):
        if w['k'] in _BREAK:
            break
        if w['k'] == 'expire':
            n += OC.ORGS[x['org']]['decay_days']
    return n


def heal(x: dict | None, d: int) -> str:
    """Warnings whose discipline is served (10 days in a row without a violation) are cleared; also run on load, so a
    save from a build that kept them longer recovers at once. '' when nothing changes."""
    if not x or not x['warns']:
        return ''
    o = OC.ORGS[x['org']]
    run = streak(x)
    if run < o['decay_days']:
        return ''
    x['warns'] = []
    x['clean'] = min(999, run)
    _log(x, d, 'expire', 'clean')
    return f'🧽 {o["decay_days"]} ngày làm không vi phạm: xóa hết cảnh cáo.'


def _gate_rows(x: dict, gi: int) -> list[dict]:
    """What the step from grade gi to gi+1 asks beyond days and ★ (a course, a clean record, the mark)."""
    o = OC.ORGS[x['org']]
    gate = o['grades'][gi]['gate']
    nxt = o['grades'][gi + 1] if gi + 1 < len(o['grades']) else None
    rows = []
    if gate and gate.startswith('course:'):
        cid = gate.split(':', 1)[1]
        rows.append(dict(id='course', met=cid in x['courses'], label=o['courses'][cid], course=cid))
    if gate == 'clean' or (nxt and barred_grade(o, nxt['id'])):
        rows.append(dict(id='mark', met=x['mark']['b'] is None, label='Chưa từng có dấu liêm chính'))
    return rows


def barred_grade(o: dict, gid: str) -> bool:
    return gid in o['bar_on_mark']


def next_grade(x: dict) -> dict | None:
    """The next grade and its requirements (None at the post's ceiling: an appointment opens the way)."""
    o = OC.ORGS[x['org']]
    g, p = x['g'], post(x)
    hi = _gi(o, p['hi'])
    if g >= hi or o['grades'][g]['days'] is None:
        return None
    gr = o['grades'][g]
    st = stars(x)
    rows = [dict(id='days', met=x['tig'] >= gr['days'], label=f'{min(x["tig"], gr["days"])}/{gr["days"]} ngày làm ở cấp này'),
            dict(id='stars', met=st is not None and st >= gr['need'], label=f'★ {gr["need"] / 10:.1f} ({(st or 0) / 10:.1f} hiện tại)'),
            clean_row(x)]
    rows += _gate_rows(x, g)
    nxt = o['grades'][g + 1]
    return dict(id=nxt['id'], name=nxt['name'], ins=nxt['ins'], rows=rows, good=min(x['tig'], gr['days']), need=gr['days'])


def _aims(x: dict) -> list[str]:
    o = OC.ORGS[x['org']]
    return [pid for pid in o['next'].get(x['p'], ()) if not barred(x, pid)]


def target(x: dict) -> str | None:
    aims = _aims(x)
    if not aims:
        return None
    return x['aim'] if x['aim'] in aims else aims[0]


def post_rows(x: dict, pid: str) -> list[dict]:
    o = OC.ORGS[x['org']]
    tp, cur = _post(o, pid), post(x)
    lo = _gi(o, tp['lo'])
    st = stars(x)
    rows = [dict(id='grade', met=x['g'] >= lo - 1, label=f'Từ {o["grades"][max(0, lo - 1)]["name"]} trở lên'),
            dict(id='days', met=x['tip'] >= cur['days'], label=f'{min(x["tip"], cur["days"])}/{cur["days"]} ngày ở chức vụ này'),
            dict(id='stars', met=st is not None and st >= tp['need'], label=f'★ {tp["need"] / 10:.1f} ({(st or 0) / 10:.1f} hiện tại)'),
            clean_row(x)]
    if tp['extra'].get('good_evals'):
        n = tp['extra']['good_evals']
        rows.append(dict(id='evals', met=_good_evals(x) >= n, label=f'{min(_good_evals(x), n)}/{n} kỳ “Hoàn thành tốt” trở lên'))
    if tp['extra'].get('nomark'):
        rows.append(dict(id='mark', met=x['mark']['b'] is None, label='Chưa từng có dấu liêm chính'))
    if x['g'] < lo:   # promoted on appointment: that step's own gate too
        rows += [r for r in _gate_rows(x, x['g']) if r['id'] != 'mark' or not tp['extra'].get('nomark')]
    return rows


# ------------------------------------------------------------------------------------- discipline
def _today(x: dict, day: int) -> list:
    if x['vt']['d'] != day:
        x['vt'] = dict(d=day, k=[])
    return x['vt']['k']


def _demote(x: dict, d: int, why: str) -> str:
    """One grade down (or a suspension at the entry grade); a grade below the post's own steps the post down."""
    o = OC.ORGS[x['org']]
    if x['g'] <= 0:
        x['susp'] = o['susp_days']
        _log(x, d, 'susp', why)
        return f'⛔ Tạm đình chỉ công tác {o["susp_days"]} ngày: không có lương. Đã ở cấp thấp nhất.'
    before = grade(x)['name']
    x['g'] -= 1
    x['tig'] = 0
    _hist(x, d, 'g', o['grades'][x['g'] + 1]['id'], o['grades'][x['g']]['id'], why)
    _log(x, d, 'demote', why)
    line = f'⬇️ Hạ 1 bậc hàm: {before} → {grade(x)["name"]}.'
    p = post(x)
    if x['g'] < _gi(o, p['lo']):
        line += ' ' + _step_down(x, d, why)
    return line


def _step_down(x: dict, d: int, why: str) -> str:
    o = OC.ORGS[x['org']]
    here = _pi(o, x['p'])
    cands = [i for i, p in enumerate(o['posts'][:here]) if _gi(o, p['lo']) <= x['g'] and p['chain'] != 'aide' and not barred(x, p['id'])]
    i = max(cands) if cands else 0
    old = post(x)
    new_p = o['posts'][i]
    x['p'], x['tip'], x['aim'], x['due'], x['vac'] = new_p['id'], 0, None, None, None   # the seat waited for is another post's
    _hist(x, d, 'p', old['id'], new_p['id'], why)
    who = OC.SEAT_NPC[_rng('seat', d, old['id']).randrange(len(OC.SEAT_NPC))]
    return f'Chức vụ: {old["short"]} → {new_p["short"]}. {who} nhận ghế {old["short"]}.'


def violation(x: dict | None, s: dict, c: dict, code: str, key: str, grace: bool = False) -> str:
    """A procedure violation the career detected: a ⚠️ cảnh cáo (once per key a day). `grace`: on probation or while a
    tutor stands beside the player, it is a reminder only."""
    if x is None or code not in OC.VIOLATIONS:
        return ''
    seen = _today(x, c['day'])
    key = ('g:' if grace else '') + key
    if key in seen:
        return ''
    if len(seen) < VT_MAX:
        seen.append(key)
    why, how = OC.VIOLATIONS[code]
    if grace:
        return f'📖 Nhắc quy trình: {why.lower()}. {how} (Đang kèm việc: chưa tính cảnh cáo.)'
    return _warn(x, s, c, code)


def _warn(x: dict, s: dict, c: dict, code: str) -> str:
    o = OC.ORGS[x['org']]
    d = _day(s)
    x['warns'] = (x['warns'] + [dict(d=d, c=code)])[-o['demote_on']:]
    x['clean'] = 0
    x['adj'] = max(-50, x['adj'] - 3)
    _log(x, d, 'warn', code)
    why, how = OC.VIOLATIONS[code]
    n = len(x['warns'])
    if n >= o['demote_on']:
        x['warns'] = []
        return f'⚠️ Cảnh cáo lần {n}: {why.lower()}. ' + _demote(x, d, 'warn4') + f' 📖 {how}'
    return f'⚠️ Cảnh cáo {n}/{o["warn_max"]}: {why.lower()}. 📖 {how}'


def bribe(x: dict | None, s: dict, c: dict, key: str) -> str:
    """An accepted bribe: one grade down at once (the warnings are kept), the envelope confiscated, a permanent mark."""
    if x is None:
        return ''
    seen = _today(x, c['day'])
    if key in seen:
        return ''
    if len(seen) < VT_MAX:
        seen.append(key)
    d = _day(s)
    x['bt'] = dict(d=c['day'], g=x['g'], p=x['p'], s=x['susp'])
    x['mark'] = dict(b=d, s=False)
    x['clean'] = 0
    x['adj'] = max(-50, x['adj'] - 10)
    _log(x, d, 'bribe', 'bribe')
    line = _demote(x, d, 'bribe')
    return f'💵 Nhận phong bì: phong bì bị tịch thu. {line} Ghi dấu liêm chính vĩnh viễn. Tự giác nộp lại trong ca thì chỉ tính cảnh cáo.'


def can_own(x: dict | None, c: dict) -> bool:
    return bool(x) and isinstance(x['bt'], dict) and x['bt']['d'] == c['day']


def own(x: dict, s: dict, c: dict) -> str:
    """Owning up the same shift: the demotion is undone and becomes a normal warning; the mark stays (đã tự giác)."""
    bt = x['bt']
    if x['g'] < bt['g']:
        x['g'] = bt['g']
        x['p'] = bt['p']
    x['susp'] = bt['s']
    x['bt'] = None
    x['mark']['s'] = True
    _log(x, _day(s), 'own', 'bribe_owned')
    return '🙇 Tự giác nộp lại phong bì, báo cáo. Giữ bậc hàm, ' + _warn(x, s, c, 'bribe_owned') + ' Dấu liêm chính vẫn ghi “đã tự giác”.'


def report(x: dict | None) -> str:
    """Refusing and reporting a bribe: +1 Liêm chính and +0.2 ★ for the day."""
    if x is None:
        return ''
    x['liem'] = min(LIEM_MAX, x['liem'] + 1)
    x['adj'] = min(10, x['adj'] + 2)
    return f'🛡️ Liêm chính +1 (tổng {x["liem"]}).'


# ------------------------------------------------------------------------------------- the day's close
def close(x: dict, s: dict, c: dict, career: str, worked: bool, good: bool, day_stars: float | None) -> list[str]:
    """end_day: suspension, the day's ★, decay, the evaluation, a grade step, and the next morning's appointment or course."""
    o = OC.ORGS[x['org']]
    d = _day(s)
    lines = []
    x['bt'] = None
    viol = bool(x['vt']['k']) and x['vt']['d'] == c['day'] and any(not k.startswith('g:') for k in x['vt']['k'])
    if x['susp'] > 0:
        x['susp'] -= 1
        lines.append(f'⛔ Đang tạm đình chỉ: còn {x["susp"]} ngày.' if x['susp'] else '✅ Hết tạm đình chỉ từ ca sau.')
    if not worked:
        x['adj'] = 0
        return lines
    base = round(day_stars * 10) if day_stars is not None else (42 if good else 32)
    x['st'] = (x['st'] + [max(10, min(50, base + x['adj']))])[-ST_MAX:]
    x['adj'] = 0
    x['tig'] = min(10**6, x['tig'] + 1)
    x['tip'] = min(10**6, x['tip'] + 1)
    if x['wait'] > 0:
        x['wait'] -= 1
    # The discipline served: N worked days in a row without a violation clear every open warning.
    if viol:
        x['clean'] = 0
    else:
        x['clean'] = min(999, x['clean'] + 1)
        line = heal(x, d)
        if line:
            lines.append(line)
    if x['warns']:   # how far the clearing is (a violation today starts it again)
        lines.append(f'🧽 Xóa cảnh cáo: {x["clean"]}/{o["decay_days"]} ngày làm không vi phạm.')
    # The end-of-period evaluation.
    x['evn'] = min(999, x['evn'] + 1)
    if x['evn'] >= o['eval_window']:
        x['evn'] = 0
        st = stars(x) or 0
        gid, label = next((k, lab) for lo, k, lab in o['evals'] if st >= lo)
        x['evals'] = (x['evals'] + [dict(d=d, g=gid)])[-EVALS_MAX:]
        lines.append(f'📋 Đánh giá kỳ: {label} (★ {st / 10:.1f}).')
        if gid == 'xs' and x['warns']:
            x['warns'].pop(0)
            _log(x, d, 'clear', 'xs')
            lines.append('🧽 Xuất sắc: xóa 1 cảnh cáo.')
    if x['susp'] > 0 or x['due'] is not None:
        return lines
    # A grade step inside the post.
    ng = next_grade(x)
    if ng and all(r['met'] for r in ng['rows']):
        before = grade(x)['name']
        x['g'] += 1
        x['tig'] = 0
        _hist(x, d, 'g', o['grades'][x['g'] - 1]['id'], grade(x)['id'], 'time')
        lines.append(f'⭐ Quyết định thăng cấp bậc hàm: {before} → {grade(x)["name"]}.')
        return lines
    if ng and all(r['met'] for r in ng['rows'] if r['id'] != 'course'):
        course = next(r for r in ng['rows'] if r['id'] == 'course')
        _book(x, s, c, 'course', course['course'])
        lines.append(f'{course["label"]}: bài kiểm tra cuối khóa đầu ca sau.')
        return lines
    # An appointment.
    tp = target(x)
    if tp and x['wait'] == 0:
        rows = post_rows(x, tp)
        if all(r['met'] for r in rows if r['id'] != 'course'):
            course = next((r for r in rows if r['id'] == 'course' and not r['met']), None)
            if course:
                _book(x, s, c, 'course', course['course'])
                lines.append(f'{course["label"]}: bài kiểm tra cuối khóa đầu ca sau.')
                return lines
            if x['vac'] is None:
                x['vac'] = 0 if _rng('vac', _seed(s), career, tp, c['day']).random() < .5 else VAC_WAIT
            elif x['vac'] > 0:
                x['vac'] -= 1
            if x['vac'] > 0:
                lines.append(f'🪑 Chờ ghế {_post(o, tp)["short"]} trống: {x["vac"]} ngày làm nữa.')
                return lines
            _book(x, s, c, 'post', tp)
            lines.append(f'🎖️ Ban chỉ huy hẹn đầu ca sau: xét bổ nhiệm {_post(o, tp)["short"]}.')
    return lines


def _book(x: dict, s: dict, c: dict, kind: str, to: str) -> None:
    o = OC.ORGS[x['org']]
    bank = OC.QUESTIONS[o['questions']]
    r = _rng('org-qs', _seed(s), x['org'], kind, to, c['day'], len(x['hist']))
    x['due'] = dict(k=kind, to=to, day=c['day'] + 1, qs=[q['id'] for q in r.sample(bank, 2)], ans={})


# ------------------------------------------------------------------------------------- the morning: interview or exam
SCORE_WORD = {2: 'tốt nhất', 1: 'tạm được', 0: 'chưa đạt'}


def answer(x: dict, s: dict, c: dict, p: dict, need) -> dict:
    due = x['due']
    need(due, 'Chưa có buổi xét nào.')
    left = [q for q in due['qs'] if q not in due['ans']]
    need(left and p.get('question') == left[0], 'Câu hỏi không hợp lệ hoặc đã trả lời.')
    q = OC.QUESTION_INDEX[left[0]]
    opt = next((o for o in q['options'] if o['id'] == p.get('option')), None)
    need(opt, 'Câu trả lời không hợp lệ.')
    due['ans'][q['id']] = opt['id']
    if len(due['ans']) < len(due['qs']):
        return dict(message='Ghi nhận.', score=opt['score'])
    rows = []
    for qid in due['qs']:
        qq = OC.QUESTION_INDEX[qid]
        oo = next(o for o in qq['options'] if o['id'] == due['ans'][qid])
        rows.append(dict(q=qq['text'], a=oo['label'], score=oo['score'], word=SCORE_WORD[oo['score']]))
    o = OC.ORGS[x['org']]
    d = _day(s)
    x['due'] = None
    if min(r['score'] for r in rows) == 0:
        x['wait'] = RETRY
        bad = next(r for r in rows if r['score'] == 0)
        return dict(message=f'Chưa đạt. Câu “{bad["q"]}”: “{bad["a"]}”. Hẹn xét lại sau {RETRY} ngày làm.', later=True,
                    review=dict(why='zero', wait=RETRY, rows=rows))
    if due['k'] == 'course':
        x['courses'] = sorted(set(x['courses'] + [due['to']]))
        return dict(message=f'🎓 Đạt {o["courses"][due["to"]]}.', celebrate=True)
    tp = _post(o, due['to'])
    before = post(x)
    x['p'], x['tip'], x['vac'], x['aim'] = tp['id'], 0, None, None
    _hist(x, d, 'p', before['id'], tp['id'], 'appoint')
    line = f'🎉 Quyết định bổ nhiệm: {tp["name"]}.'
    lo = _gi(o, tp['lo'])
    if x['g'] < lo:
        g0 = grade(x)['name']
        x['g'], x['tig'] = lo, 0
        _hist(x, d, 'g', o['grades'][lo - 1]['id'], o['grades'][lo]['id'], 'appoint')
        line += f' Thăng cấp {g0} → {grade(x)["name"]}.'
    if tp['olv'] and not post_had_office(before):
        line += ' Mở 🏢 phòng chỉ huy từ ca sau.'
    return dict(message=line, celebrate=True, promoted=dict(title=title(x)))


def post_had_office(p: dict) -> bool:
    return bool(p.get('olv'))


def set_aim(x: dict, p: dict, need) -> dict:
    aims = _aims(x)
    need(p.get('post') in aims, 'Hướng này không mở với chức vụ hiện tại.')
    need(x['due'] is None, 'Đã có lịch xét rồi.')
    x['aim'] = p['post']
    x['vac'] = None
    return dict(message=f'🧭 Hướng tới: {_post(OC.ORGS[x["org"]], p["post"])["short"]}.')


# ------------------------------------------------------------------------------------- 🔎 kiểm tra điều lệnh (Trợ lý BGĐ)
UNITS = ('Tổ Tuần tra 1', 'Tổ Tuần tra 2', 'Tổ Trực ban', 'Đội 113', 'CA phường Mây', 'CA phường Sương', 'Phòng PC06')
MEMBERS = ('Hạ sĩ Lò Văn Tú', 'Trung sĩ Mai Hoa', 'Thiếu úy Trịnh Nam', 'Trung úy Bế Lan', 'Thượng úy Đào Phong', 'Hạ sĩ Tăng Ly',
           'Thượng sĩ Quách Bình', 'Thiếu úy Âu Diệp', 'Trung úy Kha Vĩnh', 'Đại úy Lục Thảo', 'Trung sĩ Hà Tín', 'Thượng úy Mạc Hưng')
ARTEFACTS = (('📒', 'Sổ trực ban'), ('📝', 'Biên bản'), ('🪪', 'Điều lệnh'))
FLAWS = (('Ghi lệch giờ so với nhật ký 113', 'Thiếu một tin báo trong sổ'),
         ('Thiếu chữ ký người vi phạm, không có người chứng kiến', 'Biên bản thiếu căn cứ; có phong bì kẹp trong hồ sơ'),
         ('Không đeo giấy chứng nhận khi làm nhiệm vụ', 'Camera ghi hình tắt cả ca'))
CLEAN_LINES = ('Khớp nhật ký 113, đủ việc', 'Đủ trường, có chữ ký, giao 1 bản', 'Quân phục, giấy chứng nhận, camera đủ')
INSP_GRADES = ('xs', 'tot', 'ht', 'kht')


def insp_today(x: dict, s: dict, c: dict) -> dict:
    """Today's inspection board (rolled once a day): 4 units offered, one with a hint "nhiều phản ánh"."""
    if isinstance(x.get('insp'), dict) and x['insp']['day'] == c['day']:
        return x['insp']
    r = _rng('insp', _seed(s), c['day'])
    units = r.sample(range(len(UNITS)), 4)
    x['insp'] = dict(day=c['day'], units=units, hot=units[r.randrange(4)], pick=[], rows=[], sent=False, score=None)
    return x['insp']


def _insp_rows(s: dict, c: dict, unit: int, hot: bool) -> list[dict]:
    r = _rng('insp-rows', _seed(s), c['day'], unit)
    names = r.sample(MEMBERS, 2)
    rows = []
    for n in names:
        corrupt = r.random() < (.35 if hot else .12)
        bad = [r.random() < (.4 if hot else .2) for _ in ARTEFACTS]
        if corrupt:
            bad[1] = True
        rows.append(dict(u=unit, n=n, bad=bad, cor=corrupt, m=[None, None, None], gr=None))
    return rows


def _truth_grade(row: dict) -> tuple:
    n = sum(row['bad'])
    return ('kht',) if row['cor'] or n >= 2 else ('ht',) if n == 1 else ('xs', 'tot')


def inspect(x: dict, s: dict, c: dict, p: dict, need) -> dict:
    need(post(x).get('olv') == 4, 'Chỉ Trợ lý BGĐ làm kiểm tra điều lệnh.')
    ins = insp_today(x, s, c)
    need(not ins['sent'], 'Hôm nay đã trình kết quả rồi.')
    op = p.get('op')
    if op == 'pick':
        u = p.get('unit')
        need(type(u) is int and u in ins['units'], 'Đơn vị không hợp lệ.')
        need(u not in ins['pick'], 'Đã chọn đơn vị này.')
        need(len(ins['pick']) < 2, 'Mỗi ngày kiểm tra 2 đơn vị.')
        ins['pick'].append(u)
        ins['rows'] += _insp_rows(s, c, u, u == ins['hot'])
        return dict(message=f'📋 Kiểm tra: {UNITS[u]}.')
    if op == 'send':
        return _send(x, ins, need)
    i = p.get('row')
    need(type(i) is int and 0 <= i < len(ins['rows']), 'Cán bộ không hợp lệ.')
    row = ins['rows'][i]
    if op == 'mark':
        a, v = p.get('a'), p.get('v')
        need(type(a) is int and 0 <= a < len(ARTEFACTS) and type(v) is bool, 'Đánh dấu không hợp lệ.')
        row['m'][a] = v
        e, name = ARTEFACTS[a]
        return dict(message=f'{e} {row["n"]}: {name} {"vi phạm" if v else "đạt"}.')
    if op == 'grade':
        g = p.get('g')
        need(g in INSP_GRADES, 'Mức đánh giá không hợp lệ.')
        row['gr'] = g
        return dict(message=f'🗂️ {row["n"]}: {dict((k, lab) for _, k, lab in OC.EVALS)[g]}.')
    need(False, 'Thao tác kiểm tra không hợp lệ.')
    return {}


def _send(x: dict, ins: dict, need) -> dict:
    need(len(ins['pick']) == 2 and all(None not in rw['m'] and rw['gr'] for rw in ins['rows']), 'Kiểm đủ, đánh giá đủ từng người rồi mới trình.')
    ok = sum(rw['m'][k] == rw['bad'][k] for rw in ins['rows'] for k in range(len(ARTEFACTS)))
    total = len(ins['rows']) * len(ARTEFACTS)
    fair = sum(rw['gr'] in _truth_grade(rw) for rw in ins['rows'])
    caught = sum(1 for rw in ins['rows'] if rw['cor'] and rw['m'][1])
    missed = sum(1 for rw in ins['rows'] for k in range(len(ARTEFACTS)) if rw['bad'][k] and not rw['m'][k])
    score = round(100 * (ok + fair) / (total + len(ins['rows'])))
    ins['sent'], ins['score'] = True, score
    x['adj'] = max(-50, min(10, x['adj'] + (2 if score >= 80 else 0) - (2 if missed >= 2 else 0) + 2 * caught))
    bits = [f'📤 Trình PGĐ: đúng {score}%']
    if caught:
        x['liem'] = min(LIEM_MAX, x['liem'] + caught)
        bits.append(f'phát hiện {caught} cán bộ nhận phong bì · Liêm chính +{caught}')
    if missed:
        bits.append(f'bỏ sót {missed} vi phạm')
    return dict(message=' · '.join(bits) + '.', celebrate=score >= 80)


def insp_public(x: dict, c: dict) -> dict | None:
    ins = x.get('insp')
    if not isinstance(ins, dict) or ins['day'] != c.get('day'):
        return None
    rows = []
    for i, rw in enumerate(ins['rows']):
        arts = []
        for k, (e, name) in enumerate(ARTEFACTS):
            text = FLAWS[k][1 if (k == 1 and rw['cor']) else 0] if rw['bad'][k] else CLEAN_LINES[k]
            arts.append(dict(e=e, name=name, text=text, m=rw['m'][k], truth=rw['bad'][k] if ins['sent'] else None))
        rows.append(dict(i=i, unit=UNITS[rw['u']], n=rw['n'], arts=arts, gr=rw['gr']))
    return dict(units=[dict(i=u, name=UNITS[u], hot=u == ins['hot'], on=u in ins['pick']) for u in ins['units']], rows=rows,
                sent=ins['sent'], score=ins['score'], grades=[dict(id=k, label=lab) for _, k, lab in OC.EVALS])


# ------------------------------------------------------------------------------------- the client's view
LOG_WORD = {'warn': '⚠️ Cảnh cáo', 'demote': '⬇️ Hạ bậc', 'susp': '⛔ Đình chỉ', 'expire': '🧽 Hết hạn', 'clear': '🧽 Xóa nhờ xuất sắc',
            'bribe': '💵 Nhận phong bì', 'own': '🙇 Tự giác'}


def public(x: dict, c: dict) -> dict:
    o = OC.ORGS[x['org']]
    g, p = grade(x), post(x)
    st = stars(x)
    nb = next_grade(x)
    tp = target(x)
    nxt_post = None
    if tp:
        tpp = _post(o, tp)
        nxt_post = dict(id=tp, name=tpp['name'], short=tpp['short'], rows=post_rows(x, tp), vac=x['vac'])
    due = None
    if x['due']:
        dd = x['due']
        left = [q for q in dd['qs'] if q not in dd['ans']]
        due = dict(k=dd['k'], to=dd['to'], n=len(dd['ans']), of=len(dd['qs']),
                   title=(o['courses'][dd['to']] if dd['k'] == 'course' else _post(o, dd['to'])['name']))
        if left:
            q = OC.QUESTION_INDEX[left[0]]
            opts = [dict(id=op['id'], label=op['label']) for op in q['options']]
            _rng('org-opts', q['id'], dd['day']).shuffle(opts)
            due['q'] = dict(id=q['id'], text=q['text'], options=opts)
    warns = [dict(d=w['d'], why=OC.VIOLATIONS[w['c']][0], how=OC.VIOLATIONS[w['c']][1]) for w in x['warns']]
    wlog = [dict(d=w['d'], k=LOG_WORD.get(w['k'], w['k']), why=OC.VIOLATIONS.get(w['c'], ('',))[0] if w['c'] in OC.VIOLATIONS else '')
            for w in x['wlog'][-8:]][::-1]
    ev = x['evals'][-1] if x['evals'] else None
    return dict(org=x['org'], name=o['name'], unit=o['unit'], grade=dict(id=g['id'], name=g['name'], ins=g['ins']),
                post=dict(id=p['id'], name=p['name'], short=p['short']), title=title(x), stars=st, warns=warns,
                warn_max=o['warn_max'], clean=x['clean'], decay=o['decay_days'], wlog=wlog,
                mark=dict(on=x['mark']['b'] is not None, d=x['mark']['b'], self=x['mark']['s']), liem=x['liem'],
                eval=dict((k, lab) for _, k, lab in o['evals'])[ev['g']] if ev else None, evn=x['evn'], window=o['eval_window'],
                next_grade=nb, next_post=nxt_post, aims=[dict(id=a, short=_post(o, a)['short']) for a in _aims(x)], aim=tp,
                due=due, wait=x['wait'], susp=x['susp'], waits=waits(x), pct=raise_pct(x), own=can_own(x, c),
                ladder=[dict(id=gg['id'], name=gg['name'], ins=gg['ins'], on=i <= x['g']) for i, gg in enumerate(o['grades'][:-1])],
                boss=OC.BOSS, insp=insp_public(x, c) if p.get('olv') == 4 else None)


# ------------------------------------------------------------------------------------- validation
def validate(career: str, x, need, integer, txt, bad: str) -> None:
    need(isinstance(x, dict) and set(x) == KEYS and x['v'] == V and x['org'] in OC.ORGS, bad, 'invalid_save')
    o = OC.ORGS[x['org']]
    integer(x['g'], 0, len(o['grades']) - 2)   # never the NPC-only top grade
    need(x['p'] in {p['id'] for p in o['posts']}, bad)
    for k in ('tig', 'tip'):
        integer(x[k], 0, 10**6)
    need(isinstance(x['st'], list) and len(x['st']) <= ST_MAX, bad)
    for v in x['st']:
        integer(v, 10, 50)
    need(isinstance(x['warns'], list) and len(x['warns']) < o['demote_on'], bad)
    for w in x['warns']:
        need(isinstance(w, dict) and set(w) == {'d', 'c'} and w['c'] in OC.VIOLATIONS, bad)
        integer(w['d'], 1, 10**6)
    need(isinstance(x['wlog'], list) and len(x['wlog']) <= WLOG_MAX, bad)
    for w in x['wlog']:
        need(isinstance(w, dict) and set(w) == {'d', 'k', 'c'} and w['k'] in LOG_WORD, bad)
        integer(w['d'], 1, 10**6)
        txt(w['c'], 24)
    integer(x['clean'], 0, 999)
    m = x['mark']
    need(isinstance(m, dict) and set(m) == {'b', 's'} and type(m['s']) is bool, bad)
    need(m['b'] is None or type(m['b']) is int and 1 <= m['b'] <= 10**6, bad)
    integer(x['liem'], 0, LIEM_MAX)
    need(isinstance(x['evals'], list) and len(x['evals']) <= EVALS_MAX, bad)
    for e in x['evals']:
        need(isinstance(e, dict) and set(e) == {'d', 'g'} and e['g'] in {k for _, k, _ in o['evals']}, bad)
        integer(e['d'], 1, 10**6)
    integer(x['evn'], 0, 999)
    need(isinstance(x['hist'], list) and len(x['hist']) <= HIST_MAX, bad)
    for h in x['hist']:
        need(isinstance(h, dict) and set(h) == {'d', 'k', 'fr', 'to', 'why'} and h['k'] in ('g', 'p'), bad)
        integer(h['d'], 1, 10**6)
        for k in ('fr', 'to', 'why'):
            txt(h[k], 24)
    need(isinstance(x['courses'], list) and set(x['courses']) <= set(o['courses']) and len(set(x['courses'])) == len(x['courses']), bad)
    due = x['due']
    if due is not None:
        need(isinstance(due, dict) and set(due) == {'k', 'to', 'day', 'qs', 'ans'} and due['k'] in ('post', 'course'), bad)
        need(due['to'] in (o['courses'] if due['k'] == 'course' else {p['id'] for p in o['posts']}), bad)
        integer(due['day'], 1, 10**9)
        need(isinstance(due['qs'], list) and len(due['qs']) == 2 and len(set(due['qs'])) == 2 and all(q in OC.QUESTION_INDEX for q in due['qs']), bad)
        need(isinstance(due['ans'], dict) and set(due['ans']) <= set(due['qs']), bad)
        for q, a in due['ans'].items():
            need(a in [op['id'] for op in OC.QUESTION_INDEX[q]['options']], bad)
    integer(x['wait'], 0, RETRY)
    need(x['vac'] is None or type(x['vac']) is int and 0 <= x['vac'] <= VAC_WAIT, bad)
    need(x['aim'] is None or x['aim'] in {p['id'] for p in o['posts']}, bad)
    integer(x['susp'], 0, o['susp_days'])
    integer(x['floor'], 0, 100)
    bt = x['bt']
    if bt is not None:
        need(isinstance(bt, dict) and set(bt) == {'d', 'g', 'p', 's'} and bt['p'] in {p['id'] for p in o['posts']}, bad)
        integer(bt['d'], 1, 10**9)
        integer(bt['g'], 0, len(o['grades']) - 2)
        integer(bt['s'], 0, o['susp_days'])
    integer(x['adj'], -50, 10)
    vt = x['vt']
    need(isinstance(vt, dict) and set(vt) == {'d', 'k'} and isinstance(vt['k'], list) and len(vt['k']) <= VT_MAX, bad)
    integer(vt['d'], 0, 10**9)
    for k in vt['k']:
        txt(k, 80)
    if x['office'] is not None:
        from . import promotion_office as OF
        OF.validate(o['office'], x['office'], need, integer, txt, bad)
    ins = x['insp']
    if ins is not None:
        need(isinstance(ins, dict) and set(ins) == {'day', 'units', 'hot', 'pick', 'rows', 'sent', 'score'}, bad)
        integer(ins['day'], 1, 10**9)
        need(isinstance(ins['units'], list) and len(ins['units']) == 4 and all(type(u) is int and 0 <= u < len(UNITS) for u in ins['units']), bad)
        need(ins['hot'] in ins['units'] and isinstance(ins['pick'], list) and len(ins['pick']) <= 2 and set(ins['pick']) <= set(ins['units']), bad)
        need(isinstance(ins['rows'], list) and len(ins['rows']) <= 4 and type(ins['sent']) is bool, bad)
        need(ins['score'] is None or type(ins['score']) is int and 0 <= ins['score'] <= 100, bad)
        for rw in ins['rows']:
            need(isinstance(rw, dict) and set(rw) == {'u', 'n', 'bad', 'cor', 'm', 'gr'} and rw['n'] in MEMBERS and rw['u'] in ins['pick'], bad)
            need(isinstance(rw['bad'], list) and len(rw['bad']) == 3 and all(type(b) is bool for b in rw['bad']) and type(rw['cor']) is bool, bad)
            need(isinstance(rw['m'], list) and len(rw['m']) == 3 and all(m_ is None or type(m_) is bool for m_ in rw['m']), bad)
            need(rw['gr'] is None or rw['gr'] in INSP_GRADES, bad)
