# Kiểm chứng mở rộng nghề 2.4.0

Danh mục thực thi có 54 nghề × 8 bậc (34 kinh doanh, 19 công vụ, 1 chùa). Kiểm thử chạy lệnh engine cho đủ 432 tổ hợp; mua bậc tuần tự, thuê người, lập đề nghị, nhập/nhận hàng, phân vật tư, lịch người, xử lý phát sinh, nghiệm thu và trả tiền. Fixture cung cấp điều kiện ngày thực/chứng chỉ và bố trí đầy đủ để chạy mọi bậc; không mô phỏng đã chơi 240 ngày. Các điều kiện nâng cấp, mở điểm/quầy, ngày thực và replay được kiểm thử riêng.

Lần chạy cuối 489 kiểm thử lõi/mở rộng đạt; gồm 432 tổ hợp và ca nhu cầu 80%/60%, nghiệm thu lỗi, thiếu điểm, đổi nhân sự sau hủy, DTO không lộ đáp án. Sau đó bổ sung và chạy kiểm thử nghỉ việc/đình chỉ, giá vốn lô lịch sử, chuyển nguyên lô tại trần 400 dòng và Store PostgreSQL chống lặp. 292 kiểm thử hồi quy unittest đạt (1 bỏ qua có chủ đích); lần chạy pytest cùng bộ có lỗi thu thập hàm unittest sinh động `self`, nên dùng đúng unittest runner. Không thay đổi bài kiểm tra cũ để che lỗi: cập nhật phạm vi catalogue kho/nhập từ 25/24 nghề lên 36, giữ nguyên giá và quyền cũ.

Browser thật 390px cảm ứng và 1280px dùng GameAPI và PostgreSQL local: nhận đề nghị, chọn kế hoạch, đặt/nhận/giữ vật tư, xếp từng người, khởi động, phát sinh, nghiệm thu và đối soát; lãi tạp hóa bậc 1 = 1.000 xu, 12 revision gồm import fixture, không pageerror hoặc tràn ngang. Đây là bài kiểm tra UI điều phối độc lập dùng component thật; kiểm tra nội thất/social có bộ hai tài khoản riêng. Thử nghiệm tiền cấp sẵn chỉ dùng DB local, không sửa tài khoản production.

## Đối chiếu dữ liệu và thời gian chơi

DB production chỉ đọc, ngày 14/10/2026. Mẫu 100 bản lưu cập nhật gần nhất: ví median 594, p90 52.019,9, max 925.415 xu; tổng quỹ nghề median 18.059,5, p90 519.212,6, max 6.216.229 xu. Đây không phải toàn bộ người chơi. Cache bảng tài sản có 48.484 dòng, median 522, p90 2.023,7, max 63.621.390; không có dòng >=100 triệu. Tài sản cache không phải tiền mặt. Hai truy vấn JSON rộng hơn đã chạm timeout 15/20s và được dừng, không suy ra số liệu từ chúng.

Vì vậy mức 402,3 triệu tổng phí tạp hóa là mục tiêu dài hạn, không phải giá vào cửa cho người mới hoặc khẳng định đa số đang có trăm triệu. Bậc đầu 50.000 xu/3 ngày thực/10 việc sạch; bậc cuối 240 ngày thực/1.200 việc sạch. Suất bắt đầu dùng chung 4 mỗi ngày, tích tối đa 12, không thể đổi nghề/đổi ngày nghề để nhận thêm. Quota tích lũy cho phép dùng hơn 4 trong một ngày sau khi đã để dành.

