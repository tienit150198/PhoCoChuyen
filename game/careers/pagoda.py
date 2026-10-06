"""Chùa Gió Lành: a young monk's day at the neighbourhood pagoda by the river landing (plugin career).

The player is a young monk under the abbot, thầy Huệ Minh. The pagoda is the one the tour guide's trips
stop at: the bronze bell the village cast together (dented in an old storm, so it rings deeper), the well
behind the hall, the areca palms at the three-entrance gate. What the job is:

* in the morning (``setup`` task) keep the schedule (rise, bell, chanting, sweeping, breakfast; never the
  loudspeaker at four) and take in what the abbot says about the day;
* the yard (sweep, the lotus pond, the bonsai), the main hall (flowers and fruit, incense away from the
  curtains, wiping the altar), guiding visitors at the gate (dress code, where to light incense, quiet
  zones; never inventing a "lucky bell"), the vegetarian kitchen with bà Nhạn (what is not vegetarian is
  swapped or set aside; allergies and soft food), the donation book (opened by two, counted in front of
  the giver, written to the xu: the ``tally`` step), listening to someone who is grieving (and when it is
  more than grief: stay, involve the family, a doctor, 115), the full-moon ceremony (an exit kept free,
  no open flame, the loudspeaker off by half past nine), helping the old and the children, incidents;
* awkward moments: a fake monk collecting money in the street, a livestream selling "blessed" bracelets,
  an envelope pressed into your hand (it goes into the donation box and the book, never a pocket).

Nobody at the pagoda is ever asked for money, nothing is sold, no fortunes are told. The pagoda gives a
small allowance per job (no tips; a slip costs the review, never the allowance). A job is a short chain
of steps (pagoda_content.py): pick / sort / order / choose / tally. Everything random is rolled from the
day, slot or task id.
"""
from __future__ import annotations

import copy
import json

from ..jsoncopy import tree_copy
from . import kit
from .. import consequences as cq
from . import pagoda_content as pc

ID = 'pagoda'
GEN = 1

PEOPLE = pc.PEOPLE
MODS = pc.MODS
DESK = pc.DESK
SITUATIONS = pc.SITUATIONS
INTRO = pc.INTRO
REG_STORY = pc.REG_STORY
VARIANTS = pc.VARIANTS
VAR = {v['id']: v for v in VARIANTS}

KINDS = ('setup', 'yard', 'hall', 'guide', 'kitchen', 'book', 'listen', 'ceremony', 'care', 'incident')
STAGES = ('work', 'done')
STEP_TYPES = ('pick', 'sort', 'order', 'choose', 'tally')
CATS = ('cr', 'sf', 'hn', 'mn')
# What the pagoda gives for each job (xu): a modest allowance for tea, soap and bus fare. It is never cut
# for a slip (the abbot reminds you instead); the review and the stars carry the mistake.
PAY = dict(setup=0, yard=6, hall=6, guide=7, kitchen=8, book=7, listen=8, ceremony=10, care=7, incident=8)
REMIND = ('Thầy Huệ Minh: “Lần sau con để ý hơn nhé.”', 'Thầy Huệ Minh: “Sai thì sửa, con ghi nhớ là được.”',
          'Thầy Huệ Minh: “Chậm lại một chút, con sẽ thấy rõ hơn.”')
LINES_MAX = 30
TALLY_MAX = 10 ** 4


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _json(x):
    """A JSON round trip: tuples become lists, so a regenerated task compares equal to a loaded one."""
    return json.loads(json.dumps(x, ensure_ascii=False))


# ================================================================ the day plan
_PLAN_MEMO: dict = {}
DAY1 = ('y_quet', 'h_hoa', 'g_cong', 'k_trua', 'b_hom', 'l_hien', 'a_bac', 'y_canh', 'h_lau', 'i_dien')


def _eligible(kind: str, day: int, mod: str, used: set) -> list:
    out = []
    for v in VARIANTS:
        if v['kind'] != kind or v['min_day'] > day or v['id'] in used:
            continue
        mods = v['mods']
        if mods and mod not in mods and None not in mods:
            continue
        w = v['weight'] * (3 if mods and mod in mods else 1)
        out.extend([v['id']] * w)
    return out


