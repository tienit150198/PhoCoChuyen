# Friend home invitations implementation plan

**Goal:** Mời bạn bè vào chơi hoặc ở chung lâu dài, không cần kết hôn; cả hai phải đồng ý.

**Architecture:** PostgreSQL lưu lời mời gắn chủ nhà, người nhận và đúng căn nhà. Quyền vào được kiểm tra lại ở HTTP và WebSocket. Giao diện dùng bản chiếu nội thất của chủ nhà, giữ dữ liệu cá nhân của khách riêng. Ở chung cho phép vào khi chủ offline; khách vào chơi có quyền trong 2 giờ sau khi nhận lời. Chủ được thu hồi, khách được rời; bán/chuyển nhà, chặn, hủy kết bạn hoặc nhập save chấm dứt quyền cũ.

**Tech Stack:** Python, PostgreSQL, vanilla JS, WebSocket.

## Backend

- [x] Viết và chạy kiểm thử lời mời, nhận lời, chủ offline, quyền sở hữu, chặn và hết hạn.
- [x] `game/home_guests.py`: root list, invite/answer/revoke/leave, safe room view, shared live authorization.
- [x] `game/pg_schema.py`: schema 20 và bảng lời mời.
- [x] `server.py`: session, CSRF, rate limits; `game/storage.py`, friends/block hooks: vĩnh viễn thu hồi quyền cũ.

## Giao diện

- [x] `home-guests.js`: chọn bạn, hai loại lời mời, trả lời, vào nhà, quản lý người ở cùng.
- [x] `reno.js`, `home-walk.js`: xem nhà được mời; không ghi đè state cá nhân hoặc sửa đồ người khác.
- [x] House, Friends, Family entrypoints rõ ràng; bỏ nội dung nói phải cưới mới được vào nhà cùng bạn.
- [x] Cảnh báo/lời mời mới và làm mới quyền định kỳ; đóng view khi bị thu hồi.

## Gặp nhau trong nhà

- [x] `live/home.py`: cùng một phòng cho chủ, vợ/chồng và bạn được mời; nhiều nhân vật, kiểm tra quyền trên từng sự kiện.
- [x] `home-crowd.js`: hiển thị nhiều người, chọn đúng người tương tác, giữ luồng đáp lại.
- [x] Kiểm thử kết nối, chặn, thu hồi, phòng cũ, nhiều tab và tương thích nhà vợ chồng.

## Xác nhận

- [x] Chạy kiểm thử backend, HTTP, live, UI và các kiểm thử nhà cũ liên quan.
- [x] Thử trình duyệt hai tài khoản chưa cưới ở 390px, lời mời và vào nhà offline.
- [x] Ghi kết quả local. Không deploy, không đổi phiên bản, không đăng Có gì mới.
