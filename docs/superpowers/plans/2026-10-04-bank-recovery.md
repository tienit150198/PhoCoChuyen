# Hoàn tiền khi công an bắt được kẻ hack — 1.7.2

Yêu cầu bổ sung của chủ game: đôi khi công an bắt được kẻ hack rồi hoàn tiền. Tiếp tục quyền triển khai/deploy đã có.

Thiết kế: nút xử lý sự cố `secure` giữ nguyên ID để tương thích client 1.7.1, đổi nội dung thành khóa phiên lạ và báo công an. Cơ hội 30% theo seed và mã vụ việc; sau 2 ngày sống trả kết quả. Thành công hoàn đủ số xu thực tế bị mất vào tài khoản thanh toán và ghi cả hai sổ. Thất bại chỉ thông báo. Tự xử lý thẻ quá hạn cũng trình báo theo cùng quy tắc. Không chạy theo thời gian offline.

Dùng hàng chờ tùy chọn `rui.hack_back` riêng, không đè hồ sơ trộm tiền mặt `back`. Không đổi các khóa bắt buộc của save cũ. Mỗi hồ sơ có ID, ngày trả kết quả và số tiền (0 nếu chưa bắt được). Kiểm tra kiểu/giới hạn/ID trùng khi validate. Nếu tài khoản vắng mặt, giữ khoản hoàn chờ mở lại, không chuyển sang ví. Không mở lại ngân sách rủi ro trong tháng khi hoàn.

- [x] Test thất bại trước: hoàn đúng nguồn/đúng hạn/một lần, không bắt được, không đè hồ sơ cũ, save cũ và validate hồ sơ.
- [x] Backend, hướng dẫn và EN; giữ nguyên giới hạn thiệt hại và cách phòng ngừa.
- [x] Test hồi quy, kiểm tra render/EN và review.
- [ ] Đóng gói, verify, deploy 1.7.2 và kiểm tra live.

Giới hạn tương thích: 1.7.1 không xử lý hàng chờ mới; rollback cần giữ phần xử lý hoàn tiền hoặc sửa tiến, không khôi phục DB cũ.

Bổ sung: nếu tài khoản ở mức tối đa, giữ nguyên khoản hoàn tới khi nhận được. Hàng chờ tối đa 64 hồ sơ; khi đầy giữ thẻ vụ mới để trình báo sau, vẫn cho tiến ngày sống, không sinh thêm hack khi hàng chờ đầy. Có test hồi quy trạng thái này.

Kiểm chứng: 128 bài ngân hàng/rủi ro/hướng dẫn/i18n đạt, gồm 17 bài bank hack. Reviewer độc lập xác nhận đã sửa tràn hàng chờ, không còn lỗi chặn. JS syntax và git diff check đạt.
