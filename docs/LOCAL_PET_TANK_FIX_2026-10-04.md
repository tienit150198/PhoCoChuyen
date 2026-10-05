# Sửa chia bể tại shop thú cưng — chưa deploy

Đơn setup trước đây chỉ có một bể: chọn cỡ mới ghi đè bể cũ, và phần chấm điểm coi mọi cá trong giỏ là sống chung. Đơn nhiều loài vì vậy không có cách tách cá để tránh lỗi tương thích.

- Cho thêm bể riêng, đổi cỡ, chọn số cá và đồ dùng theo từng bể. Bớt cá ở bể cũ rồi thêm sang bể mới để chuyển; chỉ bỏ bể khi đã lấy cá ra.
- Chấm dung tích, cá xung khắc và thiếu đồ dùng theo từng bể. Cảnh báo hiển thị trước thanh toán và chỉ rõ số bể.
- Giỏ hàng, giá tiền và trừ kho cộng đủ mọi bể; kiểm tra tổng tồn kho, khóa chỉnh sửa sau chốt hóa đơn, kiểm tra dữ liệu lưu chống sửa sai phân bể. Save cũ vẫn được hiểu là một bể.
- Không thay đổi tính cách hoặc cơ chế đánh giá của khách; tách bể đúng chỉ loại bỏ lỗi chăm cá bị tính sai.

Đã chạy đạt 110 kiểm thử Python (shop thú cưng, chia bể, đơn khách thật), kiểm thử UI Node và kiểm tra cú pháp JS. Thử trình duyệt local ở 390px: thêm/bỏ bể, cá vàng riêng với cá bảy màu; thêm betta vào bể cá vàng hiện cảnh báo đúng bể, bỏ ra thì cảnh báo biến mất. Không tràn ngang.

Chưa deploy, chưa đăng Có gì mới.
