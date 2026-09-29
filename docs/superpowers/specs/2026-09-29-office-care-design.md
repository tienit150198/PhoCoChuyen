# Office care loop (sub-project 3) — the three office careers

Date: 2026-09-29 · Branch: care-wave1 · Careers: `corp_accounting` (Công ty CP Mây Tre Xanh),
`tax_payroll` (Dịch vụ Thuế & Tiền lương Minh Bạch), `group_accounting` (Sông Hồng Group).
Files: `game/careers/{corp_accounting,tax_payroll,group_accounting}.py`,
`public/js/careers/{office_kit,corp_accounting,tax_payroll,group_accounting}.js`, their stylesheets,
`tests/test_career_{corp_accounting,tax_payroll,group_accounting}.py`.

## Problem

An office day already has a clock, deadlines, the boss's trust and a luck of the day, but almost
nothing reaches past 17:30: a dossier left open is due at 10:00 tomorrow and that is all. The
finished careers (farm, pet care, delivery, restaurant…) each have something the player looks
after from one day to the next. In an office, "care" is not a pot or a pet — it is **relationships
and cycles that span days**.

## Goals

* Each office career gets **one work cycle that runs over the five-day month / quarter** with real
  due days: corp's month-end close plan, tax's filing calendar with late fees, group's reporting
  packs and the auditor's questions.
* All three share **four things that carry over**: the colleagues you help (and who cover you
  later), your energy ("sức bền", drained by overtime, recovered by a normal day), a mentor /
  promotion track fed by reliable days, and a **calendar strip** of the next five days in the top
  strip.
* Fair and recoverable: no penalty for declining a favour, one long night is fine, every late
  item has a cheap fix, nothing is hidden (the calendar shows every due day).
* Server-authoritative and deterministic: every new roll is `kit.rng(career, …, day)`; nothing
  reads player state inside `make_task`, no generator or `FIXED` field changes, so every existing
  (day, slot) still builds the same dossier.
* Old saves load (`setdefault` migration in `_data()`; `validate_data` range-checks everything),
  and all existing commands keep their payloads.

## Shared layer — "Đời sống văn phòng"

`office.py` is outside this change, so the shared helpers live in a clearly marked section of
`corp_accounting.py` (`care_*` functions, parameterised by a per-career `CARE` dict) and the two
other careers import them. State: `data.care` in each career.

### 1. Energy — "Sức bền" (0–100, start 80)

* At day close: a normal day **+15**, a day with overtime **−25** (min 5).
* ☕ `<p>_break` (once a day, 15 office minutes, not when full): **+6** (+10 from rank 1).
* Below 60 "Hơi mệt" (a warning). Below 35 "Kiệt sức": work takes **20 % longer** on the office
  clock and overtime is refused ("về nghỉ đi em").
* So one overtime (80 → 55) is free, two nights in a row (→ 30) cost a slow day, and a single
  normal day brings you back above the line (→ 45).

### 2. Colleagues — "Đồng nghiệp" (bond 0–5, favours owed)

Three or four named people per career (portraits from the career's cast; tax's junior Bình uses an
emoji). From day 2, on about three days in four, one of them asks for help, never the same person
two days running (a deterministic chain seeded by the day, cached like `office.mod_of`):
`<p>_help {mate, answer:'yes'|'no'}`.

* Yes: costs 15–25 office minutes, bond +1, the colleague owes you one favour (at most 1, or 2
  once bond ≥ 3), and the NPC relationship warms (`kit.remember`).
* No: nothing happens ("để em nhờ người khác") — never a penalty.
* `<p>_cover {mate, task}` calls a favour in: a timed dossier due today that is not late yet gets
  **+60 minutes** (once per dossier, stored as `task.cover`). Not on tax's payroll grid on a bank
  cut-off day (the bank does not wait).
* Group only: a subsidiary accountant with bond ≥ 3 never sends their reporting pack late.

### 3. Reliable days and the mentor track — "Lộ trình"

