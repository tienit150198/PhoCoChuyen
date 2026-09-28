# Nguồn tham khảo thiết kế v0.3

Ảnh người dùng cung cấp là chuẩn thị giác chính: nền kem, viền nâu, nút hồng nổi, menu bảng phấn, ngày/két/rating, khách với yêu cầu và thanh kiên nhẫn, chuẩn bị mẻ, review có trả lời, kết ngày. Không trích xuất/đóng gói hình, font, logo hoặc code của các game trong ảnh. Canvas/SVG/CSS trong repo là bộ hình nguyên bản đơn giản, không phải bản clone tài sản.

Đọc mô tả chính thức dưới đây để học **cơ chế**, không tuyên bố đã chơi thử toàn bộ game hoặc kiểm tất cả phiên bản. Ngày nghiên cứu: 28/09/2026.

| Nguồn chính thức | Điều rút ra | Cách hiện thực trong v0.3 |
|---|---|---|
| Good Pizza, Great Pizza — https://www.goodpizzagreatpizza.com/ | Đơn khách có khác biệt, thao tác món, câu chuyện và trang trí | Pha trà nhiều thành phần, menu/chuẩn bị, review, chuyện khách quen; không sao chép pizza hoặc nội dung nhân vật |
| Coffee Talk, Toge Productions — https://www.togeproductions.com/project/coffee-talk/ | Đồ uống đi cùng việc lắng nghe và câu chuyện người ghé | Hội thoại và lời hẹn nối qua công việc thật; mẩu chuyện trà/khách; không sao chép cốt truyện |
| TOEM, trang nhà phát triển trên Steam — https://store.steampowered.com/app/1307580/TOEM_A_Photo_Adventure/ | Chụp ảnh để giải vấn đề và khám phá nhẹ nhàng | Phiếu ảnh tìm chủ thể, bưu thiếp theo điểm, giúp đoàn; đây là mini-game biểu tượng nhỏ, không hệ máy ảnh TOEM |
| Let's School, trang nhà phát triển trên Steam — https://store.steampowered.com/app/1937500/Lets_School/ | Trường học có học sinh/giáo viên, phát triển người và hoạt động | Tiết học, nhu cầu từng hồ sơ, trợ giảng và câu chuyện lớp; không xây trường 3D hoặc sao chép mô hình quản trị |

Trang Tiệm Trà Nhỏ người dùng dẫn: https://trongnhi.trongnhi110266.workers.dev/ chỉ trả về văn bản HUD rất ít qua trình đọc web. Vì vậy mọi nhận xét chi tiết về bố cục được dựa trên **ảnh người dùng**, không suy diễn đã truy cập/chơi thành công toàn bộ trang.

Các trang nguồn là bằng chứng cho đặc trưng họ tự mô tả, không phải bằng chứng rằng bản game này sẽ tăng retention, có doanh thu hoặc đạt mức chất lượng của game thương mại. Không lấy giá bán, review-score hoặc thông tin sale làm thiết kế.
