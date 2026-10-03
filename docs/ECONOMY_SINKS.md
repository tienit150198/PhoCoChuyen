# Xu sinks (03/10)

Owner, 03/10: "tính toán xem có cách nào bào thêm xu của người dùng nhé, thì mình thêm vào. cái này thông báo k có".
No "Có gì mới" entry: the changes are shown where they apply (Nhà xe, Nhà của bạn, Đầu tư, Sổ ví, the guide).

## Where the xu come from (prod, 291 saves, ~2 days)

Wallets: median 70, p90 997, average 7 048 — 11 saves hold most of the xu. Net by group: work +2.41M, fair +256k
(the stalls alone ~+106k), bank & invest −131k, home & furniture −507k. The faucet is the careers' work; the people
whose wallets grow are the few rich players, who also own the villas, the boats and the planes, keep large Mây savings
at 0,3 %/ngày, and play the fair's skill stall well.

Rules kept: the rich pay most, a new or median player (wallet ~70) pays nothing or a few xu; every cost is visible
before it is paid and has its own Sổ ví row; nothing ever pushes the wallet below 0; no stated rule changes without
its text; nothing is billed for the days before this build.

## The sinks

| # | Sink | Numbers | Who pays | Code |
|---|------|---------|----------|------|
| 1 | 🧾 Phí giữ xe & bảo dưỡng | a share of the price paid, a tháng (5 life days): xe máy 0,5 %, ô tô 0,75 %, du thuyền 1 %, máy bay 1,25 % (≈ 6 / 9 / 12 / 15 % a year of the game's calendar). Bicycles free. Xe số 3 xu/tháng, ô tô mini 23, mui trần 90, du thuyền 450, phản lực 1 125 | vehicle owners, in proportion to what they bought | `game/upkeep.py` |
| 2 | 🧾 Phí bảo trì nhà | every home owned from 6 000 xu list price (lived in, empty or let): 0,2 % a tháng from 6 000, 0,3 % from 20 000, 0,35 % from 30 000. Nhà phố 16 xu/tháng, penthouse 65, biệt thự Sông Hồng 210. The flats under 6 000 xu: nothing new. A let home's rent (0,42 %) still covers it | owners of the dearer homes | `game/upkeep.py` |
| 3 | 💧 Lãi bậc thang (Mây savings) | 0,3 %/ngày on the first 20 000 xu, 0,1 %/ngày above (≈ the bank's 7-day term). A term begun before keeps the flat rate until it ends | only balances above 20 000 xu | `game/invest.py` |
| 4 | 🎟️ Vé số cào edge | wins 42 % → 39,5 %: 1,03 → 0,97 xu back per xu (floor 0,96 unchanged) | everyone who scratches, a few xu | `game/fair_scratch.py` |
| 5 | 🗡️ Phóng dao top | ladder levels 6..10: 3,9 5,4 8 12 19 → 3,6 4,6 6 7,8 10 × the stake. Stopping after 2..5 pays as before (average .98, good 2,00); going deep: average .99 → .86, a good thumb 4,5 → 3,8, clearing all ten 11,6× → 6× | mostly the practised thumbs who play deep | `game/fair_knife.py` |
| 6 | 🚘🚁🛳️ New luxury models | Siêu xe Tia Chớp 30 000 (225/tháng), Trực thăng riêng 60 000 (750/tháng), Siêu du thuyền Ngọc Trai 150 000 (1 500/tháng) | the richest, by choice; shown in Phố nghề as "đang đi" | `game/garage.py` |
| — | 📸 Photobooth (other branch) | ~5 xu a session at the fair | counted in the simulation only | — |

Bills (1, 2): every life-day morning adds one day's share of what is owned that morning (thousandths of a xu), so a
vehicle or home bought or sold mid-tháng pays only its days. On every life day that is a multiple of 5 the whole xu are
billed: one Sổ ví row per part ("Phí giữ xe & bảo dưỡng · 3 xe", "Phí bảo trì nhà · 2 căn", kind `upkeep` 💡) and one
line ("🧾 Hóa đơn tháng: …"). Paid from cash (never below 0), then the bank account; what both do not cover is waived
and said so ("… được miễn, không tính nợ"), never owed. The first morning under this build, a player who owns
something billable gets one line: "🧾 Ban quản lý gửi thông báo: … khoảng N xu mỗi tháng …".
Shown before paying: the garage listing, buy page and each vehicle (`upkeep`), the month's bill and its day on
"Xe của bạn"; the home listing, buy page, owned homes (`care`) and the month's total on Nhà của bạn; the guide.

## Simulation (`python scripts/sim_economy.py`)

14 life days, fair open 5 of them; the game's own functions for every sink. Net xu, before → after:

| profile (saves it stands for) | before | after | change |
|---|---:|---:|---:|
| new (161): job 60/day, no assets, a few 2-xu tickets | +683 | +656 | −4 % |
| median (90): 120/day, xe số, 600 saved | +1 487 | +1 439 | −3 % |
| upper (29): 450/day, xe ga + ô tô mini, căn hộ mini, 8 000 saved | +6 383 | +6 194 | −3 % |
| rich_assets (6): 3 000/day, villa + penthouse let + nhà có sân, 5 vehicles incl. yacht & jet, 60 000 saved, good knife thumb | +51 484 | +42 903 | −17 % |
| rich_saver (5): 3 000/day, mui trần, 250 000 saved, good knife thumb | +59 520 | +50 957 | −14 % |
| **sample, per save** | **+3 558** | **+3 185** | **−10 %** |
| … if one rich player in three buys the Trực thăng riêng | | +2 416 | −32 % |

87 % of the cut is paid by the 11 rich saves; the new and median players lose 27–48 xu over two weeks (the fair).

Per group (sample, per save, 14 days): savings interest +276 → +140; fair net +275 → +168; new bills −131.

## What the owner should decide

* The mandatory sinks alone cut the net inflow by about 10 % (≈ 15 % for the rich). Reaching 30–40 % needs either the
  rich to buy what is offered (the scenario above), or a lever on income itself, which these changes avoid on purpose:
  * the 🔥 x3 bonus cap (`game/x3_week.py` CAP 3 000 a shift) — the rich hit it every week;
  * bầu cua / xóc đĩa / lô tô are at the owner's 53 % ("tổng phải lời"): one-face bầu cua returns +21 % per xu staked,
    lô tô +16 %. A 50 % win rate would make them about even;
  * a visible thuế thu nhập on very high days, or higher asset rates.
* Old Mây terms keep 0,3 % until they end; the bank's long term deposits (up to 8,8 %/năm) were left as they are.

## Compatibility (rolling release)

* New state only in `journey['upk']` (optional; `journey.validate` of 1.4.25 allows extra journey keys and ignores it:
  an older server simply does not bill, the next morning on this build catches up). No new key in `garage`, `home`,
  `invest` or `fair` (their older validators are strict). Sổ ví rows use the existing kind `upkeep`.
* New vehicle ids pass 1.4.25's garage validator (unknown ids are allowed by shape and kept).
* New public fields are optional: an older client ignores `upkeep` / `care` / `save_tier`; a newer client against an
  older server shows no fee chips and the older texts.
* Fair: a phóng dao run in progress during the deploy is paid on the new ladder (a few minutes).
