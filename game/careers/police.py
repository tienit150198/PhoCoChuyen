"""Công an phường: a day shift at the (fictional) Công an phường Mây, the ward's community police (plugin career).

The player is a newly hired ward officer (employment: CV and interview; the "Chứng chỉ Tiếp dân & hòa giải"
certificate raises the hire chance) under anh Định, the leader of the beat officers. The work is community service,
never force: one task is one piece of the shift.

* ``brief`` (slot 0): the morning briefing. Read the night's duty book and choose what to handle first (the topic
  that went wrong overnight). The first job of the day (slot 1) follows that topic;
* ``desk``: the residence desk. Check each paper of a resident's file (form, identity paper, the landlord's consent,
  a parent's consent for a minor); accept it, or send it back naming the paper to bring. Some come with an envelope
  "to speed things up", a relative "up at the district", or a hurry: the player answers first;
* ``lost``: lost and found. Count the item with the finder and sign the receipt; then someone comes to claim it:
  ask (colour, what is inside, where it was lost, the identity paper) and give it back or keep it. A claimant may
  not be the owner (hidden);
* ``dispute``: mediation between neighbours (karaoke, parking, a cracked wall, a dog, a mango tree). Listen to each
  side, then propose terms; each side accepts or not from hidden traits (how strict it is about what it cares
  about, softened by being heard). Sign the agreement, or refer it to the ward's mediation team;
* ``child``: a lost child. Calm the child first, ask, look at the bag's name tag, have it announced (never post
  the child's photo); verify whoever comes to pick the child up. A neighbour the parents did not send is not
  handed the child (hidden);
* ``patrol``: three scenes at the market, the school gate, the ward fair or a wedding in the lane. Look, then act:
  the game's patrol rule is "a reminder first; a written report when it is repeated or dangerous; make it safe now
  when there is danger";
* ``talk``: a scam-awareness talk for the elderly: read the invitation, choose up to three topics that fit what
  happened there, then answer the audience's questions;
* ``calls``: three calls on the duty phone at once: call back, then give each a priority on the game's card. Someone
  in danger goes first; a false report is noted, not chased.

Around the tasks: the awkward people of the ward (air_odd engine, game/careers/police_content.py ODD): envelopes,
an official's relative, the karaoke neighbour, the daily "suspicious person" report, a TikToker filming the desk, a
drunk uncle, a grandmother who wants to chat for an hour, fake reports, a boss chasing quotas. Giving in is never
rewarded (conduct points; stood down for the day; demoted). Desk surprises and real-life situations as in every
career. At the end of the shift the player may write the duty book from what really happened (lines that did not
happen, the tempting quota lines, are ghi khống).

Money only through the engine (the salary at day close, a small bonus per task). Everything random comes from
(day, slot) or the task id: make_task is pure.
"""
from __future__ import annotations

import copy

from ..jsoncopy import tree_copy
from . import kit
from . import air_odd as ao
from . import street_folk as folk
from .. import consequences as cq
from . import police_content as PC
from .police_content import (PEOPLE, BRIEF, BRIEF_IDS, FLAG_TASK, DOCS, DOC_TEXT, BACK_LINE, DESKS, PRESS, LOSTS, QUESTIONS_LOST,
                             DISPUTES, CHILDREN, KID_Q, ANNOUNCE, VERIFY, PLACES, SCENES, PATROLS, TOPICS, TALK_Q, TALKS, PRIO, CALLS)

ID = 'police'
GEN = 1
BONUS = 10            # xu per task done by the book (a performance bonus: the salary is the pay)
LEARN = 3             # anh Định stands beside you for the first three jobs
FACTS_MAX = 14
KINDS = ('brief', 'desk', 'lost', 'dispute', 'child', 'patrol', 'talk', 'calls')
STAGES = ('open', 'done')
MODS = PC.MODS
DINH, HANG, NAM, THOA, QUY, KHA, VUONG, UT = range(8)
PLACE_NPC = {'market': UT, 'gate': DINH, 'fair': VUONG, 'wedding': QUY}

# The words of the encounters (air_odd): who to bring in, the office, what a demotion or a stand-down is called here.
CFG = dict(crew='👮 Gọi anh Định', company='🏢 Báo Ban chỉ huy phường', union='Nhờ công đoàn', office='Văn phòng Công an phường',
           demoted='cán bộ tập sự', title='cán bộ khu vực',
           labels={'charm': dict(duty='Tôi đang trong ca trực.', rule='Cán bộ không được nhận quà, tiền của dân.',
                                 alt='Cảm ơn, có gì cứ lên phường làm đúng thủ tục.', later='Để hôm khác nha…'),
                   'demand': dict(rule='Quy định của phường không cho phép.', alt='Có cách khác đúng thủ tục…'),
                   'corner': dict(speak='Mình chưa làm đủ bước.', rule='Quy trình bắt buộc mà.', alt='Làm nhanh mà vẫn đủ bước.'),
                   'bargain': dict(rule='Vượt giờ quy định rồi.', paper='Cho em xin văn bản.')},
           ground_line='⚖️ Ban chỉ huy: tạm dừng nhiệm vụ hết hôm nay, mai lên giải trình.',
           harass_note='🛡️ Báo là đúng: phường có quy trình bảo vệ cán bộ đang làm nhiệm vụ.',
           demote_line='⚖️ Hội đồng kỷ luật: hạ xuống {demoted}, tạm dừng nhiệm vụ hôm nay, không có thưởng tới khi hồ sơ sạch lại.',
           tired_line='😮‍💨 Mệt rồi: thưởng việc chỉ còn một nửa. Xin nghỉ bù ở phòng trực.',
           rest_ok=' Ca của bạn đã có người trực thay; bạn thấy nhẹ cả người.',
           levels={'ground': 'Tạm dừng nhiệm vụ'})


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError, AttributeError):
        return 0


def _rot(rows: tuple, day: int, slot: int, opened: int, salt: str) -> str:
    """A case from a rotation: the first `opened` rows on early days, all of them later (pure)."""
    pool = rows[:max(1, min(len(rows), opened))]
    return pool[kit.rng(ID, salt, day, slot).randrange(len(pool))]


def _low(s: str) -> str:
    """Only the first letter lowered (“Cổng trường Tiểu học Mây” → “cổng trường Tiểu học Mây”): names keep their capitals."""
    return s[:1].lower() + s[1:] if s else s


def _opened(day: int, simple: int, total: int) -> int:
    return simple if day <= 1 else simple + 2 if day == 2 else total


# ================================================================ tasks
def flag_of(day: int) -> str:
    """The duty book's urgent topic today (the briefing's right answer); day 1 starts with the found wallet."""
    if day <= 1:
        return 'wallet'
    return BRIEF_IDS[kit.rng(ID, 'flag', day).randrange(len(BRIEF_IDS))]


def _weights(day: int, mod: str) -> list:
    w = {'desk': 3, 'lost': 2, 'patrol': 2, 'calls': 2 if day >= 2 else 0, 'dispute': 2 if day >= 2 else 0,
         'child': 1 if day >= 2 else 0, 'talk': 1 if day >= 3 else 0}
    if mod == 'market':
        w['patrol'] += 2
        w['child'] += 1
        w['lost'] += 1
    elif mod == 'school':
        w['patrol'] += 2
        w['child'] += 1
    elif mod == 'season':
        w['patrol'] += 2
        w['dispute'] += 1
    elif mod == 'audit':
        w['desk'] += 2
    elif mod == 'rain':
        w['calls'] += 3
    return [(k, v) for k, v in w.items() if v]


DAY_ONE = ('desk', 'patrol', 'desk', 'calls', 'lost')


def task_kind(day: int, slot: int) -> str:
    if slot <= 0:
        return 'brief'
    if slot == 1:
        return FLAG_TASK[flag_of(day)][0]
    if day == 1:
        return DAY_ONE[(slot - 2) % len(DAY_ONE)]
    mod = mod_of(day)['id']
    prev = task_kind(day, slot - 1)
    rows = [(k, v) for k, v in _weights(day, mod) if k != prev]
    total = sum(v for _, v in rows)
    x = kit.rng(ID, 'kind', day, slot).random() * total
    for k, v in rows:
        x -= v
        if x < 0:
            return k
    return rows[-1][0]


def _patrol_case(day: int, slot: int) -> str:
    mod = mod_of(day)['id']
    r = kit.rng(ID, 'patrol', day, slot)
    if mod == 'market':
        return 'pt-market'
    if mod == 'school':
        return 'pt-gate'
    if mod == 'season':
        return ('pt-fair', 'pt-wedding')[r.randrange(2)]
    return _rot(PC.PATROL_ROTATION, day, slot, _opened(day, 2, len(PC.PATROL_ROTATION)), 'pt')


def _case(day: int, slot: int, kind: str) -> str:
    if slot == 1:
        return FLAG_TASK[flag_of(day)][1]
    if kind == 'desk':
        return _rot(PC.DESK_ROTATION, day, slot, _opened(day, 4, len(PC.DESK_ROTATION)), 'desk')
    if kind == 'lost':
        return _rot(PC.LOST_ROTATION, day, slot, _opened(day, 3, len(PC.LOST_ROTATION)), 'lost')
    if kind == 'dispute':
        return _rot(PC.DISPUTE_ROTATION, day, slot, len(PC.DISPUTE_ROTATION), 'dp')
    if kind == 'child':
        return _rot(PC.CHILD_ROTATION, day, slot, len(PC.CHILD_ROTATION), 'ch')
    if kind == 'patrol':
        return _patrol_case(day, slot)
    if kind == 'talk':
        return _rot(PC.TALK_ROTATION, day, slot, len(PC.TALK_ROTATION), 'tk')
    return ''


def _scenes(day: int, slot: int, case: str) -> list:
    """Three scenes of the patrol's place (the case's must-see scene among them), in a pure order."""
    p = PATROLS[case]
    r = kit.rng(ID, 'scenes', day, slot)
    pool = [k for k, v in SCENES.items() if v['place'] == p['place'] and k != p['must']]
    r.shuffle(pool)
    out = ([p['must']] if p['must'] else []) + pool
    out = out[:PC.PATROL_SCENES]
    r.shuffle(out)
    return out


def _calls(day: int, slot: int, case: str) -> list:
    """Three calls at once: one where someone is in danger, one that can wait or is false, one more (pure)."""
    r = kit.rng(ID, 'calls', day, slot)
    a = 'nam_bank' if case == 'cl-scam' else PC.CALL_NOW[r.randrange(len(PC.CALL_NOW))]
    minor = [k for k, v in CALLS.items() if v['best'] in ('later', 'fake')]
    b = minor[r.randrange(len(minor))]
    rest = [k for k in CALLS if k not in (a, b) and k not in PC.CALL_NOW]
    c = rest[r.randrange(len(rest))]
    out = [a, b, c]
    r.shuffle(out)
    return out


def _common() -> dict:
    return dict(gen=GEN, stage='open', seen=[], choice=None, result=None, story=None, press=None, offers=[], prio={}, acts={},
                topics=[], answers={})


