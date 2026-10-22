"""📈 Thu nhập +50 % for everyone.

Owner 22/10: "tăng 50% thu nhập tất cả mọi người nữa nhé", then "tăng cả tiền quầy,.. mọi thứ luôn mn kiếm được nhé".
Everything a player EARNS from the game is worth INCOME_PCT % of what it paid before; prices, costs and every other
flow stay as they were. One constant, a few hooks where earnings enter a player's pockets:

* Finished jobs (engine.task_done → on_job): the share of what the job earned, a shop's margin (`bonus_base`, as the
  🔧 gear counts it) or else the whole pay; the "Hoàn thành:" row itself is not counted again.
* Workplace funds (engine.money → on_money): a positive row of an EARN category (the jobs' other payments, tips,
  wages and salaries, story / quest / skill / event rewards, the team's and the manager's bonuses, and the % bonuses
  other modules book on an earning: 🔧 gear, 🧩 Phúc lợi, 🐾 pets, 💰 Tiền công, ⏱️ tăng ca, 💛 khách quen …) adds
  INCOME_PCT − 100 % of it to ONE row a day of that workplace, LABEL, ref REF, category 'other_income' (no period tax,
  never another row per job: the save's ledger stays small). Every bonus is computed by its own module on the
  un-boosted figure and gets its own share here, so a day's earnings are × INCOME_PCT / 100 exactly, never twice.
  Its rows are summed by day_total for the day's summary ('incomeboost') and kept out of the 🔥 x3 base net.
* Staff orders (workplace_business._finish, rows booked directly): on_staff, the share of the order's positive margin
  and its 40 % bonus (not of the revenue: the goods' cost is not earned).
* Quầy (quay_business.sale): take_percent, the owner's take on the margin, (100 + percent) × INCOME_PCT / 100 − 100,
  exactly as owner 15/10's ×1.6 was built (staff sales, the owner's own sales and online ones; never a player visitor).
* Contract settlements (career_scale_contracts, career_specialism_jobs): the share of the receipt's positive net.
* The shift's wallet extras (journey._end_of_day): 🔥 x3, 🔨 Biển đẹp and 🧰 Đồ nghề độc bản count on the shift's base
  net × INCOME_PCT / 100 (scale), under their own caps.
* Wallet / bank earnings outside a fund (earned): a tenant's rent (game/housing.py), a delivery contract's bonus
  (game/courier.py), a 🧰 chest in the street (game/town_treasure.py).

Never: refunds, recoveries, insurance, compensation, gifts and envelopes, grants and admin / system gifts, transfers
(owner capital, draws, salary to the wallet), money between players (the service market, a real player's order, the
Phố nghề market, a hired player's wage, a visitor's bill: skip() around them), bank and savings interest, the Chợ đen,
sales of what a player owns.

MNL_INCOME_BOOST_OFF=1 turns it off (the tests set it, so older tests keep their exact pay; tests/test_income_boost.py
turns it on). Nothing is saved: the rows are ordinary ledger rows, the rest is arithmetic.
"""
from __future__ import annotations

import contextlib
import contextvars
import hashlib
import os

INCOME_PCT = 150                 # owner 22/10: +50 % on everything earned
LABEL = f'📈 Thu nhập +{INCOME_PCT - 100}%'
REF = 'income-boost'
CATEGORY = 'other_income'
LOOK = 60                        # today's row is looked for among the last rows only
ROW_MAX = 10**8                  # past this a day's row starts a new one (a row holds at most 10**9)
# The fund categories that are earnings (engine.money, after operations.classify_money): what customers pay, wages,
# tips, rewards and the bonuses booked on them. Refunds, recoveries, compensation, gifts, grants, capital and the
# scale_* settlements (booked through on_settle) are not.
EARN = frozenset((
    'revenue', 'sales', 'service', 'room', 'tip', 'salary', 'overtime', 'commission', 'promotion',
    'bonus', 'office_bonus', 'audit_bonus', 'board_bonus', 'event_income', 'other_income', 'debt_paid', 'debt_repaid',
    'skill_reward', 'story_reward', 'situation_reward', 'goal_reward', 'festival_reward', 'activity_reward',
))

_SKIP = contextvars.ContextVar('income_boost_skip', default=False)


def off() -> bool:
    return os.environ.get('MNL_INCOME_BOOST_OFF', '').strip() not in ('', '0')


def _story(s) -> bool:
    j = s.get('journey') if isinstance(s, dict) else None
    return isinstance(j, dict) and bool(j.get('story'))


