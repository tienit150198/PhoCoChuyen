# Giải Kéo co chó sủa và điều chỉnh Chợ đen

Người dùng xác nhận trò kéo co bằng micro, giải hằng tuần và ít nhất 30 trận hợp lệ.

1. Tính top theo tuần Việt Nam (thứ Hai 00:00), tỷ lệ thắng = thắng / (thắng + thua + hòa); chỉ vé đã chốt có dấu xác minh trận thực sự bắt đầu, cả người và chó máy. Lịch sử trước bản cập nhật không đủ xác minh nên không tính. Không tính hủy/hoàn cược. Bằng tỷ lệ: nhiều thắng hơn, đạt kết quả sớm hơn, khóa ổn định cuối cùng. Dùng tên và quyền riêng tư hiện có.
2. Top 1–5 nhận lần lượt 2.000.000 / 1.000.000 / 500.000 / 250.000 / 100.000 xu cùng danh hiệu theo hạng. Chốt tuần đã kết thúc, xử lý duy nhất một lần trong giao dịch; nhận tiền qua đường live_effects có chống trả trùng. Không trả thưởng các tuần trước khi tính năng ra mắt. Không sửa số liệu lịch sử.
3. Hiển thị bảng top, tỷ lệ, thắng/tổng trận, tiến độ đủ 30 trận, thời điểm chốt, các mức giải và kết quả tuần trước ngay trong sảnh kéo co. Giữ màn chơi micro hiện tại.
4. Tăng nhẹ xác suất cơ sở xóc đĩa 48,5% → 49%, lô tô 45,5% → 46%, vé cào 50% → 51%; kiểm tra ranh giới thắng và kỳ vọng trả thưởng. Các trò kỹ năng giữ cơ chế kỹ năng. Theo yêu cầu bổ sung: bỏ toàn bộ phí 10.000 xu và trấn lột do từ chối tại cổng; lệnh trang cũ là no-op, giữ công an và trại giam.
5. Kiểm thử PostgreSQL thật cục bộ, tái chạy chốt giải và nhận thưởng, biên tuần, quyền ẩn tên, đồng hạng, thiếu trận, dữ liệu cũ. Kiểm thử UI điện thoại, XML của 30 tranh, tương thích nhiệm vụ; review rồi đóng gói và rolling deploy khi có kết nối SSH hợp lệ.

API dự kiến: `/api/dogbark` thêm `competition` gồm `week`, `ends`, `minimum`, `prizes`, `rows`, `me`, `previous`. Mỗi hàng công khai gồm `rank`, `name`, `wins`, `played`, `rate` (0–100), `reward`, `title`; không lộ sid. `me` gồm thêm `eligible`, `remaining`, `visible`. Danh sách `prizes` gồm `rank`, `coins`, `title`. `previous` có `week`, `rows`.
