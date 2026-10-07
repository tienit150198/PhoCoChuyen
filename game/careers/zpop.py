"""Tiệm album Mây Pop: chị Thơ's ZPOP album and fan-goods shop on Phố chợ (plugin career `zpop`).

Content (groups, albums, products, customers, the annoying ones, surprises) lives in zpop_content.py; everything
there is fiction (BLANKPINK, 7GIÓ, KIWIZ, Búa hồng, BLINKY, Bảng Zchart). What the job is:

* the morning (``setup`` task): count the limited copies and the POB sets, put up the sign "N limited copies a person"
  (the distributor's rule of the day: 2 on a comeback day, else 3), test the demo lightstick (a weak one takes a pack of
  AAA batteries), and on the pre-order deadline day close the pre-orders with the distributor: the number in the book,
  paid at cost into the stock (a real purchase); then open;
* a customer (``sale`` task): their words name what they want, often by what is inside rather than by the product
  (a member's card for sure: only that member's Digipack; a CD: not the Kit version; a lightstick with Bluetooth: ver.2,
  which takes AA batteries; the cheapest: the opened display copy). The player fills the basket from the shelves, turns
  on what was asked (Zchart scan, the poster rolled in a tube, fansign entries, the shop's POB) and rings it up; the
  shared till takes the cash. Limited copies are capped per person;
* an annoying customer: a decision with probes and answers (zpop_content.TW). The other side decides from a hidden
  trait rolled from the task id: the card trader who wants to open albums before paying, the parent who does not know
  the group (the kid's note decides the basket), the chart buyer who wants only receipts, the reseller, a pre-order picked
  up under another name, the fan who wants a fansign win promised, another store's POB, a queue jumper;
* a ``case``: someone comes back with a problem (a refund for the "wrong" member's card, a fake lightstick "under
  warranty", a lightstick that will not pair, bootleg albums on consignment). No basket, a decision;
* the apprenticeship: for the first three customers chị Thơ looks at the basket before it is rung up and stops each kind
  of mistake once (nothing recorded).

Money only moves through the engine: the price of the goods sold (bought earlier in the Kho at cost), a refund out, a cost.
Nothing is paid that a customer did not hand over. Every random thing is rolled from the day, slot or task id.
"""
from __future__ import annotations

import copy
import hashlib

from ..jsoncopy import tree_copy
from . import kit
from . import till
from .. import consequences as cq
from .zpop_content import (ALBUMS, APPRENTICE, BOOK_NAMES, CASE_TW, CASES, CATCH, CHART, DESK, DISTRIBUTOR, FANSIGN_SLOTS, GROUPS,
                           INTRO, LESSONS, LIMIT_OPTIONS, MEMBERS, MODS, ORDERS, OTHER_STORES, PEOPLE, POB_COMEBACK, PRICES,
                           REG_STORY, SALE_TW, SELL, SITUATIONS, SKU, SKUS, SLIP_NOTE, SLIP_WORDS, STORE, TW)

ID = 'zpop'
GEN = 1
MOD = {m['id']: m for m in MODS}
KINDS = ('setup', 'sale', 'case')
STAGES = ('prep', 'pay', 'done')
OPTS = ('zchart', 'tube', 'raffle', 'pob')
QUALITY = ('good', 'ok', 'bad')
MAX_CART = 60          # units in one basket
MAX_LINE = 40          # units of one product
CLOSE_MAX = 60         # copies closed with the distributor in one morning
CASE_SHARE = 18        # % of customers from day 2 who come back with a problem
POB_OPENING = 10       # POB sets the shop starts with (the distributor sends more on a comeback morning)
ITEMS = [dict(id=x['id'], name=x['name'], emoji=x['emoji'], group=x['group'], unit=x['unit'], cost=x['cost'], start=x['start'])
         for x in SKUS]


# ================================================================ small helpers
def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def mod_of(day: int) -> dict:
    return kit.daily(ID, day, MODS)


def limit_of(day: int) -> int:
    """The distributor's rule of the day: limited copies a person (the sign must say it)."""
    return mod_of(day)['limit']


def fam(sku: str) -> str:
    """What a product is a version of (a wrong pick of the same family is a wrong version, not an extra)."""
    x = SKU[sku]
    if x.get('album'):
        return x['album']
    return 'pin' if sku.startswith('pin_') else x['group']


def _npc_index(t: dict) -> int:
    try:
        return int(t['npc'].rsplit('_', 1)[1]) - 1
    except (ValueError, KeyError, IndexError):
        return 0


def _who(t: dict) -> str:
    i = _npc_index(t)
    return PEOPLE[i][0] if 0 <= i < len(PEOPLE) else 'Khách'


def _price(c: dict, sku: str) -> int:
    return max(1, int(kit.price(c, sku, PRICES[sku])))


def fansign_entries(day: int) -> int:
    """Entries already in the fansign draw (every store in town), shown honestly next to the 30 places."""
    return 600 + 37 * max(1, int(day))


def odds_text(day: int) -> dict:
    n = fansign_entries(day)
    pct = FANSIGN_SLOTS * 100 / n
    return dict(slots=FANSIGN_SLOTS, entries=n, pct=f'{pct:.1f}%'.replace('.', ','))


def book_of(day: int) -> list[dict]:
    """The pre-order book for the deadline morning: who ordered how many Jewel cases (pure from the day)."""
    r = kit.rng(ID, 'book', day)
    names = list(BOOK_NAMES)
    r.shuffle(names)
    return [dict(name=n, qty=1 + r.randrange(3), phone=f'{r.randrange(10000):04d}') for n in names[:3 + r.randrange(3)]]


def book_total(day: int) -> int:
    return sum(x['qty'] for x in book_of(day))


def demo_weak(day: int) -> bool:
    """The demo lightstick's batteries are flat this morning."""
    return day >= 2 and _hash('zp-demo', day) % 3 == 0


# ================================================================ tasks
def _pick(rows: list, r) -> dict:
    total = sum(x.get('weight', 1) for x in rows)
    x = r.random() * total
    for row in rows:
        x -= row.get('weight', 1)
        if x < 0:
            return row
    return rows[-1]


def _order_for(day: int, slot: int, mod: str) -> tuple[str, dict]:
    if day == 1:
        return 'sale', ORDERS[(slot - 1) % 3]
    r = kit.rng(ID, day, slot)
    cases = [x for x in CASES if x['min_day'] <= day]
    if cases and r.randrange(100) < CASE_SHARE:
        return 'case', _pick(cases, r)
    pool = [o for o in ORDERS if o['min_day'] <= day and o['mod'] in (None, mod)]
    weighted = [dict(o, weight=o['weight'] * (3 if o['mod'] else 1)) for o in pool]
    return 'sale', _pick(weighted, r)


def _trait(script: str, weights: dict | None, day: int, slot: int) -> str:
    w = weights or TW[script]['traits']
    keys = sorted(w)
    total = sum(w[k] for k in keys)
    x = kit.rng(ID, 'trait', day, slot).random() * total
    for k in keys:
        x -= w[k]
        if x < 0:
            return k
    return keys[-1]


def _fresh_tw(script: str | None) -> dict | None:
    if not script:
        return None
    return dict(asked=[], ans=None, round=0, tries=0, q=None, out=None, done=False, nolimit=False)


