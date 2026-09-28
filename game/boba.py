"""Quầy trà sữa (milk_tea): a hands-on boba counter.

Stations: a cup stack (M/L), tea dispensers, syrup bottles, a 12-bin topping
tray, ice and sugar levels, a sealing machine, then serve. The server grades the
finished cup against the order. Customers wait in beats (turns), never in
wall-clock time. Daily modifiers, a regulars' notebook and counter surprises
with real trade-offs. Everything random is seeded from stable facts (day, task
id, turn) and stored once rolled. State lives lazily in
c['ext']['data']['boba'] so saves from earlier versions keep loading.
"""
from __future__ import annotations
import copy
import hashlib
import random

from . import extra_content as data
from . import consequences as cq

CAREER = 'milk_tea'
ING = data.INGREDIENT_INDEX
BASES = [x['id'] for x in data.INGREDIENTS if x['group'] == 'base']
FLAVORS = [x['id'] for x in data.INGREDIENTS if x['group'] == 'flavor']
TOPPINGS = [x['id'] for x in data.INGREDIENTS if x['group'] == 'topping']
BASE_PRICE = {'milk': 30, 'black': 25, 'matcha': 35, 'green': 28, 'oolong': 32, 'thai': 34}
FLAVOR_PRICE, TOPPING_PRICE, SIZE_L_PRICE = 6, 5, 7
SUGARS = (0, 30, 50, 70, 100)
ICES = ('none', 'little', 'normal', 'extra')
ICE_TEXT = {'none': 'không đá', 'little': 'ít đá', 'normal': 'đá vừa', 'extra': 'nhiều đá'}
CUP_START = {'M': 30, 'L': 20}
CUP_CAP = 120
CUP_PACK = dict(qty=20, cost=4)
MAX_TOPPINGS = 3
BEAT_ACTIONS = {'cup', 'add', 'ice', 'sugar', 'config', 'check', 'seal_start', 'seal', 'serve', 'discard', 'wipe', 'event'}
UNSAFE_MESS = 2
# Heat-sealer timing (seconds between "Ép nắp" and "Nhả"), measured on the server.
SEAL = dict(loose=0.8, good_lo=1.4, good_hi=2.6, burn=4.2, max=5.0)
SEAL_QUALITY = (None, 'perfect', 'ok', 'burnt')
APP_FEE_PCT = 20
APP_NAMES = [dict(id='app-maichi', name='Chị Mai Chi', kind='app', me='mình', emoji='📱'), dict(id='app-khiem', name='Ông Khiêm', kind='app', me='mình', emoji='📱'),
             dict(id='app-kiet', name='Tuấn Kiệt', kind='app', me='mình', emoji='📱'), dict(id='app-ngoc', name='Cô Ngọc', kind='app', me='mình', emoji='📱'),
             dict(id='app-duy', name='Anh Duy', kind='app', me='mình', emoji='📱')]

UPGRADES = [
    dict(id='bell', name='Chuông gọi món', emoji='🔔', level=2, price=60, text='Khách đang xếp hàng mất kiên nhẫn chậm một nửa.'),
    dict(id='pot', name='Nồi ủ trân châu', emoji='🍲', level=2, price=90, text='Trân châu nấu xong giữ được thêm một ngày.'),
    dict(id='fridge', name='Tủ mát topping', emoji='🧊', level=3, price=120, text='Siro và topping giữ thêm một ngày.'),
    dict(id='sealer', name='Máy dán nắp tự động', emoji='⚙️', level=4, price=140, text='Dán nắp không tốn nhịp; cúp điện vẫn dán được bằng pin dự phòng.'),
]
UPGRADE_INDEX = {u['id']: u for u in UPGRADES}

MODS = [
    dict(id='quiet', title='Sáng đầu tuần yên ả', emoji='🌤️', text='Khách thưa, ai cũng thong thả. Hợp để luyện tay.', extra=0),
    dict(id='students', title='Học sinh tan học', emoji='🎒', text='Đông học sinh: ly size L, trân châu gọi nhiều, khách nhỏ hơi sốt ruột.', extra=1, min_day=2),
    dict(id='heat', title='Trưa nắng gắt', emoji='☀️', text='Trời nóng: khách thích nhiều đá và vị trái cây, ly L bán chạy.', extra=1, min_day=2),
    dict(id='rain', title='Mưa chiều', emoji='🌧️', text='Mưa lất phất: khách ít hơn nhưng kiên nhẫn, hay gọi ít đá.', extra=-1, min_day=2),
    dict(id='office', title='Văn phòng đặt trà chiều', emoji='💼', text='Công ty gần quán hay đặt nhiều ly một lúc. Để ý đơn lớn.', extra=0, min_day=3),
    dict(id='market', title='Phiên chợ cuối tuần', emoji='🏮', text='Chợ đông: khách quen ghé nhiều, dễ có chuyện bất ngờ.', extra=1, min_day=3),
    dict(id='review', title='Có bạn làm video ghé phố', emoji='📱', text='Một vị khách đặc biệt có thể ghé. Làm chuẩn từng ly nhé.', extra=0, min_day=4),
]
MOD_INDEX = {m['id']: m for m in MODS}

WALKINS = [
    dict(id='na', name='Bé Na', kind='student', me='em', emoji='👧'), dict(id='ti', name='Tí', kind='student', me='em', emoji='👦'),
    dict(id='khoa', name='Khoa', kind='student', me='em', emoji='🧑‍🎓'), dict(id='hanh', name='Chị Hạnh', kind='office', me='chị', emoji='👩‍💼'),
    dict(id='tuan', name='Anh Tuấn', kind='office', me='anh', emoji='👨‍💼'), dict(id='sau', name='Ông Sáu', kind='elder', me='ông', emoji='👴'),
    dict(id='nam', name='Bà Năm', kind='elder', me='bà', emoji='👵'), dict(id='vy', name='Vy', kind='young', me='mình', emoji='👩'),
    dict(id='phong', name='Phong', kind='young', me='mình', emoji='🧑'), dict(id='ship', name='Anh giao hàng', kind='office', me='anh', emoji='🛵'),
]
WALKIN_INDEX = {w['id']: w for w in WALKINS}
REGULARS = {
    'milk_tea_npc_01': dict(kind='young', me='mình', usual=dict(base='matcha', flavor=None, toppings=['foam'], size='M', sugar=30, ice='little')),
    'milk_tea_npc_02': dict(kind='elder', me='bác', usual=dict(base='black', flavor=None, toppings=['q3'], size='M', sugar=100, ice='little')),
    'milk_tea_npc_03': dict(kind='young', me='mình', usual=dict(base='milk', flavor='strawberry', toppings=['pearls', 'popping'], size='L', sugar=50, ice='normal')),
}
FALLBACK = {'q3': 'jelly', 'pudding': 'jelly', 'white_pearl': 'pearls', 'aloe': 'jelly', 'cheese': 'foam', 'coconut': 'jelly',
            'red_bean': 'pearls', 'flan': 'popping', 'green': 'black', 'oolong': 'black', 'thai': 'milk', 'passion': 'peach'}


def opening(kind: str, me: str) -> str:
    return {'student': 'Chào ạ! Em gọi món nha.', 'office': f'Em ơi, {me} gọi món mang đi nhé.',
            'elder': f'Cháu ơi, {me} gọi ly nước nhé.', 'young': 'Chào bạn! Mình gọi món nhé.'}.get(kind, 'Chào bạn! Mình gọi món nhé.')


def _e():
    from . import engine
    return engine


def rng(*parts) -> random.Random:
    seed = int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16)
    return random.Random(seed)


# Counter skill ("tay nghề"): grows with cups actually handed over, not with other chores.
TIERS = (0, 4, 10, 18, 28, 40, 55, 72, 92)


def level(c: dict) -> int:
    raw = ((c.get('ext') or {}).get('data') or {}).get('boba') or {}
    total = raw.get('total', 0) if isinstance(raw, dict) else 0
    return sum(1 for x in TIERS if total >= x)


def next_tier(c: dict) -> int | None:
    lv = level(c)
    return TIERS[lv] if lv < len(TIERS) else None


def unlocked(c: dict, item: str) -> bool:
    return item in ING and ING[item].get('level', 1) <= level(c)


# ---------------------------------------------------------------- state
def fresh() -> dict:
    return dict(v=1, cups=dict(CUP_START), mess=0, upgrades=[], day=0, turn0=0, mod='quiet', quota=0, arrived=0,
                served=0, perfect=0, returned=0, walkouts=0, revenue=0, fines=0, bonus=0, total=0,
                event=None, events_today=0, last_event_beat=-99, today_kinds=[], ev_seq=0, ev_history=[],
                history=[], notebook={}, story=dict(step=0, day=0, choices=[]), sold_out=[], sealer_off=0, dome=False,
                promises=[], office=None)


def view(c: dict) -> dict:
    """Read-only merged state (never mutates the save)."""
    raw = ((c.get('ext') or {}).get('data') or {}).get('boba')
    out = fresh()
    if isinstance(raw, dict):
        out.update(copy.deepcopy(raw))
    return out


def state(c: dict) -> dict:
    d = c['ext']['data']
    b = d.get('boba')
    if not isinstance(b, dict):
        b = d['boba'] = fresh()
    for k, v in fresh().items():
        b.setdefault(k, copy.deepcopy(v))
    return b


def modifier(c: dict) -> dict:
    b = view(c)
    if b['day'] == c['day'] and b['mod'] in MOD_INDEX:
        return MOD_INDEX[b['mod']]
    return MOD_INDEX[roll_mod(c['day'])]


def roll_mod(day: int) -> str:
    if day <= 1:
        return 'quiet'
    pool = [m['id'] for m in MODS if m.get('min_day', 1) <= day]
    weights = [1 if m == 'quiet' else 3 for m in pool]
    return rng(CAREER, 'mod', day).choices(pool, weights)[0]


def beats(c: dict) -> int:
    return max(0, c['turn'] - view(c)['turn0'])


def clock(c: dict) -> str:
    b = view(c)
    span = max(24, (b['quota'] or 4) * 9)
    minutes = 8 * 60 + round(12 * 60 * min(1.0, beats(c) / span)) if c['open'] else 8 * 60
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def clock_minutes(c: dict) -> int:
    h, m = clock(c).split(':')
    return int(h) * 60 + int(m)


# ---------------------------------------------------------------- orders
def price(c: dict, needs: dict) -> int:
    prices = c['life']['prices']
    return (prices.get(needs['base'], BASE_PRICE[needs['base']]) + (FLAVOR_PRICE if needs.get('flavor') else 0)
            + TOPPING_PRICE * len(needs['toppings']) + (SIZE_L_PRICE if needs['size'] == 'L' else 0))


def _fit(item: str, tier: int) -> str:
    seen = set()
    while item in ING and ING[item].get('level', 1) > tier and item not in seen:
        seen.add(item)
        item = FALLBACK.get(item, item)
    return item


def gen_needs(tid: str, tier: int, mod: str, avoid: list, kind: str) -> dict:
    r = rng(CAREER, 'order', tid, tier, mod)
    ok = lambda x: ING[x].get('level', 1) <= tier and x not in avoid
    bases = [x for x in BASES if ok(x)] or ['milk']
    flavors = [x for x in FLAVORS if ok(x)]
    tops = [x for x in TOPPINGS if ok(x)]
    base = r.choice(bases)
    flavor_p = 0.25 + (0.15 if tier >= 3 else 0) + (0.3 if mod == 'heat' else 0)
    flavor = r.choice(flavors) if flavors and r.random() < flavor_p else None
    counts = [0, 1, 1, 1] if tier <= 1 else [0, 1, 1, 2] if tier <= 3 else [1, 1, 2, 2, 3]
    n = min(len(tops), r.choice(counts))
    toppings = []
    if n and kind == 'student' and 'pearls' in tops:
        toppings.append('pearls')
    while len(toppings) < n:
        x = r.choice(tops)
        if x not in toppings:
            toppings.append(x)
    size_p = 0.35 + (0.3 if mod in ('students', 'heat') else 0) - (0.15 if kind == 'elder' else 0)
    size = 'L' if r.random() < size_p else 'M'
    sugar = r.choices(SUGARS, [2, 3, 4, 2, 3 if kind != 'elder' else 5])[0]
    ice_w = {'heat': [1, 2, 3, 5], 'rain': [3, 5, 2, 0]}.get(mod, [2, 3, 4, 2])
    ice = r.choices(ICES, ice_w)[0]
    return dict(base=base, flavor=flavor, toppings=toppings, size=size, sugar=sugar, ice=ice)


def fit_usual(usual: dict, tier: int) -> dict:
    n = copy.deepcopy(usual)
    n['base'] = _fit(n['base'], tier)
    if n['flavor']:
        n['flavor'] = _fit(n['flavor'], tier)
    tops = []
    for x in n['toppings']:
        x = _fit(x, tier)
        if x not in tops:
            tops.append(x)
    n['toppings'] = tops
    return n


