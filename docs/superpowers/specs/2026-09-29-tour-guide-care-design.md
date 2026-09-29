# Chuyến đi Mây Lang Thang — care loop (tour guide)

Date: 2026-09-29 · Branch: care-wave1 · Career `tour_guide` (legacy career, v2 trip
layer) · Files: `game/tour_trip.py`, tour parts of `game/experiences.py`, tour parts
of `public/js/v4/teach-tour.js` and `public/css/teach.css`, `tests/test_tour_care.py`.

## Problem

Every trip is a one-off: a group appears, walks three to five stops and is gone. A
hard hilly day in the heat costs nothing tomorrow, the guide never gets to know the
restaurant, the boat owner or the homestay, telling the same stop's story for the
twentieth time is no richer than the first, the reviews change nothing, and the
kit (loudspeaker, first-aid bag, flag) never needs looking after.

## Goals

* What you do today shows up tomorrow: the same group travels 2–3 days, gets
  tired, and someone who is pushed too hard wakes up sick.
* Server-authoritative and seeded. `make_task` and every existing (day, slot)
  ticket stay unchanged. Trip facts are still rolled from (day, slot) alone, so
  validation can regenerate them.
* Recoverable and fair: sickness only follows real tiredness, and it can always
  be avoided by planning a gentler day. Every penalty has a cheap cure the same
  day. Mood never drops below 25.
* Old saves load, and every existing command keeps its payload and meaning.

## 1. Multi-day groups — "Đoàn nhiều ngày"

* A seeded calendar (`group_of(day)`) starts at day 3. Groups stay 2 or 3 days,
  and sometimes there is a free day between them. On a group day, **slot 0** is
  that group's leg: `trip.group = {start, days, leg}` is a fixed fact. Members come
  from the group's seed, so every leg has the same people (size 5, or 6 from
  tier 3). Other slots are ordinary day trips.
* The career keeps `life.tour.group`: members, **energy** 0–100 (elders start at
  75, others at 90), today's sick member and the call made about them, legs
  done, the mood at each leg's end, and short diary lines.
* **Energy cost of a leg** (applied at "Khép chuyến"): walking time/5, +6 for
  elders, +5 per outdoor stop in the heat, a hill (+16 for elders, +6 for kids,
  +4 for others), +4 for kids on a route over 100′, +1 per 4′ late, and −6 with
  a rest stop. The minimum is 4. A gentle 70′ day costs about 8, and a hilly
  120′ day in the heat costs an elder about 40.
* **Overnight** (the next morning): +6 +2 × homestay level, then +6 if the
  homestay was called about the night, or −4 if it was not. The maximum is 100.
  Gentle days therefore recover, and two hard days in a row wear people down.
* **Morning sickness** (legs 2–3): someone below 30 energy wakes up sick. Below
  45 there is a 60 % chance (seeded by group, day and member). At most one
  person is sick; the leader Linh never is. A guest who was pushed while sick
  yesterday stays sick. A guest who was cared for yesterday (rest or clinic) is
  on the mend and is not rolled again that morning.
* **At the plan stage** the sick guest needs a decision before the route
  (`tour_care {task, option}`):
  * `rest`: stays at the homestay with medicine from the first-aid bag (3 xu if
    the bag is empty). They are away for the day: their wish, the events around
    them and the tips no longer count, and they get +30 energy.
  * `clinic`: the health station (4 xu), then the day at half effort. Mood −3.
  * `push`: "cố đi cho trọn chuyến". This is a mistake and a safety-critical
    slip at the end, the leg costs 1.5×, and they are still sick tomorrow.
* A tired guest (below 50) makes a hard route (hill, over 100′, or more than one
  outdoor stop in the heat) cost 5 mood each at planning. The plan screen says
  so ("Bà Sáu đang mệt: tránh dốc, đi ≤ 100′").
* **The group's review**: when the last leg ends (or the morning after the
  group's last day), the group posts a starred review on the booking page. It
  starts from the average end-of-leg mood (85+: 5★, 72+: 4★, 58+: 3★, lower: 2★).
  It loses 1 for a skipped leg, 1 for a sick guest who was pushed, and 1 for a
  night the homestay was not called.

## 2. Local partners — "Bạn hàng"

Trust points 0–10, level = points // 2 (Mới quen … Như người nhà).

