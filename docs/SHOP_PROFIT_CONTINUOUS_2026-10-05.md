# Tiệm hoạt động liên tục và tăng lợi nhuận

Trạng thái: sửa tại máy, chưa deploy. Người dùng xác nhận tăng thêm 40% lợi nhuận hiện tại, không đặt biên lãi bằng 40% doanh thu. Phi công thay đổi cả số chuyến và thưởng; xem `PILOT_VARIATION_2026-10-05.md`.

## Hành vi

- Quầy riêng bỏ nút tạm dừng kinh doanh. Chủ vẫn có thể tự đứng quầy, tự giao hoặc thuê nhân viên; nút “Rời quầy” chỉ kết thúc lượt của chủ.
- Khách/đơn tiếp theo tính thời gian đến trong lúc chủ đang phục vụ. Không cộng thêm một khoảng chờ từ đầu sau mỗi lần giao xong. Giá bán cao và thiết bị vẫn ảnh hưởng tốc độ khách/đơn.
- Nhân viên Sổ tiệm tiếp tục làm khi chủ khép ngày, đổi nghề hoặc offline. Thuê khi ngày đã khép cũng bắt đầu làm. Nhân viên thực sự nghỉ, bệnh, đình công hoặc chờ xử lý sự cố vẫn được tôn trọng.
- Hết hàng hoặc không đủ tiền vận hành thì chờ bổ sung. Không tự mua hàng hay lấy tiền cá nhân. Thời gian tiệm cũ đã đóng/tạm dừng không sinh đơn hồi tố.

## Cách cộng lãi

Quầy riêng cộng 40% lãi thực hiện sau giá vốn món đã giao, thuế/phí thực trả, chi phí vận hành, tiền thối dư và các khoản lỗ/phạt chưa bù. Phần chi phí chưa bù chuyển sang đơn sau; phần lẻ xu được giữ. Hàng nhập chưa bán không tạo thưởng. Doanh thu và giá khách trả giữ nguyên; khoản cộng thêm vào két có trường riêng `profit_bonus` và được tính vào lãi công khai.

Sổ tiệm cộng 40% phần lãi dương của đơn riêng nhân viên đã hoàn thành sau giá vốn, lương và vật tư, trước khoản thuế kết kỳ hiện có. Khoản thêm được ghi riêng vào sổ thu chi. Đơn khách người chơi do nhân viên phục vụ chỉ được cộng khi thanh toán trong cùng giao dịch xác nhận biên nhận. Không nhân lương, thưởng nghề, tiền góp vốn hoặc tiền hoàn hủy đơn.

Các khoản thưởng là lợi nhuận từng đơn theo chi phí đã ghi nhận; không bảo đảm tổng lãi cả kỳ tăng đúng 40% sau mọi chi phí/lỗ có thể phát sinh trong tương lai.

## Tương thích và kiểm chứng

- Dữ liệu thưởng bổ sung là trường tùy chọn; phiếu thu, doanh thu và giá menu cũ giữ cấu trúc.
- Có kiểm thử phần lẻ, đơn lỗ, phạt chưa trả, vốn/nhập kho, thanh toán một lần, thời gian tạm dừng cũ và tính tương đương giữa nhiều lần cập nhật với cập nhật sau offline.
- Quầy và phi công: 234 kiểm thử qua, nhật ký `output/shop-pilot-final.log`.
- Sổ tiệm, đơn khách, vận hành và thanh toán PostgreSQL: 132 kiểm thử qua (`tests.test_workplace_business`, `tests.test_player_service_tasks`, `tests.test_operations`, `tests.test_work_visits`).
- Ba bộ kiểm thử giao diện quầy, Sổ tiệm, phi công qua; kiểm tra cú pháp và diff không có lỗi.
- Trình duyệt thật: `output/playwright/shop-update/report.json`, ảnh quầy/phi công ở 320, 390 và 430 px; thao tác chọn món, tính tiền, giao khách. Không tràn ngang, không có lỗi JavaScript trong luồng đã kiểm.

Chưa tăng phiên bản, chưa phát hành “Có gì mới”, chưa deploy.
