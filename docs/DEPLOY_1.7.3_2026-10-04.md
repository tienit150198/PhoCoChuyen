# Phát hành 1.7.3 — 04/10/2026

Theo yêu cầu chủ dự án, phát hành sửa tính năng hiện có trước; các nghề mới thuộc đợt riêng.

- Hoàn tất rolling deploy lúc 17:35:26 UTC+7, website https://phocochuyen.io.vn.
- Release: `/opt/mot-ngay-lam-nghe/releases/1.7.3-feedback-20261004`.
- Health: HTTP 200, `status=ok`, `game_version=1.7.3+bd37e2a456e6`, vẫn 41 nghề.
- Game và live active; bridge đã dừng. PostgreSQL schema 18. Khóa VAPID khớp hash trước triển khai; namespace giữ nguyên giá trị cũ để giữ khóa bảo trì.
- Sao lưu PostgreSQL hoàn tất trước triển khai: `/var/backups/mot-ngay-lam-nghe-pg/phocochuyen-20261004-102827.dump`, khoảng 1,6 GB; pg_restore đọc được mục lục.
- Driver PostgreSQL 3.3.6 binary đặt riêng tại `/opt/mot-ngay-lam-nghe/shared/postgres-173`; giữ vendor cũ phía sau trong PYTHONPATH. Game/live nạp `/etc/mot-ngay-lam-nghe/postgres-only-173.env` qua drop-in `zzzz-postgres-only-173.conf`.
- Không tạo nghề mới, gửi thông báo chat, trả lời hoặc sửa trạng thái feedback trong đợt triển khai này.

## Kiểm chứng

- Đối chiếu 186 file Python của release 1.7.2 đang chạy với baseline: khớp toàn bộ.
- 40.800 nhiệm vụ từ baseline, 41 nghề/ngày 1–40, tương thích bản mới.
- Gói release: 1.145 hash nguồn/tài nguyên khớp tại máy phát triển và Linux production; 328 tài nguyên đã minify. Chạy thử từ ZIP giải nén trên PostgreSQL riêng qua tạo hồ sơ, mở ca, replay và export save.
- 80 test family/bank transfer/community/admin/PostgreSQL trước deploy đều qua; 234/234 file JavaScript qua kiểm tra cú pháp.
- 12 mẫu health trong lúc chuyển traffic đều `ok`, không lỗi request. Health sau khi canonical và live khởi động lại trả HTTP 200.
- Admin production hiện danh sách người dùng và ô tìm tên/username; đã kiểm tra cả hai cách tìm.
- Kiểm tra giới hạn kích thước public journey vẫn có lỗi đã tái hiện trên HEAD gốc; không tuyên bố toàn bộ suite xanh. Chi tiết trong kế hoạch feedback/PostgreSQL.

Gói local: `output/release-173/mnl-1.7.3.zip`; SHA256 `c279ccf6737e519c0d5e7d90856687f85a342348106e99bd1b2409610173bcc1`. Báo cáo package, compatibility, test và health lưu cùng output hoặc `output/compat-173.log`.

## Điều kiện rollback

Không chạy nguyên lệnh rollback do helper in ra nếu bản lưu đã có giao dịch lớn: bản cũ cần mang theo validation lịch sử ví/ngân hàng ±1 tỷ. Dữ liệu con chung nằm ở schema 18; bản cũ không có giao diện này. Giữ bản sao lưu, khóa VAPID và namespace hiện tại. Ưu tiên sửa tiến bản khi có sự cố; không restore database làm mất tiến trình mới của người chơi.
