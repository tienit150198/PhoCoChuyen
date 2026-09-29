"""Tiệm Mây Nhỏ (mother_baby) — the caring loop that spans days.

mother_baby is one of the original careers: its counter rules live in
game/giftshop.py (orders from day 2, surprises) and the engine's shop_* actions.
This module adds what carries over from one day to the next, without touching
the order generator (every (day, slot) still makes the same order):

* Sổ bé quen   four regular families. Their babies grow with the game days
               (game rule: one day at the shop counts as one week of the baby's
               life), so the diaper size, the formula stage, first foods and
               teething change and the book is how you remember them.
* Gói định kỳ  each family picks up a diaper pack (and a formula can when the
               baby drinks formula) every 4–5 days, over a two-day window.
               Pick the size that fits today's weight, the family's brand at the
               right stage, from a lot that is in date and not recalled.
* Kệ bỉm sữa   its own small shelf: packs by size and formula lots with a use-by
               day. Orders arrive the next morning. Expired lots must be pulled
               (a loss); recalled lots are pulled for a supplier credit.
* Danh sách quà mừng  an expecting mother's baby-shower registry, days ahead:
               friends buy lines, you set the goods aside, suggest a newborn-safe
               swap for a line whose box says 3+, and hand the box over on time.
* Tư vấn thật lòng  at a pickup a parent may ask a question. The honest answer
               (sometimes "yes, this one thing is enough") builds trust; the
               upsell earns a little now and costs trust.

Trust (0–5) per family: from 2 the parent tells today's weight unasked, from 3
they leave a small tip after a perfect pickup.

Everything is decided on the server. Randomness is seeded by (care start, family,
day). Data lives in c['ext']['data']['gift']['care'], so the public projection of
the gift shop (giftshop.public) replaces it and hidden answers never leave.

Wiring: giftshop.py ends with `from .careers import mother_baby as _care` and
`_care.install(globals())`, which wraps handle/on_start/on_close/public/validate/
upgrade. Only the standard library is imported at module level.
"""
from __future__ import annotations

import hashlib
import random
import re
from .. import archive as ar

CAREER = 'mother_baby'
V = 1
START_DAY = 2            # the corner opens with the gift shop's day-2 orders
RULE = 'Ở Tiệm Mây Nhỏ, mỗi ngày mở cửa tính như một tuần của bé: bé lớn nhanh, nhớ ghi lại nhé.'

SIZES = ('NB', 'S', 'M', 'L')
SIZE_INFO = {
    'NB': dict(name='Size NB', range='dưới 5 kg', top=50),
    'S': dict(name='Size S', range='5–7 kg', top=70),
    'M': dict(name='Size M', range='7–10 kg', top=100),
    'L': dict(name='Size L', range='từ 10 kg', top=10**6),
}
BRANDS = {'mx': 'Mầm Xanh', 'sm': 'Sao Mai'}
FORMULAS = {
    'mx1': dict(brand='mx', stage=1), 'mx2': dict(brand='mx', stage=2),
    'sm1': dict(brand='sm', stage=1), 'sm2': dict(brand='sm', stage=2),
}
STAGE_RANGE = {1: '0–6 tháng', 2: '6–12 tháng'}
STAGE_TWO_WEEKS = 26     # 26 weeks ≈ 6 months
DIAPER = dict(price=60, cost=34, cap=12)
FORMULA = dict(price=95, cost=55, cap=10)
TIP = 3
WRAP = 5
TRUST_NAMES = ('Khách mới', 'Quen mặt', 'Tin tưởng', 'Thân thiết', 'Khách ruột', 'Như người nhà')
TELLS_WEIGHT = 2
TIPS_FROM = 3

# Days are relative to the day the corner opens (care['start']).
FAMILIES = [
    dict(id='hoa', parent='Chị Hoa', emoji='🤱', baby='Na', girl=True, born=-3, b10=31, every=4, first=1, milk=None, npc=1),
    dict(id='tuan', parent='Anh Tuấn', emoji='👨‍🍼', baby='Tôm', girl=False, born=-10, b10=36, every=5, first=1, milk='sm', npc=2),
    dict(id='dieu', parent='Chị Diệu', emoji='👩', baby='Mít', girl=True, born=-21, b10=30, every=4, first=2, milk='mx', npc=3),
    dict(id='ly', parent='Chị Ly', emoji='🤰', baby='Bắp', girl=False, born=7, b10=32, every=4, first=9, milk='sm', npc=4),
]
FAM = {f['id']: f for f in FAMILIES}

# The registry of the expecting family (Chị Ly): (id, item, qty, bought on start+n).
REGISTRY = dict(family='ly', open=2, shower=6, lines=[
    ('r1', 'towel', 2, 3), ('r2', 'bear', 1, 3), ('r3', 'socks', 2, 4), ('r4', 'bottle', 1, 4), ('r5', 'blanket', 1, 5)])
REG_LINES = {x[0]: x for x in REGISTRY['lines']}