def _day_plan(day: int) -> list:
    """What the jobs of the day are, slot 1..11: (kind, variant id). Pure from the day."""
    day = max(1, int(day))
    if day in _PLAN_MEMO:
        return _PLAN_MEMO[day]
    if day == 1:
        plan = [(VAR[v]['kind'], v) for v in DAY1]
    else:
        mod = mod_of(day)['id']
        r = kit.rng(ID, 'plan', day)
        used: set = set()
        plan = []

        def take(kind):
            pool = _eligible(kind, day, mod, used)
            if not pool:
                return
            vid = pool[r.randrange(len(pool))]
            used.add(vid)
            plan.append((kind, vid))

        take('yard')
        bag = ['hall', 'guide', 'kitchen', 'book', 'listen', 'care', 'incident', 'yard', 'hall', 'guide', 'ceremony', 'kitchen']
        bag += {'ram': ['ceremony', 'kitchen', 'care'], 'rain': ['incident', 'hall'], 'tour': ['guide', 'guide'],
                'windy': ['incident', 'yard']}.get(mod, [])
        r.shuffle(bag)
        if mod == 'ram':
            bag.remove('ceremony')
            bag.insert(0, 'ceremony')
        for kind in bag:
            if len(plan) >= 11:
                break
            take(kind)
        base = len(plan)
        while len(plan) < 11:
            plan.append(plan[len(plan) % max(1, base)])
    _PLAN_MEMO[day] = plan
    return plan


# ================================================================ steps: public part and key
def _split(raw: dict) -> tuple[dict, dict]:
    typ = raw['type']
    pub = dict(type=typ, id=raw['id'], title=raw['title'], lead=raw.get('lead', ''), when=raw.get('when'), skip=raw.get('skip', ''))
    key: dict = {}
    if typ == 'pick':
        pub.update(go=raw['go'], items=[dict(id=i['id'], emoji=i['emoji'], name=i['name'], look=i['look']) for i in raw['items']])
        key = dict(done=raw['done'], items={i['id']: dict(ok=i['ok'], why=i['why'], sev=i['sev'], cat=i['cat'], safety=i['safety'])
                                            for i in raw['items']})
    elif typ == 'sort':
        pub.update(go=raw['go'], bins=raw['bins'], items=[dict(id=i['id'], emoji=i['emoji'], name=i['name'], look=i['look']) for i in raw['items']])
        key = dict(done=raw['done'], items={i['id']: dict(right=i['right'], why=i['why'], sev=i['sev'], cat=i['cat'], wrong=i['wrong']) for i in raw['items']})
    elif typ == 'order':
        pub.update(go=raw['go'], items=[dict(id=i['id'], emoji=i['emoji'], name=i['name']) for i in raw['items']])
        key = dict(done=raw['done'], bad={i['id']: i['bad'] for i in raw['items'] if i['bad']}, rules=raw['rules'])
    elif typ == 'choose':
        pub.update(text=raw['text'], options=[dict(id=o['id'], label=o['label'], hint=o.get('hint', '')) for o in raw['options']])
        key = dict(options={o['id']: dict(q=o['q'], out=o['out'], sev=o['sev'], why=o['why'], cat=o['cat'], safety=o['safety']) for o in raw['options']})
    elif typ == 'tally':
        pub.update(who=raw['who'], bills=list(raw['bills']))
        key = dict(total=sum(raw['bills']))
    return pub, key


def _mix(raw: dict, r) -> dict:
    """Shuffle what is on screen (chores, answers, the bills on the table): the right one is never always first."""
    if raw['type'] in ('pick', 'order'):
        r.shuffle(raw['items'])
    elif raw['type'] == 'choose':
        r.shuffle(raw['options'])
    elif raw['type'] == 'tally':
        raw['bills'] = list(raw['bills'])
        r.shuffle(raw['bills'])
    return raw


def _order_of(st: dict, key: dict) -> list:
    """A right sequence for an order step (the chores that belong in it, every rule kept)."""
    left = [i['id'] for i in st['items'] if i['id'] not in key['bad']]
    rules = [(a, b) for a, b, *_ in key['rules']]
    out = []
    while left:
        x = next((x for x in left if not any(b == x and a in left for a, b in rules)), left[0])
        out.append(x)
        left.remove(x)
    return out


def _tip(st: dict, key: dict):
    """The first morning only: what thầy Huệ Minh shows you (the control that glows on a first task)."""
    if st['type'] == 'choose':
        return next((o for o, k in key['options'].items() if k['q'] == 'good'), None)
    if st['type'] == 'order':
        return _order_of(st, key)
    return None


