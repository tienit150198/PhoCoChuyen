# Cân bằng hội chợ — 05/10/2026

Yêu cầu chốt: mỗi 30 phút thực chỉ một trò may rủi được ưu đãi; 70–50% theo mức cược ở trò ưu đãi, 55–30% ở trò còn lại. Phóng dao và ô ăn quan giữ kỹ năng.

- Vòng xoay server chung: lô tô → bầu cua → chiếu trong → vé cào → ném vòng. Chọn bằng timestamp chia 1.800 giây, không tạo timer, polling, truy vấn SQL hoặc công việc nền. Mốc chuyển là phút 00/30.
- Nội suy theo thứ tự các mức cược của từng trò; tổng cược nhiều mặt, nhiều tờ và cược phụ đều tính. Chỉ mức thấp nhất đạt mức cao nhất. Ném vòng miễn phí dùng mức cao nhất của khung.
- Giữ giảm theo lãi ngày 2.000–5.000 xu, tối đa 15 điểm %, không vượt đáy của khung ưu đãi/thường. 10 lượt liên tiếp đầu chưa giảm do lặp; từ lượt 11 giảm 1 điểm %/lượt tới 40%. Nếu tỷ lệ ban đầu dưới 40% thì không tăng ngược. Đổi trò hoặc nghỉ hơn 180 giây đặt lại chuỗi.
- Vé cào: trọng số giải 1×/2×/3×/5×/10×/20×/50× là 675/230/60/25/8/1/1 trên 1.000 vé có giải. Giải gồm hoàn vốn. Trung bình 1,59× trên vé có giải (trước 2,46×). Năm trong tám mức vé có kỳ vọng trả dưới giá vé ngay cả lúc ưu đãi, trước giảm theo lãi/lặp. Vé đã mua giữ nguyên ô số và khoản trả.
- Trên 50.000 xu lãi ròng hội chợ trong ngày Việt Nam, kiểm tra sau ván cược bầu cua/xóc đĩa/vé cào hoặc Kinh thành công. Mỗi người tối đa một lần kiểm tra/30 phút, kể cả lần không bị bắt. Xác suất bắt 70%; thu 30% ví sau khi thanh toán ván, làm tròn xuống xu. Ghi khoản thu riêng vào Sổ ví, giảm lãi ròng và điểm tiền hội chợ. Không trừ khi chỉ tải trang, offline, chơi phóng dao/ô ăn quan/ném vòng. Không thu thêm cùng lượt đã bị bắt ở chiếu trong.
- Biên nhận thu tiền hiện riêng tại quầy; không thay hình xúc xắc, ô vé hay kết quả thao tác. Request lặp dùng idempotency của PostgreSQL để tránh trừ hai lần.
- Ván ném vòng lưu xác suất tại lúc phát vòng; lô tô giữ seed tại lúc mua. Qua mốc 30 phút không đổi ván đang chơi.

## Triển khai

Đóng gói trên release đã chạy `1.7.15-fair-skill-final-20261005192026`, chỉ thay `game/fair.py`, `game/fair_scratch.py` và biên nhận trong `public/js/v4/fair.js`, kèm kiểm thử/tài liệu. Không gom thay đổi khác trong workspace.

Phải đưa reader tương thích lên game và live trước: chấp nhận `wealth_check_at` tùy chọn và xác suất vòng 400/1000. Reader này giữ cách tạo ván của bản trước. Sau khi mọi worker đọc được save mới, mới bật logic mới ở game; giữ live ở reader tương thích để không restart socket lần hai. Rollback về reader tương thích, không về release cũ chưa biết timestamp.

Không thêm thông báo “Có gì mới”. Biên nhận là thông tin giao dịch cho người bị thu tiền.
