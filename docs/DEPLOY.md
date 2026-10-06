# Mở game cho mọi người chơi (triển khai công khai)

Game chạy bằng Python và PostgreSQL, cần driver `psycopg` (`python -m pip install -r requirements.txt`). PostgreSQL là bắt buộc; xem [POSTGRES_ONLY.md](POSTGRES_ONLY.md). Để mở cho mọi người, đặt nó sau một reverse proxy HTTPS. Service worker, web push và cookie `Secure` đều cần HTTPS.

## Cách nhanh nhất: Docker + Caddy (HTTPS tự động)

1. Trỏ tên miền (ví dụ `game.example.com`) về IP máy chủ bằng bản ghi A/AAAA.
2. Tạo cấu hình:
   ```bash
   cp .env.example .env
   # sửa trong .env:
   #   POSTGRES_PASSWORD=<mật khẩu database>
   #   DATABASE_URL=postgresql://phocochuyen:<mật khẩu đã URL-encode>@postgres:5432/phocochuyen
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

Dữ liệu PostgreSQL nằm trong volume `postgres-data`; khóa VAPID và tệp phụ trợ nằm trong `game-data` (`/app/storage`). Sao lưu database bằng `pg_dump`; ví dụ dưới đây tạo archive PostgreSQL trong thư mục backup của service database. Hãy chép archive ra nơi sao lưu riêng và lưu cả khóa VAPID.

```bash
docker compose exec postgres sh -c 'mkdir -p /tmp/mnl-backup && pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/mnl-backup/game.dump'
docker compose cp postgres:/tmp/mnl-backup/game.dump ./game.dump
```

## Không dùng Docker (systemd + Nginx/Caddy)

Cài PostgreSQL, tạo tài khoản/database game, đặt `DATABASE_URL` trong `.env` hoặc `EnvironmentFile` của systemd. Cài driver bằng `python3 -m pip install -r requirements.txt` trước khi chạy.

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

### Tài nguyên tĩnh có phiên bản (tải nhanh, không trộn phiên bản)

Trang `/` được server dựng lúc phục vụ: mọi URL `/js/`, `/css/`, `/i18n/`, `/music/`, `/audio/`, `/icons/` mang `?v=<mã băm nội dung>` và một import map đưa mọi module ES (kể cả `import()` động) về đúng URL đó. Một URL `?v=` không bao giờ đổi nội dung, nên được giữ một năm (`immutable`); lần vào lại gần như không tải gì. Danh mục game nằm ở `GET /api/content?v=<mã>` (cũng giữ một năm) thay vì trong `/api/bootstrap`.

Để một URL `?v=` luôn trả đúng các byte nó gọi tên (kể cả trong lúc deploy, và cho tab cũ còn mở), mỗi tiến trình khi khởi động chép các tệp đó vào kho theo mã băm `STATIC_CAS_DIR/<mã>/<đường dẫn>` (mặc định `public/_v`). Nên đặt kho này **ngoài thư mục release** để các bản cũ vẫn còn:

```bash
sudo install -d -o <user chạy game> -m 755 /opt/mot-ngay-lam-nghe/shared/_v
# mỗi unit systemd: Environment=STATIC_CAS_DIR=/opt/mot-ngay-lam-nghe/shared/_v
```

Nginx (khối `map` đặt trong `http {}`; `location` đặt trong `server {}`):
```nginx
map $arg_v $asset_v { "~^[0-9a-f]{12}$" $arg_v; default ""; }

