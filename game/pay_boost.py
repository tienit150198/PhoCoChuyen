"""💰 Tăng tiền công nghề, 🎉 Tuần lễ tay nghề, 🧰 Bộ đồ nghề / 🤝 Mối khách quen / ⏩ Làm nhanh.

Owner 21/10: "coi hướng thêm tiền thưởng cho mọi người khi làm nghề nhé, hiện tại đang ít, tăng nhẹ nữa thì tốt, coi làm
event hay gì đó thì làm ngắn hạn cũng được" and "cái nào thêm để mọi người mua và tự động hay scale gì đó hợp lý thì làm
luôn nha". Standing rules kept: no "lương x5" career, no staff that restocks a shop (restocking stays the player's job),
a higher post pays more (every % here is ON the pay a post already earns, so the order of posts never changes), and the
🔥 x3 week (game/x3_week.py) is neither broken nor duplicated.

Where it applies (one hook, `on_earning`, called by tile_match.fund_bonus for the player's OWN work in story mode):
own finished jobs (income_gear.completion_bonus, the hook every guarded terminal job calls), the hired job's daily
salary (employment.on_close), the TT99 practice salary and the clothing branch's commission abroad. Never on staff
orders (fund_bonus direct=True), counter sales, the 2.x settlements, the fair, interest, gifts or transfers.

The bonus of one earning of `base` xu, booked as its own 'other_income' row "💰 Tiền công +N% · …" next to it:
  1. 💰 the permanent raise RAISE[career] (8–20 %: low-paid careers get the most, so none is left behind)
  2. 🎉 Tuần lễ tay nghề +EVENT_PCT % while the event window is open (MNL_PAYWEEK_FROM <= now <= MNL_PAYWEEK_UNTIL,
     Unix seconds; both unset = off). Planned: 22/10/2026 00:00 – 28/10/2026 23:59:59 VN = 1792602000 – 1793206799.
  3. 🧰 Bộ đồ nghề of that career: +2 / 3 / 5 / 6 / 8 % (tiers replace, never add)
  The three are added (never multiplied) and clamped at CAP_PCT (50 %); on the career's 🔥 x3 day at CAP_X3_PCT (40 %),
  so an x3 day pays at most base × 3.4: the x3 bonus is paid on the day's BASE net (journey._base_net subtracts these
  rows, summary['payboost']), and these rows are counted on the base only, never on the x3 bonus. One row at most
  ROW_CAP xu. Rounding: the fraction goes up or down by a hash of the row (deterministic for a retried command).
  4. 🤝 Mối khách quen (own finished jobs only): a TIP_CHANCE % chance (hash of the job) of a tip of TIP_PCT % of the
     job's pay (1..TIP_MAX xu): +2 % on average. Purchases together stay ≤ +10 % (8 % tools + 2 % tips on average).
  5. 🎉 Chuyên cần (event only): the first STREAK_JOBS own finished jobs of a Vietnam day pay STREAK_XU[streak] once
     that day, into the fund where the last one was done; the streak counts consecutive days.

🧰 Purchases, per career, paid from that workplace's fund (like 🔧 Thiết bị nghề), kept forever:
  * Bộ đồ nghề tiers 1–5 (each needs the one before), prices TOOL_PRICES (steep).
  * 🤝 Mối khách quen (BOOK_PRICE).
  * ⏩ Làm nhanh (FAST_PRICE, only careers in FAST): a step of the job the player has done right FAST_NEED times by
    hand (counted only on a correct answer, never on an auto-filled one) can be filled by one tap (payk_fast). The
    server computes the answer from the task's own key and runs the career's normal command with it, so the step is
    graded, paid and timed exactly like a hand-made one; nothing is ever skipped and a wrong answer can never farm it.
    No staff, no auto-restock: it only speeds up the player's own hands.

🛑 MNL_PAYBOOST_OFF=1: no raise, no event bonus, no tool / tip / streak effect, no Làm nhanh (what was bought stays).

Save (optional, absent until first use; older builds keep an unknown journey key untouched, journey.validate allows
extra keys): journey['paykit'] = {v: 1, tool: {career: 1..5}, book: [career], fast: [career],
st: {career: {action: n ≤ ST_MAX}}, wk: {d: 'YYYY-MM-DD', n: jobs that day, got: 0|1, s: streak, last: 'YYYY-MM-DD'}}.
No table, no schema step.
"""
from __future__ import annotations

