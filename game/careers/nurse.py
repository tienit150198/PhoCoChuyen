"""Điều dưỡng khoa Nội: a day shift on the medical ward of Bệnh viện phường Lá Sen (plugin career).

The player is a newly hired nurse (employment: CV and interview; the "Chứng chỉ An toàn người bệnh" certificate
raises the hire chance) under chị Hoa, the ward's head nurse. The doctor decides treatment; the nurse carries out
the orders, checks every step, and reports anything that is not right. One task is one piece of the shift:

* ``shift`` (slot 0): take the handover. Read the night nurse's note for each of the four beds and choose the bed
  to see first (the one whose night went wrong). The first round's vitals (slot 1) are on that bed;
* ``vitals``: wash your hands, check the patient's identity (ask full name and date of birth, compare the
  wristband), measure temperature, pulse, blood pressure, SpO2 and pain, chart what you measured (typed in), and
  compare it with the game's alarm card: anything outside it is reported to the doctor (say which signs). A reading
  that does not fit the patient (a loose finger probe) is measured again;
* ``med``: the doctor's order card and the pharmacy's tray. Identity, the allergy band, the tray label, the blood
  sugar when the order says so, the "nil by mouth" sign: give as ordered, or hold and report the reason. A patient
  who refuses is asked why and the reason explained; they decide (hidden traits). Pushing them is a mistake;
* ``bell``: a call bell; go and see, then answer in one of several ways (fall risk, an empty drip, chest pain,
  a lonely grandmother who only wants to talk, a livestream from the bed);
* ``triage``: three people arrive at reception at once; ask, take a quick look, then give each a colour on the
  fictional "Thẻ màu Lá Sen" (the loud one is not always the sick one);
* ``proc``: get someone ready for a procedure: consent form, fasting, allergy, jewellery. A missing consent goes
  to the doctor; someone who has eaten, or changed their mind, is not sent;
* ``discharge``: the signed discharge paper, the insurance card, the cannula out, what to teach (and asking the
  patient to say it back).

Around the tasks: the awkward people of the ward (air_odd engine, game/careers/nurse_content.py ODD): envelopes,
bribes for a better bed, "the best doctor", relatives who film, the "thần y" with herbs, a drunk at night, colleagues
who cut corners, extra shifts. Giving in is never rewarded (conduct points; stood down for the day; demoted).
Desk surprises and real-life situations as in every career. At the end of the shift the player may write the
handover notes from what really happened (lines that did not happen are ghi khống).

Nothing here is medical advice: no dose or amount is ever given. Mistakes go through consequences.slip; money only
through the engine (the salary at day close, a small bonus per task). Everything random comes from (day, slot) or
the task id: make_task is pure.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import air_odd as ao
from . import street_folk as folk
from .. import consequences as cq
from .. import archive as ar
from . import nurse_content as NC
from .nurse_content import PEOPLE, BEDS, DRUGS, ROUTES, ALLERGY, SIGNS, SIGN_IDS, VITALS, MEDS, BELLS, TRIAGE, PROCS, DISCHARGES, TEACH

ID = 'nurse'
GEN = 1
BONUS = 10            # xu per task done by the book (a performance bonus: the salary is the pay)
LEARN = 3             # chị Hoa stands beside you for the first three patient tasks
FACTS_MAX = 14
BED_IDS = tuple(BEDS)
KINDS = ('shift', 'vitals', 'med', 'bell', 'triage', 'proc', 'discharge')
PATIENT = ('vitals', 'med', 'bell', 'proc', 'discharge')
STAGES = ('open', 'done')
ID_HOW = ('open', 'name', 'bed')
SAID = ('refused', 'yes', 'no', 'pushed')
HOLD = dict(NC.HOLD_REASONS, ate='Người bệnh đã ăn uống trước thủ thuật', consent='Chưa có giấy cam đoan, chờ bác sĩ giải thích')
MED_CHECKS = ('allergy', 'label', 'sugar')
PROC_KEYS = tuple(NC.PROC_CHECKS)
DIS_CHECKS = ('paper', 'bhyt', 'cannula')
MODS = NC.MODS
MOD = {m['id']: m for m in MODS}
HOA, KHANG, TU, BAY, NGAN, TUAN, LIEN, MY = range(8)

# The words of the encounters (air_odd): who to bring in, the office, what a demotion or a stand-down is called here.
CFG = dict(crew='👩‍⚕️ Gọi chị Hoa', company='🏥 Báo bệnh viện', union='Nhờ công đoàn', office='Phòng Điều dưỡng',
           demoted='điều dưỡng tập sự', title='điều dưỡng viên',
           labels={'charm': dict(duty='Em đang trong ca trực.', rule='Bệnh viện không cho nhân viên nhận quà, hẹn hò người bệnh.',
                                 alt='Cảm ơn, chúc người nhà mau khỏe.')},
           ground_line='⚖️ Phòng Điều dưỡng: tạm đình chỉ trực hết hôm nay, mai lên trình bày.',
           demote_line='⚖️ Hội đồng kỷ luật: hạ xuống điều dưỡng tập sự, tạm đình chỉ trực hôm nay, không có thưởng tới khi hồ sơ sạch lại.',
           tired_line='😮‍💨 Mệt rồi: thưởng việc chỉ còn một nửa. Xin nghỉ bù ở phòng trực.',
           rest_ok=' Ca của bạn đã có người trực thay; bạn thấy nhẹ cả người.',
           levels={'ground': 'Tạm đình chỉ trực'})


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError, AttributeError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Người bệnh'


def _short(bed: str) -> str:
    b = BEDS[bed]
    return f'G{b["bed"]} {PEOPLE[b["npc"]][0].lower()}'


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _num(v) -> str:
    """A typed reading, normalised: '38.9' and '38,9' are the same; '118 / 76' is '118/76'."""
    s = str(v or '').strip().replace(' ', '').replace('.', ',')
    if '/' in s:
        a, _, b = s.partition('/')
        return f'{a.lstrip("0") or "0"}/{b.lstrip("0") or "0"}'
    if ',' in s:
        a, _, b = s.partition(',')
        b = b.rstrip('0')
        return f'{a.lstrip("0") or "0"},{b}' if b else (a.lstrip('0') or '0')
    return s.lstrip('0') or ('0' if s else '')


def _value(raw: str) -> float:
    return float(raw.split('/')[0].replace(',', '.'))


def abnormal(sign: str, raw: str) -> bool:
    """The game's alarm card ("Thẻ báo động Lá Sen"): a simplified game rule, not medical guidance."""
    v = _value(raw)
    return {'temp': v >= 38.0 or v <= 35.5, 'pulse': v > 110 or v < 50, 'bp': v < 90 or v > 180, 'spo2': v < 94,
            'pain': v >= 7}[sign]


def _rot(rows: tuple, day: int, slot: int, opened: int, salt: str) -> str:
    """A case from a rotation: the first `opened` rows on early days, all of them later (pure)."""
    pool = rows[:max(1, min(len(rows), opened))]
    return pool[kit.rng(ID, salt, day, slot).randrange(len(pool))]


def _opened(day: int, simple: int, total: int) -> int:
    return simple if day <= 1 else simple + 2 if day == 2 else total


# ================================================================ tasks
def flag_bed(day: int) -> str:
    """The bed whose night went wrong (the handover's flag): the first round's vitals are on it."""
    return BED_IDS[kit.rng(ID, 'flag', day).randrange(len(BED_IDS))]


def _weights(day: int, mod: str) -> list:
    w = {'vitals': 2, 'med': 3, 'bell': 3, 'triage': 2 if day >= 2 else 0, 'proc': 2 if day >= 3 else 0, 'discharge': 1 if day >= 3 else 0}
    if mod == 'busy':
        w['triage'] += 3
    elif mod == 'flu':
        w['triage'] += 2
        w['vitals'] += 1
    elif mod == 'audit':
        w['med'] += 1
        w['vitals'] += 1
    elif mod == 'visit':
        w['bell'] += 2
        w['discharge'] += 1
    return [(k, v) for k, v in w.items() if v]


def task_kind(day: int, slot: int) -> str:
    if slot <= 0:
        return 'shift'
    if slot == 1:
        return 'vitals'
    if day == 1:
        return ('med', 'bell', 'vitals', 'med', 'bell')[(slot - 2) % 5]
    mod = mod_of(day)['id']
    prev = task_kind(day, slot - 1) if slot > 2 else 'vitals'
    rows = [(k, v) for k, v in _weights(day, mod) if k != prev]
    total = sum(v for _, v in rows)
    x = kit.rng(ID, 'kind', day, slot).random() * total
    for k, v in rows:
        x -= v
        if x < 0:
            return k
    return rows[-1][0]


def _case(day: int, slot: int, kind: str) -> str:
    flag = flag_bed(day)
    if kind == 'vitals':
        if slot == 1:
            return NC.FLAG_VITALS[flag]
        return _rot(NC.VITALS_ROTATION, day, slot, _opened(day, 4, len(NC.VITALS_ROTATION)), 'vit')
    if kind == 'med':
        return _rot(NC.MED_ROTATION, day, slot, _opened(day, 4, len(NC.MED_ROTATION)), 'med')
    if kind == 'bell':
        return _rot(NC.BELL_ROTATION, day, slot, _opened(day, 4, len(NC.BELL_ROTATION)), 'bell')
    if kind == 'proc':
        return _rot(NC.PROC_ROTATION, day, slot, len(NC.PROC_ROTATION), 'proc')
    if kind == 'discharge':
        rows = tuple(x for x in NC.DISCHARGE_ROTATION if DISCHARGES[x]['bed'] != flag) or NC.DISCHARGE_ROTATION
        return _rot(rows, day, slot, len(rows), 'dis')
    return ''


def _queue(day: int, slot: int) -> list:
    """Three arrivals at reception: one serious, one loud but minor, one more (pure)."""
    r = kit.rng(ID, 'triage', day, slot)
    serious = [k for k, v in TRIAGE.items() if v['best'] in ('do', 'cam')]
    minor = [k for k, v in TRIAGE.items() if v['best'] == 'xanh']
    a = serious[r.randrange(len(serious))]
    b = minor[r.randrange(len(minor))]
    rest = [k for k in TRIAGE if k not in (a, b)]
    c = rest[r.randrange(len(rest))]
    out = [a, b, c]
    r.shuffle(out)
    return out


def _common() -> dict:
    return dict(gen=GEN, stage='open', washed=False, idm=None, seen=[], chart=None, called=[], choice=None, colors={}, said=None,
                teach=[], result=None, story=None)


