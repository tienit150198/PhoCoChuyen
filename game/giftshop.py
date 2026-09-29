"""Tiệm quà mẹ & bé (mother_baby), from day 2 on.

Day 1 keeps the original eight gentle orders. From day 2 each order is rolled
from (day, slot) and stored once:

* occasion  - gift wrap with the card that matches the occasion (đầy tháng,
              thôi nôi, sinh nhật, Tết...), sometimes "chọn giúp một món".
* safety    - the customer asks for a toy whose box says 3+ for a baby of
              10 months: read the label and advise a safe swap (gift_advise).
* kit       - a first-time parent: ask (gift_ask) about age, worries and
              budget, then build a small kit that covers what they worry about.
* return    - a return without a receipt: read the sales book (gift_book),
              look at the tag and the item (gift_inspect), then resolve
              (refund / exchange / credit / decline) under a fair policy.
* bulk      - a baby-shower order of several items wrapped together.

Counter surprises live in c['ext']['data']['gift'] (formula date check,
counterfeit supplier, lost child, haggling, Tết rush, label inspection,
ward donation). Hidden truths use keys that start with "_" and never leave the
server before they are discovered. Only the standard library is imported at
module level so content.py can import this module.
"""
from __future__ import annotations
import copy
import datetime
import hashlib
import random

CAREER = 'mother_baby'
GEN_FROM_DAY = 2

NEW_PRODUCTS = [
    dict(id='rattle', name='Xúc xắc gỗ', category='toy', icon='rattle', color='cream', price=45, cost=20, description='Xúc xắc gỗ sồi, tiếng lách cách nhỏ.'),
    dict(id='teether', name='Vòng gặm nướu', category='toy', icon='teether', color='mint', price=40, cost=18, description='Vòng silicon mềm cho bé mọc răng.'),
    dict(id='bottle', name='Bình sữa 150ml', category='feeding', icon='bottle', color='blue', price=70, cost=34, description='Bình nhựa PP, núm ti size S.'),
    dict(id='bib', name='Yếm ăn dặm', category='feeding', icon='bib', color='rose', price=30, cost=12, description='Yếm chống thấm có túi hứng.'),
    dict(id='socks', name='Tất sơ sinh', category='clothes', icon='socks', color='cream', price=25, cost=10, description='Ba đôi tất cotton cho bé nhỏ.'),
    dict(id='book', name='Sách vải sột soạt', category='book', icon='book', color='mint', price=55, cost=25, description='Sách vải kêu sột soạt, giặt được.'),
    dict(id='blanket', name='Chăn ủ Mây', category='sleep', icon='blanket', color='blue', price=90, cost=42, description='Chăn ủ cotton mềm cho bé ngủ ngon.'),
    dict(id='lixi', name='Bao lì xì Mây', category='card', icon='envelope', color='rose', price=8, cost=3, description='Năm bao lì xì đỏ in hình mây.'),
]

# Printed on every box. Months; None = not a baby item (cards, envelopes).
LABELS = {
    'bunny': dict(age=0, use='play', label='0+ · vải mềm, mắt thêu'),
    'bear': dict(age=36, use='play', label='3+ · mắt nhựa gắn nút', warn='Mắt nhựa nhỏ: không dành cho bé dưới 3 tuổi.'),
    'cat_bag': dict(age=36, use='wear', label='3+ · dây đeo dài', warn='Dây đeo dài: không dành cho bé dưới 3 tuổi.'),
    'cloud_shirt': dict(age=6, age_max=12, use='wear', label='Cỡ M · 6–12 tháng'),
    'rose_shirt': dict(age=6, age_max=12, use='wear', label='Cỡ M · 6–12 tháng'),
    'towel': dict(age=0, use='bath', label='0+ · cotton mềm'),
    'blocks': dict(age=36, use='play', label='3+ · có chi tiết nhỏ', warn='Chi tiết nhỏ dễ nuốt: không dành cho bé dưới 3 tuổi.'),
    'card': dict(age=None, use='card', label='Thiệp viết lời chúc'),
    'rattle': dict(age=3, use='play', label='3 tháng+ · gỗ sơn gốc nước'),
    'teether': dict(age=4, use='play', label='4 tháng+ · silicon thực phẩm'),
    'bottle': dict(age=0, use='feed', label='0+ · núm ti size S'),
    'bib': dict(age=6, use='feed', label='6 tháng+ · chống thấm'),
    'socks': dict(age=0, age_max=6, use='wear', label='0–6 tháng · 3 đôi'),
    'book': dict(age=0, use='play', label='0+ · sách vải'),
    'blanket': dict(age=0, use='sleep', label='0+ · chăn ủ cotton'),
    'lixi': dict(age=None, use='card', label='5 bao lì xì'),
}
for _v in LABELS.values():
    _v.setdefault('age_max', None)
    _v.setdefault('warn', '')

USES = {'sleep': 'Giấc ngủ', 'bath': 'Tắm & giữ ấm', 'feed': 'Ăn uống', 'play': 'Chơi & giác quan', 'wear': 'Mặc', 'card': 'Thiệp & lì xì'}
TAGS = [dict(id='born', text='Mừng bé chào đời'), dict(id='moon', text='Mừng đầy tháng'), dict(id='year', text='Mừng thôi nôi'),
        dict(id='bday', text='Chúc mừng sinh nhật'), dict(id='tet', text='Chúc mừng năm mới'), dict(id='thanks', text='Lời cảm ơn')]
TAG_IDS = [x['id'] for x in TAGS]
TOPICS = ('age', 'need', 'budget')
RESOLUTIONS = ('refund', 'exchange', 'credit', 'decline')
PAPER_NAMES = {'cream': 'kem ấm', 'blue': 'xanh trời', 'rose': 'hồng phấn', 'mint': 'xanh lá', 'red': 'đỏ Tết'}
PLAIN_PAPERS = ('cream', 'blue', 'rose', 'mint')

MODS = [
    dict(id='normal', title='Ngày thường ở tiệm', emoji='🌤️', text='Khách ghé lai rai, hợp để sắp lại kệ.'),
    dict(id='weekend', title='Cuối tuần gia đình', emoji='👨‍👩‍👧', text='Nhiều người đi mừng đầy tháng, thôi nôi: để ý thiệp đúng dịp.', min_day=2),
    dict(id='payday', title='Ngày lương về', emoji='💰', text='Khách rộng tay hơn, hay mua món giá cao và xin bớt giá.', min_day=2),
    dict(id='rain', title='Mưa rả rích', emoji='🌧️', text='Khách ít nhưng hỏi kỹ. Bố mẹ lần đầu hay ghé hỏi han.', min_day=2),
    dict(id='fair', title='Hội chợ mẹ & bé đầu phố', emoji='🎪', text='Đơn tiệc nhiều, người chào hàng lạ cũng nhiều. Soi tem kỹ nhé.', min_day=3),
    dict(id='tet', title='Tết sắp về', emoji='🧧', text='Ai cũng muốn giấy đỏ và thiệp chúc năm mới. Quầy đông hơn thường ngày.', min_day=4),
]
MOD_INDEX = {m['id']: m for m in MODS}

GUESTS = {
    'lan': dict(id='lan', name='Cô Lan', me='cô', you='cháu', emoji='👩‍🦳'),
    'sau': dict(id='sau', name='Bà Sáu', me='bà', you='cháu', emoji='👵'),
    'hung': dict(id='hung', name='Chú Hùng', me='chú', you='cháu', emoji='👨'),
    'khang': dict(id='khang', name='Anh Khang', me='mình', you='bạn', emoji='👨‍🍼'),
    'thao': dict(id='thao', name='Chị Thảo', me='mình', you='bạn', emoji='🤱'),
    'vy': dict(id='vy', name='Vy', me='mình', you='bạn', emoji='👩‍🎓'),
    'quan': dict(id='quan', name='Anh Quân', me='mình', you='bạn', emoji='🧔'),
    'nga': dict(id='nga', name='Chị Nga', me='mình', you='bạn', emoji='👩'),
}
KIND_GUESTS = {'simple': ('vy', 'quan', 'nga', 'lan'), 'occasion': ('lan', 'vy', 'nga', 'sau', 'quan'), 'safety': ('sau', 'lan', 'hung'),
               'kit': ('khang', 'thao'), 'return': ('quan', 'vy', 'hung', 'nga')}

OCCASIONS = {
    'born': dict(age=0, line='Em gái {me} vừa sinh bé đầu lòng hôm qua.'),
    'moon': dict(age=1, line='{Me} đi mừng đầy tháng cháu.'),
    'year': dict(age=12, line='Cuối tuần bé nhà hàng xóm làm thôi nôi.'),
    'bday': dict(age=36, line='Bé Bin nhà bạn {me} tròn ba tuổi.'),
    'tet': dict(age=None, line='{Me} mua quà Tết cho mấy đứa cháu.'),
    'thanks': dict(age=None, line='{Me} muốn gửi quà cảm ơn cô hộ sinh đã chăm mẹ con em gái {me}.'),
}
NEED_TEXT = {
    'sleep': 'Đêm bé hay giật mình, quấn khăn mỏng cứ tuột ra.',
    'bath': 'Tắm cho bé mà tay mình run, sợ bé bị lạnh.',
    'feed': 'Bé bú bình mà nhà chưa có cái bình nào cho ra hồn.',
    'play': 'Lúc bé thức mình không biết cho bé nhìn, nghe gì.',
    'wear': 'Chân tay bé lúc nào sờ cũng lạnh.',
}
BULK_SETS = [dict(towel=3, card=3), dict(socks=3, card=3, blanket=1), dict(bib=2, teether=2, card=4),
             dict(book=2, rattle=2, card=4), dict(towel=2, socks=2, card=4)]


def _e():
    from . import engine
    return engine


def _catalog() -> dict:
    from .content import PRODUCT_INDEX
    return PRODUCT_INDEX


def _price_of(pid: str) -> int:
    from .content import PRODUCT_INDEX
    return PRODUCT_INDEX[pid]['price']


def _base_products() -> dict:
    """Name/price lookup that does not need content.py (it may still be loading)."""
    from .content import PRODUCT_INDEX
    return PRODUCT_INDEX


def rng(*parts) -> random.Random:
    seed = int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:12], 16)
    return random.Random(seed)


