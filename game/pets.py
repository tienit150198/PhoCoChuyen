"""🐾 Nuôi thú cưng: adopt or buy a dog or a cat, name it, care for it, dress it up, walk it around town (story mode).

Owner 07/10: "ra thêm nhiều dòng mèo chó cute hơn nữa nhé", and players should have more to spend xu on.
Catalogue: game/pets_content.py (27 breeds, each drawn by public/js/v4/pet-art.js in its coats and poses).

* 🏠 Góc nhận nuôi Chân Nhỏ (the adoption corner of Tiệm Thú Nhỏ Chú Út): SHELTER_SEEN animals wait each life day
  (seeded), local breeds and now and then a purebred someone gave up. Adoption is free; a donation to the rescue
  group is offered (a pure sink, never required). 🛍️ The shop sells every breed and coat at its price.
* Up to MAX_PETS at home. 🏡 "Về quê với bà" sends one to the grandparents' (kept, frozen, can come back): nothing
  is ever lost, no pet ever dies or runs away.
* Care loop, gentle: no bụng (f), vui (j), sạch (c), khỏe (h) 0–100 drop each life day (DECAY). Neglect makes the pet
  sad (mood 'buon') and a little less healthy, never worse. 🍚 Food tiers (free rice at home to a 80 xu feast),
  🎾 play (free by hand, toys wear out or keep), 🛁 bath at home, ✂️ the spa next door (Pet Care Mèo Mập, an NPC),
  or a real player's pet_care workplace (work_visits order → groom_by_player), 🩺 vet check-up, 💉 vaccine.
* Accessories (collars, bows and hats, clothes, beds) are kept; each copy is worn by one pet. Cosmetic only.
* Bond: one point per kind of care a pet gets in a life day (feed, play, clean, vet, show); tricks unlock with it.
* Never pay-to-win: no xu, no work bonus. A happy pet gives +SPIRIT tinh thần once a life day (game/needs.py _spirit).
* 🏆 Bé cưng của tuần: the same care points per (real, Vietnam) ISO week, at most WEEK_DAY_PTS a pet a life day;
  the best pet of each player goes to the `pet_board` table in the save's own transaction (command_commit) and
  GET /api/pets/board shows the top. Cosmetic only, money never buys points.

Money: wallet first, then the bank account (garage._take), never debt; the wallet history uses the existing kind 'life'
(journey.HISTORY_KINDS of every older build): no closed list grows. No command pays xu.

State `s['journey']['pets']` (absent until the first adoption; journey.validate allows extra keys, so 1.9.10 and older
keep loading and writing a save with it untouched), see initial():
    v       VERSION
    list    [pet] at home (≤ MAX_PETS)          farm  [pet] at the grandparents' (≤ MAX_FARM)
    walk    the id of the pet walking with you, or None
    own     {toy or accessory id: count (accessories, kept toys) | uses left (toys that wear out)}
    day     the life day `today` belongs to      today  ['spirit', 'a0'…] used that life day (shelter animals taken)
    seq     the number of the next pet id        stats  {adopted, bought, xu, donated, groomed, vet}
    pet = {id, b (breed), c (coat index), n (name), s ('shop' | 'shelter'), d (life day it came), p (xu paid),
           f, j, cl, h (needs), t (life day the needs belong to), x (bond), tr [trick ids], w {slot: id | None},
           wk (week key of pts), pts, dd (life day of done), done [care kinds that day], vac (vaccinated until, life day)}
Ids a newer build wrote (breeds, accessories) are kept by shape and simply not drawn, so a rollback loses nothing.
Commands (journey.action): jr_pet_adopt, jr_pet_name, jr_pet_feed, jr_pet_play, jr_pet_bath, jr_pet_groom, jr_pet_vet,
jr_pet_buy, jr_pet_wear, jr_pet_walk, jr_pet_show, jr_pet_donate, jr_pet_home, jr_pet_back.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import threading
import time

from . import pets_content as C

VERSION = 1
KIND = 'life'
BLOCK_KEYS = frozenset({'v', 'list', 'farm', 'walk', 'own', 'day', 'today', 'seq', 'stats'})
PET_KEYS = frozenset({'id', 'b', 'c', 'n', 's', 'd', 'p', 'f', 'j', 'cl', 'h', 't', 'x', 'tr', 'w', 'wk', 'pts', 'dd', 'done', 'vac'})
STATS = ('adopted', 'bought', 'xu', 'donated', 'groomed', 'vet')
CARE = ('feed', 'play', 'clean', 'vet', 'show')
SOURCES = ('shop', 'shelter')
NEEDS = ('f', 'j', 'cl', 'h')
ID_RE = re.compile(r'[a-z0-9_]{1,24}')
PID_RE = re.compile(r'p[0-9]{1,6}')
WK_RE = re.compile(r'[0-9]{4}-W[0-9]{2}')
COMMANDS = ('jr_pet_adopt', 'jr_pet_name', 'jr_pet_feed', 'jr_pet_play', 'jr_pet_bath', 'jr_pet_groom', 'jr_pet_vet',
            'jr_pet_buy', 'jr_pet_wear', 'jr_pet_walk', 'jr_pet_show', 'jr_pet_donate', 'jr_pet_home', 'jr_pet_back')
VN = datetime.timezone(datetime.timedelta(hours=7))
BIG = 10**12
MAX_DAYS = 30             # one tick never counts more life days than this (the floor is reached long before)
TRICK_IDS = {k: tuple(t[0] for t in v) for k, v in C.TRICKS.items()}


# ---------------------------------------------------------------- helpers
def now() -> float:
    return time.time()


def week_key(t: float | None = None) -> str:
    y, w, _ = datetime.datetime.fromtimestamp(now() if t is None else t, VN).isocalendar()
    return f'{y:04d}-W{w:02d}'


def _core():
    from . import engine
    return engine


def _gr():
    from . import garage
    return garage


def _fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _int(v, lo: int = 0, hi: int = BIG) -> bool:
    return type(v) is int and lo <= v <= hi


def initial(day: int = 1) -> dict:
    return dict(v=VERSION, list=[], farm=[], walk=None, own={}, day=max(1, int(day)), today=[], seq=1,
                stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get('pets') if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('pets'), dict):
        j['pets'] = initial(j['life_day'])
    b = j['pets']
    if b['day'] != j['life_day']:
        b['day'], b['today'] = j['life_day'], []
    return b


def _today(s: dict) -> list:
    b = get(s)
    return list(b['today']) if b and b['day'] == s['journey']['life_day'] else []


def breed_of(p: dict) -> dict | None:
    return C.BREEDS.get(p.get('b'))


def kind_of(p: dict) -> str:
    br = breed_of(p)
    return br['kind'] if br else 'dog'


def coat_of(p: dict) -> dict:
    br = breed_of(p)
    coats = br['coats'] if br else [dict(name='', b='#d9a066', m='#b47a45', l='#ecc28f', e='#3b2a22')]
    return coats[p['c']] if 0 <= p.get('c', 0) < len(coats) else coats[0]


# ---------------------------------------------------------------- needs
def needs_at(p: dict, day: int) -> dict:
    """The pet's needs on life day `day` (pure: the save is not touched)."""
    n = {k: p[k] for k in NEEDS}
    days = max(0, min(MAX_DAYS, day - p['t']))
    for i in range(days):
        n['f'] = max(0, n['f'] - C.DECAY['f'])
        n['j'] = max(0, n['j'] - C.DECAY['j'])
        n['cl'] = max(0, n['cl'] - C.DECAY['c'])
        n['h'] = max(0, n['h'] - C.DECAY['h'] - (C.SICK_DECAY if n['f'] < C.LOW or n['cl'] < C.LOW else 0))
        if p['vac'] >= p['t'] + i + 1:
            n['h'] = max(n['h'], C.VACCINE['floor'])
    return n


