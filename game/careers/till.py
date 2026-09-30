"""Cash at the counter: the customer's notes, the change you count, and what the
customer does about it. Shared by the careers where the player counts change by
hand: delivery COD (building blocks only), the homestay checkout, the clothing shop,
the pet shop and the trà đá stall. The grocery counter keeps its own change logic.

A career keeps one record per task, `t['cash']`, made by `new()` once the price
is final: the notes the customer hands over are rolled once from the task id and
stored. The player builds the change from DENOMS (the tray lives in the browser
and comes with the hand-over as a list of notes), then the career calls:

1. `check(s, c, t, rec, change, who)` before the customer's reaction:
   * short change: a careful customer counts it at once and asks for the rest.
     The hand-over stops (`stop=True`), the player adds notes and hands over
     again; a small slip is named in the review. Anyone else takes it home.
2. `cq.react(...)` as usual (only the mistakes the customer saw at the counter);
3. `settle(s, c, t, rec, react, who)` before `kit.complete()`:
   * short change nobody caught: found at home, a 2★ review and, some days, a
     report on the app;
   * excess change: an honest customer gives it back; anyone else keeps it and
     the shop loses exactly that much (`loss`, taken off the pay);
   * exact change: a seeded chance of "khỏi thối, giữ tiền lẻ đi". The change
     stays in the till as a tip (money category 'tip', t['tip_given']), once.
     Refuse and walk-out reactions never tip.

Short payment (game/short_pay.py): a till record made with the task (`new(price, id, c=c, t=t)`)
may roll, once, a customer who hands over less than the bill. The notes on the counter show it;
`short_action()` is the career's `<prefix>short` command (count again, remind, call the ward
police, let it go…), `check()` waits while that decision is open, and `settle()` takes what was
never paid off the pay (`loss`), or names it at the till count when nobody noticed.

Everything is decided from the task id and the customer's persona, so the same
hand-over always goes the same way; nothing is rolled twice and nothing pays twice.
"""
from __future__ import annotations

import hashlib

from .. import consequences as cq
from .. import short_pay as sp_
from . import kit

DENOMS = (1, 2, 5, 10, 20, 50, 100, 200, 500)
NOTES = (10, 20, 50, 100, 200, 500)
MAX_TRAY = 40
STYLES = ('exact', 'round', 'note', 'big')
OUTCOMES = (None, 'exact', 'keep', 'missed', 'returned', 'kept', 'void')
# Who counts every coin at the counter, who gives back extra change, who waves the change off.
CAREFUL = {'picky', 'sour', 'bossy', 'knowitall', 'parent_strict', 'parent_knowitall', 'entitled'}
HONEST = {'warm', 'quiet', 'parent_kind', 'parent_worried'}
NEVER_HONEST = {'rude', 'entitled', 'troll', 'drama'}
GENEROUS = dict(warm=35, parent_kind=30, genz=25, quiet=20, bossy=20, parent_worried=15, drama=10,
                sour=4, picky=4, knowitall=6, rude=0, entitled=0, troll=5, parent_strict=5, parent_knowitall=5, parent_rude=0)
KEEP_MAX = 20            # "khỏi thối" only for small change


def _hash(*parts) -> int:
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _persona(c: dict, t: dict) -> str:
    try:
        return cq.persona(c, t)
    except Exception:  # an old task whose npc no longer has a persona row
        return 'quiet'


# ---------------------------------------------------------------- the customer's notes
def greedy(amount: int) -> list[int]:
    """The fewest notes and coins for `amount` (how a till counts)."""
    out, left = [], max(0, int(amount))
    for d in reversed(DENOMS):
        while left >= d and len(out) < MAX_TRAY:
            out.append(d)
            left -= d
    return out


