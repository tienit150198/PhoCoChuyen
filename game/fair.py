"""Folk fair, played with in-game xu only.

🎪 The house always wins (owner 08/10: "mở hội chợ nhé, tỷ lệ chỉnh lại làm sao cho phù hợp, đảm bảo nhà cái luôn
thắng"; the edition from FAIR_START 2026-10-09). Every paid luck stall returns less than it takes on every round, so
no way of betting (big when warm, small when cooled, switching stalls, a long pause) comes out ahead in the long run.
The most a round can return per xu staked (a fresh run, perfect play, see docs/FAIR_HOUSE_EDGE.md and
scripts/sim_fair_odds.py, which checks it on 10^6 rounds a stall):

  stall        how                                                  return  with 🍀 Lộc (gate always open)
  bầu cua      three honest dice, 1:1 a die, bão BAO:1               95.4%   96.5%
  chiếu trong  even money, BASES['xd'] won draws, RAID_PCT raids     96.1%   97.4%   (no fine: wallet short)
  lô tô        BASES['lt'] rounds go the player's way, Kinh 2.1×     95.6%   96.8%   (2- and 5-xu tờ: 91.0%)
  vé cào       BASES['xs'] tickets win, scratch.PRIZES mean 1.80×    90.0%   90.5%

Every other state is lower: the cool-off after STREAK wins (WIN_P_LOW), the spam decay (RUN_STEP down to P_FLOOR),
a Kinh called late, the police (raids, the asset check). The lô tô side bets are closed (SIDE_OPEN: the minute's
calls are the same for everyone, so a player who saw them could pick the likely chẵn/lẻ or cột). 🍀 Lộc trời cho stays
(LOC_P lower: on a busy server it still comes about once an hour). Phóng dao is a skill game (owner 05/10: no chance
draw ever turns a clean board into a loss): its return depends on the thumb, see game/fair_knife.py, but what it
pays over its stakes is capped, silently, at KN_DAY_CAP (300) xu a player and Vietnam day (_kn_over). Ô ăn quan and
ném vòng take no stake. No rate reaches the client (owner 08/10). Bầu cua and chiếu trong take any stake (STAKE_MAX).

Earlier rules (owner 07/10: "giảm tỷ lệ thắng của mọi người ở hội chợ, nếu ai spam 1 trò thì tỷ lệ thắng sẽ giảm dần
xuống còn 40%, công an sẽ đòi chứng minh tài sản ở đâu ra và thu 10% lợi nhuận của cả hội chợ"), still in force:

* Per-player, per-stall winning streaks: after four wins in a row the next rounds cool off to WIN_P_LOW (45%), a draw
  already lower stays lower. The sure win after four losses is gone (07/10: bet small four times, then big).
* Spam decay (journey[COOL_KEY], _heat): past RUN_FREE rounds of the same luck stall, each round's draw is RUN_STEP
  lower, down to P_FLOOR (40% won rounds; xóc đĩa XD_FLOOR so its won rounds stop at 40% too). Only two things bring a
  stall back to the full rate: SWITCH_ROUNDS rounds of other paid luck stalls (PAID_LUCK, any mix) since its last
  round, each staking at least switch_min (max(SWITCH_MIN, ¼ of the last stake there)), or a RUN_GAP pause from it.
  Free or skill stalls (ném vòng, ô ăn quan, phóng dao) change nothing. Bầu cua (honest dice) never cools.
  The stall shows "Vận đang nguội vì chơi liền một trò" (public: cold).
* Knife and o an quan remain skill games with unchanged opponents/collisions.
* Normal back-corner raids: 0.88% (owner 07/10, "giảm bớt bị công an bắt xuống 50%": half of 1.76%). Paid chance
  rounds can also trigger a 35% enforcement check (was 70%) above 50,000 daily net xu, at most once per 30 minutes;
  a successful check seizes 30% of the current wallet after settling the round.
* Owner 07/10 adds, as a separate rule after that check on the same round, the police's asset check (chứng minh
  nguồn tài sản, _asset_audit) once the player's fair profit this edition (money_of, the Bảng vàng number) is
  above AUDIT_FROM: AUDIT_P (22.5%, half of 45% since the owner's 07/10 "giảm bớt bị công an bắt xuống 50%"), at most
  once per AUDIT_GAP. It takes AUDIT_PCT (10%) of the profit made since the last
  check (journey['fair_audit'] keeps that mark: never twice on the same xu), from the wallet first, then the bank
  account, never below zero.
* 🍀 Lộc trời cho: a won paid luck round (bầu cua too: the dice stay honest) may, LOC_P of the time, win LOC_MULT× its
  stake instead of its normal winnings, at most once per LOC_GAP across the whole server (mnl_meta row LOC_KEY, taken in
  the command's own transaction by storage: loc_prepare / loc_claim).

Wallet limits, deadlines and the leaderboard remain unchanged.
Scratch prizes lean towards refunds/small prizes. Loto still requires correct
marks and a Kinh claim. There are no daily money or round limits.

Optional journey fair_chance metadata keeps old knife rounds and current ring
rounds readable. An already-started chance knife level can finish without a random
loss; its next level uses skill. fair_kn_skill locks the gentler board schedule for
new skill levels. No client-supplied win flag is trusted; the server replays taps.
Commands are idempotent through storage.
"""
from __future__ import annotations

import contextvars
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
from . import fair_photo as fp  # 📸 the photobooth's ticket
from . import fair_bm as bm     # 🕶️ Chợ đen: the bảo kê at the gate, the police's arrests

VERSION = 1
FAIR_START = '2026-10-09'      # first day (Vietnam date), 00:00 UTC+7 (owner 08/10: the fair opens again)
FAIR_DAYS = 5
PAST = (('2026-10-03', 5),)    # earlier editions (first day, days): their titles are settled even by a server that
                               # missed their end (game/fair_board.py)
SHOW_BEFORE = 2 * 86400        # the entry shows "sắp mở" this long before the start
SHOW_AFTER = 3 * 86400         # and "đã tàn" this long after the end
VN = datetime.timezone(datetime.timedelta(hours=7))
KIND = 'fair'                  # journey wallet history kind (journey.HISTORY_KINDS)

# No daily money cap and no round limit (owner 03/10: "mỗi ngày chơi không giới hạn tiền", "không giới hạn lượt
# chơi"): the wallet is the only limit. DAY_CAP and ROUNDS_DAY are kept only as the bounds an older server's validator
# puts on the saved counters (rolling release), which therefore stop there.
DAY_CAP = 150
ROUNDS_DAY = 400
# The draw of a fresh round, per stall (owner 08/10: "đảm bảo nhà cái luôn thắng"): each one below what breaks even,
# so every round of every paid stall returns less than its stake (the table at the top, docs/FAIR_HOUSE_EDGE.md).
# xóc đĩa: even money, its raids (RAID_PCT) come first; lô tô: a Kinh pays LOTO_PAY tenths of the tờ; vé cào: a won
# ticket pays scratch.PRIZES; ném vòng takes no stake (3 decimals: a ring round keeps its draw as p/1000).
BASES = dict(xd=.485, lt=.455, xs=.50, ring=.503)
WIN_P, WIN_P_LOW = .50, .45   # the older single rate (rules.luck_pct for an older client), and the streak cool-off
LOTO_WIN_P = BASES['lt']
LUCK_BASE = BASES['ring']      # the draw of a stall without its own BASES entry
XD_BASE = BASES['xd']
LUCK_PCT = 48                  # rules.luck_pct, the one rate an older client shows for all of them (about BASES' mean)
STREAK = 4                     # wins in a row before the cool-off (no sure win after losses since 07/10)
# Spam decay (owner 07/10): rounds RUN_FREE + 1, + 2, … of one luck stall draw RUN_STEP less each, down to P_FLOOR
# (XD_FLOOR for xóc đĩa: 40% won rounds after its raids). Back to the full rate: SWITCH_ROUNDS rounds of other PAID_LUCK
# stalls since the stall's last round, or a RUN_GAP pause from it; a free or skill stall resets nothing (07/10).
RUN_FREE, RUN_STEP, RUN_GAP, P_FLOOR = 10, .015, 600, .40
XD_FLOOR = .404               # .404 × (1 − 0.88%) ≈ 40.04% won rounds (was .407 with 1.76% raids)
DECAY_EXEMPT = ('bc',)         # bầu cua: honest dice with a house edge, no draw to lower
PAID_LUCK = ('bc', 'xd', 'lt', 'xs')   # the paid luck stalls whose rounds count as a switch
SWITCH_ROUNDS = 3
SWITCH_MIN, SWITCH_DIV = 20, 4   # a switch round stakes ≥ max(20 xu, ¼ of the last stake on the cooled stall) (07/10)
COOL_KEY = 'fair_cool'         # journey['fair_cool'] {stall: {n, at, sw, st}}: optional, an older server keeps it as is
COOL_GAMES = ('xd', 'lt', 'xs', 'ring')
RUN_GAMES = ('bc', 'xd', 'lt', 'dt')
# Stalls newer than 1.4.17, whose validator takes only RUN_GAMES in 'fair_run': their run is journey['fair_run2'], the
# same shape; there is one run at a time (a round of the other kind drops the other key), as if it were one key.
RUN_GAMES2 = ('xs',)
# One shared repetition floor; the bowl still takes five seconds to open.
RUN_RULES = {}                 # retained for older integrations; no repeat penalty
BC_OPEN_MS = 5000
BC_GAP_MS = 4800                 # BC_OPEN_MS less a little network slack
TAPER_FROM, TAPER_TO = 2000, 5000
FEATURE_SECONDS = 30 * 60
CHANCE_GAMES = ('lt', 'bc', 'xd', 'xs', 'ring')  # Knife and o an quan remain skill.
FEATURE_RATES = (WIN_P, WIN_P)
ORDINARY_RATES = (WIN_P, WIN_P)
STAKE_TIERS = dict(bc=(1, 2, 5, 10, 50, 100, 200, 500, 1000), xd=(10, 20, 30, 50, 100, 200, 500, 1000),
                   lt=(2, 5, 10, 50, 100, 200, 500, 1000), xs=scratch.TIERS)
