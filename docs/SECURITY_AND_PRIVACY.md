# Bảo mật và quyền riêng tư — v0.4 (mở công khai)

Tài liệu này tóm tắt các biện pháp đang có trong mã nguồn và phần việc chủ server phải tự làm. Đây **không phải** chứng nhận đã audit bảo mật. Chính sách hiển thị cho người chơi nằm ở `/privacy` và `/terms`; liên hệ: trachanhtv.works@gmail.com.

## Máy chủ

- Nếu không cấu hình gì, server chỉ bind loopback. Khi mở công khai, hãy đặt server sau một reverse proxy HTTPS (xem `DEPLOY.md`).
- `ALLOWED_HOSTS` kiểm tra header Host, chống DNS rebinding. Mọi request ghi đều phải có Origin cùng nguồn và token CSRF.
- Cookie phiên có HttpOnly và SameSite=Strict. Cờ Secure được bật khi chạy sau HTTPS (tự nhận biết khi `TRUST_PROXY=1`, hoặc ép bằng `COOKIE_SECURE=1`).
- CSP chặt: không có script inline hay script từ nguồn ngoài (style inline được cho phép, vì giao diện dùng thuộc tính `style`), kèm `frame-ancestors 'none'`. Các header bảo vệ khác: Permissions-Policy, COOP, nosniff, Referrer-Policy; HSTS khi chạy HTTPS.
- Giới hạn tần suất cho lệnh, tạo phiên mới, Phố nghề, push và AI (theo phiên và toàn server). Giới hạn kích thước body: 256 KB cho lệnh, 64 KB cho API khác; riêng nhập bản lưu được phép lớn hơn.
- Server chỉ phục vụ thư mục `public/` với danh sách đuôi tệp cho phép. Mã Python, DB, `.env` và `storage/` không bao giờ được phục vụ.
- Với `TRUST_PROXY=1`, server chỉ lấy giá trị **cuối** của X-Forwarded-For (do proxy của bạn thêm vào) nên người chơi không giả IP được.

## Luật game và chống gian lận cơ bản

- Server giữ luật (server-authoritative). Mọi thay đổi tiền, kho hay thưởng đều đi qua reducer thuần, với revision và `request_id` idempotent, trong một giao dịch SQLite.
- Các action nội bộ (`fb_resolve`, `fb_voice`, `soc_*`) chỉ chạy được từ bên trong server. Gửi qua HTTP sẽ bị từ chối.
- Đáp án thủ tục và bài tập (`_key`) và dữ kiện ẩn của vụ việc không bao giờ được gửi xuống trình duyệt.
- Chợ Phố nghề dùng cơ chế giữ hàng (escrow): hàng rời kho người bán ngay khi đăng, bị khóa khi có người mua, và tiền được chuyển bằng lệnh idempotent. Giá bị giới hạn từ 0,5× đến 3× giá vốn, người nhận quà nhận tối đa 100 xu/ngày, nên không bơm tiền giữa các tài khoản được.
- Nhập bản lưu là bản sao lưu của chính người chơi. Server vẫn kiểm tra hợp lệ (validate) nhưng không coi đó là chứng nhận chống gian lận. Game không có bảng xếp hạng ăn tiền.

## AI nhân vật

- Tắt mặc định. Người chơi phải bật "Cho phép AI" trong Cài đặt, và server phải có `LLM_*`.
- Khóa API chỉ nằm trên server (trong `.env` hoặc biến môi trường). Khóa không bao giờ được gửi xuống trình duyệt, ghi vào log hay đưa vào ảnh Docker.
- Dữ liệu gửi tới LLM gồm: review hiện tại, tính cách nhân vật, các tiêu chí đã chấm và lời phản hồi của chủ quán. Không gửi tên thật, cookie hay IP.
- Kết quả từ AI **chỉ được đề xuất**. Server kẹp số sao trong khoảng dữ kiện cho phép, loại bỏ link, markup và câu lệnh chèn (prompt injection), rồi dùng kịch bản dự phòng khi AI lỗi. AI không thể thay đổi tiền, kho hay quyền.

## Phố nghề (người chơi với nhau)

- Mã người chơi (`pid`) là hash một chiều của phiên, không làm lộ cookie.
- Văn bản tự do bị lọc: chặn link, email và số điện thoại; che từ thô tục.
- Có chặn, báo cáo (nội dung bị 3 người báo cáo sẽ tự ẩn), giới hạn tần suất, và mỗi quán chỉ nhận một review/ngày từ mỗi người, sau khi người đó đã thực sự ghé thăm.
- Người chơi có thể ẩn hồ sơ khỏi danh bạ, hoặc tự xóa toàn bộ dữ liệu (Cài đặt → Dữ liệu).
- Phần quản trị hiện được làm thủ công qua SQLite (xem `DEPLOY.md`). Chưa có bảng quản trị riêng.

## Web push

- Push được gửi rỗng (payload-less): nội dung ở lại server, service worker tự lấy qua `/api/push/pending` bằng cookie của chính người chơi.
- Server chỉ gửi tới endpoint thuộc các dịch vụ push đã biết (whitelist), để chống SSRF. Endpoint lỗi 404/410 sẽ tự bị xóa.
- VAPID ES256 được viết bằng Python thuần. Khóa riêng nằm ở `storage/vapid.json` hoặc biến môi trường, và không được đóng vào gói phát hành.

## Dữ liệu và lưu giữ

| Dữ liệu | Lưu bao lâu |
|---|---|
| Bản lưu game | Xóa sau `SESSION_IDLE_DAYS` ngày không hoạt động (mặc định 180), kèm hồ sơ Phố nghề |
| Biên nhận lệnh | 3 ngày |
| Hộp thư Phố nghề | 60 ngày |
| Lượt ghé thăm | 30 ngày |
| Bài bảng tin | 180 ngày |

- Không có analytics, quảng cáo hay SDK theo dõi. Font và icon đều được tự host.
- Log không ghi cookie hay nội dung người chơi gõ.
- Ai đọc được DB hoặc bản backup thì thấy được nội dung chơi, nên hãy bảo vệ volume `storage` và các bản sao lưu.

## Việc chủ server còn phải làm

- Cấu hình HTTPS, sao lưu định kỳ và theo dõi dung lượng đĩa.
- Đổi ngay khóa API nếu khóa từng lộ, kể cả khi lộ trong chat hay issue.
- Xử lý báo cáo và yêu cầu xóa dữ liệu gửi qua email.
- Nếu tải tăng lớn: thêm chống bot (captcha khi tạo phiên), dùng rate-limit chia sẻ khi chạy nhiều tiến trình, và cân nhắc chuyển sang tài khoản đăng nhập.
