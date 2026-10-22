"""🛒 The selling counter shared by the station-style shops: 🍱 Căn tin trường học (canteen) and ✏️ Tiệm văn phòng phẩm
(stationery). Owner 22/10: "UI như kiểu của trà sữa, show hết ra người ta chọn như game bán hàng ấy".

Everything the shop sells is on one counter at once (public/js/careers/counter_kit.js): the shelves in a grid with their
stock counts, the services, the customer's bubble and the tray. A customer is one task: what they ask for (`needs`,
pure of (day, slot)), the tray the player fills by tapping goods (`tray`: item → quantity) and one hand-over (`serve`)
that the server grades against the order:

  lines    each asked line: `any` (the goods that answer it: one id, or several when "cái nào cũng được") × `qty`
  budget   the most the customer can pay (a student's pocket money): a bill above it is refused at the counter
  avoid    tags the customer cannot take (an allergy, a vegetarian): one in the tray is a safety mistake
  sample   (canteen lunch trays) the day's food sample must be kept before the first tray leaves the kitchen

A wrong hand-over keeps the tray to fix, is logged once per kind (a review slip) and lowers the task's quality; nothing
leaves the shelf until the tray is right. Then the goods leave the stock (FIFO, their cost kept as `cogs`), a service
uses its material (giấy bọc, nhãn, giấy A4) and the customer pays the list price (fixed: the school's canteen board,
the cover price of a notebook). The margin (bill − cogs) counts for the quality gear and the competition.

A rush customer (`bell`: the canteen's morning and recess queues) leaves when the school bell rings: `bell` beats
(turns) after they joined the queue, unless the shift is calm or the player is still learning the place.
Each shop module passes a `Shop` (its ids, goods, words) to these functions; the shop's own content stays in
game/careers/<id>_content.py.
"""
from __future__ import annotations

from copy import deepcopy

from . import kit

DONE = ('completed', 'referred', 'cancelled')
TRAY_MAX = 60          # pieces in one tray (a class's lunch, a class list covered and labelled)
ADD_MAX = 20           # pieces one tap may add (a service's +5 / +10)
LINES = 12             # the counter log kept on a task
LEARN = 3              # the first customers of a place never hear the bell


class Shop:
    """What a counter shop tells the kit: `goods` {id: dict(name, emoji, group, price, cost, unit, start, tags,
    uses: material id | None, service: bool)}, `groups` [(id, title)], the words of its people."""

    def __init__(self, id: str, prefix: str, goods: dict, groups, who: str, wrong_cost: int = 10, floor: int = 40,
                 words: dict | None = None):
        self.id, self.prefix, self.goods, self.groups, self.who = id, prefix, goods, tuple(groups), who
        self.wrong_cost, self.floor = wrong_cost, floor
        self.words = dict(WORDS, **(words or {}))

    def item(self, k: str) -> dict:
        return self.goods[k]

    def quality(self, wrong: int) -> int:
        return max(self.floor, 100 - self.wrong_cost * wrong)


WORDS = dict(
    budget='{who}: “Con chỉ có {budget} xu thôi à.” Khay đang {bill} xu.',
    avoid='{who}: “Con dặn rồi mà, con không ăn được {tag}!” Bỏ món đó ra nhé.',
    missing='Còn thiếu: {what}.',
    extra='Khách không hỏi: {what}.',
    too_many='Lấy dư: {what}.',
    empty='Khay còn trống: chạm món trên kệ để lấy cho khách.',
    sample='Chưa lưu mẫu thức ăn trưa nay: bấm 🧪 Lưu mẫu trước khi phát phần cơm đầu tiên.',
    bell='Trống trường đã đánh, {who} chạy vội vào lớp, không kịp mua.',
    served='Giao đủ cho {who}. Thu {bill} xu.',
)
TAG_WORDS = {'peanut': 'đậu phộng', 'milk': 'sữa', 'egg': 'trứng', 'fish': 'cá', 'meat': 'đồ mặn', 'spicy': 'đồ cay'}


