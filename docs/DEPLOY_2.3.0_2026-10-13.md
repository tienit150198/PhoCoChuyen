# Phát hành 2.3.0 — nâng cấp trả phí và thi đua NPC

Đã phát hành tại https://phocochuyen.io.vn lúc **22:07:53 UTC+7 ngày13/10/2026**. Release `/opt/mot-ngay-lam-nghe/releases/2.3.0-20261013220650`, build `2.3.0+14b9a3c887f2`.

## Nguồn và nội dung

- Source: `baf36b505b9788c6e37197610e83632d780ffb0d`. Manifest đang chạy được tải về root repo. Dùng source này làm `--base` lần sau, không dùng commit ghi báo cáo.
- Gói local: `output/deploy-20261013/mnl-2.3.0.zip`,104.125.920byte, SHA-256 `fb067d83cca02e7c532295451a5089e7cd82eb5f7a00718477fcf4699cfbbbf8`.
- Tái tạo live2.2.1 từ source24a910f3:1.820file nguyên byte,483asset minify khớp. Gói mới2.347file gồm manifest;100file thay đổi,15asset minify, không xóa nguồn.
- Mở nhánh tiện ích, kiểm đếm, hạn mức nhập/sở hữu/nâng quầy trả xu theo10bậc, từ3.000 đến100triệu xu mỗi bậc; tổng152.692.000xu mỗi nhánh.27nghề có nâng sức chứa kho và các tài nguyên liên quan.
-54nghề có3đồng nghiệp NPC mỗi nghề và162tình huống phân công/kiểm tra/khen.10ca/kỳ,80/100 là kỳ tốt bất kể xếp hạng;5hạng cần ít nhất150ca và bậc nghề tương ứng. Thưởng cơ bản có trần, không nhân x3; chùa nhận đúng phần tinh thần còn tăng được.
- Không có schema DB mới, không sửa hàng loạt hồ sơ.540gói công thức/mẫu hàng trong thiết kế chưa được phát hành.

## Kiểm chứng

- Trước deploy:67tests thi đua/kho/bản dịch đạt;1test Store ban đầu thiếu TEST_DATABASE_URL, chạy lại với PostgreSQL local đạt. Hai bộ Node thi đua và kho đạt.
-53.280mẫu nhiệm vụ của54nghề so sánh trực tiếp gói live2.2.1 với source mới: tương thích.
- Gói giải nén mới:2.346hash khớp; server khởi động bằng DB test riêng, tạo nhân vật/mở ca/chống replay/xuất bản lưu54nghề qua HTTP đạt.
- Rolling exit0; game và mnl-live active; bridge inactive.10mẫu HTTPS health đều ok/2.3.0/54nghề.
-1.614file runtime trên máy chủ đúng hash;732tests/artifacts được installer loại có chủ đích.7asset HTTPS (JS/CSS/tiếng Anh) đúng hash ZIP.
- Khởi tạo và đọc projection bằng mã đã deploy xác nhận54bảng thi đua,162tình huống. Playwright mở app thực tế ở390px/1280px đúng build, không có pageerror.
- Journal game/live từ lúc bắt đầu rolling không có Traceback/CRITICAL/ModuleNotFoundError/No space left/ERROR khớp bộ lọc.

## Khắc phục dung lượng trước deploy

Ban đầu filesystem chỉ còn khoảng99MB. Đã xóa39ZIP cài đặt tạm trong `/tmp` có manifest phiên bản từ2.0.7 trở xuống, giải phóng1.465.316.306byte; không xóa release, backup hoặc dữ liệu người chơi.

Dung lượng tiếp tục giảm trong lúc upload. Kiểm tra cho thấy PostgreSQL WAL9,2GB, `max_wal_size=16GB`, archive off và không có replication slot. Sao lưu `postgresql.auto.conf` vào `/root/mnl-pg-auto.pre-2.3.0-20261013.conf`, đổi `max_wal_size` thành4GB bằng ALTER SYSTEM, reload cấu hình và chạy CHECKPOINT. PostgreSQL tự thu hồi WAL; không xóa file WAL thủ công, không đổi bảng. Sau đó còn5.480.693.760byte, health cũ vẫn ok.

Guard trước rolling kiểm đường dẫn/manifest live, SHA ZIP và đủ152.701.244byte giải nén cộng2GiB dự phòng. KEEP=999 giữ các release cũ. Sau xác minh đã xóa đúng ZIP mới trong `/tmp`, giữ ZIP local; còn5.724.954.624byte (~5,33GiB). DB test local đã dừng.

## Khắc phục và quay lui

Ưu tiên sửa tiến bằng mã2.3.x. Không hạ trực tiếp về2.2.1 khi đã có người mua sức chứa/quầy vượt giới hạn cũ; không phục hồi DB cũ để quay lui mã.

Guard `/root/mnl-business-licenses-disable.sh` đã chuyển điều kiện từ2.2.1 sang2.3.0, có bản `.pre-2.3.0-20261013`, kiểm bash -n đạt; không chạy tắt tính năng.

Bằng chứng tại `output/deploy-20261013/`, ảnh browser tại `output/playwright/deploy-230/`. Không đăng thông báo hoặc gửi tin nhắn người chơi trong lần deploy này.
