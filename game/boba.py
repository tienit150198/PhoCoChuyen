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
from . import archive as ar

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
BEAT_ACTIONS = {'cup', 'add', 'ice', 'sugar', 'config', 'check', 'seal_start', 'seal', 'serve', 'discard', 'wipe', 'event', 'clean', 'wait', 'greet', 'swap'}
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
    dict(id='pot', name='Nồi ủ trân châu', emoji='🍲', level=2, price=90, text='Trân châu nấu xong giữ dẻo thêm 2 giờ.'),
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

# ---------------------------------------------------------------- care loop (docs/superpowers/specs/2026-09-29-milk-tea-care-design.md)
DAY_MIN = 24 * 60
OPEN_MIN, CLOSE_MIN = 8 * 60, 20 * 60
LATE_MIN, OVERTIME_STEP = 23 * 60, 5  # a busy day runs over: suppliers are closed, the pots keep ageing slowly
# Made at the counter (instant, paid at cost): tea brewed in pots, pearls cooked in the pot, foam and cheese whipped.
MADE = set(BASES) | {'pearls', 'white_pearl', 'foam', 'cheese'}
# Bought from suppliers with a real delivery window: syrups, jellies, puddings… and cups.
BOUGHT = [x for x in ING if x not in MADE]
CUP_ITEMS = {'cup_M': 'M', 'cup_L': 'L'}
ORDERABLE = BOUGHT + list(CUP_ITEMS)
# Freshness of a pot/batch in shop minutes: (good until, still OK until). After that it is thrown away.
FRESH = {'pearls': (240, 360), 'white_pearl': (240, 360), **{b: (360, 540) for b in BASES}}
POT_BONUS = 120  # the warming pot keeps pearls soft two more hours
FRESH_WORD = {'pearls': ('dẻo mềm', 'hơi cứng', 'cứng'), 'white_pearl': ('dẻo mềm', 'hơi cứng', 'cứng')}
TEA_WORD = ('thơm', 'hơi chát', 'ôi')
SEALER_STICKY, SEALER_DIRTY = 12, 20  # seals since the last clean
MAX_ORDERS = 12
NOTES = {  # regulars' card: note 1 after the first cup, note 2 after the third
    'milk_tea_npc_01': [('less_sweet', '🍯', 'Kỹ chuyện đường: dặn bao nhiêu phần trăm là đúng bấy nhiêu.'),
                        ('exam', '📚', 'Đang ôn thi, hay mang về học: nắp dán phải thật kín.')],
    'milk_tea_npc_02': [('teeth', '🦷', 'Răng yếu: ít đá thôi, đá to bác không nhai được.'),
                        ('doctor', '🩺', 'Bác sĩ dặn bớt ngọt: hỏi bác trước khi pha 100%.')],
    'milk_tea_npc_03': [('photo', '📸', 'Chụp ảnh ly trước khi uống: topping xếp đẹp, nắp căng.'),
                        ('lactose', '🥛', 'Hơi kém sữa: không kem cheese, foam sữa thì hỏi lại.')],
}
ADVICE = {
    'quiet': 'Khách thưa: ủ ít trà, nấu một mẻ trân châu nhỏ thôi.',
    'students': 'Nấu thêm một mẻ trân châu buổi chiều, xếp đủ ly L.',
    'heat': 'Đặt thêm siro trái cây, đủ ly L.',
    'rain': 'Khách thưa, đơn app nhiều. Ủ trà vừa đủ, đừng nấu dư.',
    'office': 'Đơn nhiều ly: ủ sẵn trà nền trước trưa.',
    'market': 'Khách quen ghé nhiều: xem lại sổ khách quen.',
    'review': 'Lau máy dán nắp từ sớm để nắp căng đẹp.',
}
V_MARKET = dict(late='Xe ba gác của chị kẹt ở đầu chợ, tới trễ chút nha em.')
SUPPLIERS = [
    dict(id='market', name='Chợ đầu mối Mây', emoji='🧺', kind='next', cutoff=17 * 60, at=(-75, -35), factor=0.8, late=10,
         items=['lychee', 'peach', 'strawberry', 'passion', 'jelly', 'q3', 'aloe', 'coconut', 'red_bean', 'cup_M', 'cup_L'],
         note='Rẻ nhất. Đặt trước 17:00, hàng tới sáng mai trước giờ mở cửa.', voice=V_MARKET),
    dict(id='partner', name='Nhà phân phối Hạt Nắng', emoji='🚚', kind='runs',
         runs=((11 * 60, 13 * 60, 14 * 60), (15 * 60, 16 * 60 + 30, 17 * 60 + 30)), factor=1.0, late=8, items=None,
         note='Giá niêm yết. Hai chuyến: đặt trước 11:00 tới trưa, trước 15:00 tới chiều.',
         voice=dict(late='Xe giao của Hạt Nắng kẹt ở cầu Mây, bên em báo trễ khoảng một tiếng ạ.')),
    dict(id='express', name='Giao hỏa tốc Mây Xanh', emoji='⚡', kind='rush', mins=(30, 60), factor=1.35, late=12, items=None,
         note='Đắt nhất, tới trong 30–60 phút. Dùng khi hết hàng giữa ca.',
         voice=dict(late='Tài xế phải vòng tránh đoạn đường ngập, tới trễ vài chục phút ạ.')),
    dict(id='factory', name='Xưởng topping Đài Mây', emoji='✈️', kind='days', days=(2, 3), at=(60, 180), factor=0.65, late=15,
         items=['popping', 'pudding', 'flan', 'coconut', 'q3', 'aloe', 'red_bean', 'jelly', 'cup_M', 'cup_L'],
         note='Topping đóng hộp và ly in logo giá xưởng: rẻ hẳn nhưng 2–3 ngày mới tới. Đặt sớm cho cả tuần.',
         voice=dict(late='Xe tuyến về trễ một ngày vì kẹt ở trạm, xưởng xin lỗi quán.')),
]
SUP_INDEX = {x['id']: x for x in SUPPLIERS}


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
                promises=[], office=None, span=0, orders=[], order_seq=0, sealer_wear=0, cleaned=0, night=[])


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


def _raw(c: dict) -> dict:
    """The stored counter state without copying (read-only lookups on hot paths)."""
    raw = ((c.get('ext') or {}).get('data') or {}).get('boba')
    return raw if isinstance(raw, dict) else {}


def beats(c: dict) -> int:
    return max(0, c['turn'] - (_raw(c).get('turn0') or 0))


