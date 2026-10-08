# 🕶️ Chợ đen (was Hội chợ): the house always wins (08/10/2026)

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

## 🕶️ Chợ đen: bảo kê and arrests (owner 08/10, late)

Owner 08/10 23:15: "k phải là hội chợ, nó là "Chợ đen". Vào chợ đen phải nộp bảo kê, phí bảo kê là 10k xu, nếu k nộp
thì bị trấn lột 30% tiền hiện có. vào chợ đen có thể bị công an bắt, tỷ lệ bị bắt cực cao". Players see "Chợ đen"
everywhere (ids, keys, endpoints and the edition `fair20261009` are unchanged). The rules live in `game/fair_bm.py`:

- **Bảo kê** once per Vietnam day (UTC+7): `fair_bm_pay` takes `BM_FEE` (10,000 xu, shown: it is a price) from the
  wallet; `fair_bm_refuse` lets the đàn em take `ROB_PCT` (30%) of the wallet, cash only, never the bank account, 0 when
  the wallet is empty. Either way the player is in until the day ends. Until then every `fair_*` command except
  finishing what was begun (`fair.LATE`), the gift and repaying a loan is refused (`fair_bm_gate`).
- **Arrests on every paid round** (bầu cua, chiếu trong, a lô tô purchase, a vé cào, a phóng dao run's stake):
  `BM_ARREST_P` (20%) per round, drawn by `fair_bm._arrest_roll` from its own random source before the round is drawn.
  Caught: the stake is lost with no outcome, a fine of `FINE_PCT` (30%) of the wallet left after the stake, and a ban
  (`fair_bm_ban`) until the Vietnam day ends. The wallet never goes below zero. The arrest replaces neither the chiếu
  trong's own rare dẹp chiếu (`RAID_PCT`) nor the police's wealth check and asset check; those still run on rounds the
  police did not catch.
- **What it does to the house edge:** every return in the table above is now multiplied by 0.8 (one round in five
  returns nothing), before the fine: at most 0.8 × 97.4% ≈ **77.9%** of the stake for the best stall with the 🍀 gate
  open, and 76.3% (bầu cua) to 76.9% (chiếu trong) without it. The fine (30% of the wallet on an arrest) makes the
  expected loss of a round grow with the wallet, not the stake: on average 6% of the wallet left per paid round, on
  top. The day's bảo kê (10,000 xu, or 30% of the wallet) comes before any round. Phóng dao's stake is lost to an
  arrest too, so its daily cap now applies to a game that also loses one run in five outright.
- **Nothing reaches the client** about the rate or the percentages: `fair.bm` carries only the fee, today's standing
  (`st`, `inside`, `ban`) and the đàn em's name. Receipts give xu (the robbery, the fine).
- **Save:** `journey['fair_bm']` `{d, s}` (the Vietnam date; `paid`, `robbed` or `ban`) sits beside `journey['fair']`,
  where a 1.9.26 server's fair validator would refuse a new key; the journey keeps unknown optional blocks, so a
  1.9.20–1.9.26 server validates and keeps the save (it just has no gate).

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

  - **Daily cap: 300 xu** (`fair.KN_DAY_CAP`) a player and Vietnam day, and **silent**: no message, no public field.
    What each paid run wins over its stake counts (rounded up to 10 xu, the house's side); a losing run does not give
    any of it back, so the player's real net from the stall can only be lower. A level whose clearing would win past
    what is left (`_kn_over`) starts on the hardest board (`hot = HEAT_MAX`), and if every throw still lands clean, the
    clearing throw glances off: the run is lost like any crash ("Dao chạm dao rồi!"). The stall keeps taking stakes, and
    the prizes it shows are the ladder's. Once the cap is reached, the first level of any stake is such a level, so
    every run after it loses its stake. The payout is also clamped to stake + what is left, as a backstop only.
  - **Why 300:** it is the bound the older validators already put on the saved counter it uses: the legacy points
    tally `fair.dpts` (reset each Vietnam day and each edition, unused since points went on 03/10) is checked as
    0..`POINTS_DAY` = 30, and stored in 10-xu steps that makes 300 xu. That needs no new save key, and a 1.9.21 server
    validates the save. DAY_CAP (150) is no live cap any more, only a bound on the chance stalls' saved net. 300 xu is
    three easy clears at 100 xu: a real reward for a good thumb, but small next to a day's work.
  - **Worst case for the house:** a player can net at most **+300 xu a day** from Phóng dao, whatever the stake or the
    number of runs. That is at most 1,500 xu over the five fair days. A prize left waiting overnight is paid under the
    next day's cap (fresh that day, since the prize is paid by the day's first command). The police's checks and the
    heat on a winning day still apply on top.
- **Ô ăn quan and ném vòng take no stake.** They pay out but cost nothing.

## Save compatibility

The house-edge changes added no save keys (the Chợ đen's bảo kê adds the optional `journey['fair_bm']`, above). A save from the last edition starts afresh on its first command: money, days, Bảng vàng,
gift and the police's mark reset, and its loan is collected. `fair_board.settle` also settles `fair.PAST` editions that
a server missed, once each.
