# Phố liền mạch, thao tác gọn, mỗi nghề có cảnh riêng

Người dùng xác nhận: xử lý đường cụt và gom nút thao tác, không yêu cầu xóa công trình. Các map nghề cần bố trí và thông tin riêng.

- [x] Đường: rà đầu đường chính; nối các khu bằng đường nhìn thấy, giữ nhánh vào nhà, không cắt vật cản. Bổ sung kiểm tra tính liên thông của đường vẽ, ngoài kiểm tra đất đi bộ.
- [x] HUD: giữ chỉ đường, trò chuyện và điều khiển đi bộ dễ tìm; gom sổ việc/người quen/trạng thái/thư giãn/sự kiện/cài đặt vào menu gọn; camera thu gọn trên cả desktop. Giữ đầy đủ thao tác và hỗ trợ Escape, bàn phím, cảm ứng.
- [x] Nghề: tách các bố trí còn trùng; giữ dữ liệu, tương tác và đồ đã lưu; mỗi nghề có trọng tâm công việc, vật dụng và tên khu vực đúng nghề.
- [x] Rà yêu cầu rồi rà chất lượng; chạy kiểm tra và xem desktop/mobile, không commit/push/deploy.


## Kết quả kiểm tra 2026-10-10

- Mạng đường vẽ: 32 tuyến liên thông, không còn đầu đường chính không có điểm đến; 58 nhánh cửa nhà và 84 điểm đến trong kiểm tra điều hướng. Các đoạn cong mới lưu sẵn điểm mẫu, không tính lại từng khung hình.
- HUD: Chỉ đường/Trò chuyện vẫn trực tiếp; Tiện ích gom thao tác phụ, Thư giãn mở bên trong, góc nhìn thu gọn, thanh đáy còn Công việc/Thêm. Mở/đóng, Escape, trả focus, cập nhật dữ liệu và dialog được kiểm tra. Sửa lớp hiển thị bằng dataset tương thích Safari 15, không phụ thuộc :has().
- 50 nghề có bố trí vật dụng và trọng tâm riêng; bộ kiểm tra 51 trường hợp gồm fallback, toàn bộ điểm tương tác, 9 nhân vật và đồ trang trí đã lưu. Nhãn điều dưỡng, hải đăng và tiếp viên được rà theo chức năng thực. Đồ tĩnh mới được cache thành texture.
- Build và TypeScript qua; bundle Phaser 1.377.904 byte, gzip 389.798 byte. Đây là số dung lượng bundle, không phải kết quả FPS hay tải 1.000 CCU.
- `npm run test:isometric` qua; một kiểm tra icon tùy chọn cần server URL được bỏ qua. Các kiểm tra vocabulary/shell/camera/work-layout/street-connectivity chạy lại sau các chỉnh sửa cuối đều qua.
- `npm run check`: 1.035/1.035 tệp JS; kiểm tra tương thích cú pháp Safari 15: 332/332. Chưa thử thiết bị Safari vật lý.
- Rà spec và chất lượng độc lập đã thông qua sau sửa nhãn và lớp menu.
- Xem bằng trình duyệt: 1280×720, điện thoại 390×844, tablet 820×1180; menu tiện ích/thư giãn, chat, camera và Escape. Kiểm tra trực tiếp bảy nghề: pilot, flight_attendant, nurse, lighthouse, oil, lifeguard, it_helpdesk. Sửa tiêu đề nhiệm vụ bị cắt chữ và chụp lại trên desktop/điện thoại. Không thấy lỗi console trong lần kiểm tra cuối.
- Ảnh: `output/connected-streets-compact-hud-20261010/`. Dữ liệu fixture ở schema preview riêng đã trả về bản gốc (Mây, 460 xu, chưa chọn nghề).
- Không commit, push hoặc deploy trong lượt này. Kiểm tra whitespace trong phạm vi tệp sửa của lượt này sạch; kiểm tra rộng phát hiện CRLF có sẵn ở `tests/isometric-world.mjs`, giữ nguyên để tránh sửa ngoài phạm vi.
- Tra cứu UI/UX skill không trả ví dụ phù hợp; quyết định gom thao tác dựa trên yêu cầu người dùng và kiểm tra trực tiếp.
