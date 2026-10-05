# Người làm thuê không thấy vốn chủ quầy

Trạng thái: xác định nguyên nhân; chưa thay đổi cơ chế tiền, chưa deploy.

## Bằng chứng

Đọc PostgreSQL production bằng transaction mặc định read-only và statement timeout 5–8 giây. Không sửa dữ liệu người chơi.

Trong đoạn chat liên quan ngày 04/10/2026, người làm thuê nói thiếu quỹ nhập hàng; chủ quầy được hướng dẫn Quầy của bạn → Vốn, sau đó báo đã góp. Người làm thuê tiếp tục thấy quỹ bằng 0. Tên tài khoản chủ trong chat là Bạch Du Dương, tên nhân vật trong save đã đổi. Không lưu thông tin đăng nhập hoặc bản sao save ở tài liệu này.

## Nguyên nhân ở mã

- `game/quay.py`, nhánh `jr_quay_fund`: trừ ví chủ và cộng `journey.quay.stalls[].fund` của chủ.
- `game/quay_hire.py`, `accept`: ghi mã ca, nghề, lương, tên quầy và thời hạn vào `journey.quay.shift` của người làm; không gắn ngân quỹ hoặc kho của chủ vào ca.
- Người làm thực hiện công việc bằng `careers[trade]` trong save của chính mình. Thanh quỹ và nhập hàng lấy `careers[trade].money`, không phải `stalls[].fund` của chủ.
- `game/quay.py`, `on_shift` cùng `game/quay_hire.py`, `flush`: chỉ chốt số việc/lương và phần doanh thu chủ nhận cuối ca. Chưa có cơ chế chủ cấp vốn nhập hàng trong ca.

Vì vậy đây là hai quỹ tách biệt trong thiết kế ca thuê người chơi hiện tại, không phải chỉ cache giao diện. Không nên sửa bằng cách sao chép số vốn chủ lên quỹ người làm: cách đó tạo tiền hoặc cho phép dùng tiền chủ vào tài sản riêng.

## Phạm vi cần xử lý tiếp

Nếu nối vốn chủ vào ca thuê, cần một ngân quỹ và kho dành riêng cho ca, giao dịch chi của chủ và công việc của người làm phải nguyên tử/idempotent; chủ bổ sung vốn hiện lên bên làm thuê; không trộn ví/quỹ/tài sản riêng của người làm. Chốt ca, bỏ ca, hết hạn, sang nhượng quầy, chi đồng thời và nhân viên offline phải hoàn/tất toán phần còn lại đúng một lần. UI phải phân biệt quỹ ca thuê và quỹ nghề riêng. Lương đã giữ chỗ không được tính thêm thành vốn nhập hàng hoặc trả hai lần.
