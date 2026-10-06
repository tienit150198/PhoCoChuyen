# Phóng dao theo thao tác thật, vòng liền nét — 05/10/2026

Trạng thái: đã sửa và kiểm tra local, chưa deploy. Yêu cầu mới thay thế quyết định xác suất của riêng phóng dao. Các trò may rủi khác giữ cân bằng đang chạy.

## Nguyên nhân và cách sửa

- Phóng dao: nhánh `fair_kn_throw` trước đây bỏ qua va chạm, rồi bốc xác suất ở dao cuối. Một kết quả thua được trả về như thể dao cuối đụng dao khác, dù hình ảnh không va chạm. Lượt mới nay dùng `knife.judge`: client và server tính cùng lịch xoay, cùng thời điểm dao chạm bia, cùng khoảng va chạm. Đủ dao không va chạm thì qua màn; va chạm thật thì thua. Server vẫn xác nhận thưởng và chống trả thưởng hai lần.
- Lượt mới không gọi `luck_p`, không lưu xác suất hay chuỗi giảm xác suất cho phóng dao. Giữ lịch xoay nhẹ hơn đã triển khai (135%, màn đầu 10 dao), điều khiển pointerdown, thời gian bay 80 ms, giới hạn 60 giây/màn, bậc thưởng và màn thưởng x2 hiện có. Các mức khó theo màn và mức thắng trong ngày vẫn thể hiện qua tốc độ bia/dao có sẵn, không bốc thắng thua.
- `fair_kn_skill` lưu seed/thời điểm/hệ số của màn để tải lại hoặc chơi tiếp không đổi lịch xoay giữa client và server. Ván kỹ năng rất cũ chưa có metadata giữ lịch 100% của màn đang chơi; màn tiếp theo chuyển 135%.
- Màn xác suất đã bắt đầu trước cập nhật được hoàn thành mà không bốc thua ngẫu nhiên. Không áp va chạm ngược lên các cú phóng cũ từng cho phép đè lên nhau. Từ màn tiếp theo chuyển kỹ năng, có dao cắm sẵn hiện rõ. Hướng dẫn trong UI giải thích chuyển tiếp này.
- Ném vòng: `.fh-fly.pending` bị vẽ xám nét đứt trong khi đợi đủ năm lần ném, trông như vòng vỡ thành mảnh. Bỏ hai thuộc tính màu xám/nét đứt, giữ vòng đỏ liền nét. Vòng trúng tiếp tục bao quanh cổ chai với cung sau bị cổ chai che và cung trước hiện phía trước. Không thay xác suất hoặc tiền thưởng.
- Không thêm request mỗi cú phóng, polling hay công việc theo frame. Phóng dao vẫn gửi một bộ thời điểm khi kết thúc màn/va chạm; ném vòng vẫn gửi một lần sau năm cú ném.

Runtime thay đổi: `game/fair.py`, `game/fair_knife.py`, `public/js/v4/fair-knife.js`, `public/css/fair.css`. Các thay đổi khác sẵn có trong checkout không thuộc bản sửa này.

## Bằng chứng kiểm tra

- RED trước sửa: test kỹ năng thất bại do thua xác suất/thiếu cấu hình kỹ năng; test CSS và cả bốn cấu hình trình duyệt ném vòng thất bại vì nét đứt.
- GREEN: `unittest discover -s tests -p test_fair*.py`: **160 test đạt**, 41,347 giây; `tests.test_economy_pass2`: **9 test đạt**. Bao gồm lưu/tải giữa màn, màn cũ, qua đủ 10 màn, va chạm, hết giờ, trả thưởng/idempotency, các trò may rủi và giới hạn tiền đặt.
- Trong bộ trên, kiểm tra đối chiếu Python/JavaScript **328 tình huống**: bốn seed × mười màn × bốn mức nóng × cú an toàn/va chạm, cộng tám trường hợp sát mép và góc quay qua 0/360. Chỉ số dao va chạm và số dao cắm khớp; sai số góc cắm trong độ làm tròn 0,005 độ của server.
- **77 test JavaScript đạt**: input, va chạm, thời gian bay, kết quả trễ, retry, hình học dao/vòng, vòng đời canvas, ngân sách render và vé cào.
- Ném vòng trên Chromium/WebKit ở 390 và 1280 px: **40 kiểm tra đạt**, không page error. Kiểm tra nét liền khi chờ, chỗ rơi khớp vòng đã cắm, cổ chai xuyên tâm vòng, xếp năm vòng trên một chai, không nhận nhầm tiền khi trượt. Đã xem ảnh pending/hit WebKit 390 px.
- Phóng dao bằng ứng dụng thật và PostgreSQL local: Chromium ở 390×844, 320×640, 430×932 hoàn thành, exit 0; chơi qua màn, nhận thưởng, chủ động ném trúng dao để thua, màn x2, sáng/tối và không tràn ngang. WebKit ở cùng ba kích thước cũng qua tất cả kiểm tra gameplay; script tổng thể exit 1 vì console ngoài gameplay: viewport `interactive-widget` chưa được hỗ trợ, beacon trả 403 ở localhost, một ảnh bị hủy/access-control khi reload. Probe riêng xác định hai 403 là `/api/beacon`; không có lỗi request phóng dao. Không tuyên bố toàn bộ console WebKit sạch.
- Log: `output/fair-skill-suite-final.txt`, `output/fair-skill-economy.txt`, `output/fair-skill-js-final.txt`, `output/fair-ring-browser-solid-green.txt`, `output/fair-knife-skill-browser.txt`, `output/fair-knife-skill-webkit.txt`, `output/fair-webkit-console.txt`.
- Ảnh: `output/playwright/ring-geometry/after/`, `output/playwright/knife-skill/`, `output/playwright/knife-skill-webkit/`.

## Lưu ý khi triển khai sau

Production hiện vẫn là `1.7.15-fair-gentle-final-20261005181749`. Bản này chưa đọc `fair_kn_skill`; nếu đọc lượt mới sẽ nhầm về lịch 100% (7 dao thay vì 10). Khi được yêu cầu deploy, phải đưa khả năng đọc/validate metadata và tính va chạm kỹ năng lên tất cả game/live/background writer trước, sau đó mới bật sinh lượt kỹ năng mới. Bản cầu vẫn tạo lượt xác suất cũ, nhưng phải đọc và xử lý đúng cả hai loại; không được bật lượt mới trong lúc còn worker cũ. Rollback về bản cầu này, không về bản gentle cũ sau khi đã ghi lượt kỹ năng mới. Đóng gói từ release production hiện hành với bốn file runtime nêu trên, tránh gom các sửa đổi không liên quan trong checkout.