# Questions at a pickup. `kind`: honest (+1 trust), upsell (+commission now, −1 trust,
# a regret review tomorrow), wrong (−1 trust). An honest answer may still sell the
# one thing that helps (`sell`: an item of the gift shelf).
QUESTIONS = {
    'bigger': dict(text='Lấy luôn bỉm lớn hơn một cỡ cho bé dùng được lâu, đỡ phải mua lại, được không bạn?',
                   options=[dict(id='a', kind='honest', label='Lấy vừa cân nặng thôi ạ: rộng quá dễ tràn. Bé lớn tới đâu mình đổi tới đó.'),
                            dict(id='b', kind='upsell', label='Được ạ, lấy thêm một gói cỡ lớn cho tiện.', gain=25,
                                 regret='Mua gói bỉm to “cho dùng lâu”, mặc vào tràn ướt hết cả đêm. Lẽ ra tiệm nên khuyên mình lấy vừa cỡ.')]),
    'gainer': dict(text='Hộp sữa tăng cân Mầm Vàng 180 xu có giúp bé mau lớn hơn không?',
                   options=[dict(id='a', kind='upsell', label='Có ạ, bé nào uống cũng mau lớn. Lấy một hộp nhé.', gain=50,
                                 regret='Mua hộp sữa tăng cân 180 xu, đi khám bác sĩ bảo bé lên cân đều, chưa cần. Tiếc tiền ghê.'),
                            dict(id='b', kind='honest', label='Bé đang lên cân đều ạ. Chưa cần đổi sữa đắt; lo thì mình hỏi bác sĩ nhi.')]),
    'breast': dict(text='Bé bú mẹ hoàn toàn, mình có nên mua thêm hộp sữa công thức để dành cho chắc không?',
                   options=[dict(id='a', kind='honest', label='Bé bú mẹ tốt, lên cân đều thì chưa cần ạ. Khi nào cần, tiệm tư vấn tiếp.'),
                            dict(id='b', kind='upsell', label='Nên lấy một hộp phòng khi ạ.', gain=30,
                                 regret='Nghe tiệm mua hộp sữa “để dành”, rốt cuộc bé chỉ bú mẹ, hộp sữa nằm góc tủ tới hết hạn.')]),
    'solids': dict(text='Bé sắp sáu tháng rồi, cho ăn dặm từ tuần này được chưa?',
                   options=[dict(id='a', kind='upsell', label='Được ạ, lấy luôn bộ bột ăn dặm 70 xu cho bé tập.', gain=20,
                                 regret='Tiệm bán bộ bột ăn dặm khi bé chưa tròn sáu tháng, bác sĩ dặn phải đợi. Hơi buồn.'),
                            dict(id='b', kind='honest', label='Đợi bé tròn sáu tháng và ngồi vững đã ạ. Tới lúc đó yếm ăn dặm của tiệm là đủ.')]),
    'teeth': dict(text='Mấy hôm nay bé chảy dãi, cứ cắn tay suốt. Mình nên mua gì cho bé?',
                  options=[dict(id='a', kind='upsell', label='Lấy trọn bộ: vòng gặm, gel bôi lợi và đồ chơi phát nhạc, 150 xu.', gain=45,
                                regret='Mua cả bộ đồ mọc răng 150 xu, về mới biết bé chỉ cần cái vòng gặm. Lần sau mình hỏi kỹ hơn.'),
                           dict(id='b', kind='honest', sell='teether', label='Chắc bé sắp mọc răng: một vòng gặm nướu silicon là đủ, rửa sạch, để mát.')]),
    'stage2': dict(text='Bé tròn sáu tháng rồi, sữa vẫn dùng số 1 được không?',
                   options=[dict(id='a', kind='wrong', label='Cứ dùng số 1 tiếp cũng được ạ.'),
                            dict(id='b', kind='honest', label='Bé đủ sáu tháng nên chuyển sang số 2 (6–12 tháng) ạ, pha xen dần vài ngày cho quen.')]),
}
Q_ORDER = ('stage2', 'teeth', 'solids', 'breast', 'gainer', 'bigger')

FAM_KEYS = {'trust', 'next', 'visits', 'last', 'kg10', 'size', 'prod', 'asked', 'told', 'q', 'missed'}
LOT_KEYS = {'id', 'p', 'qty', 'exp', 'recalled', 'got'}
TODAY_KEYS = ('pickups', 'perfect', 'pulled', 'honest', 'upsell', 'safety')
LOT_ID = re.compile(r'(MX|SM)[12]-\d{2,4}')


# ---------------------------------------------------------------- helpers
def _e():
    from .. import engine
    return engine


def _gs():
    from .. import giftshop
    return giftshop


def _rng(*parts) -> random.Random:
    seed = int(hashlib.sha256('|'.join(map(str, ('mb-care',) + parts)).encode()).hexdigest()[:12], 16)
    return random.Random(seed)


def _products() -> dict:
    from ..content import PRODUCT_INDEX
    return PRODUCT_INDEX


def _price(c: dict, item: str) -> int:
    from ..experiences import price
    return price(c, item, _products()[item]['price'])


def kg_text(kg10) -> str:
    return f'{kg10 // 10},{kg10 % 10} kg'


def formula_name(p: str) -> str:
    f = FORMULAS[p]
    return f"{BRANDS[f['brand']]} số {f['stage']}"


def raw(c: dict):
    """The saved care record or None (read only; no defaults are written)."""
    gift = ((c.get('ext') or {}).get('data') or {}).get('gift')
    return gift.get('care') if isinstance(gift, dict) else None


def weeks(cr: dict, f: dict, day: int) -> int:
    return day - (cr['start'] + f['born'])


def weight(f: dict, w: int) -> int:
    """Tenths of a kilo: a steady curve, faster in the first three months."""
    w = max(0, w)
    return f['b10'] + 2 * min(w, 13) + max(0, w - 13)


def size_for(kg10: int) -> str:
    return next(s for s in SIZES if kg10 < SIZE_INFO[s]['top'])


def stage_for(w: int) -> int:
    return 2 if w >= STAGE_TWO_WEEKS else 1


def product_for(f: dict, w: int) -> str | None:
    return f"{f['milk']}{stage_for(w)}" if f['milk'] else None


def status(cr: dict, f: dict, day: int) -> str:
    if weeks(cr, f, day) < 0:
        return 'expecting'
    if day < cr['start'] + f['first']:
        return 'soon'
    return 'active'


def due(cr: dict, fid: str, day: int) -> bool:
    f = FAM[fid]
    r = cr['fam'][fid]
    return status(cr, f, day) == 'active' and r['next'] <= day <= r['next'] + 1


def _trust(r: dict, delta: int) -> int:
    before = r['trust']
    r['trust'] = max(0, min(5, before + delta))
    return r['trust'] - before


def _log(cr: dict, day: int, text: str) -> None:
    cr['log'] = ar.last(cr['log'] + [dict(day=day, text=text)], 12, 'baby.log', None)


def _zero() -> dict:
    return {k: 0 for k in TODAY_KEYS}


def expired(lot: dict, day: int) -> bool:
    return lot['exp'] < day


def safe_lot(lot: dict, day: int) -> bool:
    return not expired(lot, day) and not lot['recalled']


def _post(s: dict, c: dict, f: dict, text: str, ref: str, stars: int | None = None, kind: str = 'review') -> None:
    post = _e().add_feed(s, c, f'{CAREER}_npc_{f["npc"]:02d}', text, ref, stars, kind)
    post['author'] = f['parent']


# ---------------------------------------------------------------- state
def fresh(start: int) -> dict:
    fam = {f['id']: dict(trust=0, next=start + f['first'], visits=0, last=None, kg10=None, size=None, prod=None,
                         asked=[], told=None, q=None, missed=0) for f in FAMILIES}
    lots = [dict(id='MX1-01', p='mx1', qty=3, exp=start + 12), dict(id='SM1-02', p='sm1', qty=2, exp=start + 2),
            dict(id='MX2-03', p='mx2', qty=2, exp=start + 9), dict(id='SM1-04', p='sm1', qty=2, exp=start + 14),
            dict(id='SM2-05', p='sm2', qty=1, exp=start + 15)]
    for lot in lots:
        lot.update(recalled=False, got=start)
    reg = dict(lines={x[0]: dict(aside=False, swap=None) for x in REGISTRY['lines']}, state='soon')
    return dict(v=V, start=start, day=0, seq=5, fam=fam, diapers=dict(NB=3, S=3, M=2, L=1), lots=lots, orders=[], notices=[],
                reg=reg, log=[], follow=[], today=_zero(), waste=0)


