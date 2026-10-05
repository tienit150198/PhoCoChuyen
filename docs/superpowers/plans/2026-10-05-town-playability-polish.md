# Phố Có Chuyện — di chuyển, cảnh phố và trò chuyện

> **For agentic workers:** Use superpowers:subagent-driven-development for bounded tasks and independent review. This continues the approved game direction and implements the user's seven concrete corrections; no additional design approval is needed.

**Goal:** Đi chéo tự nhiên, cảnh phố đa dạng, biển trên mặt tiền và trò chuyện luôn dễ tìm trên điện thoại, tablet, desktop.

**Architecture:** Giữ Phaser và dữ liệu nghề/server hiện hữu. Chuyển hướng di chuyển bằng vector liên tục, đường chạm có đoạn chéo hợp lệ; thêm cảnh quan tĩnh ngoài đường đi; biển gắn cùng công trình. HUD và chat dùng DOM responsive, tiếp tục transport thật.

**Tech Stack:** TypeScript, Phaser 3.90, JavaScript, CSS, WebSocket, Python/PostgreSQL.

## 1. Di chuyển — root

- [ ] Kiểm tra đường chạm, bàn phím, cần tròn ở phố, trong nhà, ngoài trời, lái xe. Loại bỏ snap trục không cần thiết, giữ chuẩn hóa tốc độ và va chạm.
- [ ] Test vector chéo, góc va chạm không xuyên tường, đường chạm chéo, dừng ngay khi nhả/blur.
- Files: `client/isometric/model.ts`, `client/isometric/phaser-world.ts`, `public/js/isometric-movement.js`, `public/js/pixel/places.js`, các module lái xe nếu có khóa hướng; kiểm tra `tests/isometric-world.mjs`, `tests/isometric-movement.mjs`, `tests/pixel-places.mjs`.

## 2. HUD, chat, responsive — worker

- [ ] Nút Trò chuyện có nhãn và trạng thái chưa đọc ngay trên HUD; mở đúng chat hiện hữu. Không tạo người hay tin nhắn giả.
- [ ] Chat giấy kem, nét gỗ/pixel nhẹ; tên/avatar/tin nhắn phân cấp rõ, composer luôn thấy, empty/loading/offline rõ; giữ nhắn riêng, trả lời, lịch sử, report/block.
- [ ] Sắp HUD quanh mép, dành trung tâm cho cảnh; mobile, tablet portrait/landscape, desktop; touch tablet có joystick, desktop có chỉ dẫn phím.
- [ ] Test routing chat và lifecycle; kiểm tra trình duyệt các kích thước 390×844, 844×390, 820×1180, 1180×820, 1440×900.
- Files: `public/js/isometric-shell.js`, `public/css/isometric.css`, `public/css/cozy-reference.css` (chỉ phần HUD), `public/js/v4/chat.js`, `public/css/chat.css`, `public/js/isometric/ui-icons.js`, tests liên quan. Worker không sửa model/phaser hoặc logic di chuyển.

## 3. Cảnh và biển hiệu — root

- [ ] Giữ đường bờ Đảo Hoàng Sa, nghề và cửa hợp lệ; thêm cụm cây cao/thấp, bụi hoa, bồn cỏ, ghế/đèn khác nhau bằng dữ liệu xác định, cache tĩnh.
- [ ] Phá cảm giác mỗi lô giống nhau bằng sân vườn có bố cục bất đối xứng, khoảng trống và scale/tint phù hợp; không đặt cây lớn chắn cửa/đường đi.
- [ ] Biển tiệm ở mặt tiền/mái nhà, không cọc bảng dưới đất; nhãn khu công cộng xử lý riêng, readable ở zoom chơi.
- Files: `client/isometric/phaser-world.ts`, module cảnh quan mới nếu cần, `client/isometric/model.ts`, tests hình học/cửa; dùng asset minh họa hiện có.

## 4. Nghiệm thu — root + reviewer

- [ ] `npm run test:isometric`, `npm run typecheck:isometric`, `npm run build:isometric`; các test chat liên quan.
- [ ] Browser thật: đi chéo, chạm đi, vào cửa, chat hiển thị/gửi/nhận qua hai phiên thử, tránh HUD che nhau ở năm kích thước; ảnh thực tế.
- [ ] Review spec, sau đó quality; sửa blocker; ghi bằng chứng và giới hạn.
- [ ] Không commit/deploy; không chỉnh dữ liệu thật. Mọi thử chat dùng tài khoản và database preview riêng.
