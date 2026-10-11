"""👴 Ông Hai's table and the police (owner 09/10: "ông Hai tăng lên để k cho người dùng thắng nữa, hạn chế cho người ta
thắng đi nhé. nếu thắng nhiều thì cho công an bắt thu tiền là được"). Ông Hai himself is game/fair_oaq.py; the
commands are in game/fair.py. Nothing here reaches the client before it happens (no count, no threshold shown).

* Games: no limit (owner 11/10; HAI_DAY is only the legacy day counter's name).
* Wins keep their prize. The DEVICE_WINS + 1-th win (count_win, journey[WINS_KEY]) brings the police: "thiết bị hỗ
  trợ", DEVICE_PCT % of the player's money (device_base: the wallet, the bank, and since 11/10 the Mây savings book,
  Mây Coin and gold at what they sell for now, so parking the winnings there no longer halves the fine; device_fine)
  and the jail, while police enforcement is on. Legacy streak/window records remain readable; legacy collection
  (seize) uses the same small ceiling, wallet only, and does not stack another arrest fine.

Save: journey['fair_hai'] {d: the Vietnam date of `n`, n: games started with him that day, s: wins in a row,
w: [[epoch s, xu], ...] his wins not taken yet, within WINDOW} (optional: an older server keeps the journey's unknown
blocks as they are and never reads it; absent = nothing counted yet).
"""
from __future__ import annotations
from .loss_limits import bounded_loss

KEY = 'fair_hai'
HAI_DAY = 30             # legacy: games a day were capped here until 11/10 (owner: "không giới hạn số ván"); a counter only
# Owner 11/10 (later): "ô ăn quan nếu thắng trên 50 ván thì bị bắt vì sử dụng thiết bị hỗ trợ, và phạt 50% ví (tổng
# tiền, có trừ cả ví ngân hàng)". Wins against him are counted in journey[WINS_KEY] {n} (optional: an older server keeps
# the journey's unknown blocks); the DEVICE_WINS + 1-th brings the police, then the count starts again.
WINS_KEY = 'fair_hai_w'
DEVICE_WINS = 50
DEVICE_PCT = 50
STREAK = 2               # wins in a row that bring the police
WINDOW, WINDOW_WINS = 86400, 3   # ... or this many wins within a day (24 h)
W_MAX = 10               # the save's bound on w (a raid clears it at WINDOW_WINS)
TIRED = 'Hôm nay Ông Hai đánh nhiều ván quá, ông mệt rồi. Mai cháu ghé nha!'
SEIZE_LABEL = '🚨 Công an kiểm tra bàn Ông Hai · Nộp phạt'
# Owner 10/10: "nếu chơi thắng ông Hai thì bị bắt và phạt vì tội sử dụng thiết bị thứ 3, bỏ tù luôn và phạt 30 - 50% tiền;
# còn ai thắng vẫn thắng bình thường". The nominal percentage is now bounded by loss_limits;
# the prize and the existing trại tạm giữ (fair_bm.JAIL_DAYS) remain.
FINE_LO, FINE_HI = 30, 50
FINE_LABEL = '🚨 Công an phạt: dùng thiết bị hỗ trợ khi chơi với Ông Hai'
SAY_DEVICE = 'Thắng Ông Hai nhiều cỡ này thì chỉ có máy giúp thôi! Dùng thiết bị hỗ trợ là gian lận, nộp phạt rồi về đồn!'
SAY = 'Thắng Ông Hai liền mấy ván rồi nha. Nộp phạt nhẹ rồi về đồn làm việc!'


def _of(j: dict) -> dict:
    h = j.get(KEY)
    if not isinstance(h, dict):
        h = j[KEY] = dict(d='', n=0, s=0, w=[])
    return h


def can_start(j: dict, today: str) -> bool:
    """A new game with Ông Hai: always (owner 11/10, no limit on games)."""
    return True


