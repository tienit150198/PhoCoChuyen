"""🧊 Tủ lạnh ở nhà: keep a little food at home and eat it when hungry (story mode).

Owner (03/10): "ở nhà mình cho phép người chơi đi vào luôn … tủ lạnh thì khi mua xong được phép mua để đồ ăn trong đó,
khi đói thì vào nhà mua đồ ăn trong đó cũng được, trọ hay ktx tương tự". The player walks around inside the place they
live in (public/js/v4/home-walk.js, in the room of public/js/v4/reno.js) and taps the fridge; this file is the fridge.

* Where there is a fridge: a Tủ lạnh (deco item `tu_lanh` or `tu_lanh_magnet`, bought in the Bày trí phòng shop) standing
  in the place you live in: a home you own, your spouse's, the rented room, Bà Tám's attic (each placed fridge holds
  FRIDGE_CAP things, at most FRIDGES_MAX counted). A fridge still in the bag (túi đồ) is not plugged in: set it up first.
  The dorm (Ký túc xá Hẻm 7) has no room for one (the bunk corner takes no floor furniture) but a shared fridge in the
  room, one shelf each: DORM_CAP things, no purchase.
* Đi chợ cất tủ (jr_fridge_buy {item}): one thing into the fridge, paid from the wallet (refused when the wallet does
  not hold the price: food never makes debt), while there is room.
* Ăn (jr_fridge_eat {item}): one from the fridge (already paid; hungry at home with an empty fridge: store one, then
  eat it, the owner's "vào nhà mua đồ ăn trong đó cũng được"). Eating follows the work day's Ăn thêm (game/needs.py
  jr_needs_snack): no bụng / tỉnh táo go up (at most 100); a food is refused when no bụng is already at needs.FULL_CAP,
  the coffee when tỉnh táo is at needs.WAKE_CAP; no tinh thần, no daily cap. Allowed in the work day and in the evening
  (counted towards tomorrow morning, like the dinner).
* Prices sit with the street's: a bánh bao or a coffee costs what Ăn thêm asks, a home-cooked hộp cơm a little more
  filling than a gói xôi for the same 5 xu. Nothing spoils.
* Sổ ví: one row a life day (kind 'living', which every build accepts), "🧊 Đồ ăn ở nhà · N món", updated in place.
* Moving house: the food goes along (the fridge goes to the bag with the other furniture, see game/deco.py); it waits
  until a fridge is there again. A smaller fridge than the food in it: eat first, no buying until there is room.

State (absent in older saves; created on the first purchase): journey['fridge'] = {v, items {food id: how many},
n (eaten in all), b (bought in all)}. An older build ignores the key (journey.validate allows extra keys) and answers
jr_fridge_* with 'unknown_action'; the view rides in deco.public()['fridge'] (a page loaded before ignores it).
"""
from __future__ import annotations

import re

from . import housing as hs
from . import needs as nd

VERSION = 1
KEYS = {'v', 'items', 'n', 'b'}
COMMANDS = ('jr_fridge_buy', 'jr_fridge_eat')
FRIDGES = ('tu_lanh', 'tu_lanh_magnet')   # deco_content.ITEMS that are a fridge
FRIDGE_CAP = 10                            # things one fridge holds
FRIDGES_MAX = 2                            # fridges counted in one place
DORM_CAP = 4                               # your shelf of the dorm's shared fridge
CAP_MAX = FRIDGE_CAP * FRIDGES_MAX
LABEL = '🧊 Đồ ăn ở nhà'

# id → what it is, its price (xu), no bụng / tỉnh táo added, the line when it is eaten. Ids are stored in saves:
# never rename or remove one.
FOODS = {
    'sua': dict(emoji='🥛', name='Hộp sữa tươi', price=2, full=10, wake=0, say='Sữa mát lạnh, uống một hơi hết hộp.'),
    'flan': dict(emoji='🍮', name='Bánh flan', price=2, full=8, wake=0, say='Bánh flan mềm mịn, caramen đắng nhẹ, ngon ghê.'),
    'trai_cay': dict(emoji='🍉', name='Hộp trái cây cắt sẵn', price=3, full=12, wake=0, say='Dưa hấu, xoài mát lạnh, ngọt lịm.'),
    'banh_bao': dict(emoji='🥟', name='Bánh bao nhân thịt', price=3, full=20, wake=0, say='Hâm lại nóng hổi, nhân thịt trứng cút thơm phức.'),
    'goi_cuon': dict(emoji='🥗', name='Gỏi cuốn tôm thịt', price=4, full=25, wake=0, say='Chấm tương đậu, rau sống giòn mát.'),
    'com_hop': dict(emoji='🍱', name='Hộp cơm thịt kho', price=5, full=40, wake=0, say='Hâm nóng hộp cơm thịt kho trứng, ăn ngon lành.'),
    'ca_phe': dict(emoji='🧋', name='Chai cà phê sữa', price=3, full=0, wake=15, say='Cà phê sữa đá mát lạnh, tỉnh hẳn người.'),
}

