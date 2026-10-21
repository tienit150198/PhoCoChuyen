"""💍 Tiệm vàng Ngọc Mây: a gold, silver and diamond shop the player runs (player #472 "làm chủ bán vàng, bán kim cương";
owner 21/10 "nghề mới thì làm đi").

Every morning the gold company sends the middle price of 9999 gold; the shop's board (`board(day)`, pure) sells 1,2 %
above it and buys 1,2 % below, and the other purities follow their gold content. The board moves a little every day
(two slow waves and a small daily jitter, at most about ±3,4 % around REF), never with the real market, never with 🏪 Tiệm
vàng Kim Phát (game/vang.py, the players' own gold savings): this board only prices the shop's counter.

A day starts with the morning slip (slot 0, kind 'open': count the safe against the ledger, check the scale with the
standard weight, post the board); no customer is served before it is done. Then each customer is a slip of server-graded
steps (game/careers/stepkit.py) of one of three kinds:
  ban   sell a piece off the shelf: pick the piece the customer asked for (the piece leaves the stock now, FIFO, its
        cost kept as `cogs`), settle the awkward demands, weigh it in phân, work out the gold value from today's board,
        write the invoice (and sometimes the hand-over). Bill = gold + the stone + the shop's tiền công (SPEC prices,
        tunable 75–125 % before the shift, frozen on the slip by on_task) × quality.
  mua   buy old gold back: papers (a stranger with three rings and no ID is refused), the XRF reading (a plated fake is
        refused), the weight without the stone, the payout at today's buy price less the deduction (none for the shop's
        own piece with its invoice, 3 % otherwise), the purchase ledger. The old gold goes straight to the company at its
        middle price the same day: the shop's margin is the spread plus the deduction, × quality. No gold is kept, so
        there is nothing to speculate on, and no player ever buys or sells gold with another player here.
  kc    appraise a diamond by its 4C (carat on the scale, colour against the master stones, clarity under the loupe,
        cut by its proportions) and check the certificate against the laser inscription (from day 25, a moissanite
        that fools the thermal pen). Pay: the appraisal fee (SPEC prices) × quality.
Out of stock (`vg_out`): a sale whose piece is not on the shelf is referred before it starts (no pay).

Money: stock is bought from the company like every shop's (game/inventory.py, one supplier, no wholesale tiers, no
haggling); the opening shelf is free, like every shop's. Pay per job is the shop's margin (bonus_base), about 13–60 xu.
"""
from __future__ import annotations

from copy import deepcopy
import math

from . import kit
from . import jewelry_content as C
from . import stepkit as sk

ID = 'jewelry'
CERT_ID = 'jewelry_basics'   # certificate_content.GROUPS (hire=False): its perk is 2 xu more on each diamond appraisal
PREFIX = 'vg_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('vg_step', 'vg_out')
FREE = ('vg_intro',)
NO_TICK = ('vg_intro', 'vg_desk')
LINES = 24
KINDS = ('open', 'ban', 'mua', 'kc')
PRICE = {'9999': 10000, '18k': 7500, '14k': 5850, '10k': 4160}   # board price per 10 000 of 9999's (gold content)
WORKSHOP = {'cong_vang': 3, 'cong_tay': 8, 'cong_cuoi': 20, 'cong_bac': 6, 'cong_kc': 20}   # the workshop's labour in a piece's cost
PRICES = {k: v['base'] for k, v in C.CONG.items()}


def _gold(tuoi: str, phan: int, mid: int) -> int:
    """Xu of `phan` phân of this purity at a 9999 middle price of `mid` a chỉ (silver: its own middle price)."""
    if tuoi == 'bac':
        return phan * C.SILVER[1] // 10
    return phan * mid * PRICE[tuoi] // 100000


def _cost(k: str) -> int:
    """What a piece costs the shop from the company: its metal at REF less 1 %, the workshop's labour, the stone."""
    x = C.PIECES[k]
    return _gold(x['tuoi'], x['phan'], C.REF) * 99 // 100 + WORKSHOP[x['cong']] + x.get('stone', 0)


ITEMS = [dict(id=k, name=x['name'], emoji=x['emoji'], group='bac' if x['tuoi'] == 'bac' else 'kim_cuong' if x.get('stone') else 'vang',
              unit=x['unit'], cost=_cost(k), price=_cost(k) + C.CONG[x['cong']]['base'], start=x['start'],
              **({'unlock': x['unlock']} if x.get('unlock') else {}))
         for k, x in C.PIECES.items()]
ITEM = {x['id']: x for x in ITEMS}


