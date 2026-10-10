# Phát hành 1.9.48 và số dư đầu tuần — 10/10/2026

Chủ game yêu cầu lấy số lời/lỗ Hội chợ sẵn có đưa vào Top lỗ hiện tại. Tuần 05–11/10 có mốc từ số dư đang lưu; từ thứ Hai 12/10 chỉ tính giao dịch phát sinh trong tuần mới. Không đổi ví, save, lịch trao danh hiệu hoặc Có gì mới.

## Release

- Hoàn tất rolling 23:06:39 giờ Việt Nam tại https://phocochuyen.io.vn, production `103.195.238.178`. Game và live active đúng cwd `/opt/mot-ngay-lam-nghe/releases/1.9.48-20261010230537`.
- Source `43d6cc129742c17c1f33435d31d3f2a4eb74ad58`, base live manifest `43cca849`, manifest mới `ff76378b`.
- Gói `/root/mnl-1.9.48.zip`: 91.123.257 byte; SHA256 `a3010393724f77b385c2dde2c983070a8be3ffcde4e3798c8371baa49503c53e`. 1.938 file, 10 đổi, 1 minify, không xóa. Schema giữ 36.
- Backup trước thay đổi: `/root/mnl-backups/before-1.9.47-20261010-223259.dump`, đã xác minh mục lục. Giữ nguyên release cũ.
- 29 mẫu health khi rolling đều 200 (6 bản cũ, 23 bản mới). Không khẳng định bao quát mọi request. Hai file thông báo Python/JS giữ nguyên từng byte.

## Seed và kiểm tra

- `scripts/seed_fair_loss.py --week 2026-10-05` chạy thủ công theo từng lô. Khóa toàn bộ save trong lô trước khi khóa tuần; số dư và con trỏ commit cùng nhau. Những lượt đã xử lý không bị cộng lại khi tiếp tục. Không cấp danh hiệu sớm.
- Công cụ được đưa vào thư mục riêng `/root/mnl-seed-1948` để bắt đầu lấy dữ liệu trước rollout; không thay file của release đang chạy. Tiếp tục từ con trỏ sau khi tối ưu gom cập nhật số 0 và bỏ parse JSON không có khóa fair. Bản đã triển khai chứa cùng mã cuối.
- 9 test PostgreSQL của Top lỗ đạt; sau tối ưu, 3 kiểm tra seed mục tiêu đạt (mốc cũ/chuyển tuần/chạy lại, rollback con trỏ cùng sổ, số dư 0/save chưa chơi và không đổi ví/save). Gate tương thích 10 test đạt; renderer 6 test đạt; Safari 312/312 đạt. UI tổng thể đã kiểm tra Chromium/WebKit ở 320/390/1280 trong 1.9.47.
- API xác nhận `fair.seeded=true`, có người xếp hạng với số lỗ cũ; public JS/CSS khớp gói. Kéo co vẫn minimum=30, năm mức thưởng không đổi; game/live health OK.
- Kiểm tra cuối lúc 23:09: seed `done=true`, đã xử lý 59.611 save và lấy 712 số dư khác 0; API có 332 người đủ điều kiện hiện tên trong Top lỗ. Sổ tuần có 713 dòng (kể cả số dư 0/phát sinh mới), chưa có hiệu ứng trao danh hiệu trước lịch.
- PostgreSQL kiểm thử chỉ nghe localhost, đã dừng; output/log/gói không commit.

Rollback giữ bảng sổ, con trỏ seed và registry hai danh hiệu Top lỗ. Không chạy lại seed cho tuần kế tiếp; công cụ từ chối tuần đã qua.
