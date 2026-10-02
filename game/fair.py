"""🏮 Hội chợ dân gian: a short folk fair in the neighbourhood (feedback #63, owner 02/10: "kiểu hội chợ ấy, mấy trò
này trò dân gian thôi nên cứ làm đi, mở ngắn hạn trong 5 ngày").

Played with the journey wallet's in-game xu only (never real money). Two kinds of stalls:

Chơi kiếm xu, no stake (owner 02/10: "vào đó có mấy trò dân gian như ô ăn quan, lô tô, bầu cua,... cho mọi người chơi
kiếm xu nhé"); each pays at most a few xu a Vietnam day (EARN_DAY):

* 🪨 Ô ăn quan against a neighbour (game/fair_oaq.py: the rules and the opponent): Bé Bi ("de") or Ông Hai ("kho").
  A win pays OAQ_PRIZE xu by level; a loss or a draw costs nothing.
* 💍 Ném vòng cổ chai (game/fair_ring.py): RINGS throws at five bottles, timing a swinging ring; RING_HIT xu a ring
  that lands (a bottle can take several), RING_ALL more when all five land; no daily cap since 03/10.

Thử vận may, small stakes:

* 🦀 Bầu cua tôm cá: six faces, three dice in a covered bowl; bet 1..BC_MAX xu in all on one or more faces. A face
  that shows k times pays the stake back plus 1:1 per die (standard rules); a "bão" (all three dice the face you bet)
  pays BAO:1 instead of 3:1. Since 03/10 a round is drawn to come out ahead for the bets with win_p (WIN_P, tapering
  above TAPER_FROM of today's luck net), any of those dice alike (bc_roll).
* 🎱 Gánh lô tô (owner 02/10: "loto thì có nhạc, có mc, có người biểu diễn, mn đặt cược loto được nhé"): tờ dò of 3
  rows of 5 numbers (1..90). The caller's numbers come from the minute the cards were bought (everyone who buys in the
  same minute hears the same calls), and so does the minute's vòng (mode_of: Kinh đôi, lật ngược, the evening's Hũ đêm
  hội); the neighbours play their own cards (drawn per round, so knowing a minute's calls tells nothing about who
  wins). Buy 1..LOTO_CARDS tờ of one LOTO_TIERS price. Since 03/10 (owner: "tỷ lệ thắng 53%") a round is drawn
  first: it goes the player's way with luck_p(…, 'lt', …) (WIN_P by today's net and the run of rounds), and loto_rs picks a round id whose
  cards fit (the player's best tờ fills the vòng's pattern at least one call before the first neighbour, or a
  neighbour fills it first); whoever fills the pattern first takes the hũ (a tie goes to the player), which is
  LOTO_PAY tenths of the player's tờ (LOTO_MODES' neighbours and cut now only set the scene and the rival cards).
  The player marks the called numbers by hand and hô "Kinh!": the server checks that every mark was called and that the
  marks fill the pattern; a Kinh hụt costs KINH_FINE xu (never above the wallet) and nothing else: the cards
  stay in the round, as many Kinh hụt as the player likes (owner 03/10: "kinh hụt thoải mái nhé"). Side bets, placed
  with the cards and settled at once (the result comes from the round's secret cards): chẵn/lẻ of the số chốt (the call that filled the first pattern on the
  mat) pays 1:1, but 7 and 70, cô Bảy's own numbers, lose both sides; the cột may mắn (the tờ dò column the số chốt is
  in) pays COT_PAY_HALF/2 times the stake back. With perfect play (scratch simulation of these functions, 20 000
  rounds of vé vừa 1 tờ, today's net under TAPER_FROM): Kinh in 52.7 % of the rounds, +16 % per xu staked (2 000
  rounds of each vòng × vé × tờ: +4..+25 %, the vé nhỏ 1 tờ lowest by rounding; Hũ đêm hội +18..+33 %; at WIN_P_LOW
  ≈ −3 %), like a one-face bầu cua bet (+21 %); the side bets ≈ −4 % per xu (chẵn/lẻ and cột together)
  (tests/test_fair.py LotoShow checks seeded samples. The older client's
  plain card is the thường vòng at LOTO_PRICE, paying LOTO_PRIZE.) A purchase's whole stake (tờ + side bets, at
  most 3 × 10 + 2 × 10 xu) must fit the wallet, the only limit (owner 03/10: "mỗi ngày chơi không giới hạn tiền",
  "không giới hạn lượt chơi"; _guard_free: no DAY_CAP, no ROUNDS_DAY). The day's tally (Bảng kinh hôm nay: rounds,
  Kinh, Kinh hụt, the neighbours' wins) is journey['fair']['ltd'].
* 🗡️ Phóng dao (game/fair_knife.py, owner 03/10, in the 🎯 phi tiêu's place: its tab 'dt' and its spot on the
  fairground): pay a stake (knife.STAKES), throw knives into a turning wooden board, level after level; after each
  level cleared "Dừng" pays knife.prize (the ladder) or "Chơi tiếp" risks it all on a harder level, sometimes a 🔥 x2
  one. The board's turning is drawn from a server seed, the client sends its throw times and the server judges them
  (fair_kn_*). No daily money or round limit, only the wallet (_guard_free); today's net makes the board harder
  (knife.heat). Save: journey['fair_kn'] (outside journey['fair'], whose older validator rejects unknown keys; an
  older server ignores it). The phi tiêu's 'dt' {n, w, b} in journey['fair'] stays as it was (read, never written);
  an older client's fair_dart is refused with a reload hint, and with no public `darts` it leaves the stall out.
* 🎟️ Vé số cào (game/fair_scratch.py, owner 03/10): buy a vé of one scratch.TIERS price; the server decides it at the
  purchase (luck_p(…, 'xs', …): wins ~42 %, ~1.03 xu back per xu, ~0.95 at the floor) and pays the prize at once; the
  player scratches the silver off by hand to see it. Nothing new in the save (the Sổ ví row counts the tickets).
* 🕯️ Chiếu trong (back corner): xóc đĩa chẵn lẻ (four coins, 1:1), bigger stakes XD_MIN..XD_MAX; the side picked
  is right with win_p, the coins any pattern of that parity alike (xd_toss). Each round
  has RAID_PCT % odds that Công an phường comes by: the stake is confiscated, a fine of stake // FINE_DIV (at least
  FINE_MIN, never more than the wallet holds) is paid, and the corner stays closed RAID_COOLDOWN seconds. The front
  stalls are never raided.

* 🍡 Hàng ăn vặt (game/fair_food.py, fair_snack, owner 03/10): the walkable fairground's two food carts sell kẹo bông,
  bắp nướng, nước mía… for a few xu; eating moves no bụng / tỉnh táo like the work day's Ăn thêm (game/needs.py).
  Not a game: no net, not on the Bảng vàng, nothing saved in journey['fair'].

Safety: the fair is open FAIR_DAYS days from FAIR_START (Vietnam dates; env MNL_FAIR_START=YYYY-MM-DD and
MNL_FAIR_DAYS override them at deploy), story saves only, no stake above what the wallet holds; since 03/10 no daily
money cap and no round limit (owner), a short pause between rounds (and a per-session rate limit in server.py). Dice, coins, cards and raids come from the OS random source
(server side; nothing the client sends decides a result). Request ids/revisions make every command idempotent
(game/storage.py).

🏆 Bảng vàng hội chợ (owner: "event hội chợ mà top thì nhận danh hiệu vua trò chơi nhé"; 03/10: "thay vì tính điểm,
tính tổng tiền mọi người thắng nhé… tiền thắng nhiều xếp top"): the xu won at the fair this edition, money_of: the luck
stalls' net (stats won − lost: stakes, payouts, Kinh hụt and raid fines) plus the skill stalls' xu (stats earned). Not
the 🎁 tiền vốn nor a vay nóng or its repayment (game/fair_cash.py). Only a player ahead (> 0) has a row on the
leaderboard table (board `board()`, game/leaderboard.py summary; ties: who reached the score first); the titles after
the end are game/fair_board.py. (Until 03/10 the board counted participation points, 'pts'/'dpts' in the save: kept
at what they were, an older server's validator requires them.)

Save: `journey['fair']` (optional, created by the first fair command; older saves load unchanged), a few numbers:
today's counters (chance net, rounds, xu earned per skill game; 'ltd', added on first use), the back corner's
cooldown, the current lô tô round {slot, rs, at, stage} plus, from the gánh lô tô on, {mode, tier, n, fk} and the
side bets {sb} (cards and calls are re-drawn from those; a round without them is the older plain card), the ô ăn quan game in progress {lv, g, at, stage},
the ném vòng round {rs, at, stage}, the days played this edition and the stats (lifetime, but won/lost/earned: this
edition's). Wallet moves go through one history row per game and life day
(kind 'fair'), updated in place, so a long evening at the fair does not push the rest of Sổ ví out.
"""
from __future__ import annotations

import datetime
import hashlib
import os
import random
import time

from . import fair_knife as knife
from . import fair_scratch as scratch
from . import fair_oaq as oaq
from . import fair_ring as ring
from . import fair_cash as fc   # 🎁 tiền vốn and 💸 vay nóng
from . import fair_food as ff   # 🍡 the food carts

VERSION = 1
FAIR_START = '2026-10-03'      # first day (Vietnam date), 00:00 UTC+7
FAIR_DAYS = 5
SHOW_BEFORE = 2 * 86400        # the entry shows "sắp mở" this long before the start
SHOW_AFTER = 3 * 86400         # and "đã tàn" this long after the end
VN = datetime.timezone(datetime.timedelta(hours=7))
KIND = 'fair'                  # journey wallet history kind (journey.HISTORY_KINDS)

