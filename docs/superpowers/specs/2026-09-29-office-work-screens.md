# Office work screens: a desk, not a shop

Date: 2026-09-29 · Sub-project 2 of 4 (scenes → **work screens** → career stories → care mechanics)

## Problem

The three office careers — `corp_accounting` (Công ty CP Mây Tre Xanh), `tax_payroll` (Dịch vụ Thuế & Tiền lương Minh Bạch) and `group_accounting` (Sông Hồng Group) — drew their job sheet as one long stack of generic cards: an office bar, the boss's quote, a wall of rule cards, the queue, the paper, the binder, the ledger. On a phone the paper you had to judge started a full screen below the top, and the stamp buttons were another screen further down. It read like a shop catalogue, not like sitting at an office desk.

## Goal

The job sheet feels like an office computer: a status strip, folder tabs, an email-like inbox, one document at a time, and the decision always one tap away. **Game logic and commands are unchanged** — only rendering and client-side tab state.

## Design

### Shared frame: `public/js/careers/office_kit.js` + `public/css/careers/office_kit.css`

Each career stylesheet imports the kit (`@import url('office_kit.css')`, like `food_kit.css`). The root is `.career-job.ok.<prefix>` (`ca`, `tp`, `ga`).

| Piece | What it shows | Data |
|---|---|---|
| Status strip (`statusStrip`) | 🕗 clock + "nghỉ trưa / tan sở", 👩‍💼 boss trust label + meter, ⏰ deadline chip, luck-of-the-day chip; overtime / lock alert under it | `room.data.office`, `today.mod`, `task.due` |
| Folder tabs (`desk`) | 📥 Hộp thư · 📂 Hồ sơ · 📋 Quy định (· 📒 Sổ sách for dossiers with a ledger). Badges: unread dossiers/claims, new rules | client state `ui.okTab[taskId:known]` |
| 📥 Hộp thư (`inboxPane`, `taskMails`, `dayMails`) | One email per open dossier (sender portrait, role, deadline, subject, preview). The dossier on the desk is expanded with the full request, 🎯 brief and chips; the others open with a tap (existing `job` action). Then messages of the day: new rules (tap → 📋 tab), the day's luck, fines and late notes from the office log, and (tax) payroll claims with their answer buttons | `room.tasks`, `office.notes`, `today.rules`, `claims` |
| 📂 Hồ sơ | The work itself, one document at a time (per career below) | — |
| 📋 Quy định (`rulesList`) | Today's rule cards, new ones first and marked MỚI, plus the career's reference books in folds | `today.rules`, `cc.rules`, binder docs |
| Sticky bar (`bar`) | The next step in words + the main action. From another tab on a phone it becomes "📂 Về hồ sơ". "Nhận …" works from any tab | — |
| Idle (`idleDesk`) | Strip, the last recap, the inbox and today's rules | — |

Tab switching (`switchTab`) is DOM-only — no re-render — so typed numbers and the voucher's live totals survive. `keepBarAboveFooter` (from `tick`) keeps the bar above the sheet's sticky footer.

### Layout

- **Phone (sheet < 720px):** one tab at a time. Default tab: 📥 while the dossier is unopened, 📂 once it is received.
- **Wide (≥ 720px, container query on `sheet`):** two columns — the left column shows 📥 or 📋 / 📒 (switchable), the right column always shows 📂. The 📂 tab button is hidden there.
- Text ≥ 14px (`.933rem`), inputs 16px, tap targets ≥ 44px (inputs 48px). Theme tokens only; `--career` is used only for the strip's top stripe.

### Per career — what 📂 Hồ sơ holds and what the bar does

| Career · task | 📂 Hồ sơ | Sticky bar |
|---|---|---|
| corp · khay chứng từ (`desk`) | Tray chips (Bộ 1…n with result marks), the sender's sticky note, the paper with tappable zones (khoanh), hint, verdict after stamping | The three rubber stamps DUYỆT · TRÌNH SẾP · TRẢ LẠI → "Bộ tiếp theo ›" → "📤 Chốt khay" (confirm) |
| corp · hồ sơ nhiều bước | Current step card (Bước i/n, prompt, widget, hint), last-step feedback, done steps folded; then the dossier's papers as folder chips, one open at a time | The step's confirm (Xác nhận / Chốt thứ tự / Ghi bút toán…); choices answer on tap; handover → "📤 Nộp hồ sơ" |
| tax · bảng lương nháp (`grid`) | People chips, one payslip line printed on paper with tappable cells, verdict; the source papers (hồ sơ gốc) one at a time | "✓ Xong dòng" → "Người tiếp theo ›" → "💸 Chuyển lương" (confirm) |
| tax · tờ khai | Worksheet (current step first), then the client's papers, then the desk calculator | "✔ Kiểm tra" → "📤 Nộp / bàn giao" (confirm) |
| group · đối chiếu nội bộ (`match`) | Gap meter, FX card when rates move, the two ledgers side by side, evidence fold; waiting card while the pack is late | Selection actions: 🔗 Ghép / cause chips / reason chips / 💡 Gợi ý / ✕ Bỏ chọn → "✂️ Loại trừ" (confirm); "📞 Gọi giục" while waiting |
| group · hồ sơ hợp nhất | As corp's dossier | As corp's dossier |

📋 Quy định also holds corp's 📚 Sổ tra cứu (binder), tax's 📘 Sổ tay quy định and group's FX board. 📒 Sổ sách holds corp's period milestones, trial balance and journal, and group's quarter milestones, group chart and consolidation journal.

## Unchanged

Every command (`ask`, `ca_*`, `tp_*`, `ga_*`, `more_work`, `task_select` via the `job` action), every payload, `summary()`, drafts/sync, validation toasts and server files. Only the three career modules, their stylesheets and the new kit changed.

## Verification

- `node scripts/check_js.mjs`; `python -m unittest tests.test_career_corp_accounting tests.test_career_tax_payroll tests.test_career_group_accounting`.
- `scripts/browser_v04.py --careers corp_accounting,tax_payroll,group_accounting`.
- A Playwright playthrough (phone 390×844 light + dark, tablet 820, desktop 1440) that plays a full task of every variant through the UI: stamping and closing a tray, flagging and paying a payroll grid, pairing/tagging and eliminating a board, and answering choice, multi, number, match, fields and entry steps through the widgets and the sticky bar, opening the next dossier from the inbox.

## Follow-ups

- New Vietnamese strings need the English pack (`scripts/i18n_extract.py`, not run here).
