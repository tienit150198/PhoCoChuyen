# Tạp Hoá Cô Ba — care mechanics (sub-project 3)

Date: 2026-09-29 · Career: `grocery` · Files: `game/careers/grocery.py`,
`public/js/careers/grocery.js`, `public/css/careers/grocery.css`, `tests/test_career_grocery.py`.

## Goal

Before this change the shop was mostly a same-day till. The credit book paid
itself back on a timer, real shelf lots were always sold oldest-first no matter
what the player did, and nothing told you what tomorrow would need. This change
adds four small things that carry over from one day to the next, so the shop
feels like somewhere you look after:

1. **Sổ nợ có tình**: neighbours on the credit book have a trust level. Some
   days they are short of money, a repayment plan helps, and a debt that is
   left alone too long can be lost.
2. **Xoay kệ thật**: new stock put in front of old stock is a real state of
   the shelf. Until the shelf is rotated, customers take the fresh units first
   and the old lot goes out of date behind them.
3. **Giỏ quen hàng tuần**: four regulars have a weekly shopping list. You see
   it the day before and pack it on the day. They collect it at closing time.
4. **Dự báo ngày mai**: tomorrow's mood (already fixed by the day), what
   tomorrow's first customers and lists will need, and what will run short.

Everything is decided on the server and is deterministic. The one new random
roll, a neighbour's lean days, uses `kit.rng(ID, 'hard', neighbour, block)`,
so it depends only on the save's day. `make_task` still never reads player
state, and every existing (day, slot) produces the same task as before.

## 1. Credit book: trust, lean days, plans, bad debt

Each ledger row gains `trust` (0–5), `late` (bool), `plan` (None or
`{each, left, next}`) and `written` (the amount written off in the past).

* **Trust → limit.** The effective limit is the base limit × 0/60/80/100/120/140 %
  for trust 0–5 (names: Ngưng ghi sổ, Dè dặt, Tạm tin, Tin, Tin cậy, Như người nhà).
  Starting trust: Chú Bảy 2, Chị Lan 4, Bà Sáu 4, Chị Diệu 3. At trust 0 the
  book is closed to new credit.
* **Trust moves**
  * +1 when a debt is paid off with no overdue in that spell;
  * +1 when a repayment plan is paid through;
  * −1 once when a debt goes overdue (older than 5 days);
  * −1 when you remind someone on a lean day (“biết nhà người ta đang kẹt mà còn nhắc”);
  * −1 when you refuse credit that was within the rules (the existing `credit_harsh`).
* **Lean days (`kẹt tiền`).** In each 6-day block a neighbour may have a 2–3 day
  spell (Chú Bảy 65 %, Lan 40 %, Sáu 35 %, Diệu 45 %, never before day 4). Chú Bảy's
  scooter also breaks down on days 5–6 (his payday), so everyone meets the
  mechanic in the first week. It
  has a reason the whole alley knows about (a scooter clutch, a sick child, a late
  pension, a quiet week at the rice shop), and the ledger shows it. On a lean
  day, payday and reminder repayments are skipped (“xin khất”).
* **Repayment plan (`gr_plan {npc, parts: 2|3}`, no turn).** It splits the
  balance into 2 or 3 instalments, one every 2 days, starting 2 days later.
  Instalments are paid even on lean days. The plan restarts the overdue clock
  (`since = today`), and no new credit is written while it runs. Paying the
  plan through gives trust +1.
* **Bad debt.** When a debt is more than 12 days old, the neighbour's trust is
  1 or less and there is no plan, Cô Ba writes it off at the morning count.
  The balance leaves the book (`written`, `stats.bad_debt`), with a log line and
  a note in the day summary. No cash moves, because a credit sale never put
  money in the till. The loss is the receivable you will never collect.
  Afterwards trust is at least 1.
* The existing rules stay. Payday cycles, “remind today → pays tomorrow”,
  once-a-day reminders and no new credit on an overdue debt all work as
  before.

## 2. Shelf rotation that matters

Dated goods on real stock: milk, egg, bread, greens, tomato.
`data.rot[item]` is the list of lot ids that were on the shelf the last time it
was put in order.

* A shelf is **unrotated** when a lot not in that list (new stock) expires later
  than a lot in the list that is still on the shelf. New stock that is not
  fresher is simply accepted into the list.
