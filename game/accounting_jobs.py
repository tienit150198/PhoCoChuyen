"""💼 Việc làm kế toán: what the accounting school (game/accounting_school.py) opens in the town.

Owner 03/10: "coi code kế toán thông tư 99, làm xong giới thiệu việc làm ở đâu nữa nhé, với check kiến thức này kia,
bắt học thi qua mới làm được nhé, và ở đó kế toán lương x3 bình thường, đôi khi lễ tăng lên x5".

* Gate (story mode, journey.gate): an accounting workplace takes you once you hold its course certificate (JOBS):
  Mây Tre Xanh (corp_accounting) the basic one, Sông Hồng Group (group_accounting) the Việt Nam enterprise (TT99) one.
  The certificate also opens the place before its chapter does (derived: nothing stored until the first shift there,
  see journey.after). Without it every command of that career is refused with the reason ('need_cert').
* Grandfathered: a save that already worked there (a shift opened, a task done, a paid day) or holds a job record in
  flight (hired, applying, offer) keeps the place without the exam. Derived from the save, nothing written: after
  this release nobody uncertified can reach those states (the gate refuses every career command, the boss's lucky
  offer skips gated places).
* Entry check (kiểm tra kiến thức đầu ca): a certified accountant opens a shift (start_day) with CHECK_N quick questions
  (choice/number) of the exam bank of the place's course, CHECK_PASS right. Drawn from (seed, career, career day,
  attempt), so nothing is stored: as_job_check shows them, as_job_grade grades without changing the save (wrong
  answers point to the lessons to reread, never to the answer), and start_day carries {acct_check: {attempt,
  answers}} and is graded again by the server. A failed check costs nothing; the next attempt draws other questions.
  Grandfathered players without the certificate work as before, at the plain salary and without the check.
* Pay: with the certificate the day's salary (and the school's practice salary) is X3 times the contract salary (the
  85 % probation rate first), X5 on a Vietnamese public holiday (VN time, HOLIDAYS), never above PAY_CAP a day. Only the
  salary row is multiplied: the weekly 🔥 x3 of game/x3_week.py pays on the shift's net, which engine.end_day sums
  before the salary is paid, so the two never multiply each other.
* MNL_HOLIDAY_OFF=1: no holiday rate (the tests set it so a wallet does not depend on the day they run).
"""
from __future__ import annotations

import datetime
import hashlib
import os
import random
import time

VN = datetime.timezone(datetime.timedelta(hours=7))
JOBS = {'corp_accounting': 'basic', 'group_accounting': 'vn_business'}   # career: the course certificate it needs
X3, X5 = 3, 5
PAY_CAP = 600           # xu a day: the top contract (120) × 5
CHECK_N, CHECK_PASS = 3, 2
CHECK_KINDS = ('choice', 'number')   # quick to answer on a phone: no account picker, no forms
ATTEMPTS = 1000         # attempt numbers 0..ATTEMPTS-1 (the client counts them; any one is a fair draw)

# Ngày nghỉ lễ (Bộ luật Lao động 2019, Điều 112). Solar days every year; the lunar ones (Tết Nguyên đán: the last day
# of the old year + mùng 1–4, 5 days; Giỗ Tổ Hùng Vương 10/3 âm lịch) and the day next to Quốc khánh (the law gives
# 2/9 and one adjacent day, fixed by the government each year) from a small table for 2026–2028, Gregorian dates.
SOLAR = {(1, 1): 'Tết Dương lịch', (4, 30): 'Ngày Giải phóng miền Nam 30/4', (5, 1): 'Ngày Quốc tế Lao động 1/5',
         (9, 2): 'Quốc khánh 2/9'}
TET = {2026: '2026-02-17', 2027: '2027-02-06', 2028: '2028-01-26'}          # mùng 1 Tết
GIO_TO = {2026: '2026-04-26', 2027: '2027-04-16', 2028: '2028-04-04'}       # 10/3 âm lịch
QUOC_KHANH_NEXT = {2026: '2026-09-01', 2027: '2027-09-03', 2028: '2028-09-01'}


def _table() -> dict:
    out = {}
    for y, d in TET.items():
        day1 = datetime.date.fromisoformat(d)
        for k in range(-1, 4):
            out[(day1 + datetime.timedelta(days=k)).isoformat()] = 'Tết Nguyên đán'
    for y, d in GIO_TO.items():
        out[d] = 'Giỗ Tổ Hùng Vương'
    for y, d in QUOC_KHANH_NEXT.items():
        out[d] = 'Quốc khánh 2/9'
    return out


HOLIDAYS = _table()


def now() -> float:
    return time.time()


