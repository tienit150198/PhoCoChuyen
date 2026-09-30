"""Điểm thân quen: how close you are with each neighbour and customer (0–100, five tiers).

One score per person, reusing the scores that already exist:

* the journey cast (Bà Tám, Cô Ba…) → `s['journey']['life']['bonds'][id]` (game/life.py, starts at 50);
* customers of a workplace → `s['careers'][cid]['relationships'][npc]` (engine.remember adds 4 per
  job done for them). A few customers ARE cast members (ALIAS: Cô Ba at the tạp hóa…): their
  score is the cast bond.

This module adds what moves the score and what it changes:

* chatting (first chat of the day +1..+3, rude words −3), gifts (liked +6, neutral +3, disliked −2,
  one a day per person), thanking a gift (+2), a neighbour's invite (go +5, send wishes +1, ignore −3),
  work reviews (5★ +2 … 1★ −5, short-changed −3), help in chuyện đời thường (life.py moves the cast
  bond; it shows up in the history), and a very gentle decay after 14 days apart;
* close people give you things (food into the gift bag, an envelope now and then, paid once through
  engine.money with category 'gift'), check on you, bring food when your spirit is low and warn you
  about an inspection;
* helpers for other systems: closeness(), tier(), closeness_bonus() (tips), forgiveness()
  (softer reactions), wedding() (the marriage agent), known().

State: `s['journey']['closeness']` (initial() / migrate() / validate()). Commands (engine routes the
`qn_` prefix): qn_chat {who}, qn_gift {who, gift, src}, qn_thank {id}, qn_invite {id, choice},
qn_use {item}. Rolls are seeded from journey.seed and the day; each day is rolled once.
"""
from __future__ import annotations

import random

from . import archive as ar
from .closeness_content import (ADULT_POOL, CARE, CAST_TASTE, CHAT, CHAT_NPC, ENVELOPE, ENVELOPE_ARRIVE, GIFT_ARRIVE,
                                GIFT_LINES, GIFTS, INVITE_COST, INVITES, KID_NOT, KID_POOL, RECEIVED, STALL, TAGS,
                                THANK, TIERS, TIRED, UNTHANKED, WARN_INSPECT)

VERSION = 1
LOG_MAX = 60
INBOX_MAX = 10
BAG_MAX = 9                 # of one item
WARNED_MAX = 20
HISTORY = 5                 # rows shown on a profile
TALK = (1, 3)
RUDE = -3
THANK_GAIN = 2
UNTHANKED_LOSS = -1
THANK_DAYS = 2              # an unthanked gift turns a little sour after this many days
GIFT_GAIN = dict(liked=6, neutral=3, disliked=-2)
PRICEY = 10                 # a gift of this price or more: +1
STARS = {5: 2, 4: 0, 3: -1, 2: -3, 1: -5}
SHORT = -3
SHORT_CODES = ('change_short', 'change_home', 'short_change', 'overcharge')
INVITE_GO, INVITE_WISH, INVITE_MISS = 5, 1, -3
DECAY_AFTER, DECAY_EVERY = 14, 7
FLOOR_CAST, FLOOR_NPC = 40, 20
RECEIVE_P = {3: .015, 4: .035, 5: .06}
FESTIVAL_BONUS = .03
ENVELOPE_P = .15            # tier 5: share of their gifts that are an envelope
FESTIVAL_ENVELOPE_P = .3    # tier 4+ on a festival day
TIRED_SPIRIT, TIRED_P = 40, .35
CARE_P = .12
INVITE_P = .06
INVITE_GAP = 20             # the same person invites again at most this often
TIP_BONUS = {1: 1.0, 2: 1.05, 3: 1.15, 4: 1.35, 5: 1.6}   # multiplier on the tip chance (game/tips.py)
WEDDING = {1: (10, .5), 2: (30, .8), 3: (55, 1.0), 4: (80, 1.5), 5: (95, 2.2)}
KINDS = ('talk', 'gift', 'thank', 'work', 'life', 'invite', 'decay', 'rude', 'got')
INBOX_KINDS = ('gift', 'envelope', 'care', 'warn', 'invite')
INBOX_STATES = ('new', 'thanked', 'done', 'went', 'wished', 'missed')
SOURCES = ('buy', 'stall', 'bag')
REC_KEYS = {'seen', 'talk', 'gift', 'dec', 'rv', 'given', 'got'}
LOG_KEYS = {'day', 'who', 'd', 'text', 'k'}
INBOX_KEYS = {'id', 'day', 'kind', 'who', 'text', 'item', 'amount', 'state', 'until'}
# Customers who are really members of the journey cast (same name and role).
ALIAS = {'grocery_npc_01': 'co_ba', 'grocery_npc_04': 'be_ti', 'grocery_npc_05': 'ba_sau', 'grocery_npc_06': 'anh_khoa',
         'florist_npc_03': 'co_lua', 'repair_npc_06': 'ba_tam'}
KID_WORDS = ('học sinh', 'cô bé', 'cậu bé')


# ---------------------------------------------------------------- lookups
def _core():
    from . import engine
    return engine


# Looked up lazily (import cycles) but only once: these run a few hundred times per command.
_CAST: dict | None = None
_NPCS: dict | None = None


