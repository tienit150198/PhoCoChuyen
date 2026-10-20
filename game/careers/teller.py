"""🏦 Ngân hàng — giao dịch viên: Quầy số 3 at the Bến Chợ transaction office of Ngân hàng Phố. "Quầy số 3 xin chào!"

One customer at a time, five steps: nhận yêu cầu (read the slip: the engine's 'ask') → kiểm tra thông tin → xử lý tiền →
xác nhận → giao biên nhận. Jobs: 💵 Rút tiền (drag notes into the tray to the exact amount; the tray totals itself; the
customer's wishes and an empty drawer slot are rules), 🪙 Đổi tiền lẻ (the bundles a shop owner needs), 🔁 Chuyển tiền (the
recipient by name, photo and one more detail: two people share the name), 🐷 Gửi tiết kiệm theo mục tiêu (a monthly plan
for a goal; Bà Lựu's long arc saves for a new tea cart) and 🏧 Tiếp quỹ ATM. The shift opens with the float count and closes
with 🧾 Bàn giao cuối ca (receipts against transactions, the pending one, the drawer total).

Customers are the street's people (Bà Lựu of the trà đá, dì Bảy of the cơm tấm, bác Lâm of the phở, chị Thơ of the album
shop…). The counter's money is the bank's cash, counted in nghìn đồng: nothing here ever moves the player's own wallet or
Ngân hàng Phố account (game/bank.py). Pay is the employment contract's salary at closing plus a small bonus per customer.

Hiring inside the branch (after the town's job application): học việc ngắn (three lessons) → thi thực hành (three parts:
counting and change; confirming a transfer when two recipients share a name; a slip that says one amount while the
customer says another) → a name badge (⚡ fast and 🎯 no hints are extra achievements) → TRAINING shifts with chị Hạnh beside
you → giao dịch viên. Then four branches with their own ranks (Giao dịch, Tư vấn, Vận hành, Quản lý), the key steps
behind a short review; the honest advice record helps at the review.

Every step is graded on the server; a wrong step stays open to fix in place and lowers the quality (and the bonus). A
job's content is a pure function of (day, slot, job) plus the arc stage and branch rank stamped on the task when it is
made, so a save validates on any date. Rollback: the career is dormant (engine.DORMANT) until used, and
scripts/strip_new_careers.py takes a used one out for an older build (tests/test_career_teller_compat.py).
"""
from __future__ import annotations

from copy import deepcopy
import json
import math

from . import kit
from . import teller_content as tc
from .. import consequences as cq

ID = 'teller'
GEN = 1
PEOPLE = tc.PEOPLE
FIXED = ('gen', 'needs', '_key', 'kind', 'job')
PHYSICAL = ('tl_step',)
FREE = ('tl_intro', 'tl_learn', 'tl_exam', 'tl_exam_hint', 'tl_branch', 'tl_review', 'tl_seen')
NO_TICK = FREE + ('tl_desk',)
TYPES = ('choice', 'number', 'multi', 'tray', 'pick')
LINES = 24


def money_text(k: int) -> str:
    """2350 (nghìn đồng) → '2.350.000đ'."""
    return f'{int(k) * 1000:,}'.replace(',', '.') + 'đ'


