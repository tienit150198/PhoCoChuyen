# Camera và không gian hoạt động dưới nước

Yêu cầu: kéo bản đồ rồi giữ nguyên góc nhìn cho đến khi người chơi chọn về nhân vật; sửa hồ bơi, chặn thuyền xuyên cầu, mở vùng bơi. Giữ dữ liệu thành tích và các sửa chữa trước.

## Nguyên nhân đã đọc trong source

- `PhaserWorld.step()` tự bám bất cứ khi nào nhân vật di chuyển và không còn pointer đang kéo. Chưa có trạng thái xem bản đồ độc lập.
- `places.js` chỉ kiểm tra tâm trong một hình chữ nhật. Cầu gỗ vẽ trong lake backdrop hoàn toàn không có collision. Pool trapezoid và thang không khớp collision rectangle.
- Cảnh 320×200 luôn phủ kín màn hình, nhân vật khá lớn, vùng bơi chỉ 196×90 và camera không thể cho cảm giác một không gian rộng trên desktop.

## Thực hiện (subagent-driven-development)

- [x] Camera: test hồi quy thao tác kéo/thả trong khi tự đi; giữ chế độ xem khi di chuyển và resize; chỉ reset/recenter/Home hoặc đổi cảnh mới bám lại. Review spec đã phát hiện và sửa thêm trường hợp `iso-guide` tự focus khi đến khu.
- [x] Nước: hình học dùng chung cho ranh bờ, mặt hồ, cầu và kích thước thân thuyền. Kiểm tra chuyển động xiên, tiếp cận/rời bến, mốc vòng và hết hạn. Mở không gian tương đối với người bơi, giữ giao thức tọa độ server.
- [x] Build/typecheck và test liên quan; chạy local trên desktop/mobile, kéo bản đồ đang đi, kiểm tra mép trái hồ và bơi chéo, chèo quanh cầu, quay về bờ. Lưu ảnh và ghi đúng các giới hạn kiểm chứng.

Không commit/push, không ghi đè save hoặc sửa trực tiếp dữ liệu người chơi. Chơi thử qua UI có tạo vòng hoạt động tạm; không lưu thành tích hoặc tiêu tiền.

## Kết quả kiểm tra trên local

- Camera desktop: sau pan, giữ W để di chuyển; tọa độ camera không đổi. Xem `output/camera-water-20261010/camera-manual.json`.
- Camera mobile 390×844: nhân vật từ (65,42) đi đến (26.40,39), còn 4 đoạn đường; camera giữ nguyên (1415.851,2013.691), zoom .64. Xem `camera-auto-mobile.json`.
- Boat desktop: giữ A hướng vào cầu 1.5 giây bị chặn thân, đi vòng đầu cầu; rời vòng chưa hoàn tất và quay về bến lên bờ thành công.
- Boat mobile: lái thực tế qua cả 4 mốc, server xác nhận đủ; chọn Về bến, thành tích vẫn 0 vì không bấm Lưu vòng. `boat-mobile-checkpoints.jpg`.
- Pool desktop: xuống thang và bơi tới mép trái trước đây bị chặn sai. Pool dùng nền đúng tỷ lệ 960×600 trong world 640×400; các điểm mạng và bằng chứng vẫn 320×200, qua ánh xạ hai chiều. `pool-expanded-left-edge.jpg`.
- Pool mobile: dùng cần tròn bơi chéo, quay lại thang và Lên bờ mà không hoàn tất vòng; UI không chồng lên cần tròn. `pool-mobile-diagonal.jpg`.
- Build + TypeScript đã qua. Toàn bộ `npm run test:isometric` qua (1 bài phụ thuộc live server được skip); `npm run check`: 1036 JS và 333 bài kiểm tra cú pháp Safari 15 qua. `python -m unittest tests.test_leisure`: 5/5 qua.
- Review chất lượng phát hiện Space trên nút Lên bờ bị shortcut toàn cảnh chiếm mất; đã sửa để button nhận Space gốc. 7 test sự kiện DOM qua; trên browser dùng Tab tới Về bến rồi Space: lên bờ thành công, thống kê vẫn 0. `keyboard-exit.txt`.
- Review spec và chất lượng cuối đều qua. Đã chạy lại toàn bộ test:isometric và check sau sửa bàn phím, exit code 0; đã đăng ký test mới trong package.json.
- Resize mobile→desktop giữ chính xác tâm thế giới và zoom; nút Đưa góc nhìn về nhân vật đưa camera về đúng người chơi. `camera-resize.json`.

Giới hạn: kích thước mobile được mô phỏng bằng viewport Chromium, không phải đo trên iPhone thật. Không benchmark 1000CCU trong lượt sửa này. Không thêm texture hoặc vòng animation mới; vẫn dùng cơ chế idle sleep.
