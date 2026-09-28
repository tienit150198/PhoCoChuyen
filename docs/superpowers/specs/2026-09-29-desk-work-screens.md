# Desk work screens: pharmacy, bookkeeping, support

Date: 2026-09-29 · Sub-project 2 of 4 (scenes → **work screens** → career stories → care mechanics)

## Problem

The classic tasks of three careers still used the old generic views in `public/js/app.js`:

- **pharmacy** ("Quầy Bình An"): read a slip, read lot labels, pick the right code, lot and quantity, do the 2-step check, then hand over or refer.
- **accounting** ("Góc Sổ Xinh"): match source documents to bank transactions.
- **customer_care** ("Trạm Lắng Nghe"): verify identity, open evidence, propose a solution, execute it, confirm the result and close the case.

All three looked like a shop: the guest ribbon, a product grid and small 11–13px text. The two-column boards also did not fit a phone.

## Scope

This change covers only rendering and client-side UI state. The game logic, the commands and the `data-action` names are unchanged: `selectDoc`, `selectTx`, `clearSelection`, `match`, `completeAC`, `executeCS`, `closeCS`, `verifyPH`, `deliverPH`, `referPH`, the `data-phcheck` checkboxes and `#ph-filter`. The server checks every step again.

The paperwork desk cases (`t.desk`, rendered by `desk.js`) are separate and not touched here. In a day these three careers deal one or two classic tasks; this screen is for those tasks.

## Shared pieces (app.js, next to the three views)

- `dwWho(t, sub)` draws the header: portrait, name, one context line, a patience meter (`role="meter"`) and a 44px chat button, then the customer's opening line. `desks.css` hides the old `.guest-ribbon` whenever a `.career-job.dw` screen is shown, the same way `desk.css` does it.
- `dwBar(text, buttons)` is a sticky bar that sits above the sheet footer. It holds one status line and at most one main action. It uses the `--dw-foot` offset: the footer height plus an 8px gap (65px on phone and desktop, 69px on tablet, plus the bottom safe area on phone).
- `dwState(label, tone)` is a 14px state chip.
- `reqList` and `fold` come from `ui-kit.js`.

Everything is scoped under `.career-job.dw` (`.dw-ph`, `.dw-ac`, `.dw-cs`) and uses theme tokens only. Text is at least 14px (`.933rem`) and tap targets are at least 44px. Columns come from `@container sheet`, never from `@media`.

## Pharmacy: dispensing view

The phone order is: slip → shelf of lots → tray and check → refer. From a sheet width of 760px, the lots sit on the left and the slip, tray and refer box sit on the right.

- **Slip.** A dashed card with Mã hộp, Số lượng and Ghi chú.
  - Unknown slip: a "Hỏi rõ phiếu" button (the same `ask` command the ribbon used).
  - Referral slip: only the slip and "Chuyển cô Thu". There is nothing to pick.
- **Lots.** They are grouped by code. The group whose code is on the slip is tagged "Mã trên phiếu". Each lot is one row with a state chip:
  - *Chưa đọc*: the state is hidden until the label is read. The only action is **Đọc nhãn**.
  - *Hợp lệ*: shows the stock and **Lấy 1**.
  - *Tạm giữ* (amber) or *Hết hiệu lực* (red): no action.

  The `#ph-filter` select still filters by code and defaults to the slip's code.
- **Tray and 2-step check.** The tray lines have a − button (`basket_remove`) and an x/qty counter.
  - Step 1 is a checklist of three `data-phcheck` boxes. Each box shows the facts next to each other ("Phiếu P-01 · khay P-01"), so the player compares them instead of guessing. **Kiểm khay** becomes the primary button once the tray count matches the slip.
  - Step 2: **Bàn giao phiếu** stays disabled until the server marks the tray `checked`.
- **Refer.** "Chuyển cô Thu" sits in its own dashed box below the tray, apart from the dispensing flow.
- **Phone bar.** The pinned slip summary, "Phiếu P-01 × 1 · Khay 0/1 · lấy thêm", plus **Bàn giao** once the tray is checked. The sheet head is sticky and its height changes, so the reminder sits at the bottom instead of the top.

