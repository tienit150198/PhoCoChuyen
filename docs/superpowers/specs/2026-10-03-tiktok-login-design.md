# Đăng nhập TikTok cùng tài khoản hiện tại

Yêu cầu người dùng: thêm đăng nhập TikTok, giữ đăng nhập tên/mật khẩu và tiến trình hiện tại. Website `https://phocochuyen.io.vn/`, Login Kit Sandbox `7692095542670739474`, callback `https://phocochuyen.io.vn/auth/tiktok/callback`. Production chưa được TikTok duyệt.

## Cách triển khai

Giữ nguyên các endpoint đăng ký/đăng nhập/đổi mật khẩu/đăng xuất hiện có. Thêm OAuth ở máy chủ với quyền duy nhất `user.info.basic`. Giao diện thêm nút TikTok cạnh form thông thường. Tài khoản đã đăng nhập có nút liên kết TikTok. Dùng lại bảng accounts/logins và bản lưu sessions; thêm bảng danh tính TikTok và giao dịch OAuth. Không thay đổi gameplay.

Hai phương án khác đã cân nhắc: thay phương thức hiện tại không đáp ứng yêu cầu; tạo hệ thống bản lưu riêng cho TikTok gây tách tiến trình. Chọn liên kết danh tính vào cùng tài khoản/bản lưu.

## Dữ liệu và quyền

- Khóa ứng dụng, secret và callback lấy từ environment máy chủ. Không trả secret trong bootstrap, JavaScript, log hoặc tài liệu.
- API TikTok lấy open_id và display_name. Không cần avatar, video, nội dung đăng, email hoặc mật khẩu TikTok.
- Danh tính duy nhất theo `(client_key, open_id)`, gắn với một tài khoản. Access/refresh token chỉ dùng trong callback, không lưu lâu dài.
- Luồng OAuth có state ngẫu nhiên, thời hạn 10 phút, ràng buộc với cookie riêng ngẫu nhiên HttpOnly/Secure/SameSite=Lax và phiên nguồn. Giữ nguyên cookie game SameSite=Strict. DB lưu hash state và hash cookie. Callback xác thực trước khi đổi code; mỗi giao dịch chỉ dùng một lần.
- Xóa dữ liệu tài khoản cũng xóa danh tính và giao dịch OAuth liên quan. SQLite và PostgreSQL đều được hỗ trợ.

## Các trường hợp

1. Khách chơi lần đầu đăng nhập TikTok mới: tạo tài khoản TikTok trên chính bản lưu đang chơi, xoay session token như đăng ký hiện tại.
2. Người chơi đăng nhập TikTok đã có tài khoản: mở bản lưu của danh tính đó. Nếu phiên khách hiện tại đã chơi, phải xác nhận chuyển tiến trình sau khi xác minh danh tính; hủy xác nhận giữ phiên cũ.
3. Tài khoản tên/mật khẩu chọn liên kết TikTok: giữ username, password hash, bản lưu và tiến trình. Chặn nếu danh tính đã thuộc tài khoản khác; không gộp hoặc chiếm tài khoản theo tên hiển thị.
4. TikTok mới đăng nhập không có mật khẩu: hiển thị rõ phương thức đăng nhập, không yêu cầu mật khẩu cũ/hiển thị form đổi mật khẩu vốn không thể dùng.
5. Hủy quyền, code sai, state sai, cookie thiếu, hết hạn, lỗi mạng: trở lại trang tài khoản với thông báo an toàn; không đổi bản lưu và không để code/token trong URL trang game.
6. Khi chưa có cấu hình, hiện thông báo phù hợp; đăng nhập thông thường hoạt động độc lập. Bootstrap chỉ công bố enabled/mode.

## Kiểm tra và triển khai

Kiểm thử HTTP và DB bao gồm CSRF, state/cookie/replay/expiry, API lỗi, preserve guest save, link existing local account, login from another device, identity conflict, progress confirmation và account deletion. Chạy lại test_accounts và HTTP/regression liên quan để xác minh đăng nhập hiện tại.

Triển khai overlay chỉ các file thay đổi lên bản release được sao chép từ production đang chạy, kiểm tra hash file trước áp dụng, thêm cấu hình environment và bảng DB, rolling deploy có khóa và đường rollback. Tránh thay release bằng checkout cũ. Nginx và Python không ghi query của callback vào log. Chính sách riêng tư cập nhật tiếng Việt và tiếng Anh. Sau triển khai kiểm tra cả nút thường/TikTok và luồng tới màn hình ủy quyền. Sandbox cần tài khoản Target User của người dùng trước khi thử callback thật; chưa tuyên bố production được duyệt.