def ensure(c: dict) -> dict | None:
    """The care record (created once the corner opens), with new keys filled in."""
    if c['day'] < START_DAY and raw(c) is None:
        return None
    b = _gs().state(c)
    cr = b.get('care')
    if not isinstance(cr, dict):
        cr = b['care'] = fresh(max(START_DAY, c['day']))
    base = fresh(cr.get('start', START_DAY))
    for k, v in base.items():
        cr.setdefault(k, v)
    return cr


def upgrade(c: dict) -> None:
    """Old saves: nothing to do until the corner opens; later versions fill keys here."""
    cr = raw(c)
    if isinstance(cr, dict) and isinstance(cr.get('start'), int):
        for k, v in fresh(cr['start']).items():
            cr.setdefault(k, v)


# ---------------------------------------------------------------- day hooks
def on_start(s: dict, c: dict) -> None:
    if c['day'] < START_DAY:
        return
    cr = ensure(c)
    day = c['day']
    if cr['day'] == day:
        return
    cr['day'] = day
    cr['today'] = _zero()
    # Orders placed yesterday are on the doorstep in the morning.
    keep = []
    for o in cr['orders']:
        if o['day'] > day:
            keep.append(o)
            continue
        if o['item'] in SIZES:
            cr['diapers'][o['item']] = min(DIAPER['cap'], cr['diapers'][o['item']] + o['qty'])
        else:
            cr['seq'] += 1
            exp = day + _rng(cr['start'], 'lot', o['id']).randint(8, 16)
            cr['lots'].append(dict(id=f"{o['item'].upper()}-{cr['seq']:02d}", p=o['item'], qty=o['qty'], exp=exp, recalled=False, got=day))
        _log(cr, day, f"Nhận hàng đặt hôm qua: {o['qty']} × {_item_name(o['item'])}.")
    cr['orders'] = keep
    cr['lots'] = ar.last([lot for lot in cr['lots'] if lot['qty'] > 0], 30, 'baby.lots', c)
    _recall(s, c, cr, day)
    # Pickup windows: a family that was never seen (odd saves) moves on quietly.
    for f in FAMILIES:
        r = cr['fam'][f['id']]
        while r['next'] + 1 < day:
            r['next'] += f['every']
            r['q'] = None
            r['told'] = None
        if due(cr, f['id'], day) and r['q'] is None:
            r['q'] = _roll_question(cr, f, r, day)
    # Yesterday's upsells become a review once the family is home.
    rest = []
    for fu in cr['follow']:
        if fu['day'] > day:
            rest.append(fu)
            continue
        f = FAM[fu['fam']]
        _post(s, c, f, fu['text'], fu['ref'], fu['stars'])
    cr['follow'] = ar.last(rest, 8, 'baby.follow', c)
    reg = cr['reg']
    if reg['state'] == 'soon' and day >= cr['start'] + REGISTRY['open']:
        reg['state'] = 'open'
        _log(cr, day, f"{FAM['ly']['parent']} mở danh sách quà mừng bé {FAM['ly']['baby']}: tiệc ngày {_gs().date_text(cr['start'] + REGISTRY['shower'])}.")


def _roll_question(cr: dict, f: dict, r: dict, day: int) -> str:
    w = weeks(cr, f, day)
    kg = weight(f, w)
    ok = []
    for q in Q_ORDER:
        if q in r['asked']:
            continue
        if q == 'stage2' and not (f['milk'] and w >= STAGE_TWO_WEEKS and r['prod'] == f"{f['milk']}1"):
            continue
        if q == 'teeth' and not 16 <= w <= 34:
            continue
        if q == 'solids' and not 21 <= w <= 25:
            continue
        if q == 'breast' and f['milk']:
            continue
        if q == 'gainer' and not (f['milk'] and w < 20):
            continue
        if q == 'bigger' and size_for(kg) not in ('NB', 'S'):
            continue
        ok.append(q)
    rr = _rng(cr['start'], 'q', f['id'], r['next'])
    if ok and (ok[0] == 'stage2' or rr.random() < 0.7):
        return ok[0] if ok[0] == 'stage2' else rr.choice(ok)
    return ''


def _recall(s: dict, c: dict, cr: dict, day: int) -> None:
    """Every nine days from start+4 the supplier recalls one lot on the shelf."""
    if (day - cr['start']) % 9 != 4 or any(n['day'] == day for n in cr['notices']):
        return
    lots = [x for x in cr['lots'] if x['qty'] > 0 and not expired(x, day) and not x['recalled']]
    if not lots:
        return
    soon = set()
    for f in FAMILIES:
        r = cr['fam'][f['id']]
        if f['milk'] and status(cr, f, r['next']) == 'active' and r['next'] - day <= 3:
            soon.add(product_for(f, weeks(cr, f, r['next'])))
    rr = _rng(cr['start'], 'recall', day)
    lot = rr.choices(lots, [3 if x['p'] in soon else 1 for x in lots])[0]
    lot['recalled'] = True
    cr['notices'] = ar.last(cr['notices'] + [dict(day=day, lot=lot['id'], p=lot['p'])], 6, 'baby.notices', c)
    _log(cr, day, f"📣 Hãng {BRANDS[FORMULAS[lot['p']]['brand']]} thu hồi lô {lot['id']} (lỗi hàn nắp). Rút khỏi kệ, hãng hoàn tiền.")
    _e().log(s, c, 'shop_event', f"Thông báo thu hồi lô sữa {lot['id']}.", ref=f"care-recall-{day}")


def on_close(s: dict, c: dict) -> dict | None:
    cr = raw(c)
    if not isinstance(cr, dict) or cr.get('day') != c['day']:
        return None
    day = c['day']
    lines = []
    for f in FAMILIES:
        r = cr['fam'][f['id']]
        if status(cr, f, day) == 'active' and r['next'] + 1 == day:
            # The last day of the window passed: this time they bought elsewhere.
            r['next'] += f['every']
            r['missed'] += 1
            r['q'] = None
            r['told'] = None
            _trust(r, -1)
            text = f"{f['parent']} chờ không được, lần này mua bỉm sữa chỗ khác."
            _log(cr, day, text)
            lines.append('⌛ ' + text)
    reg = cr['reg']
    if reg['state'] == 'open' and day >= cr['start'] + REGISTRY['shower']:
        lines.append('💔 ' + _shower_failed(s, c, cr, day))
    t = cr['today']
    if t['pickups']:
        lines.append(f"📦 Gói định kỳ đã trao: {t['pickups']} (đúng hết: {t['perfect']}).")
    if t['honest']:
        lines.append(f"🤝 Tư vấn thật lòng: {t['honest']} lần, khách tin tiệm hơn.")
    if t['upsell']:
        lines.append(f"🪙 Bán thêm thứ chưa cần: {t['upsell']} lần. Ngày mai khách sẽ nghĩ lại.")
    if t['pulled']:
        lines.append(f"🧹 Đã rút {t['pulled']} lô sữa khỏi kệ.")
    bad = [x for x in cr['lots'] if x['qty'] and (x['recalled'] or expired(x, day + 1))]
    if bad:
        lines.append(f"⚠️ Sáng mai còn {sum(x['qty'] for x in bad)} hộp sữa quá hạn hoặc bị thu hồi trên kệ: rút ra kẻo trao nhầm.")
    for f in FAMILIES:
        r = cr['fam'][f['id']]
        if status(cr, f, day + 1) == 'active' and r['next'] == day + 1:
            last = ('lần trước size ' + r['size'] + (f" · {kg_text(r['kg10'])}" if r['kg10'] else '')) if r['visits'] else 'lần đầu lấy gói'
            lines.append(f"📅 Mai {f['parent']} ghé lấy gói cho bé {f['baby']} ({last}).")
    return dict(lines=lines[:10])


