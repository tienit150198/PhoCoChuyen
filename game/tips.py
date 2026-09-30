"""Tip hên xui: after a job, a customer sometimes leaves a tip, or a small thank-you gift.

Called once per finished task from experiences.after_task (inside engine.task_done, after
the review is posted). Every career can tip, with its own norm (tip_content.NORMS): often
at the salon or on a tour, now and then at a counter, rarely and only as a gift at the
pharmacy, the school or the office. The chance is luck, weighted by

* how good the job really was (the review's fair stars: 1–2★ never tips),
* how it went at the counter (a grumble rarely tips; any cut, refund, walkout or refusal never),
* the day (the street's festival, payday, a wedding season…),
* the customer: a seeded generosity trait per person (and closeness, when that module exists).

A tip is rolled once, seeded by the task id, and stored on the task (t['tip_roll']): a replay,
a reload or a second call never pays twice. Where the money goes:

* hired staff on shift: the tip goes to the team (life.staff_tips), not through the till;
* story mode, working as an employee (a hiring workplace): tips are personal, so the tip is
  booked as 'tip' in the workplace's cash book and moved straight to the player's wallet,
  the way the daily salary is (journey._transfer + journey._wallet);
* otherwise (your own shop, or outside the story): the till, money(..., category='tip').

Skipped: anything not 'completed', a task whose cash flow already paid a keep-the-change tip
(t['tip_given'] > 0) or a career tip before the hand-off, a safety slip, and the very first
job at a workplace (the guided tour / first dossier runs there).

State: t['tip_roll'] on the task, c['life']['tip_day'] (today's tips, shown by
public/js/v4/tips.js and folded into the day recap at close; optional in older saves).
"""
from __future__ import annotations

import hashlib
import math
import random

from . import tip_content as tc

VERSION = 1
KINDS = ('cash', 'gift', 'none', 'skip')
TO = ('till', 'wallet', 'team')
WHY = ('ok', 'roll', 'status', 'given', 'reaction', 'safety', 'stars', 'first')
DAY_KEEP = 24
MAX_CHANCE = .85
WALKIN_VOICE = dict(student='genz', office='busy', elder='elder', young='genz', app='plain')


def _eng():
    from . import engine
    return engine


def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16)


def norm(career: str) -> dict:
    return tc.NORMS.get(career, tc.DEFAULT_NORM)


def nice(x: float) -> int:
    """The nearest amount people actually hand over (ties go to the smaller one)."""
    if x <= 1:
        return 1
    return min(tc.NICE, key=lambda n: (abs(n - x), n))


# ---------------------------------------------------------------- the customer
def _npc(npc: str) -> dict:
    from .content import NPC_INDEX
    return NPC_INDEX.get(npc) or {}


def persona(career: str, npc: str) -> str:
    from .feedback import persona_for
    return persona_for(career, npc)


def _trait(career: str, who: str, npc: str) -> float:
    roll = _hash('tip-gen', who) % sum(w for _, w in tc.GENEROSITY)
    base = tc.GENEROSITY[-1][0]
    for factor, weight in tc.GENEROSITY:
        if roll < weight:
            base = factor
            break
        roll -= weight
    return base * tc.PERSONA_GENEROSITY.get(persona(career, npc), 1.0)


_MEAN: dict = {}


def _career_mean(career: str) -> float:
    """Average trait of a workplace's regulars: a career with a few lucky draws among its six
    regulars must not tip far above its norm, so each person is measured against their street."""
    if career not in _MEAN:
        from .content import NPCS
        rows = [_trait(career, n['id'], n['id']) for n in NPCS if n['career_id'] == career]
        _MEAN[career] = sum(rows) / len(rows) if rows else 1.0
    return _MEAN[career]


def generosity(career: str, who: str, npc: str) -> float:
    """A stable trait of each person: tight, ordinary, open-handed or very generous,
    nudged by their temper (a warm regular tips more than a sour one)."""
    return _trait(career, who, npc) / _career_mean(career)


