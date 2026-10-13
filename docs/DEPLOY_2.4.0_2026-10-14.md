# Phát hành 2.4.0 — mở rộng quy mô nghề

Đã phát hành lúc 04:37:45 UTC+7 ngày 14/10/2026 tại https://phocochuyen.io.vn, sau khi phát hành bản hiện tại 2.3.1 lúc 03:32:57 cùng ngày theo yêu cầu.

- Source: `23fb59ff53d0bb35e7fef35347c505645e016708`; dùng làm base lần phát hành tiếp theo.
- Release: `/opt/mot-ngay-lam-nghe/releases/2.4.0-20261014043642`.
- Build: `2.4.0+d4ae9b9b6df9`.
- ZIP: `output/deploy-20261014/mnl-2.4.0.zip`, 104.366.459 byte.
- SHA-256: `187a75570bc16aea152496fa1f9b0695e0119e828156a0958c0776da343ea294`.

## Nội dung đang chạy

54 nghề có 8 bậc quy mô riêng. Tạp hóa đi từ tạp hóa mở rộng → minimart → siêu thị mini → siêu thị khu phố → cụm ba siêu thị → chuỗi năm điểm → chuỗi khu vực → hệ thống bán lẻ. Phí tăng tuần tự, tổng 402,3 triệu xu cho tám bậc tạp hóa; tối đa 12 điểm và 50 vị trí tính toàn mạng. Các nhóm nghề dùng hệ số, nhân sự, tài nguyên và tình huống riêng; công vụ là phạm vi điều phối, chùa là công quả.

Vào nghề → Thăng tiến → Mở rộng nghề. Mỗi bậc kiểm tra việc sạch, ngày thực đủ chuẩn, chứng chỉ và quỹ nghề. Có tuyển người, gán tài nguyên, mở điểm, nhập/nhận/chuyển vật tư, hợp đồng nhiều bước, xử lý phát sinh, nghiệm thu và biên nhận tiền. Kho và hạn mức nhập mỗi lần vẫn là nâng cấp trả phí độc lập; điểm phụ dùng chung quyền số quầy. Suất hợp đồng dùng chung tài khoản: ban đầu 1, thêm 4/ngày thực, tích tối đa 12.

Cơ sở có nội thất đi lại và tương tác, trạm/NPC theo bố trí, quyền riêng tư/công khai. Hai người cùng cơ sở trò chuyện, xem nhau và thả reaction; lời nói/reaction hiện trên đầu, đi theo vị trí, tự ẩn sau 8 giây và xóa khi rời hoặc mất kết nối.

## Kiểm chứng

- 489 kiểm thử lõi/mở rộng đạt, gồm 432 luồng engine cho đủ nghề × bậc; kiểm tra hạch toán, lịch sử giá vốn, quota, tiến trình, giữ vật tư và Store chống replay.
- 292 hồi quy unittest đạt (1 bỏ qua có chủ đích). Bộ tiền/kho/chứng chỉ/thi đua/quầy bổ sung phát hiện thiếu mapping chứng chỉ luật sư/bưu điện và một timeout HTTP local; sửa mapping và chạy lại 59 ca liên quan đạt. Chi tiết trong báo cáo kiểm chứng.
- 53.280 mẫu nhiệm vụ khớp Release A. Review spec và quality độc lập; sửa tranh chấp admission ở phòng đầy bằng ba kiểm thử hồi quy trước phát hành.
- Gói mới giải nén có 2.403 hash đúng; HTTP tạo nhân vật/mở ca/replay/xuất bản lưu đạt. Trên chính gói nén: browser Chromium hai tài khoản 390px/1280px và PostgreSQL Store đạt cả hai bài tích hợp, gồm speech/reaction, TTL, reconnect và thu hồi quyền.
- Rolling exit 0; game và mnl-live active, bridge inactive. HTTPS health đúng 2.4.0/54 nghề; bảy asset thay đổi đúng SHA qua HTTPS. Toàn bộ 1.650 file runtime đúng hash; 753 file tests bị installer bỏ có chủ đích, không có file runtime thiếu/sai.
- Browser public 390px/1280px trả 200, có nội dung, không pageerror. Journal game/live từ 04:36:40 không có dòng khớp Traceback/CRITICAL/ModuleNotFoundError/No space left/ERROR. Sau deploy còn 5.347.086.336 byte trống.

MANIFEST.json lấy từ release đang chạy. Giữ release cũ và DB; cập nhật guard của helper tắt chứng chỉ lên 2.4.0, có bản sao trước sửa và kiểm tra bash -n; không chạy helper. Đã dừng HTTP test 8876 cùng hai PostgreSQL thử nghiệm local 55432/55433. Bằng chứng chi tiết ở `C:/Users/ADMIN/AppData/Local/Temp/mnl-scale-20261014`.

## Giới hạn và khôi phục

Một dòng vật tư lõi được triển khai cho mỗi nghề; chưa có 540 gói công thức/mẫu hàng từng đề xuất. Nhãn chính có tiếng Anh, tình huống mới có fallback tiếng Việt. Không tuyên bố đã đo thời lượng 10–20 phút/ca. Tiến trình ngày thực được kiểm thử bằng đồng hồ/fixture, không giả đã chơi 240 ngày.

Bản trước chưa hiểu hợp đồng đang giữ vốn và tài nguyên, nên ưu tiên bản sửa tiến tương thích 2.4.x. Không dùng gợi ý rollback tự động cuối rolling log để hạ mù về 2.3.1; không khôi phục DB để quay lại mã.