def _cast() -> dict:
    global _CAST
    if _CAST is None:
        from .journey import CAST
        _CAST = CAST
    return _CAST


def _npcs() -> dict:
    global _NPCS
    if _NPCS is None:
        from .content import NPC_INDEX
        _NPCS = NPC_INDEX
    return _NPCS


def home(npc_id) -> str | None:
    """The canonical id of a person (a cast alias maps to the cast id); None when unknown."""
    if not isinstance(npc_id, str):
        return None
    pid = ALIAS.get(npc_id, npc_id)
    return pid if pid in _cast() or pid in _npcs() else None


def is_cast(pid: str) -> bool:
    return pid in _cast()


def _clamp(v, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(v)))


def tier_of(score: int) -> int:
    # 1 + the last tier whose floor the score reaches (what max() over them gives)
    for i in range(len(TIERS) - 1, -1, -1):
        if score >= TIERS[i][0]:
            return i + 1
    raise ValueError('max() iterable argument is empty')


def tier_name(t: int) -> str:
    return TIERS[max(1, min(5, t)) - 1][1]


def closeness(s: dict, npc_id: str) -> int:
    """0..100 for anyone (a cast id like 'ba_tam' or a customer id like 'grocery_npc_03'); 0 when unknown."""
    pid = home(npc_id)
    if not pid:
        return 0
    if is_cast(pid):
        bonds = ((s.get('journey') or {}).get('life') or {}).get('bonds') or {}
        v = bonds.get(pid, 50)
    else:
        c = (s.get('careers') or {}).get(_npcs()[pid]['career_id']) or {}
        v = (c.get('relationships') or {}).get(pid, 0)
    return _clamp(v if type(v) is int else 0)


def tier(s: dict, npc_id: str) -> int:
    """1 Người lạ · 2 Quen mặt · 3 Người quen · 4 Thân thiết · 5 Như người nhà."""
    return tier_of(closeness(s, npc_id))


def closeness_bonus(s: dict, npc_id: str) -> float:
    """Multiplier on a customer's tip chance (game/tips.py): 1.0 · 1.05 · 1.15 · 1.35 · 1.6 by tier."""
    return TIP_BONUS[tier(s, npc_id)]


def forgiveness(s: dict, npc_id: str) -> int:
    """How many reaction levels a close regular lets slide (0, or 1 from Thân thiết)."""
    return 1 if tier(s, npc_id) >= 4 else 0


def forgives(c: dict, npc_id: str) -> int:
    """Same as forgiveness() from one workplace record only (for consequences.decide, which has no save):
    1 when this customer is Thân thiết or closer there, else 0."""
    v = (c.get('relationships') or {}).get(npc_id, 0) if isinstance(c, dict) else 0
    return 1 if type(v) is int and v >= TIERS[3][0] else 0


def wedding(s: dict, npc_id: str) -> dict:
    """For a wedding: attend = chance in percent, gift_mult = multiplier on the gift envelope."""
    attend, mult = WEDDING[tier(s, npc_id)]
    return dict(attend=attend, gift_mult=mult)


def known(s: dict, min_tier: int = 1) -> list[str]:
    """Everyone you know (the cast, customers you have met), closest first."""
    return _known(s, min_tier)[0]


def _known(s: dict, min_tier: int = 1) -> tuple[list[str], dict]:
    """known() and the score of each id it looked at."""
    ids = list(_cast())
    for cid, c in (s.get('careers') or {}).items():
        for npc, v in (c.get('relationships') or {}).items():
            if type(v) is int and v > 0 and npc not in ALIAS and npc in _npcs():
                ids.append(npc)
    st = ((s.get('journey') or {}).get('closeness') or {}).get('people') or {}
    seen = set(ids)
    ids += [p for p in st if p not in seen and p in _npcs()]
    score = {p: closeness(s, p) for p in ids}  # each score once (this runs on every command's view)
    out = [p for p in ids if tier_of(score[p]) >= min_tier]
    return sorted(out, key=lambda p: (-score[p], p)), score


def name_of(pid: str) -> str:
    if is_cast(pid):
        return _cast()[pid]['name']
    return _npcs()[pid]['display_name']


def is_kid(pid: str) -> bool:
    if pid == 'be_ti':
        return True
    n = _npcs().get(pid)
    return bool(n) and any(w in n.get('role', '').lower() for w in KID_WORDS)


_TASTE: dict = {}  # pid -> (likes, dislikes): fixed by the seed, so drawn once per process


def taste(pid: str) -> dict:
    """Seeded likes (two tags) and one dislike."""
    if pid in CAST_TASTE:
        return dict(likes=list(CAST_TASTE[pid]['likes']), dislikes=list(CAST_TASTE[pid]['dislikes']))
    got = _TASTE.get(pid)
    if got is None:
        pool = KID_POOL if is_kid(pid) else ADULT_POOL
        rng = random.Random('qn-taste|' + pid)
        likes = rng.sample(pool, 2)
        got = (tuple(likes), (rng.choice([t for t in pool if t not in likes]),))
        if len(_TASTE) < 5000:
            _TASTE[pid] = got
    return dict(likes=list(got[0]), dislikes=list(got[1]))


# ---------------------------------------------------------------- state
def _story(s: dict) -> bool:
    return bool((s.get('journey') or {}).get('story'))


