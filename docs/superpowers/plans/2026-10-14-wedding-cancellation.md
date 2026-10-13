# Ngăn tiệc cưới tiếp tục sau khi hủy hôn

## Bằng chứng và phạm vi

Phản hồi 370 được kiểm tra lại sau khi chủ game hỏi rõ về giờ mở tiệc. SQL production xác nhận một tiệc đã hủy trước giờ mở vẫn có 17 bản ghi khách sau thời điểm hủy và 360 xu thưởng theo phút. Kết luận ban đầu chỉ về nhãn lịch sử là chưa đầy đủ.

`WeddingFeature.refresh` giữ mọi tiệc đã có trong bộ nhớ dù truy vấn lịch mới không còn trả về; `wed_in` tin bản ghi bộ nhớ. Cần sửa vòng đời tiệc trực tiếp, giữ thay đổi nhãn lịch sử hợp lệ của đợt trước.

## Các bước

1. Tái hiện bằng PostgreSQL và WebSocket thật: hủy sau khi nạp lịch, vào từ lịch cũ, hủy khi có khách và khách xem ngoài cổng, thưởng đang chờ.
2. Phân biệt tiệc đã hủy với tiệc đã hoàn tất còn thời gian chào tạm biệt. Gỡ lịch, đóng phòng và kiểm tra trạng thái mới khi vào.
3. Chặn tác vụ ghi khách, tương tác và phát thưởng sau khi hủy; kiểm tra trạng thái trong giao dịch cho các thay đổi cần tính nguyên tử. Giữ thứ tự khóa phù hợp với hủy hôn.
4. Rà soát độc lập yêu cầu, sau đó chất lượng; chạy bộ kiểm thử tiệc và hiệu ứng liên quan.
5. Đính chính lời đáp phản hồi 370, lưu kết quả kiểm chứng và commit. Chưa deploy trong lượt này.

Không thay đổi quan hệ/tiệc mới hợp lệ, không thu hồi xu lịch sử, không sửa dữ liệu người chơi để che lỗi.
