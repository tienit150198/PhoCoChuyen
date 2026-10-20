"""👗 Tủ đồ thú cưng (owner 19/10: "trang phục thêm nhiều đi, nhiều món cũng có ghép, nhiều món cấp cao thì được cộng
thêm %, làm pet cute, tỏa hào quang, mấy cái đó cũng phân cấp, ghép thì được món cấp cao hơn"; "ghép đồ thì 3 món phải
giống nhau"; "dòng sang k bán mà phải ghép"; "đồ ở shop là chỉ có bậc D và C"; "đồ level thấp chưa tăng nhưng đồ cao tăng
giá"; "đừng show tỷ lệ ra"). The pieces are in game/pet_wardrobe_content.py.

* Every piece you own is one item {id, k piece, r rank D…SSS}. Six slots (neck, head, eye, body, back, bed); a pet wears
  one item a slot, an item is worn by one pet at a time.
* 🛍️ jr_pet_wbuy: rank D at its price or C at C_MULT times it; a luxury piece is never sold, a season's piece only in
  its `sale` days.
* 🔀 jr_pet_wfuse: three items of the same piece and rank (worn ones are taken off) for FUSE_FEE: FUSE_BP of a success
  gives one item a rank up; from rank A up, LUX_BP of those turn into the slot's luxury piece. A failure keeps the
  three, the fee is spent. No daily limit (owner 19/10 "đừng giới hạn lượt ghép"). The odds are never shown.
* 🤖 jr_pet_wfuse_auto (owner: "ghép tự động cho áo quần"): that fusion again and again, the lowest-rank triple
  first, worn items kept out (keep_worn), within a budget and AUTO_MAX fusions; one charge, one save, a summary.
* 💰 What a pet wears adds to its work bonus (game/pet_tiers.bonus_bp): BONUS_BP of each worn piece's rank (the bed
  not: it stays home), LUX_BONUS more for a luxury piece, SET_BONUS for a whole set; at most BONUS_MAX. The day's cap
  stays the pet's rank's.
* ✨ The look: each piece glows in its rank's colour, the sum of the worn ranks gives a cute aura (cute_level), a whole
  set its own effect (public/js/v4/pet-art.js).

State `journey['petw']` (absent until first used; older builds keep unknown journey keys, and their pets keep their
old `w` and `own`, so a rollback loses nothing it had). Until then get() reads the old accessories as rank D items
(_from_old), and _ensure() stores exactly that.
    v    VERSION
    it   [{id 'o12', k piece id, r rank}] (≤ ITEM_MAX)
    on   {pet id: {slot: item id}}
    os   the next item number
    day  {d Vietnam day, f fusions}
    hot  [item id, unix time] the last luxury or SSS piece born (the street's ticker: game/pets.py)
    lg   [pet id] 🌟 legendaries that kept their own breed (game/pet_tiers.py _fuse `breed`)
    gm   {gear id: 0…4} the premium model of a gear (game/pet_tiers.py GMODELS_X; the gear itself says model 0)
"""
from __future__ import annotations

import datetime
import re

from . import pet_wardrobe_content as W

KEY = 'petw'
VERSION = 1
BLOCK_KEYS = frozenset({'v', 'it', 'on', 'os', 'day', 'hot', 'lg', 'gm'})
OPT_KEYS = frozenset({'mo'})                        # ✨ mo: a thần thú offer waiting for an answer (2.4.59)
MYTH_BP = {4: 2500, 5: 3000, 6: 4000}               # per 10 000, a fusion that reaches S / SS / SSS+ (never shown)
OID_RE = re.compile(r'o[0-9]{1,7}')
RANKS = ('D', 'C', 'B', 'A', 'S', 'SS', 'SSS')
TOP = len(RANKS) - 1
SHOP_RANKS = 2                                     # D and C
C_MULT = 4
FUSE_BP = (6000, 4500, 3000, 1500, 600, 300)       # per 10 000, D→C … SS→SSS (never shown)
FUSE_FEE = (200, 1_000, 5_000, 40_000, 300_000, 3_000_000)
LUX_FROM = 3                                       # a fusion of rank A or more …
LUX_BP = 1000                                      # … may turn into the slot's luxury piece
BONUS_BP = (0, 50, 100, 150, 200, 300, 500)        # per worn piece (per 10 000 of the earning)
LUX_BONUS = 100
SET_BONUS = 100
BONUS_MAX = 2500
ITEM_MAX = 150
BUY_QTY_MAX = 20                                   # 🛍️ owner 21/10 "trang phục cũng thế": one purchase of one piece × rank (and the room)
CUTE_AT = (6, 15, 24)                              # the worn ranks' sum for cute aura 1, 2, 3
AUTO_MAX = 50                                      # 🤖 the fusions one Ghép tự động makes at most
COMMANDS = ('jr_pet_wbuy', 'jr_pet_wwear', 'jr_pet_wfuse', 'jr_pet_wfuse_auto', 'jr_pet_wdrop', 'jr_pet_morph')
VN = datetime.timezone(datetime.timedelta(hours=7))