def today(s: dict) -> int:
    """The life day in the story; outside it (tests, tools) every closed workday counts."""
    j = s.get('journey') or {}
    if j.get('story') and type(j.get('life_day')) is int:
        return j['life_day']
    cs = [c for c in (s.get('careers') or {}).values() if isinstance(c, dict) and type(c.get('day')) is int]
    return max(1, sum(c['day'] for c in cs) - len(cs) + 1)


def _bonds(s: dict) -> dict:
    return ((s.get('journey') or {}).get('life') or {}).get('bonds') or {}


def initial(s: dict | None = None) -> dict:
    s = s or {}
    return dict(version=VERSION, day=today(s) if s else 1, mark=int(s.get('seq', 0)) if s else 0, seq=0,
                people={}, log=[], inbox=[], bag={}, warned=[],
                snap={k: int(v) for k, v in _bonds(s).items() if type(v) is int})


def migrate(s: dict) -> dict:
    """Adds `s['journey']['closeness']` (setdefault only: no retro reviews, gifts or decay). After life.migrate."""
    j = s.get('journey')
    if not isinstance(j, dict):
        return s
    base = initial(s)
    st = j.setdefault('closeness', base)
    if isinstance(st, dict):
        for k, v in base.items():
            st.setdefault(k, v)
    return s


def _state(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('closeness'), dict):
        migrate(s)
    return j['closeness']


def _rec(st: dict, pid: str, day: int) -> dict:
    rec = st['people'].get(pid)
    if rec is None:
        rec = st['people'][pid] = dict(seen=day, talk=0, gift=0, dec=0, rv=[], given=0, got=0)
    return rec


def _log(st: dict, day: int, pid: str, delta: int, text: str, kind: str) -> None:
    st['log'] = ar.last(st['log'] + [dict(day=day, who=pid, d=int(delta), text=str(text)[:140], k=kind)], LOG_MAX, 'closeness.log', ar.JOURNEY)


def _set(s: dict, pid: str, value: int) -> None:
    value = _clamp(value)
    if is_cast(pid):
        life = (s.get('journey') or {}).get('life')
        if isinstance(life, dict) and isinstance(life.get('bonds'), dict):
            life['bonds'][pid] = value
            _state(s)['snap'][pid] = value
    else:
        c = s['careers'][_npcs()[pid]['career_id']]
        c.setdefault('relationships', {})[pid] = value


def change(s: dict, npc_id: str, delta: int, text: str, kind: str, touch: bool = True) -> int:
    """Move one person's score (clamped) and write the history row. Returns the actual change."""
    pid = home(npc_id)
    if not pid:
        return 0
    st = _state(s)
    day = today(s)
    rec = _rec(st, pid, day)
    if touch:
        rec['seen'] = day
        rec['dec'] = 0
    before = closeness(s, pid)
    _set(s, pid, before + int(delta))
    got = closeness(s, pid) - before
    if got or delta:
        _log(st, day, pid, got, text, kind)
    return got


def _gender(s: dict) -> str:
    g = (s.get('journey') or {}).get('gender')
    return g if g in ('male', 'female') else 'none'


def _fill(s: dict, text, **kw) -> str:
    from .life_content import TOKENS
    g = _gender(s)
    if isinstance(text, dict):
        text = text.get(g) or text['none']
    for k, v in TOKENS.items():
        text = text.replace('{' + k + '}', v[g])
    for k, v in kw.items():
        text = text.replace('{' + k + '}', str(v))
    return text


def _rng(s: dict, *parts) -> random.Random:
    return random.Random('|'.join(['qn', str((s.get('journey') or {}).get('seed', 0))] + [str(p) for p in parts]))


def _lc(name: str) -> str:
    """'Gói trà Thái Nguyên' → 'gói trà Thái Nguyên' (proper names keep their capitals)."""
    return name[:1].lower() + name[1:]


def _signed(n: int) -> str:
    return f'+{n}' if n > 0 else str(n)


def _note(pid: str, got: int) -> str:
    return f'{"💛" if got > 0 else "💔"} {name_of(pid)} {_signed(got)} thân quen.' if got else ''


# ---------------------------------------------------------------- actions that move the score
def _talk(s: dict, pid: str, rude: bool = False) -> int:
    st = _state(s)
    day = today(s)
    rec = _rec(st, pid, day)
    if rude:
        if rec['talk'] == -day:
            return 0
        rec['talk'] = -day            # one rude hit a day; no chat gain today either
        return change(s, pid, RUDE, 'Nói năng nặng lời khi trò chuyện.', 'rude')
    if rec['talk'] in (day, -day):
        rec['seen'] = day
        return 0
    rec['talk'] = day
    gain = _rng(s, 'talk', pid, day).randint(*TALK)
    return change(s, pid, gain, 'Trò chuyện hỏi thăm.', 'talk')


def _gift_item(career: str | None, gift: str, src: str) -> dict | None:
    if src == 'buy':
        return GIFTS.get(gift)
    if src == 'stall':
        x = STALL.get(career or '')
        return x if x and gift == 'stall' else None
    x = RECEIVED.get(gift)
    return dict(x, price=0) if x else None


