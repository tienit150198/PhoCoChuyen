# Observability Implementation Plan

**Goal:** Cài Firebase Analytics/Performance riêng và chuẩn bị xác minh Search Console, giữ log game hiện có.

**Architecture:** Cấu hình whitelist từ env được nhúng thành meta bởi WebAssets; CSP mở đúng endpoints khi có cấu hình. Module observability khởi động qua telemetry sau frame đầu, chỉ tải SDK trên origin production sau consent.

**Tech Stack:** Python standard library, ES modules, Firebase web SDK 12.19.0, node:test/unittest.

- [x] Kiểm thử trước: tests/test_observability.py và tests/observability.mjs. Chạy `python -m unittest tests.test_observability -v` và `node --test tests/observability.mjs`, xác nhận các chức năng mới chưa tồn tại.
- [x] game/observability.py: whitelist config public, escape meta, CSP endpoints, validate site URL/verification; game/webassets.py: nhúng config và canonical.
- [x] public/js/observability.js: consent, origin guard, SDK tải bất đồng bộ, lọc event; public/js/telemetry.js: boot và thông báo loại lỗi.
- [x] public/robots.txt, public/sitemap.xml: chỉ public origin; public/privacy.html: mô tả Analytics và lựa chọn thống kê.
- [x] .env.example và docs/OBSERVABILITY.md: cấu hình, event dictionary, đường dẫn dashboard, kiểm tra log và quy trình kích hoạt.
- [x] Tạo Firebase project riêng và web app, Analytics property/web stream; lấy config từ UI. Search Console: tạo URL property và lấy verification meta. Đã đặt múi giờ Việt Nam, stream URL và 3 custom dimensions.
- [x] Chạy `python -m unittest tests.test_observability tests.test_telemetry_js tests.test_http tests.test_webassets -v`, `node --test tests/observability.mjs`, `node scripts/check_js.mjs`; kiểm tra diff và thực trạng external.
- [ ] Search Console: xác minh property và submit sitemap sau deploy.
- [ ] Kích hoạt server bằng rolling release khi có quyền truy cập; xác minh HTTP/CSP, Analytics Realtime và Search Console. Ghi rõ phần bị chặn nếu chưa có quyền truy cập.
