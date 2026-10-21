"""🚗 Đại lý xe Phố Mây: a motorbike and car showroom the player runs (player #472 "làm chủ bán xe hơi, xe máy"; owner
21/10 "nghề mới thì làm đi").

A day starts with the morning slip (slot 0, kind 'open': check the frame number of the new batch against the factory
slip, the five-step PDI, an honest price board); no customer is served before it is done. Each customer is then a slip
of server-graded steps (game/careers/stepkit.py) of one of four kinds:
  ban      sell a vehicle: pick the model that fits the customer's need, licence and budget (it leaves the showroom
           now, FIFO, its cost kept as `cogs`), the awkward demands, an honest answer about its specs, [the test drive],
           the total with lệ phí trước bạ and the plate fee (passed on to the state, never income), [trả góp through
           the NPC bank: the 30 % down payment and the 40 % debt-to-income check, under game/bank.py's own rate and
           ceiling; the bank pays the dealer in full, the dealer never lends], the registration papers, [the plate:
           random at the police, a nice one only at the 🔨 auction], [the hand-over]. Pay: the list price + the
           registration service fee (SPEC prices, tunable 75–125 %, frozen on the slip) × quality.
  thu_cu   take a used vehicle in: papers and frame number (a filed-off number or no authorisation is refused), the
           price by age (10 % a year, at least 30 %), less the repairs, the purchase record. The used-vehicle yard buys
           it the same day at 106 %: the dealer's margin is that 6 % × quality; nothing is kept, nothing to speculate.
  hau_mai  after-sales: the warranty call (crash damage and modified parts are not covered), the first service in
           order, the next service mark. Pay: the service fee × quality.
  pk       an accessory off the shelf (a certified helmet of the right size, a lock, floor mats, a dash camera).
Out of stock (`dx_out`): a sale whose model or accessory is not in the showroom is referred before it starts.

The players' own vehicles: "Mua xe cho mình" in the client opens 🚗 Xe & phương tiện (game/garage.py) at its own
prices; the showroom never sells a vehicle to a player (a dealer's price would turn the garage's sink into a transfer).
Players' cars are serviced through 🛎️ Phố dịch vụ (game/dealer_service.py): 🔧 Bảo dưỡng ô tô, worked here as a
three-step job (dx_svc) whose finish is recorded in `svc_ok`, read by the market's deliver hook.
"""
from __future__ import annotations

from copy import deepcopy
import math

from . import kit
from . import car_dealer_content as C
from . import stepkit as sk

ID = 'car_dealer'
CERT_ID = 'car_dealer_basics'   # certificate_content.GROUPS (hire=False): its perk is 2 xu more on each after-sales job
PREFIX = 'dx_'
GEN = 1
PEOPLE = C.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind')
PHYSICAL = ('dx_step', 'dx_out', 'dx_svc')
FREE = ('dx_intro',)
NO_TICK = ('dx_intro', 'dx_desk')
LINES = 24
KINDS = ('open', 'ban', 'thu_cu', 'hau_mai', 'pk')
SERVICES = ('bao_duong_oto',)
PRICES = {**{k: v['base'] for k, v in C.FEES.items()}, **{k: v['base'] for k, v in C.ACCESSORIES.items()}}
LOAN_PCT = 30   # the least down payment of trả góp (% of the list price, rounded up)
LOAN_TERM = 28  # days


def _cost(m: dict) -> int:
    return m['price'] * m['cost_pct'] // 100


ITEMS = ([dict(id=k, name=m['name'], emoji=m['emoji'], group='xe_may' if m['kind'] == 'xm' else 'o_to', unit='chiếc', cost=_cost(m),
               price=m['price'], start=m['start'], **({'unlock': m['unlock']} if m.get('unlock') else {})) for k, m in C.MODELS.items()]
         + [dict(id=k, name=a['name'], emoji=a['emoji'], group='phu_kien', unit=a['unit'], cost=a['cost'], price=a['base'], start=a['start'])
            for k, a in C.ACCESSORIES.items()])
ITEM = {x['id']: x for x in ITEMS}


def tax(model: str) -> tuple:
    """(lệ phí trước bạ, plate fee) of a model: passed on to the state, never the dealer's income."""
    m = C.MODELS[model]
    pct, plate = C.TAX[m['kind']]
    return m['price'] * pct // 100, plate


def _km(v: int) -> str:
    return f'{v:,}'.replace(',', '.')


