# Góp ý người chơi ngày 04/10/2026

Base: `65ad1c7` (nhánh phát triển sau 1.6.6). Làm trên `fix/feedback-0410` để giữ các thay đổi khác.

1. Kiểm tra lại quỹ: nghề cũ không thu phí, mở lại miễn phí, hoàn phí cũ một lần. Dùng `tests/test_old_career_cost.py`; giữ cơ chế hiện có nếu kiểm thử qua.
2. Thêm trình báo trong game cho review đe dọa đòi tiền (`bocphot`). Lưu nội dung và cuộc trao đổi làm bằng chứng; không thay sao hoặc thu tiền; khóa trao đổi đã trình báo và ngăn trình báo lặp. Giao diện giải thích đây là hồ sơ trong game, không bảo đảm gỡ sao. Kiểm thử luồng action, public state, xác nhận, tính tương thích bản lưu.
3. Homestay: tái hiện việc giữ phòng/nhận cọc bỏ sót đơn OTA chưa đồng bộ và giữ phòng của khách khác. Thống nhất kiểm tra lịch ở backend và frontend, bỏ qua đúng phiếu/đơn đang xử lý; giữ quy tắc ngày trả phòng được đón khách mới. Kiểm thử từ chối trùng lịch và xác nhận hợp lệ.
4. Thăng chức: giải thích ngay ở màn hình thăng tiến rằng làm thuê tăng lương, chủ tiệm tăng tiền boa; từ bậc 3 được giao và kiểm tra việc của đội. Không thay cơ chế đã có.
5. Chạy kiểm thử Python liên quan, kiểm tra JavaScript và kiểm tra render UI; lưu kết quả và ghi rõ tình trạng chưa triển khai lên website.