_DIGIT = ('không', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín')
_GROUP = ('', 'nghìn', 'triệu', 'tỷ')


def _three(n: int, inner: bool) -> list:
    """0..999 in words; `inner`: a higher group comes before it (so 50 reads 'không trăm năm mươi', 5 'không trăm linh năm')."""
    h, t, u = n // 100, n // 10 % 10, n % 10
    out = [_DIGIT[h], 'trăm'] if h or inner else []
    if t == 0:
        if u:
            out += (['linh'] if h or inner else []) + [_DIGIT[u]]
    elif t == 1:
        out += ['mười'] + (['lăm' if u == 5 else _DIGIT[u]] if u else [])
    else:
        out += [_DIGIT[t], 'mươi'] + (['mốt' if u == 1 else 'lăm' if u == 5 else _DIGIT[u]] if u else [])
    return out


def number_words(n: int) -> str:
    """1050000 → 'một triệu không trăm năm mươi nghìn' (how a slip writes an amount bằng chữ)."""
    n = int(n)
    if n <= 0:
        return 'không'
    groups = []
    while n:
        groups.append(n % 1000)
        n //= 1000
    words = []
    for i in range(len(groups) - 1, -1, -1):
        if groups[i]:
            words += _three(groups[i], i < len(groups) - 1) + ([_GROUP[i]] if _GROUP[i] else [])
    return ' '.join(words)


def money_words(k: int) -> str:
    """2350 (nghìn đồng) → 'Hai triệu ba trăm năm mươi nghìn đồng'."""
    w = number_words(int(k) * 1000) + ' đồng'
    return w[:1].upper() + w[1:]


# ---------------------------------------------------------------- tray rules (the bank's cash, in nghìn đồng)
def tray_norm(value) -> dict:
    """A tray from the client: {denomination: count} with string keys. Only known notes, 0..TRAY_MAX each."""
    kit.need(isinstance(value, dict) and len(value) <= len(tc.DENOMS), 'Khay tiền không hợp lệ.')
    out = {}
    for k, n in value.items():
        kit.need(k in tc.DENOM_KEYS, 'Khay chỉ nhận tờ 500, 200, 100, 50, 20 và 10 nghìn.')
        n = kit.integer(n, 0, tc.TRAY_MAX)
        if n:
            out[k] = n
    return {k: out[k] for k in tc.DENOM_KEYS if k in out}


def tray_total(tray: dict) -> int:
    return sum(int(k) * n for k, n in tray.items())


def tray_count(tray: dict) -> int:
    return sum(tray.values())


def _usable(rule: dict) -> list[str]:
    allowed = rule.get('allowed') or list(tc.DENOM_KEYS)
    caps = rule.get('max') or {}
    return [k for k in tc.DENOM_KEYS if k in allowed and caps.get(k, 1) != 0]


def fewest_notes(total: int, rule: dict) -> int | None:
    """The fewest notes that make `total` from the usable notes (after the rule's minimums). Pure DP."""
    mins = rule.get('min') or {}
    rest = total - sum(int(k) * n for k, n in mins.items())
    if rest < 0 or rest % 10:
        return None
    notes = [int(k) // 10 for k in _usable(rule)]
    goal = rest // 10
    best = [0] + [None] * goal
    for v in range(1, goal + 1):
        got = [best[v - d] for d in notes if d <= v and best[v - d] is not None]
        best[v] = min(got) + 1 if got else None
    return None if best[goal] is None else best[goal] + sum(mins.values())


def tray_problem(tray: dict, rule: dict) -> str | None:
    """Why `tray` does not satisfy `rule` (None: it does). The words point at the slip, never at the answer."""
    total = tray_total(tray)
    if total != rule['total']:
        return f'Khay đang {money_text(total)}, phiếu cần {money_text(rule["total"])}.'
    allowed = set(_usable(rule))
    if any(k not in allowed for k in tray):
        return 'Trong khay có tờ khách không lấy hoặc két đang hết.'
    for k, n in (rule.get('min') or {}).items():
        if tray.get(k, 0) < n:
            return f'Khách dặn ít nhất {n} tờ {k} nghìn.'
    if rule.get('exact') is not None and tray != rule['exact']:
        return 'Số tờ từng loại chưa đúng các cọc khách cần.'
    if rule.get('fewest') and tray_count(tray) != fewest_notes(rule['total'], rule):
        return 'Khách muốn ít tờ nhất: còn đổi được vài tờ nhỏ thành tờ to hơn.'
    return None


def tray_answer(rule: dict) -> dict:
    """One tray that satisfies the rule (what chị Hạnh lays out): the bundles, else the minimums and then the biggest
    usable notes first (the fewest notes for these values; tests check it against fewest_notes)."""
    if rule.get('exact') is not None:
        return dict(rule['exact'])
    tray = {k: n for k, n in (rule.get('min') or {}).items()}
    rest = rule['total'] - tray_total(tray)
    for k in _usable(rule):
        n, rest = divmod(rest, int(k))
        if n:
            tray[k] = tray.get(k, 0) + n
    return {k: tray[k] for k in tc.DENOM_KEYS if k in tray}


# ---------------------------------------------------------------- steps
def _opts(r, rows, shuffle=True):
    out = [dict(id=k, label=v) for k, v in rows]
    if shuffle:
        r.shuffle(out)
    return out


def _step(job, name, typ, title, evidence, options=None, unit='', **more):
    st = dict(id=f'{job}.{name}', type=typ, title=title, evidence=evidence)
    if options is not None:
        st['options'] = options
    if unit:
        st['unit'] = unit
    st.update(more)
    return st


def _tray_step(job, name, title, evidence, rule):
    palette = [k for k in tc.DENOM_KEYS if k in _usable(rule)] if rule.get('exact') is None else list(tc.DENOM_KEYS)
    return _step(job, name, 'tray', title, evidence, target=rule['total'], palette=palette)


def _person(npc: int) -> str:
    return PEOPLE[npc][0]


def low(text: str) -> str:
    """'Tiếp quỹ ATM' → 'tiếp quỹ ATM' (only the first letter)."""
    return text[:1].lower() + text[1:]


def _withdraw(r, day, slot, npc, rk):
    who = _person(npc)
    amount = r.randint(8, 60) * 50
    # its own draw (the rota's withdrawal slots all fall on one parity of day + slot: an index by it never met two cases)
    variant = kit.rng(ID, 'withdraw-case', day, slot).choice(tc.WD_VARIANTS) if day > 1 else 'ok'
    wish_id, wish, wish_rule = r.choice(tc.WISHES)
    out = r.choice(list(tc.OUT_LINES)) if r.random() < 0.35 else None
    if out and wish_id == 'lixi' and out == '50':
        out = '200'
    rule = dict(total=amount, **deepcopy(wish_rule))
    if out:
        rule.setdefault('max', {})[out] = 0
    if wish_id == 'small' and out:
        rule['allowed'] = [k for k in rule['allowed'] if k != out]
    if fewest_notes(amount, rule) is None:   # never an impossible tray
        rule = dict(total=amount)
        wish_id, wish, out = 'none', tc.WISHES[0][1], None
    words_amount = amount
    slip = dict(name=who, amount=amount, amount_text=money_text(amount), signed=True, face=tc.NPC_FACE[npc])
    card = dict(name=who, face=slip['face'], no=f'0{r.randint(10, 99)}…{r.randint(100, 999)}')
    said = ''
    if variant == 'clarify':
        swapped = int(str(amount)[::-1].lstrip('0') or 0)
        words_amount = swapped if swapped and swapped != amount and swapped % 10 == 0 and 400 <= swapped <= 3000 else amount + 500
        slip['words'] = f'bằng chữ: {money_words(words_amount)}'
        confirmed = r.choice((amount, words_amount))
        rule['total'] = confirmed
        if fewest_notes(confirmed, rule) is None:
            rule = dict(total=confirmed)
            wish_id, wish, out = 'none', tc.WISHES[0][1], None
        said = f'Khách xác nhận lấy {money_text(confirmed)} và ký sửa phiếu.'
    elif variant == 'sign':
        slip['signed'] = False
        said = 'Khách ký vào phiếu trước mặt bạn.'
    elif variant == 'refuse':
        rel = r.choice(tc.RELATIVES)
        card = dict(name=f'{r.choice(("Trần", "Lê", "Phạm"))} Văn {r.choice(("Bình", "Dũng", "Sơn"))}', face='🧑🏻',
                    no=f'0{r.randint(10, 99)}…{r.randint(100, 999)}', note=f'{rel} của {who}')
        slip['by'] = f'Người đứng quầy: {rel} của {who}, đưa CCCD của mình, không có giấy ủy quyền.'
    check_key = {'ok': 'ok', 'clarify': 'clarify', 'sign': 'sign', 'refuse': 'refuse'}[variant]
    steps = [_step('withdraw', 'check', 'choice', 'Kiểm tra thông tin',
                   'So tên, ảnh, số CCCD với phiếu rút; so số với chữ trên phiếu.', _opts(r, tc.CHECK_OPTS))]
    key = {'withdraw.check': check_key}
    if variant == 'refuse':
        steps.append(_step('withdraw', 'next', 'choice', 'Hướng dẫn khách', 'Người đứng quầy không phải chủ tài khoản.', _opts(r, tc.REFUSE_NEXT)))
        key['withdraw.next'] = 'poa'
    else:
        notes = [wish]
        if out:
            notes.append(tc.OUT_LINES[out])
        if said:
            notes.insert(0, said)
        steps.append(_tray_step('withdraw', 'tray', 'Xếp tiền vào khay', ' '.join(notes), rule))
        key['withdraw.tray'] = dict(rule, tray=True)
        steps.append(_step('withdraw', 'confirm', 'choice', 'Xác nhận với khách', 'Tiền đã nằm đủ trong khay.', _opts(r, tc.CONFIRM_OPTS)))
        key['withdraw.confirm'] = 'count'
    steps.append(_step('withdraw', 'receipt', 'choice', 'Giao biên nhận', 'Máy in ra hai liên biên nhận.', _opts(r, tc.RECEIPT_OPTS)))
    key['withdraw.receipt'] = 'own'
    brief = dict(slip=slip, card=card, wish=wish, variant=variant, steps=steps)
    title = f'Rút tiền · {who}'
    opening = f'{who} đặt phiếu rút tiền lên quầy: “Quầy số 3 đây rồi!”'
    return brief, key, title, opening


def _change(r, day, slot, npc, rk):
    who = _person(npc)
    shop = tc.CHANGE_SHOP.get(npc, 'quán')
    brought = {'500': r.randint(1, 4), '200': r.randint(0, 3)}
    brought = {k: n for k, n in brought.items() if n}
    total = tray_total(brought)
    rest = r.choice(('50', '20'))
    small = [k for k in ('10', '20', '50') if k != rest]
    final = {k: r.randint(0, 2) for k in small}
    final = {k: n for k, n in final.items() if n} or {small[0]: 1}
    bundles = lambda x: tray_total({k: n * tc.BUNDLE for k, n in x.items()})
    while bundles(final) > total - 2 * int(rest):   # always at least two notes of the remainder
        if final == {small[0]: 1}:
            break
        k = max(final, key=lambda x: int(x) * final[x])
        final[k] -= 1
        final = {x: n for x, n in final.items() if n} or {small[0]: 1}
    # The customer first asks for one value, then changes her mind (the bundles she finally wants are `final`).
    swap = None
    pair = [k for k in final if k in ('10', '20')]
    if r.random() < 0.4 and len(final) == 1 and pair:
        to = pair[0]
        frm = '20' if to == '10' else '10'
        if frm != rest:
            swap = (frm, to)
    want = {swap[0]: final[swap[1]]} if swap else dict(final)
    exact = {k: n * tc.BUNDLE for k, n in final.items()}
    exact[rest] = exact.get(rest, 0) + (total - tray_total(exact)) // int(rest)
    exact = {k: exact[k] for k in tc.DENOM_KEYS if exact.get(k)}
    wanted = ', '.join(f'{n} cọc tờ {k} nghìn' for k, n in want.items())
    ask = (f'“Đổi cho dì {wanted}, còn lại tờ {rest} nghìn hết nhé.”' if npc == tc.BAY
           else f'“Đổi cho tôi {wanted}, còn lại tờ {rest} nghìn hết nhé.”')
    notes_line = ', '.join(f'{n} tờ {k} nghìn' for k, n in brought.items())
    evidence = 'Đưa đúng số cọc khách cần, phần còn lại theo mệnh giá khách chọn. Một cọc là 10 tờ.'
    if swap:
        evidence = f'{who} chợt nhớ: “Thôi đổi cọc tờ {swap[0]} thành cọc tờ {swap[1]} giùm!” ' + evidence
    steps = [
        _step('change', 'count', 'number', 'Đếm tiền khách đưa', f'{who} đưa: {notes_line}.', unit='nghìn'),
        _step('change', 'tray', 'tray', 'Xếp các cọc vào khay', evidence, target=total, palette=list(tc.DENOM_KEYS)),
        _step('change', 'bundle', 'choice', 'Buộc cọc, xác nhận', 'Tiền lẻ đã đủ trong khay.', _opts(r, tc.BUNDLE_OPTS)),
        _step('change', 'receipt', 'choice', 'Giao bảng kê', 'Khách cần giấy để đối chiếu sổ của quán.', _opts(r, tc.LIST_OPTS)),
    ]
    key = {'change.count': total, 'change.tray': dict(total=total, exact=exact, tray=True), 'change.bundle': 'band', 'change.receipt': 'list'}
    brief = dict(shop=shop, brought=brought, ask=ask, swap=list(swap) if swap else None, steps=steps)
    title = f'Đổi tiền lẻ · {who}'
    opening = f'{who} ({shop}) dằn xấp tiền chẵn lên quầy. {ask}'
    return brief, key, title, opening


def faces_of(name: str) -> tuple:
    """Faces that fit the name ('Thị', 'Thu': a woman's name)."""
    return tc.FACES_F if (' Thị ' in name or ' Thu ' in name) else tc.FACES_M


def _directory(r, name, face, detail):
    """Four cards: the right one, a twin with the same name and detail but another face, the same name and face with
    another detail, and a near name with the same face and detail. Shuffled."""
    faces = [f for f in faces_of(name) if f != face]   # the twin: another face of the same kind
    details = [d for d in tc.DETAILS if d != detail]
    tails = r.sample(range(10, 99), 4)
    cards = [dict(id='right', name=name, face=face, detail=detail),
             dict(id='twin', name=name, face=r.choice(faces), detail=detail),
             dict(id='other', name=name, face=face, detail=r.choice(details)),
             dict(id='near', name=tc.NEAR.get(name, name + ' (B)'), face=face, detail=detail)]
    for c, t in zip(cards, tails):
        c['tail'] = f'…{t}'
    r.shuffle(cards)
    ids = 'abcd'
    out, right = [], None
    for i, c in enumerate(cards):
        if c['id'] == 'right':
            right = ids[i]
        out.append(dict(id=ids[i], label=f'{c["name"]} · {c["detail"]} · TK {c["tail"]}', name=c['name'], face=c['face'],
                        detail=c['detail'], tail=c['tail']))
    return out, right


def _transfer(r, day, slot, npc, rk):
    who = _person(npc)
    name = r.choice(tc.NAMES)
    face = r.choice(faces_of(name))
    detail = r.choice(tc.DETAILS)
    cards, right = _directory(r, name, face, detail)
    amount = r.randint(4, 120) * 50
    other_bank = r.random() < 0.5
    fee_in = other_bank and r.random() < 0.3      # "trừ phí vào tiền chuyển luôn"
    fee = tc.FEE_OTHER if other_bank else 0
    collect = amount if fee_in else amount + fee
    purpose = r.choice(tc.PURPOSES)
    bank = 'ngân hàng khác' if other_bank else 'cùng Ngân hàng Phố'
    ask = f'“Chuyển {money_text(amount)} cho {name}, {detail}, để {purpose}. Ảnh đây nè.”'
    fee_line = (f'Người nhận ở {bank}: phí {tc.FEE_OTHER} nghìn. ' + ('Khách dặn: “Trừ phí vào luôn tiền chuyển.”' if fee_in else 'Khách trả phí riêng.')
                if other_bank else 'Người nhận cùng Ngân hàng Phố: miễn phí.')
    steps = [
        _step('transfer', 'who', 'pick', 'Chọn đúng người nhận', f'{who} giơ điện thoại có ảnh người nhận {face}. Tên, ảnh và nghề phải khớp cả ba.', cards),
        _step('transfer', 'collect', 'number', 'Thu tiền của khách', f'Chuyển {money_text(amount)}. {fee_line} Thu của khách bao nhiêu?', unit='nghìn'),
        _step('transfer', 'readback', 'choice', 'Xác nhận với khách', 'Màn hình chờ bấm Chuyển.', _opts(r, tc.READBACK_OPTS)),
        _step('transfer', 'receipt', 'choice', 'Giao chứng từ', 'Giao dịch thành công.', _opts(r, tc.TRANSFER_RECEIPT)),
    ]
    key = {'transfer.who': right, 'transfer.collect': collect, 'transfer.readback': 'read', 'transfer.receipt': 'own'}
    brief = dict(ask=ask, photo=face, name=name, detail=detail, amount=amount, fee=fee, other_bank=other_bank, steps=steps)
    title = f'Chuyển tiền · {who}'
    opening = f'{who} chìa tờ giấy ghi tên người nhận. {ask}'
    return brief, key, title, opening


def monthly(goal: int, saved: int, months: int) -> int:
    """The monthly deposit: (goal − saved) ÷ months, rounded up to 10 nghìn."""
    return math.ceil(max(0, goal - saved) / months / 10) * 10


def _savings_plan(r, job, who, goal_text, emoji, goal, saved, months, flex, rk):
    steps = [
        _step(job, 'ask', 'choice', 'Hỏi mục tiêu', f'{who} muốn để dành tiền {goal_text}.', _opts(r, tc.ASK_OPTS)),
        _step(job, 'monthly', 'number', 'Tính tiền góp mỗi tháng',
              f'Cần {money_text(goal)}, đã có {money_text(saved)}, còn {months} tháng. Làm tròn lên tới 10 nghìn.', unit='nghìn'),
        _step(job, 'product', 'choice', 'Chọn sản phẩm hợp nhu cầu',
              ('Khách nói: “Có khi giữa chừng phải rút ra một ít.”' if flex else 'Khách nói: “Tiền này để dành, không động tới.”'), _opts(r, tc.PRODUCTS)),
    ]
    key = {f'{job}.ask': 'goal', f'{job}.monthly': monthly(goal, saved, months), f'{job}.product': 'flex' if flex else 'goal'}
    if rk >= 1:
        steps.append(_step(job, 'remind', 'choice', 'Hẹn lịch góp (khách quen)', 'Khách hay quên ngày góp.', _opts(r, tc.REMIND_OPTS)))
        key[f'{job}.remind'] = 'payday'
    steps.append(_step(job, 'receipt', 'choice', 'Giao sổ, hẹn ngày', 'Sổ tích lũy vừa in xong.', _opts(r, tc.BOOK_OPTS)))
    key[f'{job}.receipt'] = 'book'
    return steps, key


def arc_saved_before(stage: int) -> int:
    """What Bà Lựu has saved when visit `stage` starts (nghìn đồng)."""
    if stage <= 1:
        return tc.ARC_SAVED
    if stage >= 4:
        return tc.ARC_GOAL   # visit 3 paid in what the cart still lacked: the book holds the whole goal
    after_first = tc.ARC_SAVED + tc.ARC_MONTHLY - tc.ARC_SHORT
    return after_first + sum(tc.ARC_DEPOSITS) if stage >= 3 else after_first


def _arc(r, day, slot, stage):
    who = _person(tc.LUU)
    st = tc.ARC_STAGES[min(stage, tc.ARC_N)]
    if stage == 0:
        steps, key = _savings_plan(r, 'savings', who, 'mua chiếc xe trà inox có mái che', '🍵', tc.ARC_GOAL, tc.ARC_SAVED, tc.ARC_MONTHS, False, 0)
        opening = f'{who} đặt cái túi vải lên quầy: “Bà muốn sắm cái xe trà mới, cái cũ gỉ hết bánh rồi. Bà để dành kiểu gì cho kịp?”'
    elif stage == 1:
        bag = {'50': 12, '20': 18, '10': 21}
        got = tray_total(bag)
        steps = [
            _step('savings', 'count', 'number', 'Đếm túi tiền góp', f'{who} bảo: “Đủ một triệu hai đó con.” Trong túi: 12 tờ 50 nghìn, 18 tờ 20 nghìn, 21 tờ 10 nghìn.', unit='nghìn'),
            _step('savings', 'short', 'choice', 'Xử lý chỗ lệch', 'Túi tiền và lời bà nói không khớp.', _opts(r, tc.SHORT_OPTS)),
            _step('savings', 'receipt', 'choice', 'Giao sổ, hẹn ngày', 'Sổ tích lũy ghi khoản góp tháng đầu.', _opts(r, tc.BOOK_OPTS)),
        ]
        key = {'savings.count': got, 'savings.short': 'tell', 'savings.receipt': 'book'}
        opening = f'{who} ghé góp tháng đầu cho chiếc xe trà, tay còn thơm mùi chè.'
    elif stage == 2:
        steps = [
            _step('savings', 'advise', 'choice', 'Bà hỏi ý kiến', 'Cháu trai bà muốn bà rút một nửa sổ cho nó vay mua xe máy.', _opts(r, tc.NEPHEW_OPTS)),
            _step('savings', 'lost', 'number', 'Rút trước hạn mất bao nhiêu lãi',
                  'Sổ tích lũy mục tiêu: rút trước hạn thì mất phần lãi đã tính. Lãi tạm tính tới hôm nay là 36 nghìn.', unit='nghìn'),
            _step('savings', 'receipt', 'choice', 'Giao sổ, hẹn ngày', 'Bà quyết định giữ sổ.', _opts(r, tc.BOOK_OPTS)),
        ]
        key = {'savings.advise': 'advise', 'savings.lost': 36, 'savings.receipt': 'book'}
        opening = f'{who} ngồi xuống ghế, thở dài: “Thằng cháu nó xin bà rút tiền, bà phân vân quá con ạ.”'
    elif stage == 3:
        saved = arc_saved_before(3)
        steps = [
            _step('savings', 'left', 'number', 'Còn thiếu bao nhiêu cho chiếc xe',
                  f'Sổ đang có {money_text(saved)}. Xe trà giá {money_text(tc.ARC_GOAL)}.', unit='nghìn'),
            _step('savings', 'receipt', 'choice', 'Giao sổ, hẹn ngày', 'Bà góp đúng số còn thiếu.', _opts(r, tc.BOOK_OPTS)),
        ]
        key = {'savings.left': tc.ARC_GOAL - saved, 'savings.receipt': 'book'}
        opening = f'{who} cười tít mắt: “Bà dành dụm thêm được rồi, góp nốt đợt cuối nhé!”'
    elif stage == 4:
        shops = list(tc.CART_SHOPS)
        cards = [dict(id='a', label=f'{shops[0]} · đường Ven Sông · TK …31', name=shops[0], face='🛠️', detail='đường Ven Sông', tail='…31'),
                 dict(id='b', label=f'{shops[1]} · chợ Bến · TK …31', name=shops[1], face='🛠️', detail='chợ Bến', tail='…31'),
                 dict(id='c', label=f'{shops[2]} · đường Ven Sông · TK …13', name=shops[2], face='🛠️', detail='đường Ven Sông', tail='…13')]
        r.shuffle(cards)
        right = next(c['id'] for c in cards if c['name'] == shops[0] and c['detail'] == 'đường Ven Sông')
        total = tc.ARC_GOAL + tc.ARC_INTEREST
        steps = [
            _step('savings', 'settle', 'number', 'Tất toán sổ', f'Sổ có {money_text(tc.ARC_GOAL)} gốc và {money_text(tc.ARC_INTEREST)} lãi. Tất toán được bao nhiêu?', unit='nghìn'),
            _step('savings', 'who', 'pick', 'Chuyển cho đúng xưởng', 'Hóa đơn xưởng ghi: Xưởng inox Phát Đạt, đường Ven Sông. Hai xưởng trùng tên.', cards),
            _step('savings', 'receipt', 'choice', 'Giao chứng từ', 'Tiền xe đã chuyển.', _opts(r, tc.TRANSFER_RECEIPT)),
        ]
        key = {'savings.settle': total, 'savings.who': right, 'savings.receipt': 'own'}
        opening = f'{who} mặc áo bà ba mới: “Hôm nay bà trả tiền xe! Con làm giúp bà cho đúng nhé.”'
    else:
        coins = {'20': r.randint(5, 15), '10': r.randint(10, 30)}
        steps = [
            _step('savings', 'count', 'number', 'Đếm tiền bán trà gửi vào', f'{who} đưa túi tiền bán trà: {coins["20"]} tờ 20 nghìn, {coins["10"]} tờ 10 nghìn.', unit='nghìn'),
            _step('savings', 'receipt', 'choice', 'Giao sổ', 'Bà gửi vào sổ linh hoạt.', _opts(r, tc.BOOK_OPTS)),
        ]
        key = {'savings.count': tray_total(coins), 'savings.receipt': 'book'}
        opening = f'{who} đẩy xe trà mới bóng loáng tới cửa, gửi tiền bán trà hôm nay.'
    brief = dict(arc=stage, arc_title=st['title'], emoji=st['emoji'], goal=tc.ARC_GOAL, saved=arc_saved_before(stage), steps=steps)
    return brief, key, f'{st["emoji"]} {st["title"]}', opening


def _savings(r, day, slot, npc, rk):
    g = tc.GOALS[(day + slot) % len(tc.GOALS)]
    gnpc, goal_text, emoji, goal, saved, months, flex = g
    who = _person(gnpc)
    steps, key = _savings_plan(r, 'savings', who, goal_text, emoji, goal, saved, months, flex, rk)
    brief = dict(goal_text=goal_text, emoji=emoji, goal=goal, saved=saved, months=months, steps=steps)
    title = f'{emoji} Tiết kiệm · {who}'
    opening = f'{who}: “Mình muốn để dành {goal_text}. Gửi sao cho kịp đây?”'
    return brief, key, title, opening


def _atm(r, day, slot, npc, rk):
    denoms = list(tc.ATM_DENOMS)
    r.shuffle(denoms)
    low_n = r.choice((1, 1, 2))
    lows = set(r.sample(range(4), low_n))
    edge = r.choice([i for i in range(4) if i not in lows])
    cassettes = []
    for i, (slot_id, d) in enumerate(zip(tc.ATM_SLOTS, denoms)):
        left = r.randint(15, tc.ATM_LOW - 5) if i in lows else tc.ATM_LOW if i == edge else r.randint(tc.ATM_LOW + 20, tc.ATM_CAP - 40)
        cassettes.append(dict(id=slot_id, denom=d, left=left))
    low_ids = sorted(c['id'] for c in cassettes if c['left'] < tc.ATM_LOW)
    first = next(c for c in cassettes if c['id'] == low_ids[0])
    steps = [
        _step('atm', 'low', 'multi', 'Chọn hộp tiền cần tiếp', f'Màn hình ATM báo số tờ còn lại từng khe. Dưới {tc.ATM_LOW} tờ là phải tiếp.',
              [dict(id=c['id'], label=f'Khe {c["id"]} · tờ {c["denom"]} nghìn · còn {c["left"]} tờ') for c in cassettes]),
        _step('atm', 'slot', 'choice', f'Lắp hộp tờ {first["denom"]} nghìn vào khe nào', 'Hộp tiền mới dán nhãn mệnh giá. Xem màn hình ATM: khe nào đang giữ tờ này?',
              [dict(id=c['id'], label=f'Khe {c["id"]}') for c in cassettes]),
        _step('atm', 'fill', 'number', 'Tổng số tờ cần nạp', f'Nạp đầy lại mọi hộp đã chọn tới {tc.ATM_CAP} tờ mỗi hộp.', unit='tờ'),
    ]
    key = {'atm.low': low_ids, 'atm.slot': first['id'], 'atm.fill': sum(tc.ATM_CAP - c['left'] for c in cassettes if c['id'] in low_ids)}
    if rk >= 1:
        logs = r.sample(tc.ATM_LOG, 5)
        if not any(x[2] for x in logs):
            logs[0] = next(x for x in tc.ATM_LOG if x[2])
        steps.append(_step('atm', 'journal', 'multi', 'Đối chiếu nhật ký máy (vận hành)', 'Chọn mọi dòng phải lập phiếu sự cố.',
                           [dict(id=x[0], label=x[1]) for x in logs]))
        key['atm.journal'] = sorted(x[0] for x in logs if x[2])
    steps.append(_step('atm', 'seal', 'choice', 'Niêm phong, ghi sổ', 'Hộp tiền đã lắp xong.', _opts(r, tc.SEAL_OPTS)))
    key['atm.seal'] = 'two'
    brief = dict(cassettes=cassettes, cap=tc.ATM_CAP, low=tc.ATM_LOW, steps=steps)
    return brief, key, 'Tiếp quỹ ATM', 'Anh Quân gọi: “ATM trước cửa báo sắp hết tiền, xuống tiếp quỹ với anh!”'


BUILD = dict(withdraw=_withdraw, change=_change, transfer=_transfer, savings=_savings, atm=_atm)
NPC_OF = dict(withdraw=tc.WITHDRAW_NPC, change=tc.CHANGE_NPC, transfer=tc.TRANSFER_NPC)


def job_of(day: int, slot: int) -> str:
    return tc.ROTA[((day - 1) * 3 + slot) % len(tc.ROTA)]   # day 1: rút, chuyển, đổi


def luu_slot(day: int, slot: int) -> bool:
    """🍵 Bà Lựu comes on even days from day 2, as the day's first savings customer."""
    if day < 2 or day % 2 or job_of(day, slot) != 'savings':
        return False
    return all(job_of(day, s) != 'savings' for s in range(slot))


def npc_of(day: int, slot: int, job: str) -> int:
    if job == 'atm':
        return tc.OPS
    if job == 'savings':
        return tc.LUU if luu_slot(day, slot) else tc.GOALS[(day + slot) % len(tc.GOALS)][0]
    rows = NPC_OF[job]
    return rows[kit.rng(ID, 'npc', day, slot).randrange(len(rows))]


def brief(day: int, slot: int, job: str, arc: int = -1, rk: int = 0) -> tuple[dict, list, dict, str, str]:
    """(brief with its steps, steps, answer key, title, opening) of a job. Pure."""
    r = kit.rng(ID, job, day, slot, arc, rk)
    if job == 'savings' and luu_slot(day, slot) and arc >= 0:
        b, key, title, opening = _arc(r, day, slot, arc)
    else:
        b, key, title, opening = BUILD[job](r, day, slot, npc_of(day, slot, job), rk)
    return b, b['steps'], key, title, opening


def make_task(day: int, slot: int, serial: int) -> dict:
    job = job_of(day, slot)
    npc = npc_of(day, slot, job)
    j = tc.JOBS[job]
    return kit.base_task(ID, day, slot, serial, npc, f'{j[1]} {j[0]}', f'{PEOPLE[npc][0]} bốc số, chờ tới Quầy số 3.',
                         gen=GEN, kind='counter', job=job, needs={}, _key={}, arc=-1, rk=0, pct=100,
                         at=0, work={}, errors=[], wrong=0, quality=100, paid=0, lines=[], stage='work')


def _slot(t: dict) -> int:
    return int(t['id'].rsplit('-', 1)[1])


def _active(t: dict) -> tuple[dict, list, dict]:
    b, steps, key, *_ = brief(t['day'], _slot(t), t['job'], t.get('arc', -1), t.get('rk', 0))
    return b, steps, key


def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _right(st: dict, value, want) -> bool:
    if st['type'] == 'tray':
        return tray_problem(value, want) is None
    return _same(value, want)


def _quality(wrong: int) -> int:
    return max(tc.QUALITY_FLOOR, 100 - tc.WRONG_COST * wrong)


def _bonus(t: dict) -> int:
    return max(2, round(tc.BONUS[t['job']] * t['quality'] * t['pct'] / 10000))


HOW = {
    'change.count': 'Cộng mệnh giá nhân số tờ của từng loại khách đưa.',
    'transfer.collect': 'Tiền chuyển cộng phí, trừ khi khách dặn trừ phí vào tiền chuyển.',
    'savings.monthly': 'Lấy số cần trừ số đã có, chia số tháng, làm tròn lên tới 10 nghìn.',
    'savings.count': 'Cộng mệnh giá nhân số tờ của từng loại.',
    'savings.left': 'Giá xe trừ số đang có trong sổ.',
    'savings.settle': 'Gốc cộng lãi.',
    'savings.lost': 'Rút trước hạn mất đúng phần lãi tạm tính.',
    'atm.fill': f'Mỗi hộp đã chọn: {tc.ATM_CAP} trừ số tờ còn lại, rồi cộng lại.',
    'atm.low': f'Chỉ những hộp dưới {tc.ATM_LOW} tờ, đúng {tc.ATM_LOW} thì chưa cần.',
}


# ---------------------------------------------------------------- shift: float at opening, handover at closing
def short_day(day: int) -> bool:
    return day >= 2 and day % tc.SHORT_DAY_EVERY == 3


def desk_scripts(day: int) -> list:
    """The desk surprises that can happen on `day`: “ca trước bàn giao quỹ thiếu” only on a day the float really is short."""
    return [x for x in tc.DESK if x['id'] != 'short_float' or short_day(day)]


def _transactions(day: int) -> tuple[list, str]:
    """The day's ledger for the handover (pure): five rows with their receipt numbers; the receipt of one withdrawal is not
    in the tray (signed, never paid out: pending)."""
    r = kit.rng(ID, 'handover', day)
    rows = []
    for i in range(5):
        kind = r.choice(('dep', 'wd', 'wd'))
        rows.append(dict(id=f'gd{i + 1}', kind=kind, amount=r.randint(4, 60) * 50, who=PEOPLE[r.choice((2, 3, 4, 5, 6, 7))][0],
                         time=f'{9 + i}:{r.randint(10, 59)}', receipt=f'BN-{day % 1000:03d}{i + 1}'))
    pending = r.choice([x['id'] for x in rows if x['kind'] == 'wd'] or [rows[0]['id']])
    return rows, pending


def shift_steps(day: int, part: str, mgr: int = 0) -> tuple[list, dict]:
    """The opening float count ('open') or the closing handover ('close') of `day`: (steps, key). Pure."""
    r = kit.rng(ID, 'shift', part, day)
    if part == 'open':
        total = sum(int(k) * n for k, n in tc.ENVELOPES)
        book = total + (200 if short_day(day) else 0)
        steps = [_step('open', 'count', 'number', 'Đếm quỹ đầu ca', 'Đếm từng phong bì ca trước bàn giao, cộng lại.', unit='nghìn',
                       rows=[f'Tờ {k} nghìn × {n}' for k, n in tc.ENVELOPES]),
                 _step('open', 'sign', 'choice', 'So với sổ bàn giao', f'Sổ bàn giao ghi: {money_text(book)}.', _opts(r, tc.OPEN_SIGN, shuffle=False))]
        return steps, {'open.count': total, 'open.sign': 'report' if book != total else 'sign'}
    rows, pending = _transactions(day)
    shown = [dict(id=x['id'], label=f'{x["time"]} · {x["who"]} · {dict(tc.TX_KINDS)[x["kind"]]} {money_text(x["amount"])} · {x["receipt"]}') for x in rows]
    tray = [f'🧾 {x["receipt"]}' for x in rows if x['id'] != pending]
    r.shuffle(tray)
    float_total = sum(int(k) * n for k, n in tc.ENVELOPES)
    cash = float_total + sum(x['amount'] for x in rows if x['kind'] == 'dep') - sum(x['amount'] for x in rows if x['kind'] == 'wd' and x['id'] != pending)
    steps = [_step('close', 'pending', 'choice', 'Tìm giao dịch treo', 'Khớp biên nhận trong khay với từng dòng sổ giao dịch: dòng nào không có biên nhận?', shown,
                   rows=tray),
             _step('close', 'action', 'choice', 'Xử lý giao dịch treo', 'Khách đã ký phiếu rút nhưng chưa nhận tiền, đã về.', _opts(r, tc.PENDING_OPTS)),
             _step('close', 'cash', 'number', 'Tiền quầy phải có', f'Quỹ đầu ca {money_text(float_total)}. Cộng tiền gửi vào, trừ tiền đã chi; khoản treo chưa chi thì không trừ.',
                   unit='nghìn')]
    key = {'close.pending': pending, 'close.action': 'log', 'close.cash': cash}
    if mgr >= 1:
        steps.append(_step('close', 'roster', 'choice', 'Xếp ca ngày mai (quản lý)', tc.ROSTER_RULES,
                           _opts(r, [(f'r{i}', txt) for i, (txt, _) in enumerate(tc.ROSTERS)])))
        key['close.roster'] = next(f'r{i}' for i, (_, ok) in enumerate(tc.ROSTERS) if ok)
    return steps, key


# ---------------------------------------------------------------- 🎓 thi thực hành and promotion reviews (pure)
def exam_parts(attempt: int, day: int) -> tuple[list, dict]:
    """The practical exam: three parts, one shot each. Pure in (attempt, day)."""
    r = kit.rng(ID, 'exam', attempt, day)
    total = r.randint(6, 20) * 100
    k = r.choice(('10', '20'))
    exact = {k: tc.BUNDLE * 2, '50': (total - 2 * tc.BUNDLE * int(k)) // 50}
    exact = {x: exact[x] for x in tc.DENOM_KEYS if exact.get(x)}
    name = r.choice(tc.NAMES)
    face = r.choice(faces_of(name))
    detail = r.choice(tc.DETAILS)
    cards, right = _directory(r, name, face, detail)
    slip_amt = r.randint(10, 40) * 100
    said = slip_amt + r.choice((-500, 500, 900))
    parts = [
        _step('exam', 'money', 'tray', 'Phần 1 · Đếm và đổi tiền',
              f'Dì Bảy đưa {money_text(total)}: “Đổi cho dì 2 cọc tờ {k} nghìn, còn lại tờ 50 nghìn hết.”', target=total, palette=list(tc.DENOM_KEYS)),
        _step('exam', 'person', 'pick', 'Phần 2 · Xác nhận giao dịch',
              f'Chị Thơ chuyển tiền cho {name}, {detail}; ảnh trên điện thoại là {face}. Có người trùng tên.', cards),
        _step('exam', 'issue', 'choice', 'Phần 3 · Xử lý bất thường',
              f'Phiếu nộp tiền ghi {money_text(slip_amt)}, ông Khang nói “nộp {money_text(said)} nhé”.',
              _opts(r, [('clarify', 'Dừng lại, đếm tiền thật trong túi cùng ông, ông viết phiếu mới và ký, rồi mới làm'),
                        ('slip', 'Làm theo phiếu, phiếu là giấy tờ'),
                        ('said', 'Làm theo lời ông, khách nói là đúng')])),
    ]
    return parts, {'exam.money': dict(total=total, exact=exact, tray=True), 'exam.person': right, 'exam.issue': 'clarify'}


EXAM_HINTS = {
    'exam.money': 'Hai cọc là 20 tờ. Phần còn lại chia 50.',
    'exam.person': 'Chọn thẻ khớp cả tên, ảnh và nghề, không chỉ hai trong ba.',
    'exam.issue': 'Số tiền chưa rõ thì chưa làm gì cả.',
}


def review_parts(branch: str, to: int, day: int, record: dict) -> tuple[list, dict]:
    """A promotion review (a key step of a branch). Pure in (branch, to, day) and the record it reads."""
    r = kit.rng(ID, 'review', branch, to, day)
    rows, pending = _transactions(day + 1000)
    if branch == 'giao_dich':
        busy = _opts(r, [('plan', 'Cụ chống gậy vào quầy bạn trước; khách chuyển 200 triệu sang quầy anh Quân có chị Hạnh kiểm soát; dì Bảy đổi tiền lẻ ở máy đếm phụ'),
                         ('fifo', 'Cứ theo số thứ tự, ai tới trước làm trước, không đổi gì'),
                         ('big', 'Ưu tiên khách 200 triệu cho sếp vui, những người khác chờ')])
        gap = r.choice((200, 500, 100))
        parts = [_step('review', 'busy', 'choice', 'Điều phối ca đông', 'Giờ cao điểm, mở hai quầy. Đang chờ: một cụ chống gậy, dì Bảy cần tiền lẻ gấp, một khách chuyển 200 triệu cần kiểm kỹ.', busy),
                 _step('review', 'gap', 'number', 'Tìm chỗ hụt khi bàn giao', f'Sổ ghi tiền quầy phải có {money_text(52000)}; đếm thực tế được {money_text(52000 - gap)}. Hụt bao nhiêu?', unit='nghìn'),
                 _step('review', 'fix', 'choice', 'Xử lý chỗ hụt', 'Ca sau đang chờ nhận quỹ.',
                       _opts(r, [('trace', 'Chưa bàn giao: đối chiếu biên nhận, camera, ngăn kéo; lập biên bản nếu chưa ra'),
                                 ('fill', 'Bù tạm bằng quỹ khác cho khớp sổ'), ('sign', 'Ca sau ký nhận rồi tính sau')]))]
        key = {'review.busy': 'plan', 'review.gap': gap, 'review.fix': 'trace'}
    elif branch == 'tu_van':
        g = tc.GOALS[day % len(tc.GOALS)]
        parts = [_step('review', 'plan', 'number', 'Lập kế hoạch mục tiêu', f'{_person(g[0])} cần {money_text(g[3])}, có {money_text(g[4])}, còn {g[5]} tháng. Góp mỗi tháng?', unit='nghìn'),
                 _step('review', 'honest', 'choice', 'Chỉ tiêu và nhu cầu khách', 'Giám đốc hỏi: “Khách này không cần bảo hiểm, em có mời không?”',
                       _opts(r, [('honest', 'Không mời gói khách không cần; ghi lý do vào sổ tư vấn'), ('sell', 'Mời cho đủ chỉ tiêu'), ('vague', 'Mời nhẹ, khách chịu thì thôi')]))]
        key = {'review.plan': monthly(g[3], g[4], g[5]), 'review.honest': 'honest'}
    elif branch == 'van_hanh':
        logs = list(tc.ATM_LOG)
        r.shuffle(logs)
        parts = [_step('review', 'log', 'multi', 'Soát nhật ký giao dịch', 'Chọn mọi dòng phải lập phiếu sự cố.', [dict(id=x[0], label=x[1]) for x in logs]),
                 _step('review', 'cash', 'number', 'Đối chiếu quỹ ATM', f'Nạp 3 hộp, mỗi hộp {tc.ATM_CAP} tờ 100 nghìn; đã chi 640 tờ. Còn bao nhiêu tiền trong máy?', unit='nghìn'),
                 _step('review', 'dual', 'choice', 'Nguyên tắc vận hành', 'Anh Quân bảo: “Ca đêm ít người, mở máy một mình cho nhanh.”',
                       _opts(r, [('two', 'Không: luôn hai người, hai chữ ký, niêm phong'), ('ok', 'Được nếu có camera'), ('once', 'Một lần thôi')]))]
        key = {'review.log': sorted(x[0] for x in logs if x[2]), 'review.cash': (3 * tc.ATM_CAP - 640) * 100, 'review.dual': 'two'}
    else:   # quan_ly
        parts = [_step('review', 'roster', 'choice', 'Xếp lịch nhân sự', tc.ROSTER_RULES, _opts(r, [(f'r{i}', txt) for i, (txt, _) in enumerate(tc.ROSTERS)])),
                 _step('review', 'staff', 'number', 'Cần mở bao nhiêu quầy', 'Ngày lương hưu dự kiến 130 khách buổi sáng; một quầy làm được 30 khách một buổi. Làm tròn lên.', unit='quầy'),
                 _step('review', 'conflict', 'choice', 'Chuyện trong phòng', 'Hai nhân viên cãi nhau vì một người hay nhận công của người kia.',
                       _opts(r, [('facts', 'Gặp riêng từng người, xem nhật ký hệ thống, ghi đúng tên người làm, nhắc quy định'),
                                 ('side', 'Bênh người làm lâu năm hơn'), ('ignore', 'Kệ, người lớn tự lo')]))]
        key = {'review.roster': next(f'r{i}' for i, (_, ok) in enumerate(tc.ROSTERS) if ok), 'review.staff': 5, 'review.conflict': 'facts'}
    return parts, key


def record_covers(branch: str, record: dict) -> set:
    """Parts a good service record answers by itself ("the record helps in the review")."""
    if branch == 'tu_van' and record.get('honest', 0) >= 2:
        return {'review.honest'}
    return set()


# ---------------------------------------------------------------- data
def _today(day: int) -> dict:
    return dict(day=day, jobs=0, good=0, bonus=0, counted=0, open_at=0, close_at=0, slips=0, mgr=0, handover=0)


def _ranks() -> dict:
    return {b: 0 for b in tc.BRANCH_IDS}


def initial() -> dict:
    return dict(intro=False, stage='learn', learned=[], exam=None, exams=[], badge=None, training=0, last_train_day=0,
                branch='giao_dich', ranks=_ranks(), prog=_ranks(), review=None, record={k: 0 for k in tc.RECORD_KEYS},
                arc=dict(stage=0, done_day=0, cup=False), today=_today(0), last_active_day=0,
                stats=dict(jobs=0, good=0, active_days=0, bonus=0, handovers=0, kinds={k: 0 for k in tc.JOB_IDS}),
                desk=kit.desk_initial())


def _data(c: dict) -> dict:
    d = kit.data(c)
    if d['today']['day'] != c['day']:
        d['today'] = _today(c['day'])
    return d


def _open_done(c: dict, today: dict) -> bool:
    return today['open_at'] >= len(shift_steps(today['day'], 'open')[0])


def _close_done(today: dict) -> bool:
    return today['close_at'] >= len(shift_steps(today['day'], 'close', today['mgr'])[0])


def rank_of(d: dict, job: str) -> int:
    return d['ranks'].get(tc.JOBS[job][2], 0) if job in tc.JOBS else d['ranks'].get('quan_ly', 0)


def title_of(d: dict) -> str:
    if d['stage'] != 'teller':
        return tc.STAGE_LABEL[d['stage']]
    b = tc.BRANCHES[d['branch']]
    return b['ladder'][min(d['ranks'][d['branch']], len(b['ladder']) - 1)]


def _pct(d: dict, job: str) -> int:
    return tc.STAGE_PCT[d['stage']] * (100 + tc.RANK_PCT * rank_of(d, job)) // 100


PCTS = frozenset(tc.STAGE_PCT[s] * (100 + tc.RANK_PCT * k) // 100 for s in tc.STAGES for k in range(5))


# ---------------------------------------------------------------- actions
def _value(st: dict, value):
    typ = st['type']
    if typ in ('choice', 'pick'):
        return kit.one_of(value, [o['id'] for o in st['options']])
    if typ == 'number':
        return kit.integer(value, 0, 10 ** 7)
    if typ == 'tray':
        return tray_norm(value)
    ids = [o['id'] for o in st['options']]
    return sorted(kit.id_list(value, ids, len(ids)))


def _answer_words(st: dict, want) -> str:
    if st['type'] == 'tray':
        tray = tray_answer(want)
        return ', '.join(f'{n} tờ {k} nghìn' for k, n in tray.items())
    if st['type'] == 'pick':
        o = next((o for o in st['options'] if o['id'] == want), None)
        return o['label'] if o else str(want)
    return kit.answer_text(st, want)


def _wrong_help(t: dict, st: dict, value, want, d: dict) -> str:
    """The first slip says how to work it out (the tray says what is off); the second (the first while learning) shows it."""
    reveal = 1 if d['stage'] in ('learn', 'exam', 'training') else kit.REVEAL_AFTER
    if kit.tries_on_step(t.get('lines')) + 1 >= reveal:
        return f'Chị Hạnh chỉ: {_answer_words(st, want).rstrip(".")}.'
    if st['type'] == 'tray':
        return tray_problem(value, want) or 'Xếp lại khay theo phiếu nhé.'
    return HOW.get(st['id']) or ('Tính lại cho kỹ nhé.' if st['type'] == 'number' else 'Đọc lại phiếu và lời khách rồi làm lại bước này.')


def handle(s: dict, c: dict, name: str, p: dict) -> dict:
    kit.need(name in ('tl_intro', 'tl_learn', 'tl_exam', 'tl_exam_hint', 'tl_step', 'tl_shift', 'tl_desk', 'tl_branch', 'tl_review',
                      'tl_shadow', 'tl_seen'), 'Thao tác ở quầy không hợp lệ.')
    d = _data(c)
    if name == 'tl_intro':
        d['intro'] = True
        return dict(message='Chị Hạnh đưa bạn chiếc ghế xoay ở Quầy số 3: “Học ba bài ngắn với chị đã nhé.”')
    if name == 'tl_seen':
        kit.need(d['arc']['stage'] >= tc.ARC_N and not d['arc']['cup'], 'Không có gì mới ở xe trà.')
        d['arc']['cup'] = True
        return dict(message='🍵 Bà Lựu rót ly trà đầu tiên từ chiếc xe mới, mời bạn: “Ly này bà mời con, không lấy tiền!”', celebrate=True)
    if name == 'tl_learn':
        return _learn(s, c, d, p)
    if name in ('tl_exam', 'tl_exam_hint'):
        return _exam(s, c, d, name, p)
    if name == 'tl_branch':
        return _branch(s, c, d, p)
    if name == 'tl_review':
        return _review(s, c, d, p)
    desk = d['desk']
    if name == 'tl_desk':
        return kit.desk_choose(s, c, ID, desk, tc.DESK, p.get('option'), _hook)
    kit.desk_block(desk, 'Có chuyện cần quyết ở quầy, quyết xong rồi làm tiếp nhé.')
    if name == 'tl_shift':
        return _shift(s, c, d, p)
    t = kit.task(c, p)
    kit.need(t['career'] == ID, 'Phiếu này không phải của quầy.')
    if name == 'tl_shadow':
        return _shadow(s, c, d, t)
    kit.need(t['known'], 'Bấm nhận yêu cầu của khách trước nhé.')
    kit.need(d['stage'] != 'learn', 'Học xong ba bài ngắn với chị Hạnh rồi mới đứng quầy nhé.', 'teller_learn')
    kit.need(d['stage'] != 'exam', 'Qua thi thực hành rồi mới tự đứng quầy. Chưa thi thì đứng cạnh chị Hạnh xem chị làm.', 'teller_exam')
    kit.need(_open_done(c, d['today']), 'Nhận quỹ đầu ca trước khi mở quầy nhé.', 'teller_float')
    kit.need(not _close_done(d['today']), 'Đã bàn giao quỹ cuối ca. Khách còn lại để ca sau nhé.')
    _, steps, key = _active(t)
    kit.need(t['at'] < len(steps), 'Khách này đã xong.')
    st = steps[t['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở trên phiếu nhé.')
    value = _value(st, p.get('value'))
    kit.start_work(t)
    want = key[st['id']]
    if not _right(st, value, want):
        if st['id'] not in t['errors']:
            t['errors'].append(st['id'])
            cq.slip(t, st['id'], 1, 'Phải làm lại: ' + st['title'])
        t['wrong'] += 1
        t['mistakes'] += 1
        t['quality'] = _quality(t['wrong'])
        message = f'Chưa đúng: {low(st["title"])}. {_wrong_help(t, st, value, want, d)}'
        t['lines'] = (t['lines'] + [message[:480]])[-LINES:]
        d['today']['slips'] = min(d['today']['slips'] + 1, 999)
        result = dict(message=message, correct=False)
        _after(s, c, d, result)
        return result
    t['work'][st['id']] = value
    t['at'] += 1
    t['lines'] = (t['lines'] + [f'✓ {st["title"]}.'])[-LINES:]
    if t['at'] < len(steps):
        result = dict(message='Đúng rồi. Tiếp: ' + low(steps[t['at']]['title']) + '.', correct=True)
        _after(s, c, d, result)
        return result
    return _finish(s, c, d, t)


def _finish(s: dict, c: dict, d: dict, t: dict) -> dict:
    t['pct'] = _pct(d, t['job'])
    bonus = _bonus(t)
    t['paid'] = bonus
    t['stage'] = 'done'
    good = t['quality'] >= tc.GOOD
    today = d['today']
    for bucket in (today, d['stats']):
        bucket['jobs'] += 1
        bucket['good'] += int(good)
        bucket['bonus'] += bonus
    extra = ''
    if good:
        d['stats']['kinds'][t['job']] += 1
        if d['stage'] == 'teller':
            b = tc.JOBS[t['job']][2]
            d['prog'][b] = min(d['prog'][b] + 1, 10 ** 6)
    arc_done = False
    if t['job'] == 'savings' and t.get('arc', -1) >= 0 and t['arc'] == d['arc']['stage'] and d['arc']['stage'] < tc.ARC_N:
        d['arc']['stage'] += 1
        if d['arc']['stage'] == tc.ARC_N:
            d['arc']['done_day'] = c['day']
            arc_done = True
            c['xp'] += 12
            kit.review(s, c, kit.npc_id(ID, tc.LUU), 5, 'Xe trà mới của bà đã về gốc bàng! Nhờ quầy số 3 tính giúp từng tháng. Ghé bà mời ly trà đầu tiên nhé.',
                       f'arc-{c["day"]}')
            kit.log(s, c, 'story', '🍵 Chiếc xe trà inox mới của bà Lựu đã đứng dưới gốc bàng đầu phố.', kit.npc_id(ID, tc.LUU), t['id'])
            extra = ' 🍵 Xe trà mới của bà Lựu đã ra phố!'
    j = tc.JOBS[t['job']]
    kit.complete(s, c, t, bonus, f'Xong việc {low(j[0])} cho {PEOPLE[int(t["npc"].rsplit("_", 1)[1]) - 1][0]}, chất lượng {t["quality"]}%.')
    result = dict(message=f'Xong: {low(j[0])}. Chất lượng {t["quality"]}%, thưởng {bonus} xu.{extra}', correct=good, celebrate=good or arc_done)
    if arc_done:
        result['arc'] = 'done'
    _after(s, c, d, result)
    return result


def _shadow(s: dict, c: dict, d: dict, t: dict) -> dict:
    """Before the practical exam: chị Hạnh serves the customer, the player watches (no bonus, a little xp)."""
    kit.need(d['stage'] in ('learn', 'exam'), 'Bạn đã tự đứng quầy được rồi.')
    kit.need(t['at'] == 0 and t['status'] in ('new', 'understood'), 'Khách này đang làm dở.')
    j = tc.JOBS[t['job']]
    t['stage'] = 'done'
    t['at'] = len(_active(t)[1])
    t['known'] = True
    _, steps, key = _active(t)
    t['work'] = {st['id']: tray_answer(key[st['id']]) if st['type'] == 'tray' else key[st['id']] for st in steps}
    t['lines'] = (t['lines'] + ['👀 Chị Hạnh làm, bạn đứng cạnh xem.'])[-LINES:]
    t['shadow'] = True
    c['xp'] += 1
    # Watching is not serving: the customer is chị Hạnh's. The slip closes (referred) without the engine's task_done, so
    # it adds nothing to day_completed (the contract's worked day), served, the career's good days or the promotion
    # counters, and brings no review.
    t['status'] = 'referred'
    t['completed_turn'] = c['turn']
    t['deferred'] = False
    kit.eng().mark_done(c, t['id'])
    kit.eng().next_active(c)
    return dict(message=f'👀 Chị Hạnh làm {low(j[0])}, vừa làm vừa nói từng bước cho bạn nghe.')


def _hook(s: dict, c: dict, key: str, v) -> str | None:
    """Desk effects beyond kit's: 'record' bumps the service record."""
    if key == 'record' and isinstance(v, dict):
        rec = kit.data(c)['record']
        for k, n in v.items():
            if k in rec:
                rec[k] = min(rec[k] + int(n), 10 ** 6)
    return None


def _learn(s: dict, c: dict, d: dict, p: dict) -> dict:
    kit.need(d['stage'] == 'learn', 'Bạn đã học xong ba bài ngắn.')
    lesson = next((x for x in tc.LESSONS if x['id'] == p.get('lesson')), None)
    kit.need(lesson is not None, 'Bài học không có.')
    kit.need(lesson['id'] not in d['learned'], 'Bài này bạn học rồi.')
    ans = kit.one_of(p.get('answer'), [o[0] for o in lesson['options']])
    if ans != lesson['answer']:
        return dict(message=f'Chưa đúng. {lesson["text"]}', correct=False)
    d['learned'].append(lesson['id'])
    c['xp'] += 1
    if len(d['learned']) == len(tc.LESSONS):
        d['stage'] = 'exam'
        return dict(message='✓ Xong ba bài học việc. Sẵn sàng thì bấm 📝 Thi thực hành: ba phần, mỗi phần làm một lần.', celebrate=True)
    return dict(message=f'✓ {lesson["title"]}. Còn {len(tc.LESSONS) - len(d["learned"])} bài.', correct=True)


def _exam(s: dict, c: dict, d: dict, name: str, p: dict) -> dict:
    kit.need(d['stage'] == 'exam', 'Chưa tới thi thực hành.' if d['stage'] == 'learn' else 'Bạn đã qua thi thực hành.')
    ex = d['exam']
    busy = any(t.get('career') == ID and t['status'] == 'in_progress' for t in c['tasks'])
    if ex is None or ex['done']:
        kit.need(name == 'tl_exam' and p.get('start') is True, 'Bấm Bắt đầu thi trước nhé.')
        kit.need(not ex or ex['day'] < c['day'], 'Hôm nay thi rồi. Mai thi lại với đề khác nhé.', 'teller_retry')
        kit.need(not busy, 'Xong khách đang làm dở rồi mới thi.')
        attempt = len(d['exams']) + 1
        d['exam'] = dict(attempt=attempt, day=c['day'], at=0, started=round(kit.now(), 3), hints=0, got=[], done=False, secs=0)
        return dict(message='📝 Bắt đầu thi thực hành. Phần 1: đếm và đổi tiền. Mỗi phần làm một lần.')
    parts, key = exam_parts(ex['attempt'], ex['day'])
    st = parts[ex['at']]
    if name == 'tl_exam_hint':
        kit.need(ex['hints'] < 9, 'Hết gợi ý rồi.')
        ex['hints'] += 1
        return dict(message=f'💡 {EXAM_HINTS[st["id"]]}', hint=True)
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm phần đang mở nhé.')
    value = _value(st, p.get('value'))
    ok = _right(st, value, key[st['id']])
    ex['got'].append(bool(ok))
    ex['at'] += 1
    if ex['at'] < len(parts):
        return dict(message=('✓ Đạt. ' if ok else '✗ Chưa đạt phần này. ') + 'Tiếp: ' + parts[ex['at']]['title'] + '.', correct=ok)
    ex['done'] = True
    ex['secs'] = max(0, min(10 ** 6, int(kit.now() - ex['started'])))
    passed = all(ex['got'])
    fast = passed and ex['secs'] <= tc.EXAM_FAST
    clean = passed and ex['hints'] == 0
    d['exams'] = (d['exams'] + [dict(attempt=ex['attempt'], day=ex['day'], passed=passed, secs=ex['secs'], hints=ex['hints'], got=list(ex['got']))])[-10:]
    names = ['đếm và đổi tiền', 'đúng người nhận', 'làm rõ chỗ bất thường']
    if not passed:
        miss = ', '.join(n for n, g in zip(names, ex['got']) if not g)
        return dict(message=f'Chưa qua: {miss}. Mai thi lại với đề khác; hôm nay đứng cạnh chị Hạnh xem chị làm nhé.', correct=False, exam='fail')
    d['stage'] = 'training'
    d['badge'] = dict(day=c['day'], fast=fast, clean=clean, secs=ex['secs'])
    c['xp'] += 8 + (3 if fast else 0) + (3 if clean else 0)
    extra = (' ⚡ Thi nhanh!' if fast else '') + (' 🎯 Không cần gợi ý!' if clean else '')
    kit.log(s, c, 'job', '🪪 Nhận bảng tên Quầy số 3 sau thi thực hành.' + extra, kit.npc_id(ID, tc.MENTOR))
    return dict(message=f'🪪 Qua thi thực hành! Chị Hạnh cài bảng tên cho bạn.{extra} {tc.TRAINING} ca tới chị đứng cạnh kèm.', celebrate=True, exam='pass')


def _branch(s: dict, c: dict, d: dict, p: dict) -> dict:
    kit.need(d['stage'] == 'teller', f'Đứng quầy một mình (sau {tc.TRAINING} ca kèm) rồi mới chọn nhánh nghề.')
    b = kit.one_of(p.get('branch'), tc.BRANCH_IDS, 'Nhánh nghề không có.')
    need = tc.BRANCHES[b].get('needs')
    if need:
        kit.need(d['ranks'][need[0]] >= need[1], f'Lên {tc.BRANCHES[need[0]]["ladder"][need[1]]} ở nhánh {tc.BRANCHES[need[0]]["label"]} trước.')
    kit.need(not (d['review'] and not d['review']['done']), 'Đang thi lên chức, thi xong rồi đổi nhánh.')
    d['branch'] = b
    return dict(message=f'Nhánh {tc.BRANCHES[b]["label"]}: {title_of(d)}.')


def next_rank(d: dict, branch: str) -> tuple[int, int, bool] | None:
    """(to rank, good jobs needed, exam?) of the branch's next step, or None at the top."""
    to = d['ranks'][branch] + 1
    row = tc.RANK_NEEDS.get((branch, to))
    return (to, row[0], row[1]) if row else None


def _review(s: dict, c: dict, d: dict, p: dict) -> dict:
    kit.need(d['stage'] == 'teller', 'Chưa tới lúc xét lên chức.')
    rv = d['review']
    if rv is None or rv['done']:
        kit.need(p.get('start') is True, 'Bấm Bắt đầu thi lên chức nhé.')
        nr = next_rank(d, d['branch'])
        kit.need(nr and nr[2] and d['prog'][d['branch']] >= nr[1], 'Chưa đủ điều kiện thi lên chức ở nhánh này.')
        # one attempt a day, whatever the branch (switching branch never buys a same-day retake)
        kit.need(not rv or rv['day'] < c['day'], 'Hôm nay thi rồi, mai thi lại nhé.', 'teller_retry')
        d['review'] = rv = dict(branch=d['branch'], to=nr[0], day=c['day'], at=0, got=[], done=False, passed=False)
        parts, _ = review_parts(rv['branch'], rv['to'], rv['day'], d['record'])
        covered = record_covers(rv['branch'], d['record'])
        while rv['at'] < len(parts) and parts[rv['at']]['id'] in covered:
            rv['got'].append(True)
            rv['at'] += 1
        note = f' 📒 Sổ tư vấn có {d["record"]["honest"]} lần tư vấn đúng nhu cầu: phần câu hỏi về chỉ tiêu được tính đạt.' if covered else ''
        return dict(message=f'📝 Thi lên {tc.BRANCHES[rv["branch"]]["ladder"][rv["to"]]}.{note}')
    parts, key = review_parts(rv['branch'], rv['to'], rv['day'], d['record'])
    st = parts[rv['at']]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm phần đang mở nhé.')
    value = _value(st, p.get('value'))
    ok = _right(st, value, key[st['id']])
    rv['got'].append(bool(ok))
    rv['at'] += 1
    covered = record_covers(rv['branch'], d['record'])
    while rv['at'] < len(parts) and parts[rv['at']]['id'] in covered:
        rv['got'].append(True)
        rv['at'] += 1
    if rv['at'] < len(parts):
        return dict(message=('✓ Đạt. ' if ok else '✗ Chưa đạt phần này. ') + 'Tiếp: ' + parts[rv['at']]['title'] + '.', correct=ok)
    rv['done'] = True
    rv['passed'] = all(rv['got'])
    if not rv['passed']:
        return dict(message='Chưa qua đợt xét này. Mai thi lại nhé.', correct=False)
    return dict(message=_promote(s, c, d, rv['branch']), celebrate=True)


def _promote(s: dict, c: dict, d: dict, branch: str) -> str:
    d['ranks'][branch] += 1
    d['prog'][branch] = 0
    c['xp'] += 10
    title = tc.BRANCHES[branch]['ladder'][d['ranks'][branch]]
    kit.log(s, c, 'job', f'🏅 Lên {title} (nhánh {tc.BRANCHES[branch]["label"]}).', kit.npc_id(ID, tc.MENTOR))
    return f'🏅 Lên {title}! Việc nhánh {tc.BRANCHES[branch]["label"]} được thưởng thêm {tc.RANK_PCT}%.'


def _shift(s: dict, c: dict, d: dict, p: dict) -> dict:
    today = d['today']
    part = kit.one_of(p.get('part'), ('open', 'close'), 'Chọn việc đầu ca hay cuối ca nhé.')
    kit.need(c.get('open'), 'Mở ca trước đã.')
    kit.need(d['stage'] not in ('learn',), 'Học xong ba bài ngắn với chị Hạnh trước nhé.')
    if part == 'open' and today['open_at'] == 0:
        today['mgr'] = d['ranks']['quan_ly']
    if part == 'close':
        kit.need(_open_done(c, today), 'Chưa nhận quỹ đầu ca thì chưa bàn giao được.')
        busy = [t for t in c['tasks'] if t.get('career') == ID and t['status'] not in ('completed', 'referred', 'cancelled') and t.get('at', 0) > 0]
        kit.need(not busy, 'Còn khách đang làm dở, xong rồi mới bàn giao nhé.')
    steps, key = shift_steps(today['day'], part, today['mgr'])
    field = part + '_at'
    at = today[field]
    kit.need(at < len(steps), 'Đã nhận quỹ đầu ca.' if part == 'open' else 'Đã bàn giao xong.')
    st = steps[at]
    kit.need(isinstance(p.get('step'), str) and p['step'] == st['id'], 'Làm theo bước đang mở nhé.')
    value = _value(st, p.get('value'))
    if not _same(value, key[st['id']]):
        today['slips'] = min(today['slips'] + 1, 999)
        how = HOW_SHIFT.get(st['id'], 'Xem lại sổ rồi làm lại nhé.')
        return dict(message=f'Chưa đúng: {low(st["title"])}. {how}', correct=False)
    today[field] = at + 1
    if today[field] < len(steps):
        return dict(message='Đúng rồi. Tiếp: ' + low(steps[today[field]]['title']) + '.', correct=True)
    if part == 'open':
        return dict(message='💼 Đã nhận quỹ đầu ca. “Quầy số 3 xin chào!”' if key['open.sign'] == 'sign'
                    else '💼 Quỹ lệch sổ: đã lập biên bản với chị Hạnh, chưa ký nhận đủ. Quầy mở.', correct=True)
    today['handover'] = 1
    d['stats']['handovers'] += 1
    if not today['jobs']:   # an empty shift hands over an untouched float: no bonus, no step on the Quản lý ladder
        return dict(message='🧾 Bàn giao xong, quỹ khớp từng đồng. Hôm nay chưa phục vụ khách nào nên chưa có thưởng bàn giao.', correct=True)
    if d['stage'] == 'teller':
        d['prog']['quan_ly'] = min(d['prog']['quan_ly'] + 1, 10 ** 6)
    bonus = round(tc.HANDOVER_BONUS * (100 + tc.RANK_PCT * d['ranks']['quan_ly']) / 100)
    kit.money(s, c, bonus, 'Thưởng bàn giao quỹ đúng', f'handover-{c["day"]}', 'bonus')
    return dict(message=f'🧾 Bàn giao xong, quỹ khớp từng đồng. Thưởng {bonus} xu.', correct=True, celebrate=True)


HOW_SHIFT = {'open.count': 'Nhân mệnh giá với số tờ của từng phong bì rồi cộng lại.',
             'open.sign': 'So tổng vừa đếm với số trong sổ bàn giao.',
             'close.pending': 'Tìm dòng không có biên nhận khớp.',
             'close.cash': 'Quỹ đầu ca + tiền gửi vào − tiền đã chi; khoản treo chưa chi thì không trừ.'}


def _after(s: dict, c: dict, d: dict, result: dict) -> None:
    desk = d['desk']
    fired = desk['fired']
    kit.desk_tick(s, c, ID, desk, desk_scripts(c['day']), kit.daily(ID, c['day'], tc.MODS)['id'])
    if desk['fired'] > fired and desk['ev']:
        x = kit.desk_script(tc.DESK, desk['ev']['script'])
        result['message'] = f'{result.get("message", "")} 🔔 {x["emoji"]} {x["title"]}: quyết giúp nhé.'.strip()
        result['surprise'] = True


def on_task(s: dict, c: dict, t: dict) -> None:
    """A new customer: Bà Lựu's visit takes the arc's stage, a branch job the player's rank in that branch."""
    if t.get('career') != ID or t.get('status') != 'new' or t.get('at') != 0:
        return
    d = _data(c)
    if luu_slot(t['day'], _slot(t)):
        t['arc'] = d['arc']['stage']
    t['rk'] = min(3, rank_of(d, t['job'])) if d['stage'] == 'teller' else 0
    t['pct'] = _pct(d, t['job'])


def on_start(s: dict, c: dict) -> None:
    d = _data(c)
    mod = kit.daily(ID, c['day'], tc.MODS)
    kit.desk_start(s, c, ID, d['desk'], desk_scripts(c['day']), mod['id'], c['life'].get('mode') == 'festival')


def on_close(s: dict, c: dict) -> dict:
    d = _data(c)
    today = d['today']
    note = kit.desk_close(s, c, ID, d['desk'], tc.DESK, _hook)
    lines = [f'Quầy số 3: {today["jobs"]} khách xong, {today["good"]} khách đạt từ {tc.GOOD}%. Thưởng: {today["bonus"]} xu.']
    if today['good'] and not today['counted'] and d['last_active_day'] < c['day']:
        d['stats']['active_days'] += 1
        today['counted'] = 1
        d['last_active_day'] = c['day']
    handed = _close_done(today) if today['day'] == c['day'] else False
    if today['jobs'] and not handed:
        lines.append('🧾 Chưa bàn giao quỹ cuối ca: chị Hạnh phải đếm lại thay bạn, ngày này không tính vào tập sự hay lên chức.')
        kit.review(s, c, kit.npc_id(ID, tc.MENTOR), 2, 'Về mà không bàn giao quỹ, chị phải đếm lại cả két.', f'handover-miss-{c["day"]}')
    if d['stage'] == 'training' and handed and today['good'] >= tc.TRAINING_GOOD and d['last_train_day'] < c['day']:
        d['training'] += 1
        d['last_train_day'] = c['day']
        if d['training'] >= tc.TRAINING:
            d['stage'] = 'teller'
            c['xp'] += 10
            lines.append('🪪 Chị Hạnh tháo chữ “Tập sự” khỏi bảng tên: từ mai bạn đứng Quầy số 3 một mình. Chọn nhánh nghề khi muốn.')
        else:
            lines.append(f'👩‍💼 Một ca kèm cặp đạt. Còn {tc.TRAINING - d["training"]} ca nữa.')
    if d['stage'] == 'teller' and handed:
        nr = next_rank(d, d['branch'])
        if nr and not nr[2] and d['prog'][d['branch']] >= nr[1]:
            lines.append(_promote(s, c, d, d['branch']))
        elif nr and nr[2] and d['prog'][d['branch']] >= nr[1]:
            lines.append(f'📝 Đủ điều kiện thi lên {tc.BRANCHES[d["branch"]]["ladder"][nr[0]]}: vào quầy bấm Thi lên chức.')
    if note:
        lines.append(note)
    return dict(lines=lines, note='Lương ca do hợp đồng chi trả. Tiền ở quầy là tiền của ngân hàng, không phải tiền của bạn.')


def known_request(c: dict, t: dict) -> str:
    _, _, _, title, opening = brief(t['day'], _slot(t), t['job'], t.get('arc', -1), t.get('rk', 0))
    return f'{title}: {opening}'


def hint(c: dict, t: dict) -> str:
    if not t.get('known'):
        return 'Bấm nhận yêu cầu để xem phiếu của khách.'
    _, steps, _ = _active(t)
    return steps[t['at']]['evidence'] if t['at'] < len(steps) else 'Khách đã xong; mời khách tiếp theo.'


def feedback(c: dict, t: dict) -> dict:
    _, steps, _ = _active(t)
    n = len(t['errors'])
    if t.get('shadow'):
        return dict(criteria=[dict(key='steps', label='Đúng quy trình', score=5, note='Chị Hạnh làm, bạn quan sát.'),
                              dict(key='care', label='Chu đáo với khách', score=4, note='Học việc.')])
    return dict(criteria=[dict(key='steps', label='Đúng quy trình', score=max(1, 5 - n), note=f'{len(steps) - n}/{len(steps)} bước đúng ngay lần đầu.'),
                          dict(key='care', label='Chu đáo với khách', score=max(1, min(5, (t['quality'] + 19) // 20)), note=f'Chất lượng {t["quality"]}%.')])


def public_task(t: dict) -> dict:
    v = deepcopy({k: x for k, x in t.items() if not k.startswith('_')})
    b, _, _, title, opening = brief(t['day'], _slot(t), t['job'], t.get('arc', -1), t.get('rk', 0))
    v['title'] = title
    v['opening'] = opening
    v['needs'] = deepcopy(b) if t['known'] else None
    if v['needs']:
        v['needs'].pop('variant', None)   # the withdrawal's case is the check step's answer: kept on the server
    j = tc.JOBS[t['job']]
    v['job_info'] = dict(id=t['job'], label=j[0], emoji=j[1], branch=j[2])
    return v


def public_data(c: dict) -> dict:
    d = deepcopy(kit.data(c))
    st = d['stats']
    kinds = sum(1 for k in tc.JOB_IDS if st['kinds'].get(k, 0) > 0)
    milestones = [dict(m, achieved=st['good'] >= m['jobs'] and st['active_days'] >= m['days'] and kinds >= m['kinds']) for m in tc.MILESTONES]
    branches = []
    for b, row in tc.BRANCHES.items():
        nr = next_rank(d, b)
        need = row.get('needs')
        branches.append(dict(id=b, label=row['label'], emoji=row['emoji'], rank=d['ranks'][b], title=row['ladder'][d['ranks'][b]],
                             ladder=list(row['ladder']), prog=d['prog'][b], next=(dict(to=nr[0], title=row['ladder'][nr[0]], need=nr[1], exam=nr[2]) if nr else None),
                             open=not need or d['ranks'][need[0]] >= need[1]))
    d['progress'] = dict(earned=[m['id'] for m in milestones if m['achieved']], milestones=milestones, kinds=kinds,
                         title=title_of(d), stage_label=tc.STAGE_LABEL[d['stage']], training=tc.TRAINING, branches=branches)
    d['desk'] = kit.desk_public(d['desk'], tc.DESK, ID, c)
    mod = kit.daily(ID, c['day'], tc.MODS)
    d['mod'] = dict(id=mod['id'], emoji=mod['emoji'], label=mod['label'], hint=mod['hint'])
    today = d['today'] if d['today']['day'] == c['day'] else _today(c['day'])
    shift = {}
    for part in ('open', 'close'):
        steps, _ = shift_steps(c['day'], part, today['mgr'] if today['open_at'] else d['ranks']['quan_ly'])
        at = today[part + '_at']
        shift[part] = dict(at=at, total=len(steps), done=at >= len(steps), step=deepcopy(steps[at]) if at < len(steps) else None)
    d['shift'] = shift
    ex = d['exam']
    if d['stage'] == 'exam' and ex and not ex['done']:
        parts, _ = exam_parts(ex['attempt'], ex['day'])
        d['exam_view'] = dict(at=ex['at'], total=len(parts), step=deepcopy(parts[ex['at']]), hints=ex['hints'], started=ex['started'])
    else:
        d['exam_view'] = None
    d['exam_retry'] = bool(d['stage'] == 'exam' and ex and ex['done'] and ex['day'] >= c['day'])
    rv = d['review']
    if rv and not rv['done']:
        parts, _ = review_parts(rv['branch'], rv['to'], rv['day'], d['record'])
        d['review_view'] = dict(at=rv['at'], total=len(parts), step=deepcopy(parts[rv['at']]), title=tc.BRANCHES[rv['branch']]['ladder'][rv['to']])
    else:
        d['review_view'] = None
    nr = next_rank(d, d['branch']) if d['stage'] == 'teller' else None
    d['review_ready'] = bool(nr and nr[2] and d['prog'][d['branch']] >= nr[1] and not (rv and not rv['done'])
                             and not (rv and rv['done'] and rv['day'] >= c['day'] and rv['branch'] == d['branch']))
    d['lessons'] = [dict(id=x['id'], emoji=x['emoji'], title=x['title'], text=x['text'], ask=x['ask'],
                         options=_opts(kit.rng(ID, 'lesson', x['id']), x['options']), done=x['id'] in d['learned']) for x in tc.LESSONS]
    arc = d['arc']
    d['arc_view'] = dict(stage=arc['stage'], total=tc.ARC_N, goal=tc.ARC_GOAL, saved=min(tc.ARC_GOAL, arc_saved_before(arc['stage'])) if arc['stage'] < tc.ARC_N else tc.ARC_GOAL,
                         title=tc.ARC_STAGES[min(arc['stage'], tc.ARC_N)]['title'], done=arc['stage'] >= tc.ARC_N, cup=arc['cup'])
    return d


def tea_cart(s: dict) -> bool:
    """🍵 Bà Lựu's savings arc is done: her new cart stands by the trà đá stall in the 2.5D street (journey.tea_cart)."""
    c = (s.get('careers') or {}).get(ID)
    d = (c.get('ext') or {}).get('data') if isinstance(c, dict) else None
    return isinstance(d, dict) and isinstance(d.get('arc'), dict) and d['arc'].get('stage', 0) >= tc.ARC_N


def content() -> dict:
    return dict(
        notebook=tc.NOTEBOOK, denoms=list(tc.DENOM_KEYS), bundle=tc.BUNDLE, tray_max=tc.TRAY_MAX,
        jobs=[dict(id=k, label=v[0], emoji=v[1], branch=v[2]) for k, v in tc.JOBS.items()],
        branches=[dict(id=k, label=v['label'], emoji=v['emoji'], ladder=list(v['ladder'])) for k, v in tc.BRANCHES.items()],
        record=[dict(id=k, label=tc.RECORD_LABEL[k]) for k in tc.RECORD_KEYS], exam_fast=tc.EXAM_FAST, training=tc.TRAINING,
        intro=dict(title='Một ca ở Quầy số 3',
                   lead='Phòng giao dịch Bến Chợ của Ngân hàng Phố. Khách là người trong phố: bà Lựu trà đá, dì Bảy cơm tấm, bác Lâm phở, chị Thơ tiệm album… '
                        'Mỗi khách năm bước: nhận yêu cầu, kiểm tra thông tin, xử lý tiền, xác nhận, giao biên nhận. Tiền ở quầy là tiền của ngân hàng, không phải tiền của bạn. '
                        f'Học ba bài ngắn, thi thực hành ba phần, nhận bảng tên, {tc.TRAINING} ca có chị Hạnh kèm rồi đứng quầy một mình.',
                   short=[['💵', 'Rút, đổi, chuyển tiền'], ['🐷', 'Tiết kiệm theo mục tiêu'], ['🧾', 'Nhận quỹ, bàn giao quỹ']],
                   work=[['💵', 'Rút tiền: kéo tờ tiền vào khay cho đúng số, theo lời dặn của khách'], ['🪙', 'Đổi tiền lẻ: đúng số cọc chủ quán cần'],
                         ['🔁', 'Chuyển tiền: đúng người nhận theo tên, ảnh và nghề'], ['🐷', 'Gửi tiết kiệm theo mục tiêu: sửa nhà, mua xe, mở quán'],
                         ['🏧', 'Tiếp quỹ ATM: đúng khe, đúng mệnh giá, hai người ký'], ['🧾', 'Bàn giao cuối ca: khớp biên nhận, tìm giao dịch treo']],
                   meet=[['👩‍💼', 'Chị Hạnh trưởng quầy, người kèm bạn'], ['🙃', 'Anh Quân ca sáng, hay nhờ vả'], ['🍵', 'Bà Lựu đang để dành mua xe trà mới'],
                         ['📈', 'Giám đốc Vy và bảng chỉ tiêu']],
                   stars=[['🪪', 'Đối chiếu đủ tên, ảnh, giấy tờ trước khi chi'], ['🔁', 'Đọc lại cho khách gật đầu rồi mới bấm chuyển'],
                          ['🧾', 'Bàn giao quỹ cuối ca, khớp từng đồng']]))


# ---------------------------------------------------------------- validation
def _step_ok(st: dict, value, want) -> bool:
    if st['type'] == 'tray':
        return isinstance(value, dict) and tray_norm(value) == value and tray_problem(value, want) is None
    return _same(value, want)


def validate_task(t: dict, original: dict) -> None:
    for k in FIXED:
        kit.need(_same(t.get(k), original.get(k)), 'Dữ kiện phiếu quầy bị thay đổi: ' + k)
    kit.need(t.get('job') in tc.JOBS, 'Loại việc ở quầy không hợp lệ.')
    arc = t.get('arc')
    kit.need(type(arc) is int and -1 <= arc <= tc.ARC_N and (arc == -1 or luu_slot(t['day'], _slot(t))), 'Chặng tiết kiệm của bà Lựu sai.')
    kit.integer(t.get('rk'), 0, 3)
    kit.need(t.get('pct') in PCTS, 'Mức thưởng của phiếu quầy sai.')
    _, steps, key = _active(t)
    ids = [st['id'] for st in steps]
    at = kit.integer(t.get('at'), 0, len(steps))
    kit.need(t.get('stage') == ('done' if at == len(steps) else 'work'), 'Tiến trình phiếu quầy sai.')
    shadow = t.get('shadow', False)
    kit.need(type(shadow) is bool and (not shadow or (at == len(steps) and t.get('status') == 'referred')), 'Phiếu học việc sai.')
    kit.need(at == 0 or t['known'] or shadow, 'Chưa nhận yêu cầu của khách.')
    work = t.get('work')
    kit.need(isinstance(work, dict) and set(work) == set(ids[:at]), 'Các bước đã làm không liên tục.')
    kit.need(all(_step_ok(st, work[st['id']], key[st['id']]) for st in steps[:at]), 'Kết quả bước ở quầy sai.')
    errors = t.get('errors')
    kit.need(isinstance(errors, list) and all(isinstance(e, str) for e in errors), 'Nhật ký lỗi quầy sai.')
    kit.need(len(errors) == len(set(errors)) and set(errors) <= set(ids[:min(at + 1, len(ids))]), 'Nhật ký lỗi quầy sai.')
    wrong = kit.integer(t.get('wrong'), 0, 100000)
    kit.need(len(errors) <= wrong <= t.get('mistakes', 0) and (wrong == 0) == (not errors), 'Số lần làm lại sai.')
    kit.need(t.get('quality') == _quality(wrong), 'Điểm chất lượng quầy không khớp.')
    paid = 0 if shadow or at < len(steps) else _bonus(t)
    kit.need(type(t.get('paid')) is int and t['paid'] == paid, 'Tiền thưởng quầy không khớp.')
    kit.need(isinstance(t.get('lines'), list) and len(t['lines']) <= LINES and all(isinstance(x, str) and len(x) < 500 for x in t['lines']),
             'Nhật ký quầy sai.')
    kit.need((t['stage'] == 'done') == (t.get('status') in ('completed', 'referred')), 'Phiếu quầy chưa xong mà đã hoàn tất.')
    kit.need(at == 0 or t.get('status') != 'new', 'Phiếu quầy sai trạng thái.')


def validate_data(c: dict) -> None:
    d = kit.data(c)
    base = initial()
    kit.need(isinstance(d, dict) and set(d) == set(base), 'Sổ quầy giao dịch sai.')
    kit.need(type(d['intro']) is bool and d['stage'] in tc.STAGES, 'Sổ quầy giao dịch sai.')
    lessons = [x['id'] for x in tc.LESSONS]
    kit.need(isinstance(d['learned'], list) and len(set(d['learned'])) == len(d['learned']) and set(d['learned']) <= set(lessons), 'Bài học việc sai.')
    kit.need((d['stage'] == 'learn') == (len(d['learned']) < len(lessons)), 'Bài học việc sai.')
    ex = d['exam']
    if ex is not None:
        kit.need(isinstance(ex, dict) and set(ex) == {'attempt', 'day', 'at', 'started', 'hints', 'got', 'done', 'secs'}, 'Bài thi thực hành sai.')
        kit.integer(ex['attempt'], 1, 10 ** 6)
        kit.integer(ex['day'], 1, 10 ** 7)
        kit.need(type(ex['started']) in (int, float) and 0 <= ex['started'] < 10 ** 11, 'Bài thi thực hành sai.')
        kit.integer(ex['hints'], 0, 9)
        kit.integer(ex['secs'], 0, 10 ** 6)
        n = len(exam_parts(ex['attempt'], ex['day'])[0])
        kit.integer(ex['at'], 0, n)
        kit.need(isinstance(ex['got'], list) and len(ex['got']) == ex['at'] and all(type(g) is bool for g in ex['got']), 'Bài thi thực hành sai.')
        kit.need(type(ex['done']) is bool and ex['done'] == (ex['at'] == n), 'Bài thi thực hành sai.')
    kit.need(d['stage'] in ('learn', 'exam') or ex is None or ex['done'], 'Bài thi thực hành sai.')
    kit.need(isinstance(d['exams'], list) and len(d['exams']) <= 10, 'Lịch sử thi sai.')
    for row in d['exams']:
        kit.need(isinstance(row, dict) and set(row) == {'attempt', 'day', 'passed', 'secs', 'hints', 'got'} and type(row['passed']) is bool
                 and isinstance(row['got'], list) and len(row['got']) <= 3 and all(type(g) is bool for g in row['got']), 'Lịch sử thi sai.')
        for k in ('attempt', 'day', 'secs', 'hints'):
            kit.integer(row[k], 0, 10 ** 7)
    badge = d['badge']
    kit.need((badge is None) == (d['stage'] in ('learn', 'exam')), 'Bảng tên sai.')
    if badge is not None:
        kit.need(isinstance(badge, dict) and set(badge) == {'day', 'fast', 'clean', 'secs'} and type(badge['fast']) is bool and type(badge['clean']) is bool, 'Bảng tên sai.')
        kit.integer(badge['day'], 1, 10 ** 7)
        kit.integer(badge['secs'], 0, 10 ** 6)
    kit.integer(d['training'], 0, tc.TRAINING)
    kit.need((d['stage'] == 'teller') == (d['training'] >= tc.TRAINING), 'Ca kèm cặp sai.')
    kit.integer(d['last_train_day'], 0, 10 ** 7)
    kit.need(d['branch'] in tc.BRANCH_IDS, 'Nhánh nghề sai.')
    for k in ('ranks', 'prog'):
        kit.need(isinstance(d[k], dict) and set(d[k]) == set(tc.BRANCH_IDS), 'Nhánh nghề sai.')
    for b, row in tc.BRANCHES.items():
        kit.integer(d['ranks'][b], 0, len(row['ladder']) - 1)
        kit.integer(d['prog'][b], 0, 10 ** 6)
    kit.need(d['stage'] == 'teller' or (not any(d['ranks'].values()) and d['branch'] == 'giao_dich'), 'Nhánh nghề sai.')
    need = tc.BRANCHES['quan_ly']['needs']
    kit.need(d['ranks'][need[0]] >= need[1] or (d['ranks']['quan_ly'] == 0 and d['branch'] != 'quan_ly'), 'Nhánh quản lý chưa mở.')
    rv = d['review']
    if rv is not None:
        kit.need(isinstance(rv, dict) and set(rv) == {'branch', 'to', 'day', 'at', 'got', 'done', 'passed'} and rv['branch'] in tc.BRANCH_IDS, 'Bài xét lên chức sai.')
        kit.need((rv['branch'], rv['to']) in tc.RANK_NEEDS and tc.RANK_NEEDS[(rv['branch'], rv['to'])][1], 'Bài xét lên chức sai.')
        kit.integer(rv['day'], 1, 10 ** 7)
        n = len(review_parts(rv['branch'], rv['to'], rv['day'], d['record'])[0])
        kit.integer(rv['at'], 0, n)
        kit.need(isinstance(rv['got'], list) and len(rv['got']) == rv['at'] and all(type(g) is bool for g in rv['got']), 'Bài xét lên chức sai.')
        kit.need(type(rv['done']) is bool and rv['done'] == (rv['at'] == n) and type(rv['passed']) is bool and (rv['passed'] <= rv['done']), 'Bài xét lên chức sai.')
        kit.need(rv['passed'] == (rv['done'] and all(rv['got'])), 'Bài xét lên chức sai.')
    rec = d['record']
    kit.need(isinstance(rec, dict) and set(rec) == set(tc.RECORD_KEYS), 'Sổ ghi nhận sai.')
    for v in rec.values():
        kit.integer(v, 0, 10 ** 6)
    arc = d['arc']
    kit.need(isinstance(arc, dict) and set(arc) == {'stage', 'done_day', 'cup'} and type(arc['cup']) is bool, 'Sổ tiết kiệm của bà Lựu sai.')
    kit.integer(arc['stage'], 0, tc.ARC_N)
    kit.integer(arc['done_day'], 0, 10 ** 7)
    kit.need((arc['done_day'] > 0) == (arc['stage'] >= tc.ARC_N) and (not arc['cup'] or arc['stage'] >= tc.ARC_N), 'Sổ tiết kiệm của bà Lựu sai.')
    kit.integer(d['last_active_day'], 0, 10 ** 7)
    today = d['today']
    kit.need(isinstance(today, dict) and set(today) == set(base['today']), 'Số liệu quầy sai.')
    for v in today.values():
        kit.integer(v, 0, 10 ** 9)
    for k in ('counted', 'handover'):
        kit.integer(today[k], 0, 1)
    kit.integer(today['mgr'], 0, len(tc.BRANCHES['quan_ly']['ladder']) - 1)
    kit.integer(today['slips'], 0, 999)
    kit.integer(today['open_at'], 0, len(shift_steps(today['day'], 'open')[0]))
    kit.integer(today['close_at'], 0, len(shift_steps(today['day'], 'close', today['mgr'])[0]))
    kit.need(today['good'] <= today['jobs'] and (today['close_at'] == 0 or today['open_at'] == len(shift_steps(today['day'], 'open')[0])), 'Số liệu quầy sai.')
    st = d['stats']
    kit.need(isinstance(st, dict) and set(st) == set(base['stats']), 'Số liệu quầy sai.')
    for k, v in st.items():
        if k != 'kinds':
            kit.integer(v, 0, 10 ** 9)
    kit.need(isinstance(st['kinds'], dict) and set(st['kinds']) == set(tc.JOB_IDS), 'Số liệu loại việc sai.')
    for v in st['kinds'].values():
        kit.integer(v, 0, 10 ** 9)
    kit.need(st['good'] <= st['jobs'] and sum(st['kinds'].values()) == st['good'] and st['active_days'] <= st['good'], 'Tiến trình nghề ở quầy sai.')
    kit.desk_validate(d['desk'], tc.DESK)


SITUATIONS = [
    dict(id='TL-S01', title='Bà cụ muốn rút hết tiền đưa “cán bộ” qua điện thoại', npc=tc.MEN, tone='tense', min_day=3,
         opening='Cụ Mến vừa nghe điện thoại vừa run: “Cán bộ công an bảo bà rút hết sổ chuyển vào tài khoản an toàn, không thì bị bắt.”',
         facts=[dict(id='call', title='Cuộc gọi', source='Lời cụ', text='Người gọi xưng công an, dặn không được nói với ai, kể cả ngân hàng.'),
                dict(id='acct', title='Tài khoản nhận', source='Phiếu chuyển', text='Tài khoản nhận đứng tên một cá nhân lạ ở tỉnh khác.'),
                dict(id='rule', title='Quy định quầy', source='Sổ tay quầy', text='Nghi lừa đảo thì được tạm dừng, giải thích, mời người thân, báo trưởng quầy.')],
         options=[dict(id='stop', label='Tạm dừng, giải thích đây là chiêu lừa, gọi người thân cụ, báo chị Hạnh', requires=['call', 'acct'], cost=0, reward=20, quality='good', stars=5,
                       review='Cô cậu ở quầy giữ bà lại, gọi cho con bà. Suýt mất cả đời dành dụm.', outcome='Con trai cụ tới, gọi lại số kia thì máy đã tắt. Cụ ôm bạn khóc.',
                       perspectives=[dict(who='Cụ Mến', emoji='👵', text='Bà sợ lắm, may có con giữ bà lại.'),
                                     dict(who='Chị Hạnh', emoji='👩‍💼', text='Chậm một chút mà cứu được cả sổ tiết kiệm.')]),
                  dict(id='do', label='Làm theo yêu cầu, tiền của cụ cụ quyết', requires=[], cost=0, reward=0, quality='bad', stars=1,
                       review='Ngân hàng thấy bà cụ run run mà vẫn chuyển hết.', outcome='Tiền đi mất. Hôm sau cả phố biết chuyện.',
                       perspectives=[dict(who='Cụ Mến', emoji='👵', text='Bà mất hết rồi.'), dict(who='Con trai cụ', emoji='🧔', text='Sao không ai hỏi một câu?')]),
                  dict(id='refuse', label='Từ chối thẳng, mời cụ về', requires=['rule'], cost=0, reward=5, quality='ok',
                       outcome='Cụ về, nhưng kẻ gian gọi lại, dẫn cụ sang chi nhánh khác.',
                       perspectives=[dict(who='Cụ Mến', emoji='👵', text='Ngân hàng không cho, bà đi chỗ khác.'),
                                     dict(who='Chị Hạnh', emoji='👩‍💼', text='Từ chối chưa đủ, phải giải thích và gọi người thân.')])],
         lesson='Nghi lừa đảo thì chậm lại, giải thích và gọi người thân; không chỉ từ chối.'),
    dict(id='TL-S02', title='Chủ quán nhờ “làm ngơ” khoản tiền mặt lớn', npc=tc.TAI, tone='tense', min_day=4,
         opening='Ông Tài đặt túi 900 triệu tiền mặt: “Gửi giúp tôi, chia làm mười lần cho khỏi phải khai.”',
         facts=[dict(id='split', title='Chia nhỏ', source='Lời khách', text='Khách muốn chia nhỏ để tránh khai báo nguồn tiền.'),
                dict(id='rule', title='Quy định', source='Sổ tay quầy', text='Giao dịch tiền mặt lớn phải khai nguồn gốc; cố ý chia nhỏ phải báo kiểm soát.')],
         options=[dict(id='report', label='Giải thích quy định, mời khai nguồn tiền, báo kiểm soát việc chia nhỏ', requires=['split', 'rule'], cost=0, reward=20, quality='good',
                       outcome='Ông Tài bực bội khai nguồn tiền bán đất. Hồ sơ đủ, giao dịch đi một lần.',
                       perspectives=[dict(who='Ông Tài', emoji='🕶️', text='Rắc rối thật, nhưng thôi, đất của tôi mà.'),
                                     dict(who='Giám đốc Vy', emoji='📈', text='Làm đúng thế này thì chi nhánh không phải lo.')]),
                  dict(id='split', label='Chia mười lần cho ông như ông muốn', requires=[], cost=0, reward=0, quality='bad', stars=1,
                       review='Quầy nhận chia nhỏ để lách khai báo.', outcome='Đợt kiểm tra cuối quý phát hiện, chi nhánh bị nhắc nhở.',
                       perspectives=[dict(who='Ông Tài', emoji='🕶️', text='Thấy chưa, quen biết là được.'), dict(who='Kiểm soát viên', emoji='🔍', text='Mười giao dịch cách nhau năm phút, ai nhìn cũng thấy.')])],
         lesson='Không giúp khách lách quy định khai báo, dù khách quen hay hứa hẹn gì.'),
    dict(id='TL-S03', title='Bà Lựu muốn ghi tên cháu vào sổ cho “sau này tiện”', npc=tc.LUU, tone='gentle', min_day=3,
         opening='Bà Lựu hỏi: “Con ghi luôn tên thằng cháu đồng chủ sổ được không, bà già rồi, lỡ có chuyện gì.”',
         facts=[dict(id='own', title='Chủ sổ', source='Hồ sơ', text='Đồng chủ sổ thì người kia cũng rút được tiền.'),
                dict(id='nephew', title='Cháu trai', source='Lời bà', text='Tuần trước cháu vừa xin bà rút tiền cho vay.')],
         options=[dict(id='explain', label='Giải thích đồng chủ sổ là gì; gợi ý giữ sổ đứng tên bà, làm giấy ủy quyền khi cần', requires=['own', 'nephew'], cost=0, reward=15, quality='good', stars=5,
                       review='Con giải thích kỹ, bà hiểu rồi, sổ cứ để tên bà.', outcome='Bà giữ sổ tên mình, hẹn khi nào cần thì làm ủy quyền.',
                       perspectives=[dict(who='Bà Lựu', emoji='🍵', text='Già rồi mà vẫn tự lo được, vui.'), dict(who='Chị Hạnh', emoji='👩‍💼', text='Nói rõ để khách tự quyết, đúng nghề.')]),
                  dict(id='add', label='Ghi luôn tên cháu cho bà vui', requires=[], cost=0, reward=0, quality='bad',
                       outcome='Hai tuần sau cháu ra rút một nửa sổ.',
                       perspectives=[dict(who='Bà Lựu', emoji='🍵', text='Bà đâu biết nó rút được.'), dict(who='Cháu trai', emoji='🛵', text='Bà cho rồi mà.')])],
         lesson='Giải thích rõ quyền của từng người trên sổ để khách tự quyết.'),
]


SPEC = dict(
    id=ID, prefix='tl_', category='office', people=PEOPLE,
    meta=dict(short='Ngân hàng', place='Phòng giao dịch Bến Chợ · Ngân hàng Phố', tagline='Quầy số 3 xin chào!', icon='coin',
              color='#1f6f6b', light='#e3f3ef', weather='Máy gọi số kêu “ting” đều đều', work='Phiếu giao dịch', station='Quầy số 3',
              greeting='Chị Hạnh kéo ghế cho bạn ở Quầy số 3: nhận quỹ đầu ca, mời khách, bàn giao cuối ca. Tiền ở quầy là tiền của ngân hàng.',
              caption='Một quầy giao dịch, một máy đếm, một khay tiền', map_label='NGÂN HÀNG PHỐ · BẾN CHỢ'),
    staff=[('Chị Hạnh', 'counter', 'Trưởng quầy, đếm tiền nhanh như máy.', 84, 92), ('Anh Quân', 'ops', 'Phụ trách ATM, tay nhanh miệng nhanh.', 88, 78)],
    roles={'counter': 'Quầy giao dịch', 'ops': 'Vận hành ATM'}, tip=0, physical=PHYSICAL, free_actions=FREE, no_tick=NO_TICK,
    activity=('🏦', 'Một ca ở Quầy số 3', [('Đầu ca', 'Đếm quỹ, ký nhận'), ('Rút tiền', 'Đúng số, đúng lời dặn'), ('Chuyển tiền', 'Đúng người nhận'),
                                         ('Cuối ca', 'Bàn giao khớp từng đồng')],
              ['Nhận quỹ đầu ca', 'Mời khách, kiểm tra thông tin', 'Xếp tiền vào khay', 'Bàn giao cuối ca']),
    stories=[('Chiếc ghế xoay ở Quầy số 3', ('Chiếc ghế xoay ở Quầy số 3 kêu cót két, chị Hạnh bảo nó đã qua mười hai mùa lương hưu.',
                                              'Bạn đếm cọc tiền đầu tiên hai lần, tay hơi run.', 'Bà Lựu ghé qua, gật gù: “Con bé cẩn thận, bà gửi chỗ này được.”')),
             ('Chiếc xe trà mới', ('Bà Lựu mang túi vải tới góp tháng đầu, thiếu ba chục.', 'Cháu trai xin rút, bà ngồi im rất lâu ở ghế chờ.',
                                   'Chiếc xe trà inox đứng dưới gốc bàng, ly trà đầu tiên bà mời bạn.')),
             ('Hai người cùng tên', ('Hai anh Nguyễn Văn An, một người bán bánh mì, một người sửa xe đạp.', 'Chị Thơ giơ điện thoại có ảnh.',
                                     'Bạn đọc lại tên, nghề, đuôi tài khoản; chị Thơ gật đầu rồi mới bấm chuyển.'))],
    review_asides=['Đếm tiền trước mặt mình, yên tâm.', 'Đọc lại tên người nhận rõ ràng.', 'Quầy số 3 lúc nào cũng tươi.'], situations=SITUATIONS,
    more_line='Máy gọi số vừa kêu: một khách nữa tới Quầy số 3.', open_line='Phòng giao dịch Bến Chợ mở cửa. Máy gọi số kêu “ting”: Quầy số 3 xin chào!',
    guide='Nhận quỹ đầu ca, rồi từng khách năm bước: nhận yêu cầu, kiểm tra thông tin, xử lý tiền, xác nhận, giao biên nhận. Cuối ca bàn giao quỹ. '
          'Học việc ba bài, thi thực hành ba phần, ca kèm cặp rồi đứng quầy một mình; sau đó chọn nhánh nghề.',
    employment=dict(postings=[dict(id='teller-benchu', org='Phòng giao dịch Bến Chợ, Ngân hàng Phố', kind='company', title='Giao dịch viên Quầy số 3',
                                   salary=(56, 70), probation_days=3, wants=['careful', 'numbers', 'communication'],
                                   perks=['Chị Hạnh kèm những ca đầu', 'Thưởng nhỏ mỗi khách, theo chất lượng', 'Bốn nhánh nghề để lên chức'],
                                   culture='Đếm hai lần, đọc lại một lần, không ai ký thay ai.',
                                   stages=['cv', 'interview'], questions=['tl_twin', 'tl_quota', 'mistake'], reference=False)],
                    questions={'tl_twin': dict(text='Khách chuyển tiền cho “Nguyễn Văn An”, danh sách có hai người cùng tên. Bạn làm gì?', options=[
                                   dict(id='three', label='So cả tên, ảnh và một chi tiết khác; đọc lại cho khách xác nhận', score=3, note='Đúng cách đối chiếu người nhận.'),
                                   dict(id='first', label='Chọn người đầu tiên trong danh sách', score=0, note='Dễ chuyển nhầm người.'),
                                   dict(id='ask', label='Hỏi khách “người nào?” rồi làm theo', score=1, note='Khách cũng có thể nhầm.')]),
                               'tl_quota': dict(text='Sếp giao chỉ tiêu bán bảo hiểm, khách trước mặt không cần. Bạn làm gì?', options=[
                                   dict(id='honest', label='Tư vấn đúng nhu cầu, ghi lý do; tìm khách khác có nhu cầu', score=3, note='Giữ được niềm tin của khách.'),
                                   dict(id='sell', label='Mời bằng được cho đủ chỉ tiêu', score=0, note='Khách sẽ quay lại đòi hủy.'),
                                   dict(id='skip', label='Không làm chỉ tiêu nữa', score=1, note='Thẳng thắn nhưng chưa tìm cách.')])}),
)
