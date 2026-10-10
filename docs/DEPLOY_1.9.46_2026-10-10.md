# Phát hành âm thầm 1.9.46 — 10/10/2026

Hoàn tất 22:18:35 giờ Việt Nam tại https://phocochuyen.io.vn, production 103.195.238.178. Game và live service active tại `/opt/mot-ngay-lam-nghe/releases/1.9.46-20261010221732`.

- Chủ game yêu cầu khôi phục ít nhất 30 trận hợp lệ trong tuần trước khi xếp top tỷ lệ thắng. Tiền thưởng và danh hiệu không đổi. Trận đã chơi vẫn tính theo tuần hiện tại.
- Chủ game yêu cầu giữ nguyên Có gì mới, deploy âm thầm. Hai file Python/JS thông báo giữ nguyên từng byte so với 1.9.45; không tạo entry mới.
- Source `fcae078af1739d056da71d419423eb730c780202`, base `a8f2061a`, manifest live lưu riêng tại `9f52df18`.
- Gói `/root/mnl-1.9.46.zip`, 91.102.345 byte, SHA256 `0efc3d5994afdbf176d7f33169955f244d9771d20a6935c3192a8128b365ef4f`. 1.929 file, 9 đổi, 1 minify, không xóa file.
- Đã xác minh 1.317 file runtime bản cũ khớp manifest trước đóng gói. Không thay schema, không sửa trực tiếp dữ liệu người chơi. Giữ release cũ và backup đợt 1.9.44.
- 11 test PostgreSQL bảng top đạt; hồi quy xác nhận 29 trận không xếp hạng/nhận giải, trận thứ 30 đủ điều kiện; đã thấy test fail trước sửa. Suite UI đạt; gate tương thích 10 test đạt và LIVE_REF được cập nhật.
- Sau rollout, API minimum=30, mọi hàng top có played>=30, đúng năm mức thưởng. Public assets bảng top/thông báo khớp gói; cả hai unit đúng cwd, live health OK.
- Lấy mẫu health lúc rolling: 29 mẫu, tất cả 200 (6 mẫu 1.9.45, 23 mẫu 1.9.46). Không khẳng định bao quát mọi request.
- PostgreSQL dùng kiểm thử chỉ nghe localhost và đã dừng. Dữ liệu test nằm trong output, không commit.
