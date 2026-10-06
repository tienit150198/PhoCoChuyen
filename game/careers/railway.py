"""Gác chắn đường ngang Bến Mây: level-crossing keeper and track patrol for Xí nghiệp Đường sắt Sông Mây (plugin career).

The player keeps the crossing at Km 7+250 on phố Ray beside chú Sáu Cờ, who has held the flag there for twenty-eight
years. It is a salaried job (employment); a train seen through by the book adds a small bonus. One task is:

* ``shift`` (nhận ca, slot 0): read the hand-over book, copy today's trains onto the board and test the equipment one
  by one (bell and red lights, the barrier arms, the radio, flags and lamp, the book, the vest). A fault is fixed when
  the keeper can (a spare battery, the spare flag, the hand crank) and reported through the right channel: the
  hand-over book, the repair slip to the depot, or a call to the station when it touches train safety. Signing for a
  shift without testing everything, or keeping a dangerous fault from the station, is a slip;
* ``train``: ga Bến Mây radios a train (number, left ga Bến Gỗ at, due at the crossing at). The keeper reads it back
  word for word, looks over the crossing and clears whoever is on the rails (selfies, kids, chú Hớn asleep, a cow, a
  stuck cart…), rings the bell and only then lowers the arms, at the right time: about three minutes before the train
  (earlier keeps the street waiting and people start ducking under; later is dangerous). Then the people at the
  barrier push: the grab driver, a funeral, a wedding car, an ambulance, a bribe, a "VIP"… The player answers in their
  own way (hold, show the board, a detour, wait with them, report the plate) and each person decides by their hidden
  traits; lifting the arm for anyone is never right. The keeper shows the driver the clear flag (or stops the train
  when the crossing cannot be cleared in time), watches the whole train go by (smoke, an open door, the tail lamp),
  reports what is wrong, asks the station whether another train is due before opening, and writes the log truthfully.
  Delays are radioed in the middle: with the station's word the arm may be lifted while the train is held;
* ``patrol``: walk the section Km 7–8: loose bolts, cracked sleepers, washed-out ballast, a cracked rail, a dark
  signal, rubbish, bà Bông's chilli on the rails… Fix what is the keeper's to fix, protect what is dangerous (red flags
  both ways) and report each finding through the right form; a dangerous one also by an emergency call.

Around the work: surprises (kit desk), situations (sit_ engine), and the chuyện oái oăm of the people around the job
(game/careers/air_odd.py with this career's scripts): flirting, harassment at the crossing, bosses who want the log
"tidied", colleagues who want the hand-over signed blind, extra night shifts. Night shifts tire the keeper (fatigue);
tired, they must wake themselves up before taking an order, and earn half the bonus.

Safety is always the right choice. Mistakes go through consequences.slip; money only through the engine's money().
Everything random is rolled from (day, slot) or the task id: the same moves always end the same way.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import air_odd as ao
from . import street_folk as folk
from .. import consequences as cq
from .. import archive as ar
from . import railway_content as RC
from .railway_content import (PEOPLE, TRAIN, DIRS, EQUIP, EQUIP_IDS, FORMS, FAULTS, HANDOVER, CROWD, CLEAR, CLEARED,
                              ANSWERS, PUSH, PUSH_INDEX, POINTS, PATROL_FORMS, HANDLE, FINDS, LOCALS, REMARKS, DEFECTS, INTRO,
                              REG_STORY, DESK, SITUATIONS, ODD, SAU, HANH, QUY, KHAI)

ID = 'railway'
GEN = 1

HOURS = (5 * 60 + 30, 21 * 60 + 30)   # nhận ca 05:30; the last train of a day shift is through by 21:00
LOWER_AT = 3          # close when the train is at most this many minutes away (Nội quy gác chắn, a game rule)
EARLY_AT = LOWER_AT + 1   # closing with more than this left keeps the street waiting for nothing
BELL_LEAD = 1         # the bell rings at least a minute before the arms come down
HOLD_STOP = 6         # minutes a train stopped short of the crossing loses
RECALL_AT = 6         # a held train set off again: the station calls this many minutes out
MAX_WAIT = 40
LOG_MAX = 12
BONUS = 10

MODS = [
    dict(id='normal', emoji='🌤️', label='Ngày thường', hint='Tàu đều, xe đều. Hạ chắn đúng lúc: khoảng ba phút trước khi tàu tới, sớm quá là dân sốt ruột.', weight=3),
    dict(id='night', emoji='🌙', label='Ca chiều tối', hint='Tàu qua lúc chạng vạng và buổi tối: đèn cầm tay thay cờ, trắng là đường thông, đỏ là dừng. Buồn ngủ thì rửa mặt cho tỉnh.',
         min_day=2, weight=1),
    dict(id='rain', emoji='⛈️', label='Mưa lớn', hint='Đường trơn, nhìn kém. Đi tuần để ý đá ba-lát trôi, cống ngập.', min_day=2, weight=2),
    dict(id='rush', emoji='🎏', label='Cao điểm lễ', hint='Xe đông gấp đôi, ai cũng vội, người chen chắn nhiều: giữ chắn, nói rõ còn mấy phút.', min_day=3, weight=2),
    dict(id='heat', emoji='🌡️', label='Nắng gắt', hint='Ray giãn nở, người nóng tính. Đi tuần soi kỹ đoạn đường cong.', min_day=3, weight=1),
]
MOD = {m['id']: m for m in MODS}

KINDS = ('shift', 'train', 'patrol')
DAY_TIMES = (None, 7 * 60 + 40, 11 * 60 + 15, 15 * 60 + 5, 17 * 60 + 35, 19 * 60 + 10, 20 * 60 + 20)
NIGHT_TIMES = (None, 17 * 60 + 50, 19 * 60 + 5, 20 * 60 + 10, 20 * 60 + 45, 21 * 60 + 5, 21 * 60 + 20)

# The words of the encounters (air_odd): who to bring in, the office, the rank lost on a demotion.
CFG = dict(crew='Báo chú Sáu', company='Báo cung trưởng', union='Nhờ công đoàn xí nghiệp', office='Đội trưởng', demoted='gác chắn tập sự',
           title='gác chắn chính', harass_note='🛡️ Báo là đúng: xí nghiệp có quy trình bảo vệ người đang trực gác.', ground_line='⚖️ Đội trưởng: tạm đình chỉ gác hết hôm nay, mai lên đội trình bày.',
           demote_line='⚖️ Hội đồng kỷ luật xí nghiệp: hạ xuống {demoted}, tạm đình chỉ gác hôm nay, thưởng ca về 0 tới khi hồ sơ sạch lại.')


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _clock(m: int) -> str:
    m %= 24 * 60
    return f'{m // 60:02d}:{m % 60:02d}'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def daily_task_count(day: int) -> int:
    """The hand-over and three jobs (day one: the hand-over and two trains)."""
    return 3 if day == 1 else 4


# ================================================================ tasks
def _kind(day: int, slot: int, mod: str) -> str:
    if slot == 0:
        return 'shift'
    if day >= 2 and slot == 2 and (day % 2 == 0 or mod in ('rain', 'heat')):
        return 'patrol'
    return 'train'


def _weighted(r, rows: list) -> dict:
    total = sum(x.get('weight', 1) for x in rows)
    pick = r.random() * total
    for x in rows:
        pick -= x.get('weight', 1)
        if pick < 0:
            return x
    return rows[-1]


def _train_of(day: int, slot: int) -> dict:
    """The train due in this slot (pure: the hand-over board lists the same trains the slots will bring)."""
    mod = mod_of(day)['id']
    r = kit.rng(ID, 'train', day, slot)
    kinds = ['se', 'dp'] if day == 1 else ['se', 'tn', 'dp', 'h', 'h' if mod == 'night' else 'se']
    spec = TRAIN[kinds[r.randrange(len(kinds))] if day > 1 else kinds[(slot - 1) % 2]]
    num = r.randint(1, 19) if spec['id'] != 'h' else r.randint(1, 29)
    times = NIGHT_TIMES if mod == 'night' else DAY_TIMES
    base = times[min(slot, len(times) - 1)] + 22 * max(0, slot - len(times) + 1)
    at = base + r.randint(-6, 6)
    eta = 7 if day == 1 else r.randint(6, 8)
    return dict(id=spec['id'], code=f'{spec["code"]}{num}', name=spec['name'], emoji=spec['emoji'], kind=spec['kind'],
                cars=r.randint(*spec['cars']), dir=DIRS[num % 2], at=_clock(at), dep=_clock(at - eta), track=1 + (num % 3 == 0), eta=eta)


def _readback(r, tr: dict) -> tuple:
    """Three ways to read the order back: the right one and two that mishear a number."""
    right = f'{tr["code"]}, rời Bến Gỗ {tr["dep"]}, qua đường ngang {tr["at"]}. Rõ.'
    code = tr['code']
    digits = ''.join(ch for ch in code if ch.isdigit())
    other = str(int(digits) + (1 if int(digits) % 2 else 3)) if digits else '1'
    h, m = map(int, tr['at'].split(':'))
    wrong_time = _clock(h * 60 + m + 10)
    opts = [right, f'{code[:len(code) - len(digits)]}{other}, rời Bến Gỗ {tr["dep"]}, qua đường ngang {tr["at"]}. Rõ.',
            f'{code}, rời Bến Gỗ {tr["dep"]}, qua đường ngang {wrong_time}. Rõ.']
    order = [0, 1, 2]
    r.shuffle(order)
    return [opts[i] for i in order], order.index(0)


def _crowd(r, day: int, slot: int, mod: str) -> list:
    if day == 1:
        return [['selfie'], ['stalled']][(slot - 1) % 2]
    pool = [k for k in CROWD if not (mod in ('rain', 'night') and k in ('chili', 'chairs', 'selfie'))
            and not (mod != 'night' and k == 'drunk' and r.random() < 0.5)]
    n = r.choice((0, 1, 1, 2) if mod != 'rush' else (1, 2, 2))
    out = []
    while len(out) < n and pool:
        k = pool[r.randrange(len(pool))]
        pool.remove(k)
        out.append(k)
    return out


def _pushers(r, day: int, slot: int, mod: str, crowd: list) -> list:
    """Who comes up to the lowered barrier, and how many minutes after it came down."""
    if day == 1:
        return [] if slot == 1 else [['grab', 1]]
    pool = [x for x in PUSH if x['min_day'] <= day and (not x['mods'] or mod in x['mods']) and not (x['id'] == 'drunk' and 'drunk' in crowd)]
    n = r.choice((2, 3, 3, 4) if mod != 'rush' else (4, 4, 5))
    offsets = [0, 1, 2, 4, 6][:n]
    out = []
    for at in offsets:
        if not pool:
            break
        x = _weighted(r, pool)
        pool = [y for y in pool if y['id'] != x['id']]
        out.append([x['id'], at])
    return out


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)['id']
    kind = _kind(day, slot, mod)
    if kind == 'shift':
        board = []
        for sl in range(1, daily_task_count(day)):
            if _kind(day, sl, mod) == 'train':
                x = _train_of(day, sl)
                board.append(dict(code=x['code'], at=x['at'], dir=x['dir'], name=x['name'], emoji=x['emoji']))
        r = kit.rng(ID, 'shift', day)
        fault = None if day == 1 else list(FAULTS)[r.randrange(len(FAULTS))] if r.random() < 0.75 else None
        needs = dict(shift=True, board=board, handover=HANDOVER[r.randrange(len(HANDOVER))],
                     note='Thử lần lượt từng thứ, thấy hỏng thì xử lý và báo đúng nơi rồi mới ký nhận ca.')
        return kit.base_task(ID, day, slot, serial, SAU, 'Nhận ca, kiểm tra thiết bị',
                             'Chú Sáu đưa cuốn sổ giao ca: “Đọc sổ, thử từng thứ một. Chưa thử thì đừng ký, con ạ.”',
                             kind='shift', needs=needs, _fault=fault, gen=GEN, checked=[], found=None, fixed=False, forms=[], story=None)
    if kind == 'patrol':
        r = kit.rng(ID, 'patrol', day, slot)
        pts = [dict(p) for p in POINTS]
        r.shuffle(pts)
        pts = sorted(pts[:5], key=lambda p: p['id'])
        finds = {}
        pool = [k for k, v in FINDS.items() if k != 'ok' and (not v.get('mods') or mod in v['mods'])]
        danger = [k for k in pool if FINDS[k]['danger']]
        for i, p in enumerate(pts):
            roll = r.random()
            used = set(finds.values())
            if i == 2 and mod in ('rain', 'heat'):
                finds[p['id']] = 'ballast' if mod == 'rain' else 'buckle'
            elif roll < 0.32:
                finds[p['id']] = 'ok'
            elif roll < 0.42 and [k for k in danger if k not in used]:
                left = [k for k in danger if k not in used]
                finds[p['id']] = left[r.randrange(len(left))]
            else:
                safe = [k for k in pool if not FINDS[k]['danger'] and k not in used] or ['ok']
                finds[p['id']] = safe[r.randrange(len(safe))]
        needs = dict(patrol=True, section='Km 7+000 → Km 8+100', points=pts,
                     note='Đi hết từng điểm. Tự xử lý việc của mình, chỗ nguy hiểm thì phòng vệ và điện khẩn, ghi đúng loại phiếu.')
        return kit.base_task(ID, day, slot, serial, KHAI, 'Tuần đường Km 7 – Km 8',
                             'Anh Khải đưa cái búa nhỏ với cuốn sổ tuần đường: “Đi chậm, nhìn kỹ. Bu lông, tà vẹt, đá, đèn. Chỗ nào cũng phải tới.”',
                             kind='patrol', needs=needs, _finds=finds, gen=GEN, walked=[], handled={}, pforms={}, story=None)
    tr = _train_of(day, slot)
    r = kit.rng(ID, 'train-extra', day, slot)
    opts, rb = _readback(r, tr)
    crowd = _crowd(r, day, slot, mod)
    push = _pushers(r, day, slot, mod, crowd)
    late = 0 if day == 1 else (r.choice((10, 15, 20)) if r.random() < (0.35 if mod == 'rush' else 0.25) else 0)
    second = None
    if day >= 2 and r.random() < 0.22:
        num = r.randint(2, 28) // 2 * 2
        second = dict(code=f'H{num}', gap=2)
    tail = True if day == 1 else not (r.random() < (0.12 if tr['kind'] == 'hang' else 0.05))
    defect = None
    if day >= 2 and r.random() < 0.12:
        defect = dict(kind=['hot', 'door', 'drag'][r.randrange(3)], n=r.randint(2, max(2, tr['cars'] - 1)))
    npc = QUY if day >= 3 and slot == 3 else HANH
    needs = dict(train=tr, eta=tr['eta'], readback=opts, night=mod == 'night', crowd=crowd, push=push,
                 note=f'Hạ chắn khi tàu còn khoảng {LOWER_AT} phút, chuông đèn bật trước. Chắn đã hạ thì không mở cho ai.')
    title = f'Tàu {tr["code"]} {tr["dir"]} · {tr["at"]}'
    opening = f'📻 Bộ đàm rè rè: “Đường ngang Bến Mây, ga Bến Mây gọi. Có tàu {tr["code"]}, nghe rõ trả lời.”'
    left = list(crowd)
    pushers = [dict(id=p, at=at, state='wait', round=0, out=None) for p, at in push]
    return kit.base_task(ID, day, slot, serial, npc, title, opening, kind='train', needs=needs, _rb=rb, _late=late, _second=second,
                         _tail=tail, _defect=defect, gen=GEN, rb=False, rb_tries=0, eta=None, bell=None, arm='up', down_at=None, down_min=0,
                         scanned=False, left=left, progress={}, flag=None, stopped=False, standing=False, pushers=pushers, late_told=False,
                         held=False, recalled=False, reopened=0, passed=False, watched=False, radioed=[], asked=False, second='none',
                         reported=[], sneaks=[], remarks=None, early=0, late_min=0, awake=False, story=None)


FIXED = ('needs', '_fault', '_finds', '_rb', '_late', '_second', '_tail', '_defect')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'shift':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


def _bonus(t: dict) -> int:
    """A train seen through by the book: more people to deal with, a little more (fixed from the job)."""
    n = t['needs']
    if t['kind'] == 'patrol':
        return 8 + 3 * sum(FINDS[f]['danger'] for f in t['_finds'].values())
    return BONUS + 2 * len(n['crowd']) + min(6, len(n['push'])) + (4 if t['_late'] else 0) + (3 if t['_second'] else 0)


# ================================================================ the career's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, trains=0, safe=0, held=0, reported=0, stopped=0, patrols=0, finds=0, earned=0)


def initial() -> dict:
    return dict(v=1, intro=False, on_duty=False, crank=False, jam=False, log=[], regulars={}, today=_fresh_today(0),
                stats=dict(trains=0, safe=0, held=0, reported=0, stopped=0, tails=0, defects=0, seconds=0, patrols=0, finds=0, dangers=0, opened=0),
                desk=kit.desk_initial(), odd=ao.initial())


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


def _pressure(c: dict, d: dict) -> int:
    """How hard the depot leans on its keepers today: the season, and a keeper who snapped at the office."""
    marks = d['odd']['marks']
    return {'rush': 2, 'night': 1, 'heat': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


# ================================================================ the actions
FREE = ('rw_intro', 'rw_rest')
NO_TICK = ('rw_intro', 'rw_check', 'rw_fix', 'rw_form', 'rw_readback', 'rw_wake', 'rw_flag', 'rw_radio', 'rw_ask', 'rw_log',
           'rw_pform', 'rw_desk', 'rw_odd', 'rw_rest')
PHYSICAL = ('rw_lower', 'rw_raise', 'rw_walk')
GROUNDED = ('rw_readback', 'rw_walk')   # a keeper stood down takes no new train; one already coming is still seen through safely
SAFE = ('rw_stop', 'rw_clear', 'rw_flag', 'rw_answer', 'rw_wait')   # never blocked by someone talking at the barrier


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'rw_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Chú Sáu đang chờ ở chòi gác.')
    odd = d['odd']
    if name == 'rw_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    desk = d['desk']
    if name == 'rw_desk':
        result = kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'rw_odd':
        result = ao.reply(s, c, ID, odd, ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở chòi gác.')
    if name not in SAFE:
        kit.desk_block(desk, 'Có chuyện ở đường ngang, quyết xong rồi làm tiếp nhé.')
        ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
    kit.need(not (ao.grounded(c, odd) and name in GROUNDED), 'Bạn đang bị tạm đình chỉ gác hết hôm nay. Tan ca, mai lên đội trình bày.', 'grounded')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    """A surprise or an encounter turns up between jobs, never in the middle of a train going by."""
    busy = any(t.get('career') == ID and t.get('kind') == 'train' and t['status'] not in ('completed', 'cancelled', 'referred')
               and t.get('eta') is not None and not t.get('passed') for t in c['tasks'])
    if busy:
        return
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
        return
    _odd_tick(s, c, d, result)


def _odd_tick(s: dict, c: dict, d: dict, result: dict) -> None:
    x = ao.tick(s, c, ID, d['odd'], ODD, busy=d['desk']['ev'] is not None)
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kind: str | None = None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc chòi gác.')
    if kind:
        kit.need(t['kind'] == kind, 'Thao tác này không dành cho việc đang làm.')
    return t


def _slip(t: dict, code: str, sev: int, text: str, note: str, safety: bool = False) -> None:
    t['mistakes'] += 1
    cq.slip(t, code, sev, text, note, safety=safety)


# ---------------------------------------------------------------- the hand-over
def _check(s, c, d, p):
    t = _task(c, p, 'shift')
    item = kit.one_of(p.get('item'), EQUIP_IDS, 'Thiết bị không có trong chòi.')
    kit.need(item not in t['checked'], 'Đã kiểm tra thứ này rồi.')
    kit.start_work(t)
    t['checked'].append(item)
    x = next(e for e in EQUIP if e['id'] == item)
    f = t['_fault']
    if f and FAULTS[f]['item'] == item:
        t['found'] = f
        return dict(message=f'{x["emoji"]} {x["test"]}: ⚠️ {FAULTS[f]["text"]}', correct=True)
    return dict(message=f'{x["emoji"]} {x["test"]}: {x["ok"]}')


def _fix(s, c, d, p):
    t = _task(c, p, 'shift')
    kit.need(t['found'], 'Chưa thấy gì hỏng để xử lý.')
    f = FAULTS[t['found']]
    kit.need(f['fix'], 'Cái này mình không tự xử lý được: báo đúng nơi để thợ cung tới sửa.')
    kit.need(not t['fixed'], 'Đã xử lý rồi.')
    t['fixed'] = True
    if t['found'] == 'motor':
        d['crank'] = True
    return dict(message=f'🔧 {f["fix"]}. {f["why"]}')


def _form(s, c, d, p):
    t = _task(c, p, 'shift')
    kit.need(t['found'], 'Chưa thấy gì hỏng để báo.')
    form = kit.one_of(p.get('form'), FORMS, 'Không có loại phiếu này.')
    if form in t['forms']:
        t['forms'].remove(form)
        return dict(message=f'Bỏ {_lower(FORMS[form]["name"])}.')
    t['forms'].append(form)
    line = {'giao_ca': '📒 Ghi vào sổ giao ca, ký tên, ghi giờ.', 'phieu': '🧾 Điền phiếu báo hỏng, gửi cung đường qua tàu địa phương.',
            'ga': '📞 Gọi ga: chị Nguyệt ghi nhận, sẽ dặn lái tàu chú ý đường ngang Bến Mây.'}[form]
    return dict(message=line)


def _sign(s, c, d, p):
    t = _task(c, p, 'shift')
    kit.start_work(t)
    missing = [e for e in EQUIP if e['id'] not in t['checked']]
    f = t['_fault']
    if missing:
        _slip(t, 'unchecked', 2, f'Ký nhận ca mà chưa thử {", ".join(_lower(e["name"]) for e in missing)}.', 'ký nhận ca khi chưa thử hết')
        if f and not t['found'] and FAULTS[f]['danger']:
            _slip(t, 'hidden_fault', 3, f'{FAULTS[f]["text"]} Không ai biết cho tới khi tàu tới.', 'bỏ sót thiết bị hỏng', safety=True)
    if t['found']:
        x = FAULTS[t['found']]
        if x['fix'] and not t['fixed']:
            _slip(t, 'unfixed', 2 if x['danger'] else 1, f'Thấy hỏng mà chưa xử lý: {_lower(x["text"])}', 'chưa xử lý chỗ hỏng')
        if x['danger'] and 'ga' not in t['forms']:
            _slip(t, 'no_station', 3, 'Thiết bị đường ngang hỏng mà không báo ga, lái tàu không được dặn chú ý.', 'không báo ga', safety=True)
        miss = [k for k in x['forms'] if k != 'ga' and k not in t['forms']]
        if miss:
            _slip(t, 'no_form', 1, f'Chưa {_lower(FORMS[miss[0]]["name"])}: ca sau, tổ thợ không ai biết.', 'báo chưa đúng nơi')
    d['jam'] = bool(f == 'motor' and not t['fixed'])
    d['on_duty'] = True
    ok = not cq.slips(t)
    _finish(s, c, d, t, 0, 'Nhận ca, ký sổ giao ca.')
    extra = ''
    if t['found'] and 'ga' in t['forms'] and not FAULTS[t['found']]['danger']:
        extra = ' Chị Nguyệt: “Cái này ghi sổ là được rồi em, nhưng báo thế chị cũng yên tâm.”'
    return dict(message=('✍️ Ký nhận ca. Chú Sáu gật gù: “Thử kỹ vậy mới yên tâm.”' if ok else '✍️ Ký nhận ca. Chú Sáu nhíu mày: “Ký là nhận trách nhiệm đấy con.”') + extra,
                celebrate=ok)


def _need_duty(d: dict) -> None:
    kit.need(d['on_duty'], 'Nhận ca, ký sổ giao ca trước đã nhé.')


# ---------------------------------------------------------------- a train: the clock
def _live(t: dict) -> None:
    kit.need(t['eta'] is not None, 'Nhắc lại lệnh của ga trước đã.')


def _talking(t: dict) -> dict | None:
    return next((x for x in t['pushers'] if x['state'] == 'on'), None)


def _need_calm(t: dict) -> None:
    kit.need(_talking(t) is None, 'Có người đang đòi qua chắn: trả lời họ trước đã.')


def _advance(s: dict, c: dict, d: dict, t: dict, minutes: int, stop_on_event: bool = False) -> list:
    """Let the minutes go by: the train comes closer, people come up to the barrier, the station calls."""
    notes = []
    for _ in range(max(0, minutes)):
        if t['eta'] is None or t['passed'] or t['standing']:
            break
        t['eta'] -= 1
        if t['arm'] == 'down':
            t['down_min'] += 1
        n = _events(t)
        notes += n
        if t['eta'] <= 0:
            notes.append(_arrive(s, c, d, t))
            break
        if stop_on_event and n:
            break
    return notes


def _events(t: dict) -> list:
    notes = []
    tr = t['needs']['train']
    if t['_late'] and not t['late_told'] and ((t['arm'] == 'down' and t['down_min'] >= 1) or t['eta'] <= 2):
        t['late_told'] = True
        t['eta'] += t['_late']
        t['late_min'] += t['_late']
        for k in ('bell', 'down_at'):
            if t[k] is not None:
                t[k] += t['_late']
        notes.append(f'📻 Chị Nguyệt: “Đường ngang Bến Mây, tàu {tr["code"]} còn đứng ở ga Bến Gỗ, chậm thêm {t["_late"]} phút. Nhắc lại.”')
    if t['late_told'] and not t['recalled'] and t['eta'] <= RECALL_AT:
        t['recalled'] = True
        t['held'] = False
        notes.append(f'📻 Chị Nguyệt: “Tàu {tr["code"]} đã chạy khỏi Bến Gỗ, còn {t["eta"]} phút tới đường ngang. '
                     + ('Chuẩn bị đóng chắn.”' if t['arm'] == 'up' else 'Giữ chắn.”'))
    if t['arm'] == 'down':
        for x in t['pushers']:
            if x['state'] == 'wait' and t['down_min'] >= x['at']:
                x['state'] = 'on'
                px = PUSH_INDEX[x['id']]
                notes.append(f'{px["emoji"]} {px["who"].split(" · ")[0]}: {px["line"]}')
                break   # one at a time
    return notes


def _arrive(s: dict, c: dict, d: dict, t: dict) -> str:
    tr = t['needs']['train']
    t['eta'] = 0
    for x in t['pushers']:
        if x['state'] in ('wait', 'on'):
            x.update(state='done', out=x['out'] or 'waited')
    if t['stopped']:
        t['standing'] = True
        return f'🟥 Tàu {tr["code"]} phanh dừng cách đường ngang ba trăm mét, chờ bạn báo đường đã thông.'
    protected = t['arm'] == 'down' and not t['left']
    if not protected:
        if t['arm'] != 'down':
            _slip(t, 'unprotected', 3, f'Tàu {tr["code"]} tới mà cần chắn chưa hạ. Lái tàu kéo phanh khẩn cấp, xe máy phanh cháy lốp.', 'tàu tới khi chắn chưa hạ', safety=True)
        else:
            _slip(t, 'on_rails', 3, f'Tàu {tr["code"]} tới mà trên ray vẫn còn người. Lái tàu kéo còi, phanh khẩn cấp, may họ nhảy ra kịp.', 'tàu tới khi trên ray còn người', safety=True)
        t['left'] = []
        t['progress'] = {}
    elif t['flag'] != 'green':
        _slip(t, 'no_flag', 1, 'Lái tàu không thấy cờ báo đường thông, phải giảm tốc qua đường ngang.', 'không đứng cờ đón tàu')
    t['passed'] = True
    line = f'🚆 Tàu {tr["code"]} {tr["cars"]} toa ầm ầm qua đường ngang. Gió tàu thốc tung vạt áo.'
    return line + (' Nhìn kỹ đoàn tàu nhé.' if protected else '')


# ---------------------------------------------------------------- a train: the order
def _readback_act(s, c, d, p):
    t = _task(c, p, 'train')
    _need_duty(d)
    kit.need(t['known'], 'Nghe ga gọi bộ đàm trước đã.')
    kit.need(not t['rb'], 'Đã nhắc lại lệnh rồi.')
    if d['odd']['fatigue'] >= ao.TIRED and not t['awake']:
        kit.need(False, 'Mắt díp lại rồi: rửa mặt, đi lại cho tỉnh rồi hãy nghe lệnh.', 'tired')
    pick = kit.integer(p.get('option'), 0, len(t['needs']['readback']) - 1)
    kit.start_work(t)
    tr = t['needs']['train']
    if pick != t['_rb']:
        t['rb_tries'] += 1
        _slip(t, 'readback', 1, 'Nhắc lại lệnh sai, ga phải đọc lại lần nữa.', 'nhắc lại lệnh sai')
        return dict(message=f'📻 Chị Nguyệt: “Sai! Nghe lại: tàu {tr["code"]}, rời Bến Gỗ {tr["dep"]}, qua đường ngang {tr["at"]}. Nhắc lại cho đúng.”', correct=False)
    t['rb'] = True
    if t['eta'] is None:
        t['eta'] = t['needs']['eta']
    return dict(message=f'📻 Bạn: “{t["needs"]["readback"][pick]}” · Chị Nguyệt: “Đúng. Đường ngang Bến Mây chuẩn bị.” Tàu còn khoảng {t["eta"]} phút.')


def _wake(s, c, d, p):
    t = _task(c, p, 'train')
    kit.need(not t['awake'], 'Bạn đang tỉnh như sáo rồi.')
    t['awake'] = True
    return dict(message='🚰 Bạn vốc nước lạnh lên mặt, đi quanh chòi hai vòng, vươn vai. Tỉnh hẳn.')


def _warn(s, c, d, p):
    t = _task(c, p, 'train')
    _live(t)
    _need_calm(t)
    kit.need(not t['passed'], 'Tàu qua rồi.')
    kit.need(t['bell'] is None, 'Chuông đèn đang kêu rồi.')
    t['bell'] = t['eta']
    notes = _advance(s, c, d, t, 1)
    return dict(message=' '.join(['🔔 Bật chuông, hai cụm đèn đỏ nhấp nháy. Xe cộ chậm lại trước vạch dừng.'] + notes))


def _scan(s, c, d, p):
    t = _task(c, p, 'train')
    _live(t)
    _need_calm(t)
    kit.need(not t['scanned'], 'Đã nhìn đường ngang rồi.')
    t['scanned'] = True
    who = [CROWD[k]['name'] for k in t['left'] if k in CROWD]
    notes = _advance(s, c, d, t, 1)
    head = ('👀 Nhìn hai phía đường ngang: ' + '; '.join(who) + '. Dẹp hết rồi mới hạ chắn.') if who else '👀 Nhìn hai phía đường ngang: không còn ai, không còn gì trên ray.'
    return dict(message=' '.join([head] + notes))


def _crowd_of(key: str) -> dict:
    if key.startswith('sneak:'):
        px = PUSH_INDEX.get(key[6:], {})
        return dict(emoji=px.get('emoji', '🏃'), name=f'{px.get("who", "Người chui chắn").split(" · ")[0]} chui qua chắn, đứng giữa ray',
                    works=['go'], steps=1, miss='Người đó vẫn đứng giữa ray, mặt tỉnh bơ.')
    return CROWD[key]


def _clear(s, c, d, p):
    t = _task(c, p, 'train')
    _live(t)
    kit.need(t['scanned'] or any(k.startswith('sneak:') for k in t['left']), 'Nhìn đường ngang trước đã.')
    who = kit.one_of(p.get('who'), t['left'], 'Trên ray không còn ai như vậy.')
    how = kit.one_of(p.get('how'), CLEAR, 'Chọn cách dẹp.')
    x = _crowd_of(who)
    kit.start_work(t)
    if how not in x['works']:
        notes = _advance(s, c, d, t, 1)
        return dict(message=' '.join([f'{CLEAR[how]["emoji"]} {x["miss"]} Cách này không ăn thua.'] + notes), correct=False)
    t['progress'][who] = t['progress'].get(who, 0) + 1
    if t['progress'][who] < x['steps']:
        notes = _advance(s, c, d, t, 1)
        return dict(message=' '.join([f'{CLEAR[how]["emoji"]} {x["name"]}: được một nửa rồi, thêm chút nữa!'] + notes))
    t['left'].remove(who)
    t['progress'].pop(who, None)
    line = CLEARED.get(who) or f'Bạn kéo {x["name"].split(" chui")[0]} ra sau vạch dừng, ghi tên vào sổ người vượt chắn.'
    notes = _advance(s, c, d, t, 1) if not t['standing'] else []
    return dict(message=' '.join([f'{CLEAR[how]["emoji"]} {line}'] + notes), celebrate=not t['left'])


def _lower_act(s, c, d, p):
    t = _task(c, p, 'train')
    _live(t)
    _need_calm(t)
    kit.need(t['arm'] == 'up', 'Cần chắn đang hạ rồi.')
    kit.need(not t['passed'], 'Tàu qua rồi, không cần hạ nữa.')
    kit.need(not d['jam'], 'Cần chắn kẹt mô-tơ: lắp tay quay trước đã (ở phần nhận ca hoặc tủ dụng cụ).', 'jam')
    kit.start_work(t)
    tr = t['needs']['train']
    notes = []
    if not t['scanned']:
        if t['left']:
            _slip(t, 'trapped', 2, 'Hạ chắn mà không nhìn đường ngang: người còn kẹt giữa hai cần chắn.', 'hạ chắn khi chưa nhìn đường ngang', safety=True)
        else:
            _slip(t, 'no_look', 1, 'Hạ chắn mà không nhìn hai phía đường ngang.', 'không nhìn trước khi hạ')
    elif t['left']:
        _slip(t, 'trapped', 2, 'Hạ chắn khi trên ray vẫn còn người, họ bị kẹt giữa hai cần chắn.', 'hạ chắn khi trên ray còn người', safety=True)
    if t['bell'] is None:
        _slip(t, 'no_bell', 2, 'Hạ chắn không bật chuông đèn, một xe máy lao thẳng vào cần chắn.', 'hạ chắn không báo trước', safety=True)
    elif t['bell'] - t['eta'] < BELL_LEAD:
        _slip(t, 'short_bell', 1, 'Chuông vừa kêu đã sập chắn, người đi đường giật nảy mình.', 'chuông đèn chưa đủ thời gian')
    if t['eta'] <= 1 and not t['stopped']:
        _slip(t, 'late_close', 2, f'Tàu {tr["code"]} gần sát mới hạ chắn, xe phanh rít cả dãy.', 'hạ chắn muộn', safety=True)
    early = t['eta'] - LOWER_AT if t['eta'] > EARLY_AT + d['crank'] and not t['late_told'] else 0
    t['early'] = max(t['early'], early)
    t['arm'] = 'down'
    t['down_at'] = t['eta']
    head = '🚧 Cần chắn hạ xuống, khóa chốt. Xe cộ dồn lại sau vạch dừng.'
    if d['crank']:
        head = '🚧 Bạn quay tay, cần chắn hạ chậm rì rì, khóa chốt.'
    if early:
        head += f' Còn {t["eta"]} phút tàu mới tới: hạ sớm quá, dân sẽ sốt ruột.'
    notes += _advance(s, c, d, t, 2 if d['crank'] else 1)
    return dict(message=' '.join([head] + notes))


def _flag(s, c, d, p):
    t = _task(c, p, 'train')
    _live(t)
    color = kit.one_of(p.get('color'), ('green', 'red'), 'Chọn cờ.')
    kit.need(not t['passed'], 'Tàu qua rồi.')
    if color == 'red':
        return _stop(s, c, d, p)
    kit.need(t['arm'] == 'down', 'Hạ chắn trước rồi mới báo đường thông.')
    kit.need(not t['left'], 'Trên ray còn người: chưa báo đường thông được. Dẹp ngay, hoặc báo dừng tàu.')
    kit.need(t['flag'] != 'green', 'Đang đứng cờ báo đường thông rồi.')
    t['flag'] = 'green'
    lamp = 'Giơ đèn trắng' if t['needs']['night'] else 'Giơ cờ xanh'
    return dict(message=f'🟩 {lamp}, đứng nghiêm bên chòi, mắt nhìn về phía tàu tới.')


def _stop(s, c, d, p):
    """Stop the train short of the crossing: always allowed, always safe."""
    t = _task(c, p, 'train')
    _live(t)
    kit.need(not t['passed'], 'Tàu qua rồi.')
    kit.need(not t['stopped'], 'Đã báo dừng tàu rồi.')
    tr = t['needs']['train']
    t['stopped'] = True
    t['flag'] = 'red'
    t['late_min'] += HOLD_STOP
    needless = not t['left'] and t['arm'] == 'down'
    lamp = 'đèn đỏ' if t['needs']['night'] else 'cờ đỏ'
    msg = f'🟥 Bạn gọi ga: “Dừng tàu {tr["code"]}, đường ngang có vật cản!” rồi cầm {lamp} chạy về phía tàu tới.'
    if needless:
        msg += ' (Trên ray không có gì: lần sau đường thông thì cứ đứng cờ xanh.)'
    notes = _advance(s, c, d, t, 1)
    return dict(message=' '.join([msg] + notes))


def _allclear(s, c, d, p):
    t = _task(c, p, 'train')
    kit.need(t['standing'], 'Tàu không đứng chờ.')
    kit.need(not t['left'], 'Trên ray còn người, chưa báo thông được.')
    kit.need(t['arm'] == 'down', 'Hạ chắn đã rồi mới cho tàu qua.')
    tr = t['needs']['train']
    t['standing'] = False
    t['passed'] = True
    return dict(message=f'📻 Bạn báo ga: “Đường ngang đã thông.” Tàu {tr["code"]} kéo còi, chạy chậm qua đường ngang. Nhìn kỹ đoàn tàu nhé.')


def _wait(s, c, d, p):
    t = _task(c, p, 'train')
    _live(t)
    _need_calm(t)
    kit.need(not t['passed'] and not t['standing'], 'Tàu không còn tới nữa.' if t['passed'] else 'Tàu đang đứng chờ bạn báo đường thông.')
    hum = LOWER_AT + 1 + d['crank']        # the hand crank is a minute slower: the keeper starts a minute earlier
    if t['arm'] == 'up' and t['eta'] > hum:
        # Waiting with the arms up: the rails start to hum about four minutes out (the keeper's ear, or the station).
        notes = []
        while t['eta'] > hum and not notes and not t['passed']:
            notes = _advance(s, c, d, t, 1)
        if not notes and not t['passed']:
            notes = [f'〰️ Ray bắt đầu rung nhè nhẹ: tàu còn khoảng {t["eta"]} phút.']
        return dict(message=' '.join(['⏳ Bạn đứng chờ ở cửa chòi.'] + notes))
    notes = _advance(s, c, d, t, MAX_WAIT if t['arm'] == 'down' or t['stopped'] else 1, stop_on_event=True)
    return dict(message=' '.join(['⏳ Bạn đứng cạnh chòi, tay cầm cờ, mắt nhìn về phía tàu tới.'] + notes))


# ---------------------------------------------------------------- a train: the people at the barrier
def _push_react(tr: dict, px: dict, answer: str, rnd: int, eta: int) -> str:
    """How someone at the barrier takes the answer (pure: traits rolled from the job and the person)."""
    score = 2 if answer in px['best'] else 1 if answer in px['ok'] else -1 if answer in px['bad'] else 0
    if px['soft'] and answer == 'report':
        score -= 1
    heat = tr['rude'] // 25 + tr['proud'] // 40 + (1 if tr['mood'] < 35 else 0)
    calm = tr['honest'] // 40 + tr['savvy'] // 50
    v = 2 * score + calm - heat + rnd
    if answer == 'report' and tr['proud'] >= 75 and not px['soft']:
        return 'blowup'
    if v >= 2:
        return 'ok'
    if v >= 0:
        return 'sulk'
    if rnd == 0:
        return 'again'
    return 'sneak' if px['sneaky'] and eta >= 2 else 'sulk'


def _answer(s, c, d, p):
    t = _task(c, p, 'train')
    x = next((r for r in t['pushers'] if r['id'] == p.get('who') and r['state'] == 'on'), None)
    kit.need(x, 'Không có ai đang đòi qua.')
    answer = kit.one_of(p.get('answer'), ANSWERS, 'Chọn cách trả lời.')
    px = PUSH_INDEX[x['id']]
    who = px['who'].split(' · ')[0]
    if answer == 'open':
        x.update(state='done', out='opened')
        d['stats']['opened'] += 1
        _slip(t, 'opened', 3, f'Gác chắn nâng chắn cho {who} qua khi tàu đang tới.', 'mở chắn khi tàu sắp tới', safety=True)
        note = ao.penalize(c, d['odd'], 2, CFG)
        notes = _advance(s, c, d, t, 1)
        return dict(message=' '.join([f'⚠️ {RC.PUSH_OPEN.format(who=who)} {note}'] + notes), correct=False)
    tr = folk.traits(f'{t["id"]}|{x["id"]}', PEOPLE[px['npc']][3] if px['npc'] is not None else None)
    how = _push_react(tr, px, answer, x['round'], t['eta'])
    if answer == 'report' and how != 'again':
        if x['id'] not in t['reported']:
            t['reported'].append(x['id'])
    if px['soft'] and answer == 'report':
        cq.slip(t, 'cruel', 1, 'Ghi biển số người đang lo việc hiếu, việc bệnh: đúng luật mà nặng tay.', 'nặng tay với người đang khổ')
    if how == 'again':
        x['round'] = 1
        notes = _advance(s, c, d, t, 1)
        return dict(message=' '.join([f'{px["emoji"]} {who}: {px["again"]}'] + notes))
    if how == 'sneak':
        x.update(state='done', out='sneak')
        t['left'].append(f'sneak:{x["id"]}')
        t['sneaks'].append(x['id'])
        notes = _advance(s, c, d, t, 1)
        return dict(message=' '.join([f'🏃 {RC.PUSH_SNEAK.format(who=who)} Kéo người đó ra ngay, hoặc báo dừng tàu!'] + notes), correct=False)
    x.update(state='done', out=how)
    if how == 'blowup':
        line = RC.PUSH_BLOWUP.format(who=who)
        if px['npc'] is not None:
            kit.review(s, c, kit.npc_id(ID, px['npc']), 2, 'Ghi biển số hàng xóm như bắt tội phạm. Làm căng quá.', t['id'])
    elif how == 'ok':
        line = RC.PUSH_OK[answer].format(who=who, eta=max(1, t['eta']))
        c['xp'] += 2
    else:
        line = RC.PUSH_SULK.format(who=who)
    if px['soft'] and answer == 'report':
        line = RC.PUSH_SOFT_REPORT.format(who=who)
    notes = _advance(s, c, d, t, 1)
    return dict(message=' '.join([f'{px["emoji"]} {line}'] + notes), correct=how != 'blowup')


# ---------------------------------------------------------------- a train: after it has gone by
def _watch(s, c, d, p):
    t = _task(c, p, 'train')
    kit.need(t['passed'], 'Tàu chưa tới.')
    kit.need(not t['watched'], 'Đã nhìn đoàn tàu rồi.')
    t['watched'] = True
    tr = t['needs']['train']
    rows = [f'👁️ Bạn đếm đủ {tr["cars"]} toa.']
    if t['_defect']:
        x = DEFECTS[t['_defect']['kind']]
        rows.append(f'{x["emoji"]} {x["text"].format(n=t["_defect"]["n"])}')
    rows.append('🏮 Toa cuối có đèn đuôi đỏ sáng.' if t['_tail'] else '🏮 Toa cuối KHÔNG thấy đèn đuôi đâu!')
    if t['_tail'] and not t['_defect']:
        rows.append('Đoàn tàu bình thường.')
    return dict(message=' '.join(rows), correct=True)


def _radio(s, c, d, p):
    t = _task(c, p, 'train')
    what = kit.one_of(p.get('what'), ('tail', 'defect'), 'Báo ga chuyện gì?')
    kit.need(t['watched'], 'Nhìn đoàn tàu trước đã.')
    kit.need(what not in t['radioed'], 'Đã báo ga chuyện này rồi.')
    tr = t['needs']['train']
    if what == 'tail':
        kit.need(not t['_tail'], 'Toa cuối có đèn đuôi mà.')
        line = f'📻 Bạn: “Tàu {tr["code"]} vừa qua Bến Mây không có đèn đuôi.” Chị Nguyệt: “Rõ! Ga dừng tàu kiểm tra ngay.”'
    else:
        kit.need(t['_defect'], 'Đoàn tàu không có gì bất thường.')
        line = f'📻 Bạn: “Tàu {tr["code"]}, toa số {t["_defect"]["n"]} có bất thường.” Chị Nguyệt: “Rõ! Báo lái tàu dừng ở Bến Mây kiểm tra.”'
    t['radioed'].append(what)
    return dict(message=line, celebrate=True)


def _ask(s, c, d, p):
    t = _task(c, p, 'train')
    _live(t)
    tr = t['needs']['train']
    if not t['passed']:
        kit.need(t['late_told'], f'Tàu {tr["code"]} đang tới đúng giờ: giữ chắn.')
        kit.need(not t['held'] and not t['recalled'], 'Ga đã xác nhận rồi.' if t['held'] else f'Tàu {tr["code"]} đã chạy lại rồi: chuẩn bị đóng chắn.')
        if t['eta'] <= RECALL_AT:
            t['recalled'] = True
            return dict(message=f'📻 Chị Nguyệt: “Tàu {tr["code"]} đã chạy khỏi Bến Gỗ rồi, còn {t["eta"]} phút. Giữ chắn!”')
        t['held'] = True
        return dict(message=f'📻 Chị Nguyệt: “Tàu {tr["code"]} còn đứng ở Bến Gỗ, chưa có lệnh chạy. Đường ngang được mở tạm, khi tàu chạy ga gọi lại.”')
    kit.need(not t['asked'], 'Đã hỏi ga rồi.')
    if t['_second'] and t['second'] == 'none':
        t['second'] = 'coming'
        return dict(message=f'📻 Chị Nguyệt: “Còn! Tàu hàng {t["_second"]["code"]} chạy ngược chiều, còn {t["_second"]["gap"]} phút. Giữ nguyên chắn!”', correct=True)
    if t['second'] == 'coming':
        t['second'] = 'passed'
        t['asked'] = True
        return dict(message=f'🚂 Tàu {t["_second"]["code"]} rầm rập qua đường bên kia. 📻 Chị Nguyệt: “Hết tàu. Đường ngang Bến Mây được nâng chắn.”')
    t['asked'] = True
    return dict(message='📻 Chị Nguyệt: “Không còn tàu. Đường ngang Bến Mây được nâng chắn.”')


def _raise(s, c, d, p):
    t = _task(c, p, 'train')
    _live(t)
    if not t['held']:
        _need_calm(t)          # with the station's word the waiting street is glad to go: nobody to answer first
    kit.need(t['arm'] == 'down', 'Cần chắn đang nâng.')
    tr = t['needs']['train']
    kit.start_work(t)
    if not t['passed']:
        # Before the train: only while the station holds it, and with its word.
        if t['held']:
            t.update(arm='up', bell=None, flag=None, reopened=t['reopened'] + 1, down_at=None)
            for x in t['pushers']:
                if x['state'] in ('wait', 'on'):
                    x.update(state='done', out=x['out'] or 'waited')
            notes = _advance(s, c, d, t, 2 if d['crank'] else 1)
            return dict(message=' '.join(['🚧 Ga đã xác nhận tàu còn đứng ở Bến Gỗ: bạn nâng chắn tạm cho xe qua. Khi ga gọi lại thì đóng như từ đầu.'] + notes))
        _slip(t, 'open_due', 3 if not t['late_told'] else 2, f'Nâng chắn khi tàu {tr["code"]} chưa qua, chưa có xác nhận của ga.', 'nâng chắn khi tàu chưa qua', safety=True)
        d['stats']['opened'] += 1
        t.update(arm='up', bell=None, flag=None, down_at=None)
        notes = _advance(s, c, d, t, 1)
        return dict(message=' '.join(['⚠️ Bạn nâng chắn trong khi tàu vẫn đang tới! Xe ùa qua đường ray. Hạ lại ngay!'] + notes), correct=False)
    if not t['watched']:
        _slip(t, 'no_watch', 2, 'Tàu qua mà gác chắn không nhìn đoàn tàu, không biết đoàn tàu có bình thường không.', 'không nhìn đoàn tàu')
    notes = []
    if not t['asked']:
        if t['_second'] and t['second'] != 'passed':
            _slip(t, 'second', 3, f'Vừa nâng chắn thì tàu hàng {t["_second"]["code"]} rúc còi lao tới. Xe máy phanh dúi dụi, bạn hạ chắn khẩn cấp.',
                  'nâng chắn khi còn tàu thứ hai', safety=True)
            t['second'] = 'passed'
            notes.append(f'🚂 Tàu {t["_second"]["code"]} qua sát nút. Tim bạn đập thình thịch.')
        else:
            _slip(t, 'no_confirm', 1, 'Nâng chắn mà không hỏi ga còn tàu nào không.', 'chưa hỏi ga')
    t.update(arm='up', bell=None, down_at=None)
    return dict(message=' '.join(['🚧 Nâng chắn, tắt chuông. Dòng xe ùa qua, có người còn bấm còi cảm ơn.'] + notes))


def _truth(t: dict) -> set:
    out = {'late' if t['late_min'] else 'ontime'}
    if t['reported'] or t['sneaks']:
        out.add('violator')
    if t['stopped']:
        out.add('stopped')
    if not t['_tail']:
        out.add('tail')
    if t['_defect']:
        out.add('defect')
    if t['_second']:
        out.add('second')
    return out


def _log(s, c, d, p):
    t = _task(c, p, 'train')
    kit.need(t['passed'] and t['arm'] == 'up', 'Tàu qua, nâng chắn rồi mới ghi sổ.')
    picks = kit.id_list(p.get('remarks'), REMARKS, max_items=len(REMARKS), message='Chọn dòng ghi sổ.')
    kit.need(picks, 'Chọn ít nhất một dòng ghi sổ.')
    truth = _truth(t)
    tr = t['needs']['train']
    if not t['_tail'] and 'tail' not in t['radioed']:
        _slip(t, 'tail_unreported', 3, f'Tàu {tr["code"]} qua không có đèn đuôi mà gác chắn không báo ga.', 'không báo mất đèn đuôi', safety=True)
    if t['_defect'] and 'defect' not in t['radioed']:
        _slip(t, 'defect_unreported', 2, f'Toa số {t["_defect"]["n"]} tàu {tr["code"]} có bất thường mà không ai báo ga.', 'không báo bất thường của tàu', safety=True)
    if set(picks) != truth:
        _slip(t, 'log', 1, 'Sổ nhật ký ghi không khớp với những gì đã xảy ra.', 'ghi sổ chưa đúng')
    t['remarks'] = list(picks)
    d['stats']['trains'] += 1
    d['today']['trains'] += 1
    safe = not cq.safety(t)
    d['stats']['safe'] += safe
    d['today']['safe'] += safe
    held = sum(1 for x in t['pushers'] if x['out'] in ('ok', 'sulk', 'blowup', 'waited'))
    d['stats']['held'] += held
    d['today']['held'] += held
    d['stats']['reported'] += len(t['reported'])
    d['today']['reported'] += len(t['reported'])
    d['stats']['stopped'] += t['stopped']
    d['today']['stopped'] += t['stopped']
    d['stats']['tails'] += 'tail' in t['radioed']
    d['stats']['defects'] += 'defect' in t['radioed']
    d['stats']['seconds'] += bool(t['_second'])
    if t['needs']['night']:
        d['odd']['fatigue'] = min(ao.FATIGUE_MAX, d['odd']['fatigue'] + 1)
    d['log'] = ar.last(d['log'] + [dict(day=c['day'], code=tr['code'], at=tr['at'], late=t['late_min'], held=held, ok=not cq.slips(t), safe=safe)],
                       LOG_MAX, 'railway.log', c)
    full = 0 if not safe else max(0, _bonus(t) - 3 * cq.points(t))
    reward = ao.bonus(d['odd'], full)
    d['today']['earned'] += reward
    line = f'Tàu {tr["code"]} qua đường ngang Bến Mây' + (f', chậm {t["late_min"]} phút' if t['late_min'] else ', đúng giờ') + '.'
    msg = _finish(s, c, d, t, reward, line)
    head = '📒 Ghi sổ nhật ký, ký tên.' + (f' Thưởng ca {reward} xu.' if reward else '')
    if full and reward < full:
        head += ' (Đang bị hạ bậc: không có thưởng.)' if not reward else ' (Mệt quá: nửa thưởng.)'
    if not safe:
        head += ' 🛡️ Đội sẽ đọc lại chuyến này cùng bạn.'
    note = ao.flown(d['odd'], not cq.slips(t), CFG)
    return dict(message=f'{head} {note} {msg}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- the patrol
def _point(t: dict, p: dict) -> dict:
    pid = kit.one_of(p.get('point'), [x['id'] for x in t['needs']['points']], 'Không có điểm này trên đoạn tuần.')
    return next(x for x in t['needs']['points'] if x['id'] == pid)


def _walk(s, c, d, p):
    t = _task(c, p, 'patrol')
    _need_duty(d)
    pt = _point(t, p)
    kit.need(pt['id'] not in t['walked'], 'Đã đi qua điểm này rồi.')
    kit.start_work(t)
    t['walked'].append(pt['id'])
    f = FINDS[t['_finds'][pt['id']]]
    return dict(message=f'{pt["emoji"]} {pt["km"]} · {pt["name"]}: {f["emoji"]} {f["text"]}', correct=True)


def _handle_point(s, c, d, p):
    t = _task(c, p, 'patrol')
    pt = _point(t, p)
    kit.need(pt['id'] in t['walked'], 'Đi tới điểm đó đã.')
    how = kit.one_of(p.get('how'), HANDLE, 'Chọn cách xử lý.')
    kit.need(t['handled'].get(pt['id']) != how, 'Đã làm việc này ở đây rồi.')
    fid = t['_finds'][pt['id']]
    f = FINDS[fid]
    if how == 'talk':
        kit.need(fid in LOCALS, 'Ở đây không có ai để nói chuyện.')
        tr = folk.traits(f'{t["id"]}|{pt["id"]}', PEOPLE[f['npc']][3] if f.get('npc') is not None else 'genz')
        mood = folk.word(tr, 'answer')
        t['handled'][pt['id']] = how
        extra = {'calm': '', 'sulk': ' (Người ta lầm bầm mãi mới chịu.)', 'blowup': ' (Bị mắng một trận, nhưng việc vẫn xong.)'}[mood]
        return dict(message=f'🗣️ {f.get("done", "Đã nhắc nhở.")}{extra}')
    if how == 'fix':
        kit.need(f['need'] == 'fix', 'Cái này không tự xử lý được: phải báo đúng nơi.' if fid != 'ok' else 'Ở đây mọi thứ ổn, không có gì để sửa.')
        t['handled'][pt['id']] = how
        return dict(message=f'🔧 {f["done"]}')
    t['handled'][pt['id']] = how
    if f['danger']:
        return dict(message='🚩 Bạn cắm cờ đỏ phòng vệ cách hai đầu chỗ hỏng, đứng chờ ở chỗ thấy được tàu tới.', celebrate=True)
    return dict(message='🚩 Cắm cờ đỏ cho chắc. (Chỗ này không nguy hiểm tới mức phải phòng vệ, nhưng cẩn thận thì không thừa.)')


def _pform(s, c, d, p):
    t = _task(c, p, 'patrol')
    pt = _point(t, p)
    kit.need(pt['id'] in t['walked'], 'Đi tới điểm đó đã.')
    form = kit.one_of(p.get('form'), PATROL_FORMS, 'Không có loại phiếu này.')
    rows = t['pforms'].setdefault(pt['id'], [])
    if form in rows:
        rows.remove(form)
        if not rows:
            t['pforms'].pop(pt['id'])
        return dict(message=f'Bỏ {_lower(PATROL_FORMS[form]["name"])} ở {pt["km"]}.')
    rows.append(form)
    line = {'so': '📒 Ghi sổ tuần đường', 'phieu': '🧾 Điền phiếu báo hỏng gửi cung', 'khan': '📞 Điện khẩn cho ga',
            'phuong': '🏛️ Báo tổ dân phố, phường'}[form]
    tail = ''
    if form == 'khan':
        f = FINDS[t['_finds'][pt['id']]]
        tail = ' Chị Nguyệt: “Rõ! Ga cho tàu dừng chờ, cử thợ ra ngay.”' if f['danger'] else ' Chị Nguyệt: “Rõ… mà cái này ghi phiếu là được rồi em.”'
    return dict(message=f'{line}: {pt["km"]}.{tail}')


def _patrol_done(s, c, d, p):
    t = _task(c, p, 'patrol')
    kit.start_work(t)
    dangers = 0
    for pt in t['needs']['points']:
        fid = t['_finds'][pt['id']]
        f = FINDS[fid]
        forms = t['pforms'].get(pt['id'], [])
        if pt['id'] not in t['walked']:
            _slip(t, 'skipped', 2, f'Bỏ qua đoạn {pt["km"]}, ghi sổ như đã đi.', 'bỏ qua điểm tuần')
            if f['danger']:
                _slip(t, 'missed_danger', 3, f'{f["text"]} ở {pt["km"]} không ai thấy cho tới khi tàu tới.', 'bỏ sót chỗ nguy hiểm', safety=True)
            continue
        if f['danger']:
            dangers += 1
            if 'khan' not in forms:
                _slip(t, 'no_alarm', 3, f'Chỗ nguy hiểm ở {pt["km"]} mà không điện khẩn cho ga.', 'không báo khẩn', safety=True)
            if f['need'] == 'protect' and t['handled'].get(pt['id']) != 'protect':
                _slip(t, 'no_protect', 3, f'Chỗ hỏng nguy hiểm ở {pt["km"]} không cắm cờ phòng vệ.', 'không phòng vệ', safety=True)
        elif f['need'] in ('fix', 'talk') and t['handled'].get(pt['id']) != f['need']:
            _slip(t, 'left_' + f['need'], 1, f'Thấy {_lower(f["text"])} ở {pt["km"]} mà để nguyên.', 'chưa xử lý tại chỗ')
        miss = [k for k in f['forms'] if k != 'khan' and k not in forms]
        if miss:
            _slip(t, 'no_form', 1, f'{pt["km"]}: chưa {_lower(PATROL_FORMS[miss[0]]["name"])}.', 'ghi chưa đúng loại phiếu')
    finds = sum(1 for v in t['_finds'].values() if v != 'ok')
    d['stats']['patrols'] += 1
    d['today']['patrols'] += 1
    d['stats']['finds'] += finds
    d['today']['finds'] += finds
    d['stats']['dangers'] += dangers
    safe = not cq.safety(t)
    full = 0 if not safe else max(0, _bonus(t) - 3 * cq.points(t))
    reward = ao.bonus(d['odd'], full)
    d['today']['earned'] += reward
    msg = _finish(s, c, d, t, reward, f'Tuần đường {t["needs"]["section"]}: {finds} chỗ cần để ý.')
    head = '📒 Ký sổ tuần đường.' + (f' Thưởng ca {reward} xu.' if reward else '')
    if not safe:
        head += ' 🛡️ Đội sẽ đọc lại buổi tuần này cùng bạn.'
    note = ao.flown(d['odd'], not cq.slips(t), CFG)
    return dict(message=f'{head} {note} {msg}'.strip(), celebrate=not cq.slips(t))


def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str) -> str:
    i = _npc_index(t)
    story = ''
    if i in REG_STORY:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        lines = REG_STORY[i]
        story = lines[min(r['visits'], len(lines)) - 1]
        t['story'] = story
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    return f'{narrative} 💬 {story}'.strip() if story else narrative


ACTIONS = {
    'rw_check': _check, 'rw_fix': _fix, 'rw_form': _form, 'rw_sign': _sign,
    'rw_readback': _readback_act, 'rw_wake': _wake, 'rw_warn': _warn, 'rw_scan': _scan, 'rw_clear': _clear, 'rw_lower': _lower_act,
    'rw_flag': _flag, 'rw_stop': _stop, 'rw_allclear': _allclear, 'rw_wait': _wait, 'rw_answer': _answer,
    'rw_watch': _watch, 'rw_radio': _radio, 'rw_ask': _ask, 'rw_raise': _raise, 'rw_log': _log,
    'rw_walk': _walk, 'rw_handle': _handle_point, 'rw_pform': _pform, 'rw_patrol': _patrol_done,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d.update(on_duty=False, crank=False, jam=False)
    d['today'] = _fresh_today(day)
    # Yesterday's trains have long gone by and its hand-over is over: what is left of them is closed, and today's
    # roster is topped up so the day still has its hand-over and its trains.
    for t in c['tasks']:
        if t.get('career') == ID and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    mine = [t for t in c['tasks'] if t.get('career') == ID and t['day'] == day]
    if mine:
        slot = max(int(t['id'].split('-')[-1]) for t in mine) + 1
        for _ in range(max(0, daily_task_count(day) - len(mine))):
            t = make_task(day, slot, c['turn'])
            c['tasks'].append(t)
            on_task(s, c, t)
            slot += 1
    shift = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'shift' and t['day'] == day
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if shift is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        shift = make_task(day, 0, c['turn'])
        c['tasks'].append(shift)
        on_task(s, c, shift)
    if shift:
        c['active_task'] = shift['id']
        shift['deferred'] = False
    else:
        d['on_duty'] = True   # a shift already signed today (a day reopened): carry on
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')
    ao.start(c, ID, d['odd'])
    ao.tick(s, c, ID, d['odd'], ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    odd_note = ao.close(s, c, d['odd'], ODD)
    today = d['today']
    lines = [f'🚆 {today["trains"]} chuyến tàu qua đường ngang, {today["safe"]} chuyến an toàn tuyệt đối.']
    if today['held']:
        lines.append(f'✋ Giữ chắn trước {today["held"]} người đòi qua' + (f', ghi biển số {today["reported"]} người.' if today['reported'] else '.'))
    if today['stopped']:
        lines.append(f'🟥 Báo dừng tàu {today["stopped"]} lần vì có vật cản. Đúng quy trình.')
    if today['patrols']:
        lines.append(f'🔩 Tuần đường: {today["finds"]} chỗ cần để ý đã ghi sổ.')
    if today['earned']:
        lines.append(f'💵 Thưởng ca hôm nay {today["earned"]} xu (lương trả theo hợp đồng).')
    odd = d['odd']
    seen = [h for h in odd['log'] if h['day'] == c['day'] and h['how'] != 'lapse']
    if seen:
        lines.append(RC.DAY_LINES['odd'].format(n=len(seen), ok=sum(h['good'] is True for h in seen)))
    lv = ao.level(odd['conduct']['points'])
    if lv[1] != 'ok':
        lines.append(RC.DAY_LINES['record'].format(label=lv[2].lower()))
    if odd['fatigue'] >= ao.TIRED:
        lines.append(RC.DAY_LINES['tired'])
    for n in (desk_note, odd_note):
        if n:
            lines.append(n)
    d.update(on_duty=False, crank=False, jam=False)
    return dict(lines=lines, note='Sáng mai nhận ca: đọc sổ giao ca, thử từng thiết bị rồi mới ký.', trains=today['trains'], safe=today['safe'],
                held=today['held'], reported=today['reported'], stopped=today['stopped'], patrols=today['patrols'], earned=today['earned'])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'shift':
        return dict(criteria=[dict(key='check', label='Thử đủ thiết bị', score=2 if 'unchecked' in codes else 5,
                                   note='thử từng thứ' if 'unchecked' not in codes else 'ký khi chưa thử'),
                              dict(key='report', label='Báo đúng nơi', score=1 if codes & {'no_station', 'hidden_fault'} else 3 if codes & {'no_form', 'unfixed'} else 5,
                                   note='đúng kênh' if not codes & {'no_station', 'hidden_fault', 'no_form', 'unfixed'} else 'báo chưa đúng')])
    if t['kind'] == 'patrol':
        return dict(criteria=[dict(key='walk', label='Đi đủ đoạn tuần', score=2 if 'skipped' in codes else 5, note='đủ từng điểm' if 'skipped' not in codes else 'bỏ qua điểm'),
                              dict(key='protect', label='Phòng vệ, báo khẩn', score=1 if codes & {'no_alarm', 'no_protect', 'missed_danger'} else 5,
                                   note='chỗ nguy hiểm được báo ngay' if not codes & {'no_alarm', 'no_protect', 'missed_danger'} else 'chỗ nguy hiểm chưa được báo'),
                              dict(key='forms', label='Đúng loại phiếu', score=3 if codes & {'no_form', 'left_fix', 'left_talk'} else 5,
                                   note='ghi đúng phiếu' if not codes & {'no_form', 'left_fix', 'left_talk'} else 'phiếu chưa đủ')])
    radio = 5 if not t.get('rb_tries') else 3
    timing = 1 if codes & {'unprotected', 'on_rails', 'trapped'} else 2 if codes & {'late_close', 'no_bell'} else 3 if codes & {'short_bell', 'no_look', 'no_flag'} \
        else 4 if t.get('early') else 5
    hold = 1 if codes & {'opened', 'open_due'} else 4 if 'cruel' in codes else 5
    watch = 1 if codes & {'tail_unreported', 'second', 'defect_unreported', 'false_green'} else 3 if codes & {'no_watch', 'no_confirm'} else 5
    log = 3 if 'log' in codes else 5
    return dict(criteria=[dict(key='radio', label='Nhắc lại lệnh', score=radio, note='rõ từng chữ' if radio == 5 else 'nhắc sai phải đọc lại'),
                          dict(key='timing', label='Hạ chắn đúng lúc', score=timing, note='chuông trước, chắn sau, đúng giờ' if timing == 5 else 'hạ sớm quá' if timing == 4 else 'chưa đúng quy trình'),
                          dict(key='hold', label='Giữ chắn', score=hold, note='không mở cho ai' if hold == 5 else 'mở chắn khi tàu tới' if hold == 1 else 'hơi nặng tay'),
                          dict(key='watch', label='Nhìn tàu, hỏi ga', score=watch, note='nhìn đủ đoàn tàu, hỏi ga trước khi nâng' if watch == 5 else 'bỏ sót'),
                          dict(key='log', label='Sổ nhật ký', score=log, note='ghi đúng sự thật' if log == 5 else 'ghi chưa khớp')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'shift':
        trains = '; '.join(f'{b["code"]} {b["at"]}' for b in n['board'])
        return f'Bảng giờ tàu hôm nay: {trains}. {n["handover"]} {n["note"]}'
    if t['kind'] == 'patrol':
        return f'Tuần đường {n["section"]}: {len(n["points"])} điểm. {n["note"]}'
    tr = n['train']
    return (f'📻 Chị Nguyệt: “Đường ngang Bến Mây! Tàu {tr["code"]} {tr["dir"]}, {tr["cars"]} toa, rời ga Bến Gỗ lúc {tr["dep"]}, '
            f'dự kiến qua đường ngang {tr["at"]}. Nhắc lại!” {n["note"]}')


def _push_view(t: dict, x: dict) -> dict:
    px = PUSH_INDEX[x['id']]
    line = px['line'] if x['round'] == 0 else px['again']
    return dict(id=x['id'], emoji=px['emoji'], who=px['who'], npc=kit.npc_id(ID, px['npc']) if px['npc'] is not None else None,
                state=x['state'], out=x['out'], line=line, soft=px['soft'])


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
        return v
    if t['kind'] == 'shift':
        v['found_text'] = FAULTS[t['found']]['text'] if t['found'] else None
        v['found_fix'] = FAULTS[t['found']]['fix'] if t['found'] else None
        v['found_item'] = FAULTS[t['found']]['item'] if t['found'] else None
        return v
    if t['kind'] == 'patrol':
        v['seen'] = {pid: dict(find=t['_finds'][pid], emoji=FINDS[t['_finds'][pid]]['emoji'], text=FINDS[t['_finds'][pid]]['text'],
                               local=t['_finds'][pid] in LOCALS, done=FINDS[t['_finds'][pid]].get('done'))
                     for pid in t['walked']}
        return v
    n = v['needs']
    n.pop('push', None)
    n['crowd'] = None if not t['scanned'] else list(t['needs']['crowd'])
    v['left'] = [dict(key=k, name=_crowd_of(k)['name'], emoji=_crowd_of(k)['emoji'], line=_crowd_of(k).get('line', ''),
                      done=t['progress'].get(k, 0), steps=_crowd_of(k)['steps'])
                 for k in t['left'] if t['scanned'] or k.startswith('sneak:')]
    v['left_hidden'] = not t['scanned']
    v['pushers'] = [_push_view(t, x) for x in t['pushers'] if x['state'] != 'wait']
    v['waiting'] = sum(1 for x in t['pushers'] if x['state'] == 'wait' and t['arm'] == 'down')
    v.pop('progress', None)
    v['seen'] = None
    if t['watched']:
        dx = t['_defect']
        v['seen'] = dict(tail=t['_tail'], defect=DEFECTS[dx['kind']]['text'].format(n=dx['n']) if dx else None)
    v['second_train'] = t['_second']['code'] if t['_second'] and t['second'] != 'none' else None
    v['bonus'] = _bonus(t)
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    board = []
    for t in sorted((x for x in c['tasks'] if x.get('career') == ID and x.get('kind') == 'train' and x['day'] == c['day']), key=lambda x: x['id']):
        tr = t['needs']['train']
        state = 'done' if t['status'] == 'completed' else 'now' if t['id'] == c.get('active_task') else 'wait'
        board.append(dict(task=t['id'], code=tr['code'], at=tr['at'], dir=tr['dir'], emoji=tr['emoji'], state=state,
                          late=t.get('late_min', 0) if t.get('late_told') or t['status'] == 'completed' else 0))
    odd = d.get('odd') or ao.initial()
    return dict(intro=d['intro'], on_duty=d['on_duty'], crank=d['crank'], jam=d['jam'],
                mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']), today=d['today'], stats=d['stats'],
                regulars={k: dict(v) for k, v in d['regulars'].items()}, desk=kit.desk_public(d['desk'], DESK, ID), log=d['log'][-6:],
                board=board, odd=ao.public(c, odd, ODD, ID, CFG))


def content() -> dict:
    return dict(equip=EQUIP, forms=FORMS, clear=CLEAR, answers=ANSWERS, patrol_forms=PATROL_FORMS, handle=HANDLE, remarks=REMARKS,
                intro=INTRO, lower_at=LOWER_AT, bell_lead=BELL_LEAD, crossing=RC.CROSSING, company=RC.COMPANY, detour=RC.DETOUR,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    if k == 'shift':
        return 'Đọc sổ giao ca → thử từng thiết bị → hỏng thì xử lý và báo đúng nơi (nguy hiểm thì gọi ga) → ký nhận ca.'
    if k == 'patrol':
        return 'Đi từng điểm → tự xử lý việc nhỏ → chỗ nguy hiểm: cắm cờ phòng vệ và điện khẩn → ghi đúng loại phiếu → ký sổ tuần đường.'
    return ('Nghe ga → nhắc lại lệnh → nhìn đường ngang, dẹp người trên ray → bật chuông đèn → còn khoảng 3 phút thì hạ chắn → '
            'giữ chắn, trả lời người đòi qua → cờ xanh đón tàu → nhìn hết đoàn tàu → báo ga nếu bất thường → hỏi ga còn tàu không → nâng chắn → ghi sổ.')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'flag':
        if t and t.get('career') == ID and t.get('kind') == 'train' and t['status'] not in ('completed', 'cancelled') and t.get('scanned') and t.get('left'):
            key = t['left'][0]
            name = _crowd_of(key)['name']
            t['left'].remove(key)
            t['progress'].pop(key, None)
            return f'Đã ra dẫn khỏi đường ray: {_lower(name)}.'
        return 'Đã lau đèn đỏ, tra dầu chốt cần chắn.'
    if e.get('role') == 'track':
        return 'Đã siết lại mấy con bu lông mối nối gần chòi, ghi sổ tuần đường.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu chòi gác sai.')


def _vlist(v, allowed, n: int, msg: str = 'Dữ liệu việc gác chắn sai.') -> None:
    kit.need(isinstance(v, list) and len(v) <= n and len(v) == len(set(v)) and all(isinstance(x, str) and x in allowed for x in v), msg)


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN and t.get('kind') in KINDS, 'Việc gác chắn không hợp lệ.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện người quen sai.')
    if t['kind'] == 'shift':
        _vlist(t.get('checked'), EQUIP_IDS, len(EQUIP_IDS))
        kit.need(t.get('found') in (None, t['_fault']) and (t['found'] is None or t['_fault'] is not None), 'Thiết bị hỏng sai.')
        _vbool(t.get('fixed'))
        _vlist(t.get('forms'), FORMS, len(FORMS))
        return
    if t['kind'] == 'patrol':
        ids = [x['id'] for x in t['needs']['points']]
        _vlist(t.get('walked'), ids, len(ids))
        h = t.get('handled')
        kit.need(isinstance(h, dict) and set(h) <= set(t['walked']) and all(v in HANDLE for v in h.values()), 'Xử lý điểm tuần sai.')
        f = t.get('pforms')
        kit.need(isinstance(f, dict) and set(f) <= set(t['walked']), 'Phiếu tuần đường sai.')
        for v in f.values():
            _vlist(v, PATROL_FORMS, len(PATROL_FORMS))
            kit.need(v, 'Phiếu tuần đường sai.')
        return
    for k in ('rb', 'scanned', 'stopped', 'standing', 'late_told', 'held', 'recalled', 'passed', 'watched', 'asked', 'awake'):
        _vbool(t.get(k))
    kit.integer(t.get('rb_tries'), 0, 9)
    for k in ('eta', 'bell', 'down_at'):
        if t.get(k) is not None:
            kit.integer(t[k], -5, 200)
    for k in ('down_min', 'reopened', 'early', 'late_min'):
        kit.integer(t.get(k), 0, 500)
    kit.need(t.get('arm') in ('up', 'down') and t.get('flag') in (None, 'green', 'red') and t.get('second') in ('none', 'coming', 'passed'), 'Trạng thái đường ngang sai.')
    kit.need(t['rb'] or t['eta'] is None, 'Trạng thái đường ngang sai.')
    push_ids = [p[0] for p in t['needs']['push']]
    keys = list(t['needs']['crowd']) + [f'sneak:{x}' for x in push_ids]
    _vlist(t.get('left'), keys, len(keys))
    pr = t.get('progress')
    kit.need(isinstance(pr, dict) and set(pr) <= set(t['left']) and all(type(v) is int and 0 <= v <= 3 for v in pr.values()), 'Trạng thái đường ngang sai.')
    ps = t.get('pushers')
    kit.need(isinstance(ps, list) and [x.get('id') for x in ps] == push_ids, 'Người chờ ở chắn sai.')
    for x, (pid, at) in zip(ps, t['needs']['push']):
        kit.need(isinstance(x, dict) and set(x) == {'id', 'at', 'state', 'round', 'out'} and x['at'] == at and x['state'] in ('wait', 'on', 'done')
                 and x['round'] in (0, 1) and x['out'] in (None, 'ok', 'sulk', 'blowup', 'sneak', 'opened', 'waited'), 'Người chờ ở chắn sai.')
    _vlist(t.get('radioed'), ('tail', 'defect'), 2)
    _vlist(t.get('reported'), push_ids, len(push_ids))
    _vlist(t.get('sneaks'), push_ids, len(push_ids))
    if t.get('remarks') is not None:
        _vlist(t['remarks'], REMARKS, len(REMARKS))


def validate_data(c: dict) -> None:
    d = _data(c)
    for k in ('intro', 'on_duty', 'crank', 'jam'):
        _vbool(d[k])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ người quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu chòi gác sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.need(isinstance(d['log'], list) and len(d['log']) <= LOG_MAX, 'Sổ chuyến tàu sai.')
    for x in d['log']:
        kit.need(isinstance(x, dict) and set(x) == {'day', 'code', 'at', 'late', 'held', 'ok', 'safe'}, 'Sổ chuyến tàu sai.')
        kit.integer(x['day'], 1, 10 ** 7)
        kit.integer(x['late'], 0, 500)
        kit.integer(x['held'], 0, 20)
        kit.text(x['code'], 12)
        kit.text(x['at'], 5)
        _vbool(x['ok'])
        _vbool(x['safe'])
    kit.desk_validate(d['desk'], DESK)
    ao.validate(d['odd'], ODD)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='rw_', category='outdoor',
    meta=dict(short='Gác chắn đường sắt', place='Đường ngang Bến Mây', tagline='Chắn hạ đúng lúc, trên ray không còn ai.', icon='bell',
              color='#a23b2c', light='#f8e8e3', weather='Nắng nhẹ, ray sáng loáng', work='Chuyến tàu', station='Chòi gác',
              greeting='Nhận ca, thử từng thiết bị. Ga gọi là nhắc lại lệnh, dẹp người trên ray, chuông trước, chắn sau, không mở cho ai.',
              caption='Tàu không chờ ai, mình chờ tàu', map_label='28 · ĐƯỜNG NGANG BẾN MÂY'),
    people=PEOPLE,
    staff=[('Hưng', 'flag', 'Cựu bộ đội, đứng gác nghiêm như cột mốc.', 74, 94),
           ('Thảo', 'track', 'Tinh mắt, thấy bu lông lỏng từ xa mười mét.', 78, 90),
           ('Đạt', 'flag', 'Giọng to, quát xe máy lùi lại một câu là nghe.', 82, 80),
           ('Nga', 'track', 'Đi bộ khỏe, thuộc từng cột cây số.', 84, 84)],
    roles={'flag': 'Gác phụ', 'track': 'Thợ tuần đường'},
    tip=0,
    open_line='Chú Sáu đưa sổ giao ca: “Nhận ca thôi con.”',
    more_line='Ga báo thêm một chuyến tàu.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('🚦', 'Chòi gác đường ngang', [('Nhắc lại lệnh', 'Khi ga báo tàu'), ('Chuông đèn', 'Trước khi hạ chắn'),
                                           ('Đèn đuôi', 'Toa cuối phải có'), ('Hỏi ga', 'Trước khi nâng chắn')],
              ['Nhắc lại lệnh của ga', 'Dẹp người trên ray, bật chuông, hạ chắn', 'Giữ chắn, đứng cờ đón tàu', 'Nhìn tàu, hỏi ga, nâng chắn, ghi sổ']),
    stories=[('Cái còi đồng của chú Sáu', ('Chú Sáu đeo cái còi đồng cũ ở cổ, mòn bóng chỗ ngậm.',
                                            'Chú kể đêm mưa năm nọ, tiếng còi ấy gọi một xe bò ra khỏi ray kịp lúc.',
                                            'Ngày bạn gác trọn một tuần không sơ suất, chú tháo cái còi đưa cho bạn.')),
             ('Hàng nước bà Bông', ('Bà Bông ghét còi tàu, ghét luôn cả cái chuông đường ngang.',
                                    'Bạn ghi phiếu ý kiến của bà gửi xí nghiệp, kèm lời giải thích vì sao còi phải kêu.',
                                    'Chiều nay bà Bông rót cho bạn chén chè: “Thôi, còi thì còi. Cháu gác cẩn thận là được.”')),
             ('Cuốn sổ nhật ký đường ngang', ('Cuốn sổ nhật ký của chòi gác dày cộp, chữ chú Sáu nghiêng nghiêng.',
                                              'Anh Quý lật từng trang, so với sổ ga: không vênh một phút.',
                                              'Xí nghiệp đem cuốn sổ của ca Bến Mây làm mẫu cho cả cung.'))],
    review_asides=['Chuông trước, chắn sau, đúng từng phút.', 'Nhắc lại lệnh rành rọt, ga nghe là yên tâm.', 'Giữ chắn cứng mà nói năng mềm.',
                   'Nhìn đủ cả đoàn tàu tới tận đèn đuôi.'],
    situations=SITUATIONS,
    guide='Nhận ca: thử từng thiết bị, báo đúng nơi. Mỗi chuyến tàu: nhắc lại lệnh → dẹp người trên ray → chuông đèn → còn khoảng 3 phút thì hạ chắn → '
          'giữ chắn, không mở cho ai → cờ xanh đón tàu → nhìn hết đoàn tàu, báo bất thường → hỏi ga còn tàu không → nâng chắn → ghi sổ đúng sự thật.',
    employment=dict(
        postings=[
            dict(id='rw-gac', org='Xí nghiệp Đường sắt Sông Mây · Đường ngang Bến Mây', kind='company', title='Nhân viên gác chắn đường ngang',
                 salary=(62, 80), probation_days=3, wants=['careful', 'calm', 'communication'],
                 perks=['Chú Sáu kèm cặp ca đầu', 'Có phụ cấp ca đêm', 'Ngày nào cũng gặp đủ kiểu người'],
                 culture='Xí nghiệp nhỏ, một cung đường mười hai cây số. Chòi gác nào cũng thuộc tên nhau; an toàn nói trước, đúng giờ nói sau.',
                 questions=['rw_close', 'rw_push', 'rw_tail', 'mistake'], reference=True),
            dict(id='rw-tuan', org='Xí nghiệp Đường sắt Sông Mây · Cung đường Sông Mây', kind='branch', title='Công nhân tuần đường kiêm gác chắn',
                 salary=(55, 70), probation_days=2, wants=['careful', 'teamwork'],
                 perks=['Nhận việc nhanh', 'Đi bộ khỏe người', 'Lương thấp hơn gác chính'],
                 culture='Tổ tuần đường ba người, mỗi ngày đi bộ mấy cây số ray, thay gác chắn khi thiếu người.',
                 questions=['rw_patrol'], reference=False),
        ],
        questions={
            'rw_close': dict(text='Ga báo tàu còn tám phút. Đường ngang đang đông xe. Bạn hạ chắn lúc nào?', options=[
                dict(id='rule', label='Bật chuông đèn trước, còn khoảng ba phút thì hạ, trước đó dẹp người trên ray', score=3, note='Chú Sáu gật đầu: đúng nhịp của nghề.'),
                dict(id='now', label='Hạ ngay cho chắc, đông mấy cũng chờ', score=1, note='An toàn đấy, nhưng chờ lâu quá người ta sẽ chui chắn.'),
                dict(id='late', label='Đợi thấy đèn tàu rồi hạ cho xe kịp qua', score=0, note='Thấy đèn tàu mới hạ là quá muộn.')]),
            'rw_push': dict(text='Chắn đã hạ. Một xe cứu thương hú còi xin qua, tàu còn hai phút.', options=[
                dict(id='hold', label='Giữ chắn, nói rõ còn hai phút, tàu qua là nâng ngay', score=3, note='Tàu không phanh kịp; hai phút chờ cứu được thêm người.'),
                dict(id='open', label='Nâng chắn cho xe cứu thương qua', score=0, note='Không ai được mở chắn khi tàu sắp tới, kể cả xe ưu tiên.'),
                dict(id='call', label='Gọi ga xin dừng tàu cho xe cứu thương', score=1, note='Tàu còn hai phút thì dừng không kịp; giữ chắn mới là đúng.')]),
            'rw_tail': dict(text='Tàu hàng vừa qua, bạn không thấy đèn đuôi toa cuối. Bạn làm gì?', options=[
                dict(id='radio', label='Báo ngay trực ban ga, ghi giờ, ghi sổ', score=3, note='Đèn đuôi cho biết đoàn tàu còn nguyên.'),
                dict(id='later', label='Ghi sổ, cuối ca báo', score=1, note='Chuyện này không chờ cuối ca được.'),
                dict(id='skip', label='Chắc đèn cháy, không sao', score=0, note='Có khi toa cuối đã tuột lại trên đường.')]),
            'rw_patrol': dict(text='Đi tuần thấy đá ba-lát trôi, ray treo hẫng. Mười lăm phút nữa có tàu.', options=[
                dict(id='protect', label='Cắm cờ đỏ phòng vệ hai đầu, điện khẩn cho ga', score=3, note='Phòng vệ và báo khẩn: đúng quy trình.'),
                dict(id='slip', label='Ghi phiếu báo hỏng gửi cung', score=0, note='Phiếu là cho việc không gấp.'),
                dict(id='fill', label='Tự xúc đá chèn tạm', score=1, note='Việc đó của tổ thợ; việc của mình là báo và phòng vệ.')]),
        }),
)
