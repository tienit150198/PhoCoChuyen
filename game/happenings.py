"""Chuyện bất ngờ trong ca: live happenings shown in the scene.

Per workplace, stored in c['happen'] (see initial()):

* plan — rolled once when the shift opens (seeded from the journey seed, the
  workplace and its day): whether something happens today, what and after
  how many finished jobs. None in the first days, rare early, more later,
  half as often on calm days. A night break-in is rolled at opening too and
  is found right away (the loss already happened: before/after view);
* live — the happening on screen now (one at a time, never while another
  decision — a chuyện đời card, a surprise, a situation, a security case — is
  open). The player reacts (shout, chase, call 113, check the camera…); if
  they carry on working instead, the moment passes and the default applies;
* cases — police files opened by a reaction; solved (all or part back),
  or gone cold (insurance pays part if it was on when it happened) a few days
  later, announced at opening as news;
* last / history / news — results for the loss banner, the day summary and
  the "Công an phá án" notification.

Everything is decided here, seeded and stored once: the client only animates
what the public view says. Cash goes through engine.money() with a ledger
category (theft_loss, damage, compensation, recovery, insurance_recovery);
your own money goes through the journey wallet (kind 'incident'). Story mode
only (real sessions); with the story off nothing ever happens.
"""
from __future__ import annotations

import copy
import hashlib
import random

from .happening_content import HAPPENINGS, INDEX, KINDS, REACTIONS, HURT, EMPLOYEE, OFFICE, POLICE, INSURANCE_TEXT
from . import archive as ar

VERSION = 1
HISTORY = 60
CASES_MAX = 12
NEWS_MAX = 8
INSURANCE_PERCENT = 60
CASE_BASE = 25
BUILDING_CAMERA = OFFICE + ('teacher',)


def initial() -> dict:
    return dict(v=VERSION, seq=0, plan=None, live=None, last=None, history=[], cases=[], news=[], flags={},
                count=dict(day=0, n=0))


def _eng():
    from . import engine
    return engine


def _rng(*parts) -> random.Random:
    return random.Random(int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16))


def _story(s: dict) -> bool:
    return bool(s.get('journey', {}).get('story'))


def _on(s: dict) -> bool:
    return _story(s) and s.get('settings', {}).get('securityEvents', True) is not False


def _sec(c: dict) -> dict:
    return (c.get('ops') or {}).get('security') or {}


def _has(c: dict, item: str) -> bool:
    return item in _sec(c).get('items', [])


def _staff(c: dict) -> bool:
    return any(e.get('status') == 'hired' and e.get('on_shift') for e in (c.get('ops') or {}).get('staff', []))


def _reaction(x: dict, rid: str) -> dict:
    return {**REACTIONS[rid], **x['over'].get(rid, {})}


# ---------------------------------------------------------------- migration
def migrate(s: dict) -> None:
    """Older saves gain an empty book (setdefault only, nothing retroactive)."""
    for c in (s.get('careers') or {}).values():
        if not isinstance(c, dict):
            continue
        box = c.setdefault('happen', initial())
        if isinstance(box, dict):
            for k, v in initial().items():
                box.setdefault(k, copy.deepcopy(v))


# ---------------------------------------------------------------- stock
def _stock_rows(c: dict, career: str) -> list:
    """(item, name, emoji, count, unit value) of what can be taken right now."""
    e = _eng()
    rows = []
    if career == 'mother_baby':
        from .content import PRODUCT_INDEX
        for k in sorted(c.get('stock', {})):
            p = PRODUCT_INDEX.get(k)
            if p:
                rows.append((k, p['name'], '🎁', max(0, e.available(c, k)), p.get('cost', 10)))
    elif career == 'pharmacy':
        from .content import LOT_INDEX
        for k in sorted(c.get('stock', {})):
            lot = LOT_INDEX.get(k)
            if lot and lot['status'] == 'available' and k not in c.get('held_lots', []) and lot['valid_until'] >= c['day']:
                rows.append((k, lot['name'], '💊', max(0, e.available(c, k)), lot.get('cost', 8)))
    elif career == 'milk_tea':
        from . import boba
        st = boba.stock(c)
        for k, ing in boba.ING.items():
            rows.append((k, ing['name'], ing.get('emoji', '📦'), st.get(k, 0), ing.get('cost', 3)))
    else:
        from . import inventory
        if (c.get('ext') or {}).get('inv'):
            for it in inventory.catalogue(career):
                rows.append((it['id'], it['name'], it.get('emoji', '📦'), inventory.count(c, it['id']), it.get('cost', 3)))
    return [r for r in rows if r[3] > 0]