def clock_minutes(c: dict) -> int:
    """08:00 at start_day; the opening hours are spread over `span` beats (fixed at start_day, so the
    clock never runs backwards). A busy day runs into overtime: 5 minutes a beat, up to 23:00."""
    if not c['open']:
        return OPEN_MIN
    b = _raw(c)
    span = b.get('span') or max(30, (b.get('quota') or 4) * 12)
    n = beats(c)
    if n <= span:
        return OPEN_MIN + round((CLOSE_MIN - OPEN_MIN) * n / span)
    return min(LATE_MIN, CLOSE_MIN + (n - span) * OVERTIME_STEP)


def hm(minute: int) -> str:
    m = int(minute) % DAY_MIN
    return f'{m // 60:02d}:{m % 60:02d}'


def clock(c: dict) -> str:
    return hm(clock_minutes(c))


def now_abs(c: dict) -> int:
    """Shop time in absolute minutes (day × 1440 + minute). Closed: the evening of
    the day that just closed, so goods due before the next opening wait at the door."""
    if c['open']:
        return c['day'] * DAY_MIN + clock_minutes(c)
    return (c['day'] - 1) * DAY_MIN + CLOSE_MIN


def opening_abs(c: dict) -> int:
    """When a pot brewed now counts as made: now while open, else the next opening."""
    return now_abs(c) if c['open'] else c['day'] * DAY_MIN + OPEN_MIN


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
            t['src'] = dict(tier=lv, mod=mod, avoid=_avoid(c, b))
        else:
            t['src'] = dict(fixed=fit_usual(REGULARS[t['npc']]['usual'], lv))
    else:
        t['src'] = dict(tier=lv, mod=mod, avoid=_avoid(c, b))
    t['needs'] = derive(t)
    t['quoted_price'] = price(c, t['needs'])


def swap_to(c: dict, t: dict, item: str) -> str | None:
    """What the counter can offer instead of a syrup or topping it has run out of."""
    st = stock(c)
    n = t['needs']
    if ING[item]['group'] == 'flavor':
        return next((x for x in FLAVORS if x != item and unlocked(c, x) and st[x] > 0), None)
    pool = [FALLBACK.get(item)] + TOPPINGS
    return next((x for x in pool if x and x != item and x not in n['toppings'] and unlocked(c, x) and st[x] > 0), None)


def _avoid(c: dict, b: dict) -> list[str]:
    """The menu board marks what is out: walk-ins do not order a syrup or topping the shop does not have.
    (Pearls, tea and foam are made at the counter, so they are never off the menu.)"""
    st = stock(c)
    return sorted(set(b['sold_out']) | {x for x in BOUGHT if st[x] == 0})


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
def fresh_window(c: dict, item: str) -> tuple[int, int]:
    good, ok = FRESH[item]
    if item in ('pearls', 'white_pearl') and 'pot' in (_raw(c).get('upgrades') or []):
        good, ok = good + POT_BONUS, ok + POT_BONUS
    return good, ok


def band(c: dict, lot: dict, now: int | None = None) -> str:
    """'fresh' / 'tired' (hơi cứng, hơi chát: a small slip) / 'stale' (thrown away).
    Lots without a brewing time (opening stock, older saves) count as fresh today."""
    if lot['item'] not in FRESH or lot.get('made') is None:
        return 'fresh'
    good, ok = fresh_window(c, lot['item'])
    age = max(0, (now_abs(c) if now is None else now) - lot['made'])
    return 'fresh' if age <= good else 'tired' if age <= ok else 'stale'


def _lots(c: dict, item: str | None = None, now: int | None = None, usable: bool = True) -> list[dict]:
    now = now_abs(c) if now is None else now
    return [l for l in c['life']['pantry'] if (item is None or l['item'] == item) and l['expires'] >= c['day'] and l['qty'] > 0
            and (not usable or band(c, l, now) != 'stale')]


def stock(c: dict) -> dict:
    """Portions that can go into a cup right now (expired and stale batches do not count)."""
    now = now_abs(c)
    out = {k: 0 for k in ING}
    for l in _lots(c, now=now):
        if l['item'] in out:
            out[l['item']] += l['qty']
    return out


def held(c: dict) -> dict:
    """Everything on the shelf that has not expired by date (the 60-portion shelf limit)."""
    out = {k: 0 for k in ING}
    for l in c['life']['pantry']:
        if l['item'] in out and l['expires'] >= c['day']:
            out[l['item']] += l['qty']
    return out


def _fifo(l: dict) -> tuple:
    return (l.get('made') or 0, l['expires'], l['received'])


def _use(c: dict, item: str) -> tuple[int, str]:
    e = _e()
    e.need(stock(c)[item] > 0, 'Hết ' + ING[item]['name'] + '. ' + ('Nấu hoặc ủ thêm một mẻ nhé.' if item in MADE else 'Mở Kho để đặt thêm hàng nhé.'))
    now = now_abs(c)
    lot = min(_lots(c, item, now), key=_fifo)
    lot['qty'] -= 1
    return lot['unit_cost'], band(c, lot, now)


def shelf_life(c: dict, item: str) -> int:
    b = view(c)
    life = ING[item]['life']
    if 'fridge' in b['upgrades'] and ING[item]['group'] in ('topping', 'flavor'):
        life += 1
    return life


def add_lot(s: dict, c: dict, item: str, qty: int, unit_cost: int, note: str = '', made: int | None = None) -> None:
    """A new batch on the shelf. Brewed tea and cooked pearls remember when they were made."""
    from . import experiences as life
    lot = dict(id=life._id(c, 'batch'), item=item, qty=qty, unit_cost=unit_cost,
               expires=c['day'] + shelf_life(c, item) - 1, received=c['day'])
    if item in FRESH:
        lot['made'] = opening_abs(c) if made is None else made
    c['life']['pantry'].append(lot)


def _waste(c: dict, item: str, qty: int, value: int, reason: str) -> None:
    x = c['life']
    x['day_waste'] += value
    x['waste'].append(dict(day=c['day'], item=item, qty=min(60, qty), value=min(10000, value), reason=reason))
    x['waste'] = ar.last(x['waste'], 120, 'life.waste', c)


def till(minute: int, made: int) -> str:
    """'14:20', or 'hết ca' when the batch outlasts the day (it is thrown away at closing anyway)."""
    if minute // DAY_MIN > made // DAY_MIN or minute % DAY_MIN >= CLOSE_MIN:
        return 'hết ca'
    return hm(minute)


def fresh_word(item: str, bnd: str) -> str:
    words = FRESH_WORD.get(item, TEA_WORD)
    return words[('fresh', 'tired', 'stale').index(bnd)]


