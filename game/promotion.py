"""🎖️ Thăng tiến (every career) and 🧑‍💼 Ca quản lý (its top steps).

A good day of work moves you towards the next step. When the next step is in reach, the day
summary says so and the next morning brings a short review: two situation questions (the boss's
office for an employee, the street traders' association for an owner), then, for an employee, the
pay ask. Passing gives the new title and, for good:

* an employee: a raise on the contract salary (+8 / 16 / 25 / 35 %, plus up to +12 points earned in
  the pay asks), paid by employment.on_close before probation and the ×3/×5 accounting rate;
  `job['salary']` itself never changes (its validator keeps it inside the posting's range);
* an owner: regulars tip a share of the day's sales (+3 / 6 / 9 / 12 %, capped per day).

Nothing goes down: a weak day only pauses the count, a review that does not pass simply comes again
after a few worked days. Quitting a job starts that job's ladder again (the log is kept).

From step 3 the player may open a day as a 🧑‍💼 manager shift instead of serving customers
(start_day {manager: true}). The day's jobs (the career's own tasks of that day, read with
make_task) go to 2 teammates (3 at step 4): tap a job, tap a teammate (a good match is faster and
better), check what comes back (✅ or ↩️), settle one or two small crises, close the shift. The pay
is the day's salary plus a manager bonus from the team's output (an owner: the team's sales minus
the temporary helpers). The usual hands-on shift stays available every day.

State: journey['promo'] = {career: record} — a new optional key: older servers ignore it (their
journey.validate allows extra keys), and nothing about the career or job blocks changes.
"""
from __future__ import annotations

import random

from . import promotion_content as PC

VERSION = 1
# Steps 1..4. good: good days since the last step; ratio: share of worked days that were good (%).
EMP_STEPS = (None,
             dict(good=5, ratio=70, pct=8),
             dict(good=8, pct=16),
             dict(good=12, pct=25, served=40, cert=True),
             dict(good=20, pct=35, served=80, chapter=5))
OWN_STEPS = (None,
             dict(good=5, ratio=70, served=15, pct=3, cap=10),
             dict(good=8, served=30, rating=40, pct=6, cap=18),
             dict(good=12, served=50, pct=9, cap=26),
             dict(good=20, served=100, chapter=5, pct=12, cap=35))
TOP = 4
ACCT = ('corp_accounting', 'tax_payroll', 'group_accounting')
ACCT_CARE = {1: 2, 2: 3}       # the accounting care track's rank a step needs
RETRY = 3                      # worked days before a review that did not pass comes again
EXTRA_MAX = 12
LOG_MAX = 8
TIP_CATS = ('revenue', 'room', 'service')   # the day's sales an owner's regulars tip on

# 🧑‍💼 Ca quản lý
MGR_FROM = 3
SIZE = {3: 6, 4: 8}            # jobs in a shift
TEAM = {3: 2, 4: 3}            # teammates
CAP = {3: 60, 4: 90}           # employee: manager bonus cap (xu)
OWN_CAP = {3: 90, 4: 135}      # owner: the team's sales cap (xu)
XU_PER_PT, OWN_XU_PER_PT = 2, 3
HELPER_WAGE = 8                # an owner's temporary helper, per shift
PTS_GOOD, PTS_OK, PTS_CATCH = 5, 2, 1
GOOD_Q = 60                    # quality (%) that makes a manager shift a good day
LEFT = {'s': 1, 'n': 2, 'w': 3}     # moves a job takes: teammate's strength, neutral, weakness
FLAW = {'s': 10, 'n': 30, 'w': 55}  # % that a job comes back with a mistake
LOW_MOOD = 40                  # below it, +15 points of mistakes
MAX_MOVES = 80

REC_KEYS = frozenset(('rank', 'good', 'worked', 'wait', 'extra', 'emp', 'hd', 'due', 'log', 'shift', 'mgr'))
TASK_ST = ('q', 'w', 'd', 'ok', 'meh')


def _core():
    from . import engine
    return engine


def _emp():
    from . import employment
    return employment


def track(career: str) -> str:
    return 'emp' if _emp().required(career) else 'own'


def group(career: str) -> str:
    return next((g for g, ids in PC.GROUP.items() if career in ids), 'trade')


def _own_key(career: str) -> str:
    return career if career in PC.OWN_TITLES else 'shop'


def _rng(*parts) -> random.Random:
    return random.Random('|'.join(map(str, parts)))


def _seed(s: dict) -> int:
    return int((s.get('journey') or {}).get('seed') or 0)


def new_record() -> dict:
    return dict(rank=0, good=0, worked=0, wait=0, extra=0, emp=None, hd=0, due=None, log=[], shift=None,
                mgr=dict(n=0, best=0))


def _book(s: dict, create: bool = False) -> dict | None:
    j = s.get('journey')
    if not isinstance(j, dict):
        return None
    if 'promo' not in j:
        if not create:
            return None
        j['promo'] = {}
    return j['promo']