def apply_changes(needs: dict, changes: list) -> dict:
    n = copy.deepcopy(needs)
    for ch in changes or []:
        if 'set' in ch:
            n[ch['set']] = ch['to']
        elif 'swap' in ch:
            n['toppings'] = [ch['to'] if x == ch['swap'] else x for x in n['toppings']]
            n['toppings'] = list(dict.fromkeys(n['toppings']))
        elif 'add' in ch and ch['add'] not in n['toppings']:
            n['toppings'].append(ch['add'])
        elif 'drop' in ch:
            n['toppings'] = [x for x in n['toppings'] if x != ch['drop']]
    return n


def derive(t: dict) -> dict:
    src = t.get('src') or {}
    if 'fixed' in src:
        base = src['fixed']
    else:
        base = gen_needs(t['id'], src.get('tier', 1), src.get('mod', ''), src.get('avoid', []), speech_kind(t))
    return apply_changes(base, t.get('changes', []))


def new_cup() -> dict:
    return dict(placed=False, size='M', items=[], sugar=None, ice=None, sealed=False, checked=False, cost=0, dome=False, seal_t=None, seal_q=None)


def now() -> float:
    from .careers import kit
    return kit.now()


def low(name: str) -> str:
    return name[:1].lower() + name[1:]


def task_fields(day: int, slot: int) -> dict:
    """Deterministic parts of a milk-tea task (engine validation replays the npc)."""
    n = (day - 1) * 3 + slot
    regular = slot == 0 or rng(CAREER, 'who', day, slot).random() < (0.5 if day <= 2 else 0.35)
    npc = f'{CAREER}_npc_{n % 3 + 1:02d}'
    walkin = None
    if not regular:
        w = WALKINS[rng(CAREER, 'walkin', day, slot).randrange(len(WALKINS))]
        walkin = dict(id=w['id'], name=w['name'], kind=w['kind'], me=w['me'], emoji=w['emoji'])
    tid = f'{CAREER}-{day:04d}-{slot:02d}'
    src = dict(fixed=fit_usual(REGULARS[npc]['usual'], 1)) if regular else dict(tier=1, mod='', avoid=[])
    t = dict(id=tid, npc=npc, walkin=walkin, src=src, changes=[], usual=False, beats=0,
             discount=0, vip=False, office=False, combo=False, group=None, app=None, cup=new_cup(), stage='order', quoted_price=None)
    label(t)
    t['needs'] = derive(t)
    t.pop('id')
    return t


def label(t: dict) -> None:
    """Title and greeting follow the customer actually standing at the counter."""
    kind = speech_kind(t)
    name = customer_name(t) if t.get('walkin') else data.PEOPLE[CAREER][int(t['npc'][-2:]) - 1][0]
    if t.get('app'):
        t['title'] = f"Đơn app {t['app']['code']} · {name}"
        t['opening'] = 'Tài xế sẽ ghé lấy đơn. Pha theo phiếu in từ máy nhé.'
        return
    if t.get('walkin'):
        t['title'] = name + ' ghé quầy'
    else:
        t['title'] = 'Khách quen: ' + name
    if t.get('group'):
        t['title'] += f" · ly {t['group']['i']}/{t['group']['n']}"
    t['opening'] = opening(kind, pronoun(t))


def pronoun(t: dict) -> str:
    if t.get('walkin'):
        return t['walkin'].get('me') or 'mình'
    return REGULARS.get(t['npc'], {}).get('me', 'mình')


def setup_task(s: dict, c: dict, t: dict, fixed: dict | None = None) -> None:
    """Roll the real order once, with today's level, modifier and notebook."""
    b = state(c)
    lv = level(c)
    mod = modifier(c)['id']
    t.setdefault('changes', [])
    if fixed:
        t['src'] = dict(fixed=copy.deepcopy(fixed))
    elif not t.get('walkin') and t['npc'] in REGULARS:
        book = b['notebook'].get(t['npc'])
        if book and lv >= 2 and rng(CAREER, 'usual', t['id']).random() < 0.7:
            t['src'] = dict(fixed=copy.deepcopy(book['usual']))
            t['usual'] = True
        elif book:
            t['src'] = dict(tier=lv, mod=mod, avoid=sorted(b['sold_out']))
        else:
            t['src'] = dict(fixed=fit_usual(REGULARS[t['npc']]['usual'], lv))
    else:
        t['src'] = dict(tier=lv, mod=mod, avoid=sorted(b['sold_out']))
    t['needs'] = derive(t)
    t['quoted_price'] = price(c, t['needs'])


def customer_name(t: dict) -> str:
    if t.get('walkin'):
        return t['walkin']['name']
    return _e().NPC_INDEX.get(t['npc'], {}).get('display_name', 'Khách')


def speech_kind(t: dict) -> str:
    if t.get('walkin'):
        return 'young' if t['walkin']['kind'] == 'app' else t['walkin']['kind']
    return REGULARS.get(t['npc'], {}).get('kind', 'young')


def order_text(t: dict) -> str:
    n = t['needs']
    kind = speech_kind(t)
    if t.get('usual'):
        return {'elder': f'Như mọi khi nha cháu! Cháu nhớ ly của {pronoun(t)} chứ?', 'young': 'Như mọi khi nhé! Bạn nhớ ly của mình không?'}.get(kind, 'Như mọi khi nha!')
    body = cup_text(n)
    if t.get('app'):
        return f"Phiếu app {t['app']['code']}: 1 ly {body}."
    me = pronoun(t)
    g = t.get('group')
    if g:
        lead = {'elder': f"Cháu ơi, cho {me} {g['n']} ly, ly {g['i']} là ", 'student': f"Cho em {g['n']} ly, ly {g['i']} là ",
                'office': f"Em ơi, {me} lấy {g['n']} ly, ly {g['i']} là ", 'young': f"Cho mình {g['n']} ly, ly {g['i']} là "}[kind]
    else:
        lead = {'elder': f'Cháu ơi, cho {me} 1 ly ', 'student': 'Cho em 1 ly ', 'office': f'Em ơi, {me} lấy 1 ly ', 'young': 'Cho mình 1 ly '}[kind]
    tail = {'elder': ' nha.', 'student': ' nha!', 'office': ', mang đi nhé.', 'young': ' nhé!'}[kind]
    return lead + body + tail


def cup_text(n: dict) -> str:
    parts = [f"{low(ING[n['base']]['name'])} size {n['size']}"]
    if n['flavor']:
        parts.append('vị ' + low(ING[n['flavor']]['name']))
    parts.append(', '.join(low(ING[x]['name']) for x in n['toppings']) or 'không topping')
    return ', '.join(parts) + f", {n['sugar']}% đường và {ICE_TEXT[n['ice']]}"


# ---------------------------------------------------------------- stock
def stock(c: dict) -> dict:
    return {k: sum(l['qty'] for l in c['life']['pantry'] if l['item'] == k and l['expires'] >= c['day']) for k in ING}


def _use(c: dict, item: str) -> int:
    e = _e()
    e.need(stock(c)[item] > 0, 'Hết ' + ING[item]['name'] + '. Mở Kho để chuẩn bị thêm một mẻ nhé.')
    lot = min((l for l in c['life']['pantry'] if l['item'] == item and l['expires'] >= c['day'] and l['qty'] > 0), key=lambda l: (l['expires'], l['received']))
    lot['qty'] -= 1
    return lot['unit_cost']


def shelf_life(c: dict, item: str) -> int:
    b = view(c)
    life = ING[item]['life']
    if 'fridge' in b['upgrades'] and ING[item]['group'] in ('topping', 'flavor'):
        life += 1
    if 'pot' in b['upgrades'] and item in ('pearls', 'white_pearl'):
        life += 1
    return life


def add_lot(s: dict, c: dict, item: str, qty: int, unit_cost: int, note: str = '') -> None:
    from . import experiences as life
    c['life']['pantry'].append(dict(id=life._id(c, 'batch'), item=item, qty=qty, unit_cost=unit_cost,
                                    expires=c['day'] + shelf_life(c, item) - 1, received=c['day']))


def warnings(c: dict) -> list[dict]:
    st = stock(c)
    b = view(c)
    out = []
    tops = [x for x in ('pearls', 'white_pearl') if unlocked(c, x)]
    if any(st[x] == 0 for x in tops):
        out.append(dict(id='pearls', text='Chưa nấu trân châu', where='stock'))
    empty = [ING[x]['name'] for x in BASES if unlocked(c, x) and st[x] == 0]
    if empty:
        out.append(dict(id='base', text='Hết trà nền: ' + ', '.join(empty), where='stock'))
    low = [k for k, v in b['cups'].items() if v < 5]
    if low:
        out.append(dict(id='cups', text='Sắp hết ly ' + '/'.join(low), where='stock'))
    if b['mess'] >= UNSAFE_MESS:
        out.append(dict(id='mess', text='Quầy còn vệt trà đổ', where='counter'))
    return out


