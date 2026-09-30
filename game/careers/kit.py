"""Helpers shared by plugin careers.

Plugins never import the engine directly at module load (the engine imports the
plugins), so everything here resolves the engine lazily. All state changes still
run inside engine.apply_action on a deep-copied candidate state.
"""
from __future__ import annotations
import hashlib
import random
import time
from typing import Any
from .. import archive as ar
from .. import patience as pt

# Wall clock for real-time kitchen/oven timers. Tests replace `clock`.
clock = time.time


def now() -> float:
    return float(clock())


_ENGINE = None


def eng():
    global _ENGINE
    if _ENGINE is None:  # imported lazily: the engine imports the careers
        from .. import engine
        _ENGINE = engine
    return _ENGINE


def need(condition: Any, message: str, code: str = 'invalid_action') -> None:
    eng().need(condition, message, code)


def integer(value: Any, low: int = 0, high: int = 999999) -> int:
    return eng().integer(value, low, high)


def text(value: Any, max_length: int = 500, minimum: int = 1) -> str:
    return eng().clean_text(value, max_length, minimum)


def one_of(value: Any, options, message: str = 'Lựa chọn không hợp lệ.'):
    need(isinstance(value, (str, int)) and not isinstance(value, bool) and value in options, message)
    return value


def confirm(p: dict, message: str = 'Xác nhận trước khi thực hiện nhé.') -> None:
    need(p.get('confirm') is True, message)


def id_list(value: Any, allowed, max_items: int = 12, message: str = 'Danh sách lựa chọn không hợp lệ.') -> list:
    need(isinstance(value, list) and len(value) <= max_items and all(isinstance(x, str) for x in value), message)
    need(len(set(value)) == len(value) and all(x in allowed for x in value), message)
    return value


def rng(*parts) -> random.Random:
    """Deterministic generator: the same day/slot always yields the same task."""
    seed = int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16)
    return random.Random(seed)


def money(s: dict, c: dict, amount: int, reason: str, ref: str | None = None, category: str | None = None) -> None:
    eng().money(s, c, amount, reason, ref, category)


def bank(amount: int) -> None:
    """A customer's transfer / QR payment just reached the shop's own account: the browser's
    bank speaker reads it out ("ting ting · Đã nhận N xu"). Announcement only: book the money with money()."""
    from .. import bank_speaker
    bank_speaker.transfer(amount)


def log(s: dict, c: dict, kind: str, message: str, npc: str | None = None, ref: str | None = None) -> str:
    return eng().log(s, c, kind, message, npc, ref)


def metric(c: dict, key: str, n: int = 1) -> None:
    eng().metric(c, key, n)


def remember(s: dict, c: dict, npc: str, message: str, ref: str | None = None) -> None:
    eng().remember(s, c, npc, message, ref)


def complete(s: dict, c: dict, t: dict, reward: int, narrative: str, status: str = 'completed') -> None:
    """Finish a task once: pays the reward, writes memory and a persona review."""
    eng().task_done(s, c, t, reward, narrative, status)


def data(c: dict) -> dict:
    return c['ext']['data']


def level(c: dict) -> int:
    return 1 + c['xp'] // 90


def npc_id(career: str, index: int) -> str:
    return f'{career}_npc_{index + 1:02d}'


def next_id(c: dict, prefix: str) -> str:
    ext = c['ext']
    ext['seq'] = ext.get('seq', 0) + 1
    return f'{prefix}-{ext["seq"]}'


# Inventory shortcuts for trade careers (lots live in c['ext']['inv']).
def stock(c: dict, item: str) -> int:
    from .. import inventory
    return inventory.count(c, item)


def take(c: dict, item: str, qty: int = 1) -> int:
    """Consume `qty` units FIFO by expiry. Returns the recorded unit cost total."""
    from .. import inventory
    return inventory.take(c, item, qty)


def add_lot(c: dict, item: str, qty: int, unit_cost: int, life_left: int, supplier: str) -> dict:
    """Put produced/returned goods into the career's stock as a new lot
    (capacity is the caller's responsibility)."""
    from .. import inventory
    return inventory.add_lot(c, item, qty, unit_cost, life_left, supplier)


