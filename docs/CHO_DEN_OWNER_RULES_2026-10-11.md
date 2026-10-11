# Chợ đen: luật chủ game chốt và chỗ code đang lệch — 11/10/2026

Tài liệu này ghi lại luật chủ game nhắc lại chiều 11/10, sau khi xem vì sao top Bảng vàng `fair20261009xu` thắng
nhiều. Phần sau so sánh luật đó với code đang chạy: `origin/main` a84d1d32, production 2.0.3-20261011132357.
**Chưa sửa code.** Các điểm lệch dưới đây chờ chủ game quyết rồi mới làm.

## 1. Luật chủ game (11/10)

1. **Không có trần cho người chơi.** Chơi thoải mái: không giới hạn số ván, tiền thắng hay tiền chơi mỗi ngày.
   Giới hạn duy nhất là tiền trong ví.
2. **Ô ăn quan:** ai thắng nhiều (hơn 50 ván) thì bị **phạt cực nặng**, và hiện dòng
   **"phát hiện dùng thiết bị hỗ trợ"**.
3. **Bị công an bắt ở chợ đen thì phạt theo %:** thắng nhiều thì phạt nhiều, thắng ít thì phạt ít.
4. **Chơi tiền lớn thì khó ăn hơn:** từ 300k trở lên, tỷ lệ thắng là 40%.

## 2. Code hiện tại so với luật

| Luật | Code đang chạy | Khớp? |
|---|---|---|
| 1. Không trần số ván/tiền | `ROUNDS_DAY = 400` chỉ là bộ đếm cho validator cũ, không chặn (`fair.py` dòng 1153). Không có trần tiền thắng/chơi trong ngày. | ✅ |
| 1. Không trần | `STAKE_MAX = 10**6`: một ván bầu cua, chiếu trong hoặc đua chó tối đa 1.000.000 xu. Ván lớn hơn bị từ chối với câu "Ván lớn cỡ này nhà cái không nhận đâu". Code coi đây là giới hạn an toàn cho dòng Sổ ví. | ⚠️ trần mỗi ván |
| 1. Không trần | `fair_hai.HAI_DAY = 30`: mỗi ngày tối đa 30 ván với Ông Hai. Ván thứ 31 bị từ chối với câu "Ông Hai mệt rồi". | ❌ đây là trần |
| 2. Ô ăn quan thắng hơn 50 ván thì phạt cực nặng | **Mọi** ván thắng Ông Hai (mức `kho`) đều bị phạt ngay (`fair._hai_device`), không có mốc 50 ván. Tiền phạt danh nghĩa là 30–50% ví (`FINE_LO`, `FINE_HI`), nhưng từ 2.0.3 bị `loss_limits.bounded_loss` ép còn **tối đa 2% ví và tối đa 2.000 xu**. Người chơi vẫn giữ tiền thưởng 10.000 xu và bị tạm giữ 3 ngày. | ❌ không có mốc 50; mức phạt không nặng |
| 2. Dòng thông báo | "Thắng Ông Hai, +10.000 xu. 🚨 Nhưng công an phát hiện dùng thiết bị thứ ba: nộp phạt X xu. Bạn bị tạm giữ 3 ngày." Sổ ví ghi "🚨 Công an phạt: dùng thiết bị hỗ trợ khi chơi với Ông Hai". | ⚠️ gần đúng, chữ là "thiết bị thứ ba" |
| 3. Phạt % theo thắng nhiều/ít | Trước 2.0.3: mất tiền cược của ván và phạt 30% ví còn lại. **Từ 2.0.3 (11/10 13:23, commit `45c94be5` "gentle losses")**: ván bị hủy, người chơi giữ lại tiền cược, phạt tối đa 2% ví và tối đa 2.000 xu. Bản 2.0.3 vốn nhắm vào chuyện người chơi bị phạt hoặc trộm mất sạch tiền ở nghề và đời thường, nhưng đã áp luôn cho chợ đen. Ra tù: bạn bè bảo lãnh 30.000 xu. | ❌ |
| 4. Từ 300k thì 40% | Trong "Hai ngày vàng" (`fair_golden_days.py`, 11/10 10:39 → 13/10 10:39), xóc đĩa, lô tô và vé cào thắng 70%. Mức 40% chỉ áp khi **tiền cược của một ván** từ 300.000 xu, không xét ví hay tiền lời trong ngày. Cược 299.999 xu mỗi ván vẫn được 70%, tức lời trung bình khoảng +120.000 xu/ván và không có giới hạn số ván. | ❌ dễ lách |

