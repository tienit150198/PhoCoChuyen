# Sửa nghẽn bộ nhớ và HTTP khi có 1.000 người chơi

Ngày 06/10/2026. Phạm vi: sửa backend và kiểm tra khung hình của bản Phaser 2.5D. Không thay đồ họa, dữ liệu người chơi thật hay cấu hình production.

**Đã giảm sự cố quá tải, chưa chứng nhận toàn bộ mục tiêu 1.000 CCU.** Lượt hoàn chỉnh gần nhất dùng bản sửa ứng dụng, PostgreSQL mặc định, 1.000 người vừa đi lại vừa gửi gần 200 command/s trong 600 giây:

| Chỉ số | Kết quả |
|---|---:|
| Kết nối thành công | 1.000/1.000 |
| Command thành công / đã gửi | 119.995/119.995; 0 lỗi HTTP |
| Tốc độ hoàn thành trong cửa sổ đo | 199,98 command/s |
| Lượt gửi theo lịch bị bỏ lỡ | 5/120.000 |
| API p50 / p95 / p99 | 30,11 / 846,13 / 1.521,35 ms |
| Đồng bộ chuyển động người khác p95 | 105,43 ms |
| CPU API trung bình / đỉnh mẫu khoảng 1 giây | 3,732 / 5,963 core |
| RAM API cao nhất | 3.881,4 MiB (~3,79 GiB) |
| RAM realtime cao nhất | 98,2 MiB |
| OOM-kill / mất kết nối WebSocket | 0 / 0 |
| Thông báo vượt nhịp chuyển động | 59/1.976.494 lần gửi (~0,003%) |

So với lượt cũ bị 7 OOM-kill và 483 lỗi HTTP, bản sửa đã xử lý được hai lỗi lớn này trong bài thử dài hơn. Tuy nhiên **p95 API 846 ms chưa đạt mục tiêu 300 ms**; không kết luận “hết lag” hoặc đủ cho mọi kiểu chơi ở 1.000 CCU. Core chưa phải giới hạn duy nhất: đã quan sát được COMMIT chờ ghi WAL.

Ngày 06/10, người dùng yêu cầu xử lý tạm, dừng thử thêm, commit và push. Bản cuối bổ sung sửa thứ tự khóa thống kê sau lượt tải trên; sửa này đã qua regression và suite 98 test, **chưa chạy lại bài tải**. Chưa có lượt mới 100 command/s; số 100 command/s trong báo cáo trước thuộc baseline, không phải phép chứng nhận bản cuối.

Ưu tiên tiếp theo khi tiếp tục: đo trên staging đúng CPU/RAM/SSD và proxy đích; xác nhận độ trễ ghi WAL, tải nghề thực và phiên dài. Chưa thay cấu hình production.

## Đã sửa gì và vì sao

1. **Chặn thao tác nặng trước khi tải bản lưu, rồi chạy trên nhóm thread cố định.** Mỗi tiến trình mặc định chỉ có 4 command đang xử lý; các `Store` cùng tiến trình dùng chung giới hạn. Chỉ dùng semaphore trên các thread HTTP vẫn làm RAM tăng tới OOM trong thử nghiệm. Nhóm worker tái sử dụng giới hạn cả số bản lưu đang sống và số thread giữ vùng cấp phát lớn. ContextVars, phép gọi lồng nhau, lỗi và khởi động worker sau fork đã được kiểm tra. Revision, giao dịch, receipt/idempotency và kiểm tra dữ liệu vẫn giữ nguyên.
2. **Bỏ vòng tham chiếu trong bộ tạo response delta.** Hai hàm lồng nhau giữ bộ hash/đường dẫn của từng request cho tới khi cyclic GC chạy. Chuyển sang helper cấp module giữ nguyên byte JSON và hash, đồng thời cho phép giải phóng ngay. So sánh 488 trường hợp cho kết quả byte giống bản cũ. Thí nghiệm riêng với GC tắt: 32 bộ hash bị giữ ở bản cũ, 0 ở bản sửa. Đây là một nguồn giữ RAM đã xác nhận, không phải toàn bộ nguyên nhân OOM.
3. **Nhả slot HTTP đúng lúc.** Kết nối HTTP rảnh trước đây vẫn chiếm một trong 64 thread của mỗi worker. Timeout rảnh 2 giây đã giảm lỗi nhưng chưa đủ. `POST /api/command` giờ trả rõ `Connection: close`, gửi hết phản hồi rồi nhả slot ngay. Client biết phải kết nối lại; không tự động gửi lại thao tác hay bỏ qua kiểm tra an toàn. GET/tệp tĩnh tiếp tục dùng lại kết nối. Timeout đọc yêu cầu đầu, header/body vẫn 20 giây; WebSocket không đổi.