# ---------------------------------------------------------------- day hooks
def on_start(s: dict, c: dict) -> None:
    b = state(c)
    if b['day'] == c['day'] and b['turn0']:
        return
    lv = level(c)
    mod = MOD_INDEX[roll_mod(c['day'])]
    b.update(day=c['day'], turn0=c['turn'], mod=mod['id'], served=0, perfect=0, returned=0, walkouts=0, revenue=0, fines=0, bonus=0,
             events_today=0, last_event_beat=-99, today_kinds=[], sold_out=[], sealer_off=0, dome=False, office=None)
    active = [t for t in c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled')]
    b['arrived'] = len(active)
    base = 2 if c['life'].get('mode') == 'calm' else 4 if c['life'].get('mode') == 'festival' else 3
    b['quota'] = max(len(active), base + min(4, lv - 1) + mod['extra'])
    e = _e()
    # Promises from yesterday (a supplier who owes portions, a student who owes coins).
    keep = []
    for pr in b['promises']:
        if pr['day'] > c['day']:
            keep.append(pr)
            continue
        if pr['kind'] == 'portions' and pr.get('_honest'):
            add_lot(s, c, pr['item'], pr['qty'], 0)
            e.log(s, c, 'stock', f"Bình mang bù {pr['qty']} phần {ING[pr['item']]['name']} giao thiếu hôm trước.", 'milk_tea_npc_05', pr['ref'])
            e.add_feed(s, c, 'milk_tea_npc_05', f"Hôm qua giao thiếu {pr['qty']} phần, sáng nay mình mang bù rồi nha. Cảm ơn quán đã tin mình!", pr['ref'], kind='story')
        elif pr['kind'] == 'portions':
            e.log(s, c, 'stock', 'Phần giao thiếu hôm trước không được mang bù. Lần sau nên đếm trước khi ký.', 'milk_tea_npc_05', pr['ref'])
        elif pr['kind'] == 'coins' and pr.get('_honest'):
            e.money(s, c, pr['qty'], 'Khách trả tiền còn nợ hôm trước', pr['ref'], category='revenue')
            e.add_feed(s, c, 'milk_tea_npc_01', 'Hôm qua em thiếu tiền lẻ, quán vẫn cho em ly trà. Hôm nay em ghé trả rồi nha, cảm ơn nhiều 🥹', pr['ref'], kind='story')
        elif pr['kind'] == 'coins':
            e.log(s, c, 'promise', 'Bạn học sinh hôm trước chưa ghé trả tiền. Chuyện nhỏ, quán vẫn vui.', ref=pr['ref'])
    b['promises'] = keep[-10:]
    # Keep a short queue at the counter; more guests arrive as cups go out.
    for t in active:
        t.setdefault('changes', [])
        if t.get('quoted_price') is None:
            setup_task(s, c, t)
    _top_up(s, c, b)


def _top_up(s: dict, c: dict, b: dict, room: int = 3) -> list[dict]:
    new = []
    lv = level(c)
    mod = modifier(c)['id']
    while True:
        live = [t for t in c['tasks'] if t['status'] not in ('completed', 'referred', 'cancelled') and not t.get('deferred')]
        counter = [t for t in live if not t.get('app')]
        apps = [t for t in live if t.get('app')]
        if b['arrived'] >= b['quota']:
            break
        r = rng(CAREER, 'arrive', c['day'], b['arrived'])
        roll = r.random()
        app_p = (0.5 if mod == 'rain' else 0.25) if lv >= 2 and c['life'].get('mode') != 'calm' else 0
        if roll < app_p and len(apps) < 2:
            t = spawn(s, c, app=True)
        elif len({(t.get('group') or {}).get('id', t['id']) for t in counter}) >= room:
            break
        elif lv >= 2 and r.random() < (0.35 if mod in ('students', 'office') else 0.2):
            made = spawn_group(s, c, 3 if lv >= 4 and r.random() < 0.4 else 2)
            t = made[0] if made else None
            new += made[1:]
        else:
            t = spawn(s, c)
        if not t:
            break
        new.append(t)
    return new


def _busy(c: dict) -> set:
    """Who is already waiting at the counter (walk-in id or regular npc)."""
    return {(x.get('walkin') or {}).get('id') or x['npc'] for x in c['tasks']
            if x['status'] not in ('completed', 'referred', 'cancelled') and not x.get('app')}


def spawn_group(s: dict, c: dict, n: int, walkin: dict | None = None, count_quota: bool = True, patience: int | None = None) -> list[dict]:
    """One customer, several cups: sibling tasks share a group id and a guest."""
    slots = [int(t['id'].split('-')[-1]) for t in c['tasks'] if t['day'] == c['day']]
    first = max(slots, default=-1) + 1
    n = min(n, 12 - first)
    if n < 2:
        return [x for x in [spawn(s, c, walkin=walkin, count_quota=count_quota, patience=patience)] if x]
    if walkin is None:
        busy = _busy(c)
        pool = [w for w in WALKINS if w['kind'] in ('student', 'office', 'young') and w['id'] not in busy] or [w for w in WALKINS if w['kind'] in ('student', 'office', 'young')]
        w = pool[rng(CAREER, 'group', c['day'], first).randrange(len(pool))]
        walkin = dict(id=w['id'], name=w['name'], kind=w['kind'], me=w['me'], emoji=w['emoji'])
    gid = f"g{c['day']}-{first:02d}"
    made = []
    for i in range(n):
        t = spawn(s, c, walkin=walkin, count_quota=count_quota and i == 0, patience=patience, group=dict(id=gid, n=n, i=i + 1))
        if t:
            made.append(t)
    return made


def spawn(s: dict, c: dict, fixed: dict | None = None, patience: int | None = None, walkin: dict | None = None,
          count_quota: bool = True, group: dict | None = None, app: bool = False) -> dict | None:
    from .content import make_task
    b = state(c)
    slots = [int(t['id'].split('-')[-1]) for t in c['tasks'] if t['day'] == c['day']]
    slot = max(slots, default=-1) + 1
    if slot >= 12:
        return None
    t = make_task(CAREER, c['day'], slot, c['turn'])
    if not walkin and not app:
        # The same person never stands in the queue twice: re-pick a free walk-in.
        busy = _busy(c)
        if ((t.get('walkin') or {}).get('id') or t['npc']) in busy:
            pool = [w for w in WALKINS if w['id'] not in busy]
            if pool:
                w = pool[rng(CAREER, 'again', c['day'], slot).randrange(len(pool))]
                walkin = dict(id=w['id'], name=w['name'], kind=w['kind'], me=w['me'], emoji=w['emoji'])
    if app:
        r = rng(CAREER, 'app', c['day'], slot)
        span = 30 + (6 if 'bell' in b['upgrades'] else 0)
        walkin = APP_NAMES[r.randrange(len(APP_NAMES))]
        t['app'] = dict(code=f'#{r.randint(1000, 9999)}', deadline=c['turn'] + span, span=span)
        t['known'] = True
        t['status'] = 'understood'
    if group:
        t['group'] = dict(group)
    if walkin:
        t['walkin'] = dict(walkin)
    if walkin or group or app:
        label(t)
    if patience:
        t['patience'] = patience
    setup_task(s, c, t, fixed=fixed)
    c['tasks'].append(t)
    if count_quota:
        b['arrived'] += 1
    if not c.get('active_task'):
        c['active_task'] = t['id']
    return t


def on_close(s: dict, c: dict) -> dict:
    b = state(c)
    ev = b.get('event')
    if ev and ev['stage'] == 'open':
        if ev['kind'] == 'inspection':
            _resolve(s, c, b, ev, 'open')
        b['event'] = None
    elif ev:
        b['event'] = None
    for t in c['tasks']:
        if t['status'] not in ('completed', 'referred', 'cancelled') and t.get('cup', {}).get('placed') and not t['cup']['items']:
            t['cup'] = new_cup()
    summary = dict(day=c['day'], served=b['served'], perfect=b['perfect'], returned=b['returned'], walkouts=b['walkouts'],
                   revenue=b['revenue'], fines=b['fines'], bonus=b['bonus'], events=b['events_today'], modifier=b['mod'],
                   level=level(c))
    b['history'] = (b['history'] + [summary])[-14:]
    b['turn0'] = 0
    return summary


# ---------------------------------------------------------------- patience
def rate(c: dict) -> int:
    if c['life'].get('mode') == 'calm':
        return 0
    mod = modifier(c)['id']
    if mod == 'rain' or mod == 'quiet':
        return 1
    return 1 + (1 if mod == 'students' else 0) + (1 if level(c) >= 5 else 0)


def _beat(s: dict, c: dict, active_id: str | None) -> list[str]:
    b = state(c)
    r = rate(c)
    notes = []
    if not r:
        return notes
    half = 'bell' in b['upgrades']
    active = next((t for t in c['tasks'] if t['id'] == active_id), None)
    gid = ((active or {}).get('group') or {}).get('id')
    for t in c['tasks']:
        if t['career'] != CAREER or t['status'] in ('completed', 'referred', 'cancelled') or t.get('deferred'):
            continue
        if t.get('app'):
            if c['turn'] > t['app']['deadline'] + 10 and not t['cup']['sealed']:
                notes.append(_app_cancel(s, c, t))
            continue
        if t['id'] != active_id and gid and (t.get('group') or {}).get('id') == gid:
            continue
        if t['id'] == active_id:
            t['beats'] = t.get('beats', 0) + 1
            par = 8 + len(t['needs']['toppings']) + (1 if t['needs'].get('flavor') else 0)
            loss = (1 if t['beats'] > par else 0) + (1 if b['mess'] >= 3 else 0)
        else:
            loss = r if not half or c['turn'] % 2 == 0 else 0
        if loss:
            t['patience'] = max(25, t.get('patience', 100) - loss)
        waiting = t['id'] != active_id and not t['cup']['placed'] and not t['cup']['items']
        if waiting and t.get('patience', 100) <= 25 and t['status'] not in ('completed', 'referred', 'cancelled'):
            notes.append(_walkout(s, c, t))
    return notes


def _app_cancel(s: dict, c: dict, t: dict) -> str:
    e = _e()
    b = state(c)
    t['status'] = 'cancelled'
    t['walked'] = True
    t['completed_turn'] = c['turn']
    b['walkouts'] += 1
    e.metric(c, 'walkouts')
    if t['cup']['placed'] and not t['cup']['items']:
        b['cups'][t['cup']['size']] += 1
        t['cup'] = new_cup()
    post = e.add_feed(s, c, t['npc'], 'Đặt trà trên app mà chờ mãi tài xế không lấy được đơn, đành hủy 😢', t['id'], 2, 'review')
    post['author'] = customer_name(t)
    e.log(s, c, 'walkout', f"Đơn app {t['app']['code']} bị hủy vì quá giờ lấy.", t['npc'], t['id'])
    e.next_active(c)
    _top_up(s, c, b)
    return f"Đơn app {t['app']['code']} quá giờ nên tài xế đã hủy."


def _walkout(s: dict, c: dict, t: dict) -> str:
    e = _e()
    b = state(c)
    gid = (t.get('group') or {}).get('id')
    for x in [t] + [x for x in c['tasks'] if gid and x is not t and (x.get('group') or {}).get('id') == gid]:
        if x['status'] in ('completed', 'referred', 'cancelled'):
            continue
        x['status'] = 'cancelled'
        x['walked'] = True
        x['completed_turn'] = c['turn']
        if x['cup']['items']:
            _waste_cup(c, x, 'Khách về trước khi nhận ly')
        elif x['cup']['placed']:
            b['cups'][x['cup']['size']] += 1
            x['cup'] = new_cup()
    b['walkouts'] += 1
    e.metric(c, 'walkouts')
    name = customer_name(t)
    text = {'student': 'Đợi lâu quá em phải đi học thêm rồi, hôm khác em ghé lại 😢', 'office': 'Hết giờ nghỉ trưa rồi, mình đi trước nha. Quán đông quá.',
            'elder': 'Bác đợi hơi lâu nên về trước, mai bác ghé.', 'young': 'Đợi lâu quá nên mình về trước, hôm khác ghé lại nha 😢'}[speech_kind(t)]
    post = e.add_feed(s, c, t['npc'], text, t['id'], 2, 'review')
    post['author'] = name
    e.log(s, c, 'walkout', name + ' đã rời hàng vì chờ quá lâu.', t['npc'], t['id'])
    e.next_active(c)
    _top_up(s, c, b)
    return name + ' đợi lâu quá nên đã về.'


# ---------------------------------------------------------------- actions
def _task(c: dict, p: dict) -> dict:
    e = _e()
    t = e.current_task(c, p.get('task'))
    e.need(t['career'] == CAREER, 'Sai nghề công việc.')
    t.setdefault('changes', [])
    t.setdefault('beats', 0)
    t.setdefault('discount', 0)
    cup = t['cup']
    cup.setdefault('placed', bool(cup['items']))
    cup.setdefault('dome', False)
    if t.get('quoted_price') is None:
        t['quoted_price'] = price(c, t['needs'])
    return t


def handle(s: dict, c: dict, action: str, p: dict) -> dict:
    e = _e()
    need = e.need
    name = action[4:]
    b = state(c)
    if name == 'prepare':
        return _prepare(s, c, p)
    if name == 'cups':
        return _buy_cups(s, c, p)
    if name == 'upgrade':
        return _upgrade(s, c, p)
    if name == 'event_ok':
        ev = b.get('event')
        need(ev and ev['stage'] == 'done', 'Không có kết quả nào đang chờ xác nhận.')
        b['event'] = None
        return dict(message='Quầy trở lại nhịp bình thường.')
    need(c['open'], 'Mở cửa quán trước khi pha nhé.')
    need(name in BEAT_ACTIONS, 'Thao tác pha chế không hợp lệ.')
    _expire_moot(c, b)
    active = None
    if name == 'wipe':
        need(b['mess'] > 0, 'Quầy đang sạch bong rồi.')
        b['mess'] = 0
        r = dict(message='Đã lau sạch quầy. Khách nhìn vào thấy yên tâm hơn.')
    elif name == 'event':
        r = _answer(s, c, b, p)
    else:
        t = _task(c, p)
        active = t['id']
        r = _station(s, c, b, t, name, p)
    notes = []
    if not r.pop('_free', False):
        c['turn'] += 1
        notes = _beat(s, c, active or c.get('active_task'))
    if r.pop('_arrivals', False):
        arrived = _top_up(s, c, b)
        if arrived:
            notes.append('Có khách mới tới quầy: ' + ', '.join(customer_name(t) for t in arrived) + '.')
    _maybe_event(s, c, b)
    if notes:
        r['message'] = r.get('message', '') + ' ' + ' '.join(notes)
    return r


def _prepare(s: dict, c: dict, p: dict) -> dict:
    e = _e()
    need = e.need
    item = p.get('item')
    need(item in ING, 'Không có nguyên liệu này.')
    need(unlocked(c, item), f"{ING[item]['name']} mở ở cấp {ING[item].get('level', 1)}. Phục vụ thêm vài ly nhé.")
    qty = e.integer(p.get('qty'), 1, 20)
    need(p.get('confirm') is True, 'Xác nhận chi phí trước khi nhập.')
    need(stock(c)[item] + qty <= 60, 'Kho chứa tối đa 60 phần mỗi loại.')
    ing = ING[item]
    cost = qty * ing['cost']
    e.money(s, c, -cost, 'Chuẩn bị ' + ing['name'], category='stock')
    add_lot(s, c, item, qty, ing['cost'])
    verb = 'nấu' if item in ('pearls', 'white_pearl') else 'nhập'
    return dict(message=f"Đã {verb} {qty} phần {ing['name']}. Dùng đến hết ngày {c['day'] + shelf_life(c, item) - 1}.")


def _buy_cups(s: dict, c: dict, p: dict) -> dict:
    e = _e()
    b = state(c)
    size = p.get('size')
    e.need(size in ('M', 'L'), 'Cỡ ly không hợp lệ.')
    e.need(p.get('confirm') is True, 'Xác nhận chi phí trước khi nhập ly.')
    e.need(b['cups'][size] + CUP_PACK['qty'] <= CUP_CAP, f'Chồng ly {size} đã đầy.')
    e.money(s, c, -CUP_PACK['cost'], f'Nhập {CUP_PACK["qty"]} ly {size}', category='materials')
    b['cups'][size] += CUP_PACK['qty']
    return dict(message=f'Đã xếp thêm {CUP_PACK["qty"]} ly size {size} lên chồng ly.')


def _upgrade(s: dict, c: dict, p: dict) -> dict:
    e = _e()
    b = state(c)
    u = UPGRADE_INDEX.get(p.get('id'))
    e.need(u, 'Không có nâng cấp này.')
    e.need(u['id'] not in b['upgrades'], 'Quầy đã có ' + u['name'].lower() + '.')
    e.need(level(c) >= u['level'], f"Cần cấp {u['level']} để lắp {u['name'].lower()}.")
    e.need(p.get('confirm') is True, 'Xác nhận chi phí trước khi lắp.')
    e.money(s, c, -u['price'], 'Mua ' + u['name'], 'boba-' + u['id'], category='upgrade')
    b['upgrades'].append(u['id'])
    return dict(message=u['name'] + ' đã được lắp ở quầy.', celebrate=True)


def _station(s: dict, c: dict, b: dict, t: dict, name: str, p: dict) -> dict:
    e = _e()
    need = e.need
    cup = t['cup']
    need(t['known'], 'Nghe khách gọi món trước đã nhé.')
    ev = b.get('event')
    if ev and ev['stage'] == 'open' and ev.get('task') == t['id'] and ev['kind'] in ('change_mind', 'short_money'):
        need(name not in ('serve',), 'Khách đang nói thêm với bạn. Trả lời khách trước khi trao ly nhé.')
    if name == 'cup':
        size = p.get('size')
        need(size in ('M', 'L'), 'Chỉ có ly M hoặc L.')
        need(not cup['items'], 'Ly đã có trà. Muốn đổi cỡ thì làm lại ly nhé.')
        if cup['placed'] and cup['size'] == size:
            return dict(message=f'Ly {size} đã nằm sẵn trên quầy.', _free=True)
        need(b['cups'][size] > 0, f'Hết ly {size}. Mở Kho để xếp thêm ly.')
        if cup['placed']:
            b['cups'][cup['size']] += 1
        b['cups'][size] -= 1
        cup.update(placed=True, size=size, checked=False)
        return dict(message=f'Đặt một ly {size} lên quầy.')
    if name == 'config':
        # Legacy one-shot form: size + sugar + ice.
        size, sugar, ice = p.get('size'), p.get('sugar'), p.get('ice')
        need(size in ('M', 'L') and type(sugar) is int and sugar in SUGARS and ice in ICES, 'Cỡ, đường hoặc đá không hợp lệ.')
        need(not cup['sealed'], 'Ly đã đóng nắp.')
        if not cup['placed'] or cup['size'] != size:
            need(not cup['items'], 'Ly đã có trà. Muốn đổi cỡ thì làm lại ly nhé.')
            need(b['cups'][size] > 0, f'Hết ly {size}. Mở Kho để xếp thêm ly.')
            if cup['placed']:
                b['cups'][cup['size']] += 1
            b['cups'][size] -= 1
            cup.update(placed=True, size=size)
        cup.update(sugar=sugar, ice=ice, checked=False)
        return dict(message='Đã chỉnh cỡ, đường và đá.')
    if name == 'add':
        item = p.get('item')
        need(item in ING, 'Nguyên liệu không tồn tại.')
        need(unlocked(c, item), f"{ING[item]['name']} mở ở cấp {ING[item].get('level', 1)}.")
        need(cup['placed'], 'Lấy một ly từ chồng ly trước nhé.')
        need(not cup['sealed'], 'Ly đã dán nắp. Muốn đổi thì làm lại ly.')
        need(item not in cup['items'], ING[item]['name'] + ' đã có trong ly.')
        group = ING[item]['group']
        have = [k for k in cup['items'] if ING[k]['group'] == group]
        limit = {'base': 1, 'flavor': 1, 'topping': MAX_TOPPINGS}[group]
        need(len(have) < limit, {'base': 'Ly chỉ nhận một loại trà nền.', 'flavor': 'Ly chỉ nhận một loại siro.', 'topping': f'Ly nhận tối đa {MAX_TOPPINGS} topping.'}[group])
        if group != 'base':
            need(any(ING[k]['group'] == 'base' for k in cup['items']), 'Rót trà nền trước đã nhé.')
        cost = _use(c, item)
        cup['items'].append(item)
        cup['cost'] += cost
        cup['checked'] = False
        verb = {'base': 'Rót', 'flavor': 'Thêm siro', 'topping': 'Múc'}[group]
        return dict(message=f"{verb} {ING[item]['name'].lower() if group != 'base' else ING[item]['name']}.")
    if name == 'ice':
        lv = p.get('level')
        need(lv in ICES, 'Mức đá không hợp lệ.')
        need(cup['placed'] and not cup['sealed'], 'Cần một ly đang mở để thêm đá.')
        cup['ice'] = lv
        cup['checked'] = False
        return dict(message='Đá: ' + ICE_TEXT[lv] + '.')
    if name == 'sugar':
        lv = p.get('level')
        need(type(lv) is int and lv in SUGARS, 'Mức đường không hợp lệ.')
        need(cup['placed'] and not cup['sealed'], 'Cần một ly đang mở để thêm đường.')
        cup['sugar'] = lv
        cup['checked'] = False
        return dict(message=f'Đường: {lv}%.')
    if name == 'check':
        need(cup['placed'] and cup['items'], 'Ly còn trống.')
        ok = not _diff(cup, t['needs'])
        if ok:
            cup['checked'] = True
            return dict(message='Ly đúng phiếu gọi món. Sẵn sàng dán nắp.')
        cup['checked'] = False
        t['mistakes'] += 1
        return dict(message='Ly chưa khớp phiếu: soi lại trà, siro, topping, cỡ, đường và đá.')
    if name in ('seal_start', 'seal'):
        need(cup['placed'] and any(ING[k]['group'] == 'base' for k in cup['items']), 'Ly chưa có trà nền.')
        need(not cup['sealed'], 'Ly đã dán nắp rồi.')
        need(cup['sugar'] is not None, 'Chưa chọn mức đường.')
        need(cup['ice'] is not None, 'Chưa chọn mức đá.')
        cut = b['sealer_off'] > c['turn'] and 'sealer' not in b['upgrades']
        if name == 'seal_start':
            need(not cut, 'Máy dán nắp đang tạm ngưng vì cúp điện.')
            need('sealer' not in b['upgrades'], 'Máy dán nắp tự động tự ép đúng lực, chỉ cần bấm dán.')
            cup['seal_t'] = round(now(), 3)
            return dict(message='Máy đang ép nhiệt… nhả tay khi kim vào vùng xanh.', _free=True)
        dome = False
        quality = 'ok'
        if cut:
            need(b['dome'], 'Máy dán nắp đang tạm ngưng vì cúp điện. Làm ly khác hoặc chờ một chút.')
            e.money(s, c, -1, 'Nắp cầu thay màng dán', t['id'], category='materials')
            dome = True
        elif 'sealer' in b['upgrades']:
            quality = 'perfect'
        elif cup.get('seal_t') is not None:
            held = max(0.0, now() - cup['seal_t'])
            cup['seal_t'] = None
            if held < SEAL['loose']:
                return dict(message='Nhả tay sớm quá, màng chưa dính. Ép lại nhé.')
            quality = 'perfect' if SEAL['good_lo'] <= held <= SEAL['good_hi'] else 'burnt' if held > SEAL['burn'] else 'ok'
        cup.update(sealed=True, dome=dome, seal_q=quality, seal_t=None)
        text = {'perfect': 'Tách! Màng nắp căng bóng, kín đều — hoàn hảo.', 'ok': 'Máy dán nắp kêu “tách” — ly đã kín.',
                'burnt': 'Ép lâu quá, màng nắp hơi cháy xém. Vẫn kín, nhưng khách sẽ để ý.'}[quality]
        r = dict(message='Nắp cầu đã đậy chặt.' if dome else text, seal=quality)
        if 'sealer' in b['upgrades']:
            r['_free'] = True
        return r
    if name == 'discard':
        need(p.get('confirm') is True, 'Xác nhận đổ ly làm lại; nguyên liệu đã dùng không hoàn kho.')
        need(cup['placed'] or cup['items'], 'Chưa có ly nào để làm lại.')
        _waste_cup(c, t, 'Làm lại ly')
        t['mistakes'] += 1
        return dict(message='Đã đổ ly và lấy lại từ đầu. Nguyên liệu đã dùng được ghi hao hụt.')
    if name == 'serve':
        need(p.get('confirm') is True, 'Xác nhận trao ly và thu tiền.')
        need(cup['sealed'], 'Dán nắp trước khi trao ly nhé.')
        return _serve(s, c, b, t)
    raise e.GameError('Thao tác pha chế không hợp lệ.')


def _waste_cup(c: dict, t: dict, reason: str) -> None:
    x = c['life']
    value = t['cup']['cost']
    x['day_waste'] += value
    x['waste'].append(dict(day=c['day'], item='cup', qty=1, value=value, reason=reason))
    x['waste'] = x['waste'][-120:]
    t['cup'] = new_cup()


def _diff(cup: dict, n: dict) -> list[str]:
    """Differences between a cup and an order. Critical ones come first."""
    base = next((k for k in cup['items'] if ING[k]['group'] == 'base'), None)
    flavor = next((k for k in cup['items'] if ING[k]['group'] == 'flavor'), None)
    tops = {k for k in cup['items'] if ING[k]['group'] == 'topping'}
    out = []
    if base != n['base']:
        out.append('base')
    if cup['size'] != n['size']:
        out.append('size')
    if flavor != n['flavor']:
        out.append('flavor')
    if tops != set(n['toppings']):
        out.append('toppings')
    if cup['sugar'] != n['sugar']:
        out.append('sugar')
    if cup['ice'] != n['ice']:
        out.append('ice')
    return out


CRITICAL = ('base', 'size', 'flavor', 'toppings')


def _complaint(t: dict, cup: dict, issue: str) -> str:
    n = t['needs']
    kind = speech_kind(t)
    me = {'elder': 'bác', 'student': 'em', 'office': 'mình', 'young': 'mình'}[kind]
    if issue == 'base':
        got = next((ING[k]['name'].lower() for k in cup['items'] if ING[k]['group'] == 'base'), 'trà')
        return f"Ơ, {me} gọi {ING[n['base']]['name'].lower()} mà, ly này là {got}."
    if issue == 'size':
        return f"{me.capitalize()} gọi size {n['size']} cơ, ly này size {cup['size']}."
    if issue == 'flavor':
        return f"Vị này không phải {ING[n['flavor']]['name'].lower()} {me} dặn." if n['flavor'] else f"{me.capitalize()} đâu có gọi siro trái cây."
    tops = {k for k in cup['items'] if ING[k]['group'] == 'topping'}
    missing = [ING[x]['name'].lower() for x in n['toppings'] if x not in tops]
    extra = [ING[x]['name'].lower() for x in tops if x not in n['toppings']]
    if missing:
        return f"Thiếu {', '.join(missing)} rồi."
    return f"{me.capitalize()} đâu có gọi {', '.join(extra)}."


def _serve(s: dict, c: dict, b: dict, t: dict) -> dict:
    e = _e()
    cup = t['cup']
    issues = _diff(cup, t['needs'])
    critical = [x for x in issues if x in CRITICAL]
    name = customer_name(t)
    if critical:
        said = _complaint(t, cup, critical[0])
        # Waiting for a remake is a small slip of its own: the review remembers it.
        cq.slip(t, 'returned', 1, f'{said} Phải chờ làm lại ly.', 'phải làm lại ly')
        t['remade'] = True
        _waste_cup(c, t, 'Khách trả ly')
        t['mistakes'] += 1
        t['patience'] = max(25, t.get('patience', 100) - 12)
        b['returned'] += 1
        b['mess'] = min(9, b['mess'] + 1)
        return dict(message=f"{name} trả ly: “{said}” Làm lại ly mới nhé.", correct=False)
    if cup.get('seal_q') == 'burnt':
        issues.append('seal')
    late = bool(t.get('app')) and c['turn'] > t['app']['deadline']
    if late:
        issues.append('late')
    _slips(t, cup, issues)
    if issues and not t.get('remade') and not t.get('app') and cq.decide(c, t, remake=True) == 'remake':
        # A strict customer hands a clearly wrong cup back: new cup, same order.
        r = cq.react(s, c, t, 0, remake=True, who=name)
        worst = max((x for x in cq.slips(t) if x['code'] != 'returned'), key=lambda x: x['sev'])
        cq.downgrade(t, 'returned', f"{worst['text']} Phải trả ly bắt làm lại.", 'phải làm lại ly')
        _waste_cup(c, t, 'Khách trả ly')
        t['mistakes'] += 1
        t['patience'] = max(25, t.get('patience', 100) - 8)
        b['returned'] += 1
        return dict(message=f"{name} trả ly: “{r['line']}” Pha lại ly mới nhé.", correct=False, reaction='remake')
    gid = (t.get('group') or {}).get('id')
    siblings = [x for x in c['tasks'] if gid and x is not t and (x.get('group') or {}).get('id') == gid]
    rest = [x for x in siblings if x['status'] not in ('completed', 'referred', 'cancelled')]
    if gid and not rest:
        # The whole order is judged once, when the last cup goes out.
        t['mistakes'] += sum(x['mistakes'] for x in siblings if x['status'] == 'completed')
    t['mistakes'] += len(issues)
    fee = round(t['quoted_price'] * APP_FEE_PCT / 100) if t.get('app') else 0
    reward = max(0, t['quoted_price'] - t.get('discount', 0) - fee)
    said = cq.react(s, c, t, reward, who=name)
    reward = said['pay']
    c['life']['consumed_cost'] += cup['cost']
    words = {'sugar': 'độ ngọt', 'ice': 'lượng đá', 'seal': 'nắp dán', 'late': 'giờ giao'}
    note = 'Đúng từng lớp: trà, topping, đường và đá.' if not issues else 'Ly được nhận, nhưng ' + ' và '.join(words[x] for x in issues) + ' chưa như ý.'
    e.task_done(s, c, t, reward, f'Đã nhận ly {low(ING[t["needs"]["base"]]["name"])} từ quầy. {note}')
    post = next((f for f in c['feed'] if f.get('source') == t['id'] and f.get('kind') == 'review'), None)
    if post and rest:
        # One customer, one review: earlier cups of a group wait for the last one.
        c['feed'].remove(post)
        e.metric(c, 'reviews_' + str(post['stars']), -1)
        post = None
    if rest:
        c['active_task'] = rest[0]['id']
    if post and t.get('walkin'):
        post['author'] = name
    if t.get('walkin'):
        # A passer-by does not come back as one of the regulars tomorrow.
        c['pending'] = [x for x in c['pending'] if not (x.get('kind') == 'return_note' and x.get('ref') == t['id'])]
    b['served'] += 1
    b['total'] += 1
    b['revenue'] += reward
    note = next((x for x in c['pending'] if x.get('kind') == 'return_note' and x.get('ref') == t['id']), None)
    if note and not t.get('walkin'):
        note['text'] = f"Hôm qua ly {low(ING[t['needs']['base']]['name'])} ở quầy ngon lắm. Hôm nay mình ghé chào một chút nhé."

    if not issues:
        b['perfect'] += 1
    if not t.get('walkin') and t['npc'] in REGULARS:
        book = b['notebook'].get(t['npc'])
        b['notebook'][t['npc']] = dict(usual=copy.deepcopy(t['needs']), visits=(book or {}).get('visits', 0) + 1, day=c['day'])
    extra = []
    if t.get('vip'):
        if not issues:
            e.money(s, c, 20, 'Video của Hân giới thiệu quán', t['id'], category='promotion')
            b['bonus'] += 20
            e.add_feed(s, c, 'milk_tea_npc_04', 'Video mới: “Ly trà chuẩn vị ở Trà Mây — pha trước mặt, đúng từng lời dặn.” Mọi người ghé thử nha! ✨', t['id'], 5, 'review')
            extra.append('Hân khen trong video: +20 xu quảng bá.')
            b['quota'] += 1
        else:
            e.add_feed(s, c, 'milk_tea_npc_04', 'Ly hôm nay hơi lệch lời dặn. Quán dễ thương, chắc hôm khác sẽ chuẩn hơn.', t['id'], 3, 'review')
    if t.get('office'):
        off = b.get('office')
        if off:
            off['done'] += 1
            if off['done'] >= off['count']:
                if c['turn'] <= off['deadline'] and off['bonus']:
                    e.money(s, c, off['bonus'], 'Đơn văn phòng giao đúng hẹn', off['ref'], category='tip')
                    b['bonus'] += off['bonus']
                    e.add_feed(s, c, 'milk_tea_npc_01', f"Đơn {off['count']} ly của văn phòng tới đúng hẹn, cả phòng ai cũng khen. Cảm ơn quán! 💼", off['ref'], 5, 'review')
                    extra.append(f"Đơn văn phòng xong đúng hẹn: +{off['bonus']} xu.")
                else:
                    e.add_feed(s, c, 'milk_tea_npc_01', 'Đơn văn phòng đủ ly nhưng trễ hơn giờ hẹn một chút. Lần sau hẹn dư giờ giúp chị nha.', off['ref'], 3, 'review')
                    extra.append('Đơn văn phòng xong nhưng trễ hẹn: không có thưởng.')
                b['office'] = None
    if cup.get('seal_q') == 'perfect' and not issues:
        e.money(s, c, 1, 'Nắp dán đẹp, khách thưởng thêm', t['id'], category='tip')
        extra.append('Nắp căng đẹp: khách thưởng 1 xu.')
    if t.get('app'):
        msg = f"Tài xế lấy đơn {t['app']['code']}{' — đúng giờ!' if not late else ' (hơi trễ)'} +{reward} xu (app giữ {fee} xu phí)."
    elif gid:
        msg = f"{name} nhận ly {t['group']['i']}/{t['group']['n']}{' — hoàn hảo!' if not issues else ''} +{reward} xu." + (f" Còn {len(rest)} ly nữa." if rest else ' Đủ cả đơn rồi!')
    else:
        msg = f"{name} nhận ly{' — hoàn hảo!' if not issues else ''} +{reward} xu."
    if t.get('discount'):
        msg += f" (bớt {t['discount']} xu như đã hẹn)"
    if said['message']:
        extra.insert(0, said['message'])
    r = dict(message=' '.join([msg] + extra), celebrate=not issues and not cq.slips(t), _arrivals=not rest)
    if cq.slips(t):
        r['reaction'] = said['kind']
    return r


def _slips(t: dict, cup: dict, issues: list) -> None:
    """What the customer notices when the cup is not what they asked for."""
    n = t['needs']
    if 'ice' in issues:
        want, got = n['ice'], cup['ice']
        gap = abs(ICES.index(want) - ICES.index(got))
        more = ICES.index(got) > ICES.index(want)
        if gap >= 2:
            text = f'Dặn {ICE_TEXT[want]} mà đưa {ICE_TEXT[got]}, uống toàn nước đá.' if more else f'Dặn {ICE_TEXT[want]} mà đưa {ICE_TEXT[got]}, ly trà chẳng mát gì.'
        else:
            text = f'Dặn {ICE_TEXT[want]} mà đưa {ICE_TEXT[got]}, hơi nhiều đá so với ý mình.' if more else f'Dặn {ICE_TEXT[want]} mà đưa {ICE_TEXT[got]}, hơi ít đá so với ý mình.'
        cq.slip(t, 'ice', 2 if gap >= 2 else 1, text, f'dặn {ICE_TEXT[want]} mà đưa {ICE_TEXT[got]}')
    if 'sugar' in issues:
        want, got = n['sugar'], cup['sugar']
        gap = abs(SUGARS.index(want) - SUGARS.index(got))
        if gap >= 2:
            text = f'Dặn {want}% đường mà ngọt lịm như {got}%.' if got > want else f'Dặn {want}% đường mà chỉ có {got}%, uống nhạt thếch.'
        else:
            text = f'Dặn {want}% đường mà pha {got}%, hơi ngọt so với ý mình.' if got > want else f'Dặn {want}% đường mà pha {got}%, hơi nhạt so với ý mình.'
        cq.slip(t, 'sugar', 2 if gap >= 2 else 1, text, f'dặn {want}% đường mà pha {got}%')
    if 'seal' in issues:
        cq.slip(t, 'seal', 1, 'Nắp dán cháy xém, cầm lên thấy ngại.', 'nắp dán cháy xém')
    if 'late' in issues:
        cq.slip(t, 'late', 1, 'Đơn giao trễ giờ hẹn.', 'giao trễ giờ hẹn')


# ---------------------------------------------------------------- events
def _open_tasks(c: dict) -> list[dict]:
    return [t for t in c['tasks'] if t['career'] == CAREER and t['status'] not in ('completed', 'referred', 'cancelled')]


def _active(c: dict) -> dict | None:
    return next((t for t in _open_tasks(c) if t['id'] == c.get('active_task')), None)


def _check_inspection(s, c, b):
    if c['day'] < 3 and level(c) < 2:
        return None
    if 'inspection' in [h['kind'] for h in b['ev_history'][-6:]]:
        return None
    return dict(team='Đội quản lý thị trường phường')


def _check_pearls(s, c, b):
    if not unlocked(c, 'pearls') or 'pearls' in b['sold_out'] or clock_minutes(c) < 11 * 60:
        return None
    if stock(c)['pearls'] > 2:
        return None
    waiting = [t for t in _open_tasks(c) if 'pearls' in t['needs']['toppings'] and 'pearls' not in t['cup']['items']]
    if not waiting:
        return None
    return dict(tasks=[t['id'] for t in waiting], left=stock(c)['pearls'])


def _check_rush(s, c, b):
    if c['day'] < 2 or clock_minutes(c) < 13 * 60:
        return None
    if len(_open_tasks(c)) > 3:
        return None
    n = 3 if modifier(c)['id'] == 'students' or level(c) >= 4 else 2
    return dict(count=n)


def _check_story(s, c, b):
    st = b['story']
    if c['day'] < 2 or st['step'] >= 3 or st['day'] >= c['day']:
        return None
    if st['step'] == 2 and len(_open_tasks(c)) > 4:
        return None
    return dict(step=st['step'])


def _check_change(s, c, b):
    if c['day'] < 2:
        return None
    t = _active(c)
    if not t or not t['known'] or t['cup']['sealed'] or not t['cup']['items'] or t.get('usual') or t.get('vip') or t.get('office'):
        return None
    r = rng(CAREER, 'change', t['id'])
    n = t['needs']
    options = []
    if n['size'] == 'M':
        options.append(dict(set='size', to='L'))
    ice = next((x for x in ('little', 'none') if x != n['ice']), None)
    if ice:
        options.append(dict(set='ice', to=ice))
    sugar = next((x for x in (30, 50, 70) if x != n['sugar']), None)
    options.append(dict(set='sugar', to=sugar))
    extra = [x for x in TOPPINGS if unlocked(c, x) and x not in n['toppings'] and stock(c)[x] > 0]
    if extra and len(n['toppings']) < MAX_TOPPINGS:
        options.append(dict(add=r.choice(extra)))
    return dict(task=t['id'], change=r.choice(options))


def _check_office(s, c, b):
    if b.get('office') or clock_minutes(c) < 12 * 60:
        return None
    if modifier(c)['id'] != 'office' and level(c) < 3:
        return None
    return dict(count=3, bonus=15)


def _check_spill(s, c, b):
    if c['day'] < 2:
        return None
    t = next((t for t in _open_tasks(c) if t['cup']['sealed']), None)
    if not t:
        return None
    return dict(task=t['id'], value=t['cup']['cost'])


def _check_short(s, c, b):
    if c['day'] < 2:
        return None
    st = stock(c)
    bases = [x for x in BASES if unlocked(c, x) and st[x] <= 6]
    if not bases:
        return None
    r = rng(CAREER, 'short', c['day'], c['turn'])
    item = r.choice(bases)
    billed = 10
    got = r.choice([6, 7, 8])
    return dict(item=item, billed=billed, got=got, cost=ING[item]['cost'], _honest=r.random() < 0.75)


def _check_power(s, c, b):
    if level(c) < 2 or 'sealer' in b['upgrades']:
        return None
    return dict(beats=4)


def _check_money(s, c, b):
    if c['day'] < 2:
        return None
    t = next((t for t in _open_tasks(c) if t['known'] and (t.get('walkin') or {}).get('kind') == 'student' and not t.get('discount')), None)
    if not t:
        return None
    return dict(task=t['id'], short=5, size=t['needs']['size'], _honest=rng(CAREER, 'coins', t['id']).random() < 0.8)


def _check_vip(s, c, b):
    if modifier(c)['id'] != 'review' and level(c) < 4:
        return None
    if any(t.get('vip') for t in _open_tasks(c)):
        return None
    return dict(guest='Hân')


EVENTS = {
    'inspection': dict(check=_check_inspection, weight=2, title='Quản lý thị trường kiểm tra', emoji='📋'),
    'pearls_out': dict(check=_check_pearls, weight=5, title='Hết trân châu giữa trưa', emoji='🟤'),
    'rush': dict(check=_check_rush, weight=3, title='Học sinh tan học ùa vào', emoji='🎒'),
    'regular': dict(check=_check_story, weight=3, title='Chuyện của bác Tư', emoji='👵'),
    'change_mind': dict(check=_check_change, weight=2, title='Khách đổi ý giữa chừng', emoji='🔄'),
    'office': dict(check=_check_office, weight=3, title='Đơn văn phòng 3 ly', emoji='💼'),
    'spill': dict(check=_check_spill, weight=1, title='Ly vừa dán nắp bị đổ', emoji='💦'),
    'short_delivery': dict(check=_check_short, weight=2, title='Bình giao hàng thiếu', emoji='📦'),
    'power_cut': dict(check=_check_power, weight=1, title='Cúp điện, máy dán nắp ngưng', emoji='🔌'),
    'short_money': dict(check=_check_money, weight=2, title='Bé học sinh thiếu tiền lẻ', emoji='🪙'),
    'vip': dict(check=_check_vip, weight=2, title='Hân xin quay video ly signature', emoji='📱'),
}
MOD_BOOST = {'students': 'rush', 'office': 'office', 'review': 'vip', 'market': 'regular'}


def _maybe_event(s: dict, c: dict, b: dict) -> None:
    ev = b.get('event')
    if ev or not c['open'] or c['day_completed'] < 1:
        return
    lv = level(c)
    mod = modifier(c)['id']
    cap = 1 + (lv >= 3) + (lv >= 5) + (mod == 'market')
    if b['events_today'] >= cap:
        return
    now = beats(c)
    if now - b['last_event_beat'] < 5:
        return
    r = rng(CAREER, 'event', c['day'], c['turn'], b['events_today'])
    if r.random() > 0.4:
        return
    recent = [h['kind'] for h in b['ev_history'][-4:]]
    cands = []
    for kind, spec in EVENTS.items():
        if kind in b['today_kinds']:
            continue
        facts = spec['check'](s, c, b)
        if facts is None:
            continue
        weight = spec['weight'] * (3 if MOD_BOOST.get(mod) == kind else 1) * (1 if kind not in recent else 0.3)
        cands.append((kind, facts, weight))
    if not cands:
        return
    kind, facts, _ = r.choices(cands, [x[2] for x in cands])[0]
    b['ev_seq'] += 1
    ev = dict(id=f"tea-ev-{c['day']}-{b['ev_seq']}", kind=kind, day=c['day'], turn=c['turn'], stage='open', facts=facts,
              task=facts.get('task'), choice=None, result=None, effects=[])
    b['event'] = ev
    b['events_today'] += 1
    b['last_event_beat'] = now
    b['today_kinds'].append(kind)
    if kind == 'spill':
        t = next(t for t in c['tasks'] if t['id'] == facts['task'])
        _waste_cup(c, t, 'Ly bị đổ')
        b['mess'] = min(9, b['mess'] + 2)
    if kind == 'power_cut':
        b['sealer_off'] = c['turn'] + facts['beats']
    _e().log(s, c, 'counter_event', EVENTS[kind]['title'], ref=ev['id'])


def _expire_moot(c: dict, b: dict) -> None:
    ev = b.get('event')
    if not ev or ev['stage'] != 'open' or not ev.get('task'):
        return
    if ev['kind'] == 'spill':
        return
    t = next((t for t in c['tasks'] if t['id'] == ev['task']), None)
    if not t or t['status'] in ('completed', 'referred', 'cancelled'):
        ev.update(stage='done', choice='moot', result='Khách đã rời quầy, chuyện nhỏ này cũng qua.', effects=[])


def event_text(c: dict, ev: dict) -> str:
    f = ev['facts']
    k = ev['kind']
    task = next((t for t in c['tasks'] if t['id'] == ev.get('task')), None)
    who = customer_name(task) if task else 'Khách'
    if k == 'inspection':
        return 'Hai cán bộ đội quản lý thị trường ghé quầy: “Cho kiểm tra vệ sinh quầy pha và sổ nhập nguyên liệu nhé.”'
    if k == 'pearls_out':
        return f"Mới giữa trưa mà nồi trân châu chỉ còn {f['left']} phần, trong khi {len(f['tasks'])} ly đang chờ có trân châu."
    if k == 'rush':
        return f"Chuông tan học vừa reo, {f['count']} bạn học sinh ùa vào cùng lúc: “Quán ơi, bán cho tụi em với!”"
    if k == 'regular':
        return [
            'Bác Tư ghé quầy, tay cầm sổ khám: “Bác sĩ dặn bác bớt ngọt. Mà bác mê ly hồng trà 100% đường của cháu lắm…”',
            'Bác Tư khoe tấm ảnh: “Cháu gái bác đỗ đại học trên thành phố rồi! Cuối tuần nó về, bác muốn dẫn nó ra quán.”',
            'Bác Tư dắt cháu gái vào quán, cười tươi: “Đây, quán bác kể đó. Cháu pha cho Ngân một ly thật ngon nha.”',
        ][f['step']]
    if k == 'change_mind':
        ch = f['change']
        what = (f"đổi sang size {ch['to']}" if ch.get('set') == 'size' else f"cho {ICE_TEXT[ch['to']]}" if ch.get('set') == 'ice'
                else f"chỉnh {ch['to']}% đường" if ch.get('set') == 'sugar' else f"thêm {ING[ch['add']]['name'].lower()}")
        return f"{who} gọi với theo: “À khoan, cho mình {what} được không?”"
    if k == 'office':
        return f"Chị Hạnh ở văn phòng gần quán gọi: “Đặt {f['count']} ly mang lên phòng họp nha em, kịp trong khoảng một tiếng rưỡi được không?”"
    if k == 'spill':
        return f"Một bé chạy nhảy va vào quầy, ly vừa dán nắp của {who} đổ lênh láng. Mẹ bé cuống quýt xin lỗi."
    if k == 'short_delivery':
        return f"Bình giao {ING[f['item']]['name'].lower()}: phiếu ghi {f['billed']} phần, nhưng thùng hình như chỉ có {f['got']} phần."
    if k == 'power_cut':
        return 'Phụt! Cả dãy phố cúp điện. Máy dán nắp tắt ngấm, khách vẫn đang chờ.'
    if k == 'short_money':
        return f"{who} đếm tiền lẻ, mặt đỏ ửng: “Em thiếu {f['short']} xu… em về lấy thêm được không ạ?”"
    if k == 'vip':
        return 'Hân (làm video ẩm thực) ghé quầy: “Mình quay một ly signature của quán được không? Pha thật như mọi ngày thôi nha.”'
    return ''


def event_choices(c: dict, ev: dict) -> list[dict]:
    f = ev['facts']
    k = ev['kind']
    if k == 'inspection':
        return [dict(id='open', label='Mời kiểm tra, mở sổ nhập hàng'), dict(id='clean', label='Xin 2 phút lau quầy trước', hint='Khách đang chờ mất kiên nhẫn'),
                dict(id='envelope', label='Dúi phong bì “uống nước”', hint='Không nên đâu…')]
    if k == 'pearls_out':
        return [dict(id='cook', label='Nấu gấp một nồi', cost=16, hint='8 phần, khách chờ thêm 3 nhịp'),
                dict(id='swap', label='Mời khách đổi topping khác', hint='Thay bằng thạch'),
                dict(id='sign', label='Treo bảng “Tạm hết trân châu”', hint='Có khách sẽ tiếc mà về')]
    if k == 'rush':
        return [dict(id='all', label=f"Nhận hết {f['count']} bạn", hint='Nhiều ly, nhiều áp lực'), dict(id='two', label='Nhận 2 bạn, hẹn nhóm sau'),
                dict(id='menu', label='Mời cả nhóm “ly nhanh” trà sữa trân châu', hint='Cùng một công thức, không tip')]
    if k == 'regular':
        return [
            [dict(id='less', label='Gợi ý 50% đường cho bác'), dict(id='same', label='Pha đúng ý bác, dặn uống chậm thôi')],
            [dict(id='reserve', label='Hẹn giữ góc bàn cạnh cửa sổ'), dict(id='treat', label='Mời bác ly hôm nay, mừng cháu đỗ', cost=25)],
            [dict(id='serve', label='Pha cho Ngân một ly, hỏi kỹ từng phần'), dict(id='photo', label='Chụp cho hai bác cháu tấm ảnh trước quầy')],
        ][f['step']]
    if k == 'change_mind':
        return [dict(id='accept', label='Dạ được ạ!'), dict(id='keep', label='Ly đã pha rồi, xin giữ như cũ nhé')]
    if k == 'office':
        return [dict(id='accept', label='Nhận đơn, hẹn đúng giờ', hint=f"Xong kịp: +{f['bonus']} xu"),
                dict(id='later', label='Nhận nhưng xin hẹn trễ hơn', hint='Không thưởng, đỡ áp lực'), dict(id='decline', label='Xin lỗi, hôm nay quầy kín đơn')]
    if k == 'spill':
        return [dict(id='wipe', label='Lau quầy ngay, rồi làm lại ly'), dict(id='pay', label='Nhận 10 xu mẹ bé đền, lau quầy'),
                dict(id='later', label='Làm lại ly trước, lau sau', hint='Quầy còn bẩn')]
    if k == 'short_delivery':
        return [dict(id='count', label=f"Đếm lại, ký nhận {f['got']} phần", cost=f['got'] * f['cost']),
                dict(id='sign', label=f"Ký đủ {f['billed']} phần cho nhanh", cost=f['billed'] * f['cost']),
                dict(id='refuse', label='Trả cả thùng, hẹn giao lại')]
    if k == 'power_cut':
        return [dict(id='dome', label='Dùng nắp cầu thay màng dán', hint='1 xu mỗi ly'), dict(id='wait', label='Mời khách chờ, tặng thêm thạch', hint='Khách vui hơn, quầy chậm lại')]
    if k == 'short_money':
        opts = [dict(id='trust', label='Cho nợ, mai ghé trả'), dict(id='treat', label='Mời luôn phần thiếu')]
        if f['size'] == 'L':
            opts.insert(1, dict(id='size', label='Gợi ý đổi xuống size M cho vừa tiền'))
        return opts
    if k == 'vip':
        return [dict(id='accept', label='Nhận quay, pha như mọi ly'), dict(id='decline', label='Cảm ơn, hôm nay quầy đông quá')]
    return []


def _answer(s: dict, c: dict, b: dict, p: dict) -> dict:
    e = _e()
    ev = b.get('event')
    e.need(ev and ev['stage'] == 'open', 'Không có chuyện nào đang chờ bạn trả lời.')
    choice = p.get('choice')
    opts = event_choices(c, ev)
    opt = next((o for o in opts if o['id'] == choice), None)
    e.need(opt, 'Lựa chọn không có trong tình huống.')
    if opt.get('cost'):
        e.need(c['money'] >= opt['cost'], 'Chưa đủ xu cho lựa chọn này. Chọn cách khác nhé.')
    _resolve(s, c, b, ev, choice)
    return dict(message=ev['result'], celebrate=ev.get('good', False))


def _task_by(c: dict, tid: str | None) -> dict | None:
    return next((t for t in c['tasks'] if t['id'] == tid and t['status'] not in ('completed', 'referred', 'cancelled')), None)


def _change(c: dict, t: dict, ch: dict) -> None:
    t['changes'] = t.get('changes', []) + [dict(ch)]
    t['needs'] = derive(t)
    t['quoted_price'] = price(c, t['needs'])


def _resolve(s: dict, c: dict, b: dict, ev: dict, choice: str) -> None:
    e = _e()
    f = ev['facts']
    k = ev['kind']
    eff = []
    good = False
    result = ''
    waiting = [t for t in _open_tasks(c) if t['id'] != c.get('active_task')]
    if k == 'inspection':
        dirty = b['mess'] >= UNSAFE_MESS
        if choice == 'open':
            if dirty:
                fine = min(40, c['money'])
                if fine:
                    e.money(s, c, -fine, 'Phạt vệ sinh quầy pha', ev['id'], category='fine')
                b['fines'] += fine
                result = f'Đoàn ghi biên bản: quầy còn vệt trà đổ, chưa lau. Phạt {fine} xu. Buồn ghê…'
                eff.append(f'-{fine} xu')
            else:
                result = 'Quầy sạch, sổ nhập hàng ghi rõ từng mẻ. Đoàn ký biên bản “không vi phạm” rồi chào về.'
                c['xp'] += 10
                good = True
                eff.append('+10 XP')
        elif choice == 'clean':
            b['mess'] = 0
            for t in waiting:
                t['patience'] = max(25, t.get('patience', 100) - 8)
            result = 'Bạn lau quầy trước khi mở sổ. Đoàn nhắc nhở giữ vệ sinh thường xuyên, không lập biên bản phạt.' if dirty else 'Quầy vốn đã sạch; đoàn kiểm nhanh rồi về. Khách xếp hàng phải chờ thêm một chút.'
            eff.append('Khách chờ -8 kiên nhẫn')
        else:
            fine = min(80, c['money'])
            if fine:
                e.money(s, c, -fine, 'Phạt vì đưa tiền cho đoàn kiểm tra', ev['id'], category='fine')
            b['fines'] += fine
            result = f'Đoàn từ chối phong bì và lập biên bản nặng hơn: phạt {fine} xu. Làm đúng từ đầu vẫn nhẹ nhõm nhất.'
            eff.append(f'-{fine} xu')
    elif k == 'pearls_out':
        tasks = [t for t in (_task_by(c, x) for x in f['tasks']) if t and 'pearls' not in t['cup']['items']]
        if choice == 'cook':
            e.money(s, c, -16, 'Nấu gấp trân châu', ev['id'], category='stock')
            add_lot(s, c, 'pearls', 8, 2)
            for t in _open_tasks(c):
                t['patience'] = max(25, t.get('patience', 100) - 3 * max(1, rate(c)))
            result = 'Nồi trân châu mới sôi lăn tăn. Thêm 8 phần, nhưng khách phải chờ lâu hơn một chút.'
            eff += ['-16 xu', '+8 trân châu']
        elif choice == 'swap':
            swap_to = next((x for x in ('q3', 'jelly', 'coconut', 'pudding') if unlocked(c, x) and stock(c)[x] > 0), 'jelly')
            for t in tasks:
                _change(c, t, dict(swap='pearls', to=swap_to))
            result = f"Bạn xin lỗi và mời {len(tasks)} khách đổi sang {ING[swap_to]['name'].lower()}. Ai cũng gật đầu."
            eff.append(f"Đổi {len(tasks)} ly sang {ING[swap_to]['name'].lower()}")
            good = True
        else:
            b['sold_out'] = sorted(set(b['sold_out'] + ['pearls']))
            left = []
            for i, t in enumerate(tasks):
                if i == 0 and len(tasks) > 1:
                    t['status'] = 'cancelled'
                    t['walked'] = True
                    t['completed_turn'] = c['turn']
                    b['walkouts'] += 1
                    post = e.add_feed(s, c, t['npc'], 'Mới trưa đã hết trân châu, buồn ghê 💔', t['id'], 3, 'review')
                    post['author'] = customer_name(t)
                    left.append(customer_name(t))
                else:
                    _change(c, t, dict(drop='pearls'))
            e.next_active(c)
            result = 'Bảng “Tạm hết trân châu” đã treo. ' + (f"{left[0]} tiếc quá nên về trước; " if left else '') + 'các khách khác bỏ trân châu khỏi ly.'
            eff.append('Hôm nay không nhận thêm trân châu')
    elif k == 'rush':
        n = f['count'] if choice in ('all', 'menu') else 2
        fixed = dict(base='milk', flavor=None, toppings=['pearls'] if unlocked(c, 'pearls') else [], size='M', sugar=50, ice='normal') if choice == 'menu' else None
        kids = [w for w in WALKINS if w['kind'] == 'student']
        made = []
        for i in range(n):
            t = spawn(s, c, fixed=fixed, patience=70, walkin=kids[i % len(kids)], count_quota=False)
            if t:
                if choice == 'menu':
                    t['combo'] = True
                made.append(t)
        result = f"{len(made)} bạn học sinh vào hàng chờ. " + ('Cả nhóm cùng một công thức: trà sữa trân châu size M.' if choice == 'menu' else 'Làm nhanh tay nhé!')
        eff.append(f'+{len(made)} khách')
        good = choice != 'two'
    elif k == 'regular':
        st = b['story']
        npc = 'milk_tea_npc_02'
        if f['step'] == 0:
            if choice == 'less':
                book = b['notebook'].get(npc)
                if book:
                    book['usual']['sugar'] = 50
                result = 'Bác Tư gật gù: “Ừ, 50% thôi. Cháu ghi vào sổ giúp bác.” Sổ khách quen đã cập nhật.'
            else:
                result = 'Bác Tư cười: “Bác uống chậm, đi bộ nhiều hơn.” Bạn nhớ dặn bác uống thêm nước lọc.'
            e.remember(s, c, npc, 'Bác kể chuyện đi khám; bạn đã ' + ('gợi ý bớt đường.' if choice == 'less' else 'pha đúng ý và dặn bác uống chậm.'), ev['id'])
        elif f['step'] == 1:
            if choice == 'treat':
                e.money(s, c, -25, 'Mời bác Tư ly mừng cháu đỗ', ev['id'], category='gift')
                eff.append('-25 xu')
                result = 'Bác Tư rưng rưng: “Cháu tốt quá.” Bác kể về cháu gái suốt một lúc.'
            else:
                result = 'Bạn ghi chú giữ góc bàn cạnh cửa sổ cho cuối tuần. Bác Tư vui ra mặt.'
            e.remember(s, c, npc, 'Bác khoe cháu gái đỗ đại học; bạn đã ' + ('mời bác ly mừng.' if choice == 'treat' else 'hẹn giữ góc bàn.'), ev['id'])
        else:
            if choice == 'serve':
                t = spawn(s, c, fixed=dict(base='milk', flavor='peach' if unlocked(c, 'peach') else None, toppings=['jelly'], size='M', sugar=50, ice='little'),
                          walkin=dict(id='ngan', name='Ngân', kind='young', emoji='👩‍🎓'), count_quota=False)
                result = 'Ngân gọi một ly trà sữa đào thạch mây. ' + ('Ngân đã vào hàng chờ.' if t else 'Hôm nay quầy kín lượt, bạn pha tặng ở bàn.')
                if t:
                    eff.append('+1 khách')
            else:
                result = 'Tấm ảnh hai bác cháu cười bên quầy trà được ghim lên bảng của quán.'
                c['xp'] += 10
            e.remember(s, c, npc, 'Bác dẫn cháu gái Ngân tới quán; một chương mới của khách quen.', ev['id'])
            e.add_feed(s, c, npc, 'Hôm nay bác dẫn cháu gái ra quán. Cháu nó khen trà ngon, bác vui cả ngày. Cảm ơn quán nha!', ev['id'], 5, 'review')
            from . import experiences as life
            life._sticker(c, 'tea-story-tu', 'Chuyện của bác Tư', '👵')
            good = True
        st['step'] += 1
        st['day'] = c['day']
        st['choices'] = (st['choices'] + [choice])[-3:]
        c['relationships'][npc] = min(100, c['relationships'].get(npc, 0) + 3)
    elif k == 'change_mind':
        t = _task_by(c, f['task'])
        ch = f['change']
        if t:
            if choice == 'accept':
                _change(c, t, ch)
                result = 'Bạn vui vẻ ghi lại lời dặn mới. ' + ('Ly đang pha khác cỡ nên cần làm lại.' if ch.get('set') == 'size' and t['cup']['placed'] and t['cup']['size'] != ch['to'] else 'Chỉnh tiếp trên ly đang pha nhé.')
                t['patience'] = min(100, t.get('patience', 100) + 5)
                good = True
            else:
                t['patience'] = max(25, t.get('patience', 100) - 6)
                result = 'Khách hơi tiếc nhưng hiểu: giữ nguyên như lúc gọi.'
                eff.append('-6 kiên nhẫn')
    elif k == 'office':
        if choice == 'decline':
            result = 'Chị Hạnh bảo không sao, hẹn hôm khác đặt sớm hơn.'
        else:
            deadline = c['turn'] + 3 * 11 + (14 if choice == 'later' else 0)
            b['office'] = dict(ref=ev['id'], count=0, done=0, deadline=deadline, bonus=0 if choice == 'later' else f['bonus'])
            hanh = dict(id='hanh', name='Chị Hạnh', kind='office', me='chị', emoji='👩‍💼')
            for t in spawn_group(s, c, f['count'], walkin=hanh, count_quota=False, patience=90):
                t['office'] = True
                b['office']['count'] += 1
            if not b['office']['count']:
                b['office'] = None
            result = f"Đã nhận {b['office']['count'] if b['office'] else 0} ly văn phòng. " + ('Hẹn trong khoảng một tiếng rưỡi.' if choice == 'accept' else 'Hẹn giờ thong thả hơn, không có thưởng đúng hẹn.')
            eff.append('Đơn văn phòng')
    elif k == 'spill':
        if choice == 'wipe':
            b['mess'] = 0
            result = 'Bạn lau sạch quầy rồi làm lại ly. Mẹ bé cảm ơn rối rít.'
            good = True
        elif choice == 'pay':
            b['mess'] = 0
            e.money(s, c, 10, 'Mẹ bé đền ly bị đổ', ev['id'], category='compensation')
            eff.append('+10 xu')
            result = 'Mẹ bé gửi 10 xu đền ly. Quầy đã sạch, bạn làm lại ly mới.'
        else:
            result = 'Bạn làm lại ly trước, quầy còn vệt trà. Nhớ lau khi rảnh tay nhé.'
            eff.append('Quầy còn bẩn')
    elif k == 'short_delivery':
        if choice == 'count':
            e.money(s, c, -f['got'] * f['cost'], 'Nhận ' + ING[f['item']]['name'], ev['id'], category='stock')
            add_lot(s, c, f['item'], f['got'], f['cost'])
            result = f"Bạn đếm lại cùng Bình và ký đúng {f['got']} phần. Bình gãi đầu xin lỗi."
            eff.append(f"+{f['got']} phần")
            good = True
        elif choice == 'sign':
            e.money(s, c, -f['billed'] * f['cost'], 'Nhận ' + ING[f['item']]['name'], ev['id'], category='stock')
            add_lot(s, c, f['item'], f['got'], f['cost'])
            b['promises'].append(dict(kind='portions', day=c['day'] + 1, item=f['item'], qty=f['billed'] - f['got'], ref=ev['id'], _honest=f['_honest']))
            result = f"Ký đủ {f['billed']} phần cho nhanh, nhưng thùng chỉ có {f['got']}. Bình hứa mai mang bù."
            eff.append(f"+{f['got']} phần, trả tiền {f['billed']}")
        else:
            result = 'Bạn trả thùng, hẹn Bình giao lại đủ số. Kho vẫn đang thiếu.'
        c['relationships']['milk_tea_npc_05'] = min(100, c['relationships'].get('milk_tea_npc_05', 0) + (2 if choice == 'count' else 0))
    elif k == 'power_cut':
        if choice == 'dome':
            b['dome'] = True
            result = 'Bạn lôi hộp nắp cầu ra. Dán màng tạm ngưng, đậy nắp cầu thì vẫn giao được.'
        else:
            for t in _open_tasks(c):
                t['patience'] = min(100, t.get('patience', 100) + 10)
            result = 'Bạn mời khách ngồi chờ, tặng mỗi người chút thạch. Ai cũng thông cảm.'
            eff.append('Khách +10 kiên nhẫn')
            good = True
    elif k == 'short_money':
        t = _task_by(c, f['task'])
        if t:
            if choice == 'size' and t['needs']['size'] == 'L':
                _change(c, t, dict(set='size', to='M'))
                result = 'Bé gật đầu đổi xuống size M, vừa đủ tiền.' + (' Ly đang pha cần đổi cỡ.' if t['cup']['placed'] and t['cup']['size'] == 'L' else '')
            elif choice == 'trust':
                t['discount'] = f['short']
                b['promises'].append(dict(kind='coins', day=c['day'] + 1, qty=f['short'], ref=ev['id'], _honest=f['_honest']))
                result = 'Bé hứa mai ghé trả. Bạn ghi vào sổ nợ nhỏ của quầy.'
            else:
                t['discount'] = f['short']
                c['xp'] += 5
                result = 'Bạn mời luôn phần thiếu. Bé cảm ơn lí nhí, mắt sáng rỡ.'
                good = True
    elif k == 'vip':
        if choice == 'accept':
            best = [x for x in BASES if unlocked(c, x)][-1]
            tops = [x for x in TOPPINGS if unlocked(c, x)][-2:]
            fixed = dict(base=best, flavor=None, toppings=tops, size='L', sugar=50, ice='little')
            t = spawn(s, c, fixed=fixed, walkin=dict(id='han', name='Hân', kind='young', emoji='📱'), count_quota=False)
            if t:
                t['vip'] = True
                t['patience'] = 85
            result = 'Hân dựng máy quay ở góc quầy. Ly signature của quán: pha thật chuẩn nhé!' if t else 'Quầy đã kín lượt hôm nay; Hân hẹn ghé dịp khác.'
            eff.append('Khách đặc biệt')
        else:
            result = 'Hân vui vẻ hẹn dịp khác, không sao cả.'
    ev.update(stage='done', choice=choice, result=result, effects=eff, good=good)
    b['ev_history'] = (b['ev_history'] + [dict(kind=k, choice=choice, day=c['day'])])[-30:]
    e.log(s, c, 'counter_event', EVENTS[k]['title'] + ': ' + result, ref=ev['id'])


# ---------------------------------------------------------------- projection
def _clean(v):
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items() if not str(k).startswith('_')}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def public(c: dict) -> dict:
    b = view(c)
    lv = level(c)
    mod = modifier(c)
    active = _open_tasks(c)
    ev = b.get('event')
    ev_view = None
    if ev:
        ev_view = dict(id=ev['id'], kind=ev['kind'], stage=ev['stage'], title=EVENTS[ev['kind']]['title'], emoji=EVENTS[ev['kind']]['emoji'],
                       text=event_text(c, ev), choices=event_choices(c, ev) if ev['stage'] == 'open' else [],
                       result=ev.get('result'), effects=ev.get('effects', []), good=ev.get('good', False), task=ev.get('task'))
    st = stock(c)
    notebook = []
    for npc, row in REGULARS.items():
        entry = b['notebook'].get(npc)
        notebook.append(dict(npc=npc, name=_e().NPC_INDEX[npc]['display_name'], usual=copy.deepcopy(entry['usual']) if entry else None,
                             visits=entry['visits'] if entry else 0))
    left = max(0, b['quota'] - b['arrived']) + len([t for t in active])
    return _clean(dict(
        cups=b['cups'], cup_pack=CUP_PACK, mess=b['mess'], level=lv, total=b['total'], next_tier=next_tier(c), clock=clock(c), beats=beats(c), rate=rate(c),
        modifier=dict(id=mod['id'], title=mod['title'], emoji=mod['emoji'], text=mod['text']),
        quota=b['quota'], arrived=b['arrived'], left=left if c['open'] else None, served=b['served'], perfect=b['perfect'],
        returned=b['returned'], walkouts=b['walkouts'], revenue=b['revenue'], fines=b['fines'], streak=c['life'].get('streak', 0),
        best_streak=c['life'].get('best_streak', 0),
        stations=[dict(id=x['id'], group=x['group'], level=x.get('level', 1), unlocked=x.get('level', 1) <= lv, stock=st[x['id']]) for x in data.INGREDIENTS],
        upgrades=[dict(u, owned=u['id'] in b['upgrades'], ready=lv >= u['level']) for u in UPGRADES],
        event=ev_view, notebook=notebook, warnings=warnings(c), history=b['history'][-7:], sold_out=b['sold_out'],
        sealer_off=b['sealer_off'] > c['turn'] and 'sealer' not in b['upgrades'], dome=b['dome'],
        office=dict(count=b['office']['count'], done=b['office']['done'], deadline_in=max(0, b['office']['deadline'] - c['turn']), bonus=b['office']['bonus']) if b.get('office') else None,
        story_step=b['story']['step'], prices=dict(base=BASE_PRICE, flavor=FLAVOR_PRICE, topping=TOPPING_PRICE, size_l=SIZE_L_PRICE),
        sugars=list(SUGARS), ices=list(ICES), seal=SEAL, app_fee=APP_FEE_PCT, turn=c['turn']))


