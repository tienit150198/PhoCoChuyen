# Deploy bản sửa hội chợ đã chơi thử local

Đã deploy theo yêu cầu ngày 05/10/2026, hoàn tất lúc **16:59:29 (UTC+7)**. Không tạo thông báo mới.

- Bản phục vụ: `1.7.15+840d67b91f5d`.
- Release: `/opt/mot-ngay-lam-nghe/releases/1.7.15-fair-local-fixes-20261005165705`.
- Bản trước: `/opt/mot-ngay-lam-nghe/releases/1.7.15-fair-stability-20261005144053`.
- SHA-256 gói: `e9593d32b16cca9c03d1f8ea9e38390df5eed33b252d942e934580853f99fe25`.

## Nội dung

Chỉ bốn tệp runtime được thay: `fair-knife.js`, `fair.js`, `fair-scratch.js`, `fair.css`. Bổ sung nhận phóng dao ngay khi nhấn, giữ vị trí cắm/nảy dao liên tục, vòng ôm cổ chai và hiện riêng từng vòng trúng, bảo toàn canvas vé cào khi đóng/mở trong lúc chờ mua vé. Chi tiết tái hiện và đo local: [FAIR_LOCAL_REVIEW_2026-10-05.md](FAIR_LOCAL_REVIEW_2026-10-05.md).

Toàn bộ backend, schema, `app.js`, trang chủ và nội dung thông báo khớp byte với release trước. Không đưa thay đổi Phaser hoặc công cụ đo local vào gói. Backend build vẫn là `1150f8b5b8ae1f9d51f0`.

## Kiểm tra phát hành

- 1.326 tệp trong ZIP khớp manifest; chạy được server từ ZIP với PostgreSQL test; tạo nhân vật, mở ngày, xuất save và gửi trùng lệnh qua HTTP đúng.
- So 40.800 nhiệm vụ, 41 nghề, ngày 1–40: tương thích hoàn toàn.
- Gói JS/CSS đã nén: Chromium/WebKit đạt 6 luồng phóng dao mỗi engine; 36 kiểm tra hình học và kết quả ném vòng ở 390/1280 px đạt.
- Rolling release qua bridge, kiểm tra health trước mỗi lần chuyển; canonical trở lại cổng 8765 và bridge đã dừng.
- Giữ `mnl-live` đang chạy vì mã live/backend không đổi; PID trước/sau đều `2595469`. Giữ các release cũ cho rollback và thư mục làm việc của live.
- HTTPS phục vụ đúng fingerprint và hash của bốn tệp sửa; `app.js` và thông báo không đổi; tài nguyên có cache immutable.
- Chromium/WebKit mở được app production, không lỗi JavaScript trong lượt kiểm tra.

## Cửa sổ log lúc chuyển bản

Từ lúc bắt đầu deploy đến lúc kiểm tra (147 giây): **3.290 request, 0 HTTP 5xx, 0 traceback**. Game, live và self-heal đều active; bridge inactive.

1.665 lệnh `/api/command`: p50 **151 ms**, p95 **467 ms**, p99 **689 ms**; gồm 1.659 HTTP 200, 5 HTTP 400, 1 HTTP 409. Đây là cửa sổ gồm cả thời gian chuyển bản, không phải đối chứng để kết luận tốc độ backend cải thiện. Bản này sửa tương tác/hình ảnh ở client; không tuyên bố đã hết mọi nguyên nhân lag.

## Bằng chứng và rollback

Các tệp trong `output/release-1715-fair-local-fixes/`: `package.json`, `package-verified.json`, `task-compat.txt`, `browser/knife-bundle.json`, `browser/ring/results.json`, `production-https.json`, `production-browser.json`, `production-smoke.json`, `production-api-window.json`, `deployed.json`, `deploy.log`.

Nếu cần rollback, dùng rolling release trỏ tới đường dẫn bản trước ở trên; frontend của tab cũ vẫn có tài nguyên theo mã băm trong kho dùng chung. Đợt này không thay đổi dữ liệu hoặc cấu hình thị trường.