def _pt():
    from . import pets
    return pets


def _need(ok, msg, code='invalid_action'):
    from .engine import need
    need(ok, msg, code)


def _int(v, lo=0, hi=10**12) -> bool:
    return type(v) is int and lo <= v <= hi


def roll(n: int) -> int:
    from . import pet_tiers
    return pet_tiers.roll(n)


def vn_day() -> int:
    from . import pet_tiers
    return pet_tiers.vn_day()


def vn_date() -> str:
    return datetime.datetime.fromtimestamp(_pt().now(), VN).date().isoformat()


def on_sale(it: dict, date: str | None = None) -> bool:
    if it.get('lux'):
        return False
    sale = it.get('sale')
    if not sale:
        return True
    d = date or vn_date()
    return sale[0] <= d <= sale[1]


def price(it: dict, r: int) -> int:
    return it['price'] * (C_MULT if r == 1 else 1)


def name(i: dict) -> str:
    it = W.ITEM[i['k']]
    return f'{it["emoji"]} {it["name"]} {RANKS[i["r"]]}'


# ---------------------------------------------------------------- state
def _pet_ids(s: dict) -> set:
    from . import pet_tiers
    return {p['id'] for p in pet_tiers.all_pets(s)}


def _from_old(s: dict) -> dict:
    """The block an older save starts with: each old accessory owned (pets' `own`) a rank D item, worn where it was."""
    from . import pet_tiers, pets_content as C
    b = _pt().get(s)
    out = dict(v=VERSION, it=[], on={}, os=1, day=dict(d=0, f=0), hot=None, lg=[], gm={})
    if not b:
        return out
    free = {}
    for k, n in b['own'].items():
        if k in C.ACC and k in W.ITEM:
            for _ in range(min(int(n), ITEM_MAX - len(out['it']))):
                i = dict(id=f'o{out["os"]}', k=k, r=0)
                out['os'] += 1
                out['it'].append(i)
                free.setdefault(k, []).append(i['id'])
    for p in pet_tiers.all_pets(s):
        for slot, k in (p.get('w') or {}).items():
            if slot in W.SLOT_IDS and free.get(k):
                out['on'].setdefault(p['id'], {})[slot] = free[k].pop(0)
    return out


def stored(s: dict) -> dict | None:
    """The block as saved, or None (nothing made from the old accessories)."""
    j = s.get('journey') if isinstance(s, dict) else None
    x = j.get(KEY) if isinstance(j, dict) else None
    return x if isinstance(x, dict) else None


def get(s: dict) -> dict:
    """The wardrobe (read only): the stored block, or what the old accessories make."""
    j = s.get('journey')
    x = j.get(KEY) if isinstance(j, dict) else None
    return x if isinstance(x, dict) else _from_old(s)


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = _from_old(s)
    x = j[KEY]
    _tidy(s, x)
    return x


def _tidy(s: dict, x: dict) -> None:
    """Pets gone (a fusion, the grandparents' list trimmed): what they wore is free again."""
    live = _pet_ids(s)
    for pid in [pid for pid in x['on'] if pid not in live or not x['on'][pid]]:
        x['on'].pop(pid)
    x['lg'] = [pid for pid in x['lg'] if pid in live]
    if 'mo' in x and x['mo']['p'] not in live:
        x.pop('mo')


