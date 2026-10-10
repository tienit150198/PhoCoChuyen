# Đường làng tự nhiên theo ảnh tham khảo

Yêu cầu đã chốt: đường uốn, phân nhánh và nối sân nhà như ảnh người dùng gửi; giữ hình ảnh 2.5D nét mềm hiện tại.

- [x] Tạo lối vào từng cửa nhà/quầy, nối đường gần nhất bằng đường đi không xuyên vật cản.
- [x] Bỏ sân chữ nhật rời rạc; thay sân nhỏ bo mềm và lòng đường rộng hẹp nhẹ, ngã rẽ không bị viền cắt ngang.
- [x] Giữ toàn bộ mặt đường là hình tĩnh trong bộ nhớ đệm nền; không thêm vòng lặp chuyển động hay đồng bộ server.
- [x] Kiểm tra hình học, đường tới các cửa, build và xem lại desktop/mobile trên trình duyệt.

Không thay dữ liệu lưu người chơi, vị trí công trình hoặc quy tắc va chạm client/server.

## Kết quả kiểm chứng

- `node tests/organic-streets.mjs`: 50 cửa nghề + 8 quầy cư dân nối tới đường chính, mọi đoạn cong giữ khoảng tránh vật cản; hình học cố định, không sửa dữ liệu gốc. Kiểm tra cửa bị vách ngăn không vẽ đường xuyên vách.
- `node tests/island-neighbourhoods.mjs`: 84 điểm đến liên tục, 16 đường chính không cắt vật cản; lần cuối đường chậm nhất 32 ms trên máy phát triển.
- `npm run typecheck:isometric`, `npm run build:isometric`: qua. Bundle cuối 1.347.794 byte; gzip 380.678 byte.
- `npm run test:isometric`: qua toàn bộ; có 1 kiểm tra tài nguyên server tùy chọn được bỏ qua. Sau chỉnh nét cuối chạy lại kiểm tra hình học, typecheck và build.
- `npm run check`: 1035/1035 JavaScript qua. `node scripts/check_old_safari.mjs` sau build cuối: 332/332 qua.
- Xem trực tiếp ở desktop 1280×720 và điện thoại 390×844; không có console error. Đã trả viewport về mặc định.
- Ảnh kiểm chứng: `output/organic-streets-20261010/garden-desktop.jpg`, `market-phone.jpg`. Bản đối chiếu công viên: `park-before.jpg`, `park-after.jpg` (trước bước tinh chỉnh cuối).

Đường nhánh được tạo một lần khi dựng cảnh, dùng cùng dữ liệu va chạm với nhân vật. Lòng đường thay đổi rộng hẹp nhẹ, nhánh nhập theo hướng tiếp tuyến khi đủ khoảng trống, sân bo mềm kéo tới hàng hiên. Các vai đường vẽ trước toàn bộ mặt đường để tránh đường viền cắt ngang ngã rẽ. Nền vẫn dùng bộ nhớ đệm hiện có, không thêm tài nguyên ảnh, lịch cập nhật hoặc lưu lượng multiplayer.
