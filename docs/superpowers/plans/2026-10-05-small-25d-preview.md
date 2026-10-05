# Một góc phố 2.5D chơi thử

**Goal:** Chuyển ảnh mẫu vừa được người dùng chọn thử thành một cảnh nhỏ có thể đi lại và trò chuyện, trước khi quyết định đổi tiếp game chính.

**Scope:** Bản thử độc lập tại `/preview25d/index.html`. Hai tiệm, người chơi đi tám hướng bằng cần tròn/phím/chạm đường; đến gần Cô Ba hoặc chủ quán để trò chuyện theo lựa chọn. Không nối ví, nhiệm vụ hoặc chat cộng đồng của game chính. Gắn nhãn bản thử rõ.

**Art:** Dùng imagegen tách nền từ ảnh concept đã cho xem, bỏ HUD và nhân vật chính, giữ cảnh và người bán hàng tĩnh. Nhân vật dùng atlas chibi minh họa có sẵn, màu áo xanh. HUD giấy kem/gỗ mềm, không pixel. Cảnh tĩnh giữ nhẹ, dừng vẽ khi đứng yên hoặc ẩn trang.

**Implementation:** `public/preview25d/index.html`, `style.css`, `app.js`, `model.js`, `scene.webp`. Canvas hiển thị nền theo đúng tỷ lệ, cảnh dọc trên điện thoại và máy tính, input và đối thoại là DOM. `model.js` chứa vùng đường, bước di chuyển liên tục và tìm đường trong vùng, có test góc/đường/giới hạn.

**Verification:** Test đơn vị hình học và tốc độ chéo; trình duyệt thực kiểm tra tải hình, đi chéo, thả tay dừng, chạm đi tới quầy, mở/đóng thoại, resize và không có lỗi console. Chụp ảnh bản chạy; mở URL thử trong Codex. Không triển khai game chính hay tiếp tục bản polish đang chờ.