import contextvars
import datetime
import hashlib
import os
import time

from . import price_index

VN = datetime.timezone(datetime.timedelta(hours=7))
KEY = 'paykit'
VERSION = 1
PREFIX = '💰 Tiền công'
STREAK_PREFIX = '🎉 Chuyên cần'
TIP_PREFIX = '🤝 Khách quen boa'
ACTIONS = ('payk_buy', 'payk_fast')

# 1. The permanent raise (%), by what a career pays a day before it (measured 21/10 from the career tests' finished jobs,
# CHANGELOG "pay-boost"): 4 × the median pay of a finished job + the contract salary's midpoint. Under 90 xu a day: LOW;
# 250 and more: HIGH; else MID. The 💼 accountants (×3 salary with their certificate) count as HIGH.
LOW, MID, HIGH = 20, 12, 8
RAISE = {
    # low-paid: the most, so nobody leaves them (tra_da 3 xu a cup, garbage 6, pagoda 7, … laundry 18, farm 21 a job;
    # the hotel / banquet / office desks pay ~60 a day with 5–7 xu a job)
    'banquet': LOW, 'com': LOW, 'drain': LOW, 'farm': LOW, 'fruit': LOW, 'garbage': LOW, 'homemaker': LOW, 'hotel': LOW,
    'ice_cream': LOW, 'laundry': LOW, 'lawyer': LOW, 'library': LOW, 'nail': LOW, 'naucom': LOW, 'pagoda': LOW,
    'photobooth': LOW, 'post_office': LOW, 'moto': LOW, 'tuning': LOW, 'radio': LOW, 'reception': LOW, 'research': LOW, 'teller': LOW, 'tra_da': LOW,
    'kol': LOW, 'singer': LOW,   # 📱 ~17 xu a deal, no salary; 🎤 ~6 xu a set + a ~62 xu salary (🎬 actor: ~97 a day, MID)
    # well-paid (florist 195 a job, clothing 133, salon 97, grocery 90, babysitter 86, mother_baby 85, …)
    'accounting': HIGH, 'babysitter': HIGH, 'clothing': HIGH, 'customer_care': HIGH, 'florist': HIGH, 'grocery': HIGH,
    'mother_baby': HIGH, 'salon': HIGH, 'teacher': HIGH, 'tour_guide': HIGH,
    'corp_accounting': HIGH, 'tax_payroll': HIGH, 'group_accounting': HIGH,
}
DEFAULT_RAISE = MID
EVENT_PCT = 20
TOOL_PCTS = (0, 2, 3, 5, 6, 8)
TOOL_PRICES = tuple(price_index.price(x) if x else 0 for x in (0, 250, 700, 1600, 3500, 7500))
TOOL_NAMES = (None, 'Hộp đồ nghề gọn', 'Bộ đồ nghề thợ quen', 'Bộ đồ nghề tay vững', 'Bộ đồ nghề cao cấp',
              'Bộ đồ nghề nghệ nhân')
TOP = 5
BOOK_PRICE = price_index.price(1500)
TIP_CHANCE, TIP_PCT, TIP_MAX = 20, 10, 40
FAST_PRICE = price_index.price(2500)
FAST_NEED = 50
ST_MAX = 999
CAP_PCT = 50
CAP_X3_PCT = 40
ROW_CAP = 500
STREAK_JOBS = 5
STREAK_XU = (0, 30, 40, 50, 60, 70, 80, 100)   # by the streak's day (1..7; more stays at the last)

