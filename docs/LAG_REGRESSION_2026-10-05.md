# Nguyên nhân lag sau cập nhật tối 04/10/2026

Đối chiếu lúc 13:10–13:25 ngày 05/10, giờ Việt Nam. Kết luận: có regression thật do đợt triển khai và thay đổi phần mềm. Không có cơ sở quy toàn bộ hiện tượng cho mạng người chơi hoặc thiếu 9 core. Đã đọc 2.732.762 dòng log API từ 00:00 ngày 04/10 đến khoảng 13:11 ngày 05/10; dữ liệu chỉ tổng hợp đường dẫn, số lượt và thời gian, không xuất nội dung người chơi.

## 1. Diễn biến đã xác nhận

- 23:00–23:06: command P95 mỗi phút 333–367 ms, khoảng 1.100–1.300 lệnh/phút.
- **23:07–23:14: sự cố triển khai.** Migration sửa tên giữ DDL lock rồi đợi save đang được cập nhật; phát sinh deadlock/chặn truy vấn. P95 command khoảng 12 giây. Riêng 23:09 có 171 mã 502; có nhiều 503 và 499 trong đoạn sự cố. Tài liệu triển khai ghi giao dịch lỗi đã rollback, sửa tách DDL khỏi backfill tên rồi chạy tiếp. Đây là lỗi triển khai, không phải thiếu core.
- 23:15–23:19: bản cũ phục hồi, command P95 210–358 ms, lưu lượng đã giảm.
- **23:20:48: 1.7.8 thực sự khởi động.** Sau đó độ trễ tăng dù không còn sự cố migration: 23:25–23:29 command P95 1.289–1.651 ms. Bản này thêm full-state polling, xử lý tiệm tự động và hook ghé chỗ làm vào đường chung của mọi command.
- 23:53:49: 1.7.9 khởi động; 23:54 P95 command 445 ms, so với 1.749 ms phút 23:53. Đã loại nhiều lần sao chép/đọc thừa, nhưng vẫn cao hơn trước cập nhật và còn đọc nền.
- Sáng 05/10 có thêm tính năng và nhiều lần đổi BUILD. Mỗi đổi BUILD lại khiến save phải đi qua kiểm tra lạnh. Một số bản vá cải thiện CPU thực sự, song không giải quyết hết luồng đồng bộ toàn save và chi phí giao diện.

Giờ đóng gói trong MANIFEST không phải giờ deploy. Mốc trên đã đối chiếu journal và log theo phút. Số theo giờ dưới đây bao gồm cả chuyển bản, không được coi là benchmark A/B cùng người chơi.

| Giờ | API | Lượt | P50 ms | P95 ms | P99 ms |
|---|---|---|---|---|---|
| 2026-10-04 22:00 | GET /api/state | 1312 | 100.0 | 277.0 | 594.0 |
| 2026-10-04 22:00 | POST /api/command | 71901 | 120.0 | 333.0 | 500.0 |
| 2026-10-04 23:00 | GET /api/state | 5355 | 319.0 | 2396.0 | 3835.0 |
| 2026-10-04 23:00 | POST /api/command | 46075 | 243.0 | 1915.0 | 12000.0 |
| 2026-10-05 00:00 | GET /api/state | 9142 | 140.0 | 562.0 | 837.0 |
| 2026-10-05 00:00 | POST /api/command | 58001 | 176.0 | 486.0 | 747.0 |
| 2026-10-05 09:00 | GET /api/state | 13784 | 159.0 | 500.0 | 837.0 |
| 2026-10-05 09:00 | POST /api/command | 29885 | 170.0 | 508.0 | 839.0 |
| 2026-10-05 11:00 | GET /api/state | 12794 | 186.0 | 797.0 | 1135.0 |
| 2026-10-05 11:00 | POST /api/command | 39969 | 168.0 | 547.0 | 929.0 |
| 2026-10-05 12:00 | GET /api/state | 5623 | 214.0 | 668.0 | 967.0 |
| 2026-10-05 12:00 | POST /api/command | 45104 | 159.0 | 451.0 | 685.0 |

## 2. Thay đổi nào gây nặng