def gift_effect(pid: str, item: dict) -> tuple[str, int]:
    """('liked'|'neutral'|'disliked'|'cash', change) for giving `item` to `pid`."""
    t = taste(pid)
    tags = set(item['tags'])
    if tags & set(t['dislikes']):
        return 'disliked', GIFT_GAIN['disliked']
    bonus = 1 if item.get('price', 0) >= PRICEY else 0
    if tags & set(t['likes']):
        return 'liked', GIFT_GAIN['liked'] + bonus
    if 'cash' in tags:
        return 'cash', GIFT_GAIN['neutral']
    return 'neutral', GIFT_GAIN['neutral'] + bonus


def _reveal(rec: dict, tags) -> None:
    for tg in tags:
        if tg in TAGS and tg not in rec['rv']:
            rec['rv'] = (rec['rv'] + [tg])[-6:]


# ---------------------------------------------------------------- after every career action
def after(s: dict, career: str | None, action: str, p: dict, result: dict) -> None:
    """Engine hook after a career action: chats, reviews, life changes, a new day."""
    j = s.get('journey')
    if not isinstance(j, dict) or not isinstance(s.get('careers'), dict):
        return
    st = _state(s)
    notes = []
    c = s['careers'].get(career) if career else None
    if action == 'talk' and isinstance(p, dict) and home(p.get('npc')):
        text = p.get('text') if isinstance(p.get('text'), str) else ''
        from . import ai
        pid = home(p['npc'])
        notes.append(_note(pid, _talk(s, pid, rude=bool(text) and ai.abusive(text))))
    if isinstance(c, dict):
        notes += _reviews(s, st, c)
    st['mark'] = max(st['mark'], int(s.get('seq', 0)))
    _life_changes(s, st)
    d = today(s)
    if d > st['day']:
        notes += _new_day(s, st, c if isinstance(c, dict) else None, career, d)
        st['day'] = d
    notes = [n for n in notes if n]
    if notes and isinstance(result, dict):
        result.setdefault('effects', [])
        result['effects'].extend(notes)


def _reviews(s: dict, st: dict, c: dict) -> list[str]:
    """Reviews posted since the last look: the stars (and short change) move the customer's score."""
    notes = []
    for post in (c.get('feed') or [])[:40]:
        try:
            seq = int(str(post.get('id', '')).split('-')[-1])
        except ValueError:
            continue
        if seq <= st['mark'] or post.get('kind') != 'review' or type(post.get('stars')) is not int:
            continue
        pid = home(post.get('npc'))
        if not pid:
            continue
        stars = max(1, min(5, post['stars']))
        delta = STARS[stars]
        t = next((x for x in c.get('tasks') or [] if x.get('id') == post.get('source')), None)
        short = bool(t) and any(r.get('code') in SHORT_CODES for r in (t.get('slips') or []) if isinstance(r, dict))
        text = f'Đánh giá {stars}★ sau khi được phục vụ.'
        if delta:
            got = change(s, pid, delta, text, 'work')
        else:
            got = 0
            _rec(st, pid, today(s)).update(seen=today(s), dec=0)
        if short:
            got += change(s, pid, SHORT, 'Bị thối thiếu tiền.', 'work')
        if got and stars in (5, 1) or short:
            notes.append(_note(pid, got))
    return notes


def _life_changes(s: dict, st: dict) -> None:
    """The cast bond moved in chuyện đời thường (help, gossip, a hard day): show it in the history."""
    bonds = _bonds(s)
    day = today(s)
    for pid, v in bonds.items():
        if type(v) is not int or pid not in _cast():
            continue
        old = st['snap'].get(pid)
        if old is not None and old != v:
            _log(st, day, pid, v - old, 'Chuyện đời thường trong hẻm.', 'life')
            _rec(st, pid, day).update(seen=day, dec=0)
        st['snap'][pid] = v


