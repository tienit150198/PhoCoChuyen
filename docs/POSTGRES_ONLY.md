# PostgreSQL là cơ sở dữ liệu duy nhất

Máy chủ game, dịch vụ live và công cụ vận hành đều yêu cầu PostgreSQL. Không có chế độ tệp cơ sở dữ liệu hay fallback khi kết nối thất bại. `DATABASE_URL` phải bắt đầu bằng `postgresql://` hoặc `postgres://`; thông tin kết nối không được ghi vào log.

## Chạy trên máy

1. Cài Python 3.10+ và PostgreSQL 16+; tạo database và tài khoản dành cho game.
2. Chạy `python -m pip install -r requirements.txt`.
3. Sao chép `.env.example` thành `.env`, thay `DATABASE_URL` và mật khẩu mẫu.
4. Chạy `python server.py --open` hoặc script `start` của hệ điều hành.

Game tự cài schema PostgreSQL khi khởi động. Biến `GAME_NAMESPACE` và tùy chọn `--namespace` nhận diện khóa của công việc nền và thư mục giữ khóa web push; khi kiểm thử, chúng cũng chọn schema riêng. Namespace không mở tệp database. Dữ liệu chính nằm trong PostgreSQL.

Khi nâng cấp máy chủ đang chạy, đặt `GAME_NAMESPACE` bằng đúng giá trị đường dẫn `GAME_DB` trước đây trước lần khởi động đầu tiên. Như vậy vị trí `vapid.json`, khóa bảo trì và cache thống kê được giữ nguyên. Nếu khóa web push nằm ở nơi khác, đặt `VAPID_KEY_FILE` tới tệp hiện có. Không tạo khóa VAPID mới: các đăng ký thông báo hiện tại cần dùng cùng khóa.

Dịch vụ live và các test socket cần Python 3.11 trở lên: cài `python -m pip install -r requirements-live.txt`, đặt cùng `DATABASE_URL` và chạy `python -m live`. Bản WebSocket được ghim theo `scripts/vendor_websockets.sh` để tương thích API phát tin. Trên Windows, entrypoint live và runner test dùng event loop selector tương thích psycopg async.

## Docker Compose

Sao chép `.env.example` thành `.env`, đổi `POSTGRES_PASSWORD` và đặt `DATABASE_URL` với host `postgres` (ví dụ `postgresql://phocochuyen:mat-khau-da-encode@postgres:5432/phocochuyen`), rồi chạy `docker compose up -d --build`. Mật khẩu trong `POSTGRES_PASSWORD` giữ nguyên; mật khẩu trong URL cần URL-encode nếu có ký tự đặc biệt. Compose dùng URL bạn cấu hình, chạy PostgreSQL và đợi database sẵn sàng. Dữ liệu database nằm trong volume `postgres-data`; volume `game-data` giữ khóa web push và tệp phục vụ khác. PostgreSQL chỉ mở cổng 5432 trên localhost.

Để bật HTTPS, đặt tên miền trong `deploy/Caddyfile`, cấu hình `ALLOWED_HOSTS` và `TRUST_PROXY=1`, rồi chạy `docker compose --profile public up -d --build`. Mật khẩu trong URL phải được URL-encode nếu có ký tự đặc biệt.

## Kiểm thử

Chỉ trỏ `TEST_DATABASE_URL` tới PostgreSQL dùng riêng cho kiểm thử; bỏ `DATABASE_URL` khỏi môi trường kiểm thử. Tài khoản cần quyền tạo và xóa schema. Mỗi namespace tạm nhận một schema riêng; test và server con dùng chung mã lần chạy để chia sẻ đúng fixture. Schema được dọn khi thư mục tạm mất hoặc lần chạy kết thúc.

```powershell
$env:TEST_DATABASE_URL='postgresql://test_user@127.0.0.1:5432/phocochuyen_test'
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
python scripts/run_checks.py
```

Các script `browser_*.py`, `verify_package.py` và `live_load.py` cũng dùng endpoint kiểm thử này hoặc URL database dùng riêng được truyền rõ ràng. Không dùng endpoint production. `live_load.py` tự khởi chạy dịch vụ live trên cùng schema kiểm thử; tùy chọn cũ `--url`/`--pid` bị từ chối trước khi tạo fixture để tránh kết nối tới schema khác.

## Vận hành

Các công cụ tặng quà, tạo tài khoản vận hành, backfill, ghim chat và quyết toán đám cưới sử dụng `DATABASE_URL`. `deploy/pg/install_pg16.sh` cài PostgreSQL trên máy Linux; `deploy/pg/pg_backup.sh` và timer đi kèm sao lưu bằng `pg_dump`.

Các tài liệu migration cũ được giữ làm lịch sử. Công cụ đồng bộ và rollback sang cơ sở dữ liệu tệp đã được gỡ. Tệp dữ liệu và bản sao lưu cũ không bị xóa bởi thay đổi này; nếu cần lấy dữ liệu từ chúng, thực hiện một lần import riêng có kiểm chứng.