Hệ quả của các điểm lệch 3 và 4: trong sự kiện, người chơi cược 299k mỗi ván, mỗi lần bị bắt chỉ mất tối đa 2.000 xu
và được bạn bảo lãnh 30k là ra ngay. Như vậy tiền lời gần như chỉ phụ thuộc vào số ván họ chơi.

## 3. Số liệu production 11/10 16:15

Đọc bằng giao dịch chỉ đọc. Danh sách là người có điểm Bảng vàng `fair20261009xu` trên 1.000.000.

| # | Người chơi | Điểm | Lời chợ đen hôm nay | Nguồn chính |
|---|---|---|---|---|
| 1 | Hiếu wibu | 10.969.286 | +10.979.186 | Xóc đĩa trong Hai ngày vàng; 40 lần bị bắt, tổng phạt 2,41 triệu (phần lớn trước 2.0.3) |
| 2 | Mãn kinh cô nương | 5.795.765 | 0 | Ô ăn quan: 658 ván thắng = 6.580.000 xu (10/10) |
| 3 | chíp | 5.299.538 | +5.359.914 | Xóc đĩa trong Hai ngày vàng; có dòng +1,08 triệu lúc 15:54 và +705k lúc 16:06 (sau hotfix 300k) |
| 4 | Liệt dương công tử | 4.615.049 | −126.023 | Ô ăn quan khoảng 4,2 triệu (10/10 11:29–11:56); bị phạt "thiết bị hỗ trợ" 99.695 xu theo luật 30–50% cũ |
| 5 | tieuthuki | 3.442.123 | +3.408.949 | Xóc đĩa trong Hai ngày vàng, vé cào +387k |
| 6 | anni | 3.106.921 | +3.108.061 | Xóc đĩa trong Hai ngày vàng; được Hiếu wibu bảo lãnh |
| 7 | Mun | 2.817.659 | +2.817.653 | Xóc đĩa trong Hai ngày vàng |
| 8 | Dino | 1.461.578 | +1.617.617 | Xóc đĩa trong Hai ngày vàng |

Ghi chú về số liệu:

- "Số ván hôm nay" trong save dừng ở 400 (bộ đếm), nên người hiện 400 có thể đã chơi nhiều hơn.
- Save không lưu giờ của từng ván, nên không tách chính xác được phần thắng trước và sau hotfix 13:12.
- Hai trường hợp ô ăn quan diễn ra trước luật "thắng Ông Hai là bị phạt" và trước trần 30 ván/ngày.

## 4. Quyết định của chủ game (11/10, chiều)

1. **Không giới hạn số ván** ở mọi trò: chơi thoải mái, trò nào cũng vậy.
2. **Ô ăn quan:** thắng **trên 50 ván** thì bị bắt vì "sử dụng thiết bị hỗ trợ" và **phạt 50% tổng tiền**, gồm ví và
   tài khoản ngân hàng.
3. **Bị công an bắt ở chợ đen:** phạt **30% tiền lời**. Tỷ lệ bị bắt **giảm thấp**.
4. **Cược một ván từ 300k trở lên** thì bị bắt nhiều.
5. **Tiền lời không giới hạn, tiền cược một ván không giới hạn** (được cược hơn 1 triệu). Cược càng nhiều thì tỷ lệ bị
   bắt **cực cao**, đặt sao cho không ai khai thác được.

