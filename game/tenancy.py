"""🏠 Chuyện nhà thuê (feedback #261): small moments of renting, on the life layer's card (game/life.py).

* Who gets them (story mode, from FIRST_DAY): a player who rents (Bà Tám's attic, the Phòng trọ khép kín, a home
  leased from another player: rentals.py, then only the cards that do not name the landlord) meets the THUE pool;
  a player who lets a home they own (housing.py jr_home_let) the CHU pool, about one of their tenants. The dorm has its
  roommate moments already (life kind 'dorm'); the pagoda's monk lives at the pagoda. Someone both renting and letting
  draws from both.
* How often: at most one card every GAP life days, on about P of the days after that, and only on a day the life
  layer drew no card of its own (one card a day at most). Its own random stream (seed, 'tenancy', day): every other
  card rolls exactly as before. No identical card within RECENT days.
* A card: two choices (tenancy_content), ±1–4 tinh thần (the life layer's spirit), a few xu (the journey wallet, history
  kind 'home'; a cost needs the wallet and never pushes it below zero; the default costs nothing), closeness: the life
  layer's bond with a neighbour of the CAST (Bà Tám, Cô Ba…), or with your tenant (`close`, per tenancy). Undecided,
  it takes its default when the next life day turns. Nothing else: never a fee, never the rent itself (housing.py
  keeps the real rent, its late days and repairs).
* The page: life.public() shows it as the pending card when the life layer has none (kind 'home', stage 'dorm' while
  open, so pages that know the roommate cards draw it unchanged), and lf_choose / lf_close with its `tn-` id land here.
* Saves: `journey.tenancy` {v, day, last, seq, card, recent, close, log}, written on the first card. journey.validate
  accepts extra keys, so an older build keeps it untouched and simply shows no card; the life block is unchanged.
"""
from __future__ import annotations

import random

from . import housing as hs
from .tenancy_content import CATS, CHU, LANDLORDS, THUE

VERSION = 1
KIND = 'home'             # journey wallet history kind
FIRST_DAY = 4
GAP = 4                   # life days between two cards, at least
P = .3                    # a card on about this share of the days after the gap
RECENT = 20               # no identical card within this many life days
CLOSE_START = 50
CLOSE_MAX = 8             # tenancies remembered (OWNED_MAX homes, a few past tenants)
LOG_MAX = 12
KEYS = {'v', 'day', 'last', 'seq', 'card', 'recent', 'close', 'log'}
CARD_KEYS = {'id', 'day', 'ref', 'home', 'stage', 'choice', 'spirit', 'money', 'text'}
LOG_KEYS = {'day', 'ref', 'choice', 'spirit', 'money'}
INDEX = {x['id']: dict(x, side='thue') for x in THUE}
INDEX.update({x['id']: dict(x, side='chu') for x in CHU})


def _lf():
    from . import life
    return life


def _core():
    from . import engine
    return engine


def initial() -> dict:
    return dict(v=VERSION, day=0, last=0, seq=0, card=None, recent={}, close={}, log=[])


def get(s: dict) -> dict | None:
    j = s.get('journey')
    T = j.get('tenancy') if isinstance(j, dict) else None
    return T if isinstance(T, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('tenancy'), dict):
        j['tenancy'] = initial()
    return j['tenancy']


# ---------------------------------------------------------------- where you stand
def renting(s: dict) -> str | None:
    """'attic' | 'tro_moi' | 'lease' while you rent (None: you own, share a spouse's home, or sleep in the dorm)."""
    j = s['journey']
    if hs.active_lease(j):
        return 'lease'
    place, kind = hs.where(hs.get(s))
    if place == 'attic':
        return 'attic'
    if place == 'rent' and kind in LANDLORDS:
        return kind
    return None


def lets(s: dict) -> list[dict]:
    """The homes you own that a tenant lives in now."""
    h = hs.get(s)
    return [x for x in (h['props'] if h else []) if x.get('let')]


def _tkey(x: dict) -> str:
    """One tenancy: the home and the day the tenant moved in (a new tenant starts a new closeness)."""
    return f'{x["id"]}:{x["let"]["since"]}'


def _pool(s: dict, T: dict, day: int) -> list[tuple[dict, str]]:
    out = []
    where = renting(s)
    if where:
        out += [(x, '') for x in THUE if not (x.get('landlord') and where == 'lease')]
    for home in lets(s):
        out += [(x, _tkey(home)) for x in CHU]
    return [(x, home) for x, home in out if day - T['recent'].get(x['id'], -99) >= RECENT]


