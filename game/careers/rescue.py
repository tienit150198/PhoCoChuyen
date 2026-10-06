"""Nhân viên trực tổng đài cứu hộ: a day shift on the hotline of Tổng đài Cứu hộ phường Mây (plugin career).

The player is a newly hired dispatcher (employment: CV and interview; the "Chứng chỉ Tiếp nhận cuộc gọi khẩn cấp"
raises the hire chance) under chị Thảo, the shift lead. One task is one piece of the shift:

* ``shift`` (slot 0): take over the board. Check each unit on the radio (the handover says which one is out of
  service today) and mark the one that is down before signing. A unit left unmarked costs minutes later;
* ``call``: a call comes in. Pick up, ask the script (where, what, how many, what danger, a number to call back),
  find the place when the caller cannot say it (a landmark, a location link, a passer-by), calm a caller who panics
  (a tactic that works on this caller, hidden), check a doubtful call (listen, ask for details, call back) before
  deciding, then either SEND (a priority on the "Bảng ưu tiên Mây" and the teams) or REDIRECT (where a call with
  nobody to send belongs, in a tone of your choosing), read out safe instructions while help comes, and close the
  call or stay on the line until the team arrives. The callers decide from hidden traits: how much they panic,
  which calming works, how they take a refusal, and, for a doubtful call, whether it is real at all;
* ``queue``: rain season, several lines ringing at once: listen to each, give each a priority, answer in order.

The board: a unit sent is away for the next call; one sent for nothing (a prank, a cat, a VIP) is away when a real
call needs it. Around the tasks: the awkward people of the line (air_odd engine, rescue_content.ODD): flirting
callers, envelopes, a DJ wanting names, a boss sharpening the KPI, colleagues cutting corners, family wanting a
favour. Giving in is never rewarded. Desk surprises and real-life situations as in every career. At the end of the
shift the player may write the log book from what really happened (lines that did not happen are ghi khống).

Nothing here is medical advice: no medicine and no amount is ever given. Mistakes go through consequences.slip;
money only through the engine (the salary at day close, a small bonus per call). Everything random comes from
(day, slot): make_task is pure.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import air_odd as ao
from . import street_folk as folk
from .. import consequences as cq
from . import rescue_content as RC
from .rescue_content import PEOPLE, CALLS, QUESTIONS, Q_IDS, FIND, VERIFY, CALM, UNITS, UNIT_IDS, PRIO, PRIO_ORDER, REDIRECT, TONES, INSTR, BAD, HARM, LINES

ID = 'rescue'
GEN = 1
BONUS = 10            # xu per call handled by the book (a performance bonus: the salary is the pay)
LEARN = 3             # chị Thảo listens in on the first three calls
FACTS_MAX = 14
KINDS = ('shift', 'call', 'queue')
STAGES = ('open', 'decided', 'done')
SEND_PRIO = ('p1', 'p2', 'p3')
AWAY = 2              # a unit sent is away for this call and the next one
SECS = dict(ask=12, find=15, calm=10, verify=15, send=10, redirect=10, tell=8, panic=10, close=5)
MODS = RC.MODS
MOD = {m['id']: m for m in MODS}
THAO, BINH, VY, BA, KHAI, LONG, HANH, NA = range(8)

# The words of the encounters (air_odd): who to bring in, the office, what a demotion or a stand-down is called here.
CFG = dict(crew='🎧 Gọi chị Thảo', company='🏢 Báo trung tâm', union='Nhờ công đoàn', office='Phòng Điều phối',
           demoted='nhân viên tiếp nhận tập sự', title='điều phối viên',
           labels={'charm': dict(duty='Tôi đang trực đường dây khẩn.', rule='Trung tâm không cho trực ban nhận quà, hẹn hò người gọi.',
                                 alt='Cảm ơn, chúc anh chị bình an.')},
           ground_line='⚖️ Phòng Điều phối: tạm đình chỉ trực hết hôm nay, mai lên trình bày.',
           harass_note='🛡️ Báo là đúng: trung tâm có quy trình bảo vệ trực ban.',
           demote_line='⚖️ Hội đồng kỷ luật: hạ xuống {demoted}, tạm đình chỉ trực hôm nay, không có thưởng tới khi hồ sơ sạch lại.',
           tired_line='😮‍💨 Mệt rồi: thưởng cuộc gọi chỉ còn một nửa. Xin nghỉ bù ở phòng trực.',
           rest_ok=' Ca của bạn đã có người trực thay; bạn thấy nhẹ cả người.',
           levels={'ground': 'Tạm đình chỉ trực'})


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _unit(u: str) -> str:
    e, name = UNITS[u]
    return f'{e} {name}'


def _prio(p: str) -> str:
    e, name, _ = PRIO[p]
    return f'{e} {name}'


def _clock(slot: int) -> str:
    m = min(18 * 60 + 50, 7 * 60 + 6 + max(0, slot) * 53)
    return f'{m // 60:02d}:{m % 60:02d}'


def _pick(r, rows: list):
    """A weighted pick from [(item, weight)] (pure: the caller's random)."""
    total = sum(w for _, w in rows)
    x = r.random() * total
    for k, w in rows:
        x -= w
        if x < 0:
            return k
    return rows[-1][0]


# ================================================================ tasks
def flag_unit(day: int) -> str:
    """The unit out of service today (the handover says so; the shift task asks the player to mark it)."""
    return UNIT_IDS[kit.rng(ID, 'down', day).randrange(len(UNIT_IDS))]


def task_kind(day: int, slot: int) -> str:
    if slot <= 0:
        return 'shift'
    if day == 1:
        return 'call'
    mod = mod_of(day)['id']
    prev = task_kind(day, slot - 1) if slot > 1 else 'shift'
    queue = (3 if mod == 'rain' else 1) if prev != 'queue' and slot >= 2 else 0
    return _pick(kit.rng(ID, 'kind', day, slot), [('call', 7), ('queue', queue)] if queue else [('call', 1)])


DAY1 = ('real', 'junk', 'real', 'doubt', 'junk', 'real', 'doubt')
ROT = {'real': RC.REAL_ROTATION, 'doubt': RC.DOUBT_ROTATION, 'junk': RC.JUNK_ROTATION}
OPENED = {'real': (4, 9), 'doubt': (1, 3), 'junk': (3, 6)}


def call_case(day: int, slot: int) -> str:
    r = kit.rng(ID, 'case', day, slot)
    mod = mod_of(day)['id']
    if day == 1:
        cat = DAY1[(slot - 1) % len(DAY1)]
    else:
        w = {'real': 5, 'doubt': 3, 'junk': 3}
        if mod == 'night':
            w['junk'] += 2
            w['doubt'] += 1
        elif mod == 'rain':
            w['real'] += 2
        elif mod == 'kpi':
            w['junk'] += 1
        cat = _pick(r, list(w.items()))
    rows = ROT[cat]
    first, second = OPENED[cat]
    n = first if day <= 1 else second if day == 2 else len(rows)
    pool = list(rows[:max(1, min(len(rows), n))])
    if day >= 2:
        pool += [k for k in RC.MOD_EXTRA.get(mod, ()) if CALLS[k]['cat'] == cat]
    return pool[r.randrange(len(pool))]


def traits(case: str, day: int, slot: int) -> dict:
    """The caller's hidden traits, rolled once from (day, slot): how much they panic, how they take a no, which
    calming works best, whether their phone opens a location link, and whether a doubtful call is real."""
    x = CALLS[case]
    r = kit.rng(ID, 'traits', day, slot, case)
    panic = r.randint(*x['panic'])
    mood = r.randint(*x['mood'])
    others = [k for k in ('breathe', 'name', 'task') if k != x['soothe']]
    soothe = x['soothe'] if r.random() < .6 else others[r.randrange(len(others))]
    smart = r.random() < .5
    real = r.random() < x['real']
    truth = 'real' if x['cat'] == 'real' else 'fake' if x['cat'] == 'junk' else ('real' if real else 'fake')
    return dict(case=case, truth=truth, panic=panic, mood=mood, soothe=soothe, smart=smart)


def _lines(day: int, slot: int) -> list:
    """Several lines ringing at once: at least one that cannot wait, one that should not be on this line (pure)."""
    r = kit.rng(ID, 'queue', day, slot)
    n = 4 if mod_of(day)['id'] == 'rain' else 3
    urgent = [k for k, v in LINES.items() if v['best'] == 'p1']
    calm = [k for k, v in LINES.items() if v['best'] in ('p3', 'p4')]
    a = urgent[r.randrange(len(urgent))]
    b = calm[r.randrange(len(calm))]
    rest = [k for k in LINES if k not in (a, b)]
    r.shuffle(rest)
    out = [a, b] + rest[:n - 2]
    r.shuffle(out)
    return out


def _common() -> dict:
    return dict(gen=GEN, stage='open', asked=[], tried=[], calm=0, drop=False, secs=0, prio=None, teams=[], to=None, tone=None,
                told=[], stay=None, colors={}, result=None, story=None)


def make_task(day: int, slot: int, serial: int) -> dict:
    kind = task_kind(day, slot)
    c = _common()
    if kind == 'shift':
        units = [dict(id=u, emoji=UNITS[u][0], name=UNITS[u][1]) for u in UNIT_IDS]
        return kit.base_task(ID, day, slot, serial, THAO, 'Nhận ca, rà bảng đội',
                             'Chị Thảo: “Gọi bộ đàm từng đội đi em. Đội nào tạm ngưng thì đánh dấu lên bảng trước khi ký nhận ca, '
                             'kẻo lát gửi tới đội không ai trả lời.”',
                             kind='shift', needs=dict(units=units), _v=dict(down=flag_unit(day)), **c)
    if kind == 'queue':
        q = _lines(day, slot)
        needs = dict(lines=[dict(who=LINES[k]['who'], emoji=LINES[k]['emoji'], text=LINES[k]['text']) for k in q], time=_clock(slot))
        return kit.base_task(ID, day, slot, serial, THAO, f'Nhiều đường dây cùng réo · {_clock(slot)}',
                             f'Chị Thảo: “Mưa to, {len(q)} đường dây réo cùng lúc. Nghe nhanh từng máy, xếp ưu tiên rồi nhấc theo thứ tự.”',
                             kind='queue', needs=needs, _v=dict(lines=q), **c)
    case = call_case(day, slot)
    x = CALLS[case]
    line = 1 + kit.rng(ID, 'line', day, slot).randrange(4)
    return kit.base_task(ID, day, slot, serial, x['npc'], f'Cuộc gọi đến · {_clock(slot)}',
                         f'📞 Đèn đường dây {line} nháy đỏ, chuông réo.', kind='call',
                         needs=dict(line=line, time=_clock(slot)), _v=traits(case, day, slot), **c)


FIXED = ('needs', '_v')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t.get('kind') == 'shift':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the centre's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, calls=0, sent=0, redirected=0, checked=0, told=0, safety=0, secs=0, facts=[], report=None)


def _fresh_board(day: int) -> dict:
    return dict(day=day, down=None, busy={}, tied=[])


def initial() -> dict:
    return dict(v=1, intro=False, regulars={}, today=_fresh_today(0), learn=dict(n=0, caught=[]), board=_fresh_board(0),
                stats=dict(calls=0, sent=0, redirected=0, checked=0, told=0, safety=0, pranks=0, stayed=0, reports=0, honest=0),
                desk=kit.desk_initial(), odd=ao.initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'learn', 'board'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, copy.deepcopy(v))
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    ao.ensure(d)
    return d


def _pressure(c: dict, d: dict) -> int:
    """How hard the centre leans on its dispatchers today: a storm, the KPI day, a dispatcher who snapped at the office."""
    marks = d['odd']['marks']
    return {'rain': 1, 'kpi': 1, 'night': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


def _stat(d: dict, key: str, n: int = 1) -> None:
    if key in d['today']:
        d['today'][key] = min(10 ** 7, d['today'][key] + n)
    d['stats'][key] = min(10 ** 7, d['stats'].get(key, 0) + n)


# ================================================================ the actions
FREE = ('cu_intro', 'cu_rest')
NO_TICK = ('cu_intro', 'cu_rest', 'cu_desk', 'cu_odd', 'cu_report', 'cu_radio', 'cu_ask', 'cu_find', 'cu_calm', 'cu_verify', 'cu_tell',
           'cu_listen', 'cu_color')
PHYSICAL = ('cu_close', 'cu_sort')
GROUNDED = ('cu_ask', 'cu_send', 'cu_redirect', 'cu_close', 'cu_sort', 'cu_sign', 'cu_listen')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'cu_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Chị Thảo đang chờ ở bảng đội.')
    odd = d['odd']
    if name == 'cu_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    desk = d['desk']
    if name == 'cu_desk':
        result = kit.desk_choose(s, c, ID, desk, RC.DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'cu_odd':
        result = ao.reply(s, c, ID, odd, RC.ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    kit.desk_block(desk, 'Có chuyện ở phòng trực, quyết xong rồi làm tiếp nhé.')
    ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
    kit.need(not (ao.grounded(c, odd) and name in GROUNDED), 'Bạn đang bị tạm đình chỉ trực hết hôm nay. Tan ca, mai lên phòng Điều phối trình bày.', 'grounded')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở tổng đài.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, RC.DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(RC.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
        return
    _odd_tick(s, c, d, result)


def _odd_tick(s: dict, c: dict, d: dict, result: dict) -> None:
    """Someone around the line turns up when today's plan says so (never over an open desk surprise)."""
    x = ao.tick(s, c, ID, d['odd'], RC.ODD, busy=d['desk']['ev'] is not None)
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None, stage: str | None = 'open', known: bool = True) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tổng đài.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    if known:
        kit.need(t['known'], 'Nhấc máy trước đã.' if t['kind'] == 'call' else 'Nghe chị Thảo giao việc đã nhé.')
    kit.need(t['stage'] != 'done', 'Việc này đã xong.')
    if stage == 'open':
        kit.need(t['stage'] == 'open', 'Đã quyết cuộc này rồi: đọc hướng dẫn hoặc kết thúc cuộc gọi.')
    elif stage == 'decided':
        kit.need(t['stage'] == 'decided', 'Quyết gửi đội hay chuyển đúng nơi trước đã.')
    return t


def _case(t: dict) -> dict:
    return CALLS[t['_v']['case']]


def _tick(t: dict, what: str) -> None:
    t['secs'] = min(9999, t['secs'] + SECS[what])


# ---------------------------------------------------------------- chị Thảo listening in (the first three calls)
def _learning(d: dict) -> bool:
    return d['learn']['n'] < LEARN


def _guard(d: dict, code: str, line: str) -> dict | None:
    """In the first calls chị Thảo stops each kind of mistake once, before it is made (nothing is recorded)."""
    lr = d['learn']
    if lr['n'] >= LEARN or code in lr['caught'] or len(lr['caught']) >= 24:
        return None
    lr['caught'].append(code)
    return dict(message=f'✋ Chị Thảo bấm nút nghe kèm: “{line}”', correct=False)


# ---------------------------------------------------------------- the board at the start of the shift
def _radio(s, c, d, p):
    t = _task(c, p, ('shift',))
    u = kit.one_of(p.get('unit'), UNIT_IDS, 'Đội không có trên bảng.')
    key = f'u:{u}'
    kit.need(key not in t['tried'], 'Đã gọi đội này rồi.')
    t['tried'].append(key)
    kit.start_work(t)
    return dict(message=f'📻 {RC.UNIT_NOTES[u][1 if u == t["_v"]["down"] else 0]}')


def _sign(s, c, d, p):
    t = _task(c, p, ('shift',))
    down = kit.one_of(p.get('down'), UNIT_IDS + ('none',), 'Chọn đội tạm ngưng, hoặc “không đội nào”.')
    heard = sum(1 for u in UNIT_IDS if f'u:{u}' in t['tried'])
    real = t['_v']['down']
    if down != real:
        g = _guard(d, 'board', 'Nghe lại bộ đàm: có đội nào báo tạm ngưng không? Đánh dấu cho đúng rồi hãy ký.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'unmarked', 2, 'Ký nhận ca mà bảng đội chưa đánh dấu đúng đội tạm ngưng.', 'bảng đội chưa đúng')
    if heard < len(UNIT_IDS):
        t['mistakes'] += 1
        cq.slip(t, 'skim', 1, 'Nhận ca mà không gọi đủ các đội.', 'chưa gọi đủ các đội')
    b = d['board']
    b['day'] = c['day']
    b['down'] = None if down == 'none' else down
    t['choice'] = down
    t['result'] = 'signed'
    kit.start_work(t)
    ok = not cq.slips(t)
    _finish(s, c, d, t, 0, 'Nhận ca, rà bảng đội.', call=False)
    tail = f' Bảng đội: {_unit(down)} tạm ngưng.' if down != 'none' else ' Bảng đội: tất cả sẵn sàng.'
    return dict(message=f'🗺️ Ký nhận ca.{tail}' + (' Chị Thảo gật đầu: “Bảng đúng, ca này yên tâm.”' if ok else ''), celebrate=ok)


# ---------------------------------------------------------------- the call: the script
def _panicked(t: dict) -> bool:
    return t['calm'] < t['_v']['panic']


def _not_dropped(t: dict) -> None:
    kit.need(not t['drop'], 'Máy đã cúp: tút tút tút. Gọi lại số vừa gọi trước đã.')


def _panic_line(d: dict, t: dict) -> dict:
    _tick(t, 'panic')
    g = _guard(d, 'panic', 'Người gọi đang hoảng, hỏi gì cũng không nghe. Trấn an trước, rồi hỏi tiếp.')
    if g:
        return g
    lines = RC.PANIC_LINE
    return dict(message=f'😰 {lines[len(t["tried"]) % len(lines)]}')


def _answer(t: dict, q: str) -> str:
    x = _case(t)
    if t['_v']['truth'] == 'fake' and q in x['fake']:
        return x['fake'][q]
    return x['ans'][q]


def _ask(s, c, d, p):
    t = _task(c, p, ('call',), stage=None)
    q = kit.one_of(p.get('q'), Q_IDS, 'Câu hỏi không có trong kịch bản.')
    kit.need(q not in t['asked'], 'Đã hỏi câu này rồi.')
    _not_dropped(t)
    kit.start_work(t)
    if t['stage'] == 'open' and q != 'where' and 'where' not in t['asked'] and _case(t)['cat'] != 'junk':
        g = _guard(d, 'where_first', 'Địa chỉ trước em ơi. Lỡ rớt máy giữa chừng thì còn biết gửi xe tới đâu.')
        if g:
            return g
    if _panicked(t):
        return _panic_line(d, t)
    _tick(t, 'ask')
    t['asked'].append(q)
    text = _answer(t, q)
    msg = f'{QUESTIONS[q][0]} {text}'
    if _case(t)['hang'] and len(t['asked']) == 1 and 'recall' not in t['tried']:
        t['drop'] = True
        msg += ' (Tút… tút… tút. Máy cúp ngang.)'
    return dict(message=msg)


def _find(s, c, d, p):
    t = _task(c, p, ('call',))
    how = kit.one_of(p.get('how'), tuple(FIND), 'Cách tìm chỗ không có.')
    kit.need(how not in t['tried'], 'Đã thử cách này rồi.')
    kit.need('where' in t['asked'], 'Hỏi địa chỉ trước đã.')
    _not_dropped(t)
    if _panicked(t):
        return _panic_line(d, t)
    _tick(t, 'find')
    t['tried'].append(how)
    x = _case(t)
    lost = x['lost']
    if how == 'landmark':
        return dict(message=f'🪧 {x["ans"].get("landmark") or "“Thì ngay số nhà tôi vừa đọc đó.”"}')
    if how == 'locate':
        if x['addr'] == 'lost':
            return dict(message=lost['locate'] if t['_v']['smart'] else lost['no_locate'])
        return dict(message='📲 Định vị về khớp địa chỉ người gọi vừa đọc.')
    if x['addr'] == 'lost':
        return dict(message=lost['passer'])
    return dict(message='🙋 “Không có ai đi ngang… mà địa chỉ tôi đọc rồi đó.”')


def located(t: dict) -> bool:
    x = _case(t)
    if 'where' not in t['asked']:
        return False
    if x['addr'] == 'ok':
        return True
    if x['addr'] == 'vague':
        return 'landmark' in t['tried'] or 'locate' in t['tried']
    return ('locate' in t['tried'] and t['_v']['smart']) or ('landmark' in t['tried'] and 'passer' in t['tried'])


def _calm(s, c, d, p):
    t = _task(c, p, ('call',), stage=None)
    how = kit.one_of(p.get('how'), tuple(CALM), 'Cách trấn an không có.')
    key = f'calm:{how}'
    kit.need(key not in t['tried'], 'Đã nói câu này rồi.')
    _not_dropped(t)
    kit.start_work(t)
    if how == 'shout':
        g = _guard(d, 'shout', 'Quát người đang hoảng thì họ càng hoảng. Thử cho họ một việc nhỏ, hoặc thở cùng họ.')
        if g:
            return g
    _tick(t, 'calm')
    t['tried'].append(key)
    panic = t['_v']['panic']
    if how == 'shout':
        t['calm'] = max(0, t['calm'] - 1)
        t['mistakes'] += 1
        cq.slip(t, 'harsh', 1, 'Tổng đài quát người gọi đang hoảng.', 'quát người đang hoảng')
        return dict(message='😭 Người gọi khóc to hơn: “Sao chị la tôi!”', correct=False)
    if panic == 0:
        return dict(message=f'{CALM[how][0]} Người gọi vẫn bình tĩnh: “Dạ, tôi nghe đây.”')
    t['calm'] = min(5, t['calm'] + (2 if how == t['_v']['soothe'] else 1))
    if t['calm'] >= panic:
        return dict(message=f'{CALM[how][0]} Giọng người gọi chậm lại: “…được rồi… tôi nghe đây.”', celebrate=True)
    return dict(message=f'{CALM[how][0]} Người gọi thở hổn hển, vẫn còn run: “…dạ… dạ…”')


def _verify(s, c, d, p):
    t = _task(c, p, ('call',))
    how = kit.one_of(p.get('how'), tuple(VERIFY), 'Cách kiểm tra không có.')
    kit.need(how not in t['tried'], 'Đã kiểm tra cách này rồi.')
    if how != 'recall':
        _not_dropped(t)
    if how == 'probe' and _panicked(t):
        return _panic_line(d, t)
    kit.start_work(t)
    _tick(t, 'verify')
    t['tried'].append(how)
    t['drop'] = False
    x = _case(t)
    clue = (x['clues'].get(how) or {}).get(t['_v']['truth'])
    if clue:
        return dict(message=clue)
    if how == 'recall':
        return dict(message='↩️ Gọi lại: người gọi nghe máy ngay, vẫn đang ở đó.')
    if how == 'listen':
        return dict(message='👂 Tiếng nền khớp với lời người gọi kể.')
    return dict(message='🔎 Người gọi kể thêm chi tiết, khớp với những gì đã nói.')


# ---------------------------------------------------------------- the call: deciding
def _checked(t: dict) -> bool:
    return any(k in t['tried'] for k in VERIFY)


def _send(s, c, d, p):
    t = _task(c, p, ('call',))
    prio = kit.one_of(p.get('prio'), SEND_PRIO, 'Chọn mức ưu tiên trên bảng.')
    teams = kit.id_list(p.get('teams') or [], UNIT_IDS, len(UNIT_IDS), 'Chọn đội cần gửi.')
    kit.need(teams, 'Chọn ít nhất một đội để gửi.')
    _not_dropped(t)
    kit.need(located(t), 'Chưa có địa chỉ chắc chắn: xe không biết đi đâu. Hỏi địa chỉ, hỏi mốc hoặc gửi định vị trước.')
    x = _case(t)
    truth = t['_v']['truth']
    if 'what' not in t['asked']:
        g = _guard(d, 'blind', 'Chưa biết chuyện gì mà đã chọn đội? Hỏi “chuyện gì đang xảy ra” đã em.')
        if g:
            return g
    if x['cat'] == 'doubt' and not _checked(t):
        g = _guard(d, 'check', 'Giọng này có gì lạ không? Lắng nghe, hỏi kỹ hoặc gọi lại trước khi quyết.')
        if g:
            return g
    if x['cat'] == 'junk':
        g = _guard(d, 'junk', 'Có ai đang gặp nguy hiểm tính mạng không? Đường dây khẩn gửi xe cho chuyện nguy hiểm thôi.')
        if g:
            return g
    if truth == 'real':
        miss = [u for u in x['teams'] if u not in teams]
        if miss:
            g = _guard(d, 'short', 'Nghe lại lời người gọi: còn đội nào cần tới nữa không?')
            if g:
                return g
        if PRIO_ORDER.index(prio) > PRIO_ORDER.index(x['prio']) and prio not in x['ok_prio']:
            g = _guard(d, 'under', 'Nguy hiểm tính mạng tới đâu? Xem lại bảng ưu tiên.')
            if g:
                return g
    _tick(t, 'send')
    t['prio'] = prio
    t['teams'] = list(teams)
    t['stage'] = 'decided'
    kit.start_work(t)
    _stat(d, 'sent')
    notes = _board_send(c, d, t, x, teams)
    who = BINH if 'fire' in teams or 'boat' in teams else VY if 'amb' in teams else THAO
    reply = {BINH: 'Anh Bình: “Nhận, xuất phát!”', VY: 'Bác sĩ Vy: “Xe chạy rồi, em giữ người gọi giúp chị.”', THAO: 'Bộ đàm: “Nhận, đang tới.”'}[who]
    head = f'{PRIO[prio][0]} Gửi {", ".join(_unit(u) for u in teams)} · mức {PRIO[prio][1].lower()}. {reply}'
    return dict(message=' '.join([head] + notes).strip())


def _board_send(c: dict, d: dict, t: dict, x: dict, teams: list) -> list:
    """Units on the board: the one down today (marked or not), the ones still away from an earlier call."""
    b = d['board']
    if b['day'] != c['day']:
        d['board'] = b = _fresh_board(c['day'])
    real_down = flag_unit(c['day'])
    notes = []
    urgent = x['prio'] == 'p1' and t['_v']['truth'] == 'real'
    for u in teams:
        name = _unit(u)
        if u == real_down:
            if b['down'] == u:
                notes.append(f'↪️ {name} tạm ngưng: tự động mượn đội phường bên.')
            else:
                t['mistakes'] += 1
                cq.slip(t, 'board', 2 if urgent else 1, f'Gọi {name.lower()} không ai trả lời: bảng đội chưa đánh dấu tạm ngưng, mất ba phút mới mượn được phường bên.',
                        'gọi đội đang tạm ngưng')
                notes.append(f'📻 {name} không trả lời! Bảng đội chưa đánh dấu tạm ngưng: mất ba phút mới mượn được phường bên.')
        elif b['busy'].get(u, 0) > 0:
            if u in b['tied']:
                t['mistakes'] += 1
                cq.slip(t, 'tied', 2, f'{name} còn đang đi một chuyến không cần thiết lúc nãy, ca này phải chờ đội phường bên.', 'đội bị giữ chân vì gửi thừa')
                notes.append(f'⏳ {name} còn kẹt ở chuyến không cần thiết lúc nãy: chờ đội phường bên.')
            else:
                notes.append(f'↪️ {name} đang đi ca trước, đội phường bên hỗ trợ.')
    need = set(x['teams']) | set(x['ok_teams']) if t['_v']['truth'] == 'real' else set()
    for u in teams:
        b['busy'][u] = AWAY
        if u not in need and u not in b['tied']:
            b['tied'].append(u)
        elif u in need and u in b['tied']:
            b['tied'].remove(u)
    return notes


def _redirect(s, c, d, p):
    t = _task(c, p, ('call',))
    to = kit.one_of(p.get('to'), tuple(REDIRECT), 'Chọn nơi chuyển tới.')
    tone = kit.one_of(p.get('tone'), tuple(TONES), 'Chọn giọng nói.')
    x = _case(t)
    truth = t['_v']['truth']
    if x['cat'] == 'doubt' and not _checked(t):
        g = _guard(d, 'check', 'Chưa kiểm tra mà đã cho là gọi đùa? Lắng nghe, hỏi kỹ hoặc gọi lại trước khi quyết.')
        if g:
            return g
    if truth == 'real':
        g = _guard(d, 'missed', 'Người gọi đang gặp nguy hiểm thật đó. Nghe lại: có cần gửi đội không?')
        if g:
            return g
    if tone == 'sharp':
        g = _guard(d, 'sharp', 'Từ chối cũng giữ giọng lịch sự em. Dứt khoát mà không gắt.')
        if g:
            return g
    _tick(t, 'redirect')
    t['to'] = to
    t['tone'] = tone
    t['stage'] = 'decided'
    kit.start_work(t)
    _stat(d, 'redirected')
    mood = t['_v']['mood']
    who = 'Người gọi'
    push = x['push']
    if tone == 'sharp':
        t['mistakes'] += 1
        cq.slip(t, 'rude', 1, 'Tổng đài trả lời cộc lốc, gắt gỏng.', 'gắt với người gọi')
        line = '“Thái độ gì vậy! Tôi khiếu nại đó!”' if mood == 0 else '“Gắt với ai đó? Tôi gọi lại hoài cho coi!”'
        return dict(message=f'😤 {REDIRECT[to][0]} {REDIRECT[to][1]}. {who}: {line}', correct=False)
    if tone == 'soft' and mood >= 2:
        t['mistakes'] += 1
        _tick(t, 'redirect')
        cq.slip(t, 'loop', 1, 'Nói nhẹ quá, người gọi cứ nằn nì, đường dây bị giữ lâu.', 'để người gọi nằn nì giữ máy')
        line = push[0] if push else '“Thôi mà, giúp tôi chút đi!”'
        return dict(message=f'🙂 {REDIRECT[to][0]} {REDIRECT[to][1]}. {who} nằn nì: {line} (Đường dây bị giữ thêm nửa phút.)')
    tail = {'warn': '“…dạ… em xin lỗi.” (cúp máy)', 'adult': '“Dạ… con đi gọi ông…”', 'talk': '“Ờ, có người hỏi han là vui rồi.”',
            'taxi': '“Ờ… ờ… để anh gọi taxi.”', 'noise': '“Vậy để tôi gọi số đó.”', 'press': '“Okela, Long gọi phòng truyền thông.”',
            'utility': '“Ờ, để tôi gọi điện lực.”', 'morning': '“Sáng mai hả… thôi cũng được.”', 'clinic': '“Ờ, vậy tôi đi khám.”',
            'explain': '“À… vậy hả, để tôi gọi đúng chỗ.”'}[to]
    return dict(message=f'{TONES[tone][0]} {REDIRECT[to][0]} {REDIRECT[to][1]}. {who}: {tail}')


# ---------------------------------------------------------------- the call: instructions and closing
def _tell(s, c, d, p):
    t = _task(c, p, ('call',), stage='decided')
    x = _case(t)
    card = kit.one_of(p.get('card'), x['cards'], 'Thẻ hướng dẫn không dành cho cuộc gọi này.')
    kit.need(card not in t['told'], 'Đã đọc thẻ này rồi.')
    _not_dropped(t)
    if card in BAD:
        g = _guard(d, 'unsafe', f'Khoan! Đọc lại thẻ “{INSTR[card][1]}”: làm vậy có an toàn không?')
        if g:
            return g
    _tick(t, 'tell')
    t['told'].append(card)
    if card in BAD:
        t['mistakes'] += 1
        cq.slip(t, 'unsafe', 3, f'Tổng đài hướng dẫn sai: {INSTR[card][1].lower()}.', 'hướng dẫn nguy hiểm', safety=True)
        return dict(message=f'⚠️ Bạn đọc: “{INSTR[card][1]}”. {HARM[card]}', correct=False)
    _stat(d, 'told')
    return dict(message=f'🗣️ Bạn đọc: “{INSTR[card][1]}.” — “Dạ, tôi làm liền.”')


def _close(s, c, d, p):
    t = _task(c, p, ('call',), stage='decided')
    stay = p.get('stay')
    kit.need(type(stay) is bool, 'Chọn giữ máy hay kết thúc cuộc gọi.')
    x = _case(t)
    truth = t['_v']['truth']
    sent = bool(t['teams'])
    need_help = truth == 'real' and sent
    if need_help:
        miss = [k for k in x['key'] if k not in t['told']]
        if miss:
            g = _guard(d, 'noinstr', f'Trong lúc chờ xe, người gọi cần làm gì cho an toàn? Đọc thẻ “{INSTR[miss[0]][1]}”.')
            if g:
                return g
        if 'phone' not in t['asked']:
            g = _guard(d, 'nophone', 'Chưa xin số gọi lại. Lỡ đội lạc đường thì gọi ai?')
            if g:
                return g
        if x['stay'] and not stay:
            g = _guard(d, 'left', 'Người gọi đang một mình, đang sợ. Giữ máy với họ tới khi đội tới.')
            if g:
                return g
    _tick(t, 'close')
    t['stay'] = stay
    _grade(c, d, t, x, truth, sent, stay)
    if stay:
        _stat(d, 'stayed')
    outcome = _outcome(t, x, truth, sent, stay)
    _fact(d, t, *_facts(t, x, truth, sent))
    msg = _finish(s, c, d, t, BONUS, f'{x["label"]}.')
    clean = not cq.slips(t)
    return dict(message=f'{outcome} {msg}'.strip(), celebrate=clean, correct=not cq.safety(t))


def _grade(c: dict, d: dict, t: dict, x: dict, truth: str, sent: bool, stay: bool) -> None:
    def slip(code, sev, text, note, safety=False):
        t['mistakes'] += 1
        cq.slip(t, code, sev, text, note, safety=safety)

    checked = _checked(t)
    if checked:
        _stat(d, 'checked')
    if 'what' not in t['asked']:
        slip('blind', 1, 'Quyết mà chưa hỏi chuyện gì đang xảy ra.', 'quyết khi chưa hỏi chuyện gì')
    if sent:
        if truth == 'real':
            if 'phone' not in t['asked']:
                slip('nophone', 1, 'Không xin số gọi lại; rớt máy là mất liên lạc.', 'thiếu số gọi lại')
            if 'who' not in t['asked']:
                slip('nocount', 1, 'Không hỏi mấy người, ai bị thương.', 'không hỏi số người')
            if 'danger' not in t['asked']:
                slip('nodanger', 1, 'Không hỏi lửa, gas, điện, nước: đội tới không biết trước nguy hiểm.', 'không hỏi nguy hiểm')
            want, got = PRIO_ORDER.index(x['prio']), PRIO_ORDER.index(t['prio'])
            if got > want and t['prio'] not in x['ok_prio']:
                red = x['prio'] == 'p1'
                slip('under_red' if red else 'under', 3 if red and got - want >= 2 else 2, 'Ca nguy hiểm tính mạng mà xếp mức thấp, xe chạy không còi.',
                     'xếp ưu tiên thấp hơn mức nguy hiểm', safety=red and got - want >= 2)
            elif got < want and t['prio'] not in x['ok_prio']:
                slip('over', 1, 'Xếp mức cao hơn cần thiết, xe hú còi chạy ẩu qua phố.', 'xếp ưu tiên cao quá')
            miss = [u for u in x['teams'] if u not in t['teams']]
            if miss:
                red = x['prio'] == 'p1'
                slip('short_red' if red else 'short', 3 if red else 2, f'Thiếu {", ".join(UNITS[u][1].lower() for u in miss)}.', 'gửi thiếu đội',
                     safety=red)
            extra = [u for u in t['teams'] if u not in x['teams'] and u not in x['ok_teams']]
            if extra:
                slip('waste', 1, f'Gửi thừa {", ".join(UNITS[u][1].lower() for u in extra)}: đội đó bị giữ chân.', 'gửi thừa đội')
            miss = [k for k in x['key'] if k not in t['told']]
            if miss:
                slip('noinstr', 2, f'Không hướng dẫn người gọi: {INSTR[miss[0]][1].lower()}.', 'thiếu hướng dẫn an toàn')
            if x['stay'] and not stay:
                slip('left', 2, 'Người gọi một mình đang sợ, tổng đài cúp máy.', 'bỏ người gọi một mình')
        else:
            if x['cat'] == 'junk':
                slip('waste', 2, 'Gửi xe cho chuyện không khẩn: đội bị giữ chân, ca thật phải chờ.', 'gửi xe cho cuộc không khẩn')
            else:
                _stat(d, 'pranks')
                slip('waste', 1, 'Xe chạy tới nơi không có chuyện gì.', 'gửi xe cho cuộc gọi giả')
                if not checked:
                    slip('nocheck', 1, 'Gửi xe mà không kiểm tra cuộc gọi nghi ngờ.', 'không kiểm tra cuộc gọi')
            if stay:
                slip('hog', 1, 'Giữ máy với cuộc không khẩn, đường dây khác réo không ai nghe.', 'giữ máy không cần thiết')
        return
    # nobody sent
    if truth == 'real':
        red = x['prio'] in ('p1', 'p2')
        slip('missed', 3 if red else 2, 'Cuộc gọi thật mà tổng đài không gửi ai.', 'bỏ sót cuộc gọi thật', safety=red)
        return
    if x['cat'] == 'doubt':
        _stat(d, 'pranks')
        if not checked:
            slip('guess', 2, 'Cho là gọi đùa mà không kiểm tra gì.', 'đoán mò, không kiểm tra')
    if t['to'] != x['to'] and t['to'] not in x['ok_to']:
        slip('misroute', 1, 'Chuyển người gọi tới nơi không giúp được họ.', 'chuyển chưa đúng nơi')
    miss = [k for k in x['key'] if k not in t['told']]
    if miss:
        slip('noinstr', 1, f'Quên dặn: {INSTR[miss[0]][1].lower()}.', 'quên dặn an toàn')
    if stay:
        slip('hog', 1, 'Giữ máy với cuộc không khẩn, đường dây khác réo không ai nghe.', 'giữ máy không cần thiết')


def _outcome(t: dict, x: dict, truth: str, sent: bool, stay: bool) -> str:
    if sent and truth == 'real':
        safe = not cq.safety(t)
        head = '🚨 Đội tới nơi.' if safe else '🚨 Đội tới nơi, nhưng có chuyện không hay.'
        if stay:
            head += ' Bạn giữ máy tới lúc nghe tiếng còi xe đầu hẻm: “Họ tới rồi! Cảm ơn chị!”'
        return head
    if sent:
        return '🚒 Đội tới nơi: không có chuyện gì. Anh Bình gọi về: “Đi không rồi em.”'
    if truth == 'real':
        return '📵 Không ai được gửi tới. Lát sau người gọi phải gọi lại lần nữa.'
    return '✅ Đường dây trống lại cho cuộc gọi kế.'


def _facts(t: dict, x: dict, truth: str, sent: bool) -> tuple:
    head = f'{t["needs"]["time"]} {x["label"]}'
    if sent:
        text = f'{head}: gửi {", ".join(UNITS[u][1].lower() for u in t["teams"])} ({PRIO[t["prio"]][1].lower()}).'
        if truth != 'real':
            text = f'{head}: gửi xe, tới nơi không có chuyện gì.'
    else:
        text = f'{head}: không gửi xe, {REDIRECT[t["to"]][1].lower()}.'
    key = sent or truth == 'real' or bool(cq.safety(t))
    lie = (f'{head}: đã hỏi đủ kịch bản, gửi đúng đội, hướng dẫn đầy đủ.' if sent else f'{head}: đã hỏi đủ kịch bản, chuyển đúng nơi, lời lẽ lịch sự.') \
        if cq.slips(t) else None
    return text, key, lie


def _fact(d: dict, t: dict, text: str, key: bool, lie: str | None = None) -> None:
    """A line the end-of-shift log may carry (true), and a tempting one that did not happen (lie)."""
    rows = d['today']['facts']
    rows.append(dict(id=f'f-{t["id"]}', text=text[:160], key=bool(key), true=True))
    if lie:
        rows.append(dict(id=f'l-{t["id"]}', text=lie[:160], key=False, true=False))
    d['today']['facts'] = rows[-FACTS_MAX:]


# ---------------------------------------------------------------- the rain-season queue
def _listen(s, c, d, p):
    t = _task(c, p, ('queue',))
    i = kit.integer(p.get('i'), 0, len(t['_v']['lines']) - 1)
    key = f'q:{i}'
    kit.need(key not in t['tried'], 'Đã nghe máy này rồi.')
    t['tried'].append(key)
    kit.start_work(t)
    x = LINES[t['_v']['lines'][i]]
    return dict(message=f'👂 {x["who"]}: {x["ask"]}')


def _color(s, c, d, p):
    t = _task(c, p, ('queue',))
    i = kit.integer(p.get('i'), 0, len(t['_v']['lines']) - 1)
    prio = kit.one_of(p.get('prio'), PRIO_ORDER, 'Mức ưu tiên không có trên bảng.')
    t['colors'][str(i)] = prio
    kit.start_work(t)
    return dict(message=f'{PRIO[prio][0]} {t["needs"]["lines"][i]["who"]}: {PRIO[prio][1].lower()}.')


def _sort(s, c, d, p):
    t = _task(c, p, ('queue',))
    lines = t['_v']['lines']
    kit.need(len(t['colors']) == len(lines), 'Xếp ưu tiên cho đủ các đường dây đã.')
    under = [i for i, k in enumerate(lines) if LINES[k]['best'] == 'p1' and t['colors'][str(i)] != 'p1']
    if under:
        g = _guard(d, 'q_under', f'Nghe lại {t["needs"]["lines"][under[0]]["who"].lower()}: chuyện đó có nguy hiểm tính mạng không?')
        if g:
            return g
    out = []
    worst = 0
    for i, k in enumerate(lines):
        x = LINES[k]
        got = t['colors'][str(i)]
        gi, bi = PRIO_ORDER.index(got), PRIO_ORDER.index(x['best'])
        if gi == bi:
            out.append(f'{PRIO[got][0]} {x["who"]}: đúng.')
            continue
        if f'q:{i}' not in t['tried']:
            t['mistakes'] += 1
            cq.slip(t, 'blind', 1, 'Xếp ưu tiên mà chưa nghe máy.', 'xếp khi chưa nghe')
        if gi > bi:
            sev = 3 if x['best'] == 'p1' else 2
            t['mistakes'] += 1
            cq.slip(t, 'under_red' if sev == 3 else 'under', sev, f'{x["who"]} nguy hiểm mà phải chờ.', 'xếp ca nguy hiểm xuống sau', safety=sev == 3)
            worst = max(worst, sev)
            out.append(f'{PRIO[got][0]} {x["who"]}: đáng lẽ {PRIO[x["best"]][0]} {PRIO[x["best"]][1].lower()}.')
        else:
            t['mistakes'] += 1
            cq.slip(t, 'over', 1, 'Ca không gấp được nhấc trước, ca khác phải chờ.', 'đẩy ca nhẹ lên trước')
            out.append(f'{PRIO[got][0]} {x["who"]}: hơi cao, {PRIO[x["best"]][0]} là đủ.')
    t['choice'] = 'sorted'
    t['result'] = 'sorted'
    _stat(d, 'calls', len(lines))
    reds = sum(1 for i in range(len(lines)) if t['colors'][str(i)] == 'p1')
    _fact(d, t, f'{t["needs"]["time"]} Mưa lớn: xếp {len(lines)} đường dây, {reds} ca khẩn cấp nhấc trước.', key=True,
          lie=f'{t["needs"]["time"]} Mưa lớn: xếp đúng hết các đường dây.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, 'Xếp ưu tiên nhiều đường dây.')
    return dict(message=f'📞 {" ".join(out)} {msg}'.strip(), celebrate=not cq.slips(t), correct=worst < 3)


# ---------------------------------------------------------------- finishing a task
def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str, call: bool = True) -> str:
    """Pays the bonus (none after a safety mistake; half when tired, none while demoted) and completes once."""
    pts = cq.points(t)
    full = 0 if cq.safety(t) or not reward else max(0, reward - 3 * pts)
    pay = ao.bonus(d['odd'], full)
    t['stage'] = 'done'
    story = ''
    i = int(t['npc'].rsplit('_', 1)[1]) - 1 if t.get('npc') else -1
    if call:
        if i in RC.REG_STORY and t['kind'] == 'call':
            r = d['regulars'].setdefault(str(i), dict(visits=0))
            r['visits'] = min(999, r['visits'] + 1)
            story = RC.REG_STORY[i][min(r['visits'], len(RC.REG_STORY[i])) - 1]
            t['story'] = story
        d['learn']['n'] = min(10 ** 6, d['learn']['n'] + 1)
        if t['kind'] == 'call':
            _stat(d, 'calls')
            d['today']['secs'] = min(10 ** 7, d['today']['secs'] + t['secs'])
        if cq.safety(t):
            _stat(d, 'safety')
        _board_tick(c, d)
    kit.complete(s, c, t, pay, (narrative or t['title'])[:300])
    note = ao.flown(d['odd'], not cq.slips(t), CFG) if call else ''
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


def _board_tick(c: dict, d: dict) -> None:
    """A call is over: the units away come one call nearer to home."""
    b = d['board']
    for u in list(b['busy']):
        b['busy'][u] -= 1
        if b['busy'][u] <= 0:
            del b['busy'][u]
            if u in b['tied']:
                b['tied'].remove(u)


# ---------------------------------------------------------------- the end-of-shift log
def _report(s, c, d, p):
    today = d['today']
    kit.need(today['report'] is None, 'Hôm nay đã ghi sổ nhật ký rồi.')
    rows = today['facts']
    kit.need(rows, 'Chưa có gì để ghi sổ. Nhận cuộc gọi trước đã.')
    pick = kit.id_list(p.get('lines') or [], [r['id'] for r in rows], FACTS_MAX, 'Chọn dòng ghi vào sổ.')
    kit.need(pick, 'Chọn ít nhất một dòng ghi vào sổ nhật ký.')
    chosen = [r for r in rows if r['id'] in pick]
    lies = [r for r in chosen if not r['true']]
    miss = [r for r in rows if r['key'] and r['true'] and r['id'] not in pick]
    d['stats']['reports'] = min(10 ** 7, d['stats']['reports'] + 1)
    if lies:
        today['report'] = 'false'
        note = ao._conduct(c, d['odd'], 2, CFG)
        return dict(message=f'📒 Chị Thảo đối chiếu băng ghi âm, khựng lại ở dòng “{lies[0]["text"]}”: “Băng đâu có vậy, em?” Ghi khống sổ nhật ký. {note}',
                    correct=False)
    if miss:
        today['report'] = 'miss'
        c['xp'] += 2
        return dict(message=f'📒 Sổ nhật ký thật, nhưng thiếu: “{miss[0]["text"]}”. Ca sau phải nghe lại băng mới biết.')
    today['report'] = 'ok'
    c['xp'] += 8
    d['stats']['honest'] = min(10 ** 7, d['stats']['honest'] + 1)
    return dict(message='📒 Sổ nhật ký rõ ràng, thật, đủ các cuộc cần theo dõi. Ca sau đọc một lượt là nắm hết.', celebrate=True)


ACTIONS = {
    'cu_radio': _radio, 'cu_sign': _sign, 'cu_ask': _ask, 'cu_find': _find, 'cu_calm': _calm, 'cu_verify': _verify, 'cu_send': _send,
    'cu_redirect': _redirect, 'cu_tell': _tell, 'cu_close': _close, 'cu_listen': _listen, 'cu_color': _color, 'cu_sort': _sort,
    'cu_report': _report,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['today'] = _fresh_today(day)
    d['board'] = _fresh_board(day)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'shift' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    if not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        sh = make_task(day, 0, c['turn'])
        c['tasks'].append(sh)
        on_task(s, c, sh)
    sh = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'shift' and t['day'] == day
               and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if sh:
        c['active_task'] = sh['id']
        sh['deferred'] = False
    ao.start(c, ID, d['odd'])
    kit.desk_start(s, c, ID, d['desk'], RC.DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')
    ao.tick(s, c, ID, d['odd'], RC.ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], RC.DESK)
    odd_note = ao.close(s, c, d['odd'], RC.ODD)
    x = d['today']
    lines = [f'📞 Ca trực: {x["calls"]} cuộc gọi ở tổng đài cứu hộ.']
    if x['sent']:
        lines.append(f'🚒 Gửi đội {x["sent"]} lần.')
    if x['redirected']:
        lines.append(f'↪️ Chuyển đúng nơi {x["redirected"]} cuộc không cần xe.')
    if x['checked']:
        lines.append(f'🔎 Kiểm tra {x["checked"]} cuộc gọi nghi ngờ trước khi quyết.')
    if x['told']:
        lines.append(f'🗣️ Đọc {x["told"]} hướng dẫn an toàn trong lúc chờ xe.')
    calls = x['calls']
    if calls and x['secs']:
        lines.append(f'⏱️ Trung bình {x["secs"] // max(1, calls)} giây mỗi cuộc (anh Khải có xem biểu đồ).')
    if x['safety']:
        lines.append(f'📋 {x["safety"]} báo cáo sự cố. Mai họp ca rút kinh nghiệm.')
    if x['report'] is None and x['facts']:
        lines.append('📒 Chưa ghi sổ nhật ký: ca sau phải nghe lại băng từng cuộc.')
    elif x['report'] == 'ok':
        lines.append('📒 Sổ nhật ký rõ ràng, thật, đủ.')
    if desk_note:
        lines.append(desk_note)
    if odd_note:
        lines.append(odd_note)
    lines += ao.day_lines(c, d['odd'], CFG)
    lines.append('🏠 Tháo tai nghe, tai còn ù ù. Về tới hẻm, mùi cơm nhà ai thơm phức.')
    return dict(lines=lines, note='Mai nhận ca lúc 7:00, gọi bộ đàm từng đội trước khi ký.', tasks=calls, calls=calls, sent=x['sent'],
                redirected=x['redirected'], safety=x['safety'])


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
    if k == 'shift':
        return dict(criteria=[dict(key='radio', label='Gọi đủ các đội', score=_score(codes, {'skim'}), note='gọi đủ bộ đàm' if 'skim' not in codes else 'gọi sót đội'),
                              dict(key='board', label='Bảng đội đúng', score=_score(codes, set(), {'unmarked'}),
                                   note='đánh dấu đúng đội tạm ngưng' if 'unmarked' not in codes else 'bảng đội sai')])
    if k == 'queue':
        return dict(criteria=[dict(key='order', label='Xếp ưu tiên đúng', score=_score(codes, {'over'}, {'under'}, {'under_red'}),
                                   note='ca khẩn nhấc trước' if not codes & {'over', 'under', 'under_red'} else 'thứ tự chưa đúng'),
                              dict(key='listen', label='Nghe trước khi xếp', score=_score(codes, {'blind'}), note='nghe từng máy' if 'blind' not in codes else 'xếp khi chưa nghe')])
    script = {'blind', 'nophone', 'nocount', 'nodanger'}
    decide_bad, decide_worse, decide_worst = {'over', 'waste', 'misroute', 'nocheck', 'board'}, {'under', 'short', 'tied', 'guess'}, {'under_red', 'short_red', 'missed'}
    return dict(criteria=[
        dict(key='script', label='Hỏi đủ kịch bản', score=_score(codes, script), note='địa chỉ, chuyện gì, mấy người, nguy hiểm, số gọi lại' if not codes & script else 'hỏi thiếu'),
        dict(key='decide', label='Ưu tiên và đội đúng', score=_score(codes, decide_bad, decide_worse, decide_worst),
             note='đúng mức, đúng đội' if not codes & (decide_bad | decide_worse | decide_worst) else 'quyết chưa đúng'),
        dict(key='safe', label='Hướng dẫn an toàn', score=_score(codes, set(), {'noinstr'}, {'unsafe'}),
             note='dặn đúng, đủ' if not codes & {'noinstr', 'unsafe'} else 'dặn thiếu hoặc sai'),
        dict(key='voice', label='Giọng nói, giữ máy', score=_score(codes, {'rude', 'loop', 'hog', 'harsh'}, {'left'}),
             note='bình tĩnh, lịch sự' if not codes & {'rude', 'loop', 'hog', 'harsh', 'left'} else 'chưa khéo')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    k = t['kind']
    if k == 'shift':
        return 'Bảng đội: ' + ', '.join(UNITS[u][1].lower() for u in UNIT_IDS) + '.'
    if k == 'queue':
        return f'Chị Thảo: “{len(t["needs"]["lines"])} đường dây réo cùng lúc, xếp ưu tiên giúp chị.”'
    return _case(t)['opening']


def _addr(t: dict, x: dict) -> str | None:
    """The best address known so far (what the player has heard)."""
    if 'where' not in t['asked']:
        return None
    bits = [_answer(t, 'where')]
    if 'landmark' in t['tried'] and x['ans'].get('landmark'):
        bits.append(x['ans']['landmark'])
    if x['addr'] == 'lost':
        if 'locate' in t['tried']:
            bits.append(x['lost']['locate'] if t['_v']['smart'] else x['lost']['no_locate'])
        if 'passer' in t['tried']:
            bits.append(x['lost']['passer'])
    return ' · '.join(bits)


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    k = t['kind']
    if k == 'shift':
        if t['stage'] == 'done':
            v['down'] = t['_v']['down']
        v['needs'] = dict(units=[dict(u, note=RC.UNIT_NOTES[u['id']][1 if u['id'] == t['_v']['down'] else 0] if f'u:{u["id"]}' in t['tried'] else None)
                                 for u in t['needs']['units']])
        return v
    if k == 'queue':
        lines = t['_v']['lines']
        v['needs'] = dict(time=t['needs']['time'], lines=[dict(q, ask=LINES[lines[i]]['ask'] if f'q:{i}' in t['tried'] else None,
                                                                best=LINES[lines[i]]['best'] if t['stage'] == 'done' else None)
                                                           for i, q in enumerate(t['needs']['lines'])])
        return v
    if not t['known']:
        v['needs'] = dict(line=t['needs']['line'], time=t['needs']['time'])
        return v
    x = _case(t)
    view = dict(line=t['needs']['line'], time=t['needs']['time'], emoji=x['emoji'], label=x['label'], opening=x['opening'],
                answers={q: _answer(t, q) for q in t['asked']}, addr=_addr(t, x), located=located(t), lost=x['addr'] != 'ok',
                panicked=_panicked(t), drop=t['drop'], checked=[w for w in VERIFY if w in t['tried']], found=[w for w in FIND if w in t['tried']],
                calmed=[w for w in CALM if f'calm:{w}' in t['tried']], cards=list(x['cards']) if t['stage'] != 'open' else [])
    v['needs'] = view
    return v


def _board_view(c: dict, d: dict) -> list:
    b = d['board'] if d['board'].get('day') == c['day'] else _fresh_board(c['day'])
    out = []
    for u in UNIT_IDS:
        state = 'down' if b.get('down') == u else 'away' if b.get('busy', {}).get(u, 0) > 0 else 'ready'
        out.append(dict(id=u, emoji=UNITS[u][0], name=UNITS[u][1], state=state, back=b.get('busy', {}).get(u, 0)))
    return out


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
                today=dict(day=today.get('day', 0), calls=today.get('calls', 0), sent=today.get('sent', 0), redirected=today.get('redirected', 0),
                           checked=today.get('checked', 0), told=today.get('told', 0), safety=today.get('safety', 0), secs=today.get('secs', 0),
                           report=today.get('report'), facts=facts),
                stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()}, board=_board_view(c, d),
                learn=dict(on=lr.get('n', 0) < LEARN, n=lr.get('n', 0), of=LEARN),
                desk=kit.desk_public(d['desk'], RC.DESK, ID), odd=ao.public(c, ao.ensure(d), RC.ODD, ID, CFG))


def content() -> dict:
    return dict(intro=RC.INTRO, questions={k: list(v) for k, v in QUESTIONS.items()}, q_ids=list(Q_IDS), find={k: list(v) for k, v in FIND.items()},
                verify={k: list(v) for k, v in VERIFY.items()}, calm={k: list(v) for k, v in CALM.items()}, units={k: list(v) for k, v in UNITS.items()},
                unit_ids=list(UNIT_IDS), prio={k: list(v) for k, v in PRIO.items()}, prio_order=list(PRIO_ORDER), send_prio=list(SEND_PRIO),
                redirect={k: list(v) for k, v in REDIRECT.items()}, tones={k: list(v) for k, v in TONES.items()},
                instr={k: list(v) for k, v in INSTR.items()}, learn=LEARN,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    return {'shift': 'Gọi bộ đàm từng đội → đánh dấu đội tạm ngưng → ký nhận ca.',
            'call': 'Nhấc máy → địa chỉ trước (mốc, định vị nếu cần) → chuyện gì → trấn an nếu hoảng → nghi ngờ thì kiểm tra → '
                    'gửi đúng đội đúng mức, hoặc chuyển đúng nơi → đọc hướng dẫn an toàn → giữ máy nếu người gọi một mình.',
            'queue': 'Nghe nhanh từng máy → xếp mức ưu tiên theo nguy hiểm, không theo tiếng la → nhấc theo thứ tự.'}.get(t.get('kind'), '')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'radio':
        return 'Đã trực bộ đàm, báo giờ xe tới nơi cho từng ca.'
    if e.get('role') == 'clerk':
        return 'Đã sắp nhật ký cuộc gọi theo giờ, đánh dấu những cuộc cần gọi lại.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu tổng đài sai.')


def _tried_ok(t: dict) -> set:
    k = t.get('kind')
    if k == 'shift':
        return {f'u:{u}' for u in UNIT_IDS}
    if k == 'queue':
        n = len(t.get('_v', {}).get('lines') or [])
        return {f'q:{i}' for i in range(n)}
    return set(FIND) | set(VERIFY) | {f'calm:{w}' for w in CALM}


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN and t.get('kind') in KINDS and t.get('stage') in STAGES, 'Việc ở tổng đài sai.')
    asked = t.get('asked')
    kit.need(isinstance(asked, list) and len(asked) == len(set(asked)) and set(asked) <= set(Q_IDS), 'Câu hỏi kịch bản sai.')
    tried = t.get('tried')
    kit.need(isinstance(tried, list) and len(tried) == len(set(tried)) and set(tried) <= _tried_ok(t), 'Việc ở tổng đài sai.')
    kit.integer(t.get('calm'), 0, 5)
    _vbool(t.get('drop'))
    kit.integer(t.get('secs'), 0, 9999)
    kit.need(t.get('prio') in (None, *SEND_PRIO), 'Mức ưu tiên sai.')
    teams = t.get('teams')
    kit.need(isinstance(teams, list) and len(teams) == len(set(teams)) and set(teams) <= set(UNIT_IDS), 'Đội gửi sai.')
    kit.need(t.get('to') in (None, *REDIRECT), 'Nơi chuyển sai.')
    kit.need(t.get('tone') in (None, *TONES), 'Giọng nói sai.')
    told = t.get('told')
    kit.need(isinstance(told, list) and len(told) == len(set(told)) and set(told) <= set(INSTR), 'Hướng dẫn sai.')
    kit.need(t.get('stay') in (None, True, False), 'Giữ máy sai.')
    cols = t.get('colors')
    kit.need(isinstance(cols, dict) and len(cols) <= 4 and all(isinstance(k, str) and k in ('0', '1', '2', '3') and v in PRIO for k, v in cols.items()),
             'Mức ưu tiên sai.')
    kit.need(t.get('choice') is None or (isinstance(t['choice'], str) and len(t['choice']) <= 24), 'Lựa chọn sai.')
    kit.need(t.get('result') is None or (isinstance(t['result'], str) and len(t['result']) <= 24), 'Kết quả sai.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện người gọi sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in RC.REG_STORY}, 'Sổ người quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người quen sai.')
        kit.integer(v['visits'], 0, 999)
    kit.need(isinstance(d['stats'], dict) and len(d['stats']) <= 20, 'Số liệu tổng đài sai.')
    for v in d['stats'].values():
        kit.integer(v, 0, 10 ** 9)
    x = d['today']
    kit.need(isinstance(x, dict) and set(x) == set(_fresh_today(0)), 'Số liệu trong ngày sai.')
    for k in ('day', 'calls', 'sent', 'redirected', 'checked', 'told', 'safety', 'secs'):
        kit.integer(x[k], 0, 10 ** 9)
    kit.need(x['report'] in (None, 'ok', 'miss', 'false'), 'Sổ nhật ký sai.')
    kit.need(isinstance(x['facts'], list) and len(x['facts']) <= FACTS_MAX, 'Sổ nhật ký sai.')
    for r in x['facts']:
        kit.need(isinstance(r, dict) and set(r) == {'id', 'text', 'key', 'true'} and type(r['key']) is bool and type(r['true']) is bool, 'Sổ nhật ký sai.')
        kit.text(r['id'], 60)
        kit.text(r['text'], 160)
    b = d['board']
    kit.need(isinstance(b, dict) and set(b) == set(_fresh_board(0)), 'Bảng đội sai.')
    kit.integer(b['day'], 0, 10 ** 7)
    kit.need(b['down'] in (None, *UNIT_IDS), 'Bảng đội sai.')
    kit.need(isinstance(b['busy'], dict) and set(b['busy']) <= set(UNIT_IDS), 'Bảng đội sai.')
    for v in b['busy'].values():
        kit.integer(v, 0, AWAY)
    kit.need(isinstance(b['tied'], list) and len(b['tied']) == len(set(b['tied'])) and set(b['tied']) <= set(UNIT_IDS), 'Bảng đội sai.')
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'n', 'caught'} and isinstance(lr['caught'], list) and len(lr['caught']) <= 24, 'Sổ kèm việc sai.')
    kit.integer(lr['n'], 0, 10 ** 6)
    for k in lr['caught']:
        kit.text(k, 40)
    kit.desk_validate(d['desk'], RC.DESK)
    ao.validate(d['odd'], RC.ODD)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='cu_', category='service',
    meta=dict(short='Tổng đài cứu hộ', place='Tổng đài Cứu hộ phường Mây', tagline='Địa chỉ trước, gửi đúng đội, không bỏ ai một mình.', icon='headphones',
              color='#c4532f', light='#fbe9e2', weather='Trời trong, đường dây yên ả', work='Cuộc gọi trong ca', station='Bàn trực tổng đài',
              greeting='Nhận ca lúc 7:00. Gọi bộ đàm từng đội, đánh dấu đội tạm ngưng. Mỗi cuộc gọi: địa chỉ trước, gửi đúng đội, dặn an toàn.',
              caption='Mỗi hồi chuông là một người đang cần mình', map_label='29 · TỔNG ĐÀI CỨU HỘ'),
    people=PEOPLE,
    staff=[('Quân', 'radio', 'Trực bộ đàm lâu năm, nghe tiếng còi là biết xe nào.', 82, 90),
           ('Thư', 'clerk', 'Bạn thực tập ghi nhật ký nhanh, không sót giờ nào.', 76, 94),
           ('Hậu', 'radio', 'Nói chuyện với đội rõ ràng, gọn từng chữ.', 88, 82),
           ('Vân', 'clerk', 'Thuộc lòng bản đồ phường, hẻm nào cũng biết.', 74, 92)],
    roles={'radio': 'Trực bộ đàm', 'clerk': 'Thư ký nhật ký'},
    tip=0,
    open_line='Nhận ca lúc 7:00. Chị Thảo đang chờ ở bảng đội.',
    more_line='Đèn một đường dây nữa nháy đỏ.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('📞', 'Một ca ở tổng đài cứu hộ', [('Địa chỉ', 'Hỏi trước tiên'), ('Người đang hoảng', 'Trấn an, giao một việc nhỏ'),
                                              ('Cuộc gọi lạ', 'Nghe, hỏi kỹ, gọi lại'), ('Chảo dầu cháy', 'Không dội nước')],
              ['Rà bảng đội', 'Hỏi đủ kịch bản', 'Gửi đúng đội', 'Dặn an toàn, ghi sổ']),
    stories=[('Chiếc tai nghe cũ của chị Thảo', ('Chị Thảo giữ chiếc tai nghe đầu tiên của trung tâm, dây quấn băng keo đen.',
                                                 'Bạn trực thêm một ca; chị chỉ cách nghe tiếng nền để đoán người gọi đứng đâu.',
                                                 'Chị Thảo dặn: “Tai mình phải nghe được cả cái người ta không nói.”')),
             ('Bức tranh của bé Na', ('Bé Na gửi tổng đài bức tranh vẽ cô tổng đài đeo tai nghe.',
                                      'Bạn trực thêm một ca, dán bức tranh cạnh màn hình.',
                                      'Ông Ba gọi tới chỉ để hỏi: “Cô thấy tranh con Na vẽ chưa?”')),
             ('Cuốn sổ nhật ký đêm bão', ('Trong tủ trực có cuốn sổ nhật ký đêm bão mười năm trước, chữ chị Thảo nắn nót.',
                                          'Bạn trực thêm một ca, ghi sổ thật kỹ.',
                                          'Chị Thảo đọc xong, gập sổ: “Ca sau sẽ yên tâm.”'))],
    review_asides=['Hỏi địa chỉ trước tiên, nghe là yên tâm.', 'Giọng bình tĩnh ghê, nghe là bớt run.', 'Giữ máy với tôi tới lúc xe tới, cảm ơn nhiều.',
                   'Dặn từng bước rõ ràng, làm theo được liền.'],
    situations=RC.SITUATIONS,
    guide='Nhận ca: gọi bộ đàm, đánh dấu đội tạm ngưng → nhấc máy → địa chỉ trước → chuyện gì, mấy người, nguy hiểm gì, số gọi lại → '
          'người hoảng thì trấn an → cuộc nghi ngờ thì nghe, hỏi kỹ, gọi lại → gửi đúng đội, đúng mức, hoặc chuyển đúng nơi → '
          'đọc hướng dẫn an toàn → giữ máy với người một mình → cuối ca ghi sổ nhật ký thật.',
    employment=dict(
        postings=[
            dict(id='cu-dieuphoi', org='Tổng đài Cứu hộ phường Mây · Trung tâm điều phối', kind='public', title='Điều phối viên tổng đài cứu hộ',
                 salary=(52, 68), probation_days=3, wants=['calm', 'communication', 'careful'],
                 perks=['Chị Thảo kèm ba cuộc gọi đầu', 'Ca ngày 7:00–19:00', 'Có tai nghe và ghế tốt'],
                 culture='Sáu đội, một bảng ưu tiên, một nguyên tắc: hỏi địa chỉ trước, không bỏ ai một mình. Ở đây không ai được chặn số của ai.',
                 questions=['cu_q_addr', 'cu_q_prank', 'cu_q_panic', 'mistake'], reference=True),
            dict(id='cu-tiepnhan', org='Tổng đài Cứu hộ phường Mây · Bàn tiếp nhận', kind='parttime', title='Nhân viên tiếp nhận cuộc gọi (bán thời gian)',
                 salary=(40, 52), probation_days=2, wants=['patience', 'communication'],
                 perks=['Ca ngắn', 'Ngồi cạnh chị Thảo', 'Lương thấp hơn'],
                 culture='Bàn tiếp nhận nghe máy trước, hỏi kịch bản, chuyển cho điều phối viên. Nhiều cuộc gọi nhầm, gọi đùa, gọi để tâm sự.',
                 questions=['cu_q_vip', 'cu_q_addr'], reference=False),
        ],
        questions={
            'cu_q_addr': dict(text='Người gọi hét: “Cháy! Cháy! Tới liền đi!” Câu đầu tiên bạn hỏi là gì?', options=[
                dict(id='where', label='“Địa chỉ ở đâu ạ?” rồi mới hỏi chuyện gì', score=3, note='Chị Thảo gật đầu: có địa chỉ là gửi xe được ngay.'),
                dict(id='what', label='“Cháy cái gì, cháy to không?”', score=1, note='Cần hỏi, nhưng lỡ rớt máy thì không biết gửi xe đi đâu.'),
                dict(id='calm', label='“Bình tĩnh đi!”', score=0, note='Quát người đang hoảng không giúp ai bình tĩnh.')]),
            'cu_q_prank': dict(text='Một giọng con nít cười khúc khích báo cháy nhà. Bạn làm gì?', options=[
                dict(id='check', label='Lắng nghe tiếng nền, hỏi chi tiết, gọi lại số máy rồi mới quyết', score=3, note='Mỗi cuộc gọi là một cuộc mới: kiểm tra trước khi quyết.'),
                dict(id='hang', label='Cúp máy, chắc gọi đùa', score=0, note='Có bé gọi vì bà té thật mà sợ quá nên cười.'),
                dict(id='send', label='Gửi xe luôn cho chắc', score=1, note='An toàn hơn cúp máy, nhưng cần địa chỉ và kiểm tra để xe không đi không.')]),
            'cu_q_panic': dict(text='Người gọi khóc nấc, nói không thành câu. Bạn làm gì?', options=[
                dict(id='task', label='Xưng tên mình, thở chậm cùng họ, giao một việc nhỏ an toàn', score=3, note='Một việc nhỏ giúp người ta lấy lại nhịp.'),
                dict(id='wait', label='Chờ họ tự bình tĩnh', score=1, note='Thời gian trôi mà chưa có địa chỉ.'),
                dict(id='shout', label='Nói to: “Nói nhanh lên!”', score=0, note='Càng quát càng hoảng.')]),
            'cu_q_vip': dict(text='Một người tự xưng “quan trọng” đòi xe công an dẫn đường vì kẹt xe.', options=[
                dict(id='explain', label='Lịch sự giải thích đường dây chỉ dành cho nguy hiểm tính mạng, chỉ đúng chỗ cần gọi', score=3,
                     note='Dứt khoát mà không gắt: đường dây trống cho người cần.'),
                dict(id='send', label='Gửi xe cho yên chuyện', score=0, note='Xe đi dẫn đường thì ca thật phải chờ.'),
                dict(id='hang', label='Cúp máy không nói gì', score=1, note='Đường dây trống, nhưng người gọi sẽ gọi lại cả chục lần.')]),
        }),
)