def _new_day(s: dict, st: dict, c: dict | None, career: str | None, d: int) -> list[str]:
    notes = []
    # 1. What was left waiting: an invite nobody answered, a gift nobody thanked.
    for row in st['inbox']:
        if row['state'] != 'new':
            continue
        if row['kind'] == 'invite' and row['until'] < d:
            row['state'] = 'missed'
            got = change(s, row['who'], INVITE_MISS, 'Không đến, cũng không nhắn gì khi được mời.', 'invite', touch=False)
            notes.append(_note(row['who'], got))
        elif row['kind'] in ('gift', 'envelope') and row['day'] + THANK_DAYS <= d:
            row['state'] = 'done'
            change(s, row['who'], UNTHANKED_LOSS, _fill(s, UNTHANKED, who=name_of(row['who'])), 'thank', touch=False)
    # 2. A very gentle decay after a long time apart.
    for pid, rec in st['people'].items():
        gap = d - rec['seen']
        if gap < DECAY_AFTER:
            continue
        steps = (gap - DECAY_AFTER) // DECAY_EVERY + 1
        new = steps - rec['dec']
        if new <= 0:
            continue
        rec['dec'] = steps
        floor = FLOOR_CAST if is_cast(pid) else FLOOR_NPC
        now = closeness(s, pid)
        if now > floor:
            change(s, pid, -min(new, now - floor), 'Lâu rồi chưa gặp nhau.', 'decay', touch=False)
    # 3. Today's roll (once per day): a warning, a gift or food, an invite, a word of care.
    rng = _rng(s, 'day', d)
    people = known(s, 3)
    close = [p for p in people if tier(s, p) >= 4]
    close_cast = [p for p in close if is_cast(p)]
    if c is not None and close:
        notes += _warn(s, st, c, career, close, d)
    gave = False
    spirit = int(((s.get('journey') or {}).get('life') or {}).get('spirit', 70))
    if _story(s) and spirit < TIRED_SPIRIT and close_cast and rng.random() < TIRED_P:
        who = close_cast[rng.randrange(len(close_cast))]
        item = rng.choice([k for k, x in RECEIVED.items() if 'food' in x['tags'] or 'sweet' in x['tags']])
        notes.append(_receive_item(s, st, who, item, _fill(s, rng.choice(TIRED), who=name_of(who), gift=_lc(RECEIVED[item]['name'])), d))
        gave = True
    festival = bool(c) and (c.get('life') or {}).get('mode') == 'festival'
    if not gave:
        for pid in people:
            tr = tier(s, pid)
            p = RECEIVE_P.get(tr, 0) + (FESTIVAL_BONUS if festival and tr >= 4 else 0)
            if rng.random() >= p:
                continue
            envelope = (tr == 5 and rng.random() < ENVELOPE_P) or (festival and tr >= 4 and rng.random() < FESTIVAL_ENVELOPE_P)
            if envelope and c is not None and not is_kid(pid):
                notes.append(_receive_envelope(s, st, c, pid, rng.randint(10, 20 if tr == 4 else 30), rng, d))
            else:
                pool = [k for k, x in RECEIVED.items() if x['tier'] <= tr]
                item = pool[rng.randrange(len(pool))]
                notes.append(_receive_item(s, st, pid, item, _fill(s, rng.choice(GIFT_ARRIVE), who=name_of(pid),
                                                                  gift=_lc(RECEIVED[item]['name'])), d))
            break
    if not any(r['kind'] == 'invite' and r['state'] == 'new' for r in st['inbox']) and rng.random() < INVITE_P:
        pool = [p for p in people if is_cast(p) and p in INVITES
                and not any(r['kind'] == 'invite' and r['who'] == p and r['day'] > d - INVITE_GAP for r in st['inbox'])]
        if pool:
            who = pool[rng.randrange(len(pool))]
            emoji, title, line = INVITES[who]
            _push(st, 'invite', who, f'{emoji} {title}: “{_fill(s, line)}”', d, until=d + 1)
            notes.append(f'{emoji} {name_of(who)} mời bạn: {title}.')
    if close and rng.random() < CARE_P:
        who = close[rng.randrange(len(close))]
        line = _fill(s, rng.choice(CARE))
        _push(st, 'care', who, f'{name_of(who)} nhắn: “{line}”', d, state='done')
        notes.append(f'💬 {name_of(who)}: “{line}”')
    return notes


def _push(st: dict, kind: str, who: str, text: str, day: int, item: str | None = None, amount: int = 0,
          state: str = 'new', until: int = 0) -> dict:
    st['seq'] += 1
    row = dict(id=f'qn-{st["seq"]}', day=day, kind=kind, who=who, text=text[:200], item=item, amount=int(amount),
               state=state, until=int(until or day))
    # Keep the newest; never drop an unanswered invite or unthanked gift before older finished rows.
    rows = st['inbox'] + [row]
    while len(rows) > INBOX_MAX:
        old = next((r for r in rows if r['state'] != 'new'), rows[0])
        rows.remove(old)
    st['inbox'] = rows
    return row


def _bag_add(st: dict, item: str) -> None:
    st['bag'][item] = min(BAG_MAX, st['bag'].get(item, 0) + 1)


def _receive_item(s: dict, st: dict, pid: str, item: str, text: str, d: int) -> str:
    _bag_add(st, item)
    rec = _rec(st, pid, d)
    rec['got'] += 1
    rec['seen'] = d
    _push(st, 'gift', pid, text, d, item=item)
    _log(st, d, pid, 0, f'Tặng bạn {_lc(RECEIVED[item]["name"])}.', 'got')
    return f'🎁 {text}'


def _receive_envelope(s: dict, st: dict, c: dict, pid: str, amount: int, rng: random.Random, d: int) -> str:
    """Paid here, once: the day is rolled once and the row id is the ledger ref."""
    text = _fill(s, rng.choice(ENVELOPE_ARRIVE), who=name_of(pid), amount=amount)
    row = _push(st, 'envelope', pid, text, d, amount=amount)
    _core().money(s, c, amount, f'{ENVELOPE["name"]} của {name_of(pid)}'[:120], row['id'], category='gift')
    rec = _rec(st, pid, d)
    rec['got'] += 1
    rec['seen'] = d
    _log(st, d, pid, 0, f'Lì xì bạn phong bì {amount} xu.', 'got')
    return f'🧧 {text}'


