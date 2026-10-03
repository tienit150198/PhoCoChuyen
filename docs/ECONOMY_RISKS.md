# Rủi ro & bảo hiểm, Tiệm vàng (03/10)

Owner, 03/10: the xu come in faster than they go (x3 weeks, the fair, staff bonuses). Players should sometimes lose
money ("trộm, ốm đau, hỏng xe, sửa nhà, mất két") and have somewhere to put it ("đầu tư"). First "tăng thêm rủi ro",
then "cho người ta chơi thoải mái tí và có cảm giác happy tí". So: more frequent and bigger losses than the first
draft, but always warned, preventable, capped, and never for new or poor players. Earning is never limited; the x3 cap
stays 3 000.

Code: `game/rui.py` (risks, insurance, gear), `game/vang.py` (gold), `public/js/v4/rui.js` + `public/css/rui.css`
(the card, the "Bảo hiểm" and "Tiệm vàng" pages), `scripts/sim_risks.py` (simulation), `scripts/browser_risks.py`
(browser smoke), `tests/test_rui.py` (rules + the 1.4.31 round trip).

## Rules

| | |
|---|---|
| Who | nothing before life day 15 and chapter 3, nor in the 3 life days after this build first meets a save. Odds halved before life day 30 or while W < 1 500 |
| W | cash + bank account (demand and terms) + Mây savings + gold at the shop's buy-back price |
| Floor | nothing at all while W < 300 xu |
| Caps | an event ≤ 8 % of (W − 300); a tháng (5 life days) ≤ 12 % of (W − 300) at its start, ≤ 2 events, ≥ 3 life days apart |
| Flow | a warning 1–2 life days ahead with a prevention that works (20 % of the projected cost, a free option for thefts: bank the cash) → else a story card with 2–3 choices, 3 life days to pick (then the gentlest one) |
| Debt | never: cash, then the bank account, the rest waived |
| Offline | rolled only on the player's own life-day tick; an older build's days are not back-filled |

Events (per 10 000 a life day): xe 400 for the vehicle ridden, 120 the others (repair 4 % of the price paid; a
bike can be fixed by hand); nhà 200 a home owned (dột, vỡ ống, chập điện, cháy bếp, ngập — 1–3 % of the list price,
tied to the Sửa nhà parts); ốm 100 (+200 when hungry/tired, +100 low tinh thần; the clinic 1,5 % of W−300, 30..600);
móc túi 120 (×1,5 above 3 000 cash; 12 % of the cash above 300, ≤ 2 000; or the phone); trộm 100 with ≥ 600 cash at
home (20 %, ≤ 4 000); phạt đỗ xe 200 while driving a car (the first is only a reminder). Left broken: a vehicle cannot
go out and sells for less; a home loses its Ấm cúng bonus until fixed. A waived month's bill doubles the odds for 10
life days; a worn home part doubles them, a fully upgraded home halves them.

Insurance (billed every 5 life days with the month's bills, kind `upkeep`; pays 80 % from 3 life days after buying,
prevention included): BHYT 3 xu + 0,03 % of W a tháng (≤ 60); xe 0,25 % of the motor vehicles' price; nhà 0,08 % of the
homes' price. A company's BHYT (promotion rank ≥ 1) covers illness for free. Gear, bought once: túi đeo chéo 40, khóa
chống trộm 150, két sắt mini 500, bình chữa cháy 120.

Gold (Tiệm vàng Kim Phát): one price a Vietnam day for everyone, a mean-reverting walk from 500 xu/chỉ (drift +0,1 %,
σ 1,3 %, a 4 % chance of a 2–5 % news jump), seeded by `MNL_GOLD_SALT`. Buy 2,5 % above, sell 2,5 % below, by the phân
(1 chỉ = 10 phân), at most 10 000 chỉ. Paid from cash then the bank account; proceeds to the wallet (kind `invest`).

## Simulation (`python scripts/sim_risks.py`, 60 life days, 200 saves each)

| Archetype | careless | mixed | careful |
|---|---|---|---|
| new (60 xu/day, rents) | 2,5 % of earnings, 1,2 events | 3,0 % | 4,1 % (gear and premiums, ~145 xu) |
| average (120/day, xe số) | 1,1 %, 2,8 events | 1,0 % | 1,6 % |
| rich (3 000/day, 5 vehicles, 3 homes) | 5,0 % (9k of 180k), 7,6 events, p90 14k, worst 24,5k | 2,9 % | 3,8 % (premiums 6k, 0 events) |
| x3 farmer (1 500/day + spikes, cash) | 2,8 %, 4,4 events | 1,3 % | 0,9 % |

Gold held 20 real days: mean −2,8 %, a gain in 30 % of walks; held 60 days: mean +1,8 %, p10 −5,8 %, p90 +9,6 %,
a gain in 59 %.

## Compatibility

New optional keys only: `journey.rui`, `journey.vang` (older validators keep unknown journey keys). Wallet rows use
kinds 1.4.31 knows (`life`, `home`, `incident`, `upkeep`, `invest`); no new STATS, upk keys or life kinds. Public
state: top-level `rui` and `vang` (not inside `journey`, so its size budget is untouched). `tests/test_rui.py
OldServer` runs a save with every block and row through the 1.4.31 tree (`MNL_OLD_TREE`, else
`../_rel1431/mot-ngay-lam-nghe`) and back.
