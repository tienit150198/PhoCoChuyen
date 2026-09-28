# Kết quả kinh doanh: end-of-day profit and loss

## Goal

After selling, and at the end of a day, the owner should see three things clearly:

- **revenue**;
- **profit or loss**;
- **how much they actually earned**, meaning what reached their wallet.

Today the end-of-day sheet shows only "Thay đổi trong ca: +X xu · thu A · chi B".

The feature is client only: `public/js/v4/pnl.js` and `public/css/pnl.css`. The server does not change. Every number is read from data the client already has:

| Data | Where it comes from |
|---|---|
| `c.ops.finance.ledger` | Rows `{id, day, turn, amount, category, reason, ref}`, written by `game/operations.py` `record_money`. `public_operations` copies the whole ledger to the client, up to 1200 rows. |
| `c.shift_summary` | The `end_day` summary from `game/engine.py`: `day`, `income`, `cost`, `net`, `operations` (`wages`, `utilities`, `rent_accrued`, `unpaid`), `expired_value`, `job.salary` and `journey` (`life_day`, `living`, `upkeep`, `salary`, `wallet`). `journey._end_of_day` adds `journey`. |
| `state.journey` | `story`, `wallet`, `places[cid].withdraw_max` and `history` (the last 30 wallet moves, each with the life day it happened on). |
| `content.inventory.items[career]` | Catalogue cost of each stock item. Used only for the per-order estimate. |

## Accounting basis

The statement is **cash basis, per career day**. It uses the ledger rows where `row.day === day`.

- Every row lands in exactly one group, so `revenue − cogs − opex − losses + other + transfers` equals the ledger's own sum for the day. The harness checks this for every day of the real ledgers it generates.
- **Owner transfers are shown but never count as profit.** These are `owner_draw`, `owner_capital` and `salary_to_wallet`.
- The ledger is more complete than `summary.net`. Two things reach the ledger after `summary.net` is computed: the career's `on_close` bonuses (for example the restaurant's "Thưởng hạng S", +12) and the salary, paid in `employment.on_close`. The ledger also counts bills paid on the morning of that day.
- **Bills are the one accrual gap.** Wages, utilities and rent become bills when the day closes and are paid later, usually on the next day. The card therefore adds one line for each of these:
  - "Chi phí hôm nay sẽ thành hóa đơn trả sau: N xu (…)", from `summary.operations`. This amount is not subtracted in the statement.
  - "Đã trả N xu hóa đơn của ngày trước", the bill categories paid today, which are already in operating costs.
- **Giá vốn is stock bought that day**, not stock used. So a day that sells from older stock shows a high margin. When the career keeps `task.served` (the restaurant does), the card adds "Nguyên liệu đã dùng cho K đơn hôm nay: ~X xu theo giá nhập". X is the catalogue cost of what went into the bowls.
- `summary.expired_value` appears as a note: "Hàng hết hạn phải bỏ". That money was already spent when the stock was bought, so the note does not change any total.
- **Biên lãi = (lãi ròng − khác) ÷ doanh thu.** This is the operating margin, without rewards and support. The card shows it only on a profitable day. On a loss day with losses, it shows instead "Không có thất thoát thì hôm nay đã lời N xu" whenever that is true.

## Category mapping

