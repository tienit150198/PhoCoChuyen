# Phát hành 1.7.15 — 05/10/2026

Người dùng đã cho phép deploy và yêu cầu thông báo đúng bốn dòng. Bản đang chạy: `/opt/mot-ngay-lam-nghe/releases/1.7.15-20261005112207`, game build `1.7.15+1e05accb2db4`.

- Gói phát hành SHA256: `fb6e109db4b56588c8a4166f35142f10e739619a1f4f9bce312b34cbe399de80`.
- Sao lưu PostgreSQL trước triển khai: `/root/mnl-backups/pre-1.7.15-20261005-111317.dump`, 1.767.077.052 bytes; đọc kiểm tra toàn bộ bằng pg_restore thành công.
- Chuyển phiên bản sau khi dừng reducer cũ; từ bắt đầu dừng tới health thành công 13,09 giây. Giữ schema 23.
- Thị trường có seed riêng cố định và mốc `1791174150`; kiểm tra cùng cấu hình trên 9 process game (master + workers) và process live. Không ghi seed vào báo cáo. Một ngày thị trường = 3.600 giây, phiên giá = 600 giây.
- Game, live, selfheal active; bridge inactive. Live nối lại 81 kết nối trong lần kiểm tra sau khởi động. Không thấy Traceback, ERROR, Exception hoặc HTTP 500/502/503 trong journal được kiểm tra sau cutover.
- Gói được giải nén và chạy độc lập với PostgreSQL: toàn bộ 1.286 hash đúng, khởi động, assets, bootstrap, profile, work/start day, chống lặp lệnh và export đều đạt. Thêm 83 tests Python từ staging và Node whats_new đạt.
- HTTPS health sáu lần: 319,6 / 94,3 / 89,2 / 101,6 / 96,1 / 96,5 ms. Đây là health, không đại diện độ trễ mọi thao tác.
- Tám assets public theo URL có hash khớp gói, gồm đầu tư, quầy, hội chợ và thông báo. Nội dung thông báo 1.7.15 đúng bốn dòng yêu cầu, dùng dấu gạch đầu dòng.

Báo cáo: `output/release-1715/package-check.json`, `output/release-1715/production-check.json`. Các kết quả benchmark trước triển khai trong tài liệu lag và hội chợ; không coi là cam kết hết lag trên mọi thiết bị.

Không rollback reducer cũ trên dữ liệu đã được ghi bởi 1.7.15 (coin realtime và metadata hội chợ mới). Nếu có sự cố cần sửa tiếp trên phiên bản tương thích hoặc khôi phục có kiểm soát với bản sao lưu.
