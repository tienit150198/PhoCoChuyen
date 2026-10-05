# Phát hành 1.7.13 — giảm lag

Chủ game cho phép deploy bản sửa lag, sau đó làm đợt nghề mới và TT99. Đợt nghề mới không nằm trong gói này.

## Gói phát hành

- Nguồn sạch từ gói đã phát hành 1.7.12, chép đè đúng 12 file trong `output/release-1713/changed-files.json`; không lấy các thay đổi khác trong worktree.
- Tối ưu ghi archive theo batch trong cùng transaction; bỏ lượt đọc/snapshot lặp khi ghé nơi làm. Chat bỏ render danh sách không đổi, Nhà tách tải chợ thuê khỏi khóa thanh toán.
- Version 1.7.13; schema vẫn 23. Giữ byte server, schema, toàn bộ module live và hai file Có gì mới. Không phát lại quà.
- ZIP: `output/release-1713/mnl-1.7.13.zip`, 30.169.483 byte, SHA256 `1d09459cfb3adec7a5da7a1f7a42ededd06f7a9dd5c2f0e8c3143860fceeb917`.

## Kiểm tra trước chuyển bản

- 94/94 kiểm tra PostgreSQL và 40/40 kiểm tra Node chạy từ đúng cây nguồn staging đều đạt.
- So sánh 40.800 nhiệm vụ của 41 nghề giữa 1.7.12 và 1.7.13: không thay đổi nhiệm vụ đã sinh.
- Kiểm ZIP: đủ 1.261 hash nguồn/asset, server từ gói giải nén khởi động trên schema PostgreSQL riêng; HTTP tạo nhân vật/mở nghề/ngày, chặn nghề khóa, retry đúng receipt, export save đều đạt.
- Script production xác minh toàn bộ manifest và source live/schema/thông báo không đổi trước khi sao lưu và chuyển bản.

## Cách chuyển bản

`output/deploy-1713.py` chạy trong tmux `mnl1713`, log `/tmp/mnl1713-deploy.log`. Tạo pg_dump riêng trước khi chuyển. Dùng rolling release với bridge pool max 3; giữ toàn bộ release cũ (`KEEP=999`). Dịch vụ live giữ nguyên PID vì source/schema tương thích và không đổi. Sau chuyển kiểm tra health, schema và PID live.

## Kết quả production

- Hoàn tất 08:31:29 UTC+7 ngày 05/10/2026, `EXIT=0`; release `/opt/mot-ngay-lam-nghe/releases/1.7.13-20261005083032`, build `1.7.13+680f6b7be623`.
- Sao lưu `/root/mnl-backups/pre-1.7.13-20261005082507.dump`, 1.757.120.734 byte. Rolling mất 58,09 giây, có bridge phục vụ trong khi canonical chuyển bản; không dừng chat.
- Game health OK, schema 23. PID live không đổi; live health OK, uptime 3.859 giây, cut=0 ở lúc hoàn thành.
- Sáu mẫu health từ domain đều đúng 1.7.13; hash trong HTML và nội dung asset thường/hashed đều khớp với gói cho chat, Nhà, Có gì mới. Thông báo vẫn 1.7.10 với đúng ba dòng đã được duyệt.
- Kiểm tra public lưu tại `output/release-1713/production-check.json`; báo cáo server `/root/mnl-deploy-1713.json`.
- Không đưa 9 nghề mới hoặc TT99 vào bản này. Thiết kế đợt mới ở `docs/superpowers/specs/2026-10-05-new-careers-tt99-design.md`, chờ người dùng duyệt trước triển khai.
