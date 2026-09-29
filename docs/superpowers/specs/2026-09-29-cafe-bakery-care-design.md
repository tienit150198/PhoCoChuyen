# Tiệm Bánh & Cà Phê Sớm Mai — care loop (sub-project 3)

Date: 2026-09-29 · Career `cafe_bakery` · Files: `game/careers/cafe_bakery.py`,
`public/js/careers/cafe_bakery.js`, `public/css/careers/cafe_bakery.css`,
`tests/test_career_cafe_bakery.py`.

## Goal

Until now every bakery shift stood on its own: dough shaped in the afternoon
simply went flat, the day-old basket was the only thing that carried over. This
change adds four small things to look after **from one day to the next**, all
tied to the oven and the counter the player already uses:

1. **Bé Men**, the shop's sourdough starter, fed once a day.
2. **Dough that proofs overnight** in the fridge for tomorrow's first bake.
3. **The morning case**: yesterday's pastries waiting for a decision.
4. **Sổ khách quen**: what the regulars always want, learned visit by visit.

Everything is server-authoritative and deterministic (no new randomness), old
saves load, every existing command keeps its payload and meaning, and missing a
day costs a little but is always fixed the same day.

## 1. Bé Men — the sourdough starter (`data.starter`)

`{strength 10..100, fed: day last fed, feeds}`. Start: strength 70, never fed.

* `cb_feed` (one beat, once per shift day, 1 flour): strength +20, or +30 when
  it is hungry (< 40). Capped at 100.
* Overnight (day close): fed today −5, not fed −25. Never below 10 — the
  starter sleeps, it never dies.
* Only the **bánh mì que** is leavened with Bé Men (croissants use yeast):

  | strength | band | bánh mì proofing | bread |
  |---|---|---|---|
  | ≥ 80 | 💪 Sung sức | 2 beats | as baked |
  | 40–79 | 🙂 Ổn | 3 beats (as before) | as baked |
  | < 40 | 😴 Đói | 5 beats | golden/dark trays come out **đặc ruột** (`dense`) |

  The band is read when the dough is shaped (`tray.dense`), so feeding first and
  shaping after is the right order. A dense loaf still sells but counts like a
  pale one (freshness 3, a small "bake quality" slip).
* Pace: fed daily it sits at 85–100. One missed day: 95 → 70 (still fine).
  Three missed days: hungry; one feed brings it back to "ổn" at once.
* The baker on staff feeds Bé Men first when nobody has.

## 2. Overnight cold proof (`data.cold`, the fridge)

* `cb_chill {tray}` moves a shaped tray from the warm proofer into the fridge
  (2 shelves). The rise stops; the tray remembers the day it went in.
* A chilled tray is baked with the existing `cb_bake {item, tray}` from the
  **next** day on, with no waiting and no over-proof clock (the fridge did the
  proofing). Bake it within two nights; at the close of the second day an
  unbaked tray is logged as waste (over-fermented).
* **Warm dough does not survive the night**: at day close every tray still in
  the warm proofer is thrown away and logged as waste ("bột ủ ấm qua đêm bị
  chua"). The care list warns before closing whenever warm trays are left.
* Tomorrow's luck of the day is already fixed, so the forecast drives the plan:
  when tomorrow brings 2+ walk-in buyers per guest (exam, market, festival) the
  care list asks for one tray chilled tonight.

## 3. The morning case

No new rules — yesterday's pastries could already be marked down, donated or
thrown away. The care list now names them each morning ("3 bánh hôm qua chờ xử
lý") so the decision is not forgotten, and the close summary says how many will
be waiting.

## 4. Regulars' notes card (`data.book`)

`book[npc_id] = {visits, notes:[note ids]}`. Each of the seven guests has two
notes (static table `NOTES`: Chú Lâm's espresso, Chị Thảo's lactose, Bà Sáu's
heart and soft bread…). Note 1 is learned after the first served order, note 2
after the third. Unlearned notes never leave the server.

* A task records `regular` (notes known when it arrived, 0–2) in `on_task`.
* `cb_greet {task}` (no beat, once per task, needs a learned note): "Như mọi
  khi hả chú?" — the guest gains 8 patience.
* The review of a regular gets a row "Nhớ khách quen": 5 when greeted, 4 when not.

## The care list (`public_data.care`)

Server-computed rows for `ui-kit.reqList`: feed Bé Men · yesterday's pastries ·
chilled dough ready to bake (warning on the last night) · warm dough before
closing · tomorrow's chill (busy days only). `public_data.night` keeps the lines
of the last close (what happened overnight) for the morning card.

## Order ticket readability

The one-line order (`.order-line`) becomes a short headline ("🥛 Latte · nóng ·
mang về") plus a `reqList` with one row per requirement checked live
(✓ done, ✗ wrong, ○ not yet). Allergy, lactose and caffeine rows come first
with the danger tone. Trays show a compact tab per cup and the list of the cup
in hand. Pastry and cake orders use the same list.

## Saves and validation

* `_migrate` adds `starter`, `cold`, `book`, `night` with `setdefault`, and
  `dense` on proof trays; tasks get `regular`/`greeted` lazily (`t.get`).
* `validate_data` range-checks starter (10–100, fed ≥ 0), cold trays (≤ 2,
  known proof items, day ≤ today, unique ids), book (known npc ids, visits
  0–999, only that guest's note ids, no more notes than the visits allow),
  night lines (≤ 8 strings). `validate_task` checks `regular` 0–2 and `greeted`.
* `make_task`, `FIXED` and the order generator are untouched (`GEN` stays 2).

## Non-goals

Coffee beans resting after roasting (needs lot dates from the shared inventory),
new stock items, engine or kit changes.