# ---------------------------------------------------------------- items for the inventory (SPEC inventory)
def inventory_items(shop: Shop) -> list:
    """The stocked goods (and the services' materials) as game/inventory.py items. A service itself has no stock."""
    out = []
    for k, g in shop.goods.items():
        if g.get('service'):
            continue
        out.append(dict(id=k, name=g['name'], emoji=g['emoji'], group=g['group'], unit=g['unit'], cost=g['cost'],
                        price=g['price'], start=g['start'], **({'life': g['life']} if g.get('life') else {}),
                        **({'unlock': g['unlock']} if g.get('unlock') else {})))
    return out


# ---------------------------------------------------------------- the order (pure)
def line(n: int, any_of, qty: int, say: str) -> dict:
    return dict(id=f'l{n}', any=sorted(any_of), qty=qty, say=say)


def cheapest(shop: Shop, lines: list) -> int:
    """The lowest bill that answers every line (the budget is set against it)."""
    return sum(min(shop.goods[k]['price'] for k in ln['any']) * ln['qty'] for ln in lines)


def needs(kind: str, lines: list, budget: int | None = None, avoid=(), sample: bool = False, bell: int = 0, **extra) -> dict:
    return dict(kind=kind, lines=lines, budget=budget, avoid=sorted(avoid), sample=sample, bell=bell, **extra)


# ---------------------------------------------------------------- the bill and the grade
def bill(shop: Shop, tray: dict) -> int:
    return sum(shop.goods[k]['price'] * q for k, q in tray.items())


def _names(shop: Shop, rows) -> str:
    return ', '.join(shop.goods[k]['name'][:1].lower() + shop.goods[k]['name'][1:] for k, _ in rows)   # every piece has its English (i18n: 'Khách không hỏi: $1, $2.')


def grade(shop: Shop, t: dict, who: str) -> tuple:
    """(problem key | None, the words at the counter). Checked in the order a customer would object."""
    n, tray = t['needs'], t['tray']
    if not tray:
        return 'empty', shop.words['empty']
    total = bill(shop, tray)
    if n.get('avoid'):
        bad = [k for k in tray if set(shop.goods[k].get('tags', ())) & set(n['avoid'])]
        if bad:
            tag = next(x for x in n['avoid'] if x in shop.goods[bad[0]].get('tags', ()))
            return 'avoid', shop.words['avoid'].format(who=who, tag=TAG_WORDS.get(tag, tag))
    if n.get('budget') is not None and total > n['budget']:
        return 'budget', shop.words['budget'].format(who=who, budget=n['budget'], bill=total)
    asked = {k for ln in n['lines'] for k in ln['any']}
    extra = [(k, q) for k, q in tray.items() if k not in asked]
    missing, over = [], []
    for ln in n['lines']:
        got = sum(tray.get(k, 0) for k in ln['any'])
        if got < ln['qty']:
            missing.append(f'{ln["qty"] - got} {ln["say"]}')
        elif got > ln['qty']:
            over.append(f'{got - ln["qty"]} {ln["say"]}')
    if missing:
        return 'missing', shop.words['missing'].format(what=', '.join(missing))
    if extra:
        return 'extra', shop.words['extra'].format(what=_names(shop, extra))
    if over:
        return 'too_many', shop.words['too_many'].format(what=', '.join(over))
    return None, ''


SEVERITY = {'avoid': 3, 'sample': 3, 'budget': 1, 'missing': 1, 'extra': 1, 'too_many': 1, 'empty': 0}


# ---------------------------------------------------------------- actions
def materials(shop: Shop, tray: dict) -> dict:
    """What the tray takes off the shelves: the goods themselves, and each service's material."""
    use = {}
    for k, q in tray.items():
        g = shop.goods[k]
        src = g.get('uses') if g.get('service') else k
        if src:
            use[src] = use.get(src, 0) + q
    return use


