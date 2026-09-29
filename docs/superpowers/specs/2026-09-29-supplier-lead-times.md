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

| Kind | Rule | Card wording |
|---|---|---|
| `rush` | Arrives `mins = (lo, hi)` minutes after the order. | "⚡ 30–60 phút · ~14:50" |
| `runs` | Fixed delivery runs `(cutoff, lo, hi)`: the first run whose cutoff is still ahead today; else tomorrow's first run. | "🚚 Chiều nay ~16:45" |
| `next` | Next-day drop at `open + at` (before opening when `at` is negative) if ordered before `cutoff`, else the day after. | "🧺 Sáng mai 07:15" |
| `days` | Specialty / import: `days = (a, b)` days later (seeded), at `open + at`. | "✈️ 2–3 ngày · ngày 6" |

Anything that would land after closing time moves to the next morning, 30 minutes before opening
(the crate waits at the door). Each supplier also has `factor` (price ×), `short` (% chance a box is packed
short, as before), `late` (% chance of a delay), an optional `items` list (what it sells; `None` = everything),
an optional `fresh` (+days of life for perishable goods, Đà Lạt flowers) and a `voice` with `good / bad / claim / late`.

**Reliability.** At order time the arrival is picked inside the promised window from a seeded roll
(`day, order seq, item, supplier`). With probability `late` the goods come later: rush +15–30 min,
runs/next +60–120 min, days +1 day. The player sees the promised window until it passes; then the order shows
the supplier's reason ("Kẹt xe ở cầu Mây…") and the new time. Goods are never lost.

## 3. Suppliers per career

`partner` and `express` exist in every career (other code sends them: grocery bulk orders use `express`,
the round-trip test uses `partner`). Old ids stay valid for old saves.

| Career | Suppliers (id · window · price) |
|---|---|
| restaurant | market Chợ đầu mối Mây · sáng mai trước giờ mở, đặt trước 17:00 · ×0.85 · hay thiếu · partner Hạt Nắng · 2 chuyến 13:00 & 17:00 · ×1 · express Mây Xanh · 30–60 phút · ×1.35 · import Kho hàng nhập Kim Mây · 2–3 ngày · ×0.72 (broth packs, kim chi, cheese, rice cakes, fish balls, sausage, beef) |
| cafe_bakery | market (milk, cream, butter, egg, flour, sugar, almond, oat, condensed) · partner · express · roaster Xưởng rang Đồi Mây · trưa mai 10:00–11:00, đặt trước 18:00 · ×0.8 (beans) |
| florist | market Chợ hoa đêm Sương Mai · sáng mai trước giờ mở, đặt trước 22:00 · ×0.85 · 25% gãy/thiếu cành (flowers, fillers) · dalat Nhà vườn Đà Lạt · xe đêm, sáng mai 08:30–10:00 nếu đặt trước 15:00 · ×0.7 · tươi thêm 1 ngày · partner · express ×1.4 |
| grocery | market (fresh goods) · partner · express · wholesale Tổng kho sỉ Mây Xanh · 1–2 ngày · ×0.8 (rice, noodles, fish sauce, oil, soap, snacks, drinks) |
| repair | market Chợ linh kiện Mây · sáng mai, đặt trước 16:00 · ×0.8 (compatible & used parts, consumables) · partner · express · genuine Kho chính hãng · 2–3 ngày · ×0.85 (genuine screens, batteries, capacitors, heaters, motors, SSD) |
| farm | coop HTX Nông nghiệp Mây · sáng mai 06:30–07:30, đặt trước 16:00 · ×0.8 (seeds, fertiliser, sprays, feed, packing) · partner · express · nursery Trại giống Đồng Xanh · 2–3 ngày · ×0.7 (tomato, cucumber, herb seedlings) |
| delivery | market Chợ bao bì Mây · chiều mai trước ca · ×0.8 · partner · 2–4 giờ (rush kind) · express |
| homestay | market Chợ sáng (breakfast, minibar) · partner · express · textile Xưởng dệt Hòa Mây · 2–3 ngày · ×0.7 (linen, towels, soap kits) |
| pet_care | wholesale Kho sỉ thú cưng Mây · sáng mai · ×0.82 · partner · express · import Hàng nhập Nhật Mây · 2–3 ngày · ×0.8 (sensitive shampoo, conditioner, styptic) |
| salon | market Chợ sỉ vật tư tóc · sáng mai · ×0.85 (towels, gloves, foil, shampoo, conditioner, retail) · partner · express · brand Kho hãng màu nhuộm · 2–3 ngày · ×0.75 (dyes, developers, toners, bleach, keratin) |

`partner` (Nhà phân phối Hạt Nắng) runs twice a day, cut-offs 11:00 and 15:00, drops 13:00–14:00 and
16:30–17:30. The delivery career overrides it to a 2–4 hour `rush` window because its shift starts at 17:00.

## 4. Orders and API

Commands are unchanged: `inv_order {item, qty, supplier, confirm}`, `inv_receive {order, count}`,
`inv_claim`, `inv_rate`, `inv_discard`. New rules:

- `inv_order` refuses a supplier that does not sell the item ("X không bán Y. Chọn nhà khác nhé.").
- The result adds `eta` (the order's public ETA block) next to `message`. The message says
  "Nhà phân phối Hạt Nắng giao chiều nay ~16:45 (16:30–17:30)".
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