4. **Ghi thống kê theo thứ tự khóa nhất quán.** Log PostgreSQL của lượt chẩn đoán phát hiện deadlock khi hai batch cộng `stat_actions` trùng hàng. SQL thêm `ORDER BY` theo đủ bốn khóa xung đột, dùng collation `C`; việc chỉ sắp xếp list Python không buộc planner giữ thứ tự. Regression tái hiện lỗi `40P01` ở bản cũ và chạy qua ở bản sửa, giữ tổng đếm, quyền riêng tư và chặn ghi cho phiên đã xóa. Không coi đây là bằng chứng mọi độ trễ COMMIT đều do deadlock.

Đánh đổi: mỗi command tạo một kết nối TCP và thread HTTP mới. Với Nginx/Caddy kết thúc TLS, chi phí này nằm ở kết nối upstream tới Python; trình duyệt có thể tiếp tục dùng TLS/HTTP2 với proxy. Bài tải đo cả chi phí tạo kết nối/thread này. Chưa đo cấu hình proxy/TLS thật, và không suy ra khả năng mở rộng vô hạn từ kết quả này.

Không thêm cache dùng chung cho bản lưu cá nhân; không tắt kiểm tra giao dịch, giới hạn chuyển động hay kiểm tra toàn bộ bản lưu định kỳ.

## Các lượt chẩn đoán không đạt

| Lượt | Kết quả | Kết luận được phép rút ra |
|---|---|---|
| Baseline `f3ada34`, 200 lệnh/s, 180 giây | 35.124/35.607 lệnh thành công; 483 lỗi HTTP; p95 901,3 ms; RAM chạm 6 GiB; 7 OOM-kill kể cả xử lý nốt | Đã tái hiện sự cố thật; chỉ tăng core/worker không giải quyết được |
| Baseline + `MALLOC_ARENA_MAX=2`, 180 giây | 2 timeout HTTP, 2 cảnh báo giới hạn chuyển động; đỉnh RAM 4.069,7 MiB | Giảm RAM có ích nhưng riêng cấu hình allocator chưa đủ |
| Nhóm command cố định + delta, HTTP rảnh vẫn 20 giây, 180 giây | 128 timeout HTTP; 415 lượt gửi bỏ lỡ; đỉnh RAM 2.996 MiB; không OOM | Hết OOM chưa đồng nghĩa hết nghẽn HTTP |
| Thêm timeout HTTP rảnh 2 giây, 600 giây | 119.976 lệnh thành công; 17 ngắt HTTP; 7 lượt gửi bỏ lỡ; p95 1.006,2 ms; đỉnh RAM 3.870,5 MiB; không OOM | Chưa đạt mục tiêu độ trễ/lỗi; tiếp tục sửa vòng đời kết nối |
| Client yêu cầu đóng kết nối command, 60 giây chẩn đoán | p95 86,45 ms nhưng 442 ngắt HTTP do server chưa báo đóng trong response | Chỉ thêm header ở client không phải bản sửa hợp lệ; server phải báo đóng rõ ràng |
| Thử LZ4 WAL/4 GB WAL; tăng RAM PG 1,5→3 GiB và đổi quota API/PG 6/2→5/3 giữa lượt | 115.047/115.061 HTTP 200; 7 timeout, 7 xung đột revision; 4.939 lượt bỏ lỡ; p95 4.363,58 ms; không OOM | **Không đạt, nhiều cấu hình trong một lượt**; không khuyến nghị áp dụng các chỉnh thử này |