def count_win(j: dict) -> bool:
    """A won game against him: True when it is past DEVICE_WINS (the police come; the count starts again)."""
    w = j.get(WINS_KEY)
    n = (w['n'] if isinstance(w, dict) and type(w.get('n')) is int else 0) + 1
    caught = n > DEVICE_WINS
    j[WINS_KEY] = dict(n=0 if caught else n)
    return caught


def started(j: dict, today: str) -> None:
    h = _of(j)
    if h['d'] != today:
        h['d'], h['n'] = today, 0
    h['n'] = min(10**6, h['n'] + 1)


def lost(j: dict) -> None:
    """A game with him lost, drawn or given up: the run of wins is broken (the day's wins stay counted)."""
    h = j.get(KEY)
    if isinstance(h, dict):
        h['s'] = 0


def won(j: dict, t: float, xu: int) -> int:
    """A won game paying `xu`: the xu the police take back now (0: none). A raid clears the run."""
    h = _of(j)
    now = int(t)
    h['w'] = [w for w in h['w'] if 0 <= now - w[0] < WINDOW][-(W_MAX - 1):] + [[now, max(0, int(xu))]]
    h['s'] = min(10**6, h['s'] + 1)
    if h['s'] < STREAK and len(h['w']) < WINDOW_WINS:
        return 0
    due = sum(x for _, x in h['w'])
    h['s'], h['w'] = 0, []
    return due


def _coin_net(j: dict) -> int:
    """What the Mây Coin held sells for now, the sale fee taken off (0: none)."""
    from . import invest as iv
    if not isinstance(j.get('invest'), dict):
        return 0
    gross = iv.value(dict(journey=j))
    return gross - iv._fee(gross) if gross > 1 else 0


def device_base(j: dict) -> int:
    """What a "thiết bị hỗ trợ" fine counts (owner 11/10 "50% tổng tiền"): the wallet and the bank (fair_bm.total_money)
    plus the Mây savings book, the Mây Coin and the gold at what they would sell for now (11/10 audit: winnings parked
    there escaped half the fine). Homes, vehicles and the workplaces' funds are not money (and not taken)."""
    from . import fair_bm as bm
    from . import vang
    total = bm.total_money(j)
    inv = j.get('invest')
    if isinstance(inv, dict):
        total += max(0, inv['saving']['balance']) + _coin_net(j)
    return total + vang.value(dict(journey=j))


def _credit(j: dict, amount: int, label: str) -> None:
    """The change of a forced sale back into the wallet, Sổ ví rows of at most fair_bm.ROW_MAX."""
    from . import fair_bm as bm
    from . import journey as jr
    while amount > 0:
        part = min(amount, bm.ROW_MAX)
        jr._wallet(j, part, 'invest', label)
        amount -= part


