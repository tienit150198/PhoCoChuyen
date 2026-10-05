# Vận hành tiệm liên tục — bản local

Chưa deploy, chưa tăng phiên bản và chưa tạo thông báo phát hành. Chỉ triển khai khi người dùng yêu cầu lại.

## Hành vi đã làm

- Quầy riêng và nhân viên trong Sổ tiệm của đủ 41 nghề nhận đơn theo thời gian máy chủ, kể cả khi người chơi chuyển nghề hoặc offline. Hết hàng, thiếu tiền lương, đóng ca hoặc tạm dừng thì dừng theo trạng thái của từng nơi.
- Sổ tiệm có đơn nhân viên riêng, không hoàn thành hộ hoặc xóa công việc thủ công đang dở của chủ. Kho thực, phần hàng đã giữ cho khách và lương được đối chiếu trước khi ghi nhận tiền. Nghề dịch vụ tính vật tư cần cho từng đơn vào quỹ nghề.
- Quầy riêng giữ số quầy không giới hạn; danh mục mỗi ngành có 12 món, chọn toàn bộ được. Giá nhập riêng từng món, tính cầu và đánh giá theo giá trị của món. Kho tối đa 20.000 phần mỗi quầy là giới hạn số lượng vật tư, không phải giới hạn chọn món.
- Chủ không thuê người thì tự phục vụ và giao hàng. Khách và đơn đến tiếp theo thời gian thật; chỉ đơn thực sự hoàn thành mới trả tiền. Đóng ca không tạo thêm doanh thu chưa làm.
- Giao diện có góc nhìn sau quầy/bàn làm việc và từ vị trí người giao hàng, trạng thái hoạt động, nhập hàng, tạm dừng, chi phí và biên nhận. Bản nháp giá, tìm kiếm, con trỏ và vị trí cuộn được giữ khi cập nhật.
- Thiết bị riêng cho mỗi nghề có ba bậc +15%, +35%, +60% tốc độ, trả bằng quỹ nghề, cần mua bậc trước. Tăng tốc đơn nhân viên; cà phê tăng tốc máy pha, sữa và lò; nghề giao hàng giảm phút chạy tuyến và tăng tốc tự lái. Chuyến tự giao quầy chuẩn bị đơn tiếp theo nhanh hơn. Công việc đang chạy giữ tốc độ lúc bắt đầu.

## Quy tắc tiền và lưu trữ

- Quầy lấy tiền hàng/lương/phí từ két và vốn quầy, nhân viên Sổ tiệm lấy từ quỹ nghề. Không tự lấy ví hoặc ngân hàng khi quỹ thiếu.
- Quầy dùng sổ liên tục theo thời gian thực, thuế xu 2% doanh thu. Sổ ca thuê người chơi và lịch sử cũ vẫn được giữ riêng. Không trả hai lần theo cả đồng hồ và ngày sống.
- Tiền phạt giao thông chưa đủ trả được giữ ở quầy, đã trừ vào lãi và thu từ tiền bán hàng hoặc vốn bổ sung sau đó. Không bỏ khoản phạt khi đóng ca và không trừ thêm lần nữa khi đã trả xong.
- Chốt hoạt động cũ trước đổi giá, nhân viên, thiết bị hoặc dòng tiền. Khi bổ sung hàng/vốn, mốc mới bắt đầu từ lúc có đủ nguồn lực; không trả công cho thời gian bị dừng.
- `/api/bootstrap` và `/api/state` đồng bộ bằng giao dịch có revision/CAS. Đồng thời mở nhiều tab hoặc gửi lại cùng yêu cầu không cộng trùng tiền. Public projection chỉ đọc.
- Bản lưu cũ khởi tạo đồng hồ từ lần hoạt động đầu tiên sau cập nhật, không sinh tiền cho khoảng thời gian trước khi có tính năng.

## Kiểm tra

- Các lượt chốt đều qua trên PostgreSQL local: 241 ca phần nghề/nhân viên/máy pha/giao hàng/tích hợp, 132 ca quầy/thuê người/tiền hoàn/giao thông, và 76 ca rà soát cuối. Các nhóm có giao nhau, không cộng thành tổng duy nhất. Log ở `output/business-core-final.log` và `output/business-final-review.log`.
- API trạng thái và bootstrap trả hoạt động đã chốt; hoàn tất một đơn đúng một lần khi nhiều tab cùng cập nhật. Đã sửa cả tiền hoàn cấp vốn ngược cho thời gian quầy hết tiền và tiền phạt chưa đủ trả bị bỏ khi đóng ca.
- 520 module JavaScript qua kiểm tra cú pháp trước lượt sửa UI cuối; kiểm tra lại tệp thay đổi và bộ JS trong lượt chốt.
- Trình duyệt thật desktop và 390px: mua thiết bị đúng số dư, đội tăng đơn/doanh thu, pause/resume, chọn 12 món, sửa giá, giữ bản nháp qua refresh, nhập hàng, phục vụ tại quầy, đóng gói và đi đủ ba giao lộ, nhập thêm khi thiếu hàng rồi giao tiếp.

## Giới hạn vận hành đã cân nhắc

- Bù thời gian ở quầy giới hạn theo lượng hàng thực, khoảng 0,233 giây cho 20.000 lượt bán trên một quầy trong phép đo local. Nhiều quầy chứa đầy hàng sẽ tốn thời gian tương ứng.
- Sổ tiệm bù tối đa 1.024 công việc mỗi giao dịch, khoảng 130 ms cho nghề dịch vụ trong phép đo local. Giữ phần chưa xử lý cho lượt đọc tiếp theo và hiện trạng thái đang cập nhật các đơn lúc vắng mặt.
