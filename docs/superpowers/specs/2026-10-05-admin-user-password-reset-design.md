# Đổi mật khẩu người dùng trong admin

Ngày: 05/10/2026

## Yêu cầu

Trong admin, tìm theo tên hoặc username rồi bấm **Đổi mật khẩu** ở người dùng cần xử lý. Quản trị viên đặt mật khẩu mới trực tiếp, tương tự thao tác đã thực hiện cho Yến My và Cô Cả.

## Luồng được đề xuất

1. Mỗi hàng trong danh sách người dùng có nút **Đổi mật khẩu**, kể cả kết quả tìm kiếm và các trang tiếp theo.
2. Nút mở hộp thoại ghi rõ tên và username đã chọn, có hai ô **Mật khẩu mới** và **Nhập lại mật khẩu**, nút **Hủy** và **Đổi mật khẩu**.
3. Mật khẩu cần 8–128 ký tự, hai lần nhập phải khớp. Không yêu cầu mật khẩu cũ của người dùng.
4. Khi đang gửi, khóa nút gửi để tránh thao tác trùng. Lỗi xuất hiện trong hộp thoại để quản trị viên sửa hoặc thử lại; không tự gửi lại yêu cầu ghi.
5. Thành công thì xóa nội dung mật khẩu khỏi giao diện, đóng hộp thoại và báo tài khoản đã đổi. Giữ nguyên từ khóa tìm kiếm và trang danh sách đang xem.
6. Các phiên đăng nhập của tài khoản được đặt lại mật khẩu bị thu hồi; tiến trình chơi và hồ sơ của họ được giữ nguyên. Nếu quản trị viên đổi chính tài khoản đang dùng, họ cũng đăng nhập lại bằng mật khẩu mới.

## Lựa chọn giao diện

- **Hộp thoại tại hàng người dùng — chọn:** khớp yêu cầu, nhìn rõ tài khoản trước khi đổi, giữ ngữ cảnh tìm kiếm.
- Trang chi tiết riêng: phù hợp khi có thêm nhiều chức năng quản lý tài khoản, nhưng hiện tại tăng số bước.
- Biểu mẫu ngay trong hàng: ít chuyển màn hình, nhưng làm bảng dài và khó dùng trên điện thoại.

## Máy chủ

- Thêm API POST riêng cho admin và tái sử dụng kiểm tra quyền admin, CSRF và Origin đang có.
- Chỉ xử lý sau khi xác thực. Giới hạn tần suất thao tác theo phiên quản trị.
- Nhận ID và username từ hàng đã chọn; đối chiếu chúng với cùng một tài khoản trước khi cập nhật.
- Dùng bộ kiểm tra mật khẩu và hàm băm scrypt hiện có. Không lưu mật khẩu rõ, không đưa mật khẩu hoặc hash vào phản hồi hay nhật ký.
- Cập nhật mật khẩu và thu hồi các phiên của tài khoản trong một giao dịch. Không đọc hoặc ghi JSON bản lưu của người chơi, không thay đổi cấu trúc dữ liệu.
- Trả lỗi rõ cho mật khẩu không hợp lệ, xác nhận không khớp, tài khoản không còn tồn tại và truy cập thiếu quyền.

## Kiểm tra hoàn thành

- Người chưa đăng nhập, người chơi thường và admin thiếu CSRF không được đổi mật khẩu.
- Admin đổi đúng tài khoản: mật khẩu mới đăng nhập được, mật khẩu cũ bị từ chối, các phiên cũ bị thu hồi; tài khoản khác và bản lưu mục tiêu không thay đổi.
- Mật khẩu yếu, xác nhận sai và ID/username không khớp không gây cập nhật.
- Giao diện tìm người dùng, chọn đúng hàng, hủy, gửi, lỗi và thành công hoạt động trên máy tính và điện thoại.
- Kiểm thử trên dữ liệu riêng; không dùng tài khoản người chơi thật để thử đổi mật khẩu.

## Phạm vi mã nguồn

Danh sách đang nằm trong `game/admin_users.py`, `public/js/admin/users.js`; quyền và API ở `server.py`; giao diện dùng CSS admin hiện tại. Bổ sung kiểm thử backend và frontend cạnh các kiểm thử danh sách người dùng.

Workspace `wt-feedback-0410` có nhiều thay đổi của công việc khác. Phần thực hiện sẽ dùng bản nguồn tách riêng dựa trên bản đang phục vụ hoặc gói tương ứng để không gom các thay đổi ngoài yêu cầu. Đối chiếu lại bản đang chạy trước khi chuẩn bị cập nhật máy chủ.
