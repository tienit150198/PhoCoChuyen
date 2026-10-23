"""🏫 Trường học: 🎓 Đại học Phố Mây (many majors) and ✈️ Du học một học kỳ (story mode).

Owner 23/10: "du lịch trải nghiệm thật thì bạn làm cho nó đi học thật nữa nhé, nhiều ngành cũng thế xử lý luôn";
feedback #315 (du học Trung Quốc) and #322 (trường học nhiều môn, đại học nhiều ngành). Catalogue:
game/school_content.py; question banks: game/school_bank_*.py (shapes game/school_q.py).

One program at a time (a major, or a term abroad); more majors one after another (each its own degree).
A program is học kỳ (semesters) of three subjects. A semester runs on the life-day clock with a weekly timetable:
the day the semester starts is Thứ 2; every day but Chủ nhật has two class slots (TIMETABLE), and a slot whose subject
has all its classes becomes a free slot (any subject still short of classes). Per subject:
  * CLASSES classes (one a slot, at most PER_DAY a life day, a subject once a day): class k is lesson k of the subject,
    its key lines then three quick questions (attendance counts whatever the answers: a wrong answer only teaches);
  * homework (three questions drawn from the subject's ten) once two classes are done: once a life day, best kept;
  * the exam (five questions drawn from the ten) once every class and one homework are done: pass from EXAM_PASS
    right answers; a failed exam is retaken the next life day for free (a new paper), best kept.
  The subject's mark (thang 10) = 10 % chuyên cần + 20 % câu hỏi trên lớp + 20 % bài tập + 50 % thi, then the letter
  and the 4-point scale (GRADES). GPA: the average of the program's subjects (all three credits).
A semester whose three subjects are passed: the next one opens after its tuition (jr_sch_next), the last one graduates.
Graduation: a degree {d, g, gpa, date, serial, ev} with a class (CLASSES by GPA) and, for good:
  * 🎓 every own earning at a workplace of the program's `careers` +pct % (CLASSES: 8–15 %), in game/pay_boost.py (the
    same rows as 💰 Tiền công; the best degree for that place counts, never two);
  * the place's hire chance as with its certificate (game/employment.py _cert_roll) and the 🎓 row of the third
    promotion step (game/promotion.py);
  * the place opens before its chapter (journey.gate / is_unlocked / public, career_locks);
  * titles 🎓 Cử nhân, 📚 Song bằng, 🏅 Thủ khoa, 🌏 Du học sinh (journey TITLES 'h_bachelor', 'h_double', 'h_top',
    'h_overseas'); Xuất sắc: a scholarship of SCHOLAR_PCT % of the tuition paid back to the wallet.
  * a term abroad also counts as a ✈️ Du học degree of its country (game/abroad.py degrees: hired pay +10/15/20 %).
A term abroad starts with the application: tick the right papers (jr_sch_apply, a mistake costs nothing), tuition +
visa paid, a short visa interview (jr_sch_visa, retried freely), the flight (jr_sch_fly), then the semester; there a
part-time job (jr_sch_job, once a life day, JOB_PAY xu) and culture events (jr_sch_event, one a life day, every choice
is a memory). The workplaces at home stay open (someone at home keeps an eye on them): a life day still passes when a
shift closes, as everywhere in the journey.
Leaving (jr_sch_drop): half of the classes not taken this semester comes back; a major keeps its finished semesters
(bảo lưu: enrolling again resumes there).

Commands jr_sch_* (game/journey.py), each result carrying `school` (the page's view, never in public_state):
  jr_sch_view {view?}        nothing changes
  jr_sch_enrol {program, pay?}            a major: the semester's tuition
  jr_sch_next {pay?}                      the next semester's tuition
  jr_sch_apply {program, docs, pay?}      a term abroad: tuition + visa
  jr_sch_visa {option}  jr_sch_fly        the interview, the flight
  jr_sch_class {subject, answers}         today's class of that subject
  jr_sch_hw {subject, answers}            homework
  jr_sch_exam {subject, answers}          the exam
  jr_sch_job {option}  jr_sch_event {event, option}   abroad / at school
  jr_sch_drop {confirm}
  `view` {open: 'class'|'hw'|'exam'|'job', subject?}: the questions to show (no key), drawn as the next command grades.
Answers: a choice → the option's index `i` as listed; true/false → true/false; order → the items' `i` in the order
picked; a number → an integer.

Save journey['school'] (absent until the first command that changes something; journey.validate allows extra keys,
so an older build keeps it and ignores it):
  {v, cur: None | CUR, deg: {pid: {d, g, gpa, date, serial, ev}}, kept: {pid: {sid: mark}}}
  CUR = {p, sem, ph ('visa'|'fly'|'study'|'break'), start, fee, paid, day, nt, at: [sid], sub: {sid: SUB},
         marks: {sid: mark 0–100}, ev: [event ids], evd, job, jn}
  SUB = {a, cs, hw, hwn, hwd, ex, tries, exd}
"""
from __future__ import annotations

import hashlib
import random
import re
from fractions import Fraction

from . import price_index as pi
from . import school_content as C
from .school_q import questions as _questions