def add(shop: Shop, c: dict, t: dict, p: dict) -> dict:
    k = kit.one_of(p.get('item'), list(shop.goods), 'Món này không có trên quầy.')
    qty = kit.integer(p.get('qty', 1), 1, ADD_MAX)
    kit.need(t['stage'] == 'work', 'Đơn này đã giao xong.')
    kit.need(sum(t['tray'].values()) + qty <= TRAY_MAX, f'Khay chỉ chứa {TRAY_MAX} món.')
    g = shop.goods[k]
    if g.get('unlock') and kit.level(c) < g['unlock']:
        kit.need(False, f'{g["name"]} mở ở cấp {g["unlock"]}.', 'locked')
    src = g.get('uses') if g.get('service') else k
    if src:
        want = materials(shop, t['tray']).get(src, 0) + qty
        have = kit.stock(c, src)
        name = shop.goods[src]['name'].lower()
        kit.need(have >= want, f'Trên kệ chỉ còn {have} {shop.goods[src]["unit"]} {name}. Nhập thêm ở Kho nhé.' if have else
                 f'Hết {name} trên kệ. Nhập thêm ở Kho nhé.', 'out_of_stock')
    kit.start_work(t)
    t['tray'][k] = t['tray'].get(k, 0) + qty
    return dict(message=f'+{qty} {g["name"].lower()}' if qty > 1 else f'+ {g["name"]}', quiet=True)


def remove(shop: Shop, t: dict, p: dict) -> dict:
    k = kit.one_of(p.get('item'), list(t['tray']), 'Món này không có trong khay.')
    qty = kit.integer(p.get('qty', 1), 1, TRAY_MAX)
    kit.need(t['stage'] == 'work', 'Đơn này đã giao xong.')
    left = t['tray'][k] - qty
    if left > 0:
        t['tray'][k] = left
    else:
        del t['tray'][k]
    return dict(message=f'− {shop.goods[k]["name"]}', quiet=True)


def clear(t: dict) -> dict:
    kit.need(t['stage'] == 'work', 'Đơn này đã giao xong.')
    t['tray'] = {}
    return dict(message='Đã dọn khay.', quiet=True)


def serve(shop: Shop, s: dict, c: dict, t: dict, who: str, sampled: bool = True) -> tuple:
    """(finished, message): a wrong tray stays to fix (quality lower), a right one is paid and the goods leave the shelf."""
    from .. import consequences as cq
    kit.need(t['stage'] == 'work', 'Đơn này đã giao xong.')
    kit.need(t['tray'], shop.words['empty'])
    problem, words = grade(shop, t, who)
    if problem is None and t['needs'].get('sample') and not sampled:
        problem, words = 'sample', shop.words['sample']
    kit.start_work(t)
    if problem:
        if problem not in t['errors']:
            t['errors'].append(problem)
            if SEVERITY.get(problem):
                cq.slip(t, f'{shop.id}.{problem}', SEVERITY[problem], 'Phải sửa khay: ' + words[:120])
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = shop.quality(t['wrong'])
        t['lines'] = (t['lines'] + [words[:480]])[-LINES:]
        return False, words
    use = materials(shop, t['tray'])
    for src, q in use.items():   # the tray was checked as it was filled; a delivery or a waste since may have moved it
        have = kit.stock(c, src)
        kit.need(have >= q, f'Trên kệ chỉ còn {have} {shop.goods[src]["unit"]} {shop.goods[src]["name"].lower()}. Bớt khay hoặc nhập thêm ở Kho nhé.',
                 'out_of_stock')
    t['cogs'] = sum(kit.take(c, src, q) for src, q in use.items())
    t['paid'] = bill(shop, t['tray'])
    t['stage'] = 'done'
    t['lines'] = (t['lines'] + [shop.words['served'].format(who=who, bill=t['paid'])])[-LINES:]
    return True, shop.words['served'].format(who=who, bill=t['paid'])


# ---------------------------------------------------------------- the school bell
def bell_due(c: dict, t: dict) -> bool:
    """A rush customer still waiting when the bell rings (calm shifts and a place's first customers excepted)."""
    b = t['needs'].get('bell') or 0
    if not b or t['status'] in DONE or t['stage'] != 'work':
        return False
    if c['life'].get('mode') == 'calm' or c['metrics'].get('served', 0) < LEARN:
        return False
    return c['turn'] - t['created_turn'] >= b


def bell_left(c: dict, t: dict) -> int | None:
    b = t['needs'].get('bell') or 0
    if not b or c['life'].get('mode') == 'calm' or c['metrics'].get('served', 0) < LEARN:
        return None
    return max(0, b - (c['turn'] - t['created_turn']))


