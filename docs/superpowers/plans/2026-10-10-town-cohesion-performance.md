# Town cohesion and performance

**Goal:** Thống nhất đường phố, phân biệt nhà theo nghề, tìm lại tiện ích có sẵn và giảm giật ở map/lái xe theo số đo.

**Approved direction:** User explicitly requests these fixes. Keep cozy illustrated 2.5D, organic connected streets, compact HUD, mobile joystick, desktop/tablet. Preserve saves and existing gameplay. No commits/deploys this turn.

**Implementation:** Parallel independent ownership via dispatching-parallel-agents; parent integrates and verifies in CUA browser. Current base sprites and Canvas are retained. Cache reusable artwork and simplify unnecessary draw work before adding effects.

- [x] Parent: measure town overview/panning before changes; unify road surfaces/shoulders and remove per-neighbourhood overlapping path colours. Keep meaningful terrain (garden/runway/quay).
- [x] Parent: reduce ground draw complexity and repeated large sprite downsampling based on measurements; ensure caches are bounded, hit-testing and fading remain correct, idle loops sleep.
- [x] Career facade worker: meaningful per-career exterior props/silhouettes/accents and cached composition; parent integrates into town. All catalogue jobs covered with stable fallback and mounted signs.
- [x] Utility worker: audit actual available actions vs grouped menus, restore omitted working features; avoid fake or duplicated buttons.
- [x] Driving worker: measure existing rendering hot paths, optimize caches/render scheduling without changing simulation or trip settlement.
- [x] Regression tests per changed subsystem, independent review, build/typecheck/full isometric suite/JS checks, browser desktop/mobile. Record before/after scope and limitations; screenshots show the reviewed result.

## Baseline findings

Roads select nine district palettes, so crossing main roads and door branches visibly paint over each other. Each curve sample stamps a 24-vertex disc plus a quad in two passes, making the ground cache expensive to regenerate. Building families collapse many occupations to the same source. Further performance causes require measured verification.


## Kết quả triển khai và kiểm chứng

- Đường chính, đường nhánh và sân trước cửa dùng cùng màu nền/viền, vẽ toàn bộ viền trước mặt đường. Vẫn giữ đường cong, lối vào và dữ liệu va chạm; đường băng/cầu cảng có chất liệu riêng theo công năng.
- 50 nghề có ký hiệu nghề riêng, mái/mái hiên và trang thiết bị; 7 kiểu mặt tiền, 12 nhóm đồ vật. Ghép texture một lần từ ảnh nền đúng loại đã tải, giữ biển tên trên nhà và cơ chế che khuất.
- Khôi phục lối vào những tiện ích sẵn có qua 4 nhóm thu gọn; Chỉ đường tìm được tiện ích không có điểm vật lý và mở trực tiếp. Không nhân đôi những tiện ích đã có điểm đi tới.
- Map: thay mỗi mẫu đường gồm vòng tròn + hình thang bằng đường bao liên tục và hai đầu bo; bài đo 500 mẫu chỉ còn 2.408 đỉnh. Static LOD dùng các mức 64/128/256 pixel, ít nhất hai mẫu ảnh cho mỗi pixel hiển thị, ảnh gốc được khôi phục khi phóng gần. Giữ kích thước/hit-test/alpha; cache theo ảnh nguồn + frame atlas, dọn cùng scene.
- Lái xe: giữ tập ảnh/nền đang nằm trong viewport, chỉ loại phần không dùng sau khung hình; cache nền minimap. Sửa nguyên nhân liên tục xóa rồi tạo lại ảnh khi viewport lớn hơn giới hạn FIFO.

### Số đo có giới hạn rõ ràng

Map được đo trên cùng IAB 1280×720, cùng camera toàn đảo zoom 0,0836, cửa sổ 240 mẫu chuyển động. Chi phí JavaScript đồng bộ update + gửi lệnh vẽ p95: **4,4 → 1,5 ms**; trung vị **3,2 → 1,2 ms**. Số phần tử vẽ tương đương 423/424. Nhân vật ở vị trí khác; đây không phải GPU timing hay một benchmark FPS trên điện thoại. `output/town-cohesion-20261010/town-before.json` và `town-after.json` lưu kết quả.

Lái xe thật bằng giữ nút Ga 7 giây, viewport game 1140×432, DPR 1: mẫu đang chuyển động 484 frames, khoảng cách frame trung bình 14,8 ms, p95 26,6 ms; gửi lệnh vẽ trung bình 4,21 ms, p95 11,9 ms. Tập ảnh tăng theo cảnh mới, không còn tạo lại mỗi frame. File `driving-after.json` là cửa sổ 600 mẫu sau khi thả ga, draw sample lúc đó có cả trạng thái nghỉ; không dùng để thay thế số đo đang chạy.

Benchmark tự động dùng renderer thật với Canvas boundary mock, **không phải FPS/GPU**: trong 240 frames đã làm nóng, 1920×1080 giảm số canvas mới 41.412 → 6, 2560×1440 giảm 64.431 → 0; số thao tác minimap 85.440 → 7.920. Cache thu nhỏ lại khi viewport nhỏ.

### Kiểm tra

- `npm run typecheck:isometric`, `npm run build:isometric`, toàn bộ `npm run test:isometric`: đạt.
- `npm run check`: 1.037/1.037 JS syntax và 334/334 Safari 15 checks đạt. Đã bổ sung AST regression cho false positive `.reset()` của Phaser Loader/Tween, vẫn bắt `CanvasRenderingContext2D.reset()` chưa được bảo vệ.
- Hai lượt review độc lập về yêu cầu và chất lượng: không có lỗi P1/P2 xác nhận.
- Browser: đường thống nhất, nhà có nhận diện nghề, ảnh gốc quay lại khi phóng gần; chọn điểm đi xa và điều khiển bằng phím mũi tên, camera đang xem không bị kéo về nhân vật; engine ngủ khi nhân vật dừng.
- Browser desktop: Tiện ích → Tiền, nhà & phương tiện → Xe & phương tiện mở gara; Chỉ đường tìm `ke toan` → Học kế toán mở đúng màn.
- Browser mobile 390×844: menu nhóm nằm trong màn, cuộn được; Học tập → Học lịch sử mở đúng màn. Đã trả viewport về mặc định, tắt query đo và giữ preview local.
- IAB native fullscreen tự thoát khi thao tác qua công cụ, nên không dùng kết quả đó để khẳng định FPS toàn màn hình thật. Cache ở 1920/2560 và lifecycle fullscreen/reset được kiểm bằng regression; cần thử native fullscreen trên trình duyệt sử dụng trực tiếp nếu tiếp tục đánh giá riêng phần này.

Ảnh bằng chứng: `output/town-cohesion-20261010/overview.png`, `career-street.png`, `mobile-utilities.png`, `mobile-history.png`.

Không commit, push hoặc deploy trong lượt này. Preview dùng dữ liệu thử hiện có; đã đi qua thao tác nhận/cân/nhận hàng/gọi khách để mở lái xe, không ghi đè bản lưu bằng seed/restore.
