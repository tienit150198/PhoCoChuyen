# Phố Có Chuyện 2.0.0 — kết quả chuẩn bị phát hành

Ngày 11/10/2026. Trạng thái: hoàn thiện mã nguồn và kiểm tra local; **chưa triển khai, chưa thông báo, chưa kích hoạt hai ngày vàng**. Production được đọc qua `/api/health` vẫn là 1.9.48. Kết nối SSH trên máy phát triển hiện bị từ chối xác thực; cần khôi phục kết nối deploy đã được chủ game cho phép.

## Nội dung

- Phaser 2.5D, 50 ngoại thất và hồ sơ nội thất theo nghề; bản đồ/camera/nước, khu dân cư và nhà 3D, avatar và phụ kiện dùng chung dữ liệu với giao diện cũ. Các báo cáo nghiệm thu chi tiết nằm trong `docs/superpowers/plans/2026-10-11-*-verification.md`.
- Cài đặt → Giao diện → **Giao diện mới**. Bật/tắt lưu theo tài khoản rồi tải lại. Người mới mặc định bật và có lời mời trở lại giao diện cũ một lần. Lựa chọn lưu trong `journey.interface`, tránh thêm khóa vào settings mà máy chủ cũ không hiểu.
- Góp ý gửi tối đa 3 ảnh PNG/JPEG/WebP, 2 MiB mỗi ảnh. Ảnh chuẩn hóa lưu PostgreSQL, URL chỉ dành cho chủ ảnh và quản trị viên. Sửa nội dung, trả lời, xử lý góp ý và dọn tài khoản khách tự động không xóa ảnh. Không có TTL; chỉ xóa khi có yêu cầu riêng của chủ game hoặc quy trình xóa dữ liệu tài khoản được cho phép.
- Giới hạn giải mã 12,6 MP, một lượt giải mã mỗi worker; bận trả 503 và giữ bản nháp. Peak RSS đo local với 3 ảnh lớn lần lượt: PNG 116,5 MiB, JPEG 118,1 MiB, WebP 236,7 MiB. Đây là phép đo bộ giải mã, không phải cam kết bộ nhớ toàn máy chủ.
- Hai ngày vàng: cửa sổ 48 giờ bất biến lưu trong PostgreSQL, chỉ bắt đầu bằng lệnh vận hành sau khi triển khai đạt. Áp dụng Chiếu trong, lô tô và vé cào. Trò kỹ năng, xúc xắc chung và đua chó giữ luật hiện có. Thông báo công khai không ghi xác suất.
- Danh mục nâng cấp chuyển sang tải sau, giảm dữ liệu core từ 980.345 xuống 695.254 byte (39,92% toàn danh mục). Phiên bản catalogue 2.0.0 ngăn trộn cache của hai cách chia dữ liệu. Màn trang trí chờ đủ danh mục trước khi mở.

## Kiểm tra đã thực hiện

| Nhóm | Kết quả |
|---|---|
| Build Phaser, build nhà 3D, TypeScript | Đạt |
| Nghề/ngoại thất/nội thất/biển hiệu; bản đồ/nước/camera; khu nhà/treasure frontend | Các script `test:career-architecture`, `test:isometric`, `test:living-districts` đạt |
| JavaScript nguồn | 345/345 cú pháp và Safari 15 đạt |
| JavaScript đã nén | 344/344 Safari 15 đạt; nhận diện probe RegExp có catch, vẫn chặn literal/callback không an toàn |
| Backend bị ảnh hưởng | 35 kiểm tra core và 19 kiểm tra HTTP/static/catalogue đạt; 11 kiểm tra public view đạt |
| Góp ý | 31 kiểm tra DB/HTTP, 2 kiểm tra giữ ảnh/giới hạn request, 6 kiểm tra tài nguyên giải mã, 2 kiểm tra schema catalog đạt; frontend đạt |
| Hai ngày vàng | 17 kiểm tra; lấy mẫu 30.000 lần mỗi trò; khởi động lại, hết hạn, tranh chấp và kích hoạt lặp đạt |
| Thông báo | 5 kiểm tra PostgreSQL; khóa giao dịch, chống gửi trùng, đọc lại thời hạn sau khi chờ khóa, không ghi đè ghim mới khi chạy lại |
| Rollback | Hai bộ kiểm tra lịch sử, bốn revision đạt; 8 avatar và 8 phụ kiện mới giữ sở hữu/màu qua bộ đọc 1.9.48 |
| Tương thích nhiệm vụ | 49.440 dòng của 50 nghề, ngày 1–40, hai kiểu nhiệm vụ khớp source production `43d6cc12` |

Review chéo độc lập đã sửa lỗi save khi quay lui, giới hạn bộ nhớ ảnh, khai báo bốn bảng rương trong catalog, ngân sách catalogue đầu trang và điều kiện thông báo sau khi chờ khóa.

## Trình duyệt

Dùng tài khoản khách kiểm thử riêng, PostgreSQL/schema riêng, HTTP `localhost:18893` và WebSocket `localhost:18894`. Đã xác nhận viewport DOM 320×740, 390×844, 768×1024 và desktop 1280 px. Không thấy tràn ngang trong các màn đã kiểm tra.