def record(s: dict, career: str, create: bool = False) -> dict | None:
    book = _book(s, create)
    if book is None:
        return None
    rec = book.get(career)
    if rec is None and create:
        rec = book[career] = new_record()
    return rec


def _job_ok(c: dict) -> bool:
    job = c.get('job') or {}
    return job.get('status') == 'hired'


def _sync(rec: dict, c: dict) -> None:
    """An employee's ladder belongs to one contract: a new employer or a new hire starts it again."""
    job = c.get('job') or {}
    if rec['emp'] == job.get('employer') and rec['hd'] == job.get('hired_day'):
        return
    keep = rec['log']
    rec.clear()
    rec.update(new_record(), emp=job.get('employer'), hd=job.get('hired_day') or 0, log=keep)


def _live(s: dict, c: dict, career: str, create: bool = False) -> dict | None:
    """The career's record as it applies now (an employee's only while hired at the contract it was earned at)."""
    if track(career) == 'emp':
        if not _job_ok(c):
            return None
        rec = record(s, career, create)
        if rec is None:
            return None
        if create:
            _sync(rec, c)
        elif rec['emp'] != c['job'].get('employer') or rec['hd'] != c['job'].get('hired_day'):
            return None
        return rec
    return record(s, career, create)


def rank(s: dict, c: dict, career: str) -> int:
    rec = _live(s, c, career)
    return rec['rank'] if rec else 0


def raise_pct(s: dict, c: dict, career: str) -> int:
    """Employee: the raise (%) on the contract salary at today's step (employment.on_close)."""
    if track(career) != 'emp':
        return 0
    rec = _live(s, c, career)
    if not rec or rec['rank'] < 1:
        return 0
    return EMP_STEPS[rec['rank']]['pct'] + rec['extra']


def step_pct(career: str, n: int, extra: int = 0) -> int:
    if n < 1:
        return 0
    return (EMP_STEPS[n]['pct'] + extra) if track(career) == 'emp' else OWN_STEPS[n]['pct']


def title(s: dict, c: dict, career: str, n: int) -> str:
    if track(career) == 'emp':
        if n < 1:
            job = c.get('job') or {}
            return job.get('title') or PC.BASE_EMP
        return PC.EMP_TITLES.get(career, PC.EMP_TITLES['repair'])[n - 1]
    if n < 1:
        return PC.BASE_OWN
    gender = (s.get('journey') or {}).get('gender')
    return PC.OWN_TITLES[_own_key(career)][n - 1].format(chu=PC.CHU.get(gender, PC.CHU[None]), ong=PC.ONG.get(gender, PC.ONG[None]))


def _served(c: dict) -> int:
    return int((c.get('metrics') or {}).get('served') or 0)


def _rating10(c: dict) -> int | None:
    stars = [f['stars'] for f in c.get('feed') or () if f.get('stars')]
    return round(10 * sum(stars) / len(stars)) if stars else None


def _care_rank(c: dict) -> int:
    care = ((c.get('ext') or {}).get('data') or {}).get('care')
    r = care.get('rank') if isinstance(care, dict) else None
    return r if type(r) is int else 0


def _gates(s: dict, c: dict, career: str, rec: dict) -> list[dict]:
    """All career-specific requirements, shared by eligibility and its public explanation."""
    n = rec['rank'] + 1
    if n > TOP:
        return []
    emp = track(career) == 'emp'
    st = (EMP_STEPS if emp else OWN_STEPS)[n]
    rows = []
    if emp and n == 1:
        rows.append(dict(id='probation', met=not bool((c.get('job') or {}).get('probation')),
                         label='Hết thử việc trước đã'))
    if emp and career in ACCT and n in ACCT_CARE:
        rows.append(dict(id='care', met=_care_rank(c) >= ACCT_CARE[n],
                         label='🧭 Lộ trình phòng kế toán: bậc ' + str(ACCT_CARE[n])))
    served = st.get('served', 0)
    if st.get('cert'):
        from . import certificates as ct
        rows.append(dict(id='certificate_or_served', met=bool(ct.held_for(s, career) or _served(c) >= served),
                         label=f'🎓 Chứng chỉ nhóm nghề hoặc {served} lượt khách'))
    elif served:
        rows.append(dict(id='served', met=_served(c) >= served, label=f'{served} lượt khách ({_served(c)} rồi)'))
    if st.get('rating'):
        r = _rating10(c)
        rows.append(dict(id='rating', met=r is None or r >= st['rating'],
                         label=f'Điểm đánh giá ★{st["rating"] / 10:.1f}'))
    j = s.get('journey') or {}
    if st.get('chapter') and j.get('story'):
        rows.append(dict(id='chapter', met=int(j.get('chapter') or 1) >= st['chapter'],
                         label=f'Tới chương {st["chapter"]}'))
    return rows


def gate(s: dict, c: dict, career: str, rec: dict) -> str | None:
    """First unmet career requirement; kept for callers that need one short line."""
    return next((row['label'] for row in _gates(s, c, career, rec) if not row['met']), None)


