# Kiến trúc riêng cho từng nghề

Yêu cầu đã được người dùng chốt: mặt ngoài và nội thất phải khác rõ, nhận ra nghề bằng công trình và đồ nghề; kiểm tra thoải mái trên local. Không đổi tiến trình, tài khoản, giá hoặc điều kiện mở khóa.

## Nguyên nhân

- 50 nghề dùng khoảng 16 thân nhà; lớp mặt tiền chỉ đổi biểu tượng/mái che.
- Phòng có bố trí theo nghề nhưng cùng vỏ hai tường và cửa sổ.
- Khu nhà 3D lặp cùng một khối nhà theo hàng.

## Triển khai

1. Vẽ riêng 50 mặt ngoài nền trong suốt, có dáng mái/khối nhà/cửa/thiết bị phù hợp nghề. Lưu WebP, dùng lại texture, giữ cửa và va chạm hiện có. Bảng nghề và gallery dùng chung registry để phát hiện thiếu.
2. Nội thất riêng từng nghề: cấu trúc không gian, mặt tường, trần mở, đồ nghề và khu thao tác. Giữ ID thao tác, lối đi, đồ trang trí đã lưu và sự kiện.
3. Khu thuê/căn hộ/nhà phố/biệt thự 3D dùng các hình khối thực sự khác nhau, có sân, hiên, mái, cổng và sân vườn phù hợp loại nhà.
4. Trang xem thử local cho toàn bộ nghề, dùng trạng thái minh họa riêng, không gọi API ghi tiến trình hoặc bỏ khóa nghề trong game.
5. Kiểm chứng: đủ 50 ảnh khác nhau, alpha sạch, kích thước/tải hữu hạn; đường tới mọi điểm thao tác; typecheck/build; mở gallery và chơi thử local qua trình duyệt.

## Nghiệm thu

- Không dùng tên/biểu tượng để thay cho khác biệt kiến trúc.
- Biển nằm trên mặt tiền; người và cửa ra vào không bị vật thể mới che kín.
- Ngoại thất thống nhất nét vẽ 2.5D ấm, nhưng mỗi nghề có kiến trúc riêng.
- Cảnh tĩnh được cache; nhà 3D và preview tạm dừng khi bị che/ẩn.
- Ghi đúng giới hạn đã kiểm tra; không hứa hiệu năng 1.000 người khi chưa có phép đo tương ứng.
