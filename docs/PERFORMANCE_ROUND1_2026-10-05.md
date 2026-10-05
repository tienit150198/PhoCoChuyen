# Cải thiện lần 1 — đối chiếu với bản trước lỗi tối 04/10

Mốc chuẩn là **1.7.7 trước sự cố triển khai lúc 23:07 ngày 04/10/2026**, không lấy bản đang lỗi làm chuẩn đạt yêu cầu. Đợt sửa server đã deploy xong lúc **13:44:32 ngày 05/10/2026**, không đăng thông báo trong game.

Kết luận sau đợt đầu: có giảm chi phí xử lý và trung vị request, nhưng **chưa khôi phục toàn bộ tốc độ của bản cũ, nhất là nhóm request chậm**. Phóng dao còn một regression giao diện riêng đã được tái hiện: màn chờ/kết quả bị hạ nhịp vẽ xuống khoảng 11fps; bỏ giới hạn khôi phục khoảng 60fps trong phép thử cùng trình duyệt. Xem phần xác minh rollout giao diện được bổ sung ở cuối tài liệu.

## Xác minh bản đang phục vụ

Bản sửa nhịp vẽ đã deploy xong lúc **13:57:59**, release `1.7.15-knife-smooth-20261005135629`, bản giao diện **`1.7.15+c28915a7a936`**. Đã kiểm tra trực tiếp qua HTTPS: HTML/import map trỏ đúng tệp phóng dao mới; hash tệp khớp gói đã kiểm thử. API/live/selfheal đang hoạt động, bridge đã dừng. Engine BUILD giữ `44bcdd25b2a0861f474c`, không làm toàn bộ save phải kiểm tra lạnh lần nữa. Process live được giữ; thông báo trong game không thay đổi. Dữ liệu xác minh HTTPS nằm ở `output/release-1715-knife-smooth/production-https.json`.

Người chơi đang giữ tab cũ cần tải lại một lần để nhận JavaScript mới. Đợt này cũng nâng dung lượng bộ đo lên 1.024 action/worker sau khi thấy hơn 500 loại hành động thực tế; không thay đổi xử lý tiền hay luật chơi.

Kiểm tra lúc 14:00:39: cửa sổ 119 giây có **2.338 request, 0 HTTP 5xx**. Đủ 8 API worker gửi thống kê, ghi nhận 1.863 command và **0 command bị gộp vì chạm giới hạn action** trong các worker mới. Journal từ lúc bắt đầu rollout giao diện: 0 traceback, 0 slow-command và 0 slow-lock theo ngưỡng log đang cấu hình. Đây là xác minh hoạt động sau triển khai, không chứng minh mọi request đã đạt mục tiêu độ trễ.

## 1. Tốc độ API thực tế

Log tối qua lúc 22h, khi 1.7.7 đang chạy: `/api/command` có **71.901 lượt**, P50 **120 ms**, P95 **333 ms**, P99 **500 ms**. `/api/state`: 1.312 lượt, **100 / 277 / 594 ms**. Đây là mốc lịch sử; không phải A/B trên cùng tài khoản. Một số thao tác nhẹ đạt vài chục ms, nhưng log không chứng minh tất cả thao tác tối qua đều đạt mức đó.

Hai cửa sổ 5 phút hôm nay:

- Trước đợt 1: kết thúc 2026-10-05T13:39:50.396846+07:00, tổng 6594 request.
- Sau đợt 1: kết thúc 2026-10-05T13:50:14.349191+07:00, tổng 6885 request; **0 HTTP 5xx**. Request 400/409 là nhóm lỗi nghiệp vụ/xung đột, cần phân biệt với lỗi máy chủ; 499 là client đóng kết nối.

| API | Trước: n / P50 / P95 / P99 ms | Sau: n / P50 / P95 / P99 ms |
|---|---|---|
| POST /api/command | 3867 / 160.0 / 421.0 / 700.0 | 4033 / 137.0 / 436.0 / 892.0 |
| GET /api/state | 72 / 207.0 / 775.0 / 913.0 | 132 / 211.0 / 453.0 / 632.0 |
| GET /api/business/quay | 82 / 188.0 / 355.0 / 473.0 | 109 / 176.0 / 399.0 / 539.0 |
| GET /api/work-visits/places | 150 / 64.0 / 210.0 / 317.0 | 155 / 64.0 / 238.0 / 463.0 |

