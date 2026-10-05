# Phi công: lịch bay và thưởng thay đổi

Theo yêu cầu: cả số chuyến và tiền thưởng đều thay đổi.

- Ngày đầu giữ 3 chuyến hướng dẫn. Từ ngày 2, lịch điều phái có mục tiêu 2–5 chuyến, xác định theo ngày nghề. Tải lại hoặc khởi động lại không đổi lịch.
- Giữ toàn bộ chuyến chưa xong từ ngày trước; chỉ bổ sung tới mục tiêu của ngày mới. Vì vậy số chuyến thực tế có thể vượt mục tiêu nếu còn nhiều chuyến cũ. Nút nhận thêm chặng vẫn hoạt động như trước. Ca quản lý giữ cách xếp việc hiện có.
- Chuyến mới có thưởng cơ bản 8–20 xu theo mã chuyến (ngày và vị trí trong lịch), cộng 2 xu nếu kín khách: tổng 8–22 xu. Thưởng được ghi vào chuyến khi điều phái tạo chuyến, được kiểm tra khi đọc bản lưu.
- Chuyến cũ chưa có trường thưởng vẫn dùng 12 xu; không tạo lại đường bay, thời tiết, lỗi kỹ thuật hay tiến độ chuyến cũ.
- Mỗi điểm lỗi quy trình trừ 3 xu, tối thiểu 0; lỗi an toàn mất toàn bộ thưởng. Mệt mỏi nhận nửa thưởng (làm tròn xuống); đang bị cách chức không nhận thưởng. Lương theo hợp đồng giữ nguyên.
- Thẻ chuyến bay chính ngay trên màn hình sân bay hiện tổng số chặng, số chặng còn lại và thưởng dự kiến, kể cả trước khi đọc giới thiệu nghề. Bảng giờ bay hiện tổng số chặng, đã bay và còn lại. Chuyến chờ bản tin và thẻ chuyến đang làm hiện thưởng dự kiến; thông tin cho phép xuống dòng trên màn hình hẹp.

Kiểm thử bổ sung trong `tests/test_pilot_variation.py` và `tests/pilot_variation.mjs`: lịch nhiều ngày; bản lưu tải lại; thưởng báo trước và thực nhận; tương thích chuyến cũ; dữ liệu thưởng giả; lỗi an toàn; giảm thưởng do lỗi quy trình, mệt mỏi, cách chức; chuyến còn dở và tiến độ trên giao diện. Bộ kiểm thử phi công hiện có cũng kiểm tra lương ngày và các quyết định bay an toàn.

Lệnh kiểm tra:

```powershell
python -m unittest tests.test_career_pilot tests.test_pilot_guidance tests.test_pilot_variation tests.test_air_odd -q
node tests/pilot_variation.mjs
node --check public/js/careers/pilot.js
```

Kết quả: bộ 101 kiểm thử Python liên quan đã qua (41,461 giây), kiểm thử tích hợp dựng bảng giờ bay mới thêm đã qua riêng, kiểm tra cú pháp JavaScript và `git diff --check` cho các tệp phi công đều qua. Chưa kiểm tra trực quan bằng trình duyệt; kiểm thử giao diện hiện xác nhận HTML xuất ra.

Thay đổi chưa commit hoặc triển khai.
