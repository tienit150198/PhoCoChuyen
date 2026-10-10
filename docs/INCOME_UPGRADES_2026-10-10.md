# Nâng cấp thu nhập và kiểm tra feedback — 10/10/2026

## Bản thay đổi

Nhánh `codex/income-upgrades-20261010`, worktree `D:/projects/Mot_ngay_lam_nghe/wt-income-upgrades`, xuất phát từ `origin/main` tại `09f630c4` (1.9.43). Đã đối chiếu lại remote trong lượt làm việc. Chưa merge hoặc triển khai lên game đang chạy.

Mở **Trang trí & nâng cấp → Thiết bị nghề**. Giữ ba bậc tốc độ hiện có; thêm 324 lựa chọn theo nghề, tương ứng ba nhóm thiết bị mới:

| Nhóm | Bậc 1 / 2 / 3 | Giá từng bậc | Phạm vi |
|---|---|---|---|
| Đón thêm khách | Tối đa +15 / +30 / +50% nhịp khách | 120 / 280 / 600 xu | Nhân viên ở 50 nghề và khách quầy tự mở; vẫn chịu giới hạn tốc độ phục vụ |
| Chất lượng | +10 / +20 / +30% | 100 / 260 / 560 xu | Tiền hoàn thành đơn/hồ sơ, lãi dương đơn nhân viên và quầy tự mở |
| Online | +25 / +50 / +100% nhịp đơn online | 140 / 320 / 680 xu | Tám nghề có quầy tự mở: trà đá, trái cây, kem, bánh/cà phê, trà sữa, hoa, tạp hóa, quần áo; phải bật bán online |

Mua bằng quỹ nghề, theo thứ tự bậc. Cùng nhóm chỉ dùng bậc cao nhất. Nhóm khác nhau phối hợp được. Ví dụ thiết bị: bảng hiệu và đèn, bộ chăm khách quen, bàn kiểm chất lượng, đèn chụp sản phẩm, máy nhận đơn/in phiếu.

Thưởng chất lượng ở nghề làm tròn lên xu nguyên để bậc đầu cũng có ích với đơn nhỏ; tại quầy, xu lẻ được giữ trong cơ chế thưởng lợi nhuận hiện có. Có dòng riêng trong sổ tiền và thông báo `+N xu nhờ thiết bị chất lượng`. Phiếu nhà thuốc, khóa sổ tháng, hoa cài áo/đặt trước/định kỳ và hộp bánh văn phòng có thưởng khi hoàn thành. Cọc hoa chưa hoàn thành không nhận thưởng; khi giao đủ tính trên giá cuối cùng của cả đơn. Lương cố định, bài học và chuyển tiền giữa người chơi không thuộc nhóm thưởng này.

Đơn đang chờ giữ thời điểm hẹn; nhịp mới áp dụng cho lượt sau. Nếu còn đơn nhân viên quá hạn chưa quyết toán do giới hạn số đơn mỗi lần đồng bộ, phải đồng bộ hết trước khi mua. Nâng cấp không tăng tiền cho công việc trong quá khứ. Đơn tự động vẫn dùng kho, quỹ, lương, phí và thuế thật; hết hàng thì ngừng bán.

## Kiểm tra kinh tế

Mô phỏng cố định một nhân viên kế toán, cùng trạng thái ban đầu và thời điểm kết thúc (tới 600 giây sau đơn đầu tiên). Đây là test có kiểm soát, không phải số liệu người chơi live, không phải cam kết thu nhập và chưa trừ giá mua thiết bị:

| Thiết bị | Đơn hoàn thành | Quỹ tăng |
|---|---:|---:|
| Cơ bản | 11 | 130 xu |
| Chất lượng bậc 1 | 11 | 145 xu |
| Chất lượng bậc 3 | 11 | 176 xu |
| Đón khách + chất lượng bậc 3 | 16 | 257 xu |

Test mới kiểm tra mua đúng giá, thiếu tiền/bậc trước/sai nghề/mua trùng, thay thế bậc thấp, đơn lỗ, thưởng đơn nhỏ, kho thực, đọc không tạo tiền, online bật/tắt, số đơn online, quyết toán online/offline giống nhau, không nâng cấp ngược đơn lịch sử, sổ tiền và thông báo thưởng. Đã thử mua thật qua `apply_action` trong giao diện thử cục bộ, kiểm tra mở bậc tiếp theo và quỹ giảm đúng; thử giao diện điện thoại 390×844, nghề kế toán không hiện nhánh online.

