"""🏦 Ngân hàng Phố, phần thêm 22/10: hạng tiết kiệm, hạn mức thẻ theo thu nhập, vay nhập hàng (game/bank.py holds the bank).

* 🐷 Hạng tiết kiệm (owner 22/10, feedback #480: "tiền gửi nếu muốn nhiêu tiền phải bắt mua bảo hiểm hoặc nâng cấp (ban
  đầu gửi 10m, xong nâng lên cho gửi 100m, 1 tỷ,...)"): the savings (sổ không kỳ hạn + sổ có kỳ hạn) take new money up
  to the tier's cap: Phổ thông 10 triệu, Bạc 100 triệu, Vàng 1 tỷ (the bank's own bounds stop near 1,05 tỷ: a demand
  pot of BAL_MAX and TERMS_MAX sổ of TERM_MAX). A tier is a deposit insurance package bought once (TIERS price, from the
  account or the cash in hand); a jump of two tiers pays both. Grandfathered: money already saved above the cap stays,
  keeps its interest and its tái tục; only NEW deposits are refused until the player upgrades (nothing is ever taken).
* 💳 Hạn mức thẻ (owner 22/10, feedback #481 "cho phép thêm cái cho vay nhé ... hoặc thẻ tín dụng nhé"): the card's
  limit follows the same rule as before (income × CARD_CYCLE × the score factor) with a cap of CARD_LIMIT_MAX instead
  of bank.LIMIT_MAX. The card itself keeps c['limit'] ≤ bank.LIMIT_MAX (an older build's validator); the full limit of
  THAT card (by its number) is kept here. "Xét lại hạn mức" once every REVIEW_DAYS (a credit inquiry) raises it.
* 📦 Vay nhập hàng (feedback #481: "nhập hàng khi ví không đủ tiền được không"): at a restock (🏪 Quầy riêng
  jr_quay_restock, 📦 Kho & nhập hàng inv_order / inv_order_cart, 🍼💊 order_stock) the part the shop's money lacks can
  be swiped on the card (bank.pay, card) or borrowed here, in the SAME command: the money goes into the shop and is spent
  at once (engine.money calls short() at the very payment, so exactly the shortfall is borrowed, never more). One
  repayment after STOCK_DAYS life days with a flat STOCK_BP fee. On the due day (and every morning after) the bank takes
  the account, then that shop's money (két/vốn quầy or the workplace fund), then the wallet only when it finishes the
  debt (never below 0). Unpaid: a late fee (STOCK_LATE_PCT, then again every LOAN_PERIOD days, at most NFEE_MAX), a
  miss on the record (bank.BAD_MISSES of them = nợ xấu, which blocks new credit and the card) and collector calls.
  The line: STOCK_MAX at most; 14 days of income × the score factor plus SAVINGS_SHARE % of the savings, less what is
  still owed. No inquiry per drawdown (a credit line, not an application).
* ⏳ 7 ngày (owner 22/10: "vay thì 7 ngày trở lên mới được vay"): a new card, any new loan and a restock loan need
  CREDIT_DAYS full life days lived (life_day > CREDIT_DAYS): the bank's own clock (bank.py counts every term, statement
  and installment in life days). A card opened before this rule keeps working.

Save: one OPTIONAL journey key j[KEY] (absent: tier Phổ thông, no raised limit, no restock loan). Not inside j['bank'],
whose keys, loan kinds and card limit 2.5.2.x validates one by one and would refuse; an older build ignores an unknown
journey key (tests/test_bank_plus.py loads such saves on `git archive d4eb098b`, 2.5.2.4). On such a build the card is
capped back to its c['limit'] and restock loans wait (no fee) until this build catches them up on the next morning.

    j['bank_plus'] = {'v': 1, 'tier': 0, 'card': None | {'no': '1234', 'limit': int}, 'review': 0, 'seq': 0,
                      'loans': [{'id', 'start', 'due', 'principal', 'interest', 'fees', 'nfee', 'paid', 'at', 'label'}]}
    at = {'k': 'quay', 'id': stall id} | {'k': 'career', 'id': career id}

Commands (jr_bk_*, through bank.apply): jr_bk_tier {tier, src, confirm}, jr_bk_card_review {confirm},
jr_bk_stock_pay {id, src}.
"""
from __future__ import annotations

