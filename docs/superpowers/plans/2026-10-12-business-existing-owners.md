# Kiểm tra chủ nhiều quầy trước khi áp dụng chứng chỉ kinh doanh

Kiểm tra DB production `phocochuyen` ngày 12/10/2026 bằng các giao dịch chỉ đọc. Không cập nhật bản lưu, quyết toán thu nhập, cấp giấy, trừ tiền, deploy hoặc restart dịch vụ. Release được xác nhận trước khi đọc: `2.0.5-20261011224257`.

## Phạm vi và thời điểm

- Tài khoản đăng ký: 2026-10-12T04:54:19.766825+07:00 đến 2026-10-12T04:56:34.565962+07:00; đọc đủ 6336 tài khoản trong giới hạn UID chụp đầu lượt. Thiếu bản lưu: 0; bản lưu không đọc được: 0.
- Bản lưu khách chưa liên kết tài khoản tại thời điểm đọc: 2026-10-12T04:57:11.825479+07:00 đến 2026-10-12T05:02:27.227173+07:00; kiểm tra 54598 bản lưu. Không có khóa quay: 33309; bản lưu ứng viên không đọc được: 0.
- Từng đợt truy vấn nhỏ theo khóa chính, transaction read-only, timeout 5 giây và nghỉ giữa các nhóm; không giữ khóa hàng hay snapshot kéo dài. Người chơi vẫn có thể giao dịch trong lúc quét, nên đây là quan sát trong cửa sổ thời gian, không phải ảnh chụp toàn DB tại một mili giây.
- Bản lưu khách không đồng nghĩa người duy nhất; không cộng với tài khoản để tuyên bố tổng số người. Không lọc riêng tài khoản quản trị/thử nghiệm. Chỉ lưu kết quả tổng hợp, không xuất tên, mật khẩu, cookie hay toàn bộ state.

## Quy mô sở hữu

| Số quầy đang sở hữu | Tài khoản đăng ký | Bản lưu khách |
|---|---:|---:|
| 1 | 206 | 30 |
| 2 | 49 | 1 |
| 3-5 | 15 | 0 |
| 6-10 | 2 | 0 |
| 11-20 | 3 | 0 |
| 21+ | 0 | 0 |
| Tổng chủ/bản lưu có quầy | **275** | **31** |
| Tổng quầy | **403** | **32** |

| Loại quầy | Trong tài khoản đăng ký | Trong bản lưu khách |
|---|---:|---:|
| Xe đẩy | 212 | 23 |
| Sạp | 75 | 8 |
| Ki-ốt | 116 | 1 |

Tài khoản đăng ký: 69 chủ có từ hai quầy; 20 chủ có từ ba quầy. Nhóm từ ba quầy sở hữu 99 quầy. Có 10 chủ sở hữu từ ba ki-ốt. Nhiều nhất 12 quầy; hai bản ghi đứng đầu có 12 ki-ốt mỗi bản ghi. Các quy mô tiếp theo gồm 11 quầy (10 ki-ốt, 1 sạp), 8 ki-ốt, 6 quầy (5 ki-ốt, 1 xe đẩy).

Bản lưu khách: 1 có từ hai quầy; 0 có từ ba quầy; 0 có từ ba ki-ốt; nhiều nhất 2 quầy.

## Chứng chỉ và tình trạng bản lưu

- Không có chủ nào trong các nhóm được kiểm tra đạt các mã mới đang đề xuất: `business_basics`, `business_advanced`, `business_chain`. Các mã này chưa được triển khai trong công việc hiện tại; không coi việc chưa có chúng là vi phạm.
- Trong tài khoản đăng ký, 258/275 chủ có ít nhất một chứng chỉ nghề hiện có; 17 chưa có chứng chỉ nghề nào trong `journey.certificates`. Cả nhóm 20 chủ từ ba quầy đều có chứng chỉ nghề khác; không tự quy đổi sang chứng chỉ kinh doanh.
- Trong bản lưu khách, 26/31 chủ có chứng chỉ nghề hiện có; 5 chưa có. Nhóm từ ba quầy không có chứng chỉ nghề: 0.
- Việc đã đạt chứng chỉ không chứng minh đã trả học phí: hệ thống cũ có cả tự học miễn phí. Lượt kiểm tra này xét quyền sở hữu giấy, không truy lịch sử phương thức học/thanh toán.
- Trong tài khoản đăng ký, 266 chủ với 392 quầy có bản lưu cập nhật trong bảy ngày trước thời điểm bắt đầu; cả 20 chủ từ ba quầy thuộc nhóm này. “Cập nhật bản lưu” không phải chứng cứ đăng nhập hay thời gian online.
- Có 119 quầy tài khoản đăng ký chưa có NPC, 36 quầy đánh dấu tạm đóng. Không coi mọi quầy đang sở hữu là đều tạo thu nhập tự động; trạng thái đọc chưa được quyết toán/làm mới.

