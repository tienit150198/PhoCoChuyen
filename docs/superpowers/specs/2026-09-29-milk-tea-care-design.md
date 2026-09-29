# Trà Mây & Trân Châu — care loop, real supplier windows, pinned serve bar

Date: 2026-09-29 · Career `milk_tea` · Files: `game/boba.py`, `public/js/careers/milk_tea.js`,
`public/css/careers/milk_tea.css`, `tests/test_milk_tea.py`, `tests/test_milk_tea_care.py`.
(`game/experiences.py`, `game/engine.py`, `app.js`, `app.css`, `food_kit.js` and `boba-world.js` are untouched.)

## Goal

Every milk-tea shift used to stand on its own: tea and toppings were bought instantly at cost from the
Kho sheet, cups appeared the moment you paid, pearls simply expired at midnight. This change gives the
counter things to look after **during the day and from one day to the next**, like the other food
counters, and makes ordering use real delivery times like the shared inventory
(`docs/superpowers/specs/2026-09-29-supplier-lead-times.md`).

All rules are server-side and deterministic (seeded from day, order number, item and supplier; nothing is
rolled twice). Old saves load, every existing command keeps its name and payload, and every penalty has
a cheap way out on the same day.

## 1. One shop clock

`boba.clock_minutes(c)` already turned beats into a time of day (08:00–20:00). Two fixes make it a clock
that goods and pots can run on:

* `span` (beats that fill the opening hours) is fixed at `start_day` as `max(30, quota × 12)` and stored,
  so the clock never runs backwards when more guests arrive (before, a VIP guest raised the quota and
  pulled the clock back).
* A busy day runs into **overtime**: after `span` beats the clock keeps going 5 minutes per beat, up to
  23:00 (HUD: "🕐 20:35 · tăng ca"). Suppliers are closed then; pots keep ageing slowly.

`now_abs(c) = day × 1440 + minute` while open; closed, it reads the evening of the day that just closed
(20:00), exactly like `inventory.clock`. The shop's hours equal `inventory.hours('milk_tea')` (the default
08:00–20:00) — a test guards this.

## 2. Made at the counter vs. bought

| Kind | Items | How you get it |
|---|---|---|
| **Made** (`MADE`) | 6 tea bases (brewed), trân châu đen / trắng (cooked), foam, kem cheese (whipped) | `tea_prepare {item, qty, confirm}` — paid at cost, ready now. Brewing / cooking takes **one beat (20 minutes) while the shop is open**, none before opening. |
| **Bought** (`BOUGHT`) | syrups, thạch, popping, 3Q, pudding, nha đam, thạch dừa, đậu đỏ, flan, cups M/L | `tea_order {item, qty, supplier, confirm}` — paid now, delivered at a real time. `tea_prepare` refuses them with a pointer to Kho → Đặt hàng. |

`tea_cups {size, confirm}` keeps working: it now orders one pack (20 cups) from Hạt Nắng (or the
`supplier` in the payload) instead of stacking cups instantly.

## 3. Pots and pearl batches go stale (`lot.made`)

A brewed pot or a cooked batch remembers when it was made (`made`, absolute minutes; brewed before opening
counts as made at 08:00).

| Item | 🟢 fresh | 🟡 tired | 🔴 stale |
|---|---|---|---|
| trân châu đen / trắng | ≤ 4 h "dẻo mềm" | ≤ 6 h "hơi cứng" | "cứng": thrown away |
| tea bases | ≤ 6 h "thơm" | ≤ 9 h "hơi chát" | "ôi": thrown away |