def _spoil(s: dict, c: dict) -> list[str]:
    """Batches past their time are thrown away (logged as waste once)."""
    now = now_abs(c)
    gone = {}
    for l in c['life']['pantry']:
        if l['qty'] > 0 and l['expires'] >= c['day'] and l['item'] in FRESH and band(c, l, now) == 'stale':
            _waste(c, l['item'], l['qty'], l['qty'] * l['unit_cost'], f"{'Trân châu' if l['item'] in ('pearls', 'white_pearl') else 'Trà'} để quá giờ ({hm(l['made'])})")
            gone[l['item']] = gone.get(l['item'], 0) + l['qty']
            l['qty'] = 0
    notes = []
    for item, n in gone.items():
        what = 'đã cứng' if item in ('pearls', 'white_pearl') else 'đã ôi'
        notes.append(f"{ING[item]['name']} {what}: bỏ {n} phần.")
        _e().log(s, c, 'stock', f"{ING[item]['name']} để quá giờ, bỏ {n} phần.")
    return notes


def _pending(b: dict, item: str) -> int:
    return sum(o['qty'] for o in b['orders'] if o['item'] == item)


def _deliver(s: dict, c: dict, b: dict, now: int | None = None) -> list[str]:
    """Orders whose time has come are unpacked onto the shelf."""
    now = now_abs(c) if now is None else now
    due = [o for o in b['orders'] if o['at'] <= now]
    if not due:
        return []
    b['orders'] = [o for o in b['orders'] if o['at'] > now]
    e = _e()
    notes = []
    for o in sorted(due, key=lambda o: o['at']):
        sup = SUP_INDEX.get(o['supplier'], SUP_INDEX['partner'])
        if o['item'] in CUP_ITEMS:
            size = CUP_ITEMS[o['item']]
            got = min(o['qty'] * CUP_PACK['qty'], CUP_CAP - b['cups'][size])
            b['cups'][size] += max(0, got)
            text = f"{o['qty'] * CUP_PACK['qty']} ly {size}"
        else:
            got = min(o['qty'], 60 - held(c)[o['item']])
            if got > 0:
                add_lot(s, c, o['item'], got, o['unit'])
            text = f"{o['qty']} phần {low(ING[o['item']]['name'])}"
        notes.append(f"📦 {sup['name']} giao tới {text}.")
        e.log(s, c, 'stock', f"Nhận hàng: {text} từ {sup['name']} lúc {hm(o['at'])}.", ref=o['id'])
    return notes


def _order_name(item: str) -> str:
    return f'ly {CUP_ITEMS[item]}' if item in CUP_ITEMS else low(ING[item]['name'])


def sells(sup: dict, item: str) -> bool:
    return sup.get('items') is None or item in sup['items']


def _place(s: dict, c: dict, b: dict, item: str, qty: int, sup: dict, cost: int, unit: int, reason: str) -> dict:
    """Pay now, get a promised window from the supplier's schedule (shared with game/inventory.py)."""
    from . import inventory as inv
    e = _e()
    if cost:
        e.money(s, c, -cost, reason, category='materials' if item in CUP_ITEMS else 'stock')
    now = now_abs(c)
    b['order_seq'] += 1
    oid = f"tea-po-{b['order_seq']}"
    sch = inv._schedule(sup, CAREER, now, f"{CAREER}|po|{c['day']}|{b['order_seq']}|{item}|{sup['id']}")
    o = dict(id=oid, item=item, qty=qty, supplier=sup['id'], cost=cost, unit=unit, placed=sch['placed'], lo=sch['lo'],
             hi=sch['hi'], at=sch['at'], late=sch['late'])
    b['orders'].append(o)
    e.log(s, c, 'stock', f"Đặt {qty} {'thùng ' if item in CUP_ITEMS else 'phần '}{_order_name(item)} từ {sup['name']}.", ref=oid)
    return o


def _when(t: int, now: int, approx: bool = False) -> str:
    from . import inventory as inv
    return inv.when(t, now, approx=approx)


def order_view(c: dict, o: dict, now: int | None = None) -> dict:
    """Public ETA of an order. The real arrival (`at`) and a delay stay hidden until due."""
    from . import inventory as inv
    now = now_abs(c) if now is None else now
    sup = SUP_INDEX.get(o['supplier'], SUP_INDEX['partner'])
    late = bool(o['late']) and now > o['hi']
    eta = o['at'] if late else int(round((o['lo'] + o['hi']) / 10.0)) * 5
    left = max(0, eta - now)
    if o['lo'] == o['hi']:
        window = hm(o['lo'])
    elif o['lo'] // DAY_MIN == o['hi'] // DAY_MIN:
        window = f"{hm(o['lo'])}–{hm(o['hi'])}"
    else:
        window = f"ngày {o['lo'] // DAY_MIN}–{o['hi'] // DAY_MIN}"
    days = eta // DAY_MIN - now // DAY_MIN
    if days <= 0:
        left_label = 'còn ' + inv._duration(left) if left else 'sắp tới'
    elif days == 1:
        left_label = 'mai, trước giờ mở cửa' if eta % DAY_MIN < OPEN_MIN else 'ngày mai'
    else:
        left_label = f'còn {days} ngày'
    span = max(1, eta - o['placed'])
    return dict(id=o['id'], item=o['item'], name=_order_name(o['item']), qty=o['qty'], cups=o['item'] in CUP_ITEMS,
                supplier=sup['id'], supplier_name=sup['name'], emoji=sup['emoji'], cost=o['cost'],
                eta_label=_when(eta, now, approx=not late), window=window, left_label=left_label,
                progress=round(min(1.0, max(0.0, (now - o['placed']) / span)), 2),
                late_note=o['late'] if late else None)


def supplier_view(c: dict, sup: dict, now: int | None = None) -> dict:
    from . import inventory as inv
    now = now_abs(c) if now is None else now
    q = inv.quote(sup, CAREER, now)
    k = sup['kind']
    window = (f"{sup['mins'][0]}–{sup['mins'][1]} phút" if k == 'rush' else 'Hai chuyến · ' + ' & '.join(hm(r[1]) for r in sup['runs']) if k == 'runs'
              else f"Sáng mai · đặt trước {hm(sup['cutoff'])}" if k == 'next' else f"{sup['days'][0]}–{sup['days'][1]} ngày")
    return dict(id=sup['id'], name=sup['name'], emoji=sup['emoji'], kind=k, factor=sup['factor'], note=sup['note'],
                items=list(sup['items']) if sup.get('items') is not None else None, window=window, late=sup['late'],
                quote=dict(label=q['label'], eta_label=q['eta_label'], day=q['day'], time=q['time']))


