"""💰 Tiệm vàng Kim Phát: buy and sell gold by the chỉ (story mode).

Owner 03/10 (docs/ECONOMY_RISKS.md): somewhere to put the xu, "đầu tư", with visible gains and a real risk. Gold is
the street's calm investment next to the bank's savings (sure, small) and Mây Coin (wild):

* One price for everyone, by the Vietnam date (like the 🔥 x3 week): a walk that drifts up slowly (DRIFT a day, about
  3 % a month), pulled back towards that trend (KAPPA), with a daily wobble (SIGMA) and now and then news that moves it
  2–5 % (SHOCK_P). From BASE xu a chỉ on EPOCH. MNL_GOLD_SALT (the server's environment) keeps the walk unknown in
  advance; every server of one deployment must share it.
* The shop buys and sells around that price: you pay SPREAD_BP more, it pays SPREAD_BP less (a round trip costs
  about 5 %, so gold pays only when held a while: weeks, not hours). Bought and sold by the phân (a tenth of a chỉ),
  so a small wallet can try too.
* Paid like a vehicle (game/garage.py): the cash in the wallet first, then the bank account; never a loan, never
  below 0 (a wallet in debt buys nothing). The sale goes to the wallet. Wallet rows of kind 'invest' (older builds
  accept them), bank lines 'acc'.
* What you paid (`cost`) is kept so the page can say "lãi" or "lỗ"; selling part takes the same share of it.

State journey['vang'] (optional; older builds allow extra journey keys and keep it untouched; unknown fields a
newer build adds are kept): v, phan (tenths of a chỉ held), cost (xu paid for them), stats {bought, sold, fees}
(phân bought and sold, xu of spread paid), log [≤ LOG_MAX {d: 'YYYY-MM-DD', k: 'buy'|'sell', n: phân, x: xu}].
Commands (journey.action): jr_vang_buy {phan}, jr_vang_sell {phan | all: true}.
"""
from __future__ import annotations

import datetime
import functools
import hashlib
import math
import os
import random
import time

from . import archive as ar
from . import bank as bk

VERSION = 1
KEY = 'vang'
VN = datetime.timezone(datetime.timedelta(hours=7))
EPOCH = datetime.date(2026, 9, 1)  # the walk starts here (a month of history on the first day)
BASE = 500                         # xu a chỉ on EPOCH
DRIFT = 0.001                      # the trend, log a day (about +3 % a month)
KAPPA = 0.06                       # pull back towards the trend, a day
SIGMA = 0.013                      # the daily wobble
SHOCK_P, SHOCK = 0.04, (0.02, 0.05)
SPREAD_BP = 250                    # the shop sells 2,5 % above the price and buys 2,5 % below
PHAN = 10                          # phân a chỉ
MAX_PHAN = 100_000                 # 10 000 chỉ held at most
HIST = 30                          # days on the chart
LOG_MAX = 10
KIND = 'invest'
STATS = ('bought', 'sold', 'fees')
COMMANDS = ('jr_vang_buy', 'jr_vang_sell')
NEWS = (('Tin vàng thế giới tăng mạnh', 1), ('Người dân đổ xô mua vàng cưới', 1), ('Ngân hàng hạ lãi suất', 1),
        ('Vàng thế giới quay đầu giảm', -1), ('Nhiều người chốt lời bán ra', -1), ('Đồng tiền mạnh lên', -1))


def now() -> float:
    return time.time()


def today() -> datetime.date:
    return datetime.datetime.fromtimestamp(now(), VN).date()


def _salt() -> str:
    return os.environ.get('MNL_GOLD_SALT', 'kim-phat')


@functools.lru_cache(maxsize=4)
def _walk(salt: str, upto: datetime.date) -> tuple[tuple[int, int], ...]:
    """((price a chỉ, news index or -1) for every day from EPOCH to `upto`)."""
    out = []
    x = math.log(BASE)
    for t in range((upto - EPOCH).days + 1):
        if t:
            d = EPOCH + datetime.timedelta(days=t)
            h = hashlib.sha256(f'vang|{salt}|{d.isoformat()}'.encode()).digest()
            rng = random.Random(int.from_bytes(h[:8], 'big'))
            trend = math.log(BASE) + DRIFT * t
            x += KAPPA * (trend - x) + DRIFT + rng.gauss(0, SIGMA)
            news = -1
            if rng.random() < SHOCK_P:
                news = rng.randrange(len(NEWS))
                x += NEWS[news][1] * rng.uniform(*SHOCK)
            out.append((max(50, round(math.exp(x))), news))
        else:
            out.append((BASE, -1))
    return tuple(out)