# No daily money cap and no round limit (owner 03/10: "mỗi ngày chơi không giới hạn tiền", "không giới hạn lượt
# chơi"): the wallet is the only limit. DAY_CAP and ROUNDS_DAY are kept only as the bounds an older server's validator
# puts on the saved counters (rolling release), which therefore stop there.
DAY_CAP = 150
ROUNDS_DAY = 400
# The dice and coin stalls lean the player's way (owner 03/10: "tổng phải lời", "thắng 70% số ván", "người ta thắng
# khoảng 2000 xu thì cho thua dần bớt đi"): a round is a win with WIN_P (bầu cua: the bets come out ahead; xóc đĩa:
# the side picked is right), tapering linearly from TAPER_FROM xu of today's luck net to WIN_P_LOW at TAPER_TO and
# staying there. Payouts stay the folk ones (bầu cua per die, xóc đĩa 1:1).
WIN_P, WIN_P_LOW = .53, .45     # owner 03/10 01:45: "bầu cua, chiếu trong, gánh lô tô -> tỷ lệ thắng 53%" (was .60)
# One stall played on and on (owner 03/10: "chơi liên tục 1 game thì tỷ lệ thắng sẽ giảm dần xuống, tối thiểu 40%"):
# after RUN_FREE rounds in a row of the same stall (each within RUN_GAP s of the one before) the odds drop RUN_STEP a
# round, never below P_FLOOR. The run is journey['fair_run'] {g, n, at} (optional; outside journey['fair'], whose older
# validator rejects unknown keys).
RUN_FREE, RUN_STEP, RUN_GAP, P_FLOOR = 10, .01, 180, .40
RUN_GAMES = ('bc', 'xd', 'lt', 'dt')
# Stalls newer than 1.4.17, whose validator takes only RUN_GAMES in 'fair_run': their run is journey['fair_run2'], the
# same shape; there is one run at a time (a round of the other kind drops the other key), as if it were one key.
RUN_GAMES2 = ('xs',)
# Bầu cua runs cool faster and further (owner 03/10 02:00: "spam mãi cái đó thì giảm tỷ lệ thắng xuống… có thể thấp hơn
# 30%"), and the bowl opens BC_OPEN_MS after a roll ("mỗi lần bấm đợi 5s để mở"): rounds at least BC_GAP_MS apart.
RUN_RULES = dict(bc=(.02, .25), xs=(scratch.RUN_STEP, scratch.P_LO))  # game: (step a round past RUN_FREE, floor); others RUN_STEP, P_FLOOR
BC_OPEN_MS = 5000
BC_GAP_MS = 4800                 # BC_OPEN_MS less a little network slack
TAPER_FROM, TAPER_TO = 2000, 5000
GAP_MS = 400                   # between two rounds of dice/coins (owner 03/10: nhanh lên; was 1200)
# 🦀 Bầu cua
FACES = ('bau', 'cua', 'tom', 'ca', 'ga', 'nai')
FACE_NAMES = dict(bau='Bầu', cua='Cua', tom='Tôm', ca='Cá', ga='Gà', nai='Nai')
BC_OUTCOMES = [(x, y, z) for x in FACES for y in FACES for z in FACES]   # the 216 ways three dice land
BC_MAX = 20
BAO = 10                       # three dice on the face you bet: BAO:1 (standard rules: 3:1)
# 🕯️ Chiếu trong
XD_MIN, XD_MAX = 10, 50
SIDES = ('chan', 'le')
RAID_PCT = 2
FINE_MIN = 3
FINE_DIV = 4                   # a raid's fine: stake // FINE_DIV, at least FINE_MIN
RAID_COOLDOWN = 120
# 🎱 Lô tô
LOTO_PRICE = 5
LOTO_PRIZE = 11                # the older client's plain card: prize_of('thuong', LOTO_PRICE, 1) (was 23, a pot)
LOTO_NPCS = 4
# Owner 03/10: "gánh lô tô -> tỷ lệ thắng 53%": a round is drawn to go the player's way with luck_p (WIN_P, tapering
# like the other luck stalls), and a Kinh pays LOTO_PAY tenths of what the tờ cost, so that a player who always
# calls in time comes out a little ahead, like at bầu cua (the pot of everyone's tờ paid ~4.6× a single tờ).
LOTO_PAY = dict(thuong=22, nguoc=22, doi=22, dem=23)
LOTO_TRIES = 300               # round ids tried for the outcome drawn (≈2..8 needed); the last one tried after that
LOTO_TTL = 20 * 60             # a card can be claimed this long after it was bought
NEIGHBOURS = (('Bác Tư', '👴'), ('Bà Năm', '👵'), ('Chú Sáu', '🧔'), ('Cô Ba', '👩'), ('Anh Tèo', '🧑'), ('Chị Mận', '👧'))
STAGES = ('play', 'won', 'lost')
LOTO_TIERS = dict(nho=2, vua=5, lon=10)   # price of one tờ; 'vua' is the old plain card (LOTO_PRICE)
LOTO_CARDS = 3                 # tờ a round at most
# vòng: (full rows needed on one tờ, neighbours playing, the stall's cut of the pot in %)
LOTO_MODES = dict(thuong=(1, 4, 8), nguoc=(1, 4, 8), doi=(2, 4, 10), dem=(3, 6, 13))
MODE_NAMES = dict(thuong='Vòng thường', nguoc='Vòng lật ngược', doi='Vòng Kinh đôi', dem='Hũ đêm hội')
DEM_HOURS = (20, 21)           # Vietnam hours of the Hũ đêm hội: every round is one
KINH_FINE = 1                  # a Kinh hụt (the marks do not fill the pattern, or a mark was never called); no limit
FK_MAX = 10**6                 # Kinh hụt counted in a round / a day at most (the save's sane bound)
SIDE_STAKES = (2, 4, 6, 10)    # side bets (even, so the cột's 8.5× is whole xu)
BAY_NUMS = (7, 70)             # cô Bảy's own numbers: a số chốt on one of them loses both chẵn and lẻ
COT_PAY_HALF = 17              # cột may mắn: stake × 17 / 2 back
LOTO_OPT = ('mode', 'tier', 'n', 'sb', 'fk')   # newer round keys (absent in older saves: thuong, vua, 1 tờ)
LTD_KEYS = ('r', 'w', 'fk', 'npc')            # today's lô tô: rounds, Kinh won, Kinh hụt, the neighbours' wins
# 🪨 Ô ăn quan and 💍 Ném vòng: no stake, a little xu for playing well, capped a day per game
OAQ_PRIZE = dict(de=15, kho=30)
OAQ_PEOPLE = dict(de=('Bé Bi', '👦'), kho=('Ông Hai', '👴'))
OAQ_STAGES = ('play', 'won', 'lost', 'draw')
RING_HIT, RING_ALL = 3, 8      # xu per bottle ringed, and the bonus for all five
RING_DAY = 80                  # rounds a day at most
EARN_DAY = dict(oaq=90, ring=45)   # no cap any more (owner 03/10: kiếm không giới hạn); these bound the saved counters
EARN_UNCAPPED = ('oaq', 'ring')
EARN_GAMES = tuple(EARN_DAY)
# 🏆 Bảng vàng hội chợ: xu won (money_of); the points it counted until 03/10 are gone, POINTS_DAY only bounds the
# saved 'dpts' (older validators)
POINTS_DAY = 30
MONEY = ('won', 'lost', 'earned')   # the stats that make the board's score, reset with each edition

TITLE_ROWS = (   # journey.TITLES (secret, granted here only)
    ('f_oaq', '🪨', 'Cao tay ô ăn quan', 'Thắng Ông Hai một ván ô ăn quan ở hội chợ dân gian.'),
    ('f_ring', '💍', 'Tay ném vòng thần sầu', 'Ném trúng cả năm cổ chai trong một lượt ở hội chợ.'),
    ('f_loto', '🎱', 'Thần lô tô hội chợ', 'Hô “Kinh!” thắng một ván lô tô ở hội chợ dân gian.'),
    ('f_kinh2', '🎎', 'Kinh đôi rộn ràng', 'Thắng một vòng Kinh đôi ở gánh lô tô hội chợ.'),
    ('f_nguoc', '🙃', 'Đọc ngược như xuôi', 'Thắng một vòng lô tô lật ngược ở hội chợ.'),
    ('f_hu', '🏺', 'Ôm hũ đêm hội', 'Kinh cả tờ, ôm Hũ đêm hội ở gánh lô tô.'),
    ('f_bao', '🌪️', 'Trúng bão bầu cua', 'Ba con xúc xắc cùng ra đúng mặt bạn đặt ở hội chợ.'),
    ('f_dart', '🎯', 'Mắt thần phi tiêu', 'Phóng phi tiêu cắm ngay hồng tâm ở hội chợ dân gian.'),
    ('f_raid', '🚨', 'Bị công an hỏi thăm', 'Đang chơi ở chiếu trong thì công an phường tới kiểm tra.'),
    ('f_king', '👑', 'Vua trò chơi', 'Đứng đầu Bảng vàng hội chợ dân gian khi hội tàn.'),
    ('f_master', '🎪', 'Cao thủ hội chợ', 'Lọt top 10 Bảng vàng hội chợ dân gian khi hội tàn.'),
)
AWARDS = ('f_king', 'f_master')   # granted after the end by game/fair_board.py (through game/live_effects.py)
AWARD_NAMES = {tid: f'{emoji} {name}' for tid, emoji, name, _ in TITLE_ROWS if tid in AWARDS}
STATS = ('bc', 'xd', 'lt', 'lt_won', 'raids', 'bao', 'won', 'lost', 'oaq', 'oaq_won', 'ring', 'ring_hits', 'earned')
KEYS = ('v', 'date', 'net', 'rounds', 'last', 'raid_until', 'loto', 'stats', 'ed', 'pts', 'dpts', 'pdays', 'pday',
        'earn', 'oaq', 'ring')
KEYS_OPT = ('ltd', 'dt')       # newer keys, added on first use (older saves load without them)
DT_KEYS = ('n', 'w', 'b')      # 🎯 phi tiêu, lifetime: throws, hits, hồng tâm
LOTO_KEYS = ('slot', 'rs', 'at', 'stage')
OAQ_KEYS = ('lv', 'g', 'at', 'stage')
RING_KEYS = ('rs', 'at', 'stage')
EARN_KEYS = ('oaq', 'ring', 'ring_n')   # today: xu earned per game, ném vòng rounds
LABELS = dict(bc='🦀 Bầu cua hội chợ', xd='🕯️ Chiếu trong hội chợ', lt='🎱 Lô tô hội chợ', oaq='🪨 Ô ăn quan hội chợ',
              ring='💍 Ném vòng hội chợ', dt='🎯 Phi tiêu hội chợ', xs='🎟️ Vé số cào hội chợ', kn='🗡️ Phóng dao hội chợ')
