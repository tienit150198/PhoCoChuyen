"""🔬 Đơn nghiên cứu: players order research from a player of the Viện nghiên cứu career (owner 21/10, "làm hết đi").

Three services in 🛎️ Phố dịch vụ (game/service_market.py, career 'research'), priced like every service there (NPC price
× 3 by default, the provider's ×1…×10 or thương lượng; 95 % to the researcher, 5 % burned; escrow, refunds, pair caps and
the anti-laundering rules are the market's):

* 🌱 giong · Giống cây cải tiến: the buyer's 🌟 Vườn mới (game/careers/farm_plus.py) gives +SEED_ADD unit on each of the
  next SEED_HARVESTS harvests (SEED_LOW below QUALITY_FULL), for at most SEED_DAYS real days.
* 🍳 mon · Công thức món mới: a finished order of the buyer's own food shop (FOOD careers) pays RECIPE_PCT % more (at least
  1 xu, at most RECIPE_PER xu a job) on the next RECIPE_USES jobs (RECIPE_LOW below QUALITY_FULL), RECIPE_CAP xu in all,
  for at most RECIPE_DAYS real days (game/engine.py task_done → recipe_bonus, into the career's fund like any earning).
* 🛠️ may · Đồ sáng chế: a one-off gadget with its inventor's name, shown in 📱 Mây Mobile → Của bạn (game/gadgets.py is
  untouched: it is cosmetic, it cannot be sold, it pays nothing). At most GADGET_MAX kept; a full shelf refuses new orders.

Bounds (tests/test_research_lab.py proves them): one active seed batch and one active recipe per buyer (a second order of
the same kind is refused while one is open or active), COOLDOWN_DAYS real days between two of the same kind, every
effect clamped again when it lands in the save. The most a service can ever add is max_value(): never more than its NPC
price (the buyer pays three times that by default), so an order never pays for itself, and a buyer–provider pair making
deals at ×1 nets at most that small amount once per cooldown.

The work: the provider takes the order (market inbox, or here), then does three research steps graded on the server (a
pure function of the order id, the same builders as the career's own jobs: research.BUILD), kept in research_jobs
(SCHEMA_VERSION 71). The last step delivers the order through the market (service_market.deliver, exactly once: the row's
status flips work → done under its lock, the market's order row flips working → ready under its own). The market's
generic "Xong việc" refuses until the three steps are done (the deliver hook raises). The effect reaches the buyer's
save in the market's settlement transaction (on_buyer, once; the order id is also kept in the block so it is never
applied twice).

Save: s['journey']['lab'] (optional; absent until the first effect lands; 2.4.66 keeps it unread: journey.validate
allows extra keys, tests/test_research_lab_compat.py). Nothing in the career record.

Kill switch MNL_RESEARCH_OFF=1: no new order, no listing, no research step, no delivery (open orders run out to the
market's refund), and the effects in saves pause (kept, not consumed). Bounded caches: none (each request reads its rows).
"""
from __future__ import annotations

import json
import os
import re
import time

from . import service_market as sm

CAREER = 'research'
VERSION = 1
QUALITY_FULL = 90
QUALITY_FLOOR = 60
WRONG_COST = 10
STEPS = 3                        # research steps of one order
COOLDOWN_DAYS = 3                # real days between two effects of the same kind for one buyer
DAY = 86400

SEED_ADD = 1                     # units added to one harvest
SEED_HARVESTS, SEED_LOW = 3, 2   # harvests boosted (full quality / below)
SEED_DAYS = 14
SEED_PRICE_MAX = 6               # crops whose chợ price is at most this (ớt, lúa, thanh long, dâu tây, xoài): the bound below
RECIPE_PCT = 10                  # % of a finished food job's pay
RECIPE_PER = 3                   # at most this many xu a job
RECIPE_USES, RECIPE_LOW = 12, 8
RECIPE_CAP = 30                  # xu in all, per recipe
RECIPE_DAYS = 7
GADGET_MAX = 12                  # kept on the shelf; a full shelf (with open orders counted) refuses a new order
GADGET_HARD = GADGET_MAX + sm.BUYER_OPEN   # what the validator accepts (racing orders never pass it)
ORDERS_KEPT = 40                 # applied order ids kept in the block (exactly once)
NAME_MAX = 32

