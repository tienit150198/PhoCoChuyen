"""🎢 Sàn Phố: the wild shared market (owner 24/10: "cho thêm nhiều loại coin khác, nhiều loại chứng khoán nữa nhé…
cho biến động lên xuống thất thường, có khi lên nhiều khi xuống nhiều cho mọi người cảm giác tiếc nuối").

Why the old market was easy (realtime_market.py, measured 24/10 with the real price code): the price was a deterministic
rising reference (+0,06 % a market day, about +1,4 % a real day) times a finite sum of decaying hourly regimes, so every
dip was pulled back to a trend anyone could read off the chart (buy 10 % under the 24 h average, sell 12 h later:
+13 % a trade after fees, 66 % winners; a week's hold +4 %).

This engine is a fair random walk instead. Every ten-minute step multiplies the price by e^r where, given everything
known before the step (the regimes, a pump in progress, the news already out), E[e^r] = 1 exactly: the compensator
`mu` cancels the expected growth of every random part (factor and own noise, jumps, sector and market shocks). A pump
is fair too: each step it either goes on (+g) or dumps (−A−δ, under where it began) with the hazard that makes the
step's expectation 1. Prices are therefore martingales: no rule built on what a player can see (dips, momentum,
headlines, a pump going on, the time of day) has a positive expectation, and the trading fee makes every round trip a
small loss on average, while single assets swing hard (fat tails: jumps, pump-and-dumps, wild regimes, sector and
market shocks). Bull and bear regimes are fair as well: a bull regime raises the odds of a crash jump, so the
compensator gives it a steady climb (and the opposite for a bear's sudden rebounds).

Bounds: a fair walk's median falls (by σ²/2 a day) while its mean holds, so the coins and stocks (and Mây Coin) are
split 1→10 above launch×10 and merged 10→1 under launch/10: price and units change together, a holding's value never
does (game/san.py, game/invest.py rescale units by 10^(e saved − e now); charts are split-adjusted). Gold gets calmer
near its floor and ceiling instead (the step shrinks; still a martingale). [lo, hi] clamps are a last resort. A risky
coin (said so in its description) is not merged but delisted when it falls to its delist level: holdings of that
listing are worth nothing, and the coin lists again ("2.0") a real day later at its launch price.

Randomness: one random.Random per stream and real day, seeded from the secret market salt (realtime_market._salt,
validated for public servers), the stream and the day: shared by every worker, unknowable to players, and nothing
future is ever computed or sent. Mây Coin and gold keep the old prices up to WILD_TICK and continue from their last
old price (no jump at deploy); the new assets list at WILD_TICK.

Cost: the walk is path dependent, so a process steps it forward from WILD_TICK once (≈ 3–9 µs an asset step: about
0,4–1 s of CPU a month of market age, 5–15 s after a year; a checkpoint file would remove it) and then one step every
ten minutes; server.py warms it before forking workers. Memory ≈ 15 MB a year of market.
Fictional gameplay parameters, not real market data.
"""
from __future__ import annotations

import array
import datetime as dt
import math
import os
import random
import threading
import time

from . import realtime_market as rm

ENGINE = 'mnl-wild-v1'
TICK = rm.TICK_SECONDS                 # 600 s
HOUR = rm.DAY_SECONDS // TICK          # 6 ticks: regimes change on the real hour
DAY_TICKS = 86400 // TICK              # 144 ticks a real day
RELIST = DAY_TICKS                     # a delisted risky coin lists again a real day later
SQ3H = math.sqrt(3) / 2
LN10 = math.log(10)
SPLIT = 10                # a new asset is split 1→10 above launch×SPLIT, and (not risky) merged 10→1 under launch/SPLIT
E_MAX = 12                # at most 10^12 either way

_DEFAULT_WILD_AT = int(dt.datetime(2026, 10, 26, 4, tzinfo=rm._VN).timestamp())


def _wild_at() -> int:
    raw = os.environ.get('MNL_MARKET_WILD_AT', '')
    try:
        return int(raw) if raw else _DEFAULT_WILD_AT
    except ValueError as exc:
        raise ValueError('MNL_MARKET_WILD_AT must be a Unix timestamp') from exc


WILD_AT = _wild_at()


