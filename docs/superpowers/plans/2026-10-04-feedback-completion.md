# Rà soát góp ý và chat ngày 04/10/2026

## Phạm vi và nguồn

Yêu cầu chủ dự án: đọc góp ý/tin nhắn, liệt kê và xử lý các mục còn thiếu; ưu tiên con chung, ở chung nhà và bỏ giới hạn 60 món nội thất. Giữ toàn bộ thay đổi PostgreSQL, admin và chat đang có trong checkout. Chưa triển khai lên máy chủ hoặc gửi lời đáp cho người chơi trong lượt này.

Chủ dự án đã xác nhận trong lượt này: “Sửa tính năng hiện có trước, nghề mới làm đợt riêng”. Các nghề mới được giữ trong backlog cho đợt sau. Phản ánh thiếu bước tái hiện không được đổi trạng thái thành đã sửa.

- Đã đọc danh sách 161 góp ý trên admin, đến #164; chi tiết #155–164 và bản lưu sáng nay.
- Đã đọc 200 tin chat chung gần nhất (#18473–19758), 42 tin nhóm, đối chiếu bản lưu 715 tin trước đó. Không đưa tên/tin riêng của người chơi vào tài liệu dự án.
- Trạng thái “đã xem” và lời hứa trong admin không phải bằng chứng tính năng đã hoàn thành.

## Thiết kế triển khai

1. Con chung có một hồ sơ PostgreSQL, cả hai người đồng ý trước khi tạo. Hai người cùng chăm sóc và thấy cùng tiến trình; chăm theo ngày Việt Nam, thao tác đồng thời không trừ tiền hai lần. Giữ nguyên con riêng và thú cưng. Có lựa chọn nhận nuôi hoặc đón bé mới sinh. Kết thúc hôn nhân không làm mất tiến trình của bé.
2. Ở chung có lời mời/đồng ý/từ chối/rời nhà rõ ràng, giữ tài sản riêng và các nhà đang ở chung. Làm rõ góp quỹ mua nhà; kiểm tra dùng đồ trong nhà chung.
3. Bỏ tổng giới hạn nội thất ở mua, lưu, hoàn tác, màu và dữ liệu đồ của người cùng nhà. Giữ kiểm tra tọa độ, quyền sở hữu, sức chứa mặt bàn và không gian phòng. TV/sofa có hướng trước/sau thực sự.
4. Pha trà/cà phê/làm bánh: tốc độ có lựa chọn, đồng hồ hiển thị và máy chủ dùng cùng quy tắc. Nhập quần áo cho chọn size. Giao diện giải thích đúng trợ lý trong ca và người thuê vận hành quầy.
5. Đối chiếu chuyển khoản/quỹ chung, cuộn đánh giá, xem lương và hướng dẫn uy tín. Kiểm tra các yêu cầu nghề/địa điểm cũ, phân biệt phần đã có và phần chưa có trước khi bổ sung.

## Kiểm tra

- PostgreSQL 17 tách biệt tại localhost; không đọc/ghi DB thật để thử tính năng.
- Kiểm thử giới hạn hơn 60 món, lưu/tải/màu/hướng/đồ người cùng nhà.
- Kiểm thử hai tài khoản: đồng ý, chăm đồng thời, retry, ly hôn/xóa tài khoản, lời mời cũ.
- Kiểm thử đồng hồ, stock size, thanh toán và giao diện điện thoại.
- Cập nhật bảng đối chiếu mỗi yêu cầu với code/test và trạng thái thực tế; không đánh dấu xong khi chưa có bằng chứng.

## Tiến độ

- [x] Đọc nguồn mới trên admin và chat chung/nhóm.
- [x] Gia đình và ở chung: đồng ý hai bên, chăm chung, bản chăm riêng khi chia tay, dùng đồ người cùng nhà đúng quyền.
- [x] Nội thất không giới hạn và đổi hướng trước/sau của TV, sofa.
- [x] Thao tác nghề: tốc độ 1×/2×/4×, chọn size nhập kho, đổi nghề dễ tìm, giải thích trợ lý.
- [x] Phân loại các yêu cầu còn lại trong bảng đối chiếu; giữ rõ mục mở rộng và mục chưa tái hiện.
- [x] Kiểm tra tích hợp, review độc lập và báo cáo phần đã hoàn tất/chưa xác minh.

## Kết quả kiểm tra hiện tại

- 70 kiểm tra chuyển xu/hướng dẫn/live effects/đi chơi chạy thành công trên PostgreSQL riêng (`output/feedback-parent-final.log`).
- 48 kiểm tra tích hợp mới về con chung/nội thất/dùng đồ chung/thao tác nghề chạy thành công (`output/feedback-integration-final.log`).
- Sau review, thay cắt bỏ kỷ niệm cũ bằng lưu archive; 7 kiểm tra hoạt động cộng đồng chạy thành công, gồm lưu PostgreSQL và retry.
- Node kiểm tra gia đình, chuyển xu không quota, thao tác đi chơi và gesture cuộn/đóng bảng đều thành công.
- Sau các sửa do review:64 kiểm tra family/bank_xfer/community/guides chạy thành công trong47,382giây (`output/feedback-review-final.log`).
- 12 kiểm tra hướng dẫn UI/review/admin chạy thành công; 10 tình huống chat lịch sử/reconnect và bộ Node admin user đều thành công. Kiểm tra cú pháp35file JavaScript đã đổi và `git diff --check` thành công.
- Review độc lập đã đóng các phát hiện. Thử đồng thời chăm con và ly hôn trên PostgreSQL: trừ4xu đúng một lần, cả hai bản chăm riêng đều giữ tiến trình mới, không deadlock.
- Thử ứng dụng thật ở 390×844 với tài khoản mẫu trong DB riêng: đăng nhập, mở gia đình, chăm bé từ65 lên100, ví3164→3160, tải lại vẫn giữ mục đã chăm; hộp thoại rộng378px không tràn ngang. Đưa con chung lên trước thiệp cưới sau kiểm tra này.
- Có một kiểm tra giới hạn kích thước JSON hành trình đã lỗi trên HEAD gốc trước các sửa này:10865byte >8650. Bản hiện tại10942byte; không nâng ngưỡng test để che lỗi.

## Sửa bổ sung sau review

- Mã thanh toán chăm con dùng hash toàn bộ người chơi và request id; tránh hai mã dài có chung tiền tố bị hiểu nhầm là đã trả tiền. Regression dùng hai mã64ký tự xác nhận sữa4xu + quần áo18xu trừ đủ22xu, retry không trừ lại.
- Khi tài khoản gần đầy, truy vấn nhận chuyển khoản chọn các khoản còn vừa số dư trước giới hạn trang. Một hàng dài khoản lớn đang chờ không chặn khoản nhỏ đến sau.
- Kỷ niệm cộng đồng cũ chuyển vào archive trong cùng transaction, thay vì bị bỏ khi quá42dòng gần nhất.

## Lưu ý phát hành

Schema PostgreSQL tăng lên18 cho con chung/lời mời/bản chăm riêng. Chưa chạy migration trên DB người chơi trong lượt này. Giao dịch lớn cần giới hạn lịch sử ngân hàng/ví mới (±1tỷ); trước khi rollback về bản cũ phải mang theo phần validation này, nếu không bản cũ có thể từ chối bản lưu sau giao dịch lớn. Các kiểm tra tương thích bản cũ với giao dịch nhỏ không bảo đảm rollback cho giao dịch lớn.
