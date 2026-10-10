# Phát hành 1.9.44 — 10/10/2026

Đã triển khai tại https://phocochuyen.io.vn, VPS production 103.195.238.178. Hoàn tất lúc 21:49:19 giờ Việt Nam. Game và live service cùng chạy `/opt/mot-ngay-lam-nghe/releases/1.9.44-20261010214815`.

## Nội dung

- 324 nâng cấp theo nghề: tăng nhịp khách, thu nhập và đơn online; 50 nghề, online tại 8 nghề có quầy hỗ trợ.
- Tổng 30 tranh đấu giá có bố cục riêng, mô tả nghệ thuật và độ hiếm; bảng top nhà sưu tầm.
- Chợ đen miễn phí vào cổng; tăng nhẹ xác suất Xóc đĩa, Lô tô và vé cào.
- Giải tuần kéo co chó sủa bằng micro: tối thiểu 30 trận thực sự bắt đầu, top 5 nhận 2 triệu / 1 triệu / 500 nghìn / 250 nghìn / 100 nghìn xu cùng danh hiệu. Tuần theo giờ Việt Nam, chốt sau thứ Hai 00:00 một phút. Trận cũ không hồi tố.

## Gói và sao lưu

- Source ref: `8593e926738d101d74ec54734dc7611196374619`; base live trước đó: `09f630c4a5cc0d133ec5310b013e69519696701a`.
- Manifest live 1.9.44 được lưu riêng ở commit `2823001e`; dùng commit này làm base cho gói kế tiếp. Các ghi chú sau triển khai và LIVE_REF được cập nhật sau commit manifest.
- Gói: `/root/mnl-1.9.44-8593e926.zip`, 91.096.618 byte.
- SHA256: `06a9c9427acf08cab653eb8ed6673cd7850bd826f503d981ed924418fd0e0418` (local và VPS khớp).
- Backup: `/root/mnl-backups/before-1.9.44-20261010-214108.dump`, 4.131.950.088 byte, `pg_dump -Fc -Z1`; `pg_restore --list` thành công. Chưa thử phục hồi toàn bộ backup này.
- Release trước: `/opt/mot-ngay-lam-nghe/releases/1.9.43-20261010121015`.
- Rolling release với `KEEP=999`, `BRIDGE_PG_POOL_MAX=3`, `BRIDGE_MEMORY_MAX=2G`. Giữ các release cũ, không thay cấu hình game/nginx ngoài chuyển upstream theo script hiện có.

## Kiểm chứng

- So khớp manifest 1.9.43: 1.304 file runtime khớp; tests/artifacts được script triển khai loại khỏi runtime như thiết kế. Đóng gói từ archive live đã xác minh, giữ byte tài nguyên không đổi.
- Build 1.926 file, thay đổi 60, không xóa file; minify 12. Kiểm tra lại zip/manifest đạt.
- Sau deploy cập nhật LIVE_REF về 8593e926: 10/10 test_task_compat đạt với dependency psycopg của dự án.
- Gate tương thích: 49.440 nhiệm vụ, 50 nghề, cả desk và classic. 312/312 module JS hợp Safari 15. Test nghiệp vụ chi tiết ở tài liệu tính năng.
- 62 mẫu public health trong lúc chuyển: 15 mẫu 1.9.43, 47 mẫu 1.9.44, tất cả HTTP 200; độ trễ lớn nhất 1.345 ms. Đây là lấy mẫu, không phải bằng chứng mọi request người chơi đều thành công.
- API public: health 1.9.44; content có 150 demand + 150 quality + 24 online; dogbark có minimum=30 và đúng 5 giải; leaderboard collection trả 200.
- Module public dog-bark-board, auction-art, auction khớp byte gói phát hành.
- Cả hai unit active, cwd trỏ đúng release mới; health nội bộ game và live trả OK. Live health chỉ nội bộ, `/live/health` public được nginx giữ kín (404 như thiết kế).
- PostgreSQL schema 35, competitive boolean default false NOT NULL và con trỏ giải đã tồn tại. Runtime có 30 tranh, phí vào chợ bằng 0, xác suất mới đúng cấu hình.
- Log sau chuyển không ghi nhận traceback, lỗi board, OOM hoặc failed-start tại thời điểm kiểm tra.

## Lưu ý vận hành

Sau khi phát danh hiệu giải tuần mới, không rollback về registry cũ không biết những danh hiệu này. Bản rollback phải giữ hỗ trợ `bark_weekly`, danh hiệu và schema bổ sung. Không phục hồi backup đè dữ liệu đang chơi chỉ để rollback mã nguồn.

Kiểm thử cục bộ đã biết một lỗi nền không liên quan: `fair_shell_render.mjs` báo `otChip is not defined`; không khẳng định toàn bộ suite dự án xanh. Không ghi thông tin đăng nhập vào tài liệu hoặc gói.
