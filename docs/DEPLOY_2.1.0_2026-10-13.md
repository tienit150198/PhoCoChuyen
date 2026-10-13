# Phát hành nghề mới và cấp cao 2.1.0 — 13/10/2026

Bản 2.1.0 đã chạy tại https://phocochuyen.io.vn. Rolling helper hoàn tất 15:13:12 UTC+7; kiểm chứng sau khắc phục sự cố dung lượng lúc khoảng 15:17–15:19. Không tuyên bố phát hành hoàn toàn không gián đoạn: đã có phản hồi bị cắt khi ổ đĩa đầy, ghi rõ bên dưới.

## Nội dung đã chạy

- Bốn nghề mới: xưởng vẽ, luật sư, giặt ủi, bưu điện; tổng 54 nghề. Mỗi nghề có quy trình riêng, biến thể nâng cao và mốc việc tốt/ngày thực làm.
- Thang nghề thông thường lên bậc 7; giữ bảy bậc phi công, giữ cấp hàm/chức vụ/quy tắc ghế công an. Giáo viên thêm bậc 6–7. Các danh hiệu cũ và tiến độ giữ nguyên.
- Ba bậc tay nghề riêng cho cả 54 nghề: điều kiện việc sạch, ngày chuẩn, XP và sát hạch 7/8. Thưởng 6/12/20 xu/ngày chuẩn, có giới hạn lượt nhận thu nhập, không nhân tiếp x3. Lưu bài đang thi; nghỉ việc không xóa tay nghề.
- Giao diện hộ chiếu/thăng tiến cho cả hai chế độ, điện thoại/máy tính; tiếng Anh, bản đồ và cửa nghề mới. Không thêm bảng DB hoặc sửa hàng loạt hồ sơ.

Chi tiết số tiền, giả định và thời gian chinh phục: [CAREER_BALANCE_2.1.0.md](CAREER_BALANCE_2.1.0.md).

## Nguồn và gói

- Source gói: `b217a0ca494b95fb45fc75969c880cae299398b7`; đã push main. Commit sau đó ghi tài liệu cân bằng và bằng chứng phát hành.
- Release: `/opt/mot-ngay-lam-nghe/releases/2.1.0-20261013151209`.
- Build công khai: `2.1.0+a57d301a1f52`.
- ZIP 103.725.490 byte, SHA-256 `aba3f22e562d933ac4e0f3584a9e9d207a415e0e8349a79dd2a9b266f878558a`; bản local còn giữ ở `_business_balance_20261012/mnl-2.1.0-careers.zip`.
- Tái tạo từ live 2.0.7/source `53eaad980c35296acd9c3b4c658b683f10f807bf`: 1.767 file nguyên byte, 472 asset minify tái tạo khớp. Gói mới 2.281 file, không xóa file nguồn; 18 asset thay đổi được minify.
- Guard đường dẫn live cũ, manifest cũ và SHA ZIP trước rolling. `KEEP=999` giữ các release cũ.

## Kiểm tra

- Lượt tổng hợp cuối: 87 tests nghề mới, tay nghề, reducer/tiền, x3, migration, staff và phân loại đạt. 27 tests tài nguyên và tiếng Anh đạt. Promotion/office: 76 đạt, 1 bỏ qua; 9 tests endgame mới có trong đó.
- 354/354 file JS đạt cú pháp và Safari/iOS 15. Typecheck/build isometric, cấu trúc nghề, toàn bộ isometric và performance parity đã đạt; các kiểm tra Node mới về tay nghề/danh hiệu đạt.
- 16 ca browser cho bốn nghề ở ngày 1/40 và 390/1280px: hoàn tất, sai rồi sửa, reload và thu nhập; 64 checkpoint không tràn. Bốn ca browser tay nghề cho giao diện cũ/mới ở 390/1280px: thi trượt/retry, thi đạt và reload giữa bài; 16 checkpoint không tràn, không lỗi browser.
- 108 mô phỏng tay nghề: 54 nghề × hai nhịp việc. Ba việc sạch/ngày đạt bậc vào ngày 19/44/89; bốn việc/ngày vào 15/40/75. Mô phỏng 90 ngày cộng thưởng 710/870 xu khi luôn còn lượt thu nhập.
- Đối chiếu 49.440 mẫu nhiệm vụ cũ, 50 nghề và 40 ngày: tất cả tương thích.
- Gói giải nén mới: toàn bộ hash khớp; server/DB thử riêng; tạo nhân vật, mở ca, chống lệnh lặp và xuất bản lưu 54 nghề qua HTTP đạt.
- Sau phục hồi dung lượng: 1.572 file trên máy chủ đúng hash; 709 file tests/artifacts được installer loại có chủ đích. Bảy asset công khai đúng hash. Tám mẫu health đúng build/54 nghề; danh mục HTTP đầy đủ và có bốn nghề mới. Game/live active đúng cwd, bridge inactive.
- DB không ở chế độ recovery, postmaster vẫn là tiến trình từ 30/09. Giao dịch tạo bảng TEMP/ghi một dòng/đọc/ROLLBACK đạt; không ghi thử vào dữ liệu người chơi. Không có dấu lỗi mới trong cửa sổ journal sau 15:17 được kiểm tra.

