# Chat reply implementation plan

**Goal:** Chọn tin nhắn rồi Trả lời trong Cả phố, chat riêng và nhóm.
**Architecture:** Tin nhắn lưu reply_to ID, máy chủ xác minh tin gốc cùng kênh và người gửi có quyền xem. Frame trả reply={id,pid,name,text} hoặc {id,unavailable:true}; nội dung lấy từ tin gốc tại thời điểm đọc, không tin dữ liệu trích dẫn do client gửi. Không tạo luồng chat riêng. Giao diện tái sử dụng menu tin nhắn, vùng trích dẫn trên ô nhập có Hủy trả lời; giữ trích dẫn trong tin đã gửi. Thu hồi/xóa/chặn phải ẩn nội dung gốc.
**Tech Stack:** Python, PostgreSQL, WebSocket, vanilla JS.

- [x] Backend: tests/test_live_chat_reply.py test send/history/reconnect, cùng kênh, quyền, bị chặn/ẩn/thu hồi, idempotency; tái hiện RED.
- [x] live/chat.py + helper nếu cần: reply_to validation/storage, per-viewer projection trên live/history/buffer/pin/last, không N+1 theo từng tin trong trang.
- [x] game/pg_schema.py schema 21, reply_to nullable bigint, idempotent upgrade.
- [x] UI tests/chat_reply.mjs: chọn/hủy/gửi, chuyển kênh, lỗi gửi giữ draft, trích dẫn escape và trạng thái unavailable; tái hiện RED.
- [x] public/js/v4/chat.js + helper public/js/v4/chat-reply.js và public/css/chat.css: chọn tin Trả lời, composer preview, render quote, reset an toàn khi đổi kênh/đóng/thu hồi/chặn.
- [x] Chạy regression chat/history/delete/reactions + browser local hai tài khoản ở 390px.
- [x] Ghi kết quả local; không deploy/đổi phiên bản/Có gì mới, không commit các thay đổi có sẵn.
