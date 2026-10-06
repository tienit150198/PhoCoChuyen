"""Nhân viên cứu hộ hồ bơi: a day on the high chair at Hồ bơi Sóng Xanh, the ward's public pool (plugin career).

The player is a newly hired lifeguard (employment: CV and interview; the "Chứng chỉ Cứu hộ hồ bơi" certificate raises
the hire chance) under anh Hải, the head lifeguard. One task is one piece of the shift:

* ``open`` (slot 0): open the pool. Check each item one by one (the water's clarity, the chlorine and pH test strip
  against the game's card, the drain cover, the rescue tube, the ring buoy and pole, the first-aid kit, the depth
  signs, the emergency phone), write the strip's numbers in the water log, fix what is the lifeguard's to fix (the
  spare tube, the pole back on its rack, the kit refilled, the sign put back), report each fault through the right
  channel (the shift book, the technician's slip, a call to the manager) and decide: open on time, or hold the gate
  until the technician has made it safe (cloudy water, the strip off the card, a loose drain cover);
* ``watch``: a scan of the five zones on a clock (look at all five within a minute). Whistle the right rule at the
  right person (running, diving into the shallow end, glass, a small child without an adult, backflips, lanes, swim
  caps, filming, a fake cry for help, dunking, a couple blocking a lane, a tired swimmer); the noisy splashing child
  is fine. Somebody may be drowning the quiet way (upright, head back, mouth at the water, no headway, no sound) or
  lying on the bottom: sound the alarm, get backup, reach or throw before going in and never go in without the tube,
  check their breathing, then care for them the right way (never upside down to "drain the water"; 115 and the AED
  when they do not breathe);
* ``gate``: three people at the gate; look, ask, then let each one in, in after a fix (cap, shower, glass left at
  the desk), in the shallow end with an adult, or not in the water today (beer, an open wound, diarrhoea, red eyes,
  a tight chest);
* ``lesson``: a children's class: the pick-up sheet, a swim test for each child (the one who says he can swim
  cannot), a wristband by what the test showed, today's two topics, and a head count when they come out;
* ``aid``: first aid at the pool's post (gloves first, no medicine from your own pocket, never tilt a nosebleed
  back, keep a neck still after a dive into the shallows, 115 for breathing trouble);
* ``storm``: thunder. Everyone out and into the concrete hall (not under a canvas roof, not under a tree), count
  heads, wait, answer the manager who wants to reopen for the takings, and reopen only thirty minutes after the last
  thunder (Nội quy Sóng Xanh, a game rule).

Around the tasks: the awkward people of the pool (air_odd engine, game/careers/lifeguard_content.py ODD), desk
surprises, real-life situations, and the end-of-shift log written from what really happened. Safety is always the
right choice: a cut corner is a slip (consequences.slip), giving in to a push costs conduct points. Money only through
the engine (the daily salary, a small bonus per task). Everything random comes from (day, slot) or the task id:
make_task is pure. The scan's clock reads kit.tap_now (the moment of the tap, not of the network).
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import air_odd as ao
from . import street_folk as folk
from .. import consequences as cq
from . import lifeguard_content as LC
from .lifeguard_content import (PEOPLE, ZONES, ZONE_IDS, CHECKS, CHECK_IDS, CHANNELS, FAULTS, RULES, WATCH, METHODS, METHOD_GRADE,
                                METHOD_FAIL, ASSESS, CARE, CARE_GRADE, CARE_OUT, CARE_BAD, VERDICTS, STRICT, GATE, BANDS, BAND_ORDER, KIDS,
                                TOPICS, TOPIC_LINE, LESSONS, AID, SHELTERS, SHELTER_GRADE, STORMS, REPLIES)

ID = 'lifeguard'
GEN = 1
BONUS = 10            # xu per task done by the book (a performance bonus: the salary is the pay)
LEARN = 3             # anh Hải sits beside you for the first three tasks after the opening
FACTS_MAX = 14
SWEEP_S = 60          # seconds to look at all five zones once (a game rule, after the pools' "scan in ten seconds")
ALARM_S = 90          # seconds from the start of the scan to the alarm for someone drowning
KINDS = ('open', 'watch', 'gate', 'lesson', 'aid', 'storm')
STAGES = ('open', 'done')
MODS = LC.MODS
MOD = {m['id']: m for m in MODS}
HAI, PHUONG, TU, HANG, BON, MAI, KHA, TAM = range(8)
DROWNING = ('distress', 'sink')
RULE_KINDS = tuple(RULES)

# The words of the encounters (air_odd): who to bring in, the office, what a demotion or a stand-down is called here.
CFG = dict(crew='🛟 Gọi anh Hải', company='💼 Báo quản lý hồ', union='Nhờ công đoàn', office='Ban giám đốc Trung tâm',
           demoted='cứu hộ tập sự', title='cứu hộ viên',
           labels={'charm': dict(duty='Mình đang trực ghế.', rule='Hồ không cho nhân viên hẹn hò, nhận quà của khách.',
                                 alt='Cảm ơn, chúc bạn bơi vui.')},
           ground_line='⚖️ Ban giám đốc Trung tâm: tạm đình chỉ trực ghế hết hôm nay, mai lên trình bày.',
           harass_note='🛡️ Báo là đúng: trung tâm có quy trình bảo vệ nhân viên và khách.',
           demote_line='⚖️ Hội đồng kỷ luật Trung tâm: hạ xuống {demoted}, tạm đình chỉ trực hôm nay, không có thưởng tới khi hồ sơ sạch lại.',
           tired_line='😮‍💨 Mệt rồi: thưởng việc chỉ còn một nửa. Xin nghỉ bù ở phòng trực.',
           rest_ok=' Ghế của bạn đã có người ngồi thay; bạn thấy nhẹ cả người.',
           levels={'ground': 'Tạm đình chỉ trực'})


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    """The day's mood. Day two is always the first afternoon storm: thunder is taught early, not by luck."""
    return MOD['storm'] if day == 2 else kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError, AttributeError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Khách bơi'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _num(v) -> str:
    """A typed reading, normalised: '7.4' and '7,4' are the same; '2,0' is '2'."""
    s = str(v or '').strip().replace(' ', '').replace('.', ',')
    if ',' in s:
        a, _, b = s.partition(',')
        b = b.rstrip('0')
        return f'{a.lstrip("0") or "0"},{b}' if b else (a.lstrip('0') or '0')
    return s.lstrip('0') or ('0' if s else '')


def _value(raw: str) -> float:
    return float(str(raw).replace(',', '.'))


def on_card(what: str, raw: str) -> bool:
    """The game's water card ("Bảng mẫu Sóng Xanh"): a simplified game rule."""
    lo, hi = LC.CARD[what]
    return lo <= _value(raw) <= hi


def _minutes(hhmm: str) -> int:
    h, _, m = hhmm.partition(':')
    return int(h) * 60 + int(m)


def _rot(rows: tuple, day: int, slot: int, opened: int, salt: str) -> str:
    """A case from a rotation: the first `opened` rows on early days, all of them later (pure)."""
    pool = rows[:max(1, min(len(rows), opened))]
    return pool[kit.rng(ID, salt, day, slot).randrange(len(pool))]


def _opened(day: int, simple: int, total: int) -> int:
    return simple if day <= 1 else simple + 2 if day == 2 else total


# ================================================================ tasks
def faults_of(day: int) -> list:
    """What is wrong at the pool this morning (pure): day one, one thing the lifeguard fixes; later one or two."""
    r = kit.rng(ID, 'faults', day)
    if day <= 1:
        return [LC.EASY_FAULTS[r.randrange(len(LC.EASY_FAULTS))]]
    mod = mod_of(day)['id']
    out = []
    if mod == 'inspect' or r.random() < 0.45:
        out.append(LC.STOP_FAULTS[r.randrange(len(LC.STOP_FAULTS))])
    if not out or r.random() < 0.5:
        out.append(LC.FIX_FAULTS[r.randrange(len(LC.FIX_FAULTS))])
    return out


def _weights(day: int, mod: str) -> list:
    w = {'watch': 3, 'gate': 2, 'aid': 2, 'lesson': 1 if day >= 2 else 0}
    if mod == 'hot':
        w['gate'] += 2
        w['aid'] += 1
        w['watch'] += 1
    elif mod == 'class':
        w['lesson'] += 3
    elif mod == 'inspect':
        w['watch'] += 1
    return [(k, v) for k, v in w.items() if v]


def task_kind(day: int, slot: int) -> str:
    if slot <= 0:
        return 'open'
    if slot == 1:
        return 'watch'
    if day == 1:
        return ('gate', 'watch', 'aid', 'lesson', 'watch')[(slot - 2) % 5]
    mod = mod_of(day)['id']
    if mod == 'storm' and slot == 2:
        return 'storm'
    prev = task_kind(day, slot - 1) if slot > 2 else 'watch'
    rows = [(k, v) for k, v in _weights(day, mod) if k != prev]
    total = sum(v for _, v in rows)
    x = kit.rng(ID, 'kind', day, slot).random() * total
    for k, v in rows:
        x -= v
        if x < 0:
            return k
    return rows[-1][0]


def _case(day: int, slot: int, kind: str) -> str:
    if kind == 'watch':
        if day == 1:
            return 'w-run' if slot == 1 else LC.WATCH_DAY1
        return _rot(LC.WATCH_ROTATION, day, slot, _opened(day, 5, len(LC.WATCH_ROTATION)), 'watch')
    if kind == 'lesson':
        return _rot(LC.LESSON_ROTATION, day, slot, len(LC.LESSON_ROTATION), 'lesson')
    if kind == 'aid':
        return _rot(LC.AID_ROTATION, day, slot, _opened(day, 4, len(LC.AID_ROTATION)), 'aid')
    if kind == 'storm':
        return LC.STORM_ROTATION[0] if day <= 2 else _rot(LC.STORM_ROTATION, day, slot, len(LC.STORM_ROTATION), 'storm')
    return ''


def _queue(day: int, slot: int) -> list:
    """Three people at the gate: one who must not swim (or only with an adult), one who needs a fix, one more (pure)."""
    r = kit.rng(ID, 'gate', day, slot)
    a = LC.GATE_SERIOUS[r.randrange(len(LC.GATE_SERIOUS))]
    b = LC.GATE_FIX[r.randrange(len(LC.GATE_FIX))]
    rest = [k for k in GATE if k not in (a, b)]
    c = rest[r.randrange(len(rest))]
    out = [a, b, c]
    r.shuffle(out)
    return out


def _common() -> dict:
    return dict(gen=GEN, stage='open', washed=False, seen=[], marks={}, step=0, sweep=None, choice=None, result=None, story=None)


def make_task(day: int, slot: int, serial: int) -> dict:
    kind = task_kind(day, slot)
    c = _common()
    if kind == 'open':
        return kit.base_task(ID, day, slot, serial, HAI, 'Mở hồ buổi sáng',
                             'Anh Hải: “Sáu giờ mở cổng. Thử từng món một, món nào hỏng thì sửa hoặc báo, chưa an toàn thì chưa mở nhé.”',
                             kind='open', needs=dict(checks=list(CHECK_IDS)), _v=dict(faults=faults_of(day)), **c)
    if kind == 'gate':
        q = _queue(day, slot)
        npc = TU if 'g-cap' in q else BON if 'g-bon' in q else PHUONG
        needs = dict(queue=[dict(who=GATE[k]['who'], emoji=GATE[k]['emoji']) for k in q])
        return kit.base_task(ID, day, slot, serial, npc, 'Soát người ở cổng xuống hồ',
                             'Chị Phượng: “Cổng đông rồi em, ra soát giúp chị. Ai xuống nước được thì cho vào, ai chưa được thì nói khéo.”',
                             kind='gate', needs=needs, _v=dict(cases=q), **c)
    case = _case(day, slot, kind)
    if kind == 'watch':
        return kit.base_task(ID, day, slot, serial, HAI, 'Canh hồ: một vòng quét',
                             'Lên ghế cao, quàng dây phao ống, còi trên môi. Quét đủ năm khu, mắt không rời mặt nước.',
                             kind='watch', needs=dict(zones=list(ZONE_IDS)), _v=dict(case=case), **c)
    if kind == 'lesson':
        x = LESSONS[case]
        npc = BON if 'bon' in x['kids'] else MAI
        needs = dict(kids=[dict(id=k, name=KIDS[k]['name'], emoji=KIDS[k]['emoji'], age=KIDS[k]['age'], claim=KIDS[k]['claim']) for k in x['kids']],
                     topics=list(x['topics']))
        return kit.base_task(ID, day, slot, serial, npc, 'Lớp bơi trẻ em ở khu cạn',
                             'Ba bé mặc đồ bơi xếp hàng ở bậc khu cạn. Anh Hải dặn: “Bơi thử từng đứa rồi mới phát vòng tay.”',
                             kind='lesson', needs=needs, _v=dict(case=case), **c)
    if kind == 'aid':
        x = AID[case]
        return kit.base_task(ID, day, slot, serial, x['npc'], f'Sơ cứu: {x["who"]}',
                             'Có người cần sơ cứu ở bờ hồ. Mang hộp sơ cứu tới.', kind='aid', needs=dict(who=x['who']), _v=dict(case=case), **c)
    x = STORMS[case]
    return kit.base_task(ID, day, slot, serial, PHUONG, 'Dông chiều',
                         f'{x["events"][0][0]} · {x["events"][0][3]}', kind='storm', needs=dict(start=x['events'][0][0]), _v=dict(case=case), **c)