def _schedule_step() -> dict:
    """Thời khóa sáng: the morning in its order (and no loudspeaker at four)."""
    return pc.order('kh', 'Thời khóa sáng', '🔔 Bắt đầu ngày', [
        pc.O('thuc', '⏰', 'Thức dậy lúc 4 giờ, rửa mặt'),
        pc.O('chuong', '🔔', 'Thỉnh chuông sáng, chậm và đều'),
        pc.O('congphu', '🙏', 'Công phu sáng trong chánh điện'),
        pc.O('quet', '🧹', 'Quét sân'),
        pc.O('diemtam', '🍵', 'Điểm tâm cùng mọi người'),
        pc.O('loa', '📢', 'Mở loa ra đường đọc kinh từ 4 giờ sáng',
             bad=(2, 'Loa vang ra đường từ bốn giờ sáng: cả xóm mất ngủ, trẻ nhỏ giật mình khóc.', 'mn')),
    ], [('thuc', 'chuong', 1, 'Chưa rửa mặt, chưa tỉnh đã lên gác chuông.', 'cr'),
        ('chuong', 'congphu', 1, 'Công phu trước khi thỉnh chuông: chuông là để báo giờ.', 'cr'),
        ('congphu', 'diemtam', 1, 'Điểm tâm trước giờ công phu sáng.', 'cr')],
        lead='Bấm theo thứ tự sẽ làm. Bấm lại việc cuối để bỏ.', done='Chuông sáng ngân dài, công phu xong thì trời vừa hửng.')


def _word_step(day: int) -> dict:
    """Lời thầy dặn: the abbot's word about the day (which kind of day it is)."""
    mod = mod_of(day)
    return pc.choose('dan', 'Lời thầy dặn', f'Thầy Huệ Minh dặn sau giờ điểm tâm: “Hôm nay {pc.MOD_WORD[mod["id"]]}”', [
        pc.C('ghi', 'Ghi lời thầy lên bảng ở bếp, hỏi lại chỗ chưa rõ', 'good', 'Thầy gật đầu: “Ghi ra thì cả chùa cùng nhớ.”'),
        pc.C('nho', 'Dạ, rồi nhớ trong đầu', 'ok', 'Thầy cười: “Nhớ được hết thì giỏi.”'),
        pc.C('luot', 'Vừa nghe vừa lướt điện thoại', 'bad', 'Thầy dừng lại, chờ bạn cất điện thoại.', 1, 'Thầy đang dặn việc mà cúi xem điện thoại.', 'mn'),
    ], lead='Thầy dặn ít, mà câu nào cũng có việc.')


def _raw_steps(day: int, kind: str, vid: str | None) -> list:
    if kind == 'setup':
        return [_schedule_step(), _word_step(day)]
    return [copy.deepcopy(s) for s in VAR[vid]['steps']]


# ================================================================ tasks
def make_task(day: int, slot: int, serial: int) -> dict:
    common = dict(gen=GEN, stage='work', at=0, work={}, closed=[], skipped=[], lines=[], story=None)
    mix = kit.rng(ID, 'mix', day, slot)
    if slot == 0:
        steps = [_split(_mix(r, mix)) for r in _raw_steps(day, 'setup', None)]
        mod = mod_of(day)
        needs = _json(dict(variant='setup', steps=[p for p, _ in steps], note=f'{mod["emoji"]} {mod["label"]}: {mod["hint"]}'))
        key = _json({p['id']: k for p, k in steps})
        return kit.base_task(ID, day, slot, serial, 0, 'Bắt đầu ngày ở chùa Gió Lành',
                             'Bốn giờ sáng, sương còn đọng trên hàng cau. Thầy Huệ Minh đã ngồi trong chánh điện, chờ tiếng chuông đầu ngày.',
                             kind='setup', needs=needs, _key=key, **common)
    plan = _day_plan(day)
    kind, vid = plan[(slot - 1) % len(plan)]
    v = VAR[vid]
    steps = [_split(_mix(r, mix)) for r in _raw_steps(day, kind, vid)]
    needs = _json(dict(variant=vid, steps=[p for p, _ in steps], note=v['note']))
    key = _json({p['id']: k for p, k in steps})
    return kit.base_task(ID, day, slot, serial, v['npc'], v['title'], v['opening'], kind=kind, needs=needs, _key=key, **common)


FIXED = ('needs', '_key')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the pagoda's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, jobs=0, clean=0, slips=0, earned=0, counted=0)


