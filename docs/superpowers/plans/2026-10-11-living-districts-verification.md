# Khu dân cư 3D và hoạt động trên đảo — nghiệm thu local

Ngày 11/10/2026. Mã nguồn tại `wt-feedback-0410`, nhánh `main`. Chưa deploy, chưa gửi thông báo phát hành. Không thay số dư hoặc nhà đang sở hữu của tài khoản preview để tạo ảnh minh họa.

## Nội dung đã ghép

| Phần | Cách hoạt động |
|---|---|
| Hội chợ, đua chó, chợ đen | Cổng và dữ liệu điều hướng riêng; mở đúng hoạt động và tab đã có, giữ điều kiện mở của máy chủ. |
| Xe máy, ô tô, thú cưng, gia đình | Lối vào riêng đến garage, thú cưng, con và gia đình; dùng chung dữ liệu hiện có. |
| Xóm trọ, căn hộ, nhà liền kề, biệt thự | Bốn khu 3D với chiều cao, mái, màu và cây khác nhau. Danh sách lấy từ catalogue, nhà thực sự sở hữu, nơi đang ở và tin thuê công khai. |
| Trang trí nhà 3D | Hình học sàn/tường/đồ đạc; xoay/thu phóng, đi trong phòng, chọn/di chuyển/xoay/cất đồ. Sơn sửa và mua đồ dùng lệnh kiểm tra quyền của hệ thống cũ. Nội thất và các phòng ngoài trời dùng chung save với chế độ minh họa. |
| Người trong khu | Dùng kênh hiện diện thị trấn hiện có, lọc đúng khu; giới hạn tối đa 18 người đang vẽ và 6 NPC dùng lại. Nội thất chỉ hiển thị người được phép vào nhà qua hệ thống home presence. |
| Con và thú cưng | Đọc dữ liệu gia đình/thú cưng có sẵn, hiển thị qua bộ actor chung; không tạo hồ sơ hoặc tiến trình thứ hai. |
| Nhà che nhân vật | Bản đồ 2.5D và tường/nhà 3D giảm xuống alpha 0,35, sau đó phục hồi; không xóa vật thể. |
| Rương chung | Một đợt mỗi 600 giây theo giờ máy chủ, 3–5 rương ngẫu nhiên ở điểm công cộng đi tới được, mỗi rương 10.000 xu. Đợt hết hạn khi sang đợt mới. |

Chi tiết 36 tiện ích, 14 khu và đường nối: `2026-10-11-district-inventory-audit.md`. Sáu ảnh mới ở `public/icons/cozy-v5`, tổng khoảng 1,15 MB; tất cả là vật thể tĩnh.

## Đồng bộ và giới hạn tải

- Three.js tải khi mở cảnh nhà/khu nhà, không nằm trong bundle ban đầu của phố. Bundle sau build: 823.931 byte, gzip 183.507 byte. Hình học 3D là thật; nhân vật vẫn dùng sprite chibi chung.
- Khu nhà gộp đồ tĩnh theo vật liệu, giới hạn pixel ratio 1,5 và tốc độ vẽ 30 khung/giây. Đây là giới hạn của vòng vẽ, không phải kết quả đo FPS trên điện thoại.
- NPC là diễn hoạt cục bộ, không ghi save và không có socket riêng. Người chơi tái sử dụng socket, bộ lọc và giới hạn gửi tọa độ hiện có.
- Cảnh dừng khi tab ẩn, bị dialog khác che hoặc đóng; dọn WebGL, listener, observer và texture. Đổi sơn nhiều lần giải phóng vật liệu không còn dùng.
- Chưa có phép đo tải 1.000 người trên máy 9 core cho bản thay đổi này. Không suy ra khả năng chịu tải từ số lượng NPC hoặc kiểm thử đơn vị.
- Khu công cộng dùng đường đi chung. Phòng thuê riêng vẫn giữ kiểm tra hợp đồng/quyền truy cập; không mở nội thất riêng tư cho mọi người trong xóm.

## Rương: tính đúng tiền và vận hành

