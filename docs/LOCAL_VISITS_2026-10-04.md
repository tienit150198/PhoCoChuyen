# Ghé chỗ làm, khách thật và đánh giá — bản local

Chưa deploy. Chưa tăng phiên bản ứng dụng, chưa ghi Có gì mới.

## Trải nghiệm

- Bạn bè, chat và hồ sơ có lối Ghé chỗ làm; Mọi người đang làm gì hiển thị nơi chủ cho phép công khai. Danh sách có tải thêm.
- Hiển thị nghề đã bắt đầu và quầy đang sở hữu. Mặc định chỉ bạn bè; chủ chọn công khai, bạn bè hoặc tạm đóng. Chặn hai chiều có hiệu lực ở API và phòng trực tiếp.
- Khung ghé thăm riêng giữ công việc và bản nháp của khách. Thấy avatar, người có mặt, hoạt động; đổi chỗ đứng, chào, thả tim, cổ vũ, nói chuyện. Chủ thấy khách khi đang thao tác nghề.
- Xem và xác nhận giá trước khi giữ xu. Khách chọn dịch vụ thật trong nghề/menu và ghi chú. Chủ nhận đơn trong sổ khách rồi thực hiện minigame hiện có; giữ nguyên công việc cũ.
- Nhân viên tự phục vụ bằng vật liệu, quỹ lương và thời gian thật. Khi chủ offline, khách ghé vẫn làm công việc đã đến hạn được tính tiếp. Thiếu hàng/quỹ thì không nhận thêm.
- Hoàn thành mới chuyển tiền giữ đúng một lần. Mỗi đơn có một đánh giá 1–5 sao, nhãn, nhận xét và lời trả lời của chủ. Hiển thị chủ hoặc nhân viên phục vụ. Hủy/từ chối trước nhận đơn được hoàn xu.

## Tính nhất quán

- PostgreSQL schema 19: work_visit_places, work_service_orders, work_service_reviews. Không thêm SQLite.
- Giữ dữ kiện/đáp án nhiệm vụ; metadata chứa đơn và khách. Chặn tiền, tip và nhận xét NPC cho đơn người chơi.
- Store ghi biên nhận cùng giao dịch tiến trình ở cả CAS và nhánh khóa trực tiếp. Thanh toán/hoàn tiền có chốt trạng thái chống trả trùng.
- Nhập bản lưu xóa liên kết và đơn người chơi từ tệp, hủy đơn đang phục vụ để hoàn tiền. Không trả tiền từ nhiệm vụ nhập; thử nhập lại tệp cũ nhiều lần không kẹt chỗ nhân viên.
- Phòng live tối đa 24 người, hiện diện chỉ ở bộ nhớ. LIVE_VISITS mặc định theo LIVE_STREET. Kiểm tra quyền trước tương tác và định kỳ; vào đồng thời không vượt qua chặn nhau.
- Khung phòng hiển thị người và hoạt động công khai; không gửi toàn bộ bản lưu, số tiền hay lời giải của chủ.

## Kiểm chứng

- Lượt tích hợp cuối: **105 tests Python passed**, gồm bridge, giao dịch PostgreSQL, quầy, Sổ tiệm, Store, HTTP/CSRF, live và schema. Log: output/visits-final-checks.log.
- Các lượt riêng: 287 engine/task compatibility/business tests; 33 live/home/schema tests. Không cộng vì có phần trùng.
- Bốn bộ JavaScript: workplace_visit_ui, quay_business_ui, workplace_business_ui, api_refresh; kiểm tra cú pháp module sửa.
- Hai tài khoản local: Bạn bè → Ghé tiệm → thấy nhau → đặt đơn 75 xu và ghi chú → chủ nhận → minigame lấy/gói/kiểm/giao quà → khách đánh giá → chủ trả lời. Màn phục vụ ở 390px; công việc cũ của cả hai giữ nguyên.
- Rà soát độc lập xác nhận đã sửa lỗi phân trang, activity live, avatar và nhập bản lưu gây kẹt đơn.

Không truy cập hoặc thay đổi production. Fixture và PostgreSQL thử nghiệm chạy riêng.
