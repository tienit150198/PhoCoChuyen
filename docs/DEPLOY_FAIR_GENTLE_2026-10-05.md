# Deploy hội chợ dễ chơi hơn — 05/10/2026

Hoàn tất **18:22:26 (UTC+7)** theo yêu cầu “ok deploy”. Không thêm thông báo game.

- Release cuối: `/opt/mot-ngay-lam-nghe/releases/1.7.15-fair-gentle-final-20261005181749`.
- Engine build: `0455f5384204b25b154c`.
- Gói SHA-256: `144b193f8ecff6dd04b3c8c81d87cd9df51528fbb4eab2b1964697f5123c43bc`.
- Bản giao diện vẫn là `1.7.15+d295b3ef724e`: backend thay đổi, toàn bộ tài nguyên frontend giữ nguyên.
- Nền phát hành là bản mới nhất `1.7.15-admin-password-reset-20261005170913`, giữ nguyên sửa reset mật khẩu và hội chợ đã mượt. Không đóng gói các thay đổi giao diện khác đang làm trong checkout.

## Thay đổi

Các trò may rủi (gồm vé cào, lô tô/Kinh, bầu cua, xóc đĩa, phóng dao và ném vòng) dùng mức cơ bản 70%, giảm theo chuỗi/lãi ngày nhưng không dưới 55%. Phóng dao mới dùng hệ số 135 thay cho 150: tốc độ bia giảm 10%, màn đầu 10 dao thay 11. Ván đang chơi giữ xác suất và lịch đã lưu. Ô ăn quan/ông Hai, bảng trả thưởng và tỷ lệ truy bắt giữ nguyên.

Chỉ ba module runtime thay đổi: `game/fair.py`, `game/fair_knife.py`, `game/fair_scratch.py`.

## Kiểm chứng

- Bộ 159 test source đạt. Trên gói thực tế: 158 đạt, 1 test save 1.5.4 thiếu đường dẫn nên skip; chạy riêng test đó với `MNL_PREV_TREE` đúng đã đạt. Hai kiểm tra sinh state mới/đọc bằng bản trung gian cũng đạt.
- 1.332 entry trong manifest đúng SHA; server từ ZIP chạy với PostgreSQL riêng, tạo hồ sơ, mở ngày, export save và idempotency qua HTTP đạt.
- 40.800 nhiệm vụ, 41 nghề, ngày 1–40 tương thích với bản admin hiện đang chạy.
- Trên production: game và live khỏe, bridge dừng, mọi game worker ở release cuối; live ở release tương thích. Xác minh cấu hình thực tế 70%/55%, hệ số 135, lịch màn đầu 10 dao.
- HTTPS phục vụ đúng hash của chín tài nguyên hội chợ, admin, app và thông báo; cache immutable; không có probe local.
- Cửa sổ chuyển bản: **4.016 request, 0 HTTP 5xx, 0 traceback trong journal các dịch vụ**. Không dùng số liệu cửa sổ chuyển bản để khẳng định cải thiện tốc độ.

## Hai bước triển khai và rollback

Trước tiên triển khai bản đọc tương thích cho game/live để chấp nhận `p <= 700` và hệ số 135, vẫn sinh ván theo mức cũ. Sau đó mới chuyển game sang mức mới. Chat được khởi động lại một lần ở bước đầu, giữ kết nối ở bước sau.

Kiểm tra readiness ban đầu gọi health chat ngay khi systemd báo active, sớm hơn lúc socket sẵn sàng; script dừng an toàn ở bản trung gian. Đã thêm chờ readiness có giới hạn, xác minh mọi writer rồi tiếp tục. Traceback của lần kiểm tra này nằm trong log deploy, không phải lỗi game. Lượt triển khai cuối exit code 0.

**Rollback về bản tương thích:** `/opt/mot-ngay-lam-nghe/releases/1.7.15-fair-gentle-compat-20261005181749`, build `ad3bc5959a4544f3ee66`. Không rollback trực tiếp về bản admin trước đó sau khi đã tạo ván mới vì validator cũ không nhận mức 700/hệ số 135. Giữ release tương thích vì live đang chạy từ đó.

Bằng chứng: `output/release-1715-fair-gentle/` gồm package, prepared, deployed, packaged-tests, previous-save-test, task-compat, package-verified, production-https, production-api-window và deploy.log. Các script operator trong `output/lag-9core-20261005/*fair_gentle*`.
