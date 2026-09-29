# Tiệm Mây Nhỏ (mother & baby) — care mechanics

Date: 2026-09-29 · Career `mother_baby` · Files: `game/careers/mother_baby.py`,
`public/js/careers/mother_baby.js`, `public/css/careers/mother_baby.css`,
`tests/test_career_mother_baby.py`.

## Goal

Turn one-off gift orders into a caring loop that spans days, like farm, pet care
and delivery: a few families keep coming back, their babies grow between visits
so what fits changes, and the shop has to remember, stock ahead and be honest.
Everything is decided on the server, anything random is seeded, old saves keep
working, and it reads on a 390 px phone.

`mother_baby` is an original career, not a plugin: its rules live in
`game/giftshop.py` and the engine's `shop_*` actions. The order generator is not
touched, so every (day, slot) still makes the same order and saved tasks validate.
The care loop is a separate module that wraps giftshop's hooks.

**Wiring (one line, outside this sub-project's files):** `game/giftshop.py` must end with

```python
# Care loop: regular families, subscriptions, the diaper & formula shelf, registry.
from .careers import mother_baby as _care  # noqa: E402
_care.install(globals())
```

`install(ns)` wraps `handle` (new `gift_care_*` actions), `on_start`, `on_close`
(adds `care.lines` to the day summary), `public` (adds `care`), `validate` and
`upgrade`. It is idempotent. The module only imports the standard library at
module level. `game/careers/__init__.py` does not load it as a plugin, because it
is not in `ORDER`, and it must stay out of `ORDER`: it has no `SPEC`.
Until the line is added, the tests install it themselves and the scratchpad
launcher does the same for browser checks.

## Game rule: time

One day at the shop counts as **one week of the baby's life**. The UI says this
in the families book. Babies' weights follow a fixed curve per family
(tenths of a kg: birth weight + 0.2 kg/week for 13 weeks, then +0.1 kg/week).

| | rule |
|---|---|
| diaper size | NB under 5 kg · S 5–7 kg · M 7–10 kg · L from 10 kg |
| formula stage | stage 1 before 26 weeks, stage 2 from 26 weeks (≈ 6 months) |

## 1. Families book — "Sổ bé quen" (`care.fam`)

Four families, with days counted from the day the corner opens (`care.start`, day 2
in a new game, or the next day start for an older save):

| family | baby | feeding | first pickup | every |
|---|---|---|---|---|
| Chị Hoa | Na, 3 weeks | breastfed only (diapers only) | start+1 | 4 days |
| Anh Tuấn | Tôm, 10 weeks | Sao Mai | start+1 | 5 days |
| Chị Diệu | Mít, 21 weeks | Mầm Xanh (moves to stage 2 during play) | start+2 | 4 days |
| Chị Ly | Bắp, due at start+7 | Sao Mai | start+9 | 4 days |

Each record: trust 0–5 (Khách mới → Như người nhà), visits, the last pickup day,
the last size and formula handed over, and the last weight the shop *learned*
(only when the parent told it). Played normally, each baby moves up a size
(and Mít moves to stage 2) within about two weeks.

## 2. Subscription pickups — "Gói định kỳ"

* A family is due on `next` and `next+1` (two-day window). The pickup card shows
  last time's size, weight and formula, and today's news once known.
* `gift_care_ask {family}` (1 turn): the parent tells the weeks and today's
  weight, plus a hint when the old size is too small ("dán tới nấc cuối, hằn đỏ
  đùi") or the baby just turned six months. From trust 2 they tell it unasked.
* `gift_care_hand {family, size, lot|null, advice|null, confirm:true}`: one pack
  of the chosen size, and one can from the chosen lot for formula families.
  `lot:null` hands over diapers only when no fitting can is on the shelf.
  The sale is 60 xu per pack and 95 xu per can, credited at once.
  * All right (size fits today's weight, the family's brand at the right stage,
    the lot is in date and not recalled): trust +1 and 6 xp.
  * Wrong size, wrong brand or stage, or no milk: trust −1 and a 3★ review.
  * Expired or recalled can: the can is refunded, trust −2, a 1★ review and the
    `safety_miss` metric.
  * From trust 3, a perfect pickup with no upsell leaves a 3 xu tip.
* When the window's last day closes without a pickup, the family buys elsewhere
  this time: trust −1, `missed` +1, and the next pickup is scheduled.

## 3. Honest advice — "Tư vấn thật lòng"

When the window opens, a due family may have one question, rolled once from
`(start, family, next)` among the ones that fit the baby and that they have not
asked yet. Stage 2 is always asked when a stage-1 baby turns 26 weeks.

| question | when | honest | tempting |
|---|---|---|---|
| bigger size "to last" | NB/S | size by weight | +25 xu commission |
| weight-gain formula | formula, < 20 weeks | "gaining well, ask the doctor" | +50 xu |
| formula "just in case" | breastfed | "not needed" | +30 xu |
| first foods | 21–25 weeks | "wait for six months" | +20 xu |
| drooling, chewing | 16–34 weeks | one teether (sold from the gift shelf) | +45 xu kit |
| still stage 1? | turned 26 weeks | "move to stage 2" | "keep stage 1" (wrong) |

The answer is required in the hand-over. Option ids are neutral (`a`/`b`, and
the order varies), so the public state does not reveal the honest one.
Honest: trust +1 and 3 xp; the teething answer also sells one teether when in stock.
Upsell: the commission now, trust −1, and a 2★ regret review the next morning.
Wrong: trust −1.

## 4. Diaper & formula shelf — "Kệ bỉm sữa"

* Its own stock: packs by size (cap 12 each) and formula lots `{id, p, qty, exp,
  recalled, got}` (cap 10 cans per product). Starting stock includes one lot
  that expires on start+2, so first-expiry-first-out matters on day one.
* `gift_care_order {item, qty 1–4, confirm:true}` pays the cost now (34 xu a pack,
  55 xu a can). It arrives the next morning. A new lot's use-by is 8–16 days,
  seeded by the order id.
* A can is expired when `exp < today`. `gift_care_pull {lot}` works only on an
  expired or recalled lot, so tapping it cannot reveal anything. Expired lots are
  a loss (`care.waste`). Recalled lots are credited back by the supplier.
* **Recalls:** on start+4 and every 9 days after, the supplier recalls one lot on
  the shelf. The pick is seeded and weighted towards products a family needs
  within 3 days. The notice (lot code, reason) is public and the lot is tagged.

## 5. Baby-shower registry — "Danh sách quà mừng" (Chị Ly)

* Opens on start+2, and the shower is on start+6. The lines are towel ×2,
  Gấu Mật Ong ×1 (the box says 3+), socks ×2, bottle ×1 and blanket ×1. Friends
  buy them on fixed days (start+3…+5).
* `gift_care_aside {line}` works on a bought line. It takes the goods from the
  gift shelf (needs stock) and credits the friend's payment.
* `gift_care_swap {line, item}` works on a line whose box is not newborn-safe,
  until the line is set aside. The swap must be to a newborn-safe item at a
  similar price. Chị Ly agrees: trust +1 and 5 xp. Safe lines are refused with
  the label as the reason.
* `gift_care_shower {confirm:true}` works on shower−1 or on the shower day, with
  at least one line in the box. The wrapping costs 5 xu.
  * Complete and safe: 5★ review, trust +1 and 15 xp.
  * A 3+ item in the box: 3★ review and trust −1.
  * A bought line missing: 3★ review, trust −1 and 5 xp. Friends were never
    charged for it.
* If the shower day closes without a delivery, the set-aside goods go back to
  the shelf, the friends are refunded, trust −2 and a 1★ review.

## Day summary

`on_close` adds `care.lines` to the gift shop's day summary: pickups (and how
many were perfect), honest answers and upsells, pulled lots, cans still on the
shelf that are expired or recalled at tomorrow's date, missed windows, the
shower outcome, and **tomorrow's pickups** with the last size and weight known.
This forecast is what lets the player stock ahead.

## Saves, validation, fairness

* Data: `c.ext.data.gift.care` (`v:1`). `giftshop.public` rebuilds `data.gift`,
  so the raw record (question kinds, weights not told yet, future recalls) never
  reaches the client. The public view is built by `care.public`.
* Old saves: there is nothing until the next `start_day` from day 2. The timeline starts
  that day, so a day-20 save meets newborn Na, not a 5-month-old. Mid-shift, the
  care actions answer "opens at the next day start" and change nothing.
  `upgrade`/`ensure` fill new keys with `setdefault`.
* `validate` checks exact key sets and ranges for every family record, lot (id
  pattern `MX1-01`, product matches id, qty caps, unique ids), order, notice,
  registry line (swap must be a newborn-safe item) and log entry. It also bounds
  every list.
* Every action validates types strictly, and a failure changes nothing. Actions
  that spend money or cannot be undone require `confirm:true`. Each care action is
  one turn. They need an open shop.
* Existing commands (`shop_*`, `gift_*`, `order_stock`…) and their payloads are
  unchanged. The order generator, the surprises and the tests' `next_move` are
  unchanged.

## UI (390 px first)

* **Pinned request strip** at the top of the job sheet. It is sticky under the
  sheet head, so it stays in view while browsing the shelf. It shows what the
  customer asked (qty × item, or the kit, party list, open occasion or return),
  the budget and the wrapping, with a basket chip (items · xu, red when over
  budget). The existing “＋ Thêm” add button is kept.
* **Góc bỉm sữa & khách quen**: a collapsible section in the job sheet with tags
  for pickups due and lots to pull. It is always open in the between-customers
  panel.
  * Pickup cards: the family, weeks, feeding, trust hearts and last time. There is
    an ask button or today's news, size choices (range, stock), lot choices (brand,
    stage, code, use-by, recalled or expired tags, and "no fitting can") and the
    parent's question with its answers. A `reqList` checklist shows the choices
    made, and one "Trao gói · N xu" button asks for confirmation.
  * Registry card: each line with its age label, status, "Để riêng" (with shelf
    stock) and "Gợi ý đổi" (opens the newborn-safe choices). The deliver button
    says how many lines are still missing.
  * A "Kệ bỉm sữa" fold (open when a lot needs pulling): recall notices, lots with
    pull buttons, packs and cans with a quantity stepper and an order button.
  * A "Sổ bé quen" fold: every family with status, weeks, last size and weight,
    the next pickup, missed visits and trust, the time rule, the trust perks and
    the recent log.
* Day summary: a "Góc bỉm sữa & khách quen" list under the gift shop's numbers.
