# Ghé chỗ làm và làm khách thật

**Đã được người dùng đồng ý:** làm dễ chơi; ghé quầy riêng hoặc chỗ làm của các nghề hiện có, đặt dịch vụ thật và đánh giá sau khi hoàn thành. Chỉ local, không deploy và chưa ghi Có gì mới.

**Luồng:** Bạn bè / Mọi người đang làm gì → Ghé chỗ làm → Làm khách → chọn dịch vụ và thấy giá → gửi yêu cầu → được phục vụ → nhận kết quả → đánh giá. Người bán nhận đơn trong hàng chờ đang dùng. Không chuyển nghề hoặc mất bản nháp của người ghé.

**Kiến trúc:** PostgreSQL giữ nơi làm công khai tối thiểu, đơn giữ tiền và đánh giá gắn đơn. Quyền công khai/bạn bè/tạm đóng và chặn hai chiều kiểm tra tại máy chủ. WebSocket giữ người đang có mặt, chuyển động và trò chuyện ngắn; không lưu vị trí. Dịch vụ thủ công dùng nhiệm vụ gốc của nghề với metadata khách riêng; không đổi đáp án hoặc cấp thêm tiền NPC. Hoàn thành được xác nhận trong giao dịch lưu tiến trình, thanh toán một lần bằng giao dịch khóa các bản lưu theo thứ tự. Nhân viên dùng kho, thời gian và lương thật.

## Phân công

Skill dispatching-parallel-agents được áp dụng cho các phần độc lập, giữ tích hợp chung ở root.

- [x] Bridge nghề và kiểm thử: game/player_service_tasks.py, engine hooks.
- [x] Places/orders/ratings và kiểm thử: game/work_visits.py.
- [x] Giao diện dễ dùng, liên kết bạn bè/chat/phố và danh tính khách thật.
- [x] Root: schema, Store/server integration, phòng live và kiểm thử quyền.
- [x] Kiểm tra giao dịch đồng thời, hoàn tiền, nhập bản lưu, chặn/quyền riêng tư, nghề và nhân viên.
- [x] Kiểm tra trình duyệt desktop/390px từ khách tới người phục vụ và đánh giá; lưu bằng chứng local.

## Quyết định UX và dữ liệu

- Mặc định chỉ bạn bè; chủ chọn công khai hoặc tạm đóng.
- Giá hiện trước khi gửi. Ghi chú là lời nhắn; chỉ những lựa chọn thực sự được nghề hỗ trợ mới là tùy chọn dịch vụ.
- Giữ nguyên công việc đang dở và lựa chọn của người bán. Đơn mới được thêm khi có chỗ trong ca.
- Hủy/từ chối trước phục vụ được hoàn tiền. Không có nút giả hoàn thành thay minigame.
- Mỗi đơn hoàn thành chỉ có một đánh giá 1–5 sao, nhãn chất lượng/thái độ/thời gian và lời nhận xét; chủ được trả lời.
- Tên/avatar công khai được dùng ở phòng và thẻ khách; không lộ sid, tài khoản, tiền hoặc đáp án nghề.
