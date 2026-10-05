# Rà soát socket bị rớt

Sau deploy 1.7.9, người dùng báo rớt mạng liên tục. Đã kiểm tra read-only production; sửa client ở local, chưa deploy sửa socket này.

## Bằng chứng

- Nginx reload lúc 23:53:21 và 23:53:49 ngày 04/10; `worker_shutdown_timeout 20s` làm đóng WebSocket của worker cũ. Live restart lúc 23:54:11, mã đóng 1012; sẵn sàng nghe lúc 23:54:15.
- Log `/live`: 23:53 có 140 kết nối 101 kết thúc, 23:54 có 174 kết nối 101 kết thúc, 180 handshake HTTP 502 và 56 handshake HTTP 503. Những lỗi này nằm trong giai đoạn deploy, khác cửa sổ kiểm tra API sau deploy ghi trong báo cáo 1.7.9.
- Trước/sau deploy thường thấy khoảng 6–19 kết nối 101 kết thúc mỗi phút trên khoảng 120–130 kết nối. Chỉ số này gồm cả đóng tab/tải lại/mất mạng; không dùng nó để kết luận mọi lần đóng đều là lỗi.
- `mnl-live NRestarts=0`, không có crash/restart ngoài lần deploy trong cửa sổ 20 phút đọc log. Health lúc 23:58 có 126 kết nối, cut=0. `cut` chỉ đếm client chậm bị ngắt, không đếm mọi nguyên nhân đóng.
- Browser ở lần quan sát cuối: banner nối lại bị ẩn, nút gửi bật. Không gửi tin thử và không sửa nội dung chat.
- Nginx timeout socket 75s; server đóng socket không nhận frame ứng dụng sau 70s; client ping mỗi 25s. Mobile đóng băng app/tab vẫn có thể cần nối lại.

## Lỗi client đã tái hiện và sửa local

1. Heartbeat cũ thấy frame cuối quá 60s thì gọi close ngay. Nếu bộ hẹn giờ bị chậm ở nền, socket còn sống cũng bị đóng. Mới: gửi ping kiểm tra trước, chỉ thay kết nối nếu không có phản hồi trong hạn kiểm tra đang dùng.
2. Close trên socket nửa sống có thể không phát `onclose` sớm, làm không lên lịch nối lại. Mới: probe quá hạn chủ động bỏ socket cũ, tạo kết nối mới mà không đợi close event.
3. Kết nối không mở hoặc mở transport nhưng không nhận welcome có thể chờ vô hạn. Mới: deadline 20s, đóng và retry theo backoff hiện có; welcome hủy deadline.
4. Callback `onopen`/`onmessage` của socket cũ có thể chạy muộn và sửa state của socket mới. Mới: kiểm tra danh tính socket trước khi xử lý, hủy timer cũ khi bỏ/đóng kết nối.
5. Console chỉ ghi close code, clean flag và deadline để phân biệt nguyên nhân khi cần kiểm tra; không ghi cookie, tên hay nội dung chat.

## Xác minh và giới hạn

6 ca kiểm tra socket giả lập: heartbeat bị trì hoãn nhưng socket khỏe, socket không có close event, handshake treo, welcome treo, frame cũ, welcome hủy deadline. Trước sửa: 5 fail/1 pass. Sau sửa: 6 pass. Cùng kiểm tra đồng bộ tên, chat history và reply: tổng 39 pass. Log ở `output/live-connection-red.log` và `output/live-connection-green.log`.

Chưa đủ close-code telemetry để quy tất cả lần rớt ngoài deploy về một nguyên nhân. Sửa client không loại bỏ việc server cố ý đóng socket khi deploy hoặc khi thiết bị bị hệ điều hành ngắt mạng. Quy trình deploy hiện có thể làm rớt socket nhiều lần; cần tách vòng đời proxy/socket khỏi game hoặc thiết kế lại thứ tự chuyển trước khi hứa deploy không gián đoạn chat. Chưa thay cấu hình proxy hay nới giới hạn bảo vệ.