def initial() -> dict:
    return dict(v=1, intro=False, regulars={}, today=_fresh_today(0),
                stats=dict(jobs=0, clean=0, slips=0, safety=0, tallies=0, exact=0),
                desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'desk'):
        kit.need(isinstance(d[k], dict), 'Số liệu việc chùa sai.')
    for k in ('stats', 'today'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


# ================================================================ the actions
FREE = ('chua_intro',)
NO_TICK = ('chua_intro', 'chua_pick', 'chua_put', 'chua_seq', 'chua_desk')
PHYSICAL = ('chua_close', 'chua_choose', 'chua_tally')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'chua_intro':
        d['intro'] = True
        return dict(message='Tiếng chuông sáng vừa dứt. Vào việc thôi!')
    desk = d['desk']
    if name == 'chua_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ngoài sân, lo xong rồi làm tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Việc này không có ở chùa.')
    result = fn(s, c, d, p)
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
    return result


def _task(c: dict, p: dict) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc chùa Gió Lành.')
    return t


def _step(t: dict, typ=None) -> tuple[dict, dict]:
    """The step being worked on now (its public part and its key)."""
    kit.need(t['stage'] == 'work', 'Việc này đã xong rồi.')
    kit.need(t['known'], 'Nghe dặn việc trước đã.')
    steps = t['needs']['steps']
    kit.need(0 <= t['at'] < len(steps), 'Không còn bước nào để làm.')
    st = steps[t['at']]
    if typ:
        kit.need(st['type'] in ((typ,) if isinstance(typ, str) else typ), 'Bước này làm theo cách khác.')
    kit.start_work(t)
    return st, t['_key'].get(st['id'], {})


def _line(t: dict, text: str) -> None:
    if text:
        t['lines'] = (t['lines'] + [str(text)[:300]])[-LINES_MAX:]


def _slip(t: dict, sid: str, iid: str, sev, why: str, cat: str, safety: bool = False, note: str = '') -> bool:
    """One mistake on the job (once per code): the review and the stars follow."""
    code = f'{cat}:{sid}.{iid}'[:32]
    before = len(cq.slips(t))
    cq.slip(t, code, int(sev), why, note[:120], bool(safety))
    if len(cq.slips(t)) > before:
        t['mistakes'] += 1
        return True
    return False


def _when_ok(t: dict, when) -> bool:
    if not when:
        return True
    sid, want = when
    got = t['work'].get(sid)
    wants = want if isinstance(want, list) else [want]
    if isinstance(got, list):
        return any(w in got for w in wants)
    return got in wants


def _advance(s: dict, c: dict, d: dict, t: dict, msg: str, ok: bool = True) -> dict:
    """Close the current step and move on (skipping steps that do not happen); the last one ends the job."""
    steps = t['needs']['steps']
    t['closed'].append(steps[t['at']]['id'])
    i = t['at'] + 1
    while i < len(steps) and not _when_ok(t, steps[i].get('when')):
        t['skipped'].append(steps[i]['id'])
        _line(t, steps[i].get('skip', ''))
        i += 1
    t['at'] = i
    if i < len(steps):
        return dict(message=msg, correct=ok)
    r = _end(s, c, d, t, msg)
    if not ok:
        r['correct'] = False
    return r


def _verdict(t: dict, st: dict, key: dict, bad: list) -> str:
    if bad:
        for b in bad:
            _line(t, f'⚠️ {b}')
        return f'{st["title"]}: ' + ' '.join(bad)
    _line(t, f'✅ {key["done"]}')
    return key['done']


# ---------------------------------------------------------------- pick: tap what to do, then close
def _pick(s, c, d, p):
    t = _task(c, p)
    st, _ = _step(t, 'pick')
    iid = kit.one_of(p.get('item'), [i['id'] for i in st['items']], 'Không có việc này.')
    got = t['work'].setdefault(st['id'], [])
    if iid in got:
        got.remove(iid)
    else:
        got.append(iid)
    return dict(message='')


def _close_pick(t, st, key) -> str:
    got = t['work'].setdefault(st['id'], [])
    bad = []
    for iid, k in key['items'].items():
        on = iid in got
        if (k['ok'] is True and not on) or (k['ok'] is False and on):
            if _slip(t, st['id'], iid, k['sev'] or 1, k['why'], k['cat'], k['safety'], st['title']):
                bad.append(k['why'])
    return _verdict(t, st, key, bad)