- Người mới thấy lời mời; giữ giao diện mới rồi tải lại không hỏi lặp.
- Tắt giao diện qua settings mở bản cũ; bật lại mở Phaser. Ví 460 xu, quỹ 320 xu, nghề trà sữa và ngày chơi giữ nguyên.
- Gửi thật ba ảnh fixture từ mobile; xem lại cả ba ảnh sau đổi mode và khởi động lại HTTP server. Nút chọn ảnh hiển thị tiếng Việt.
- Mở/đóng settings, góp ý, vào/ra nơi làm việc; kiểm tra tablet và mobile. Console ở lượt kiểm tra cuối không có error.
- Ảnh và log ở `output/release-2.0-local/` (không đưa vào source/gói).

Đây là kiểm tra Chromium với kích thước mô phỏng, không thay thế thử trên phần cứng iPhone/Android/iPad thật hoặc kiểm tra tải 1.000 CCU. Một tab tự động hóa bị treo; tab mới cùng tài khoản hoạt động lại. Chưa suy ra FPS từ phiên kiểm tra này.

## Baseline và đóng gói

Source ghép main `bafd85ea` (1.9.48); safety stash vẫn được giữ. Dựng lại baseline từ Git và manifest `ff76378b`: 1.937 mục khớp SHA-256, gồm 1.507 file nguyên bản và 430 file tái nén chính xác bằng esbuild 0.28.2. `release_from_live.py --check-base` đạt. Đây là baseline tái lập theo manifest, không phải bản sao lấy trực tiếp từ máy chủ.

Manifest baseline SHA-256: `8405660b1bee772f392f2b1882e5d1d5f1dc77b0985c4b4b54356ca53c4baf29`. Phải đối chiếu manifest thực trên production trước khi rollout. Không đóng gói output/tmp, thông tin xác thực, bản lưu hoặc ghi chú khôi phục mật khẩu.

Source ứng viên `0c7db8d6eb9e4c51c2a9ac812619eb12b556b802` đã push lên main. Gói `output/release-2.0-local/mnl-2.0.0.zip`: **103.213.669 byte**, SHA-256 `892c52b5815d642a7e0a5be45f58c45447e332cfac1eaad51b05188883d99fe0`; 2.181 file kể cả manifest, 329 mục thay đổi, không xóa mục nào. Root `MANIFEST.json` trong Git vẫn đại diện production 1.9.48 cho đến khi thực sự deploy.

`verify_package.py` đạt: toàn bộ 2.180 mã băm source/asset khớp, server giải nén khởi động bằng PostgreSQL riêng, phục vụ asset, tạo hồ sơ/chọn nghề/mở ngày làm, từ chối nghề bị khóa, replay request không áp dụng hai lần và export save 50 nghề. **345/345 JavaScript trong chính gói ZIP** qua gate Safari 15. Báo cáo máy đọc được nằm ở `output/release-2.0-local/package-verify.json`; chưa có smoke production 2.0 vì SSH chưa truy cập được.

## Bổ sung hiệu năng ngày 11/10/2026

Sau ứng viên `0c7db8d6`, đã bổ sung sửa vòng vẽ nền, cache che khuất/LOD, cập nhật live và lối vào menu ở cả ba bố cục. Bằng chứng và phạm vi kiểm chứng ở `docs/qa/performance-2026-10-11.md`; danh mục 50 nghề/66 tiện ích ở `docs/qa/isometric-feature-parity.md`. Gói ZIP mang SHA-256 ở phần trên là **ứng viên trước các sửa hiệu năng này**; không dùng nó thay cho ứng viên mới.

## Các bước còn lại trên production

1. Khôi phục SSH; đọc health, current release và manifest; nếu production đã đổi thì cập nhật baseline và kiểm tra tương thích lại.
2. Backup PostgreSQL và xác minh mục lục; giữ toàn bộ release cũ. Kiểm tra dependency **Pillow >=12.1.1,<13** trong đúng Python của service trước khi bật bridge; script rolling hiện không tự cài dependency.
3. Kiểm tra nginx cho phép body 16m hiện có để ba ảnh không bị chặn; không tăng giới hạn các endpoint game. Xác minh `LIVE_TOWN=1`, `LIVE_TOWN_TREASURE=1`, `LIVE_HOME=1`, `LIVE_VISITS=1` theo cấu hình service dùng thật, không in secret.
4. Rolling release theo `docs/DEPLOY_ROLLING.md`, `KEEP=999` để không dọn release cũ; schema 38 chỉ thêm cấu trúc cần thiết. Theo dõi health game/live và các API/static của bản mới.
5. Kiểm tra trên production hai mode, lưu lựa chọn, góp ý/ảnh được bảo vệ, bản đồ/nghề/nhà và live. Chưa gửi thông báo nếu có lỗi nghiêm trọng.
6. Trong môi trường service đúng DB/namespace: `python scripts/activate_fair_golden_days.py --activate`. Kiểm tra starts/ends đúng 48 giờ; chạy lại không kéo dài.
7. `python scripts/publish_major_release.py` xem trạng thái; sau kiểm tra cuối chạy với `--publish`. Xác minh một tin ghim công khai, đúng thời hạn Việt Nam, có hướng dẫn quay về giao diện cũ. Chạy lại không tạo trùng hoặc ghi đè tin ghim mới.

Nội dung thông báo đã chuẩn bị trong `scripts/publish_major_release.py`: giao diện 2.5D, 50 nơi làm nghề, avatar/phụ kiện, nhà 3D; hướng dẫn settings; góp ý ba ảnh; “2 ngày vàng, tăng tỷ lệ thắng cược Chợ Đen” cùng ba trò áp dụng và giờ kết thúc thực tế.
