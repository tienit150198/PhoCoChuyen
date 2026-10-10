# Kiểm tra hiệu năng và đủ chức năng — 11/10/2026

Nền đối chứng: `5c671878`. Thay đổi chỉ ở vòng vẽ, vòng đời màn hình, cập nhật DOM và đường mở menu; không đổi luật tính tiền, tiến trình hoặc điều kiện mở nghề.

## Các điểm đã sửa và đo lại

| Trường hợp trong kiểm thử hành vi | Trước | Sau |
|---|---:|---:|
| 100 hình tĩnh, lượt đầu + 120 khung kéo camera cùng zoom | 12.100 lượt kiểm tra LOD | 100 lượt |
| Khu nhà 3D đứng yên, 121 khung có khách hoạt động | 13.552 lượt raycast vào mesh nhà | 112 lượt; vẫn vẽ 121 khung |
| Lái xe/nông trại/máy bay bị bảng khác che, 120 nhịp | 120 bước mô phỏng thừa | 0 bước |
| 300 gói live không đổi phần chat | 900 lần ghi DOM | 0 lần; nhận đủ 300 sự kiện |
| 60 lần khách di chuyển trong quán | 60 lần thay HTML bảng khách | 0 lần; tọa độ vẫn cập nhật |
| Sáu lượt polling chủ quán không đổi | Sáu lần thay HTML | 0 lần |

Chỉ đường bỏ RAF riêng, dùng `postupdate` của Phaser; dừng cùng cảnh và không dựng lại đường đứng yên. Thay zoom, hình nhà, góc nhìn hoặc người chơi vẫn làm mới phần cần thiết. Các hoạt động giải phóng phím/cần điều khiển khi bị che và không cộng bù thời gian ẩn khi quay lại.

Review độc lập phát hiện ô chat khách có thể còn chữ sau khi gửi vì cache HTML không phản ánh `input.value`. Đã sửa đồng bộ giá trị ô nhập, thêm ca gửi thành công/thất bại/khách di chuyển; giữ nguyên bản nháp khi gửi thất bại.

## Đối chiếu giao diện

- Danh mục tại `isometric-feature-parity.json`: 50 nghề, 57 nhóm chức năng, 57 điểm vào cũ và 66 tiện ích.
- Kiểm tra dock/menu của cả 50 nghề ở phone/tablet/desktop; ngoài đảo vẫn mở được các thao tác đang bị ẩn ở dock.
- `Đổi nghề` trong menu và trong nơi làm, cùng liên kết hành trình, mở đúng danh sách/hành trình. Nút `isoTown` vẫn trở về đảo.
- 19 màn hình dùng chung truyền đúng hành động; 66 tiện ích giữ dữ liệu route; 12 lối điều hướng vẫn chịu rào chặn trại; khóa truyện vẫn được giữ.
- Sửa nút trở lại phố từ khu riêng bị trùng với thao tác ngồi sau xe. Năm ca chạy hàm thật xác nhận quay lại nơi công cộng và giao thức ngồi sau xe vẫn độc lập, kể cả khi không có bạn đời hoặc chưa nhớ điểm quay lại.
- Đây là kiểm tra đầy đủ đường vào theo danh mục, không phải xác nhận đã chơi toàn bộ giao dịch của 50 nghề.

## Trình duyệt thật

Chromium trong IAB, tài khoản khách kiểm thử riêng tại `localhost:18893`, PostgreSQL/schema riêng. Kích thước là viewport mô phỏng, không phải phần cứng điện thoại thật.

- 320×740: sổ tiệm nằm gọn trong màn, không tràn ngang.
- 390×844: menu có Khách ghé/Pha chế/Kho/Sổ tiệm; mở kho, quay lại bàn pha, mở sổ, đổi nghề thành công. Ví 460 xu, quỹ 320 xu giữ nguyên.
- 768×1024: kiểm tra menu, tủ đồ và điều kiện khóa; phát hiện và sửa thiếu thao tác nghề trên tablet, tải lại xác nhận Khách ghé/Pha chế hiện.
- 1280×720: kiểm tra menu, toàn đảo, kéo camera. Góc nhìn sau kéo giữ ở chế độ browse và vòng vẽ ngủ sau khi đứng yên.
- Đang đi theo chỉ dẫn có bảy điểm đường: mở hành trình giữ bộ đếm ở 87 khung trong hai lần đọc cách nhau qua các lượt kiểm tra; đóng bảng nhân vật tiếp tục. Không có lỗi console ở lượt kiểm tra cuối.
- Mở nhà 3D từ hành trình và vào màn bày trí: cảnh nhà cùng danh sách vật dụng hiển thị; không thực hiện mua vật dụng trong lượt kiểm tra này.

### Mẫu chẩn đoán sau sửa

| Viewport / cảnh | Số mẫu | JS tổng p50 | JS tổng p95 | JS tổng lớn nhất |
|---|---:|---:|---:|---:|
| 390×844, di chuyển, zoom 0,64 | 240 | 1,1 ms | 1,8 ms | 3,6 ms |
| 1280×720, toàn đảo 357 mục được vẽ, zoom 0,0836 | 240 | 2,2 ms | 2,9 ms | 15,3 ms |

Nguồn: `canvas.dataset.isoProfile` khi bật `?isometricdebug=1`. Đây là thời gian JavaScript đồng bộ của Phaser, bao gồm update/render; **không phải FPS hoặc thời gian GPU/compositor**. Hai cảnh khác nhau nên không dùng làm tỷ lệ tăng tốc trước–sau. Những lượt tải đầu/đổi kích thước khi đang chạy test nền có đỉnh cao hơn; bảng trên là mẫu di chuyển sau tải. Không kết luận hết giật trên mọi thiết bị hoặc đủ 1.000 CCU từ các mẫu này.

Ảnh bằng chứng: `output/release-2.0-local/perf-mobile-menu.png`, `perf-desktop-menu.png`, `perf-home3d.png`.

## Kiểm tra đã chạy

- Build Phaser và nhà/khu dân cư 3D; `typecheck:isometric` đạt.
- `test:performance-parity`: 72/72 ca đạt; bao gồm các ca thất bại trước sửa.
- `test:isometric`, `test:career-architecture`, `test:living-districts`, `test:release-ui` đạt.
- `npm run check`: 346/346 file JS và gate cú pháp Safari 15 đạt.
- `illustrated-icons.mjs --live=http://127.0.0.1:18893/api/content`: 7/7 đạt, đã chạy cả ca catalogue HTTP thường bị bỏ qua.
- Review chéo độc lập không còn lỗi chặn sau sửa ô chat, mở rộng menu tablet/desktop và tách thao tác quay lại phố/ngồi sau xe.

Chưa đo GPU trên Android/iPhone/iPad thật, chưa chạy lại tải 1.000 người cho thay đổi frontend này, chưa phát hành production. Cần xác minh bản triển khai rồi mới gửi thông báo hoặc kích hoạt sự kiện hai ngày vàng.
