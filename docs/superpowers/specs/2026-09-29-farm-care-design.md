# Farm care loop (sub-project 3) — Nông Trại Đồi Gió

Date: 2026-09-29 · Branch: workplace-scenes · Files: `game/careers/farm.py`,
`public/js/careers/farm.js`, `public/css/careers/farm.css`, `tests/test_career_farm.py`.

## Problem

Before this change a crop planted in the morning could be harvested the same
afternoon: growth was per action ("nhịp") with no daily limit, so most of the
farm was a same-day chore list. Nothing done or skipped today mattered much
tomorrow except moisture, weeds and hunger for the hens.

## Goals

* Crops take **several days** (2–3 nights) from seed to harvest, with a clear
  stage and "chín hôm nay / mai / 2 ngày nữa" shown per bed.
* What happens **overnight** depends on the care given today and on tomorrow's
  weather, so checking the forecast is part of planning.
* Ignoring a problem for a day costs something but is always recoverable
  (no death spirals): growth slows, it never stops for good; hens never die of
  neglect; every penalty has a cheap cure.
* Fully server-authoritative and deterministic. No new randomness: every new
  rule is a pure function of the save (plots, coop, day) and the existing
  day-keyed weather.
* Old saves load (setdefault migration in `validate_data`), existing commands
  keep their meaning, existing tests stay green.

## Mechanics

### 1. Multi-day growth: a daily growth budget ("sức lớn mỗi ngày")
Each crop gets `cap` — how much it can grow during one day's work
(muống 34, xà lách 32, rau thơm 30, dưa leo 26, cà chua 18). Per-action growth
works as before (moisture, weeds, pests, season, fertiliser) but stops once the
day's budget is used (`plot.grown`, reset every night). Once a crop is ripe its
budget halves (produce ages more slowly than it grows), so the harvest window is
about one full day, and a missed day turns it "quá lứa" (grade B), not rotten.
Compost adds +4 and NPK +8 to the budget; depleted soil multiplies it by 0.6.
Night growth (20, winter 10) stays; it is halved on depleted soil.
Result: leafy crops ripen on the 3rd day after sowing, tomatoes late on the 3rd.

### 2. Soil fertility ("đất màu", 0–100) per bed
* Every night a planted bed uses its crop's `feed` (6–12); an empty bed rests
  (+8); a waterlogged bed on a rainy night leaches (−4).
* Compost +20 (still organic), NPK +30 (not organic, PHI as before).
* Compost is now also allowed on an **empty bed** ("bón lót"): the flag carries
  into the next crop.
* Below 25 the bed is "bạc màu": budget ×0.6 and night growth ½. Never zero.

### 3. Rotation and rest ("luân canh")
Each bed remembers the previous crop (`prev`). Sowing the other family
(rau lá ↔ cây trái) gives +8 soil; sowing the **same crop** again brings the old
pests back (pests start at 1, hidden until scouted). The seed tiles show which.

### 4. Pests spread overnight
A bed with pests ≥ 2 at night infests orthogonal neighbours in the 3×2 grid
(P1 P2 P3 / P4 P5 P6) that have a crop and no pests, unless the neighbour was
sprayed today (`guard` = day of the last spray). The night summary says how many
beds were reached, without naming hidden ones. Bio spray (−2) cures it.

### 5. Weather outlook and nights that follow it
The weather bar shows today + a 3-day strip (tomorrow, the day after, day 3),
season changes included, and one planning tip for tonight. Night drying now
depends on tomorrow's sky: nắng gắt −18, gió −15, nắng nhẹ −12, râm −8,
mưa +13 (unchanged for rain and sun).

### 6. Hen mood ("tinh thần đàn", 20–100)
New `coop.mood` (start 80) and `coop.cleaned` (day). At night:
fed +8 / hungry −15; cleaned today (`fa_clean`, new action, or the coop helper)
+6, not cleaned for 2 days −8; a hot day without a clean coop −5; fox −15.
Eggs = (hens if fed else hens/2) × 100% (mood ≥ 60) / 80% (35–59) / 60% (< 35).
One missed feeding drops the mood but still lays fully the next day; three
good days bring the worst flock back to 100%.

### 7. "Việc chăm hôm nay" checklist
`public_data.care` lists today's chores computed on the server (dry/wet beds,
weeds, depleted soil, known pests, beds not walked today, ripe beds, feed,
clean, eggs) with ok/pending/danger. The UI renders it with `ui-kit.reqList`
in a fold at the top of the field tab.

## Data changes (all migrated with setdefault)
* plot: `soil` (60), `grown` (0), `prev` (None), `guard` (0).
* coop: `mood` (80), `cleaned` (0).
* public view only: plot `eta` (days to ripe), `over_in`, `cap`, `soil_low`;
  `outlook` (3 days), `plan` (tip), `care` (rows), coop `lay_pct`, `cleaned_today`.

## Non-goals
No new stock items, no hen death, no random disease rolls, no engine changes.
