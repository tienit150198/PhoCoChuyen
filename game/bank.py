"""🏦 Ngân hàng Phố: the player's own bank (story mode).

The journey wallet stays the cash in hand ("Tiền mặt"). The bank adds, under
`s['journey']['bank']` (absent = no account yet, so older saves load unchanged):

* a current account (tài khoản thanh toán) with deposits, ATM withdrawals and a
  statement with running balances;
* savings: a demand pot credited daily and term deposits quoted per in-game year
  (7 days to 3 years; 1 tháng = MONTH_DAYS life days, 1 năm = YEAR_DAYS), paid at
  maturity or renewed (tái tục); closing a term early pays the demand rate for the days held;
* a credit card: approval and limit from the credit score and recent income,
  swipes through `pay()`, a statement every 7 life days, a minimum payment due 3
  days later, interest on carried balances, late fees, cash advances;
* loans: unsecured personal loans and "vay mở rộng tiệm" paid into a workplace
  fund, an amortization schedule auto-debited on due days, early repayment with
  a small fee, late penalties, collector reminders and a "nợ xấu" flag that
  blocks new credit for a while;
* a credit score (300–850) that moves with how the player handles all of this.

Rules resolve on the life-day tick (`on_life_day`, called from journey.after):
the bank remembers the last life day it closed, so interest, statements,
installments and fees are applied exactly once whatever the retries.
Nothing here is random: the account and card numbers come from the journey seed.
Commands arrive as `jr_bk_*` through journey.action.
"""
from __future__ import annotations

import hashlib

from . import archive as ar
from . import bank_content as K
from . import days as dy      # "Ngày N" wording (game/days.py)
from . import price_index as pi   # 💹 07/10: the flat fees (the percentages and the loan rates stay; 1.9.9 pins LOAN_BP)

VERSION = 1
KIND = 'bank'               # journey wallet history kind (journey.HISTORY_KINDS)
AMOUNT_MAX = 10**7
BAL_MAX = 10**9

# Current account.
ATM_OTHER_FEE = 1           # xu, "cây ATM khác ngân hàng"

# In-game calendar for savings and mortgages (game/housing.py): 1 tháng = 5 ngày sống,
# 1 năm = 12 tháng = 60 ngày sống. Rates are quoted per year, like a real passbook.
MONTH_DAYS = 5
YEAR_DAYS = 12 * MONTH_DAYS
# Savings. Không kỳ hạn: basis points of a xu per xu per life day (5 = 0,05 %/ngày = 3 %/năm), credited daily.
DEMAND_BP = 5
# Có kỳ hạn: term (life days) -> basis points per year, paid at maturity. Longer terms pay more; the
# Invest's 7-day savings (invest.py, 0,3 %/ngày) stays the higher-return option; every rate stays below the loans.
TERM_RATE = {7: 600, 15: 700, 30: 750, 60: 800, 120: 850, 180: 880}
LEGACY_RATE = {7: 1200, 14: 1500, 30: 1800}   # sổ opened before 0.9.5 (0,2/0,25/0,3 %/ngày) keep their rate
SAVE_MIN = 20
TERMS_MAX = 5

# Credit score.
SCORE_START, SCORE_MIN, SCORE_MAX = 650, 300, 850
DELTA = dict(inquiry=-5, card_full=10, card_min=4, card_late=-35, loan_ok=6, loan_late=-40, loan_done=10,
             income=4, age=2, util_low=2, util_mid=-4, util_high=-10, bad=-60,
             home_ok=5, home_late=-25, home_done=15)   # 🏠 vay mua nhà (game/housing.py)
AGE_CAP = 30                # most points the account's age can add
REVIEW = 7                  # weekly review (income, age) every 7 life days after opening

# Card.
CARD_MIN_SCORE = 580
CARD_CYCLE = 7              # a statement every 7 life days
CARD_GRACE = 3              # due 3 life days after the statement
CARD_MIN_PCT, CARD_MIN_FLOOR = 10, 10
CARD_BP = 50                # 0,5 %/ngày on carried balances and cash advances
CARD_LATE_FEE = pi.price(8)   # 💹 07/10: base 8
CASH_FEE_PCT, CASH_FEE_MIN, CASH_SHARE = 4, pi.price(3), 50
LIMIT_MIN, LIMIT_MAX = 50, 5000

# Loans (interest per 7-day period, basis points).
LOAN_PERIOD = 7
LOAN_BP = {'personal': 400, 'shop': 350}
LOAN_DAYS = {'personal': 14, 'shop': 21}   # how many days of income the offer may reach
LOAN_TERMS = (14, 21, 28)
LOAN_MIN, LOAN_MAX = 50, 5000
LOANS_MAX = 2
LOAN_LATE_PCT, LOAN_LATE_MIN = 5, 3
EARLY_FEE_PCT, EARLY_FEE_MIN = 2, 2
DTI_PCT = 40

# Applications and bad debt.
INCOME_WINDOW, INCOME_DAYS, INCOME_MIN = 14, 3, 10
INQ_WINDOW, INQ_MANY = 14, 3
BAD_MISSES, BAD_DAYS = 3, 30
CALL_DAYS = (2, 5, 9)       # overdue days on which the collector calls

LOG_MAX, INBOX_MAX, SCORE_LOG_MAX, INQ_MAX = 80, 12, 20, 10
ACCOUNTS = ('acc', 'sav', 'card', 'loan')
INBOX_KINDS = ('sms', 'call')
PREFS = tuple(K.PAY_PREF)
AUTOPAYS = tuple(K.AUTOPAY)
STATS = ('interest_in', 'interest_out', 'fees', 'ontime', 'late', 'swipes', 'loans_closed')
COMMANDS = ('jr_bk_open', 'jr_bk_deposit', 'jr_bk_withdraw', 'jr_bk_save', 'jr_bk_unsave', 'jr_bk_card_apply',
            'jr_bk_card_pay', 'jr_bk_card_cash', 'jr_bk_card_autopay', 'jr_bk_card_close', 'jr_bk_loan_apply',
            'jr_bk_loan_pay', 'jr_bk_loan_close', 'jr_bk_settings', 'jr_bk_read')


# ---------------------------------------------------------------- helpers
def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def _pct_of(amount: int, pct: int) -> int:
    return _ceil_div(amount * pct, 100)


def _floor10(x: int) -> int:
    return max(0, int(x)) // 10 * 10


def _digits(seed: int, what: str, n: int) -> str:
    h = int(hashlib.sha256(f'bank|{seed}|{what}'.encode()).hexdigest()[:12], 16)
    return str(h % 10 ** n).zfill(n)


def initial(seed: int = 0, day: int = 1) -> dict:
    return dict(v=VERSION, no=_digits(seed, 'acct', 10), open_day=int(day), day=int(day), balance=0,
                demand=0, pend=0, terms=[], card=None, loans=[], score=SCORE_START, score_log=[], inq=[],
                misses=0, bad_until=0, age_pts=0, log=[], inbox=[], seq=0, pref='auto', sweep=True,
                stats={k: 0 for k in STATS})


def get(s: dict) -> dict | None:
    j = s.get('journey')
    b = j.get('bank') if isinstance(j, dict) else None
    return b if isinstance(b, dict) else None


def _band(score: int) -> tuple:
    for low, name, tone in K.BANDS:
        if score >= low:
            return name, tone
    return K.BANDS[-1][1], K.BANDS[-1][2]


def _seq(b: dict, prefix: str) -> str:
    b['seq'] += 1
    return f'{prefix}{b["seq"]}'


def term_interest(amount: int, rate: int, days: int) -> int:
    """Interest of `amount` xu at `rate` basis points per in-game year over `days` life days."""
    return amount * rate * days // (10000 * YEAR_DAYS)


def year_text(rate: int) -> str:
    """600 -> '6%/năm', 750 -> '7,5%/năm'."""
    return _pct_text(rate) + '/năm'


def upgrade(j: dict) -> None:
    """Older bank blocks join 0.9.5: a term deposit keeps the rate it was opened with, now written per
    year (bp per day × YEAR_DAYS gives exactly the same interest), and is not renewed."""
    b = j.get('bank') if isinstance(j, dict) else None
    if not isinstance(b, dict) or not isinstance(b.get('terms'), list):
        return
    for t in b['terms']:
        if isinstance(t, dict) and 'bp' in t and 'rate' not in t and type(t['bp']) is int:
            t['rate'] = t.pop('bp') * YEAR_DAYS
        if isinstance(t, dict):
            t.setdefault('renew', False)