Lượt chỉnh PostgreSQL có 115.054 commit: 7 request timeout vẫn đã commit, nên thao tác tiếp theo gặp revision conflict; không đếm timeout là HTTP thành công. Các mốc thay RAM/CPU và cấu hình thử giữ trong `iterations/tuned-diagnostic/`; không phát hành file cấu hình đó vào `deploy/`.

Các lượt có khác biệt về thời lượng, revision, trạng thái PostgreSQL/cache và cấu hình. Đây là chuỗi thí nghiệm chẩn đoán, không phải phép A/B cô lập mọi biến. Các lần có instrument heap/stack làm thay đổi tải đã hủy không được tính là bài nghiệm thu. Giữ số liệu trung gian trong `iterations/`, `arena2-200.json` và `pool4-default-200.json`.

## Môi trường, tải và giới hạn cho máy 9 core

- Host Windows i7-12700K, Docker Linux **thực có 8 vCPU**, khoảng 16 GiB RAM. Bộ phát tải cũng chạy trong VM này, quota riêng 2 CPU/4 GiB. Không gọi đây là phép đo trực tiếp trên máy 9 core production.
- Tổng quota dịch vụ là 9 CPU: API 6 CPU/6 GiB, 8 worker; realtime 1 CPU/768 MiB; PostgreSQL 2 CPU/1.5 GiB. `PG_POOL=3`, `PG_POOL_MAX=8`, PostgreSQL 16, `max_connections=120`, `shared_buffers=256MB`.
- Bản sửa dùng mặc định `COMMAND_CONCURRENCY=4`, `HTTP_KEEPALIVE_SECONDS=2`, không đặt `MALLOC_ARENA_MAX`. Đây là tùy chọn Linux/glibc đã thử riêng, không phải điều kiện bắt buộc cho lượt cuối. [Tài liệu allocator chính thức](https://sourceware.org/glibc/manual/latest/html_node/Memory-Allocation-Tunables.html).
- Snapshot của lượt tải hoàn chỉnh: Git `f3ada34` cộng đúng ba file đã sửa `game/storage.py`, `game/state_delta.py`, `server.py`; hash trong `results.json`. Bản mã cuối thêm `game/retention.py` sau lượt tải, ghi riêng trong `post_benchmark_patch`; không gán thay đổi này cho số đo cũ. Không đưa các sửa hội chợ đang dở của workspace vào image. Python 3.12.15, psycopg 3.3.6, orjson 3.12, websockets 17.1; generator aiohttp 3.14.4. Test image thêm psutil để quan sát.
- PostgreSQL được tạo mới sau integration test. 1.000 tài khoản tổng hợp: 900 save 162.017 byte, 100 save 4.701.855 byte, đã bắt đầu 41 nghề. Dữ liệu lặp lại nên nén tốt; không đại diện I/O xấu nhất của save thật.
- Seed revision 40 để lượt 600 giây đi qua kiểm tra toàn bộ bản lưu ở revision 50/100/150. Có authentication, CSRF, revision, ghi database, receipt, delta và gzip thật. Hành động `feed_like` kiểm tra đường đọc–sửa–ghi; không phải mọi logic của 41 nghề hoặc dịch vụ AI.
- 1.000 WebSocket chia thành **34 khu, tối đa 30 người/khu**. Mỗi người đi khoảng một lần/300 ms; 3 tin chat chung/s. Health có thêm một kênh chat nên báo 35 phòng. Không vẽ 1.000 avatar cùng một màn hình.
- 200 command/s theo lịch: mỗi người một lệnh/5 giây, tối đa một request đang chờ. Ghi riêng lượt bỏ lỡ, lỗi và phản hồi đến sau cửa sổ đo; không lấy số kết nối rảnh làm bằng chứng về thông lượng. Tăng người dần khoảng 40/s, chưa phải bài 1.000 người đăng nhập cùng một mili giây.
- Generator giữ một tập hash cũ có chặn trên 8.000, khác cách browser chỉ giữ hash hiện tại; phân phối kích thước thực có trong report. Lượt cuối dùng client thông thường, không đặt `CAP_CLOSE_COMMANDS`.
- Độ trễ chính và CPU dùng đồng hồ monotonic. VM có chênh lệch giữa thời gian wall-clock và monotonic; giữ cả hai trong số liệu. Các hint `server_command`/`outside_handler` dựa trên wall-clock không dùng làm tiêu chí nghiệm thu. Không so CPU trung bình của báo cáo cũ dùng wall-clock với lượt mới để tuyên bố tiết kiệm theo phần trăm.
- Chạy trong mạng Docker, chưa có TLS, Internet, mất gói, reverse proxy thật, điện thoại vật lý, failover hay soak nhiều giờ. Chưa biết model CPU/RAM/SSD của máy 9 core đích. Cần chạy lại trên staging đúng máy trước khi cam kết vận hành.

## Khung hình của client

Không tái hiện được giật kéo dài trên những đoạn đi ngắn đã đo, nên không thay đổi renderer theo phỏng đoán. Chromium trên máy này có nhịp khoảng 75 Hz. Khi luôn có 29 nhân vật khác trong camera, frame p95 là 13,4 ms ở viewport desktop và mobile giả lập, kể cả throttle CPU 4×. Có vài khung 26–40 ms; không có rAF interval trên 50 ms trong các mẫu sáu giây.

Đây là đo cảnh đã tải xong trên máy tính, không phải bằng chứng mọi điện thoại đều đạt 60 FPS. Maximum zoom, cold-start, GPU/DPR cao và chơi nhiều giờ chưa được chứng nhận. Renderer đã dùng cache nền tĩnh, texture tái sử dụng và ngủ khi rảnh. Xem [phương pháp và dữ liệu client](client/report.md).

## Kiểm chứng mã và tái lập

- **98 test backend chạy thành công trong 69,410 giây ở bản mã cuối, một test Node được skip vì image không có Node.** Bao gồm storage/concurrency, HTTP, state delta, transaction/ledger và bộ nhớ. Các test delta có Node đã chạy riêng trên host; typecheck và test isometric cũng đã qua.
- Regression kiểm tra giới hạn dùng chung giữa Store, worker tái sử dụng, nhả permit khi lỗi, ContextVars/phép gọi lồng nhau, fork sau khi executor đã chạy; delta giải phóng reference khi GC tắt; slot HTTP rảnh; response 200/401/403 báo đóng; client tự nối lại; GET/static dùng cùng socket; request đầu, header/body gửi chậm và pipelining; hai batch thống kê tranh chấp vẫn hoàn tất và cộng đúng số liệu.
- [Review mã](client/backend-final-review.md) đọc độc lập trước lượt tải cuối. Ghi chú về tài liệu `HTTP_KEEPALIVE_SECONDS` đã được bổ sung trong `docs/DEPLOY.md`.
- [Harness và hướng dẫn tái lập](../../../scripts/capacity/README.md); [số liệu cuối](results.json), response gốc `load-original.json`, resource JSONL và log cùng thư mục. Không lưu token/tài khoản thật trong Git.

## Bản xem thử và điểm dừng

Đã khởi động lại riêng API ở `http://127.0.0.1:18891/` bằng bản mã cuối, giữ cùng PostgreSQL/schema và dữ liệu bản xem thử. `GET /api/health` trả `status=ok`, phiên bản 1.7.15; trang chính trả HTTP 200. Realtime ở 18892 tiếp tục chạy. Đã dừng và xóa ba container/volume PostgreSQL thử tải, network thử và tệp tài khoản tổng hợp; không dừng database của bản xem thử.

Theo yêu cầu người dùng, dừng tối ưu thêm tại đây và commit/push các sửa hiệu năng cùng báo cáo. Các sửa hội chợ ngoài phạm vi đang có trong workspace không đưa vào commit này. Không deploy hay đổi PostgreSQL production.