UNITS = dict(bc='ván', xd='ván', lt='tờ', oaq='ván thắng', ring='lượt', dt='lượt', xs='vé', kn='lượt')
# 🗡️ Phóng dao: journey['fair_kn'] {n: runs, w: runs cashed out, b: the most levels cleared in a run, top: the biggest
# payout, run: the run going on or the last one}; a run {st: stake, lv: level, sd: the level's seed, hot: its heat,
# at: ms it started, sg: stage, bn: the 🔥 x2 levels' bonus xu, x2: this level is one, nx: the next one is, tp: throws
# the server has taken this level, day: the Vietnam date the level was cleared (the choice waits until that day ends,
# then the prize is paid by itself), pz: what "Dừng" paid}
KN_KEY = 'fair_kn'
KN_KEYS = ('n', 'w', 'b', 'top', 'run')
KN_RUN = ('st', 'lv', 'sd', 'hot', 'at', 'sg', 'bn', 'x2', 'nx', 'tp', 'day', 'pz')
KN_STAGES = ('play', 'choice', 'lost', 'done')   # a level being thrown, cleared (Dừng or Chơi tiếp), lost, cashed out
DART_GONE = 'Sạp phi tiêu đã đổi thành trò phóng dao. Tải lại trang để chơi nha.'

CLOSED = 'Hội chợ đã tàn, hẹn lần sau nha!'
SOON = 'Hội chợ chưa mở đâu, hẹn bạn ngày khai hội nha!'
ENOUGH = 'Hôm nay chơi vậy đủ rồi, mai ghé tiếp nha.'

_rng = random.SystemRandom()   # tests replace it with a seeded random.Random


def now() -> float:
    return time.time()


def titles(make) -> list:
    """journey.TITLES rows (make = journey._t): secret, never earned by a check, only granted by a fair round."""
    return [make(tid, 'secret', emoji, name, desc, lambda x: False, True) for tid, emoji, name, desc in TITLE_ROWS]


# ---------------------------------------------------------------- the calendar
def _start_date() -> datetime.date:
    raw = os.environ.get('MNL_FAIR_START', '').strip() or FAIR_START
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError:
        return datetime.date.fromisoformat(FAIR_START)


def _days() -> int:
    try:
        n = int(os.environ.get('MNL_FAIR_DAYS', '') or FAIR_DAYS)
    except ValueError:
        n = FAIR_DAYS
    return max(1, min(30, n))


def window() -> tuple[int, int]:
    """(opens, closes) as epoch seconds: FAIR_START 00:00 Vietnam time, FAIR_DAYS days later."""
    d = _start_date()
    t0 = datetime.datetime(d.year, d.month, d.day, tzinfo=VN).timestamp()
    return int(t0), int(t0) + _days() * 86400


def is_open(t: float | None = None) -> bool:
    t = now() if t is None else t
    a, b = window()
    return a <= t < b


def vn_date(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, VN).date().isoformat()


def edition() -> str:
    """This fair's id ('fair20261003'): the save's edition (its days, its money), its titles' settle mark."""
    return 'fair' + _start_date().strftime('%Y%m%d')


# ---------------------------------------------------------------- the save
def _earn0() -> dict:
    return {k: 0 for k in EARN_KEYS}


def initial() -> dict:
    return dict(v=VERSION, date='', net=0, rounds=0, last=0, raid_until=0, loto=None, stats={k: 0 for k in STATS},
                ed='', pts=0, dpts=0, pdays=0, pday='', earn=_earn0(), oaq=None, ring=None)


def _state(j: dict, t: float) -> dict:
    """journey['fair'] (created on first use), with today's counters reset on a new Vietnam day."""
    f = j.get('fair')
    if not isinstance(f, dict):
        f = j['fair'] = initial()
    today = vn_date(t)
    if f['date'] != today:
        f.update(date=today, net=0, rounds=0, dpts=0, earn=_earn0())
        f.pop('ltd', None)
    ed = edition()
    if f['ed'] != ed:   # a new fair: its own days and its own money
        f.update(ed=ed, pts=0, dpts=0, pdays=0)
        f['stats'].update({k: 0 for k in MONEY})
    return f


def _day(f: dict, t: float) -> None:
    """The first game of a Vietnam day (any stall, while open): a day played."""
    today = vn_date(t)
    if f['pday'] == today or not is_open(t):
        return
    f['pday'] = today
    f['pdays'] += 1


def money_of(j: dict) -> tuple[int, int]:
    """(xu won at the fair this edition, may be < 0; days played): the Bảng vàng score (game/leaderboard.py summary)."""
    f = j.get('fair') if type(j) is dict else None
    if type(f) is not dict or f.get('ed') != edition():
        return 0, 0
    st, days = f.get('stats'), f.get('pdays')
    st = st if type(st) is dict else {}
    won, lost, earned = (st.get(k) if type(st.get(k)) is int else 0 for k in MONEY)
    return won - lost + earned, (days if type(days) is int and days > 0 else 0)


def board() -> str:
    """The Bảng vàng's leaderboard board: 'fair20261003xu' (xu won). Not the edition itself, whose rows an older
    server filled with points (rolling release 03/10): they are simply not read, and go when that save is next written."""
    return edition() + 'xu'


def _today(f: dict | None, t: float) -> dict:
    """Read-only view of today's counters (public)."""
    if not f or f.get('date') != vn_date(t):
        return dict(net=0, rounds=0, earn=_earn0())
    return dict(net=f['net'], rounds=f['rounds'], earn=dict(f['earn']))


def budget(f: dict | None, t: float) -> int:
    """How much more may be lost today: no daily cap any more (the wallet is the limit)."""
    return 10 ** 9


def _pay(j: dict, f: dict, game: str, amount: int) -> None:
    """Move `amount` (signed) between the wallet and the fair: one Sổ ví row per game and life day, kept up to date
    (the row is looked for among the life day's last rows). Chance stalls count towards today's net (DAY_CAP); the
    skill stalls' xu are counted by _earn."""
    from . import journey as jr
    st = f['stats']
    if game in EARN_GAMES:
        st['earned'] += amount
    else:
        f['net'] += amount
        if amount > 0:
            st['won'] += amount
        else:
            st['lost'] -= amount
    last = None
    for row in reversed(j['history'][-12:]):
        if not isinstance(row, dict) or row.get('day') != j['life_day']:
            break
        if row.get('kind') == KIND and row.get('career') is None and str(row.get('label', '')).startswith(LABELS[game]):
            last = row
            break
    if game == 'xs':   # one _pay a ticket and no counter in the save: the row's own count, one more
        count = _row_count(last) + 1
    elif game == 'kn':   # the stake counts a run, its payout is the same run
        count = max(1, _row_count(last) + (amount < 0))
    else:
        count = f['dt']['n'] if game == 'dt' else st['oaq_won' if game == 'oaq' else game]
    label = f'{LABELS[game]} · {count} {UNITS[game]}'
    if last is not None and abs(last['amount'] + amount) <= 10**7:
        j['wallet'] += amount
        last['amount'] += amount
        last['label'] = label
        if j['wallet'] >= 0 and j['in_debt']:
            j['in_debt'] = False
            j['stats']['debt_repaid'] += 1
        j['stats']['max_wallet'] = max(j['stats']['max_wallet'], j['wallet'])
    else:
        jr._wallet(j, amount, KIND, label)


def _row_count(row: dict | None) -> int:
    """The count at the end of a Sổ ví row's label ("… · 12 vé"), 0 when there is none."""
    tail = str((row or {}).get('label', '')).rsplit(' · ', 1)[-1].split(' ')[0]
    return min(10**6, int(tail)) if tail.isdigit() else 0


def _earn(j: dict, f: dict, game: str, amount: int) -> int:
    """Pay a skill stall's reward, up to what is left of today's EARN_DAY for that game (ô ăn quan; ném vòng has no
    cap since 03/10, its counter stops at the older bound); returns what was paid."""
    if game in EARN_UNCAPPED:
        paid = max(0, amount)
        f['earn'][game] = min(EARN_DAY[game], f['earn'][game] + paid)
    else:
        paid = max(0, min(amount, EARN_DAY[game] - f['earn'][game]))
        f['earn'][game] += paid
    if paid:
        _pay(j, f, game, paid)
    return paid


def _grant(j: dict, tid: str, got: list) -> None:
    from . import journey as jr
    if tid in j['titles']:
        return
    j['titles'][tid] = j['life_day']
    jr._news(j, 'titles', 'titles', [tid])
    got.append(tid)


# ---------------------------------------------------------------- lô tô cards and calls
def _range(col: int) -> range:
    return range(1, 10) if col == 0 else range(col * 10, 91 if col == 8 else col * 10 + 10)


def card(rng: random.Random) -> list[list[int]]:
    """A tờ dò: 3 rows of 5 numbers, column c holds c*10..c*10+9 (1..9 first, 80..90 last), sorted down a column."""
    rows = [sorted(rng.sample(range(9), 5)) for _ in range(3)]
    picks = {c: iter(sorted(rng.sample(_range(c), sum(c in r for r in rows)))) for c in range(9)}
    return [[next(picks[c]) for c in r] for r in rows]


def calls(slot: int) -> list[int]:
    """The 90 calls of a minute: the same for everyone who bought a card in that minute."""
    seq = list(range(1, 91))
    random.Random(int(hashlib.sha256(f'fair-loto|{slot}'.encode()).hexdigest()[:12], 16)).shuffle(seq)
    return seq


def done_at(rows: list[list[int]], pos: dict, need: int = 1) -> int:
    """How many calls until the card has `need` full rows (1: a row, 2: Kinh đôi, 3: the whole card)."""
    return sorted(max(pos[n] for n in r) for r in rows)[need - 1] + 1


def mode_of(slot: int) -> str:
    """The vòng of a minute, the same for everyone: the Hũ đêm hội in the evening (DEM_HOURS, Vietnam time), else
    a Kinh đôi or a lật ngược one minute in four each, a thường one the other half."""
    if datetime.datetime.fromtimestamp(slot * 60, VN).hour in DEM_HOURS:
        return 'dem'
    k = int(hashlib.sha256(f'fair-mode|{slot}'.encode()).hexdigest()[:8], 16) % 8
    return 'doi' if k < 2 else 'nguoc' if k < 4 else 'thuong'


def prize_of(mode: str, price: int, n: int) -> int:
    """What a Kinh takes: LOTO_PAY tenths of the n tờ's price (rounded)."""
    return (n * price * LOTO_PAY[mode] + 5) // 10


