# Bổ sung nội dung nghề sau 2.4.0

Chủ game yêu cầu “bổ sung và deploy”, tiếp tục danh mục 540 gói đã đề xuất và các giới hạn tiền đã thống nhất. Không xin lại quyền triển khai. Phần sửa chat che zoom là lỗi độc lập, cùng đợt phát hành.

Chọn nhánh chuyên môn riêng trong nghề, không đổi nhiệm vụ cũ hoặc dùng tên gói làm hệ số tiền. Mỗi nghề có đúng 10 gói theo danh mục 13/10: vật tư đầu vào định lượng, trình tự thao tác riêng, điểm kiểm nghiệm thu và đơn khách tương ứng. Học phí cuối là 3000,9000,30000,100000,350000,1200000,4000000,12000000,35000000,100000000. Chùa miễn phí, không tạo thu nhập mới.

Mở tuần tự: XP cấp 5/12/25/50/90/150/250/400/650/1000, việc sạch 10/30/70/140/260/450/750/1200/1900/3000, ngày thực chuẩn 3/7/14/24/40/65/95/140/200/280. Dùng bằng chứng scale hiện có, không suy ngày từ tiền; ca chuyên môn nghiệm thu tốt cũng ghi nhận ca thực trong ngày. Phí trừ quỹ nghề một lần khi đăng ký, thực hành miễn phí thử lại và không sinh tiền/XP. Trình tự và định lượng phải đúng mới cấp quyền, giữ chứng chỉ/chức vụ hiện hành.

Đơn chuyên môn độc lập quy mô cơ sở: nhận khách → nhập vật tư → cam kết → làm bước theo định lượng/trình tự → kiểm và bàn giao → quyết toán. Dùng cùng quota tài khoản 4 suất/ngày thực, tối đa12, ban đầu1 với quản lý; không còn ngân sách giờ của bản đề xuất13/10. Hủy trước bắt đầu trả suất nhưng giữ pack/khách/khối lượng. Đơn đang chạy giữ vật tư, trả đúng một lần, không nhân x3/nhân viên/thi đua. Kho chuyên môn có SKU mới theo vật tư/mẫu gói, giá vốn FIFO, mỗi mã dùng quyền kho/nhập đã mua. Giao nhận vật tư là lệnh thật, không đòi mua quy mô50k để dùng gói3k.

Khối lượng mỗi đơn tăng theo bậc 1/2/4/8/20/50/100/200/500/1000 bộ hoặc đơn vị thành phẩm nêu trong gói. Dự toán tách vật tư, công/dịch vụ trực tiếp, thuế4% kinh doanh, và lãi mục tiêu200/400/800/1500/3000/8000/18000/40000/100000/250000 cho toàn đơn đúng. Công vụ chỉ trả phụ cấp; vật tư cấp hiện vật, ngân sách/COD/tiền khách không thành thu nhập. Phân loại theo catalogue2.4.0 (luật sư dịch vụ kinh doanh). Chùa chỉ tăng tinh thần trong trần100. Hóa đơn cao đi kèm số bộ/khối lượng thực, không nhân giá món nền.

UI trong Thăng tiến: lộ trình10gói, điều kiện/giá/vốn/lợi ích, học và thực hành, đơn đang làm, kho, biên nhận. Hiện SKU mới trực tiếp trong kho chuyên môn và đơn khách sau khi mở; không sửa kho/đơn legacy. Core nhãn English có fallback tình huống Việt. Client không có đáp án; lời giải học chỉ sau chấm. Server kiểm enum/types, stale/replay, đồng bộ quota xuyên hai hệ, bảo toàn tiền/hàng qua reload, reset không sinh suất.

Nghiệm thu: đủ540catalogue khôngtrùng tên, mọi gói có định lượng/trình tự/điểm kiểm riêng; mô phỏng lệnh thực540gói, học sai/đúng/thi lại/đúp, kho và nhập trần, FIFO/cancel/reset/replay/quota, publicDTO khônglộđápán, tươngthích53280nhiệmvụ, browser390/1280vàzoom320/landscape. Gói phát hành từ đúngbytes2.4.0 vàsource23fb59ff, xácminhHTTP/hash, rolling và hậukiểm.