def _fresh_fields(script: str | None = None) -> dict:
    return dict(gen=GEN, stage='prep', cart={}, opt=dict(zchart=False, tube=False, raffle=False, pob=False), tw=_fresh_tw(script),
                price=None, cash=None, cost=0, disc=0, sold=None, entries=0, story=None)


def make_task(day: int, slot: int, serial: int) -> dict:
    mod = mod_of(day)
    if slot == 0:
        note = {'comeback': f'Comeback: Jewel tối đa {mod["limit"]} bản/người, POB tặng kèm PINK STATIC.',
                'chot': 'Hạn chốt: cộng sổ đặt trước, chốt đúng số Jewel với nhà phân phối.',
                'cosplay': 'Ngày cosplay: dọn góc standee cho hội cosplay chụp.',
                'rain': 'Mưa chiều: kê thùng album lên cao.'}.get(mod['id'], 'Đếm bản giới hạn, dựng biển, thử búa trưng bày rồi mở tiệm.')
        return kit.base_task(ID, day, 0, serial, 0, 'Mở tiệm album đầu ngày',
                             'Chị Thơ nhắn: “Chị đi lấy hàng. Em đếm bản giới hạn, dựng biển giới hạn, thử cây búa trưng bày rồi hẵng mở tiệm nghe.”',
                             kind='setup', needs=dict(setup=True, note=note, limit=mod['limit'], chot=mod['id'] == 'chot'),
                             _tw=None, **_fresh_fields())
    kind, o = _order_for(day, slot, mod['id'])
    script = o['tw']
    trait = _trait(script, o.get('tw_w'), day, slot) if script else None
    if kind == 'case':
        say = (TW[script].get('say') or {}).get(trait) or o['say']
        needs = dict(case=True, say=say, tw=script, note='')
        return kit.base_task(ID, day, slot, serial, o['npc'], o['title'], say, kind='case', needs=needs,
                             _tw=dict(trait=trait), **_fresh_fields(script))
    needs = dict(lines=copy.deepcopy(o['lines']), say=o['say'], note=o['note'], zchart=o['zchart'], tube=o['tube'],
                 raffle=o['raffle'], pob=o['pob'], tw=script, upto=o['upto'], guess=o['guess'],
                 book=copy.deepcopy(o['book']), limit=mod['limit'])
    return kit.base_task(ID, day, slot, serial, o['npc'], o['title'], o['say'], kind='sale', needs=needs,
                         _tw=dict(trait=trait) if script else None, **_fresh_fields(script))


FIXED = ('needs', '_tw')


def on_task(s: dict, c: dict, t: dict) -> None:
    if t['kind'] == 'setup':
        t['known'] = True
        if t['status'] == 'new':
            t['status'] = 'understood'


# ================================================================ the shop's data
def _fresh_shop(day: int) -> dict:
    return dict(day=day, open=False, counted=False, sign=None, demo=False, battery=False, closed=False)


def _fresh_today(day: int) -> dict:
    return dict(day=day, customers=0, units=0, revenue=0, entries=0, cases=0, refused=0)


def initial() -> dict:
    return dict(v=1, intro=False, shop=_fresh_shop(0), regulars={}, today=_fresh_today(0),
                stats=dict(customers=0, units=0, entries=0, fair=0, cases=0, sticks=0), desk=kit.desk_initial(),
                learn=dict(task=None, codes=[], done=False), pob=POB_OPENING, zban=0, raffle=0)


def _data(c: dict) -> dict:
    d = c['ext']['data']
    base = initial()
    for k, v in base.items():
        d.setdefault(k, copy.deepcopy(v))
    for k in ('stats', 'today', 'shop', 'learn'):
        for kk, v in base[k].items():
            d[k].setdefault(kk, v)
    for k, v in kit.desk_initial().items():
        d['desk'].setdefault(k, copy.deepcopy(v))
    return d


# ================================================================ the actions
FREE = ('zp_intro',)
NO_TICK = ('zp_intro', 'zp_desk', 'zp_count', 'zp_sign', 'zp_demo', 'zp_battery', 'zp_add', 'zp_drop', 'zp_opt', 'zp_probe',
           'zp_pay', 'zp_short')
