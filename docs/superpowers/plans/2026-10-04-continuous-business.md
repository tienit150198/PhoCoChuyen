# Quầy vận hành liên tục và nâng cấp tốc độ — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for the independent backend/UI/upgrade domains; keep shared engine and server integration with the parent.

**Goal:** Quầy riêng và nhân viên Sổ tiệm của từng nghề tự vận hành cả khi chủ offline tới khi hết hàng hoặc hết tiền lương; chủ không thuê người phải tự phục vụ/giao hàng; menu không giới hạn lựa chọn, tự định giá, có kinh tế giá–khách–đánh giá; đồ nâng cấp tăng tốc các nghề.

**Architecture:** Tính hoạt động bằng thời gian máy chủ trong giao dịch bản lưu có revision/CAS, không dựa đồng hồ trình duyệt. Kho quầy hữu hạn, sổ doanh thu/chi phí rõ, cursor chống trả trùng; bootstrap tính bù thời gian vắng mặt. Quầy cũ kích hoạt từ lúc đọc/lệnh đầu tiên sau cập nhật, không truy lĩnh thời gian trước đó. Giá so với giá trị từng món, tăng giá quá cao làm cầu giảm đủ mạnh, tránh lợi nhuận vô hạn.

**Tech Stack:** Python/PostgreSQL, reducer hiện có, JavaScript/canvas/SVG/CSS. Chỉ local; không deploy, không ghi “Có gì mới” trước lệnh người dùng.

## Quyết định và ranh giới

- Người dùng đã chọn nhân viên làm cả lúc offline, dừng khi hết hàng hoặc tiền trả lương.
- Người dùng đã xác nhận áp dụng cho cả Quầy riêng và Sổ tiệm của từng nghề. Sổ tiệm dùng đơn nhân viên riêng, giữ nguyên công việc thủ công đang dở; đóng ca thì đội dừng.
- Số quầy hiện đã không giới hạn, giữ phân trang. Bỏ giới hạn 4 món, mở rộng danh mục; không nhầm phân trang/preview với giới hạn sở hữu.
- Vốn và két quầy trả hàng/lương/phí. Không tự rút ví hoặc ngân hàng để cứu quầy thiếu vốn.
- Chốt thời gian theo cấu hình cũ trước khi đổi giá/menu/nhân viên. Không vừa bán tự động theo thời gian vừa được trả lại theo ngày sống.
- Không có nhân viên thì không tự sinh doanh thu khi đóng ca. Chủ có thể đứng quầy và nhận đơn/giao hàng liên tiếp.
- Các ca thuê người chơi giữ sổ escrow hiện có; không coi người chơi được thuê là NPC chạy offline.
- Góc nhìn chủ sau quầy, khách trước mặt; đường giao hàng nhìn từ người lái. Giữ thao tác bàn phím và điện thoại, giảm chuyển động.
- Nâng cấp là vật liệu/linh kiện trả bằng xu game, mô tả tác dụng cụ thể; máy và giao hàng tăng tốc theo giá trị máy chủ, giữ các nhiệm vụ/bộ đếm đang dở tương thích.

## Phân công và kiểm tra

### 1. Backend quầy và menu

Files: `game/quay.py`, `game/quay_self.py`, `game/quay_economy.py`, new `game/quay_business.py`; tests quay và tests kinh tế liên tục mới.

- [x] Red: cùng khoảng thời gian chỉ trả một lần; nhiều lần tải trang bằng một lần offline; không nhân viên không tự bán; hết hàng/tiền lương dừng; đổi giá không tính ngược; chọn toàn bộ menu hợp lệ.
- [x] Implement timestamp cursor, kho thật, trả lương và chi phí, thống kê doanh thu/lãi, phản hồi giá và đánh giá. Bỏ đóng cửa vì chủ vắng và giới hạn ngày ở quầy mới.
- [x] Red/green cho đóng ca không tặng doanh thu chủ chưa làm; luồng chủ tự làm/ship liên tục, giữ bản lưu cũ và ca thuê người chơi.
- [x] Mô phỏng 8 ngành và 3 quy mô, mức giá thấp/vừa/cao: giá cao giảm khách/đánh giá, giá thấp giảm lãi mỗi món, số dư không âm, không thu trùng phí.

### 2. UI quầy

Files: `public/js/v4/quay.js`, `quay-scene.js`, `quay-ride.js`, `public/css/quay.css`; tests JS mới.

- [x] Thẻ trạng thái nhân viên đang bán, kho còn, lý do dừng, tiền lương/lãi; nút vào xem tiệm tách khỏi tự đứng quầy.
- [x] Menu tìm/chọn nhiều, giá nhập số trực tiếp, giá vốn/lãi ước tính và dự báo phản ứng khách; không reset bản nháp khi refresh.
- [x] Nhập hàng có xem tiền trước, pause/resume, cập nhật hoạt động qua refresh có giới hạn khi dialog mở.
- [x] Cảnh sau quầy và giao hàng từ người lái có khách/đơn thực từ server; không tạo số tiền hay đơn giả ở client.

### 3. Nâng cấp nghề

Files: common gear module mới, `game/engine.py`, metadata/content, các adapter timer được khảo sát; UI mua thiết bị và delivery adapter.

- [x] Danh mục có tác dụng cho đủ 41 nghề; mua nguyên liệu/linh kiện tăng tốc theo bậc có lợi ích giảm dần, thanh toán/idempotency server.
- [x] Test thật thời gian/thao tác trước–sau, máy đang chạy không bị thay công thức giữa chừng; delivery server và hình ảnh cùng hệ số.
- [x] Gắn lối vào dễ thấy trong nghề/Sổ tiệm, hiển thị đã lắp và hiệu quả trước mua.

### 4. Tích hợp và xác minh (parent)

Files: `game/engine.py`, `server.py`, storage tests/HTTP tests, guides/i18n.

- [x] Trước reducer: `quay_business.settle(s, now=server_now)`; internal sync action và on-load command có CAS; không mutate public projection.
- [x] Test PostgreSQL hai tab/cùng request/retry, offline xuyên lần khởi động, bản lưu cũ, nhập/export.
- [x] Kiểm tra browser desktop/390px: thuê người, thoát/quay lại, kho cạn, nhập thêm, tự bán/ship, định giá, mua thiết bị.
- [x] Review độc lập và báo kết quả local. Không chạy deploy, không sửa thông báo phát hành.


## Kết quả chốt local

Đã hoàn thành cả hai cơ chế nhân viên theo xác nhận của người dùng. Sổ tiệm dùng `game/workplace_business.py`, chốt 1.024 đơn mỗi lần và hiển thị trạng thái đang cập nhật nếu còn backlog. Hai lỗi rà soát cuối về tiền hoàn/escrow và tiền phạt chưa trả đã có kiểm thử hồi quy. Chi tiết và giới hạn hiệu năng tại `docs/LOCAL_BUSINESS_2026-10-04.md`. Không deploy, không tăng phiên bản, không đăng thông báo.
