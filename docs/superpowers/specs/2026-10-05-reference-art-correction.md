# Phố Có Chuyện — sửa hình theo mẫu người dùng

Người dùng đã từ chối bản pixel thô và trả lời rõ: **“Giữ đúng nét và độ chi tiết trong ảnh mẫu”**. Đây là chỉ dẫn mỹ thuật hiện hành, thay phần “toàn bộ thành pixel” trong kế hoạch trước. Không yêu cầu thêm vòng xin phép cho việc sửa đã được giao.

## Chuẩn hình

- Bám bộ ảnh Phố Có Chuyện người dùng gửi: chibi đầu tròn lớn, mắt rõ, má hồng, nét nâu mềm; nhà phố Việt, mái ngói, cây xanh, hàng quán nhiều chi tiết sinh hoạt.
- Dùng sprite minh họa có alpha, góc nhìn 2.5D; không phóng hình ô vuông thô để thay cho chi tiết.
- Công trình tĩnh tải/cache một lần; nhân vật có bốn hướng, đứng và các khung đi. Camera, va chạm, tiến tới cửa rồi tương tác phải dùng dữ liệu thật.
- Cập nhật đã xác nhận: **chỉ chữ và giao diện dùng kiểu pixel**. HUD giấy kem, gỗ nâu, viền bậc; chữ tiêu đề/nút VT323 có dấu Việt, phần giải thích dùng chữ dễ đọc. Cảnh và nhân vật vẫn minh họa nét mềm.

## Đảo và không gian mở

- Tên bản đồ là **Đảo Hoàng Sa (Pattle Island)** trong quần đảo Hoàng Sa. Đường bờ được giản lược theo ảnh vệ tinh AMTI ngày 01/02/2014: https://amti.csis.org/dao-hoang-sa/?lang=vi. Mô tả hình bầu dục đối chiếu cổng Đà Nẵng: https://danang.gov.vn/vi/web/dng/w/ubnd-huyen-hoang-sa-i.
- Giữ tỷ lệ đường bờ tự nhiên trước phép chiếu isometric; không chép các công trình hiện có ngoài đời. Đường phố và nghề trong game là bố trí giả tưởng, không phải bản đồ khảo sát.
- Biển bao quanh; khu nghề hiện tại ở trong đất liền. Vùng dự trữ phía tây/đông nằm bên trong đường bờ cố định. Nghề mới, nội dung và mở vùng thêm bằng dữ liệu sau, không tự mở thưởng hay nghề chưa hoàn thiện.
- Cảnh nghề riêng trong nhà. Câu cá, chèo thuyền, bơi mở toàn màn hình với cần câu/phao/giật cần/cá mắc câu, mái chèo và động tác bơi; không thu vào hộp thoại nhỏ.
- Người chơi trên cùng phố có thể thấy nhau ở khu hoạt động ngoài trời. Chỉ đồng bộ ngoại hình, vị trí và động tác công khai; nhiệm vụ, vòng chơi, vật phẩm, ví và thành tích vẫn riêng.

## Giữ chức năng và tốc độ

Giữ 41 nghề, bản lưu và luật do server quyết định; cần tròn điện thoại, bàn phím, phố nhiều người thật, nhiệm vụ/ví riêng. Giữ câu cá, thuyền, hồ bơi có thao tác và thành tích riêng. Tất cả input phải dừng khi thả, hủy pointer, blur, ẩn trang hoặc mở hộp thoại. Giới hạn texture/cache và dừng vòng vẽ khi đứng yên. Không dùng kết quả desktop để cam kết FPS điện thoại thật.

## Kiểm tra trước khi báo đạt

So ảnh cảnh chạy thật trên desktop và điện thoại với mẫu; kiểm tra người mới, trang phục đã lưu, bốn hướng/đi/dừng, chạm cửa, camera, hai trình duyệt có người khác, lái xe và thao tác giải trí. Các asset gốc và prompt được giữ trong `docs/cozy-reference-assets`; bản nén WebP nằm trong `public/icons/cozy-v2`.

Mẫu ảnh đẹp chưa đủ chứng minh game hoàn tất. Phải kiểm tra hình sau khi ghép, khả năng điều khiển và các giới hạn còn lại, rồi review spec và chất lượng.