def make_task(day: int, slot: int, serial: int) -> dict:
    kind = task_kind(day, slot)
    c = _common()
    if kind == 'brief':
        flag = flag_of(day)
        entries = [dict(id=k, name=BRIEF[k]['name'], emoji=BRIEF[k]['emoji'], text=BRIEF[k]['urgent' if k == flag else 'calm']) for k in BRIEF_IDS]
        return kit.base_task(ID, day, slot, serial, DINH, 'Giao ban đầu ca',
                             'Anh Định: “Đọc sổ trực ban đêm qua đi em, rồi chọn việc làm trước. Chuyện nào có người đang gặp nguy thì đi trước.”',
                             kind='brief', needs=dict(entries=entries), _v=dict(first=flag), **c)
    case = _case(day, slot, kind)
    if kind == 'desk':
        x = DESKS[case]
        docs = ['form', 'id', 'host'] + (['guard'] if x['minor'] else [])
        return kit.base_task(ID, day, slot, serial, HANG, f'Bàn cư trú: {x["who"]}', f'{x["emoji"]} {x["who"]} ({_low(x["role"])}): {x["line"]}',
                             kind='desk', needs=dict(who=x['who'], role=x['role'], emoji=x['emoji'], docs=docs, press=x['press']), _v=dict(case=case), **c)
    if kind == 'lost':
        x = LOSTS[case]
        return kit.base_task(ID, day, slot, serial, x['npc'], f'Đồ thất lạc: {_low(x["item"])}',
                             f'{x["finder"]} mang tới một {_low(x["item"])} nhặt được ({_low(x["found"])}).',
                             kind='lost', needs=dict(item=x['item'], emoji=x['emoji'], finder=x['finder'], found=x['found']), _v=dict(case=case), **c)
    if kind == 'dispute':
        x = DISPUTES[case]
        side = lambda s: dict(name=x[s]['name'], emoji=x[s]['emoji'], say=x[s]['say'])
        return kit.base_task(ID, day, slot, serial, x['npc'], f'Hòa giải: {_low(x["title"])}',
                             f'{x["a"]["name"]} và {x["b"]["name"]} cùng lên phường, chưa ngồi đã to tiếng.',
                             kind='dispute', needs=dict(title=x['title'], emoji=x['emoji'], a=side('a'), b=side('b'),
                                                        terms=[dict(id=tm['id'], label=tm['label'], options=list(tm['options'])) for tm in x['terms']]),
                             _v=dict(case=case), **c)
    if kind == 'child':
        x = CHILDREN[case]
        return kit.base_task(ID, day, slot, serial, x['npc'], f'Trẻ lạc ở {_low(x["place"])}',
                             f'{x["emoji"]} Một bé {x["age"]} đứng khóc một mình: {_low(x["found"])}.',
                             kind='child', needs=dict(kid=x['kid'], emoji=x['emoji'], age=x['age'], found=x['found'], place=x['place']), _v=dict(case=case), **c)
    if kind == 'patrol':
        p = PATROLS[case]
        e, name = PLACES[p['place']]
        ids = _scenes(day, slot, case)
        return kit.base_task(ID, day, slot, serial, PLACE_NPC[p['place']], f'Tuần tra: {name}', f'{e} Một vòng tuần tra {name}: ba chuyện cần để mắt.',
                             kind='patrol', needs=dict(place=p['place'], name=name, emoji=e,
                                                       scenes=[dict(emoji=SCENES[k]['emoji'], text=SCENES[k]['text']) for k in ids]),
                             _v=dict(case=case, scenes=ids), **c)
    if kind == 'talk':
        x = TALKS[case]
        return kit.base_task(ID, day, slot, serial, x['npc'], f'Nói chuyện chống lừa đảo: {x["where"]}',
                             f'{x["where"]}: {_low(x["audience"])} chờ nghe phường nói chuyện chống lừa đảo.',
                             kind='talk', needs=dict(where=x['where'], audience=x['audience']), _v=dict(case=case), **c)
    q = _calls(day, slot, case)
    return kit.base_task(ID, day, slot, serial, HANG, 'Điện thoại trực ban', '☎️ Ba cuộc gọi tới cùng lúc. Chị Hằng: “Em xếp giúp chị, ai đi trước.”',
                         kind='calls', needs=dict(queue=[dict(who=CALLS[k]['who'], emoji=CALLS[k]['emoji'], text=CALLS[k]['text']) for k in q]),
                         _v=dict(case=case, calls=q), **c)


FIXED = ('needs', '_v')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t.get('kind') == 'brief':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the station's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, tasks=0, helped=0, reports=0, reminders=0, refused=0, safety=0, facts=[], log=None)


