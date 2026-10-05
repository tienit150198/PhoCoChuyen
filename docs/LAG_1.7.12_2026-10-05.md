# Kiểm tra lag sau 1.7.12 — 05/10/2026

Người chơi báo lag toàn bộ. Kiểm tra production chỉ đọc; bản sửa hiện ở local, chưa phát hành và chưa đổi Có gì mới.

## Bằng chứng production

Mẫu khoảng 07:59–08:06 UTC+7: load 2,41 trên 9 CPU, RAM còn khoảng 9,5/16 GB; PostgreSQL không có phiên bị khóa chờ. Game/live đang chạy, không restart; mẫu live có 52 kết nối, 51 người và cut=0. Mẫu này không chứng minh mọi thời điểm đều ổn định.

Log API trong khoảng 10 phút:

| API | Số mẫu | Trung vị | p95 |
|---|---:|---:|---:|
| command | 5.401 | 173 ms | 513 ms |
| state | 1.520 | 166 ms | 603 ms |
| orders | 671 | 5 ms | 25 ms |
| social/me | 488 | 63 ms | 138 ms |
| work-visits/place | 7 | 2.510 ms | 2.613 ms |
| bootstrap | 52 | 312 ms | 19.909 ms |

Một số bootstrap mất gần 20 giây tổng cộng nhưng upstream chỉ 304–383 ms, không gửi được byte hoặc kết thúc 499; content tương tự với upstream 12–24 ms. Đây là chậm/hủy ở phần sau backend, chưa đủ bằng chứng xác định mạng, proxy hay trình duyệt. AI feedback/review mất 4–8 giây cả upstream, là đường xử lý riêng.

Log lệnh chậm với bản lưu 3,5 MB ghi nhận compute khoảng 1,4 giây, store khoảng 0,2 giây. Đo thuần trong bộ nhớ trên bản lưu lớn, đúng PYTHONPATH service và orjson, vẫn thấy chi phí kiểm tra dữ liệu đáng kể. Production **có orjson**; phép đo shell thiếu PYTHONPATH ban đầu không dùng làm kết luận.

## Nguyên nhân đã tái hiện và sửa

1. Ghé chỗ làm đọc lại bản lưu chủ tiệm và đồng bộ lại snapshot dù đã có dữ liệu. Tái sử dụng state/revision đã đọc, giữ kiểm tra revision dưới khóa; sau settlement dùng snapshot đã ghi cùng transaction.
2. Đơn nhân viên tích lũy ghi từng dòng lịch sử bằng từng INSERT riêng. Ghi tối đa 512 dòng mỗi batch, cùng transaction. Flush trước lệnh xóa lịch sử để giữ đúng thứ tự, sequence và rollback.
3. Chat dựng lại toàn bộ danh sách tin nhắn ngay cả khi chỉ đổi online/đã đọc. Giữ các node khi nội dung không đổi; tin mới và thay đổi nội dung vẫn cập nhật.
4. Nhà dùng chung khóa thao tác thanh toán với tải chợ thuê. Tách trạng thái đọc, giữ điều hướng và thao tác không phụ thuộc chợ thuê hoạt động; kết quả GET cũ không được ghi đè giao dịch hoặc mở khóa thanh toán đang chạy.

## Đo local, không phải kết quả sau deploy

- PostgreSQL riêng, bản lưu tổng hợp 2,70 MB; 1.024 đơn nhân viên mỗi lượt ghé. Trung vị trước batching khoảng 844 ms, sau 528 ms (giảm khoảng 37%). Lượt ghé không có đơn đến hạn sau sửa khoảng 27 ms. Chi phí deepcopy và kiểm tra save lớn vẫn còn.
- Chromium, viewport 390×844, 400 tin nhắn tổng hợp: render không đổi nội dung trung vị 99,7→21,0 ms; p95 126,6→27,6 ms. CPU chậm 4 lần: trung vị 687→144,1 ms; p95 831,3→150,6 ms. Trường hợp tin mới vẫn dựng lại danh sách; không áp dụng mức cải thiện này cho mọi render.
- Dữ liệu benchmark: `output/lag-visit-after.log`, `output/playwright/chat-lag-compare.json`. Bộ đo: `output/benchmark_work_visit_latency.py`, `output/playwright/chat-lag-compare.py`.

## Kiểm tra

- 94 kiểm tra PostgreSQL đạt: archive, batching/rollback, work visits/HTTP, business storage, rentals. Log `output/lag-backend-regression.log`.
- Một kiểm tra tiền cũ bỏ sót thưởng lợi nhuận 40% đã có trước bản sửa. Tái hiện cùng lỗi 302 != 299 trên nguồn sạch đã phát hành 1.7.12; cập nhật kiểm tra theo margin, carry và thưởng, đồng thời xác nhận không trả trùng khi đồng thời/retry.
- Rà soát độc lập backend không thấy lỗi chặn; giữ nguyên bảo vệ revision, transaction và thứ tự lịch sử.
- 40 kiểm tra Node đạt: chat redraw/history/reply, tải Nhà và rental UI; cả hai module qua kiểm tra cú pháp. Log `output/lag-frontend-regression.log`.
- Rà soát frontend phát hiện cache HTML có thể giữ checkbox “Hiện online” chưa lưu khi gửi thất bại. Đã giới hạn cache cho khung tin nhắn, giữ redraw theo dữ liệu thật cho các form và bổ sung hồi quy presence/prefs.
- Chromium kiểm tra giữ focus, node tin nhắn, bản nháp, reply, vị trí cuộn và hiển thị tin mới; Nhà vẫn điều hướng được khi GET đang chờ và GET cũ không mở khóa thanh toán đang chạy.

Không có thay đổi dữ liệu người chơi, mức thưởng, thông báo hay version trong lượt sửa lag này. Cần đo lại production sau khi được cho phép triển khai; chưa khẳng định xử lý hết hiện tượng lag toàn bộ.
