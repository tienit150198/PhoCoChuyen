"""Nội trợ nhà chị Thảo: a home helper's day in a three-generation family (plugin career).

The player helps out by the hour in chị Thảo's house in ngõ Hoa Sữa: bà Lành (76, high blood pressure
and diabetes), anh Dũng (spicy food, a bad stomach), bé Su (7, allergic to shrimp) and bé Cốm (18 months).
What the job is:

* in the morning (``setup`` task) take the market money (count it in front of chị Thảo) and put the
  day's chores in a sensible order (washing machine before the market, market before cooking…);
* a market trip (``market``): read chị Thảo's list, then go — at the stall the list is gone from view
  (call her to hear it again, which she does not love in a meeting). Pick the fresh goods and not the
  shiny sprayed greens or the dull-eyed fish, haggle (each seller decides from hidden traits), weigh it
  again at the market's own scale, and write the market book: what was really spent, the change back.
  Writing more than was spent puts the difference in your pocket — sometimes chị Thảo notices at once,
  sometimes days later (an audit trouble);
* cooking for each person (allergies, salt, sugar, bones, a toddler's porridge), washing up, laundry
  sorted by colour (and what is in the pockets), cleaning room by room with the right cleaner (never
  two cleaners mixed), bà's pills at the right time, picking up bé Su (only to the people on the list),
  the fridge, the plants, incidents (power cut, burnt rice, a blocked sink, guests out of nowhere, a pan
  on fire, a gas smell) and the Tết clean-up;
* awkward people all day: the camera call, the nosy neighbour, the unpaid extra house, the leftovers for
  the helper, the missing money, the husband who asks you to lie, the bag check… and chị Thảo paying
  late (wait, or ask politely; a debt book to chase).

A job is a short chain of steps (homemaker_content.py): pick / sort / order / choose / haggle / receipt.
The public step goes to the client in ``needs``; the verdicts stay in ``_key``. Mistakes go through
consequences (cq.slip); money only through the engine's money(). Everything random is rolled from the
day, slot or task id.
"""
from __future__ import annotations

import copy
import json

from ..jsoncopy import tree_copy
from . import kit
from . import street_folk as folk
from .. import consequences as cq
from . import homemaker_content as hc

ID = 'homemaker'
GEN = 1

PEOPLE = hc.PEOPLE
MODS = hc.MODS
DESK = hc.DESK
SITUATIONS = hc.SITUATIONS
INTRO = hc.INTRO
REG_STORY = hc.REG_STORY
VARIANTS = hc.VARIANTS
VAR = {v['id']: v for v in VARIANTS}

KINDS = ('setup', 'market', 'cook', 'dishes', 'laundry', 'clean', 'elder', 'kids', 'fridge', 'garden', 'incident', 'tet')
STAGES = ('work', 'late', 'done')
STEP_TYPES = ('pick', 'sort', 'order', 'choose', 'haggle', 'receipt')
CATS = ('cr', 'sf', 'hn', 'mn')
# What the family pays for each job (xu). The rubbish round pays 14 a stop and a drain call 12–45:
# a house job is half an hour to an hour of careful work.
PAY = dict(setup=0, market=18, cook=22, dishes=12, laundry=16, clean=16, elder=18, kids=16, fridge=12, garden=10, incident=20, tet=30)
# What chị Thảo takes back when a job went wrong (consequences.decide → kind); a family never walks out.
CUT = dict(accept=0, grumble=0, discount=25, refund=50, walkout=50, refuse=100, remake=0)
REACT = dict(
    grumble=('“Lần sau để ý giúp chị nhé.”', '“Thôi được, nhưng chị không vui đâu.”'),
    discount=('“Việc này chị trừ một ít công nhé, sai thế là phải chịu.”', '“Chị bớt chút công, coi như nhắc em.”'),
    refund=('“Việc này chị chỉ tính nửa công thôi.”', '“Làm thế này chị chỉ trả được một nửa.”'),
    refuse=('“Chuyện này không đùa được. Việc này chị không tính công.”', '“Suýt nữa thì có chuyện. Hôm nay việc này chị không trả.”'),
)
LINES_MAX = 30
HAGGLE_HIGH = 115        # buying above this % of the fair price is overpaying
LATE_RATE = 12           # % of jobs (day 3+) where chị Thảo pays later
AUDIT_DAYS = (1, 3)      # an unnoticed padded market book comes up again 1..3 days later


# ================================================================ small helpers
def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _persona(i: int) -> str | None:
    return PEOPLE[i][3] if 0 <= i < len(PEOPLE) else None


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s else s


def _json(x):
    """A JSON round trip: tuples become lists, so a regenerated task compares equal to a loaded one."""
    return json.loads(json.dumps(x, ensure_ascii=False))


