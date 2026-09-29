# Salon Tóc Gió — care mechanics (sub-project 3)

Date: 2026-09-29 · Career `salon` · Files: `game/careers/salon.py`,
`public/js/careers/salon.js`, `public/css/careers/salon.css`,
`tests/test_career_salon.py`.

## Goal

Before this change every visit stood alone. A client who came back three days
later was a stranger: nobody remembered her colour formula, what the bleach did
to her hair, or when she should come back for her roots. Clean tools were a
single tick box.

This change adds a loop that spans several days. The salon keeps a **card for
each regular**. The card holds her formula and her **hair health**, which
improves or suffers from one visit to the next. At checkout the stylist can
**book a follow-up** that brings the client back on a later day. **Clean tool
sets** are used up client by client, so sterilising them becomes a daily
routine.

As before, the server decides everything and nothing new is random. The
changes do not touch `make_task`: which client arrives on a (day, slot) is
exactly what it was. Everything that depends on the player's history is added
by `on_task` into task fields that are not `FIXED`.

A small coherent set was chosen from the ideas list. **Opened dye tubes with
their own shelf life** were left out. Stock already expires by lot, and
splitting a tube into uses would change the stock accounting that other screens
and tests rely on.

## 1. Client card — "Thẻ khách quen" (`data.cards[npc_id]`)

* A new card is written when a v0.5 visit reaches checkout, and an existing
  card is updated. It holds: `visits`, `first`, `last` (day), `trust` (0–5),
  `health` (0–100), `hist` (the chemical history, recorded only if the stylist
  asked), `formula` (the last colour bowl: tubes, parts, developer, ratio, the
  target level and tone band, whether it hit and its timing zone, the day),
  `cut` (cm removed, too short or not, the day), `services` (last visit),
  `stars` and `patch_file` (the client showed a patch-test record).
  Patch-test days and allergies still come from the existing `patch_log` and
  `allergy` books, and the card view shows them.
* Hair type and porosity are shown in words from `hist`: virgin → low
  porosity; box dye → uneven; bleached → high porosity, takes colour fast;
  relaxed → medium, dries out.
* **Trust** rises by 1 after a finished visit (served, or honestly referred
  such as a patch test) with ≥ 4★ and no slip, and after a 5★ booking. It falls
  by 1 after a safety slip or a missed booking. Names: Khách mới, Quen mặt,
  Khách quen, Thân thiết, Khách ruột, Như người nhà. A regular arrives
  +3 patience per trust level (`on_task`).
* **Same formula.** Suppose a regular's card has a colour that hit, and today's
  colour target (level + band) is the same as on the card. Then the review adds
  a **"Nhớ khách"** criterion. The exact card formula (the same tubes in the
  same proportions and the same developer) scores 5: "màu y lần trước". A
  different bowl that still hits the target scores 4: "ánh hơi khác lần
  trước". The mixer shows the card formula next to the tubes. This is a small
  bonus for remembering the client, not a trap.

## 2. Hair health (`task.health`, `card.health`)

* On a first visit, health comes from the template damage (100 − 20 × damage).
  For a regular it is the card value plus natural recovery of +3 per day since
  the last visit, capped at 85. New growth and home care help, but only a
  treatment gets hair above 85.
* Each visit changes it at checkout. Bleach: −12 under, −20 ideal, −28 over,
  −40 damage. Colour: −4, −6, −10, −25. Toner: −2 (−8 damage). Keratin
  treatment: +25. A take-home mask sold: +5. Heat spray: +3. The result is
  clamped to 10–100.
* The stylist learns a first-time client's health by feeling the lengths or
  ends (inspect). A regular's health is on her card.
* **Weak hair (< 50): recommend a treatment, don't upsell.** The plan may add
  keratin even though the client did not ask for it (`advised`). The client
  accepts the extra price because the reason is real, so it is left out of her
  budget check. The review notes the honest advice. Chemistry on weak hair
  without a treatment costs 1 point of care. That rule already existed for
  damaged templates and now also follows the card. On healthy hair (≥ 50),
  treatment is still an extra the client refuses.
* Weak hair is fragile under bleach: the short bleach window applies. **Below
  30** Linh stops the bleach, since the hair would snap. Bleach may then be
  postponed with a reason (flag `weak_stop`, −1 care if the stylist tried).

## 3. Follow-up bookings — "Sổ hẹn" (`data.appts`)

