# Quyền xem thẻ chúc — 2.2.1

Ở hàng rào lời chúc trong chùa, người chơi chọn **Chỉ mình tôi** hoặc **Công khai** khi viết thẻ. Mặc định là riêng tư. Chọn công khai cho phép mọi người đọc nội dung thẻ, gồm tên người nhận và lời nhắn đã nhập.

**Lời chúc của tôi** hiển thị quyền xem của từng thẻ và nút đổi quyền. Thẻ cũ nằm trong lịch sử cũng đổi được, không cần viết lại. **Bảng chung** chỉ hiển thị thẻ được chủ động chia sẻ, có tải thêm và làm mới. Chuyển về riêng tư gỡ thẻ khỏi kết quả bảng chung ở lần đọc tiếp theo.

Thẻ từ 2.2.0 tiếp tục riêng tư. Số lần viết thẻ và hoạt động chùa vẫn không giới hạn; thanh tinh thần vẫn 0–100.

## Dữ liệu

Thẻ gốc vẫn ở bản lưu/archive của chủ, không chứa quyền công khai dùng để nhập lại. Bảng PostgreSQL `chua_public_cards` là bản dữ liệu riêng phục vụ thẻ công khai, có khóa chủ/thẻ và chỉ mục phân trang. Không quét toàn bộ hồ sơ hoặc archive khi tải bảng chung; không backfill thẻ cũ. Thu hồi, nhập bản lưu, đặt lại và xóa phiên xử lý dữ liệu chia sẻ theo quyền chủ.

Tạo thẻ công khai ghi cùng giao dịch Store và chống replay. API đổi quyền dùng xác thực phiên, CSRF và kiểm tra thẻ thuộc chủ; không trả SID trong dữ liệu bảng. Đọc bảng không cache để tránh giữ kết quả công khai sau thu hồi. Cảnh chùa giữ vị trí và các hoạt động trước đây.