def make_task(day: int, slot: int, serial: int) -> dict:
    kind = task_kind(day, slot)
    c = _common()
    if kind == 'shift':
        flag = flag_bed(day)
        notes = [dict(bed=b, name=f'Giường {BEDS[b]["bed"]} · {BEDS[b]["name"]}', dx=BEDS[b]['dx'],
                      text=NC.NOTES[b][0 if b == flag else 1]) for b in BED_IDS]
        return kit.base_task(ID, day, slot, serial, HOA, 'Nhận giao ca sáng',
                             'Chị Hoa: “Đọc sổ giao ca từng giường đi em, rồi chọn giường xem trước. Giường nào đêm qua có chuyện thì đi trước.”',
                             kind='shift', needs=dict(notes=notes), _v=dict(first=flag), **c)
    if kind == 'triage':
        q = _queue(day, slot)
        needs = dict(queue=[dict(who=TRIAGE[k]['who'], emoji=TRIAGE[k]['emoji'], text=TRIAGE[k]['text']) for k in q])
        return kit.base_task(ID, day, slot, serial, MY, 'Phân loại ở quầy tiếp đón',
                             'Cô Mỹ: “Ba người vừa tới cùng lúc, em phân loại giúp chị. Người la to chưa chắc là người nặng nha.”',
                             kind='triage', needs=needs, _v=dict(cases=q), **c)
    case = _case(day, slot, kind)
    if kind == 'vitals':
        x = VITALS[case]
        b = BEDS[x['bed']]
        return kit.base_task(ID, day, slot, serial, b['npc'], f'Đo dấu hiệu sinh tồn giường {b["bed"]}',
                             f'Tới giờ đo giường {b["bed"]}. {x["look"]}', kind='vitals', needs=dict(bed=x['bed']), _v=dict(case=case), **c)
    if kind == 'med':
        x = MEDS[case]
        b = BEDS[x['bed']]
        card = x.get('card') or dict(name=b['name'], dob=b['dob'], bed=b['bed'])
        order = dict(name=card['name'], dob=card['dob'], bed=card['bed'], drug=DRUGS[x['drug']]['name'], route=ROUTES[x['route']], time=x['time'],
                     rule='Đo đường huyết trước; máy báo THẤP thì giữ thuốc, báo bác sĩ.' if x['drug'] == 'pen' else '')
        board = 'NHỊN ĂN UỐNG · chờ nội soi 10:00' if x['variant'] == 'npo' else ''
        return kit.base_task(ID, day, slot, serial, b['npc'], f'Thuốc {x["time"]} giường {b["bed"]}',
                             f'Phiếu y lệnh của bác sĩ Khang và khay thuốc khoa dược đã để trên xe tiêm. Giường {b["bed"]}: {b["dx"].lower()}.',
                             kind='med', needs=dict(bed=x['bed'], order=order, board=board), _v=dict(case=case), **c)
    if kind == 'bell':
        x = BELLS[case]
        b = BEDS[x['bed']]
        return kit.base_task(ID, day, slot, serial, b['npc'], f'Chuông gọi giường {b["bed"]}',
                             f'🔔 Đèn chuông giường {b["bed"]} sáng đỏ, kêu tít tít.', kind='bell', needs=dict(bed=x['bed']), _v=dict(case=case), **c)
    if kind == 'proc':
        x = PROCS[case]
        b = BEDS[x['bed']]
        return kit.base_task(ID, day, slot, serial, b['npc'], f'Chuẩn bị {x["name"].lower()} giường {b["bed"]}',
                             f'Phòng thủ thuật hẹn {x["time"]}: {x["name"].lower()} cho giường {b["bed"]}. Chuẩn bị người bệnh rồi chuyển đi.',
                             kind='proc', needs=dict(bed=x['bed'], proc=x['name'], time=x['time']), _v=dict(case=case), **c)
    x = DISCHARGES[case]
    b = BEDS[x['bed']]
    return kit.base_task(ID, day, slot, serial, b['npc'], f'Ra viện giường {b["bed"]}',
                         f'Bác sĩ Khang cho giường {b["bed"]} ra viện hôm nay. Làm thủ tục và dặn dò trước khi về.',
                         kind='discharge', needs=dict(bed=x['bed'], rush=x.get('rush', '')), _v=dict(case=case), **c)


FIXED = ('needs', '_v')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t.get('kind') == 'shift':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the ward's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, tasks=0, calls=0, held=0, safety=0, washed=0, triaged=0, facts=[], report=None)