GAP_MS = 400                   # between two rounds of dice/coins (owner 03/10: nhanh lên; was 1200)
# 🦀 Bầu cua
FACES = ('bau', 'cua', 'tom', 'ca', 'ga', 'nai')
FACE_NAMES = dict(bau='Bầu', cua='Cua', tom='Tôm', ca='Cá', ga='Gà', nai='Nai')
BC_OUTCOMES = [(x, y, z) for x in FACES for y in FACES for z in FACES]   # the 216 ways three dice land
ROUND_MAX = 1000               # what the saves keep of a stake (lô tô rounds, the cool-off run) stays within it: older validators
# Owner 08/10 "mn đặt cược bao nhiêu thoải mái nhé": bầu cua and chiếu trong take any stake the wallet holds. STAKE_MAX is
# only the sane bound that keeps one round's Sổ ví row within what every validator accepts (|amount| <= 10**7: a bão
# pays BAO times the stake); NET_SAFE keeps today's saved net (validated within ±10**9) far from its bound.
STAKE_MAX = 10**6
NET_SAFE = 10**8
BC_MAX = STAKE_MAX
BAO = 10                       # three dice on the face you bet: BAO:1 (standard rules: 3:1)
# 🕯️ Chiếu trong
XD_MIN, XD_MAX = 10, STAKE_MAX
SIDES = ('chan', 'le')
RAID_PCT = .88                 # owner 07/10 "giảm bớt bị công an bắt xuống 50%": half of 1.76% (was 1.6% → +10%)
FINE_MIN = 3
FINE_DIV = 4                   # a raid's fine: stake // FINE_DIV, at least FINE_MIN
RAID_COOLDOWN = 120
WEALTH_THRESHOLD, WEALTH_CHECK_GAP, WEALTH_RAID_P = 50000, 1800, .35   # 07/10: half of .70; gap and 30% unchanged
# 🚨 The asset check (owner 07/10, a rule of its own; players: "công an tới hoài": at most once per 2 hours, 22.5% when
# due (half of 45%, owner 07/10 "giảm … xuống 50%"), a failed draw waits too): fair profit above AUDIT_FROM, AUDIT_PCT
# of the profit made since the last check.
AUDIT_FROM, AUDIT_GAP, AUDIT_P = 50000, 7200, .225
AUDIT_KEY, AUDIT_PCT = 'fair_audit', 10   # journey['fair_audit'] {ed, base, at}: the profit left, the last check's time
AUDIT_LABEL = '🚨 Công an kiểm tra tài sản · Thu 10% tiền lời chợ đen'
POLICE_SAY = 'Chào em, nghe nói em lời ở chợ đen hơi bị nhiều. Chứng minh nguồn tài sản giúp anh cái nha.'
# 🍀 Lộc trời cho (owner 07/10): a won round of a paid luck stall pays LOC_MULT× its stake, LOC_P of the time, once per
# LOC_GAP for the whole server (the mnl_meta row LOC_KEY holds the last one's time).
# 08/10: LOC_P .015 → .003, so a won round's Lộc stays inside the house edge even with the gate always open (a lone
# player at night); on a busy server the gate still opens about once an hour, the first lucky won round takes it.
LOC_MULT, LOC_P, LOC_GAP, LOC_KEY = 10, .003, 3600, 'fair_loc_at'
# 🚓 A quiet start (owner 07/10, B6: "vừa vào bị tóm", "tay đầu tiên bị tóm luôn"): time away counted towards both
# police cooldowns, so the first paid round after a break rolled the raid and the asset check at once. A fair session
# starts with a paid round SESSION_GAP or more after the last one; neither check (_wealth_raid, _asset_audit) runs in its
# first GRACE_S seconds or its first GRACE_ROUNDS paid rounds, whichever ends LATER. Their odds and gaps are unchanged,
# the xóc đĩa's own per-round raid (dẹp chiếu) too. journey['fair_sess'] {at, n, ls}: the session's start, its paid
# rounds, the last one's time (optional: an older server keeps it as is; absent = the next paid round starts one).
SESS_KEY, SESSION_GAP, GRACE_S, GRACE_ROUNDS = 'fair_sess', 1800, 600, 20
LOC_LABEL = '🍀 Lộc trời cho ×10'
LOC_ACTIONS = ('fair_bc', 'fair_xd', 'fair_xs', 'fair_loto_kinh')
# 🎱 Lô tô
LOTO_PRICE = 5
LOTO_PRIZE = 10                # the older client's plain card: prize_of('thuong', LOTO_PRICE, 1) (was 23, a pot)
LOTO_NPCS = 4
# Loto: BASES['lt'] of the rounds go the player's way, and a Kinh pays LOTO_PAY tenths of what the tờ cost, rounded
# down (07/10: 2.1×, was 2.2× / 2.3×): a player who always calls in time gets 95.6% back (91% on the 2- and 5-xu tờ).
LOTO_PAY = dict(thuong=21, nguoc=21, doi=21, dem=21)
LOTO_TRIES = 300               # round ids tried for the outcome drawn (≈2..8 needed); the last one tried after that
LOTO_TTL = 20 * 60             # a card can be claimed this long after it was bought
NEIGHBOURS = (('Bác Tư', '👴'), ('Bà Năm', '👵'), ('Chú Sáu', '🧔'), ('Cô Ba', '👩'), ('Anh Tèo', '🧑'), ('Chị Mận', '👧'))
STAGES = ('play', 'won', 'lost')
LOTO_TIERS = dict(nho=2, vua=5, lon=10, dai=50, tram=100, cao=200, dac_biet=500, nghin=1000)
LOTO_CARDS = 3                 # tờ a round at most
# vòng: (full rows needed on one tờ, neighbours playing, the stall's cut of the pot in %)
LOTO_MODES = dict(thuong=(1, 4, 8), nguoc=(1, 4, 8), doi=(2, 4, 10), dem=(3, 6, 13))
MODE_NAMES = dict(thuong='Vòng thường', nguoc='Vòng lật ngược', doi='Vòng Kinh đôi', dem='Hũ đêm hội')
DEM_HOURS = (20, 21)           # Vietnam hours of the Hũ đêm hội: every round is one
KINH_FINE = 1                  # a Kinh hụt (the marks do not fill the pattern, or a mark was never called); no limit
FK_MAX = 10**6                 # Kinh hụt counted in a round / a day at most (the save's sane bound)
SIDE_STAKES = (2, 4, 6, 10, 20, 50, 100, 200)  # even: cột's 8.5× stays whole xu
# The side bets (chẵn/lẻ, cột may mắn) take no new bets since 08/10: they are settled on the số chốt, a call of the
# minute's sequence (calls(slot), the same for every card of that minute), so a player who saw the minute's calls on a
# first tờ could bet a second one on the likely parity or column and come out ahead. Rounds bought before still settle.
SIDE_OPEN = False
BAY_NUMS = (7, 70)             # cô Bảy's own numbers: a số chốt on one of them loses both chẵn and lẻ
COT_PAY_HALF = 17              # cột may mắn: stake × 17 / 2 back
LOTO_OPT = ('mode', 'tier', 'n', 'sb', 'fk')   # newer round keys (absent in older saves: thuong, vua, 1 tờ)
LTD_KEYS = ('r', 'w', 'fk', 'npc')            # today's lô tô: rounds, Kinh won, Kinh hụt, the neighbours' wins
# 🪨 Ô ăn quan and 💍 Ném vòng: no stake, a little xu for playing well, capped a day per game
OAQ_PRIZE = dict(de=50, kho=10000)   # owner 06/10: Ông Hai pays 10.000 xu a won game (was 500)
OAQ_PEOPLE = dict(de=('Bé Bi', '👦'), kho=('Ông Hai', '👴'))
OAQ_FIRST = ('kho',)   # owner 06/10 "không ai thắng được": Ông Hai opens (the first move is a big edge), Bé Bi lets you
OAQ_STAGES = ('play', 'won', 'lost', 'draw')
RING_HIT, RING_ALL = 3, 8      # xu per bottle ringed, and the bonus for all five
RING_DAY = 80                  # rounds a day at most
# B5 (07/10: one session sent ~20,000 ring calls): a new round starts at least this long after the last one started.
# A human round (5 throws GAP apart, the rings landing, "Ném lượt nữa") takes longer; the stall waits for it
# (public/js/v4/fair.js ringStart). No round cap and no penalty: a refused start changes nothing.
RING_GAP_MS = 2000
EARN_DAY = dict(oaq=90, ring=45)   # no cap any more (owner 03/10: kiếm không giới hạn); these bound the saved counters
EARN_UNCAPPED = ('oaq', 'ring')
EARN_GAMES = tuple(EARN_DAY)
# 🏆 Bảng vàng hội chợ: xu won (money_of); the points it counted until 03/10 are gone, POINTS_DAY only bounds the
# saved 'dpts' (older validators)
POINTS_DAY = 30
# 🗡️ Phóng dao stays a skill game, but the house still always wins (owner 08/10): what its runs win over their stakes
# is capped at KN_DAY_CAP xu a player and Vietnam day. The tally lives in the legacy 'dpts' (reset each Vietnam day and
# each edition, no other use since 03/10) in KN_CAP_UNIT steps, rounded up: the older validators' bound POINTS_DAY
# makes the cap 300 xu, so no new save key. Losing runs do not give it back. Silent (owner 08/10: "k báo ... số liệu
# k hiển thị ra"): nothing about it reaches the client. A level whose clearing would pay past it starts on the hardest
# board (knife.HEAT_MAX) and its clearing throw glances off (_kn_over): the run is lost like any crash.
KN_CAP_UNIT = 10
KN_DAY_CAP = KN_CAP_UNIT * POINTS_DAY
MONEY = ('won', 'lost', 'earned')   # the stats that make the board's score, reset with each edition