import contextvars
from contextlib import contextmanager

from . import bank as bk
from . import bank_content as K

VERSION = 1
KEY = 'bank_plus'
CREDIT_DAYS = 7                 # owner 22/10: credit from 7 full life days
# (cap of savings, one-off price) per tier; owner 22/10: "ban đầu gửi 10m, xong nâng lên cho gửi 100m, 1 tỷ"
TIERS = ((10_000_000, 0), (100_000_000, 2_000_000), (1_000_000_000, 20_000_000))
CARD_LIMIT_MAX = 5_000_000      # the card limit's cap (was bank.LIMIT_MAX = 5.000 for every card)
REVIEW_DAYS = 7                 # "Xét lại hạn mức" at most once a week
STOCK_DAYS = 7                  # a restock loan is repaid once, after a week
STOCK_BP = 300                  # 3 % flat for the week (bank: personal 4 %, shop 3,5 % a week; card 0,5 %/day after grace)
STOCK_MAX = 10_000_000          # most principal owed at once (= bank.AMOUNT_MAX)
STOCK_LOANS_MAX = 5
STOCK_LATE_PCT, STOCK_LATE_MIN = 5, 3
NFEE_MAX = 4                    # late fees on one loan at most
SAVINGS_SHARE = 50              # % of the savings that back the restock line
COVER_VIA = ('wallet', 'card', 'loan')
COMMANDS = ('jr_bk_tier', 'jr_bk_card_review', 'jr_bk_stock_pay')
KEYS = {'v', 'tier', 'card', 'review', 'seq', 'loans'}
LOAN_KEYS = {'id', 'start', 'due', 'principal', 'interest', 'fees', 'nfee', 'paid', 'at', 'label'}


def _e():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _qy():
    from . import quay
    return quay


def initial() -> dict:
    return dict(v=VERSION, tier=0, card=None, review=0, seq=0, loans=[])


def get(s: dict) -> dict | None:
    j = s.get('journey')
    x = j.get(KEY) if isinstance(j, dict) else None
    return x if isinstance(x, dict) else None


def ensure(s: dict) -> dict:
    x = get(s)
    if x is None:
        s['journey'][KEY] = x = initial()
    return x


# ---------------------------------------------------------------- 🐷 hạng tiết kiệm
def tier(s: dict) -> int:
    x = get(s)
    return x['tier'] if x else 0


def cap(s: dict) -> int:
    return TIERS[tier(s)][0]


def save_room(s: dict, b: dict) -> int:
    return max(0, cap(s) - bk._savings_total(b))


def check_save(s: dict, b: dict, amount: int) -> None:
    """jr_bk_save: new money only up to the tier's cap (what is already saved above it stays: grandfathered)."""
    room = save_room(s, b)
    t = tier(s)
    _e().need(amount <= room, K.SAVE_CAP.format(name=K.TIER_NAMES[t], cap=bk._fmt(TIERS[t][0]), have=bk._fmt(bk._savings_total(b)),
                                                room=bk._fmt(room)), 'save_cap')


def tier_cost(s: dict, n: int) -> int:
    return sum(TIERS[k][1] for k in range(tier(s) + 1, n + 1))


# ---------------------------------------------------------------- ⏳ the 7-day rule
def young(s: dict) -> str | None:
    """Why the bank lends nothing yet (None: CREDIT_DAYS full life days lived)."""
    day = int(s['journey']['life_day'])
    if day > CREDIT_DAYS:
        return None
    return K.DECLINE['young'].format(days=CREDIT_DAYS, day=day, open=CREDIT_DAYS + 1)


