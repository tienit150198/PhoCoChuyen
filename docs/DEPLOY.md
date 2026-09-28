# Mở game cho mọi người chơi (triển khai công khai)

Game là một tiến trình Python duy nhất: thư viện chuẩn, SQLite, không cần `pip install`. Để mở cho mọi người, đặt nó sau một reverse proxy HTTPS. Service worker, web push và cookie `Secure` đều cần HTTPS.

## Cách nhanh nhất: Docker + Caddy (HTTPS tự động)

1. Trỏ tên miền (ví dụ `game.example.com`) về IP máy chủ bằng bản ghi A/AAAA.
2. Tạo cấu hình:
   ```bash
   cp .env.example .env
   # sửa trong .env:
   #   ALLOWED_HOSTS=game.example.com
   #   TRUST_PROXY=1
   #   (tùy chọn) LLM_BASE_URL / LLM_MODEL / LLM_API_KEY cho AI nhân vật
   ```
3. Sửa tên miền trong `deploy/Caddyfile`.
4. Chạy cả game và Caddy:
   ```bash
   docker compose --profile public up -d --build
   ```
5. Mở `https://game.example.com`, rồi kiểm tra `https://game.example.com/api/health`.

Dữ liệu (SQLite + khóa VAPID của web push) nằm trong volume `game-data`, được mount vào `/app/storage`. Hãy sao lưu volume này định kỳ, ví dụ:
```bash
docker compose exec game python -c "import sqlite3;s=sqlite3.connect('/app/storage/game.sqlite3');d=sqlite3.connect('/app/storage/backup.sqlite3');s.backup(d)"
```

## Không dùng Docker (systemd + Nginx/Caddy)

```bash
python3 server.py --host 127.0.0.1 --port 8765
```
Chạy lệnh này dưới một user riêng bằng systemd, với `Restart=always` và `Environment=QUIET=1`. Cấu hình proxy chuyển `https://domain` → `http://127.0.0.1:8765`, giữ nguyên header `Host` và đặt `X-Forwarded-Proto`/`X-Forwarded-For`. Ví dụ với Nginx:
```nginx
location / {
    proxy_pass http://127.0.0.1:8765;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 60s;
    client_max_body_size 16m;
}
```
Nếu chạy tạm ở cổng khác 80/443 (ví dụ `http://IP:8080` khi chưa có tên miền), dùng `proxy_set_header Host $http_host;` để giữ cả số cổng. Máy chủ so `Origin` với `Host` gồm cả cổng, nên nếu thiếu cổng thì mọi thao tác sẽ bị từ chối.

## Biến môi trường quan trọng

| Biến | Ý nghĩa |
|---|---|
| `ALLOWED_HOSTS` | Tên miền/IP được phép. Header `Host` khác sẽ bị từ chối, để chống DNS rebinding. |
| `TRUST_PROXY=1` | Tin `X-Forwarded-For` (lấy giá trị cuối do proxy thêm) và `X-Forwarded-Proto`. Chỉ bật khi đứng sau proxy của bạn. |
| `COOKIE_SECURE=1` | Luôn gắn cờ `Secure` cho cookie. Không bật cũng được: cờ tự bật khi proxy báo `https`. |
| `COMMANDS_PER_MINUTE`, `NEW_SESSIONS_PER_MINUTE`, `AI_PER_MINUTE`, `AI_GLOBAL_PER_MINUTE` | Giới hạn chống spam. |
| `SESSION_IDLE_DAYS` | Số ngày không hoạt động trước khi bản lưu bị xóa (mặc định 180). |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_CONCURRENCY` | AI cho nhân vật review/phụ huynh. Người chơi phải tự bật “Cho phép AI” trong Cài đặt. |
| `MNL_DEV` | **Không bao giờ đặt trên máy chủ thật.** `MNL_DEV=1` tắt hành trình (mở mọi nghề, không trừ tiền sinh hoạt) và cho nhận việc không cần phỏng vấn. Chỉ dùng cho script kiểm trình duyệt. |
| `VAPID_SUBJECT`, `VAPID_PRIVATE_KEY`, `PUSH_DISABLED` | Web push. Mặc định khóa được tự tạo ở `storage/vapid.json`; đừng xóa tệp này, nếu mất thì mọi đăng ký thông báo cũ hết hiệu lực. |

## Bảo mật và vận hành

- **Khóa API AI** chỉ để trong `.env` hoặc biến môi trường của máy chủ. Không commit, không đưa vào ảnh Docker (`.dockerignore` đã loại `.env`). Nếu khóa từng bị dán vào chat, email hay issue, hãy **đổi khóa** ở nhà cung cấp.
- Máy chủ đã bật sẵn: CSP chặt (không có script inline), cookie HttpOnly + SameSite=Strict, token CSRF, kiểm tra Origin/Host, giới hạn tần suất, giới hạn kích thước request và gzip. Tài nguyên tĩnh có ETag.
- Phố nghề lọc link, e-mail, số điện thoại và từ thô tục. Nội dung bị 3 người báo cáo sẽ tự ẩn. Để gỡ hay khôi phục thủ công, sửa cột `hidden` trong SQLite (bảng `board`, `comments`, `previews`, `market`, `profiles`).
- Người chơi tự xóa dữ liệu được trong Cài đặt → Dữ liệu. Nếu ai đó gửi yêu cầu qua email `trachanhtv.works@gmail.com`, hãy tìm hồ sơ theo tên hiển thị trong bảng `profiles`, rồi xóa bằng `sid` tương ứng.
- Nhật ký (log) không ghi cookie hay nội dung người chơi gõ. Bật `QUIET=1` để tắt hẳn access log.
- Một tiến trình chịu được vài trăm người chơi đồng thời. Khi cần hơn, hãy nâng cấp máy (SQLite WAL chạy tốt trên SSD) trước khi nghĩ tới việc tách dịch vụ.

## Kiểm tra trước khi mở

```bash
python scripts/run_checks.py        # toàn bộ test Python
python server.py --port 8899 &       # chạy thử
curl -s localhost:8899/api/health
```
Sau đó mở trên điện thoại thật và thử: chọn nghề, mở ca, làm một việc, trả lời một review, vào Phố nghề, bật thông báo. Trên iPhone, thông báo chỉ hoạt động sau khi đã “Thêm vào MH chính”.
