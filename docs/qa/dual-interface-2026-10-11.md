# Rà hành vi hai giao diện — 11/10/2026

Tiếp nối `performance-2026-10-11.md` và danh mục `isometric-feature-parity.md`. Kiểm tra trên dữ liệu PostgreSQL riêng, không sửa dữ liệu người chơi production.

## Phạm vi và lỗi phát hiện

- Đường vào đã đối chiếu đủ 50 nghề, 57 nhóm chức năng và 66 tiện ích ở báo cáo trước. Lượt này đi sâu vào trạng thái nhiệm vụ khi đổi giao diện, kho/nhân viên/điều kiện mở, nhà, avatar và kết nối người chơi.
- Đổi trang phục trên đảo trước đây chỉ cập nhật máy của mình. Gói di chuyển nay gửi ngoại hình công khai khi thay đổi; máy chủ kiểm tra dữ liệu rồi gửi cho những người đã ở trong phòng. Giữ nguyên người chơi, vị trí và quyền nhận rương; không thoát/vào phòng lại. Người vào sau cũng thấy ngoại hình mới.
- Gợi ý thao tác trùng đã được CSS ẩn nhưng vẫn xuất hiện như một nút trong cây trợ năng. Đã ẩn đúng phần trùng khỏi cây trợ năng, giữ nút thao tác đang nhìn thấy. Không có lỗi xử lý đơn trà sữa phía máy chủ trong tình huống này.
- Bộ hẹn giờ ngâm hoa có thể gửi lệnh của nghề hoa sau khi người chơi đổi nghề/đổi khách. Đã bổ sung quản lý vòng đời theo nghề, ca, khách và hoa đang ngâm; đóng bàn làm việc vẫn cho phép tiếp tục công việc hợp lệ. Rà chéo còn phát hiện phải giữ được cú bấm ngay khi `task_select` đang chờ xác nhận; việc gửi lệnh sau cùng vẫn cần đúng khách đã xác nhận.
- Bốn fixture bán nhà được sửa để dùng giá chào bán từ public state thay vì giá tài sản thô; fixture làm mới hội chợ bổ sung trạng thái bảng đang bận. Không đổi công thức giá hoặc luật hội chợ để làm test qua.

## Chơi thử xuyên hai giao diện

Chromium, tài khoản khách kiểm thử **Mây Kiểm Thử**, HTTP `localhost:18893`, WebSocket `localhost:18894`:

1. Nghe yêu cầu khách Linh; chuyển về giao diện cũ.
2. Chọn ly M, rót matcha, rồi bật lại giao diện 2.5D khi đơn đang làm dở.
3. Xác nhận ly, trà, khách và yêu cầu giữ nguyên; thêm foam, ít đá, 30% đường, dán nắp và giao món.
4. Giao thành công, còn hai khách; ví giữ 460 xu, quỹ tăng từ 320 lên 365 xu. Tải lại vẫn giữ kết quả.
5. Với nguồn sau sửa gợi ý, nút ẩn không còn trong cây trợ năng; bấm “Nghe gọi món” hiện đúng phiếu Chị Hạnh. DOM xác nhận phần trùng có `aria-hidden=true`.

Ảnh: `output/release-2.0-local/parity-classic-in-progress.png`, `parity-isometric-order-complete.png`, `parity-guide-fixed.png`.

Lượt này dùng viewport DOM thực 1280×720. Lệnh đổi viewport của công cụ không áp dụng vào tab kiểm tra trong lần thử mới, nên không tính lần này là bằng chứng mobile. Các kiểm tra 320/390/768 px đã xác nhận bằng DOM ở lượt trước được giữ trong báo cáo hiệu năng và readiness. Đây là mô phỏng trình duyệt, chưa phải kiểm tra thiết bị thật.

## Kiểm tra tự động và review độc lập

- **97 ca backend/HTTP/WebSocket đạt**: town, hoạt động ngoài trời, rương, lựa chọn giao diện, sửa/bán nhà và phòng nhà. Có hai người kết nối thật để nhận ngoại hình; thay trang phục giữa bước chuẩn bị và nhận rương vẫn thưởng đúng 10.000 xu, phát lại không thưởng lần hai.
- Probe chạy phương thức render thật: cập nhật trang phục/giới tính thay texture trên cùng actor và sprite, giải phóng texture cũ; trạng thái không đổi không tạo texture hay lượt vẽ mới.
- **110/110 ca `test:performance-parity` đạt**, không bỏ qua ca nào. Bộ client kiểm tra 300 lượt đồng bộ đứng yên không phát gói; đổi ngoại hình phát một gói và không vào lại phòng. Gói công khai không chứa tiền hoặc trường riêng tư.
- **28 ca vòng đời chờ hoa đạt** trong suite trên: chờ được khi chọn khách đang gửi, đợi cả thời hạn và xác nhận trước khi thao tác; từ chối/đổi khách/đổi nghề hủy vĩnh viễn lượt cũ. Hai ca routing bổ sung đạt. Review độc lập đối chiếu cả Promise/state của `GameAPI` không còn lỗi chặn; chưa thử riêng timer nền bằng trình duyệt/mạng chậm thật.
- Rà rộng có 78 ca kho/nhân viên/điều kiện/giao diện và ba ca state-delta/nghề trà sữa đạt; 288 ca hủy việc/trải nghiệm đạt, trong đó hai ca lưu trữ chạy riêng với PostgreSQL. Kiểm tra đổi giao diện giữa việc của bảy nghề đại diện giữ raw state, chỉ thay cờ giao diện.
- Các nhóm kiểm tra có phần giao nhau; không cộng các số trên thành một tổng bao phủ. Danh mục 50 nghề là bằng chứng đủ đường vào, không khẳng định đã chơi mọi giao dịch của từng nghề bằng tay.

Kết quả cuối của suite client, kiểm tra cú pháp và gói phát hành được ghi tại `docs/RELEASE_2.0.0_READINESS.md` sau khi hoàn tất sửa/review.

## Giới hạn phát hành

Chưa triển khai production: SSH báo `Permission denied (publickey,password)`, health vẫn 1.9.48. Chưa gửi thông báo hoặc kích hoạt sự kiện. Đo hiệu năng trước đó là thời gian JavaScript của cảnh kiểm tra, không chứng minh FPS trên mọi máy hoặc năng lực 1.000 CCU.