VERSION = 1
KEY = 'school'
PROGRAMS = {p['id']: p for p in C.MAJORS + C.TERMS}
MAJOR_IDS = tuple(p['id'] for p in C.MAJORS)
TERM_IDS = tuple(p['id'] for p in C.TERMS)
SUBJECTS = C.SUBJECTS
CLASSES_N = 3          # classes per subject (= its lessons)
PER_DAY = 2            # classes a life day
CLASS_Q = 3            # questions a class
HW_Q = 3               # questions of a homework
EXAM_Q = 5             # questions of an exam
EXAM_PASS = 3          # right answers to pass it
CREDITS = 3            # tín chỉ a subject
SCHOLAR_PCT = 20       # Xuất sắc: this share of the tuition paid comes back
JOB_PAY = (20, 30)     # xu of a part-time shift abroad (an answer that misses, a good one); earnings: never indexed
JOB_MAX = 12           # part-time shifts a term
WEEKDAYS = ('Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật')
TIMETABLE = ((0, 1), (2, 0), (1, 2), (0, 1), (2, 0), (1, 2), ())   # subject indexes of the semester, by weekday
SUNDAY = 6
# (from mark ×10, letter, points ×100): the Vietnamese credit scale
GRADES = ((85, 'A', 400), (80, 'B+', 350), (70, 'B', 300), (65, 'C+', 250), (55, 'C', 200), (50, 'D+', 150),
          (40, 'D', 100), (0, 'F', 0))
# (id, name, from GPA ×100, 🎓 % at the program's workplaces)
CLASSES = (('xuat_sac', 'Xuất sắc', 360, 15), ('gioi', 'Giỏi', 320, 12), ('kha', 'Khá', 250, 10), ('tb', 'Trung bình', 0, 8))
CLASS_IDS = tuple(c[0] for c in CLASSES)
CLASS_NAME = {c[0]: c[1] for c in CLASSES}
CLASS_PCT = {c[0]: c[3] for c in CLASSES}
TITLE_FIRST, TITLE_TWO, TITLE_TOP, TITLE_ABROAD = 'h_bachelor', 'h_double', 'h_top', 'h_overseas'
DOC_NEED = frozenset(d for d, _, ok in C.DOCS if ok)
DOC_IDS = tuple(d for d, _, _ in C.DOCS)
PHASES = ('visa', 'fly', 'study', 'break')
BLOCK_KEYS = frozenset({'v', 'cur', 'deg', 'kept'})
CUR_KEYS = frozenset({'p', 'sem', 'ph', 'start', 'fee', 'paid', 'day', 'nt', 'at', 'sub', 'marks', 'ev', 'evd', 'job', 'jn'})
SUB_KEYS = frozenset({'a', 'cs', 'hw', 'hwn', 'hwd', 'ex', 'tries', 'exd'})
DEG_KEYS = frozenset({'d', 'g', 'gpa', 'date', 'serial', 'ev'})
_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')


def _core():
    from . import engine
    return engine


def tuition(pid: str) -> int:
    return pi.price(PROGRAMS[pid]['fee'], luxury=False)


def visa_fee(pid: str) -> int:
    p = PROGRAMS[pid]
    return pi.price(p['visa'], luxury=False) if p['kind'] == 'abroad' else 0


def events_of(p: dict) -> tuple:
    return p['events'] if p['kind'] == 'abroad' else C.UNI_EVENTS


def initial() -> dict:
    return dict(v=VERSION, cur=None, deg={}, kept={})


def _sub0() -> dict:
    return dict(a=0, cs=0, hw=-1, hwn=0, hwd=0, ex=-1, tries=0, exd=0)


