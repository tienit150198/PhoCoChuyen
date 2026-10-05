# Đồng bộ tên hiển thị — local, chưa deploy

Yêu cầu: giữ nguyên username đăng nhập, tên bạn bè đổi theo tên nhân vật mới.

## Thay đổi

- Settings lưu tên nhân vật và accounts.display trong cùng giao dịch PostgreSQL ở cả CAS và đường khóa dòng; chỉ phát sự kiện khi tên thực sự thay đổi. Username, mật khẩu, phiên đăng nhập và nickname riêng của Phố nghề không đổi.
- Schema 22 sửa tên tài khoản bị lệch với tên trong save trước đây, bỏ qua tên trống, mặc định Mây và giá trị không hợp lệ. Migration khóa session theo cùng thứ tự với lệnh đổi tên, chạy lại không đổi dữ liệu đã sửa.
- Live phát tên mới đến các phiên của người đổi tên, bạn bè, thành viên chat và người cùng phòng phù hợp; tôn trọng chặn hai chiều.
- Cập nhật tên trong danh sách bạn bè, tiêu đề chat, lời nhắn/quote đã tải, thành viên nhóm, ghim và người trong nhà. Đọc lịch sử dùng tên hiện tại với truy vấn theo index và cache có giới hạn, không sửa hàng loạt nội dung chat lưu trữ.
- Khi listener kết nối lại sẽ đối chiếu tên; welcome/state đồng bộ tên của chính người chơi. Tránh gộp cập nhật tên vào một request state cũ đang chạy. Bản nháp và lựa chọn trả lời được giữ nguyên.

## Kiểm tra

- 44 kiểm tra PostgreSQL cho lưu tên, migration, account/storage và schema catalog đạt; gồm rollback, idempotence, race migration và username/mật khẩu không đổi.
- 23 kiểm tra live PostgreSQL/WebSocket đạt (8 tên + 15 reply), gồm người vào nhà sau rename, tên trong lịch sử, chặn hai chiều, khôi phục notification và SELECT trễ. Log: `output/live-player-names-tests.log`.
- 35 kiểm tra Node đạt: tên trên client, request state trễ, reconnect, bản nháp/reply, lịch sử chat và phòng chung. Log: `output/player-names-node.log`.
- Trình duyệt với hai tài khoản giả trên fixture local 61792/61793: An đổi tên → Bình thấy tên mới trong tab Bạn bè mà không reload; chat riêng đang mở đổi tiêu đề nhưng giữ bản nháp; tài khoản An hiển thị tên mới với username visit_seller không đổi. Mục Quan hệ → Bạn bè đọc được tên mới. Kiểm tra cập nhật ngay khi mục Quan hệ đang mở bị gián đoạn do công cụ trình duyệt timeout; không xác nhận bước đó bằng UI.
- Review độc lập tìm ra và đã xác nhận sửa ba nhánh còn sót: request state cũ, welcome/state khi reconnect, snapshot người trong nhà.
- git diff --check đạt cho các file thay đổi liên quan.

Không truy cập dữ liệu production, không deploy và không thay đổi Có gì mới. Migration sẽ áp dụng khi bản sửa được triển khai sau khi chủ dự án yêu cầu.