def suits(pid: str, months) -> bool:
    lab = LABELS[pid]
    if lab['age'] is None or months is None:
        return True
    return lab['age'] <= months and (lab['age_max'] is None or months <= lab['age_max'])


def date_text(day: int) -> str:
    d = datetime.date(2025, 3, 1) + datetime.timedelta(days=day - 1)
    return f'{d.day:02d}/{d.month:02d}'


def age_text(months) -> str:
    if months is None:
        return ''
    if months == 0:
        return 'mới chào đời'
    if months == 1:
        return 'tròn một tháng'
    if months < 12:
        return f'{months} tháng'
    if months == 12:
        return 'tròn một tuổi'
    if months % 12 == 0:
        return f'{months // 12} tuổi'
    return f'{months} tháng'


# ---------------------------------------------------------------- day facts
def roll_mod(day: int) -> str:
    if day < GEN_FROM_DAY:
        return 'normal'
    pool = [m['id'] for m in MODS if m.get('min_day', 1) <= day]
    weights = [3 if m == 'normal' else 2 for m in pool]
    return rng(CAREER, 'mod', day).choices(pool, weights)[0]


def kind_for(day: int, slot: int, mod: str) -> str:
    fixed = {(2, 0): 'occasion', (2, 1): 'safety', (3, 0): 'kit', (3, 1): 'return', (4, 0): 'bulk'}
    if (day, slot) in fixed:
        return fixed[(day, slot)]
    w = dict(simple=3, occasion=3, safety=2)
    if day >= 3:
        w.update(kit=2, ret=2)
    if day >= 4:
        w['bulk'] = 1
    if mod == 'weekend':
        w['occasion'] += 3
    if mod == 'tet':
        w['occasion'] += 4
    if mod == 'rain' and 'kit' in w:
        w['kit'] += 3
    if mod == 'fair' and 'bulk' in w:
        w['bulk'] += 3
    if mod == 'payday' and 'bulk' in w:
        w['bulk'] += 1
    keys = list(w)
    k = rng(CAREER, 'kind', day, slot).choices(keys, [w[x] for x in keys])[0]
    return 'return' if k == 'ret' else k


def _budget(amount: int, mod: str) -> int:
    return int(round(amount * 1.2)) if mod == 'payday' else amount


def _paper(r: random.Random, mod: str) -> str:
    return 'red' if mod == 'tet' and r.random() < 0.7 else r.choice(PLAIN_PAPERS)


def _hello(g: dict) -> str:
    return 'Cháu ơi,' if g['you'] == 'cháu' else 'Chào bạn,'


def _fill(text: str, g: dict) -> str:
    return text.replace('{Me}', g['me'].capitalize()).replace('{me}', g['me']).replace('{you}', g['you'])


def make_fields(day: int, slot: int) -> dict:
    """Everything fixed about an order, from (day, slot) only (engine re-checks it)."""
    names = _base_products()
    mod = roll_mod(day)
    kind = kind_for(day, slot, mod)
    r = rng(CAREER, 'task', day, slot)
    gift = dict(mod=mod, guest=None, age=None, tag=None, occasion=None, pick=None, items=None)
    npc = f'{CAREER}_npc_{(slot % 3) + 1:02d}'
    out = dict(gen=2, gift_kind=kind, basket={}, pack=None, checked=False, gs=dict(swap=None, asked=[], seen=[], resolution=None, discount=0))
    if kind == 'bulk':
        items = dict(r.choice(BULK_SETS))
        first = next(iter(items))
        total = sum(names[k]['price'] * q for k, q in items.items())
        budget = _budget(total + r.choice([10, 20]), mod)
        paper = _paper(r, mod)
        gift.update(items=items, tag='born')
        out.update(npc=f'{CAREER}_npc_03', title='Tiệc mừng em bé của Mai',
                   opening='Cuối tuần mình tổ chức tiệc mừng em bé cho bạn thân, muốn đặt quà nhỏ cho khách mời.',
                   needs=dict(product=first, qty=items[first], budget=budget, paper=paper, gift=True))
        out['gift'] = gift
        return out
    g = GUESTS[r.choice(KIND_GUESTS[kind])]
    gift['guest'] = dict(g)
    hello = _hello(g)
    if kind == 'simple':
        pool = [k for k in names if k not in ('card', 'lixi')] + (['lixi', 'lixi'] if mod == 'tet' else [])
        pid = r.choice(pool)
        qty = r.choice([1, 2]) if pid in ('towel', 'socks', 'bib', 'lixi') else 1
        budget = _budget(names[pid]['price'] * qty + r.choice([0, 10, 20, 30]), mod)
        paper = _paper(r, mod)
        wrap = r.random() < 0.6
        out.update(title=f"{g['name']} tìm {names[pid]['name']}", opening=f"{hello} {g['me']} tìm {names[pid]['name']}.",
                   needs=dict(product=pid, qty=qty, budget=budget, paper=paper, gift=wrap))
    elif kind == 'occasion':
        pool = ['born', 'moon', 'year', 'bday', 'thanks'] + (['moon', 'year'] if mod == 'weekend' else []) + (['tet'] * 4 if mod == 'tet' else [])
        occ = r.choice(pool)
        age = OCCASIONS[occ]['age']
        if occ == 'thanks':
            options = ['towel', 'blanket', 'book', 'bunny']
        elif occ == 'tet':
            options = ['lixi', 'bunny', 'book', 'rattle', 'blanket']
        else:
            options = [k for k in names if k not in ('card', 'lixi') and suits(k, age)]
        pick = r.choice(['named', 'open'])
        pid = r.choice(options)
        if pick == 'open':
            cheapest = min(names[k]['price'] for k in options)
            budget = _budget(max(cheapest + 20, r.choice([80, 100, 120])), mod)
        else:
            budget = _budget(names[pid]['price'] + r.choice([10, 20, 30]), mod)
        paper = 'red' if occ == 'tet' else r.choice(PLAIN_PAPERS)
        gift.update(age=age, tag=occ, occasion=occ, pick=pick, options=sorted(options) if pick == 'open' else None)
        line = _fill(OCCASIONS[occ]['line'], g)
        tail = f" Lấy giúp {g['me']} {names[pid]['name']} nhé." if pick == 'named' else f" {g['you'].capitalize()} chọn giúp {g['me']} một món thật hợp nhé."
        title = {'born': 'Quà mừng bé chào đời', 'moon': 'Quà mừng đầy tháng', 'year': 'Quà thôi nôi', 'bday': 'Quà sinh nhật bé Bin',
                 'tet': 'Quà Tết cho các cháu', 'thanks': 'Quà cảm ơn cô hộ sinh'}[occ]
        out.update(title=f"{title} · {g['name']}", opening=f'{hello} {line}{tail}',
                   needs=dict(product=pid, qty=1, budget=budget, paper=paper, gift=True))
    elif kind == 'safety':
        age = r.choice([8, 10, 14, 18])
        pid = r.choice(['blocks', 'bear', 'cat_bag'])
        budget = _budget(names[pid]['price'] + 20, mod)
        paper = _paper(r, mod)
        gift.update(age=age)
        who = {'bà': 'cháu nội', 'cô': 'cháu ngoại', 'chú': 'thằng cu nhà chú'}.get(g['me'], 'bé nhà mình')
        out.update(title=f"{g['name']} chọn quà cho {who}", opening=f"{hello} {g['me']} lấy {names[pid]['name']} cho {who} nhé.",
                   needs=dict(product=pid, qty=1, budget=budget, paper=paper, gift=r.random() < 0.7))
    elif kind == 'kit':
        weeks = r.choice([2, 3, 5, 6, 8, 10])
        months = weeks // 4
        pool = ['sleep', 'bath', 'feed', 'play', 'wear']
        wants = sorted(r.sample(pool, 2))
        cheapest = sum(min(names[k]['price'] for k in LABELS if LABELS[k]['use'] == w and suits(k, months)) for w in wants)
        budget = _budget(cheapest + r.choice([30, 50, 70]), mod)
        first = min((k for k in LABELS if LABELS[k]['use'] == wants[0] and suits(k, months)), key=lambda k: names[k]['price'])
        gift.update(age=months, kit=dict(weeks=weeks, wants=wants, budget=budget))
        out.update(title=f"Bố mẹ lần đầu · {g['name']}", opening=f"{hello} nhà mình vừa đón bé đầu lòng, mình rối quá, chẳng biết mua gì…",
                   needs=dict(product=first, qty=1, budget=budget, paper='blue', gift=False))
    else:  # return
        pid = r.choice(['cloud_shirt', 'rose_shirt', 'bear', 'bunny', 'socks', 'bottle', 'blocks'])
        case = r.choices(['found', 'nofind', 'defect', 'worn', 'other'], [25, 20, 20, 20, 15])[0]
        offset = r.choice([1, 2, 3]) if day > 3 else r.choice([1, 2])
        said = max(1, day - offset)
        found = case in ('found', 'defect', 'worn') and (case != 'worn' or r.random() < 0.6)
        tag = 'other' if case == 'other' else 'ours'
        cond = {'defect': 'defect', 'worn': 'worn'}.get(case, 'new')
        gift.update(ret=dict(item=pid, said=said, _tag=tag, _cond=cond, _found=found, book=_book(day, said, pid, found, r)))
        out.update(title=f"{g['name']} muốn đổi trả", opening=f"{hello} {g['me']} muốn đổi món này… mà {g['me']} lỡ làm mất hóa đơn rồi.",
                   needs=dict(product=pid, qty=1, budget=names[pid]['price'], paper='cream', gift=False))
    out['npc'] = npc
    out['gift'] = gift
    return out


def _book(day: int, said: int, item: str, found: bool, r: random.Random) -> list:
    names = _base_products()
    lines = []
    first = max(1, day - 3)
    others = [k for k in names if k != item and k != 'lixi']
    for d in range(first, day):
        for _ in range(r.choice([1, 2])):
            k = r.choice(others)
            lines.append(dict(day=d, item=k, qty=1, pay=r.choice(['tiền mặt', 'chuyển khoản'])))
    if found:
        lines.append(dict(day=said, item=item, qty=1, pay=r.choice(['tiền mặt', 'chuyển khoản'])))
    # A decoy: the same item sold on another day, so reading the date matters.
    decoy = [d for d in range(first, day) if d != said]
    if decoy and r.random() < 0.6:
        lines.append(dict(day=r.choice(decoy), item=item, qty=1, pay='tiền mặt'))
    lines.sort(key=lambda x: (x['day'], x['item']))
    for x in lines:
        x['price'] = names[x['item']]['price']
        x['date'] = date_text(x['day'])
    return lines