TITLE_ROWS = (   # journey.TITLES (secret, granted here only)
    ('f_oaq', '🪨', 'Cao tay ô ăn quan', 'Thắng Ông Hai một ván ô ăn quan ở chợ đen.'),
    ('f_ring', '💍', 'Tay ném vòng thần sầu', 'Ném trúng cả năm cổ chai trong một lượt ở chợ đen.'),
    ('f_loto', '🎱', 'Thần lô tô chợ đen', 'Hô “Kinh!” thắng một ván lô tô ở chợ đen.'),
    ('f_kinh2', '🎎', 'Kinh đôi rộn ràng', 'Thắng một vòng Kinh đôi ở gánh lô tô chợ đen.'),
    ('f_nguoc', '🙃', 'Đọc ngược như xuôi', 'Thắng một vòng lô tô lật ngược ở chợ đen.'),
    ('f_hu', '🏺', 'Ôm hũ đêm hội', 'Kinh cả tờ, ôm Hũ đêm hội ở gánh lô tô.'),
    ('f_bao', '🌪️', 'Trúng bão bầu cua', 'Ba con xúc xắc cùng ra đúng mặt bạn đặt ở chợ đen.'),
    ('f_dart', '🎯', 'Mắt thần phi tiêu', 'Phóng phi tiêu cắm ngay hồng tâm ở chợ đen.'),
    ('f_raid', '🚨', 'Bị công an hỏi thăm', 'Đang chơi ở chợ đen thì công an phường ập vào kiểm tra.'),
    ('f_king', '👑', 'Vua trò chơi', 'Đứng đầu Bảng vàng chợ đen khi chợ tàn.'),
    ('f_master', '🎪', 'Cao thủ chợ đen', 'Lọt top 10 Bảng vàng chợ đen khi chợ tàn.'),
)
AWARDS = ('f_king', 'f_master')   # granted after the end by game/fair_board.py (through game/live_effects.py)
AWARD_NAMES = {tid: f'{emoji} {name}' for tid, emoji, name, _ in TITLE_ROWS if tid in AWARDS}
STATS = ('bc', 'xd', 'lt', 'lt_won', 'raids', 'bao', 'won', 'lost', 'oaq', 'oaq_won', 'ring', 'ring_hits', 'earned')
KEYS = ('v', 'date', 'net', 'rounds', 'last', 'raid_until', 'loto', 'stats', 'ed', 'pts', 'dpts', 'pdays', 'pday',
        'earn', 'oaq', 'ring')
KEYS_OPT = ('ltd', 'dt', 'wealth_check_at')  # reader-first deploy before writing new metadata
DT_KEYS = ('n', 'w', 'b')      # 🎯 phi tiêu, lifetime: throws, hits, hồng tâm
LOTO_KEYS = ('slot', 'rs', 'at', 'stage')
OAQ_KEYS = ('lv', 'g', 'at', 'stage')
RING_KEYS = ('rs', 'at', 'stage')
EARN_KEYS = ('oaq', 'ring', 'ring_n')   # today: xu earned per game, ném vòng rounds
LABELS = dict(bc='🦀 Bầu cua chợ đen', xd='🕯️ Chiếu trong chợ đen', lt='🎱 Lô tô chợ đen', oaq='🪨 Ô ăn quan chợ đen',
              ring='💍 Ném vòng chợ đen', dt='🎯 Phi tiêu chợ đen', xs='🎟️ Vé số cào chợ đen', kn='🗡️ Phóng dao chợ đen')
# The rows an older server wrote today under the fair's former name (owner 08/10: "k phải là hội chợ, nó là Chợ đen") are
# still the stall's rows: kept up to date, counted in today_xu.
LABELS_OLD = {g: v.replace('chợ đen', 'hội chợ') for g, v in LABELS.items()}
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

CLOSED = 'Chợ đen đã tàn, hẹn lần sau nha!'
SOON = 'Chợ đen chưa mở đâu, hẹn bạn ngày chợ mở nha!'
ENOUGH = 'Hôm nay chơi vậy đủ rồi, mai ghé tiếp nha.'
TOO_BIG = 'Ván lớn cỡ này nhà cái không nhận đâu, đặt ít lại chút nha.'   # past STAKE_MAX (no number shown)

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
    """This fair's id ('fair20261009'): the save's edition (its days, its money), its titles' settle mark. A new id
    starts afresh: the save's days and money of the fair (_state), its Bảng vàng (board()), the police's mark
    (audit_base), the gift (fair_cash); a loan of an older edition is collected (fair_cash.settle)."""
    return 'fair' + _start_date().strftime('%Y%m%d')


def past() -> list[tuple[str, str, int]]:
    """The earlier editions before this one: [(edition, its board, its close as epoch seconds)]."""
    cur = _start_date()
    out = []
    for raw, days in PAST:
        d = datetime.date.fromisoformat(raw)
        if d < cur:
            t0 = int(datetime.datetime(d.year, d.month, d.day, tzinfo=VN).timestamp())
            ed = 'fair' + d.strftime('%Y%m%d')
            out.append((ed, ed + 'xu', t0 + days * 86400))
    return out


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
    """The Bảng vàng's leaderboard board: 'fair20261009xu' (xu won). Not the edition itself, whose rows an older
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
        st['earned'] = min(10**9, st['earned'] + amount)
    else:
        f['net'] = max(-10**9, min(10**9, f['net'] + amount))   # the validators' bounds (big stakes: STAKE_MAX)
        if amount > 0:
            st['won'] = min(10**9, st['won'] + amount)
        else:
            st['lost'] = min(10**9, st['lost'] - amount)
    last = None
    for row in reversed(j['history'][-12:]):
        if not isinstance(row, dict) or row.get('day') != j['life_day']:
            break
        if row.get('kind') == KIND and row.get('career') is None and str(row.get('label', '')).startswith((LABELS[game], LABELS_OLD[game])):
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
    """What a Kinh takes: LOTO_PAY tenths of the n tờ's price (rounded down)."""
    return n * price * LOTO_PAY[mode] // 10


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
    """The older single rate of luck rounds (WIN_P at any net; no money taper since 05/10; kept for older callers):
    each stall now draws its own BASES. Winning streaks cool off in _draw_luck."""
    return WIN_P if hi is None else hi


def _run(j: dict, game: str, t: float) -> int:
    """Count this round in the player's run of `game`; returns its length (1 for a new run)."""
    key = 'fair_run3' if game == 'ring' else 'fair_run2' if game in RUN_GAMES2 else 'fair_run'
    for other in ('fair_run', 'fair_run2', 'fair_run3'):
        if other != key:
            j.pop(other, None)
    r = j.get(key)
    if not (isinstance(r, dict) and r.get('g') == game and 0 <= int(t) - r.get('at', 0) <= RUN_GAP):
        r = j[key] = dict(g=game, n=0, at=int(t))
    r['n'] = min(10**6, r['n'] + 1)
    r['at'] = int(t)
    return r['n']


