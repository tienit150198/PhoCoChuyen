"""🛡️ Rủi ro & bảo hiểm: the street's everyday bad luck, always warned first, with insurance and prevention that work.

Owner 03/10 (docs/ECONOMY_RISKS.md): the xu come in faster than they go (x3 weeks, the fair, staff bonuses), so life
should cost something now and then: "đầu tư hoặc mất tiền bởi trộm, ốm đau, hỏng xe, sửa nhà", "tăng thêm rủi ro", and
then "cho người ta chơi thoải mái tí và có cảm giác happy tí". So the losses are real and more frequent than the first
draft, but fair:

* Warned first. Every event starts as a warning (`warn`) one or two life days ahead, with a prevention that works:
  a checkup, a repair man, putting the cash in the bank, a lock (PREVENT_PCT % of what the event would cost, covered by
  the insurance like the event). Then, if nothing was done, a story card (`card`) with a choice: pay more and be done,
  pay less and lose some tinh thần, or leave it for later (a broken vehicle cannot be taken out, a broken home loses
  its Ấm cúng bonus). Street thefts take cash; a bank hack takes only the current account balance.
* Capped. W = cash + bank account + savings (bank and Mây) + gold. Nothing happens while W < FLOOR; an event costs at
  most EVENT_PCT % of (W − FLOOR); a tháng (MONTH_DAYS life days) at most MONTH_PCT % of (W − FLOOR) at its start,
  MONTH_EVENTS events and one every GAP life days at most. Never a debt: cash, then the bank account, the rest waived.
* New players are left alone: nothing before life day START_DAY and chapter START_CHAPTER, and nothing in the QUIET
  life days after this build first meets a save (an intro line says what is coming).
* Rolled only on the player's own life-day tick (journey.after, after the bank, the homes and the month's bills):
  life days move only when the player closes a shift, so an offline player never loses anything. A save that comes
  back from an older build is not back-filled: only the last life day is looked at.
* Insurance (`pol`, per tháng, accrued a day at a time and billed every MONTH_DAYS life days like game/upkeep.py, wallet
  kind 'upkeep'): 🩺 BHYT, 🚗 xe (a share of the motor vehicles' price), 🏠 nhà (a share of the homes' price). Each pays
  COVER % of what its kind costs (prevention included) for an event first warned at least WAIT life days after it was
  switched on. A bill the wallet and the account cannot pay switches the policies off (never a debt).
* Đồ phòng thân (`gear`, bought once): 👜 túi đeo chéo (móc túi ×½), 🔐 khóa chống trộm (trộm ×0,4), 🗄️ két sắt
  (a burglary takes a quarter), 🧯 bình chữa cháy (a kitchen fire costs a third).
* Integration with the month's bills (game/upkeep.py): a vehicle or a home whose bill could not be paid (waived) is
  twice as likely to break for 10 life days; a home in poor repair (game/reno.py, condition < WORN_AT) twice, a home
  with every part upgraded half. Repairing a home part brings it back to 100; leaving it lowers it (reno shows the
  flaw) and pauses the Ấm cúng bonus until it is fixed here or in Sửa nhà. A company's BHYT (a promotion, job.promo
  rank ≥ 1, when a build has it) covers illness like BHYT.

Kinds (KINDS, ids stored in saves: never rename): xe (a motor vehicle breaks), nha (a home: dột, vỡ ống, chập điện,
cháy bếp, ngập), om (ill), moc (pickpocket: cash or the phone), trom (burglary: cash at home), phat (a parking fine
while driving a car; the first one is only a warning), hack (a compromised bank account).

Money moves through the wallet with kinds every older build accepts (journey.HISTORY_KINDS of 1.4.31): 'life'
(vehicles, health, gear), 'home' (homes), 'incident' (thefts, fines, money the police find), 'upkeep' (premiums).
Counters live in this block, not in journey STATS.

State journey['rui'] (optional; journey.validate of older builds allows extra keys, so an older server keeps it and
does nothing; unknown fields a newer build adds are kept):
    v, since, day        version, the life day this block began, the last life day ticked
    next_ok              the first life day a new warning may come
    month                {i: tháng index, w: W − FLOOR at its start, lost: xu paid for events, n: events}
    warn                 {kind, sub, ref, day (it happens that morning), at (warned on), cost} or None
    card                 {id, kind, sub, ref, day, cost, loss, cover} or None
    pol                  {policy id: the life day it was switched on}
    acc                  thousandths of a xu of premiums accrued, not billed yet
    gear                 [gear ids]
    waived               the last life day a month's bill was waived (game/upkeep.py), 0: never
    broken               {xe: {vid: {c: cost, d: day}}, nha: {home id: {p: reno part, c: cost, d: day}}}
    sick, fines          the life day of the last illness (0), parking fines so far
    back                 {day, amount} the police bring back on that morning, or None
    seq, log, stats      card ids; the last LOG_MAX lines; counters (STATS)
Commands (journey.action, the jr_rui_ prefix): jr_rui_prevent {opt}, jr_rui_choose {id, choice}, jr_rui_pol {id, on},
jr_rui_gear {id}, jr_rui_fix {kind, ref}. Deterministic: every draw is seeded by the journey seed and the life day.
"""
from __future__ import annotations

import hashlib
import random

from . import archive as ar
from . import bank as bk

VERSION = 1
KEY = 'rui'
MONTH_DAYS = bk.MONTH_DAYS        # 5 life days
START_DAY, START_CHAPTER = 15, 3  # new players: nothing before
QUIET = 3                         # life days after this build first meets a save: nothing rolled
EASE_DAY, EASE_W = 30, 1500       # before this life day, or with less W: half the odds (new and poor players)
FLOOR = 300                       # W below this: nothing happens; losses come out of what is above it
EVENT_PCT, MONTH_PCT = 8, 12      # caps, % of W − FLOOR
MONTH_EVENTS = 2
GAP = 3                           # life days between two warnings at least
CARD_DAYS = 3                     # a card not answered takes its default choice after this many life days
WAIT = 3                          # a policy covers events first warned this many life days after it began
PREVENT_PCT = 20                  # a prevention costs this share of the event
MIN_COST = 5                      # an event that would cost less does not happen
WAIVED_DAYS = 10                  # a waived month's bill doubles the odds this long
SICK_GAP = 10
LOG_MAX = 20
ACC_MAX = 10**12
LEAD = (1, 2)                     # life days from the warning to the event

KINDS = ('xe', 'nha', 'om', 'moc', 'trom', 'phat', 'hack')
STATS = ('warned', 'prevented', 'events', 'paid', 'covered', 'lost', 'waived', 'premiums', 'gear', 'back', 'fizzled')
WALLET = dict(xe='life', nha='home', om='life', moc='life', trom='incident', phat='incident', pol='upkeep', gear='life')

# Policies: id -> (emoji, name, what it covers, cover %, premium: ('flat', xu a tháng) | ('bp', basis points a tháng
# of the price of what it insures)).
POLICIES = {
    'yte': dict(emoji='🩺', name='Bảo hiểm y tế', what='Ốm đau, khám bệnh', cover=80, flat=3, bp=3, most=60),
    'xe': dict(emoji='🚗', name='Bảo hiểm xe', what='Xe hỏng, sửa xe', cover=80, bp=25),
    'nha': dict(emoji='🏠', name='Bảo hiểm nhà', what='Dột, vỡ ống, chập điện, cháy, ngập', cover=80, bp=8),
}
POLICY_OF = dict(om='yte', xe='xe', nha='nha')

GEAR = {
    'tui': dict(emoji='👜', name='Túi đeo chéo', price=40, what='Móc túi giảm một nửa'),
    'khoa': dict(emoji='🔐', name='Khóa chống trộm', price=150, what='Trộm vào nhà giảm 60%'),
    'ket': dict(emoji='🗄️', name='Két sắt mini', price=500, what='Trộm chỉ lấy được 1/4'),
    'binh': dict(emoji='🧯', name='Bình chữa cháy', price=120, what='Cháy bếp chỉ thiệt 1/3'),
}