def _savings_total(b: dict) -> int:
    return b['demand'] + sum(t['amount'] for t in b['terms'])


def _loan_left(b: dict) -> int:
    return sum(r['principal'] - min(r['principal'], r['paid']) for ln in b['loans'] for r in ln['rows'])


def _log(b: dict, day: int, acc: str, text: str, amount: int) -> None:
    if acc == 'acc':
        bal = b['balance']
    elif acc == 'sav':
        bal = _savings_total(b)
    elif acc == 'card':
        bal = b['card']['bal'] if b['card'] else 0
    else:
        bal = _loan_left(b)
    b['log'] = ar.last(b['log'] + [dict(id=_seq(b, 'g'), day=int(day), acc=acc, text=text[:120], amt=int(amount), bal=int(bal))],
                       LOG_MAX, 'bank.log', ar.JOURNEY)


def _inbox(b: dict, day: int, kind: str, text: str) -> str:
    b['inbox'] = ar.last(b['inbox'] + [dict(id=_seq(b, 'm'), day=int(day), kind=kind, text=text[:300], read=False)],
                         INBOX_MAX, 'bank.inbox', ar.JOURNEY)
    return text


def _score(b: dict, day: int, why: str, delta: int | None = None) -> int:
    delta = DELTA[why] if delta is None else delta
    before = b['score']
    b['score'] = max(SCORE_MIN, min(SCORE_MAX, before + delta))
    moved = b['score'] - before
    if moved:
        b['score_log'] = ar.last(b['score_log'] + [dict(day=int(day), why=why, delta=moved, score=b['score'])],
                                 SCORE_LOG_MAX, 'bank.score', ar.JOURNEY)
    return moved


def _wallet(s: dict, amount: int, label: str) -> None:
    _jr()._wallet(s['journey'], amount, KIND, label)


def _fmt(n: int) -> str:
    return f'{int(n):,}'.replace(',', '.')


def _pct_text(bp: int) -> str:
    whole, part = divmod(bp, 100)
    return f'{whole},{part:02d}'.rstrip('0').rstrip(',') + '%'


