# Hội chợ dễ chơi hơn — 05/10/2026

Trạng thái: đã deploy theo yêu cầu lúc **18:22:26 ngày 05/10/2026 (UTC+7)**, không tạo thông báo cho người chơi. Chi tiết: [DEPLOY_FAIR_GENTLE_2026-10-05.md](DEPLOY_FAIR_GENTLE_2026-10-05.md).

## Cân bằng

- Bầu cua, xóc đĩa, lô tô/Kinh, vé cào, phóng dao và ném vòng: xác suất cơ bản 70%, sàn 55%.
- Trong điều kiện chưa chạm ngưỡng lãi ngày: 10 lượt liên tiếp đầu giữ 70%; lượt 11 là 69%; lượt 25 trở đi là 55%. Đổi quầy hoặc nghỉ quá 180 giây xóa chuỗi lặp.
- Cơ chế giảm theo lãi hội chợ trong ngày từ 2.000 đến 5.000 xu vẫn áp dụng, nhưng cũng không thấp hơn 55%.
- Phóng dao mới dùng hệ số 135 thay cho 150: tốc độ bia bằng 90% bản đang chạy, màn đầu 10 dao thay cho 11. Các màn sau làm tròn số dao lên theo hệ số; giữ nhịp nhận thao tác và thời gian dao bay đã sửa mượt.
- Ném vòng tăng cơ hội có ít nhất một vòng trúng từ 60% lên 70%; không đổi cách vẽ vòng ôm cổ chai.
- Giữ bảng trả thưởng, mức cược, quy tắc đánh dấu và bấm Kinh, giới hạn thời gian, tỷ lệ truy bắt. Ô ăn quan và ông Hai giữ nguyên như yêu cầu trước.
- Vé cào: một lần thắng có thể hoàn vé; tiền nhận trung bình trước các hiệu ứng khác tăng từ 1,476 lên 1,722 xu trên mỗi xu mua vé ở mức cơ bản, và từ 1,107 lên 1,353 ở sàn. Đây là trung bình xác suất, không bảo đảm lãi cho mỗi người hay mỗi lượt.

## Ván đang chơi và triển khai sau này

- Ván phóng dao/ném vòng đã mua giữ xác suất được lưu khi mua (kể cả 45–60%) và cấu hình cũ; tăng mức mới từ lượt mua tiếp theo.
- Validator nhận cả hệ số 135/150 và xác suất lưu 450–700 phần nghìn. Thiếu metadata vẫn dùng luật ván kỹ năng cũ.
- Backend bản production hiện tại chỉ nhận `p <= 600` và `difficulty = 150`. Khi được yêu cầu deploy, phải đưa validator cùng bộ dựng lịch 135 lên toàn bộ các process có thể đọc/ghi state trước, sau đó mới bật xác suất 700 và hệ số 135 cho ván mới. Không rolling trực tiếp bản sinh state mới song song với validator cũ.
- Bản cầu tương thích chỉ mở rộng validator và hỗ trợ lịch 135, vẫn sinh ván 60%/45%, hệ số 150 như production; triển khai bản cầu cả main, bridge, live/background writers trước khi đổi cân bằng. Rollback sau khi đã sinh state mới phải về bản cầu tương thích.
- Chỉ ba module runtime thay đổi: `game/fair.py`, `game/fair_knife.py`, `game/fair_scratch.py`. Không thêm polling, request, animation hoặc xử lý theo frame.

## Kiểm tra

- Đã chạy test yêu cầu mới trước sửa: thất bại đúng ở xác suất 60%/45%, số dao 11 và validator không nhận 135.
- Bộ hồi quy: **159/159 test đạt**, 62,669 giây, exit code 0. Các module: event odds, gentle balance, scratch, knife, round identity, fair và economy pass 2. Bao gồm tiền thưởng, chống trả thưởng hai lần, lưu/tải ván, bộ dựng lịch cũ và lô tô/Kinh.
- Lượt test source có một cảnh báo flush KPI `stat_counters` không tồn tại trong môi trường PostgreSQL test; không có test failure/error. Gói phát hành đã được kiểm tra riêng và đã xác minh trên production, xem báo cáo deploy.
- Log: `output/fair-balance-red.txt`, `output/fair-balance-tests.txt`.