FIXED = ('needs', '_v')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t.get('kind') == 'open':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the pool's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, tasks=0, whistles=0, rescues=0, closed=0, safety=0, gate=0, facts=[], report=None)


def initial() -> dict:
    return dict(v=1, intro=False, regulars={}, today=_fresh_today(0), learn=dict(n=0, caught=[]),
                stats=dict(tasks=0, whistles=0, rescues=0, closed=0, safety=0, gate=0, kids=0, aid=0, reports=0, honest=0),
                desk=kit.desk_initial(), odd=ao.initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'learn'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, copy.deepcopy(v))
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    ao.ensure(d)
    return d


def _pressure(c: dict, d: dict) -> int:
    """How hard the pool leans on its lifeguards today: a crowded day, and a lifeguard who snapped at the office."""
    marks = d['odd']['marks']
    return {'hot': 1, 'class': 1, 'storm': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


def _stat(d: dict, key: str, n: int = 1) -> None:
    if key in d['today']:
        d['today'][key] += n
    d['stats'][key] = min(10 ** 7, d['stats'].get(key, 0) + n)


# ================================================================ the actions
FREE = ('hb_intro', 'hb_rest')
NO_TICK = ('hb_intro', 'hb_rest', 'hb_check', 'hb_log', 'hb_scan', 'hb_look', 'hb_desk', 'hb_odd', 'hb_report', 'hb_gq', 'hb_verdict',
           'hb_assess', 'hb_sheet', 'hb_test', 'hb_band', 'hb_aidask', 'hb_gloves', 'hb_sky')
PHYSICAL = ('hb_alarm', 'hb_method', 'hb_aid', 'hb_shelter')
GROUNDED = ('hb_open', 'hb_scan', 'hb_alarm', 'hb_method', 'hb_round', 'hb_gate', 'hb_lesson', 'hb_aid', 'hb_shelter', 'hb_reopen')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'hb_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Anh Hải đang chờ ở ghế trực.')
    odd = d['odd']
    if name == 'hb_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    desk = d['desk']
    if name == 'hb_desk':
        result = kit.desk_choose(s, c, ID, desk, LC.DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'hb_odd':
        result = ao.reply(s, c, ID, odd, LC.ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    kit.desk_block(desk, 'Có chuyện ở hồ, quyết xong rồi làm tiếp nhé.')
    ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
    kit.need(not (ao.grounded(c, odd) and name in GROUNDED), 'Bạn đang bị tạm đình chỉ trực ghế hết hôm nay. Tan ca, mai lên trung tâm trình bày.', 'grounded')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở hồ bơi.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _sweeping(c: dict) -> bool:
    """A scan is running (started, not finished): nobody walks up to the chair while the clock runs."""
    return any(t.get('career') == ID and t.get('kind') == 'watch' and t.get('sweep') is not None and t.get('stage') == 'open'
               and t['status'] not in ('completed', 'cancelled', 'referred') for t in c['tasks'])


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    if _sweeping(c):
        return
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, LC.DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(LC.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
        return
    _odd_tick(s, c, d, result)


def _odd_tick(s: dict, c: dict, d: dict, result: dict) -> None:
    """Someone around the pool turns up when today's plan says so (never over an open desk surprise or a running scan)."""
    if _sweeping(c):
        return
    x = ao.tick(s, c, ID, d['odd'], LC.ODD, busy=d['desk']['ev'] is not None)
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None, known: bool = True) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc hồ bơi.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    if known:
        kit.need(t['known'], 'Tới chỗ đó xem chuyện gì trước đã.')
    kit.need(t['stage'] == 'open', 'Việc này đã xong.')
    return t


# ---------------------------------------------------------------- anh Hải beside you (the first three tasks after the opening)
def _guard(d: dict, code: str, line: str) -> dict | None:
    """In the first tasks anh Hải stops each kind of mistake once, before it is made (nothing is recorded)."""
    lr = d['learn']
    if lr['n'] >= LEARN or code in lr['caught'] or len(lr['caught']) >= 24:
        return None
    lr['caught'].append(code)
    return dict(message=f'✋ Anh Hải giữ tay bạn lại: “{line}”', correct=False)


def _tr(t: dict, salt: str = '') -> dict:
    i = _npc_index(t)
    return folk.traits(f'{t["id"]}{salt}', PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None)


# ---------------------------------------------------------------- opening the pool
def _faults(t: dict) -> dict:
    """check id -> fault id, for this morning's faults."""
    return {FAULTS[f]['check']: f for f in t['_v']['faults']}


def _strip(t: dict) -> dict:
    f = _faults(t).get('strip')
    return FAULTS[f]['strip'] if f else LC.STRIP_OK


def _check(s, c, d, p):
    t = _task(c, p, ('open',))
    what = kit.one_of(p.get('what'), CHECK_IDS, 'Món này không có trong danh sách mở hồ.')
    kit.need(what not in t['seen'], 'Đã kiểm món này rồi.')
    t['seen'].append(what)
    kit.start_work(t)
    e, label, ok = CHECKS[what]
    f = _faults(t).get(what)
    if what == 'strip':
        st = _strip(t)
        line = f'🧪 Nhúng que thử, so bảng mẫu: Clo {st["cl"]} · pH {st["ph"]}.'
        return dict(message=f'{line} {FAULTS[f]["text"]}' if f else line)
    if f:
        return dict(message=f'⚠️ {e} {label}: {FAULTS[f]["text"]}')
    return dict(message=f'✅ {e} {label}: {ok}')


def _log(s, c, d, p):
    t = _task(c, p, ('open',))
    kit.need('strip' in t['seen'], 'Thử que trước rồi mới ghi sổ nước.')
    kit.need('cl' not in t['marks'], 'Sổ nước hôm nay đã ghi rồi.')
    cl = kit.text(str(p.get('cl', '')), 8, 0).strip()
    ph = kit.text(str(p.get('ph', '')), 8, 0).strip()
    kit.need(cl and ph, 'Ghi đủ hai ô Clo và pH.')
    st = _strip(t)
    wrong = [k for k, v in (('cl', cl), ('ph', ph)) if _num(v) != _num(st[k])]
    if wrong:
        g = _guard(d, 'log', 'Số ghi chưa khớp que thử. Nhìn lại que rồi ghi đúng số nhé.')
        if g:
            return g
    t['marks']['cl'] = cl[:8]
    t['marks']['ph'] = ph[:8]
    if wrong:
        t['mistakes'] += 1
        cq.slip(t, 'log', 2, 'Sổ nước ghi số khác que thử thật.', 'ghi sổ nước sai số')
        return dict(message='📒 Đã ghi sổ nước. (Số ghi không khớp que thử.)', correct=False)
    off = [k for k in ('cl', 'ph') if not on_card(k, st[k])]
    tail = ' Có số ngoài bảng mẫu: chưa mở hồ, báo anh Tâm.' if off else ' Cả hai đều trong bảng mẫu.'
    return dict(message=f'📒 Sổ nước: Clo {cl} · pH {ph}.{tail}')


def _fix(s, c, d, p):
    t = _task(c, p, ('open',))
    what = kit.one_of(p.get('what'), CHECK_IDS, 'Món này không có trong danh sách mở hồ.')
    kit.need(what in t['seen'], 'Kiểm món đó trước đã.')
    f = _faults(t).get(what)
    kit.need(f and FAULTS[f]['fix'], 'Món này không có gì để tự sửa.')
    kit.need(f'fix:{what}' not in t['seen'], 'Đã xử lý rồi.')
    t['seen'].append(f'fix:{what}')
    return dict(message=f'🔧 {FAULTS[f]["fix"]}.')


REPORT_LINE = {
    'book': '📒 Ghi sổ trực ca: {label} — {text}',
    'tech': '🔧 Phiếu báo anh Tâm: {label}. Anh Tâm: “Để anh xuống xem ngay.”',
    'boss': '📞 Gọi chị Phượng: {label}. Chị Phượng: “Rồi, chị xuống liền.”',
}


def _rep(s, c, d, p):
    t = _task(c, p, ('open',))
    what = kit.one_of(p.get('what'), CHECK_IDS, 'Món này không có trong danh sách mở hồ.')
    to = kit.one_of(p.get('to'), CHANNELS, 'Chọn nơi báo.')
    kit.need(what in t['seen'], 'Kiểm món đó trước đã.')
    f = _faults(t).get(what)
    kit.need(f, 'Món này ổn, không có gì phải báo.')
    kit.need(f'rep:{what}' not in t['marks'], 'Đã báo chuyện này rồi.')
    x = FAULTS[f]
    if to not in x['to']:
        g = _guard(d, 'channel', 'Chuyện này ai xử lý được? Ghi sổ thôi thì ca sau mới biết.' if x['stop'] else
                   'Chuyện nhỏ mình xử lý được thì ghi sổ trực là đủ, khỏi làm phiền cả trung tâm.')
        if g:
            return g
    t['marks'][f'rep:{what}'] = to
    if to not in x['to']:
        t['mistakes'] += 1
        cq.slip(t, 'channel', 2 if x['stop'] else 1, 'Báo không đúng người xử lý, chuyện cần làm ngay phải chờ.', 'báo chưa đúng kênh')
    return dict(message=REPORT_LINE[to].format(label=CHECKS[what][1], text=x['text']))


def _open(s, c, d, p):
    t = _task(c, p, ('open',))
    decision = kit.one_of(p.get('decision'), ('open', 'delay'), 'Mở hồ hay hoãn?')
    faults = [FAULTS[f] | dict(id=f) for f in t['_v']['faults']]
    stops = [x for x in faults if x['stop']]
    unchecked = [k for k in CHECK_IDS if k not in t['seen']]
    if unchecked:
        g = _guard(d, 'skip', f'Còn {len(unchecked)} món chưa kiểm. Thử đủ từng món rồi hẵng quyết.')
        if g:
            return g
    if decision == 'open':
        found = [x for x in stops if x['check'] in t['seen']]
        if found:
            g = _guard(d, 'stop', f'{CHECKS[found[0]["check"]][1]} chưa an toàn. Chưa xử lý xong thì chưa mở cổng.')
            if g:
                return g
    elif not stops:
        g = _guard(d, 'needless', 'Mọi thứ đã ổn rồi mà, mở cổng cho khách vào thôi.')
        if g:
            return g
    for x in faults:
        if x['fix'] and x['check'] in t['seen'] and f'fix:{x["check"]}' not in t['seen']:
            g = _guard(d, 'fix', f'{CHECKS[x["check"]][1]}: mình tự xử lý được mà. Làm trước khi mở nhé.')
            if g:
                return g
    if 'strip' in t['seen'] and 'cl' not in t['marks']:
        g = _guard(d, 'nolog', 'Ghi số que thử vào sổ nước trước đã.')
        if g:
            return g
    inspect = mod_of(c['day'])['id'] == 'inspect'
    if unchecked:
        t['mistakes'] += 1
        cq.slip(t, 'skip', 2 if inspect else 1, f'Mở hồ mà chưa kiểm {_lower(CHECKS[unchecked[0]][1])}.', 'chưa kiểm đủ trước khi mở')
    for x in faults:
        seen = x['check'] in t['seen']
        if x['stop']:
            if decision == 'open':
                t['mistakes'] += 1
                cq.slip(t, x['id'], x['sev'], x['slip'], 'mở hồ khi chưa an toàn', safety=x['safety'])
        elif f'fix:{x["check"]}' not in t['seen']:
            t['mistakes'] += 1
            cq.slip(t, x['id'], x['sev'], x['slip'], 'chưa xử lý đồ cứu hộ', safety=x['safety'])
        if seen and f'rep:{x["check"]}' not in t['marks']:
            t['mistakes'] += 1
            cq.slip(t, 'unreported', 2 if x['stop'] else 1, 'Có chuyện mà không ghi lại, không báo ai: ca sau không biết.', 'không báo lại')
    if decision == 'delay' and not stops:
        t['mistakes'] += 1
        cq.slip(t, 'needless', 1, 'Mọi thứ ổn mà hoãn mở, khách đứng nắng ngoài cổng.', 'hoãn mở không cần thiết')
    if 'strip' in t['seen'] and 'cl' not in t['marks']:
        t['mistakes'] += 1
        cq.slip(t, 'nolog', 2 if inspect else 1, 'Thử que mà không ghi sổ nước.', 'chưa ghi sổ nước')
    t['choice'] = decision
    t['result'] = decision
    if decision == 'delay':
        _stat(d, 'closed')
    unsafe = cq.safety(t)
    if decision == 'delay':
        head = f'⏳ Hoãn mở hồ. {stops[0]["delay"]}' if stops else '⏳ Hoãn mở hồ, khách đứng chờ ngoài cổng.'
    else:
        head = '🔓 Mở cổng đón khách. Ông Tư là người đầu tiên, khăn vắt vai.'
    fact = ('Mở hồ: kiểm đủ, ' + ('hoãn tới khi kỹ thuật xử lý xong.' if decision == 'delay' else 'mở đúng giờ.')) if not unchecked else 'Mở hồ: chưa kiểm đủ các món.'
    if t['marks'].get('cl'):
        fact += f' Sổ nước: Clo {t["marks"]["cl"]}, pH {t["marks"]["ph"]}.'
    _fact(d, t, fact, key=bool(stops) or unsafe, lie='Mở hồ: kiểm đủ từng món, mọi thứ an toàn.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, 0, 'Mở hồ buổi sáng.' if decision == 'open' else 'Hoãn mở hồ chờ kỹ thuật.', counted=False)
    if unsafe:
        msg += ' 📋 Anh Hải lập biên bản, đóng cổng lại kiểm tra từ đầu.'
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t), correct=not unsafe)


# ---------------------------------------------------------------- the scan
def _zone(t: dict, z: str) -> tuple:
    return WATCH[t['_v']['case']]['zones'][z]


def _drowning(t: dict) -> str | None:
    return next((z for z in ZONE_IDS if _zone(t, z)[0] in DROWNING), None)


def _rescue(t: dict) -> dict:
    return WATCH[t['_v']['case']].get('rescue') or {}


def _elapsed(t: dict, p: dict) -> float:
    return max(0.0, kit.tap_now(p) - float(t['sweep'] or 0))


def _scan(s, c, d, p):
    t = _task(c, p, ('watch',))
    kit.need(t['sweep'] is None, 'Vòng quét đang chạy rồi.')
    t['sweep'] = round(kit.tap_now(p), 3)
    kit.start_work(t)
    return dict(message=f'👀 Bắt đầu vòng quét: nhìn lần lượt năm khu, đủ năm khu trong {SWEEP_S} giây.')


def _look(s, c, d, p):
    t = _task(c, p, ('watch',))
    kit.need(t['sweep'] is not None, 'Bắt đầu vòng quét trước đã.')
    z = kit.one_of(p.get('zone'), ZONE_IDS, 'Khu này không có ở hồ.')
    kit.need(f'z:{z}' not in t['seen'], 'Đã nhìn khu này rồi.')
    t['seen'].append(f'z:{z}')
    late = ''
    if all(f'z:{k}' in t['seen'] for k in ZONE_IDS) and _elapsed(t, p) > SWEEP_S:
        t['mistakes'] += 1
        cq.slip(t, 'slow', 1, 'Một vòng quét mà lâu quá, có khu không ai nhìn cả phút.', 'quét chậm')
        late = ' ⏱️ Vòng quét quá một phút.'
    e, name = ZONES[z]
    return dict(message=f'{e} {name}: {_zone(t, z)[1]}{late}')


def _whistle(s, c, d, p):
    t = _task(c, p, ('watch',))
    z = kit.one_of(p.get('zone'), ZONE_IDS, 'Khu này không có ở hồ.')
    rule = kit.one_of(p.get('rule'), RULES, 'Chọn điều cần nhắc.')
    kit.need(f'z:{z}' in t['seen'], 'Nhìn khu đó trước đã.')
    kit.need(f'w:{z}' not in t['marks'], 'Đã thổi còi khu này rồi.')
    kind, _, react = _zone(t, z)
    e, label = RULES[rule]
    if kind in DROWNING:
        g = _guard(d, 'misread', 'Người đó không vi phạm gì đâu: nhìn kỹ lại, họ đang chìm!')
        if g:
            return g
        t['marks'][f'w:{z}'] = rule
        t['mistakes'] += 1
        cq.slip(t, 'misread', 2, 'Người đang chìm mà cứu hộ tưởng họ nghịch, chỉ thổi còi nhắc.', 'không nhận ra người đuối nước')
        return dict(message='📣 Tuýt! Người đó không phản ứng gì, đầu vẫn ngửa ra sau, miệng ngang mặt nước…', correct=False)
    if kind == 'ok':
        g = _guard(d, 'nag', 'Ở đó có ai làm sai đâu. Ồn ào, té nước mà đứng vững là đang chơi thôi.')
        if g:
            return g
        t['marks'][f'w:{z}'] = rule
        t['mistakes'] += 1
        cq.slip(t, 'nag', 1, 'Đang bơi đàng hoàng mà bị thổi còi nhắc.', 'thổi còi nhầm')
        return dict(message=f'📣 Tuýt! “{label}.” Khách ngơ ngác: “Tui làm gì sai?”', correct=False)
    if rule != kind:
        g = _guard(d, 'wrong_rule', 'Nhắc cho đúng chuyện người ta đang làm thì họ mới nghe.')
        if g:
            return g
        t['marks'][f'w:{z}'] = rule
        t['mistakes'] += 1
        cq.slip(t, 'wrong_rule', 1, 'Bị thổi còi nhắc một chuyện mình không làm.', 'nhắc sai luật')
        return dict(message=f'📣 Tuýt! “{label}.” Người ta ngơ ngác vì lời nhắc không đúng chuyện.', correct=False)
    t['marks'][f'w:{z}'] = rule
    _stat(d, 'whistles')
    return dict(message=f'📣 Tuýt! “{label}.” {react}')


def _alarm(s, c, d, p):
    t = _task(c, p, ('watch',))
    z = kit.one_of(p.get('zone'), ZONE_IDS, 'Khu này không có ở hồ.')
    kit.need(f'z:{z}' in t['seen'], 'Nhìn khu đó trước đã.')
    kit.need('alarm' not in t['marks'], 'Đang cứu người rồi.')
    kind = _zone(t, z)[0]
    if kind not in DROWNING:
        kit.need('false' not in t['marks'], 'Bình tĩnh nhìn lại từng khu đã.')
        g = _guard(d, 'false_alarm', 'Khoan! Người đó đứng được, đang cười. Người đuối nước thật thì im lặng, không vẫy được.')
        if g:
            return g
        t['marks']['false'] = z
        t['mistakes'] += 1
        cq.slip(t, 'false_alarm', 1, 'Còi báo động vang lên mà không ai gặp nạn, cả hồ hoảng hồn.', 'báo động nhầm')
        return dict(message='🚨 Bạn thổi còi dài, nhảy khỏi ghế… người đó đứng dậy, nước chỉ tới ngực, ngơ ngác nhìn bạn.', correct=False)
    t['marks']['alarm'] = z
    kit.start_work(t)
    if _elapsed(t, p) > ALARM_S:
        t['mistakes'] += 1
        cq.slip(t, 'late', 2, 'Người chìm cả phút rưỡi mới có còi báo động.', 'báo động chậm')
    return dict(message=f'🚨 Còi dài! Bạn báo động, mắt không rời {_lower(ZONES[z][1])}. Gọi hỗ trợ, rồi chọn cách đưa người vào.')


def _backup(s, c, d, p):
    t = _task(c, p, ('watch',))
    kit.need('alarm' in t['marks'], 'Chưa có ai cần cứu.')
    kit.need('help' not in t['marks'], 'Đã gọi rồi.')
    how = kit.one_of(p.get('how'), ('team', 'alone'), 'Gọi hỗ trợ hay tự làm?')
    if how == 'alone':
        g = _guard(d, 'alone', 'Ba hồi còi gọi anh! Một mình vừa cứu vừa trông cả hồ là không được.')
        if g:
            return g
        t['marks']['help'] = 'alone'
        t['mistakes'] += 1
        cq.slip(t, 'alone', 2, 'Cứu hộ xuống cứu người, cả hồ không ai trông, không ai gọi 115.', 'không gọi hỗ trợ')
        return dict(message='🤐 Bạn tự làm một mình. Ghế trực trống, cả hồ vẫn bơi như không có chuyện gì.', correct=False)
    t['marks']['help'] = 'team'
    st = _rescue(t).get('state', 'awake')
    tail = ' Lễ tân gọi 115, anh Hải mang máy AED và hộp sơ cứu chạy tới.' if st != 'awake' else ''
    return dict(message=f'📣 Ba hồi còi: anh Hải lên ghế trông hồ, mời mọi người lên bờ.{tail}')


def _method(s, c, d, p):
    t = _task(c, p, ('watch',))
    kit.need('alarm' in t['marks'], 'Chưa có ai cần cứu.')
    kit.need('method' not in t['marks'], 'Đã đưa người vào bờ rồi.')
    m = kit.one_of(p.get('method'), METHODS, 'Chọn cách cứu.')
    kit.need(f'fail:{m}' not in t['seen'], 'Cách đó vừa không được, thử cách khác.')
    res = _rescue(t)
    where, st = res.get('where', 'edge'), res.get('state', 'awake')
    grade = METHOD_GRADE[where][m]
    if grade == 'fail':
        g = _guard(d, 'fail', 'Xa quá hoặc người không còn tự bám được. Phải xuống nước cùng phao ống thôi.' if st != 'awake' else
                   'Sào không tới được giữa làn đâu. Ném phao hoặc xuống cùng phao ống.')
        if g:
            return g
        t['seen'].append(f'fail:{m}')
        t['mistakes'] += 1
        cq.slip(t, 'delay', 3 if st != 'awake' else 2, 'Mất mấy chục giây với cách không tới được người đang chìm.', 'chọn cách cứu không tới',
                safety=st != 'awake')
        return dict(message=f'⌛ {METHOD_FAIL[m]} Mất thêm mấy chục giây quý giá.', correct=False)
    if grade == 'bad':
        g = _guard(d, 'bare', 'Không bao giờ xuống tay không! Người đuối nước ôm ghì là chìm cả hai. Quàng phao ống vào.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'bare', 2, 'Cứu hộ nhảy xuống tay không, bị người đuối nước ôm ghì chìm cả hai.', 'xuống nước không mang phao')
    elif grade == 'ok':
        t['mistakes'] += 1
        cq.slip(t, 'roundabout', 1, 'Với được từ bờ mà vẫn rời ghế nhảy xuống, mất thêm thời gian.', 'chưa chọn cách an toàn nhất')
    t['marks']['method'] = m
    _stat(d, 'rescues')
    line = {'reach': '🪝 Bạn nằm thấp trên bờ, chìa sào. Bàn tay bé xíu chụp lấy đầu sào, bạn kéo vào thành.',
            'throw': '⭕ Phao tròn bay qua người, rơi ngay tầm tay. Họ ôm chặt, bạn kéo dây vào thành.',
            'go': '🛟 Bạn bước dài xuống nước, mắt không rời người, đưa phao ống tới. Kéo vào thành, anh Hải đỡ lên bờ.',
            'bare': '🏊 Bạn nhảy xuống tay không. Người đuối nước ôm ghì lấy cổ bạn, cả hai chìm một nhịp; anh Hải ném phao xuống kịp.'}[m]
    return dict(message=f'{line} Người đã lên bờ.', correct=grade != 'bad')


def _assess(s, c, d, p):
    t = _task(c, p, ('watch',))
    kit.need('method' in t['marks'], 'Đưa người lên bờ trước đã.')
    kit.need('assess' not in t['seen'], 'Đã xem rồi.')
    t['seen'].append('assess')
    return dict(message=f'🩺 {ASSESS[_rescue(t).get("state", "awake")]}')


def _care(s, c, d, p):
    t = _task(c, p, ('watch',))
    kit.need('method' in t['marks'], 'Đưa người lên bờ trước đã.')
    kit.need('care' not in t['marks'], 'Đã sơ cứu rồi.')
    k = kit.one_of(p.get('care'), CARE, 'Chọn cách sơ cứu.')
    st = _rescue(t).get('state', 'awake')
    grade = CARE_GRADE[st][k]
    if 'assess' not in t['seen']:
        g = _guard(d, 'assess', 'Gọi to, vỗ vai, nhìn ngực mười giây xem có thở không đã rồi mới quyết.')
        if g:
            return g
    if grade == 'unsafe':
        g = _guard(d, f'care_{k}', 'Khoan! Làm vậy là nguy cho người ta. Nhìn lại: họ có tỉnh, có thở không?')
        if g:
            return g
    if 'assess' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'blind', 1, 'Chưa xem tỉnh hay thở mà đã quyết cách sơ cứu.', 'chưa đánh giá trước khi sơ cứu')
    t['marks']['care'] = k
    if grade == 'unsafe':
        t['mistakes'] += 1
        cq.slip(t, 'care', 3, CARE_BAD[k], 'sơ cứu sai, nguy hiểm', safety=True)
        return dict(message=f'⚠️ {CARE_BAD[k]}', correct=False)
    if grade == 'bad':
        t['mistakes'] += 1
        cq.slip(t, 'care_bad', 2, CARE_BAD[k], 'sơ cứu chưa đúng')
        return dict(message=f'😕 {CARE_BAD[k]}', correct=False)
    return dict(message=f'{CARE[k][0]} {CARE_OUT[st]}', celebrate=True)


def _round(s, c, d, p):
    """End the scan: everyone seen, every rule said, anyone in trouble out and cared for."""
    t = _task(c, p, ('watch',))
    kit.need(t['sweep'] is not None, 'Bắt đầu vòng quét trước đã.')
    m = t['marks']
    if 'alarm' in m:
        kit.need('method' in m, 'Đưa người vào bờ trước đã.')
        kit.need('care' in m, 'Sơ cứu, theo dõi người vừa cứu lên đã.')
    unlooked = [z for z in ZONE_IDS if f'z:{z}' not in t['seen']]
    drown = _drowning(t)
    missed_rules = [z for z in ZONE_IDS if _zone(t, z)[0] in RULES and f'w:{z}' not in m]
    if unlooked:
        g = _guard(d, 'unlooked', 'Còn khu chưa nhìn tới. Quét đủ năm khu rồi mới kết thúc vòng.')
        if g:
            return g
    if drown and 'alarm' not in m:
        g = _guard(d, 'missed', 'Nhìn lại: có người không bơi, không kêu, người dựng đứng hoặc nằm im. Đó là người đang chìm!')
        if g:
            return g
    if missed_rules:
        g = _guard(d, 'rule', 'Còn người đang làm sai nội quy mà chưa ai nhắc.')
        if g:
            return g
    if unlooked:
        t['mistakes'] += 1
        cq.slip(t, 'unlooked', 2, f'Cả vòng quét không ai nhìn tới {_lower(ZONES[unlooked[0]][1])}.', 'bỏ sót khu')
    if drown and 'alarm' not in m:
        t['mistakes'] += 1
        cq.slip(t, 'missed', 3, 'Có người chìm lặng lẽ mà cứu hộ không thấy. Anh Hải từ phòng trực chạy ra kéo lên.', 'bỏ sót người đuối nước', safety=True)
    if missed_rules:
        sev = 2 if any(_zone(t, z)[0] in LC.DANGER for z in missed_rules) else 1
        t['mistakes'] += 1
        cq.slip(t, 'missed_rule', sev, f'Không ai nhắc: {_lower(_zone(t, missed_rules[0])[1])}', 'bỏ qua người vi phạm nội quy')
    if 'alarm' in m and m.get('help') is None:
        t['mistakes'] += 1
        cq.slip(t, 'alone', 2, 'Cứu người mà không gọi ai, cả hồ không người trông.', 'không gọi hỗ trợ')
    t['choice'] = 'rescue' if 'alarm' in m else 'scan'
    t['result'] = t['choice']
    unsafe = cq.safety(t)
    n_wh = sum(1 for z in ZONE_IDS if m.get(f'w:{z}') == _zone(t, z)[0])
    if 'alarm' in m:
        z = m['alarm']
        fact = f'Cứu một người ở {_lower(ZONES[z][1])}: báo động, ' + ('có anh Hải hỗ trợ' if m.get('help') == 'team' else 'không gọi hỗ trợ') + \
               f', sơ cứu: {_lower(CARE[m["care"]][1].split(",")[0])}.'
    elif drown:
        fact = 'Vòng quét: CÓ NGƯỜI CHÌM, anh Hải phát hiện và kéo lên.'
    else:
        fact = f'Vòng quét đủ năm khu, thổi còi {n_wh} lần.'
    _fact(d, t, fact, key=bool(drown) or unsafe, lie='Vòng quét đủ năm khu, không có gì bất thường.' if (drown or cq.slips(t)) else None)
    msg = _finish(s, c, d, t, BONUS, 'Canh hồ, một vòng quét.' if not drown else 'Canh hồ và cứu người.')
    if unsafe:
        msg += ' 📋 Anh Hải lập biên bản sự cố, cả nhóm họp rút kinh nghiệm.'
    head = '✅ Hết vòng quét. Mặt hồ yên.' if not drown or 'alarm' in m else '⚠️ Hết vòng quét.'
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t), correct=not unsafe)