Lãi ca tạp hóa bậc 8 ở 100%/80%/60% nhu cầu là 800.000/544.000/288.000 xu, tổng toàn mạng. Nếu các nhu cầu xuất hiện ngang nhau thì kỳ vọng danh mục là 544.000 xu/ca đạt chuẩn, tối đa dài hạn 2.176.000 xu/ngày ở 4 suất; chưa trừ phí tuyển/đại tu trả riêng. Đây là giả định cân bằng, không phải thống kê tần suất thực đo. Nhu cầu theo hạt giống máy chủ, hủy giữ nguyên khách và nhu cầu; đổi bố trí chỉ đổi quy mô phục vụ. So với lợi ích bậc 7, phí bậc 8 thu hồi khoảng 658 ca đủ nhu cầu, chưa tính ngày học nghề và chi phí phát sinh.

Không áp đặt bộ đếm chờ 10–20 phút. Thời lượng đề xuất ban đầu chưa được đo bằng người chơi thật; ca lớn có nhiều bước theo điểm và tài nguyên, cùng điều kiện ngày thực cho tiến trình dài hạn. Một dòng vật tư lõi mới mỗi nghề có định lượng/giá vốn rõ: thùng chứa 20 gói nhà cung cấp. Đây là khối lượng thật lớn hơn, giá đơn vị giữ nguyên; tránh ca bậc cuối vượt trần kho tối đa. Tất cả điểm dùng chung sức chứa của mã, không nhân sức chứa theo số điểm.

## Giới hạn đã công khai

Không triển khai hoặc thu tiền cho 540 gói công thức/mẫu hàng trong đề xuất trước. Tiếng Anh có nhãn điều phối/tiền/điều kiện chính; các tình huống nghề chi tiết mới vẫn ưu tiên tiếng Việt và có fallback. Không tuyên bố bản dịch toàn bộ hoàn tất. Bản cũ không hiểu hợp đồng đang giữ vốn/tài nguyên, nên sửa tiến bằng bản tương thích; không hạ code mù hoặc phục hồi DB để quay lui.

## Kiểm chứng tương thích và nội thất

53.280 mẫu nhiệm vụ của 54 nghề/ngày 1–40/12 vị trí/chế độ desk và classic khớp mã nguồn Release A `0a5e3b0537d78d4ca6ac7019c032cc397539b503`. Bộ kiểm tra social/town/socket/browser độc lập đạt 44 ca trước bản sửa admission cuối. Hai tài khoản xác thực kiểm tra chủ sở hữu/khách, đi bàn phím/cảm ứng, chat/reaction, reconnect 1012, mở điều phối tại trạm và thu hồi quyền vào phòng.

Review phát hiện tranh chấp khi hai khách vào sát giới hạn phòng trong lúc giải phóng treasure lease. Đã chuyển kiểm tra sức chứa sau await cuối, xử lý kết quả Room.add và thêm ba ca hồi quy: hai khách vào phòng còn một chỗ, hai phòng khi còn một suất, Room.add từ chối. Không sửa dữ liệu người chơi để thử.

Chat/reaction trong cơ sở có bong bóng trên đầu người nói, chỉ hiện sau xác nhận máy chủ, đi theo vị trí, tự ẩn sau 8 giây, dùng một timer và xóa khi rời/mất kết nối. Kiểm tra Chromium thật 390px/1280px, Node vòng đời/render/đồng bộ và 12 kiểm thử admission/room đạt sau sửa; reviewer độc lập duyệt.

Hồi quy bổ sung 177 ca tiền/kho/chứng chỉ/thi đua/quầy: 175 đạt lần đầu. Một timeout HTTP local 10 giây không tái hiện khi chạy riêng (7 giây); một lỗi danh mục chứng chỉ thiếu hai nghề mới đã sửa bằng nhóm đào tạo hiện hữu (bưu điện: an toàn giao nhận/COD; luật sư: hành chính/hồ sơ/chữ ký, chứng chỉ hỗ trợ tuyển dụng). Không đổi học phí hoặc ngân hàng câu hỏi. Chạy lại toàn bộ 59 ca chứng chỉ và lưu trữ liên quan đạt; reviewer độc lập duyệt và chạy ba ca Chance đạt. Node chứng chỉ kinh doanh/thi đua/hạn mức nhập đều đạt.