# ---------------------------------------------------------------- actions
ACTIONS = ('gift_care_ask', 'gift_care_hand', 'gift_care_order', 'gift_care_pull', 'gift_care_swap', 'gift_care_aside', 'gift_care_shower')


def handle(s: dict, c: dict, action: str, p: dict) -> dict:
    e = _e()
    need = e.need
    need(action in ACTIONS, 'Thao tác ở góc bỉm sữa không hợp lệ.')
    need(c['open'], 'Mở cửa tiệm trước nhé.')
    # The corner opens at a day start (on_start); an old save mid-shift waits for tomorrow.
    old = raw(c)
    need(isinstance(old, dict) and old.get('day') == c['day'], 'Góc bỉm sữa mở khi bắt đầu ngày mới.')
    cr = ensure(c)
    fn = {'gift_care_ask': _ask, 'gift_care_hand': _hand, 'gift_care_order': _order, 'gift_care_pull': _pull,
          'gift_care_swap': _swap, 'gift_care_aside': _aside, 'gift_care_shower': _shower}[action]
    result = fn(s, c, cr, p)
    c['turn'] += 1
    return result


def _family(cr: dict, p: dict, day: int) -> tuple[dict, dict]:
    need = _e().need
    fid = p.get('family')
    need(isinstance(fid, str) and fid in FAM, 'Không có gia đình này trong sổ.')
    need(due(cr, fid, day), 'Hôm nay gia đình này chưa tới hẹn lấy gói.')
    return FAM[fid], cr['fam'][fid]


def _news(cr: dict, f: dict, r: dict, day: int) -> str:
    w = weeks(cr, f, day)
    kg = weight(f, w)
    bits = [f"Bé {f['baby']} được {w} tuần, hôm nay cân {kg_text(kg)}."]
    if r['size'] and SIZES.index(size_for(kg)) > SIZES.index(r['size']):
        bits.append('Bỉm cũ dán tới nấc cuối rồi, đùi bé hằn đỏ.')
    if f['milk'] and r['prod'] and stage_for(w) == 2 and r['prod'].endswith('1'):
        bits.append('Bé vừa tròn sáu tháng.')
    return ' '.join(bits)


def _ask(s, c, cr, p):
    f, r = _family(cr, p, c['day'])
    _e().need(r['told'] != c['day'] and r['trust'] < TELLS_WEIGHT, f"{f['parent']} đã kể chuyện bé hôm nay rồi.")
    r['told'] = c['day']
    return dict(message=f"{f['parent']}: “{_news(cr, f, r, c['day'])}”")


