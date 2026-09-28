# Pet Care Mèo Mập — care mechanics (sub-project 3)

Date: 2026-09-29 · Career `pet_care` · Files: `game/careers/pet_care.py`,
`public/js/careers/pet_care.js`, `public/css/careers/pet_care.css`,
`tests/test_career_pet_care.py`.

## Goal

Turn single visits into a caring loop that spans days: the shop remembers the
pets that come back, boarded pets need looking after every day they stay,
owners get reminders when a vaccine or a deworming dose is due, and adopted
pets get a follow-up call. Everything is decided on the server, and anything
random comes from `kit.rng` seeded by the career, the pet and the day. Nothing
reads the player's state inside `make_task`.

## 1. Regulars' book (`data.book`)

* A pet is keyed `"<npc index>:<name>"`. The same owner and pet show up as
  groom, board and feed jobs (Bông, Lu, Mướp, Bơ, Xám…), so they meet again.
* Each finished groom, board or feed job writes or updates a record. The record
  holds name, species, breed, owner (npc), visits, first and last day, trust
  (0–5), plus what the shop has actually learned: temperament (only once the
  mood has been checked), allergy, nail colour, weight, the signs the owner was
  told about, whether the favourite comfort is known, the last job and its
  stars, and the vaccine and deworming due days.
* **Trust** goes up by 1 after a visit with no mistake the owner finds and a
  review of 4★ or more. It goes down by 1 after a safety slip. It changes by
  0 otherwise. Names: Khách mới, Quen mặt, Quen tay, Thân thiết, Khách ruột,
  Như người nhà.
* When a regular's new task is created (`on_task`, v0.5 tasks only),
  `t.regular` holds the trust at arrival. On the grooming table, a pet that
  knows the shop starts calmer: −3 stress per trust level.
* The first good visit makes the owner mention the pet's **favourite comfort**
  (a static per-pet table: a treat, a toy or a touch). From trust 2 the
  groomer can use it as a calming option (`pc_calm how=fav`, −30 stress). A
  treat-type favourite uses a treat, and the no-treat rule still applies.
* **Remembering them**: the ticket shows a profile card. `pc_greet` (no turn)
  greets the pet by name and asks about last time: the owner gains 8
  patience, and the review of a regular gets a "Nhớ bé" row (5 when greeted,
  4 when not). This is a small bonus, not a trap.

## 2. Boarding days (`data.stay`, one record per occupied pen)

* Every occupied pen gets a stay record with mood and health (0–100), today's
  chores (meals given, walk or litter, play, medicine, owner called) and
  today's issue (`warn`).
* On admission day the owner has already fed breakfast at home, so one
  meal counts as done.
* Chores come from the pen card. Meals: the card's meals per day, using house
  food from stock when the card says so. Dogs are walked, which uses a poop
  bag; cats get their litter cleaned. Medicine applies only to pets with a
  standing prescription (Mướp one pill, Lu half a pill) and must be given with
  a meal at the dose on the label. Play is optional but lifts mood.
* A day's issue is rolled from the seed. It is homesick (`appetite`: the first
  night for pets that don't know the shop yet, fixed by play or comfort),
  loose stool (`upset`: fixed by calling the owner), or restless (`bored`:
  fixed by play or a walk).
* The existing feeding-round task counts toward the stay: its meal, walk,
  litter and medicine tick the same chores, so work is never done twice. A
  kennel staff member does one pending walk or litter per turn.
* At day close each stay is scored. A full day gives mood +15 and health +10.
  A missed meal costs 12 mood each, and missing every meal costs health.
  Missing the walk or litter costs 10 mood. A skipped or wrong medicine costs
  12–15 health. An unresolved issue costs 10. Mood never drops below 25 and
  health never below 45, so one good day recovers most of a missed one.
* At pick-up, pets the player admitted get an owner review from their final
  mood and health (5★ happy and healthy … 2★ tired and not told). Calling the
  owner about a tired pet lifts a would-be 2★ to 3★. Pre-loaded or
  feeding-round pets get a log line only. Pick-up also updates the book's
  trust.

## 3. Vaccine and deworming reminders

* Due days are game rules. A booster is due every 12 game days and
  deworming every 8. They are set from the checked vaccine book: valid until
  day X, or overdue now when the book is expired or missing. Deworming starts
  4–9 days after the first visit (seeded).
* The idle panel lists pets due within 2 days, or overdue. `pc_remind`
  (no turn) texts the owner and moves the due day one cycle forward. On time
  (at most 2 days late) it gives 3 xp, and trust +1 up to “Thân thiết” (3).
  Above that, only good visits raise trust. Late still works, but
  gives no trust. It is refused when the due day is still more than 2 days
  away. A reminder never replaces checking the real vaccine book at intake.

## 4. Adoption follow-up

* A good adoption match schedules a follow-up call 2 days later, with the
  question the family is likely to have (Đốm chews furniture, Mây hides,
  Tôm is wild at night, Bi soils indoors). `pc_follow` offers three answers:
  good (5★ from the family, 8 xp), fair (3 xp) and harmful (2★).
* A call left 3 days past due lapses quietly. The rescue group calls instead,
  with no penalty.

## Saves, validation, fairness

* New data keys (`book`, `stay`, `follow`) are added by `setdefault` in
  `_data()` / `_migrate()`, which run on every access and in `validate_data`.
  Stays are synced to the pens: an occupied pen without a stay gets a neutral
  one, and an empty pen loses its stay. Old saves load unchanged, and older
  tasks without `regular` or `greeted` are valid.
* `validate_data` type- and range-checks every new field and bounds list and
  dict sizes (book ≤ 80, follow ≤ 12, log ≤ 3). `validate_task` checks
  `regular` and `greeted`.
* All existing commands keep their payloads. New commands: `pc_stay`,
  `pc_greet`, `pc_remind`, `pc_follow`, and `pc_calm how=fav`.

## UI (390 px first)

* Ticket: a folded "Khách quen" card (trust, temperament, allergy, favourite,
  nails, what the owner was told last time, due dates) with a greet button.
* Kennel box and idle panel: one card per boarded pet, with mood and health
  in words and a thin bar, today's chores as a `reqList` checklist, and
  buttons that wrap at 44 px height. The kennel box summary counts the chores
  left.
* Idle panel: reminders due, follow-up calls, and the regulars' book folded
  by default.
