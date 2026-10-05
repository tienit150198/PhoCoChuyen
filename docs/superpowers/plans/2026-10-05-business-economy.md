# Kinh tế quầy, rủi ro tài sản và đời sống nhân viên

Yêu cầu trực tiếp 05/10: bổ sung các cơ chế dưới đây, kiểm tra rồi deploy yên lặng. Đây là việc mới trong cùng đợt công việc; đề án 9 nghề/TT99 vẫn được giữ riêng, chưa trộn vào gói kinh tế.

## Quyết định triển khai

- Mở/đóng quầy là trạng thái kinh doanh thật trên server, không chỉ đóng màn hình. Đóng ngừng khách mới và doanh thu NPC; xử lý nốt khách đã đặt, không tạo đơn bù cho giờ đã đóng. Giữ công nợ đã có. Mở lại không hoàn lại chi phí hay thay kết quả cũ.
- Thị trường theo đợt thời gian thực, có suy thoái rõ (lượng khách còn 25–50%), ổn định và hưng thịnh (150–180%). Quyết định theo kỳ, không theo số lần tải. Tác động số khách/đơn NPC; giữ giá người dùng đặt và hóa đơn khách đã nhận.
- Quầy thêm vật dụng bảo vệ có tác dụng cụ thể, giữ camera giảm một nửa xác suất trộm. Có chi phí bảo vệ định kỳ, thuế thu nhập tính trên lãi dương, phí môi trường; sổ thu chi hiển thị từng khoản. Đây là mức tiền mô phỏng game, không phải chế độ thuế ngoài đời. Không trừ ví cá nhân hoặc âm quỹ tự động.
- Rủi ro người giàu dựa vào tài sản hiện có: tăng xác suất và mức thiệt hại trộm/hack theo bậc tài sản, không nhắm tài khoản cụ thể. Giữ bảo vệ người mới, thời gian nghỉ giữa sự cố, trần thiệt hại tháng và tác dụng đồ phòng vệ. Không truy thu sự cố cá nhân trong thời gian offline.
- Nhân viên NPC tại Quầy riêng và Sổ tiệm có sự kiện tăng lương, xin nghỉ, cưới. Có lựa chọn và chi phí công khai tại thời điểm xử lý, nhật ký và chống trả hai lần; không áp dụng nhầm cho người chơi làm thuê. Chất lượng/morale/kinh nghiệm ảnh hưởng sao đánh giá, đánh giá khách thể hiện rõ người phục vụ.
- Giữ mọi khoản tiền/hàng/đơn đã có. Mọi kết quả server kiểm tra; reload/retry không quay lại sự kiện hoặc tính tiền hai lần. Không phát Có gì mới hay phát lại quà.

## Phân công và thứ tự

1. Rủi ro: `game/rui.py`, module hỗ trợ mới nếu cần, giao diện rủi ro và test riêng. Viết ca kiểm tra bậc tài sản, thiệt hại/tháng, bảo vệ, save cũ trước; sau đó thực hiện.
2. Quầy: `game/quay_business.py`, `game/quay_self.py`, `game/quay.py` và module thị trường/chi phí riêng. Test đóng/mở/offline, phân kỳ thị trường, tính chi phí nhất quán theo polling, đơn đã đặt và save cũ trước; sau đó thực hiện.
3. NPC: module `game/staff_life.py`, `game/workplace_business.py`, `game/operations.py` và test riêng. Tạo API dùng chung cho quầy; điều phối với phần quầy về hook, không cùng sửa file.
4. Giao diện: root sở hữu `public/js/v4/quay.js`, `public/js/operations-ui.js`, CSS và test UI. Hiển thị trạng thái mở, thị trường, thiết bị/chi phí, sự kiện và sao nhân viên ở đúng màn quản lý.
5. Kiểm tra tích hợp PostgreSQL, schema và luồng browser di động. Kiểm tra lại các cam kết phân kỳ, không âm kho/quỹ, không trả trùng và hiệu năng settlement.
6. Review thay đổi và tương thích save với bản 1.7.13. Đóng gói từ nguồn sạch 1.7.13, chỉ chép thay đổi đã duyệt; lưu backup, chuyển bản tương thích, xác nhận health/static/luồng đọc. Giữ hai file Có gì mới byte-for-byte.

Không tự tạo mục tiêu hoàn tất hay ghi đã deploy khi chưa có kiểm chứng production.