NO_FRIDGE = 'Chưa có tủ lạnh'
IN_BAG = 'Tủ lạnh còn trong túi đồ'
FULL = 'Tủ đầy rồi'
POOR = 'Chưa đủ xu'
EMPTY = 'Hết trong tủ'
TOO_FULL = 'Bụng no rồi'
AWAKE = 'Đang tỉnh rồi'


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _dc():
    from . import deco
    return deco


def _story(s: dict) -> bool:
    j = s.get('journey')
    return isinstance(j, dict) and bool(j.get('story'))


def get(s: dict) -> dict | None:
    j = s.get('journey')
    f = j.get('fridge') if isinstance(j, dict) else None
    return f if isinstance(f, dict) else None


def _ensure(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get('fridge'), dict):
        j['fridge'] = dict(v=VERSION, items={}, n=0, b=0)
    return j['fridge']


def stock(s: dict) -> dict:
    """{food id: how many} in the fridge (empty without one)."""
    f = get(s)
    return {k: v for k, v in f['items'].items() if k in FOODS} if f else {}


def used(s: dict) -> int:
    return sum(stock(s).values())


def spot(s: dict, L: dict | None = None) -> dict:
    """The fridge of the place you live in: {kind 'own' (yours) | 'dorm' (the shared one) | '', cap, why}."""
    place, kind = hs.where(hs.get(s))
    if place == 'rent' and kind == hs.DORM:
        return dict(kind='dorm', cap=DORM_CAP, why='')
    L = L or _dc().layout(s)
    count = sum(1 for u in L['pos'] if L['kinds'].get(u) in FRIDGES)
    if count:
        return dict(kind='own', cap=FRIDGE_CAP * min(FRIDGES_MAX, count), why='')
    bag = any(k in FRIDGES and u not in L['pos'] for u, k in L['kinds'].items())
    return dict(kind='', cap=0, why=IN_BAG if bag else NO_FRIDGE)


def _eat_why(n: dict, x: dict) -> str:
    if x['full'] and n['full'] >= nd.FULL_CAP:
        return TOO_FULL
    if not x['full'] and n['wake'] >= nd.WAKE_CAP:
        return AWAKE
    return ''


def _whys(s: dict, sp: dict, fid: str) -> tuple[str, str]:
    """(why it cannot go into the fridge, why it cannot be eaten now): '' = it can."""
    j = s['journey']
    x = FOODS[fid]
    wallet = int(j.get('wallet', 0))
    have = stock(s).get(fid, 0)
    if not sp['cap']:
        return sp['why'], sp['why']
    buy = FULL if used(s) >= sp['cap'] else POOR if wallet < x['price'] else ''
    eat = '' if have else EMPTY
    eat = eat or _eat_why(nd.get(s) or nd.initial(j['life_day']), x)
    return buy, eat


def _row(j: dict, price: int) -> None:
    """Pay `price` into today's row (one a life day, looked for among the day's last rows), else a new row."""
    for row in reversed(j['history'][-12:]):
        if not isinstance(row, dict) or row.get('day') != j['life_day']:
            break
        m = re.fullmatch(re.escape(LABEL) + r' · (\d{1,6}) món', str(row.get('label', '')))
        if row.get('kind') == 'living' and row.get('career') is None and m and abs(row['amount'] - price) <= 10**7:
            j['wallet'] -= price
            row['amount'] -= price
            row['label'] = f'{LABEL} · {int(m.group(1)) + 1} món'
            return
    _jr()._wallet(j, -price, 'living', f'{LABEL} · 1 món')