def ready(s: dict, c: dict, career: str, rec: dict) -> bool:
    n = rec['rank'] + 1
    if n > TOP or rec['wait'] > 0 or rec['due']:
        return False
    st = (EMP_STEPS if track(career) == 'emp' else OWN_STEPS)[n]
    if rec['good'] < st['good']:
        return False
    if st.get('ratio') and rec['good'] * 100 < st['ratio'] * rec['worked']:
        return False
    return gate(s, c, career, rec) is None


def can_manage(s: dict, c: dict, career: str) -> bool:
    if track(career) == 'emp' and (not _job_ok(c) or c['job'].get('probation')):
        return False
    return rank(s, c, career) >= MGR_FROM


def _shift(s: dict, c: dict, career: str) -> dict | None:
    rec = _live(s, c, career)
    sh = rec.get('shift') if rec else None
    return sh if isinstance(sh, dict) and sh.get('day') == c.get('day') else None


def managing(s: dict, c: dict, career: str) -> bool:
    """Today is a manager shift (more_work stays closed, also once the board is closed: the team took the day)."""
    sh = _shift(s, c, career)
    return bool(sh and c.get('open'))


def managed_today(s: dict, c: dict, career: str) -> bool:
    """Today was a manager shift that got work done: the day's salary is due as on a worked day."""
    sh = _shift(s, c, career)
    return bool(sh and any(t['st'] in ('ok', 'meh') for t in sh['tasks']))


# ------------------------------------------------------------------------------------- manager shift
def _sw(career: str, name: str) -> tuple[str, str]:
    r = _rng('pm-sw', career, name)
    strong = r.choice(PC.KINDS)
    weak = r.choice([k for k in PC.KINDS if k != strong])
    return strong, weak


def _team(s: dict, c: dict, career: str, n: int) -> list[dict]:
    from . import operations as ops
    people = list(enumerate(ops.PEOPLE.get(career) or ()))
    team = []
    if track(career) == 'own':
        # The hired staff first (Sổ tiệm), then temporary helpers from the same candidates.
        for e in (c.get('ops') or {}).get('staff') or ():
            if e.get('status') == 'hired' and len(team) < n:
                mood = e.get('morale') if type(e.get('morale')) is int else 70
                team.append(dict(id=str(e['id'])[:60], name=str(e['name'])[:24], mood=max(20, min(100, mood)), tmp=False))
        taken = {m['id'] for m in team}
        r = _rng('pm-helpers', _seed(s), career, c['day'])
        r.shuffle(people)
        for i, p in people:
            if len(team) >= n:
                break
            pid = f'{career}-staff-{i + 1}'
            if pid not in taken:
                team.append(dict(id=pid, name=p[0], mood=65, tmp=True))
    else:
        r = _rng('pm-team', _seed(s), career, c['day'])
        r.shuffle(people)
        for i, p in people[:n]:
            team.append(dict(id=f'{career}-staff-{i + 1}', name=p[0], mood=70, tmp=False))
    k = 0
    while len(team) < n:   # a career without enough people: neighbours lend a hand
        k += 1
        team.append(dict(id=f'{career}-help-{k}', name=('Bé Na', 'Anh Tư', 'Cô Sáu')[(k - 1) % 3], mood=65, tmp=track(career) == 'own'))
    for m in team:
        m['s'], m['w'] = _sw(career, m['name'])
        m['off'] = False
    return team


def _jobs(s: dict, c: dict, career: str, n: int) -> list[dict]:
    """The day's jobs: the career's own tasks of the day (title and customer), kinds spread over the team."""
    from .content import make_task, NPC_INDEX
    kinds = list(PC.KINDS) * 3
    _rng('pm-kinds', _seed(s), career, c['day']).shuffle(kinds)
    out = []
    for i in range(n):
        label, who = '', ''
        try:
            t = make_task(career, c['day'], i, c.get('turn', 0))
            label = str(t.get('title') or '')
            npc = NPC_INDEX.get(t.get('npc'))
            who = npc['display_name'] if npc else ''
        except Exception:   # a career whose task needs more context: a plain job card
            pass
        out.append(dict(t=(label or f'Việc {i + 1}')[:60], k=str(who)[:40], kind=kinds[i], st='q', who=None, left=0, q=0, back=0))
    return out


def _escalations(s: dict, c: dict, career: str, n_rank: int, team: list) -> list[dict]:
    r = _rng('pm-esc', _seed(s), career, c['day'])
    count = 2 if n_rank >= 4 or r.random() < .35 else 1
    picks = r.sample(PC.ESCALATIONS, count)
    ats = [r.randint(3, 5), r.randint(8, 11)]
    out = []
    for i, x in enumerate(picks):
        a, b = r.sample(range(len(team)), 2)
        out.append(dict(id=x['id'], at=ats[i], a=a, b=b, pick=None))
    return out