def _take_parked(j: dict, f: dict, amount: int, label: str) -> int:
    """What the wallet and the bank could not pay of a device fine: from the Mây savings book (this period's interest
    forfeited, as on a withdrawal), then gold and Mây Coin sold at today's price (the shop's spread, the 2 % fee; the
    change back to the wallet). Each block's own log says so. A fair loss (net, stats.lost). Returns what was taken."""
    from . import invest as iv
    from . import vang
    s = dict(journey=j)
    day = j['life_day']
    left = int(amount)
    inv = j.get('invest') if isinstance(j.get('invest'), dict) else None
    if left > 0 and inv is not None and inv['saving']['balance'] > 0:
        sv = inv['saving']
        x = min(left, sv['balance'])
        lost = sv['pending'] // 1000
        sv['forfeited'] = min(10**9, sv['forfeited'] + lost)
        sv['pending'] = 0
        sv['balance'] -= x
        if not sv['balance']:
            sv['term_day'] = day
        iv._log(inv, day, 'withdraw', f'{label}: trừ {x} xu tiết kiệm' + (f', mất {lost} xu lãi kỳ này.' if lost else '.'))
        left -= x
    g = vang.get(s)
    if left > 0 and g is not None and g.get('phan', 0) > 0:
        pr = vang.price()
        n = min(g['phan'], -(-left * vang.PHAN // max(1, vang.sell_price(pr))))   # the phân whose sale covers it
        got = vang.worth(n, pr)
        part = g['cost'] if n == g['phan'] else g['cost'] * n // g['phan']
        g['phan'] -= n
        g['cost'] -= part
        g['stats']['sold'] = min(10**12, g['stats'].get('sold', 0) + n)
        g['stats']['fees'] = min(10**12, g['stats'].get('fees', 0) + max(0, n * pr // vang.PHAN - got))
        vang._log(g, 'sell', n, got)
        x = min(left, got)
        _credit(j, got - x, f'Tiền thừa sau khi bán vàng nộp phạt · {vang.amount_text(n)}')
        left -= x
    if left > 0 and inv is not None and iv._live_units(j, inv) > 0:
        iv.sync_market(s)   # the one-time conversion of a legacy holding, today's price (as a sale does)
        coin, price = inv['coin'], inv['price']
        want = -(-left * 100 // (100 - iv.FEE_PCT)) + 2   # a gross whose proceeds cover `left`
        units = min(coin['units'], -(-want * iv.COIN * iv.CENT // price))
        gross = iv._value(units, price)
        fee = iv._fee(gross)
        if gross > fee:
            got = gross - fee
            part = coin['basis'] if units == coin['units'] else coin['basis'] * units // coin['units']
            coin['realised'] = max(-10**9, min(10**9, coin['realised'] + got - part))
            coin['units'] -= units
            coin['basis'] -= part
            coin['fees'] = min(10**9, coin['fees'] + fee)
            coin['trades'] = min(10**7, coin['trades'] + 1)
            iv._log(inv, day, 'sell', f'{label}: bán {iv._coins_text(units)} MÂY, nhận {got} xu nộp phạt.')
            x = min(left, got)
            _credit(j, got - x, 'Tiền thừa sau khi bán Mây Coin nộp phạt')
            left -= x
    parked = int(amount) - left
    if parked:
        f['net'] = max(-10**9, f['net'] - parked)
        f['stats']['lost'] = min(10**9, f['stats']['lost'] + parked)
    return parked


def device_fine(s: dict | None, j: dict, f: dict, pct: int = DEVICE_PCT, label: str = FINE_LABEL) -> int:
    """The prize stays; pct % of device_base, taken from the wallet and the bank (fair_bm.take_total), then from the
    Mây savings, the gold and the Mây Coin (_take_parked); no ceiling, never below zero. Returns what was taken."""
    from . import fair_bm as bm
    due = device_base(j) * pct // 100
    taken = bm.take_total(j, f, due, label)
    if taken < due:
        taken += _take_parked(j, f, due - taken, label)
    return taken


def seize(s: dict, j: dict, f: dict, due: int, label: str = SEIZE_LABEL) -> int:
    """Legacy collection: one bounded wallet-only loss, recorded at its actual amount."""
    from . import fair_bm as bm
    return bm._take(j, f, bounded_loss(j['wallet'], due, fine=True), label)


def validate(j: dict) -> None:
    if WINS_KEY in j:
        from .engine import need, integer
        w = j[WINS_KEY]
        need(isinstance(w, dict) and set(w) == {'n'}, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        integer(w['n'], 0, DEVICE_WINS)
    if KEY not in j:
        return
    from .engine import need, integer
    bad = 'Dữ liệu chợ đen không hợp lệ.'
    h = j[KEY]
    need(isinstance(h, dict) and set(h) == {'d', 'n', 's', 'w'} and isinstance(h['d'], str) and len(h['d']) <= 10
         and isinstance(h['w'], list) and len(h['w']) <= W_MAX, bad, 'invalid_save')
    integer(h['n'], 0, 10**6)
    integer(h['s'], 0, 10**6)
    for w in h['w']:
        need(isinstance(w, list) and len(w) == 2, bad, 'invalid_save')
        integer(w[0], 0, 10**11)
        integer(w[1], 0, 10**7)