def roll(s: dict, life: dict, day: int, career: str | None) -> dict | None:
    """Today's card (or None), on a day the life layer drew nothing. Deterministic from the seed and the day."""
    from .life_content import CALLING
    j = s['journey']
    if not j.get('story') or day < FIRST_DAY or career in CALLING:
        return None
    T = get(s)
    if T and (T['card'] or day - T['last'] < GAP or T['day'] >= day):
        return None
    if not renting(s) and not lets(s):
        return None
    r = random.Random(f'tenancy|{j.get("seed", 0)}|{day}')
    if r.random() >= P:
        return None
    T = T or initial()
    pool = _pool(s, T, day)
    if not pool:
        return None
    x, home = r.choice(pool)
    T = _ensure(s)
    T['seq'] += 1
    T.update(day=day, last=day)
    T['recent'] = {k: v for k, v in T['recent'].items() if day - v < RECENT and k in INDEX}
    T['recent'][x['id']] = day
    T['card'] = dict(id=f'tn-{T["seq"]}', day=day, ref=x['id'], home=home, stage='ask', choice=None, spirit=0, money=0, text='')
    return T['card']


# ---------------------------------------------------------------- who is in the card
def _home_of(s: dict, card: dict) -> dict | None:
    """The let home a CHU card is about, while that same tenant still lives there."""
    return next((x for x in lets(s) if _tkey(x) == card['home']), None) if card['home'] else None


def _landlord(s: dict) -> dict:
    return LANDLORDS.get(renting(s) or '', LANDLORDS['attic'])


def _speaker(s: dict, card: dict) -> dict | None:
    x = INDEX[card['ref']]
    who = x['who']
    if who == 'chu':
        L = _landlord(s)
        return dict(id=L['cast'] or 'chu', name=L['name'], emoji=L['emoji'], role=L['role'])
    if who == 'khach':
        home = _home_of(s, card)
        emoji, name = hs.tenant(home['let']) if home else ('🙂', 'Người thuê')
        where = hs.lname(hs.HOMES[home['kind']]['name']) if home else 'nhà cho thuê'
        return dict(id='khach', name=name, emoji=emoji, role=f'Người thuê {where}')
    if who:
        p = _lf()._cast().get(who)
        return dict(id=who, name=p['name'], emoji=p['emoji'], role=p['role']) if p else None
    p = x.get('person')
    return dict(id='', **p) if p else None


def _fill(s: dict, card: dict, text: str) -> str:
    home = _home_of(s, card)
    text = text.replace('{chu}', _landlord(s)['name'])
    text = text.replace('{khach}', hs.tenant(home['let'])[1] if home else 'Người thuê')
    text = text.replace('{nha}', hs.lname(hs.HOMES[home['kind']]['name']) if home else 'cho thuê')
    return _lf()._fill(text, s)


def _bond_target(s: dict, card: dict) -> str | None:
    """The life layer's neighbour this card's closeness goes to (None: your tenant, or nobody)."""
    who = INDEX[card['ref']]['who']
    if who == 'chu':
        return _landlord(s)['cast']
    return who if who in _lf()._cast() else None


def _choices(s: dict, card: dict) -> list[dict]:
    w = s['journey']['wallet']
    out = []
    for c in INDEX[card['ref']]['choices']:
        why = f'Ví còn {max(0, w)} xu' if c['money'] < 0 and w < -c['money'] else None
        out.append(dict(id=c['id'], label=_fill(s, card, c['label']), spirit=c['spirit'], money=c['money'], emoji=None,
                        risky=False, ok=not why, why=why))
    return out


# ---------------------------------------------------------------- choosing
def _apply(s: dict, card: dict, cid: str, auto: bool = False) -> str:
    e = _core()
    lf = _lf()
    x = INDEX[card['ref']]
    c = next((c for c in x['choices'] if c['id'] == cid), None)
    e.need(c, 'Lựa chọn này không có trong chuyện.')
    j = s['journey']
    if c['money'] < 0 and j['wallet'] < -c['money']:
        e.need(auto, f'Chưa đủ tiền: ví còn {max(0, j["wallet"])} xu.', 'not_enough')
        c = next(o for o in x['choices'] if o['default'])
    L = lf._state(s)
    T = _ensure(s)
    card['spirit'] = lf._spirit(L, c['spirit'])
    money = c['money']
    if money < 0:
        money = -min(-money, max(0, j['wallet']))
    if money:
        from . import journey
        journey._wallet(j, money, KIND, f'{CATS[x["side"]][1]}: {_fill(s, card, x["title"])}'[:120])
    card['money'] = money
    target = _bond_target(s, card)
    if target:
        lf._bond(L, target, c['bond'])
    for who, n in c['also'].items():
        lf._bond(L, who, n)
    if x['who'] == 'khach' and _home_of(s, card):
        T['close'][card['home']] = lf._clamp(T['close'].get(card['home'], CLOSE_START) + c['bond'])
        keep = {_tkey(h) for h in lets(s)}
        while len(T['close']) > CLOSE_MAX:   # tenants who left first
            T['close'].pop(next((k for k in T['close'] if k not in keep), next(iter(T['close']))))
    card.update(stage='done', choice=c['id'], text=_fill(s, card, c['text'])[:200])
    T['log'] = (T['log'] + [dict(day=card['day'], ref=card['ref'], choice=c['id'], spirit=card['spirit'], money=money)])[-LOG_MAX:]
    return card['text']