def initial() -> dict:
    return dict(v=1, intro=False, regulars={}, today=_fresh_today(0), learn=dict(n=0, caught=[]),
                stats=dict(tasks=0, calls=0, held=0, safety=0, washed=0, triaged=0, refusals=0, reports=0, honest=0),
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
    """How hard the ward leans on its nurses today: a busy day, and a nurse who snapped at the office."""
    marks = d['odd']['marks']
    return {'busy': 1, 'flu': 1, 'visit': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


# ================================================================ the actions
FREE = ('dd_intro', 'dd_rest')
NO_TICK = ('dd_intro', 'dd_rest', 'dd_read', 'dd_wash', 'dd_id', 'dd_check', 'dd_chart', 'dd_tq', 'dd_color', 'dd_teach', 'dd_desk', 'dd_odd',
           'dd_report', 'dd_explain')
PHYSICAL = ('dd_measure', 'dd_give', 'dd_bell', 'dd_send', 'dd_discharge', 'dd_triage')
GROUNDED = ('dd_give', 'dd_measure', 'dd_bell', 'dd_send', 'dd_discharge', 'dd_triage', 'dd_round', 'dd_hold', 'dd_done')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'dd_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Chị Hoa đang chờ ở bàn giao ca.')
    odd = d['odd']
    if name == 'dd_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    desk = d['desk']
    if name == 'dd_desk':
        result = kit.desk_choose(s, c, ID, desk, NC.DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'dd_odd':
        result = ao.reply(s, c, ID, odd, NC.ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    kit.desk_block(desk, 'Có chuyện trong khoa, quyết xong rồi làm tiếp nhé.')
    ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
    kit.need(not (ao.grounded(c, odd) and name in GROUNDED), 'Bạn đang bị tạm đình chỉ trực hết hôm nay. Tan ca, mai lên phòng Điều dưỡng trình bày.', 'grounded')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở khoa Nội.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, NC.DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(NC.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
        return
    _odd_tick(s, c, d, result)


def _odd_tick(s: dict, c: dict, d: dict, result: dict) -> None:
    """Someone around the ward turns up when today's plan says so (never over an open desk surprise)."""
    x = ao.tick(s, c, ID, d['odd'], NC.ODD, busy=d['desk']['ev'] is not None)
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None, known: bool = True) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc khoa Nội.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    if known:
        kit.need(t['known'], 'Tới giường chào và hỏi chuyện người bệnh trước đã.' if t['kind'] != 'triage' else 'Nghe cô Mỹ kể đã nhé.')
    kit.need(t['stage'] == 'open', 'Việc này đã xong.')
    return t


def _case_of(t: dict) -> dict:
    v = t['_v']
    return {'vitals': VITALS, 'med': MEDS, 'bell': BELLS, 'proc': PROCS, 'discharge': DISCHARGES}[t['kind']][v['case']]


# ---------------------------------------------------------------- chị Hoa beside you (the first three patient tasks)
def _learning(d: dict) -> bool:
    return d['learn']['n'] < LEARN


def _guard(d: dict, code: str, line: str) -> dict | None:
    """In the first tasks chị Hoa stops each kind of mistake once, before it is made (nothing is recorded)."""
    lr = d['learn']
    if lr['n'] >= LEARN or code in lr['caught'] or len(lr['caught']) >= 24:
        return None
    lr['caught'].append(code)
    return dict(message=f'✋ Chị Hoa giữ tay bạn lại: “{line}”', correct=False)


def _touch(c: dict, d: dict, t: dict) -> dict | None:
    """The first time the hands touch the patient: were they cleaned?"""
    if t['washed'] or any(r['code'] == 'hands' for r in cq.slips(t)):
        return None
    g = _guard(d, 'hands', 'Chưa sát khuẩn tay mà đã chạm người bệnh. Bóp chai ở đầu giường trước nhé.')
    if g:
        return g
    t['mistakes'] += 1
    cq.slip(t, 'hands', 2 if mod_of(c['day'])['id'] == 'audit' else 1, 'Điều dưỡng chạm vào tôi mà không sát khuẩn tay.', 'chưa sát khuẩn tay')
    return None


def _wash(s, c, d, p):
    t = _task(c, p, PATIENT)
    kit.need(not t['washed'], 'Đã sát khuẩn tay rồi.')
    t['washed'] = True
    kit.start_work(t)
    d['today']['washed'] += 1
    d['stats']['washed'] = min(10 ** 7, d['stats']['washed'] + 1)
    return dict(message='🧴 Bóp chai sát khuẩn ở đầu giường, xoa đủ sáu bước tới khi tay khô.')


def _id(s, c, d, p):
    t = _task(c, p, PATIENT)
    kit.need(t['idm'] is None, 'Đã xác định người bệnh rồi.')
    how = kit.one_of(p.get('how'), ID_HOW, 'Chọn cách xác định người bệnh.')
    b = BEDS[t['needs']['bed']]
    if how != 'open':
        g = _guard(d, 'id', 'Hỏi để người bệnh tự nói họ tên và ngày sinh, rồi đối chiếu vòng tay. Hỏi kiểu “có phải không” thì ai cũng dạ.')
        if g:
            return g
    t['idm'] = how
    kit.start_work(t)
    if how == 'open':
        return dict(message=f'🪪 “{b["name"]}, sinh ngày {b["dob"]}.” Vòng tay: {b["band"]} · {b["name"]} · {b["dob"]}.')
    if how == 'name':
        return dict(message=f'🪪 “{_who(t)} phải không ạ?” — “Ờ, phải.”')
    return dict(message=f'🪪 Nhìn số giường: {b["bed"]}.')


# ---------------------------------------------------------------- the handover
def _read(s, c, d, p):
    t = _task(c, p, ('shift',))
    bed = kit.one_of(p.get('bed'), BED_IDS, 'Giường không có trong sổ.')
    key = f'note:{bed}'
    kit.need(key not in t['seen'], 'Đã đọc ghi chú giường này.')
    t['seen'].append(key)
    kit.start_work(t)
    note = next(n for n in t['needs']['notes'] if n['bed'] == bed)
    return dict(message=f'📋 Giường {BEDS[bed]["bed"]}: {note["text"]}')


def _round(s, c, d, p):
    t = _task(c, p, ('shift',))
    first = kit.one_of(p.get('first'), BED_IDS, 'Chọn giường đi xem trước.')
    read = sum(1 for b in BED_IDS if f'note:{b}' in t['seen'])
    if first != t['_v']['first']:
        g = _guard(d, 'priority', 'Đọc lại sổ: giường nào đêm qua có chuyện bất thường thì xem trước.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'priority', 2, 'Giường có chuyện đêm qua mà sáng ra lại xem sau cùng.', 'xem chưa đúng giường ưu tiên')
    if read < len(BED_IDS):
        t['mistakes'] += 1
        cq.slip(t, 'skim', 1, 'Nhận ca mà không đọc hết sổ giao ca.', 'chưa đọc hết sổ giao ca')
    t['choice'] = first
    t['result'] = 'round'
    kit.start_work(t)
    ok = not cq.slips(t)
    _finish(s, c, d, t, 0, f'Nhận ca, đi buồng từ giường {BEDS[first]["bed"]}.', patient=False)
    return dict(message=f'📋 Nhận ca xong. Đi buồng bắt đầu từ giường {BEDS[first]["bed"]}.' +
                (' Chị Hoa gật đầu: “Đúng giường cần xem trước.”' if ok else ''), celebrate=ok)


# ---------------------------------------------------------------- vital signs
def _vals(t: dict) -> dict:
    """What the instruments show now (a re-measure replaces the first reading)."""
    x = _case_of(t)
    out = {}
    for k in SIGN_IDS:
        if f'{k}2' in t['seen']:
            out[k] = x.get('recheck', {}).get(k, x['vals'][k])
        elif k in t['seen']:
            out[k] = x['vals'][k]
    return out


def _abn(t: dict) -> list:
    return [k for k, v in _vals(t).items() if abnormal(k, v)]


def _measure(s, c, d, p):
    t = _task(c, p, ('vitals',))
    sign = kit.one_of(p.get('sign'), SIGN_IDS, 'Chỉ số không có.')
    kit.need(sign not in t['seen'], 'Đã đo chỉ số này rồi.')
    stop = _touch(c, d, t)
    if stop:
        return stop
    t['seen'].append(sign)
    kit.start_work(t)
    v, sg = _case_of(t)['vals'][sign], SIGNS[sign]
    if sign == 'pain':
        return dict(message=f'{sg["emoji"]} “Đau mấy điểm trên mười ạ?” — “{v}.”')
    return dict(message=f'{sg["emoji"]} {sg["name"]}: {v} {sg["unit"]}.')


def _recheck(s, c, d, p):
    t = _task(c, p, ('vitals',))
    sign = kit.one_of(p.get('sign'), SIGN_IDS, 'Chỉ số không có.')
    kit.need(sign in t['seen'], 'Đo lần đầu đã.')
    kit.need(f'{sign}2' not in t['seen'], 'Đã đo lại rồi.')
    kit.need(t['chart'] is None, 'Đã ghi phiếu rồi.')
    t['seen'].append(f'{sign}2')
    x = _case_of(t)
    v = x.get('recheck', {}).get(sign, x['vals'][sign])
    sg = SIGNS[sign]
    head = 'Chỉnh lại kẹp, xoa ấm tay, đo ngón khác' if sign == 'spo2' else 'Đo lại'
    return dict(message=f'🔁 {head}: {sg["name"]} {v} {sg["unit"]}.')


def _chart(s, c, d, p):
    t = _task(c, p, ('vitals',))
    kit.need(t['chart'] is None, 'Phiếu đã ghi rồi.')
    kit.need(all(k in t['seen'] for k in SIGN_IDS), 'Đo đủ năm chỉ số rồi mới ghi phiếu.')
    raw = p.get('vals')
    kit.need(isinstance(raw, dict) and set(raw) <= set(SIGN_IDS), 'Phiếu ghi sai mẫu.')
    typed = {k: kit.text(str(raw.get(k, '')), 12, 0) for k in SIGN_IDS}
    for k, v in typed.items():
        kit.need(v.strip(), f'Còn ô {SIGNS[k]["name"].lower()} chưa ghi.')
    want = _vals(t)
    wrong = [k for k in SIGN_IDS if _num(typed[k]) != _num(want[k])]
    if wrong:
        g = _guard(d, 'chart', f'Ô {SIGNS[wrong[0]]["name"].lower()} chưa khớp số vừa đo. Nhìn máy đo rồi ghi lại nhé.')
        if g:
            return g
    t['chart'] = {k: typed[k].strip()[:12] for k in SIGN_IDS}
    if wrong:
        t['mistakes'] += 1
        names = ', '.join(SIGNS[k]['name'].lower() for k in wrong)
        cq.slip(t, 'chart', 2, f'Phiếu theo dõi ghi sai {names} so với số đo thật.', 'ghi phiếu sai số đo')
        return dict(message=f'📝 Đã ghi phiếu. (Ô {names} không khớp số đo.)', correct=False)
    return dict(message='📝 Ghi phiếu theo dõi: đủ năm chỉ số, đúng giờ đo.')


def _call(s, c, d, p):
    t = _task(c, p, ('vitals', 'proc', 'discharge'))
    kit.need(not t['called'], 'Đã báo bác sĩ rồi.')
    who = _who(t)
    if t['kind'] == 'vitals':
        kit.need(t['seen'], 'Đo ít nhất một chỉ số rồi mới báo.')
        signs = kit.id_list(p.get('signs') or [], [k for k in SIGN_IDS if k in t['seen']], 5, 'Chọn chỉ số muốn báo.')
        kit.need(signs, 'Chọn chỉ số bất thường muốn báo bác sĩ.')
        t['called'] = list(signs)
        _count_call(d)
        bad = _abn(t)
        vals = _vals(t)
        said = ', '.join(f'{SIGNS[k]["name"].lower()} {vals[k]}' for k in signs)
        if not bad:
            return dict(message=f'📞 Báo bác sĩ Khang: {said}. — “Các số này trong ngưỡng, cảm ơn em đã báo. Cứ theo dõi tiếp nhé.”')
        miss = [k for k in bad if k not in signs]
        if miss:
            t['mistakes'] += 1
            cq.slip(t, 'sbar', 1, f'Báo bác sĩ mà quên nói {", ".join(SIGNS[k]["name"].lower() for k in miss)}.', 'báo bác sĩ thiếu chỉ số')
        x = _case_of(t)
        tail = ' “Em đo lại ngón khác chưa? Máy kẹp lỏng hay báo sai lắm.”' if 'recheck' in x and 'spo2' in bad else ' “Anh tới ngay. Em ở cạnh người bệnh nhé.”'
        return dict(message=f'📞 Báo bác sĩ Khang: {said}.{tail}', celebrate=not miss)
    reason = kit.one_of(p.get('reason'), ('consent', 'paper', 'unsure'), 'Chọn điều cần báo bác sĩ.')
    x = _case_of(t)
    t['called'] = [reason]
    _count_call(d)
    if t['kind'] == 'proc':
        if reason == 'consent' and x['variant'] == 'unsigned' and 'consent' in t['seen']:
            t['seen'].append('signed')
            return dict(message=f'📞 Bác sĩ Khang tới giải thích từng bước nội soi, nói rõ lợi ích và rủi ro, trả lời hết câu hỏi. {who} thở phào, ký giấy cam đoan.',
                        celebrate=True)
        if x['variant'] == 'refuse' and 'consent' in t['seen']:
            return dict(message=f'📞 Bác sĩ Khang tới ngồi nói chuyện với {who}, giải thích vì sao cần mổ và nghe hết điều {who} lo. '
                                f'{who} vẫn muốn suy nghĩ thêm. Bác sĩ dặn: tôn trọng quyết định, hoãn ca, ghi hồ sơ.')
        return dict(message=f'📞 Bác sĩ Khang: “Anh xem rồi, hồ sơ ổn. Em cứ chuẩn bị theo quy trình.”')
    if reason == 'paper' and x['paper'] == 'unsigned' and 'paper' in t['seen']:
        t['seen'].append('signed')
        return dict(message='📞 Bác sĩ Khang tới khám lại, ký giấy ra viện, đưa đơn thuốc in sẵn. Chị Ngân lầm bầm nhưng chờ được.', celebrate=True)
    return dict(message='📞 Bác sĩ Khang: “Giấy tờ đủ rồi em. Làm tiếp đi.”')


def _count_call(d: dict) -> None:
    d['today']['calls'] += 1
    d['stats']['calls'] = min(10 ** 7, d['stats']['calls'] + 1)


def _done(s, c, d, p):
    t = _task(c, p, ('vitals',))
    kit.need(t['chart'] is not None, 'Ghi phiếu theo dõi rồi mới xong lượt đo.')
    bad = _abn(t)
    if bad and not t['called']:
        g = _guard(d, 'escalate', 'Có chỉ số ngoài thẻ báo động mà chưa báo bác sĩ. Báo đi em, đừng ngại.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'missed', 3, f'{SIGNS[bad[0]]["name"]} bất thường mà không ai báo bác sĩ.', 'không báo bác sĩ khi bất thường', safety=True)
    if t['idm'] != 'open':
        t['mistakes'] += 1
        cq.slip(t, 'id', 1, 'Đo xong mà chưa hỏi tên, ngày sinh để ghi đúng phiếu.', 'chưa xác định đúng người bệnh')
    vals = _vals(t)
    t['result'] = 'abnormal' if bad else 'normal'
    if bad:
        line = ', '.join(f'{SIGNS[k]["name"].lower()} {vals[k]}' for k in bad)
        fact = f'{_short(t["needs"]["bed"])}: {line}' + (', đã báo bác sĩ Khang.' if t['called'] else ', CHƯA báo bác sĩ.')
    else:
        fact = f'{_short(t["needs"]["bed"])}: đo đủ năm chỉ số, đều trong ngưỡng.'
    _fact(d, t, fact, key=bool(bad), lie=f'{_short(t["needs"]["bed"])}: đã đo và báo bác sĩ đầy đủ.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, f'Đo dấu hiệu sinh tồn giường {BEDS[t["needs"]["bed"]]["bed"]}.')
    return dict(message=f'✅ Xong lượt đo. {msg}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- medication
def _check(s, c, d, p):
    t = _task(c, p, ('med', 'proc', 'discharge'))
    allowed = {'med': MED_CHECKS, 'proc': PROC_KEYS, 'discharge': DIS_CHECKS}[t['kind']]
    what = kit.one_of(p.get('what'), allowed, 'Kiểm tra này không dành cho việc đang làm.')
    kit.need(what not in t['seen'], 'Đã kiểm tra rồi.')
    x = _case_of(t)
    b = BEDS[t['needs']['bed']]
    kit.start_work(t)
    if t['kind'] == 'med':
        if what == 'sugar':
            kit.need(x['drug'] == 'pen', 'Y lệnh này không cần đo đường huyết.')
            stop = _touch(c, d, t)
            if stop:
                return stop
        t['seen'].append(what)
        if what == 'allergy':
            return dict(message=f'🔴 Vòng dị ứng: {ALLERGY[b["allergy"]]}.' if b['allergy'] else '⚪ Không có vòng dị ứng. “Có dị ứng thuốc gì không ạ?” — “Không.”')
        if what == 'label':
            tray = DRUGS[x.get('tray', x['drug'])]['name']
            card = x.get('card') or dict(name=b['name'])
            return dict(message=f'🏷️ Nhãn khay của khoa dược: {tray} · {card["name"]}.')
        return dict(message='🩸 Đường huyết: máy báo THẤP (đỏ). Ông Bảy vã mồ hôi, tay run.' if x.get('sugar') == 'low'
                    else '🩸 Đường huyết: máy báo trong ngưỡng (xanh).')
    if t['kind'] == 'proc':
        t['seen'].append(what)
        if what == 'consent':
            if x['variant'] == 'refuse':
                return dict(message='📝 Giấy cam đoan đã ký từ hôm qua. Nhưng Tuấn nói: “Em đổi ý rồi, không mổ đâu. Mẹ em bảo đắp lá là lành.”')
            return dict(message='📝 ' + NC.PROC_TEXT['consent'][x['consent']])
        if what == 'fasting':
            return dict(message='🍽️ ' + NC.PROC_TEXT['fasting'][x['fasting']])
        if what == 'allergy':
            return dict(message=f'🔴 Vòng dị ứng: {ALLERGY[b["allergy"]]}. Ghi rõ lên phiếu chuyển.' if b['allergy'] else '⚪ Không có dị ứng.')
        return dict(message='💍 ' + NC.PROC_TEXT['jewel'][x['jewel']])
    t['seen'].append(what)
    return dict(message={'paper': '📄 ', 'bhyt': '💳 ', 'cannula': '🩹 '}[what] + NC.DISCHARGE_TEXT[what][x[what]])


def _med_gate(c: dict, d: dict, t: dict, x: dict) -> dict | None:
    """chị Hoa's catches before a dose leaves the tray (first tasks only); None = go on."""
    v = x['variant']
    if t['idm'] != 'open':
        g = _guard(d, 'id', 'Chưa hỏi họ tên, ngày sinh để đối chiếu với phiếu. Đúng người trước đã.')
        if g:
            return g
    if 'allergy' not in t['seen'] or (v == 'allergy'):
        g = _guard(d, 'allergy', 'Xem vòng dị ứng và so với nhóm thuốc trên phiếu chưa?')
        if g:
            return g
    if 'label' not in t['seen'] or v == 'label':
        g = _guard(d, 'label', 'Nhãn khay của khoa dược có khớp y lệnh không? Đọc nhãn trước khi cho.')
        if g:
            return g
    if x['drug'] == 'pen' and ('sugar' not in t['seen'] or v == 'lowsugar'):
        g = _guard(d, 'sugar', 'Y lệnh dặn đo đường huyết trước. Đọc dòng dặn cuối phiếu nhé.')
        if g:
            return g
    if v == 'npo':
        g = _guard(d, 'npo', 'Đọc biển đầu giường: cô đang nhịn ăn uống chờ nội soi. Thuốc uống lúc này thì hỏi lại bác sĩ.')
        if g:
            return g
    if v == 'wrongpt':
        g = _guard(d, 'wrongpt', 'Tên và ngày sinh trên phiếu có khớp người đang nằm đây không?')
        if g:
            return g
    return None


def _give(s, c, d, p):
    t = _task(c, p, ('med',))
    x = _case_of(t)
    v = x['variant']
    who = _who(t)
    stop = _touch(c, d, t)
    if stop:
        return stop
    if v == 'refuse' and t['said'] not in ('yes', 'pushed'):
        kit.need(t['said'] != 'no', f'{who} đã nói không. Người bệnh có quyền từ chối: giữ thuốc và báo bác sĩ.')
        t['said'] = 'refused'
        kit.start_work(t)
        return dict(message=f'🙅 {x["refuse"]}')
    gate = _med_gate(c, d, t, x)
    if gate:
        return gate
    if t['idm'] != 'open':
        t['mistakes'] += 1
        if v == 'wrongpt':
            cq.slip(t, 'wrong_patient', 3, 'Phiếu và khay thuốc của người khác mà vẫn cho uống.', 'cho thuốc nhầm người', safety=True)
        else:
            cq.slip(t, 'id', 2, 'Cho thuốc mà không hỏi tên, ngày sinh, không xem vòng tay.', 'không xác định người bệnh')
    elif v == 'wrongpt':
        t['mistakes'] += 1
        cq.slip(t, 'wrong_patient', 3, 'Phiếu ghi tên người khác, ngày sinh khác mà vẫn cho uống.', 'cho thuốc nhầm người', safety=True)
    if v == 'allergy':
        t['mistakes'] += 1
        cq.slip(t, 'allergy', 3, 'Tôi đeo vòng dị ứng nhóm P mà vẫn bị truyền thuốc nhóm P.', 'cho thuốc trùng nhóm dị ứng', safety=True)
    elif 'allergy' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'no_allergy', 1, 'Cho thuốc mà không hỏi tôi dị ứng gì.', 'chưa kiểm dị ứng')
    if v == 'label':
        t['mistakes'] += 1
        cq.slip(t, 'label', 3, 'Khay thuốc ghi một thuốc, phiếu ghi thuốc khác mà vẫn cho.', 'nhãn khay khác y lệnh', safety=True)
    elif 'label' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'no_label', 1, 'Không đọc nhãn khay trước khi cho thuốc.', 'chưa đọc nhãn khay')
    if x['drug'] == 'pen':
        if v == 'lowsugar':
            t['mistakes'] += 1
            cq.slip(t, 'low_sugar', 3, 'Đường huyết thấp mà vẫn tiêm thuốc tiểu đường, ông Bảy lả đi.', 'không làm theo dòng dặn của y lệnh', safety=True)
        elif 'sugar' not in t['seen']:
            t['mistakes'] += 1
            cq.slip(t, 'no_sugar', 2, 'Y lệnh dặn đo đường huyết trước mà không đo.', 'chưa đo đường huyết')
    if v == 'npo':
        t['mistakes'] += 1
        cq.slip(t, 'npo', 2, 'Đang nhịn ăn uống chờ nội soi mà cho uống thuốc, phải lùi lịch nội soi.', 'cho uống khi đang nhịn ăn')
    t['choice'] = 'give'
    t['result'] = 'given'
    drug = t['needs']['order']['drug']
    unsafe = cq.safety(t)
    bed = t['needs']['bed']
    _fact(d, t, f'{_short(bed)}: đã cho {drug} theo y lệnh' + (' — có sự cố, đã lập báo cáo.' if unsafe else '.'), key=unsafe,
          lie=f'{_short(bed)}: đã đối chiếu đủ người, dị ứng, nhãn khay trước khi cho thuốc.' if cq.slips(t) else None)
    line = f'Thực hiện y lệnh: {drug}, {t["needs"]["order"]["route"].lower()}, ký phiếu thực hiện.'
    msg = _finish(s, c, d, t, BONUS, line)
    if unsafe:
        msg += ' 📋 Chị Hoa lập báo cáo sự cố, bác sĩ Khang tới theo dõi người bệnh ngay.'
    return dict(message=f'💊 {msg}'.strip(), celebrate=not cq.slips(t), correct=not unsafe)


HOLD_NEED = {'allergy': 'allergy', 'wrongpt': 'wrongpt', 'label': 'label', 'refuse': 'refuse', 'npo': 'npo', 'lowsugar': 'lowsugar',
             'ate': 'ate', 'unsigned': 'consent'}
HOLD_OUTCOME = {
    'allergy': 'Bác sĩ Khang cảm ơn, đổi sang kháng sinh khác nhóm, ghi lại cảnh báo dị ứng to hơn trên hồ sơ.',
    'wrongpt': 'Phiếu và khay được trả về đúng giường 4 của bà Trần Thị Tứ. Khoa dán nhãn “trùng tên” lên hai hồ sơ.',
    'label': 'Khoa dược xin lỗi, đổi khay đúng thuốc. Nhãn sai đó là thuốc nhóm P, mà Tuấn dị ứng nhóm P.',
    'refuse': 'Bác sĩ Khang tới hỏi chuyện, tìm cách khác người bệnh chịu được. Hồ sơ ghi rõ: người bệnh từ chối, đã giải thích, đã báo bác sĩ.',
    'npo': 'Bác sĩ Khang dặn để sau nội soi mới uống. Cô Liên vẫn kịp ca nội soi 10 giờ.',
    'lowsugar': 'Bác sĩ Khang tới ngay, xử trí hạ đường huyết theo phác đồ khoa, dặn đo lại. Ông Bảy tỉnh táo dần.',
    'ate': 'Phòng nội soi dời ca sang chiều mai. Cô Liên được dặn lại kỹ giờ nhịn ăn.',
    'consent': 'Ca thủ thuật lùi lại một chút, chờ bác sĩ giải thích và người bệnh tự quyết.',
}


def _hold(s, c, d, p):
    t = _task(c, p, ('med', 'proc'))
    reason = kit.one_of(p.get('reason'), HOLD, 'Chọn lý do giữ lại.')
    x = _case_of(t)
    v = x['variant']
    who = _who(t)
    need = HOLD_NEED.get(v)
    allowed = (('allergy', 'wrongpt', 'label', 'refuse', 'npo', 'lowsugar', 'unsure') if t['kind'] == 'med'
               else ('ate', 'refuse', 'consent', 'unsure'))
    kit.need(reason in allowed, 'Lý do này không hợp với việc đang làm.')
    if reason == 'unsure' and not need:
        _count_call(d)
        return dict(message='📞 Bác sĩ Khang xem lại: “Y lệnh đúng rồi em, cứ làm theo quy trình.”')
    kit.start_work(t)
    _count_call(d)
    if not need:
        t['mistakes'] += 1
        cq.slip(t, 'needless', 1, 'Có y lệnh, mọi thứ khớp mà không làm, người bệnh lỡ cữ.', 'giữ lại khi không cần')
    elif reason not in (need, 'unsure') and not (v == 'unsigned' and reason == 'consent'):
        t['mistakes'] += 1
        cq.slip(t, 'reason', 1, 'Giữ lại đúng lúc, nhưng báo bác sĩ chưa đúng lý do.', 'báo chưa đúng lý do')
    if need == 'refuse' and t['said'] not in ('refused', 'no') and not (t['kind'] == 'proc' and 'consent' in t['seen']):
        t['mistakes'] += 1
        cq.slip(t, 'guess', 1, 'Chưa hỏi người bệnh mà đã ghi là từ chối.', 'ghi từ chối khi chưa hỏi')
    if need == 'lowsugar' and 'sugar' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'guess', 1, 'Giữ thuốc mà chưa đo đường huyết, bác sĩ không có số để quyết.', 'chưa đo đường huyết')
    t['choice'] = 'hold'
    t['result'] = reason
    d['today']['held'] += 1
    d['stats']['held'] = min(10 ** 7, d['stats']['held'] + 1)
    if need == 'refuse':
        d['stats']['refusals'] = min(10 ** 7, d['stats']['refusals'] + 1)
    bed = t['needs']['bed']
    what = t['needs']['order']['drug'] if t['kind'] == 'med' else t['needs']['proc'].lower()
    _fact(d, t, f'{_short(bed)}: giữ lại {what} ({HOLD[reason].lower()}), đã báo bác sĩ Khang.', key=True,
          lie=f'{_short(bed)}: mọi việc đúng y lệnh, không có gì cần báo.' if not need else None)
    out = HOLD_OUTCOME[need] if need else 'Bác sĩ Khang xem lại: “Mọi thứ khớp mà em, lần sau cứ thực hiện.”'
    msg = _finish(s, c, d, t, BONUS, f'Giữ lại, báo bác sĩ: {HOLD[reason].lower()}.')
    return dict(message=f'✋ Giữ lại, báo bác sĩ: {HOLD[reason].lower()}. {out} {msg}'.strip(), celebrate=not cq.slips(t))


def _tr(t: dict) -> dict:
    i = _npc_index(t)
    return folk.traits(t['id'], PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None)


def _explain(s, c, d, p):
    """Ask why and explain; the patient decides (hidden traits). A procedure's consent stays the doctor's to take."""
    t = _task(c, p, ('med', 'proc'))
    x = _case_of(t)
    who = _who(t)
    tr = _tr(t)
    kit.start_work(t)
    if t['kind'] == 'med':
        kit.need(t['said'] == 'refused', 'Người bệnh chưa từ chối gì.')
        if tr['mood'] + tr['honest'] >= 100:
            t['said'] = 'yes'
            return dict(message=f'🗣️ Bạn hỏi vì sao, giải thích thuốc dùng để làm gì, có bác sĩ chỉ định. {who} nghĩ một lúc: “Thôi được, đưa đây.”',
                        celebrate=True)
        t['said'] = 'no'
        return dict(message=f'🗣️ Bạn hỏi vì sao, giải thích kỹ. {who} vẫn lắc đầu: “Không là không.” Đó là quyền của người bệnh.')
    kit.need('consent' in t['seen'], 'Xem giấy cam đoan trước đã.')
    kit.need(x['variant'] in ('unsigned', 'refuse') and 'explained' not in t['seen'], 'Người bệnh không có điều gì cần giải thích thêm.')
    t['seen'].append('explained')
    if x['variant'] == 'unsigned':
        return dict(message=f'🗣️ Bạn kể sơ các bước, hỏi điều cô lo nhất. {who} bớt run, nhưng giấy cam đoan phải có bác sĩ giải thích và ký cùng.')
    t['said'] = 'no'
    line = '“Thôi để em nghe bác sĩ nói lại đã, giờ em chưa mổ.”' if tr['mood'] >= 50 else '“Em nói rồi, không mổ.”'
    return dict(message=f'🗣️ Bạn hỏi vì sao Tuấn đổi ý, giải thích những gì mình biết. Tuấn: {line}')


def _push(s, c, d, p):
    t = _task(c, p, ('med', 'proc'))
    who = _who(t)
    if t['kind'] == 'med':
        kit.need(t['said'] in ('refused', 'no'), 'Người bệnh chưa từ chối gì.')
    else:
        kit.need(_case_of(t)['variant'] == 'refuse' and 'consent' in t['seen'], 'Người bệnh không từ chối gì.')
    g = _guard(d, 'push', 'Không ép. Người bệnh có quyền từ chối: hỏi vì sao, giải thích, rồi báo bác sĩ.')
    if g:
        return g
    t['mistakes'] += 1
    surgery = t['kind'] == 'proc'
    cq.slip(t, 'pressure', 3 if surgery else 2, 'Tôi đã nói không mà vẫn bị ép, dọa bệnh nặng thêm.', 'ép người bệnh', safety=surgery)
    t['said'] = 'pushed'
    return dict(message=f'😤 “Không làm là nặng thêm đó!” {who} miễn cưỡng gật đầu, mặt hằm hằm.', correct=False)


# ---------------------------------------------------------------- procedures
def _jewel(s, c, d, p):
    t = _task(c, p, ('proc',))
    x = _case_of(t)
    kit.need('jewel' in t['seen'], 'Xem người bệnh có đeo gì không đã.')
    kit.need(x['jewel'] and 'jewel_off' not in t['seen'], 'Không có gì cần tháo.')
    stop = _touch(c, d, t)
    if stop:
        return stop
    t['seen'].append('jewel_off')
    return dict(message='💍 Tháo dây chuyền, nhẫn, cho vào túi niêm phong, giao người nhà ký nhận.')


def _send(s, c, d, p):
    t = _task(c, p, ('proc',))
    x = _case_of(t)
    v = x['variant']
    who = _who(t)
    if v == 'refuse' and 'consent' in t['seen']:
        kit.need(t['said'] == 'pushed', f'{who} đã nói không mổ. Không chuyển người bệnh đi khi họ không đồng ý.')
    signed = x['consent'] == 'signed' or 'signed' in t['seen']
    if t['idm'] != 'open':
        g = _guard(d, 'id', 'Chuyển người bệnh đi thủ thuật mà chưa hỏi họ tên, ngày sinh, đối chiếu vòng tay?')
        if g:
            return g
    if 'consent' not in t['seen'] or not signed:
        g = _guard(d, 'consent', 'Xem giấy cam đoan đã. Chưa ký thì bác sĩ phải giải thích để người bệnh tự quyết.')
        if g:
            return g
    if 'fasting' not in t['seen'] or x['fasting'] == 'no':
        g = _guard(d, 'fasting', 'Hỏi lại giờ ăn uống cuối cùng chưa?')
        if g:
            return g
    if t['idm'] != 'open':
        t['mistakes'] += 1
        cq.slip(t, 'id', 2, 'Chuyển đi thủ thuật mà không đối chiếu tên, ngày sinh.', 'không xác định người bệnh')
    if v == 'refuse':
        t['mistakes'] += 1
        cq.slip(t, 'consent', 3, 'Người bệnh đã rút lại đồng ý mà vẫn bị chuyển đi mổ.', 'thủ thuật khi người bệnh không đồng ý', safety=True)
    elif not signed:
        t['mistakes'] += 1
        cq.slip(t, 'consent', 3, 'Chuyển đi thủ thuật khi chưa có giấy cam đoan.', 'chưa có giấy cam đoan', safety=True)
    if x['fasting'] == 'no':
        t['mistakes'] += 1
        cq.slip(t, 'ate', 2, 'Người bệnh đã ăn sáng mà vẫn chuyển đi, phòng thủ thuật phải trả về.', 'chưa nhịn ăn đủ')
    elif 'fasting' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'no_fasting', 1, 'Không hỏi giờ ăn uống cuối cùng trước thủ thuật.', 'chưa hỏi nhịn ăn')
    if 'allergy' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'no_allergy', 1, 'Phiếu chuyển không ghi dị ứng.', 'chưa ghi dị ứng')
    if x['jewel'] and 'jewel_off' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'jewel', 1, 'Lên phòng mổ còn đeo dây chuyền, nhẫn; phải tháo ở cửa phòng.', 'chưa tháo trang sức')
    elif 'jewel' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'no_jewel', 1, 'Không xem người bệnh còn đeo trang sức không.', 'chưa xem trang sức')
    t['choice'] = 'send'
    t['result'] = 'sent'
    unsafe = cq.safety(t)
    bed = t['needs']['bed']
    _fact(d, t, f'{_short(bed)}: đã chuyển đi {t["needs"]["proc"].lower()}' + (' — có sự cố, đã lập báo cáo.' if unsafe else ', hồ sơ đủ.'), key=True,
          lie=f'{_short(bed)}: đã kiểm đủ giấy cam đoan, nhịn ăn, dị ứng, trang sức.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, f'Chuẩn bị và chuyển người bệnh đi {t["needs"]["proc"].lower()}.')
    if unsafe:
        msg += ' 📋 Phòng thủ thuật dừng ca, chị Hoa lập báo cáo sự cố.'
    return dict(message=f'🛏️ Đẩy giường sang phòng thủ thuật, bàn giao hồ sơ. {msg}'.strip(), celebrate=not cq.slips(t), correct=not unsafe)


# ---------------------------------------------------------------- going home
def _cannula(s, c, d, p):
    t = _task(c, p, ('discharge',))
    x = _case_of(t)
    kit.need(x['cannula'] and 'cannula_off' not in t['seen'], 'Không còn kim luồn nào.')
    stop = _touch(c, d, t)
    if stop:
        return stop
    t['seen'].append('cannula_off')
    kit.start_work(t)
    return dict(message='🩹 Rút kim luồn, ấn bông gòn vài phút, dán băng. Chỗ kim sạch, không sưng.')


def _teach(s, c, d, p):
    t = _task(c, p, ('discharge',))
    topic = kit.one_of(p.get('topic'), TEACH, 'Nội dung dặn không có.')
    kit.need(topic not in t['teach'], 'Đã dặn điều này rồi.')
    t['teach'].append(topic)
    kit.start_work(t)
    lines = {'tai_kham': 'Tái khám sau một tuần, mang giấy ra viện theo.', 'dau_hieu': 'Sốt cao, khó thở, đau tăng, vết thương sưng đỏ: quay lại ngay, đừng chờ.',
             'thuoc': 'Uống đúng như đơn in sẵn, không tự thêm, bớt hay ngưng.', 'an_uong': 'Ăn đúng bữa, ít ngọt, tự đo đường huyết theo lịch bác sĩ dặn.',
             'vet': 'Giữ vết thương, nẹp khô sạch, kê cao, không tự tháo.', 'giay': 'Cất giấy ra viện, thẻ BHYT; tái khám mang theo.'}
    return dict(message=f'{TEACH[topic][0]} Dặn: {lines[topic]}')


def _teachback(s, c, d, p):
    t = _task(c, p, ('discharge',))
    kit.need(t['teach'], 'Dặn dò trước đã rồi mới nhờ người bệnh nhắc lại.')
    kit.need('teachback' not in t['seen'], 'Đã nhờ nhắc lại rồi.')
    t['seen'].append('teachback')
    x = _case_of(t)
    miss = [k for k in x['topics'] if k not in t['teach']]
    who = _who(t)
    if miss:
        return dict(message=f'🔁 {who} nhắc lại được những điều bạn dặn, rồi hỏi: “Còn {TEACH[miss[0]][1].lower()} thì sao cô?”')
    return dict(message=f'🔁 {who} nhắc lại đủ từng điều. Người nhà ghi vào điện thoại.', celebrate=True)


def _discharge(s, c, d, p):
    t = _task(c, p, ('discharge',))
    x = _case_of(t)
    signed = x['paper'] == 'signed' or 'signed' in t['seen']
    if 'paper' not in t['seen'] or not signed:
        g = _guard(d, 'paper', 'Giấy ra viện có chữ ký bác sĩ chưa? Chưa có thì chưa cho về.')
        if g:
            return g
    if x['cannula'] and 'cannula_off' not in t['seen']:
        g = _guard(d, 'cannula', 'Kim luồn trên tay còn kìa. Rút trước khi về nhé.')
        if g:
            return g
    if not signed:
        t['mistakes'] += 1
        cq.slip(t, 'no_paper', 2, 'Về nhà không có giấy ra viện, không đơn thuốc, phải quay lại.', 'cho về khi chưa có giấy ra viện')
    if x['cannula'] and 'cannula_off' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'cannula', 2, 'Về tới nhà mới thấy kim luồn còn trên tay.', 'quên rút kim luồn')
    if x['bhyt'] == 'expired' and 'bhyt' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'bhyt', 1, 'Ra tới cổng mới biết thẻ bảo hiểm hết hạn, phải quay lại làm thủ tục.', 'chưa xem thẻ BHYT')
    miss = [k for k in x['topics'] if k not in t['teach']]
    if miss:
        t['mistakes'] += 1
        cq.slip(t, 'teach', 1, f'Về nhà không biết {TEACH[miss[0]][1].lower()}.', 'dặn dò chưa đủ')
    if 'teachback' not in t['seen']:
        t['mistakes'] += 1
        cq.slip(t, 'no_teachback', 1, 'Dặn một tràng mà không hỏi lại xem tôi nhớ chưa.', 'không nhờ người bệnh nhắc lại')
    if t['idm'] != 'open':
        t['mistakes'] += 1
        cq.slip(t, 'id', 1, 'Giao giấy ra viện mà không đối chiếu tên, ngày sinh.', 'chưa đối chiếu người bệnh')
    t['choice'] = 'home'
    t['result'] = 'home'
    bed = t['needs']['bed']
    _fact(d, t, f'{_short(bed)}: đã ra viện, rút kim, dặn dò, có giấy ra viện.' if not cq.slips(t) else
          f'{_short(bed)}: đã ra viện (còn thiếu: {cq.slips(t)[0]["note"]}).', key=False,
          lie=f'{_short(bed)}: ra viện đủ thủ tục, dặn dò đầy đủ.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, f'Làm thủ tục ra viện giường {BEDS[bed]["bed"]}.')
    return dict(message=f'🏠 {_who(t)} chào cả phòng ra về. {msg}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- call bells
def _bell(s, c, d, p):
    t = _task(c, p, ('bell',))
    x = _case_of(t)
    opts = {o[0]: o for o in x['options']}
    choice = kit.one_of(p.get('choice'), opts, 'Chọn cách trả lời chuông.')
    _, label, grade, outcome, touch = opts[choice]
    if grade == 'unsafe':
        g = _guard(d, f'unsafe:{t["_v"]["case"]}', 'Khoan đã, cách đó có thể làm người bệnh gặp nguy. Nghĩ lại nhé.')
        if g:
            return g
    if touch:
        stop = _touch(c, d, t)
        if stop:
            return stop
    kit.start_work(t)
    if grade == 'ok':
        t['mistakes'] += 1
        cq.slip(t, 'meh', 1, 'Được việc nhưng chưa chu đáo.', 'trả lời chuông chưa trọn')
        if choice == 'long':
            for o in c['tasks']:
                if o.get('career') == ID and o['id'] != t['id'] and o['status'] not in ('completed', 'cancelled', 'referred') and 'patience' in o:
                    o['patience'] = max(25, o['patience'] - 8)
    elif grade == 'bad':
        t['mistakes'] += 1
        cq.slip(t, 'bad', 2, outcome, 'trả lời chuông chưa đúng')
    elif grade == 'unsafe':
        t['mistakes'] += 1
        cq.slip(t, 'unsafe', 3, outcome, 'làm người bệnh gặp nguy', safety=True)
    if choice in ('call', 'assess', 'measure'):
        _count_call(d)
    t['choice'] = choice
    t['result'] = grade
    bed = t['needs']['bed']
    _fact(d, t, f'{_short(bed)}: chuông gọi — {label.split(" ", 1)[1].lower()}.', key=grade == 'unsafe' or choice in ('call', 'assess', 'measure'),
          lie=f'{_short(bed)}: chuông gọi, đã xử lý chu đáo.' if grade in ('bad', 'unsafe') else None)
    msg = _finish(s, c, d, t, BONUS, f'Trả lời chuông giường {BEDS[bed]["bed"]}.')
    return dict(message=f'{outcome} {msg}'.strip(), celebrate=grade == 'good', correct=grade != 'unsafe')


# ---------------------------------------------------------------- triage
def _tq(s, c, d, p):
    t = _task(c, p, ('triage',))
    i = kit.integer(p.get('i'), 0, len(t['_v']['cases']) - 1)
    what = kit.one_of(p.get('what'), ('ask', 'quick'), 'Chọn hỏi hay đo nhanh.')
    key = f'{what}:{i}'
    kit.need(key not in t['seen'], 'Đã xem rồi.')
    t['seen'].append(key)
    kit.start_work(t)
    x = TRIAGE[t['_v']['cases'][i]]
    return dict(message=f'{"👂" if what == "ask" else "🩺"} {x["who"]}: {x[what]}')


def _color(s, c, d, p):
    t = _task(c, p, ('triage',))
    i = kit.integer(p.get('i'), 0, len(t['_v']['cases']) - 1)
    color = kit.one_of(p.get('color'), NC.COLORS, 'Màu không có trên thẻ.')
    t['colors'][str(i)] = color
    kit.start_work(t)
    e, name, when = NC.COLORS[color]
    return dict(message=f'{e} {t["needs"]["queue"][i]["who"]}: thẻ {name.lower()} · {when.lower()}.')


def _triage(s, c, d, p):
    t = _task(c, p, ('triage',))
    cases = t['_v']['cases']
    kit.need(len(t['colors']) == len(cases), 'Phát thẻ màu cho cả ba người đã.')
    order = NC.COLOR_ORDER
    under_red = [i for i, k in enumerate(cases) if TRIAGE[k]['best'] == 'do' and t['colors'][str(i)] != 'do']
    if under_red:
        g = _guard(d, 'under', f'Xem lại {t["needs"]["queue"][under_red[0]]["who"].lower()}: dấu hiệu đó trên thẻ là màu gì?')
        if g:
            return g
    lines = []
    worst = 0
    for i, k in enumerate(cases):
        x = TRIAGE[k]
        got = t['colors'][str(i)]
        ok = got == x['best'] or got in x.get('ok', ())
        gi, bi = order.index(got), order.index(x['best'])
        e = NC.COLORS[x['best']][0]
        if ok:
            lines.append(f'{NC.COLORS[got][0]} {x["who"]}: đúng.')
            continue
        if f'ask:{i}' not in t['seen'] and f'quick:{i}' not in t['seen']:
            t['mistakes'] += 1
            cq.slip(t, 'blind', 1, 'Phát thẻ màu mà không hỏi, không đo gì.', 'phân loại khi chưa hỏi, chưa đo')
        if gi > bi:
            sev = 3 if x['best'] == 'do' or gi - bi >= 2 else 2
            t['mistakes'] += 1
            cq.slip(t, 'under' if sev < 3 else 'under_red', sev, f'{x["who"]} nặng mà phải ngồi chờ.', 'xếp người nặng xuống sau', safety=sev == 3)
            worst = max(worst, sev)
            lines.append(f'{NC.COLORS[got][0]} {x["who"]}: đáng lẽ {e} {NC.COLORS[x["best"]][1].lower()}.')
        else:
            t['mistakes'] += 1
            cq.slip(t, 'over', 1, 'Ca nhẹ được ưu tiên, người khác phải chờ thêm.', 'đẩy ca nhẹ lên trước')
            lines.append(f'{NC.COLORS[got][0]} {x["who"]}: hơi cao, {e} {NC.COLORS[x["best"]][1].lower()} là đủ.')
    t['choice'] = 'sent'
    t['result'] = 'triaged'
    d['today']['triaged'] += len(cases)
    d['stats']['triaged'] = min(10 ** 7, d['stats']['triaged'] + len(cases))
    reds = [t['needs']['queue'][i]['who'] for i in range(len(cases)) if t['colors'][str(i)] == 'do']
    if reds:
        _count_call(d)
    _fact(d, t, f'Quầy tiếp đón: phân loại {len(cases)} người' + (f', {len(reds)} thẻ đỏ đã gọi bác sĩ.' if reds else '.'), key=bool(reds) or worst >= 3,
          lie='Quầy tiếp đón: phân loại đúng hết.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, 'Phân loại ở quầy tiếp đón.')
    head = '🚦 ' + ' '.join(lines)
    if reds:
        head += f' 🚨 Thẻ đỏ vào phòng cấp cứu, bác sĩ tới ngay.'
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t), correct=worst < 3)


# ---------------------------------------------------------------- finishing a task
def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str, patient: bool = True) -> str:
    """Pays the bonus (none after a safety mistake; half when tired, none while demoted) and completes once."""
    pts = cq.points(t)
    full = 0 if cq.safety(t) or not reward else max(0, reward - 3 * pts)
    pay = ao.bonus(d['odd'], full)
    t['stage'] = 'done'
    story = ''
    i = _npc_index(t)
    if patient and i in NC.REG_STORY:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        story = NC.REG_STORY[i][min(r['visits'], len(NC.REG_STORY[i])) - 1]
        t['story'] = story
    if patient:
        d['learn']['n'] = min(10 ** 6, d['learn']['n'] + 1)
        d['today']['tasks'] += 1
        d['stats']['tasks'] = min(10 ** 7, d['stats']['tasks'] + 1)
        if cq.safety(t):
            d['today']['safety'] += 1
            d['stats']['safety'] = min(10 ** 7, d['stats']['safety'] + 1)
    kit.complete(s, c, t, pay, (narrative or t['title'])[:300])
    note = ao.flown(d['odd'], not cq.slips(t), CFG) if patient else ''
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
    """A line the end-of-shift handover may carry (true), and a tempting one that did not happen (lie)."""
    rows = d['today']['facts']
    rows.append(dict(id=f'f-{t["id"]}', text=text[:160], key=bool(key), true=True))
    if lie:
        rows.append(dict(id=f'l-{t["id"]}', text=lie[:160], key=False, true=False))
    d['today']['facts'] = rows[-FACTS_MAX:]


