# Phát hành chùa và địa điểm đi bộ 2.2.0

Đã phát hành tại https://phocochuyen.io.vn, hoàn tất rolling lúc **16:04:01 UTC+7 ngày 13/10/2026**.

## Nguồn và gói

- Source: `e179dd8a9cc6e773dc98fe453c206a1008e1bf2d`, đã push main.
- Release: `/opt/mot-ngay-lam-nghe/releases/2.2.0-20261013160258`.
- Build công khai: `2.2.0+709de7842c55`.
- ZIP local: `_business_balance_20261012/mnl-2.2.0-temple-final.zip`, 103.771.474 byte, SHA-256 `6adfb1deb911310a14fa23332f23b96a45ea3be8041c1683d8c4eb231a96b3e0`.
- Dựng từ live 2.1.0/source `b217a0ca494b95fb45fc75969c880cae299398b7`: 1.802 file nguyên byte, 479 asset minify tái tạo khớp. Gói gồm 2.297 file tính cả manifest, 39 file thay đổi, 14 asset minify, không xóa file nguồn.
- Trước chuyển: kiểm đường dẫn live, hash manifest, hash ZIP và chỗ trống cho ZIP + 151.188.654 byte giải nén + 2 GB dự phòng. `KEEP=999` giữ release cũ.

## Nội dung

Chùa đi bộ có hoạt động lặp không giới hạn, thẻ chúc riêng tư lưu lâu dài, xem lịch sử cũ và tinh thần 0–100. Thêm 14 không gian công cộng có đi lại/vật cản/quầy tương tác; vào miễn phí, giao dịch dùng dịch vụ hiện có. Giao diện cũ cũng vào được ba khu nước. Chi tiết và điều kiện được giữ tại [TEMPLE_VENUES_2.2.0.md](TEMPLE_VENUES_2.2.0.md).

## Kiểm tra

- Lượt tổng hợp cuối **116 tests** chùa, thẻ, dịch vụ, đi chơi, cộng đồng, archive, bản dịch và tài nguyên đạt.
- Node kiểm tra di chuyển/vật cản/đường đi/proximity, tạm dừng/tiếp tục, định tuyến và các dialog lồng nhau đạt; 1.756 đường đi chùa đạt. 357/357 file JS đạt cú pháp và Safari/iOS 15.
- Bốn lượt browser chùa 390/1280 × giao diện cũ/mới đạt; lượt riêng 43 thẻ đọc được thẻ đầu tiên trong archive, công đức giữ vị trí; lượt tiếng Anh giữ nguyên tên/lời nhắn tiếng Việt, không còn chữ hệ thống chùa chưa dịch trong báo cáo phạm vi chùa.
- 14 phòng được thử trực tiếp ở 390/1280. 13 kiểm tra đường vào trong ứng dụng đạt, giữ ví khi tham quan, quay lại đúng vị trí, không lỗi browser.
- 53.280 mẫu nhiệm vụ, 54 nghề × 40 ngày đối chiếu với live 2.1.0: tất cả tương thích.
- Gói giải nén mới: toàn bộ 2.296 hash nội dung đúng; server và PostgreSQL thử riêng khởi động; tạo người chơi, mở ca, chống lệnh lặp và xuất bản lưu 54 nghề qua HTTP đạt.
- Sau triển khai: **1.583 file đúng hash**, 713 tests/artifacts được installer loại có chủ đích, không thiếu runtime. Chín asset công khai đúng hash, gồm JS/CSS chùa/phòng mới và gói tiếng Anh.
- Tám mẫu health đúng version/build/54 nghề; `/api/content` tải đầy đủ. Game/live active và cwd đúng release, bridge inactive. Cửa sổ journal từ 16:02:57 không có dấu Traceback/CRITICAL/ModuleNotFoundError.

Assertion mã lỗi nhập bản lưu ngoài phạm vi thất bại y hệt trên baseline 2.1.0 (`import_other` thay vì `import_richer`). Không tính assertion này là đạt hoặc sửa cơ chế import trong đợt chùa.

## Dung lượng, sao lưu và vận hành

Đã thử stream `pg_dump` thẳng về máy phát triển để không chiếm ổ production. Do truyền chậm, đã dừng tiến trình của đợt này; xác nhận không còn pg_dump, xóa đúng file local dở 948.961.280 byte. **Không có bản backup mới hoàn tất trong đợt này.** Không thay schema hay sửa hàng loạt hồ sơ. Bản tự động `/var/backups/mot-ngay-lam-nghe-pg/phocochuyen-20261012-204831.dump` vẫn nguyên, 3.741.560.009 byte; `pg_restore --list` đọc được.

Sau kiểm chứng đã xóa riêng ZIP vừa tải ở `/tmp`, bản local vẫn giữ. Không xóa backup/release cũ. Chỗ trống cuối **2.797.404.160 byte (~2,6 GiB), filesystem 99%**. Cần mở rộng ổ hoặc dọn theo chính sách lưu trữ được chủ hệ thống chấp thuận; không tạo thêm full backup trên ổ này.

Không dùng câu rollback về 2.1.0 mà rolling helper in tự động: validator chùa cũ không nhận cards/hơn bốn loại hoạt động. Dùng sửa tiến tương thích 2.2.x, không phục hồi DB cũ để quay lui mã. Guard `/root/mnl-business-licenses-disable.sh` đã đổi sang 2.2.0, giữ bản `.pre-2.2.0-20261013`, chỉ kiểm `bash -n`, không chạy tắt tính năng.

Manifest gốc được tải từ release đang chạy. Báo cáo và ảnh trong `output/temple-walk/`, `output/live-verification-2.2.0.json` ở máy phát triển.
