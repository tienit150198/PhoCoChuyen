# Giờ giao hàng thật cho nhà cung cấp (supplier lead times)

## Goal

The owner: "ordering from different suppliers should take different waiting times; no more 'wait 1 beat (nhịp)'
— real, different waiting times until the goods arrive."

Before: `game/inventory.py` had three suppliers for every trade career with a lead in turns
(`market` 2, `partner` 1, `express` 0). Messages and the Kho sheet said "sau N nhịp làm việc",
"TỚI SAU N NHỊP", "Chờ một nhịp".

After: every supplier promises a delivery window in **in-game clock time** (giờ trong ngày), each career
has 2–5 suppliers with a clear trade-off (price factor, window, reliability), and the ordering flow never
talks about beats.

Scope: `game/inventory.py`, the inventory part of `public/js/v4/views.js`, `tests/test_inventory*.py`.
Everything else (engine, career plugins, `app.js`, CSS) is untouched; the few engine lines that would
make it tidier are listed at the end as optional.

## 1. One clock for every stocked career

A single helper, `inventory.clock(c, career, turn=None)`, turns the career's turn counter into a time of day:

| Piece | Rule |
|---|---|
| Opening hours | `HOURS[career] = (open, close)` in minutes. Default 08:00–20:00. Restaurant 10:00–22:00, café 07:00–19:00, florist 07:30–19:30, grocery 06:30–21:30, repair 08:00–19:00, farm 05:30–17:30, delivery 17:00–23:00 (evening shift, matches its route clock), homestay 07:00–22:00, pet care 08:00–19:00, salon 08:30–20:00. |
| Minutes per turn | `STEP = 20`. One ticking action ≈ 20 minutes of shop time. A typical day of 25–35 actions fills the opening hours. |
| Day open | `now = open + (turn − turn0) × STEP`, capped at `close`. `turn0` is the turn of that day's `start_day`: stored in `ext.inv.opened` when known, otherwise read from the journal row "Mở ca ngày N." that `start_day` always writes (1200-row journal, so the current day's row is always there). |
| Day closed | After `end_day` the engine has already moved to day N+1. The clock then reads **the evening of day N at closing time**: `(day − 1, close)`. So an order placed after closing is an evening order, and anything due before the next opening is waiting at the door when `start_day` runs. |
| Career hook | If a career plugin defines `clock_minutes(c) -> int | None` (minutes since midnight while open), it wins over the turn formula. None does today; `delivery` is the obvious candidate. |
| Absolute time | `abs = day × 1440 + minute`. Orders store absolute minutes, so "today / tomorrow / ngày 7" all compare with one number. |

`public()` returns `clock = {day, minute, time "14:20", open, close, step, is_open, label}` so the Kho sheet
can show "Bây giờ 14:20".

## 2. Supplier kinds

Values below are the halved waits of §8 (2026-09-29).