def _hand(s, c, cr, p):
    e = _e()
    need = e.need
    day = c['day']
    f, r = _family(cr, p, day)
    size = p.get('size')
    need(size in SIZES, 'Chọn size bỉm cho bé.')
    need(cr['diapers'][size] >= 1, f'Kệ hết bỉm {size}. Đặt thêm, sáng mai hàng về.')
    lot = None
    lid = p.get('lot')
    if f['milk']:
        # None = the shelf has no fitting can today: diapers only, the family buys milk elsewhere.
        if lid is not None:
            lot = next((x for x in cr['lots'] if x['id'] == lid and x['qty'] > 0), None) if isinstance(lid, str) else None
            need(lot, 'Không có hộp sữa này trên kệ.')
    else:
        need(p.get('lot') is None, f"Bé {f['baby']} bú mẹ, gói này không có sữa.")
    q = QUESTIONS.get(r['q'] or '')
    advice = p.get('advice')
    opt = None
    if q:
        opt = next((o for o in q['options'] if o['id'] == advice), None) if isinstance(advice, str) else None
        need(opt, f"Trả lời câu {f['parent']} hỏi trước đã nhé.")
    else:
        need(advice is None, 'Hôm nay khách không hỏi gì thêm.')
    need(p.get('confirm') is True, 'Xác nhận trao gói cho khách nhé.')
    w = weeks(cr, f, day)
    kg = weight(f, w)
    ref = f"care-{f['id']}-{day}"
    # Hand over and ring it up (one atomic step).
    cr['diapers'][size] -= 1
    total = DIAPER['price']
    if lot:
        lot['qty'] -= 1
        total += FORMULA['price']
    e.money(s, c, total, f"Gói định kỳ của {f['parent']}", ref, category='revenue')
    size_ok = size == size_for(kg)
    want = product_for(f, w)
    milk_ok = not f['milk'] or (lot is not None and lot['p'] == want)
    unsafe = lot is not None and not safe_lot(lot, day)
    notes = []
    delta = 0
    stars = None
    if unsafe:
        e.money(s, c, -min(c['money'], FORMULA['price']), f"Hoàn tiền hộp sữa lô {lot['id']}", ref, category='refund')
        delta -= 2
        cr['today']['safety'] += 1
        e.metric(c, 'safety_miss')
        why = 'đã quá hạn' if expired(lot, day) else 'nằm trong lô bị thu hồi'
        notes.append(f"Hộp sữa {why}: khách trả lại, tiệm hoàn tiền.")
        stars = 1
        review = f"Về nhà mới thấy hộp sữa {lot['id']} {why}. May mình đọc kỹ trước khi pha cho bé {f['baby']}."
    elif not size_ok or not milk_ok:
        delta -= 1
        stars = 3
        if not size_ok:
            tight = SIZES.index(size) < SIZES.index(size_for(kg))
            notes.append('Bỉm ' + ('chật, hằn đỏ đùi bé.' if tight else 'rộng, tràn ướt cả đêm.'))
        if not milk_ok:
            notes.append(f"Sữa sai loại: bé dùng {formula_name(want)}." if lot else f"Gói thiếu sữa {formula_name(want)}, phải chạy mua chỗ khác.")
        review = f"Gói định kỳ lần này chưa đúng: {' '.join(notes)} Mong lần sau tiệm nhớ bé {f['baby']} đã lớn."
    else:
        delta += 1
        cr['today']['perfect'] += 1
        c['xp'] += 6
        review = None
    tip = 0
    if opt:
        if opt['kind'] != 'wrong':
            cr['today']['honest' if opt['kind'] == 'honest' else 'upsell'] += 1
        r['asked'] = (r['asked'] + [r['q']])[-len(QUESTIONS):]
        if opt['kind'] == 'honest':
            delta += 1
            c['xp'] += 3
            e.metric(c, 'honest_advice')
            if opt.get('sell') and e.available(c, opt['sell']) > 0:
                c['stock'][opt['sell']] -= 1
                amount = _price(c, opt['sell'])
                e.money(s, c, amount, f"Bán {_products()[opt['sell']]['name']} theo tư vấn", ref, category='revenue')
                notes.append(f"Bán kèm đúng một {_products()[opt['sell']]['name'].lower()} (+{amount} xu).")
            elif opt.get('sell'):
                notes.append('Kệ đang hết món đó, hẹn khách lần sau.')
        elif opt['kind'] == 'upsell':
            delta -= 1
            e.money(s, c, opt['gain'], 'Hoa hồng bán kèm', ref, category='revenue')
            notes.append(f"Bán kèm thêm, hoa hồng +{opt['gain']} xu.")
            cr['follow'].append(dict(day=day + 1, fam=f['id'], ref=ref + '-regret', stars=2, text=opt['regret']))
            cr['follow'] = ar.last(cr['follow'], 8, 'baby.follow', c)
        else:
            delta -= 1
            notes.append('Lời khuyên chưa đúng: bé đủ sáu tháng nên chuyển sữa số 2.')
    if stars is None and r['trust'] >= TIPS_FROM and (not opt or opt['kind'] == 'honest'):
        tip = TIP
        e.money(s, c, tip, f"{f['parent']} gửi tiền bồi dưỡng", ref, category='tip')
    before = r['trust']
    _trust(r, delta)
    if stars is not None:
        _post(s, c, f, review, ref, stars)
    elif r['trust'] > before and r['trust'] in (3, 5):
        _post(s, c, f, f"Tiệm Mây Nhỏ nhớ bé {f['baby']} từng tuần, tư vấn thật lòng chứ không bán thừa. Cả nhà mình tin tiệm {TRUST_NAMES[r['trust']].lower()} rồi 💛", ref + '-trust', 5)
    told = r['told'] == day or before >= TELLS_WEIGHT
    r.update(visits=r['visits'] + 1, last=day, size=size, prod=lot['p'] if lot else None, next=r['next'] + f['every'], q=None, told=None,
             kg10=kg if told else r['kg10'])
    cr['today']['pickups'] += 1
    e.metric(c, 'care_pickups')
    head = f"Trao gói cho {f['parent']}: bỉm {size}" + (f" + {formula_name(lot['p'])} ({lot['id']})" if lot else '') + f" · +{total} xu."
    _log(cr, day, head + (' ' + ' '.join(notes) if notes else ''))
    good = stars is None and (not opt or opt['kind'] == 'honest')
    tail = f" ❤ {TRUST_NAMES[r['trust']]}." + (f" Khách gửi {tip} xu bồi dưỡng." if tip else '')
    return dict(message=head + (' ' + ' '.join(notes) if notes else ' Vừa vặn, đúng loại, còn hạn.') + tail, celebrate=good, correct=good if stars else None)


def _item_name(item: str) -> str:
    return f'bỉm {item}' if item in SIZES else f'hộp {formula_name(item)}'


def _order(s, c, cr, p):
    e = _e()
    need = e.need
    item = p.get('item')
    need(isinstance(item, str) and (item in SIZES or item in FORMULAS), 'Mã hàng không hợp lệ.')
    qty = e.integer(p.get('qty'), 1, 4)
    need(p.get('confirm') is True, 'Xác nhận đặt hàng nhé.')
    coming = sum(o['qty'] for o in cr['orders'] if o['item'] == item)
    if item in SIZES:
        have, cap, unit = cr['diapers'][item], DIAPER['cap'], DIAPER['cost']
    else:
        have, cap, unit = sum(x['qty'] for x in cr['lots'] if x['p'] == item), FORMULA['cap'], FORMULA['cost']
    need(have + coming + qty <= cap, f'Kệ chứa tối đa {cap} {"gói" if item in SIZES else "hộp"} mỗi loại (đang có {have}, chờ về {coming}).')
    need(len(cr['orders']) < 12, 'Đang chờ quá nhiều kiện. Nhận hàng rồi đặt tiếp nhé.')
    cost = unit * qty
    need(c['money'] >= cost, f'Cần {cost} xu để đặt hàng.')
    cr['seq'] += 1
    oid = f"care-order-{cr['seq']}"
    e.money(s, c, -cost, f'Đặt nhập {qty} × {_item_name(item)}', oid, category='stock')
    cr['orders'].append(dict(id=oid, item=item, qty=qty, day=c['day'] + 1))
    return dict(message=f'Đã đặt {qty} × {_item_name(item)} (−{cost} xu). Sáng mai hàng về kệ.')


def _pull(s, c, cr, p):
    e = _e()
    need = e.need
    day = c['day']
    lid = p.get('lot')
    lot = next((x for x in cr['lots'] if x['id'] == lid and x['qty'] > 0), None) if isinstance(lid, str) else None
    need(lot, 'Không có lô này trên kệ.')
    need(not safe_lot(lot, day), f"Lô {lot['id']} còn hạn tới {_gs().date_text(lot['exp'])} và không bị thu hồi.")
    value = lot['qty'] * FORMULA['cost']
    cr['lots'].remove(lot)
    cr['today']['pulled'] += 1
    if lot['recalled']:
        e.money(s, c, value, f"Hãng hoàn tiền lô thu hồi {lot['id']}", f"care-recall-{lot['id']}", category='stock')
        text = f"Rút {lot['qty']} hộp lô {lot['id']} bị thu hồi. Hãng hoàn {value} xu."
    else:
        cr['waste'] += value
        text = f"Rút {lot['qty']} hộp lô {lot['id']} quá hạn, bỏ đi {value} xu tiền hàng. Lần sau bán lô sắp hết hạn trước nhé."
    c['xp'] += 2
    _log(cr, day, text)
    return dict(message=text)


# ---------------------------------------------------------------- registry
def _reg_item(cr: dict, lid: str) -> str:
    return cr['reg']['lines'][lid]['swap'] or REG_LINES[lid][1]


