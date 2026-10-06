# Admin User Password Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép admin đổi mật khẩu ngay tại người dùng tìm được.

**Architecture:** API POST `/api/admin/users/password` nhận `{id, username, password, confirm}`. Chỉ admin có CSRF hợp lệ được gọi; cập nhật hash và thu hồi login/TikTok flow của mục tiêu trong một giao dịch. Giao diện thêm nút từng hàng và hộp thoại ngoài vùng danh sách, giữ nguyên kết quả tìm kiếm.

**Tech Stack:** Python, PostgreSQL, JavaScript ES modules, CSS admin hiện có, unittest, Node, Playwright.

**Approved design:** `docs/superpowers/specs/2026-10-05-admin-user-password-reset-design.md`; chủ dự án đã duyệt trong chat.

## Task 1: Baseline tách riêng

- [x] Xác minh release đang chạy và hash của gói 1.7.15-fair-stability.
- [x] Trích xuất gói vào `output/admin-password-reset-20261005/app`, giữ nguyên file ngoài phạm vi thay đổi.
- [x] Xác minh nguồn admin dễ đọc khớp byte gói sau chuẩn hóa xuống dòng; gói baseline chưa minify các file này.
- [x] Chạy kiểm thử danh sách người dùng hiện có, dùng cơ sở dữ liệu PostgreSQL riêng.

## Task 2: Backend

Ownership: `game/admin_users.py`, `game/accounts.py`, `server.py`, `tests/test_admin_users_reset.py` trong app tách riêng. Mở rộng `accounts.py` để chặn đăng nhập hoặc tự đổi mật khẩu đang chạy đồng thời vượt qua lần reset của admin.

- [x] Viết và chạy kiểm thử thất bại cho quyền admin/CSRF, xác nhận mật khẩu, định danh mục tiêu và thu hồi phiên.
- [x] Thêm hàm reset và API trước nhánh đọc bản lưu nặng; dùng kiểm tra/băm mật khẩu sẵn có, lỗi JSON thông thường, rate limit.
- [x] Giao dịch không động vào bản lưu và tài khoản khác; xóa TikTok flow gắn với login bị thu hồi.
- [ ] Chạy lại kiểm thử mới và kiểm thử tài khoản/admin liên quan.

## Task 3: Frontend

Ownership: `public/js/admin/users.js`, `public/js/admin/main.js`, `public/css/admin/admin.css`, `tests/admin_users_reset.mjs` trong app tách riêng.

- [x] Viết và chạy kiểm thử thất bại cho nút tại hàng, đúng mục tiêu, hủy, xác nhận, gửi một lần và lỗi.
- [x] Dùng kiểu modal và focus trap admin hiện có; mật khẩu chỉ ở trường nhập, không đưa vào HTML dựng lại hoặc bộ nhớ lâu dài.
- [x] Bổ sung gửi API, báo thành công và reauth khi admin tự đổi mật khẩu.
- [x] Chạy lại kiểm thử mới và kiểm thử danh sách cũ.

## Task 4: Kiểm tra tích hợp và bàn giao

- [x] Chơi luồng admin đầy đủ trên desktop và mobile bằng tài khoản thử local; xác minh mật khẩu mới đăng nhập được, mật khẩu cũ/phiên cũ bị từ chối.
- [ ] Review mã và sửa các phát hiện có căn cứ; kiểm tra không lộ mật khẩu trong HTML/phản hồi.
- [ ] Đóng gói bằng cách chỉ thay file của tính năng trong gói baseline; xác minh manifest và file khác giữ nguyên.
- [ ] Báo người dùng kết quả và ảnh giao diện trước khi cập nhật máy chủ.
- [ ] Đối chiếu lại release trước triển khai; nếu thay đổi thì áp dụng phần tính năng lên baseline mới trước khi rolling deploy.
- [ ] Xác minh HTTPS có nút/API mới, kiểm tra quyền truy cập và dịch vụ sau triển khai; không đổi mật khẩu người chơi thật để thử.
- [ ] Đưa delta nguồn đã kiểm tra vào workspace phát triển mà vẫn giữ các chỉnh sửa của công việc khác; lưu báo cáo.