# ---------------------------------------------------------------- income and offers
def income(s: dict, day: int | None = None, window: int = INCOME_WINDOW) -> dict:
    """Salary and profit drawn into the wallet (minus money put back into the workplaces) over the
    `window` life days before `day` (the days already lived)."""
    j = s['journey']
    day = int(j['life_day']) if day is None else day
    total, days = 0, set()
    for row in j.get('history', ()):
        d = row.get('day', 0)
        if not (day - window <= d < day):
            continue
        if row.get('kind') in ('salary', 'draw') and row.get('amount', 0) > 0:
            total += row['amount']
            days.add(d)
        elif row.get('kind') == 'invest' and row.get('amount', 0) < 0 and row.get('career'):
            total += row['amount']
    # A shop loan paid into a fund and drawn back out is borrowed money, not income.
    b = j.get('bank') if isinstance(j.get('bank'), dict) else None
    for ln in (b or {}).get('loans', ()):
        if ln.get('kind') == 'shop' and day - window <= ln.get('start', 0) < day + 1:
            total -= ln['principal']
    total = max(0, total)
    return dict(total=total, avg=total // window, days=len(days), window=window)


def _factor(score: int) -> tuple[int, int]:
    """(numerator, denominator) of the limit multiplier for a score."""
    if score >= 740:
        return 3, 2
    if score >= 670:
        return 1, 1
    return 3, 5


def _overdue(b: dict, day: int) -> bool:
    if b['card'] and b['card']['past_due'] > 0:
        return True
    return any(r['due'] <= day and r['paid'] < r['amount'] for ln in b['loans'] for r in ln['rows'])


def _blocked(b: dict, day: int) -> str | None:
    if b['bad_until'] > day:
        return 'bad'
    if _overdue(b, day):
        return 'overdue'
    return None


def _inq_recent(b: dict, day: int) -> int:
    return sum(1 for d in b['inq'] if d > day - INQ_WINDOW)


def _screen(s: dict, b: dict, need_score: int, inc: dict | None = None) -> tuple[str | None, str]:
    """(reason code, text) when the bank would say no before looking at amounts.
    `inc`: income(s) when the caller already has it."""
    day = s['journey']['life_day']
    why = _blocked(b, day)
    if why:
        return why, K.DECLINE[why].format(until=dy.on_day(s, b['bad_until']))
    if _inq_recent(b, day) >= INQ_MANY:
        recent = sorted(d for d in b['inq'] if d > day - INQ_WINDOW)
        return 'many', K.DECLINE['many'].format(window=INQ_WINDOW, when=dy.when_day(s, recent[-INQ_MANY] + INQ_WINDOW))
    if b['score'] < need_score:
        return 'score', K.DECLINE['score'].format(score=b['score'], need=need_score)
    inc = income(s, day) if inc is None else inc
    if inc['days'] < INCOME_DAYS or inc['avg'] < INCOME_MIN:
        return 'income', K.DECLINE['income'].format(days=INCOME_DAYS, window=INCOME_WINDOW)
    return None, ''


def card_offer(s: dict, b: dict, inc: dict | None = None) -> dict:
    inc = income(s) if inc is None else inc
    why, text = _screen(s, b, CARD_MIN_SCORE, inc)
    num, den = _factor(b['score'])
    limit = max(LIMIT_MIN, min(LIMIT_MAX, _floor10(inc['avg'] * CARD_CYCLE * num // den)))
    return dict(ok=why is None, why=why, text=text, limit=limit if why is None else 0)


def _weekly_due(b: dict) -> int:
    """What the active loans take in a 7-day week (their largest scheduled installment)."""
    return sum(max((r['amount'] for r in ln['rows']), default=0) for ln in b['loans'])


def loan_offer(s: dict, b: dict, kind: str, inc: dict | None = None) -> dict:
    inc = income(s) if inc is None else inc
    why, text = _screen(s, b, CARD_MIN_SCORE, inc)
    num, den = _factor(b['score'])
    most = min(LOAN_MAX, _floor10(inc['avg'] * LOAN_DAYS[kind] * num // den))
    places = owned_places(s) if kind == 'shop' else []
    if why is None and len(b['loans']) >= LOANS_MAX:
        why, text = 'count', f'Mỗi người giữ tối đa {LOANS_MAX} khoản vay cùng lúc. Tất toán một khoản trước nhé.'
    if why is None and any(ln['kind'] == kind for ln in b['loans']):
        why, text = 'same', 'Bạn đang có một khoản vay loại này. Tất toán xong rồi hãy vay tiếp nhé.'
    if why is None and kind == 'shop' and not places:
        why, text = 'place', 'Vay mở rộng tiệm cần một tiệm bạn làm chủ và đã mở cửa.'
    if why is None and most < LOAN_MIN:
        why, text = 'income', K.DECLINE['income'].format(days=INCOME_DAYS, window=INCOME_WINDOW)
    room = max(0, inc['avg'] * LOAN_PERIOD * DTI_PCT // 100 - _weekly_due(b))
    return dict(ok=why is None, why=why, text=text, max=most if why is None else 0, bp=LOAN_BP[kind],
                terms=list(LOAN_TERMS), min=LOAN_MIN, weekly_room=room, places=places)


def owned_places(s: dict) -> list[str]:
    """Started workplaces the player runs (not a job): a shop loan can go into their fund."""
    jr = _jr()
    j = s['journey']
    return [cid for cid, c in s['careers'].items()
            if c.get('started') and cid in j.get('unlocked', ()) and cid not in j.get('paused', {}) and not jr._employed(cid)]


# ---------------------------------------------------------------- loan maths (mirrored in public/js/v4/bank.js)
def _interest(rest: int, bp: int) -> int:
    return (rest * bp + 5000) // 10000


def _fits(principal: int, bp: int, n: int, pay: int) -> bool:
    rest = principal
    for _ in range(n - 1):
        rest -= pay - _interest(rest, bp)
        if rest <= 0:
            return True
    return rest + _interest(rest, bp) <= pay


def installment(principal: int, bp: int, n: int) -> int:
    """The smallest whole installment that clears `principal` in `n` periods."""
    lo, hi = max(1, _ceil_div(principal, n)), principal * 2 + 10
    while lo < hi:
        mid = (lo + hi) // 2
        if _fits(principal, bp, n, mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def schedule(principal: int, bp: int, term: int, start: int) -> list[dict]:
    n = term // LOAN_PERIOD
    pay = installment(principal, bp, n)
    rows, rest = [], principal
    for k in range(1, n + 1):
        i = _interest(rest, bp)
        part = rest if k == n else max(0, min(rest, pay - i))
        rows.append(dict(k=k, due=start + LOAN_PERIOD * k, principal=part, interest=i, amount=part + i, paid=0, fee=0, late=False))
        rest -= part
    return rows


def quote(principal: int, kind: str, term: int, start: int = 0) -> dict:
    rows = schedule(principal, LOAN_BP[kind], term, start)
    return dict(rows=rows, installment=rows[0]['amount'], interest=sum(r['interest'] for r in rows),
                total=sum(r['amount'] for r in rows))


# ---------------------------------------------------------------- paying (other modules call this)
def card_usable(s: dict, b: dict | None = None) -> str | None:
    """None when the card can be swiped, otherwise why not (Vietnamese sentence)."""
    b = b or get(s)
    if not b or not b['card']:
        return 'Bạn chưa có thẻ tín dụng Ngân hàng Phố.'
    c = b['card']
    if b['bad_until'] > s['journey']['life_day']:
        return 'Thẻ đang tạm ngưng vì hồ sơ bị ghi nhận nợ xấu.'
    if c['past_due'] > 0:
        return f'Thẻ đang tạm khóa vì trễ hạn: cần trả {_fmt(c["past_due"])} xu quá hạn trước.'
    return None


def available(b: dict) -> int:
    c = b['card']
    return max(0, c['limit'] - c['bal']) if c else 0


def _couple():
    try:
        from . import couple
        return couple
    except ImportError:   # a build without marriage
        return None


def joint(s: dict) -> dict | None:
    """The couple's joint fund as game/couple.py sees it (None: not married, or no database bound)."""
    cp = _couple()
    try:
        return cp.joint_account(s) if cp else None
    except Exception:   # noqa: BLE001 - the joint card is optional, the bank must still work
        return None


def pay_options(s: dict, amount: int, with_joint: bool = False, no_joint: bool = False) -> dict:
    """no_joint: never look at the joint fund (callers inside a store transaction: couple.joint_account
    reads the database, and joint_spend refuses to run under the write lock)."""
    j = s['journey']
    b = get(s)
    why = card_usable(s, b)
    out = dict(cash=j['wallet'] >= amount, account=False, account_why='Bạn chưa mở tài khoản thanh toán.',
               account_available=0, card=False, card_why=why, pref='auto', available=0, joint=False, joint_why='')
    if b is not None:
        out.update(account=b['balance'] >= amount, account_available=b['balance'],
                   account_why='' if b['balance'] >= amount else f'Tài khoản chỉ còn {_fmt(b["balance"])} xu, cần {_fmt(amount)} xu.')
        out.update(card=why is None and available(b) >= amount, card_why=why or ('' if available(b) >= amount else 'Vượt hạn mức còn lại của thẻ.'),
                   pref=b['pref'], available=available(b))
    if no_joint:
        out['joint_why'] = 'Thẻ chung không dùng được cho khoản này.'
    elif with_joint or out['pref'] == 'joint':
        acc = joint(s)
        if not acc:
            out['joint_why'] = 'Bạn chưa có quỹ chung vợ chồng.'
        elif acc['balance'] < amount:
            out['joint_why'] = f'Quỹ chung chỉ còn {_fmt(acc["balance"])} xu.'
        else:
            out['joint'] = True
    return out


def _method(s: dict, amount: int, method: str, no_joint: bool = False) -> str | None:
    if no_joint and method == 'joint':
        method = 'auto'
    opts = pay_options(s, amount, method == 'joint', no_joint)
    if method in ('cash', 'card', 'joint', 'account'):
        return method if opts[method] else None
    order = dict(account=('account',), card=('card', 'cash'), cash=('cash',), joint=('joint', 'cash', 'card')).get(opts['pref'], ('cash', 'card'))
    return next((m for m in order if opts[m]), None)


def can_pay(s: dict, amount: int, method: str = 'auto', no_joint: bool = False) -> bool:
    return _method(s, amount, method, no_joint) is not None


def pay(s: dict, amount: int, label: str, ref: str | None = None, method: str = 'auto', kind: str = KIND,
        career: str | None = None, short: str | None = None, no_joint: bool = False) -> dict:
    """Pay a personal purchase: cash, current-account debit, credit card, or the couple's
    joint card ("Thẻ chung", charged to the joint fund through game/couple.py).

    method: 'account' | 'cash' | 'card' | 'joint' | 'auto' (the player's preference in the bank app: cash when
    the wallet is enough, otherwise the card; or card first; or the joint card first).
    Account preference is account-only: insufficient funds never silently borrow or spend cash.
    Debit is entirely in the command's save copy, so command retries use existing store deduplication.
    `kind`/`career` label the wallet history row of a cash payment. no_joint=True excludes the joint fund
    (use it inside a marriage/couple store transaction; see pay_options). Raises GameError (`short` or
    a default sentence) when no way works. Returns {method, text}."""
    e = _core()
    e.need(type(amount) is int and 0 < amount <= AMOUNT_MAX, 'Số tiền thanh toán không hợp lệ.')
    method = method if method in ('auto', 'cash', 'card', 'joint', 'account') else 'auto'
    if no_joint and method == 'joint':
        method = 'auto'
    how = _method(s, amount, method, no_joint)
    if how is None:
        if method == 'account' or (method == 'auto' and get(s) and get(s)['pref'] == 'account'):
            raise e.GameError(pay_options(s, amount, no_joint=True)['account_why'], 'not_enough')
        if method in ('card', 'joint'):
            why = pay_options(s, amount, method == 'joint', no_joint)[method + '_why']
            raise e.GameError(f'Thẻ bị từ chối: {why[0].lower() + why[1:]}' if why else 'Thẻ bị từ chối.', 'card_declined')
        raise e.GameError(short or f'Ví chưa đủ {_fmt(amount)} xu.', 'not_enough')
    j = s['journey']
    b = get(s)
    if how == 'account':
        b['balance'] -= amount
        _log(b, j['life_day'], 'acc', f'Thanh toán · {label}', -amount)
        b['ting'] = b.get('ting', 0) + amount
        return dict(method='account', text=f'Trả {_fmt(amount)} xu từ tài khoản thanh toán.')
    if how == 'cash':
        _jr()._wallet(j, -amount, kind, label[:120], career)
        return dict(method='cash', text=f'Trả {_fmt(amount)} xu tiền mặt.')
    if how == 'joint':
        sp = (s.get('marriage') or {}).get('spouse') or {}
        # A ref that only depends on the save: a retried command recomputes the same one (joint_spend is
        # idempotent per ref), while every new purchase gets a new one (the bank's counter, or else the
        # latest marriage effect id, which joint_spend itself appends after each charge).
        last = ((s.get('marriage') or {}).get('applied') or [''])[-1]
        tick = _seq(b, '') if b else hashlib.sha1(f'{j["life_day"]}|{amount}|{label}|{last}|{len(j["history"])}'.encode()).hexdigest()[:10]
        tag = ref or f'bk{sp.get("side", "x")}{j["life_day"]}n{tick}'
        try:
            _couple().joint_spend(s, amount, f'Thẻ chung · {label}'[:120], tag[:40])
        except e.GameError as x:
            # 'busy': this command is being recomputed under the store's write lock (a contended save);
            # an automatic choice then simply pays the next way instead of failing the purchase.
            if x.code != 'busy' or method != 'auto':
                raise
            return pay(s, amount, label, ref, 'auto', kind, career, short, no_joint=True)
        if b:
            b['ting'] = b.get('ting', 0) + amount
        return dict(method='joint', text=f'Quẹt thẻ chung {_fmt(amount)} xu từ quỹ chung vợ chồng.')
    c = b['card']
    c['bal'] += amount
    b['stats']['swipes'] += 1
    _log(b, j['life_day'], 'card', f'Quẹt thẻ · {label}', -amount)
    b['ting'] = b.get('ting', 0) + amount
    return dict(method='card', text=f'Quẹt thẻ •••• {c["no"]} {_fmt(amount)} xu, trả khi có sao kê.')


# ---------------------------------------------------------------- the daily tick
def _debit(s: dict, b: dict, amount: int, label: str, day: int, wallet_too: bool = True) -> bool:
    """Take `amount` from the account, then the cash in hand. All or nothing."""
    j = s['journey']
    cash = max(0, j['wallet']) if wallet_too else 0
    if b['balance'] + cash < amount:
        return False
    from_acc = min(b['balance'], amount)
    if from_acc:
        b['balance'] -= from_acc
        _log(b, day, 'acc', label, -from_acc)
    if amount > from_acc:
        _wallet(s, -(amount - from_acc), label)
    return True


def _call(s: dict, b: dict, day: int, what: str, amount: int, days: int) -> str:
    lines = K.COLLECTOR_CALLS
    text = lines[int(_digits(s['journey'].get('seed', 0), f'call|{day}|{what}', 4)) % len(lines)]
    return _inbox(b, day, 'call', text.format(name=s.get('name') or 'bạn', bank=K.BANK_NAME, what=what, amount=_fmt(amount), days=days))


def _loan_name(ln: dict) -> str:
    return K.LOANS[ln['kind']]['name'].lower()


def _tick_loans(s: dict, b: dict, n: int, notes: list) -> None:
    for ln in list(b['loans']):
        what = _loan_name(ln)
        for r in ln['rows']:
            if r['due'] > n or r['paid'] >= r['amount']:
                continue
            left = r['amount'] - r['paid']
            if _debit(s, b, left, f'Trả góp kỳ {r["k"]}/{len(ln["rows"])} · {K.LOANS[ln["kind"]]["name"]}', n):
                r['paid'] = r['amount']
                _log(b, n, 'loan', f'Kỳ {r["k"]}/{len(ln["rows"])} · {K.LOANS[ln["kind"]]["name"]}', -left)
                if not r['late']:
                    _score(b, n, 'loan_ok')
                    b['stats']['ontime'] += 1
                    _inbox(b, n, 'sms', K.INSTALLMENT_SMS.format(bank=K.BANK_NAME, amount=_fmt(left), k=r['k'], n=len(ln['rows']), what=what))
                else:
                    notes.append(f'🏦 Đã trích {_fmt(left)} xu trả khoản quá hạn kỳ {r["k"]} ({what}).')
                continue
            if not r['late']:
                r['late'] = True
                fee = max(LOAN_LATE_MIN, _pct_of(r['amount'], LOAN_LATE_PCT))
                r['fee'] = fee
                r['amount'] += fee
                b['stats']['fees'] += fee
                b['stats']['late'] += 1
                b['misses'] += 1
                _score(b, n, 'loan_late')
                _log(b, n, 'loan', f'Phạt trễ hạn kỳ {r["k"]} · {K.LOANS[ln["kind"]]["name"]}', -fee)
                notes.append(_inbox(b, n, 'sms', K.REMIND_SMS[0].format(bank=K.BANK_NAME, what=f'trả góp kỳ {r["k"]} {what}',
                                                                        amount=_fmt(r['amount'] - r['paid']))))
            elif n - r['due'] in CALL_DAYS:
                notes.append('📞 ' + _call(s, b, n, what, r['amount'] - r['paid'], n - r['due']))
        if all(r['paid'] >= r['amount'] for r in ln['rows']):
            b['loans'].remove(ln)
            b['stats']['loans_closed'] += 1
            _score(b, n, 'loan_done')
            notes.append(f'🎉 Bạn đã trả xong {what}.')


def _tick_card(s: dict, b: dict, n: int, notes: list) -> None:
    c = b['card']
    if not c:
        return
    st = c['stmt']
    # Due date of the last statement.
    if st and not st['done'] and n >= st['due']:
        want = st['amount'] - st['paid'] if c['autopay'] == 'full' else st['min'] - st['paid'] if c['autopay'] == 'min' else 0
        want = min(want, c['bal'])
        if want > 0 and b['balance'] < want and c['autopay'] == 'full':
            want = min(st['min'] - st['paid'], c['bal'])
        if want > 0 and b['balance'] >= want:
            _card_payment(b, n, want, 'acc', auto=True)
        st['done'] = True
        if st['amount'] > 0:
            if st['paid'] >= st['amount']:
                _score(b, n, 'card_full')
                b['stats']['ontime'] += 1
            elif st['paid'] >= st['min']:
                _score(b, n, 'card_min')
                b['stats']['ontime'] += 1
            else:
                c['past_due'] = st['min'] - st['paid']
                c['late_day'] = n
                c['bal'] += CARD_LATE_FEE
                b['stats']['fees'] += CARD_LATE_FEE
                b['stats']['late'] += 1
                b['misses'] += 1
                _score(b, n, 'card_late')
                _log(b, n, 'card', 'Phí trễ hạn thanh toán thẻ', -CARD_LATE_FEE)
                notes.append(_inbox(b, n, 'sms', K.REMIND_SMS[0].format(bank=K.BANK_NAME, what=f'thanh toán thẻ •••• {c["no"]}',
                                                                        amount=_fmt(c['past_due']))))
    elif c['past_due'] > 0 and n - c['late_day'] in CALL_DAYS:
        notes.append('📞 ' + _call(s, b, n, f'thẻ tín dụng •••• {c["no"]}', c['past_due'], n - c['late_day']))
    # Statement day.
    if n > c['cycle'] and (n - c['cycle']) % CARD_CYCLE == 0:
        charge = 0
        if st and st['amount'] > st['paid']:
            revolving = min(c['bal'], st['amount'] - st['paid'])
            charge += _ceil_div(revolving * CARD_BP * CARD_CYCLE, 10000)
        if c['cash'] > 0:
            charge += _ceil_div(c['cash'] * CARD_BP * max(1, n - c['cash_day']), 10000)
            c['cash'] = 0
        if charge:
            c['bal'] += charge
            b['stats']['interest_out'] += charge
            _log(b, n, 'card', 'Lãi thẻ tín dụng kỳ này', -charge)
        bal = c['bal']
        util = bal * 100 // c['limit'] if c['limit'] else 0
        if bal > 0 or (st and st['amount'] > 0):
            _score(b, n, 'util_high' if util > 70 else 'util_mid' if util > 30 else 'util_low')
        low = min(bal, max(_pct_of(bal, CARD_MIN_PCT), CARD_MIN_FLOOR) + c['past_due']) if bal > 0 else 0
        c['stmt_n'] += 1
        c['stmt'] = dict(n=c['stmt_n'], day=n, amount=bal, min=low, due=n + CARD_GRACE, paid=0, done=bal == 0)
        if bal > 0:
            notes.append(_inbox(b, n, 'sms', K.STATEMENT_SMS.format(bank=K.BANK_NAME, no=c['no'], amount=_fmt(bal), min=_fmt(low),
                                                                    due=n + CARD_GRACE)))


def _tick(s: dict, b: dict, n: int, notes: list) -> None:
    """Morning of life day `n`: everything that the night before settled."""
    j = s['journey']
    # Savings: the demand pot earns every day; term deposits pay out on maturity.
    if b['demand'] > 0:
        b['pend'] += b['demand'] * DEMAND_BP
        gain, b['pend'] = divmod(b['pend'], 10000)
        if gain:
            b['demand'] += gain
            b['stats']['interest_in'] += gain
            _log(b, n, 'sav', 'Lãi tiết kiệm không kỳ hạn', gain)
    for t in list(b['terms']):
        if n >= t['due']:
            gain = term_interest(t['amount'], t['rate'], t['term'])
            b['stats']['interest_in'] += gain
            if t['renew'] and t['term'] in TERM_RATE and t['amount'] + gain <= BAL_MAX:
                # Tái tục: principal and interest roll into a new sổ of the same term, at today's rate.
                t.update(amount=t['amount'] + gain, rate=TERM_RATE[t['term']], start=n, due=n + t['term'])
                _log(b, n, 'sav', f'Tái tục sổ {K.TERMS[t["term"]].lower()}: nhập lãi {_fmt(gain)} xu vào gốc', gain)
                notes.append(_inbox(b, n, 'sms', K.RENEWED_SMS.format(bank=K.BANK_NAME, term=K.TERMS[t['term']].lower(),
                                                                      gain=_fmt(gain), total=_fmt(t['amount']), due=t['due'])))
                continue
            b['terms'].remove(t)
            b['balance'] += t['amount'] + gain
            _log(b, n, 'sav', f'Tất toán sổ {K.TERMS[t["term"]].lower()}', -t['amount'])
            _log(b, n, 'acc', f'Sổ {K.TERMS[t["term"]].lower()} đáo hạn: gốc {_fmt(t["amount"])} + lãi {_fmt(gain)} xu', t['amount'] + gain)
            notes.append(_inbox(b, n, 'sms', K.MATURED_SMS.format(bank=K.BANK_NAME, term=K.TERMS[t['term']].lower(),
                                                                  amount=_fmt(t['amount']), total=_fmt(t['amount'] + gain))))
    _tick_loans(s, b, n, notes)
    _tick_card(s, b, n, notes)
    # Weekly review: steady income, account age.
    if n > b['open_day'] and (n - b['open_day']) % REVIEW == 0:
        if income(s, n, REVIEW)['days'] >= 4:
            _score(b, n, 'income')
        if b['age_pts'] < AGE_CAP:
            b['age_pts'] += _score(b, n, 'age', min(DELTA['age'], AGE_CAP - b['age_pts'])) or 0
    # Nợ xấu.
    if b['misses'] >= BAD_MISSES and b['bad_until'] <= n:
        b['bad_until'] = n + BAD_DAYS
        b['misses'] = 0
        _score(b, n, 'bad')
        notes.append('⚠️ ' + _inbox(b, n, 'sms', K.BAD_DEBT_SMS.format(bank=K.BANK_NAME, until=b['bad_until'])))
    elif b['bad_until'] and b['bad_until'] <= n:
        if _overdue(b, n):
            b['bad_until'] = n + REVIEW
        else:
            b['bad_until'] = 0
            notes.append(_inbox(b, n, 'sms', K.BAD_CLEAR_SMS.format(bank=K.BANK_NAME)))
    # The account quietly covers a wallet that went below zero (rent, meals).
    if b['sweep'] and j['wallet'] < 0 and b['balance'] > 0:
        amt = min(b['balance'], -j['wallet'])
        b['balance'] -= amt
        _log(b, n, 'acc', 'Tự động bù tiền mặt đang âm', -amt)
        _wallet(s, amt, 'Tài khoản ngân hàng bù ví âm')
        notes.append(f'🏦 Tài khoản đã tự bù {_fmt(amt)} xu cho ví đang âm.')


def on_life_day(s: dict, result: dict | None = None) -> list[str]:
    """Catch the bank up to `journey.life_day` (idempotent), and hand a card swipe to the result."""
    j = s.get('journey')
    b = get(s)
    if not b:
        return []
    notes: list[str] = []
    swipe = b.pop('ting', 0)
    if swipe and isinstance(result, dict):
        result['card_swipe'] = swipe
    if j.get('story'):
        target = int(j['life_day'])
        b['day'] = max(b['day'], target - 400)
        while b['day'] < target:
            b['day'] += 1
            _tick(s, b, b['day'], notes)
    if notes and isinstance(result, dict):
        result.setdefault('effects', []).extend(notes)
    return notes


# ---------------------------------------------------------------- commands
def _amount(p: dict, key: str = 'amount', low: int = 1) -> int:
    e = _core()
    v = p.get(key)
    e.need(type(v) is int and low <= v <= AMOUNT_MAX, f'Số tiền cần là số xu nguyên, ít nhất {_fmt(low)} xu.')
    return v


def _card_payment(b: dict, day: int, amount: int, src: str, auto: bool = False) -> None:
    c = b['card']
    c['bal'] -= amount
    st = c['stmt']
    if st:
        st['paid'] += amount
    c['past_due'] = max(0, c['past_due'] - amount)
    if src == 'acc':
        b['balance'] -= amount
        _log(b, day, 'acc', ('Tự động trả thẻ' if auto else 'Thanh toán thẻ') + f' •••• {c["no"]}', -amount)
    _log(b, day, 'card', 'Thanh toán dư nợ' + (' (tự động)' if auto else ''), amount)


def _src(p: dict) -> str:
    e = _core()
    src = p.get('src', 'acc')
    e.need(src in ('acc', 'cash'), 'Chọn trả từ tài khoản hoặc tiền mặt nhé.')
    return src


def _take(s: dict, b: dict, src: str, amount: int, label: str, day: int) -> None:
    e = _core()
    if src == 'acc':
        e.need(b['balance'] >= amount, f'Tài khoản chỉ còn {_fmt(b["balance"])} xu.', 'not_enough')
        b['balance'] -= amount
        _log(b, day, 'acc', label, -amount)
    else:
        e.need(s['journey']['wallet'] >= amount, f'Tiền mặt chỉ còn {_fmt(max(0, s["journey"]["wallet"]))} xu.', 'not_enough')
        _wallet(s, -amount, label)


def _loan(b: dict, lid) -> dict:
    e = _core()
    ln = next((x for x in b['loans'] if x['id'] == lid), None)
    e.need(ln, 'Không tìm thấy khoản vay này.')
    return ln


def _payoff(ln: dict, day: int) -> dict:
    """Early repayment: overdue rows in full, the rest of the principal, interest for the days used, a small fee."""
    overdue = sum(r['amount'] - r['paid'] for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount'])
    future = [r for r in ln['rows'] if r['due'] > day and r['paid'] < r['amount']]
    principal = sum(r['principal'] for r in future)
    used = 0
    if future:
        start = future[0]['due'] - LOAN_PERIOD
        used = _ceil_div(principal * ln['bp'] * max(0, day - start), 10000 * LOAN_PERIOD)
    fee = max(EARLY_FEE_MIN, _pct_of(principal, EARLY_FEE_PCT)) if principal else 0
    return dict(overdue=overdue, principal=principal, interest=used, fee=fee, total=overdue + principal + used + fee,
                saved=sum(r['interest'] for r in future) - used)


def apply(s: dict, name: str, p: dict) -> dict:
    """`jr_bk_*` commands. Everything is checked before anything changes (except the declines,
    which are normal results: the bank's inquiry stays on the record)."""
    e = _core()
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác ngân hàng không hợp lệ.', 'unknown_action')
    need(j['story'], 'Ngân hàng chỉ có trong chế độ hành trình.', 'story_only')
    day = j['life_day']
    b = get(s)
    if name == 'jr_bk_open':
        need(b is None, 'Bạn đã có tài khoản ở Ngân hàng Phố rồi.')
        j['bank'] = b = initial(int(j.get('seed', 0)), day)
        _inbox(b, day, 'sms', f'{K.BANK_NAME}: Chào mừng quý khách. Số tài khoản {b["no"]}. Điểm tín dụng khởi đầu {SCORE_START}.')
        return dict(message=f'Đã mở tài khoản {K.BANK_NAME}, số {b["no"]}. Nộp tiền mặt vào để bắt đầu nhé.')
    need(b is not None, 'Mở tài khoản Ngân hàng Phố trước nhé.', 'no_account')
    c = b['card']
    if name == 'jr_bk_deposit':
        amount = _amount(p)
        need(j['wallet'] >= amount, f'Tiền mặt chỉ còn {_fmt(max(0, j["wallet"]))} xu.', 'not_enough')
        _wallet(s, -amount, f'Nộp tiền vào tài khoản {K.BANK_SHORT}')
        b['balance'] += amount
        _log(b, day, 'acc', 'Nộp tiền mặt tại quầy', amount)
        return dict(message=f'Đã nộp {_fmt(amount)} xu vào tài khoản. Số dư {_fmt(b["balance"])} xu.')
    if name == 'jr_bk_withdraw':
        amount = _amount(p)
        atm = p.get('atm', 'own')
        need(atm in K.ATM, 'Chọn cây ATM nhé.')
        fee = ATM_OTHER_FEE if atm == 'other' else 0
        need(b['balance'] >= amount + fee, f'Tài khoản chỉ còn {_fmt(b["balance"])} xu' + (f' (phí rút {fee} xu).' if fee else '.'), 'not_enough')
        b['balance'] -= amount
        _log(b, day, 'acc', f'Rút tiền · {K.ATM[atm]}', -amount)
        if fee:
            b['balance'] -= fee
            b['stats']['fees'] += fee
            _log(b, day, 'acc', 'Phí rút tiền ATM khác ngân hàng', -fee)
        _wallet(s, amount, f'Rút tiền từ tài khoản {K.BANK_SHORT}')
        return dict(message=f'Đã rút {_fmt(amount)} xu tiền mặt' + (f', phí {fee} xu.' if fee else '.'))
    if name == 'jr_bk_save':
        term = p.get('term')
        need(type(term) is int and (term == 0 or term in TERM_RATE), 'Chọn kỳ hạn gửi nhé.')
        amount = _amount(p, low=1 if term == 0 else SAVE_MIN)
        src = _src(p)
        renew = p.get('renew', False)
        need(type(renew) is bool, 'Chọn có tái tục hay không nhé.')
        if term:
            need(len(b['terms']) < TERMS_MAX, f'Mỗi người mở tối đa {TERMS_MAX} sổ có kỳ hạn cùng lúc.')
        _take(s, b, src, amount, f'Gửi tiết kiệm {K.TERMS[term].lower()}', day)
        if term == 0:
            b['demand'] += amount
            _log(b, day, 'sav', 'Gửi tiết kiệm không kỳ hạn', amount)
            return dict(message=f'Đã gửi {_fmt(amount)} xu không kỳ hạn, lãi {year_text(DEMAND_BP * YEAR_DAYS)}, cộng mỗi ngày.')
        t = dict(id=_seq(b, 't'), amount=amount, term=term, rate=TERM_RATE[term], start=day, due=day + term, renew=renew)
        b['terms'].append(t)
        _log(b, day, 'sav', f'Mở sổ {K.TERMS[term].lower()}', amount)
        gain = term_interest(amount, t['rate'], term)
        return dict(message=f'Đã mở sổ {K.TERMS[term].lower()} {_fmt(amount)} xu, lãi {year_text(t["rate"])}. Đáo hạn {dy.on_day(s, t["due"])}, '
                            f'lãi dự kiến {_fmt(gain) + " xu" if gain else "dưới 1 xu (gửi nhiều hơn để thấy lãi)"}'
                            + (', tới hạn tự tái tục.' if renew else '.'))
    if name == 'jr_bk_unsave':
        tid = p.get('id')
        if tid == 'demand':
            amount = _amount(p)
            need(b['demand'] >= amount, f'Sổ không kỳ hạn chỉ có {_fmt(b["demand"])} xu.', 'not_enough')
            b['demand'] -= amount
            if not b['demand']:
                b['pend'] = 0
            _log(b, day, 'sav', 'Rút tiết kiệm không kỳ hạn', -amount)
            b['balance'] += amount
            _log(b, day, 'acc', 'Từ sổ tiết kiệm không kỳ hạn', amount)
            return dict(message=f'Đã chuyển {_fmt(amount)} xu từ sổ tiết kiệm về tài khoản.')
        t = next((x for x in b['terms'] if x['id'] == tid), None)
        need(t, 'Không tìm thấy sổ tiết kiệm này.')
        need(p.get('confirm') is True, 'Xác nhận tất toán sổ trước hạn.')
        held = max(0, day - t['start'])
        gain = t['amount'] * DEMAND_BP * held // 10000
        lost = term_interest(t['amount'], t['rate'], t['term']) - gain
        b['terms'].remove(t)
        b['balance'] += t['amount'] + gain
        b['stats']['interest_in'] += gain
        _log(b, day, 'sav', f'Tất toán trước hạn sổ {K.TERMS[t["term"]].lower()}', -t['amount'])
        _log(b, day, 'acc', f'Tất toán sớm: gốc {_fmt(t["amount"])} + lãi không kỳ hạn {_fmt(gain)} xu', t['amount'] + gain)
        return dict(message=f'Đã tất toán sớm: nhận {_fmt(t["amount"] + gain)} xu về tài khoản. '
                            f'Rút trước hạn nên chỉ hưởng lãi không kỳ hạn (bớt {_fmt(lost)} xu so với giữ đến hạn).')
    if name == 'jr_bk_card_apply':
        need(c is None, 'Bạn đã có thẻ tín dụng rồi.')
        need(p.get('confirm') is True, 'Xác nhận nộp hồ sơ mở thẻ.')
        offer = card_offer(s, b)
        if offer['why'] != 'many':
            b['inq'] = (b['inq'] + [day])[-INQ_MAX:]
            _score(b, day, 'inquiry')
        if not offer['ok']:
            return dict(message=f'Hồ sơ mở thẻ chưa được duyệt. {offer["text"]}', approved=False)
        b['card'] = dict(no=_digits(j.get('seed', 0), f'card|{b["stats"]["loans_closed"]}|{b["seq"]}', 4), limit=offer['limit'], bal=0,
                         open_day=day, cycle=day, stmt=None, stmt_n=0, cash=0, cash_day=day, past_due=0, late_day=0, autopay='off')
        _log(b, day, 'card', f'Mở thẻ, hạn mức {_fmt(offer["limit"])} xu', 0)
        _inbox(b, day, 'sms', f'{K.BANK_NAME}: Thẻ tín dụng •••• {b["card"]["no"]} đã được kích hoạt, hạn mức {_fmt(offer["limit"])} xu. '
                              f'Sao kê mỗi {CARD_CYCLE} ngày, kỳ đầu vào Ngày {day + CARD_CYCLE}, hạn thanh toán sau sao kê {CARD_GRACE} ngày.')
        return dict(message=f'Chúc mừng! Thẻ tín dụng được duyệt, hạn mức {_fmt(offer["limit"])} xu.', approved=True)
    if name == 'jr_bk_card_pay':
        need(c, 'Bạn chưa có thẻ tín dụng.')
        need(c['bal'] > 0, 'Thẻ không còn dư nợ.')
        src = _src(p)
        st = c['stmt']
        what = p.get('what')
        if what == 'min':
            amount = max(c['past_due'], (st['min'] - st['paid']) if st else 0)
            need(amount > 0, 'Khoản tối thiểu kỳ này đã trả đủ rồi.')
        elif what == 'stmt':
            amount = (st['amount'] - st['paid']) if st else 0
            need(amount > 0, 'Dư nợ sao kê kỳ này đã trả hết rồi.')
        elif what == 'all':
            amount = c['bal']
        else:
            amount = _amount(p)
        amount = min(amount, c['bal'])
        if src == 'acc':
            need(b['balance'] >= amount, f'Tài khoản chỉ còn {_fmt(b["balance"])} xu.', 'not_enough')
        else:
            need(j['wallet'] >= amount, f'Tiền mặt chỉ còn {_fmt(max(0, j["wallet"]))} xu.', 'not_enough')
            _wallet(s, -amount, f'Trả thẻ tín dụng •••• {c["no"]}')
        _card_payment(b, day, amount, src)
        return dict(message=f'Đã trả {_fmt(amount)} xu cho thẻ. Dư nợ còn {_fmt(c["bal"])} xu.')
    if name == 'jr_bk_card_cash':
        need(c, 'Bạn chưa có thẻ tín dụng.')
        why = card_usable(s, b)
        need(why is None, why or '')
        amount = _amount(p)
        fee = max(CASH_FEE_MIN, _pct_of(amount, CASH_FEE_PCT))
        cap = c['limit'] * CASH_SHARE // 100
        need(c['cash'] + amount <= cap, f'Ứng tiền mặt tối đa {CASH_SHARE}% hạn mức: còn ứng được {_fmt(max(0, cap - c["cash"]))} xu.')
        need(amount + fee <= available(b), f'Hạn mức còn {_fmt(available(b))} xu, chưa đủ cho {_fmt(amount)} xu cộng phí {_fmt(fee)} xu.')
        if c['cash'] == 0:
            c['cash_day'] = day
        c['cash'] += amount
        c['bal'] += amount + fee
        b['stats']['fees'] += fee
        _log(b, day, 'card', 'Ứng tiền mặt tại ATM', -amount)
        _log(b, day, 'card', f'Phí ứng tiền mặt {CASH_FEE_PCT}%', -fee)
        _wallet(s, amount, f'Ứng tiền mặt từ thẻ •••• {c["no"]}')
        b['ting'] = b.get('ting', 0) + amount
        return dict(message=f'Đã ứng {_fmt(amount)} xu tiền mặt, phí {_fmt(fee)} xu. Lãi {_pct_text(CARD_BP)}/ngày tính ngay từ hôm nay.')
    if name == 'jr_bk_card_autopay':
        need(c, 'Bạn chưa có thẻ tín dụng.')
        need(p.get('mode') in AUTOPAYS, 'Chọn cách tự động trả nhé.')
        c['autopay'] = p['mode']
        return dict(message=f'Đã chọn: {K.AUTOPAY[c["autopay"]].lower()}.' if c['autopay'] != 'off' else 'Đã tắt tự động trả thẻ.')
    if name == 'jr_bk_card_close':
        need(c, 'Bạn chưa có thẻ tín dụng.')
        need(c['bal'] == 0, 'Trả hết dư nợ rồi mới hủy thẻ được.')
        need(p.get('confirm') is True, 'Xác nhận hủy thẻ.')
        _log(b, day, 'card', f'Hủy thẻ •••• {c["no"]}', 0)
        b['card'] = None
        return dict(message='Đã hủy thẻ tín dụng.')
    if name == 'jr_bk_loan_apply':
        kind = p.get('kind')
        need(kind in K.LOANS, 'Chọn loại khoản vay nhé.')
        term = p.get('term')
        need(term in LOAN_TERMS, 'Chọn kỳ hạn vay nhé.')
        amount = _amount(p, low=LOAN_MIN)
        need(p.get('confirm') is True, 'Xác nhận ký hợp đồng vay.')
        q = quote(amount, kind, term, day)
        need(p.get('total_interest') == q['interest'], 'Điều khoản vay vừa thay đổi. Xem lại lịch trả nợ rồi ký nhé.', 'stale_quote')
        place = None
        if kind == 'shop':
            place = p.get('career')
            need(place in owned_places(s), 'Chọn một tiệm bạn làm chủ để nhận vốn vay.')
        offer = loan_offer(s, b, kind)
        if offer['why'] not in ('many', 'count', 'same', 'place'):
            b['inq'] = (b['inq'] + [day])[-INQ_MAX:]
            _score(b, day, 'inquiry')
        if not offer['ok']:
            return dict(message=f'Hồ sơ vay chưa được duyệt. {offer["text"]}', approved=False)
        if amount > offer['max']:
            return dict(message=f'Hồ sơ vay chưa được duyệt: với thu nhập hiện tại, ngân hàng chỉ duyệt tối đa {_fmt(offer["max"])} xu.',
                        approved=False)
        if q['installment'] > offer['weekly_room']:
            return dict(message=f'Hồ sơ vay chưa được duyệt. {K.DECLINE["dti"].format(pct=DTI_PCT)}', approved=False)
        ln = dict(id=_seq(b, 'L'), kind=kind, principal=amount, bp=LOAN_BP[kind], term=term, start=day, career=place, rows=q['rows'])
        b['loans'].append(ln)
        label = K.LOANS[kind]['name']
        _log(b, day, 'loan', f'Giải ngân {label.lower()}', amount)
        if kind == 'shop':
            jr = _jr()
            jr._transfer(s, s['careers'][place], amount, f'Vốn vay {K.BANK_SHORT} góp vào quỹ', 'owner_capital')
            where = f'quỹ {jr._place(place)}'
        else:
            b['balance'] += amount
            _log(b, day, 'acc', f'Giải ngân {label.lower()}', amount)
            where = 'tài khoản của bạn'
        return dict(message=f'Hợp đồng đã ký. {_fmt(amount)} xu đã vào {where}. Trả {len(q["rows"])} kỳ, mỗi kỳ khoảng '
                            f'{_fmt(q["installment"])} xu, kỳ đầu {dy.on_day(s, q["rows"][0]["due"])}.', approved=True)
    if name == 'jr_bk_loan_pay':
        ln = _loan(b, p.get('id'))
        src = _src(p)
        rows = [r for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount']]
        if not rows:
            rows = [next(r for r in ln['rows'] if r['paid'] < r['amount'])]
        amount = sum(r['amount'] - r['paid'] for r in rows)
        _take(s, b, src, amount, f'Trả góp {K.LOANS[ln["kind"]]["name"].lower()}', day)
        for r in rows:
            r['paid'] = r['amount']
        _log(b, day, 'loan', f'Trả kỳ {", ".join(str(r["k"]) for r in rows)} · {K.LOANS[ln["kind"]]["name"]}', -amount)
        msg = f'Đã trả {_fmt(amount)} xu cho {_loan_name(ln)}.'
        if all(r['paid'] >= r['amount'] for r in ln['rows']):
            b['loans'].remove(ln)
            b['stats']['loans_closed'] += 1
            _score(b, day, 'loan_done')
            msg += ' Khoản vay đã trả xong!'
        return dict(message=msg)
    if name == 'jr_bk_loan_close':
        ln = _loan(b, p.get('id'))
        src = _src(p)
        need(p.get('confirm') is True, 'Xác nhận tất toán khoản vay trước hạn.')
        off = _payoff(ln, day)
        _take(s, b, src, off['total'], f'Tất toán sớm {K.LOANS[ln["kind"]]["name"].lower()}', day)
        b['stats']['fees'] += off['fee']
        b['loans'].remove(ln)
        b['stats']['loans_closed'] += 1
        _score(b, day, 'loan_done')
        _log(b, day, 'loan', f'Tất toán sớm · phí {_fmt(off["fee"])} xu', -off['total'])
        return dict(message=f'Đã tất toán sớm {_fmt(off["total"])} xu (phí trả trước hạn {_fmt(off["fee"])} xu). '
                            f'Bạn tiết kiệm được {_fmt(max(0, off["saved"]))} xu tiền lãi.')
    if name == 'jr_bk_settings':
        need(p and set(p) <= {'pref', 'sweep'}, 'Thiết lập không hợp lệ.')
        if 'pref' in p:
            need(p['pref'] in PREFS, 'Thiết lập không hợp lệ.')
            b['pref'] = p['pref']
        if 'sweep' in p:
            need(type(p['sweep']) is bool, 'Thiết lập không hợp lệ.')
            b['sweep'] = p['sweep']
        return dict(message='Đã lưu thiết lập ngân hàng.')
    # jr_bk_read
    for m in b['inbox']:
        m['read'] = True
    return dict(message='')


def action(s: dict, name: str, p: dict) -> dict:
    """Entry from journey.action (which runs journey.after and validate_state)."""
    return apply(s, name, p or {})


# ---------------------------------------------------------------- views
def rules() -> dict:
    return dict(demand_bp=DEMAND_BP, demand_rate=DEMAND_BP * YEAR_DAYS, term_rate={str(k): v for k, v in TERM_RATE.items()},
                terms=[0] + sorted(TERM_RATE), month_days=MONTH_DAYS, year_days=YEAR_DAYS, save_min=SAVE_MIN, terms_max=TERMS_MAX,
                atm_fee=ATM_OTHER_FEE, card_cycle=CARD_CYCLE, card_grace=CARD_GRACE, card_min_pct=CARD_MIN_PCT,
                card_min_floor=CARD_MIN_FLOOR, card_bp=CARD_BP, card_late_fee=CARD_LATE_FEE, cash_fee_pct=CASH_FEE_PCT,
                cash_fee_min=CASH_FEE_MIN, cash_share=CASH_SHARE, loan_bp=dict(LOAN_BP), loan_terms=list(LOAN_TERMS),
                loan_period=LOAN_PERIOD, loan_min=LOAN_MIN, loan_late_pct=LOAN_LATE_PCT, loan_late_min=LOAN_LATE_MIN,
                early_fee_pct=EARLY_FEE_PCT, early_fee_min=EARLY_FEE_MIN, dti_pct=DTI_PCT, score_min=SCORE_MIN,
                score_max=SCORE_MAX, card_score=CARD_MIN_SCORE, bad_misses=BAD_MISSES, bad_days=BAD_DAYS)


def public(s: dict) -> dict:
    j = s['journey']
    b = get(s)
    base = dict(open=b is not None, story=bool(j.get('story')), name=K.BANK_NAME, wallet=j['wallet'], life_day=j['life_day'],
                rules=rules(), holder=s.get('name') or '')
    if not b:
        return base
    day = j['life_day']
    c = b['card']
    band, tone = _band(b['score'])
    card = None
    if c:
        st = c['stmt']
        card = dict(no=c['no'], limit=c['limit'], bal=c['bal'], available=available(b), util=c['bal'] * 100 // c['limit'] if c['limit'] else 0,
                    stmt=dict(st, left=max(0, st['amount'] - st['paid']), min_left=max(0, st['min'] - st['paid']), days_left=st['due'] - day) if st else None,
                    next_stmt=c['cycle'] + CARD_CYCLE * ((day - c['cycle']) // CARD_CYCLE + 1), autopay=c['autopay'],
                    past_due=c['past_due'], cash=c['cash'], cash_room=max(0, c['limit'] * CASH_SHARE // 100 - c['cash']),
                    locked=card_usable(s, b), open_day=c['open_day'])
    terms = []
    for t in b['terms']:
        gain = term_interest(t['amount'], t['rate'], t['term'])
        held = max(0, min(t['term'], day - t['start']))
        terms.append(dict(t, name=K.TERMS[t['term']], interest=gain, value=t['amount'] + gain, days_left=max(0, t['due'] - day),
                          accrued=term_interest(t['amount'], t['rate'], held), rate_text=year_text(t['rate']),
                          early=t['amount'] * DEMAND_BP * held // 10000))
    inc = income(s)  # once: the card and loan offers read the same window
    loans = []
    for ln in b['loans']:
        nxt = next((r for r in ln['rows'] if r['paid'] < r['amount']), None)
        loans.append(dict(ln, name=K.LOANS[ln['kind']]['name'], emoji=K.LOANS[ln['kind']]['emoji'],
                          left=sum(r['amount'] - r['paid'] for r in ln['rows']),
                          principal_left=sum(r['principal'] for r in ln['rows'] if r['paid'] < r['amount']),
                          next=nxt, overdue=sum(r['amount'] - r['paid'] for r in ln['rows'] if r['due'] <= day and r['paid'] < r['amount']),
                          payoff=_payoff(ln, day), place=_jr()._place(ln['career']) if ln['career'] else None))
    return dict(base, no=b['no'], balance=b['balance'], open_day=b['open_day'],
                savings=dict(demand=b['demand'], total=_savings_total(b), daily_milli=b['demand'] * DEMAND_BP // 10, terms=terms),
                card=card, card_offer=None if c else card_offer(s, b, inc),
                loans=loans, loan_offers={k: loan_offer(s, b, k, inc) for k in K.LOANS},
                loan_kinds={k: dict(v) for k, v in K.LOANS.items()},
                places={cid: _jr()._place(cid) for cid in owned_places(s)},
                score=dict(value=b['score'], band=band, tone=tone, log=list(reversed(b['score_log'])), tips=list(K.SCORE_TIPS),
                           inquiries=_inq_recent(b, day)),
                bad_until=b['bad_until'] if b['bad_until'] > day else 0, overdue=_overdue(b, day), misses=b['misses'],
                log=list(reversed(b['log'])), inbox=list(reversed(b['inbox'])), unread=sum(1 for m in b['inbox'] if not m['read']),
                pref=b['pref'], sweep=b['sweep'], stats=dict(b['stats']), income=inc,
                prefs=dict(K.PAY_PREF), autopays=dict(K.AUTOPAY), atms=dict(K.ATM), term_names={str(k): v for k, v in K.TERMS.items()})


# ---------------------------------------------------------------- validation
def validate(s: dict) -> None:
    e = _core()
    need, integer, txt = e.need, e.integer, e.clean_text
    j = s.get('journey')
    if not isinstance(j, dict) or j.get('bank') is None:
        return
    b = j['bank']
    bad = 'Dữ liệu ngân hàng không hợp lệ.'
    keys = set(initial())
    need(isinstance(b, dict) and keys <= set(b) <= keys | {'ting'} and b['v'] == VERSION, bad, 'invalid_save')
    if 'ting' in b:
        integer(b['ting'], 1, AMOUNT_MAX * 10)
    need(isinstance(b['no'], str) and b['no'].isdigit() and len(b['no']) == 10, bad)
    integer(b['open_day'], 1, 10**6)
    integer(b['day'], b['open_day'], 10**6)
    need(b['day'] <= j['life_day'], bad)
    for k in ('balance', 'demand'):
        integer(b[k], 0, BAL_MAX)
    integer(b['pend'], 0, 10**4)
    integer(b['score'], SCORE_MIN, SCORE_MAX)
    integer(b['misses'], 0, 1000)
    integer(b['bad_until'], 0, 10**6 + BAD_DAYS)
    integer(b['age_pts'], 0, AGE_CAP)
    integer(b['seq'], 0, 10**9)
    need(b['pref'] in PREFS and type(b['sweep']) is bool, bad)
    need(isinstance(b['stats'], dict) and set(b['stats']) == set(STATS), bad)
    for v in b['stats'].values():
        integer(v, 0, 10**9)
    need(isinstance(b['inq'], list) and len(b['inq']) <= INQ_MAX, bad)
    for d in b['inq']:
        integer(d, 1, 10**6)
    need(isinstance(b['terms'], list) and len(b['terms']) <= TERMS_MAX, bad)
    for t in b['terms']:
        need(isinstance(t, dict) and set(t) == {'id', 'amount', 'term', 'rate', 'start', 'due', 'renew'}
             and t['rate'] is not None and t['rate'] in (TERM_RATE.get(t['term']), LEGACY_RATE.get(t['term']))
             and t['due'] == t['start'] + t['term'] and type(t['renew']) is bool, bad)
        txt(t['id'], 16)
        integer(t['amount'], SAVE_MIN, BAL_MAX)
        integer(t['start'], 1, 10**6)
    c = b['card']
    if c is not None:
        need(isinstance(c, dict) and set(c) == {'no', 'limit', 'bal', 'open_day', 'cycle', 'stmt', 'stmt_n', 'cash', 'cash_day',
                                                 'past_due', 'late_day', 'autopay'}, bad)
        need(isinstance(c['no'], str) and c['no'].isdigit() and len(c['no']) == 4 and c['autopay'] in AUTOPAYS, bad)
        integer(c['limit'], LIMIT_MIN, LIMIT_MAX)
        integer(c['bal'], 0, BAL_MAX)
        for k in ('open_day', 'cycle', 'cash_day'):
            integer(c[k], 1, 10**6)
        for k in ('stmt_n', 'cash', 'past_due', 'late_day'):
            integer(c[k], 0, BAL_MAX)
        st = c['stmt']
        if st is not None:
            need(isinstance(st, dict) and set(st) == {'n', 'day', 'amount', 'min', 'due', 'paid', 'done'} and type(st['done']) is bool, bad)
            for k in ('n', 'day', 'due'):
                integer(st[k], 1, 10**6 + CARD_GRACE)
            for k in ('amount', 'min', 'paid'):
                integer(st[k], 0, BAL_MAX)
            need(st['min'] <= st['amount'] and st['due'] == st['day'] + CARD_GRACE, bad)
    need(isinstance(b['loans'], list) and len(b['loans']) <= LOANS_MAX, bad)
    for ln in b['loans']:
        need(isinstance(ln, dict) and set(ln) == {'id', 'kind', 'principal', 'bp', 'term', 'start', 'career', 'rows'}
             and ln['kind'] in K.LOANS and ln['bp'] == LOAN_BP[ln['kind']] and ln['term'] in LOAN_TERMS, bad)
        txt(ln['id'], 16)
        integer(ln['principal'], LOAN_MIN, AMOUNT_MAX)
        integer(ln['start'], 1, 10**6)
        need(ln['career'] is None or ln['career'] in s['careers'], bad)
        need((ln['kind'] == 'shop') == (ln['career'] is not None), bad)
        rows = ln['rows']
        need(isinstance(rows, list) and len(rows) == ln['term'] // LOAN_PERIOD, bad)
        for i, r in enumerate(rows):
            need(isinstance(r, dict) and set(r) == {'k', 'due', 'principal', 'interest', 'amount', 'paid', 'fee', 'late'}
                 and r['k'] == i + 1 and r['due'] == ln['start'] + LOAN_PERIOD * (i + 1) and type(r['late']) is bool, bad)
            for k in ('principal', 'interest', 'amount', 'paid', 'fee'):
                integer(r[k], 0, AMOUNT_MAX * 2)
            need(r['amount'] == r['principal'] + r['interest'] + r['fee'] and r['paid'] <= r['amount'], bad)
        need(sum(r['principal'] for r in rows) == ln['principal'], bad)
    need(isinstance(b['score_log'], list) and len(b['score_log']) <= SCORE_LOG_MAX, bad)
    for r in b['score_log']:
        need(isinstance(r, dict) and set(r) == {'day', 'why', 'delta', 'score'} and r['why'] in K.SCORE_WHY, bad)
        integer(r['day'], 1, 10**6)
        integer(r['delta'], -1000, 1000)
        integer(r['score'], SCORE_MIN, SCORE_MAX)
    need(isinstance(b['log'], list) and len(b['log']) <= LOG_MAX, bad)
    for r in b['log']:
        need(isinstance(r, dict) and set(r) == {'id', 'day', 'acc', 'text', 'amt', 'bal'} and r['acc'] in ACCOUNTS, bad)
        txt(r['id'], 16)
        txt(r['text'], 120)
        integer(r['day'], 1, 10**6)
        integer(r['amt'], -BAL_MAX, BAL_MAX)
        integer(r['bal'], -BAL_MAX, BAL_MAX * 2)
    need(isinstance(b['inbox'], list) and len(b['inbox']) <= INBOX_MAX, bad)
    for m in b['inbox']:
        need(isinstance(m, dict) and set(m) == {'id', 'day', 'kind', 'text', 'read'} and m['kind'] in INBOX_KINDS
             and type(m['read']) is bool, bad)
        txt(m['id'], 16)
        txt(m['text'], 300)
        integer(m['day'], 1, 10**6)