A day is **reliable** when at least one dossier was handed in, nothing was late, and the
career's own serious slips stayed at zero (corp: no wrongly approved voucher; tax: no risky payroll
error; group: at most one correction). The last seven days show as a strip.

| rank | needs | perk |
|---|---|---|
| 0 Thử việc | — | — |
| 1 Chính thức | 3 reliable days | coffee break +10 |
| 2 Vững tay (corp: giữ tủ chứng từ …) | 6 reliable days, trust ≥ 55 | +4 xu on reliable days |
| 3 Được đề cử (kế toán tổng hợp / trưởng nhóm) | 10 reliable days, trust ≥ 70 | +8 xu on reliable days |

Reliable days never go down. The mentor (Chị Hạnh / Chị Hồng / Chị Mai Anh) writes a note at each
rank. The client shows the career story arc next to the track (first audit, the fake-invoice /
two-payroll / inflated-revenue dilemma, the promotion) from `state.stories`; the track is the
nomination, the story beat is the decision, so neither gates the other.

### 4. Calendar strip — "Lịch 5 ngày"

`data.care.calendar`: today and the next four days, each with its date, the luck of the day when it
is not normal (the schedule is deterministic and already shown the morning it happens) and the
career's due items with a state: done / due today / late / to do.

## Per career

### Corp — month-end close plan ("Kế hoạch khóa sổ tháng")

The five-day month already has six milestones. Five of them now have a **due day**:

| item | due (phase) | ticked by finishing |
|---|---|---|
| 🧾 Chốt chứng từ & hóa đơn | day 2 | any desk tray or invoice/journal dossier |
| 💵 Kiểm quỹ & kho | day 3 | petty cash or stock count |
| 🏦 Đối chiếu ngân hàng | day 4 | bank reconciliation |
| 🪑 Khấu hao TSCĐ | day 4 | depreciation |
| 🔒 Khóa sổ & báo cáo | day 5 | trial balance or month close |

Every item's dossier is in the day's first two slots or one "＋ Nhận thêm việc" away, so each
deadline can be met. Only work from this month's dossiers counts. At the close of an item's due
day, an undone item costs 2 trust and a note. On the close day: all five on time → 12 xu
"thưởng khóa sổ đúng hạn" and +3 trust. `data.care.close = {month, done:{item: day}, missed:[…]}`.

### Tax — filing calendar with real due days and late fees ("Lịch nộp")

| filing | opens | due | minutes | needs |
|---|---|---|---|---|
| 🧾 Tờ khai thuế TNCN tháng trước (Xưởng Chỉ Vàng) | day 1 | day 2 | 25 | — |
| 🛡️ Hồ sơ BHXH tháng này | day 2 | day 3 | 20 | a payroll grid paid this month |
| 📑 Báo cáo sử dụng hóa đơn tháng trước (Quán Mộc Miên) | day 2 | day 4 | 30 | — |

