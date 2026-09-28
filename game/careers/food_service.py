"""Shared day rhythm for the three small shops (restaurant, cafe_bakery, florist).

Not a career itself (it is not listed in careers.ORDER). It gives each shop:

* the luck of the day: one modifier rolled from (career, day) — rain, a rush
  hour, a festival… — so orders, prices and pacing change from day to day;
* surprises: one or two events per day that open after the n-th served order
  and wait for a real decision with consequences (fines, lost stock, a big
  catering order, a critic at the corner table…);
* guests with personalities (in a hurry, chatty, picky, generous, regulars
  whose little stories move on with each visit);
* walk-in customers on busy days, a streak bonus and an end-of-day grade.

Everything is rolled deterministically from (career, day, slot) and stored in
the career's ext data, so reloading never rerolls. Each career owns the event
texts and what a choice does (`apply(s, c, plan, choice) -> (text, good)`).
"""
from __future__ import annotations
from . import kit

DONE = ('completed', 'cancelled', 'referred')
PERSONAS = dict(
    plain=('🙂', 'Khách mới'),
    regular=('🏠', 'Khách quen'),
    rush=('⏱️', 'Đang vội'),
    chatty=('💬', 'Vui chuyện'),
    picky=('🧐', 'Khó tính'),
    kid=('🧒', 'Khách nhí'),
    elder=('🧓', 'Người lớn tuổi'),
    tourist=('🧳', 'Khách phương xa'),
    generous=('💝', 'Hào phóng'),
)
EVENT_STATUS = ('waiting', 'open', 'done', 'missed', 'skipped')
GRADES = (('S', 90), ('A', 78), ('B', 62), ('C', 45), ('D', 0))
GRADE_BONUS = dict(S=12, A=6)
STREAK_BONUS_AT = 5
STREAK_BONUS = 10
PLAN_COUNTERS = ('served', 'perfect', 'refused', 'patience', 'walkins', 'sales', 'missed', 'flash_n', 'tips')


def guest(kind: str) -> dict:
    emoji, label = PERSONAS[kind]
    return dict(kind=kind, emoji=emoji, label=label)


def open_tasks(c: dict, cid: str) -> list[dict]:
    return [t for t in c['tasks'] if t['career'] == cid and t['status'] not in DONE]


# ---------------------------------------------------------------- the day plan
def pick_mod(cid: str, day: int, mods: list[dict]) -> dict:
    """Luck of the day. Day 1 is always the first (gentle) modifier."""
    if day <= 1:
        return mods[0]
    def pool_for(d: int) -> list[dict]:
        return [m for m in mods if m.get('min_day', 1) <= d]

    def raw(d: int) -> dict:
        r = kit.rng(cid, 'mod', d)
        pool_d = pool_for(d)
        return r.choices(pool_d, [m.get('weight', 1) for m in pool_d])[0]
    pool = pool_for(day)
    first = raw(day)
    if len(pool) > 1 and day > 2 and first['id'] == raw(day - 1)['id']:
        # Avoid the same luck two days in a row.
        rest = [m for m in pool if m['id'] != first['id']]
        return rest[kit.rng(cid, 'mod2', day).randrange(len(rest))]
    return first


def roll_events(cid: str, day: int, events: list[dict], mod_id: str) -> list[dict]:
    """Which surprises happen today and after how many served orders."""
    def pool_for(d: int) -> list[dict]:
        return [e for e in events if e.get('min_day', 1) <= d and mod_id not in e.get('not_mods', ())
                and (not e.get('mods') or mod_id in e['mods'])]
    pool = pool_for(day)
    if day <= 1:
        pool = [e for e in pool if e.get('gentle')] or pool
    if not pool:
        return []
    r = kit.rng(cid, 'events', day)
    count = 1 if day <= 2 else 2 if day >= 7 else 1 + (r.random() < 0.25 + day * 0.08)
    # Yesterday's surprises are not repeated when there is anything else.
    y = kit.rng(cid, 'events', day - 1)
    ypool = pool_for(day - 1)
    yesterday = {e['id'] for e in (y.sample(ypool, min(len(ypool), 2)) if ypool else [])}
    fresh = [e for e in pool if e['id'] not in yesterday]
    if len(fresh) >= count:
        pool = fresh
    picks = r.sample(pool, min(count, len(pool)))
    slots = sorted(r.sample(range(1, 5), len(picks)))
    rows = []
    for e, at in zip(picks, slots):
        at = e['at'] if 'at' in e else (2 if day <= 1 else at)
        rows.append(dict(id=e['id'], at=at, status='waiting', choice=None, good=None, note=None))
    rows.sort(key=lambda x: x['at'])
    return rows


