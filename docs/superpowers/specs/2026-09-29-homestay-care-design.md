# Homestay Mây Đà Lạt — care loop (sub-project 3)

Date: 2026-09-29 · Branch: care-wave1 · Career `homestay` · Files: `game/careers/homestay.py`,
`public/js/careers/homestay.js`, `public/css/careers/homestay.css`, `tests/test_career_homestay.py`.

## Problem

A guest who stays three nights costs the house nothing between check-in and
check-out: nobody asks for fresh towels, a cold night passes unnoticed, and a
room is as good on day 20 as on day 1 as long as each turnover is done in the
right order. The homestay is a front desk, not yet a house you look after.

## Goals

* Things done (or skipped) today show up tomorrow and at check-out: rooms age,
  staying guests have small daily needs, regulars remember you, the app rating
  moves with how people felt.
* Server-authoritative; anything random comes from `kit.rng(ID, …)` seeded by
  room, guest and day. `make_task` and every existing (day, slot) ticket are
  unchanged.
* Recoverable: every penalty has a cheap cure the same day, a guest's mood never
  drops below 25, and a single bad day costs at most one star.
* Old saves load (`_data()` migration also runs inside `validate_data`); every
  existing command keeps its payload and meaning.

## 1. Room upkeep — “Độ tươm tất” and small repairs

* Each room has `wear` (0–100, start 75–100). Every night a room is occupied it
  loses 10 (+4 on a rainy day: Đà Lạt damp; +4 for Ban Công Hồ: wooden balcony
  and lake mist). The ordinary turnover keeps a room clean but does not restore
  `wear`.
* `hs_deep {room, confirm}` — “Tổng vệ sinh”: an empty room (clean, or dirty
  with no turnover in progress) is aired, dusted, treated against mould, the
  balcony oiled and its flowers watered. 3 xu, one turn, `wear` = 100.
* At the “báo phòng sạch” step `wear` < 50 costs 1 point of room quality and
  `wear` < 25 costs 2 (musty curtains, damp corners). The message says why.
* Crossing below 60 during the night adds a small repair (`snag`: squeaky hinge,
  dripping tap, loose curtain hook, loose socket, wobbly balcony chair — picked
  from the room and day). The room is still sellable, but a snag costs 1 point of
  quality at turnover and a staying guest 5 mood a day. `hs_fix {room, confirm}`
  (4 xu, one turn) repairs it, also while guests are in (they are out for the day).
* Door numbers are shown: Sương Sớm 1, Dã Quỳ 2, **Đồi Thông 3** (the pine-view
  room of the career story), Ban Công Hồ 4, Gác Mái 5.

## 2. Guests who stay — “Khách ở tiếp”

* Every occupied room has a stay card (`data.stays[room]`): guest, arrival day,
  mood 25–100 (start 70; regulars +5 per earlier visit, up to +10), today's needs
  and what was done, a three-line diary.
* Each morning a guest who sleeps here again tonight (arrived before today, not
  leaving today) rolls today's needs from the seed:
  * **Dọn giữa kỳ** — always. 25 % of days the door has a *Xin đừng làm phiền*
    sign. Two ways to do it (`hs_stay do=tidy|door`, 2 towels either way): go in
    and tidy, or leave fresh towels at the door. On a normal day the door basket
    is only half the job (−4); with the sign on, going in is an intrusion (−15).
  * **Đêm lạnh** — on a cold day (and half the rainy days) the room needs warmth:
    `hs_stay do=warm how=wood|gas` uses one bundle of firewood or one gas bottle.
  * **Một lời nhờ** (60 %): pack a breakfast box for a sunrise trip (bread + milk
    from stock), a pot of ginger tea, lend umbrellas on a rainy day, or suggest one
    place for today — four places are offered with their tags, the guest's wish
    (e.g. “đi dạo nhẹ, không bậc thang”) decides which fits (`place`).
* Day close scores each stay: a full day +8; missing tidy −10, half tidy −4,
  intrusion −15; a cold night without warmth −18 (+4 when warmed); missed request
  −8, an unsuitable place −10, a good one +4; garden in bloom +3 / wilted −4;
  worn room (< 40) −5; snag −5.
