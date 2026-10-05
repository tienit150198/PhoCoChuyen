# Sửa thông báo hội chợ và tiệm riêng

Chủ game yêu cầu thay nội dung Có gì mới hiện tại, bỏ số xu cụ thể và các phần trăm. Nội dung thay thế:

1. Tặng xu chơi hội chợ
2. Tăng tỷ lệ thắng khi chơi hội chợ
3. Tăng tỷ lệ lãi khi mở tiệm riêng

Giữ version thông báo 1.7.10 và ngày 05/10/2026; người đã đọc không bị bật thông báo mới. Không thay cơ chế game, phát lại quà, chỉnh trạng thái đã đọc, hoặc đưa các tính năng local chưa deploy lên server.

Đã kiểm tra 4 tests EntriesData và Node whats_new.mjs. Hai file game/whats_new.py và public/js/v4/whatsnew-data.js được cập nhật trong bản đang chạy 1.7.11-20261005063033, sau khi xác minh SHA256 nguồn gốc. File nguồn và JS cũ được lưu ở /root/mnl-announcement-backups/20261005-070629.

Asset mới có hash a3f509cb458f, có bản nội dung tương ứng trong shared/_v. Bộ nhớ đệm trang tự cập nhật import map; không sửa nội dung asset cũ mang hash cũ. Tab đã tải module cũ cần tải lại trang. Không khởi động lại game/live; hai dịch vụ active và live vẫn có thời điểm khởi động 06:31:30.

Kết quả kiểm tra HTTPS và import map: output/announcement-production-check.json. ZIP 1.7.11 gốc giữ nguyên để đối chiếu lịch sử; lần đóng gói sau phải lấy thông báo đã chỉnh từ worktree.