# ---------------------------------------------------------------- the gate
def _gq(s, c, d, p):
    t = _task(c, p, ('gate',))
    i = kit.integer(p.get('i'), 0, len(t['_v']['cases']) - 1)
    what = kit.one_of(p.get('what'), ('ask', 'look'), 'Hỏi hay nhìn?')
    key = f'{what}:{i}'
    kit.need(key not in t['seen'], 'Đã xem rồi.')
    t['seen'].append(key)
    kit.start_work(t)
    x = GATE[t['_v']['cases'][i]]
    return dict(message=f'{"👂" if what == "ask" else "👀"} {x["who"]}: {x[what]}')


def _verdict(s, c, d, p):
    t = _task(c, p, ('gate',))
    i = kit.integer(p.get('i'), 0, len(t['_v']['cases']) - 1)
    v = kit.one_of(p.get('verdict'), VERDICTS, 'Chọn cách cho vào.')
    t['marks'][f'v:{i}'] = v
    kit.start_work(t)
    e, label = VERDICTS[v]
    return dict(message=f'{e} {t["needs"]["queue"][i]["who"]}: {_lower(label)}.')


GATE_SAY = {
    'in': '{who} cảm ơn, xuống nước.',
    'fix': '{who} đi sửa rồi vào.',
    'adult': '{who} ở khu cạn, có người lớn kèm sát.',
    'no': '{who} hẹn hôm khác.',
}
GRUMBLE = '{who} càu nhàu một hồi rồi cũng nghe.'


