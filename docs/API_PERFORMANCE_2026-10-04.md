# Rà soát API sau bản 1.7.8

Trạng thái: sửa và kiểm tra local, **chưa deploy** các thay đổi trong báo cáo này.

## Số đo production

Mẫu log Nginx 5 phút tối 04/10/2026; tổng hợp theo đường dẫn, không xuất nội dung người chơi. Đơn vị giây. p95 là mốc 95% request hoàn tất trước đó.

| API | Số request | p50 | p95 | Chậm nhất |
| --- | ---: | ---: | ---: | ---: |
| POST /api/command | 4079 | 0.371 | 1.504 | 5.207 |
| GET /api/work-visits/orders | 2611 | 0.384 | 1.190 | 3.834 |
| GET /api/work-visits/places | 551 | 0.454 | 1.248 | 2.321 |
| GET /api/work-visits/place | 59 | 0.923 | 4.024 | 5.884 |
| GET /api/state | 650 | 0.449 | 2.351 | 3.813 |
| GET /api/bootstrap | 66 | 0.475 | 1.768 | 6.701 |
| GET /api/social/me | 539 | 0.116 | 0.364 | — |
| GET /api/home-guests | 351 | 0.171 | 0.464 | — |
| GET /api/news | 563 | 0.009 | 0.175 | — |
| GET /api/content | 154 | 0.013 | 0.164 | — |

Các API AI có p50 khoảng 4.4–6.5 giây, p95 khoảng 5.9–8.1 giây; cần tách thời gian chờ nhà cung cấp khỏi xử lý game. File AI và pool PostgreSQL không đổi so với bản 1.7.7.

Máy có 9 CPU, load average 9.78 tại lúc đo; 8 worker Python dùng khoảng 71–73% CPU mỗi worker. PostgreSQL khoảng 6.8%, RAM còn khả dụng khoảng 8.6 GB. Không thấy bằng chứng cạn pool hoặc hàng đợi khóa kéo dài trong mẫu kiểm tra. Thời gian upstream gần thời gian Nginx, cho thấy phần lớn độ trễ quan sát nằm ở backend.

## Nguyên nhân và thay đổi

1. `player_service_tasks.offers` deepcopy toàn bộ save 41 nghề để khởi tạo một dịch vụ. Profile trên một save production 2.26 MB, 13 nghề đã bắt đầu: deepcopy 272.6 ms, dựng offer 313 ms. Khi chạy cProfile, deepcopy chiếm 99.7% thời gian hàm. Hàm này còn chạy trong hook ghi tiến trình đang giữ khóa save.
   - Chỉ sao chép nghề cần dựng và journey phục vụ xét thăng tiến; dùng bộ sao chép cây JSON đã có. So sánh kết quả với cách cũ và kiểm tra không làm đổi input cho cả 41 nghề.
2. Mọi lượt hỏi đơn, kể cả rỗng, đều tải và dựng lại thông tin tiệm của người hỏi; route còn tải save một lần chỉ để xác thực.
   - Bỏ dựng tiệm cho `orders` và bỏ dựng tiệm của người ghé khi đang xem tiệm khác. Giữ cập nhật tiệm đích và thanh toán đơn thực sự đến hạn. GET/POST work-visits xác thực phiên nhẹ, giữ kiểm tra CSRF/origin cho POST.
3. Các hook ghi tiến trình parse lại cùng một JSON trước thay đổi hai lần, ba lần với đổi tên.
   - Dùng chung bản trước/sau trong cùng transaction; giữ CAS, receipt, cập nhật tên và thanh toán nguyên tử.
4. `/api/state` tính tiền nhân viên bằng command rồi bỏ kết quả, đọc save và dựng public view thêm lần nữa.
   - Dùng public view và revision của command đã commit. Khi chưa đến hạn vẫn trả trạng thái đọc ban đầu.
5. Frontend tự kiểm tra hộp đơn quá thường xuyên khi không có việc.
   - 30 giây khi không có đơn đang xử lý, 5 giây khi đang có đơn, phát hiện tiệm 120 giây hoặc đổi nghề/focus. Dừng vòng owner khi tab ẩn hoặc đang dùng màn ghé tiệm; đồng bộ lại khi quay về.

