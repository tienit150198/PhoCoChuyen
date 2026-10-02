"""🏮 Hội chợ dân gian: a short folk fair in the neighbourhood (feedback #63, owner 02/10: "kiểu hội chợ ấy, mấy trò
này trò dân gian thôi nên cứ làm đi, mở ngắn hạn trong 5 ngày").

Played with the journey wallet's in-game xu only (never real money). Two kinds of stalls:

Chơi kiếm xu, no stake (owner 02/10: "vào đó có mấy trò dân gian như ô ăn quan, lô tô, bầu cua,... cho mọi người chơi
kiếm xu nhé"); each pays at most a few xu a Vietnam day (EARN_DAY):

* 🪨 Ô ăn quan against a neighbour (game/fair_oaq.py: the rules and the opponent): Bé Bi ("de") or Ông Hai ("kho").
  A win pays OAQ_PRIZE xu by level and PT_OAQ points; a loss or a draw costs nothing.
* 💍 Ném vòng cổ chai (game/fair_ring.py): RINGS throws at five bottles, timing a swinging ring; RING_HIT xu a bottle
  ringed, RING_ALL more for all five.

Thử vận may, small stakes:

* 🦀 Bầu cua tôm cá: six faces, three dice in a covered bowl; bet 1..BC_MAX xu in all on one or more faces. A face
  that shows k times pays the stake back plus 1:1 per die (standard rules); a "bão" (all three dice the face you bet)
  pays BAO:1 instead of 3:1, which keeps the house edge slight (95.4 % back over many rounds instead of 92.1 %).
* 🎱 Gánh lô tô (owner 02/10: "loto thì có nhạc, có mc, có người biểu diễn, mn đặt cược loto được nhé"): tờ dò of 3
  rows of 5 numbers (1..90). The caller's numbers come from the minute the cards were bought (everyone who buys in the
  same minute hears the same calls), and so does the minute's vòng (mode_of: Kinh đôi, lật ngược, the evening's Hũ đêm
  hội); the neighbours play their own cards (drawn per round, so knowing a minute's calls tells nothing about who
  wins). Buy 1..LOTO_CARDS tờ of one LOTO_TIERS price. The pot is everyone's cards ((yours + the neighbours') × price)
  less the stall's LOTO_MODES cut; whoever fills the vòng's pattern first takes it (a tie goes to the player). The
  player marks the called numbers by hand and hô "Kinh!": the server checks that every mark was called and that the
  marks fill the pattern; a Kinh hụt costs KINH_FINE xu (never above the wallet or the day's room) and the
  KINH_HUT_MAX-th one puts the cards out of the round. Side bets, placed with the cards and settled at once (the
  result comes from the round's secret cards): chẵn/lẻ of the số chốt (the call that filled the first pattern on the
  mat) pays 1:1, but 7 and 70, cô Bảy's own numbers, lose both sides; the cột may mắn (the tờ dò column the số chốt is
  in) pays COT_PAY_HALF/2 times the stake back. Returns with perfect play, from 200 000 simulated rounds each:

      vòng · vé nhỏ/vừa/lớn (2/5/10 xu)       1 tờ                2 tờ                3 tờ
      thường, lật ngược (4 neighbours, 8 %)   93.6/95.7/95.7 %    94.7/96.5/94.7 %    95.7/94.2/94.2 %
      Kinh đôi (4 neighbours, 10 %)           95.4/93.3/95.4 %    96.1/94.4/94.4 %    96.6/92.1/93.6 %
      Hũ đêm hội (6 neighbours, 13 %)         95.3/95.3/96.9 %    95.2/95.2/95.2 %    96.0/93.6/93.6 %
      chẵn/lẻ ≈ 97.6 %, cột may mắn ≈ 94.4 %

  (scratch simulation of the same functions; tests/test_fair.py LotoShow checks seeded samples. The older client's
  plain card is the thường vòng at LOTO_PRICE, paying LOTO_PRIZE.) A purchase is one round of ROUNDS_DAY and its
  whole stake (tờ + side bets, at most 3 × 10 + 2 × 10 xu) must fit the wallet and the day's DAY_CAP room. The day's
  tally (Bảng kinh hôm nay: rounds, Kinh, Kinh hụt, the neighbours' wins) is journey['fair']['ltd'].
* 🕯️ Chiếu trong (back corner): xóc đĩa chẵn lẻ (four coins, even money), bigger stakes XD_MIN..XD_MAX. Each round
  has RAID_PCT % odds that Công an phường comes by: the stake is confiscated, a fine of half the stake (at least
  FINE_MIN, never more than the wallet holds) is paid, and the corner stays closed RAID_COOLDOWN seconds. The front
  stalls are never raided.

Safety: the fair is open FAIR_DAYS days from FAIR_START (Vietnam dates; env MNL_FAIR_START=YYYY-MM-DD and
MNL_FAIR_DAYS override them at deploy), story saves only, no stake above what the wallet holds (no loans), a net
loss of at most DAY_CAP xu per Vietnam day (wins give some room back), ROUNDS_DAY rounds a day, a short pause between
rounds (and a per-session rate limit in server.py). Dice, coins, cards and raids come from the OS random source
(server side; nothing the client sends decides a result). Request ids/revisions make every command idempotent
(game/storage.py).

🏆 Bảng vàng hội chợ (owner: "event hội chợ mà top thì nhận danh hiệu vua trò chơi nhé"): fair points, never xu,
so big stakes or a lucky streak do not decide it and nobody is pushed to bet more: +1 for each day played, +3 for an ô
ăn quan won, +1 for a ném vòng round with 3 bottles or more (+2 for all five), +1 for a bầu cua round where a face you
bet came up, +1 for a xóc đĩa round won (a raided one: 0), +3 for a lô tô won; at most
POINTS_DAY a Vietnam day, and only while the fair is open. The points ride in the save and on the leaderboard table
(board `edition()`, game/leaderboard.py summary; ties: who reached the score first); the titles after the end are
game/fair_board.py.

Save: `journey['fair']` (optional, created by the first fair command; older saves load unchanged), a few numbers:
today's counters (chance net, rounds, xu earned per skill game; 'ltd', added on first use), the back corner's
cooldown, the current lô tô round {slot, rs, at, stage} plus, from the gánh lô tô on, {mode, tier, n, fk} and the
side bets {sb} (cards and calls are re-drawn from those; a round without them is the older plain card), the ô ăn quan game in progress {lv, g, at, stage},
the ném vòng round {rs, at, stage}, this edition's points and lifetime stats. Wallet moves go through one history row per game and life day
(kind 'fair'), updated in place, so a long evening at the fair does not push the rest of Sổ ví out.
"""
from __future__ import annotations