def _warn(s: dict, st: dict, c: dict, career: str | None, close: list, d: int) -> list[str]:
    box = c.get('incidents')
    if not isinstance(box, dict) or not isinstance(box.get('follow'), list):
        return []
    from .content import CAREER_META
    out = []
    for f in box['follow']:
        if not isinstance(f, dict) or 'inspect' not in str(f.get('script', '')) or f.get('day') not in (c.get('day'), c.get('day', 0) + 1):
            continue
        key = f'{career}:{f["script"]}:{f["day"]}'[:60]
        if key in st['warned']:
            continue
        st['warned'] = (st['warned'] + [key])[-WARNED_MAX:]
        who = close[0]
        text = _fill(s, WARN_INSPECT, who=name_of(who), place=CAREER_META.get(career, {}).get('place', 'chỗ làm'))
        _push(st, 'warn', who, text, d, state='done')
        out.append(f'⚠️ {text}')
    return out


# ---------------------------------------------------------------- commands
COMMANDS = ('qn_chat', 'qn_gift', 'qn_thank', 'qn_invite', 'qn_use')


def _fund(s: dict, career: str | None) -> tuple[str | None, dict | None]:
    from .content import CAREERS
    cid = career if career in CAREERS else s.get('current')
    c = s['careers'].get(cid) if cid else None
    return (cid, c) if isinstance(c, dict) else (None, None)


