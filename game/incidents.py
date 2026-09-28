"""Chuyện đời: a cross-career incident layer (fines, police, tax, theft, scams, people).

Per workplace, stored in c['incidents'] (see initial()):

* plan — rolled once when the shift opens (seeded from the journey seed, the
  workplace and its day, never rerolled): whether an incident happens today,
  which one and after how many finished jobs. Rarer early, more often later,
  gentler on calm days, a bit more on festival days;
* follow — follow-ups a few days later (legal trouble chains);
* active — the incident waiting for a decision (one at a time, never while a
  career surprise, a street situation or a staff/security case is open);
* last / history — results; trust — how the street sees you (0–100); flags.

Money goes through engine.money() with a ledger category (fund) or the journey
wallet (kind 'incident'). Incidents only happen when the journey story is on
(real sessions); practice replays of past incidents change nothing. Hidden
things (which answer is right, luck, follow-ups, today's plan) never reach the
public projection before the decision.
"""
from __future__ import annotations

import copy
import hashlib
import random

from .incident_content import INCIDENTS, INDEX, CATS, EMPLOYEE

VERSION = 1
HISTORY = 80
FOLLOW_MAX = 12
TRUST_START = 50
DAILY_CAP = 2
TRUST_NAMES = ((80, 'Cả phố tin cậy'), (60, 'Được tin cậy'), (40, 'Bình thường'), (20, 'Bị dè chừng'), (0, 'Mang tiếng xấu'))


def initial() -> dict:
    return dict(v=VERSION, seq=0, trust=TRUST_START, plan=None, active=None, last=None, history=[], follow=[], flags={},
                count=dict(day=0, n=0))


def _eng():
    from . import engine
    return engine


def _rng(*parts) -> random.Random:
    return random.Random(int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16))


def _story(s: dict) -> bool:
    return bool(s.get('journey', {}).get('story'))


def _gender(s: dict) -> str:
    g = s.get('journey', {}).get('gender')
    return g if g in ('male', 'female') else 'none'


def _txt(value, gender: str) -> str:
    if isinstance(value, dict):
        return value.get(gender) or value['none']
    return value


def _camera(c: dict) -> bool:
    return 'camera' in c.get('ops', {}).get('security', {}).get('items', [])


def _npc(career: str, x: dict) -> str:
    return f'{career}_npc_{x.get("npc", 0) + 1:02d}'


def trust_name(t: int) -> str:
    return next(name for low, name in TRUST_NAMES if t >= low)


# ---------------------------------------------------------------- migration
def migrate(s: dict) -> None:
    """Older saves gain an empty incident book (setdefault only, no retro events)."""
    for c in (s.get('careers') or {}).values():
        if not isinstance(c, dict):
            continue
        box = c.setdefault('incidents', initial())
        if isinstance(box, dict):
            for k, v in initial().items():
                box.setdefault(k, copy.deepcopy(v))


# ---------------------------------------------------------------- when things happen
def rate(day: int, mode: str = 'normal') -> float:
    """Chance that a workplace day has an incident: none in the first days, then more."""
    if day <= 2:
        return 0.0
    p = 0.3 if day <= 5 else 0.45 if day <= 9 else 0.55
    if mode == 'calm':
        p *= 0.5
    elif mode == 'festival':
        p += 0.15
    return min(0.8, p)


def _pool(c: dict, career: str, box: dict) -> list:
    mode = c['life'].get('mode', 'normal')
    rows = [x for x in INCIDENTS if not x['chain'] and career in x['careers'] and x['min_day'] <= c['day']]
    if mode == 'calm':
        rows = [x for x in rows if x['tone'] == 'mild']
    recent = {h['script'] for h in box['history'][-12:]}
    return [x for x in rows if x['id'] not in recent] or rows


def _weight(x: dict, career: str, box: dict) -> float:
    w = x['weight'] * x.get('weights', {}).get(career, 1)
    if len(x['careers']) <= 7:
        w *= 2   # the workplace's own stories come up more often than the street's shared ones
    if x['cat'] == 'phat' and box['trust'] < 35:
        w *= 2   # a place with a bad name gets checked more
    return w


def roll_plan(s: dict, c: dict, career: str) -> dict | None:
    """Today's plan for this workplace. Pure function of (seed, career, day, history)."""
    box = c['incidents']
    day = c['day']
    seed = s.get('journey', {}).get('seed', 0)
    r = _rng('incident-plan', seed, career, day)
    p = rate(day, c['life'].get('mode', 'normal'))
    if any(h['day'] == day - 1 and not h.get('follow') for h in box['history']):
        p *= 0.6
    if r.random() >= p:
        return None
    pool = _pool(c, career, box)
    if not pool:
        return None
    weights = [_weight(x, career, box) for x in pool]
    pick = r.random() * sum(weights)
    x = pool[-1]
    for row, w in zip(pool, weights):
        pick -= w
        if pick < 0:
            x = row
            break
    return dict(day=day, at=1 + r.randrange(2), script=x['id'], fired=False)


