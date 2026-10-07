"""⏱️ Tăng ca ×2 and ⚡ Thưởng năng suất 30%.

Owner 07/10: "bạn nào mà trong 1 ngày làm nhiều việc thì thưởng OT là lương x2, nhiều nữa thì cộng 30% năng suất …
để người chơi có tiền ổn hơn nhé."

A shift (one career day, c['day']) counts the player's own paid jobs: the cash book's "Hoàn thành: …" rows of that day.
engine.task_done writes one for every finished job that pays; staff-run orders, a manager shift's team and other
players' orders never write one, so they never count.

* Past the career's normal day (NORMAL: about the 65th percentile of paid jobs per worked day on production, 07/10),
  every further job finished well (status 'completed', paid, the fair grade of its review at least MIN_STARS) earns
  its pay once more: "⏱️ Tăng ca ×2", at most OT_MAX jobs a shift and JOB_CAP xu a job.
* Reaching the busy tier (BUSY: about the 88th percentile, never under NORMAL + GAP) adds, when the shift closes,
  PCT % of the day's job pay: "⚡ Thưởng năng suất 30%", at most DAY_CAP xu.
* Base job pay only: tips, the day's salary, the ×3/×5 accounting rate and promotion raises are never doubled. The
  🔥 x3 day (journey._end_of_day) figures its bonus on the day's net without these rows: no stacking.
* Paid like job pay, by the system: engine.money into the workplace fund. Category 'overtime' (the office's "Phụ cấp
  tăng ca" uses it too): never shop revenue, so no 4% period tax (a salaried career pays none anyway) and no owner tip
  on it. Each row has its own ref (ot2-<task id>, otp-<day>): nothing pays twice.
* Nothing in the save: the counts are read back from the cash book, whose rows of the last days are always kept
  (operations.trim_ledger). A save made with this reads under 1.9.9 (any ledger category passes there). Only jobs
  finished from now on pay: no back pay.
* A career without enough measured days, or a career added later, gets max(DEFAULT_NORMAL, its own planned jobs that
  day) and BUSY = NORMAL + GAP.
"""
from __future__ import annotations

PCT = 30            # ⚡ the busy tier's share of the day's job pay
OT_MAX = 3          # ⏱️ jobs a shift that pay ×2
JOB_CAP = 50        # the most one job's overtime adds (xu)
DAY_CAP = 60        # the most the productivity bonus adds (xu)
MIN_STARS = 3       # the job's fair grade (feedback 'fair') needed for overtime
SLOTS = 12          # jobs a career day can hand out (engine.MORE_DAY; task ids keep slot < 12)
DEFAULT_NORMAL = 4  # all careers together: p65 of paid jobs per worked day
GAP = 3             # the busy tier is at least this many jobs past the normal day

JOB = 'Hoàn thành:'           # engine.task_done's job pay row
OT_REF, PROD_REF = 'ot2-', 'otp-'
CATEGORY = 'overtime'

# Paid jobs per worked day, production 28/09–07/10 (96 786 shifts): p65, clamped to 2..SLOTS-OT_MAX.
NORMAL = {
    'milk_tea': 7, 'grocery': 4, 'delivery': 6, 'pet_care': 3, 'mother_baby': 3, 'cafe_bakery': 4, 'homestay': 3,
    'florist': 3, 'restaurant': 4, 'clothing': 6, 'customer_care': 4, 'salon': 3, 'teacher': 3, 'repair': 5,
    'pharmacy': 6, 'photobooth': 4, 'flight_attendant': 9, 'pilot': 8, 'pagoda': 9, 'fruit': 6, 'secretary': 9,
    'babysitter': 2, 'hr_admin': 9, 'homemaker': 7, 'accounting': 5, 'tra_da': 6, 'farm': 3, 'garbage': 3,
    'corp_accounting': 2, 'tax_payroll': 3, 'ice_cream': 9, 'tour_guide': 3, 'pet_shop': 3, 'nail': 2, 'giupviec': 2,
    'com': 6, 'drain': 3, 'naucom': 4, 'it_helpdesk': 9, 'group_accounting': 2, 'police': 7, 'pho': 3, 'nurse': 5,
    'lifeguard': 7, 'library': 2, 'oil': 8,
}
# p88 where it lies past NORMAL + GAP (elsewhere the busy tier is NORMAL + GAP).
BUSY = {'milk_tea': 12, 'naucom': 9, 'pho': 7, 'library': 6}


