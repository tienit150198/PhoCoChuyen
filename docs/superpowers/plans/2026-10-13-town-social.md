# Tương tác trong phố 2.5D

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Người đang đi trên bản đồ 2.5D nói chuyện qua bong bóng trên đầu, gửi cảm xúc và mở thẻ tương tác của người chơi khác.

**Architecture:** Giữ transport /live và xác thực hiện có. TownSocial bổ sung town_say, town_emote, town_card vào TownFeature; nội dung đi qua chat.store_message. Client social độc lập nhận snapshot presence từ isometric-town, dùng tọa độ màn hình của Phaser để đặt bong bóng DOM và bắt chọn nhân vật. Không thay đổi dữ liệu nghề/xu.

**Tech Stack:** Python WebSocket/PostgreSQL, JavaScript DOM, Phaser TypeScript.

## Phạm vi và quyết định

- Chat toàn phố hiện có giữ nguyên. Cách nối toàn bộ chat lên đầu nhân vật dễ làm nhưng gây nhiễu; chỉ hiển thị giả lập phía client không đáp ứng tương tác hai người. Chọn phát sự kiện thật tới người trong cùng phòng, ở phố (không trong hoạt động khác), cách nhau tối đa 8 ô.
- Tin tối đa 120 ký tự, bong bóng 6 giây; cảm xúc 3 giây. Mỗi người một bong bóng, không tích lũy vô hạn. Chỉ hiện sau server xác nhận; có lỗi và giữ bản nháp khi mất mạng.
- Emoji 👋 ❤️ 😂 😮 🙏 👏 👍. Có thể gửi cho cả nhóm gần đó hoặc nhắm một người trong tầm; không dịch chuyển hoặc ép người kia làm hành động.
- Thẻ người chơi: chào, cảm xúc, kết bạn qua API hiện có, nhắn riêng chỉ với bạn bè, chặn/báo cáo tin qua chat hiện có.
- Chặn hai chiều, mute, rate limit, rời phòng/tab ẩn/mất mạng dọn UI. Tin riêng không bao giờ trở thành bong bóng.
- Mỗi tin dùng kênh ngẫu nhiên riêng và danh sách người thực sự nhận (tối đa 4096 tin/10 phút trong RAM); history/report/react chỉ truy cập bởi những người đó, không lộ lời nói ở xa hay phòng tái sử dụng.
- Thao tác thông thường miễn phí; không thêm kinh tế hoặc phần thưởng ngoài yêu cầu.

## Thực hiện

- [x] Viết/running test đỏ: hai tài khoản thật, lời nói có lọc, xa/hoạt động khác/chặn không nhận, giả mạo đối tượng, account/mute/giới hạn, thu hồi và reactions.
- [x] Thêm live/town_social.py, nối start/handlers với live/town.py; không truy vấn DB trên mỗi bước đi.
- [x] Thêm model JS có test thời hạn, xác nhận/lỗi, disconnect, rời phòng, chặn/thu hồi.
- [x] Thêm panel/ô nhập/reaction/thẻ người chơi bằng DOM, CSS responsive. Nối snapshot từ presence, projection/hit test từ Phaser.
- [x] Typecheck/build bundle và chạy các test presence, chat, renderer liên quan.
- [x] Kiểm tra trình duyệt hai người thật trên server local, desktop/mobile, không chắn joystick, nhập chữ không làm nhân vật đi.
- [x] Ghi kết quả và giới hạn triển khai. Không tự báo đã deploy khi chưa phát hành.


## Kết quả — 14/10/2026

- Đã triển khai trong worktree `wt-feedback-0410`; chưa triển khai production. Không thay đổi schema, dữ liệu nghề, xu hoặc phí người chơi.
- Thêm `live/town_social.py`, `public/js/isometric-social.js`, CSS và nối renderer/presence. Bundle Phaser đã build lại từ TypeScript.
- Mỗi tin 120 ký tự, tồn tại trên đầu 6 giây; 7 cảm xúc tồn tại 3 giây, có nhắm người nhận. Phát cho người trong cùng phòng, không tham gia hoạt động riêng, cách tối đa 8 ô. Các nút reaction trên lời nói dùng bộ 6 emoji chat có sẵn.
- Máy chủ lưu lời nói đã lọc bằng chat hiện có. Quyền history/report/react dựa trên người thực sự nhận. Dọn RAM mỗi tick; dọn tối đa 200 tin quá 24 giờ mỗi phút, giữ tin bị báo cáo chưa xử lý. Biểu cảm tức thời không ghi DB, nhưng kiểm tra mute DB trước phát; reaction trên lời nói có lưu theo chat hiện có.
- Chọn nhân vật hoặc danh sách người gần: chào, cảm xúc, kết bạn qua API thật, mở DM của bạn bè, chặn, báo cáo lời nói đang hiện.
- Đã sửa qua review: kiểm tra mute cả khi notification chậm; phản hồi thẻ đến trễ; dữ liệu bản nháp/chặn không lẫn khi đổi tài khoản; bỏ phản hồi rời phòng cũ.

### Kiểm chứng

- Python: 42 passed, 1 deselected cho social/retention/town/town activities/chat reactions. Một test có sẵn `test_pruned_and_forgotten_take_their_reactions` bị treo lúc teardown trong lượt đầu, đã ngừng tiến trình test và loại riêng test này; không tuyên bố toàn bộ suite đạt.
- Node: các bộ social (15), presence (10), peer renderer (12), appearance (5), loader (3), leisure presence (7) và chat boot đều đạt.
- `npm run typecheck:isometric`, `npm run build:isometric`, diff whitespace với cr-at-eol đạt.
- Browser: `scripts/browser_town_social.py`, hai tài khoản thật trên game + live + PostgreSQL thử nghiệm riêng; desktop 1280×860, mobile 390×844. Lời nói/reaction hai chiều, chọn avatar, chào có người nhận, kết bạn, DM, phím nhập không di chuyển, chặn và không tràn ngang đều đạt, không pageerror; mở trang mới dưới CSP bình thường cũng đạt. Ảnh/report: `output/playwright/town-social/`.
- Kiểm tra bubble projection dùng vị trí đã nội suy của renderer, không dùng vị trí mạng thô; rời phòng/ẩn tab/mất mạng dọn UI và không tự gửi lại bản nháp.

### Giới hạn

- Chỉ bản đồ phố 2.5D; không mang lời nói sang nơi làm việc hoặc hoạt động riêng. Chat Cả phố/DM hiện có vẫn giữ luồng riêng.
- Không ép người khác dịch chuyển/làm động tác; tương tác nhắm mục tiêu là lời chào/cảm xúc.
- Tin gần đây không cung cấp lịch sử UI; receipt quyền đọc tồn tại tối đa 10 phút/4096 tin, còn dữ liệu phục vụ quản trị được dọn theo chính sách trên.
- Release 2.3.0 đang chạy chưa có phần này; cần bước phát hành riêng.
