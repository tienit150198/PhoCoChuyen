# 🕶️ Chợ đen (was Hội chợ): ordinary odds, returns and free entry (updated 22/10/2026)

Owner 08/10: "mở hội chợ nhé, tỷ lệ chỉnh lại làm sao cho phù hợp, đảm bảo nhà cái luôn thắng", then "chợ đen để
luôn ở ngoài nhé". This edition opened on 09/10 (`FAIR_START` 2026-10-09, edition `fair20261009`). Its entry stays in
sight: a 🏮 Hội chợ chip in the town's top bar and a main menu entry. The 🏮 gate on Phố hàng rong is still there too.

## Current ordinary odds — 22/10/2026 (+3 points)

Owner 22/10: "tăng nhẹ tỷ lệ thắng của chợ đen luôn nhé". Every band of the 16/10 draw below gains 3 points; the bands
themselves (`HOT_FROM` 100,000, `UP_FROM` 30,000, `BACK_MAX` 5,000), the pace cut (−5 / −12 points), `P_MIN` 40%, the
four-win cool-off (`WIN_P_LOW` 45%), the payouts, bầu cua's honest dice, đua chó's prices and the police are unchanged.

| Today's net | 16/10 draw | 22/10 draw | Chiếu trong (0.75×) | Lô tô (1.8×) | Vé cào (1.775×) |
|---|---:|---:|---:|---:|---:|
| ≥ 100,000 xu (`P_HOT`) | 45% | **48%** | 78.75% → 84.0% | 81.0% → 86.4% | 79.9% → 85.2% |
| > 30,000 xu (`P_UP`) | 52% | **55%** | 91.0% → 96.25% | 93.6% → 99.0% | 92.3% → 97.6% |
| otherwise (`BASES`) | 57% | **60%** | 99.75% → 105.0% | 102.6% → 108.0% | 101.2% → 106.5% |
| winning back, stake ≤ min(−net, 5,000) (`P_BACK`) | 60% | **63%** | 105.0% → 110.25% | 108.0% → 113.4% | 106.5% → 111.8% |
| a stake ≥ 50,000 xu, any net (`BIG_WIN_P`, a cap) | 40% | **43%** | 70.0% → 75.25% | 72.0% → 77.4% | 71.0% → 76.3% |

Expected money back per xu staked, one ordinary round, before the streak cool-off, Lộc and the police. With the pace
cut a fast player draws 55% / 48% at net 0 (96.25% / 84.0% on chiếu trong).

**The house edge.** Above 30,000 xu up today every stall keeps its edge (96–99%, then 84–86%), and a 50k+ stake stays
far below even. The 0–30,000 band now returns 105–108% (lô tô and vé cào were already 102.6% / 101.2% there on 16/10),
so a day's expected gain is bounded by that band: a player who stops once 30,000 up today keeps at most about that
plus one win's overshoot; one who plays on draws 55% and gives it back. Normal play is now slightly in the player's
favour (owner 16/10: "đừng cho lỗ nhưng đừng cho lãi nhiều"; 22/10: a little more). If the owner wants the edge back at
the base band with the higher win rate, the payouts would have to drop (chiếu trong 0.66×, lô tô 1.6×, vé cào ~1.65×).

`python scripts/sim_fair_odds.py` (1,000,000 rounds a pattern, seed 1), before police:

| Stall | Exact .60 | +Lộc | Fresh | Spam (1 s) | Press | Fresh + Lộc |
|---|---:|---:|---:|---:|---:|---:|
| Bầu cua | 100.00% | 101.10% | 99.81% | 95.47% | 99.90% | 101.39% |
| Chiếu trong | 105.00% | 106.67% | 102.44% | 83.71% | 105.00% | 104.10% |
| Lô tô | 108.00% | 109.66% | 105.32% | 86.13% | 107.89% | 106.95% |
| Vé cào | 106.50% | 108.17% | 103.91% | 84.95% | 106.42% | 105.70% |

Lô tô's 2-xu tờ (pays 3): 90.0%. 300 lô tô card rounds: drawn for the player 60.21%, cards agree 100%.

`python scripts/sim_bm_strategies.py` (4,000 Vietnam days a strategy, seed 1; no police, no Lộc), 16/10 → 22/10:

| Strategy | Rounds/day | Won | Mean day net | RTP | P(day > 0) |
|---|---:|---:|---:|---:|---:|
| Chiếu trong normal (1,000 xu, 8 s apart) | 200 | 57.14% → 59.18% | −8 → 7,132 | 100.00% → 103.57% | 47.25% → 75.92% |
| Chiếu trong martingale (≤ 49,000) | 200 | 55.89% → 57.86% | −5,796 → 15,690 | 98.95% → 103.13% | 66.47% → 77.85% |
| Chiếu trong lose small then 45,000 | 200 | 53.43% → 56.02% | −13,400 → 15,933 | 98.31% → 103.28% | 94.45% → 97.82% |
| Chiếu trong bot (5,000 xu every 3 s) | 3,000 | 47.87% → 50.66% | −2,434,388 → −1,701,553 | 83.77% → 88.66% | 0% → 0% |
| Chiếu trong probe (10 xu, then 49,000) | 400 | 55.02% → 56.63% | −101,012 → −38,115 | 94.22% → 97.96% | 36.23% → 49.80% |
| Vé cào normal / fast | 200 / 3,000 | 59.42% / 50.56% | 1,084 / −30,691 | 105.42% / 89.77% | 70.40% / 0% |
| Lô tô normal / fast | 200 / 3,000 | 59.02% / 50.69% | 1,247 / −26,247 | 106.23% / 91.25% | 87.45% / 0% |
| Bầu cua, đua chó | unchanged | | | | |

