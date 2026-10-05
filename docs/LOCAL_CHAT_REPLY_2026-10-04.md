# Trả lời tin nhắn — bản local 2026-10-04

Chưa deploy; không đổi phiên bản hoặc đăng Có gì mới.

## Cách dùng

Chạm tin nhắn (hoặc nhấn giữ) → Trả lời → nhập nội dung → Gửi. Có xem trước tên/nội dung tin gốc và Hủy trả lời. Hủy không xóa chữ đang soạn. Áp dụng Cả phố, chat riêng và nhóm; không tạo cuộc trò chuyện mới. Trích dẫn giữ lại khi mở lịch sử hoặc kết nối lại. Tin gốc bị thu hồi/ẩn/chặn chuyển thành Tin nhắn không còn khả dụng.

Trên màn hình nhỏ, Ghé chỗ làm nằm dòng dưới để tên người đang chat vẫn nhìn rõ.

## Triển khai

- PostgreSQL schema21: chat_messages.reply_to bigint nullable; nâng cấp lặp lại không mất tin cũ.
- Client chỉ gửi ID tin gốc; máy chủ kiểm tra cùng kênh và quyền xem. Tin trả về reply={id,pid,name,text} tối đa160 ký tự, hoặc {id,unavailable:true}.
- Nguồn trích dẫn đọc mới theo từng người xem: blocked/marriage_blocks, hides/clears, membership, hidden/deleted/missing. Không lưu bản sao nội dung gốc trong buffer.
- Live fanout gom100 người mỗi truy vấn. Epoch vô hiệu hóa kết quả đọc bị chồng với thu hồi/ẩn/chặn; quote được xử lý ở cuối các bước bất đồng bộ history/join/resume/welcome.
- reply_hidden xóa trích dẫn cached khi chặn hai chiều hoặc xóa dữ liệu tài khoản.
- UI giữ bản nháp sau lỗi gửi, không ghi đè chữ mới hoặc mang reply sang cuộc chat khác.

## Kiểm chứng

- 15 kiểm thử PostgreSQL/socket chuyên biệt đã qua; có RED→GREEN cho xử lý thu hồi giữa lúc đọc, history decoration/welcome delay, gom truy vấn và nâng schema20→21.
- 25 kiểm thử Node reply/history đã qua.
- Review độc lập xác nhận các trường hợp tranh chấp và 205 người nhận dùng đúng3 truy vấn.
- Thử trình duyệt local: hai tài khoản chat riêng, chọn tin Trả lời, hủy giữ draft, gửi/nhận quote, mở lại vẫn có quote, thu hồi gốc làm quote unavailable ở bên kia. 390x844 không tràn ngang, tên người nhận và preview dễ đọc.
- 71 kiểm thử regression Python đã qua trong62.442 giây: output/chat-reply-verified.log. Môi trường thử PostgreSQL riêng, không đọc/ghi production.