Việc phải làm trong code để khớp các quyết định trên:

| Quyết định | Sửa ở đâu |
|---|---|
| 1 | Bỏ `fair_hai.HAI_DAY` (30 ván Ông Hai/ngày), `KN_DAY_CAP` (phóng dao: tiền lời tối đa 20.000 xu/ngày) và `RING_PAY_DAY` (ném vòng: tối đa 400 xu/ngày). Lưu ý `KN_DAY_CAP` được thêm 09/10 vì có script giải bàn phóng dao (xem mục 5, điểm 5). |
| 2 | Bỏ việc phạt từng ván thắng Ông Hai (`fair._hai_device`), thay bằng bộ đếm ván thắng. Khoản phạt này không đi qua `loss_limits` và được trừ cả tài khoản ngân hàng. |
| 3 | `fair_bm.arrest`: phạt = 30% tiền lời, không đi qua trần 2.000 xu của `loss_limits`. Hạ `BM_ARREST_P`. |
| 4, 5 | Bỏ `STAKE_MAX` (1.000.000) và đường cong tỷ lệ bị bắt mới theo tiền cược (`fair_bm.big_stake_pct`, `ARREST_CAP`). Sổ ví phải tách khoản lớn thành nhiều dòng (`ROW_MAX` 10^7 mỗi dòng); số lời ngày (`f.net`, giới hạn ±10^9, `NET_SAFE` 10^8) cần nâng giới hạn. Save có số lớn hơn sẽ bị bản cũ từ chối: sau bản này **không quay lui được**. |

## 5. Đề xuất bổ sung để không bị khai thác (chờ chủ game chốt)

1. **Hai ngày vàng vẫn là lỗ hổng chính.** Sự kiện chạy tới 13/10 10:39. Cược 299.999 xu được 70%, nên trung bình lời
   +40% tiền cược mỗi ván. Luật "từ 300k bị bắt nhiều" không chặn được, vì người chơi chỉ cần đặt dưới 300k. Muốn ván
   70% không có lời, tỷ lệ bị bắt ở mức cược đó phải trên khoảng 29% **và** bị bắt phải mất tiền cược. Điều này trái
   với "tỷ lệ bị bắt giảm thấp". Đề xuất chọn một:
   - Tỷ lệ 70% chỉ cho cược nhỏ (ví dụ dưới 50.000 xu); từ mức đó trở lên dùng tỷ lệ thường; hoặc
   - Hạ về tỷ lệ thường khi tiền lời chợ đen trong ngày vượt một mốc (ví dụ 300.000 xu), cược bao nhiêu cũng vậy; hoặc
   - Kết thúc sự kiện sớm.

   Vé cào trong sự kiện trả trung bình khoảng 232% giá vé. Khi bỏ giới hạn số ván và tiền cược, vé cào thành máy in
   tiền. Cần bỏ ưu đãi vé cào, hoặc giữ vé cào ở mức tối đa 1.000 xu/vé.
2. **Bị bắt phải có giá.** "30% tiền lời" cần định nghĩa rõ:
   - Lời **hôm nay** (`f.net`, về 0 lúc nửa đêm) hay lời **cả mùa** (`stats.won − stats.lost`)? Nếu tính hôm nay thì
     tiền thắng hôm qua an toàn tuyệt đối.
   - Đang lỗ thì 30% tiền lời là 0, nên bị bắt không mất gì. Đề xuất: **luôn tịch thu tiền cược của ván bị bắt**
     (như trước 2.0.3), cộng 30% tiền lời nếu đang lời.
   - Trừ từ đâu: nếu chỉ trừ ví thì người chơi chuyển tiền thắng sang ngân hàng để né. Đề xuất trừ ví trước, thiếu thì
     trừ tài khoản ngân hàng, giống luật ô ăn quan.