def set_legend(s: dict, pid: str) -> None:
    x = _ensure(s)
    if pid not in x['lg']:
        x['lg'].append(pid)


def set_model(s: dict, gid: str, m: int) -> None:
    x = _ensure(s)
    x['gm'][gid] = m
    tidy_models(s)


def myth_offer(s: dict, pet: dict, rank: int) -> dict | None:
    """✨ Owner 19/10: a fusion that reaches S or more may bring a thần thú (kỳ lân, khủng long …): the game picks which,
    the player only keeps the pet as it is or lets it turn into that one (jr_pet_morph). Hidden odds (MYTH_BP)."""
    from . import pets_content as C
    bp = MYTH_BP.get(min(rank, TOP), 0)
    pool = [b for b in C.MYTH if b != pet['b']]
    if not bp or not pool or roll(10000) >= bp:
        return None
    b = pool[roll(len(pool))]
    o = dict(p=pet['id'], b=b, c=roll(len(C.BREEDS[b]['coats'])))
    _ensure(s)['mo'] = o
    return dict(o, name=C.BREEDS[b]['name'])


def _morph(s: dict, x: dict, p: dict) -> dict:
    from . import pet_tiers, pets_content as C
    pt = _pt()
    pt._keys(p, {'take'}, {'take'})
    _need(p['take'] in (True, False), 'Thông tin không hợp lệ.')
    o = x.get('mo')
    _need(isinstance(o, dict), 'Không có thần thú nào đang chờ.', 'gone')
    rows, pet, where = pet_tiers._where(s, o['p'])
    x.pop('mo')
    _need(pet is not None, 'Bé này không còn ở bên bạn.', 'not_owned')
    br = C.BREEDS[o['b']]
    if not p['take']:
        return dict(message=f'💛 {pet["n"]} vẫn là {C.BREEDS[pet["b"]]["name"]} như cũ. {br["name"]} bay đi tìm chủ khác rồi.', morph=None)
    if C.BREEDS[pet['b']].get('fuse') == 'legend':
        set_legend(s, pet['id'])   # a 🌟 Linh Khuyển / Mèo Thần Tài stays legendary in its new shape
    old = C.BREEDS[pet['b']]['name']
    pet['b'], pet['c'] = o['b'], o['c']
    return dict(message=f'✨ {pet["n"]} đã hóa thành {br["name"]}! Hạng, tên, đồ và linh kiện vẫn giữ nguyên (trước là {old}).',
                morph=dict(pet=pet['id'], breed=o['b']))


def tidy_models(s: dict) -> None:
    """Premium models of gear no longer in the bag are forgotten."""
    x = stored(s)
    if not x:
        return
    from . import pet_tiers
    px = pet_tiers.get(s)
    have = {g['id'] for g in px['gear']} if px else set()
    for gid in [g for g in x['gm'] if g not in have]:
        x['gm'].pop(gid)


def _today(x: dict) -> dict:
    d = vn_day()
    if x['day']['d'] != d:
        x['day'] = dict(d=d, f=0)
    return x['day']


def wearer(x: dict, oid: str):
    return next((pid for pid, w in x['on'].items() if oid in w.values()), None)


def worn(s: dict, p: dict) -> dict:
    """{slot: item} pet `p` wears (read only)."""
    x = get(s)
    items = {i['id']: i for i in x['it']}
    w = x['on'].get(p['id']) or {}
    return {slot: items[oid] for slot, oid in w.items() if oid in items}


def full_sets(wear: dict) -> list:
    """The sets worn whole: every slot a set has pieces for wears one of them (Bộ Đám cưới: vest or the dress)."""
    out = []
    for st in W.SETS:
        slots = {W.ITEM[k]['slot'] for k in st['pieces']}
        if slots and all(slot in wear and W.ITEM[wear[slot]['k']].get('set') == st['id'] for slot in slots):
            out.append(st['id'])
    return out


def bonus_bp(s: dict, p: dict) -> int:
    """What pet `p`'s outfit adds to its work bonus, per 10 000 (the bed not)."""
    wear = worn(s, p)
    bp = sum(BONUS_BP[i['r']] + (LUX_BONUS if W.ITEM[i['k']].get('lux') else 0) for slot, i in wear.items() if slot != 'bed')
    bp += SET_BONUS * len(full_sets(wear))
    return min(BONUS_MAX, bp)


