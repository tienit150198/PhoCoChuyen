# Quán Mì Cay Mây — care mechanics (sub-project 3)

Date: 2026-09-29 · Career `restaurant` · Files: `game/careers/restaurant.py`,
`public/js/careers/restaurant.js`, `public/css/careers/restaurant.css`,
`tests/test_career_restaurant.py`.

## Goal

Make the noodle shop a place you look after from one day to the next. Three
things now carry over: **the broth pots** (they keep overnight, but not
forever), **the regulars** (they remember you, and you learn their little
habits), and **the kitchen's hygiene book** (a week of clean shifts earns
trust with the inspectors). A fourth piece, **tonight's prep and tomorrow's
outlook**, is what lets the player plan instead of react.

All rules are server-side and deterministic. No new randomness: tomorrow's
"luck of the day" is already rolled from (career, day), so it can be shown
the evening before. Nothing reads player state in `make_task`, and the order
generator (`GEN`) is unchanged.

## 1. Broth overnight — "Nồi qua đêm"

`data.pot_lots[broth]` lists the batches in a pot, oldest first, as
`[portions, nights]` (their sum is always `data.pots[broth]`).
`data.pot_warm[broth]` says whether the pot has been brought back to the boil
since the last close. Every close adds one night to every batch and lets the
pots cool.

| oldest batch (nights) | state | what the player does |
|---|---|---|
| 0 | 🟢 mới nấu | ladle as before |
| 1–2 | 🟡 để qua đêm, nguội | `rs_reheat` (one turn, all cold pots at once) before ladling |
| 2 | … after reheating | usable, but the bowl's review gets "Nước dùng 4/5 · để 2 đêm, hơi nhạt" |
| 3+ | 🔴 có phần quá hạn | the pot is blocked until `rs_toss {broth, confirm}` pours out the expired batches (logged as waste at the pack's cost per portion); newer batches stay |

* Ladling always takes the oldest batch first (first in, first out), so a pot
  that is used and topped up every day never spoils. Cooking a batch
  (`rs_pot`) adds a fresh batch and boils the pot, so it counts as reheated.
* A stale pot refuses `rs_pot`, `rs_broth` and `rs_batch` with a message that
  says what to do.
* The kitchen helper (`prep` staff) reheats cold pots first, before cooking
  low ones.
* Fair: reheating is free and takes one turn for every pot; a pot only
  expires after two nights; tossing costs just what the broth was worth.

## 2. Tonight's prep — "Chuẩn bị cho mai"

`rs_prep {broth, confirm}` (shift open, up to 2 pots a night, 2 broth packs
each): simmer a pot overnight. At the next `start_day` that pot opens full
(12 portions), fresh and hot — no reheating, no cooking turns during service.
Old broth left in that pot goes to the staff meal (a log line, no waste).
Stored in `data.prep = {day, broths}`.

The evening panel and the day-close summary show **tomorrow's luck of the
day** with advice computed from the save: pots that will need reheating or
will expire, cold wind (2 portions a bowl → simmer a pot), rain (count the
takeaway boxes), beef day, and whether today's hygiene line is still empty.

## 3. Regulars' book — "Sổ khách quen"

`data.guests[npc_id] = {visits, bond 0..5}` for the eight named guests
(the tourist has no card).

* Every regular has two small habits (a glass of iced tea after a run, noodles
  cut short for Bé Na, chopsticks scalded in front of Bà Hoa, a wet towel for
  the mechanic…). Habit 1 is learned after the first served visit, habit 2
  after the third. Unlearned habits never leave the server.
* When a regular's order arrives (`on_task`), `t.regular = {bond, notes}`
  snapshots what the shop knows. The ticket shows a notes card: bond hearts,
  visits, the habits as a checklist, their usual bowl if the notebook has it,
  and one button per habit: `rs_touch {task, touch}` (no turn). The "extra
  broth" habit uses one portion from the bowl's pot.
* The review gets "Nhớ ý khách" (5 when every known habit was honoured, 4 when
  one was forgotten). A small bonus, never a trap.
* Bond +1 after a clean visit (no slips, not refused, no habit forgotten),
  −1 after a refused bowl or a safety slip, else unchanged. Bond 3+ adds a
  2 xu thank-you on clean visits.
* The existing "như mọi khi" notebook, regular stories and visit counts stay
  exactly as they were.

## 4. Hygiene book — "Sổ vệ sinh 7 ngày"

At every close the day gets a line in `data.hlog` (last 7 days):
`{day, clean, dishes, pots}`. Points: kitchen checked today (`rs_clean`) 2,
no dirty bowls left 1, no expired broth in a pot 1 — 4 a day.

* Score = points of the last 7 days out of 28; days not yet written count as
  2/4, so a new shop starts around 50 and a week of care brings it to 100.
  Grade: **A** ≥ 85, **B** ≥ 60, **C** below.
* The surprise inspection reads the book: checked today → pass and the
  "Bếp sạch" badge (as before); not checked today but grade A → no fine, a
  reminder; otherwise the old fine. One missed day costs ~7 points, so an A
  kitchen stays A.
* Bà Hoa ("rất để ý vệ sinh"), once the book has 3+ days, reviews a
  "Bếp sạch" row: 5 at grade A, 3 at grade C, no row at B.

## Saves, validation, fairness

* `_migrate` (run on every access and from `validate_data`) adds `pot_lots`
  (one fresh batch for what a pot holds — old saves are treated as fresh),
  `pot_warm` (true),
  `prep`, `guests`, `hlog`; restaurant tasks get `regular=None`, `touches=[]`,
  `broth_age=0` with `setdefault`.
* `validate_data` checks the batches (known broths, 1–12 portions, nights
  0–99, strictly oldest first, summing to the pot), prep (≤ 2 known
  broths), guests (known npc ids, visits 0–999, bond 0–5), hlog (≤ 7 rows of
  booleans). `validate_task` checks `regular`, `touches` (known ids, no
  repeats) and `broth_age` (0–2).
* All existing commands keep their payloads. New: `rs_reheat`, `rs_toss`,
  `rs_prep`, `rs_touch`.

## UI (390 px first)

* Pot tiles say "cần đun lại" / "quá hạn"; a one-line bar above the pots offers
  "🔥 Đun lại N nồi" and "🗑️ Đổ N phần … cũ". The pot list shows each batch
  ("3 phần để 1 đêm + 6 phần mới").
* Ticket: a folded "📒 Khách quen" card with the habits as a `reqList` and
  44 px buttons.
* Side column and evening panel: a "🧽 Bếp & ngày mai" fold — the 7-day
  hygiene strip with the grade, pots overnight, simmer-for-tomorrow buttons,
  tomorrow's outlook and advice. It opens by itself when something needs care.
* Evening panel: "📒 Sổ khách quen" fold with every regular, hearts, learned
  habits and "phục vụ thêm N lần để biết thêm".
* Day-close summary: the grade card plus a care card (pots overnight,
  hygiene line, prep, tomorrow).

## Non-goals

No weekly special menu, no new stock items, no changes to the order
generator, food_kit or the engine.