# ---------------------------------------------------------------- sort: every item into one place, then close
def _put(s, c, d, p):
    t = _task(c, p)
    st, _ = _step(t, 'sort')
    iid = kit.one_of(p.get('item'), [i['id'] for i in st['items']], 'Không có thứ này.')
    b = kit.one_of(p.get('bin'), [x['id'] for x in st['bins']], 'Không có chỗ này.')
    t['work'].setdefault(st['id'], {})[iid] = b
    return dict(message='')


def _close_sort(t, st, key) -> str:
    got = t['work'].get(st['id'], {})
    kit.need(all(i['id'] in got for i in st['items']), 'Còn thứ chưa xếp chỗ.')
    bad = []
    for iid, k in key['items'].items():
        b = got[iid]
        if b in k['right']:
            continue
        w = k['wrong'].get(b)
        sev, why, cat, safety = (list(w) + [False])[:4] if w else (k['sev'], k['why'], k['cat'], False)
        if _slip(t, st['id'], iid, sev, why, cat, safety, st['title']):
            bad.append(why)
    return _verdict(t, st, key, bad)


# ---------------------------------------------------------------- order: tap in the order you do it (tap the last to undo)
def _seq(s, c, d, p):
    t = _task(c, p)
    st, _ = _step(t, 'order')
    iid = kit.one_of(p.get('item'), [i['id'] for i in st['items']], 'Không có việc này.')
    got = t['work'].setdefault(st['id'], [])
    if iid in got:
        kit.need(got[-1] == iid, 'Chỉ bỏ được việc vừa xếp cuối cùng.')
        got.pop()
    else:
        got.append(iid)
    return dict(message='')


def _close_order(t, st, key) -> str:
    got = t['work'].get(st['id'], [])
    need = [i['id'] for i in st['items'] if i['id'] not in key['bad']]
    # The button counts “đã xếp k/n” (n = the chores that belong, public_task 'need'); it is ready at n, so
    # the server takes the sequence at n too (live 06/10: 68 refusals “Còn việc chưa xếp”). A chore that
    # belongs but was left out for one that does not is a slip, not a refusal: no hint which one it was.
    kit.need(len(got) >= len(need), f'Còn việc chưa xếp vào thứ tự (đã xếp {len(got)}/{len(need)}).')
    bad = []
    for iid in need:
        if iid not in got:
            name = next(i['name'] for i in st['items'] if i['id'] == iid)
            if _slip(t, st['id'], 'miss.' + iid, 1, f'Quên mất việc “{name}”.', 'cr', False, st['title']):
                bad.append(f'Quên mất việc “{name}”.')
    for iid in got:
        if iid in key['bad']:
            sev, why, cat, safety = (list(key['bad'][iid]) + [False])[:4]
            if _slip(t, st['id'], iid, sev, why, cat, safety, st['title']):
                bad.append(why)
    for a, b, sev, why, cat in key['rules']:
        if a in got and b in got and got.index(a) > got.index(b):
            if _slip(t, st['id'], f'{a}>{b}', sev, why, cat, False, st['title']):
                bad.append(why)
    return _verdict(t, st, key, bad)


def _close(s, c, d, p):
    t = _task(c, p)
    st, key = _step(t, ('pick', 'sort', 'order'))
    n = len(cq.slips(t))
    msg = {'pick': _close_pick, 'sort': _close_sort, 'order': _close_order}[st['type']](t, st, key)
    return _advance(s, c, d, t, msg, len(cq.slips(t)) == n)


# ---------------------------------------------------------------- choose: one answer
def _choose(s, c, d, p):
    t = _task(c, p)
    st, key = _step(t, 'choose')
    oid = kit.one_of(p.get('option'), key['options'], 'Chọn một cách.')
    k = key['options'][oid]
    t['work'][st['id']] = oid
    _line(t, ('✅ ' if k['q'] == 'good' else '⚠️ ' if k['q'] == 'bad' else '• ') + k['out'])
    msg, ok = k['out'], True
    if k['sev']:
        ok = False
        if _slip(t, st['id'], oid, k['sev'], k['why'], k['cat'], k['safety'], st['title']):
            _line(t, f'⚠️ {k["why"]}')
            msg = f'{k["out"]} {k["why"]}'
    if k['q'] == 'good':
        c['xp'] += 2
    res = _advance(s, c, d, t, msg, ok)
    res.setdefault('celebrate', k['q'] == 'good')
    return res