- Có bảng PostgreSQL và khóa giao dịch cho người nhặt đầu tiên. Claim và cộng ví cùng giao dịch; các room/shard chia sẻ một đợt và một kết quả người thắng.
- Chứng thực vị trí do dịch vụ live phát sau vị trí hợp lệ mới nhận. Không nhận vị trí do HTTP claim tự khai; bơi, chèo, trong nhà và các hoạt động khác không nhặt rương phố từ xa.
- Chứng thực chỉ xin sau khi hàng đợi lệnh trống. Retry giữ nguyên request ID và proof. Nếu kết quả vẫn không rõ, tải lại trạng thái ví từ máy chủ.
- Snapshot trễ không hồi sinh rương đã nhặt. Khởi động lại không sinh thêm thưởng cho đợt cũ. Lưu lịch sử có giới hạn 24 giờ.
- Mặc định `LIVE_TOWN_TREASURE=0`. Khi được yêu cầu phát hành, cần bật `LIVE_TOWN=1` và `LIVE_TOWN_TREASURE=1` trên cả HTTP và live service. Lịch 24 giờ chạy trong live service; không cần cron của trình duyệt. Cần tiến trình live được giám sát và tự khởi động lại như dịch vụ hiện có.
- Thông báo đợt rương là thông báo trong game. Chưa gửi thông báo ra người dùng hoặc kênh phát hành.

## Bằng chứng kiểm thử

- `npm run test:isometric`: toàn bộ chuỗi regression hiện có qua.
- `npm run test:living-districts`: model nhà/khu nhà, adapter trang trí, tương thích vendor, danh sách tiện ích và client rương.
- `tests/three-scene-lifecycle.mjs`: 5 kiểm thử qua, gồm export của bundle thật, dừng/chạy lại khi bị che, giải phóng vật liệu khi đổi sơn, raycast xuyên tường mờ và phục hồi độ đậm.
- `tests/town-treasure-client.mjs`: 7 kiểm thử qua, gồm hàng đợi hơn 5 giây, phản hồi đến trễ, mất đáp ứng và gửi lại cùng biên nhận.
- `tests/isometric-town.mjs`: 9 kiểm thử qua, gồm nhận checkpoint có thẩm quyền trước khi gửi vị trí tiếp.
- `tests/isometric-guide-lifecycle.mjs`: 21 kiểm thử qua.
- `npm run check`: 339/339 JS qua cú pháp và kiểm tra Safari 15. Bundle 3D sau build cuối cũng đã kiểm tra lại.
- PostgreSQL/HTTP/WebSocket thật: `tests.test_town_treasure tests.test_live_town_treasure`: 16 kiểm thử qua. Nhóm HTTP CSRF/rate limit, proof và hiện diện hoạt động/khu nhà: 12 kiểm thử qua.
- `npm run typecheck:isometric` và build Phaser qua. Kiểm tra whitespace cần dùng `git -c core.whitespace=cr-at-eol diff --check` vì một số file cũ trong worktree dùng CRLF.

## Kiểm tra trực quan

Đã thao tác trên bản local bằng trình duyệt: tìm khu căn hộ qua Chỉ đường, đi đến cổng, mở cảnh khu nhà với 6 NPC, vào căn gác hiện tại, mở/đóng bộ bày trí, chạm sàn và thấy nhân vật đổi vị trí, quay ra phố rồi mở lại khu nhà. Ví vẫn 460 xu và quỹ 320 xu; không mua thêm đồ hoặc sửa save để tạo ảnh.

Ảnh `output/living-districts-20261011/home3d-local.jpg` cho thấy phòng 3D và nhân vật sau khi đi. Đây là căn gác chưa có đồ của tài khoản preview, không phải mẫu nội thất biệt thự đã trang trí.

Ảnh `output/living-districts-20261011/district3d-local.jpg` ghi lại sân chung khu căn hộ và nhóm NPC. Tab preview được giữ mở ở cảnh này.

Trình duyệt vẫn trả viewport thực tế 551 × 672 sau yêu cầu đổi kích thước, nên chưa xác nhận trực quan các breakpoint desktop/tablet. Cũng chưa thử bằng hai tài khoản thật cùng vào khu nhà, hoặc bằng tài khoản đã sở hữu biệt thự/con/thú cưng. Những phần đó hiện có kiểm thử model/adapter/máy chủ, không được tính là đã nghiệm thu hình ảnh trên nhiều thiết bị. Lần mở WebGL đầu chậm trong môi trường thử; chưa có số đo đủ tin cậy để khẳng định FPS.