def new_plan(cid: str, day: int, mods: list[dict], events: list[dict]) -> dict:
    m = pick_mod(cid, day, mods)
    p = dict(day=day, mod=m['id'], events=roll_events(cid, day, events, m['id']), rules={}, flash=None,
             grade=None, streak_paid=False)
    for k in PLAN_COUNTERS:
        p[k] = 0
    return p


def plan(c: dict, cid: str, mods: list[dict], events: list[dict]) -> dict:
    """Today's plan, rolled once per day and stored."""
    d = kit.data(c)
    p = d.get('plan')
    if not isinstance(p, dict) or p.get('day') != c['day']:
        p = d['plan'] = new_plan(cid, c['day'], mods, events)
    return p


def mod_of(p: dict, mods: list[dict]) -> dict:
    return next((m for m in mods if m['id'] == p['mod']), mods[0])


def flash(p: dict, kind: str, text: str) -> None:
    p['flash_n'] += 1
    p['flash'] = dict(n=p['flash_n'], kind=kind, text=text[:220])


# ------------------------------------------------------------------ surprises
def open_event(p: dict) -> dict | None:
    return next((e for e in p['events'] if e['status'] == 'open'), None)


def trigger(s: dict, c: dict, p: dict, index: dict) -> dict | None:
    """Open the next waiting surprise once enough orders were served."""
    if not c['open'] or open_event(p):
        return None
    for e in p['events']:
        if e['status'] == 'waiting' and p['served'] >= e['at']:
            spec = index[e['id']]
            e['status'] = 'open'
            kit.log(s, c, 'event', spec['emoji'] + ' ' + spec['title'])
            flash(p, 'event', spec['emoji'] + ' ' + spec['title'])
            if spec.get('on_open'):
                spec['on_open'](s, c, p)
            return e
    return None


def choice_ok(s: dict, c: dict, p: dict, spec: dict, choice: dict) -> str | None:
    """Why a choice is not possible right now (None = possible)."""
    cost = choice.get('cost', 0)
    if cost and c['money'] < cost:
        return f'Cần {cost} xu.'
    check = choice.get('check')
    return check(s, c, p) if check else None


def resolve(s: dict, c: dict, p: dict, index: dict, payload: dict) -> dict:
    e = open_event(p)
    kit.need(e, 'Hiện không có chuyện nào cần quyết.')
    kit.need(payload.get('event') in (None, e['id']), 'Chuyện này đã được xử lý rồi.')
    spec = index[e['id']]
    cid = kit.one_of(payload.get('choice'), [x['id'] for x in spec['choices']], 'Chọn một cách xử lý nhé.')
    choice = next(x for x in spec['choices'] if x['id'] == cid)
    why = choice_ok(s, c, p, spec, choice)
    kit.need(why is None, why or '')
    text, good = spec['apply'](s, c, p, cid)
    e.update(status='done', choice=cid, good=good, note=text[:300])
    d = kit.data(c)
    d['ev_hist'] = (d.get('ev_hist', []) + [dict(day=c['day'], id=e['id'], choice=cid, good=good)])[-30:]
    kit.metric(c, 'events_handled')
    if good:
        kit.metric(c, 'events_good')
    flash(p, 'good' if good else 'bad' if good is False else 'info', text)
    kit.log(s, c, 'event', text)
    return dict(message=text, event=e['id'], good=good)


def public_plan(c: dict, p: dict, mods: list[dict], index: dict) -> dict:
    """What the player may see: waiting surprises stay secret."""
    m = mod_of(p, mods)
    rows = []
    for e in p['events']:
        if e['status'] in ('waiting', 'skipped'):
            continue
        spec = index[e['id']]
        row = dict(id=e['id'], status=e['status'], emoji=spec['emoji'], title=spec['title'], note=e['note'], good=e['good'], choice=e['choice'])
        if e['status'] == 'open':
            row['text'] = spec['text']
            row['choices'] = [dict(id=x['id'], label=x['label'], hint=x.get('hint', ''), cost=x.get('cost', 0),
                                   blocked=choice_ok(None, c, p, spec, x)) for x in spec['choices']]
        rows.append(row)
    out = {k: p[k] for k in ('day', 'served', 'perfect', 'refused', 'walkins', 'sales', 'missed', 'grade', 'flash')}
    out.update(mod=dict(id=m['id'], emoji=m['emoji'], label=m['label'], hint=m['hint']), events=rows,
               open_event=next((r for r in rows if r['status'] == 'open'), None))
    return out