def public_task(t: dict) -> dict:
    v = _clean(copy.deepcopy(t))
    v.pop('src', None)
    v.pop('changes', None)
    if not t['known']:
        v['needs'] = None
        v['order_text'] = None
    else:
        v['order_text'] = order_text(t)
        if t.get('usual'):
            v['needs'] = None
    v['customer'] = customer_name(t)
    v['speech'] = speech_kind(t)
    return v


# ---------------------------------------------------------------- validation
def _valid_needs(n) -> bool:
    return (isinstance(n, dict) and n.get('base') in BASES and (n.get('flavor') is None or n.get('flavor') in FLAVORS)
            and isinstance(n.get('toppings'), list) and len(n['toppings']) <= MAX_TOPPINGS and len(set(n['toppings'])) == len(n['toppings'])
            and all(x in TOPPINGS for x in n['toppings']) and n.get('size') in ('M', 'L') and type(n.get('sugar')) is int
            and n['sugar'] in SUGARS and n.get('ice') in ICES)


def _valid_change(ch) -> bool:
    if not isinstance(ch, dict) or len(ch) > 2:
        return False
    if 'set' in ch:
        return (ch['set'] == 'size' and ch.get('to') in ('M', 'L')) or (ch['set'] == 'ice' and ch.get('to') in ICES) or \
               (ch['set'] == 'sugar' and type(ch.get('to')) is int and ch['to'] in SUGARS)
    if 'swap' in ch:
        return ch['swap'] in TOPPINGS and ch.get('to') in TOPPINGS
    if 'add' in ch:
        return ch['add'] in TOPPINGS
    if 'drop' in ch:
        return ch['drop'] in TOPPINGS
    return False