import datetime
import hashlib
import os
import random
import time

from . import fair_oaq as oaq
from . import fair_ring as ring

VERSION = 1
FAIR_START = '2026-10-03'      # first day (Vietnam date), 00:00 UTC+7
FAIR_DAYS = 5
SHOW_BEFORE = 2 * 86400        # the entry shows "sắp mở" this long before the start
SHOW_AFTER = 3 * 86400         # and "đã tàn" this long after the end
VN = datetime.timezone(datetime.timedelta(hours=7))
KIND = 'fair'                  # journey wallet history kind (journey.HISTORY_KINDS)

DAY_CAP = 150                  # net loss a Vietnam day at most
ROUNDS_DAY = 400
GAP_MS = 1200                  # between two rounds of dice/coins
# 🦀 Bầu cua
FACES = ('bau', 'cua', 'tom', 'ca', 'ga', 'nai')
FACE_NAMES = dict(bau='Bầu', cua='Cua', tom='Tôm', ca='Cá', ga='Gà', nai='Nai')
BC_MAX = 20
BAO = 10                       # three dice on the face you bet: BAO:1 (standard rules: 3:1)
# 🕯️ Chiếu trong
XD_MIN, XD_MAX = 10, 50
SIDES = ('chan', 'le')
RAID_PCT = 4
FINE_MIN = 5
RAID_COOLDOWN = 120
# 🎱 Lô tô
LOTO_PRICE = 5
LOTO_PRIZE = 23
LOTO_NPCS = 4
LOTO_TTL = 20 * 60             # a card can be claimed this long after it was bought
NEIGHBOURS = (('Bác Tư', '👴'), ('Bà Năm', '👵'), ('Chú Sáu', '🧔'), ('Cô Ba', '👩'), ('Anh Tèo', '🧑'), ('Chị Mận', '👧'))
STAGES = ('play', 'won', 'lost')
LOTO_TIERS = dict(nho=2, vua=5, lon=10)   # price of one tờ; 'vua' is the old plain card (LOTO_PRICE)
LOTO_CARDS = 3                 # tờ a round at most
# vòng: (full rows needed on one tờ, neighbours playing, the stall's cut of the pot in %)
LOTO_MODES = dict(thuong=(1, 4, 8), nguoc=(1, 4, 8), doi=(2, 4, 10), dem=(3, 6, 13))
MODE_NAMES = dict(thuong='Vòng thường', nguoc='Vòng lật ngược', doi='Vòng Kinh đôi', dem='Hũ đêm hội')
DEM_HOURS = (20, 21)           # Vietnam hours of the Hũ đêm hội: every round is one
KINH_FINE = 1                  # a Kinh hụt (the marks do not fill the pattern, or a mark was never called)
KINH_HUT_MAX = 3               # the third one in a round: the cards are out
SIDE_STAKES = (2, 4, 6, 10)    # side bets (even, so the cột's 8.5× is whole xu)
BAY_NUMS = (7, 70)             # cô Bảy's own numbers: a số chốt on one of them loses both chẵn and lẻ
COT_PAY_HALF = 17              # cột may mắn: stake × 17 / 2 back
LOTO_OPT = ('mode', 'tier', 'n', 'sb', 'fk')   # newer round keys (absent in older saves: thuong, vua, 1 tờ)
LTD_KEYS = ('r', 'w', 'fk', 'npc')            # today's lô tô: rounds, Kinh won, Kinh hụt, the neighbours' wins
# 🪨 Ô ăn quan and 💍 Ném vòng: no stake, a little xu for playing well, capped a day per game
OAQ_PRIZE = dict(de=15, kho=30)
OAQ_PEOPLE = dict(de=('Bé Bi', '👦'), kho=('Ông Hai', '👴'))
OAQ_STAGES = ('play', 'won', 'lost', 'draw')
RING_HIT, RING_ALL = 2, 5      # xu per bottle ringed, and the bonus for all five
RING_DAY = 80                  # rounds a day at most
EARN_DAY = dict(oaq=90, ring=45)
EARN_GAMES = tuple(EARN_DAY)
# 🏆 Bảng vàng hội chợ: points
POINTS_DAY = 30
PT_DAY, PT_BC, PT_XD, PT_LOTO = 1, 1, 1, 3
PT_OAQ, PT_RING3, PT_RING5 = 3, 1, 2