def swaps(line_item: str) -> list:
    """Newborn-safe items a registry line can be swapped to (similar price)."""
    gs = _gs()
    names = _products()
    top = names[line_item]['price'] + 20
    return sorted((k for k in names if gs.LABELS[k]['use'] not in ('card',) and gs.suits(k, 0) and k != line_item and names[k]['price'] <= top
                   and names[k]['price'] >= names[line_item]['price'] - 40), key=lambda k: names[k]['price'])


def _reg_line(cr: dict, p: dict) -> tuple[str, dict]:
    need = _e().need
    lid = p.get('line')
    need(isinstance(lid, str) and lid in REG_LINES, 'Không có dòng này trong danh sách quà.')
    need(cr['reg']['state'] == 'open', 'Danh sách quà mừng chưa mở hoặc đã khép.')
    return lid, cr['reg']['lines'][lid]


def _swap(s, c, cr, p):
    e = _e()
    need = e.need
    lid, line = _reg_line(cr, p)
    need(not line['aside'], 'Món này đã để riêng vào hộp quà rồi.')
    need(line['swap'] is None, 'Dòng này đã đổi món rồi.')
    base = REG_LINES[lid][1]
    lab = _gs().LABELS[base]
    need(not _gs().suits(base, 0), f"Hộp ghi “{lab['label']}”: món này hợp với bé sơ sinh rồi, không cần đổi.")
    item = p.get('item')
    need(isinstance(item, str) and item in swaps(base), 'Chọn một món hợp bé sơ sinh, giá tương đương.')
    line['swap'] = item
    f = FAM['ly']
    r = cr['fam']['ly']
    _trust(r, 1)
    c['xp'] += 5
    cr['today']['honest'] += 1
    e.metric(c, 'honest_advice')
    name = _products()[item]['name']
    text = f"{f['parent']} đồng ý đổi {_products()[base]['name']} (hộp ghi “{lab['label']}”) sang {name} cho bé sơ sinh."
    _log(cr, c['day'], text)
    return dict(message=f"{f['parent']}: “Ôi mình không để ý nhãn. Đổi sang {name} nhé, cảm ơn bạn!”", celebrate=True)


def _aside(s, c, cr, p):
    e = _e()
    need = e.need
    lid, line = _reg_line(cr, p)
    need(c['day'] >= cr['start'] + REG_LINES[lid][3], 'Chưa có ai mua dòng này.')
    need(not line['aside'], 'Món này đã để riêng rồi.')
    item = _reg_item(cr, lid)
    qty = REG_LINES[lid][2]
    need(e.available(c, item) >= qty, f"Kệ không đủ {qty} × {_products()[item]['name']}. Đặt nhập ở Kho rồi để riêng sau nhé.")
    c['stock'][item] -= qty
    amount = _price(c, item) * qty
    e.money(s, c, amount, f"Bạn của {FAM['ly']['parent']} mua quà trong danh sách", f"care-reg-{lid}", category='revenue')
    line['aside'] = True
    text = f"Để riêng {qty} × {_products()[item]['name']} vào hộp quà mừng (+{amount} xu)."
    _log(cr, c['day'], text)
    return dict(message=text)


def _shower(s, c, cr, p):
    e = _e()
    need = e.need
    day = c['day']
    reg = cr['reg']
    need(reg['state'] == 'open', 'Danh sách quà mừng chưa mở hoặc đã khép.')
    shower = cr['start'] + REGISTRY['shower']
    need(day >= shower - 1, f"Tiệc mừng bé là ngày {_gs().date_text(shower)}. Trao hộp trước tiệc một ngày là đẹp.")
    bought = [lid for lid in REG_LINES if day >= cr['start'] + REG_LINES[lid][3]]
    boxed = [lid for lid in bought if reg['lines'][lid]['aside']]
    need(boxed, 'Hộp quà còn trống. Để riêng các món bạn bè đã mua trước nhé.')
    need(p.get('confirm') is True, 'Xác nhận giao hộp quà nhé.')
    missing = [lid for lid in bought if lid not in boxed]
    e.money(s, c, -min(c['money'], WRAP), 'Giấy gói hộp quà mừng', 'care-reg', category='materials')
    f = FAM['ly']
    r = cr['fam']['ly']
    unsafe = [lid for lid in boxed if not _gs().suits(_reg_item(cr, lid), 0)]
    reg['state'] = 'done'
    c['xp'] += 15 if not missing else 5
    e.metric(c, 'registry_done')
    if missing:
        # Friends were never charged for what the shop could not set aside.
        _trust(r, -1)
        name = _products()[_reg_item(cr, missing[0])]['name']
        _post(s, c, f, f"Hộp quà mừng tới kịp tiệc nhưng thiếu {name.lower()} bạn mình đã chọn, bạn ấy phải mua chỗ khác.", 'care-reg', 3)
        text = f"Đã giao hộp quà mừng cho {f['parent']}, còn thiếu {len(missing)} món bạn bè đã chọn."
    elif unsafe:
        _trust(r, -1)
        name = _products()[_reg_item(cr, unsafe[0])]['name']
        _post(s, c, f, f"Hộp quà mừng gói xinh lắm, nhưng có {name.lower()} hộp ghi 3+ cho bé sơ sinh. Giá mà tiệm nhắc mình sớm.", 'care-reg', 3)
        text = f"Đã giao hộp quà mừng cho {f['parent']}. Còn {name} ghi 3+ trong hộp: chưa hợp bé sơ sinh."
    else:
        _trust(r, 1)
        _post(s, c, f, f"Hộp quà mừng bé {f['baby']} đủ từng món bạn bè chọn, món nào cũng hợp bé sơ sinh. Cảm ơn Tiệm Mây Nhỏ 🍼", 'care-reg', 5)
        text = f"Đã giao hộp quà mừng cho {f['parent']}: đủ món, hợp bé sơ sinh."
    _log(cr, day, text)
    return dict(message=text, celebrate=not unsafe, correct=None if not unsafe else False)


def _shower_failed(s: dict, c: dict, cr: dict, day: int) -> str:
    e = _e()
    reg = cr['reg']
    reg['state'] = 'failed'
    back = 0
    for lid, line in reg['lines'].items():
        if line['aside']:
            item = _reg_item(cr, lid)
            qty = REG_LINES[lid][2]
            c['stock'][item] = min(24, c['stock'][item] + qty)
            back += _price(c, item) * qty
            line['aside'] = False
    if back:
        e.money(s, c, -min(c['money'], back), 'Hoàn tiền quà mừng chưa giao', 'care-reg', category='refund')
    _trust(cr['fam']['ly'], -2)
    f = FAM['ly']
    _post(s, c, f, 'Tới ngày tiệc mà hộp quà mừng vẫn chưa tới, bạn bè mình phải xin lại tiền. Buồn ghê.', 'care-reg', 1)
    text = f"Hộp quà mừng của {f['parent']} không kịp tiệc: hoàn {back} xu cho bạn bè." if back else f"Hộp quà mừng của {f['parent']} không kịp tiệc."
    _log(cr, day, text)
    return text


