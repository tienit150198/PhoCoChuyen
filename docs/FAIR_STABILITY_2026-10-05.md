# Hội chợ: lỗi kết quả, vòng đời màn hình và độ mượt — 05/10/2026

## Nguyên nhân đã tái hiện

1. **Ném vòng:** mọi vòng dùng hoạt cảnh chờ rơi xuống rồi biến mất; đáp án máy chủ chỉ đánh dấu chai, không diễn lại vòng trúng. Sửa để vòng chờ nằm phía trên cổ chai, sau đó thể hiện đúng từng kết quả máy chủ và giữ dấu vòng trên chai trúng.
2. **Phi đao:** dao cuối được coi là cắm trúng trước khi có đáp án; phản hồi thua muộn làm nó bật ngược. Sửa trạng thái chờ xác nhận, không phát âm thanh trúng trước đáp án. Không đổi xác suất hay tiền thưởng.
3. **Phi đao khi mạng chậm:** lỗi phản hồi làm mất các lần bấm; callback hết giờ có thể ghi đè lượt mới hoặc tự hiện thua dù chưa xác nhận. Giữ các lần bấm, thêm kiểm tra kết quả có chủ động, đọc lại trạng thái trước khi gửi lại. Lệnh mang mã bia; máy chủ từ chối mã bia cũ kể cả cùng số màn. Máy khách cũ vẫn được hỗ trợ.
4. **Giật lúc trả kết quả:** mỗi cập nhật hội chợ dựng lại DOM nơi làm việc phía sau và đánh dấu canvas cảnh cần vẽ. Hoãn phần bị che, đóng hội chợ mới vẽ trạng thái mới nhất một lần. Cache hình dao thay vì tạo gradient/đường vẽ cho từng dao mỗi frame.
5. **Đổi quầy:** vòng ném dở chặn cập nhật tất cả quầy; ô ăn quan tiếp tục 40 lần vẽ và phát âm thanh sau khi đóng. Giới hạn trạng thái bận theo quầy đang xem; dừng hiệu ứng khi rời quầy, giữ kết quả máy chủ.
6. **Chụp ảnh:** thanh toán phản hồi muộn có thể tự bắt đầu chụp sau khi rời phòng. Giữ vé đã trả tiền, chỉ dùng khi người chơi chủ động chụp; callback in ảnh cũ không mở lại màn hình.
7. **Bảng kéo trên điện thoại:** mất pointer capture/focus để lại transform, timer đóng bảng cũ có thể đóng bảng vừa mở. Theo dõi đúng pointer; hủy transform/timer khi mất capture, blur, ẩn trang hoặc mở bảng khác.

## Kiểm chứng

- 146 kiểm thử Python đạt, gồm hội chợ, luật thắng/thưởng, PostgreSQL/idempotency, mã bia, ứng tuyển.
- 76 kiểm thử JavaScript đạt, gồm kiểm tra âm thanh start/stop khi đóng bảng.
- Ném vòng/đổi quầy/ô ăn quan/chụp ảnh: 12 ca Chromium, không lỗi JS.
- Phi đao: Chromium và WebKit mỗi bên 6 luồng thao tác/mạng lỗi đạt, không lỗi JS.
- Ứng tuyển: 46 trạng thái engine, 6 bước; mỗi trình duyệt Chromium/WebKit kiểm tra 92 lần dựng/morph với CSS thật, giữ cuộn, hướng dẫn và ví tiền. Chromium kiểm tra touch/capture thật cho lỗi kéo bảng.
- Ảnh thân bảng trắng/chỉ còn tiêu đề trên iPhone **chưa tái hiện chính xác**. Đã sửa lỗi gesture xác định được; không sửa suy đoán dữ liệu ứng tuyển. Log `room.tasks` gần nhất 11:57 là lỗi trước bản đang chạy và đã có sửa fallback nghề.

## Số đo và giới hạn

Lúc 14:11, cửa sổ 5 phút có 3.148 lệnh: P50/P95/P99 **125/457/840 ms**; upstream **122/397/552 ms**. Live có 83 kết nối/82 người chơi, không có kết nối bị cắt theo bộ đếm live. Không có bằng chứng nghẽn hết 9 core từ lần kiểm tra này; không tăng worker mù quáng.

Trong cửa sổ đo theo action, `fair_kn_throw` chỉ có 6 mẫu: trung bình **78,7 ms**, lớn nhất **141,5 ms**; mẫu ít, không suy thành P95 ổn định.

Đo riêng canvas phi đao, Chromium CPU×4, 11 dao, ABBA mỗi mẫu 3 giây: draw P95 **2,7–2,8 → 1,7 ms**; frame **172/179 → 181/181**; gradient dựng lại **1.892/1.969 → 0**. Đây là đo module, không phải FPS toàn ứng dụng hay máy iPhone của người chơi.

Phần API chậm đuôi vẫn liên quan chi phí xử lý/lưu bản game nhiều MB đã nêu trong `PERFORMANCE_ROUND1_2026-10-05.md`. Bản sửa này tập trung lỗi hội chợ và giảm giật phía giao diện; không dùng kết quả canvas để tuyên bố toàn bộ API đã đạt vài chục ms.

## Phạm vi đóng gói

Gói nền: `release-1715-knife-smooth`, SHA256 `aa3a3db5768c4adcbce655e37af16b4ac377a2db2ee5de3c5863cbd0e4088a45`. Chỉ overlay các tệp được liệt kê. Workspace đang có một nhánh tích hợp renderer khác sửa chung `app.js`; bản deploy dùng bản app cô lập, giữ renderer hiện hành. Hoàn tác riêng các sửa của đợt này trong bản cô lập rồi minify cho SHA256 **trùng tuyệt đối** app đang chạy `8e11079fc9e752f0314468bef2c984a8947c9a7ca90f8b82aad9c812e95192bc`. Không đụng các chỉnh sửa đang làm chung workspace.

Không thay đổi schema, epoch/salt thị trường, xác suất, giá vé, tiền thưởng hoặc nội dung thông báo.