FOOD = ('milk_tea', 'cafe_bakery', 'restaurant', 'pho', 'com', 'ice_cream', 'tra_da')
TRACK = dict(giong='seed', mon='recipe', may='invent')
JOB = dict(giong='cross', mon='scale', may='proto')
SERVICES = {
    'giong': dict(name='Giống cây cải tiến', icon='🌱', base=40, unit='lô giống', duration=60,
                  desc=f'Vườn mới (ớt, lúa, thanh long, dâu tây, xoài): +{SEED_ADD} sản lượng mỗi vụ thu, {SEED_HARVESTS} vụ tới (trong {SEED_DAYS} ngày).',
                  note_hint='Trồng gì nhiều nhất? (vd: dưa hấu, cà phê)'),
    'mon': dict(name='Công thức món mới', icon='🍳', base=40, unit='công thức', duration=60,
                desc=f'Quán ăn của bạn: khách trả thêm {RECIPE_PCT}% (tối đa {RECIPE_PER} xu một đơn), {RECIPE_USES} đơn tới, tổng tối đa {RECIPE_CAP} xu (trong {RECIPE_DAYS} ngày).',
                note_hint='Quán gì, món nào? (vd: quán phở, muốn nước dùng thơm hơn)'),
    'may': dict(name='Đồ sáng chế', icon='🛠️', base=60, unit='món đồ', duration=60,
                desc='Một món đồ công nghệ độc bản mang tên người sáng chế, để khoe trong Mây Mobile (không bán được).',
                note_hint='Muốn món đồ làm gì? (vd: quạt mini cho quầy)'),
}
KINDS = tuple(SERVICES)
STATS = ('seed_units', 'recipe_xu', 'gadgets')


def off() -> bool:
    return os.environ.get('MNL_RESEARCH_OFF') == '1'


def now() -> float:
    return sm.now()


def need(cond, message: str, code: str = 'lab_error', status: int = 400):
    sm.need(cond, message, code, status)


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _rs():
    from .careers import research as rs   # the career's own step builders (pure)
    return rs


