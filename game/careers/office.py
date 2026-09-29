"""Office day shared by the three office careers (corp_accounting, tax_payroll,
group_accounting). Not a career itself (it is not listed in careers.ORDER).

A visible office clock (08:00 → 17:30, lunch at 12:00, overtime until 20:00),
a deadline for every dossier, the boss's trust (0–100) and small fines that are
always capped by the wallet. The state lives in the career data under 'office';
old saves get it through ensure(). Every change goes through these helpers so the
rules stay the same in all three careers.
"""
from __future__ import annotations
import copy
from . import kit

OPEN, LUNCH, CLOSE, LOCK = 480, 720, 1050, 1200      # 08:00, 12:00, 17:30, 20:00
LUNCH_MIN = 60
DUE = (630, 720, 900, 990)                             # 10:30, 12:00, 15:00, 16:30 by order in the day
MORE_WORK_WINDOW = 150                                 # a job taken mid-day is due 2.5 hours later
CARRY_DUE = 600                                        # yesterday's leftovers are due 10:00
TIRED_MIN = 30                                         # the morning after overtime starts at 08:30
TRUST_START = 50
TRUST_HIGH, TRUST_LOW = 75, 35
TRUST_BONUS = 5                                        # xu per dossier while trust is high
LOW_TRUST_REVIEW = 20                                  # minutes the boss spends re-checking when trust is low
LATE_CUT = 8                                           # xu taken off a dossier bonus when it is late
NOTES = 10

# Minutes each kind of work takes on the office clock.
COST = dict(open=5, ref=6, hint=5, step=20, wrong=15, stamp=10, circle=1, submit=10, claim=15, pair=5, tag=5, flag=4,
            overtime=0)


def initial() -> dict:
    return dict(day=0, clock=OPEN, ot=False, tired=0, trust=TRUST_START, streak=0, ontime=0, late=0, fines=0,
                ot_days=0, day_trust=0, day_fines=0, day_late=0, notes=[])


def ensure(d: dict) -> dict:
    """The office sub-state of a career's data (created for saves made before it existed)."""
    o = d.get('office')
    if not isinstance(o, dict):
        o = d['office'] = initial()
    for k, v in initial().items():
        o.setdefault(k, v)
    return o


def hhmm(minutes: int) -> str:
    m = max(0, int(minutes))
    return f'{m // 60:02d}:{m % 60:02d}'


def begin(o: dict, day: int, late_start: int = 0) -> None:
    """Start a new office day (from on_start; also lazily for old saves)."""
    tired = TIRED_MIN if o['tired'] == day else 0
    o.update(day=day, clock=OPEN + tired + max(0, int(late_start)), ot=False, day_trust=0, day_fines=0, day_late=0)


def sync(o: dict, day: int, late_start: int = 0) -> None:
    if o['day'] != day:
        begin(o, day, late_start)


def limit(o: dict) -> int:
    return LOCK if o['ot'] else CLOSE


def closed(o: dict) -> bool:
    return o['clock'] >= limit(o)


def need_open(o: dict) -> None:
    if o['clock'] >= LOCK:
        kit.need(False, 'Đã 20:00, văn phòng khóa cửa. Khép ngày để về nghỉ nhé — việc dở được giữ nguyên.', 'office_closed')
    kit.need(not closed(o), 'Đã 17:30, hết giờ hành chính. Chọn “Ở lại tăng ca” hoặc khép ngày — việc dở được giữ nguyên.',
             'office_closed')


def spend(o: dict, minutes: int) -> str:
    """Advance the clock for one piece of work. Returns a short note (lunch) or ''."""
    need_open(o)
    before = o['clock']
    after = before + max(0, int(minutes))
    note = ''
    if before < LUNCH <= after:
        after += LUNCH_MIN
        note = '🍜 Nghỉ trưa 12:00–13:00.'
    o['clock'] = min(LOCK, after)
    return note


def trust(o: dict, delta: int) -> int:
    old = o['trust']
    o['trust'] = max(0, min(100, old + int(delta)))
    o['day_trust'] += o['trust'] - old
    return o['trust'] - old


def trust_label(v: int) -> str:
    return 'Rất tin bạn' if v >= TRUST_HIGH else 'Tin tưởng' if v >= 50 else 'Đang dè dặt' if v >= TRUST_LOW else 'Lo ngại'


def note(o: dict, day: int, text: str, kind: str = 'info') -> None:
    o['notes'] = (o['notes'] + [dict(day=int(day), text=str(text)[:200], kind=kind)])[-NOTES:]