# ------------------------------------------------------------------ guests
def patience_tick(c: dict, cid: str, active_id: str | None, extra: int = 0) -> None:
    """Personalities change how waiting feels. Runs after a physical action,
    before the engine's own -1 for everyone who is not being served."""
    if not c['open'] or c['life'].get('mode') == 'calm':
        return
    for t in open_tasks(c, cid):
        if t['id'] == active_id or t.get('deferred'):
            continue
        kind = (t.get('guest') or {}).get('kind')
        loss = extra + (2 if kind == 'rush' else 0) - (1 if kind in ('chatty', 'elder') else 0)
        if loss:
            t['patience'] = max(25, min(100, t.get('patience', 100) - loss))


def spawn_walkin(s: dict, c: dict, cid: str, chance: float, tag: str) -> dict | None:
    """A guest walks in on a busy day (same limits as `more_work`)."""
    if not c['open'] or len(open_tasks(c, cid)) >= 4:
        return None
    slots = [int(t['id'].split('-')[-1]) for t in c['tasks'] if t['day'] == c['day']]
    slot = max(slots, default=-1) + 1
    if slot >= 12 or kit.rng(cid, 'walkin', tag, c['day'], slot).random() >= chance:
        return None
    from .. import content
    from . import PLUGINS
    t = content.make_task(cid, c['day'], slot, c['turn'])
    c['tasks'].append(t)
    mod = PLUGINS[cid]
    if hasattr(mod, 'on_task'):
        mod.on_task(s, c, t)
    if not c.get('active_task'):
        c['active_task'] = t['id']
    return t


def after_serve(s: dict, c: dict, cid: str, p: dict, t: dict, walkin_chance: float = 0.0) -> list[str]:
    """Bookkeeping after kit.complete: counters, persona tips, streak bonus,
    walk-ins and the next surprise. Returns short lines for the result."""
    lines = []
    p['served'] += 1
    p['patience'] += int(t.get('patience', 100))
    if t['mistakes'] == 0 and not t.get('refused'):
        p['perfect'] += 1
    kind = (t.get('guest') or {}).get('kind')
    tip = 0
    if t['mistakes'] == 0 and kind == 'generous':
        tip = 4
    elif t['mistakes'] == 0 and kind == 'rush' and t.get('patience', 100) >= 80:
        tip = 3
    if tip:
        kit.money(s, c, tip, 'Khách thưởng thêm vì hài lòng', t['id'], category='tip')
        p['tips'] += tip
        lines.append(f'{PERSONAS[kind][0]} Khách thưởng thêm {tip} xu.')
    d = kit.data(c)
    if kind == 'regular':
        regs = d.setdefault('regulars', {})
        regs[t['npc']] = min(99, regs.get(t['npc'], 0) + 1)
    streak = c['life'].get('streak', 0)
    if streak >= STREAK_BONUS_AT and not p['streak_paid']:
        p['streak_paid'] = True
        kit.money(s, c, STREAK_BONUS, f'{STREAK_BONUS_AT} đơn liền không sai', f'streak-{c["day"]}', category='skill_reward')
        lines.append(f'🔥 {STREAK_BONUS_AT} đơn liền không sai · +{STREAK_BONUS} xu')
    if walkin_chance > 0:
        w = spawn_walkin(s, c, cid, walkin_chance, 'serve')
        if w:
            p['walkins'] += 1
            lines.append('🚶 Có khách mới ghé vào.')
    return lines


# ------------------------------------------------------------------ closing
def grade(p: dict, waste_value: int, extra: float = 0.0) -> dict | None:
    served = p['served']
    if not served:
        return None
    acc = p['perfect'] / served
    speed = min(1.0, max(0.0, (p['patience'] / served - 40) / 55))
    evs = [e for e in p['events'] if e['status'] in ('done', 'missed')]
    ev = (sum(1.0 if e['good'] else 0.5 if e['good'] is None and e['status'] == 'done' else 0.0 for e in evs) / len(evs)) if evs else 1.0
    waste = max(0.0, 1 - waste_value / 80)
    score = round(100 * (0.45 * acc + 0.25 * speed + 0.2 * ev + 0.1 * waste) - 5 * p['refused'] + extra)
    score = max(0, min(100, score))
    letter = next(g for g, low in GRADES if score >= low)
    return dict(letter=letter, score=score, acc=round(acc * 100), speed=round(speed * 100), events=round(ev * 100), waste=int(waste_value))


