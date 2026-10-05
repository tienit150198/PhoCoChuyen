# Nhà chung: hiện diện, tương tác và trang trí

Người sống chung trong hệ thống hôn nhân hiện tại nhìn thấy nhau khi mở cùng phòng. Máy chủ xác định quyền từ phiên đăng nhập và trạng thái nhà/hôn nhân đã lưu; trình duyệt chỉ gửi phòng, vị trí và một trong ba tương tác ôm, hôn, thả tim.

- Thêm HomeFeature cho WebSocket: vào/rời phòng, di chuyển, tương tác, thu hồi khi chuyển nhà/ly hôn/chặn và xử lý nhiều tab.
- Dùng nội thất của cả hai như hiện tại, giữ quyền sở hữu riêng. Tường/sàn lấy chủ nhà làm nguồn chung; đổi từ bên nào cũng lưu nguyên tử cùng thanh toán và biên nhận. Hiển thị kết cấu sửa sang giống nhau.
- Phát thông báo làm mới trang trí sau commit; giữ polling dự phòng. Thứ tự vẽ đồ trùng vị trí phải nhất quán theo chủ sở hữu.
- Hiển thị người kia bằng avatar, tên, chuyển động và các nút tương tác dùng được bằng bàn phím; rời hiện diện khi đóng nhà.
- Kiểm tra PostgreSQL/WebSocket với hai tài khoản, chặn/ly hôn/chuyển nhà, kết nối lại và nhiều tab; kiểm tra giao diện và đóng gói trước deploy.

Không thêm nghề DIY hay nghề mới trong đợt này. Không đưa thay đổi xác suất rủi ro của bản trước vào thông báo người chơi.