# ---------------------------------------------------------------- projection
def public(c: dict) -> dict:
    cr = raw(c)
    day = c['day']
    if not isinstance(cr, dict) or not isinstance(cr.get('fam'), dict) or not cr.get('day'):
        return dict(ready=False, opens=max(START_DAY, day + (1 if c.get('open') or day < START_DAY else 0)))
    gs = _gs()
    names = _products()
    fam = []
    for f in FAMILIES:
        r = cr['fam'][f['id']]
        st = status(cr, f, day)
        w = weeks(cr, f, day)
        row = dict(id=f['id'], parent=f['parent'], emoji=f['emoji'], baby=f['baby'], girl=f['girl'], status=st, trust=r['trust'],
                   trust_name=TRUST_NAMES[r['trust']], visits=r['visits'], last=r['last'], next=r['next'], next_date=gs.date_text(r['next']),
                   first=cr['start'] + f['first'], milk=f['milk'], feeding=f"Sữa {BRANDS[f['milk']]}" if f['milk'] else 'Bú mẹ hoàn toàn',
                   last_kg=r['kg10'], last_size=r['size'], last_prod=r['prod'], last_prod_name=formula_name(r['prod']) if r['prod'] else None,
                   missed=r['missed'], weeks=w if w >= 0 else None, born=cr['start'] + f['born'], born_date=gs.date_text(cr['start'] + f['born']),
                   due=False, late=False, kg=None, news=None, can_ask=False, question=None)
        if due(cr, f['id'], day):
            told = r['told'] == day or r['trust'] >= TELLS_WEIGHT
            q = QUESTIONS.get(r['q'] or '')
            row.update(due=True, late=day == r['next'] + 1, can_ask=not told,
                       kg=weight(f, w) if told else None, news=_news(cr, f, r, day) if told else None,
                       question=dict(text=q['text'], options=[dict(id=o['id'], label=o['label']) for o in q['options']]) if q else None)
        fam.append(row)
    lots = [dict(id=x['id'], p=x['p'], name=formula_name(x['p']), brand=BRANDS[FORMULAS[x['p']]['brand']], stage=FORMULAS[x['p']]['stage'],
                 range=STAGE_RANGE[FORMULAS[x['p']]['stage']], qty=x['qty'], exp=x['exp'], date=gs.date_text(x['exp']), left=x['exp'] - day,
                 expired=expired(x, day), recalled=x['recalled']) for x in sorted(cr['lots'], key=lambda x: (x['p'], x['exp'])) if x['qty'] > 0]
    reg = cr['reg']
    lines = []
    for lid, item, qty, n in REGISTRY['lines']:
        line = reg['lines'][lid]
        now = line['swap'] or item
        lab = gs.LABELS[now]
        lines.append(dict(id=lid, item=now, orig=item, name=names[now]['name'], orig_name=names[item]['name'], qty=qty, label=lab['label'], warn=lab['warn'],
                          price=_price(c, now) * qty, bought=day >= cr['start'] + n, bought_day=cr['start'] + n, aside=line['aside'], swapped=line['swap'] is not None,
                          stock=_e().available(c, now) if isinstance(c.get('stock'), dict) and now in c['stock'] else 0))
    shower = cr['start'] + REGISTRY['shower']
    reg_view = dict(state=reg['state'], family='ly', open=cr['start'] + REGISTRY['open'], shower=shower, shower_date=gs.date_text(shower),
                    lines=lines, swaps={x[1]: swaps(x[1]) for x in REGISTRY['lines']},
                    ready=reg['state'] == 'open' and day >= shower - 1 and all(x['aside'] for x in lines if x['bought']))
    names_of = {k: names[k]['name'] for k in {i for v in reg_view['swaps'].values() for i in v}}
    notices = [dict(day=n['day'], date=gs.date_text(n['day']), lot=n['lot'], name=formula_name(n['p'])) for n in cr['notices'][-3:]]
    orders = [dict(item=o['item'], name=_item_name(o['item']), qty=o['qty'], day=o['day']) for o in cr['orders']]
    alerts = sum(1 for x in lots if x['expired'] or x['recalled'])
    return dict(ready=True, day=day, rule=RULE, start=cr['start'], sizes=[dict(id=k, name=SIZE_INFO[k]['name'], range=SIZE_INFO[k]['range']) for k in SIZES],
                formulas=[dict(id=k, name=formula_name(k), stage=v['stage'], range=STAGE_RANGE[v['stage']]) for k, v in FORMULAS.items()],
                stage_weeks=STAGE_TWO_WEEKS, prices=dict(diaper=DIAPER['price'], formula=FORMULA['price'], diaper_cost=DIAPER['cost'],
                                                          formula_cost=FORMULA['cost'], diaper_cap=DIAPER['cap'], formula_cap=FORMULA['cap']),
                fam=fam, diapers=dict(cr['diapers']), lots=lots, orders=orders, notices=notices, reg=reg_view, item_names=names_of,
                log=[dict(x) for x in cr['log'][-6:]], today=dict(cr['today']), waste=cr['waste'],
                due=sum(1 for x in fam if x['due']), alerts=alerts, trust_names=list(TRUST_NAMES), tells_weight=TELLS_WEIGHT, tips_from=TIPS_FROM)


