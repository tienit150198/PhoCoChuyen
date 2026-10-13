# Phát hành 2.3.1

Đã phát hành lúc 03:32:57 UTC+7 ngày 14/10/2026 tại https://phocochuyen.io.vn.

- Source: `0a5e3b0537d78d4ca6ac7019c032cc397539b503`; dùng làm base lần phát hành tiếp theo.
- Release: `/opt/mot-ngay-lam-nghe/releases/2.3.1-20261014033154`.
- Build: `2.3.1+002f93d280be`.
- ZIP: `output/deploy-20261014/mnl-2.3.1.zip`, 104.220.087 byte.
- SHA-256: `ab616f6d485cb87b39aed5182dcc84aa729def2325e7181621d1d05673a4ae6d`.

Nội dung: chat/reaction và tương tác 2.5D; hạn mức nhập trả phí theo nghề; lịch sử hôn nhân; chặn lịch/hoạt động đám cưới đã hủy; điều chỉnh chợ đen với đúng một lượt đầu 55%, sau đó giảm dần theo luật đã thống nhất. Bản thiết kế quy mô 54 nghề có trong source nhưng chưa có runtime trong 2.3.1.

Kiểm chứng: 53.280 mẫu nhiệm vụ/54 nghề tương thích với live 2.3.0; bốn bộ Node order/social/lawyer/marriage đạt; 68 kiểm thử Python trọng tâm đạt trên PostgreSQL riêng. Gói giải nén có 2.374 hash đúng và kiểm thử HTTP tạo nhân vật/mở ca/chống replay/xuất bản lưu đạt.

Rolling exit 0. Game và mnl-live active, bridge inactive; HTTPS health đúng phiên bản/build/54 nghề. Toàn bộ 1.635 file runtime đúng SHA; 739 file tests bị installer loại có chủ đích; không có file sai hash. Asset isometric-town và marriage qua HTTPS đúng gói. Browser thực ở 390px/1280px trả 200, có nội dung và không có pageerror. Journal game/live từ lúc bắt đầu rolling không có lỗi khớp Traceback/CRITICAL/ModuleNotFoundError/No space left/ERROR. Sau deploy còn 5.084.377.088 byte trống.

Root MANIFEST.json khớp bản đang chạy. Bằng chứng chi tiết lưu trong thư mục test tạm `C:/Users/ADMIN/AppData/Local/Temp/mnl-scale-20261014` và gói tại output. Giữ các release cũ và DB. Ưu tiên sửa tiến; không hạ trực tiếp về 2.3.0 sau khi người chơi đã mua hạn mức nhập vượt giới hạn cũ, không khôi phục DB để quay lui mã.
