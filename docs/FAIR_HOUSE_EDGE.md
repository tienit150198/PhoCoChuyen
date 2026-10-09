# 🕶️ Chợ đen (was Hội chợ): the house always wins (08/10/2026)

Owner 08/10: "mở hội chợ nhé, tỷ lệ chỉnh lại làm sao cho phù hợp, đảm bảo nhà cái luôn thắng", then "chợ đen để
luôn ở ngoài nhé". This edition opened on 09/10 (`FAIR_START` 2026-10-09, edition `fair20261009`). Its entry stays in
sight: a 🏮 Hội chợ chip in the town's top bar and a main menu entry. The 🏮 gate on Phố hàng rong is still there too.

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
| 🐕 Đua chó (09/10, fixed odds; the outsider ×19 at best) | – | 95.0% (favourite 92.8%) | 95.0% | 93.5% / 93.9% / 93.8% (a dog at random: 93.85%) |
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

- **Bảo kê, hên xui** (owner 09/10: "phí bảo kê k phải khi nào cũng thu, tỷ lệ thu là hên xui 40% /2 ngày"): Vietnam
  days (UTC+7) go in stretches of 2 (`ASK_DAYS`); in a stretch the đàn em ask `BM_ASK_P` (40%) of the time, fixed by
  (journey seed, stretch) in `fair_bm.asked` (never shown, never saved). Not asked: the player walks in. Asked: `fair_bm_pay` takes `BM_FEE` (10,000 xu, shown: it is a price) from the
  wallet; `fair_bm_refuse` lets the đàn em take `ROB_PCT` (30%) of the wallet, cash only, never the bank account, 0 when
  the wallet is empty. Either way the player is in until the stretch ends. Until then every `fair_*` command except
  finishing what was begun (`fair.LATE`), the gift and repaying a loan is refused (`fair_bm_gate`).
- **Arrests on the paid rounds** (bầu cua, chiếu trong, a lô tô purchase, a vé cào, a đua chó bet; not Phóng dao or
  ô ăn quan, see below), rate `fair_bm.arrest_p(f, stake)`, drawn by `fair_bm._arrest_roll(p)` from its own random
  source before the round is drawn; at 0 nothing is rolled:
  - `BM_ARREST_P` (5%) while today's Chợ đen net is above `ARREST_FROM` (300,000 xu; owner 09/10 "ae ăn tiền nhiều
    (hơn 300k) thì mới bị bắt", "tỷ lệ bị bắt thấp tý");
  - **plus big stakes, whatever the net** (owner 09/10 "cược mà ai cược nhiều, từ 50k trở lên thì tăng tỷ lệ bị bắt,
    mỗi 10k tăng 1% (từ mốc 50k)"): a round staking `BIG_STAKE_FROM` (50,000) xu or more adds
    `BIG_STAKE_PCT × (1 + (stake − 50,000) // BIG_STAKE_STEP)` %, with `BIG_STAKE_PCT` 1 and `BIG_STAKE_STEP` 10,000:

    | stake | net ≤ 300k | net > 300k |
    |---|---|---|
    | < 50,000 | 0 (not rolled) | 5% |
    | 50,000 – 59,999 | 1% | 6% |
    | 60,000 – 69,999 | 2% | 7% |
    | 100,000 | 6% | 11% |
    | 690,000 | 65% | 70% (cap) |
    | ≥ 740,000 | 70% (cap) | 70% (cap) |

  - never above `ARREST_CAP` (70%) a round. The stake is the round's whole stake (bầu cua: all faces; lô tô: tờ and
    side bets; vé cào: its price).

  Caught: the stake is lost with no outcome, a fine of `FINE_PCT` (30%) of the wallet left after the stake, and
  `JAIL_DAYS` (3) days in the trại tạm giữ (`game/jail.py`). The wallet never goes below zero. The arrest replaces
  neither the chiếu trong's own rare dẹp chiếu (`RAID_PCT`) nor the police's wealth check and asset check; those still
  run on rounds the police did not catch. Nothing new is saved for the rate (it is computed from the stake and
  `journey['fair'].net`), so the save stays what 1.9.30/1.9.31 validate.
- **What it does to the house edge:** a round rolled at rate p returns (1 − p) × the table's return, before the fine:
  above 300k, at most 0.95 × 97.4% ≈ **92.5%** for the best stall with the 🍀 gate open; a 100,000 xu round below 300k
  at most 0.94 × the table; a capped round 0.3 × the table. The fine (30% of the wallet on an arrest) makes the
  expected loss of a raided round grow with the wallet, not the stake. The day's bảo kê comes before any round.
- **Nothing reaches the client** about the rate or the percentages: `fair.bm` carries only the fee, today's standing
  (`st`, `inside`, `ban`) and the đàn em's name. Receipts give xu (the robbery, the fine).
- **Save:** `journey['fair_bm']` `{d, s}` (the Vietnam date; `paid`, `robbed` or `ban`) sits beside `journey['fair']`,
  where a 1.9.26 server's fair validator would refuse a new key; the journey keeps unknown optional blocks, so a
  1.9.20–1.9.26 server validates and keeps the save (it just has no gate).

## 🐕 Đua chó (owner 09/10: "trò đua chó")

