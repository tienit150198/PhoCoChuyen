# Phát hành 1.7.10 — feedback, hội chợ và tiệm riêng

Chủ game yêu cầu sửa feedback/chat, tặng mỗi người 300 xu hội chợ, deploy và thông báo đúng ba ý.

## Gói đã kiểm tra

- ZIP: output/release-1710/mnl-1.7.10.zip — 30.109.931 byte.
- SHA256: d0bc7d1ec7f787d3011e7a72398dcedb108a56b49cb3012dece689cf149c321d. Server đã xác nhận khớp trước khi chạy.
- 88 file thay đổi có chủ đích trên nguồn sạch 1.7.9, 1.238 hash source/asset đúng khi giải nén.
- Nguồn đóng gói: 596 kiểm tra backend (593 qua, 3 kiểm tra bản lịch sử không tìm thấy cây nguồn trong thư mục staging); 96 kiểm tra bản đồ/giao thông/menu qua. Các kiểm tra lịch sử tương ứng đã chạy riêng từ worktree có cây nguồn và qua.
- Kiểm tra HTTP từ ZIP: khởi động PostgreSQL riêng, tạo nhân vật, mở nghề/ngày, từ chối nghề khóa, replay một lần và export bản lưu đều qua.
- 39.840 mẫu nhiệm vụ của 40 nghề giữ nguyên; 480 đơn cà phê 1.7.9 bằng bộ sinh legacy. Đơn GEN2 đang pha được giữ nguyên và dừng shot 27 giây thành công sau migration.
- Trình duyệt thật trên 320–430 px: quầy xếp hàng/phục vụ, lỗi mở quầy/thử lại, cả ba thức uống mới, bán nhẫn, bản đồ giao hàng, bản đồ khu phố/đi bộ/lái xe/đỗ xe. Không thấy lỗi JavaScript hoặc tràn ngang trong các luồng đã thử.
- Tặng quà có kiểm tra PostgreSQL đồng thời: trùng nội dung an toàn; xung đột nội dung/xóa sau preflight làm rollback. Bán nhẫn có kiểm tra nguyên tử, quyền sở hữu, nhẫn chung/cầu hôn và thử lại.

## Nội dung

Xem docs/FEEDBACK_2026-10-05.md. Có gì mới gồm: 300 xu chơi hội chợ; tăng xác suất thắng; thêm 40% lợi nhuận đủ điều kiện. Không phát thông báo về các thay đổi rủi ro riêng từ yêu cầu cũ.

## Triển khai và giới hạn

Chạy rolling_release.sh trong tmux mnl1710; log /tmp/mnl1710-deploy.log. Game/live dùng PostgreSQL hiện có; không đổi schema và không ghi đè dữ liệu người chơi.

Menu mới dùng GEN3 và danh mục nguyên liệu mới: sau khi có dữ liệu mới không quay nguyên bản về 1.7.9. Bản sửa tiếp phải giữ bộ đọc GEN2/GEN3; không khôi phục database cũ. Các kiểm tra quay lại 1.4/1.5 theo từng tính năng không phải cam kết tương thích toàn bộ save mới.

Quà fair1005 được xếp pending cho mọi bản lưu hiện có, rồi vào ví qua đường nhận quà chuẩn ở lần tải game kế tiếp. Người offline không mất quà đã xếp. Bản lưu mới nhận theo cửa sổ cấu hình; ID ổn định tránh phát lặp.

## Kết quả production

Hoàn tất 06:07:13 UTC+7 ngày 05/10/2026, rolling release EXIT=0.

- Release: /opt/mot-ngay-lam-nghe/releases/1.7.10-20261005060615.
- Build: 1.7.10+dadc7a50edf3.
- 6 mẫu HTTPS health trả 200/ok đúng version; 16 asset production khớp byte ZIP. Có gì mới đúng1.7.10,3 mục. Xem output/release-1710/production-check.json.
- Quà: 47.432 bản lưu tại lúc chạy. 2 đã được bộ cấp quà khi tải game ghi nhận trước; công cụ xếp thêm47.430, tổng47.432. Xem lại không còn thiếu và không chèn thêm.
- Lúc kiểm tra,4 quà đã vào ví (1applied,3seen),47.428 đang chờ người chơi tải game. Tất cả đúng300xu. Đây là sốbảnlưu,gồm khách,không phải sốtài khoản hoạtđộng.
- Game và mnl-live active; live health ok,chat/home/visits bật,20 kết nối/19người/cut0 tại mẫu đọc.
- Log sau06:07:14 không có Traceback/Internal error/Database error/deadlock detected/pool timeout trong mẫu kiểm tra.
- Bảncũ được giữ trên server nhưng không dùng nguyên bản làm rollback sau dữ liệu menu mới; xem giới hạn ở trên.

Không commit/push. Không sửa tin chat hay trạng thái feedback của người chơi; chỉ thông báo phát hành và quà đã được chủ game yêu cầu.
