# Phát hành 1.9.45 — 10/10/2026

Hoàn tất lúc 22:05:36 giờ Việt Nam trên https://phocochuyen.io.vn (103.195.238.178). Game và live service active, cùng cwd `/opt/mot-ngay-lam-nghe/releases/1.9.45-20261010220433`.

- Theo chủ game: bỏ ngưỡng 30 trận ở giải kéo co tuần, xếp tỷ lệ thắng cho mọi tài khoản có trận hợp lệ. Giữ tiền thưởng, danh hiệu, quyền riêng tư và tie-break. Trường API minimum=1 giữ tương thích với client cũ; người chưa chơi không có tỷ lệ để xếp hạng.
- Có gì mới gồm đúng bốn mục: sàn đấu giá đẹp hơn, vật dụng tăng khách/thu nhập, vào Chợ đen miễn phí, top kéo co giải nhất 2 triệu xu. Dùng cơ chế hiện một lần cho người chơi quay lại hiện có.
- Source `ee2bc1d7a9e482ddf1ee5d0e30e9083c828ef510`; base `2823001e`; manifest mới commit `a8f2061a` là base cho lần đóng gói tiếp theo.
- Gói `/root/mnl-1.9.45.zip`: 91.100.728 byte; SHA256 `648a40ed40012adbbc200c58c215e89913b1ea6c32c00993896d614fb192cb62`. Build 1.928 file, 13 file đổi, 2 file minify, không xóa file.
- Xác minh 1.315 file runtime live 1.9.44 khớp manifest trước đóng gói. Giữ release 1.9.44 để rollback; bản sao lưu database đã kiểm tra từ đợt 1.9.44 vẫn giữ nguyên. Đợt này không thay schema hay sửa trực tiếp dữ liệu người chơi.
- 22 test PostgreSQL bảng top và thông báo đạt. Test hồi quy xác nhận người thắng 1/1 trận được đứng đầu và nhận 2 triệu, người chưa chơi không xếp hạng; đã thấy test thất bại với luật cũ trước sửa.
- Hai suite JS bảng top/thông báo đạt, 312 module đạt Safari 15, gate tương thích 10 test đạt trước đóng gói. Lần chạy test ban đầu thiếu cấu hình DB không tính là pass; đã chạy lại đủ 22 test với PostgreSQL riêng.
- Sau deploy: API minimum=1, đúng năm mức thưởng; announcement LATEST=1.9.45 với bốn mục; file public bảng top và notes khớp byte gói. Health nội bộ live OK, không có traceback trong log ngay sau chuyển.
- 29 mẫu health khi rolling, tất cả 200 (5 mẫu 1.9.44, 24 mẫu 1.9.45). Đây là lấy mẫu, không bao quát mọi request.
- Rolling giữ các release cũ, bridge pool max 3 và MemoryMax 2G. PostgreSQL test cục bộ đã dừng, dữ liệu test chỉ trong output không commit.
