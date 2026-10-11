# Kiểm tra phạt và trộm — 11/10/2026

## Yêu cầu

Người chơi báo có lần bị phạt mất sạch tiền. Chủ game yêu cầu kiểm tra tiền phạt/trộm và giảm xuống mức thấp, không lấy hết.

## Nguyên nhân đã xác định

- `mishap.apply_fx` cho phép khoản thu hồi theo lịch lấy từ tài khoản thanh toán, tiền gửi không kỳ hạn/kỳ hạn, đầu tư, ví và quỹ nghề. Không có trần nhỏ theo nguồn tiền thực tế.
- Các cảnh báo trộm/hack tính phần trăm trên tổng tài sản rồi chặn ở toàn bộ tiền trong nguồn bị trừ. Sở hữu nhà hoặc tài sản lớn nhưng ví nhỏ có thể làm mất toàn bộ ví.
- Nhánh công an tại hội chợ vừa thu cược, vừa phạt theo ví; kiểm tra tài sản có thể lấy thêm từ ngân hàng. Ông Hai phạt 30–50% ví cộng ngân hàng.
- Quầy hàng và sự cố nghề có các cách tính theo tổng tài sản tương tự.

## Hợp đồng mới

- Phạt: tối đa 2% số dư nguồn trực tiếp bị phạt và 2.000 xu mỗi lần.
- Trộm/hack/lừa đảo/bảo kê: tối đa 1% số dư nguồn trực tiếp bị tác động và 1.000 xu mỗi lần.
- Giữ lại ít nhất 100 xu; nguồn đang dưới mức này không bị trừ thêm. Các đồ bảo vệ tiếp tục giảm tiền mất.
- Không thanh lý sổ tiết kiệm, đầu tư, Mây Coin hoặc truy đòi sang nguồn tiền khác.
- Áp dụng khi thực thu, kể cả cảnh báo cũ. Lịch sử cũ vẫn đọc được; không sửa hồi tố số tiền đã ghi.
- Ván bị công an dừng không bị tịch thu cả cược. Kết quả thua cược thông thường không thuộc thay đổi này.

## Vận hành

Đọc trực tiếp production 2.0.2: 79 hiệu ứng mishap đã áp dụng, 180 đã hủy, không có pending. Đã tắt `mnl-mishap-sweep.timer`, xác nhận disabled/inactive; giữ lịch sử. Không sửa bản lưu hoặc tự hoàn tiền lịch sử trong đợt này.

## Bằng chứng kiểm thử

Các kiểm thử tái hiện trước sửa phát hiện khoản thu hồi lấy 32.838.237 xu, trong khi giới hạn mong muốn là 2.000; cảnh báo cũ lấy 900 thay vì 9 xu; trộm két lấy 1.000 thay vì 10 xu. Kết quả sau sửa và kiểm thử triển khai được ghi trong báo cáo phát hành sau khi xác minh.

- 84 kiểm thử lõi về ngân hàng, trộm, quầy và rủi ro đều qua; gồm kiểm thử giao diện hack tài khoản với dữ liệu thực từ reducer.
- 34 kiểm thử đời thường và chuyện tình cảm qua. Tám tình huống lừa đảo được kiểm ở tám mức số dư; trước sửa có 40 trường hợp vi phạm giới hạn.
- 90 kiểm thử sự cố và giới hạn qua; kiểm thử lưu DB còn lại được chạy riêng với PostgreSQL và qua. Lượt đầu thiếu biến môi trường DB, không phải lỗi ứng dụng.
- Hội chợ: 89 kiểm thử tập trung gồm PostgreSQL và 124 kiểm thử chức năng qua (mỗi bộ có một skip vì thiếu fixture ngân hàng cũ; bộ mới có ca ngân hàng giàu). 32 kiểm thử UI và hai script biên nhận qua. Không cộng các bộ thành số test độc lập vì có phần trùng nhau.
- Rà soát spec độc lập: 31 kiểm thử lõi và 63 trường hợp tình huống nghề bổ sung qua; kiểm tiền thực trừ, biên nhận và validator.
- Bộ nghề liên quan: 292 kiểm thử có PostgreSQL qua. Bốn script UI quầy qua; các file JavaScript thay đổi kiểm tra cú pháp thành công.
- Lượt cuối sau sửa các phát hiện review: 93 kiểm thử qua, gồm lưu PostgreSQL, biên nhận, giao thông, validator 2.0.2 và khoản phạt kiểm toán nghề. Rà soát chất lượng độc lập xác nhận không còn lỗi nghiêm trọng/quan trọng trong diff đã rà.
- Sau khi live có hotfix 2.0.2.1 trong lúc tải bản đầu, guard triển khai dừng đúng trước chuyển dịch vụ. Đã tích hợp mã hotfix mới từ main, chạy 17 kiểm thử kết hợp đều qua, dựng lại gói và xác minh quy tắc hotfix còn nguyên trên runtime. Chi tiết triển khai ở [báo cáo 2.0.3](../DEPLOY_2.0.3_2026-10-11.md).
- Đối chiếu 50 nghề, 40 ngày, 49.440 nhiệm vụ: mọi nhiệm vụ sinh từ baseline live 2.0.2 vẫn khớp bản mới.
- Kiểm thử quay lui RUI tới 1.4.31 đã lỗi `Mã bảng giá không hợp lệ` ngay trên ZIP 2.0.2 đã xác minh, trước thay đổi này. Không dùng kiểm thử lịch sử đó để tuyên bố tương thích rollback hiện tại.

## Chi tiết và giới hạn

- Khoản phạt giao thông còn nợ của quầy cũ được khép lại một lần, đối chiếu phần chi phí chưa thực trả và thuế; không hút tiếp tiền các lần bán sau. Hóa đơn phạt nghề cũ khi thanh toán cũng chỉ thu mức nhỏ hiện tại, lưu phần thực trả/miễn.
- Cược phóng dao mới lưu ngày đặt cược để hoàn đúng thống kê ngày khi ván bị dừng. Ván cũ ở màn từ 2 trở lên thiếu ngày gốc vẫn hoàn ví và thống kê lỗ/bảng tuần đúng; bộ đếm ngày giữ phần debit cũ theo hướng thận trọng vì không đoán được ngày gốc.
- Cược bị dừng được trả lại làm RTP lý thuyết chiếu trong tăng từ khoảng 97,1% lên 98,0%; không đổi xác suất rút kết quả. Chi tiết trong `docs/FAIR_HOUSE_EDGE.md`.
- Không hạ các chi phí mua hàng, sửa chữa, thuế, trả nợ hoặc tiền cược thua thông thường.
- PostgreSQL kiểm thử là cluster dùng riêng trong `output/pg-gentle-203`, cổng 55443. Đã tắt fsync/synchronous_commit chỉ tại cluster dùng một lần này để kiểm chức năng; không dùng kết quả làm bằng chứng độ bền lưu trữ và không đổi cấu hình production.
- Đã kiểm trực tiếp validator nguyên trạng 2.0.2 với giao thông/phạt chủ quầy do bản mới tạo, cả lượt bản cũ giao hàng rồi trả về bản mới. Phần thực trả lưu ở trường tùy chọn ngoài cấu trúc biên nhận cũ; không giả số tiền danh nghĩa thành số đã thu. Chưa tuyên bố mọi tổ hợp thao tác hỗn hợp đều được chứng minh. Quay lui nguyên bản 2.0.2 sẽ mất chính sách phạt nhẹ; không phục hồi database cũ để quay lui mã.