1. **Bản 1.7.8 thêm tải toàn state mỗi 5 giây khi bất kỳ nghề nào có nhân viên đang hoạt động.** Poll vẫn chạy khi chơi hội chợ. Mỗi lần nhận state gọi lại render giao diện chung. Repro 60 giây: 12 lượt tải/render mới so với bản trước không có poll này. Bản market trưa nay đã giảm còn 30 giây và bỏ lượt nếu vừa đồng bộ; vẫn còn chạy khi mở hội chợ trước bản vá đang chuẩn bị.
2. **Bản 1.7.8 đọc/parse full save thêm trong transaction.** Hai hook parse save cũ riêng, ba lần ở settings; dựng offer còn deepcopy toàn bộ 41 nghề. 1.7.9 đã gom parse/copy; bản quay 12:40 hôm nay bỏ lần đọc/parse thừa còn lại. Không được tiếp tục mô tả những lỗi đã sửa này là còn nguyên trên production.
3. **Quyết toán tiệm chạy trước mọi lệnh**, kể cả fair_kn_throw. Có backlog offline thì một lượt bấm phải trả luôn chi phí dựng/hoàn thành đơn, lịch sử, lương và doanh thu của các tiệm. 1.7.10 cho hoạt động liên tục và thêm một ledger entry cho thưởng lãi; 1.7.12/14 thêm sự kiện quán/nhân viên. Benchmark cùng fixture 1.024 đơn: compute 1.7.9 ~296 ms, 1.7.10 ~400 ms, 1.7.14 ~447 ms. Các tối ưu 1.7.15 giảm còn ~110 ms ở current. Đây là CPU local, không phải HTTP production. Khi không có backlog, compute cùng fixture giữ quanh 40 ms; không thể đổ mọi giây chờ cho vòng settle rỗng.
4. **Phóng dao bản 1.7.10 chờ hiệu ứng hai lần.** Cùng lần ném cuối, server trả tức thì: kết quả thắng từ 730 lên 1.380 ms; thua từ 780 lên 1.430 ms. Đây là chờ chủ động trong client, khác với FPS khi đang ngắm. Đã sửa local và kiểm thử giữ nguyên kết quả do server quyết định.
5. **Nút thắt còn tồn tại:** save nhiều MB vẫn bị parse/serialize cả khối; work_visits.sync duyệt các nghề đã mở và thử upsert mỗi nghề sau command; kiểm tra lạnh còn hai vòng 41 nghề, kiểm tra định kỳ còn một vòng. Có 49 SQL call trong fixture 41 nghề đã mở ở audit trước, không được gọi đó là 49 lần ghi vật lý vì upsert có WHERE chỉ đổi data khi khác.

Đối chiếu mã: thân public_state và state-listener/render chính không thay đổi giữa 1.7.4 và các bản được so. Không có bằng chứng “mới dựng full view cả 41 nghề”; chi phí render cũ bị gọi nhiều hơn bởi poll mới. Mã world.js cùng hash trên các bản so. Sáu client beacon chỉ cho thấy có long task (max 336 ms), render đồng bộ max 99 ms; mẫu quá ít và không riêng hội chợ để kết luận hết nguyên nhân giật khung hình.

## 3. Tất cả API trong mẫu 12:55:41–13:10:41

P95 = 95% request hoàn tất trong khoảng này. Thời gian Nginx bao gồm cả gửi dữ liệu; upstream là phần chờ ứng dụng. Xếp theo tổng thời gian request cộng dồn để thấy tác động, **không phải tổng CPU**. API chỉ 1–3 mẫu không đại diện được percentile ổn định. 400/409 là lỗi nghiệp vụ/xung đột cần xem riêng, 499 là client đóng kết nối.