PHYSICAL = ('zp_ring', 'zp_close')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    d = _data(c)
    if name == 'zp_intro':
        d['intro'] = True
        return dict(message='Vào việc thôi! Kệ album đã xếp, Búa hồng trưng bày đang nháy.')
    desk = d['desk']
    if name == 'zp_desk':
        return kit.desk_choose(s, c, ID, desk, DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở tiệm, quyết xong rồi bán tiếp nhé.')
    fn = ACTIONS.get(name)
    kit.need(fn, 'Thao tác không có ở tiệm album.')
    result = fn(s, c, d, p)
    _after(s, c, d, result)
    return result


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    if learning(d):
        return             # no surprises while chị Thơ is still teaching
    kit.desk_tick(s, c, ID, desk, DESK, mod_of(c['day'])['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def _task(c: dict, p: dict, kinds=None) -> dict:
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm album.')
    if kinds:
        kit.need(t['kind'] in kinds, 'Thao tác này không dành cho việc đang làm.')
    return t


def _open_rules(d: dict, setup=None, need=kit.need) -> None:
    """The shop must be open before any customer (public_data sends it as can.open, the fix brings up the morning)."""
    need(d['shop']['open'], 'Chưa mở tiệm: đếm bản giới hạn, dựng biển, thử búa rồi bấm “Mở tiệm” nhé.',
         fix=dict(cmd='task_select', payload=dict(task=setup), label='🏪 Mở tiệm') if setup else None)


def _setup_id(c: dict):
    return next((t['id'] for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'setup'
                 and t.get('status') not in ('completed', 'referred', 'cancelled')), None)


def _need_prep(t: dict) -> None:
    kit.need(t['known'], 'Hỏi khách cần gì đã nhé.')
    kit.need(t['stage'] == 'prep', 'Khách này đã tính tiền rồi.')


def learning(d: dict) -> bool:
    """Học nghề: the first APPRENTICE customers, chị Thơ at your side."""
    return not d['learn']['done'] and d['stats']['customers'] < APPRENTICE


# ---------------------------------------------------------------- the morning
def _count(s, c, d, p):
    d['shop']['counted'] = True
    return dict(message=f'📦 Đếm kho: Jewel còn {kit.stock(c, "ps_jewel")} bản · POB còn {d["pob"]} bộ · ống poster còn {kit.stock(c, "ong_poster")}.')


def _sign(s, c, d, p):
    n = p.get('n')
    kit.need(type(n) is int and n in LIMIT_OPTIONS, 'Chọn một số trên biển giới hạn.')
    kit.need(not d['shop']['open'], 'Tiệm mở rồi, biển đã dựng.')
    d['shop']['sign'] = n
    return dict(message=f'🚫 Dựng biển: “Bản giới hạn tối đa {n} bản/người”.' if n else '🚫 Dựng biển: “Không giới hạn”.')


def _demo(s, c, d, p):
    d['shop']['demo'] = True
    if demo_weak(c['day']) and not d['shop']['battery']:
        return dict(message='🔨 Bật cây Búa hồng trưng bày: nháy yếu rồi tắt. Pin AAA hết, thay vỉ mới đi.', correct=False)
    return dict(message='🔨 Bật cây Búa hồng trưng bày: sáng hồng rực, đổi màu đủ năm chế độ.')


def _battery(s, c, d, p):
    kit.need(kit.stock(c, 'pin_aaa') > 0, 'Hết pin AAA trong kho. Nhập thêm ở Kho nhé.')
    kit.need(not d['shop']['battery'], 'Đã thay pin rồi.')
    kit.take(c, 'pin_aaa', 1)
    d['shop']['battery'] = True
    return dict(message='🔋 Thay ba viên AAA cho búa trưng bày: sáng lại rực rỡ.')


def _close(s, c, d, p):
    """The pre-order deadline: order the book's Jewel cases from the distributor, paid at cost now."""
    t = _task(c, p, ('setup',))
    kit.need(mod_of(c['day'])['id'] == 'chot', 'Hôm nay không phải hạn chốt đặt trước.')
    kit.need(not d['shop']['closed'], 'Đã chốt đơn với nhà phân phối rồi.')
    qty = kit.integer(p.get('qty'), 0, CLOSE_MAX)
    unit = SKU['ps_jewel']['cost']
    cost = qty * unit
    from .. import inventory
    room = max(0, inventory.capacity(ID) - kit.stock(c, 'ps_jewel'))
    kit.need(qty <= room, f'Kho chỉ còn chỗ cho {room} bản Jewel.')
    kit.need(c['money'] >= cost, f'Chốt {qty} bản cần {cost} xu, quỹ tiệm chưa đủ.')
    if qty:
        kit.money(s, c, -cost, f'Chốt đặt trước {qty} bản Jewel · {DISTRIBUTOR}', t['id'], 'stock')
        kit.add_lot(c, 'ps_jewel', qty, unit, 999, 'npp')
    d['shop']['closed'] = True
    need = book_total(c['day'])
    kit.start_work(t)
    if qty < need:
        t['mistakes'] += 1
        cq.slip(t, 'close_short', 2, f'Sổ ghi {need} bản mà chỉ chốt {qty}: có người đặt trước sẽ không có hàng.', 'chốt thiếu đặt trước')
    elif qty > need + 2:
        cq.slip(t, 'close_over', 1, f'Sổ ghi {need} bản mà chốt tới {qty}: tiền nằm chết trong kho.', 'chốt dư đặt trước')
    return dict(message=f'📒 Chốt {qty} bản Jewel với {DISTRIBUTOR}: −{cost} xu, hàng đã về kho.')


def _open(s, c, d, p):
    t = _task(c, p, ('setup',))
    b = d['shop']
    kit.need(not b['open'], 'Tiệm mở rồi.')
    rule = limit_of(c['day'])
    if not b['counted']:
        t['mistakes'] += 1
        cq.slip(t, 'no_count', 1, 'Chưa đếm bản giới hạn đã mở tiệm, bán quá tay lúc nào không hay.', 'chưa đếm kho')
    if b['sign'] != rule:
        t['mistakes'] += 1
        cq.slip(t, 'sign', 2, f'Biển giới hạn ghi sai: hôm nay nhà phân phối cho {rule} bản/người.', 'biển giới hạn sai')
    if not b['demo']:
        t['mistakes'] += 1
        cq.slip(t, 'no_demo', 1, 'Búa trưng bày chưa thử, khách hỏi mới biết tắt ngóm.', 'chưa thử búa trưng bày')
    elif demo_weak(c['day']) and not b['battery']:
        t['mistakes'] += 1
        cq.slip(t, 'demo_dead', 1, 'Búa trưng bày nháy yếu cả ngày, khách tưởng hàng lỗi.', 'búa trưng bày hết pin')
    if mod_of(c['day'])['id'] == 'chot' and not b['closed']:
        t['mistakes'] += 1
        cq.slip(t, 'no_close', 2, 'Quá hạn chốt mà chưa đặt hàng: khách đặt trước sẽ không có Jewel.', 'quên chốt đặt trước')
    b['open'] = True
    kit.start_work(t)
    ok = not cq.slips(t)
    kit.complete(s, c, t, 0, 'Đếm kho, dựng biển giới hạn, thử búa trưng bày.')
    return dict(message='💿 Mở tiệm! ' + ('Chị Thơ nhắn: “Ngon, hôm nay bán đắt nha!”' if ok else 'Chị Thơ nhắn: “Mở đi em, mai nhớ kỹ hơn nghe.”'),
                celebrate=ok)


# ---------------------------------------------------------------- the basket
def _add(s, c, d, p):
    t = _task(c, p, ('sale',))
    _open_rules(d)
    _need_prep(t)
    sku = kit.one_of(p.get('sku'), SELL, 'Kệ không có món này.')
    cart = t['cart']
    _add_rules(c, t, sku)
    cart[sku] = cart.get(sku, 0) + 1
    kit.start_work(t)
    x = SKU[sku]
    return dict(message=f'{x["emoji"]} Lấy {x["name"]} ({cart[sku]}).')


def _add_rules(c: dict, t: dict, sku: str, need=kit.need) -> None:
    """One more of this product: it must be on the shelf, the basket not too big (public_task: can.zp_add)."""
    have = t['cart'].get(sku, 0)
    need(kit.stock(c, sku) > have, f'Kệ hết {SKU[sku]["name"]} rồi. Nhập thêm ở Kho, hoặc nói thật với khách.',
         fix=dict(act='inventory', label='📦 Kho'))
    need(have < MAX_LINE and sum(t['cart'].values()) < MAX_CART, 'Giỏ đầy rồi.')


def _drop(s, c, d, p):
    t = _task(c, p, ('sale',))
    _need_prep(t)
    sku = kit.one_of(p.get('sku'), SELL, 'Kệ không có món này.')
    cart = t['cart']
    kit.need(cart.get(sku, 0) > 0, 'Món này chưa có trong giỏ.')
    cart[sku] -= 1
    if not cart[sku]:
        del cart[sku]
    return dict(message=f'↩️ Cất lại {SKU[sku]["name"]}.')


def _opt(s, c, d, p):
    t = _task(c, p, ('sale',))
    _need_prep(t)
    key = kit.one_of(p.get('key'), OPTS, 'Không có lựa chọn này.')
    on = p.get('on')
    kit.need(type(on) is bool, 'Bật hay tắt?')
    if on:
        _opt_rules(c, d, key)
    t['opt'][key] = on
    word = dict(zchart=('🧾 Bật quét Zchart cho từng bản.', '🧾 Tắt quét Zchart.'),
                tube=('🧻 Cuộn poster vào ống.', '🧻 Để poster gập trong album.'),
                raffle=('🎟️ Ghi phiếu fansign cho mỗi bản.', '🎟️ Không ghi phiếu fansign.'),
                pob=('🎁 Kèm POB Mây Pop.', '🎁 Không kèm POB.'))[key]
    return dict(message=word[0] if on else word[1])


def _opt_rules(c: dict, d: dict, key: str, need=kit.need) -> None:
    """Turning an option on (public_data: can.opt)."""
    if key == 'zchart':
        need(d['zban'] < c['day'], f'{CHART} đang khóa quét của tiệm tới hết ngày {d["zban"]}.')
    elif key == 'tube':
        need(kit.stock(c, 'ong_poster') > 0, 'Hết ống cuộn poster. Nhập thêm ở Kho nhé.', fix=dict(act='inventory', label='📦 Kho'))
    elif key == 'pob':
        need(d['pob'] > 0, 'Hết POB rồi, nói thật với khách nhé.')


def ring_slips(c: dict, t: dict) -> list[tuple]:
    """(code, weight, the customer's words, short note) for what is wrong with the basket as it is now."""
    n, cart, opt = t['needs'], t['cart'], t['opt']
    tw = t.get('tw') or {}
    limit = n['limit']
    left = dict(cart)
    missing = []
    for line in n['lines']:
        skus = line['any']
        want = line['qty']
        if n.get('upto'):
            want = min(want, sum(kit.stock(c, x) for x in skus))
        got = 0
        for x in skus:
            k = min(left.get(x, 0), line['qty'] - got)
            left[x] = left.get(x, 0) - k
            got += k
        if any(SKU[x].get('limited') for x in skus) and limit and not tw.get('nolimit'):
            want = min(want, limit)
        if got < want:
            missing.append(line)
    out = []
    for line in missing:
        fams = {fam(x) for x in line['any']}
        alts = [x for x, q in left.items() if q > 0 and fam(x) in fams]
        for x in alts:
            left[x] = 0
        code = (line['code'] or 'version') if alts else 'missing'
        words = SLIP_WORDS[code] if code not in ('version', 'missing') else (
            f'Tôi dặn {line["label"].lower()} mà.' if code == 'version' else f'Thiếu {line["label"].lower()} rồi.')
        out.append((code, 2, words, SLIP_NOTE[code]))
    extra = [x for x, q in left.items() if q > 0]
    if extra:
        names = ', '.join(SKU[x]['short'] for x in extra)
        out.append(('extra', 2 if n.get('tw') == 'parent' else 1, f'{SLIP_WORDS["extra"]} ({names})', SLIP_NOTE['extra']))
    if limit and not tw.get('nolimit'):
        for x, q in cart.items():
            if SKU[x].get('limited') and q > limit:
                out.append(('limit', 2, SLIP_WORDS['limit'], SLIP_NOTE['limit']))
                break
    pob_left = (c['ext'].get('data') or {}).get('pob', 0)
    for key, code, w in (('zchart', 'zchart', 2), ('tube', 'poster', 1), ('raffle', 'raffle', 1), ('pob', 'pob', 1)):
        if n.get(key) and not opt.get(key) and not (key == 'pob' and not pob_left):   # no POB left: said honestly, no slip
            out.append((code, w, SLIP_WORDS[code], SLIP_NOTE[code]))
    return out


def _catch(d: dict, c: dict, t: dict) -> dict | None:
    """While learning, chị Thơ looks at the basket before it is rung up: the first time a kind of mistake shows she
    stops you and says how to fix it (nothing recorded). The same mistake again goes through."""
    if not learning(d):
        return None
    lr = d['learn']
    if lr['task'] != t['id']:
        lr['task'], lr['codes'] = t['id'], []
    for code, *_ in ring_slips(c, t):
        if code in CATCH and code not in lr['codes']:
            lr['codes'].append(code)
            return dict(message=f'💿 Chị Thơ: “{CATCH[code]}”', correct=False, lesson=code)
    return None


def _ring_rules(c: dict, t: dict, need=kit.need) -> None:
    """Ring up (public_task: can.zp_ring): the basket filled, the customer's matter settled, the goods still there."""
    tw = t.get('tw')
    need(not tw or tw['done'], 'Còn chuyện với khách chưa xong: hỏi, rồi chọn cách trả lời nhé.', fix=dict(sel='.zp-tw', label='👉 Trả lời khách'))
    need(sum(t['cart'].values()) > 0, 'Giỏ còn trống: lấy hàng khách cần trước đã.')
    for x, q in t['cart'].items():
        need(kit.stock(c, x) >= q, f'Kệ chỉ còn {kit.stock(c, x)} {SKU[x]["name"]}. Bớt lại trong giỏ nhé.')


def _ring(s, c, d, p):
    t = _task(c, p, ('sale',))
    _open_rules(d)
    _need_prep(t)
    _ring_rules(c, t)
    opt = t['opt']
    if opt['tube']:
        _opt_rules(c, d, 'tube')
    caught = _catch(d, c, t)
    if caught:
        return caught
    for code, weight, words, note in ring_slips(c, t):
        t['mistakes'] += 1
        cq.slip(t, code, weight, words, note)
    cost = 0
    for x, q in sorted(t['cart'].items()):
        cost += kit.take(c, x, q)
    if opt['tube']:
        cost += kit.take(c, 'ong_poster', 1)
    fs = sum(q for x, q in t['cart'].items() if ALBUMS.get(SKU[x].get('album'), {}).get('fansign'))
    if opt['pob']:
        give = min(d['pob'], sum(q for x, q in t['cart'].items() if SKU[x].get('album') == 'ps') or 1)
        d['pob'] -= give
    if opt['raffle'] and fs:
        t['entries'] = min(99, fs)
        d['raffle'] = min(10 ** 7, d['raffle'] + fs)
        d['today']['entries'] += fs
        d['stats']['entries'] += fs
    total = sum(_price(c, x) * q for x, q in t['cart'].items())
    price = max(1, total * (100 - t['disc']) // 100)
    t['cost'], t['price'], t['sold'] = cost, price, dict(t['cart'])
    t['stage'] = 'pay'
    t['cash'] = till.new(price, t['id'], c=c, t=t)
    units = sum(t['cart'].values())
    d['today']['units'] += units
    d['stats']['units'] += units
    d['stats']['sticks'] += sum(q for x, q in t['cart'].items() if SKU[x]['group'] == 'stick')
    rec = t['cash']
    head = f'🧾 Tính tiền {units} món · {price} xu' + (f' (bớt {t["disc"]}%)' if t['disc'] else '') + '.'
    if t['entries']:
        head += f' 🎟️ {t["entries"]} phiếu fansign.'
    return dict(message=f'{head} Khách đưa {sum(rec["tender"])} xu: thối lại cho đúng.')


def _decline(s, c, d, p):
    """Out of what the customer wants: say so honestly (the shelf must really be empty for one of the asks)."""
    t = _task(c, p, ('sale',))
    _need_prep(t)
    kit.need(any(sum(kit.stock(c, x) for x in line['any']) == 0 for line in t['needs']['lines']),
             'Kệ còn đủ hàng khách cần mà.')
    t['cart'] = {}
    kit.start_work(t)
    d['today']['refused'] += 1
    msg = _finish(s, c, d, t, 0, f'Nói thật với {_who(t)}: kệ hết món khách cần, hẹn hàng về.')
    return dict(message='🙏 ' + msg)


def _pay(s, c, d, p):
    t = _task(c, p, ('sale',))
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    who = _who(t)
    rec = t['cash']
    chk = till.check(s, c, t, rec, p.get('change'), who)
    if chk['stop']:
        return dict(message='💵 ' + chk['message'], correct=False)
    react = cq.react(s, c, t, t['price'], who=who)
    stl = till.settle(s, c, t, rec, react, who)
    net = react['pay'] - stl['loss']
    d['today']['customers'] += 1
    d['stats']['customers'] += 1
    d['today']['revenue'] += max(0, net)
    if not cq.slips(t):
        d['stats']['fair'] += 1
    parts = [x for x in (react['message'], stl['message']) if x]
    msg = _finish(s, c, d, t, max(0, net), ' '.join(parts))
    if net < 0:
        lost = min(-net, c['money'])
        if lost:
            kit.money(s, c, -lost, f'Thối dư cho khách: {t["title"]}'[:120], t['id'], 'change_loss')
    given = sum(rec['change'])
    head = f'💵 Thu {t["price"]} xu' + (f', thối {given} xu.' if given else '.')
    grad = _graduate(d)
    return dict(message=f'{head} {msg}{grad}'.strip(), celebrate=not cq.slips(t) or bool(grad))


def _short(s, c, d, p):
    t = _task(c, p)
    kit.need(t['stage'] == 'pay' and isinstance(t.get('cash'), dict), 'Chưa đến lúc thu tiền.')
    return till.short_action(s, c, t, t['cash'], p, _who(t))


# ---------------------------------------------------------------- the annoying ones
def trait_of(t: dict) -> str | None:
    x = t.get('_tw')
    return x.get('trait') if isinstance(x, dict) else None


def _by(v, trait):
    """A value written per trait ({trait: v}) or once for all."""
    if isinstance(v, dict) and (trait in v or v and all(k in TW_TRAITS for k in v)):
        return v.get(trait)
    return v


TW_TRAITS = {k for x in TW.values() for k in x['traits']}


def _fill(text: str, t: dict) -> str:
    n = t['needs']
    b = n.get('book') or {}
    o = odds_text(t['day'])
    return (text or '').replace('{note}', n.get('note') or '').replace('{code}', b.get('code', '')).replace('{phone}', b.get('phone', '')) \
        .replace('{slots}', str(o['slots'])).replace('{entries}', f'{o["entries"]:,}'.replace(',', '.')).replace('{pct}', o['pct'])


def _probe_text(script: dict, probe: dict, trait: str, t: dict) -> str:
    text = probe['text']
    if isinstance(text, dict):
        text = text.get(trait, probe.get('default', ''))
    return _fill(text, t)


def _need_tw(t: dict) -> tuple[dict, dict]:
    kit.need(t['known'], 'Hỏi khách cần gì đã nhé.')
    tw = t.get('tw')
    kit.need(isinstance(tw, dict) and t['needs'].get('tw') in TW, 'Khách này không có chuyện gì cần quyết.')
    kit.need(not tw['done'], 'Chuyện này đã xong rồi.')
    kit.need(t['stage'] == 'prep', 'Khách này đã tính tiền rồi.')
    return tw, TW[t['needs']['tw']]


def _probe(s, c, d, p):
    t = _task(c, p, ('sale', 'case'))
    tw, x = _need_tw(t)
    pid = kit.one_of(p.get('probe'), [y['id'] for y in x['probes']], 'Không có câu hỏi này.')
    kit.need(pid not in tw['asked'], 'Hỏi câu này rồi.')
    probe = next(y for y in x['probes'] if y['id'] == pid)
    tw['asked'].append(pid)
    kit.start_work(t)
    text = _probe_text(x, probe, trait_of(t), t)
    if x.get('probe_only') and probe.get('reveal'):
        tw.update(done=True, q='good', out=text)
    return dict(message=f'{x["emoji"]} {text}')


def _answer(s, c, d, p):
    t = _task(c, p, ('sale', 'case'))
    tw, x = _need_tw(t)
    kit.need(not x.get('probe_only'), 'Chuyện này không cần trả lời, hỏi là biết.')
    aid = kit.one_of(p.get('answer'), [y['id'] for y in x['answers']], 'Không có cách trả lời này.')
    a = next(y for y in x['answers'] if y['id'] == aid)
    trait = trait_of(t)
    q = _by(a['q'], trait) or 'bad'
    kit.start_work(t)
    if a.get('retry') and q != 'good':
        # a wrong fix: nothing happens, the customer waits a little longer, try again
        tw['tries'] = min(9, tw['tries'] + 1)
        t['patience'] = max(20, t['patience'] - 10)
        return dict(message=f'{x["emoji"]} Thử “{a["label"]}”: vẫn không được. Khách sốt ruột rồi, coi kỹ lại nhé.', correct=False)
    if q == 'good' and a['need'] and not set(a['need']) & set(tw['asked']):
        q = 'ok'            # right, but without checking: a lucky guess
    if q == 'good' and tw['tries']:
        q = 'ok'            # right in the end, after wrong tries
    push = (x.get('push') or {}).get(trait)
    if push and tw['round'] == 0 and aid in push['after']:
        tw['round'] = 1
        return dict(message=f'{x["emoji"]} {_fill(push["say"], t)}')
    out = _fill(_by(a['out'], trait) or '', t)
    eff = _by(a['eff'], trait) or {}
    happy = _by(a.get('happy', False), trait)
    tw.update(ans=aid, q=q, out=out[:300], done=True)
    notes = _effects(s, c, d, t, x, eff)
    if q != 'good' and not happy:
        rv = eff.get('review')
        mine = rv and len(rv) < 3
        sev = (3 if rv[0] <= 1 else 2) if mine else (2 if q == 'bad' else 1)
        t['mistakes'] += 1
        cq.slip(t, 'tw_' + q, sev, (rv[1] if mine else out)[:200], 'xử lý chưa khéo' if q == 'ok' else 'xử lý sai')
    msg = f'{x["emoji"]} {out}' + (' ' + ' '.join(notes) if notes else '')
    if t['kind'] == 'case' or eff.get('sale') == 'end':
        t['cart'] = {}
        if t['kind'] == 'case':
            d['today']['cases'] += 1
            d['stats']['cases'] += 1
        msg = _finish(s, c, d, t, 0, msg)
    elif eff.get('disc'):
        t['disc'] = kit.integer(eff['disc'], 0, 90)
    return dict(message=msg, correct=True if q == 'good' else False if q == 'bad' else None)


def _effects(s: dict, c: dict, d: dict, t: dict, x: dict, eff: dict) -> list[str]:
    notes = []
    rv = eff.get('review')
    if rv and len(rv) > 2:      # someone else (a fan who missed out, the distributor's man) writes it
        kit.review(s, c, kit.npc_id(ID, rv[2]), rv[0], rv[1], t['id'])
    for sku, n in (eff.get('waste') or {}).items():
        k = min(int(n), kit.stock(c, sku))
        if k:
            lost = kit.take(c, sku, k)
            kit.waste(c, sku, k, lost, x['title'])
            notes.append(f'(−{k} {SKU[sku]["short"]})')
    if eff.get('refund'):
        amount = min(_price(c, eff['refund']), c['money'])
        if amount:
            kit.money(s, c, -amount, f'Hoàn tiền: {t["title"]}'[:120], t['id'], 'refund')
            notes.append(f'(−{amount} xu hoàn tiền)')
    if eff.get('money'):
        amount = min(int(eff['money']), c['money'])
        if amount:
            kit.money(s, c, -amount, f'{x["title"]}'[:120], t['id'], 'event_cost')
            notes.append(f'(−{amount} xu)')
    if eff.get('zban'):
        d['zban'] = max(d['zban'], c['day'] + int(eff['zban']))
        notes.append(f'⛔ {CHART} khóa quét tới hết ngày {d["zban"]}.')
    if eff.get('nolimit'):
        t['tw']['nolimit'] = True
    return notes


# ---------------------------------------------------------------- finishing
def _graduate(d: dict) -> str:
    if d['learn']['done'] or d['stats']['customers'] < APPRENTICE:
        return ''
    d['learn'].update(done=True, task=None, codes=[])
    return ' 🎓 Học nghề xong! Chị Thơ: “Giờ em tự đứng quầy được rồi. Chị ra sau xếp hàng mới về.”'


def _finish(s: dict, c: dict, d: dict, t: dict, reward: int, narrative: str) -> str:
    i = _npc_index(t)
    story = ''
    if i in REG_STORY and t['kind'] == 'sale' and reward > 0:
        r = d['regulars'].setdefault(str(i), dict(visits=0))
        r['visits'] = min(999, r['visits'] + 1)
        lines = REG_STORY[i]
        story = lines[min(r['visits'], len(lines)) - 1]
        t['story'] = story
    t['stage'] = 'done'
    kit.complete(s, c, t, max(0, int(reward)), (narrative or t['title'])[:300])
    return f'{narrative} 💬 {story}'.strip() if story else narrative


ACTIONS = {
    'zp_count': _count, 'zp_sign': _sign, 'zp_demo': _demo, 'zp_battery': _battery, 'zp_close': _close, 'zp_open': _open,
    'zp_add': _add, 'zp_drop': _drop, 'zp_opt': _opt, 'zp_ring': _ring, 'zp_decline': _decline, 'zp_pay': _pay, 'zp_short': _short,
    'zp_probe': _probe, 'zp_ans': _answer,
}


# ================================================================ day start and close
def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    day = c['day']
    d['shop'] = _fresh_shop(day)
    d['today'] = _fresh_today(day)
    if mod_of(day)['id'] == 'comeback':
        d['pob'] = max(d['pob'], POB_COMEBACK)
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'setup' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    mine = [t for t in c['tasks'] if t.get('career') == ID and t['day'] == day]
    setup = next((t for t in mine if t.get('kind') == 'setup' and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    if setup is None and not mine:
        setup = make_task(day, 0, c['turn'])
        c['tasks'].append(setup)
        on_task(s, c, setup)
        mine.append(setup)
    # comeback day: the queue outside brings one more customer
    if mod_of(day)['id'] == 'comeback' and len(mine) < 4:
        slot = max(int(t['id'].split('-')[-1]) for t in mine) + 1 if mine else 1
        extra = make_task(day, slot, c['turn'])
        c['tasks'].append(extra)
        on_task(s, c, extra)
    if setup:
        c['active_task'] = setup['id']
        setup['deferred'] = False
    elif c['active_task'] and not any(t['id'] == c['active_task'] and t['status'] not in ('completed', 'referred', 'cancelled') for t in c['tasks']):
        kit.eng().next_active(c)
    kit.desk_start(s, c, ID, d['desk'], DESK, mod_of(day)['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    desk_note = kit.desk_close(s, c, ID, d['desk'], DESK)
    today = d['today']
    lines = [f'💿 Bán {today["units"]} món cho {today["customers"]} lượt khách.']
    if today['entries']:
        lines.append(f'🎟️ Ghi {today["entries"]} phiếu fansign.')
    if today['cases']:
        lines.append(f'🔁 Giải quyết {today["cases"]} chuyện khách quay lại.')
    if desk_note:
        lines.append(desk_note)
    d['shop'].update(open=False)
    stock = {x['id']: kit.stock(c, x['id']) for x in SKUS}
    low = [x['id'] for x in SKUS if stock[x['id']] <= (1 if x['group'] == 'stick' or x.get('member') else 2)]
    tm = mod_of(c['day'] + 1)
    return dict(tomorrow=dict(emoji=tm['emoji'], label=tm['label'], hint=tm['hint']), lines=lines,
                note=f'Kho: Pink {stock["ps_pink"]}, Blank {stock["ps_blank"]}, Jewel {stock["ps_jewel"]}, Búa {stock["bua1"] + stock["bua2"]} · POB {d["pob"]} bộ.',
                customers=today['customers'], units=today['units'], entries=today['entries'], cases=today['cases'], low=low[:12])


# ================================================================ reviews
def feedback(c: dict, t: dict) -> dict:
    p = t.get('patience', 100)
    speed = 5 if p >= 85 else 4 if p >= 65 else 3 if p >= 45 else 2
    codes = {x['code'] for x in cq.slips(t)}
    if t['kind'] == 'setup':
        ready = 5 - len(codes & {'no_count', 'no_demo', 'demo_dead'})
        rule = 2 if codes & {'sign', 'no_close', 'close_short'} else 5
        return dict(criteria=[dict(key='ready', label='Tiệm sẵn sàng', score=max(2, ready), note='đếm kho, thử búa' if ready == 5 else 'còn sót khâu chuẩn bị'),
                              dict(key='rule', label='Biển & sổ đặt trước', score=rule, note='đúng luật nhà phân phối' if rule == 5 else 'biển hoặc sổ chưa đúng')])
    tw = t.get('tw') or {}
    fair = {'good': 5, 'ok': 3, 'bad': 1}.get(tw.get('q'), 5)
    if 'limit' in codes:
        fair = min(fair, 2)
    if t['kind'] == 'case':
        return dict(criteria=[dict(key='handle', label='Xử lý đúng', score=fair, note=tw.get('out', '')[:80] or 'đã xử lý'),
                              dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')])
    if t.get('cart') == {} and t.get('sold') is None:
        return dict(criteria=[dict(key='fair', label='Công bằng, nói thật', score=fair, note='nói thật với khách' if fair >= 3 else 'xử lý chưa đúng'),
                              dict(key='order', label='Có hàng đúng ý', score=3, note='lần này chưa có')])
    wrong = codes & {'bias', 'cd', 'battery', 'cheap', 'bt', 'version', 'missing'}
    order = max(1, 5 - 2 * len(wrong) - (1 if 'extra' in codes else 0))
    care = max(1, 5 - len(codes & {'zchart', 'poster', 'raffle', 'pob'}))
    return dict(criteria=[dict(key='order', label='Đúng album, đúng phiên bản', score=order, note='đúng lời dặn' if order == 5 else 'sai hoặc thiếu món'),
                          dict(key='care', label='Zchart, poster, fansign, POB', score=care, note='đủ như dặn' if care == 5 else 'quên lời dặn'),
                          dict(key='fair', label='Công bằng, nói thật', score=fair, note='đúng luật, nói thật' if fair == 5 else 'chưa công bằng'),
                          dict(key='speed', label='Nhanh gọn', score=speed, note=f'chờ còn {p}% kiên nhẫn')])


# ================================================================ what the client sees
def _line_text(line: dict) -> str:
    return f'{line["qty"]}× {line["label"]}' if line['qty'] > 1 and not line['label'][:1].isdigit() else line['label']


def known_request(c: dict, t: dict) -> str:
    n = t['needs']
    if t['kind'] == 'setup':
        return (f'Chị Thơ dặn: đếm bản giới hạn, dựng biển “tối đa {n["limit"]} bản/người”, thử búa trưng bày (yếu thì thay pin AAA)'
                + (', chốt đúng số Jewel trong sổ đặt trước' if n.get('chot') else '') + ', rồi mở tiệm. ' + n['note'])
    if t['kind'] == 'case':
        return f'{_who(t)}: “{n["say"]}”'
    if n.get('tw') == 'parent' and not (t.get('tw') or {}).get('done'):
        return f'{_who(t)}: “{n["say"]}” Hỏi giấy nhắn của bé mới biết bé cần gì.'
    want = '; '.join(_line_text(x) for x in n['lines'])
    extra = [w for k, w in (('zchart', 'quét Zchart'), ('tube', 'poster cuộn'), ('raffle', 'phiếu fansign'), ('pob', 'POB')) if n.get(k)]
    return f'{_who(t)} muốn: {want}' + (f' · {", ".join(extra)}' if extra else '') + f'. {n.get("note") or ""}'.rstrip()


def _tw_view(t: dict) -> dict | None:
    tw = t.get('tw')
    sid = t['needs'].get('tw') if isinstance(t.get('needs'), dict) else None
    if not isinstance(tw, dict) or sid not in TW:
        return None
    x, trait = TW[sid], trait_of(t)
    probes = [dict(id=y['id'], label=y['label'], asked=y['id'] in tw['asked'],
                   text=_probe_text(x, y, trait, t) if y['id'] in tw['asked'] else None) for y in x['probes']]
    answers = [dict(id=a['id'], label=_fill(a['label'], t)) for a in x['answers']]
    push = (x.get('push') or {}).get(trait) if tw['round'] else None
    return dict(id=sid, emoji=x['emoji'], title=x['title'], probes=probes, answers=answers, probe_only=bool(x.get('probe_only')),
                push=_fill(push['say'], t) if push else None, done=tw['done'], q=tw['q'] if tw['done'] else None, out=tw['out'],
                ans=tw['ans'], tries=tw['tries'])


def public_task(t: dict) -> dict:
    v = tree_copy(t)
    for k in list(v):
        if k.startswith('_'):
            del v[k]
    if not v['known']:
        v['needs'] = None
        v['tw'] = None
    else:
        v['tw'] = _tw_view(t)
        if t['kind'] == 'sale':
            n = v['needs']
            if n.get('tw') == 'parent' and not t['tw']['done']:
                n['lines'], n['hidden'] = [], True
                n['note'] = ''
            g = n.get('guess')
            n['guess'] = SKU[g]['name'] if g in SKU else None
            v['can'] = dict(zp_ring=kit.check(_ring_rules_view, t))
    v['cash'] = till.public(t.get('cash'))
    return v


def _ring_rules_view(t: dict, need=kit.need) -> None:
    """The ring rules a task alone can answer (the shelf is checked from public_data's stock)."""
    tw = t.get('tw')
    need(not tw or tw['done'], 'Còn chuyện với khách chưa xong: hỏi, rồi chọn cách trả lời nhé.', fix=dict(sel='.zp-tw', label='👉 Trả lời khách'))
    need(sum(t['cart'].values()) > 0, 'Giỏ còn trống: lấy hàng khách cần trước đã.')


def public_data(c: dict) -> dict:
    raw = c['ext']['data']
    d = tree_copy(raw)
    base = initial()
    for k, v in base.items():
        d.setdefault(k, tree_copy(v))
    mod = mod_of(c['day'])
    has_inv = bool(c['ext'].get('inv'))
    stock = {x['id']: kit.stock(c, x['id']) for x in SKUS} if has_inv else {}
    on = not d['learn']['done'] and d['stats']['customers'] < APPRENTICE
    n = min(d['stats']['customers'], APPRENTICE - 1)
    can = dict(open=kit.check(_open_rules, d, _setup_id(c)))
    if has_inv:
        can['opt'] = {k: kit.check(_opt_rules, c, d, k) for k in OPTS}
    return dict(intro=d['intro'], shop=d['shop'], stock=stock, pob=d['pob'], zban=d['zban'], raffle=d['raffle'],
                odds=odds_text(c['day']), mod=dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint'], limit=mod['limit']),
                demo_weak=demo_weak(c['day']), book=book_of(c['day']) if mod['id'] == 'chot' else [],
                book_total=book_total(c['day']) if mod['id'] == 'chot' else 0,
                today=d['today'], stats=d['stats'], regulars={k: dict(v) for k, v in d['regulars'].items()},
                desk=kit.desk_public(d['desk'], DESK, ID), can=can,
                learn=dict(on=on, n=d['stats']['customers'], of=APPRENTICE, title=LESSONS[n][0] if on else None, text=LESSONS[n][1] if on else None))


def content() -> dict:
    skus = [dict(x, fam=fam(x['id'])) for x in SKUS]
    return dict(skus=skus, groups=GROUPS, members={k: [list(m) for m in v] for k, v in MEMBERS.items()}, albums=ALBUMS, prices=PRICES,
                sell=list(SELL), intro=INTRO, apprentice=APPRENTICE, limits=list(LIMIT_OPTIONS), slots=FANSIGN_SLOTS, store=STORE,
                stores=list(OTHER_STORES), chart=CHART, distributor=DISTRIBUTOR,
                people=[dict(name=p[0], role=p[1], note=p[2]) for p in PEOPLE], denoms=list(till.DENOMS))


def hint(c: dict, t: dict) -> str:
    if t.get('kind') == 'setup':
        return 'Đếm bản giới hạn → dựng biển đúng số → thử búa trưng bày (yếu thì thay pin) → hạn chốt thì chốt sổ → Mở tiệm.'
    if t.get('kind') == 'case':
        return 'Hỏi cho rõ (xem album, tem, seri, mã…) → chọn cách trả lời đúng chính sách và nói thật.'
    return ('Hỏi khách → lấy đúng phiên bản (Digipack chắc card một người, Kit không có CD, ver.2 có Bluetooth ăn pin AA) → '
            'bật Zchart, ống poster, phiếu fansign, POB nếu khách dặn → giữ giới hạn → tính tiền → thối đúng.')


def assist(s: dict, c: dict, e: dict, t: dict | None) -> str | None:
    d = _data(c)
    if e.get('role') == 'shelf':
        d['shop']['counted'] = True
        return 'Đã đếm bản giới hạn, xếp lại kệ album.'
    if e.get('role') == 'queue':
        return 'Đã phát số thứ tự cho hàng chờ ngoài cửa.'
    return None


# ================================================================ saves
def _vbool(x) -> None:
    kit.need(type(x) is bool, 'Dữ liệu tiệm album sai.')


def _vcart(cart) -> None:
    kit.need(isinstance(cart, dict) and len(cart) <= len(SELL) and set(cart) <= set(SELL), 'Giỏ hàng sai.')
    for q in cart.values():
        kit.integer(q, 1, MAX_LINE)
    kit.need(sum(cart.values()) <= MAX_CART, 'Giỏ hàng sai.')


def validate_task(t: dict, original: dict) -> None:
    kit.need(t.get('gen') == GEN, 'Phiên bản việc tiệm album không hợp lệ.')
    kit.need(t.get('kind') in KINDS and t.get('stage') in STAGES, 'Trạng thái việc tiệm album sai.')
    _vcart(t.get('cart'))
    opt = t.get('opt')
    kit.need(isinstance(opt, dict) and set(opt) == set(OPTS), 'Lựa chọn ở quầy sai.')
    for v in opt.values():
        _vbool(v)
    tw = t.get('tw')
    sid = (t.get('needs') or {}).get('tw') if isinstance(t.get('needs'), dict) else None
    if tw is None:
        kit.need(sid is None, 'Chuyện với khách sai.')
    else:
        kit.need(sid in TW and isinstance(tw, dict) and set(tw) == {'asked', 'ans', 'round', 'tries', 'q', 'out', 'done', 'nolimit'},
                 'Chuyện với khách sai.')
        x = TW[sid]
        kit.need(isinstance(tw['asked'], list) and len(tw['asked']) <= len(x['probes']) and len(set(tw['asked'])) == len(tw['asked'])
                 and set(tw['asked']) <= {y['id'] for y in x['probes']}, 'Câu đã hỏi sai.')
        kit.need(tw['ans'] is None or tw['ans'] in {y['id'] for y in x['answers']}, 'Câu trả lời sai.')
        kit.integer(tw['round'], 0, 1)
        kit.integer(tw['tries'], 0, 9)
        kit.need(tw['q'] is None or tw['q'] in QUALITY, 'Kết quả chuyện với khách sai.')
        kit.need(tw['out'] is None or (isinstance(tw['out'], str) and len(tw['out']) <= 300), 'Kết quả chuyện với khách sai.')
        _vbool(tw['done'])
        _vbool(tw['nolimit'])
    if t.get('price') is not None:
        kit.integer(t['price'], 0, 10 ** 6)
    kit.integer(t.get('cost'), 0, 10 ** 6)
    kit.integer(t.get('disc'), 0, 90)
    kit.integer(t.get('entries'), 0, 99)
    if t.get('sold') is not None:
        _vcart(t['sold'])
    till.validate(t.get('cash'), t)
    kit.need(t.get('story') is None or (isinstance(t['story'], str) and len(t['story']) <= 300), 'Chuyện khách quen sai.')


def validate_data(c: dict) -> None:
    d = _data(c)
    _vbool(d['intro'])
    till.validate_book(c)
    b = d['shop']
    kit.need(isinstance(b, dict) and set(b) == set(_fresh_shop(0)), 'Quầy tiệm album sai.')
    kit.integer(b['day'], 0, 10 ** 7)
    for k in ('open', 'counted', 'demo', 'battery', 'closed'):
        _vbool(b[k])
    kit.need(b['sign'] is None or (type(b['sign']) is int and b['sign'] in LIMIT_OPTIONS), 'Biển giới hạn sai.')
    kit.integer(d['pob'], 0, 999)
    kit.integer(d['zban'], 0, 10 ** 7)
    kit.integer(d['raffle'], 0, 10 ** 7)
    lr = d['learn']
    kit.need(isinstance(lr, dict) and set(lr) == {'task', 'codes', 'done'}, 'Học nghề sai.')
    kit.need(lr['task'] is None or (isinstance(lr['task'], str) and len(lr['task']) <= 80), 'Học nghề sai.')
    kit.need(isinstance(lr['codes'], list) and len(lr['codes']) <= len(CATCH) and set(lr['codes']) <= set(CATCH), 'Học nghề sai.')
    _vbool(lr['done'])
    kit.need(isinstance(d['regulars'], dict) and set(d['regulars']) <= {str(i) for i in REG_STORY}, 'Sổ khách quen sai.')
    for v in d['regulars'].values():
        kit.need(isinstance(v, dict) and set(v) == {'visits'}, 'Sổ khách quen sai.')
        kit.integer(v['visits'], 0, 999)
    for k in ('today', 'stats'):
        kit.need(isinstance(d[k], dict) and len(d[k]) <= 20, 'Số liệu tiệm album sai.')
        for v in d[k].values():
            kit.integer(v, 0, 10 ** 9)
    kit.desk_validate(d['desk'], DESK)


# ================================================================ the plugin spec
SPEC = dict(
    id=ID, prefix='zp_', category='shop',
    meta=dict(short='Bán album ZPOP', place='Tiệm album Mây Pop', tagline='Đúng phiên bản, đúng card bias, đúng giới hạn!', icon='music',
              color='#d6458f', light='#ffe3f1', weather='Chiều Phố chợ, loa phát nhạc comeback', work='Khách mua album', station='Kệ album & quầy',
              greeting='Đếm bản giới hạn, dựng biển, thử búa trưng bày rồi mở tiệm. Nghe kỹ khách cần phiên bản nào, card ai, Zchart hay poster cuộn nhé.',
              caption='Bản nào cũng đúng ý fan', map_label='35 · TIỆM ALBUM MÂY POP'),
    people=PEOPLE,
    staff=[('Bơ', 'shelf', 'Em họ chị Thơ, đếm kho nhanh như máy.', 80, 88),
           ('Kun', 'queue', 'Sinh viên làm thêm, giữ hàng chờ ngày comeback êm ru.', 82, 78),
           ('Trâm', 'shelf', 'Thuộc mã từng phiên bản, xếp kệ thẳng tắp.', 70, 94),
           ('Hưng', 'queue', 'Nhớ tên fan quen, ai vào cũng chào bằng tên bias.', 78, 82)],
    roles={'shelf': 'Đếm kho, xếp kệ album', 'queue': 'Giữ hàng chờ, phát số thứ tự'},
    inventory=dict(items=ITEMS, capacity=80),
    prices=PRICES,
    tip=2,
    physical=PHYSICAL,
    free_actions=FREE,
    no_tick=NO_TICK,
    waste_items=(),
    activity=('💿', 'Kệ album gọn gàng', [('Digipack Mận-Ji', 'Kệ PINK STATIC'), ('Gió Mùa Đêm ver', 'Kệ 7GIÓ'), ('Vỉ pin AA', 'Hộc phụ kiện'),
                                         ('Búa hồng ver.2', 'Tủ kính lightstick')],
              ['Đếm bản giới hạn', 'Dựng biển giới hạn', 'Lấy đúng phiên bản khách cần', 'Quét Zchart, tính tiền']),
    stories=[('Tờ lịch comeback', ('Chị Thơ dán tờ lịch comeback của cả năm sau quầy.',
                                   'Ngày nào có nhóm comeback, chị khoanh đỏ, dặn: “Hôm đó mở sớm.”',
                                   'Bạn học thuộc từng ngày, như học lịch thi.')),
             ('Tấm card đầu tiên', ('Chị Thơ giữ một tấm card cũ bọc ba lớp toploader.',
                                    'Tấm card chị đổi được năm mười lăm tuổi, đổi bằng cả tháng tiền ăn sáng.',
                                    'Chị bảo: “Card nào cũng là tuổi trẻ của ai đó, cầm cho nhẹ tay.”')),
             ('Hàng chờ lúc sáu giờ', ('Sáng comeback, hàng đã dài tới đầu hẻm.',
                                       'Bạn phát số, nhắc giới hạn, mời nước những bạn đứng từ sớm.',
                                       'Na số 1, cười tít: “Năm nay em đứng đầu rồi!”'))],
    review_asides=['Lấy đúng Digipack bias, không phải nhắc.', 'Poster cuộn ống đàng hoàng, không một nếp gấp.',
                   'Giới hạn rõ ràng, ai xếp hàng cũng có phần.', 'Nói thật tỉ lệ fansign, mua mà yên tâm.'],
    situations=SITUATIONS,
    guide='Đếm bản giới hạn → dựng biển → thử búa → mở tiệm. Mỗi khách: hỏi → lấy đúng phiên bản → Zchart, poster cuộn, '
          'phiếu fansign, POB nếu khách dặn → giữ giới hạn → tính tiền → thối đúng.',
)
