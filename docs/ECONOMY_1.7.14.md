# Kinh tế 1.7.14 — 05/10/2026

Phát hành theo yêu cầu, không tạo Có gì mới và không phát lại quà. Nghề mới/TT99 giữ riêng.

## Cơ chế

- Mở/đóng quầy là trạng thái lưu server. Đóng chặn khách mới và bán NPC; đơn đã nhận được phục vụ nốt. Không bù doanh thu cho thời gian đóng.
- Thị trường có 48 kỳ nửa giờ lặp theo ngày: suy thoái giảm lượng khách còn 25–50%, hưng thịnh tăng lên 150–180%. Giá menu và hóa đơn khách đã nhận giữ nguyên. Thời điểm khách NPC tới tích phân qua các kỳ bằng lịch cộng dồn, không lặp từng kỳ trống khi offline lâu.
- Thuế quầy mới bằng 8% lãi dương, thay thuế doanh thu cũ cho giao dịch mới; khoản thuế lịch sử được giữ. Thiệt hại, chi phí nhân viên và chi phí hoạt động giảm cơ sở chịu thuế; phần xu lẻ có carry. Có phí môi trường và gói bảo vệ 0/3/7 xu mỗi 10 phút hoạt động, không tự rút ví cá nhân.
- Chuông báo trộm giảm xác suất trộm; thiết bị chống chập và vệ sinh giảm chi phí xử lý tương ứng. Camera vẫn giảm đúng một nửa xác suất trộm sau các hệ số khác.
- Trộm/hack cá nhân tăng theo bậc tổng tài sản 10 nghìn/100 nghìn/1 triệu xu. Mức thiệt hại tối đa tăng theo tài sản; vẫn có trần mỗi sự cố/tháng, bảo vệ người mới và không truy thu cá nhân offline. Bổ sung bảo mật hai lớp, diệt virus và báo trộm.
- NPC ở Quầy riêng và Sổ tiệm có yêu cầu tăng lương, cưới và xin nghỉ sau hoạt động thực. Một sự kiện chờ, lựa chọn có giá, phương án miễn phí, lịch sử và chống xử lý hai lần. Tăng lương chỉ áp dụng công việc tương lai; giữ lương đã làm. Nhân viên có đánh giá theo năng lực, tinh thần và kinh nghiệm.

## Kiểm tra

- PostgreSQL: luồng quầy, thị trường, thuế, đóng/mở, khách đã nhận, NPC, rủi ro cá nhân, sổ tiệm và lưu bản chơi.
- Kiểm tra giao diện thuần JS cho payload mở/đóng, gói bảo vệ từ server, lựa chọn NPC, số tiền và escaping.
- Chromium 390×844 trên server thật và schema dùng một lần: đóng/mở qua reload, đổi gói bảo vệ, tặng phong bì qua API; không lỗi console hay tràn ngang. Bằng chứng tại output/playwright/economy-1714.
- Review độc lập lịch thị trường: 21.736 ca điểm biên/ngẫu nhiên và thời gian rất dài. Không duyệt qua kỳ trống.
- Một số bộ kiểm tương thích server 1.4.31/1.5.2 cũ đã lỗi whitelist giá nghề từ trước; không sửa lỏng validation để che lỗi. Kiểm tương thích tác vụ trực tiếp với nguồn sạch 1.7.13 trước phát hành.

## Triển khai

Đóng gói từ nguồn sạch 1.7.13 và danh sách file chọn rõ. Hai file thông báo giữ nguyên từng byte. Không đổi PostgreSQL schema 23.

Các field chi phí, vật dụng mới và lịch sử giảm phí không được validator 1.7.13 chấp nhận. Dừng đồng thời game/live, chuyển bản, khởi động và kiểm tra health; không chạy song song writer cũ/mới. Sao lưu trước khi chuyển. Sau khi đã có giao dịch mới, sửa tiến trên bản tương thích, không tự phục hồi backup làm mất tiến trình mới.
