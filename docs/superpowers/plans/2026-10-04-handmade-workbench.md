# Handmade workbench implementation plan

**Goal:** Nâng Xưởng DIY hiện có thành trải nghiệm trực tiếp, ưu tiên thao tác đo/cắt/may và UI điện thoại.

**Architecture:** Một dialog bàn thủ công độc lập, tránh render trang cha làm mất pointer capture. Các thao tác và bản nháp ở trình duyệt; thành phẩm, chi phí và biên nhận do lệnh game/PostgreSQL hiện có lưu. Tóm tắt công đoạn không được xem là bằng chứng chống gian lận.

**Tech stack:** JavaScript ES modules, SVG, Pointer Events, CSS, Python reducer, PostgreSQL.

## Thiết kế

Người chơi đang nghỉ ở nhà, tự làm một món kỷ niệm với nhịp thong thả. Chọn hướng thao tác có vạch hướng dẫn; phù hợp điện thoại hơn mô phỏng vật lý tự do và vẫn cho cảm giác tự làm. Không dùng đếm ngược hay phạt làm hỏng vật liệu.

Bàn cắt là phần trung tâm; chất liệu vải kem, bàn gỗ, thảm xanh, phấn trắng, chỉ hồng. Mỗi bước chỉ hiện dụng cụ đang cần. Thước, vạch cắt, mũi kim, bông nhồi và dấu trang trí đều gắn lên chính món đồ. Dùng font Be Vietnam Pro có sẵn, khoảng cách theo 4/8 px, bề mặt giấy/vải phân lớp nhẹ, nút tối thiểu 44 px.

Món may đầu tiên mặc định là gấu bông: đo 24×30 cm → cắt → may → nhồi bông → trang trí. Người chơi kéo thước và đi theo đường cắt/may; có thao tác bàn phím tương đương, làm lại từng bước. Gốm, vòng tay, thiệp có công đoạn tương ứng. Kệ cũ vẫn đọc được; thành phẩm mới lưu vị trí trang trí để nhìn lại.

## Công việc

- [ ] Thêm kiểm tra thất bại trước: hoàn thành công đoạn, dữ liệu lỗi, thanh toán một lần, kỷ niệm cũ.
- [ ] Thêm catalog và validator `game/craft_work.py`, nối vào `game/outings.py`; dữ liệu mới không buộc migration database.
- [ ] Bàn thao tác `craft-workbench.js`, helpers gesture, CSS riêng; bản nháp theo tài khoản và loại món, giữ khi đóng hoặc lưu thất bại.
- [ ] Nút mở bàn từ outings; SVG thành phẩm và dấu trang trí trên kệ; không thay salon/nail.
- [ ] Kiểm tra gesture không nhảy qua đường dẫn, thứ tự bước, draft, keyboard, payment failure và hành vi mobile.
- [ ] Rà soát độc lập, chạy gói phát hành trên PostgreSQL riêng, kiểm tra tương thích nghề và deploy.

## Giao thức lưu

`jr_out_craft {kind,color,pattern,pay,work:{v:1,steps:[...],size:[w,h],marks:[[x,y],...]}}`.

Recipe teddy: measure/cut/sew/stuff/decorate; pot: shape/glaze/decorate; bracelet: thread/beads/decorate; card: fold/decorate. Kích thước tương ứng 24×30, 20×24, 18×1, 15×20. Dấu trang trí 1–12, tọa độ hữu hạn 0–1. Kiểm tra mọi dữ liệu trước thanh toán. Legacy không có work vẫn đọc và nhận cho ba loại cũ; teddy bắt buộc work.