def mood(n: dict) -> str:
    """'vui' (happy), 'on' (fine) or 'buon' (sad: something under LOW). Never worse than sad."""
    lo = min(n.values())
    if lo < C.LOW:
        return 'buon'
    return 'vui' if lo >= 50 and sum(n.values()) >= 4 * 70 else 'on'


def _tick(p: dict, day: int) -> None:
    if p['t'] < day:
        p.update(needs_at(p, day))
        p['t'] = day


def _clamp(v: int) -> int:
    return max(0, min(100, int(v)))


def _care(s: dict, p: dict, kind: str, out: list) -> None:
    """Bond and the week's points: one per kind of care a pet gets in a life day. Tricks unlock with the bond.
    The first care of a life day from a pet that is not sad: +SPIRIT tinh thần (once a day for all pets)."""
    day = s['journey']['life_day']
    if p['dd'] != day:
        p['dd'], p['done'] = day, []
    b = _ensure(s)
    if 'spirit' not in b['today'] and mood({k: p[k] for k in NEEDS}) != 'buon':
        from . import needs
        got = needs._spirit(s, C.SPIRIT)
        b['today'].append('spirit')
        if got:
            out.append(f'{p["n"]} quấn chân, tinh thần +{got}.')
    if kind in p['done']:
        return
    p['done'].append(kind)
    p['x'] += 1
    wk = week_key()
    if p['wk'] != wk:
        p['wk'], p['pts'] = wk, 0
    p['pts'] += 1
    for tid, emoji, name, at in C.TRICKS[kind_of(p)]:
        if p['x'] >= at and tid not in p['tr']:
            p['tr'].append(tid)
            out.append(f'🎉 {p["n"]} vừa học được: {emoji} {name}!')
            break


# ---------------------------------------------------------------- the shelter (seeded each life day)
def shelter_today(s: dict) -> list:
    """[{i, b, c, n}] waiting at the adoption corner on this life day (taken ones are marked by the client)."""
    j = s['journey']
    h = hashlib.sha256(f"pets|{j.get('seed', 0)}|{j['life_day']}".encode()).digest()
    out, used = [], set()
    for i in range(C.SHELTER_SEEN):
        pool = C.SHELTER_RARE if i == C.SHELTER_SEEN - 1 and h[20] % C.RARE_EVERY == 0 else C.SHELTER
        bid = pool[h[i * 3] % len(pool)]
        coat = h[i * 3 + 1] % len(C.BREEDS[bid]['coats'])
        name = C.SHELTER_NAMES[h[i * 3 + 2] % len(C.SHELTER_NAMES)]
        while name in used:
            name = C.SHELTER_NAMES[(C.SHELTER_NAMES.index(name) + 1) % len(C.SHELTER_NAMES)]
        used.add(name)
        out.append(dict(i=i, b=bid, c=coat, n=name))
    return out


