# Kiểm chứng nhà và nội thất riêng cho từng nghề

Ngày 11/10/2026. Phạm vi: bản local, không triển khai hoặc thông báo cho người chơi.

## Kết quả thực hiện

- 50 nghề trong catalogue có 50 tranh ngoại thất riêng tại `public/icons/careers-v1/`: đổi khối nhà, mái, cửa, thiết bị và hàng hóa theo nghề. Các ảnh dùng chung phong cách nhưng không ghép biểu tượng lên một thân nhà chung.
- Registry `career-art.ts` dùng chung cho cảnh phố, quán người chơi và trang xem thử. Biển hiệu được đo trên từng ảnh thực tế; chữ nằm trong phần bảng có sẵn.
- 50 mặt bằng nghề có đường bao, tường, cửa mở, kiến trúc phụ và bố trí đồ nghề riêng. Nhà thuốc có quầy kiểm hàng, kệ thuốc và tủ bảo quản; phòng khám giữ giường khám. Buồng ảnh có máy ảnh, rèm và khe in; tủ lạnh gia đình không dùng tủ kem.
- 32 mẫu khối nhà 3D cho bốn nhóm trọ/căn hộ/nhà phố/biệt thự; 12 cấu trúc nội thất nhà. Giữ quyền sở hữu, vị trí đồ đã lưu và quyền chỉnh sửa.
- `/career-gallery.html` mở thử tất cả nghề, cả nghề chưa mở khóa: mặt ngoài, vào phòng, chọn điểm thao tác, đi bằng bàn phím hoặc nút, phóng/thu. Dữ liệu minh họa chỉ nằm trong bộ nhớ, không ghi tiền hoặc tiến trình.
- Kiểm tra trình duyệt phát hiện vòng lặp nghỉ khi hàng đợi ảnh còn đang tải, làm nhà cũ lưu lại trên phố. Đã sửa vòng đời loader: cảnh đang nhìn thấy tiếp tục xử lý hàng đợi tới khi xong; cảnh bị che/ẩn vẫn nghỉ. Chỉ báo sẵn sàng sau sự kiện CREATE của Phaser để lần mở phòng đầu tiên không bị đặt lại góc nhìn.
- Bổ sung hình vector cho các khóa biểu tượng chăm cây và ngọn lửa còn thiếu trong dữ liệu server; đổi bóng đổ nhà 3D sang kiểu được phiên bản Three hiện tại hỗ trợ.

## Chứng cứ

- `output/career-art-20261011/sign-review-1.png` đến `sign-review-5.png`: toàn bộ 50 ảnh.
- `output/career-art-20261011/sign-measurements-final.json`: vị trí bảng chữ trên ảnh thật, kiểm tra alpha và tương phản.
- `output/career-art-20261011/browser/50-room-switches.json`: chuyển qua đủ 50 nội thất bằng giao diện trình duyệt.
- `output/career-art-20261011/browser/`: ảnh chụp cảnh nghề, phố và khu nhà 3D.
- `tmp/architecture-preview/`: bản dựng phối cảnh 3D của các nhóm nhà và phòng.
- `2026-10-11-career-art-prompts.json`: mô tả vẽ từng nghề; đường dẫn ảnh nguồn và dữ liệu đóng gói nằm trong thư mục output tương ứng.

## Kiểm tra tự động

- `npm run test:career-architecture`: dữ liệu 50 nghề, tranh/alpha/ngân sách ảnh, biển hiệu, 50 kiến trúc, đồ nghề đúng ngữ nghĩa, đường đi với đồ trang trí tối đa, gallery và kiến trúc nhà ở.
- `npm run test:isometric`: hồi quy cảnh phố, nhân vật, di chuyển, camera, nhà/biển, nội thất và các hoạt động hiện có.
- `npm run test:living-districts`: mô hình nhà, quyền sửa đồ, khách/NPC, vòng đời cảnh, giải phóng tài nguyên.
- `npm run typecheck:isometric`, `npm run build:isometric`, `npm run build:home3d`, `npm run check`.
- `node tests/isometric-asset-lifecycle.mjs`: 6 trường hợp loader/khởi tạo, tái hiện bốn lỗi trước sửa và đạt sau sửa.
- `node tests/illustrated-icons.mjs --live=http://127.0.0.1:18891/api/content`: 7/7, bao gồm toàn bộ trường icon trong dữ liệu server local.
- Lượt duyệt cuối: 50/50 phòng báo sẵn sàng, không có lỗi JavaScript; nhà mới đã hiện trên phố; vào/ra nơi làm việc chính và mở khu căn hộ/nhà 3D thành công. Ví thử vẫn 460 xu, quỹ 320 xu.

## Ngân sách và giới hạn

50 ảnh WebP tổng khoảng 3,86 MiB, cạnh dài tối đa 512 px. Cảnh dùng lại texture, nền/đồ nghề tĩnh được cache; không thêm vòng lặp vẽ từng căn nhà. Cảnh 3D dừng khi bị che hoặc ẩn.

Lượt này kiểm tra một trình duyệt local, mô phỏng đường đi và vòng đời tài nguyên. Chưa kiểm tra tải 1.000 người đồng thời, nhiều máy khách thật hoặc hiệu năng trên mọi điện thoại. Các hoạt động kinh tế và tiến trình vẫn theo dữ liệu game hiện có.
