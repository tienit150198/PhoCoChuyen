# Độ trễ giờ cao điểm 05/10/2026 — bản 1.7.15

## Kết luận và phạm vi đo

Không có bằng chứng tất cả API chậm hơn sau 1.7.15. Có những lượt đứng/chờ thực sự: kiểm tra toàn bộ bản lưu lớn, màn chuẩn bị nghề bị lỗi JavaScript, tải lại giao diện và gọi AI. Health chỉ chứng minh dịch vụ còn trả lời; không đại diện trải nghiệm chơi.

Nguồn: log Nginx, journal game/live, tài nguyên máy, PostgreSQL và bộ đếm lỗi/tải trang. Đo reducer bằng bản lưu production trong RAM với kết nối database chỉ đọc; không lưu nội dung người chơi ra file, không ghi kết quả mô phỏng, không phát sinh tải thử đông người. Benchmark được hạ ưu tiên CPU.

## So sánh API (UTC+7)

Hai khoảng 5 phút: trước 11:17:18–11:22:18; ngay sau 11:23:30–11:28:30. P95 là thời gian 95% yêu cầu hoàn thành; thời gian tại proxy chưa bao gồm toàn bộ mạng người chơi và vẽ màn hình. Hai cửa sổ khác người dùng/thao tác nên không phải A/B nhân quả.

| API | Số yêu cầu trước/sau | Trung vị trước/sau | P95 trước/sau |
|---|---:|---:|---:|
| Thao tác `/api/command` | 3.471 / 3.114 | 167 / 169 ms | 574 / 495 ms |
| Đồng bộ `/api/state` | 919 / 978 | 227 / 184 ms | 798 / 801 ms |
| Hộp đơn ghé tiệm | 563 / 543 | 5 / 5 ms | 30 / 28 ms |
| Danh sách tiệm | 149 / 181 | 68 / 68 ms | 255 / 340 ms |
| Vào game `/api/bootstrap` | 19 / 85 | 211 / 260 ms | 1.834 / 1.365 ms |
| Phản hồi AI | 38 / 34 | 4.489 / 4.904 ms | 14.201 / 7.982 ms |

Cửa sổ sau ổn định hơn 11:33:18–11:38:18: command 2.563 yêu cầu, trung vị 182 ms, P95 574 ms; state 1.115 yêu cầu, trung vị 174 ms, P95 772 ms; danh sách tiệm 129 yêu cầu, trung vị 68 ms, P95 190 ms. Lượt bootstrap giảm về 36. Vì vậy danh sách tiệm chậm hơn ở cửa sổ đầu chưa chứng minh một regression kéo dài.

Sau deploy ở cửa sổ đầu: command có 16 lượt >=1 giây, state 15 lượt >=1 giây. 36 phản hồi command HTTP 409 tương ứng xung đột tiến trình, có thể cần đồng bộ/gửi lại nên làm người chơi đợi thêm. Các HTTP 499 là client ngắt yêu cầu, chưa đủ kết luận rớt socket. Không thấy HTTP 5xx trong các API có số đo upstream hợp lệ của hai cửa sổ này.

## Nguyên nhân đã xác nhận