def settle(s: dict) -> None:
    """A new life day: yesterday's card takes its default if still open, and is put away."""
    T = get(s)
    if not T or not T['card']:
        return
    card = T['card']
    if card['stage'] == 'ask':
        _apply(s, card, next(c['id'] for c in INDEX[card['ref']]['choices'] if c['default']), auto=True)
    T['card'] = None


def is_mine(cid) -> bool:
    return isinstance(cid, str) and cid.startswith('tn-')


def choose(s: dict, p: dict) -> dict:
    e = _core()
    T = get(s)
    card = T['card'] if T else None
    e.need(card and card['id'] == p['id'] and card['stage'] == 'ask', 'Chuyện này đã qua rồi.', 'already_decided')
    return dict(message=_apply(s, card, p['choice']), effects=[])


def close(s: dict, p: dict) -> dict:
    e = _core()
    T = get(s)
    card = T['card'] if T else None
    e.need(card and card['id'] == p['id'], 'Chuyện này đã cất rồi.', 'already_decided')
    e.need(card['stage'] == 'done', 'Chọn một cách trước đã nhé.')
    T['card'] = None
    return dict(message='', effects=[])


# ---------------------------------------------------------------- the page
def view(s: dict) -> dict | None:
    """The card as life.public's `pending` (the fields of life._card_view)."""
    T = get(s)
    card = T['card'] if T else None
    if not card or card['ref'] not in INDEX:
        return None
    x = INDEX[card['ref']]
    cat_emoji, cat_label = CATS[x['side']]
    who = _speaker(s, card)
    done = card['stage'] == 'done'
    trail = [card['text']] if done and card['text'] else []
    if done and x['who'] == 'khach' and card['home'] in T['close']:
        trail.append(f'Thân thiết với người thuê: {T["close"][card["home"]]}/100')
    return dict(id=card['id'], day=card['day'], kind='home', cat=x['side'], cat_emoji=cat_emoji, cat_label=cat_label,
                emoji=x['emoji'], title=_fill(s, card, x['title']), stage='done' if done else 'dorm', loss=0, hit=0,
                spirit=card['spirit'], money=card['money'], trail=trail, lines=[_fill(s, card, t) for t in x['lines']],
                speaker=who, gop=None, choices=[] if done else _choices(s, card), fact=None, gossip=None,
                who=[who] if who and done else [])


def summary(s: dict) -> dict | None:
    v = view(s)
    return dict(emoji=v['emoji'], title=v['title'], cat_label=v['cat_label']) if v else None


def closeness(s: dict, x: dict) -> int | None:
    """Closeness with the tenant of a let home (housing's home card), once a moment happened."""
    T = get(s)
    return T['close'].get(_tkey(x)) if T and x.get('let') else None


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    T = get(s)
    j = s.get('journey')
    if T is None:
        need(not isinstance(j, dict) or j.get('tenancy') is None, 'Dữ liệu chuyện nhà thuê không hợp lệ.', 'invalid_save')
        return
    bad = 'Dữ liệu chuyện nhà thuê không hợp lệ.'
    need(set(T) == KEYS and T['v'] == VERSION, bad, 'invalid_save')
    for k in ('day', 'last', 'seq'):
        integer(T[k], 0, 10**9)
    need(T['day'] <= j['life_day'] and T['last'] <= j['life_day'], bad)
    need(isinstance(T['recent'], dict) and len(T['recent']) <= len(INDEX), bad)
    for k, v in T['recent'].items():
        need(k in INDEX, bad)
        integer(v, 0, 10**6)
    need(isinstance(T['close'], dict) and len(T['close']) <= CLOSE_MAX, bad)
    for k, v in T['close'].items():
        txt(k, 40)
        integer(v, 0, 100)
    need(isinstance(T['log'], list) and len(T['log']) <= LOG_MAX, bad)
    for r in T['log']:
        need(isinstance(r, dict) and set(r) == LOG_KEYS and r['ref'] in INDEX
             and r['choice'] in {c['id'] for c in INDEX[r['ref']]['choices']}, bad)
        integer(r['day'], 1, 10**6)
        integer(r['spirit'], -20, 20)
        integer(r['money'], -100, 100)
    card = T['card']
    if card is not None:
        need(isinstance(card, dict) and set(card) == CARD_KEYS and card['ref'] in INDEX and card['stage'] in ('ask', 'done'), bad)
        need(is_mine(card['id']) and len(card['id']) <= 24, bad)
        integer(card['day'], 1, 10**6)
        need(card['day'] <= j['life_day'], bad)
        txt(card['home'], 40, 0)
        need((card['home'] != '') == (INDEX[card['ref']]['side'] == 'chu'), bad)
        need(card['choice'] is None if card['stage'] == 'ask' else card['choice'] in {c['id'] for c in INDEX[card['ref']]['choices']}, bad)
        integer(card['spirit'], -20, 20)
        integer(card['money'], -100, 100)
        txt(card['text'], 200, 0)
