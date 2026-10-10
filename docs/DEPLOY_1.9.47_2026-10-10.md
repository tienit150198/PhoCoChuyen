# Phát hành 1.9.47 — 10/10/2026

Hoàn tất 22:41:17 giờ Việt Nam tại https://phocochuyen.io.vn. Hai unit game/live active trong `/opt/mot-ngay-lam-nghe/releases/1.9.47-20261010224014`.

- Source `1bfb627456f7e0e3290f6ea975b097d26925c8c6`, base manifest `9f52df18`, manifest mới lưu tại `43cca849`.
- Gói 91.118.796 byte, SHA256 `4c0181c650b906f8ef1c62eaa8b7714a655b10a932fd259adc0b6b40971deb3d`; 1.936 file, 18 đổi, 2 minify, không xóa.
- Trước rollout xác minh 1.318 file runtime cũ. Backup `/root/mnl-backups/before-1.9.47-20261010-223259.dump`, 4.145.480.624 byte; pg_restore --list đạt, chưa thử khôi phục toàn bộ.
- 44 test tích hợp mục tiêu đạt; 7 test Top lỗ đạt gồm trì hoãn writer qua ranh giới tuần. 10 test gate tương thích đạt. 10 test renderer/hồi quy UI đạt; Chromium/WebKit 320/390/1280 đạt; Safari 312/312 đạt. npm check có lỗi launcher đường dẫn Windows từ trước; script Safari trực tiếp đạt.
- Schema 36, bảng/index sổ tuần và con trỏ đã có. API Top lỗ trả đúng tuần/tier. Hai dịch vụ đúng cwd; public assets khớp gói; kéo co vẫn minimum=30 và 5 mức giải đúng. Thông báo Python/JS giữ nguyên từng byte.
- Health khi rolling: 30 mẫu đều 200 (6 bản cũ, 24 bản mới), chỉ đại diện các mẫu kiểm tra.
- Sau rollout chủ game yêu cầu thêm số lời/lỗ hiện có vào tuần đầu; xử lý tiếp ở 1.9.48.