# ---------------------------------------------------------------- save
def _pet_ok(p) -> bool:
    if not (isinstance(p, dict) and set(p) == PET_KEYS):
        return False
    return (isinstance(p['id'], str) and PID_RE.fullmatch(p['id']) is not None
            and isinstance(p['b'], str) and ID_RE.fullmatch(p['b']) is not None and _int(p['c'], 0, 15)
            and isinstance(p['n'], str) and 1 <= len(p['n']) <= C.NAME_MAX and p['s'] in SOURCES
            and _int(p['d'], 1, 10**6) and _int(p['p'], 0, 10**7) and all(_int(p[k], 0, 100) for k in NEEDS)
            and _int(p['t'], 1, 10**6) and _int(p['x'], 0, 10**6)
            and isinstance(p['tr'], list) and len(p['tr']) <= 16 and all(isinstance(x, str) and ID_RE.fullmatch(x) for x in p['tr'])
            and isinstance(p['w'], dict) and set(p['w']) == set(C.SLOT_IDS)
            and all(v is None or (isinstance(v, str) and ID_RE.fullmatch(v) is not None) for v in p['w'].values())
            and isinstance(p['wk'], str) and (p['wk'] == '' or WK_RE.fullmatch(p['wk']) is not None) and _int(p['pts'], 0, 10**6)
            and _int(p['dd'], 0, 10**6) and isinstance(p['done'], list) and len(p['done']) <= len(CARE)
            and all(x in CARE for x in p['done']) and _int(p['vac'], 0, 10**6))


def _worn_counts(b: dict) -> dict:
    out: dict = {}
    for p in b['list'] + b['farm']:
        for v in p['w'].values():
            if v:
                out[v] = out.get(v, 0) + 1
    return out


def validate(s: dict) -> None:
    """``s['journey']['pets']`` (absent in older saves). Raises GameError like validate_state."""
    e = _core()
    b = get(s)
    j = s.get('journey')
    bad = 'Dữ liệu thú cưng trong bản lưu không hợp lệ.'
    if b is None:
        e.need(not isinstance(j, dict) or j.get('pets') is None, bad, 'invalid_save')
        return
    need = lambda ok: e.need(ok, bad, 'invalid_save')
    need(set(b) == BLOCK_KEYS and b['v'] == VERSION and _int(b['day'], 1, 10**6) and _int(b['seq'], 1, 10**6))
    need(isinstance(b['list'], list) and len(b['list']) <= C.MAX_PETS and isinstance(b['farm'], list) and len(b['farm']) <= C.MAX_FARM)
    pets = b['list'] + b['farm']
    need(all(_pet_ok(p) for p in pets))
    ids = [p['id'] for p in pets]
    need(len(ids) == len(set(ids)) and all(int(i[1:]) < b['seq'] for i in ids))
    need(b['walk'] is None or b['walk'] in [p['id'] for p in b['list']])
    own = b['own']
    need(isinstance(own, dict) and len(own) <= 64 and all(isinstance(k, str) and ID_RE.fullmatch(k) and _int(v, 0, 10**6) for k, v in own.items()))
    need(all(own.get(k, 0) >= n for k, n in _worn_counts(b).items()))
    need(isinstance(b['today'], list) and len(b['today']) <= 16 and all(isinstance(x, str) and ID_RE.fullmatch(x) for x in b['today']))
    st = b['stats']
    need(isinstance(st, dict) and set(st) <= set(STATS) and all(_int(v) for v in st.values()))


def _fix_pet(p, seq_ok) -> dict | None:
    """A pet record from a newer build (extra fields) or a hand edit: keep it when its core still makes sense."""
    if not isinstance(p, dict):
        return None
    core = {k: p.get(k) for k in PET_KEYS}
    if not (isinstance(core['id'], str) and PID_RE.fullmatch(core['id']) and seq_ok(core['id'])):
        return None
    if not (isinstance(core['b'], str) and ID_RE.fullmatch(core['b']) and isinstance(core['n'], str) and 1 <= len(core['n']) <= C.NAME_MAX):
        return None
    out = dict(id=core['id'], b=core['b'], n=core['n'])
    out['c'] = core['c'] if _int(core['c'], 0, 15) else 0
    out['s'] = core['s'] if core['s'] in SOURCES else 'shop'
    out['d'] = core['d'] if _int(core['d'], 1, 10**6) else 1
    out['p'] = core['p'] if _int(core['p'], 0, 10**7) else 0
    for k in NEEDS:
        out[k] = core[k] if _int(core[k], 0, 100) else 50
    out['t'] = core['t'] if _int(core['t'], 1, 10**6) else out['d']
    out['x'] = core['x'] if _int(core['x'], 0, 10**6) else 0
    out['tr'] = [x for x in core['tr'] if isinstance(x, str) and ID_RE.fullmatch(x)][:16] if isinstance(core['tr'], list) else []
    w = core['w'] if isinstance(core['w'], dict) else {}
    out['w'] = {k: w.get(k) if isinstance(w.get(k), str) and ID_RE.fullmatch(w.get(k)) else None for k in C.SLOT_IDS}
    out['wk'] = core['wk'] if isinstance(core['wk'], str) and WK_RE.fullmatch(core['wk']) else ''
    out['pts'] = core['pts'] if _int(core['pts'], 0, 10**6) else 0
    out['dd'] = core['dd'] if _int(core['dd'], 0, 10**6) else 0
    out['done'] = [x for x in core['done'] if x in CARE][:len(CARE)] if isinstance(core['done'], list) else []
    out['done'] = list(dict.fromkeys(out['done']))
    out['vac'] = core['vac'] if _int(core['vac'], 0, 10**6) else 0
    return out