def fine(s: dict, c: dict, o: dict, amount: int, reason: str, ref: str | None = None) -> int:
    """Take a fine from the wallet, never more than what is there. Returns the amount taken."""
    amount = min(max(0, int(amount)), max(0, c['money']))
    if amount:
        kit.money(s, c, -amount, reason, ref, 'penalty')
        o['fines'] += amount
        o['day_fines'] += amount
    return amount


def overtime(s: dict, c: dict, o: dict, pay: int, crunch: bool) -> str:
    kit.need(not o['ot'], 'Hôm nay bạn đã ở lại tăng ca rồi.')
    kit.need(o['clock'] >= CLOSE - 60, 'Tăng ca đăng ký từ 16:30 nhé — giờ vẫn còn trong giờ hành chính.')
    o['ot'] = True
    o['tired'] = c['day'] + 1
    o['ot_days'] += 1
    if pay:
        kit.money(s, c, int(pay), 'Phụ cấp tăng ca', None, 'overtime')
    extra = ''
    if crunch:
        trust(o, 3)
        extra = ' Ngày cuối kỳ mà ở lại cùng cả phòng — sếp ghi nhận (+3 tin tưởng).'
    note(o, c['day'], 'Ở lại tăng ca tới 20:00.', 'ot')
    return f'Đã đăng ký tăng ca tới 20:00 · phụ cấp +{pay} xu. Sáng mai bạn vào muộn 30 phút cho đỡ mệt.' + extra


def due_for(c: dict, t: dict, o: dict) -> int:
    """Deadline (minutes) of a new task: by its order among today's jobs, or 2.5 h after a mid-day request."""
    if o['day'] == c['day'] and c.get('open') and o['clock'] > OPEN + TIRED_MIN:
        return min(LOCK, max(o['clock'] + MORE_WORK_WINDOW, DUE[0]))
    earlier = [x for x in c['tasks'] if x.get('career') == t['career'] and x.get('day') == t['day'] and x['id'] < t['id']]
    return DUE[len(earlier)] if len(earlier) < len(DUE) else CLOSE


def set_due(c: dict, t: dict, o: dict) -> None:
    t['due'] = due_for(c, t, o)
    t['due_day'] = t['day']


def carry(c: dict, career: str, o: dict) -> int:
    """At the start of a day, leftovers from earlier days are due at 10:00 today. Returns how many."""
    n = 0
    for t in c['tasks']:
        if t.get('career') == career and t['status'] not in ('completed', 'referred', 'cancelled') and t['day'] < c['day']:
            t['due'] = CARRY_DUE
            t['due_day'] = c['day']
            n += 1
    return n


def is_late(t: dict, o: dict, day: int) -> bool:
    if type(t.get('due')) is not int:
        return False
    return day > t.get('due_day', day) or o['clock'] > t['due']


def settle(o: dict, t: dict, day: int) -> tuple[bool, int, str]:
    """A dossier is handed in: lateness, bonus change and a short note. Updates trust and streak."""
    late = is_late(t, o, day)
    if late:
        o['late'] += 1
        o['day_late'] += 1
        o['streak'] = 0
        trust(o, -3)
        return True, -LATE_CUT, f'Trễ hạn {hhmm(t["due"])} (−{LATE_CUT} xu, sếp −3 tin tưởng).'
    if type(t.get('due')) is int:
        o['ontime'] += 1
        o['streak'] += 1
        trust(o, 2)
        bonus = TRUST_BONUS if o['trust'] >= TRUST_HIGH else 0
        return False, bonus, 'Kịp hạn ✓' + (f' · thưởng tin cậy +{bonus} xu' if bonus else '')
    return False, 0, ''


def review_cost(o: dict) -> int:
    """Low trust: the boss re-checks every page before signing."""
    return LOW_TRUST_REVIEW if o['trust'] < TRUST_LOW else 0


def close_day(c: dict, career: str, o: dict) -> dict:
    """End of day: unfinished work costs a little trust. Returns the office part of the summary."""
    left = [t for t in c['tasks'] if t.get('career') == career and t['status'] not in ('completed', 'referred', 'cancelled')]
    lost = trust(o, -min(6, 2 * len(left))) if left else 0
    return dict(clock=hhmm(o['clock']), trust=o['trust'], trust_label=trust_label(o['trust']), trust_change=o['day_trust'],
                fines=o['day_fines'], late=o['day_late'], overtime=o['ot'], carried=len(left), carried_trust=lost)


def public(o: dict, day: int) -> dict:
    today = o['day'] == day
    clock = o['clock'] if today else OPEN + (TIRED_MIN if o['tired'] == day else 0)
    ot = o['ot'] if today else False
    lim = LOCK if ot else CLOSE
    return dict(clock=clock, time=hhmm(clock), limit=lim, limit_time=hhmm(lim), closed=clock >= lim, locked=clock >= LOCK,
                overtime=ot, can_overtime=today and not ot and clock >= CLOSE - 60, lunch=clock < LUNCH,
                trust=o['trust'], trust_label=trust_label(o['trust']), streak=o['streak'], fines=o['fines'],
                ontime=o['ontime'], late=o['late'], notes=list(o['notes'][-4:]), tired=o['tired'] == day)