| Partner | Call | Effect | Trust |
|---|---|---|---|
| 🏡 Homestay Mây (cô Hạnh) | `tour_partner partner=homestay`: tonight's headcount and diets (a group night) | Overnight recovery +2 per level, +6 when called (−4 when not) | +1 per called night, −2 per night not called |
| 🍚 Quán cơm Bà Tư | `partner=restaurant`: book the group's lunch before the leg departs | Leg mood +3 + level at departure. Without it −4 (waiting for a table) | +1 per booked leg, −1 per unbooked one |
| 🛶 Đò chú Sáu | `partner=boat`: tomorrow's early boat for the group (`when=today` from level 3) | Leg mood +8. Price 8 − level xu (at least 3) from the wallet. No boat when tomorrow's forecast is rain or wind | +1 per ride, −2 for a no-show |

## 3. Place knowledge — "Sổ tay điểm đến"

* `life.tour.know[place]` goes up by 1 each time a story there goes down well
  (tell delta > 0).
* From 4: "chuyện ít ai biết", an extra line with +2 mood at later good tellings.
* From 10: "góc ẩn", a hidden spot (the kiln's back window, the bench behind
  the hibiscus…) with +4 mood instead.
* The stop screen shows the progress ("kể hay thêm 1 lần để mở …").

## 4. Kit — "Đồ nghề"

* 🔋 **Loudspeaker** 0–100: −8 per telling. Below 8, the back of the group
  cannot hear: the telling costs −4 mood. `tour_kit item=mic` plugs it in, and it
  is full the next morning.
* 🩹 **First-aid bag** 0–6 supplies, used by the heat-stroke "shade" call and by
  sick-guest care. When it is empty, the good call still works but costs −3 mood
  (running out to buy things). `item=aid` refills it at 1 xu per missing supply.
* 🚩 **Flag** 0–100: −10 per trip, −18 in rain or wind. Below 30 it is faded, and
  departure costs −4 mood ("đoàn ngó nghiêng tìm cờ"). `item=flag` mends it for
  3 xu.

## 5. Booking page and forecast

* Each finished v2 trip's review stars (and each group review) go into
  `life.tour.reviews`, which keeps the last 12. With 5 or more reviews and an
  average of 4.5 or more, the booking page features the guide: one extra group
  books that morning (if fewer than 4 open jobs). Below 3.5, the care list warns
  that bookings are thin.
* **Tomorrow's forecast** is the weather of tomorrow's slot-0 trip, with a tip
  (rain or wind: no boat, the river path and hill are closed; heat: fill the
  first-aid bag and keep outdoor stops to 2 or fewer).

## UI (390 px first)

* On the trip sheet, a **Việc chăm hôm nay** fold (`ui-kit.reqList` plus 44 px
  buttons) lists the group call, lunch, boat, loudspeaker, first-aid bag, flag
  and tomorrow's forecast, with a "N việc chờ" count on its summary. It opens
  by itself at the plan stage when a partner call is waiting (and no sick guest
  comes first), and at the gather stage while lunch is still unbooked. Folds
  remember their open state across re-renders (a toggle listener in the
  module).
* A **Đoàn nhiều ngày** chip ("👥 Đoàn 3 ngày · ngày 2/3"). The roster shows
  energy in words with a thin bar, the sick guest, and "🏠 nghỉ ở homestay".
* A sick-guest card at the top of the plan stage with three options. The plan
  button stays disabled until it is decided. The route summary warns about
  tired guests.
* The stop shows the notebook's progress and the loudspeaker's battery.
* A **Bạn hàng · Sổ tay · Đánh giá** fold: partner trust and perks, places'
  knowledge, and the booking page's rating strip.

## Data and saves

* `life.tour` (new for `tour_guide` in `life.initial`, and added by
  `upgrade_save` for old saves): `v, day, group, partners, know, kit, reviews,
  featured`. `validate_care` type- and range-checks every field. It
  cross-checks the group's calendar and members against the seed.
* Trips: new trips carry `group` (fixed) and `care` (`{sick, call}` on a leg,
  otherwise None). Old trips without `group` keep the old roll and old keys (a
  legacy path in `roll`/`validate`). Old trips whose roll is unchanged get
  `group=None, care=None` on load.
* Today's leg trips are created at the morning start, so the sick-guest card is
  there before planning. When one is missing (a slot-0 trip from "more work"),
  the projection `life.tour.group.today` covers it and `tour_care` creates the
  trip.
* New commands: `tour_care`, `tour_partner`, `tour_kit`. All existing
  `tour_*` commands keep their payloads.

## Non-goals

No engine, `make_task` or app.js changes. No new places on the map (hidden
spots live inside existing places). Clock and fund math are unchanged; care
effects move mood, energy, trust and the wallet only.