| API | n | P50 ms | P95 ms | P99 ms | Max ms | Upstream P95 ms | Tỷ trọng thời gian | Mã khác 200 |
|---|---|---|---|---|---|---|---|---|
| POST /api/command | 11530 | 145.0 | 381.0 | 586.0 | 15000.0 | 359.0 | 54.4% | 400: 75, 409: 9, 408: 2, 499: 1 |
| POST /api/ai/feedback | 118 | 4389.0 | 6765.0 | 7661.0 | 9316.0 | 6766.0 | 11.6% | — |
| POST /api/ai/review | 115 | 4754.0 | 8350.0 | 9085.0 | 10594.0 | 8351.0 | 10.0% | — |
| POST /api/ai/board | 56 | 5159.0 | 6931.0 | 8218.0 | 8218.0 | 6930.0 | 5.6% | — |
| GET /api/state | 413 | 279.0 | 619.0 | 926.0 | 1342.0 | 603.0 | 3.1% | 499: 3 |
| GET /api/home-guests | 1140 | 80.0 | 225.0 | 357.0 | 434.0 | 226.0 | 2.9% | 499: 2 |
| GET /api/business/quay | 368 | 326.0 | 596.0 | 817.0 | 877.0 | 596.0 | 2.8% | — |
| GET /api/social/me | 1362 | 64.0 | 143.0 | 208.0 | 469.0 | 143.0 | 2.6% | 499: 4 |
| POST /api/ai/interview | 16 | 3768.0 | 6052.0 | 6052.0 | 6052.0 | 6052.0 | 1.3% | — |
| GET /api/bootstrap | 130 | 215.0 | 1208.0 | 1909.0 | 2605.0 | 1149.0 | 1.2% | 499: 1 |
| GET /api/work-visits/places | 569 | 60.0 | 214.0 | 297.0 | 1342.0 | 199.0 | 1.2% | 499: 3 |
| POST /api/ai/chat | 9 | 4862.0 | 6771.0 | 6771.0 | 6771.0 | 6771.0 | 1.1% | — |
| GET /api/content | 285 | 3.0 | 201.0 | 1521.0 | 1909.0 | 41.0 | 0.4% | — |
| GET /api/work-visits/orders | 2149 | 5.0 | 24.0 | 65.0 | 260.0 | 25.0 | 0.4% | 499: 1 |
| POST /api/ai/class | 6 | 233.0 | 4449.0 | 4449.0 | 4449.0 | 4449.0 | 0.3% | — |
| GET /api/news | 1384 | 4.0 | 13.0 | 68.0 | 390.0 | 13.0 | 0.2% | — |
| GET /api/marriage | 82 | 57.0 | 265.0 | 411.0 | 411.0 | 265.0 | 0.2% | — |
| GET /api/garage/spouse | 163 | 23.0 | 87.0 | 154.0 | 156.0 | 87.0 | 0.1% | — |
| GET /api/work-visits/place | 13 | 359.0 | 613.0 | 613.0 | 613.0 | 613.0 | 0.1% | — |
| POST /api/beacon | 389 | 2.0 | 22.0 | 106.0 | 661.0 | 9.0 | 0.1% | 403: 236, 204: 149, 499: 3, 401: 1 |
| GET /api/quay | 11 | 206.0 | 293.0 | 293.0 | 293.0 | 293.0 | 0.1% | — |
| GET /api/home-guests/view | 3 | 438.0 | 447.0 | 447.0 | 447.0 | 447.0 | 0.0% | — |
| POST /api/marriage/family_child_care | 3 | 393.0 | 474.0 | 474.0 | 474.0 | 474.0 | 0.0% | — |
| POST /api/work-visits/cancel | 1 | 905.0 | 905.0 | 905.0 | 905.0 | 905.0 | 0.0% | — |
| GET /api/rentals | 23 | 27.0 | 68.0 | 83.0 | 83.0 | 67.0 | 0.0% | — |
| POST /api/bank/xfer/send | 1 | 677.0 | 677.0 | 677.0 | 677.0 | 677.0 | 0.0% | — |
| GET /api/board | 26 | 24.0 | 49.0 | 50.0 | 50.0 | 49.0 | 0.0% | — |
| GET /api/health | 360 | 1.0 | 2.0 | 9.0 | 44.0 | 3.0 | 0.0% | — |
| GET /api/leaderboard | 4 | 68.0 | 244.0 | 244.0 | 244.0 | 243.0 | 0.0% | — |
| POST /api/bank/xfer/receive | 1 | 322.0 | 322.0 | 322.0 | 322.0 | 323.0 | 0.0% | — |
| POST /api/gift/seen | 34 | 5.0 | 35.0 | 41.0 | 41.0 | 15.0 | 0.0% | — |
| POST /api/home-guests/answer | 1 | 291.0 | 291.0 | 291.0 | 291.0 | 290.0 | 0.0% | — |
| GET /api/bank/xfer | 3 | 63.0 | 64.0 | 64.0 | 64.0 | 65.0 | 0.0% | — |
| POST /api/marriage/seen | 1 | 158.0 | 158.0 | 158.0 | 158.0 | 157.0 | 0.0% | — |
| POST /api/account/login | 1 | 116.0 | 116.0 | 116.0 | 116.0 | 115.0 | 0.0% | — |
| POST /api/marriage/settings | 1 | 44.0 | 44.0 | 44.0 | 44.0 | 43.0 | 0.0% | — |
| POST /api/work-visits/visibility | 3 | 7.0 | 20.0 | 20.0 | 20.0 | 6.0 | 0.0% | — |
| GET /api/feedback/mine | 1 | 33.0 | 33.0 | 33.0 | 33.0 | 32.0 | 0.0% | — |
| GET /api/market | 10 | 2.0 | 7.0 | 7.0 | 7.0 | 7.0 | 0.0% | — |

