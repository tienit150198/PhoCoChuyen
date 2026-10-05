# Phát hành 1.7.7 — Nhà & Gia đình và lời đáp cử chỉ

Rolling deploy hoàn tất 19:33:23 UTC+7 ngày 04/10/2026, trước khi nhận chỉ dẫn dừng deploy. Build `1.7.7+762710f62176`; release `/opt/mot-ngay-lam-nghe/releases/1.7.7-20261004193225`. Game và `mnl-live` active; bridge inactive. Live dùng PostgreSQL và bật home.

**Chỉ dẫn mới của người dùng:** từ sau bản này, chỉ sửa và kiểm tra local; chỉ deploy khi người dùng nói rõ. Khi người dùng yêu cầu phát hành, ghi mục “Có gì mới” cho nội dung được phát hành. Bản 1.7.7 không thêm thông báo “Có gì mới”. Không tự deploy bản sửa tiếp theo.

## Thay đổi

- Nhà & Gia đình, Vào nhà, Mời về ở, Con chung nằm ngay dưới nhân vật trong danh sách Hành trình. Lời mời nhận nằm đầu trang; người gửi thấy trạng thái chờ. Điều kiện đón con nói rõ tiến trình cả hai; các lựa chọn phụ được thu gọn.
- Người gửi bước tới và làm động tác. Người nhận tự chọn Đáp lại, Ngại ngùng, Giận dỗi hoặc Để sau. Đáp lại khiến cả hai tương tác, không trả lời thì chỉ người gửi làm. Lời đề nghị hết sau 15 giây; rời phòng, di chuyển, mất quyền ở chung đều hủy.
- Giữ ngoại hình và trang phục. Có tư thế tĩnh khi giảm chuyển động; giữ tiêu điểm nút đáp lại qua lần vẽ lại phòng.

## Kiểm chứng

- 47 kiểm tra family/live-home và 90 kiểm tra hôn nhân, nhà, trang trí và dùng đồ chung qua trên PostgreSQL thử nghiệm.
- Sáu bộ JavaScript family, family UX, home affection, home crowd, home redraw và journey experience qua; 517/517 file JavaScript hợp lệ.
- Hai tài khoản thử nghiệm trên trình duyệt: gửi/nhận lời mời về ở, gửi/nhận lời mời đón con, chăm bé cập nhật dấu hoàn tất ở cả hai. Kiểm tra bố cục 390px.
- Hai phiên live riêng: gặp nhau cùng phòng, hôn và đáp lại, ôm/ngại ngùng, thả tim/giận dỗi, Để sau, rời phòng. Quan sát động tác trên cả hai màn hình, nút phản hồi ở trên sàn phòng.
- Review độc lập phát hiện và đã xác nhận sửa hai lỗi: mất lời mời khi hai người gửi đồng thời; mất tiêu điểm bàn phím khi hiệu ứng hết. Có kiểm tra hồi quy mô phỏng chuỗi sự kiện thật.
- 21 kiểm tra hướng dẫn và gói tiếng Anh qua; sửa 24 mẫu dịch dùng số thứ tự biến không hợp lệ. Trên nguồn đóng gói, chạy lại 42 kiểm tra family/guide/i18n đều qua.
- Đối chiếu 40.800 mẫu nhiệm vụ qua 41 nghề, ngày 1–40: tương thích. ZIP chạy qua HTTP trên PostgreSQL riêng; 1.168 hash source/asset đều khớp.
- Sau deploy: 6 mẫu HTTPS health trả 200 đúng build, 8 file gia đình/cử chỉ bằng đúng byte trong ZIP. Kết quả `output/release-177/production-check.json`.

## Gói và vận hành

Gói lấy nguồn sạch 1.7.6 và chép các file được liệt kê trong `output/release-177/changed-files.json`. Không gom toàn bộ workspace đang có nhiều thay đổi khác.

ZIP `output/release-177/mnl-1.7.7.zip`, SHA256 `ea6799b6019466d302ca58221a5030285186bbbb989e60964347c044fe83b529`; 24 file thay đổi so với nguồn phát hành trước. Hash trên server khớp gói local. Preflight xác nhận bản trước 1.7.6 và bridge 8767 trống.

Kết quả kiểm tra gói: `output/release-177/package-verify.json`.

Không đổi schema PostgreSQL hoặc định dạng bản lưu. Trạng thái cử chỉ chỉ sống trong phiên live. Có thể quay về 1.7.6 nếu cần; giữ lưu ý tương thích handmade khi cân nhắc bản cũ hơn trong tài liệu 1.7.6.

## Bản sửa local đang chờ người dùng yêu cầu deploy

Kiểm tra log sau phát hành phát hiện `KeyError: bar_pace` ở `cafe_bakery.public_data` cho bản lưu cũ đang chiết espresso. Projection đọc trước lệnh migrate, nên thiếu giá trị mặc định 1×. Đã tái hiện bằng regression test thất bại, thêm default vào bản sao projection (không sửa bản lưu khi đọc), chạy 69 kiểm tra café/bakery thành công. Chỉ sửa local `game/careers/cafe_bakery.py` và `tests/test_career_cafe_bakery.py`; chưa đưa lên server và chưa thêm “Có gì mới”. Lỗi bản lưu cũ này vẫn có thể xảy ra trên production cho tới đợt phát hành được người dùng yêu cầu.
