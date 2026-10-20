"""💒 Dịch vụ cưới từ người chơi (owner 21/10 "làm hết đi": careers interact player to player).

A couple planning or holding their wedding hires OTHER players who work the fitting careers:
  🍽️ Tiệc cưới        banquet (Nhà hàng tiệc)   ('banquet', 'tiec_cuoi'), per table
  💐 Hoa cưới          florist (Tiệm hoa)        ('florist', 'hoa_cuoi')
  👰 Váy cưới & vest   clothing (Shop quần áo)   ('clothing', 'vay_cuoi')
  💄 Trang điểm        salon (Salon tóc)         ('salon', 'trang_diem_cuoi')
  📸 Ảnh cưới          photobooth: game/photo_studio.py's own 'doi' package (Ảnh đôi · cưới), reused, not duplicated
No career fits an MC or a band (the NPC extras 'mc' and 'band' of the plan stay as they are).

Money, escrow, prices, negotiation and the anti-laundering rules are game/service_market.py's (registered here at import):
the price is the NPC price of the wedding plan (wedding_content: a table of the standard menu, the extras 'flowers',
'dress', 'makeup') × 3 by default, ×1–×10 or 🤝 thương lượng; the escrow comes from the wallet then the bank account,
the provider receives 95 % and 5 % is burned when the work is delivered; a declined, cancelled or late order is
refunded in full. Nothing in any save: no new key, no hook into a save (on_buyer / on_provider unused).

The provider's real work (their career's 💒 Đơn cưới entry, public/js/v4/wed-services.js): a taken order is a job of
seven steps rolled once from the order id (game/wed_services_content.py): two craft steps that must follow the couple's
brief, one craft-knowledge step, three "oái ăm" demands (the bride changes the flower colour at 5 am, the mother-in-law
finds the soup bland, the groom's side announces more tables…; one of them changes the brief when the provider agrees)
and the last check before the ceremony, which must match the brief as it is NOW. Each step is graded here, once
(`at` = the step's index: a retried tap changes nothing). The stars (1–5) come from the points. The service's
`deliver` hook refuses until every step is answered, so the generic "Xong việc" of Phố dịch vụ cannot skip the work.

What the couple gets (visibly):
* the 💒 card of the Hôn nhân sheet and the wedding's result card: "Tiệc do X phục vụ ⭐ 4", "Hoa do Y cắm"…;
* the live party (live/wedding.py `wed.svc`, public/js/v4/wedfeast.js): the MC thanks each provider, a board by the
  gate lists them, the bouquet and the flower strings take the florist's colour;
* 💌 the wedding invite card (game/wed_invite.py `svc`): "Đội ngũ: 🍽️ X · 💐 Y";
* the wedding day (game/marriage.py resolve): a delivered service of 3 stars or more counts as its NPC extra for the
  party's mood (flowers / dress / makeup / album), a 4-star banquet raises the menu one level for the guests' tiền
  mừng. The costs (the stored quote) never change. A couple who hires nobody gets exactly the NPC wedding as before.

Who may order: an engaged couple (planning or confirmed), or a married couple whose live party is not over yet.
🛑 MNL_WEDSVC_OFF=1: no new order, no work step, no delivery (orders already paid wait, or are refunded by the market's
timers); the NPC wedding is untouched.

Table (game/pg_schema.py SCHEMA_VERSION 69): wedsvc_jobs (one row per order: the brief, the rolled steps, the answers,
the score and stars, the couple it serves). Bounded cache: the credits of a couple (CACHE_MAX couples, CACHE_TTL s).
"""
from __future__ import annotations

import json
import os
import random
import time
from collections import OrderedDict

from . import marriage as mr
from . import service_market as sm
from . import wedding_content as W
from . import wed_services_content as C

WORK_HOURS = 72                # a taken order must be delivered within this long (the market refunds it after)
CACHE_TTL = 20.0               # seconds the credits of a couple are kept (invite cards: every player's page load)
CACHE_MAX = 512                # couples kept at most
NOTE_MAX = 200
DAY = 86400
OPEN = ('talk', 'held', 'working', 'delivered', 'ready', 'refund')
OFF_TEXT = 'Dịch vụ cưới từ người chơi đang tạm nghỉ để bảo trì. Kế hoạch cưới với NPC vẫn dùng bình thường nhé!'
_cache: OrderedDict = OrderedDict()


def off() -> bool:
    return os.environ.get('MNL_WEDSVC_OFF', '').strip().lower() in ('1', 'true', 'yes', 'on')


def now() -> float:
    return time.time()


def need(cond, message: str, code: str = 'wedsvc', status: int = 400):
    sm.need(cond, message, code, status)


def _j(raw, default):
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return default
    return v if isinstance(v, type(default)) else default


