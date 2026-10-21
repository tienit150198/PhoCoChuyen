# 💍 Đời sống vợ chồng: lễ cưới truyền thống, đi chơi thật, sống chung (góp ý #442, #444)

Chủ game 21/10: "lên hướng triển khai cho người ta nhé, có đi thật luôn nhé, có chụp ảnh này kia luôn, thuê máy bay du
thuyền gì đó". Người chơi hỏi: #442 nghi lễ cưới (rước dâu, lễ gia tiên) trước tiệc cả phố; #444 nhập vai cuộc sống sau
cưới (việc nhà, đi chơi, chăm con cùng nhau).

## Tóm tắt cho người chơi (6 dòng)

1. 🧺 Lễ rước dâu + lễ gia tiên: hai bạn cùng làm từng bước (sửa lễ vật, xin dâu, thắp hương, trao nhẫn, rước dâu về) với hai họ.
2. 🎤 Khách dự tiệc cưới nghe MC kể lại lễ rước dâu của hai bạn; tin vui chạy trên bảng tin nếu cả hai đồng ý.
3. ✈️ Đi chơi cùng nhau thật: chọn nơi (Đà Lạt, Hội An, Hạ Long, Phú Quốc… hay Seoul, Osaka, Lyon, Melbourne, đảo riêng).
4. 🛩️ Đi vé thường, thuê máy bay riêng hay du thuyền; nhà có sẵn máy bay, du thuyền thì chỉ tốn tiền xăng.
5. 📸 Mỗi ngày trên chuyến đi có hoạt động chung, chuyện bất ngờ và một tấm ảnh đôi vào album chung của hai bạn.
6. 🏠 Sống chung mỗi ngày: rủ nhau làm việc nhà, đi chợ, nấu cơm, chăm con: vui hơn, thương nhau hơn (không ra tiền).

## Các giai đoạn

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| 1 (2.5.2) | Lễ rước dâu + gia tiên tương tác, MC kể lại ở tiệc; chuyến đi chơi có ký quỹ, thuê / dùng máy bay, du thuyền; album ảnh chung; việc nhà cùng nhau | Làm trên `feat/wedding-life` |
| 2 | Chuyến đi cùng bạn bè (mời thêm 2–6 người như ra đảo), vé khứ hồi theo lịch thật, quà lưu niệm vào túi quà | Sau khi phase 1 chạy ổn |
| 3 | Tổ ấm: lịch việc nhà theo tuần, bữa cơm gia đình có món do nghề nấu ăn làm, con lớn đi học / đi chơi cùng bố mẹ | Chờ chủ game duyệt |
| 4 | Thuê người chơi (nghề phi công, tiếp viên, hướng dẫn viên, nhiếp ảnh) phục vụ chuyến đi qua Phố dịch vụ | Cần nghề hướng dẫn viên |

## Phase 1 chi tiết

### A. 🧺 Lễ rước dâu + lễ gia tiên (`game/wedding_life.py`, `wl_rites`)

* Ai làm: đôi đã đính hôn có kế hoạch cưới đã chốt, hoặc vợ chồng đã cưới (kể cả cưới từ trước). Mỗi đám cưới một lễ.
  Không làm được khi tiệc cưới đang diễn ra (phòng tiệc đang mở).
* Một người bắt đầu (là "họ đi rước"), người kia là "họ đón". Sáu bước xen kẽ, mỗi bước một người chọn trong 3 cách;
  hai họ là NPC (ông chủ hôn, bà nội, mẹ, cô dì) nói theo lựa chọn. Không có đáp án "thua": mỗi bước cho 1–2 điểm lễ.
  1. Sửa soạn mâm quả (trầu cau, rượu, chè, bánh phu thê, xôi gấc, lợn quay) · 2. Xin phép rước dâu · 3. Nhà gái nhận lễ
  · 4. Thắp hương bàn thờ gia tiên · 5. Trao quà, cha mẹ dặn dò · 6. Đón dâu về nhà.
* Giá: miễn phí nếu kế hoạch cưới đã có lễ gia tiên (đã trả trong kế hoạch). Nếu chưa có: phí lễ gia tiên của bảng giá
  cưới. Mâm quả: lấy số mâm ăn hỏi đã đặt; chưa đặt thì chọn 5 / 7 / 9 mâm theo giá ăn hỏi. Người bắt đầu trả (ví,
  tài khoản hoặc thẻ như mọi món mua trong mục Hôn nhân), không bao giờ từ quỹ chung.
