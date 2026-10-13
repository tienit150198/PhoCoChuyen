# Kiểm tra bổ sung lỗi tiệc cưới sau hủy hôn

## Xác nhận production

Đọc PostgreSQL qua SSH, bản đang chạy 2.3.0. Không chỉnh dữ liệu quan hệ, tiệc, khách hoặc tiền.

- Quan hệ cũ đã kết thúc lúc **18:59:35 ngày 13/10/2026 (UTC+7)**; cả đám cưới và tiệc cũ ghi `cancelled`.
- Giờ tiệc cũ: **21:00 cùng ngày**.
- Có **17 bản ghi khách**, thời điểm vào từ **20:55:01 đến 21:09:26**, tổng `steps` là 19.
- Các khóa hiệu ứng tiền theo phút của tiệc cũ có **18 bản ghi, tổng 360 xu**.
- Người gửi góp ý có một quan hệ và tiệc mới hợp lệ riêng; không thay đổi chúng.

Đây là bằng chứng tiệc trực tiếp tiếp tục chạy sau hủy, không chỉ là nhãn lịch sử gây hiểu nhầm. Chẩn đoán trước đã được đính chính. Số bước tham dự và số hiệu ứng tiền là hai phép thống kê khác nhau, không suy diễn một bước luôn tương ứng một khoản thưởng.

## Nguyên nhân

`game.marriage._divorce` đã cập nhật trạng thái hủy đúng trong DB. `live.wedding.WeddingFeature.refresh` chỉ lấy tiệc `booked`, nhưng sau đó giữ lại mọi tiệc thiếu trong kết quả mới vì giả định chúng đã hoàn tất và cần thời gian chào tạm biệt. Tiệc bị hủy vì thế vẫn nằm trong lịch. Vào phòng từ lịch đã nạp chỉ kiểm tra thời gian; tác vụ ghi khách và thưởng theo phút cũng chưa kiểm tra lại việc hủy.

## Phạm vi sửa và kiểm chứng

Thực hiện theo `docs/superpowers/plans/2026-10-14-wedding-cancellation.md`:

- Đối chiếu trạng thái DB khi nạp/xem lịch và mỗi tick; gỡ tiệc đã hủy, mất bản ghi hoặc có quan hệ đã kết thúc, đóng phòng của cả khách trong tiệc và khách xem ngoài cổng.
- Kiểm tra lại khi vào, sau các tác vụ tải dữ liệu bất đồng bộ; không chấp nhận lịch cũ.
- Ghi khách, thưởng theo phút, ăn/uống, tung hoa, chụp ảnh và quyết toán chủ tiệc được bảo vệ bằng trạng thái hiện hành. Các thao tác ghi khóa quan hệ trước, tiệc sau, cùng thứ tự với hủy hôn; phần thưởng nằm trong cùng giao dịch.
- Chỉ cập nhật trạng thái thưởng trong bộ nhớ và thông báo nhận xu sau khi giao dịch thành công. Đồng bộ số ảnh/cooldown trong khóa tiệc để các yêu cầu chụp ảnh chồng nhau không dùng số ảnh cũ.
- Giữ thời gian chào tạm biệt 120 giây và thưởng phút cuối đã xếp hàng cho tiệc hoàn tất hợp lệ.

Kiểm chứng trên PostgreSQL cục bộ, WebSocket thật:

- Tái hiện trước sửa: 5/6 kiểm thử đầu thất bại; lịch/phòng cũ vẫn tồn tại, vào tiệc trả `walk_room`, ăn vẫn có thưởng và tác vụ chờ vẫn ghi hiệu ứng. Trường hợp giữ thời gian chào tạm biệt đã đạt từ trước.
- Bổ sung tái hiện lỗi khi hủy giữ khóa quan hệ nhưng quyết toán vẫn ghi thưởng chủ tiệc; vào tiệc đang chờ tải dữ liệu; trạng thái thưởng trong bộ nhớ đổi dù giao dịch rollback. Các ca này đã đạt sau sửa.
- `tests/test_live_wedding.py`: **31 passed**, 129.53 giây, gồm 10 kiểm thử mới về hủy/race/rollback.
- Rà soát chất lượng phát hiện kiểm tra trạng thái mới ở `_toss_open` nằm ngoài khối đặt lại trạng thái khi DB lỗi. Bổ sung ca tái hiện đỏ, chuyển kiểm tra vào khối phục hồi; **16 kiểm thử Feast + Cancellation passed**, 40.82 giây. Ca mới xác nhận đọc DB lỗi tạm thời → tick sau mở lại tung hoa → thưởng đúng một lần. Tổng cộng thêm 11 kiểm thử trong bản sửa này.
- `tests/test_marriage.py tests/test_wedding_live.py`: **66 passed, 1 skipped**, 80.45 giây. Ca bỏ qua cần `MNL_OLD_TREE` để so sánh bản cũ.
- `tests/test_live_units.py tests/test_live_effects_apply.py`: **26 passed**, một ca HTTP timeout 20 giây. Chạy lại có trace xác định timeout khi tạo snapshot tài nguyên lần đầu (`WebAssets._file_hash`), trước xử lý hiệu ứng. Chạy lại chính ca HTTP với snapshot thật được tạo sẵn trong setup: **1 passed**, 37.99 giây; bootstrap/nhận thưởng/lặp yêu cầu/CSRF đúng. Không thay source để bỏ qua kiểm tra hay giả dữ liệu HTTP.
- `compileall`, `git diff --check` đạt. Rà soát yêu cầu độc lập và rà soát chất lượng cuối đều đạt; phát hiện P2 về phục hồi tung hoa đã được kiểm tra lại và đóng.

Bản sửa chưa deploy. Không thay đổi schema hoặc dữ liệu tiền/quan hệ/tiệc production.

Chi phí vận hành mới: thêm một truy vấn đối chiếu trạng thái mỗi tick (khoảng một giây) khi có tiệc trong bộ nhớ. Chưa thực hiện benchmark tải riêng.

## Phản hồi người chơi

Đã đính chính lời đáp 370 trên production và đọc lại xác nhận đúng nội dung: thừa nhận chẩn đoán trước chưa đủ, giải thích lỗi giữ lịch trong bộ nhớ và nói rõ bản sửa chưa phát hành. Giữ `seen` chờ phát hành. Cập nhật có điều kiện theo `updated_at`, trạng thái và lời đáp cũ; không ghi đè nếu có người khác trả lời đồng thời. Snapshot riêng trong `output/feedback-20261014`, không commit dữ liệu tài khoản.
