# Đồ độc bản & nhà sưu tầm

Yêu cầu: đồ đấu giá khác nhau rõ, đẹp và đáng sưu tầm hơn; có bảng top liên quan.

## Thiết kế

Người chơi xem món trước khi trả giá, rồi trưng bày thành quả. Cảm giác phòng tranh nhỏ của Phố Mây: khung đồng, lụa, sơn mài, con dấu, nhãn tác giả. Màu trong tranh: đồng vàng, đỏ son, xanh ngọc, chàm đêm, trắng ngà. Giao diện giữ token, font và khoảng cách 4px của game; khung tranh là vật thể minh họa, không phải khung UI.

Điểm riêng: tác phẩm nhìn thấy ở phiên đấu giá chính là tác phẩm treo ở nhà. Thay ảnh đổi màu bằng bố cục theo chủ đề; thay danh sách sở hữu toàn chữ bằng phòng tranh; thay top chi tiền bằng điểm độ hiếm cố định. Quy tắc và câu chuyện nằm trong phần mở rộng, ưu tiên món đồ và nút trả giá trên điện thoại.

## Các bước

1. Test catalogue, điểm sưu tầm, bản lưu cũ, metadata phiên cũ và đầu ra bảng top.
2. Bổ sung bốn tác phẩm: Long vân sơn mài, Hạc trên nền ngọc, Vịnh ngọc ban mai, Ngân hà khảm trai. Giữ nguyên ID và quyền sở hữu cũ.
3. Bộ SVG dùng chung: 14 tranh có bố cục riêng, hiển thị cả ở đấu giá và nhà. Tạo hình riêng cho danh thắng, huy hiệu, biển số và số điện thoại.
4. Điểm theo tier 10/40/120; chỉ tính đồ đã nhận. Không tính tiền giữ, giá trả hoặc stats tự khai. Top tích hợp bảng xếp hạng hiện có, cùng quyền ẩn tên, backfill khi nâng phiên bản.
5. Kiểm tra Python/JS, UI mobile/desktop, code review và commit. Không thay schema hoặc cơ chế escrow/chốt phiên.

## Xác minh

- Bốn món mới nhận được và treo nhà được; 14 hình khác nhau về cấu trúc.
- Đồ cũ vẫn được nhận diện, tiền mua không biến thành điểm hoặc tài sản ròng.
- Top có dữ liệu, rỗng, lỗi/thử lại, vị trí cá nhân và trạng thái ẩn tên.
- Các test PostgreSQL chỉ chạy với database thử nghiệm.