TITLE_ROWS = (   # journey.TITLES (secret, granted here only)
    ('f_oaq', '🪨', 'Cao tay ô ăn quan', 'Thắng Ông Hai một ván ô ăn quan ở hội chợ dân gian.'),
    ('f_ring', '💍', 'Tay ném vòng thần sầu', 'Ném trúng cả năm cổ chai trong một lượt ở hội chợ.'),
    ('f_loto', '🎱', 'Thần lô tô hội chợ', 'Hô “Kinh!” thắng một ván lô tô ở hội chợ dân gian.'),
    ('f_kinh2', '🎎', 'Kinh đôi rộn ràng', 'Thắng một vòng Kinh đôi ở gánh lô tô hội chợ.'),
    ('f_nguoc', '🙃', 'Đọc ngược như xuôi', 'Thắng một vòng lô tô lật ngược ở hội chợ.'),
    ('f_hu', '🏺', 'Ôm hũ đêm hội', 'Kinh cả tờ, ôm Hũ đêm hội ở gánh lô tô.'),
    ('f_bao', '🌪️', 'Trúng bão bầu cua', 'Ba con xúc xắc cùng ra đúng mặt bạn đặt ở hội chợ.'),
    ('f_raid', '🚨', 'Bị công an hỏi thăm', 'Đang chơi ở chiếu trong thì công an phường tới kiểm tra.'),
    ('f_king', '👑', 'Vua trò chơi', 'Đứng đầu Bảng vàng hội chợ dân gian khi hội tàn.'),
    ('f_master', '🎪', 'Cao thủ hội chợ', 'Lọt top 10 Bảng vàng hội chợ dân gian khi hội tàn.'),
)
AWARDS = ('f_king', 'f_master')   # granted after the end by game/fair_board.py (through game/live_effects.py)
AWARD_NAMES = {tid: f'{emoji} {name}' for tid, emoji, name, _ in TITLE_ROWS if tid in AWARDS}
STATS = ('bc', 'xd', 'lt', 'lt_won', 'raids', 'bao', 'won', 'lost', 'oaq', 'oaq_won', 'ring', 'ring_hits', 'earned')
KEYS = ('v', 'date', 'net', 'rounds', 'last', 'raid_until', 'loto', 'stats', 'ed', 'pts', 'dpts', 'pdays', 'pday',
        'earn', 'oaq', 'ring')