def featured_game(t: float) -> str:
    """Pure wall-clock rotation: no polling, timers, database or per-worker RNG."""
    return CHANCE_GAMES[int(t // FEATURE_SECONDS) % len(CHANCE_GAMES)]


def chance_rate(game: str, t: float, stake: int | None = None, net: int = 0) -> float:
    """The draw of a fresh round of a stall (BASES), independent of money or time: the most it ever is."""
    return BASES.get(game, LUCK_BASE)


def switch_min(r: dict) -> int:
    """The smallest stake of a round elsewhere that counts towards warming the stall of run `r` up again."""
    return max(SWITCH_MIN, -(-r['st'] // SWITCH_DIV))


def _heat(j: dict, game: str, t: float, stake: int = 0) -> int:
    """The spam-decay count of this round of `game` (1: a fresh run). A round of a paid luck stall staking at least
    switch_min counts towards every other stall's switch (a smaller one changes nothing); a stall SWITCH_ROUNDS such
    rounds past its last one, or RUN_GAP after it, starts afresh. A free stall (ring) counts only for itself."""
    c = j.get(COOL_KEY)
    if not isinstance(c, dict):
        c = j[COOL_KEY] = {}
    now = int(t)
    for g in list(c):
        if g == game:
            continue
        r = c[g]
        if game in PAID_LUCK and stake >= switch_min(r):
            r['sw'] = min(SWITCH_ROUNDS, r['sw'] + 1)
        if not 0 <= now - r['at'] <= RUN_GAP or r['sw'] >= SWITCH_ROUNDS:
            del c[g]   # back to the full rate
    if game not in COOL_GAMES:
        if not c:
            j.pop(COOL_KEY)
        return 1
    r = c.get(game)
    if not (isinstance(r, dict) and 0 <= now - r['at'] <= RUN_GAP and r['sw'] < SWITCH_ROUNDS):
        r = c[game] = dict(n=0, at=now, sw=0, st=0)
    r.update(n=min(10**6, r['n'] + 1), at=now, sw=0, st=min(ROUND_MAX, max(0, int(stake or 0))))
    return r['n']


def run_rate(game: str, n: int) -> float:
    """The draw of round n (1: the first) of a run of one stall: the full rate for RUN_FREE rounds, then RUN_STEP less a
    round, never below the floor. Bầu cua (DECAY_EXEMPT) keeps its rate (its dice are honest anyway)."""
    base = chance_rate(game, 0)
    if game in DECAY_EXEMPT or n <= RUN_FREE:
        return base
    return max(XD_FLOOR if game == 'xd' else P_FLOOR, round(base - RUN_STEP * (n - RUN_FREE), 3))


def luck_p(j: dict, f: dict | None, game: str, t: float, *, stake: int | None = None) -> float:
    """Count the round in the player's runs and return its draw (run_rate of the decay count): no profit or price
    penalty. The older run keys (_run) are kept up to date for older servers, but decide nothing any more."""
    _run(j, game, t)
    return run_rate(game, _heat(j, game, t, stake or 0))


def cold(j: dict, t: float) -> dict | None:
    """The most recently played stall whose next round is cooled by a long run (public: the "Vận đang nguội" hint),
    else None. switch: the rounds of another paid luck stall still needed to warm it up again, each staking ≥ min."""
    c = j.get(COOL_KEY)
    out = None
    for g, r in (c.items() if isinstance(c, dict) else ()):
        if not 0 <= int(t) - r['at'] <= RUN_GAP or r['sw'] >= SWITCH_ROUNDS:
            continue
        p = run_rate(g, r['n'] + 1)
        if p < chance_rate(g, t) and (out is None or r['at'] >= out[0]):
            out = r['at'], dict(game=g, n=r['n'], gap=RUN_GAP // 60, switch=SWITCH_ROUNDS - r['sw'], min=switch_min(r))
    return out and out[1]


def _draw_luck(j: dict, game: str, probability: float) -> bool:
    draw = _rng.random()
    # A round locked at a higher rate before this build (a ring round started earlier) keeps it.
    if probability > chance_rate(game, 0) + 1e-9:
        return draw < probability
    balance = j.setdefault('fair_balance', {})
    streak = balance.get(game, 0)
    # Four wins in a row or more: cooled off to WIN_P_LOW (a draw already lower stays lower). No sure win after losses;
    # the losing side of the streak is still counted, within the older validator's bound.
    won = draw < (min(probability, WIN_P_LOW) if streak >= STREAK else probability)
    balance[game] = min(STREAK, max(0, streak) + 1) if won else max(-STREAK, min(0, streak) - 1)
    return won


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


def bc_fair_roll() -> list:
    """Three honest dice (owner 06/10): uniform over the 216 outcomes, whatever was bet. Single-face EV −10/216 a xu."""
    return [_rng.choice(FACES) for _ in range(3)]


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


def ring_view(r: dict | None, t: float, j: dict | None = None) -> dict | None:
    if not r or r['stage'] != 'play' or int(t * 1000) - r['at'] > ring.TTL:
        return None
    return dict(id=r['rs'], **ring.params(r['rs']), chance=_chance(j or {}, 'ring', r) is not None)


def _chance(j: dict, game: str, run: dict) -> dict | None:
    """Optional metadata outside legacy round shapes. Old rounds keep their original rules."""
    c = j.get('fair_chance', {}).get(game)
    return c if c and c['at'] == run['at'] and c['seed'] == run.get('sd', run.get('rs')) else None


def _set_chance(j: dict, game: str, run: dict, p: float) -> None:
    j.setdefault('fair_chance', {})[game] = dict(at=run['at'], seed=run.get('sd', run.get('rs')), p=round(p * 1000))


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
    need(j['wallet'] >= stake, 'Ví không đủ xu cho ván này. Chợ đen không cho vay để chơi đâu nha.', 'fair_wallet')
    need(abs(f['net']) + stake < NET_SAFE, ENOUGH, 'fair_enough')   # the saved net's sane bound; pending prizes still settle
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


def _kn_sched(run: dict, j: dict | None = None) -> dict:
    if _kn_soft(j or {}, run):
        return knife.schedule(run['sd'], run['lv'], run['hot'], knife.SOFT_DIFFICULTY)
    rules = _kn_skill(j or {}, run) or _chance(j or {}, 'kn', run) or {}
    return knife.schedule(run['sd'], run['lv'], run['hot'], rules.get('difficulty', 100))


def _kn_soft(j: dict, run: dict) -> bool:
    """A level started on this build: the softer board (fair_knife.SOFT_*). journey['fair_kn_soft'] = {at, seed}."""
    soft = j.get('fair_kn_soft')
    return isinstance(soft, dict) and soft.get('at') == run['at'] and soft.get('seed') == run['sd']


def _kn_skill(j: dict, run: dict) -> dict | None:
    rules = j.get('fair_kn_skill')
    return rules if rules and rules['at'] == run['at'] and rules['seed'] == run['sd'] else None


def _set_kn_skill(j: dict, run: dict) -> None:
    # fair_kn_skill keeps the value an older worker validates (rolling deploy); fair_kn_soft marks this level softer.
    j['fair_kn_skill'] = dict(at=run['at'], seed=run['sd'], difficulty=knife.SKILL_DIFFICULTY)
    j['fair_kn_soft'] = dict(at=run['at'], seed=run['sd'])
    j.get('fair_chance', {}).pop('kn', None)


def _kn_cleared(run: dict) -> int:
    return run['lv'] if run['sg'] in ('choice', 'done') else run['lv'] - 1


def _kn_late(run: dict, t: float) -> bool:
    """A level not finished in time (LEVEL_MS, plus SLACK for the network) is lost, like a knife on a knife (else a
    client could hold back a losing throw and keep the prize of the levels before)."""
    return run['sg'] == 'play' and int(t * 1000) - run['at'] > knife.LEVEL_MS + knife.SLACK


def _kn_level(f: dict, run: dict, t: float) -> None:
    """A new level of the run: its own seed (drawn now, so nothing of it is known before), the heat of today's net;
    the hardest board when clearing it would pay past today's KN_DAY_CAP."""
    run.update(sd=_rng.getrandbits(31), hot=knife.heat(_today(f, t)['net']), at=int(t * 1000), sg='play', tp=[], day='')
    if _kn_over(f, run, t):
        run['hot'] = knife.HEAT_MAX


def _kn_over(f: dict, run: dict, t: float) -> bool:
    """Clearing the run's level (its x2 bonus too) would win more over the stake than today's KN_DAY_CAP has left."""
    bn = run['bn'] + (knife.x2_bonus(run['st'], run['lv']) if run['x2'] else 0)
    return knife.prize(run['st'], run['lv'], bn) - run['st'] > kn_cap_left(f, t)


def kn_cap_left(f: dict | None, t: float) -> int:
    """How many more xu Phóng dao may win over its stakes today (KN_DAY_CAP)."""
    if not f or f.get('date') != vn_date(t):
        return KN_DAY_CAP
    return max(0, KN_DAY_CAP - f['dpts'] * KN_CAP_UNIT)


def _kn_pay(j: dict, f: dict, run: dict) -> int:
    """Dừng: the prize of the levels cleared into the wallet; the run is done. f is today's _state. A level that would
    pay past KN_DAY_CAP is never cleared (_kn_over), so the min() below is only a backstop."""
    k = _kn(j)
    st = run['st']
    pz = min(knife.prize(st, _kn_cleared(run), run['bn']), st + max(0, KN_DAY_CAP - f['dpts'] * KN_CAP_UNIT))
    if pz > st:   # the gain, in KN_CAP_UNIT steps rounded up (the house's side)
        f['dpts'] = min(POINTS_DAY, f['dpts'] + -(-(pz - st) // KN_CAP_UNIT))
    run.update(sg='done', pz=pz)
    if pz:
        _pay(j, f, 'kn', pz)
    k['w'] = min(10**9, k['w'] + 1)
    k['top'] = max(k['top'], pz)
    return pz


def _kn_view_run(run: dict | None, t: float, j: dict | None = None) -> dict | None:
    """The run for the client: the level being thrown (its board), the choice, or how the last run ended."""
    if not run:
        return None
    sg = 'lost' if _kn_late(run, t) else run['sg']
    st, lv, bn = run['st'], run['lv'], run['bn']
    chance = _chance(j or {}, 'kn', run) is not None
    out = dict(stake=st, lv=lv, stage=sg, x2=bool(run['x2']), prize=knife.prize(st, _kn_cleared(dict(run, sg=sg)), bn), chance=chance)
    if sg == 'play':
        ms = int(t * 1000)
        board = knife.public_schedule(_kn_sched(run, j))
        if chance:
            board.update(chance=True, pre=[])
        out.update(board=board, id=f'{run["sd"]}-{lv}', el=ms - run['at'],
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
    """🗡️ fair_kn_start {stake}, fair_kn_throw {lv, taps, id?}, fair_kn_next {}, fair_kn_stop {} (game/fair_knife.py)."""
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
        _police(j, f, t, 'kn', stake)
        run = k['run'] = dict(st=stake, lv=1, sd=0, hot=0, at=0, sg='play', bn=0, x2=0, nx=0, tp=[], day='', pz=0)
        _kn_level(f, run, t)
        _set_kn_skill(j, run)
        for key in ('fair_run', 'fair_run2', 'fair_run3'):
            j.pop(key, None)  # the older run keys only: the spam decay (COOL_KEY) waits for paid rounds or a pause
        k['n'] = min(10**9, k['n'] + 1)
        _pay(j, f, 'kn', -stake)
        return dict(fair=dict(game='kn', started=True, run=_kn_view_run(run, t, j)), message='')
    if name == 'fair_kn_throw':
        lv, taps = p.get('lv'), p.get('taps')
        need(set(p) in ({'lv', 'taps'}, {'lv', 'taps', 'id'}) and type(lv) is int, bad)
        need(run and run['lv'] == lv and run['sg'] in ('play', 'lost'), 'Màn này đã xong rồi.', 'fair_kn_over')
        # New clients bind delayed/retried throws to this board, not just level 1
        # of whichever run another tab has most recently started.
        need('id' not in p or p['id'] == f'{run["sd"]}-{lv}', 'Lượt này đã đổi rồi. Mở lại bia hiện tại nhé.', 'fair_kn_over')
        need(run['sg'] == 'play' or late, 'Màn này đã xong rồi.', 'fair_kn_over')   # lost already (another tab)
        if late:
            return dict(fair=dict(game='kn', lv=lv, lost=True, late=True, run=_kn_view_run(run, t, j)),
                        message='Lâu quá bia ngừng quay rồi, lượt này thua. Phóng lượt mới nha.')
        sc = _kn_sched(run, j)
        need(knife.taps_ok(taps, sc['need'], ms - run['at']) and taps[:len(run['tp'])] == run['tp'], bad, 'fair_kn_bad')
        chance = _chance(j, 'kn', run)
        if chance is not None:
            # Already displayed chance-mode throws allowed overlaps. Do not turn
            # those into retroactive collisions or invent a random loss now.
            # The next board will be visible skill play from its first throw.
            stuck = knife.chance_positions(sc['need'], len(taps))
            hit = -1
        else:
            stuck, hit = knife.judge(sc, taps)
        if hit < 0 and len(stuck) >= sc['need'] and _kn_over(f, run, t):   # KN_DAY_CAP: the clearing throw glances off
            stuck, hit = stuck[:len(taps) - 1], len(taps) - 1
        out = dict(game='kn', lv=lv, stuck=stuck, hit=hit)
        if hit >= 0:
            run['sg'] = 'lost'
            out.update(lost=True, run=_kn_view_run(run, t, j))
            return dict(fair=out, message='Dao chạm dao rồi! Lượt này thua hết.')
        if len(stuck) < sc['need']:   # not done yet: the server keeps the throws it has judged
            run['tp'] = list(taps)
            out.update(run=_kn_view_run(run, t, j))
            return dict(fair=out, message='')
        if run['x2']:
            run['bn'] += knife.x2_bonus(run['st'], lv)
        k['b'] = max(k['b'], lv)
        run.update(sg='choice', tp=[], day=vn_date(t), nx=0)
        if lv >= knife.LEVELS:   # the last level: nothing more to risk, the prize is paid
            pz = _kn_pay(j, f, run)
            out.update(cleared=True, all=True, paid=pz, run=_kn_view_run(run, t, j))
            return dict(fair=out, message=f'Phá đảo cả {knife.LEVELS} màn! +{pz} xu.')
        run['nx'] = int(not run['x2'] and _rng.random() < knife.X2_P)   # never two x2 levels in a row
        out.update(cleared=True, run=_kn_view_run(run, t, j))
        return dict(fair=out, message='')
    need(not p, bad)
    if name == 'fair_kn_next':
        need(run and run['sg'] == 'choice', 'Không có màn nào đang chờ chơi tiếp.', 'fair_kn_over')
        run.update(lv=run['lv'] + 1, x2=run['nx'], nx=0)
        _kn_level(f, run, t)
        _set_kn_skill(j, run)
        _day(f, t)
        return dict(fair=dict(game='kn', next=True, run=_kn_view_run(run, t, j)), message='')
    need(run and run['sg'] in ('choice', 'done'), 'Không có thưởng nào đang chờ.', 'fair_kn_over')   # fair_kn_stop
    if run['sg'] == 'done':   # already paid (the day ended, or another tab)
        return dict(fair=dict(game='kn', stopped=True, prize=run['pz'], again=True, run=_kn_view_run(run, t, j)),
                    message='Thưởng lượt này đã vô ví rồi.')
    pz = _kn_pay(j, f, run)
    return dict(fair=dict(game='kn', stopped=True, prize=pz, run=_kn_view_run(run, t, j)), message=f'Nhận thưởng {pz} xu!')


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
    _police(j, f, t, 'xs', price)
    win = _draw_luck(j, 'xs', luck_p(j, f, 'xs', t, stake=price))
    mult = scratch.prize_mult(_rng) if win else 0
    cells = scratch.layout(price, mult, _rng)
    prize = mult * price
    _pay(j, f, 'xs', prize - price)
    out = dict(game='xs', id=_rng.getrandbits(31), price=price, name=scratch.NAMES[price], cells=cells, prize=prize,
               mult=mult, net=prize - price, hits=[i for i, v in enumerate(cells) if prize and v == prize])
    loc = _loc(j, f, 'xs', price, prize - price, t)
    if loc:
        out['loc'] = loc
    return dict(fair=out, message='')


def _guard_round(e, f: dict, j: dict, t: float, stake: int, worst: int) -> None:
    """A new round: open, paid from the wallet (no loans), not too fast. Counts the day played."""
    need = e.need
    need(j['wallet'] >= stake, 'Ví không đủ xu cho ván này. Chợ đen không cho vay để chơi đâu nha.', 'fair_wallet')
    need(abs(f['net']) + worst * (BAO + 1) < NET_SAFE, ENOUGH, 'fair_enough')   # the saved net's sane bound
    ms = int(t * 1000)
    need(ms - f['last'] >= GAP_MS or f['last'] > ms, 'Từ từ thôi, xúc xắc chưa kịp lăn!', 'fair_slow')
    f['last'] = ms
    f['rounds'] = min(ROUNDS_DAY, f['rounds'] + 1)   # a counter only (no limit); bounded for older validators
    _day(f, t)


def _xu(n: int) -> str:
    return f'{n:,}'.replace(',', '.')


def audit_base(j: dict) -> int:
    """The fair profit already checked by the police this edition (0: none yet)."""
    a = j.get(AUDIT_KEY)
    return a['base'] if isinstance(a, dict) and a.get('ed') == edition() else 0


def _session(j: dict, t: float) -> bool:
    """Count a paid round in the fair session (a new one after SESSION_GAP away); True while the police wait."""
    now = int(t)
    ss = j.get(SESS_KEY)
    if not (isinstance(ss, dict) and 0 <= now - ss.get('ls', -SESSION_GAP) < SESSION_GAP):
        ss = j[SESS_KEY] = dict(at=now, n=0, ls=now)
    ss['n'] = min(10**6, ss['n'] + 1)
    ss['ls'] = now
    return now - ss['at'] < GRACE_S or ss['n'] <= GRACE_ROUNDS


def _wealth_raid(j: dict, f: dict, t: float) -> dict | None:
    """Check only after a paid chance round. Reads/offline time cannot take money."""
    if f['net'] <= WEALTH_THRESHOLD or t - f.get('wealth_check_at', 0) < WEALTH_CHECK_GAP:
        return None
    f['wealth_check_at'] = int(t)  # Failed checks share the cooldown, across workers/reloads.
    if _rng.random() >= WEALTH_RAID_P:
        return None
    amount = max(0, j['wallet']) * 30 // 100
    if not amount:
        return None
    from . import journey as jr
    jr._wallet(j, -amount, KIND, '🚨 Công an kiểm tra chợ đen · Thu tiền trong ví')
    f['net'] -= amount
    f['stats']['lost'] += amount
    f['stats']['raids'] += 1
    return dict(amount=amount, wallet=j['wallet'],
                message=f'Công an kiểm tra đánh bạc! Thu {amount:,} xu trong ví.'.replace(',', '.'))


def _asset_audit(s: dict, j: dict, f: dict, t: float, raided: bool = False) -> dict | None:
    """🚨 The police's asset check (chứng minh nguồn tài sản, owner 07/10), a rule of its own next to _wealth_raid (which
    stays as it was): only after a paid chance round (reads and offline time cannot take money), with fair profit this
    edition (money_of, the Bảng vàng number) above AUDIT_FROM, new profit since the last check, AUDIT_GAP since the
    last check (journey['fair_audit']['at'], failed draws too), then AUDIT_P. It takes AUDIT_PCT of the new profit, from
    the wallet, then the bank account, never below zero (what neither holds is let go, no debt); the profit left becomes
    the next check's base. A raid on the same round comes first: what it took is already out of the profit."""
    a = j.get(AUDIT_KEY)
    a = a if isinstance(a, dict) else {}
    profit = money_of(j)[0]
    base = audit_base(j)
    gain = profit - base
    if profit <= AUDIT_FROM or gain <= 0 or t - a.get('at', 0) < AUDIT_GAP:
        return None
    j[AUDIT_KEY] = dict(ed=edition(), base=base, at=int(t))   # failed draws wait too, across workers/reloads
    if _rng.random() >= AUDIT_P:
        return None
    due = min(10**7, gain * AUDIT_PCT // 100)
    if not due:
        return None
    from . import journey as jr
    from . import bank as bk
    cash = min(max(0, j['wallet']), due)
    if cash:
        jr._wallet(j, -cash, KIND, AUDIT_LABEL)
    b = bk.get(s)
    bank = min(max(0, b['balance']), due - cash) if b and type(b.get('balance')) is int else 0
    if bank:
        b['balance'] -= bank
        bk._log(b, j['life_day'], 'acc', 'Công an thu 10% tiền lời chợ đen', -bank)
    took = cash + bank
    if took:
        f['net'] -= took
        f['stats']['lost'] += took
        f['stats']['raids'] += 1
    j[AUDIT_KEY]['base'] = profit - took
    where = ' và '.join(x for x in (cash and f'ví {_xu(cash)}', bank and f'tài khoản ngân hàng {_xu(bank)}') if x)
    msg = (f'Công an hỏi nguồn tài sản: thu 10% tiền lời mới ở chợ đen, {_xu(took)} xu ({where}).' if took else
           'Công an hỏi nguồn tài sản, nhưng ví với tài khoản trống trơn nên lần này cho qua.')
    return dict(amount=took, cash=cash, bank=bank, due=due, gain=gain, pct=AUDIT_PCT, say=POLICE_SAY,
                wallet=j['wallet'], after_raid=raided, message=msg)


# ---------------------------------------------------------------- 🍀 Lộc trời cho
# The server-wide hourly gate. storage reads it before computing a luck-round command (loc_prepare) and takes it in the
# command's own transaction (loc_claim): a retried command replays its receipt, one that lost the race is computed
# again with the gate shut. Outside storage (tools, tests of the reducer alone) the gate is shut.
_loc_gate: contextvars.ContextVar = contextvars.ContextVar('fair_loc_gate', default=False)
_loc_seen = [0.0]   # this worker's latest known grant time (any worker's): no read while it is under an hour old


def loc_prepare(db, action: str) -> None:
    """Before computing `action`: open the gate for this command when the last Lộc is LOC_GAP old (one row read)."""
    if action not in LOC_ACTIONS:
        _loc_gate.set(False)
        return
    t = now()
    if t - _loc_seen[0] < LOC_GAP:
        _loc_gate.set(False)
        return
    row = db.execute('SELECT value FROM mnl_meta WHERE key=?', (LOC_KEY,)).fetchone()
    try:
        last = float(row[0]) if row else 0.0
    except (TypeError, ValueError):
        last = 0.0
    _loc_seen[0] = max(_loc_seen[0], last)
    _loc_gate.set(t - last >= LOC_GAP)


def loc_shut() -> None:
    _loc_gate.set(False)


def loc_claim(db, result: dict | None) -> bool:
    """In the command's transaction: take the gate for a Lộc this result granted (True when none was granted). One
    atomic statement: a second worker waits for the first one's commit, then finds the row too new."""
    loc = ((result or {}).get('fair') or {}).get('loc') if isinstance(result, dict) else None
    if not loc:
        return True
    at = int(loc['at'])
    row = db.execute('INSERT INTO mnl_meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value '
                     'WHERE CAST(mnl_meta.value AS double precision) <= ? RETURNING key', (LOC_KEY, str(at), at - LOC_GAP)).fetchone()
    if row is None:
        return False
    _loc_seen[0] = max(_loc_seen[0], at)
    return True


def _loc(j: dict, f: dict, game: str, stake: int, gain: int, t: float) -> dict | None:
    """A won round (gain > 0) of a paid luck stall, the gate open: LOC_P of the time it wins LOC_MULT× its stake
    (capped at the stall's ROUND_MAX) instead of `gain`; the difference is the system's, its own Sổ ví row."""
    if gain <= 0 or not _loc_gate.get() or _rng.random() >= LOC_P:
        return None
    stake = min(stake, ROUND_MAX)
    bonus = LOC_MULT * stake - gain
    if bonus <= 0:   # the round already won as much (a bão, a big ticket): nothing to add, the gate stays open
        return None
    from . import journey as jr
    _loc_gate.set(False)
    jr._wallet(j, bonus, KIND, f'{LOC_LABEL} · {LABELS[game]}')
    f['net'] += bonus
    f['stats']['won'] += bonus
    return dict(game=game, stake=stake, mult=LOC_MULT, won=LOC_MULT * stake, bonus=bonus, at=int(t),
                message=f'🍀 Lộc trời cho! Ván này ăn ×{LOC_MULT} tiền cược: +{_xu(LOC_MULT * stake)} xu.')


class _Caught(Exception):
    """🚨 The police caught a paid round (fair_bm.arrest): the command's whole result."""
    def __init__(self, result: dict):
        super().__init__('caught')
        self.result = result


def _police(j: dict, f: dict, t: float, game: str, stake: int) -> None:
    """🕶️ Every paid round of the Chợ đen, once its checks passed and before anything is drawn: the police may raid it
    (fair_bm.BM_ARREST_P). Caught: the stake is gone, the fine, the ban for the rest of the Vietnam day; the round has
    no outcome (raises _Caught, which apply() turns into the command's result)."""
    if not bm._gate_on() or not bm._arrest_roll():
        return
    if game in f['stats']:   # the round counts on the stall's Sổ ví row ("· N ván")
        f['stats'][game] = min(10**9, f['stats'][game] + 1)
    r = bm.arrest(j, f, t, game, stake, lambda amount: _pay(j, f, game, amount))
    f['stats']['raids'] = min(10**9, f['stats']['raids'] + 1)
    got: list = []
    _grant(j, 'f_raid', got)
    fair = dict(game=game, arrest=r)
    if got:
        fair['titles'] = got
    msg = (f'🚨 Công an ập vào! Mất {_xu(stake)} xu tiền cược' + (f', nộp phạt {_xu(r["fine"])} xu' if r['fine'] else '')
           + '. Hôm nay bạn bị đuổi khỏi chợ đen.')
    raise _Caught(dict(message=msg, effects=[], fair=fair))


def _gate(need, j: dict, t: float) -> None:
    """🕶️ Inside the Chợ đen only with today's bảo kê settled, and not after an arrest (fair_bm)."""
    if not bm._gate_on():
        return
    st = bm.status(j, t)
    need(st != 'ban', bm.BANNED, 'fair_bm_ban')
    need(st in ('paid', 'robbed'), bm.NEED_IN, 'fair_bm_gate')


# What the bảo kê gate lets through: finishing what was begun (LATE), the organisers' gift, paying a loan back.
GATE_FREE = LATE + fc.LATE + ('fair_gift',)


def apply(s: dict, name: str, p: dict) -> dict:
    """`fair_*` commands (a round the police caught: its receipt)."""
    try:
        return _apply(s, name, p)
    except _Caught as c:
        return c.result


def _apply(s: dict, name: str, p: dict) -> dict:
    """`fair_*` commands. Checks everything before changing anything (the engine works on a copy anyway)."""
    from . import engine as e
    need = e.need
    j = s['journey']
    need(isinstance(p, dict), 'Dữ liệu thao tác không hợp lệ.')
    need(name in COMMANDS or name in fc.COMMANDS or name in ff.COMMANDS or name in fp.COMMANDS or name in bm.COMMANDS,
         'Thao tác chợ đen không hợp lệ.', 'unknown_action')
    need(j.get('story'), 'Chợ đen chỉ có trong hành trình.', 'not_story')
    t = now()
    opens, closes = window()
    if name in bm.COMMANDS:   # 🕶️ the bảo kê at the gate: only while the Chợ đen is open
        need(t >= opens, SOON, 'fair_closed')
        need(t < closes, CLOSED, 'fair_closed')
        return bm.apply(s, name, p, _state(j, t), t)
    if name not in GATE_FREE and opens <= t < closes:
        _gate(need, j, t)
    if name in fc.COMMANDS:
        return fc.apply(s, name, p, t, edition(), opens <= t < closes)
    if name in ff.COMMANDS:   # 🍡 a snack from the food carts: only while the fair is open
        need(t >= opens, SOON, 'fair_closed')
        need(t < closes, CLOSED, 'fair_closed')
        return ff.apply(s, p)
    if name in fp.COMMANDS:   # 📸 a photobooth ticket: only while the fair is open
        need(t >= opens, SOON, 'fair_closed')
        need(t < closes, CLOSED, 'fair_closed')
        return fp.apply(s, p)
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
            need(type(v) is int and v >= 1, 'Dữ liệu thao tác không hợp lệ.')
        stake = sum(bets.values())
        need(stake <= BC_MAX, TOO_BIG, 'fair_big')
        need(f is None or int(t * 1000) - f['last'] >= BC_GAP_MS or f['last'] > int(t * 1000),
             'Chờ chú Tám mở bát đã nha!', 'fair_slow')
        luck_p(j, f, 'bc', t, stake=stake)   # the run counters only
        _guard_round(e, f, j, t, stake, stake)
        _police(j, f, t, 'bc', stake)
        # Owner 06/10 ("ra cua nhiều quá, bị cheat, cho random lại"): three honest dice, each face 1/6, nothing
        # decided before the roll and no sure win after a losing streak (bets no longer pull the dice their way).
        dice = bc_fair_roll()
        back = bc_back(bets, dice)
        bao = next((face for face in bets if dice.count(face) == 3), None)
        st['bc'] += 1
        delta = back - stake
        _pay(j, f, 'bc', delta)
        loc = _loc(j, f, 'bc', stake, delta, t)
        if bao:
            st['bao'] += 1
            _grant(j, 'f_bao', got)
        result['fair'] = dict(game='bc', dice=dice, bets=dict(bets), stake=stake, back=back, net=delta, bao=bao)
        if loc:
            result['fair']['loc'] = loc
        result['message'] = (f'Bão {FACE_NAMES[bao].lower()}! +{delta} xu.' if bao else
                             f'Thắng {delta} xu.' if delta > 0 else 'Hòa vốn.' if delta == 0 else f'Thua {-delta} xu.')
    elif name == 'fair_xd':
        need(set(p) == {'side', 'stake'} and p.get('side') in SIDES, 'Chọn chẵn hay lẻ nha.')
        stake = p['stake']
        need(type(stake) is int and stake >= XD_MIN, f'Chiếu trong đặt từ {XD_MIN} xu nha.')
        need(stake <= XD_MAX, TOO_BIG, 'fair_big')
        wait = f['raid_until'] - int(t)
        need(wait <= 0, f'Chiếu trong vừa bị dẹp, {max(1, -(-wait // 60))} phút nữa mới bày lại. Ra trước chơi bầu cua, lô tô cho lành nha.',
             'fair_raided')
        fine = xd_fine(stake)
        want = None
        _guard_round(e, f, j, t, stake, stake + fine)
        _police(j, f, t, 'xd', stake)
        st['xd'] += 1
        probability = luck_p(j, f, 'xd', t, stake=stake)
        if _rng.random() * 100 < RAID_PCT:
            fine = min(fine, j['wallet'] - stake)
            st['raids'] += 1
            f['raid_until'] = int(t) + RAID_COOLDOWN
            _pay(j, f, 'xd', -(stake + fine))
            _grant(j, 'f_raid', got)
            result['fair'] = dict(game='xd', raid=True, side=p['side'], stake=stake, fine=fine, net=-(stake + fine), cooldown=RAID_COOLDOWN)
            result['message'] = f'Công an phường kiểm tra! Mất {stake} xu tiền cược và nộp phạt {fine} xu.'
        else:
            want = _draw_luck(j, 'xd', probability)
            coins = xd_toss(p['side'], want)
            even = sum(coins) % 2 == 0
            win = (p['side'] == 'chan') == even
            delta = stake if win else -stake
            _pay(j, f, 'xd', delta)
            loc = _loc(j, f, 'xd', stake, delta, t)
            result['fair'] = dict(game='xd', raid=False, side=p['side'], stake=stake, coins=coins, even=even, net=delta)
            if loc:
                result['fair']['loc'] = loc
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
            need(SIDE_OPEN or not sb, 'Gánh lô tô giờ không nhận cược phụ, bỏ chọn chẵn lẻ và cột rồi mua tờ nha.',
                 'fair_loto_side')
            tier, n = p['tier'], p['n']
        else:
            mode, tier, n, sb = 'thuong', 'vua', 1, {}
        cost = n * LOTO_TIERS[tier]
        stake = cost + sum(b[1] for b in sb.values())
        need(stake <= ROUND_MAX, f'Tổng tiền vé và cược phụ mỗi ván tối đa {ROUND_MAX} xu.')
        _guard_free(e, f, j, t, stake)   # no daily money or round limit (owner 03/10)
        _police(j, f, t, 'lt', stake)
        want = _draw_luck(j, 'lt', luck_p(j, f, 'lt', t, stake=stake))  # one count per purchase
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
        elif marks is not None and set(marks) <= set(rv['seq'][:at]) and sum(set(r) <= set(marks) for r in rv['cards'][ci]) < rv['need']:
            # Every mark was a called number, only the rows are short (Kinh đôi 2, Hũ 3): no fine, nothing changes.
            need(False, f'Vòng này cần đủ {rv["need"]} hàng trên một tờ. Dò tiếp rồi kinh nha!', 'fair_loto_short')
        elif marks is not None and not (set(marks) <= set(rv['seq'][:at])
                                        and sum(set(r) <= set(marks) for r in rv['cards'][ci]) >= rv['need']):
            # Kinh hụt: a mark that was never called
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
            cost = rv['price'] * rv['n']
            loc = _loc(j, f, 'lt', cost, prize - cost, t)
            _grant(j, 'f_loto', got)
            if rv['mode'] in ('doi', 'nguoc', 'dem'):
                _grant(j, dict(doi='f_kinh2', nguoc='f_nguoc', dem='f_hu')[rv['mode']], got)
            result['fair'] = dict(game='lt', won=True, prize=prize, mode=rv['mode'], **({} if marks is not None else dict(row=row)))
            if loc:
                result['fair']['loc'] = loc
            result['message'] = f'Kinh! Bạn thắng {prize} xu.'
    elif name == 'fair_loto_fold':
        need(not p, 'Dữ liệu thao tác không hợp lệ.')
        lt = f['loto']
        if lt and lt['stage'] == 'play':
            _loto_lost(f, lt)
        result['fair'] = dict(game='lt', folded=True)
    elif name == 'fair_oaq_start':
        need(set(p) == {'lv'} and p.get('lv') in oaq.LEVELS, 'Chọn người chơi cùng nha.')
        for key in ('fair_run', 'fair_run2', 'fair_run3'):
            j.pop(key, None)
        o = f['oaq']
        if o and o['stage'] == 'play':
            o['stage'] = 'lost'   # a new game gives the old one up
        _day(f, t)
        st['oaq'] += 1
        f['oaq'] = dict(lv=p['lv'], g=oaq.new_game(), at=int(t), stage='play')
        trace: list = []
        if p['lv'] in OAQ_FIRST:   # he opens: the board comes back on the player's turn, as older builds expect
            g = f['oaq']['g']
            c, d = oaq.ai_move(g, p['lv'], _rng)
            trace.append(['turn', 1, c, d])
            oaq.play(g, 1, c, d, trace)
            oaq.begin_turn(g, 0, trace)   # never the end after one move (each row still has dân)
        result['fair'] = dict(game='oaq', started=True, view=oaq_view(f['oaq']), trace=trace)
        result['message'] = (f'Bày bàn ô ăn quan với {OAQ_PEOPLE[p["lv"]][0]}. '
                             + ('Ông đi trước rồi, tới cháu nha!' if p['lv'] in OAQ_FIRST else 'Bạn đi trước nha!'))
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
        need(not (r and 0 <= ms - r['at'] < RING_GAP_MS), 'Từ từ thôi nha, cô Tư đang nhặt vòng!', 'fair_slow')
        _day(f, t)
        f['earn']['ring_n'] = min(RING_DAY, f['earn']['ring_n'] + 1)   # a counter only, bounded for older validators
        st['ring'] += 1
        f['ring'] = dict(rs=_rng.getrandbits(31), at=ms, stage='play')
        _set_chance(j, 'ring', f['ring'], luck_p(j, f, 'ring', t))
        result['fair'] = dict(game='ring', round=ring_view(f['ring'], t, j))
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
            chance = _chance(j, 'ring', r)
            if chance is not None:
                hits = [-1] * ring.RINGS
                if _draw_luck(j, 'ring', chance['p'] / 1000):
                    n = 1 + _rng.randrange(ring.RINGS)
                    hits = ring.land(ring.params(r['rs']), p['taps'], n)
            else:
                hits = ring.judge(ring.params(r['rs']), p['taps'])
            n = sum(h >= 0 for h in hits)
            st['ring_hits'] += n
            prize = _earn(j, f, 'ring', n * RING_HIT + (RING_ALL if n == ring.BOTTLES else 0))
            if n == ring.BOTTLES:
                _grant(j, 'f_ring', got)
            full = n * RING_HIT + (RING_ALL if n == ring.BOTTLES else 0)
            result['fair'] = dict(game='ring', hits=hits, n=n, prize=prize, capped=prize < full)
            result['message'] = f'Trúng {n}/{ring.BOTTLES} cổ chai' + (f', +{prize} xu.' if prize else '.')
    paid_round = name in ('fair_bc', 'fair_xd', 'fair_xs') or name == 'fair_loto_kinh' and result['fair'].get('won')
    quiet = paid_round and _session(j, t)   # B6: the session's first minutes / rounds, no police check
    if paid_round and not quiet and not result['fair'].get('raid'):
        seizure = _wealth_raid(j, f, t)
        if seizure:
            result['fair']['wealth_raid'] = seizure
            result['message'] = (result['message'] + ' ' + seizure['message']).strip()
        audit = _asset_audit(s, j, f, t, bool(seizure))   # 07/10: a separate rule, after the raid
        if audit:
            result['fair']['audit'] = audit
            result['message'] = (result['message'] + ' ' + audit['message']).strip()
    loc = (result.get('fair') or {}).get('loc')
    if loc and name != 'fair_xs':   # the vé cào's message says nothing before the silver is scratched
        result['message'] = (result['message'] + ' ' + loc['message']).strip()
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
            game = next((g for g, name in LABELS.items() if label.startswith((name, LABELS_OLD[g]))), None)
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
                rules=dict(bc_open=BC_OPEN_MS, cap=DAY_CAP, bc_max=BC_MAX, bao=BAO, xd_min=XD_MIN, xd_max=XD_MAX, fine_min=FINE_MIN,
                           loto_price=LOTO_PRICE, loto_prize=LOTO_PRIZE, loto_npcs=LOTO_NPCS, faces=list(FACES),
                           oaq_prize=dict(OAQ_PRIZE), oaq_people={k: list(v) for k, v in OAQ_PEOPLE.items()}, quan=oaq.QUAN,
                           quan_non=oaq.QUAN_NON, ring_hit=RING_HIT, ring_all=RING_ALL, rings=ring.RINGS, ring_tol=ring.TOL,
                           ring_day=RING_DAY, ring_left=RING_DAY, oaq_turn=1, xd_fine_div=FINE_DIV, nocap=1, ring_chance=True,
                           # owner 08/10 "số liệu k hiển thị ra": no win rate reaches the client (no luck_pct: an
                           # older client then leaves its 🍀 line out)
                           run_gap_min=RUN_GAP // 60, run_switch=SWITCH_ROUNDS, run_switch_min=SWITCH_MIN,
                           audit_pct=AUDIT_PCT,
                           audit_from=AUDIT_FROM, loc_mult=LOC_MULT),
                # the stall whose run has cooled its luck ("Vận đang nguội"), or None; under a new name and without its
                # rate, so an older client (which printed "khoảng N% thắng" from `cold`) shows nothing
                cool=cold(j, t),
                oaq=oaq_view(o) if o and (o['stage'] == 'play' or t - o['at'] < 6 * 3600) else None,
                ring=ring_view((f or {}).get('ring'), t, j),
                loto=loto, stats={k: st.get(k, 0) for k in STATS},
                # 🕶️ the bảo kê at the gate and today's standing (absent from older servers: no gate on the client)
                bm=bm.public(j, t),
                food=ff.public(s),   # 🍡 the food carts' menus (absent from older servers: the carts only say a line)
                photo=fp.public(s),   # 📸 the photobooth's ticket (absent from older servers: the client leaves the booth out)
                # 🗡️ phóng dao, in the phi tiêu's place (absent from older servers: the client then leaves the stall
                # out; `darts` is gone, so an older client leaves the phi tiêu out)
                knife=knife_public(j, f, t),
                # 🎟️ vé số cào (absent from older servers: the client then leaves the stall out)
                scratch=dict(tiers=list(scratch.TIERS), names={str(k): v for k, v in scratch.NAMES.items()},
                             cells=scratch.CELLS, match=scratch.MATCH, mults=list(scratch.MULTS)),
                # 🎱 the gánh lô tô: the vòng of this minute and the next nine, the tiers and side bets, today's tally
                # (hut_max 0: no limit on Kinh hụt; the older client showed it as "hụt N lần là nghỉ ván")
                ganh=dict(modes=[[slot + i, mode_of(slot + i)] for i in range(10)], names=dict(MODE_NAMES),
                           # side_stakes [] and side False: no new side bets (SIDE_OPEN; an older client still shows them,
                           # the server then says so)
                           tiers=dict(LOTO_TIERS), cards=LOTO_CARDS, max_stake=ROUND_MAX, bay=list(BAY_NUMS),
                           side_stakes=list(SIDE_STAKES) if SIDE_OPEN else [], side=SIDE_OPEN,
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
                levels=knife.LEVELS, gap=knife.GAP, chance=False,
                draw=knife.DRAW_W, fly=knife.FLY_MS, impact=knife.IMPACT, min_tap=knife.MIN_TAP, level_ms=knife.LEVEL_MS,
                hot=knife.heat(_today(f, t)['net']), **{x: k.get(x, 0) for x in ('n', 'w', 'b', 'top')},
                run=_kn_view_run(k.get('run'), t, j))


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
    bm.validate(j)
    if 'fair_balance' in j:
        from .engine import need, integer
        balance = j['fair_balance']
        need(isinstance(balance, dict) and set(balance) <= set(CHANCE_GAMES), 'Chuỗi kết quả chợ đen không hợp lệ.', 'invalid_save')
        for streak in balance.values():integer(streak, -4, 4)
    if AUDIT_KEY in j:   # 07/10, optional: an older server ignores it (the journey keeps unknown blocks)
        from .engine import need, integer
        a = j[AUDIT_KEY]
        need(isinstance(a, dict) and set(a) == {'ed', 'base', 'at'} and isinstance(a['ed'], str) and len(a['ed']) <= 12,
             'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        integer(a['base'], -10**10, 10**10)
        integer(a['at'], 0, 10**11)
    if COOL_KEY in j:   # 07/10, optional: an older server keeps it as is
        from .engine import need, integer
        c = j[COOL_KEY]
        need(isinstance(c, dict) and set(c) <= set(COOL_GAMES), 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        for r in c.values():
            need(isinstance(r, dict) and set(r) == {'n', 'at', 'sw', 'st'}, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
            integer(r['st'], 0, ROUND_MAX)
            integer(r['n'], 0, 10**6)
            integer(r['at'], 0, 10**11)
            integer(r['sw'], 0, SWITCH_ROUNDS)
    if SESS_KEY in j:   # 07/10 (B6), optional: an older server keeps it as is
        from .engine import need, integer
        ss = j[SESS_KEY]
        need(isinstance(ss, dict) and set(ss) == {'at', 'n', 'ls'}, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        integer(ss['at'], 0, 10**11)
        integer(ss['n'], 0, 10**6)
        integer(ss['ls'], 0, 10**11)
    if 'fair_run3' in j:
        from .engine import need, integer
        r = j['fair_run3']
        need(isinstance(r, dict) and set(r) == {'g', 'n', 'at'} and r['g'] == 'ring', 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        integer(r['n'], 0, 10**6)
        integer(r['at'], 0, 10**11)
    if 'fair_kn_skill' in j:
        from .engine import need, integer
        rules = j['fair_kn_skill']
        need(isinstance(rules, dict) and set(rules) == {'at', 'seed', 'difficulty'}, 'Dữ liệu phóng dao không hợp lệ.', 'invalid_save')
        integer(rules['at'], 0, 10**14)
        integer(rules['seed'], 0, 2**31)
        integer(rules['difficulty'], 135, 135)
    if 'fair_kn_soft' in j:
        from .engine import need, integer
        soft = j['fair_kn_soft']
        need(isinstance(soft, dict) and set(soft) == {'at', 'seed'}, 'Dữ liệu phóng dao không hợp lệ.', 'invalid_save')
        integer(soft['at'], 0, 10**14)
        integer(soft['seed'], 0, 2**31)
    if 'fair_chance' in j:
        from .engine import need, integer
        c = j['fair_chance']
        need(isinstance(c, dict) and set(c) <= {'kn', 'ring'}, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        for game, r in c.items():
            need(isinstance(r, dict) and {'at', 'seed', 'p'} <= set(r) <= ({'at', 'seed', 'p', 'difficulty'} if game == 'kn' else {'at', 'seed', 'p'}), 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
            if 'difficulty' in r:
                integer(r['difficulty'], 135, 150)
                need(r['difficulty'] in (135, 150), 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
            integer(r['at'], 0, 10**14)
            integer(r['seed'], 0, 2**31)
            # New repeated ring rounds may reach 40%; older locked odds stay valid.
            integer(r['p'], 400, 700)
    if 'fair_run' in j:
        from .engine import need, integer
        r = j['fair_run']
        need(isinstance(r, dict) and set(r) == {'g', 'n', 'at'} and r['g'] in RUN_GAMES, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        integer(r['n'], 0, 10**6)
        integer(r['at'], 0, 10**11)
    if 'fair_run2' in j:
        from .engine import need, integer
        r = j['fair_run2']
        need(isinstance(r, dict) and set(r) == {'g', 'n', 'at'} and r['g'] in RUN_GAMES2, 'Dữ liệu chợ đen không hợp lệ.', 'invalid_save')
        integer(r['n'], 0, 10**6)
        integer(r['at'], 0, 10**11)
    if KN_KEY in j:
        _kn_validate(j[KN_KEY])
    if 'fair' not in j:
        return
    from .engine import need, integer
    bad = 'Dữ liệu chợ đen không hợp lệ.'
    f = j['fair']
    need(isinstance(f, dict) and set(KEYS) <= set(f) <= set(KEYS + KEYS_OPT) and f['v'] == VERSION, bad, 'invalid_save')
    need(isinstance(f['date'], str) and len(f['date']) <= 10, bad, 'invalid_save')
    if f['date']:
        try:
            datetime.date.fromisoformat(f['date'])
        except ValueError:
            need(False, bad, 'invalid_save')
    # A purchased 1,000-xu ticket can return 50,000, and pending prizes may settle
    # beyond the existing 1e6 new-purchase guard. Preserve every earned payout.
    integer(f['net'], -10**9, 10**9)
    integer(f['rounds'], 0, ROUNDS_DAY)
    integer(f['last'], 0, 10**14)
    integer(f['raid_until'], 0, 10**11)
    if 'wealth_check_at' in f:
        integer(f['wealth_check_at'], 0, 10**11)
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
        need(LOTO_TIERS[lt.get('tier', 'vua')] * lt.get('n', 1) + sum(b[1] for b in sb.values()) <= ROUND_MAX,
             bad, 'invalid_save')
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
    bad = 'Dữ liệu chợ đen không hợp lệ.'
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
    need(len(run['tp']) <= (max(x[0] for x in knife.DIFF.values()) * 3 + 1) // 2, bad, 'invalid_save')
    for v in run['tp']:
        integer(v, 0, knife.LEVEL_MS)
