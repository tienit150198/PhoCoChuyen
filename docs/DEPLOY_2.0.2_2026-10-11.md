# Phát hành sửa feedback 2.0.2 — 11/10/2026

Production: https://phocochuyen.io.vn. Thời gian UTC+7.

## Bản đã triển khai

- Rolling hoàn tất **12:09:36**, exit 0. HTTP và live chạy tại `/opt/mot-ngay-lam-nghe/releases/2.0.2-20261011120834`.
- Health `2.0.2`, build `2.0.2+a9ed1467badd`. Source `22be33b0ed6ceec017022f720880ba8fb986b9ba`.
- ZIP `mnl-2.0.2-feedback.zip`: 103.306.790 byte, SHA-256 `574551f666403d092127dc948f162f1b7fde300593258d37e4797eb5534f8d9f`; file tải lên khớp mã băm.
- Dựng từ ZIP 2.0.0 đã xác minh và source của nó `253bc53c91eb6fdbeab14ea7381ebe08ccee2f19`. Trong lúc làm việc, hotfix 2.0.1 được phát hành; đã nhập đầy đủ source `4e1923c7`, xác minh 1.529 file runtime và hai dịch vụ của 2.0.1 trước khi chuyển bản.
- So manifest 2.0.2 với 2.0.1: chỉ 11 file được duyệt khác nhau, gồm ba module sửa lỗi, ba file phiên bản, bốn file kiểm thử và báo cáo QA. Giữ nguyên toàn bộ mã giao diện/rương và thay đổi Chợ Đen của 2.0.1. Không xóa file.
- Kiểm symlink và hash manifest 2.0.1 lần nữa ngay trước rolling. Root `MANIFEST.json` được tải trực tiếp từ 2.0.2 sau triển khai.

## Xác minh

- 29 mẫu HTTP health trong lúc chuyển bản, không mẫu lỗi; thấy phiên bản chuyển 2.0.1 → 2.0.2. Lấy mẫu không chứng minh mọi request đều không lỗi.
- HTTP/live active, working directory đúng bản mới; live health đạt. Không thấy `Traceback`, `CRITICAL`, `ModuleNotFoundError` trong tối đa 500 dòng log mỗi dịch vụ kể từ lần khởi động mới. Rolling vẫn có cảnh báo fork đa luồng và một số lệnh business_sync chậm trên bản lưu lớn; không quy các cảnh báo đó là đã sửa.
- 1.530 file runtime khớp manifest. Asset kéo co phục vụ qua HTTPS khớp ZIP; file Có gì mới và bảng thưởng giữ nguyên byte.
- Kiểm trên runtime: đủ 50 truyện nghề, giỏ chung 40 dòng; dữ liệu truyện của góp ý 337 qua validator. Hồi quy thanh toán đã kiểm cục bộ; không tự chơi thay người dùng trên production.
- Khoản cược 5.000 xu của góp ý 336 đã được hoàn, hiệu ứng `applied` và sổ ví đồng nhất; không cấp bù lần hai. Điều kiện top kéo co vẫn 30 trận, thưởng top 5 vẫn 2M/1M/500k/250k/100k.
- Mốc Hai ngày vàng vẫn bắt đầu `1791689983`, kết thúc `1791862783`; không kích hoạt lại. Không sửa Có gì mới hoặc đăng thông báo công khai.
- Dùng bản backup trước hotfix 2.0.1 tại `/var/backups/mot-ngay-lam-nghe-pg/hotfix-2.0.1-20261011/phocochuyen.dump`: kiểm lại 3.327.536.576 byte, đọc mục lục `pg_restore --list` thành công. Chưa thử restore. Đợt này không đổi schema hoặc sửa trực tiếp bản lưu.

## Feedback

Đã đọc lại database và xác minh đúng nội dung/trạng thái của **13 góp ý người chơi**, cùng một góp ý kiểm thử phát hành 2.0. Không còn mục `new` trong nhóm 324–338 tại lần kiểm cuối. Các ID đã phản hồi: 324, 325, 326, 327, 329, 330, 331, 332, 333, 334, 336, 337, 338; mục kỹ thuật 335 đóng sau đối chiếu báo cáo, giữ nguyên ảnh.

Đã trả lời trực tiếp theo yêu cầu chủ game; cập nhật có điều kiện theo thời điểm đọc để không ghi đè phản hồi mới. Các mục thiếu thông tin hoặc còn yêu cầu mở rộng giữ `seen`: hát cùng bạn, du học, tiền mất cần đối chiếu, đồ nội thất/nhận hàng tự động. Không nhận là đã bổ sung các tính năng chưa làm. Góp ý 328 có phản hồi quản trị trước đó, giữ nguyên.

Phạm vi và kiểm thử chi tiết: [QA feedback](qa/feedback-2026-10-11.md). Bằng chứng riêng và log ở `output/`, không commit dữ liệu người chơi hoặc thông tin xác thực.

## Quay lui

Giữ release cũ với `KEEP=999`; bridge pool 1, max 3, MemoryMax 3G. Nếu cần quay lui, phải giữ giới hạn truyện theo số nghề và giỏ 40 dòng trong bản quay lui: validator 2.0.1 nguyên trạng không đọc được những bản lưu đã vượt giới hạn cũ. Cũng giữ cơ chế rương tích lũy của 2.0.1. Không tự phục hồi database cũ để quay lui mã.