# ---------------------------------------------------------------- texts
def guest(t: dict) -> dict:
    g = (t.get('gift') or {}).get('guest')
    if g:
        return g
    from .content import NPC_INDEX
    name = NPC_INDEX[t['npc']]['display_name']
    return dict(id=t['npc'], name=name, me='mình', you='bạn', emoji='🙂')


def low(name: str) -> str:
    return name[:1].lower() + name[1:]


def paper_name(pid: str) -> str:
    return PAPER_NAMES.get(pid, pid)


def request_text(c, t: dict) -> str:
    names = _base_products()
    g = guest(t)
    n = t['needs']
    gift = t['gift']
    kind = t['gift_kind']
    Me = g['me'].capitalize()
    wrap = f"gói giấy {paper_name(n['paper'])}" if n['gift'] else 'không cần gói quà'
    if kind == 'bulk':
        lst = ', '.join(f"{q} × {names[k]['name']}" for k, q in gift['items'].items())
        return f"Mình cần {lst}. Gói chung giấy {paper_name(n['paper'])}, kèm thiệp mừng em bé. Tối đa {n['budget']} xu nhé."
    if kind == 'simple':
        return f"{Me} cần {n['qty']} × {names[n['product']]['name']}, tối đa {n['budget']} xu, {wrap} nhé."
    if kind == 'occasion':
        who = f"Bé {age_text(gift['age'])}. " if gift['age'] is not None else ''
        if gift['pick'] == 'named':
            return f"{who}{Me} lấy 1 × {names[n['product']]['name']}, tối đa {n['budget']} xu, {wrap}, kèm thiệp đúng dịp nhé."
        if gift['age'] is None:
            # No baby age to read from the labels: the guest names what would please.
            ideas = ', '.join(low(names[k]['name']) for k in gift['options'])
            return f"{Me} gửi tối đa {n['budget']} xu: chọn giúp một món trong mấy thứ này nhé: {ideas}. {wrap.capitalize()}, kèm thiệp đúng dịp."
        return f"{who}{Me} gửi tối đa {n['budget']} xu: chọn giúp một món thật hợp, {wrap}, kèm thiệp đúng dịp nhé."
    if kind == 'safety':
        return f"Bé nhà {g['me']} được {gift['age']} tháng rồi. {Me} lấy 1 × {names[n['product']]['name']}, tối đa {n['budget']} xu, {wrap} nhé."
    if kind == 'kit':
        return f"Bé nhà mình mới được ít tuần. {g['you'].capitalize()} hỏi giúp mình vài điều rồi chọn đồ cho bé nhé."
    ret = gift['ret']
    when = {1: 'hôm qua', 2: 'hôm kia'}.get(t['day'] - ret['said'], 'mấy hôm trước')
    why = 'bé mặc không vừa' if LABELS[ret['item']]['use'] == 'wear' else 'bé không chịu dùng' if ret['item'] == 'bottle' else 'bé không thích'
    return f"{Me} mua {names[ret['item']]['name']} ở tiệm {when} (ngày {date_text(ret['said'])}), {why}. Không còn hóa đơn, {g['you']} đổi hoặc trả giúp {g['me']} được không?"


def answer(t: dict, topic: str) -> str:
    k = t['gift']['kit']
    if topic == 'age':
        return f"Bé được {k['weeks']} tuần rồi."
    if topic == 'need':
        return ' '.join(NEED_TEXT[w] for w in k['wants'])
    return f"Mình mang theo khoảng {k['budget']} xu thôi."


def inspect_text(t: dict, part: str) -> str:
    names = _base_products()
    ret = t['gift']['ret']
    item = ret['item']
    toy = LABELS[item]['use'] != 'wear'
    if part == 'tag':
        return f"Tem giấy của tiệm, mã “{item}” còn nguyên." if ret['_tag'] == 'ours' else 'Tem của một cửa hàng khác, không phải tem của tiệm mình.'
    return {'new': 'Còn mới: bao bì, nếp gấp nguyên vẹn, chưa qua sử dụng.',
            'worn': ('Đã chơi nhiều: lông xù, có vết bẩn đã giặt.' if toy else 'Đã mặc và giặt nhiều lần: vải sờn cổ, bạc màu.'),
            'defect': ('Mắt khâu lỏng ngay từ xưởng, chưa qua sử dụng.' if toy else 'Đường may bung ngay từ xưởng, chưa qua sử dụng.')}[ret['_cond']] + f" ({names[item]['name']})"


# ---------------------------------------------------------------- state
def fresh() -> dict:
    return dict(v=1, day=0, mod='normal', event=None, events_today=0, last_turn=-99, today_kinds=[], ev_seq=0, ev_history=[],
                fake=0, expired_left=0, followups=[], stats=dict(advised=0, kits=0, returns=0, bulk=0, events=0),
                today=dict(sold=0, advised=0, returns=0, events=0, fines=0), history=[])


def view(c: dict) -> dict:
    raw = ((c.get('ext') or {}).get('data') or {}).get('gift')
    out = fresh()
    if isinstance(raw, dict):
        out.update(copy.deepcopy(raw))
    return out


def state(c: dict) -> dict:
    d = c['ext']['data']
    b = d.get('gift')
    if not isinstance(b, dict):
        b = d['gift'] = fresh()
    for k, v in fresh().items():
        b.setdefault(k, copy.deepcopy(v))
    return b


def modifier(c: dict) -> dict:
    return MOD_INDEX[roll_mod(c['day'])]


def upgrade(c: dict) -> None:
    """Old saves: new shelf items join with a small starter stock."""
    from .content import PRODUCT_INDEX
    stock = c.get('stock')
    if isinstance(stock, dict) and stock:
        for k in PRODUCT_INDEX:
            stock.setdefault(k, 4)


def _open(t: dict) -> bool:
    return t['status'] not in ('completed', 'referred', 'cancelled')


# ---------------------------------------------------------------- shelf rules
def target(t: dict) -> dict | None:
    """The exact basket this order needs, or None when several baskets are fine."""
    kind = t['gift_kind']
    n = t['needs']
    if kind == 'bulk':
        return dict(t['gift']['items'])
    if kind in ('kit', 'return'):
        return None
    if kind == 'occasion' and t['gift']['pick'] == 'open':
        return None
    if kind == 'safety' and t['gs'].get('swap'):
        return {t['gs']['swap']: n['qty']}
    return {n['product']: n['qty']}


def basket_cap(t: dict) -> int:
    return 12 if t.get('gift_kind') == 'bulk' else 6


def pick_mistake(c: dict, t: dict, item: str) -> int:
    e = _e()
    kind = t['gift_kind']
    e.need(kind != 'return', 'Đơn này là đổi trả: không lấy thêm hàng, hãy xử lý ở bàn đổi trả.')
    age = t['gift'].get('age')
    if age is not None and LABELS[item]['use'] != 'card' and not suits(item, age):
        return 1
    want = target(t)
    if want is not None:
        return 1 if t['basket'].get(item, 0) > want.get(item, 0) else 0
    if kind == 'occasion':
        return 0 if item in (t['gift'].get('options') or []) else 1
    return 0


def _total(c: dict, basket: dict) -> int:
    from . import experiences as life
    names = _catalog()
    return sum(life.price(c, k, names[k]['price']) * v for k, v in basket.items())


def ensure(t: dict, c: dict, pack_check: bool = True) -> None:
    """What the counter can refuse: nothing asked yet, an empty basket, a return at the
    wrong desk, stock that is not there. A basket that does not match the order CAN be
    handed over (the customer notices at the counter: see judge()); the check step
    does not tell right from wrong."""
    e = _e()
    need = e.need
    need(t['known'], 'Hỏi nhu cầu khách trước để biết ngân sách và món cần tìm.')
    kind = t['gift_kind']
    need(kind != 'return', 'Đơn này là đổi trả: xem sổ bán hàng, soi tem và chọn cách xử lý ở bàn đổi trả nhé.')
    basket = t['basket']
    need(basket, 'Giỏ còn trống. Chọn món trên kệ trước nhé.')
    for k, v in basket.items():
        need(c['stock'].get(k, 0) >= v, 'Hàng trong kho không đủ; cần đặt thêm và kiểm nhận.')
    if pack_check:
        # Settled at the hand-off (shop_deliver runs only on a checked order); before that
        # nothing is kept, so the check never gives the answer away.
        t['slips'] = []
        if t['checked']:
            for row in judge(c, t):
                from . import consequences as cq
                cq.slip(t, *row)
            if t['slips'] and t['mistakes'] == 0:
                t['mistakes'] = 1
        else:
            t.pop('slips', None)


def _age_phrase(months) -> str:
    return 'mới chào đời' if months == 0 else 'mới ' + age_text(months)