def upgrade(j: dict) -> None:
    """A block a newer build wrote with extra fields, or a hand-edited one: keep every pet and item that still makes
    sense (pets over the cap go to the grandparents', never away). Absent stays absent."""
    if not isinstance(j, dict) or 'pets' not in j:
        return
    b = j['pets']
    if not isinstance(b, dict):
        j['pets'] = initial(j.get('life_day') if _int(j.get('life_day'), 1, 10**6) else 1)
        return
    out = initial(b['day'] if _int(b.get('day'), 1, 10**6) else 1)
    seq = b['seq'] if _int(b.get('seq'), 1, 10**6) else 1
    seen: set = set()

    def fixed(rows):
        res = []
        for p in rows if isinstance(rows, list) else []:
            q = _fix_pet(p, lambda i: True)
            if q and q['id'] not in seen:
                seen.add(q['id'])
                res.append(q)
        return res
    home, farm = fixed(b.get('list')), fixed(b.get('farm'))
    out['list'], over = home[:C.MAX_PETS], home[C.MAX_PETS:]
    out['farm'] = (over + farm)[:C.MAX_FARM]
    out['seq'] = max([seq] + [int(p['id'][1:]) + 1 for p in out['list'] + out['farm']])
    out['walk'] = b.get('walk') if b.get('walk') in [p['id'] for p in out['list']] else None
    own = b.get('own') if isinstance(b.get('own'), dict) else {}
    out['own'] = {k: v for k, v in list(own.items())[:64] if isinstance(k, str) and ID_RE.fullmatch(k) and _int(v, 0, 10**6)}
    for k, n in _worn_counts(out).items():   # a worn item the block no longer counts: owned again, never taken off
        out['own'][k] = max(out['own'].get(k, 0), n)
    if isinstance(b.get('today'), list):
        out['today'] = [x for x in b['today'] if isinstance(x, str) and ID_RE.fullmatch(x)][:16]
    st = b.get('stats') if isinstance(b.get('stats'), dict) else {}
    out['stats'] = {k: st[k] if _int(st.get(k)) else 0 for k in STATS}
    if out != b:
        j['pets'] = out


# ---------------------------------------------------------------- commands
def _keys(p: dict, allowed: set, required: set = frozenset()) -> None:
    _core().need(isinstance(p, dict) and set(p) <= allowed and required <= set(p), 'Thông tin không hợp lệ.')


def _pet(s: dict, pid) -> dict:
    b = get(s)
    p = next((x for x in b['list'] if x['id'] == pid), None) if b and isinstance(pid, str) else None
    _core().need(p is not None, 'Chọn một bé ở nhà nhé.', 'not_owned')
    return p


def _name(value) -> str:
    from .accounts import character_name
    name = character_name(value)
    _core().need(len(name) <= C.NAME_MAX, f'Tên bé tối đa {C.NAME_MAX} ký tự nhé.', 'bad_display')
    return name


def _ready_why(s: dict, price: int) -> str:
    j = s['journey']
    if price <= 0:
        return ''
    if j['wallet'] < 0:
        return f'Ví đang nợ {_fmt(-j["wallet"])} xu. Trả nợ trước nhé.'
    short = price - _gr()._have(s)['ready']
    return f'Còn thiếu {_fmt(short)} xu.' if short > 0 else ''


def _pay(s: dict, price: int, label: str) -> str:
    """Wallet first, then the bank account; the caller checked _ready_why. The sentence saying where it came from."""
    if price <= 0:
        return ''
    why = _ready_why(s, price)
    _core().need(not why, why, 'not_enough')
    how = _gr()._take(s, price, label[:120])
    _ensure(s)['stats']['xu'] += price
    return how