## Cách xử lý đề xuất cho người chơi cũ

**Cập nhật theo ý kiến người dùng ngày 12/10/2026:** Công an trong game kiểm tra chủ nhiều quầy và yêu cầu đi học. Hướng này thay thế đề xuất miễn yêu cầu cho cơ sở cũ vô thời hạn. Các ngưỡng và thời hạn dưới đây là đề xuất thiết kế, chưa triển khai.

1. Từ ba quầy đang sở hữu, kể cả quầy tự tạm đóng, phát sinh một hồ sơ kiểm tra theo chủ. Một chủ có 12 quầy nhận một yêu cầu bổ sung giấy, không phải 12 khoản học phí. Theo cửa sổ DB đã đọc, ngưỡng này bao gồm 20 tài khoản đăng ký có tổng 99 quầy; không có bản lưu khách nào đạt ngưỡng.
2. Lần đầu công an giao biên bản nhắc bổ sung chứng chỉ, hiển thị cấp còn thiếu, học phí thực tế và nút đi học. Đề xuất cho 72 giờ thực từ lúc thông báo được giao trong phiên chơi; không tính từ ngày deploy hay hồi tố thời gian trước khi người chơi nhận thông báo. Trong hạn, quầy cũ vẫn bán bình thường.
3. Mức học đề xuất: nhiều xe đẩy/sạp cần cơ bản; có ki-ốt cần quản lý cửa tiệm; từ ba ki-ốt cần quản lý chuỗi. Quy mô chuỗi xe đẩy/sạp rất lớn cần tính thêm trước khi chốt; không dùng mặc định “quầy thứ ba = cấp 3”. Các khóa học có phí và tiên quyết như nhau cho chủ cũ/mới.
4. Quá hạn chưa đủ giấy thì tạm dừng nhận đơn mới tại các quầy vượt quyền vận hành. Người chơi được chọn quầy tiếp tục bán trong giới hạn hợp lệ; riêng chủ cũ chưa đạt cấp nào được giữ một quầy hiện có làm nguồn kiếm học phí trong đợt chuyển đổi. Đây là ngoại lệ chuyển đổi, không phải quyền mở mới ki-ốt miễn chứng chỉ. Không tịch thu, hạ mặt bằng hay tự trừ tiền. Đơn đã nhận được xử lý xong, két/quỹ/hàng/nhân viên được bảo toàn.
5. Thi đạt cấp yêu cầu thì hồ sơ hoàn tất, gỡ hạn chế do kiểm tra; không tự mở lại quầy mà chủ đã chủ động đóng. Đạt cấp trung gian mở lại phần quyền tương ứng. Bán bớt quầy làm giảm cấp cần có thì đánh giá lại; tự tạm đóng không làm giảm số sở hữu. Không thể nộp phạt thay việc học hoặc đóng/mở quầy để đặt lại hạn.
6. Ví dụ chủ 12 ki-ốt phải hoàn thành các khóa còn thiếu đến cấp 3 dù không mở quầy thứ 13. Tổng học phí từ đầu theo chỉ số giá trong phép tính là 8.250 xu nếu đậu ngay, không nhân với 12. Chứng chỉ nghề cũ không thay cho ba chứng chỉ kinh doanh mới.
7. Bộ validate/save vẫn phải đọc được mọi bản lưu cũ. Hồ sơ kiểm tra là trạng thái vận hành mới có migration tùy chọn, không phải lý do từ chối tải/lưu. Học phí chỉ trừ khi người chơi đăng ký; lần kiểm tra đầu không phạt tiền.

Trước triển khai cần chốt ngưỡng chuỗi quầy nhỏ, thời hạn và chi phí duy trì trong lúc bị hạn chế. Với quầy bị dừng, phải hiển thị rõ tiền thuê/lương còn phát sinh theo luật hiện tại và cho phép quản lý tài sản; không ngầm cam kết dừng quầy là miễn mọi chi phí.

## Bằng chứng và tái lập

Script: `D:/projects/Mot_ngay_lam_nghe/_business_balance_20261012/audit_db_readonly.py`.

Kết quả tổng hợp: `db-registered-owners.json` và `db-guest-owners.json` trong cùng thư mục. Script dùng PostgreSQL peer authentication trên máy chủ; không chứa thông tin đăng nhập SSH. Các phép đối chiếu tổng nhóm/chủ/quầy/ngành hàng đã khớp trước khi viết báo cáo.