Fast play, bots and big stakes still lose. The 16/10 section below is the shape these numbers come from.

## Ordinary odds — 16/10/2026 (bands +3 points since 22/10, above)

Owner 16/10: "tỷ lệ là 55 - 60% thôi … đừng cho lỗ nhưng đừng cho lãi nhiều", "phải tính cả trường hợp người ta
cheat, hoặc chơi kiểu ít tiền thua sau đó chơi tiền lớn, hoặc cheat spam ăn nhiều", "đừng giới hạn 600 ván, thay vì đó
là mình cho spam 1 game nhanh quá thì thua cao hơn". This supersedes the 14/10 one-round-then-decay rule (below) and
the 15/10 boosts (the day's first round at 65% and the 70% windows: `fair_boost.rate` now always returns `None`;
xóc đĩa's 3 s gap between rounds stays).

**The draw** (chiếu trong `xd`, lô tô `lt`, vé cào `xs`; `fair.luck_p` → `base_p`, `pace_cut`), by today's Chợ đen
net (all paid stalls, Vietnam day, before this round):

| Today's net | Draw |
|---|---:|
| ≥ 100,000 xu (`HOT_FROM`) | 45% (`P_HOT`) |
| > 30,000 xu (`UP_FROM`) | 52% (`P_UP`) |
| < 0 and stake ≤ min(−net, 5,000) (`BACK_MAX`) | 60% (`P_BACK`, winning back a loss with small stakes) |
| otherwise | 57% (`BASES`) |

**The pace**, per stall: this player's rounds at that stall in the last 60 s (`PACE_S`), this one included, kept in
the optional journey key `fair_pace` = `{game: [epoch seconds, at most 20]}` (validated: games `bc xd lt xs dg`,
whole seconds). Up to 10: nothing; 11–15: −5 points; 16 or more: −12 points. Never below 40% (`P_MIN`). The stall
shows "🥶 Chơi dồn dập quá, vận đang nguội. Chậm tay lại chút là vận ấm lại." when its next round would be slowed
(`public.fair.cool` = `{game, pace: true, n, gap: 1}`; no number). The round-by-round decay (`RUN_STEP`) no longer
lowers xd/lt/xs; `fair_cool` is still written and validated (an older server reads it; the free ném vòng still cools
by it). No daily round cap.

**Unchanged:** a stake of 50,000 xu or more draws at most 40% (`BIG_WIN_P`); four wins in a row cool the next draws to
45% (`WIN_P_LOW`); the police; 🍀 Lộc; ném vòng; the golden-days code (its 70% draw still wins over the streak cap).

**Payouts:**

- Chiếu trong: a win pays `stake + floor(stake × 75 / 100)` (`XD_PAY_PCT`, the house keeps 25%).
- Lô tô: every mode pays 1.8× the tờ (`LOTO_PAY` 18).
- Vé cào: a won ticket pays, per 1,000 won tickets, ×1.5 (800), ×2 (140), ×3 (40), ×5 (15), ×20 (5): mean 1.775×,
  rounded down (`fair_scratch.amount`; the 2-xu ticket's ×1.5 pays 3). No refund prize any more.
- Bầu cua: honest dice; a bão (three of the bet face) pays 20:1 (`BAO`), 10:1 (`BAO_LOW`) when today's net is ≥
  100,000 or the bầu cua pace is 11+ (`bc_bao`; the receipt's `bao_x` and `bc_back` use the same value).
- Đua chó (superseded the same night, owner "tỷ lệ ăn cao quá … giảm 5% so với hiện tại thôi": `CLASSES` (29, 39, 52, 78, 105, 190)
  = 92.8–95.0%, `OLD` (28, 37, 49, 74, 100, 180) = 88.2–90.0%; the figures below are the earlier ones): about 5% more per class (`fair_dog.CLASSES`, table below); the 15/10 prices (`OLD`) when the đua chó pace
  is 11+ or today's net ≥ 100,000 (`slow_odds`; the board shows the prices the player's next race gets).

### Exact single-round return before police

Expected money back per xu staked, one ordinary round, no streak cap, lô tô with a timely Kinh, no police. Lộc
assumes its server gate is always open (`python scripts/sim_fair_odds.py`).

| Stall | 57% | +Lộc | 60% (winning back) | 52% (> 30k up) | 45% (≥ 100k up) |
|---|---:|---:|---:|---:|---:|
| Bầu cua (bão 20) | 100.00% | 101.10% | — | — | bão 10: 95.37% |
| Chiếu trong (0.75×) | 99.75% | 101.33% | 105.0% | 91.0% | 78.75% |
| Lô tô (1.8×) | 102.60% | 104.17% | 108.0% | 93.6% | 81.0% |
| Vé cào (1.775×) | 101.17% | 102.76% | 106.5% | 92.3% | 79.9% |
| Đua chó, best dog | 100.00% | 100.00% | — | — | old prices 92.8–95.0% |

Lô tô's 2-xu tờ (pays 3) returns 85.5%; a random dog 98.47%, the favourite 96%.

### 16/10 verification: `python scripts/sim_fair_odds.py 300000`

| Stall | Fresh | Spam (1 s) | Press | Fresh + Lộc |
|---|---:|---:|---:|---:|
| Bầu cua | 100.02% | 95.41% | 100.02% | 101.43% |
| Chiếu trong | 97.97% | 78.70% | 99.72% | 99.97% |
| Lô tô | 100.69% | 80.95% | 102.35% | 101.90% |
| Vé cào | 99.05% | 80.25% | 101.38% | 100.83% |
| Đua chó (random dog) | 97.74% | 94.31% | 98.35% | 99.18% |

Fresh is lower than the exact 57% column because of the four-win cool-off (≈ 98.2% of it). 300 lô tô card rounds:
drawn for the player 57.62%, cards agree 100%.

### 16/10 strategies per Vietnam day: `python scripts/sim_bm_strategies.py` (4,000 days, seed 1)

Every round through the real code (net bands, pace, 50k cap, streak cool-off, payouts); no police, no Lộc.

| Strategy | Rounds/day | Won | Mean day net | RTP | P(day > 0) |
|---|---:|---:|---:|---:|---:|
| Chiếu trong normal (1,000 xu, 8 s apart) | 200 | 57.14% | −8 | 100.00% | 47.25% |
| Chiếu trong martingale (1,000 doubled after a loss, ≤ 49,000) | 200 | 55.89% | −5,796 | 98.95% | 66.47% |
| Chiếu trong lose small then 45,000 | 200 | 53.43% | −13,400 | 98.31% | 94.45% |
| Chiếu trong bot (5,000 xu, every 3 s) | 3,000 | 47.87% | −2,434,388 | 83.77% | 0% |
| Chiếu trong probe (10 xu until 3 wins, then 49,000) | 400 | 55.02% | −101,012 | 94.22% | 36.23% |
| Vé cào normal / fast | 200 / 3,000 | 57.28% / 47.82% | 326 / −45,350 | 101.63% / 84.88% | 51.70% / 0% |
| Lô tô normal / fast | 200 / 3,000 | 56.87% / 47.93% | 475 / −41,174 | 102.37% / 86.28% | 65.15% / 0% |
| Bầu cua normal / fast | 200 / 3,000 | 42.06% / 42.15% | −671 / −133,605 | 99.66% / 95.55% | 44.52% / 4.00% |
| Đua chó normal / fast | 200 / 3,000 | 16.67% / 16.68% | −3,468 / −186,612 | 98.27% / 93.78% | 43.60% / 8.50% |

Normal play is about even (the owner's "đừng cho lỗ nhưng đừng cho lãi nhiều"); lô tô and vé cào at a calm pace sit
slightly above 100% under these rules. Fast play, a bot and big stakes after a probe all lose.

## Superseded ordinary odds — 14/10/2026

The latest owner instruction supersedes the historical requirement that every paid stall always have a house edge.
Only chiếu trong (`xd`), lô tô (`lt`) and vé cào (`xs`) change: **one initial round at 55% per run**, then subtract
1.5 percentage points on each subsequent round. The first ten draws are **55%, 53.5%, 52%, 50.5%, 49%, 47.5%,
46%, 44.5%, 43%, 41.5%**. Round 11 reaches the existing floor: **40.4% xd**, **40% lt/xs**, and stays there.
`RUN_FREE = 1`; ném vòng alone keeps `RING_RUN_FREE = 10`, its .503 base and its existing decay.

- Existing `fair_cool` history is retained, including after reload; this release does not grant every player a new first round.
- Reset behavior is unchanged: the elapsed whole-second gap must be **greater than 600 seconds** (exactly 600 remains
  the same run), or three qualifying paid rounds at other stalls must occur since the last round there. Each must
  stake at least `max(20, ceil(last saved stake / 4))`; free/skill rounds and smaller bets do not qualify.
- Four consecutive wins still cap the next ordinary draw at 45%, without raising an already lower rate. A stake
  **at least 50,000 xu** still caps xd/lt/xs at 40%, including during the golden-days event. Existing stake menus remain.
- The one-shot golden-days 70% event and its persisted window are unchanged. These figures describe ordinary play
  outside that event. Purchased scratch tickets and locked ring rounds keep their original outcomes/rates.
- Payouts are unchanged. Ordinary scratch wins include refunds; `PRIZES` still has conditional mean **1.801×**.
  Bầu cua keeps honest dice, dog racing fixed odds, and knife/oan-quan skill rules. No public probability is added.

### Exact single-round return before police

This is expected money returned divided by stake, **not the chance of net profit**. It assumes a fresh ordinary
round with no four-win streak cap and, for lô tô, correct marks and timely Kinh. It excludes all police enforcement
and fines. Lộc is shown separately assuming its server gate is always open; actual hourly gating can lower it.

| Stall | Exact initial RTP | With always-open Lộc gate |
|---|---:|---:|
| Bầu cua | 95.370370% | 96.474537% |
| Chiếu trong | **110%** (`2 × .55`) | 111.485% |
| Lô tô, best tier | **115.5%** (`2.1 × .55`) | 116.9685% |
| Vé cào | **99.055%** (`1.801 × .55`) | 99.51238% |
| Đua chó, best dog | 95% | 95% |

Lô tô tickets whose payout rounds to 2× return 110% on the first round. The new xd/lt figures mean that
fresh or selectively larger warm bets **can exceed 100% expected return**. Cooling repeated play below 100%
does not establish a house edge for every strategy.

`scripts/sim_fair_odds.py` reports these exact values and Monte Carlo using real draw and payout functions.
It deliberately omits all enforcement: the actual xd raid requires `bm.arrest_p(f, stake) > 0`; an unconditional
raid on every simulated small bet would incorrectly reduce the before-police result.
The patterns are fresh (pause >600 s each round, 100 xu), spam (one round each second, 100 xu), and press
(pause >600 s, 1,000 xu when the streak is warm, 10 xu xd / 2 xu lt/xs when cooled). Pauses reset repetition,
but preserve the four-win cap, so repeated fresh results are lower than the exact single fresh round.
The long-run fresh win probability is approximately .54238645: RTP 108.4773% xd, 113.9012% lt,
97.6838% xs before Lộc. At the spam floor, expected RTP is 80.8% xd, 84% lt and 72.04% xs.
Finite samples vary, especially scratch jackpots; tests compare simulation to the relevant expectation.

### 14/10 verification sample

`python scripts/sim_fair_odds.py 1000000` (default seed 1; 1,000,000 rounds per pattern):

| Stall | Fresh | Spam | Press | Fresh + Lộc |
|---|---:|---:|---:|---:|
| Bầu cua | 95.24% | 95.47% | 95.21% | 96.63% |
| Chiếu trong | 108.50% | 80.90% | 110.01% | 110.07% |
| Lô tô | 113.92% | 84.04% | 115.39% | 115.31% |
| Vé cào | 97.49% | 72.14% | 98.73% | 98.07% |
| Đua chó (random dog) | 93.52% | 93.92% | 93.76% | 94.09% |

20,000 additional lô tô card rounds agreed with their drawn outcome in 100% of cases; 55.66% were drawn for the player.
These are before-police samples under the current ordinary rules, not a guarantee for a particular player.

The dated tables and change notes below are historical; the 16/10 section above defines the current rules.

## No end (owner 09/10: "chợ đen mở mãi đi, k có thời hạn nhé")

- **Open for good.** `FAIR_DAYS` is 0 (`fair.forever()`): `window()` closes at `fair.NEVER` (2100), so no command is
  refused as `fair_closed` once the edition has opened, and `api.state.fair.forever` is true (`closes` stays a number,
  `NEVER`, so a client from before this change counts down years instead of a few minutes until it reloads). The client
  then shows no countdown ("Chợ đen · đang mở" in the header, nothing on the Hành trình banner). An edition with an end
  is still possible: `MNL_FAIR_DAYS` > 0 (the tests of the closing rules use it).
- **Same edition.** `fair20261009` goes on: the saves' fair money and days, the Bảng vàng `fair20261009xu`, the
  gift (once per edition) and the police's mark all carry on. Nothing in the save changes.
- **Titles weekly.** With no end there is no end-of-edition settlement. Instead `fair_board.settle` crowns every
  Monday 00:00 (Vietnam, + `GRACE`): the board as shown then, Top 1 👑 Vua trò chơi, Top 2–10 🎪 Cao thủ chợ đen, as
  before (`live_effects` titles, kept for good). Once per week (`leaderboard_meta` `fair:fair20261009@<Monday>`); a
  player crowned again gets no second row (the row id is per edition, title and player). The board is not reset each
  week: it is the edition's running total. The first crowning is Monday 12/10. A server that missed a Monday crowns
  only the latest one. `GET /api/leaderboard?board=fair20261009xu` shows the latest winners (`fair.weekly`,
  `fair.crowned`, `fair.next`).
- **Vay nóng.** There is no close to collect a loan at: it waits until the player pays it back, and no new loan until
  then (one at a time, as before). A `debt` left from an earlier edition is still taken from later income.
- **Rollback.** A release from before this change (1.9.29 / 1.9.30, `FAIR_DAYS` 5) sees the edition close on 14/10
  00:00: from then it refuses the stalls, collects open loans and crowns the end once (`fair:fair20261009`). Saves stay
  valid both ways (nothing new is written).

## Historical return tables — 07–11/10 (superseded)

The table gives the upper return per xu staked for a fresh run with perfect play, before the separate Chợ đen arrest
roll. Cool-off, spam decay and late Kinh claims lower this return. Canceled arrests retain their stake; their effect
is described below and does not change the stalls' draw probabilities.
The figures come from `scripts/sim_fair_odds.py` (`exact()`), which also checks them on 10^6 real-draw rounds per stall.
`tests/test_fair_house_edge.py` runs the same checks on smaller samples.

| stall | before (07/10 rules) | 10/10 rules | 10/10 with 🍀 Lộc gate always open | 10^6 rounds, 10/10 rerun (fresh / spam / press) |
|---|---|---|---|---|
| 🦀 Bầu cua (honest dice, bão 10:1) | 95.4% (Lộc: 100.9%) | 95.4% | 96.5% | 95.2% / 95.5% / 95.2% |
| 🕯️ Chiếu trong (even money, 0.88% raids) | 100.7% (Lộc: 107.5%) | 98.0% | 99.3% | 96.5% / 79.7% / 96.9% (before 11/10 cancellation change) |
| 🎱 Lô tô (Kinh 2.1× the tờ) | 105.6% (2/5-xu tờ 100.6%; Lộc: 112.3%) | 96.6% (2/5-xu tờ 92.0%) | 97.8% | 96.5% / 84.0% / 96.5% |
| 🎟️ Vé cào | 80.0% | 91.9% | 92.3% | 91.2% / 72.1% / 91.7% |
| 🐕 Đua chó (09/10, fixed odds; the outsider ×19 at best) | – | 95.0% (favourite 92.8%) | 95.0% | 93.5% / 93.9% / 93.8% (a dog at random: 93.85%) |
| 🎲 Lô tô side bets (chẵn/lẻ, cột) | 94–98% blind; **107.7% / 163.8%** after seeing the minute's calls | closed | – | – |

The 10/10 rerun of `python scripts/sim_fair_odds.py 1000000` also returned 96.63%, 97.82%, 97.58%,
91.58% and 94.09% respectively for fresh rounds with Lộc. All simulated patterns stayed below 100%; 20,000 lô tô
rounds agreed with their server draw in 100% of cases. A finite sample can differ from the exact expectation.
These are historical 10/10 samples, not a rerun of the 11/10 fine rules. The historical 11/10 simulator modeled xóc đĩa upper return as
98.0176%, or 99.3289576% with the Lộc gate always open. A dẹp chiếu now cancels the stake, so the formula adds the
raid probability: `(1 − r) × 2 × p + r`, before its small fine. That historical simulator retained the canceled stake and charged
a bounded fine for a representative 100,000-xu wallet. The current before-police simulator excludes this roll entirely.

How the three betting patterns play:

- **fresh:** a long pause before every round.
- **spam:** one round a second at one stall.
- **press:** 1000 xu while the stall is warm, 10 xu once it has cooled.

## Historical changes through 11/10 (odds superseded above)

- **11/10 small compulsory losses:** each arrest/check event takes at most 2% of the affected wallet, at most
  2,000 xu, retaining 100 xu (or the entire balance if below 100). Wealth and asset checks on one paid round share
  one ceiling. There is no bank/savings fallback. Unplayed arrested bets are canceled; an already-paid knife
  stake is refunded once, with its loss reversed rather than recorded as winnings. Ông Hai's prize remains.
  Ordinary played losing bets, draw probabilities, cooldowns, watch enforcement, jail days and awards are unchanged.
  The optional `journey.fair_kn_stake` marker preserves the original stake day and cancellation receipt across
  reloads without adding keys to the old fair/run schema. New runs reverse the correct daily counters across
  midnight. A pre-update run already beyond level 1 may have no recoverable original stake date: its wallet,
  edition loss statistics and weekly ranking are corrected, but its daily net/cap debit is conservatively retained.

- **10/10 scope:** only the base win draws of chiếu trong, lô tô and vé cào increased. Skill games keep their
  opponents/collisions; bầu cua keeps honest dice; dog racing keeps its fixed draw and payouts. Cool-off, spam decay,
  Lộc limits and police enforcement remain. Exact fresh maximum RTP is 97.1376% / 96.6% / 91.851% respectively;
  even with Lộc's gate always open it is 98.4489576% / 97.8282% / 92.275116%, all below 100%.

- **Per-stall fresh draw:** `fair.BASES` sets xóc đĩa .49 (48.57 won rounds in 100 after raids), lô tô .46 and vé cào
  .51, increased slightly on 10/10 from .485 / .455 / .50. Earlier rates were .508 / .503 / .503. Ném vòng is free and stays at .503.
- **Vé cào prizes:** the weights in `fair_scratch.PRIZES` now average 1.80× a won ticket (was 1.59×). Big prizes come a
  little more often and a fresh ticket now returns 91.851%.
- **🍀 Lộc trời cho:** `LOC_P` drops from .015 to .003 and stays ×10, once an hour across the server. On a busy server
  the hour's Lộc still comes. A lone player can no longer count on it.
- **Lô tô side bets are closed** (`SIDE_OPEN`). The số chốt is a call of the minute's sequence, and that sequence is the
  same for every tờ bought that minute. A player could buy a cheap first tờ, see the calls, then bet a second one on
  the likely parity or column. Rounds bought before still settle and validate.
- **No numbers shown** (owner 08/10: "số liệu k hiển thị ra"). No win rate reaches the client: `rules` has no
  `luck_pct`, `luck`, `cooled_pct`, `floor_pct`, `run_free` or `raid_pct`, and the "Vận đang nguội" hint is sent as
  `cool`, without its rate. An older client's 🍀 line needs `luck_pct` and its cold hint reads `cold`, so it shows
  neither. The new client has no 🍀 line; the 🚨 police line stays.
- **Stakes** (owner 08/10: "mn đặt cược bao nhiêu thoải mái nhé"). Bầu cua and chiếu trong take any whole stake the
  wallet holds, typed or from the quick chips. `STAKE_MAX` (1,000,000 a round) is only a technical bound: a bão pays 10
  times the stake, and one Sổ ví row must stay within ±10,000,000 for every validator. `NET_SAFE` keeps today's saved
  net far from its ±10^9 bound. Lô tô, phóng dao and vé cào keep their menus: a lô tô round (≤ `ROUND_MAX` 1,000) and a
  knife stake (`fair_knife.STAKES`) are saved and checked by older servers, and vé cào sells fixed-price tickets.
  None of this changes a return: every stake gets the same odds.

## 🕶️ Chợ đen: free entry and arrests (updated 11/10)

The owner removed the entry fee on 10/10. Players see "Chợ đen" everywhere; ids, keys, endpoints and edition
`fair20261009` are unchanged. The rules live in `game/fair_bm.py`:

- **Free entry for everyone**, including an empty or negative wallet. The old randomized 10,000 xu protection fee
  and 30% refusal robbery are retired. `fair_bm_pay` and `fair_bm_refuse` accept legacy client retries as safe no-ops:
  no wallet/bank/history mutation, no new paid/robbed record, no charge or refund. The public compatibility field
  `fee` is 0, `st` is `free`, and `inside` is true, except for a saved same-day ban. Payment/refusal controls are removed.
- **Saved bans and jail remain enforced.** A legacy `ban` for today's Vietnam date still blocks new stall entry;
  it expires at Vietnam midnight. Existing `paid`/`robbed` records remain valid and unchanged. Finishing existing
  rounds, the gift and loan repayment keep their existing gate exceptions. Current police arrests still fine and
  jail players according to their existing rules; removing the fee does not disable `_gate_on()` or police checks.
- **Arrests on the paid rounds** (bầu cua, chiếu trong, a lô tô purchase, a vé cào, a đua chó bet; not Phóng dao or
  ô ăn quan, see below), rate `fair_bm.arrest_p(f, stake)`, drawn by `fair_bm._arrest_roll(p)` from its own random
  source before the round is drawn; at 0 nothing is rolled:
  - `BM_ARREST_P` (4.25%) while today's Chợ đen net is above `ARREST_FROM` (300,000 xu; owner 09/10 "ae ăn tiền nhiều
    (hơn 300k) thì mới bị bắt", "tỷ lệ bị bắt thấp tý");
  - **plus big stakes, whatever the net** (owner 09/10 "cược mà ai cược nhiều, từ 50k trở lên thì tăng tỷ lệ bị bắt,
    mỗi 10k tăng 1% (từ mốc 50k)"): a round staking `BIG_STAKE_FROM` (50,000) xu or more adds
    `BIG_STAKE_PCT × (1 + (stake − 50,000) // BIG_STAKE_STEP)` %, with `BIG_STAKE_PCT` .85 and `BIG_STAKE_STEP` 10,000:

    | stake | net ≤ 300k | net > 300k |
    |---|---|---|
    | < 50,000 | 0 (not rolled) | 4.25% |
    | 50,000 – 59,999 | .85% | 5.1% |
    | 60,000 – 69,999 | 1.7% | 5.95% |
    | 100,000 | 5.1% | 9.35% |
    | 290,000 | 21.25% | 25% (cap) |
    | ≥ 340,000 | 25% (cap) | 25% (cap) |

  - never above `ARREST_CAP` (25%, after the earlier 11/10 modest reduction) a round. The stake is the round's whole stake (bầu cua: all faces; lô tô: tờ and
    side bets; vé cào: its price).

  Caught: the unplayed stake stays in the wallet, one small fine under `loss_limits.bounded_loss(..., fine=True)`, and
  `JAIL_DAYS` (3) days in the trại tạm giữ (`game/jail.py`). The wallet reserve remains. The arrest replaces
  neither the chiếu trong's own rare dẹp chiếu (`RAID_PCT`) nor the police's wealth check and asset check; those still
  run on rounds the police did not catch. Nothing new is saved for the rate (it is computed from the stake and
  `journey['fair'].net`), so the save stays what 1.9.30/1.9.31 validate.
- **What it does to the house edge:** for arrest rate `a` and the table's return `R`, canceling an unplayed stake
  gives `a + (1 − a) × R` before the bounded fine. This stays below 100% whenever `R < 1` and `a < 1`; it does not establish a house edge when the current fresh `R` exceeds 1.
  The expected actual fine, divided by the stake, lowers it further. Cancellations no longer forfeit the stake.
- **Nothing reaches the client** about the rate or the percentages: `fair.bm` carries only the zero legacy fee, today's standing
  (`st`, `inside`, `ban`) and the đàn em's name. Receipts give the fine in xu.
- **Save:** `journey['fair_bm']` `{d, s}` (the Vietnam date; `paid`, `robbed` or `ban`) sits beside `journey['fair']`,
  where a 1.9.26 server's fair validator would refuse a new key; the journey keeps unknown optional blocks, so a
  1.9.20–1.9.26 server validates and keeps the save (it just has no gate).

## 🐕 Đua chó (owner 09/10: "trò đua chó")

A betting stall of the Chợ đen where the player only watches and cheers (`game/fair_dog.py`, command `fair_dg`,
client `public/js/v4/fair-dog.js`). Each race number (one every `SLOT_S` = 120 s, the same for everyone) has a lineup
of six dogs from `RACERS` (the pet system's breeds and coats) and gives each one a class. A class is a weight (out of
1000, never sent) and a payout in tenths of the stake (shown on the board next to the dog: a price):

| class | weight | payout since 16/10 (stake included) | return per xu | 15/10 price (`OLD`) | its return |
|---|---|---|---|---|---|
| favourite | 320 | ×3.0 | 96.0% | ×2.9 | 92.8% |
| 2 | 240 | ×4.1 | 98.4% | ×3.9 | 93.6% |
| 3 | 180 | ×5.5 | 99.0% | ×5.2 | 93.6% |
| 4 | 120 | ×8.2 | 98.4% | ×7.8 | 93.6% |
| 5 | 90 | ×11 | 99.0% | ×10.5 | 94.5% |
| outsider | 50 | ×20 | 100.0% | ×19 | 95.0% |

Owner 16/10: the `OLD` prices apply when the player raced 11 or more times in the last minute (`fair_pace['dg']`) or
today's Chợ đen net is ≥ 100,000 (`fair.slow_odds`); the board shows the prices the player's next race gets.

- **The draw:** the player sends `{race, lane, stake}` (the race shown, the one before or the next: the client's
  clock). The server draws the finishing order at once from the weights (`draw`, `fair._rng`), pays a winning stake
  `stake × payout // 10` (rounded down) and sends the order, a photo-finish flag and a seed for the show. The client
  plays a ~16 s race that ends in that order; the 📣 cổ vũ button sends nothing and changes nothing.
- **Stakes** like bầu cua / chiếu trong: any whole stake from 10 xu (`DG_MIN`) to `STAKE_MAX` the wallet holds. An
  outsider on a 1,000,000 stake pays 19,000,000 over it (×20 since 16/10): the Sổ ví gets it in rows of at most 10,000,000
  (`fair._pay_big`), counted as one race.
- **No cool-off, no spam decay:** fixed odds like the bầu cua's honest dice (only the 16/10 pace/net switch to the
  `OLD` prices above); a race counts as a
  switch for a cooled stall (`PAID_LUCK`). 🍀 Lộc: yes (`LOC_ACTIONS`), within the table above (the ×20 dog already
  wins more than ×10). The police: the bảo kê gate, the arrest roll, the wealth check and the asset check, as on every
  paid round; a jailed player cannot race (`game/jail.py` blocks every `fair_*`).
- **Nothing about the chances reaches the client:** `api.state.fair.dog` has the roster, the lineups with their
  payouts and the stake bounds; the receipt has the order, the payout and the xu.
- **Save:** nothing new. A race settles in its command; its Sổ ví row (`🐕 Đua chó chợ đen · N lượt`) counts the races,
  today's net and the Bảng vàng's won/lost take it like any paid stall. `journey['fair_cool']`, `fair_balance` and
  `fair_run` never get a `dg` key, so a 1.9.30 / 1.9.31 server validates a save after a race, won, lost or caught
  (`tests/test_fair_dog.py` OldServer). Since 16/10 the race's time goes in the new optional `journey['fair_pace']`
  (`dg` list), a key older servers ignore.

## Not a wager

- **🗡️ Phóng dao is a skill game.** Owner 05/10: no chance draw ever turns a clean board into a loss. Its return
  depends on the thumb. The simulated players (`scripts/sim_fair_knife.py --table 2000 30000`: each sees the board
  with a reaction delay and aim noise; a run stops at a level drawn from the range) get back, per xu staked:

  | player | 1.9.31 soft board, 2–5 / 5–8 levels | 1.9.32 +5 % ramp | **twist board (now)** | twist: clears level 1 / 3 / 5 / 10 |
  |---|---|---|---|---|
  | weak | .18 / .03 | .15 / .01 | **.11 / .01** | 49 / 36 / 28 / 24 % |
  | average | .38 / .14 | .32 / .07 | **.22 / .02** | 63 / 45 / 34 / 28 % |
  | good | 1.67 / 2.58 | 1.56 / 1.94 | **1.39 / 1.34** | 96 / 87 / 77 / 54 % |
  | script (clears every level) | 11.8 | 11.8 | **11.8** | 100 % |

  Owner 09/10 ("phóng dao, ô ăn quan thì chơi hệ kĩ năng", "giới hạn 1k/1 lần", "bắt nếu cảm thấy có cheat hoặc
  spam", "phóng dao mà level cao thì tăng tốc lên nhé, mỗi level tăng 5% tốc độ"):

  - **No daily cap.** The silent 300 xu a day of 08/10 (`KN_DAY_CAP`, `_kn_over`, the level forced to `HEAT_MAX`, the
    clearing throw that glanced off) is gone: a clean board always clears and "Dừng" pays the ladder in full. The
    legacy `fair.dpts` it counted in is left alone (still within 0..`POINTS_DAY` = 30, the bound the older validators
    check); no older validator bounds what Phóng dao pays in a day (a run's `pz` ≤ 10^7, `top` ≤ 10^9, today's
    `fair.net` ≤ 10^9, `NET_SAFE` 10^8 for new stakes), so nothing had to stay for a rollback. **Rollback note:** a
    1.9.30/1.9.31 server still has the cap: after a rollback it caps that day's knife wins again from the `dpts`
    left (0 for days played on this build), and a run's prize waiting as a choice is clamped by it when paid there.
  - **Stake at most 1,000 xu a run** (`fair_knife.STAKES` = 2 … 1,000; a larger stake is refused). The most a run can
    pay is the top of the ladder at 1,000 xu: 10,000 xu, plus the 🔥 x2 levels' steps.
  - **Faster each level, and it turns back and forth** (owner 09/10: "mỗi level tăng 5% tốc độ", then "phóng dao mình
    tăng tốc lên, hoặc là xoay tới lui gì đó cho khó là được chứ vẫn cho người ta chơi kĩ năng"). A level started on
    this build plays the **twist board** (`fair_knife.twist_schedule()`, the `TWIST_*` constants), all of it drawn from
    the run's seed, the level and today's heat — no draw at the throw, no cap, no forced miss:
    - it cruises `twist_up(n)` = 1 + `TWIST_PCT` (10 %) × (n − 1) faster than the soft board (× 1 at level 1, × 1.9 at
      level 10); the owner's 5 % a level is the floor, held by the cruising speed and the level's average speed (tested);
    - it **turns back**, more often each level (over the 60 s level clock ~4 turns on average at level 1, ~11 at level 10; ~1 and ~3.6 in its first 20 s), but
      never as a jerk: it first brakes visibly to a near stop (`TWIST_BRAKE` 380–520 ms at level 1, 240–340 ms at the
      top), rests (`TWIST_DWELL` 100–240 ms), then speeds up the other way (`TWIST_ACCEL` 220–320 ms) to a burst a
      little faster than before (× 1 … 1.25, up to 1.55 at the top);
    - it speeds up and slows down smoothly within the level (ramps of 400–650 ms), the swings wider each level
      (× 0.65–1.35 the cruise at level 1, 0.6–1.7 at the top).

    The server sends the level's `segs` ([ms, deg/s, ramp ms]: the speed moves linearly over the ramp); the client
    (`public/js/v4/fair-knife.js` `angleAt`/`judge`) turns and judges exactly that, checked against the server on random
    ramp and twist boards and taps by the node parity test (`tests/test_fair_knife_nocap.py` `ClientParity`). The
    simulated good thumb still clears levels 1–3 96 / 92 / 87 % of the time.

    **Which board a level is judged on:** each level carries a marker `{at, seed}`. A twist level sets
    `journey['fair_kn_twist']` (and the 1.9.31 `fair_kn_soft`, so an older server judges it on its soft board); a
    1.9.32 level has `journey['fair_kn_ramp']` (`speed_up(n)` = 1 + 5 % × (n − 1) on the soft board); neither means a
    1.9.31 soft level. This build judges each level on the board it was started on, so a level in play across the
    deploy settles on what the player was shown. Both markers are optional keys the older validators keep unread.
    **Rollback note:** after a rollback to 1.9.31 (e4ea7eba) or 1.9.30 (65dafa3b), a twist level in play is shown and
    judged by that server on its own soft board (no turn-backs), so it settles sanely, only easier. Today's heat
    (`heat()`, from the day's Chợ đen net) still applies as before.
  - **Out of the arrest roll.** Phóng dao and ô ăn quan are never rolled for by the Chợ đen's arrest
    (`fair_bm.arrest_p`, neither the 4.25% nor the big stakes), and the wealth/asset checks run only after the paid
    luck rounds as before. The police come only for a **script or a burst** (`game/fair_watch.py`, conservative: a
    miss is better than an honest player arrested):

    | stall | what is caught | rule |
    |---|---|---|
    | Phóng dao | throws sent before they happen | a throw whose last knife claims more than `KN_AHEAD_MS` (2.5 s) beyond the level time the server has seen pass, `KN_AHEAD_FLAGS` (2) times within an hour |
    | Phóng dao | a burst of runs | `KN_SPAM_RUNS` (100) runs started within `KN_SPAM_MS` (5 min): 3 s a run for five minutes on end |
    | Ô ăn quan | moves no hand makes | `OAQ_FAST_MOVES` (8) moves within 10 min each less than `OAQ_FAST_MS` (350 ms) after the game's previous command |
    | Ô ăn quan | a burst of games | `OAQ_SPAM_GAMES` (120) games started within 10 min |

    Why these hold for people: the stall's page measures throws on a level clock that starts when the board arrives,
    behind the server's (at most ~1 s ahead, from the state's whole-second `now`); throws more than `SLACK` (4 s)
    ahead were already refused. The ô ăn quan page plays every sowing out (fast mode and reduced motion too, at least
    ~0.3 s a move) and a move takes two taps after it. Not used: tap rhythm (touch time stamps are often snapped to the
    screen's frames, so an even hand could look machine-regular).

    Caught: the same arrest as the Chợ đen's (`fair._arrested`): Phóng dao cancels an unstarted bet or refunds the
    already-paid run's stake once, ô ăn quan has no stake (the game in play is lost); a bounded wallet-only fine;
    `JAIL_DAYS` (3) in the trại tạm giữ. The message says what was seen in words
    ("Công an thấy tay ném nhanh bất thường, nghi gian lận!"); no threshold reaches the client. The counters live in
    `journey['fair_watch']` (optional; windows `[at, n]`, an older server's journey keeps it unread). Off with the
    Chợ đen's kill switch (`MNL_BM_OFF`).
  - **Worst case for the house:** no daily bound any more. A good thumb gets back ~1.3–1.4× its stakes on the twist board
    (the table above), so at 1,000 xu a run a strong player can win several thousand xu an hour from the
    stall. A script that paces its throws like a person is not caught (by design); it can clear every level (11.8×).
- **Ô ăn quan and ném vòng take no stake.** They pay out but cost nothing. A won ô ăn quan game pays `OAQ_PRIZE`:
  Bé Bi 50, Ông Hai 10,000 xu (owner 09/10: "thắng ông Hai vẫn là 10k/1 lần"; the "1k/1 lần" limit is Phóng dao's stake).

## Save compatibility

The house-edge changes added no save keys (the Chợ đen's bảo kê adds the optional `journey['fair_bm']`, above). A save from the last edition starts afresh on its first command: money, days, Bảng vàng,
gift and the police's mark reset, and its loan is collected. `fair_board.settle` also settles `fair.PAST` editions that
a server missed, once each.
