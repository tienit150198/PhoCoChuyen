"""🌟 Trang trại — the farm's new garden, pens and upgrades (Nông trại mới, 10/2026).

Why (production, 01–06/10): 57% of farm taps were chores on the six beds (tưới 10 370, nhổ cỏ 4 920,
thăm sâu 4 214, khơi rãnh 2 529) for a median 4 deliveries a day; 27% of farm players left on a day
without one delivery and only 16% came back a second day. Nothing grew while you watched, and there
was nothing to buy or reach. This layer adds what a farm game is about, on top of the order loop:

* Vườn mới: plots that grow on the server's wall clock (minutes, also while you are away), with
  Vietnamese crops (ớt, lúa, dưa hấu, bí ngô, thanh long, dâu tây, xoài, cà phê). Each planting gets
  its own care needs, fixed when it is sown (the crop's own step, plus a thirsty day, a storm, pests),
  shown as one tap each when they come up. A missed need costs yield and the grade.
* Chuồng: vịt (trứng vịt), bò sữa (sữa), heo (raised over four feeds, then sold).
* Bán: at the chợ (price falls after DEPTH units a day per product) or to buyers with their own fussy
  demands (grade A only, VietGAP stamp, a deadline); some haggle, and whether they walk away when you
  hold your price depends on a trait you cannot see.
* Nâng cấp (xu sinks): more plots, drip irrigation (also keeps the six beds watered), greenhouse,
  mini tractor (one tap for the whole garden), barn, VietGAP.
* Cấp trang trại, the "Nông dân giỏi" title, records; rare moments: trái vàng, bí khổng lồ, Hội mùa.

State: c['ext'][KEY] (optional; saves without it are fine, older builds ignore it: ext is checked as a
superset of its template keys and farm.validate_data reads only its own keys). Nothing here touches the
order tasks, the beds' schema or the cold room, so a rollback to 1.9.3 loads every save this writes.
All randomness is seeded by the planting/order serial; all time is kit.now() (tests set kit.clock).
"""
from __future__ import annotations

from . import kit

KEY = 'farm_plus'
VERSION = 1
MAX_PLOTS = 6
START_PLOTS = 2
PLOT_COST = (80, 150, 250, 400)          # the 3rd, 4th, 5th and 6th plot
DEPTH = 40                               # units of one product the chợ holds at most (sold, not yet absorbed)
SLIP = 8                                 # every SLIP units it still holds take 10% off the next ones (floor 60%)
ABSORB = 60                              # the chợ absorbs one unit of each product every ABSORB seconds
B_PCT, GAP_PCT, FEST_PCT = 60, 120, 125
MISS_PCT, OVER_PCT = 30, 60              # yield lost per missed need; yield kept when over-ripe
GREEN_SPEED = 85                         # % of the growing time under the greenhouse
ORDERS_OPEN = 3
STORE_CAP = 240
GOLD_P, GOLD_PAY = 0.03, 25
GIANT_P = 0.08

CARES = {
    'water': dict(icon='💧', label='Tưới gốc', done='Tưới đẫm gốc, đất mát lại.'),
    'pest': dict(icon='🐛', label='Bắt sâu', done='Bắt sạch sâu bằng tay, không cần thuốc.'),
    'cover': dict(icon='⛺', label='Che mưa', done='Căng bạt che, mưa giông không quật được cây.'),
    'stake': dict(icon='🪵', label='Cắm cọc', done='Cắm cọc đỡ cây ớt, trái không rụng.'),
    'flood': dict(icon='🌊', label='Dẫn nước', done='Mở bờ dẫn nước vào ruộng, lúa trổ đều.'),
    'straw': dict(icon='🌾', label='Lót rơm', done='Lót rơm dưới trái dưa, không thối đáy.'),
    'pinch': dict(icon='✋', label='Bấm ngọn', done='Bấm ngọn bí để dồn sức nuôi trái.'),
    'light': dict(icon='💡', label='Thắp đèn', done='Thắp đèn đêm cho thanh long ra hoa trái vụ.'),
    'net': dict(icon='🕸️', label='Che lưới', done='Che lưới, chim hết mổ dâu.'),
    'bag': dict(icon='🛍️', label='Bao trái', done='Bao từng trái xoài, ruồi vàng hết chích.'),
    'prune': dict(icon='✂️', label='Tỉa cành', done='Tỉa cành tăm, cà phê ra bông đều.'),
}

# mins: real minutes to ripe; seed: xu per planting; qty: units at grade A; price: xu a unit at the chợ.
CROPS = [
    dict(id='ot', name='Ớt hiểm', emoji='🌶️', unit='kg', mins=6, seed=3, qty=3, price=2, xp=2, level=1, care='stake', pest=60),
    dict(id='lua', name='Lúa', emoji='🌾', unit='kg', mins=15, seed=4, qty=6, price=2, xp=3, level=1, care='flood', pest=30),
    dict(id='dua', name='Dưa hấu', emoji='🍉', unit='trái', mins=25, seed=6, qty=2, price=9, xp=4, level=2, care='straw', pest=25),
    dict(id='bi', name='Bí ngô', emoji='🎃', unit='trái', mins=30, seed=6, qty=2, price=10, xp=4, level=2, care='pinch', pest=25),
    dict(id='tl', name='Thanh long', emoji='🐉', unit='trái', mins=45, seed=10, qty=5, price=5, xp=6, level=3, care='light', pest=20),
    dict(id='dau', name='Dâu tây', emoji='🍓', unit='hộp', mins=20, seed=8, qty=4, price=5, xp=5, level=1, care='net', pest=35, green=True),
    dict(id='xoai', name='Xoài cát', emoji='🥭', unit='trái', mins=60, seed=12, qty=6, price=6, xp=8, level=4, care='bag', pest=30),
    dict(id='cafe', name='Cà phê', emoji='☕', unit='kg', mins=120, seed=15, qty=4, price=14, xp=12, level=5, care='prune', pest=20),
]
CROP = {x['id']: x for x in CROPS}
# In season (farm.SEASONS ids): +1 unit at harvest.
IN_SEASON = dict(spring=('lua', 'dau'), summer=('dua', 'xoai', 'tl'), autumn=('bi', 'ot'), winter=('cafe', 'dau'))