# ---------------------------------------------------------------- tally: count the donation, write it in the book
def _tally(s, c, d, p):
    """Write what was counted. The money is the pagoda's: it never touches the player's wallet."""
    t = _task(c, p)
    st, key = _step(t, 'tally')
    wrote = kit.integer(p.get('amount'), 0, TALLY_MAX)
    t['work'][st['id']] = wrote
    total = key['total']
    d['stats']['tallies'] += 1
    d['today']['counted'] += 1
    if wrote == total:
        d['stats']['exact'] += 1
        c['xp'] += 3
        _line(t, f'📒 Ghi sổ công đức {wrote} xu, khớp từng tờ.')
        return _advance(s, c, d, t, f'📒 Sổ công đức ghi {wrote} xu. Đếm lại vẫn khớp từng tờ.')
    gap = abs(wrote - total)
    why = f'Ghi sổ công đức {wrote} xu, đếm lại thì là {total} xu (lệch {gap} xu).'
    _slip(t, st['id'], 'lech', 2, why, 'hn', note='Ghi sổ công đức lệch')
    _line(t, f'⚠️ {why}')
    return _advance(s, c, d, t, f'📒 Đếm lại thì là {total} xu, sổ ghi {wrote} xu. Phải gạch đi ghi lại, ký tên bên cạnh.', False)


ACTIONS = {'chua_pick': _pick, 'chua_put': _put, 'chua_seq': _seq, 'chua_close': _close, 'chua_choose': _choose, 'chua_tally': _tally}


# ---------------------------------------------------------------- the end of a job
def _end(s: dict, c: dict, d: dict, t: dict, msg: str) -> dict:
    if t['kind'] == 'setup':
        t['stage'] = 'done'
        kit.complete(s, c, t, 0, 'Giữ thời khóa sáng, nghe thầy dặn việc trong ngày.')
        return dict(message=f'{msg} 🛕 Bắt đầu một ngày ở chùa.'.strip())
    said = ''
    if cq.slips(t):
        said = REMIND[kit.rng(ID, 'remind', t['id']).randrange(len(REMIND))]
    return _finish(s, c, d, t, PAY[t['kind']], f'{msg} {said}'.strip())


