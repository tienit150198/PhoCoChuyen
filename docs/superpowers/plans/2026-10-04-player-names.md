# Đồng bộ tên hiển thị bạn bè

Tên nhân vật mới phải xuất hiện ở danh sách bạn bè, chat và người cùng nhà. Username đăng nhập giữ nguyên. Không deploy, không thay đổi bản tin Có gì mới.

- [x] Đồng bộ accounts.display trong cùng giao dịch lưu settings.name, giữ nguyên username và nickname riêng của Phố nghề.
- [x] Sửa dữ liệu tên cũ qua migration PostgreSQL idempotent, tránh ghi đè rename đang chạy.
- [x] Phát tên mới đến các phiên và bạn bè có quyền nhận, cập nhật lịch sử chat khi đọc.
- [x] Cập nhật cache phía trình duyệt, tên người cùng nhà, bản nháp/reply không bị mất.
- [x] Kiểm tra PostgreSQL, WebSocket thật và trình duyệt hai người dùng; xác nhận username không đổi.

Frontend RED đã tái hiện tên cũ ở account, bạn bè, DM, reply và phòng chung trước khi sửa.

Kết quả và giới hạn kiểm tra: `docs/LOCAL_PLAYER_NAMES_2026-10-04.md`.