def item(career: str, item_id: str) -> dict:
    from .. import inventory
    return inventory.item(career, item_id)


def price(c: dict, key: str, default: int) -> int:
    return c['life']['prices'].get(key, default)


def waste(c: dict, item_id: str, qty: int, value: int, reason: str) -> None:
    x = c['life']
    x['day_waste'] += value
    x['waste'] = ar.last(x['waste'] + [dict(day=c['day'], item=item_id, qty=qty, value=value, reason=reason)], 120, 'life.waste', c)


def task(c: dict, p: dict) -> dict:
    """The task named in the payload (or the active one), never a finished one."""
    return eng().current_task(c, p.get('task'))


def base_task(career: str, day: int, slot: int, serial: int, npc_index: int, title: str, opening: str, **fields) -> dict:
    """Common task fields; the plugin adds its own. Everything here is derived from
    (career, day, slot) so validate_state can regenerate and compare it."""
    t = dict(id=f'{career}-{day:04d}-{slot:02d}', career=career, day=day, status='new', created_turn=serial,
             known=False, inspected=[], notes=[], mistakes=0, chat=[], kind=career, deferred=False,
             npc=npc_id(career, npc_index), title=title, opening=opening, patience=100)
    t.update(fields)
    return t


def start_work(t: dict) -> None:
    if t['status'] in ('new', 'understood'):
        t['status'] = 'in_progress'


# ------------------------------------------------------------ waiting guests (0.9.5)
# Careers where one order has many parts (stems, bowls, accessories) wear the queue down
# tap by tap. Two fairness rules, shared so every such career counts them the same way:
# * while the player keeps working one order (an action on it within BUSY_TURNS turns of
#   the last one), the others wait at BUSY_RATE speed: they see the shop busy for a guest;
# * a guest whose own order is bigger waits more patiently: the loss is divided by
#   size_factor (SIZE_STEP per unit over the career's usual size, at most SIZE_CAP).
# Losses are fractional; what is left over carries per task in the career data ('wait').
# PATIENCE_FACTOR (game/patience.py) thins each beat's loss once, before these rules, exactly as
# it thins the engine's flat -1 it replaces: the rules shape the drain, the factor stretches it.
BUSY_TURNS = 2
BUSY_RATE = 0.5
SIZE_STEP = 0.05
SIZE_CAP = 1.5
_DONE = ('completed', 'cancelled', 'referred')


def size_factor(units: int | float, base: int | float) -> float:
    """1.0 for an order of the usual size or less, up to SIZE_CAP for a big one."""
    return min(SIZE_CAP, 1.0 + SIZE_STEP * max(0.0, float(units) - float(base)))


def _wait(c: dict) -> dict:
    d = data(c)
    w = d.get('wait')
    if not isinstance(w, dict):
        w = d['wait'] = dict(task=None, turn=-1, carry={})
    return w


def busy(c: dict, task_id: str | None) -> bool:
    """The player has been working this order just now (read before `worked` records this action)."""
    w = data(c).get('wait')
    return bool(task_id) and isinstance(w, dict) and w.get('task') == task_id and 0 <= c['turn'] - w.get('turn', -99) <= BUSY_TURNS


def worked(c: dict, task_id: str | None) -> None:
    """Remember the order the player just acted on (any action on an order, physical or not)."""
    if task_id:
        w = _wait(c)
        w['task'], w['turn'] = task_id, c['turn']


def wait_loss(c: dict, t: dict, loss: int | float, busy_now: bool = False, factor: float = 1.0) -> int:
    """Take `loss` patience from a waiting task, slowed while the shop is busy and by the
    order's size factor. A gain (negative loss) is applied at once. Returns the points taken."""
    if loss <= 0:
        if loss:
            t['patience'] = max(25, min(100, t.get('patience', 100) - int(loss)))
        return 0
    w = _wait(c)
    # Rounded to 3 places before the whole points are taken, so what carries is always below 1
    # (0.999762 would round up to 1.0 and fail wait_validate).
    carry = round(float(w['carry'].get(t['id'], 0.0)) + loss * (BUSY_RATE if busy_now else 1.0) / max(1.0, factor), 3)
    n = int(carry)
    w['carry'][t['id']] = round(carry - n, 3)
    if n:
        t['patience'] = max(25, min(100, t.get('patience', 100) - n))
    return n