A betting stall of the Chợ đen where the player only watches and cheers (`game/fair_dog.py`, command `fair_dg`,
client `public/js/v4/fair-dog.js`). Each race number (one every `SLOT_S` = 120 s, the same for everyone) has a lineup
of six dogs from `RACERS` (the pet system's breeds and coats) and gives each one a class. A class is a weight (out of
1000, never sent) and a payout in tenths of the stake (shown on the board next to the dog: a price):

| class | weight | payout (stake included) | return per xu |
|---|---|---|---|
| favourite | 320 | ×2.9 | 92.8% |
| 2 | 240 | ×3.9 | 93.6% |
| 3 | 180 | ×5.2 | 93.6% |
| 4 | 120 | ×7.8 | 93.6% |
| 5 | 90 | ×10.5 | 94.5% |
| outsider | 50 | ×19 | 95.0% |

- **The draw:** the player sends `{race, lane, stake}` (the race shown, the one before or the next: the client's
  clock). The server draws the finishing order at once from the weights (`draw`, `fair._rng`), pays a winning stake
  `stake × payout // 10` (rounded down) and sends the order, a photo-finish flag and a seed for the show. The client
  plays a ~16 s race that ends in that order; the 📣 cổ vũ button sends nothing and changes nothing.
- **Stakes** like bầu cua / chiếu trong: any whole stake from 10 xu (`DG_MIN`) to `STAKE_MAX` the wallet holds. An
  outsider on the biggest stake pays 18,000,000 over the stake: the Sổ ví gets it in rows of at most 10,000,000
  (`fair._pay_big`), counted as one race.
- **No cool-off, no spam decay:** fixed odds like the bầu cua's honest dice (nothing to lower); a race counts as a
  switch for a cooled stall (`PAID_LUCK`). 🍀 Lộc: yes (`LOC_ACTIONS`), within the table above (the ×19 dog already
  wins more than ×10). The police: the bảo kê gate, the arrest roll, the wealth check and the asset check, as on every
  paid round; a jailed player cannot race (`game/jail.py` blocks every `fair_*`).
- **Nothing about the chances reaches the client:** `api.state.fair.dog` has the roster, the lineups with their
  payouts and the stake bounds; the receipt has the order, the payout and the xu.
- **Save:** nothing new. A race settles in its command; its Sổ ví row (`🐕 Đua chó chợ đen · N lượt`) counts the races,
  today's net and the Bảng vàng's won/lost take it like any paid stall. `journey['fair_cool']`, `fair_balance` and
  `fair_run` never get a `dg` key, so a 1.9.30 / 1.9.31 server validates a save after a race, won, lost or caught
  (`tests/test_fair_dog.py` OldServer).

## Not a wager

- **🗡️ Phóng dao is a skill game.** Owner 05/10: no chance draw ever turns a clean board into a loss. Its return
  depends on the thumb. On today's boards the simulated players get back:

  | player | stops after 2–5 levels | stops after 5–8 levels |
  |---|---|---|
  | weak | .28 | .06 |
  | average | .57 | .30 |
  | good | 1.80 | 3.06 |
  | script (clears every level) | 11.8 (all ten levels) | 11.8 |

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
  - **Faster each level:** a level started on this build turns `speed_up(n)` = 1 + 5% × (n − 1) faster (level 1 as
    before, level 10 × 1.45), on top of the soft board's 115%. The server puts the speeds in the level's `segs`, which
    the client draws as sent, so both sides turn the same board. Marked per level by `journey['fair_kn_ramp']`
    `{at, seed}` (optional; an older server ignores it). A level started before keeps its board and settles; after a
    rollback, a ramped level in play is judged and shown by the older server on its unramped board (level 1 is the same
    either way). Today's heat (`heat()`, from the day's Chợ đen net) still applies as before.
  - **Out of the arrest roll.** Phóng dao and ô ăn quan are never rolled for by the Chợ đen's arrest
    (`fair_bm.arrest_p`, neither the 5% nor the big stakes), and the wealth/asset checks run only after the paid
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

    Caught: the same arrest as the Chợ đen's (`fair._arrested`): Phóng dao loses the run's stake (taken at the start of
    a run, or the run in play is lost with what rode on it), ô ăn quan has no stake (the game in play is lost); a fine
    of `FINE_PCT` (30%) of the wallet; `JAIL_DAYS` (3) in the trại tạm giữ. The message says what was seen in words
    ("Công an thấy tay ném nhanh bất thường, nghi gian lận!"); no threshold reaches the client. The counters live in
    `journey['fair_watch']` (optional; windows `[at, n]`, an older server's journey keeps it unread). Off with the
    Chợ đen's kill switch (`MNL_BM_OFF`).
  - **Worst case for the house:** no daily bound any more. A good thumb gets back ~1.8–3× its stakes (the table above;
    the faster levels lower that), so at 1,000 xu a run a strong player can win several thousand xu an hour from the
    stall. A script that paces its throws like a person is not caught (by design); it can clear every level (11.8×).
- **Ô ăn quan and ném vòng take no stake.** They pay out but cost nothing. A won ô ăn quan game pays at most 1,000 xu
  (`OAQ_PRIZE`: Bé Bi 50, Ông Hai 1,000; owner 09/10 "giới hạn 1k/1 lần", was 10,000).

## Save compatibility

The house-edge changes added no save keys (the Chợ đen's bảo kê adds the optional `journey['fair_bm']`, above). A save from the last edition starts afresh on its first command: money, days, Bảng vàng,
gift and the police's mark reset, and its loan is collected. `fair_board.settle` also settles `fair.PAST` editions that
a server missed, once each.