def cute_level(wear: dict) -> int:
    n = sum(i['r'] + 1 for slot, i in wear.items() if slot != 'bed')
    return sum(1 for at in CUTE_AT if n >= at)


def look(s: dict, p: dict) -> dict:
    """What the art and the live street draw: a [piece ids], ar [their ranks] (bed last), o cute aura, st sets."""
    wear = worn(s, p)
    order = [slot for slot in W.SLOT_IDS if slot in wear]
    out = dict(a=[wear[slot]['k'] for slot in order], ar=[wear[slot]['r'] for slot in order])
    o = cute_level(wear)
    if o:
        out['o'] = o
    st = full_sets(wear)
    if st:
        out['st'] = st[0]
    return out


def walk_look(s: dict, p: dict) -> dict:
    """The look without the bed (it stays home): the street, the boards."""
    wear = {slot: i for slot, i in worn(s, p).items() if slot != 'bed'}
    order = [slot for slot in W.SLOT_IDS if slot in wear]
    out = dict(a=[wear[slot]['k'] for slot in order])
    if any(wear[slot]['r'] for slot in order):
        out['ar'] = [wear[slot]['r'] for slot in order]
    o = cute_level(wear)
    if o:
        out['o'] = o
    st = full_sets(wear)
    if st:
        out['st'] = st[0]
    return out


def pet_extra(s: dict, p: dict) -> dict:
    """What a pet's card shows: w {slot: piece}, wr {slot: rank}, wo cute aura, wst a whole set, wb the bonus (%)."""
    wear = worn(s, p)
    out = dict(w={slot: i['k'] for slot, i in wear.items()}, wr={slot: i['r'] for slot, i in wear.items()},
               wb=bonus_bp(s, p) / 100)
    o = cute_level(wear)
    if o:
        out['wo'] = o
    st = full_sets(wear)
    if st:
        out['wst'] = st[0]
    return out


def clean_ids(raw) -> list:
    """Piece ids read back from a board row: known, not a bed, at most five."""
    if not isinstance(raw, list):
        return []
    return [k for k in raw if isinstance(k, str) and k in W.ITEM and W.ITEM[k]['slot'] != 'bed'][:5]


def row_look(raw: dict) -> dict:
    """The look kept in a 💪 board row (game/pets.py _power_row acc), checked: a, ar, o, st, lg (a legendary)."""
    a = clean_ids(raw.get('a'))
    ar = raw.get('ar') if isinstance(raw.get('ar'), list) else []
    ar = [v if type(v) is int and 0 <= v <= TOP else 0 for v in ar[:len(a)]] + [0] * max(0, len(a) - len(ar))
    out = dict(a=a, ar=ar[:len(a)], lg=raw.get('lp') is True)
    if raw.get('o') in (1, 2, 3):
        out['o'] = raw['o']
    if raw.get('st') in W.SET:
        out['st'] = raw['st']
    return out


def best_rank(s: dict) -> tuple:
    """(the highest item rank owned, whether a luxury piece is owned): live/pet_rank.py keeps a walk's look within it."""
    x = get(s)
    return (max((i['r'] for i in x['it']), default=0), any(W.ITEM[i['k']].get('lux') for i in x['it']))