location ~ ^/(js|css|i18n|icons|music|audio)/ {
    if ($asset_v) { rewrite ^ /_v/$asset_v$uri last; }
    root /opt/mot-ngay-lam-nghe/current/public;   # URL không có ?v=: như cũ, no-cache
    try_files $uri =404;
    add_header Cache-Control "no-cache" always;
}
location ^~ /_v/ {
    internal;
    root /opt/mot-ngay-lam-nghe/shared;            # = STATIC_CAS_DIR không có "/_v"
    try_files $uri @asset_miss;
    add_header Cache-Control "public, max-age=31536000, immutable" always;
}
location @asset_miss {                              # mã chưa có trong kho: tệp hiện tại, no-cache
    rewrite ^/_v/[0-9a-f]+(/.*)$ $1 break;
    root /opt/mot-ngay-lam-nghe/current/public;
    add_header Cache-Control "no-cache" always;
}
```
(giữ nguyên `etag`, `gzip` và các header bảo mật như các location tĩnh hiện có; `gzip_static on;` trong `location ^~ /_v/` cho nginx gửi luôn bản `.gz` mức 9 mà server đã nén sẵn cạnh mỗi tệp trong kho). Thiếu kho hay thiếu cấu hình này thì game vẫn chạy đúng, chỉ là tài nguyên về lại `no-cache`. Khi server chạy bản mới hơn trang đang mở, người chơi thấy nút nhỏ “Đã có phiên bản mới, bạn tải lại để cập nhật nha” (header `X-Game-Version` trên mọi phản hồi `/api/`); game không tự tải lại. Kiểm tra: `python scripts/browser_deploy.py`.

### Tải lần đầu trên mạng yếu (gói phát hành, danh mục chia phần)

- **Gói phát hành rút gọn JS/CSS.** `python3 scripts/package.py` chạy `scripts/build_static.py`: mọi tệp `.js` trong `public/` được esbuild rút gọn (từng tệp riêng, không gộp: một lần deploy đổi một module thì chỉ URL của module đó đổi), `.css` bỏ khoảng trắng/chú thích. Mã trong git giữ nguyên để đọc và để test. Máy đóng gói cần `node`/`npx` (esbuild được ghim phiên bản: cùng mã nguồn ra đúng cùng byte, nên tệp không đổi giữ URL và cache của người chơi); máy chủ không cần node. `--no-minify` đóng gói nguyên mã nguồn. Lần phát hành đầu tiên theo cách này đổi URL của mọi tệp một lần.
- **Danh mục chia phần.** `GET /api/content?v=<mã>` vẫn trả cả danh mục (trang cũ dùng). Trang mới chỉ chờ `&part=core` (~40 KB gzip thay vì ~120 KB); `&part=more` (tin tuyển dụng, sổ tiệm, tình huống, đề thi chứng chỉ, chuyện của nghề) tải ngay sau khung hình đầu; `&career=<id>` là dữ liệu riêng của một nghề plugin, tải cùng bàn làm việc của nghề đó. Mọi phần đều giữ một năm theo cùng mã nội dung (`game/content.py` `content_parts`). Mã nội dung chỉ đổi khi dữ liệu game đổi (7 lần phát hành gần nhất: 2 lần).
- **Nơi làm việc của khung hình đầu.** `/api/bootstrap` gửi header `X-Game-Warm` (cảnh, bàn làm việc, stylesheet của nghề đang mở) và `X-Game-Place`; `boot.js` tải trước chúng ngay khi header về, thay vì một chuỗi import sau khi `app.js` chạy.
- **Brotli:** nginx 1.24 bản Ubuntu không có module brotli, nên không phục vụ được `.br` cho tệp tĩnh một cách an toàn (gắn tay `Content-Encoding: br` qua `add_header` dễ bị nén chồng); vẫn dùng gzip mức 9 nén sẵn.

## Biến môi trường quan trọng

| Biến | Ý nghĩa |
|---|---|
| `DATABASE_URL` | Bắt buộc: URL PostgreSQL. Thiếu hoặc sai định dạng thì máy chủ dừng. |
| `ALLOWED_HOSTS` | Tên miền/IP được phép. Header `Host` khác sẽ bị từ chối, để chống DNS rebinding. |
| `TRUST_PROXY=1` | Tin `X-Forwarded-For` (lấy giá trị cuối do proxy thêm) và `X-Forwarded-Proto`. Chỉ bật khi đứng sau proxy của bạn. |
| `COOKIE_SECURE=1` | Luôn gắn cờ `Secure` cho cookie. Không bật cũng được: cờ tự bật khi proxy báo `https`. |
| `COMMANDS_PER_MINUTE`, `NEW_SESSIONS_PER_MINUTE`, `AI_PER_MINUTE`, `AI_GLOBAL_PER_MINUTE` | Giới hạn chống spam. |
| `FEEDBACK_PER_10MIN`, `FEEDBACK_PER_DAY` | Số góp ý tối đa mỗi phiên trong 10 phút (mặc định 5) và trong 24 giờ (mặc định 30). Mỗi IP được gấp 4 lần mức 10 phút. |
| `ADMIN_USERS` | Tên đăng nhập (cách nhau bằng dấu phẩy) được xem **📥 Hộp góp ý** trong mục Góp ý: đọc, đổi trạng thái, trả lời người chơi. Mặc định trống = không ai. Tài khoản phải đăng nhập; tạo bằng nút Đăng ký trong game. |
| `SESSION_IDLE_DAYS` | Số ngày không hoạt động trước khi bản lưu bị xóa (mặc định 180). |
| `WORKERS` | Số tiến trình phục vụ cùng một cổng (mặc định 1). Đặt bằng số CPU (ví dụ `WORKERS=4`). Không cần đổi cấu hình proxy: các tiến trình cùng nhận kết nối trên một socket. Giới hạn AI, đăng nhập, phiên mới và góp ý được chia sẻ giữa các tiến trình (bảng PostgreSQL `hits`); việc dọn dẹp và gửi thông báo chỉ chạy ở một tiến trình. |
| `GAME_NAMESPACE` | Đường dẫn nhận diện khóa bảo trì, cache thống kê và thư mục khóa web push (mặc định `storage/game`); không phải tệp database. Khi nâng cấp, chuyển nguyên giá trị `GAME_DB` cũ sang biến này để giữ các vị trí hiện có. |
| `PRUNE_GUEST_DAYS` | Bản lưu khách chưa từng chơi thật (không tài khoản, không tên công khai, `revision <= 1`, không có tiến trình) bị xóa sau số ngày này (mặc định 3, `0` = tắt). Chạy mỗi giờ, từng nhóm nhỏ. |
| `LAZY_SAVES` | `1` = phiên mới chỉ lưu một dấu nhỏ (~200 byte) cho tới thao tác đầu tiên, thay vì cả bản lưu ~90 KB (khách vào rồi đi không làm phình cơ sở dữ liệu). Mặc định `0`. Chỉ bật khi MỌI tiến trình dùng chung cơ sở dữ liệu đã chạy bản mới: bản cũ không đọc được dấu này. |
| `RECEIPT_DAYS`, `RECEIPTS_PER_SAVE` | Biên nhận chống gửi trùng được giữ bao lâu (mặc định 2 ngày) và tối đa bao nhiêu cho mỗi bản lưu (mặc định 200). |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_CONCURRENCY` | AI cho nhân vật review/phụ huynh. Người chơi phải tự bật “Cho phép AI” trong Cài đặt. |
| `STATIC_RECHECK_SECONDS` | Bao lâu (giây) máy chủ tin danh sách tệp tĩnh (`public/`) trước khi `stat()` lại ~230 tệp. Mặc định 2 giây khi `WORKERS=1` (máy dev: sửa tệp thấy ngay) và 300 giây khi `WORKERS>1`. Trên máy chủ thật nên đặt `3600`: mỗi lần deploy là thư mục mới và khởi động lại, tệp không đổi giữa chừng. |
| `SLOW_COMMAND_MS`, `SLOW_LOG_PER_MINUTE` | Ghi `[slow-cmd]` khi một thao tác mất quá số mili giây này (mặc định 1500); `[slow-lock]`/`[slow-write]` khi chờ khóa hoặc ghi quá nửa mức đó. Mỗi tiến trình ghi tối đa `SLOW_LOG_PER_MINUTE` dòng như vậy mỗi phút (mặc định 20, `0` = không giới hạn); dòng kế tiếp ghi số dòng đã bỏ. |
| `STATIC_CAS_DIR` | Kho tệp tĩnh theo mã băm mà proxy phục vụ cho URL `?v=` (mặc định `public/_v`). Xem mục “Tài nguyên tĩnh có phiên bản”. |
| `API_GZIP_LEVEL` | Mức gzip của phản hồi `/api/` (mặc định 4: tốn ~2/3 CPU so với mức 5, dữ liệu gửi đi nhiều hơn ~5%). Tệp tĩnh luôn được nén sẵn ở mức 6. |
| `COMMAND_CONCURRENCY` | Số worker xử lý `Store.command` trong một tiến trình, mặc định `4` (1–64). Yêu cầu chờ trước khi tải bản lưu từ PostgreSQL và dùng lại nhóm thread cố định để tái sử dụng bộ nhớ. Giới hạn này tách biệt với `MAX_THREADS` của kết nối HTTP. Khi tăng, phải đo lại RAM và độ trễ; thêm thread không tạo thêm CPU cho một tiến trình Python. |
| `HTTP_KEEPALIVE_SECONDS` | Chờ dòng yêu cầu kế tiếp trên kết nối HTTP đang rảnh, mặc định `2` giây (0,1–120). Riêng `POST /api/command` luôn trả `Connection: close` và nhả slot ngay sau phản hồi, không phụ thuộc biến này. GET/tệp tĩnh vẫn tái sử dụng kết nối. Yêu cầu đầu tiên và giai đoạn đọc header/body vẫn có timeout 20 giây; WebSocket không bị ảnh hưởng. Mỗi command cần TCP/thread HTTP mới; khi Nginx/Caddy kết thúc TLS, đây là kết nối upstream tới Python, không bắt buộc tạo lại TLS phía trình duyệt. |
| `MALLOC_ARENA_MAX` | Tùy chọn cho Linux/glibc: có thể thử `2` để giới hạn số vùng cấp phát bộ nhớ, rồi đo lại RAM/độ trễ. Bản sửa đã có nhóm thread tái sử dụng; lượt tải cuối dùng mặc định, không cần biến này. **Phải đặt trước khi Python khởi chạy**, qua systemd `Environment=`, Docker `environment`/`env_file` hoặc shell; `server.py` đọc `.env` sau khi Python đã chạy nên không đủ. Không áp dụng cho Windows hay libc khác. |
| `GC_THRESHOLD` | Ngưỡng bộ gom rác của Python (mặc định `50000,20,20`: ít lượt gom hơn khi đọc/ghi bản lưu lớn; `700,10,10` là mặc định của Python). Đối tượng lúc khởi động được `gc.freeze()` giữ ngoài các lượt gom. |
| `MNL_DEV` | **Không bao giờ đặt trên máy chủ thật.** `MNL_DEV=1` tắt hành trình (mở mọi nghề, không trừ tiền sinh hoạt) và cho nhận việc không cần phỏng vấn. Chỉ dùng cho script kiểm trình duyệt. |
| `VAPID_SUBJECT`, `VAPID_PRIVATE_KEY`, `VAPID_KEY_FILE`, `PUSH_DISABLED` | Web push. Mặc định khóa được tự tạo ở `vapid.json` trong thư mục của `GAME_NAMESPACE`; `VAPID_KEY_FILE` chọn một tệp khóa hiện có. Đừng xóa hoặc thay khóa này: mọi đăng ký thông báo cũ cần dùng cùng khóa. |

