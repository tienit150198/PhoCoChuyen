# Shipper — bản thử local 04/10/2026

Bản thử riêng: http://127.0.0.1:8766/ — chạy bằng `python output/run-shipper-preview.py` trong worktree này. SQLite và nhân vật mẫu nằm riêng trong `output/shipper-preview-20261004`; không thay bản chơi ở cổng 8765. Chưa deploy.

## Thay đổi

- Bản đồ chọn tuyến có khu dân cư, dịch vụ, nhà vườn; nhà/cây, đường chính, điểm lấy/giao và số thứ tự các chặng. Tuyến nháp dùng nét đứt.
- Bản đồ khi lái có đường đi theo phố, vị trí xe, điểm đến; mở bản lớn sẽ dừng xe. Escape hoặc Tiếp tục lái để quay lại.
- Chỉ dẫn rẽ và khoảng cách theo đường, tiến độ dừng xe tại ô vàng, nút Cách lái cho bàn phím và điện thoại.
- Cảnh phố thêm sân vườn, vỉa hè, chậu cây và chi tiết cửa hàng. Giữ cơ chế đèn giao thông, tiền phạt, xăng và chuyến đi do server xử lý.
- Âm thanh nhân vật mẫu đã tắt.

## Kiểm tra

- 101 Python tests: delivery, drive, traffic, guides, i18n đều đạt.
- 1.225 cặp đường đi và hồi quy chỉ dẫn sát ngã tư; planner geometry, escaping, marker tests đạt.
- 483/483 JavaScript files qua kiểm tra cú pháp; diff check sạch.
- Browser 390×844 và 1440×1000: bản đồ, nút trợ giúp, phím Tab/Escape, trả focus, dừng xe khi xem bản đồ và lái tiếp được kiểm tra thực tế.
- Desktop canvas 1140×480: khoảng 75 FPS, thời gian vẽ trung bình 1,30 ms trên máy thử. Không phải cam kết hiệu năng cho mọi thiết bị.
- Review độc lập đã đóng lỗi chỉ dẫn bỏ qua chỗ rẽ cách dưới 5 m.

## Bổ sung joystick và chạy lùi

- Joystick analog tròn với núm kéo tự do, không chia bốn nút. Kéo lên/xuống điều khiển tiến/lùi, kéo ngang/chéo điều khiển tay lái; độ kéo quyết định mức ga và góc lái. Buông tay núm về tâm, xe giảm tốc.
- S/↓ chạy lùi, Space phanh; giữ nút Ga và Phanh riêng. Lùi tối đa 4 m/s, đổi chiều phải giảm về 0 trước. Chuyển tab, đóng cảnh, mở map/help và pointer cancellation đều xoá đầu vào đang giữ.
- Va chạm, kiểm tra đèn giao thông, tiến độ dừng giao hàng dùng tốc độ có dấu đúng cách. Xe bò chậm vẫn giao được; nhả phím sau khi chuyển focus không kẹt phanh.
- Tests: controls và lifecycle Node đạt; 80 bài courier/drive/traffic đạt, sau sửa review chạy lại 18 drive/traffic/i18n đạt. Browser xác nhận kéo chéo, lùi, thả/cancel, phanh, chuyển focus và dừng khi mở map. Review đã đóng cả hai lỗi.

## Nâng cấp người, cây và thành phố

- Nhân vật có tay chân, dáng đi/vẫy tay, khuôn mặt, tóc, nón và túi; góc trước/sau/nghiêng. Xe máy có bánh, thân xe, gương, đèn và người ngồi.
- Cây có thân phân nhánh, tán không đều nhiều lớp, bóng tiếp đất. Tán cây xa dùng ảnh Canvas đệm theo bảng màu; cây rất gần vẫn vẽ vector.
- Phố dùng màu tường dịu hơn, kính có khung/phản chiếu, ban công, mái che sọc, bảng hiệu, máy lạnh, chậu cây, chân tường, gạch vỉa hè và rãnh thoát nước. Góc nhìn desktop rộng hơn; culling khớp góc nhìn mới.
- Đồ họa Canvas bán hiện thực, không phải mô hình 3D hoặc ảnh chân thực. Vị trí đường, điểm giao và luật chơi giữ nguyên.
- 85 Python courier/drive/traffic/i18n tests đạt; Node sprites/architecture/controls/lifecycle đạt; review không còn phát hiện nghiêm trọng. Đã xem thực tế mobile/desktop và chuyển ánh sáng mưa/đêm trong trình duyệt kiểm thử.
- Đo sau khi làm nóng trên máy thử: khung desktop 1150×480 khoảng 60 FPS (vẽ trung bình 4,77 ms); khung mobile 360×374 khoảng 75 FPS (3,44 ms). Đây là số đo máy hiện tại, không phải benchmark điện thoại thật.

## Toàn màn hình

- Nút Toàn màn hình ngay dưới map; khi mở đổi thành Thu nhỏ. Ưu tiên fullscreen của browser, tự dùng khung phủ toàn viewport nếu bị từ chối/không hỗ trợ.
- Esc đóng map/trợ giúp trước; Esc tiếp hoặc Thu nhỏ quay về màn làm việc. Khi đổi chế độ hoặc đóng ca lái, xoá ga/phanh đang giữ. Tab giữ focus trong các điều khiển lái khi mở rộng.
- Canvas tự đo lại kích thước, có khoảng đệm safe area cho nút điều khiển. Native fullscreen 1280×720 và fallback mobile 390×844 đã kiểm tra trực tiếp; kiểm thử lifecycle fullscreen và 18 drive/traffic/i18n đạt.
- Giữ nguyên canvas khi sheet cập nhật trạng thái để không làm thoát fullscreen; kiểu mở rộng của dialog vẫn áp dụng khi lớp CSS được cập nhật. Kiểm thử morph cho vùng động và vùng thường đạt, review đã đóng phát hiện này.
