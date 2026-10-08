# 🎪 Hội chợ: the house always wins (08/10/2026)

Owner 08/10: "mở hội chợ nhé, tỷ lệ chỉnh lại làm sao cho phù hợp, đảm bảo nhà cái luôn thắng", then "chợ đen để
luôn ở ngoài nhé". This edition runs from 09/10 to 13/10 (`FAIR_START` 2026-10-09, `FAIR_DAYS` 5, edition
`fair20261009`). Its entry stays in sight: a 🏮 Hội chợ chip in the town's top bar and a main menu entry, from "sắp mở"
until the fair closes. The 🏮 gate on Phố hàng rong is still there too.

The table gives the most one round can return per xu staked. That is a fresh run with perfect play. Every other state
returns less: the cool-off after 4 wins, the spam decay, a late Kinh, the police. So no betting pattern comes out ahead.
The figures come from `scripts/sim_fair_odds.py` (`exact()`), which also checks them on 10^6 real-draw rounds per stall.
`tests/test_fair_house_edge.py` runs the same checks on smaller samples.

| stall | before (07/10 rules) | now | now, with 🍀 Lộc gate always open | 10^6 rounds (fresh / spam / press) |
|---|---|---|---|---|
| 🦀 Bầu cua (honest dice, bão 10:1) | 95.4% (Lộc: 100.9%) | 95.4% | 96.5% | 95.2% / 95.5% / 95.2% |
| 🕯️ Chiếu trong (even money, 0.88% raids) | 100.7% (Lộc: 107.5%) | 96.1% | 97.4% | 95.6% / 79.7% / 96.0% |
| 🎱 Lô tô (Kinh 2.1× the tờ) | 105.6% (2/5-xu tờ 100.6%; Lộc: 112.3%) | 95.6% (2/5-xu tờ 91.0%) | 96.8% | 95.5% / 84.0% / 95.5% |
| 🎟️ Vé cào | 80.0% | 90.0% | 90.5% | 89.6% / 72.1% / 90.0% |
| 🎲 Lô tô side bets (chẵn/lẻ, cột) | 94–98% blind; **107.7% / 163.8%** after seeing the minute's calls | closed | – | – |

How the three betting patterns play:

- **fresh:** a long pause before every round.
- **spam:** one round a second at one stall.
- **press:** 1000 xu while the stall is warm, 10 xu once it has cooled.

## What changed

- **Per-stall fresh draw:** `fair.BASES` sets xóc đĩa .485 (48 won rounds in 100 after raids), lô tô .455 and vé cào
  .50. These used to be .508 / .503 / .503. Ném vòng is free and stays at .503.
- **Vé cào prizes:** the weights in `fair_scratch.PRIZES` now average 1.80× a won ticket (was 1.59×). Big prizes come a
  little more often and a ticket returns 90%.
- **🍀 Lộc trời cho:** `LOC_P` drops from .015 to .003 and stays ×10, once an hour across the server. On a busy server
  the hour's Lộc still comes. A lone player can no longer count on it.
- **Lô tô side bets are closed** (`SIDE_OPEN`). The số chốt is a call of the minute's sequence, and that sequence is the
  same for every tờ bought that minute. A player could buy a cheap first tờ, see the calls, then bet a second one on
  the likely parity or column. Rounds bought before still settle and validate.
- **The rules line** shows each stall's rate (`rules.luck`). An older client still reads the single `luck_pct`, now 48.

## Not a wager

- **🗡️ Phóng dao is a skill game.** Owner 05/10: no chance draw ever turns a clean board into a loss. Its return
  depends on the thumb. On today's boards the simulated players get back:

  | player | stops after 2–5 levels | stops after 5–8 levels |
  |---|---|---|
  | weak | .28 | .06 |
  | average | .57 | .30 |
  | good | 1.80 | 3.06 |
  | script (clears every level) | 11.8 (all ten levels) | 11.8 |

  The ladder alone would let a good thumb win without limit, so (owner 08/10) the house caps it:

  - **Daily cap: 300 xu** (`fair.KN_DAY_CAP`) a player and Vietnam day. What each run pays over its stake counts
    (rounded up to 10 xu, the house's side); a losing run does not give any of it back, so the stall's net for the
    player can only be lower. A run that would cross the cap pays the stake back plus what is left of it, and the
    prize the stall shows (`run.prize`, `run.win`) is already capped, so nothing promised is cut later. Once the cap is
    reached the stall takes no new stake that day ("Hôm nay bạn đã thắng đủ ở Phóng dao, mai quay lại nhé."), and a
    payout that reaches it ends with that line. This is cleaner than letting the player keep staking for at most the
    stake back, which could only lose. `api.state.fair.knife` gains `cap` and `cap_left` (an older client ignores them).
  - **Why 300:** it is the bound the older validators already put on the saved counter it uses: the legacy points
    tally `fair.dpts` (reset each Vietnam day and each edition, unused since points went on 03/10) is checked as
    0..`POINTS_DAY` = 30, and stored in 10-xu steps that makes 300 xu. That needs no new save key, and a 1.9.21 server
    validates the save. DAY_CAP (150) is no live cap any more, only a bound on the chance stalls' saved net. 300 xu is
    three easy clears at 100 xu: a real reward for a good thumb, but small next to a day's work.
  - **Worst case for the house:** a player can net at most **+300 xu a day** from Phóng dao, whatever the stake or the
    number of runs. That is at most 1,500 xu over the five fair days. A prize left waiting overnight is paid under the
    next day's cap. The police's checks and the heat on a winning day still apply on top.
- **Ô ăn quan and ném vòng take no stake.** They pay out but cost nothing.

## Save compatibility

There are no new save keys. A save from the last edition starts afresh on its first command: money, days, Bảng vàng,
gift and the police's mark reset, and its loan is collected. `fair_board.settle` also settles `fair.PAST` editions that
a server missed, once each.