ANIMALS = [
    dict(id='duck', name='Đàn vịt', emoji='🦆', cost=40, barn=False, feed=2, mins=20, product='trung_vit', qty=6, food='lúa lép'),
    dict(id='cow', name='Bò sữa', emoji='🐄', cost=150, barn=True, feed=4, mins=30, product='sua', qty=4, food='cỏ voi'),
    dict(id='pig', name='Heo thịt', emoji='🐖', cost=30, barn=True, feed=3, mins=15, feeds=4, sell=80, food='cám gạo'),
]
ANIMAL = {x['id']: x for x in ANIMALS}
PRODUCTS = {**{x['id']: dict(name=x['name'], emoji=x['emoji'], unit=x['unit'], price=x['price']) for x in CROPS},
            'trung_vit': dict(name='Trứng vịt', emoji='🥚', unit='quả', price=1),
            'sua': dict(name='Sữa bò tươi', emoji='🥛', unit='lít', price=3)}

UPGRADES = [
    dict(id='drip', name='Tưới nhỏ giọt', emoji='💧', cost=180, text='Vườn mới hết khát; 6 luống rau tự giữ ẩm.'),
    dict(id='tractor', name='Máy cày mini', emoji='🚜', cost=260, text='Gieo, chăm, thu cả vườn một chạm.'),
    dict(id='barn', name='Chuồng trại', emoji='🏚️', cost=220, text='Nuôi bò sữa và heo.'),
    dict(id='green', name='Nhà kính', emoji='🏠', cost=350, text='Hết sợ mưa bão, lớn nhanh 15%, trồng dâu tây.'),
    dict(id='gap', name='Chứng nhận VietGAP', emoji='🏅', cost=450, need_a=15, text='Giá bán +20%, mở đơn quán chay.'),
]
UPGRADE = {x['id']: x for x in UPGRADES}

LEVELS = (0, 25, 70, 140, 240, 380, 560, 800, 1100, 1500)
TITLES = ((10, '👑 Vua nông trại'), (8, '🌾 Lão nông tri điền'), (5, '🏅 Nông dân giỏi'), (3, '💪 Nông dân chăm chỉ'), (1, '🌱 Nông dân tập sự'))

# Buyers: who, what they take, their fussy line. Hidden trait per order (see _order).
BUYERS = [
    dict(id='boba', name='Tiệm trà sữa Boba', emoji='🧋', want=('sua', 'dau'), grade='A',
         lines=('“Sữa với dâu cho món trà sữa dâu nha. Loại B pha lên màu xỉn, khách chê là chị trả hết.”',
                '“Dâu phải đỏ đều, sữa phải thơm. Chị nếm từng hộp đó em.”')),
    dict(id='bakery', name='Lò bánh Bếp Mây', emoji='🥐', want=('trung_vit', 'bi'), grade='A',
         lines=('“Trứng vịt quả to cho bánh bông lan trứng muối, quả nào lấm phân là chị trả.”',
                '“Bí ngô làm bánh bí, trái phải nặng tay, gõ nghe bồm bộp mới lấy.”')),
    dict(id='che', name='Quán chè cô Ba', emoji='🍧', want=('dua', 'tl'), grade='A',
         lines=('“Dưa phải đỏ ruột, thanh long ruột đỏ càng tốt. Cô bổ thử một trái đó nghen.”',
                '“Khách quán cô kén lắm, trái nào nhạt là cô gửi lại liền.”')),
    dict(id='comtam', name='Cơm tấm Sài Gòn', emoji='🍚', want=('lua', 'ot'), grade='any',
         lines=('“Gạo với ớt cho quán, loại nào cũng được miễn đủ cân, anh cân lại đó.”',
                '“Ớt cay xé lưỡi nha em, ớt hiền là khách anh chửi anh.”')),
    dict(id='cafe', name='Cà phê Đồi Gió', emoji='☕', want=('cafe', 'sua'), grade='A',
         lines=('“Cà phê hạt chín đỏ, hái xanh là anh biết liền. Sữa tươi cho món bạc xỉu.”',
                '“Anh rang mộc, hạt nào lép là cả mẻ hỏng, lựa kỹ giùm anh.”')),
    dict(id='fruit', name='Sạp trái cây chị Mai', emoji='🍍', want=('xoai', 'tl', 'dau'), grade='A',
         lines=('“Trái đẹp chị mới bày sạp được, trầy một vết là khách lựa ra.”',
                '“Xoài cát phải thơm cuống, chị ngửi từng trái nha.”')),
    dict(id='chay', name='Quán chay Lá Xanh', emoji='🥗', want=('ot', 'dau', 'lua', 'tl'), grade='A', gap=True,
         lines=('“Anh Phong chỉ lấy hàng có tem VietGAP, menu quán ghi rõ rồi.”',
                '“Không tem VietGAP là anh không nhận, đừng năn nỉ nha em.”')),
    dict(id='tuan', name='Anh Tuấn thương lái', emoji='🚚', want=tuple(PRODUCTS), grade='any', haggle=True,
         lines=('“Có bao nhiêu anh gom bấy nhiêu, mà giá phải mềm mềm nghe em.”',
                '“Loại B cũng lấy, tiền mặt liền, nhưng bớt chút đỉnh nha.”')),
]
BUYER = {x['id']: x for x in BUYERS}
TRAITS = ('fair', 'fair', 'tip', 'haggle_bluff', 'haggle_firm')   # hidden; Anh Tuấn always haggles
HAGGLE_PCT = 85
TIP_PCT = 110