def _busy(c: dict) -> bool:
    """Another decision is already on screen: a surprise, a situation, a case."""
    if (c.get('happen') or {}).get('live'):
        return True   # a live happening in the scene (game/happenings.py)
    e = c.get('event')
    if e and e.get('stage') != 'resolved' and not e.get('practice'):
        return True
    ext = c.get('ext') or {}
    sit = ext.get('situation')
    if sit and sit.get('stage') != 'resolved' and not sit.get('practice'):
        return True
    o = c.get('ops') or {}
    if o.get('incident') and o['incident'].get('status') != 'resolved' and not o['incident'].get('practice'):
        return True
    sec = o.get('security') or {}
    active = next((x for x in sec.get('cases', []) if x.get('id') == sec.get('active')), None)
    if active and active.get('status') != 'closed' and not active.get('practice'):
        return True
    return _open_surprise(ext.get('data'), 0)


def _open_surprise(node, depth: int) -> bool:
    if depth > 3 or not isinstance(node, dict):
        return False
    ev = node.get('ev')
    if isinstance(ev, dict) and ev.get('script'):
        return True   # kit desk surprise
    ev = node.get('event')
    if isinstance(ev, dict) and ev.get('id') and ev.get('stage', ev.get('status', 'open')) == 'open':
        return True   # boba / gift counter surprise
    evs = node.get('events')
    if isinstance(evs, list) and any(isinstance(e, dict) and e.get('status') == 'open' for e in evs):
        return True   # food_service plan
    return any(_open_surprise(v, depth + 1) for v in node.values() if isinstance(v, dict))


def _fire(s: dict, c: dict, career: str, sid: str, follow: bool = False, practice: bool = False) -> dict:
    box = c['incidents']
    x = INDEX[sid]
    box['seq'] += 1
    row = dict(id=f'inc-{box["seq"]}', script=sid, day=c['day'], practice=practice, follow=follow)
    box['active'] = row
    if not practice:
        if box['count']['day'] != c['day']:
            box['count'] = dict(day=c['day'], n=0)
        box['count']['n'] += 1
        _eng().log(s, c, 'incident', f'{x["emoji"]} {x["title"]}', _npc(career, x), row['id'])
    return row


def after(s: dict, c: dict, career: str, action: str, result: dict) -> None:
    """Engine hook after every successful action (before validation)."""
    box = c.get('incidents')
    if not isinstance(box, dict):
        return
    if action == 'start_day' and c['open']:
        box['plan'] = roll_plan(s, c, career) if _story(s) else None
    if not c['open'] or not _story(s) or action.startswith('inc_') or action == 'end_day':
        return
    if box['active'] and not box['active']['practice']:
        return
    if c['day_completed'] < 1 or _busy(c):
        return
    n = box['count']['n'] if box['count']['day'] == c['day'] else 0
    cap = 1 if c['life'].get('mode') == 'calm' else DAILY_CAP
    if n >= cap:
        return
    due = next((f for f in box['follow'] if f['day'] <= c['day']), None)
    plan = box['plan']
    if due:
        box['follow'].remove(due)
        sid, follow = due['script'], True
    elif plan and plan['day'] == c['day'] and not plan['fired'] and c['day_completed'] >= plan['at']:
        plan['fired'] = True
        sid, follow = plan['script'], False
    else:
        return
    if box['active']:        # a practice replay steps aside for the real thing
        box['active'] = None
    row = _fire(s, c, career, sid, follow)
    x = INDEX[sid]
    result['incident'] = row['id']
    result.setdefault('effects', []).append(f'{x["emoji"]} {x["title"]}')


# ---------------------------------------------------------------- deciding
def _lines(opt: dict, res: dict | None) -> list:
    return list(opt.get('pay', [])) + (list(res.get('pay', [])) if res else [])


