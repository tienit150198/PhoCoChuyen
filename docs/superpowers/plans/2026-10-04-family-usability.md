# Nhà & Gia đình dễ dùng — kế hoạch triển khai

**Goal:** Người chơi tìm thấy nhà chung, lời mời và con chung ngay; cử chỉ có động tác thật và phản hồi tự chọn từ người nhận.

**Architecture:** Giữ giao dịch gia đình PostgreSQL hiện có, cải thiện dữ liệu điều kiện và điều hướng. Live lưu lời đề nghị tương tác tạm trong phòng, kiểm tra quyền và khoảng cách trước gửi/trả lời; không lưu cảm xúc vào hồ sơ. Client vẽ tư thế từ ngoại hình hiện tại.

**Tech Stack:** Python/PostgreSQL/WebSocket; JavaScript/SVG/CSS hiện có.

## Thiết kế đã chọn

Nhà là nơi quay về, mời người thương, chăm bé, nhận lời mời và gặp nhau. Tông giấy kem, gỗ nâu, cây xanh, hồng dịu, vải vàng theo giao diện game. Giữ Be Vietnam, nhịp 8px, nút tối thiểu 44px. Điểm nhận diện là căn nhà và hai nhân vật, không dùng bảng thông số thay các lối vào sinh hoạt. Thay đoạn hướng dẫn dài bằng bước kế tiếp; thay nút biến mất bằng lý do và lối đi; cất đổi tên/quần áo/rời nhà vào mục phụ.

- Lối vào Nhà & Gia đình rõ trên hành trình/nhà, ba hành động Vào nhà, Mời về ở, Con chung.
- Tab riêng, lời mời nhận nằm đầu, người gửi thấy đang chờ; thông tin chưa đủ ngày/nhà nói rõ ai còn thiếu và cách tiếp tục.
- Người gửi bước tới, tự ôm/hôn/thả tim trước. Người nhận tự chọn Đáp lại, Ngại ngùng, Giận dỗi, Để sau. Đáp lại thì cả hai cùng tương tác; bỏ qua chỉ người gửi làm. Người dùng đã chọn rõ cơ chế này.
- Cử chỉ và phản ứng đồng bộ hai màn hình; hết lời mời sau 15 giây, đổi phòng/đi xa/đóng cửa sổ thì hủy; hỗ trợ giảm chuyển động.

## Công việc

- [x] Kiểm tra thất bại trước cho điều kiện cả hai và quyền trả lời/cự ly/phòng/hết hạn/chống trả lời lặp.
- [x] Dữ liệu family eligibility + phản hồi live tạm thời.
- [x] Family navigation và thứ bậc nội dung/nút/trạng thái dễ đọc trên điện thoại.
- [x] Tư thế người gửi và phản ứng nhận, cleanup đúng vòng đời; không thay ngoại hình/đồ mặc.
- [x] Hai tài khoản thật trên PostgreSQL thử nghiệm: mời về, đồng ý, con chung; cử chỉ và ba phản ứng.
- [ ] Review độc lập, bản dịch, gói chung, kiểm tra tương thích và deploy một lần.