def _new_pet(b: dict, day: int, bid: str, coat: int, name: str, src: str, paid: int) -> dict:
    p = dict(id=f'p{b["seq"]}', b=bid, c=coat, n=name, s=src, d=day, p=paid, f=C.START['f'], j=C.START['j'],
             cl=C.START['c'], h=C.START['h'], t=day, x=0, tr=[], w={k: None for k in C.SLOT_IDS}, wk='', pts=0, dd=0,
             done=[], vac=0)
    b['seq'] += 1
    return p


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Nuôi thú cưng chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    day = j['life_day']
    b0 = get(s)
    if b0:
        for x in b0['list']:
            _tick(x, day)
    out: list = []

    if name == 'jr_pet_adopt':
        _keys(p, {'from', 'i', 'breed', 'coat', 'nick', 'donate', 'confirm'}, {'from', 'nick', 'confirm'})
        src = p['from']
        need(src in SOURCES, 'Chọn nhận nuôi hoặc mua ở tiệm nhé.')
        b = get(s)
        need(not b or len(b['list']) < C.MAX_PETS, f'Nhà đã đủ {C.MAX_PETS} bé rồi. Gửi một bé về quê với bà trước nhé.', 'limit')
        pet_name = _name(p['nick'])
        donate = p.get('donate', 0)
        need(_int(donate, 0, C.DONATE_MAX), 'Số xu ủng hộ không hợp lệ.')
        if src == 'shelter':
            need(_int(p.get('i'), 0, C.SHELTER_SEEN - 1), 'Chọn một bé ở góc nhận nuôi nhé.')
            a = shelter_today(s)[p['i']]
            need(f'a{a["i"]}' not in _today(s), f'{a["n"]} đã có nhà mới hôm nay rồi.', 'gone')
            bid, coat, price = a['b'], a['c'], 0
        else:
            need(donate == 0, 'Ủng hộ cứu hộ ở góc nhận nuôi nhé.')
            bid = p.get('breed')
            need(isinstance(bid, str) and bid in C.BREEDS, 'Chọn một giống trong tiệm nhé.')
            coat = p.get('coat', 0)
            need(_int(coat, 0, len(C.BREEDS[bid]['coats']) - 1), 'Chọn một màu lông nhé.')
            price = C.BREEDS[bid]['price']
        br = C.BREEDS[bid]
        need(p['confirm'] is True, f'Xác nhận đón bé {br["name"]} về nhà.')
        total = price + donate
        why = _ready_why(s, total)
        need(not why, why, 'not_enough')
        how = _pay(s, price, f'Thú cưng · {br["name"]} {pet_name}') if price else ''
        gift = _pay(s, donate, 'Ủng hộ Nhóm cứu hộ Chân Nhỏ') if donate else ''
        b = _ensure(s)
        if donate:
            b['stats']['donated'] += donate
        pet = _new_pet(b, day, bid, coat, pet_name, src, price)
        b['list'].append(pet)
        if b['walk'] is None:
            b['walk'] = pet['id']
        if src == 'shelter':
            b['today'].append(f'a{p["i"]}')
            b['stats']['adopted'] += 1
            msg = f'🏠 {pet_name} về nhà mới rồi!'
        else:
            b['stats']['bought'] += 1
            msg = f'🐾 {pet_name} về nhà! ({how})'
        if gift:
            msg += ' 💗 Chân Nhỏ cảm ơn bạn!'
        return dict(message=msg)

    if name == 'jr_pet_donate':
        _keys(p, {'amount', 'confirm'}, {'amount', 'confirm'})
        amount = e.integer(p['amount'], 1, C.DONATE_MAX)
        need(p['confirm'] is True, f'Xác nhận ủng hộ {_fmt(amount)} xu.')
        how = _pay(s, amount, 'Ủng hộ Nhóm cứu hộ Chân Nhỏ')
        b = _ensure(s)
        b['stats']['donated'] += amount
        return dict(message=f'💗 Đã ủng hộ {how}. Mấy bé ở Chân Nhỏ có thêm bữa pate rồi!')

    if name == 'jr_pet_buy':
        _keys(p, {'id', 'qty', 'confirm'}, {'id', 'confirm'})
        iid = p['id']
        it = C.ACC.get(iid) or C.TOY.get(iid) if isinstance(iid, str) else None
        need(it is not None, 'Chọn một món trong tiệm nhé.')
        qty = p.get('qty', 1)
        need(_int(qty, 1, 3), 'Mua từ 1 đến 3 món một lần nhé.')
        need(p['confirm'] is True, f'Xác nhận mua {it["name"]}.')
        b = _ensure(s)
        kept = iid in C.TOY and C.TOY[iid]['uses'] == 0
        if kept:
            need(b['own'].get(iid, 0) == 0, f'Bạn đã có {it["name"]} rồi.', 'duplicate')
            qty = 1
        price = it['price'] * qty
        how = _pay(s, price, f'Đồ thú cưng · {it["name"]}' + (f' ×{qty}' if qty > 1 else ''))
        b['own'][iid] = min(10**6, b['own'].get(iid, 0) + (C.TOY[iid]['uses'] * qty if iid in C.TOY and not kept else qty))
        return dict(message=f'🛍️ Đã trả {how} cho {it["name"]}' + (f' ×{qty}' if qty > 1 else '') + '.')

    if name == 'jr_pet_back':
        _keys(p, {'pet'}, {'pet'})
        b = get(s)
        x = next((q for q in b['farm'] if q['id'] == p['pet']), None) if b else None
        need(x is not None, 'Không thấy bé này ở quê.', 'not_owned')
        need(len(b['list']) < C.MAX_PETS, f'Nhà đã đủ {C.MAX_PETS} bé rồi.', 'limit')
        b['farm'].remove(x)
        x['t'] = day   # bà chăm kỹ lắm: no decay while away
        for k in NEEDS:
            x[k] = max(x[k], 80)
        b['list'].append(x)
        if b['walk'] is None:
            b['walk'] = x['id']
        return dict(message=f'🏡 {x["n"]} về lại nhà, mập lên trông thấy. Bà gửi kèm túi cơm cháy.')

    pet = _pet(s, p.get('pet'))
    b = get(s)
    nm = pet['n']
    kind = kind_of(pet)

    if name == 'jr_pet_name':
        _keys(p, {'pet', 'nick'}, {'pet', 'nick'})
        pet['n'] = _name(p['nick'])
        return dict(message=f'Giờ bé tên là {pet["n"]}.')

    if name == 'jr_pet_feed':
        _keys(p, {'pet', 'food'}, {'pet', 'food'})
        f = C.FOOD.get(p['food']) if isinstance(p['food'], str) else None
        need(f is not None, 'Chọn món cho bé nhé.')
        need(pet['f'] < C.FULL, f'{nm} no căng rồi, để lát nữa nhé.', 'full')
        how = _pay(s, f['price'], f'Thức ăn thú cưng · {f["name"]}')
        pet['f'] = _clamp(pet['f'] + f['f'])
        pet['j'] = _clamp(pet['j'] + f['j'])
        _care(s, pet, 'feed', out)
        return dict(message=' '.join([f'{f["emoji"]} {f["line"]}' + (f' ({how})' if how else '')] + out))

    if name == 'jr_pet_play':
        _keys(p, {'pet', 'toy'}, {'pet'})
        tid = p.get('toy')
        need(pet['j'] < C.FULL, f'{nm} chơi mệt rồi, đang nằm thở.', 'full')
        if tid is None:
            gain, line = C.PLAY_FREE, f'Bạn ném dép, {nm} chạy theo cười toe.' if kind == 'dog' else f'Bạn lắc sợi dây, {nm} vồ trượt rồi giả vờ không quan tâm.'
        else:
            t = C.TOY.get(tid) if isinstance(tid, str) else None
            need(t is not None and t['kind'] in ('both', kind), 'Món đồ chơi này không hợp với bé.')
            need(b['own'].get(tid, 0) > 0, f'Bạn chưa có {t["name"]}.', 'not_owned')
            if t['uses']:
                b['own'][tid] -= 1
                if not b['own'][tid]:
                    b['own'].pop(tid)
            gain, line = t['j'], f'{t["emoji"]} {nm} mê {t["name"].lower()} lắm luôn!'
        pet['j'] = _clamp(pet['j'] + gain)
        pet['f'] = _clamp(pet['f'] - 5)
        _care(s, pet, 'play', out)
        return dict(message=' '.join([line] + out))

    if name in ('jr_pet_bath', 'jr_pet_groom'):
        _keys(p, {'pet', 'confirm'}, {'pet'})
        need(pet['cl'] < C.FULL, f'{nm} đang thơm phức rồi.', 'full')
        if name == 'jr_pet_bath':
            it, price = C.BATH, C.BATH['price']
        else:
            it, price = C.GROOM, C.GROOM['price'] if kind == 'dog' else C.GROOM_CAT
            need(p.get('confirm') is True, f'Xác nhận spa cho {nm} ({price} xu).')
        how = _pay(s, price, f'Thú cưng · {it["name"]}')
        pet['cl'] = _clamp(pet['cl'] + it['c'])
        pet['j'] = _clamp(pet['j'] + it['j'])
        if name == 'jr_pet_groom':
            b['stats']['groomed'] += 1
        _care(s, pet, 'clean', out)
        return dict(message=' '.join([f'{it["emoji"]} {it["line"]} ({how})'] + out))

    if name == 'jr_pet_vet':
        _keys(p, {'pet', 'what', 'confirm'}, {'pet', 'what', 'confirm'})
        what = p['what']
        need(what in ('kham', 'tiem'), 'Chọn khám hay tiêm nhé.')
        it = C.VET if what == 'kham' else C.VACCINE
        if what == 'kham':
            need(pet['h'] < C.FULL, f'{nm} đang khỏe re, chưa cần khám.', 'full')
        else:
            need(pet['vac'] < day, f'{nm} còn hạn tiêm {pet["vac"] - day + 1} ngày.', 'full')
        need(p['confirm'] is True, f'Xác nhận {it["name"].lower()} cho {nm} ({it["price"]} xu).')
        how = _pay(s, it['price'], f'Thú y Cỏ May · {it["name"]}')
        if what == 'kham':
            pet['h'] = it['h']
        else:
            pet['h'] = _clamp(max(pet['h'] + it['h'], it['floor']))
            pet['vac'] = day + it['days'] - 1
        b['stats']['vet'] += 1
        _care(s, pet, 'vet', out)
        return dict(message=' '.join([f'{it["emoji"]} {it["line"]} ({how})'] + out))

    if name == 'jr_pet_wear':
        _keys(p, {'pet', 'slot', 'id'}, {'pet', 'slot'})
        slot, iid = p['slot'], p.get('id')
        need(slot in C.SLOT_IDS, 'Thông tin không hợp lệ.')
        if iid is None:
            pet['w'][slot] = None
            return dict(message=f'Đã tháo cho {nm}.')
        a = C.ACC.get(iid) if isinstance(iid, str) else None
        need(a is not None and a['slot'] == slot, 'Món này không đeo chỗ đó được.')
        pet['w'][slot] = None
        free = b['own'].get(iid, 0) - _worn_counts(b).get(iid, 0)
        need(free > 0, f'{a["name"]} đang có bé khác dùng. Mua thêm một cái nhé.', 'not_owned')
        pet['w'][slot] = iid
        return dict(message=f'{a["emoji"]} {nm} diện {a["name"].lower()}, xinh xỉu!')

    if name == 'jr_pet_walk':
        _keys(p, {'pet'}, set())
        b['walk'] = pet['id'] if b['walk'] != pet['id'] else None
        return dict(message=f'🦮 {nm} đi dạo cùng bạn.' if b['walk'] else f'{nm} ở nhà trông nhà.')

    if name == 'jr_pet_show':
        _keys(p, {'pet', 'trick'}, {'pet'})
        tr = p.get('trick')
        known = [t for t in C.TRICKS[kind] if t[0] in pet['tr']]
        if tr is not None:
            need(isinstance(tr, str) and tr in pet['tr'], f'{nm} chưa học trò này.')
            t = next(t for t in known if t[0] == tr)
            line = f'{t[1]} {nm}: {t[2]}! Cả xóm vỗ tay.'
        else:
            line = f'📸 Tạch! Ảnh {nm} xinh hết nấc.'
        _care(s, pet, 'show', out)
        return dict(message=' '.join([line] + out))

    if name == 'jr_pet_home':
        _keys(p, {'pet', 'confirm'}, {'pet', 'confirm'})
        need(p['confirm'] is True, f'Xác nhận gửi {nm} về quê với bà.')
        need(len(b['farm']) < C.MAX_FARM, 'Nhà bà đã đông thú lắm rồi.', 'limit')
        b['list'].remove(pet)
        b['farm'].append(pet)
        if b['walk'] == pet['id']:
            b['walk'] = b['list'][0]['id'] if b['list'] else None
        return dict(message=f'🏡 {nm} về quê với bà, có vườn rộng chạy nhảy. Muốn đón về lúc nào cũng được.')
    raise e.GameError('Thao tác thú cưng không hợp lệ.', 'unknown_action')