def initial() -> dict:
    return dict(v=1, intro=False, regulars={}, today=_fresh_today(0), learn=dict(n=0, caught=[]),
                stats=dict(tasks=0, helped=0, reports=0, reminders=0, refused=0, safety=0, deals=0, returned=0, kids=0, logs=0, honest=0),
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


def _bump(d: dict, key: str, n: int = 1) -> None:
    d['today'][key] = d['today'].get(key, 0) + n
    d['stats'][key] = min(10 ** 7, d['stats'].get(key, 0) + n)


def _pressure(c: dict, d: dict) -> int:
    """How hard the station leans on its officers today: a busy day, and an officer who snapped at the boss."""
    marks = d['odd']['marks']
    return {'market': 1, 'season': 1, 'audit': 1, 'rain': 1}.get(mod_of(c['day'])['id'], 0) + ('strained' in marks) + ('kpi_black' in marks)


# ================================================================ the actions
FREE = ('cap_intro', 'cap_rest')
NO_TICK = ('cap_intro', 'cap_rest', 'cap_read', 'cap_doc', 'cap_lq', 'cap_kq', 'cap_look', 'cap_topic', 'cap_invite', 'cap_cb', 'cap_prio',
           'cap_desk', 'cap_odd', 'cap_log', 'cap_hear', 'cap_verify')
PHYSICAL = ('cap_accept', 'cap_give', 'cap_handover', 'cap_act', 'cap_dispatch', 'cap_sign', 'cap_present')
GROUNDED = ('cap_first', 'cap_accept', 'cap_back', 'cap_count', 'cap_give', 'cap_keep', 'cap_offer', 'cap_sign', 'cap_refer', 'cap_calm',
            'cap_handover', 'cap_hold', 'cap_act', 'cap_endpatrol', 'cap_present', 'cap_answer', 'cap_dispatch')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'cap_intro':
        d['intro'] = True
        return dict(message='Vào ca thôi! Anh Định đang chờ ở phòng giao ban.')
    odd = d['odd']
    if name == 'cap_rest':
        return ao.rest(s, c, odd, p, _pressure(c, d), CFG)
    desk = d['desk']
    if name == 'cap_desk':
        result = kit.desk_choose(s, c, ID, desk, PC.DESK, p.get('option'))
        _odd_tick(s, c, d, result)
        return result
    if name == 'cap_odd':
        result = ao.reply(s, c, ID, odd, PC.ODD, p, CFG, _pressure(c, d))
        if odd['ev'] is None:
            _odd_tick(s, c, d, result)
        return result
    if name == 'cap_log':
        return _log(s, c, d, p)
    kit.desk_block(desk, 'Có chuyện ở phường, quyết xong rồi làm tiếp nhé.')
    ao.block(odd, 'Có người đang chờ bạn trả lời, xong rồi làm tiếp nhé.')
    kit.need(not (ao.grounded(c, odd) and name in GROUNDED), 'Bạn đang bị tạm dừng nhiệm vụ hết hôm nay. Tan ca, mai lên Ban chỉ huy giải trình.', 'grounded')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở Công an phường.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, PC.DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(PC.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
        return
    _odd_tick(s, c, d, result)


def _odd_tick(s: dict, c: dict, d: dict, result: dict) -> None:
    """Someone around the ward turns up when today's plan says so (never over an open desk surprise)."""
    x = ao.tick(s, c, ID, d['odd'], PC.ODD, busy=d['desk']['ev'] is not None)
    if x:
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: trả lời giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None, known: bool = True) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc Công an phường.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    if known:
        kit.need(t['known'], 'Chào hỏi, nghe chuyện trước đã.')
    kit.need(t['stage'] == 'open', 'Việc này đã xong.')
    return t


def _case_of(t: dict) -> dict:
    v = t['_v']
    return {'desk': DESKS, 'lost': LOSTS, 'dispute': DISPUTES, 'child': CHILDREN, 'patrol': PATROLS, 'talk': TALKS}[t['kind']][v['case']]


def _seen(t: dict, key: str) -> bool:
    return key in t['seen']


def _see(t: dict, key: str) -> None:
    if key not in t['seen']:
        t['seen'].append(key)


# ---------------------------------------------------------------- anh Định beside you (the first three jobs)
def _guard(d: dict, code: str, line: str) -> dict | None:
    """In the first jobs anh Định stops each kind of mistake once, before it is made (nothing is recorded)."""
    lr = d['learn']
    if lr['n'] >= LEARN or code in lr['caught'] or len(lr['caught']) >= 24:
        return None
    lr['caught'].append(code)
    return dict(message=f'✋ Anh Định kéo tay bạn lại: “{line}”', correct=False)


def _bribe(c: dict, d: dict, t: dict, text: str) -> str:
    """Taking an envelope (or sitting at a gambling mat): never rewarded. Conduct points and a serious slip."""
    t['mistakes'] += 1
    cq.slip(t, 'bribe', 3, text, 'nhận phong bì, làm trái quy định', safety=True)
    _bump(d, 'safety')
    return ao.penalize(c, d['odd'], 3, CFG)


# ---------------------------------------------------------------- the briefing
def _read(s, c, d, p):
    t = _task(c, p, ('brief',))
    k = kit.one_of(p.get('entry'), BRIEF_IDS, 'Mục này không có trong sổ trực ban.')
    kit.need(not _seen(t, f'note:{k}'), 'Đã đọc mục này rồi.')
    _see(t, f'note:{k}')
    kit.start_work(t)
    e = next(x for x in t['needs']['entries'] if x['id'] == k)
    return dict(message=f'{e["emoji"]} {e["name"]}: {e["text"]}')


def _first(s, c, d, p):
    t = _task(c, p, ('brief',))
    first = kit.one_of(p.get('first'), BRIEF_IDS, 'Chọn việc làm trước.')
    read = sum(1 for k in BRIEF_IDS if _seen(t, f'note:{k}'))
    if first != t['_v']['first']:
        g = _guard(d, 'priority', 'Đọc lại sổ: mục nào có người đang cần mình ngay thì làm trước.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'priority', 2, 'Chuyện gấp nhất trong sổ trực ban lại để sau cùng.', 'chọn chưa đúng việc gấp')
    if read < len(BRIEF_IDS):
        t['mistakes'] += 1
        cq.slip(t, 'skim', 1, 'Giao ban mà không đọc hết sổ trực ban.', 'chưa đọc hết sổ')
    t['choice'] = first
    t['result'] = 'brief'
    kit.start_work(t)
    ok = not cq.slips(t)
    _finish(s, c, d, t, 0, f'Giao ban, làm trước: {_low(BRIEF[first]["name"])}.', job=False)
    return dict(message=f'📋 Giao ban xong. Việc đầu tiên: {_low(BRIEF[first]["name"])}.' + (' Anh Định gật đầu: “Đúng việc cần làm trước.”' if ok else ''),
                celebrate=ok)


# ---------------------------------------------------------------- the residence desk
def _issue(t: dict) -> str | None:
    x = _case_of(t)
    return next((k for k in t['needs']['docs'] if x['docs'][k] != 'ok'), None)


def _press_open(t: dict) -> bool:
    return bool(t['needs'].get('press')) and t['press'] is None


def _doc(s, c, d, p):
    t = _task(c, p, ('desk',))
    doc = kit.one_of(p.get('doc'), t['needs']['docs'], 'Hồ sơ này không có giấy đó.')
    kit.need(not _seen(t, f'doc:{doc}'), 'Đã xem giấy này rồi.')
    _see(t, f'doc:{doc}')
    kit.start_work(t)
    state = _case_of(t)['docs'][doc]
    return dict(message=f'{DOCS[doc][0]} {DOCS[doc][1]}: {DOC_TEXT[doc][state]}')


def _press(s, c, d, p):
    t = _task(c, p, ('desk',))
    kit.need(_press_open(t), 'Không có chuyện gì cần trả lời.')
    x = PRESS[t['needs']['press']]
    opts = {o[0]: o for o in x['options']}
    choice = kit.one_of(p.get('choice'), opts, 'Chọn cách trả lời.')
    _, label, grade, outcome = opts[choice]
    if grade in ('bad', 'bribe'):
        g = _guard(d, f'press:{t["needs"]["press"]}', 'Khoan. Ở bàn này ai cũng như ai, không phong bì, không chen hàng, không bỏ bước.')
        if g:
            return g
    t['press'] = choice
    kit.start_work(t)
    note = ''
    if grade == 'bribe':
        note = _bribe(c, d, t, 'Cán bộ nhận phong bì ngay tại bàn tiếp dân.')
    elif grade == 'bad':
        t['mistakes'] += 1
        if t['needs']['press'] == 'vip':
            cq.slip(t, 'queue', 2, 'Có người quen là được làm trước, người chờ từ sáng phải chờ thêm.', 'cho chen hàng')
            note = ao.penalize(c, d['odd'], 1, CFG)
        else:
            cq.slip(t, 'rush', 2, 'Nhận hồ sơ khỏi xem cho nhanh, chiều phải gọi người ta quay lại.', 'nhận mà không xem')
    elif grade == 'ok':
        t['mistakes'] += 1
        cq.slip(t, 'press_meh', 1, 'Trả lời chưa khéo, người khai không vui.', 'trả lời chưa khéo')
    else:
        if t['needs']['press'] == 'envelope':
            _bump(d, 'refused')
        if choice == 'log':
            _fact(d, t, f'Bàn cư trú: {t["needs"]["who"]} kẹp phong bì trong hồ sơ, đã trả lại, ghi sổ.', key=True)
    return dict(message=f'{outcome} {note}'.strip(), correct=grade not in ('bad', 'bribe'), celebrate=grade == 'good')


def _accept(s, c, d, p):
    t = _task(c, p, ('desk',))
    kit.need(not _press_open(t), 'Trả lời người khai trước đã.')
    issue = _issue(t)
    docs = t['needs']['docs']
    unseen = [k for k in docs if not _seen(t, f'doc:{k}')]
    if unseen:
        g = _guard(d, 'check', 'Xem đủ từng giấy trước khi nhận. Thiếu một tờ là người ta phải đi lại.')
        if g:
            return g
    if issue and _seen(t, f'doc:{issue}'):
        g = _guard(d, 'issue', f'{DOCS[issue][1]} chưa đúng kìa. Hướng dẫn bổ sung, đừng nhận vội.')
        if g:
            return g
    state = _case_of(t)['docs'][issue] if issue else 'ok'
    if issue == 'id' and state == 'other':
        t['mistakes'] += 1
        cq.slip(t, 'wrong_person', 3, 'Nhận hồ sơ bằng giấy tờ của người khác.', 'nhận giấy tờ không đúng người', safety=True)
    elif issue:
        t['mistakes'] += 1
        cq.slip(t, 'accept_bad', 2, f'Hồ sơ còn thiếu ({_low(DOCS[issue][1])}) mà vẫn nhận, chị Hằng phải gọi người ta lên lại.', 'nhận hồ sơ chưa đủ')
    if unseen and not any(r['code'] == 'rush' for r in cq.slips(t)):
        t['mistakes'] += 1
        cq.slip(t, 'skim', 1, 'Nhận hồ sơ mà không xem hết giấy tờ.', 'chưa xem đủ giấy tờ')
    t['choice'] = 'accept'
    t['result'] = 'accepted'
    _bump(d, 'helped')
    who = t['needs']['who']
    _fact(d, t, f'Bàn cư trú: nhận hồ sơ tạm trú của {who} (còn thiếu giấy, phải gọi lại).' if issue else f'Bàn cư trú: nhận hồ sơ tạm trú của {who}, đủ giấy tờ.',
          key=bool(issue),
          lie=f'Bàn cư trú: hồ sơ của {who} đã đối chiếu đủ từng giấy.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, f'Nhận hồ sơ tạm trú của {who}.')
    return dict(message=f'🗂️ Nhận hồ sơ, hẹn trả giấy chiều nay. {msg}'.strip(), celebrate=not cq.slips(t), correct=not cq.safety(t))


def _back(s, c, d, p):
    t = _task(c, p, ('desk',))
    kit.need(not _press_open(t), 'Trả lời người khai trước đã.')
    doc = kit.one_of(p.get('doc'), t['needs']['docs'], 'Chọn giấy cần bổ sung.')
    issue = _issue(t)
    if not issue or doc != issue:
        g = _guard(d, 'back', 'Giấy đó có sao đâu em. Xem lại từng tờ rồi hãy bắt người ta đi bổ sung.')
        if g:
            return g
    if not issue:
        t['mistakes'] += 1
        cq.slip(t, 'needless', 2, 'Hồ sơ đủ mà bị bắt về bổ sung, mất thêm buổi làm.', 'bắt bổ sung khi không cần')
    elif doc != issue:
        t['mistakes'] += 1
        cq.slip(t, 'wrong_doc', 2, 'Về bổ sung một giấy chẳng thiếu, lên lại mới biết thiếu giấy khác.', 'hướng dẫn bổ sung sai giấy')
    if not _seen(t, f'doc:{doc}'):
        t['mistakes'] += 1
        cq.slip(t, 'guess', 1, 'Chưa xem giấy mà đã bảo thiếu.', 'đoán mà không xem')
    t['choice'] = f'back:{doc}'
    t['result'] = 'back'
    _bump(d, 'helped')
    who = t['needs']['who']
    tr = folk.traits(t['id'], 'warm' if t['needs']['press'] is None else 'bossy')
    reply = '“Dạ, chiều em mang lên đủ.”' if tr['mood'] >= 45 else '“Trời, lại phải đi thêm một chuyến…” Nhưng vẫn ghi lại giấy cần mang.'
    _fact(d, t, f'Bàn cư trú: hướng dẫn {who} bổ sung {_low(DOCS[doc][1])}.', key=False,
          lie=f'Bàn cư trú: đã nhận đủ hồ sơ của {who}.' if issue else None)
    msg = _finish(s, c, d, t, BONUS, f'Hướng dẫn {who} bổ sung hồ sơ.')
    return dict(message=f'📄 {BACK_LINE[doc]}. {who}: {reply} {msg}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- lost and found
def _count(s, c, d, p):
    t = _task(c, p, ('lost',))
    kit.need(not _seen(t, 'count'), 'Đã kiểm đếm rồi.')
    _see(t, 'count')
    kit.start_work(t)
    x = _case_of(t)
    tr = x['truth']
    return dict(message=f'🧾 Kiểm đếm cùng {_low(x["finder"])}: {tr["color"]}; bên trong: {tr["inside"]}. Hai bên ký biên bản tiếp nhận. '
                        f'Một lúc sau, {x["who"]} tới xin nhận lại.')


def _lq(s, c, d, p):
    t = _task(c, p, ('lost',))
    kit.need(_seen(t, 'count'), 'Kiểm đếm, ký biên bản tiếp nhận trước đã.')
    q = kit.one_of(p.get('q'), QUESTIONS_LOST, 'Câu hỏi không có.')
    kit.need(not _seen(t, f'q:{q}'), 'Đã hỏi câu này rồi.')
    _see(t, f'q:{q}')
    x = _case_of(t)
    return dict(message=f'{QUESTIONS_LOST[q][0]} {x["who"]}: {x["says"][q]}')


def _asked(t: dict, prefix: str) -> list:
    return [k for k in t['seen'] if k.startswith(prefix)]


def _give(s, c, d, p):
    t = _task(c, p, ('lost',))
    kit.need(_seen(t, 'count'), 'Kiểm đếm, ký biên bản tiếp nhận trước đã.')
    x = _case_of(t)
    asked = _asked(t, 'q:')
    if len(asked) < 2:
        g = _guard(d, 'thin', 'Hỏi ít nhất hai câu, có câu bên trong có gì hoặc xem giấy tờ, rồi mới trả.')
        if g:
            return g
    if not x['genuine']:
        g = _guard(d, 'owner', 'Nghe lại câu trả lời đi: có khớp với biên bản không?')
        if g:
            return g
    if not x['genuine']:
        t['mistakes'] += 1
        cq.slip(t, 'wrong_owner', 3, f'{x["item"]} được trả cho người không phải chủ.', 'trả nhầm người', safety=True)
    elif len(asked) < 2 or not ({'q:inside', 'q:id'} & set(asked)):
        t['mistakes'] += 1
        cq.slip(t, 'thin', 1, 'Trả đồ mà hỏi qua loa, may mà đúng chủ.', 'hỏi chưa kỹ')
    t['choice'] = 'give'
    t['result'] = 'given'
    if x['genuine']:
        _bump(d, 'helped')
        d['stats']['returned'] = min(10 ** 7, d['stats']['returned'] + 1)
    _fact(d, t, f'Đồ thất lạc: trả {_low(x["item"])} cho {x["who"]}, có ký nhận.' + ('' if x['genuine'] else ' Người nhận không phải chủ, đã báo cáo.'),
          key=not x['genuine'], lie=f'Đồ thất lạc: {_low(x["item"])} đã trả đúng chủ, đối chiếu đủ.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, f'Trả lại {_low(x["item"])}.')
    head = (f'👛 {x["who"]} ký nhận, cảm ơn rối rít.' if x['genuine'] else
            f'👛 {x["who"]} ký nhận rồi đi vội. Chiều đó chủ thật lên hỏi… 📋 Anh Định lập báo cáo, đi tìm lại đồ.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t), correct=not cq.safety(t))


def _keep(s, c, d, p):
    t = _task(c, p, ('lost',))
    kit.need(_seen(t, 'count'), 'Kiểm đếm, ký biên bản tiếp nhận trước đã.')
    x = _case_of(t)
    asked = _asked(t, 'q:')
    if x['genuine']:
        g = _guard(d, 'keep', 'Người ta trả lời khớp hết mà em. Hỏi thêm cho chắc rồi trả.' if asked else 'Hỏi vài câu đã, đừng từ chối ngay.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'needless', 2 if len(asked) >= 2 else 1, 'Chủ thật trả lời đúng mà vẫn không được nhận lại.', 'giữ lại khi đúng chủ')
    elif not asked:
        t['mistakes'] += 1
        cq.slip(t, 'blind', 1, 'Không hỏi câu nào đã từ chối.', 'từ chối khi chưa hỏi')
    t['choice'] = 'keep'
    t['result'] = 'kept'
    item = _low(x['item'])
    _fact(d, t, f'Đồ thất lạc: chưa trả {item}, người tới nhận chưa chứng minh được là chủ.' if not x['genuine'] else
          f'Đồ thất lạc: chưa trả {item}, người tới nhận được hẹn mang thêm giấy tờ.', key=not x['genuine'])
    msg = _finish(s, c, d, t, BONUS, f'Giữ lại {_low(x["item"])} chờ chủ thật.')
    head = (f'🔒 Bạn cất {_low(x["item"])} vào tủ: “Anh mang thêm giấy tờ, chứng minh được thì phường trả.” {x["who"]} lủi đi mất.'
            if not x['genuine'] else f'🔒 {x["who"]} ngơ ngác: “Tôi trả lời đúng hết mà?” Hẹn mai lên lại.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- mediation
def _tol(t: dict, side: str, term: str) -> int:
    """How far from its own end of a term a side accepts (hidden: rolled from the task, softened by being heard)."""
    x = _case_of(t)
    s_ = x[side]
    n = len(next(tm for tm in x['terms'] if tm['id'] == term)['options'])
    if term != s_['care']:
        return n - 1
    base = 1 if folk.traits(f'{t["id"]}:{side}', s_['persona'])['mood'] >= 55 else 0
    return max(0, min(n - 1, base + _seen(t, f'hear:{side}') - _seen(t, 'threat')))


def accepts(t: dict, side: str, terms: dict) -> bool:
    x = _case_of(t)
    for tm in x['terms']:
        n = len(tm['options'])
        i = terms[tm['id']]
        tol = _tol(t, side, tm['id'])
        if (side == 'a' and i > tol) or (side == 'b' and i < n - 1 - tol):
            return False
    return True


def _hear(s, c, d, p):
    t = _task(c, p, ('dispute',))
    side = kit.one_of(p.get('side'), ('a', 'b'), 'Chọn bên muốn nghe.')
    kit.need(not _seen(t, f'hear:{side}'), 'Đã nghe bên này rồi.')
    _see(t, f'hear:{side}')
    kit.start_work(t)
    return dict(message=f'👂 {_case_of(t)[side]["heard"]}')


def _offer(s, c, d, p):
    t = _task(c, p, ('dispute',))
    x = _case_of(t)
    kit.need(len(t['offers']) < PC.MAX_OFFERS, 'Đã đề xuất ba lần rồi. Chuyển tổ hòa giải, hẹn buổi sau.')
    kit.need(not (t['offers'] and t['offers'][-1]['a'] and t['offers'][-1]['b']), 'Hai bên đã đồng ý rồi, ký biên bản thôi.')
    raw = p.get('terms')
    kit.need(isinstance(raw, dict) and set(raw) == {tm['id'] for tm in x['terms']}, 'Chọn đủ từng điều khoản.')
    terms = {tm['id']: kit.integer(raw[tm['id']], 0, len(tm['options']) - 1) for tm in x['terms']}
    if not (_seen(t, 'hear:a') and _seen(t, 'hear:b')):
        g = _guard(d, 'hear', 'Nghe cả hai bên đã. Người ta chịu nhường khi thấy mình được nghe.')
        if g:
            return g
    kit.start_work(t)
    a, b = accepts(t, 'a', terms), accepts(t, 'b', terms)
    t['offers'].append(dict(terms=terms, a=a, b=b))
    said = ', '.join(f'{_low(tm["label"])}: {_low(tm["options"][terms[tm["id"]]])}' for tm in x['terms'])
    lines = [f'{x[k]["name"]}: “Được, tôi chịu.”' if ok else f'{x[k]["name"]}: {x[k]["no"]}' for k, ok in (('a', a), ('b', b))]
    tail = ''
    if a and b:
        tail = ' 🤝 Hai bên gật đầu. Ký biên bản hòa giải thôi.'
    elif len(t['offers']) >= PC.MAX_OFFERS:
        tail = ' Ba lần chưa xong: chuyển tổ hòa giải, hẹn buổi sau.'
    return dict(message=f'📝 Đề xuất: {said}. ' + ' '.join(lines) + tail, celebrate=a and b)


def _threat(s, c, d, p):
    t = _task(c, p, ('dispute',))
    kit.need(not _seen(t, 'threat'), 'Đã dọa rồi.')
    g = _guard(d, 'threat', 'Hòa giải là để hai nhà còn nhìn mặt nhau. Dọa phạt thì ai cũng cứng lại.')
    if g:
        return g
    _see(t, 'threat')
    kit.start_work(t)
    t['mistakes'] += 1
    cq.slip(t, 'threat', 2, 'Lên hòa giải mà bị dọa phạt cả hai nhà.', 'dọa thay vì hòa giải')
    x = _case_of(t)
    return dict(message=f'😤 “Không chịu thì phạt cả hai!” {x["a"]["name"]} khoanh tay, {x["b"]["name"]} quay mặt đi. Không khí đặc quánh.', correct=False)


def _sign(s, c, d, p):
    t = _task(c, p, ('dispute',))
    kit.need(t['offers'] and t['offers'][-1]['a'] and t['offers'][-1]['b'], 'Hai bên chưa cùng đồng ý.')
    x = _case_of(t)
    last = t['offers'][-1]['terms']
    said = '; '.join(f'{tm["label"]}: {tm["options"][last[tm["id"]]]}' for tm in x['terms'])
    t['choice'] = 'sign'
    t['result'] = 'agreed'
    _bump(d, 'helped')
    d['stats']['deals'] = min(10 ** 7, d['stats']['deals'] + 1)
    _fact(d, t, f'Hòa giải {_low(x["title"])}: hai bên ký biên bản ({said}).'[:160], key=True)
    msg = _finish(s, c, d, t, BONUS, f'Hòa giải thành: {_low(x["title"])}.')
    return dict(message=f'🤝 {x["a"]["name"]} và {x["b"]["name"]} ký biên bản hòa giải: {said}. {msg}'.strip(), celebrate=not cq.slips(t))


def _refer(s, c, d, p):
    t = _task(c, p, ('dispute',))
    kit.need(not (t['offers'] and t['offers'][-1]['a'] and t['offers'][-1]['b']), 'Hai bên đã đồng ý rồi, ký biên bản thôi.')
    x = _case_of(t)
    kit.start_work(t)
    t['mistakes'] += 1
    cq.slip(t, 'nodeal', 1, 'Lên phường hòa giải mà chưa xong, phải hẹn buổi khác.', 'chưa hòa giải được')
    t['choice'] = 'refer'
    t['result'] = 'referred'
    _fact(d, t, f'Hòa giải {_low(x["title"])}: chưa thành, chuyển tổ hòa giải, hẹn buổi sau.', key=True,
          lie=f'Hòa giải {_low(x["title"])}: hai bên đã ký biên bản.')
    msg = _finish(s, c, d, t, BONUS, f'Chuyển tổ hòa giải: {_low(x["title"])}.')
    return dict(message=f'📅 Chuyển tổ hòa giải cơ sở, hẹn hai nhà buổi sau. {msg}'.strip())


# ---------------------------------------------------------------- lost children
def _calm(s, c, d, p):
    t = _task(c, p, ('child',))
    kit.need(not _seen(t, 'calm'), 'Bé đã bình tĩnh hơn rồi.')
    _see(t, 'calm')
    kit.start_work(t)
    x = _case_of(t)
    return dict(message=f'🧸 Bạn ngồi xuống ngang tầm mắt {_low(x["kid"])}, đưa ly nước, nói nhỏ: “Chú/cô ở đây với con, mình đứng chỗ này chờ mẹ nha.” Bé nín dần.')


def _not_calm(d: dict, t: dict) -> dict | None:
    if _seen(t, 'calm') or any(r['code'] == 'calm' for r in cq.slips(t)):
        return None
    g = _guard(d, 'calm', 'Dỗ bé trước đã. Bé đang sợ thì hỏi gì cũng không nói được.')
    if g:
        return g
    t['mistakes'] += 1
    cq.slip(t, 'calm', 1, 'Bé đang khóc mà bị hỏi dồn, càng sợ.', 'chưa dỗ bé')
    return None


def _kq(s, c, d, p):
    t = _task(c, p, ('child',))
    q = kit.one_of(p.get('q'), KID_Q, 'Câu hỏi không có.')
    kit.need(not _seen(t, f'k:{q}'), 'Đã hỏi rồi.')
    stop = _not_calm(d, t)
    if stop:
        return stop
    _see(t, f'k:{q}')
    kit.start_work(t)
    return dict(message=f'{KID_Q[q][0]} {_case_of(t)["asks"][q]}')


def _tag(s, c, d, p):
    t = _task(c, p, ('child',))
    kit.need(not _seen(t, 'tag'), 'Đã xem rồi.')
    _see(t, 'tag')
    kit.start_work(t)
    return dict(message=f'🎒 {_case_of(t)["tag"]}')


def _announce(s, c, d, p):
    t = _task(c, p, ('child',))
    how = kit.one_of(p.get('how'), ANNOUNCE, 'Chọn cách tìm người nhà.')
    kit.need(not _seen(t, f'a:{how}'), 'Đã làm rồi.')
    if how == 'call':
        kit.need(_seen(t, 'tag'), 'Xem thẻ tên của bé trước đã.')
    if how == 'post':
        g = _guard(d, 'post', 'Không đăng ảnh, thông tin của trẻ lên mạng. Đọc loa, gọi số trên thẻ là đủ.')
        if g:
            return g
    stop = _not_calm(d, t)
    if stop:
        return stop
    _see(t, f'a:{how}')
    kit.start_work(t)
    x = _case_of(t)
    lines = {'loa': f'📢 Loa {_low(x["place"])} đọc: “Một bé {x["age"]}, {_low(x["asks"]["wear"])} Người nhà mời tới điểm tìm trẻ lạc.”',
             'call': '📞 Gọi số trên thẻ: chuông đổ, đầu dây vội vã “Tôi tới ngay!”' if x['genuine'] else
                     '📞 Gọi số trên thẻ, mẹ bé nghe máy: “Hôm nay ông ngoại đón, chị giữ cháu giúp tôi, ông sắp tới.”',
             'post': '📲 Ảnh bé lên nhóm khu phố, ba trăm lượt chia sẻ trong mười phút, kèm cả tên trường.'}
    if how == 'post':
        t['mistakes'] += 1
        cq.slip(t, 'post', 2, 'Ảnh và thông tin của bé bị đăng lên mạng.', 'đăng ảnh trẻ lên mạng')
    msg = lines[how]
    if not _seen(t, 'arrived'):
        _see(t, 'arrived')
        msg += f' Một lúc sau, {x["who"]} tới: “Cho tôi đón bé!”'
    return dict(message=msg, correct=how != 'post')


def _verify(s, c, d, p):
    t = _task(c, p, ('child',))
    kit.need(_seen(t, 'arrived'), 'Chưa có ai tới đón.')
    q = kit.one_of(p.get('q'), VERIFY, 'Chọn cách xác minh.')
    kit.need(not _seen(t, f'v:{q}'), 'Đã xác minh cách này rồi.')
    _see(t, f'v:{q}')
    return dict(message=f'{VERIFY[q][0]} {_case_of(t)["says"][q]}')


def _handover(s, c, d, p):
    t = _task(c, p, ('child',))
    kit.need(_seen(t, 'arrived'), 'Chưa có ai tới đón.')
    x = _case_of(t)
    checks = _asked(t, 'v:')
    if len(checks) < 2:
        g = _guard(d, 'verify', 'Xác minh ít nhất hai cách rồi mới giao bé: để bé tự nhận, hỏi người đón, gọi bố mẹ.')
        if g:
            return g
    if not x['genuine']:
        g = _guard(d, 'adult', 'Bố mẹ bé có nhờ người này đón không? Chưa chắc thì giữ bé lại.')
        if g:
            return g
    _not_calm(d, t)
    if not x['genuine']:
        t['mistakes'] += 1
        cq.slip(t, 'wrong_adult', 3, 'Bé được giao cho người mà bố mẹ không nhờ đón.', 'giao trẻ khi chưa xác minh', safety=True)
    elif len(checks) < 2:
        t['mistakes'] += 1
        cq.slip(t, 'thin', 2, 'Giao bé mà xác minh qua loa, may mà đúng người nhà.', 'xác minh chưa kỹ')
    t['choice'] = 'handover'
    t['result'] = 'handed'
    if x['genuine']:
        _bump(d, 'helped')
        d['stats']['kids'] = min(10 ** 7, d['stats']['kids'] + 1)
    _fact(d, t, f'Trẻ lạc: {x["kid"]} ({_low(x["place"])}) đã giao cho {x["who"]}.' + ('' if x['genuine'] else ' Bố mẹ không nhờ người này, đã báo cáo.'),
          key=True, lie=f'Trẻ lạc: {x["kid"]} đã giao cho người nhà, xác minh đủ.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, f'Giao {_low(x["kid"])} cho người nhà.')
    head = (f'🧒 {x["kid"]} về với {x["who"]}. Cả hai cảm ơn rối rít.' if x['genuine'] else
            f'🧒 {x["who"]} dắt bé đi. Mười phút sau ông ngoại bé tới… 📋 Anh Định gọi ngay cho mẹ bé, lập báo cáo.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t), correct=not cq.safety(t))


def _hold(s, c, d, p):
    t = _task(c, p, ('child',))
    kit.need(_seen(t, 'arrived'), 'Chưa có ai tới đón.')
    x = _case_of(t)
    checks = _asked(t, 'v:')
    if x['genuine']:
        g = _guard(d, 'hold', 'Bé nhận ra người nhà, mọi thứ khớp rồi mà em.' if checks else 'Xác minh trước đã, đừng giữ bé vô cớ.')
        if g:
            return g
        t['mistakes'] += 1
        cq.slip(t, 'needless', 1, 'Người nhà thật đứng đó mà vẫn phải chờ.', 'giữ bé khi đã rõ người nhà')
    t['choice'] = 'hold'
    t['result'] = 'held'
    _bump(d, 'helped')
    _fact(d, t, f'Trẻ lạc: giữ {x["kid"]} ở phường, gọi bố mẹ xác nhận.', key=True)
    msg = _finish(s, c, d, t, BONUS, f'Giữ {_low(x["kid"])} chờ bố mẹ xác nhận.')
    head = (f'🏠 Bạn giữ bé ở phường, gọi mẹ bé. Mười phút sau ông ngoại tới, mẹ xác nhận qua điện thoại. {x["who"]} gật gù: “Vậy là đúng.”'
            if not x['genuine'] else f'🏠 {x["who"]} phải ngồi chờ thêm mười phút cho phường gọi xác nhận, hơi phật ý.')
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t))


# ---------------------------------------------------------------- patrols
def _scene(t: dict, i) -> tuple:
    ids = t['_v']['scenes']
    n = kit.integer(i, 0, len(ids) - 1)
    return n, ids[n], SCENES[ids[n]]


def _look(s, c, d, p):
    t = _task(c, p, ('patrol',))
    n, sid, x = _scene(t, p.get('i'))
    kit.need(not _seen(t, f'look:{n}'), 'Đã xem kỹ rồi.')
    _see(t, f'look:{n}')
    kit.start_work(t)
    return dict(message=f'🔍 {x["look"]}')


def _act(s, c, d, p):
    t = _task(c, p, ('patrol',))
    n, sid, x = _scene(t, p.get('i'))
    kit.need(str(n) not in t['acts'], 'Chuyện này đã xử lý rồi.')
    opts = {o[0]: o for o in x['options']}
    choice = kit.one_of(p.get('choice'), opts, 'Chọn cách xử lý.')
    _, label, grade, outcome = opts[choice]
    if grade in ('unsafe', 'bad', 'bribe'):
        g = _guard(d, f'scene:{sid}', 'Khoan. Nhắc trước, biên bản sau; nguy hiểm thì làm cho an toàn trước đã. Xem kỹ rồi chọn lại nhé.')
        if g:
            return g
    t['acts'][str(n)] = choice
    kit.start_work(t)
    note = ''
    if grade == 'bribe':
        note = _bribe(c, d, t, 'Cán bộ đang tuần tra mà nhận phong bì, ngồi vào chiếu bạc.')
    elif grade == 'unsafe':
        t['mistakes'] += 1
        cq.slip(t, f'unsafe{n}', 3, outcome, 'bỏ qua nguy hiểm trước mắt', safety=True)
        _bump(d, 'safety')
    elif grade == 'bad':
        t['mistakes'] += 1
        cq.slip(t, f'bad{n}', 2, outcome, 'xử lý chưa đúng')
    elif grade == 'ok':
        t['mistakes'] += 1
        cq.slip(t, f'ok{n}', 1, outcome, 'xử lý chưa trọn')
    if grade != 'good' and not _seen(t, f'look:{n}'):
        cq.slip(t, 'blind', 1, 'Xử lý mà không xem kỹ đầu đuôi.', 'chưa xem kỹ')
    if choice == 'report':
        _bump(d, 'reports')
    elif choice == 'remind':
        _bump(d, 'reminders')
    return dict(message=f'{x["emoji"]} {outcome} {note}'.strip(), celebrate=grade == 'good', correct=grade not in ('unsafe', 'bribe'))


def _endpatrol(s, c, d, p):
    t = _task(c, p, ('patrol',))
    ids = t['_v']['scenes']
    kit.need(len(t['acts']) == len(ids), 'Xử lý đủ ba chuyện rồi mới về.')
    t['choice'] = 'end'
    t['result'] = 'patrolled'
    _bump(d, 'helped')
    name = t['needs']['name']
    rep = sum(1 for v in t['acts'].values() if v == 'report')
    rem = sum(1 for v in t['acts'].values() if v == 'remind')
    unsafe = any(r.get('safety') for r in cq.slips(t))
    _fact(d, t, f'Tuần tra {name}: {rem} lần nhắc nhở, {rep} biên bản — có chuyện nguy hiểm bị bỏ qua.' if unsafe else
          f'Tuần tra {name}: {rem} lần nhắc nhở, {rep} biên bản.', key=unsafe or rep > 0,
          lie=f'Tuần tra {name}: lập {rep + 3} biên bản xử lý vi phạm.')
    msg = _finish(s, c, d, t, BONUS, f'Tuần tra {name}.')
    return dict(message=f'🚶 Xong vòng tuần tra {name}. {msg}'.strip(), celebrate=not cq.slips(t), correct=not unsafe)


# ---------------------------------------------------------------- scam-awareness talks
def _invite(s, c, d, p):
    t = _task(c, p, ('talk',))
    kit.need(not _seen(t, 'invite'), 'Đã đọc thư mời rồi.')
    _see(t, 'invite')
    kit.start_work(t)
    return dict(message=f'✉️ {_case_of(t)["invite"]}')


def _add_topic_rules(t: dict, need=kit.need) -> None:
    """What cap_topic refuses when one more topic is added (a chosen chip only comes off). public_task sends it as
    can.cap_topic, for the chips not chosen yet."""
    need(len(t['topics']) < PC.TOPIC_MAX, f'Chọn tối đa {PC.TOPIC_MAX} chủ đề cho một buổi.')


def _topic(s, c, d, p):
    t = _task(c, p, ('talk',))
    kit.need(not _seen(t, 'present'), 'Đã trình bày rồi.')
    k = kit.one_of(p.get('topic'), TOPICS, 'Chủ đề không có.')
    if k in t['topics']:
        t['topics'].remove(k)
        return dict(message=f'Bỏ chủ đề: {_low(TOPICS[k][1])}.')
    _add_topic_rules(t)
    t['topics'].append(k)
    return dict(message=f'{TOPICS[k][0]} Thêm chủ đề: {_low(TOPICS[k][1])}.')


def _present(s, c, d, p):
    t = _task(c, p, ('talk',))
    kit.need(not _seen(t, 'present'), 'Đã trình bày rồi.')
    kit.need(t['topics'], 'Chọn ít nhất một chủ đề.')
    x = _case_of(t)
    miss = [k for k in x['want'] if k not in t['topics']]
    if not _seen(t, 'invite'):
        g = _guard(d, 'invite', 'Đọc thư mời đã: ở đó vừa có chuyện gì thì nói chuyện đó trước.')
        if g:
            return g
    if miss:
        g = _guard(d, 'topics', 'Thư mời kể chuyện gì vừa xảy ra ở đó? Nói đúng chuyện người ta cần nghe.')
        if g:
            return g
    _see(t, 'present')
    kit.start_work(t)
    if not _seen(t, 'invite'):
        t['mistakes'] += 1
        cq.slip(t, 'noinvite', 1, 'Nói chuyện mà không biết ở đây vừa xảy ra chuyện gì.', 'chưa đọc thư mời')
    if miss:
        t['mistakes'] += 1
        cq.slip(t, 'miss', min(3, len(miss)), f'Nói đủ thứ mà không nhắc chuyện {_low(TOPICS[miss[0]][1])}, đúng cái tổ đang gặp.', 'chưa nói đúng chuyện cần nghe')
    lines = ' '.join(f'{TOPICS[k][0]} {TOPICS[k][2]}' for k in t['topics'])
    return dict(message=f'🎤 {lines} Các cụ bắt đầu hỏi.', celebrate=not miss)


def _answer(s, c, d, p):
    t = _task(c, p, ('talk',))
    kit.need(_seen(t, 'present'), 'Trình bày trước đã.')
    x = _case_of(t)
    q = kit.one_of(p.get('q'), x['qs'], 'Câu hỏi không có.')
    kit.need(q not in t['answers'], 'Đã trả lời câu này rồi.')
    opts = {o[0]: o for o in TALK_Q[q]['options']}
    choice = kit.one_of(p.get('option'), opts, 'Chọn câu trả lời.')
    _, label, grade, outcome = opts[choice]
    if grade == 'bad':
        g = _guard(d, f'answer:{q}', 'Nghĩ lại đi em: nói vậy thì các cụ dễ bị lừa hơn.')
        if g:
            return g
    t['answers'][q] = choice
    n = len(t['answers'])
    if grade == 'bad':
        t['mistakes'] += 1
        cq.slip(t, f'qbad{n}', 2, f'Cán bộ trả lời sai câu hỏi về lừa đảo: “{label}”.'[:200], 'trả lời sai')
    elif grade == 'ok':
        t['mistakes'] += 1
        cq.slip(t, f'qok{n}', 1, 'Trả lời chưa đủ ý, các cụ còn lăn tăn.', 'trả lời chưa trọn')
    msg = f'{TALK_Q[q]["who"]}: {outcome}'
    if len(t['answers']) == len(x['qs']):
        t['choice'] = 'done'
        t['result'] = 'talked'
        _bump(d, 'helped')
        topics = ', '.join(_low(TOPICS[k][1]) for k in t['topics'])
        _fact(d, t, f'Nói chuyện chống lừa đảo ở {_low(x["where"])}: {topics}.',
              key=False, lie=f'Nói chuyện chống lừa đảo ở {_low(x["where"])}: trả lời đúng hết mọi câu hỏi.' if cq.slips(t) else None)
        msg += ' ' + _finish(s, c, d, t, BONUS, f'Nói chuyện chống lừa đảo ở {_low(x["where"])}.')
        msg = f'🎤 {msg} Buổi nói chuyện kết thúc, các cụ vỗ tay.' if not cq.slips(t) else f'🎤 {msg}'
    return dict(message=msg.strip(), celebrate=grade == 'good', correct=grade != 'bad')


# ---------------------------------------------------------------- the duty phone
def _call_index(t: dict, i) -> int:
    return kit.integer(i, 0, len(t['_v']['calls']) - 1)


def _cb(s, c, d, p):
    t = _task(c, p, ('calls',))
    i = _call_index(t, p.get('i'))
    kit.need(not _seen(t, f'cb:{i}'), 'Đã gọi lại rồi.')
    _see(t, f'cb:{i}')
    kit.start_work(t)
    x = CALLS[t['_v']['calls'][i]]
    return dict(message=f'📞 {x["who"]}: {x["detail"]}')


def _prio(s, c, d, p):
    t = _task(c, p, ('calls',))
    i = _call_index(t, p.get('i'))
    k = kit.one_of(p.get('prio'), PRIO, 'Mức ưu tiên không có trên thẻ.')
    t['prio'][str(i)] = k
    kit.start_work(t)
    e, name, when = PRIO[k]
    return dict(message=f'{e} {t["needs"]["queue"][i]["who"]}: {_low(name)} · {_low(when)}.')


def _dispatch(s, c, d, p):
    t = _task(c, p, ('calls',))
    ids = t['_v']['calls']
    kit.need(len(t['prio']) == len(ids), 'Xếp ưu tiên cho cả ba cuộc gọi đã.')
    under = [i for i, k in enumerate(ids) if CALLS[k]['best'] == 'now' and t['prio'][str(i)] != 'now']
    if under:
        g = _guard(d, 'under', f'Xem lại {_low(t["needs"]["queue"][under[0]]["who"])}: có người đang gặp nguy không?')
        if g:
            return g
    lines = []
    worst = 0
    for i, k in enumerate(ids):
        x = CALLS[k]
        got = t['prio'][str(i)]
        e = PRIO[x['best']][0]
        if got == 'fake' and not _seen(t, f'cb:{i}'):
            t['mistakes'] += 1
            cq.slip(t, 'blind', 1, 'Coi là tin báo sai mà không gọi lại kiểm tra.', 'chưa gọi lại')
        if got == x['best'] or got in x.get('ok', ()):
            lines.append(f'{PRIO[got][0]} {x["who"]}: đúng.')
            continue
        t['mistakes'] += 1
        if x['best'] == 'now':
            cq.slip(t, f'under{i}', 3, f'{x["who"]} gọi báo người đang gặp nguy mà phải chờ.', 'để người gặp nguy phải chờ', safety=True)
            worst = 3
        elif got == 'fake':
            cq.slip(t, f'dismiss{i}', 2, f'Tin báo thật của {_low(x["who"])} bị coi là báo sai.', 'gạt tin báo thật')
            worst = max(worst, 2)
        elif x['best'] == 'fake':
            cq.slip(t, f'over{i}', 1, 'Chạy theo một tin báo sai, việc khác phải chờ.', 'chạy theo tin báo sai')
        else:
            cq.slip(t, f'order{i}', 1, 'Xếp chưa đúng mức gấp.', 'xếp chưa đúng mức')
        lines.append(f'{PRIO[got][0]} {x["who"]}: đáng lẽ {e} {_low(PRIO[x["best"]][1])}.')
    t['choice'] = 'dispatched'
    t['result'] = 'dispatched'
    _bump(d, 'helped')
    nows = [CALLS[k]['who'] for i, k in enumerate(ids) if t['prio'][str(i)] == 'now']
    if worst >= 3:
        _bump(d, 'safety')
    _fact(d, t, f'Trực ban: ba cuộc gọi, đi ngay: {", ".join(nows)}.' if nows else 'Trực ban: ba cuộc gọi, không có việc đi ngay.', key=bool(nows) or worst >= 3,
          lie='Trực ban: xử lý đúng mức cả ba cuộc gọi.' if cq.slips(t) else None)
    msg = _finish(s, c, d, t, BONUS, 'Xếp cuộc gọi ở điện thoại trực ban.')
    head = '☎️ ' + ' '.join(lines)
    if nows:
        head += ' 🚨 Tổ tuần tra lên đường ngay.'
    return dict(message=f'{head} {msg}'.strip(), celebrate=not cq.slips(t), correct=worst < 3)


# ---------------------------------------------------------------- finishing a task
def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str, job: bool = True) -> str:
    """Pays the bonus (none after a serious slip; half when tired, none while demoted) and completes once."""
    pts = cq.points(t)
    full = 0 if cq.safety(t) or not reward else max(0, reward - 3 * pts)
    pay = ao.bonus(d['odd'], full)
    t['stage'] = 'done'
    story = ''
    i = _npc_index(t)
    if job and i in PC.REG_STORY:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        story = PC.REG_STORY[i][min(r['visits'], len(PC.REG_STORY[i])) - 1]
        t['story'] = story
    if job:
        d['learn']['n'] = min(10 ** 6, d['learn']['n'] + 1)
        _bump(d, 'tasks')
    kit.complete(s, c, t, pay, (narrative or t['title'])[:300])
    note = ao.flown(d['odd'], not cq.slips(t), CFG) if job else ''
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
    """A line the end-of-shift duty book may carry (true), and a tempting one that did not happen (lie)."""
    rows = d['today']['facts']
    fid = f'f-{t["id"]}'
    if any(r['id'] == fid for r in rows):
        fid = f'f-{t["id"]}-2'
    rows.append(dict(id=fid, text=text[:160], key=bool(key), true=True))
    if lie and not any(r['id'] == f'l-{t["id"]}' for r in rows):
        rows.append(dict(id=f'l-{t["id"]}', text=lie[:160], key=False, true=False))
    d['today']['facts'] = rows[-FACTS_MAX:]


# ---------------------------------------------------------------- the end-of-shift duty book
def _log(s, c, d, p):
    today = d['today']
    kit.need(today['log'] is None, 'Hôm nay đã ghi sổ trực ban rồi.')
    rows = today['facts']
    kit.need(rows, 'Chưa có gì để ghi sổ. Làm việc trước đã.')
    pick = kit.id_list(p.get('lines') or [], [r['id'] for r in rows], FACTS_MAX, 'Chọn dòng ghi vào sổ.')
    kit.need(pick, 'Chọn ít nhất một dòng ghi vào sổ trực ban.')
    chosen = [r for r in rows if r['id'] in pick]
    lies = [r for r in chosen if not r['true']]
    miss = [r for r in rows if r['key'] and r['true'] and r['id'] not in pick]
    d['stats']['logs'] = min(10 ** 7, d['stats']['logs'] + 1)
    if lies:
        today['log'] = 'false'
        note = ao.penalize(c, d['odd'], 2, CFG)
        return dict(message=f'📒 Anh Định đọc sổ, khựng lại ở dòng “{lies[0]["text"]}”: “Cái này đâu có xảy ra, em?” Ghi khống vào sổ trực ban. {note}',
                    correct=False)
    if miss:
        today['log'] = 'miss'
        c['xp'] += 2
        return dict(message=f'📒 Sổ trực ban thật, nhưng thiếu: “{miss[0]["text"]}”. Ca sau phải gọi điện hỏi lại.')
    today['log'] = 'ok'
    c['xp'] += 8
    d['stats']['honest'] = min(10 ** 7, d['stats']['honest'] + 1)
    return dict(message='📒 Sổ trực ban rõ ràng, thật, đủ việc cần theo dõi. Ca sau đọc một lượt là nắm hết.', celebrate=True)


ACTIONS = {
    'cap_read': _read, 'cap_first': _first,
    'cap_doc': _doc, 'cap_press': _press, 'cap_accept': _accept, 'cap_back': _back,
    'cap_count': _count, 'cap_lq': _lq, 'cap_give': _give, 'cap_keep': _keep,
    'cap_hear': _hear, 'cap_offer': _offer, 'cap_threat': _threat, 'cap_sign': _sign, 'cap_refer': _refer,
    'cap_calm': _calm, 'cap_kq': _kq, 'cap_tag': _tag, 'cap_announce': _announce, 'cap_verify': _verify, 'cap_handover': _handover, 'cap_hold': _hold,
    'cap_look': _look, 'cap_act': _act, 'cap_endpatrol': _endpatrol,
    'cap_invite': _invite, 'cap_topic': _topic, 'cap_present': _present, 'cap_answer': _answer,
    'cap_cb': _cb, 'cap_prio': _prio, 'cap_dispatch': _dispatch,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['today'] = _fresh_today(day)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'brief' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    if not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        sh = make_task(day, 0, c['turn'])
        c['tasks'].append(sh)
        on_task(s, c, sh)
    sh = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'brief' and t['day'] == day
               and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if sh:
        c['active_task'] = sh['id']
        sh['deferred'] = False
    ao.start(c, ID, d['odd'])
    kit.desk_start(s, c, ID, d['desk'], PC.DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')
    ao.tick(s, c, ID, d['odd'], PC.ODD, busy=d['desk']['ev'] is not None)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], PC.DESK)
    odd_note = ao.close(s, c, d['odd'], PC.ODD)
    x = d['today']
    lines = [f'👮 Ca trực: {x["tasks"]} việc ở Công an phường Mây.']
    if x['helped']:
        lines.append(f'🤝 Giúp dân {x["helped"]} việc: giấy tờ, đồ thất lạc, hòa giải, trẻ lạc, tin báo.')
    if x['reminders'] or x['reports']:
        lines.append(f'🚶 Tuần tra: {x["reminders"]} lần nhắc nhở, {x["reports"]} biên bản. Nhắc trước, biên bản sau.')
    if x['refused']:
        lines.append(f'✉️ Từ chối {x["refused"]} phong bì. Đúng bài.')
    if x['safety']:
        lines.append(f'📋 {x["safety"]} báo cáo sự việc. Mai họp tổ rút kinh nghiệm.')
    if x['log'] is None and x['facts']:
        lines.append('📒 Chưa ghi sổ trực ban: ca sau phải đi hỏi lại từng việc.')
    elif x['log'] == 'ok':
        lines.append('📒 Sổ trực ban rõ ràng, thật, đủ.')
    if desk_note:
        lines.append(desk_note)
    if odd_note:
        lines.append(odd_note)
    lines += ao.day_lines(c, d['odd'], CFG)
    lines.append('🏠 Tối về ngang chợ Mây, dì Út đã dọn sạp, còn vẫy tay chào.')
    return dict(lines=lines, note='Mai giao ban lúc 7:30, đọc sổ trực ban trước khi đi.', tasks=x['tasks'], helped=x['helped'],
                reports=x['reports'], reminders=x['reminders'], safety=x['safety'])


# ================================================================ reviews
def _score(codes: set, bad: set, worse: set = frozenset(), worst: set = frozenset()) -> int:
    if codes & worst:
        return 1
    if codes & worse:
        return 2
    if codes & bad:
        return 3
    return 5


def _pre(codes: set, *prefixes: str) -> set:
    return {c_ for c_ in codes if c_.startswith(prefixes)}


def feedback(c: dict, t: dict) -> dict:
    codes = {x['code'] for x in cq.slips(t)}
    k = t.get('kind')
    honest = dict(key='honest', label='Liêm chính', score=_score(codes, set(), set(), {'bribe'}),
                  note='không nhận gì của ai' if 'bribe' not in codes else 'nhận phong bì')
    if k == 'brief':
        return dict(criteria=[dict(key='read', label='Đọc sổ trực ban', score=_score(codes, {'skim'}), note='đọc hết từng mục' if 'skim' not in codes else 'đọc sót'),
                              dict(key='first', label='Việc gấp làm trước', score=_score(codes, set(), {'priority'}), note='chọn đúng việc gấp' if 'priority' not in codes else 'chọn sai')])
    if k == 'desk':
        return dict(criteria=[honest,
                              dict(key='fair', label='Ai cũng như ai', score=_score(codes, {'press_meh'}, {'queue'}), note='đúng lượt, lịch sự' if not codes & {'queue', 'press_meh'} else 'chưa công bằng'),
                              dict(key='papers', label='Xem đủ giấy tờ', score=_score(codes, {'skim', 'guess'}, {'accept_bad', 'wrong_doc', 'needless', 'rush'}, {'wrong_person'}),
                                   note='nhận đúng, bổ sung đúng giấy' if not codes & {'skim', 'guess', 'accept_bad', 'wrong_doc', 'needless', 'rush', 'wrong_person'} else 'hồ sơ chưa chuẩn')])
    if k == 'lost':
        return dict(criteria=[dict(key='verify', label='Hỏi kỹ người nhận', score=_score(codes, {'thin', 'blind'}, set(), {'wrong_owner'}),
                                   note='hỏi đủ, đối chiếu biên bản' if not codes & {'thin', 'blind', 'wrong_owner'} else 'hỏi chưa kỹ'),
                              dict(key='return', label='Trả đúng chủ', score=_score(codes, {'needless'}, set(), {'wrong_owner'}),
                                   note='đồ về đúng chủ' if not codes & {'needless', 'wrong_owner'} else 'chưa đúng chủ')])
    if k == 'dispute':
        return dict(criteria=[dict(key='listen', label='Nghe cả hai bên', score=_score(codes, {'nodeal'}), note='hai nhà được nghe' if 'nodeal' not in codes else 'chưa xong'),
                              dict(key='calm', label='Bình tĩnh, không dọa', score=_score(codes, set(), {'threat'}), note='nói nhẹ, rõ ràng' if 'threat' not in codes else 'dọa phạt')])
    if k == 'child':
        return dict(criteria=[dict(key='care', label='Dỗ bé, giữ bé an toàn', score=_score(codes, {'calm'}, {'post'}), note='bé bình tĩnh, không lộ ảnh' if not codes & {'calm', 'post'} else 'chưa chu đáo'),
                              dict(key='verify', label='Xác minh người đón', score=_score(codes, {'needless'}, {'thin'}, {'wrong_adult'}),
                                   note='giao đúng người nhà' if not codes & {'needless', 'thin', 'wrong_adult'} else 'xác minh chưa đúng')])
    if k == 'patrol':
        return dict(criteria=[honest,
                              dict(key='rule', label='Nhắc trước, biên bản sau', score=_score(codes, _pre(codes, 'ok', 'blind'), _pre(codes, 'bad')),
                                   note='đúng mức, đúng lúc' if not _pre(codes, 'ok', 'bad', 'blind') else 'chưa đúng mức'),
                              dict(key='safe', label='An toàn trước', score=_score(codes, set(), set(), _pre(codes, 'unsafe')),
                                   note='xử lý nguy hiểm ngay' if not _pre(codes, 'unsafe') else 'bỏ qua nguy hiểm')])
    if k == 'talk':
        return dict(criteria=[dict(key='topics', label='Đúng chuyện cần nghe', score=_score(codes, {'noinvite', 'miss'}), note='nói đúng chuyện của tổ' if not codes & {'noinvite', 'miss'} else 'chưa sát'),
                              dict(key='answers', label='Trả lời đúng', score=_score(codes, _pre(codes, 'qok'), _pre(codes, 'qbad')),
                                   note='các cụ hiểu, nhớ' if not _pre(codes, 'qok', 'qbad') else 'trả lời chưa đúng')])
    return dict(criteria=[dict(key='priority', label='Người gặp nguy đi trước', score=_score(codes, set(), set(), _pre(codes, 'under')),
                               note='đúng người cần trước' if not _pre(codes, 'under') else 'để người gặp nguy chờ'),
                          dict(key='check', label='Gọi lại kiểm tra', score=_score(codes, _pre(codes, 'blind', 'order', 'over'), _pre(codes, 'dismiss')),
                               note='kiểm tra rồi mới xếp' if not _pre(codes, 'blind', 'order', 'over', 'dismiss') else 'xếp chưa đúng')])


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    k = t['kind']
    n = t['needs']
    if k == 'brief':
        return 'Sổ trực ban: ' + '; '.join(x['name'] for x in n['entries']) + '.'
    if k == 'desk':
        docs = ', '.join(_low(DOCS[x][1]) for x in n['docs'])
        return f'{n["who"]} ({_low(n["role"])}) khai báo tạm trú: {docs}.'
    if k == 'lost':
        return f'{n["finder"]} nộp {_low(n["item"])} nhặt được: {_low(n["found"])}.'
    if k == 'dispute':
        return f'{n["a"]["name"]}: {n["a"]["say"]} — {n["b"]["name"]}: {n["b"]["say"]}'
    if k == 'child':
        return f'{n["kid"]}, {n["age"]}: {_low(n["found"])}.'
    if k == 'patrol':
        return f'Tuần tra {n["name"]}: ' + ' '.join(sc['text'] for sc in n['scenes'])
    if k == 'talk':
        return f'{n["where"]}: {_low(n["audience"])}.'
    return 'Ba cuộc gọi: ' + '; '.join(f'{q["who"]}: {q["text"]}' for q in n['queue'])


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not t['known'] and t['kind'] != 'brief':
        v['needs'] = None
        return v
    k = t['kind']
    seen = set(t.get('seen') or [])
    n = t['needs']
    done = t['stage'] == 'done'
    if k == 'brief':
        v['needs'] = dict(entries=[dict(e, text=e['text'] if f'note:{e["id"]}' in seen else None) for e in n['entries']])
        if done:
            v['first'] = t['_v']['first']
        return v
    if k == 'calls':
        ids = t['_v']['calls']
        v['needs'] = dict(queue=[dict(q, detail=CALLS[ids[i]]['detail'] if f'cb:{i}' in seen else None, best=CALLS[ids[i]]['best'] if done else None)
                                 for i, q in enumerate(n['queue'])])
        return v
    x = _case_of(t)
    if k == 'desk':
        view = dict(n, checks={doc: DOC_TEXT[doc][x['docs'][doc]] for doc in n['docs'] if f'doc:{doc}' in seen},
                    ok={doc: x['docs'][doc] == 'ok' for doc in n['docs'] if f'doc:{doc}' in seen})
        if n.get('press'):
            pr = PRESS[n['press']]
            view['pressure'] = dict(emoji=pr['emoji'], title=pr['title'], text=pr['text'], answered=t['press'],
                                    options=[dict(id=o[0], label=o[1]) for o in pr['options']])
    elif k == 'lost':
        view = dict(n)
        if 'count' in seen:
            view.update(truth=dict(x['truth']), who=x['who'], who_emoji=x['who_emoji'],
                        says={q: x['says'][q] for q in QUESTIONS_LOST if f'q:{q}' in seen})
    elif k == 'dispute':
        view = dict(n, heard={s_: x[s_]['heard'] for s_ in ('a', 'b') if f'hear:{s_}' in seen}, threat='threat' in seen,
                    offers=[dict(o) for o in t['offers']], deal=bool(t['offers'] and t['offers'][-1]['a'] and t['offers'][-1]['b']),
                    left=PC.MAX_OFFERS - len(t['offers']))
    elif k == 'child':
        view = dict(n, calm='calm' in seen, asks={q: x['asks'][q] for q in KID_Q if f'k:{q}' in seen}, tag=x['tag'] if 'tag' in seen else None,
                    announced=[h for h in ANNOUNCE if f'a:{h}' in seen])
        if 'arrived' in seen:
            view.update(who=x['who'], who_emoji=x['who_emoji'], says={q: x['says'][q] for q in VERIFY if f'v:{q}' in seen})
    elif k == 'patrol':
        ids = t['_v']['scenes']
        rows = []
        for i, sid in enumerate(ids):
            sc = SCENES[sid]
            got = t['acts'].get(str(i))
            opt = next((o for o in sc['options'] if o[0] == got), None)
            rows.append(dict(n['scenes'][i], look=sc['look'] if f'look:{i}' in seen else None, done=got,
                             outcome=opt[3] if opt else None, options=[dict(id=o[0], label=o[1]) for o in sc['options']]))
        view = dict(n, scenes=rows)
    else:
        view = dict(n, invite=x['invite'] if 'invite' in seen else None, presented='present' in seen)
        if 'present' not in seen:
            v['can'] = dict(cap_topic=kit.check(_add_topic_rules, t))
        if 'present' in seen:
            view['questions'] = [dict(id=q, who=TALK_Q[q]['who'], text=TALK_Q[q]['text'], answered=t['answers'].get(q),
                                      options=[dict(id=o[0], label=o[1]) for o in TALK_Q[q]['options']]) for q in x['qs']]
    v['needs'] = view
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
    # While anh Định stands beside a new officer, he points at the duty book's urgent topic once every entry is read.
    point = None
    if lr.get('n', 0) < LEARN:
        b = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'brief' and t.get('stage') == 'open'), None)
        if b and all(f'note:{k}' in (b.get('seen') or []) for k in BRIEF_IDS):
            point = b['_v']['first']
    return dict(intro=d['intro'], mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']),
                today=dict(day=today.get('day', 0), tasks=today.get('tasks', 0), helped=today.get('helped', 0), reports=today.get('reports', 0),
                           reminders=today.get('reminders', 0), refused=today.get('refused', 0), safety=today.get('safety', 0),
                           log=today.get('log'), facts=facts),
                stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                learn=dict(on=lr.get('n', 0) < LEARN, n=lr.get('n', 0), of=LEARN, point=point),
                desk=kit.desk_public(d['desk'], PC.DESK, ID), odd=ao.public(c, ao.ensure(d), PC.ODD, ID, CFG))


def content() -> dict:
    return dict(intro=PC.INTRO, docs={k: list(v) for k, v in DOCS.items()}, back_line=BACK_LINE, lost_q={k: list(v) for k, v in QUESTIONS_LOST.items()},
                kid_q={k: list(v) for k, v in KID_Q.items()}, announce={k: list(v) for k, v in ANNOUNCE.items()},
                verify={k: list(v) for k, v in VERIFY.items()}, places={k: list(v) for k, v in PLACES.items()},
                topics={k: list(v) for k, v in TOPICS.items()}, topic_max=PC.TOPIC_MAX, prio={k: list(v) for k, v in PRIO.items()},
                prio_order=list(PC.PRIO_ORDER), max_offers=PC.MAX_OFFERS, learn=LEARN,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    return {'brief': 'Đọc từng mục sổ trực ban → chọn chuyện có người đang cần mình ngay để làm trước.',
            'desk': 'Trả lời người khai nếu có chuyện → xem từng giấy → đủ thì nhận, thiếu thì chỉ đúng giấy cần bổ sung.',
            'lost': 'Kiểm đếm cùng người nhặt → hỏi người tới nhận ít nhất hai câu (bên trong có gì, giấy tờ) → khớp thì trả, không khớp thì giữ lại.',
            'dispute': 'Nghe bên này → nghe bên kia → đề xuất từng điều khoản → hai bên đồng ý thì ký biên bản.',
            'child': 'Dỗ bé trước → hỏi, xem thẻ tên → đọc loa hoặc gọi số trên thẻ → xác minh người đón hai cách → giao hoặc giữ lại.',
            'patrol': 'Xem kỹ từng chuyện → lần đầu, chuyện nhỏ thì nhắc; tái phạm, nguy hiểm thì lập biên bản; nguy hiểm trước mắt thì xử lý ngay.',
            'talk': 'Đọc thư mời → chọn đúng chủ đề tổ đang gặp → trình bày → trả lời câu hỏi của các cụ.',
            'calls': 'Gọi lại từng cuộc → ai đang gặp nguy thì đi ngay → tin báo sai thì ghi nhận, nhắc nhở → điều động.'}.get(t.get('kind'), '')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'clerk':
        return 'Đã sắp hồ sơ tạm trú theo tổ, phát số thứ tự cho hàng chờ.'
    if e.get('role') == 'aide':
        return 'Đã đi một vòng hẻm nhắc bà con khóa cửa, cất xe.'
    return None


# ================================================================ saves
def _seen_ok(t: dict) -> set:
    k = t.get('kind')
    v = t.get('_v') or {}
    if k == 'brief':
        return {f'note:{b}' for b in BRIEF_IDS}
    if k == 'desk':
        return {f'doc:{x}' for x in DOCS}
    if k == 'lost':
        return {'count'} | {f'q:{q}' for q in QUESTIONS_LOST}
    if k == 'dispute':
        return {'hear:a', 'hear:b', 'threat'}
    if k == 'child':
        return {'calm', 'tag', 'arrived'} | {f'k:{q}' for q in KID_Q} | {f'a:{h}' for h in ANNOUNCE} | {f'v:{q}' for q in VERIFY}
    if k == 'patrol':
        return {f'look:{i}' for i in range(len(v.get('scenes') or []))}
    if k == 'talk':
        return {'invite', 'present'}
    if k == 'calls':
        return {f'cb:{i}' for i in range(len(v.get('calls') or []))}
    return set()


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN and t.get('kind') in KINDS and t.get('stage') in STAGES, 'Việc ở Công an phường sai.')
    seen = t.get('seen')
    kit.need(isinstance(seen, list) and len(seen) == len(set(seen)) and set(seen) <= _seen_ok(t), 'Việc ở Công an phường sai.')
    for key in ('choice', 'result'):
        kit.need(t.get(key) is None or (isinstance(t[key], str) and len(t[key]) <= 24), 'Lựa chọn sai.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện người quen sai.')
    press = (t.get('needs') or {}).get('press') if t.get('kind') == 'desk' else None
    kit.need(t.get('press') is None or (press in PRESS and t['press'] in {o[0] for o in PRESS[press]['options']}), 'Câu trả lời ở bàn cư trú sai.')
    offers = t.get('offers')
    kit.need(isinstance(offers, list) and len(offers) <= PC.MAX_OFFERS, 'Đề xuất hòa giải sai.')
    if offers:
        kit.need(t.get('kind') == 'dispute', 'Đề xuất hòa giải sai.')
        x = DISPUTES.get((t.get('_v') or {}).get('case'))
        kit.need(x is not None, 'Đề xuất hòa giải sai.')
        for o in offers:
            kit.need(isinstance(o, dict) and set(o) == {'terms', 'a', 'b'} and type(o['a']) is bool and type(o['b']) is bool
                     and isinstance(o['terms'], dict) and set(o['terms']) == {tm['id'] for tm in x['terms']}, 'Đề xuất hòa giải sai.')
            for tm in x['terms']:
                kit.integer(o['terms'][tm['id']], 0, len(tm['options']) - 1)
    prio = t.get('prio')
    n_calls = len((t.get('_v') or {}).get('calls') or []) if t.get('kind') == 'calls' else 0
    kit.need(isinstance(prio, dict) and len(prio) <= n_calls and all(k in {str(i) for i in range(n_calls)} and v in PRIO for k, v in prio.items()),
             'Mức ưu tiên sai.')
    acts = t.get('acts')
    scenes = (t.get('_v') or {}).get('scenes') or [] if t.get('kind') == 'patrol' else []
    kit.need(isinstance(acts, dict) and len(acts) <= len(scenes), 'Việc tuần tra sai.')
    for k_, v_ in acts.items():
        kit.need(k_ in {str(i) for i in range(len(scenes))} and v_ in {o[0] for o in SCENES[scenes[int(k_)]]['options']}, 'Việc tuần tra sai.')
    topics = t.get('topics')
    kit.need(isinstance(topics, list) and len(topics) <= PC.TOPIC_MAX and len(set(topics)) == len(topics) and set(topics) <= set(TOPICS), 'Chủ đề sai.')
    answers = t.get('answers')
    qs = TALKS[(t.get('_v') or {}).get('case')]['qs'] if t.get('kind') == 'talk' and (t.get('_v') or {}).get('case') in TALKS else []
    kit.need(isinstance(answers, dict) and set(answers) <= set(qs), 'Câu trả lời sai.')
    for q, a in answers.items():
        kit.need(a in {o[0] for o in TALK_Q[q]['options']}, 'Câu trả lời sai.')


def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu Công an phường sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in PC.REG_STORY}, 'Sổ người quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người quen sai.')
        kit.integer(v['visits'], 0, 999)
    kit.need(isinstance(d['stats'], dict) and len(d['stats']) <= 24, 'Số liệu phường sai.')
    for v in d['stats'].values():
        kit.integer(v, 0, 10 ** 9)
    x = d['today']
    kit.need(isinstance(x, dict) and set(x) == set(_fresh_today(0)), 'Số liệu trong ngày sai.')
    for k in ('day', 'tasks', 'helped', 'reports', 'reminders', 'refused', 'safety'):
        kit.integer(x[k], 0, 10 ** 9)
    kit.need(x['log'] in (None, 'ok', 'miss', 'false'), 'Sổ trực ban sai.')
    kit.need(isinstance(x['facts'], list) and len(x['facts']) <= FACTS_MAX, 'Sổ trực ban sai.')
    for r in x['facts']:
        kit.need(isinstance(r, dict) and set(r) == {'id', 'text', 'key', 'true'} and type(r['key']) is bool and type(r['true']) is bool, 'Sổ trực ban sai.')
        kit.text(r['id'], 60)
        kit.text(r['text'], 160)
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'n', 'caught'} and isinstance(lr['caught'], list) and len(lr['caught']) <= 24, 'Sổ kèm việc sai.')
    kit.integer(lr['n'], 0, 10 ** 6)
    for k in lr['caught']:
        kit.text(k, 40)
    kit.desk_validate(d['desk'], PC.DESK)
    ao.validate(d['odd'], PC.ODD)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='cap_', category='service',
    meta=dict(short='Công an phường', place='Công an phường Mây', tagline='Nhắc trước, biên bản sau, phong bì thì không bao giờ.', icon='shield',
              color='#2f5d8a', light='#e3edf7', weather='Trời trong, phường yên', work='Việc trong ca', station='Bàn tiếp dân',
              greeting='Giao ban lúc 7:30. Đọc sổ trực ban, làm việc gấp trước, ai cũng như ai, không nhận gì của ai.',
              caption='Giúp dân từng việc nhỏ, giữ phường bình yên', map_label='34 · CÔNG AN PHƯỜNG MÂY'),
    people=PEOPLE,
    staff=[('Thảo', 'clerk', 'Văn thư tiếp dân, thuộc lòng thủ tục, chữ đẹp như in.', 76, 94),
           ('Hải', 'aide', 'Tổ an ninh dân phố, biết mặt từng nhà trong hẻm.', 84, 86),
           ('Liên', 'clerk', 'Nhập hồ sơ nhanh, không sót tờ nào.', 82, 90),
           ('Bảy', 'aide', 'Đứng cổng trường mười năm, tụi nhỏ gọi là “ông Bảy đèn xanh”.', 74, 92)],
    roles={'clerk': 'Văn thư tiếp dân', 'aide': 'Tổ an ninh dân phố'},
    tip=0,
    open_line='Giao ban lúc 7:30. Anh Định đang chờ ở phòng giao ban.',
    more_line='Anh Định giao thêm một việc trong ca.',
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    activity=('👮', 'Một ca ở Công an phường', [('Phong bì', 'Trả lại, ghi sổ'), ('Hai bên tranh chấp', 'Nghe cả hai'),
                                               ('Người tới đón trẻ', 'Xác minh hai cách'), ('Lần đầu, chuyện nhỏ', 'Nhắc nhở')],
              ['Giao ban, đọc sổ', 'Tiếp dân, giấy tờ', 'Hòa giải, tuần tra', 'Ghi sổ trực ban']),
    stories=[('Cuốn sổ hẻm của anh Định', ('Anh Định có cuốn sổ nhỏ ghi tên từng nhà, từng cụ già sống một mình trong khu vực.',
                                           'Bạn đi tuần thêm một buổi, ghi thêm vài dòng vào sổ của mình.',
                                           'Anh Định đọc sổ của bạn, gật gù: “Thuộc hẻm rồi đó em.”')),
             ('Cái cặp lồng của bà Năm', ('Bà Năm lên phường mỗi trưa, lần nào cũng mang theo cặp lồng.',
                                          'Bạn làm thêm một ca, ghé nhà bà nghe kể chuyện mười phút.',
                                          'Bà Năm lưu số phường đầu danh bạ: “Có gì bà gọi con trước.”')),
             ('Bảng thành tích mới', ('Anh Vượng treo bảng thành tích đếm biên bản.',
                                      'Bạn làm thêm một ca, ghi đủ từng lần nhắc nhở, hòa giải, giúp dân.',
                                      'Bảng thành tích đổi tên: “Số việc giúp dân”.'))],
    review_asides=['Không nhận gì của ai, làm đúng hẹn.', 'Nghe hết rồi mới nói, dễ chịu ghê.', 'Nhắc khéo mà ai cũng nghe.',
                   'Có cán bộ đứng cổng trường, yên tâm hẳn.'],
    situations=PC.SITUATIONS,
    guide='Giao ban, đọc sổ trực ban → việc gấp làm trước → bàn cư trú xem đủ giấy tờ → đồ thất lạc hỏi kỹ người nhận → hòa giải nghe cả hai bên → '
          'trẻ lạc dỗ bé, xác minh người đón → tuần tra nhắc trước, biên bản sau → không bao giờ nhận phong bì → cuối ca ghi sổ trực ban thật.',
    employment=dict(
        postings=[
            dict(id='cap-kv', org='Công an phường Mây · Tổ cảnh sát khu vực', kind='public', title='Cán bộ cảnh sát khu vực',
                 salary=(55, 72), probation_days=3, wants=['calm', 'communication', 'careful'],
                 perks=['Anh Định kèm ba việc đầu', 'Ca ngày 7:30–17:30', 'Có cơm trưa ở căng tin phường'],
                 culture='Tổ khu vực sáu người, phụ trách bảy tổ dân phố. Ở đây ai lên phường cũng được tiếp như nhau, và không ai nhận phong bì.',
                 questions=['cap_q_envelope', 'cap_q_relative', 'cap_q_dispute', 'mistake'], reference=True),
            dict(id='cap-td', org='Công an phường Mây · Bàn tiếp dân', kind='parttime', title='Hỗ trợ tiếp dân (bán thời gian)',
                 salary=(42, 55), probation_days=2, wants=['patience', 'communication'],
                 perks=['Ca ngắn', 'Ngồi bàn cư trú cùng chị Hằng', 'Lương thấp hơn'],
                 culture='Bàn cư trú đông từ sáng. Việc chính là xem giấy tờ, hướng dẫn bổ sung đúng giấy, giữ hàng chờ đúng lượt.',
                 questions=['cap_q_relative', 'cap_q_child'], reference=False),
        ],
        questions={
            'cap_q_envelope': dict(text='Người khai kẹp phong bì trong hồ sơ “cho nhanh”. Bạn làm gì?', options=[
                dict(id='decline', label='Trả lại, nói rõ hồ sơ đủ thì không mất đồng nào, ghi vào sổ', score=3, note='Anh Định gật đầu: đúng nếp của phường.'),
                dict(id='fund', label='Nhận rồi bỏ quỹ chung', score=0, note='Quỹ chung hay quỹ riêng thì vẫn là nhận.'),
                dict(id='later', label='Bảo để làm xong hẵng đưa', score=0, note='Hẹn lại cũng là nhận.')]),
            'cap_q_relative': dict(text='Một người nói “chú tôi làm trên quận”, đòi làm trước. Bạn nói gì?', options=[
                dict(id='queue', label='Mời lấy số, chờ đúng lượt như mọi người', score=3, note='Ai cũng như ai.'),
                dict(id='call', label='Gọi hỏi “chú” cho chắc', score=1, note='Không cần biết chú ai, hàng chờ vẫn là hàng chờ.'),
                dict(id='skip', label='Làm trước cho yên chuyện', score=0, note='Người chờ từ sáng sẽ nghĩ gì?')]),
            'cap_q_dispute': dict(text='Hai nhà cãi nhau vì karaoke tới khuya. Bạn bắt đầu thế nào?', options=[
                dict(id='listen', label='Nghe riêng từng bên, hỏi điều họ cần nhất, rồi đề xuất', score=3, note='Người được nghe thì chịu nhường.'),
                dict(id='fine', label='Phạt luôn nhà hát karaoke cho xong', score=0, note='Hòa giải là để hai nhà còn nhìn mặt nhau.'),
                dict(id='skip', label='Chuyện hàng xóm, tự giải quyết', score=1, note='Để lâu thì to chuyện.')]),
            'cap_q_child': dict(text='Một người tới đón bé lạc, nói là hàng xóm được nhờ. Bạn làm gì?', options=[
                dict(id='verify', label='Hỏi bé, hỏi người đón, gọi bố mẹ xác nhận rồi mới giao', score=3, note='Xác minh hai cách, chắc rồi mới giao.'),
                dict(id='trust', label='Bé gật đầu là giao', score=1, note='Bé biết mặt chưa chắc là bố mẹ nhờ.'),
                dict(id='give', label='Giao luôn cho đỡ mất thời gian', score=0, note='Không bao giờ giao trẻ khi chưa xác minh.')]),
        }),
)
