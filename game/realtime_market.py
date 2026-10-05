"""Shared fictional prices, keyed only by server salt, asset and wall-clock tick.

One real hour is one market day; quotes change every ten minutes. The causal
48-day finite response below gives persistent bull/bear hours with mean reversion
without replaying an ever-growing random walk. Its kernel ramps in during the
news hour, decays with an eight-hour time constant, then fades to zero in the
last hour. There is no block reset or future price in a public quote.

News contributes a signed .7–1.3 hourly signal; independent hidden liquidity
adds uniform -1.8–1.8, so a headline supports but cannot guarantee its direction.
Coin/gold log amplitudes: hourly regime .070/.018, tick noise .008/.002,
3%-probability tick shock .025/.008 decaying to zero over six ticks. The slow
reference grows linearly by .060%/.035% per market day, capped at 4x the anchor.
These are fictional gameplay parameters, not real financial market data.

Rollout: set MNL_MARKET_EPOCH once to the actual cutover Unix second on all
workers before enabling realtime holdings. Keep it and the market/gold salts
unchanged afterwards: changing them rewrites prices. The local default is
2026-10-05 00:00 Vietnam time; it is not an instruction to deploy retroactively.
Public listeners must call validate_runtime before opening their store. A public
deployment requires an explicit, already-reached epoch and a persistent random
secret of at least 24 characters shared by all workers. Local offline tests may
keep the deterministic defaults.
"""
from __future__ import annotations

import datetime as dt
import functools
import hashlib
import math
import os
import time

_VN = dt.timezone(dt.timedelta(hours=7))
_DEFAULT_EPOCH = int(dt.datetime(2026, 10, 5, tzinfo=_VN).timestamp())
try:
    EPOCH = int(os.environ.get('MNL_MARKET_EPOCH', str(_DEFAULT_EPOCH)))
    if EPOCH <= 0:
        raise ValueError('epoch must be positive')
    _ANCHOR_DATE = dt.datetime.fromtimestamp(EPOCH, _VN).date()
except (ValueError, OverflowError, OSError) as exc:
    raise ValueError('MNL_MARKET_EPOCH must be a valid positive integer Unix timestamp') from exc
TICK_SECONDS = 600
DAY_SECONDS = 3600
HISTORY = 30
_TICKS_PER_DAY = DAY_SECONDS // TICK_SECONDS
_REGIME_DAYS = 48
_DECAY_DAYS = 8.0
_PARAMETERS = {'coin': (.070, .008, .025, .00060),
               'gold': (.018, .002, .008, .00035)}
_LIMITS = {'coin': (100, 10_000_000), 'gold': (50, 100_000)}
_NEWS = {
    'coin': {
        'up': ('Mây Coin được nhiều cửa hàng trong phố đón nhận',
               'Cộng đồng Mây Coin hào hứng với bản cập nhật mới'),
        'down': ('Người giữ Mây Coin chốt lời, lực bán tăng',
                 'Tin đồn trong phố khiến người mua Mây Coin thận trọng'),
        'flat': ('Mây Coin giao dịch thăm dò, chưa rõ xu hướng',)},
    'gold': {
        'up': ('Nhu cầu vàng cưới trong phố tăng',
               'Người dân trong phố tăng mua vàng tích lũy'),
        'down': ('Nhiều người trong phố bán vàng chốt lời',
                 'Nhu cầu mua vàng tại Kim Phát hạ nhiệt'),
        'flat': ('Tiệm vàng giao dịch cầm chừng, chờ tin mới',)},
}


def now() -> float:
    return time.time()


def _salt() -> str:
    return os.environ.get('MNL_MARKET_SALT') or os.environ.get('MNL_GOLD_SALT', 'kim-phat')


def validate_runtime(public: bool = True, at: float | None = None) -> None:
    """Fail startup before public traffic can use predictable or future prices.

    This checks configuration, not the source or long-term persistence of a
    secret: operators must generate it randomly, retain it and share it across
    workers. Error messages deliberately contain variable names, never values.
    """
    if not public:
        return
    configured_epoch = os.environ.get('MNL_MARKET_EPOCH', '')
    try:
        configured_epoch = int(configured_epoch)
    except ValueError as exc:
        raise ValueError('Public market requires explicit MNL_MARKET_EPOCH') from exc
    if configured_epoch != EPOCH:
        raise ValueError('MNL_MARKET_EPOCH changed after import; restart with the intended configuration')
    secret = os.environ.get('MNL_MARKET_SALT') or os.environ.get('MNL_GOLD_SALT', '')
    if (len(secret.strip()) < 24 or len(set(secret)) < 8
            or not secret.replace('kim-phat', '')):
        raise ValueError('Public market requires persistent random MNL_MARKET_SALT or MNL_GOLD_SALT '
                         'of at least 24 characters; keep the same secret on all workers')
    if EPOCH > (now() if at is None else at):
        raise ValueError('MNL_MARKET_EPOCH is in the future; start the public market at or after cutover')


