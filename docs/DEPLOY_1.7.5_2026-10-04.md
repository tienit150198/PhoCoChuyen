# Phát hành 1.7.5 — nhà chung

Rolling deploy hoàn tất 18:39:04 UTC+7 ngày 04/10/2026. Build `1.7.5+b02de58106ce`; release `/opt/mot-ngay-lam-nghe/releases/1.7.5-20261004183807`. Game và live active, bridge inactive. Live xác nhận `home: True`; không thêm nghề, vẫn 41 nghề, không đổi schema.

- Cùng nhà, cùng phòng: hiển thị người kia, di chuyển, ôm, hôn, thả tim; thu hồi hiện diện sau đổi nhà/ly hôn/chặn; xử lý nhiều tab và nối lại mạng.
- Tường/sàn lấy căn nhà làm nguồn chung, đổi từ hai phía; lưu giao dịch và biên nhận nguyên tử, giữ quyền mua riêng. Nội thất và kết cấu sửa sang hiển thị nhất quán, cập nhật qua live và polling dự phòng.
- Đã kiểm tra hai tài khoản trong trình duyệt: avatar, ba tương tác hai chiều, đổi phòng, đóng/mở nhà, đổi tường hai chiều, cất đồ một bên biến mất bên kia. Không có lỗi console. Crowd redraw chờ kết thúc kéo/nhấn/lưu, có kiểm tra hồi quy.

Kiểm chứng: 45 kiểm tra live (19 nhà chung), 18 kiểm tra transaction trang trí chung; 121 kiểm tra trang trí/storage, 47 scaling/archive/resilience (3 skip dự kiến). Kiểm tra tích hợp cuối 33 ca qua. Các harness JavaScript home_crowd, home_redraw, home_view, home_wardrobe qua; code review không còn vấn đề cần sửa. 40.800 mẫu nhiệm vụ tương thích; ZIP chạy thử trên PostgreSQL riêng và xác minh toàn bộ 1.156 hash thành công.

Gói `output/release-175/mnl-1.7.5.zip`, SHA256 `fcb2b45fe185c4f72b46ce2a79965db9681bed0ec65cf03351b149e6cf07ab4d`. Manifest chỉ thay đúng 23 file đã chọn so với gói 1.7.4. Kết quả HTTPS ở `output/release-175/production-check.json`; kết quả gói ở `output/release-175/package-verify.json`.

Rollback đã được helper xác định: dùng rolling release về `/opt/mot-ngay-lam-nghe/releases/1.7.4-20261004174805` với bridge port 8767. Không đụng dịch vụ/website khác.