def close(s: dict, c: dict, cid: str, p: dict, mods: list[dict], extra: float = 0.0) -> dict:
    """End of day: unanswered surprises count against the day, then a grade."""
    for e in p['events']:
        if e['status'] == 'open':
            e.update(status='missed', good=False, note='Chưa kịp xử lý trước khi khép ca.')
        elif e['status'] == 'waiting':
            e['status'] = 'skipped'
    recap = c['life'].get('recap') or {}
    waste = recap.get('waste_value', 0) if recap.get('day') == c['day'] else 0
    g = grade(p, int(waste or 0), extra)
    p['grade'] = g
    d = kit.data(c)
    lines = []
    if g:
        d['grades'] = (d.get('grades', []) + [dict(day=c['day'], letter=g['letter'], score=g['score'])])[-14:]
        bonus = GRADE_BONUS.get(g['letter'], 0) if p['served'] >= 2 else 0
        if bonus:
            kit.money(s, c, bonus, f'Thưởng hạng {g["letter"]} cuối ngày', f'grade-{c["day"]}', category='skill_reward')
            lines.append(f'Hạng {g["letter"]}: thưởng thêm {bonus} xu.')
    today = mod_of(p, mods)
    tomorrow = pick_mod(cid, c['day'] + 1, mods)
    handled = [e for e in p['events'] if e['status'] in ('done', 'missed')]
    return dict(grade=g, served=p['served'], perfect=p['perfect'], walkins=p['walkins'], sales=p['sales'], missed=p['missed'],
                tips=p['tips'], today=dict(emoji=today['emoji'], label=today['label']),
                tomorrow=dict(emoji=tomorrow['emoji'], label=tomorrow['label'], hint=tomorrow['hint']),
                events=[dict(id=e['id'], good=e['good'], note=e['note']) for e in handled], lines=lines)


# ------------------------------------------------------------------ validation
def validate(c: dict, mods: list[dict], index: dict) -> None:
    d = kit.data(c)
    p = d.get('plan')
    if p is not None:
        kit.need(isinstance(p, dict), 'Kế hoạch ngày không hợp lệ.')
        kit.integer(p.get('day'), 1, 10**9)
        kit.need(p.get('mod') in {m['id'] for m in mods}, 'Vận may trong ngày không hợp lệ.')
        for k in PLAN_COUNTERS:
            kit.integer(p.get(k), 0, 10**9)
        kit.need(type(p.get('streak_paid')) is bool, 'Thưởng chuỗi không hợp lệ.')
        kit.need(isinstance(p.get('events'), list) and len(p['events']) <= 4, 'Danh sách bất ngờ không hợp lệ.')
        for e in p['events']:
            kit.need(isinstance(e, dict) and e.get('id') in index and e.get('status') in EVENT_STATUS, 'Chuyện bất ngờ không hợp lệ.')
            kit.integer(e.get('at'), 0, 12)
            kit.need(e.get('choice') is None or e['choice'] in [x['id'] for x in index[e['id']]['choices']], 'Lựa chọn bất ngờ không hợp lệ.')
            kit.need(e.get('good') in (None, True, False), 'Kết quả bất ngờ không hợp lệ.')
            kit.need(e.get('note') is None or (isinstance(e['note'], str) and len(e['note']) <= 300), 'Ghi chú bất ngờ không hợp lệ.')
        kit.need(sum(e['status'] == 'open' for e in p['events']) <= 1, 'Chỉ một chuyện mở cùng lúc.')
        kit.need(isinstance(p.get('rules'), dict) and len(p['rules']) <= 24, 'Luật trong ngày không hợp lệ.')
        for k, v in p['rules'].items():
            kit.need(isinstance(k, str) and len(k) <= 40, 'Luật trong ngày không hợp lệ.')
            kit.need(v is None or isinstance(v, (bool, int, str)) or (isinstance(v, (list, dict)) and len(v) <= 24), 'Luật trong ngày không hợp lệ.')
        kit.need(p.get('flash') is None or (isinstance(p['flash'], dict) and isinstance(p['flash'].get('text'), str)), 'Thông báo nhanh không hợp lệ.')
        kit.need(p.get('grade') is None or isinstance(p['grade'], dict), 'Hạng ngày không hợp lệ.')
    regs = d.get('regulars', {})
    kit.need(isinstance(regs, dict) and len(regs) <= 40, 'Sổ khách quen không hợp lệ.')
    for k, v in regs.items():
        kit.need(isinstance(k, str), 'Sổ khách quen không hợp lệ.')
        kit.integer(v, 0, 99)
    for key in ('grades', 'ev_hist'):
        kit.need(isinstance(d.get(key, []), list) and len(d.get(key, [])) <= 30, 'Lịch sử ngày không hợp lệ.')


def migrate(c: dict) -> dict:
    """Old saves: add the shared keys (idempotent)."""
    d = kit.data(c)
    d.setdefault('regulars', {})
    d.setdefault('grades', [])
    d.setdefault('ev_hist', [])
    return d
