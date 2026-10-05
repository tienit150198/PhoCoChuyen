> Tài liệu lịch sử của bản phát hành cũ. Cấu hình và công cụ database mô tả dưới đây không còn áp dụng; cách chạy hiện tại dùng PostgreSQL duy nhất tại [POSTGRES_ONLY.md](POSTGRES_ONLY.md).

# Phạm vi thực tế v0.3.0

Nguồn đối chiếu là code và báo cáo kiểm thử. Tài liệu trong `reference/` mô tả thiết kế dài hạn, không có nghĩa toàn bộ đã được triển khai. Phân biệt số lượng bộ nội dung với số loại cơ chế trò chơi.

| Hệ thống | Đã có | Giới hạn |
|---|---|---|
| Danh mục | 19 nghề, 7 nghề chơi được | 12 nghề khóa, chưa có vòng chơi |
| Giao diện | Nền kem, điểm nhấn hồng/nâu; ngày–két–sao; menu bảng phấn; mục tiêu; quầy tương tác; review; kết ca | Vector nguyên bản gọn, không sao chép tranh hoặc asset của game tham khảo |
| Bốn nghề cũ | Giữ vòng chơi mẹ & bé, nhà thuốc, kế toán, CSKH; nối thêm mục tiêu và trò nhỏ | Bàn chi tiết vẫn mở trong cửa sổ tương tác, chưa có hoạt ảnh tay cho mọi động tác |
| Trà sữa | 10 nguyên liệu, lớp ly, cỡ/đường/đá, kiểm–đóng nắp–giao; kho theo lô; dùng lô hết hạn trước; giá chốt | Không mô phỏng nhiệt độ, chất lỏng hoặc nhu cầu thị trường theo giá |
| Giáo viên | 8 bài mẫu, 4 hồ sơ; kế hoạch tiết học, điểm danh, cách giải thích và phản hồi riêng | Lớp nhỏ theo kịch bản, không quản trị cả trường hoặc đánh giá người học thật |
| Hướng dẫn viên | 6 điểm hư cấu, tuyến có ngân sách/thời lượng/thời tiết; 4 du khách; kiểm đoàn, kể chuyện từ nguồn, tìm chủ thể ảnh | Bản đồ điểm bấm, không thế giới mở, GPS, AR hoặc lịch trình du lịch thật |
| Trò nhỏ | 28 bộ nội dung theo 7 nghề | Bốn họ cơ chế dùng chung: phân loại, lật thẻ, xếp bước, ghép cặp |
| Chuyện mới | 21 mẩu với lời thoại riêng; 3 chặng, lựa chọn, công việc nối tiếp và kỷ vật | Các lựa chọn chủ yếu thay lời đáp và nhật ký, không phải mọi nhánh đều thay toàn bộ thế giới |
| Nội dung cũ | 12 tuyến cột mốc và 96 tình huống ở bốn nghề gốc | Tình huống dùng chung khung chứng cứ/lựa chọn/thực hiện, không phải 96 mini-game |
| Hộ chiếu | Mục tiêu ngày, 12 loại huy hiệu, sticker, kỷ lục cá nhân theo nghề | Không bảng xếp hạng cộng đồng hoặc chuỗi đăng nhập bắt buộc |
| Khu phố | 5 điểm mở hoạt động thật, kỷ niệm và mục tiêu ngày hội | Chưa có đi bộ giữa các khu hoặc lễ hội nhiều người chơi |
| Nhân vật | 42 NPC hội thoại và 28 ứng viên nhân viên | NPC theo kịch bản/từ khóa; hồ sơ học sinh và du khách không cộng trùng vào số NPC |
| Nhân viên | Tuyển, phân việc, ca, đào tạo, nghỉ, chat, thưởng; sai sót và khắc phục; hiện trong cảnh | Các vai trò mới hỗ trợ theo quy tắc, không tự giải toàn bộ tiết học/chuyến đi/ly nước |
| Vận hành | Chi phí ca thực tế; kỳ 7 ca; thuê, thuế giả lập, hóa đơn, thanh toán, gia hạn; 3 cấp mặt bằng | Không luật thuế thật, vay lãi hoặc tự đuổi khỏi tiệm |
| An ninh | Kiểm chứng, báo tin, công an NPC, kết quả xử lý, thu hồi, thưởng và bảo hiểm chống nhận trùng | Hư cấu; không PvP, bạo lực hoặc dịch vụ công an thật; diễn tập không trả xu |
| Kiên nhẫn | Giảm mềm theo thao tác/lỗi và ưu tiên việc khác, thấp nhất 25%; nhịp Thư thả không giảm | Không chạy đồng hồ thật để khách bỏ về; đọc/chat/nghỉ không bị phạt |
| Review và chat | Review có công việc nguồn; 28 câu nhận xét vui theo nghề; sửa được lời trả lời của mình, không sửa sao; ký ức có nguồn | Chưa có review người thật; adapter LLM tùy chọn chưa được kiểm với model thật |
| Kinh tế mới | Lô nguyên liệu, giá chốt; tip đội tách két; thưởng combo/mục tiêu/huy hiệu chống trùng; hao hụt không trừ tiền lần hai | Bản local do người chơi sở hữu, không phải hệ chống gian lận bảng xếp hạng online |
| Lưu game | Chuyển schema 1/2 thành 3; SQLite atomic; mã yêu cầu và phiên bản; xuất/nhập bảy nghề | Chưa có tài khoản hoặc đồng bộ cloud; nhập thay cả phiên |
| Kiểm thử | Python, HTTP, SQLite, UI Chromium qua cầu nối HTTP và kiểm gói ZIP sạch | Chưa kiểm điều hướng mạng/CSP trực tiếp của trình duyệt, Safari/iPhone thật, tải đồng thời hoặc giữ chân người chơi |

Các chức năng v0.2 được giữ trừ những thay đổi router, giao diện, chuyển phiên bản và phản hồi nêu trên. Xem `ARCHIVE_V02_SCOPE.md` cho lịch sử. Không coi số lượng nội dung hoặc tên module là bằng chứng game đã hoàn thiện thương mại; cần thử chơi và cân bằng tiếp.