def closeness(s: dict, npc: str) -> float:
    """Điểm thân quen (game/closeness.py, another module): close regulars tip more often
    and a little more. 1.0 while that module is missing or says nothing usable."""
    try:
        from . import closeness as cl
    except ImportError:
        return 1.0
    fn = getattr(cl, 'closeness_bonus', None)
    if not callable(fn):
        return 1.0
    try:
        v = float(fn(s, npc))
    except Exception:  # an optional bonus must never block finishing a job
        return 1.0
    return max(.5, min(3.0, v)) if math.isfinite(v) else 1.0


def _review(c: dict, t: dict) -> dict | None:
    return next((f for f in c['feed'] if f.get('source') == t['id'] and f.get('kind') == 'review'), None)


def fair_stars(c: dict, t: dict, post: dict | None) -> int:
    """How good the job really was: the review's fair stars (before a troll's twist)."""
    fb = (post or {}).get('feedback') or {}
    if type(fb.get('fair')) is int:
        return fb['fair']
    if post and type(post.get('stars')) is int:
        return post['stars']
    m = t.get('mistakes', 0)
    return 5 if m == 0 else 4 if m <= 2 else 3


def day_mod(c: dict, career: str) -> str | None:
    """Id of the career's luck of the day, where the career exposes one."""
    from .careers import PLUGINS
    day = c['day']
    try:
        if career == 'milk_tea':
            from . import boba
            return boba.modifier(c).get('id')
        if career == 'mother_baby':
            from . import giftshop
            return giftshop.modifier(c).get('id')
        mod = PLUGINS.get(career)
        if not mod:
            return None
        for name in ('today', 'mod_of'):
            fn = mod.__dict__.get(name)
            if callable(fn):
                return fn(day).get('id')
        fs = mod.__dict__.get('FS')
        if fs is not None and hasattr(fs, 'pick_mod') and isinstance(mod.__dict__.get('MODS'), list):
            return fs.pick_mod(career, day, mod.MODS).get('id')
    except Exception:  # a career refactor must never block finishing a job
        return None
    return None


def day_boost(c: dict, career: str) -> float:
    x = c.get('life') or {}
    boost = tc.FESTIVAL_MODE if x.get('mode') == 'festival' or x.get('festival') else 1.0
    boost *= tc.GENEROUS_DAYS.get(day_mod(c, career), 1.0)
    return min(1.6, boost)