_PARTS = contextvars.ContextVar('pay_boost_parts', default=None)


# ------------------------------------------------------------------ switches and the event window
def off() -> bool:
    return os.environ.get('MNL_PAYBOOST_OFF', '').strip() not in ('', '0')


def now() -> float:
    return time.time()


def _epoch(name: str) -> int | None:
    raw = (os.environ.get(name) or '').strip()
    return int(raw) if raw.isdigit() else None


def window() -> tuple[int, int] | None:
    a, b = _epoch('MNL_PAYWEEK_FROM'), _epoch('MNL_PAYWEEK_UNTIL')
    return (a, b) if a is not None and b is not None and a <= b else None


def event_on(t: float | None = None) -> bool:
    w = window()
    t = now() if t is None else t
    return bool(w) and not off() and w[0] <= t <= w[1]


def vn_day(t: float | None = None) -> str:
    return datetime.datetime.fromtimestamp(now() if t is None else t, VN).strftime('%Y-%m-%d')


def _until_text(w) -> str:
    return datetime.datetime.fromtimestamp(w[1], VN).strftime('%d/%m')


# ------------------------------------------------------------------ state
def _kit(s: dict, create: bool = False) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict):
        return None
    k = j.get(KEY)
    if not isinstance(k, dict):
        if not create:
            return None
        k = j[KEY] = dict(v=VERSION)
    return k


def tier(s: dict, career: str) -> int:
    k = _kit(s)
    return int(((k or {}).get('tool') or {}).get(career, 0))


def has(s: dict, what: str, career: str) -> bool:
    k = _kit(s)
    return career in ((k or {}).get(what) or [])


def raise_pct(career: str) -> int:
    return RAISE.get(career, DEFAULT_RAISE)


def _career_of(s: dict, c: dict) -> str | None:
    for cid, x in (s.get('careers') or {}).items():
        if x is c:
            return cid
    return None


def _story(s: dict) -> bool:
    j = s.get('journey') if isinstance(s, dict) else None
    return isinstance(j, dict) and bool(j.get('story'))


def pcts(s: dict, career: str, t: float | None = None) -> dict:
    """The parts (%) of the bonus on one earning of `career` now, already clamped: {raise, event, tools, total, cap}."""
    if off():
        return dict(raise_=0, event=0, tools=0, total=0, cap=CAP_PCT)
    from . import x3_week
    r, ev, tl = raise_pct(career), EVENT_PCT if event_on(t) else 0, TOOL_PCTS[min(TOP, tier(s, career))]
    cap = CAP_X3_PCT if x3_week.on(career, t) else CAP_PCT
    total = min(cap, r + ev + tl)
    # Clamped from the top: the tools first, then the event (the raise alone never reaches a cap).
    over = r + ev + tl - total
    cut = min(tl, over)
    tl -= cut
    over -= cut
    ev -= min(ev, over)
    return dict(raise_=r, event=ev, tools=tl, total=r + ev + tl, cap=cap)