# ---------------------------------------------------------------- state
def initial(now: int) -> dict:
    return dict(v=VERSION, at=now, seq=0, xp=0, plots=[None] * START_PLOTS, pens={}, store={}, ups=[], orders=[],
                sold=dict(at=now, n={}), stats=dict(harvests=0, a=0, gold=0, giant=0, pumpkin=0, melon=0, orders=0, income=0))


def get(c: dict) -> dict | None:
    return c['ext'].get(KEY)


def _now() -> int:
    return int(kit.now())


def level_of(xp: int) -> int:
    return sum(1 for v in LEVELS if xp >= v)


def title(lv: int) -> str:
    return next(t for need, t in TITLES if lv >= need)


def _season(c: dict) -> str:
    from . import farm
    return farm.season(c['day'])['id']


def _weather(c: dict) -> str:
    from . import farm
    return farm._weather(c['day'])['id']


def festival(c: dict) -> bool:
    """Hội mùa: the last day of every season."""
    from . import farm
    return farm._season_day(c['day']) == farm.SEASON_DAYS


def _has(g: dict, up: str) -> bool:
    return up in g['ups']


def _unlocked(g: dict, crop: dict) -> str | None:
    """Why this crop cannot be sown yet (None: it can)."""
    if crop.get('green') and not _has(g, 'green'):
        return 'Cần nhà kính'
    if level_of(g['xp']) < crop['level']:
        return f'Mở ở cấp {crop["level"]}'
    return None


# ---------------------------------------------------------------- plots
def _dur(g: dict, crop: dict) -> int:
    return crop['mins'] * 60 * (GREEN_SPEED if _has(g, 'green') else 100) // 100


def _needs_for(g: dict, crop: dict, serial: int, sky: str) -> list:
    """The care a planting will ask for, fixed when it is sown: [kind, percent of growth it comes up at]."""
    r = kit.rng('farm_plus', 'needs', serial, crop['id'])
    out = [[crop['care'], 30 + r.randrange(25)]]
    if sky in ('hot', 'sun', 'wind') and not _has(g, 'drip'):
        out.append(['water', 40 + r.randrange(30)])
    if sky in ('rain', 'cloud') and not _has(g, 'green') and r.randrange(100) < (60 if sky == 'rain' else 25):
        out.append(['cover', 35 + r.randrange(40)])
    if r.randrange(100) < crop['pest']:
        out.append(['pest', 20 + r.randrange(55)])
    return sorted(out, key=lambda n: n[1])


