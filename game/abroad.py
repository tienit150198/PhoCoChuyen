"""✈️ Du học and 🌏 Làm việc ở nước ngoài (story mode). Player feedback #254, owner OK 08/10.

Both run on the life-day clock like the rest of the journey (a life day passes when a shift closes somewhere):

* ✈️ Du học (jr_abroad_enrol {program}, jr_abroad_lesson {option}, jr_abroad_drop {confirm}): a short course at a
  made-up school in one of four destinations (game/abroad_content.py). Tuition up front (wallet, account or card:
  game/bank.py pay, wallet row kind 'study'); then one lesson a life day, each a little scene and one question (a wrong
  answer only teaches, nobody fails). The last lesson gives the degree: Xuất sắc (every answer right, and a scholarship
  back: SCHOLAR_PCT % of the tuition), Giỏi or Khá. Leaving early gives half of the unused lessons' tuition back.
  A degree (any one) is for good:
    - every hired job pays DEG_PCT more (+10 %, +15 % with two degrees, +20 % from three), on top of the step's raise
      (game/employment.py on_close/public);
    - every 🎖️ promotion step needs GOOD_CUT % fewer good days, and it counts as the 🎓 certificate the third step
      asks for (game/promotion.py).
* 🌏 Làm việc ở nước ngoài (jr_abroad_work {to, career}, jr_abroad_home {confirm}): a hired job off probation sends you
  to its branch abroad for a few worked days at more pay (WORK[to]['pct'] %, on the salary as paid at home). The ticket
  and the work visa are paid up front and refunded when the contract is done. While you are away, the other workplaces
  stay shut (journey.gate: start_day), and each worked day brings a line from the city and a letter from home. The last
  day brings you home: the fee back, LADDER_BONUS good days on that job's ladder. Coming home early is allowed (no
  refund, no bonus, the pay earned stays). After a contract, REST life days at home before the next one. Quitting or
  changing the job ends the contract (sync()).

State journey['abroad'] (absent until first used; journey.validate allows extra keys, so an older build keeps it and
ignores it: it would pay the plain salary and not shut the other workplaces for as long as it runs):
    v      VERSION
    study  None | {p: program id, start, n: lessons done, ok: right answers, last: life day of the last lesson, fee}
    deg    {program id: {d: life day, g: grade id}}
    work   None | {to: destination id, career, emp: posting id, hd: hired_day, n: days worked there, need, pct, fee, start}
    back   life day you came home from the last contract (0: never)
    done   {destination id: contracts finished}
Wallet rows use the existing kinds 'study' and 'life' (journey.HISTORY_KINDS is a closed list older builds validate).
"""
from __future__ import annotations

from . import abroad_content as C
from . import price_index as pi

VERSION = 1
KEY = 'abroad'
DEST = {d['id']: d for d in C.DESTS}
DEG_PCT = (0, 10, 15, 20)        # the hired salary's bonus by degrees held (0, 1, 2, 3+)
GOOD_CUT = 20                    # % fewer good days for every promotion step with a degree
SCHOLAR_PCT = 20                 # Xuất sắc: this share of the tuition comes back
REST = 3                         # life days at home after a contract before the next one
LADDER_BONUS = 2                 # good days on the job's ladder when a contract is done
BLOCK_KEYS = frozenset({'v', 'study', 'deg', 'work', 'back', 'done'})
STUDY_KEYS = frozenset({'p', 'start', 'n', 'ok', 'last', 'fee'})
DEG_KEYS = frozenset({'d', 'g'})
WORK_KEYS = frozenset({'to', 'career', 'emp', 'hd', 'n', 'need', 'pct', 'fee', 'start'})
GRADE_IDS = tuple(g for g, _ in C.GRADES)
GRADE_NAME = dict(C.GRADES)


def _core():
    from . import engine
    return engine


def tuition(pid: str) -> int:
    return pi.price(C.PROGRAMS[pid]['fee'], luxury=False)


def work_fee(did: str) -> int:
    return pi.price(C.WORK[did]['fee'], luxury=False)


def initial() -> dict:
    return dict(v=VERSION, study=None, deg={}, work=None, back=0, done={})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get(KEY) if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _block(s: dict) -> dict:
    j = s['journey']
    b = j.get(KEY)
    if not isinstance(b, dict):
        b = j[KEY] = initial()
    for k, v in initial().items():
        b.setdefault(k, v)
    return b


