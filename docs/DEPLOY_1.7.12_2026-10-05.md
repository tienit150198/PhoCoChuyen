# Phát hành 1.7.12 — chủ tiệm và thuê nhà

Chủ game yêu cầu trả lời feedback và đưa các tính năng local lên phiên bản mới, không thêm thông báo.

## Phạm vi và kiểm tra

- Gói nguồn sạch từ 1.7.11 với 39 file thay đổi có chủ đích. Thêm tình huống chủ tiệm, camera, giá thuê do chủ đặt, NPC/người chơi thuê nhà, tin bất động sản và nội thất nhà thuê.
- Giữ byte hai file thông báo đã chỉnh trên production; mã thông báo vẫn 1.7.10 với đúng ba dòng, không phát lại quà hội chợ.
- ZIP output/release-1712/mnl-1.7.12.zip: 30.160.848 byte, SHA256 651cf6f615f7b33356d5b0e12493e5e7a37cd8c15f162406e4482e617358d319.
- Bộ hồi quy staging: 311 kiểm tra, 310 đạt, 1 bỏ qua do thiếu cây nguồn lịch sử 1.4.31. Node UI tình huống/thuê nhà/Có gì mới đạt. Không xem kiểm tra lịch sử này là cam kết rollback.
- Kiểm gói giải nén: 1.257 hash nguồn/asset khớp, server PostgreSQL độc lập khởi động, HTTP tạo nhân vật/mở nghề/ngày, từ chối nghề khóa, replay và export bản lưu đều đạt.
- Nâng schema 22→23 bằng đúng module hai bản trong PostgreSQL độc lập: giữ nguyên nội dung 95 bảng cũ, tạo đủ 3 bảng/8 chỉ mục thuê nhà, chạy lại không thay đổi. Xem output/release-1712/schema-upgrade-rehearsal.json.
- Các luồng giao diện và giao dịch thuê nhà qua Chromium đã được xác minh trong output/playwright/owner-rentals/report.json trước đóng gói.

## Feedback

- Đã trả lời và đánh dấu xử lý 173, 175, 178, 179, 181: đèn giao hàng, đón bé, áo thun, nhẫn dư, tự đứng quầy. Nội dung ở output/feedback-replies-1712.json; audit production /root/mnl-feedback-replies-1712.json.
- Góp ý mới 182: trả lời hướng dẫn mua ô tô và ghi nhận nghề bác sĩ cho đợt sau, giữ trạng thái đã xem. Nội dung ở output/feedback-reply-182.json.
- Mẫu kiểm tra sau trả lời không còn feedback thiếu lời đáp; không sửa chat hoặc tự hứa nghề mới đã làm.

## Chuyển bản

Rà soát độc lập xác nhận không được chạy rolling chồng worker cũ/mới: camera mới không qua bộ kiểm tra cũ; worker cũ thiếu bảo vệ hợp đồng và không hiểu nội thất lease. Script output/deploy-1712.py xác minh gói, sao lưu PostgreSQL, dừng cả game/live, xác nhận tiến trình cũ đã thoát, đổi current nguyên tử rồi khởi động bản mới. Không tự rollback về 1.7.11 sau khi bản mới đã nhận giao dịch.

Log triển khai: /tmp/mnl1712-deploy.log, phiên tmux mnl1712.

## Kết quả production

- Hoàn tất 07:27:10 UTC+7 ngày 05/10/2026, EXIT=0. Release /opt/mot-ngay-lam-nghe/releases/1.7.12-20261005072125, build 1.7.12+491ea8cf3ed7, schema 23.
- Sao lưu PostgreSQL trước chuyển bản: /root/mnl-backups/pre-1.7.12-20261005072125.dump, 1.751.267.631 byte. Không phục hồi/ghi đè dữ liệu người chơi.
- Từ bắt đầu dừng dịch vụ đến cả game/live healthy: 17,95 giây. Mẫu sau chuyển bản: cả hai dịch vụ active; live 28 kết nối, cut=0. Không có Traceback/Internal error/Database error/deadlock/pool timeout/ERROR trong mẫu log sau 07:27:11.
- Sáu mẫu HTTPS health đúng 1.7.12. Bảy asset kiểm tra cả URL thường và URL hash đều đúng byte gói; import map trỏ đúng. Thông báo vẫn 1.7.10, đúng ba dòng đã yêu cầu. Chứng cứ: output/release-1712/production-check.json; báo cáo server /root/mnl-deploy-1712.json.
- Xác nhận feedback 173/175/178/179/181 đã xử lý và có lời đáp; 182 đã xem và có lời đáp. Tại kiểm tra cuối không còn feedback chưa trả lời.
- Không commit/push, không thêm Có gì mới, không phát lại quà.