def start_shift(s: dict, c: dict, career: str) -> str:
    rec = _live(s, c, career, create=True)
    n = min(rec['rank'], TOP)
    team = _team(s, c, career, TEAM[n])
    rec['shift'] = dict(day=c['day'], size=SIZE[n], n=0, team=team, tasks=_jobs(s, c, career, SIZE[n]),
                        esc=_escalations(s, c, career, n, team), pts=0, caught=0, closed=False, bonus=0, wage=0)
    return '🧑‍💼 Ca quản lý: giao việc cho đội nhé.'


def _open_esc(sh: dict) -> dict | None:
    return next((x for x in sh['esc'] if x['pick'] is None and x['at'] <= sh['n']), None)


def _tick(sh: dict) -> None:
    sh['n'] += 1
    for t in sh['tasks']:
        if t['st'] == 'w':
            t['left'] -= 1
            if t['left'] <= 0:
                t['st'], t['left'] = 'd', 0


def _match(m: dict, kind: str) -> str:
    return 's' if m['s'] == kind else 'w' if m['w'] == kind else 'n'


def _fill(text: str, sh: dict, x: dict) -> str:
    team = sh['team']
    k = next((t['k'] for t in sh['tasks'] if t['k']), '') or PC.CUSTOMER
    return text.format(a=team[x['a']]['name'], b=team[x['b']]['name'], k=k)


def _results(sh: dict) -> dict:
    good = sum(t['st'] == 'ok' for t in sh['tasks'])
    meh = sum(t['st'] == 'meh' for t in sh['tasks'])
    mood = round(sum(m['mood'] for m in sh['team']) / len(sh['team'])) if sh['team'] else 0
    return dict(done=good + meh, good=good, size=sh['size'], quality=round(100 * good / sh['size']) if sh['size'] else 0,
                mood=mood, pts=sh['pts'], bonus=sh['bonus'], wage=sh['wage'], caught=sh['caught'])


def _close(s: dict, c: dict, career: str, rec: dict, sh: dict) -> dict:
    e = _core()
    n = min(rec['rank'], TOP)
    res = _results(sh)
    if track(career) == 'emp':
        bonus = min(CAP.get(n, CAP[3]), XU_PER_PT * sh['pts'])
        if bonus:
            e.money(s, c, bonus, f'🧑‍💼 Thưởng quản lý · {res["good"]} việc tốt', f'pm-{c["day"]}', category='bonus')
        sh['bonus'] = bonus
    else:
        sales = min(OWN_CAP.get(n, OWN_CAP[3]), OWN_XU_PER_PT * sh['pts'])
        wage = min(sales, HELPER_WAGE * sum(1 for m in sh['team'] if m.get('tmp')))
        if sales:
            e.money(s, c, sales, f'🧑‍💼 Doanh thu đội · {res["good"]} việc tốt', f'pm-{c["day"]}', category='revenue')
        if wage:
            e.money(s, c, -wage, '🧑‍💼 Phụ việc thời vụ', f'pm-{c["day"]}-w', category='staff')
        sh['bonus'], sh['wage'] = sales, wage
    sh['closed'] = True
    rec['mgr']['n'] = min(10**6, rec['mgr']['n'] + 1)
    rec['mgr']['best'] = max(rec['mgr']['best'], res['quality'])
    return _results(sh)


