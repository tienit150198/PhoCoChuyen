# Deploy cân bằng hội chợ — 20:12:33 ngày 05/10/2026 (UTC+7)

Đã đưa lên production theo yêu cầu deploy của chủ game. Không đổi thông báo “Có gì mới”.

- Game: `/opt/mot-ngay-lam-nghe/releases/1.7.15-fair-rotation-final-20261005200954`.
- Public version: `1.7.15+28a76cd1c705`; engine build: `574e05c362d35ab74e25`.
- Game PID 3034039, 8 worker. Live PID 3032609 dùng reader tương thích; không restart live ở bước bật logic mới.
- Rollback tương thích: `/opt/mot-ngay-lam-nghe/releases/1.7.15-fair-rotation-compat-20261005200954`. Không rollback thẳng về bản trước chưa biết `wealth_check_at`.
- ZIP SHA-256: `918fd487a53e79205fdcbe1ce9496b086e47ecfba6d94ea53d7f884203336c99`.

## Nội dung

Một trò may rủi ưu đãi/30 phút thực, 70–50% theo mức cược; còn lại 55–30%. Lặp liên tục hạ về 40%, không tăng ngược mức thấp hơn. Vé cào giảm trọng số giải lớn. Phóng dao/ô ăn quan giữ kỹ năng; ván đã mở giữ kết quả/xác suất đã chốt.

Lãi ròng hội chợ ngày Việt Nam vượt 50.000 xu: kiểm tra khi hoàn thành ván cược, tối đa một lần/30 phút, xác suất bắt 70%. Thu 30% ví sau ván, làm tròn xuống, có biên nhận và Sổ ví. Khoản thu hạ lãi ròng và điểm tiền hội chợ. Không thu khi tải trang/offline hoặc chơi trò kỹ năng/miễn phí; không thu hai lần khi retry request.

## Kiểm chứng

- Bộ fair trên package: 177 bài; 176 pass, 1 kiểm tra bản 1.5.x thiếu fixture ở cây package. Chạy lại bài này với `MNL_PREV_TREE` đã pass.
- 18 kiểm tra tiền, phạt và kinh tế pass; 8 kiểm tra knife skill pass; 64 kiểm tra JS về tương tác/animation/biên nhận pass.
- Roundtrip save final → compatible reader/write → final pass; reader cũ từ chối metadata mới đúng như dự kiến, xác nhận cần rollout hai bước.
- Xác minh SHA-256 của 1.338 file tại release và 9 tài nguyên qua HTTPS; admin và nội dung thông báo giữ nguyên.
- Trong cửa sổ triển khai 3.507 API request: 0 HTTP 5xx, 0 traceback trong log game/bridge/live. Health game và live đều thành công, bridge đã dừng.

Hồ sơ JSON, ZIP và log: `output/release-1715-fair-rotation/`. Thiết kế: `docs/FAIR_ROTATION_2026-10-05.md`.