def _story(s: dict) -> bool:
    j = s.get('journey')
    return isinstance(j, dict) and bool(j.get('story'))


# ---------------------------------------------------------------- what the rest of the game reads
def degrees(s: dict) -> int:
    b = get(s) if _story(s) else None
    return len(b.get('deg') or {}) if b else 0


def degree_pct(s: dict) -> int:
    """The hired salary's bonus (%) from the degrees held (employment.on_close/public)."""
    return DEG_PCT[min(degrees(s), len(DEG_PCT) - 1)]


def good_need(s: dict, need: int) -> int:
    """A promotion step's good days: GOOD_CUT % fewer (rounded up, at least 1) with a degree."""
    if need <= 0 or not degrees(s):
        return need
    return max(1, -(-need * (100 - GOOD_CUT) // 100))


def _valid(s: dict, w: dict) -> bool:
    c = (s.get('careers') or {}).get(w.get('career'))
    job = c.get('job') if isinstance(c, dict) else None
    return (isinstance(job, dict) and job.get('status') == 'hired' and job.get('employer') == w.get('emp')
            and (job.get('hired_day') or 0) == w.get('hd'))


def contract(s: dict) -> dict | None:
    """The contract abroad running now (None when there is none, or its job was left: sync() then ends it)."""
    b = get(s) if _story(s) else None
    w = b.get('work') if b else None
    return w if isinstance(w, dict) and _valid(s, w) else None


def pay_pct(s: dict, c: dict, career: str) -> int:
    """% more on the day's salary while working at the branch abroad (employment.on_close/public)."""
    w = contract(s)
    return w['pct'] if w and w['career'] == career else 0


def sync(s: dict) -> None:
    """journey.after: a contract whose job was quit or changed ends (no refund, no bonus)."""
    b = get(s)
    w = b.get('work') if b else None
    if isinstance(w, dict) and not _valid(s, w):
        b['work'] = None
        b['back'] = int(s['journey'].get('life_day') or 1)


def gate_start(s: dict, career: str) -> None:
    """journey.gate (start_day): the other workplaces stay shut while you are abroad."""
    w = contract(s)
    if w and career != w['career']:
        d = DEST[w['to']]
        from .journey import _place
        _core().need(False, f'Bạn đang làm ở chi nhánh {d["city"]} ({d["flag"]} {d["name"]}), còn {w["need"] - w["n"]} ngày nữa. '
                            f'Làm tiếp ở {_place(w["career"])}, hoặc về nước sớm ở mục 🌏 Làm việc ở nước ngoài.', 'abroad')


def on_paid(s: dict, c: dict, career: str, note: dict) -> None:
    """employment.on_close, after a worked day's salary at the contract's job: count the day, the city, a letter from
    home; the last day brings you home (the fee back, good days on the ladder)."""
    w = contract(s)
    if not w or w['career'] != career:
        return
    w['n'] += 1
    d, wk = DEST[w['to']], C.WORK[w['to']]
    seed = int(s['journey'].get('seed') or 0)
    lines = [f'🌏 Ngày {w["n"]}/{w["need"]} ở {d["city"]}: {wk["lines"][(w["n"] - 1) % len(wk["lines"])]}',
             f'✉️ {C.LETTERS[(seed + w["n"] + len(w["to"])) % len(C.LETTERS)]}']
    home = w['n'] >= w['need']
    if home:
        lines.append(_home(s, w, True))
    note['abroad'] = dict(to=w['to'], n=min(w['n'], w['need']), need=w['need'], home=home, lines=lines)


def _home(s: dict, w: dict, done: bool) -> str:
    b, j = _block(s), s['journey']
    d = DEST[w['to']]
    b['work'] = None
    b['back'] = int(j.get('life_day') or 1)
    if not done:
        return f'🏠 Bạn về nước sớm từ {d["city"]}. Lương những ngày đã làm vẫn là của bạn.'
    b['done'][w['to']] = min(10**6, int(b['done'].get(w['to']) or 0) + 1)
    from .journey import _wallet
    _wallet(j, w['fee'], 'life', f'Hoàn tiền vé · hết hợp đồng {d["city"]}', w['career'])
    from . import promotion
    c = s['careers'][w['career']]
    bonus = promotion.bonus_good(s, c, w['career'], LADDER_BONUS)
    tail = f' Sếp ghi nhận chuyến công tác: +{LADDER_BONUS} ngày tốt để lên chức.' if bonus else ''
    return (f'🏠 Hết hợp đồng ở {d["city"]}! Bạn về lại hẻm nhà, Bà Tám nấu canh chua đón. '
            f'Công ty hoàn {w["fee"]} xu tiền vé.{tail}')


def day_lines(job_note: dict | None) -> list[str]:
    """journey._end_of_day: the day abroad's lines for the day's effects."""
    x = (job_note or {}).get('abroad')
    return [str(t) for t in x.get('lines') or ()] if isinstance(x, dict) else []


# ---------------------------------------------------------------- jr_abroad_*
def _eligible(s: dict, cid: str) -> str | None:
    """Why this workplace cannot send you abroad now, or None."""
    from . import employment
    c = (s.get('careers') or {}).get(cid)
    if not isinstance(c, dict) or not employment.required(cid):
        return 'Chỉ nơi làm thuê mới cử người đi làm ở nước ngoài.'
    job = c.get('job') or {}
    if job.get('status') != 'hired':
        return 'Cần đang có việc ở nơi này.'
    if job.get('probation'):
        return 'Hết thử việc rồi công ty mới cử đi.'
    return None


def _rest_until(b: dict) -> int:
    return int(b.get('back') or 0) + REST if b.get('back') else 0


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j['story'], 'Du học và làm việc ở nước ngoài có trong hành trình.')
    b = _block(s)
    sync(s)
    day = int(j['life_day'])
    from . import bank as bk
    if name == 'jr_abroad_enrol':
        pid = p.get('program')
        need(pid in C.PROGRAMS, 'Khóa học không tồn tại.')
        pr, d = C.PROGRAMS[pid], DEST[pid]
        st = b['study']
        need(st is None, f'Bạn đang học khóa ở {DEST[st["p"]]["name"]}. Học xong hoặc thôi học trước nhé.' if st else '')
        need(pid not in b['deg'], f'Bạn đã có {pr["degree"]} rồi.')
        cost = tuition(pid)
        bk.pay(s, cost, f'Học phí du học · {d["name"]}', method=p.get('pay', 'auto'), kind='study',
               short=f'Chưa đủ {cost} xu học phí. Làm thêm vài ngày rồi quay lại nhé.')
        b['study'] = dict(p=pid, start=day, n=0, ok=0, last=0, fee=cost)
        return dict(message=f'✈️ Bạn nhập học {pr["school"]} ({d["flag"]} {d["city"]}): khóa {pr["course"]}, '
                            f'{len(pr["lessons"])} buổi, mỗi ngày sống một buổi. Buổi 1 học được ngay hôm nay!', celebrate=True)
    if name == 'jr_abroad_lesson':
        st = b['study']
        need(st, 'Bạn chưa đăng ký khóa du học nào.')
        need(st['last'] < day, 'Hôm nay học rồi. Khép ca ở đâu đó qua ngày mới rồi học buổi tiếp nhé.', 'not_now')
        pr = C.PROGRAMS[st['p']]
        lesson = pr['lessons'][st['n']]
        opt = p.get('option')
        need(type(opt) is int and 0 <= opt < len(lesson['options']), 'Chọn một câu trả lời nhé.')
        right = opt == lesson['ok']
        st['n'] += 1
        st['ok'] += int(right)
        st['last'] = day
        line = (f'✅ Đúng rồi! {lesson["why"]}' if right else
                f'💡 Chưa đúng: “{lesson["options"][lesson["ok"]]}”. {lesson["why"]}')
        if st['n'] < len(pr['lessons']):
            return dict(message=f'{line} Xong buổi {st["n"]}/{len(pr["lessons"])}, mai học tiếp.', abroad=dict(right=right))
        return _graduate(s, b, st, line)
    if name == 'jr_abroad_drop':
        st = b['study']
        need(st, 'Bạn không có khóa du học nào đang học.')
        need(p.get('confirm') is True, 'Xác nhận thôi học.')
        total = len(C.PROGRAMS[st['p']]['lessons'])
        back = st['fee'] * (total - st['n']) // total // 2
        b['study'] = None
        if back > 0:
            from .journey import _wallet
            _wallet(j, back, 'study', f'Hoàn học phí du học · {DEST[st["p"]]["name"]}')
        return dict(message=f'Bạn thôi học khóa ở {DEST[st["p"]]["name"]}.' + (f' Trường hoàn {back} xu cho các buổi chưa học.' if back else ''))
    if name == 'jr_abroad_work':
        to, cid = p.get('to'), p.get('career')
        need(to in C.WORK, 'Nơi làm việc ở nước ngoài không tồn tại.')
        need(b['work'] is None, 'Bạn đang có hợp đồng ở nước ngoài rồi.')
        rest = _rest_until(b)
        need(day >= rest, f'Vừa về nước, ở nhà với mọi người ít hôm đã: đi tiếp được từ Ngày {rest}.', 'not_now')
        why = _eligible(s, cid) if isinstance(cid, str) else 'Chọn nơi làm thuê sẽ cử bạn đi.'
        need(why is None, why or '')
        busy = next((x for x, c in s['careers'].items() if c.get('open')), None)
        from .journey import _place
        need(busy is None, f'Khép ca ở {_place(busy)} trước rồi hẵng lên đường nhé.' if busy else '', 'shift_open')
        need(p.get('confirm') is True, 'Xác nhận đi làm ở nước ngoài.')
        d, wk = DEST[to], C.WORK[to]
        cost = work_fee(to)
        bk.pay(s, cost, f'Vé & visa lao động · {d["name"]}', method=p.get('pay', 'auto'), kind='life', career=cid,
               short=f'Chưa đủ {cost} xu tiền vé và visa. Làm thêm vài ngày rồi quay lại nhé.')
        job = s['careers'][cid]['job']
        b['work'] = dict(to=to, career=cid, emp=job.get('employer'), hd=job.get('hired_day') or 0, n=0, need=wk['days'],
                         pct=wk['pct'], fee=cost, start=day)
        return dict(message=f'🌏 Lên đường tới {d["flag"]} {d["city"]}! {wk["days"]} ngày làm ở chi nhánh của {_place(cid)}, '
                            f'lương +{wk["pct"]}%. Hết hợp đồng công ty hoàn {cost} xu tiền vé. Các nơi làm khác tạm nghỉ tới lúc bạn về.',
                    celebrate=True)
    if name == 'jr_abroad_home':
        w = b['work']
        need(w, 'Bạn đang ở nhà mà.')
        need(p.get('confirm') is True, 'Xác nhận về nước sớm.')
        return dict(message=_home(s, w, False))
    raise e.GameError('Thao tác du học không hợp lệ.', 'unknown_action')


def _graduate(s: dict, b: dict, st: dict, line: str) -> dict:
    j = s['journey']
    pr, d = C.PROGRAMS[st['p']], DEST[st['p']]
    total = len(pr['lessons'])
    grade = 'xuat_sac' if st['ok'] >= total else 'gioi' if st['ok'] >= total - 1 else 'kha'
    b['deg'][st['p']] = dict(d=int(j['life_day']), g=grade)
    b['study'] = None
    gift = st['fee'] * SCHOLAR_PCT // 100 if grade == 'xuat_sac' else 0
    if gift > 0:
        from .journey import _wallet
        _wallet(j, gift, 'study', f'Học bổng xuất sắc · {d["name"]}')
    n = len(b['deg'])
    pct = degree_pct(s)
    more = f'lương mọi việc làm thuê +{pct}%' + (f' (có {n} bằng)' if n > 1 else '')
    msg = (f'{line} 🎓 Tốt nghiệp loại {GRADE_NAME[grade]}: {pr["degree"]}! Từ nay {more}, '
           f'lên chức cần ít hơn {GOOD_CUT}% ngày tốt.' + (f' Học bổng xuất sắc: +{gift} xu.' if gift else ''))
    return dict(message=msg, celebrate=True, abroad=dict(graduated=st['p'], grade=grade))


# ---------------------------------------------------------------- views
def catalogue() -> dict:
    return dict(
        dests=[dict(d) for d in C.DESTS],
        programs={k: dict(school=v['school'], course=v['course'], degree=v['degree'], fee=tuition(k), lessons=len(v['lessons']))
                  for k, v in C.PROGRAMS.items()},
        work={k: dict(days=v['days'], pct=v['pct'], fee=work_fee(k)) for k, v in C.WORK.items()},
        grades=dict(C.GRADES), deg_pct=list(DEG_PCT), good_cut=GOOD_CUT, scholar=SCHOLAR_PCT, rest=REST, bonus=LADDER_BONUS)


def public(s: dict) -> dict | None:
    if not _story(s):
        return None
    j = s['journey']
    b = get(s) or initial()
    day = int(j.get('life_day') or 1)
    out = dict(deg=[dict(id=k, d=v['d'], g=v['g']) for k, v in (b.get('deg') or {}).items() if k in C.PROGRAMS],
               deg_pct=degree_pct(s), study=None, work=None, rest_until=_rest_until(b), done=dict(b.get('done') or {}))
    st = b.get('study')
    if isinstance(st, dict) and st.get('p') in C.PROGRAMS:
        pr = C.PROGRAMS[st['p']]
        v = dict(p=st['p'], n=st['n'], of=len(pr['lessons']), ok=st['ok'], today=st['last'] >= day, fee=st['fee'])
        if not v['today'] and st['n'] < len(pr['lessons']):
            ls = pr['lessons'][st['n']]
            v['lesson'] = dict(scene=ls['scene'], q=ls['q'], options=list(ls['options']))
        out['study'] = v
    w = contract(s)
    if w:
        out['work'] = dict(to=w['to'], career=w['career'], n=w['n'], need=w['need'], pct=w['pct'], fee=w['fee'], start=w['start'])
    from . import employment
    jobs = []
    for cid, c in (s.get('careers') or {}).items():
        job = c.get('job') if isinstance(c, dict) else None
        if not isinstance(job, dict) or job.get('status') != 'hired' or not employment.required(cid):
            continue
        jobs.append(dict(career=cid, title=str(job.get('title') or ''), why=_eligible(s, cid), open=bool(c.get('open')),
                         pay=employment.day_pay(s, c, cid)))   # a day at home; abroad: × (100 + pct) / 100
    out['jobs'] = jobs
    return out


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu du học không hợp lệ.'
    b = j[KEY]
    need(isinstance(b, dict) and BLOCK_KEYS <= set(b), bad, 'invalid_save')   # keys a newer build adds are kept
    need(b['v'] == VERSION, bad, 'invalid_save')
    st = b['study']
    if st is not None:
        need(isinstance(st, dict) and set(st) == STUDY_KEYS and st['p'] in C.PROGRAMS, bad, 'invalid_save')
        total = len(C.PROGRAMS[st['p']]['lessons'])
        integer(st['n'], 0, total - 1)
        integer(st['ok'], 0, st['n'])
        integer(st['start'], 1, 10**6)
        integer(st['last'], 0, 10**6)
        integer(st['fee'], 0, 10**7)
    need(isinstance(b['deg'], dict) and len(b['deg']) <= 64, bad, 'invalid_save')
    for k, v in b['deg'].items():
        need(isinstance(k, str) and len(k) <= 24 and isinstance(v, dict) and DEG_KEYS <= set(v), bad, 'invalid_save')
        integer(v['d'], 1, 10**6)
        need(v['g'] in GRADE_IDS or k not in C.PROGRAMS, bad, 'invalid_save')
    w = b['work']
    if w is not None:
        need(isinstance(w, dict) and set(w) == WORK_KEYS and w['to'] in C.WORK and w['career'] in (s.get('careers') or {}), bad, 'invalid_save')
        need(w['emp'] is None or isinstance(w['emp'], str) and len(w['emp']) <= 80, bad, 'invalid_save')
        integer(w['hd'], 0, 10**9)
        integer(w['need'], 1, 60)
        integer(w['n'], 0, w['need'] - 1)
        integer(w['pct'], 0, 100)
        integer(w['fee'], 0, 10**7)
        integer(w['start'], 1, 10**6)
    integer(b['back'], 0, 10**6)
    need(isinstance(b['done'], dict) and len(b['done']) <= 64, bad, 'invalid_save')
    for k, v in b['done'].items():
        need(isinstance(k, str) and len(k) <= 24, bad, 'invalid_save')
        integer(v, 0, 10**6)
