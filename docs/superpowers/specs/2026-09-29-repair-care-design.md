# Tiệm Sửa Đồ Chú Tư — care mechanics (sub-project 3)

Date: 2026-09-29 · Career `repair` · Files: `game/careers/repair.py`,
`public/js/careers/repair.js`, `public/css/careers/repair.css`,
`tests/test_career_repair.py`.

## Goal

Machines now stay in the shop for more than one day. A device can wait on the
shelf for a part and its owner phones to ask "xong chưa?". A part can be
ordered from the city for a genuine repair, or the repair can use a salvaged
part today. A promised pickup date matters, and so does a repair done in a
hurry or with a cheap part, because it can come back days later. Regular
customers remember all of this. The two tools on the bench (the soldering
tip and the multimeter) also need looking after.

Everything below is decided on the server. Anything random comes from
`kit.rng` seeded by the career and the task id. `make_task` and `FIXED` do
not change, so every existing (day, slot) still makes the same customer.
Waiting times are shown as clock and day words ("chiều nay 15:00",
"sáng mai", "ngày kia"), never as "nhịp".

## 0. Shop clock

`data.clock = {day, turn0}` is set when the shift opens. The shop opens at
08:00, and each turn is 10 minutes, up to 19:00 ("sắp đóng cửa"). The clock
only turns part arrivals and promises into words. It never ends the shift.

## 1. Parts ordered for one device (`bench.orders`)

After the customer accepts the quote for a fault, `rp_order {task, fault,
confirm}` orders that one part for this device. The source follows the
approved grade:

| grade | source | arrives | shipping |
|---|---|---|---|
| Chính hãng | 🏙️ Nhà phân phối hàng hãng trên thành phố | the day after tomorrow, when the shop opens ("ngày kia") | 3 xu |
| Tương thích / Thay mới | 🛵 Lâm Linh Kiện | 15:00 today if ordered before 12:00, otherwise when the shop opens tomorrow | 2 xu |
| Tháo máy / Vệ sinh | cannot be ordered: salvaged parts come from the shelf, today | — | — |

* The part's catalogue cost plus shipping is paid when ordering (`stock`).
  `rp_fix` uses the ordered unit once it has arrived. If it has not
  arrived, it says when it will ("Lâm giao chiều nay 15:00"). Without an
  order, `rp_fix` takes the part from stock as before.
* Quote tiles show the wait when the shelf is empty ("hết · hàng hãng về
  ngày kia", "hết · Lâm giao chiều nay"), so the choice between a genuine
  part in two days and a salvaged part today is made in the open.
* When a task ends, an ordered part it did not use goes to the shop's stock
  (or is written off if the shelf is full).
* A part that arrives during the shift is announced once in the next
  action's message. Parts that arrive overnight are logged at opening.

## 2. The shelf of waiting devices (`bench.shelf`)

* `rp_shelf {task, days 0..3, confirm}` ("Hẹn khách, để máy lại tiệm")
  tags the device (`#014`), records `since` and `promise = day + days`, and
  sends the customer home. The task becomes `deferred`, which the queue
  shows as "Đã hẹn", and it loses no patience. The shelf holds at most 2
  devices placed this way, so every morning still brings new customers.
* At closing time, any device still in the shop (intake done, not handed
  back) is put on the shelf automatically, with the promise "mai".
* Every morning, each device still waiting (not yet passed its final test)
  gets a call: "📞 Ông Bảy gọi: quạt xong chưa cháu?". `rp_answer {task,
  reply}` does not use a turn:
  * `truth` gives the real arrival time. If the promise can no longer be
    kept, it is moved to the real day (`moved`). No trust is lost.
  * `soothe` answers "chiều nay xong", which sets the promise to today.
    When the parts are known not to be here yet, this counts as a lie
    (`lied`).
  * A call still unanswered at closing counts as `missed`.
* At closing, a device that is not back with its owner by the promised
  day gets `late += 1`.
* At handover, a shelf device is judged on the promise, not on patience.
  The review's "Thời gian chờ" line becomes "Giữ hẹn": 5 when on time, 4
  when the date was moved honestly, and −1 for each missed call (at least
  3). A late pickup adds the slip `late_pickup`. Its severity is 1, or 2
  when late two days or after a lie, and it lowers stars and pay as usual.

## 3. Regular customers (`data.regulars`)

`regulars[npc] = {visits, trust 0..5, ontime, late, history[≤4]}` covers the
seven customers who bring devices in (not the parts dealer, not the
stranger).

* On a finished repair, `visits` goes up by 1 and the repair is added to
  the history (day, device, fault, part grade, warranty).
* Trust goes up by 1 on a handover with no slips. It goes down by 1 on a
  late pickup, by 1 when a warranty comeback is ignored, and by 2 when a
  comeback still under warranty is charged. The trust names are Khách mới,
  Quen mặt, Quen tay, Thân thiết, Khách ruột and Như người nhà.
* Each trust level adds 3 patience when the customer comes back
  (`on_task`). From trust 3, the customer accepts a quote up to 10 % over
  the budget they gave.
* The ticket shows a folded card: trust, visits, the last repair of the
  same kind of device, and the customer's habit (a static line per person,
  shown from the second visit).