# ---------------------------------------------------------------- save
def validate(s: dict) -> None:
    from .engine import need
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    x = j[KEY]
    bad = 'Dữ liệu tủ đồ thú cưng không hợp lệ.'
    ok = lambda v: need(v, bad, 'invalid_save')
    ok(isinstance(x, dict) and BLOCK_KEYS <= set(x) <= BLOCK_KEYS | OPT_KEYS and x['v'] == VERSION and _int(x['os'], 1, 10**7))
    ok(isinstance(x['it'], list) and len(x['it']) <= ITEM_MAX)
    ids = set()
    for i in x['it']:
        ok(isinstance(i, dict) and set(i) == {'id', 'k', 'r'} and isinstance(i['id'], str) and OID_RE.fullmatch(i['id'])
           and int(i['id'][1:]) < x['os'] and i['k'] in W.ITEM and _int(i['r'], 0, TOP) and i['id'] not in ids)
        ids.add(i['id'])
    kind = {i['id']: W.ITEM[i['k']]['slot'] for i in x['it']}
    ok(isinstance(x['on'], dict) and len(x['on']) <= 128)
    seen = set()
    for pid, w in x['on'].items():
        ok(isinstance(pid, str) and _pt().PID_RE.fullmatch(pid) is not None and isinstance(w, dict))
        for slot, oid in w.items():
            ok(slot in W.SLOT_IDS and oid in kind and kind[oid] == slot and oid not in seen)
            seen.add(oid)
    ok(isinstance(x['day'], dict) and set(x['day']) == {'d', 'f'} and _int(x['day']['d'], 0, 10**7) and _int(x['day']['f'], 0, 10**9))
    ok(isinstance(x['lg'], list) and len(x['lg']) <= 128 and len(set(x['lg'])) == len(x['lg'])
       and all(isinstance(pid, str) and _pt().PID_RE.fullmatch(pid) is not None for pid in x['lg']))
    ok(isinstance(x['gm'], dict) and len(x['gm']) <= 64 and all(isinstance(g, str) and len(g) <= 12 and _int(m, 0, 4) for g, m in x['gm'].items()))
    if 'mo' in x:
        from . import pets_content as C
        o = x['mo']
        ok(isinstance(o, dict) and set(o) == {'p', 'b', 'c'} and isinstance(o['p'], str) and _pt().PID_RE.fullmatch(o['p']) is not None
           and o['b'] in C.MYTH and _int(o['c'], 0, len(C.BREEDS[o['b']]['coats']) - 1))
    ok(x['hot'] is None or (isinstance(x['hot'], list) and len(x['hot']) == 2 and isinstance(x['hot'][0], str)
                            and _int(x['hot'][1], 0, 10**11)))


# ---------------------------------------------------------------- commands
def _new(x: dict, k: str, r: int) -> dict:
    i = dict(id=f'o{x["os"]}', k=k, r=r)
    x['os'] += 1
    x['it'].append(i)
    return i


def _fmt(n: int) -> str:
    return f'{n:,}'.replace(',', '.')


def _fuse_three(s: dict, x: dict, three: list) -> tuple:
    """🔀 One fusion of three identical items (paid already), jr_pet_wfuse's own: the day's count, FUSE_BP of a success
    (the three go, worn ones taken off, one item a rank up; from A up LUX_BP of those the slot's luxury piece), a
    failure keeps the three. (the new item, luxury) or (None, False); the same rolls in the same order."""
    pt = _pt()
    d = _today(x)
    k, r0 = three[0]['k'], three[0]['r']
    it = W.ITEM[k]
    d['f'] = min(10**9, d['f'] + 1)
    if roll(10000) >= FUSE_BP[r0]:
        return None, False
    for i in three:
        for w in x['on'].values():
            for slot in [slot for slot, oid in w.items() if oid == i['id']]:
                w.pop(slot)
        x['it'].remove(i)
    r = r0 + 1
    lux = False
    if r0 >= LUX_FROM and not it.get('lux') and roll(10000) < LUX_BP:
        k, lux = W.LUX[it['slot']], True
    i = _new(x, k, r)
    _tidy(s, x)
    if lux or r == TOP:
        x['hot'] = [i['id'], int(pt.now())]
    return i, lux


_ORDER = {it['id']: n for n, it in enumerate(W.ITEMS)}


def triples(x: dict, scope: str = 'all', max_rank: int = TOP, keep_worn: bool = True) -> list:
    """🤖 What Ghép tự động may fuse now: [(k, r, the items in the order jr_pet_wfuse takes them)] for every piece × rank
    with three to use (worn ones left out when keep_worn, else last, as jr_pet_wfuse takes them) whose result is at
    most max_rank; the lowest rank first, then the catalogue's order."""
    groups: dict = {}
    for i in x['it']:
        if (scope == 'all' or i['k'] == scope) and i['r'] < min(max_rank, TOP):
            groups.setdefault((i['k'], i['r']), []).append(i)
    out = []
    for (k, r), its in groups.items():
        free = [i for i in its if wearer(x, i['id']) is None]
        use = free if keep_worn else free + [i for i in its if wearer(x, i['id']) is not None]
        if len(use) >= 3:
            out.append((k, r, use))
    out.sort(key=lambda g: (g[1], _ORDER[g[0]]))
    return out