def _pay(s: dict, c: dict, career: str, lines: list, title: str, ref: str) -> list:
    """Apply money lines. Fund costs never overdraw: what the fund lacks comes
    from the wallet (story on) — a fine does not vanish because the till is empty."""
    e = _eng()
    j = s.get('journey') or {}
    story = _story(s)
    from . import journey as jr
    done = []
    for where, amount, cat in lines:
        if not amount:
            continue
        if where == 'wallet' and story:
            jr._wallet(j, amount, 'incident', title, career)
            done.append(dict(where='wallet', amount=amount, cat=cat))
            continue
        if amount > 0:
            e.money(s, c, amount, title, ref, cat)
            done.append(dict(where='fund', amount=amount, cat=cat))
            continue
        take = min(-amount, c['money'])
        if take:
            e.money(s, c, -take, title, ref, cat)
            done.append(dict(where='fund', amount=-take, cat=cat))
        rest = -amount - take
        if rest and story:
            jr._wallet(j, -rest, 'incident', title, career)
            done.append(dict(where='wallet', amount=-rest, cat=cat))
    return done


def _need(s: dict, c: dict, opt: dict) -> tuple[int, int]:
    fund = -sum(a for w, a, _ in opt.get('pay', []) if a < 0 and (w == 'fund' or not _story(s)))
    wallet = -sum(a for w, a, _ in opt.get('pay', []) if a < 0 and w == 'wallet' and _story(s))
    return fund, wallet


def _affordable(s: dict, c: dict, opt: dict) -> bool:
    if not opt.get('voluntary'):
        return True
    fund, wallet = _need(s, c, opt)
    return c['money'] >= fund and (not wallet or s['journey']['wallet'] >= wallet)


def _luck(c: dict, row: dict, opt: dict) -> bool | None:
    luck = opt.get('luck')
    if not luck:
        return None
    p = luck['p_camera'] if luck.get('p_camera') is not None and _camera(c) else luck['p']
    return _rng('incident-luck', row['id'], row['script'], opt['id']).random() < p


def _schedule(box: dict, follow, day: int, src: str) -> None:
    if not follow:
        return
    sid, days = follow
    if sid in INDEX and len(box['follow']) < FOLLOW_MAX and not any(f['script'] == sid for f in box['follow']):
        box['follow'].append(dict(script=sid, day=day + max(1, int(days)), src=src))


def decide(s: dict, c: dict, career: str, option: str, auto: bool = False) -> dict:
    e = _eng()
    box = c['incidents']
    row = box['active']
    e.need(row, 'Không có chuyện nào đang chờ bạn quyết.')
    x = INDEX[row['script']]
    opt = next((o for o in x['options'] if o['id'] == option), None)
    e.need(opt, 'Lựa chọn không có trong chuyện này.')
    practice = row['practice']
    if not auto and not practice:
        e.need(_affordable(s, c, opt), 'Chưa đủ tiền cho lựa chọn này. Chọn cách khác nhé.', 'not_enough')
    won = _luck(c, row, opt)
    res = (opt['luck']['win'] if won else opt['luck']['lose']) if won is not None else None
    outcome = _txt(res['outcome'] if res and res.get('outcome') else opt['outcome'], _gender(s))
    good = res['good'] if res else opt['good']
    trust = opt.get('trust', 0) + (res.get('trust', 0) if res else 0)
    done = []
    if not practice:
        done = _pay(s, c, career, _lines(opt, res), x['title'], row['id'])
        box['trust'] = max(0, min(100, box['trust'] + trust))
        for src in (opt, res or {}):
            if src.get('flag'):
                box['flags'][src['flag']] = c['day']
            if src.get('unflag'):
                box['flags'].pop(src['unflag'], None)
            _schedule(box, src.get('follow'), c['day'], row['id'])
        review = (res or {}).get('review') or opt.get('review')
        npc = _npc(career, x)
        if review and npc in e.NPC_INDEX:
            post = e.add_feed(s, c, npc, review[1], row['id'], review[0], 'review')
            post['incident'] = x['id']
        e.metric(c, 'incidents')
        if good is True:
            e.metric(c, 'incidents_good')
            c['xp'] += 8
        e.log(s, c, 'incident', f'{x["title"]}: {outcome}', npc, row['id'])
        box['history'] = (box['history'] + [dict(id=row['id'], script=x['id'], choice=opt['id'], day=row['day'], good=good,
                                                 won=won, auto=auto, follow=row.get('follow', False),
                                                 fund=sum(d['amount'] for d in done if d['where'] == 'fund'),
                                                 wallet=sum(d['amount'] for d in done if d['where'] == 'wallet'),
                                                 trust=trust)])[-HISTORY:]
    box['last'] = dict(id=row['id'], script=x['id'], choice=opt['id'], day=row['day'], good=good, won=won, auto=auto,
                       practice=practice, lines=done, trust=trust)
    box['active'] = None
    return dict(message=outcome, celebrate=good is True and not practice)