def base_price(asset: str) -> int:
    """Fixed migration anchor; explicit-date gold calls retain the legacy walk."""
    if asset == 'coin':
        return 10000
    if asset == 'gold':
        from . import vang
        return vang.price(_ANCHOR_DATE)
    raise ValueError(f'Unknown market asset: {asset}')


@functools.lru_cache(maxsize=8192)
def _randoms(asset: str, salt: str, kind: str, index: int) -> tuple[float, ...]:
    digest = hashlib.sha256(f'mnl-realtime-v1|{asset}|{salt}|{kind}|{index}'.encode()).digest()
    return tuple(int.from_bytes(digest[i:i + 8], 'big') / 2**64 for i in range(0, 32, 8))


def _regime(asset: str, salt: str, day: int) -> tuple[float, str, str]:
    selector, strength, headline, liquidity = _randoms(asset, salt, 'day', day)
    direction = 'up' if selector < .4 else 'down' if selector < .8 else 'flat'
    sign = 1 if direction == 'up' else -1 if direction == 'down' else 0
    titles = _NEWS[asset][direction]
    signal = sign * (.7 + .6 * strength) + 1.8 * (2 * liquidity - 1)
    return signal, direction, titles[int(headline * len(titles))]


def _weight(age: float) -> float:
    """Integral of an hourly unit impulse, followed by a continuous decay."""
    if age <= 0 or age >= _REGIME_DAYS:
        return 0.0
    if age <= 1:
        return _DECAY_DAYS * (1 - math.exp(-age / _DECAY_DAYS))
    weight = _DECAY_DAYS * (math.exp(-(age - 1) / _DECAY_DAYS)
                             - math.exp(-age / _DECAY_DAYS))
    return weight * min(1.0, _REGIME_DAYS - age)


@functools.lru_cache(maxsize=4096)
def _price(asset: str, salt: str, anchor: int, tick: int) -> int:
    if tick <= 0:
        return anchor
    amplitude, noise, shock, drift = _PARAMETERS[asset]
    age = tick / _TICKS_PER_DAY
    day = tick // _TICKS_PER_DAY
    # At most 48 old/current regimes, even after years offline. Each term is
    # causal: a regime starts with zero contribution at its opening boundary.
    regime = sum(_regime(asset, salt, d)[0] * _weight(age - d)
                 for d in range(max(0, day - _REGIME_DAYS + 1), day + 1))
    wobble = (2 * _randoms(asset, salt, 'tick', tick)[0] - 1) * noise
    wobble *= min(1.0, tick / _TICKS_PER_DAY)
    impulse = 0.0
    for old_tick in range(max(1, tick - 5), tick + 1):
        chance, sign, magnitude, _ = _randoms(asset, salt, 'shock', old_tick)
        if chance < .03:
            impulse += (1 if sign < .5 else -1) * shock * (.5 + .5 * magnitude) * (1 - (tick - old_tick) / 6)
    reference = min(4.0, 1 + drift * age)
    lower, upper = _LIMITS[asset]
    return max(lower, min(upper, round(anchor * reference * math.exp(amplitude * regime + wobble + impulse))))


@functools.lru_cache(maxsize=256)
def _snapshot(asset: str, salt: str, anchor: int, tick: int) -> tuple:
    start = max(0, tick - HISTORY + 1)
    prices = tuple(_price(asset, salt, anchor, t) for t in range(start, tick + 1))
    timestamps = tuple(EPOCH + t * TICK_SECONDS for t in range(start, tick + 1))
    _, direction, title = _regime(asset, salt, tick // _TICKS_PER_DAY)
    return prices, timestamps, direction, title


def quote(asset: str, at: float | None = None) -> dict:
    """Return a fresh quote; cached internals are immutable and private.

    Explicit pre-epoch times clamp to the migration anchor for offline tests.
    Public runtime validation prevents serving that anchor before live cutover.
    """
    anchor = base_price(asset)
    tick = max(0, math.floor(((now() if at is None else at) - EPOCH) / TICK_SECONDS))
    prices, timestamps, direction, title = _snapshot(asset, _salt(), anchor, tick)
    return {
        'price': prices[-1], 'previous': prices[-2] if len(prices) > 1 else prices[-1],
        'history': list(prices), 'timestamps': list(timestamps), 'tick': tick,
        'market_day': tick // _TICKS_PER_DAY + 1, 'as_of': timestamps[-1],
        'next_at': timestamps[-1] + TICK_SECONDS,
        'news': {'title': title, 'direction': direction, 'active': direction != 'flat'},
    }