Nhóm AI có P95 6–8 giây và cần tách thời gian đợi nhà cung cấp khỏi đọc/ghi save. Không nên dùng các số này để kết luận Python tính game mất 8 giây. `/api/command` chiếm phần lớn thời gian cộng dồn và bao gồm nhiều nghề/trò chơi. Log HTTP hiện không lưu action, nên không thể suy ngược P95 phóng dao từ P95 chung.

## 4. Riêng phóng dao và bản lưu lớn

Thống kê action từ DB là số lần được retention ghi nhận, khác đơn vị số HTTP (có retry/receipt), không có latency đi kèm. Ngày 05/10 là phần ngày tới lúc lấy mẫu; không so tốc độ chơi với cả ngày 04/10.

| Ngày | Action | Lượt | Lỗi |
|---|---|---|---|
| 2026-10-04 | fair_kn_throw | 12298 | 0 |
| 2026-10-04 | fair_kn_next | 9989 | 1 |
| 2026-10-04 | fair_kn_start | 2315 | 0 |
| 2026-10-04 | fair_kn_stop | 649 | 0 |
| 2026-10-05 | fair_kn_throw | 1362 | 3 |
| 2026-10-05 | fair_kn_next | 992 | 3 |
| 2026-10-05 | fair_kn_start | 366 | 2 |
| 2026-10-05 | fair_kn_stop | 85 | 3 |

Slow log từ 22:30 tối qua: fair_kn_next có 2 mẫu trên ngưỡng, tối đa 3.583 ms, trung bình phần store 2.538 ms; fair_kn_start có 1 mẫu 4.476 ms. Đây là log có ngưỡng và bị giới hạn số dòng/phút, không phải mọi request và không thể tính P95 toàn trò từ ba mẫu. Mẫu 3.583 ms lúc 23:20:17 nằm trong giai đoạn chuyển bản.

Đo chỉ đọc trên production, save 5.739.134 bytes/41 nghề: lấy một snapshot trong bộ nhớ, không ghi save hoặc xuất nội dung người chơi. Cùng input cho ba lần mỗi case, cố định đồng hồ; chuẩn bị lượt dao chỉ trong bản sao. Thời gian dưới đây **chưa bao gồm commit DB, HTTP, mạng hoặc trình duyệt**. Một lần SELECT ban đầu 63,64 ms.

| Case | Median compute ms | Ba lần đo ms | Public-view ms | JSON response ms |
|---|---|---|---|---|
| business_sync | 245.04 | 246.07, 245.04, 214.42 | 37.96, 37.22, 24.61 | 25.85, 25.97, 25.36 |
| knife_start | 256.19 | 287.63, 255.11, 256.19 | 25.47, 25.37, 25.06 | 26.23, 26.81, 25.66 |
| knife_throw | 267.62 | 318.1, 263.94, 267.62 | 26.1, 25.16, 25.18 | 26.03, 25.46, 25.47 |
| periodic_audit | 723.81 | 723.81, 753.53, 718.3 | 127.38, 27.96, 38.43 | 25.77, 26.65, 26.31 |
| cold_build | 1246.0 | 1279.44, 1198.85, 1246.0 | 38.63, 25.79, 39.22 | 25.74, 25.66, 25.64 |

Profile phóng dao cho thấy parse/serialize và kiểm tra dữ liệu chiếm phần lớn, không phải phép tính xác định dao. cProfile tự thêm overhead nên chỉ dùng phân rã, không trộn số profile với median phía trên. Cold BUILD còn 82 lần validate_career; deploy liên tiếp làm nhiều người gặp chi phí này lại.

