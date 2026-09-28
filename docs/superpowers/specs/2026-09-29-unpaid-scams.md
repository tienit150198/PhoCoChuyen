# Bị quỵt tiền & cuộc gọi lừa đảo: new chuyện đời

Date: 2026-09-29 · Content only (`game/incident_content.py`), no engine change.

## Problem

Players rarely lose money to the two things every small business in the street actually worries about:
customers who never pay ("bị quỵt") and phone / online scams ("gọi điện lừa đảo"). A few exist already
(`scam_police` + `scam_caught`, `fake_fine_sms`, `fake_transfer`, `counterfeit`, `fake_supplier`,
`guest_skip`, `drunk_bill`, and the live happening `dine_dash`), but most careers meet at most one or two.

## Goal

A balanced set of new incidents, written with the existing DSL (`I()`, `O()`, `W()`, `F()`, `L()`, `R()`,
`follow=`, `voluntary=`, `hint=`, `review=`), where:

* each root has 2–3 choices; the careful one prevents or limits the loss, the careless one loses money;
* the lesson is visible in the outcome text ("Ngân hàng không bao giờ hỏi OTP qua điện thoại.");
* amounts stay in the game's range (tens of xu: the wallet starts at 60, a day's salary is 35–90);
* nothing fires before workplace day 5 (the shared phone scams are staggered from day 5 to day 9);
* vigilance is sometimes rewarded: trust, a warm line from cô Lụa, a small tip from the ward
  (`scam_ring_bust` follow-up, `security_reward`), a thank-you bonus at the office.

Careless choices a player "would not know are careless" hide their loss in a `luck` roll (the stake is not
shown on the button); money the player knowingly hands over is `voluntary` with a visible hint, as before.

## Money categories

| category | where | meaning | P&L label (suggested) |
|---|---|---|---|
| `scam_loss` (existing) | wallet / fund | money taken by a scammer | Bị lừa |
| `bad_debt` (**new**) | wallet / fund | goods or services given and never paid for: a tab, a runaway table, a refused COD parcel, a minibar | Bị quỵt / nợ khó đòi |
| `recovery` (existing) | fund | part of a debt paid back later | Thu hồi |
| `service` (existing) | fund | a late invoice finally paid | Tiền dịch vụ |
| `security_reward` (existing) | wallet | the ward's thank-you for reporting a scam number | Thưởng khu phố |
| `gift` (existing) | wallet | a thank-you bonus for stopping a fake-boss transfer | Quà tặng |

`bad_debt` needs no server change: the ledger validation only checks the category text length (≤ 60) and
incident lines only check ≤ 40. The client falls back to "Khác" (ledger, `public/js/operations-ui.js`
`categories`) and "Chuyện đời" (`public/js/v4/incidents.js` `CAT_NAMES`) until someone adds
`bad_debt:'Bị quỵt'` to both maps (out of scope here: those files are being edited in parallel).

A new incident category `no` (📒 "Chuyện tiền nợ") groups the unpaid stories, next to `lua` (📵 Cảnh giác
lừa đảo) for the scams. The label is neutral so the eyebrow does not give the ending away.

## New incidents

### Unpaid (cat `no`)

| id | careers | min_day | choices (careful → careless) | follow-ups |
|---|---|---|---|---|
| `tab_regular` Khách quen xin “ghi sổ” | grocery, pharmacy, mother_baby, repair, salon, pet_care, florist | 5 | ghi sổ có ký tên + hẹn ngày (−25 now, recoverable) · nói khéo không bán chịu (0) · **gật đầu cho qua** (−25, default) | `tab_due` (3 d) / `tab_gone` (4 d) |
| `tab_due` (chain) Tới hẹn trả sổ | — | — | nhận một nửa, hẹn trả nốt (+15) · đòi đủ ngay (luck: +30 or +15, trust −) · xóa nợ (trust +3) | — |
| `tab_gone` (chain) Khách ghi sổ biến mất | — | — | hỏi tổ dân phố (luck: +15) · bêu tên lên mạng (trust −4, review) · coi như bài học (default) | — |
| `atm_runaway` “Chờ em ra ATM” | restaurant, cafe_bakery, milk_tea | 5 | đưa mã QR cả bàn trả tại chỗ (0) · để một người ở lại chờ (luck: 0 or −20) · **tin lời** (−60, default) | — |
| `cod_bomb` Khách bùng hàng COD | delivery | 5 | chụp ảnh, hoàn hàng về shop theo quy trình (0) · gọi năn nỉ (luck: 0 or −10) · **để trong cốp tính sau** (−45, default) | — |
| `minibar_dawn` Khách trả phòng lúc tờ mờ sáng | homestay | 5 | trừ vào tiền cọc, gửi hóa đơn (0) · nhắn xin chuyển khoản (luck: 0 or −25) · **hoàn cọc đủ rồi tính sau** (luck: 0 or −25, default) | — |
| `class_fund` Quỹ lớp cứ hẹn mãi | teacher | 5 | nhắn riêng, gợi ý đóng dần / quỹ khuyến học (0, trust +3) · tự đóng thay (wallet −20, default) · nêu tên trong nhóm lớp (trust −4) | — |
| `late_invoice` Khách hàng chậm thanh toán | accounting, tax_payroll | 5 | đối chiếu công nợ + lịch trả (→ +45) · tạm dừng dịch vụ (luck: +45 or +20) · **thôi đợi** (−20, default) | `invoice_paid` (2 d) / `invoice_gone` (4 d) |
| `invoice_paid` (chain) Tiền phí quá hạn đã về | — | — | cảm ơn, xuất hóa đơn (+45) · giảm 10% giữ khách (+40) | — |
| `invoice_gone` (chain) Khách hàng ngừng hoạt động | — | — | gửi hồ sơ đòi nợ (luck +15) · ghi nợ khó đòi, sửa hợp đồng thu trước | — |

