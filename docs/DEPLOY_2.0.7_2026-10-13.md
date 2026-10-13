# Xử lý góp ý và phát hành 2.0.7 — 13/10/2026

Triển khai hoàn tất lúc 12:28:04 UTC+7 tại https://phocochuyen.io.vn. Đã trả lời 14 góp ý #354–#367: 8 mục khép lại sau sửa/hướng dẫn/đính chính, 6 mục giữ trạng thái đang xem xét. Câu trả lời được ghi có điều kiện theo phiên bản nội dung và chỉ khi chưa có lời đáp; không ghi đè người chơi sửa hoặc người quản trị khác trả lời.

## Thay đổi đã chạy

- #357: ưu tiên rương khi trùng độ sâu điểm bấm hoặc trùng khoảng cách tương tác phím E với địa điểm. Giữ nguyên thứ tự khoảng cách khác nhau, tầm với và kiểm tra đường đi.
- #362: mỗi quầy có mức vốn giữ lại tùy chọn, mặc định 0. Thu két bù vốn tới mức đó rồi chuyển phần dư vào ví; áp dụng cả thu nhiều quầy. Lưu mức chưa chuyển tiền. Két vào vốn để lại phần vượt trần trong két.
- #360: liệt kê tất cả ca còn mở và nút trở về từng nơi trước khi đi làm nước ngoài.
- #366: giải thích học tiếp theo ngày sống trong game, luôn hiện hướng dẫn sau buổi học và có nút về nơi làm việc để khép ca.
- Bổ sung tiếng Anh. Không thay bảng DB hoặc sửa bản lưu người chơi hàng loạt.

## Đối soát và việc còn mở

- #354: nhật ký và sổ lưu trữ xác nhận 11 khoản sự cố cũ trong ngày nghề số 6, tổng 11.954.832 xu. Cơ chế cũ lấy từ quỹ nghề; mã hiện tại đã bỏ cách trừ này. Không quy nguyên nhân cho lương nhân viên hoặc khẳng định người chơi vi phạm. Không tự hoàn khoản lịch sử; giữ mục đang xem xét. Không còn sự cố loại này chờ áp dụng trong hồ sơ được kiểm tra.
- #355, #358, #363, #364: ghi nhận lần lượt danh sách chọn cho lời nhắn điện thoại, xoay nội thất 90°, tăng kho và bảo vệ tài chính 100%; chưa triển khai các thay đổi đó.
- #367: bản lưu hợp lệ; không có NPC nhân viên để tạo backlog. Đo local chưa thấy nút thắt ở quyết toán hay hàm dựng hộ chiếu. Phép đo không bao gồm DB/mạng/GPU của người chơi; đã hỏi thêm thao tác gây chậm, không tuyên bố sửa lag.
- #356, #361: hướng dẫn sang nhượng quầy và đếm theo khay/giữ để kiểm hàng. #359, #365: phản hồi đính chính; không xóa báo cáo hay thực hiện xử phạt.

## Gói phát hành

- Source đã push main: `53eaad980c35296acd9c3b4c658b683f10f807bf`.
- Release: `/opt/mot-ngay-lam-nghe/releases/2.0.7-20261013122656`.
- Build: `2.0.7+35a197338bc2`.
- ZIP: 103.511.816 byte; SHA-256 `5e3b74f0cc3f375f385723025465691155db91bffc15821641ee5c9b93620208`.
- Dựng từ gói live 2.0.6 và source `ca19d423afe224d0545839908fcbca4c33ed6682`: 1.762 file nguyên byte, 472 asset tái tạo đúng bản minify; thay/thêm 23 file, không xóa, minify 4 asset thay đổi.
- Có guard đường dẫn release, manifest cũ và hash ZIP trước rolling; `KEEP=999` giữ các release cũ.

## Kiểm thử và kiểm chứng

- Lượt Python tổng hợp: **105 đạt** cho du học, quầy giữ vốn, bản dịch, sự cố tài chính và nhập kho. Lượt quầy riêng của worker: 83 đạt; có phần trùng, không cộng thành số test duy nhất.
- Năm suite Node về rương/bản đồ: **34 đạt**; typecheck và build isometric đạt. Kiểm thử rương và giữ vốn được quan sát thất bại trước sửa rồi đạt sau sửa.
- UI giữ vốn trên browser thật 390px kiểm lưu rõ ràng, giữ bản nháp khi đồng bộ, xem trước và số thu thực từ phản hồi. Browser dùng API giả; server money logic có kiểm thử Python riêng.
- Hướng dẫn du học trên browser 390px/1280px: nút đúng nơi, không tràn ngang, không pageerror. Node kiểm ca còn mở sau khép một phần và hướng dẫn hiện cả sau trả lời bài học.
- 349/349 JS đạt cú pháp và Safari/iOS 15; 5 kiểm tra cấu trúc bản dịch đạt.
- Đối chiếu live 2.0.6: **49.440 mẫu nhiệm vụ, 50 nghề, 40 ngày**, tất cả khớp.
- Gói giải nén mới: 2.239 hash khớp; khởi động với PostgreSQL thử riêng; HTTP tạo nhân vật, mở ngày, chống xử lý lặp và xuất bản lưu đạt.
- Sau triển khai: game và live active đúng cwd; bridge inactive; 8 mẫu health trả đúng build. 1.551 file còn trên máy chủ đúng hash; 688 file tests/artifacts bị installer loại có chủ đích. Năm asset công khai khớp ZIP. Log kiểm 19 dòng game và 7 dòng live không có Traceback/CRITICAL/ModuleNotFoundError.

Ba kiểm tra historical-server 1.4.31/1.5.2 vẫn lỗi trên baseline do chứng chỉ/nghề hiện tại, không tính là đạt. Minifier báo ba khóa lặp trong thư viện của bundle Phaser; build hoàn tất và các kiểm tra liên quan đạt.

## Quay lui

2.0.6 chấp nhận bản lưu có trường reserve tùy chọn; đã kiểm validator trên bản live đó. Nếu quay về 2.0.6, chức năng giữ vốn không được áp dụng dù trường vẫn giữ trong dữ liệu. Không quay về 2.0.5 vì thiếu hỗ trợ chứng chỉ.

Script `/root/mnl-business-licenses-disable.sh` được cập nhật guard cho 2.0.7, kiểm cú pháp và chưa chạy; bản trước được lưu riêng. Khi cần tắt chứng chỉ, dùng mã hiện tại với hai cờ OFF như tài liệu vận hành. Không khôi phục DB cũ để quay lui mã.

Root MANIFEST và LIVE_BASE được cập nhật sau triển khai; commit tài liệu này là bằng chứng, không phải source ref của gói đã chạy. Bản lưu, ảnh và nội dung trả lời chi tiết nằm trong output riêng, không commit dữ liệu tài khoản.
