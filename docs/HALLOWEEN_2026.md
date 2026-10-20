# 🎃 Lễ hội Ma Phố — Halloween 2026 (kế hoạch cho chủ game)

Chủ game 20/10: "tính toán luôn cả halloween … chạy trước 5 ngày". Nhánh `feat/halloween-2026` (từ `careers-integ`), dự kiến lên bản ~24/10, **tự mở 0:00 ngày 26/10 giờ Việt Nam** và tự khép 23:59:59 ngày 31/10. Thêm **một ngày đổi kẹo** (01/11) để ai còn kẹo đổi quà. Trước 26/10 0:00 không có gì hiện ra cả (máy chủ quyết định theo giờ máy chủ, không theo giờ điện thoại).

Code: `game/halloween.py` (luật + số), `game/halloween_content.py` (chữ: ngày, câu đố, câu cho kẹo / ghẹo, quầy đổi), `public/js/v4/halloween*.js`, `public/css/halloween.css`, quản trị `public/js/admin/halloween.js`.

## Người chơi thấy gì

- **Thẻ khai hội ở giữa màn hình** (mỗi ngày một lần trên một máy, thêm một lần khi Đêm hội hóa trang bắt đầu): chủ đề hôm nay + nút "🍬 Nhận N kẹo · vào lễ hội" (điểm danh luôn rồi mở lễ hội). Không hiện ngày đầu đời của người mới, không hiện cho khách chưa có tài khoản, không chen ngang quà / Có gì mới (xếp sau Thiệp 20/10 trong break-gate).
- **Dòng tin chạy chữ** mỗi ngày: "🎃 Lễ hội Ma Phố · <chủ đề>: … Khu phố → 🎃 Lễ hội Ma Phố." và một dòng riêng lúc 19:00 ngày 31/10.
- **Lối vào**: menu (Lễ hội Ma Phố 🎃, có chấm khi đang mở) và Tiện ích của phố 2.5D (nhóm Cộng đồng). Ngày 01/11 đổi tên thành "Đổi kẹo Halloween 🎃".
- **Phố 2.5D trang trí**: lớp phủ chiều tà, trăng khuyết, dây đèn bí ngô, thỉnh thoảng đàn dơi bay ngang; đêm 31/10 tối hơn và có con ma nhỏ. Chỉ là lớp trang trí (không chặn chạm, tắt chuyển động khi máy bật giảm chuyển động, ẩn khi vào trong nơi làm việc).
- **Bảng lễ hội** 4 thẻ: 🎃 Hôm nay · 🚪 Gõ cửa · 🎁 Đổi kẹo · 🏆 Bảng kẹo.

### Từng ngày

| Ngày | Chủ đề | Thêm gì |
|---|---|---|
| T2 26/10 | 🏮 Phố treo đèn bí ngô (khai hội) | Điểm danh +5 kẹo (15 thay vì 10) |
| T3 27/10 | 🐈‍⬛ Đêm mèo đen | Mỗi quả bí ngô tìm được +1 (6) |
| T4 28/10 | 👻 Ngõ ma lém lỉnh | Chủ nhà được +1 mỗi khách gõ (3) |
| T5 29/10 | 🕸️ Hẻm mạng nhện | Mỗi quả bí ngô +1 (6) |
| T6 30/10 | 🧙 Chợ phù thủy | Gõ cửa được cho kẹo +1 (5) |
| T7 31/10 | 🎭 Đêm hội hóa trang | Từ 19:00 tới nửa đêm: mọi viên kẹo ×2 + 🎃 Bí ngô khổng lồ (30 kẹo, một lần) |
| CN 01/11 | (ngày đổi kẹo) | Không kiếm thêm kẹo; quầy đổi + bảng vẫn mở tới hết ngày |

### Cách kiếm kẹo (mỗi ngày)

1. **✅ Điểm danh**: 10 kẹo.
2. **🎃 Săn bí ngô**: 5 quả nấp ở 5 nơi của phố (bốc ngẫu nhiên theo ngày, ai cũng như nhau). Mỗi quả một câu đố ("Meo meo, gâu gâu…") và 4 lựa chọn; **đoán một lần**, sai là lăn mất. Đúng: 5 kẹo. Ở phố 2.5D, đi tới đúng biển của nơi đó là nhặt được luôn (không cần đoán).
3. **🚪 Cho kẹo hay bị ghẹo?**: gõ cửa nhà người chơi khác (bạn bè + người đang chơi lễ hội, hoặc gõ theo tên đăng nhập; có nút "Gõ lại" cho người vừa gõ cửa nhà mình). Mỗi nhà một lần một ngày, **tối đa 10 nhà/ngày**. 70 % được cho kẹo (4), 30 % bị ghẹo (1 viên an ủi), câu chữ vui ngẫu nhiên. **Chủ nhà được 2 kẹo mỗi khách, tối đa 15 khách/ngày** (30 kẹo).
4. **🎭 Đêm 31/10**: mọi thứ trên ×2 + Bí ngô khổng lồ 30 kẹo.

### Quầy đổi kẹo (tới hết 01/11)