def warnings(c: dict) -> list[dict]:
    st = stock(c)
    b = view(c)
    out = []
    tops = [x for x in ('pearls', 'white_pearl') if unlocked(c, x)]
    if any(st[x] == 0 for x in tops):
        out.append(dict(id='pearls', text='Chưa nấu trân châu', where='stock'))
    empty = [ING[x]['name'] for x in BASES if unlocked(c, x) and st[x] == 0]
    if empty:
        out.append(dict(id='base', text='Chưa ủ trà: ' + ', '.join(empty), where='stock'))
    low = [k for k, v in b['cups'].items() if v < 5]
    if low:
        out.append(dict(id='cups', text='Sắp hết ly ' + '/'.join(low), where='stock'))
    if b['mess'] >= UNSAFE_MESS:
        out.append(dict(id='mess', text='Quầy còn vệt trà đổ', where='counter'))
    if b['sealer_wear'] >= SEALER_DIRTY:
        out.append(dict(id='sealer', text='Máy dán nắp bám keo, cần lau', where='counter'))
    return out


def sealer_state(b: dict) -> str:
    w = b['sealer_wear']
    return 'clean' if w < SEALER_STICKY else 'sticky' if w < SEALER_DIRTY else 'dirty'


def seal_zones(b: dict) -> dict:
    """Green zone of the heat sealer: glue on the plate narrows it."""
    st = sealer_state(b)
    if st == 'sticky':
        return dict(SEAL, good_lo=1.7, good_hi=2.3, burn=3.8)
    if st == 'dirty':
        return dict(SEAL, good_lo=1.9, good_hi=2.1, burn=3.4)
    return dict(SEAL)


def forecast(c: dict) -> dict:
    """Tomorrow's luck of the day is already fixed by the day number, so it can be shown tonight."""
    day = c['day'] + 1 if c['open'] else c['day']
    m = MOD_INDEX[roll_mod(day)]
    return dict(day=day, id=m['id'], title=m['title'], emoji=m['emoji'], text=m['text'], advice=ADVICE[m['id']])


def batches(c: dict, now: int | None = None) -> list[dict]:
    """Pots and pearl batches on the counter, oldest first, with their freshness."""
    now = now_abs(c) if now is None else now
    out = []
    for item in [x for x in ING if x in FRESH]:
        rows = []
        for l in sorted(_lots(c, item, now), key=_fifo):
            bnd = band(c, l, now)
            row = dict(qty=l['qty'], band=bnd, word=fresh_word(item, bnd))
            if l.get('made') is not None:
                good, ok = fresh_window(c, item)
                row.update(made=hm(l['made']), good_until=till(l['made'] + good, l['made']), ok_until=till(l['made'] + ok, l['made']))
            rows.append(row)
        if rows:
            out.append(dict(item=item, name=ING[item]['name'], emoji=ING[item]['emoji'], lots=rows))
    return out


def care(c: dict) -> list[dict]:
    """Today's care list, computed on the server (ok / warn / danger)."""
    b = view(c)
    now = now_abs(c)
    st = stock(c)
    rows = []
    cooked = [x for x in ('pearls', 'white_pearl') if unlocked(c, x)]
    for item in cooked:
        lots = sorted(_lots(c, item, now), key=_fifo)
        name = ING[item]['name']
        if not lots:
            rows.append(dict(id='pot-' + item, icon='🟤', tone='danger' if c['open'] else 'warn', text=f'{name}: chưa nấu mẻ nào. Nấu mất 20 phút.'))
            continue
        worst = band(c, lots[0], now)
        good, ok = fresh_window(c, item)
        made = lots[0].get('made')
        when = f" · dẻo tới {till(made + good, made)}" if made is not None and worst == 'fresh' else f" · cứng lúc {till(made + ok, made)}" if made is not None else ''
        rows.append(dict(id='pot-' + item, icon='🟤', tone='ok' if worst == 'fresh' else 'warn',
                         text=f"{name}: {st[item]} phần {fresh_word(item, worst)}{when}" + (' · đổ mẻ cũ hoặc nấu mẻ mới' if worst == 'tired' else '')))
    tired = [x for x in BASES if unlocked(c, x) and any(band(c, l, now) == 'tired' for l in _lots(c, x, now))]
    if tired:
        rows.append(dict(id='tea', icon='🫖', tone='warn', text='Trà ủ lâu, hơi chát: ' + ', '.join(ING[x]['name'] for x in tired) + '. Ủ bình mới nhé.'))
    empty = [ING[x]['name'] for x in BASES if unlocked(c, x) and st[x] == 0]
    if empty:
        rows.append(dict(id='tea-empty', icon='🫖', tone='warn', text='Chưa ủ: ' + ', '.join(empty) + '.'))
    wear = b['sealer_wear']
    sst = sealer_state(b)
    rows.append(dict(id='sealer', icon='⚙️', tone='ok' if sst == 'clean' else 'warn' if sst == 'sticky' else 'danger',
                     text=f'Máy dán nắp: {wear} ly từ lần lau trước' + ('' if sst == 'clean' else ' · bám keo, vùng xanh hẹp lại' if sst == 'sticky' else ' · bẩn, khó dán đẹp. Lau ngay!')))
    lowcups = [k for k, v in b['cups'].items() if v < 8 and not _pending(b, 'cup_' + k)]
    if lowcups:
        rows.append(dict(id='cups', icon='🥤', tone='warn', text='Sắp hết ly ' + '/'.join(lowcups) + '. Đặt thêm trước khi cạn.'))
    if b['orders']:
        first = min(b['orders'], key=lambda o: o['lo'])
        v = order_view(c, first, now)
        rows.append(dict(id='orders', icon='📦', tone='ok', text=f"{len(b['orders'])} đơn đang giao · sớm nhất {v['name']}: {v['eta_label']}"))
    if c['open'] and clock_minutes(c) >= 17 * 60:
        left = sum(l['qty'] for l in _lots(c, now=now) if l['item'] in FRESH)
        if left:
            rows.append(dict(id='night', icon='🌙', tone='warn', text=f'Trà ủ và trân châu không để qua đêm: {left} phần sẽ bỏ khi khép ca.'))
    if not c['open'] or clock_minutes(c) >= 14 * 60:
        f = forecast(c)
        rows.append(dict(id='tomorrow', icon=f['emoji'], tone='ok', text=f"Mai: {f['title']}. {f['advice']}"))
    return rows


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
    b['promises'] = ar.last(keep, 10, 'boba.promises', c)
    # The shop clock runs over a fixed number of beats today; goods due before opening wait at the door.
    b['span'] = max(30, b['quota'] * 12)
    arrived = _deliver(s, c, b, now=c['day'] * DAY_MIN + OPEN_MIN)
    b['night'] = ar.last(b['night'] + arrived, 8, 'boba.night', c)
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
    # Brewed tea and cooked pearls never stay overnight: what is left is logged as waste once.
    dumped = {}
    for l in c['life']['pantry']:
        if l['qty'] > 0 and l['item'] in FRESH and l['expires'] >= c['day']:
            _waste(c, l['item'], l['qty'], l['qty'] * l['unit_cost'], 'Trà ủ và trân châu không để qua đêm')
            dumped[l['item']] = dumped.get(l['item'], 0) + l['qty']
            l['qty'] = 0
    tomorrow = forecast(c)
    summary = dict(day=c['day'], served=b['served'], perfect=b['perfect'], returned=b['returned'], walkouts=b['walkouts'],
                   revenue=b['revenue'], fines=b['fines'], bonus=b['bonus'], events=b['events_today'], modifier=b['mod'],
                   level=level(c), dumped=sum(dumped.values()), sealer=b['sealer_wear'], orders=len(b['orders']),
                   tomorrow=dict(title=tomorrow['title'], emoji=tomorrow['emoji'], advice=tomorrow['advice']))
    b['history'] = ar.last(b['history'] + [summary], 14, 'boba.history', c)
    lines = []
    if dumped:
        lines.append('🌙 Cuối ca bỏ ' + ', '.join(f"{n} phần {low(ING[k]['name'])}" for k, n in dumped.items()) + ' (không để qua đêm).')
    b['night'] = lines
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
    # Time may have passed through other commands: unpack deliveries, throw out batches past their time.
    before = _deliver(s, c, b) + _spoil(s, c)
    r = _dispatch(s, c, b, name, p)
    after = []
    if r.pop('_tick', False):
        c['turn'] += 1
        after = _beat(s, c, r.pop('_active', None) or c.get('active_task'))
        after += _deliver(s, c, b) + _spoil(s, c)
    r.pop('_active', None)
    if r.pop('_arrivals', False):
        arrived = _top_up(s, c, b)
        if arrived:
            after.append('Có khách mới tới quầy: ' + ', '.join(customer_name(t) for t in arrived) + '.')
    if r.pop('_events', False):
        _maybe_event(s, c, b)
    notes = before + after
    if notes:
        r['message'] = (r.get('message', '') + ' ' + ' '.join(notes)).strip()
    return r


