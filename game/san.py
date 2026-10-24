"""🎢 Sàn Phố: the new coins and the town's stocks (owner 24/10), bought and sold at the shared wild market
(game/market_wild.py). Mây Coin stays in game/invest.py and gold in game/vang.py (same ids, same saves).

State journey['san'] (optional; an older build keeps unknown journey keys untouched):
  v: 1
  h: {asset id: {u: units (thousandths), b: xu put in (fees included, a sale takes its share off), r: realised xu,
                 f: fees paid, n: trades, g: the listing generation bought, t: tick of the first buy (the regret
                 note's "since"), e: the split exponent `u` is counted in (optional, 0 when missing)}}
  log: [≤ LOG_MAX {t: tick, k: 'buy'|'sell'|'delist', a: asset id, x: xu moved, p: profit (sell / delist)}]
  st: {r: realised xu over all assets, f: fees, n: trades, lost: xu lost to delistings}
An asset id this build does not list is kept and validated loosely (a rollback never breaks a save); it is worth 0
here and cannot be traded.

Commands (journey.action): jr_san_buy {a, amount | all: true}, jr_san_sell {a, amount | all: true}.
Rules: an asset opens when the wallet has once held its `unlock` xu (stats.max_wallet, like Mây Coin's 500); a buy is
MIN_TRADE..AMOUNT_MAX xu from the wallet with the asset's fee (coins 2 %, stocks 1 %) taken first; a sale gets the
price minus the fee, at most SELL_MAX gross an order, and never past journey.WALLET_MAX. Wallet moves are Sổ ví rows
of kind 'invest', at most ROW_MAX each (journey.validate). A risky coin that is delisted (price 0, then a new listing
generation) leaves its holders nothing: sync() books the loss once. A split (1→10 above launch×10) or a merge
(10→1 under launch/10) changes the price and the units together, never the value: `u` is rescaled by 10^(e - e now).
"""
from __future__ import annotations

import re

from . import market_wild as mw

VERSION = 1
KEY = 'san'
COIN, CENT = 1000, 100
SCALE = COIN * CENT
MIN_TRADE = 10
AMOUNT_MAX = 10**7       # one buy order (as Mây Coin)
SELL_MAX = 10**8         # one sale's gross: at most ten Sổ ví rows
BASIS_MAX = 10**9        # xu put into one asset
UNITS_MAX = 10**15       # ≤ AMOUNT_MAX × SCALE / the lowest price (100) with room for many buys
ROW_MAX = 10**7          # journey.validate: one Sổ ví row's |amount|
LOG_MAX = 12
KIND = 'invest'
COMMANDS = ('jr_san_buy', 'jr_san_sell')
LOG_KINDS = ('buy', 'sell', 'delist')
H_KEYS = {'u', 'b', 'r', 'f', 'n', 'g', 't'}
ST_KEYS = ('r', 'f', 'n', 'lost')
ID_RE = re.compile(r'[a-z0-9_]{1,16}')
REGRET_PCT = 10          # the regret note shows when the peak was worth this much more than now


def _core():
    from . import engine
    return engine


def _jr():
    from . import journey
    return journey


def initial() -> dict:
    return dict(v=VERSION, h={}, log=[], st={k: 0 for k in ST_KEYS})


def get(s: dict) -> dict | None:
    j = s.get('journey') if isinstance(s, dict) else None
    g = j.get(KEY) if isinstance(j, dict) else None
    return g if isinstance(g, dict) else None


def _state(s: dict) -> dict:
    j = s['journey']
    if not isinstance(j.get(KEY), dict):
        j[KEY] = initial()
    return j[KEY]


def unlocked(s: dict, a: str) -> bool:
    return int(s['journey'].get('stats', {}).get('max_wallet', 0)) >= mw.ASSETS[a]['unlock']


def value_of(units: int, price: int) -> int:
    return units * price // SCALE