# ---------------------------------------------------------------- views and checks
def public_task(t: dict, shop: Shop, c: dict | None = None) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    v['bill'] = bill(shop, t['tray'])
    if not t['known']:
        v['needs'] = None
        return v
    v['needs']['lines'] = [dict(id=ln['id'], qty=ln['qty']) for ln in t['needs']['lines']]   # which goods answer a line is the player's call
    if c is not None:
        v['bell_left'] = bell_left(c, t)
    return v


def validate_task(shop: Shop, t: dict, what: str) -> None:
    tray = t.get('tray')
    kit.need(isinstance(tray, dict) and len(tray) <= len(shop.goods) and all(k in shop.goods and type(q) is int and 1 <= q <= TRAY_MAX
                                                                            for k, q in tray.items()), f'Khay {what} sai.')
    kit.need(sum(tray.values()) <= TRAY_MAX, f'Khay {what} sai.')
    kit.need(t.get('stage') in ('work', 'done'), f'Tiến trình {what} sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and len(errors) == len(set(errors)) and set(errors) <= set(SEVERITY), f'Nhật ký lỗi {what} sai.')
    wrong = kit.integer(t.get('wrong'), 0, 100000)
    kit.need(len(errors) <= wrong <= t.get('mistakes', 0) and (wrong == 0) == (not errors), 'Số lần sửa khay sai.')
    kit.need(t.get('quality') == shop.quality(wrong), f'Điểm chất lượng {what} không khớp.')
    done = t['stage'] == 'done'
    kit.need(t.get('status') != 'completed' or done, f'{what} chưa giao mà đã hoàn tất.')
    kit.need(not done or t.get('status') == 'completed', f'{what} sai trạng thái.')
    kit.need(type(t.get('paid')) is int and t['paid'] == (bill(shop, tray) if done else 0), f'Tiền {what} không khớp.')
    top = sum(shop.goods[src]['cost'] * q for src, q in materials(shop, tray).items()) * 2 + 1 if done else 0
    kit.need(type(t.get('cogs')) is int and 0 <= t['cogs'] <= top, f'Giá vốn {what} sai.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= LINES and all(isinstance(x, str) and len(x) < 500 for x in t['lines']),
             f'Nhật ký {what} sai.')
    kit.need(t['known'] or (not tray and wrong == 0), f'Chưa nghe khách mà đã lấy hàng ({what}).')


# ---------------------------------------------------------------- the shop's book (career data), shared by both shops
def today_row(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, earned=0)


def initial(**extra) -> dict:
    return dict(intro=False, today=today_row(0), closed_day=0, stats=dict(jobs=0, good=0, active_days=0, earned=0, missed=0),
                desk=kit.desk_initial(), **extra)


def book(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = today_row(c['day'])
    return d


def finish(s: dict, c: dict, d: dict, t: dict, narrative: str) -> int:
    """The tray was right: the customer pays the bill; the margin (bill − cogs) is what the quality gear counts on."""
    margin = max(0, t['paid'] - t['cogs'])
    kit.complete(s, c, t, t['paid'], narrative, bonus_base=margin)
    good = t['quality'] >= 90
    for bucket in (d['today'], d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['earned'] += margin
    return margin


def has_cert(s: dict, cert_id: str) -> bool:
    rec = ((s.get('journey') or {}).get('certificates') or {}).get(cert_id)
    return isinstance(rec, dict) and rec.get('earned_day') is not None


def cert_tip(s: dict, c: dict, t: dict, cert_id: str, reason: str) -> str:
    """🎓 The certificate's perk: 2 xu more on the order it names (certificate_content: canteen_basics, stationery_basics)."""
    if not has_cert(s, cert_id):
        return ''
    kit.money(s, c, 2, reason, t['id'], 'other_income')
    return ' 🎓 Khách trả thêm 2 xu vì bạn có chứng chỉ.'


def ring(s: dict, c: dict, shop: Shop, d: dict, who_of, line: str) -> list:
    """The bell: every rush customer still waiting goes back to class unserved (no pay, nothing leaves the shelf).
    Returns [(task id, who)]."""
    gone = []
    for t in list(c['tasks']):
        if t.get('career') == shop.id and bell_due(c, t):
            t['tray'] = {}
            kit.complete(s, c, t, 0, line, status='referred')
            d['stats']['missed'] += 1
            gone.append((t['id'], who_of(t)))
    return gone


def after(s: dict, c: dict, shop: Shop, d: dict, result: dict, scripts: list, mod_id: str | None) -> None:
    """After a counter action: a surprise between customers when today's plan says so."""
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, shop.id, desk, scripts, mod_id)
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(scripts, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def close(s: dict, c: dict, shop: Shop, d: dict, scripts: list, place: str) -> dict:
    today = d['today']
    note = kit.desk_close(s, c, shop.id, d['desk'], scripts)
    if today['day'] == c['day'] and today['good'] > 0 and d['closed_day'] != c['day']:
        d['stats']['active_days'] += 1
        d['closed_day'] = c['day']
    lines = [f'{place} phục vụ {today["jobs"]} lượt, {today["good"]} lượt đạt từ 90%, lời {today["earned"]} xu.']
    if note:
        lines.append(note)
    return dict(lines=lines, jobs=today['jobs'], clean=today['good'], earned=today['earned'])


def public_book(c: dict, shop: Shop, scripts: list, master: tuple, expert: tuple) -> dict:
    d = deepcopy(kit.data(c))
    st = d['stats']
    d['mastered'] = st['good'] >= master[0] and st['active_days'] >= master[1]
    d['expert'] = st['good'] >= expert[0] and st['active_days'] >= expert[1]
    d['desk'] = kit.desk_public(d['desk'], scripts, shop.id, c)
    return d


def validate_book(c: dict, base: dict, scripts: list, name: str) -> None:
    d = kit.data(c)
    kit.need(isinstance(d, dict) and set(d) == set(base), f'Sổ {name} sai.')
    kit.need(type(d['intro']) is bool, f'Sổ {name} sai.')
    for field in ('today', 'stats'):
        kit.need(isinstance(d[field], dict) and set(d[field]) == set(base[field]), f'Thống kê {name} sai.')
        for v in d[field].values():
            kit.integer(v, 0, 10**9)
        kit.need(d[field]['good'] <= d[field]['jobs'], 'Số lượt đạt sai.')
    kit.integer(d['closed_day'], 0, 10**9)
    kit.need(d['stats']['active_days'] <= d['stats']['good'], 'Ngày làm thực tế sai.')
    kit.desk_validate(d['desk'], scripts)


def goods_view(shop: Shop) -> list:
    """The counter as the page lays it out: every shelf, every good (price, unit, tags), in order."""
    return [dict(id=g, title=title, items=[dict(id=k, name=x['name'], emoji=x['emoji'], price=x['price'], unit=x['unit'],
                                               tags=list(x.get('tags', ())), service=bool(x.get('service')), uses=x.get('uses'))
                                          for k, x in shop.goods.items() if x['group'] == g])
            for g, title in shop.groups]


def feedback(t: dict, labels: dict) -> dict:
    """The review's criteria: right the first time, safe (allergy / the rule), on time and within the customer's money."""
    e = set(t['errors'])
    tries = t['wrong']
    gone = t['status'] == 'referred'
    crit = [dict(key='order', label=labels['order'], score=1 if gone else max(1, 5 - tries), note='Khay đúng ngay lần đầu.' if not tries else f'Sửa khay {tries} lần.'),
            dict(key='safe', label=labels['safe'], score=2 if ({'avoid', 'sample'} & e) else 5, note=labels['safe_note']),
            dict(key='speed', label='Kịp giờ', score=1 if gone else 5 if t['patience'] >= 70 else 4 if t['patience'] >= 50 else 3,
                 note='Khách phải về khi chưa mua được.' if gone else 'Giao kịp lúc.')]
    if 'budget' in e:
        crit.append(dict(key='money', label=labels['money'], score=3, note='Khay lố tiền khách mang theo.'))
    return dict(criteria=crit, cap=2 if gone else 5)