## 4. Warranty comebacks (`data.comebacks`)

At handover, a repair that fixed everything that was really wrong may come
back 2–5 days later. The chance is seeded once from the task id:

| cause | added chance |
|---|---|
| part grade: genuine 0 · standard 6 % · compatible 14 % · cleaning only 8 % · salvaged (tested) 25 % | base |
| handed over without the final test | +30 % |
| board that had been in water | +15 % |
| soldered with a worn tip (below 30 %) | +20 % |

The total is capped at 60 %. On the day it is due, the customer is at the
counter with the old symptom (the fault's `left` line), and the shop names
the cause: a cheap part that wore out early (compatible or salvaged), a
faulty batch (standard), a cleaning that did not last (cleaning only), a
cold joint, rust coming back, or a fault that surfaced because there was no
final test. `rp_back {id, choice, confirm}`:

* `redo` repairs it for free. The shop pays the part's cost. Under warranty
  this brings a 4★ review with no trust change. Out of warranty it brings a
  5★ review and +1 trust.
* `charge` bills the part plus half the labour. Under warranty this brings a
  1★ review and −2 trust. Out of warranty it brings no review and no change.
* A comeback left until closing makes the customer leave with a 2★ review
  and −1 trust.

Coverage means the comeback day falls within the warranty written on the
slip. The quote tiles show durability next to the warranty ("bền",
"khá bền", "hên xui").

## 5. Tool upkeep (`data.tools`)

| tool | wear | when low | care (`rp_tool`) |
|---|---|---|---|
| 🔥 Mũi hàn | −12 % per fix that uses solder | below 30 %: one extra solder, and the joint may crack later (comeback risk); at 0 % no soldering | `clean`: +25 % up to 80 %, uses 1 solder · `replace`: 4 xu, 100 % |
| 📟 Pin đồng hồ đo | −6 % per multimeter test | below 20 %: the reading jumps around, the turn is spent and nothing is ruled out | `battery`: 2 xu, 100 % |

A worn tool is fixed the moment it is looked after. The parts clerk (staff
role `parts`) points out a tool that is low.

## Saves, validation, fairness

* New data keys (`clock`, `tools`, `regulars`, `comebacks`, `shelf_seq`
  and the counters) and new bench keys (`shelf`, `orders`, `cold`) are
  added with `setdefault` in `_data()`, which runs on every access and from
  `validate_data`. Old saves and old tasks load unchanged.
* `validate_data` checks the types and ranges of every new field and bounds
  the sizes (regulars ≤ 12, history ≤ 4, comebacks ≤ 8). `validate_task`
  checks the shelf (promise within 30 days of since, counters 0–99) and the
  orders (the item matches that fault's part for an orderable grade, the
  source matches the grade, cost 0–5000).
* All existing commands keep their payloads. New commands: `rp_order`,
  `rp_shelf`, `rp_answer` (no turn), `rp_back` and `rp_tool`.
* The truthful answer to a call is always safe. The cheap choice today
  (a salvaged part, no final test) is never forbidden, but its risk is
  written on the tile.

## UI (390 px first)

* Top of the bench and the idle panel: calls and comebacks waiting for an
  answer, each with its own buttons, and the shop clock beside today's
  mood.
* The idle panel shows "🗄️ Kệ máy chờ" as one card per device. Each card
  has the tag, the promise chip (on time, today, late) and a `reqList` of
  the steps: diagnosed, quote accepted, part (arrived, or when it will
  arrive), passed test, handed back. It also has a "Làm tiếp" button, a
  folded "🧰 Dụng cụ" section and the regulars' book.
* On the bench: a banner for a device on the shelf, order buttons next to
  fixes whose part is not in stock, a folded "Hẹn khách, để máy lại tiệm"
  with four promise buttons and the earliest honest date, and a warning
  when the tip or the meter is low.
* Audit fixes: the "Lời dặn của khách" summary now carries the global ▾
  marker at its right edge, and the device mat on phones is larger
  (the mat takes about half the card width, 132 px tall, 64 px device).