def fee_of(a: str, amount: int) -> int:
    return max(1, -(-amount * mw.ASSETS[a]['fee'] // 100))


def _now() -> int:
    return mw.tick_of()


def _units(a: str, h: dict, t: int) -> int:
    """The holding's units in the split terms of tick t (a merge rounds down, keeping at least one unit)."""
    d = h.get('e', 0) - mw.exp_at(a, t)
    if d > 0:
        return min(UNITS_MAX, h['u'] * 10**d)
    if d < 0:
        return max(1, h['u'] // 10**-d)
    return h['u']


def _rebase(a: str, h: dict, t: int) -> None:
    h['u'], h['e'] = _units(a, h, t), mw.exp_at(a, t)


def _dead(a: str, h: dict, t: int) -> bool:
    """Bought in a listing that has been delisted since (a risky coin): worth nothing."""
    if t < mw.WILD_TICK:
        return False
    return h['g'] != mw.gen_at(a, t) or mw.price_at(a, t) == 0


def _log(g: dict, t: int, k: str, a: str, x: int, p: int = 0) -> None:
    g['log'] = (g['log'] + [dict(t=int(t), k=k, a=a, x=int(x), p=int(p))])[-LOG_MAX:]   # not archived: a short memo


def _wallet(s: dict, amount: int, label: str) -> None:
    jr = _jr()
    left = amount
    while True:
        part = max(-ROW_MAX, min(ROW_MAX, left))
        jr._wallet(s['journey'], part, KIND, label)
        left -= part
        if not left:
            return


def _cap(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def sync(s: dict, notes: list | None = None) -> None:
    """Book the loss of every holding whose listing was delisted (once). Called after life days and before trades."""
    g = get(s)
    if not g or not g['h']:
        return
    t = _now()
    for a in sorted(g['h']):
        h = g['h'][a]
        if a not in mw.ASSETS:
            continue
        if not _dead(a, h, t):
            _rebase(a, h, t)
            continue
        lost = h['b']
        g['st']['lost'] = _cap(g['st']['lost'] + lost, 0, 10**12)
        g['st']['r'] = _cap(g['st']['r'] - lost, -10**12, 10**12)
        _log(g, t, 'delist', a, 0, -lost)
        del g['h'][a]
        if notes is not None:
            notes.append(f'🕳️ {mw.ASSETS[a]["name"]} đã bị hủy niêm yết: {lost:,} xu bạn bỏ vào mất trắng.'.replace(',', '.'))


def _amount(p: dict, most: int, cap: int, what: str) -> int:
    e = _core()
    e.need(set(p) <= {'a', 'amount', 'all'} and ('amount' in p) != ('all' in p), 'Chọn số xu hoặc “Tất cả” nhé.')
    if 'all' in p:
        e.need(p['all'] is True, 'Chọn số xu hoặc “Tất cả” nhé.')
        e.need(most >= MIN_TRADE, f'{what} cần ít nhất {MIN_TRADE} xu.')
        return min(most, cap)
    amount = p['amount']
    e.need(type(amount) is int and MIN_TRADE <= amount, f'{what} cần là số xu nguyên, ít nhất {MIN_TRADE} xu.')
    e.need(amount <= cap, f'Mỗi lệnh tối đa {cap:,} xu.'.replace(',', '.'))
    return amount


def action(s: dict, name: str, p: dict) -> dict:
    """jr_san_buy / jr_san_sell (journey.action). Checks everything before changing anything."""
    e = _core()
    need = e.need
    need(name in COMMANDS, 'Thao tác không hợp lệ.', 'unknown_action')
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    a = p.get('a')
    need(isinstance(a, str) and a in mw.NEW, 'Mã tài sản không hợp lệ.')
    sp = mw.ASSETS[a]
    j = s['journey']
    need(j.get('story'), 'Sàn Phố chỉ có trong chế độ hành trình.')
    need(unlocked(s, a), f'{sp["name"]} mở khi ví của bạn từng có {sp["unlock"]:,} xu.'.replace(',', '.'), 'locked')
    t = _now()
    need(mw.listed(t), 'Sàn Phố chưa mở cửa. Quay lại sau nhé!')
    sync(s)
    price = mw.price_at(a, t)
    gen = mw.gen_at(a, t)
    need(price > 0, f'{sp["name"]} đang bị hủy niêm yết, chưa giao dịch được.')
    g = _state(s)
    h = g['h'].get(a)
    result = dict(message='', effects=[])
    if name == 'jr_san_buy':
        wallet = j['wallet']
        amount = _amount(p, max(0, wallet), AMOUNT_MAX, 'Lệnh mua')
        need(amount <= wallet, 'Ví không đủ để mua số này.')
        fee = fee_of(a, amount)
        units = (amount - fee) * SCALE // price
        need(units >= 1, 'Số tiền quá nhỏ để mua được.')
        have_u, have_b = (h['u'], h['b']) if h else (0, 0)
        need(have_b + amount <= BASIS_MAX, f'Mỗi mã chỉ bỏ vào tối đa {BASIS_MAX:,} xu.'.replace(',', '.'))
        need(have_u + units <= UNITS_MAX, 'Bạn đã giữ quá nhiều đơn vị mã này.')
        _wallet(s, -amount, f'Mua {sp["name"]}')
        if not h:
            h = g['h'][a] = dict(u=0, b=0, r=0, f=0, n=0, g=gen, t=t, e=mw.exp_at(a, t))
        h['u'] += units
        h['b'] += amount
        h['f'] = _cap(h['f'] + fee, 0, 10**12)
        h['n'] = _cap(h['n'] + 1, 0, 10**7)
        g['st']['f'] = _cap(g['st']['f'] + fee, 0, 10**12)
        g['st']['n'] = _cap(g['st']['n'] + 1, 0, 10**7)
        _log(g, t, 'buy', a, -amount)
        result['message'] = f'Đã mua {sp["name"]} bằng {amount:,} xu (phí {fee:,} xu).'.replace(',', '.')
        if sp['risky']:
            result['effects'].append('⚠️ Coin rủi ro rất cao: có thể bị hủy niêm yết và về 0.')
    else:
        need(h is not None and h['u'] > 0, f'Bạn chưa có {sp["name"]} để bán.')
        value = value_of(h['u'], price)
        if p.get('all') is True and set(p) == {'a', 'all'} and value <= SELL_MAX:
            units = h['u']
        else:
            amount = _amount(p, value, SELL_MAX, 'Lệnh bán')
            need(amount <= value, f'Bạn chỉ giữ khoảng {value:,} xu {sp["name"]}.'.replace(',', '.'))
            units = min(h['u'], -(-amount * SCALE // price))
        gross = value_of(units, price)
        fee = fee_of(a, gross)
        need(gross > fee, 'Số này bán ra không đủ trả phí.')
        proceeds = gross - fee
        need(j['wallet'] + proceeds <= _jr().WALLET_MAX,
             f'Ví chỉ giữ thêm được {max(0, _jr().WALLET_MAX - j["wallet"]):,} xu.'.replace(',', '.'))
        part = h['b'] if units == h['u'] else h['b'] * units // h['u']
        pnl = proceeds - part
        h['u'] -= units
        h['b'] -= part
        h['r'] = _cap(h['r'] + pnl, -10**12, 10**12)
        h['f'] = _cap(h['f'] + fee, 0, 10**12)
        h['n'] = _cap(h['n'] + 1, 0, 10**7)
        g['st']['r'] = _cap(g['st']['r'] + pnl, -10**12, 10**12)
        g['st']['f'] = _cap(g['st']['f'] + fee, 0, 10**12)
        g['st']['n'] = _cap(g['st']['n'] + 1, 0, 10**7)
        if not h['u']:
            del g['h'][a]
        _wallet(s, proceeds, f'Bán {sp["name"]}')
        _log(g, t, 'sell', a, proceeds, pnl)
        result['message'] = (f'Đã bán, nhận {proceeds:,} xu (phí {fee:,} xu). ' +
                             (f'Lãi {pnl:,} xu.' if pnl >= 0 else f'Lỗ {-pnl:,} xu.')).replace(',', '.')
    return result


# ---------------------------------------------------------------- reads
def value(s: dict) -> int:
    """Live market value of every holding (0 for a dead listing or an id this build does not know)."""
    g = get(s)
    if not g or not g.get('h'):
        return 0
    t = _now()
    total = 0
    for a, h in g['h'].items():
        if a in mw.ASSETS and isinstance(h, dict) and not _dead(a, h, t):
            total += value_of(_units(a, h, t), mw.price_at(a, t))
    return total


def net_value(j: dict) -> int:
    """What every holding sells for now, the fee taken off (game/fair_hai.py device fines)."""
    g = j.get(KEY) if isinstance(j, dict) else None
    if not isinstance(g, dict) or not g.get('h'):
        return 0
    t = _now()
    total = 0
    for a, h in g['h'].items():
        if a in mw.ASSETS and not _dead(a, h, t):
            gross = value_of(_units(a, h, t), mw.price_at(a, t))
            total += gross - fee_of(a, gross) if gross > 1 else 0
    return total


def basis(j: dict) -> int:
    """Σ xu put into the live holdings (game/wealth.py counts them at cost, like Mây Coin)."""
    g = j.get(KEY) if isinstance(j, dict) else None
    if not isinstance(g, dict) or not isinstance(g.get('h'), dict):
        return 0
    return sum(max(0, h.get('b', 0)) for h in g['h'].values() if isinstance(h, dict) and type(h.get('b')) is int)


def force_sell(j: dict, left: int, label: str) -> int:
    """Sell holdings (biggest value first) until `left` xu are covered; the change goes to the wallet. Returns the
    xu taken (≤ left). game/fair_hai.py: a device fine the wallet, bank and savings could not pay."""
    from . import fair_hai
    g = j.get(KEY) if isinstance(j, dict) else None
    if not isinstance(g, dict) or not g.get('h') or left <= 0:
        return 0
    t = _now()
    taken = 0
    order = sorted((a for a in g['h'] if a in mw.ASSETS and not _dead(a, g['h'][a], t)),
                   key=lambda a: -value_of(_units(a, g['h'][a], t), mw.price_at(a, t)))
    for a in order:
        if left <= 0:
            break
        h, price = g['h'][a], mw.price_at(a, t)
        _rebase(a, h, t)
        sp = mw.ASSETS[a]
        want = -(-left * 100 // (100 - sp['fee'])) + 2
        units = min(h['u'], -(-want * SCALE // price))
        gross = value_of(units, price)
        fee = fee_of(a, gross)
        if gross <= fee:
            continue
        got = gross - fee
        part = h['b'] if units == h['u'] else h['b'] * units // h['u']
        h['u'] -= units
        h['b'] -= part
        h['r'] = _cap(h['r'] + got - part, -10**12, 10**12)
        h['f'] = _cap(h['f'] + fee, 0, 10**12)
        h['n'] = _cap(h['n'] + 1, 0, 10**7)
        g['st']['r'] = _cap(g['st']['r'] + got - part, -10**12, 10**12)
        g['st']['f'] = _cap(g['st']['f'] + fee, 0, 10**12)
        if not h['u']:
            del g['h'][a]
        _log(g, t, 'sell', a, got, got - part)
        x = min(left, got)
        fair_hai._credit(j, got - x, f'Tiền thừa sau khi bán {sp["name"]} nộp phạt')
        left -= x
        taken += x
    return taken


def public(s: dict) -> dict | None:
    """api.state.san: rules, the static catalogue, what is open, each holding with its value now, the peak since it
    was bought (the regret note) and the log. Prices for the screen come from /api/market (market_data `board`)."""
    j = s.get('journey') if isinstance(s, dict) else None
    if not isinstance(j, dict) or not j.get('story'):
        return None
    g = get(s) or initial()
    t = _now()
    mx = int(j.get('stats', {}).get('max_wallet', 0))
    hold = {}
    for a, h in g['h'].items():
        if a not in mw.ASSETS:
            continue
        dead = _dead(a, h, t)
        price = 0 if dead else mw.price_at(a, t)
        units = h['u'] if dead else _units(a, h, t)
        val = value_of(units, price)
        peak = 0 if dead else mw.peak_since(a, h['t'], t)     # in the split terms of t, like units
        peak_val = value_of(units, peak)
        peak_net = peak_val - fee_of(a, peak_val) if peak_val > 1 else 0
        hold[a] = dict(units=units, e=mw.exp_at(a, t), basis=h['b'], realised=h['r'], fees=h['f'], trades=h['n'],
                       value=val, dead=dead, peak=peak, peak_net=peak_net,
                       regret=bool(peak_net > h['b'] and peak_val * 100 >= val * (100 + REGRET_PCT)))
    return dict(open=mw.listed(t), opens_at=mw.rm.EPOCH + mw.WILD_TICK * mw.TICK, tick=t,
                rules=dict(coin=COIN, cent=CENT, min_trade=MIN_TRADE, amount_max=AMOUNT_MAX, sell_max=SELL_MAX),
                assets=[dict(x, open=mx >= x['unlock']) for x in mw.catalogue() if not x['legacy']],
                hold=hold, log=list(reversed([dict(r) for r in g['log']])), stats=dict(g['st']),
                max_wallet=mx)


def validate(s: dict) -> None:
    e = _core()
    need, integer = e.need, e.integer
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    g = j[KEY]
    bad = 'Dữ liệu Sàn Phố không hợp lệ.'
    need(isinstance(g, dict) and {'v', 'h', 'log', 'st'} <= set(g), bad, 'invalid_save')
    need(g['v'] == VERSION, bad, 'invalid_save')
    need(isinstance(g['h'], dict) and len(g['h']) <= 64, bad, 'invalid_save')
    for a, h in g['h'].items():
        need(isinstance(a, str) and ID_RE.fullmatch(a) is not None, bad, 'invalid_save')
        need(isinstance(h, dict) and H_KEYS <= set(h), bad, 'invalid_save')
        integer(h['u'], 1, UNITS_MAX)
        integer(h['b'], 0, BASIS_MAX)
        integer(h['r'], -10**12, 10**12)
        integer(h['f'], 0, 10**12)
        integer(h['n'], 0, 10**7)
        integer(h['g'], 1, 10**4)
        integer(h['t'], 0, 10**9)
        if 'e' in h:
            integer(h['e'], -mw.E_MAX, mw.E_MAX)
    need(isinstance(g['log'], list) and len(g['log']) <= LOG_MAX, bad, 'invalid_save')
    for r in g['log']:
        need(isinstance(r, dict) and {'t', 'k', 'a', 'x', 'p'} <= set(r) and r['k'] in LOG_KINDS
             and isinstance(r['a'], str) and len(r['a']) <= 16, bad, 'invalid_save')
        integer(r['t'], 0, 10**9)
        integer(r['x'], -10**9, 10**9)
        integer(r['p'], -10**12, 10**12)
    need(isinstance(g['st'], dict) and set(ST_KEYS) <= set(g['st']), bad, 'invalid_save')
    integer(g['st']['r'], -10**12, 10**12)
    integer(g['st']['f'], 0, 10**12)
    integer(g['st']['n'], 0, 10**7)
    integer(g['st']['lost'], 0, 10**12)