# ---------------------------------------------------------------- 💳 the card's full limit
def full_limit(inc: dict, score: int) -> int:
    num, den = bk._factor(score)
    return max(bk.LIMIT_MIN, min(CARD_LIMIT_MAX, bk._floor10(inc['avg'] * bk.CARD_CYCLE * num // den)))


def card_limit(s: dict, b: dict) -> int:
    """The limit the card swipes against: its own c['limit'], or the raised one kept here for that card number."""
    c = b.get('card') if b else None
    if not c:
        return 0
    x = get(s)
    raised = x['card']['limit'] if x and x['card'] and x['card']['no'] == c['no'] else 0
    return max(c['limit'], raised)


def on_card_open(s: dict, b: dict, full: int) -> None:
    c = b['card']
    x = get(s)
    if full > c['limit'] or x:
        x = ensure(s)
        x['card'] = dict(no=c['no'], limit=full) if full > c['limit'] else None
        x['review'] = int(s['journey']['life_day'])


# ---------------------------------------------------------------- 📦 vay nhập hàng
def owed(ln: dict) -> int:
    return ln['principal'] + ln['interest'] + ln['fees'] - ln['paid']


def owed_total(s: dict) -> int:
    x = get(s)
    return sum(owed(ln) for ln in x['loans']) if x else 0


def overdue(s: dict, day: int) -> bool:
    x = get(s)
    return bool(x) and any(ln['due'] <= day for ln in x['loans'])


def stock_offer(s: dict, b: dict | None, inc: dict | None = None) -> dict:
    """The restock line today: {ok, why, text, limit, room}."""
    out = dict(ok=False, why='account', text='Mở tài khoản Ngân hàng Phố để dùng vay nhập hàng nhé.', limit=0, room=0,
               bp=STOCK_BP, days=STOCK_DAYS)
    if b is None:
        return out
    day = int(s['journey']['life_day'])
    x = get(s)
    why = young(s)
    if why:
        return dict(out, why='young', text=why)
    if b['bad_until'] > day:
        return dict(out, why='bad', text=K.DECLINE['bad'].format(until=bk.dy.on_day(s, b['bad_until'])))
    if bk._overdue(b, day) or overdue(s, day):
        return dict(out, why='overdue', text=K.DECLINE['overdue'])
    if b['score'] < bk.CARD_MIN_SCORE:
        return dict(out, why='score', text=K.DECLINE['score'].format(score=b['score'], need=bk.CARD_MIN_SCORE))
    if x and len(x['loans']) >= STOCK_LOANS_MAX:
        return dict(out, why='count', text=f'Bạn đang có {len(x["loans"])} khoản vay nhập hàng. Trả bớt một khoản rồi vay tiếp nhé.')
    inc = bk.income(s) if inc is None else inc
    num, den = bk._factor(b['score'])
    limit = min(STOCK_MAX, bk._floor10(inc['total'] * num // den + bk._savings_total(b) * SAVINGS_SHARE // 100))
    room = max(0, limit - sum(ln['principal'] for ln in (x['loans'] if x else ())))
    if room <= 0:
        text = ('Hạn mức vay nhập hàng đã dùng hết. Trả bớt khoản đang vay nhé.' if limit else
                f'Chưa có hạn mức: ngân hàng xét theo thu nhập {bk.INCOME_WINDOW} ngày gần nhất và tiền tiết kiệm của bạn.')
        return dict(out, why='room', text=text, limit=limit)
    return dict(out, ok=True, why=None, text='', limit=limit, room=room)


def draw(s: dict, amount: int, label: str, at: dict) -> dict:
    """A restock loan of `amount` xu (the caller puts the money into the shop)."""
    e = _e()
    b = bk.get(s)
    o = stock_offer(s, b)
    if not o['ok']:
        raise e.GameError(f'Ngân hàng chưa cho vay nhập hàng: {o["text"][0].lower() + o["text"][1:]}', 'credit_declined')
    e.need(amount <= o['room'], f'Hạn mức vay nhập hàng còn {bk._fmt(o["room"])} xu, chưa đủ {bk._fmt(amount)} xu.', 'credit_declined')
    day = int(s['journey']['life_day'])
    x = ensure(s)
    x['seq'] += 1
    ln = dict(id=f'S{x["seq"]}', start=day, due=day + STOCK_DAYS, principal=amount, interest=max(1, bk._ceil_div(amount * STOCK_BP, 10000)),
              fees=0, nfee=0, paid=0, at=dict(at), label=label[:60])
    x['loans'].append(ln)
    bk._log(b, day, 'loan', f'Giải ngân vay nhập hàng · {ln["label"]}', amount)
    return ln


def cover(s: dict, amount: int, via: str, label: str, at: dict) -> str:
    """Pay `amount` xu of a restock the shop cannot: a card swipe or a restock loan. Raises GameError when the bank says
    no. Returns the sentence for the result."""
    e = _e()
    e.need(via in ('card', 'loan'), 'Chọn quẹt thẻ hoặc vay nhập hàng nhé.')
    e.need(s['journey'].get('story'), 'Ngân hàng chỉ có trong chế độ hành trình.', 'story_only')
    b = bk.get(s)
    e.need(b is not None, 'Mở tài khoản Ngân hàng Phố trước nhé.', 'no_account')
    e.need(type(amount) is int and 0 < amount <= STOCK_MAX, f'Mỗi lần bù tối đa {bk._fmt(STOCK_MAX)} xu.')
    if via == 'card':
        bk.pay(s, amount, label, method='card', no_joint=True)
        return f'Quẹt thẻ •••• {b["card"]["no"]} {bk._fmt(amount)} xu, trả khi có sao kê.'
    ln = draw(s, amount, label, at)
    return f'Vay nhập hàng {bk._fmt(amount)} xu, trả {bk._fmt(owed(ln))} xu {bk.dy.on_day(s, ln["due"])}.'


# The career command being run with `cover` (engine._apply_action): engine.money and inventory call short() at the payment.
_ARMED = contextvars.ContextVar('bank_plus_cover', default=None)


@contextmanager
def armed(s: dict, career: str, p: dict):
    """Yields the payload without `cover`. With cover in COVER_VIA, a payment of `career`'s fund that falls short during
    the block is topped up by short() (from the wallet then the account, the card, or a restock loan)."""
    via = p.get('cover') if isinstance(p, dict) else None
    if via is None:
        yield p
        return
    e = _e()
    e.need(via in COVER_VIA, 'Chọn cách bù tiền nhập hàng nhé.')
    e.need(s['journey'].get('story'), 'Ngân hàng chỉ có trong chế độ hành trình.', 'story_only')
    e.need(career in bk.owned_places(s), 'Chỉ tiệm bạn làm chủ mới bù tiền nhập hàng bằng ví, thẻ hay khoản vay được.')
    token = _ARMED.set(dict(s=s, career=career, via=via, notes=[]))
    try:
        yield {k: v for k, v in p.items() if k != 'cover'}
    finally:
        _ARMED.reset(token)


def short(s: dict, c: dict, gap: int) -> None:
    """The armed workplace fund lacks `gap` xu for the payment being made: put them in (or do nothing when not armed)."""
    a = _ARMED.get()
    if not a or gap <= 0 or a['s'] is not s or s['careers'].get(a['career']) is not c:
        return
    e, jr, cid = _e(), _jr(), a['career']
    place = jr._place(cid)
    label = f'Nhập hàng {place}'
    if a['via'] == 'wallet':
        j = s['journey']
        e.need(j['wallet'] >= 0, 'Ví đang nợ. Trả nợ trước rồi nhập hàng nhé.', 'in_debt')
        e.need(_qy()._have(s) >= gap, f'Thiếu {bk._fmt(gap)} xu: ví và tài khoản chưa đủ.', 'no_money')
        _qy()._take(s, gap, label, cid)
        jr._transfer(s, c, gap, 'Bù tiền nhập hàng từ ví và tài khoản của bạn', 'owner_capital')
        a['notes'].append(f'Lấy {bk._fmt(gap)} xu từ ví (thiếu mới lấy tài khoản).')
        return
    text = cover(s, gap, a['via'], label, dict(k='career', id=cid))
    jr._transfer(s, c, gap, 'Quẹt thẻ tín dụng nhập hàng' if a['via'] == 'card' else 'Vay nhập hàng Ngân hàng Phố', 'owner_capital')
    a['notes'].append(text)


def notes() -> list[str]:
    a = _ARMED.get()
    return list(a['notes']) if a else []


def _where(s: dict, at: dict):
    """(kind, the shop dict) a restock loan went into, or (kind, None) when it is gone."""
    if at['k'] == 'quay':
        q = _qy().get(s)
        return 'quay', next((x for x in (q or {}).get('stalls', ()) if x.get('id') == at['id']), None)
    c = s['careers'].get(at['id'])
    return 'career', c if isinstance(c, dict) and c.get('started') else None


def _collect(s: dict, b: dict, ln: dict, left: int, n: int) -> int:
    """Morning of a due (or overdue) day: the account, then the shop that got the money, then the wallet if it finishes."""
    got = min(b['balance'], left)
    text = f'Trả vay nhập hàng · {ln["label"]}'
    if got:
        b['balance'] -= got
        bk._log(b, n, 'acc', text, -got)
    kind, shop = _where(s, ln['at'])
    if left > got and shop is not None:
        if kind == 'quay':
            part = _qy()._from_till_fund(shop, left - got)
            if part:
                _qy()._log(shop, n, f'Trả vay nhập hàng {K.BANK_SHORT}', -part)
        else:
            part = min(max(0, shop['money']), left - got)
            if part:
                _jr()._transfer(s, shop, -part, f'Trả vay nhập hàng {K.BANK_SHORT}', 'owner_draw')
        got += part
    if left > got and s['journey']['wallet'] >= left - got:
        bk._wallet(s, -(left - got), text)
        got = left
    return got


def tick(s: dict, b: dict, n: int, notes_: list) -> None:
    """bank._tick, morning of life day n: repayments due, late fees, collector calls."""
    x = get(s)
    if not x or not x['loans']:
        return
    for ln in list(x['loans']):
        if n < ln['due']:
            continue
        left = owed(ln)
        got = _collect(s, b, ln, left, n)
        ln['paid'] += got
        if owed(ln) <= 0:
            x['loans'].remove(ln)
            b['stats']['loans_closed'] = min(10**9, b['stats']['loans_closed'] + 1)
            if not ln['nfee']:
                bk._score(b, n, 'loan_ok')
                b['stats']['ontime'] = min(10**9, b['stats']['ontime'] + 1)
            bk._log(b, n, 'loan', f'Tất toán vay nhập hàng · {ln["label"]}', -got)
            bk._inbox(b, n, 'sms', K.STOCK_DUE_SMS.format(bank=K.BANK_NAME, amount=bk._fmt(got), where=ln['label']))
            continue
        if got:
            bk._log(b, n, 'loan', f'Trả một phần vay nhập hàng · {ln["label"]}', -got)
            notes_.append(bk._inbox(b, n, 'sms', K.STOCK_PART_SMS.format(bank=K.BANK_NAME, amount=bk._fmt(got), where=ln['label'],
                                                                          left=bk._fmt(owed(ln)))))
        due_fees = min(NFEE_MAX, 1 + (n - ln['due']) // bk.LOAN_PERIOD)
        if ln['nfee'] < due_fees:
            fee = max(STOCK_LATE_MIN, bk._pct_of(owed(ln), STOCK_LATE_PCT))
            ln['fees'] += fee
            ln['nfee'] += 1
            b['stats']['fees'] = min(10**9, b['stats']['fees'] + fee)
            b['stats']['late'] = min(10**9, b['stats']['late'] + 1)
            b['misses'] = min(1000, b['misses'] + 1)
            bk._score(b, n, 'loan_late')
            bk._log(b, n, 'loan', f'Phạt trễ hạn vay nhập hàng · {ln["label"]}', -fee)
            notes_.append(bk._inbox(b, n, 'sms', K.REMIND_SMS[1].format(bank=K.BANK_NAME, what=f'vay nhập hàng {ln["label"]}',
                                                                         amount=bk._fmt(owed(ln)))))
        elif n - ln['due'] in bk.CALL_DAYS:
            notes_.append('📞 ' + bk._call(s, b, n, f'vay nhập hàng {ln["label"]}', owed(ln), n - ln['due']))


# ---------------------------------------------------------------- commands (bank.apply hands them over)
def apply(s: dict, b: dict, name: str, p: dict) -> dict:
    e = _e()
    need = e.need
    day = int(s['journey']['life_day'])
    if name == 'jr_bk_tier':
        n = p.get('tier')
        need(type(n) is int and tier(s) < n < len(TIERS), 'Chọn một hạng cao hơn hạng hiện tại nhé.')
        need(p.get('confirm') is True, 'Xác nhận nâng hạng tiết kiệm.')
        src = bk._src(p)
        price = tier_cost(s, n)
        bk._take(s, b, src, price, f'Nâng hạng tiết kiệm {K.TIER_NAMES[n]}', day)
        x = ensure(s)
        x['tier'] = n
        b['stats']['fees'] = min(10**9, b['stats']['fees'] + price)
        bk._inbox(b, day, 'sms', K.TIER_SMS.format(bank=K.BANK_NAME, name=K.TIER_NAMES[n], cap=bk._fmt(TIERS[n][0])))
        return dict(message=f'{K.TIER_EMOJI[n]} Đã lên hạng {K.TIER_NAMES[n]}: gửi tiết kiệm tới {bk._fmt(TIERS[n][0])} xu. '
                            f'Phí {bk._fmt(price)} xu.')
    if name == 'jr_bk_card_review':
        c = b['card']
        need(c, 'Bạn chưa có thẻ tín dụng.')
        need(p.get('confirm') is True, 'Xác nhận xét lại hạn mức thẻ.')
        x = get(s)
        last = max(x['review'] if x else 0, c['open_day'])   # a week after the card opened, then a week after each review
        need(day - last >= REVIEW_DAYS, f'Mỗi {REVIEW_DAYS} ngày xét lại hạn mức một lần. Lần tới: {bk.dy.on_day(s, last + REVIEW_DAYS)}.',
             'too_soon')
        offer = bk.card_offer(s, b)
        if offer['why'] not in ('many', 'young'):
            b['inq'] = (b['inq'] + [day])[-bk.INQ_MAX:]
            bk._score(b, day, 'inquiry')
        x = ensure(s)
        x['review'] = day
        if not offer['ok']:
            return dict(message=f'Ngân hàng chưa nâng hạn mức. {offer["text"]}', approved=False)
        old = card_limit(s, b)
        if offer['full'] <= old:
            return dict(message=f'Hạn mức giữ nguyên {bk._fmt(old)} xu: thu nhập gần đây chưa đủ để nâng thêm.', approved=False)
        x['card'] = dict(no=c['no'], limit=offer['full'])
        c['limit'] = max(c['limit'], min(offer['full'], bk.LIMIT_MAX))
        bk._log(b, day, 'card', f'Nâng hạn mức thẻ lên {bk._fmt(offer["full"])} xu', 0)
        bk._inbox(b, day, 'sms', f'{K.BANK_NAME}: Hạn mức thẻ •••• {c["no"]} đã nâng lên {bk._fmt(offer["full"])} xu.')
        return dict(message=f'Hạn mức thẻ đã nâng từ {bk._fmt(old)} lên {bk._fmt(offer["full"])} xu.', approved=True)
    # jr_bk_stock_pay
    x = get(s)
    ln = next((v for v in (x['loans'] if x else ()) if v['id'] == p.get('id')), None)
    need(ln, 'Không tìm thấy khoản vay nhập hàng này.')
    src = bk._src(p)
    amount = owed(ln)
    bk._take(s, b, src, amount, f'Trả vay nhập hàng · {ln["label"]}', day)
    ln['paid'] += amount
    x['loans'].remove(ln)
    b['stats']['loans_closed'] = min(10**9, b['stats']['loans_closed'] + 1)
    if not ln['nfee']:
        bk._score(b, day, 'loan_ok')
        b['stats']['ontime'] = min(10**9, b['stats']['ontime'] + 1)
    bk._log(b, day, 'loan', f'Tất toán vay nhập hàng · {ln["label"]}', -amount)
    return dict(message=f'Đã trả xong khoản vay nhập hàng {bk._fmt(amount)} xu.')


# ---------------------------------------------------------------- view
def rules() -> dict:
    return dict(credit_days=CREDIT_DAYS, card_limit_max=CARD_LIMIT_MAX, review_days=REVIEW_DAYS, stock_days=STOCK_DAYS,
                stock_bp=STOCK_BP, stock_max=STOCK_MAX, stock_loans_max=STOCK_LOANS_MAX, stock_late_pct=STOCK_LATE_PCT,
                stock_late_min=STOCK_LATE_MIN, nfee_max=NFEE_MAX, savings_share=SAVINGS_SHARE)


def public(s: dict, b: dict, inc: dict) -> dict:
    day = int(s['journey']['life_day'])
    x = get(s) or initial()
    t = x['tier']
    saved = bk._savings_total(b)
    tiers = [dict(n=k, name=K.TIER_NAMES[k], emoji=K.TIER_EMOJI[k], cap=cp, price=pr, cost=tier_cost(s, k) if k > t else 0, own=k <= t)
             for k, (cp, pr) in enumerate(TIERS)]
    offer = stock_offer(s, b, inc)
    loans = [dict(ln, owed=owed(ln), days_left=ln['due'] - day, late=ln['nfee'] > 0) for ln in x['loans']]
    c = b['card']
    lim = card_limit(s, b)
    why = bk.card_usable(s, b)
    avail = max(0, lim - c['bal']) if c else 0
    review = None
    if c:
        nxt = max(x['review'], c['open_day']) + REVIEW_DAYS
        review = dict(ok=nxt <= day, day=nxt)
    return dict(tier=t, name=K.TIER_NAMES[t], emoji=K.TIER_EMOJI[t], cap=TIERS[t][0], saved=saved, room=max(0, TIERS[t][0] - saved),
                over=saved > TIERS[t][0], tiers=tiers, young=young(s), stock=offer, stock_loans=loans, owed=sum(v['owed'] for v in loans),
                card_limit=lim, review=review, rules=rules(),
                cover=dict(card=dict(ok=bool(c) and why is None and avail > 0, available=avail, why=why or ('' if avail else 'Thẻ đã hết hạn mức.')),
                           loan=dict(ok=offer['ok'], room=offer['room'], why=offer['text'])))


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    j = s.get('journey')
    if not isinstance(j, dict) or j.get(KEY) is None:
        return
    e = _e()
    need, integer, txt = e.need, e.integer, e.clean_text
    x = j[KEY]
    bad = 'Dữ liệu ngân hàng không hợp lệ.'
    need(isinstance(x, dict) and set(x) == KEYS and x['v'] == VERSION and isinstance(j.get('bank'), dict), bad, 'invalid_save')
    integer(x['tier'], 0, len(TIERS) - 1)
    integer(x['review'], 0, 10**6)
    integer(x['seq'], 0, 10**9)
    c = x['card']
    if c is not None:
        need(isinstance(c, dict) and set(c) == {'no', 'limit'} and isinstance(c['no'], str) and c['no'].isdigit() and len(c['no']) == 4, bad)
        integer(c['limit'], bk.LIMIT_MIN, CARD_LIMIT_MAX)
    need(isinstance(x['loans'], list) and len(x['loans']) <= STOCK_LOANS_MAX, bad)
    for ln in x['loans']:
        need(isinstance(ln, dict) and set(ln) == LOAN_KEYS and isinstance(ln['at'], dict) and set(ln['at']) == {'k', 'id'}
             and ln['at']['k'] in ('quay', 'career'), bad)
        txt(ln['id'], 16)
        txt(ln['at']['id'], 40)
        txt(ln['label'], 60)
        integer(ln['start'], 1, 10**6)
        need(ln['due'] == ln['start'] + STOCK_DAYS, bad)
        integer(ln['principal'], 1, STOCK_MAX)
        integer(ln['interest'], 1, STOCK_MAX)
        integer(ln['nfee'], 0, NFEE_MAX)
        integer(ln['fees'], 0, STOCK_MAX * NFEE_MAX)
        integer(ln['paid'], 0, STOCK_MAX * (NFEE_MAX + 2))
        need(owed(ln) > 0, bad)