1. **Bản lưu nguyên khối và kiểm tra định kỳ.** Mẫu lớn 5,54 MB: compute bình thường 213–258 ms sau warmup; ở lượt kiểm tra toàn bộ sau mỗi 50 revision: 1.181–1.262 ms (đo không gắn profiler). Profiler chỉ dùng xác định vị trí: full validation bị gọi hai lần, tổng 82 lượt validate_career cho 41 nghề. Log thực tế có command 1.635–2.092 ms, compute 1.285–1.624 ms, store 156–382 ms. Mẫu sau nữa có business_sync tổng 1.727 ms, compute 1.222 ms, store 436 ms.
2. **Mỗi bản code mới đổi build stamp.** Lượt đầu của bản lưu trên build mới phải migration/kiểm tra toàn bộ. Cache worker cũng nguội khi restart. Điều này có thể làm chậm rõ hơn ngay sau deploy, nhưng không giải thích hết các lượt định kỳ về sau.
3. **Màn chuẩn bị nghề bị lỗi.** careerContext dùng state.current trực tiếp; trước ca, current có thể null và nghề đang chọn ở state.focus. Đọc room.tasks khi room undefined làm render throw. Tái hiện local đúng stack production. Bộ đếm ngày có 67 sự kiện cùng nhóm lỗi, last_at 11:26:41; không phải 67 người và không phải tất cả phát sinh sau deploy. File này không đổi trong 1.7.15: đây là lỗi cũ còn tồn tại.
4. **Chi phí tải lại giao diện.** Ngay sau deploy, bootstrap 19→85 lượt/5 phút. Cơ chế update có tự tải lại khi tab trở lại và đang rảnh. Chưa có dữ liệu tách chính xác người tự refresh với auto reload. Telemetry cả ngày 05/10: 361 cold-load, hình đầu tiên trung vị 2.411 ms/P90 6.464 ms; 447 warm-load, 1.925/P90 4.482 ms. Đây là thống kê cả ngày, không dùng làm bằng chứng riêng cho 1.7.15.
5. **AI có độ trễ riêng.** Các endpoint AI thường mất 4–8 giây, có mẫu trước deploy 20 giây. Cần trạng thái chờ riêng và tách khỏi hàng đợi tương tác; tối ưu reducer không tự làm AI nhanh hơn.

## Chưa có bằng chứng là nguyên nhân chính

- CPU 9 vCPU, mẫu vmstat còn 52–68% idle, RAM available khoảng 8,6 GB, không swap; chưa thấy thiếu máy là nguyên nhân chính. Mức này không loại trừ một worker có lúc chờ hoặc GIL tranh CPU.
- PostgreSQL snapshot chủ yếu idle; không thấy chờ khóa kéo dài trong mẫu. Một lần slow-write 790 ms cần theo dõi, không suy ra toàn DB nghẽn.
- Live có 92 người/kết nối, cut=0 sau 397 giây; journal có restart 1012 khi deploy, không có lỗi chương trình. cut chỉ đếm cơ chế cắt người nhận chậm, không chứng minh mạng mọi người ổn.
- Giá vàng + coin: hai quote khoảng 0,018–0,031 ms khi nóng, khoảng 1 ms cold trong mẫu. Không có bằng chứng bộ giá làm toàn server lag.
- Chưa có đo FPS/INP trực tiếp từ điện thoại đang phản ánh. Benchmark hội chợ trước đó là Chromium giả lập, không thay thế được số đo thiết bị thật.

## Bản sửa hẹp đang kiểm chứng

- Với bản lưu đã được build hiện tại kiểm tra, lượt audit định kỳ giữ kiểm tra trung gian theo phạm vi và kiểm tra TOÀN BỘ kết quả cuối đúng một lần trước khi ghi. Vẫn chạy mỗi 50 revision. Lỗi dữ liệu trong audit phải bị từ chối; không bỏ kiểm tra tiền/hàng, không tăng chu kỳ để che độ trễ. Bản cũ/import giữ đường kiểm tra đầy đủ.
- careerContext chọn current, rồi focus, rồi nghề mặc định giống app.js, sửa màn chuẩn bị trước ca.
- Bỏ kiểm tra trùng nội dung trong store_message: các tin trùng là các bản ghi có ID khác nhau, cả DM/nhóm/phố/reply. Giữ phân quyền và các cơ chế còn lại.
- Không đổi schema PostgreSQL, seed/mốc thị trường, tỷ lệ kinh tế hay nội dung Có gì mới.

Kiểm chứng: regression đã bắt 82 so với 41 lượt; so sánh toàn state/result/serialized/archive, dữ liệu sai phải bị từ chối; chat dùng WebSocket thật và PostgreSQL; UI kiểm tra trước ca/during shift/default. Nhóm 97 tests có một timeout HTTP local, chạy lại riêng nhóm 3 business_storage đạt; các bài còn lại đạt. Nhóm 296 tests có 1 skipped và 1 test daily fund cap thất bại giống hệt trên nguồn 1.7.15 cũ; không do bản vá, không sửa kỳ vọng để che. Gói giải nén độc lập vượt qua kiểm tra hash, server, HTTP workflow và idempotency.