def apply(s: dict, career: str | None, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    st = _state(s)
    d = today(s)
    result = dict(message='', effects=[])
    if name in ('qn_chat', 'qn_gift'):
        pid = home(p.get('who'))
        need(pid, 'Không tìm thấy người này.')
        here = _fund(s, career)[0]
        need(is_cast(pid) or closeness(s, pid) > 0 or pid in st['people'] or _npcs()[pid]['career_id'] == here,
             'Bạn chưa quen người này. Gặp ở chỗ làm trước đã nhé.')
    if name == 'qn_chat':
        need(set(p) == {'who'}, 'Dữ liệu thao tác không hợp lệ.')
        rec = _rec(st, pid, d)
        first = rec['talk'] not in (d, -d)
        got = _talk(s, pid)
        band = 1 if tier(s, pid) >= 4 else 0
        rng = _rng(s, 'chat', pid, d, rec['given'] + rec['got'])
        if is_cast(pid):
            line = _fill(s, rng.choice(CHAT[pid][band]))
        else:
            line = _fill(s, rng.choice(CHAT_NPC[band]))
        result.update(message=f'{name_of(pid)}: “{line}”', line=line, who=pid, gain=got)
        if got:
            result['effects'].append(_note(pid, got))
        elif not first:
            result['effects'].append('Hôm nay hai bên trò chuyện rồi. Mai hỏi thăm tiếp nhé.')
    elif name == 'qn_gift':
        need(set(p) == {'who', 'gift', 'src'} and p['src'] in SOURCES and isinstance(p['gift'], str), 'Chọn một món quà nhé.')
        cid, c = _fund(s, career)
        item = _gift_item(cid, p['gift'], p['src'])
        need(item, 'Món quà này không có sẵn.')
        rec = _rec(st, pid, d)
        need(rec['gift'] != d, f'Hôm nay đã tặng {name_of(pid)} rồi. Mai hãy tặng tiếp nhé.', 'already_done')
        need(not (is_kid(pid) and set(item['tags']) & set(KID_NOT)), 'Món này không hợp để tặng trẻ nhỏ.')
        if p['src'] == 'bag':
            need(st['bag'].get(p['gift'], 0) > 0, 'Túi quà không còn món này.')
            st['bag'][p['gift']] -= 1
            if not st['bag'][p['gift']]:
                st['bag'].pop(p['gift'])
        else:
            need(c is not None and c.get('started'), 'Chọn một nơi làm việc đã mở để lấy tiền mua quà nhé.')
            need(c['money'] >= item['price'], f'Quỹ còn {c["money"]} xu, chưa đủ {item["price"]} xu mua quà.', 'not_enough')
            e.money(s, c, -item['price'], f'Quà cho {name_of(pid)}: {item["name"]}'[:120], f'qn-gift-{st["seq"] + 1}', category='gift_out')
            st['seq'] += 1
        how, delta = gift_effect(pid, item)
        rec['gift'] = d
        rec['given'] += 1
        if how in ('liked', 'disliked'):
            _reveal(rec, set(item['tags']) & set(taste(pid)['likes' if how == 'liked' else 'dislikes']))
        got = change(s, pid, delta, f'Nhận quà: {item["name"]}.', 'gift')
        line = _fill(s, _rng(s, 'giftline', pid, d).choice(GIFT_LINES[how]), who=name_of(pid), gift=_lc(item['name']))
        result.update(message=line, how=how, gain=got, who=pid)
        result['effects'].append(_note(pid, got))
    elif name == 'qn_thank':
        need(set(p) == {'id'}, 'Dữ liệu thao tác không hợp lệ.')
        row = next((r for r in st['inbox'] if r['id'] == p['id']), None)
        need(row and row['kind'] in ('gift', 'envelope'), 'Không tìm thấy món quà này.')
        need(row['state'] == 'new', 'Bạn đã cảm ơn rồi.', 'already_done')
        row['state'] = 'thanked'
        got = change(s, row['who'], THANK_GAIN, 'Được bạn cảm ơn món quà.', 'thank')
        result.update(message=_fill(s, THANK, who=name_of(row['who'])), gain=got)
        result['effects'].append(_note(row['who'], got))
    elif name == 'qn_invite':
        need(set(p) == {'id', 'choice'} and p['choice'] in ('go', 'wish'), 'Chọn đi dự hoặc gửi lời chúc nhé.')
        row = next((r for r in st['inbox'] if r['id'] == p['id']), None)
        need(row and row['kind'] == 'invite', 'Không tìm thấy lời mời này.')
        need(row['state'] == 'new', 'Lời mời này đã qua rồi.', 'already_done')
        who = name_of(row['who'])
        if p['choice'] == 'go':
            cid, c = _fund(s, career)
            need(c is not None and c.get('started'), 'Chọn một nơi làm việc đã mở để lấy tiền phong bì nhé.')
            need(c['money'] >= INVITE_COST, f'Cần {INVITE_COST} xu làm phong bì mừng.', 'not_enough')
            e.money(s, c, -INVITE_COST, f'Phong bì đi dự: {who}'[:120], row['id'], category='gift_out')
            row['state'] = 'went'
            got = change(s, row['who'], INVITE_GO, 'Bạn tới dự, có phong bì mừng.', 'invite')
            result['message'] = f'Bạn tới chung vui với {who}. Cả nhà mừng lắm.'
        else:
            row['state'] = 'wished'
            got = change(s, row['who'], INVITE_WISH, 'Bạn bận, nhắn lời chúc.', 'invite')
            result['message'] = f'Bạn nhắn lời chúc tới {who}. {who} cảm ơn.'
        result['gain'] = got
        result['effects'].append(_note(row['who'], got))
    elif name == 'qn_use':
        need(set(p) == {'item'} and p['item'] in RECEIVED, 'Món này không có trong túi quà.')
        need(st['bag'].get(p['item'], 0) > 0, 'Túi quà không còn món này.')
        st['bag'][p['item']] -= 1
        if not st['bag'][p['item']]:
            st['bag'].pop(p['item'])
        life = (s.get('journey') or {}).get('life')
        lift = 0
        if _story(s) and isinstance(life, dict) and type(life.get('spirit')) is int:
            lift = min(2, 100 - life['spirit'])
            life['spirit'] += lift
        x = RECEIVED[p['item']]
        result['message'] = f'Bạn thưởng thức {_lc(x["name"])}. Ấm lòng ghê.' + (f' Tinh thần +{lift}.' if lift else '')
    result['effects'] = [n for n in result['effects'] if n]
    return result


def action(s: dict, career: str | None, name: str, p: dict) -> tuple[dict, dict]:
    """Engine entry point (like life.action): apply, then validate everything."""
    e = _core()
    result = apply(s, career, name, p or {})
    validate(s)
    e.validate_state(s)
    return s, result


# ---------------------------------------------------------------- views
def _revealed(s: dict, pid: str, rec: dict | None, tr: int | None = None) -> dict:
    t = taste(pid)
    tr = tier(s, pid) if tr is None else tr
    rv = set((rec or {}).get('rv') or [])
    likes = [x for i, x in enumerate(t['likes']) if x in rv or tr >= 3 + i]
    dislikes = [x for x in t['dislikes'] if x in rv or tr >= 5]
    view = lambda tags: [dict(tag=x, emoji=TAGS[x][0], label=TAGS[x][1]) for x in tags]
    return dict(likes=view(likes), dislikes=view(dislikes), hidden=len(t['likes']) + len(t['dislikes']) - len(likes) - len(dislikes))


_BASES: dict = {}  # pid -> (who they are, is_kid): fixed content, built once per process


def _base(pid: str) -> tuple[dict, bool]:
    got = _BASES.get(pid)
    if got is None:
        from .content import CAREER_META
        if is_cast(pid):
            x = _cast()[pid]
            base = dict(id=pid, name=x['name'], emoji=x['emoji'], role=x['role'], cast=True, career=None, place='Hàng xóm')
        else:
            n = _npcs()[pid]
            base = dict(id=pid, name=n['display_name'], emoji='', role=n.get('role', ''), cast=False, career=n['career_id'],
                        place=CAREER_META.get(n['career_id'], {}).get('place', ''))
        got = (base, is_kid(pid))
        if len(_BASES) < 5000:
            _BASES[pid] = got
    return got


_AT: dict = {}  # career -> the customers who walk in there (content order, cast aliases left out)


def _walk_ins(cid: str) -> list[str]:
    got = _AT.get(cid)
    if got is None:
        got = _AT[cid] = [pid for pid, n in _npcs().items() if n['career_id'] == cid and pid not in ALIAS]
    return got


def _person(s: dict, st: dict, pid: str, d: int, log: list | None = None, score: int | None = None) -> dict:
    score = closeness(s, pid) if score is None else score
    tr = tier_of(score)
    rec = st['people'].get(pid)
    nxt = TIERS[tr][0] if tr < 5 else None
    base, kid = _base(pid)
    return dict(base, score=score, tier=tr, tier_name=tier_name(tr), tier_emoji=TIERS[tr - 1][2], floor=TIERS[tr - 1][0], next=nxt,
                kid=kid, talked=bool(rec) and rec['talk'] in (d, -d), gifted=bool(rec) and rec['gift'] == d,
                given=(rec or {}).get('given', 0), got=(rec or {}).get('got', 0), **_revealed(s, pid, rec, tr),
                history=[dict(day=r['day'], d=r['d'], text=r['text'], k=r['k'])
                         for r in (st['log'] if log is None else log) if r['who'] == pid][-HISTORY:][::-1])


def public(s: dict, career: str | None = None) -> dict:
    j = s.get('journey') or {}
    st = j.get('closeness') if isinstance(j.get('closeness'), dict) else initial(s)
    d = today(s)
    cid, c = _fund(s, career)
    ids, score = _known(s)
    # Everyone who walks into the place you are at now, even before you know them (the old “Bạn quen”).
    if cid:
        have = set(ids)
        ids += [pid for pid in _walk_ins(cid) if pid not in have]
    by_who: dict = {}
    for r in st['log']:
        by_who.setdefault(r['who'], []).append(r)
    people = [_person(s, st, pid, d, by_who.get(pid, ()), score.get(pid)) for pid in ids]
    stall = STALL.get(cid or '')
    gifts = [dict(id=k, src='buy', name=x['name'], emoji=x['emoji'], price=x['price'], tags=list(x['tags'])) for k, x in GIFTS.items()]
    if stall:
        gifts.insert(0, dict(id='stall', src='stall', name=stall['name'], emoji=stall['emoji'], price=stall['price'], tags=list(stall['tags'])))
    bag = [dict(id=k, src='bag', name=RECEIVED[k]['name'], emoji=RECEIVED[k]['emoji'], price=0, qty=q, tags=list(RECEIVED[k]['tags']))
           for k, q in st['bag'].items() if k in RECEIVED]
    inbox = [dict(r, who_name=name_of(r['who']) if home(r['who']) else '', item_view=dict(name=RECEIVED[r['item']]['name'], emoji=RECEIVED[r['item']]['emoji'])
                  if r['item'] in RECEIVED else None) for r in reversed(st['inbox'])]
    return dict(day=d, people=people, gifts=gifts, bag=bag, inbox=inbox, fund=c['money'] if c else 0, fund_ok=bool(c and c.get('started')),
                career=cid, alias=dict(ALIAS), pending=sum(1 for r in st['inbox'] if r['state'] == 'new'), invite_cost=INVITE_COST,
                tiers=[dict(tier=i + 1, low=row[0], name=row[1], emoji=row[2]) for i, row in enumerate(TIERS)])


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    j = s.get('journey')
    if not isinstance(j, dict) or 'closeness' not in j:
        return
    st = j['closeness']
    bad = 'Dữ liệu điểm thân quen không hợp lệ.'
    need(isinstance(st, dict) and set(st) == set(initial()), bad, 'invalid_save')
    need(st['version'] == VERSION, bad, 'invalid_save')
    integer(st['day'], 1, 10**7)
    integer(st['mark'], 0, 10**9)
    integer(st['seq'], 0, 10**9)
    need(isinstance(st['people'], dict) and len(st['people']) <= 400, bad, 'invalid_save')
    for pid, rec in st['people'].items():
        need(home(pid) == pid and isinstance(rec, dict) and set(rec) == REC_KEYS, bad, 'invalid_save')
        integer(rec['seen'], 0, 10**7)
        integer(rec['talk'], -10**7, 10**7)
        integer(rec['gift'], 0, 10**7)
        integer(rec['dec'], 0, 10**6)
        integer(rec['given'], 0, 10**6)
        integer(rec['got'], 0, 10**6)
        need(isinstance(rec['rv'], list) and len(rec['rv']) <= 6 and all(x in TAGS for x in rec['rv']), bad, 'invalid_save')
    need(isinstance(st['log'], list) and len(st['log']) <= LOG_MAX, bad, 'invalid_save')
    for r in st['log']:
        need(isinstance(r, dict) and set(r) == LOG_KEYS and home(r['who']) == r['who'] and r['k'] in KINDS, bad, 'invalid_save')
        integer(r['day'], 0, 10**7)
        integer(r['d'], -100, 100)
        txt(r['text'], 140)
    need(isinstance(st['inbox'], list) and len(st['inbox']) <= INBOX_MAX, bad, 'invalid_save')
    for r in st['inbox']:
        need(isinstance(r, dict) and set(r) == INBOX_KEYS and r['kind'] in INBOX_KINDS and r['state'] in INBOX_STATES, bad, 'invalid_save')
        need(home(r['who']) == r['who'] and (r['item'] is None or r['item'] in RECEIVED), bad, 'invalid_save')
        txt(r['id'], 24)
        txt(r['text'], 200)
        integer(r['day'], 0, 10**7)
        integer(r['until'], 0, 10**7)
        integer(r['amount'], 0, 10**6)
    need(isinstance(st['bag'], dict) and all(k in RECEIVED for k in st['bag']), bad, 'invalid_save')
    for v in st['bag'].values():
        integer(v, 1, BAG_MAX)
    need(isinstance(st['warned'], list) and len(st['warned']) <= WARNED_MAX and all(isinstance(x, str) and len(x) <= 60 for x in st['warned']),
         bad, 'invalid_save')
    need(isinstance(st['snap'], dict) and set(st['snap']) <= set(_cast()), bad, 'invalid_save')
    for v in st['snap'].values():
        integer(v, 0, 100)