def _auto(s: dict, x: dict, p: dict) -> dict:
    """🤖 Ghép tự động (owner 21/10 "ghép thú thì thêm chế độ ghép tự động cho áo quần nhé"): jr_pet_wfuse again and
    again, each time the lowest-rank triple left (a failure tries the same three again, as a player would), until none
    is left, the next fee would pass the budget or the money, or AUTO_MAX fusions; one charge of what they cost, one
    save. Nothing new is stored: the items are those a fusion makes, so an older build loads the save."""
    pt = _pt()
    pt._keys(p, {'scope', 'max_rank', 'keep_worn', 'budget', 'confirm'}, {'budget', 'confirm'})
    scope = p.get('scope', 'all')
    _need(scope == 'all' or (isinstance(scope, str) and scope in W.ITEM), 'Chọn một món hoặc tất cả nhé.')
    top = p.get('max_rank', TOP)
    _need(_int(top, 1, TOP), 'Hạng dừng không hợp lệ.')
    keep = p.get('keep_worn', True)
    _need(keep in (True, False), 'Thông tin không hợp lệ.')
    budget = p['budget']
    _need(_int(budget, 1, 10**12), 'Nhập số xu tối đa muốn tiêu nhé.')
    first = triples(x, scope, top, keep)
    _need(bool(first), 'Không còn ba món giống hệt nhau (cùng món, cùng hạng) để ghép tự động.'
          + (' Món đang mặc được giữ nguyên.' if keep else ''), 'not_owned')
    fee0 = FUSE_FEE[first[0][1]]
    _need(fee0 <= budget, f'Ngân sách chưa đủ cho lượt ghép đầu ({_fmt(fee0)} xu).', 'not_enough')
    why = pt._ready_why(s, fee0)
    _need(not why, why, 'not_enough')
    _need(p['confirm'] is True, f'Xác nhận ghép tự động, tiêu tối đa {_fmt(budget)} xu.')
    before = {i['id'] for i in x['it']}
    n = won = lux = spent = 0
    stop = 'done'
    while True:
        left = triples(x, scope, top, keep)
        if not left:
            break
        if n >= AUTO_MAX:
            stop = 'cap'
            break
        fee = FUSE_FEE[left[0][1]]
        if spent + fee > budget:
            stop = 'budget'
            break
        if pt._ready_why(s, spent + fee):
            stop = 'money'
            break
        spent += fee
        n += 1
        i, l = _fuse_three(s, x, left[0][2][:3])
        if i is not None:
            won += 1
            lux += l
    how = pt._pay(s, spent, f'Ghép tự động đồ thú cưng · {n} lượt')
    made = [dict(id=i['id'], k=i['k'], r=i['r']) for i in x['it'] if i['id'] not in before]
    used = len(before - {i['id'] for i in x['it']})
    msg = f'🤖 Ghép tự động {n} lượt: {won} thành công, {n - won} trượt.'
    if lux:
        msg += f' 💎 Ra {lux} món dòng sang!'
    msg += {'done': ' Hết bộ ba để ghép.', 'budget': ' Dừng vì chạm ngân sách.', 'money': ' Dừng vì hết tiền.',
            'cap': f' Mỗi lần tối đa {AUTO_MAX} lượt.'}[stop]
    return dict(message=f'{msg} ({how})', ok=won > 0,
                auto=dict(n=n, ok=won, lux=lux, spent=spent, stop=stop, used=used, made=made,
                          left=len(triples(x, scope, top, keep))))