def wait_tick(c: dict, career: str, active_id: str | None, loss_for, factor_for=None) -> None:
    """After a physical action: every other open order of `career` loses `loss_for(t)`
    (PATIENCE_FACTOR, then the wait_loss rules). Replaces the engine's flat -1 for careers with SPEC['wait']."""
    if not c.get('open') or c['life'].get('mode') == 'calm':
        return
    open_ = [t for t in c['tasks'] if t.get('career') == career and t['status'] not in _DONE]
    w = _wait(c)
    ids = {t['id'] for t in open_}
    w['carry'] = {k: v for k, v in w['carry'].items() if k in ids}
    now = busy(c, active_id)
    for t in open_:
        if t['id'] == active_id or t.get('deferred'):
            continue
        loss = loss_for(t)
        if loss > 0:
            loss = pt.drain(c, t, loss)  # waiting (PATIENCE_FACTOR)
        wait_loss(c, t, loss, now, factor_for(t) if factor_for else 1.0)


def wait_validate(c: dict) -> None:
    w = data(c).get('wait')
    if w is None:
        return
    need(isinstance(w, dict) and (w.get('task') is None or isinstance(w['task'], str)), 'Nhịp chờ của khách không hợp lệ.')
    integer(w.get('turn'), -1, 10**9)
    need(isinstance(w.get('carry'), dict) and len(w['carry']) <= 80, 'Nhịp chờ của khách không hợp lệ.')
    for k, v in w['carry'].items():
        need(isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 1, 'Nhịp chờ của khách không hợp lệ.')


def people_count(career: str) -> int:
    from . import PLUGINS
    return len(PLUGINS[career].SPEC['people'])


# ======================================================================== v0.5 shared helpers
# (additive; used by repair, salon, pet_care, homestay — any plugin may reuse them)

# --- Task generator versions ---------------------------------------------------------------
# validate_state regenerates every saved task with make_task(day, slot, serial) and compares
# its fixed facts, so a career cannot change what old (day, slot) pairs produce. A career
# that ships a new generator marks the tasks it makes with a key (default 'gen'); in its
# validate_data it calls mark_legacy() so tasks saved earlier move their serial into the
# legacy band, and make_task() sends legacy serials to the untouched old generator.
LEGACY_TURN = 10 ** 8


def legacy(serial) -> bool:
    return type(serial) is int and serial >= LEGACY_TURN


def mark_legacy(c: dict, career: str, marker: str = 'gen') -> None:
    for t in c.get('tasks', []):
        if (isinstance(t, dict) and t.get('career') == career and marker not in t
                and type(t.get('created_turn')) is int and t['created_turn'] < LEGACY_TURN):
            t['created_turn'] += LEGACY_TURN


# --- Luck of the day --------------------------------------------------------------------------
def _daily_raw(career: str, day: int, rows: list) -> dict:
    pool = [r for r in rows if r.get('min_day', 1) <= day] or rows[:1]
    total = sum(r.get('weight', 1) for r in pool)
    x = rng(career, 'daily', day).random() * total
    for r in pool:
        x -= r.get('weight', 1)
        if x < 0:
            return r
    return pool[-1]


_DAILY_MEMO: dict = {}


def daily(career: str, day: int, rows: list) -> dict:
    """Deterministic modifier of the day (rows: dict(id, min_day, weight, …)). The same
    modifier never repeats on two days in a row when another one is possible. Each day is
    decided from the one before it, walked forward from day 1 once and remembered."""
    memo = _DAILY_MEMO.setdefault((career, id(rows)), {})
    day = max(1, int(day))
    if day not in memo:
        start = max(memo) if memo else 0
        prev = memo.get(start)
        for d in range(start + 1, day + 1):
            today = _daily_raw(career, d, rows)
            if prev is not None and today['id'] == prev['id']:
                pool = [r for r in rows if r.get('min_day', 1) <= d and r['id'] != today['id']]
                if pool:
                    today = pool[rng(career, 'daily-alt', d).randrange(len(pool))]
            memo[d] = prev = today
    return memo[day]


