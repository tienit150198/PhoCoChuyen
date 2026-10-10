# Hiệu năng và đối chiếu hai giao diện — 11/10/2026

Yêu cầu: giảm giật khi chơi và giữ toàn bộ chức năng của giao diện cũ trong giao diện 2.5D. Giữ dữ liệu, điều kiện mở khóa và luật chơi trên server. Không công bố bảo đảm FPS hoặc 1.000 CCU từ kiểm thử trình duyệt đơn lẻ.

## Phạm vi thực hiện

1. Đối chiếu đủ 50 nghề, nút nghề trên điện thoại/tablet/desktop và các nhóm đời sống; sửa lối vào bị ẩn trên đảo và nút đổi nghề. Ghi riêng mức kiểm tra cấu trúc, hành vi và trình duyệt.
2. Dừng công việc vẽ/kiểm tra thừa: đường chỉ dẫn dùng chung vòng Phaser; hoạt động và cảnh 3D ngừng khi bị che; chỉ kiểm tra che khuất khi người/camera thay đổi.
3. Giảm xử lý lặp khi kéo bản đồ ở cùng mức zoom và cập nhật DOM không đổi khi nhận gói vị trí/người tới quán.
4. Chạy kiểm thử hồi quy có ca thất bại trước sửa, build/typecheck và kiểm tra giao diện thật tại các cỡ màn hình. Đo chi phí JavaScript bằng chẩn đoán opt-in; không gọi số này là FPS/GPU.

## Bằng chứng ban đầu

- Bản nguồn 5c671878, gói 2.0.0 đang chạy cục bộ, 1280×720, zoom 0,8: mẫu 240 khung khi di chuyển có JS tổng p50 0,8 ms, p95 1,8 ms, max 12,7 ms; đứng yên vòng Phaser ngủ. Đây là một mẫu IAB, không đại diện thiết bị người dùng.
- `railHTML` loại nút đã nằm ở dock khỏi menu điện thoại, trong khi dock bị CSS ẩn trên đảo: kiểm thử 50 nghề thất bại ở nút queue của grocery.
- Chỉ dẫn có RAF riêng vẽ lại cả đường dù Phaser đang dừng; hoạt động và kiểm tra che khuất 3D còn làm việc khi trạng thái không cần đổi.

## Điều kiện phát hành

Chỉ đưa thông báo sau khi ứng viên cuối vượt kiểm thử và bản triển khai được xác minh. Lần triển khai trước bị chặn bởi SSH; kết quả cục bộ không đồng nghĩa đã phát hành.
