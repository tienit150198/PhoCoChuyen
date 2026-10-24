"""🍳 Nấu cơm tối ở nhà: a small cooking game in the evening (story mode), feedback #485 "nấu ăn mỗi tối dạng game nấu ăn".

Where and when: the evening between closing the day and going to bed (game/needs.py: needs.day < journey.life_day and
no dinner chosen yet), in a home with a kitchen (a rented room or a home you own / share; Bà Tám cooks in the attic and
the dorm only has a kettle). Once an evening.

The game (public/js/v4/cook-night.js draws it; the server only scores what was done):
1. Chọn món: one of DISHES (Vietnamese home dishes, each with its ingredients, its fire and its seasonings).
2. Đi chợ: the ingredients are bought at Chợ sáng Mây from the wallet (refused when the wallet does not hold the price:
   food never makes debt). With a fridge at home (game/fridge.py spot) the eggs and greens already there take
   FRIDGE_OFF xu off.
3. Sơ chế: tap to wash and cut (drawn only).
4. Nấu: a flame needle sweeps 0–100; the player stops it. `heat` is scored against the dish's zone: inside 2 points,
   within NEAR of it 1, else 0 (raw or burnt).
5. Nêm: pick the seasonings from SPICES; the dish's exact set 2 points, one off 1, else 0.
6. Dọn mâm: the score → stars (4 points ★★★, 2–3 ★★, 0–1 ★).

Reward: no bụng + the dish's `full` × (70 + 15 × stars) % (at most 100), tinh thần + (stars − 1); eating with a spouse
(game/needs.py _spouse) +1 more from ★★. Tonight's dinner is then this meal (needs.meals: the home row becomes the
cooked tray with nothing more to eat, the paid ones are off), and the evening sheet goes on with the bedtime.

State (absent in older saves; created on the first dish): journey['cook'] = {v, day (the life day whose evening it
was), dish, stars, n (dishes cooked), best {dish: best stars}}. An older build ignores the key (journey.validate
allows extra keys) and answers jr_cook_* with 'unknown_action'.
Command (journey.action): jr_cook_done {dish, heat, spices}.
"""
from __future__ import annotations

from . import price_index as pi

VERSION = 1
KEYS = {'v', 'day', 'dish', 'stars', 'n', 'best'}
COMMANDS = ('jr_cook_done',)
NEAR = 10
FRIDGE_OFF = 1

SPICES = {
    'mam': dict(emoji='🐟', name='Nước mắm'),
    'duong': dict(emoji='🍬', name='Đường'),
    'muoi': dict(emoji='🧂', name='Muối'),
    'tieu': dict(emoji='⚫', name='Tiêu'),
    'ot': dict(emoji='🌶️', name='Ớt'),
    'me': dict(emoji='🟤', name='Me chua'),
}

# id → the dish. Ids are stored in saves: never rename or remove one. `heat`: the fire's good zone on the 0–100 needle;
# `fire`: how the recipe card says it; `prep`: the cutting board's taps (drawn only).
DISHES = {
    'trung': dict(emoji='🍳', name='Trứng chiên hành', price=2, full=30, minutes=15, heat=(35, 60), fire='Lửa vừa',
                  spices=('mam', 'tieu'), items=(('🥚', 'Trứng gà'), ('🧅', 'Hành lá')),
                  prep=('Đập trứng', 'Cắt hành'), say='Trứng vàng ươm, thơm mùi hành phi.'),
    'rau': dict(emoji='🥬', name='Rau muống xào tỏi', price=2, full=25, minutes=15, heat=(65, 90), fire='Lửa lớn, xào nhanh',
                spices=('muoi', 'duong'), items=(('🥬', 'Rau muống'), ('🧄', 'Tỏi')),
                prep=('Nhặt rau', 'Đập tỏi'), say='Rau xanh giòn, tỏi thơm lừng.'),
    'canh': dict(emoji='🍲', name='Canh chua cá', price=5, full=40, minutes=35, heat=(45, 70), fire='Sôi vừa',
                 spices=('me', 'duong', 'mam'), items=(('🐟', 'Cá lóc'), ('🍅', 'Cà chua'), ('🍍', 'Thơm'), ('🌱', 'Giá')),
                 prep=('Làm cá', 'Cắt cà chua', 'Cắt thơm'), say='Canh chua ngọt thanh, cá chín tới.'),
    'kho': dict(emoji='🥘', name='Thịt kho trứng', price=6, full=50, minutes=60, heat=(20, 45), fire='Lửa liu riu',
                spices=('mam', 'duong', 'tieu'), items=(('🥩', 'Thịt ba chỉ'), ('🥚', 'Trứng vịt'), ('🥥', 'Nước dừa')),
                prep=('Cắt thịt', 'Luộc trứng', 'Bóc trứng'), say='Thịt mềm, nước kho sánh màu cánh gián.'),
}
pi.index(DISHES, luxury=False)   # 💹 what a player pays (game/price_index.py; under 5 xu a price stays)

