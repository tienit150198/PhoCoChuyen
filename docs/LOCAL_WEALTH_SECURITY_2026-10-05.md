# Phí an ninh và thiệt hại theo tổng tài sản

Người dùng đã yêu cầu sửa xong deploy. Không tạo thông báo mới. Kết quả deploy lưu riêng trong output/release-security-percent.

Tổng tài sản dùng để định giá gồm ví dương, ngân hàng và tiết kiệm, quỹ tiệm tự sở hữu, vốn/két các quầy, nhà đang sở hữu theo giá hiện tại, xe theo giá bán lại, vàng và coin theo giá hiện tại. Không tính quỹ của nơi làm thuê hay nhà ở nhờ của người khác. Không tự bán tài sản để trả phí.

Hệ số chi phí: `1 + max(0, tổng tài sản − 10.000) / 100.000`, tối đa 1.000 lần; làm tròn lên. Các phương án miễn phí vẫn miễn phí.

| Tổng tài sản | Bảo vệ cơ bản / 10 phút | Tăng cường / 10 phút |
|---:|---:|---:|
| ≤ 10.000 | 3 xu | 7 xu |
| 100.000 | 6 xu | 14 xu |
| 1.000.000 | 33 xu | 77 xu |
| 10.000.000 | 303 xu | 707 xu |

- Báo giá quầy giữ trong ngày game, bảo vệ tài sản Sổ tiệm giữ theo ca; phần vận hành đã trôi qua luôn thanh toán theo báo giá trước đó, rồi mới đổi báo giá.
- Tình huống chủ tiệm/quầy chốt cơ sở tài sản theo báo giá ngày/ca, tránh lệch số tiền giữa một lần đồng bộ offline và nhiều lần tải online. Bảo kê chốt giá khi tình huống xuất hiện; lời thoại, lựa chọn, điều kiện đủ tiền, biên nhận và số tiền thực trừ đều dùng cùng giá.
- Vụ trộm mới tại quầy/tiệm và tiền bảo kê chọn ngẫu nhiên nguyên 1–20% tổng tài sản, chốt một lần phía server và lưu cùng sự kiện. Trộm tại quầy/tiệm không trừ quá quỹ/két hiện có; nhờ hỗ trợ, giữ chứng cứ giảm thiệt hại còn một phần ba. Phí bảo vệ định kỳ giữ biểu phí trên. Các tình huống khác và sự kiện cũ giữ cách tính trước. Camera, khóa/két và chuông vẫn giữ hiệu lực bảo vệ. Các phương án cũ và biên nhận đã phát sinh không bị tính lại.
- Trộm/hack cá nhân mới chọn 1–20% tổng tài sản khi cảnh báo xuất hiện. Trộm chỉ trừ ví; hack chỉ trừ tài khoản thanh toán; giữ sàn 300 xu tiền sử dụng được và không tự bán nhà/xe/đầu tư. Tổng thất thoát cá nhân trong tháng không vượt 20% cơ sở tài sản của vụ đang tính, sau đồ bảo vệ và tiền thực có. Sự kiện cũ giữ trần cũ. Mỗi khoản thiệt hại tối đa 1 tỷ xu theo giới hạn sổ giao dịch hiện có.

## Kiểm chứng trước khi đổi sang tỷ lệ ngẫu nhiên

- 179 kiểm tra Python đạt: định giá, biểu phí, trừ tiền đúng báo giá, không thu lại, online/offline, bù lỗ/thuế, bảo kê, hóa đơn cũ và các quy tắc bảo vệ.
- Kiểm tra giao diện kinh tế và tình huống chủ tiệm đạt; cú pháp JS đạt; `git diff --check` trên các file liên quan đạt.
- Một bài lưu PostgreSQL (`tests.test_incidents.Saves.test_round_trip_store`) chưa chạy được do thiếu `TEST_DATABASE_URL` local. Không kết nối production để chạy test.
- Định giá trên bản lưu cơ bản local: khoảng 0,0046 ms/lần trong 10.000 lần gọi; đây không phải số đo tải production. Không thêm API, polling hay truy vấn database cho định giá.

## Lưu ý cho lần deploy được cho phép sau này

Có metadata báo giá mới trong tình huống và lịch sử. Reader cũ có kiểm tra tập khóa chính xác sẽ không đọc được các bản lưu này. Cần rollout reader tương thích trước writer hoặc dừng toàn bộ writer cũ trước khi bật bản mới; rollback phải dùng reader đã biết metadata mới. Các mức thuế local 4%/7% và thưởng ô ăn quan 500/50 vẫn đang chờ deploy cùng các thay đổi này.

## Kiểm chứng và triển khai tỷ lệ ngẫu nhiên

- Kiểm tra mới bao phủ hai đầu 1% và 20%, ngẫu nhiên đủ 20 mức, tải lại, chống xử lý lặp, giảm thiệt hại bằng đồ bảo vệ, chỉ trừ nguồn tiền đúng, không bán tài sản và reader tương thích. Kết quả cuối lưu trong output/release-security-percent.
- Triển khai hai bước: reader tương thích (chưa tạo báo giá mới), sau đó bật writer mới khi toàn bộ worker đọc được schema mới. Rollback dùng bản compat; không quay về reader cũ chưa hiểu thuế 4% và báo giá.