def tier(day: int) -> int:
    """Difficulty band from the game day: 0 first days … 3 seasoned."""
    return 0 if day <= 2 else 1 if day <= 5 else 2 if day <= 9 else 3


def review(s: dict, c: dict, npc: str, stars: int, text_: str, ref: str) -> dict:
    """Post a star review on the career feed (same channel as situation reviews)."""
    return eng().add_feed(s, c, npc, text_, ref, max(1, min(5, int(stars))), 'review')


# --- Surprise desk events ---------------------------------------------------------------------
# A career keeps `desk_initial()` in its data and a list of scripts:
#   dict(id, title, emoji, npc (people index), min_day, tone, at='open'|'between', weight,
#        need_mark / no_mark (persistent mark names), mods=(daily modifier ids) or None,
#        text, options=[dict(id, label, hint, effects=dict(...), outcome, good=True|False|None,
#        luck=dict(p=0.0..1.0, win=dict(effects, outcome, good), lose=dict(...)))], default='option id')
# Generic effects: money (int), review ([stars, text]), patience (int, all open tasks), xp (int),
# stock ({item: qty}), mark / unmark (name or list). Unknown keys go to the career `hook`.
DESK_LOG = 60


def desk_initial() -> dict:
    return dict(ev=None, last=None, log=[], plan=[], day=0, fired=0, seq=0, marks={})


def desk_plan(career: str, day: int, festival: bool = False) -> list:
    """When today's surprises happen: 'open' (morning) and/or after the n-th finished job."""
    if day <= 1:
        return []
    r = rng(career, 'desk-plan', day)
    # The street's own stories (situations) come after the first finished job,
    # so desk surprises use the morning or the 2nd+ job.
    if day <= 3:
        plan = [2]
    elif day <= 6:
        plan = [['open'], [2], ['open', 3], [2, 4]][r.randrange(4)]
    else:
        plan = [['open', 2], [2, 3], ['open', 3], ['open', 2, 4]][r.randrange(4)]
    if festival:
        plan = list(plan) + [5]
    return list(plan)


def _desk_pool(career: str, c: dict, desk: dict, scripts: list, at: str, mod_id: str | None) -> list:
    marks = desk['marks']
    rows = []
    for x in scripts:
        if x.get('min_day', 1) > c['day'] or x.get('at', 'between') not in (at, 'any'):
            continue
        if x.get('need_mark') and x['need_mark'] not in marks:
            continue
        if x.get('no_mark') and x['no_mark'] in marks:
            continue
        if x.get('mods') and mod_id not in x['mods']:
            continue
        rows.append(x)
    recent = [h['script'] for h in desk['log'][-max(1, min(len(rows) - 1, 12)):]]
    return [x for x in rows if x['id'] not in recent] or rows


def desk_fire(s: dict, c: dict, career: str, desk: dict, scripts: list, at: str, mod_id: str | None = None) -> dict | None:
    """Open one surprise now (deterministic from day and how many fired today)."""
    if desk['ev'] is not None:
        return None
    pool = _desk_pool(career, c, desk, scripts, at, mod_id)
    if not pool:
        return None
    weights = [x.get('weight', 1) for x in pool]
    pick = rng(career, 'desk', c['day'], desk['fired'], len(desk['log'])).random() * sum(weights)
    x = pool[-1]
    for row, w in zip(pool, weights):
        pick -= w
        if pick < 0:
            x = row
            break
    desk['seq'] += 1
    desk['fired'] += 1
    desk['ev'] = dict(id=f'desk-{desk["seq"]}', script=x['id'], day=c['day'], at=at)
    log(s, c, 'surprise', f'{x["emoji"]} {x["title"]}: {x["text"]}', npc_id(career, x.get('npc', 0)), desk['ev']['id'])
    return x


def desk_start(s: dict, c: dict, career: str, desk: dict, scripts: list, mod_id: str | None = None, festival: bool = False) -> None:
    """Call from on_start: plan today's surprises and fire a morning one if planned."""
    if desk['day'] != c['day']:
        desk.update(day=c['day'], fired=0, plan=desk_plan(career, c['day'], festival))
    if 'open' in desk['plan'] and desk['fired'] == 0:
        desk_fire(s, c, career, desk, scripts, 'open', mod_id) or desk_fire(s, c, career, desk, scripts, 'between', mod_id)


