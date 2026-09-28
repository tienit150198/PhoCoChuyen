# Kết quả kiểm thử v0.3

## Luật game và mã nguồn

`artifacts/python-test-report.json` và `python-tests.log` ghi lại lần chạy thực tế: **457 kiểm thử Python đạt**, không lỗi hoặc thất bại. Môi trường kiểm thử dùng Python 3.13. Runtime nhắm tới Python 3.11 trở lên; chưa chạy riêng trên mọi phiên bản Python và mọi hệ điều hành.

Kiểm cú pháp các module JavaScript bằng `npm run check`; đầu ra ở `artifacts/javascript-syntax.log`. Đây là kiểm cú pháp, không phải thay thế thử luồng UI.

## Giao diện

Ba báo cáo ghi tổng **41 nhóm kiểm tra luồng**:

| Báo cáo | Nhóm đạt | Phạm vi |
|---|---:|---|
| `browser-test-report.json` | 13 | Bốn nghề gốc, sự kiện, chat, review, trang trí, album và lưu game |
| `browser-operations-report.json` | 12 | Nhân viên, chi phí, mặt bằng, bảo hiểm, trộm, công an và thu hồi |
| `browser-v03-report.json` | 16 | Ba nghề mới, bốn họ trò nhỏ, mục tiêu, khu phố, tổng kết, màn hình dọc và bản lưu v3 |

Các luồng trên không có lỗi JavaScript chưa được bắt. Desktop dùng Chromium; màn hình dọc mô phỏng viewport 390×844, không phải iPhone vật lý.

### Phương thức thực thi và giới hạn

Môi trường chặn điều hướng Chromium trực tiếp tới HTTP local. Bộ thử đưa cùng HTML/CSS/module vào trang thử `about:blank`, rồi chuyển các yêu cầu bằng cầu nối trong tiến trình kiểm thử tới **HTTP server và SQLite thật**. Cơ chế này kiểm DOM, sự kiện bấm, render và luật API, nhưng **không kiểm chính sách mạng/CSP khi browser điều hướng trực tiếp**.

Các nhánh công an, bảo hiểm, sửa đồ và hóa đơn bảy ca có dữ liệu kiểm thử có kiểm soát. Chúng kiểm tính đúng của nhánh và chống nhận trùng, không phải bằng chứng phân bố xác suất hoặc cân bằng dài hạn.

## Gói ZIP sạch

Chạy `python scripts/verify_package.py <zip> --report <tệp-báo-cáo>` để giải nén vào thư mục mới, kiểm CRC, đường dẫn và hash trong MANIFEST, bật server với SQLite rỗng, đọc asset, thực hiện lệnh và xuất bản lưu. Báo cáo kiểm gói cuối được cung cấp riêng bên cạnh ZIP để không tạo vòng tham chiếu hash của chính nó.

## Chưa kiểm

Chưa thử model LLM thật, Safari/iPhone thật, Docker build, tải nhiều người dùng, cân bằng kinh tế 100 ngày hoặc giữ chân người chơi. Không có multiplayer hoặc review người dùng thật. Các con số nội dung không chứng minh game sẽ chắc chắn thu hút; cần thử chơi với người dùng và tiếp tục chỉnh nhịp.
