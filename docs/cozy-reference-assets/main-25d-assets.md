# Asset bổ sung cho main 2.5D

Ngày 2026-10-05, dùng công cụ image_gen tích hợp. Nguồn và đầu ra ở trong repository, không phụ thuộc thư mục generated_images khi chạy game.

- `vegetation-source.png` → `public/icons/cozy-v2/vegetation.webp`: 8 cây/bụi/đá, atlas 1536×1024, 476206 byte, alpha trong suốt. Phần màu haze trong RGB nguồn nằm dưới alpha 0. Script chỉ đóng gói vùng sprite, co kích thước và thêm lề trong suốt; không vẽ lại asset. Thứ tự: đa, phượng, dừa, chuối, tre, hoa giấy, bụi hoa vàng, đá.
- `preview-corner-source.png` → `public/preview25d/scene.webp`: hình tham khảo góc phố cho prototype độc lập trước đây. Bản game chính vẫn dựng từng sprite bằng Phaser; không dùng ảnh này làm bản đồ chính.

## Prompt thực tế của atlas mới

Use case: background-extraction. Edit target: the provided game vegetation atlas. Make a clean production PNG atlas for a Vietnamese cozy 2.5D game, true transparent background. Keep eight separate detailed illustrated objects: top row banyan tree, red flamboyant tree, coconut palm, banana; bottom row bamboo, pink bougainvillea bush, yellow-flowered shrub, garden rocks. REMOVE ALL colored haze, colored background, colored glows; empty space must be completely alpha-zero. Arrange exactly 4 equal columns by 2 equal rows, each individual object centered within its own cell, fully contained, with wide transparent gutters around all eight sprites. Each cell has at least 12% margin ALL sides, root/ground contact at 85% cell height. Slightly shrink objects to enforce margins. Preserve the soft warm hand-painted leaves, delicate brown outlines, original detailed cozy cartoon style, view from slightly above. No grid lines, no text, no white rectangle backdrop, no checkerboard painted into image, no atmosphere. Every individual silhouette and all roots must be intact and separated, no sprite touches another cell. Output landscape 1536x1024.

Tham chiếu: atlas nháp trước đó trong cùng phiên làm việc, xây theo các bảng Phố Có Chuyện người dùng cung cấp. Đóng gói lại bằng `npm run assets:reference`; source regions được ghi trong `sources.json` vì bố cục ảnh nguồn không chia ô đều hoàn toàn.
