# Deploy phóng dao kỹ năng và vòng liền nét — 05/10/2026

Hoàn tất lúc **19:23:38 UTC+7**, theo yêu cầu deploy của người dùng. Không thêm thông báo trong game.

- Release game: `/opt/mot-ngay-lam-nghe/releases/1.7.15-fair-skill-final-20261005192026`.
- Public version: `1.7.15+dbb84f991e77`; engine build: `420811703f97a7506ffc`.
- ZIP SHA-256: `adbce5c3e297ebc81d91f56efe308d2100965bc4752535fcdd3efe9a14d6bad0`.
- Live/chat giữ reader tương thích: `/opt/mot-ngay-lam-nghe/releases/1.7.15-fair-skill-compat-20261005192026`, build `8313749c6298769fcc90`. Live không tạo lượt phóng dao; reader hiểu đầy đủ các lượt kỹ năng mới. Giữ nguyên PID live trong bước cuối để tránh ngắt kết nối thêm một lần.
- Đây cũng là điểm rollback hợp lệ sau khi đã sinh `fair_kn_skill`. Không rollback thẳng về bản gentle cũ.

Gói nền là bản production gentle đã xác minh. Chỉ bốn file runtime thay đổi: `game/fair.py`, `game/fair_knife.py`, `public/js/v4/fair-knife.js`, `public/css/fair.css`; các file test/tài liệu liên quan được cập nhật kèm. Đối chiếu byte frontend sau khi đảo đúng thay đổi nội dung xác nhận không có sửa đổi giao diện không liên quan. Tính năng admin và `whatsnew-data.js` giữ nguyên hash.

Đã kiểm tra trước deploy:

- 167 test trên gói phát hành: 166 đạt, một test đọc save phiên bản trước tạm bỏ qua vì chưa cấu hình đường dẫn bản cũ. Test đó sau đó được chạy riêng với bản production trước, đạt. Một lần chạy Python 3.12 của test này thiếu psycopg trong subprocess; chạy lại bằng môi trường Conda có dependencies đạt.
- Bốn lượt kiểm tra tương thích qua subprocess đạt: bản mới ghi lượt → bản cầu đọc/hoàn thành/chơi tiếp và xét va chạm đúng; bản cũ ghi lượt → bản cuối đọc/hoàn thành và chuyển kỹ năng đúng. Bản cầu không tự tạo metadata kỹ năng khi còn các worker cũ.
- Gói giải nén độc lập khởi động được trên PostgreSQL, thực hiện API hồ sơ/chọn nghề/mở ngày, xuất save và replay yêu cầu không trả thưởng hai lần. 1.334 hash khớp manifest.
- Các kiểm tra local khác, gồm browser, hình học và 328 tình huống va chạm: xem `FAIR_KNIFE_SKILL_RING_FIX_2026-10-05.md`.

Đã xác minh sau deploy:

- Rolling hai giai đoạn hoàn tất, exit 0. Game main PID 2958277 và tám worker đều ở release cuối; live PID 2957011 ở reader tương thích; dịch vụ bridge đã dừng.
- Game health `ok`, live health `ok`. Live ghi nhận 75 kết nối, 99 player, 46 room tại thời điểm chụp.
- 3.269 request trong cửa sổ triển khai: **0 HTTP 5xx, 0 traceback** ở game/bridge/live.
- Chín asset phục vụ qua HTTPS khớp SHA-256, có cache immutable, bao gồm module phóng dao, CSS hội chợ, app, vé cào, admin và thông báo. Public fingerprint đã đổi sang bản mới.
- Bảy test kỹ năng chạy trực tiếp bằng code đã cài trên server, trạng thái giả lập trong bộ nhớ: đạt. Không sửa dữ liệu tài khoản người chơi để thử.

Bằng chứng: `output/release-1715-fair-skill/` gồm package/prepared/deployed JSON, kiểm tra HTTPS, cửa sổ API, log rolling, test gói, test tương thích và test save cũ. SSH vận hành được đóng sau khi lấy báo cáo.