def _gate(s, c, d, p):
    t = _task(c, p, ('gate',))
    cases = t['_v']['cases']
    kit.need(all(f'v:{i}' in t['marks'] for i in range(len(cases))), 'Quyết cho cả ba người đã.')
    under = [i for i, k in enumerate(cases) if STRICT.index(t['marks'][f'v:{i}']) < STRICT.index(GATE[k]['best']) and GATE[k].get('safety')]
    if under:
        g = _guard(d, 'under', f'Xem lại {_lower(GATE[cases[under[0]]]["who"])}: cho xuống nước vậy có an toàn không?')
        if g:
            return g
    lines = []
    worst = 0
    for i, k in enumerate(cases):
        x = GATE[k]
        got = t['marks'][f'v:{i}']
        gi, bi = STRICT.index(got), STRICT.index(x['best'])
        tr = folk.traits(f'{t["id"]}:{i}', PEOPLE[x['npc']][3] if x.get('npc') is not None else None)
        grumble = GRUMBLE.format(who=x['who']) + ' ' if tr['rude'] >= 60 and got != 'in' else ''
        if got == x['best']:
            lines.append(f'{VERDICTS[got][0]} {grumble}' + GATE_SAY[got].format(who=x['who']))
            continue
        if f'ask:{i}' not in t['seen'] and f'look:{i}' not in t['seen']:
            t['mistakes'] += 1
            cq.slip(t, 'blind', 1, 'Cho vào hay không mà chẳng nhìn, chẳng hỏi.', 'quyết khi chưa hỏi, chưa nhìn')
        if gi < bi:
            sev = x['sev'] or 1
            t['mistakes'] += 1
            cq.slip(t, 'let_in' if not x.get('safety') else 'let_in_unsafe', sev, x.get('why') or 'Cho xuống nước khi chưa đủ điều kiện.',
                    'cho xuống nước khi chưa đủ điều kiện', safety=bool(x.get('safety')))
            worst = max(worst, sev)
            lines.append(f'{VERDICTS[got][0]} {x["who"]}: đáng lẽ {VERDICTS[x["best"]][0]} {_lower(VERDICTS[x["best"]][1])}.')
        else:
            t['mistakes'] += 1
            cq.slip(t, 'over', 1, 'Đủ điều kiện mà bị chặn ở cổng, đòi hoàn vé.', 'chặn người đủ điều kiện')
            lines.append(f'{VERDICTS[got][0]} {x["who"]}: hơi khắt khe, {VERDICTS[x["best"]][0]} {_lower(VERDICTS[x["best"]][1])} là đủ.')
    t['choice'] = 'sent'
    t['result'] = 'gate'
    _stat(d, 'gate', len(cases))
    turned = sum(1 for i in range(len(cases)) if t['marks'][f'v:{i}'] == 'no')
    _fact(d, t, f'Cổng: soát {len(cases)} người' + (f', {turned} người không cho xuống nước hôm nay.' if turned else '.'),
          key=worst >= 3, lie='Cổng: soát đúng hết.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, 'Soát người ở cổng xuống hồ.')
    return dict(message=f'🎫 {" ".join(lines)} {msg}'.strip(), celebrate=not cq.slips(t), correct=not cq.safety(t))


# ---------------------------------------------------------------- swimming lessons
def _kids(t: dict) -> tuple:
    return LESSONS[t['_v']['case']]['kids']


def _sheet(s, c, d, p):
    t = _task(c, p, ('lesson',))
    kit.need('sheet' not in t['seen'], 'Đã xem sổ đón rồi.')
    t['seen'].append('sheet')
    kit.start_work(t)
    parts = []
    for k in _kids(t):
        x = KIDS[k]
        parts.append(f'{x["name"]}: ' + ('mẹ ký sổ rồi đi chợ, có ghi số điện thoại' if x.get('away') else 'phụ huynh ký sổ, ngồi ở khu chờ'))
    return dict(message='📋 Sổ đón: ' + '; '.join(parts) + '.')


def _callparent(s, c, d, p):
    t = _task(c, p, ('lesson',))
    k = kit.one_of(p.get('kid'), _kids(t), 'Bé không có trong lớp.')
    kit.need('sheet' in t['seen'], 'Xem sổ đón trước đã.')
    kit.need(KIDS[k].get('away'), 'Phụ huynh của bé đang ở khu chờ rồi.')
    kit.need(f'call:{k}' not in t['seen'], 'Đã gọi rồi.')
    t['seen'].append(f'call:{k}')
    return dict(message=f'📞 Bạn gọi số trong sổ đón. Mười phút sau mẹ {KIDS[k]["name"].split()[-1]} quay lại, xách giỏ chợ ngồi sát mép khu cạn.')


def _test(s, c, d, p):
    t = _task(c, p, ('lesson',))
    k = kit.one_of(p.get('kid'), _kids(t), 'Bé không có trong lớp.')
    kit.need(f'test:{k}' not in t['seen'], 'Bé đã bơi thử rồi.')
    t['seen'].append(f'test:{k}')
    kit.start_work(t)
    return dict(message=f'🏊 Bơi thử ở làn sát thành, bạn đứng ngay mép: {KIDS[k]["test"]}')


def _band(s, c, d, p):
    t = _task(c, p, ('lesson',))
    k = kit.one_of(p.get('kid'), _kids(t), 'Bé không có trong lớp.')
    b = kit.one_of(p.get('band'), BANDS, 'Chọn màu vòng tay.')
    t['marks'][f'b:{k}'] = b
    kit.start_work(t)
    return dict(message=f'{BANDS[b][0]} {KIDS[k]["name"]}: vòng {_lower(BANDS[b][1])}.')


def _teach(s, c, d, p):
    t = _task(c, p, ('lesson',))
    k = kit.one_of(p.get('topic'), TOPICS, 'Nội dung này không có trong giáo án.')
    kit.need(f'topic:{k}' not in t['seen'], 'Đã dạy phần này rồi.')
    t['seen'].append(f'topic:{k}')
    kit.start_work(t)
    return dict(message=f'{TOPICS[k][0]} {TOPIC_LINE[k]}')


def _count(s, c, d, p):
    t = _task(c, p, ('lesson', 'storm'))
    kit.need('count' not in t['seen'], 'Đã đếm rồi.')
    if t['kind'] == 'storm':
        kit.need('shelter' in t['marks'], 'Cho mọi người lên bờ trước rồi mới đếm.')
        t['seen'].append('count')
        st = STORMS[t['_v']['case']]['straggler']
        return dict(message=f'🔢 Đếm lại: thiếu một người! {st} Bạn thổi còi gọi lên ngay.' if st else
                    '🔢 Đếm đủ người: dưới nước không còn ai, phòng thay đồ cũng trống.')
    t['seen'].append('count')
    return dict(message=f'🔢 Điểm danh lúc lên bờ: đủ {len(_kids(t))} bé, khăn quấn kín người.')


def _lesson(s, c, d, p):
    t = _task(c, p, ('lesson',))
    kids = _kids(t)
    kit.need(all(f'b:{k}' in t['marks'] for k in kids), 'Phát vòng tay cho cả ba bé đã.')
    over = [k for k in kids if BAND_ORDER.index(t['marks'][f'b:{k}']) > BAND_ORDER.index(KIDS[k]['band'])]
    if over:
        g = _guard(d, 'over_band', f'{KIDS[over[0]]["name"]} bơi thử ra sao? Vòng tay theo bài bơi thử, không theo lời bé nói.')
        if g:
            return g
    if any(f'test:{k}' not in t['seen'] for k in kids):
        g = _guard(d, 'test', 'Còn bé chưa bơi thử. Bơi thử rồi mới phát vòng.')
        if g:
            return g
    if 'count' not in t['seen']:
        g = _guard(d, 'count', 'Lên bờ là điểm danh, đếm đủ đầu đã.')
        if g:
            return g
    away = [k for k in kids if KIDS[k].get('away') and f'call:{k}' not in t['seen']]
    if away and 'sheet' in t['seen']:
        g = _guard(d, 'noparent', f'Mẹ {KIDS[away[0]]["name"].split()[-1]} đi chợ rồi. Gọi số trong sổ đón mời quay lại nhé.')
        if g:
            return g
    for k in over:
        x = KIDS[k]
        got = t['marks'][f'b:{k}']
        t['mistakes'] += 1
        if x['band'] == 'do' and got == 'xanh':
            cq.slip(t, 'over_band', 3, f'{x["name"]} chưa bơi được mà đeo vòng xanh ra khu sâu.', 'phát vòng cao hơn khả năng', safety=True)
        else:
            cq.slip(t, 'over_band2', 2, f'{x["name"]} được phát vòng cao hơn bài bơi thử.', 'phát vòng cao hơn khả năng')
    under = [k for k in kids if BAND_ORDER.index(t['marks'][f'b:{k}']) < BAND_ORDER.index(KIDS[k]['band'])]
    if under:
        t['mistakes'] += 1
        cq.slip(t, 'under_band', 1, f'{KIDS[under[0]]["name"]} bơi được mà bị xếp vòng thấp, buồn thiu.', 'phát vòng thấp hơn khả năng')
    if any(f'test:{k}' not in t['seen'] for k in kids):
        t['mistakes'] += 1
        cq.slip(t, 'untested', 1, 'Phát vòng tay mà không cho bơi thử.', 'chưa bơi thử')
    miss = [k for k in LESSONS[t['_v']['case']]['topics'] if f'topic:{k}' not in t['seen']]
    if miss:
        t['mistakes'] += 1
        cq.slip(t, 'topics', 1, f'Hôm nay chưa học phần {_lower(TOPICS[miss[0]][1])}.', 'dạy thiếu giáo án')
    if 'count' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'nocount', 2, 'Tan lớp mà không điểm danh, không ai chắc đủ bé đã lên bờ.', 'không điểm danh')
    if away:
        t['mistakes'] += 1
        cq.slip(t, 'noparent', 1, 'Bé học bơi mà phụ huynh không có ở hồ.', 'phụ huynh không có mặt')
    t['choice'] = 'lesson'
    t['result'] = 'lesson'
    _stat(d, 'kids', len(kids))
    bands = ', '.join(f'{KIDS[k]["name"]} {BANDS[t["marks"][f"b:{k}"]][0]}' for k in kids)
    _fact(d, t, f'Lớp bơi: {bands}.', key=cq.safety(t), lie='Lớp bơi: bơi thử đủ, vòng tay đúng, điểm danh đủ.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, 'Dạy lớp bơi trẻ em.')
    return dict(message=f'🏫 Tan lớp: {bands}. {msg}'.strip(), celebrate=not cq.slips(t), correct=not cq.safety(t))


# ---------------------------------------------------------------- first aid
def _gloves(s, c, d, p):
    t = _task(c, p, ('aid',))
    kit.need(not t['washed'], 'Đã đeo găng rồi.')
    t['washed'] = True
    kit.start_work(t)
    return dict(message='🧤 Đeo găng tay sạch từ hộp sơ cứu.')


def _aidask(s, c, d, p):
    t = _task(c, p, ('aid',))
    kit.need('ask' not in t['seen'], 'Đã hỏi rồi.')
    t['seen'].append('ask')
    kit.start_work(t)
    x = AID[t['_v']['case']]
    return dict(message=f'👂 {x["who"]}: {x["ask"]}')


def _aid(s, c, d, p):
    t = _task(c, p, ('aid',))
    x = AID[t['_v']['case']]
    opts = {o[0]: o for o in x['options']}
    choice = kit.one_of(p.get('choice'), opts, 'Chọn cách sơ cứu.')
    _, label, grade, outcome, touch = opts[choice]
    if grade == 'unsafe':
        g = _guard(d, f'unsafe:{t["_v"]["case"]}', 'Khoan đã, làm vậy có thể làm người ta nguy hơn. Nghĩ lại nhé.')
        if g:
            return g
    if touch and not t['washed']:
        g = _guard(d, 'gloves', 'Đeo găng trước khi chạm vào vết thương, máu nhé.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'gloves', 1, 'Sơ cứu chạm máu, vết thương mà không đeo găng.', 'chưa đeo găng')
    kit.start_work(t)
    if grade == 'ok':
        t['mistakes'] += 1
        cq.slip(t, 'meh', 1, 'Được việc nhưng chưa chu đáo.', 'sơ cứu chưa trọn')
    elif grade == 'bad':
        t['mistakes'] += 1
        cq.slip(t, 'bad', 2, outcome, 'sơ cứu chưa đúng')
    elif grade == 'unsafe':
        t['mistakes'] += 1
        cq.slip(t, 'unsafe', 3, outcome, 'sơ cứu làm người ta gặp nguy', safety=True)
    t['choice'] = choice
    t['result'] = grade
    _stat(d, 'aid')
    _fact(d, t, f'Sơ cứu {x["who"]}: {_lower(label.split(" ", 1)[1])}.', key=grade == 'unsafe' or choice in ('call', 'still'),
          lie=f'Sơ cứu {x["who"]}: xử trí đúng, ghi sổ đủ.' if grade in ('bad', 'unsafe') else None)
    msg = _finish(s, c, d, t, BONUS, f'Sơ cứu {x["who"]}.')
    return dict(message=f'{outcome} {msg}'.strip(), celebrate=grade == 'good', correct=grade != 'unsafe')


# ---------------------------------------------------------------- thunderstorms
def _events(t: dict) -> list:
    return STORMS[t['_v']['case']]['events']


def _shown(t: dict) -> list:
    return _events(t)[:t['step'] + 1]


def _thunder_at(t: dict) -> int | None:
    rows = [e for e in _shown(t) if e[2]]
    return _minutes(rows[-1][0]) if rows else None


def _sky(s, c, d, p):
    t = _task(c, p, ('storm',))
    kit.need('sky' not in t['seen'], 'Đã nghe bản tin rồi.')
    t['seen'].append('sky')
    kit.start_work(t)
    return dict(message='📻 Bản tin trên loa phường: chiều nay có dông, có thể kèm lốc và sét. Nghe sấm là vào nơi trú kiên cố.')


def _shelter(s, c, d, p):
    t = _task(c, p, ('storm',))
    kit.need('shelter' not in t['marks'], 'Mọi người đã lên bờ rồi.')
    where = kit.one_of(p.get('where'), SHELTERS, 'Chọn chỗ trú.')
    grade = SHELTER_GRADE[where]
    if grade != 'good':
        g = _guard(d, 'shelter', 'Mái bạt, dù che nắng, gốc cây không che được sét. Vào sảnh có mái bê tông.')
        if g:
            return g
    t['marks']['shelter'] = where
    t['marks']['cleared'] = str(t['step'])
    kit.start_work(t)
    _stat(d, 'closed')
    if grade == 'unsafe':
        t['mistakes'] += 1
        cq.slip(t, 'tree', 3, 'Trú dông dưới gốc cây giữa sân, sét đánh trúng cây bàng góc sân bên kia.', 'trú dưới gốc cây', safety=True)
        return dict(message='🌳 Cả hồ dồn dưới gốc bàng. Một tia sét đánh xuống cây bên kia sân, cả đám hét toáng, chạy vào sảnh.', correct=False)
    if grade == 'bad':
        t['mistakes'] += 1
        cq.slip(t, 'shelter', 2, 'Trú dông dưới mái bạt sát mép hồ, gió thổi bạt tung.', 'chỗ trú không an toàn')
        return dict(message='⛱️ Mọi người chen dưới mái bạt. Gió giật làm một cây dù bay ngang mặt hồ.', correct=False)
    return dict(message='📣 Ba hồi còi: mời tất cả lên bờ, vào sảnh nhà thay đồ. Anh Hải đứng cửa sảnh, chị Phượng phát khăn.')


def _wait(s, c, d, p):
    t = _task(c, p, ('storm',))
    ev = _events(t)
    kit.need(t['step'] < len(ev) - 1, 'Trời đã quang. Quyết mở lại hồ thôi.')
    thunder = _thunder_at(t) is not None
    if thunder and 'shelter' not in t['marks']:
        g = _guard(d, 'thunder', 'Có sấm rồi! Cho tất cả lên bờ, vào sảnh ngay, đừng chờ mưa.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'late_clear', 3, 'Sấm rền mà khách vẫn ở dưới nước.', 'chưa cho lên bờ khi có sấm', safety=True)
    elif thunder and STORMS[t['_v']['case']]['straggler'] and 'count' not in t['seen']:
        g = _guard(d, 'count', 'Lên bờ hết chưa? Đếm lại người, nhìn cả phòng thay đồ.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'straggler', 3, 'Có người còn ở dưới nước lúc sấm sét mà không ai biết.', 'không đếm người', safety=True)
    t['step'] += 1
    kit.start_work(t)
    tm, kind, th, text = ev[t['step']]
    tail = ' (Có người hỏi: trả lời hay không là tùy bạn.)' if kind == 'push' else ''
    return dict(message=f'⏱️ {tm} · {text}{tail}')


def _reply(s, c, d, p):
    t = _task(c, p, ('storm',))
    tm, kind, _, text = _events(t)[t['step']]
    kit.need(kind == 'push', 'Không ai đang hỏi gì.')
    kit.need(f'reply:{t["step"]}' not in t['seen'], 'Đã trả lời rồi.')
    say = kit.one_of(p.get('say'), REPLIES, 'Chọn câu trả lời.')
    if say == 'cave':
        return _reopen(s, c, d, dict(p, cave=True))
    t['seen'].append(f'reply:{t["step"]}')
    who = text.split(':', 1)[0]
    tr = _tr(t, f':{t["step"]}')
    if say == 'rule':
        line = f'{who} hừ một tiếng: “Nội quy thì nội quy.” rồi ngồi xuống chờ.' if tr['rude'] >= 50 else f'{who} gật gù: “Ừ, chờ thêm chút.”'
    else:
        line = f'{who}: “Có vé bù thì được, chị in liền.” Khách cầm vé, bớt càu nhàu hẳn.'
    return dict(message=f'{REPLIES[say][0]} {line}')


def _reopen(s, c, d, p):
    t = _task(c, p, ('storm',))
    cave = bool(p.get('cave'))
    now = _minutes(_events(t)[t['step']][0])
    last = _thunder_at(t)
    kit.need('shelter' in t['marks'] or last is not None, 'Dông chưa tới: chờ, xem trời đã.')
    case = STORMS[t['_v']['case']]
    early = 'shelter' in t['marks'] and last is not None and now - last < LC.WAIT_AFTER
    if early:
        g = _guard(d, 'early', f'Tiếng sấm cuối lúc {[e for e in _shown(t) if e[2]][-1][0]}. Chờ đủ ba mươi phút đã, nắng lên cũng vậy.')
        if g:
            return g
    if last is not None and 'shelter' not in t['marks']:
        g = _guard(d, 'thunder', 'Có sấm rồi mà! Cho lên bờ trước đã.')
        if g:
            return g
    if last is not None and 'shelter' not in t['marks']:
        t['mistakes'] += 1
        cq.slip(t, 'late_clear', 3, 'Sấm rền mà khách vẫn ở dưới nước.', 'chưa cho lên bờ khi có sấm', safety=True)
    if early:
        t['mistakes'] += 1
        cq.slip(t, 'early', 3, 'Mới tạnh đã cho xuống nước, mười phút sau lại có sấm.', 'mở lại khi chưa đủ ba mươi phút', safety=True)
    if case['straggler'] and 'shelter' in t['marks'] and 'count' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'nocount', 2, 'Lên bờ mà không đếm người, không ai chắc hồ đã trống.', 'không đếm người')
    note = ''
    if cave:
        t['seen'].append(f'reply:{t["step"]}')
        note = ao.penalize(c, d['odd'], 2 if early else 1, CFG)
    t['choice'] = 'reopen'
    t['result'] = 'cave' if cave else 'reopen'
    unsafe = cq.safety(t)
    fact = (f'Dông: cho lên bờ, trú ở {_lower(SHELTERS[t["marks"]["shelter"]][1])}, mở lại lúc {_events(t)[t["step"]][0]}.'
            if 'shelter' in t['marks'] else f'Dông: không đóng hồ, mở tới {_events(t)[t["step"]][0]}.')
    _fact(d, t, fact, key=True, lie='Dông: đóng hồ đúng lúc, chờ đủ ba mươi phút mới mở.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, 'Đóng hồ vì dông, mở lại an toàn.')
    head = '🔓 Mở lại hồ. ' + ('Trời quang, khách xuống nước, ông Tư đội mũ cam dẫn đầu.' if not unsafe else 'Mười phút sau sấm lại rền, cả hồ phải lên bờ lần nữa.')
    return dict(message=f'{head} {note} {msg}'.replace('  ', ' ').strip(), celebrate=not cq.slips(t), correct=not unsafe)


# ---------------------------------------------------------------- finishing a task
def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str, counted: bool = True) -> str:
    """Pays the bonus (none after a safety mistake; half when tired, none while demoted) and completes once."""
    pts = cq.points(t)
    full = 0 if cq.safety(t) or not reward else max(0, reward - 3 * pts)
    pay = ao.bonus(d['odd'], full)
    t['stage'] = 'done'
    story = ''
    i = _npc_index(t)
    if counted and i in LC.REG_STORY:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        story = LC.REG_STORY[i][min(r['visits'], len(LC.REG_STORY[i])) - 1]
        t['story'] = story
    if counted:
        d['learn']['n'] = min(10 ** 6, d['learn']['n'] + 1)
        _stat(d, 'tasks')
        if cq.safety(t):
            _stat(d, 'safety')
    kit.complete(s, c, t, pay, (narrative or t['title'])[:300])
    note = ao.flown(d['odd'], not cq.slips(t), CFG) if counted else ''
    parts = []
    if pay:
        parts.append(f'Thưởng {pay} xu.')
    elif full and not pay:
        parts.append('(Đang bị hạ bậc: chưa có thưởng.)')
    if full and pay and pay < full:
        parts.append('(Mệt quá: nửa thưởng.)')
    if note:
        parts.append(note)
    if story:
        parts.append(f'💬 {story}')
    return ' '.join(parts)


def _fact(d: dict, t: dict, text: str, key: bool, lie: str | None = None) -> None:
    """A line the end-of-shift log may carry (true), and a tempting one that did not happen (lie)."""
    rows = d['today']['facts']
    rows.append(dict(id=f'f-{t["id"]}', text=text[:160], key=bool(key), true=True))
    if lie:
        rows.append(dict(id=f'l-{t["id"]}', text=lie[:160], key=False, true=False))
    d['today']['facts'] = rows[-FACTS_MAX:]


# ---------------------------------------------------------------- the end-of-shift log
def _report(s, c, d, p):
    today = d['today']
    kit.need(today['report'] is None, 'Hôm nay đã ghi sổ trực rồi.')
    rows = today['facts']
    kit.need(rows, 'Chưa có gì để ghi sổ. Làm việc trước đã.')
    pick = kit.id_list(p.get('lines') or [], [r['id'] for r in rows], FACTS_MAX, 'Chọn dòng ghi vào sổ.')
    kit.need(pick, 'Chọn ít nhất một dòng ghi vào sổ trực.')
    chosen = [r for r in rows if r['id'] in pick]
    lies = [r for r in chosen if not r['true']]
    miss = [r for r in rows if r['key'] and r['true'] and r['id'] not in pick]
    _stat(d, 'reports')
    if lies:
        today['report'] = 'false'
        note = ao.penalize(c, d['odd'], 2, CFG)
        return dict(message=f'📒 Anh Hải đọc sổ, khựng lại ở dòng “{lies[0]["text"]}”: “Cái này đâu có xảy ra, em?” Ghi khống vào sổ trực. {note}',
                    correct=False)
    if miss:
        today['report'] = 'miss'
        c['xp'] += 2
        return dict(message=f'📒 Sổ trực thật, nhưng thiếu: “{miss[0]["text"]}”. Ca chiều phải hỏi lại từng người.')
    today['report'] = 'ok'
    c['xp'] += 8
    _stat(d, 'honest')
    return dict(message='📒 Sổ trực rõ ràng, thật, đủ chuyện cần biết. Ca sau đọc một lượt là nắm hết.', celebrate=True)


ACTIONS = {
    'hb_check': _check, 'hb_log': _log, 'hb_fix': _fix, 'hb_rep': _rep, 'hb_open': _open,
    'hb_scan': _scan, 'hb_look': _look, 'hb_whistle': _whistle, 'hb_alarm': _alarm, 'hb_backup': _backup, 'hb_method': _method,
    'hb_assess': _assess, 'hb_care': _care, 'hb_round': _round,
    'hb_gq': _gq, 'hb_verdict': _verdict, 'hb_gate': _gate,
    'hb_sheet': _sheet, 'hb_call': _callparent, 'hb_test': _test, 'hb_band': _band, 'hb_teach': _teach, 'hb_count': _count, 'hb_lesson': _lesson,
    'hb_gloves': _gloves, 'hb_aidask': _aidask, 'hb_aid': _aid,
    'hb_sky': _sky, 'hb_shelter': _shelter, 'hb_wait': _wait, 'hb_reply': _reply, 'hb_reopen': _reopen,
    'hb_report': _report,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['today'] = _fresh_today(day)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'open' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    if not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        sh = make_task(day, 0, c['turn'])
        c['tasks'].append(sh)
        on_task(s, c, sh)
    sh = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'open' and t['day'] == day
               and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if sh:
        c['active_task'] = sh['id']
        sh['deferred'] = False
    ao.start(c, ID, d['odd'])
    kit.desk_start(s, c, ID, d['desk'], LC.DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')
    ao.tick(s, c, ID, d['odd'], LC.ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], LC.DESK)
    odd_note = ao.close(s, c, d['odd'], LC.ODD)
    x = d['today']
    lines = [f'🛟 Ca trực: {x["tasks"]} việc ở Hồ bơi Sóng Xanh.']
    if x['whistles']:
        lines.append(f'📣 Thổi còi đúng luật {x["whistles"]} lần.')
    if x['rescues']:
        lines.append(f'🛟 Đưa {x["rescues"]} người gặp nạn lên bờ. Ngực còn đập thình thịch.')
    if x['closed']:
        lines.append(f'⛔ Đóng hoặc hoãn mở hồ {x["closed"]} lần vì an toàn: đúng bài.')
    if x['gate']:
        lines.append(f'🎫 Soát {x["gate"]} người ở cổng.')
    if x['safety']:
        lines.append(f'📋 {x["safety"]} biên bản sự cố. Mai họp nhóm rút kinh nghiệm.')
    if x['report'] is None and x['facts']:
        lines.append('📒 Chưa ghi sổ trực: ca sau phải hỏi lại từng chuyện.')
    elif x['report'] == 'ok':
        lines.append('📒 Sổ trực rõ ràng, thật, đủ.')
    if desk_note:
        lines.append(desk_note)
    if odd_note:
        lines.append(odd_note)
    lines += ao.day_lines(c, d['odd'], CFG)
    lines.append('🏠 Tối về tới đầu hẻm, tóc còn mùi clo, bà Tám để phần cơm trên bàn.')
    return dict(lines=lines, note='Mai mở hồ lúc 6:00: thử nước, kiểm phao trước khi mở cổng.', tasks=x['tasks'], whistles=x['whistles'],
                rescues=x['rescues'], closed=x['closed'], safety=x['safety'])


# ================================================================ reviews
def _score(codes: set, bad: set, worse: set = frozenset(), worst: set = frozenset()) -> int:
    if codes & worst:
        return 1
    if codes & worse:
        return 2
    if codes & bad:
        return 3
    return 5


def feedback(c: dict, t: dict) -> dict:
    codes = {x['code'] for x in cq.slips(t)}
    k = t.get('kind')
    if k == 'open':
        stops = {f for f in LC.STOP_FAULTS}
        fixes = {f for f in LC.FIX_FAULTS}
        return dict(criteria=[dict(key='checks', label='Kiểm đủ từng món', score=_score(codes, {'skip', 'nolog'}, {'log'}),
                                   note='thử đủ, ghi sổ đúng' if not codes & {'skip', 'nolog', 'log'} else 'kiểm chưa đủ'),
                              dict(key='safe', label='Chỉ mở khi an toàn', score=_score(codes, {'needless'}, set(), stops),
                                   note='mở đúng lúc' if not codes & (stops | {'needless'}) else 'mở khi chưa an toàn'),
                              dict(key='gear', label='Đồ cứu hộ sẵn sàng', score=_score(codes, set(), fixes - {'tube_torn'}, {'tube_torn'}),
                                   note='phao, sào, hộp sơ cứu đủ' if not codes & fixes else 'đồ cứu hộ chưa sẵn'),
                              dict(key='report', label='Báo đúng người', score=_score(codes, {'unreported', 'channel'}),
                                   note='báo đúng kênh' if not codes & {'unreported', 'channel'} else 'báo chưa đúng')])
    if k == 'watch':
        return dict(criteria=[dict(key='scan', label='Quét đủ, kịp', score=_score(codes, {'slow'}, {'unlooked'}),
                                   note='đủ năm khu trong một phút' if not codes & {'slow', 'unlooked'} else 'quét chậm hoặc sót'),
                              dict(key='rules', label='Thổi còi đúng luật', score=_score(codes, {'nag', 'wrong_rule'}, {'missed_rule'}),
                                   note='nhắc đúng chuyện' if not codes & {'nag', 'wrong_rule', 'missed_rule'} else 'nhắc chưa đúng'),
                              dict(key='spot', label='Nhận ra người đuối nước', score=_score(codes, {'false_alarm'}, {'misread', 'late'}, {'missed'}),
                                   note='thấy kịp' if not codes & {'false_alarm', 'misread', 'late', 'missed'} else 'nhận ra chậm hoặc nhầm'),
                              dict(key='rescue', label='Cứu và sơ cứu đúng', score=_score(codes, {'roundabout', 'blind'}, {'bare', 'alone', 'care_bad'}, {'delay', 'care'}),
                                   note='với, ném trước; có phao; sơ cứu đúng' if not codes & {'roundabout', 'blind', 'bare', 'alone', 'care_bad', 'delay', 'care'} else 'cứu chưa đúng cách')])
    if k == 'gate':
        return dict(criteria=[dict(key='safe', label='Ai xuống nước được', score=_score(codes, {'over'}, {'let_in'}, {'let_in_unsafe'}),
                                   note='quyết đúng từng người' if not codes & {'over', 'let_in', 'let_in_unsafe'} else 'quyết chưa đúng'),
                              dict(key='look', label='Nhìn, hỏi trước', score=_score(codes, {'blind'}), note='nhìn và hỏi' if 'blind' not in codes else 'quyết khi chưa hỏi')])
    if k == 'lesson':
        return dict(criteria=[dict(key='bands', label='Vòng tay theo bài bơi thử', score=_score(codes, {'under_band', 'untested'}, {'over_band2'}, {'over_band'}),
                                   note='bơi thử rồi mới phát' if not codes & {'under_band', 'untested', 'over_band2', 'over_band'} else 'vòng chưa đúng'),
                              dict(key='class', label='Giáo án, điểm danh', score=_score(codes, {'topics', 'noparent'}, {'nocount'}),
                                   note='dạy đủ, đếm đủ' if not codes & {'topics', 'noparent', 'nocount'} else 'thiếu bước')])
    if k == 'aid':
        return dict(criteria=[dict(key='gloves', label='Găng tay', score=_score(codes, {'gloves'}), note='đeo găng trước' if 'gloves' not in codes else 'chưa đeo găng'),
                              dict(key='care', label='Sơ cứu đúng', score=_score(codes, {'meh'}, {'bad'}, {'unsafe'}),
                                   note='an toàn, đúng cách' if not codes & {'meh', 'bad', 'unsafe'} else 'chưa đúng cách')])
    return dict(criteria=[dict(key='clear', label='Lên bờ khi có sấm', score=_score(codes, set(), {'shelter', 'nocount'}, {'late_clear', 'tree', 'straggler'}),
                               note='lên bờ ngay, trú đúng chỗ' if not codes & {'shelter', 'nocount', 'late_clear', 'tree', 'straggler'} else 'chưa an toàn'),
                          dict(key='wait', label='Chờ đủ ba mươi phút', score=_score(codes, set(), set(), {'early'}),
                               note='chờ đủ rồi mới mở' if 'early' not in codes else 'mở lại sớm')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    k = t['kind']
    n = t['needs']
    if k == 'open':
        return 'Danh sách mở hồ: ' + ', '.join(_lower(CHECKS[x][1]) for x in n['checks']) + '.'
    if k == 'watch':
        return 'Quét đủ năm khu: ' + ', '.join(_lower(ZONES[z][1]) for z in ZONE_IDS) + '.'
    if k == 'gate':
        return 'Ở cổng: ' + ', '.join(x['who'] for x in n['queue']) + '.'
    if k == 'lesson':
        return 'Lớp bơi: ' + ', '.join(x['name'] for x in n['kids']) + '. Giáo án: ' + ', '.join(_lower(TOPICS[x][1]) for x in n['topics']) + '.'
    if k == 'aid':
        return AID[t['_v']['case']]['detail']
    return f'Dông chiều, bắt đầu từ {n["start"]}.'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not t['known'] and t['kind'] != 'open':
        v['needs'] = None
        return v
    k = t['kind']
    seen = set(t.get('seen') or [])
    m = t.get('marks') or {}
    if k == 'open':
        faults = _faults(t)
        rows = []
        for cid in CHECK_IDS:
            e, label, ok = CHECKS[cid]
            row = dict(id=cid, emoji=e, label=label, state=None, text=None, fix=None, fixed=False, rep=None)
            if cid in seen:
                f = faults.get(cid)
                st = _strip(t)
                line = f'Clo {st["cl"]} · pH {st["ph"]}.' if cid == 'strip' else ''
                row.update(state='fault' if f else 'ok', text=' '.join(x for x in (line, FAULTS[f]['text'] if f else ok) if x),
                           fix=FAULTS[f]['fix'] if f else None, fixed=f'fix:{cid}' in seen, rep=m.get(f'rep:{cid}'))
            rows.append(row)
        view = dict(checks=rows, card=LC.CARD_TEXT)
        if 'strip' in seen:
            view['strip'] = dict(_strip(t))
        if 'cl' in m:
            view['log'] = dict(cl=m['cl'], ph=m['ph'])
        v['needs'] = view
        return v
    if k == 'watch':
        zones = []
        for z in ZONE_IDS:
            e, name = ZONES[z]
            looked = f'z:{z}' in seen
            zones.append(dict(id=z, emoji=e, name=name, text=_zone(t, z)[1] if looked else None, whistle=m.get(f'w:{z}')))
        view = dict(zones=zones, sweep=t.get('sweep'), limit=SWEEP_S, alarm=m.get('alarm'), false=m.get('false'))
        if 'alarm' in m:
            st = _rescue(t).get('state', 'awake')
            view['rescue'] = dict(help=m.get('help'), method=m.get('method'), fails=[x.split(':', 1)[1] for x in seen if x.startswith('fail:')],
                                  assess=ASSESS[st] if 'assess' in seen else None, care=m.get('care'))
        v['needs'] = view
        return v
    if k == 'gate':
        cases = t['_v']['cases']
        v['needs'] = dict(queue=[dict(q, ask=GATE[cases[i]]['ask'] if f'ask:{i}' in seen else None,
                                      look=GATE[cases[i]]['look'] if f'look:{i}' in seen else None,
                                      verdict=m.get(f'v:{i}'), best=GATE[cases[i]]['best'] if t['stage'] == 'done' else None)
                                 for i, q in enumerate(t['needs']['queue'])])
        return v
    if k == 'lesson':
        kids = []
        for x in t['needs']['kids']:
            kid = x['id']
            kids.append(dict(x, test=KIDS[kid]['test'] if f'test:{kid}' in seen else None, band=m.get(f'b:{kid}'),
                             away=bool(KIDS[kid].get('away')) if 'sheet' in seen else None, called=f'call:{kid}' in seen))
        v['needs'] = dict(kids=kids, topics=t['needs']['topics'], taught=[x.split(':', 1)[1] for x in seen if x.startswith('topic:')],
                          sheet='sheet' in seen, counted='count' in seen)
        return v
    if k == 'aid':
        x = AID[t['_v']['case']]
        v['needs'] = dict(who=x['who'], detail=x['detail'], ask=x['ask'] if 'ask' in seen else None,
                          options=[dict(id=o[0], label=o[1]) for o in x['options']])
        return v
    ev = _shown(t)
    last = [e for e in ev if e[2]]
    v['needs'] = dict(events=[dict(at=e[0], kind=e[1], thunder=e[2], text=e[3]) for e in ev], now=ev[-1][0],
                      last_thunder=last[-1][0] if last else None, more=t['step'] < len(_events(t)) - 1,
                      shelter=m.get('shelter'), counted='count' in seen, sky='sky' in seen,
                      push=ev[-1][1] == 'push' and f'reply:{t["step"]}' not in seen)
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    lr = d['learn']
    today = d['today']
    # Shuffled by a hash of the line id: the order never tells which lines really happened.
    facts = [dict(id=r['id'], text=r['text']) for r in sorted(today.get('facts') or [], key=lambda r: folk.roll('fact', r['id']))]
    return dict(intro=d['intro'], mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=dict(day=today.get('day', 0), tasks=today.get('tasks', 0), whistles=today.get('whistles', 0), rescues=today.get('rescues', 0),
                           closed=today.get('closed', 0), safety=today.get('safety', 0), gate=today.get('gate', 0), report=today.get('report'), facts=facts),
                stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                learn=dict(on=lr.get('n', 0) < LEARN, n=lr.get('n', 0), of=LEARN),
                desk=kit.desk_public(d['desk'], LC.DESK, ID), odd=ao.public(c, ao.ensure(d), LC.ODD, ID, CFG))


def content() -> dict:
    return dict(intro=LC.INTRO, zones={k: list(v) for k, v in ZONES.items()}, zone_ids=list(ZONE_IDS),
                checks={k: [v[0], v[1]] for k, v in CHECKS.items()}, check_ids=list(CHECK_IDS), card=LC.CARD_TEXT,
                channels={k: list(v) for k, v in CHANNELS.items()}, rules={k: list(v) for k, v in RULES.items()},
                methods={k: list(v) for k, v in METHODS.items()}, care={k: list(v) for k, v in CARE.items()},
                verdicts={k: list(v) for k, v in VERDICTS.items()}, bands={k: list(v) for k, v in BANDS.items()}, band_order=list(BAND_ORDER),
                topics={k: list(v) for k, v in TOPICS.items()}, shelters={k: list(v) for k, v in SHELTERS.items()},
                replies={k: list(v) for k, v in REPLIES.items()}, sweep_s=SWEEP_S, alarm_s=ALARM_S, wait_after=LC.WAIT_AFTER, learn=LEARN,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    return {'open': 'Kiểm từng món → ghi số que thử vào sổ nước → món hỏng thì tự sửa hoặc báo đúng người → chưa an toàn thì hoãn mở.',
            'watch': 'Bắt đầu vòng quét → nhìn đủ năm khu trong một phút → nhắc đúng luật → ai đang chìm thì báo động, gọi hỗ trợ, với hoặc ném trước, '
                     'xuống nước thì mang phao ống → xem thở không → sơ cứu → kết thúc vòng.',
            'gate': 'Nhìn và hỏi từng người → chọn: mời vào, vào sau khi sửa, chỉ khu cạn có người lớn, hay hôm nay không xuống nước.',
            'lesson': 'Xem sổ đón → bơi thử từng bé → phát vòng tay theo bài bơi thử → dạy hai phần của giáo án → điểm danh lúc lên bờ.',
            'aid': 'Hỏi chuyện gì xảy ra → đeo găng trước khi chạm → chọn cách sơ cứu an toàn; không đưa thuốc của mình.',
            'storm': 'Nghe sấm là cho tất cả lên bờ, vào sảnh có mái kiên cố → đếm người → chờ → chỉ mở lại khi đã ba mươi phút không nghe sấm.'}.get(t.get('kind'), '')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'guard':
        return 'Đã ngồi thay ghế trực nửa tiếng cho bạn uống nước, đổi ca.'
    if e.get('role') == 'desk':
        return 'Đã soát vé, phát mũ bơi, nhắc khách tắm tráng ở cổng.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu hồ bơi sai.')


def _seen_ok(t: dict) -> set:
    k = t.get('kind')
    v = t.get('_v') or {}
    if k == 'open':
        return set(CHECK_IDS) | {f'fix:{x}' for x in CHECK_IDS}
    if k == 'watch':
        return {f'z:{z}' for z in ZONE_IDS} | {'assess'} | {f'fail:{m}' for m in METHODS}
    if k == 'gate':
        n = len(v.get('cases') or [])
        return {f'{w}:{i}' for w in ('ask', 'look') for i in range(n)}
    if k == 'lesson':
        kids = LESSONS.get(v.get('case'), {}).get('kids', ())
        return {'sheet', 'count'} | {f'{w}:{x}' for w in ('test', 'call') for x in kids} | {f'topic:{x}' for x in TOPICS}
    if k == 'aid':
        return {'ask'}
    if k == 'storm':
        n = len(STORMS.get(v.get('case'), {}).get('events') or [])
        return {'sky', 'count'} | {f'reply:{i}' for i in range(n)}
    return set()


def _marks_ok(t: dict, m: dict) -> bool:
    k = t.get('kind')
    v = t.get('_v') or {}
    for key, val in m.items():
        if not isinstance(key, str) or not isinstance(val, str) or len(val) > 12:
            return False
        if k == 'open':
            if key in ('cl', 'ph'):
                continue
            if not (key.startswith('rep:') and key[4:] in CHECK_IDS and val in CHANNELS):
                return False
        elif k == 'watch':
            if key.startswith('w:'):
                if key[2:] not in ZONE_IDS or val not in RULES:
                    return False
            elif key in ('alarm', 'false'):
                if val not in ZONE_IDS:
                    return False
            elif key == 'help':
                if val not in ('team', 'alone'):
                    return False
            elif key == 'method':
                if val not in METHODS:
                    return False
            elif key == 'care':
                if val not in CARE:
                    return False
            else:
                return False
        elif k == 'gate':
            n = len(v.get('cases') or [])
            if not (key.startswith('v:') and key[2:] in {str(i) for i in range(n)} and val in VERDICTS):
                return False
        elif k == 'lesson':
            kids = LESSONS.get(v.get('case'), {}).get('kids', ())
            if not (key.startswith('b:') and key[2:] in kids and val in BANDS):
                return False
        elif k == 'storm':
            if key == 'shelter':
                if val not in SHELTERS:
                    return False
            elif key == 'cleared':
                if not val.isdigit():
                    return False
            else:
                return False
        else:
            return False
    return True


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN and t.get('kind') in KINDS and t.get('stage') in STAGES, 'Việc ở hồ bơi sai.')
    _vbool(t.get('washed'))
    seen = t.get('seen')
    kit.need(isinstance(seen, list) and len(seen) == len(set(seen)) and all(isinstance(x, str) for x in seen) and set(seen) <= _seen_ok(t),
             'Việc ở hồ bơi sai.')
    m = t.get('marks')
    kit.need(isinstance(m, dict) and len(m) <= 16 and _marks_ok(t, m), 'Việc ở hồ bơi sai.')
    if t.get('kind') == 'open':
        kit.need(('cl' in m) == ('ph' in m), 'Sổ nước sai.')
    n_ev = len(STORMS.get((t.get('_v') or {}).get('case'), {}).get('events') or [1])
    kit.integer(t.get('step'), 0, max(0, n_ev - 1))
    sw = t.get('sweep')
    kit.need(sw is None or (isinstance(sw, (int, float)) and not isinstance(sw, bool) and 0 <= sw < 10 ** 11), 'Vòng quét sai.')
    kit.need(t.get('choice') is None or (isinstance(t['choice'], str) and len(t['choice']) <= 24), 'Lựa chọn sai.')
    kit.need(t.get('result') is None or (isinstance(t['result'], str) and len(t['result']) <= 24), 'Kết quả sai.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in LC.REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    kit.need(isinstance(d['stats'], dict) and len(d['stats']) <= 20, 'Số liệu hồ bơi sai.')
    for v in d['stats'].values():
        kit.integer(v, 0, 10 ** 9)
    x = d['today']
    kit.need(isinstance(x, dict) and set(x) == set(_fresh_today(0)), 'Số liệu trong ngày sai.')
    for k in ('day', 'tasks', 'whistles', 'rescues', 'closed', 'safety', 'gate'):
        kit.integer(x[k], 0, 10 ** 9)
    kit.need(x['report'] in (None, 'ok', 'miss', 'false'), 'Sổ trực sai.')
    kit.need(isinstance(x['facts'], list) and len(x['facts']) <= FACTS_MAX, 'Sổ trực sai.')
    for r in x['facts']:
        kit.need(isinstance(r, dict) and set(r) == {'id', 'text', 'key', 'true'} and type(r['key']) is bool and type(r['true']) is bool, 'Sổ trực sai.')
        kit.text(r['id'], 60)
        kit.text(r['text'], 160)
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'n', 'caught'} and isinstance(lr['caught'], list) and len(lr['caught']) <= 24, 'Sổ kèm việc sai.')
    kit.integer(lr['n'], 0, 10 ** 6)
    for k in lr['caught']:
        kit.text(k, 40)
    kit.desk_validate(d['desk'], LC.DESK)
    ao.validate(d['odd'], LC.ODD)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='hb_', category='service',
    meta=dict(short='Cứu hộ hồ bơi', place='Hồ bơi Sóng Xanh', tagline='Mắt không rời mặt nước. Với, ném trước khi xuống.', icon='shield',
              color='#1f8fc4', light='#e2f3fb', weather='Nắng đẹp, mặt hồ lấp lánh', work='Việc trong ca', station='Ghế trực cao',
              greeting='Mở hồ lúc 6:00. Thử nước, kiểm phao, quét đủ năm khu; nghe sấm là cho tất cả lên bờ.',
              caption='Người đuối nước không vẫy tay, không kêu cứu', map_label='29 · HỒ BƠI SÓNG XANH'),
    people=PEOPLE,
    staff=[('Lộc', 'guard', 'Cứu hộ thời vụ, sinh viên đội bơi trường, mắt tinh như cú.', 84, 90),
           ('Hà', 'desk', 'Lễ tân lâu năm, nhớ mặt khách vé tháng, soát mũ bơi không sót ai.', 78, 94),
           ('Sang', 'guard', 'Bơi sải nhanh nhất nhóm, mới học xong lớp sơ cứu.', 90, 80),
           ('Thư', 'desk', 'Nói chuyện khéo, khách khó tính cỡ nào cũng chịu đội mũ.', 74, 92)],
    roles={'guard': 'Cứu hộ thời vụ', 'desk': 'Lễ tân hồ'},
    tip=0,
    open_line='Mở hồ lúc 6:00. Anh Hải đang chờ ở ghế trực.',
    more_line='Anh Hải giao thêm một việc trong ca.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('🛟', 'Một ca trên ghế cao', [('Người đuối nước', 'Im lặng, dựng đứng'), ('Với, ném', 'Trước khi xuống nước'),
                                          ('Có sấm', 'Tất cả lên bờ'), ('Dốc ngược', 'Không bao giờ')],
              ['Thử nước, kiểm phao', 'Quét đủ năm khu', 'Với, ném, phao ống', 'Sơ cứu, ghi sổ']),
    stories=[('Cái còi của anh Hải', ('Cái còi đồng của anh Hải đã mòn vẹt chỗ ngậm, mười lăm năm chưa đổi.',
                                     'Bạn trực thêm một ca; anh chỉ cách thổi: một tiếng nhắc, ba tiếng gọi người, một hồi dài là có chuyện.',
                                     'Anh Hải dặn: “Còi để người ta nghe, chứ không phải để người ta sợ.”')),
             ('Mũ bơi màu cam', ('Ông Tư nhất định không đội mũ bơi, mười năm nay vẫn vậy.',
                                 'Bạn trực thêm một ca, mua tặng ông cái mũ màu cam “cho dễ thấy”.',
                                 'Sáng hôm sau ông Tư xuống nước, mũ cam trên đầu, còn khoe với cả làn.')),
             ('Vòng tay xanh của bé Bon', ('Bé Bon đeo vòng đỏ, mỗi lần đi ngang khu sâu lại nhìn thèm thuồng.',
                                           'Bạn dạy thêm một buổi, Bon nổi được mười giây không cần ai đỡ.',
                                           'Cuối hè Bon bơi hết 25 mét, giơ tay nhận vòng xanh, cả lớp vỗ tay.'))],
    review_asides=['Cứu hộ quét hồ không rời mắt, gửi con thấy yên tâm.', 'Còi đúng lúc, nói dễ nghe.', 'Có sấm là cho lên bờ liền, chuyên nghiệp ghê.',
                   'Bơi thử từng bé rồi mới cho ra khu sâu, cẩn thận.'],
    situations=LC.SITUATIONS,
    guide='Mở hồ: thử từng món, ghi sổ nước, sửa hoặc báo đúng người, chưa an toàn thì hoãn → lên ghế quét đủ năm khu → nhắc đúng luật → '
          'người đuối nước thì im lặng: báo động, gọi hỗ trợ, với hoặc ném trước, xuống nước thì mang phao ống → xem thở không, gọi 115, '
          'không dốc ngược → có sấm thì lên bờ, ba mươi phút sau tiếng sấm cuối mới mở lại → cuối ca ghi sổ trực thật.',
    employment=dict(
        postings=[
            dict(id='hb-sx', org='Hồ bơi Sóng Xanh · Trung tâm Văn hóa – Thể thao phường', kind='public', title='Nhân viên cứu hộ hồ bơi',
                 salary=(50, 66), probation_days=3, wants=['careful', 'calm', 'communication'],
                 perks=['Anh Hải kèm ba việc đầu', 'Ca 6:00–20:00 xoay ghế mỗi giờ', 'Bơi miễn phí ngoài giờ trực'],
                 culture='Hồ bơi phường bốn làn, một khu cạn trẻ em. Ở đây ai lên ghế cũng quàng phao ống, mắt không rời mặt nước, kể cả lúc hồ vắng.',
                 questions=['hb_q_silent', 'hb_q_reach', 'hb_q_storm', 'mistake'], reference=True),
            dict(id='hb-he', org='Hồ bơi Sóng Xanh · Lớp bơi hè thiếu nhi', kind='parttime', title='Cứu hộ kiêm dạy bơi hè (bán thời gian)',
                 salary=(40, 52), probation_days=2, wants=['patience', 'communication'],
                 perks=['Ca sáng ngắn', 'Đứng lớp cùng anh Hải', 'Lương thấp hơn'],
                 culture='Mỗi lớp ba bé, khu cạn. Việc chính là bơi thử, phát vòng tay đúng sức từng bé và dạy các bé biết gọi người lớn.',
                 questions=['hb_q_liar', 'hb_q_silent'], reference=False),
        ],
        questions={
            'hb_q_silent': dict(text='Trên ghế cao, bạn thấy một bé đứng thẳng trong nước, đầu ngửa ra sau, miệng ngang mặt nước, không kêu. Bạn nghĩ gì?', options=[
                dict(id='drown', label='Bé đang đuối nước: báo động, xuống cứu ngay', score=3, note='Người đuối nước thật thường im lặng, không vẫy được.'),
                dict(id='play', label='Bé đang chơi trò nín thở, để ý thêm chút', score=0, note='Chờ thêm là mất những giây quý nhất.'),
                dict(id='shout', label='Gọi to hỏi bé có sao không', score=1, note='Người đang chìm không trả lời được.')]),
            'hb_q_reach': dict(text='Một người lớn đang chìm cách thành hồ một sải tay. Bạn làm gì?', options=[
                dict(id='reach', label='Nằm thấp trên bờ, chìa sào hoặc phao ống cho họ bám', score=3, note='Với được từ bờ thì với: an toàn cho cả hai.'),
                dict(id='jump', label='Nhảy xuống tay không ôm họ vào', score=0, note='Người đuối nước ôm ghì là chìm cả hai.'),
                dict(id='wait', label='Gọi người khác tới rồi tính', score=1, note='Gọi hỗ trợ là đúng, nhưng cứu thì không chờ.')]),
            'hb_q_storm': dict(text='Nghe sấm xa, trời chưa mưa, quản lý bảo cứ cho bơi. Bạn làm gì?', options=[
                dict(id='clear', label='Cho tất cả lên bờ, vào nơi trú kiên cố, ba mươi phút sau tiếng sấm cuối mới mở', score=3, note='Sét không chờ mưa.'),
                dict(id='deep', label='Chỉ cho khu sâu lên bờ', score=0, note='Nước nào cũng nguy hiểm khi có sét.'),
                dict(id='wait', label='Chờ mưa xuống rồi đóng', score=0, note='Nghe được sấm là đã ở trong tầm sét.')]),
            'hb_q_liar': dict(text='Một bé tám tuổi khoe “con bơi được 50 mét”, đòi ra khu sâu. Bạn làm gì?', options=[
                dict(id='test', label='Cho bơi thử ở làn sát thành, qua được mới ra khu sâu', score=3, note='Không tin miệng, tin bài bơi thử.'),
                dict(id='trust', label='Bé nói vậy thì cho ra', score=0, note='Trẻ con hay nói quá khả năng.'),
                dict(id='never', label='Trẻ con không bao giờ được ra khu sâu', score=1, note='An toàn nhưng chưa công bằng với bé bơi giỏi.')]),
        }),
)