def _demands(r, day: int, kind: str, level: int) -> list:
    pool = [x for x in C.DEMANDS if x[0] <= day and (x[4] is None or kind in x[4])]
    want = 2 if level >= 2 and r.random() < 0.5 else 1
    return [sk.scenario(r, 'khach', f'd{i + 1}', 'Khách dặn điều oái oăm', d[1:4]) for i, d in enumerate(r.sample(pool, min(want, len(pool))))]


# ---------------------------------------------------------------- building a slip (pure: day, slot)
def _open(day: int) -> tuple:
    r = kit.rng(ID, day, 0)
    vin = ''.join(r.choice('ABCDEFGHJKLMNPRSTUVWXYZ0123456789') for _ in range(6))
    match = r.random() < 0.75
    seen = vin if match else vin[:-1] + r.choice([ch for ch in '0123456789' if ch != vin[-1]])
    right = 'Khớp: ký nhận lô xe, cất phiếu xuất xưởng vào hồ sơ' if match else 'Không khớp: không nhận chiếc đó, lập biên bản gửi hãng'
    wrong = 'Không khớp: không nhận chiếc đó, lập biên bản gửi hãng' if match else 'Khớp: ký nhận lô xe, cất phiếu xuất xưởng vào hồ sơ'
    pairs = [sk.scenario(r, 'vin', 'doi', 'Đối chiếu số khung', (f'Phiếu xuất xưởng ghi số khung …{vin}. Soi số khung đóng trên xe: …{seen}.',
                                                               right, (wrong, 'Ký nhận trước, kiểm sau cũng được')))]
    pairs.append(sk.ordered(r, 'pdi', 'kiem', 'Kiểm xe mới (PDI)', 'Bấm lần lượt năm bước kiểm xe mới trước khi trưng bày.', C.PDI))
    pairs.append(sk.picks(r, 'gia', 'niem_yet', 'Niêm yết bảng giá', 'Bảng giá treo ở showroom ghi những dòng nào?', C.LISTING_GOOD, C.LISTING_BAD))
    steps, key = sk.pairs_to_steps(pairs)
    return (dict(steps=steps, demands=0), key, C.MENTOR, 'Nhận lô xe, mở showroom',
            'Anh Quân dặn: “Xe mới về: đối số khung, kiểm năm bước, treo bảng giá cho đàng hoàng rồi mới mở cửa nghe.”')


def _models(day: int) -> list:
    return [k for k, m in C.MODELS.items() if day >= m['day']]