def action(s: dict, c: dict, career: str, name: str, p: dict) -> dict:
    e = _eng()
    box = c['incidents']
    if name == 'inc_choose':
        row = box['active']
        e.need(row, 'Chuyện này đã được quyết rồi.', 'already_decided')
        e.need(p.get('id') in (None, row['id']), 'Chuyện này đã được quyết rồi.', 'already_decided')
        e.need(isinstance(p.get('option'), str), 'Chọn một cách xử lý nhé.')
        return decide(s, c, career, p['option'])
    if name == 'inc_practice':
        sid = p.get('script')
        e.need(isinstance(sid, str) and any(h['script'] == sid for h in box['history']),
               'Chỉ xem lại được những chuyện đã từng gặp ở đây.')
        e.need(not box['active'] or box['active']['practice'], 'Đang có một chuyện thật chờ bạn quyết.')
        _fire(s, c, career, sid, practice=True)
        return dict(message='Nhớ lại chuyện cũ: thử một cách khác, không ảnh hưởng tiền hay tiếng.')
    if name == 'inc_close':
        row = box['active']
        e.need(row and row['practice'], 'Chuyện thật cần được quyết, không cất đi được.')
        box['active'] = None
        return dict(message='Đã cất chuyện cũ lại.')
    raise e.GameError('Thao tác không hợp lệ.')


def on_close(s: dict, c: dict, career: str) -> dict | None:
    """Closing time: an undecided incident takes its default; today's list for the summary."""
    box = c.get('incidents')
    if not isinstance(box, dict):
        return None
    row = box['active']
    if row and row['practice']:
        box['active'] = None
    elif row:
        decide(s, c, career, INDEX[row['script']]['default'], auto=True)
    box['plan'] = None
    today = [h for h in box['history'] if h['day'] == c['day']]
    if not today:
        return None
    return dict(items=[_history_view(h, _gender(s)) for h in today], trust=box['trust'], trust_name=trust_name(box['trust']))


# ---------------------------------------------------------------- public view
def _history_view(h: dict, gender: str) -> dict:
    x = INDEX[h['script']]
    opt = next(o for o in x['options'] if o['id'] == h['choice'])
    res = None
    if h.get('won') is not None and opt.get('luck'):
        res = opt['luck']['win'] if h['won'] else opt['luck']['lose']
    return dict(id=h['id'], script=x['id'], emoji=x['emoji'], title=x['title'], cat=x['cat'], cat_label=CATS[x['cat']][1],
                label=_txt(opt['label'], gender), outcome=_txt(res['outcome'] if res and res.get('outcome') else opt['outcome'], gender),
                good=h['good'], auto=h.get('auto', False), day=h['day'], fund=h.get('fund', 0), wallet=h.get('wallet', 0),
                trust=h.get('trust', 0))


def _evidence(x: dict, c: dict, gender: str) -> list:
    cam = _camera(c)
    out = []
    for ev in x['evidence']:
        if isinstance(ev, dict):
            if ev.get('when') == 'camera' and not cam or ev.get('when') == 'no_camera' and cam:
                continue
            out.append(_txt(ev['text'], gender))
        else:
            out.append(_txt(ev, gender))
    return out


def _stakes(s: dict, opt: dict) -> list:
    story = _story(s)
    return [dict(where=w if story else 'fund', amount=a, cat=cat) for w, a, cat in opt.get('pay', []) if a]


def public(c: dict, career: str, s: dict) -> dict:
    box = c.get('incidents') or initial()
    gender = _gender(s)
    view = dict(trust=box['trust'], trust_name=trust_name(box['trust']), active=None, last=None,
                log=[_history_view(h, gender) for h in reversed(box['history'][-12:])],
                replay=list(dict.fromkeys(h['script'] for h in reversed(box['history'])))[:8],
                employee=career in EMPLOYEE)
    row = box['active']
    if row:
        x = INDEX[row['script']]
        emoji, label = CATS[x['cat']]
        view['active'] = dict(
            id=row['id'], script=x['id'], day=row['day'], practice=row['practice'], cat=x['cat'], cat_emoji=emoji,
            cat_label=label, emoji=x['emoji'], title=x['title'], text=_txt(x['text'], gender), tone=x['tone'],
            evidence=_evidence(x, c, gender), ticket=copy.deepcopy(x['ticket']),
            options=[dict(id=o['id'], label=_txt(o['label'], gender), hint=o.get('hint', ''), stakes=_stakes(s, o),
                          affordable=row['practice'] or _affordable(s, c, o)) for o in x['options']])
    last = box['last']
    if last:
        x = INDEX[last['script']]
        opt = next(o for o in x['options'] if o['id'] == last['choice'])
        res = None
        if last.get('won') is not None and opt.get('luck'):
            res = opt['luck']['win'] if last['won'] else opt['luck']['lose']
        view['last'] = dict(id=last['id'], script=x['id'], emoji=x['emoji'], title=x['title'], cat=x['cat'],
                            cat_label=CATS[x['cat']][1], label=_txt(opt['label'], gender),
                            outcome=_txt(res['outcome'] if res and res.get('outcome') else opt['outcome'], gender), good=last['good'],
                            practice=last['practice'], auto=last['auto'], day=last['day'], lines=copy.deepcopy(last['lines']),
                            trust=last['trust'])
    return view