def groom_by_player(s: dict) -> bool:
    """A real player's pet_care workplace took an order from this save (game/work_visits.py): every pet at home comes
    back clean. No money here (the order service holds and pays it). True when a pet was groomed."""
    b = get(s)
    j = s.get('journey')
    if not b or not b['list'] or not isinstance(j, dict) or not _int(j.get('life_day'), 1, 10**6):
        return False
    out: list = []
    for p in b['list']:
        _tick(p, j['life_day'])
        p['cl'] = 100
        p['j'] = _clamp(p['j'] + C.GROOM['j'])
        if b['day'] != j['life_day']:
            b['day'], b['today'] = j['life_day'], []
        _care(s, p, 'clean', out)
    b['stats']['groomed'] += 1
    return True


# ---------------------------------------------------------------- views
def pet_view(p: dict, day: int) -> dict:
    n = needs_at(p, day) if p['t'] < day else {k: p[k] for k in NEEDS}
    br = breed_of(p)
    known = br is not None
    kind = kind_of(p)
    tricks = C.TRICKS[kind]
    nxt = next(({'emoji': t[1], 'name': t[2], 'at': t[3]} for t in tricks if t[0] not in p['tr']), None)
    wk = week_key()
    return dict(id=p['id'], b=p['b'], c=p['c'], n=p['n'], s=p['s'], d=p['d'], known=known, kind=kind, needs=n, mood=mood(n),
                x=p['x'], tr=[t[0] for t in tricks if t[0] in p['tr']], next=nxt,
                w={k: v for k, v in p['w'].items() if v in C.ACC}, pts=p['pts'] if p['wk'] == wk else 0,
                done=list(p['done']) if p['dd'] == day else [], vac=max(0, p['vac'] - day + 1))