def _ban(day: int, slot: int, r, level: int) -> tuple:
    k = r.choice(_models(day))
    m = C.MODELS[k]
    npc, words = r.choice(C.NEEDS[k])
    who = C.PEOPLE[npc][0]
    pool = [o for o in C.MODELS if o != k]
    opts, ids = sk.lettered(r, [(o, f'{C.MODELS[o]["name"]} · {_km(C.MODELS[o]["price"])} xu') for o in [k] + r.sample(pool, 3)])
    pairs = [(sk.step('xe', 'chon', 'choice', 'Chọn xe hợp nhu cầu', f'{who}: “{words}”', opts), ids[k])]
    demands = _demands(r, day, 'ban', level)
    pairs += demands
    pairs.append(sk.scenario(r, 'xe', 'thong_so', 'Nói thật thông số', (f'Khách hỏi: “{m["spec"][0]}”',) + m['spec'][1:]))
    if k != 'dx_xe_dien' and r.random() < 0.6:   # an e-bike needs no licence
        pairs.append(sk.picks(r, 'lai', 'thu', 'Cho khách lái thử', 'Khách muốn lái thử. Làm những việc nào?', C.DRIVE_GOOD, C.DRIVE_BAD))
    before, plate = tax(k)
    pct = C.TAX[m['kind']][0]
    kind_name = 'xe máy' if m['kind'] == 'xm' else 'ô tô'
    pairs.append((sk.step('tien', 'tong', 'number', 'Tính tổng tiền khách trả',
                          f'Giá xe {_km(m["price"])} xu (đã gồm VAT). Lệ phí trước bạ {kind_name} {pct}% giá xe, bỏ phần lẻ; phí biển số {plate} xu. '
                          'Khách trả tất cả bao nhiêu xu?', unit='xu'), m['price'] + before + plate))
    loan = None
    if level >= 1 and r.random() < 0.4:
        down = -(-m['price'] * LOAN_PCT // 100)
        principal = m['price'] - down
        if principal <= 5000:
            from .. import bank
            pay = bank.installment(principal, bank.LOAN_BP['personal'], LOAN_TERM // bank.LOAN_PERIOD)
            ok = r.random() < 0.6
            income = (pay * 100 + 39) // 40 + r.randrange(0, 40) if ok else max(1, pay * 100 // 40 - r.randrange(10, 60))
            pairs.append((sk.step('gop', 'tra_truoc', 'number', 'Tính tiền trả trước',
                                  f'Khách muốn trả góp. Sổ tay: trả trước ít nhất {LOAN_PCT}% giá xe, làm tròn lên. Trả trước ít nhất bao nhiêu xu?',
                                  unit='xu'), down))
            pairs.append(sk.scenario(r, 'gop', 'duyet', 'Xét hồ sơ trả góp',
                                     (f'Vay {_km(principal)} xu trong {LOAN_TERM} ngày, Ngân hàng Phố tính mỗi tuần góp {pay} xu. '
                                      f'Giấy tờ thu nhập của khách: {income} xu mỗi tuần.',
                                      C.LOAN_OK if ok else C.LOAN_NO, ((C.LOAN_NO if ok else C.LOAN_OK),) + C.LOAN_WRONG)))
            loan = dict(down=down, principal=principal, pay=pay, ok=ok)
    pairs.append(sk.picks(r, 'giay', 'ho_so', 'Làm hồ sơ đăng ký', 'Bộ hồ sơ đăng ký xe gồm những gì?', C.PAPERS_GOOD, r.sample(C.PAPERS_BAD, 2)))
    if r.random() < 0.5:
        pairs.append(sk.scenario(r, 'giay', 'bien', 'Biển số xe', C.PLATE))
    if r.random() < 0.6:
        pairs.append(sk.picks(r, 'giao', 'kiem', 'Giao xe cho khách', 'Trước khi trao chìa khóa, làm những việc nào?', C.HANDOVER_GOOD, C.HANDOVER_BAD))
    steps, key = sk.pairs_to_steps(pairs)
    needs = dict(steps=steps, demands=len(demands), model=k, model_name=m['name'], emoji=m['emoji'], vkind=m['kind'],
                 price=m['price'], tax=before, plate=plate, loan=loan, vid=m['vid'])
    return needs, key, npc, f'{who} xem xe', f'{who}: “{words}”'


def _thu_cu(day: int, slot: int, r, level: int) -> tuple:
    roll = r.random() if level >= 1 else 1.0
    if roll < 0.15:
        row = r.choice(C.TRADE_BAD)
        pairs = [sk.scenario(r, 'giay', 'cavet', 'Xem giấy tờ xe', row)]
        pairs.append(sk.picks(r, 'bao', 'ghi', 'Ghi lại để báo công an', 'Từ chối mua rồi. Ghi lại những gì?',
                              ('Biển số và đặc điểm xe', 'Mô tả người bán và giờ tới', 'Số khung đọc được trên xe'),
                              ('Giữ xe của khách lại', 'Đăng ảnh khách lên mạng')))
        steps, key = sk.pairs_to_steps(pairs)
        who = C.PEOPLE[C.STRANGER][0]
        return (dict(steps=steps, demands=0, used='Chiếc xe máy cũ', refused=True), key, C.STRANGER, f'{who} muốn bán xe gấp',
                f'{who} dắt chiếc xe máy cũ vào: “Bán gấp, tính lẹ giùm anh.”')
    pool = [u for u in C.USED if u != 'oto_mini' or day >= C.MILESTONES[0]]
    u = r.choice(pool)
    name, new, (lo, hi) = C.USED[u]
    years = r.randint(lo, hi)
    npc = r.choice(C.CUSTOMERS)
    who = C.PEOPLE[npc][0]
    pairs = [sk.scenario(r, 'giay', 'cavet', 'Xem giấy tờ xe', C.TRADE_OK)]
    demands = _demands(r, day, 'thu_cu', level)
    pairs += demands
    pct, floor = C.DEPRECIATE
    value = new * max(floor, 100 - pct * years) // 100
    pairs.append((sk.step('gia', 'tuoi', 'number', 'Tính giá theo tuổi xe',
                          f'{name}, giá xe mới {_km(new)} xu, đã dùng {years} năm. Sổ tay: mỗi năm trừ {pct}% giá mới, thấp nhất còn {floor}%. '
                          'Giá theo tuổi bao nhiêu xu (bỏ phần lẻ)?', unit='xu'), value))
    fixes = r.sample(C.REPAIRS, r.randint(1, 3))
    repairs = sum(x for _, x in fixes)
    pairs.append((sk.step('gia', 'thu', 'number', 'Trừ tiền sửa, chốt giá thu',
                          'Tú kiểm xe: ' + '; '.join(f'{w.lower()} (sửa {x} xu)' for w, x in fixes) + '. Giá thu = giá theo tuổi trừ tiền sửa. '
                          'Trả khách bao nhiêu xu?', unit='xu'), value - repairs))
    pairs.append(sk.picks(r, 'so', 'ghi', 'Lập hồ sơ thu xe', 'Hồ sơ thu xe cũ phải có những gì?', C.TRADE_LEDGER_GOOD, C.TRADE_LEDGER_BAD))
    steps, key = sk.pairs_to_steps(pairs)
    needs = dict(steps=steps, demands=len(demands), used=name, years=years, refused=False)
    return needs, key, npc, f'{who} bán lại xe cũ', f'{who} dắt chiếc {name.lower()} đã dùng {years} năm vào: “Đại lý thu lại giá bao nhiêu?”'


def _hau_mai(day: int, slot: int, r, level: int) -> tuple:
    npc = r.choice(C.CUSTOMERS)
    who = C.PEOPLE[npc][0]
    pairs = [sk.scenario(r, 'bh', 'xet', 'Xét bảo hành', r.choice(C.WARRANTY))]
    demands = _demands(r, day, 'hau_mai', level)
    pairs += demands
    pairs.append(sk.ordered(r, 'bd', 'lam', 'Bảo dưỡng đúng thứ tự', 'Xe tới mốc bảo dưỡng. Bấm lần lượt các việc.', C.SERVICE))
    now = r.randrange(C.SERVICE_FIRST + 200, 30000, 100)
    n = (now - C.SERVICE_FIRST) // C.SERVICE_EVERY + 1
    nxt = C.SERVICE_FIRST + n * C.SERVICE_EVERY
    pairs.append((sk.step('bd', 'hen', 'number', 'Hẹn mốc bảo dưỡng kế tiếp',
                          f'Sổ bảo hành: bảo dưỡng lần đầu ở {_km(C.SERVICE_FIRST)} km, sau đó mỗi {_km(C.SERVICE_EVERY)} km. '
                          f'Đồng hồ xe đang {_km(now)} km. Mốc kế tiếp là bao nhiêu km?', unit='km'), nxt))
    steps, key = sk.pairs_to_steps(pairs)
    return (dict(steps=steps, demands=len(demands)), key, npc, f'{who} mang xe tới bảo dưỡng',
            f'{who} chạy xe vào xưởng: “Xe tới hẹn bảo dưỡng, mà có chỗ này muốn hỏi bảo hành.”')


def _pk(day: int, slot: int, r, level: int) -> tuple:
    k = r.choice(tuple(C.ACC_WANT))
    a = C.ACCESSORIES[k]
    npc, words = r.choice(C.ACC_WANT[k])
    who = C.PEOPLE[npc][0]
    opts, ids = sk.lettered(r, [(o, C.ACCESSORIES[o]['name']) for o in C.ACCESSORIES])
    pairs = [(sk.step('pk', 'chon', 'choice', 'Lấy đúng món', f'{who}: “{words}”', opts), ids[k])]
    if k == 'dx_mu':
        lo, hi, size = r.choice(C.HELMET)
        cm = r.randint(lo, hi)
        o2, i2 = sk.lettered(r, [(s, f'Cỡ {s}') for _, _, s in C.HELMET])
        pairs.append((sk.step('pk', 'co', 'choice', 'Chọn cỡ mũ', f'Đo vòng đầu khách bằng thước dây: {cm} cm. Lấy mũ cỡ nào?', o2), i2[size]))
    elif k == 'dx_camera':
        gb, per = r.choice(((32, 4), (64, 8), (128, 8), (64, 4)))
        pairs.append((sk.step('pk', 'the', 'number', 'Tính giờ ghi hình',
                              f'Thẻ nhớ {gb} GB, camera ghi {per} GB mỗi giờ. Ghi được bao nhiêu giờ thì bắt đầu ghi đè?', unit='giờ'), gb // per))
    demands = _demands(r, day, 'pk', level)
    pairs += demands
    pairs.append(sk.picks(r, 'pk', 'giao', 'Giao hàng cho khách', 'Trước khi đưa món cho khách, làm những việc nào?', C.ACC_HAND_GOOD, C.ACC_HAND_BAD))
    steps, key = sk.pairs_to_steps(pairs)
    return (dict(steps=steps, demands=len(demands), item=k, item_name=a['name'], emoji=a['emoji']), key, npc,
            f'{who} mua phụ kiện', f'{who}: “{words}”')   # the title never names it: picking it is a step


def slip(day: int, slot: int) -> tuple:
    """(kind, needs, key, npc, title, opening) of (day, slot). Pure."""
    if slot == 0:
        return ('open',) + _open(day)
    r = kit.rng(ID, day, slot)
    level = sum(day >= n for n in C.MILESTONES)
    roll = r.random()
    if roll < 0.45:
        kind = 'ban'
    elif roll < 0.62:
        kind = 'pk'
    elif roll < 0.82 and day >= 2:
        kind = 'thu_cu'
    elif day >= C.MILESTONES[0]:
        kind = 'hau_mai'
    else:
        kind = 'ban'
    return (kind,) + {'ban': _ban, 'thu_cu': _thu_cu, 'hau_mai': _hau_mai, 'pk': _pk}[kind](day, slot, r, level)


def _fee_key(t: dict) -> str | None:
    kind = t['kind']
    if kind == 'ban':
        return 'dv_dang_ky_xm' if t['needs']['vkind'] == 'xm' else 'dv_dang_ky_ot'
    if kind == 'hau_mai':
        return 'bao_duong'
    if kind == 'pk':
        return t['needs']['item']
    return None


def _stock_item(t: dict) -> str | None:
    return t['needs']['model'] if t['kind'] == 'ban' else t['needs']['item'] if t['kind'] == 'pk' else None


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
    """The dealer's own price list is frozen on the slip when the customer walks in."""
    fk = _fee_key(t)
    if fk and t['status'] == 'new' and not t['at']:
        t['fee'] = kit.price(c, fk, PRICES[fk])


# ---------------------------------------------------------------- player jobs (🛎️ Phố dịch vụ, game/dealer_service.py)
def svc_job(order: str, service: str) -> tuple:
    """(steps, key) of a player's car service: the same three steps for one order, always. Pure."""
    r = kit.rng(ID, 'svc', order, service)
    now = r.randrange(C.SERVICE_FIRST + 200, 40000, 100)
    n = (now - C.SERVICE_FIRST) // C.SERVICE_EVERY + 1
    return sk.pairs_to_steps((
        sk.ordered(r, 'bd', 'lam', 'Bảo dưỡng đúng thứ tự', 'Bấm lần lượt các việc bảo dưỡng ô tô.', C.SERVICE),
        (sk.step('bd', 'hen', 'number', 'Hẹn mốc bảo dưỡng kế tiếp',
                 f'Bảo dưỡng lần đầu ở {_km(C.SERVICE_FIRST)} km, sau đó mỗi {_km(C.SERVICE_EVERY)} km. Đồng hồ xe đang {_km(now)} km. '
                 'Mốc kế tiếp là bao nhiêu km?', unit='km'), C.SERVICE_FIRST + n * C.SERVICE_EVERY),
        sk.picks(r, 'bd', 'an_toan', 'Kiểm an toàn trước khi giao', 'Bảo dưỡng ô tô: kiểm những gì?',
                 ('Áp suất và gai lốp', 'Má phanh, dầu phanh', 'Đèn, còi, gạt mưa', 'Dây đai an toàn'),
                 ('Tắt đèn báo lỗi cho khỏi hiện', 'Chỉnh lùi đồng hồ km'))))


def _svc(d: dict, p: dict) -> dict:
    return sk.svc_work(d, p, SERVICES, svc_job, '🔧 Bảo dưỡng xong! Bấm Giao để trả xe cho khách ở 🛎️ Phố dịch vụ.')


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, earned=0)


def initial() -> dict:
    return dict(intro=False, today=_today(0), closed_day=0, open_day=0,
                stats=dict(jobs=0, good=0, active_days=0, earned=0, sold=0, traded=0, refused=0, svc=0),
                desk=kit.desk_initial(), svc=[], svc_ok=[])


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _quality(wrong: int) -> int:
    return sk.quality(wrong, C.WRONG_COST, C.QUALITY_FLOOR)


def _severity(step_id: str) -> int:
    """A wrong call on papers, the frame number or a loan is a trust matter for the review."""
    return 2 if step_id.split('.')[0] in ('giay', 'vin', 'gop', 'bh') else 1


def refused(t: dict) -> bool:
    return t['kind'] == 'thu_cu' and t['needs']['refused']


def yard(t: dict) -> int:
    """What the used-vehicle yard pays the dealer for a trade-in (the same day)."""
    return t['_key']['gia.thu'] * C.YARD_PCT // 100


def _paid(t: dict) -> int:
    q, kind = t['quality'], t['kind']
    if kind == 'open' or refused(t):
        return 0
    if kind == 'ban':
        return t['needs']['price'] + max(1, t['fee'] * q // 100)
    if kind == 'thu_cu':
        return max(1, (yard(t) - t['_key']['gia.thu']) * q // 100)
    return max(1, t['fee'] * q // 100)


def has_cert(s: dict) -> bool:
    rec = ((s.get('journey') or {}).get('certificates') or {}).get(CERT_ID)
    return isinstance(rec, dict) and rec.get('earned_day') is not None


def _open_rules(d: dict, c: dict) -> None:
    kit.need(d['open_day'] == c['day'], 'Chưa mở showroom: đối số khung, kiểm xe mới, treo bảng giá trước đã nhé.', 'shop_closed')


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('dx_intro', 'dx_step', 'dx_desk', 'dx_out', 'dx_svc'), 'Thao tác ở đại lý xe không hợp lệ.')
    d = _data(c)
    if name == 'dx_intro':
        d['intro'] = True
        return dict(message='Anh Quân đưa xấp catalogue: “Bán chiếc xe, giữ người khách. Nói thật thông số, giấy tờ cho đủ.”')
    desk = d['desk']
    if name == 'dx_desk':
        return kit.desk_choose(s, c, ID, desk, C.DESK, p.get('option'))
    kit.desk_block(desk, 'Có chuyện ở showroom cần quyết, quyết xong rồi làm tiếp nhé.')
    if name == 'dx_svc':
        return _svc(d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Việc này không thuộc đại lý xe.')
    if t['kind'] != 'open':
        _open_rules(d, c)
        kit.need(t['known'], 'Nghe khách cần gì trước đã.')
    if name == 'dx_out':
        return _out(s, c, t)
    item = _stock_item(t)
    first = t['needs']['steps'][0]['id'] if t['needs']['steps'] else None
    if item and t['at'] == 0 and p.get('step') == first and p.get('value') == t['_key'][first]:
        kit.need(kit.stock(c, item) > 0, f'Showroom hết {ITEM[item]["name"].lower()}. Nhập thêm ở Kho, hoặc bấm “Hết hàng” hẹn khách.',
                 'out_of_stock')
    correct, message, finished = sk.work(t, p, _quality, 'Anh Quân', LINES, _severity)
    if item and correct and t['at'] == 1 and not t['held']:   # the vehicle or accessory leaves the showroom: its cost goes on the slip
        t['cogs'] = kit.take(c, item)
        t['held'] = True
    if not finished:
        result = dict(message=message, correct=correct)
        _after(s, c, d, result)
        return result
    result = _finish(s, c, d, t)
    _after(s, c, d, result)
    return result


def _out(s: dict, c: dict, t: dict) -> dict:
    item = _stock_item(t)
    kit.need(item and t['at'] == 0, 'Chỉ hẹn khách khi chưa lấy hàng ra.')
    kit.need(kit.stock(c, item) == 0, 'Showroom còn hàng này, lấy ra bán cho khách nhé.')
    kit.complete(s, c, t, 0, f'Hết {ITEM[item]["name"].lower()}, ghi số điện thoại báo khách khi hàng về.', status='referred')
    return dict(message='Đã ghi số điện thoại khách, hẹn báo khi hàng về. Nhập thêm ở Kho nhé.')


def _finish(s: dict, c: dict, d: dict, t: dict) -> dict:
    n, kind = t['needs'], t['kind']
    paid = _paid(t)
    t['paid'] = paid
    good = t['quality'] >= 90
    margin = paid
    if kind == 'open':
        d['open_day'] = c['day']
        kit.complete(s, c, t, 0, 'Lô xe mới đã kiểm, bảng giá đã treo.')
        return dict(message='🔓 Showroom mở cửa: xe đã kiểm, bảng giá đã treo. Mời khách vào nhé.', correct=True, celebrate=good)
    if kind == 'ban':
        margin = max(0, paid - t['cogs'])
        kit.complete(s, c, t, paid, f'Bán {n["model_name"].lower()}, chất lượng {t["quality"]}%.', bonus_base=margin)
        d['stats']['sold'] += 1
        loan = n.get('loan')
        how = ' Ngân hàng Phố giải ngân phần vay.' if loan and loan['ok'] else ''
        msg = (f'Giao {n["model_name"].lower()}. Khách trả {n["price"] + n["tax"] + n["plate"]} xu: xe {n["price"]} xu, '
               f'trước bạ {n["tax"]} xu và biển số {n["plate"]} xu nộp hộ; đại lý thu thêm phí đăng ký {paid - n["price"]} xu.{how}')
    elif kind == 'thu_cu' and refused(t):
        d['stats']['refused'] += 1
        kit.complete(s, c, t, 0, 'Không thu xe giấy tờ không khớp.')
        msg = 'Đã từ chối thu xe, ghi lại đặc điểm. Đại lý giữ được chữ tín.'
    elif kind == 'thu_cu':
        price = t['_key']['gia.thu']
        kit.complete(s, c, t, price + paid, f'Bãi xe cũ mua lại {n["used"].lower()}: {yard(t)} xu.', bonus_base=paid)
        kit.money(s, c, -price, 'Trả tiền thu xe cũ của khách', t['id'], 'stock')
        d['stats']['traded'] += 1
        msg = f'Trả khách {price} xu, xe chuyển về bãi xe cũ. Đại lý lời {paid} xu.'
    elif kind == 'hau_mai':
        kit.complete(s, c, t, paid, f'Bảo dưỡng xe, chất lượng {t["quality"]}%.')
        msg = f'Xe bảo dưỡng xong, sổ đã ghi mốc kế tiếp. Phí {paid} xu.'
        if has_cert(s):
            kit.money(s, c, 2, '🎓 Bảo dưỡng có chứng chỉ', t['id'], 'other_income')
            msg += ' 🎓 Khách trả thêm 2 xu vì thợ có chứng chỉ.'
    else:
        margin = max(0, paid - t['cogs'])
        kit.complete(s, c, t, paid, f'Bán {n["item_name"].lower()}.', bonus_base=margin)
        msg = f'Giao {n["item_name"].lower()}, thu {paid} xu.'
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
    lines = [f'Đại lý xe phục vụ {today["jobs"]} lượt khách, {today["good"]} lượt đạt từ 90%, lời {today["earned"]} xu.']
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
    honest = not any(e.split('.')[0] in ('giay', 'vin', 'gop', 'bh', 'xe') for e in t['errors'])
    return dict(criteria=[dict(key='steps', label='Làm đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='talk', label='Nói thật với khách', score=3 if talked else 5, note='Yêu cầu oái oăm đã chốt thật thà.'),
                          dict(key='papers', label='Thông số, giấy tờ rõ ràng', score=5 if honest else 2, note='Thông số theo hãng, hồ sơ đủ, trả góp đúng luật.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    if not t['known']:
        v['needs'] = None
    elif t['kind'] == 'ban' and t['at'] == 0:   # the first step is picking the model: not named before it is answered
        for k in ('model', 'model_name', 'emoji', 'price', 'tax', 'plate', 'vid', 'vkind', 'loan'):
            v['needs'].pop(k, None)
    elif t['kind'] == 'pk' and t['at'] == 0:
        for k in ('item', 'item_name', 'emoji'):
            v['needs'].pop(k, None)
    if v.get('needs') and v['needs'].get('loan'):
        v['needs']['loan'] = {k: x for k, x in v['needs']['loan'].items() if k != 'ok'}
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    st = d['stats']
    d['mastered'] = st['good'] >= C.MASTER[0] and st['active_days'] >= C.MASTER[1]
    d['expert'] = st['good'] >= C.EXPERT[0] and st['active_days'] >= C.EXPERT[1]
    d['desk'] = kit.desk_public(d['desk'], C.DESK, ID, c)
    d['svc'], d['svc_ok'] = sk.svc_public(kit.data(c), svc_job)
    d['opened'] = d['open_day'] == c['day']
    return d


def content() -> dict:
    return dict(
        rules=C.RULES,
        models=[dict(id=k, name=m['name'], emoji=m['emoji'], kind=m['kind'], price=m['price'], vid=m['vid'], day=m['day']) for k, m in C.MODELS.items()],
        accessories=[dict(id=k, name=a['name'], emoji=a['emoji']) for k, a in C.ACCESSORIES.items()],
        intro=dict(title='Một ngày ở Đại lý xe Phố Mây',
                   lead='Showroom xe máy và ô tô của phố. Sáng nhận lô xe, kiểm năm bước, treo bảng giá; rồi tư vấn đúng nhu cầu, nói thật thông số, '
                        'làm giấy tờ, thu xe cũ, bảo dưỡng. Trả góp qua Ngân hàng Phố, đại lý không tự cho nợ.',
                   work=[['🚗', 'Tư vấn xe theo nhu cầu, bằng lái, ngân sách'], ['🧾', 'Trước bạ, biển số, hồ sơ đăng ký'],
                         ['🔁', 'Thu xe cũ theo tuổi xe'], ['🔧', 'Bảo hành, bảo dưỡng']],
                   meet=[['🚗', 'Anh Quân chủ đại lý'], ['📂', 'Chị Mai lo giấy tờ'], ['🔧', 'Tú kỹ thuật viên']],
                   stars=[['📋', 'Thông số theo hãng'], ['🔑', 'Giấy tờ đủ rồi mới giao xe']]))


# ---------------------------------------------------------------- validation
def validate_task(t: dict, original: dict) -> None:
    sk.validate_slip(t, original, FIXED, _quality, _paid, LINES, 'phiếu đại lý xe')
    fk = _fee_key(t)
    if fk:
        base = PRICES[fk]
        kit.need(type(t.get('fee')) is int and round(base * .75) <= t['fee'] <= round(base * 1.25), 'Phí trên phiếu sai.')
    else:
        kit.need(t.get('fee') == 0, 'Phí trên phiếu sai.')
    item = _stock_item(t)
    held = t.get('held')
    kit.need(type(held) is bool and held == (item is not None and t['at'] >= 1), 'Hàng lấy khỏi showroom sai.')
    top = math.ceil(ITEM[item]['cost'] * 1.35) if held else 0
    kit.need(type(t.get('cogs')) is int and 0 <= t['cogs'] <= top, 'Giá vốn trên phiếu sai.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ đại lý xe sai.')
    kit.need(type(d['intro']) is bool, 'Sổ đại lý xe sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), 'Thống kê đại lý xe sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số lượt đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.integer(d['open_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], C.DESK)
    sk.svc_validate(d, SERVICES, svc_job)


SPEC = dict(
    id=ID, prefix=PREFIX, category='shop', people=PEOPLE,
    meta=dict(short='Đại lý xe', place=C.PLACE, tagline='Bán chiếc xe, giữ người khách.', icon='bike',
              color='#1f5f8b', light='#e3eff8', weather='Mùi xe mới, sàn showroom bóng loáng', work='Phiếu đại lý xe',
              station='Showroom, bàn giấy tờ và xưởng bảo dưỡng',
              greeting='Nhận lô xe, kiểm năm bước, treo bảng giá rồi mới mở cửa. Tư vấn đúng nhu cầu, nói thật thông số.',
              caption='Xe đúng người, giấy đủ tờ', map_label='ĐẠI LÝ XE PHỐ MÂY'),
    staff=[('Tú', 'tech', 'Kỹ thuật viên: kiểm xe mới, bảo dưỡng, lau xe trước khi giao.', 72, 80)], roles={'tech': 'Kỹ thuật viên'},
    tip=1, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK, waste_items=(),
    inventory=dict(items=ITEMS, capacity=80),   # inventory.LINE_MAX: every stocked shelf holds 80 (tests/test_stock_limits.py)
    prices=PRICES,
    activity=('🚗', 'Sổ tay đại lý xe', [('Trước bạ', 'Xe máy 2%, ô tô 10%'), ('Trả góp', 'Trả trước 30%, góp ≤ 40% thu nhập'),
                                       ('Thu xe cũ', 'Trừ 10% mỗi năm'), ('Bảo hành', '3 năm / 30.000 km')],
              ['Nhận lô xe, kiểm năm bước', 'Tư vấn đúng nhu cầu', 'Tính đủ phí, làm đủ giấy', 'Giao xe, hẹn bảo dưỡng']),
    stories=[('Chiếc xe đầu tiên', ('Anh Quân chỉ chiếc xe Cub cũ dựng góc showroom: “Chiếc đầu tiên anh bán, mười lăm năm trước.”',
                                    'Bạn lau lại yên xe, tem bảo hành cũ vẫn còn dán.',
                                    'Anh Quân cười: “Khách đó giờ mua chiếc thứ ba ở đây. Nói thật một lần, người ta nhớ cả đời.”'))],
    review_asides=['Đại lý nói thật thông số, không vẽ thêm.', 'Giấy tờ làm gọn, hẹn biển số đúng ngày.', 'Thu xe cũ tính rõ từng khoản.'],
    situations=[],
    more_line='Thêm một vị khách vừa bước vào showroom.',
    open_line='Anh Quân kéo cửa kính; xe đã lau bóng, bảng giá và sổ tay đại lý đã sẵn.',
    guide='Sáng: đối số khung, kiểm xe mới năm bước, treo bảng giá → bán xe (chọn xe hợp nhu cầu, nói thật thông số, lái thử, tính trước bạ và biển số, '
          'trả góp qua ngân hàng, hồ sơ đăng ký, giao xe) · thu xe cũ theo tuổi xe · bảo hành, bảo dưỡng · bán phụ kiện. Sai thì làm lại bước đó.',
)
