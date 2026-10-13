# Chùa và địa điểm công cộng đi lại được

Yêu cầu trực tiếp: ghé chùa, thắp hương, cầu may và treo thẻ chúc người thân; không hạn chế lượt, tăng tinh thần. Các địa điểm khác cũng phải có không gian đi lại. Giữ nghề làm việc ở chùa độc lập với ghé thăm.

## Chùa

Tận dụng cảnh sân/chánh điện/nhà ăn đã có. Cửa chùa trên phố và nút đi chùa mở thẳng cảnh. Người chơi đi tới lư hương, chiếu khấn và hàng treo thẻ rồi tương tác. Bỏ hạn mức ngày và chặn lặp mọi hoạt động; quy tắc bữa cơm ngày rằm/mùng một và bụng no vẫn giữ. Tinh thần hồi trong thang hiện có 0–100; đầy vẫn làm được, phản hồi chỉ ghi điểm thực tăng.

Lời khấn thêm may mắn cho người sống. Thẻ chọn người nhận và lời chúc, tùy chọn tên 40 ký tự/lời riêng 140 ký tự, được lưu qua lần quay lại/ngày mới. Lưu 40 thẻ gần nhất trong bản lưu, phần cũ vào kho lưu trữ cùng giao dịch để không phình hồ sơ. Không giới hạn số lần tạo. Mặc định thẻ riêng người viết; câu hỏi tùy chọn về bảng chung đã gửi và sẽ cập nhật theo câu trả lời trước khi chốt.

Giữ v1 và các trường cũ; thẻ là trường tùy chọn. Payload lời nguyện cũ tiếp tục hoạt động. Nội dung thẻ hiển thị có escape; danh sách xem lại có ngày và người nhận.

## Các địa điểm công cộng

Phòng đi lại mới cho café, spa, rạp phim, karaoke, sân chơi kéo co/chó sủa, làm tóc, làm móng, thủ công, sách, mỹ thuật, âm nhạc, góc đọc, vườn cộng đồng và gia đình. Cảnh có đồ đạc và đường đi riêng phù hợp nơi chốn. Đi tới quầy/ghế/bàn hoạt động mới mở chức năng hiện có; phí vẫn do server hiện tại quyết định và cần xác nhận như trước. Vào cảnh không thu tiền.

Giữ các cảnh đã đi được: công viên chung, hội chợ, câu cá, thuyền, hồ bơi, khu nhà. Sửa lối vào câu cá/thuyền/hồ bơi đang im lặng ở giao diện cũ. Điểm quản lý thuần túy như ngân hàng, bảng xếp hạng, hồ sơ và bảng việc giữ màn hình chức năng; không giả thành địa điểm vui chơi.

Điều khiển chuột/chạm, bàn phím và cảm ứng; tránh vật cản, chỉ tương tác khi tới gần. Thoát bằng cửa/Escape/nút về phố, hủy vòng vẽ và bộ nghe phím, không cho nhân vật ngoài phố chạy phía sau. Tận dụng avatar/trang phục hiện tại. Không mở rộng giao thức hiện diện nhiều người trong đợt này.

## Kiểm chứng và phát hành

Kiểm thử backend lặp/đầy tinh thần/dữ liệu cũ/lưu ngày mới/idempotency và archive. Kiểm thử hình học/pathfinding/proximity và vòng đời đóng mở. Browser thật 390/1280, giao diện cũ/mới, nhấp cửa đi vào, avatar đổi tọa độ, tương tác, ra lại phố và tải lại thẻ.

Phát hành sau kiểm thử và đóng gói dựa đúng live2.1.0. Máy chủ chỉ còn ~3,7GB: kiểm dung lượng trước, không tạo backup lớn trên ổ production; nếu sao lưu dùng streaming ra máy phát triển. Không xóa backup/release cũ. Sau triển khai kiểm API đầy đủ, tài nguyên, DB và dung lượng.