def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str) -> dict:
    i = _npc_index(t)
    story = ''
    if i in REG_STORY:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        lines = REG_STORY[i]
        if r['visits'] % 3 == 0 and r['visits'] // 3 <= len(lines):
            story = lines[r['visits'] // 3 - 1]
            t['story'] = story
    t['stage'] = 'done'
    today, stats = d['today'], d['stats']
    n = len(cq.slips(t))
    today['jobs'] += 1
    stats['jobs'] += 1
    if n:
        today['slips'] += n
        stats['slips'] += n
    else:
        today['clean'] += 1
        stats['clean'] += 1
    if cq.safety(t):
        stats['safety'] += 1
    today['earned'] += max(0, int(reward))
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    msg = f'{narrative} 💬 {story}'.strip() if story else narrative
    return dict(message=msg, correct=not n, celebrate=not n)


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['today'] = _fresh_today(day)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    setup = next((t for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] == day
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if setup is None and not any(t.get('career') == ID and t['day'] == day for t in c['tasks']):
        setup = make_task(day, 0, c['turn'])
        c['tasks'].append(setup)
        on_task(s, c, setup)
    if setup:
        c['active_task'] = setup['id']
        setup['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    today = d['today']
    lines = [f'🛕 Làm {today["jobs"]} việc ở chùa: {today["clean"]} việc chu đáo trọn vẹn.']
    if today['slips']:
        lines.append(f'📝 Thầy Huệ Minh nhắc {today["slips"]} điều cần nhớ.')
    if today['counted']:
        lines.append('📒 Sổ công đức hôm nay đã ghi, cô Hạnh ký bên cạnh.')
    if today['earned']:
        lines.append(f'🍵 Chùa gửi {today["earned"]} xu chi dùng.')
    if desk_note:
        lines.append(desk_note)
    return dict(lines=lines, note='Sáng mai bốn giờ thức dậy, thỉnh chuông rồi hẵng làm.', jobs=today['jobs'], clean=today['clean'],
                earned=today['earned'])


# ================================================================ reviews
CRIT = (('cr', 'craft', 'Làm việc chu đáo', 'cẩn thận, đúng cách', 'còn sơ suất'),
        ('sf', 'safe', 'An toàn', 'để ý lửa, người già, trẻ nhỏ', 'chưa an toàn'),
        ('hn', 'honest', 'Minh bạch, ngay thẳng', 'rõ ràng từng xu, nói thật', 'chưa minh bạch'),
        ('mn', 'manner', 'Hòa nhã, lắng nghe', 'nhẹ nhàng, biết lắng nghe', 'chưa hòa nhã'))


def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 80 else 4 if p >= 60 else 3 if p >= 40 else 2
    pts = {k: 0 for k in CATS}
    for r in cq.slips(t):
        cat = r['code'].split(':', 1)[0]
        if cat in pts:
            pts[cat] += r['sev']
    if t['kind'] == 'setup':
        return dict(criteria=[dict(key='plan', label='Giữ thời khóa', score=max(2, 5 - pts['cr'] - pts['mn']), note='đúng giờ, đúng thứ tự' if not pts['cr'] else 'thứ tự chưa đúng'),
                              dict(key='word', label='Nghe thầy dặn', score=max(2, 5 - pts['mn']), note='chăm chú' if not pts['mn'] else 'còn lơ đãng')])
    crit = [dict(key=key, label=label, score=max(1, 5 - pts[cat]), note=ok if not pts[cat] else bad) for cat, key, label, ok, bad in CRIT]
    crit.append(dict(key='speed', label='Nhanh nhẹn', score=speed, note=f'mọi người chờ còn {p}% kiên nhẫn'))
    return dict(criteria=crit)


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return f'Thỉnh chuông, công phu sáng, nghe thầy dặn việc. {n["note"]}'
    return f'{t["opening"]} {n["note"]}'.strip()


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
        return v
    for st in v['needs']['steps']:
        if st['type'] == 'order':
            # How many chores belong in the sequence: the client shows “đã xếp k/n” and readies the button at n.
            st['need'] = len(st['items']) - len(t['_key'].get(st['id'], {}).get('bad') or {})
    if t['kind'] == 'setup' and t['day'] == 1:
        for st in v['needs']['steps']:
            tip = _tip(st, t['_key'].get(st['id'], {}))
            if tip:
                st['tip'] = tip
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    return dict(intro=d['intro'], mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']), today=d['today'],
                stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()}, desk=kit.desk_public(d['desk'], DESK, ID))


def content() -> dict:
    return dict(intro=INTRO, notebook=[dict(emoji=e, who=w, text=x) for e, w, x in pc.NOTEBOOK], kinds=pc.KIND_LABEL, kind_emoji=pc.KIND_EMOJI,
                pay=PAY, pay_note=pc.PAY_NOTE, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    if k == 'setup':
        return 'Thức dậy → thỉnh chuông → công phu → rồi mới điểm tâm. Loa không mở ra đường lúc sáng sớm.'
    if k == 'book':
        return 'Hai người cùng mở hòm, đếm từng tờ, cộng lại rồi ghi đúng số. Không làm tròn, không ghi khống.'
    if k == 'kitchen':
        return 'Bếp chay: thứ gì từ thịt cá (mắm cá, hạt nêm gà, mỡ heo) thì thay hoặc để riêng. Nhớ người dị ứng.'
    return 'Mở Bảng nội quy: thời khóa, hương đèn, trang phục, bếp chay, công đức. Làm từng bước, nhẹ nhàng với mọi người.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'yard':
        return 'Đã quét lá, tưới hàng cau, vớt lá úa trên hồ sen.'
    if e.get('role') == 'kitchen':
        return 'Đã nhặt rau, ngâm nấm, nấu sẵn nồi nước dùng chay.'
    return None


# ================================================================ saves
def _vwork(st: dict, v) -> None:
    typ = st['type']
    ids = [i['id'] for i in st.get('items', [])]
    if typ in ('pick', 'order'):
        kit.need(isinstance(v, list) and len(v) == len(set(v)) and all(x in ids for x in v), 'Bước việc chùa sai.')
    elif typ == 'sort':
        bins = [b['id'] for b in st['bins']]
        kit.need(isinstance(v, dict) and all(k in ids and x in bins for k, x in v.items()), 'Bước việc chùa sai.')
    elif typ == 'choose':
        kit.need(v in [o['id'] for o in st['options']], 'Bước việc chùa sai.')
    else:
        kit.integer(v, 0, TALLY_MAX)


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc chùa không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc chùa sai.')
    steps = t['needs']['steps']
    kit.need(all(st.get('type') in STEP_TYPES for st in steps), 'Bước việc chùa sai.')
    by = {st['id']: st for st in steps}
    kit.integer(t.get('at'), 0, len(steps))
    kit.need(isinstance(t.get('work'), dict) and set(t['work']) <= set(by), 'Việc chùa sai.')
    for sid, v in t['work'].items():
        _vwork(by[sid], v)
    for k in ('closed', 'skipped'):
        v = t.get(k)
        kit.need(isinstance(v, list) and len(v) == len(set(v)) and set(v) <= set(by), 'Việc chùa sai.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= LINES_MAX and all(isinstance(x, str) and len(x) <= 300 for x in t['lines']), 'Nhật ký việc chùa sai.')
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện người quen ở chùa sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    kit.need(type(d['intro']) is bool, 'Dữ liệu việc chùa sai.')
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ người quen ở chùa sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người quen ở chùa sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu việc chùa sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='chua_', category='service',
    meta=dict(short='Thầy ở chùa', place='Chùa Gió Lành', tagline='Sân sạch, hương đèn an toàn, sổ công đức rõ từng xu.', icon='bell',
              color='#a8641f', light='#fbf1e0', weather='Gió sông mát, lá bàng rơi đầy sân', work='Việc chùa', station='Sân chùa & chánh điện',
              greeting='Thỉnh chuông, công phu sáng rồi vào việc. Thời khóa, hương đèn, bếp chay, công đức: xem Bảng nội quy nhé.',
              caption='Tiếng chuông trầm bên bến sông', map_label='CHÙA GIÓ LÀNH'),
    people=PEOPLE,
    staff=[('Hai', 'yard', 'Phật tử về hưu, sáng nào cũng lên quét sân.', 78, 86),
           ('Nguyệt', 'kitchen', 'Phụ bà Nhạn trong bếp chay đã mười năm.', 82, 84),
           ('Tâm', 'yard', 'Sinh viên làm công quả cuối tuần, khỏe và nhanh.', 88, 72),
           ('Thanh', 'kitchen', 'Nấu chay khéo, thuộc ai dị ứng gì.', 74, 92)],
    roles={'yard': 'Sân vườn', 'kitchen': 'Bếp chay'},
    tip=0,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('🔔', 'Bảng nội quy', [('4:00', 'Thức chúng, thỉnh chuông'), ('11:00', 'Cúng ngọ, thọ trai'), ('Hương', 'Thắp ở lư ngoài sân'),
                                     ('Công đức', 'Đếm trước mặt, ghi đúng từng xu')],
              ['Thời khóa sáng', 'Quét sân, chăm hồ sen', 'Hương đèn, đón khách', 'Bếp chay, sổ công đức, lắng nghe']),
    stories=[('Quả chuông có vết lõm', ('Quả chuông đồng do cả làng góp đúc, năm bão bị cành đa quật lõm một góc.',
                                        'Thầy Huệ Minh dạy bạn thỉnh chuông: chậm, đều, chờ tiếng ngân tắt hẳn mới đánh tiếng sau.',
                                        'Sáng nay ông Bảy Đò đứng dưới bến nghe chuông, bảo tiếng chuông của bạn trầm y như ngày xưa.')),
             ('Cái giếng sau chùa', ('Giếng sau chùa có từ thời ông bà, nước trong và mát.',
                                     'Bạn cùng anh Toàn thay dây gàu, dọn rêu quanh thành giếng.',
                                     'Bà Nhạn bảo nấu canh bằng nước giếng này thì ngọt hơn hẳn.')),
             ('Mười hai con cá đỏ', ('Hồ sen có mười hai con cá đỏ, bé Na thuộc từng con.',
                                     'Bé Na đặt tên cho từng con, viết vào một tờ giấy dán cạnh hồ.',
                                     'Hôm đi thi về, bé Na chạy lên khoe: bài văn “Ngôi chùa quê em” được điểm mười.'))],
    review_asides=['Sân chùa sạch sẽ, mát mẻ.', 'Thầy nói năng nhẹ nhàng, dễ gần.', 'Sổ công đức rõ ràng từng xu.',
                   'Cơm chay ngon, đúng là chay.'],
    situations=SITUATIONS,
    more_line='Thầy Huệ Minh nhờ thêm một việc.',
    open_line='Cổng chùa đã mở. Khách thập phương đang lên, mình đón từng người nhé.',
    guide='Sáng: thức dậy, thỉnh chuông, công phu rồi mới điểm tâm. Mỗi việc: nghe dặn → làm từng bước (chọn, xếp, sắp thứ tự, quyết định, đếm tiền công đức). Hương đèn, trang phục, bếp chay, công đức: xem Bảng nội quy.',
)