KEYS_OPT = ('ltd',)            # newer keys, added on first use (older saves load without them)
LOTO_KEYS = ('slot', 'rs', 'at', 'stage')
OAQ_KEYS = ('lv', 'g', 'at', 'stage')
RING_KEYS = ('rs', 'at', 'stage')
EARN_KEYS = ('oaq', 'ring', 'ring_n')   # today: xu earned per game, ném vòng rounds
LABELS = dict(bc='🦀 Bầu cua hội chợ', xd='🕯️ Chiếu trong hội chợ', lt='🎱 Lô tô hội chợ', oaq='🪨 Ô ăn quan hội chợ',
              ring='💍 Ném vòng hội chợ')
UNITS = dict(bc='ván', xd='ván', lt='tờ', oaq='ván thắng', ring='lượt')

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
    """This fair's id ('fair20261003'): its points, its leaderboard board, its titles' settle mark."""
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
    if f['ed'] != ed:   # a new fair: its own points
        f.update(ed=ed, pts=0, dpts=0, pdays=0)
    return f


def _points(f: dict, n: int, t: float) -> int:
    """Add up to `n` fair points (today's cap, only while the fair is open); returns how many counted."""
    if n <= 0 or not is_open(t):
        return 0
    add = max(0, min(n, POINTS_DAY - f['dpts']))
    f['dpts'] += add
    f['pts'] += add
    return add


def _day(f: dict, t: float) -> int:
    """The first game of a Vietnam day (any stall, while open): a day played, PT_DAY points."""
    today = vn_date(t)
    if f['pday'] == today or not is_open(t):
        return 0
    f['pday'] = today
    f['pdays'] += 1
    return _points(f, PT_DAY, t)


def points_of(j: dict) -> tuple[int, int]:
    """(points, days played) of this edition in a journey: the leaderboard row (game/leaderboard.py summary)."""
    f = j.get('fair') if type(j) is dict else None
    if type(f) is not dict or f.get('ed') != edition():
        return 0, 0
    pts, days = f.get('pts'), f.get('pdays')
    return (pts if type(pts) is int and pts > 0 else 0), (days if type(days) is int and days > 0 else 0)


def _today(f: dict | None, t: float) -> dict:
    """Read-only view of today's counters (public)."""
    if not f or f.get('date') != vn_date(t):
        return dict(net=0, rounds=0, earn=_earn0())
    return dict(net=f['net'], rounds=f['rounds'], earn=dict(f['earn']))


def budget(f: dict | None, t: float) -> int:
    """How much more may be lost today: DAY_CAP plus today's net (a win gives room back)."""
    return max(0, DAY_CAP + _today(f, t)['net'])


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
    count = st['oaq_won' if game == 'oaq' else game]
    label = f'{LABELS[game]} · {count} {UNITS[game]}'
    last = None
    for row in reversed(j['history'][-12:]):
        if not isinstance(row, dict) or row.get('day') != j['life_day']:
            break
        if row.get('kind') == KIND and row.get('career') is None and str(row.get('label', '')).startswith(LABELS[game]):
            last = row
            break
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


