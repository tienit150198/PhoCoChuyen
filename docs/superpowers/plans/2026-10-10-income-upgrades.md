# Nâng cấp tăng thu nhập — 10/10/2026

**Mục tiêu:** Cho người chơi đầu tư xu để nhận thêm khách, kiếm thêm từ công việc và tăng đơn online. Không tăng tiền từ tải lại trang hoặc thay đổi các khoản chuyển tiền giữa người chơi.

**Thiết kế:** Giữ ba bậc tốc độ hiện có. Thêm các chuỗi thiết bị độc lập, mua bằng quỹ nghề và phải mua bậc trước: đón khách +15/30/50% (120/280/600 xu), chất lượng +10/20/30% (100/260/560 xu), online +25/50/100% (140/320/680 xu, chỉ tám nghề có quầy online). Đón khách tăng nhịp đơn của nhân viên và khách quầy tự mở; chất lượng tăng tiền công hoàn thành và lãi dương đơn nhân viên/quầy; online chỉ có tác dụng khi bật bán online ở quầy tự mở. Bậc cao thay thế bậc thấp trong cùng nhánh. Giao diện tách các nhóm, nêu điều kiện và phạm vi.

**An toàn kinh tế:** Tính hiệu quả từ quyền sở hữu trên server; đơn cần hàng thật, trả lương/phí/thuế như cũ. Đồng bộ thu nhập cũ trước khi mua; không đổi hạn của đơn đang chờ. Bản lưu cũ không có thiết bị mới giữ nguyên thu nhập. Lưu cache hiệu quả ở quầy tương tự tốc độ hiện có, kiểm tra miền giá trị. Mua đồ mới khiến rollback về bản không biết ID mới cần migration.

**Feedback kiểm tra trực tiếp:** #325 hỏi nhạc và âm lượng; đã có Cài đặt → Âm thanh, nhạc theo nhóm nghề. #326 muốn tự nhận kho do mỏi thao tác đếm; cần giảm thao tác kiểm đếm mà vẫn giữ kiểm nhận thiếu/hỏng. #310 trong đợt trước nói giá bán/thu nhập thấp. Không coi các phản hồi đã đọc là đã triển khai.

## Các bước

- [x] Test hành vi mua, tiền tăng trên đơn thực, nhịp khách/online, hàng hết, đọc lại, tương thích lưu và giao diện.
- [x] Module `game/income_gear.py`: catalogue, quyền sở hữu, tác dụng và tính phần thưởng; đăng ký ở content.
- [x] Tích hợp engine, workplace_business, quay_business, quay_self; giữ sổ tiền và các dự báo khớp công thức.
- [x] Tách nhóm trên `public/js/v4/work-equipment.js`; hiển thị tác dụng và điều kiện mua.
- [x] Chạy test kinh tế liên quan, kiểm tra JavaScript và kiểm tra giao diện trên trình duyệt.
- [x] Ghi kết quả, phạm vi feedback còn lại và trạng thái phát hành trong `docs/INCOME_UPGRADES_2026-10-10.md`.

## Điều chỉnh sau review

Chặn mua thiết bị khi còn đơn cũ chưa quyết toán; dùng cùng thời điểm server với lần settle trước lệnh mua. Thêm thưởng vào các luồng hoàn thành đặc biệt, không thưởng cọc trước khi giao. Thưởng ở nghề làm tròn lên để bậc 1 không mất tác dụng trên đơn nhỏ, ghi rõ cách làm tròn và giới hạn tốc độ; cố định lương/bài học ngoài phạm vi. Thông báo cuối lệnh ghi riêng phần xu nhờ thiết bị. Review độc lập đã kiểm tra các đường tính tiền và tương thích; 436 tests đạt (1 bỏ qua), các giới hạn môi trường ghi trong báo cáo.