def validate_task(t: dict) -> None:
    e = _e()
    need = e.need
    need(_valid_needs(t.get('needs')), 'Món khách gọi không hợp lệ.')
    if 'src' in t:
        src = t['src']
        need(isinstance(src, dict), 'Nguồn món gọi sai.')
        if 'fixed' in src:
            need(_valid_needs(src['fixed']), 'Món cố định sai.')
        else:
            e.integer(src.get('tier'), 1, 99)
            need(src.get('mod', '') in ('', *MOD_INDEX) and isinstance(src.get('avoid', []), list) and all(x in ING for x in src.get('avoid', [])), 'Nguồn món gọi sai.')
        need(isinstance(t.get('changes', []), list) and len(t.get('changes', [])) <= 6 and all(_valid_change(x) for x in t.get('changes', [])), 'Thay đổi món sai.')
        need(t['needs'] == derive(t), 'Món khách gọi không khớp nguồn đã chốt.')
    if t.get('walkin') is not None:
        w = t['walkin']
        need(isinstance(w, dict) and w.get('kind') in ('student', 'office', 'elder', 'young', 'app'), 'Khách vãng lai sai.')
        for k in ('id', 'name', 'emoji', 'me'):
            e.clean_text(w.get(k, 'mình'), 40)
    for k in ('usual', 'vip', 'office', 'combo', 'walked'):
        need(type(t.get(k, False)) is bool, 'Cờ khách sai.')
    e.integer(t.get('beats', 0), 0, 10**6)
    e.integer(t.get('discount', 0), 0, 50)
    if 'patience' in t:
        e.integer(t['patience'], 25, 100)
    cup = t['cup']
    need(isinstance(cup, dict) and set(('items', 'size', 'sugar', 'ice', 'sealed', 'checked', 'cost')) <= set(cup), 'Ly thiếu dữ liệu.')
    need(isinstance(cup['items'], list) and len(cup['items']) <= 5 and len(cup['items']) == len(set(cup['items'])) and all(k in ING for k in cup['items']), 'Nguyên liệu trong ly sai.')
    need(cup['size'] in ('M', 'L') and (cup['sugar'] is None or (type(cup['sugar']) is int and cup['sugar'] in SUGARS)) and (cup['ice'] is None or cup['ice'] in ICES), 'Tùy chọn ly sai.')
    groups = [ING[k]['group'] for k in cup['items']]
    need(groups.count('base') <= 1 and groups.count('flavor') <= 1 and groups.count('topping') <= MAX_TOPPINGS, 'Ly có quá nhiều lớp.')
    e.integer(cup['cost'], 0, 100)
    for k in ('sealed', 'checked', 'placed', 'dome'):
        need(type(cup.get(k, False)) is bool, 'Trạng thái ly sai.')
    st = cup.get('seal_t')
    need(st is None or (type(st) in (int, float) and 0 <= st < 10**11), 'Giờ ép nắp sai.')
    need(cup.get('seal_q') in SEAL_QUALITY and (cup.get('seal_q') is None or cup['sealed']), 'Chất lượng nắp sai.')
    g = t.get('group')
    if g is not None:
        need(isinstance(g, dict) and set(g) == {'id', 'n', 'i'} and type(g['n']) is int and 2 <= g['n'] <= 3
             and type(g['i']) is int and 1 <= g['i'] <= g['n'], 'Đơn nhiều ly sai.')
        e.clean_text(g['id'], 24)
    a = t.get('app')
    if a is not None:
        need(isinstance(a, dict) and set(a) == {'code', 'deadline', 'span'}, 'Đơn app sai.')
        e.clean_text(a['code'], 12)
        e.integer(a['deadline'], 0, 10**9)
        e.integer(a['span'], 1, 200)
    if cup['items']:
        need(cup.get('placed', True), 'Ly có trà nhưng chưa được đặt lên quầy.')
    if t['quoted_price'] is not None:
        e.integer(t['quoted_price'], 1, 1000)