STARS = {1: 'Ăn được', 2: 'Ngon', 3: 'Ngon tuyệt'}
NO_KITCHEN = 'Chỗ ở chưa có bếp riêng'
NOT_EVENING = 'Khép ca xong mới tới giờ nấu'
ATE = 'Tối nay ăn rồi'
DONE = 'Tối nay nấu rồi'


def _core():
    from . import engine
    return engine


def _nd():
    from . import needs
    return needs


def _story(s: dict) -> bool:
    j = s.get('journey')
    return isinstance(j, dict) and bool(j.get('story'))


def get(s: dict) -> dict | None:
    j = s.get('journey')
    x = j.get('cook') if isinstance(j, dict) else None
    return x if isinstance(x, dict) else None


def tonight(s: dict) -> dict | None:
    """Tonight's cooked dish {dish, stars} (None: nothing cooked this evening)."""
    x, n = get(s), _nd().get(s)
    if not x or not n or n['day'] >= s['journey']['life_day'] or x['day'] != n['day']:
        return None
    return dict(dish=x['dish'], stars=x['stars'])


def _fridge(s: dict) -> bool:
    try:
        from . import fridge
        return bool(fridge.spot(s)['cap'])
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def cost(s: dict, did: str) -> int:
    return max(1, DISHES[did]['price'] - (FRIDGE_OFF if _fridge(s) else 0))


def why(s: dict) -> str:
    """Why the kitchen is closed now ('' = a dish can be cooked)."""
    nd = _nd()
    j = s['journey']
    n = nd.get(s)
    if tonight(s):
        return DONE
    if not n or n['day'] >= j['life_day']:
        return NOT_EVENING
    if n['eve']:
        return ATE
    if nd._where(s) not in ('rent', 'own'):
        return NO_KITCHEN
    return ''