## Accounting: reconciliation board

- **Tabs on phone.** "📂 Chứng từ" and "🔗 Giao dịch" use the existing `jobTab` action (`ui.jobTab = acDocs | acTx`). Each tab shows "còn N" or "đã chọn N". From a sheet width of 680px, the tabs disappear and the two columns show side by side.
- **Compact card.**
  - Row 1: a 44px select box, then code · amount · state.
    - Document states: Chưa đọc gốc, Đã đọc, Lệch gốc, Thiếu nguồn, Đã ghép, Đã loại trùng.
    - A transaction shows "Đã ghép" once it is in a group.
  - Row 2: the reference (HD-…) as a fold, next to the one action: Mở gốc, Sửa theo gốc or Đánh dấu trùng. The source text and the original amount are inside the fold.
  - Every document always has exactly one fold. The sheet restores `<details>` open state by index, so this keeps the index stable.
  - Transactions show their references and note openly, because they are the matching key.
- **Sticky selection bar.**
  - Nothing selected: a hint.
  - Something selected: the two sums "Chứng từ · n" and "Giao dịch · n" with = (green) or ≠ (red), plus ✕ (clear).
  - The main button depends on the selection:
    - both sides picked: **Ghép nhóm**;
    - only one side picked, on phone: "Chọn giao dịch →" / "← Chọn chứng từ" (switches the tab);
    - only one side picked, wide screen: a disabled Ghép nhóm.
  - Everything matched: **Bàn giao**.
- **Missing source.** An amber alert at the top offers "Xin nguồn bổ sung" first, then "Nhận phản hồi" (advance).
- **Handover.** The matched groups have a **Tháo** button. A `reqList` shows the three conditions: bản gốc đã mở, chứng từ đã ghép/loại, giao dịch đã có nguồn. **Kiểm & bàn giao hồ sơ** comes after it.

## Customer care: support desk

- **Case header.** The customer, the channel and the order value once identity is verified. The channel (💬 Tin nhắn / 📞 Gọi điện / ✉️ Thư điện tử) is picked from the task id. It is flavour only and has no rule attached. The patience meter works as the SLA.
- **Step tracker.** Xác minh → Chứng cứ → Phương án → Thực hiện → Kiểm kết quả → Đóng vụ. Done steps show a green check. The current step is filled with the accent colour and marked `aria-current="step"`. Below 600px, the labels are visually hidden and one line says "Bước n/6 · …".
- **"Việc bây giờ" card.** It always holds exactly one primary action:
  - `cs_identity`;
  - open the next unread evidence;
  - the solution choices, as five buttons with a short line each;
  - "Gửi việc cho đầu mối" (`executeCS`);
  - "Xem phản hồi phối hợp" (advance);
  - "Kiểm kết quả" (`cs_confirm`);
  - "Hoàn tất & đóng vụ" (`closeCS`);
  - a handover in progress: "Nhận phản hồi bàn giao".

  While a proposal is still open, a compact "Đổi phương án?" list stays visible.
- **Evidence.** A checklist of cards with a round ✓ mark, the text once opened and "Mở" for the rest. The counter shows n/3.
- **Other pieces.** A dashed box offers "Bàn giao cùng chị Mai", with the same conditions as before. The refund note, the workbench notice and a folded "Nhật ký vụ" sit at the end. From a sheet width of 760px, the work sits on the left and the evidence on the right.

## Verification

- `node scripts/check_js.mjs`
- `python scripts/run_checks.py`
- The browser sweep on the three careers, `scripts/browser_v04.py --careers accounting,customer_care,pharmacy`, must report 0 problems.
- One task per career was played through the UI at 390px (bien), 360px (dem, the dark theme), 820px (keo) and 1440px (kem). The results matched `browser_smoke.py`: pharmacy 360 xu, accounting 390, support 385. A crafted save covered the referral slip, the missing source and the handover.
- A check during play found no text under 14px and no tap target under 44px inside `.dw`.

## Follow-ups

- The English pack has no entries yet for the new Vietnamese strings. `scripts/i18n_extract.py` should run once all the work screens are in.