def _low(name: str) -> str:
    return name[:1].lower() + name[1:]


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    need(_story(s), 'Tủ lạnh ở nhà chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) == {'item'} and isinstance(p['item'], str) and p['item'] in FOODS, 'Chọn một món nhé.')
    j = s['journey']
    fid = p['item']
    x = FOODS[fid]
    sp = spot(s)
    need(sp['why'] != IN_BAG, 'Tủ lạnh còn nằm trong túi đồ. Bày tủ ra bếp rồi cất đồ ăn nhé.', 'no_fridge')
    need(sp['cap'], 'Chưa có tủ lạnh. Tủ lạnh có trong cửa hàng Bày trí phòng.', 'no_fridge')
    buy, eat = _whys(s, sp, fid)
    have = stock(s).get(fid, 0)
    shelf = 'ngăn tủ chung' if sp['kind'] == 'dorm' else 'tủ lạnh'
    if name == 'jr_fridge_buy':
        need(buy != FULL, f'{shelf[:1].upper() + shelf[1:]} đầy rồi ({used(s)}/{sp["cap"]} món). Ăn bớt rồi hãy mua thêm nhé.', 'full')
        need(not buy, f'Ví còn {max(0, j["wallet"])} xu, chưa đủ {x["price"]} xu.', 'not_enough')
        f = _ensure(s)
        _row(j, x['price'])
        f['items'][fid] = have + 1
        f['b'] = min(10**6, f['b'] + 1)
        return dict(message=f'{x["emoji"]} Cất {_low(x["name"])} vào {shelf} ({x["price"]} xu). Trong tủ: {used(s)}/{sp["cap"]} món.', effects=[])
    # jr_fridge_eat
    need(eat != EMPTY, f'Trong tủ hết {_low(x["name"])} rồi. Cất thêm một phần rồi ăn nhé.', 'empty')
    need(eat != TOO_FULL, 'Bụng no rồi, để dành trong tủ ăn sau nhé.', 'too_full')
    need(not eat, 'Đang tỉnh rồi, uống nữa tối khó ngủ đó.', 'too_full')
    n = nd.ensure(s)
    f = _ensure(s)
    if have > 1:
        f['items'][fid] = have - 1
    else:
        f['items'].pop(fid)
    f['n'] = min(10**6, f['n'] + 1)
    n['full'] = nd._clamp(n['full'] + x['full'])
    n['wake'] = nd._clamp(n['wake'] + x['wake'])
    gain = f'No bụng {n["full"]}.' if x['full'] else f'Tỉnh táo {n["wake"]}.'
    return dict(message=f'{x["emoji"]} {x["say"]} {gain}', effects=[])


def view(s: dict, L: dict | None = None) -> dict | None:
    """deco.public()['fridge'] (None outside story mode): {kind, cap, why} of the place you live in, plus, when there
    is a fridge, what is in it, no bụng / tỉnh táo and the food list. Kept small (it rides in every state answer):
    a food's buy / eat is the reason it is refused, '' when it can be done."""
    if not _story(s):
        return None
    j = s['journey']
    sp = spot(s, L)
    out = dict(kind=sp['kind'], cap=sp['cap'], why=sp['why'])
    if not sp['cap']:
        return out
    have = stock(s)
    n = nd.get(s) or nd.initial(j['life_day'])
    foods = []
    for k, x in FOODS.items():
        buy, eat = _whys(s, sp, k)
        foods.append(dict(id=k, emoji=x['emoji'], name=x['name'], price=x['price'], full=x['full'], wake=x['wake'], n=have.get(k, 0),
                          buy=buy, eat=eat))
    return dict(out, used=sum(have.values()), full=n['full'], wake=n['wake'], foods=foods)


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'fridge' not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu tủ lạnh không hợp lệ.'
    f = j['fridge']
    need(isinstance(f, dict) and set(f) == KEYS and f.get('v') == VERSION, bad, 'invalid_save')
    items = f['items']
    need(isinstance(items, dict) and set(items) <= set(FOODS), bad, 'invalid_save')
    for v in items.values():
        integer(v, 1, CAP_MAX)
    need(sum(items.values()) <= CAP_MAX, bad, 'invalid_save')
    integer(f['n'], 0, 10**6)
    integer(f['b'], 0, 10**6)