| Group (label) | Categories | Where they are written |
|---|---|---|
| **revenue** (Doanh thu) | `revenue`, `room`, `tip`, `commission`, `salary`, `service`(+) | `engine.task_done` "Hoàn thành:", careers, `social`, `boba`, `homestay`, `tour_trip`, `employment`, incidents (late invoice paid) |
| **cogs** (Giá vốn) | `stock`, `materials`, `tour_cost`, `refund`(+) | `inventory.inv_order`, `boba`, `giftshop`, `social` market, `experiences` tour. A supplier refund (+) reduces the cost of goods. |
| **opex** (Chi phí vận hành) | `wage`, `utility`, `rent`, `insurance`, `tax`, `repair` (paid bills, category = bill kind), `staff`, `utilities`, `recruitment`, `training`, `marketing`, `security`, `upgrade`, `property_setup`, `upkeep`, `reopen_fee`, `situation`, `other_cost`, `legal`, `office`, `bonus`(−), `gift`(−), `service`(−) | `operations` (bills, hiring, training, bonus, property, security), careers, `journey` (upkeep, reopen), `situations`, incidents |
| **losses** (Thất thoát) | `theft_loss`, `scam_loss`, `bad_debt`, `unpaid`, `discount`, `fine`, `under_table`, `damage`, `medical`, `refund`(−), `compensation`(−), `incident`(−) | `operations` security cases, `happenings`, `incident_content`, `giftshop`, `homestay`, `restaurant`, `cafe_bakery`, `feedback` |
| **other** (Khác) | `grant`, `recovery`, `insurance_recovery`, `security_reward`, `skill_reward`, `goal_reward`, `activity_reward`, `festival_reward`, `story_reward`, `situation_reward`, `promotion`, `other_income`, `gift`(+), `compensation`(+), `bonus`(+), `incident`(+) | `operations`, `experiences`, `food_service`, `boba`, `classroom`, `situations`, `social`, `happenings` |
| **transfers** (Chuyển tiền của chủ, never profit) | `owner_draw`, `owner_capital`, `salary_to_wallet` | `journey._transfer` |
| *unknown category* | falls into **other**, signed, and is labelled with the row's `reason` | |

(+) means an inflow and (−) an outflow. Two-sided categories pick their group from the sign. For example, `refund`(+) is a supplier paying back and `refund`(−) is money returned to a customer.

The implicit categories from `classify_money` are all covered: `revenue`, `story_reward`, `stock`, `materials`, `upgrade`, `other_income` and `other_cost`.

**Timing quirk:** `salary_to_wallet` is stamped on the next career day, because `journey.after` runs after `c.day += 1`. The "Bạn kiếm được" block therefore takes the salary from `summary.journey.salary`, not from the ledger.

## The card: `pnlCard(env)` or `pnlCard({career, summary, journey, cid, content, day?})`

The card is built from these parts, top to bottom:

1. **Eyebrow and hero.** The eyebrow reads "KẾT QUẢ KINH DOANH · NGÀY d", or "KẾT QUẢ NGÀY LÀM" for a salaried office job. Below it is a big net figure, green or red on the `--good-soft` / `--bad-soft` plate, followed by "Lãi ròng hôm nay · biên lãi X%", "Lỗ hôm nay" or "Hòa vốn". Last comes one plain lead sentence, for example "Hôm nay lỗ 162 xu, nặng nhất là bị trộm, mất tiền (60 xu)."
2. **Statement table.** It has seven rows: Doanh thu, − Giá vốn, = Lãi gộp, − Chi phí vận hành, − Thất thoát, + Khác and = Lãi/Lỗ ròng. Each row has a one-line explanation, such as "Lãi gộp = tiền bán − tiền hàng". On shop days, zero rows stay visible but muted, so the structure teaches itself. Office days hide the zero rows and the goods rows.
3. **Margin note** and the **bills note**, as described under "Accounting basis".
4. **"Chi nhiều nhất hôm nay".** This is the top 3 outflows, grouped by short reason (the text before " · "). Each has a group label and a category label, plus a proportion meter coloured by group: `--warn` for giá vốn, `--second` for vận hành and `--bad` for thất thoát.
5. **7-day mini chart.** An inline SVG with one bar per day, up to 7 days, showing net profit.
   - Zero baseline; profit bars grow up in `--good` and loss bars hang down in `--bad`.
   - Today's bar is solid and carries a direct value label. Older days are 55% opacity.
   - The caption gives the total and the average per day.
   - Each bar has a `<title>` tooltip, and the SVG has an `aria-label` that lists every day.