`/api/command` trung vị giảm **14,4% (160 → 137 ms)**, nhưng P95/P99 **không cải thiện** trong hai mẫu này. So với bản cũ 120/333/500 ms vẫn chưa đạt. Lưu lượng command tăng từ 773 lên 807 lượt/phút giữa hai cửa sổ; mốc 22h tối qua khoảng 1.198 lượt/phút. Cơ cấu người chơi/hành động khác nhau nên không quy mọi thay đổi percentile cho bản vá.

Phần upstream của command: P50 **155 → 130 ms**, P95 **368 → 375 ms**, P99 **499 → 539 ms**. Phần chờ client/mạng cũng góp vào đuôi HTTP; không được đánh đồng toàn bộ HTTP với CPU tính game. Mẫu sau deploy đã bỏ khoảng chuyển bản nhưng vẫn có thể gặp người chơi mới vào với save chưa được kiểm tra theo BUILD mới.

## 2. Đã sửa gì và phép đo cùng đầu vào

- **Ghép dữ liệu lưu bằng UTF-8 rồi decode một lần**, tránh nhiều bản sao Unicode lớn. Định dạng JSON, dấu vân tay từng nghề và kiểm tra số không hợp lệ được giữ nguyên. Trên cùng hồ sơ production 5.780.853 byte, thử chỉ trong bộ nhớ, không ghi vào game: trung vị đóng gói **124,916 → 50,027 ms**; tính toán `business_sync` **245,417 → 184,198 ms**, 5 lần mỗi bản xen kẽ. Kết quả đầu ra bằng nhau. Đây là CPU của phép thử, không phải HTTP production.
- **Đồng bộ danh sách chỗ làm chỉ ghi khi dữ liệu đổi; gộp các dòng thay đổi.** Fixture 41 nghề không đổi: **47 → 6 SQL call, 41 → 0 lệnh upsert**. Cả 41 cùng đổi: **47 → 7 SQL call**, ghi gộp một lần. Các lệnh upsert cũ có WHERE, nên không gọi chúng là 41 lần ghi vật lý. Giữ nguyên giao dịch tiền/đơn hàng và quyền hiển thị.
- Fixture lưu đa ngôn ngữ 4,25 MB: peak allocation **52,47 → 35,07 MB**. Kiểm tra 60 trường hợp đầu vào đối chiếu hàm serialize của ZIP production: kết quả, lỗi và digest trùng nhau.
- Thêm đo **từng action** bao quanh toàn bộ `Store.command`; không ghi nội dung chat/token/ID người chơi, không thêm truy vấn DB. Dữ liệu có histogram nên percentile theo action là ước lượng cận trên, khác percentile chính xác tính từ log HTTP.

Đợt server: release `1.7.15-round1-20261005134308`, engine BUILD `44bcdd25b2a0861f474c`. Không đổi schema PostgreSQL, seed/epoch thị trường hoặc thông báo. Đã xác minh hash các tệp triển khai, process chạy đúng release, health API/live và bridge đã dừng. Có rollback về release trước mà không rollback dữ liệu người chơi.

## 3. Phóng dao so với 1.7.7

Đo module thật bằng Chromium 123, viewport 390×844, DPR2, cùng dữ liệu mô phỏng; thứ tự A/B/B/A, mỗi mẫu 4,5 giây sau warmup:

| Trường hợp | 1.7.7 | Bản fairfix trước sửa nhịp | Sau sửa nhịp |
|---|---|---|---|
| Màn chờ, CPU thường | 271 / 271 frame | 49 / 50 frame | 270–271 frame |
| Khoảng cách frame trung vị | 16,7 ms | 92,0–92,2 ms | 16,6–16,7 ms |
| Đang ngắm bia nhiều dao, CPU chậm 4× | 117 / 117 frame | 141 / 148 frame | 155 frame trong lần kiểm tra local |

Nguyên nhân chắc chắn: timer 80 ms trước mỗi frame ở preview/result. Bản sửa bỏ timer này, giữ cache hình nền/gỗ và dừng khi tab ẩn, dialog đóng hoặc chế độ giảm chuyển động yêu cầu dừng. Số dao, tốc độ bia, thời điểm tap và kết quả server không đổi. Hai bản đều nhận đủ 8/8 lần click, không dựng lại canvas/DOM trong hoạt cảnh ổn định.

Phép thử không bao gồm toàn bộ UI game, live event hoặc GPU/điện thoại thật. **Không dùng kết quả này để khẳng định mọi giật khung hình khi đang chơi đã hết.** Chi tiết và số đo gốc: `output/client-release-regression/KNIFE_177_VS_FAIRFIX.md`.

## 4. Hành động còn nặng

