"""Thợ dầu khí: an offshore operations technician of Dầu khí Sóng Bạc on giàn Hải Âu (plugin career).

The rotation (đợt đi biển 14 ngày) without breaking the game's day loop: each career day is one phase of the hitch,
walked forward from day 1 (`phase`), so it is a pure function of the day:

    out (bay ra giàn) → rig × 4 (ca 12 tiếng, ~3 hitch days each) → home (bàn giao, về bờ) → out …

A typhoon on the day the crew should fly home turns it into `stay` (ở lại thêm vì bão) and home slides a day; a
typhoon on a fly-out day is `wait` (chờ ở bờ, the hitch starts the day after). The jobs of the day follow the phase:

* ``heli`` (out): pack the soft bag (15 kg, no lighter, aerosol, knife, alcohol, vape), put on the survival suit, the
  helicopter life jacket, the emergency breathing system and ear defenders, answer the HUET check, wait out fog;
* ``induct`` (out): your T-card on the POB board, your muster station from your cabin, the rig's alarm tones;
* ``toolbox`` (rig): the toolbox talk: PPE, bump-test the gas monitor (swap a failed one), name the job's hazards,
  remind everyone of stop-work authority;
* ``ptw`` (rig): maintenance under a permit to work: the right permit, cross-check other permits (SIMOPS), every
  isolation point locked and tagged with your own lock, bleed, prove zero energy, test the air, a fire watch or a
  standby person, then work, restore, hand the permit back. A trap may wait behind a check (a passing valve, gas at
  the flange, low oxygen in the tank, the crane overhead, a mislabelled breaker): the right move is ✋ stop work;
* ``round`` (rig): read the gauges against their limits, report what is out to the control room, look/listen/smell
  each area; a leak is reported and cordoned, never tightened under pressure;
* ``drill`` (rig): name the alarm, make your work safe, never go back for the phone, go upwind and never by the lift,
  to your own station, swipe your card;
* ``secure`` (typhoon, stay): lash, stow or check what is loose on deck, stand the crane down;
* ``handover`` (home): write every open item for the back-to-back, your own near-miss included;
* ``shore`` (home, wait): the family asks for money (the remittance haggle): ask what it is really for, send what
  is needed, say no kindly, never to a scam; call home.

Stop-work authority is never wrong: stopping when nothing is wrong costs a little time and no mark. Around the job:
chuyện oái oăm (game/careers/air_odd.py with oil_content.ODD: supervisors who push to skip a step, a contractor who
fakes a checklist, a snoring bunkmate, galley complaints, calls with no signal, family who wants money, seduction and
harassment PG-13; giving in to a corner cut costs conduct points), desk surprises by phase, situations.
The job is salaried (employment); a job done by the book adds a small bonus, never after a safety slip.
Everything random is rolled from (day, slot) or the task id.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import air_odd as ao
from . import airline as air
from .. import consequences as cq
from . import oil_content as K
from .oil_content import HSE, TOAN, SAU, BAO, MA, GAU, THOA

ID = 'oil'
GEN = 1
PEOPLE = K.PEOPLE
MODS = K.MODS
CYCLE = ('out', 'rig', 'rig', 'rig', 'rig', 'home')
PHASES = ('out', 'rig', 'home', 'stay', 'wait')
KINDS = ('heli', 'induct', 'toolbox', 'ptw', 'round', 'drill', 'secure', 'handover', 'shore')
BONUS = dict(heli=5, induct=5, toolbox=6, ptw=15, round=10, drill=10, secure=10, handover=8, shore=0)
LOG_MAX = 12
BAD = '⚠️ '         # a reading that shows something wrong (the client colours it; the server never says what to do)
STOP_DELAY = 6     # patience a stop costs the job (time, never a mark)


# ================================================================ the rotation
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


_PHASE: dict = {}


def phase(day: int) -> dict:
    """The hitch phase of a career day: kind, step in the cycle (0 out … 5 home), hitch number, days added by storms.
    Walked forward from day 1 once and remembered (like kit.daily)."""
    day = max(1, int(day))
    if day not in _PHASE:
        start = max(_PHASE) if _PHASE else 0
        prev = _PHASE.get(start)
        for d in range(start + 1, day + 1):
            m = mod_of(d)['id']
            if prev is None:
                step, hitch, extra = 0, 1, 0
            else:
                if prev['kind'] == 'wait':
                    step = 0
                elif prev['kind'] == 'stay':
                    step = 5
                else:
                    step = (prev['step'] + 1) % len(CYCLE)
                hitch = prev['hitch'] + (1 if prev['kind'] == 'home' else 0)
                extra = prev['extra'] if prev['kind'] in ('stay', 'wait') else 0
            kind = CYCLE[step]
            if m == 'typhoon' and kind == 'out' and d > 1 and extra < 2:
                kind, extra = 'wait', extra + 1
            elif m == 'typhoon' and kind == 'home' and extra < 2:
                kind, extra = 'stay', extra + 1
            _PHASE[d] = prev = dict(kind=kind, step=step, hitch=hitch, extra=extra)
    return _PHASE[day]


def hitch_label(day: int) -> str:
    p = phase(day)
    if p['kind'] == 'out':
        return 'Ngày 1/14 · bay ra giàn'
    if p['kind'] == 'wait':
        return 'Chờ bay ở bờ · bão'
    if p['kind'] == 'home':
        return 'Ngày 14/14 · bàn giao, về bờ'
    if p['kind'] == 'stay':
        return f'Ngày {14 + p["extra"]} · ở lại thêm vì bão'
    a = 3 * p['step'] - 1
    return f'Ngày {a}–{a + 2}/14 · ca 12 tiếng'


def bunk(hitch: int) -> dict:
    room = K.BUNKS[kit.rng(ID, 'bunk', hitch).randrange(len(K.BUNKS))]
    return dict(room=room, station='A' if room < 200 else 'B')


def plan_of(day: int) -> list:
    """The jobs of the day, slot by slot."""
    p = phase(day)
    m = mod_of(day)['id']
    if p['kind'] == 'out':
        return ['heli', 'induct']
    if p['kind'] == 'wait':
        return ['heli', 'shore']
    if p['kind'] == 'home':
        return ['handover', 'shore']
    if p['kind'] == 'stay' or m == 'typhoon':
        return ['toolbox', 'secure', 'round']
    if day <= 2:
        return ['toolbox', 'ptw', 'round']
    r = kit.rng(ID, 'plan', day)
    rows = ['toolbox', 'ptw', r.choice(('round', 'drill'))]
    if r.random() < 0.5:
        rows.append('drill' if rows[2] == 'round' else 'round')
    return rows


def daily_task_count(day: int) -> int:
    return len(plan_of(day))


def _kind_at(day: int, slot: int) -> str:
    rows = plan_of(day)
    if slot < len(rows):
        return rows[slot]
    if phase(day)['kind'] in ('home', 'wait'):
        return 'shore'
    return ('round', 'ptw')[slot % 2]


# ================================================================ tasks
def _rx(*parts):
    return kit.rng(ID, *parts)


def _heli(day, slot, r):
    p, m = phase(day), mod_of(day)
    cancel = p['kind'] == 'wait'
    delay = 0 if cancel else 60 if m['id'] == 'fog' else 30 if m['id'] == 'monsoon' and r.random() < 0.5 else 0
    if day == 1:
        bag = ['quan_ao', 'thuoc', 'laptop', 'mi', 'ta', 'bat_lua']
        quiz = 'q_sink'
    else:
        ok = [x['id'] for x in K.BAG if not x['banned'] and x['id'] != 'quan_ao']
        bad = [x['id'] for x in K.BAG if x['banned']]
        bag = ['quan_ao'] + r.sample(ok, 4) + r.sample(bad, r.choice((1, 1, 2)))
        r.shuffle(bag)
        quiz = r.choice([q['id'] for q in K.QUIZ])
    needs = dict(phase=p['kind'], hitch=p['hitch'], wx=m['id'], cancel=cancel, delay=delay, bag=bag, limit=K.BAG_LIMIT, quiz=quiz)
    if cancel:
        title, opening = 'Chuyến trực thăng ra giàn: bão', 'Chị Hạnh nhắn: “Áp thấp vào gần, cảng trực thăng có thể hủy chuyến. Em vẫn ra cảng làm thủ tục rồi nghe thông báo nhé.”'
    else:
        title = 'Bay trực thăng ra giàn Hải Âu'
        opening = ('Chị Hạnh: “Soạn túi cho gọn, mặc đồ bơi giữ nhiệt, nghe hướng dẫn thoát hiểm. Ra giàn là không có chuyện quên đồ đâu nha.”' if day == 1 else
                   r.choice(('Chị Hạnh: “Đợt mới rồi em. Túi, đồ bơi, bình thở, nghe hướng dẫn, như mọi lần.”',
                             'Cảng trực thăng Mũi Sao sáng sớm, tiếng cánh quạt xa xa. Chị Hạnh vẫy: “Cân túi trước nha em.”')))
    return HSE, title, opening, needs, dict(bag_out=[], gear=[], quiz=None, waited=False)


def _induct(day, slot, r):
    p = phase(day)
    b = bunk(p['hitch'])
    tones = list(K.ALARM_IDS)
    r.shuffle(tones)
    needs = dict(phase=p['kind'], hitch=p['hitch'], room=b['room'], station=b['station'], tones=tones)
    opening = (f'Chú Toàn đón ở chân sân trực thăng: “Phòng {b["room"]}, ở với thằng Gấu. Gắn thẻ lên bảng đếm người, nhớ xuồng của mình, nghe kỹ tiếng còi.”')
    return TOAN, 'Nhận giàn: thẻ, xuồng, tiếng còi', opening, needs, dict(tcard=False, muster=None, matched={})


def _day_job(day: int) -> str:
    if day <= 3:
        return 'seal' if day <= 2 else 'filter'     # day 3 teaches the passing valve on the lube-oil filter
    return K.JOBS[_rx('job', day).randrange(len(K.JOBS))]['id']


def _toolbox(day, slot, r):
    p, m = phase(day), mod_of(day)
    job = K.JOB_INDEX[_day_job(day)]
    storm = p['kind'] == 'stay' or m['id'] == 'typhoon'
    real = ['height', 'slip', 'lift'] if storm else list(job['hazards'])
    decoys = [h for h in K.HAZARDS if h not in real]
    r.shuffle(decoys)
    hazards = real + decoys[:3]
    r.shuffle(hazards)
    bump_fail = day >= 3 and r.random() < 0.3
    needs = dict(phase=p['kind'], job=None if storm else job['id'], storm=storm, hazards=hazards)
    opening = ('Chú Toàn gom cả ca ở boong chính: “Trước khi chằng buộc chống bão, họp nhanh năm phút.”' if storm else
               f'Chú Toàn gom cả ca ở boong chính: “Hôm nay ca mình {job["title"][0].lower() + job["title"][1:]}. Em dẫn buổi họp an toàn nhé.”')
    return TOAN, 'Họp an toàn đầu ca', opening, needs, dict(ppe=[], bumped=None, swapped=False, picked=[], remind=False), dict(_bump=bump_fail, _real=sorted(real))


def _ptw(day, slot, r):
    p = phase(day)
    jid = _day_job(day) if slot < len(plan_of(day)) else K.JOBS[r.randrange(len(K.JOBS))]['id']
    job = K.JOB_INDEX[jid]
    trap = None
    if day == 3 and jid in K.TRAPS['passing']['jobs']:
        trap = 'passing'
    elif day >= 3:
        pool = [k for k, v in K.TRAPS.items() if jid in v['jobs']]
        if pool and r.random() < 0.5:
            trap = r.choice(pool)
    val = {'passing': str(r.choice((3, 4, 6))), 'gas': str(r.choice((12, 14, 18)) if job['permit'] != 'hot' else r.choice((3, 4, 6))),
           'o2': r.choice(('18,2', '18,6', '17,9')), 'simops': r.choice(('9:30', '10:15', '13:40')), 'live': '380 V'}.get(trap)
    needs = dict(phase=p['kind'], job=jid)
    npc = r.choice((HSE, BAO))
    opening = {HSE: f'Chị Hạnh đưa phiếu việc: “{job["title"]}. Xin đúng giấy phép, khóa đủ, kiểm về không rồi mới mở nhé.”',
               BAO: f'Anh Bảo kẹp điện thoại vào tai: “{job["title"]}, làm lẹ giùm anh, trưa tàu dịch vụ tới lấy đồ cũ!”'}[npc]
    return npc, job['title'], opening, needs, dict(permit=None, xref=False, locks=[], bled=False, proven=False, gas=False, watch=False,
                                                   worked=False, restored=False, stops=[], fixed=False, nearmiss=False, read={}), dict(_trap=trap, _trapv=val)


def _round(day, slot, r):
    p = phase(day)
    tags = r.sample([g[0] for g in K.GAUGES], 5)
    bad = []
    if day >= 2 and r.random() < 0.7:
        bad = r.sample(tags, 1 if r.random() < 0.75 else 2)
    gauges = []
    for tag in tags:
        g = K.GAUGE_INDEX[tag]
        lo, hi, v = g[3], g[4], g[5]
        if tag in bad:
            v = hi + max(1, (hi - lo) // 4) if r.random() < 0.6 else max(0, lo - max(1, (hi - lo) // 4))
        else:
            v = v + r.randint(-max(1, (hi - lo) // 6), max(1, (hi - lo) // 6))
            v = max(lo, min(hi, v))
        gauges.append(dict(tag=tag, value=v))
    areas = r.sample(list(K.AREAS), 3)
    leak = None
    if day >= 3 and r.random() < 0.4:
        leak = dict(area=r.choice(areas), kind=r.choice(tuple(K.LEAKS)))
    needs = dict(phase=p['kind'], gauges=gauges, areas=areas)
    opening = r.choice(('Chú Toàn: “Đi một vòng tuần tra nha. Đọc đồng hồ, nghe tiếng máy, ngửi mùi. Lạ gì báo phòng điều khiển.”',
                        'Phòng điều khiển gọi bộ đàm: “Ca tuần tra đâu rồi? Đi vòng khu công nghệ, báo số cho anh.”'))
    return TOAN, 'Đi tuần: đồng hồ, van, mùi lạ', opening, needs, dict(reads={}, called=[], looked=[], found=False, leak=None), dict(_leak=leak)


def _drill(day, slot, r):
    p = phase(day)
    b = bunk(p['hitch'])
    alarm = r.choice(K.ALARM_IDS)
    real = alarm == 'gas' and r.random() < 0.35
    wind = r.choice(('Đông Bắc', 'Tây Nam', 'Đông', 'Nam'))
    near = r.choice(('khu bình tách', 'khu máy nén', 'khu đầu giếng'))
    routes = [dict(id='up', text=f'Cầu thang phía đón gió {wind}, tránh {near}', ok=True),
              dict(id='short', text=f'Lối tắt băng qua {near}', ok=False),
              dict(id='lift', text='Thang máy khu ở cho nhanh', ok=False)]
    r.shuffle(routes)
    tone = next(x['tone'] for x in K.ALARMS if x['id'] == alarm)
    needs = dict(phase=p['kind'], hitch=p['hitch'], station=b['station'], room=b['room'], wind=wind, near=near, tone=tone, routes=[x['id'] for x in routes],
                 route_text={x['id']: x['text'] for x in routes})
    opening = f'Đang làm thì loa vang lên, kèm tiếng còi. Gió đang thổi từ hướng {wind}.'
    return HSE, 'Còi báo động!', opening, needs, dict(alarm=None, dropped=False, phone=False, route=None, muster=None, carded=False), dict(_alarm=alarm, _live=real)


def _secure(day, slot, r):
    p = phase(day)
    items = ['lifeboat'] + r.sample([x['id'] for x in K.LOOSE if x['id'] != 'lifeboat'], 4)
    r.shuffle(items)
    needs = dict(phase=p['kind'], items=items)
    opening = 'Trưởng giàn đọc loa: “Áp thấp mạnh lên, gió giật cấp 9 trong đêm. Các tổ chằng buộc boong, cẩu dừng, báo về phòng điều khiển.”'
    return TOAN, 'Chằng buộc trước bão', opening, needs, dict(done={}, crane=False)


def _handover(day, slot, r):
    p = phase(day)
    must = [x['id'] for x in K.OPEN_ITEMS if x['must']]
    minor = [x['id'] for x in K.OPEN_ITEMS if not x['must']]
    items = r.sample(must, 3) + r.sample(minor, 1)
    r.shuffle(items)
    needs = dict(phase=p['kind'], items=items)
    opening = 'Anh Bảo: “Viết bàn giao cho ca sau gọn gọn thôi em, ghi mấy cái đẹp đẹp, chuyện lặt vặt khỏi ghi.”'
    return BAO, 'Bàn giao cuối đợt', opening, needs, dict(picked=[])


def _shore(day, slot, r):
    p = phase(day)
    first = not any(phase(d)['kind'] in ('home', 'wait') for d in range(1, day))
    if first and slot < len(plan_of(day)):
        reqs = ['med', 'phone', 'crypto']
    else:
        pick = lambda kind: [x['id'] for x in K.REQUESTS if x['kind'] == kind]
        need = r.choice(pick('need'))
        other = r.choice(pick('want') + pick('gift') + pick('loan'))
        third = r.choice(pick('scam') + pick('loan') + pick('want'))
        reqs = list(dict.fromkeys([need, other, third]))
        while len(reqs) < 3:
            reqs.append(r.choice([x['id'] for x in K.REQUESTS if x['id'] not in reqs]))
        r.shuffle(reqs)
    allowance = 40 + 5 * r.randint(0, 4)
    needs = dict(phase=p['kind'], allowance=allowance, reqs=reqs)
    opening = ('Về tới nhà, Má nấu nồi canh chua. Ăn chưa xong thì điện thoại rung liên tục: ai cũng biết hôm nay bạn nhận phụ cấp đi biển.'
               if p['kind'] == 'home' else 'Bão làm hủy chuyến bay, bạn ở nhà thêm một ngày. Má mừng, rồi cả nhà… bắt đầu nhờ vả.')
    return MA, 'Ngày trên bờ: tiền gửi về nhà', opening, needs, dict(paid=False, asked=[], sent={}, called=False), dict(_push={q: _rx('kin', day, slot, q).randint(0, 2) for q in reqs})


MAKERS = dict(heli=_heli, induct=_induct, toolbox=_toolbox, ptw=_ptw, round=_round, drill=_drill, secure=_secure, handover=_handover, shore=_shore)


def make_task(day: int, slot: int, serial: int) -> dict:
    kind = _kind_at(day, slot)
    r = _rx(kind, day, slot)
    out = MAKERS[kind](day, slot, r)
    npc, title, opening, needs, fields = out[:5]
    hidden = out[5] if len(out) > 5 else {}
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind=kind, needs=needs, gen=GEN, story=None, **fields, **hidden)


FIXED = ('needs', '_bump', '_real', '_trap', '_trapv', '_leak', '_alarm', '_live', '_push')


# ================================================================ the career's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, jobs=0, stops=0, good_stops=0, nearmiss=0, sent=0, scams=0, muster=0)


def initial() -> dict:
    return dict(v=1, intro=False, stats=dict(jobs=0, permits=0, stops=0, good_stops=0, nearmiss=0, drills=0, best_muster=0, sent=0,
                                             scams_refused=0, scammed=0, safe=0, slips=0),
                log=[], regulars={}, today=_fresh_today(0), desk=kit.desk_initial(), odd=ao.initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    ao.ensure(d)
    return d


CFG = dict(crew='Báo chú Toàn (trưởng ca)', company='Báo phòng An toàn', union='Nhờ công đoàn', office='Phòng điều phối nhân sự',
           demoted='kỹ thuật viên tập sự', title='kỹ thuật viên vận hành')


def _pressure(c: dict, d: dict) -> int:
    marks = d['odd']['marks']
    return {'typhoon': 1, 'monsoon': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


def _phase_kind(c: dict) -> str:
    return phase(c['day'])['kind']


# ================================================================ the actions
FREE = ('dk_intro', 'dk_rest')
NO_TICK = ('dk_intro', 'dk_rest', 'dk_desk', 'dk_odd', 'dk_bag', 'dk_gear', 'dk_quiz', 'dk_tcard', 'dk_station', 'dk_tone', 'dk_ppe', 'dk_bump',
           'dk_swap', 'dk_hazard', 'dk_remind', 'dk_permit', 'dk_xref', 'dk_iso', 'dk_verify', 'dk_gas', 'dk_watch', 'dk_nearmiss', 'dk_read',
           'dk_call', 'dk_alarm', 'dk_drop', 'dk_station2', 'dk_note', 'dk_ask', 'dk_send', 'dk_love', 'dk_crane')
PHYSICAL = ('dk_work', 'dk_bleed', 'dk_secure')
WORK_KINDS = ('toolbox', 'ptw', 'round', 'drill', 'secure')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'dk_intro':
        d['intro'] = True
        return dict(message='Vào nghề thôi! Chị Hạnh đang chờ ở cảng trực thăng Mũi Sao.')
    odd = d['odd']
    if name == 'dk_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    desk = d['desk']
    if name == 'dk_desk':
        result = kit.desk_choose(s, c, ID, desk, K.DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'dk_odd':
        result = ao.reply(s, c, ID, odd, K.ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    kit.desk_block(desk, 'Có chuyện trên giàn, quyết xong rồi làm tiếp nhé.')
    ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có trên giàn.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, K.DESK, _phase_kind(c))
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(K.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
        return
    _odd_tick(s, c, d, result)


def _odd_tick(s: dict, c: dict, d: dict, result: dict) -> None:
    x = ao.tick(s, c, ID, d['odd'], K.ODD, busy=d['desk']['ev'] is not None)
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc giàn Hải Âu.')
    kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    kit.need(t['known'], 'Nhận phiếu việc trước đã nhé.')
    return t


def _grounded(c: dict, d: dict, t: dict) -> None:
    kit.need(not (ao.grounded(c, d['odd']) and t['kind'] in WORK_KINDS),
             'Bạn đang tạm đình chỉ làm việc trên giàn hôm nay. Tan ca, mai lên phòng an toàn trình bày.', 'grounded')


def _refuse(t: dict, code: str, sev: int, text: str, note: str, message: str) -> dict:
    t['mistakes'] += 1
    cq.slip(t, code, sev, text, note)
    return dict(message=message, correct=False)


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _finish(s: dict, c: dict, d: dict, t: dict, narrative: str) -> str:
    """Close a job once: the small bonus (none after a safety slip), the log, a line of the people you work with."""
    pts = cq.points(t)
    base = BONUS[t['kind']]
    full = 0 if cq.safety(t) else max(0, base - 2 * pts)
    reward = ao.bonus(d['odd'], full)
    i = _npc_index(t)
    story = ''
    if i in K.REG_STORY:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        story = K.REG_STORY[i][min(r['visits'], len(K.REG_STORY[i])) - 1]
        t['story'] = story
    st, today = d['stats'], d['today']
    st['jobs'] = min(10 ** 7, st['jobs'] + 1)
    today['jobs'] += 1
    st['safe' if not cq.safety(t) else 'slips'] = min(10 ** 7, st['safe' if not cq.safety(t) else 'slips'] + 1)
    d['log'] = (d['log'] + [dict(day=c['day'], kind=t['kind'], title=t['title'][:80], ok=not cq.slips(t))])[-LOG_MAX:]
    kit.complete(s, c, t, reward, narrative[:300])
    note = ao.flown(d['odd'], not cq.slips(t), CFG)
    tail = f' Thưởng {reward} xu.' if reward else ''
    if full and reward < full:
        tail += ' (Đang bị hạ bậc: không có thưởng.)' if not reward else ' (Mệt quá: nửa thưởng.)'
    if cq.safety(t):
        tail += ' 🛡️ Chị Hạnh sẽ ngồi xem lại việc này cùng bạn.'
    return f'{narrative}{tail} {note} {("💬 " + story) if story else ""}'.strip()


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Chú Toàn'


# ---------------------------------------------------------------- the helicopter out
def _bag(s, c, d, p):
    t = _task(c, p, ('heli',))
    kit.need(t['status'] != 'completed', 'Đã lên trực thăng rồi.')
    item = kit.one_of(p.get('item'), t['needs']['bag'], 'Món này không có trong túi.')
    x = K.BAG_INDEX[item]
    if item in t['bag_out']:
        t['bag_out'].remove(item)
        return dict(message=f'{x["emoji"]} Bỏ lại {_lower(x["name"])} vào túi.')
    t['bag_out'].append(item)
    kit.start_work(t)
    return dict(message=f'{x["emoji"]} Lấy {_lower(x["name"])} ra, gửi về nhà.' + (f' {x["why"]}' if x['banned'] else ''))


def bag_kg(t: dict) -> float:
    return round(sum(K.BAG_INDEX[i]['kg'] for i in t['needs']['bag'] if i not in t['bag_out']), 1)


def _gear(s, c, d, p):
    t = _task(c, p, ('heli',))
    g = kit.one_of(p.get('item'), K.GEAR_IDS, 'Đồ này không có ở cảng.')
    x = next(r for r in K.GEAR if r['id'] == g)
    if g in t['gear']:
        t['gear'].remove(g)
        return dict(message=f'Cởi {_lower(x["name"])}.')
    t['gear'].append(g)
    kit.start_work(t)
    return dict(message=f'{x["emoji"]} {x["name"]}: {x["note"]}')


def _quiz(s, c, d, p):
    t = _task(c, p, ('heli',))
    kit.need(t['quiz'] is None, 'Đã trả lời rồi.')
    q = K.QUIZ_INDEX[t['needs']['quiz']]
    a = kit.one_of(p.get('answer'), [o[0] for o in q['options']], 'Chọn một câu trả lời.')
    t['quiz'] = a
    kit.start_work(t)
    if a != q['answer']:
        t['mistakes'] += 1
        cq.slip(t, 'huet', 1, 'Trả lời sai câu hỏi thoát hiểm trực thăng trước giờ bay.', 'chưa thuộc cách thoát hiểm')
        right = next(o[1] for o in q['options'] if o[0] == q['answer'])
        return dict(message=f'🎬 Chị Hạnh dừng video: “Chưa đúng. {q["why"]}” Đáp án: {right}.', correct=False)
    return dict(message=f'🎬 Đúng rồi. {q["why"]}', celebrate=True)


def _wait(s, c, d, p):
    t = _task(c, p, ('heli',))
    n = t['needs']
    kit.need(n['delay'] or n['cancel'], 'Chuyến bay đúng giờ, không cần chờ.')
    kit.need(not t['waited'], 'Đã nghe thông báo rồi.')
    t['waited'] = True
    kit.start_work(t)
    if n['cancel']:
        msg = _finish(s, c, d, t, 'Cảng trực thăng hủy chuyến vì áp thấp. Bạn trả đồ bơi, về nhà chờ, mai bay.')
        return dict(message='🌀 ' + msg)
    t['patience'] = max(25, t.get('patience', 100) - 5)
    return dict(message=f'🌫️ Chuyến bay hoãn {n["delay"]} phút vì {"sương" if n["wx"] == "fog" else "gió giật"}. Bạn ngồi phòng chờ, không đi đâu xa. Có loa gọi thì làm thủ tục tiếp.')


def _board(s, c, d, p):
    t = _task(c, p, ('heli',))
    n = t['needs']
    kit.need(not n['cancel'], 'Chuyến bay đã hủy vì bão. Nghe thông báo rồi về nhà chờ nhé.')
    kit.need(not n['delay'] or t['waited'], 'Chuyến bay đang hoãn. Nghe thông báo, ngồi chờ ở phòng chờ trước đã.')
    kit.need(t['quiz'] is not None, 'Xem video hướng dẫn thoát hiểm và trả lời câu hỏi trước khi lên máy bay.')
    missing = [x['name'].lower() for x in K.GEAR if x['id'] not in t['gear']]
    if missing:
        return _refuse(t, 'gear', 2, 'Ra cửa lên trực thăng mà thiếu đồ cứu sinh.', 'thiếu đồ cứu sinh',
                       f'✋ Nhân viên cảng chặn ở cửa: “Thiếu {", ".join(missing)}. Mặc đủ mới lên được.”')
    banned = [K.BAG_INDEX[i] for i in n['bag'] if i not in t['bag_out'] and K.BAG_INDEX[i]['banned']]
    kit.start_work(t)
    notes = []
    if banned:
        t['mistakes'] += 1
        names = ', '.join(_lower(x['name']) for x in banned)
        cq.slip(t, 'banned', 2, f'Máy soi phát hiện {names} trong túi lên trực thăng.', 'mang đồ cấm lên trực thăng', safety=True)
        t['bag_out'] += [x['id'] for x in banned]
        notes.append(f'🚫 Máy soi phát hiện {names}: bị giữ lại ở cảng, ghi biên bản.')
    if bag_kg(t) > n['limit']:
        t['mistakes'] += 1
        cq.slip(t, 'heavy', 1, f'Túi nặng {bag_kg(t)} kg, quá {n["limit"]} kg của cảng.', 'túi quá ký')
        notes.append(f'⚖️ Túi {bag_kg(t)} kg, quá {n["limit"]} kg: phải mở túi bỏ bớt đồ ngay ở quầy, cả hàng chờ.')
    msg = _finish(s, c, d, t, '🚁 Thắt dây, chụp tai, trực thăng cất cánh. Bốn mươi phút sau giàn Hải Âu hiện ra giữa biển.')
    return dict(message=' '.join(notes + [msg]), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- arrival
def _tcard(s, c, d, p):
    t = _task(c, p, ('induct',))
    kit.need(not t['tcard'], 'Thẻ đã gắn rồi.')
    t['tcard'] = True
    kit.start_work(t)
    return dict(message='🪪 Gắn thẻ tên vào cột “Trên giàn” của bảng đếm người. Có báo động, người ta đếm theo bảng này.')


def _station(s, c, d, p):
    t = _task(c, p, ('induct',))
    st = kit.one_of(p.get('station'), tuple(K.STATIONS), 'Chọn xuồng cứu sinh.')
    kit.start_work(t)
    n = t['needs']
    if st != n['station']:
        t['mistakes'] += 1
        cq.slip(t, 'muster', 2, f'Nhận nhầm điểm tập trung: phòng {n["room"]} thuộc xuồng {n["station"]}.', 'nhầm điểm tập trung')
        return dict(message=f'✋ Chú Toàn chỉ tấm biển ở cửa phòng {n["room"]}: “Phòng em thuộc {K.STATIONS[n["station"]]}. Xem lại biển cửa phòng nhé.”', correct=False)
    t['muster'] = st
    return dict(message=f'🛶 {K.STATIONS[st]}: điểm tập trung của bạn đợt này.')


def _tone(s, c, d, p):
    t = _task(c, p, ('induct',))
    tone = kit.one_of(p.get('tone'), K.ALARM_IDS, 'Tiếng còi không có.')
    pick = kit.one_of(p.get('pick'), K.ALARM_IDS, 'Chọn ý nghĩa của tiếng còi.')
    kit.start_work(t)
    a = next(x for x in K.ALARMS if x['id'] == tone)
    if pick != tone:
        t['mistakes'] += 1
        cq.slip(t, 'tones', 1, 'Nhầm ý nghĩa tiếng còi báo động của giàn.', 'nhầm tiếng còi')
        return dict(message=f'✋ “{a["tone"]}” không phải vậy. Đọc lại bảng tiếng còi ở chân cầu thang nhé.', correct=False)
    t['matched'][tone] = pick
    return dict(message=f'{a["emoji"]} {a["tone"]} = {a["name"]}: {a["do"]}')


def _settle(s, c, d, p):
    t = _task(c, p, ('induct',))
    kit.need(t['muster'], 'Chọn đúng xuồng cứu sinh của phòng mình trước đã.')
    kit.need(set(t['matched']) == set(K.ALARM_IDS), 'Nhớ đủ ba tiếng còi của giàn trước đã.')
    kit.start_work(t)
    if not t['tcard']:
        t['mistakes'] += 1
        cq.slip(t, 'pob', 2, 'Lên giàn mà chưa gắn thẻ vào bảng đếm người.', 'chưa gắn thẻ đếm người')
    msg = _finish(s, c, d, t, f'🧳 Cất túi vào phòng {t["needs"]["room"]}. Gấu chìa tay: “Chào bạn cùng phòng! Tao ngáy hơi to, thông cảm nha.”')
    return dict(message=('⚠️ Bảng đếm người không có tên bạn: chị Hạnh nhắc gắn thẻ ngay. ' if not t['tcard'] else '') + msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the toolbox talk
def _ppe(s, c, d, p):
    t = _task(c, p, ('toolbox',))
    _grounded(c, d, t)
    item = kit.one_of(p.get('item'), K.PPE_IDS, 'Đồ bảo hộ không có.')
    x = next(r for r in K.PPE if r['id'] == item)
    kit.start_work(t)
    if item in t['ppe']:
        t['ppe'].remove(item)
        return dict(message=f'Tháo {_lower(x["name"])}.')
    t['ppe'].append(item)
    return dict(message=f'{x["emoji"]} {x["name"]}: đã mang.')


def _bump(s, c, d, p):
    t = _task(c, p, ('toolbox',))
    _grounded(c, d, t)
    kit.need(t['bumped'] != 'pass', 'Máy đo đã thử đạt rồi.')
    kit.start_work(t)
    if t['_bump'] and not t['swapped']:
        t['bumped'] = 'fail'
        return dict(message='📟 Xịt khí mẫu vào máy đo: kênh LEL, O₂, CO kêu đủ, kênh H₂S không phản ứng ❌. Máy này không dùng được.', correct=False)
    t['bumped'] = 'pass'
    return dict(message='📟 Xịt khí mẫu: cả bốn kênh báo đủ, còi rung đèn chớp ✅. Máy đo dùng được.')


def _swap(s, c, d, p):
    t = _task(c, p, ('toolbox',))
    kit.need(t['bumped'] == 'fail', 'Máy đo đang tốt, không cần đổi.')
    t['swapped'] = True
    t['bumped'] = None
    return dict(message='🔁 Gửi máy hỏng lên kho an toàn, nhận máy dự phòng. Thử khí mẫu lại nhé.')


def _hazard(s, c, d, p):
    t = _task(c, p, ('toolbox',))
    h = kit.one_of(p.get('hazard'), t['needs']['hazards'], 'Mối nguy này không có trong danh sách.')
    kit.start_work(t)
    if h in t['picked']:
        t['picked'].remove(h)
        return dict(message='Bỏ khỏi danh sách họp.')
    t['picked'].append(h)
    e, name, ctrl = K.HAZARDS[h]
    return dict(message=f'{e} {name}: {ctrl}')


def _remind(s, c, d, p):
    t = _task(c, p, ('toolbox',))
    kit.need(not t['remind'], 'Đã nhắc rồi.')
    t['remind'] = True
    return dict(message='✋ “Ai thấy không an toàn thì dừng việc, ai cũng có quyền, không ai bị trách vì dừng.” Cả ca gật đầu.')


def _talk(s, c, d, p):
    t = _task(c, p, ('toolbox',))
    _grounded(c, d, t)
    kit.start_work(t)
    notes = []
    if t['bumped'] is None:
        t['mistakes'] += 1
        cq.slip(t, 'nobump', 2, 'Vào ca với máy đo khí chưa thử khí mẫu.', 'chưa thử máy đo khí', safety=True)
        notes.append('📟 Máy đo khí chưa thử: lỡ hỏng thì có khí cũng không báo.')
    elif t['bumped'] == 'fail':
        t['mistakes'] += 1
        cq.slip(t, 'badmon', 3, 'Vào ca với máy đo khí đã thử hỏng kênh H₂S.', 'dùng máy đo khí hỏng', safety=True)
        notes.append('📟 Mang máy đo hỏng kênh H₂S vào khu công nghệ: chú Toàn giật lại ngay ở cửa.')
    miss = [K.PPE[i]['name'].lower() for i in range(len(K.PPE)) if K.PPE[i]['id'] not in t['ppe']]
    if miss:
        t['mistakes'] += 1
        cq.slip(t, 'ppe', 1, f'Vào ca thiếu {", ".join(miss)}.', 'thiếu đồ bảo hộ')
        notes.append(f'🦺 Thiếu {", ".join(miss)}.')
    real = set(t['_real'])
    left = [K.HAZARDS[h][1].lower() for h in t['needs']['hazards'] if h in real and h not in t['picked']]
    if left:
        t['mistakes'] += 1
        cq.slip(t, 'hazard', 1, f'Buổi họp an toàn bỏ sót mối nguy: {", ".join(left)}.', 'sót mối nguy')
        notes.append(f'🗣️ Chú Toàn bổ sung: “Còn {", ".join(left)} nữa.”')
    if not t['remind']:
        t['mistakes'] += 1
        cq.slip(t, 'stopcard', 1, 'Buổi họp không nhắc quyền dừng việc.', 'quên nhắc quyền dừng việc')
    msg = _finish(s, c, d, t, '🗣️ Họp an toàn xong, cả ca ký tên. Ai vào việc nấy.')
    return dict(message=' '.join(notes + [msg]), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- maintenance under a permit
def _job(t: dict) -> dict:
    return K.JOB_INDEX[t['needs']['job']]


def _trap_open(t: dict) -> str | None:
    return t['_trap'] if t['_trap'] and not t['fixed'] else None


def _ptw_live(c, d, p) -> dict:
    t = _task(c, p, ('ptw',))
    _grounded(c, d, t)
    return t


def _permit(s, c, d, p):
    t = _ptw_live(c, d, p)
    kit.need(t['permit'] is None, 'Giấy phép đã cấp rồi.')
    kind = kit.one_of(p.get('permit'), tuple(K.PERMITS), 'Chọn loại giấy phép.')
    kit.start_work(t)
    job = _job(t)
    if kind != job['permit']:
        return _refuse(t, 'permit', 1, 'Xin sai loại giấy phép cho việc bảo dưỡng.', 'sai loại giấy phép',
                       f'📋 Chị Hạnh trả lại: “{K.PERMITS[kind][1]} không đúng việc này. Đọc kỹ phiếu việc: việc có sinh lửa không, có vào bồn không, có làm trên điện không?”')
    t['permit'] = kind
    d['stats']['permits'] = min(10 ** 7, d['stats']['permits'] + 1)
    return dict(message=f'{K.PERMITS[kind][0]} Chị Hạnh ký cấp {K.PERMITS[kind][1].lower()}, dán bản sao lên bảng giấy phép.')


def _need_permit(t):
    kit.need(t['permit'], 'Xin giấy phép làm việc trước đã.')
    kit.need(not t['worked'], 'Việc chính đã làm xong.')


def _xref(s, c, d, p):
    t = _ptw_live(c, d, p)
    _need_permit(t)
    kit.need(not t['xref'], 'Đã đối chiếu rồi.')
    t['xref'] = True
    if _trap_open(t) == 'simops':
        t['read']['xref'] = BAD + K.TRAPS['simops']['text'].format(v=t['_trapv'])
        return dict(message='🏗️ ' + t['read']['xref'][len(BAD):], correct=False)
    t['read']['xref'] = 'Không có việc nào trùng khu: cẩu nghỉ, không ai làm nóng gần đó.'
    return dict(message='📋 ' + t['read']['xref'])


def _iso(s, c, d, p):
    t = _ptw_live(c, d, p)
    _need_permit(t)
    job = _job(t)
    pts = {x[0]: x for x in job['points']}
    pid = kit.one_of(p.get('point'), pts, 'Điểm cô lập không có trong phiếu.')
    tag, name, kind = pts[pid]
    if pid in t['locks']:
        t['locks'].remove(pid)
        return dict(message=f'🔓 Tháo khóa {tag}.')
    t['locks'].append(pid)
    verb = 'Đóng' if kind == 'valve' else 'Cắt'
    return dict(message=f'🔒 {verb} {name.lower()} {tag}, treo ổ khóa đỏ của bạn và thẻ “Cấm thao tác”.')


def _bleed(s, c, d, p):
    t = _ptw_live(c, d, p)
    _need_permit(t)
    job = _job(t)
    kit.need(job['bleed'], 'Việc này không cần xả.')
    kit.need(not t['bled'], 'Đã xả rồi.')
    valves = [x[0] for x in job['points'] if x[2] == 'valve']
    kit.need(all(v in t['locks'] for v in valves), 'Khóa đủ các van cô lập rồi mới xả.')
    t['bled'] = True
    return dict(message=f'💨 Mở {job["bleed"]}: xả áp, xả cạn về bồn thu.')


def _verify(s, c, d, p):
    t = _ptw_live(c, d, p)
    _need_permit(t)
    job = _job(t)
    kit.need(job['prove'], 'Việc này không có gì để kiểm về không.')
    kit.need(all(x[0] in t['locks'] for x in job['points']), 'Khóa đủ mọi điểm cô lập trước khi kiểm về không.')
    kit.need(not job['bleed'] or t['bled'], 'Xả áp trước rồi mới kiểm về không.')
    t['proven'] = True
    trap = _trap_open(t)
    if trap in ('passing', 'live'):
        t['read']['verify'] = BAD + K.TRAPS[trap]['text'].format(v=t['_trapv'])
        return dict(message=('💥 ' if trap == 'passing' else '⚡ ') + t['read']['verify'][len(BAD):], correct=False)
    t['read']['verify'] = f'{job["prove"]}: về không. Không còn áp, không còn điện.' if any(x[2] == 'breaker' for x in job['points']) else f'{job["prove"]}: 0 bar, không còn áp.'
    return dict(message='0️⃣ ' + t['read']['verify'])


def gas_reading(t: dict) -> dict:
    job = _job(t)
    trap = _trap_open(t)
    lel, o2, h2s = 0, 20.9, 0
    if trap == 'gas':
        lel = int(t['_trapv'])
    elif trap == 'o2':
        o2 = float(t['_trapv'].replace(',', '.'))
    hot = job['permit'] == 'hot'
    limit = K.GAS_LIMIT['lel_hot'] if hot else K.GAS_LIMIT['lel']
    ok = lel <= limit and K.GAS_LIMIT['o2_lo'] <= o2 <= K.GAS_LIMIT['o2_hi'] and h2s <= K.GAS_LIMIT['h2s']
    return dict(lel=lel, o2=o2, h2s=h2s, lel_limit=limit, ok=ok)


def _gas(s, c, d, p):
    t = _ptw_live(c, d, p)
    _need_permit(t)
    t['gas'] = True
    g = gas_reading(t)
    o2 = f'{g["o2"]:.1f}'.replace('.', ',')
    line = f'LEL {g["lel"]}% (giới hạn {g["lel_limit"]}%) · O₂ {o2}% · H₂S {g["h2s"]} ppm.'
    trap = _trap_open(t)
    if trap in ('gas', 'o2'):
        t['read']['gas'] = f'{BAD}{line} {K.TRAPS[trap]["text"].format(v=t["_trapv"])}'
        return dict(message='☁️ ' + t['read']['gas'][len(BAD):], correct=False)
    t['read']['gas'] = f'{line} Đạt.'
    return dict(message='📟 ' + t['read']['gas'])


def _watch(s, c, d, p):
    t = _ptw_live(c, d, p)
    _need_permit(t)
    job = _job(t)
    kit.need(job['watch'], 'Việc này không cần người canh riêng.')
    kit.need(not t['watch'], 'Đã bố trí rồi.')
    t['watch'] = True
    e, line = K.WATCH[job['watch']]
    return dict(message=f'{e} {line}: Gấu đứng canh, không rời chỗ tới khi xong việc.')


def _stop(s, c, d, p):
    """✋ Stop-work authority: never wrong. With a hazard there, the work waits until it is put right."""
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['kind'] in ('ptw', 'round', 'drill', 'secure', 'toolbox'), 'Không có việc nào để dừng.')
    kit.need(t['known'], 'Nhận phiếu việc trước đã nhé.')
    kit.need(not t.get('worked'), 'Việc chính đã làm xong.')
    reason = kit.one_of(p.get('reason', 'unsure'), tuple(K.STOP_REASONS), 'Chọn lý do dừng việc.')
    stops = t.setdefault('stops', [])
    kit.need(len(stops) < 6, 'Đã dừng nhiều lần rồi. Bàn với chú Toàn nhé.')
    stops.append(reason)
    kit.start_work(t)
    st, today = d['stats'], d['today']
    st['stops'] = min(10 ** 7, st['stops'] + 1)
    today['stops'] += 1
    t['patience'] = max(25, t.get('patience', 100) - STOP_DELAY)
    trap = _trap_open(t) if t['kind'] == 'ptw' else None
    if trap:
        x = K.TRAPS[trap]
        t['fixed'] = True
        st['good_stops'] = min(10 ** 7, st['good_stops'] + 1)
        today['good_stops'] += 1
        c['xp'] += 10 if reason == x['reason'] else 6
        if x['seen'] in t['read']:
            t['read'][x['seen']] = 'Đã xử lý: ' + x['fix']
        head = '✋ Bạn dừng việc, gọi chú Toàn.' + (' Đúng chỗ bạn nghi.' if reason == x['reason'] else ' Chú Toàn kiểm cùng bạn và tìm ra chỗ sai.')
        return dict(message=f'{head} {x["fix"]} Bạn có thể ghi báo cáo suýt sự cố.', celebrate=True)
    c['xp'] += 2
    return dict(message='✋ Bạn dừng việc, chú Toàn ra kiểm cùng: không có gì bất thường, làm tiếp được. “Dừng để hỏi không bao giờ sai, con.”')


def _nearmiss(s, c, d, p):
    t = kit.task(c, p)
    kit.need(t['career'] == ID and t['known'], 'Không có việc nào để báo.')
    kit.need(not t.get('nearmiss'), 'Đã gửi báo cáo rồi.')
    kit.need((t['kind'] == 'ptw' and t.get('fixed')) or cq.slips(t), 'Chưa có suýt sự cố nào để báo ở việc này.')
    t['nearmiss'] = True
    st, today = d['stats'], d['today']
    st['nearmiss'] = min(10 ** 7, st['nearmiss'] + 1)
    today['nearmiss'] += 1
    c['xp'] += 6
    kit.review(s, c, kit.npc_id(ID, HSE), 5, 'Cảm ơn em đã ghi báo cáo suýt sự cố. Cả giàn sẽ học từ chuyện này, không ai bị phạt vì báo.', f'nm-{t["id"]}')
    return dict(message='📝 Gửi báo cáo suýt sự cố cho chị Hạnh: chuyện gì xảy ra, vì sao, sửa thế nào. Người báo không bị phạt.', celebrate=True)


def _work(s, c, d, p):
    t = _ptw_live(c, d, p)
    _need_permit(t)
    job = _job(t)
    kit.start_work(t)
    notes = []
    missing = [x[0] for x in job['points'] if x[0] not in t['locks']]
    if missing:
        t['mistakes'] += 1
        cq.slip(t, 'iso', 3, f'Làm việc khi chưa khóa đủ điểm cô lập: {", ".join(missing)}.', 'chưa khóa đủ điểm cô lập', safety=True)
        notes.append(f'🔓 {", ".join(missing)} chưa khóa: chú Toàn chạy tới khóa giùm, mặt tái đi.')
    if job['bleed'] and not t['bled']:
        t['mistakes'] += 1
        cq.slip(t, 'bleed', 2, 'Mở thiết bị khi chưa xả áp.', 'chưa xả áp', safety=True)
        notes.append('💨 Chưa xả áp mà mở: hơi xì mạnh ra, may đứng lệch.')
    if job['prove'] and not t['proven']:
        t['mistakes'] += 1
        cq.slip(t, 'prove', 2, 'Không kiểm về không trước khi mở thiết bị.', 'không kiểm về không', safety=True)
    if not t['gas']:
        t['mistakes'] += 1
        cq.slip(t, 'nogas', 2, 'Không đo khí trước khi làm.', 'không đo khí', safety=True)
    if job['watch'] and not t['watch']:
        t['mistakes'] += 1
        cq.slip(t, 'watch', 2, 'Làm nóng/vào bồn mà không có người canh.', 'không có người canh', safety=True)
    if job['permit'] == 'hot' and not t['xref']:
        t['mistakes'] += 1
        cq.slip(t, 'xref', 1, 'Làm nóng mà không đối chiếu bảng giấy phép đang mở.', 'không đối chiếu giấy phép')
    trap = _trap_open(t)
    if trap:
        x = K.TRAPS[trap]
        t['mistakes'] += 1
        cq.slip(t, 'trap_' + trap, 3, x['harm'], 'làm tiếp khi có dấu hiệu nguy hiểm', safety=True)
        t['fixed'] = True
        if x['seen'] in t['read']:
            t['read'][x['seen']] = 'Đã xử lý: ' + x['fix']
        notes.append(f'🚨 {x["harm"]} Cả khu dừng việc; {x["fix"]}')
    t['worked'] = True
    head = f'🔧 {job["work"]}'
    return dict(message=' '.join([head] + notes), correct=not notes, celebrate=not cq.slips(t))


def _restore(s, c, d, p):
    t = _task(c, p, ('ptw',))
    kit.need(t['worked'], 'Làm xong việc chính đã.')
    kit.need(not t['restored'], 'Đã trả thiết bị về vận hành.')
    t['restored'] = True
    t['locks'] = []
    return dict(message='🔁 Dọn dụng cụ, đếm đủ đồ nghề, tháo khóa của mình, mở van theo thứ tự, chạy thử: thiết bị chạy êm.')


def _close(s, c, d, p):
    t = _task(c, p, ('ptw',))
    kit.need(t['worked'], 'Làm xong việc chính đã.')
    if not t['restored']:
        t['mistakes'] += 1
        cq.slip(t, 'restore', 1, 'Trả giấy phép khi chưa tháo khóa, chưa chạy thử thiết bị.', 'chưa trả thiết bị về vận hành')
    msg = _finish(s, c, d, t, f'📋 Trả giấy phép, chị Hạnh ký đóng. {_job(t)["tag"]} trở lại vận hành.')
    return dict(message=msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- rounds
def _gauge(t: dict, tag: str) -> dict:
    g = next(x for x in t['needs']['gauges'] if x['tag'] == tag)
    row = K.GAUGE_INDEX[tag]
    return dict(tag=tag, name=row[1], unit=row[2], lo=row[3], hi=row[4], value=g['value'],
                verdict='high' if g['value'] > row[4] else 'low' if g['value'] < row[3] else 'ok')


def _read(s, c, d, p):
    t = _task(c, p, ('round',))
    _grounded(c, d, t)
    tags = [g['tag'] for g in t['needs']['gauges']]
    tag = kit.one_of(p.get('tag'), tags, 'Đồng hồ này không có trên tuyến tuần.')
    verdict = kit.one_of(p.get('verdict'), ('ok', 'high', 'low'), 'Chọn: trong giới hạn, cao hay thấp.')
    kit.start_work(t)
    g = _gauge(t, tag)
    t['reads'][tag] = verdict
    if verdict != g['verdict']:
        t['mistakes'] += 1
        cq.slip(t, 'misread', 1, 'Đọc nhầm đồng hồ so với giới hạn.', 'đọc nhầm đồng hồ')
        return dict(message=f'✋ Chú Toàn: “{tag} chỉ {g["value"]} {g["unit"]}, giới hạn {g["lo"]}–{g["hi"]}. Nhìn lại dải giới hạn nhé.”', correct=False)
    word = {'ok': 'trong giới hạn', 'high': 'CAO quá giới hạn', 'low': 'THẤP dưới giới hạn'}[verdict]
    return dict(message=f'📈 {tag} {g["name"]}: {g["value"]} {g["unit"]}, {word}.' + (' Báo phòng điều khiển nhé.' if verdict != 'ok' else ''))


def _call(s, c, d, p):
    t = _task(c, p, ('round',))
    tags = [g['tag'] for g in t['needs']['gauges']]
    tag = kit.one_of(p.get('tag'), tags, 'Đồng hồ này không có trên tuyến tuần.')
    kit.need(tag not in t['called'], 'Đã báo rồi.')
    t['called'].append(tag)
    g = _gauge(t, tag)
    if g['verdict'] == 'ok':
        return dict(message=f'📻 Phòng điều khiển: “{tag} {g["value"]} {g["unit"]} là bình thường mà em. Cảm ơn đã hỏi.”')
    return dict(message=f'📻 Báo phòng điều khiển: {tag} {g["value"]} {g["unit"]}. “Nhận, anh chỉnh van điều khiển, ghi sổ ca.”')


def _look(s, c, d, p):
    t = _task(c, p, ('round',))
    _grounded(c, d, t)
    area = kit.one_of(p.get('area'), t['needs']['areas'], 'Khu này không có trên tuyến tuần.')
    kit.need(area not in t['looked'], 'Đã đi khu này rồi.')
    t['looked'].append(area)
    kit.start_work(t)
    e, name = K.AREAS[area]
    lk = t['_leak']
    if lk and lk['area'] == area:
        t['found'] = True
        return dict(message=f'{e} {name}: {K.LEAKS[lk["kind"]]} Phải xử lý ngay.', correct=False)
    return dict(message=f'{e} {name}: {K.CALM_LOOK[area]}')


def _leak(s, c, d, p):
    t = _task(c, p, ('round',))
    kit.need(t['found'] and t['leak'] is None, 'Không có chỗ rò nào đang chờ xử lý.')
    how = kit.one_of(p.get('how'), ('report', 'tighten'), 'Chọn cách xử lý.')
    t['leak'] = how
    if how == 'report':
        c['xp'] += 6
        return dict(message='📻 Báo phòng điều khiển, rào khu vực, đứng ngược gió chờ đội bảo dưỡng cô lập đoạn ống. Không tự siết khi còn áp.', celebrate=True)
    t['mistakes'] += 1
    cq.slip(t, 'tighten', 3, 'Tự siết bích đang rò khi đường ống còn áp.', 'tự xử lý rò khi còn áp', safety=True)
    return dict(message='🔧 Bạn cầm cờ lê siết thử: bu lông cũ gãy, chỗ rò xì mạnh hơn. Phòng điều khiển phải dừng khẩn cấp đoạn ống.', correct=False)


def _logbook(s, c, d, p):
    t = _task(c, p, ('round',))
    _grounded(c, d, t)
    tags = [g['tag'] for g in t['needs']['gauges']]
    kit.need(all(tag in t['reads'] for tag in tags), 'Đọc hết các đồng hồ trên tuyến trước khi ghi sổ.')
    kit.start_work(t)
    notes = []
    silent = [tag for tag in tags if _gauge(t, tag)['verdict'] != 'ok' and tag not in t['called']]
    if silent:
        t['mistakes'] += 1
        cq.slip(t, 'nocall', 2, f'Thấy {", ".join(silent)} ngoài giới hạn mà không báo phòng điều khiển.', 'không báo số ngoài giới hạn')
        notes.append(f'📻 {", ".join(silent)} ngoài giới hạn mà chưa báo: ca sau phát hiện muộn.')
    skipped = [a for a in t['needs']['areas'] if a not in t['looked']]
    lk = t['_leak']
    if lk and lk['area'] in skipped:
        t['mistakes'] += 1
        cq.slip(t, 'missed', 2, f'Bỏ qua {K.AREAS[lk["area"]][1].lower()}, chỗ rò để tới ca sau mới thấy.', 'bỏ qua khu có rò')
        notes.append(f'🔎 Ca sau thấy chỗ rò ở {K.AREAS[lk["area"]][1].lower()}, khu bạn bỏ qua.')
    elif skipped:
        t['mistakes'] += 1
        cq.slip(t, 'skipped', 1, 'Không đi hết các khu trên tuyến tuần.', 'bỏ khu tuần tra')
    if lk and t['found'] and t['leak'] is None:
        t['mistakes'] += 1
        cq.slip(t, 'leak_quiet', 2, 'Thấy chỗ rò mà không báo.', 'không báo chỗ rò')
    msg = _finish(s, c, d, t, '📒 Ghi sổ tuần tra, ký tên, gửi phòng điều khiển.')
    return dict(message=' '.join(notes + [msg]), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- drills
def _alarm(s, c, d, p):
    t = _task(c, p, ('drill',))
    _grounded(c, d, t)
    kit.need(t['alarm'] is None, 'Đã nhận ra tiếng còi rồi.')
    pick = kit.one_of(p.get('pick'), K.ALARM_IDS, 'Chọn ý nghĩa tiếng còi.')
    kit.start_work(t)
    a = next(x for x in K.ALARMS if x['id'] == t['_alarm'])
    t['alarm'] = pick
    if pick != t['_alarm']:
        t['mistakes'] += 1
        cq.slip(t, 'tone', 1, 'Nhầm tiếng còi báo động.', 'nhầm tiếng còi')
        return dict(message=f'📢 Loa nhắc lại: “{a["name"]}!” Bạn nghe nhầm. {a["do"]}', correct=False)
    return dict(message=f'{a["emoji"]} {a["name"]}. {a["do"]}')


def _drop(s, c, d, p):
    t = _task(c, p, ('drill',))
    kit.need(not t['dropped'], 'Đã để thiết bị an toàn rồi.')
    t['dropped'] = True
    return dict(message='🧰 Tắt máy hàn, rút điện, để dụng cụ gọn một chỗ, đóng van đang thao tác. Đi.')


def _phone(s, c, d, p):
    t = _task(c, p, ('drill',))
    kit.need(not t['phone'] and t['route'] is None, 'Không quay lại được nữa.')
    t['phone'] = True
    t['mistakes'] += 1
    cq.slip(t, 'phone', 2, 'Có báo động mà quay về phòng lấy điện thoại.', 'quay lại lấy đồ khi có báo động')
    return dict(message='📱 Bạn chạy ngược về phòng lấy điện thoại, mất hai phút. Điện thoại không cứu được ai.', correct=False)


def _route(s, c, d, p):
    t = _task(c, p, ('drill',))
    _grounded(c, d, t)
    kit.need(t['alarm'] is not None, 'Nghe rõ tiếng còi là gì trước đã.')
    kit.need(t['route'] is None, 'Đã chọn đường rồi.')
    rid = kit.one_of(p.get('route'), t['needs']['routes'], 'Chọn một lối đi.')
    t['route'] = rid
    if rid == 'up':
        return dict(message=f'🧭 Đi cầu thang phía đón gió {t["needs"]["wind"]}, tránh xa {t["needs"]["near"]}.')
    t['mistakes'] += 1
    if rid == 'lift':
        cq.slip(t, 'lift', 2, 'Đi thang máy khi có báo động.', 'đi thang máy khi báo động', safety=True)
        return dict(message='🛗 Thang máy khóa cứng khi có báo động. Bạn kẹt lại, phải quay ra cầu thang.', correct=False)
    cq.slip(t, 'downwind', 3 if t['_live'] else 2, f'Đi tắt băng qua {t["needs"]["near"]} khi có báo động.', 'đi qua khu nguy hiểm', safety=True)
    return dict(message=f'☁️ Lối tắt băng qua {t["needs"]["near"]}, khói khí bay theo gió về phía bạn. Đi ngược gió mới đúng.', correct=False)


def _muster(s, c, d, p):
    t = _task(c, p, ('drill',))
    kit.need(t['route'] is not None, 'Chọn đường đi trước đã.')
    kit.need(t['muster'] is None, 'Đã tới điểm tập trung.')
    st = kit.one_of(p.get('station'), tuple(K.STATIONS), 'Chọn điểm tập trung.')
    if st != t['needs']['station']:
        t['mistakes'] += 1
        cq.slip(t, 'station', 2, 'Tới nhầm điểm tập trung, bảng đếm thiếu một người.', 'nhầm điểm tập trung')
        return dict(message=f'✋ Trưởng xuồng {st}: “Phòng {t["needs"]["room"]} đâu thuộc xuồng này!” Bạn chạy sang xuồng {t["needs"]["station"]}.', correct=False)
    t['muster'] = st
    return dict(message=f'🛶 Tới {K.STATIONS[st]}.')


def _card(s, c, d, p):
    t = _task(c, p, ('drill',))
    kit.need(t['muster'], 'Tới đúng điểm tập trung trước đã.')
    kit.start_work(t)
    if not t['dropped']:
        t['mistakes'] += 1
        cq.slip(t, 'drop', 1, 'Bỏ đi khi chưa để thiết bị đang làm ở trạng thái an toàn.', 'chưa để thiết bị an toàn')
    minutes = 3 + len(cq.slips(t))
    d['stats']['drills'] = min(10 ** 7, d['stats']['drills'] + 1)
    best = d['stats']['best_muster']
    d['stats']['best_muster'] = minutes if not best else min(best, minutes)
    d['today']['muster'] = minutes
    tail = ' Hóa ra là rò khí thật ở mặt bích: đội ứng cứu đã cô lập xong.' if t['_live'] else ' Loa báo: “Đây là buổi diễn tập.”'
    msg = _finish(s, c, d, t, f'💳 Quẹt thẻ, trưởng xuồng đếm đủ người: {minutes} phút.{tail}')
    return dict(message=msg, celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the storm
def _secure_item(s, c, d, p):
    t = _task(c, p, ('secure',))
    _grounded(c, d, t)
    item = kit.one_of(p.get('item'), t['needs']['items'], 'Món này không có trên boong.')
    how = kit.one_of(p.get('how'), ('lash', 'inside', 'check'), 'Chọn: chằng buộc, cất vào trong hay kiểm tra.')
    kit.start_work(t)
    x = K.LOOSE_INDEX[item]
    if how != x['do']:
        t['mistakes'] += 1
        cq.slip(t, 'secure', 1, f'{x["name"]}: xử lý chưa đúng trước bão.', 'chằng buộc chưa đúng')
        return dict(message=f'✋ Chú Toàn: “{x["name"]}: {x["note"]}”', correct=False)
    t['done'][item] = how
    return dict(message=f'{x["emoji"]} {x["name"]}: {x["note"]}')


def _crane(s, c, d, p):
    t = _task(c, p, ('secure',))
    kit.need(not t['crane'], 'Cẩu đã dừng rồi.')
    t['crane'] = True
    return dict(message='🏗️ Báo cẩu trưởng: hạ cần về giá đỡ, khóa, tắt máy. Không nâng hàng tới khi bão qua.')


def _report(s, c, d, p):
    t = _task(c, p, ('secure',))
    _grounded(c, d, t)
    kit.start_work(t)
    left = [K.LOOSE_INDEX[i]['name'].lower() for i in t['needs']['items'] if i not in t['done']]
    notes = []
    if left:
        t['mistakes'] += 1
        cq.slip(t, 'loose', 2, f'Bão tới mà còn {", ".join(left)} chưa xử lý.', 'còn đồ rời trên boong', safety=True)
        notes.append(f'🌀 Đêm đó gió giật: {", ".join(left)} xô lệch, sáng ra phải dọn.')
    if not t['crane']:
        t['mistakes'] += 1
        cq.slip(t, 'crane', 2, 'Bão tới mà cần cẩu chưa hạ, chưa khóa.', 'cẩu chưa dừng', safety=True)
    msg = _finish(s, c, d, t, '📻 Báo phòng điều khiển: boong đã chằng buộc, cẩu dừng, mọi người vào khu ở.')
    return dict(message=' '.join(notes + [msg]), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the handover
def _note(s, c, d, p):
    t = _task(c, p, ('handover',))
    item = kit.one_of(p.get('item'), t['needs']['items'], 'Mục này không có.')
    kit.start_work(t)
    if item in t['picked']:
        t['picked'].remove(item)
        return dict(message='Bỏ khỏi bản bàn giao.')
    t['picked'].append(item)
    return dict(message=f'✍️ Ghi: {K.OPEN_INDEX[item]["text"]}')


def _handover_done(s, c, d, p):
    t = _task(c, p, ('handover',))
    kit.start_work(t)
    left = [K.OPEN_INDEX[i]['text'] for i in t['needs']['items'] if K.OPEN_INDEX[i]['must'] and i not in t['picked']]
    notes = []
    if left:
        t['mistakes'] += 1
        cq.slip(t, 'omit', 2, f'Bàn giao bỏ sót: {left[0]}', 'bàn giao thiếu')
        notes.append(f'📞 Hai hôm sau người ca sau gọi: “Sao không ghi vụ {_lower(left[0][:60])}?”')
    msg = _finish(s, c, d, t, '🚁 Bàn giao xong, bắt tay người ca sau. Trực thăng đưa bạn về bờ, biển xanh lùi dần.')
    return dict(message=' '.join(notes + [msg]), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the shore day: the family's requests
def _shore_task(c, p) -> dict:
    t = _task(c, p, ('shore',))
    kit.need(t['status'] != 'completed', 'Ngày trên bờ đã xong.')
    return t


def _paid(s, c, t) -> str:
    """The hitch allowance reaches the fund on the first move of the shore day."""
    if t['paid']:
        return ''
    t['paid'] = True
    kit.money(s, c, t['needs']['allowance'], 'Phụ cấp đi biển đợt này', t['id'], 'salary')
    kit.start_work(t)
    return f'💵 Nhận {t["needs"]["allowance"]} xu phụ cấp đi biển. '


def _ask(s, c, d, p):
    t = _shore_task(c, p)
    rid = kit.one_of(p.get('req'), t['needs']['reqs'], 'Không có lời nhờ này.')
    kit.need(rid not in t['asked'], 'Đã hỏi rõ rồi.')
    head = _paid(s, c, t)
    t['asked'].append(rid)
    r = K.REQUEST_INDEX[rid]
    return dict(message=f'{head}🔎 Hỏi rõ {r["who"]}: {r["fact"]}')


def _love(s, c, d, p):
    t = _shore_task(c, p)
    kit.need(not t['called'], 'Đã gọi rồi.')
    head = _paid(s, c, t)
    t['called'] = True
    c['xp'] += 3
    return dict(message=f'{head}📹 Cả nhà quây quần trước màn hình: Má hỏi ăn chưa, Ba khoe con cá lóc mới câu, bé Vy đọc bài văn “Người thân của em làm dầu khí”.')


def _judge(r: dict, amount: int, words: set, asked: bool, push: int, round_: int, counter: int | None) -> tuple:
    """How a family member takes what you send: (out, good, counter). Pure."""
    kind, need, ask = r['kind'], r['need'], r['ask']
    soft = bool(words & {'explain', 'later', 'love'})
    if counter is not None:
        need = max(need, counter) if kind in ('need', 'gift') else need
    if kind == 'scam':
        return ('scammed', False, None) if amount > 0 else ('refused', True, None)
    if kind == 'need':
        if amount >= need:
            return 'happy', True, None
        if round_ == 0 and push >= 1:
            return 'counter', None, need
        if amount * 3 >= need * 2 and soft:
            return 'ok', None, None
        return 'short', False, None
    if kind == 'want':
        if amount >= ask:
            return 'spoiled', None, None
        if amount == 0 and not soft:
            return 'sulk', None, None
        if round_ == 0 and push == 2 and amount < max(need, 1) and not asked:
            return 'counter', None, max(need, ask // 2)
        return 'ok', True, None
    if kind == 'gift':
        if need <= amount <= need * 2:
            return 'happy', True, None
        if amount > need * 2:
            return 'lavish', None, None
        if round_ == 0 and push >= 1:
            return 'counter', None, need
        return 'sulk', None, None
    # loan
    if amount == 0:
        return ('ok', True, None) if soft or asked else ('sulk', None, None)
    if amount <= need and asked:
        return 'ok', True, None
    if amount > need:
        return 'risky', False, None
    return 'ok', None, None


OUT_LINE = {
    'happy': '{who} mừng ra mặt: “Con lo chu đáo quá.”', 'ok': '{who} gật đầu: “Ừ, con tính vậy cũng phải.”',
    'short': '{who} im một lúc: “Thôi được… má xoay thêm.” Giọng buồn hẳn.', 'spoiled': '{who} reo lên. Ví bạn mỏng hẳn đi.',
    'sulk': '{who} hờn: “Hỏi có chút mà cũng không.” Rồi cũng qua.', 'lavish': '{who} mừng lắm, cả họ biết bạn mừng to. Lần sau ai cũng nhờ.',
    'risky': '{who} cầm tiền, hứa “tháng sau trả liền”. Má nhìn bạn, thở dài.', 'scammed': '{who} cảm ơn rối rít. Một tuần sau số điện thoại không liên lạc được nữa.',
    'refused': '{who} bĩu môi rồi thôi. Bạn giữ được tiền, và giữ được cả nhà khỏi một vụ lừa.',
    'counter': '{who}: “Có nhiêu đó hả? Thêm cho đủ {c} xu đi mà.”',
}


def _send(s, c, d, p):
    t = _shore_task(c, p)
    rid = kit.one_of(p.get('req'), t['needs']['reqs'], 'Không có lời nhờ này.')
    r = K.REQUEST_INDEX[rid]
    prev = t['sent'].get(rid)
    kit.need(prev is None or prev['out'] == 'counter', 'Chuyện này đã xong.')
    amount = kit.integer(p.get('amount', 0), 0, r['ask'] * 2)
    words = p.get('words') or []
    kit.need(isinstance(words, list) and len(words) <= 2 and len(set(words)) == len(words) and all(w in K.SHORE_WORDS for w in words),
             'Chọn tối đa hai ý để nói.')
    head = _paid(s, c, t)
    if amount:
        kit.need(c['money'] >= amount, f'Quỹ chỉ còn {c["money"]} xu, không đủ gửi {amount} xu.')
        kit.money(s, c, -amount, f'Gửi về nhà: {r["who"]}'[:120], t['id'], 'event_cost')
    round_ = 1 if prev else 0
    counter = prev['counter'] if prev else None
    total = amount + (prev['amount'] if prev else 0)
    out, good, cnt = _judge(r, total, set(words), rid in t['asked'], t['_push'][rid], round_, counter)
    t['sent'][rid] = dict(amount=total, words=list(words), out=out, good=good, counter=cnt if out == 'counter' else None)
    d['stats']['sent'] = min(10 ** 7, d['stats']['sent'] + amount)
    d['today']['sent'] += amount
    if out == 'scammed':
        t['mistakes'] += 1
        cq.slip(t, 'scam', 2, f'Gửi {amount} xu cho “{_lower(r["line"][:60])}”: mất trắng.', 'gửi tiền cho trò lừa')
        d['stats']['scammed'] = min(10 ** 7, d['stats']['scammed'] + amount)
        d['today']['scams'] += 1
    elif out == 'refused':
        d['stats']['scams_refused'] = min(10 ** 7, d['stats']['scams_refused'] + 1)
        c['xp'] += 6 if rid in t['asked'] else 3
    elif out in ('short', 'risky'):
        t['mistakes'] += 1
        cq.slip(t, out, 1, {'short': f'{r["who"]} thiếu tiền cho việc cần: {_lower(r["line"][:50])}.', 'risky': f'Cho {r["who"]} mượn quá sức, khó đòi.'}[out],
                'chưa lo đủ việc cần' if out == 'short' else 'cho mượn quá sức')
    line = OUT_LINE[out].format(who=r['who'], c=cnt or 0)
    sent = f'📲 Gửi {amount} xu. ' if amount else '📲 Không gửi. '
    said = ' '.join(f'“{K.SHORE_WORDS[w]}.”' for w in words)
    msg = f'{head}{sent}{said} {line}'.strip()
    if out == 'counter':
        return dict(message=msg)
    return dict(message=msg, correct=good is not False, celebrate=good is True)


def _shore_done(s, c, d, p):
    t = _shore_task(c, p)
    left = [rid for rid in t['needs']['reqs'] if rid not in t['sent'] or t['sent'][rid]['out'] == 'counter']
    kit.need(not left, f'Còn lời nhờ chưa trả lời: {K.REQUEST_INDEX[left[0]]["who"]}.' if left else '')
    head = _paid(s, c, t)
    msg = _finish(s, c, d, t, '🌙 Tối trên bờ: ngủ một giấc dài trong tiếng ếch nhái, không còi báo động nào.')
    return dict(message=head + msg, celebrate=not cq.slips(t))


ACTIONS = {
    'dk_bag': _bag, 'dk_gear': _gear, 'dk_quiz': _quiz, 'dk_wait': _wait, 'dk_board': _board,
    'dk_tcard': _tcard, 'dk_station': _station, 'dk_tone': _tone, 'dk_settle': _settle,
    'dk_ppe': _ppe, 'dk_bump': _bump, 'dk_swap': _swap, 'dk_hazard': _hazard, 'dk_remind': _remind, 'dk_talk': _talk,
    'dk_permit': _permit, 'dk_xref': _xref, 'dk_iso': _iso, 'dk_bleed': _bleed, 'dk_verify': _verify, 'dk_gas': _gas, 'dk_watch': _watch,
    'dk_stop': _stop, 'dk_nearmiss': _nearmiss, 'dk_work': _work, 'dk_restore': _restore, 'dk_close': _close,
    'dk_read': _read, 'dk_call': _call, 'dk_look': _look, 'dk_leak': _leak, 'dk_log': _logbook,
    'dk_alarm': _alarm, 'dk_drop': _drop, 'dk_phone': _phone, 'dk_route': _route, 'dk_station2': _muster, 'dk_card': _card,
    'dk_secure': _secure_item, 'dk_crane': _crane, 'dk_report': _report,
    'dk_note': _note, 'dk_handover': _handover_done,
    'dk_ask': _ask, 'dk_love': _love, 'dk_send': _send, 'dk_done': _shore_done,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    d['today'] = _fresh_today(c['day'])
    ph = _phase_kind(c)
    odd = d['odd']
    if ph in ('home', 'wait'):
        odd['marks']['ashore'] = c['day']
    else:
        odd['marks'].pop('ashore', None)
    ao.start(c, ID, odd)
    kit.desk_start(s, c, ID, d['desk'], K.DESK, ph, c['life'].get('mode') == 'festival')
    ao.tick(s, c, ID, odd, K.ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], K.DESK)
    odd_note = ao.close(s, c, d['odd'], K.ODD)
    x = d['today']
    ph = phase(c['day'])
    lines = [f'🛢️ {hitch_label(c["day"])}: xong {x["jobs"]} việc.']
    if x['stops']:
        lines.append(f'✋ Dừng việc {x["stops"]} lần' + (f', {x["good_stops"]} lần chặn đúng mối nguy.' if x['good_stops'] else '. Dừng để hỏi không bao giờ sai.'))
    if x['nearmiss']:
        lines.append(f'📝 Gửi {x["nearmiss"]} báo cáo suýt sự cố.')
    if x['muster']:
        lines.append(f'🛶 Về điểm tập trung trong {x["muster"]} phút.')
    if x['sent']:
        lines.append(f'📲 Gửi về nhà {x["sent"]} xu.')
    if x['scams']:
        lines.append('🕳️ Có một khoản gửi vào trò lừa. Lần sau hỏi rõ trước khi gửi.')
    if desk_note:
        lines.append(desk_note)
    if odd_note:
        lines.append(odd_note)
    lines += ao.day_lines(c, d['odd'])
    nxt = phase(c['day'] + 1)['kind']
    note = {'out': 'Mai bay ra giàn: soạn túi tối nay, đừng mang bật lửa.', 'rig': 'Mai ca 6 giờ sáng: ngủ sớm, Gấu ngáy thì xin nút tai.',
            'home': 'Mai bàn giao rồi về bờ.', 'stay': 'Bão: mai có thể phải ở lại thêm.', 'wait': 'Bão: chuyến bay mai có thể hủy.'}[nxt]
    lines.append({'home': '🏠 Tối nay ngủ ở nhà, cơm Má nấu.', 'wait': '🏠 Tối nay ngủ ở nhà, chờ bão qua.'}.get(ph['kind'], '🌊 Tối nay ngủ trên giàn, sóng vỗ chân giàn.'))
    return dict(lines=lines, note=note, jobs=x['jobs'], stops=x['stops'], nearmiss=x['nearmiss'], sent=x['sent'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    codes = {x['code'] for x in cq.slips(t)}
    k = t['kind']
    if k == 'shore':
        sent = t.get('sent') or {}
        outs = {v['out'] for v in sent.values()}
        needs = 2 if 'short' in outs else 5
        scam = 1 if 'scammed' in outs else 5
        total = sum(v['amount'] for v in sent.values())
        allow = t['needs']['allowance']
        save = 5 if total <= allow * 3 // 4 else 4 if total <= allow else 3 if total <= allow * 3 // 2 else 2
        care = 5 if t.get('called') else 3
        return dict(criteria=[dict(key='needs', label='Lo việc cần', score=needs, note='đủ thuốc, đủ học phí' if needs == 5 else 'còn thiếu việc cần'),
                              dict(key='scam', label='Không bị lừa', score=scam, note='hỏi rõ trước khi gửi' if scam == 5 else 'gửi vào trò lừa'),
                              dict(key='save', label='Để dành', score=save, note=f'gửi {total}/{allow} xu phụ cấp'),
                              dict(key='care', label='Hỏi han cả nhà', score=care, note='gọi video cả nhà' if care == 5 else 'chưa gọi về')])
    safe_codes = {'banned', 'nobump', 'badmon', 'iso', 'bleed', 'prove', 'nogas', 'watch', 'tighten', 'lift', 'downwind', 'loose', 'crane'} | {c_ for c_ in codes if c_.startswith('trap_')}
    safe = 1 if codes & safe_codes else 3 if codes & {'gear', 'pob', 'muster', 'station', 'phone', 'xref', 'ppe'} else 5
    proc = max(1, 5 - len(codes - safe_codes))
    p = min(100, t.get('patience', 100) + STOP_DELAY * len(t.get('stops') or []))   # a stop for safety never counts as slow
    pace = 5 if p >= 80 else 4 if p >= 60 else 3
    crit = [dict(key='safety', label='An toàn trên hết', score=safe, note='không bỏ bước an toàn nào' if safe == 5 else 'có bước an toàn bị bỏ'),
            dict(key='procedure', label='Đúng quy trình', score=proc, note='đủ từng bước' if proc == 5 else 'sót bước, sai thứ tự')]
    if k == 'ptw':
        stops = t.get('stops') or []
        crit.append(dict(key='stop', label='Dám dừng việc', score=5 if (t.get('fixed') and stops) or not t.get('_trap') else 2,
                         note='dừng đúng lúc' if t.get('fixed') and stops else 'không có gì phải dừng' if not t.get('_trap') else 'làm tiếp khi có dấu hiệu nguy hiểm'))
    crit.append(dict(key='pace', label='Gọn gàng', score=pace, note='không để ai chờ lâu' if pace == 5 else 'mọi người chờ hơi lâu (dừng an toàn không bị tính)'))
    return dict(criteria=crit)


VOICES = {
    HSE: {5: ['Làm đúng từng bước, chị không phải nhắc gì.', 'Việc này chị ký đóng giấy phép mà yên tâm.'], 4: ['Ổn, còn một chỗ chị ghi lại cho lần sau.'],
          3: ['Chị phải nhắc khá nhiều ở việc này.'], 1: ['Việc này chị phải ghi vào sổ an toàn. Mai mình ngồi lại nhé.']},
    TOAN: {5: ['Gọn, chắc, đúng bài. Chú yên tâm.', 'Làm vậy là được việc của giàn rồi con.'], 4: ['Được, còn một chút chưa chắc tay.'],
           3: ['Chú phải đứng cạnh nhắc nhiều quá.'], 1: ['Không được con. Trên giàn không có chỗ cho làm ẩu.']},
    BAO: {5: ['Đúng tiến độ mà vẫn đủ bước, anh chịu.', 'Ok em, xong gọn.'], 4: ['Tạm được, hơi chậm xíu.'], 3: ['Chưa ổn lắm em.'],
          1: ['Việc này để lại rắc rối cho cả tổ.']},
    MA: {5: ['Con lo cho nhà chu đáo, má thương.', 'Má yên tâm rồi, con giữ sức nghe.'], 4: ['Được con, có chút má còn lo.'],
         3: ['Má không trách, mà má còn lo.'], 1: ['Má buồn lắm con.']},
}


def review_text(c: dict, t: dict, persona: str, stars: int, criteria: list, seed: int) -> str:
    i = _npc_index(t)
    return air.review(t, stars, criteria, seed, VOICES.get(i, VOICES[TOAN]), None)


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n, k = t['needs'], t['kind']
    if k == 'heli':
        if n['cancel']:
            return 'Phiếu bay: áp thấp gần bờ, chuyến có thể hủy. Làm thủ tục, nghe thông báo.'
        return f'Phiếu bay: túi mềm tối đa {n["limit"]} kg, không đồ cấm; mặc đủ đồ cứu sinh; xem video thoát hiểm.' + (f' Chuyến hoãn {n["delay"]} phút.' if n['delay'] else '')
    if k == 'induct':
        return f'Phòng {n["room"]} · bạn cùng phòng Tuấn “Gấu”. Biển cửa phòng ghi xuồng cứu sinh của bạn.'
    if k == 'toolbox':
        return 'Họp an toàn đầu ca: đồ bảo hộ, thử máy đo khí, mối nguy của việc hôm nay, quyền dừng việc.'
    if k == 'ptw':
        j = K.JOB_INDEX[n['job']]
        return f'Phiếu việc {j["tag"]}: {j["work"]}'
    if k == 'round':
        return 'Tuyến tuần: ' + ', '.join(g['tag'] for g in n['gauges']) + ' · ' + ', '.join(K.AREAS[a][1].lower() for a in n['areas']) + '.'
    if k == 'drill':
        return f'Gió từ hướng {n["wind"]}. Phòng {n["room"]}.'
    if k == 'secure':
        return 'Danh sách chằng buộc: ' + ', '.join(K.LOOSE_INDEX[i]['name'].lower() for i in n['items']) + '.'
    if k == 'handover':
        return 'Bản bàn giao cho người ca sau: ghi mọi việc còn dở, kể cả chuyện của mình.'
    return f'Phụ cấp đi biển {n["allowance"]} xu. ' + ' '.join(f'{K.REQUEST_INDEX[r]["who"]}: “{K.REQUEST_INDEX[r]["line"]}”' for r in n['reqs'])


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    v['hitch'] = hitch_label(t['day'])
    if not v['known']:
        v['needs'] = None
        return v
    k, n = t['kind'], t['needs']
    if k == 'heli':
        v['bag_kg'] = bag_kg(t)
        v['quizq'] = dict(id=n['quiz'], text=K.QUIZ_INDEX[n['quiz']]['text'], options=[dict(id=a, label=b) for a, b in K.QUIZ_INDEX[n['quiz']]['options']])
    elif k == 'ptw':
        j = K.JOB_INDEX[n['job']]
        v['job'] = dict(id=j['id'], title=j['title'], tag=j['tag'], work=j['work'], bleed=j['bleed'], prove=j['prove'], watch=j['watch'],
                        points=[dict(id=a, name=b, kind=c_) for a, b, c_ in j['points']])
        v['can_report'] = bool(t['fixed']) or bool(cq.slips(t))
    elif k == 'round':
        v['gauges'] = [dict(_gauge(t, g['tag']), verdict=None) for g in n['gauges']]
        v['can_report'] = bool(cq.slips(t))
        v['leak_seen'] = K.LEAKS[t['_leak']['kind']] if t['found'] and t['_leak'] else None
    elif k == 'shore':
        v['reqs'] = [dict(id=r, who=K.REQUEST_INDEX[r]['who'], emoji=K.REQUEST_INDEX[r]['emoji'], line=K.REQUEST_INDEX[r]['line'], ask=K.REQUEST_INDEX[r]['ask'],
                          fact=K.REQUEST_INDEX[r]['fact'] if r in t['asked'] else None, done=t['sent'].get(r)) for r in n['reqs']]
    elif k == 'drill':
        v['can_report'] = bool(cq.slips(t))
    return v


def public_data(c: dict) -> dict:
    d = tree_copy(c['ext']['data'])
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    ph = phase(c['day'])
    b = bunk(ph['hitch'])
    nxt = next((k for k in range(1, 9) if phase(c['day'] + k)['kind'] == 'home'), None)
    return dict(intro=d['intro'], stats=d['stats'], today=d['today'], log=d['log'][-6:], regulars={k: dict(v) for k, v in d['regulars'].items()},
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                hitch=dict(kind=ph['kind'], n=ph['hitch'], step=ph['step'], label=hitch_label(c['day']), room=b['room'], home_in=nxt,
                           ashore=ph['kind'] in ('home', 'wait')),
                desk=kit.desk_public(d['desk'], K.DESK, ID), odd=ao.public(c, ao.ensure(d), K.ODD, ID, CFG))


def content() -> dict:
    return dict(intro=K.INTRO, company=K.COMPANY, rig=K.RIG, field=K.FIELD, heliport=K.HELIPORT,
                bag=[dict(id=x['id'], emoji=x['emoji'], name=x['name'], kg=x['kg']) for x in K.BAG], gear=K.GEAR,
                alarms=K.ALARMS, stations=K.STATIONS, ppe=K.PPE, hazards={k: dict(emoji=v[0], name=v[1]) for k, v in K.HAZARDS.items()},
                permits={k: dict(emoji=v[0], name=v[1], note=v[2]) for k, v in K.PERMITS.items()}, stop_reasons=K.STOP_REASONS,
                gas_limit=K.GAS_LIMIT, watch={k: dict(emoji=v[0], name=v[1]) for k, v in K.WATCH.items()}, areas={k: dict(emoji=v[0], name=v[1]) for k, v in K.AREAS.items()},
                loose={x['id']: dict(emoji=x['emoji'], name=x['name']) for x in K.LOOSE}, open_items={x['id']: dict(emoji=x['emoji'], text=x['text']) for x in K.OPEN_ITEMS},
                shore_words=K.SHORE_WORDS, bonus=BONUS, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    if (c['ext']['data'].get('odd') or {}).get('ev'):
        return 'Có người đang chờ bạn trả lời: chọn giọng, chọn ý, cần thì báo chú Toàn hoặc phòng an toàn.'
    return {
        'heli': 'Bỏ đồ cấm và đồ nặng khỏi túi → mặc đủ đồ cứu sinh → trả lời câu thoát hiểm → hoãn thì chờ → lên trực thăng.',
        'induct': 'Gắn thẻ bảng đếm người → xem biển cửa phòng chọn xuồng → nhớ ba tiếng còi → cất túi.',
        'toolbox': 'Đủ đồ bảo hộ → thử máy đo khí (hỏng thì đổi) → chọn mối nguy của việc hôm nay → nhắc quyền dừng việc → kết thúc họp.',
        'ptw': 'Đúng giấy phép → đối chiếu bảng giấy phép → khóa từng điểm → xả → kiểm về không → đo khí → người canh nếu cần → làm → trả thiết bị → trả giấy phép. Thấy lạ: ✋ Dừng việc.',
        'round': 'Đọc từng đồng hồ so với giới hạn → báo số ngoài giới hạn → đi từng khu nghe nhìn ngửi → rò thì báo, không tự siết → ghi sổ.',
        'drill': 'Nhận ra tiếng còi → để thiết bị an toàn → không quay lại lấy đồ → đi ngược gió, không thang máy → đúng xuồng → quẹt thẻ.',
        'secure': 'Chằng buộc, cất vào trong hay kiểm tra từng món → dừng cẩu → báo phòng điều khiển.',
        'handover': 'Ghi mọi việc còn dở cho ca sau, kể cả suýt sự cố của mình → bàn giao.',
        'shore': 'Hỏi rõ từng lời nhờ → gửi cho việc cần, nói khéo với việc muốn, không gửi cho trò lừa → gọi video cả nhà → xong ngày.',
    }.get(t.get('kind'), 'Nhận phiếu việc rồi làm từng bước.')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'roust':
        return 'Đã gom dây chằng, kiểm khóa góc container trên boong hàng.'
    if e.get('role') == 'ccr':
        return 'Đã trực màn hình phòng điều khiển, ghi số đồng hồ vào sổ ca.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu việc trên giàn sai.')


def _vlist(v, allowed, n=20) -> None:
    kit.need(isinstance(v, list) and len(v) <= n and len(set(v)) == len(v) and all(x in allowed for x in v), 'Dữ liệu việc trên giàn sai.')


def _vtext_dict(v, keys) -> None:
    kit.need(isinstance(v, dict) and set(v) <= set(keys), 'Dữ liệu việc trên giàn sai.')
    for x in v.values():
        kit.text(x, 300)


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN and t.get('kind') in KINDS, 'Việc trên giàn không hợp lệ.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện trên giàn sai.')
    n, k = t['needs'], t['kind']
    if k == 'heli':
        _vlist(t.get('bag_out'), n['bag'])
        _vlist(t.get('gear'), K.GEAR_IDS)
        q = K.QUIZ_INDEX[n['quiz']]
        kit.need(t.get('quiz') in (None, *[o[0] for o in q['options']]), 'Câu trả lời sai.')
        _vbool(t.get('waited'))
    elif k == 'induct':
        _vbool(t.get('tcard'))
        kit.need(t.get('muster') in (None, *K.STATIONS), 'Điểm tập trung sai.')
        m = t.get('matched')
        kit.need(isinstance(m, dict) and set(m) <= set(K.ALARM_IDS) and all(m[x] == x for x in m), 'Tiếng còi sai.')
    elif k == 'toolbox':
        _vlist(t.get('ppe'), K.PPE_IDS)
        kit.need(t.get('bumped') in (None, 'pass', 'fail'), 'Thử máy đo sai.')
        _vbool(t.get('swapped'))
        _vbool(t.get('remind'))
        _vlist(t.get('picked'), n['hazards'])
    elif k == 'ptw':
        j = K.JOB_INDEX[n['job']]
        kit.need(t.get('permit') in (None, j['permit']), 'Giấy phép sai.')
        _vlist(t.get('locks'), [x[0] for x in j['points']])
        for f in ('xref', 'bled', 'proven', 'gas', 'watch', 'worked', 'restored', 'fixed', 'nearmiss'):
            _vbool(t.get(f))
        kit.need(not t['bled'] or bool(j['bleed']), 'Xả áp sai.')
        kit.need(isinstance(t.get('stops'), list) and len(t['stops']) <= 6 and all(x in K.STOP_REASONS for x in t['stops']), 'Dừng việc sai.')
        _vtext_dict(t.get('read'), ('verify', 'gas', 'xref'))
    elif k == 'round':
        tags = [g['tag'] for g in n['gauges']]
        r = t.get('reads')
        kit.need(isinstance(r, dict) and set(r) <= set(tags) and all(x in ('ok', 'high', 'low') for x in r.values()), 'Sổ tuần sai.')
        _vlist(t.get('called'), tags)
        _vlist(t.get('looked'), n['areas'])
        _vbool(t.get('found'))
        kit.need(t.get('leak') in (None, 'report', 'tighten'), 'Xử lý rò sai.')
        kit.need(not t['found'] or t['_leak'] is not None, 'Chỗ rò sai.')
        _stops_ok(t)
    elif k == 'drill':
        kit.need(t.get('alarm') in (None, *K.ALARM_IDS) and t.get('route') in (None, *n['routes']) and t.get('muster') in (None, *K.STATIONS), 'Diễn tập sai.')
        for f in ('dropped', 'phone', 'carded'):
            _vbool(t.get(f))
        _stops_ok(t)
    elif k == 'secure':
        dn = t.get('done')
        kit.need(isinstance(dn, dict) and set(dn) <= set(n['items']) and all(dn[i] == K.LOOSE_INDEX[i]['do'] for i in dn), 'Chằng buộc sai.')
        _vbool(t.get('crane'))
        _stops_ok(t)
    elif k == 'handover':
        _vlist(t.get('picked'), n['items'])
    if k == 'toolbox':
        _stops_ok(t)
    elif k == 'shore':
        _vbool(t.get('paid'))
        _vbool(t.get('called'))
        _vlist(t.get('asked'), n['reqs'])
        sent = t.get('sent')
        kit.need(isinstance(sent, dict) and set(sent) <= set(n['reqs']), 'Tiền gửi sai.')
        for rid, x in sent.items():
            kit.need(isinstance(x, dict) and set(x) == {'amount', 'words', 'out', 'good', 'counter'} and x['out'] in OUT_LINE
                     and x['good'] in (True, False, None), 'Tiền gửi sai.')
            kit.integer(x['amount'], 0, 10 ** 4)
            _vlist(x['words'], K.SHORE_WORDS, 2)
            if x['counter'] is not None:
                kit.integer(x['counter'], 0, 10 ** 4)
    if 'nearmiss' in t and k != 'ptw':
        _vbool(t['nearmiss'])


def _stops_ok(t: dict) -> None:
    if 'stops' in t:
        kit.need(isinstance(t['stops'], list) and len(t['stops']) <= 6 and all(x in K.STOP_REASONS for x in t['stops']), 'Dừng việc sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    for k in ('stats', 'today'):
        kit.need(isinstance(d[k], dict) and set(d[k]) == set(initial()[k] if k == 'stats' else _fresh_today(0)), 'Số liệu trên giàn sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.need(isinstance(d['log'], list) and len(d['log']) <= LOG_MAX, 'Nhật ký giàn sai.')
    for x in d['log']:
        kit.need(isinstance(x, dict) and set(x) == {'day', 'kind', 'title', 'ok'} and x['kind'] in KINDS, 'Nhật ký giàn sai.')
        kit.integer(x['day'], 0, 10 ** 7)
        kit.text(x['title'], 80)
        _vbool(x['ok'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in K.REG_STORY}, 'Sổ người quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người quen sai.')
        kit.integer(v['visits'], 0, 999)
    kit.desk_validate(d['desk'], K.DESK)
    ao.validate(d['odd'], K.ODD)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='dk_', category='outdoor',
    meta=dict(short='Thợ dầu khí', place='Giàn Hải Âu · Dầu khí Sóng Bạc', tagline='An toàn trước, tiến độ sau, nhà luôn chờ.', icon='flame',
              color='#1f5f7a', light='#e2f0f5', weather='Biển êm, gió nhẹ', work='Ca trên giàn', station='Boong chính',
              greeting='Đợt đi biển 14 ngày: bay trực thăng ra giàn, làm ca 12 tiếng, thấy không an toàn thì dừng việc, rồi về bờ với gia đình.',
              caption='Mỗi ổ khóa một cái tên, mỗi tiếng còi một mạng người', map_label='22 · CẢNG TRỰC THĂNG MŨI SAO'),
    people=PEOPLE,
    staff=K.STAFF,
    roles=K.ROLES,
    tip=0,
    open_line='Vào ca. Chú Toàn đang chờ ở boong chính.',
    more_line='Chú Toàn giao thêm một việc.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('🛢️', 'Ca trên giàn', [('Ổ khóa đỏ', 'Mỗi người một khóa'), ('Đồng hồ về 0', 'Mới được mở'), ('Còi ngắt quãng', 'Về điểm tập trung'),
                                     ('Ngược gió', 'Đường thoát khi rò khí')],
              ['Soạn túi, mặc đồ cứu sinh', 'Giấy phép, cô lập, đo khí', 'Đi tuần, đọc đồng hồ', 'Báo động: đúng xuồng, đúng đường']),
    stories=K.STORIES,
    review_asides=K.REVIEW_ASIDES,
    situations=K.SITUATIONS,
    guide='Đợt 14 ngày: ngày bay (túi, đồ cứu sinh, thoát hiểm) → nhận giàn (thẻ, xuồng, tiếng còi) → mỗi ca: họp an toàn, bảo dưỡng có giấy phép '
          '(khóa đủ, xả, kiểm về không, đo khí), đi tuần, báo động → ngày về: bàn giao thật, rồi lo tiền nhà mà không bị lừa. Thấy lạ: ✋ Dừng việc.',
    employment=dict(
        postings=[
            dict(id='dk-tech', org='Dầu khí Sóng Bạc · giàn Hải Âu', kind='company', title='Kỹ thuật viên vận hành ngoài khơi',
                 salary=(110, 140), probation_days=3, wants=['careful', 'calm', 'teamwork'],
                 perks=['Lương đi biển cao', 'Đợt 14 ngày trên giàn, 14 ngày trên bờ', 'Có người kèm cặp'],
                 culture='Giàn nhỏ tám mươi người giữa biển. Ai cũng có quyền dừng việc; báo suýt sự cố được cảm ơn, không bị phạt.',
                 questions=['dk_stop', 'dk_lock', 'dk_family', 'mistake'], reference=True),
            dict(id='dk-shore', org='Căn cứ dịch vụ Sóng Bạc · cảng Mũi Sao', kind='branch', title='Thợ vận hành tập sự trên bờ',
                 salary=(80, 100), probation_days=2, wants=['learning', 'careful'],
                 perks=['Tối về nhà', 'Học trên giàn mô phỏng', 'Lương thấp hơn đi biển'],
                 culture='Xưởng và giàn mô phỏng ở cảng, nơi người mới học khóa van, đo khí trước khi ra biển.',
                 questions=['dk_lock'], reference=False),
        ],
        questions={
            'dk_stop': dict(text='Giám sát giục bỏ bước đo khí cho kịp tàu dịch vụ. Bạn làm gì?', options=[
                dict(id='stop', label='Dùng quyền dừng việc: đo khí xong mới làm, báo giờ xong cho giám sát', score=3, note='Chị Hạnh gật đầu: đúng người trong nghề.'),
                dict(id='quick', label='Đo nhanh cho có rồi làm', score=1, note='Đo cho có là chưa đo.'),
                dict(id='skip', label='Nghe giám sát cho kịp tàu', score=0, note='Tiến độ không bao giờ đáng một mạng người.')]),
            'dk_lock': dict(text='Hai người cùng sửa một cái bơm. Khóa cầu dao thế nào?', options=[
                dict(id='each', label='Mỗi người treo một ổ khóa của mình, chìa ai nấy giữ', score=3, note='Cầu dao chỉ mở khi cả hai cùng tháo.'),
                dict(id='one', label='Một người khóa, người kia làm cùng', score=0, note='Người giữ chìa đi ăn trưa, người kia còn trong máy.'),
                dict(id='tag', label='Chỉ treo thẻ, không cần khóa', score=1, note='Thẻ nhắc, khóa mới giữ.')]),
            'dk_family': dict(text='Đi biển 14 ngày, nhà ở xa. Bạn giữ liên lạc với gia đình thế nào?', options=[
                dict(id='plan', label='Hẹn giờ gọi cố định khi hết ca, kể cho nhà nghe lịch đợt đi', score=3, note='Gia đình yên tâm, ca làm không bị phân tâm.'),
                dict(id='anytime', label='Ai gọi lúc nào cũng nghe, kể cả trong ca', score=0, note='Trong khu công nghệ không cầm điện thoại.'),
                dict(id='none', label='Về bờ rồi kể một thể', score=1, note='Nhà lo lắng suốt 14 ngày.')]),
        }),
)