# ================================================================ the day plan
_PLAN_MEMO: dict = {}
DAY1 = ('m_canh', 'c_trua', 'd_trua', 'l_ca_nha', 'k_khach', 't_don', 'e_thuoc', 'f_cat', 'g_tuoi')


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

        take('market')
        take('cook')
        bag = ['dishes', 'laundry', 'clean', 'elder', 'kids', 'fridge', 'garden', 'incident', 'laundry', 'clean', 'kids', 'incident']
        bag += {'tet': ['tet', 'tet'], 'rain': ['incident', 'laundry'], 'guests': ['cook', 'dishes', 'incident'], 'sick': ['elder', 'cook']}.get(mod, [])
        r.shuffle(bag)
        if mod == 'tet':
            bag.remove('tet')
            bag.insert(0, 'tet')
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
        pub.update(go=raw['go'], items=[dict(id=i['id'], emoji=i['emoji'], name=i['name'], look=i['look'], price=i['price']) for i in raw['items']])
        key = dict(done=raw['done'], items={i['id']: dict(ok=i['ok'], why=i['why'], sev=i['sev'], cat=i['cat'], safety=i['safety'], say=i['say'])
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
    elif typ == 'haggle':
        pub.update(seller=raw['seller'], goods=raw['goods'], quote=raw['quote'])
        key = dict(fair=raw['fair'])
    return pub, key


def _mix(raw: dict, r) -> dict:
    """Shuffle what is on screen (goods, chores, answers): the right one is never always first."""
    if raw['type'] in ('pick', 'order'):
        r.shuffle(raw['items'])
    elif raw['type'] == 'choose':
        r.shuffle(raw['options'])
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
    """The first morning only: what chị Thảo shows you (the control that glows on a first task)."""
    if st['type'] == 'choose':
        return next((o for o, k in key['options'].items() if k['q'] == 'good'), None)
    if st['type'] == 'order':
        return _order_of(st, key)
    return None


def _cash_step(day: int) -> dict:
    """Nhận tiền chợ: count it in front of chị Thảo (sometimes she is ten short)."""
    r = kit.rng(ID, 'cash', day)
    total, bills = hc.CASH_LINES[r.randrange(len(hc.CASH_LINES))]
    short = day >= 2 and r.random() < 0.35
    if short:
        bills = list(bills)
        bills.remove(10)
    got = sum(bills)
    text = f'Chị Thảo dúi vào tay bạn xấp tiền chợ: “{total} xu nhé em, chị muộn làm rồi.” Một xấp {len(bills)} tờ gấp đôi.'
    if short:
        opts = [hc.C('count', 'Đếm lại ngay trước mặt chị', 'good', f'Đếm ra chỉ có {got} xu. Chị Thảo đếm lại: “À chị nhầm”, đưa thêm 10 xu.'),
                hc.C('msg', f'Cất ví riêng, nhắn tin “Em nhận {total} xu tiền chợ”', 'ok', 'Tối đếm lại thì thiếu 10 xu.', 1,
                     'Nhắn là nhận đủ mà tối đếm lại thiếu mười xu, chẳng biết thiếu từ đâu.'),
                hc.C('pocket', 'Nhét túi quần, chị đang vội', 'bad', 'Tiền chợ lẫn với tiền riêng.', 1, 'Tiền chợ thiếu mười xu, không ai biết thiếu từ lúc nào.')]
    else:
        opts = [hc.C('count', 'Đếm lại ngay trước mặt chị', 'good', f'Đủ {total} xu. Chị Thảo gật đầu: “Cẩn thận thế là tốt.”'),
                hc.C('msg', f'Cất ví riêng, nhắn tin “Em nhận {total} xu tiền chợ”', 'good', 'Chị Thảo thả tim tin nhắn.'),
                hc.C('pocket', 'Nhét túi quần, chị đang vội', 'ok', 'Tiền chợ lẫn với tiền riêng.', 1, 'Tiền chợ để lẫn tiền riêng, ghi sổ lộn xộn.')]
    return hc.choose('tien', 'Nhận tiền chợ', text, opts, lead='Tiền chợ là tiền của nhà chủ.')


def _plan_step(day: int) -> dict:
    """Xếp việc trong ngày: the morning's chores in a sensible order."""
    kinds = []
    for kind, _ in _day_plan(day)[:4]:
        if kind in hc.PLAN_ITEM and kind not in kinds:
            kinds.append(kind)
    for extra in ('laundry', 'elder', 'garden'):
        if len(kinds) >= 4:
            break
        if extra not in kinds:
            kinds.append(extra)
    items = [hc.O(k, *hc.PLAN_ITEM[k]) for k in kinds]
    rules = [(a, b, sev, why, 'cr') for a, b, sev, why in hc.PLAN_RULES if a in kinds and b in kinds]
    return hc.order('ke', 'Xếp việc trong ngày', '📋 Bắt đầu ngày', items, rules,
                    lead='Bấm theo thứ tự sẽ làm. Bấm lại việc cuối để bỏ.', done='Việc nào trước việc nào sau, đâu ra đấy.')


def _rice_kind(day: int, slot: int) -> str:
    return ('moi', 'cu', 'thuong')[kit.rng(ID, 'rice', day, slot).randrange(3)]


def _raw_steps(day: int, slot: int, kind: str, vid: str | None) -> list:
    if kind == 'setup':
        return [_cash_step(day), _plan_step(day)]
    return [hc._rice(_rice_kind(day, slot)) if s == 'RICE' else copy.deepcopy(s) for s in VAR[vid]['steps']]


# ================================================================ tasks
def make_task(day: int, slot: int, serial: int) -> dict:
    common = dict(gen=GEN, stage='work', at=0, work={}, closed=[], skipped=[], lines=[], spent=0, out=False, calls=0, bid=None, story=None)
    mix = kit.rng(ID, 'mix', day, slot)
    if slot == 0:
        steps = [_split(_mix(r, mix)) for r in _raw_steps(day, 0, 'setup', None)]
        mod = mod_of(day)
        needs = _json(dict(variant='setup', steps=[p for p, _ in steps], shop=None, budget=0,
                           note=f'{mod["emoji"]} {mod["label"]}: {mod["hint"]}'))
        key = _json({p['id']: k for p, k in steps})
        return kit.base_task(ID, day, slot, serial, 0, 'Bắt đầu ngày ở nhà chị Thảo',
                             'Chị Thảo vừa xỏ giày vừa dặn: “Tiền chợ đây em. Hôm nay nhiều việc, em xếp xem làm gì trước nhé.”',
                             kind='setup', needs=needs, _key=key, **common)
    plan = _day_plan(day)
    kind, vid = plan[(slot - 1) % len(plan)]
    v = VAR[vid]
    steps = [_split(_mix(r, mix)) for r in _raw_steps(day, slot, kind, vid)]
    needs = _json(dict(variant=vid, steps=[p for p, _ in steps], shop=v['shop'] or None, budget=v['budget'], note=v['note']))
    key = _json({p['id']: k for p, k in steps})
    return kit.base_task(ID, day, slot, serial, v['npc'], v['title'], v['opening'], kind=kind, needs=needs, _key=key, **common)


FIXED = ('needs', '_key')


def twist_of(t: dict) -> dict | None:
    """chị Thảo pays this job later (a pure function of the job: the validator checks a stored twist against it)."""
    if t.get('kind') in (None, 'setup') or t.get('day', 1) < 3:
        return None
    if folk.roll('nt-late', t['id']) >= LATE_RATE:
        return None
    return dict(kind='late', n=folk.roll('nt-late-n', t['id']) % len(hc.LATE_LINES))


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'
    tw = twist_of(t)
    if tw:
        t['twist'], t['tw'] = tw, dict(state='wait', choice=None)


# ================================================================ the house's data
def _fresh_today(day: int) -> dict:
    return dict(day=day, jobs=0, clean=0, slips=0, earned=0, pocket=0, market=0)


def initial() -> dict:
    return dict(v=1, intro=False, regulars={}, today=_fresh_today(0),
                stats=dict(jobs=0, clean=0, slips=0, safety=0, honest=0, pocket=0, caught=0, haggled=0, overpaid=0, calls=0),
                desk=kit.desk_initial(), debts=[], audits=[], trouble=folk.trouble_initial())


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'desk', 'trouble'):
        kit.need(isinstance(d[k], dict), 'Số liệu việc nhà sai.')
    for k in ('stats', 'today'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    for k, v in folk.trouble_initial().items():
        d['trouble'].setdefault(k, copy.deepcopy(v))
    return d


# ================================================================ the actions
FREE = ('nt_intro', 'nt_chase')
NO_TICK = ('nt_intro', 'nt_pick', 'nt_put', 'nt_seq', 'nt_call', 'nt_offer', 'nt_desk', 'nt_late', 'nt_chase', 'nt_trouble')
PHYSICAL = ('nt_close', 'nt_choose', 'nt_buy', 'nt_out')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'nt_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Chị Thảo đang chờ ở cửa.')
    desk = d['desk']
    if name == 'nt_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    if name in ('nt_chase', 'nt_trouble'):
        return ACTIONS[name](s, c, d, p)
    kit.desk_block(desk, 'Có chuyện trong nhà, quyết xong rồi làm tiếp nhé.')
    kit.need(d['trouble']['ev'] is None, 'Chị Thảo đang hỏi chuyện sổ chợ: trả lời trước đã.', 'surprise_open')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở nhà chị Thảo.')
    result = fn(s, c, d, p)
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True
    if _audit_open(s, c, d):
        result['message'] = f'{result.get("message", "")} 🔔 Chị Thảo muốn hỏi lại chuyện sổ chợ.'.strip()
        result['surprise'] = True
    return result


def _task(c: dict, p: dict) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc nhà chị Thảo.')
    return t


def _step(t: dict, typ=None) -> tuple[dict, dict]:
    """The step being worked on now (its public part and its key)."""
    kit.need(t['stage'] == 'work', 'Việc này đã xong phần làm rồi.' if t['stage'] == 'done' else 'Chị Thảo đang nói chuyện tiền công với bạn.')
    kit.need(t['known'], 'Nghe dặn việc trước đã.')
    steps = t['needs']['steps']
    kit.need(0 <= t['at'] < len(steps), 'Không còn bước nào để làm.')
    st = steps[t['at']]
    if typ:
        kit.need(st['type'] in ((typ,) if isinstance(typ, str) else typ), 'Bước này làm theo cách khác.')
    if t['kind'] == 'market':
        kit.need(t['out'], 'Đọc danh sách rồi bấm “Ra chợ” đã.')
    kit.start_work(t)
    return st, t['_key'].get(st['id'], {})


def _line(t: dict, text: str) -> None:
    if text:
        t['lines'] = (t['lines'] + [str(text)[:300]])[-LINES_MAX:]


def _slip(t: dict, sid: str, iid: str, sev, why: str, cat: str, safety: bool = False, note: str = '') -> bool:
    """One mistake on the job (once per code): the review, the stars, the pay and the patience follow."""
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


# ---------------------------------------------------------------- the market: the list, then out the door
def _out(s, c, d, p):
    t = _task(c, p)
    kit.need(t['known'], 'Nghe dặn việc trước đã.')
    kit.need(t['kind'] == 'market', 'Việc này không phải đi chợ.')
    kit.need(not t['out'], 'Đang ở chợ rồi.')
    kit.start_work(t)
    t['out'] = True
    d['today']['market'] += 1
    return dict(message='🛵 Ra chợ Mây. Danh sách nằm trong đầu bạn rồi nhé.')


def _call(s, c, d, p):
    t = _task(c, p)
    kit.need(t['kind'] == 'market' and t['out'] and t['stage'] == 'work', 'Chưa ra chợ mà.')
    kit.need(t['calls'] == 0, 'Danh sách đang hiện rồi.')
    t['calls'] = 1
    d['stats']['calls'] += 1
    t['patience'] = max(25, t.get('patience', 100) - 5)
    tr = folk.traits(f'{t["id"]}-call', 'picky')
    if tr['mood'] < 50:
        _slip(t, 'list', 'call', 1, 'Đang họp mà gọi hỏi lại danh sách đi chợ.', 'mn', note='Gọi hỏi lại danh sách')
        return dict(message='📞 Chị Thảo thì thầm: “Chị đang họp! Đây, chị nhắn lại danh sách.”', correct=False)
    return dict(message='📞 Chị Thảo: “Đây, chị nhắn lại danh sách cho em. Nhớ chọn đồ tươi nhé.”')


# ---------------------------------------------------------------- pick: tap what to take, then close
def _pick(s, c, d, p):
    t = _task(c, p)
    st, _ = _step(t, 'pick')
    iid = kit.one_of(p.get('item'), [i['id'] for i in st['items']], 'Không có thứ này.')
    got = t['work'].setdefault(st['id'], [])
    if iid in got:
        got.remove(iid)
    else:
        got.append(iid)
    return dict(message='')


def _close_pick(s, c, d, t, st, key) -> str:
    got = t['work'].setdefault(st['id'], [])
    names = {i['id']: i for i in st['items']}
    bad = []
    for iid, k in key['items'].items():
        on = iid in got
        if (k['ok'] is True and not on) or (k['ok'] is False and on):
            if _slip(t, st['id'], iid, k['sev'] or 1, k['why'], k['cat'], k['safety'], st['title']):
                bad.append(k['why'])
        if on and k['say']:
            _line(t, k['say'])
    spent = sum(names[i]['price'] for i in got)
    if spent:
        t['spent'] += spent
        _line(t, f'🧾 {st["title"]}: {spent} xu.')
    if bad:
        for b in bad:
            _line(t, f'⚠️ {b}')
        return f'{st["title"]}: ' + ' '.join(bad)
    _line(t, f'✅ {key["done"]}')
    return key['done']


# ---------------------------------------------------------------- sort: every item into one bin, then close
def _put(s, c, d, p):
    t = _task(c, p)
    st, _ = _step(t, 'sort')
    iid = kit.one_of(p.get('item'), [i['id'] for i in st['items']], 'Không có món này.')
    b = kit.one_of(p.get('bin'), [x['id'] for x in st['bins']], 'Không có chỗ này.')
    t['work'].setdefault(st['id'], {})[iid] = b
    return dict(message='')


def _close_sort(s, c, d, t, st, key) -> str:
    got = t['work'].get(st['id'], {})
    kit.need(all(i['id'] in got for i in st['items']), 'Còn món chưa xếp chỗ.')
    bad = []
    for iid, k in key['items'].items():
        b = got[iid]
        if b in k['right']:
            continue
        w = k['wrong'].get(b)
        sev, why, cat, safety = (w + [False])[:4] if w else (k['sev'], k['why'], k['cat'], False)
        if _slip(t, st['id'], iid, sev, why, cat, safety, st['title']):
            bad.append(why)
    if bad:
        for b in bad:
            _line(t, f'⚠️ {b}')
        return f'{st["title"]}: ' + ' '.join(bad)
    _line(t, f'✅ {key["done"]}')
    return key['done']


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


def _close_order(s, c, d, t, st, key) -> str:
    got = t['work'].get(st['id'], [])
    need = [i['id'] for i in st['items'] if i['id'] not in key['bad']]
    kit.need(all(i in got for i in need), 'Còn việc chưa xếp vào thứ tự.')
    bad = []
    for iid in got:
        if iid in key['bad']:
            sev, why, cat, safety = (key['bad'][iid] + [False])[:4]
            if _slip(t, st['id'], iid, sev, why, cat, safety, st['title']):
                bad.append(why)
    for a, b, sev, why, cat in key['rules']:
        if a in got and b in got and got.index(a) > got.index(b):
            if _slip(t, st['id'], f'{a}>{b}', sev, why, cat, False, st['title']):
                bad.append(why)
    if bad:
        for b in bad:
            _line(t, f'⚠️ {b}')
        return f'{st["title"]}: ' + ' '.join(bad)
    _line(t, f'✅ {key["done"]}')
    return key['done']


def _close(s, c, d, p):
    t = _task(c, p)
    st, key = _step(t, ('pick', 'sort', 'order'))
    n = len(cq.slips(t))
    msg = {'pick': _close_pick, 'sort': _close_sort, 'order': _close_order}[st['type']](s, c, d, t, st, key)
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


# ---------------------------------------------------------------- haggle: buy at the price, or name your own
def _seller_tr(t: dict, st: dict) -> dict:
    return folk.traits(f'{t["id"]}-{st["id"]}', _persona(st['seller']))


def _bid(t: dict, st: dict) -> dict:
    if not isinstance(t.get('bid'), dict):
        t['bid'] = dict(tries=0, ask=st['quote'], firm=False)
    return t['bid']


def _offer(s, c, d, p):
    t = _task(c, p)
    st, key = _step(t, 'haggle')
    b = _bid(t, st)
    who = PEOPLE[st['seller']][0]
    kit.need(not b['firm'], f'{who} không bớt nữa đâu. Mua hay thôi?')
    price = kit.integer(p.get('price'), 1, max(1, b['ask'] - 1))
    fair = key['fair']
    tr = _seller_tr(t, st)
    floor = fair * (92 + tr['stingy'] // 8) // 100
    b['tries'] += 1
    if price >= floor:
        d['stats']['haggled'] += 1
        return _bought(s, c, d, t, st, key, price, f'{who}: “Thôi được, lấy đi cho nhanh.”')
    if b['tries'] >= 3 or price * 100 < fair * 70:
        b['firm'] = True
        rude = ' Trả thế thì về chợ khác mà mua!' if tr['rude'] > 60 and price * 100 < fair * 70 else ''
        return dict(message=f'{who}: “{b["ask"]} xu là thấp nhất rồi, không bớt được nữa.{rude}”')
    counter = max(floor, min(b['ask'] - 1, (b['ask'] + price + 1) // 2))
    b['ask'] = counter
    return dict(message=f'{who}: “Thôi, {counter} xu, không hơn được đâu.”')


def _buy(s, c, d, p):
    t = _task(c, p)
    st, key = _step(t, 'haggle')
    b = _bid(t, st)
    return _bought(s, c, d, t, st, key, b['ask'], '')


def _bought(s, c, d, t, st, key, price: int, said: str) -> dict:
    fair = key['fair']
    t['work'][st['id']] = price
    t['spent'] += price
    t['bid'] = None
    msg = f'{said} Mua {_lower(st["goods"])} giá {price} xu.'.strip()
    _line(t, f'🧾 {st["goods"]}: {price} xu.')
    if price * 100 > fair * HAGGLE_HIGH:
        d['stats']['overpaid'] += 1
        why = f'{st["goods"]} chợ bán {fair} xu mà mua những {price} xu.'
        _slip(t, st['id'], 'dat', 1, why, 'cr', note='Mua đắt')
        _line(t, f'⚠️ {why}')
        msg += ' Hơi đắt so với giá chợ.'
    elif price <= fair:
        _line(t, '👍 Giá đúng giá chợ.')
    return _advance(s, c, d, t, msg, price * 100 <= fair * HAGGLE_HIGH)


# ---------------------------------------------------------------- receipt: the market book
def _receipt(s, c, d, p):
    t = _task(c, p)
    st, _ = _step(t, 'receipt')
    budget = t['needs']['budget']
    real = t['spent']
    wrote = kit.integer(p.get('amount'), 0, budget)
    t['work'][st['id']] = wrote
    back = budget - wrote
    if wrote == real:
        d['stats']['honest'] += 1
        _line(t, f'📒 Ghi sổ {wrote} xu, trả lại {back} xu tiền thừa. Khớp từng xu.')
        c['xp'] += 3
        return _advance(s, c, d, t, f'📒 Sổ chợ khớp từng xu: tiêu {wrote} xu, trả lại {back} xu.')
    if wrote < real:
        gap = real - wrote
        take = min(gap, c['money'])
        if take:
            kit.money(s, c, -take, 'Ghi thiếu sổ chợ, tự bù tiền túi', t['id'], 'event_cost')
        why = f'Ghi sổ thiếu {gap} xu, phải tự bù tiền túi.'
        _slip(t, st['id'], 'thieu', 1, why, 'cr', note='Ghi sổ sai')
        _line(t, f'⚠️ {why}')
        return _advance(s, c, d, t, f'📒 Ghi {wrote} xu nhưng thật ra đã tiêu {real} xu: bạn tự bù {take} xu.', False)
    diff = wrote - real
    tr = folk.traits(f'{t["id"]}-so', 'picky')
    if tr['savvy'] >= 60 or diff * 100 >= max(1, real) * 30:
        d['stats']['caught'] += 1
        why = f'Ghi khống sổ chợ {diff} xu, chị Thảo cộng lại thấy ngay.'
        _slip(t, st['id'], 'khong', 3, why, 'hn', note='Ghi khống tiền chợ')
        _line(t, f'⚠️ {why}')
        return _advance(s, c, d, t, f'📒 Chị Thảo cộng lại hóa đơn: “Sao lại {wrote} xu? Chị hỏi giá rồi, chỉ {real} xu thôi.” Bạn phải trả lại {diff} xu.', False)
    kit.money(s, c, diff, 'Tiền chợ ghi khống', t['id'], 'event_income')
    d['stats']['pocket'] += diff
    d['today']['pocket'] += diff
    due = c['day'] + AUDIT_DAYS[0] + folk.roll('nt-audit', t['id']) % (AUDIT_DAYS[1] - AUDIT_DAYS[0] + 1)
    d['audits'] = (d['audits'] + [dict(id=f'au-{t["id"]}'[:60], task=t['id'], due=due, diff=diff, state='wait')])[-8:]
    _line(t, f'📒 Ghi sổ {wrote} xu, trả lại {back} xu.')
    return _advance(s, c, d, t, f'📒 Ghi sổ {wrote} xu, trả lại chị Thảo {back} xu. Chị Thảo cất sổ, không nói gì.')


# ---------------------------------------------------------------- the end of a job: pay, and sometimes later
def _end(s: dict, c: dict, d: dict, t: dict, msg: str) -> dict:
    if t['kind'] == 'setup':
        t['stage'] = 'done'
        kit.complete(s, c, t, 0, 'Nhận tiền chợ, xếp việc trong ngày.')
        return dict(message=f'{msg} 🏠 Bắt tay vào việc thôi!'.strip())
    tw = t.get('twist')
    pay, said = _settle(c, t)
    if isinstance(tw, dict) and t['tw']['state'] == 'wait' and pay > 0:
        t['tw']['state'] = 'on'
        t['stage'] = 'late'
        line = hc.LATE_LINES[tw['n']]
        return dict(message=f'{msg} 💸 Chị Thảo: {line}'.strip(), surprise=True)
    return _finish(s, c, d, t, pay, f'{msg} {said}'.strip())


def _settle(c: dict, t: dict) -> tuple[int, str]:
    """How the family takes the job (decided once from the slips) and what it pays."""
    price = PAY[t['kind']]
    old = t.get('reaction')
    if isinstance(old, dict):
        return max(0, price - old['cut']), ''
    kind = cq.decide(c, t) if cq.slips(t) else 'accept'
    if kind == 'remake':
        kind = 'discount'
    cut = price * CUT[kind] // 100
    rows = REACT.get('refund' if kind == 'walkout' else kind)
    line = rows[folk.roll('nt-react', t['id']) % len(rows)] if rows else ''
    t['reaction'] = dict(kind=kind, cut=cut, line=line, day=c['day'])
    said = f'Chị Thảo: {line}' if line else ''
    if cut:
        said += f' (−{cut} xu)'
    return price - cut, said


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


def _late(s, c, d, p):
    """chị Thảo pays later: say it is fine (a line in the debt book), or ask politely for it now."""
    t = _task(c, p)
    kit.need(t['stage'] == 'late' and t['tw']['state'] == 'on', 'Chị Thảo trả công rồi mà.')
    choice = kit.one_of(p.get('choice'), ('ok', 'ask'), 'Chọn cách trả lời.')
    t['tw'].update(state='done', choice=choice)
    pay, said = _settle(c, t)
    tr = folk.traits(f'{t["id"]}-late', 'picky')
    if choice == 'ask' and tr['budget'] + tr['honest'] >= 100:
        return _finish(s, c, d, t, pay, f'🙏 Bạn nhẹ nhàng xin công hôm nay. Chị Thảo: “Ừ nhỉ, chị chuyển khoản luôn.” {said}'.strip())
    now = pay // 2 if choice == 'ask' else 0
    rest = pay - now
    full = len(folk.open_debts(d['debts'])) >= folk.DEBT_MAX
    if rest and full:
        now, rest = pay, 0
    if rest:
        d['debts'] = folk.trim_debts(d['debts'] + [folk.debt_line(f'late-{t["id"]}', 0, 'Chị Thảo', t['id'], c['day'], rest, t['title'])])
    head = (f'🙏 Bạn xin công hôm nay. Chị Thảo đưa trước {now} xu: “Còn lại cuối tuần nhé.”' if choice == 'ask'
            else f'📒 “Dạ vâng, chị gửi sau cũng được.” Sổ nợ ghi {rest} xu.')
    return _finish(s, c, d, t, now, f'{head} {said}'.strip())


def _chase(s, c, d, p):
    """Ask chị Thảo (or bà, or anh Dũng) for the money owed, in the house's own words."""
    x = next((r for r in d['debts'] if r['id'] == p.get('debt')), None)
    kit.need(x and x['state'] == 'open', 'Khoản này không còn.')
    who = x['who']
    if p.get('forgive') is True:
        x.update(state='forgiven', last=f'Bỏ qua khoản công cho {who}.')
        c['xp'] += 2
        return dict(message=f'🤝 Bỏ qua {x["owed"] - x["paid"]} xu tiền công. Coi như giúp nhà chị Thảo.')
    kit.need(x['on'] != c['day'] or x['tries'] == 0, 'Hôm nay đã nhắc rồi. Mai nhắc tiếp.')
    tone = kit.one_of(p.get('tone'), folk.TONES, 'Chọn cách nhắc.')
    owed = x['owed'] - x['paid']
    asked = kit.integer(p['amount'], 1, owed) if p.get('amount') is not None else owed
    tr = folk.traits(x['id'], _persona(x['npc']))
    tr = dict(tr, honest=max(tr['honest'], 40))      # a family that hires by the hour never vanishes
    r = folk.chase(tr, owed, tone, asked, x['tries'], c['day'] - x['day'])
    kind = 'later' if r['kind'] == 'gone' else r['kind']
    x['tries'] += 1
    x['on'] = c['day']
    line = hc.CHASE_LINES[kind][folk.roll('nt-chase', x['id'], x['tries']) % 2].format(who=who)
    if r['paid']:
        kit.money(s, c, r['paid'], f'{who} trả công'[:120], x['task'], 'debt_paid')
        x['paid'] += r['paid']
    if x['paid'] >= x['owed']:
        x['state'] = 'paid'
    if kind == 'angry':
        kit.review(s, c, kit.npc_id(ID, x['npc']), 3, 'Có mấy đồng công mà nhắc như đòi nợ, nhờ bà nói hộ. Ngại thật.', x['id'])
    x['last'] = line[:200]
    label = {'soft': 'Nhắc nhẹ', 'straight': 'Nói thẳng', 'family': 'Nhờ bà nói hộ'}[tone]
    head = {'paid': '💵', 'part': '💵', 'later': '⏳', 'deny': '🙄', 'angry': '😤'}[kind]
    tail = f' (+{r["paid"]} xu)' if r['paid'] else ''
    return dict(message=f'{head} {label}: {line}{tail}', correct=kind not in ('angry',), celebrate=kind == 'paid')


# ---------------------------------------------------------------- chị Thảo checks the market book again
TROUBLE = ('audit',)
AUDIT_CHOICES = ('refund', 'explain', 'deny')


def _audit_open(s: dict, c: dict, d: dict) -> bool:
    tb = d['trouble']
    if tb['ev'] is not None or not c.get('open'):
        return False
    au = next((x for x in d['audits'] if x['state'] == 'wait' and x['due'] <= c['day']), None)
    if not au:
        return False
    au['state'] = 'open'
    tb['seq'] += 1
    tb['ev'] = dict(id=f'tr-{tb["seq"]}', kind='audit', day=c['day'], npc=0, step=0, tries=0,
                    facts=dict(au=au['id'], diff=au['diff'], who='Chị Thảo'))
    kit.log(s, c, 'surprise', f'Chị Thảo cầm sổ chợ: “Hôm trước em ghi lệch {au["diff"]} xu so với giá cô Năm nói. Em xem lại giúp chị.”',
            kit.npc_id(ID, 0), tb['ev']['id'])
    return True


def _trouble(s, c, d, p):
    tb = d['trouble']
    ev = tb['ev']
    kit.need(ev and ev['kind'] == 'audit', 'Không có chuyện gì cần trả lời.')
    choice = kit.one_of(p.get('choice'), AUDIT_CHOICES, 'Chọn cách trả lời.')
    f = ev['facts']
    diff = f['diff']
    tr = folk.traits(f['au'], 'picky')
    good = None
    if choice == 'refund':
        back = min(diff, c['money'])
        if back:
            kit.money(s, c, -back, 'Trả lại tiền chợ ghi khống', f['au'], 'refund')
        c['xp'] += 2
        good, out = None, f'Bạn nhận sai, trả lại {back} xu. Chị Thảo im một lúc: “Nói thật là chị còn tin. Lần sau đừng thế nhé.”'
    elif choice == 'explain':
        back = min(diff, c['money'])
        if back:
            kit.money(s, c, -back, 'Trả lại tiền chợ ghi khống', f['au'], 'refund')
        kit.review(s, c, kit.npc_id(ID, 0), 2, 'Ghi khống tiền chợ, hỏi ra còn bảo hôm đó giá tăng. Cô Năm nói khác hẳn.', f['au'])
        good, out = False, 'Bạn bảo hôm đó giá tăng. Chị Thảo gọi hỏi cô Năm ngay trước mặt bạn. Bạn phải trả lại tiền, mặt nóng ran.'
        if tr['savvy'] < 40:
            good, out = None, 'Bạn bảo hôm đó giá tăng. Chị Thảo nhìn bạn rất lâu rồi bảo: “Thôi, chị ghi lại cho đúng.” Bạn trả lại tiền.'
    else:
        kit.review(s, c, kit.npc_id(ID, 0), 1, 'Ghi khống tiền chợ, hỏi thì chối. Từ nay chị đưa tiền chợ từng bữa.', f['au'])
        good, out = False, 'Bạn chối. Chị Thảo không nói gì nữa, nhưng từ hôm đó tiền chợ đưa từng bữa, kèm danh sách ghi giá.'
    for x in d['audits']:
        if x['id'] == f['au']:
            x['state'] = 'done'
    folk.trouble_close(tb, out, good, choice, 'Chị Thảo hỏi lại sổ chợ', '📒')
    return dict(message='📒 ' + out, correct=good is not False, celebrate=False)


ACTIONS = {
    'nt_out': _out, 'nt_call': _call, 'nt_pick': _pick, 'nt_put': _put, 'nt_seq': _seq, 'nt_close': _close, 'nt_choose': _choose,
    'nt_offer': _offer, 'nt_buy': _buy, 'nt_receipt': _receipt, 'nt_late': _late, 'nt_chase': _chase, 'nt_trouble': _trouble,
}


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
    for note in folk.auto_repay(s, c, ID, d['debts'], _persona):
        kit.log(s, c, 'surprise', note)


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    today = d['today']
    lines = [f'🏠 Làm {today["jobs"]} việc nhà: {today["clean"]} việc không ai phải nhắc.']
    if today['slips']:
        lines.append(f'📝 Chị Thảo ghi {today["slips"]} điều cần nhớ vào sổ tay nhà.')
    if today['pocket']:
        lines.append(f'📒 Sổ chợ hôm nay lệch {today["pocket"]} xu. Chị Thảo chưa nói gì.')
    elif today['market']:
        lines.append('📒 Sổ chợ khớp. Chị Thảo yên tâm.')
    if today['earned']:
        lines.append(f'💵 Nhận {today["earned"]} xu tiền công.')
    if desk_note:
        lines.append(desk_note)
    return dict(lines=lines, note='Sáng mai nhận tiền chợ, xếp việc rồi hẵng làm.', jobs=today['jobs'], clean=today['clean'],
                earned=today['earned'], pocket=today['pocket'])


# ================================================================ reviews
CRIT = (('cr', 'craft', 'Làm khéo, đúng cách', 'gọn gàng, đúng cách', 'còn sai cách'),
        ('sf', 'safe', 'An toàn, sức khỏe', 'để ý từng người', 'chưa an toàn'),
        ('hn', 'honest', 'Trung thực', 'rõ ràng, nói thật', 'chưa thật thà'),
        ('mn', 'manner', 'Cư xử', 'lễ phép, khéo léo', 'chưa khéo'))


def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 80 else 4 if p >= 60 else 3 if p >= 40 else 2
    pts = {k: 0 for k in CATS}
    for r in cq.slips(t):
        cat = r['code'].split(':', 1)[0]
        if cat in pts:
            pts[cat] += r['sev']
    if t['kind'] == 'setup':
        return dict(criteria=[dict(key='cash', label='Tiền chợ rõ ràng', score=max(1, 5 - pts['cr'] - pts['hn']), note='đếm, xác nhận' if not pts['hn'] else 'chưa rõ ràng'),
                              dict(key='plan', label='Xếp việc hợp lý', score=max(2, 5 - pts['cr']), note='việc nào trước việc nào sau' if not pts['cr'] else 'thứ tự chưa hợp lý')])
    crit = [dict(key=key, label=label, score=max(1, 5 - pts[cat]), note=ok if not pts[cat] else bad) for cat, key, label, ok, bad in CRIT]
    crit.append(dict(key='speed', label='Nhanh nhẹn', score=speed, note=f'cả nhà chờ còn {p}% kiên nhẫn'))
    return dict(criteria=crit)


# ================================================================ what the client sees
def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return f'Nhận tiền chợ, xếp việc trong ngày. {n["note"]}'
    return f'{t["opening"]} {n["note"]}'.strip()


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    v.pop('twist', None)
    v.pop('tw', None)
    v.pop('reaction', None)
    if not v['known']:
        v['needs'] = None
        return v
    if t['kind'] == 'setup' and t['day'] == 1:
        for st in v['needs']['steps']:
            tip = _tip(st, t['_key'].get(st['id'], {}))
            if tip:
                st['tip'] = tip
    if t['kind'] == 'market' and t['out'] and not t['calls']:
        v['needs']['shop'] = None          # at the stall the list is in your head (or call chị Thảo)
        v['needs']['note'] = ''            # the note repeats the list
    b = t.get('bid')
    v['bid'] = dict(tries=b['tries'], ask=b['ask'], firm=b['firm']) if isinstance(b, dict) else None
    tw = t.get('twist')
    if isinstance(tw, dict) and t['tw']['state'] != 'wait':
        v['twist'] = dict(kind=tw['kind'], state=t['tw']['state'], choice=t['tw']['choice'], line=hc.LATE_LINES[tw['n']])
    return v


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    tb = d['trouble']
    return dict(intro=d['intro'], mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint']), today=d['today'],
                stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()}, desk=kit.desk_public(d['desk'], DESK, ID),
                debts=folk.public_debts(d['debts']), trouble=dict(ev=tb['ev'], last=tb['last']))


def content() -> dict:
    return dict(intro=INTRO, notebook=[dict(emoji=e, who=w, text=x) for e, w, x in hc.NOTEBOOK], kinds=hc.KIND_LABEL, kind_emoji=hc.KIND_EMOJI,
                pay=PAY, debt_max=folk.DEBT_MAX, people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE])


def hint(c: dict, t: dict) -> str:
    k = t.get('kind')
    if k == 'setup':
        return 'Đếm tiền chợ trước mặt chị Thảo → xếp việc: bật máy giặt rồi đi chợ, nấu xong mới rửa bát.'
    if k == 'market':
        return 'Nhớ danh sách → ra chợ → chọn đồ tươi, đúng danh sách → trả giá vừa phải → ghi sổ đúng từng xu.'
    return 'Mở Sổ tay nhà: ai ăn gì, kiêng gì, uống thuốc gì. Làm từng bước, sai thì nói thật.'


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    if e.get('role') == 'kitchen':
        return 'Đã nhặt rau, vo gạo, rửa sạch hai cái thớt.'
    if e.get('role') == 'tidy':
        return 'Đã gom rác, phơi khăn, lau khô sàn nhà tắm.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu việc nhà sai.')


def _vwork(st: dict, v) -> None:
    typ = st['type']
    ids = [i['id'] for i in st.get('items', [])]
    if typ in ('pick', 'order'):
        kit.need(isinstance(v, list) and len(v) == len(set(v)) and all(x in ids for x in v), 'Bước việc nhà sai.')
    elif typ == 'sort':
        bins = [b['id'] for b in st['bins']]
        kit.need(isinstance(v, dict) and all(k in ids and x in bins for k, x in v.items()), 'Bước việc nhà sai.')
    elif typ == 'choose':
        kit.need(v in [o['id'] for o in st['options']], 'Bước việc nhà sai.')
    else:
        kit.integer(v, 0, 10 ** 5)


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc nhà không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc nhà sai.')
    steps = t['needs']['steps']
    by = {st['id']: st for st in steps}
    kit.integer(t.get('at'), 0, len(steps))
    kit.need(isinstance(t.get('work'), dict) and set(t['work']) <= set(by), 'Việc nhà sai.')
    for sid, v in t['work'].items():
        _vwork(by[sid], v)
    for k in ('closed', 'skipped'):
        v = t.get(k)
        kit.need(isinstance(v, list) and len(v) == len(set(v)) and set(v) <= set(by), 'Việc nhà sai.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= LINES_MAX and all(isinstance(x, str) and len(x) <= 300 for x in t['lines']), 'Nhật ký việc nhà sai.')
    kit.integer(t.get('spent'), 0, 10 ** 5)
    kit.integer(t.get('calls'), 0, 1)
    _vbool(t.get('out'))
    b = t.get('bid')
    if b is not None:
        kit.need(isinstance(b, dict) and set(b) == {'tries', 'ask', 'firm'}, 'Trả giá sai.')
        kit.integer(b['tries'], 0, 9)
        kit.integer(b['ask'], 1, 10 ** 5)
        _vbool(b['firm'])
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện người nhà sai.')
    if 'twist' in t or 'tw' in t:
        tw, st = t.get('twist'), t.get('tw')
        kit.need(tw is not None and tw == twist_of(t), 'Chuyện tiền công không khớp.')
        kit.need(isinstance(st, dict) and set(st) == {'state', 'choice'} and st['state'] in ('wait', 'on', 'done')
                 and st['choice'] in (None, 'ok', 'ask'), 'Chuyện tiền công sai.')
    kit.need(t['stage'] != 'late' or (isinstance(t.get('tw'), dict) and t['tw']['state'] == 'on'), 'Chuyện tiền công sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ người nhà sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ người nhà sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu việc nhà sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)
    folk.validate_debts(d['debts'], len(PEOPLE), kit.need)
    folk.validate_trouble(d['trouble'], TROUBLE, kit.need)
    kit.need(isinstance(d['audits'], list) and len(d['audits']) <= 8, 'Sổ chợ cần hỏi lại sai.')
    for x in d['audits']:
        kit.need(isinstance(x, dict) and set(x) == {'id', 'task', 'due', 'diff', 'state'} and x['state'] in ('wait', 'open', 'done'), 'Sổ chợ cần hỏi lại sai.')
        kit.integer(x['due'], 1, 10 ** 7)
        kit.integer(x['diff'], 1, 10 ** 5)
        kit.text(x['id'], 80)
        kit.text(x['task'], 60)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='nt_', category='service',
    meta=dict(short='Nội trợ, giúp việc nhà', place='Nhà chị Thảo', tagline='Đúng khẩu vị, đúng giờ thuốc, rõ từng xu.', icon='home',
              color='#b0613a', light='#f8ebe2', weather='Nắng nhẹ, gió mát ngõ Hoa Sữa', work='Việc nhà', station='Bếp & nhà cửa',
              greeting='Đếm tiền chợ, xếp việc trong ngày. Ai ăn gì, kiêng gì, uống thuốc gì thì mở Sổ tay nhà nhé.',
              caption='Mỗi người trong nhà một khẩu vị', map_label='22 · NHÀ CHỊ THẢO'),
    people=PEOPLE,
    staff=[('Hiền', 'kitchen', 'Nhặt rau nhanh thoăn thoắt, nêm nếm khéo.', 80, 88),
           ('Mai', 'tidy', 'Gọn gàng, nhà nào qua tay cũng sáng bóng.', 84, 82),
           ('Thu', 'kitchen', 'Từng nấu cho nhà có người ốm, thuộc món nào kiêng gì.', 74, 92),
           ('Lan', 'tidy', 'Khỏe, lau cả căn nhà ba tầng không nghỉ.', 88, 76)],
    roles={'kitchen': 'Phụ bếp', 'tidy': 'Dọn dẹp'},
    tip=0,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('📒', 'Sổ tay nhà', [('Bà Lành', 'Ăn nhạt, không đường'), ('Bé Su', 'Dị ứng tôm'), ('Anh Dũng', 'Ớt để riêng'), ('Bé Cốm', 'Cháo nhuyễn')],
              ['Đếm tiền chợ, xếp việc', 'Đi chợ, ghi sổ', 'Nấu theo từng người', 'Giặt, lau, chăm bà, trông bé']),
    stories=[('Cuốn sổ chợ của chị Thảo', ('Cuốn sổ chợ bìa xanh, chị Thảo ghi từng khoản từ năm năm nay.',
                                           'Chị dạy bạn ghi cả tên sạp, giá từng thứ: “Ghi rõ thì không ai phải nghi ai.”',
                                           'Cuối tháng cộng sổ khớp từng xu, chị Thảo viết thêm một dòng: “Cảm ơn em.”')),
             ('Hũ dưa của bà Lành', ('Hũ dưa cải bà Lành muối từ hồi còn ông.',
                                     'Bà chỉ bạn cách phơi cải, pha nước muối, nén đá cho dưa vàng giòn.',
                                     'Mẻ dưa đầu tiên bạn muối, bà nếm rồi gật gù: “Được, chua vừa.”')),
             ('Bức tranh của bé Su', ('Bé Su vẽ cả nhà trên tờ giấy A4, thiếu mỗi một người.',
                                      'Mấy tuần sau, trong tranh có thêm một người đeo tạp dề, tay xách làn đi chợ.',
                                      'Bức tranh được dán lên tủ lạnh, cạnh tờ Sổ tay nhà.'))],
    review_asides=['Cơm nước đúng khẩu vị từng người.', 'Sổ chợ rõ ràng từng xu.', 'Nhà cửa sạch sẽ, gọn gàng.',
                   'Bà và các cháu đều quý.'],
    situations=SITUATIONS,
    more_line='Chị Thảo nhắn thêm một việc nhà.',
    guide='Sáng: đếm tiền chợ trước mặt chị Thảo, xếp việc trong ngày. Mỗi việc: nghe dặn → làm từng bước (chọn, xếp, sắp thứ tự, quyết định) → ghi sổ chợ đúng từng xu. Ai ăn gì, kiêng gì, uống thuốc gì: xem Sổ tay nhà.',
)