def on(s=None) -> bool:
    """The boost applies (to this save, when given: story mode only, like every pay buff)."""
    return not off() and (s is None or _story(s))


def part(amount: int, key: str = '') -> int:
    """The extra on an earning of `amount` xu: amount × (INCOME_PCT − 100) / 100, its fraction rounded up or down by a
    hash of `key` (deterministic for a retried command, fair on average, no state). 0 when off or not positive."""
    if off() or type(amount) is not int or amount <= 0:
        return 0
    whole, frac = divmod(amount * (INCOME_PCT - 100), 100)
    if frac and int(hashlib.sha256(f'ib|{key}|{amount}'.encode()).hexdigest()[:8], 16) % 100 < frac:
        whole += 1
    return whole


def scale(amount: int, key: str = '') -> int:
    """`amount` with the boost (a base a multiplier counts on, or an earning paid in place)."""
    return amount + part(amount, key) if type(amount) is int and amount > 0 else amount


def earned(s, amount: int, key: str = '') -> int:
    """An earning paid straight to the wallet or the bank (rent, a contract bonus, a chest): `amount` boosted for a story
    save while on."""
    return scale(amount, key) if on(s) else amount


def take_percent(percent: int) -> int:
    """A quầy's profit bonus percent so that the owner's take, margin × (100 + percent) / 100, is × INCOME_PCT / 100."""
    if off() or type(percent) is not int:
        return percent
    return (100 + percent) * INCOME_PCT // 100 - 100


@contextlib.contextmanager
def skip():
    """Money between players (or anything else that is not earned) booked with an earning's category: no boost."""
    token = _SKIP.set(True)
    try:
        yield
    finally:
        _SKIP.reset(token)


# ------------------------------------------------------------------ the fund's row
def book(c: dict, extra: int) -> int:
    """Add `extra` xu to the workplace's fund as today's LABEL row (one a day; the cash book stays whole: opening
    balance + rows == fund). Earnings, not an owner transfer: in the day's income and net like any earning."""
    if type(extra) is not int or extra <= 0:
        return 0
    from . import operations as ops
    c['money'] += extra
    c['earnings'] += extra
    rows = c['ops']['finance']['ledger']
    for r in reversed(rows[-LOOK:]):
        if (isinstance(r, dict) and r.get('ref') == REF and r.get('day') == c['day'] and r.get('category') == CATEGORY
                and type(r.get('amount')) is int and r['amount'] + extra <= ROW_MAX):
            r['amount'] += extra
            r['turn'] = c['turn']
            return extra
    ops.record_money(c, extra, LABEL, REF, CATEGORY)
    return extra


def on_money(s: dict, c: dict, amount: int, reason: str, ref, category) -> int:
    """engine.money, after a row is booked: its share when it is an earning (EARN), else 0."""
    if amount <= 0 or _SKIP.get() or not on(s) or ref == REF:
        return 0
    from .operations import classify_money
    if classify_money(amount, reason, category) not in EARN:
        return 0
    return book(c, part(amount, f'{ref}|{reason}|{c.get("day")}'))


def on_job(s: dict, c: dict, base: int, ref) -> int:
    """engine.task_done: a finished job's share, on what it earned (a shop's margin, `bonus_base`, like the 🔧 gear's
    bonus; else the whole pay). Its "Hoàn thành:" row itself is booked under skip()."""
    if not on(s) or _SKIP.get():
        return 0
    return book(c, part(max(0, base), f'job|{ref}|{c.get("day")}'))


def on_staff(s: dict, c: dict, base: int, ref: str) -> int:
    """A staff order's positive margin and its 40 % bonus (workplace_business._finish, after both are booked)."""
    if not on(s) or _SKIP.get():
        return 0
    return book(c, part(max(0, base), f'staff|{ref}|{c.get("day")}'))


def settle_part(s: dict, net: int, ref: str) -> int:
    """A management / specialist contract's share of its positive net (booked by the caller as a scale_ row)."""
    return part(max(0, net), f'settle|{ref}') if on(s) else 0


def day_total(c: dict, day: int) -> int:
    """This module's rows of a workplace's day (journey._base_net keeps them out of the 🔥 x3 base: x3 counts on the
    base × INCOME_PCT / 100 itself, never on these rows as well)."""
    rows = ((c.get('ops') or {}).get('finance') or {}).get('ledger') or ()
    return sum(r['amount'] for r in rows if isinstance(r, dict) and r.get('day') == day and r.get('ref') == REF
               and r.get('category') == CATEGORY and type(r.get('amount')) is int and r['amount'] > 0)
