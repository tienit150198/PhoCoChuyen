# Kiểm tra lag toàn game và hội chợ — 05/10/2026

Phản ánh: toàn game có cảm giác chậm, hội chợ giật. Đo production chỉ đọc; không thay đổi tiền, lượt chơi hoặc dữ liệu người dùng. Bản đang chạy khi đo: 1.7.14, release 20261005090549.

## Số liệu server

Mẫu 15 phút quanh 10:00 UTC+7, 9 CPU, load khoảng 2,08, RAM khả dụng 8,3 GB. PostgreSQL không có phiên chờ khóa trong mẫu kiểm tra. Live có 78 người/kết nối, cut=0 tại thời điểm kiểm tra. Đây là ảnh chụp trạng thái, không kết luận mạng luôn tốt.

| API | Số mẫu | Trung vị | p95 | p95 upstream |
|---|---:|---:|---:|---:|
| command | 8.441 | 174 ms | 480 ms | 460 ms |
| state | 3.223 | 143 ms | 504 ms | 502 ms |
| work-visits/orders | 1.189 | 5 ms | 23 ms | 24 ms |
| social/me | 1.030 | 63 ms | 152 ms | 150 ms |
| work-visits/places | 356 | 58 ms | 172 ms | 173 ms |
| bootstrap | 92 | 260 ms | 2.100 ms | 1.020 ms |

Các lệnh chậm trên 1,5 giây trong mẫu chủ yếu ở bản lưu khoảng 4,2 MB: compute 1,2–1,74 giây, store 0,22–0,49 giây. Không thấy lỗi chương trình trong mẫu journal này.

Đo độc lập, chỉ tính trong bộ nhớ trên server với một bản lưu lớn 4,78 MB: stamp đúng, không cần migration, dùng orjson thật. Sau warmup, business_sync khoảng 303 ms và fair_bc khoảng 338 ms; phần lớn thuộc serialize/kiểm tra các nghề bị thay đổi. Không commit kết quả mô phỏng. Không tải bản lưu về máy hoặc đưa nội dung riêng tư vào báo cáo.

## Điểm nghẽn đã tái hiện

- Hội chợ 390×844, DPR2, CPU chậm 4 lần: 30 người đi lại chỉ khoảng 19 fps; 68 long task trong cửa sổ 6 giây. Đo/vẽ tên và biểu tượng lặp từng khung hình là một chi phí chính.
- Khung phóng dao trước khi bắt đầu vẫn vẽ như lúc đang chơi. A/B trong trình duyệt: giảm nhịp phần xem trước làm thời gian bận main thread giảm khoảng 67%. Không áp dụng giảm nhịp này cho ngắm/phóng dao đang chơi.
- Chế độ giảm chuyển động không vẽ khung mới nhưng vẫn đánh thức requestAnimationFrame ở nhịp màn hình. Cảnh chính phía sau hộp hội chợ đã được dừng phần lớn; không coi đây là nguyên nhân chính.
- Nhân viên xử lý nhiều đơn tích lũy: mỗi đơn ghi nhiều dòng thu chi, mỗi dòng lại quét sổ gần 1.200 dòng cùng ngày. Cần giữ chính xác các mốc lưu trữ và tiền, tránh quét lặp khi đã chứng minh toàn bộ sổ còn trong khoảng ngày gần đây.

## Các giả thuyết không chọn làm bản sửa chính

- Mỗi lệnh hội chợ vẫn đồng bộ snapshot ghé tiệm. Đo PostgreSQL riêng: 41 nghề tạo 49 câu SQL nhưng hook khoảng 6–7 ms. Đây là công việc dư, chưa đủ giải thích giật hình/đợi nhiều giây. Giữ các ràng buộc hợp đồng và đơn khách.
- Cache kiểm tra chuỗi văn bản chỉ giảm compute trung vị 302→287 ms trên bản lưu lớn; chưa đủ lợi ích để thêm cache toàn cục ở lần sửa này.

## Phạm vi sửa và kiểm chứng