# ---------------------------------------------------------------- the most a service can add (tests prove the caps)
def max_value(service: str) -> int:
    """The most xu an effect can ever bring its buyer (an upper bound, before the market's price)."""
    if service == 'giong':
        from .careers import farm_plus as fp
        # a unit's best price anywhere: the chợ (VietGAP × festival) or a buyer's order (premium up to 170 % + 15 %)
        mult = max(fp.GAP_PCT * fp.FEST_PCT // 100, 170 + 15)
        top = max(fp.CROP[cid]['price'] for cid in seed_crops()) * mult // 100 + 1
        return SEED_HARVESTS * SEED_ADD * top
    if service == 'mon':
        return min(RECIPE_CAP, RECIPE_USES * RECIPE_PER)
    return 0


def seed_crops() -> tuple:
    """The Vườn mới crops a seed batch boosts (game/careers/farm_plus.py CROPS at most SEED_PRICE_MAX xu a unit)."""
    from .careers import farm_plus as fp
    return tuple(c['id'] for c in fp.CROPS if c['price'] <= SEED_PRICE_MAX)


# ---------------------------------------------------------------- the buyer's block in the save
def initial() -> dict:
    return dict(v=VERSION, seed=None, recipe=None, gadgets=[], last={}, orders=[], stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    lab = j.get('lab') if isinstance(j, dict) else None
    return lab if isinstance(lab, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('lab'), dict):
        j['lab'] = initial()
    return j['lab']


def _int(v, lo, hi) -> bool:
    return type(v) is int and lo <= v <= hi


def _txt(v, n=NAME_MAX) -> bool:
    return isinstance(v, str) and len(v) <= n


SEED_KEYS = frozenset({'o', 'n', 'add', 'until', 'by', 'name'})
RECIPE_KEYS = frozenset({'o', 'n', 'pct', 'per', 'left', 'until', 'by', 'name'})
GADGET_KEYS = frozenset({'o', 'kind', 'name', 'by', 'at', 'q'})


def _seed_ok(x) -> bool:
    return (isinstance(x, dict) and set(x) == SEED_KEYS and _txt(x['o'], 40) and _int(x['n'], 0, SEED_HARVESTS)
            and _int(x['add'], 1, SEED_ADD) and _int(x['until'], 0, 10 ** 11) and _txt(x['by']) and _txt(x['name']))


def _recipe_ok(x) -> bool:
    return (isinstance(x, dict) and set(x) == RECIPE_KEYS and _txt(x['o'], 40) and _int(x['n'], 0, RECIPE_USES)
            and _int(x['pct'], 1, RECIPE_PCT) and _int(x['per'], 1, RECIPE_PER) and _int(x['left'], 0, RECIPE_CAP)
            and _int(x['until'], 0, 10 ** 11) and _txt(x['by']) and _txt(x['name']))


def _gadget_ok(x) -> bool:
    return (isinstance(x, dict) and set(x) == GADGET_KEYS and _txt(x['o'], 40) and _txt(x['kind'], 24) and _txt(x['name'])
            and _txt(x['by']) and _int(x['at'], 0, 10 ** 11) and _int(x['q'], 0, 100))


def validate(s: dict) -> None:
    """``s['journey']['lab']`` (optional). Raises GameError like validate_state."""
    from . import engine as e
    lab = get(s)
    j = s.get('journey')
    bad = 'Dữ liệu Viện nghiên cứu trong bản lưu không hợp lệ.'
    if lab is None:
        e.need(not isinstance(j, dict) or j.get('lab') is None, bad, 'invalid_save')
        return
    e.need(set(lab) == set(initial()) and lab['v'] == VERSION, bad, 'invalid_save')
    e.need(lab['seed'] is None or _seed_ok(lab['seed']), bad, 'invalid_save')
    e.need(lab['recipe'] is None or _recipe_ok(lab['recipe']), bad, 'invalid_save')
    e.need(isinstance(lab['gadgets'], list) and len(lab['gadgets']) <= GADGET_HARD and all(_gadget_ok(g) for g in lab['gadgets']), bad, 'invalid_save')
    e.need(isinstance(lab['last'], dict) and set(lab['last']) <= set(KINDS) and all(_int(v, 0, 10 ** 11) for v in lab['last'].values()), bad, 'invalid_save')
    e.need(isinstance(lab['orders'], list) and len(lab['orders']) <= ORDERS_KEPT and all(_txt(o, 40) for o in lab['orders']), bad, 'invalid_save')
    st = lab['stats']
    e.need(isinstance(st, dict) and set(st) == set(STATS) and all(_int(v, 0, 10 ** 9) for v in st.values()), bad, 'invalid_save')


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep what still makes sense. Absent stays absent."""
    if not isinstance(j, dict) or 'lab' not in j:
        return
    lab = j['lab']
    if not isinstance(lab, dict):
        j['lab'] = initial()
        return
    out = initial()
    out['seed'] = lab.get('seed') if _seed_ok(lab.get('seed')) else None
    out['recipe'] = lab.get('recipe') if _recipe_ok(lab.get('recipe')) else None
    out['gadgets'] = [g for g in (lab.get('gadgets') if isinstance(lab.get('gadgets'), list) else []) if _gadget_ok(g)][:GADGET_HARD]
    last = lab.get('last') if isinstance(lab.get('last'), dict) else {}
    out['last'] = {k: v for k, v in last.items() if k in KINDS and _int(v, 0, 10 ** 11)}
    orders = lab.get('orders') if isinstance(lab.get('orders'), list) else []
    out['orders'] = [o for o in orders if _txt(o, 40)][-ORDERS_KEPT:]
    st = lab.get('stats') if isinstance(lab.get('stats'), dict) else {}
    out['stats'] = {k: st[k] if _int(st.get(k), 0, 10 ** 9) else 0 for k in STATS}
    if out != lab:
        j['lab'] = out


def _live(x, t) -> bool:
    return bool(x) and x['n'] > 0 and x['until'] > t and (x.get('left', 1) > 0)


def public(s: dict) -> dict | None:
    """What the buyer sees (journey public 'lab'): the running effects and the gadgets."""
    lab = get(s)
    if lab is None:
        return None
    t = int(now())
    seed, rec = lab['seed'], lab['recipe']
    return dict(
        seed=dict(name=seed['name'], by=seed['by'], left=seed['n'], add=seed['add'], until=seed['until']) if _live(seed, t) else None,
        recipe=dict(name=rec['name'], by=rec['by'], left=rec['n'], pct=rec['pct'], per=rec['per'], xu=rec['left'], until=rec['until']) if _live(rec, t) else None,
        gadgets=[dict(kind=g['kind'], name=g['name'], by=g['by'], at=g['at'], q=g['q'], emoji=_gadget_emoji(g['kind'])) for g in lab['gadgets']],
        paused=off(), stats=dict(lab['stats']))


def _gadget_emoji(kind: str) -> str:
    return dict(fan='🪭', lamp='💡', water='💧', bell='🔔', box='🍱', solar='🌞').get(kind, '🛠️')


# ---------------------------------------------------------------- effects at work (engine side, pure on the save)
def seed_bonus(s: dict, room: int, crop: str = '') -> tuple:
    """🌱 One Vườn mới harvest of `crop`: (extra units, note). Uses one boosted harvest when one is running, the crop is
    one the batch boosts and there is room."""
    lab = get(s)
    if lab is None or off() or crop not in seed_crops():
        return 0, ''
    x = lab['seed']
    from .careers import kit
    t = int(kit.now())
    if not _live(x, t):
        if x and (x['n'] <= 0 or x['until'] <= t):
            lab['seed'] = None
        return 0, ''
    add = min(x['add'], SEED_ADD)
    if room < add:
        return 0, ''
    x['n'] -= 1
    lab['stats']['seed_units'] = min(10 ** 9, lab['stats']['seed_units'] + add)
    left = x['n']
    if left <= 0:
        lab['seed'] = None
    return add, f'🌱 +{add} nhờ giống «{x["name"]}» của Viện' + (f' (còn {left} vụ).' if left else ' (vụ cuối).')


def recipe_bonus(s: dict, c: dict, t: dict, reward: int) -> int:
    """🍳 A finished food job: the recipe's extra pay (into the career's fund, like the job's pay). Returns the xu added."""
    if t.get('career') not in FOOD or type(reward) is not int or reward <= 0 or off():
        return 0
    lab = get(s)
    if lab is None or lab['recipe'] is None:
        return 0
    x = lab['recipe']
    from .careers import kit
    now_ = int(kit.now())
    if not _live(x, now_):
        lab['recipe'] = None
        return 0
    bonus = min(x['per'], RECIPE_PER, x['left'], max(1, reward * min(x['pct'], RECIPE_PCT) // 100))
    if bonus <= 0:
        lab['recipe'] = None
        return 0
    from . import engine
    engine.money(s, c, bonus, f'🍳 Công thức «{x["name"]}» của Viện: khách trả thêm', t.get('id'), 'revenue')
    x['n'] -= 1
    x['left'] -= bonus
    lab['stats']['recipe_xu'] = min(10 ** 9, lab['stats']['recipe_xu'] + bonus)
    if x['n'] <= 0 or x['left'] <= 0:
        lab['recipe'] = None
    return bonus


# ---------------------------------------------------------------- the research work of one order (pure by order id)
def brief(order_id: str, service: str) -> tuple:
    """(steps, key, extra) of an order: the first STEPS steps of the career's own job of that track."""
    from .careers import kit
    rs = _rs()
    job = JOB[service]
    b, key, title, opening, npc = rs.BUILD[job](kit.rng('research-order', order_id, service), 1, 0)
    steps = b['steps'][:STEPS]
    extra = dict(title=title, gadget=next((g[0] for g in _rs().rc.GADGETS if g[1] == b.get('gadget')), 'fan'))
    return steps, {st['id']: key[st['id']] for st in steps}, extra


def quality(wrong: int) -> int:
    return max(QUALITY_FLOOR, 100 - WRONG_COST * wrong)


def _job_row(db, oid: str, lock: bool = False):
    r = db.execute('SELECT * FROM research_jobs WHERE order_id=?' + (' FOR UPDATE' if lock else ''), (oid,)).fetchone()
    return dict(r) if r else None


def _default_name(service: str, oid: str) -> str:
    n = int(oid[-4:], 16) % 90 + 10
    return dict(giong=f'Mây-{n}', mon=f'Công thức SM-{n}', may='')[service]


def _clean_name(v) -> str:
    v = re.sub(r'\s+', ' ', str(v or '')).strip()
    v = ''.join(ch for ch in v if ch.isprintable())
    return v[:24]


# ---------------------------------------------------------------- market hooks
def _base(service):
    return SERVICES[service]['base']


def _can_provide(state) -> str:
    if off():
        return 'Viện nghiên cứu tạm nghỉ nhận đơn.'
    c = (state.get('careers') or {}).get(CAREER)
    if not (isinstance(c, dict) and c.get('started')):
        return 'Bạn cần làm ở Viện nghiên cứu trước đã.'
    if not (isinstance(c.get('job'), dict) and c['job'].get('status') == 'hired'):
        return 'Ứng tuyển vào Viện nghiên cứu Sông Mây trước đã.'
    return ''


def _open_of(db, buyer: str, service: str) -> int:
    return db.execute("SELECT COUNT(*) AS n FROM svc_orders WHERE buyer=? AND career=? AND service=? AND status IN "
                      "('talk','held','working','delivered','ready')", (buyer, CAREER, service)).fetchone()['n']


def _check(service):
    def check(db, buyer, state) -> str:
        if off():
            return 'Viện nghiên cứu tạm nghỉ nhận đơn.'
        lab = get(state) or initial()
        t = int(now())
        careers = state.get('careers') or {}
        if service == 'giong':
            farm = careers.get('farm')
            if not (isinstance(farm, dict) and farm.get('started') and isinstance((farm.get('ext') or {}).get('farm_plus'), dict)):
                return 'Giống cải tiến dùng cho 🌟 Vườn mới ở Trang trại. Mở Vườn mới trước đã.'
            if _live(lab['seed'], t):
                return 'Vườn mới đang dùng một lô giống của Viện. Dùng hết rồi đặt tiếp nhé.'
        if service == 'mon':
            if not any(isinstance(careers.get(cid), dict) and careers[cid].get('started') for cid in FOOD):
                return 'Công thức món dùng cho quán ăn của bạn (trà sữa, bánh, mì cay, phở, cơm, kem, trà đá). Mở quán trước đã.'
            if _live(lab['recipe'], t):
                return 'Quán đang dùng một công thức của Viện. Dùng hết rồi đặt tiếp nhé.'
        if service in ('giong', 'mon') and _open_of(db, buyer, service):
            return 'Bạn đã có một đơn loại này đang chờ Viện làm.'
        if service == 'may' and len(lab['gadgets']) + _open_of(db, buyer, service) >= GADGET_MAX:
            return f'Tủ đồ sáng chế đã đầy ({GADGET_MAX} món).'
        last = lab['last'].get(service, 0)
        if last and t - last < COOLDOWN_DAYS * DAY:
            left = COOLDOWN_DAYS * DAY - (t - last)
            return f'Mỗi {COOLDOWN_DAYS} ngày đặt một {SERVICES[service]["unit"]} thôi. Còn khoảng {max(1, -(-left // 3600))} giờ nữa.'
        return ''
    return check


def _deliver(service):
    def deliver(db, provider, buyer, order) -> dict:
        need(not off(), 'Viện nghiên cứu tạm nghỉ, chưa giao được.', 'lab_off', 409)
        row = _job_row(db, order['id'], lock=True)
        need(row and row['status'] == 'done' and row['provider'] == provider,
             'Làm xong ba bước nghiên cứu ở Viện rồi mới giao được.', 'lab_not_done', 409)
        q = int(row['quality'])
        name = row['name'] or _default_name(service, order['id'])
        full = q >= QUALITY_FULL
        by = str(sm._person(db, provider).get('name') or '')[:NAME_MAX]
        if service == 'giong':
            n = SEED_HARVESTS if full else SEED_LOW
            return dict(text=f'🌱 Giống «{name}»: +{SEED_ADD} sản lượng mỗi vụ, {n} vụ thu tới ở Vườn mới (trong {SEED_DAYS} ngày).',
                        quality=f'{q}%', by=by, kind='giong', name=name, n=n, add=SEED_ADD, days=SEED_DAYS)
        if service == 'mon':
            n = RECIPE_USES if full else RECIPE_LOW
            return dict(text=f'🍳 Công thức «{name}»: khách trả thêm {RECIPE_PCT}% (tối đa {RECIPE_PER} xu một đơn), {n} đơn tới, tổng tối đa {RECIPE_CAP} xu (trong {RECIPE_DAYS} ngày).',
                        quality=f'{q}%', by=by, kind='mon', name=name, n=n, pct=RECIPE_PCT, per=RECIPE_PER, cap=RECIPE_CAP, days=RECIPE_DAYS)
        extra = json.loads(row['data'] or '{}')
        kind = extra.get('gadget') if extra.get('gadget') in {g[0] for g in _rs().rc.GADGETS} else 'fan'
        label = next(g[1] for g in _rs().rc.GADGETS if g[0] == kind)
        name = row['name'] or label
        return dict(text=f'🛠️ Đồ sáng chế «{name}» ({label.lower()}): vào 📱 Mây Mobile → Của bạn.' + ('' if full else ' Bản thử nghiệm.'),
                    quality=f'{q}%', by=by, kind='may', name=name, gadget=kind)
    return deliver


def _on_buyer(service):
    def on_buyer(state, order) -> None:
        """In the settlement transaction (once). Never raises: every number is clamped to the caps again."""
        j = state.get('journey') if isinstance(state.get('journey'), dict) else None
        if j is None:
            return
        lab = _ensure(state)
        if order['id'] in lab['orders']:
            return
        res = order.get('result') if isinstance(order.get('result'), dict) else {}
        t = int(now())
        by = (str(res.get('by') or '')[:NAME_MAX]) or 'Viện Sông Mây'
        name = _clean_name(res.get('name')) or _default_name(service, order['id']) or 'Viện Sông Mây'
        if service == 'giong':
            n = max(0, min(SEED_HARVESTS, int(res.get('n') or 0) if type(res.get('n')) is int else 0))
            new = dict(o=order['id'], n=n, add=SEED_ADD, until=t + SEED_DAYS * DAY, by=by, name=name)
            cur = lab['seed']
            if _live(cur, t):   # two racing orders: the stronger one, never the sum
                new = dict(new, n=max(cur['n'], n), until=max(cur['until'], new['until']))
            lab['seed'] = new if new['n'] > 0 else cur
        elif service == 'mon':
            n = max(0, min(RECIPE_USES, int(res.get('n') or 0) if type(res.get('n')) is int else 0))
            new = dict(o=order['id'], n=n, pct=RECIPE_PCT, per=RECIPE_PER, left=RECIPE_CAP, until=t + RECIPE_DAYS * DAY, by=by, name=name)
            cur = lab['recipe']
            if _live(cur, t):
                new = dict(new, n=max(cur['n'], n), left=max(cur['left'], RECIPE_CAP), until=max(cur['until'], new['until']))
            lab['recipe'] = new if new['n'] > 0 else cur
        else:
            kinds = {g[0] for g in _rs().rc.GADGETS}
            kind = res.get('gadget') if res.get('gadget') in kinds else 'fan'
            q = int(str(res.get('quality') or '0').rstrip('%') or 0) if str(res.get('quality') or '0').rstrip('%').isdigit() else 0
            if len(lab['gadgets']) < GADGET_HARD:
                lab['gadgets'].append(dict(o=order['id'], kind=kind, name=name, by=by, at=t, q=max(0, min(100, q))))
                lab['stats']['gadgets'] = min(10 ** 9, lab['stats']['gadgets'] + 1)
        lab['last'][service] = t
        lab['orders'] = (lab['orders'] + [order['id']])[-ORDERS_KEPT:]
    return on_buyer


_installed = [False]


def install() -> bool:
    """Register the three services with the market (idempotent; at import and at server start)."""
    for sid, sp in SERVICES.items():
        sm.register(CAREER, sid, dict(name=sp['name'], icon=sp['icon'], desc=sp['desc'], base=sp['base'], unit=sp['unit'],
                                      duration=sp['duration'], note_hint=sp['note_hint'], work_hours=48, confirm='auto',
                                      requires=dict(story=True), check=_check(sid), can_provide=_can_provide,
                                      deliver=_deliver(sid), on_buyer=_on_buyer(sid)))
    _installed[0] = True
    return True


# ---------------------------------------------------------------- HTTP: /api/lab/…
def _actor(store, token) -> str:
    return sm._actor(store, token)


def _public_step(st: dict) -> dict:
    return {k: v for k, v in st.items()}


def _order_view(db, o: dict) -> dict:
    row = _job_row(db, o['id'])
    steps, _, extra = brief(o['id'], o['service'])
    at = row['at'] if row else 0
    sp = SERVICES.get(o['service'], {})
    return dict(id=o['id'], service=o['service'], name=sp.get('name', ''), icon=sp.get('icon', '🔬'), status=o['status'],
                note=o.get('note', ''), price=o['price'], qty=o['qty'], buyer=sm._person(db, o['buyer']).get('name', ''),
                title=extra['title'], at=at, total=len(steps), done=bool(row and row['status'] == 'done'),
                wrong=row['wrong'] if row else 0, quality=quality(row['wrong'] if row else 0),
                step=_public_step(steps[at]) if at < len(steps) else None, label=(row or {}).get('name', ''))


def orders(store, sid: str) -> dict:
    with store.connect() as db:
        rows = sm.open_orders(db, sid, CAREER)
        return dict(orders=[_order_view(db, o) for o in rows if o['service'] in SERVICES], off=off(),
                    services=[dict(id=k, name=v['name'], icon=v['icon'], desc=v['desc'], base=v['base']) for k, v in SERVICES.items()])


def get_(store, token, state, sub: str, query: dict) -> dict:
    sid = _actor(store, token)
    if sub in ('', 'orders'):
        return orders(store, sid)
    if sub == 'mine':
        loaded = state if state is not None else (sm.mr._read_state(store, sid) or [None])[0]
        return dict(lab=public(loaded) if loaded else None, off=off())
    raise sm.ServiceError('Không có mục này.', 'not_found', 404)


def _step(store, sid: str, data: dict) -> dict:
    need(set(data) <= {'order', 'step', 'value', 'name'}, 'Thông tin không hợp lệ.')
    need(not off(), 'Viện nghiên cứu tạm nghỉ.', 'lab_off', 409)
    oid = data.get('order')
    need(isinstance(oid, str) and sm.ID_RX.fullmatch(oid), 'Không tìm thấy đơn.', 'not_found', 404)
    t = now()
    out = {}

    def run(db):
        cur = db.execute('SELECT * FROM svc_orders WHERE id=? FOR UPDATE', (oid,)).fetchone()
        need(cur and cur['provider'] == sid and cur['career'] == CAREER and cur['service'] in SERVICES, 'Không tìm thấy đơn.', 'not_found', 404)
        need(cur['status'] == 'working', 'Nhận đơn trước rồi mới làm được.' if cur['status'] == 'held' else 'Đơn không còn chờ làm.', 'not_working', 409)
        steps, key, extra = brief(oid, cur['service'])
        row = _job_row(db, oid, lock=True)
        if row is None:
            db.execute('INSERT INTO research_jobs(order_id,provider,buyer,service,at,wrong,status,name,data,created_at,updated_at) '
                       "VALUES(?,?,?,?,0,0,'work','',?,?,?) ON CONFLICT DO NOTHING",
                       (oid, sid, cur['buyer'], cur['service'], _json(dict(gadget=extra['gadget'])), t, t))
            row = _job_row(db, oid, lock=True)
        if row['status'] == 'done':
            out.update(done=True, message='Đã xong ba bước, đang giao kết quả.')
            return
        st = steps[row['at']]
        need(data.get('step') == st['id'], 'Làm theo bước đang mở nhé.', 'stale_step', 409)
        value = _rs()._value(st, data.get('value'))
        if not _rs()._same(value, key[st['id']]):
            db.execute('UPDATE research_jobs SET wrong=wrong+1, updated_at=? WHERE order_id=? AND at=?', (t, oid, row['at']))
            how = _rs().HOW.get(st['id'], 'Đọc lại phiếu rồi làm lại bước này.')
            out.update(correct=False, message=f'Chưa đúng: {st["title"].lower()}. {how}')
            return
        at = row['at'] + 1
        done = at >= len(steps)
        name = _clean_name(data.get('name')) if done else ''
        n = db.execute("UPDATE research_jobs SET at=?, status=?, name=?, quality=?, updated_at=? WHERE order_id=? AND at=? AND status='work'",
                       (at, 'done' if done else 'work', name, quality(row['wrong']), t, oid, row['at'])).rowcount
        need(n == 1, 'Bước này vừa được ghi rồi.', 'stale_step', 409)
        out.update(correct=True, done=done, message='Xong ba bước nghiên cứu! Đang giao kết quả cho khách.' if done else
                   'Đúng rồi. Tiếp: ' + steps[at]['title'].lower() + '.')
    store.transaction(run)
    if out.get('done'):
        view = sm.deliver(store, sid, oid)
        out['order'] = view
        out['message'] = 'Đã giao kết quả nghiên cứu, tiền công vào ví.' if view.get('status') == 'done' else out['message']
    out.update(orders(store, sid))
    return out


def post(store, token, state, sub: str, data: dict, ip: str = '') -> dict:
    sid = _actor(store, token)
    data = data if isinstance(data, dict) else {}
    if sub == 'take':
        need(not off(), 'Viện nghiên cứu tạm nghỉ.', 'lab_off', 409)
        r = sm.post(store, token, state, 'take', dict(order=data.get('order')), ip=ip)
        return dict(r, **orders(store, sid))
    if sub == 'step':
        return _step(store, sid, data)
    raise sm.ServiceError('Không có thao tác này.', 'not_found', 404)


install()