def _earn(j: dict, f: dict, game: str, amount: int) -> int:
    """Pay a skill stall's reward, up to what is left of today's EARN_DAY for that game; returns what was paid."""
    paid = max(0, min(amount, EARN_DAY[game] - f['earn'][game]))
    if paid:
        f['earn'][game] += paid
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
    """The pot a Kinh takes: everyone's tờ (n of the player's, the vòng's neighbours one each) less the cut."""
    pot = (n + LOTO_MODES[mode][1]) * price
    return pot - max(1, (pot * LOTO_MODES[mode][2] + 50) // 100)


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


def _ltd(f: dict) -> dict:
    """Today's lô tô counters (the Bảng kinh hôm nay), created on first use."""
    return f.setdefault('ltd', dict(r=0, w=0, fk=0, npc=[0] * len(NEIGHBOURS)))


def _loto_lost(f: dict, lt: dict) -> None:
    """A round ends without the player's Kinh: the neighbour who filled the pattern first takes the day's tally."""
    lt['stage'] = 'lost'
    _ltd(f)['npc'][round_view(lt)['npc_k']] += 1


# ---------------------------------------------------------------- commands
COMMANDS = ('fair_bc', 'fair_xd', 'fair_loto_buy', 'fair_loto_kinh', 'fair_loto_fold',
            'fair_oaq_start', 'fair_oaq_move', 'fair_oaq_quit', 'fair_ring_start', 'fair_ring_throw')
LATE = ('fair_loto_kinh', 'fair_loto_fold', 'fair_oaq_move', 'fair_oaq_quit', 'fair_ring_throw')   # may finish after the close


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
    """The game is over: who won, the reward (capped a day), the points."""
    g = o['g']
    me, opp = oaq.score(g, 0), oaq.score(g, 1)
    o['stage'] = 'won' if me > opp else 'lost' if me < opp else 'draw'
    out = dict(stage=o['stage'], me=me, opp=opp, prize=0, points=0)
    if o['stage'] == 'won':
        f['stats']['oaq_won'] += 1
        out['prize'] = _earn(j, f, 'oaq', OAQ_PRIZE[o['lv']])
        out['capped'] = out['prize'] < OAQ_PRIZE[o['lv']]
        out['points'] = _points(f, PT_OAQ, t)
        if o['lv'] == 'kho':
            _grant(j, 'f_oaq', got)
    return out


def _guard_round(e, f: dict, j: dict, t: float, stake: int, worst: int) -> int:
    """A new round: open, under today's caps, paid from the wallet (no loans), not too fast. Returns the day's
    point when this is the first round of the day."""
    need = e.need
    need(f['rounds'] < ROUNDS_DAY, ENOUGH, 'fair_enough')
    left = budget(f, t)
    need(left > 0, ENOUGH, 'fair_enough')
    need(worst <= left, f'Hôm nay bạn chỉ chơi thêm được {left} xu nữa thôi. {ENOUGH}' if left < worst else ENOUGH, 'fair_enough')
    need(j['wallet'] >= stake, 'Ví không đủ xu cho ván này. Hội chợ không cho vay để chơi đâu nha.', 'fair_wallet')
    ms = int(t * 1000)
    need(ms - f['last'] >= GAP_MS or f['last'] > ms, 'Từ từ thôi, xúc xắc chưa kịp lăn!', 'fair_slow')
    f['last'] = ms
    f['rounds'] += 1
    return _day(f, t)


def apply(s: dict, name: str, p: dict) -> dict:
    """`fair_*` commands. Checks everything before changing anything (the engine works on a copy anyway)."""
    from . import engine as e
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS, 'Thao tác hội chợ không hợp lệ.', 'unknown_action')
    need(j.get('story'), 'Hội chợ chỉ có trong hành trình.', 'not_story')
    t = now()
    opens, closes = window()
    if name not in LATE:   # a card, a game or a round begun while open can still be finished
        need(t >= opens, SOON, 'fair_closed')
        need(t < closes, CLOSED, 'fair_closed')
    f = _state(j, t)
    st = f['stats']
    got: list = []
    pts = 0
    result = dict(message='', effects=[])
    if name == 'fair_bc':
        bets = p.get('bets')
        need(set(p) == {'bets'} and isinstance(bets, dict) and bets and set(bets) <= set(FACES), 'Chọn mặt để đặt nha.')
        for v in bets.values():
            need(type(v) is int and 1 <= v <= BC_MAX, f'Mỗi ván đặt tối đa {BC_MAX} xu.')
        stake = sum(bets.values())
        need(stake <= BC_MAX, f'Mỗi ván đặt tối đa {BC_MAX} xu.')
        pts = _guard_round(e, f, j, t, stake, stake)
        dice = [_rng.choice(FACES) for _ in range(3)]
        back, bao = 0, None
        for face, b in bets.items():
            k = dice.count(face)
            if k == 3:
                back += b * (1 + BAO)
                bao = face
            elif k:
                back += b * (1 + k)
        st['bc'] += 1
        if back:
            pts += _points(f, PT_BC, t)
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
        fine = max(FINE_MIN, stake // 2)
        pts = _guard_round(e, f, j, t, stake, stake + fine)
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
            coins = [_rng.randrange(2) for _ in range(4)]
            even = sum(coins) % 2 == 0
            win = (p['side'] == 'chan') == even
            delta = stake if win else -stake
            if win:
                pts += _points(f, PT_XD, t)
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
        pts = _guard_round(e, f, j, t, stake, stake)
        lt = f['loto']
        if lt and lt['stage'] == 'play':
            _loto_lost(f, lt)   # a new card folds the old one
        lt = dict(slot=slot, rs=_rng.getrandbits(31), at=int(t), stage='play')
        if p:
            lt.update(mode=mode, tier=tier, n=n, fk=0)
            if sb:
                lt['sb'] = sb
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
            lt['fk'] = lt.get('fk', 0) + 1
            _ltd(f)['fk'] += 1
            fine = min(KINH_FINE, j['wallet'], budget(f, t))
            if fine > 0:
                _pay(j, f, 'lt', -fine)
            out = lt['fk'] >= KINH_HUT_MAX
            if out:
                _loto_lost(f, lt)
            result['fair'] = dict(game='lt', won=False, hut=True, fine=fine, fk=lt['fk'], out=out)
            result['message'] = ('Kinh hụt lần thứ ba, cô Bảy mời nghỉ ván này nha!' if out else
                                 'Kinh hụt rồi! ' + (f'Bỏ {fine} xu vô hũ phạt nha.' if fine else 'Dò lại cho kỹ nha.'))
        elif at > rv['npc_done']:
            _loto_lost(f, lt)
            result['fair'] = dict(game='lt', won=False, by=rv['npc_name'])
            result['message'] = f'Chậm một nhịp rồi! {rv["npc_name"]} đã hô “Kinh!” trước.'
        else:
            prize = LOTO_PRIZE if 'mode' not in lt else rv['prize']
            lt['stage'] = 'won'
            st['lt_won'] += 1
            _ltd(f)['w'] += 1
            pts += _points(f, PT_LOTO, t)
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
        pts = _day(f, t)
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
            pts += end['points']
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
        need(f['earn']['ring_n'] < RING_DAY, 'Hôm nay ném vòng vậy đủ rồi, mai ghé tiếp nha.', 'fair_enough')
        ms = int(t * 1000)
        r = f['ring']
        need(not (r and r['stage'] == 'play' and ms - r['at'] < 1500), 'Từ từ thôi, vòng chưa phát xong!', 'fair_slow')
        pts = _day(f, t)
        f['earn']['ring_n'] += 1
        st['ring'] += 1
        f['ring'] = dict(rs=_rng.getrandbits(31), at=ms, stage='play')
        result['fair'] = dict(game='ring', round=ring_view(f['ring'], t))
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
            pts += _points(f, PT_RING5 if n == ring.BOTTLES else PT_RING3 if n >= 3 else 0, t)
            if n == ring.BOTTLES:
                _grant(j, 'f_ring', got)
            full = n * RING_HIT + (RING_ALL if n == ring.BOTTLES else 0)
            result['fair'] = dict(game='ring', hits=hits, n=n, prize=prize, capped=prize < full)
            result['message'] = f'Trúng {n}/{ring.BOTTLES} cổ chai' + (f', +{prize} xu.' if prize else '.')
    result['fair']['points'] = pts
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
                    prize=rv['prize'] if 'mode' in lt else LOTO_PRIZE, fk=lt.get('fk', 0), hut_max=KINH_HUT_MAX,
                    chot=rv['chot'], chot_n=rv['chot_n'])
        if lt.get('sb'):
            back = side_back(lt['sb'], rv['chot_n'])
            loto['side'] = {k: dict(pick=b[0], stake=b[1], back=back[k]) for k, b in lt['sb'].items()}
    left = budget(f, t)
    pts, pdays = points_of(j)
    dpts = f['dpts'] if f and f.get('date') == vn_date(t) and f.get('ed') == edition() else 0
    earn = today['earn']
    o = (f or {}).get('oaq')
    ltd = (f or {}).get('ltd') if f and f.get('date') == vn_date(t) else None
    slot = int(t // 60)
    return dict(base, show=True, now=int(t), board=edition(),   # the clock (countdowns, cooldowns) only around the fair
                points=dict(total=pts, today=dpts, cap=POINTS_DAY, days=pdays,
                            rules=dict(day=PT_DAY, bc=PT_BC, xd=PT_XD, loto=PT_LOTO, oaq=PT_OAQ, ring3=PT_RING3, ring5=PT_RING5)),
                soon=t < opens, over=t >= closes, wallet=j.get('wallet', 0), played=bool(f) and f.get('pday') == vn_date(t),
                today=dict(net=today['net'], rounds=today['rounds'], left=left, done=left <= 0 or today['rounds'] >= ROUNDS_DAY),
                earn={g: dict(today=earn[g], cap=EARN_DAY[g], left=max(0, EARN_DAY[g] - earn[g])) for g in EARN_GAMES},
                raid_left=max(0, int((f or {}).get('raid_until', 0) - t)) if f else 0,
                rules=dict(cap=DAY_CAP, bc_max=BC_MAX, bao=BAO, xd_min=XD_MIN, xd_max=XD_MAX, raid_pct=RAID_PCT, fine_min=FINE_MIN,
                           loto_price=LOTO_PRICE, loto_prize=LOTO_PRIZE, loto_npcs=LOTO_NPCS, faces=list(FACES),
                           oaq_prize=dict(OAQ_PRIZE), oaq_people={k: list(v) for k, v in OAQ_PEOPLE.items()}, quan=oaq.QUAN,
                           quan_non=oaq.QUAN_NON, ring_hit=RING_HIT, ring_all=RING_ALL, rings=ring.RINGS, ring_tol=ring.TOL,
                           ring_day=RING_DAY, ring_left=max(0, RING_DAY - earn['ring_n']), oaq_turn=1),
                oaq=oaq_view(o) if o and (o['stage'] == 'play' or t - o['at'] < 6 * 3600) else None,
                ring=ring_view((f or {}).get('ring'), t),
                loto=loto, stats={k: st.get(k, 0) for k in STATS},
                # 🎱 the gánh lô tô: the vòng of this minute and the next nine, the tiers and side bets, today's tally
                ganh=dict(modes=[[slot + i, mode_of(slot + i)] for i in range(10)], names=dict(MODE_NAMES),
                           tiers=dict(LOTO_TIERS), cards=LOTO_CARDS, side_stakes=list(SIDE_STAKES), bay=list(BAY_NUMS),
                           cot_pay=COT_PAY_HALF / 2, fine=KINH_FINE, hut_max=KINH_HUT_MAX, dem_hours=list(DEM_HOURS),
                           modes_rule={m: dict(need=v[0], npcs=v[1], cut=v[2]) for m, v in LOTO_MODES.items()},
                           prizes={m: {tr: [prize_of(m, pr, n) for n in range(1, LOTO_CARDS + 1)] for tr, pr in LOTO_TIERS.items()}
                                   for m in LOTO_MODES},
                           neighbours=[list(x) for x in NEIGHBOURS],
                           today=dict(ltd) if ltd else dict(r=0, w=0, fk=0, npc=[0] * len(NEIGHBOURS))))


def validate(j: dict) -> None:
    """journey['fair'] (optional)."""
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
        integer(lt.get('fk', 0), 0, KINH_HUT_MAX)
        sb = lt.get('sb', {})
        need(isinstance(sb, dict) and set(sb) <= {'cl', 'cot'}, bad, 'invalid_save')
        for k, b in sb.items():
            need(isinstance(b, list) and len(b) == 2 and b[1] in SIDE_STAKES and type(b[1]) is int
                 and (b[0] in ('chan', 'le') if k == 'cl' else type(b[0]) is int and 0 <= b[0] <= 8), bad, 'invalid_save')
    ltd = f.get('ltd')
    if ltd is not None:
        need(isinstance(ltd, dict) and set(ltd) == set(LTD_KEYS) and isinstance(ltd['npc'], list)
             and len(ltd['npc']) == len(NEIGHBOURS), bad, 'invalid_save')
        for v in [ltd['r'], ltd['w'], ltd['fk'], *ltd['npc']]:
            integer(v, 0, 10**6)
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