# ---------------------------------------------------------------- odds and costs
XE_P = (400, 120)                 # per 10 000 after an actual outing: displayed vehicle / another vehicle
XE_PCT = 400                      # repair: basis points of the price paid
NHA_P = 200                       # a home you own, per 10 000 a life day
NHA_SUBS = {   # sub: (weight, reno part, basis points of the list price)
    'dot': (30, 'roof', 120), 'ong': (30, 'power', 100), 'dien': (20, 'power', 150),
    'chay': (10, 'kitchen', 300), 'ngap': (10, 'floor', 250),
}
NGAP_GROUPS = ('townhouse', 'villa')   # a flat high up does not flood
OM_P = (100, 200, 100)            # per 10 000: everyone, + no bụng or tỉnh táo low, + tinh thần < 35
OM_PCT, OM_MIN, OM_MAX = 150, 30, 600   # the clinic: basis points of W − FLOOR, clamped
THUOC = 15                        # medicine from the pharmacy
THUOC_LAI = 30                    # % it does not help: a second card two days later
MOC_P, MOC_RICH = 120, 3000       # per 10 000 with cash ≥ FLOOR + 100; ×1,5 with more cash than MOC_RICH
MOC_PCT, MOC_MAX = 12, 2000       # % of the cash above FLOOR, at most
DT_PCT, DT_MIN, DT_MAX = 100, 40, 500   # a new phone: basis points of W − FLOOR, clamped
TROM_P, TROM_CASH = 100, 600      # per 10 000, with cash ≥ TROM_CASH, living in a home or a rented room
TROM_PCT, TROM_MAX = 20, 4000
HACK_P, HACK_PCT, HACK_MAX = 120, 8, 3000  # per 10 000; current account only, before shared risk caps
PHAT_P = 200                      # per 10 000 a life day while driving a car
PHAT_BP, PHAT_MIN, PHAT_MAX = 30, 20, 300
BAO_BACK = 30                     # % the police find the money (half of it), BACK_DAYS later
BACK_DAYS = 2
XIN_OK, XIN_MORE = 30, 150        # "xin bỏ qua": % waived; else the fine × XIN_MORE / 100
SPIRIT = dict(tu_xe=-8, tu_nha=-10, thuoc=-4, nghi=-12, nghi_lai=-8, cu=-6)

KIND_META = {
    'xe': ('🔧', 'Xe hỏng'), 'nha': ('🏚️', 'Nhà gặp sự cố'), 'om': ('🤒', 'Ốm'),
    'moc': ('👛', 'Móc túi'), 'trom': ('🔓', 'Trộm vào nhà'), 'phat': ('🚓', 'Phạt đỗ xe'),
    'hack': ('🔐', 'Tài khoản ngân hàng bị hack'),
}
XE_WARN = {'bike': 'Xe kêu lạch cạch, phanh hơi lỏng.', 'car': 'Đèn báo động cơ cứ chớp tắt.',
           'boat': 'Máy thuyền nổ không đều.', 'plane': 'Thợ máy báo cánh tà hơi kẹt.'}
XE_TEXT = {'bike': 'Xe chết máy giữa đường.', 'car': 'Xe báo lỗi, phải kéo về xưởng.',
           'boat': 'Thuyền hỏng máy ngoài bến.', 'plane': 'Máy bay phải nằm xưởng.'}
NHA_TEXT = {   # sub: (emoji, title, the event, the warning)
    'dot': ('☔', 'Trần nhà dột', 'Mưa đêm qua, nước nhỏ giọt xuống sàn.', 'Trần có vết ố nâu loang ra.'),
    'ong': ('🚿', 'Vỡ ống nước', 'Ống nước âm tường vỡ, sàn ướt sũng.', 'Tường ẩm, đồng hồ nước cứ quay.'),
    'dien': ('⚡', 'Chập điện', 'Cầu dao nhảy, một đoạn dây cháy đen.', 'Ổ điện hơi nóng, đèn chớp chớp.'),
    'chay': ('🔥', 'Cháy bếp', 'Chảo dầu bén lửa, tủ bếp cháy sém.', 'Bếp có mùi khét lạ.'),
    'ngap': ('🌊', 'Nhà bị ngập', 'Mưa lớn, nước tràn vào nhà.', 'Sắp mưa to, cống trước nhà đầy rác.'),
}
OM_TEXT = {
    'cam': ('🤒', 'Bị cảm sốt', 'Sáng dậy người nóng ran, đầu nặng trĩu.'),
    'bung': ('🤢', 'Đau bụng', 'Hôm qua ăn quán lạ, giờ bụng quặn từng cơn.'),
    'lung': ('🩹', 'Đau lưng', 'Bê đồ nặng, sáng nay cúi không nổi.'),
    'lai': ('🤧', 'Vẫn chưa khỏi', 'Thuốc không đỡ, người vẫn mệt rã rời.'),
}


def _jr():
    from . import journey
    return journey


def _core():
    from . import engine
    return engine


def _fmt(n: int) -> str:
    return bk._fmt(n)


def _lname(name: str) -> str:
    return name[:1].lower() + name[1:]


