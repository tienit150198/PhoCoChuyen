# Hotfix Chợ đen 2.0.2.1 — 11/10/2026

Đã triển khai theo yêu cầu chủ game, **không công bố**. Rolling hoàn tất 13:12:44 UTC+7.

- Release: `/opt/mot-ngay-lam-nghe/releases/2.0.2.1-20261011131139`.
- Health: `2.0.2.1`, build `2.0.2.1+a68306fb053f`.
- Source bản vá: `b7074860`; source phiên bản: `b497aae0`.
- ZIP: `mnl-2.0.2.1-black-market.zip`, 103.411.294 byte, SHA-256 `f7fd74e9617e47b7fe23dfb39db48ea601ef65f4a6459516b6dce3b9b47f2141`. File trên server đã đối chiếu mã băm trước triển khai.
- Dựng từ ZIP 2.0.2 đã xác minh và manifest production SHA-256 `f44ae534590da43821ff8b57ff2c6a2b272217c64e04340425542bf21a25cec5`.
- Chỉ sáu file thay đổi: hai module tỷ lệ, ba file phiên bản và kiểm thử mới. Toàn bộ file thông báo giữ nguyên byte; không chạy tác vụ publish, không sửa bản lưu người chơi hoặc schema.

## Hành vi đã kiểm trực tiếp trên server

Trong cửa sổ Hai ngày vàng, tiền cược **mỗi ván** dưới 300.000 xu dùng tỷ lệ quay thắng 70%; từ 300.000 xu dùng 40%. Đã xác minh 299.000 / 299.999 / 300.000 / 300.001 / 1.000.000 xu. Không tính theo ví, lời/lỗ hay tổng cược. Xóc đĩa là trò hưởng sự kiện hiện cho cược tới mức này.

Mốc sự kiện giữ nguyên: bắt đầu `1791689983`, kết thúc `1791862783`; kiểm bằng giao dịch PostgreSQL chỉ đọc. Không tái kích hoạt sự kiện. Quy tắc thường tự trở lại khi hết thời gian.

## Xác minh phát hành

- 50 kiểm thử trên gói sẽ triển khai: đạt. Rà soát độc lập thêm 15 kiểm thử tỷ lệ/sự kiện: đạt.
- Gate tương thích bản lưu: 49.440 mẫu nhiệm vụ của 50 nghề, ngày 1–40, slot 0–11, desk/classic: đạt.
- 74 mẫu health công khai trong lúc tải/chuyển bản, không mẫu lỗi; thấy chuyển 2.0.2 → 2.0.2.1. Đây là lấy mẫu, không khẳng định mọi request đều không lỗi.
- HTTP và live active, PID/cwd cùng đúng release mới; health nội bộ, HTTPS và live đạt. Live health cần đợi khởi động xong sau rolling trước khi đạt.
- 1.530 file runtime khớp manifest; thư mục tests được quy trình triển khai loại khỏi runtime.
- Không thấy Traceback, CRITICAL, ModuleNotFoundError trong tối đa 500 dòng log mỗi dịch vụ từ lúc khởi động mới.
- Giữ release cũ với `KEEP=999`, bridge `8767`, pool 1/max 3, MemoryMax 3G. Kiểm tra release và manifest cũ ngay trước rolling để tránh ghi đè bản khác.

## Tích hợp với bản tiếp theo

Trong lúc rolling, `origin/main` nhận commit `45c94be5` chuẩn bị 2.0.3 (giảm phạt/trộm). Chưa đưa phần đó lên trong hotfix này. Khi tích hợp mã nguồn, giữ đầy đủ thay đổi 2.0.3 và thêm quy tắc 300k; **không ghi đè `game/fair.py` bằng bản 2.0.2.1 nguyên file**.

Quay lui mã nếu cần: rolling `--to /opt/mot-ngay-lam-nghe/releases/2.0.2-20261011120834`, nhưng thao tác đó khôi phục tỷ lệ 70% cho cược lớn; chỉ dùng khi có sự cố. Không cần phục hồi database.