def public_task(t: dict, o: dict, day: int) -> dict | None:
    if type(t.get('due')) is not int:
        return None
    clock = o['clock'] if o['day'] == day else OPEN
    overdue = day > t.get('due_day', day) or clock > t['due']
    left = t['due'] - clock if not overdue else 0
    return dict(due=t['due'], time=hhmm(t['due']), overdue=overdue, soon=not overdue and left <= 45, left=max(0, left))


# ---------------------------------------------------------------- first dossier: a coached screen
# A new player's first dossier in an office career (nothing handed in yet) is a guided tutorial: the
# screen lights the right option, the right cell and the right stamp. The office screens only ever
# show documents, and the answers are judgements the client cannot derive from them, so the view
# carries them for that first dossier only (data['coach'], keyed by task id). Rules stay the same.
def first_dossier(c: dict) -> bool:
    return not (c.get('metrics') or {}).get('served')


def coach_step(t: dict) -> dict | None:
    """The current step of a step-by-step dossier and its answer key."""
    proc, ps = t.get('proc') or [], t.get('proc_state') or {}
    at = ps.get('at', 0)
    if at >= len(proc):
        return None
    return dict(step=proc[at]['id'], key=copy.deepcopy(proc[at]['_key']))


def coach(c: dict, career: str, fn) -> dict:
    if not first_dossier(c):
        return {}
    out = {}
    for t in c.get('tasks') or []:
        if t.get('career') == career and t.get('known') and t['status'] not in ('completed', 'referred', 'cancelled'):
            v = fn(t)
            if v:
                out[t['id']] = v
    return out


def validate(o) -> None:
    kit.need(isinstance(o, dict) and set(initial()) <= set(o), 'Sổ giờ làm việc thiếu dữ liệu.')
    kit.integer(o['day'], 0, 10 ** 7)
    kit.integer(o['clock'], OPEN, LOCK)
    kit.integer(o['tired'], 0, 10 ** 7)
    kit.integer(o['trust'], 0, 100)
    for k in ('streak', 'ontime', 'late', 'fines', 'ot_days', 'day_fines', 'day_late'):
        kit.integer(o[k], 0, 10 ** 9)
    kit.integer(o['day_trust'], -100, 100)
    kit.need(type(o['ot']) is bool, 'Cờ tăng ca sai.')
    kit.need(isinstance(o['notes'], list) and len(o['notes']) <= NOTES, 'Ghi chú giờ làm sai.')
    for n in o['notes']:
        kit.need(isinstance(n, dict) and set(n) == {'day', 'text', 'kind'}, 'Ghi chú giờ làm sai.')
        kit.integer(n['day'], 0, 10 ** 7)
        kit.text(n['text'], 200)
        kit.text(n['kind'], 20)


def validate_task(t: dict) -> None:
    if 'due' in t or 'due_day' in t:
        kit.integer(t.get('due'), OPEN, LOCK)
        kit.integer(t.get('due_day'), 1, 10 ** 7)


_CHAIN: dict = {}


def _pick(career: str, day: int, rows: list, forced: dict | None, recent: list, intro: dict | None) -> str:
    if intro and day in intro:
        return intro[day]
    phase = (day - 1) % 5
    if forced and phase in forced and day > 1:
        return forced[phase]
    pool = [r for r in rows if not r.get('forced_only') and r.get('min_day', 1) <= day] or rows[:1]
    fresh = [r for r in pool if r['id'] not in recent] or [r for r in pool if r['id'] not in recent[-1:]] or pool
    total = sum(r.get('weight', 1) for r in fresh)
    x = kit.rng(career, 'office-day', day).random() * total
    for r in fresh:
        x -= r.get('weight', 1)
        if x < 0:
            return r['id']
    return fresh[-1]['id']


def mod_of(career: str, day: int, rows: list, forced: dict | None = None, intro: dict | None = None) -> dict:
    """Luck of the day, deterministic from the day: forced[phase] wins (e.g. month-end crunch);
    `intro` fixes the first days so each twist shows up early; later a weighted pick avoids the
    modifiers of the two previous days."""
    chain = _CHAIN.setdefault(career, [None])
    day = max(1, int(day))
    while len(chain) <= day:
        d = len(chain)
        chain.append(_pick(career, d, rows, forced, [x for x in chain[max(1, d - 2):d] if x], intro))
    return next(r for r in rows if r['id'] == chain[day])