`tp_declare {filing, confirm}` files it (office minutes). On time: +1 trust. From the close of the
due day, each day unfiled costs a **3 xu late fee** (capped by the wallet, "tiền chậm nộp Minh
Bạch chịu thay khách"); filing late stops the fees. On the last day of the month Chị Hồng files
whatever is left (−3 trust each). Day 5 shows 💸 payday. A plan created for an old save in the
middle of a month marks filings that are already due as handled (no retroactive fees).

### Group — reporting packs and audit questions ("Gói báo cáo quý", "Câu hỏi kiểm toán")

* Each of the four subsidiaries sends its quarter pack; the due day is day 2 of the quarter. The
  arrival day is seeded per quarter; one subsidiary (two from the third quarter) is late by one or
  two days. `ga_nudge {sub}` (10 min, once a day, from the due day): the pack arrives this
  afternoon if you get on with that accountant (bond ≥ 2), otherwise tomorrow morning.
* `ga_review {sub}` (15 min) checks an arrived pack. One pack a quarter has a mistake: the review
  sends it back and it returns corrected the next morning (review it again).
* From day 3 of the quarter, chị Thảo (audit) asks one question a day (two on an audit-visit
  day) about a subsidiary, due two days later. `ga_answer {query}` takes 10 minutes when that
  pack was reviewed (the working paper is ready), 35 otherwise. On time +1 trust; unanswered at
  the close of the due day → "thư quản lý", −3 trust.
* Quarter close: every reviewed pack +1 trust; all four → 10 xu; a pack that never came and was
  never chased −2 trust (a late pack you chased costs nothing).

## Data (all added with `setdefault`)

`data.care = {v, energy, rest, mates:{id:{bond, owes, helped}}, ask:{day, mate, i, state}|None,
reliable, streak, rank, days:[{day, ok, why}], eval}` plus corp `close`, tax `filings`, group
`packs` and `queries`. Tasks may carry `cover` (a mate id). Public view: `data.care` with
`energy`, `mates` (cards; asks only for today), `track`, `calendar`, and the career's plan.

## Commands (new; existing ones unchanged)

`ca_help`, `ca_cover`, `ca_break` · `tp_help`, `tp_cover`, `tp_break`, `tp_declare` ·
`ga_help`, `ga_cover`, `ga_break`, `ga_nudge`, `ga_review`, `ga_answer`. All are `no_tick` (they
move the office clock, not the patience turn) and need the shift open.

## UI (390 px first, office_kit)

* Status strip: "🔋 Sức bền 80" under the clock (with "· Hơi mệt / Kiệt sức" when it matters, and a
  warning line when exhausted), and under the strip the **calendar strip** — five day cells in a
  horizontal scroll-snap row (today highlighted), each with its date, luck-of-day emoji and short
  due items (✓ done · ⏰ due today · ⚠️ late · ○ to do) coloured by state.
* 📥 Hộp thư, under the dossiers and "＋ Nhận thêm việc": the career's **plan card** (a fold that opens
  by itself when something is due, late or can be done now: close-plan marks, filings with
  "📨 Nộp · 25 phút", packs with "📞 Gọi giục" / "🔎 Soát gói", audit questions with "✉️ Trả lời"),
  then **colleague cards** (portrait, role, bond hearts and a word — Mới quen … Như người nhà —, the
  favour owed, today's request as a speech bubble with "🤝 Giúp · 20 phút" / "Để hôm khác", and
  "🙏 Nhờ đỡ … +1 giờ" when a favour is owed and a dossier can be covered), then the day's messages
  (mentor notes included), then a fold "🧭 Lộ trình & sức bền" (rank ladder, next step, seven-day
  strip, perks, story arc, energy meter, coffee break). Folds remember what the player opened or
  closed (`ui.okFold`). Buttons are disabled or hidden while the shift is closed.
* The tab badge on 📥 also counts a colleague's request and the plan items waiting for you.
* Idle desk shows the same. The day-close summary gets a care card (energy change, reliable day,
  rank-up, close / filings / packs result).

## Non-goals

No change to `office.py`, the engine, generators or the English pack (new strings need
`scripts/i18n_extract.py`, run by the lead). No colleague ever gets angry at a refusal.

## Verification

* `tests/test_career_{corp_accounting,tax_payroll,group_accounting}.py` gain an `OfficeCareTests`
  class each (energy and overtime refusal, the slow day, coffee break, seeded asks, help / decline /
  cover, reliable days and ranks with pay, close plan ticks / misses / month bonus, filings on time /
  late fees / chị Hồng files / wallet cap / bank cut-off, packs seed / nudge / review / bond,
  audit questions and the management letter, quarter bonus, old-save migration, tampered saves, a
  multi-day play-through per career).
* `scripts/run_checks.py`, `node scripts/check_js.mjs`, `scripts/browser_v04.py --careers …`.
* A Playwright play-through of five days per career at 390×844 (help through the colleague card,
  cover a dossier, file / nudge / review / answer through the plan card, coffee break, day summary).