* At checkout the stylist may book what the visit calls for (`book` in the
  checkout payload, optional):
  * `roots`: root touch-up ("dặm chân tóc", 4 weeks, which is **4 game days**
    here). Only offered after a colour that took (ideal/over, formula hit).
  * `trim`: keep-the-shape trim, **5 days**. Only offered after a cut that was
    not too short.
  * `care`: keratin top-up, **2 days**. Only offered when the hair leaves
    weak (< 60).

  A client who walks out or refuses to pay does not book. Booking the same kind
  again moves the date.
* A booking is open from its due day until 2 days after. On the due day the
  morning log says who is coming. The client then waits in the Sổ hẹn card on
  the idle panel and under the work bench. One command serves her,
  `sl_appt {id, …}`, which takes one turn and counts as physical work:
  * roots: pick the tube(s), parts and developer (the card shows the
    formula). Exact card formula: 5★, the regrowth matches the lengths. Same
    level, band and developer: 4★, the line shows a slightly different reflect.
    Anything else: 2★ and half pay, a visible band. 40 vol is refused. Uses the
    tubes, developer and gloves. Health −3.
  * trim: pick 1–6 cm. The card allows 2 cm, or 1 cm if the last cut went too
    short. Within that: 5★. More: 3★.
  * care: uses one keratin. Health +25. 5★.

  Roots and trim use a tool set (see 4). A dirty set costs 1★.
  Pay: roots 35, trim 20, care = the treatment price. Each booking posts a
  review from the client and updates the card (visits, trust +1 on 5★).
* If the same client comes in as an ordinary task and gets the same work
  (colour for roots, a cut for trim, treatment for care), the booking is closed
  as done-in-visit (`merged`) with no penalty.
* **Missed:** a booking left more than 2 days past due lapses at the next
  shift start. Trust −1 and a log line, but no review and no fine.

## 4. Tool hygiene — "Bộ dụng cụ sạch" (`data.clean`, `task.tools`)

* The sterilising jar holds **4 sets** (comb, scissors, clipper guard, brush).
  The disinfectant is changed every morning, so the day starts with 0 clean
  sets.
* `sl_sanitize` refills the jar to 4 sets (one turn). It is refused only when
  all 4 are already clean. It still signs the hygiene log that the inspector
  desk event reads.
* A client's first hands-on step (wash, apply, cut, treat, style) takes a
  clean set if there is one (`tools='clean'`). If not, it goes ahead with a
  used set (`tools='dirty'`) and the message warns. A dirty set costs 1 point
  of care in the review: "dùng lược kéo chưa khử khuẩn".
* The cutter on staff (role `cut`) sterilises one set per turn when a set is
  used, so what the old flavour text promised now actually happens.

## Saves, validation, fairness

* New data keys (`cards`, `appts`, `appt_seq`, `clean`, `appts_done`) are added
  with `setdefault` in `_data()`, which `validate_data` also runs. An old save
  whose tools were sanitised today starts with 4 clean sets. Old tasks without
  the new fields are valid: `health`, `regular`, `tools`, `memo`, `advised`
  and `booked` are read with defaults. `FIXED` and the generators are
  unchanged.
* `validate_data` bounds and type-checks cards (known npc ids, ranges, formula
  tubes, bands, zones), bookings (≤ 40, known kinds and states), `clean`
  (0–4) and `appt_seq`. `validate_task` checks the new task fields. A plan may
  hold an unrequested treatment only when the task's health is weak.
* All existing commands keep their payloads. `sl_checkout` gains an optional
  `book` list, and there is one new command, `sl_appt`.

## UI (390 px first)

* Ticket: a folded **📇 Thẻ khách quen** (`reqList` rows: hair type, health
  bar and word, formula, patch test, last cut, booking). It is open when the
  card's formula applies today.
* Plan: the keratin tile says "tóc yếu — nên phục hồi" when advised.
* Mixer: a "📇 Thẻ: …" line with the formula on file.
* Bill: "📅 Hẹn lần tới" toggles with the due day.
* Idle panel and work bench: **📅 Sổ hẹn** cards for clients due today (tube,
  length or confirm controls), later bookings in a fold, and a folded
  **📇 Sổ khách quen**.
* Foot: "🧴 Khử khuẩn · 2/4 bộ sạch".
* Step tabs: from 720 px down they scroll sideways (84 px each) with labels
  ≥ 0.8rem, instead of seven squeezed columns.
