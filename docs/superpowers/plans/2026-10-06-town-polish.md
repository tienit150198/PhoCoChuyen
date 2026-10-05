# Phố Có Chuyện — hoàn thiện tám phản hồi

Tiếp tục thiết kế 2.5D nét mềm đã được người dùng duyệt. Làm trên main; giữ archive/pixel-2026-10-05 và các thay đổi hội chợ của công việc khác.

## Bằng chứng ban đầu

- Tab thật 127.0.0.1:18891 đang là Phaser, viewport nhỏ bị nhiều cụm HUD chiếm chỗ.
- GET /api/content: 44 nghề, 41 playable. fish, basket, sparkles, bear không có hình trong thư viện icon chung.
- Chat thật mở được nhưng tài khoản khách chỉ xem; cần biểu đạt quyền gửi ngay ở điểm vào, không giả trạng thái online.
- Mặt nhà hiện chỉ có bảy nhóm, biển đã gắn ảnh nhưng tỉ lệ/vị trí còn cần khớp từng mẫu.

## Thực hiện

1. **Icon toàn sản phẩm:** public/js/icons.js và public/js/isometric/ui-icons.js dùng chung bộ vector nét mềm có màu; bao phủ tên icon trong nội dung server, HUD và các module hiện có. Giữ API, hỗ trợ dark theme, có kiểm thử coverage thật. Không sửa logic nghề hoặc hội chợ.
2. **Chat và bố cục:** public/js/v4/chat.js, public/js/isometric-shell.js và CSS liên quan. Giữ chat/DM thật, quyền guest và unread. Entry luôn có nhãn, thu gọn điều khiển camera trên mobile, chat bố cục rõ kênh/avatar/bubble/composer; không làm mới toàn DOM khi chỉ đổi nội dung chat. Kiểm tra mobile ngắn/dài, ngang, tablet và desktop.
3. **Cảnh và di chuyển:** client/isometric cùng dữ liệu bản đồ chia sẻ. Giảm cảm giác đổi hướng đột ngột, giữ tốc độ đi chéo và collision; thêm họ mặt nhà minh họa, sign bám mặt tiền và cây bụi/tiểu cảnh không theo lưới. Trang trí tĩnh, tải theo nhu cầu. Các hoạt động ngoài trời và lái xe phải giữ điều khiển chéo/liên tục.
4. **Nghiệm thu:** typecheck/build, test isometric/chat/icon/map contract; kiểm tra trực tiếp browser, chụp kết quả và ghi rõ giới hạn chưa đo máy thật. Review spec rồi quality, sửa phát hiện thực chất trước khi giao.

## Quyết định

Không thêm nghề giả. Những nghề cùng nhóm có thể dùng cùng kiến trúc nhưng biển hiệu và icon phải đúng nghĩa. Không đổi dữ liệu kinh tế/save và không push hay deploy. Những yêu cầu đã duyệt được thực hiện liên tục, không xin duyệt lại.

## Kết quả đã xác minh — 2026-10-06

- Di chuyển giữ hướng ổn định khi đi chéo; nhịp bước theo quãng đường. Sửa cắt góc qua vật cản và sai số chạm góc; kiểm tra đường tới toàn bộ 41 cửa nghề.
- Thêm tám mặt nhà minh họa, tổng 392.534 byte WebP; 41 nghề chơi được ánh xạ rõ vào 15 họ công trình. Biển hiệu bám bảng trên nhà, tên dài chia tối đa hai dòng. Bổ sung cây bụi tĩnh đa dạng, dùng cùng dữ liệu va chạm phía client/server.
- Bộ SVG có màu dùng chung cho giao diện và các icon trong catalogue server. Điều chỉnh metadata icon của các nghề đang dùng hình không đúng nghĩa.
- Chat có điểm vào luôn thấy, trạng thái khách rõ ràng, tab/kênh, ngày và giờ tin nhắn. Camera thu gọn trên màn nhỏ; sửa tranh chấp phím Escape với hộp thoại và menu Thư giãn bị cắt/che.
- TypeScript, build Phaser và kiểm tra cú pháp JavaScript đều qua. Bộ test isometric qua; 48 test live/chat qua, 7 test icon với server thật qua, 11 test live town Python qua. `git diff --check` sạch.
- Browser kiểm tra 320×568, 390×844, 667×375, 844×390, 820×1180, 1180×820 và 1440×900; cả ba nút Thư giãn bấm được ở cả bảy kích thước. Kiểm tra bàn phím camera → chat → Escape và review spec/quality độc lập đều qua.
- Ảnh nghiệm thu lưu tại `output/playwright/town-polish-final-desktop.png`, `town-polish-final-chat-mobile.png` và `town-polish-final-outings-mobile.png` (không đưa dữ liệu runtime vào Git).
- Giới hạn: chưa đo FPS trên điện thoại vật lý trong lần này. Các nghề cùng nhóm vẫn dùng chung mặt nhà; chưa phải 41 công trình riêng biệt.