def desk_tick(s: dict, c: dict, career: str, desk: dict, scripts: list, mod_id: str | None = None) -> None:
    """Call after a plugin action: a surprise between customers when the plan says so."""
    if not c.get('open') or desk['ev'] is not None:
        return
    if desk['day'] != c['day']:
        desk.update(day=c['day'], fired=0, plan=desk_plan(career, c['day']))
    due = [p for p in desk['plan'] if p != 'open' and c['day_completed'] >= p]
    done = desk['fired'] - (1 if 'open' in desk['plan'] else 0)
    if len(due) > max(0, done):
        desk_fire(s, c, career, desk, scripts, 'between', mod_id)


def desk_script(scripts: list, sid: str) -> dict | None:
    return next((x for x in scripts if x['id'] == sid), None)


def desk_block(desk: dict, message: str = 'Có chuyện bất ngờ ở quầy — quyết xong rồi làm tiếp nhé.') -> None:
    need(desk['ev'] is None, message, 'surprise_open')


def _apply_effects(s: dict, c: dict, career: str, desk: dict, x: dict, eff: dict, ref: str, hook=None) -> list:
    notes = []
    for key, v in eff.items():
        if key == 'money' and v:
            amount = int(v)
            if amount < 0:
                amount = -min(-amount, c['money'])
            if amount:
                money(s, c, amount, f'{x["title"]}', ref, 'event_income' if amount > 0 else 'event_cost')
        elif key == 'review':
            review(s, c, npc_id(career, x.get('npc', 0)), v[0], v[1], ref)
        elif key == 'patience':
            for t in c['tasks']:
                if t.get('career') == career and t['status'] not in ('completed', 'referred', 'cancelled') and 'patience' in t:
                    t['patience'] = max(25, min(100, t['patience'] + int(v)))
        elif key == 'xp':
            c['xp'] += max(0, int(v))
        elif key == 'stock':
            from .. import inventory
            box = c.get('ext', {}).get('inv')
            for item_id, q in (v.items() if box else ()):
                if q > 0:
                    # Room left counts goods still on the way, like a normal order does.
                    cap = inventory.capacity(career)
                    q = min(q, max(0, cap - stock(c, item_id) - inventory._in_transit(box, item_id)))
                    if q:
                        it = item(career, item_id)
                        add_lot(c, item_id, q, 0, it.get('life') or 999, 'event')
                elif q < 0:
                    n = min(-q, stock(c, item_id))
                    if n:
                        lost = take(c, item_id, n)
                        waste(c, item_id, n, lost, x['title'])
        elif key in ('mark', 'unmark'):
            for m in ([v] if isinstance(v, str) else v):
                if key == 'mark':
                    desk['marks'][m] = c['day']
                else:
                    desk['marks'].pop(m, None)
        elif hook:
            note = hook(s, c, key, v)
            if note:
                notes.append(note)
    return notes


def desk_choose(s: dict, c: dict, career: str, desk: dict, scripts: list, option, hook=None, auto: bool = False) -> dict:
    ev = desk['ev']
    need(ev is not None, 'Không có chuyện nào đang chờ quyết.')
    x = desk_script(scripts, ev['script'])
    need(x, 'Chuyện này không còn nữa.')
    opt = next((o for o in x['options'] if o['id'] == option), None)
    need(opt, 'Lựa chọn không có trong tình huống.')
    cost = -min(0, int(opt.get('effects', {}).get('money', 0)))
    if not auto and cost:
        need(c['money'] >= cost, f'Chưa đủ {cost} xu cho lựa chọn này. Chọn cách khác nhé.')
    luck = opt.get('luck')
    result = opt
    won = None
    if luck:
        won = rng(career, 'desk-luck', ev['id'], opt['id']).random() < luck['p']
        result = luck['win'] if won else luck['lose']
    eff = dict(opt.get('effects', {}))
    for k, v in result.get('effects', {}).items() if result is not opt else ():
        eff[k] = eff.get(k, 0) + v if isinstance(v, int) and isinstance(eff.get(k), int) else v
    notes = _apply_effects(s, c, career, desk, x, eff, ev['id'], hook)
    good = result.get('good', opt.get('good'))
    outcome = ' '.join([result.get('outcome', opt.get('outcome', ''))] + notes).strip()   # hook notes belong to the outcome
    desk['last'] = dict(script=x['id'], title=x['title'], emoji=x['emoji'], choice=opt['id'], label=opt['label'],
                        outcome=outcome, good=good, day=c['day'], auto=auto)
    desk['log'] = ar.last(desk['log'] + [dict(id=ev['id'], script=x['id'], choice=opt['id'], day=c['day'], good=good, won=won)], DESK_LOG, 'desk.log', c)
    desk['ev'] = None
    metric(c, 'surprises')
    if good is True:
        metric(c, 'surprises_good')
        c['xp'] += 8
    log(s, c, 'surprise', f'{x["title"]}: {outcome}', npc_id(career, x.get('npc', 0)), ev['id'])
    return dict(message=outcome, celebrate=good is True)