def _dispatch(s: dict, c: dict, b: dict, name: str, p: dict) -> dict:
    e = _e()
    need = e.need
    if name == 'prepare':
        return _prepare(s, c, p)
    if name == 'cups':
        return _order(s, c, dict(item='cup_' + str(p.get('size')), qty=1, supplier=p.get('supplier', 'partner'), confirm=p.get('confirm')))
    if name == 'order':
        return _order(s, c, p)
    if name == 'toss':
        return _toss(s, c, p)
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
    elif name == 'clean':
        need(b['sealer_wear'] > 0, 'Máy dán nắp vừa lau, còn sạch lắm.')
        n = b['sealer_wear']
        b['sealer_wear'] = 0
        b['cleaned'] = c['day']
        r = dict(message=f'Đã tháo khuôn dán, lau sạch keo sau {n} ly. Vùng dán đẹp rộng trở lại.')
    elif name == 'wait':
        need(b['orders'] or any(t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']), 'Không có gì phải chờ lúc này.')
        r = dict(message='Bạn tranh thủ lau ly, xếp lại quầy (20 phút).')
    elif name == 'greet':
        return _greet(s, c, b, p)
    elif name == 'event':
        r = _answer(s, c, b, p)
    else:
        t = _task(c, p)
        active = t['id']
        r = _station(s, c, b, t, name, p)
    r['_tick'] = not r.pop('_free', False)
    r['_active'] = active
    r['_events'] = True
    return r


def _prepare(s: dict, c: dict, p: dict) -> dict:
    """Brew a pot of tea, cook a batch of pearls or whip foam at the counter (paid at cost, ready now).
    Brewing and cooking take 20 minutes of shop time while the shop is open."""
    e = _e()
    need = e.need
    item = p.get('item')
    need(item in ING, 'Không có nguyên liệu này.')
    need(unlocked(c, item), f"{ING[item]['name']} mở ở cấp {ING[item].get('level', 1)}. Phục vụ thêm vài ly nhé.")
    need(item in MADE, f"{ING[item]['name']} mua từ nhà cung cấp: mở Kho → Đặt hàng (hỏa tốc 30–60 phút).")
    qty = e.integer(p.get('qty'), 1, 20)
    need(p.get('confirm') is True, 'Xác nhận chi phí trước khi nhập.')
    need(held(c)[item] + qty <= 60, 'Kho chứa tối đa 60 phần mỗi loại.')
    ing = ING[item]
    cost = qty * ing['cost']
    verb = 'Nấu' if item in ('pearls', 'white_pearl') else 'Ủ' if item in BASES else 'Đánh'
    e.money(s, c, -cost, f"{verb} {ing['name'].lower()}", category='stock')
    made = opening_abs(c)
    add_lot(s, c, item, qty, ing['cost'], made=made)
    if item in FRESH:
        good, ok = fresh_window(c, item)
        word = 'dẻo' if item in ('pearls', 'white_pearl') else 'ngon'
        end = till(made + ok, made)
        msg = f"{verb} xong {qty} phần {ing['name'].lower()} lúc {hm(made)}: {word} tới {till(made + good, made)}" + (f", bỏ sau {end}." if end != 'hết ca' else '.')
    else:
        msg = f"{verb} {qty} phần {ing['name'].lower()}. Dùng đến hết ngày {c['day'] + shelf_life(c, item) - 1}."
    r = dict(message=msg)
    if c['open'] and item in FRESH:
        r.update(_tick=True, _events=True)
    return r


def _order(s: dict, c: dict, p: dict) -> dict:
    """Order from a supplier: paid now, delivered at a real time of day (see SUPPLIERS)."""
    e = _e()
    need = e.need
    b = state(c)
    item = p.get('item')
    need(item in ORDERABLE, 'Mặt hàng này không đặt được. Trà nền, trân châu, foam và kem cheese làm ngay tại quầy.')
    cups = item in CUP_ITEMS
    if not cups:
        need(unlocked(c, item), f"{ING[item]['name']} mở ở cấp {ING[item].get('level', 1)}. Phục vụ thêm vài ly nhé.")
    qty = e.integer(p.get('qty'), 1, 5 if cups else 20)
    sup = SUP_INDEX.get(p.get('supplier'))
    need(sup, 'Nhà cung cấp không hợp lệ.')
    need(sells(sup, item), f"{sup['name']} không bán {_order_name(item)}. Chọn nhà khác nhé.")
    need(p.get('confirm') is True, 'Xác nhận chi phí trước khi đặt hàng.')
    need(len(b['orders']) < MAX_ORDERS, f'Đang chờ {MAX_ORDERS} đơn rồi. Đợi hàng tới bớt đã nhé.')
    if cups:
        size = CUP_ITEMS[item]
        need(b['cups'][size] + (_pending(b, item) + qty) * CUP_PACK['qty'] <= CUP_CAP, f'Chồng ly {size} không còn chỗ cho ngần ấy ly.')
        base = CUP_PACK['cost']
    else:
        need(held(c)[item] + _pending(b, item) + qty <= 60, 'Kho chứa tối đa 60 phần mỗi loại (tính cả hàng đang giao).')
        base = ING[item]['cost']
    cost = max(1, round(qty * base * sup['factor']))
    unit = min(20, max(0, round(base * sup['factor'])))
    label = f"{qty} thùng {_order_name(item)} ({qty * CUP_PACK['qty']} ly)" if cups else f"{qty} phần {_order_name(item)}"
    o = _place(s, c, b, item, qty, sup, cost, unit, f"Đặt {label} · {sup['name']}")
    v = order_view(c, o)
    return dict(message=f"Đã đặt {label}, {cost} xu. {sup['name']} giao {v['eta_label']} ({v['window']}).", eta=v)


def _toss(s: dict, c: dict, p: dict) -> dict:
    """Pour out an old pot / batch that is past its best, so the next cup uses the fresh one."""
    e = _e()
    item = p.get('item')
    e.need(item in FRESH, 'Chỉ đổ được trà ủ hoặc trân châu đã nấu.')
    now = now_abs(c)
    have = _lots(c, item, now)
    e.need(have, f"Không còn mẻ {ING[item]['name'].lower()} nào để đổ.")
    lots = [l for l in have if band(c, l, now) == 'tired']
    e.need(lots, f"{ING[item]['name']} vẫn còn {fresh_word(item, 'fresh')}, chưa cần đổ.")
    n = sum(l['qty'] for l in lots)
    _waste(c, item, n, sum(l['qty'] * l['unit_cost'] for l in lots), 'Đổ mẻ cũ trước khi hết ngon')
    for l in lots:
        l['qty'] = 0
    return dict(message=f"Đã đổ {n} phần {ING[item]['name'].lower()} {fresh_word(item, 'tired')}. Ly sau dùng mẻ mới.")


def _greet(s: dict, c: dict, b: dict, p: dict) -> dict:
    """“Như mọi khi hả?” — a regular whose card has a note feels remembered (no beat)."""
    e = _e()
    t = _task(c, p)
    e.need(not t.get('walkin') and t['npc'] in REGULARS, 'Khách này chưa có trong sổ khách quen.')
    notes = notes_for(b, t['npc'])
    e.need(notes, 'Sổ chưa ghi gì về khách này. Pha cho khách một ly trước đã.')
    e.need(not t.get('greeted'), 'Đã chào khách rồi.')
    t['greeted'] = True
    t['patience'] = min(100, t.get('patience', 100) + 8)
    c['relationships'][t['npc']] = min(100, c['relationships'].get(t['npc'], 0) + 1)
    name = customer_name(t)
    return dict(message=f"{name} cười tít: “Nhớ cả chuyện đó luôn hả?” ({notes[-1]['text']})")


def notes_for(b: dict, npc: str) -> list[dict]:
    visits = (b['notebook'].get(npc) or {}).get('visits', 0)
    rows = NOTES.get(npc, [])
    return [dict(id=k, emoji=em, text=text) for i, (k, em, text) in enumerate(rows) if visits >= (1, 3)[i]]


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
        cost, bnd = _use(c, item)
        cup['items'].append(item)
        cup['cost'] += cost
        cup['checked'] = False
        if bnd == 'tired':
            cup['tired'] = cup.get('tired', []) + [item]
        verb = {'base': 'Rót', 'flavor': 'Thêm siro', 'topping': 'Múc'}[group]
        note = f" ({fresh_word(item, 'tired')}: mẻ này để lâu rồi)" if bnd == 'tired' else ''
        return dict(message=f"{verb} {ING[item]['name'].lower() if group != 'base' else ING[item]['name']}{note}.")
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
    if name == 'swap':
        # Out of a syrup, a topping or a cup size: ask the guest to take something else (a little patience, no beat).
        item = p.get('item')
        n = t['needs']
        if item in CUP_ITEMS:
            size = CUP_ITEMS[item]
            other = 'L' if size == 'M' else 'M'
            need(n['size'] == size, 'Khách không gọi cỡ ly này.')
            need(b['cups'][size] == 0 and not (cup['placed'] and cup['size'] == size), f'Chồng ly {size} vẫn còn, không cần đổi cỡ.')
            need(b['cups'][other] > 0, 'Hết cả hai cỡ ly. Đặt hỏa tốc rồi chờ nhé.')
            _change(c, t, dict(set='size', to=other))
            if other == 'L':
                t['discount'] = min(50, t.get('discount', 0) + SIZE_L_PRICE)  # free upgrade: the shop ran out, not the guest
            t['patience'] = max(25, t.get('patience', 100) - 4)
            said = 'lên ly L, giữ giá ly M' if other == 'L' else 'xuống ly M, trả tiền ly M'
            return dict(message=f"Quầy hết ly {size}. {customer_name(t)} đồng ý {said}.", _free=True)
        need(item in BOUGHT and (item in n['toppings'] or item == n['flavor']), 'Món này không có trong ly khách gọi.')
        need(item not in cup['items'], 'Món này đã vào ly rồi.')
        need(stock(c)[item] == 0, f"Quầy vẫn còn {ING[item]['name'].lower()}, không cần mời khách đổi.")
        to = swap_to(c, t, item)
        if ING[item]['group'] == 'topping':
            need(to, 'Không còn topping nào khác để mời đổi. Đặt hỏa tốc rồi chờ nhé.')
            _change(c, t, dict(swap=item, to=to))
            said = f"thay {ING[item]['name'].lower()} bằng {ING[to]['name'].lower()}"
        else:
            _change(c, t, dict(set='flavor', to=to))
            said = f"đổi siro {ING[item]['name'].lower()} sang {ING[to]['name'].lower()}" if to else f"bỏ siro {ING[item]['name'].lower()}"
        t['patience'] = max(25, t.get('patience', 100) - 6)
        return dict(message=f"Quầy hết {ING[item]['name'].lower()}. {customer_name(t)} gật đầu {said}. Giá mới {t['quoted_price']} xu.", _free=True)
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
            took = max(0.0, now() - cup['seal_t'])
            cup['seal_t'] = None
            z = seal_zones(b)
            if took < z['loose']:
                return dict(message='Nhả tay sớm quá, màng chưa dính. Ép lại nhé.')
            quality = 'perfect' if z['good_lo'] <= took <= z['good_hi'] else 'burnt' if took > z['burn'] else 'ok'
        if quality == 'perfect' and 'sealer' in b['upgrades'] and sealer_state(b) == 'dirty':
            quality = 'ok'  # even the automatic sealer cannot make a clean film on a sticky plate
        if not dome:
            b['sealer_wear'] = min(999, b['sealer_wear'] + 1)
        cup.update(sealed=True, dome=dome, seal_q=quality, seal_t=None)
        text = {'perfect': 'Tách! Màng nắp căng bóng, kín đều — hoàn hảo.', 'ok': 'Máy dán nắp kêu “tách” — ly đã kín.',
                'burnt': 'Ép lâu quá, màng nắp hơi cháy xém. Vẫn kín, nhưng khách sẽ để ý.'}[quality]
        r = dict(message='Nắp cầu đã đậy chặt.' if dome else text, seal=quality)
        if not dome and b['sealer_wear'] in (SEALER_STICKY, SEALER_DIRTY):
            r['message'] += ' Khuôn dán bắt đầu bám keo: lau máy khi rảnh tay nhé.' if b['sealer_wear'] == SEALER_STICKY else ' Máy dán nắp bẩn rồi, lau ngay để nắp đẹp lại.'
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
    x['waste'] = ar.last(x['waste'], 120, 'life.waste', c)
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
    if [x for x in cup.get('tired', []) if x in cup['items']]:
        issues.append('tired')
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
    words = {'sugar': 'độ ngọt', 'ice': 'lượng đá', 'seal': 'nắp dán', 'late': 'giờ giao', 'tired': 'độ tươi'}
    note = 'Đúng từng lớp: trà, topping, đường và đá.' if not issues else 'Ly được nhận, nhưng ' + ' và '.join(words[x] for x in issues) + ' chưa như ý.'
    e.task_done(s, c, t, reward, f'Đã nhận ly {low(ING[t["needs"]["base"]]["name"])} từ quầy. {note}')
    post = next((f for f in c['feed'] if f.get('source') == t['id'] and f.get('kind') == 'review'), None)
    if post and rest:
        # One customer, one review: earlier cups of a group wait for the last one.
        ar.record([post], 'feed.retracted', c)
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
    extra = []
    if not t.get('walkin') and t['npc'] in REGULARS:
        book = b['notebook'].get(t['npc'])
        known = len(notes_for(b, t['npc']))
        b['notebook'][t['npc']] = dict(usual=copy.deepcopy(t['needs']), visits=(book or {}).get('visits', 0) + 1, day=c['day'])
        learned = notes_for(b, t['npc'])
        if len(learned) > known:
            extra.append(f"📒 Sổ khách quen ghi thêm: {learned[-1]['text']}")
        if t.get('greeted') and not issues:
            e.money(s, c, 2, 'Khách quen vui vì được nhớ', t['id'], category='tip')
            b['bonus'] += 2
            extra.append('Khách quen vui vì được nhớ: +2 xu.')
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
    if 'tired' in issues:
        pearls = any(x in ('pearls', 'white_pearl') for x in cup.get('tired', []))
        cq.slip(t, 'tired', 1, 'Trân châu hơi cứng, nhai mỏi cả hàm.' if pearls else 'Trà ủ lâu quá nên hơi chát.',
                'trân châu để lâu, hơi cứng' if pearls else 'trà ủ lâu, hơi chát')


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
        return [dict(id='cook', label='Nấu gấp một nồi', cost=16, hint='8 phần, khách chờ thêm một lúc'),
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
                dict(id='refuse', label='Trả cả thùng, hẹn giao lại', hint=f"Đặt lại đủ {f['billed']} phần chuyến sau của Hạt Nắng, trả {f['billed'] * f['cost']} xu nếu đủ tiền")]
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
        st['choices'] = ar.last(st['choices'] + [choice], 3, 'boba.story_choices', c)
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
            sup = SUP_INDEX['partner']
            cost = f['billed'] * f['cost']
            if c['money'] >= cost and held(c)[f['item']] + _pending(b, f['item']) + f['billed'] <= 60 and len(b['orders']) < MAX_ORDERS:
                o = _place(s, c, b, f['item'], f['billed'], sup, cost, f['cost'], 'Đặt lại ' + ING[f['item']]['name'])
                v = order_view(c, o)
                result = f"Bạn trả thùng. Bình hẹn giao lại đủ {f['billed']} phần theo chuyến Hạt Nắng: {v['eta_label']}."
                eff.append(f'-{cost} xu · tới {v["eta_label"]}')
            else:
                result = 'Bạn trả thùng, hẹn Bình giao lại đủ số khi quán đặt đơn mới. Kho vẫn đang thiếu.'
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
    b['ev_history'] = ar.last(b['ev_history'] + [dict(kind=k, choice=choice, day=c['day'])], 30, 'boba.events', c)
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
                             visits=entry['visits'] if entry else 0, notes=notes_for(b, npc),
                             next_note=next((n for n in (1, 3) if (entry['visits'] if entry else 0) < n), None)))
    left = max(0, b['quota'] - b['arrived']) + len([t for t in active])
    now = now_abs(c)
    tired = {}
    for l in _lots(c, now=now):
        if band(c, l, now) == 'tired':
            tired[l['item']] = tired.get(l['item'], 0) + l['qty']
    express = SUP_INDEX['express']
    care_loop = dict(
        now=dict(time=hm(now), day=now // DAY_MIN, is_open=bool(c['open']), open=hm(OPEN_MIN), close=hm(CLOSE_MIN)),
        orders=[order_view(c, o, now) for o in sorted(b['orders'], key=lambda o: (o['lo'], o['id']))],
        suppliers=[supplier_view(c, x, now) for x in SUPPLIERS], batches=batches(c, now), care=care(c), tomorrow=forecast(c),
        night=list(b['night']), made=sorted(MADE), orderable=list(ORDERABLE),
        pending={k: _pending(b, k) for k in ORDERABLE + list(BASES) if _pending(b, k)},
        express=dict(eta=supplier_view(c, express, now)['quote']['eta_label'], factor=express['factor']),
        sealer=dict(wear=b['sealer_wear'], state=sealer_state(b), sticky=SEALER_STICKY, dirty=SEALER_DIRTY, cleaned=b['cleaned']))
    return _clean(dict(
        cups=b['cups'], cup_pack=CUP_PACK, mess=b['mess'], level=lv, total=b['total'], next_tier=next_tier(c), clock=clock(c), beats=beats(c), rate=rate(c),
        modifier=dict(id=mod['id'], title=mod['title'], emoji=mod['emoji'], text=mod['text']),
        quota=b['quota'], arrived=b['arrived'], left=left if c['open'] else None, served=b['served'], perfect=b['perfect'],
        returned=b['returned'], walkouts=b['walkouts'], revenue=b['revenue'], fines=b['fines'], streak=c['life'].get('streak', 0),
        best_streak=c['life'].get('best_streak', 0),
        stations=[dict(id=x['id'], group=x['group'], level=x.get('level', 1), unlocked=x.get('level', 1) <= lv, stock=st[x['id']],
                       tired=tired.get(x['id'], 0), made=x['id'] in MADE, fresh=x['id'] in FRESH) for x in data.INGREDIENTS],
        upgrades=[dict(u, owned=u['id'] in b['upgrades'], ready=lv >= u['level']) for u in UPGRADES],
        event=ev_view, notebook=notebook, warnings=warnings(c), history=b['history'][-7:], sold_out=b['sold_out'],
        sealer_off=b['sealer_off'] > c['turn'] and 'sealer' not in b['upgrades'], dome=b['dome'],
        office=dict(count=b['office']['count'], done=b['office']['done'], deadline_in=max(0, b['office']['deadline'] - c['turn']), bonus=b['office']['bonus']) if b.get('office') else None,
        story_step=b['story']['step'], prices=dict(base=BASE_PRICE, flavor=FLAVOR_PRICE, topping=TOPPING_PRICE, size_l=SIZE_L_PRICE),
        sugars=list(SUGARS), ices=list(ICES), seal=seal_zones(b), app_fee=APP_FEE_PCT, turn=c['turn'], **care_loop))


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
               (ch['set'] == 'sugar' and type(ch.get('to')) is int and ch['to'] in SUGARS) or \
               (ch['set'] == 'flavor' and 'to' in ch and (ch['to'] is None or ch['to'] in FLAVORS))
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
    for k in ('usual', 'vip', 'office', 'combo', 'walked', 'greeted'):
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
    tired = cup.get('tired', [])
    need(isinstance(tired, list) and len(tired) == len(set(tired)) and all(k in FRESH and k in cup['items'] for k in tired), 'Độ tươi trong ly sai.')
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
    for k in ('span', 'order_seq', 'cleaned'):
        e.integer(b[k], 0, 10**9)
    e.integer(b['sealer_wear'], 0, 999)
    need(isinstance(b['night'], list) and len(b['night']) <= 8, 'Ghi chú đầu ngày sai.')
    for line in b['night']:
        e.clean_text(line, 300)
    need(isinstance(b['orders'], list) and len(b['orders']) <= MAX_ORDERS, 'Đơn đặt hàng sai.')
    ids = set()
    for o in b['orders']:
        need(isinstance(o, dict) and set(o) == {'id', 'item', 'qty', 'supplier', 'cost', 'unit', 'placed', 'lo', 'hi', 'at', 'late'}, 'Đơn đặt hàng thiếu dữ liệu.')
        e.clean_text(o['id'], 40)
        need(o['id'] not in ids, 'Trùng mã đơn đặt hàng.')
        ids.add(o['id'])
        need(o['item'] in ING or o['item'] in CUP_ITEMS, 'Mặt hàng đặt sai.')
        need(o['supplier'] in SUP_INDEX, 'Nhà cung cấp sai.')
        e.integer(o['qty'], 1, 5 if o['item'] in CUP_ITEMS else 20)
        e.integer(o['cost'], 0, 10000)
        e.integer(o['unit'], 0, 20)
        for k in ('placed', 'lo', 'hi', 'at'):
            e.integer(o[k], 0, 10**9)
        need(o['placed'] <= o['lo'] <= o['hi'], 'Giờ giao hẹn sai.')
        if o['late'] is None:
            need(o['lo'] <= o['at'] <= o['hi'], 'Giờ giao sai.')
        else:
            e.clean_text(o['late'], 200)
            need(o['at'] > o['hi'], 'Giờ giao trễ sai.')
    for lot in c['life']['pantry']:
        if 'made' in lot:
            need(lot['item'] in FRESH, 'Chỉ trà ủ và trân châu mới ghi giờ làm.')
            e.integer(lot['made'], 0, 10**9)
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
            if b['cups']['L' if n['size'] == 'M' else 'M'] > 0 and not cup['items']:
                return 'tea_swap', dict(task=tid, item='cup_' + n['size'])
            if _pending(b, 'cup_' + n['size']):
                return 'tea_wait', {}
            return 'tea_order', dict(item='cup_' + n['size'], qty=1, supplier='express', confirm=True)
        return 'tea_cup', dict(task=tid, size=n['size'])
    for item in [n['base']] + ([n['flavor']] if n['flavor'] else []) + n['toppings']:
        if item not in cup['items']:
            if stock(c)[item] <= 0:
                if item in MADE:
                    return 'tea_prepare', dict(item=item, qty=3, confirm=True)
                if (item in n['toppings'] and swap_to(c, t, item)) or item == n['flavor']:
                    return 'tea_swap', dict(task=tid, item=item)
                if _pending(b, item):
                    return 'tea_wait', {}
                return 'tea_order', dict(item=item, qty=3, supplier='express', confirm=True)
            return 'tea_add', dict(task=tid, item=item)
    if cup['ice'] != n['ice']:
        return 'tea_ice', dict(task=tid, level=n['ice'])
    if cup['sugar'] != n['sugar']:
        return 'tea_sugar', dict(task=tid, level=n['sugar'])
    if b['sealer_off'] > c['turn'] and 'sealer' not in b['upgrades'] and not b['dome']:
        return 'tea_ice', dict(task=tid, level=n['ice'])
    return 'tea_seal', dict(task=tid)