def _dump(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


# ---------------------------------------------------------------- NPC prices (the base of every player price)
def npc_price(key: str) -> int:
    """The NPC price of one unit in the wedding plan: a table of the standard menu at a restaurant, or the extra."""
    if key == 'tiec':
        return mr.table_price('restaurant', 'tieu_chuan')
    return int(W.EXTRA_INDEX[C.SVC[key]['extra']]['price'])


# ---------------------------------------------------------------- who may order: the couple and their wedding
def ctx(db, sid: str, t: float | None = None) -> dict:
    """{c (couple row | None), wedding (latest plan row | None), party (wedding_live.party_view | None), when (label),
    tables (the plan's), why ('' or the refusal)}."""
    from . import wedding_live as wl
    t = now() if t is None else t
    c = mr._bond(db, sid)
    out = dict(c=None, wedding=None, party=None, when='', tables=0, why='')
    if not c or c['status'] not in ('engaged', 'married'):
        out['why'] = 'Dịch vụ cưới dành cho cặp đã đính hôn. Cầu hôn rồi lên kế hoạch cưới trước nhé 💍'
        return out
    out['c'] = c
    w = mr._row(db, "SELECT id, status, plan FROM weddings WHERE couple=? AND status IN ('proposed','rejected','confirmed','done') "
                    'ORDER BY id DESC LIMIT 1', (c['id'],))
    out['wedding'] = w
    plan = _j((w or {}).get('plan'), {})
    out['tables'] = int(plan.get('tables') or 0)
    party = wl.party_view(db, c, t)
    out['party'] = party
    if party and party.get('state') in ('booked', 'live'):
        out['when'] = 'Tiệc cưới ' + str(party.get('at_label') or '')
    elif plan.get('at') and (w or {}).get('status') == 'confirmed':
        out['when'] = 'Cưới lúc ' + wl.fmt_at(plan['at'])
    elif (w or {}).get('status') in ('proposed', 'rejected'):
        out['when'] = 'Đang bàn kế hoạch cưới'
    if c['status'] == 'married' and (not party or party.get('state') == 'done'):
        out['why'] = ('Tiệc cưới của hai bạn đã tổ chức xong rồi 🎉' if party else
                      'Đám cưới của hai bạn đã xong rồi.')
    return out


def _check(db, buyer: str, state: dict) -> str:
    """service_market's `check` hook: '' or why this buyer cannot order a wedding service now."""
    if off():
        return OFF_TEXT
    return ctx(db, buyer)['why']


def _can_provide(career: str):
    def ok(state: dict) -> str:
        if off():
            return OFF_TEXT
        c = (state.get('careers') or {}).get(career)
        return '' if isinstance(c, dict) and c.get('started') else 'Bạn cần làm nghề này trước đã.'
    return ok


# ---------------------------------------------------------------- the provider's job
def _opts(key: str, field: str) -> list:
    return next(o for f, _, o in C.SVC[key]['brief'] if f == field)


def clean_brief(key: str, brief, fill_from: str = '') -> dict:
    """The couple's choices: every field of the service, each one of its options. `fill_from` (an order id): a
    missing or bad value is rolled from it (an order made from the generic directory carries no brief)."""
    brief = brief if isinstance(brief, dict) else {}
    rng = random.Random('wedsvc-brief|' + fill_from) if fill_from else None
    out = {}
    for field, label, opts in C.SVC[key]['brief']:
        v = brief.get(field)
        ids = [i for i, _, _ in opts]
        if v not in ids:
            need(rng is not None, f'Chọn {label.lower()} nhé.', 'bad_brief')
            v = rng.choice(ids)
        out[field] = v
    return out


def plan_of(oid: str, key: str, brief: dict, qty: int) -> list:
    """The seven steps of a job, rolled once from the order id (the same on every retry)."""
    rng = random.Random(f'wedsvc|{oid}')
    s = C.SVC[key]
    f0, f1 = [f for f, _, _ in s['brief']]
    ids = lambda f: [i for i, _, _ in _opts(key, f)]

    def shuffled(xs):
        xs = list(xs)
        rng.shuffle(xs)
        return xs
    steps = [dict(k='b1', f=f0, o=shuffled(ids(f0))), dict(k='b2', f=f1, o=shuffled(ids(f1)))]
    steps.append(dict(k='k', id=rng.choice(C.KNOW[key])[0], o=shuffled('abc')))
    ch = dict(k='d', id=C.CHANGE[key][0], change=True, o=shuffled('abc'))
    if key == 'tiec':
        ch['n'] = rng.choice(C.EXTRA_TABLES)
    else:
        field = s['change']
        ch['old'] = brief[field]
        ch['new'] = rng.choice([i for i in ids(field) if i != brief[field]])
    demands = [dict(k='d', id=x, o=shuffled('abc')) for x in rng.sample([d[0] for d in C.DEMANDS[key]], C.DEMANDS_PER_JOB)]
    demands.insert(rng.randrange(len(demands) + 1), ch)
    steps += demands
    if key == 'tiec':
        n = ch['n']
        final = sorted({qty, qty + n, max(1, qty - 2) if qty > 2 else qty + n + 2})
        steps.append(dict(k='final', o=[str(x) for x in shuffled(final)]))
    else:
        steps.append(dict(k='final', o=shuffled(ids(s['change']))))
    return steps


def _ensure_job(db, order: dict, brief=None, couple=None, lock: bool = True) -> dict:
    """The job row of an order (created on first use: an order from the generic directory gets a rolled brief)."""
    key = C.PAIRS.get((order['career'], order['service']))
    need(key, 'Đây không phải đơn cưới.', 'not_wedding', 404)
    t = now()
    b = clean_brief(key, brief, order['id'])
    if key == 'tiec':
        b['tables'] = int(order['qty'])
    if couple is None:
        c = mr._bond(db, order['buyer'])
        couple = c['id'] if c and c['status'] in ('engaged', 'married') else None
    db.execute('INSERT INTO wedsvc_jobs(order_id, svc, career, service, provider, buyer, couple, brief, plan, answers, status, score, stars, '
               "created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,'[]','work',0,0,?,?) ON CONFLICT(order_id) DO NOTHING",
               (order['id'], key, order['career'], order['service'], order['provider'], order['buyer'], couple, _dump(b),
                _dump(plan_of(order['id'], key, b, int(order['qty']))), t, t))
    r = db.execute('SELECT * FROM wedsvc_jobs WHERE order_id=?' + (' FOR UPDATE' if lock else ''), (order['id'],)).fetchone()
    return dict(r)


def _demand(key: str, st: dict):
    if st.get('change'):
        return C.CHANGE[key]
    return next(d for d in C.DEMANDS[key] if d[0] == st['id'])


def _fmt(key: str, text: str, st: dict, brief: dict) -> str:
    if key == 'tiec':
        n = int(st.get('n') or 0)
        return text.replace('{total}', str(int(brief.get('tables') or 0) + n)).replace('{n}', str(n))
    field = C.SVC[key]['change']
    return text.replace('{new}', C.opt_name(key, field, st.get('new')).lower()).replace('{old}', C.opt_name(key, field, st.get('old')).lower())


def _right(key: str, st: dict, brief: dict) -> str:
    if st['k'] in ('b1', 'b2'):
        return str(brief[st['f']])
    if st['k'] == 'k':
        return 'a'
    if key == 'tiec':
        return str(int(brief['tables']))
    return str(brief[C.SVC[key]['change']])


def _question(key: str, st: dict, brief: dict, before: dict | None = None) -> tuple:
    """(question, [(option id, text)]) of a step as the provider sees it (`before`: the brief when it was asked)."""
    b = before if before is not None else brief
    if st['k'] in ('b1', 'b2'):
        q = C.CRAFT[key][0 if st['k'] == 'b1' else 1]
        names = {i: f'{e} {n}' for i, n, e in _opts(key, st['f'])}
        return q, [(i, names[i]) for i in st['o']]
    if st['k'] == 'k':
        k = next(x for x in C.KNOW[key] if x[0] == st['id'])
        texts = dict(k[2])
        return k[1], [(i, texts[i]) for i in st['o']]
    if st['k'] == 'd':
        d = _demand(key, st)
        texts = {o[0]: _fmt(key, o[1], st, b) for o in d[2]}
        return _fmt(key, d[1], st, b), [(i, texts[i]) for i in st['o']]
    if key == 'tiec':
        return C.SVC[key]['final'], [(i, f'{i} bàn') for i in st['o']]
    names = {i: f'{e} {n}' for i, n, e in _opts(key, C.SVC[key]['change'])}
    return C.SVC[key]['final'], [(i, names[i]) for i in st['o']]


def _grade(key: str, st: dict, pick: str, brief: dict) -> tuple:
    """(points, reply, the brief after the step)."""
    after = dict(brief)
    if st['k'] == 'd':
        d = _demand(key, st)
        o = next(x for x in d[2] if x[0] == pick)
        if st.get('change') and pick == 'a':
            if key == 'tiec':
                after['tables'] = int(after['tables']) + int(st['n'])
            else:
                after[C.SVC[key]['change']] = st['new']
        return int(o[2]), o[3], after
    right = _right(key, st, brief)
    if st['k'] == 'k':
        why = next(x for x in C.KNOW[key] if x[0] == st['id'])[3]
        return (2, '✓ ' + why, after) if pick == right else (0, '✗ ' + why, after)
    if pick == right:
        return 2, '✓ Đúng như cô dâu chú rể dặn.', after
    if st['k'] == 'final' and key == 'tiec':
        return 0, f'✗ Sai rồi: phải dọn {right} bàn.', after
    field = st['f'] if st['k'] != 'final' else C.SVC[key]['change']
    return 0, f'✗ Sai rồi: phải là {C.opt_name(key, field, right).lower()}.', after


def _replay(key: str, job: dict) -> list:
    """[(step, the brief when it was asked, answer)] of the answered steps."""
    plan, answers = _j(job['plan'], []), _j(job['answers'], [])
    brief0 = _j(job['brief'], {})
    # the brief column is the CURRENT brief: rebuild the one each step saw from the original values of the plan
    b = dict(brief0)
    for st in plan:
        if st.get('change'):
            if key == 'tiec':
                b['tables'] = int(b['tables']) - (int(st['n']) if _changed(st, plan, answers) else 0)
            elif _changed(st, plan, answers):
                b[C.SVC[key]['change']] = st['old']
    out = []
    for i, st in enumerate(plan):
        a = answers[i] if i < len(answers) else None
        out.append((st, dict(b), a))
        if a is not None:
            _, _, b = _grade(key, st, a['pick'], b)
    return out


def _changed(st: dict, plan: list, answers: list) -> bool:
    i = plan.index(st)
    return i < len(answers) and answers[i]['pick'] == 'a'


def job_view(job: dict) -> dict:
    """The provider's job: the brief now, the answered steps (with their replies), the next step, the score."""
    key = job['svc']
    brief = _j(job['brief'], {})
    steps, nxt = [], None
    for i, (st, b, a) in enumerate(_replay(key, job)):
        q, opts = _question(key, st, brief, b)
        if a is not None:
            pick = next((t for o, t in opts if o == a['pick']), a['pick'])
            steps.append(dict(i=i, k=st['k'], name=C.STEP_NAMES[st['k']], q=q, pick=pick, pts=int(a['pts']), reply=a.get('reply', ''),
                              mark=C.FEEDBACK[int(a['pts'])]))
        elif nxt is None:
            nxt = dict(i=i, k=st['k'], name=C.STEP_NAMES[st['k']], q=q, options=[dict(id=o, text=t) for o, t in opts])
    s = C.SVC[key]
    return dict(order=job['order_id'], svc=key, status=job['status'], brief=[dict(label=lab, value=C.opt_name(key, f, brief.get(f)))
                                                                              for f, lab, _ in s['brief']]
                + ([dict(label='Số bàn', value=f'{int(brief.get("tables") or 0)} bàn')] if key == 'tiec' else []),
                steps=steps, next=nxt, total=len(_j(job['plan'], [])), score=int(job['score']), max=C.MAX_SCORE,
                stars=int(job['stars']), done=job['status'] in ('ready', 'delivered'))


def step(store, sid: str, d: dict) -> dict:
    """The provider answers the next step of a job (once: `at` must be that step's index)."""
    need(not off(), OFF_TEXT, 'wedsvc_off', 503)
    need(isinstance(d, dict) and set(d) <= {'order', 'at', 'pick'}, 'Thông tin không hợp lệ.')
    oid, at, pick = d.get('order'), d.get('at'), d.get('pick')
    need(isinstance(oid, str) and sm.ID_RX.fullmatch(oid) and oid.startswith('sv_'), 'Không tìm thấy đơn.', 'not_found', 404)
    need(type(at) is int and 0 <= at < 20 and isinstance(pick, str) and len(pick) <= 24, 'Chọn một cách làm nhé.', 'bad_step')

    def run(db):
        o = db.execute('SELECT * FROM svc_orders WHERE id=?', (oid,)).fetchone()
        need(o and o['provider'] == sid, 'Không tìm thấy đơn.', 'not_found', 404)
        o = dict(o)
        need(C.PAIRS.get((o['career'], o['service'])), 'Đây không phải đơn cưới.', 'not_wedding', 404)
        job = _ensure_job(db, o)
        answers, plan = _j(job['answers'], []), _j(job['plan'], [])
        if at != len(answers) or job['status'] != 'work':
            return job   # a retried tap, or the job is already finished: nothing changes
        need(o['status'] == 'working', 'Nhận đơn trước rồi mới bắt tay vào làm nhé.' if o['status'] == 'held' else 'Đơn này không còn chờ làm.',
             'not_working', 409)
        st = plan[at]
        need(pick in st['o'], 'Chọn một cách làm nhé.', 'bad_step')
        brief = _j(job['brief'], {})
        pts, reply, after = _grade(job['svc'], st, pick, brief)
        answers.append(dict(pick=pick, pts=pts, reply=reply))
        score = sum(int(a['pts']) for a in answers)
        done = len(answers) == len(plan)
        t = now()
        db.execute('UPDATE wedsvc_jobs SET answers=?, brief=?, score=?, stars=?, status=?, updated_at=? WHERE order_id=?',
                   (_dump(answers), _dump(after), score, C.stars_of(score) if done else 0, 'ready' if done else 'work', t, oid))
        return dict(job, answers=_dump(answers), brief=_dump(after), score=score, stars=C.stars_of(score) if done else 0,
                    status='ready' if done else 'work')
    job = store.transaction(run)
    v = job_view(job)
    last = v['steps'][-1] if v['steps'] else None
    return dict(job=v, changed=True, message=(last or {}).get('reply', ''))


def _deliver(db, provider: str, buyer: str, order: dict) -> dict:
    """service_market's `deliver` hook (inside the transaction that marks the work done): refuses until every step
    of the job is answered; binds the job to the buyer's couple; the result both players see."""
    need(not off(), OFF_TEXT, 'wedsvc_off', 503)
    row = db.execute('SELECT * FROM svc_orders WHERE id=?', (order['id'],)).fetchone()
    job = _ensure_job(db, dict(row))
    need(job['status'] in ('ready', 'delivered'), 'Làm xong các bước của đơn cưới trước đã (mục 💒 Đơn cưới ở nơi làm việc).', 'wedsvc_unfinished', 409)
    if job['couple'] is None:
        c = mr._bond(db, buyer)
        job['couple'] = c['id'] if c else None
    t = now()
    db.execute("UPDATE wedsvc_jobs SET status='delivered', couple=?, delivered_at=COALESCE(delivered_at, ?), updated_at=? WHERE order_id=?",
               (job['couple'], t, t, order['id']))
    _cache.pop(job['couple'], None)
    key = job['svc']
    brief = _j(job['brief'], {})
    name = C.clean_name(mr._display(db, provider))
    return dict(wedsvc=key, stars=int(job['stars']), score=int(job['score']), max=C.MAX_SCORE, line=C.SVC[key]['credit'].format(n=name),
                detail=C.brief_line(key, brief))


def _register() -> None:
    for key in C.ORDER:
        s = C.SVC[key]
        sm.register(s['career'], s['service'], dict(
            name=s['short'] if len(s['name']) > 60 else s['name'], icon=s['icon'], desc=s['desc'], base=npc_price(key), unit=s['unit'],
            qty_max=s['qty_max'], work_hours=WORK_HOURS, duration=120, deliver=_deliver, confirm='auto', check=_check,
            can_provide=_can_provide(s['career']), note_hint='Ví dụ: cô dâu thích tông pastel, nhà trai đông người…'))


_register()


# ---------------------------------------------------------------- credits: who serves this couple's wedding
def credits(db, couple: dict | None) -> list:
    """[{key, icon, label, line, name, state, stars, detail…}] (game/wed_services_content.credits_from_rows)."""
    if not couple:
        return []
    since = float(couple.get('since') or 0) - DAY   # an order a day before the engagement still counts
    rows = [dict(r) for r in db.execute(C.CREDITS_SQL, (couple['a'], couple['b'], since)).fetchall()]
    try:
        photos = [dict(r) for r in db.execute(C.PHOTO_SQL, (couple['a'], couple['b'], since)).fetchall()]
    except Exception:  # noqa: BLE001  (a database without photo_orders: no photographer line)
        photos = []
    return C.credits_from_rows(rows, photos, couple['id'])


def credits_cached(db, couple: dict | None) -> list:
    """credits() kept CACHE_TTL seconds per couple, at most CACHE_MAX couples (the invite cards of every page load)."""
    if not couple:
        return []
    t, k = now(), int(couple['id'])
    hit = _cache.get(k)
    if hit and 0 <= t - hit[0] < CACHE_TTL:
        return hit[1]
    out = credits(db, couple)
    _cache[k] = (t, out)
    _cache.move_to_end(k)
    while len(_cache) > CACHE_MAX:
        _cache.popitem(last=False)
    return out


def alerts(db, sid: str) -> int:
    """💒 The provider's badge (the ticker's me.wedsvc): wedding orders paid and waiting to be taken or finished."""
    if off():
        return 0
    marks = ','.join('?' * len(C.SERVICES))
    r = db.execute(f"SELECT COUNT(*) AS n FROM svc_orders WHERE provider=? AND status IN ('held','working') AND service IN ({marks})",
                   (sid, *sorted(C.SERVICES))).fetchone()
    return int(r['n'] or 0)


def card(db, couple: dict | None) -> list:
    """The Hôn nhân sheet's 💒 card: the credits (short)."""
    if off() or not couple:
        return []
    return [{k: x[k] for k in ('key', 'icon', 'label', 'line', 'name', 'state', 'stars', 'detail')} for x in credits(db, couple)]


def invite_svc(db, couple_id) -> list:
    """💌 The invite card's team: [{icon, label, name}] (game/wed_invite.py due)."""
    if off() or couple_id is None:
        return []
    c = mr._row(db, 'SELECT * FROM couples WHERE id=?', (int(couple_id),))
    return [dict(icon=x['icon'], label=x['label'], name=x['name']) for x in credits_cached(db, c)][:5]


def roll_plan(db, couple: dict, plan: dict) -> tuple:
    """The wedding day (game/marriage.py resolve): (the plan the guests' roll uses, the credits). A delivered service of
    3 stars or more counts as its NPC extra; a 4-star banquet raises the menu one level. No player service: the plan
    as it is."""
    if off():
        return plan, []
    cr = credits(db, couple)
    extras, menu = list(plan.get('extras') or []), plan.get('menu')
    for x in cr:
        if x['state'] != 'done':
            continue
        extra = C.PHOTO['extra'] if x['key'] == 'anh' else C.SVC[x['key']]['extra']
        if x['key'] == 'anh' or x['stars'] >= 3:
            if extra and extra in W.EXTRA_INDEX and extra not in extras:
                extras.append(extra)
        if x['key'] == 'tiec' and x['stars'] >= 4:
            ids = [m['id'] for m in W.MENUS]
            if menu in ids and ids.index(menu) + 1 < len(ids):
                menu = ids[ids.index(menu) + 1]
    if extras == list(plan.get('extras') or []) and menu == plan.get('menu'):
        return plan, cr
    return dict(plan, extras=extras, menu=menu), cr


# ---------------------------------------------------------------- the couple's sheet
def _order_line(db, r: dict, sid: str, jobs: dict) -> dict:
    key = C.PAIRS[(r['career'], r['service'])]
    j = jobs.get(r['id'])
    brief = _j((j or {}).get('brief'), {}) or {}
    st = r['status']
    return dict(id=r['id'], svc=key, icon=C.SVC[key]['icon'], label=C.SVC[key]['short'], status=st, price=int(r['price'] or r['ask']),
                qty=int(r['qty']), mine=r['buyer'] == sid, who=C.clean_name(mr._display(db, r['provider'])),
                pid=sm._pid(r['provider']), stars=int((j or {}).get('stars') or 0) if (j or {}).get('status') == 'delivered' else 0,
                detail=C.brief_line(key, brief, int(r['qty'])) if brief else '',
                progress=len(_j((j or {}).get('answers'), [])), total=len(_j((j or {}).get('plan'), [])) or 7)


def _jobs(db, ids) -> dict:
    ids = [i for i in ids if i]
    if not ids:
        return {}
    marks = ','.join('?' * len(ids))
    return {r['order_id']: dict(r) for r in db.execute(f'SELECT * FROM wedsvc_jobs WHERE order_id IN ({marks})', tuple(ids)).fetchall()}


def _photographers(db, sid: str) -> list:
    """📸 Open photographers (game/photo_studio.py) with their 'doi' price and place, the busiest first."""
    from . import photo_studio as ps
    out = []
    try:
        rows = [dict(r) for r in db.execute('SELECT * FROM photo_studios WHERE open=1 AND sid<>? ORDER BY done DESC, at DESC LIMIT 20', (sid,)).fetchall()]
    except Exception:  # noqa: BLE001  (a database without the photo tables)
        return out
    for r in rows:
        if len(out) >= 6:
            break
        if not ps._is_shooter(db, r['sid']) or sm._blocked(db, sid, r['sid']):
            continue
        done = int(r['done'] or 0)
        out.append(dict(name=C.clean_name(r['name'] or mr._display(db, r['sid'])), pid=r['pid'], place=ps.place_id(r['sid']),
                        price=ps.prices_of(r)[C.PHOTO['pkg']], done=done, stars=round(int(r['stars'] or 0) / done, 1) if done else 0))
    return out


def couple_view(store, sid: str, state: dict | None) -> dict:
    """GET /api/wedsvc/couple: the couple's wedding, the services (NPC price, the providers listed in Phố dịch vụ), the
    orders of both spouses, the credits and the photographers."""
    sm.settle_for(store, sid)
    t = now()
    with store.connect() as db:
        cx = ctx(db, sid, t)
        c = cx['c']
        orders, cr, photo = [], [], []
        if c:
            since = float(c.get('since') or 0) - DAY
            marks = ','.join('?' * len(C.SERVICES))
            rows = [dict(r) for r in db.execute(f"SELECT * FROM svc_orders WHERE buyer IN (?, ?) AND kind='svc' AND service IN ({marks}) "
                                                'AND created_at>=? ORDER BY created_at DESC LIMIT 30', (c['a'], c['b'], *sorted(C.SERVICES), since)).fetchall()]
            rows = [r for r in rows if (r['career'], r['service']) in C.PAIRS]
            jobs = _jobs(db, [r['id'] for r in rows])
            orders = [_order_line(db, r, sid, jobs) for r in rows if r['status'] in OPEN or r['status'] == 'done' or r['updated_at'] > t - 3 * DAY]
            cr = credits(db, c)
            photo = _photographers(db, sid)
        partner = mr._display(db, mr._other(c, sid)) if c else ''
    services = []
    for key in C.ORDER:
        s = C.SVC[key]
        listed = []
        if c and not cx['why'] and not off():
            try:
                listed = sm.directory(store, sid, dict(career=s['career'], service=s['service'], sort='rating'))['items'][:8]
            except sm.ServiceError:
                listed = []
        services.append(dict(key=key, icon=s['icon'], name=s['name'], short=s['short'], desc=s['desc'], unit=s['unit'], qty_max=s['qty_max'],
                             career=s['career'], service=s['service'], npc=npc_price(key), extra=s['extra'],
                             brief=[dict(field=f, label=lab, options=[dict(id=i, name=n, emoji=e) for i, n, e in o]) for f, lab, o in s['brief']],
                             providers=[x for x in listed if not x.get('mine')]))
    return dict(ok=True, off=off(), why=cx['why'] or (OFF_TEXT if off() else ''), status=(c or {}).get('status'), partner=partner,
                when=cx['when'], tables=cx['tables'], services=services, orders=orders, credits=cr, photographers=photo,
                photo=dict(pkg=C.PHOTO['pkg'], icon=C.PHOTO['icon'], label=C.PHOTO['short']), rules=sm.rules())


# ---------------------------------------------------------------- the provider's sheet
def work_view(store, sid: str, state: dict | None) -> dict:
    """GET /api/wedsvc/work: my wedding services (can I sell them, are they on), my wedding orders and their jobs."""
    sm.settle_for(store, sid)
    if state is None:
        got = mr._read_state(store, sid)
        state = got[0] if got else {}
    t = now()
    careers = (state or {}).get('careers') or {}
    with store.connect() as db:
        settings = {(r['career'], r['service']): dict(r) for r in db.execute('SELECT * FROM svc_settings WHERE provider=?', (sid,)).fetchall()}
        mine = []
        for key in C.ORDER:
            s = C.SVC[key]
            started = bool((careers.get(s['career']) or {}).get('started'))
            row = settings.get((s['career'], s['service']))
            if not started and not row:
                continue
            q = sm.quote(db, sid, s['career'], s['service'], 1, setting=row)
            mine.append(dict(key=key, icon=s['icon'], name=s['name'], short=s['short'], career=s['career'], service=s['service'], can=started,
                             on=bool(row and row['on_']), mode=q['mode'], mult=q['mult'], price=q['price'] if q['price'] is not None else q['lo'],
                             npc=npc_price(key), unit=s['unit']))
        marks = ','.join('?' * len(C.SERVICES))
        rows = [dict(r) for r in db.execute(f"SELECT * FROM svc_orders WHERE provider=? AND kind='svc' AND service IN ({marks}) "
                                            'ORDER BY created_at DESC LIMIT 40', (sid, *sorted(C.SERVICES))).fetchall()]
        rows = [r for r in rows if (r['career'], r['service']) in C.PAIRS and (r['status'] in OPEN or r['updated_at'] > t - 7 * DAY)]
        jobs = _jobs(db, [r['id'] for r in rows])
        bare = [r for r in rows if r['status'] in ('held', 'working') and r['id'] not in jobs]
        if bare and not off():   # an order from the generic directory: its job (a rolled brief) is made on first sight
            store.transaction(lambda tx: [_ensure_job(tx, r, lock=False) for r in bare])
            jobs = _jobs(db, [r['id'] for r in rows])
        orders = []
        for r in rows:
            key = C.PAIRS[(r['career'], r['service'])]
            j = jobs.get(r['id'])
            buyer = ctx(db, r['buyer'], t)
            couple = buyer['c']
            names = ''
            if couple:
                names = f"{C.clean_name(mr._display(db, couple['a']))} & {C.clean_name(mr._display(db, couple['b']))}"
            note = sm._data(r).get('note', '')
            orders.append(dict(id=r['id'], svc=key, icon=C.SVC[key]['icon'], label=C.SVC[key]['short'], status=r['status'],
                               price=int(r['price'] or r['ask']), fee=sm.fee_of(int(r['price'] or r['ask'])), qty=int(r['qty']),
                               who=C.clean_name(mr._display(db, r['buyer'])), couple=names, when=buyer['when'], note=note,
                               due_at=r['due_at'], job=job_view(j) if j else None,
                               result=sm._data(r).get('result') if isinstance(sm._data(r).get('result'), dict) else None))
    return dict(ok=True, off=off(), mine=mine, orders=orders, rules=sm.rules(),
                careers=[dict(key=k, icon=C.SVC[k]['icon'], career=C.SVC[k]['career'], short=C.SVC[k]['short']) for k in C.ORDER])


# ---------------------------------------------------------------- writing
def hire(store, token, state, d: dict, ip: str = '') -> dict:
    """POST /api/wedsvc/hire {svc, pid, qty?, brief, rid, expected_price? | price (🤝 an offer), note?}: an order (or an
    offer) through Phố dịch vụ, then the couple's brief kept with it."""
    need(not off(), OFF_TEXT, 'wedsvc_off', 503)
    need(isinstance(d, dict) and set(d) <= {'svc', 'pid', 'qty', 'brief', 'rid', 'expected_price', 'price', 'note'}, 'Thông tin thuê dịch vụ không hợp lệ.')
    key = d.get('svc')
    need(key in C.SVC, 'Chọn một dịch vụ cưới nhé.', 'bad_svc')
    s = C.SVC[key]
    brief = clean_brief(key, d.get('brief'))
    qty = d.get('qty', 1)
    need(type(qty) is int and 1 <= qty <= s['qty_max'], 'Số lượng không hợp lệ.', 'bad_number')
    from . import work_visits
    extra = work_visits._clean(d.get('note') or '', 120) if d.get('note') else ''
    note = (C.brief_line(key, dict(brief, tables=qty) if key == 'tiec' else brief) + (' · ' + extra if extra else ''))[:NOTE_MAX]
    body = dict(pid=d.get('pid'), career=s['career'], service=s['service'], qty=qty, note=note, rid=d.get('rid'))
    if 'price' in d:
        out = sm.post(store, token, state, 'offer', dict(body, price=d['price']), ip)
    else:
        if 'expected_price' in d:
            body['expected_price'] = d['expected_price']
        out = sm.post(store, token, state, 'order', body, ip)
    oid = (out.get('order') or {}).get('id')
    sid = store.key(token)
    if oid:
        def keep(db):
            r = db.execute('SELECT * FROM svc_orders WHERE id=? AND buyer=?', (oid, sid)).fetchone()
            if r:
                c = mr._bond(db, sid)
                _ensure_job(db, dict(r), brief, c['id'] if c else None, lock=False)
        store.transaction(keep)
    return out


def deliver(store, sid: str, d: dict) -> dict:
    """POST /api/wedsvc/deliver {order}: hand the finished work over (service_market.deliver: the hook checks the job;
    'auto': the provider is paid at once, 95 %, 5 % burned)."""
    need(not off(), OFF_TEXT, 'wedsvc_off', 503)
    need(isinstance(d, dict) and set(d) <= {'order'}, 'Thông tin không hợp lệ.')
    oid = d.get('order')
    need(isinstance(oid, str) and sm.ID_RX.fullmatch(oid) and oid.startswith('sv_'), 'Không tìm thấy đơn.', 'not_found', 404)
    with store.connect() as db:
        r = db.execute('SELECT career, service, provider FROM svc_orders WHERE id=?', (oid,)).fetchone()
    need(r and r['provider'] == sid and (r['career'], r['service']) in C.PAIRS, 'Không tìm thấy đơn.', 'not_found', 404)
    view = sm.deliver(store, sid, oid)
    paid = view['status'] == 'done'
    return dict(order=view, changed=True,
                message=f'💒 Đã giao cho cô dâu chú rể. Bạn nhận {sm.fmt(view["paid"])} xu.' if paid else '💒 Đã giao. Tiền về ví ngay khi đối soát xong.')


def get(store, token, state, sub: str, q: dict) -> dict:
    sid = sm._actor(store, token)
    if sub == 'couple':
        return couple_view(store, sid, state)
    if sub == 'work':
        return work_view(store, sid, state)
    raise sm.ServiceError('Không có mục này.', 'not_found', 404)


def post(store, token, state, op: str, d: dict, ip: str = '') -> dict:
    sid = sm._actor(store, token)
    need(isinstance(d, dict), 'Dữ liệu không hợp lệ.')
    if op == 'hire':
        return hire(store, token, state, d, ip)
    if op == 'step':
        return step(store, sid, d)
    if op == 'deliver':
        return deliver(store, sid, d)
    if op == 'sell':   # 🧰 on / off at ×mult (the details stay in Phố dịch vụ › Dịch vụ của tôi)
        need(set(d) <= {'svc', 'on', 'mult'} and d.get('svc') in C.SVC, 'Thông tin không hợp lệ.')
        s = C.SVC[d['svc']]
        with store.connect() as db:
            row = db.execute('SELECT mode, mult FROM svc_settings WHERE provider=? AND career=? AND service=?', (sid, s['career'], s['service'])).fetchone()
        mult = d.get('mult', int(row['mult']) if row else sm.DEFAULT_MULT)
        out = sm.post(store, token, state, 'settings', dict(career=s['career'], service=s['service'], on=d.get('on') is True,
                                                            mode=row['mode'] if row else 'fixed', mult=mult), ip)
        return dict(changed=True, message=out.get('message', ''), work=work_view(store, sid, state))
    raise sm.ServiceError('Thao tác không hợp lệ.', 'unknown_action')
