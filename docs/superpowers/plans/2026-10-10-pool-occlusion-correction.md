# Sửa hồ bơi và nhân vật trông như đứng trên mái

Ảnh phản hồi ngày 10/10/2026 cho thấy hai lỗi trình bày: viền/vòng chân được vẽ cao hơn công trình, và ảnh toàn cảnh hồ bơi đã có phối cảnh bị chiếu isometric thêm lần nữa.

## Thay đổi

- Bỏ lớp viền nhân vật nằm trên công trình. Nhân vật giữ depth theo mặt đất; vòng chân không xuất hiện khi bị che.
- Kiểm tra trực tiếp cho thấy chỉ bỏ viền vẫn chưa đủ: mái mờ 30% vẫn tạo cảm giác người đứng trên mái. Công trình đang che người và biển gắn trên đó giờ fade tới 0, để lộ mặt đất; đi ra thì fade về 1. Chỉ những vật thực sự phủ lên thân trên người mới bị ẩn. Chuyển độ mờ kết thúc để cảnh có thể ngủ.
- Công trình/biển đang ẩn không chặn thao tác chạm xuống đường. Khi hiện lại vẫn chọn được bình thường.
- Hồ bơi trên phố dùng sprite riêng có alpha, đặt trực tiếp một lần, giữ tỷ lệ và nằm dưới lớp người/công trình. Ảnh nền trong hoạt động bơi vẫn giữ nguyên.
- Asset tĩnh mới: [town-pool.webp](../../../public/icons/cozy-v3/town-pool.webp), 576 × 314 pixel. Nguồn PNG giữ trong `output/occlusion-pool-20261010/town-pool-source.png`. Được tạo bằng công cụ imagegen tích hợp, sau đó trim/resize và đóng gói WebP cho game; không thêm vòng animation.

## Kiểm tra

- Đã quan sát RED → GREEN cho yêu cầu không vẽ vòng chân/viền trên mái và ẩn hoàn toàn vật che.
- Integration test chạy phương thức thật của scene: nhiều vật che, phục hồi nhà/biển, chạm xuyên đối tượng đang ẩn, đổi map, cache, culling và renderer hồ bơi dùng đúng sprite.
- Test hình học xác nhận tỷ lệ ảnh, vị trí mặt đất; kiểm tra alpha và giới hạn kích thước/dung lượng asset.
- TypeScript, build và toàn bộ `test:isometric` đạt. Một kiểm tra icon server tùy chọn bị skip.
- Browser tại đúng Bến Biển Xanh: đi sau quán, dừng, đi ra, quán hiện lại; desktop 1280 × 720 và mobile 390 × 844. Ảnh trong `output/occlusion-pool-20261010/`. Không sửa save/server; không commit/push.

## Prompt đã dùng

Reference: `public/icons/cozy-v3/market.webp`, chỉ tham khảo phong cách. `transparent_background: true`.

> Create ONE game-ready standalone sprite: a small community swimming pool for a cozy Vietnamese 2.5D isometric town. Reference image is STYLE ONLY: match its warm outlined hand-painted cartoon game rendering, clean soft brown edges, charming detail, no pixel art. Camera: strict orthographic isometric 2:1 ground grid, parallel edges at plus/minus 26.565 degrees, NO perspective convergence. A low rectangular in-ground pool, turquoise water, subtle painted ripples, small blue tile inner rim, warm cream stone coping and a narrow pale terracotta tiled walking deck, one small metal ladder on the front-left edge, two tiny potted shrubs at rear corners. Pool occupies almost all the asset. No buildings, roofs, huts, trees, surrounding landscape, large background shadows, grass rectangle, people, furniture or text. The complete rectangular deck has a clean diamond/parallelogram silhouette with all four corners visible and transparent space outside. Make the ground footprint nearly 2:1 width:height on screen; ladder and pots only slightly rise above it. Center whole sprite, uncropped, small transparent margin. True transparent alpha background, no checkerboard or solid-color backdrop. Asset should sit naturally flush on an isometric game map, not look like a floating photographic carpet. Keep detail readable at 500 pixels wide.