def _move(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    rec = _live(s, c, career)
    sh = _shift(s, c, career) if rec else None
    need(sh and c['open'], 'Chưa có ca quản lý nào đang mở.')
    need(not sh['closed'], 'Ca quản lý đã chốt. Khép ngày thôi!')
    esc = _open_esc(sh)
    if name == 'pm_close':
        need(not esc, 'Gỡ rối chuyện đang chờ trước đã.')
        res = _close(s, c, career, rec, sh)
        own = track(career) == 'own'
        line = f'+{res["bonus"]} xu ' + ('doanh thu đội' if own else 'thưởng quản lý')
        return dict(message=f'🧑‍💼 Chốt ca: {res["good"]}/{res["size"]} việc tốt · {line}.', celebrate=res['quality'] >= GOOD_Q,
                    manager=res)
    need(sh['n'] < MAX_MOVES, 'Ca đã dài lắm rồi. Chốt ca thôi!')
    if name == 'pm_fix':
        need(esc, 'Không có chuyện nào cần gỡ.')
        x = PC.ESCALATION_INDEX[esc['id']]
        opt = next((o for o in x['options'] if o['id'] == p.get('option')), None)
        need(opt, 'Lựa chọn không hợp lệ.')
        _tick(sh)
        esc['pick'] = opt['id']
        sh['pts'] += opt['pts']
        for m in sh['team']:
            m['mood'] = max(0, min(100, m['mood'] + opt.get('mood', 0)))
        a = sh['team'][esc['a']]
        a['mood'] = max(0, min(100, a['mood'] + opt.get('a_mood', 0)))
        if opt.get('off'):
            a['off'] = True
            for t in sh['tasks']:
                if t['who'] == esc['a'] and t['st'] == 'w':
                    t.update(st='q', who=None, left=0, q=0)
        return dict(message='Đã gỡ rối.' if opt['pts'] >= 2 else 'Tạm ổn.')
    need(not esc, 'Có chuyện cần gỡ rối trước đã.')
    tasks = sh['tasks']
    if name == 'pm_wait':
        need(any(t['st'] == 'w' for t in tasks), 'Không ai đang làm dở. Giao việc tiếp nhé.')
        _tick(sh)
        return dict(message='⏳ Đội làm tiếp…')
    idx = p.get('task')
    need(type(idx) is int and 0 <= idx < len(tasks), 'Việc không hợp lệ.')
    t = tasks[idx]
    if name == 'pm_assign':
        mi = p.get('mate')
        need(type(mi) is int and 0 <= mi < len(sh['team']), 'Người nhận không hợp lệ.')
        m = sh['team'][mi]
        need(t['st'] == 'q', 'Việc này đã giao rồi.')
        need(not m['off'], f'{m["name"]} đã về nghỉ.')
        need(not any(x['who'] == mi and x['st'] == 'w' for x in tasks), f'{m["name"]} đang bận việc khác.')
        _tick(sh)
        fit = _match(m, t['kind'])
        flaw = FLAW[fit] + (15 if m['mood'] < LOW_MOOD else 0)
        roll = _rng('pm-flaw', _seed(s), career, sh['day'], idx, mi, t['back']).randrange(100)
        t.update(st='w', who=mi, left=LEFT[fit], q=1 if roll < flaw else 0)
        return dict(message={'s': f'👍 Đúng sở trường của {m["name"]}!', 'n': f'Đã giao cho {m["name"]}.',
                             'w': f'{m["name"]} hơi lúng túng việc này…'}[fit], fit=fit)
    if name == 'pm_check':
        ok = p.get('ok')
        need(type(ok) is bool, 'Chọn ✅ hoặc ↩️.')
        need(t['st'] == 'd', 'Việc này chưa xong để kiểm.')
        _tick(sh)
        m = sh['team'][t['who']] if t['who'] is not None else None
        if ok:
            if t['q']:
                t['st'] = 'meh'
                sh['pts'] += PTS_OK
                return dict(message='Đã nhận. Có chỗ chưa ổn, lần sau soi kỹ hơn nhé.', caught=False)
            t['st'] = 'ok'
            sh['pts'] += PTS_GOOD
            if m:
                m['mood'] = min(100, m['mood'] + 3)
            return dict(message='✅ Việc tốt!', caught=None)
        if t['q']:
            sh['caught'] += 1
            sh['pts'] += PTS_CATCH
            t.update(st='w', left=1, q=0, back=t['back'] + 1)
            return dict(message='🔍 Bắt đúng lỗi! Làm lại ngay.', caught=True)
        if m:
            m['mood'] = max(0, m['mood'] - 10)
        t.update(st='w', left=1, back=t['back'] + 1)
        return dict(message='Việc này vốn ổn rồi… đội hơi buồn.', caught=False)
    raise e.GameError('Thao tác quản lý không hợp lệ.')


# ------------------------------------------------------------------------------------- the review
def _draw_qs(s: dict, career: str, rec: dict, day: int) -> list[str]:
    bank = PC.QUESTIONS[group(career)]
    r = _rng('pm-qs', _seed(s), career, rec['rank'], len(rec['log']), day)
    return [q['id'] for q in r.sample(bank, 2)]


def _promote(s: dict, c: dict, career: str, rec: dict, extra: int) -> dict:
    j = s.get('journey') or {}
    rec['rank'] += 1
    rec['extra'] = min(EXTRA_MAX, rec['extra'] + extra)
    rec['good'] = rec['worked'] = rec['wait'] = 0
    rec['due'] = None
    pct = step_pct(career, rec['rank'], rec['extra'])
    rec['log'] = (rec['log'] + [dict(d=int(j.get('life_day') or 1), to=rec['rank'], pct=pct)])[-LOG_MAX:]
    name = title(s, c, career, rec['rank'])
    _core().log(s, c, 'job', f'🎖️ Lên {name}.')
    if track(career) == 'emp':
        base = int(c['job']['salary'])
        line = f'🎉 Bạn lên {name}! Từ mai lương {base} → {round(base * (100 + pct) / 100)} xu/ngày.'
    else:
        line = f'🎉 Bạn thành {name}! Khách quen boa thêm {pct}% doanh thu.'
    if rec['rank'] == MGR_FROM:
        line += ' Mở khóa 🧑‍💼 Ca quản lý.'
    return dict(message=line, celebrate=True, promoted=dict(to=rec['rank'], title=name, pct=pct))


def _later(rec: dict, line: str) -> dict:
    rec['due'] = None
    rec['wait'] = RETRY
    return dict(message=line, later=True)


def _review(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    rec = _live(s, c, career)
    due = rec.get('due') if rec else None
    need(due, 'Chưa có buổi xét lên chức nào.')
    emp = track(career) == 'emp'
    if name == 'pm_answer':
        left = [q for q in due['qs'] if q not in due['ans']]
        need(left and p.get('question') == left[0], 'Câu hỏi không hợp lệ hoặc đã trả lời.')
        q = PC.QUESTION_INDEX[left[0]]
        opt = next((o for o in q['options'] if o['id'] == p.get('option')), None)
        need(opt, 'Câu trả lời không hợp lệ.')
        due['ans'][q['id']] = opt['id']
        if len(due['ans']) < len(due['qs']):
            return dict(message='Ghi nhận.', score=opt['score'])
        scores = [_score(x, due['ans'][x]) for x in due['qs']]
        if min(scores) == 0:
            who = 'Sếp' if emp else 'Hội buôn phố'
            return _later(rec, f'{who}: “Mình cần thêm thời gian. Hẹn bạn sau {RETRY} ngày làm nữa nhé.”')
        if not emp:
            return _promote(s, c, career, rec, 0)
        return dict(message='Giờ tới phần lương.', score=opt['score'], ask=True)
    if name == 'pm_ask':
        need(emp, 'Chủ tiệm không cần xin lương.')
        need(len(due['ans']) == len(due['qs']), 'Trả lời hết câu hỏi trước đã.')
        ask = PC.ASK_INDEX.get(p.get('ask'))
        need(ask, 'Mức xin lương không hợp lệ.')
        best = all(_score(x, due['ans'][x]) == 2 for x in due['qs'])
        if ask['id'] == 'high' and not best:
            return _later(rec, f'Sếp: “Mức này để quý sau nhé.” Hẹn xét lại sau {RETRY} ngày làm.')
        return _promote(s, c, career, rec, ask['extra'] if best else 0)
    raise e.GameError('Thao tác xét lên chức không hợp lệ.')


def _score(qid: str, oid: str) -> int:
    q = PC.QUESTION_INDEX[qid]
    return next(o['score'] for o in q['options'] if o['id'] == oid)


def action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    if name in ('pm_answer', 'pm_ask'):
        return _review(s, c, career, name, p)
    return _move(s, c, career, name, p)


# ------------------------------------------------------------------------------------- engine hooks
def on_start(s: dict, c: dict, career: str, p: dict) -> str | None:
    """start_day: {manager: true} opens a manager shift (checked before the shift opens: see allowed_start)."""
    if p.get('manager') is True:
        return start_shift(s, c, career)
    rec = _live(s, c, career)
    if rec and rec.get('shift'):
        rec['shift'] = None   # yesterday's board (an older build closed that day)
    return None


def check_start(s: dict, c: dict, career: str, p: dict) -> bool:
    """Before start_day: is a manager shift asked for (and allowed)?"""
    if p.get('manager') is None:
        return False
    _core().need(p.get('manager') is True and can_manage(s, c, career), 'Ca quản lý mở từ bậc thứ ba.', 'not_manager')
    return True


def _good_normal(c: dict, summary: dict) -> bool:
    if summary.get('abandon'):
        return False
    care = (summary.get('career') or {}).get('care') if isinstance(summary.get('career'), dict) else None
    if isinstance(care, dict) and type(care.get('reliable')) is bool:
        return care['reliable']   # the office careers' "ngày chắc tay"
    if c['day_completed'] < 2:
        return False
    stars = [f['stars'] for f in c['feed'] if f.get('stars') and f.get('day') == c['day'] and f.get('kind') == 'review']
    return not stars or sum(stars) / len(stars) >= 3.5


def _day_sales(c: dict) -> int:
    rows = ((c.get('ops') or {}).get('finance') or {}).get('ledger') or ()
    return sum(r['amount'] for r in rows if r.get('day') == c['day'] and r.get('category') in TIP_CATS and r.get('amount', 0) > 0)


def on_close(s: dict, c: dict, career: str, summary: dict) -> dict | None:
    """end_day, before the day's net is summed: closes a manager shift still open, pays an owner's tip
    perk, counts the day and books the next review."""
    emp = track(career) == 'emp'
    if emp and not _job_ok(c):
        return None
    rec = _live(s, c, career, create=True)
    out = {}
    sh = _shift(s, c, career)
    mgr = None
    if sh:
        mgr = _close(s, c, career, rec, sh) if not sh['closed'] else _results(sh)
        out['manager'] = mgr
    rec['shift'] = None
    worked = c['day_completed'] >= 1 or bool(mgr and mgr['done'] >= 1)
    if not worked:
        return out or None
    good = mgr['quality'] >= GOOD_Q if mgr else _good_normal(c, summary)
    if not emp and rec['rank'] >= 1:
        st = OWN_STEPS[rec['rank']]
        tip = min(st['cap'], _day_sales(c) * st['pct'] // 100)
        if tip > 0:
            _core().money(s, c, tip, f'🎖️ Khách quen boa thêm · {title(s, c, career, rec["rank"])}', f'pm-tip-{c["day"]}', category='tip')
            out['tip'] = tip
    rec['worked'] = min(10**6, rec['worked'] + 1)
    if good:
        rec['good'] = min(10**6, rec['good'] + 1)
    if rec['wait'] > 0:
        rec['wait'] -= 1
    out['good'] = good
    if ready(s, c, career, rec):
        rec['due'] = dict(to=rec['rank'] + 1, day=c['day'] + 1, qs=_draw_qs(s, career, rec, c['day']), ans={})
        out['due'] = title(s, c, career, rec['rank'] + 1)
        out['line'] = (f'🎖️ Sếp hẹn gặp bạn đầu ca sau để xét lên {out["due"]}.' if emp else
                       f'🎖️ Hội buôn phố hẹn ghé sáng mai: xét danh hiệu {out["due"]}.')
    nxt = _next(s, c, career, rec)
    if nxt:
        out['next'] = nxt
    return out


def forget(s: dict, career: str) -> None:
    """reset_career: the place starts again from nothing."""
    book = _book(s)
    if book is not None:
        book.pop(career, None)


# ------------------------------------------------------------------------------------- the client's view
def _next(s: dict, c: dict, career: str, rec: dict) -> dict | None:
    n = rec['rank'] + 1
    if n > TOP:
        return None
    st = (EMP_STEPS if track(career) == 'emp' else OWN_STEPS)[n]
    requirements = [dict(id='good', met=rec['good'] >= st['good'],
                         label=f'{rec["good"]}/{st["good"]} ngày tốt từ lần lên bậc gần nhất')]
    if st.get('ratio'):
        # Keep the full numerator and compare integers, exactly as ready does. A rounded
        # percentage (e.g. 69.99 -> 70) must never make a blocked review appear eligible.
        pct = rec['good'] * 100 // rec['worked'] if rec['worked'] else 0
        requirements.append(dict(id='ratio', met=rec['good'] * 100 >= st['ratio'] * rec['worked'],
                                 good=rec['good'], worked=rec['worked'], need=st['ratio'],
                                 label=f'Tỷ lệ ngày tốt ít nhất {st["ratio"]}%: {rec["good"]}/{rec["worked"]} ngày làm ({pct}%)'))
    requirements.extend(_gates(s, c, career, rec))
    if rec['wait'] > 0:
        requirements.append(dict(id='wait', met=False, label=f'Hẹn xét lại sau {rec["wait"]} ngày làm'))
    if rec['due']:
        requirements.append(dict(id='review', met=False, label='Đã có lịch xét bậc ở đầu ca sau'))
    return dict(title=title(s, c, career, n), good=min(rec['good'], st['good']), need=st['good'],
                why=gate(s, c, career, rec), wait=rec['wait'], pct=step_pct(career, n, rec['extra']),
                requirements=requirements)


def _due_view(s: dict, c: dict, career: str, rec: dict) -> dict | None:
    due = rec.get('due')
    if not due:
        return None
    emp = track(career) == 'emp'
    left = [q for q in due['qs'] if q not in due['ans']]
    v = dict(to=due['to'], title=title(s, c, career, due['to']), n=len(due['ans']), of=len(due['qs']),
             who='Phòng sếp' if emp else 'Hội buôn phố')
    if left:
        q = PC.QUESTION_INDEX[left[0]]
        opts = [dict(id=o['id'], label=o['label']) for o in q['options']]
        _rng('pm-opts', q['id'], due['day']).shuffle(opts)
        v['q'] = dict(id=q['id'], text=q['text'], options=opts)
    elif emp:
        base = int(c['job']['salary'])
        pct = step_pct(career, due['to'], rec['extra'])
        v['ask'] = [dict(id=a['id'], label=a['label']) for a in PC.ASKS]
        v['pay'] = [base, round(base * (100 + pct) / 100)]
    return v


def _shift_view(sh: dict) -> dict:
    esc = _open_esc(sh)
    tasks = []
    for i, t in enumerate(sh['tasks']):
        row = dict(i=i, t=t['t'], k=t['k'], kind=t['kind'], st=t['st'], who=t['who'], left=t['left'])
        if t['st'] == 'd':
            row['res'] = PC.RESULT[t['kind']][1 if t['q'] else 0]
            row['bad'] = bool(t['q'])
        tasks.append(row)
    busy = {t['who'] for t in sh['tasks'] if t['st'] == 'w'}
    team = [dict(i=i, name=m['name'], s=m['s'], w=m['w'], mood=m['mood'], off=m['off'], busy=i in busy, tmp=bool(m.get('tmp')))
            for i, m in enumerate(sh['team'])]
    v = dict(n=sh['n'], tasks=tasks, team=team, closed=sh['closed'], **_results(sh))
    if esc:
        x = PC.ESCALATION_INDEX[esc['id']]
        v['esc'] = dict(id=x['id'], kind=x['kind'], text=_fill(x['text'], sh, esc),
                        options=[dict(id=o['id'], label=_fill(o['label'], sh, esc)) for o in x['options']])
    return v


def public(s: dict, c: dict, career: str) -> dict | None:
    """c['promo'] of the career on screen: small (the board only while a manager shift runs)."""
    emp = track(career) == 'emp'
    if emp and not _job_ok(c):
        return None
    rec = _live(s, c, career)
    if rec is None:
        rec = new_record()
    n = rec['rank']
    v = dict(track='emp' if emp else 'own', rank=n, top=TOP, title=title(s, c, career, n), pct=step_pct(career, n, rec['extra']),
             next=_next(s, c, career, rec), mgr=can_manage(s, c, career), team=TEAM.get(min(max(n, MGR_FROM), TOP)),
             due=_due_view(s, c, career, rec), log=rec['log'][-3:], shifts=rec['mgr']['n'])
    sh = _shift(s, c, career)
    if sh:
        v['shift'] = _shift_view(sh)
    return v


# ------------------------------------------------------------------------------------- validation
def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'promo' not in j:
        return
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    bad = 'Dữ liệu thăng tiến không hợp lệ.'
    book = j['promo']
    need(isinstance(book, dict) and set(book) <= set(s.get('careers') or ()), bad, 'invalid_save')
    for cid, rec in book.items():
        need(isinstance(rec, dict) and REC_KEYS <= set(rec), bad, 'invalid_save')
        integer(rec['rank'], 0, TOP)
        for k in ('good', 'worked'):
            integer(rec[k], 0, 10**6)
        integer(rec['wait'], 0, RETRY)
        integer(rec['extra'], 0, EXTRA_MAX)
        integer(rec['hd'], 0, 10**9)
        need(rec['emp'] is None or isinstance(rec['emp'], str) and len(rec['emp']) <= 80, bad)
        need(isinstance(rec['log'], list) and len(rec['log']) <= LOG_MAX, bad)
        for row in rec['log']:
            need(isinstance(row, dict), bad)
            integer(row.get('d'), 1, 10**6)
            integer(row.get('to'), 1, TOP)
            integer(row.get('pct'), 0, 100)
        mgr = rec['mgr']
        need(isinstance(mgr, dict), bad)
        integer(mgr.get('n'), 0, 10**6)
        integer(mgr.get('best'), 0, 100)
        due = rec['due']
        if due is not None:
            need(isinstance(due, dict) and due.get('to') == rec['rank'] + 1, bad)
            integer(due.get('day'), 1, 10**9)
            qs, ans = due.get('qs'), due.get('ans')
            need(isinstance(qs, list) and len(qs) == 2 and len(set(qs)) == 2 and all(q in PC.QUESTION_INDEX for q in qs), bad)
            need(isinstance(ans, dict) and set(ans) <= set(qs), bad)
            for q, o in ans.items():
                need(o in [x['id'] for x in PC.QUESTION_INDEX[q]['options']], bad)
        sh = rec['shift']
        if sh is not None:
            _validate_shift(sh, need, integer, txt, bad)


def _validate_shift(sh, need, integer, txt, bad) -> None:
    need(isinstance(sh, dict), bad)
    integer(sh.get('day'), 1, 10**9)
    size = integer(sh.get('size'), 1, max(SIZE.values()))
    integer(sh.get('n'), 0, MAX_MOVES)
    for k in ('pts', 'caught', 'bonus', 'wage'):
        integer(sh.get(k), 0, 10**4)
    need(type(sh.get('closed')) is bool, bad)
    team = sh.get('team')
    need(isinstance(team, list) and 2 <= len(team) <= max(TEAM.values()), bad)
    for m in team:
        need(isinstance(m, dict) and m.get('s') in PC.KINDS and m.get('w') in PC.KINDS and m['s'] != m['w'], bad)
        txt(m.get('name'), 24)
        txt(m.get('id'), 80)
        integer(m.get('mood'), 0, 100)
        need(type(m.get('off')) is bool and type(m.get('tmp')) is bool, bad)
    tasks = sh.get('tasks')
    need(isinstance(tasks, list) and len(tasks) == size, bad)
    for t in tasks:
        need(isinstance(t, dict) and t.get('kind') in PC.KINDS and t.get('st') in TASK_ST, bad)
        txt(t.get('t'), 60)
        need(isinstance(t.get('k'), str) and len(t['k']) <= 40, bad)
        need(t.get('who') is None or type(t['who']) is int and 0 <= t['who'] < len(team), bad)
        need((t['who'] is None) == (t['st'] == 'q'), bad)
        integer(t.get('left'), 0, max(LEFT.values()))
        need(t.get('q') in (0, 1), bad)
        integer(t.get('back'), 0, MAX_MOVES)
    esc = sh.get('esc')
    need(isinstance(esc, list) and len(esc) <= 2, bad)
    for x in esc:
        need(isinstance(x, dict) and x.get('id') in PC.ESCALATION_INDEX, bad)
        integer(x.get('at'), 0, MAX_MOVES)
        for k in ('a', 'b'):
            need(type(x.get(k)) is int and 0 <= x[k] < len(team), bad)
        need(x.get('pick') is None or x['pick'] in [o['id'] for o in PC.ESCALATION_INDEX[x['id']]['options']], bad)