def price(d: datetime.date | None = None) -> int:
    """The price of one chỉ on day `d` (today by default), xu."""
    d = d or today()
    if d <= EPOCH:
        return BASE
    return _walk(_salt(), d)[-1][0]


def history(d: datetime.date | None = None, n: int = HIST) -> list[int]:
    d = d or today()
    if d <= EPOCH:
        return [BASE]
    return [p for p, _ in _walk(_salt(), d)[-n:]]


def news(d: datetime.date | None = None) -> str:
    """Today's headline when the price jumped ('' most days)."""
    d = d or today()
    if d <= EPOCH:
        return ''
    k = _walk(_salt(), d)[-1][1]
    return NEWS[k][0] if k >= 0 else ''


def buy_price(p: int) -> int:
    return -(-p * (10000 + SPREAD_BP) // 10000)


def sell_price(p: int) -> int:
    return p * (10000 - SPREAD_BP) // 10000


def cost_of(phan: int, p: int | None = None) -> int:
    """What `phan` phân cost to buy today."""
    return -(-int(phan) * buy_price(price() if p is None else p) // PHAN)


def worth(phan: int, p: int | None = None) -> int:
    """What `phan` phân sell for today."""
    return int(phan) * sell_price(price() if p is None else p) // PHAN


def _fmt(n: int) -> str:
    return bk._fmt(n)


def amount_text(phan: int) -> str:
    """12 -> '1,2 chỉ', 10 -> '1 chỉ', 3 -> '3 phân'."""
    phan = int(phan)
    if phan < PHAN:
        return f'{phan} phân'
    whole, part = divmod(phan, PHAN)
    return f'{_fmt(whole)},{part} chỉ' if part else f'{_fmt(whole)} chỉ'


# ---------------------------------------------------------------- the block
def initial() -> dict:
    return dict(v=VERSION, phan=0, cost=0, stats={k: 0 for k in STATS}, log=[])


def get(s: dict) -> dict | None:
    j = s.get('journey')
    g = j.get(KEY) if isinstance(j, dict) else None
    return g if isinstance(g, dict) else None


def value(s: dict) -> int:
    """What the gold held sells for today (0: none)."""
    g = get(s)
    return worth(g['phan']) if g and g.get('phan') else 0


def _jr():
    from . import journey
    return journey


def _core():
    from . import engine
    return engine


def _have(s: dict) -> int:
    b = bk.get(s)
    return max(0, s['journey']['wallet']) + (b['balance'] if b else 0)


def _take(s: dict, amount: int, label: str) -> None:
    """Cash first, then the bank account (the caller checked both cover it)."""
    j = s['journey']
    cash = min(max(0, j['wallet']), amount)
    if cash:
        _jr()._wallet(j, -cash, KIND, label)
    rest = amount - cash
    if rest:
        b = bk.get(s)
        b['balance'] -= rest
        bk._log(b, j['life_day'], 'acc', label, -rest)


def _log(g: dict, k: str, n: int, x: int) -> None:
    g['log'] = ar.last(g['log'] + [dict(d=today().isoformat(), k=k, n=int(n), x=int(x))], LOG_MAX, 'vang.log', ar.JOURNEY)


def action(s: dict, name: str, p: dict) -> dict:
    e = _core()
    need = e.need
    j = s['journey']
    need(j.get('story'), 'Tiệm vàng chỉ có trong chế độ hành trình.')
    need(isinstance(p, dict), 'Dữ liệu không hợp lệ.')
    pr = price()
    if name == 'jr_vang_buy':
        need(set(p) <= {'phan'} and type(p.get('phan')) is int and 1 <= p['phan'] <= MAX_PHAN, 'Chọn số vàng muốn mua nhé.')
        n = p['phan']
        g = get(s) or initial()
        need(g['phan'] + n <= MAX_PHAN, f'Tiệm chỉ giữ hộ tối đa {_fmt(MAX_PHAN // PHAN)} chỉ.')
        need(j['wallet'] >= 0, 'Ví đang nợ. Trả nợ xong rồi hãy mua vàng nhé.', 'in_debt')
        cost = cost_of(n, pr)
        short = cost - _have(s)
        need(short <= 0, f'Còn thiếu {_fmt(short)} xu.', 'not_enough')
        _take(s, cost, f'Mua vàng · {amount_text(n)}')
        if get(s) is None:
            j[KEY] = g
        g['phan'] += n
        g['cost'] += cost
        g['stats']['bought'] = g['stats'].get('bought', 0) + n
        g['stats']['fees'] = g['stats'].get('fees', 0) + max(0, cost - n * pr // PHAN)
        _log(g, 'buy', n, -cost)
        return dict(message=f'💰 Đã mua {amount_text(n)} vàng, trả {_fmt(cost)} xu.')
    if name == 'jr_vang_sell':
        g = get(s)
        need(g is not None and g['phan'] > 0, 'Bạn chưa có vàng để bán.')
        if p.get('all') is True and set(p) == {'all'}:
            n = g['phan']
        else:
            need(set(p) <= {'phan'} and type(p.get('phan')) is int and 1 <= p['phan'], 'Chọn số vàng muốn bán nhé.')
            n = p['phan']
            need(n <= g['phan'], f'Bạn chỉ có {amount_text(g["phan"])}.')
        got = worth(n, pr)
        part = g['cost'] if n == g['phan'] else g['cost'] * n // g['phan']
        g['phan'] -= n
        g['cost'] -= part
        g['stats']['sold'] = g['stats'].get('sold', 0) + n
        g['stats']['fees'] = g['stats'].get('fees', 0) + max(0, n * pr // PHAN - got)
        if got:
            _jr()._wallet(j, got, KIND, f'Bán vàng · {amount_text(n)}')
        _log(g, 'sell', n, got)
        pnl = got - part
        tail = f' Lãi {_fmt(pnl)} xu.' if pnl > 0 else f' Lỗ {_fmt(-pnl)} xu.' if pnl < 0 else ''
        return dict(message=f'💰 Đã bán {amount_text(n)} vàng, nhận {_fmt(got)} xu vào ví.{tail}')
    raise e.GameError('Thao tác tiệm vàng không hợp lệ.', 'unknown_action')


def public(s: dict) -> dict | None:
    """state.vang (not in the journey, whose size has a budget): today's prices, the chart, what you hold."""
    j = s['journey']
    if not j.get('story'):
        return None
    d = today()
    hist = history(d)
    pr = hist[-1]
    g = get(s) or initial()
    out = dict(date=d.isoformat(), p=pr, buy=buy_price(pr), sell=sell_price(pr), y=hist[-2] if len(hist) > 1 else pr,
               hist=hist, phan=g['phan'], cost=g['cost'], value=worth(g['phan'], pr))
    headline = news(d)
    if headline:
        out['news'] = headline
    return out


def validate(s: dict) -> None:
    """journey['vang'] when present (fields a newer build adds are left alone)."""
    e = _core()
    j = s.get('journey')
    if not isinstance(j, dict) or KEY not in j:
        return
    g = j[KEY]
    bad = 'Vàng trong bản lưu không hợp lệ.'
    e.need(isinstance(g, dict) and set(initial()) <= set(g) and g['v'] == VERSION, bad, 'invalid_save')
    e.need(type(g['phan']) is int and 0 <= g['phan'] <= MAX_PHAN and type(g['cost']) is int and 0 <= g['cost'] <= 10**10
           and (g['phan'] > 0 or g['cost'] == 0), bad, 'invalid_save')
    e.need(isinstance(g['stats'], dict) and all(type(v) is int and 0 <= v <= 10**12 for v in g['stats'].values()), bad, 'invalid_save')
    e.need(isinstance(g['log'], list) and len(g['log']) <= LOG_MAX
           and all(isinstance(x, dict) and x.get('k') in ('buy', 'sell') and isinstance(x.get('d'), str) and len(x['d']) == 10
                   and type(x.get('n')) is int and type(x.get('x')) is int for x in g['log']), bad, 'invalid_save')