def walk_ref(s: dict) -> dict | None:
    """The pet walking with you as the live street sees it (`pt`, live/street.py clean_pet): breed, coat, name,
    what it wears. None: no pet out, or one this build cannot draw."""
    b = get(s)
    p = next((x for x in b['list'] if x['id'] == b['walk']), None) if b else None
    if not p or p['b'] not in C.BREEDS:
        return None
    return dict(b=p['b'], c=p['c'], n=p['n'], a=[v for k, v in p['w'].items() if v in C.ACC and k != 'bed'])


def public(s: dict) -> dict:
    j = s['journey']
    b = get(s)
    day = j['life_day']
    out = dict(story=bool(j.get('story')), max=C.MAX_PETS)
    if not j.get('story'):
        return out
    taken = set(_today(s))
    out['shelter'] = [dict(a, taken=f'a{a["i"]}' in taken) for a in shelter_today(s)]
    if b:
        out.update(pets=[pet_view(p, day) for p in b['list']],
                   farm=[dict(id=p['id'], b=p['b'], c=p['c'], n=p['n']) for p in b['farm']],
                   walk=b['walk'], own=dict(b['own']), spirit='spirit' in taken, stats=dict(b['stats']),
                   ref=walk_ref(s))
    return out


def catalogue() -> dict:
    """Static lists for the client (bootstrap content, cached)."""
    return dict(breeds=[dict(C.BREEDS[i], coats=[dict(c) for c in C.BREEDS[i]['coats']]) for i in C.ORDER],
                foods=[dict(x) for x in C.FOODS], toys=[dict(x) for x in C.TOYS], accs=[dict(x) for x in C.ACCS],
                slots=[dict(id=a, emoji=b, name=c) for a, b, c in C.SLOTS],
                tricks={k: [dict(id=t[0], emoji=t[1], name=t[2], at=t[3]) for t in v] for k, v in C.TRICKS.items()},
                bath=dict(C.BATH), groom=dict(C.GROOM, cat=C.GROOM_CAT), vet=dict(C.VET), vaccine=dict(C.VACCINE),
                play_free=C.PLAY_FREE, full=C.FULL, low=C.LOW, max=C.MAX_PETS, name_max=C.NAME_MAX,
                shelter=C.SHELTER_NAME, shop=C.SHOP_NAME, donate=list(C.DONATE),
                poses=[dict(id=a, name=b) for a, b in C.POSES], frames=[dict(id=a, emoji=b, name=c) for a, b, c in C.FRAMES])