Mẫu đo mới có 6919 lần gọi, 577 nhóm sau khi mở rộng bước đọc. Giới hạn thu thập ban đầu 256 action/worker đã chạm trần và gộp một phần vào `__other__`; đã phát hiện và nâng lên 1.024 action/worker cùng đợt sửa giao diện. Do vậy không coi mẫu đầu là đầy đủ tuyệt đối. Bản CSV liệt kê toàn bộ nhóm được giữ, kể cả ít mẫu: `output/release-1715-round1/actions-measured.csv`.

| Hành động | n | Trung bình ms | P50 ước lượng ms | P95 ước lượng ms |
|---|---|---|---|---|
| ask | 427 | 147.569 | 150 | 400 |
| business_sync | 273 | 229.691 | 250 | 750 |
| __other__ | 259 | 168.483 | 150 | 664.894 |
| more_work | 208 | 171.043 | 150 | 400 |
| tc_pick | 129 | 170.862 | 250 | 400 |
| inv_wait | 115 | 155.213 | 150 | 400 |
| start_day | 96 | 158.746 | 150 | 400 |
| end_day | 81 | 188.031 | 250 | 400 |
| chua_put | 127 | 114.431 | 150 | 250 |
| chua_seq | 81 | 153.277 | 150 | 400 |
| desk_decide | 46 | 265.996 | 400 | 635.236 |
| advance | 79 | 151.007 | 150 | 400 |
| sit_read | 60 | 191.741 | 150 | 750 |
| hs_clean | 73 | 152.283 | 150 | 388.085 |
| ac_inspect | 37 | 286.302 | 400 | 490.197 |
| jr_deco_put | 35 | 289.154 | 250 | 678.345 |
| chua_choose | 73 | 133.226 | 150 | 400 |
| tea_add | 162 | 59.281 | 75 | 150 |
| hc_mark | 46 | 198.948 | 250 | 399.272 |
| jr_needs_eve | 54 | 168.703 | 150 | 744.931 |

Chỉ có **2 mẫu `fair_kn_throw`** trong dữ liệu đầu: trung bình **117,371 ms**, tối đa **148,006 ms**. Không đủ để kết luận P95 ổn định hoặc so sánh với tối qua (log cũ không tách action).

## 5. Hướng xử lý tiếp có căn cứ

1. **Giảm phần dữ liệu phải xử lý trên mỗi thao tác.** Save lớn vẫn đọc/parse/serialize cả khối; phóng dao vẫn phải trả chi phí chung này. Bước tiếp là xác định trường lịch sử nào chiếm dung lượng rồi chuyển phần không cần cho thao tác sang kho lịch sử đã có, giữ khả năng xem/xuất lại. Không cắt mất lịch sử hay dùng state cũ để quyết toán tiền.
2. **Tách chi phí quyết toán tiệm khỏi thao tác trò chơi một cách có kiểm soát.** `business_sync` vẫn là nhóm tốn nhiều thời gian. Đo riêng parse, settle, commit, public view; giới hạn lượng catch-up mỗi lần và giữ cursor/idempotency/tiền lương chính xác trước khi đổi. Đẩy việc sang socket đơn thuần không loại chi phí đó.
3. **Loại kiểm tra toàn bộ bị lặp khi đổi BUILD.** Hồ sơ lạnh hiện có thể kiểm tra 82 lượt nghề (2×41), trong khi kiểm tra định kỳ đã còn 41. Chỉ bỏ vòng lặp khi chứng minh đầy đủ mọi nhánh đã kiểm tra cuối cùng, không bỏ validation hàng loạt.
4. **Trace toàn bộ màn hình phóng dao nếu vẫn giật trong lúc ngắm.** Gắn thời điểm nhận state/live, render shell và frame gap trong cùng phiên; so với 1.7.7 cùng state/thiết bị. Cache canvas đang giúp active aiming trong phép thử riêng, nên chưa có căn cứ viết lại toàn bộ renderer.
5. **Chỉ tăng worker khi đo thấy thiếu CPU/queue.** Mẫu trước đợt này có 8 API worker trên 9 core nhưng tổng CPU khoảng 29%, không có lock waiter. Tăng worker hoặc chuyển socket không chữa được thao tác đơn lẻ bị nặng. Cần tiếp tục dùng CPU/DB/pool cùng cửa sổ với latency, không suy ra từ số core.

## 6. Kiểm thử

- 121 kiểm thử tích hợp/storage/scaling/fair/metrics: thành công, 3 bài được skip theo nền tảng.
- 31 kiểm thử JSON, validation, snapshot commit và memory: thành công.
- 20 kiểm thử metrics sau nâng dung lượng: thành công.
- 24 kiểm thử JavaScript hội chợ, phóng dao, refresh và cache: thành công.
- Vòng mở rộng riêng của worker có một bài cũ đòi schema 22 trong khi schema hiện tại 23; lỗi này cũng tái hiện trên hàm sync cũ. Không sửa schema để chiều theo bài kiểm thử cũ.