def _hash(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


def _share(base: int, pct: int, key: str) -> int:
    whole, frac = divmod(base * pct, 100)
    if frac and _hash(f'pay|{key}|{base}') % 100 < frac:
        whole += 1
    return whole


def _note(**parts) -> None:
    box = _PARTS.get()
    if box is None:
        return
    for k, v in parts.items():
        if isinstance(v, int) and k not in ('base', 'pct'):
            box[k] = box.get(k, 0) + v
        elif v is not None:
            box[k] = v


# ------------------------------------------------------------------ the hooks
def on_earning(s: dict, c: dict, base: int, what: str, ref: str | None) -> int:
    """💰 + 🎉 + 🧰 on one earning of the player's own work (tile_match.fund_bonus, not direct): its own row in the
    fund. Returns the xu booked."""
    if off() or not _story(s) or type(base) is not int or base <= 0:
        return 0
    career = _career_of(s, c)
    if not career:
        return 0
    p = pcts(s, career)
    if p['total'] <= 0:
        return 0
    bonus = min(ROW_CAP, _share(base, p['total'], f'{ref}|{what}|{c.get("day")}'))
    if bonus <= 0:
        return 0
    ev = min(bonus, base * p['event'] // 100)
    tl = min(bonus - ev, base * p['tools'] // 100)
    rs = bonus - ev - tl
    label = f'{PREFIX} +{p["total"]}%' + (' (🎉 Tuần lễ tay nghề)' if p['event'] else '') + f' · {what}'
    from .engine import money
    money(s, c, bonus, label[:120], ref, category='other_income')
    _note(base=base, raise_=rs, event=ev, tools=tl, pct=p['total'], ref=ref)
    return bonus


def on_job(s: dict, c: dict, pay: int, title: str, ref: str | None) -> int:
    """🤝 the regular's tip and 🎉 the day's Chuyên cần, on one OWN finished job (income_gear.completion_bonus)."""
    if off() or not _story(s) or type(pay) is not int or pay <= 0:
        return 0
    career = _career_of(s, c)
    if not career:
        return 0
    from .engine import money
    got = 0
    if has(s, 'book', career) and _hash(f'tip|{ref}|{c.get("day")}|{pay}') % 100 < TIP_CHANCE:
        tip = max(1, min(TIP_MAX, pay * TIP_PCT // 100))
        money(s, c, tip, f'{TIP_PREFIX} · {title}'[:120], ref, category='other_income')
        _note(tip=tip, ref=ref)
        got += tip
    if event_on():
        got += _streak(s, c)
    return got


def _streak(s: dict, c: dict) -> int:
    k = _kit(s, create=True)
    wk = k.get('wk') if isinstance(k.get('wk'), dict) else None
    today = vn_day()
    if not wk or wk.get('d') != today:
        wk = k['wk'] = dict(d=today, n=0, got=0, s=int((wk or {}).get('s', 0)), last=(wk or {}).get('last', ''))
    wk['n'] = min(999, wk['n'] + 1)
    if wk['got'] or wk['n'] < STREAK_JOBS:
        return 0
    yesterday = (datetime.date.fromisoformat(today) - datetime.timedelta(days=1)).isoformat()
    wk['s'] = min(99, (wk['s'] if wk.get('last') == yesterday else 0) + 1)
    wk['got'], wk['last'] = 1, today
    xu = STREAK_XU[min(len(STREAK_XU) - 1, wk['s'])]
    from .engine import money
    money(s, c, xu, f'{STREAK_PREFIX} Tuần lễ tay nghề · ngày {wk["s"]} liên tiếp', f'payweek-{today}', category='other_income')
    _note(streak=xu)
    return xu


def day_total(c: dict, day: int) -> int:
    """This module's rows of a workplace's day: kept out of the 🔥 x3 day's net (journey._base_net)."""
    rows = c.get('ops', {}).get('finance', {}).get('ledger', [])
    return sum(r['amount'] for r in rows if r.get('day') == day and r.get('amount', 0) > 0
               and r.get('category') == 'other_income' and str(r.get('reason', '')).startswith((PREFIX, STREAK_PREFIX, TIP_PREFIX)))


def collect(run):
    """Attach the command's pay breakdown (result['payboost']) for the job's done screen."""
    token = _PARTS.set({})
    try:
        state, result = run()
        box = _PARTS.get()
        if box and any(box.get(k) for k in ('raise_', 'event', 'tools', 'tip', 'streak')):
            out = {('raise' if k == 'raise_' else k): v for k, v in box.items()}
            extra = sum(box.get(k, 0) for k in ('raise_', 'event', 'tools', 'tip', 'streak'))
            result = dict(result, payboost=out, message=(result.get('message') or 'Đã hoàn thành.') + f' 💰 +{extra} xu tiền công thêm.')
        return state, result
    finally:
        _PARTS.reset(token)


# ------------------------------------------------------------------ ⏩ Làm nhanh: the answer of a step from the task's key
def _ld_fast(t: dict) -> tuple[str, dict] | None:
    from .careers import laundry as L
    st = t.get('stage')
    ids = [g['id'] for g in t['needs']['garments']]
    if st == 'inspect':
        return 'ld_inspect', dict(items=ids)
    if st == 'check':
        return 'ld_check', dict(checks=list(L.CHECKS))
    if st == 'deliver':
        return 'ld_deliver', dict(tag=t['needs']['tag'])
    if st in ('sort', 'treat', 'wash', 'dry', 'finish'):
        return 'ld_' + st, dict(choices=dict(t['_key'][st]))
    return None


def _rs_fast(t: dict) -> tuple[str, dict] | None:
    from .careers import restore as R
    st, key, n = t.get('stage'), t['_key'], t['needs']
    if st in ('inspect', 'talk', 'parts', 'fix'):
        return R.PREFIX + st, dict(choices=dict(key[st]))
    if st in ('clean', 'finish'):
        return R.PREFIX + st, dict(choice=key[st])
    if st == 'check':
        return R.PREFIX + st, dict(checks=list(R.CHECK_IDS))
    if st == 'deliver':
        return R.PREFIX + st, dict(tag=n['tag'])
    return None


FAST = {'laundry': _ld_fast, 'restore': _rs_fast}


def _stage_label(career: str, t: dict) -> str:
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    labels = getattr(mod, 'LABELS', {}) if mod else {}
    return labels.get(t.get('stage'), t.get('stage') or '')


def _fast_steps(s: dict, career: str) -> list[dict]:
    """The steps counted towards ⏩, each with its name, in the order of the job."""
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    pre = mod.SPEC['prefix'] if mod else ''
    labels = getattr(mod, 'LABELS', {}) if mod else {}
    order = list(getattr(mod, 'STAGES', ()) or ())
    row = (((_kit(s) or {}).get('st') or {}).get(career) or {})
    out = []
    for a, v in row.items():
        st = a[len(pre):] if pre and a.startswith(pre) else a
        out.append((order.index(st) if st in order else len(order), a, dict(action=a, n=min(v, FAST_NEED), label=labels.get(st, st))))
    return [x[2] for x in sorted(out, key=lambda x: x[:2])]


def fast_plan(s: dict, c: dict, career: str, t: dict | None) -> tuple[str, dict] | None:
    """The step `t` is on, filled from its key, when ⏩ Làm nhanh may do it now (bought, the step done right
    FAST_NEED times by hand, the task known and open); else None."""
    if off() or career not in FAST or not t or not has(s, 'fast', career) or not t.get('known'):
        return None
    if t.get('status') in ('completed', 'referred', 'cancelled'):
        return None
    try:
        plan = FAST[career](t)
    except (KeyError, TypeError, AttributeError):
        return None
    if not plan or count(s, career, plan[0]) < FAST_NEED:
        return None
    return plan


def count(s: dict, career: str, action: str) -> int:
    k = _kit(s)
    return int((((k or {}).get('st') or {}).get(career) or {}).get(action, 0))


def counted(s: dict, career: str, action: str, result: dict, fast: bool) -> None:
    """A hand-made step of a ⏩ career answered right: one more towards FAST_NEED (fast ones never count)."""
    if fast or off() or career not in FAST or not _story(s) or not isinstance(result, dict) or result.get('correct') is not True:
        return
    from .careers import PLUGINS
    mod = PLUGINS.get(career)
    if not mod or not action.startswith(mod.SPEC['prefix']):
        return
    k = _kit(s, create=True)
    row = k.setdefault('st', {}).setdefault(career, {})
    if len(row) >= 16 and action not in row:
        return
    row[action] = min(ST_MAX, row.get(action, 0) + 1)


def resolve_fast(s: dict, c: dict, career: str, p: dict) -> tuple[str, dict]:
    """payk_fast {task}: the career's own command and payload for the step, refused unless fast_plan allows it."""
    from .engine import need, current_task
    need(not off(), 'Làm nhanh đang tạm nghỉ.')
    need(career in FAST, 'Nghề này chưa có Làm nhanh.')
    need(has(s, 'fast', career), 'Mua ⏩ Làm nhanh ở Bộ đồ nghề trước nhé.')
    t = current_task(c, p.get('task'))
    plan = fast_plan(s, c, career, t)
    need(plan is not None, f'Bước này cần làm đúng bằng tay {FAST_NEED} lần trước khi làm nhanh.')
    action, payload = plan
    return action, dict(payload, task=t['id'])


# ------------------------------------------------------------------ buying
def buy(s: dict, c: dict, career: str, p: dict) -> dict:
    """payk_buy {item: 'tool' | 'book' | 'fast'}: from the workplace fund, once (tools: the next tier)."""
    from . import engine as e
    need = e.need
    need(_story(s), 'Bộ đồ nghề chỉ có trong hành trình.')
    item = p.get('item')
    need(item in ('tool', 'book', 'fast'), 'Món này không có trong Bộ đồ nghề.')
    if item == 'tool':
        n = tier(s, career) + 1
        need(n <= TOP, 'Bộ đồ nghề đã ở bậc cao nhất.')
        price, name = TOOL_PRICES[n], f'🧰 {TOOL_NAMES[n]} (bậc {n})'
    elif item == 'book':
        need(not has(s, 'book', career), '🤝 Mối khách quen đã có rồi.')
        price, name = BOOK_PRICE, '🤝 Mối khách quen'
    else:
        need(career in FAST, 'Nghề này chưa có Làm nhanh.')
        need(not has(s, 'fast', career), '⏩ Làm nhanh đã có rồi.')
        price, name = FAST_PRICE, '⏩ Làm nhanh'
    need(c['money'] >= price, f'Quỹ nghề còn thiếu {price - max(0, c["money"])} xu để mua {name}.')
    e.money(s, c, -price, 'Mua ' + name, category='upgrade')
    k = _kit(s, create=True)
    if item == 'tool':
        k.setdefault('tool', {})[career] = n
        line = f'{name} đã sẵn sàng: tiền công nghề này +{TOOL_PCTS[n]}%.'
    else:
        k.setdefault(item, [])
        k[item].append(career)
        line = (f'{name} đã có: thỉnh thoảng khách quen boa thêm.' if item == 'book'
                else f'{name} đã có: bước nào làm đúng {FAST_NEED} lần sẽ làm được bằng một chạm.')
    e.log(s, c, 'upgrade', line)
    return dict(message=line, celebrate=True)


# ------------------------------------------------------------------ views
def public(s: dict, t: float | None = None) -> dict | None:
    """public_state['payweek']: the event (None while closed) and today's Chuyên cần."""
    if not event_on(t):
        return None
    w = window()
    k = _kit(s) or {}
    wk = k.get('wk') if isinstance(k.get('wk'), dict) else {}
    today = vn_day(t)
    n = wk.get('n', 0) if wk.get('d') == today else 0
    got = bool(wk.get('got')) if wk.get('d') == today else False
    yesterday = (datetime.date.fromisoformat(today) - datetime.timedelta(days=1)).isoformat()
    streak = wk.get('s', 0) if wk.get('last') in (today, yesterday) else 0
    nxt = STREAK_XU[min(len(STREAK_XU) - 1, streak + (0 if got else 1))]
    return dict(pct=EVENT_PCT, until=w[1], until_text=_until_text(w), jobs=min(n, STREAK_JOBS), need=STREAK_JOBS,
                got=got, streak=streak, next=nxt)


def career_public(s: dict, c: dict, career: str) -> dict | None:
    """c['paykit'] of the focused career: the pay parts now, the shop, the ⏩ step ready (None outside the story)."""
    if not _story(s):
        return None
    p = pcts(s, career)
    n = tier(s, career)
    t = None
    if c.get('active_task'):
        t = next((x for x in c.get('tasks', []) if x.get('id') == c['active_task']), None)
    plan = fast_plan(s, c, career, t) if t else None
    out = dict(off=off(), raise_pct=p['raise_'], event_pct=p['event'], tool_pct=p['tools'], total=p['total'], cap=p['cap'],
               tier=n, top=TOP, tools=[dict(n=i, name=TOOL_NAMES[i], pct=TOOL_PCTS[i], price=TOOL_PRICES[i]) for i in range(1, TOP + 1)],
               book=has(s, 'book', career), book_price=BOOK_PRICE, tip_chance=TIP_CHANCE, tip_pct=TIP_PCT,
               money=c.get('money', 0))
    if career in FAST:
        out['fast'] = dict(owned=has(s, 'fast', career), price=FAST_PRICE, need=FAST_NEED,
                           steps=_fast_steps(s, career),
                           ready=dict(task=t['id'], label=_stage_label(career, t)) if plan else None)
    return out


def news_line(t: float | None = None) -> dict | None:
    """The ticker's line while the event is on: once per Vietnam day on a device."""
    t = now() if t is None else t
    if not event_on(t):
        return None
    w = window()
    return dict(text=f'🎉 Tuần lễ tay nghề tới hết {_until_text(w)}: mọi nghề +{EVENT_PCT}% tiền công, làm đủ {STREAK_JOBS} việc '
                     f'mỗi ngày nhận thưởng Chuyên cần, ngày liên tiếp thưởng to hơn!',
                key='payweek:' + vn_day(t))


# ------------------------------------------------------------------ save
def validate(s: dict) -> None:
    from .engine import need, integer
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    k = j[KEY]
    need(isinstance(k, dict) and set(k) <= {'v', 'tool', 'book', 'fast', 'st', 'wk'}, 'Bộ đồ nghề không hợp lệ.')
    integer(k.get('v', VERSION), 1, 99)
    tool = k.get('tool', {})
    need(isinstance(tool, dict) and len(tool) <= 200, 'Bộ đồ nghề không hợp lệ.')
    for cid, n in tool.items():
        need(isinstance(cid, str) and len(cid) <= 40, 'Bộ đồ nghề không hợp lệ.')
        integer(n, 1, TOP)
    for what in ('book', 'fast'):
        rows = k.get(what, [])
        need(isinstance(rows, list) and len(rows) <= 200 and len(set(rows)) == len(rows)
             and all(isinstance(x, str) and len(x) <= 40 for x in rows), 'Bộ đồ nghề không hợp lệ.')
    st = k.get('st', {})
    need(isinstance(st, dict) and len(st) <= 200, 'Bộ đồ nghề không hợp lệ.')
    for cid, row in st.items():
        need(isinstance(cid, str) and len(cid) <= 40 and isinstance(row, dict) and len(row) <= 16, 'Bộ đồ nghề không hợp lệ.')
        for a, n in row.items():
            need(isinstance(a, str) and len(a) <= 40, 'Bộ đồ nghề không hợp lệ.')
            integer(n, 0, ST_MAX)
    wk = k.get('wk')
    if wk is not None:
        need(isinstance(wk, dict) and set(wk) == {'d', 'n', 'got', 's', 'last'}, 'Bộ đồ nghề không hợp lệ.')
        need(isinstance(wk['d'], str) and len(wk['d']) == 10 and isinstance(wk['last'], str) and len(wk['last']) <= 10,
             'Bộ đồ nghề không hợp lệ.')
        integer(wk['n'], 0, 999)
        integer(wk['got'], 0, 1)
        integer(wk['s'], 0, 99)
