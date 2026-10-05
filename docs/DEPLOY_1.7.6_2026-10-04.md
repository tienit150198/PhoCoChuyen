# Phát hành 1.7.6 — xưởng handmade, gấu bông trước

Rolling deploy hoàn tất 19:05:51 UTC+7 ngày 04/10/2026. Build `1.7.6+58943e969ae2`; release `/opt/mot-ngay-lam-nghe/releases/1.7.6-20261004190454`. Game và live active; bridge inactive; live khởi động bằng PostgreSQL, có `home: True`. Vẫn 41 nghề, schema không đổi.

Gom toàn bộ handmade trong một gói: gấu bông đo 24×30, cắt hai mặt, may viền, nhồi bông, gắn mắt/mũi/nơ và dấu riêng; công đoạn cho gốm/vòng tay/thiệp; bàn phím, bản nháp, thanh toán cuối và hình thành phẩm thống nhất. Giữ các thay đổi đã triển khai trong 1.7.5. Không sửa thông báo trong game.

## Kiểm chứng

- 35 kiểm tra handmade, outings, guides qua; harness JavaScript craft_workbench qua. Chạy lại 19 kiểm tra handmade/outings và harness trên nguồn đóng gói thành công.
- Trình duyệt 390px: đo đúng kích thước; kéo trọn đường cắt/may; kéo bông và nhồi bằng nút; gắn mặt/nơ/dấu; đóng và tải lại đúng bước; hủy thanh toán giữ thành phẩm. Gấu được cất, ví 500→478. Qua luồng game đầy đủ: Gia đình → DIY → Handmade, làm thiệp bằng bàn phím và hộp thanh toán thật; ví 478→456, hai món trên kệ. Không có lỗi console.
- Review độc lập: đã sửa validation số nguyên quá lớn, thành phẩm ba loại cũ thiếu hình và màu/họa tiết của bản nháp bị ghi đè sau reload. Không còn lỗi chặn.
- Đối chiếu 40.800 mẫu nhiệm vụ, 41 nghề, ngày 1–40, slot 0–11: tương thích.
- ZIP chạy thử qua HTTP trên PostgreSQL riêng, kiểm tra 1.164 hash thành công. Sau deploy: 6 mẫu HTTPS health HTTP 200 và 5 file handmade bằng đúng byte trong ZIP.

## Gói và vận hành

`output/release-176/mnl-1.7.6.zip` — SHA256 `049d0af7aa82642a95266be3a3be78a4fc156d611b4ee8ea5d6769856dee872c`. Gói lấy nguồn sạch 1.7.5, chép đúng 16 file trong `output/release-176/changed-files.json`. Sau đóng gói chỉ cập nhật tiến độ tài liệu kế hoạch ở workspace; runtime trùng gói.

Kết quả: `output/release-176/package-verify.json` và `output/release-176/production-check.json`.

Deploy bằng helper rolling, bridge port 8767. Không đụng website/dịch vụ khác. Bản trước: `/opt/mot-ngay-lam-nghe/releases/1.7.5-20261004183807`.

**Tương thích rollback:** sau khi người chơi đã lưu gấu hoặc metadata `work`, không quay thẳng về validator 1.7.5. Bản rollback phải giữ `game/craft_work.py` cùng khả năng đọc `teddy`/`work` của `game/outings.py`, hoặc dùng bản sửa tiến lên. Không xóa thành phẩm để rollback. Bản nháp nằm trên thiết bị theo username và loại món; chưa đồng bộ giữa thiết bị.
