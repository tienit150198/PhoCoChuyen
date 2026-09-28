# Giao Nhanh Mây Chiều — care mechanics (sub-project 3)

Date: 2026-09-29 · Career: `delivery` · Files: `game/careers/delivery.py`,
`public/js/careers/delivery.js`, `public/css/careers/delivery.css`, `tests/test_career_delivery.py`.

## Goal

Turn the courier shift into a multi-day loop of looking after three things that
carry over from one day to the next: **the scooter**, **the regular customers**
and **the neighbourhood you know**. A fourth piece, **tomorrow's forecast**, is
what lets the player plan that care instead of reacting to it.

Every rule below is server-authoritative, deterministic (no new randomness except
where a seeded `kit.rng` already decides, e.g. the existing flat tyre), recoverable,
and shown on a 390 px phone.

## 1. Scooter condition — "Chăm xe"

Five parts, each 0–100 %, stored in `data.parts` (tyre stays in the existing
`data.tyre` key so old code and saves keep working).

| part | wears (per ride leg) | below the line | fix at the garage |
|---|---|---|---|
| 🛞 Lốp (tyre) | existing: 1/ô, 2/ô in the alley, +1 in rain | < 40 %: may go flat (existing seeded event) | 10 xu (+10 if the rim is bent) |
| 🛑 Má phanh (brake) | 1 per leg, +1 in rain | < 30 %: the alley shortcut is refused (steep, sharp turns) | 8 xu |
| 🛢️ Nhớt (oil) | 1 per 3 blocks ridden (counted on the odometer, exact) | < 30 %: engine runs hot, +1 % fuel per leg | 6 xu |
| ⛓️ Sên (chain) | 1 per 2 blocks, +1 per leg in rain (mud) | < 30 %: +1 minute per leg; at 0 % the chain slips off (event) | 6 xu |
| 🧥 Áo mưa (raincoat) | 3 per leg, rainy days only | < 30 %: on rainy days +1 minute per leg (wet and cold) | 8 xu |

* New map stop **🔧 Tiệm sửa xe Chú Bảy** (`garage`, x 5 y 2). New command
  `dl_fix {parts:[…], confirm:true}` at the garage: pick any parts that need work,
  the server prices them, 3 minutes per part.
* The existing `dl_service` at the petrol station keeps working exactly as before
  (tyre + rim, 10 xu); its wording now says what it really does (new inner tube).
* New order-less surprise **DE-CHAIN "Tuột sên"** when the chain reaches 0 %:
  refit it yourself by the kerb (+8 min, chain 25 %, default), push to the garage
  (8 xu, +15 min, chain 100 %) or call a mobile mechanic (14 xu, +5 min, 100 %).
  Riding with a 0 % chain is impossible — the next ride opens the event instead.
* Pace: a normal day rides ~25 blocks, so the tyre wants attention every 2–3
  days, the chain every 5, oil/brake about once a week, the coat after ~3 rainy days.
  Every penalty stops the moment the part is fixed.

## 2. Regular customers — "Sổ tay khách quen"

The six customers (people 0–5) remember you. `data.regulars[npc_id] =
{visits, bond 0..10, notes:[note ids]}`.

* Each customer has two notes (a gate code, "call before", "help an elderly lady
  carry it in", "open the box in front of me", "send me a photo"). Note 1 is told
  to you after the first successful delivery, note 2 after the third. Unlearned
  notes never leave the server.
* A note is honoured by an action at the door before handing over:
  `call` → the existing `dl_call`; `carry`/`photo`/`check` → new `dl_care {task, kind}`
  (3/1/2 minutes); `gate` (Chú Hòa's side-gate code) is passive: the dog at the main
  gate no longer blocks you.
* At the hand-over the order's run records `kept` and `missed` note ids. The review
  gains a "Nhớ lời dặn" criterion (5 when all kept, 3 when one was forgotten).
* Bond +1 for a clean delivery with nothing forgotten; −1 when an order fails by
  your fault (broken, customer cancelled for lateness). Bond 3+ "khách quen" adds
  a 2 xu thank-you, bond 6+ "khách ruột" 4 xu, on each clean delivery.

## 3. Neighbourhood knowledge — "Thuộc hẻm"

`data.areas[node]` counts work done at a stop (loading at the pickup, handing over
at the destination).

* 2+ jobs there: the alley shortcut into that stop is **smooth** — no broth spill,
  normal tyre wear (you know the potholes).
* 5+ jobs: you also know the **local cut** — the shortcut saves 2 blocks instead of
  1 on legs of 3+ blocks. Flooded alleys still stall the engine.

## 4. Tomorrow's forecast — "Dự báo ca tới"

Weather and road conditions are already deterministic per day, so the dashboard
and the day-close summary show the next shift's weather and road board with
concrete advice computed from the player's state: rain bags in stock versus
the day's target, raincoat and brake condition before a rainy day, a worn tyre,
the road-works stop or jam window to plan around. Rain bags ordered today through
the existing stock system arrive in time — that is the planning loop.

## Save compatibility and validation

* `_extend` (the plugin's migration, also run from `validate_data`) adds `parts`,
  `regulars`, `areas` and new stat keys with `setdefault`; run keys `care`, `kept`,
  `missed` are added to saved orders like the v0.5 keys.
* `validate_data` range-checks parts (0–100), regulars (known npc ids, bond 0–10,
  note ids of that customer, no more notes than the visits allow), areas (known
  stops); `validate_task` checks the new run lists.
* No `FIXED` task field and no order generator changes: every existing (day, slot)
  still produces the same order.

## UI (390 px)

* Status strip: the tyre meter becomes "🔧 Xe" showing the weakest part.
* A folded **Chăm xe** card (open when something is below its line or at the
  garage) lists the parts with `reqList` rows: value, what happens below the line.
  At the garage, the parts are toggles with the total price and one confirm button.
* A one-line forecast chip under the road board; the full advice in a fold.
* At the door, the order card shows the customer's learned notes as a checklist
  with one button per note to honour it.
* A folded **Sổ tay khách quen** lists each customer, bond hearts, learned notes
  and "giao thêm N đơn để biết thêm".
* The ride buttons say "🗺️ thuộc hẻm: êm" / "lối tắt dân địa phương" and the
  brake refusal reason when the alley is not allowed.