def voice(s: dict, c: dict, t: dict, seed: int) -> dict:
    """Who speaks and how: dict(voice, who, self)."""
    career = t['career']
    walk = t.get('walkin') if isinstance(t.get('walkin'), dict) else None
    name = (walk or {}).get('name') or _npc(t['npc']).get('display_name') or 'Khách'
    post = _review(c, t)
    fb = (post or {}).get('feedback') or {}
    if post and not fb.get('stranger') and isinstance(post.get('author'), str) and post['author'].strip():
        name = post['author'].strip()   # the name the review shows (a guest, a parent…)
    first = name.split(' ')[0].lower()
    role = str(_npc(t['npc']).get('role') or '').lower()
    me = (walk or {}).get('me') or first
    if career == 'teacher':
        return dict(voice='parent', who=name, self='')
    if career == 'tour_guide' and seed % 5 < 2:
        who, country = tc.TOURISTS[seed // 5 % len(tc.TOURISTS)]
        return dict(voice='tourist', who=tc.TOURIST_WHO.format(name=who, country=country), self='')
    if first in tc.KID_WORDS:
        v = 'kid'
    elif walk and walk.get('kind') in WALKIN_VOICE:
        v = WALKIN_VOICE[walk['kind']]
    elif first in tc.ELDER_WORDS:
        v = 'elder'
    elif 'học sinh' in role or 'sinh viên' in role:
        v = 'genz'
    elif career in tc.OFFICE or 'văn phòng' in role or 'công ty' in role:
        v = 'busy'
    else:
        v = {'quiet': 'shy', 'warm': 'cheerful', 'parent_kind': 'cheerful', 'genz': 'genz'}.get(persona(career, t['npc']), 'plain')
    return dict(voice=v, who=name, self=me if me in tc.ELDER_WORDS else 'cô')


def _fill(line: str, s: dict, spoken: dict) -> str:
    g = (s.get('journey') or {}).get('gender')
    return line.format(self=spoken['self'] or 'cô', ac='anh' if g == 'male' else 'chị' if g == 'female' else 'anh chị',
                       gv='thầy' if g == 'male' else 'cô')


# ---------------------------------------------------------------- the bill
NOT_PAID = frozenset(('tip', 'promotion', 'skill_reward', 'story_reward', 'goal_reward', 'festival_reward',
                      'activity_reward', 'situation_reward', 'refund', 'recovery', 'grant', 'salary'))


def bill(c: dict, t: dict) -> int:
    """What this customer paid for the job (the task's own rows in the cash book)."""
    rows = c['ops']['finance']['ledger']
    return sum(r['amount'] for r in rows if r.get('ref') == t['id'] and r['amount'] > 0 and r.get('category') not in NOT_PAID)


def _tipped(c: dict, t: dict) -> bool:
    """A tip for this task already happened (keep-the-change at the till, a career's own tip)."""
    given = t.get('tip_given')
    if type(given) is int and given > 0:
        return True
    trip = t.get('trip')
    if isinstance(trip, dict) and type(trip.get('tips')) is int and trip['tips'] > 0:
        return True
    return any(r.get('ref') == t['id'] and r.get('category') == 'tip' and r['amount'] > 0 for r in c['ops']['finance']['ledger'])


# ---------------------------------------------------------------- deciding
def decide(s: dict, c: dict, t: dict) -> dict:
    """Pure: the same task in the same state always decides the same.
    Returns dict(kind, why, p, amount, big, gift, voice…) — nothing is paid here."""
    from . import consequences as cq
    out = dict(kind='skip', why='ok', p=0, amount=0, big=False)
    if t.get('status') != 'completed':
        return dict(out, why='status')
    if _tipped(c, t):
        return dict(out, why='given')
    react = (t.get('reaction') or {}).get('kind', 'accept')
    if react not in tc.REACTION:
        return dict(out, why='reaction')
    if cq.safety(t):
        return dict(out, why='safety')
    if c['metrics'].get('served', 0) <= 1:
        return dict(out, why='first')   # the guided first job at a place stays calm
    post = _review(c, t)
    stars = tc.STARS.get(fair_stars(c, t, post), 0)
    if not stars:
        return dict(out, why='stars')
    career = t['career']
    n = norm(career)
    walk = t.get('walkin') if isinstance(t.get('walkin'), dict) else None
    gen = generosity(career, (walk or {}).get('id') or t['npc'], t['npc'])
    close = closeness(s, t['npc'])
    fb = (post or {}).get('feedback') or {}
    from .feedback import HARSH
    mood = tc.HARSH_DAY if fb.get('persona') in HARSH else 1.0
    p = min(MAX_CHANCE, n['rate'] * stars * tc.REACTION[react] * gen * close * day_boost(c, career) * mood)
    seed = _hash('tip', (s.get('journey') or {}).get('seed', 0), t['id'])
    rng = random.Random(seed)
    out.update(p=round(p * 100))
    if rng.random() >= p:
        return dict(out, kind='none', why='roll')
    paid = bill(c, t)
    cash = rng.random() < n['cash'] and paid > 0
    big = cash and rng.random() < .02 * min(2.0, gen * close)
    spoken = voice(s, c, t, _hash('tip-voice', t['id']))
    v = spoken['voice']
    if cash:
        if big:
            floor = min(tc.BIG_LO, nice(2 * n['hi']))   # a 20 xu tip on a 3 xu glass of tea would be odd
            amount = min(tc.BIG_HI, max(floor, nice(paid * tc.BIG_SHARE)))
        else:
            pct = rng.uniform(.05, .15) * min(1.5, max(.75, (gen * close) ** .5))
            amount = min(n['hi'], max(n['lo'], nice(paid * pct)))
        pool = tc.BIG_LINES if big else tc.VOICE_LINES.get(v, tc.VOICE_LINES['plain'])
        # Adults sometimes praise the work itself; kids, tourists and parents keep their own voice.
        if not big and v not in ('kid', 'tourist', 'parent') and tc.CAREER_LINES.get(career) and rng.random() < .45:
            pool = tc.CAREER_LINES[career]
        line = _fill(pool[rng.randrange(len(pool))], s, spoken)
        return dict(out, kind='cash', amount=amount, big=big, line=line, who=spoken['who'], voice=v,
                    emoji='🌟' if big else '💝', gift='')
    emoji, gift = rng.choice(tc.GIFTS.get(career, tc.DEFAULT_GIFTS))
    pool = tc.GIFT_LINES.get(v, tc.GIFT_LINES['plain'])
    line = _fill(pool[rng.randrange(len(pool))], s, spoken)
    return dict(out, kind='gift', line=line, who=spoken['who'], voice=v, emoji=emoji, gift=gift)


# ---------------------------------------------------------------- paying
def _team(c: dict) -> bool:
    staff = (c.get('ops') or {}).get('staff') or []
    return any(e.get('status') == 'hired' and e.get('on_shift') and e.get('jobs', 0) > 0 for e in staff)


def _wallet_path(s: dict, c: dict, career: str) -> bool:
    """Story mode, working for someone else: the tip is the player's own money."""
    from . import employment as emp
    j = s.get('journey')
    return bool(isinstance(j, dict) and j.get('story') and emp.required(career)
                and (c.get('job') or {}).get('status') == 'hired')


def _pay(s: dict, c: dict, t: dict, amount: int, who: str) -> str:
    e = _eng()
    x = c['life']
    if _team(c):
        x['staff_tips'] += amount
        return 'team'
    e.money(s, c, amount, f'{tc.LEDGER} · {who}'[:120], t['id'], category='tip')
    if _wallet_path(s, c, t['career']):
        from . import journey as jr
        from .content import CAREER_META
        # Like the salary: booked as the workplace's income, then moved to your wallet at once.
        jr._transfer(s, c, -amount, tc.LEDGER_WALLET, 'owner_draw')
        kind = 'tip' if 'tip' in jr.HISTORY_KINDS else 'salary'
        place = CAREER_META.get(t['career'], {}).get('place', t['career'])
        jr._wallet(s['journey'], amount, kind, tc.WALLET_LABEL.format(place=place), t['career'])
        return 'wallet'
    x['tips'] += amount
    return 'till'


def _head(r: dict, to: str) -> str:
    if r['kind'] == 'gift':
        return f'{r["who"]} gửi {r["gift"]}'
    if to == 'team':
        return f'{r["who"]} gửi {r["amount"]} xu tip cho cả đội'
    return f'{r["who"]} để lại {"hẳn " if r["big"] else ""}{r["amount"]} xu tip'


def _review_line(post: dict | None, r: dict, seed: int) -> None:
    """A happy, ordinary review mentions the tip in the customer's words."""
    if not post or not isinstance(post.get('text'), str) or (post.get('stars') or 0) < 4:
        return
    fb = post.get('feedback') or {}
    if any(fb.get(k) for k in ('twist', 'unfair', 'gripe', 'stranger')):
        return
    if r['kind'] == 'gift':
        add = tc.REVIEW_GIFT.format(gift=r['gift'])
    else:
        pool = tc.REVIEW_BIG if r['big'] else tc.REVIEW_CASH
        add = pool[seed % len(pool)]
    text = post['text'].rstrip()
    if len(text) + len(add) < 2900:
        post['text'] = f'{text} {add}'
    post['tip'] = dict(kind=r['kind'], amount=r['amount'])


def after_task(s: dict, c: dict, t: dict) -> dict | None:
    """Roll, pay and record once. Returns today's tip row, or None when nobody tipped."""
    if isinstance(t.get('tip_roll'), dict):
        return None
    r = decide(s, c, t)
    t['tip_roll'] = dict(v=VERSION, kind=r['kind'], amount=r['amount'], to=None, big=r['big'], p=r['p'], why=r['why'])
    if r['kind'] not in ('cash', 'gift'):
        return None
    e = _eng()
    to = _pay(s, c, t, r['amount'], r['who']) if r['kind'] == 'cash' else None
    t['tip_roll']['to'] = to
    head = _head(r, to)
    where = tc.WHERE[to or 'gift']
    row = dict(id=t['id'], day=c['day'], kind=r['kind'], amount=r['amount'], to=to, big=r['big'],
               emoji=r['emoji'], who=r['who'][:80], head=head[:160], line=r['line'][:200], where=where, gift=r['gift'][:120])
    x = c['life']
    x['tip_day'] = (x.get('tip_day') or [])[-(DAY_KEEP - 1):] + [row]
    e.log(s, c, 'staff_tip' if to == 'team' else 'tip', f'{r["emoji"]} {head}: “{r["line"]}” {where}'[:500],
          t['npc'], t['id'])
    e.metric(c, 'tips_got' if r['kind'] == 'cash' else 'thanks_got')
    _review_line(_review(c, t), r, _hash('tip-review', t['id']))
    return row


# ---------------------------------------------------------------- day recap
def day_summary(x: dict) -> dict:
    """"Tip hôm nay" for the day recap (experiences.on_close), then the list starts over."""
    rows = [r for r in (x.get('tip_day') or []) if isinstance(r, dict)]
    cash = [r for r in rows if r['kind'] == 'cash']
    by = {k: sum(r['amount'] for r in cash if r['to'] == k) for k in TO}
    best = max(cash, key=lambda r: r['amount'], default=None) or next(iter(rows), None)
    return dict(count=len(rows), cash=by['till'] + by['wallet'], till=by['till'], wallet=by['wallet'], team=by['team'],
                tips=len(cash), gifts=len(rows) - len(cash),
                best=dict(emoji=best['emoji'], head=best['head'], line=best['line']) if best else None)


# ---------------------------------------------------------------- saves
def validate(c: dict) -> None:
    """Optional fields: life.tip_day (today's tips) and t['tip_roll'] on finished tasks."""
    e = _eng()
    need, integer, txt = e.need, e.integer, e.clean_text
    rows = (c.get('life') or {}).get('tip_day')
    if rows is not None:
        need(isinstance(rows, list) and len(rows) <= DAY_KEEP, 'Danh sách tip trong ngày sai.', 'invalid_save')
        for r in rows:
            need(isinstance(r, dict) and r.get('kind') in ('cash', 'gift') and r.get('to') in (None, *TO)
                 and type(r.get('big')) is bool, 'Dòng tip trong ngày sai.', 'invalid_save')
            need((r['kind'] == 'cash') == (r['to'] is not None), 'Dòng tip trong ngày sai.', 'invalid_save')
            txt(r.get('id'), 100)
            integer(r.get('day'), 1, 10 ** 7)
            integer(r.get('amount'), 0, 10 ** 4)
            for k, most, least in (('emoji', 16, 1), ('who', 80, 1), ('head', 160, 1), ('line', 200, 1), ('where', 120, 1), ('gift', 120, 0)):
                txt(r.get(k), most, least)
    for t in c.get('tasks') or []:
        roll = t.get('tip_roll') if isinstance(t, dict) else None
        if roll is None:
            continue
        need(isinstance(roll, dict) and roll.get('v') == VERSION and roll.get('kind') in KINDS and roll.get('why') in WHY
             and roll.get('to') in (None, *TO) and type(roll.get('big')) is bool, 'Kết quả tip của công việc sai.', 'invalid_save')
        integer(roll.get('amount'), 0, 10 ** 4)
        integer(roll.get('p'), 0, 100)
        need((roll['kind'] == 'cash') == (roll['to'] is not None) and (roll['amount'] > 0) == (roll['kind'] == 'cash'),
             'Kết quả tip của công việc sai.', 'invalid_save')