* While unrotated, every sale (till, rush queue, bulk order, packed lists,
  funeral order) takes the **new lots first**, the way customers pick from the
  front. Old units stay behind, reach their date and are thrown away at closing
  (the existing inventory expiry). Inspectors also find them (the existing
  inspection).
* `gr_rotate {item}` (1 turn, a physical action) puts the shelf in order.
  Finishing a shelf task for that item with correct FIFO also rotates the real
  shelf. An idle shelf helper (`gr_shelf`) rotates one unrotated shelf per turn.
* The existing “sold a unit dated today” slip now simulates the real pick
  order, so it stays truthful in both states.

## 3. Weekly regular lists

| regular | pickup | list (stock units) | pays |
|---|---|---|---|
| Bà Sáu | days ≡ 3 (mod 7) | rice 2 kg, egg 10, greens 3 lạng, tomato 2 lạng | cash |
| Chị Diệu | days ≡ 4 | rice 5 kg, oil 1, fish sauce 1, egg 20 | transfer |
| Chị Lan | days ≡ 6 | milk 8, egg 10, noodle 5, bread 2 | ghi sổ if the book allows, else cash |
| Anh Khoa | days ≡ 0 | milk 4, soda 6, snack 3, bread 2 | transfer |

(First pickup on day 3. One seeded item a week gets a little more,
`kit.rng(ID, 'list', npc, week)`.)

* The list shows up the day before, in the forecast and the "Giỏ quen" tab,
  so stock can be ordered in time.
* `gr_pack {npc}` (1 turn, physical, pickup day only) packs whatever is still
  missing from available stock (other open bills keep what they hold). It can be
  run again to top up. Packing uses the real pick order: packing from a shelf
  with a lot dated today puts those units in the bag (`stale`).
* At closing the regular collects: value = list prices − the weekly promos. Bond
  (0–5, start 2) goes +1 for a full, fresh bag, −1 when nothing was packed
  (“sang Mây Mart”) or a stale unit was packed, and stays the same for a partial
  bag. Bond 3+ adds a 2 xu tip, and bond 5 a 4 xu tip. **Bond 4+ means the regular no
  longer brings the Mây Mart flyer to the till** (no haggling).

## 4. Tomorrow's forecast

`public_data.forecast` has tomorrow's mood and the day after's, the regular
lists due tomorrow, repayments due tomorrow, and the items where
**tomorrow's demand** (the first three customers of tomorrow as generated by the
day's own generator, plus tomorrow's lists) is more than the stock that will still be
good tomorrow plus what is on the way. Numbers are rounded to “khoảng”. The
day-close summary repeats the headline. “Needed” includes a 20 % reserve for
walk-ins and carried-over work. “Still good tomorrow” leaves out lots whose last
selling day is tomorrow, because shop policy pulls those in the morning. Stock
on the way counts.

## 5. “Việc chăm hôm nay”

`public_data.care` gives server-computed rows: pull today's expired lots,
unrotated shelves, today's lists to pack, near-date stock to clear, lean-day
neighbours (offer a plan), overdue or due-to-remind debts, and tomorrow's
shortfalls. The client shows them with `ui-kit.reqList`, with one button per
actionable row.

## Save compatibility and validation

* `_extend` adds the new ledger keys, `rot`, `lists` and the new stat keys with
  `setdefault`, and `_sync_rot(c)` (from `validate_data`, `on_start` and
  `handle`) seeds `rot` from the lots on the shelf, so an old save starts
  rotated.
* `validate_data` range-checks trust, plan (each 1..10⁶, left 1..3, next day),
  written, rot (known items, ≤ 40 short ids), lists (known regulars, bond 0–5,
  packed items of that list, bounded counts).
* Existing commands keep their payloads. New ones are `gr_plan` (no turn),
  `gr_rotate` and `gr_pack` (physical).

## Not changed (noted for the lead-time rework)

The grocery has no ordering code of its own. It buys through `inv_order`, and
the UI still labels supplier lead time as “sau N nhịp” (`supplierPick`, the
order confirm text, and the bulk “Nhập hỏa tốc … có ngay” button). `_deal`
reads `in_transit` orders for room. These are left untouched.

## Non-goals

No new stock items (umbrellas, raincoats), no Tết calendar, no engine or
inventory changes, and no cash movement for bad debt.
