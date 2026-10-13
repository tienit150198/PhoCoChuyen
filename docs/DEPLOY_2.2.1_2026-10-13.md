# Phát hành quyền xem thẻ chúc 2.2.1

Đã phát hành tại https://phocochuyen.io.vn lúc **18:08:46 UTC+7 ngày 13/10/2026**. Release `/opt/mot-ngay-lam-nghe/releases/2.2.1-20261013180744`, build `2.2.1+fcc06e6d5dd6`.

## Nguồn và gói

- Source: `24a910f3a5c9cac877301d9a306e03057054edcd`.
- ZIP: `_business_balance_20261012/mnl-2.2.1-temple-visibility.zip`, 103.792.442 byte.
- SHA-256: `ca23b09a35561e92e3ad212aab17717608bac775faf75e11f05273381a67828b`.
- Dựng từ live 2.2.0/source `e179dd8a9cc6e773dc98fe453c206a1008e1bf2d`: 1.813 file nguyên byte, 483 asset minify tái tạo khớp. Gói có 2.304 file gồm manifest, 22 file thay đổi, ba asset minify, không xóa nguồn.

## Nội dung và kiểm tra trước triển khai

Người chơi chọn Công khai hoặc Chỉ mình tôi khi viết thẻ; mặc định riêng tư. Đổi quyền được sau khi viết, kể cả thẻ archive. Bảng chung chỉ đọc projection của thẻ được chủ động chia sẻ. Thẻ cũ không tự công khai. Xem [TEMPLE_SHARING_2.2.1.md](TEMPLE_SHARING_2.2.1.md).

- 86 tests cuối đạt: chùa/thẻ/quyền xem, Store/HTTP, archive, schema, bản dịch và web assets.
- Kiểm riêng quyền chủ, CSRF, rollback giao dịch, cả hai nhánh ghi Store, chống replay tái công khai, import/reset/delete và đổi quyền khi đang bị giam.
- Review phát hiện race phân trang khi thẻ thứ 41 đẩy thẻ cũ vào archive; sửa bằng một snapshot REPEATABLE READ, regression đạt. Thẻ archive nhập vào bị lỗi được bỏ qua an toàn.
- Hai bộ Node UI đạt; các phản hồi cũ không đưa thẻ đã thu hồi trở lại. Giao diện cũ kết nối server chưa có sharing vẫn dùng luồng riêng tư.
- 357/357 JS đạt cú pháp và Safari/iOS 15. 1.756 đường đi chùa đạt.
- Browser hai phiên người chơi ở 390/1280 × giao diện mới/cũ: tạo riêng tư/công khai, người khác không thấy thẻ riêng tư, thu hồi, tải 103 thẻ và đổi quyền thẻ archive đều đạt; không có page errors.
- 53.280 mẫu nhiệm vụ của 54 nghề đối chiếu live 2.2.0 đều tương thích.
- Gói giải nén mới có đủ 2.303 hash nội dung; khởi động bằng PostgreSQL thử riêng, tạo nhân vật/mở ca/chống lệnh lặp/xuất bản lưu 54 nghề qua HTTP đạt.

## Vận hành

Schema 42 chỉ thêm bảng `chua_public_cards` có khóa phân trang, unique chủ/thẻ và FK xóa theo phiên. Không backfill, không tạo chỉ mục trên archive lớn hoặc sửa hàng loạt hồ sơ. Kiểm nâng cấp từ schema 41 và gọi lại idempotent trên DB thử đạt.

Trước triển khai còn 4.133.937.152 byte. Guard kiểm đường dẫn live, hash manifest, hash ZIP, và đủ chỗ cho gói/151.246.703 byte giải nén/2 GB dự phòng. `KEEP=999` giữ các release cũ. Không tạo full backup mới trên ổ production, không xóa backup hoặc release cũ. Bản backup hoàn tất gần nhất đã kiểm trong đợt 2.2.0 vẫn là `phocochuyen-20261012-204831.dump`; đợt này không tạo backup mới.

Báo cáo và ảnh kiểm thử tại `output/temple-visibility/`; gói local giữ nguyên.

## Kiểm chứng sau triển khai

- Rolling hoàn tất với exit 0; schema production 42 và bảng mới tồn tại.
- 1.588 file runtime đúng hash; 715 tests/artifacts được installer loại có chủ đích, không thiếu runtime. Mười asset công khai đúng hash, gồm JS/CSS chùa và tiếng Anh.
- Tám mẫu health đúng 2.2.1/build/54 nghề, tải đầy đủ content. Game và live active, cwd đúng release; bridge inactive. Không có Traceback/CRITICAL/ModuleNotFoundError trong journal từ lúc triển khai.
- Đã tải manifest của release đang chạy vào repo và cập nhật baseline. Source cùng báo cáo được push main.
- Xóa đúng ZIP đợt này trong `/tmp` sau xác minh, giữ gói local; còn 3.944.472.576 byte (~3,67 GiB), filesystem 98%.
- Guard `/root/mnl-business-licenses-disable.sh` đổi sang 2.2.1, giữ `.pre-2.2.1-20261013`, kiểm `bash -n`; không chạy tắt tính năng. Tiếp tục ưu tiên sửa tiến tương thích; không hạ về mã trước chùa 2.2.0, không phục hồi DB cũ để quay lui mã.
