# Temple Card Visibility Implementation Plan

**Goal:** Người viết chọn Công khai hoặc Chỉ mình tôi cho từng thẻ, đổi lại sau khi treo, và đọc bảng thẻ công khai của mọi người.

**Architecture:** Giữ thẻ gốc trong bản lưu/archive riêng tư. Thêm projection PostgreSQL nhỏ, có index theo chủ/thẻ và thứ tự công khai, chỉ phục vụ các thẻ chủ động chia sẻ. Không quét toàn bộ sessions/archive khi đọc bảng, không tự công khai thẻ cũ hoặc thẻ nhập từ backup. Ghi công khai khi tạo thẻ phải nguyên tử với lệnh và chống replay. Thay đổi quyền xem phải xác thực chủ, CSRF và hoạt động cả thẻ đã archive; thu hồi hiển thị ngay ở lần đọc tiếp theo, không dùng cache công khai tồn tại sau thu hồi.

**Tech Stack:** Python authoritative game/Store, PostgreSQL additive schema, HTTP API, JS temple canvas/dialog, pytest/Node/Playwright.

- [x] Backend: viết tests thất bại cho mặc định riêng tư, tạo công khai/riêng tư, replay, đổi quyền của bản thân và từ chối người khác, thẻ archive, phân trang, không lộ SID/nội dung riêng tư, import/reset/delete phù hợp.
- [x] Backend: triển khai schema/projection/index nhỏ không backfill; API GET bảng chung và quyền thẻ của mình; API đổi quyền chuẩn CSRF/ownership. Thông báo hợp đồng API cho UI trước khi nối.
- [x] UI: chọn quyền khi viết (mặc định riêng tư), nhãn quyền trên thẻ, đổi quyền riêng từng thẻ gồm thẻ cũ; tab Lời chúc của tôi/Bảng chung, phân trang, trạng thái tải/lỗi; thoát không mất cảnh/vị trí. Giữ tên/lời nhắn user nguyên văn, escape HTML.
- [x] Verification: reducer/Store/HTTP/security/schema tests, Node rendering/lifecycle, browser hai tài khoản: public nhìn thấy, private không thấy, thu hồi biến mất, archive vẫn đổi được; mobile/desktop và giao diện cũ/mới.
- [x] Release: bản 2.2.1 từ live 2.2.0/source e179dd8a; kiểm gói và schema nâng cấp, xác nhận DB còn đủ trống. Không full backup mới vào ổ production, không dọn backup/release cũ. Rolling và kiểm manifest/assets/health; cập nhật tài liệu.

User đã chọn cả hai quyền xem. Thẻ 2.2.0 giữ riêng tư; chỉ hành động chọn Công khai mới chia sẻ nội dung.