def _stock_take(c: dict, career: str, item: str, qty: int) -> int:
    row = next((r for r in _stock_rows(c, career) if r[0] == item), None)
    qty = min(qty, row[3] if row else 0)
    if qty <= 0:
        return 0
    if career in ('mother_baby', 'pharmacy'):
        c['stock'][item] -= qty
    elif career == 'milk_tea':
        left = qty
        for lot in sorted((l for l in c['life']['pantry'] if l['item'] == item and l['expires'] >= c['day'] and l['qty'] > 0),
                          key=lambda l: (l['expires'], l['received'])):
            used = min(left, lot['qty'])
            lot['qty'] -= used
            left -= used
            if not left:
                break
    else:
        from . import inventory
        inventory.take(c, item, qty)
    return qty


def _stock_give(s: dict, c: dict, career: str, item: str, qty: int, unit: int) -> int:
    """Put recovered goods back on the shelf, within the storage limit."""
    if qty <= 0:
        return 0
    if career in ('mother_baby', 'pharmacy'):
        if item not in c.get('stock', {}):
            return 0
        qty = min(qty, 24 - c['stock'][item])
        if qty > 0:
            c['stock'][item] += qty
        return max(0, qty)
    if career == 'milk_tea':
        from . import boba
        if item not in boba.ING:
            return 0
        qty = min(qty, 60 - boba.stock(c).get(item, 0))
        if qty > 0:
            boba.add_lot(s, c, item, qty, min(20, unit))
        return max(0, qty)
    from . import inventory
    if not (c.get('ext') or {}).get('inv'):
        return 0
    it = next((x for x in inventory.catalogue(career) if x['id'] == item), None)
    if not it:
        return 0
    qty = min(qty, inventory.capacity(career) - inventory.count(c, item))
    if qty > 0:
        inventory.add_lot(c, item, qty, min(10000, unit), inventory._life(it), 'recovered')
    return max(0, qty)


# ---------------------------------------------------------------- money
def _wallet(s: dict, amount: int, label: str, career: str) -> None:
    from . import journey as jr
    jr._wallet(s['journey'], amount, 'incident', label, career)


def _charge(s: dict, c: dict, career: str, amount: int, label: str, ref: str, cat: str) -> list:
    """A cost from the workplace fund; what the fund lacks comes from the wallet."""
    e = _eng()
    out = []
    take = min(amount, c['money'])
    if take > 0:
        e.money(s, c, -take, label, ref, cat)
        out.append(dict(where='fund', amount=-take, cat=cat))
    rest = amount - max(0, take)
    if rest > 0:
        _wallet(s, -rest, label, career)
        out.append(dict(where='wallet', amount=-rest, cat=cat))
    return out


def _credit(s: dict, c: dict, career: str, amount: int, label: str, ref: str, cat: str, where: str = 'fund') -> list:
    if amount <= 0:
        return []
    if where == 'wallet':
        _wallet(s, amount, label, career)
    else:
        _eng().money(s, c, amount, label, ref, cat)
    return [dict(where=where, amount=amount, cat=cat)]


# ---------------------------------------------------------------- when things happen
def rate(day: int, mode: str = 'normal') -> float:
    """Chance that a workplace day has a live happening: none at first, then more."""
    if day <= 2:
        return 0.0
    p = 0.15 if day <= 5 else 0.25 if day <= 9 else 0.32
    if mode == 'calm':
        p *= 0.5
    elif mode == 'festival':
        p += 0.1
    return min(0.5, p)


def night_rate(c: dict, day: int, mode: str = 'normal') -> float:
    """Chance of finding a break-in at opening. A better lock and a porch light help."""
    if day <= 4:
        return 0.0
    p = 0.08
    lock = c.get('happen', {}).get('flags', {}).get('new_lock')
    if _has(c, 'lock') or (lock is not None and day - lock <= 20):
        p *= 0.5
    if _has(c, 'light'):
        p -= 0.02
    if mode == 'calm':
        p *= 0.5
    return max(0.0, p)


def _pool(c: dict, career: str, box: dict, morning: bool) -> list:
    rows = [x for x in HAPPENINGS if career in x['careers'] and x['min_day'] <= c['day'] and x['morning'] == morning]
    recent = {h['script'] for h in box['history'][-8:]}
    return [x for x in rows if x['id'] not in recent] or rows


def _pick(r: random.Random, pool: list) -> dict | None:
    if not pool:
        return None
    weights = [x['weight'] * (2 if len(x['careers']) <= 3 else 1) for x in pool]
    pick = r.random() * sum(weights)
    for x, w in zip(pool, weights):
        pick -= w
        if pick < 0:
            return x
    return pool[-1]