Frontend: vòng vẽ hội chợ/phóng dao, cache hình tên/biểu tượng và nhân vật; giữ thời điểm ngắm/phóng, kết quả do server quyết định, cập nhật tên và chức năng multiplayer.

Backend: tối ưu quét sổ trong một lượt xử lý đơn NPC, không bỏ validation, không đổi số tiền/hàng/nhịp đơn, không đổi thứ tự hoặc nội dung lưu trữ.

So sánh với nguồn phát hành sạch tại output/release-1714/mot-ngay-lam-nghe. Không tạo Có gì mới, không thay đổi tỷ lệ thắng hoặc phần thưởng. Người dùng nhắc lại chưa deploy trong lúc kiểm tra; toàn bộ thay đổi dưới đây chỉ ở máy phát triển.

### Kết quả sau sửa

Trình duyệt Chromium, viewport 390×844, DPR2, CPU throttle 4×; mỗi mẫu 6 giây, dữ liệu nhân vật giả lập. Các con số dùng so sánh trong môi trường thử, không phải cam kết tốc độ trên mọi điện thoại.

| Trường hợp | Trước | Sau |
|---|---:|---:|
| 30 người di chuyển: số khung hình/6 giây | 118 | 179 |
| 30 người di chuyển: long task | 68 | 1 |
| 30 người đứng yên: thời gian main thread bận | 4,48 giây | 2,46 giây |
| Phóng dao xem trước: thời gian main thread bận | 6,17 giây | 1,45 giây |
| Phóng dao đang ngắm: số khung hình/6 giây | — | 301 |

Mẫu sự kiện state mỗi 2 giây trong hội chợ không làm dừng hội chợ; cảnh chính vẽ lại 3 lần tương ứng 3 sự kiện. Sau đóng, không còn callback/vẽ hội chợ. Cảnh chính sau đóng vẫn có chi phí vẽ, phụ thuộc trạng thái vừa thao tác hay đã để yên lâu; không so hai mẫu này như cùng điều kiện.

Backend: bài đo 1.024 đơn NPC tích lũy giảm trung vị 257,02→63,30 ms (7 lần, JSON Python tiêu chuẩn). So sánh state, chuỗi lưu và 4.096 dòng archive đều bằng nhau. Suite PostgreSQL 125 test qua; root chạy độc lập nhóm 119 test qua. Thêm 100 chuỗi ngẫu nhiên để kiểm tra thứ tự ngày lộn xộn, vượt ngưỡng và chuyển ngày.

Frontend: 6/6 test Node qua sau sửa cuối; bổ sung tình huống callback gọi lại wake ngay trong một khung hình, chỉ được giữ một lịch vẽ. Đã xem screenshot hội chợ và bảng phóng dao; browser report không có lỗi JavaScript. Review độc lập frontend/backend không có lỗi chặn. Hash hai nguồn Có gì mới khớp bản đang phát hành.

Giới hạn còn lại: bản lưu lớn vẫn tốn thời gian kiểm tra/serialize, và một số cảnh nghề còn vẽ nền động nhiều. Bản sửa giảm các chi phí đã tái hiện, chưa chứng minh loại bỏ toàn bộ cảm giác lag trên production.

### Bằng chứng

- `output/playwright/fair-perf-fixed/report.json`: mẫu trình duyệt sau sửa, screenshot và CPU profile cùng thư mục.
- `output/playwright/fair-perf-crowd/report.json`, `output/playwright/fair-perf-ab/report.json`: mẫu trước sửa.
- `tests/fair_render_budget.mjs`, `tests/fair_chance.mjs`: lịch vẽ, cache, thời gian ném và kết quả do server quyết định.
- `tests/test_ledger_batch.py`, `output/benchmark_command_compute.py`: kiểm tra tính tương đương tiền/sổ và benchmark NPC.
- `output/lag-commit-hooks-audit.json`, `output/lag-commit-hooks-profile.txt`: chi phí hook PostgreSQL.
