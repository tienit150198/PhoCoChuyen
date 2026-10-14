# Phát hành 2.4.2 — thông báo Có gì mới tổng hợp

Đã phát hành lúc 10:04:11 UTC+7 ngày 14/10/2026 tại https://phocochuyen.io.vn.

- Source: `6b9cd04884becc1758845b0bade226d1a8cfefa4`; base cho lần phát hành tiếp theo.
- Release: `/opt/mot-ngay-lam-nghe/releases/2.4.2-20261014100307`.
- Build: `2.4.2+e6c62c2481ea`.
- ZIP: `C:/Users/ADMIN/AppData/Local/Temp/mnl-scale-20261014/mnl-2.4.2.zip`, 104.521.756 byte.
- SHA-256: `8bac232eb7c8b091f468c1130a565f1ab19c9a6aa5bb5c73d60260cca94ca639`.

## Nội dung và nguyên nhân

Game đã lên 2.4.1 nhưng bảng thông báo gần nhất vẫn là 2.0.5. Những nhân vật đã xem thông báo đó không còn bản tin mới để tự mở. Theo yêu cầu của chủ game, bổ sung một bản tin 2.4.2 gồm 17 mục tiếng Việt và bản dịch English, tổng hợp các thay đổi từ 2.0.6 đến 2.4.1: nghề mới, chứng chỉ, thăng tiến và thi đua, chùa và thẻ chúc, không gian đi bộ, chat/reaction, mở rộng chuỗi, chuyên môn nghề, sức chứa/nhập hàng, quyết toán, chợ đen và lịch cưới.

Thông báo tự hiện một lần cho nhân vật cũ sau khi giao diện ở trạng thái phù hợp; vẫn đợi hướng dẫn, câu hỏi chọn giao diện và các luồng đang mở. Nhân vật mới vẫn đánh dấu đã đọc âm thầm. Có thể mở lại ở Cài đặt → Cách chơi → Xem các cập nhật mới. Không đặt lại trạng thái đã xem và không sửa công thức gameplay.

## Kiểm chứng

- Hồi quy đã tái hiện lỗi trước sửa: bản tin mới nhất 2.0.5 khiến người đã xem 2.0.5 hoặc 2.4.1 đều không được báo. Sau sửa, Node kiểm tra các mốc đã xem 2.0.5/2.3.1/2.4.0/2.4.1 đều nhận thông báo mới, đã xem 2.4.2 thì không tự hiện lại.
- 11 kiểm thử thông báo đạt, bao gồm dữ liệu, độ dài, thứ tự, đồng bộ Python/JS và lưu trạng thái đã xem.
- Browser HTTP/PostgreSQL thực ở 390 và 1280px trên source và chính gói đã nén: tự mở thông báo sau câu hỏi giao diện, đủ 17 mục, nội dung cuộn được, không tràn ngang; đóng và tải lại không tự hiện, mở lại qua Cài đặt thành công; không pageerror.
- Gói được xây từ ZIP 2.4.1 chính xác; 2.424 hash khớp. Kiểm tra HTTP từ bản giải nén đạt tạo nhân vật/mở ca/replay/export schema 4 với 54 nghề.
- 53.280 mẫu nhiệm vụ khớp bản 2.4.1 trên 54 nghề, ngày 1–40, slot 0–11, desk và classic.
- Rolling exit 0; game/live active, bridge inactive. 1.666 hash runtime đúng; 758 file tests bị installer bỏ có chủ đích. Hai asset thông báo/bản dịch qua HTTPS khớp manifest. Health đúng 2.4.2/54 nghề.
- Browser public 390/1280px trả HTTP 200, app hiện và không pageerror. Không tạo nhân vật trên production để kiểm thử thông báo; luồng nhân vật cũ được kiểm bằng PostgreSQL riêng trên gói phát hành.
- Journal game/live từ 10:03:00 không có Traceback/CRITICAL/ModuleNotFoundError/No space left/ERROR. Còn 3.088.789.504 byte trống sau deploy.

MANIFEST.json lấy từ release đang chạy. Giữ các release cũ và DB; scratch PostgreSQL 55433 đã dừng, HTTP kiểm thử tự dừng. Bằng chứng ở thư mục C temp nêu trên và output/playwright/whats-new trong source/gói giải nén. Không đổi schema DB; nếu cần quay mã, bản trước là 2.4.1 và không cần khôi phục DB.
