# Bốn nghề nghệ thuật và dịch vụ phố

Người dùng yêu cầu trực tiếp thêm nghề nghệ thuật, luật sư, giặt ủi, bưu điện và cân đối để chơi lâu. Phạm vi chốt trong phiên: `art_studio`, `lawyer`, `laundry`, `post_office`. Tiếp tục triển khai theo chỉ đạo “cứ làm”; không đặt thêm bước xin phép cho lựa chọn triển khai thông thường.

## Thiết kế

Dùng bốn plugin nghề riêng trên engine hiện có, UI tải khi vào nghề. Không tạo thêm minigame thời gian thực hoặc chỉ đổi tên nghề cũ. Mỗi nghề có thao tác theo dữ kiện, trình tự có ý nghĩa, sai sót làm giảm kết quả và hướng dẫn sửa; mọi tiền và kết quả do server quyết định.

- Xưởng vẽ Màu Nắng: đọc đơn đặt tranh, chọn bố cục, phối màu/chất liệu, dựng các lớp tác phẩm, duyệt yêu cầu, giao tranh. Có dự án chân dung, phong cảnh, áp phích, phục dựng màu, bộ tranh và triển lãm. Xem trước tác phẩm bằng hình vector/CSS trong giao diện.
- Văn phòng luật Bình An: hồ sơ hoàn toàn hư cấu với quy tắc cho sẵn trong game; đọc tài liệu, xác định mâu thuẫn, chọn chứng cứ, tính yêu cầu, soạn phương án và xử lý diễn biến. Không dùng kết quả thắng kiện làm bảo đảm; chất lượng dựa vào chứng cứ và quy trình.
- Tiệm giặt ủi Nếp Thơm: nhận nhiều món theo phiếu, kiểm đồ và nhãn, xử lý vết bẩn, giặt, sấy/phơi, ủi/gấp, trả đúng khách. Chất liệu kỵ chế độ và lỗi trả nhầm làm mất điểm/giảm công; có đường xử lý lại.
- Bưu điện Cánh Thư: kiểm người gửi/nhận, bao gói và hàng đặc biệt, cân và tính cước theo bảng giá game, chọn dịch vụ, chia tuyến, bàn giao hoặc xử lý hàng hoàn. Phí bưu gửi là doanh thu của nơi làm, không chuyển toàn bộ thành tiền cá nhân.

## Chơi lâu và cân đối

Năm chặng nội dung theo ngày nghề 1/4/10/20/40 (xưởng vẽ có mốc triển lãm cuối 45). Các chặng thêm loại việc, dữ kiện và ngoại lệ, không chỉ tăng tiền. Thành tựu dài hạn cần số việc đạt chất lượng và nhiều ngày hoàn thành thực tế; khép ca rỗng không cấp thành tựu. Đơn tái tạo ổn định theo ngày/slot, lưu và tải giữa mọi bước.

Mỗi việc thường 5–9 thao tác có ý nghĩa; ca dùng nhịp tạo việc hiện có. Tiền công dịch vụ mục tiêu 12–28 xu/việc trước hệ số toàn game, nghề lương chỉ thêm khoản thưởng nhỏ để tránh trả lương hai lần. Công cao đi kèm thêm thao tác/độ phức tạp; vật tư trừ một lần, không cho trả công lại khi gửi lặp. Chốt các mức cuối bằng mô phỏng đường đúng/sai và đối chiếu nghề tương đương. Thời gian chơi người thật chưa đo sẽ ghi là mục tiêu, không phải kết quả kiểm thử.

Giặt ủi mở chương 2, xưởng vẽ và bưu điện chương 3, luật sư chương 4. Bản lưu cũ tự nhận bốn nghề trong migration và mở đúng chương đã đạt. Không thay dữ kiện nhiệm vụ của 50 nghề cũ.

## Tích hợp và nghiệm thu

Đủ catalogue, NPC, hướng dẫn, bản đồ, ngoại hình nơi làm, từ vựng nghề và nội dung tiến trình. Dùng lại tài nguyên hình phù hợp hiện có với biển tên/màu riêng; không ghi tài nguyên cũ là tranh mới. UI điện thoại có nút rõ, không tràn ngang, không lộ đáp án nội bộ.

Kiểm thử: từng bước đúng/sai, payload sai/đổi thứ tự/lặp nhận tiền, validate bản lưu giữa bước và JSON roundtrip, public projection không lộ khóa đáp án, chặng nội dung ngày 1–60, tiến trình không kiếm bằng ca rỗng; migration 50→54 nghề; playthrough qua HTTP/browser trên 390px và desktop; các kiểm tra map/asset/JS cùng 49.440 mẫu nhiệm vụ cũ. Đóng gói và triển khai theo quy trình live hiện có sau kiểm chứng.