def _plan(c: dict, career: str) -> int:
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    if mod is None or not hasattr(mod, 'daily_task_count'):
        return 0
    try:
        return int(mod.daily_task_count(c['day']))
    except Exception:  # noqa: BLE001 - a threshold never breaks a command
        return 0


def thresholds(c: dict, career: str) -> tuple[int, int]:
    """(normal, busy): overtime from job normal+1, the productivity bonus from job `busy`."""
    n = NORMAL.get(career)
    if n is None:
        n = max(DEFAULT_NORMAL, _plan(c, career))
    n = max(1, min(int(n), SLOTS - OT_MAX))
    return n, min(SLOTS, max(BUSY.get(career, 0), n + GAP))


def today(c: dict) -> dict:
    """The open day's figures, read from the cash book: jobs (paid), pay (their base pay), ot (jobs paid ×2),
    ot_pay, prod (the productivity row, once the day closes)."""
    day = c.get('day')
    out = dict(jobs=0, pay=0, ot=0, ot_pay=0, prod=0)
    try:
        rows = c['ops']['finance']['ledger']
    except (KeyError, TypeError):
        return out
    for r in reversed(rows):
        if not isinstance(r, dict):
            continue
        d = r.get('day')
        if d != day:
            if type(d) is int and type(day) is int and d < day:
                break           # rows are written in day order: older days end the scan
            continue
        amount = r.get('amount')
        if type(amount) is not int or amount <= 0:
            continue
        ref = r.get('ref') or ''
        if str(r.get('reason') or '').startswith(JOB):
            out['jobs'] += 1
            out['pay'] += amount
        elif ref.startswith(OT_REF):
            out['ot'] += 1
            out['ot_pay'] += amount
        elif ref == f'{PROD_REF}{day}':
            out['prod'] += amount
    return out


def on_job(s: dict, c: dict, t: dict, reward: int, status: str, fair) -> int:
    """engine.task_done, after the job's pay and review: the overtime of this job (0 when none)."""
    if status != 'completed' or type(reward) is not int or reward <= 0 or t.get('player_order'):
        return 0
    if isinstance(fair, int) and fair < MIN_STARS:
        return 0
    n, _ = thresholds(c, t['career'])
    d = today(c)
    if d['jobs'] <= n or d['ot'] >= OT_MAX:
        return 0
    ref = OT_REF + str(t['id'])
    rows = c['ops']['finance']['ledger']
    if any(isinstance(r, dict) and r.get('ref') == ref for r in rows[-60:]):
        return 0
    bonus = min(JOB_CAP, reward)
    from . import engine as e
    e.money(s, c, bonus, f'⏱️ Tăng ca ×2 · việc thứ {d["jobs"]}', ref, CATEGORY)
    return bonus


def on_close(s: dict, c: dict, career: str) -> dict | None:
    """engine end_day, before the day's figures: the productivity bonus, and the day summary's ⏱️ part."""
    n, busy = thresholds(c, career)
    d = today(c)
    if d['jobs'] <= n and not d['ot_pay']:
        return None
    prod = d['prod']
    if d['jobs'] >= busy and not prod:
        prod = min(DAY_CAP, d['pay'] * PCT // 100)
        if prod > 0:
            from . import engine as e
            e.money(s, c, prod, f'⚡ Thưởng năng suất {PCT}% · {d["jobs"]} việc', f'{PROD_REF}{c["day"]}', CATEGORY)
    return dict(jobs=d['jobs'], normal=n, busy=busy, ot=d['ot'], ot_pay=d['ot_pay'], prod=prod, pct=PCT,
                total=d['ot_pay'] + prod)


def public(c: dict, career: str) -> dict | None:
    """The work screen's chip (view only, never saved): None while the shift is closed."""
    if not c.get('open'):
        return None
    n, busy = thresholds(c, career)
    d = today(c)
    return dict(jobs=d['jobs'], normal=n, busy=busy, ot=d['ot'], max=OT_MAX, pay=d['ot_pay'], pct=PCT)
