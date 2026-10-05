# Phát hành 1.7.8 — tiệm, ghé thăm, nhà và chat

Người dùng yêu cầu rõ “ok deploy + thông báo mới đi”, sau đó xác nhận tiếp tục deploy. Hoàn tất lúc **23:21:10 UTC+7 ngày 04/10/2026**.

- Release: `/opt/mot-ngay-lam-nghe/releases/1.7.8-20261004231648`.
- Build: `1.7.8+25b49d8681f6`.
- PostgreSQL schema: **22**. Game và `mnl-live` active; bridge inactive. Live bật chat, home và visits.
- Gói: `output/release-178/mnl-1.7.8.zip`.
- SHA256: `72014728389dd0468e4e6b50b61b10d6d07988c04ac7a7a52efa8a1622fa7dde` (server khớp).

## Phạm vi

Nhân viên tự động Quầy riêng/Sổ tiệm làm liên tục và offline tới khi thiếu hàng hoặc quỹ; quầy/menu không giới hạn số lựa chọn, giá từng món và thiết bị tăng tốc. Ghé chỗ làm, đặt dịch vụ, đánh giá sau hoàn thành. Mời bạn ghé nhà hoặc ở chung lâu dài. Reply tin nhắn, đồng bộ tên nhân vật không đổi username. Tách bể cá và sửa bản lưu café thiếu `bar_pace`.

Thông báo Có gì mới có 11 mục, kèm xưởng gấu bông và gia đình/cử chỉ đã phát hành yên lặng ở 1.7.5–1.7.7. Có bản tiếng Anh. Không đưa nội dung thay đổi xác suất sự cố vào thông báo.

**Chưa sửa lỗi vốn chủ quầy không liên kết quỹ nghề của người chơi làm thuê** (Bạch Du Dương/Yuika). Không quảng bá tính năng nhân viên tự động như bản sửa cho cơ chế thuê người chơi. Các nghề mới vẫn ở đợt riêng.

## Kiểm chứng

- Nguồn sạch lấy từ gói 1.7.7, chỉ chép 110 file được liệt kê trong `output/release-178/changed-files.json`; các file còn lại giữ đúng byte bản trước.
- 371 kiểm tra tính năng: 369 qua, 2 bỏ qua do thiếu cây mã lịch sử 1.5.2. 12 bộ JavaScript qua; 245 file JS parse được.
- So sánh 40.800 mẫu nhiệm vụ, 41 nghề, ngày 1–40: tương thích với 1.7.7.
- Sau sửa lỗi migration: 60 kiểm tra PostgreSQL/tên/live qua; thêm hai regression test chạy lại trên nguồn đóng gói đều qua.
- ZIP cuối: 1.210 hash source/asset khớp, giải nén chạy HTTP trên PostgreSQL riêng; tạo nhân vật, mở nghề/ngày, replay request và xuất bản lưu thành công.
- Production: 6 mẫu HTTPS health đúng build, 13 asset bằng đúng byte ZIP. Có gì mới trả bản 1.7.8 và 11 mục. Báo cáo `output/release-178/production-check.json`.
- Kiểm tra trình duyệt tài khoản đang mở: nút Chat trở lại ở menu, mở được danh sách tin nhắn. Cài đặt → Cách chơi → Xem các cập nhật mới hiện đúng 1.7.8; đã quan sát ảnh thông báo.
- Log game/live sau 23:21:10 không có ERROR, Traceback, deadlock, Internal error hoặc Database error tại thời điểm kiểm tra. Live có người chơi kết nối lại, không có cut.

## Sự cố và khắc phục trong lúc phát hành

Lần thử đầu dùng gói SHA `8e323005ef200c119723eb383808b0d73f434f60cb630648c6d103e50215c7ff`, chưa chuyển nginx khỏi 1.7.7. Migration sửa tên giữ DDL relation locks rồi chờ session row đang được người chơi sửa, tạo deadlock với thao tác cập nhật account. Các yêu cầu bị chặn tạm thời; người dùng báo mất nút Chat. Giao dịch bị rollback, bridge dừng, bản cũ tiếp tục chạy.

Đã tái hiện đúng deadlock bằng hai kết nối PostgreSQL. Sửa `pg_schema.ensure`: commit DDL ở schema 21 trước, rồi sửa tên trong giao dịch riêng; advisory lock theo schema tuần tự hóa các lần khởi động, kiểm tra lại version sau khi chờ. Nếu sửa tên lỗi có thể chạy lại từ 21. Metadata chỉ lên 22 sau khi sửa tên thành công. Các test kiểm tra không giữ DDL lock khi đợi người chơi và khả năng tiếp tục sau lỗi đã thất bại trước sửa, qua sau sửa.

Lần thử thứ hai xử lý tên khoảng 3 phút 31 giây vì đọc bản lưu lớn, không còn khóa chéo. Đã tạm giữ vòng chờ health và tự tiếp tục khi bridge khỏe để tránh hủy migration. Bridge khỏe lúc 23:20:19, game chính khỏe lúc 23:20:48, live restart và deploy kết thúc 23:21:10. Không khẳng định toàn bộ đợt phát hành không gián đoạn vì lần đầu có chặn database.

## Sao lưu và lưu ý vận hành

Sao lưu hoàn chỉnh trước deploy: `/opt/mot-ngay-lam-nghe/backups/before-1.7.8-20261004-fast.dump`, 10.627.293.480 byte, `pg_dump -Fc -Z0`; hoàn tất 23:07:08 và `pg_restore --list` đọc được catalog. Bản sao đầu bị SSH ngắt khi chưa xong, đuôi `.partial`, **không dùng để phục hồi**. Lần sau backup và deploy chạy trong tmux độc lập với kết nối SSH.

Không dùng release thử lỗi `1.7.8-20261004230726`. Bản 1.7.7 vẫn được giữ nhưng rollback ứng dụng cần đánh giá trạng thái kinh doanh/trang bị và đơn người chơi mới; không tự hạ schema hay phục hồi database cũ làm mất tiến trình sau sao lưu. Ưu tiên sửa tiếp nếu phát sinh lỗi.

PostgreSQL thử nghiệm local đã dừng sau kiểm tra. Không tạo commit hoặc push trong đợt phát hành này.
