# Bản trải nghiệm local — 04/10/2026

Chạy tại http://127.0.0.1:8765, chỉ lắng nghe localhost. Chưa commit hoặc deploy. Bản lưu SQLite riêng tại `output/local-experience-20261004/game.sqlite3`; không sử dụng PostgreSQL, AI bên ngoài hoặc web push.

## Đã thay đổi

- Mục tiêu nằm đầu Hành trình và trên bản đồ; có nút đi tới phần liên quan. Người mới được gợi ý nhận việc trước khi khép ngày. Xem tất cả mục tiêu mở ngay trong thẻ bản đồ.
- Menu “Đổi nơi làm” rõ nghĩa hơn.
- So phiếu không mất lượt, thời gian hoặc tính lỗi; giao sai và đổ ly vẫn có hậu quả.
- Thăng tiến hiển thị toàn bộ điều kiện, gồm tỷ lệ ngày tốt, thời gian hẹn xét lại và các yêu cầu của nghề.
- Truyện nghề hiển thị tóm tắt, lựa chọn cũ, tiến độ và điều kiện cho đoạn tiếp theo.
- Hai truyện mẫu Linh/trà mùa thi và radio/Ông Bảy nhắc lại lựa chọn trước; lời ghi trên kỷ vật thay đổi theo lựa chọn.
- Phân biệt giờ trong game; đồng bộ hướng dẫn và bản dịch mới.

Đây là đợt cải thiện UX và hai truyện mẫu trong báo cáo audit, chưa viết lại toàn bộ 205 cảnh hoặc thay điều kiện các chương chính.

## Chơi thử

Mở địa chỉ local để chơi. Muốn xem truyện ngay: Cài đặt → Dữ liệu → Nhập bản lưu, chọn `output/local-experience-20261004/story-preview.json`. Đây là nhân vật mẫu “Mây xem thử”, hai truyện đang ở đoạn 3. File `story-preview-alternate.json` dùng lựa chọn ngược lại. Hai file `story-ending*.json` mở sẵn đoạn cuối để xem kỷ vật. Nhập bản lưu thay thế nhân vật của phiên local hiện tại.

Khởi động lại từ thư mục worktree: `python output/run-local-preview.py`.

## Kiểm chứng

- Review độc lập: 277 test Python hồi quy qua; 11 test Node qua. Đã sửa và kiểm tra lại trường hợp nút truyện dẫn tới nơi làm tạm đóng.
- Kiểm tra tích hợp riêng: 91 test Python qua; hướng dẫn/bản dịch 21 test qua; UI feedback cũ 1 test qua.
- 481/481 tệp JavaScript kiểm tra cú pháp thành công. `git diff --check` sạch.
- Chơi thử trình duyệt ở 390×844 và 1440×1000; nhập bản lưu mẫu, đọc hai đoạn callback, xem recap/điều kiện tiếp theo. Luồng mở rộng mục tiêu cho người chưa hoàn tất giới thiệu đã được kiểm tra lại trực tiếp.
- Một test cũ về dung lượng `journey` vẫn vượt ngưỡng 8.650 (thực tế 10.865). Đã tái hiện y hệt trên HEAD trước thay đổi bằng checkout tạm từ `git archive`; không tăng ngưỡng để che lỗi.
- Hai harness Node nhận JSON qua stdin từng được gọi trực tiếp thiếu fixture; chạy lại qua test Python cung cấp fixture đã qua.
- Theo yêu cầu, đã tắt các công tắc âm thanh và nhạc nền trên tab local của người dùng; đóng hai trình duyệt kiểm thử, giữ tab local trong Codex và máy chủ chạy.