# ---------------------------------------------------------------- the end-of-shift handover notes
def _report(s, c, d, p):
    today = d['today']
    kit.need(today['report'] is None, 'Hôm nay đã viết sổ giao ca rồi.')
    rows = today['facts']
    kit.need(rows, 'Chưa có gì để giao ca. Làm việc trước đã.')
    pick = kit.id_list(p.get('lines') or [], [r['id'] for r in rows], FACTS_MAX, 'Chọn dòng ghi vào sổ.')
    kit.need(pick, 'Chọn ít nhất một dòng ghi vào sổ giao ca.')
    chosen = [r for r in rows if r['id'] in pick]
    lies = [r for r in chosen if not r['true']]
    miss = [r for r in rows if r['key'] and r['true'] and r['id'] not in pick]
    d['stats']['reports'] = min(10 ** 7, d['stats']['reports'] + 1)
    if lies:
        today['report'] = 'false'
        note = ao._conduct(c, d['odd'], 2, CFG)
        return dict(message=f'📒 Chị Hoa đọc sổ, khựng lại ở dòng “{lies[0]["text"]}”: “Cái này đâu có xảy ra, em?” Ghi khống vào sổ giao ca. {note}',
                    correct=False)
    if miss:
        today['report'] = 'miss'
        c['xp'] += 2
        return dict(message=f'📒 Sổ giao ca thật, nhưng thiếu: “{miss[0]["text"]}”. Ca đêm phải gọi điện hỏi lại.')
    today['report'] = 'ok'
    c['xp'] += 8
    d['stats']['honest'] = min(10 ** 7, d['stats']['honest'] + 1)
    return dict(message='📒 Sổ giao ca rõ ràng, thật, đủ việc cần theo dõi. Ca đêm đọc một lượt là nắm hết.', celebrate=True)