| Món | Giá | Ghi chú |
|---|---|---|
| 🎃 Danh hiệu "Thợ săn bí ngô" | 40 | trọn đời |
| 🍬 Vòng kẹo Halloween (tủ đồ thú cưng, bậc D) | 60 | món có sẵn trong Bộ Halloween của thú cưng |
| 🦇 Khung "dơi đêm" | 100 | trọn đời |
| 👻 Danh hiệu "Ma lém lỉnh" | 150 | trọn đời |
| 🟠 Màu tên "Bí ngô ma mị" (cam → tím) | 220 | trọn đời, đủ tương phản cả hai giao diện sáng / tối |
| 🕸️ Khung "mạng nhện" | 300 | trọn đời |
| 🧛 Danh hiệu "Bá tước Phố Mây" | 450 | khó nhất mùa |
| 💰 Túi kẹo đổi 20.000 xu | 50 | **tối đa 3 lần cả mùa** |

Mỗi món đổi một lần. Đồ đổi bằng kẹo không mua được bằng xu (hiện ở 🎨 Phong cách chỉ khi đã có). Đổi quà **không làm tụt hạng** (bảng tính kẹo đã kiếm).

### 🏆 Bảng kẹo

Xếp theo kẹo đã kiếm cả mùa (bằng nhau thì ai đạt trước đứng trên). 0:00 ngày 01/11 máy chủ tự trao (đúng một lần): **Top 1–3**: danh hiệu 👑 "Vua Kẹo Halloween 2026" + 🎃 "Khung bí ngô vàng"; **Top 4–10**: danh hiệu 🍬 "Top 10 săn kẹo 2026". Kèm một dòng tin chạy chữ chúc mừng.

## Số kinh tế và trần

- Ngày thường tối đa ≈ 10 + 25 + 40 + 30 = **105 kẹo** (thực tế người chơi không có khách ≈ 55–65). Cả mùa tối đa lý thuyết ≈ **800 kẹo**; mua hết đồ trang trí cần 1.320 kẹo → không ai lấy hết, phải chọn.
- **Xu**: chỉ qua túi 20.000 xu, **tối đa 60.000 xu / tài khoản cả mùa**. Không có xu nào khác (thưởng top là danh hiệu / khung, không phải xu).
- Kẹo không chuyển được cho người khác, không mua được bằng xu.

## Chống nick phụ / lạm dụng

- Chỉ tài khoản (khách chưa đăng ký chỉ thấy lời mời đăng nhập). Mọi phần thưởng ghi một lần theo khóa (điểm danh / quả bí ngô / lượt gõ / món đổi / túi xu) trong bảng `hw_log`, khóa advisory theo người, chủ nhà và mạng → bấm đúp, hai tab, gửi lại đều không nhân đôi.
- Gõ cửa: tài khoản ≥ 1 ngày tuổi; **tối đa 3 tài khoản gõ cửa mỗi mạng mỗi ngày**; chủ nhà tối đa 15 khách được tính kẹo/ngày (nick phụ gõ cửa nhà chính tối đa +30 kẹo/ngày); người chặn nhau không gõ được.
- Túi xu: tài khoản ≥ 3 ngày tuổi, nhân vật từ ngày sống thứ 3, tối đa 3 lần/tài khoản, **tối đa 3 tài khoản đổi xu mỗi mạng cả mùa**. Mạng chỉ lưu mã băm có khóa (không lưu địa chỉ).
- Quản trị → **Halloween**: tổng người chơi, kẹo đã kiếm / còn, số túi xu và tổng xu đã ra, kẹo theo loại, top 30 kèm tuổi tài khoản, danh sách túi xu kèm "cùng mạng" (nhiều nick mới cùng mạng nổi lên ngay). API: `GET /api/admin/halloween`.

## Tắt khẩn cấp

- Đặt `MNL_HALLOWEEN_OFF=1` trong `.env` rồi khởi động lại: không kiếm, không đổi, không thẻ, không dòng tin, không trang trí, lối vào biến mất; dữ liệu giữ nguyên. Bỏ biến (hoặc `=0`) là chạy tiếp.
- Đổi câu đố / chỗ nấp (nếu đáp án bị lộ): đặt `MNL_HALLOWEEN_SALT=<chuỗi bất kỳ>` → chỗ nấp từ lúc đó đổi (ai đã tìm vẫn giữ kẹo).

## Dữ liệu và quay lui

- SCHEMA_VERSION **80** (75 của careers-integ, 76–79 của nhánh khác): 2 bảng mới `hw_players`, `hw_log` + index; không FK, không backfill, không xóa gì.
- **Không thêm khóa save.** Quà đi qua `live_effects` kind `'hween'` (như Hội chợ việc làm): bản 2.4.71 không biết kind này nên để chờ, bản mới trả đúng một lần. Danh hiệu / khung / màu là id mới trong `spend.own` (bản cũ chỉ kiểm hình dạng id và không hiện id lạ); vòng kẹo thú cưng là món đã có trong 2.4.71.
- `tests/test_halloween_compat.py`: 2.4.71 khởi động trên DB 80 không DDL, giữ mọi dòng; quà đang chờ vẫn chờ ở bản cũ rồi được trả một lần ở bản mới; bản lưu có danh hiệu / màu Halloween đang đeo chạy tiếp trên 2.4.71.

## Câu hỏi cho chủ game

1. Số kẹo / giá quầy có ổn không? Túi xu 20.000 × 3 lần có nên nhỏ hơn hay bỏ hẳn?
2. Thưởng top 10 chỉ là danh hiệu + khung (không xu) — có muốn thêm gì không?
3. Giữ món thú cưng "Vòng kẹo" trong quầy (đang bán 900 xu ở tủ đồ thú cưng)?
4. Ngày đổi kẹo 01/11 có ổn không?
5. Đáp án câu đố giống nhau cho mọi người → người chơi có thể chia sẻ đáp án trong nhóm. Chấp nhận (vui, cộng đồng) hay muốn mỗi người một bộ?
