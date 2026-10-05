# Phát hành 1.7.11 — Đầu tư

Theo yêu cầu chủ game: thêm mục Đầu tư gom Coin/Vàng, tạo tin tức trong game có chuỗi tăng/giảm nhiều ngày với đa số chiều tăng, deploy không thêm Có gì mới.

## Phạm vi

- Menu trực tiếp Đầu tư, hai thẻ tài sản cùng kích thước, giá/giá vốn/lãi lỗ và mua bán tại chỗ; tiết kiệm và nhật ký nằm trong phần mở rộng.
- Tin tức theo đợt 2–5 ngày, mục tiêu 70% đợt tăng. Vàng theo ngày thực; Coin theo ngày sống. Vàng giữ nguyên giá cũ đến 05/10/2026, bắt đầu cơ chế mới từ 06/10.
- Giữ tài sản, giá vốn, phí và lịch sử. Trạng thái coin_market_day là trường tùy chọn tương thích bộ đọc 1.7.10.
- Hai file thông báo bằng byte bản 1.7.10; không phát quà lần nữa.

## Kiểm tra

- Backend trên staging: 58 tests, 56 qua và 2 kiểm tra cây nguồn lịch sử bỏ qua vì staging không chứa bản cũ. Chạy riêng 9 market tests trong worktree có bản cũ: tất cả qua, gồm round-trip thực qua bộ đọc 1.7.10.
- Node kiểm tra UI, escape nội dung, giá giao dịch, hủy giao dịch và chống bấm trùng: qua.
- Chromium 320/390/430 px: mở trực tiếp menu, mua/bán Coin và Vàng qua HTTP, ví chưa mở Coin vẫn mua Vàng, không tràn ngang/lỗi JavaScript; tăng số vàng giữ vị trí cuộn.
- Rà soát độc lập đã sửa lỗi cuộn về đầu và đóng phần tiết kiệm khi thao tác; không còn phát hiện nghiêm trọng trong phạm vi thay đổi.
- 16.000 ngày mô phỏng: 68,46% đợt Coin và 68,28% đợt Vàng tăng; không bảo đảm lãi mỗi ngày. Giá dài hạn được kiểm tra tránh sớm chạm trần.
- ZIP: output/release-1711/mnl-1.7.11.zip, 30.120.274 byte, SHA256 f2861e84d0c02206442412a53fe4e5bf9b24609a34aa70de056ef201a25af121.
- 13 file thay đổi trên nguồn sạch 1.7.10. Verify package kiểm tra đủ 1.242 hash, khởi động PostgreSQL riêng và giao dịch HTTP/replay/export bản lưu đều đạt.

## Triển khai

Rolling release bằng tmux mnl1711; log /tmp/mnl1711-deploy.log. Không đổi schema PostgreSQL.

Hoàn tất 06:31:30 UTC+7 ngày 05/10/2026, EXIT=0. Release /opt/mot-ngay-lam-nghe/releases/1.7.11-20261005063033, build 1.7.11+dd8025ca6f42.

- Sáu mẫu HTTPS health 200/ok đúng version; năm asset (gồm file thông báo) khớp byte ZIP. Thông báo giữ nguyên 1.7.10.
- Game/live active; live khởi động lại có chủ đích lúc 06:31:30, nghe lại lúc 06:31:34. Health sau đó ok, 23 kết nối/22 người, cut=0, NRestarts=0 tại mẫu đọc.
- Chứng cứ: output/release-1711/package-check.json, production-check.json và output/playwright/investment/report.json.