def tender(price: int, seed: str, style: str | None = None) -> list[int]:
    """What the customer hands over for `price` (rolled once from `seed`; store the result)."""
    price = max(1, int(price))
    if style is None:
        roll = _hash('till-style', seed) % 100
        style = 'exact' if roll < 12 else 'round' if roll < 42 else 'note' if roll < 85 else 'big'
    if style == 'exact':
        return greedy(price)
    if style == 'round':
        step = 50 if price % 10 == 0 else 10
        return greedy(-(-price // step) * step)
    note = next((n for n in NOTES if n >= price), None)
    if note is None:
        return [500] * min(20, -(-price // 500))
    if style == 'big':
        bigger = next((n for n in NOTES if n > note), None)
        return [bigger or note]
    return [note]


def new(price: int, seed: str, style: str | None = None, c: dict | None = None, t: dict | None = None) -> dict:
    """The customer's notes for this bill. With the workplace and the task, a customer may pay short
    (game/short_pay.py, rolled once from the task id; a story already under way for the same bill is kept)."""
    price = max(1, int(price))
    rec = dict(v=1, price=price, tender=tender(price, seed, style), change=[], asked=0,
               outcome=None, short=0, over=0, tip=0, loss=0)
    if isinstance(c, dict) and isinstance(t, dict):
        old = t.get('cash')
        sp = sp_.carry(old, price)
        if sp:
            rec.update(tender=list(old['tender']), sp=sp, counted=bool(old.get('counted')))
        else:
            sp = sp_.roll(c, t, price)
            if sp:
                rec.update(tender=sp_.tender(price, sp), sp=sp)
    return rec


def due(rec: dict) -> int:
    """Change owed (negative while a customer who paid short has not made it up)."""
    return sum(rec['tender']) - rec['price']


def notes(value) -> list[int]:
    """The tray the browser sends with the hand-over: a list of notes from DENOMS."""
    kit.need(isinstance(value, list) and len(value) <= MAX_TRAY and all(type(x) is int and x in DENOMS for x in value),
             'Khay thối tiền không hợp lệ.')
    return list(value)


# ---------------------------------------------------------------- the customer's side
def careful(c: dict, t: dict, short: int, need: int) -> bool:
    """Counts the change at the counter: picky people always, anyone when the gap is big."""
    if _persona(c, t) in CAREFUL or short >= max(10, need // 2 + 1):
        return True
    return _hash('till-careful', t['id']) % 100 < 45


def honest(c: dict, t: dict) -> bool:
    who = _persona(c, t)
    if who in NEVER_HONEST:
        return False
    return _hash('till-honest', t['id']) % 100 < (85 if who in HONEST else 40)


def waves_off(c: dict, t: dict, need: int) -> bool:
    """"Khỏi thối, giữ tiền lẻ đi": only small change, and only some people."""
    if not 0 < need <= KEEP_MAX:
        return False
    chance = GENEROUS.get(_persona(c, t), 12) // (1 if need <= 10 else 2)
    return _hash('till-keep', t['id']) % 100 < chance


# ---------------------------------------------------------------- what happens (building blocks)
def ask_rest(t: dict, short: int, who: str = 'Khách') -> str:
    """A careful customer counts the change at once and asks for the rest. The caller stops the
    hand-over so the player adds the notes themselves; `asked_slip()` names it in the review later."""
    t['mistakes'] += 1
    return f'{who} đếm lại: “Thối thiếu {short} xu rồi nè.” Thối thêm cho đủ rồi đưa lại.'


def asked_slip(t: dict) -> None:
    """After cq.react: the customer already complained at the counter and the player gave the rest,
    so it is a small slip for the review, not a second telling-off (and no money off)."""
    cq.slip(t, 'change_short', 1, 'Thối thiếu tiền, tôi phải đếm lại ngay tại chỗ mới đòi đủ.', 'thối thiếu, khách phải nhắc')


def found_at_home(s: dict, c: dict, t: dict, short: int) -> str:
    """Short change nobody caught at the counter (call after cq.react, before kit.complete):
    a 2★ review that names it and, some days, a report on the app."""
    t['mistakes'] += 1
    cq.slip(t, 'change_home', 3, f'Về nhà đếm lại mới thấy bị thối thiếu {short} xu. Buôn bán kiểu này thì ai dám quay lại.',
            f'thối thiếu {short} xu')
    if _hash('till-report', t['id']) % 100 < 50 or short >= 20:
        return ' '.join(cq._escalate(s, c, t))
    return ''


def excess(c: dict, t: dict, over: int, who: str = 'Khách') -> tuple[bool, str]:
    """Extra change: (given back?, what happened). The caller takes a kept excess off the pay."""
    t['mistakes'] += 1
    if honest(c, t):
        return True, f'{who} trả lại {over} xu: “Thối dư nè, coi chừng lỗ nha!”'
    return False, f'Tối kiểm két mới thấy thối dư {over} xu, khách cầm về luôn rồi.'


def keep_change(s: dict, c: dict, t: dict, need: int, react: dict | None = None, who: str = 'Khách') -> tuple[int, str]:
    """Exact change: some customers wave it off. Books the tip once (category 'tip', t['tip_given'])."""
    kind = (react or {}).get('kind', 'accept')
    if kind != 'accept' or cq.slips(t) or t['mistakes'] or t.get('tip_given') or not waves_off(c, t, need):
        return 0, ''
    kit.money(s, c, need, f'Khách cho giữ tiền thối: {t.get("title", "")}'[:120], t['id'], 'tip')
    t['tip_given'] = need
    return need, f'{who} xua tay: “Khỏi thối, giữ tiền lẻ đi!” (+{need} xu tip)'


# ---------------------------------------------------------------- the hand-over (with a record)
def check(s: dict, c: dict, t: dict, rec: dict, change: list, who: str = 'Khách') -> dict:
    """Before the reaction: store the tray; a careful customer who was short-changed stops here.
    Returns dict(stop, message)."""
    kit.need(rec.get('outcome') is None, 'Tiền của khách này đã tính xong.')
    kit.need(not sp_.pending(rec), 'Khách đưa thiếu tiền: chọn cách xử lý trước đã.')
    rec['change'] = notes(change)
    kit.need(due(rec) >= 0 or not rec['change'], 'Không có tiền thối cho khoản này.')
    need, given = due(rec), sum(rec['change'])
    if given < need and (rec['asked'] or careful(c, t, need - given, need)):
        rec['asked'] = min(9, rec['asked'] + 1)
        return dict(stop=True, message=ask_rest(t, need - given, who))
    return dict(stop=False, message='')


def settle(s: dict, c: dict, t: dict, rec: dict, react: dict | None = None, who: str = 'Khách') -> dict:
    """After the reaction, before kit.complete(): what happens to the change.
    Returns dict(loss, tip, message); take `loss` off the pay. Settles once."""
    if rec.get('outcome') is not None:
        return dict(loss=0, tip=0, message='')
    if (react or {}).get('kind') in ('refuse', 'walkout'):
        rec['outcome'] = 'void'   # they take their notes back: no change, no tip
        gap = sp_.settle(s, c, t, rec, True, who)
        return dict(loss=0, tip=0, message=gap['message'])
    gap = sp_.settle(s, c, t, rec, False, who)   # a short payment: what was never paid (0 when none)
    out = _settle(s, c, t, rec, react, who)
    if gap['loss']:
        rec['loss'] += gap['loss']
        out['loss'] += gap['loss']
    out['message'] = ' '.join(x for x in (out['message'], gap['message']) if x)
    return out


def _settle(s: dict, c: dict, t: dict, rec: dict, react: dict | None, who: str) -> dict:
    need, given = max(0, due(rec)), sum(rec['change'])
    if rec['asked']:
        asked_slip(t)
    if given < need:
        rec.update(outcome='missed', short=need - given)
        return dict(loss=0, tip=0, message=found_at_home(s, c, t, need - given))
    if given > need:
        back, msg = excess(c, t, given - need, who)
        rec.update(outcome='returned' if back else 'kept', over=given - need, loss=0 if back else given - need)
        return dict(loss=rec['loss'], tip=0, message=msg)
    tip, msg = keep_change(s, c, t, need, react, who)
    rec.update(outcome='keep' if tip else 'exact', tip=tip)
    return dict(loss=0, tip=tip, message=msg)


def short_action(s: dict, c: dict, t: dict, rec: dict | None, p: dict, who: str = 'Khách') -> dict:
    """The career's `<prefix>short` command {task, choice} (no clock tick; calling the police takes its own time)."""
    return sp_.act(s, c, t, rec, p.get('choice'), who)


def validate_book(c: dict) -> None:
    """Call from the career's validate_data: the workplace's short-payment book (optional)."""
    sp_.validate_book(c)


def public(rec: dict | None) -> dict | None:
    """What the browser sees: the price, the notes handed over and how it went."""
    if not isinstance(rec, dict):
        return None
    return dict(price=rec['price'], tender=list(rec['tender']), due=due(rec), change=list(rec['change']),
                asked=rec['asked'], outcome=rec['outcome'], short=rec['short'], over=rec['over'], tip=rec['tip'],
                counted=bool(rec.get('counted')), gap=sp_.public(rec))


# ---------------------------------------------------------------- saves
def validate(rec, t: dict | None = None) -> None:
    if rec is None:
        return
    kit.need(isinstance(rec, dict) and rec.get('v') == 1, 'Tiền mặt của đơn sai.', 'invalid_save')
    kit.integer(rec.get('price'), 1, 10 ** 6)
    tend = rec.get('tender')
    kit.need(isinstance(tend, list) and 1 <= len(tend) <= 20 and all(type(x) is int and x in DENOMS for x in tend)
             and (sum(tend) >= rec['price'] or isinstance(rec.get('sp'), dict)), 'Tiền khách đưa sai.', 'invalid_save')
    sp_.validate_rec(rec.get('sp'), rec['price'], sum(tend))
    kit.need(type(rec.get('counted', False)) is bool, 'Tiền mặt của đơn sai.', 'invalid_save')
    ch = rec.get('change')
    kit.need(isinstance(ch, list) and len(ch) <= MAX_TRAY and all(type(x) is int and x in DENOMS for x in ch),
             'Khay thối tiền sai.', 'invalid_save')
    kit.integer(rec.get('asked'), 0, 9)
    kit.need(rec.get('outcome') in OUTCOMES, 'Kết quả thối tiền sai.', 'invalid_save')
    for k in ('short', 'over', 'tip', 'loss'):
        kit.integer(rec.get(k), 0, 10 ** 5)
    if t is not None:
        validate_tip(t)


def validate_tip(t: dict) -> None:
    if 'tip_given' in t:
        kit.integer(t['tip_given'], 0, 10 ** 6)