def judge(c: dict, t: dict) -> list:
    """What the customer notices at the counter: (code, sev, text, note, safety) rows."""
    names = _catalog()
    n = t['needs']
    kind = t['gift_kind']
    g = guest(t)
    me = g['me']
    Me = me.capitalize()
    basket = t['basket']
    age = t['gift'].get('age')
    out = []
    unsafe = [k for k in basket if age is not None and LABELS[k]['use'] != 'card' and not suits(k, age)]
    if unsafe:
        k = unsafe[0]
        out.append(('age_unsafe', 3, f"Bé {_age_phrase(age)} mà tiệm vẫn bán {low(names[k]['name'])} ghi “{LABELS[k]['label']}”, chẳng ai nhắc một câu.",
                    'bán món không hợp tuổi bé', True))
    want = target(t)
    if want is not None:
        missing = {k: q - basket.get(k, 0) for k, q in want.items() if basket.get(k, 0) < q}
        extra = {k: q - want.get(k, 0) for k, q in basket.items() if q > want.get(k, 0)}
        if kind == 'bulk':
            if missing:
                k = next(iter(missing))
                out.append(('bulk_short', 2, f"Đặt {want[k]} × {names[k]['name']} cho tiệc mà giao thiếu {missing[k]}.", 'giao thiếu món đặt tiệc', False))
            if extra:
                k = next(iter(extra))
                out.append(('extra', 1, f"Giỏ có thêm {low(names[k]['name'])} {me} không đặt, lại phải trả thêm tiền.", 'tính thêm món khách không đặt', False))
        else:
            main = next(iter(want))
            got = basket.get(main, 0)
            others = [k for k in basket if k != main and k not in unsafe]
            if not got:
                k = others[0] if others else next(iter(basket))
                if LABELS[k]['use'] == LABELS[main]['use'] and LABELS[k]['use'] == 'wear':
                    out.append(('variant', 2, f"Dặn lấy {low(names[main]['name'])} mà giao {low(names[k]['name'])}, không phải cái {me} chọn.", 'giao nhầm mẫu', False))
                elif k not in unsafe:
                    out.append(('wrong_item', 3, f"Dặn lấy {low(names[main]['name'])} mà giao {low(names[k]['name'])}, sai hẳn món.", 'giao sai món', False))
            else:
                if got < want[main]:
                    out.append(('qty_short', 2, f"Dặn {want[main]} × {names[main]['name']} mà chỉ giao {got}.", 'giao thiếu số lượng', False))
                elif got > want[main]:
                    out.append(('qty_extra', 1, f"Chỉ cần {want[main]} × {names[main]['name']} mà bị tính thành {got}.", 'tính dư số lượng', False))
                if others:
                    out.append(('extra', 1, f"Giỏ có thêm {low(names[others[0]]['name'])} {me} không hỏi mua, lại phải trả thêm tiền.", 'tính thêm món khách không hỏi', False))
    elif kind == 'occasion':
        items = [k for k in basket if k not in unsafe]
        wrong = [k for k in items if k not in (t['gift'].get('options') or [])]
        if wrong:
            out.append(('occasion', 2, f"Nhờ chọn giúp một món hợp dịp mà lại giao {low(names[wrong[0]]['name'])}, đem tặng thấy không hợp.", 'chọn quà không hợp dịp', False))
        if sum(basket.values()) > 1:
            out.append(('extra', 1, f"{Me} chỉ cần một món quà mà giỏ bị tính thành {sum(basket.values())} món.", 'bán thừa món', False))
    elif kind == 'kit':
        uses = {LABELS[k]['use'] for k in basket if k not in unsafe}
        lack = [w for w in t['gift']['kit']['wants'] if w not in uses]
        if lack:
            out.append(('kit_missing', 2, f"{Me} lo nhất chuyện {USES[lack[0]].lower()} của bé mà bộ đồ chẳng có món nào cho việc đó.", 'bộ đồ thiếu điều khách lo', False))
        if len(basket) > 4 or sum(basket.values()) > 6:
            out.append(('oversell', 1, 'Bố mẹ lần đầu hỏi han mà bị bán thừa cả đống món chưa cần tới.', 'bán thừa cho bố mẹ lần đầu', False))
    total = _total(c, basket)
    if total > n['budget']:
        over = total - n['budget']
        out.append(('budget', 1 if over <= max(10, n['budget'] // 10) else 2, f"Dặn tối đa {n['budget']} xu mà tính {total} xu, vượt túi {me} rồi.", 'vượt ngân sách khách dặn', False))
    if n['gift']:
        pack = t['pack']
        if not pack:
            out.append(('no_wrap', 2, f"Mua làm quà mà giao không gói, {me} phải tự đi gói.", 'quên gói quà', False))
        else:
            if pack['paper'] != n['paper']:
                out.append(('paper', 1, f"Chọn giấy {paper_name(n['paper'])} mà lại gói giấy {paper_name(pack['paper'])}.", 'gói sai màu giấy', False))
            tag = t['gift'].get('tag')
            if tag and pack.get('tag') != tag:
                text = {x['id']: x['text'] for x in TAGS}
                got = text.get(pack.get('tag'))
                out.append(('card', 2, f"Thiệp phải là “{text[tag]}” mà lại ghi “{got}”, đưa ra ngại lắm." if got else f"Thiệp phải là “{text[tag]}” mà để trống, đưa ra ngại lắm.",
                            'thiệp sai dịp', False))
    return out


def on_pack(t: dict, p: dict) -> None:
    e = _e()
    tag = p.get('tag')
    if tag is None:
        return
    e.need(tag in TAG_IDS, 'Lời chúc trên thiệp không hợp lệ.')
    t['pack']['tag'] = tag
    want = t['gift'].get('tag')
    if want and tag != want:
        t['mistakes'] += 1


# ---------------------------------------------------------------- actions
def handle(s: dict, c: dict, action: str, p: dict) -> dict:
    e = _e()
    need = e.need
    name = action[5:]
    b = state(c)
    if name == 'event_ok':
        ev = b.get('event')
        need(ev and ev['stage'] == 'done', 'Không có kết quả nào đang chờ xác nhận.')
        b['event'] = None
        return dict(message='Tiệm trở lại nhịp bình thường.')
    need(c['open'], 'Mở cửa tiệm trước nhé.')
    if name == 'event':
        r = _answer(s, c, b, p)
    else:
        t = e.current_task(c, p.get('task'))
        need(t['career'] == CAREER and t.get('gen'), 'Đơn này chưa có bàn tư vấn.')
        need(t['known'], 'Hỏi nhu cầu khách trước đã nhé.')
        r = {'advise': _advise, 'ask': _ask, 'book': _open_book, 'inspect': _inspect, 'resolve': _resolve_return}.get(name, _bad)(s, c, b, t, p)
    if not r.pop('_free', False):
        c['turn'] += 1
    return r


def _bad(s, c, b, t, p):
    raise _e().GameError('Thao tác ở tiệm không hợp lệ.')


def _advise(s, c, b, t, p):
    e = _e()
    need = e.need
    names = _catalog()
    need(t['gift_kind'] == 'safety', 'Khách này đã chọn đúng món cần mua.')
    need(not t['gs'].get('swap'), 'Khách đã đồng ý đổi món rồi.')
    item = p.get('item')
    need(item in names, 'Không có món này trên kệ.')
    age = t['gift']['age']
    need(item != t['needs']['product'], 'Đây chính là món khách đang hỏi.')
    need(LABELS[item]['use'] != 'card', 'Chọn một món đồ chơi hay đồ dùng cho bé nhé.')
    need(suits(item, age), f"Hộp này ghi “{LABELS[item]['label']}”: cũng chưa hợp với bé {age} tháng.")
    need(_total(c, {item: t['needs']['qty']}) <= t['needs']['budget'], 'Món này vượt ngân sách của khách.')
    need(e.available(c, item) >= t['needs']['qty'], 'Món này đang hết hàng trên kệ.')
    g = guest(t)
    t['gs']['swap'] = item
    t['basket'] = {}
    t['pack'] = None
    t['checked'] = False
    c['xp'] += 5
    b['stats']['advised'] += 1
    b['today']['advised'] += 1
    e.metric(c, 'advised')
    orig = names[t['needs']['product']]['name']
    e.remember(s, c, t['npc'], f"Bạn chỉ nhãn “{LABELS[t['needs']['product']]['label']}” trên hộp {orig} và gợi ý {names[item]['name']} cho bé {age} tháng.", t['id'])
    return dict(message=f"{g['name']} đọc kỹ nhãn trên hộp rồi gật đầu: “Vậy lấy {names[item]['name']} cho an toàn nhé. May mà {g['you']} để ý!”", celebrate=True)


def _ask(s, c, b, t, p):
    e = _e()
    need = e.need
    need(t['gift_kind'] == 'kit', 'Khách này đã nói rõ điều cần mua.')
    topic = p.get('topic')
    need(topic in TOPICS, 'Câu hỏi không hợp lệ.')
    need(topic not in t['gs']['asked'], 'Khách đã trả lời câu này rồi.')
    t['gs']['asked'].append(topic)
    e.log(s, c, 'fact', answer(t, topic), t['npc'], t['id'])
    return dict(message=f"{guest(t)['name']}: “{answer(t, topic)}”")


def _open_book(s, c, b, t, p):
    e = _e()
    e.need(t['gift_kind'] == 'return', 'Đơn này không cần tra sổ bán hàng.')
    e.need('book' not in t['gs']['seen'], 'Sổ bán hàng đang mở sẵn.')
    t['gs']['seen'].append('book')
    return dict(message='Đã mở sổ bán hàng mấy ngày gần đây. Dò đúng ngày và đúng món khách nói nhé.')


def _inspect(s, c, b, t, p):
    e = _e()
    e.need(t['gift_kind'] == 'return', 'Đơn này không có món trả lại để xem.')
    part = p.get('part')
    e.need(part in ('tag', 'item'), 'Chọn xem tem hoặc xem món hàng.')
    e.need(part not in t['gs']['seen'], 'Bạn đã xem phần này rồi.')
    t['gs']['seen'].append(part)
    return dict(message=inspect_text(t, part))


def return_verdict(t: dict, choice: str) -> int:
    """Mistakes for a return decision (0 = fair to both the shop and the customer)."""
    ret = t['gift']['ret']
    if ret['_tag'] == 'other':
        table = dict(decline=0, credit=1, exchange=2, refund=2)
    elif ret['_cond'] == 'defect':
        table = dict(refund=0, exchange=0, credit=1, decline=2)
    elif ret['_cond'] == 'worn':
        table = dict(decline=0, credit=0, exchange=1, refund=2)
    elif ret['_found']:
        table = dict(refund=0, exchange=0, credit=0, decline=1)
    else:
        table = dict(exchange=0, credit=0, refund=1, decline=1)
    blind = 0 if {'tag', 'item'} <= set(t['gs']['seen']) else 1
    return table[choice] + blind


def truth_text(t: dict) -> str:
    names = _base_products()
    ret = t['gift']['ret']
    item = names[ret['item']]['name']
    if ret['_tag'] == 'other':
        return f'{item} mang tem cửa hàng khác: tiệm không nhận đổi trả món không bán ra.'
    if ret['_cond'] == 'defect':
        return f'{item} lỗi từ xưởng: hoàn tiền hoặc đổi món mới là công bằng.'
    if ret['_cond'] == 'worn':
        return f'{item} đã qua sử dụng: từ chối nhẹ nhàng hoặc tặng phiếu mua hàng là hợp lý.'
    if ret['_found']:
        return f'Sổ có ghi bán {item} đúng ngày khách nói: hoàn tiền, đổi hay phiếu mua hàng đều ổn.'
    return f'Sổ không có dòng bán {item} đúng ngày khách nói (có thể là quà người khác tặng): đổi món hoặc phiếu mua hàng, không hoàn tiền mặt.'


RETURN_SLIPS = {
    ('defect', 'decline'): ('return_defect', 2, '{Item} lỗi từ xưởng mà tiệm từ chối đổi trả, {me} thấy không công bằng.', 'từ chối đổi món lỗi'),
    ('defect', 'credit'): ('return_defect', 1, '{Item} lỗi từ xưởng mà chỉ được phiếu mua hàng, không được đổi hay hoàn tiền.', 'món lỗi chỉ được phiếu'),
    ('found', 'decline'): ('return_refused', 1, 'Sổ tiệm có ghi bán {item} đúng ngày mà vẫn bị từ chối đổi.', 'từ chối đổi món tiệm đã bán'),
    ('nofind', 'decline'): ('return_refused', 1, '{Item} còn mới nguyên mà tiệm không cho đổi lấy món khác.', 'từ chối cả đổi món'),
}


def _return_case(ret: dict) -> str:
    if ret['_tag'] == 'other':
        return 'other'
    if ret['_cond'] in ('defect', 'worn'):
        return ret['_cond']
    return 'found' if ret['_found'] else 'nofind'


def _resolve_return(s, c, b, t, p):
    e = _e()
    need = e.need
    names = _catalog()
    need(t['gift_kind'] == 'return', 'Đơn này không phải đổi trả.')
    choice = p.get('choice')
    need(choice in RESOLUTIONS, 'Cách xử lý không hợp lệ.')
    need(p.get('confirm') is True, 'Xác nhận cách xử lý với khách trước nhé.')
    ret = t['gift']['ret']
    item = ret['item']
    price = names[item]['price']
    restock = ret['_tag'] == 'ours' and ret['_cond'] == 'new'
    if choice == 'exchange' and not restock:
        need(e.available(c, item) >= 1, 'Kệ đang hết món này để đổi. Chọn cách khác hoặc đặt thêm hàng.')
    t['mistakes'] += return_verdict(t, choice)
    t['gs']['resolution'] = choice
    if choice == 'refund':
        e.money(s, c, -price, 'Hoàn tiền đổi trả ' + names[item]['name'], t['id'], category='refund')
        if restock:
            c['stock'][item] = min(24, c['stock'][item] + 1)
    elif choice == 'exchange' and not restock:
        c['stock'][item] -= 1
    b['stats']['returns'] += 1
    b['today']['returns'] += 1
    g = guest(t)
    said = {'refund': f'Hoàn {price} xu cho khách.', 'exchange': 'Đổi cho khách một món mới.', 'credit': f'Tặng phiếu mua hàng {price} xu.',
            'decline': 'Từ chối nhẹ nhàng, giải thích chính sách.'}[choice]
    # Only what is unfair to the customer becomes their complaint (an unfair refund costs the shop).
    row = RETURN_SLIPS.get((_return_case(ret), choice))
    if row:
        from . import consequences as cq
        cq.slip(t, row[0], row[1], row[2].format(Item=names[item]['name'], item=low(names[item]['name']), me=g['me']), row[3])
    from . import consequences as cq
    r = cq.react(s, c, t, 0, who=g['name'])
    e.task_done(s, c, t, 0, f'Đổi trả với {g["name"]}: {said}')
    post = next((f for f in c['feed'] if f.get('source') == t['id'] and f.get('kind') == 'review'), None)
    if post:
        post['author'] = g['name']
    fair = t['mistakes'] == 0
    return dict(message=f"{said} {truth_text(t)}" + (f" {r['message']}" if r['message'] else ''), celebrate=fair, correct=fair)


# ---------------------------------------------------------------- hooks
def on_start(s: dict, c: dict) -> None:
    b = state(c)
    if b['day'] == c['day']:
        return
    e = _e()
    b.update(day=c['day'], mod=roll_mod(c['day']), events_today=0, last_turn=-99, today_kinds=[],
             today=dict(sold=0, advised=0, returns=0, events=0, fines=0))
    keep = []
    for f in b['followups']:
        if f['day'] > c['day']:
            keep.append(f)
            continue
        if f['kind'] == 'worried':
            post = e.add_feed(s, c, f['npc'], f"Về nhà đọc hộp mới thấy ghi {f['label']}, trong khi bé nhà mình mới {f['age']} tháng. Lần sau mong tiệm nhắc giúp mình nhé.", f['ref'], 2, 'review')
            post['author'] = f['name']
        elif f['kind'] == 'fake':
            amount = min(c['money'], f['amount'])
            if amount:
                e.money(s, c, -amount, 'Hoàn tiền gấu bông lỗi mắt', f['ref'], category='refund')
            post = e.add_feed(s, c, f['npc'], 'Gấu bông mua hôm qua bung mắt nhựa sau một buổi, may bé chưa cho vào miệng. Tiệm đã hoàn tiền nhưng mình vẫn hơi sợ.', f['ref'], 1, 'review')
            post['author'] = f['name']
        elif f['kind'] == 'thanks':
            post = e.add_feed(s, c, f['npc'], 'Tối qua bé ngủ ngon hơn hẳn. Cảm ơn tiệm đã hỏi han kỹ mà không bán thừa món nào 🥹', f['ref'], 5, 'review')
            post['author'] = f['name']
    b['followups'] = keep[-12:]


def after_task(s: dict, c: dict, t: dict) -> None:
    if not t.get('gen'):
        return
    e = _e()
    b = state(c)
    names = _catalog()
    g = guest(t)
    post = next((f for f in c['feed'] if f.get('source') == t['id'] and f.get('kind') == 'review'), None)
    if post and t['gift'].get('guest'):
        post['author'] = g['name']
    if t['gift'].get('guest'):
        # A passer-by does not come back as one of the regulars tomorrow.
        c['pending'] = [x for x in c['pending'] if not (x.get('kind') == 'return_note' and x.get('ref') == t['id'])]
    if t['gift_kind'] == 'return':
        return
    b['today']['sold'] += 1
    disc = t['gs'].get('discount', 0)
    if disc:
        e.money(s, c, -min(disc, c['money']), 'Bớt giá cho khách', t['id'], category='discount')
    # The sale was already rung up by shop_deliver: a customer who spots a mistake takes
    # part of it back (or all of it and hands the goods back) through consequences.react.
    from . import consequences as cq
    r = cq.react(s, c, t, max(0, _total(c, t['basket']) - disc), prepaid=True, who=g['name'])
    handed_back = r['kind'] in ('walkout', 'refuse')
    if handed_back:
        for k, v in t['basket'].items():
            c['stock'][k] = min(24, c['stock'].get(k, 0) + v)
    if r['message']:
        e.log(s, c, 'complaint', r['message'], t['npc'], t['id'])
    age = t['gift'].get('age')
    unsafe = [k for k in t['basket'] if age is not None and LABELS[k]['use'] != 'card' and not suits(k, age)]
    if unsafe and not handed_back:
        k = unsafe[0]
        b['followups'].append(dict(kind='worried', day=c['day'] + 1, ref=t['id'], npc=t['npc'], name=g['name'], label=LABELS[k]['label'], age=age))
    if t['gift_kind'] == 'kit' and t['mistakes'] == 0:
        b['stats']['kits'] += 1
        b['followups'].append(dict(kind='thanks', day=c['day'] + 1, ref=t['id'], npc=t['npc'], name=g['name']))
    if t['gift_kind'] == 'bulk':
        b['stats']['bulk'] += 1
    bears = 0 if handed_back else t['basket'].get('bear', 0)
    if bears and b['fake']:
        n = min(bears, b['fake'])
        b['fake'] -= n
        b['followups'].append(dict(kind='fake', day=c['day'] + 1, ref=t['id'], npc=t['npc'], name=g['name'], amount=n * names['bear']['price']))
    b['followups'] = b['followups'][-12:]


def on_close(s: dict, c: dict) -> dict:
    b = state(c)
    ev = b.get('event')
    if ev and ev['stage'] == 'open' and ev['kind'] == 'formula':
        b['expired_left'] = sum(1 for x in ev['facts']['cans'] if x['exp'] < c['day'])
    b['event'] = None
    summary = dict(day=c['day'], modifier=b['mod'], **b['today'])
    b['history'] = (b['history'] + [summary])[-14:]
    return summary


# ---------------------------------------------------------------- surprises
TRIGGERS = {'ask', 'shop_pick', 'shop_pack', 'shop_check', 'shop_deliver', 'gift_advise', 'gift_ask', 'gift_book', 'gift_inspect',
            'gift_resolve', 'receive_stock', 'order_stock', 'more_work', 'basket_remove'}


def _check_formula(c, b):
    if 'formula' in [h['kind'] for h in b['ev_history'][-3:]]:
        return None
    r = rng(CAREER, 'cans', c['day'], c['turn'])
    brands = ['Sữa bột Mầm Xanh 400g', 'Sữa bột Sao Mai 800g', 'Sữa bột Bé Na 400g', 'Sữa bột Mầm Xanh 800g', 'Sữa bột Sao Mai 400g', 'Sữa bột Bé Na 800g']
    n_old = r.choice([1, 2, 2, 3])
    idx = r.sample(range(6), n_old)
    cans = []
    for i, name in enumerate(brands):
        exp = c['day'] - r.randint(1, 9) if i in idx else c['day'] + r.choice([1, 2, 5, 12, 30, 60])
        cans.append(dict(id=f'can-{i}', name=name, exp=exp, date=date_text(exp)))
    return dict(cans=cans, today=date_text(c['day']), pulled=[])


def _check_fake(c, b):
    if c['day'] < 3 or b['fake'] or 'fake' in [h['kind'] for h in b['ev_history'][-4:]]:
        return None
    if c['stock'].get('bear', 0) + 6 > 24:
        return None
    r = rng(CAREER, 'fake', c['day'], c['turn'])
    return dict(seller='Anh Tâm', item='bear', qty=6, unit=20, _fake=r.random() < 0.7, inspected=False)


def _check_lost(c, b):
    return dict(age=4)


def _check_haggle(c, b):
    for t in c['tasks']:
        if _open(t) and t.get('gen') and t['known'] and t['gift_kind'] not in ('return', 'kit') and not t['gs'].get('discount') and t['basket']:
            total = _total(c, t['basket'])
            if total >= 80:
                return dict(task=t['id'], total=total, ask=max(5, round(total * 0.1)))
    return None


def _check_tet(c, b):
    if modifier(c)['id'] != 'tet':
        return None
    return dict(extra=2)


def _check_inspect(c, b):
    if c['day'] < 4 and not b['fake']:
        return None
    if 'inspection' in [h['kind'] for h in b['ev_history'][-5:]]:
        return None
    return dict(team='Đoàn kiểm tra nhãn hàng hóa của phường')


def _check_donation(c, b):
    if c['day'] < 3:
        return None
    return dict(org='Hội phụ nữ phường')


EVENTS = {
    'formula': dict(check=_check_formula, weight=3, title='Kiểm hạn sữa bột trên kệ', emoji='🥛'),
    'fake': dict(check=_check_fake, weight=3, title='Người chào hàng giá rẻ', emoji='🧸'),
    'lost': dict(check=_check_lost, weight=2, title='Bé đi lạc trong tiệm', emoji='🧒'),
    'haggle': dict(check=_check_haggle, weight=3, title='Khách xin bớt giá', emoji='🪙'),
    'tet': dict(check=_check_tet, weight=6, title='Khách Tết đổ về', emoji='🧧'),
    'inspection': dict(check=_check_inspect, weight=2, title='Kiểm tra nhãn hàng đồ chơi', emoji='📋'),
    'donation': dict(check=_check_donation, weight=1, title='Quyên góp đồ sơ sinh', emoji='🤲'),
}
MOD_BOOST = {'fair': ('fake', 'haggle'), 'weekend': ('lost',), 'payday': ('haggle',), 'tet': ('tet', 'lost')}


def after_action(s: dict, c: dict, action: str) -> None:
    """Maybe start one counter surprise (called after each command)."""
    if action not in TRIGGERS or not c['open'] or c['day'] < GEN_FROM_DAY or c['day_completed'] < 1:
        return
    story = c.get('event')
    # A classic story raised today goes first. One carried over from an earlier day, or a
    # practice run, must not silence the shop's surprises for the rest of the save.
    if story and story.get('stage') != 'resolved' and not story.get('practice') and story.get('created_day', c['day']) == c['day']:
        return
    b = state(c)
    if b['event']:
        return
    mod = modifier(c)['id']
    cap = 1 + (c['day'] >= 4) + (mod in ('fair', 'tet'))
    if b['events_today'] >= cap or c['turn'] - b['last_turn'] < 4:
        return
    r = rng(CAREER, 'event', c['day'], c['turn'], b['events_today'])
    if r.random() > 0.35:
        return
    recent = [h['kind'] for h in b['ev_history'][-4:]]
    cands = []
    for kind, spec in EVENTS.items():
        if kind in b['today_kinds']:
            continue
        facts = spec['check'](c, b)
        if facts is None:
            continue
        w = spec['weight'] * (3 if kind in MOD_BOOST.get(mod, ()) else 1) * (0.3 if kind in recent else 1)
        if kind == 'inspection' and b['fake']:
            w *= 4
        cands.append((kind, facts, w))
    if not cands:
        return
    kind, facts, _ = r.choices(cands, [x[2] for x in cands])[0]
    b['ev_seq'] += 1
    b['event'] = dict(id=f"gift-ev-{c['day']}-{b['ev_seq']}", kind=kind, day=c['day'], turn=c['turn'], stage='open', facts=facts,
                      task=facts.get('task'), choice=None, result=None, effects=[], good=False)
    b['events_today'] += 1
    b['today']['events'] += 1
    b['stats']['events'] += 1
    b['last_turn'] = c['turn']
    b['today_kinds'].append(kind)
    _e().log(s, c, 'shop_event', EVENTS[kind]['title'], ref=b['event']['id'])


def event_text(c: dict, ev: dict) -> str:
    f = ev['facts']
    k = ev['kind']
    if k == 'formula':
        return f"Chị Hạnh bên nguồn hàng nhắn: “Lô sữa bột trên kệ có vài hộp sắp và đã quá hạn, kiểm giúp chị nhé.” Hôm nay là {f['today']}. Chạm vào hộp đã quá hạn để rút khỏi kệ."
    if k == 'fake':
        base = f"Anh Tâm chào hàng: “{f['qty']} bé gấu bông y hệt Gấu Mật Ong, chỉ {f['unit']} xu một bé thôi, lấy nhanh kẻo hết!”"
        if f.get('inspected'):
            base += ' ' + ' · '.join(_fake_labels(f))
        return base
    if k == 'lost':
        return 'Một bé chừng bốn tuổi đứng khóc giữa hai dãy kệ, cứ gọi “mẹ ơi”. Quanh đó không thấy người lớn nào.'
    if k == 'haggle':
        return f"Khách nhìn tổng tiền {f['total']} xu rồi cười: “Mua nhiều vậy, bạn bớt cho mình {f['ask']} xu được không?”"
    if k == 'tet':
        return 'Cận Tết, khách đổ vào tiệm một lúc, ai cũng muốn giấy đỏ và thiệp chúc năm mới. Hàng chờ dài ra trông thấy.'
    if k == 'inspection':
        return 'Đoàn kiểm tra của phường ghé: “Cho xem tem hợp quy và nhãn phụ tiếng Việt trên đồ chơi, kèm hóa đơn nhập hàng nhé.”'
    if k == 'donation':
        return 'Hội phụ nữ phường ghé xin quyên góp đồ sơ sinh cho các bé ở nhà mở cuối phố.'
    return ''


def _fake_labels(f: dict) -> list:
    if f['_fake']:
        return ['Không có tem hợp quy CR', 'Không có nhãn phụ tiếng Việt', 'Mắt nhựa lung lay khi kéo nhẹ']
    return ['Tem hợp quy CR đầy đủ', 'Nhãn phụ tiếng Việt rõ ràng', 'Có hóa đơn thanh lý của nhà phân phối']


def event_choices(c: dict, ev: dict) -> list:
    f = ev['facts']
    k = ev['kind']
    if k == 'formula':
        return [dict(id='done', label=f"Xong, rút {len(f['pulled'])} hộp khỏi kệ")]
    if k == 'fake':
        opts = []
        if not f.get('inspected'):
            opts.append(dict(id='inspect', label='Xem kỹ tem và nhãn trước'))
        opts.append(dict(id='buy', label=f"Nhập {f['qty']} bé gấu", cost=f['qty'] * f['unit'], hint=f"{f['qty'] * f['unit']} xu"))
        if f.get('inspected') and f['_fake']:
            opts.append(dict(id='report', label='Từ chối và báo phường'))
        opts.append(dict(id='decline', label='Cảm ơn, tiệm không nhập'))
        return opts
    if k == 'lost':
        return [dict(id='counter', label='Giữ bé ở quầy, nhờ loa chợ tìm người nhà'), dict(id='call', label='Gọi bảo vệ chợ tới giúp'),
                dict(id='outside', label='Dắt bé ra đầu phố tìm', hint='Quầy không người trông')]
    if k == 'haggle':
        opts = [dict(id='discount', label=f"Bớt {f['ask']} xu cho khách"), dict(id='keep', label='Giữ giá, giải thích nhẹ nhàng')]
        opts.insert(1, dict(id='card', label='Tặng kèm một thiệp Nắng thay vì bớt'))
        return opts
    if k == 'tet':
        return [dict(id='number', label='Phát số thứ tự, gói lần lượt'), dict(id='helper', label='Thuê bạn gói quà thời vụ hôm nay', cost=30, hint='30 xu'),
                dict(id='rush', label='Gói thật nhanh cho kịp', hint='Khách chờ vẫn sốt ruột')]
    if k == 'inspection':
        return [dict(id='show', label='Mời xem kệ và hóa đơn nhập'), dict(id='hide', label='Xin khất, cất bớt hàng vào kho')]
    if k == 'donation':
        return [dict(id='goods', label='Tặng 2 khăn Lá và 1 đôi tất'), dict(id='money', label='Góp 20 xu', cost=20), dict(id='later', label='Hẹn dịp khác')]
    return []


def _answer(s: dict, c: dict, b: dict, p: dict) -> dict:
    e = _e()
    need = e.need
    ev = b.get('event')
    need(ev and ev['stage'] == 'open', 'Không có chuyện nào đang chờ bạn.')
    if ev['kind'] == 'formula' and 'can' in p:
        can = p.get('can')
        ids = [x['id'] for x in ev['facts']['cans']]
        need(can in ids, 'Không có hộp này trên kệ.')
        pulled = ev['facts']['pulled']
        if can in pulled:
            pulled.remove(can)
        else:
            pulled.append(can)
        pulled.sort()
        return dict(message='Đã đặt lại hộp lên kệ.' if can not in pulled else 'Đã rút hộp khỏi kệ.', _free=True)
    choice = p.get('choice')
    opt = next((o for o in event_choices(c, ev) if o['id'] == choice), None)
    need(opt, 'Lựa chọn không có trong tình huống.')
    if opt.get('cost'):
        need(c['money'] >= opt['cost'], 'Chưa đủ xu cho lựa chọn này. Chọn cách khác nhé.')
    if ev['kind'] == 'fake' and choice == 'inspect':
        ev['facts']['inspected'] = True
        return dict(message='Bạn lật nhãn, kéo thử mắt gấu: ' + ' · '.join(_fake_labels(ev['facts'])) + '.')
    _resolve(s, c, b, ev, choice)
    return dict(message=ev['result'], celebrate=ev['good'])


def _waiting(c: dict) -> list:
    return [t for t in c['tasks'] if _open(t) and t['id'] != c.get('active_task')]


def _patience(t: dict, delta: int) -> None:
    t['patience'] = max(25, min(100, t.get('patience', 100) + delta))


def _resolve(s: dict, c: dict, b: dict, ev: dict, choice: str) -> None:
    e = _e()
    f = ev['facts']
    k = ev['kind']
    eff = []
    good = False
    result = ''
    if k == 'formula':
        old = {x['id'] for x in f['cans'] if x['exp'] < c['day']}
        pulled = set(f['pulled'])
        missed = old - pulled
        wrong = pulled - old
        b['expired_left'] = len(missed)
        if not missed and not wrong:
            c['xp'] += 10
            good = True
            result = f'Rút đúng {len(old)} hộp quá hạn. Kệ sữa bột giờ chỉ còn hộp còn hạn.'
            eff.append('+10 XP')
        else:
            parts = []
            if missed:
                parts.append(f'còn sót {len(missed)} hộp quá hạn trên kệ')
                e.metric(c, 'safety_miss')
                post = e.add_feed(s, c, f'{CAREER}_npc_01', 'Suýt mua phải hộp sữa bột quá hạn ở tiệm, may mình đọc kỹ ngày trên đáy hộp.', ev['id'], 2, 'review')
                post['author'] = 'Một mẹ bỉm'
            if wrong:
                parts.append(f'rút nhầm {len(wrong)} hộp còn hạn')
                for t in _waiting(c):
                    _patience(t, -5)
            result = 'Kiểm xong nhưng ' + ' và '.join(parts) + '. Đọc kỹ ngày trên đáy hộp nhé.'
    elif k == 'fake':
        if choice == 'buy':
            cost = f['qty'] * f['unit']
            e.money(s, c, -cost, 'Nhập gấu bông giá rẻ của Anh Tâm', ev['id'], category='stock')
            c['stock']['bear'] = min(24, c['stock']['bear'] + f['qty'])
            eff.append(f"-{cost} xu · +{f['qty']} gấu")
            if f['_fake']:
                b['fake'] += f['qty']
                result = 'Gấu về kệ, giá rẻ bất ngờ.' if not f.get('inspected') else 'Bạn vẫn nhập dù thiếu tem và nhãn. Mong là không sao…'
            else:
                good = True
                result = 'Hàng thanh lý chính hãng, tem nhãn đủ. Một mẻ nhập hời!'
        elif choice == 'report':
            c['xp'] += 15
            good = True
            e.add_feed(s, c, f'{CAREER}_npc_06', 'Phường đã thu giữ lô gấu bông không tem ở chợ. Cảm ơn Tiệm Mây Nhỏ đã báo kịp!', ev['id'], kind='story')
            result = 'Phường cảm ơn tiệm đã báo. Lô gấu không tem bị thu giữ trước khi tới tay các bé.'
            eff.append('+15 XP')
        else:
            result = 'Anh Tâm lắc đầu đi sang tiệm khác.' + (' Có lẽ hàng cũng ổn, nhưng cẩn thận không bao giờ thừa.' if not f['_fake'] and f.get('inspected') else '')
            good = f['_fake']
    elif k == 'lost':
        if choice == 'counter':
            good = True
            c['xp'] += 5
            e.add_feed(s, c, f'{CAREER}_npc_03', 'Con mình lạc trong chợ, may tiệm giữ bé ở quầy và nhờ loa gọi. Cảm ơn nhiều lắm 🙏', ev['id'], 5, 'review')
            result = 'Mẹ bé chạy tới sau vài phút, ôm chầm lấy con và cảm ơn rối rít.'
        elif choice == 'call':
            good = True
            result = 'Bảo vệ chợ dắt bé tới phòng trực và tìm được mẹ bé. Quầy vẫn có người trông.'
        else:
            for t in _waiting(c):
                _patience(t, -12)
            result = 'Bạn tìm được mẹ bé ở đầu phố, nhưng quầy bỏ trống một lúc, khách chờ ai cũng sốt ruột.'
            eff.append('Khách chờ -12 kiên nhẫn')
    elif k == 'haggle':
        t = next((x for x in c['tasks'] if x['id'] == f['task'] and _open(x)), None)
        if not t:
            result = 'Khách đã rời quầy, chuyện bớt giá cũng qua.'
        elif choice == 'discount':
            t['gs']['discount'] = f['ask']
            _patience(t, 10)
            result = f"Khách vui ra mặt. Khi thanh toán sẽ bớt {f['ask']} xu."
            eff.append(f"-{f['ask']} xu khi giao")
        elif choice == 'card':
            if e.available(c, 'card') > 0:
                c['stock']['card'] -= 1
                _patience(t, 6)
                good = True
                result = 'Khách thích tấm thiệp Nắng tặng kèm hơn cả bớt giá.'
                eff.append('-1 thiệp Nắng')
            else:
                t['gs']['discount'] = f['ask']
                result = f"Kệ hết thiệp nên bạn bớt {f['ask']} xu thay vào đó."
        else:
            _patience(t, -8)
            result = 'Khách hơi tiếc nhưng hiểu: giá ở tiệm đã niêm yết rõ ràng.'
            eff.append('-8 kiên nhẫn')
    elif k == 'tet':
        from .content import make_task
        made = 0
        for _ in range(f['extra']):
            slots = [int(t['id'].split('-')[-1]) for t in c['tasks'] if t['day'] == c['day']]
            slot = max(slots, default=-1) + 1
            if slot >= 12:
                break
            c['tasks'].append(make_task(CAREER, c['day'], slot, c['turn']))
            made += 1
        if choice == 'helper':
            e.money(s, c, -30, 'Thuê bạn gói quà thời vụ ngày Tết', ev['id'], category='staff')
            for t in c['tasks']:
                if _open(t):
                    _patience(t, 15)
            good = True
            result = f'Bạn gói quà thời vụ tới phụ một tay. {made} khách mới vào hàng mà ai cũng vui vẻ.'
            eff.append('-30 xu · khách +15 kiên nhẫn')
        elif choice == 'number':
            for t in c['tasks']:
                if _open(t):
                    _patience(t, 5)
            good = True
            result = f'Ai cũng cầm số thứ tự, chờ lần lượt. {made} khách mới vào hàng.'
        else:
            for t in _waiting(c):
                _patience(t, -10)
            result = f'Bạn cố gói thật nhanh, {made} khách mới vào hàng, ai cũng sốt ruột.'
            eff.append('Khách chờ -10 kiên nhẫn')
        if made:
            eff.append(f'+{made} khách')
    elif k == 'inspection':
        if b['fake'] or b['expired_left']:
            fine = min(c['money'], 60 if choice == 'show' else 90)
            if fine:
                e.money(s, c, -fine, 'Phạt hàng thiếu tem nhãn hoặc quá hạn', ev['id'], category='fine')
            b['today']['fines'] += fine
            if b['fake']:
                c['stock']['bear'] = max(0, c['stock']['bear'] - b['fake'])
                eff.append(f"Thu giữ {b['fake']} gấu không tem")
            b['fake'] = 0
            b['expired_left'] = 0
            eff.insert(0, f'-{fine} xu')
            result = f'Đoàn tìm thấy hàng thiếu tem hoặc quá hạn trên kệ: phạt {fine} xu.' + (' Cất giấu còn bị phạt nặng hơn.' if choice == 'hide' else '')
        elif choice == 'show':
            c['xp'] += 10
            good = True
            result = 'Tem hợp quy, nhãn phụ và hóa đơn đầy đủ. Đoàn ký biên bản “không vi phạm”.'
            eff.append('+10 XP')
        else:
            result = 'Hàng không có gì sai, nhưng cất giấu khiến đoàn nghi ngờ và hẹn quay lại kiểm tra kỹ hơn.'
    elif k == 'donation':
        if choice == 'goods':
            e.need(e.available(c, 'towel') >= 2 and e.available(c, 'socks') >= 1, 'Kệ không đủ khăn hoặc tất để tặng. Chọn cách khác nhé.')
            c['stock']['towel'] -= 2
            c['stock']['socks'] -= 1
            good = True
            eff.append('-2 khăn · -1 tất')
        elif choice == 'money':
            e.money(s, c, -20, 'Góp quỹ đồ sơ sinh của phường', ev['id'], category='gift')
            good = True
            eff.append('-20 xu')
        if good:
            e.add_feed(s, c, f'{CAREER}_npc_02', 'Hội phụ nữ phường cảm ơn Tiệm Mây Nhỏ đã góp đồ cho các bé ở nhà mở 💛', ev['id'], kind='story')
            result = 'Các cô ghi tên tiệm vào sổ cảm ơn. Chiều nay đồ sẽ tới nhà mở.'
        else:
            result = 'Các cô vui vẻ hẹn dịp khác.'
    ev.update(stage='done', choice=choice, result=result, effects=eff, good=good)
    b['ev_history'] = (b['ev_history'] + [dict(kind=k, choice=choice, day=c['day'])])[-30:]
    e.log(s, c, 'shop_event', EVENTS[k]['title'] + ': ' + result, ref=ev['id'])


# ---------------------------------------------------------------- projection
def _clean(v):
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items() if not str(k).startswith('_')}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def public(c: dict) -> dict:
    b = view(c)
    mod = modifier(c) if c['day'] >= GEN_FROM_DAY else MOD_INDEX['normal']
    ev = b.get('event')
    ev_view = None
    if ev:
        facts = {}
        if ev['kind'] == 'formula':
            facts = dict(cans=[dict(id=x['id'], name=x['name'], date=x['date']) for x in ev['facts']['cans']], today=ev['facts']['today'], pulled=ev['facts']['pulled'])
        elif ev['kind'] == 'fake':
            facts = dict(labels=_fake_labels(ev['facts']) if ev['facts'].get('inspected') else [], inspected=ev['facts'].get('inspected', False))
        ev_view = dict(id=ev['id'], kind=ev['kind'], stage=ev['stage'], title=EVENTS[ev['kind']]['title'], emoji=EVENTS[ev['kind']]['emoji'],
                       text=event_text(c, ev), choices=event_choices(c, ev) if ev['stage'] == 'open' else [], result=ev.get('result'),
                       effects=ev.get('effects', []), good=ev.get('good', False), task=ev.get('task'), facts=facts)
    return _clean(dict(modifier=dict(id=mod['id'], title=mod['title'], emoji=mod['emoji'], text=mod['text']), event=ev_view,
                       labels=LABELS, uses=USES, tags=TAGS, papers=PAPER_NAMES, today=b['today'], stats=b['stats'], history=b['history'][-7:],
                       date=date_text(c['day'])))


def public_task(t: dict, v: dict) -> dict:
    """Engine task_view for day-2+ orders: hide rolled truths until discovered."""
    g = t['gift']
    gs = t['gs']
    kind = t['gift_kind']
    pub = dict(kind=kind, guest=g.get('guest'), mod=g['mod'], swap=gs.get('swap'), discount=gs.get('discount', 0), request=None,
               age=None, items=None, kit=None, ret=None, pick=g.get('pick'), options=None)
    if t['known']:
        # A first-time parent's baby age is only known once asked.
        pub.update(request=request_text(None, t), age=g.get('age') if kind != 'kit' or 'age' in gs['asked'] else None, items=g.get('items'))
        if kind == 'kit':
            pub['kit'] = dict(asked=list(gs['asked']), answers=[dict(topic=x, text=answer(t, x)) for x in gs['asked']])
            v['needs'] = dict(v['needs'], product=None, budget=v['needs']['budget'] if 'budget' in gs['asked'] else None)
        if kind == 'return':
            ret = g['ret']
            seen = gs['seen']
            pub['ret'] = dict(item=ret['item'], said=ret['said'], said_date=date_text(ret['said']), seen=list(seen),
                              book=_clean(ret['book']) if 'book' in seen else None,
                              tag=inspect_text(t, 'tag') if 'tag' in seen else None, look=inspect_text(t, 'item') if 'item' in seen else None,
                              resolution=gs.get('resolution'), verdict=truth_text(t) if gs.get('resolution') else None)
    v['gift'] = pub
    v.pop('gs', None)
    if _open(t):
        v.pop('slips', None)
        v.pop('reaction', None)
    return v


# ---------------------------------------------------------------- validation
def validate_task(t: dict) -> None:
    e = _e()
    need = e.need
    names = _catalog()
    slot = int(t['id'].rsplit('-', 1)[1])
    ref = make_fields(t['day'], slot)
    need(t.get('gen') == 2 and t.get('gift_kind') == ref['gift_kind'] and t.get('gift') == ref['gift'], 'Dữ kiện đơn quà bị thay đổi.')
    gs = t.get('gs')
    need(isinstance(gs, dict) and set(gs) == {'swap', 'asked', 'seen', 'resolution', 'discount'}, 'Tiến trình đơn quà sai.')
    if gs['swap'] is not None:
        need(t['gift_kind'] == 'safety' and gs['swap'] in names and suits(gs['swap'], t['gift']['age']), 'Món đổi an toàn sai.')
    need(isinstance(gs['asked'], list) and len(set(gs['asked'])) == len(gs['asked']) and all(x in TOPICS for x in gs['asked']), 'Câu hỏi đã hỏi sai.')
    need(isinstance(gs['seen'], list) and len(set(gs['seen'])) == len(gs['seen']) and all(x in ('book', 'tag', 'item') for x in gs['seen']), 'Phần đã xem sai.')
    need(gs['resolution'] is None or (t['gift_kind'] == 'return' and gs['resolution'] in RESOLUTIONS), 'Cách xử lý đổi trả sai.')
    e.integer(gs['discount'], 0, 500)
    need(sum(t['basket'].values()) <= basket_cap(t), 'Giỏ quá nhiều món.')
    if t['pack'] and 'tag' in t['pack']:
        need(t['pack']['tag'] in TAG_IDS, 'Lời chúc trên thiệp sai.')


def validate(c: dict) -> None:
    raw = ((c.get('ext') or {}).get('data') or {}).get('gift')
    if raw is None:
        return
    e = _e()
    need = e.need
    need(isinstance(raw, dict) and raw.get('v') == 1, 'Dữ liệu tiệm quà sai.')
    b = view(c)
    for k in ('day', 'events_today', 'ev_seq', 'fake', 'expired_left'):
        e.integer(b[k], 0, 10**9)
    e.integer(b['last_turn'], -99, 10**9)
    need(b['fake'] <= 24, 'Số gấu thiếu tem sai.')
    need(b['mod'] in MOD_INDEX, 'Biến số ngày sai.')
    need(isinstance(b['today_kinds'], list) and all(k in EVENTS for k in b['today_kinds']), 'Chuyện trong ngày sai.')
    need(isinstance(b['ev_history'], list) and len(b['ev_history']) <= 30 and all(isinstance(h, dict) and h.get('kind') in EVENTS for h in b['ev_history']), 'Lịch sử chuyện ở tiệm sai.')
    need(isinstance(b['followups'], list) and len(b['followups']) <= 12 and all(isinstance(f, dict) and f.get('kind') in ('worried', 'fake', 'thanks') for f in b['followups']), 'Lời hẹn sau sai.')
    for f in b['followups']:
        e.integer(f.get('day'), 1, 10**9)
        e.integer(f.get('amount', 0), 0, 10**6)
    need(isinstance(b['history'], list) and len(b['history']) <= 14, 'Tổng kết ngày sai.')
    for grp in ('stats', 'today'):
        need(isinstance(b[grp], dict) and all(type(v) is int and 0 <= v < 10**9 for v in b[grp].values()), 'Thống kê tiệm sai.')
    ev = b.get('event')
    if ev is not None:
        need(isinstance(ev, dict) and ev.get('kind') in EVENTS and ev.get('stage') in ('open', 'done') and isinstance(ev.get('facts'), dict), 'Chuyện ở tiệm sai.')
        if ev['kind'] == 'formula':
            ids = [x['id'] for x in ev['facts'].get('cans', [])]
            need(len(ids) == 6 and all(x in ids for x in ev['facts'].get('pulled', [])), 'Kệ sữa bột sai.')
        if ev['stage'] == 'done':
            e.clean_text(ev.get('result'), 600)


# ---------------------------------------------------------------- helpers for tests / staff
SAFE_ANSWER = {'formula': 'done', 'fake': 'decline', 'lost': 'counter', 'haggle': 'keep', 'tet': 'number', 'inspection': 'show', 'donation': 'later'}


def best_basket(c: dict, t: dict) -> dict:
    """A basket that satisfies the order (tests use it; never shown to players)."""
    names = _catalog()
    want = target(t)
    if t['gift_kind'] == 'safety' and not t['gs'].get('swap'):
        return {t['needs']['product']: t['needs']['qty']}
    if want is not None:
        return want
    if t['gift_kind'] == 'occasion':
        k = min(t['gift']['options'], key=lambda x: names[x]['price'])
        return {k: 1}
    age = t['gift']['age']
    out = {}
    for w in t['gift']['kit']['wants']:
        k = min((x for x in LABELS if LABELS[x]['use'] == w and suits(x, age)), key=lambda x: names[x]['price'])
        out[k] = 1
    return out


def safe_swap(c: dict, t: dict, in_stock: bool = True) -> str | None:
    names = _catalog()
    age = t['gift']['age']
    options = [k for k in LABELS if LABELS[k]['use'] != 'card' and suits(k, age) and names[k]['price'] * t['needs']['qty'] <= t['needs']['budget']
               and (not in_stock or _e().available(c, k) >= t['needs']['qty'])]
    return min(options, key=lambda k: names[k]['price']) if options else None


def _stock_step(c: dict, k: str) -> tuple[str, dict]:
    ship = next((x for x in c['shipments'] if x['item'] == k and x['status'] != 'received'), None)
    if ship and ship['ready'] <= c['turn']:
        return 'receive_stock', dict(shipment=ship['id'], count=ship['actual'])
    if ship:
        return 'advance', {}
    return 'order_stock', dict(item=k, qty=min(6, 24 - c['stock'][k]))


def next_move(c: dict, t: dict) -> tuple[str, dict]:
    """One sensible next command for an order (tests use it)."""
    e = _e()
    b = view(c)
    ev = b.get('event')
    tid = t['id']
    if ev and ev['stage'] == 'open':
        if ev['kind'] == 'formula':
            for can in ev['facts']['cans']:
                if (can['exp'] < c['day']) != (can['id'] in ev['facts']['pulled']):
                    return 'gift_event', dict(can=can['id'])
        return 'gift_event', dict(choice=SAFE_ANSWER[ev['kind']])
    if not t['known']:
        return 'ask', dict(task=tid)
    kind = t['gift_kind']
    if kind == 'return':
        for part in ('book', 'tag', 'item'):
            if part not in t['gs']['seen']:
                return ('gift_book', dict(task=tid)) if part == 'book' else ('gift_inspect', dict(task=tid, part=part))
        ret = t['gift']['ret']
        restock = ret['_tag'] == 'ours' and ret['_cond'] == 'new'
        for choice in ('credit', 'decline', 'exchange', 'refund'):
            if return_verdict(t, choice):
                continue
            if choice == 'exchange' and not restock and e.available(c, ret['item']) < 1:
                continue
            return 'gift_resolve', dict(task=tid, choice=choice, confirm=True)
    if kind == 'kit':
        for topic in TOPICS:
            if topic not in t['gs']['asked']:
                return 'gift_ask', dict(task=tid, topic=topic)
    if kind == 'safety' and not t['gs'].get('swap'):
        item = safe_swap(c, t)
        if item:
            return 'gift_advise', dict(task=tid, item=item)
        return _stock_step(c, safe_swap(c, t, False))
    want = best_basket(c, t)
    for k, q in t['basket'].items():
        if q > want.get(k, 0):
            return 'basket_remove', dict(task=tid, item=k)
    for k, q in want.items():
        if t['basket'].get(k, 0) < q:
            if e.available(c, k) > 0:
                return 'shop_pick', dict(task=tid, item=k)
            return _stock_step(c, k)
    n = t['needs']
    tag = t['gift'].get('tag')
    if n['gift'] and (not t['pack'] or t['pack']['paper'] != n['paper'] or (tag and t['pack'].get('tag') != tag)):
        return 'shop_pack', dict(task=tid, paper=n['paper'], ribbon='gold', card='Một ngày thật vui!', **({'tag': tag} if tag else {}))
    if not t['checked']:
        return 'shop_check', dict(task=tid)
    return 'shop_deliver', dict(task=tid)

# Care loop: regular families, subscriptions, the diaper & formula shelf, registry.
from .careers import mother_baby as _care  # noqa: E402
_care.install(globals())