### Phone / online scams (cat `lua`)

| id | careers | min_day | choices (careful → careless) | follow-ups |
|---|---|---|---|---|
| `otp_parcel` “Bưu điện” xin mã OTP | everyone | 5 | cúp máy, báo số lạ (→ `scam_ring_bust`) · hỏi mã vận đơn (neutral, default) · **đọc mã** (luck: wallet −45 mostly) | `scam_ring_bust` |
| `bank_sms` Tin nhắn “ngân hàng khóa tài khoản” | everyone | 6 | mở app chính thức / gọi tổng đài · để tối xem (neutral, default) · **bấm link, nhập OTP** (luck: −50 mostly) | — |
| `fake_prize` “Trúng thưởng, nộp phí nhận quà” | everyone | 7 | hỏi tổng đài chính thức · chặn số (default) · nộp 30 xu phí (voluntary) | `prize_more` (1 d) |
| `prize_more` (chain) Lại đòi thêm “phí bảo hiểm” | — | — | dừng lại, trình báo · nộp thêm 40 xu | — |
| `wrong_transfer` “Chuyển nhầm, chuyển lại giúp” | everyone | 9 | nhờ ngân hàng hoàn về tài khoản gốc · tự chuyển lại tài khoản gốc (default) · **chuyển vào số người gọi đưa** | `loan_claim` (2 d) |
| `loan_claim` (chain) “Công ty tài chính” đòi nợ | — | — | trình báo, trả đúng gốc qua kênh chính thức (−40) · trả đủ cả lãi (−60, default) | — |
| `ceo_fraud` “Sếp” nhắn Zalo chuyển tiền gấp | corp_accounting, tax_payroll, group_accounting | 6 | gọi số sếp đã lưu (+15 thưởng) · đòi phiếu đề nghị hai chữ ký (default) · **chuyển ngay** (wallet −60, trust −5) | — |
| `power_cut` “Điện lực” dọa cắt điện | shops + homestay, farm, accounting | 7 | tra app điện lực, báo số lạ (→ `scam_ring_bust`) · hỏi nhà bên (default) · chuyển 35 xu (voluntary, fund) | `scam_ring_bust` |
| `scam_ring_bust` (chain) Đường dây lừa qua điện thoại bị triệt phá | — | — | nhận 15 xu cảm ơn · góp vào quỹ tuần tra (trust +4) | — |

## Frequency

No global knob changes (`rate()`, `DAILY_CAP` untouched). Every new root has `weight=1`; the stories of three
careers or fewer get the existing ×2 own-workplace bonus. The shared scams are staggered by `min_day` (5, 6, 7,
9) so a new player meets them one at a time, and the 12-incident "recent" filter keeps them from repeating.

Simulated over 30 workplace days × 300 seeds (about 12 chuyện đời per workplace in that time):

* a new story comes up every 8 days (teacher, accounting, tax_payroll: small pools) to 18 days (milk_tea,
  restaurant, cafe_bakery: large pools);
* `lua` + `no` together come up 3.6–5.8 times per 30 days (they were about 2–3), i.e. one money-trap every
  5–8 workplace days. Most of them cost nothing when handled carefully, so it is noticeable, not punishing.

Calm mode only draws `tone='mild'` stories; `ceo_fraud` and `loan_claim` are `tense`.

## Tests

`tests/test_incidents_scams.py`: the new ids exist with the right careers / min_day / category, each root has
a careful `good=True` option and a careless option that loses money (directly or in the losing luck branch)
with the right category, every choice of every new incident applies its money exactly (fund ledger + wallet),
each follow-up is scheduled and later fires through `incidents.after()`, and `roll_plan` never picks a new
story for an ineligible career or before its `min_day`. The existing generic tests (integrity, every choice's
ledger, hidden fields) cover the new content automatically.