## 7. Toàn bộ API trong mẫu sau đợt 1

Các route ít lượt chỉ là quan sát, không phải percentile ổn định. Nhóm AI gồm thời gian chờ dịch vụ tạo câu trả lời nên được xem riêng với thao tác game thông thường.

| API | n | P50 ms | P95 ms | P99 ms | Upstream P95 ms |
|---|---|---|---|---|---|
| POST /api/command | 4033 | 137.0 | 436.0 | 892.0 | 375.0 |
| POST /api/ai/review | 19 | 6029.0 | 12794.0 | 12794.0 | 12794.0 |
| POST /api/ai/feedback | 22 | 4815.0 | 8404.0 | 10150.0 | 8386.0 |
| POST /api/ai/board | 14 | 6567.0 | 9441.0 | 9441.0 | 9442.0 |
| POST /api/ai/interview | 16 | 5413.0 | 9273.0 | 9273.0 | 9273.0 |
| GET /api/bootstrap | 41 | 289.0 | 1404.0 | 32063.0 | 790.0 |
| POST /api/ai/class | 12 | 255.0 | 7924.0 | 7924.0 | 7925.0 |
| GET /api/content | 93 | 3.0 | 538.0 | 32063.0 | 45.0 |
| GET /api/home-guests | 322 | 90.0 | 242.0 | 360.0 | 242.0 |
| GET /api/social/me | 446 | 66.0 | 141.0 | 192.0 | 141.0 |
| GET /api/state | 132 | 211.0 | 453.0 | 632.0 | 453.0 |
| GET /api/business/quay | 109 | 176.0 | 399.0 | 539.0 | 400.0 |
| GET /api/work-visits/places | 155 | 64.0 | 238.0 | 463.0 | 237.0 |
| POST /api/ai/support_call | 2 | 190.0 | 5522.0 | 5522.0 | 5523.0 |
| GET /api/work-visits/orders | 574 | 5.0 | 20.0 | 81.0 | 20.0 |
| GET /api/deco/mate | 62 | 58.0 | 120.0 | 161.0 | 121.0 |
| GET /api/marriage | 48 | 55.0 | 299.0 | 401.0 | 299.0 |
| GET /api/news | 460 | 5.0 | 16.0 | 71.0 | 15.0 |
| GET /api/work-visits/place | 6 | 79.0 | 627.0 | 627.0 | 627.0 |
| GET /api/garage/spouse | 44 | 23.0 | 127.0 | 178.0 | 128.0 |
| GET /api/leaderboard | 9 | 176.0 | 351.0 | 351.0 | 352.0 |
| POST /api/beacon | 108 | 5.0 | 41.0 | 56.0 | 32.0 |
| POST /api/marriage/friend_search | 5 | 187.0 | 330.0 | 330.0 | 52.0 |
| GET /api/quay | 6 | 144.0 | 211.0 | 211.0 | 211.0 |
| POST /api/quay/post | 1 | 867.0 | 867.0 | 867.0 | 868.0 |
| POST /api/marriage/respond | 1 | 466.0 | 466.0 | 466.0 | 467.0 |
| POST /api/marriage/ring_buy | 1 | 426.0 | 426.0 | 426.0 | 427.0 |
| GET /api/feedback/mine | 2 | 158.0 | 233.0 | 233.0 | 232.0 |
| GET /api/board | 10 | 19.0 | 46.0 | 46.0 | 46.0 |
| POST /api/gift/seen | 10 | 8.0 | 149.0 | 149.0 | 149.0 |
| POST /api/marriage/propose | 1 | 174.0 | 174.0 | 174.0 | 175.0 |
| POST /api/feedback | 1 | 170.0 | 170.0 | 170.0 | 170.0 |
| GET /api/wedding/race | 2 | 39.0 | 126.0 | 126.0 | 125.0 |
| GET /api/health | 112 | 1.0 | 2.0 | 3.0 | 2.0 |
| POST /api/marriage/lookup | 1 | 57.0 | 57.0 | 57.0 | 57.0 |
| GET /api/rentals | 1 | 41.0 | 41.0 | 41.0 | 41.0 |
| POST /api/marriage/quote | 2 | 12.0 | 29.0 | 29.0 | 29.0 |
| GET /api/market | 2 | 1.0 | 3.0 | 3.0 | 3.0 |
