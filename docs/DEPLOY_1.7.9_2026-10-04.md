# Phát hành 1.7.9 — tốc độ API và UI khách ghé

Người dùng yêu cầu “ok sửa xong deploy đi”. Đã hoàn tất **23:54:11 UTC+7 ngày 04/10/2026** bằng rolling release trong tmux; mã thoát 0.

- Release: `/opt/mot-ngay-lam-nghe/releases/1.7.9-20261004235313`.
- Build: `1.7.9+41cb0c05c8b9`.
- Bản trước: `/opt/mot-ngay-lam-nghe/releases/1.7.8-20261004231648`, được giữ để quay lại ứng dụng nếu cần. Không khôi phục database cũ.
- Gói: `output/release-179/mnl-1.7.9.zip`, SHA256 `c98356561ab40cc47c5339d961ee3577a425848487a160d565dfbb8688a06fc4`; server khớp hash.
- 22 file chủ đích chép lên nguồn sạch 1.7.8; các file khác giữ nguyên byte. Không đổi schema 22, quy tắc nhiệm vụ hay dữ liệu định dạng save.

## Thay đổi

- Dựng offer chỉ sao chép nghề cần dùng và journey; bỏ tải save thừa khi xác thực/hỏi đơn, dùng chung before-state trong transaction và dùng public view/revision đã commit khi settlement.
- Hỏi đơn nền 30 giây khi rỗng, 5 giây khi có đơn đang xử lý; giảm hỏi danh sách tiệm và tạm dừng owner polling ở tab ẩn/màn ghé tiệm.
- Khách ghé ở trong bố cục, không che Làm tiếp/Hoàn thành. Điện thoại có hàng riêng, giữ nguyên phiếu công việc.
- Danh sách bạn bè có biểu tượng chat và ghé tiệm 44×44 cạnh nhau, không còn nút ghé tiệm rộng một hàng.
- Có gì mới 1.7.9 có 3 mục tương ứng, có bản dịch tiếng Anh. Chưa thiết kế lại toàn bộ màn ghé tiệm; không bao gồm lỗi vốn của cơ chế thuê người chơi hay nghề mới.

## Kiểm chứng

- 137 kiểm tra backend/HTTP trên nguồn đóng gói đều qua; 35 kiểm tra chat/reply/owner UI, bộ visit/quay UI, Có gì mới và JS syntax đều qua.
- 40.800 mẫu nhiệm vụ, 41 nghề, ngày 1–40 tương thích 1.7.8.
- ZIP giải nén: 1.213 hash source/asset khớp; khởi động trên PostgreSQL riêng, tạo nhân vật, mở nghề/ngày, replay command và export save thành công.
- 6 mẫu HTTPS health đúng build, 15 asset production đúng byte ZIP, Có gì mới đúng 1.7.9/3 mục. Kết quả tại `output/release-179/production-check.json`.
- Game và mnl-live active; live health bật chat/home/visits, cut=0 tại lần kiểm tra. Log sau hoàn tất không có ERROR/Traceback/deadlock/Internal error/Database error trong mẫu đọc. Pool ghi nhận waited=0, timed out=0.
- Trình duyệt production: đã mở Có gì mới và quan sát 3 mục, mở danh sách bạn bè và quan sát nút chat/ghé tiệm nhỏ đồng đều. Tab kiểm tra riêng đã đóng; không sửa tin nhắn hay làm nhiệm vụ của người chơi.
- PostgreSQL thử nghiệm local dừng sau kiểm tra. Không commit/push.

## Số đo production trước/sau

Trước: cửa sổ 120 giây kết thúc 23:51:49. Sau: 111 giây từ 23:54:20 tới 23:56:10. Đây là quan sát lưu lượng thật trong mẫu ngắn, không phải benchmark tải cố định. Đơn vị giây.

| API | n trước/sau | p50 trước → sau | p95 trước → sau |
| --- | ---: | ---: | ---: |
| POST /api/command | 1653 / 1866 | 0.472 → 0.166 | 1.988 → 0.492 |
| GET /api/work-visits/orders | 1243 / 913 | 0.435 → 0.005 | 1.511 → 0.032 |
| GET /api/work-visits/places | 233 / 178 | 0.509 → 0.064 | 2.175 → 0.217 |
| GET /api/work-visits/place | 14 / 28 | 1.719 → 0.088 | 3.401 → 0.249 |
| GET /api/state | 260 / 250 | 0.501 → 0.192 | 2.826 → 0.598 |
| GET /api/bootstrap | 23 / 28 | 0.376 → 0.313 | 3.208 → 2.684 |

Không có HTTP 5xx trong mẫu sau; có 17 request 499 (client đóng kết nối), 56 request 403, 3 request 400, 7 request 409. Bootstrap vẫn có outlier 4.56 giây và AI vẫn có thời gian chờ nhà cung cấp; không tuyên bố mọi API đã hết chậm.

Aggregate server: `/tmp/mnl179-before.json`, `/tmp/mnl179-after.json`; log deploy `/tmp/mnl179-deploy.log` và `/var/log/mnl-rolling-release.log`.