def loto_rs(lt: dict, want: bool) -> int:
    """A round id (rs) for a new round `lt` whose cards go the player's way (want: their best tờ fills the vòng's
    pattern at least one call before the first neighbour, so a player who keeps up has time to hô) or a neighbour's
    (one fills it first): any such round alike, like bc_roll. The cards, the calls and the side bets' số chốt are then
    drawn from it exactly as before, so a round still replays from {slot, rs} on any server."""
    rs = 0
    for _ in range(LOTO_TRIES):
        rs = _rng.getrandbits(31)
        rv = round_view(dict(lt, rs=rs))
        if (rv['mine'] < rv['npc_done']) if want else (rv['npc_done'] < rv['mine']):
            break
    return rs


def _lt(lt: dict) -> tuple[str, str, int]:
    """(mode, tier, tờ) of a round; older rounds: one plain card."""
    return lt.get('mode', 'thuong'), lt.get('tier', 'vua'), lt.get('n', 1)


def round_view(lt: dict) -> dict:
    """Everything a round is drawn from: the player's cards, the neighbours' cards, the calls, who fills the vòng's
    pattern first (npc_done: the neighbours' first; mine: the player's best card; chot: the mat's first, its call is
    the số chốt of the side bets)."""
    mode, tier, n = _lt(lt)
    need, npc_n, _ = LOTO_MODES[mode]
    seq = calls(lt['slot'])
    pos = {x: i for i, x in enumerate(seq)}
    cards = [card(random.Random(f'fair-me|{lt["rs"]}' + (f'|{i}' if i else ''))) for i in range(n)]
    who = random.Random(f'fair-who|{lt["rs"]}').sample(range(len(NEIGHBOURS)), npc_n)
    npcs = []
    for i, k in enumerate(who):
        rows = card(random.Random(f'fair-npc|{lt["rs"]}|{i}'))
        npcs.append(dict(k=k, name=NEIGHBOURS[k][0], emoji=NEIGHBOURS[k][1], rows=rows, done=done_at(rows, pos, need)))
    first = min(npcs, key=lambda x: x['done'])
    mine = min(done_at(c, pos, need) for c in cards)
    chot = min(mine, first['done'])
    return dict(seq=seq, card=cards[0], cards=cards, npcs=npcs, npc_done=first['done'], npc_name=first['name'],
                npc_k=first['k'], mine=mine, mode=mode, need=need, price=LOTO_TIERS[tier], tier=tier, n=n,
                prize=prize_of(mode, LOTO_TIERS[tier], n), chot=chot, chot_n=seq[chot - 1])


def side_back(sb: dict | None, x: int) -> dict:
    """What the side bets pay back (stake included) when the số chốt is x: {'cl': xu, 'cot': xu}."""
    out = {}
    for k, (pick, stake) in (sb or {}).items():
        if k == 'cl':
            out[k] = 2 * stake if x not in BAY_NUMS and ('chan' if x % 2 == 0 else 'le') == pick else 0
        else:
            out[k] = stake * COT_PAY_HALF // 2 if (0 if x < 10 else min(8, x // 10)) == pick else 0
    return out


def odds(net: int, hi: float | None = None, lo: float | None = None) -> float:
    """How likely a luck round (bầu cua, xóc đĩa, phi tiêu) goes the player's way given today's luck net: WIN_P up to
    TAPER_FROM, then straight down to WIN_P_LOW at TAPER_TO, and WIN_P_LOW from there on."""
    hi = WIN_P if hi is None else hi
    lo = WIN_P_LOW if lo is None else lo
    if net <= TAPER_FROM:
        return hi
    return max(lo, hi - (hi - lo) * (net - TAPER_FROM) / (TAPER_TO - TAPER_FROM))


def _run(j: dict, game: str, t: float) -> int:
    """Count this round in the player's run of `game`; returns its length (1 for a new run)."""
    key, other = ('fair_run2', 'fair_run') if game in RUN_GAMES2 else ('fair_run', 'fair_run2')
    j.pop(other, None)   # another kind of stall: that run is over
    r = j.get(key)
    if not (isinstance(r, dict) and r.get('g') == game and 0 <= int(t) - r.get('at', 0) <= RUN_GAP):
        r = j[key] = dict(g=game, n=0, at=int(t))
    r['n'] = min(10**6, r['n'] + 1)
    r['at'] = int(t)
    return r['n']


def luck_p(j: dict, f: dict | None, game: str, t: float, hi: float | None = None, lo: float | None = None) -> float:
    """The odds of the next round of a luck stall: odds() by today's net, less RUN_STEP a round past RUN_FREE in a row
    of the same stall, never below P_FLOOR. Counts the round in the run."""
    n = _run(j, game, t)
    step, floor = RUN_RULES.get(game, (RUN_STEP, P_FLOOR))
    return max(floor, odds(_today(f, t)['net'], hi, lo) - step * max(0, n - RUN_FREE))


def win_p(f: dict | None, t: float) -> float:
    """odds() for the next luck round of this fair state (today's net; 0 on a new day)."""
    return odds(_today(f, t)['net'])


def bc_back(bets: dict, dice: list) -> int:
    """What a bầu cua round pays back (stakes included): 1:1 a die on the face, BAO:1 for all three."""
    back = 0
    for face, b in bets.items():
        k = dice.count(face)
        back += b * (1 + BAO) if k == 3 else b * (1 + k) if k else 0
    return back


def bc_roll(bets: dict, want: bool) -> list:
    """Three dice for a round that comes out ahead for the bets (want) or not: any of those outcomes alike."""
    stake = sum(bets.values())
    dice = [_rng.choice(FACES) for _ in range(3)]
    if (bc_back(bets, dice) > stake) != want:
        pool = [d for d in BC_OUTCOMES if (bc_back(bets, d) > stake) == want]
        dice = list(_rng.choice(pool)) if pool else dice
    return dice


def xd_toss(side: str, want: bool) -> list:
    """Four coins that make `side` right (want) or wrong: any of the 8 patterns of that parity alike."""
    coins = [_rng.randrange(2) for _ in range(4)]
    if ((side == 'chan') == (sum(coins) % 2 == 0)) != want:
        coins[_rng.randrange(4)] ^= 1   # one coin turned (a uniform wrong pattern and coin give a uniform right one)
    return coins