# ---------------------------------------------------------------- 🏆 Bé cưng của tuần (pet_board, GET /api/pets/board)
def board_row(after: dict) -> dict | None:
    """This save's best pet this week (most points, then the oldest), or None."""
    b = get(after)
    if not b:
        return None
    wk = week_key()
    best = None
    for p in b['list'] + b['farm']:
        if p['wk'] == wk and p['pts'] > 0 and p['b'] in C.BREEDS and (best is None or p['pts'] > best['pts']):
            best = p
    if not best:
        return None
    return dict(week=wk, name=best['n'], breed=best['b'], coat=best['c'], pts=best['pts'],
                acc=json.dumps([v for k, v in best['w'].items() if v in C.ACC and k != 'bed']))


def command_commit(db, sid: str, action: str, after: dict) -> None:
    """Called by the storage layer for jr_pet_* commands, in the save's transaction (game/storage.py)."""
    if not action.startswith('jr_pet_'):
        return
    row = board_row(after)
    if not row:
        return
    db.execute('INSERT INTO pet_board(sid, week, name, breed, coat, acc, pts, at) VALUES(?,?,?,?,?,?,?,?) '
               'ON CONFLICT (sid, week) DO UPDATE SET name=EXCLUDED.name, breed=EXCLUDED.breed, coat=EXCLUDED.coat, '
               'acc=EXCLUDED.acc, pts=EXCLUDED.pts, at=EXCLUDED.at',
               (sid, row['week'], row['name'], row['breed'], row['coat'], row['acc'], row['pts'], now()))
    _BOARD.clear()


def forget(db, sid: str) -> None:
    """A player erased their data: their pets leave the board."""
    db.execute('DELETE FROM pet_board WHERE sid=?', (sid,))
    _BOARD.clear()


BOARD_TOP = 10
BOARD_SECS = 15.0
_BOARD: dict = {}          # week key -> (at, rows): one entry, bounded
_LOCK = threading.Lock()


def _rows(store, wk: str) -> list:
    with _LOCK:
        hit = _BOARD.get(wk)
        if hit and time.monotonic() - hit[0] < BOARD_SECS:
            return hit[1]
    with store.connect() as db:
        rows = db.execute('SELECT b.sid AS sid, b.name AS name, b.breed AS breed, b.coat AS coat, b.acc AS acc, b.pts AS pts, '
                          'a.display AS display FROM pet_board b LEFT JOIN accounts a ON a.sid=b.sid WHERE b.week=? '
                          'ORDER BY b.pts DESC, b.at ASC LIMIT ?', (wk, BOARD_TOP)).fetchall()
    out = []
    for r in rows:
        try:
            acc = [x for x in json.loads(r['acc'] or '[]') if x in C.ACC][:3]
        except (TypeError, ValueError):
            acc = []
        out.append(dict(sid=r['sid'], name=str(r['name'])[:C.NAME_MAX], b=r['breed'], c=int(r['coat']), a=acc,
                        pts=int(r['pts']), owner=str(r['display'])[:24] if r['display'] else 'Khách'))
    with _LOCK:
        _BOARD.clear()
        _BOARD[wk] = (time.monotonic(), out)
    return out


def board(store, token: str | None) -> dict:
    wk = week_key()
    rows = _rows(store, wk)
    sid = store.key(token) if isinstance(token, str) and 16 <= len(token) <= 128 else None
    return dict(week=wk, top=[{k: v for k, v in x.items() if k != 'sid'} | {'me': bool(sid) and x['sid'] == sid} for x in rows])