* Cups draw the **oldest batch first**. A tired portion marks the cup (`cup.tired`), and at hand-off the
  guest records a **small slip** (sev 1, "Trân châu hơi cứng, nhai mỏi cả hàm." / "Trà ủ lâu quá nên hơi
  chát.") — 4★ at worst, and a strict guest may ask for a remake like any other slip.
* `tea_toss {item}` (free) pours out the tired batches so the next cup uses the fresh one; logged as waste.
* Stale batches are thrown away by themselves the moment the clock passes them (waste logged once, a
  message says so). They never count as stock.
* **Nothing brewed or cooked stays overnight**: at closing every pot and batch left is logged as waste
  ("Trà ủ và trân châu không để qua đêm"). The care list warns from 17:00 how many portions will go.
* Upgrade **Nồi ủ trân châu** now keeps pearls soft 2 hours longer (it used to add a day of shelf life).
* Lots without `made` (opening stock, older saves, fixtures) count as fresh until closing.

The balance this gives: brew and cook before opening (no clock cost), cook a second small batch around
midday, and do not brew a big pot late in the afternoon.

## 4. Supplier orders with real windows (`data.boba.orders`)

Four suppliers, same kinds and wording as the shared inventory. Promises and the actual arrival use
`inventory._schedule` / `inventory.quote` / `inventory.when` (read-only helpers) with the counter's clock,
so milk tea and the other shops say the same thing the same way.

| id | Name | Kind | Price | Sells |
|---|---|---|---|---|
| `market` | 🧺 Chợ đầu mối Mây | next: đặt trước 17:00 → sáng mai trước giờ mở | ×0.8 | syrups, thạch mây, 3Q, nha đam, thạch dừa, đậu đỏ, cups |
| `partner` | 🚚 Nhà phân phối Hạt Nắng | runs: đặt trước 11:00 → 13:00–14:00, trước 15:00 → 16:30–17:30 | ×1.0 | everything bought |
| `express` | ⚡ Giao hỏa tốc Mây Xanh | rush: 30–60 phút | ×1.35 | everything bought |
| `factory` | ✈️ Xưởng topping Đài Mây | days: 2–3 ngày | ×0.65 | boxed toppings, cups |

* Stored order: `{id, item, qty, supplier, cost, unit, placed, lo, hi, at, late}`; `at` and `late` stay on
  the server until the promised window has passed ("⏰ Tài xế phải vòng tránh…"). Goods are never lost.
* Deliveries are unpacked when the clock passes `at` (at every counter action, and at `start_day` for
  goods waiting at the door). Anything due after closing waits for the next morning.
* Limits: 12 open orders; shelf limit 60 portions per item **including goods on the way**; cups up to
  120 per size including packs on the way. No "nhịp" anywhere in the ordering flow.
* Bình's short-delivery surprise: "Trả cả thùng, hẹn giao lại" now really re-orders the billed amount from
  Hạt Nắng's next run (paid when re-ordered, if the till allows), instead of nothing.
* `tea_wait` (one beat, open only, when an order or a guest is waiting): "⏳ Chờ thêm 20 phút".

## 5. When something runs out: swaps (`tea_swap {task, item}`)

Out of a syrup or topping the order needs: "🙏 Mời khách đổi" swaps it for the natural fallback in stock
(thạch 3Q → thạch mây…), or another syrup / none; the price follows. Out of a cup size: the guest moves
to the other size — up to L at M's price (a discount of the size-L surcharge), or down to M paying M.
No beat, a little patience (−6 / −4). Walk-ins do not order bought items the board shows as out
(`src.avoid`); regulars' usual cups still can, which is what the swap is for.

## 6. Heat-sealer upkeep (`sealer_wear`, `cleaned`)

Every film seal (not the dome lid) adds one to `sealer_wear`. From 12 the plate is "bám keo": the green
zone narrows to 1.7–2.3 s (burn from 3.8 s); from 20 it is "bẩn": 1.9–2.1 s (burn 3.4 s), and even the
automatic sealer only makes an "ok" seal. `tea_clean` (one beat) resets it. The gauge the player sees is
the real one (`public.seal`). With 5–10 cups a day that is a clean every two days or so.

## 7. Regulars' card (`NOTES`)

Each of the three regulars has two notes (Linh: kỹ chuyện đường, ôn thi nên cần nắp kín; Bác Tư: răng
yếu nên ít đá, bác sĩ dặn bớt ngọt; Miu: chụp ảnh ly, hơi kém sữa). Note 1 after the first cup served,
note 2 after the third; unlearned notes never leave the server. The card sits in the order bubble with a
"👋 Như mọi khi hả?" button (`tea_greet {task}`: once per order, no beat, +8 patience, +1 bond; a clean
cup to a greeted regular earns a 2-xu thank-you).

## 8. Tomorrow's forecast and the care list

Tomorrow's luck of the day is already fixed by the day number (`roll_mod(day + 1)`), so it is shown from
14:00, in the evening Kho sheet and in the close summary, with one line of advice (students → nấu thêm
một mẻ trân châu buổi chiều, xếp đủ ly L; heat → đặt thêm siro…). From 14:00 there is still time to
order from the market before its 17:00 cut-off.

`public.care` (server-computed rows, tone ok / warn / danger): pearl batches with "dẻo tới 12:20" /
"cứng lúc 14:20", tired or unbrewed tea, sealer wear, low cups, orders on the way, the overnight
warning, tomorrow. The counter shows it as a fold "🧋 Việc chăm quầy" (opens by itself when something is
red) with one-tap buttons (Nấu +5, Đổ mẻ cũ, Lau máy); the Kho tab shows it in full.
`public.night` keeps the lines of the last close and the morning deliveries.

## 9. Counter UI (390 px first)

* **Sticky bar** (food_kit `actionBar` + `keepBarAboveFooter`, styles copied under `.career-job.mt`): a
  one-line recap "✓ Ly M · ✓ trân châu đen · 50% đường · ít đá" (each part ticked when the cup matches;
  a "như mọi khi" order uses the notebook's usual) and "🛎️ Giao · 40 xu". Hidden from 900 px, where the
  cup column is sticky; the in-flow serve button is hidden below 900 px so there is only one.
* **"Lấy ly"** in the empty cup was ~7 px: the SVG had class `empty`, which picked up the app-wide
  `.empty` card padding and shrank the drawing to half. Renamed to `mt-cup-empty`, text 17 units (≈14 px).
* Station tiles: out-of-stock made items offer "Nấu / Ủ / Đánh +5"; bought items offer "⚡ +5 · 14 xu"
  (express) or show "📦 ~12:05 hôm nay" when an order is on the way; tired batches are outlined.
* Kho tab: clock line, care list, "Nồi, bình & mẻ hôm nay", "Đang giao" (ETA, countdown, progress, late
  note, "⏳ Chờ thêm 20 phút"), "Đặt hàng" with a supplier picker (qty chips; per supplier the live
  promise "Sáng mai ~07:05" / "30–60 phút · tới ~12:05", price, "rẻ nhất / đắt / hay trễ"; suppliers that
  do not sell the item are shown disabled).

## Saves and validation

* `fresh()` gains `span, orders, order_seq, sealer_wear, cleaned, night`; `state()`/`view()` fill them in
  for older saves. Lots without `made`, cups without `tired`, tasks without `greeted` are fine.
* `validate`: orders exactly the stored key set, unique ids, known supplier and item, qty 1–20 (cups 1–5),
  `placed ≤ lo ≤ hi`, on time `lo ≤ at ≤ hi`, late `at > hi` with a reason; `made` only on tea/pearl lots;
  sealer wear 0–999; night lines ≤ 8. `validate_task`: `cup.tired` ⊆ fresh items in the cup, `greeted`
  bool; the new `set flavor` change (swap) is checked like the others.

## Needs from the lead (outside my files)

* i18n: new Vietnamese strings in `milk_tea.js` and `boba.py` need `scripts/i18n_extract.py` + English.
* Optional: `app.js hudClock` could show "tăng ca" for any career whose clock passes closing.