def xd_fine(stake: int) -> int:
    return max(FINE_MIN, stake // FINE_DIV)


def _ltd(f: dict) -> dict:
    """Today's lô tô counters (the Bảng kinh hôm nay), created on first use."""
    return f.setdefault('ltd', dict(r=0, w=0, fk=0, npc=[0] * len(NEIGHBOURS)))


def _loto_lost(f: dict, lt: dict) -> None:
    """A round ends without the player's Kinh: the neighbour who filled the pattern first takes the day's tally."""
    lt['stage'] = 'lost'
    _ltd(f)['npc'][round_view(lt)['npc_k']] += 1


# ---------------------------------------------------------------- commands
COMMANDS = ('fair_bc', 'fair_xd', 'fair_loto_buy', 'fair_loto_kinh', 'fair_loto_fold',
            'fair_oaq_start', 'fair_oaq_move', 'fair_oaq_quit', 'fair_ring_start', 'fair_ring_throw', 'fair_dart', 'fair_xs',
            'fair_kn_start', 'fair_kn_throw', 'fair_kn_next', 'fair_kn_stop')
LATE = ('fair_loto_kinh', 'fair_loto_fold', 'fair_oaq_move', 'fair_oaq_quit', 'fair_ring_throw',   # may finish after the close
        'fair_kn_throw', 'fair_kn_stop')


def oaq_view(o: dict | None) -> dict | None:
    """The ô ăn quan game for the client: the board, the scores, who plays."""
    if not o:
        return None
    g = o['g']
    name, emoji = OAQ_PEOPLE[o['lv']]
    return dict(lv=o['lv'], stage=o['stage'], b=g['b'][:], q=g['q'][:], cap=g['cap'][:], ply=g['ply'],
                me=oaq.score(g, 0), opp=oaq.score(g, 1), name=name, emoji=emoji, prize=OAQ_PRIZE[o['lv']])


def ring_view(r: dict | None, t: float) -> dict | None:
    if not r or r['stage'] != 'play' or int(t * 1000) - r['at'] > ring.TTL:
        return None
    return dict(id=r['rs'], **ring.params(r['rs']))


def _oaq_end(j: dict, f: dict, o: dict, t: float, got: list) -> dict:
    """The game is over: who won, the reward."""
    g = o['g']
    me, opp = oaq.score(g, 0), oaq.score(g, 1)
    o['stage'] = 'won' if me > opp else 'lost' if me < opp else 'draw'
    out = dict(stage=o['stage'], me=me, opp=opp, prize=0)
    if o['stage'] == 'won':
        f['stats']['oaq_won'] += 1
        out['prize'] = _earn(j, f, 'oaq', OAQ_PRIZE[o['lv']])
        out['capped'] = out['prize'] < OAQ_PRIZE[o['lv']]
        if o['lv'] == 'kho':
            _grant(j, 'f_oaq', got)
    return out


def _guard_free(e, f: dict, j: dict, t: float, stake: int) -> None:
    """A new round of a stall with no daily money or round limit (owner 03/10: the lô tô, the phi tiêu): open, paid
    from the wallet (no loans), not too fast. Counts the day played."""
    need = e.need
    need(j['wallet'] >= stake, 'Ví không đủ xu cho ván này. Hội chợ không cho vay để chơi đâu nha.', 'fair_wallet')
    need(abs(f['net']) + stake < 10**6, ENOUGH, 'fair_enough')   # the save's bound on today's net
    ms = int(t * 1000)
    need(ms - f['last'] >= GAP_MS or f['last'] > ms, 'Từ từ thôi, xúc xắc chưa kịp lăn!', 'fair_slow')
    f['last'] = ms
    _day(f, t)


# ---------------------------------------------------------------- 🗡️ phóng dao
def _kn(j: dict) -> dict:
    """journey['fair_kn'], created on first use."""
    k = j.get(KN_KEY)
    if not isinstance(k, dict):
        k = j[KN_KEY] = dict(n=0, w=0, b=0, top=0, run=None)
    return k


def _kn_sched(run: dict) -> dict:
    return knife.schedule(run['sd'], run['lv'], run['hot'])


def _kn_cleared(run: dict) -> int:
    return run['lv'] if run['sg'] in ('choice', 'done') else run['lv'] - 1


def _kn_late(run: dict, t: float) -> bool:
    """A level not finished in time (LEVEL_MS, plus SLACK for the network) is lost, like a knife on a knife (else a
    client could hold back a losing throw and keep the prize of the levels before)."""
    return run['sg'] == 'play' and int(t * 1000) - run['at'] > knife.LEVEL_MS + knife.SLACK


def _kn_level(f: dict, run: dict, t: float) -> None:
    """A new level of the run: its own seed (drawn now, so nothing of it is known before), the heat of today's net."""
    run.update(sd=_rng.getrandbits(31), hot=knife.heat(_today(f, t)['net']), at=int(t * 1000), sg='play', tp=[], day='')


def _kn_pay(j: dict, f: dict, run: dict) -> int:
    """Dừng: the prize of the levels cleared into the wallet; the run is done."""
    k = _kn(j)
    pz = knife.prize(run['st'], _kn_cleared(run), run['bn'])
    run.update(sg='done', pz=pz)
    if pz:
        _pay(j, f, 'kn', pz)
    k['w'] = min(10**9, k['w'] + 1)
    k['top'] = max(k['top'], pz)
    return pz


def _kn_view_run(run: dict | None, t: float) -> dict | None:
    """The run for the client: the level being thrown (its board), the choice, or how the last run ended."""
    if not run:
        return None
    sg = 'lost' if _kn_late(run, t) else run['sg']
    st, lv, bn = run['st'], run['lv'], run['bn']
    out = dict(stake=st, lv=lv, stage=sg, x2=bool(run['x2']), prize=knife.prize(st, _kn_cleared(dict(run, sg=sg)), bn))
    if sg == 'play':
        ms = int(t * 1000)
        out.update(board=knife.public_schedule(_kn_sched(run)), id=f'{run["sd"]}-{lv}', el=ms - run['at'],
                   tp=list(run['tp']), win=knife.prize(st, lv, bn + (knife.x2_bonus(st, lv) if run['x2'] else 0)))
    elif sg == 'choice':
        nxt = lv + 1
        out.update(nx=bool(run['nx']), late=run['day'] != vn_date(t),
                   win=knife.prize(st, nxt, bn + (knife.x2_bonus(st, nxt) if run['nx'] else 0)))
    elif sg == 'done':
        out.update(paid=run['pz'])
    else:   # lost: the prize that was riding on the level went with it
        out.update(prize=0, gone=out['prize'])
    return out


def _knife(e, j: dict, f: dict, name: str, p: dict, t: float) -> dict:
    """🗡️ fair_kn_start {stake}, fair_kn_throw {lv, taps}, fair_kn_next {}, fair_kn_stop {} (game/fair_knife.py)."""
    need = e.need
    bad = 'Dữ liệu thao tác không hợp lệ.'
    k = _kn(j)
    run = k['run']
    ms = int(t * 1000)
    late = bool(run) and _kn_late(run, t)
    if late:
        run['sg'] = 'lost'
    if name == 'fair_kn_start':
        stake = p.get('stake')
        need(set(p) == {'stake'} and type(stake) is int and stake in knife.STAKES,
             f'Phóng dao đặt {", ".join(map(str, knife.STAKES))} xu thôi nha.')
        need(not run or run['sg'] in ('lost', 'done'),
             'Lượt trước còn chờ: chơi tiếp hoặc dừng nhận thưởng đã nha.' if run and run['sg'] == 'choice'
             else 'Màn này đang chơi dở, phóng tiếp nha.', 'fair_kn_busy')
        _guard_free(e, f, j, t, stake)
        run = k['run'] = dict(st=stake, lv=1, sd=0, hot=0, at=0, sg='play', bn=0, x2=0, nx=0, tp=[], day='', pz=0)
        _kn_level(f, run, t)
        k['n'] = min(10**9, k['n'] + 1)
        _pay(j, f, 'kn', -stake)
        return dict(fair=dict(game='kn', started=True, run=_kn_view_run(run, t)), message='')
    if name == 'fair_kn_throw':
        lv, taps = p.get('lv'), p.get('taps')
        need(set(p) == {'lv', 'taps'} and type(lv) is int, bad)
        need(run and run['lv'] == lv and run['sg'] in ('play', 'lost'), 'Màn này đã xong rồi.', 'fair_kn_over')
        need(run['sg'] == 'play' or late, 'Màn này đã xong rồi.', 'fair_kn_over')   # lost already (another tab)
        if late:
            return dict(fair=dict(game='kn', lv=lv, lost=True, late=True, run=_kn_view_run(run, t)),
                        message='Lâu quá bia ngừng quay rồi, lượt này thua. Phóng lượt mới nha.')
        sc = _kn_sched(run)
        need(knife.taps_ok(taps, sc['need'], ms - run['at']) and taps[:len(run['tp'])] == run['tp'], bad, 'fair_kn_bad')
        stuck, hit = knife.judge(sc, taps)
        out = dict(game='kn', lv=lv, stuck=stuck, hit=hit)
        if hit >= 0:
            run['sg'] = 'lost'
            out.update(lost=True, run=_kn_view_run(run, t))
            return dict(fair=out, message='Dao chạm dao rồi! Lượt này thua hết.')
        if len(stuck) < sc['need']:   # not done yet: the server keeps the throws it has judged
            run['tp'] = list(taps)
            out.update(run=_kn_view_run(run, t))
            return dict(fair=out, message='')
        if run['x2']:
            run['bn'] += knife.x2_bonus(run['st'], lv)
        k['b'] = max(k['b'], lv)
        run.update(sg='choice', tp=[], day=vn_date(t), nx=0)
        if lv >= knife.LEVELS:   # the last level: nothing more to risk, the prize is paid
            pz = _kn_pay(j, f, run)
            out.update(cleared=True, all=True, paid=pz, run=_kn_view_run(run, t))
            return dict(fair=out, message=f'Phá đảo cả {knife.LEVELS} màn! +{pz} xu.')
        run['nx'] = int(not run['x2'] and _rng.random() < knife.X2_P)   # never two x2 levels in a row
        out.update(cleared=True, run=_kn_view_run(run, t))
        return dict(fair=out, message='')
    need(not p, bad)
    if name == 'fair_kn_next':
        need(run and run['sg'] == 'choice', 'Không có màn nào đang chờ chơi tiếp.', 'fair_kn_over')
        run.update(lv=run['lv'] + 1, x2=run['nx'], nx=0)
        _kn_level(f, run, t)
        _day(f, t)
        return dict(fair=dict(game='kn', next=True, run=_kn_view_run(run, t)), message='')
    need(run and run['sg'] in ('choice', 'done'), 'Không có thưởng nào đang chờ.', 'fair_kn_over')   # fair_kn_stop
    if run['sg'] == 'done':   # already paid (the day ended, or another tab)
        return dict(fair=dict(game='kn', stopped=True, prize=run['pz'], again=True, run=_kn_view_run(run, t)),
                    message='Thưởng lượt này đã vô ví rồi.')
    pz = _kn_pay(j, f, run)
    return dict(fair=dict(game='kn', stopped=True, prize=pz, run=_kn_view_run(run, t)), message=f'Nhận thưởng {pz} xu!')


def _kn_settle(s: dict) -> None:
    """Before every command: a choice left from an earlier Vietnam day (neither "Dừng" nor "Chơi tiếp" tapped) is paid
    as if "Dừng": the prize was won, it does not wait past the day (nor past the fair)."""
    j = s.get('journey')
    k = j.get(KN_KEY) if isinstance(j, dict) else None
    run = k.get('run') if isinstance(k, dict) else None
    if not isinstance(run, dict) or run.get('sg') != 'choice' or not j.get('story'):
        return
    t = now()
    if run['day'] != vn_date(t):
        _kn_pay(j, _state(j, t), run)


def _scratch(e, j: dict, f: dict, p: dict, t: float) -> dict:
    """🎟️ One vé số cào: the price from the wallet, the ticket decided from _rng and today's net and paid at once
    (game/fair_scratch.py); the client scratches the silver off to see it, so the message says nothing of the result."""
    need = e.need
    price = p.get('price')
    need(set(p) == {'price'} and type(price) is int and price in scratch.TIERS,
         f'Vé số cào có giá {", ".join(map(str, scratch.TIERS))} xu thôi nha.')
    _guard_free(e, f, j, t, price)
    win = _rng.random() < luck_p(j, f, 'xs', t, scratch.P_HI, scratch.P_LO)
    mult = scratch.prize_mult(_rng) if win else 0
    cells = scratch.layout(price, mult, _rng)
    prize = mult * price
    _pay(j, f, 'xs', prize - price)
    out = dict(game='xs', id=_rng.getrandbits(31), price=price, name=scratch.NAMES[price], cells=cells, prize=prize,
               mult=mult, net=prize - price, hits=[i for i, v in enumerate(cells) if prize and v == prize])
    return dict(fair=out, message='')


def _guard_round(e, f: dict, j: dict, t: float, stake: int, worst: int) -> None:
    """A new round: open, paid from the wallet (no loans), not too fast. Counts the day played."""
    need = e.need
    need(j['wallet'] >= stake, 'Ví không đủ xu cho ván này. Hội chợ không cho vay để chơi đâu nha.', 'fair_wallet')
    ms = int(t * 1000)
    need(ms - f['last'] >= GAP_MS or f['last'] > ms, 'Từ từ thôi, xúc xắc chưa kịp lăn!', 'fair_slow')
    f['last'] = ms
    f['rounds'] = min(ROUNDS_DAY, f['rounds'] + 1)   # a counter only (no limit); bounded for older validators
    _day(f, t)


def apply(s: dict, name: str, p: dict) -> dict:
    """`fair_*` commands. Checks everything before changing anything (the engine works on a copy anyway)."""
    from . import engine as e
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS or name in fc.COMMANDS or name in ff.COMMANDS, 'Thao tác hội chợ không hợp lệ.', 'unknown_action')
    need(j.get('story'), 'Hội chợ chỉ có trong hành trình.', 'not_story')
    t = now()
    opens, closes = window()
    if name in fc.COMMANDS:
        return fc.apply(s, name, p, t, edition(), opens <= t < closes)
    if name in ff.COMMANDS:   # 🍡 a snack from the food carts: only while the fair is open
        need(t >= opens, SOON, 'fair_closed')
        need(t < closes, CLOSED, 'fair_closed')
        return ff.apply(s, p)
    if name not in LATE:   # a card, a game or a round begun while open can still be finished
        need(t >= opens, SOON, 'fair_closed')
        need(t < closes, CLOSED, 'fair_closed')
    f = _state(j, t)
    st = f['stats']
    got: list = []
    result = dict(message='', effects=[])
    if name == 'fair_bc':
        bets = p.get('bets')
        need(set(p) == {'bets'} and isinstance(bets, dict) and bets and set(bets) <= set(FACES), 'Chọn mặt để đặt nha.')
        for v in bets.values():
            need(type(v) is int and 1 <= v <= BC_MAX, f'Mỗi ván đặt tối đa {BC_MAX} xu.')
        stake = sum(bets.values())
        need(stake <= BC_MAX, f'Mỗi ván đặt tối đa {BC_MAX} xu.')
        need(f is None or int(t * 1000) - f['last'] >= BC_GAP_MS or f['last'] > int(t * 1000),
             'Chờ chú Tám mở bát đã nha!', 'fair_slow')
        want = _rng.random() < luck_p(j, f, 'bc', t)
        _guard_round(e, f, j, t, stake, stake)
        dice = bc_roll(bets, want)
        back = bc_back(bets, dice)
        bao = next((face for face in bets if dice.count(face) == 3), None)
        st['bc'] += 1
        delta = back - stake
        _pay(j, f, 'bc', delta)
        if bao:
            st['bao'] += 1
            _grant(j, 'f_bao', got)
        result['fair'] = dict(game='bc', dice=dice, bets=dict(bets), stake=stake, back=back, net=delta, bao=bao)
        result['message'] = (f'Bão {FACE_NAMES[bao].lower()}! +{delta} xu.' if bao else
                             f'Thắng {delta} xu.' if delta > 0 else 'Hòa vốn.' if delta == 0 else f'Thua {-delta} xu.')
    elif name == 'fair_xd':
        need(set(p) == {'side', 'stake'} and p.get('side') in SIDES, 'Chọn chẵn hay lẻ nha.')
        stake = p['stake']
        need(type(stake) is int and XD_MIN <= stake <= XD_MAX, f'Chiếu trong đặt từ {XD_MIN} đến {XD_MAX} xu.')
        wait = f['raid_until'] - int(t)
        need(wait <= 0, f'Chiếu trong vừa bị dẹp, {max(1, -(-wait // 60))} phút nữa mới bày lại. Ra trước chơi bầu cua, lô tô cho lành nha.',
             'fair_raided')
        fine = xd_fine(stake)
        want = None
        _guard_round(e, f, j, t, stake, stake + fine)
        st['xd'] += 1
        if _rng.random() * 100 < RAID_PCT:
            fine = min(fine, j['wallet'] - stake)
            st['raids'] += 1
            f['raid_until'] = int(t) + RAID_COOLDOWN
            _pay(j, f, 'xd', -(stake + fine))
            _grant(j, 'f_raid', got)
            result['fair'] = dict(game='xd', raid=True, side=p['side'], stake=stake, fine=fine, net=-(stake + fine), cooldown=RAID_COOLDOWN)
            result['message'] = f'Công an phường kiểm tra! Mất {stake} xu tiền cược và nộp phạt {fine} xu.'
        else:
            want = _rng.random() < luck_p(j, f, 'xd', t)
            coins = xd_toss(p['side'], want)
            even = sum(coins) % 2 == 0
            win = (p['side'] == 'chan') == even
            delta = stake if win else -stake
            _pay(j, f, 'xd', delta)
            result['fair'] = dict(game='xd', raid=False, side=p['side'], stake=stake, coins=coins, even=even, net=delta)
            result['message'] = f'{"Chẵn" if even else "Lẻ"}! ' + (f'Thắng {stake} xu.' if win else f'Thua {stake} xu.')
    elif name == 'fair_loto_buy':
        slot = int(t // 60)
        if p:   # the newer client: a tier, 1..LOTO_CARDS tờ, side bets, the vòng it showed; the older one sends {}
            need(set(p) <= {'tier', 'n', 'mode', 'cl', 'cot'} and isinstance(p.get('tier'), str) and p['tier'] in LOTO_TIERS
                 and type(p.get('n')) is int
                 and 1 <= p['n'] <= LOTO_CARDS, 'Chọn loại vé và số tờ nha.')
            mode = mode_of(slot)
            need(p.get('mode', mode) == mode, f'Vòng vừa đổi sang {MODE_NAMES[mode]}, coi lại rồi mua nha.', 'fair_loto_mode')
            sb = {}
            for k, picks in (('cl', ('chan', 'le')), ('cot', range(9))):
                if p.get(k) is None:
                    continue
                bet = p[k]
                need(isinstance(bet, list) and len(bet) == 2 and type(bet[1]) is int and bet[1] in SIDE_STAKES
                     and (bet[0] in picks if k == 'cl' else type(bet[0]) is int and bet[0] in picks),
                     f'Cược phụ đặt {", ".join(map(str, SIDE_STAKES))} xu thôi nha.')
                sb[k] = [bet[0], bet[1]]
            tier, n = p['tier'], p['n']
        else:
            mode, tier, n, sb = 'thuong', 'vua', 1, {}
        cost = n * LOTO_TIERS[tier]
        stake = cost + sum(b[1] for b in sb.values())
        _guard_free(e, f, j, t, stake)   # no daily money or round limit (owner 03/10)
        want = _rng.random() < luck_p(j, f, 'lt', t)   # one count in the run a purchase
        lt = f['loto']
        if lt and lt['stage'] == 'play':
            _loto_lost(f, lt)   # a new card folds the old one
        lt = dict(slot=slot, rs=0, at=int(t), stage='play')
        if p:
            lt.update(mode=mode, tier=tier, n=n, fk=0)
            if sb:
                lt['sb'] = sb
        lt['rs'] = loto_rs(lt, want)
        f['loto'] = lt
        st['lt'] += 1
        _ltd(f)['r'] += 1
        _pay(j, f, 'lt', -cost)
        if sb:   # settled now from the round's secret cards; the client shows it when the round ends
            back = side_back(sb, round_view(lt)['chot_n'])
            _pay(j, f, 'lt', sum(back.values()) - (stake - cost))
        result['fair'] = dict(game='lt', bought=True, mode=mode, n=n, cost=stake)
        result['message'] = (f'Đã mua {n} tờ dò, {stake} xu. Dò kỹ nha!' if p else f'Đã mua tờ dò {LOTO_PRICE} xu. Dò kỹ nha!')
    elif name == 'fair_loto_kinh':
        lt = f['loto']
        need(set(p) == {'row', 'at'} or set(p) == {'card', 'at', 'marks'}, 'Dữ liệu thao tác không hợp lệ.')
        marks = p.get('marks')
        need('marks' not in p or isinstance(marks, list), 'Dữ liệu thao tác không hợp lệ.')
        need(lt and lt['stage'] == 'play', 'Ván lô tô này đã xong rồi.', 'fair_loto_over')
        at = p['at']
        need(type(at) is int and 1 <= at <= 90, 'Dữ liệu thao tác không hợp lệ.')
        rv = round_view(lt)
        if marks is None:   # the older client: a row of the first card, sent only once it is full
            row = p['row']
            need(type(row) is int and 0 <= row <= 2 and at >= 5, 'Dữ liệu thao tác không hợp lệ.')
            need(rv['need'] == 1, 'Vòng này cần đủ nhiều hàng hơn, tải lại trang để chơi tiếp nha.', 'fair_loto_short')
        else:
            ci = p['card']
            need(type(ci) is int and 0 <= ci < rv['n'] and len(marks) <= 15
                 and all(type(x) is int for x in marks) and len(set(marks)) == len(marks)
                 and set(marks) <= {x for r in rv['cards'][ci] for x in r}, 'Dữ liệu thao tác không hợp lệ.')
        if t - lt['at'] > LOTO_TTL:
            _loto_lost(f, lt)
            result['fair'] = dict(game='lt', won=False, late=True)
            result['message'] = 'Ván này tàn lâu rồi, mua tờ mới nha.'
        elif marks is None and not set(rv['card'][row]) <= set(rv['seq'][:at]):
            need(False, 'Hàng này chưa đủ số đâu, dò lại nha!', 'fair_loto_short')
        elif marks is not None and not (set(marks) <= set(rv['seq'][:at])
                                        and sum(set(r) <= set(marks) for r in rv['cards'][ci]) >= rv['need']):
            # Kinh hụt: a mark that was never called, or the marks do not fill the vòng's pattern
            # the cards stay in the round however many times (owner: "k giới hạn kinh hụt"); a tiny fine, wallet allowing
            lt['fk'] = min(3, lt.get('fk', 0) + 1)   # a counter only now; kept ≤ 3 so a 1.4.12 server (rolling release) still accepts the save
            ltd = _ltd(f)
            ltd['fk'] = min(FK_MAX, ltd['fk'] + 1)
            fine = max(0, min(KINH_FINE, j['wallet']))
            if fine > 0:
                _pay(j, f, 'lt', -fine)
            result['fair'] = dict(game='lt', won=False, hut=True, fine=fine, fk=lt['fk'], out=False)
            result['message'] = 'Kinh hụt rồi! ' + (f'Bỏ {fine} xu vô hũ phạt nha.' if fine else 'Dò lại cho kỹ nha.')
        elif at > rv['npc_done']:
            _loto_lost(f, lt)
            result['fair'] = dict(game='lt', won=False, by=rv['npc_name'])
            result['message'] = f'Chậm một nhịp rồi! {rv["npc_name"]} đã hô “Kinh!” trước.'
        else:
            prize = rv['prize']   # the plain card's is LOTO_PRIZE
            lt['stage'] = 'won'
            st['lt_won'] += 1
            _ltd(f)['w'] += 1
            _pay(j, f, 'lt', prize)
            _grant(j, 'f_loto', got)
            if rv['mode'] in ('doi', 'nguoc', 'dem'):
                _grant(j, dict(doi='f_kinh2', nguoc='f_nguoc', dem='f_hu')[rv['mode']], got)
            result['fair'] = dict(game='lt', won=True, prize=prize, mode=rv['mode'], **({} if marks is not None else dict(row=row)))
            result['message'] = f'Kinh! Bạn thắng {prize} xu.'
    elif name == 'fair_loto_fold':
        need(not p, 'Dữ liệu thao tác không hợp lệ.')
        lt = f['loto']
        if lt and lt['stage'] == 'play':
            _loto_lost(f, lt)
        result['fair'] = dict(game='lt', folded=True)
    elif name == 'fair_oaq_start':
        need(set(p) == {'lv'} and p.get('lv') in oaq.LEVELS, 'Chọn người chơi cùng nha.')
        o = f['oaq']
        if o and o['stage'] == 'play':
            o['stage'] = 'lost'   # a new game gives the old one up
        _day(f, t)
        st['oaq'] += 1
        f['oaq'] = dict(lv=p['lv'], g=oaq.new_game(), at=int(t), stage='play')
        result['fair'] = dict(game='oaq', started=True, view=oaq_view(f['oaq']))
        result['message'] = f'Bày bàn ô ăn quan với {OAQ_PEOPLE[p["lv"]][0]}. Bạn đi trước nha!'
    elif name == 'fair_oaq_move':
        o = f['oaq']
        need(o and o['stage'] == 'play', 'Ván ô ăn quan này đã xong rồi.', 'fair_oaq_over')
        need(set(p) in ({'cell', 'dir'}, {'cell', 'dir', 'ply'}) and p['dir'] in (1, -1) and type(p['dir']) is int
             and type(p['cell']) is int, 'Dữ liệu thao tác không hợp lệ.')
        g = o['g']
        # The newer client sends the board's ply it played on: a second tap, a retry or another tab cannot play twice
        need('ply' not in p or (type(p['ply']) is int and p['ply'] == g['ply']),
             'Nước này đi rồi, bàn đã sang lượt mới. Coi lại bàn rồi đi tiếp nha.', 'fair_oaq_turn')
        need(p['cell'] in oaq.ROWS[0] and g['b'][p['cell']] > 0, 'Chọn một ô của bạn còn quân nha.', 'fair_oaq_cell')
        trace: list = [['turn', 0, p['cell'], p['dir']]]
        oaq.play(g, 0, p['cell'], p['dir'], trace)
        alive = oaq.begin_turn(g, 1, trace)
        if alive:
            c, d = oaq.ai_move(g, o['lv'], _rng)
            trace.append(['turn', 1, c, d])
            oaq.play(g, 1, c, d, trace)
            alive = oaq.begin_turn(g, 0, trace)
        end = None
        if not alive:
            end = _oaq_end(j, f, o, t, got)
        result['fair'] = dict(game='oaq', trace=trace, view=oaq_view(o), end=end)
        if end:
            result['message'] = (f'Thắng ván ô ăn quan! +{end["prize"]} xu.' if end['stage'] == 'won' else
                                 'Hòa ván ô ăn quan.' if end['stage'] == 'draw' else 'Thua ván ô ăn quan, ván sau gỡ nha.')
    elif name == 'fair_oaq_quit':
        need(not p, 'Dữ liệu thao tác không hợp lệ.')
        o = f['oaq']
        if o and o['stage'] == 'play':
            o['stage'] = 'lost'
        result['fair'] = dict(game='oaq', quit=True, view=oaq_view(o))
    elif name == 'fair_ring_start':
        need(not p, 'Dữ liệu thao tác không hợp lệ.')
        ms = int(t * 1000)
        r = f['ring']
        need(not (r and r['stage'] == 'play' and ms - r['at'] < 1500), 'Từ từ thôi, vòng chưa phát xong!', 'fair_slow')
        _day(f, t)
        f['earn']['ring_n'] = min(RING_DAY, f['earn']['ring_n'] + 1)   # a counter only, bounded for older validators
        st['ring'] += 1
        f['ring'] = dict(rs=_rng.getrandbits(31), at=ms, stage='play')
        result['fair'] = dict(game='ring', round=ring_view(f['ring'], t))
    elif name == 'fair_dart':   # 🎯 phóng phi tiêu: replaced by 🗡️ phóng dao (an older client still showing it)
        need(False, DART_GONE, 'fair_dart_gone')
    elif name.startswith('fair_kn_'):   # 🗡️ phóng dao: no daily money or round limit, the wallet only
        d = _knife(e, j, f, name, p, t)
        result['fair'], result['message'] = d['fair'], d['message']
    elif name == 'fair_xs':   # 🎟️ vé số cào: no daily money or ticket limit, the wallet only
        d = _scratch(e, j, f, p, t)
        result['fair'], result['message'] = d['fair'], d['message']
    elif name == 'fair_ring_throw':
        r = f['ring']
        need(set(p) == {'id', 'taps'}, 'Dữ liệu thao tác không hợp lệ.')
        need(r and r['stage'] == 'play' and p['id'] == r['rs'], 'Lượt ném này đã xong rồi.', 'fair_ring_over')
        elapsed = int(t * 1000) - r['at']
        r['stage'] = 'done'
        if elapsed > ring.TTL + ring.SLACK:
            result['fair'] = dict(game='ring', late=True, hits=[], n=0, prize=0)
            result['message'] = 'Lượt này lâu quá rồi, phát vòng mới nha.'
        else:
            need(ring.taps_ok(p['taps'], elapsed), 'Lượt ném này không hợp lệ.', 'fair_ring_bad')
            hits = ring.judge(ring.params(r['rs']), p['taps'])
            n = sum(h >= 0 for h in hits)
            st['ring_hits'] += n
            prize = _earn(j, f, 'ring', n * RING_HIT + (RING_ALL if n == ring.BOTTLES else 0))
            if n == ring.BOTTLES:
                _grant(j, 'f_ring', got)
            full = n * RING_HIT + (RING_ALL if n == ring.BOTTLES else 0)
            result['fair'] = dict(game='ring', hits=hits, n=n, prize=prize, capped=prize < full)
            result['message'] = f'Trúng {n}/{ring.BOTTLES} cổ chai' + (f', +{prize} xu.' if prize else '.')
    if got:
        result['fair']['titles'] = got
    return result


def action(s: dict, name: str, p: dict) -> tuple[dict, dict]:
    """Engine entry point (like invest.action): apply, run the journey hooks, validate."""
    from . import engine as e
    from . import journey as jr
    result = apply(s, name, p or {})
    titles_got = result.get('fair', {}).get('titles') or []
    jr.after(s, None, name, p or {}, result)
    if titles_got:
        box = result.setdefault('journey', dict(chapters=[], titles=[]))
        box['titles'] = list(dict.fromkeys(list(box.get('titles') or []) + titles_got))
    e.validate_state(s)
    return s, result


# ---------------------------------------------------------------- views
def today_xu(j: dict) -> dict:
    """Each stall's xu this life day (owner 03/10: "xu kiếm hôm nay"), read off its Sổ ví row (_pay keeps one per game
    and life day), so nothing new is saved."""
    out = {}
    for row in reversed((j.get('history') or [])[-40:]):
        if not isinstance(row, dict) or row.get('day') != j.get('life_day'):
            break
        if row.get('kind') == KIND and row.get('career') is None:
            label = str(row.get('label', ''))
            game = next((g for g, name in LABELS.items() if label.startswith(name)), None)
            if game and game not in out and isinstance(row.get('amount'), int):
                out[game] = row['amount']
    return out


def public(s: dict) -> dict:
    """api.state.fair. Outside the days around the fair: a few numbers only."""
    j = s.get('journey') or {}
    t = now()
    opens, closes = window()
    base = dict(open=opens <= t < closes, opens=opens, closes=closes)   # no clock here: the same save gives the same bytes
    if not j.get('story') or not (opens - SHOW_BEFORE <= t < closes + SHOW_AFTER):
        return dict(base, show=False)
    f = j.get('fair') if isinstance(j.get('fair'), dict) else None
    today = _today(f, t)
    st = (f or {}).get('stats') or {k: 0 for k in STATS}
    lt = (f or {}).get('loto')
    loto = None
    if lt and (lt['stage'] == 'play' or t - lt['at'] < LOTO_TTL):
        rv = round_view(lt)
        loto = dict(id=f'{lt["slot"]}-{lt["rs"]}', stage=lt['stage'], at=lt['at'], slot=lt['slot'],
                    minute=datetime.datetime.fromtimestamp(lt['slot'] * 60, VN).strftime('%H:%M'),
                    expired=lt['stage'] == 'play' and t - lt['at'] > LOTO_TTL,
                    card=rv['card'], seq=rv['seq'], npcs=[dict(name=n['name'], emoji=n['emoji'], rows=n['rows']) for n in rv['npcs']],
                    npc_done=rv['npc_done'], npc_name=rv['npc_name'],
                    # newer fields (the older client reads the ones above: its card is cards[0])
                    cards=rv['cards'], mode=rv['mode'], need=rv['need'], tier=rv['tier'], price=rv['price'],
                    prize=rv['prize'], fk=lt.get('fk', 0),
                    chot=rv['chot'], chot_n=rv['chot_n'])
        if lt.get('sb'):
            back = side_back(lt['sb'], rv['chot_n'])
            loto['side'] = {k: dict(pick=b[0], stake=b[1], back=back[k]) for k, b in lt['sb'].items()}
    money, pdays = money_of(j)
    earn = today['earn']
    o = (f or {}).get('oaq')
    ltd = (f or {}).get('ltd') if f and f.get('date') == vn_date(t) else None
    slot = int(t // 60)
    return dict(base, show=True, now=int(t), board=board(), today_xu=today_xu(j), cash=fc.public(j, edition(), opens <= t < closes),   # the clock (countdowns, cooldowns) only around the fair
                # 🏆 the Bảng vàng: xu won at the fair this edition (< 0: a loss), days played (the board: `board`)
                money=dict(total=money, days=pdays),
                soon=t < opens, over=t >= closes, wallet=j.get('wallet', 0), played=bool(f) and f.get('pday') == vn_date(t),
                today=dict(net=today['net'], rounds=today['rounds'], left=max(0, j.get('wallet', 0)), done=False),
                earn={g: dict(today=earn[g], cap=EARN_DAY[g], left=max(0, EARN_DAY[g] - earn[g])) if g not in EARN_UNCAPPED
                      else dict(today=0, cap=0, left=1, nocap=True) for g in EARN_GAMES},
                raid_left=max(0, int((f or {}).get('raid_until', 0) - t)) if f else 0,
                rules=dict(bc_open=BC_OPEN_MS, cap=DAY_CAP, bc_max=BC_MAX, bao=BAO, xd_min=XD_MIN, xd_max=XD_MAX, raid_pct=RAID_PCT, fine_min=FINE_MIN,
                           loto_price=LOTO_PRICE, loto_prize=LOTO_PRIZE, loto_npcs=LOTO_NPCS, faces=list(FACES),
                           oaq_prize=dict(OAQ_PRIZE), oaq_people={k: list(v) for k, v in OAQ_PEOPLE.items()}, quan=oaq.QUAN,
                           quan_non=oaq.QUAN_NON, ring_hit=RING_HIT, ring_all=RING_ALL, rings=ring.RINGS, ring_tol=ring.TOL,
                           ring_day=RING_DAY, ring_left=RING_DAY, oaq_turn=1, xd_fine_div=FINE_DIV, nocap=1),
                oaq=oaq_view(o) if o and (o['stage'] == 'play' or t - o['at'] < 6 * 3600) else None,
                ring=ring_view((f or {}).get('ring'), t),
                loto=loto, stats={k: st.get(k, 0) for k in STATS},
                food=ff.public(s),   # 🍡 the food carts' menus (absent from older servers: the carts only say a line)
                # 🗡️ phóng dao, in the phi tiêu's place (absent from older servers: the client then leaves the stall
                # out; `darts` is gone, so an older client leaves the phi tiêu out)
                knife=knife_public(j, f, t),
                # 🎟️ vé số cào (absent from older servers: the client then leaves the stall out)
                scratch=dict(tiers=list(scratch.TIERS), names={str(k): v for k, v in scratch.NAMES.items()},
                             cells=scratch.CELLS, match=scratch.MATCH, mults=list(scratch.MULTS)),
                # 🎱 the gánh lô tô: the vòng of this minute and the next nine, the tiers and side bets, today's tally
                # (hut_max 0: no limit on Kinh hụt; the older client showed it as "hụt N lần là nghỉ ván")
                ganh=dict(modes=[[slot + i, mode_of(slot + i)] for i in range(10)], names=dict(MODE_NAMES),
                           tiers=dict(LOTO_TIERS), cards=LOTO_CARDS, side_stakes=list(SIDE_STAKES), bay=list(BAY_NUMS),
                           cot_pay=COT_PAY_HALF / 2, fine=KINH_FINE, hut_max=0, dem_hours=list(DEM_HOURS),
                           modes_rule={m: dict(need=v[0], npcs=v[1], cut=v[2], pay=LOTO_PAY[m] / 10) for m, v in LOTO_MODES.items()},
                           prizes={m: {tr: [prize_of(m, pr, n) for n in range(1, LOTO_CARDS + 1)] for tr, pr in LOTO_TIERS.items()}
                                   for m in LOTO_MODES},
                           neighbours=[list(x) for x in NEIGHBOURS],
                           today=dict(ltd) if ltd else dict(r=0, w=0, fk=0, npc=[0] * len(NEIGHBOURS))))


def knife_public(j: dict, f: dict | None, t: float) -> dict:
    """api.state.fair.knife: the stall's rules (the ladder in tenths of the stake, prizes: in xu for each stake), the
    player's tally, the run."""
    k = j.get(KN_KEY) if isinstance(j.get(KN_KEY), dict) else {}
    return dict(stakes=list(knife.STAKES), ladder=list(knife.LADDER), prizes=[list(knife.prizes(x)) for x in knife.STAKES],
                levels=knife.LEVELS, gap=knife.GAP,
                draw=knife.DRAW_W, fly=knife.FLY_MS, impact=knife.IMPACT, min_tap=knife.MIN_TAP, level_ms=knife.LEVEL_MS,
                hot=knife.heat(_today(f, t)['net']), **{x: k.get(x, 0) for x in ('n', 'w', 'b', 'top')},
                run=_kn_view_run(k.get('run'), t))


def settle(s: dict) -> None:
    """Before every command (engine._apply_action): a vay nóng of a fair that has closed is collected (fair_cash);
    a 🗡️ phóng dao prize left waiting from an earlier day is paid."""
    _kn_settle(s)
    j = s.get('journey')
    if isinstance(j, dict) and 'fair_cash' in j:
        fc.settle(s, edition(), now() >= window()[1])


def validate(j: dict) -> None:
    """journey['fair'] and journey['fair_cash'] (both optional)."""
    fc.validate(j)
    if 'fair_run' in j:
        from .engine import need, integer
        r = j['fair_run']
        need(isinstance(r, dict) and set(r) == {'g', 'n', 'at'} and r['g'] in RUN_GAMES, 'Dữ liệu hội chợ không hợp lệ.', 'invalid_save')
        integer(r['n'], 0, 10**6)
        integer(r['at'], 0, 10**11)
    if 'fair_run2' in j:
        from .engine import need, integer
        r = j['fair_run2']
        need(isinstance(r, dict) and set(r) == {'g', 'n', 'at'} and r['g'] in RUN_GAMES2, 'Dữ liệu hội chợ không hợp lệ.', 'invalid_save')
        integer(r['n'], 0, 10**6)
        integer(r['at'], 0, 10**11)
    if KN_KEY in j:
        _kn_validate(j[KN_KEY])
    if 'fair' not in j:
        return
    from .engine import need, integer
    bad = 'Dữ liệu hội chợ không hợp lệ.'
    f = j['fair']
    need(isinstance(f, dict) and set(KEYS) <= set(f) <= set(KEYS + KEYS_OPT) and f['v'] == VERSION, bad, 'invalid_save')
    need(isinstance(f['date'], str) and len(f['date']) <= 10, bad, 'invalid_save')
    if f['date']:
        try:
            datetime.date.fromisoformat(f['date'])
        except ValueError:
            need(False, bad, 'invalid_save')
    integer(f['net'], -10**6, 10**6)
    integer(f['rounds'], 0, ROUNDS_DAY)
    integer(f['last'], 0, 10**14)
    integer(f['raid_until'], 0, 10**11)
    lt = f['loto']
    if lt is not None:
        need(isinstance(lt, dict) and set(LOTO_KEYS) <= set(lt) <= set(LOTO_KEYS + LOTO_OPT) and lt['stage'] in STAGES,
             bad, 'invalid_save')
        integer(lt['slot'], 0, 10**9)
        integer(lt['rs'], 0, 2**31)
        integer(lt['at'], 0, 10**11)
        need(lt.get('mode', 'thuong') in LOTO_MODES and lt.get('tier', 'vua') in LOTO_TIERS, bad, 'invalid_save')
        integer(lt.get('n', 1), 1, LOTO_CARDS)
        integer(lt.get('fk', 0), 0, FK_MAX)   # older saves: at most 3
        sb = lt.get('sb', {})
        need(isinstance(sb, dict) and set(sb) <= {'cl', 'cot'}, bad, 'invalid_save')
        for k, b in sb.items():
            need(isinstance(b, list) and len(b) == 2 and b[1] in SIDE_STAKES and type(b[1]) is int
                 and (b[0] in ('chan', 'le') if k == 'cl' else type(b[0]) is int and 0 <= b[0] <= 8), bad, 'invalid_save')
    dt = f.get('dt')
    if dt is not None:
        need(isinstance(dt, dict) and set(dt) == set(DT_KEYS), bad, 'invalid_save')
        for v in dt.values():
            integer(v, 0, 10**9)
    ltd = f.get('ltd')
    if ltd is not None:
        need(isinstance(ltd, dict) and set(ltd) == set(LTD_KEYS) and isinstance(ltd['npc'], list)
             and len(ltd['npc']) == len(NEIGHBOURS), bad, 'invalid_save')
        for v in [ltd['r'], ltd['w'], ltd['fk'], *ltd['npc']]:
            integer(v, 0, FK_MAX)
    need(f['ed'] == '' or (isinstance(f['ed'], str) and len(f['ed']) == 12 and f['ed'].startswith('fair') and f['ed'][4:].isdigit()),
         bad, 'invalid_save')
    integer(f['pts'], 0, 10**6)
    integer(f['dpts'], 0, POINTS_DAY)
    integer(f['pdays'], 0, 10**4)
    need(isinstance(f['pday'], str) and len(f['pday']) <= 10, bad, 'invalid_save')
    earn = f['earn']
    need(isinstance(earn, dict) and set(earn) == set(EARN_KEYS), bad, 'invalid_save')
    for g in EARN_GAMES:
        integer(earn[g], 0, EARN_DAY[g])
    integer(earn['ring_n'], 0, RING_DAY)
    o = f['oaq']
    if o is not None:
        need(isinstance(o, dict) and set(o) == set(OAQ_KEYS) and o['lv'] in oaq.LEVELS and o['stage'] in OAQ_STAGES
             and oaq.valid(o['g']), bad, 'invalid_save')
        integer(o['at'], 0, 10**11)
    r = f['ring']
    if r is not None:
        need(isinstance(r, dict) and set(r) == set(RING_KEYS) and r['stage'] in ('play', 'done'), bad, 'invalid_save')
        integer(r['rs'], 0, 2**31)
        integer(r['at'], 0, 10**14)
    st = f['stats']
    need(isinstance(st, dict) and set(st) == set(STATS), bad, 'invalid_save')
    for v in st.values():
        integer(v, 0, 10**9)


def _kn_validate(k: object) -> None:
    """journey['fair_kn'] (🗡️ phóng dao, optional)."""
    from .engine import need, integer
    bad = 'Dữ liệu hội chợ không hợp lệ.'
    need(isinstance(k, dict) and set(k) == set(KN_KEYS), bad, 'invalid_save')
    for x in ('n', 'w', 'b', 'top'):
        integer(k[x], 0, 10**9)
    run = k['run']
    if run is None:
        return
    need(isinstance(run, dict) and set(run) == set(KN_RUN) and run['sg'] in KN_STAGES and type(run['st']) is int
         and run['st'] in knife.STAKES and run['x2'] in (0, 1) and run['nx'] in (0, 1) and type(run['x2']) is int
         and type(run['nx']) is int and isinstance(run['tp'], list) and isinstance(run['day'], str) and len(run['day']) <= 10,
         bad, 'invalid_save')
    integer(run['lv'], 1, knife.LEVELS)
    integer(run['sd'], 0, 2**31)
    integer(run['hot'], 0, knife.HEAT_MAX)
    integer(run['at'], 0, 10**14)
    integer(run['bn'], 0, 10**6)
    integer(run['pz'], 0, 10**7)
    need(len(run['tp']) <= max(x[0] for x in knife.DIFF.values()), bad, 'invalid_save')
    for v in run['tp']:
        integer(v, 0, knife.LEVEL_MS)