def _ceil_pct(x: int, pct: int) -> int:
    return -(-int(x) * pct // 100)


def _rng(s: dict, what: str, day: int) -> random.Random:
    seed = s['journey'].get('seed', 0)
    h = hashlib.sha256(f'rui|{seed}|{what}|{day}'.encode()).digest()
    return random.Random(int.from_bytes(h[:8], 'big'))


# ---------------------------------------------------------------- the block
def initial(day: int) -> dict:
    return dict(v=VERSION, since=int(day), day=int(day), next_ok=int(day) + QUIET, month=dict(i=-1, w=0, lost=0, n=0),
                warn=None, card=None, pol={}, acc=0, gear=[], waived=0, broken=dict(xe={}, nha={}), sick=0, fines=0,
                back=None, seq=0, log=[], stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    r = j.get(KEY) if isinstance(j, dict) else None
    return r if isinstance(r, dict) else None


def _log(r: dict, day: int, text: str, amt: int = 0) -> None:
    r['log'] = ar.last(r['log'] + [dict(d=int(day), t=text[:120], a=int(amt))], LOG_MAX, 'rui.log', ar.JOURNEY)


def _stat(r: dict, k: str, n: int = 1) -> None:
    r['stats'][k] = min(10**9, r['stats'].get(k, 0) + max(0, int(n)))


# ---------------------------------------------------------------- what the player has
def wealth(s: dict) -> int:
    """W: the cash in the wallet (never below 0), the bank account and savings, the Mây savings, the gold (sell price)."""
    j = s['journey']
    w = max(0, j['wallet'])
    b = bk.get(s)
    if b:
        w += b['balance'] + b['demand'] + sum(t['amount'] for t in b['terms'])
    iv = j.get('invest')
    if isinstance(iv, dict) and isinstance(iv.get('saving'), dict):
        w += max(0, int(iv['saving'].get('balance') or 0))
    from . import vang
    w += vang.value(s)
    return w


def room(s: dict) -> int:
    """W − FLOOR (0 below the floor): what the caps are taken from."""
    return max(0, wealth(s) - FLOOR)


def _have(s: dict) -> int:
    """What a payment may use now: the cash and the bank account."""
    b = bk.get(s)
    return max(0, s['journey']['wallet']) + (b['balance'] if b else 0)


def _take(s: dict, amount: int, kind: str, label: str) -> int:
    """Up to `amount` from the cash (never below 0), then the bank account. Returns what was taken."""
    j = s['journey']
    amount = max(0, int(amount))
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _jr()._wallet(j, -cash, kind, label)
    b = bk.get(s)
    rest = min(amount - cash, b['balance']) if b else 0
    if rest > 0:
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label, -rest)
    return cash + max(0, rest)


def _motor(s: dict) -> list[tuple[str, dict, dict]]:
    """[(vehicle id, the car record, its catalogue entry)] of the vehicles that can break (not the bicycles)."""
    from . import garage as gr
    from . import upkeep as up
    g = gr.get(s)
    out = []
    for vid in gr.ORDER:
        car = g['cars'].get(vid) if g else None
        if car and up.car_bp(vid, car['p']):
            out.append((vid, car, gr.VEHICLES[vid]))
    return out


def _homes(s: dict) -> list[dict]:
    from . import housing as hs
    return [x for x in hs.homes(hs.get(s)) if hs.HOMES.get(x.get('kind'), {}).get('kind') == 'own' and type(x.get('price')) is int]


def _home(s: dict, hid) -> dict | None:
    return next((x for x in _homes(s) if x['id'] == hid), None)


def _lived(s: dict, hid) -> bool:
    from . import housing as hs
    h = hs.get(s)
    return bool(h and h.get('own') and h['own'].get('id') == hid)


def _home_name(x: dict) -> str:
    from . import housing as hs
    return hs.HOMES[x['kind']]['name']


def _reno_part(s: dict, hid, part: str) -> dict | None:
    """The reno record of `part` in the home you live in (None: another home, or nobody has worked on it yet)."""
    from . import reno as rn
    r = rn.get(s)
    if not r or not _lived(s, hid) or r.get('hid') != hid or not isinstance(r.get('parts'), dict):
        return None
    x = r['parts'].get(part)
    return x if isinstance(x, dict) and type(x.get('c')) is int else None


def _needs_low(s: dict) -> bool:
    from . import needs as nd
    n = nd.get(s)
    return bool(n) and (n.get('full', 100) < nd.LOW or n.get('wake', 100) < nd.LOW or bool(n.get('low')))


def _spirit_now(s: dict) -> int:
    L = s['journey'].get('life')
    return L['spirit'] if isinstance(L, dict) and type(L.get('spirit')) is int else 70


def _spirit(s: dict, n: int) -> int:
    from . import housing as hs
    return hs._spirit(s, n)


def _where(s: dict) -> str:
    from . import housing as hs
    h = hs.get(s)
    place, kind = hs.where(h)
    return 'dorm' if place == 'rent' and kind == hs.DORM else place


def _company_cover(s: dict) -> bool:
    """A promoted employee's company insurance (job.promo rank ≥ 1, a build with promotions): BHYT for free."""
    for c in s.get('careers', {}).values():
        job = c.get('job') if isinstance(c, dict) else None
        promo = job.get('promo') if isinstance(job, dict) else None
        if job and job.get('status') == 'hired' and isinstance(promo, dict) and type(promo.get('rank')) is int and promo['rank'] >= 1:
            return True
    return False


# ---------------------------------------------------------------- insurance
def premium_milli(s: dict, pid: str) -> int:
    """One life day of policy `pid` for what is owned now, in thousandths of a xu."""
    P = POLICIES[pid]
    if pid == 'yte':   # like the real BHYT, by means: a few xu, a little more for a bigger W (the clinic costs more)
        return min(P['most'], P['flat'] + room(s) * P['bp'] // 10000) * 1000 // MONTH_DAYS
    if pid == 'xe':
        base = sum(car['p'] for _, car, _ in _motor(s))
    else:
        base = sum(x['price'] for x in _homes(s))
    return base * P['bp'] // (10 * MONTH_DAYS)


def premium_month(s: dict, pid: str) -> int:
    return (premium_milli(s, pid) * MONTH_DAYS + 500) // 1000


def insurable(s: dict, pid: str) -> bool:
    return pid == 'yte' or (pid == 'xe' and bool(_motor(s))) or (pid == 'nha' and bool(_homes(s)))


def cover(s: dict, r: dict, kind: str, day: int) -> int:
    """% the insurance pays for an event of `kind` first warned on life day `day`."""
    pid = POLICY_OF.get(kind)
    if not pid:
        return 0
    if pid == 'yte' and _company_cover(s):
        return POLICIES['yte']['cover']
    start = r['pol'].get(pid)
    return POLICIES[pid]['cover'] if type(start) is int and start + WAIT <= day else 0


def _bill(s: dict, r: dict, day: int, notes: list) -> None:
    amount = r['acc'] // 1000
    r['acc'] %= 1000
    if amount <= 0:
        return
    names = ', '.join(POLICIES[p]['name'].replace('Bảo hiểm ', '') for p in POLICIES if p in r['pol'])
    if _have(s) < amount:
        r['pol'] = {}
        r['acc'] = 0
        notes.append(f'🛡️ Bảo hiểm tạm ngưng: ví và tài khoản chưa đủ {_fmt(amount)} xu. Bật lại khi có tiền nhé.')
        _log(r, day, 'Bảo hiểm tạm ngưng (chưa đủ tiền đóng phí)')
        return
    got = _take(s, amount, WALLET['pol'], f'Phí bảo hiểm tháng · {names}' if names else 'Phí bảo hiểm tháng')
    _stat(r, 'premiums', got)
    notes.append(f'🛡️ Phí bảo hiểm tháng: {_fmt(got)} xu.')


# ---------------------------------------------------------------- the events
def _xe_cost(car: dict) -> int:
    return car['p'] * XE_PCT // 10000


def _nha_cost(s: dict, x: dict, sub: str, r: dict) -> int:
    cost = x['price'] * NHA_SUBS[sub][2] // 10000
    if sub == 'chay' and 'binh' in r['gear']:
        cost //= 3
    return cost


def _om_cost(s: dict) -> int:
    return max(OM_MIN, min(OM_MAX, room(s) * OM_PCT // 10000))


def _phat_cost(price: int) -> int:
    return max(PHAT_MIN, min(PHAT_MAX, price * PHAT_BP // 10000))


def _theft(s: dict, r: dict, kind: str) -> int:
    """What a theft takes from the cash this morning (before the caps)."""
    cash = max(0, s['journey']['wallet'])
    if kind == 'moc':
        return min(MOC_MAX, (cash - FLOOR) * MOC_PCT // 100) if cash > FLOOR else 0
    loss = min(TROM_MAX, (cash - FLOOR) * TROM_PCT // 100) if cash > FLOOR else 0
    return loss // 4 if 'ket' in r['gear'] else loss


def _waived(r: dict, day: int) -> bool:
    return bool(r['waived']) and day - r['waived'] <= WAIVED_DAYS


def candidates(s: dict, r: dict, day: int) -> list[tuple[int, str, str, object]]:
    """[(odds per 10 000 today, kind, sub, ref)]: what could start today (each its own odds)."""
    from . import garage as gr
    from . import reno as rn
    j = s['journey']
    out = []
    g = gr.get(s)
    ride = g['ride'] if g else None
    twice = 2 if _waived(r, day) else 1
    for vid, car, V in _motor(s):
        if vid in r['broken']['xe'] or not gr.used_before(s,vid,day):
            continue
        out.append((XE_P[0 if vid == ride else 1] * twice, 'xe', V['group'], vid))
    from . import housing as hs
    for x in _homes(s):
        if x['id'] in r['broken']['nha']:
            continue
        p = NHA_P * twice
        if _lived(s, x['id']):
            rb = rn._view_block(s)
            if rb and rb['parts']:
                if min(v['c'] for v in rb['parts'].values()) < rn.WORN_AT:
                    p *= 2
                elif all(v['lv'] >= 1 for v in rb['parts'].values()):
                    p //= 2
        out.append((p, 'nha', '', x['id']))
    if not r['sick'] or day - r['sick'] >= SICK_GAP:
        p = OM_P[0] + (OM_P[1] if _needs_low(s) else 0) + (OM_P[2] if _spirit_now(s) < 35 else 0)
        out.append((p, 'om', '', None))
    cash = max(0, j['wallet'])
    if cash >= FLOOR + 100:
        p = MOC_P * (3 if cash > MOC_RICH else 2) // 2
        out.append((p // 2 if 'tui' in r['gear'] else p, 'moc', '', None))
    if cash >= TROM_CASH and _where(s) in ('own', 'rent', 'shared'):
        out.append((TROM_P * 2 // 5 if 'khoa' in r['gear'] else TROM_P, 'trom', '', None))
    if ride and ride in gr.VEHICLES and gr.VEHICLES[ride]['group'] == 'car' and ride in g['cars'] and ride not in r['broken']['xe'] and gr.used_before(s,ride,day):
        out.append((PHAT_P, 'phat', '', ride))
    if _projected(s, r, 'hack', 'account', None) >= MIN_COST:
        out.append((HACK_P, 'hack', 'account', None))
    if day < EASE_DAY or wealth(s) < EASE_W:
        out = [(p // 2, k, sub, ref) for p, k, sub, ref in out]
    return [x for x in out if x[0] > 0]


def _month(s: dict, r: dict, day: int) -> dict:
    i = (day - 1) // MONTH_DAYS
    if r['month'].get('i') != i:
        r['month'] = dict(i=i, w=room(s), lost=0, n=0)
    return r['month']


def _budget(s: dict, r: dict, day: int) -> int:
    """How much one more event may cost today: EVENT_PCT % of W − FLOOR, and what the tháng has left."""
    m = _month(s, r, day)
    return max(0, min(room(s) * EVENT_PCT // 100, m['w'] * MONTH_PCT // 100 - m['lost']))


def eligible(s: dict, r: dict, day: int) -> bool:
    j = s['journey']
    return (bool(j.get('story')) and day >= START_DAY and j.get('chapter', 1) >= START_CHAPTER and day >= r['since'] + QUIET
            and wealth(s) >= FLOOR)


def _projected(s: dict, r: dict, kind: str, sub: str, ref) -> int:
    """What the event would cost if it happened today (before the caps)."""
    if kind == 'hack':
        b = bk.get(s)
        return min(HACK_MAX, max(0, b['balance']) * HACK_PCT // 100) if b else 0
    if kind == 'xe':
        from . import garage as gr
        return _xe_cost(gr.get(s)['cars'][ref])
    if kind == 'nha':
        return _nha_cost(s, _home(s, ref), sub, r)
    if kind == 'om':
        return _om_cost(s)
    if kind in ('moc', 'trom'):
        return _theft(s, r, kind) if kind == 'trom' or sub == 'vi' else max(DT_MIN, min(DT_MAX, room(s) * DT_PCT // 10000))
    if kind == 'phat':
        from . import garage as gr
        return _phat_cost(gr.get(s)['cars'][ref]['p'])
    return 0


def _roll(s: dict, r: dict, day: int, notes: list) -> None:
    m = _month(s, r, day)
    if r['warn'] or r['card'] or day < r['next_ok'] or m['n'] >= MONTH_EVENTS or _budget(s, r, day) < MIN_COST:
        return
    rng = _rng(s, 'roll', day)
    cands = candidates(s, r, day)
    u = rng.random() * 10000
    for p, kind, sub, ref in cands:
        if u >= p:
            u -= p
            continue
        if kind == 'nha':
            x = _home(s, ref)
            subs = [k for k in NHA_SUBS if k != 'ngap' or _home_group(x) in NGAP_GROUPS]
            sub = rng.choices(subs, weights=[NHA_SUBS[k][0] for k in subs])[0]
        elif kind == 'om':
            sub = rng.choice(('cam', 'bung', 'lung'))
        elif kind == 'moc':
            sub = 'vi' if rng.random() < .7 else 'dt'
        elif kind == 'trom':
            sub = 'nha'
        elif kind == 'phat':
            sub = 'do'
        cost = _projected(s, r, kind, sub, ref)
        if min(cost, _budget(s, r, day)) < MIN_COST and kind not in ('moc', 'trom'):
            return
        lead = rng.choice(LEAD)
        r['warn'] = dict(kind=kind, sub=sub, ref=ref, day=day + lead, at=day, cost=int(cost))
        r['next_ok'] = day + GAP
        _stat(r, 'warned')
        w = warn_view(s, r)
        if w:
            notes.append(f'{w["emoji"]} {w["title"]}: {w["text"]}')
        return


def _home_group(x: dict | None) -> str:
    from . import housing as hs
    return hs.HOMES[x['kind']]['group'] if x and x.get('kind') in hs.HOMES else ''


def _still_there(s: dict, kind: str, ref) -> bool:
    """The vehicle or home of a warning or a card is still the player's (sold since: nothing happens)."""
    from . import garage as gr
    if kind in ('xe', 'phat'):
        g = gr.get(s)
        return bool(g and ref in g['cars'] and ref in gr.VEHICLES)
    if kind == 'nha':
        return _home(s, ref) is not None
    return True


def _fire(s: dict, r: dict, day: int, notes: list) -> None:
    """The morning a warning comes true (unless it was prevented, or the tháng's caps are reached)."""
    w = r['warn']
    r['warn'] = None
    kind, sub, ref = w['kind'], w['sub'], w['ref']
    m = _month(s, r, day)
    if not _still_there(s, kind, ref) or wealth(s) < FLOOR or m['n'] >= MONTH_EVENTS:
        _stat(r, 'fizzled')
        return
    budget = _budget(s, r, day)
    if kind == 'hack':
        b = bk.get(s)
        loss = min(_projected(s, r, kind, sub, ref), budget)
        if not b or loss < MIN_COST:
            _stat(r, 'fizzled')
            return
        b['balance'] -= loss
        label = 'Tài khoản ngân hàng bị hack'
        bk._log(b, day, 'acc', label, -loss)
        _stat(r, 'lost', loss)
        m['lost'] += loss
        m['n'] += 1
        _stat(r, 'events')
        _log(r, day, label, -loss)
        _new_card(r, day, kind, sub, ref, 0, loss, 0)
        notes.append(f'🔐 Tài khoản ngân hàng bị hack: mất {_fmt(loss)} xu trong tài khoản thanh toán.')
        return
    if kind == 'phat' and r['fines'] == 0:   # the first fine: only a warning
        r['fines'] += 1
        _new_card(r, day, kind, 'nhac', ref, 0, 0, 0)
        m['n'] += 1
        return
    if kind in ('moc', 'trom') and (kind == 'trom' or sub == 'vi'):
        loss = min(_theft(s, r, kind), budget, max(0, s['journey']['wallet']))
        if loss < MIN_COST:
            _stat(r, 'fizzled')
            return
        label = 'Bị móc túi' if kind == 'moc' else 'Trộm vào nhà lấy tiền mặt'
        _jr()._wallet(s['journey'], -loss, WALLET[kind], label)
        _stat(r, 'lost', loss)
        m['lost'] += loss
        m['n'] += 1
        _stat(r, 'events')
        _log(r, day, label, -loss)
        _new_card(r, day, kind, sub, ref, 0, loss, 0)
        notes.append(f'{KIND_META[kind][0]} {label}: mất {_fmt(loss)} xu tiền mặt.')
        return
    cost = min(_projected(s, r, kind, sub, ref), budget)
    if cost < MIN_COST:
        _stat(r, 'fizzled')
        return
    if kind == 'phat':
        r['fines'] += 1
    if kind == 'om' and sub != 'lai':
        r['sick'] = day
    m['n'] += 1
    _stat(r, 'events')
    _new_card(r, day, kind, sub, ref, cost, 0, cover(s, r, kind, w['at']))
    c = card_view(s, r)
    notes.append(f'{c["emoji"]} {c["title"]}: {c["text"]}')


def _new_card(r: dict, day: int, kind: str, sub: str, ref, cost: int, loss: int, cov: int) -> None:
    r['seq'] += 1
    r['card'] = dict(id=f'r{r["seq"]}', kind=kind, sub=sub, ref=ref, day=day, cost=int(cost), loss=int(loss), cover=int(cov))


# ---------------------------------------------------------------- the card's choices
def _part(cost: int, cov: int) -> int:
    """What the player pays of `cost` when the insurance covers `cov` %."""
    return cost - cost * cov // 100


def options(s: dict, r: dict) -> list[dict]:
    """The open card's choices: [{id, emoji, label, cost (xu the player pays), spirit, ok, why}]. The first one is the
    obvious one (the primary button); `default` marks what an unanswered card takes."""
    c = r['card']
    if not c:
        return []
    k, sub, cost, cov = c['kind'], c['sub'], c['cost'], c['cover']
    have = _have(s)

    def o(oid, emoji, label, pay=0, spirit=0, default=False, note=''):
        ok = pay <= have
        return dict(id=oid, emoji=emoji, label=label, cost=pay, spirit=spirit, ok=ok,
                    why='' if ok else f'Còn thiếu {_fmt(pay - have)} xu', default=default, note=note)
    if k == 'xe':
        from . import garage as gr
        out = [o('sua', '🔧', 'Sửa ở tiệm', _part(cost, cov))]
        if sub == 'bike':
            out.append(o('tu', '🛠️', 'Tự sửa', _part(cost // 2, cov), SPIRIT['tu_xe']))
        out.append(o('de', '⏸️', 'Để đó', note='Chưa đi được xe này', default=True))
        return out
    if k == 'nha':
        let = _let(s, c['ref'])
        out = [o('tho', '👷', 'Gọi thợ sửa', _part(cost, cov), default=let)]
        if sub in ('dot', 'ong'):
            out.append(o('tu', '🛠️', 'Tự sửa', _part(cost // 2, cov), SPIRIT['tu_nha']))
        if not let:
            out.append(o('de', '⏸️', 'Để đó', note='Nhà mất Ấm cúng tới khi sửa', default=True))
        return out
    if k == 'om':
        out = [o('kham', '🏥', 'Đi khám', _part(cost, cov))]
        if sub != 'lai':
            out.append(o('thuoc', '💊', 'Mua thuốc', THUOC, SPIRIT['thuoc'], note='Có khi không đỡ'))
        out.append(o('nghi', '🛌', 'Nằm nghỉ', 0, SPIRIT['nghi_lai' if sub == 'lai' else 'nghi'], default=True))
        return out
    if k == 'hack':
        return [o('secure', '🔐', 'Khóa phiên lạ & báo ngân hàng', default=True,
                  note='Miễn phí; khoản đã mất không tự hoàn lại')]
    if k in ('moc', 'trom') and sub != 'dt':
        return [o('bao', '🚔', 'Báo công an', note='Có khi tìm lại được một nửa'),
                o('thoi', '🙏', 'Thôi, rút kinh nghiệm', default=True)]
    if k == 'moc':
        return [o('mua', '📱', 'Mua máy mới', cost), o('cu', '📞', 'Xài máy cũ', 0, SPIRIT['cu'], default=True)]
    if k == 'phat':
        if sub == 'nhac':
            return [o('ok', '🙏', 'Cảm ơn anh', default=True)]
        return [o('nop', '💵', 'Nộp phạt', cost, default=True),
                o('xin', '🙏', 'Xin bỏ qua', note=f'{XIN_OK}% được miễn, không thì phạt nặng hơn')]
    return []


def _let(s: dict, hid) -> bool:
    x = _home(s, hid)
    return bool(x and x.get('let'))


def _resolve(s: dict, r: dict, choice: str, day: int, auto: bool = False) -> str:
    """Apply `choice` to the open card. The message."""
    c = r['card']
    k, sub, ref, cost, cov = c['kind'], c['sub'], c['ref'], c['cost'], c['cover']
    opt = next(x for x in options(s, r) if x['id'] == choice)
    r['card'] = None
    pay = opt['cost']
    label = ''
    msg = ''
    if k == 'xe':
        from . import garage as gr
        V = gr.VEHICLES.get(ref, {'name': 'Xe'})
        if choice == 'de':
            r['broken']['xe'][ref] = dict(c=cost, d=day)
            msg = f'{V["name"]} để ở nhà. Sửa lúc nào cũng được ở Bảo hiểm & rủi ro.'
        else:
            label = f'Sửa xe · {V["name"]}'
            msg = f'{V["name"]} chạy ngon lại rồi.'
    elif k == 'nha':
        x = _home(s, ref)
        name = _home_name(x) if x else 'Nhà'
        part = NHA_SUBS[sub][1]
        rp = _reno_part(s, ref, part)
        if choice == 'de':
            r['broken']['nha'][ref] = dict(p=part, c=cost, d=day)
            if rp:
                from . import reno as rn
                rp['c'] = min(rp['c'], rn.WORN_AT - 15)
            msg = f'Để sửa sau. {name} tạm mất Ấm cúng.'
        else:
            if rp:
                rp['c'] = 100
            label = f'{NHA_TEXT[sub][1]} · {name}'
            msg = f'Thợ sửa xong, {_lname(name)} lại như mới.'
    elif k == 'om':
        if choice == 'kham':
            label = 'Khám bệnh, mua thuốc theo đơn'
            msg = 'Bác sĩ khám kỹ, uống thuốc vài hôm là khỏe.'
        elif choice == 'thuoc':
            label = 'Mua thuốc ở nhà thuốc'
            if _rng(s, 'thuoc', day).randint(1, 100) <= THUOC_LAI:
                r['warn'] = dict(kind='om', sub='lai', ref=None, day=day + 2, at=c['day'], cost=_om_cost(s))
                msg = 'Uống thuốc rồi, nghỉ ngơi thêm nhé.'
            else:
                msg = 'Thuốc đỡ hẳn, mai đi làm lại được.'
        else:
            msg = 'Nằm nghỉ một hôm, người cũng đỡ dần.'
    elif k == 'hack':
        msg = 'Đã khóa phiên lạ và báo ngân hàng. Khoản xu đã mất được ghi trong lịch sử tài khoản.'
        _log(r, day, 'Khóa phiên lạ & báo ngân hàng')
    elif k in ('moc', 'trom') and sub != 'dt':
        if choice == 'bao':
            ok = _rng(s, 'bao', day).randint(1, 100) <= BAO_BACK
            r['back'] = dict(day=day + BACK_DAYS, amount=c['loss'] // 2 if ok else 0)
            msg = 'Đã trình báo. Có tin công an sẽ báo bạn.'
        else:
            msg = 'Lần sau cất tiền vào ngân hàng cho chắc nhé.'
    elif k == 'moc':
        if choice == 'mua':
            label = 'Mua điện thoại mới'
            msg = 'Máy mới, nhớ cài lại danh bạ nhé.'
        else:
            msg = 'Máy cũ hơi chậm, nhưng vẫn gọi được.'
    elif k == 'phat':
        if choice == 'xin':
            if _rng(s, 'xin', day).randint(1, 100) <= XIN_OK:
                msg = 'Chú công an bỏ qua lần này. May quá!'
            else:
                pay = cost * XIN_MORE // 100
                label = 'Nộp phạt đỗ xe (lần này không bỏ qua)'
                msg = 'Không được bỏ qua, phạt nặng hơn chút.'
        elif choice == 'nop':
            label = 'Nộp phạt đỗ xe'
            msg = 'Đã nộp phạt. Lần sau gửi xe vào bãi nhé.'
        else:
            msg = 'Lần sau nhớ gửi xe vào bãi nhé.'
    if pay > 0:
        got = _take(s, pay, WALLET[k], label or KIND_META[k][1])
        if got < pay:
            _stat(r, 'waived', pay - got)
        _stat(r, 'paid', got)
        if k in POLICY_OF and choice in ('sua', 'tu', 'tho', 'kham'):
            full = cost if choice != 'tu' else cost // 2
            _stat(r, 'covered', full - pay)
        r['month']['lost'] = r['month'].get('lost', 0) + got
        _log(r, day, label or KIND_META[k][1], -got)
        msg += f' Trả {_fmt(got)} xu' + (f', bảo hiểm trả {cov}%.' if cov and choice in ('sua', 'tu', 'tho', 'kham') else '.')
        if got < pay:
            msg += f' {_fmt(pay - got)} xu còn thiếu được miễn.'
    if opt['spirit']:
        got = _spirit(s, opt['spirit'])
        if got:
            msg += f' Tinh thần {got}.'
    if auto:
        msg = f'{KIND_META[k][0]} Chưa chọn nên tự động: {opt["label"].lower()}. ' + msg
    return msg.strip()


# ---------------------------------------------------------------- prevention
def warn_options(s: dict, r: dict) -> list[dict]:
    """The open warning's preventions: [{id, emoji, label, cost, ok, why}] (first: the obvious one)."""
    w = r['warn']
    if not w:
        return []
    have = _have(s)

    def o(oid, emoji, label, pay=0, why=''):
        ok = not why and pay <= have
        return dict(id=oid, emoji=emoji, label=label, cost=pay, ok=ok,
                    why=why or ('' if ok else f'Còn thiếu {_fmt(pay - have)} xu'))
    k = w['kind']
    if k == 'hack':
        return [o('secure', '🔐', 'Đổi mã bảo mật & khóa phiên lạ')]
    if k in ('moc', 'trom'):
        g = 'tui' if k == 'moc' else 'khoa'
        out = []
        if w['sub'] == 'dt':
            out.append(o('can', '📵', 'Cất máy, đi đường cẩn thận'))
        else:
            b = bk.get(s)
            out.append(o('gui', '🏦', 'Gửi tiền mặt vào ngân hàng', 0, '' if b else 'Chưa có tài khoản ngân hàng'))
        if g not in r['gear']:
            out.append(o(g, GEAR[g]['emoji'], f'Mua {_lname(GEAR[g]["name"])}', GEAR[g]['price']))
        return out
    fee = prevent_fee(s, r)
    label = {'xe': 'Ghé tiệm kiểm tra', 'nha': 'Gọi thợ xem trước', 'om': 'Đi khám sớm', 'phat': 'Gửi xe vào bãi'}[k]
    emoji = {'xe': '🔧', 'nha': '👷', 'om': '🩺', 'phat': '🅿️'}[k]
    if k == 'nha' and w['sub'] == 'ngap':
        label, emoji = 'Khơi cống, kê đồ lên cao', '🧹'
    return [o('kiem', emoji, label, fee)]


def prevent_fee(s: dict, r: dict) -> int:
    w = r['warn']
    if w['kind'] == 'hack':
        return 0
    cost = min(w['cost'], max(MIN_COST, _budget(s, r, s['journey']['life_day'])))
    fee = max(3, _ceil_pct(cost, PREVENT_PCT))
    return _part(fee, cover(s, r, w['kind'], w['at']))


# ---------------------------------------------------------------- the daily tick
def note_waived(s: dict, day: int) -> None:
    """game/upkeep.py: a month's bill was waived today (the vehicles and homes break more easily for a while)."""
    r = get(s)
    if r is not None:
        r['waived'] = int(day)


def _repaired(s: dict, r: dict) -> None:
    """A broken home part fixed in Sửa nhà (reno condition back up), or a vehicle or home no longer owned: cleared."""
    from . import garage as gr
    from . import reno as rn
    g = gr.get(s)
    for vid in list(r['broken']['xe']):
        if not g or vid not in g['cars']:
            r['broken']['xe'].pop(vid)
    for hid, b in list(r['broken']['nha'].items()):
        if _home(s, hid) is None:
            r['broken']['nha'].pop(hid)
            continue
        rp = _reno_part(s, hid, b['p'])
        if rp and rp['c'] >= rn.WORN_AT:
            r['broken']['nha'].pop(hid)


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Catch up to journey.life_day (idempotent; after the bank, the homes and the month's bills). Only the last life
    day is looked at when several passed (an older build ran them): nothing is back-filled, nothing billed for them."""
    j = s.get('journey')
    if not isinstance(j, dict) or not j.get('story'):
        return []
    notes: list[str] = []
    target = int(j['life_day'])
    r = get(s)
    if r is None:
        r = j[KEY] = initial(target)
        if target >= START_DAY and j.get('chapter', 1) >= START_CHAPTER:
            notes.append('🛡️ Phố có tin: dạo này hay có trộm, xe hỏng, nhà dột. Mua bảo hiểm ở Ngân hàng & nhà → Bảo hiểm.')
    r['day'] = max(r['day'], target - 1)
    while r['day'] < target:
        r['day'] += 1
        n = r['day']
        for pid in POLICIES:
            if pid in r['pol']:
                r['acc'] = min(ACC_MAX, r['acc'] + premium_milli(s, pid))
        if n % MONTH_DAYS == 0:
            _bill(s, r, n, notes)
        _month(s, r, n)
        _repaired(s, r)
        if r['back'] and n >= r['back']['day']:
            amt = r['back']['amount']
            r['back'] = None
            if amt > 0:
                _jr()._wallet(j, amt, WALLET['trom'], 'Công an tìm lại được tiền bị mất')
                _stat(r, 'back', amt)
                _log(r, n, 'Công an tìm lại được tiền', amt)
                notes.append(f'🚔 Công an tìm lại được {_fmt(amt)} xu cho bạn!')
            else:
                notes.append('🚔 Công an vẫn chưa tìm ra. Hẻm mình giờ có thêm camera rồi.')
        if r['card'] and n >= r['card']['day'] + CARD_DAYS:
            d = next((x for x in options(s, r) if x['default']), None)
            if d:
                notes.append(_resolve(s, r, d['id'], n, auto=True))
            else:
                r['card'] = None
        if r['card'] and not _still_there(s, r['card']['kind'], r['card']['ref']):
            r['card'] = None
        if r['warn'] and n >= r['warn']['day']:
            if r['card'] is None:
                _fire(s, r, n, notes)
            else:
                r['warn']['day'] = n + 1   # one card at a time: a follow-up waits for the open one
        elif eligible(s, r, n):
            _roll(s, r, n, notes)
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- commands
COMMANDS = ('jr_rui_prevent', 'jr_rui_choose', 'jr_rui_pol', 'jr_rui_gear', 'jr_rui_fix')


def _ensure(s: dict) -> dict:
    j = s['journey']
    if get(s) is None:
        j[KEY] = initial(j['life_day'])
    return get(s)


def fix_cost(s: dict, r: dict, kind: str, ref) -> int:
    b = r['broken'][kind].get(ref)
    return _part(b['c'], cover(s, r, kind, b['d'])) if b else 0


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Bảo hiểm chỉ có trong chế độ hành trình.')
    need(isinstance(p, dict), 'Dữ liệu không hợp lệ.')
    r = _ensure(s)
    day = j['life_day']
    if name == 'jr_rui_prevent':
        need(set(p) <= {'opt'}, 'Dữ liệu không hợp lệ.')
        w = r['warn']
        if not w:
            return dict(message='Chuyện đó qua rồi, không sao nữa.', duplicate=True)
        opt = next((x for x in warn_options(s, r) if x['id'] == p.get('opt')), None)
        need(opt is not None, 'Chọn một cách phòng nhé.')
        need(opt['ok'], opt['why'] or 'Chưa làm được.', 'not_enough')
        if opt['id'] == 'gui':
            amount = max(0, j['wallet']) - 50
            need(amount > 0, 'Tiền mặt trong ví đã ít rồi.')
            bk.apply(s, 'jr_bk_deposit', {'amount': amount})
            msg = f'Đã gửi {_fmt(amount)} xu vào ngân hàng. Kẻ gian có đến cũng về tay không.'
        elif opt['id'] == 'can':
            msg = 'Máy cất kỹ trong túi. Đi đường yên tâm.'
        elif opt['id'] == 'secure':
            msg = 'Đã đổi mã bảo mật và khóa phiên lạ. Chặn được vụ hack này, tài khoản không mất xu.'
        elif opt['id'] in GEAR:
            g = GEAR[opt['id']]
            got = _take(s, g['price'], WALLET['gear'], f'Mua {_lname(g["name"])}')
            r['gear'].append(opt['id'])
            _stat(r, 'gear', got)
            msg = f'{g["emoji"]} Đã mua {_lname(g["name"])}. Yên tâm hơn hẳn.'
        else:
            k = w['kind']
            label = {'xe': 'Kiểm tra xe', 'nha': 'Thợ xem nhà', 'om': 'Khám sức khỏe', 'phat': 'Gửi xe vào bãi'}[k]
            got = _take(s, opt['cost'], WALLET[k], label) if opt['cost'] else 0
            _stat(r, 'paid', got)
            msg = {'xe': 'Thợ siết lại vài con ốc, xe êm ru.', 'nha': 'Thợ xử lý sớm, không sao nữa.',
                   'om': 'Bác sĩ dặn ăn ngủ đúng giờ. Khỏe rồi.', 'phat': 'Xe gửi trong bãi, yên tâm.'}[k]
            if got:
                msg += f' Trả {_fmt(got)} xu.'
        r['warn'] = None
        _stat(r, 'prevented')
        _log(r, day, f'Phòng trước: {opt["label"]}')
        return dict(message=msg)
    if name == 'jr_rui_choose':
        need(set(p) <= {'id', 'choice'}, 'Dữ liệu không hợp lệ.')
        c = r['card']
        if not c or c['id'] != p.get('id'):
            return dict(message='Chuyện này đã xong rồi.', duplicate=True)
        opt = next((x for x in options(s, r) if x['id'] == p.get('choice')), None)
        need(opt is not None, 'Chọn một cách nhé.')
        need(opt['ok'], opt['why'] or 'Chưa làm được.', 'not_enough')
        return dict(message=_resolve(s, r, opt['id'], day))
    if name == 'jr_rui_pol':
        need(set(p) <= {'id', 'on'} and p.get('id') in POLICIES and type(p.get('on')) is bool, 'Chọn một loại bảo hiểm nhé.')
        pid, on = p['id'], p['on']
        P = POLICIES[pid]
        if on == (pid in r['pol']):
            return dict(message='Không có gì thay đổi.', duplicate=True)
        if on:
            need(insurable(s, pid), 'Chưa có gì để bảo hiểm.' if pid != 'yte' else 'Chưa bật được.')
            r['pol'][pid] = day
            return dict(message=f'{P["emoji"]} Đã mua {_lname(P["name"])}: {_fmt(premium_month(s, pid))} xu/tháng, '
                                f'trả {P["cover"]}% từ ngày sống {day + WAIT}.')
        r['pol'].pop(pid)
        return dict(message=f'Đã ngưng {_lname(P["name"])}.')
    if name == 'jr_rui_gear':
        need(set(p) <= {'id'} and p.get('id') in GEAR, 'Chọn một món nhé.')
        gid = p['id']
        g = GEAR[gid]
        if gid in r['gear']:
            return dict(message=f'Bạn đã có {_lname(g["name"])} rồi.', duplicate=True)
        need(_have(s) >= g['price'], f'Cần {_fmt(g["price"])} xu.', 'not_enough')
        got = _take(s, g['price'], WALLET['gear'], f'Mua {_lname(g["name"])}')
        r['gear'].append(gid)
        _stat(r, 'gear', got)
        return dict(message=f'{g["emoji"]} Đã mua {_lname(g["name"])}.')
    if name == 'jr_rui_fix':
        need(set(p) <= {'kind', 'ref'} and p.get('kind') in ('xe', 'nha'), 'Chọn thứ cần sửa nhé.')
        kind, ref = p['kind'], p.get('ref')
        b = r['broken'][kind].get(ref) if isinstance(ref, str) else None
        if not b:
            return dict(message='Đã sửa xong rồi.', duplicate=True)
        pay = fix_cost(s, r, kind, ref)
        need(_have(s) >= pay, f'Cần {_fmt(pay)} xu để sửa.', 'not_enough')
        if kind == 'xe':
            from . import garage as gr
            label = f'Sửa xe · {gr.VEHICLES.get(ref, {"name": "xe"})["name"]}'
        else:
            x = _home(s, ref)
            label = f'Sửa nhà · {_home_name(x) if x else "nhà"}'
            rp = _reno_part(s, ref, b['p'])
            if rp:
                rp['c'] = 100
        got = _take(s, pay, WALLET[kind], label)
        r['broken'][kind].pop(ref)
        _stat(r, 'paid', got)
        _stat(r, 'covered', b['c'] - pay)
        _log(r, day, label, -got)
        return dict(message=f'Sửa xong, trả {_fmt(got)} xu.')
    raise e.GameError('Thao tác bảo hiểm không hợp lệ.', 'unknown_action')


# ---------------------------------------------------------------- views
def is_broken(s: dict, kind: str, ref) -> bool:
    r = get(s)
    return bool(r and ref in r['broken'].get(kind, {}))


def broken_cost(s: dict, kind: str, ref) -> int:
    """What fixing a broken vehicle or home costs the player now (0: not broken)."""
    r = get(s)
    return fix_cost(s, r, kind, ref) if r and ref in r['broken'].get(kind, {}) else 0


def warn_view(s: dict, r: dict) -> dict | None:
    w = r['warn']
    if not w:
        return None
    k, sub, ref = w['kind'], w['sub'], w['ref']
    emoji, title = KIND_META[k]
    text = ''
    if k == 'xe':
        from . import garage as gr
        V = gr.VEHICLES.get(ref, {})
        emoji, title, text = '🔧', V.get('name', 'Xe'), XE_WARN.get(sub, XE_WARN['bike'])
    elif k == 'nha':
        x = _home(s, ref)
        emoji, title, text = NHA_TEXT[sub][0], _home_name(x) if x else 'Nhà', NHA_TEXT[sub][3]
    elif k == 'om':
        emoji, title, text = ('🤧', 'Vẫn còn mệt', 'Uống thuốc mà người vẫn chưa đỡ.') if sub == 'lai' else \
            ('🥱', 'Người hơi mệt', 'Dạo này ăn ngủ thất thường.')
    elif k == 'moc':
        emoji, title, text = '👀', 'Coi chừng móc túi', 'Chợ dạo này có nhóm móc túi.'
    elif k == 'trom':
        emoji, title, text = '👀', 'Coi chừng trộm', 'Hàng xóm thấy người lạ dòm ngó.'
    elif k == 'hack':
        emoji, title, text = '🔐', 'Đăng nhập ngân hàng bất thường', 'Có phiên đăng nhập lạ. Khóa ngay miễn phí để tránh mất xu trong tài khoản thanh toán.'
    elif k == 'phat':
        emoji, title, text = '🚧', 'Phường dẹp lòng đường', 'Đỗ xe dưới đường dễ bị phạt.'
    return dict(kind=k, sub=sub, ref=ref, emoji=emoji, title=title, text=text,
                days=max(0, w['day'] - s['journey']['life_day']), opts=warn_options(s, r))


def card_view(s: dict, r: dict) -> dict | None:
    c = r['card']
    if not c:
        return None
    k, sub, ref = c['kind'], c['sub'], c['ref']
    emoji, title = KIND_META[k]
    text = ''
    if k == 'xe':
        from . import garage as gr
        V = gr.VEHICLES.get(ref, {})
        title, text = f'{V.get("name", "Xe")} hỏng', XE_TEXT.get(sub, XE_TEXT['bike'])
    elif k == 'nha':
        x = _home(s, ref)
        emoji, title, text = NHA_TEXT[sub][0], NHA_TEXT[sub][1], f'{_home_name(x) if x else "Nhà"}: {_lname(NHA_TEXT[sub][2])}'
    elif k == 'om':
        emoji, title, text = OM_TEXT[sub]
    elif k == 'moc':
        if sub == 'dt':
            emoji, title, text = '📱', 'Bị giật điện thoại', 'Đang xem bản đồ thì bị giật mất máy.'
        else:
            title, text = 'Bị móc túi', 'Chen chợ đông, về nhà mới thấy ví nhẹ hẳn.'
    elif k == 'trom':
        text = 'Cửa bị cạy, tiền mặt để nhà mất một phần.'
    elif k == 'hack':
        text = 'Kẻ gian đã chuyển mất một phần xu trong tài khoản thanh toán. Tiết kiệm và quỹ chung không bị trừ.'
    elif k == 'phat':
        text = 'Lần đầu, chú công an chỉ nhắc nhở.' if sub == 'nhac' else 'Đỗ xe dưới lòng đường, bị dán giấy phạt.'
    return dict(id=c['id'], kind=k, sub=sub, ref=ref, emoji=emoji, title=title, text=text, loss=c['loss'],
                cover=c['cover'], left=max(0, c['day'] + CARD_DAYS - s['journey']['life_day']), opts=options(s, r))


def public(s: dict) -> dict | None:
    """state.rui (not in the journey, whose size has a budget): the open warning and card, the policies with their
    price a tháng for what is owned now, the gear, what is broken. None outside story mode."""
    j = s['journey']
    if not j.get('story'):
        return None
    r = get(s) or initial(j['life_day'])
    day = j['life_day']
    pol = []
    for pid, P in POLICIES.items():
        start = r['pol'].get(pid)
        row = dict(id=pid, on=start is not None, month=premium_month(s, pid), can=insurable(s, pid))
        if start is not None and start + WAIT > day:
            row['wait'] = start + WAIT - day
        if pid == 'yte' and _company_cover(s):
            row['company'] = True
        pol.append(row)
    broken = []
    from . import garage as gr
    for vid, b in r['broken']['xe'].items():
        broken.append(dict(kind='xe', ref=vid, name=gr.VEHICLES.get(vid, {}).get('name', vid), cost=fix_cost(s, r, 'xe', vid)))
    for hid, b in r['broken']['nha'].items():
        x = _home(s, hid)
        broken.append(dict(kind='nha', ref=hid, name=_home_name(x) if x else '', cost=fix_cost(s, r, 'nha', hid)))
    out = dict(pol=pol, gear=list(r['gear']), broken=broken)
    if day < START_DAY or j.get('chapter', 1) < START_CHAPTER:
        out['calm'] = True   # a new player: nothing happens yet
    w, c = warn_view(s, r), card_view(s, r)
    if w:
        out['warn'] = w
    if c:
        out['card'] = c
    return out


def catalogue() -> dict:
    """Static rules for the client (bootstrap content)."""
    return dict(policies=[dict(id=k, emoji=v['emoji'], name=v['name'], what=v['what'], cover=v['cover']) for k, v in POLICIES.items()],
                gear=[dict(id=k, **v) for k, v in GEAR.items()],
                rules=dict(floor=FLOOR, event_pct=EVENT_PCT, month_pct=MONTH_PCT, wait=WAIT, start_day=START_DAY,
                           start_chapter=START_CHAPTER, prevent_pct=PREVENT_PCT, card_days=CARD_DAYS,
                           hack_pct=HACK_PCT, hack_max=HACK_MAX))


# ---------------------------------------------------------------- the save
def validate(s: dict) -> None:
    """journey['rui'] when present: every field this build knows (fields a newer build adds are left alone)."""
    e = _core()
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    r = j[KEY]
    bad = 'Bảo hiểm trong bản lưu không hợp lệ.'
    need = e.need

    def day_ok(x, low=0):
        return type(x) is int and low <= x <= 10**6 + 10

    need(isinstance(r, dict) and set(initial(1)) <= set(r) and r['v'] == VERSION, bad, 'invalid_save')
    need(day_ok(r['since'], 1) and day_ok(r['day'], 1) and r['since'] <= r['day'] <= max(r['since'], int(j.get('life_day', 1)))
         and day_ok(r['next_ok']) and day_ok(r['waived']) and day_ok(r['sick']), bad, 'invalid_save')
    need(type(r['fines']) is int and 0 <= r['fines'] <= 10**6 and type(r['seq']) is int and 0 <= r['seq'] <= 10**9
         and type(r['acc']) is int and 0 <= r['acc'] <= ACC_MAX, bad, 'invalid_save')
    m = r['month']
    need(isinstance(m, dict) and {'i', 'w', 'lost', 'n'} <= set(m)
         and all(type(m[k]) is int and -1 <= m[k] <= 10**12 for k in ('i', 'w', 'lost', 'n')), bad, 'invalid_save')
    w = r['warn']
    need(w is None or (isinstance(w, dict) and {'kind', 'sub', 'ref', 'day', 'at', 'cost'} <= set(w) and w['kind'] in KINDS
                       and isinstance(w['sub'], str) and len(w['sub']) <= 8 and (w['ref'] is None or isinstance(w['ref'], str))
                       and day_ok(w['day'], 1) and day_ok(w['at'], 1) and type(w['cost']) is int and 0 <= w['cost'] <= 10**9),
         bad, 'invalid_save')
    c = r['card']
    need(c is None or (isinstance(c, dict) and {'id', 'kind', 'sub', 'ref', 'day', 'cost', 'loss', 'cover'} <= set(c)
                       and c['kind'] in KINDS and isinstance(c['id'], str) and len(c['id']) <= 16 and isinstance(c['sub'], str)
                       and len(c['sub']) <= 8 and (c['ref'] is None or isinstance(c['ref'], str)) and day_ok(c['day'], 1)
                       and all(type(c[k]) is int and 0 <= c[k] <= 10**9 for k in ('cost', 'loss')) and type(c['cover']) is int and 0 <= c['cover'] <= 100),
         bad, 'invalid_save')
    need(isinstance(r['pol'], dict) and set(r['pol']) <= set(POLICIES) and all(day_ok(v, 1) for v in r['pol'].values()),
         bad, 'invalid_save')
    need(isinstance(r['gear'], list) and len(set(r['gear'])) == len(r['gear']) and set(r['gear']) <= set(GEAR), bad, 'invalid_save')
    br = r['broken']
    need(isinstance(br, dict) and {'xe', 'nha'} <= set(br) and isinstance(br['xe'], dict) and isinstance(br['nha'], dict)
         and len(br['xe']) <= 64 and len(br['nha']) <= 64, bad, 'invalid_save')
    for k, rows in (('xe', br['xe']), ('nha', br['nha'])):
        for ref, b in rows.items():
            need(isinstance(ref, str) and len(ref) <= 32 and isinstance(b, dict) and type(b.get('c')) is int
                 and 0 <= b['c'] <= 10**9 and day_ok(b.get('d'), 1) and (k == 'xe' or b.get('p') in ('wall', 'roof', 'floor', 'power', 'kitchen')),
                 bad, 'invalid_save')
    bb = r['back']
    need(bb is None or (isinstance(bb, dict) and day_ok(bb.get('day'), 1) and type(bb.get('amount')) is int
                        and 0 <= bb['amount'] <= 10**9), bad, 'invalid_save')
    need(isinstance(r['log'], list) and len(r['log']) <= LOG_MAX
         and all(isinstance(x, dict) and day_ok(x.get('d'), 1) and isinstance(x.get('t'), str) and len(x['t']) <= 120
                 and type(x.get('a')) is int for x in r['log']), bad, 'invalid_save')
    need(isinstance(r['stats'], dict) and all(type(v) is int and 0 <= v <= 10**9 for v in r['stats'].values()), bad, 'invalid_save')