def catalogue() -> list[dict]:
    return [dict(id=x['id'], cat=x['cat'], title=x['title'], careers=list(x['careers']), chain=x['chain']) for x in INCIDENTS]


# ---------------------------------------------------------------- validation
def validate(c: dict, career: str) -> None:
    e = _eng()
    need, integer, txt = e.need, e.integer, e.clean_text
    box = c.get('incidents')
    need(isinstance(box, dict) and set(initial()) <= set(box), 'Sổ chuyện đời thiếu dữ liệu.', 'invalid_save')
    need(box['v'] == VERSION, 'Phiên bản sổ chuyện đời không hợp lệ.', 'invalid_save')
    integer(box['seq'], 0, 10**9)
    integer(box['trust'], 0, 100)
    need(isinstance(box['count'], dict), 'Bộ đếm chuyện đời sai.')
    integer(box['count'].get('day'), 0, 10**7)
    integer(box['count'].get('n'), 0, 50)
    plan = box['plan']
    if plan is not None:
        need(isinstance(plan, dict) and plan.get('script') in INDEX and not INDEX[plan['script']]['chain'], 'Kế hoạch chuyện đời sai.')
        integer(plan.get('day'), 1, 10**7)
        integer(plan.get('at'), 1, 3)
        need(type(plan.get('fired')) is bool, 'Kế hoạch chuyện đời sai.')
    row = box['active']
    if row is not None:
        need(isinstance(row, dict) and row.get('script') in INDEX, 'Chuyện đời đang mở sai.')
        txt(row.get('id'), 40)
        integer(row.get('day'), 1, 10**7)
        need(type(row.get('practice')) is bool and type(row.get('follow')) is bool, 'Chuyện đời đang mở sai.')
    last = box['last']
    if last is not None:
        need(isinstance(last, dict) and last.get('script') in INDEX, 'Kết quả chuyện đời sai.')
        need(last.get('choice') in [o['id'] for o in INDEX[last['script']]['options']], 'Kết quả chuyện đời sai.')
        need(last.get('good') in (True, False, None) and last.get('won') in (True, False, None), 'Kết quả chuyện đời sai.')
        need(isinstance(last.get('lines'), list) and len(last['lines']) <= 8, 'Kết quả chuyện đời sai.')
        for ln in last['lines']:
            need(isinstance(ln, dict) and ln.get('where') in ('fund', 'wallet'), 'Kết quả chuyện đời sai.')
            integer(ln.get('amount'), -10**6, 10**6)
            txt(ln.get('cat'), 40)
        integer(last.get('trust'), -100, 100)
    need(isinstance(box['history'], list) and len(box['history']) <= HISTORY, 'Lịch sử chuyện đời sai.')
    for h in box['history']:
        need(isinstance(h, dict) and h.get('script') in INDEX, 'Lịch sử chuyện đời sai.')
        need(h.get('choice') in [o['id'] for o in INDEX[h['script']]['options']], 'Lịch sử chuyện đời sai.')
        need(h.get('good') in (True, False, None) and h.get('won') in (True, False, None), 'Lịch sử chuyện đời sai.')
        integer(h.get('day'), 1, 10**7)
        for k in ('fund', 'wallet'):
            integer(h.get(k), -10**6, 10**6)
        integer(h.get('trust'), -100, 100)
    need(isinstance(box['follow'], list) and len(box['follow']) <= FOLLOW_MAX, 'Chuyện chờ về sau sai.')
    for f in box['follow']:
        need(isinstance(f, dict) and f.get('script') in INDEX, 'Chuyện chờ về sau sai.')
        integer(f.get('day'), 1, 10**7)
        txt(f.get('src'), 40)
    need(isinstance(box['flags'], dict) and len(box['flags']) <= 60, 'Dấu chuyện đời sai.')
    for k, v in box['flags'].items():
        txt(k, 40)
        integer(v, 0, 10**7)
