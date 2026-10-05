# Phố Có Chuyện — chuyển sang cảnh isometric

Ngày: 2026-10-05. Người dùng đã cho phép tạo và phát triển sau khi duyệt tài liệu cùng ảnh tham chiếu.

## Kết quả cần đạt

Cảnh phố toàn màn hình; HUD giấy/gỗ gọn, màu ấm; cửa tiệm và các màn nghề cùng hệ hình ảnh; nhiệm vụ/lái xe cùng mỹ thuật. Ưu tiên sprite tĩnh, chỉ cập nhật khi thao tác; giữ toàn bộ API, ID nghề, bản lưu và luật server. Không tạo các nghề taxi/xe buýt mới từ ảnh tham chiếu.

## Kiến trúc và trách nhiệm

- `client/isometric/`: TypeScript, Phaser 3.90.0 khóa phiên bản, engine local được build ESM vào `public/js/isometric/`.
- `public/icons/isometric/`: sprite raster trong suốt tạo từ tham chiếu, nguồn/prompt trong docs.
- `PhaserWorld`: thay renderer World, giữ interface cần bởi app/sound/preview, phố và nội thất, camera/tap/drag/depth, không viết lại kinh tế.
- `public/js/isometric-shell.js` và `public/css/isometric.css`: HUD nối env hiện tại, danh mục đủ nghề/nhân vật/cài đặt, đọc nhiệm vụ từ server, responsive, có DOM thay thế tương tác canvas.
- `public/js/careers/delivery_drive.js`: thêm góc nhìn isometric cùng sprite và giữ vật lý/đèn giao thông/lệnh đến nơi; lựa chọn góc nhìn cũ nếu cần.
- `public/js/app.js`, `public/index.html`, package/build: controller chính tích hợp tối thiểu. Worktree đang có nhiều sửa đổi hợp lệ: không revert/stash/commit chúng.

## Task 1: Renderer/scene

Tạo type/math/map/renderer/adapter. Kiểm thử phép chiếu nghịch, đường đi không xuyên vật cản, tap khác drag, mission selection dùng đúng trạng thái. Phố có đường, mặt nước/công viên, các cửa tương tác cùng asset có điểm chân; tên nghề là text thật. Nhân vật và phương tiện tách riêng, depth theo chân. Bộ nghề dùng họ cảnh theo catalogue; điểm tương tác gọi callback hiện có. Chỉ chạy loop khi đang di chuyển/camera/ảnh thay đổi; ngủ khi hidden/covered, dọn observer/input khi destroy. Preview/snapshot và các phương thức API phải hoạt động.

## Task 2: HUD/shell

Tạo HUD fullbleed hoạt động từ env, không giả tiền/quest. Các nút khu phố/công việc/nhiệm vụ/người quen/nhân vật/cài đặt gọi hành động đang có. CSS giấy kem/nâu/đỏ ngói/xanh lá dùng chung sheet hiện có, rõ nhãn và focus, safe area mobile. Danh mục nghề đầy đủ giữ trình chọn/xin việc hiện có. Town default khi bootstrap xong, sheet đóng trả đúng phố/tiệm. Test pure presentation state khi cần và browser desktop/phone.

## Task 3: Lái xe

Renderer isometric tái dùng sprite nhà, nền/xe đồng bộ với phố. Giữ steering/throttle, đường đi, tọa độ, destination, tín hiệu và arrive hook đang có. Không gọi HTTP/money trực tiếp từ renderer. Background tĩnh cache; đánh dấu đích rõ; ít props động. Chạy các test delivery navigation/controls/lifecycle/signal và kiểm browser mission.

## Task 4: Asset/build/integration (controller)

Sinh riêng nhà/café/nội thất và props cần thiết, kiểm alpha/kích thước, lưu workspace/prompt; không dùng nguyên concept sheet làm runtime. Ghim dependencies, script build/typecheck/test. Tích hợp app, cache static. Tạo PostgreSQL scratch local cô lập để thử đúng API. Không dùng database production.

## Task 5: Nghiệm thu

Review spec rồi code; build/typecheck/check JS; test renderer và delivery; smoke API/menu/nghề/save, browser 1440x900 và 390x844. Kiểm không tràn/không lỗi JS/tap/drag/phóng/đóng sheet/refresh. Chụp ảnh review, ghi asset/code bytes thực tế, giới hạn. Không gọi đổi CSS là đã vẽ riêng đủ 41 nghề; ghi rõ asset dùng chung họ cảnh và các màn thao tác giữ UI chức năng.
