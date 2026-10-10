# Phố Có Chuyện 2.0 — kế hoạch phát hành

Mục tiêu: đưa giao diện Phaser 2.5D đã hoàn thiện lên hệ thống, cho người chơi chủ động dùng giao diện cũ; bổ sung ảnh góp ý và hai ngày vàng Chợ Đen. Chỉ thông báo sau khi kiểm tra và triển khai thành công.

## Kiến trúc và trách nhiệm

- Agent giao diện: lựa chọn lưu theo tài khoản trong `journey.interface`, chiếu ra `settings.newInterface` trong API; mặc định mới; lời mời quay lại giao diện cũ một lần; tải renderer/CSS theo lựa chọn, giữ chung save và phiên đăng nhập. Reload sau khi lưu thành công để kết thúc sạch renderer cũ. Cách lưu này giữ tương thích bộ đọc save cũ.
- Agent góp ý: tối đa 3 ảnh, kiểm tra ảnh và kích thước ở server, chuẩn hóa ảnh, lưu PostgreSQL; URL có kiểm tra chủ sở hữu/quản trị; không tự xóa ảnh đã gửi. Xem trước và bỏ ảnh trong bản nháp.
- Agent sự kiện: một cửa sổ 48 giờ lưu bền tại server, kích hoạt idempotent lúc phát hành. Tăng xác suất của Chiếu trong, lô tô, vé cào; giữ trò kỹ năng và kết quả chung đúng luật. Không công bố con số trong thông báo.
- Agent chính: ghép upstream, kiểm tra tích hợp/đa kích thước, review độc lập, đóng gói bản 2.0.0, deploy theo quy trình hiện có, kiểm tra production rồi thông báo.

## Danh sách thực hiện

- [x] Giữ an toàn thay đổi local và ghép main mới.
- [x] Toggle và lời mời trở lại giao diện cũ; kiểm tra lựa chọn tồn tại sau tải lại.
- [x] Ảnh góp ý: gửi 0–3 ảnh, chặn 4 ảnh/tệp lỗi; xem lại với quyền phù hợp; giữ ảnh sau phản hồi.
- [x] Sự kiện: chưa kích hoạt/đang hoạt động/hết hạn; kích hoạt lại không kéo dài; xử lý đồng thời nhiều worker.
- [x] Build Phaser/3D, typecheck, JS/Safari compatibility, nhóm kiểm tra nghề/bản đồ/nước/nhà và backend bị ảnh hưởng.
- [x] Kiểm tra trình duyệt mobile, tablet, desktop với kích thước thực được ghi nhận: mới/cũ, settings, góp ý, khu phố và nghề, popup/cuộn.
- [x] Review độc lập yêu cầu và chất lượng, sửa các lỗi còn lại.
- [x] Đóng gói từ baseline tái lập theo manifest production; xác minh manifest/task compatibility, giữ dữ liệu người dùng. Cần đối chiếu manifest thực khi SSH được khôi phục.
- [ ] Triển khai, health/static/API smoke, kích hoạt 48 giờ.
- [ ] Công bố bản 2.0 và hướng dẫn Cài đặt → Giao diện mới; xác minh thông báo hiển thị.

## Điều kiện phát hành

Không có lỗi nghiêm trọng chưa xử lý trong các luồng đã kiểm tra. Có bằng chứng lệnh, ảnh giao diện và kết quả smoke. Không suy từ kiểm tra một máy ra bảo đảm 1.000 CCU hoặc mọi thiết bị. Không đưa thư mục output/tmp, thông tin xác thực hay dữ liệu người chơi vào commit/gói phát hành.