## Feedback đọc trực tiếp

Hộp góp ý live ở thời điểm kiểm tra: 315 góp ý, gồm 2 mới (#325, #326), 245 đã xem, 68 xong. Chỉ đọc; chưa gửi lời đáp hay đổi trạng thái người chơi trong lượt này.

| Feedback | Đối chiếu | Cách xử lý |
|---|---|---|
| #325 — nhạc, tắt/mở, âm lượng, nhạc khu vực | Đã có Cài đặt → Âm thanh → Bật nhạc nền, Âm lượng nhạc; kiểu “Theo nghề” đổi nhạc theo nhóm nghề, không phải mỗi nghề một bài riêng | Đã chuẩn bị lời hướng dẫn dưới đây; không cần thêm bộ điều khiển trùng |
| #326 — nhận kho tự động vì đếm từng món mệt | Kho hiện có giữ để đếm liên tục và đếm theo khay 10 món cho kiện lớn; kiểm nhận vẫn cần xác nhận để giữ xử lý thiếu hàng | Đã chuẩn bị hướng dẫn; đề xuất tự nhận hoàn toàn còn mở, chưa đánh dấu xong |
| #310 trong đợt trước — giá thấp/thu nhập thấp | Quầy tự mở đã có chỉnh giá. Tăng giá ảnh hưởng lượng khách, không bảo đảm tăng lợi nhuận | Bản thay đổi này bổ sung hướng đầu tư thiết bị để tăng nhịp bán và lợi nhuận |

Lời đáp chuẩn bị cho #325:

> Game có sẵn phần này rồi bạn nhé: vào Cài đặt → Âm thanh → bật Nhạc nền. Bạn có thể chỉnh Âm lượng nhạc và chọn kiểu Theo nghề; nhạc sẽ đổi theo nhóm nghề. Nếu đã bật mà vẫn im, bạn thử chạm vào màn chơi để trình duyệt cho phép phát âm thanh nhé. Mình ghi nhận thêm ý muốn có nhiều bài riêng cho từng khu vực.

Lời đáp chuẩn bị cho #326:

> Mình đã đọc góp ý của bạn. Hiện tại bạn có thể giữ vào kiện để đếm nhanh; kiện lớn có nút Đếm khay để đếm theo nhóm 10 món, không cần chạm từng món. Sau đó bấm kiểm nhận để nhập kho; nếu thiếu vẫn có thể khiếu nại. Phần tự nhận toàn bộ hàng khi vừa về kho hiện chưa có, mình giữ đề xuất này trong danh sách cải tiến.

## Giới hạn kiểm tra và phát hành

- Bộ hồi quy áp dụng: **436 tests, 0 lỗi, 1 bỏ qua** (225,5 giây), gồm 19 test mới và các bộ nghiệp vụ, nhân viên, quầy, tồn kho, kế toán/nhà thuốc, bánh và hoa. Các lớp cần PostgreSQL và ba bài legacy baseline được tách rõ khỏi bộ này.
- Kiểm tra cú pháp 309/309 JavaScript đạt; kiểm tra tương thích Safari 15 trực tiếp 309/309 đạt; hai bài test UI thiết bị đạt. Script tổng `check_js.mjs` gọi sai đường dẫn con trên Windows (`D:\D:\...`), nên đã chạy kiểm tra Safari riêng.
- Kiểm tra điều hướng cảnh: 66 nghề × 2 bố cục, 1.071.810 checks, 0 lỗi.
- Chưa chạy các bài tích hợp PostgreSQL vì môi trường chưa có `TEST_DATABASE_URL`; không dùng cơ sở dữ liệu production cho test.
- Ba bài roundtrip về bản 1.5.2/1.4.31 lỗi cả trên nhánh chưa có thay đổi này (danh sách nghề/bảng giá cũ). Đã xác nhận baseline, không coi chúng là regression mới.
- Bản lưu mua ID thiết bị mới không được bản server cũ nhận biết. Khi phát hành cần phương án rollback dữ liệu hoặc migration, không chỉ đổi code về phiên bản cũ.