def roll_plan(s: dict, c: dict, career: str) -> tuple:
    """(morning script or None, today's plan or None). Pure function of (seed, career, day, history)."""
    box = c['happen']
    day = c['day']
    mode = (c.get('life') or {}).get('mode', 'normal')
    r = _rng('happen-plan', s.get('journey', {}).get('seed', 0), career, day)
    night, later, at = r.random(), r.random(), 1 + r.randrange(2)
    morning = _pick(r, _pool(c, career, box, True)) if night < night_rate(c, day, mode) else None
    plan = None
    if later < rate(day, mode) * (0.5 if morning else 1):
        x = _pick(r, _pool(c, career, box, False))
        if x:
            plan = dict(day=day, at=at, script=x['id'], fired=False)
    return morning, plan


def _busy(c: dict) -> bool:
    from . import incidents as incs
    inc = c.get('incidents') or {}
    if inc.get('active') and not inc['active'].get('practice'):
        return True
    return incs._busy(c)


def _amount(r: random.Random, span, day: int) -> int:
    lo, hi = span
    base = lo + r.randrange(hi - lo + 1)
    return base * (100 + min(day, 40) * 2) // 100


def _fire(s: dict, c: dict, career: str, sid: str) -> dict:
    e = _eng()
    box = c['happen']
    x = INDEX[sid]
    box['seq'] += 1
    rid = f'hap-{box["seq"]}'
    r = _rng('happen-fire', s.get('journey', {}).get('seed', 0), career, c['day'], sid, box['seq'])
    facts = dict(stock=[], cash=0, damage=0, comp=0, wallet=0)
    loss = x['loss']
    if 'stock' in loss:
        rows = _stock_rows(c, career)
        if rows:
            want = _amount(r, loss['stock'], 0)
            picks = r.sample(rows, min(len(rows), 2 if want >= 3 else 1))
            for i, row in enumerate(picks):
                q = min(row[3], want if len(picks) == 1 else (want + 1) // 2 if i == 0 else want // 2)
                if q > 0:
                    facts['stock'].append([row[0], q, row[4]])
        elif 'cash' not in loss:
            facts['cash'] = _amount(r, (10, 30), c['day'])   # nothing on the shelf: the till instead
    for k in ('cash', 'damage', 'comp', 'wallet'):
        if k in loss:
            facts[k] = _amount(r, loss[k], c['day'])
    live = dict(id=rid, script=sid, day=c['day'], turn=c['turn'], morning=x['morning'], facts=facts, applied=[],
                before=[], camera=_camera(c, career), insured=bool(_sec(c).get('insurance')), staff=_staff(c),
                _roll=r.randrange(100), _hurt=r.randrange(100), _solve=r.randrange(100), _hurt_cost=_amount(r, HURT['cost'], 0))
    if x['morning']:
        live['before'], live['applied'] = _apply(s, c, career, x, live, 100)
    box['live'] = live
    if box['count']['day'] != c['day']:
        box['count'] = dict(day=c['day'], n=0)
    box['count']['n'] += 1
    e.log(s, c, 'happen', f'{x["emoji"]} {x["title"]}', ref=rid)
    return live


def _apply(s: dict, c: dict, career: str, x: dict, live: dict, pct: int) -> tuple:
    """Take pct% of the rolled loss. Returns (before/after rows, money lines)."""
    f = live['facts']
    rid = live['id']
    lines, rows = [], []
    rows_now = {r[0]: r for r in _stock_rows(c, career)}
    for item, qty, unit in f['stock']:
        q = qty * pct // 100
        before = rows_now.get(item, (item, item, '📦', 0, unit))
        got = _stock_take(c, career, item, q)
        if got:
            rows.append(dict(item=item, name=before[1], emoji=before[2], before=before[3], after=before[3] - got, qty=got, value=got * unit))
            lines.append(dict(where='stock', amount=-got * unit, cat='theft_loss' if x['kind'] in ('trom', 'dem') else 'damage'))
    cash = f['cash'] * pct // 100
    if cash:
        if career in EMPLOYEE:
            # The shortage is on your watch: half comes out of your pay.
            mine = cash // 2
            lines += _charge(s, c, career, cash - mine, x['label'], rid, 'theft_loss')
            _wallet(s, -mine, 'Trừ lương bù tiền thiếu', career)
            lines.append(dict(where='wallet', amount=-mine, cat='theft_loss'))
        else:
            take = min(cash, c['money'])      # a thief cannot take more than the till holds
            if take:
                _eng().money(s, c, -take, x['label'], rid, 'theft_loss')
                lines.append(dict(where='fund', amount=-take, cat='theft_loss'))
    dmg = f['damage'] * pct // 100
    if dmg:
        lines += _charge(s, c, career, dmg, x['label'], rid, 'damage')
    comp = f['comp'] * pct // 100
    if comp:
        lines += _charge(s, c, career, comp, x['label'], rid, 'compensation')
    wal = f['wallet'] * pct // 100
    if wal:
        _wallet(s, -wal, x['label'], career)
        lines.append(dict(where='wallet', amount=-wal, cat='compensation' if x['kind'] == 'den' else 'theft_loss'))
    return rows, lines


def _lost(lines: list) -> dict:
    """What was lost, split by where it hurts (stock value counts for the case file)."""
    out = dict(fund=0, wallet=0, stock=0)
    for ln in lines:
        if ln['amount'] < 0:
            out[ln['where']] += -ln['amount']
    return out


def after(s: dict, c: dict, career: str, action: str, result: dict) -> None:
    """Engine hook after every successful action (before validation)."""
    box = c.get('happen')
    if not isinstance(box, dict):
        return
    if action == 'start_day' and c['open']:
        box['plan'] = None
        if not _on(s):
            return
        _police(s, c, career, result)
        morning, plan = roll_plan(s, c, career)
        box['plan'] = plan
        if morning and not box['live'] and not _busy(c):
            live = _fire(s, c, career, morning['id'])
            result['happening'] = live['id']
            result.setdefault('effects', []).append(f'{morning["emoji"]} {morning["title"]}')
        return
    if not c['open'] or not _on(s) or action.startswith('hap_') or action == 'end_day':
        return
    live = box['live']
    if live and c['turn'] > live['turn']:
        # You carried on working: the moment passed.
        x = INDEX[live['script']]
        resolve(s, c, career, x['default'], auto=True)
        result['happen_auto'] = live['id']
        result.setdefault('effects', []).append(f'{x["emoji"]} {x["title"]}: chuyện đã qua, không kịp xử lý.')
        return
    if live or c['day_completed'] < 1:
        return
    n = box['count']['n'] if box['count']['day'] == c['day'] else 0
    plan = box['plan']
    if n >= 1 or not plan or plan['day'] != c['day'] or plan['fired'] or c['day_completed'] < plan['at'] or _busy(c):
        return
    plan['fired'] = True
    live = _fire(s, c, career, plan['script'])
    x = INDEX[plan['script']]
    result['happening'] = live['id']
    result.setdefault('effects', []).append(f'{x["emoji"]} {x["title"]}')


# ---------------------------------------------------------------- reacting
def _chance(c: dict, live: dict, r: dict) -> int:
    p = r.get('p', 0)
    if not p:
        return 0
    b = r.get('bonus', {})
    p += b.get('bell', 0) * _has(c, 'bell') + b.get('light', 0) * _has(c, 'light') + b.get('staff', 0) * live['staff']
    return min(90, p)


def _enabled(c: dict, live: dict, r: dict) -> bool:
    return r.get('needs') != 'camera' or live['camera']


def _camera(c: dict, career: str) -> bool:
    """Installed at the shop, or the school / office building has its own."""
    return _has(c, 'camera') or career in BUILDING_CAMERA


def _feed(s: dict, c: dict, career: str, text: str, ref: str, stars=None, kind='post', seed=0) -> None:
    e = _eng()
    npcs = [k for k in (f'{career}_npc_{i:02d}' for i in range(1, 7)) if k in e.NPC_INDEX]
    if npcs:
        post = e.add_feed(s, c, npcs[seed % len(npcs)], text, ref, stars, kind)
        post['happen'] = ref


def _trust(c: dict, delta: int) -> None:
    inc = c.get('incidents')
    if delta and isinstance(inc, dict) and isinstance(inc.get('trust'), int):
        inc['trust'] = max(0, min(100, inc['trust'] + delta))


def resolve(s: dict, c: dict, career: str, rid: str, auto: bool = False) -> dict:
    e = _eng()
    box = c['happen']
    live = box['live']
    e.need(live, 'Chuyện này đã qua rồi.', 'already_decided')
    x = INDEX[live['script']]
    e.need(rid in x['reactions'], 'Cách này không dùng được lúc này.')
    r = _reaction(x, rid)
    e.need(_enabled(c, live, r), 'Chưa có camera ghi hình nên chưa xem lại được.', 'not_available')
    p = _chance(c, live, r)
    won = live['_roll'] < p if p else None
    kind = x['kind']
    lines, rows = list(live['applied']), list(live['before'])
    insurance = 0
    if kind == 'den':
        factor = r.get('pay', 100) if won is not False else r.get('pay_lose', r.get('pay', 100))
        comp = live['facts']['comp'] * factor // 100
        wal = live['facts']['wallet'] * factor // 100
        if comp:
            lines += _charge(s, c, career, comp, x['label'], live['id'], 'compensation')
        if wal:
            _wallet(s, -wal, x['label'], career)
            lines.append(dict(where='wallet', amount=-wal, cat='compensation'))
    elif not live['morning']:
        rows, got = _apply(s, c, career, x, live, r.get('share', 0) if won else 100)
        lines += got
    lost = _lost(lines)
    if live['morning'] and won:
        # Found and paid back: the culprit returns what was taken (as money).
        lines += _credit(s, c, career, lost['fund'] + lost['stock'], 'Người gây chuyện đền lại', live['id'], 'recovery')
        lines += _credit(s, c, career, lost['wallet'], 'Người gây chuyện đền lại', live['id'], 'recovery', 'wallet')
        lost = dict(fund=0, wallet=0, stock=0)
    if r.get('extra'):
        cat, amount, label = r['extra']
        lines += _charge(s, c, career, amount, label, live['id'], cat)
    hurt = bool(r.get('hurt')) and won is False and live['_hurt'] < r['hurt']
    if hurt:
        _wallet(s, -live['_hurt_cost'], 'Tiền thuốc sau vụ giằng co', career)
        lines.append(dict(where='wallet', amount=-live['_hurt_cost'], cat='medical'))
    total = lost['fund'] + lost['wallet'] + lost['stock']
    case = None
    if r.get('case') and kind != 'den' and total > 0 and len(box['cases']) < CASES_MAX:
        stolen = [[row['item'], row['qty'], row['value'] // max(1, row['qty'])] for row in rows][:4]
        case = dict(id=f'case-{live["id"]}', src=live['id'], script=x['id'], day=c['day'], due=c['day'] + 1 + live['_solve'] % 3,
                    camera=live['camera'] and (rid == 'camera' or live['morning']), witness=bool(r.get('witness')),
                    insured=live['insured'], fund=lost['fund'], wallet=lost['wallet'], stock=stolen, _solve=live['_solve'])
        box['cases'].append(case)
    elif kind == 'pha' and live['insured'] and total > 0:
        # Accidental damage is covered without a police file; theft needs one.
        insurance = (lost['fund'] + lost['stock']) * INSURANCE_PERCENT // 100
        lines += _credit(s, c, career, insurance, 'Bảo hiểm tài sản chi trả', live['id'], 'insurance_recovery')
    trust = r.get('trust', 0) + (r.get('trust_win', 0) if won else r.get('trust_lose', 0) if won is False else 0)
    _trust(c, trust)
    if r.get('flag'):
        box['flags'][r['flag']] = c['day']
    review = r.get('review_lose') if won is False else None
    if review:
        _feed(s, c, career, review[1], live['id'], review[0], 'review', live['_solve'])
    if x.get('gossip') and total > 0:
        _feed(s, c, career, x['gossip'], live['id'], seed=live['_roll'])
    if kind == 'den':
        good = r.get('good') if won is None else (None if won and rid != 'refuse' else False)
    elif rid in ('let', 'forgive', 'clean'):
        good = None
    elif kind == 'dem':
        good = True
    else:
        good = True if won else None
    outcome = r['win'] if won or won is None else r['lose']
    e.metric(c, 'happenings')
    if won and kind in ('trom', 'pha'):
        e.metric(c, 'happenings_stopped')
        c['xp'] += 6
    e.log(s, c, 'happen', f'{x["title"]}: {outcome}', ref=live['id'])
    fund = sum(ln['amount'] for ln in lines if ln['where'] == 'fund')
    wallet = sum(ln['amount'] for ln in lines if ln['where'] == 'wallet')
    stock = sum(ln['amount'] for ln in lines if ln['where'] == 'stock')
    box['history'] = (box['history'] + [dict(id=live['id'], script=x['id'], choice=rid, day=live['day'], won=won, good=good,
                                             auto=auto, fund=fund, wallet=wallet, stock=stock, case=bool(case), hurt=hurt)])[-HISTORY:]
    box['last'] = dict(id=live['id'], script=x['id'], choice=rid, day=live['day'], won=won, good=good, auto=auto,
                       lines=lines[-12:], items=[dict(name=w['name'], emoji=w['emoji'], qty=w['qty'], before=w['before'], after=w['after'])
                                                 for w in rows][:6],
                       hurt=hurt, case=bool(case), trust=trust, insurance=insurance)
    box['live'] = None
    return dict(message=outcome, celebrate=bool(won) and kind in ('trom', 'pha'))


# ---------------------------------------------------------------- police follow-ups
def _police(s: dict, c: dict, career: str, result: dict) -> None:
    """At opening: files that are due get their result (seeded when they were opened)."""
    box = c['happen']
    due = [k for k in box['cases'] if k['due'] <= c['day']]
    for k in due:
        box['cases'].remove(k)
        x = INDEX[k['script']]
        chance = min(90, CASE_BASE + 35 * k['camera'] + 15 * k['witness'] + 10 * (x['kind'] == 'pha'))
        pct = 100 if k['_solve'] < chance // 2 else 50 if k['_solve'] < chance else 0
        outcome = 'solved' if pct == 100 else 'partial' if pct else 'cold'
        lines, items = [], []
        stock_money = 0
        for item, qty, unit in k['stock']:
            back = qty * pct // 100
            put = _stock_give(s, c, career, item, back, unit)
            if put:
                row = next((r for r in _stock_rows(c, career) if r[0] == item), None)
                items.append(dict(name=row[1] if row else item, emoji=row[2] if row else '📦', qty=put))
            stock_money += (back - put) * unit       # what does not fit back comes as money
        fund_back = (k['fund'] * pct // 100) + stock_money
        lines += _credit(s, c, career, fund_back, 'Công an trả lại tang vật', k['id'], 'recovery')
        lines += _credit(s, c, career, k['wallet'] * pct // 100, 'Công an trả lại tang vật', k['id'], 'recovery', 'wallet')
        insurance = 0
        if pct < 100 and k['insured']:
            stock_value = sum(q * u for _, q, u in k['stock'])
            residual = (k['fund'] + stock_value) * (100 - pct) // 100
            insurance = residual * INSURANCE_PERCENT // 100
            lines += _credit(s, c, career, insurance, 'Bảo hiểm tài sản chi trả', k['id'], 'insurance_recovery')
        if pct:
            _trust(c, 2)
            _feed(s, c, career, 'Nghe nói công an phường vừa bắt được đứa gây chuyện ở tiệm mình quen. Khu mình yên tâm hơn rồi!',
                  k['id'], seed=k['_solve'])
        emoji, title, text = POLICE[outcome]
        news = dict(id=k['id'], script=k['script'], outcome=outcome, day=c['day'], lines=lines, items=items, insurance=insurance,
                    seen=False)
        box['news'] = ar.last(box['news'] + [news], NEWS_MAX, 'happen.news', c)
        box['history'] = [dict(h, police=outcome) if h['id'] == k['src'] else h for h in box['history']]
        _eng().log(s, c, 'happen', f'{emoji} {title}: {x["title"]}', ref=k['id'])
        result.setdefault('effects', []).append(f'{emoji} {title}: {x["title"]}')
        result['police'] = k['id']


# ---------------------------------------------------------------- actions
def action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    e = _eng()
    box = c['happen']
    if name == 'hap_react':
        live = box['live']
        e.need(live, 'Chuyện này đã qua rồi.', 'already_decided')
        e.need(p.get('id') in (None, live['id']), 'Chuyện này đã qua rồi.', 'already_decided')
        e.need(c['open'], 'Ca đã khép rồi.')
        e.need(isinstance(p.get('choice'), str), 'Chọn một cách xử lý nhé.')
        return resolve(s, c, career, p['choice'])
    if name == 'hap_ack':
        hit = [n for n in box['news'] if n['id'] == p.get('id') or p.get('id') is None]
        for n in hit:
            n['seen'] = True
        return dict(message='Đã xem tin.')
    raise e.GameError('Thao tác không hợp lệ.')


def on_close(s: dict, c: dict, career: str) -> dict | None:
    """Closing time: a happening still on screen takes its default; today's list for the summary."""
    box = c.get('happen')
    if not isinstance(box, dict):
        return None
    if box['live']:
        resolve(s, c, career, INDEX[box['live']['script']]['default'], auto=True)
    box['plan'] = None
    today = [h for h in box['history'] if h['day'] == c['day']]
    news = [n for n in box['news'] if n['day'] == c['day']]
    if not today and not news:
        return None
    return dict(items=[_history_view(h) for h in today], news=[_news_view(n) for n in news])


# ---------------------------------------------------------------- public view
def _history_view(h: dict) -> dict:
    x = INDEX[h['script']]
    r = _reaction(x, h['choice'])
    return dict(id=h['id'], script=x['id'], emoji=x['emoji'], title=x['title'], kind=x['kind'], kind_label=KINDS[x['kind']][1],
                label=x['label'], choice=r['label'], outcome=r['win'] if h['won'] or h['won'] is None else r['lose'],
                good=h['good'], auto=h['auto'], day=h['day'], fund=h['fund'], wallet=h['wallet'], stock=h['stock'],
                case=h['case'], hurt=h['hurt'], police=h.get('police'))


def _news_view(n: dict) -> dict:
    x = INDEX[n['script']]
    emoji, title, text = POLICE[n['outcome']]
    return dict(id=n['id'], outcome=n['outcome'], emoji=emoji, title=title, text=text, about=x['title'], about_emoji=x['emoji'],
                day=n['day'], lines=copy.deepcopy(n['lines']), items=copy.deepcopy(n['items']),
                insurance=n['insurance'], insurance_text=INSURANCE_TEXT if n['insurance'] else '', seen=n['seen'])


def public(c: dict, career: str, s: dict) -> dict:
    box = c.get('happen') or initial()
    view = dict(live=None, last=None, news=[_news_view(n) for n in box['news'] if not n['seen']],
                cases=[dict(id=k['id'], title=INDEX[k['script']]['title'], emoji=INDEX[k['script']]['emoji'], day=k['day'])
                       for k in box['cases']],
                log=[_history_view(h) for h in reversed(box['history'][-10:])])
    live = box['live']
    if live:
        x = INDEX[live['script']]
        emoji, label = KINDS[x['kind']]
        reactions = []
        for rid in x['reactions']:
            r = _reaction(x, rid)
            ok = _enabled(c, live, r)
            reactions.append(dict(id=rid, label=r['label'], hint=r['hint'], enabled=ok,
                                  why='' if ok else 'Chưa lắp camera', default=rid == x['default']))
        view['live'] = dict(id=live['id'], script=x['id'], kind=x['kind'], kind_emoji=emoji, kind_label=label, emoji=x['emoji'],
                            title=x['title'], text=x['text'], anim=x['anim'], actor=x['actor'], target=x['target'],
                            morning=live['morning'], label=x['label'], reactions=reactions,
                            before=[dict(name=w['name'], emoji=w['emoji'], before=w['before'], after=w['after']) for w in live['before']][:6],
                            lines=copy.deepcopy(live['applied']) if live['morning'] else [])
    last = box['last']
    if last:
        x = INDEX[last['script']]
        r = _reaction(x, last['choice'])
        view['last'] = dict(id=last['id'], script=x['id'], day=last['day'], emoji=x['emoji'], title=x['title'], kind=x['kind'],
                            label=x['label'], choice=r['label'], outcome=r['win'] if last['won'] or last['won'] is None else r['lose'],
                            good=last['good'], won=last['won'], auto=last['auto'], lines=copy.deepcopy(last['lines']),
                            items=copy.deepcopy(last['items']), hurt=last['hurt'], hurt_text=HURT['text'] if last['hurt'] else '',
                            case=last['case'], trust=last['trust'], insurance=last['insurance'])
    return view


def catalogue() -> list[dict]:
    return [dict(id=x['id'], kind=x['kind'], title=x['title'], careers=list(x['careers']), anim=x['anim']) for x in HAPPENINGS]


# ---------------------------------------------------------------- validation
def _lines_ok(lines, need, integer, txt, limit=16) -> None:
    need(isinstance(lines, list) and len(lines) <= limit, 'Dòng tiền chuyện bất ngờ sai.')
    for ln in lines:
        need(isinstance(ln, dict) and ln.get('where') in ('fund', 'wallet', 'stock'), 'Dòng tiền chuyện bất ngờ sai.')
        integer(ln.get('amount'), -10**6, 10**6)
        txt(ln.get('cat'), 40)


def validate(c: dict, career: str) -> None:
    e = _eng()
    need, integer, txt = e.need, e.integer, e.clean_text
    box = c.get('happen')
    need(isinstance(box, dict) and set(initial()) <= set(box), 'Sổ chuyện bất ngờ thiếu dữ liệu.', 'invalid_save')
    need(box['v'] == VERSION, 'Phiên bản sổ chuyện bất ngờ không hợp lệ.', 'invalid_save')
    integer(box['seq'], 0, 10**9)
    need(isinstance(box['count'], dict), 'Bộ đếm chuyện bất ngờ sai.')
    integer(box['count'].get('day'), 0, 10**7)
    integer(box['count'].get('n'), 0, 50)
    plan = box['plan']
    if plan is not None:
        need(isinstance(plan, dict) and plan.get('script') in INDEX and not INDEX[plan['script']]['morning'], 'Kế hoạch chuyện bất ngờ sai.')
        integer(plan.get('day'), 1, 10**7)
        integer(plan.get('at'), 1, 3)
        need(type(plan.get('fired')) is bool, 'Kế hoạch chuyện bất ngờ sai.')
    live = box['live']
    if live is not None:
        need(isinstance(live, dict) and live.get('script') in INDEX, 'Chuyện bất ngờ đang mở sai.')
        txt(live.get('id'), 40)
        integer(live.get('day'), 1, 10**7)
        integer(live.get('turn'), 0, 10**9)
        for k in ('morning', 'camera', 'insured', 'staff'):
            need(type(live.get(k)) is bool, 'Chuyện bất ngờ đang mở sai.')
        for k in ('_roll', '_hurt', '_solve'):
            integer(live.get(k), 0, 99)
        integer(live.get('_hurt_cost'), 0, 1000)
        f = live.get('facts')
        need(isinstance(f, dict) and isinstance(f.get('stock'), list) and len(f['stock']) <= 4, 'Chuyện bất ngờ đang mở sai.')
        for row in f['stock']:
            need(isinstance(row, list) and len(row) == 3 and isinstance(row[0], str), 'Chuyện bất ngờ đang mở sai.')
            integer(row[1], 1, 100)
            integer(row[2], 0, 10**4)
        for k in ('cash', 'damage', 'comp', 'wallet'):
            integer(f.get(k), 0, 10**5)
        _lines_ok(live.get('applied'), need, integer, txt)
        need(isinstance(live.get('before'), list) and len(live['before']) <= 6, 'Chuyện bất ngờ đang mở sai.')
    last = box['last']
    if last is not None:
        need(isinstance(last, dict) and last.get('script') in INDEX and last.get('choice') in INDEX[last['script']]['reactions'],
             'Kết quả chuyện bất ngờ sai.')
        need(last.get('won') in (True, False, None) and last.get('good') in (True, False, None), 'Kết quả chuyện bất ngờ sai.')
        _lines_ok(last.get('lines'), need, integer, txt)
        need(isinstance(last.get('items'), list) and len(last['items']) <= 6, 'Kết quả chuyện bất ngờ sai.')
        integer(last.get('trust'), -100, 100)
        integer(last.get('insurance'), 0, 10**6)
    need(isinstance(box['history'], list) and len(box['history']) <= HISTORY, 'Lịch sử chuyện bất ngờ sai.')
    for h in box['history']:
        need(isinstance(h, dict) and h.get('script') in INDEX and h.get('choice') in INDEX[h['script']]['reactions'],
             'Lịch sử chuyện bất ngờ sai.')
        need(h.get('won') in (True, False, None) and h.get('good') in (True, False, None), 'Lịch sử chuyện bất ngờ sai.')
        integer(h.get('day'), 1, 10**7)
        for k in ('fund', 'wallet', 'stock'):
            integer(h.get(k), -10**6, 10**6)
        need(h.get('police') in (None, 'solved', 'partial', 'cold'), 'Lịch sử chuyện bất ngờ sai.')
    need(isinstance(box['cases'], list) and len(box['cases']) <= CASES_MAX, 'Hồ sơ công an sai.')
    for k in box['cases']:
        need(isinstance(k, dict) and k.get('script') in INDEX, 'Hồ sơ công an sai.')
        txt(k.get('id'), 60)
        txt(k.get('src'), 40)
        integer(k.get('day'), 1, 10**7)
        integer(k.get('due'), 1, 10**7)
        for key in ('camera', 'witness', 'insured'):
            need(type(k.get(key)) is bool, 'Hồ sơ công an sai.')
        integer(k.get('fund'), 0, 10**6)
        integer(k.get('wallet'), 0, 10**6)
        integer(k.get('_solve'), 0, 99)
        need(isinstance(k.get('stock'), list) and len(k['stock']) <= 4, 'Hồ sơ công an sai.')
    need(isinstance(box['news'], list) and len(box['news']) <= NEWS_MAX, 'Tin công an sai.')
    for n in box['news']:
        need(isinstance(n, dict) and n.get('script') in INDEX and n.get('outcome') in POLICE, 'Tin công an sai.')
        integer(n.get('day'), 1, 10**7)
        need(type(n.get('seen')) is bool, 'Tin công an sai.')
        _lines_ok(n.get('lines'), need, integer, txt)
        integer(n.get('insurance'), 0, 10**6)
    need(isinstance(box['flags'], dict) and len(box['flags']) <= 20, 'Dấu chuyện bất ngờ sai.')
    for k, v in box['flags'].items():
        txt(k, 40)
        integer(v, 0, 10**7)