6. **"Bạn kiếm được"** (story mode only), on a `--second-soft` panel.
   - Lines: +owner draw today (ledger), +salary to wallet, −capital put in, −rent and meals, −upkeep.
   - "Ví thay đổi ngày sống N" is the sum of `journey.history` rows for that life day, falling back to the sum of the lines above. Then comes "Ví hiện có".
   - "Còn N xu lời hôm nay đang ở quỹ tiệm, rút được tối đa M xu", followed by the button `data-action="jrView" data-view="wallet"`. The button appears only when there is profit to move or the wallet is in debt.
   - Outside story mode, one note says where the profit went.
7. **"Sổ chi tiết ngày d · K khoản"** (`<details>`). Every line grouped by P&L group and category label, with a count, plus a note that transfers are not profit.

`pnlOf(career, day)` returns:

```
{day, count, revenue, cogs, opex, losses, other, transfers, gross, net, cashChange,
 margin, grossMargin,
 lines: {group: [{category, label, amount, count}]},
 topCosts: [{reason, label, group, amount, count}],
 draw, capital, salary, tips, billsPaid, salaryOnly}
```

Costs are positive numbers. `other` and `transfers` are signed.

`pnlSeries(career, day, n = 7)` returns `[{day, net, revenue, count}]`.

## Per-order receipt: `orderReceipt({career, task, content, items?, cost?})`

It returns `{sale, tip, refunds, cost, profit, estimated, text, html}`, or `null` before the task has been paid. The text reads, for example, "Bán 71 xu · tip 7 xu · vốn ~26 xu · lời ~52 xu".

- **sale and tip:** the ledger rows whose `ref` is the task id. `task_done` and tips both use `t.id`.
- **cost:** the first of these that applies:
  1. an explicit `cost`;
  2. the catalogue cost of `items` (`{itemId: qty}`);
  3. for the restaurant, `bowlItems()` of every bowl in `task.served.bowls`: noodles, box, chili pumps, toppings, and 1/6 of a broth pack per bowl;
  4. the bowls' real lot cost.
- The catalogue estimate is marked with "~". Opening stock has `unit_cost = 0`, so real lot costs would say "vốn 0" early in the game.

## Wiring (the lead does this)

`public/index.html`, after the `journey.css` link:

```html
<link rel="stylesheet" href="/css/pnl.css">
```

`public/js/app.js`, imports:

```js
import {pnlCard,orderReceipt} from './v4/pnl.js';
```

`summaryView()`: insert the card right after the three stats. In the return, change `…${stats}${notes.length?…` to `…${stats}${pnlCard(env())}${notes.length?…`. The card sits inside `.sheet-body.summary-v6`, so the `sheet` container queries apply.

Once the card is in, the old `jr` notice ("Ngày sống thứ…") and the `job.salary` notice repeat the same numbers. The lead may drop both, or keep them for their probation and debt text.

**Optional per-order hook.** After a successful serve, meaning a command result for a task that is now `completed`, show the receipt in the toast:

```js
const r=orderReceipt({career:room(),task:room().tasks.find(t=>t.id===tid),content:api.content}); if(r) toast(r.text);
```

It can also go in a task card's done state as `r.html`, which carries the `.pnl-receipt` style.

**i18n.** The English pack does not have the new strings yet. Run `scripts/i18n_extract.py` after wiring.

## Verification

The harness lives in the session scratchpad as `pnl/`:

- `gen.py` plays a real restaurant for 5 days in story mode through `apply_action`. The play includes:
  - supplier orders and a start-up grant;
  - four orders a day with bills paid;
  - an owner draw on day 4.
- It also plays 3 days of `tax_payroll` with salary.
- It then saves `public_state` to JSON.
- `site/harness.html` renders:
  - the real day 5 (profit);
  - the real day 4 (draw);
  - a synthetic loss day 6, made by appending theft, scam, refund, fine and a recovery to the real ledger;
  - the real office day;
  - a day outside story mode;
  - three order receipts.

  It also checks `cashChange` against the ledger's sum for every day.
- `shot.py` takes screenshots at 390×844 in the `kem` and `dem` themes. There is no horizontal scroll (`scrollWidth` is 390).
- `node scripts/check_js.mjs` passes for `pnl.js`.
