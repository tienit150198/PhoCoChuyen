# The three original desks over several days, legacy stock on the shop clock, AI support calls

Date: 2026-09-29 · Branch: care-wave1 · Careers: `pharmacy` (Quầy Bình An), `accounting`
(Góc Sổ Xinh), `customer_care` (Trạm Lắng Nghe), plus the legacy stock of `mother_baby`.
Files: `game/engine.py` (care section at the end, the shipment code, the classic `ph_`/`ac_`/`cs_`
rules and the public views), `game/operations.py` (stock helper), `game/giftshop.py` (auto-solver),
`server.py` (`/api/ai/support_call`), `public/js/app.js` (`warehouseView`, the three job views and
their helpers), `public/css/desks.css`, `tests/test_desk_care.py` and the pinned stock tests.

## Goal

Before, these careers were a day of separate cases: the paperwork desks (`desk.py`) plus one
classic counter task a day. Nothing carried over except the carried tasks. The owner wants care
loops that span days, like farm, pet care and restaurant: regulars, rotation, deadlines, cases
that stay open. The legacy stock (`order_stock` / `receive_stock`, `ready = turn + 2`, "Chờ một
nhịp") must use the real delivery windows of the shared shop clock. Support calls get an
in-character customer voice.

Rules: all on the server, seeded from ids and days (`random.Random("a|b|c")`), no secrets in
the raw save, strict validation, older saves migrate, existing commands keep their payloads,
fair (no death spirals), phone first at 390 px.

## Shared: the shop clock

`_clock(c, career)` wraps `inventory.clock` (08:00–20:00 for these careers, 20 minutes per
ticking action). When the day's "Mở ca ngày N." journal row is missing (hand-built test saves)
it anchors on the turn today's first task was dealt. Absolute minutes (`day × 1440 + minute`)
are used for every wait, deadline and timer.

Care data lives in `c.ext.data.care` (next to the desk's `ext.data.desk`). It is created at the
first `start_day` or, for older saves, lazily at the first action of an open shift. Public views
replace it with a derived projection (`data.care`).

Paper-desk cases get today's care reminders prepended to their `bulletin` (public view only),
so the reminders are visible while the player works a desk case. Day summaries append care lines
to `summary.career.lines`.

## B. Legacy stock on the shop clock (mother_baby, pharmacy)

| career | suppliers (`order_stock {item, qty, supplier?}`, default `partner`) |
|---|---|
| mother_baby | `market` Chợ sỉ đồ sơ sinh · next morning, order before 17:00 · ×0.85 · `partner` Hạt Nắng · two runs (cut-offs 11:00/15:00, drops 13:00–14:00/16:30–17:30) · ×1 · `express` · 30–60 min · ×1.35 |
| pharmacy | `partner` Nhà phân phối Thiện Tâm · **twice-daily distributor runs** · ×1 · `depot` Kho tổng Bình An · next morning, before 16:00 · ×0.85 (no courier for medicine) |

* The windows reuse `inventory._schedule` / `_eta` / `quote` (read-only): a seeded arrival inside
  the promised window, sometimes late with the supplier's reason, never lost. No shortages
  (`actual = qty`, as before).
* Stored parcel: `id, item, qty, actual, supplier, cost, status, placed, lo, hi, at, late, day,
  told?` — no `ready`. `receive_stock` checks the clock at the door (before this action's own
  20 minutes), matching the public `ready_now`. Refusal: "Kiện chưa tới. Dự kiến 13:30 hôm nay
  (còn ~4 giờ 30 phút)…". The first time a parcel is at the door the tick says so once.
* Public parcels add the ETA block (`eta_label, window, left_label, progress, late_note…`) and
  hide `at`, `late` and `actual` until due. `c.stock_desk = {clock, suppliers[+quote], default}`.
* `migrate_state` turns old parcels into the new shape (`at = now + beats left × 20 min`, after
  closing → next morning), like `inventory._upgrade_orders`. Received parcels are trimmed to 40.
* The operations stock helper receives only parcels at the door (`engine.shipment_here`), through
  `engine.stock_received` (which also dates pharmacy boxes). The gift-shop auto-solver orders the
  `express` courier when a customer is waiting.
* The assistant upgrade still brings waiting parcels to the door.

UI (Kho): "Bây giờ 09:00", chips, "Kiện sớm nhất: 13:30 hôm nay", **⏳ Chờ thêm 20 phút**
(`advance`) instead of "Chờ một nhịp", parcel cards with supplier, ETA, countdown, progress bar
and the late note, a supplier picker with live quotes, and "Đặt nhập" with a confirm that states
the price and the promised arrival. No "nhịp" anywhere in the flow.

## A1. Pharmacy — Quầy Bình An (simulated slips, never real drugs or doses)

**Lot book (use-by and recalls).** Each valid lot (`P-0x-A`) is split into dated batches
`{id L001, lot, qty, exp, got, recalled, warm}` that always add up to the shelf count (stock that
leaves through other doors goes first-expiry-first-out). A new game starts with two near-dated
boxes of P-02 and P-05 (use-by day 3) and the rest 8–12 days out; received parcels get 8–14 days.
* A box that is **out of date, recalled or warmed** on the shelf blocks the whole lot: `ph_pick`,
  `ph_check`, `ph_deliver` and refills refuse with "Kệ P-02-A còn 2 hộp quá hạn… Rút khỏi kệ trước".
* `ph_lot_pull {batch}` works only on a flagged batch: expired/warm → loss (`care.waste`), recalled
  → the distributor refunds 8 xu a box.
* Recalls: on `start+3` and every 6 days, one batch (weighted to products regulars need soon) is
  recalled with a public notice.
* At close: flagged batches still on the shelf add desk risk points (the every-4-days inspection
  reads them); boxes whose use-by is today are listed for tomorrow.

**Fridge log (cold chain, 2–8°C).** Two readings a day: morning before 12:00, afternoon from
14:00 (`ph_fridge_log {slot}`). About one day in four (from day 3) one reading is above 8°C with
a visible clue: *door* (ron bong, máy chạy êm) or *power* (đèn tắt, máy nén im). `ph_fridge_fix
{slot, fix}`: `door` (free) is right for a door; `move` (tủ dự phòng + thợ, 15 xu, confirm) is
always safe. Door-fix on a power cut, or no fix by close, warms the P-05 boxes (must be pulled)
and adds risk. Missing readings add risk; the afternoon one only counts once the clock reached
14:00. A 7-day score (3 points a day; days not yet written count 2).

**Regulars' refill slips ("phiếu lặp lại").** Bác Năm (P-02 × 1, every 5 days), Bà Tư (P-03 × 2,
4), Chị Mận (P-05 × 1, 6), Chú Lộc (P-06 × 1, 7); first due `start+1…4`.
* `ph_care_call {who}` ("nhắc lấy thuốc") from the day before to the due day → they come on the due
  day. Without a call they come a day late. Window: due and due+1.
* `ph_care_hand {who, confirm}`: the lot must not be held or blocked and must have the boxes.
  30 xu; on time → trust +1 (+5 xu thank-you from trust 3); late → trust unchanged.
* The window closes without a hand-over → trust −1, "lỡ đợt", next due scheduled. No blame after a
  long break away (the dates roll forward).
* Summary: tomorrow's pickups with shelf and on-the-way counts, so the player can order the
  midday run in time.

## A2. Bookkeeping — Góc Sổ Xinh: client books every month

Four small shops (Quán cơm cô Hoa — the existing NPC, Tiệm bánh Na, Tạp hóa bà Sáu, Sửa xe chú
Tám). One bookkeeping **month = 5 game days**; each client's box arrives on `start + offset + 5m`
and must be closed within 3 days (deadline shown).
* `ac_book_open {client}` → receipts and how many bank lines have no receipt.
* `ac_book_check {client, check}` — `dup` (hóa đơn chụp trùng), `personal` (chi tiêu nhà),
  `round` (làm tròn số), `cash` (phiếu chi tiền mặt): reveals and fixes that kind of mistake.
  Issues are seeded per (client, month): each of the client's habits usually shows up (85%),
  other kinds rarely (12%).
* **Client file:** a habit is written into the file the first time a check finds it (and "hay quên
  hẹn" when a follow-up call was needed). Known habits are starred as "nên soát", so a returning
  client costs fewer turns; unknown ones stay hidden (only their count is public).
* **Missing sources:** `ac_book_chase` → the owner promises them in 1 day (2 for Bà Sáu). Reliable
  clients send them at the next opening; Bà Sáu forgets — a **follow-up** chase on/after the
  promised day brings them at once.
* `ac_book_close {client, note, confirm}`: still missing receipts → only "khóa kèm ghi chú thiếu"
  (`missing_note`). Grade: `perfect` (every issue checked, sources in, on time) 100% of the fee,
  +1 trust (+10 xu from trust 4); `good` (with the missing note) 75%; `rough` (a kind with
  mistakes left unchecked) 40%, trust −1, a desk risk point. Late close −15 xu.
* Deadline day closes open → late, trust −1; the next day's close → the owner takes the box back
  ("lost", trust −1). Then the next month continues. Trust never goes below 0; nobody leaves.
* The classic reconciliation's `ac_request_source` now answers on the clock: +40 min on days 1–2,
  otherwise the next morning at 08:30 (`source_at`).

## A3. Support — Trạm Lắng Nghe

**Cases that stay open for days.** `cs_execute` on a classic case stores `ready_at` and `wait`:
days 1–2 and `guide` +40 min (đầu mối); `refund` +2 h (kế toán, after closing → next morning);
`reship` next day 10:00–14:00 (kho); `exchange` day+2 11:00–14:00; `trace` day+1 15:00–17:00
(day+2 while Mây Express is slow in a zone). The case is carried, the task is still `executing`,
and the result arrives on the shop clock (`tick_pending`). Handover to chị Mai: +40 min.

**SLA timers.** From day 3 a new classic case must get its first contact (`cs_identity`) within
2 hours of shop time; late → one mistake, patience −15, the customer's tone worsens. A case
waiting into another day needs an **update call before 12:00** each morning (`cs_call` with an
update/sorry line); missed → one mistake, patience −10, "khách phải tự gọi lên hỏi". Mistakes
feed the existing review stars.

**Customer history card.** `care.people[npc] = {n, last[4]}` from every closed support case
(paper desk or classic): title, outcome ("gửi bù · theo 1 ngày · trễ hẹn"), stars. Shown on the
case ("Lan đã gọi 4 lần") and on the board ("Gọi lần 5").

**Satisfaction trend.** At close, the day's support review stars are averaged into `care.trend`
(7 days) with ↑/↓ in the summary; the board draws the bars.

**Handover from yesterday's shift.** At `start_day` (day ≥ 2) open support cases become a
handover card: next step, ETA, whether an update call is due, plus "tin mới đầu ca" for results
that came in. `cs_handover_read` (free) marks it read.

**Calls (`cs_call {task, pick|text}`).** Needs a verified case. Picks: `update` (the true status
and ETA from the save), `sorry`, `ask`, `bye`; or typed text (≤ 200 chars) classified by rules:
rude > promise > sorry > update > bye > ask/other. Rule-based effects only: sorry/update calm the
customer (update only when there is something real to report), rude → one mistake and patience
−10, a promise ("cam kết, đảm bảo, hoàn tiền ngay…") calms now but costs one mistake when the case
closes. Words never move money or change a proposal. The first line of the day takes 20 minutes;
the rest of the call is free; 8 lines a day. The customer's scripted line is built from the case
facts, tone and intent and stored first; the call keeps the last 20 lines.

## C. AI route for support calls

`POST /api/ai/support_call` (server.py), guarded like `/api/ai/chat` (Host, session cookie, CSRF
header, Origin/Sec-Fetch-Site, the command rate limit, `ai_chat_budget`).

```
request  {career:"customer_care", task, pick? | text? (1..200), request_id?, expected_revision?}
response {state, revision, result:{reply, message, intent, tone, tone_label, tone_moved, kept, effects},
          mode:"ai"|"scripted"|"guard", reason, reply}
```

1. Runs `cs_call` through `Store.command` (revision-checked, idempotent by `request_id`): every
   rule and the scripted customer line are stored.
2. With consent, a configured provider and budget, `ai.persona_reply(..., purpose='support_call',
   context=engine.cs_call_context(...), canonical=scripted line, history=last 8 call lines)`.
   The context holds only facts the save shows (case, status sentence, ETA, what the customer
   knows, mood, order value once verified) — never the right solution.
3. If the reply passes the guards (no new numbers, no state claims, no links, character kept) the
   stored line is rewritten in one small transaction only if it is still the last scripted line
   (`mode:"ai"`, `canonical` kept). Abusive player text → an in-character deflection (`guard`).
4. Otherwise the scripted line stays (`reason`: `no_consent`, `not_configured`, `rate_limit`,
   `new_numeric_claim`…). 409 returns the fresh state; the client retries once, and falls back to
   the plain `cs_call` command when the route is unreachable.

UI: a "📞 Gọi {name}" panel inside the case view with bubbles (newest in view), an **AI** badge
on AI lines (title = the scripted line), a typing indicator, the four picks as chips, a
200-character box, the customer's mood chip and "còn N lượt nói hôm nay".

## UI entry points

* Pharmacy: the existing "Kho hàng" button → tabs **Kho** (parcels, suppliers, shelf with the
  nearest use-by), **Sổ lô** (fridge log, batches, pull buttons), **Khách quen** (refill cards with
  call / hand buttons, trust hearts, recent pickups). The counter view shows today's care strip and
  marks lots that need a box pulled.
* Bookkeeping: the dock's third button is now **Tủ hồ sơ** (it used to reopen the same job view as
  "Chứng cứ"); the classic view links to it.
* Support: the dock's third button is **Theo dõi** (the board); the case view has the timers,
  history card, call panel and a link to the board.
* Everything is scoped under `.wh`, `.cb`, `.cs-call` in `desks.css`: tokens only, text ≥ 14px,
  taps ≥ 44px, one column on phones, two from a 620 px sheet.

## Saves and validation

* `validate_state` → `care_validate`: exact key sets and ranges for batches (valid lots only,
  unique ids), regulars, fridge rows, the 7-day log, client books (one open book per client, due =
  arrive + 3, known habits ⊆ the client's habits), people cards, trend, handover, and the extra
  fields of classic support cases (`ready_at, wait, sla_at, sla, upd, tone, promised, call…`, call
  rows `who/text/mode/tone/canonical`). Parcels: known supplier, `placed ≤ lo ≤ hi`, `at ≥ placed`.
* Old saves: parcels migrate in `migrate_state`; care data starts at the next opening (or the first
  action of a shift already open); support fields are added with `setdefault`.

## Tests

`tests/test_desk_care.py` (34): stock windows, depot price and next-morning arrival, supplier
validation, migration of beat-based parcels, helper and one-time arrival note; refills (call,
late, missed), blocked lots and pulls, recalls on schedule, fridge windows and fixes, risk from a
missed log, desk bulletin reminders, tampered lot books; client books (habit learning, grades,
late sender follow-up, deadline → lost, desk case active, input validation); support waits over
night, handover, update call, SLA breaches, call rules, overpromise, call context without the
answer, trend/history, tampered calls; the AI route with a fake provider (stored AI line +
canonical + purpose, invalid output and abuse guards, CSRF/validation, consent, budget, 409).
Pinned tests moved to the clock: `test_engine`, `test_pharmacy`, `test_operations`,
`test_mother_baby`.

## Not in this change

* The paper-desk renderer (`desk.js`) shows care reminders only through its bulletin; a richer
  in-desk card needs desk.js.
* English strings for the new copy (run `scripts/i18n_extract.py` when all waves are in).
* `handleAction('executeCS')`'s confirm text was reworded (it promised "hai nhịp").