def score(did: str, heat: int, spices) -> tuple[int, int, int]:
    """(heat points, seasoning points, stars) for what was done."""
    x = DISHES[did]
    lo, hi = x['heat']
    hp = 2 if lo <= heat <= hi else 1 if lo - NEAR <= heat <= hi + NEAR else 0
    off = len(set(spices) ^ set(x['spices']))
    sp = 2 if off == 0 else 1 if off == 1 else 0
    pts = hp + sp
    return hp, sp, 3 if pts >= 4 else 2 if pts >= 2 else 1


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    nd = _nd()
    need(_story(s), 'Nấu ăn ở nhà chỉ có trong hành trình.', 'locked')
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict) and set(p) == {'dish', 'heat', 'spices'} and p['dish'] in DISHES and type(p['heat']) is int
         and 0 <= p['heat'] <= 100 and isinstance(p['spices'], list) and len(p['spices']) <= len(SPICES)
         and all(isinstance(k, str) and k in SPICES for k in p['spices']) and len(set(p['spices'])) == len(p['spices']),
         'Chọn món, nấu rồi nêm nhé.')
    j = s['journey']
    did = p['dish']
    x = DISHES[did]
    if (tonight(s) or {}).get('dish') == did:
        return dict(message=f'{x["emoji"]} Tối nay nấu {x["name"].lower()} rồi.', effects=[])
    w = why(s)
    need(w != DONE, 'Tối nay nấu rồi. Mai lại vào bếp nhé.', 'already_done')
    need(w != NOT_EVENING, 'Khép ca xong, buổi tối mới vào bếp nấu nhé.', 'not_now')
    need(w != ATE, 'Tối nay ăn rồi. Mai lại vào bếp nhé.', 'already_done')
    need(not w, 'Chỗ ở này chưa có bếp riêng. Thuê phòng hoặc có nhà là nấu được.', 'no_kitchen')
    price = cost(s, did)
    need(int(j.get('wallet', 0)) >= price, f'Ví còn {max(0, int(j.get("wallet", 0)))} xu, chưa đủ {price} xu đi chợ.', 'not_enough')
    n = nd.ensure(s)
    hp, sp, stars = score(did, p['heat'], p['spices'])
    from . import journey as jr
    jr._wallet(j, -price, 'living', f'🍳 Đi chợ nấu: {x["name"]}'[:120])
    full = x['full'] * (70 + 15 * stars) // 100
    n['full'] = nd._clamp(n['full'] + full)
    spouse = nd._spouse(s)
    got = nd._spirit(s, stars - 1 + (1 if spouse and stars >= 2 else 0))
    c = get(s)
    if c is None:
        c = j['cook'] = dict(v=VERSION, day=n['day'], dish=did, stars=stars, n=0, best={})
    c.update(day=n['day'], dish=did, stars=stars, n=min(10**6, c['n'] + 1))
    c['best'][did] = max(stars, c['best'].get(did, 0))
    heat = 'lửa vừa chuẩn' if hp == 2 else 'lửa hơi lệch' if hp == 1 else ('hơi sống' if p['heat'] < x['heat'][0] else 'hơi cháy')
    salt = 'nêm vừa miệng' if sp == 2 else 'nêm thiếu chút' if sp == 1 else 'nêm chưa hợp'
    msg = f'{x["emoji"]} {x["name"]}: {"★" * stars}{"☆" * (3 - stars)} {STARS[stars]}! {heat.capitalize()}, {salt}. No bụng {n["full"]}.'
    if spouse:
        msg += f' Ăn cùng {spouse}' + (', được khen ngon.' if stars >= 2 else '.')
    if got:
        msg += f' Tinh thần +{got}.'
    return dict(message=msg, effects=[], cook=dict(dish=did, stars=stars, heat=hp, spices=sp, full=full, spirit=got, price=price))


def view(s: dict) -> dict | None:
    """The kitchen for the evening sheet (needs.public evening.cook): {ok, why, done, dishes, spices, spouse, fridge}."""
    if not _story(s):
        return None
    j = s['journey']
    w = why(s)
    t = tonight(s)
    wallet = int(j.get('wallet', 0))
    dishes = []
    for k, x in DISHES.items():
        price = cost(s, k)
        dishes.append(dict(id=k, emoji=x['emoji'], name=x['name'], price=price, full=x['full'], minutes=x['minutes'],
                           heat=list(x['heat']), fire=x['fire'], spices=list(x['spices']), items=[list(i) for i in x['items']],
                           prep=list(x['prep']), say=x['say'], ok=wallet >= price,
                           best=(get(s) or {}).get('best', {}).get(k, 0)))
    return dict(ok=not w, why=w, done=dict(t, name=DISHES[t['dish']]['name'], emoji=DISHES[t['dish']]['emoji'], word=STARS[t['stars']]) if t else None,
                dishes=dishes, spices=[dict(id=k, **v) for k, v in SPICES.items()], spouse=_nd()._spouse(s), fridge=_fridge(s),
                near=NEAR)


def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or 'cook' not in j:
        return
    e = _core()
    need, integer = e.need, e.integer
    bad = 'Dữ liệu nấu ăn không hợp lệ.'
    c = j['cook']
    need(isinstance(c, dict) and set(c) == KEYS and c.get('v') == VERSION, bad, 'invalid_save')
    integer(c['day'], 1, 10**6)
    need(c['day'] <= j.get('life_day', 1), bad, 'invalid_save')
    need(c['dish'] in DISHES, bad, 'invalid_save')
    integer(c['stars'], 1, 3)
    integer(c['n'], 1, 10**6)
    need(isinstance(c['best'], dict) and c['best'] and set(c['best']) <= set(DISHES), bad, 'invalid_save')
    for v in c['best'].values():
        integer(v, 1, 3)
