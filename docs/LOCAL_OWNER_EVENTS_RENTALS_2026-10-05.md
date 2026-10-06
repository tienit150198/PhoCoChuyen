# Chủ tiệm và chợ thuê nhà — thay đổi local

Yêu cầu: thêm nhiều tình huống có lựa chọn cho chủ tiệm, camera giảm 50% nguy cơ trộm; chủ nhà tự đặt giá, NPC và người chơi thuê, cùng tin bất động sản làm giá và sức thuê biến động. Đợt này chưa deploy, không đổi Có gì mới và không đổi version 1.7.11 đang chạy.

## Chủ tiệm

- 12 tình huống: trộm, ăn quỵt, người làm nội dung xin đồ, trẻ đi lạc, kiểm tra giao thông, kiểm tra cửa tiệm, ảnh chuyển khoản giả, kiện thiếu phụ kiện, mưa, tranh tiền thừa, tranh lượt và mất điện.
- Thẻ Việc cần xử lý xuất hiện trong Sổ tiệm, thẻ Quầy riêng và màn tự bán. Lựa chọn ghi chi phí và hậu quả; nhật ký lưu kết quả.
- Camera giảm đúng một nửa xác suất trộm: 20% → 10%, hoặc 16% → 8% khi có khóa/két. Có thể mua qua đường nâng cấp hiện có.
- Khoảng nghỉ 12 đơn/nhịp việc thực tế, tối đa một sự kiện đang chờ; không tích lũy các khoản mất tiền khi offline. Mất mát giới hạn theo quỹ, luôn có phương án dùng được khi thiếu tiền.
- Uy tín ảnh hưởng lượng khách NPC trong giới hạn ±10%. Giữ khoản tăng lợi nhuận 40% đã có.

## Cho thuê và giá nhà

- Nhà của bạn → Mở chợ thuê nhà. Chủ nhập giá, xem giá tham khảo và dự báo cơ hội tìm NPC trước khi đăng.
- Danh sách người chơi tải 100 tin mỗi lượt, có nút Xem thêm nhà; không cắt bỏ các tin sau trang đầu. Tin đang cho thuê của chủ được ưu tiên trước lịch sử.
- Giá thuê tham khảo tăng gấp đôi mức cũ trước ảnh hưởng thị trường. NPC cân nhắc từ ngày sống kế tiếp; giá càng cao, xác suất thuê càng giảm; từ ba lần tham khảo NPC không nhận.
- Người chơi đăng nhập có thể đăng nhà trống hoặc thuê của người khác. Hợp đồng trả trước 5 ngày sống của người thuê, tự gia hạn; không tự trừ tiền. Giá đã ký giữ nguyên. Trả sớm không hoàn ngày còn lại, điều này hiển thị trước khi thuê và khi trả nhà.
- Chủ không thể lấy lại/bán/dọn vào căn có hợp đồng trả trước đang hiệu lực. Nhà mua bằng quỹ chung chưa cho đăng thuê; quyền ở chung/mời bạn miễn phí giữ nguyên.
- Người thuê vào được nội thất đúng loại nhà, dùng đồ của mình; đồ được cất lại khi chuyển đi. Căn thuê là phòng riêng của người thuê, không tự cho chủ nhà truy cập.
- 12 tin hư cấu về quy hoạch, giao thông, trường học, du lịch, tâm linh/ma, ngập, bụi/ồn, dư cung… Tác động nhiều ngày rồi hồi phục dần. Tin theo ngày thực Việt Nam, trung tính đến hết 05/10/2026.
- Giá rao mua nền giữ danh mục hiện tại; giá bán lại và giá thuê tham khảo chịu ảnh hưởng tin. Hệ số lúc mua được lưu riêng để tránh mua rồi bán ngay hưởng tin tăng sẵn.

## Kiểm tra và triển khai sau

- 151 tests về sự kiện, Quầy riêng, Sổ tiệm và nhân viên đã qua.
- 17 tests rental PostgreSQL đã qua, bao gồm tranh nhận nhà, bảo toàn tiền/replay, gia hạn, không đủ tiền, hết hạn, quyền sở hữu, nhập save, chuyển nhà chung, xóa tài khoản, đồ đạc, cập nhật tên, chặn người dùng và 205 tin qua ba trang không trùng nhau. Bộ hồi quy nhà/nhiều nhà/ký túc xá/trang trí/gia đình/schema gồm 148 tests đã qua.
- 8 tests tin bất động sản và 2 tests quyền phòng thuê live đã qua; Node UI kiểm tra dữ liệu/escape/giá/dự báo và giữ ID khi lỗi mạng đã qua.
- Chromium 320/390/430 px đã thao tác HTTP thật: xử lý hai loại tiệm; đăng NPC; đăng/thuê/gia hạn/trả nhà người chơi; vào nội thất. Mô phỏng trả HTTP 500 sau khi server đã thu tiền: bấm lại giữ mã và nhận replay, ví chỉ trừ một lần. Không tràn ngang hoặc lỗi JavaScript trong các luồng này.
- Luồng Xem thêm nhà đã kiểm tra trong Chromium bằng phản hồi phân trang mô phỏng: giữ tin trang đầu, thêm tin trang sau và ẩn nút khi hết trang. Phân trang dữ liệu thật kiểm bằng bộ PostgreSQL nêu trên.
- Đã sửa phát hiện review: xóa tài khoản phải kiểm hợp đồng trước khi xóa dữ liệu liên quan; ẩn tên lịch sử khi xóa; cộng tiện nghi đúng cho nhà thuê; giữ mã giao dịch khi phản hồi lỗi; nhắc rõ không hoàn tiền khi trả sớm.
- Thêm bảng PostgreSQL rentals, rental_receipts, rental_closed_accounts và chỉ mục. Cần gói nguồn sạch từ 1.7.11, kiểm migration và quy trình chuyển bản trước lần deploy tiếp theo. Không rollback mù về bộ đọc cũ sau khi có nội thất lease mới.

Chứng cứ trình duyệt: output/playwright/owner-rentals/report.json và các ảnh cùng thư mục.