def _pct(p: dict, now: int) -> int:
    return max(0, min(100, (now - p['at']) * 100 // max(1, p['dur'])))


def _keep(p: dict) -> int:
    """Seconds a ripe crop stays at its best."""
    return max(3600, 3 * p['dur'])


def _stage(p: dict, now: int) -> str:
    left = p['at'] + p['dur'] - now
    if left > 0:
        pct = _pct(p, now)
        return 'seed' if pct < 20 else 'sprout' if pct < 55 else 'grow'
    return 'ripe' if -left <= _keep(p) else 'over'


def _due(p: dict, now: int) -> list:
    """Needs that have come up and are not done yet."""
    pct = _pct(p, now)
    return [k for k, at in p['needs'] if at <= pct and k not in p['done']]


def _plant(s: dict, c: dict, g: dict, i: int, crop: dict, now: int) -> None:
    g['seq'] += 1
    serial = g['seq']
    kit.money(s, c, -crop['seed'], f'Mua giống {crop["name"].lower()} (vườn mới)', f'G{i + 1}', 'stock')
    g['plots'][i] = dict(crop=crop['id'], at=now, dur=_dur(g, crop), n=serial, needs=_needs_for(g, crop, serial, _weather(c)), done=[])


def _harvest(s: dict, c: dict, g: dict, i: int, now: int) -> str:
    p = g['plots'][i]
    crop = CROP[p['crop']]
    stage = _stage(p, now)
    kit.need(stage in ('ripe', 'over'), f'{crop["name"]} chưa chín, còn {_left(p["at"] + p["dur"] - now)}.')
    missed = [k for k, _ in p['needs'] if k not in p['done']]
    pct = max(30, 100 - MISS_PCT * len(missed))
    if stage == 'over':
        pct = pct * OVER_PCT // 100
    base = crop['qty'] + (1 if crop['id'] in IN_SEASON.get(_season(c), ()) else 0)
    qty = max(1, (base * pct + 50) // 100)
    grade = 'A' if not missed and stage == 'ripe' else 'B'
    room = STORE_CAP - _store_units(g)
    kit.need(room >= qty, f'Kho trang trại đầy ({_store_units(g)}/{STORE_CAP}). Bán bớt ở chợ hoặc giao đơn trước nhé.')
    _put(g, crop['id'], grade, qty)
    st = g['stats']
    st['harvests'] += 1
    st['a'] += grade == 'A'
    gain = crop['xp'] * (2 if grade == 'A' else 1) // 2 + len(p['done'])
    g['xp'] += gain
    r = kit.rng('farm_plus', 'harvest', p['n'], crop['id'])
    extra = []
    if crop['id'] in ('bi', 'dua'):
        giant = crop['id'] == 'bi' and grade == 'A' and r.random() < GIANT_P
        kg = r.randint(20, 60) if giant else r.randint(4, 9) if crop['id'] == 'bi' else r.randint(3, 7)
        key = 'pumpkin' if crop['id'] == 'bi' else 'melon'
        record = kg > st[key]
        st[key] = max(st[key], kg)
        if giant:
            prize = 20 + kg // 2
            st['giant'] += 1
            st['income'] += prize
            kit.money(s, c, prize, f'Giải bí khổng lồ {kg} kg (hội thi xã)', f'G{i + 1}', 'revenue')
            extra.append(f'🎃 BÍ KHỔNG LỒ {kg} kg! Hội thi xã trao giải {prize} xu.')
        elif record:
            extra.append(f'🏆 Kỷ lục mới: trái {kg} kg!')
    if grade == 'A' and r.random() < GOLD_P:
        st['gold'] += 1
        st['income'] += GOLD_PAY
        kit.money(s, c, GOLD_PAY, f'Trái vàng hiếm: {crop["name"].lower()}', f'G{i + 1}', 'revenue')
        extra.append(f'🌟 TRÁI VÀNG hiếm! Ông Sáu sưu tầm trả {GOLD_PAY} xu.')
    g['plots'][i] = None
    kit.metric(c, 'fp_harvests')
    head = f'Thu {qty} {crop["unit"]} {crop["name"].lower()} loại {grade}'
    why = (' (bỏ lỡ: ' + ', '.join(CARES[k]['label'].lower() for k in missed) + ')') if missed else ''
    why += ' (để quá lứa)' if stage == 'over' else ''
    return f'{crop["emoji"]} {head}{why} · +{gain} điểm nông.' + (' ' + ' '.join(extra) if extra else '')


def _left(sec: int) -> str:
    sec = max(0, int(sec))
    if sec < 60:
        return f'{sec} giây'
    m = -(-sec // 60)
    return f'{m} phút' if m < 60 else f'{m // 60} giờ {m % 60} phút' if m % 60 else f'{m // 60} giờ'


# ---------------------------------------------------------------- store + market
def _store_units(g: dict) -> int:
    return sum(a + b for a, b in g['store'].values())


def _put(g: dict, pid: str, grade: str, qty: int) -> None:
    a, b = g['store'].get(pid, [0, 0])
    g['store'][pid] = [a + qty, b] if grade == 'A' else [a, b + qty]


def _take(g: dict, pid: str, grade: str, qty: int) -> None:
    a, b = g['store'][pid]
    a, b = (a - qty, b) if grade == 'A' else (a, b - qty)
    if a or b:
        g['store'][pid] = [a, b]
    else:
        del g['store'][pid]


def _unit_tenths(c: dict, g: dict, pid: str, grade: str) -> int:
    v = PRODUCTS[pid]['price'] * 10
    if grade == 'B':
        v = v * B_PCT // 100
    if _has(g, 'gap'):
        v = v * GAP_PCT // 100
    if festival(c):
        v = v * FEST_PCT // 100
    return v


def _absorbed(g: dict, now: int) -> dict:
    """What the chợ still holds of each product: sales fade one unit per ABSORB seconds (wall clock, like the garden)."""
    sd = g['sold']
    k = max(0, now - sd['at']) // ABSORB
    if not k:
        return dict(sd['n'])
    return {pid: v - k for pid, v in sd['n'].items() if v > k}


def _sold(g: dict, now: int) -> dict:
    n = _absorbed(g, now)
    if n != g['sold']['n'] or now - g['sold']['at'] >= ABSORB:
        g['sold'] = dict(at=now - (now - g['sold']['at']) % ABSORB, n=n)
    return g['sold']['n']


def sale(c: dict, g: dict, pid: str, grade: str, qty: int, sold: int) -> int:
    unit = _unit_tenths(c, g, pid, grade)
    t = sum(unit * max(60, 100 - 10 * ((sold + k) // SLIP)) // 100 for k in range(qty))
    return max(1, (t + 5) // 10)


# ---------------------------------------------------------------- orders
def _available(g: dict) -> list:
    out = [x['id'] for x in CROPS if _unlocked(g, x) is None]
    for a in ANIMALS:
        if a['id'] in g['pens'] and a.get('product'):
            out.append(a['product'])
    return out


def _refill(c: dict, g: dict, now: int) -> None:
    g['orders'] = [o for o in g['orders'] if o['until'] > now]
    have = set(_available(g))
    while len(g['orders']) < ORDERS_OPEN:
        g['seq'] += 1
        r = kit.rng('farm_plus', 'order', g['seq'], c['day'])
        pool = [b for b in BUYERS if set(b['want']) & have and (not b.get('gap') or _has(g, 'gap'))
                and b['id'] not in {o['buyer'] for o in g['orders']}]
        if not pool:
            return
        b = pool[r.randrange(len(pool))]
        want = sorted(set(b['want']) & have)
        r.shuffle(want)
        items = {}
        for pid in want[:1 + (len(want) > 1 and r.random() < .4)]:
            unit = CROP[pid]['qty'] if pid in CROP else ANIMAL['duck']['qty'] if pid == 'trung_vit' else ANIMAL['cow']['qty']
            items[pid] = max(2, unit + r.randrange(unit + 1))
        prem = (r.randint(140, 170) if b['grade'] == 'A' else r.randint(115, 130)) + (15 if b.get('gap') else 0)
        pay = max(3, sum(PRODUCTS[k]['price'] * q for k, q in items.items()) * prem // 100)
        trait = 'haggle_bluff' if b.get('haggle') and r.random() < .5 else 'haggle_firm' if b.get('haggle') else TRAITS[r.randrange(len(TRAITS))]
        g['orders'].append(dict(id=f'D{g["seq"]}', buyer=b['id'], items=items, pay=pay, until=now + 60 * r.randint(40, 90),
                                line=r.randrange(len(b['lines'])), trait=trait, asked=False))


def _fits(g: dict, o: dict) -> str | None:
    """Why the store cannot fill this order now (None: it can)."""
    b = BUYER[o['buyer']]
    for pid, q in o['items'].items():
        a, bb = g['store'].get(pid, [0, 0])
        have = a if b['grade'] == 'A' else a + bb
        if have < q:
            p = PRODUCTS[pid]
            return f'Thiếu {q - have} {p["unit"]} {p["name"].lower()}' + (' loại A' if b['grade'] == 'A' else '')
    return None


def _deliver(s: dict, c: dict, g: dict, o: dict, deal) -> dict:
    b = BUYER[o['buyer']]
    why = _fits(g, o)
    kit.need(why is None, why or '')
    if o['trait'].startswith('haggle') and not o['asked']:
        o['asked'] = True
        return dict(message=f'{b["emoji"]} {b["name"]}: “Hàng ok đó, mà bớt {100 - HAGGLE_PCT}% nha em, {o["pay"] * HAGGLE_PCT // 100} xu thôi?”', haggle=True)
    pay = o['pay']
    note = ''
    if o['asked']:
        deal = kit.one_of(deal, ('yes', 'no'), 'Chọn bớt giá hay giữ giá nhé.')
        if deal == 'yes':
            pay = pay * HAGGLE_PCT // 100
            note = ' (đã bớt giá)'
        elif o['trait'] == 'haggle_firm':
            g['orders'].remove(o)
            return dict(message=f'{b["emoji"]} {b["name"]} lắc đầu: “Vậy thôi, anh qua vườn khác.” Hàng vẫn còn trong kho.', refused=True)
        else:
            note = ' (giữ giá thành công 😎)'
    elif o['trait'] == 'tip':
        pay = pay * TIP_PCT // 100
        note = ' (khách vui, bo thêm)'
    for pid, q in o['items'].items():
        left = q
        for grade in (('B', 'A') if b['grade'] == 'any' else ('A',)):
            have = g['store'].get(pid, [0, 0])[0 if grade == 'A' else 1]
            k = min(left, have)
            if k:
                _take(g, pid, grade, k)
                left -= k
    g['orders'].remove(o)
    g['stats']['orders'] += 1
    g['stats']['income'] += pay
    g['xp'] += 5
    kit.metric(c, 'fp_orders')
    kit.money(s, c, pay, f'Đơn đặc sản: {b["name"]}', o['id'], 'revenue')
    return dict(message=f'{b["emoji"]} Giao xong cho {b["name"]} · +{pay} xu{note}. +5 điểm nông.', celebrate=True)


# ---------------------------------------------------------------- actions
ACTIONS = ('fa_v_open', 'fa_v_plant', 'fa_v_care', 'fa_v_harvest', 'fa_v_all', 'fa_v_buy', 'fa_v_animal', 'fa_v_feed',
           'fa_v_collect', 'fa_v_sell', 'fa_v_deliver', 'fa_v_skip')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    now = _now()
    g = get(c)
    if name == 'fa_v_open':
        kit.need(g is None, 'Trang trại đã mở rồi.')
        g = c['ext'][KEY] = initial(now)
        _refill(c, g, now)
        kit.metric(c, 'fp_opened')
        return dict(message='🌟 Mở Trang trại: 2 ô đất mới, gieo ớt hay lúa trước nha. Cây lớn theo giờ thật, kể cả lúc bạn đi vắng.', celebrate=True)
    kit.need(g is not None, 'Mở Trang trại trước nhé.')
    before = level_of(g['xp'])
    out = _act(s, c, g, name, p, now)
    _refill(c, g, now)
    after = level_of(g['xp'])
    if after > before:
        out['message'] = (out.get('message') or '') + f' ⬆️ Trang trại lên cấp {after}! {title(after)}'
        out['celebrate'] = True
        kit.log(s, c, 'note', f'Trang trại lên cấp {after}: {title(after)}.')
    return out


def _plot_i(g: dict, p: dict) -> int:
    i = p.get('plot')
    kit.need(type(i) is int and 0 <= i < len(g['plots']), 'Ô đất không tồn tại.')
    return i


def _act(s: dict, c: dict, g: dict, name: str, p: dict, now: int) -> dict:
    if name == 'fa_v_plant':
        i = _plot_i(g, p)
        crop = CROP.get(p.get('crop'))
        kit.need(crop, 'Chưa có giống này.')
        why = _unlocked(g, crop)
        kit.need(why is None, f'{crop["name"]}: {why}.' if why else '')
        kit.need(g['plots'][i] is None, 'Ô này đang có cây.')
        _plant(s, c, g, i, crop, now)
        return dict(message=f'{crop["emoji"]} Gieo {crop["name"].lower()} ô {i + 1} (−{crop["seed"]} xu). Chín sau {_left(g["plots"][i]["dur"])}.')
    if name == 'fa_v_care':
        i = _plot_i(g, p)
        pl = g['plots'][i]
        kit.need(pl, 'Ô trống.')
        kind = p.get('need')
        kit.need(kind in _due(pl, now), 'Cây chưa cần việc này.')
        pl['done'].append(kind)
        kit.metric(c, 'fp_cared')
        return dict(message=f'{CARES[kind]["icon"]} {CARES[kind]["done"]}')
    if name == 'fa_v_harvest':
        i = _plot_i(g, p)
        kit.need(g['plots'][i], 'Ô trống.')
        return dict(message=_harvest(s, c, g, i, now), celebrate=True)
    if name == 'fa_v_all':
        kit.need(_has(g, 'tractor'), 'Cần máy cày mini để làm cả vườn một lần.')
        what = kit.one_of(p.get('what'), ('plant', 'care', 'harvest'), 'Chọn việc cho cả vườn.')
        if what == 'harvest':
            rows = [i for i, pl in enumerate(g['plots']) if pl and _stage(pl, now) in ('ripe', 'over')]
            kit.need(rows, 'Chưa ô nào chín.')
            return dict(message=' '.join(_harvest(s, c, g, i, now) for i in rows), celebrate=True)
        if what == 'care':
            n = 0
            for pl in g['plots']:
                for kind in (_due(pl, now) if pl else []):
                    pl['done'].append(kind)
                    n += 1
            kit.need(n, 'Vườn chưa cần chăm gì.')
            kit.metric(c, 'fp_cared', n)
            return dict(message=f'🚜 Chăm xong {n} việc cả vườn.')
        crop = CROP.get(p.get('crop'))
        kit.need(crop, 'Chưa có giống này.')
        why = _unlocked(g, crop)
        kit.need(why is None, f'{crop["name"]}: {why}.' if why else '')
        rows = [i for i, pl in enumerate(g['plots']) if pl is None]
        kit.need(rows, 'Không còn ô trống.')
        kit.need(c['money'] >= crop['seed'] * len(rows), f'Cần {crop["seed"] * len(rows)} xu mua giống cho {len(rows)} ô.')
        for i in rows:
            _plant(s, c, g, i, crop, now)
        return dict(message=f'🚜 Gieo {crop["name"].lower()} {len(rows)} ô (−{crop["seed"] * len(rows)} xu).')
    if name == 'fa_v_buy':
        kit.confirm(p, 'Xác nhận mua nâng cấp.')
        up = p.get('up')
        if up == 'plot':
            k = len(g['plots']) - START_PLOTS
            kit.need(len(g['plots']) < MAX_PLOTS, 'Đã đủ 6 ô đất.')
            cost = PLOT_COST[k]
            kit.money(s, c, -cost, f'Mua: khai hoang ô đất {len(g["plots"]) + 1}', 'plot', 'upgrade')
            g['plots'].append(None)
            return dict(message=f'⛏️ Khai hoang xong ô {len(g["plots"])} (−{cost} xu).', celebrate=True)
        u = UPGRADE.get(up)
        kit.need(u, 'Nâng cấp không tồn tại.')
        kit.need(up not in g['ups'], 'Đã có rồi.')
        if u.get('need_a'):
            kit.need(g['stats']['a'] >= u['need_a'], f'Cần {u["need_a"]} lần thu loại A để được chứng nhận (đang {g["stats"]["a"]}).')
        kit.money(s, c, -u['cost'], f'Mua: {u["name"]}', up, 'upgrade')
        g['ups'].append(up)
        kit.metric(c, 'fp_upgrades')
        return dict(message=f'{u["emoji"]} {u["name"]}: {u["text"]} (−{u["cost"]} xu)', celebrate=True)
    if name == 'fa_v_animal':
        kit.confirm(p, 'Xác nhận mua con giống.')
        a = ANIMAL.get(p.get('animal'))
        kit.need(a, 'Không có con giống này.')
        kit.need(a['id'] not in g['pens'], f'Đã có {a["name"].lower()} rồi.')
        kit.need(not a['barn'] or _has(g, 'barn'), 'Cần xây chuồng trại trước.')
        kit.money(s, c, -a['cost'], f'Mua {a["name"].lower()}', a['id'], 'stock')
        g['pens'][a['id']] = dict(fed=0, n=0)
        return dict(message=f'{a["emoji"]} Mua {a["name"].lower()} (−{a["cost"]} xu). Cho ăn để bắt đầu nha.')
    if name in ('fa_v_feed', 'fa_v_collect'):
        a = ANIMAL.get(p.get('animal'))
        kit.need(a and a['id'] in g['pens'], 'Chưa nuôi con này.')
        pen = g['pens'][a['id']]
        ready = pen['fed'] and now >= pen['fed'] + a['mins'] * 60
        if name == 'fa_v_feed':
            if a['id'] == 'pig':
                kit.need(pen['n'] < a['feeds'], 'Heo đã đủ lớn, bán thôi.')
                kit.need(not pen['fed'] or ready, f'Heo còn no, {_left(pen["fed"] + a["mins"] * 60 - now)} nữa cho ăn tiếp.')
            else:
                kit.need(not pen['fed'], 'Đang cho ăn rồi, chờ thu hoạch.')
            kit.money(s, c, -a['feed'], f'Mua {a["food"]} cho {a["name"].lower()}', a['id'], 'stock')
            pen['fed'] = now
            pen['n'] += a['id'] == 'pig'
            return dict(message=f'{a["emoji"]} Cho ăn {a["food"]} (−{a["feed"]} xu). ' + (f'Heo lớn {pen["n"]}/{a["feeds"]}.' if a['id'] == 'pig' else f'Sau {a["mins"]} phút thu {PRODUCTS[a["product"]]["name"].lower()}.'))
        kit.need(ready, 'Chưa tới lúc.' if pen['fed'] else 'Cho ăn trước đã.')
        if a['id'] == 'pig':
            kit.need(pen['n'] >= a['feeds'], f'Heo mới lớn {pen["n"]}/{a["feeds"]}, cho ăn tiếp.')
            pay = a['sell'] * (GAP_PCT if _has(g, 'gap') else 100) // 100
            del g['pens']['pig']
            g['xp'] += 10
            g['stats']['income'] += pay
            kit.money(s, c, pay, 'Bán heo hơi cho lò mổ xã', 'pig', 'revenue')
            return dict(message=f'🐖 Bán heo được {pay} xu. +10 điểm nông. Mua heo con nuôi lứa mới nha.', celebrate=True)
        prod = PRODUCTS[a['product']]
        kit.need(STORE_CAP - _store_units(g) >= a['qty'], f'Kho trang trại đầy ({_store_units(g)}/{STORE_CAP}).')
        _put(g, a['product'], 'A', a['qty'])
        pen['fed'] = 0
        g['xp'] += 2
        return dict(message=f'{a["emoji"]} Thu {a["qty"]} {prod["unit"]} {prod["name"].lower()}. +2 điểm nông.')
    if name == 'fa_v_sell':
        pid = p.get('item')
        kit.need(pid in g['store'], 'Kho không có món này.')
        grade = kit.one_of(p.get('grade'), ('A', 'B'), 'Chọn loại hàng.')
        have = g['store'][pid][0 if grade == 'A' else 1]
        kit.need(have > 0, f'Không còn hàng loại {grade}.')
        n = _sold(g, now)
        sold = n.get(pid, 0)
        room = DEPTH - sold
        prod = PRODUCTS[pid]
        kit.need(room > 0, f'Chợ hôm nay đủ {prod["name"].lower()} rồi, mai bán tiếp.')
        qty = kit.integer(p.get('qty', min(have, room)), 1, STORE_CAP)
        qty = min(qty, have, room)
        total = sale(c, g, pid, grade, qty, sold)
        _take(g, pid, grade, qty)
        n[pid] = sold + qty
        g['stats']['income'] += total
        kit.metric(c, 'fp_sold', qty)
        kit.money(s, c, total, f'Bán ở chợ: {qty} {prod["unit"]} {prod["name"].lower()} loại {grade}', pid, 'revenue')
        return dict(message=f'{prod["emoji"]} Bán {qty} {prod["unit"]} {prod["name"].lower()} loại {grade} · +{total} xu.' + (' 🎉 Giá Hội mùa!' if festival(c) else ''))
    if name in ('fa_v_deliver', 'fa_v_skip'):
        o = next((x for x in g['orders'] if x['id'] == p.get('order') and x['until'] > now), None)
        kit.need(o, 'Đơn không còn nữa.')
        if name == 'fa_v_skip':
            g['orders'].remove(o)
            return dict(message=f'Đã từ chối đơn của {BUYER[o["buyer"]]["name"]}.')
        return _deliver(s, c, g, o, p.get('deal'))
    raise kit.eng().GameError('Thao tác trang trại không hợp lệ.')


# ---------------------------------------------------------------- the six beds (upgrades that help them)
def drip_beds(c: dict, d: dict) -> int:
    """Tưới nhỏ giọt keeps the six beds out of the dry zone (not when the HTX pump is off). Returns beds topped up."""
    g = get(c)
    if not g or 'drip' not in g['ups'] or d['desk']['marks'].get('nopump') == c['day']:
        return 0
    from . import farm
    n = 0
    for p in d['plots']:
        if p['crop'] and p['moisture'] < farm.MOIST_LOW:
            p['moisture'] = farm.MOIST_LOW + 15
            n += 1
    return n


def close_line(c: dict) -> str | None:
    g = get(c)
    if not g:
        return None
    now = _now()
    ripe = sum(1 for pl in g['plots'] if pl and _stage(pl, now) == 'ripe')
    soon = [pl['at'] + pl['dur'] - now for pl in g['plots'] if pl and pl['at'] + pl['dur'] > now]
    if not ripe and not soon:
        return None
    return '🌟 Trang trại: ' + ', '.join(x for x in (f'{ripe} ô chín chờ thu' if ripe else '', f'ô tiếp theo chín sau {_left(min(soon))}' if soon else '') if x) + '.'


# ---------------------------------------------------------------- view
def view(c: dict) -> dict:
    g = get(c)
    if g is None:
        return dict(open=False, now=_now())
    now = _now()
    lv = level_of(g['xp'])
    plots = []
    for i, pl in enumerate(g['plots']):
        if pl is None:
            plots.append(dict(i=i, crop=None))
            continue
        stage = _stage(pl, now)
        # The page counts down on the server clock (x.now()) and brings a need up when its percent comes.
        plots.append(dict(i=i, crop=pl['crop'], stage=stage, pct=_pct(pl, now), at=pl['at'], dur=pl['dur'], ripe_at=pl['at'] + pl['dur'],
                          over_at=pl['at'] + pl['dur'] + _keep(pl), due=_due(pl, now), needs=[list(n) for n in pl['needs']], done=list(pl['done'])))
    pens = {}
    for k, pen in g['pens'].items():
        a = ANIMAL[k]
        pens[k] = dict(fed=pen['fed'], n=pen['n'], ready_at=pen['fed'] + a['mins'] * 60 if pen['fed'] else 0)
    sold = _absorbed(g, now)
    store = [dict(id=k, a=a, b=b, unit_a=_unit_tenths(c, g, k, 'A'), unit_b=_unit_tenths(c, g, k, 'B'), sold=sold.get(k, 0))
             for k, (a, b) in sorted(g['store'].items())]
    orders = [dict(id=o['id'], buyer=o['buyer'], items=o['items'], pay=o['pay'], until=o['until'], asked=o['asked'],
                   line=BUYER[o['buyer']]['lines'][o['line']], why=_fits(g, o)) for o in g['orders'] if o['until'] > now]
    crops = [dict(id=x['id'], why=_unlocked(g, x), dur=_dur(g, x)) for x in CROPS]
    nxt = LEVELS[lv] if lv < len(LEVELS) else None
    return dict(open=True, now=now, xp=g['xp'], level=lv, title=title(lv), floor=LEVELS[lv - 1], next=nxt,
                plots=plots, plot_cost=PLOT_COST[len(g['plots']) - START_PLOTS] if len(g['plots']) < MAX_PLOTS else None,
                pens=pens, store=store, store_units=_store_units(g), store_cap=STORE_CAP, orders=orders, ups=list(g['ups']),
                crops=crops, festival=festival(c), sky=_weather(c), season=_season(c), stats=dict(g['stats']), depth=DEPTH, slip=SLIP)


def content() -> dict:
    return dict(crops=CROPS, cares=CARES, animals=ANIMALS, products=PRODUCTS, upgrades=UPGRADES, buyers={b['id']: dict(name=b['name'], emoji=b['emoji'], grade=b['grade'], gap=bool(b.get('gap'))) for b in BUYERS},
                levels=list(LEVELS), plot_cost=list(PLOT_COST), in_season={k: list(v) for k, v in IN_SEASON.items()},
                b_pct=B_PCT, gap_pct=GAP_PCT, fest_pct=FEST_PCT, haggle_pct=HAGGLE_PCT, max_plots=MAX_PLOTS)


# ---------------------------------------------------------------- validation
def validate(c: dict) -> None:
    g = c['ext'].get(KEY)
    if g is None:
        return
    need = kit.need
    I = kit.integer
    need(isinstance(g, dict) and set(g) == {'v', 'at', 'seq', 'xp', 'plots', 'pens', 'store', 'ups', 'orders', 'sold', 'stats'}, 'Trang trại sai.')
    need(g['v'] == VERSION, 'Phiên bản trang trại sai.')
    for k in ('at', 'seq', 'xp'):
        I(g[k], 0, 10 ** 10)
    need(isinstance(g['plots'], list) and START_PLOTS <= len(g['plots']) <= MAX_PLOTS, 'Ô đất sai.')
    for pl in g['plots']:
        if pl is None:
            continue
        need(isinstance(pl, dict) and set(pl) == {'crop', 'at', 'dur', 'n', 'needs', 'done'} and pl['crop'] in CROP, 'Ô đất sai.')
        I(pl['at'], 0, 10 ** 10)
        I(pl['dur'], 1, 10 ** 6)
        I(pl['n'], 1, 10 ** 10)
        need(isinstance(pl['needs'], list) and len(pl['needs']) <= 4, 'Ô đất sai.')
        for row in pl['needs']:
            need(isinstance(row, list) and len(row) == 2 and row[0] in CARES, 'Ô đất sai.')
            I(row[1], 0, 100)
        need(isinstance(pl['done'], list) and len(pl['done']) <= 4 and all(k in CARES for k in pl['done'])
             and len(set(pl['done'])) == len(pl['done']), 'Ô đất sai.')
    need(isinstance(g['pens'], dict) and set(g['pens']) <= set(ANIMAL), 'Chuồng sai.')
    for k, pen in g['pens'].items():
        need(isinstance(pen, dict) and set(pen) == {'fed', 'n'}, 'Chuồng sai.')
        I(pen['fed'], 0, 10 ** 10)
        I(pen['n'], 0, ANIMAL[k].get('feeds', 0))
    need(isinstance(g['store'], dict) and set(g['store']) <= set(PRODUCTS), 'Kho trang trại sai.')
    for v in g['store'].values():
        need(isinstance(v, list) and len(v) == 2 and sum(v) > 0, 'Kho trang trại sai.')
        I(v[0], 0, STORE_CAP)
        I(v[1], 0, STORE_CAP)
    need(isinstance(g['ups'], list) and set(g['ups']) <= set(UPGRADE) and len(set(g['ups'])) == len(g['ups']), 'Nâng cấp sai.')
    need(isinstance(g['orders'], list) and len(g['orders']) <= ORDERS_OPEN, 'Đơn đặc sản sai.')
    for o in g['orders']:
        need(isinstance(o, dict) and set(o) == {'id', 'buyer', 'items', 'pay', 'until', 'line', 'trait', 'asked'} and o['buyer'] in BUYER, 'Đơn đặc sản sai.')
        kit.text(o['id'], 20)
        need(isinstance(o['items'], dict) and 0 < len(o['items']) <= 2 and set(o['items']) <= set(PRODUCTS), 'Đơn đặc sản sai.')
        for q in o['items'].values():
            I(q, 1, 100)
        I(o['pay'], 1, 10 ** 5)
        I(o['until'], 0, 10 ** 10)
        I(o['line'], 0, len(BUYER[o['buyer']]['lines']) - 1)
        need(o['trait'] in set(TRAITS) and type(o['asked']) is bool, 'Đơn đặc sản sai.')
    sd = g['sold']
    need(isinstance(sd, dict) and set(sd) == {'at', 'n'} and isinstance(sd['n'], dict) and set(sd['n']) <= set(PRODUCTS), 'Sổ chợ trang trại sai.')
    I(sd['at'], 0, 10 ** 10)
    for v in sd['n'].values():
        I(v, 0, DEPTH)
    st = g['stats']
    need(isinstance(st, dict) and set(st) == {'harvests', 'a', 'gold', 'giant', 'pumpkin', 'melon', 'orders', 'income'}, 'Thống kê trang trại sai.')
    for v in st.values():
        I(v, 0, 10 ** 9)


# ---------------------------------------------------------------- demo (screenshots / manual QA)
def demo(s: dict, c: dict) -> None:
    """A lived-in farm for screenshots: a few plots at different stages, animals, stock and orders."""
    now = _now()
    g = c['ext'][KEY] = initial(now - 4000)
    g['xp'] = 160
    g['plots'] = [None] * 5
    g['ups'] = ['drip', 'barn']
    for i, (cid, ago) in enumerate((('ot', 400), ('dua', 600), ('bi', 300), ('lua', 120))):
        g['seq'] += 1
        crop = CROP[cid]
        g['plots'][i] = dict(crop=cid, at=now - ago, dur=_dur(g, crop), n=g['seq'], needs=_needs_for(g, crop, g['seq'], 'sun'), done=[])
    g['pens'] = dict(duck=dict(fed=now - 1300, n=0), cow=dict(fed=now - 600, n=0))
    g['store'] = dict(ot=[5, 1], lua=[8, 0], trung_vit=[6, 0])
    g['stats'].update(harvests=23, a=17, gold=1, pumpkin=8, melon=6)
    _refill(c, g, now)