## Theo dõi PostgreSQL khi tải ghi lớn

Bài 1.000 người/200 command mỗi giây ghi nhận nhiều `COMMIT` chờ `WALWrite` hơn 0,5 giây. Thử nén WAL, tăng ngưỡng checkpoint và thay RAM/CPU trong một lượt chẩn đoán **không cải thiện kết quả**; không áp dụng các cấu hình thử đó làm mặc định. [Báo cáo và giới hạn phép đo](performance/2026-10-06-fix/REPORT.md) giữ cả các lượt không đạt.

Khi đo trên staging đúng máy, ghi CPU, RAM, I/O, `pg_stat_wal`, `pg_stat_bgwriter` và wait event. Giữ `fsync`, `synchronous_commit`, `full_page_writes` bật; không đổi độ bền dữ liệu để lấy số latency đẹp. [Tài liệu WAL chính thức](https://www.postgresql.org/docs/16/runtime-config-wal.html).

## Bảo mật và vận hành

- **Khóa API AI** chỉ để trong `.env` hoặc biến môi trường của máy chủ. Không commit, không đưa vào ảnh Docker (`.dockerignore` đã loại `.env`). Nếu khóa từng bị dán vào chat, email hay issue, hãy **đổi khóa** ở nhà cung cấp.
- Máy chủ đã bật sẵn: CSP chặt (script inline chỉ gồm import map và boot script, được cho phép bằng mã băm SHA-256), cookie HttpOnly + SameSite=Strict, token CSRF, kiểm tra Origin/Host, giới hạn tần suất, giới hạn kích thước request và gzip. Tài nguyên tĩnh có ETag.
- Phố nghề lọc link, e-mail, số điện thoại và từ thô tục. Nội dung bị 3 người báo cáo sẽ tự ẩn. Để gỡ hay khôi phục thủ công, sửa cột `hidden` trong PostgreSQL (bảng `board`, `comments`, `previews`, `market`, `profiles`).
- Người chơi tự xóa dữ liệu được trong Cài đặt → Dữ liệu. Nếu ai đó gửi yêu cầu qua email `trachanhtv.works@gmail.com`, hãy tìm hồ sơ theo tên hiển thị trong bảng `profiles`, rồi xóa bằng `sid` tương ứng.
- Nhật ký (log) không ghi cookie hay nội dung người chơi gõ. Bật `QUIET=1` để tắt hẳn access log.
- JSON nhanh (tùy chọn): có gói `orjson` trong `PYTHONPATH` thì bản lưu được đọc nhanh ~2 lần, ghi nhanh ~4 lần (văn bản lưu giống hệt từng byte, xem `game/fastjson.py`). Không có thì game dùng `json` chuẩn như trước. Cài: `scripts/vendor_orjson.sh /opt/mot-ngay-lam-nghe/shared/pyvendor` (hoặc `download` trên máy có mạng rồi `install <wheel> <thư mục>` trên máy chủ), rồi khởi động lại dịch vụ.
- Một tiến trình Python chỉ dùng được một CPU. Máy nhiều CPU: đặt `WORKERS` bằng số CPU. Nên để proxy (Nginx/Caddy) phục vụ thẳng thư mục `public/` để Python chỉ lo `/api/`.
- PostgreSQL tự autovacuum các bảng; theo dõi dung lượng database, WAL và bản sao lưu. Công cụ sao lưu systemd có tại `deploy/pg/pg_backup.sh`.

## Kiểm tra trước khi mở

```bash
TEST_DATABASE_URL=postgresql://test_user@127.0.0.1:5432/game_test python scripts/run_checks.py # DB dùng riêng cho test
python server.py --port 8899 &       # chạy thử
curl -s localhost:8899/api/health
```
Sau đó mở trên điện thoại thật và thử: chọn nghề, mở ca, làm một việc, trả lời một review, vào Phố nghề, bật thông báo. Trên iPhone, thông báo chỉ hoạt động sau khi đã “Thêm vào MH chính”.