## Hướng xử lý tiếp theo, theo ưu tiên

| Ưu tiên | Việc | Mục tiêu và ràng buộc |
|---|---|---|
| Ngay | Sửa quét trùng + lỗi chuẩn bị nghề; đo sau triển khai | Giảm các cú khựng đã tái hiện, không thay luật tiền/hàng |
| Cao | Tách lịch sử nguội khỏi snapshot nóng | Không đọc/serialize nhiều MB cho một thao tác nhỏ; giữ xem lại lịch sử bằng phân trang, không xóa dữ liệu |
| Cao | Tách endpoint trạng thái quầy/giá/khách thành payload nhỏ | Poll 5 giây không kéo và render lại toàn trạng thái game; giữ revision và tính tiền nguyên tử |
| Cao | Đo thời gian client sau nhận API: parse, apply state, render, long task/INP | Tách “server chậm” khỏi “điện thoại vẽ chậm”; lấy mẫu giới hạn để không tự gây tải |
| Cao | Kiểm tra telemetry bị từ chối | Cửa sổ đầu sau deploy có 105 beacon 403/210 yêu cầu; phải xác định Origin/Sec-Fetch-Site trước khi chỉnh, không bỏ kiểm tra nguồn |
| Sau | Giảm render DOM/canvas không đổi theo từng cảnh nghề | Đo trên máy yếu và Safari, không đổi timing thao tác hay giấu khách thực tế |
| Sau | Cải thiện trạng thái chờ AI/cache phù hợp | Không chặn các thao tác độc lập trong lúc đợi AI |

Tiêu chí theo dõi: API p50/p95/p99 theo endpoint và nhóm kích thước save; compute/store riêng; tỷ lệ 409/5xx; số full audit; client long task và thời gian tới thao tác được. Không tuyên bố hết lag chỉ vì health 200.

## Luồng tải thừa được xác định tiếp lúc 12:09

`work-equipment.js` trước vá chạy `api.refresh()` mỗi 5 giây khi có nhân viên ở bất kỳ nghề nào, kể cả khi xem Đầu tư. `/api/state` đọc snapshot, chạy `business.on_load_result`, có thể ghi settlement rồi trả toàn bộ public state. `app.js` nhận state lại renderMain/renderSheet/shell. Khi mở Quầy, `createQuayPoller` còn có vòng riêng. API chỉ gộp các request đang đồng thời chờ, không gộp những vòng bị lệch nhịp. Đây là tải dư có đường gọi cụ thể, không phải suy luận rằng phép tính giá coin nặng.

Đầu tư trước vá chỉ có timer theo phiên 10 phút, nhưng gọi cùng API toàn trạng thái. Live hiện có chỉ phục vụ các feature đã đăng ký, không có market subscription. Chuyển toàn bộ cùng payload qua socket sẽ không bỏ chi phí settlement/serialization. Sửa đúng là tách dữ liệu và phạm vi cập nhật.

Đo 12:04:12–12:09:12, trước bản vá market: command 3.334/5 phút, p50 210 ms, p95 503 ms, p99 637 ms, 1 request >1s; state 1.227/5 phút (245,4/phút), p50 205 ms, p95 660 ms, p99 913 ms, 3 >1s; orders 554, p50 5 ms/p95 38 ms. State tăng tần suất so với mẫu đầu 919/5 phút; không được coi toàn bộ chênh lệch do một feature vì chưa có phân bố phiên/client tương đương.

Sửa đang kiểm chứng:
- Snapshot giá riêng không chạm player store; cache chung mỗi tick/khung, tối đa 181 điểm/tài sản. Socket đăng ký khi xem, hủy khi đóng/ẩn, gửi khi sang phiên; fallback HTTP chỉ khi mở/chuyển khung/thử lại. Không timer polling giá định kỳ trên client.
- Không sửa `game/` để giữ nguyên validation BUILD, tránh bắt toàn bộ bản lưu kiểm tra lạnh lại. Không đổi salt, epoch, spread, phí hoặc mua/bán.
- Staff fallback 30 giây thay 5 giây; bỏ khi vừa đồng bộ, khi xem Đầu tư hoặc Quầy đang có poller riêng. Tối đa giảm 12 xuống 2 lần/phút cho vòng này, không phải tuyên bố API toàn server giảm 83%.
- Chart 1H/1D/3D/1W/1M theo thời gian ngoài đời; có trục giá/thời gian, kéo xem từng mốc; thị trường chưa đủ tuổi chỉ hiển thị lịch sử thực từ epoch. 1 giờ ngoài đời vẫn là 1 ngày thị trường, không sửa kinh tế.