def holiday(t: float | None = None) -> str | None:
    """The public holiday of this VN day, or None."""
    if os.environ.get('MNL_HOLIDAY_OFF') == '1':
        return None
    d = datetime.datetime.fromtimestamp(now() if t is None else t, VN).date()
    return SOLAR.get((d.month, d.day)) or HOLIDAYS.get(d.isoformat())


def _school():
    from . import accounting_school
    return accounting_school


def _content():
    from . import accounting_content
    return accounting_content


def cert_of(career: str) -> str | None:
    return JOBS.get(career)


def certified(s: dict, career: str) -> bool:
    cid = JOBS.get(career)
    return bool(cid) and _school().certified(s, cid)


def multiplier(s: dict, career: str, t: float | None = None) -> int:
    """The day's salary multiplier at this place: 1 without its certificate (or elsewhere), X3, or X5 on a holiday."""
    if not certified(s, career):
        return 1
    return X5 if holiday(t) else X3


def pay(base: int, m: int) -> int:
    """A day's salary at multiplier m (base: the contract salary, probation rate already applied)."""
    return min(PAY_CAP, base * m) if m > 1 else base


def grandfathered(s: dict, career: str) -> bool:
    """Worked there before the exam rule (see the module notes): derived from the save, nothing stored."""
    c = (s.get('careers') or {}).get(career)
    if not isinstance(c, dict):
        return False
    job = c.get('job') if isinstance(c.get('job'), dict) else {}
    return (c.get('started') is True or job.get('status') in ('hired', 'applying', 'offer')
            or int(job.get('days_worked') or 0) > 0 or int((c.get('metrics') or {}).get('served') or 0) > 0)


def _story(s: dict) -> bool:
    return bool((s.get('journey') or {}).get('story'))


def can_work(s: dict, career: str) -> tuple[bool, str]:
    """(ok, why): may this save work at `career`? Only accounting places in the story have a rule."""
    if career not in JOBS or not _story(s) or certified(s, career) or grandfathered(s, career):
        return True, ''
    name = _school().course(JOBS[career])['name']
    return False, f'Thi đạt chứng nhận “{name}” ở Học kế toán rồi mới nhận việc ở đây nhé.'


def opens(s: dict, career: str) -> bool:
    """The certificate opens the place before its chapter (story)."""
    return career in JOBS and certified(s, career)


def opened(s: dict) -> list:
    return [cid for cid in JOBS if cid in (s.get('careers') or {}) and opens(s, cid)]


def check_needed(s: dict, career: str) -> bool:
    """A certified accountant's shift opens with the knowledge check (story only)."""
    return career in JOBS and _story(s) and certified(s, career)


# ---------------------------------------------------------------- the entry check
def _bank(career: str) -> list:
    return [q for q in _content().EXAM_BANK[JOBS[career]] if q['kind'] in CHECK_KINDS]


def draw(s: dict, career: str, day: int, attempt: int) -> list:
    """CHECK_N question ids from different chapters where it can, fixed by (seed, career, day, attempt)."""
    seed = (s.get('journey') or {}).get('seed', 0)
    rng = random.Random(hashlib.sha256(f'acct-check|{seed}|{career}|{day}|{attempt}'.encode()).hexdigest())
    bank = _bank(career)
    rng.shuffle(bank)
    chosen, chapters = [], set()
    for q in bank:
        if q.get('chapter_id') not in chapters:
            chosen.append(q['id'])
            chapters.add(q.get('chapter_id'))
        if len(chosen) == CHECK_N:
            break
    chosen += [q['id'] for q in bank if q['id'] not in chosen][:CHECK_N - len(chosen)]
    return chosen


def _attempt(p: dict) -> int:
    from .engine import integer
    return integer(p.get('attempt', 0), 0, ATTEMPTS - 1)


def _career(s: dict, p: dict) -> str:
    from .engine import need
    cid = p.get('career')
    need(cid in JOBS and cid in (s.get('careers') or {}), 'Nơi làm việc kế toán không hợp lệ.')
    return cid


def grade(s: dict, career: str, check) -> dict:
    """{passed, right, total, need, review}: a check paper {attempt, answers{qid: answer}} for today's shift."""
    from .engine import need
    school = _school()
    need(isinstance(check, dict) and set(check) == {'attempt', 'answers'}, 'Làm bài kiểm tra kiến thức đầu ca trước nhé.', 'acct_check')
    attempt = _attempt(check)
    qids = draw(s, career, s['careers'][career]['day'], attempt)
    answers = check['answers']
    need(isinstance(answers, dict) and set(answers) == set(qids), 'Bài kiểm tra không khớp đề hôm nay. Mở lại bài kiểm tra nhé.', 'acct_check')
    bank = {q['id']: q for q in _bank(career)}
    lessons = _content().LESSONS
    right, review = 0, []
    for qid in qids:
        q = bank[qid]
        need(school._shape(q, answers[qid]), 'Câu trả lời chưa đúng định dạng.')
        if school._check(q, answers[qid]):
            right += 1
        elif q.get('lesson_id') in lessons and all(r['lesson'] != q['lesson_id'] for r in review):
            review.append(dict(lesson=q['lesson_id'], title=lessons[q['lesson_id']]['title']))
    return dict(passed=right >= CHECK_PASS, right=right, total=len(qids), need=CHECK_PASS, attempt=attempt, review=review)