Giới hạn kiểm thử: test rollback với bản rất cũ `_rel1431` không đạt vì bản đó không nhận danh mục 54 nghề; đây là đường quay lui không được hỗ trợ. Hai assertion chi phí bỏ dở cũ đã tái hiện lỗi trên baseline 2.0.7 trước đợt này, không tính là đạt. Minifier giữ cảnh báo khóa lặp trong thư viện bundle Phaser đã có trước.

## Sự cố dung lượng trong phát hành

Bản sao lưu mới tạo trước triển khai đạt 3.840.680.275 byte và `pg_restore --list` đọc được, nhưng cộng với giải nén release đã làm filesystem `/` đầy. Từ 15:12:34 nginx báo `No space left on device`; sau chuyển bản, tải nội dung lớn bị cắt và một số kết nối bị reset. Kiểm tra health nhỏ vẫn trả OK nên kiểm chứng đầy đủ tài nguyên đã phát hiện sự cố.

Đã xóa đúng hai tệp của đợt này: `/root/mnl-backups/pre-2.1.0-careers-20261013.dump` và `/tmp/mnl-2.1.0-careers-aba3f22e.zip`, sau khi đối chiếu đường dẫn/kích thước. Không xóa backup cũ, release cũ hoặc dữ liệu game. **Bản sao lưu mới nói trên không còn được giữ trên server.** Các backup tự động cũ còn nguyên, gồm `phocochuyen-20261012-204831.dump` (3.741.560.009 byte). ZIP triển khai vẫn còn local.

Sau giải phóng, HTTP tải đủ 1.826.002 byte nội dung, asset khớp hash và DB ghi được trong giao dịch TEMP hoàn tác. Dung lượng trống tại kiểm tra là 3.900.153.856 byte (~3,6 GiB), filesystem vẫn 98%; DB khoảng 44 GB. Cần dọn theo chính sách lưu trữ đã thống nhất hoặc mở rộng ổ đĩa. Không tự xóa thêm backup/release của các đợt khác. Lần phát hành sau phải kiểm tra dung lượng cho cả backup dự kiến và dung lượng giải nén trước khi tạo tệp; ưu tiên lưu backup ngoài ổ production.

## Vận hành và quay lui

Không hạ về 2.0.7: bản cũ không chấp nhận bốn ID nghề mới hoặc tiến độ bậc mở rộng. Dùng mã tương thích 2.1.x hoặc sửa tiến, không phục hồi DB cũ để quay lui mã.

Script tắt chứng chỉ `/root/mnl-business-licenses-disable.sh` đã cập nhật guard 2.1.0, lưu bản trước riêng, kiểm `bash -n` và chưa chạy. Hai cờ OFF vẫn chỉ tắt cơ chế chứng chỉ/kiểm tra.

MANIFEST gốc được tải từ release đang chạy; LIVE_BASE và mốc compatibility cập nhật đúng source gói. PostgreSQL thử trên máy phát triển đã dừng sau khi hoàn tất kiểm tra. Báo cáo JSON, log và ảnh ở output cục bộ; không commit dữ liệu tài khoản hoặc thông tin đăng nhập.