def action(s: dict, name_: str, p: dict) -> dict:
    pt = _pt()
    _need(name_ in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    _need(isinstance(p, dict), 'Thông tin không hợp lệ.')
    if name_ == 'jr_pet_wbuy':
        # 🛍️ owner 21/10: qty (absent: 1, an older client) items of one piece and rank, each the item one purchase makes,
        # one charge of qty × the price; none bought if the wardrobe lacks room.
        pt._keys(p, {'id', 'rank', 'qty', 'confirm'}, {'id', 'confirm'})
        it = W.ITEM.get(p['id']) if isinstance(p['id'], str) else None
        _need(it is not None, 'Chọn một món trong tiệm nhé.')
        r = p.get('rank', 0)
        _need(_int(r, 0, SHOP_RANKS - 1), 'Tiệm chỉ bán hạng D và C. Hạng cao hơn thì ghép nhé.')
        qty = p.get('qty', 1)
        _need(_int(qty, 1, BUY_QTY_MAX), f'Mua từ 1 đến {BUY_QTY_MAX} món một lần nhé.')
        _need(not it.get('lux'), f'{it["name"]} không bán: chỉ có khi ghép đồ hạng A trở lên.', 'not_for_sale')
        _need(on_sale(it), f'{it["name"]} đã hết mùa bán.', 'not_for_sale')
        times = f' ×{qty}' if qty > 1 else ''
        _need(p['confirm'] is True, f'Xác nhận mua {it["name"]} hạng {RANKS[r]}{times}.')
        x = _ensure(s)
        _need(len(x['it']) < ITEM_MAX, f'Tủ đồ đã đủ {ITEM_MAX} món. Ghép hoặc bỏ bớt nhé.', 'limit')
        room = ITEM_MAX - len(x['it'])
        _need(qty <= room, f'Tủ đồ chỉ còn chỗ cho {room} món. Ghép hoặc bỏ bớt nhé.', 'limit')
        how = pt._pay(s, price(it, r) * qty, f'Đồ thú cưng · {it["name"]} {RANKS[r]}{times}')
        made = [_new(x, it['id'], r) for _ in range(qty)]
        out = dict(message=f'🛍️ Đã mua {name(made[0])}{times} ({how}).', item=made[0]['id'])
        if qty > 1:
            out['items'] = [i['id'] for i in made]
        return out
    x = _ensure(s)
    if name_ == 'jr_pet_morph':
        return _morph(s, x, p)
    if name_ == 'jr_pet_wwear':
        pt._keys(p, {'pet', 'slot', 'item'}, {'pet', 'slot'})
        from . import pet_tiers
        _need(p['slot'] in W.SLOT_IDS, 'Thông tin không hợp lệ.')
        rows, pet, where = pet_tiers._where(s, p['pet'])
        _need(pet is not None and where in ('home', 'ken'), 'Không thấy bé này.', 'not_owned')
        w = x['on'].setdefault(pet['id'], {})
        if p.get('item') is None:
            w.pop(p['slot'], None)
            _tidy(s, x)
            return dict(message=f'Đã tháo cho {pet["n"]}.')
        i = next((q for q in x['it'] if q['id'] == p['item']), None) if isinstance(p['item'], str) else None
        _need(i is not None, 'Không thấy món đồ này.', 'not_owned')
        it = W.ITEM[i['k']]
        _need(it['slot'] == p['slot'], 'Món này không mặc chỗ đó được.')
        other = wearer(x, i['id'])
        if other and other != pet['id']:
            x['on'][other] = {k: v for k, v in x['on'][other].items() if v != i['id']}
        w[p['slot']] = i['id']
        _tidy(s, x)
        return dict(message=f'{it["emoji"]} {pet["n"]} diện {it["name"].lower()}, xinh xỉu!')
    if name_ == 'jr_pet_wfuse':
        pt._keys(p, {'k', 'r', 'confirm'}, {'k', 'r', 'confirm'})
        _need(p['k'] in W.ITEM and _int(p['r'], 0, TOP), 'Chọn một món nhé.')
        _need(p['r'] < TOP, 'Hạng SSS là cao nhất rồi.', 'full')
        same = [i for i in x['it'] if i['k'] == p['k'] and i['r'] == p['r']]
        _need(len(same) >= 3, 'Cần ba món giống hệt nhau (cùng món, cùng hạng).', 'not_owned')
        _today(x)
        same.sort(key=lambda i: wearer(x, i['id']) is not None)   # the ones in the wardrobe first
        it = W.ITEM[p['k']]
        fee = FUSE_FEE[p['r']]
        _need(p['confirm'] is True, f'Xác nhận ghép ba {it["name"]} hạng {RANKS[p["r"]]} ({_fmt(fee)} xu).')
        how = pt._pay(s, fee, f'Ghép đồ thú cưng · {it["name"]} {RANKS[p["r"]]}')
        i, lux = _fuse_three(s, x, same[:3])
        if i is None:
            return dict(message=f'💨 Ghép trượt, ba món vẫn còn nguyên. ({how})', ok=False)
        msg = (f'💎 Ghép ra món DÒNG SANG: {name(i)}!' if lux else f'🎉 Ghép thành công: {name(i)}!')
        return dict(message=f'{msg} ({how})', ok=True, item=i['id'], lux=lux)
    if name_ == 'jr_pet_wfuse_auto':
        return _auto(s, x, p)
    if name_ == 'jr_pet_wdrop':
        pt._keys(p, {'k', 'r', 'confirm'}, {'k', 'r', 'confirm'})
        same = [i for i in x['it'] if i['k'] == p.get('k') and i['r'] == p.get('r')]
        _need(bool(same), 'Không thấy món đồ này.', 'not_owned')
        same.sort(key=lambda i: wearer(x, i['id']) is not None)
        i = same[0]
        _need(p['confirm'] is True, f'Bỏ {name(i)}?')
        for w in x['on'].values():
            for slot in [slot for slot, oid in w.items() if oid == i['id']]:
                w.pop(slot)
        x['it'].remove(i)
        _tidy(s, x)
        return dict(message=f'🗑️ Đã bỏ {name(i)}.')
    return dict(message='')


# ---------------------------------------------------------------- the old commands (a client from before 2.4.56)
def old_buy(s: dict, k: str, qty: int) -> str:
    """jr_pet_buy of an accessory: rank D items."""
    pt = _pt()
    it = W.ITEM[k]
    _need(on_sale(it), f'{it["name"]} đã hết mùa bán.', 'not_for_sale')
    x = _ensure(s)
    _need(len(x['it']) + qty <= ITEM_MAX, f'Tủ đồ đã đủ {ITEM_MAX} món.', 'limit')
    how = pt._pay(s, it['price'] * qty, f'Đồ thú cưng · {it["name"]}' + (f' ×{qty}' if qty > 1 else ''))
    for _ in range(qty):
        _new(x, k, 0)
    return how


def old_wear(s: dict, pet: dict, slot: str, k: str | None) -> None:
    """jr_pet_wear: the best free item of that piece (or none: take it off)."""
    x = _ensure(s)
    w = x['on'].setdefault(pet['id'], {})
    if k is None:
        w.pop(slot, None)
    else:
        free = [i for i in x['it'] if i['k'] == k and not wearer(x, i['id'])]
        _need(bool(free), f'{W.ITEM[k]["name"]} đang có bé khác dùng. Mua thêm một cái nhé.', 'not_owned')
        w[slot] = max(free, key=lambda i: i['r'])['id']
    _tidy(s, x)


# ---------------------------------------------------------------- views
def item_view(x: dict, i: dict) -> dict:
    return dict(id=i['id'], k=i['k'], r=i['r'], on=wearer(x, i['id']))


def public(s: dict) -> dict:
    x = get(s)
    d = x['day'] if x['day']['d'] == vn_day() else dict(d=0, f=0)
    return dict(it=[item_view(x, i) for i in x['it']], fuse_today=d['f'], mo=dict(x['mo']) if x.get('mo') else None)


def catalogue() -> dict:
    date = vn_date()
    return dict(slots=[dict(id=a, emoji=b, name=c) for a, b, c in W.SLOTS],
                items=[dict(it, sale=list(it['sale']) if it.get('sale') else None, on_sale=on_sale(it, date)) for it in W.ITEMS],
                sets=[dict(st) for st in W.SETS], ranks=list(RANKS), shop_ranks=SHOP_RANKS, c_mult=C_MULT,
                fee=list(FUSE_FEE), bonus=[b / 100 for b in BONUS_BP], lux_bonus=LUX_BONUS / 100, set_bonus=SET_BONUS / 100,
                bonus_max=BONUS_MAX / 100, limit=ITEM_MAX, cute_at=list(CUTE_AT), qty_max=BUY_QTY_MAX,
                auto_max=AUTO_MAX)