def _story(s: dict) -> bool:
    j = s.get('journey')
    return isinstance(j, dict) and bool(j.get('story'))


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _block(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial()
    return j[KEY]


def _seed(s: dict) -> int:
    return int((s.get('journey') or {}).get('seed') or 0)


def _rng(*parts) -> random.Random:
    return random.Random(hashlib.sha256('|'.join(map(str, ('school',) + parts)).encode()).hexdigest())


# ---------------------------------------------------------------- what the rest of the game reads
def held(s: dict) -> dict:
    """{program id: degree} of the programs this build knows (story mode only)."""
    b = get(s) if _story(s) else None
    return {k: v for k, v in ((b or {}).get('deg') or {}).items() if k in PROGRAMS and isinstance(v, dict)}


def degree_for(s: dict, career: str) -> str | None:
    """The held degree that helps `career` most (its 🎓 %), or None."""
    best = None
    for pid, d in held(s).items():
        if career in PROGRAMS[pid]['careers']:
            pct = CLASS_PCT.get(d.get('g'), 0)
            if best is None or pct > best[0]:
                best = (pct, pid)
    return best[1] if best else None


def pay_pct(s: dict, career: str) -> int:
    """🎓 % on every own earning at `career` (game/pay_boost.py pcts): the best degree for that place."""
    pid = degree_for(s, career)
    return CLASS_PCT.get(held(s)[pid]['g'], 0) if pid else 0


def opens(s: dict, career: str) -> bool:
    """A degree opens its workplaces before their chapter (journey.gate, is_unlocked, public; career_locks)."""
    return degree_for(s, career) is not None


def opened(s: dict) -> list[str]:
    return [cid for cid in (s.get('careers') or {}) if opens(s, cid)]


def abroad_countries(s: dict) -> set[str]:
    """The countries of the terms abroad graduated ('dh_han_quoc' → 'han_quoc'): game/abroad.py degrees."""
    return {pid[3:] for pid in held(s) if PROGRAMS[pid]['kind'] == 'abroad'}


def majors_for(career: str) -> list[str]:
    """The names of the programs whose degree helps `career` (the lock line of game/career_locks.py)."""
    return [p['name'] for p in C.MAJORS + C.TERMS if career in p['careers']]


def degree_name(pid: str) -> str:
    p = PROGRAMS[pid]
    return f'Bằng cử nhân {p["name"]}' if p['kind'] == 'uni' else f'Bằng du học {p["country"]} · {p["city"]}'


# ---------------------------------------------------------------- marks
def mark(rec: dict) -> int:
    """The subject's mark ×10 (0–100): 10 % chuyên cần, 20 % câu trên lớp, 20 % bài tập, 50 % thi, rounded half up."""
    x = (Fraction(rec['a'] * 10, CLASSES_N) + Fraction(rec['cs'] * 20, CLASSES_N * CLASS_Q)
         + Fraction(max(0, rec['hw']) * 20, HW_Q) + Fraction(max(0, rec['ex']) * 50, EXAM_Q))
    return min(100, int(x + Fraction(1, 2)))


def letter(m: int) -> tuple[str, int]:
    return next((l, p) for low, l, p in GRADES if m >= low)


def gpa(marks: dict) -> int:
    """GPA ×100 (all subjects 3 credits), rounded half up; 0 without marks."""
    if not marks:
        return 0
    pts = [letter(m)[1] for m in marks.values()]
    return int(Fraction(sum(pts), len(pts)) + Fraction(1, 2))


def class_of(g100: int) -> str:
    return next(c[0] for c in CLASSES if g100 >= c[2])


def fmt_gpa(g100: int) -> str:
    return f'{g100 // 100},{g100 % 100:02d}'


# ---------------------------------------------------------------- the day
def _today(cur: dict, day: int) -> tuple[int, list]:
    return (cur['nt'], list(cur['at'])) if cur['day'] == day else (0, [])


def _roll(cur: dict, day: int) -> None:
    if cur['day'] != day:
        cur.update(day=day, nt=0, at=[])


def weekday(cur: dict, day: int) -> int:
    return (day - cur['start']) % 7


def sem_subjects(cur: dict) -> tuple:
    return PROGRAMS[cur['p']]['sems'][cur['sem']]


def available(cur: dict, day: int) -> list[str]:
    """The subjects whose class can be taken now: today's slots (a finished subject's slot is free)."""
    if cur['ph'] != 'study':
        return []
    nt, at = _today(cur, day)
    wd = weekday(cur, day)
    if nt >= PER_DAY or wd == SUNDAY:
        return []
    subs = sem_subjects(cur)
    short = [sid for sid in subs if cur['sub'][sid]['a'] < CLASSES_N and sid not in at]
    slots = [subs[i] for i in TIMETABLE[wd]]
    out = [sid for sid in slots if sid in short]
    if any(cur['sub'][sid]['a'] >= CLASSES_N for sid in slots):
        out += [sid for sid in short if sid not in out]
    return out


def _hw_open(cur: dict, sid: str, day: int) -> bool:
    r = cur['sub'][sid]
    return cur['ph'] == 'study' and r['a'] >= 2 and r['hwd'] < day and r['hw'] < HW_Q and sid not in cur['marks']


def _exam_open(cur: dict, sid: str, day: int) -> bool:
    r = cur['sub'][sid]
    return cur['ph'] == 'study' and r['a'] >= CLASSES_N and r['hw'] >= 0 and r['exd'] < day and sid not in cur['marks']


def _job_open(cur: dict, day: int) -> bool:
    p = PROGRAMS[cur['p']]
    return p['kind'] == 'abroad' and cur['ph'] == 'study' and cur['job'] < day and cur['jn'] < JOB_MAX


def _event_open(cur: dict, day: int) -> bool:
    return cur['ph'] in ('study', 'break') and cur['evd'] < day and len(cur['ev']) < len(events_of(PROGRAMS[cur['p']]))


# ---------------------------------------------------------------- questions
def _bank(sid: str) -> list[dict]:
    return _questions(SUBJECTS[sid])


def _draw(s: dict, cur: dict, sid: str, kind: str) -> list[int]:
    """The question indexes (0–9) of the next class / homework / exam of `sid`."""
    r = cur['sub'][sid]
    if kind == 'class':
        k = min(r['a'], CLASSES_N - 1)
        return list(range(k * CLASS_Q, k * CLASS_Q + CLASS_Q))
    n, size = (r['hwn'], HW_Q) if kind == 'hw' else (r['tries'], EXAM_Q)
    return _rng(_seed(s), cur['p'], sid, kind, n).sample(range(len(_bank(sid))), size)


def _order(s: dict, sid: str, qi: int, n: int) -> list[int]:
    """The order a question's options / items are shown in (fixed for a save)."""
    idx = list(range(n))
    _rng(_seed(s), sid, qi, 'shuffle').shuffle(idx)
    return idx


def _qview(s: dict, sid: str, qi: int) -> dict:
    q = _bank(sid)[qi]
    out = dict(k=q['k'], text=q['text'])
    if q['k'] == 'c':
        out['options'] = [dict(i=i, label=q['options'][i]) for i in _order(s, sid, qi, len(q['options']))]
    elif q['k'] == 'o':
        out['items'] = [dict(i=i, label=q['items'][i]) for i in _order(s, sid, qi, len(q['items']))]
    return out


def _right_text(q: dict) -> str:
    if q['k'] == 'c':
        return q['options'][q['ok']]
    if q['k'] == 't':
        return 'Đúng' if q['ok'] else 'Sai'
    if q['k'] == 'o':
        return ' → '.join(q['items'])
    return str(q['ok'])


def _shape_ok(q: dict, a) -> bool:
    if q['k'] == 'c':
        return type(a) is int and 0 <= a < len(q['options'])
    if q['k'] == 't':
        return type(a) is bool
    if q['k'] == 'o':
        return isinstance(a, list) and sorted(x for x in a if type(x) is int) == list(range(len(q['items']))) and len(a) == len(q['items'])
    return type(a) is int and 0 <= a <= 10**8


def _right(q: dict, a) -> bool:
    if q['k'] == 'o':
        return a == list(range(len(q['items'])))
    return a == q['ok']


def _grade(sid: str, qs: list[int], answers) -> tuple[int, list[dict]]:
    e = _core()
    e.need(isinstance(answers, list) and len(answers) == len(qs), 'Trả lời đủ các câu rồi nộp nhé.')
    bank = _bank(sid)
    rows, right = [], 0
    for qi, a in zip(qs, answers):
        q = bank[qi]
        e.need(_shape_ok(q, a), 'Câu trả lời không hợp lệ.')
        ok = _right(q, a)
        right += ok
        rows.append(dict(text=q['text'], ok=ok, right=_right_text(q), why=q['why']))
    return right, rows


# ---------------------------------------------------------------- commands
def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    e.need(_story(s), 'Trường học có trong hành trình.')
    out = _action(s, name, p)
    want = p.get('view') if isinstance(p.get('view'), dict) else None
    out['school'] = view(s, want)
    return out


def _pay(s: dict, cost: int, label: str, p: dict) -> None:
    from . import bank as bk
    bk.pay(s, cost, label, method=p.get('pay', 'auto'), kind='study',
           short=f'Chưa đủ {cost} xu. Làm thêm vài ngày rồi quay lại nhé.')


def _new_cur(pid: str, sem: int, ph: str, day: int, fee: int, marks: dict) -> dict:
    p = PROGRAMS[pid]
    return dict(p=pid, sem=sem, ph=ph, start=day, fee=fee, paid=fee, day=day, nt=0, at=[],
                sub={sid: _sub0() for sid in p['sems'][sem]}, marks=dict(marks), ev=[], evd=0, job=0, jn=0)


def _action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    day = int(j['life_day'])
    if name == 'jr_sch_view':
        return dict(message='')
    b = _block(s)
    cur = b['cur']
    if name in ('jr_sch_enrol', 'jr_sch_apply'):
        pid = p.get('program')
        need(isinstance(pid, str) and pid in PROGRAMS, 'Ngành học không tồn tại.')
        pr = PROGRAMS[pid]
        need(cur is None, f'Bạn đang học {PROGRAMS[cur["p"]]["name"]}. Học xong hoặc thôi học trước nhé.' if cur else '')
        need(pid not in b['deg'], f'Bạn đã có {degree_name(pid)} rồi.')
        if name == 'jr_sch_enrol':
            need(pr['kind'] == 'uni', 'Du học thì nộp hồ sơ ở mục ✈️ Du học nhé.')
            kept = b['kept'].get(pid) or {}
            sem = len(kept) // len(pr['sems'][0])
            cost = tuition(pid)
            _pay(s, cost, f'Học phí học kỳ {sem + 1} · {pr["name"]}', p)
            b['kept'].pop(pid, None)
            b['cur'] = _new_cur(pid, sem, 'study', day, cost, kept)
            back = f' Học tiếp từ học kỳ {sem + 1} (bảo lưu).' if sem else ''
            return dict(message=f'🎓 Chào tân sinh viên ngành {pr["name"]}!{back} Hôm nay là Thứ 2: xem thời khóa biểu và vào lớp nhé.',
                        celebrate=True)
        need(pr['kind'] == 'abroad', 'Ngành trong nước thì bấm Nhập học nhé.')
        docs = p.get('docs')
        need(isinstance(docs, list) and all(isinstance(x, str) for x in docs) and len(docs) <= len(DOC_IDS), 'Chọn giấy tờ cho hồ sơ nhé.')
        picked = set(docs)
        lack = [label for d, label, ok in C.DOCS if ok and d not in picked]
        extra = [label for d, label, ok in C.DOCS if not ok and d in picked]
        need(not lack and not extra, 'Hồ sơ chưa đúng: ' + '; '.join(
            ([f'còn thiếu {", ".join(lack)}'] if lack else []) + ([f'không cần {", ".join(extra)}'] if extra else [])) + '. Sửa lại rồi nộp nhé, không mất gì cả.')
        fee, visa = tuition(pid), visa_fee(pid)
        _pay(s, fee + visa, f'Học phí & visa du học · {pr["country"]}', p)
        b['cur'] = _new_cur(pid, 0, 'visa', day, fee + visa, {})
        return dict(message=f'📨 {pr["school"]} đã nhận hồ sơ! Còn buổi phỏng vấn visa ngắn nữa thôi.')
    need(cur, 'Bạn chưa đăng ký học ngành nào.')
    pr = PROGRAMS[cur['p']]
    if name == 'jr_sch_visa':
        need(cur['ph'] == 'visa', 'Visa đã xong rồi.')
        opt = p.get('option')
        q, opts, ok = pr['visa_q'][0], pr['visa_q'][1], pr['visa_q'][2]
        need(type(opt) is int and 0 <= opt < len(opts), 'Chọn một câu trả lời nhé.')
        need(opt == ok, 'Cán bộ lãnh sự mỉm cười: “Bạn nghĩ thêm chút rồi trả lời lại nhé.” Gợi ý: đi du học là để học và mang nghề về.')
        cur['ph'] = 'fly'
        return dict(message=f'🛂 Visa {pr["country"]} đã được duyệt! Sắp xếp hành lý rồi lên máy bay thôi.', celebrate=True)
    if name == 'jr_sch_fly':
        need(cur['ph'] == 'fly', 'Bạn chưa tới bước lên máy bay.' if cur['ph'] == 'visa' else 'Bạn đã tới nơi rồi.')
        cur.update(ph='study', start=day, day=day, nt=0, at=[])
        return dict(message=f'{pr["flag"]} Chào mừng tới {pr["city"]}! Hôm nay là Thứ 2, buổi học đầu tiên đang chờ.',
                    lines=list(pr['fly']), celebrate=True)
    if name == 'jr_sch_next':
        need(cur['ph'] == 'break', 'Học xong học kỳ này đã nhé.')
        sem = cur['sem'] + 1
        cost = tuition(cur['p'])
        _pay(s, cost, f'Học phí học kỳ {sem + 1} · {pr["name"]}', p)
        nxt = _new_cur(cur['p'], sem, 'study', day, cost, cur['marks'])
        nxt.update(paid=cur['paid'] + cost, ev=cur['ev'], evd=cur['evd'])
        b['cur'] = nxt
        return dict(message=f'📚 Vào học kỳ {sem + 1}! Ba môn mới, thời khóa biểu mới, hôm nay là Thứ 2.', celebrate=True)
    if name == 'jr_sch_drop':
        need(p.get('confirm') is True, 'Xác nhận thôi học.')
        left = sum(CLASSES_N - r['a'] for r in cur['sub'].values()) if cur['ph'] != 'break' else 0
        back = cur['fee'] * left // (CLASSES_N * len(cur['sub'])) // 2 if cur['ph'] != 'break' else 0
        b['cur'] = None
        keep = {}
        if pr['kind'] == 'uni':
            n = len(pr['sems'][0])
            done = cur['sem'] + (1 if cur['ph'] == 'break' else 0)
            keep = {sid: m for sid, m in cur['marks'].items() if any(sid in pr['sems'][k] for k in range(done))}
            if len(keep) == done * n and keep:
                b['kept'][cur['p']] = keep
        if back > 0:
            from .journey import _wallet
            _wallet(j, back, 'study', f'Hoàn học phí · {pr["name"]}')
        msg = f'Bạn đã thôi học {pr["name"]}.' + (f' Trường hoàn {back} xu cho các buổi chưa học.' if back else '')
        if keep:
            msg += f' Kết quả {len(keep) // len(pr["sems"][0])} học kỳ đã học được bảo lưu.'
        if pr['kind'] == 'abroad' and cur['ph'] in ('study', 'break'):
            msg += ' Bạn bay về phố Mây.'
        return dict(message=msg)
    if name == 'jr_sch_event':
        need(_event_open(cur, day), 'Hôm nay đã có một hoạt động rồi, mai tham gia tiếp nhé.' if cur['evd'] >= day else 'Chưa có hoạt động nào lúc này.', 'not_now')
        ev = next((x for x in events_of(pr) if x['id'] == p.get('event')), None)
        need(ev is not None and ev['id'] not in cur['ev'], 'Hoạt động không tồn tại.')
        opt = p.get('option')
        need(type(opt) is int and 0 <= opt < len(ev['options']), 'Chọn một lựa chọn nhé.')
        cur['ev'] = cur['ev'] + [ev['id']]
        cur['evd'] = day
        return dict(message=f'{ev["emoji"]} {ev["options"][opt][1]}', event=dict(id=ev['id']))
    if name == 'jr_sch_job':
        need(_job_open(cur, day), 'Hôm nay làm thêm rồi, mai quay lại nhé.' if cur['job'] >= day and pr['kind'] == 'abroad' else 'Chưa làm thêm được lúc này.', 'not_now')
        job = pr['jobs'][cur['jn'] % len(pr['jobs'])]
        opt = p.get('option')
        need(type(opt) is int and 0 <= opt < len(job['options']), 'Chọn một cách làm nhé.')
        good = opt == job['ok']
        pay = JOB_PAY[1] if good else JOB_PAY[0]
        cur['job'] = day
        cur['jn'] += 1
        from .journey import _wallet
        _wallet(j, pay, 'salary', f'Làm thêm · {pr["city"]}')
        line = f'✅ {job["why"]}' if good else f'💡 Cách hay hơn: “{job["options"][job["ok"]]}”. {job["why"]}'
        return dict(message=f'{line} Tiền công {pay} xu đã vào ví.', job=dict(ok=good, pay=pay))
    if name in ('jr_sch_class', 'jr_sch_hw', 'jr_sch_exam'):
        sid = p.get('subject')
        need(isinstance(sid, str) and sid in cur['sub'], 'Môn học không thuộc học kỳ này.')
        need(cur['ph'] == 'study', 'Học kỳ này đã xong.' if cur['ph'] == 'break' else 'Bạn chưa tới trường.')
        r = cur['sub'][sid]
        sub = SUBJECTS[sid]
        if name == 'jr_sch_class':
            nt, at = _today(cur, day)
            need(r['a'] < CLASSES_N, 'Môn này đã học đủ buổi. Làm bài tập và thi nhé.')
            need(weekday(cur, day) != SUNDAY, 'Chủ nhật trường nghỉ. Đi chơi, làm thêm, mai học tiếp nhé.', 'not_now')
            need(nt < PER_DAY, f'Hôm nay học đủ {PER_DAY} buổi rồi. Khép một ca làm việc để sang ngày mới nhé.', 'not_now')
            need(sid not in at, 'Môn này hôm nay học rồi.', 'not_now')
            need(sid in available(cur, day), f'Hôm nay không có lịch môn {sub["name"]}. Xem thời khóa biểu nhé.', 'not_now')
            qs = _draw(s, cur, sid, 'class')
            right, rows = _grade(sid, qs, p.get('answers'))
            lesson = sub['lessons'][r['a']]
            _roll(cur, day)
            r['a'] += 1
            r['cs'] += right
            cur['nt'] += 1
            cur['at'] = cur['at'] + [sid]
            tail = (' Bài tập về nhà đã mở.' if r['a'] == 2 else ' Đủ buổi rồi: làm bài tập và thi nhé.' if r['a'] == CLASSES_N else '')
            return dict(message=f'{sub["emoji"]} Xong buổi {r["a"]}/{CLASSES_N} môn {sub["name"]} ({lesson["title"]}): đúng {right}/{len(qs)} câu.{tail}',
                        quiz=dict(kind='class', subject=sid, right=right, of=len(qs), rows=rows))
        if name == 'jr_sch_hw':
            need(r['a'] >= 2, 'Học xong buổi 2 thì có bài tập về nhà nhé.')
            need(sid not in cur['marks'], 'Môn này đã thi đạt rồi.')
            need(r['hw'] < HW_Q, 'Bài tập môn này đã đúng hết rồi.')
            need(r['hwd'] < day, 'Hôm nay làm bài tập môn này rồi, mai làm lại nếu muốn điểm cao hơn.', 'not_now')
            qs = _draw(s, cur, sid, 'hw')
            right, rows = _grade(sid, qs, p.get('answers'))
            r['hw'] = max(r['hw'], right)
            r['hwn'] += 1
            r['hwd'] = day
            tail = ' Đã đủ điều kiện thi.' if r['a'] >= CLASSES_N else ''
            return dict(message=f'📝 Bài tập {sub["name"]}: đúng {right}/{len(qs)} câu (cao nhất {r["hw"]}/{HW_Q}).{tail}',
                        quiz=dict(kind='hw', subject=sid, right=right, of=len(qs), rows=rows))
        need(r['a'] >= CLASSES_N and r['hw'] >= 0, 'Học đủ buổi và nộp bài tập rồi mới thi nhé.')
        need(sid not in cur['marks'], 'Môn này đã thi đạt rồi.')
        need(r['exd'] < day, 'Hôm nay thi môn này rồi. Ôn lại, mai thi lại miễn phí nhé.', 'not_now')
        qs = _draw(s, cur, sid, 'exam')
        right, rows = _grade(sid, qs, p.get('answers'))
        r['tries'] += 1
        r['exd'] = day
        r['ex'] = max(r['ex'], right)
        quiz = dict(kind='exam', subject=sid, right=right, of=len(qs), rows=rows, passed=right >= EXAM_PASS)
        if right < EXAM_PASS:
            return dict(message=f'📄 Thi {sub["name"]}: đúng {right}/{EXAM_Q} câu, cần {EXAM_PASS}. Không sao, mai thi lại miễn phí với đề mới nhé!',
                        quiz=quiz)
        m = cur['marks'][sid] = mark(r)
        quiz.update(mark=m, letter=letter(m)[0])
        head = f'🎉 Đạt môn {sub["name"]}: {m // 10},{m % 10} điểm ({letter(m)[0]}).'
        if any(x not in cur['marks'] for x in sem_subjects(cur)):
            return dict(message=head, quiz=quiz)
        if cur['sem'] + 1 < len(pr['sems']):
            cur['ph'] = 'break'
            return dict(message=f'{head} Xong học kỳ {cur["sem"] + 1}! Đóng học phí học kỳ {cur["sem"] + 2} để học tiếp nhé.',
                        quiz=quiz, celebrate=True)
        out = _graduate(s, b, cur)
        out['message'] = f'{head} {out["message"]}'
        out['quiz'] = quiz
        return out
    raise e.GameError('Thao tác trường học không hợp lệ.', 'unknown_action')


def _graduate(s: dict, b: dict, cur: dict) -> dict:
    j = s['journey']
    day = int(j['life_day'])
    pid = cur['p']
    pr = PROGRAMS[pid]
    g100 = gpa(cur['marks'])
    cls = class_of(g100)
    from . import certificates as ct
    b['deg'][pid] = dict(d=day, g=cls, gpa=g100, date=ct.today_vn(), serial=ct.serial(_seed(s), pid, day), ev=len(cur['ev']))
    b['cur'] = None
    b['kept'].pop(pid, None)
    from .journey import _news, _wallet
    gift = cur['paid'] * SCHOLAR_PCT // 100 if cls == 'xuat_sac' else 0
    if gift > 0:
        _wallet(j, gift, 'study', f'Học bổng xuất sắc · {pr["name"]}')
    titles = []
    unis = [k for k in held(s) if PROGRAMS[k]['kind'] == 'uni']
    for tid, ok in ((TITLE_FIRST, pr['kind'] == 'uni'), (TITLE_TWO, len(unis) >= 2), (TITLE_TOP, cls == 'xuat_sac'),
                    (TITLE_ABROAD, pr['kind'] == 'abroad')):
        if ok and tid not in j['titles']:
            j['titles'][tid] = day
            titles.append(tid)
    if titles:
        _news(j, 'titles', 'titles', titles)
    from .content import CAREER_META
    places = ', '.join(CAREER_META[c]['short'] for c in pr['careers'] if c in CAREER_META)
    pct = CLASS_PCT[cls]
    msg = (f'🎓 Tốt nghiệp loại {CLASS_NAME[cls]} (GPA {fmt_gpa(g100)}): {degree_name(pid)}! Từ nay tiền công +{pct}% ở {places}, '
           f'tính như chứng chỉ khi xin việc, và mở sớm các nơi đó.')
    if pr['kind'] == 'abroad':
        msg += ' Bằng du học cũng tăng lương mọi việc làm thuê.' + f' {pr["home"]}'
    if gift:
        msg += f' Học bổng xuất sắc: +{gift} xu.'
    out = dict(message=msg, celebrate=True, graduated=dict(program=pid, g=cls, gpa=g100))
    if titles:
        out['journey'] = dict(chapters=[], titles=titles)
    return out


# ---------------------------------------------------------------- views
def _sub_view(s: dict, cur: dict, sid: str, day: int, avail: list) -> dict:
    r = cur['sub'][sid]
    sub = SUBJECTS[sid]
    m = cur['marks'].get(sid)
    return dict(id=sid, name=sub['name'], emoji=sub['emoji'], a=r['a'], cs=r['cs'], hw=r['hw'], ex=r['ex'], tries=r['tries'],
                passed=m is not None, mark=m, letter=letter(m)[0] if m is not None else None, now=mark(r),
                lesson=sub['lessons'][min(r['a'], CLASSES_N - 1)]['title'],
                can_class=sid in avail, can_hw=_hw_open(cur, sid, day), can_exam=_exam_open(cur, sid, day),
                hw_done_today=r['hwd'] >= day, exam_today=r['exd'] >= day)


def _week(cur: dict) -> list[dict]:
    subs = sem_subjects(cur)
    return [dict(wd=i, label=WEEKDAYS[i], subjects=[subs[k] for k in TIMETABLE[i]]) for i in range(7)]


def _quiz(s: dict, cur: dict, want: dict, day: int) -> dict | None:
    kind, sid = want.get('open'), want.get('subject')
    if kind == 'job':
        if not _job_open(cur, day):
            return None
        job = PROGRAMS[cur['p']]['jobs'][cur['jn'] % len(PROGRAMS[cur['p']]['jobs'])]
        return dict(kind='job', scene=job['scene'], q=job['q'], options=list(job['options']))
    if not isinstance(sid, str) or sid not in cur['sub']:
        return None
    if kind == 'class' and sid in available(cur, day):
        r = cur['sub'][sid]
        lesson = SUBJECTS[sid]['lessons'][r['a']]
        return dict(kind='class', subject=sid, n=r['a'] + 1, title=lesson['title'], points=list(lesson['points']),
                    qs=[_qview(s, sid, qi) for qi in _draw(s, cur, sid, 'class')])
    if kind == 'hw' and _hw_open(cur, sid, day):
        return dict(kind='hw', subject=sid, qs=[_qview(s, sid, qi) for qi in _draw(s, cur, sid, 'hw')])
    if kind == 'exam' and _exam_open(cur, sid, day):
        return dict(kind='exam', subject=sid, attempt=cur['sub'][sid]['tries'] + 1,
                    qs=[_qview(s, sid, qi) for qi in _draw(s, cur, sid, 'exam')])
    return None


def _deg_view(pid: str, d: dict) -> dict:
    p = PROGRAMS[pid]
    return dict(p=pid, name=degree_name(pid), kind=p['kind'], g=d['g'], cls=CLASS_NAME.get(d['g'], ''), gpa=d['gpa'],
                gpa_text=fmt_gpa(d['gpa']), date=d['date'], serial=d['serial'], d=d['d'], ev=d['ev'],
                pct=CLASS_PCT.get(d['g'], 0), careers=list(p['careers']))


def view(s: dict, want: dict | None = None) -> dict:
    """The page's view (jr_sch_* results): the program running, today's timetable, the degrees; a quiz on request."""
    j = s['journey']
    day = int(j.get('life_day') or 1)
    b = get(s) or initial()
    out = dict(day=day, cur=None, deg=[_deg_view(k, v) for k, v in held(s).items()],
               kept={k: len(v) // len(PROGRAMS[k]['sems'][0]) for k, v in (b.get('kept') or {}).items() if k in PROGRAMS}, quiz=None)
    cur = b.get('cur')
    if isinstance(cur, dict) and cur.get('p') in PROGRAMS:
        pr = PROGRAMS[cur['p']]
        avail = available(cur, day)
        nt, _ = _today(cur, day)
        v = dict(p=cur['p'], kind=pr['kind'], sem=cur['sem'], sems=len(pr['sems']), ph=cur['ph'], fee=cur['fee'], paid=cur['paid'],
                 wd=weekday(cur, day), wd_label=WEEKDAYS[weekday(cur, day)], week=_week(cur), avail=avail, left=max(0, PER_DAY - nt),
                 subjects=[_sub_view(s, cur, sid, day, avail) for sid in sem_subjects(cur)],
                 marks={sid: m for sid, m in cur['marks'].items()}, gpa=gpa(cur['marks']), gpa_text=fmt_gpa(gpa(cur['marks'])),
                 events=[dict(id=x['id'], emoji=x['emoji'], title=x['title'], scene=x['scene'], options=[o[0] for o in x['options']],
                              done=x['id'] in cur['ev']) for x in events_of(pr)],
                 can_event=_event_open(cur, day), next_fee=tuition(cur['p']) if cur['ph'] == 'break' else 0)
        if pr['kind'] == 'abroad':
            v.update(job=dict(can=_job_open(cur, day), n=cur['jn'], max=JOB_MAX, pay=list(JOB_PAY)))
            if cur['ph'] == 'visa':
                v['visa'] = dict(q=pr['visa_q'][0], options=list(pr['visa_q'][1]))
            if cur['ph'] == 'fly':
                v['fly'] = list(pr['fly'])
        out['cur'] = v
        if isinstance(want, dict):
            out['quiz'] = _quiz(s, cur, want, day)
    return out


def summary(s: dict) -> dict | None:
    """journey public: what the menu and the journey page show (absent until the school was used)."""
    if not _story(s):
        return None
    b = get(s)
    if not b:
        return None
    day = int(s['journey'].get('life_day') or 1)
    out = dict(deg=sorted(held(s)))
    cur = b.get('cur')
    if isinstance(cur, dict) and cur.get('p') in PROGRAMS:
        todo = len(available(cur, day)) + sum(_exam_open(cur, sid, day) for sid in cur['sub'])
        out['cur'] = dict(p=cur['p'], ph=cur['ph'], sem=cur['sem'], todo=todo, done=len(cur['marks']),
                          of=sum(len(x) for x in PROGRAMS[cur['p']]['sems']))
    return out


def catalogue() -> dict:
    """Bootstrap content: the programs (no questions, no keys), the rules the page states."""
    def subj(sid):
        return dict(id=sid, name=SUBJECTS[sid]['name'], emoji=SUBJECTS[sid]['emoji'])
    majors = [dict(id=p['id'], kind='uni', name=p['name'], emoji=p['emoji'], blurb=p['blurb'], fee=tuition(p['id']), careers=list(p['careers']),
                   sems=[[subj(x) for x in sem] for sem in p['sems']]) for p in C.MAJORS]
    terms = [dict(id=p['id'], kind='abroad', name=p['name'], flag=p['flag'], country=p['country'], city=p['city'], school=p['school'],
                  fee=tuition(p['id']), visa=visa_fee(p['id']), careers=list(p['careers']), sems=[[subj(x) for x in sem] for sem in p['sems']])
             for p in C.TERMS]
    return dict(uni=dict(C.UNI), majors=majors, terms=terms, docs=[dict(id=d, label=label) for d, label, _ in C.DOCS],
                rules=dict(classes=CLASSES_N, per_day=PER_DAY, exam_q=EXAM_Q, exam_pass=EXAM_PASS, hw_q=HW_Q, credits=CREDITS,
                           scholar=SCHOLAR_PCT, job_pay=list(JOB_PAY), classes_pct={c[0]: c[3] for c in CLASSES},
                           class_names={c[0]: c[1] for c in CLASSES}, weekdays=list(WEEKDAYS)))


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu trường học không hợp lệ.'
    b = j[KEY]
    need(isinstance(b, dict) and BLOCK_KEYS <= set(b) and b['v'] == VERSION, bad, 'invalid_save')   # keys a newer build adds are kept
    need(isinstance(b['deg'], dict) and len(b['deg']) <= 64, bad, 'invalid_save')
    for k, d in b['deg'].items():
        need(isinstance(k, str) and len(k) <= 32 and isinstance(d, dict) and DEG_KEYS <= set(d), bad, 'invalid_save')
        if k not in PROGRAMS:
            continue   # a program a newer build added
        need(d['g'] in CLASS_IDS and isinstance(d['date'], str) and _DATE.fullmatch(d['date']) is not None
             and isinstance(d['serial'], str) and len(d['serial']) <= 40, bad, 'invalid_save')
        integer(d['d'], 1, 10**6)
        integer(d['gpa'], 0, 400)
        integer(d['ev'], 0, 99)
    need(isinstance(b['kept'], dict) and len(b['kept']) <= 64, bad, 'invalid_save')
    for k, marks in b['kept'].items():
        need(isinstance(k, str) and isinstance(marks, dict) and len(marks) <= 99, bad, 'invalid_save')
        for sid, m in marks.items():
            need(isinstance(sid, str), bad, 'invalid_save')
            integer(m, 0, 100)
    cur = b['cur']
    if cur is None:
        return
    need(isinstance(cur, dict) and CUR_KEYS <= set(cur) and cur['p'] in PROGRAMS and cur['ph'] in PHASES, bad, 'invalid_save')
    pr = PROGRAMS[cur['p']]
    integer(cur['sem'], 0, len(pr['sems']) - 1)
    need(pr['kind'] == 'abroad' or cur['ph'] in ('study', 'break'), bad, 'invalid_save')
    need(cur['ph'] != 'break' or cur['sem'] + 1 < len(pr['sems']), bad, 'invalid_save')
    need(cur['p'] not in b['deg'], bad, 'invalid_save')
    for k in ('start', 'day'):
        integer(cur[k], 1, 10**6)
    integer(cur['fee'], 0, 10**7)
    integer(cur['paid'], cur['fee'], 10**8)
    integer(cur['nt'], 0, PER_DAY)
    for k in ('evd', 'job'):
        integer(cur[k], 0, 10**6)
    integer(cur['jn'], 0, JOB_MAX)
    subs = pr['sems'][cur['sem']]
    need(isinstance(cur['at'], list) and len(cur['at']) == cur['nt'] and len(set(cur['at'])) == len(cur['at'])
         and all(x in subs for x in cur['at']), bad, 'invalid_save')
    need(isinstance(cur['sub'], dict) and set(cur['sub']) == set(subs), bad, 'invalid_save')
    for sid, r in cur['sub'].items():
        need(isinstance(r, dict) and set(r) == SUB_KEYS, bad, 'invalid_save')
        integer(r['a'], 0, CLASSES_N)
        integer(r['cs'], 0, r['a'] * CLASS_Q)
        integer(r['hw'], -1, HW_Q)
        integer(r['hwn'], 0, 10**6)
        need((r['hw'] >= 0) == (r['hwn'] > 0), bad, 'invalid_save')
        integer(r['ex'], -1, EXAM_Q)
        integer(r['tries'], 0, 10**6)
        need((r['ex'] >= 0) == (r['tries'] > 0), bad, 'invalid_save')
        integer(r['hwd'], 0, 10**6)
        integer(r['exd'], 0, 10**6)
    earlier = {x for k in range(cur['sem']) for x in pr['sems'][k]}
    need(isinstance(cur['marks'], dict) and set(cur['marks']) <= earlier | set(subs) and earlier <= set(cur['marks']), bad, 'invalid_save')
    for sid, m in cur['marks'].items():
        integer(m, 0, 100)
        if sid in cur['sub']:
            need(cur['sub'][sid]['ex'] >= EXAM_PASS, bad, 'invalid_save')
    need((cur['ph'] == 'break') == (cur['ph'] != 'visa' and cur['ph'] != 'fly' and set(subs) <= set(cur['marks'])), bad, 'invalid_save')
    evs = {x['id'] for x in events_of(pr)}
    need(isinstance(cur['ev'], list) and len(set(cur['ev'])) == len(cur['ev']) and set(cur['ev']) <= evs, bad, 'invalid_save')