# ---------------------------------------------------------------- the board (pure: day)
def board(day: int) -> dict:
    """Today's board: the company's middle price of 9999 a chỉ and, per purity, mua vào / bán ra (xu a chỉ)."""
    r = kit.rng(ID, 'board', day)
    wave = 0.018 * math.sin(2 * math.pi * day / 23) + 0.010 * math.sin(2 * math.pi * day / 7 + 1) + 0.006 * (2 * r.random() - 1)
    mid = int(C.REF * (1 + wave) + 0.5)
    rows = {}
    for k in C.GOLD:
        m = mid * PRICE[k] // 10000
        rows[k] = dict(mid=m, buy=(m * (10000 - C.SPREAD_BP) + 5000) // 10000, sell=(m * (10000 + C.SPREAD_BP) + 5000) // 10000)
    rows['bac'] = dict(buy=C.SILVER[0], mid=C.SILVER[1], sell=C.SILVER[2])
    return dict(day=day, mid=mid, rows=rows)


def _row(day: int, tuoi: str) -> dict:
    return board(day)['rows'][tuoi]


# ---------------------------------------------------------------- building a slip (pure: day, slot)
def _g(phan: int) -> str:
    """5 phân → '1,875 g'."""
    return f'{phan * 375 / 1000:.3f}'.replace('.', ',') + ' g'


def _demands(r, day: int, kind: str, level: int) -> list:
    pool = [x for x in C.DEMANDS if x[0] <= day and (x[4] is None or kind in x[4])]
    want = 2 if level >= 2 and r.random() < 0.5 else 1
    return [sk.scenario(r, 'khach', f'd{i + 1}', 'Khách dặn điều oái oăm', d[1:4]) for i, d in enumerate(r.sample(pool, min(want, len(pool))))]


def _open(day: int) -> tuple:
    r = kit.rng(ID, day, 0)
    counts = [r.randint(1, 3), r.randint(0, 4), r.randint(1, 6), r.randint(0, 8)]
    total = sum(n * v for n, (_, _, v) in zip(counts, C.BILLS))   # a xấp is ten notes of 100
    say = ', '.join(f'{n} {C.BILLS[i][1]}' for i, n in enumerate(counts) if n)
    pairs = [(sk.step('ket', 'dem', 'number', 'Đếm két đầu ca', f'Mở két: {say}. Cộng két được bao nhiêu xu?', unit='xu'), total)]
    match = r.random() < 0.7
    ledger = total if match else total - r.choice((20, 50, 100))
    right, other = (C.SAFE_OK[0], C.SAFE_OK[1]) if match else (C.SAFE_OK[1], C.SAFE_OK[0])
    pairs.append(sk.scenario(r, 'ket', 'so', 'Đối chiếu sổ giao ca', (f'Sổ giao ca tối qua ghi trong két còn {ledger} xu.', right, (other,) + C.SAFE_WRONG)))
    pairs.append(sk.scenario(r, 'can', 'chuan', 'Kiểm cân bằng quả cân chuẩn', C.SCALE_FIX if r.random() < 0.4 else C.SCALE_OK))
    b = board(day)
    row = b['rows']['9999']
    if r.random() < 0.5:
        pairs.append((sk.step('bang', 'ban', 'number', 'Treo giá bán ra',
                              f'Công ty vàng báo giá giữa vàng 9999 hôm nay: {b["mid"]} xu một chỉ. Tiệm bán ra cao hơn 1,2%, làm tròn tới xu. '
                              'Ghi giá bán ra 9999 một chỉ lên bảng?', unit='xu'), row['sell']))
    else:
        pairs.append((sk.step('bang', 'mua', 'number', 'Treo giá mua vào',
                              f'Công ty vàng báo giá giữa vàng 9999 hôm nay: {b["mid"]} xu một chỉ. Tiệm mua vào thấp hơn 1,2%, làm tròn tới xu. '
                              'Ghi giá mua vào 9999 một chỉ lên bảng?', unit='xu'), row['buy']))
    steps, key = sk.pairs_to_steps(pairs)
    needs = dict(steps=steps, demands=0, mid=b['mid'])
    return needs, key, C.MENTOR, 'Mở két, treo bảng giá', 'Cô Ba Ngọc dặn: “Đếm két, kiểm cân, treo bảng giá rồi mới mở cửa đón khách nghe con.”'


def _pieces(day: int) -> list:
    return [k for k, x in C.PIECES.items() if day >= {2: 4, 3: 6}.get(x.get('unlock', 1), 1)]


def _ban(day: int, slot: int, r, level: int) -> tuple:
    k = r.choice(_pieces(day))
    x = C.PIECES[k]
    npc, words = r.choice(C.WANT[k])
    who = C.PEOPLE[npc][0]
    others = r.sample([o for o in C.PIECES if o != k], 3)
    opts, ids = sk.lettered(r, [(o, C.PIECES[o]['name']) for o in [k] + others])
    pairs = [(sk.step('khay', 'chon', 'choice', 'Lấy đúng món trong tủ', f'{who}: “{words}”', opts), ids[k])]
    demands = _demands(r, day, 'ban', level)
    pairs += demands
    phan = x['phan'] if x['tuoi'] == 'bac' else x['phan'] + r.choice((0, 0, 0, 1))   # never lighter than the company billed it
    pairs.append((sk.step('can', 'phan', 'number', 'Cân trước mặt khách',
                          f'Đặt món lên cân, quay màn hình cho khách xem: {_g(phan)}. 1 phân = 0,375 g. Món nặng bao nhiêu phân?', unit='phân'), phan))
    label = C.TUOI[x['tuoi']][1]
    sell = _row(day, x['tuoi'])['sell']
    stone = ' Hột kim cương tính riêng theo giấy, không tính vào tiền vàng.' if x.get('stone') else ''
    pairs.append((sk.step('tien', 'vang', 'number', 'Tính tiền vàng',
                          f'Bảng hôm nay: {label} bán ra {sell} xu một chỉ. Tiền vàng = số phân × giá một chỉ ÷ 10, bỏ phần lẻ. '
                          f'Tiền vàng bao nhiêu xu?{stone}', unit='xu'), phan * sell // 10))
    pairs.append(sk.picks(r, 'hd', 'ghi', 'Xuất hóa đơn', 'Hóa đơn bán hàng phải ghi những dòng nào?', C.INVOICE_GOOD, r.sample(C.INVOICE_BAD, 2)))
    if r.random() < 0.5:
        pairs.append(sk.picks(r, 'giao', 'kiem', 'Giao món cho khách', 'Trước khi đưa món cho khách, làm những việc nào?', C.HAND_GOOD, C.HAND_BAD))
    steps, key = sk.pairs_to_steps(pairs)
    needs = dict(steps=steps, demands=len(demands), piece=k, piece_name=x['name'], emoji=x['emoji'], tuoi=label,
                 cong=x['cong'], stone=x.get('stone', 0), sell=sell)
    return needs, key, npc, f'{who} mua nữ trang', f'{who}: “{words}”'   # the title never names the piece: picking it is a step


def _mua(day: int, slot: int, r, level: int) -> tuple:
    roll = r.random() if level >= 1 else 1.0
    variant = 'fake' if roll < 0.12 else 'doubt' if roll < 0.22 else 'ok'
    if variant == 'doubt':
        row = r.choice(C.DOUBT)
        pairs = [sk.scenario(r, 'giay', 'cccd', 'Xem giấy tờ người bán', row)]
        pairs.append(sk.picks(r, 'bao', 'ghi', 'Ghi lại để báo công an', 'Từ chối mua rồi. Ghi lại những gì để báo công an khu vực?',
                              ('Đặc điểm từng món', 'Mô tả người bán và giờ tới', 'Số CCCD khách đưa (nếu có)'),
                              ('Giữ món của khách lại', 'Đăng ảnh khách lên mạng cho mọi người biết')))
        steps, key = sk.pairs_to_steps(pairs)
        needs = dict(steps=steps, demands=0, desc='Mấy món vàng đựng trong túi ni lông', own=False, stone=False)
        who = C.PEOPLE[C.STRANGER][0]
        return needs, key, C.STRANGER, f'{who} muốn bán vàng gấp', f'{who} đặt lên quầy một túi ni lông: “Bán gấp, tính lẹ giùm.”'
    npc = r.choice(C.CUSTOMERS)
    who = C.PEOPLE[npc][0]
    pairs = [sk.scenario(r, 'giay', 'cccd', 'Xem giấy tờ người bán', C.ID_OK)]
    if variant == 'fake':
        desc = r.choice(C.FAKE)
        opts, ids = sk.lettered(r, list(C.TUOI_OPTS.items()))
        pairs.append((sk.step('quet', 'tuoi', 'choice', 'Quét tuổi vàng', f'{desc}. Bắn máy quét lên món: {C.XRF["fake"]}. Kết luận?', opts), ids['fake']))
        pairs.append(sk.scenario(r, 'tra', 'lai', 'Nói kết quả với khách', C.FAKE_THEN))
        steps, key = sk.pairs_to_steps(pairs)
        needs = dict(steps=steps, demands=0, desc=desc, own=False, stone=False)
        return needs, key, npc, f'{who} bán lại vàng cũ', f'{who} đặt lên quầy: {desc[0].lower() + desc[1:]}.'
    desc, tuoi, (lo, hi), stone, own = r.choice(C.OLD)
    demands = _demands(r, day, 'mua', level)
    pairs += demands
    opts, ids = sk.lettered(r, [(t, C.TUOI_OPTS[t]) for t in [tuoi] + r.sample([t for t in C.TUOI_OPTS if t != tuoi], 3)])
    pairs.append((sk.step('quet', 'tuoi', 'choice', 'Quét tuổi vàng', f'Bắn máy quét lên món: {C.XRF[tuoi]}. Tuổi vàng?', opts), ids[tuoi]))
    phan = r.randint(lo, hi)
    if stone:
        st = r.randint(1, 3)
        text = f'Cân cả món: {_g(phan + st)}. Tháo mặt đá ra cân riêng: {_g(st)}. Còn bao nhiêu phân vàng?'
    else:
        text = f'Cân trước mặt khách: {_g(phan)}. 1 phân = 0,375 g. Món nặng bao nhiêu phân?'
    pairs.append((sk.step('can', 'phan', 'number', 'Cân vàng', text, unit='phân'), phan))
    row = _row(day, tuoi)
    ded = 0 if own else C.DEDUCT_OTHER
    note = 'Hàng tiệm mình, còn hóa đơn.' if own else 'Hàng tiệm khác hoặc không còn hóa đơn.'
    pairs.append((sk.step('tien', 'tra', 'number', 'Tính tiền trả khách',
                          f'Bảng hôm nay: {C.TUOI[tuoi][1]} mua vào {row["buy"]} xu một chỉ. {note} '
                          'Tiền trả = số phân × giá một chỉ ÷ 10, trừ hao theo sổ tay, bỏ phần lẻ. Trả khách bao nhiêu xu?', unit='xu'),
                  phan * row['buy'] * (100 - ded) // 1000))
    pairs.append(sk.picks(r, 'so', 'ghi', 'Ghi sổ mua hàng', 'Sổ mua hàng phải ghi những dòng nào?', C.LEDGER_GOOD, C.LEDGER_BAD))
    steps, key = sk.pairs_to_steps(pairs)
    needs = dict(steps=steps, demands=len(demands), desc=desc, own=own, stone=bool(stone), tuoi_key=tuoi)
    return needs, key, npc, f'{who} bán lại vàng cũ', f'{who} đặt lên quầy: {desc[0].lower() + desc[1:]}.'


def _kc(day: int, slot: int, r, level: int) -> tuple:
    npc = r.choice((2, 4, 5))
    who = C.PEOPLE[npc][0]
    pts = r.randrange(30, 151, 5)
    grams = f'{pts * 2 / 1000:.3f}'.replace('.', ',')
    pairs = [(sk.step('can', 'ct', 'number', 'Cân carat',
                      f'Đá rời trên cân carat: {grams} g. 1 ct = 0,2 g = 100 điểm. Ghi trọng lượng bao nhiêu điểm?', unit='điểm'), pts)]
    i = r.randrange(1, len(C.COLOR_GRADES))
    lighter, grade = C.COLOR_GRADES[i - 1], C.COLOR_GRADES[i]
    pool = [g for g in C.COLOR_GRADES if g not in (lighter, grade)]
    opts, ids = sk.lettered(r, [(g, f'Màu {g}') for g in [grade, lighter] + r.sample(pool, 2)])
    pairs.append((sk.step('mau', 'so', 'choice', 'So màu với đá mẫu',
                          f'Đặt đá cạnh bộ đá mẫu dưới đèn chuẩn: ngả vàng hơn mẫu {lighter} một chút, nhưng trắng hơn mẫu {grade}. Màu gì?', opts), ids[grade]))
    cl = r.choice(tuple(C.CLARITY))
    opts, ids = sk.lettered(r, list(C.CLARITY_NAMES.items()))
    pairs.append((sk.step('soi', 'sach', 'choice', 'Soi độ sạch', f'{C.CLARITY[cl]}. Độ sạch?', opts), ids[cl]))
    cut = r.choice(tuple(C.CUTS))
    (table, depth, light), _ = C.CUTS[cut]
    opts, ids = sk.lettered(r, [(k, v[1]) for k, v in C.CUTS.items()] + [('w', C.CUT_WRONG)])
    pairs.append((sk.step('cat', 'giac', 'choice', 'Chấm giác cắt', f'Máy đo: mặt bàn {table}%, độ sâu {depth}%, {light}. Giác cắt?', opts), ids[cut]))
    if day >= C.MILESTONES[3] and r.random() < 0.3:
        pairs.append(sk.scenario(r, 'giay', 'so', 'Thử đá thật hay giả', C.STONE_KIND))
    else:
        cert = r.randrange(10 ** 9, 10 ** 10)
        match = r.random() < 0.7
        laser = cert if match else cert + r.choice((1, 10, 100, 1000))
        right = 'Khớp: ghi kết quả vào phiếu, kèm số giấy' if match else 'Không khớp: ghi rõ vào phiếu, không định giá theo giấy'
        wrong = 'Không khớp: ghi rõ vào phiếu, không định giá theo giấy' if match else 'Khớp: ghi kết quả vào phiếu, kèm số giấy'
        pairs.append(sk.scenario(r, 'giay', 'so', 'Đối chiếu giấy kiểm định',
                                 (f'Giấy kiểm định khách đưa ghi số {cert}. Soi mép đá thấy số khắc laser {laser}.', right,
                                  (wrong, 'Giấy của hãng lớn, cứ ghi theo giấy cho nhanh'))))
    demands = _demands(r, day, 'kc', level)
    pairs += demands
    steps, key = sk.pairs_to_steps(pairs)
    needs = dict(steps=steps, demands=len(demands), carat_g=grams)
    return needs, key, npc, f'{who} nhờ kiểm định kim cương', f'{who} đưa viên đá trong túi giấy nhỏ: “Coi giùm hột này cỡ nào, có đúng như giấy không?”'


def slip(day: int, slot: int) -> tuple:
    """(kind, needs, key, npc, title, opening) of (day, slot). Pure."""
    if slot == 0:
        return ('open',) + _open(day)
    r = kit.rng(ID, day, slot)
    level = sum(day >= n for n in C.MILESTONES)
    roll = r.random()
    kind = 'kc' if day >= C.MILESTONES[0] and roll < 0.2 else 'mua' if roll < 0.5 else 'ban'
    return (kind,) + {'ban': _ban, 'mua': _mua, 'kc': _kc}[kind](day, slot, r, level)


def _fee_key(t: dict) -> str | None:
    return t['needs']['cong'] if t['kind'] == 'ban' else 'kiem_dinh' if t['kind'] == 'kc' else None


def make_task(day: int, slot: int, serial: int) -> dict:
    kind, needs, key, npc, title, opening = slip(day, slot)
    t = kit.base_task(ID, day, slot, serial, npc, title, opening, gen=GEN, kind=kind, needs=needs, _key=key, at=0, work={}, errors=[],
                      wrong=0, quality=100, paid=0, lines=[], stage='work', fee=0, cogs=0, held=False)
    fk = _fee_key(t)
    if fk:
        t['fee'] = PRICES[fk]
    if kind == 'open':
        t['known'] = True
    return t


def on_task(s: dict, c: dict, t: dict) -> None:
    """The shop's own price list is frozen on the slip when the customer walks in (a tuned price never moves a slip)."""
    fk = _fee_key(t)
    if fk and t['status'] == 'new' and not t['at']:
        t['fee'] = kit.price(c, fk, PRICES[fk])


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, earned=0)


def initial() -> dict:
    return dict(intro=False, today=_today(0), closed_day=0, open_day=0,
                stats=dict(jobs=0, good=0, active_days=0, earned=0, sold=0, bought=0, refused=0), desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _quality(wrong: int) -> int:
    return sk.quality(wrong, C.WRONG_COST, C.QUALITY_FLOOR)


def _severity(step_id: str) -> int:
    """A wrong call on papers, a fake or the purity is a trust matter for the review."""
    return 2 if step_id.split('.')[0] in ('giay', 'quet', 'tra') else 1


def refused(t: dict) -> bool:
    """A buy-back that ends in a refusal (a fake, a doubtful seller): no money changes hands."""
    return t['kind'] == 'mua' and 'tien.tra' not in t['_key']


def refinery(t: dict) -> int:
    """What the company pays the shop for the old gold of a buy-back (its middle price, the same day)."""
    n = t['needs']
    return t['_key']['can.phan'] * _row(t['day'], n['tuoi_key'])['mid'] // 10


def _paid(t: dict) -> int:
    """What the slip pays the shop when done (validate_slip checks t['paid'] against it)."""
    q = t['quality']
    if t['kind'] == 'open' or refused(t):
        return 0
    if t['kind'] == 'ban':
        return t['_key']['tien.vang'] + t['needs']['stone'] + max(1, t['fee'] * q // 100)
    if t['kind'] == 'mua':
        return max(1, (refinery(t) - t['_key']['tien.tra']) * q // 100)
    return max(5, t['fee'] * q // 100)


def has_cert(s: dict) -> bool:
    rec = ((s.get('journey') or {}).get('certificates') or {}).get(CERT_ID)
    return isinstance(rec, dict) and rec.get('earned_day') is not None


def _open_rules(d: dict, c: dict) -> None:
    setup = next((t['id'] for t in c['tasks'] if t.get('career') == ID and t.get('kind') == 'open'
                  and t['status'] not in ('completed', 'referred', 'cancelled')), None)
    kit.need(d['open_day'] == c['day'], 'Chưa mở tiệm: đếm két, kiểm cân, treo bảng giá trước đã nhé.', 'shop_closed',
         fix=dict(cmd='task_select', payload=dict(task=setup), label='🔐 Mở két') if setup else None)


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('vg_intro', 'vg_step', 'vg_desk', 'vg_out'), 'Thao tác ở tiệm vàng không hợp lệ.')
    d = _data(c)
    if name == 'vg_intro':
        d['intro'] = True
        return dict(message='Cô Ba Ngọc đưa cái kính lúp: “Cân trước mặt khách, giấy tờ rõ ràng. Vậy là giữ được tiệm.”')
    desk = d['desk']
    if name == 'vg_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở tiệm cần quyết, quyết xong rồi làm tiếp nhé.')
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc tiệm vàng.')
    if t['kind'] != 'open':
        _open_rules(d, c)
        kit.need(t['known'], 'Nghe khách cần gì trước đã.')
    if name == 'vg_out':
        return _out(s, c, d, t)
    n = t['needs']
    if t['kind'] == 'ban' and t['at'] == 0 and p.get('step') == 'khay.chon' and p.get('value') == t['_key']['khay.chon']:
        kit.need(kit.stock(c, n['piece']) > 0, f'Trong tủ hết {n["piece_name"].lower()}. Nhập thêm ở Kho, hoặc bấm “Hết hàng” mời khách ghé lại.',
                 'out_of_stock')
    correct, message, finished = sk.work(t, p, _quality, 'Cô Ba Ngọc', LINES, _severity)
    if t['kind'] == 'ban' and correct and t['at'] == 1 and not t['held']:   # the piece leaves the case: its cost goes on the slip
        t['cogs'] = kit.take(c, n['piece'])
        t['held'] = True
    if not finished:
        result = dict(message=message, correct=correct)
        _after(s, c, d, result)
        return result
    result = _finish(s, c, d, t)
    _after(s, c, d, result)
    return result


def _out(s: dict, c: dict, d: dict, t: dict) -> dict:
    kit.need(t['kind'] == 'ban' and t['at'] == 0, 'Chỉ mời khách ghé lại khi chưa lấy món ra khỏi tủ.')
    kit.need(kit.stock(c, t['needs']['piece']) == 0, 'Trong tủ còn món này, lấy ra bán cho khách nhé.')
    kit.complete(s, c, t, 0, f'Hết {t["needs"]["piece_name"].lower()}, xin số điện thoại báo khách khi có hàng.', status='referred')
    return dict(message='Đã xin số điện thoại khách, hẹn báo khi có hàng. Nhập thêm ở Kho nhé.')


def _finish(s: dict, c: dict, d: dict, t: dict) -> dict:
    n, kind = t['needs'], t['kind']
    paid = _paid(t)
    t['paid'] = paid
    good = t['quality'] >= 90
    if kind == 'open':
        d['open_day'] = c['day']
        kit.complete(s, c, t, 0, 'Két khớp sổ, cân đúng chuẩn, bảng giá đã treo.')
        return dict(message='🔓 Tiệm mở cửa: két đã đếm, cân đã kiểm, bảng giá đã treo. Mời khách vào nhé.', correct=True, celebrate=good)
    if kind == 'ban':
        margin = max(0, paid - t['cogs'])
        kit.complete(s, c, t, paid, f'Bán {n["piece_name"].lower()}, chất lượng {t["quality"]}%.', bonus_base=margin)
        d['stats']['sold'] += 1
        msg = f'Giao {n["piece_name"].lower()}. Thu {paid} xu: tiền vàng {t["_key"]["tien.vang"]} xu' + \
              (f', hột {n["stone"]} xu' if n['stone'] else '') + f', tiền công {paid - t["_key"]["tien.vang"] - n["stone"]} xu.'
    elif kind == 'mua' and refused(t):
        margin = 0
        d['stats']['refused'] += 1
        kit.complete(s, c, t, 0, 'Không mua món không rõ nguồn gốc / không phải vàng.')
        msg = 'Đã từ chối mua, ghi sổ đàng hoàng. Tiệm giữ được chữ tín.'
    elif kind == 'mua':
        payout = t['_key']['tien.tra']
        margin = paid
        kit.complete(s, c, t, payout + paid, f'Bán lại vàng cũ cho công ty: {refinery(t)} xu.', bonus_base=paid)
        kit.money(s, c, -payout, 'Trả tiền mua vàng cũ của khách', t['id'], 'stock')
        d['stats']['bought'] += 1
        msg = f'Trả khách {payout} xu, vàng cũ chuyển về công ty. Tiệm lời {paid} xu.'
    else:
        margin = paid
        kit.complete(s, c, t, paid, f'Kiểm định kim cương, chất lượng {t["quality"]}%.')
        msg = f'Phiếu kiểm định đã ghi. Phí kiểm định {paid} xu.'
        if has_cert(s):
            kit.money(s, c, 2, '🎓 Kiểm định có chứng chỉ', t['id'], 'other_income')
            msg += ' 🎓 Khách trả thêm 2 xu vì người kiểm định có chứng chỉ.'
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['earned'] += margin
    return dict(message=msg, correct=good, celebrate=good)


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, C.DESK, None)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(C.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_start(s: dict, c: dict) -> None:
    """The morning slip (slot 0) comes first every day; one left from an earlier day is put away."""
    d = _data(c)
    day = c['day']
    for t in c['tasks']:
        if t.get('career') == ID and t.get('kind') == 'open' and t['day'] < day and t['status'] not in ('completed', 'referred', 'cancelled'):
            t['status'] = 'cancelled'
    mine = [t for t in c['tasks'] if t.get('career') == ID and t['day'] == day]
    if not mine and d['open_day'] != day:
        t = make_task(day, 0, c['turn'])
        c['tasks'].append(t)
        c['active_task'] = t['id']
    kit.desk_start(s, c, ID, d['desk'], C.DESK, None, c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], C.DESK)
    if today['day'] == c['day'] and today['good'] > 0 and d['closed_day'] != c['day']:
        d['stats']['active_days'] += 1
        d['closed_day'] = c['day']
    lines = [f'Tiệm vàng phục vụ {today["jobs"]} lượt, {today["good"]} lượt đạt từ 90%, lời {today["earned"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, jobs=today['jobs'], clean=today['good'], earned=today['earned'])


def known_request(c: dict, t: dict) -> str:
    extra = ' Khách còn dặn thêm điều oái oăm, chốt với khách trước nhé.' if t['needs']['demands'] else ''
    return t['opening'] + extra


def hint(c, t: dict) -> str:
    if not t.get('known'):
        return 'Nghe khách cần gì.'
    steps = t['needs']['steps']
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Xong; mời khách tiếp theo.'


def feedback(c, t: dict) -> dict:
    steps = t['needs']['steps']
    n = len(t['errors'])
    talked = any(e.startswith('khach.') for e in t['errors'])
    honest = not any(e.split('.')[0] in ('giay', 'quet', 'tra', 'hd', 'so') for e in t['errors'])
    return dict(criteria=[dict(key='steps', label='Cân, tính đúng', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='talk', label='Nói thật với khách', score=3 if talked else 5, note='Yêu cầu oái oăm đã chốt thật thà.'),
                          dict(key='papers', label='Giấy tờ rõ ràng', score=5 if honest else 2, note='Hóa đơn, sổ mua hàng, giấy kiểm định.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
        return v
    v['needs'].pop('tuoi_key', None)   # the purity is the scanner step's answer
    if t['kind'] == 'ban' and t['at'] == 0:   # the first step is picking the piece: not named before it is answered
        for k in ('piece', 'piece_name', 'emoji', 'tuoi', 'cong', 'stone', 'sell'):
            v['needs'].pop(k, None)
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    st = d['stats']
    d['mastered'] = st['good'] >= C.MASTER[0] and st['active_days'] >= C.MASTER[1]
    d['expert'] = st['good'] >= C.EXPERT[0] and st['active_days'] >= C.EXPERT[1]
    d['desk'] = kit.desk_public(d['desk'], C.DESK, ID, c)
    day = max(1, c['day'])
    d['board'] = board(day)
    d['board_prev'] = board(day - 1) if day > 1 else None
    d['opened'] = d['open_day'] == c['day']
    return d


def content() -> dict:
    return dict(
        rules=C.RULES,
        pieces=[dict(id=k, name=x['name'], emoji=x['emoji'], tuoi=C.TUOI[x['tuoi']][1], phan=x['phan'], cong=x['cong']) for k, x in C.PIECES.items()],
        tuoi={k: dict(label=v[1], street=v[2]) for k, v in C.TUOI.items()},
        intro=dict(title='Một ngày ở tiệm vàng Ngọc Mây',
                   lead='Tiệm vàng bạc đá quý đầu chợ. Sáng đếm két, kiểm cân, treo bảng giá; rồi bán nữ trang, mua lại vàng cũ, kiểm định kim cương. '
                        'Cân trước mặt khách, giấy tờ rõ ràng, không mua đồ không rõ nguồn gốc.',
                   work=[['📈', 'Bảng giá mua vào, bán ra mỗi ngày'], ['⚖️', 'Cân chỉ, phân; xem tuổi vàng'],
                         ['💍', 'Bán nữ trang, tính tiền công'], ['💎', 'Kiểm định kim cương 4C']],
                   meet=[['💍', 'Cô Ba Ngọc chủ tiệm'], ['🔨', 'Chú Tư Bạc thợ kim hoàn'], ['🧕', 'Bà Năm Chợ khách quen']],
                   stars=[['⚖️', 'Cân trước mặt khách'], ['🧾', 'Hóa đơn, sổ mua hàng đủ dòng']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    sk.validate_slip(t, original, FIXED, _quality, _paid, LINES, 'phiếu tiệm vàng')
    fk = _fee_key(t)
    if fk:
        base = PRICES[fk]
        kit.need(type(t.get('fee')) is int and round(base * .75) <= t['fee'] <= round(base * 1.25), 'Tiền công trên phiếu sai.')
    else:
        kit.need(t.get('fee') == 0, 'Tiền công trên phiếu sai.')
    held = t.get('held')
    kit.need(type(held) is bool and held == (t['kind'] == 'ban' and t['at'] >= 1), 'Món lấy khỏi tủ sai.')
    top = math.ceil(ITEM[t['needs']['piece']]['cost'] * 1.35) if held else 0
    kit.need(type(t.get('cogs')) is int and 0 <= t['cogs'] <= top, 'Giá vốn món hàng sai.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ tiệm vàng sai.')
    kit.need(type(d['intro']) is bool, 'Sổ tiệm vàng sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), 'Thống kê tiệm vàng sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số lượt đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.integer(d['open_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], C.DESK)


SPEC = dict(
    id=ID, prefix=PREFIX, category='shop', people=PEOPLE,
    meta=dict(short='Tiệm vàng', place=C.PLACE, tagline='Cân trước mặt khách, giấy tờ rõ ràng.', icon='coin',
              color='#b8860b', light='#fbf3dc', weather='Đèn tủ kính vàng ấm, tiếng cân tít tít', work='Phiếu tiệm vàng',
              station='Quầy kính, cân tiểu ly và két sắt',
              greeting='Đếm két, kiểm cân, treo bảng giá rồi mới mở cửa. Cân trước mặt khách, giấy tờ rõ ràng.',
              caption='Vàng thật, giá thật, giấy tờ thật', map_label='TIỆM VÀNG NGỌC MÂY'),
    staff=[('Chú Tư Bạc', 'smith', 'Thợ kim hoàn: đánh bóng, hàn khoen, khắc chữ, coi tủ kính.', 72, 80)], roles={'smith': 'Thợ kim hoàn'},
    tip=1, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    inventory=dict(items=ITEMS, capacity=12),
    prices=PRICES,
    activity=('💍', 'Sổ tay tiệm vàng', [('1 chỉ', '10 phân = 3,75 g'), ('18K', '75% vàng'), ('Mua lại', 'Trừ 3% hàng tiệm khác'),
                                       ('Kim cương', '1 ct = 0,2 g')],
              ['Mở két, treo bảng giá', 'Cân trước mặt khách', 'Tính theo bảng hôm nay', 'Hóa đơn, sổ mua hàng đủ dòng']),
    stories=[('Chiếc cân tiểu ly', ('Cô Ba Ngọc lau chiếc cân cũ: “Cân này theo cô từ hồi mới mở tiệm.”',
                                    'Bạn đặt quả cân chuẩn lên, màn hình hiện đúng 10,00 g.',
                                    'Cô Ba cười: “Tiệm vàng sống nhờ cái cân. Cân sai một ly là mất khách cả đời.”'))],
    review_asides=['Tiệm cân trước mặt, tính từng phân rõ ràng.', 'Hóa đơn ghi đủ tuổi vàng, trọng lượng, tiền công.',
                   'Tiệm nói thật món nào vàng ta, món nào vàng tây.'],
    situations=[],
    more_line='Thêm một vị khách vừa bước vào tiệm vàng.',
    open_line='Cô Ba Ngọc mở cửa kính; cân tiểu ly, máy quét tuổi vàng và kính lúp đã sẵn trên quầy.',
    guide='Sáng: đếm két, kiểm cân, treo bảng giá → bán nữ trang (lấy món, cân phân, tính tiền vàng theo bảng, hóa đơn) · '
          'mua lại vàng cũ (giấy tờ, quét tuổi, cân, trừ hao, sổ mua hàng) · kiểm định kim cương 4C. Sai thì làm lại bước đó, tiền công giảm theo chất lượng.',
)