def validate(c: dict) -> None:
    raw = ((c.get('ext') or {}).get('data') or {}).get('boba')
    if raw is None:
        return
    e = _e()
    need = e.need
    need(isinstance(raw, dict) and raw.get('v') == 1, 'Dữ liệu quầy trà sai.')
    b = view(c)
    need(isinstance(b['cups'], dict) and set(b['cups']) == {'M', 'L'}, 'Chồng ly sai.')
    for v in b['cups'].values():
        e.integer(v, 0, CUP_CAP)
    e.integer(b['mess'], 0, 9)
    need(isinstance(b['upgrades'], list) and all(u in UPGRADE_INDEX for u in b['upgrades']) and len(set(b['upgrades'])) == len(b['upgrades']), 'Nâng cấp quầy sai.')
    for k in ('day', 'turn0', 'quota', 'arrived', 'served', 'perfect', 'returned', 'walkouts', 'revenue', 'fines', 'bonus', 'events_today', 'ev_seq', 'sealer_off', 'total'):
        e.integer(b[k], 0, 10**9)
    e.integer(b['last_event_beat'], -99, 10**9)
    need(b['mod'] in MOD_INDEX, 'Biến số ngày sai.')
    need(type(b['dome']) is bool, 'Cờ nắp cầu sai.')
    need(isinstance(b['today_kinds'], list) and all(k in EVENTS for k in b['today_kinds']), 'Chuyện trong ngày sai.')
    need(isinstance(b['sold_out'], list) and all(k in ING for k in b['sold_out']), 'Món tạm hết sai.')
    need(isinstance(b['ev_history'], list) and len(b['ev_history']) <= 30 and all(isinstance(h, dict) and h.get('kind') in EVENTS for h in b['ev_history']), 'Lịch sử chuyện ở quầy sai.')
    need(isinstance(b['history'], list) and len(b['history']) <= 14, 'Tổng kết ngày sai.')
    need(isinstance(b['notebook'], dict) and all(k in REGULARS and isinstance(v, dict) and _valid_needs(v.get('usual')) for k, v in b['notebook'].items()), 'Sổ khách quen sai.')
    st = b['story']
    need(isinstance(st, dict) and type(st.get('step')) is int and 0 <= st['step'] <= 3 and isinstance(st.get('choices'), list), 'Chuyện khách quen sai.')
    need(isinstance(b['promises'], list) and len(b['promises']) <= 10, 'Lời hẹn sai.')
    for pr in b['promises']:
        need(isinstance(pr, dict) and pr.get('kind') in ('portions', 'coins'), 'Lời hẹn sai.')
        e.integer(pr.get('qty'), 1, 20)
        if pr['kind'] == 'portions':
            need(pr.get('item') in ING, 'Lời hẹn sai nguyên liệu.')
    off = b.get('office')
    if off is not None:
        need(isinstance(off, dict), 'Đơn văn phòng sai.')
        for k in ('count', 'done', 'deadline', 'bonus'):
            e.integer(off.get(k), 0, 10**9)
    ev = b.get('event')
    if ev is not None:
        need(isinstance(ev, dict) and ev.get('kind') in EVENTS and ev.get('stage') in ('open', 'done') and isinstance(ev.get('facts'), dict), 'Chuyện ở quầy sai.')
        if ev['stage'] == 'done':
            need(ev.get('choice') == 'moot' or ev.get('choice') in [o['id'] for o in event_choices(c, ev)], 'Lựa chọn chuyện ở quầy sai.')
            e.clean_text(ev.get('result'), 600)