ACTIONS = {
    'dd_read': _read, 'dd_round': _round, 'dd_wash': _wash, 'dd_id': _id, 'dd_measure': _measure, 'dd_recheck': _recheck,
    'dd_chart': _chart, 'dd_call': _call, 'dd_done': _done, 'dd_check': _check, 'dd_give': _give, 'dd_hold': _hold,
    'dd_explain': _explain, 'dd_push': _push, 'dd_jewel': _jewel, 'dd_send': _send, 'dd_cannula': _cannula, 'dd_teach': _teach,
    'dd_teachback': _teachback, 'dd_discharge': _discharge, 'dd_bell': _bell, 'dd_tq': _tq, 'dd_color': _color, 'dd_triage': _triage,
    'dd_report': _report,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['today'] = _fresh_today(day)
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
    kit.desk_start(s, c, ID, d['desk'], NC.DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')
    ao.tick(s, c, ID, d['odd'], NC.ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], NC.DESK)
    odd_note = ao.close(s, c, d['odd'], NC.ODD)
    x = d['today']
    lines = [f'🏥 Ca ngày: {x["tasks"]} việc ở khoa Nội.']
    if x['calls']:
        lines.append(f'📞 Báo bác sĩ {x["calls"]} lần. Bất thường thì báo: đúng bài.')
    if x['held']:
        lines.append(f'✋ Giữ lại {x["held"]} lần cho tới khi bác sĩ xem lại.')
    if x['triaged']:
        lines.append(f'🚦 Phân loại {x["triaged"]} người ở quầy tiếp đón.')
    if x['safety']:
        lines.append(f'📋 {x["safety"]} báo cáo sự cố. Mai họp khoa rút kinh nghiệm.')
    if x['report'] is None and x['facts']:
        lines.append('📒 Chưa viết sổ giao ca: ca đêm phải đi hỏi lại từng giường.')
    elif x['report'] == 'ok':
        lines.append('📒 Sổ giao ca rõ ràng, thật, đủ.')
    if desk_note:
        lines.append(desk_note)
    if odd_note:
        lines.append(odd_note)
    lines += ao.day_lines(c, d['odd'], CFG)
    lines.append('🏠 Tối về tới đầu hẻm, bà Tám để phần cơm trên bàn.')
    return dict(lines=lines, note='Mai nhận ca lúc 7:00, đọc sổ giao ca trước khi đi buồng.', tasks=x['tasks'], calls=x['calls'], held=x['held'],
                safety=x['safety'], triaged=x['triaged'])


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
    hands = dict(key='hands', label='Tay sạch', score=_score(codes, {'hands'}), note='sát khuẩn tay trước khi chạm' if 'hands' not in codes else 'chưa sát khuẩn tay')
    ident = dict(key='ident', label='Đúng người bệnh', score=_score(codes, {'id'}, set(), {'wrong_patient'}),
                 note='hỏi tên, ngày sinh, xem vòng tay' if not codes & {'id', 'wrong_patient'} else 'chưa xác định đúng người')
    if k == 'shift':
        return dict(criteria=[dict(key='read', label='Đọc sổ giao ca', score=_score(codes, {'skim'}), note='đọc hết từng giường' if 'skim' not in codes else 'đọc sót'),
                              dict(key='first', label='Giường ưu tiên', score=_score(codes, set(), {'priority'}), note='xem giường cần trước' if 'priority' not in codes else 'chọn sai giường')])
    if k == 'vitals':
        return dict(criteria=[hands, ident,
                              dict(key='chart', label='Ghi phiếu đúng', score=_score(codes, set(), {'chart'}), note='số ghi khớp số đo' if 'chart' not in codes else 'ghi sai số'),
                              dict(key='escalate', label='Báo bác sĩ kịp', score=_score(codes, {'sbar'}, set(), {'missed'}),
                                   note='báo đủ, đúng lúc' if not codes & {'sbar', 'missed'} else 'báo thiếu hoặc không báo')])
    if k == 'med':
        return dict(criteria=[hands, ident,
                              dict(key='check', label='Kiểm dị ứng, nhãn, y lệnh', score=_score(codes, {'no_allergy', 'no_label'}, {'no_sugar', 'npo'}, {'allergy', 'label', 'low_sugar'}),
                                   note='đối chiếu đủ' if not codes & {'no_allergy', 'no_label', 'no_sugar', 'npo', 'allergy', 'label', 'low_sugar'} else 'đối chiếu chưa đủ'),
                              dict(key='respect', label='Tôn trọng người bệnh', score=_score(codes, {'guess'}, {'pressure'}),
                                   note='hỏi ý, giải thích' if not codes & {'pressure', 'guess'} else 'ép hoặc chưa hỏi ý'),
                              dict(key='decide', label='Quyết định đúng', score=_score(codes, {'needless', 'reason'}), note='làm hoặc giữ đúng lúc' if not codes & {'needless', 'reason'} else 'giữ lại chưa đúng')])
    if k == 'bell':
        return dict(criteria=[hands, dict(key='care', label='Trả lời chuông', score=_score(codes, {'meh'}, {'bad'}, {'unsafe'}),
                                          note='chu đáo, an toàn' if not codes & {'meh', 'bad', 'unsafe'} else 'chưa chu đáo')])
    if k == 'triage':
        return dict(criteria=[dict(key='triage', label='Phân loại đúng', score=_score(codes, {'over'}, {'under'}, {'under_red'}),
                                   note='đúng màu' if not codes & {'over', 'under', 'under_red'} else 'màu chưa đúng'),
                              dict(key='look', label='Hỏi, đo trước khi xếp', score=_score(codes, {'blind'}), note='hỏi và đo nhanh' if 'blind' not in codes else 'xếp khi chưa hỏi')])
    if k == 'proc':
        return dict(criteria=[hands, ident,
                              dict(key='consent', label='Đồng ý của người bệnh', score=_score(codes, set(), {'pressure'}, {'consent'}),
                                   note='có giấy cam đoan, không ép' if not codes & {'consent', 'pressure'} else 'thiếu đồng ý'),
                              dict(key='ready', label='Chuẩn bị đủ', score=_score(codes, {'no_fasting', 'no_allergy', 'jewel', 'no_jewel', 'needless', 'reason', 'guess'}, {'ate'}),
                                   note='nhịn ăn, dị ứng, trang sức' if not codes & {'no_fasting', 'no_allergy', 'jewel', 'no_jewel', 'ate'} else 'chuẩn bị chưa đủ')])
    return dict(criteria=[hands, ident,
                          dict(key='papers', label='Giấy tờ, kim luồn', score=_score(codes, {'bhyt'}, {'no_paper', 'cannula'}), note='đủ thủ tục' if not codes & {'bhyt', 'no_paper', 'cannula'} else 'thiếu thủ tục'),
                          dict(key='teach', label='Dặn dò', score=_score(codes, {'teach', 'no_teachback'}), note='dặn đủ, hỏi lại' if not codes & {'teach', 'no_teachback'} else 'dặn chưa đủ')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    k = t['kind']
    n = t['needs']
    if k == 'shift':
        return 'Sổ giao ca: ' + '; '.join(x['name'] for x in n['notes']) + '.'
    if k == 'triage':
        who = ', '.join(_lower(x['who']) for x in n['queue'])
        return f'Cô Mỹ: “{who[:1].upper()}{who[1:]} vừa tới. Phát thẻ màu giúp chị.”'
    b = BEDS[n['bed']]
    if k == 'bell':
        return BELLS[t['_v']['case']]['detail']
    if k == 'vitals':
        return f'Giường {b["bed"]} · {b["dx"]}. {VITALS[t["_v"]["case"]]["look"]}'
    if k == 'med':
        o = n['order']
        return f'Y lệnh: {o["drug"]} · {o["route"].lower()} · {o["time"]} · {o["name"]} ({o["dob"]}, giường {o["bed"]}).'
    if k == 'proc':
        return f'{n["proc"]} lúc {n["time"]}, giường {b["bed"]} · {b["name"]}.'
    return (n['rush'] + ' ' if n['rush'] else '') + f'Ra viện: giường {b["bed"]} · {b["name"]}.'


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not t['known'] and t['kind'] != 'shift':
        v['needs'] = None
        return v
    k = t['kind']
    seen = set(t.get('seen') or [])
    if k == 'shift':
        v['needs'] = dict(notes=[dict(n, text=n['text'] if f'note:{n["bed"]}' in seen else None) for n in t['needs']['notes']])
        if t['stage'] == 'done':
            v['first'] = t['_v']['first']
        return v
    if k == 'triage':
        cases = t['_v']['cases']
        v['needs'] = dict(queue=[dict(q, ask=TRIAGE[cases[i]]['ask'] if f'ask:{i}' in seen else None,
                                      quick=TRIAGE[cases[i]]['quick'] if f'quick:{i}' in seen else None,
                                      best=TRIAGE[cases[i]]['best'] if t['stage'] == 'done' else None)
                                 for i, q in enumerate(t['needs']['queue'])])
        return v
    b = BEDS[t['needs']['bed']]
    x = _case_of(t)
    view = dict(bed=b['bed'], bed_id=t['needs']['bed'], dx=b['dx'], fall=b['fall'])
    if t['idm'] == 'open':
        view['me'] = dict(name=b['name'], dob=b['dob'], band=b['band'])
    elif t['idm'] == 'name':
        view['me'] = dict(name=None, dob=None, band=None, said='“Ờ, phải.”')
    elif t['idm'] == 'bed':
        view['me'] = dict(name=None, dob=None, band=None, said=f'Giường {b["bed"]}')
    if k == 'vitals':
        vals = _vals(t)
        view.update(look=x['look'], vals=vals, first={s_: x['vals'][s_] for s_ in SIGN_IDS if s_ in seen},
                    flags=[s_ for s_ in vals if abnormal(s_, vals[s_])] if t['chart'] is not None else None)
    elif k == 'med':
        view.update(order=t['needs']['order'], board=t['needs']['board'],
                    allergy=(ALLERGY[b['allergy']] if b['allergy'] else '') if 'allergy' in seen else None,
                    tray=DRUGS[x.get('tray', x['drug'])]['name'] if 'label' in seen else None,
                    sugar=x.get('sugar') if 'sugar' in seen else None, refuse=x.get('refuse') if t['said'] in ('refused', 'no') else None)
    elif k == 'bell':
        view.update(detail=x['detail'], options=[dict(id=o[0], label=o[1]) for o in x['options']])
    elif k == 'proc':
        # `state`: what each check found, for the buttons it opens (only for checks already made).
        state = {'consent': 'withdrawn' if x['variant'] == 'refuse' else x['consent'], 'fasting': x['fasting'], 'jewel': x['jewel'],
                 'allergy': bool(b['allergy'])}
        view.update(proc=t['needs']['proc'], time=t['needs']['time'], jewel_off='jewel_off' in seen, signed='signed' in seen,
                    explained='explained' in seen, checks={w: _proc_line(x, w, b) for w in PROC_KEYS if w in seen},
                    state={w: state[w] for w in PROC_KEYS if w in seen})
    else:
        view.update(rush=t['needs']['rush'], cannula_off='cannula_off' in seen, signed='signed' in seen, teachback='teachback' in seen,
                    checks={w: NC.DISCHARGE_TEXT[w][x[w]] for w in DIS_CHECKS if w in seen},
                    state={w: x[w] for w in DIS_CHECKS if w in seen})
    v['needs'] = view
    return v


def _proc_line(x: dict, w: str, b: dict) -> str:
    if w == 'allergy':
        return ALLERGY[b['allergy']] if b['allergy'] else 'Không có dị ứng.'
    if w == 'consent' and x['variant'] == 'refuse':
        return 'Đã ký từ hôm qua, nhưng hôm nay Tuấn nói không mổ nữa.'
    return NC.PROC_TEXT[w][x[{'consent': 'consent', 'fasting': 'fasting', 'jewel': 'jewel'}[w]]]


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
                today=dict(day=today.get('day', 0), tasks=today.get('tasks', 0), calls=today.get('calls', 0), held=today.get('held', 0),
                           safety=today.get('safety', 0), triaged=today.get('triaged', 0), report=today.get('report'), facts=facts),
                stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                learn=dict(on=lr.get('n', 0) < LEARN, n=lr.get('n', 0), of=LEARN),
                desk=kit.desk_public(d['desk'], NC.DESK, ID), odd=ao.public(c, ao.ensure(d), NC.ODD, ID, CFG))


def content() -> dict:
    return dict(intro=NC.INTRO, beds={k: dict(bed=v['bed'], name=v['name'], dx=v['dx'], sign=v['sign']) for k, v in BEDS.items()},
                signs=SIGNS, sign_ids=list(SIGN_IDS), colors={k: list(v) for k, v in NC.COLORS.items()}, color_order=list(NC.COLOR_ORDER),
                teach={k: list(v) for k, v in TEACH.items()}, proc_checks={k: list(v) for k, v in NC.PROC_CHECKS.items()},
                hold=HOLD, med_hold=['allergy', 'wrongpt', 'label', 'refuse', 'npo', 'lowsugar', 'unsure'],
                proc_hold=['ate', 'refuse', 'consent', 'unsure'], learn=LEARN,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    return {'shift': 'Đọc ghi chú từng giường → chọn giường đêm qua có chuyện để xem trước.',
            'vitals': 'Sát khuẩn tay → hỏi tên, ngày sinh → đo đủ năm chỉ số → ghi phiếu → ngoài thẻ báo động thì báo bác sĩ → xong.',
            'med': 'Sát khuẩn tay → hỏi tên, ngày sinh → vòng dị ứng → nhãn khay → (đường huyết nếu y lệnh dặn) → cho thuốc hoặc giữ lại, báo bác sĩ.',
            'bell': 'Tới giường, nghe người bệnh, chọn cách trả lời an toàn và chu đáo.',
            'triage': 'Hỏi và đo nhanh từng người → phát thẻ màu theo dấu hiệu, không theo tiếng la → gửi.',
            'proc': 'Hỏi tên, ngày sinh → giấy cam đoan → nhịn ăn → dị ứng → trang sức → chuyển đi, hoặc giữ lại báo bác sĩ.',
            'discharge': 'Giấy ra viện có chữ ký → thẻ BHYT → rút kim luồn → dặn dò → nhờ nhắc lại → cho về.'}.get(t.get('kind'), '')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'aide':
        return 'Đã thay ga giường, đẩy xe đồ vải về kho.'
    if e.get('role') == 'clerk':
        return 'Đã sắp hồ sơ theo giường, in sẵn giấy tờ chờ bác sĩ ký.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu khoa Nội sai.')


def _seen_ok(t: dict) -> set:
    k = t.get('kind')
    if k == 'shift':
        return {f'note:{b}' for b in BED_IDS}
    if k == 'triage':
        n = len(t.get('_v', {}).get('cases') or [])
        return {f'{w}:{i}' for w in ('ask', 'quick') for i in range(n)}
    if k == 'vitals':
        return set(SIGN_IDS) | {f'{x}2' for x in SIGN_IDS}
    if k == 'med':
        return set(MED_CHECKS)
    if k == 'proc':
        return set(PROC_KEYS) | {'jewel_off', 'signed', 'explained'}
    if k == 'discharge':
        return set(DIS_CHECKS) | {'cannula_off', 'signed', 'teachback'}
    return set()


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN and t.get('kind') in KINDS and t.get('stage') in STAGES, 'Việc ở khoa Nội sai.')
    _vbool(t.get('washed'))
    kit.need(t.get('idm') in (None, *ID_HOW), 'Cách xác định người bệnh sai.')
    seen = t.get('seen')
    kit.need(isinstance(seen, list) and len(seen) == len(set(seen)) and set(seen) <= _seen_ok(t), 'Việc ở khoa Nội sai.')
    ch = t.get('chart')
    kit.need(ch is None or (isinstance(ch, dict) and set(ch) == set(SIGN_IDS) and all(isinstance(x, str) and len(x) <= 12 for x in ch.values())),
             'Phiếu theo dõi sai.')
    called = t.get('called')
    kit.need(isinstance(called, list) and len(called) <= 5 and len(set(called)) == len(called)
             and set(called) <= set(SIGN_IDS) | {'consent', 'paper', 'unsure'}, 'Lần báo bác sĩ sai.')
    kit.need(t.get('choice') is None or (isinstance(t['choice'], str) and len(t['choice']) <= 24), 'Lựa chọn sai.')
    cols = t.get('colors')
    kit.need(isinstance(cols, dict) and len(cols) <= 3 and all(isinstance(k, str) and k in ('0', '1', '2') and v in NC.COLORS for k, v in cols.items()),
             'Thẻ màu sai.')
    kit.need(t.get('said') in (None, *SAID), 'Lời người bệnh sai.')
    teach = t.get('teach')
    kit.need(isinstance(teach, list) and len(teach) == len(set(teach)) and set(teach) <= set(TEACH), 'Dặn dò sai.')
    kit.need(t.get('result') is None or (isinstance(t['result'], str) and len(t['result']) <= 24), 'Kết quả sai.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện người bệnh sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in NC.REG_STORY}, 'Sổ người quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người quen sai.')
        kit.integer(v['visits'], 0, 999)
    kit.need(isinstance(d['stats'], dict) and len(d['stats']) <= 20, 'Số liệu khoa sai.')
    for v in d['stats'].values():
        kit.integer(v, 0, 10 ** 9)
    x = d['today']
    kit.need(isinstance(x, dict) and set(x) == set(_fresh_today(0)), 'Số liệu trong ngày sai.')
    for k in ('day', 'tasks', 'calls', 'held', 'safety', 'washed', 'triaged'):
        kit.integer(x[k], 0, 10 ** 9)
    kit.need(x['report'] in (None, 'ok', 'miss', 'false'), 'Sổ giao ca sai.')
    kit.need(isinstance(x['facts'], list) and len(x['facts']) <= FACTS_MAX, 'Sổ giao ca sai.')
    for r in x['facts']:
        kit.need(isinstance(r, dict) and set(r) == {'id', 'text', 'key', 'true'} and type(r['key']) is bool and type(r['true']) is bool, 'Sổ giao ca sai.')
        kit.text(r['id'], 60)
        kit.text(r['text'], 160)
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'n', 'caught'} and isinstance(lr['caught'], list) and len(lr['caught']) <= 24, 'Sổ kèm việc sai.')
    kit.integer(lr['n'], 0, 10 ** 6)
    for k in lr['caught']:
        kit.text(k, 40)
    kit.desk_validate(d['desk'], NC.DESK)
    ao.validate(d['odd'], NC.ODD)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='dd_', category='service',
    meta=dict(short='Điều dưỡng', place='Bệnh viện phường Lá Sen', tagline='Đúng người, đúng y lệnh, báo kịp lúc.', icon='cross',
              color='#2f8a8a', light='#e0f3f1', weather='Trời trong, khoa Nội yên ả', work='Việc trong ca', station='Bàn điều dưỡng',
              greeting='Nhận ca lúc 7:00. Đọc sổ giao ca, sát khuẩn tay, hỏi tên và ngày sinh trước mỗi việc, có gì bất thường thì báo bác sĩ.',
              caption='Mỗi giường một con người, mỗi việc một lần kiểm', map_label='28 · BỆNH VIỆN LÁ SEN'),
    people=PEOPLE,
    staff=[('Lan', 'aide', 'Hộ lý lâu năm, đỡ người bệnh đi lại chắc tay.', 82, 90),
           ('Hưng', 'clerk', 'Thư ký khoa, sắp hồ sơ theo giường không sót tờ nào.', 76, 94),
           ('Thu', 'aide', 'Nhanh nhẹn, thay ga giường trong hai phút.', 88, 80),
           ('Bảo', 'clerk', 'Thuộc lòng thủ tục BHYT, người nhà hỏi gì cũng biết.', 74, 92)],
    roles={'aide': 'Hộ lý', 'clerk': 'Thư ký khoa'},
    tip=0,
    open_line='Nhận ca lúc 7:00. Chị Hoa đang chờ ở bàn giao ca.',
    more_line='Chị Hoa giao thêm một việc trong ca.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('🩺', 'Một ca ở khoa Nội', [('Hai thông tin', 'Họ tên và ngày sinh'), ('Sát khuẩn tay', 'Trước khi chạm người bệnh'),
                                          ('Vòng dị ứng', 'Trước khi cho thuốc'), ('Ngoài thẻ báo động', 'Báo bác sĩ ngay')],
              ['Nhận giao ca, đọc sổ', 'Đo, ghi phiếu', 'Đối chiếu, cho thuốc', 'Báo bác sĩ, giao ca']),
    stories=[('Cái đồng hồ quả quýt của chị Hoa', ('Chị Hoa đeo cái đồng hồ quả quýt trên túi áo, đếm mạch bằng kim giây từ hồi máy đo còn hiếm.',
                                                  'Bạn đo thêm một ca; chị chỉ cách nhìn người bệnh trước khi nhìn máy.',
                                                  'Chị Hoa dặn: “Máy báo sai được. Mắt mình mở to thì ít khi sai.”')),
             ('Lá thư của bà Tư', ('Bà Tư nhờ bạn viết giùm lá thư gửi con trai ở xa.',
                                    'Bạn làm thêm một ca, đọc lại thư cho bà nghe.',
                                    'Tuần sau con trai bà về, đứng ở cửa phòng mắt đỏ hoe.')),
             ('Sổ giao ca cũ', ('Trong tủ trực có cuốn sổ giao ca từ hai mươi năm trước, chữ chị Hoa nắn nót.',
                                 'Bạn làm thêm một ca, viết sổ giao ca của mình thật kỹ.',
                                 'Chị Hoa đọc xong, đóng sổ lại: “Ca đêm sẽ ngủ yên.”'))],
    review_asides=['Hỏi tên, ngày sinh mỗi lần, thấy yên tâm ghê.', 'Tay lúc nào cũng thơm mùi sát khuẩn.', 'Báo bác sĩ kịp lúc, nhẹ cả người.',
                   'Giải thích từng bước, không ai phải lo.'],
    situations=NC.SITUATIONS,
    guide='Nhận giao ca → sát khuẩn tay → hỏi họ tên, ngày sinh, đối chiếu vòng tay → đo, ghi phiếu đúng số → đối chiếu y lệnh, dị ứng, nhãn khay → '
          'bất thường thì báo bác sĩ → người bệnh từ chối thì hỏi, giải thích, báo bác sĩ → cuối ca viết sổ giao ca thật.',
    employment=dict(
        postings=[
            dict(id='dd-noi', org='Bệnh viện phường Lá Sen · Khoa Nội tổng hợp', kind='public', title='Điều dưỡng viên khoa Nội',
                 salary=(55, 72), probation_days=3, wants=['careful', 'calm', 'communication'],
                 perks=['Chị Hoa kèm ba ca đầu', 'Ca ngày 7:00–19:00', 'Có bữa trưa ở căng tin'],
                 culture='Khoa Nội hai mươi giường, người bệnh đa số lớn tuổi. Ở đây ai cũng hỏi tên, ngày sinh trước mỗi việc, kể cả người nằm cả tháng.',
                 questions=['dd_q_id', 'dd_q_refuse', 'dd_q_gift', 'mistake'], reference=True),
            dict(id='dd-kham', org='Bệnh viện phường Lá Sen · Phòng khám ngoại trú', kind='parttime', title='Điều dưỡng phòng khám (bán thời gian)',
                 salary=(42, 55), probation_days=2, wants=['patience', 'communication'],
                 perks=['Ca ngắn', 'Đứng quầy tiếp đón cùng cô Mỹ', 'Lương thấp hơn'],
                 culture='Phòng khám đông từ sáng sớm. Việc chính là đón người bệnh, đo nhanh, phân loại ai vào trước.',
                 questions=['dd_q_queue', 'dd_q_id'], reference=False),
        ],
        questions={
            'dd_q_id': dict(text='Bạn sắp cho thuốc ở giường 3. Bạn xác định người bệnh thế nào?', options=[
                dict(id='two', label='Mời người bệnh tự nói họ tên, ngày sinh; đối chiếu vòng tay và phiếu', score=3, note='Chị Hoa gật đầu: đúng thói quen của khoa.'),
                dict(id='name', label='Hỏi “Bác là bà Tư phải không ạ?”', score=1, note='Hỏi kiểu có/không thì người lãng tai cũng dạ.'),
                dict(id='bed', label='Xem số giường là đủ', score=0, note='Số giường đổi được; người bệnh có khi nằm nhầm giường.')]),
            'dd_q_refuse': dict(text='Người bệnh không chịu uống thuốc bác sĩ cho. Bạn làm gì?', options=[
                dict(id='ask', label='Hỏi vì sao, giải thích, vẫn không chịu thì báo bác sĩ và ghi hồ sơ', score=3, note='Tôn trọng quyền từ chối, không để người bệnh một mình với nỗi lo.'),
                dict(id='family', label='Nhờ người nhà giữ tay cho uống', score=0, note='Không bao giờ ép người bệnh bằng sức.'),
                dict(id='skip', label='Thôi, để đó, không cần báo ai', score=1, note='Bác sĩ cần biết để tìm cách khác.')]),
            'dd_q_gift': dict(text='Người nhà dúi phong bì “cảm ơn”. Bạn nói gì?', options=[
                dict(id='decline', label='Cảm ơn, xin không nhận, mời viết vài dòng vào sổ góp ý', score=3, note='Lời cảm ơn có chỗ của nó, không phải phong bì.'),
                dict(id='fund', label='Nhận rồi bỏ quỹ chung', score=0, note='Đổi tên gọi thì vẫn là nhận phong bì.'),
                dict(id='later', label='Bảo để lúc ra viện hẵng đưa', score=0, note='Hẹn lại cũng là nhận.')]),
            'dd_q_queue': dict(text='Ở quầy tiếp đón, một anh la hét đòi khám trước vì trầy tay; một ông cụ ngồi im, tay ôm ngực.', options=[
                dict(id='quiet', label='Hỏi, đo nhanh cả hai; ông cụ đau ngực vào trước', score=3, note='Người la to chưa chắc là người nặng.'),
                dict(id='loud', label='Cho anh la hét vào trước cho yên', score=0, note='Ông cụ đau ngực phải chờ là nguy hiểm.'),
                dict(id='order', label='Ai tới trước khám trước', score=1, note='Công bằng nhưng chưa an toàn: nặng phải vào trước.')]),
        }),
)
