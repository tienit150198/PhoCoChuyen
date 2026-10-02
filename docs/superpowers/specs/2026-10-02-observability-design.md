# Firebase, Google Analytics và Search Console cho Phố Có Chuyện

Yêu cầu: tạo dự án Firebase riêng, liên kết Analytics, Search Console và theo dõi lỗi/hiệu năng. Người dùng xác nhận ngày 02/10/2026: “cứ tạo riêng rồi thống kê cho tôi nhé”.

- Firebase riêng tên Pho Co Chuyen. GA4 property riêng liên kết dự án, web stream cho https://phocochuyen.io.vn, múi giờ Việt Nam.
- JavaScript SDK modular cố định phiên bản, tải sau khung hình game đầu tiên. Bị chặn/mất mạng/không cấu hình không ảnh hưởng chơi game. Không thêm phụ thuộc chạy server.
- Cấu hình web công khai lấy từ biến môi trường qua meta HTML đã escape. Chỉ whitelist trường SDK; không đưa env bí mật, token, bản lưu, tên người chơi hoặc chat vào Google.
- Chỉ gửi tại origin production và khi người chơi cho phép thống kê; tôn trọng DNT/GPC. Analytics không bật Google Signals/personalized advertising. URL trang và referrer không mang query/hash.
- Sự kiện: game_ready, career_start, shift_complete, screen_view, client_error; chỉ tên nghề/màn hình/loại lỗi và bản game, không nội dung tự do. SDK Performance đo page load và kết nối khi được cho phép.
- Log lỗi chi tiết tiếp tục dùng /api/beacon và admin Giữ chân; log Python/nginx/systemd vẫn thuộc server. Không gửi toàn bộ log sang Analytics.
- Search Console xác minh bằng meta do Google cung cấp; robots.txt, sitemap.xml và canonical cho tên miền thật.
- Kiểm thử cấu hình thiếu/đủ, chống chèn HTML, CSP, giới hạn origin/consent, SDK thất bại, không đưa dữ liệu người chơi vào sự kiện, HTTP robots/sitemap. Kiểm tra bộ telemetry hiện có.

Trạng thái external phải xác nhận tại Firebase/Analytics/Search Console; code được kiểm thử không có nghĩa đã triển khai hay có dữ liệu Google. Truy cập server và kết nối Chrome là điều kiện kích hoạt production.