# ---------------------------------------------------------------- validation
def validate(c: dict) -> None:
    cr = raw(c)
    if cr is None:
        return
    e = _e()
    need = e.need
    integer = e.integer
    need(isinstance(cr, dict) and cr.get('v') == V, 'Dữ liệu góc bỉm sữa sai.')
    need(set(fresh(START_DAY)) <= set(cr), 'Góc bỉm sữa thiếu dữ liệu.')
    start = integer(cr['start'], START_DAY, 10**6)
    integer(cr['day'], 0, 10**6)
    integer(cr['seq'], 0, 10**6)
    integer(cr['waste'], 0, 10**9)
    fam = cr['fam']
    need(isinstance(fam, dict) and set(fam) == set(FAM), 'Sổ bé quen sai.')
    for fid, r in fam.items():
        need(isinstance(r, dict) and set(r) == FAM_KEYS, 'Hồ sơ gia đình sai.')
        integer(r['trust'], 0, 5)
        integer(r['next'], start, 10**6)
        integer(r['visits'], 0, 10**6)
        integer(r['missed'], 0, 10**6)
        for k in ('last', 'told'):
            need(r[k] is None or (type(r[k]) is int and start <= r[k] <= 10**6), 'Ngày trong sổ bé quen sai.')
        need(r['kg10'] is None or (type(r['kg10']) is int and 20 <= r['kg10'] <= 200), 'Cân nặng trong sổ sai.')
        need(r['size'] is None or r['size'] in SIZES, 'Size bỉm trong sổ sai.')
        need(r['prod'] is None or (FAM[fid]['milk'] and r['prod'] in FORMULAS and r['prod'][:2] == FAM[fid]['milk']), 'Loại sữa trong sổ sai.')
        need(isinstance(r['asked'], list) and len(r['asked']) <= len(QUESTIONS) and len(set(r['asked'])) == len(r['asked'])
             and all(q in QUESTIONS for q in r['asked']), 'Câu hỏi đã hỏi sai.')
        need(r['q'] is None or r['q'] == '' or r['q'] in QUESTIONS, 'Câu hỏi hôm nay sai.')
    d = cr['diapers']
    need(isinstance(d, dict) and set(d) == set(SIZES), 'Kệ bỉm sai.')
    for v in d.values():
        integer(v, 0, DIAPER['cap'])
    lots = cr['lots']
    need(isinstance(lots, list) and len(lots) <= 30, 'Kệ sữa sai.')
    for lot in lots:
        need(isinstance(lot, dict) and set(lot) == LOT_KEYS and isinstance(lot['id'], str) and LOT_ID.fullmatch(lot['id'])
             and lot['p'] in FORMULAS and lot['id'][:3].lower() == lot['p'], 'Lô sữa sai.')
        integer(lot['qty'], 0, FORMULA['cap'])
        integer(lot['exp'], 0, 10**6)
        integer(lot['got'], 0, 10**6)
        need(type(lot['recalled']) is bool, 'Cờ thu hồi sai.')
    need(len({x['id'] for x in lots}) == len(lots), 'Trùng mã lô sữa.')
    for p in FORMULAS:
        need(sum(x['qty'] for x in lots if x['p'] == p) <= FORMULA['cap'], 'Kệ sữa quá sức chứa.')
    need(isinstance(cr['orders'], list) and len(cr['orders']) <= 12, 'Đơn nhập sai.')
    for o in cr['orders']:
        need(isinstance(o, dict) and set(o) == {'id', 'item', 'qty', 'day'} and isinstance(o['id'], str) and len(o['id']) <= 40
             and (o['item'] in SIZES or o['item'] in FORMULAS), 'Đơn nhập sai.')
        integer(o['qty'], 1, 4)
        integer(o['day'], 0, 10**6)
    need(isinstance(cr['notices'], list) and len(cr['notices']) <= 6, 'Thông báo thu hồi sai.')
    for n in cr['notices']:
        need(isinstance(n, dict) and set(n) == {'day', 'lot', 'p'} and isinstance(n['lot'], str) and LOT_ID.fullmatch(n['lot']) and n['p'] in FORMULAS, 'Thông báo thu hồi sai.')
        integer(n['day'], 0, 10**6)
    reg = cr['reg']
    need(isinstance(reg, dict) and set(reg) == {'lines', 'state'} and reg['state'] in ('soon', 'open', 'done', 'failed'), 'Danh sách quà mừng sai.')
    need(isinstance(reg['lines'], dict) and set(reg['lines']) == set(REG_LINES), 'Dòng quà mừng sai.')
    for lid, line in reg['lines'].items():
        need(isinstance(line, dict) and set(line) == {'aside', 'swap'} and type(line['aside']) is bool, 'Dòng quà mừng sai.')
        need(line['swap'] is None or (isinstance(line['swap'], str) and line['swap'] in swaps(REG_LINES[lid][1])), 'Món đổi trong danh sách quà sai.')
    need(isinstance(cr['log'], list) and len(cr['log']) <= 12, 'Nhật ký góc bỉm sữa sai.')
    for row in cr['log']:
        need(isinstance(row, dict) and set(row) == {'day', 'text'}, 'Nhật ký góc bỉm sữa sai.')
        integer(row['day'], 0, 10**6)
        e.clean_text(row['text'], 400)
    need(isinstance(cr['follow'], list) and len(cr['follow']) <= 8, 'Lời hẹn góc bỉm sữa sai.')
    for fu in cr['follow']:
        need(isinstance(fu, dict) and set(fu) == {'day', 'fam', 'ref', 'stars', 'text'} and fu['fam'] in FAM, 'Lời hẹn góc bỉm sữa sai.')
        integer(fu['day'], 0, 10**6)
        integer(fu['stars'], 1, 5)
        e.clean_text(fu['ref'], 80)
        e.clean_text(fu['text'], 400)
    need(isinstance(cr['today'], dict) and set(cr['today']) == set(TODAY_KEYS), 'Tổng kết góc bỉm sữa sai.')
    for v in cr['today'].values():
        integer(v, 0, 10**6)


# ---------------------------------------------------------------- tests / staff helper
def best_hand(c: dict, fid: str) -> dict:
    """The right pickup for a due family (tests use it; never shown to players)."""
    cr = raw(c)
    f = FAM[fid]
    r = cr['fam'][fid]
    day = c['day']
    w = weeks(cr, f, day)
    want = product_for(f, w)
    lots = sorted((x for x in cr['lots'] if x['p'] == want and x['qty'] > 0 and safe_lot(x, day)), key=lambda x: x['exp'])
    q = QUESTIONS.get(r['q'] or '')
    return dict(family=fid, size=size_for(weight(f, w)), lot=lots[0]['id'] if lots else None,
                advice=next((o['id'] for o in q['options'] if o['kind'] == 'honest'), None) if q else None, confirm=True)


# ---------------------------------------------------------------- wiring
def install(ns: dict) -> None:
    """Wrap giftshop's hooks (ns = giftshop's globals()). Idempotent."""
    if ns.get('_care_installed'):
        return
    ns['_care_installed'] = True
    orig = {k: ns[k] for k in ('handle', 'on_start', 'on_close', 'public', 'validate', 'upgrade')}

    def handle_(s, c, action, p):
        if action.startswith('gift_care_'):
            return handle(s, c, action, p)
        return orig['handle'](s, c, action, p)

    def on_start_(s, c):
        orig['on_start'](s, c)
        on_start(s, c)

    def on_close_(s, c):
        out = dict(orig['on_close'](s, c))
        care = on_close(s, c)
        if care and care['lines']:
            out['care'] = care
        return out

    def public_(c):
        out = orig['public'](c)
        out['care'] = public(c)
        return out

    def validate_(c):
        orig['validate'](c)
        validate(c)

    def upgrade_(c):
        orig['upgrade'](c)
        upgrade(c)

    ns.update(handle=handle_, on_start=on_start_, on_close=on_close_, public=public_, validate=validate_, upgrade=upgrade_)
