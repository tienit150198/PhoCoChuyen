# Giới hạn tiền phạt và trộm

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Các khoản phạt/trộm bắt buộc phải nhỏ, không vét sạch nguồn tiền và không cưỡng ép thanh lý tài sản.

**Architecture:** Dùng chung giới hạn theo nguồn tiền trực tiếp bị tác động: phạt tối đa 2% và 2.000 xu, trộm/hack/lừa đảo tối đa 1% và 1.000 xu mỗi lần, giữ lại 100 xu hoặc toàn bộ nếu đang có ít hơn. Áp dụng khi thực thu, kể cả cảnh báo được lưu từ phiên bản trước. Không lấy thêm từ tài khoản khác, sổ tiết kiệm, đầu tư hoặc quỹ nghề để trả sự cố cá nhân; các sự cố tại cơ sở chỉ tác động quỹ trực tiếp của cơ sở đó.

**Tech Stack:** Python reducer, PostgreSQL, JavaScript giao diện, unittest, phát hành rolling VPS.

## 1. Tái hiện và sửa mất tiền ngoài hội chợ

- [x] Thêm kiểm thử lỗi trước sửa: tổng tài sản lớn/tiền mặt ít; khoản thu hồi quá lớn; số dư 0/1/99/100/101/1.000/1M; sự cố cũ; đồ bảo vệ; không thay đổi các tài sản khác.
- [x] Tạo helper giới hạn, áp dụng `mishap.py`, `rui.py`, `shop_events.py`, `quay_economy.py`, `incidents.py` và các điểm thu thực tế liên quan.
- [x] Giữ lịch sử cũ hợp lệ, giữ idempotence, đối chiếu sổ thu với số tiền thực trừ.
- [x] Chạy kiểm thử liên quan, rà soát spec rồi chất lượng.

## 2. Phạt hội chợ

- [x] Tái hiện các nhánh raid trừ hết cược rồi phạt thêm, Ông Hai rút cả ngân hàng, cược phóng dao đã trừ trước.
- [x] Áp dụng giới hạn tiền phạt trong `fair.py`, `fair_bm.py`, `fair_hai.py`; hủy ván chưa chơi khi bị bắt, chỉ thu khoản phạt nhẹ. Hoàn phần cược ván bị hủy đã trừ trước đúng một lần, cân bằng sổ ví/thống kê.
- [x] Đồng bộ lời thoại/biên nhận phía máy khách. Không thay xác suất thắng hoặc kết quả thua cược thông thường.
- [x] Kiểm thử reducer/JS liên quan, rà soát spec rồi chất lượng.

## 3. Kiểm tra vận hành và phát hành âm thầm

- [x] Đọc live manifest và thống kê hiệu ứng: 2.0.2; 79 đã áp dụng, 180 đã hủy, không còn pending.
- [x] Kiểm tra timer thu hồi cũ và tắt lịch tự thu hồi, giữ lịch sử để đối chiếu. `mnl-mishap-sweep.timer` đã disabled/inactive.
- [ ] Đối chiếu source mới nhất trước commit và bản đang chạy trước rolling.
- [ ] Đóng gói từ baseline live đã xác minh, xác nhận chỉ các file được duyệt thay đổi.
- [ ] Kiểm tra health HTTP/live, hash runtime, các biên giới hạn trên mã đã triển khai; không tạo người chơi thử ở production.
- [ ] Ghi báo cáo kết quả và trả lời góp ý liên quan khi có bằng chứng; không đổi Có gì mới.

Không tự hoàn xu cho lịch sử cũ khi chưa xác định từng khoản và nguyên nhân; đợt sửa này bảo vệ các lần phát sinh sau triển khai.
