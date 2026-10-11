# Phát hành hotfix 2.0.1 — 11/10/2026

Production: https://phocochuyen.io.vn. Giờ dưới đây là UTC+7.

## Bản đã triển khai

- Rolling hoàn tất **11:58:29**, exit0. HTTP và live dùng `/opt/mot-ngay-lam-nghe/releases/2.0.1-20261011115727`.
- Health: version2.0.1, build `2.0.1+683a1dccfd45`.
- Source: `4e1923c7f7759368ac13473518aab32b132046eb`, đã push main trước rollout. Commit tài liệu/manifest sau đó chỉ ghi kết quả triển khai.
- ZIP103.300.608 byte; SHA-256 `23230d45dd1ff1f88d8db83f00a6c355a6fa6fad36cc77dad60651e09ad2f62a`. File trên máy chủ trùng mã băm. Một lượt chuyển file đầu hết thời gian, gói truyền dở không được triển khai; truyền lại và đối chiếu đủ trước rolling.
- Root MANIFEST lấy trực tiếp từ current: SHA-256 `975f2f38c4625fbfba5e26581bcd13f01c0edb6ec3a241e916ab2adbdbcc2c7a`. Cả1.529 file còn trên release sau khi rolling loại tests/artifacts đều khớp.
- Baseline2.0.0 đã kiểm2.193 file trước khi dựng gói; chỉ40 file thay đổi từ source release trước, không xóa file. Gói mới có2.202 file được manifest kiểm và một MANIFEST.json.

## Nội dung

Sửa vị trí kính/mũ/màu trang phục và biên atlas nhân vật; tối ưu dựng avatar và đồng bộ peer đứng yên/ngoài màn hình; sửa tư thế bơi/ngồi thuyền và vùng lên thuyền trên cầu; cho bơi tự do về thang để lên bờ. Rương chưa nhặt tích lũy không hết hạn, gom hình theo vị trí; classic có lối ra cùng đảo để nhặt. Giảm nhẹ xác suất công an bắt khi chơi Chợ Đen, giữ điều kiện, tiền phạt và số ngày tạm giữ. Phạm vi/giới hạn ở [báo cáo QA](qa/hotfix-2.0.1-2026-10-11.md).

## Kiểm tra

- Build, TypeScript, các suite isometric/performance/living-districts đạt;347/347 JS source và347/347 JS trong ZIP đạt kiểm Safari15/iOS15.
- ZIP khởi động trên PostgreSQL riêng, thao tác profile/chọn nghề/mở ngày qua HTTP thật, replay không áp dụng lại, export đủ50 nghề đều đạt.
- Production smoke5 nhóm: health/module; giữ tiến trình khi đổi giao diện; hai guest thấy nhau qua WSS, nhận đổi trang phục; rương có số lượng tích lũy đúng và một marker mỗi vị trí. Snapshot tại lượt kiểm có29 rương ở26 vị trí, đợt hiện tại thêm5. Không nhặt thưởng hoặc gửi góp ý mới trên production.
- **155 mẫu HTTP,0 mẫu lỗi**, quan sát2.0.0→2.0.1 trong khoảng11:55:34–12:01:12. Đây là lấy mẫu, không chứng minh không có lỗi giữa các mẫu.
- Kiểm cuối12:01:13: HTTP/live healthy; cả hai active,NRestarts0; live77 kết nối/79 người, HTTP khoảng2,31GiB/live144MiB, load1phút2,39 trên9core. Không coi là thử tải1.000CCU.
- Không có Traceback/CRITICAL/RuntimeError/ModuleNotFoundError trong log hai dịch vụ kể từ11:57:25 đến lượt kiểm cuối. Python máy chủ3.12.3; điểm yếu cancellation của runtime test Windows3.10 đã ghi riêng ở QA.
- Trình duyệt production xác nhận DOM390×844 khi vào bến, đi lên cầu rồi lên thuyền và chèo;834×1112 trên phố; reset về1280×720 desktop. Không có console error trong lượt desktop cuối. Đây là viewport mô phỏng, không phải kiểm phần cứng điện thoại.

## Dữ liệu và sự kiện

- Backup trước hotfix: `/var/backups/mot-ngay-lam-nghe-pg/hotfix-2.0.1-20261011/phocochuyen.dump`,3,1GB, exit0, pg_restore đọc mục lục thành công. Chưa diễn tập restore.
- Schema39 cài hai chỉ mục `town_treasure_unclaimed_location` và `town_treasure_claimed_age`. Không xóa rương chưa nhặt. Đối chiếu32 ID đã chụp trước rollout:32/32 vẫn tồn tại, rương đã nhặt không bị mở lại.
- Marker Hai ngày vàng vẫn starts1791689983, ends1791862783 (10:39:43 ngày13/10 kết thúc). Notice2.0 vẫn33045. Không kích hoạt lại hoặc kéo dài sự kiện, không đăng lại thông báo lớn, không xóa ảnh góp ý.
- Giữ release cũ bằng KEEP999 và bridge pool1/max3/MemoryMax3G. Cấu hình canonical/database/live khác giữ nguyên.

## Bằng chứng và quay lui

Logs/JSON/ảnh nằm trong `output/hotfix-2.0.1/`: package-report,verified-package,production-smoke-report,production-verify,production-health-watch,rolling.log,production-rowing-mobile.png,production-tablet.png,production-desktop.png. Không commit output hay thông tin xác thực.

Bản cũ giữ tại `/opt/mot-ngay-lam-nghe/releases/2.0.0-20261011103230`. Nếu cần quay lui mã, dùng rolling với `--to` và cùng ngân sách bridge; không restore database cũ tự động vì sẽ mất tiến trình sau cập nhật. Lưu ý2.0.0 có luật hết hạn/dọn rương cũ: phải giữ cơ chế bảo toàn rương mới nếu quay lui lâu dài, không để rollback phá yêu cầu tích lũy.