## Đo local

Benchmark tổng hợp, 20 lần mỗi cách, so sánh trên cùng máy. Đây **không phải** độ trễ HTTP sau deploy.

| Dữ liệu giả lập | Cũ, trung vị | Mới, trung vị |
| --- | ---: | ---: |
| 41 nghề đã bắt đầu, 447 KB | 9.334 ms | 0.131 ms |
| 41 nghề và lịch sử giả lập, gần 3 MB | 107.004 ms | 0.586 ms |

Script và số đo: `output/benchmark_visit_offer.py`, `output/api-offer-benchmark.json`.

## Xác minh backend

- 126 bài PostgreSQL/HTTP đã qua: player service tasks, work visits, xác thực route, business sync/storage, storage, tên người chơi và home guests. Log `output/api-perf-regression.log`.
- Regression đã thất bại trước sửa: hỏi hộp đơn rỗng không được tải save; route work-visits không được parse save chỉ để xác thực; state sau settlement chỉ đọc save một lần.
- So sánh offer với thuật toán trước sửa và giữ input bất biến trên 41 nghề.
- Rà soát độc lập không tìm thấy lỗi ở phạm vi shadow, reuse before-state, auth/CSRF hay public state/revision trả về.
- Một test đua đặt đơn đôi khi thiếu tiền trước khi chạy do sự kiện đời sống ngẫu nhiên trong bước tạo fixture. Đã cấp đúng 25 xu sau setup, rồi kiểm tra 12 lần liên tiếp: cả hai request trả cùng đơn, tiền chỉ trừ một lần. Không sửa quy tắc game để làm test qua.
- PostgreSQL thử nghiệm local đã dừng sau kiểm tra; không sửa dữ liệu production.

## UI

Lỗi cần sửa ngay: bảng Khách ghé nổi che Làm tiếp/Hoàn thành. Đưa vào luồng bố cục, nút thu gọn đọc đầy đủ và có số khách/đơn; không thu nhỏ phiếu công việc để nhường một mép thẻ khó nhận biết. Kiểm tra desktop, điện thoại dọc/ngang và tablet dọc/ngang.

Đã sửa local bằng container bên ngoài taskHUD, giữ app sở hữu các phiếu công việc bên trong. 9 test DOM/timer, hai bộ visit/quay UI và kiểm tra cú pháp đã qua. 6 workflow Chromium ở 1280×800, 390×844, 320×568, 844×390, 820×1180, 1024×768 đã qua, gồm phiếu dài, nhiều phiếu, mở rộng khách, mở/đóng nghề và render lại. Ảnh kiểm tra ở `output/playwright/visit-owner/`; đây là fixture dùng CSS/JS thật, không phải ảnh tài khoản production.

Hướng cải thiện màn ghé tiệm: đưa tên tiệm/chủ tiệm và dịch vụ/giá lên trước; đơn đang xử lý phải dễ thấy trước khi đặt thêm; cảnh phòng, đi lại, biểu cảm và chat là phần phụ có thể mở khi muốn giao lưu. Đây là hướng thiết kế tiếp theo, chưa tuyên bố đã hoàn thành việc thiết kế lại toàn bộ màn ghé tiệm.

## Giới hạn và bước xác minh tiếp

- Chưa có số đo HTTP production sau sửa vì chưa deploy.
- Quầy đang hoạt động có thể phát sinh business_sync ngay khi con trỏ thời gian tăng 1 ms dù chưa có lượt bán mới. Thay nhịp tính tiền cần bảo toàn lương/tiền thuê lẻ; đợt này chưa đổi quy tắc kinh tế đó.
- Offline backlog tối đa 1024 đơn/nghề có thể gây outlier; không được bỏ doanh thu/chi phí để làm nhanh.
- Sau khi được yêu cầu deploy: đo lại cùng nhóm API, p50/p95, CPU và số request nền; kiểm tra chat, đơn khách, tiền nhân viên và Làm tiếp trên thiết bị nhỏ.