## 5. Chín core đang được dùng thế nào

Mẫu 30 giây 12:57:37–12:58:07: CPU toàn máy bận 29,1%, từng core 22,3–36,1%; iowait 0,2%, steal 0. API có 8 worker được phép chạy trên cả CPU0–8; mỗi worker dùng trung bình 20,3–28,3% một core, tổng khoảng 2,1 core. Live khoảng 0,08 core. Cgroup không bị throttling. API quota 800%, live 150% là trần dùng chung CPU, không phải đã chia cố định từng core.

PG max_connections 200; snapshot có 49 connection idle, 1 active WALSync, không có lock waiter. Hai log pool mới có waited=0/timedout=0. Số này chứng minh không nghẽn tài nguyên ở thời điểm lấy mẫu, không phủ nhận quá tải trước đó. Báo cáo tối 04/10 đã ghi load 9,78 và 8 worker ~71–73% một core sau 1.7.8.

Hướng phân tải: giữ 8 HTTP worker đang phân bố được trên 9 core trong đợt chẩn đoán, không tăng thread/worker tùy tiện. Phần Python của một thao tác tuần tự không tự nhanh gấp 9 vì thêm core. Nếu tách queue/job thực sự, cấu hình thử nghiệm hợp lý là khoảng 6 worker cho thao tác tương tác, 1 tiến trình quyết toán nền có quota, tài nguyên còn lại dùng chung cho live/PG/nginx/OS; phải đo trước/sau ở cùng tải mới áp dụng. Không hard-pin ngay một core cho mỗi dịch vụ vì PG và I/O cũng cần linh hoạt.

## 6. Xử lý theo thứ tự và điều kiện xác minh

1. Bản vá giao diện: bỏ lần chờ thừa, dừng staff full-refresh khi fair mở. 27 tests đã qua, gồm thời gian phản hồi 0/200/1.000 ms, thắng/thua, kết quả từ server, đóng màn và kết quả cũ. Thời gian thắng sau sửa 730/850/1.650 ms tương ứng; mạng chậm vẫn phải đợi server. Bản vá chỉ thay ba JS cùng hai test, server/game/live và Có gì mới giữ nguyên byte. Trạng thái deploy sẽ ghi riêng sau khi kiểm tra trên production.
2. Ghi histogram có giới hạn theo action + phase ở đường HTTP để biết P95 từng nghề và fair_kn_* mà không log nội dung chat. Hiện mới có tổng API, count từng action và slow log theo ngưỡng. Phải thêm đo này trước khi tuyên bố tất cả trò đã nhanh.
3. Tách discovery chỗ làm khỏi critical commit: chỉ dựng/upsert nghề/quầy có dữ liệu hiển thị thay đổi, gộp query; chuyển cập nhật bảng khám phá sang outbox có version. Hook hoàn thành đơn, chuyển tiền, receipt và CAS vẫn phải nguyên tử. Kiểm tra lại đặt đơn đồng thời/hoàn tiền/nhân viên trước khi deploy.
4. Tách quyết toán backlog khỏi một lượt ném dao: worker xử lý theo lô có checkpoint, không quá một worker cho cùng save; command có thể quyết toán phần tiền thực sự cần dùng. Giữ nợ công việc, tiền lương, doanh thu và idempotency; không cắt bỏ đơn để đạt tốc độ.
5. Tách phiên bản quy tắc validation khỏi thay đổi code không ảnh hưởng dữ liệu, tránh ép full migration sau mọi deploy. Không bỏ kiểm tra đầu vào hoặc chỉ tăng FULL_EVERY để che chi phí. Giảm save nhiều MB bằng tách lịch sử ra bảng có reader tương đương; feed còn tương tác, không xóa tùy ý.
6. AI: ghi riêng thời gian upstream; hiển thị kết quả từng phần/không chặn thao tác không liên quan nếu flow cho phép. Giật khung hình: đo rAF/long-task trên cùng cảnh và cùng thiết bị trước/sau chặn poll, không suy từ P95 HTTP.

Tiêu chí: so cùng fixture/same action, rồi theo dõi production đủ tải và phân loại client cũ/mới; P95/P99, tỷ lệ >1 giây, 5xx/409, CPU/poolwait, frame gaps. Không lấy chỉ health 200 hoặc cửa sổ một phút làm bằng chứng “hết lag”.