def desk_close(s: dict, c: dict, career: str, desk: dict, scripts: list, hook=None) -> str | None:
    """At closing time an undecided surprise takes its default (usually passive) option."""
    ev = desk['ev']
    if ev is None:
        return None
    x = desk_script(scripts, ev['script'])
    if not x:
        desk['ev'] = None
        return None
    r = desk_choose(s, c, career, desk, scripts, x.get('default', x['options'][-1]['id']), hook, auto=True)
    return f'{x["title"]}: chưa kịp quyết nên để mặc — {r["message"]}'


def desk_public(desk: dict, scripts: list, career: str) -> dict:
    ev = desk.get('ev')
    view = None
    if ev:
        x = desk_script(scripts, ev['script'])
        if x:
            view = dict(id=ev['id'], script=x['id'], title=x['title'], emoji=x['emoji'], text=x['text'], tone=x.get('tone', 'gentle'),
                        npc=npc_id(career, x.get('npc', 0)), at=ev.get('at'),
                        options=[dict(id=o['id'], label=o['label'], hint=o.get('hint', ''),
                                      cost=-min(0, int(o.get('effects', {}).get('money', 0)))) for o in x['options']])
    return dict(ev=view, last=desk.get('last'), marks=sorted(desk.get('marks', {})), plan=list(desk.get('plan', [])),
                fired=desk.get('fired', 0), log=[dict(script=h['script'], choice=h['choice'], day=h['day'], good=h['good'])
                                                   for h in desk.get('log', [])[-8:]])


def desk_validate(desk, scripts: list) -> None:
    need(isinstance(desk, dict) and set(desk_initial()) <= set(desk), 'Sổ chuyện bất ngờ thiếu dữ liệu.')
    for k in ('day', 'fired', 'seq'):
        integer(desk[k], 0, 10 ** 9)
    need(isinstance(desk['plan'], list) and len(desk['plan']) <= 8
         and all(p == 'open' or (type(p) is int and 0 <= p <= 12) for p in desk['plan']), 'Lịch chuyện bất ngờ sai.')
    need(isinstance(desk['marks'], dict) and len(desk['marks']) <= 40, 'Dấu chuyện cũ sai.')
    for k, v in desk['marks'].items():
        text(k, 40)
        integer(v, 0, 10 ** 7)
    need(isinstance(desk['log'], list) and len(desk['log']) <= DESK_LOG, 'Lịch sử chuyện bất ngờ sai.')
    ids = {x['id'] for x in scripts}
    for h in desk['log']:
        need(isinstance(h, dict) and h.get('script') in ids and h.get('good') in (True, False, None), 'Lịch sử chuyện bất ngờ sai.')
    ev = desk['ev']
    if ev is not None:
        need(isinstance(ev, dict) and ev.get('script') in ids and ev.get('at') in ('open', 'between'), 'Chuyện bất ngờ sai.')
        text(ev.get('id'), 40)
        integer(ev.get('day'), 1, 10 ** 7)
    last = desk['last']
    if last is not None:
        need(isinstance(last, dict) and last.get('script') in ids and last.get('good') in (True, False, None), 'Kết quả chuyện bất ngờ sai.')
        text(last.get('outcome'), 600, 0)