def wild_tick(epoch: int | None = None, at: int | None = None) -> int:
    """The first tick of the new market: the first whole market hour at or after WILD_AT."""
    epoch = rm.EPOCH if epoch is None else epoch
    at = WILD_AT if at is None else at
    t = max(1, -(-(at - epoch) // TICK))
    return -(-t // HOUR) * HOUR


WILD_TICK = wild_tick()

# ---------------------------------------------------------------- catalogue
# Factors: the stock index and the coin market, then sectors. vol = daily log sd in the normal market regime;
# shocks = per day, (lo, hi) log size, share of shocks that are up.
FACTORS = {
    'stock': dict(vol=.022, shocks=.15, size=(.03, .08), up=.35),
    'coin': dict(vol=.07, shocks=.3, size=(.06, .20), up=.4),
}
SECTORS = {
    # stocks
    'food': dict(market='stock', vol=.02, shocks=.2, size=(.04, .10), up=.5, name='Ăn uống'),
    'tech': dict(market='stock', vol=.03, shocks=.25, size=(.05, .14), up=.5, name='Công nghệ'),
    'realty': dict(market='stock', vol=.025, shocks=.2, size=(.05, .14), up=.45, name='Địa ốc'),
    'bank': dict(market='stock', vol=.015, shocks=.15, size=(.04, .10), up=.45, name='Ngân hàng'),
    'transport': dict(market='stock', vol=.02, shocks=.2, size=(.04, .12), up=.5, name='Vận tải'),
    'fish': dict(market='stock', vol=.025, shocks=.25, size=(.05, .14), up=.5, name='Thủy sản'),
    'pet': dict(market='stock', vol=.025, shocks=.2, size=(.05, .12), up=.5, name='Thú cưng'),
    'energy': dict(market='stock', vol=.025, shocks=.2, size=(.05, .14), up=.5, name='Năng lượng'),
    'fun': dict(market='stock', vol=.03, shocks=.2, size=(.05, .14), up=.5, name='Giải trí'),
    'health': dict(market='stock', vol=.012, shocks=.12, size=(.03, .08), up=.5, name='Y tế'),
    # coins and gold
    'cloud': dict(market='coin', vol=.05, shocks=.3, size=(.05, .16), up=.45, name='Coin phố'),
    'meme': dict(market='coin', vol=.10, shocks=.3, size=(.10, .30), up=.45, name='Coin meme'),
    'stable': dict(market='coin', vol=.004, shocks=.04, size=(.03, .08), up=.4, name='Coin bình ổn'),
    'metal': dict(market='stock', vol=.018, shocks=.15, size=(.02, .06), up=.55, name='Kim loại quý'),
}
# Regimes: (vol multiplier, jump-rate multiplier, shift of the up share of jumps).
REGIMES = {'calm': (.55, .5, 0.), 'normal': (1., 1., 0.), 'wild': (2.0, 2.2, 0.),
           'bull': (.85, 1.6, -.3), 'bear': (.9, 1.6, .3)}
REGIME_NAMES = tuple(REGIMES)
MARKET_REGIMES = {'calm': .6, 'normal': 1., 'wild': 2.2}
MARKET_WEIGHTS = (('calm', .3), ('normal', .5), ('wild', .2))
REGIME_WEIGHTS = {
    'stock': (('calm', .3), ('normal', .4), ('wild', .1), ('bull', .1), ('bear', .1)),
    'coin': (('calm', .2), ('normal', .35), ('wild', .15), ('bull', .15), ('bear', .15)),
    'gold': (('calm', .45), ('normal', .45), ('wild', .1)),
}
REGIME_TEXT = {'calm': 'Đi ngang', 'normal': 'Bình thường', 'wild': 'Biến động mạnh', 'bull': 'Đang lên', 'bear': 'Đang xuống'}


def _a(id, kind, sym, name, emoji, sector, launch, vol, beta, gamma, jumps, jsize, up=.5, pumps=0., pump=(.04, .10),
       risky=False, unlock=500, hours=12, desc='', lo=None, hi=None, unit='coin', fee=2, legacy=False, pmax=None,
       splits=None):
    lo = lo if lo is not None else max(50, launch // 200) if risky else max(100, launch // 50)
    hi = hi if hi is not None else launch * 60
    return dict(id=id, kind=kind, sym=sym, name=name, emoji=emoji, sector=sector, launch=launch, vol=vol, beta=beta,
                gamma=gamma, jumps=jumps, jsize=jsize, up=up, pumps=pumps, pump=pump, risky=risky, unlock=unlock,
                hours=hours, desc=desc, lo=lo, hi=hi, unit=unit, fee=fee, legacy=legacy,
                splits=not legacy if splits is None else splits,
                pmax=pmax if pmax is not None else 1.6 if risky else 1.3 if sector == 'meme' else 1.1,
                logs=(math.log(launch / SPLIT), math.log(launch * SPLIT)),
                delist=max(100, launch // 80) if risky else 0)


C, S = 'coin', 'stock'
ASSETS = {a['id']: a for a in (
    # the two old ones: same ids, they continue from their last old price
    _a('coin', C, 'MÂY', 'Mây Coin', '☁️', 'cloud', 10000, .07, 1., 1., 1., (.04, .12), pumps=.03,
       desc='Đồng coin đầu tiên của phố.', lo=100, hi=10_000_000, legacy=True,
       splits=True),
    _a('gold', 'gold', 'VÀNG', 'Vàng', '🪙', 'metal', 500, .025, -.2, 1., .4, (.02, .05), lo=50, hi=100_000,
       desc='Vàng của tiệm Kim Phát.', unit='chi', fee=0, legacy=True),
    # coins
    _a('pho', C, 'PHO', 'Phở Coin', '🍜', 'cloud', 25000, .07, 1., 1., .9, (.04, .12), pumps=.03,
       desc='Coin của hội quán phở trong phố. Nóng như nồi nước dùng, lúc sôi lúc nguội.'),
    _a('banhmi', C, 'BMI', 'Bánh Mì Coin', '🥖', 'cloud', 12000, .05, .8, .8, .7, (.03, .10), pumps=.02,
       desc='Coin bình dân, giòn rụm. Biến động vừa phải so với các coin khác.'),
    _a('lua', C, 'LUA', 'Lúa Coin', '🌾', 'cloud', 8000, .07, .8, 1., .9, (.04, .13), pumps=.03,
       desc='Coin nhà nông: được mùa thì lên, mất mùa thì xuống, chẳng ai đoán trước.'),
    _a('caro', C, 'CARO', 'Cá Rô Token', '🐟', 'cloud', 6000, .08, 1., 1.1, 1.1, (.05, .15), pumps=.04,
       desc='Token của dân câu hồ chung. Có hôm cá cắn liên tục, có hôm cả hồ im re.'),
    _a('trada', C, 'TRADA', 'Trà Đá Coin', '🧊', 'stable', 1000, .004, .05, 1., .04, (.03, .10), up=.35,
       desc='Coin “bình ổn”: gần như đứng giá quanh 10 xu. Hiếm khi lệch giá, nhưng đã lệch là giật mình.'),
    _a('heo', C, 'HEO', 'Heo Đất Coin', '🐷', 'stable', 5000, .01, .25, 1., .1, (.03, .09),
       desc='Coin chậm mà chắc của phố. Ít sóng, lãi lỗ đều nhỏ.'),
    _a('mai', C, 'MAI', 'Mèo Mai Coin', '🐱', 'meme', 3000, .08, .9, .7, 1.1, (.05, .15), pumps=.06, pump=(.04, .10), pmax=1.2,
       hours=8, desc='Coin meme theo bé mèo Mai. Hay được hô hào lên “mặt trăng” rồi rơi cái bịch, như mèo nhảy tủ lạnh.'),
    _a('dua', C, 'DUA', 'Dưa Hấu Coin', '🍉', 'meme', 5000, .10, 1.1, 1., 1.3, (.05, .18), pumps=.08, pump=(.05, .12),
       risky=True, unlock=3000, hours=8,
       desc='⚠️ Rủi ro rất cao: ruột đỏ hay ruột trắng chỉ biết khi bổ ra. Rơi tới mức hủy niêm yết là coin về 0.'),
    _a('gachien', C, 'GACH', 'Gà Chiến Coin', '🐓', 'meme', 7000, .11, 1.2, 1.1, 1.4, (.06, .20), pumps=.1,
       pump=(.06, .14), risky=True, unlock=3000, hours=6,
       desc='⚠️ Rủi ro rất cao: thắng thì gáy to, thua thì mất trắng. Có thể bị hủy niêm yết, coin về 0.'),
    _a('cuoi', C, 'CUOI', 'Cuội Coin', '🌕', 'meme', 4000, .11, 1.2, 1.1, 1.3, (.06, .20), pumps=.12, pump=(.06, .14),
       risky=True, unlock=3000, hours=6,
       desc='⚠️ Rủi ro rất cao: “bay lên cung trăng” rồi rơi xuống gốc đa. Có thể bị hủy niêm yết, coin về 0.'),
    _a('bao', C, 'BAO', 'Bão Coin', '🌪️', 'meme', 15000, .12, 1.3, 1.2, 1.5, (.06, .22), pumps=.08, pump=(.06, .15),
       risky=True, unlock=10000, hours=6,
       desc='⚠️ Rủi ro cực cao: quét qua là tan tành. Hay sập rất sâu, có thể bị hủy niêm yết, coin về 0.'),
    # stocks (cổ phiếu of the town's companies, fee 1 %)
    _a('pmf', S, 'PMF', 'Phố Mây Food', '🍲', 'food', 45000, .015, .8, .8, .12, (.05, .12), unlock=2000, hours=18, fee=1,
       unit='cp', desc='Tập đoàn ăn uống lớn nhất phố. Cổ phiếu “phòng thủ”, ít sóng.'),
    _a('tsg', S, 'TSG', 'Trà Sữa Gió', '🧋', 'food', 22000, .03, 1., 1., .2, (.06, .16), unlock=2000, fee=1, unit='cp',
       desc='Chuỗi trà sữa của giới trẻ. Mốt lên mốt xuống, giá cũng vậy.'),
    _a('mtech', S, 'MTC', 'Mây Tech', '💻', 'tech', 80000, .03, 1.4, 1.2, .2, (.06, .18), unlock=2000, fee=1, unit='cp',
       desc='Công ty công nghệ của phố. Tin tốt thì bay, tin xấu thì rơi.'),
    _a('app', S, 'APP', 'Ứng Dụng Phố', '📱', 'tech', 15000, .04, 1.5, 1.2, .25, (.07, .20), unlock=2000, fee=1, unit='cp',
       desc='Startup ứng dụng gọi món, gọi xe. Tăng trưởng nóng, rủi ro cũng nóng.'),
    _a('dat', S, 'DAT', 'Địa Ốc Phố Mây', '🏘️', 'realty', 60000, .02, 1.2, 1., .15, (.06, .18), up=.45, unlock=2000,
       hours=24, fee=1, unit='cp', desc='Chủ đầu tư các khu nhà trong phố. Im lìm rồi bất ngờ có sóng lớn.'),
    _a('nhp', S, 'NHP', 'Ngân Hàng Phố', '🏦', 'bank', 30000, .012, 1.3, 1., .1, (.05, .14), up=.45, unlock=2000,
       hours=24, fee=1, unit='cp', desc='Cổ phiếu ngân hàng: đi theo cả thị trường, ít khi tự bứt phá.'),
    _a('xom', S, 'XOM', 'Xe Ôm Nhanh', '🛵', 'transport', 18000, .025, 1., 1., .15, (.05, .15), unlock=2000, fee=1,
       unit='cp', desc='Hãng xe ôm công nghệ. Giá xăng lên xuống là cổ phiếu cũng nhảy theo.'),
    _a('vsm', S, 'VSM', 'Vận Tải Sông Mây', '🚢', 'transport', 26000, .022, .9, 1., .12, (.05, .14), unlock=2000,
       hours=18, fee=1, unit='cp', desc='Đội ghe tàu chở hàng trên sông. Chậm nhưng hay gặp sóng.'),
    _a('hca', S, 'HCA', 'Hồ Cá Phố Mây', '🎣', 'fish', 12000, .03, .7, 1.1, .2, (.06, .18), unlock=2000, fee=1,
       unit='cp', desc='Công ty quản lý hồ câu chung. Mùa cá lớn thì lãi, hồ vắng thì lỗ.'),
    _a('thu', S, 'THU', 'Thú Cưng Vui', '🐶', 'pet', 20000, .028, .8, 1.1, .18, (.06, .16), unlock=2000, fee=1,
       unit='cp', desc='Chuỗi cửa hàng thú cưng. Dân phố mê thú cưng nhưng tin đồn cũng nhiều.'),
    _a('nlm', S, 'NLM', 'Năng Lượng Mặt Trời Mây', '☀️', 'energy', 35000, .025, 1.1, 1.1, .15, (.06, .16),
       unlock=2000, fee=1, unit='cp', desc='Điện mặt trời trên mái nhà phố. Trời nắng chưa chắc giá đã lên.'),
    _a('krk', S, 'KRK', 'Karaoke Phố', '🎤', 'fun', 9000, .035, 1., 1.2, .22, (.06, .18), unlock=2000, fee=1,
       unit='cp', desc='Chuỗi phòng hát. Cuối tuần đông khách, cổ phiếu hát lúc cao lúc thấp.'),
    _a('ntp', S, 'NTP', 'Nhà Thuốc Phố', '💊', 'health', 40000, .012, .5, .8, .08, (.04, .10), unlock=2000, hours=24,
       fee=1, unit='cp', desc='Chuỗi nhà thuốc. Cổ phiếu ít sóng nhất sàn, nhưng không phải không có.'),
)}
ORDER = tuple(ASSETS)
NEW = tuple(a for a in ORDER if not ASSETS[a]['legacy'])

HEADLINES = {
    'stock': {'up': ('{n} báo lãi quý vượt kỳ vọng', '{n} ký được hợp đồng lớn', 'Quỹ lớn gom mạnh cổ phiếu {s}',
                     '{n} ra mắt sản phẩm mới gây sốt', 'Tin đồn {n} sắp được mua lại'),
              'down': ('{n} báo lỗ bất ngờ', 'Lãnh đạo {n} bán bớt cổ phiếu', '{n} bị khách phàn nàn tràn lan',
                       'Quỹ lớn xả cổ phiếu {s}', '{n} chậm kế hoạch mở rộng')},
    'coin': {'up': ('Ví lớn gom {s} liên tục', '{n} được thêm nhiều quán trong phố nhận thanh toán',
                    'Cộng đồng {n} hô hào “về bờ”', 'Sàn trong phố mở thêm cặp giao dịch {s}'),
             'down': ('Ví lớn xả {s}', '{n} bị đồn lỗi ví', 'Nhóm kín bán tháo {n}', 'Người giữ {n} hoảng loạn chốt lời')},
    'gold': {'up': ('Nhu cầu vàng cưới trong phố tăng', 'Người dân tăng mua vàng tích lũy'),
             'down': ('Nhiều người bán vàng chốt lời', 'Nhu cầu mua vàng tại Kim Phát hạ nhiệt')},
}
SECTOR_NEWS = {'up': ('Ngành {n} được hỗ trợ, cả nhóm tăng', 'Dòng tiền đổ vào nhóm {n}'),
               'down': ('Ngành {n} gặp khó, cả nhóm giảm', 'Dòng tiền rút khỏi nhóm {n}')}
MARKET_NEWS = {'stock': {'up': 'Cả sàn cổ phiếu bừng sáng', 'down': 'Cả sàn cổ phiếu đỏ lửa'},
               'coin': {'up': 'Thị trường coin bùng nổ', 'down': 'Thị trường coin sập mạnh'}}
NEWS_MATCH = .72          # a headline names the move's direction this often; otherwise "sell the news"
EVENT_MIN = {'stock': .05, 'coin': .10, 'gold': .02}   # a jump this large gets a headline
EVENTS_KEEP = 60          # market-wide events kept (newest last)


# ---------------------------------------------------------------- maths
def _ih_log_mgf(x: float) -> float:
    """log E[exp(x·Z)] for the Irwin–Hall draw above."""
    k = abs(x) * SQ3H
    if k < 1e-6:
        return x * x / 2
    return 4 * math.log(math.sinh(k) / k)


def _u_mgf(c: float, lo: float, hi: float) -> float:
    """E[exp(c·U)], U uniform on [lo, hi]."""
    if abs(c) < 1e-12:
        return 1.
    if hi - lo < 1e-12:
        return math.exp(c * lo)
    return (math.exp(c * hi) - math.exp(c * lo)) / (c * (hi - lo))


def _jump_log_mgf(p: float, q: float, lo: float, hi: float, scale: float = 1.) -> float:
    """log E[exp(J)]: with probability p a jump of size scale·U[lo, hi], up with probability q, else down."""
    if p <= 0:
        return 0.
    return math.log1p(p * (q * (_u_mgf(scale, lo, hi) - 1) + (1 - q) * (_u_mgf(-scale, lo, hi) - 1)))



# ---------------------------------------------------------------- the engine
_LOG6 = math.log(6)       # the last 6x before a bound is calmer (Mây Coin and gold)


class Engine:
    """The whole market for one salt and one cutover, stepped forward one tick at a time (never ahead of `upto`)."""

    def __init__(self, salt: str, start: int, legacy_start: dict | None = None):
        self.salt, self.start = salt, start
        self.lock = threading.RLock()
        self.t = start - 1                     # last computed tick
        self.prices = {a: array.array('q') for a in ORDER}   # price at tick start+i (0: delisted)
        self.gens = {a: array.array('h') for a in ORDER}     # listing generation at that tick
        self.exps = {a: array.array('b') for a in ORDER}     # split exponent e at that tick: price = base price × 10^e
        self.daymax = {a: array.array('d') for a in ORDER}   # max base price (price / 10^e) of each whole day block
        self.events = []                       # (tick, asset or '', kind, text, move %, sign)
        self.last_event = {a: None for a in ORDER}
        self.mreg = {m: 'normal' for m in FACTORS}
        self.rngs = {}
        self.mu = {}
        legacy_start = legacy_start or {}
        self.st = {}
        self.const = {}
        for a in ORDER:
            sp = ASSETS[a]
            sec = SECTORS[sp['sector']]
            m = sec['market']
            p0 = legacy_start.get(a, sp['launch'])
            self.st[a] = dict(L=math.log(max(sp['lo'], min(sp['hi'], p0))), reg='normal', pump=None, gen=1, off=-1, e=0)
            kind = 'gold' if sp['kind'] == 'gold' else sp['kind']
            self.const[a] = (sp, sec, m, FACTORS[m], math.log(sp['lo']), math.log(sp['hi']), REGIME_WEIGHTS[kind],
                             1 / sp['hours'], EVENT_MIN[kind], HEADLINES[kind])

    def _rng(self, stream: str, day: int):
        return random.Random(f'{ENGINE}|{self.salt}|{stream}|{day}').random

    @staticmethod
    def _mu(sp, sec, fac, reg, mreg, tau) -> float:
        """The compensator: -log E[e^(everything random in this step)] given the state, so that E[e^r] = 1."""
        vm, jm, qs = REGIMES[reg]
        mv = MARKET_REGIMES[mreg]
        lo, hi = sp['jsize']
        return -(_ih_log_mgf(sp['beta'] * fac['vol'] * mv * tau / 12) + _ih_log_mgf(sp['gamma'] * sec['vol'] * vm * tau / 12)
                 + _ih_log_mgf(sp['vol'] * vm * tau / 12)
                 + _jump_log_mgf(min(.5, sp['jumps'] * jm / DAY_TICKS), min(.95, max(.05, sp['up'] + qs)), lo, hi, tau)
                 + _jump_log_mgf(sec['shocks'] / DAY_TICKS, sec['up'], *sec['size'], sp['gamma'] * tau)
                 + _jump_log_mgf(fac['shocks'] / DAY_TICKS, fac['up'], *fac['size'], sp['beta'] * tau))

    def step(self) -> None:
        t = self.t + 1
        sub = t % HOUR
        if t % DAY_TICKS == 0 or not self.rngs:
            day = t // DAY_TICKS
            self.rngs = {k: self._rng(k, day) for k in ('mkt:stock', 'mkt:coin', *('sec:' + s for s in SECTORS),
                                                          *('a:' + a for a in ORDER))}
        R = self.rngs
        mdraw = {}
        for m, f in FACTORS.items():
            u = R['mkt:' + m]
            if sub == 0:
                sw, pick = u(), _pick_u(u(), MARKET_WEIGHTS)
                if sw < 1 / 18:
                    self.mreg[m] = pick
            z = (u() + u() + u() + u() - 2.) * 1.7320508075688772
            shock = _jump_u(u(), u(), u(), f['shocks'] / DAY_TICKS, f['up'], *f['size'])
            mdraw[m] = (z, shock)
            if shock:
                d = 'up' if shock > 0 else 'down'
                self.events.append((t, '', 'market:' + m, MARKET_NEWS[m][d], round((math.exp(shock) - 1) * 100),
                                    1 if shock > 0 else -1))
        sdraw = {}
        for s, f in SECTORS.items():
            u = R['sec:' + s]
            z = (u() + u() + u() + u() - 2.) * 1.7320508075688772
            pick = u()
            shock = _jump_u(u(), u(), u(), f['shocks'] / DAY_TICKS, f['up'], *f['size'])
            sdraw[s] = (z, shock)
            if shock:
                d = 'up' if shock > 0 else 'down'
                lines = SECTOR_NEWS[d]
                self.events.append((t, '', 'sector:' + s, lines[int(pick * len(lines))].format(n=f['name'].lower()),
                                    round((math.exp(shock) - 1) * 100), 1 if shock > 0 else -1))
        for a in ORDER:
            self._step_asset(t, a, sub, R['a:' + a], mdraw, sdraw)
        self.t = t
        if len(self.events) > EVENTS_KEEP * 2:
            del self.events[:-EVENTS_KEEP]

    def _step_asset(self, t, a, sub, u, mdraw, sdraw) -> None:
        sp, sec, m, fac, llo, lhi, weights, switch, event_min, headlines = self.const[a]
        st = self.st[a]
        # 15 draws a tick (17 on the hour), in a fixed order whatever happens
        if sub == 0:
            sw, pick = u(), _pick_u(u(), weights)
        else:
            sw, pick = 1., ''
        z = (u() + u() + u() + u() - 2.) * 1.7320508075688772
        j0, j1, j2 = u(), u(), u()
        p0, p1, p2, p3, p4 = u(), u(), u(), u(), u()
        h0, h1 = u(), u()
        if st['off'] >= 0:                       # delisted: lists again RELIST ticks after
            if t < st['off'] + RELIST:
                self._append(a, 0, st['gen'], st['e'])
                return
            st.update(L=math.log(sp['launch']), reg='normal', pump=None, gen=st['gen'] + 1, off=-1, e=0)
            self._event(t, a, 'relist', f'{sp["name"]} niêm yết lại ({st["gen"]}.0) với giá khởi điểm', 0, 1)
        if sw < switch and pick != st['reg']:
            st['reg'] = pick
            if pick in ('bull', 'bear', 'wild'):
                self._event(t, a, 'regime', f'{sp["name"]}: {REGIME_TEXT[pick].lower()}', 0,
                            1 if pick == 'bull' else -1 if pick == 'bear' else 0)
        L = st['L']
        reg, mreg = st['reg'], self.mreg[m]
        vm, jm, qs = REGIMES[reg]
        mv = MARKET_REGIMES[mreg]
        if not sp['splits']:                     # gold: calmer near its bounds
            top = (lhi - L) / _LOG6
            top = 1. if top >= 1 else .12 if top < .12 else top
            bottom = (L - llo) / _LOG6
            tau = min(top, 1. if bottom >= 1 else .12 if bottom < .12 else bottom)
            tau = round(tau * 50) / 50           # steps of 0,02: the compensator of each is computed once
        else:
            top = tau = 1.                       # split or merged instead (value unchanged)
        key = (a, reg, mreg, tau)
        mu = self.mu.get(key)
        if mu is None:
            mu = self.mu[key] = self._mu(sp, sec, fac, reg, mreg, tau)
        mz, mshock = mdraw[m]
        sz, sshock = sdraw[sp['sector']]
        r = (mu + (sp['beta'] * fac['vol'] * mv * mz + sp['gamma'] * sec['vol'] * vm * sz + sp['vol'] * vm * z) * tau / 12
             + (sp['gamma'] * sshock + sp['beta'] * mshock) * tau)
        p_j = sp['jumps'] * jm / DAY_TICKS
        jump = 0.
        if j0 < (p_j if p_j < .5 else .5):
            q_j = sp['up'] + qs
            lo, hi = sp['jsize']
            size = (lo + (hi - lo) * j2) * tau
            jump = size if j1 < (.95 if q_j > .95 else .05 if q_j < .05 else q_j) else -size
            r += jump
        # a pump: fair at every step (the hazard makes E[e^step] = 1); the dump goes under where it began
        pump = st['pump']
        if pump is None and sp['pumps'] and p0 < sp['pumps'] * tau / DAY_TICKS:
            g_lo, g_hi = sp['pump']
            pump = st['pump'] = [g_lo + (g_hi - g_lo) * p1, 0., (.08 + .2 * p2) * tau]
        if pump is not None:
            g = min(pump[0] * (.5 + p3) * top, sp['pmax'] - pump[1])
            eg, D = math.exp(g), pump[1] + pump[2]
            if g < .002:                         # the pump's ceiling: it ends where it is (nothing random: still fair)
                st['pump'] = None
                self._event(t, a, 'peak', f'{sp["name"]} hạ nhiệt sau đợt hô hào', 0, 0)
            elif p4 < (eg - 1) / (eg - math.exp(-D)):
                r -= D
                st['pump'] = None
                self._event(t, a, 'dump', f'{sp["name"]} bị xả hàng, giá rơi thẳng đứng' if pump[1] else
                            f'{sp["name"]} bị bán tháo bất ngờ', -round((1 - math.exp(-D)) * 100), -1)
            else:
                if not pump[1]:
                    self._event(t, a, 'pump', f'{sp["name"]} được hô hào “lên mặt trăng”', round((eg - 1) * 100), 1)
                r += g
                pump[1] += g
        if jump and (jump if jump > 0 else -jump) >= event_min:
            sign = 1 if jump > 0 else -1
            tone = ('up' if sign > 0 else 'down') if h0 < NEWS_MATCH else ('down' if sign > 0 else 'up')
            lines = headlines[tone]
            self._event(t, a, 'news', lines[int(h1 * len(lines))].format(n=sp['name'], s=sp['sym']),
                        round((math.exp(jump) - 1) * 100), sign)
        L += r
        e = st['e']
        if not sp['splits']:
            L = llo if L < llo else lhi if L > lhi else L
        else:
            # A split keeps the price readable and every holding's value the same (game/san.py rescales units):
            # 1→10 above launch×SPLIT; 10→1 under launch/SPLIT (not for a risky coin: it is delisted instead).
            while L + e * LN10 > sp['logs'][1] and e > -E_MAX:
                e -= 1
                self._event(t, a, 'split', f'{sp["name"]} tách 1 thành 10: giá chia 10, số lượng nhân 10', 0, 0)
            while not sp['risky'] and L + e * LN10 < sp['logs'][0] and e < E_MAX:
                e += 1
                self._event(t, a, 'split', f'{sp["name"]} gộp 10 thành 1: giá nhân 10, số lượng chia 10', 0, 0)
            st['e'] = e
            lo_e, hi_e = llo - e * LN10, lhi - e * LN10
            L = lo_e if L < lo_e else hi_e if L > hi_e else L
        st['L'] = L
        price = round(math.exp(L + e * LN10)) if e else round(math.exp(L))
        if sp['risky'] and price <= sp['delist']:
            st['off'], st['pump'] = t, None
            self._event(t, a, 'delist', f'{sp["name"]} bị hủy niêm yết, coin về 0', -100, -1)
            price = 0
        else:
            price = sp['lo'] if price < sp['lo'] else sp['hi'] if price > sp['hi'] else price
        self._append(a, price, st['gen'], e)

    def _append(self, a, price, gen, e) -> None:
        ps = self.prices[a]
        ps.append(price)
        self.gens[a].append(gen)
        self.exps[a].append(e)
        n = len(ps)
        if n % DAY_TICKS == 0:
            xs = self.exps[a]
            self.daymax[a].append(max(ps[k] / 10. ** xs[k] for k in range(n - DAY_TICKS, n)))

    def _event(self, t, a, kind, text, move, sign) -> None:
        ev = (t, a, kind, text, move, sign)
        self.events.append(ev)
        self.last_event[a] = ev

    def advance(self, upto: int) -> None:
        with self.lock:
            while self.t < upto:
                self.step()

    # -- reads (arrays only grow, so a reader needs no lock once advance() returned)
    def price(self, a: str, t: int) -> int:
        return self.prices[a][t - self.start]

    def gen(self, a: str, t: int) -> int:
        return self.gens[a][t - self.start]

    def exp10(self, a: str, t: int) -> int:
        return self.exps[a][t - self.start]

    def range_max(self, a: str, lo: int, hi: int) -> int:
        """Max price over ticks lo..hi (both included, clipped to what exists), in the split terms of tick hi: edge
        ticks one by one, whole days by block."""
        ps, xs, dm = self.prices[a], self.exps[a], self.daymax[a]
        i, j = max(0, lo - self.start), min(len(ps) - 1, hi - self.start)
        if j < 0:
            return 0
        best = 0.
        while i <= j and i % DAY_TICKS:
            best = max(best, ps[i] / 10. ** xs[i])
            i += 1
        while i + DAY_TICKS - 1 <= j and i // DAY_TICKS < len(dm):
            best = max(best, dm[i // DAY_TICKS])
            i += DAY_TICKS
        while i <= j:
            best = max(best, ps[i] / 10. ** xs[i])
            i += 1
        return round(best * 10. ** xs[j])


def _pick_u(u: float, weights) -> str:
    for name, w in weights:
        u -= w
        if u < 0:
            return name
    return weights[-1][0]


def _jump_u(a: float, b: float, c: float, p: float, q: float, lo: float, hi: float) -> float:
    """A shock: with probability p, of size U[lo, hi], up with probability q (three uniforms already drawn)."""
    if a >= p:
        return 0.
    size = lo + (hi - lo) * c
    return size if b < q else -size


# ---------------------------------------------------------------- process-wide engines
_engines: dict = {}
_glock = threading.Lock()


def _legacy_start(salt: str, start: int) -> dict:
    return {'coin': rm._price('coin', salt, rm.base_price('coin'), start - 1),
            'gold': rm._price('gold', salt, rm.base_price('gold'), start - 1)}


def engine(upto: int) -> Engine:
    salt, start = rm._salt(), WILD_TICK
    key = (salt, start, rm.EPOCH)
    with _glock:
        eng = _engines.get(key)
        if eng is None:
            eng = _engines[key] = Engine(salt, start, _legacy_start(salt, start))
    eng.advance(upto)
    return eng


def tick_of(at: float | None = None) -> int:
    return max(0, math.floor(((rm.now() if at is None else at) - rm.EPOCH) / TICK))


def listed(t: int) -> bool:
    return t >= WILD_TICK


def price_at(a: str, t: int) -> int:
    """The price at tick t (0 while delisted). Mây Coin and gold: the old market before WILD_TICK; a new asset is at
    its launch price before it lists."""
    if t < WILD_TICK:
        if a == 'coin' or a == 'gold':
            return rm._price(a, rm._salt(), rm.base_price(a), t)
        return ASSETS[a]['launch']
    return engine(t).price(a, t)


def gen_at(a: str, t: int) -> int:
    return 1 if t < WILD_TICK else engine(t).gen(a, t)


def exp_at(a: str, t: int) -> int:
    """The split exponent at tick t: a unit bought at exponent e0 is 10^(e0 - e) units now (game/san.py)."""
    return 0 if t < WILD_TICK else engine(t).exp10(a, t)


def history(a: str, t: int, n: int) -> list[int]:
    """The last n prices up to tick t (fewer for a new asset that listed less than n ticks ago)."""
    lo = max(0, t - n + 1)
    if t < WILD_TICK:
        return [price_at(a, k) for k in range(lo, t + 1)] if ASSETS[a]['legacy'] else [ASSETS[a]['launch']]
    eng = engine(t)
    old = [price_at(a, k) for k in range(lo, WILD_TICK)] if lo < WILD_TICK and ASSETS[a]['legacy'] else []
    i, j = max(lo, WILD_TICK) - eng.start, t + 1 - eng.start
    ps, xs = eng.prices[a], eng.exps[a]
    e = xs[j - 1]
    if e and old:                                # the old market counted in e = 0 (Mây Coin)
        old = [round(x * 10. ** e) for x in old]
    if all(x == e for x in xs[i:j]):
        return old + list(ps[i:j])
    # split-adjusted: every older price in the terms of the latest split (a chart never jumps ×10)
    return old + [round(ps[k] * 10. ** (e - xs[k])) for k in range(i, j)]


def peak_since(a: str, since: int, t: int) -> int:
    """The highest price from tick `since` to t, counted from WILD_TICK on (the regret note: "nếu bán lúc đỉnh")."""
    if t < WILD_TICK or since > t:
        return 0
    return engine(t).range_max(a, max(since, WILD_TICK), t)


def news(a: str, t: int) -> dict:
    """{title, direction, active, move}: the asset's latest headline from the last market hour (public-safe)."""
    if t < WILD_TICK:
        return {'title': '', 'direction': 'flat', 'active': False, 'move': 0}
    eng = engine(t)
    ev = eng.last_event.get(a)
    if not ev or ev[0] > t or t - ev[0] >= HOUR:
        return {'title': '', 'direction': 'flat', 'active': False, 'move': 0}
    return {'title': ev[3], 'direction': 'up' if ev[5] > 0 else 'down' if ev[5] < 0 else 'flat', 'active': True,
            'move': ev[4]}


def quote(a: str, at: float | None = None, n: int = rm.HISTORY) -> dict:
    """The realtime_market.quote shape for any asset at a tick on or after WILD_TICK."""
    t = tick_of(at)
    hist = history(a, t, n)
    ts = [rm.EPOCH + k * TICK for k in range(t - len(hist) + 1, t + 1)]
    return {'price': hist[-1], 'previous': hist[-2] if len(hist) > 1 else hist[-1], 'history': hist, 'timestamps': ts,
            'tick': t, 'market_day': t // HOUR + 1, 'as_of': ts[-1], 'next_at': ts[-1] + TICK,
            'news': {k: v for k, v in news(a, t).items() if k != 'move'}, 'e': exp_at(a, t)}


def adjusted(a: str, t: int, ref: int) -> int:
    """The price at tick t in the split terms of tick ref (charts: a split or merge is not a ×10 move)."""
    d = exp_at(a, ref) - exp_at(a, t)
    p = price_at(a, t)
    return round(p * 10. ** d) if d else p


def _change(now: int, then: int) -> float:
    return round((now - then) * 100 / then, 1) if then > 0 and now > 0 else 0.


def board(at: float | None = None) -> dict:
    """Everything the market screen needs for every asset at the current tick (no player data): price, the previous
    tick, the change over 1 h and 24 h, 24 hourly points, the high/low of 24 h, the listing state, the latest headline,
    and the market's recent events (the ticker). Pure function of the tick."""
    t = tick_of(at)
    eng = engine(t) if t >= WILD_TICK else None
    out = {}
    for a in ORDER:
        sp = ASSETS[a]
        hist = history(a, t, DAY_TICKS + 1)
        p = hist[-1]
        live = [x for x in hist if x > 0]
        g = gen_at(a, t)
        h1 = hist[-1 - HOUR] if len(hist) > HOUR else hist[0]
        d1 = hist[0]
        out[a] = dict(price=p, previous=hist[-2] if len(hist) > 1 else p, ch1h=_change(p, h1), ch24h=_change(p, d1),
                      hi=max(live) if live else 0, lo=min(live) if live else 0,
                      spark=[hist[k] for k in range(len(hist) - 1, -1, -HOUR)][::-1],
                      listed=listed(t) or sp['legacy'], delisted=p == 0 and listed(t), gen=g, e=exp_at(a, t), news=news(a, t),
                      regime=REGIME_TEXT[eng.st[a]['reg']] if eng is not None and eng.t == t else '')
    return dict(tick=t, as_of=rm.EPOCH + t * TICK, next_at=rm.EPOCH + (t + 1) * TICK, wild_tick=WILD_TICK,
                wild_at=rm.EPOCH + WILD_TICK * TICK, assets=out, ticker=ticker(t))


def ticker(t: int) -> list[dict]:
    """The market's newest events of the last two hours plus the big movers of the last hour, newest first (≤ 8)."""
    if t < WILD_TICK:
        return []
    eng = engine(t)
    rows = []
    for ev in reversed(eng.events):
        if ev[0] > t:
            continue
        if t - ev[0] >= 2 * HOUR or len(rows) >= 6:
            break
        if ev[2] == 'regime':
            continue
        rows.append(dict(tick=ev[0], asset=ev[1], kind=ev[2].split(':')[0], text=ev[3], move=ev[4], sign=ev[5]))
    movers = []
    for a in ORDER:
        if t - HOUR < eng.start:
            break
        p, h = eng.price(a, t), eng.price(a, t - HOUR)
        ch = _change(p, h)
        big = 20 if ASSETS[a]['kind'] == 'coin' else 8 if ASSETS[a]['kind'] == 'stock' else 4
        if abs(ch) >= big:
            movers.append(dict(tick=t, asset=a, kind='mover', text=f'{ASSETS[a]["name"]} {"+" if ch > 0 else "−"}'
                               f'{abs(ch):.0f}% trong 1 giờ!'.replace('.', ','), move=round(ch), sign=1 if ch > 0 else -1))
    movers.sort(key=lambda r: -abs(r['move']))
    return (movers[:3] + rows)[:8]


def catalogue() -> list[dict]:
    """The public, static part of every asset (no parameters a player could trade on beyond the description)."""
    return [dict(id=a, kind=ASSETS[a]['kind'], sym=ASSETS[a]['sym'], name=ASSETS[a]['name'], emoji=ASSETS[a]['emoji'],
                 sector=SECTORS[ASSETS[a]['sector']]['name'], risky=ASSETS[a]['risky'], unlock=ASSETS[a]['unlock'],
                 fee=ASSETS[a]['fee'], desc=ASSETS[a]['desc'], unit=ASSETS[a]['unit'], legacy=ASSETS[a]['legacy'])
            for a in ORDER]


def warm(at: float | None = None) -> float:
    """Step the process's market up to now (server.py, before forking workers). Returns the seconds it took."""
    started = time.perf_counter()
    t = tick_of(at)
    if t >= WILD_TICK:
        engine(t)
    return time.perf_counter() - started