def gate_start(s: dict, career: str, p: dict) -> None:
    """start_day of a certified accountant: the check paper rides in p['acct_check'] (journey.gate)."""
    from .engine import need
    if not check_needed(s, career):
        return
    need('acct_check' in p, f'Làm {CHECK_N} câu kiểm tra kiến thức đầu ca rồi mở ca nhé.', 'acct_check')
    g = grade(s, career, p['acct_check'])
    need(g['passed'], f'Bài kiểm tra đúng {g["right"]}/{g["total"]} câu, cần {g["need"]}. Xem lại bài gợi ý rồi làm bài khác nhé.', 'acct_check')


def check_view(s: dict, career: str, attempt: int) -> dict:
    school = _school()
    bank = {q['id']: q for q in _bank(career)}
    c = s['careers'][career]
    return dict(career=career, place=_place(career), day=c['day'], attempt=attempt, need=CHECK_PASS, total=CHECK_N,
                course=JOBS[career], questions=[school._safe_question(bank[qid]) for qid in draw(s, career, c['day'], attempt)],
                x=multiplier(s, career), holiday=holiday())


def action(s: dict, name: str, p: dict) -> dict:
    """as_job_check {career, attempt}: the questions; as_job_grade {career, attempt, answers}: a grade. Neither
    changes the save; start_day grades the paper again."""
    from .engine import need
    career = _career(s, p)
    need(check_needed(s, career), 'Ca này không cần kiểm tra kiến thức.')
    need(not s['careers'][career]['open'], 'Ca đã mở rồi.')
    if name == 'as_job_check':
        return dict(message='', acct_check=check_view(s, career, _attempt(p)))
    if name == 'as_job_grade':
        g = grade(s, career, dict(attempt=p.get('attempt', 0), answers=p.get('answers')))
        msg = (f'Đúng {g["right"]}/{g["total"]} câu. Vào ca thôi!' if g['passed'] else
               f'Đúng {g["right"]}/{g["total"]} câu, cần {g["need"]}. Xem lại bài gợi ý rồi làm bài khác nhé.')
        return dict(message=msg, acct_grade=g)
    need(False, 'Thao tác học kế toán không tồn tại.')


# ---------------------------------------------------------------- views
def _place(career: str) -> str:
    from .content import CAREER_META
    return CAREER_META.get(career, {}).get('place', career)


def summary(s: dict) -> dict:
    """public_state['accounting_school']['jobs'], on every command (the block has a 300-byte budget): {places: {career:
    [ok, multiplier, check]} for the places with a rule today (shut, ×3/×5, or a check before the shift), holiday: the
    day's holiday name, only on one}. The client words the reason from the certificate (v4/acct-jobs.js)."""
    places = {}
    for cid in JOBS:
        if cid not in (s.get('careers') or {}):
            continue
        ok, m, check = can_work(s, cid)[0], multiplier(s, cid), check_needed(s, cid)
        if not ok or m > 1 or check:
            places[cid] = [int(ok), m, int(check)]
    out = dict(places=places)
    h = holiday()
    if h:
        out['holiday'] = h
    return out


def referral(s: dict) -> list:
    """Giới thiệu việc làm: every accounting place, what it needs, what it pays (x3, x5 on holidays), its postings."""
    from .employment import postings
    from .content import CAREER_META
    j = s.get('journey') or {}
    rows = []
    for cid, course in JOBS.items():
        if cid not in (s.get('careers') or {}):
            continue
        c = s['careers'][cid]
        job = c.get('job') or {}
        ok = certified(s, cid)
        rows.append(dict(career=cid, place=_place(cid), short=CAREER_META.get(cid, {}).get('short', ''), course=course,
                         course_name=_school().course(course)['name'], certified=ok, x=multiplier(s, cid),
                         hired=job.get('status') == 'hired', employer=job.get('employer'),
                         open=not j.get('story') or cid in (j.get('unlocked') or ()) or ok,
                         postings=[dict(id=p['id'], org=p['org'], title=p['title'], salary=list(p['salary']),
                                        paid=[min(PAY_CAP, v * X3) for v in p['salary']],
                                        holiday=[min(PAY_CAP, v * X5) for v in p['salary']]) for p in postings(cid)]))
    return rows
