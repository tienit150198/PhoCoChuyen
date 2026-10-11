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

## 4. Cần chủ game chốt trước khi sửa

1. **Mốc 50 ván ô ăn quan** tính thế nào: 50 ván thắng trong một ngày, cộng dồn cả mùa chợ đen, hay thắng liên tiếp?
   Hiện mỗi ngày chỉ được 30 ván với Ông Hai, nên mốc "50 trong một ngày" sẽ không bao giờ tới. Nếu bỏ trần 30
   ván/ngày theo luật 1 thì mốc này mới có tác dụng.
2. **Dưới 50 ván** thì sao: giữ cách hiện tại (mỗi ván thắng đều bị phạt nhẹ và vào tù) hay để thắng bình thường?
3. **"Phạt cực nặng"** là bao nhiêu (ví dụ 30–50% ví như luật 10/10, hay tịch thu toàn bộ tiền thắng ô ăn quan)?
   Lấy từ ví hay cả ngân hàng?
4. **Phạt chợ đen** có được bỏ trần 2.000 xu của `loss_limits` không (chỉ cho chợ đen; trần nhỏ vẫn giữ cho nghề và
   đời thường)? Tính theo % ví hay % tiền lời hôm nay? Khi bị bắt có tịch thu lại tiền cược không?
5. **Mức 40%** chỉ xét tiền cược một ván (như hiện tại), hay xét cả tiền lời hôm nay (ví dụ đã lời trên 300k thì về 40%)?
6. **Trần 1 triệu/ván (`STAKE_MAX`)** và **30 ván Ông Hai/ngày (`HAI_DAY`)** có bỏ không? Nếu bỏ `STAKE_MAX` thì cần
   tách dòng Sổ ví (validator giới hạn |amount| ≤ 10^7 mỗi dòng).
