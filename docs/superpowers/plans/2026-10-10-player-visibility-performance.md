# Nhìn rõ nhân vật và giảm giật cảnh

> Cập nhật sau phản hồi ảnh cùng ngày: phần viền nổi và độ mờ 30% đã được thay bằng ẩn vật che để lộ mặt đất. Xem [bản sửa hồ bơi và che khuất](2026-10-10-pool-occlusion-correction.md). Các số đo bên dưới là của lần triển khai trước bản sửa đó.

> Thực hiện trong lượt hiện tại, sử dụng subagent-driven-development cho phần thuyền độc lập và rà soát. Người dùng đã chọn hướng 1, cho phép sửa lag và bổ sung lỗi chèo thuyền qua hai ảnh.

**Goal:** Nhân vật không mất dấu sau nhà/cây; giảm chi phí dựng phố; thuyền và người chèo khớp khi đổi hướng.

**Architecture:** Giữ sprite 2.5D và Canvas hiện tại. Đo trước/sau bằng bộ ghi số liệu opt-in, kiểm tra vật che bằng vùng alpha đã cache, chuyển độ mờ có giới hạn và kết thúc khi đứng yên. Tối ưu theo số đo, ưu tiên không vẽ vật ngoài màn hình. Không thay đổi server/save hoặc chuyển sang 3D.

**Tech Stack:** Phaser 3.90, TypeScript, Canvas, JS tests.

- [x] Đo frame/update/render, số vật vẽ và trạng thái ngủ trên cùng tuyến đi. Ghi nhận nguyên nhân bằng code hiện tại; không hứa FPS trên mọi thiết bị.
- [x] Thêm kiểm tra hồi quy: phía trước không mờ, vùng trong suốt không tính che, nhiều vật che, ra khỏi vật che tự phục hồi, giới hạn phân bổ, khôi phục khi chuyển map.
- [x] Thực hiện vùng che cache trong client/isometric/visibility.ts và tích hợp phaser-world.ts: nhà + biển, cây; vòng chân và viền người khi bị che, không tween vô hạn. Kiểm tra thân trên của nhân vật theo alpha sprite, chỉ đối tượng vẽ trước người được mờ.
- [x] Áp dụng tối ưu đã đo trong renderer; đảm bảo cảnh tĩnh vẫn ngủ và giảm motion vẫn hoạt động. Bộ đo chỉ bật bằng query isometricdebug.
- [x] Sửa tư thế bơi theo ba ảnh bổ sung: tay/chân nối với vai/hông, thân chìm hợp lý và đúng hướng. Đồng thời sửa public/js/isometric/water-poses.js và các hàm vẽ thuyền liên quan: thân thuyền kín, nhân vật ngồi đúng ghế, tay giữ mái chèo, trước/sau đổi theo hướng. Giữ điều khiển, waypoint và tủ đồ. Kiểm tra các góc trước/ngang/chéo/sau.
- [x] Rà yêu cầu rồi chất lượng; build/typecheck, test:isometric và kiểm tra JS/Safari. Xem local desktop/mobile và lưu ảnh + số đo. Không commit/push/deploy.

## Kết quả kiểm tra ngày 10/10/2026

- Cùng tuyến Công viên Bờ Sen → Phố Thợ Khéo, viewport 1280 × 720, zoom 0,62, 240 khung hình cuối: số phần tử display list được renderer vẽ giảm từ trung vị 494 xuống 68 (P95 494 → 73). Thời gian JavaScript phần render: trung vị 2,2 → 0,5 ms; P95 3,6 → 0,9 ms. Tổng đoạn update/render đồng bộ P95 3,9 → 1,4 ms. Hai mẫu được lưu tại `output/visibility-performance-20261010/before.json` và `after.json`.
- Đây là số đo JavaScript trên máy local, không phải FPS, thời gian GPU hoặc cam kết tải 1.000 người. `updateMs` gồm bước clear trước render của Phaser; `draws` đếm phần tử display list, không đếm từng lệnh Canvas. Vẫn có khung cập nhật ground cache khoảng 17 ms; không tuyên bố đã loại bỏ mọi nguyên nhân giật.
- Browser xác nhận nhà mờ khi che người, biển mờ cùng nhà, người có viền và vòng chân; đi ra nhà phục hồi. Khi đứng yên dưới nhà đang mờ, loop vẫn ngủ. Ảnh `player-behind-house.jpg`, `house-restored.jpg`.
- Xem trực tiếp tám hướng thuyền/bơi, trạng thái nghỉ và nhịp; kiểm tra thêm nhân vật nữ và tủ đồ. Trong game thật đã xuống hồ, bơi đổi hướng bằng bàn phím/cần tròn, lên thuyền/rời bến/đổi hướng/qua mốc đầu/quay về phố. Desktop 1280 × 720 và mobile 390 × 844. Ảnh `swimming-desktop.jpg`, `swimming-mobile.jpg`, `rowing-mobile.jpg`, `water-eight-directions.jpg`.
- Kiểm tra yêu cầu và chất lượng độc lập không còn lỗi bắt buộc. Integration test chạy phương thức thật của DioramaScene với display/Canvas stub; bao gồm nhiều vật che, phục hồi biển, đổi map, giới hạn texture, vùng nhìn camera; năm phép thay đổi gây lỗi giả lập đều bị bắt.
- `npm run test:isometric`, `npm run typecheck:isometric`, `npm run check`, `npm run build:isometric` đều đạt. Một test icon lấy từ server là tùy chọn và bị skip. Bộ Safari là kiểm tra cú pháp, không phải chạy trên iPhone thật.
- Trang thử tư thế tạm đã chuyển vào thư mục output và gỡ khỏi public. Bộ đo không được tạo khi mở URL chơi bình thường.