3. **Đường cong tỷ lệ bị bắt (đề xuất, không hiện cho người chơi):**

   | Tiền cược một ván | Tỷ lệ bị bắt |
   |---|---|
   | dưới 50.000 | 0%; 2% nếu lời hôm nay trên 300.000 |
   | 50.000 – 299.999 | 2% → 10% (tăng dần) |
   | 300.000 – 999.999 | 30% → 50% |
   | 1.000.000 – 9.999.999 | 50% → 80% |
   | từ 10.000.000 | 90% |

   Kèm tịch thu tiền cược khi bị bắt. Với tỷ lệ thắng thường (dưới 50%), mọi mức cược đều có kỳ vọng âm.
   Riêng tỷ lệ 70% của Hai ngày vàng vẫn có kỳ vọng dương ở mức 50.000 – 299.999, nên cần làm thêm điểm 1.
4. **Đếm 50 ván ô ăn quan thế nào.** Nếu đếm theo ngày, một bot thắng 50 ván mỗi ngày (500.000 xu) rồi dừng là an
   toàn mãi. Đề xuất:
   - Đếm **cộng dồn cả mùa** chợ đen, chỉ tính ván thắng Ông Hai (Bé Bi 50 xu/ván không tính).
   - Ván thắng thứ 51 thì bị bắt. Sau khi bị bắt thì đếm lại từ 0.
   - "Tổng tiền" gồm ví, tài khoản thanh toán **và tiết kiệm có kỳ hạn**. Nếu không, người chơi gửi tiết kiệm để né.
     Quỹ nghề, đầu tư và nhà thì có tính không?
   - Câu thông báo đổi "thiết bị thứ ba" thành "thiết bị hỗ trợ" cho đúng lời chủ game.
5. **Phóng dao.** Nếu bỏ trần 20.000 xu/ngày (`KN_DAY_CAP`) thì script giải bàn ngày 09/10 lại kiếm không giới hạn.
   `fair_watch` chỉ bắt được người ném quá sớm hoặc mở quá nhiều lượt liên tục. Đề xuất áp luật giống ô ăn quan: lời
   phóng dao vượt một mốc thì bị bắt vì "thiết bị hỗ trợ", phạt 50% tổng tiền.
6. **Bảo lãnh 30.000 xu làm án tù vô nghĩa.** Top 1 và anni bảo lãnh cho nhau. Đề xuất: với án chợ đen, tiền bảo lãnh
   = 30% tiền lời hôm nay của người bị bắt (tối thiểu 30.000), hoặc mỗi người chỉ được bảo lãnh một lần mỗi ngày.
7. **Chuyển tiền sang tài khoản khác.** Phạt theo tổng tiền có thể bị né bằng cách chuyển khoản sang nick phụ hoặc bạn
   bè trước. Chưa có cách chặn hết; ít nhất ghi log các lần chuyển lớn ngay sau khi thắng lớn để admin xem.
8. **Trao danh hiệu tuần thứ Hai 12/10 00:00.** `fair_board.settle` sẽ trao 👑 Vua trò chơi cho Top 1 và 🎪 cho Top
   2–10 theo bảng hiện tại. Bảng này gồm tiền thắng nhờ lỗ hổng Hai ngày vàng và hai trường hợp ô ăn quan nghi dùng
   máy giải. Cần quyết trước nửa đêm: vẫn trao, hoãn, hay loại các trường hợp này.
9. **Tiền đã thắng.** Có thu hồi hoặc phạt hồi tố không? Đề xuất không thu hồi phần thắng trong sự kiện (lỗi luật của
   game). Riêng hai trường hợp ô ăn quan (658 và khoảng 420 ván thắng) có thể áp luật mới một lần nếu chủ game muốn.
10. **Thời điểm deploy.** Đã hứa với người chơi sẽ deploy trong khung 04:00–05:00. Nếu chờ khung đó thì lỗ hổng Hai
    ngày vàng còn mở thêm khoảng 12 giờ. Chủ game quyết có hotfix sớm, không thông báo, như bản 2.0.2.1 hay không.
