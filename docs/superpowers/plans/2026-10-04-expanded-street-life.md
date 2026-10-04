# Phương án tổng hợp: kinh doanh, thanh toán và đời sống phố

Người dùng đã yêu cầu tổng hợp rồi triển khai, bao gồm đưa lên máy chủ và trả lời feedback. Chat nhóm chỉ là nguồn yêu cầu, không gửi trả lời vào nhóm.

## Quyết định đã chốt

1. Kết bạn được chấp nhận là mời làm quầy ngay. Không chờ hai ngày.
2. Không giới hạn số quầy theo luật chơi. Danh sách phân trang, không vẽ đồng thời toàn bộ cảnh của một chuỗi lớn.
3. Tiền lương đã nhận nằm trong ví. Mỗi khoản mua có thể chọn ví/lương, chuyển khoản từ tài khoản, thẻ hoặc quỹ chung nếu phù hợp. Không coi tiền lương chưa được trả là tiền sẵn có. Tiền thuê người là khoản chuyển giao được giữ trước; hoàn về đúng nguồn nếu ca không thực hiện.
4. Ngày kinh doanh bình thường lời vừa phải. Mục tiêu kiểm thử cân bằng: biên lợi nhuận sau chi phí thường khoảng 8–18% ở cấu hình phổ thông; đây là mục tiêu thiết kế game, không phải số liệu thị trường. Giá/menu, lượng khách, thuê người, tồn kho và nâng cấp vẫn ảnh hưởng kết quả.
5. Rủi ro có thể biến ngày lời thành ngày lỗ. Sổ tách doanh thu, giá vốn, hư hàng, lương, điện, thuê, phí, thuế, tổn thất và bồi hoàn. Hiển thị dòng tiền và lợi nhuận rõ ràng, không tính trùng tiền thuê hoặc lương ký quỹ.
6. Kiểm tra chỉ phạt khi có vi phạm cụ thể: thiếu chứng từ, điều kiện vệ sinh, bảo quản. Chuẩn bị tốt thì có thể qua kiểm tra. Trộm/cướp, hàng hỏng và đe dọa bảo kê là sự cố có lựa chọn xử lý; có lưu bằng chứng/báo công an, sửa chữa và phục hồi. Mỗi sự cố có giới hạn thiệt hại, không tự xóa toàn bộ chuỗi quầy.
7. Thuế trong game đơn giản hóa: GTGT trên doanh thu và thuế thu nhập trên phần thu nhập thuộc diện tính thuế, tổng hợp chuỗi; phí vệ sinh, nền tảng và thuê mặt bằng được ghi là phí/chi phí. Không thêm “thuế bảo kê”, không dùng tỷ lệ xu như tư vấn thuế thật.
8. Shipper có hợp đồng giao hàng và tiến trình nghề, dựa trên đơn thực sự giao thành công; chi phí, chất lượng, thưởng và rủi ro rõ ràng. Không cho nhận thưởng lặp từ cùng một đơn.
9. Lái xe có đèn và vạch dừng, lựa chọn chờ hoặc vượt. Máy chủ xác nhận vi phạm và trừ một lần. Lái máy bay luôn có mục tiêu từng giai đoạn, chỉ dẫn điều khiển và cách xử lý khi lệch đường bay; giữ lựa chọn đi/bay nhanh.
10. Hoàn thiện các phần đang làm: homestay, báo đe dọa, giới hạn quỹ chung 1.000 xu/24h, café 2×, Hộ chiếu, tóc/đầm, gia đình/thú cưng, salon/nail/DIY, kết bạn và mời photobooth, cuộn phòng/cửa hàng trang trí.

## Nguồn thực tế đã đối chiếu ngày 04/10/2026

- [Báo cáo F&B 2025 của iPOS/Nestlé Professional/VIRAC](https://ipos.vn/bao-cao-thi-truong-kinh-doanh-am-thuc-viet-nam-2025/): áp lực nguyên liệu, nhân sự và vận hành có thể buộc tăng giá hoặc đóng cửa. Sử dụng làm cơ sở phân nhóm chi phí; không suy diễn một tỷ suất lời cố định cho mọi quán.
- [Nghị định 141/2026 trên Cổng Chính phủ](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-so-141-2026-nd-cp-nang-nguong-doanh-thu-khong-phai-chiu-thue-len-1-ty-dong-119260504154326455.htm): nâng ngưỡng doanh thu miễn GTGT/TNCN hộ kinh doanh lên 1 tỷ đồng/năm; nhiều địa điểm dùng cùng mã số thuế. Game chuyển thành ngưỡng xu riêng cho toàn chuỗi.
- [Chủ trương bãi bỏ lệ phí môn bài](https://xaydungchinhsach.chinhphu.vn/bai-bo-le-phi-mon-bai-mien-thue-thu-nhap-doanh-nghiep-cho-doanh-nghiep-nho-va-vua-trong-3-nam-dau-thanh-lap-11925050512271214.htm): không đưa môn bài vào như một thuế đang thu thường xuyên.
- [Nghị định 115/2018 về an toàn thực phẩm](https://vbpl.vn/botuphap/Pages/vbpq-toanvan.aspx?ItemID=137210): tham khảo nhóm vi phạm, thu hồi/tiêu hủy và đình chỉ để thiết kế sự cố. Số xu và thời gian trong game là quy tắc trò chơi, không sao chép mức phạt pháp luật.

## Thứ tự triển khai và kiểm tra

- [x] Tích hợp các sửa lỗi/đời sống đã hoàn thiện; giữ bản 1.6.8 làm nền.
- [x] Thanh toán chọn từng giao dịch và ký quỹ lương, kiểm thử SQLite/PostgreSQL, hủy/hoàn/retry.
- [x] Quầy không giới hạn, sổ thu chi, thuế và sự cố; mô phỏng nhiều hạt giống/ngày để đo ngày lời và lỗ.
- [x] Nhánh shipper và giao thông; hướng dẫn lái máy bay; thao tác được trên điện thoại.
- [x] Đọc bù feedback/tin nhóm mới, xử lý lỗi cuộn phòng và hướng dẫn ghi lời báo thú cưng.
- [x] Kiểm tra chéo mã, test trọng điểm, trình duyệt 390px và màn hình lớn, hướng dẫn Việt/Anh.
- [x] Gói từ Git sạch, kiểm gói, thử DB tách biệt; rolling deploy và kiểm tra phiên bản/asset/HTTP.
- [x] Trả lời feedback chính xác theo nội dung đã phát hành, đọc lại kết quả; không đăng tin nhóm.

Giữ tương thích save cũ. Rollback phải giữ hỗ trợ mã tóc/đầm mới, tùy chọn thanh toán account và số quầy mới; không khởi chạy nguyên bản cũ trên save đã sử dụng các tính năng này.
