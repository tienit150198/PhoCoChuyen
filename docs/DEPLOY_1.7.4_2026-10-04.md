# Phát hành 1.7.4 — 04/10/2026

Rolling deploy hoàn tất 17:49:02 UTC+7, build `1.7.4+8f6ac3ee24ae` tại `/opt/mot-ngay-lam-nghe/releases/1.7.4-20261004174805`.

Bổ sung thông báo Có gì mới gồm sáu mục về các sửa vừa phát hành. Người chơi quay lại thấy bảng một lần vào lúc nghỉ phù hợp; mở lại từ Cài đặt → Cách chơi → Có gì mới. Không thêm nghề mới.

74 kiểm tra đích qua; 40.800 nhiệm vụ tương thích; ZIP giải nén chạy thử trên PostgreSQL riêng thành công. Popup tự hiện trong fixture dùng module thật; file thông báo HTTPS khớp hash với gói đã kiểm tra. Game/live active, bridge inactive; 12 mẫu health HTTP 200, không có lỗi request. Schema giữ nguyên 18; không cần migration mới.

Gói: `output/release-174/mnl-1.7.4.zip`; SHA256 `3ab27026ff87a72228e3d29606576326d85db0317b4e92e105bb0f7d6cb84b50`. Ghi chú vận hành riêng theo yêu cầu chủ dự án và bằng chứng ở `output/release-174/internal-notes.json`. Có thể rolling về 1.7.3 nếu cần; không tự rollback thấp hơn do điều kiện validation giao dịch lớn ghi trong báo cáo 1.7.3.