Còn nợ kiến trúc: settlement nhân viên hiện tính theo thời gian trôi qua khi đọc/ghi, chưa có worker phát sinh sự kiện doanh thu riêng. Vòng Quầy 5 giây còn tồn tại; cần tách summary/settlement có revision trước khi chuyển sang push để không tính tiền trùng. Social badge 60 giây và orders nhỏ vẫn là polling; chưa phải ưu tiên chi phí cao nhất. Tách lịch sử lạnh khỏi save vài MB và đo client long task vẫn cần tiếp tục.

## Bản vá market đã triển khai 12:15:57

Release `/opt/mot-ngay-lam-nghe/releases/1.7.15-market-20261005121521`, health `1.7.15+8e5c2d329d05`. Toàn bộ game/*.py giữ nguyên byte, engine BUILD vẫn `85a9e7554ddcb4ad34d9`; salt/epoch và Có gì mới giữ nguyên. Game restart 7,39 giây, live restart 9,72 giây, thực hiện lần lượt để không cùng dừng cả hai. Không thêm thông báo. Gói SHA256 `8d177f88892eb61f074e3835668c846cf8bf5719308e3a016cbcaf2663adde1b`.

Kiểm chứng: 31 bài Python đạt (HTTP giá không gọi store.read/command, socket thật, cache/range/lịch sử/giá khớp giao dịch và regression realtime market); Node kiểm tra bỏ full-state polling, đổi khung/unsubscribe, giữ revision/balances, retry và click trùng đạt. Gói độc lập có 1.294 hash đúng, PostgreSQL schema thử riêng, HTTP profile/start-day/replay/export đạt. Playwright ở 390×844: không tràn ngang, 1H/1M hoạt động, kéo về đầu biểu đồ đổi đúng giá/thời gian, console không lỗi. Mở Đầu tư và đổi ba khung chỉ 3 API giá, 0 API state; đây là kiểm thử local, không phải benchmark máy người dùng.

Mẫu production 66 giây sau cutover (bắt đầu sau thời điểm hoàn tất 5 giây): command 753, 684,5/phút, p50 161/p95 459/p99 635 ms; state 132, 120/phút, p50 213/p95 560/p99 868 ms; API market 7 lượt, p50/p95 3 ms, payload P95 0,7 KB. State có 2 mã 499, command có 5 mã 409; không có slow-cmd/slow-write trong cửa sổ này. Số lượt market ít và bao gồm probe của người vận hành. Không quy toàn bộ chênh lệch trước/sau cho bản vá vì cửa sổ sau ngắn, phiên client và cơ cấu thao tác chưa tương đương.

HTTPS từ máy local tới production: 6 lần API giá là 211,8 (lượt đầu), 92,9; 91,0; 84,3; 83,0; 89,3 ms. Khác biệt so với 3 ms ở Nginx phản ánh cả chi phí kết nối/đường truyền/client, không phải 3 ms end-to-end. Xác nhận asset mới có market_watch/range/axes, live health bật market và hồi phục 84 kết nối sau 38 giây, cut=0.

Bằng chứng bổ sung: `output/release-1715-market/verify.json`, `production-https.json`, các báo cáo production tải về và `output/playwright/market-mobile-chart.png`.

Bằng chứng gốc ở output/lag-1715 và output/release-1715-hotfix1. Báo cáo này sẽ bổ sung kết quả A/B và deploy sau khi hoàn tất.

## Đo A/B trên cùng bản lưu production, trước triển khai

Mẫu 5.566.058 bytes, cùng thời gian đóng băng và input; chỉ gọi reducer trong bộ nhớ, không ghi database. Thứ tự A/B/A/B, tiến trình nice 15. Trước: 1.596,95 và 1.160,73 ms; sau: 728,90 và 670,30 ms. Trung bình giảm 49,3%; lần đầu có chi phí warmup nên cần đọc cả các mẫu thô. Toàn bộ tuple kết quả gồm state, result, serialized, archive, bảng xếp hạng và các mốc tiến trình bằng nhau. Đây là cải thiện bước compute của lượt full audit, không phải cam kết giảm 49,3% độ trễ toàn game.

## Phát hành bản vá 11:46 ngày 05/10/2026

Đã deploy bản vá hẹp vào `/opt/mot-ngay-lam-nghe/releases/1.7.15-hotfix1-20261005114343`, health build `1.7.15+68955340a9cd`, lúc 11:46:30 UTC+7. Dừng/chạy lại game và live mất 12,47 giây; live đã có 45 kết nối ở health đầu. Giữ nguyên Có gì mới (không thêm mục), schema và cấu hình thị trường. Gói SHA256 `f2d2334ef130b63fdd0c97219a50e29ceb0dd95e8f9cfe7b2cebba79268f75ae`; xác nhận chỉ 3 file runtime và 4 file test thay đổi so với release trước.

Năm HTTPS health sau deploy đạt; asset careers.js mới đúng hash; nội dung thông báo giữ nguyên byte. Bản vá gồm tối ưu full audit, lỗi chuẩn bị nghề và cho gửi chat trùng. Các phần lưu lịch sử nguội, trạng thái quầy nhỏ và đo INP vẫn là công việc tiếp theo, chưa được triển khai trong bản này.

Theo dõi 86 giây đầu sau khi các dịch vụ healthy: 1.059 command, trung vị 166 ms/P95 817 ms; 362 state, 171/963 ms; 183 hộp đơn, 6/52 ms. Không 5xx hoặc Traceback/ERROR/Exception trong đoạn kiểm tra; live 100 kết nối, cut=0, các dịch vụ active. Đây là cửa sổ ngay sau restart với khoảng 739 command/phút, không cùng tải hoặc cùng độ dài với mẫu trước; **chưa chứng minh cải thiện P95 toàn server**. Cold validation sau đổi build vẫn còn, dù periodic audit đã giảm chi phí. Cần tách version của kiểm tra dữ liệu khỏi những đổi code không đổi quy tắc một cách có kiểm chứng ở đợt sau, thay vì bỏ kiểm tra đầu phiên.

Đến 11:49:07 (152 giây sau health), phút gần nhất có 689 command: trung vị 162 ms, P95 484 ms; 212 state: trung vị 146 ms, P95 745 ms. Đây là dấu hiệu ổn định trở lại, chưa là kết luận từ mẫu dài. Thống kê đủ phút đầu ghi nhận command P95 6.387 ms và state P95 2.515 ms: cửa sổ chuyển phiên bản có đợt chờ đáng kể, không được giấu bằng trung vị hoặc health. Vì vậy tránh deploy liên tiếp trong cao điểm; các bản sau cần giảm thời gian chuyển và chi phí kiểm tra lạnh.


## Bản sửa bổ sung Quầy và đường ghi bản lưu (05/10, sau 12:30)

Nguyên nhân được xác nhận thêm: `_command` đã đọc/parse snapshot để tính lệnh, nhưng `_store` lại SELECT cả `state` dưới FOR UPDATE và parse lần hai chỉ để cấp dữ liệu trước/sau cho các hook thuê nhà, ở chung, đơn khách và đổi tên. Trên bản lưu nhiều MB, lần đọc/parse thứ hai kéo dài khóa của cùng người chơi. Sửa bằng projection nhỏ được chụp trước reducer, mỗi lần CAS một bản riêng. Ghi vẫn kiểm tra revision dưới khóa; receipt, archive, đơn hàng và chuyển tiền vẫn cùng transaction. Đường fallback cũng chỉ parse một lần. Không bỏ validation, không đổi số dư hoặc chính sách lưu lịch sử.

Quầy vẫn cần tính doanh thu nguyên tử theo thời gian. Endpoint mới `/api/business/quay` trả revision + story/life_day/wallet/quay; không thay full API state. Giao diện chỉ cập nhật Quầy khi dữ liệu đổi, giữ ô nhập, caret, scroll, disclosures. Lệnh và xác nhận chi tiền đồng bộ full state nếu projection mới hơn. Quầy không hoạt động được cache tối đa30 giây nếu không có nghiệp vụ đến hạn trong khoảng đó; mỗi hit kiểm tra đăng nhập và revision. Quầy đang hoạt động vẫn dùng settlement cũ, không trì hoãn tính tiền hoặc cache số dư sai.

Đo fixture local: full state65.710 bytes → Quầy3.223 bytes (giảm95,1%); idle read+projection median6,917ms → auth+revision+cache0,448ms,10 lượt. Đây là fixture, không phải tốc độ production. Kiểm thử Chromium320/390/430px đạt: không tràn ngang; poll không phát full state event; sửa menu/đang xem doanh thu không bị mất focus, nhảy scroll hoặc đóng; lỗi mạng giữ số đã xác nhận và lần sau phục hồi; không gửi lại lệnh mua/thu tiền.

Đo chỉ đọc trên production trước cutover: save5.658.318 bytes, projection144 bytes. Sáu lần đọc/parse bổ sung cũ:178,964;204,065;170,033;166,024;182,368;171,642ms (median175,303). Sáu lần đọc revision + dựng projection mới:2,690;2,716;2,872;2,757;2,733;3,642ms (median2,745). Không lấy FOR UPDATE trong benchmark, không ghi DB. Toàn bộ tuple compute trước/sau bằng nhau khi đóng băng thời gian. Không coi đây là mức giảm end-to-end.

Đã bổ sung đo client trên10% lượt mở trang: JSON parse (tách khỏi chờ body), áp dụng delta/state, thời gian listener render đồng bộ, long task và sự kiện tương tác chậm. Mỗi nhóm có giới hạn200 mẫu; gửi count/total/max bằng beacon load/leave vốn có, không có polling mới. Chỉ nhận số và tên metric cố định, không lấy nội dung gõ hoặc định danh DOM. Render không bao gồm paint bất đồng bộ; slow-interaction không phải INP; histogram là số bản tổng hợp được lấy mẫu. Cần đủ dữ liệu thiết bị thật mới kết luận được lag ở điện thoại.

Beacon403: Nginx API giữ Host=$http_host. Probe qua HTTPS với Origin đúng và Sec-Fetch-Site same-origin đi qua kiểm tra nguồn (401 vì không có cookie). Chưa có bằng chứng vì sao các request403 trước đó bị từ chối; giữ nguyên các kiểm tra nguồn, không kết luận403 là nguyên nhân lag.

Rà soát lịch sử lạnh: chưa cắt thêm feed/journal/ledger/wallet. Feed100/nghề vẫn chứa bài có thể reply và phản hồi NPC đang đợi; archive hiện read-only, không đủ thay thế. Wallet dùng tính thu nhập14 ngày và fair40 bản ghi; ledger dùng P&L7 ngày; journal có anchor mở ca cũ. Cắt số lượng ngay sẽ làm sai nghiệp vụ. Tách các dữ liệu này sang bảng riêng cần migration và thay cả các reader liên quan, không gộp thao tác mất dữ liệu vào bản vá cao điểm.

Kiểm chứng: nhóm88 Python/PostgreSQL có87 đạt và1 lỗi kỳ vọng schema22 trong test_player_names; chạy đúng bài đó trên nguồn đã deploy cũng thất bại23!=22, nên không sửa kỳ vọng để giấu. Nhóm13 projection/CAS/idempotency đạt; nhóm11 client/performance/projection đạt;6 beacon tests đạt; Node API retry/refresh/clock, sync và2 browser suites đạt. Gói độc lập kiểm tra1.304 hashes, HTTP tạo nhân vật/chọn nghề/mở ca, replay và export trên PostgreSQL riêng đều đạt. Không đổi schema hoặc Có gì mới; backup trước1.7.15 đã kiểm tra pg_restore --list.


### Triển khai 12:40:26 UTC+7

Release `/opt/mot-ngay-lam-nghe/releases/1.7.15-quay-20261005123847`; health `1.7.15+e34bc470f786`; engine BUILD `34ef1ebde874e22baf55`. Gói SHA256 `29d3e0d5c4ab01d16daa335efc2fdeb89507e8dfb8ad404fcf6c043c4a19ed4e`. Game restart7,41 giây, live9,74 giây, tổng17,32 giây (lần lượt). Giữ nguyên schema23, cấu hình salt/epoch, luật thị trường và nội dung Có gì mới. Đã kiểm tra HTTPS hash của api/telemetry/quay/quay-sync/whatsnew-data; endpoint Quầy không có đăng nhập trả401; API chart1W hoạt động.

Cửa sổ64 giây ngay sau cutover:802 command, p50 132/p95 357/p99 528ms,3 lượt >1 giây;35 state, p50 198/p95 412/p99 1039ms; có7 mã499 và2 command409, không phải mọi request đều nhanh. Có1 slow-cmd1.883ms ở ca_step, bản lưu5.077KB, compute1.669ms/store133ms, phù hợp chi phí kiểm tra lạnh còn tồn tại. Live hồi phục102 kết nối sau75 giây, cut=0; con số cut không đo mọi nguyên nhân rớt mạng. Chưa đủ dữ liệu client mới để kết luận số FPS hay độ trễ cảm nhận toàn bộ điện thoại.

Năm phút ngay trước deploy:3.922 command (784,4/phút), p50 161/p95 438/p99 651ms;174 state (34,8/phút), p50 340/p95 742/p99 1030ms. Số này là baseline gần cutover của bản market, không phải baseline trước mọi thay đổi tối ưu.


### Cửa sổ sau deploy đủ 5 phút

Thời gian: 2026-10-05T12:40:54.524578+07:00 → 2026-10-05T12:45:54.524578+07:00.

| API | Trước: lượt/phút · P50/P95/P99 ms | Sau: lượt/phút · P50/P95/P99 ms |
|---|---|---|
| /api/command | 784.4 · 161.0/438.0/651.0 | 893.6 · 136.0/363.0/528.0 |
| /api/state | 34.8 · 340.0/742.0/1030.0 | 27.2 · 204.0/449.0/693.0 |

Sau có 4.468 command: 5 lượt trên 1 giây, 2 trên 2 giây, 53 lỗi 400 và 5 lỗi 409; 136 state có 10 mã 499, không có lượt ghi trong nhóm state trên 1 giây. Kiểm riêng toàn bộ 8.038 dòng API trong cùng cửa sổ, kể cả dòng không có upstream timing, không có mã 5xx. Không có slow log trong cửa sổ này. Cửa sổ lấy 300 giây gần nhất, loại phần rất đầu cutover; phần 64 giây đầu và slow-cmd đã ghi riêng phía trên. Tải và cơ cấu người chơi không được kiểm soát như thử nghiệm A/B, nên đây là quan sát production, không chứng minh bản vá sẽ giảm đúng tỷ lệ đó ở mọi thiết bị.

Endpoint Quầy mới 4 lượt (1 probe 401 và 3 lượt thực), payload P95 khoảng 3,1 KB, thời gian P95 459 ms; chưa đủ mẫu để kết luận độ trễ Quầy production. Chưa reload thì client vẫn dùng mã đã tải trước đó. Live sau 334 giây: 109 kết nối/108 người, cut 0. CPU hai mẫu mới 77% và 56% idle, không swap; chưa có bằng chứng toàn máy thiếu CPU. Không có Traceback/ERROR/Exception/worker0 stopped từ mốc cutover. Điểm còn tồn tại: bản lưu vẫn nhiều MB, full audit định kỳ/cold validation, settlement đang hoạt động vẫn phải tính và ghi đầy đủ; chưa có dữ liệu client đủ rộng để kết luận hết lag.

Bằng chứng phát hành và thống kê: `output/release-1715-quay/verify.json`, `production-https.json`, `mnl1715-quay.json`, `lag1715-quay-benchmark.json`, `lag1715-pre-quay.json`, `lag1715-quay-early.json`, `lag1715-quay-stats.json`, `all-status-check.json`. Không phát Có gì mới cho bản này.