## Bằng chứng và giới hạn

- `output/lag-9core-20261005/lag-regression-api.json`, `api-last15m.csv`: tất cả route gần đây + chuỗi theo giờ.
- `lag-regression-minutes.json`: mốc 22:45–23:59, đối chiếu gián đoạn/migration và bản 1.7.8/9.
- `lag-regression-counts.json`, `actions-daily.csv`: action count và tổng hợp slow log, không có latency đầy đủ từng action.
- `lag-regression-actions.json`: profile trên snapshot production chỉ trong bộ nhớ; số đo không phải end-to-end.
- `lag1715-cores.json`, `lag1715-client-db.json`, `lag1715-workers-log.json`: mẫu CPU/pool/client.
- `output/client-release-regression/FINDINGS.md`, `compare-client.mjs`, `timings.json`: release boundary và repro client.
- `output/server-release-regression/REPORT.md`, `benchmark_releases.py`: so cùng snapshot tổng hợp giữa các release.
- `docs/DEPLOY_1.7.8_2026-10-04.md`, `API_PERFORMANCE_2026-10-04.md`, `DEPLOY_1.7.9_2026-10-04.md`: sự cố và sửa tối qua.

Chưa chứng minh mọi máy đã mượt hoặc mọi API đã đạt mục tiêu. Các phép đo hiện tại đủ xác nhận regression và chỉ ra đường xử lý; phần backlog/SQL/schema/AI còn cần triển khai có kiểm chứng.

## Bản vá giao diện đã triển khai 13:25:49 ngày 05/10

Đã đưa lên release `1.7.15-fairfix-20261005132402`, health `1.7.15+602da73fbd90`. ZIP SHA256 `f9a868fa1ccb8c2e1e017deddf281dbdace6f301d3489da4c0d662f93229b0c6`. Chỉ ba JS và hai test khác bản quay trước; tất cả server/game/live giữ nguyên byte, engine BUILD vẫn `34ef1ebde874e22baf55`, schema và Có gì mới giữ nguyên. 27 tests đạt; 1.306 manifest entries kiểm tra hash; HTML import map và bốn asset HTTPS (gồm thông báo) đúng hash; ba health HTTPS đúng build mới.

Chuyển qua bridge để phục vụ HTTP khi canonical restart. Script bắt đầu 13:24:51, kết thúc 13:25:49, mã thoát 0; bridge đã dừng, nginx trở về 8765, game/live/selfheal active. Live PID trước/sau đều 2425122, không restart dịch vụ live. Nginx vẫn có hai lần graceful reload và timeout đóng worker cũ 20 giây; vì vậy không khẳng định mọi socket của người chơi giữ nguyên kết nối. Live sau chuyển có 99 kết nối, cut=0; chỉ số này không bao quát mọi lần ngắt ở proxy.

Mẫu 103 giây bao gồm cutover: 2.561 API, không 5xx; có 46 mã403, 52 mã400, 2 mã409, 15 mã499. Command 1.370 lượt, P50/P95/P99 159/433/890 ms; state 51 lượt, 194/1.028/1.126 ms; quầy 53 lượt, 199/444/633 ms. Đây là số theo dõi chuyển bản, không phải bằng chứng bản vá JS đã giảm P95 server. Client đang mở bản cũ cần tải lại để nhận JS mới. Không có Traceback/slow-cmd/slow-lock trong log mẫu; còn hai cảnh báo khởi động `fork()` sau khi có thread, cần rà riêng, chưa có bằng chứng chúng gây deadlock ở lần này.

Outlier command14.721 ms là HTTP499, upstream chưa có (`urt=-`). Các lượt khác request_time2.067–4.183 giây có upstream0.058–0.174 giây, cho thấy một phần chờ ở ngoài thời gian ứng dụng; không được quy chúng thành CPU xử lý command 4–15 giây. Hai lượt upstream1.130/1.375 giây lúc chuyển bản vẫn còn chậm. Không che các outlier bằng trung vị hoặc dùng chúng để phủ nhận regression đã đo tối qua.

Bằng chứng triển khai: `output/release-1715-fairfix/package.json`, `production-https.json`, `mnl1715-fairfix-verified.json`. Bản vá chỉ xử lý hai regression giao diện đã tái hiện; các hạng mục server trong mục6 vẫn chưa triển khai.