| Kind | Rule | Card wording |
|---|---|---|
| `rush` | Arrives `mins = (lo, hi)` minutes after the order (express 15–30). | "⚡ 15–30 phút · tới ~14:35" |
| `runs` | Fixed delivery runs `(cutoff, lo, hi)`: the first run whose cutoff is still ahead today; else tomorrow's first run. Hạt Nắng: four runs. | "🚚 Chiều nay ~16:15" · "Bốn chuyến/ngày · 10:00, 13:00, 16:00 & 19:00" |
| `next` | Optional same-day run `day_run = (cutoff, lo, hi)` for morning orders; any later order rides the night run to `open + at` next morning (before opening when `at` is negative). `cutoff` (the night run's) `None` = until closing; with a cutoff, a later order waits for the day after. | "🧺 Chiều nay ~15:30" · "Chiều nay nếu đặt trước 13:00, sau đó sáng mai" |
| `days` | Specialty / import: `days = (a, b)` days later (seeded), at `open + at`. | "✈️ 1–2 ngày · ngày 6–7", "1 ngày · ngày 6" |

Anything that would land after closing time moves to the next morning, 30 minutes before opening
(the crate waits at the door). Each supplier also has `factor` (price ×), `short` (% chance a box is packed
short, as before), `late` (% chance of a delay), `delay` (how late a late delivery is, minutes), an optional
`items` list (what it sells; `None` = everything), an optional `fresh` (+days of life for perishable goods,
Đà Lạt flowers) and a `voice` with `good / bad / claim / late`.

**Reliability.** At order time the arrival is picked inside the promised window from a seeded roll
(`day, order seq, item, supplier`). With probability `late` the goods come later by `delay`: rush +10–15 min,
runs/next +30–60 min, days +4–6 hours (`inventory.DELAY`). A supplier dict without `delay` (a table written
before §8, e.g. milk tea's own in `game/boba.py`) keeps the old delays: rush +15–30 min, runs/next +60–120 min,
days +1 day. The player sees the promised window until it passes; then the order shows the supplier's reason
("Kẹt xe ở cầu Mây…") and the new time. Goods are never lost.

## 3. Suppliers per career

`partner` and `express` exist in every career (other code sends them: grocery bulk orders use `express`,
the round-trip test uses `partner`). Old ids stay valid for old saves.

| Career | Suppliers (id · window · price) |
|---|---|
| restaurant | market Chợ đầu mối Mây · chiều nay 15:00–16:00 nếu đặt trước 13:00, sau đó sáng mai trước giờ mở · ×0.85 · hay thiếu · partner Hạt Nắng · 4 chuyến 10:00, 13:00, 16:00 & 19:00 · ×1 · express Mây Xanh · 15–30 phút · ×1.35 · import Kho hàng nhập Kim Mây · 1–2 ngày · ×0.72 (broth packs, kim chi, cheese, rice cakes, fish balls, sausage, beef) |
| cafe_bakery | market (milk, cream, butter, egg, flour, sugar, almond, oat, condensed) · partner · express · roaster Xưởng rang Đồi Mây · chiều nay 14:00–15:00 nếu đặt trước 11:00, sau đó sáng mai 08:30–09:00 · ×0.8 (beans) |
| florist | market Chợ hoa đêm Sương Mai · chiều nay 16:00–17:00 nếu đặt trước 15:00, sau đó sáng mai trước giờ mở · ×0.85 · 25% gãy/thiếu cành (flowers, fillers) · dalat Nhà vườn Đà Lạt · xe khách chiều nay 15:00–16:30 nếu đặt trước 09:00, sau đó xe đêm, sáng mai 08:00–08:45 · ×0.7 · tươi thêm 1 ngày · partner · express ×1.4 |
| grocery | market (fresh goods) · partner · express · wholesale Tổng kho sỉ Mây Xanh · 1 ngày (sáng mai 07:30–08:30) · ×0.8 (rice, noodles, fish sauce, oil, soap, snacks, drinks) |
| repair | market Chợ linh kiện Mây · chiều nay nếu đặt trước 13:00, sau đó sáng mai · ×0.8 (compatible & used parts, consumables) · partner · express · genuine Kho chính hãng · 1–2 ngày · ×0.85 (genuine screens, batteries, capacitors, heaters, motors, SSD) |
| farm | coop HTX Nông nghiệp Mây · chiều nay 13:00–14:00 nếu đặt trước 11:00, sau đó sáng mai 06:00–06:30 · ×0.8 (seeds, fertiliser, sprays, feed, packing) · partner · express · nursery Trại giống Đồng Xanh · 1–2 ngày · ×0.7 (tomato, cucumber, herb seedlings) |
| delivery | market Chợ bao bì Mây · tối nay 21:00–22:00 nếu đặt trước 20:00, sau đó chiều mai trước ca · ×0.8 · partner · 1–2 giờ (rush kind) · express |
| homestay | market Chợ sáng (breakfast, minibar) · partner · express · textile Xưởng dệt Hòa Mây · 1–2 ngày · ×0.7 (linen, towels, soap kits) |
| pet_care | wholesale Kho sỉ thú cưng Mây · chiều nay / sáng mai · ×0.82 · partner · express · import Hàng nhập Nhật Mây · 1–2 ngày · ×0.8 (sensitive shampoo, conditioner, styptic) |
| salon | market Chợ sỉ vật tư tóc · chiều nay / sáng mai · ×0.85 (towels, gloves, foil, shampoo, conditioner, retail) · partner · express · brand Kho hãng màu nhuộm · 1–2 ngày · ×0.75 (dyes, developers, toners, bleach, keratin) |

`partner` (Nhà phân phối Hạt Nắng) runs four times a day, cut-offs 09:00, 12:00, 15:00 and 18:00, drops
10:00–10:30, 13:00–13:30, 16:00–16:30 and 19:00–19:30 (a drop after the shop's closing waits at the door
before the next opening). The delivery career overrides it to a 1–2 hour `rush` window because its shift
starts at 17:00.

## 4. Orders and API

Commands are unchanged: `inv_order {item, qty, supplier, confirm}`, `inv_receive {order, count}`,
`inv_claim`, `inv_rate`, `inv_discard`. New rules:

- `inv_order` refuses a supplier that does not sell the item ("X không bán Y. Chọn nhà khác nhé.").
- The result adds `eta` (the order's public ETA block) next to `message`. The message says
  "Nhà phân phối Hạt Nắng giao chiều nay ~16:15 (16:00–16:30)".
- `inv_receive` before arrival: "Hàng chưa tới. Dự kiến 16:45 hôm nay — làm việc khác trong lúc chờ nhé."
  It checks the clock of the moment you walk to the door (before this action's own 20 minutes), matching
  `ready_now` in the public state.

Stored order (new shape): `placed, lo, hi, at` (absolute minutes) and `late` (reason or `None`); no `ready`.
Public order adds (all derived; `at` and `late` stay hidden until they are due, like `actual`):

| Field | Meaning |
|---|---|
| `ready_now`, `count_hint` | as before |
| `eta_label` | "16:45 hôm nay", "Sáng mai 07:15", "Ngày 6 · 10:30" |
| `window` | promised window, "16:30–17:30" or "ngày 6" |
| `arrives_day`, `arrives_time` | day number and "16:45" of the current estimate |
| `arrives_turn` | estimated turn when it arrives today (turn clock only), else `None` |
| `left_label` | countdown: "còn ~1 giờ 20 phút", "mai, trước giờ mở cửa", "còn 2 ngày" |
| `progress` | 0–1 of the wait already passed |
| `late_note` | shown once the promised window has passed and the goods are late |

Public suppliers add `kind, window, items, fresh, late` and a live `quote {label, eta_label, day, time}` for
"if you order now". `content().inventory` keeps `suppliers` (the three shared ones, with a legacy `lead`
estimate in turns for older clients) and adds `by_career`.

## 5. Old saves

Old in-transit orders carry `ready` (a turn). `inventory.migrate(s)` / the lazy `_upgrade` turn them into
the new shape: `at = now + max(0, ready − turn) × STEP` (pushed to the next morning if that is after closing),
`lo = hi = at`, `placed = now`, `late = None`. Received orders just lose `ready`. The upgrade runs lazily at
the start of every inventory action and at closing; `public()` upgrades a copy. `validate` is strict for both
shapes (legacy: `ready` and none of the new fields; new: `placed ≤ lo ≤ hi ≤ at`-or-late with the right
`late`), and supplier ids must be the career's suppliers or one of the three legacy ids.

## 6. UI (Kho sheet)

- Status strip: "🕑 Bây giờ 14:20" (or "Đã đóng cửa · mở lại 08:00").
- Supplier cards: emoji + name, the live quote in plain words, then price ("rẻ nhất ×0,85"),
  reliability ("hay thiếu", "hay trễ", "tươi thêm 1 ngày"), rating. Suppliers that do not sell the item are
  shown disabled with "Không bán mặt hàng này".
- Order total line repeats the promise: "Dự kiến nhận: Sáng mai 07:15".
- "Đang giao" rows: "Dự kiến nhận: 16:45 hôm nay" + countdown + a progress bar, the late note when late,
  and a "⏳ Chờ thêm 20 phút" button (the existing `advance` command) instead of "Chờ một nhịp".
- No "nhịp" wording in the ordering flow. Phone first (390 px), existing classes and theme tokens only.

## 7. Optional engine lines (for the lead)

Nothing is required: the journal fallback makes the clock work today. Two one-liners make it tidier:

1. `game/engine.py` `migrate_state`, next to `cst.migrate(s)`:
   `inv.migrate(s)  # kho: đơn nhập cũ theo nhịp → giờ giao dự kiến`
2. `game/engine.py` `start_day`, right after `ops.on_start(s,c,career)`:
   `inv.on_open(s,c,career)  # kho: ghi nhịp mở ca cho đồng hồ giao hàng`

Later waves: the HUD clock (`app.js hudClock`) can fall back to `c.inventory?.clock?.time`, and careers
with their own supplier code in turns (listed in the hand-off report) can reuse `inventory.clock`.

## 8. Waits halved (2026-09-29, later the same day)

The owner: "players who restock feel the wait is long; reduce the restock waiting time to 50% of the
current one."

**How the wait is measured.** For every stocked career and supplier, an order is placed at every 20-minute
step of the working day (opening to closing) with 20 seeded rolls each, late deliveries included. The wait is
counted two ways: *working minutes* (opening-hours minutes between the order and the goods at the door: the
time the player actually works through; the night passes with one tap) and *clock minutes* (`at − placed`,
nights included). Averages are per supplier, then per kind. `tests/test_inventory_lead_times.py` (`HalfWait`)
recomputes the old numbers from a frozen copy of the old table and the old scheduling rules, and asserts
45–55 % in working minutes and 40–60 % in clock minutes for every kind.

| Kind | Before | After | Working wait (avg) | Clock wait (avg) |
|---|---|---|---|---|
| `rush` | express 30–60 min; delivery's partner 2–4 h; late +15–30 min | express **15–30 min**; delivery's partner **1–2 h**; late +10–15 min | 55 → 29 min (53 %) | 3.0 → 1.7 h (55 %) |
| `runs` | Hạt Nắng: 2 runs, cut-offs 11:00 / 15:00 → 13:00–14:00 / 16:30–17:30; later → tomorrow 13:00; late +60–120 min | **4 runs**, cut-offs 09:00 / 12:00 / 15:00 / 18:00 → 10:00, 13:00, 16:00, 19:00 (30-min windows); later → tomorrow 10:00; late +30–60 min | 365 → 176 min (48 %) | 10.8 → 6.2 h (57 %) |
| `next` | next morning if ordered before a cut-off (15:00–23:30), else the day after; morning offsets up to +4 h; late +60–120 min | **same-day run** for morning orders (market 13:00 → 15:00–16:00; roaster 11:00 → 14:00–15:00; Đà Lạt 09:00 → 15:00–16:30 by day coach; co-op 11:00 → 13:00–14:00; florist market 15:00 → 16:00–17:00; packaging market 20:00 → 21:00–22:00); every later order that day rides the night run to the next morning (no more "day after tomorrow"); positive morning offsets halved; late +30–60 min | 561 → 272 min (49 %) | 23.3 → 11.3 h (49 %) |
| `days` | 2–3 days (grocery wholesale 1–2) at open + 1–5 h; late +1 day | **1–2 days** (wholesale **1 day**, the minimum: next day), at open + half the old offset; late +4–6 h | 1643 → 813 min (49 %) | 56.4 → 30.2 h (53 %) |

Why these shapes:

- `rush`: both ends halved (30–60 → 15–30). 15 minutes is below one 20-minute step, but the order is never at
  the door in the same action: the door check reads the clock before the action's own step, so at least one
  step always passes (tested).
- `runs`: the long wait was the afternoon order that missed the 15:00 cut-off and waited for tomorrow's
  13:00 run. Doubling the runs to four, spread every three hours with the last cut-off at 18:00, halves it
  and keeps the fiction (a distributor's van on a loop). A 19:00 drop after an early closing (café, repair,
  pet care, farm) waits at the door before the next opening, as every after-hours drop does.
- `next`: "tomorrow morning" cannot be halved on its own: a pre-opening drop already costs only the rest of
  today. Halving it needs a same-day run for morning orders, plus letting every order placed later that day
  catch the night run (the old evening cut-offs sent late orders to the day after tomorrow). Each supplier
  gets a run that suits it: the market's handcart, a second roast, Đà Lạt's day coach, the co-op's midday
  truck. Morning offsets after opening are halved too (roaster 10:00–11:00 → 08:30–09:00, Đà Lạt
  08:30–10:00 → 08:00–08:45, co-op 06:30–07:30 → 06:00–06:30).
- `days`: the day range is halved and rounded up, never below the next day (2–3 → 1–2, 1–2 → 1). The arrival
  hour after opening is halved, and a late van is now a few hours late, not a day.
- Late deliveries keep the same chance per supplier (`late` %); only the delay is shorter.

Labels follow the data: `_window_label` counts the runs ("Bốn chuyến/ngày · …"), names the same-day run
("Chiều nay nếu đặt trước 13:00, sau đó sáng mai"; "…, trước 16:00 thì sáng mai" when the night run closes
before the shop does), writes "1 ngày" for a single-day range, and the supplier notes and late voices say the
new numbers (tested: no "30–60", "2–3 ngày", "Hai chuyến", "trễ một ngày" left in the inventory tables).
`_lead_turns` (legacy `lead` for older clients) halves too: runs 6 → 3, next 18 → 9.

**Old saves.** An order stores its promised window (`placed, lo, hi, at, late`), so an order placed before
this change keeps the window it was promised: it is never re-promised, stranded or delivered twice (tested
with an old 3-day import and an old 16:30–17:30 van run). Beat-based `ready` orders upgrade as in §5. No new
stored fields; `validate` is unchanged.

**Other restock waits.** `game/engine.py` `STOCK_SUPPLIERS` (mother & baby, pharmacy) copy `inv.MARKET`,
`inv.PARTNER` and `inv.EXPRESS`, so their timing halves with this table; their `note` strings and the pharmacy
depot's own 16:00 night cut-off live in the engine. `game/boba.py` (milk tea) has its own supplier table using
`_schedule` / `quote`; without `delay` it keeps the old waits until its table is updated the same way.
`game/careers/repair.py` sources parts from Lâm (before 12:00 → 15:00 today, else tomorrow) and the city
distributor (the day after tomorrow) with its own constants. Crop growth, pre-order lead days (florist) and
anniversary calls (homestay) are not restocking and are unchanged.