* At departure a stay that had at least one scored day becomes a review: 85+ 5★,
  70+ 4★, 50+ 3★, else 2★ with the worst moment in the guest's words. A guest who
  leaves through a check-out ticket gets a “Mấy ngày lưu trú” row on that
  ticket's review instead (no second review). The housekeeping staff do one
  pending tidy per turn and respect the sign.

## 3. Returning guests — “Sổ lưu bút”

* `data.book[npc]` for the guests among the people (visits, first/last day, last
  room, best-liked room, last stars). A visit is written when a stay ends.
* Two notes per guest are learned (after the 1st and the 2nd visit), e.g. Cô
  Diệp “sợ lạnh” and “năm nào cũng xin phòng số 3”, Anh Kiệt “đi sớm, cần hóa
  đơn công ty”. Unlearned notes never leave the server.
* A regular checking in gets a “Nhớ khách quen” review row: 5 when given the room
  they liked (or it was not free), 4 otherwise — a small bonus, never a trap.
* **Phòng số 3**: Cô Diệp and Chú Khang call two days ahead and book Đồi Thông
  for two nights (first stay day 6, then every 12 days: “năm thứ 12, 13…”). The
  booking is a normal calendar booking (deposit paid by transfer); if room 3 is
  already sold the call falls back to another ground-floor room and the page in
  the guest book says so. Their departure adds a page (year, room, stars) to the
  room-3 card. Two days before their call the care list says “Giữ phòng số 3
  trống đêm N–N+1” (red once the room is already sold), and an app order that
  lands on those nights shows a hint with room chips to move it elsewhere. A
  departing guest's check-out ticket never binds to their room.

## 4. Garden, firewood and the app rating

* `data.garden` (hydrangeas, 0–100, start 80) loses 10 a day (6 when cold, 0 when
  it rains). `hs_garden` (one turn) +35. ≥ 70 in bloom, < 35 wilted (stay mood).
* `data.wood` (bundles, start 4). `hs_wood {confirm}` orders 5 bundles for 6 xu
  from the woodpile down the hill; they arrive **tomorrow morning**, so tomorrow's
  forecast (already shown) is what makes buying wood worth it. Gas bottles work
  the same night but cost 6 xu each.
* The app rating (average of the latest 12 reviews) is logged each night for a
  7-day strip with its trend. From ≥ 6 reviews and ≥ 4.8 the app features the
  house: one extra app order a morning (below 3.5 already costs one).

## 5. UI (390 px first)

* A folded **Việc chăm hôm nay** list (`ui-kit.reqList`) on the board and the idle
  panel, open in the idle panel when something is pending.
* Room cards: door number, a thin *Độ tươm tất* bar with words, the snag with its
  fix button, a deep-clean button on empty worn rooms, and for occupied rooms the
  stay card (mood word, sign, needs as 44 px buttons).
* **Vườn & củi** card: garden bar + tend button; wood stock, pending order, the
  forecast tip and the order button.
* **Sổ lưu bút** fold: the room-3 card, then each regular (visits, stars, learned
  notes, “ở thêm 1 lần để biết thêm”). A regular's ticket shows a small
  “📖 Khách quen” card, and their room is marked “⭐ phòng quen” on the check-in
  tiles. Folds keep their open state across re-renders (`x.ui.open`).
* Rating strip in the day chip.
* Audit fixes: the calendar's room column no longer wraps names on a phone (wider
  column, single line, the table scrolls inside its frame); a locked room shows
  “🔒 mở ở cấp 3” once; Sương Sớm uses 🌁 (🌫️ rendered as a grey box).

## Data (all added by `_data()` with `setdefault`)

* room: `wear`, `snag`; data: `stays`, `book`, `anniv`, `garden`, `wood`,
  `wood_order`, `rating`, `care_day`; booking: optional `npc`, `anniv`.
* checkout task: optional `stay` (mood, nights) read by `feedback`.

## Non-goals

No engine, inventory or `make_task` changes; no new stock items (firewood is a
career counter, like the farm's compost).