* Huỷ trước khi xong (một trong hai), hết hạn 3 ngày, ly hôn: hoàn đúng số đã trả, một lần (mã hiệu cố định).
* Xong lễ: +điểm hạnh phúc (đi qua giới hạn ngày của điểm hạnh phúc), một dòng nhật ký, một tấm ảnh "Lễ gia tiên" vào album
  chung. Tin trên bảng tin chỉ khi cả hai đã đồng ý báo tin lúc cưới. Tiệc cưới: MC kể lại lễ (live/wedding.py đọc
  `wl_rites`), bản cũ không đọc thì tiệc vẫn như trước.

### B. ✈️ Đi chơi cùng nhau (`wl_trips`, `wl_photos`)

* Chỉ vợ chồng đã cưới. Nơi đến: 6 điểm trong nước, 4 điểm nước ngoài (cùng danh sách Du học / Làm việc ở nước ngoài),
  đảo riêng nếu một trong hai có đảo.
* Phương tiện: 🎫 vé thường; 🛩️ thuê máy bay riêng; 🛥️ thuê du thuyền (chỉ nơi có biển); 🔑 máy bay / du thuyền nhà mình
  (một trong hai sở hữu, kể cả xe đấu giá có số đăng ký): chỉ tốn tiền xăng = 1/10 giá thuê.
* Ai trả: 🏦 quỹ chung, ✂️ chia đôi, hoặc 🙋 mình bao. Phần của người rủ bị giữ ngay (ký quỹ); người kia bấm "Đi thôi"
  thì phần của họ (nếu chia đôi) được trừ, chuyến đi bắt đầu, tiền chi hẳn (đốt khỏi nền kinh tế). Từ chối / huỷ / hết
  hạn 48 giờ / ly hôn trước khi đi: hoàn đúng nơi đã trả (quỹ về quỹ, ví về ví), một lần.
* Trên chuyến đi: 3 ngày (trong nước) hoặc 4 ngày (nước ngoài). Mỗi ngày một người chọn hoạt động (lần lượt), có một
  chuyện bất ngờ (mưa, lạc đường, gặp người địa phương…) và một ảnh đôi do hệ thống ảnh của game vẽ (dáng, phông, đèn
  như 📸 Chụp ảnh; chỉ lưu dữ liệu vẽ, không lưu ảnh). Về nhà: +điểm hạnh phúc, +tinh thần cho cả hai, dòng nhật ký.
* Một chuyến mỗi ngày (giờ Việt Nam) mỗi đôi, một chuyến mở một lúc; chuyến đã đi bỏ dở quá 72 giờ thì tự về.

### C. 🏠 Sống chung mỗi ngày (`wl_chores`)

* Việc nhà, đi chợ, nấu cơm, chăm con (khi có con chung). Một người rủ và chọn phần việc của mình, người kia nhận phần còn
  lại; cả hai cùng làm thì mới tính. Mỗi việc một lần mỗi ngày.
* Hiệu quả nhỏ: +điểm hạnh phúc (chung giới hạn ngày với các tương tác), +1 tinh thần mỗi người, dòng nhật ký; chăm con
  thêm vui cho bé. Không tốn tiền, không ra tiền.

## Dữ liệu

* PostgreSQL `SCHEMA_VERSION 83`: bảng mới `wl_rites`, `wl_trips`, `wl_photos`, `wl_chores` và chỉ mục; không FK, không
  backfill, không khóa save mới. Tiền đi qua đường có sẵn: `marriage_effects` (ví, mã cố định), `joint_ledger` (quỹ, mã
  UNIQUE), tinh thần là `journey.life.spirit` có sẵn.
* Rollback về 2.5.1: bản cũ không đọc các bảng mới; tiền đã giữ ở chuyến đi chưa đi nằm trong bảng `wl_trips`, khi bản mới
  chạy lại sẽ hoàn (hết hạn 48 giờ). Hoàn tiền đang chờ trong `marriage_effects` thì bản cũ vẫn trả (cùng loại 'wallet').

## Chống lạm dụng

* Không có dòng tiền từ người này sang người khác: mọi khoản đều là chi tiêu (đốt) hoặc hoàn lại đúng người / đúng quỹ đã trả.
* Mỗi yêu cầu có mã `rid`: bấm lại, mạng chập chờn không bao giờ trừ hai lần; hoàn tiền có mã cố định, chỉ một lần.
* Trạng thái đổi bằng UPDATE có điều kiện (proposed → on, on → done…), hai người bấm cùng lúc chỉ một người thành công.
* Không thưởng xu. Điểm hạnh phúc có trần 100; tinh thần có trần 100.
* Chặn nhau (chặn trong Hôn nhân hoặc chặn chat) thì không rủ nhau được; người đang ở trại tạm giữ không đi chơi được.
* Album chỉ hai vợ chồng xem; khách ở tiệc chỉ nghe MC kể (tên hiển thị, không lộ mã tài khoản).