# ---------------------------------------------------------------- helpers for tests / tools
def solution(t: dict) -> list[tuple[str, dict]]:
    """The ideal sequence of station actions for a task (used by tests)."""
    n = t['needs']
    tid = t['id']
    steps = [('tea_cup', dict(task=tid, size=n['size'])), ('tea_add', dict(task=tid, item=n['base']))]
    if n['flavor']:
        steps.append(('tea_add', dict(task=tid, item=n['flavor'])))
    steps += [('tea_add', dict(task=tid, item=x)) for x in n['toppings']]
    steps += [('tea_ice', dict(task=tid, level=n['ice'])), ('tea_sugar', dict(task=tid, level=n['sugar'])),
              ('tea_seal', dict(task=tid)), ('tea_serve', dict(task=tid, confirm=True))]
    return steps


CALM_ANSWER = {'inspection': 'open', 'pearls_out': 'swap', 'rush': 'two', 'change_mind': 'keep', 'office': 'decline', 'spill': 'wipe',
               'short_delivery': 'refuse', 'power_cut': 'dome', 'short_money': 'treat', 'vip': 'decline'}


def next_move(c: dict, t: dict) -> tuple[str, dict]:
    """One sensible next command for a task (tests and the staff helper use it)."""
    b = view(c)
    ev = b.get('event')
    if ev and ev['stage'] == 'open':
        if ev['kind'] == 'regular':
            choice = next(o['id'] for o in event_choices(c, ev) if not o.get('cost'))
        elif ev['kind'] == 'inspection' and b['mess'] >= UNSAFE_MESS:
            choice = 'clean'
        else:
            choice = CALM_ANSWER[ev['kind']]
        return 'tea_event', dict(choice=choice)
    tid = t['id']
    n = t['needs']
    cup = t['cup']
    if not t['known']:
        return 'ask', dict(task=tid)
    if cup['sealed']:
        if any(x in CRITICAL for x in _diff(cup, n)):
            return 'tea_discard', dict(task=tid, confirm=True)
        return 'tea_serve', dict(task=tid, confirm=True)
    wrong = [k for k in cup['items'] if k not in [n['base'], n['flavor'], *n['toppings']]]
    if wrong or (cup['placed'] and cup['items'] and cup['size'] != n['size']):
        return 'tea_discard', dict(task=tid, confirm=True)
    if not cup['placed'] or cup['size'] != n['size']:
        if b['cups'][n['size']] <= 0:
            return 'tea_cups', dict(size=n['size'], confirm=True)
        return 'tea_cup', dict(task=tid, size=n['size'])
    for item in [n['base']] + ([n['flavor']] if n['flavor'] else []) + n['toppings']:
        if item not in cup['items']:
            if stock(c)[item] <= 0:
                return 'tea_prepare', dict(item=item, qty=3, confirm=True)
            return 'tea_add', dict(task=tid, item=item)
    if cup['ice'] != n['ice']:
        return 'tea_ice', dict(task=tid, level=n['ice'])
    if cup['sugar'] != n['sugar']:
        return 'tea_sugar', dict(task=tid, level=n['sugar'])
    if b['sealer_off'] > c['turn'] and 'sealer' not in b['upgrades'] and not b['dome']:
        return 'tea_ice', dict(task=tid, level=n['ice'])
    return 'tea_seal', dict(task=tid)
