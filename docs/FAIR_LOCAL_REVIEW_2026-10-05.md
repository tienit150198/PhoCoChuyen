# Kiểm tra hội chợ local — 05/10/2026

## Phạm vi và trạng thái

Theo yêu cầu chơi thử local trước, chưa deploy và chưa đăng thông báo. Preview: http://127.0.0.1:59386/.

Bản local lấy từ gói release `1.7.15-fair-stability`, chép riêng bốn tệp hội chợ đã sửa. Không lấy `app.js` đang có thay đổi Phaser của công việc khác. Dùng PostgreSQL và tài khoản test riêng; tiền, kết quả và giao dịch bên dưới đều là dữ liệu local.

## Các nguyên nhân đã tái hiện và sửa trong lượt này

1. **Nút Phóng chờ thả tay mới bắn.** Canvas dùng `pointerdown`, nút lại dùng `click`. Giữ nút 200 ms khiến dao chờ thêm khoảng 200 ms dù chưa gọi API. Nút nay nhận ngay khi nhấn, chặn click tương thích phát sinh sau đó để không bắn hai lần; vẫn dùng được Space/Enter. Thử Chromium chuột/chạm: khoảng 202 ms → 0,1 ms đến thao tác phóng; WebKit chuột: 211 ms → 0 ms. Đây là phép đo callback, không phải toàn bộ thời gian vẽ.

2. **Dao nhảy khi chạm bia hoặc nhận kết quả.** Góc cắm trước đây được thay bằng các vị trí chia đều trong chế độ may rủi; đường bay và vị trí cắm cũng dùng bán kính khác nhau. Nay giữ góc cắm vật lý, dao chờ kết quả quay theo bia, dao thua nảy từ đúng vị trí, bảng kết quả giữ hướng quay đang có. Test tái hiện được bước nhảy 148 px trước khi sửa. Server vẫn quyết định thắng/thua như cũ.

3. **Vòng không nhìn như ôm cổ chai, và nhiều vòng trúng bị gộp.** Vòng cũ có lỗ quá hẹp và vẽ toàn bộ trước cổ chai. Nay tách cung sau/trước, cổ chai che cung sau, mỗi lần trúng có một vòng riêng xếp quanh cổ chai. Vòng chờ kết quả có nét đứt và nhãn chờ; không báo trúng trước phản hồi server. Kiểm tra cả năm vòng cùng một chai.

4. **Cào vé sau khi đóng/mở nhanh khởi tạo canvas 1×1.** Phản hồi mua vé đến khi hộp thoại đóng đã khởi tạo canvas không có kích thước, khiến lần mở sau một chạm cào hết. Nay đợi hộp thoại mở và có kích thước thật. Vé đã mua và phần đã cào được giữ, không mua lại.

Không thay đổi xác suất, mức cược, tiền thưởng, số dao hay tốc độ bia trong lượt sửa này.

## Chơi qua giao diện và HTTP thật

| Luồng | Kết quả local |
|---|---|
| Phóng dao | Bắt đầu với 10.921 xu; đặt 5 còn 10.916; phóng đủ 11 dao, qua màn, dừng nhận 6 → 10.922. |
| Ném vòng | Trúng 5/5; chai 2 có 3 vòng, chai 4 có 2 vòng; hình đủ 5 vòng; ví 10.898 → 10.921, đúng +23. |
| Bầu cua | Đặt 5 vào Bầu; kết quả cua/cá/tôm; trừ đúng 5. Thời gian mở bát 5 giây là cấu hình hoạt cảnh hiện có. |
| Chiếu trong | Cược Chẵn 10; kết quả 2 đỏ; cộng đúng 10. |
| Lô tô | Mua vé, gọi số nhanh, chạy đến kết thúc ván với NPC thắng. |
| Ô ăn quan | Chơi 8 nước đến hết ván, kết quả 13–57; không lỗi trang hoặc request. |
| Chụp ảnh | Chụp đủ 4 kiểu; tải được PNG 900×2700, 1.419.731 byte. |
| Vé cào | Cào tay đến 20%, cào hết, nhận đúng giải; tiếp tục thử 3 vé qua API thật. |
| Đồ ăn | Kẹo bông trừ đúng 2 xu, tăng no bụng. |
| Vay/trả xu | Nhận 100, trả 120, dư nợ về 0. |
| Bảng vàng | Hiện cả hai tài khoản local, lời và thứ hạng đúng. |

Lượt IAB sau cùng không ghi nhận lỗi JavaScript. Ba luồng ô ăn quan/chụp ảnh/vé cào tự động qua toàn app có 12 lệnh HTTP 200, không request thất bại. Test dùng phản hồi điều khiển riêng để bao phủ mất mạng, đóng/mở khi đang chờ, phản hồi trễ, thử lại và chống trả thưởng trùng; không gọi đó là đo server thật.

## Độ mượt và giới hạn phép đo

- IAB đang mở, chơi phóng dao: 75 FPS; nhấn đến frame dao khoảng 7,6 ms; thời gian vẽ p95 0,4 ms, tối đa 0,5 ms; khoảng cách frame trong cửa sổ đo 13,6 ms.
- Cả lượt làm việc trước đó từng có khoảng giật 360 ms và một đoạn 1 FPS. Chưa xác định được nguyên nhân đoạn 1 FPS; không gán cho server hay nền trình duyệt khi chưa đủ bằng chứng. Đã bổ sung trạng thái visible/focus vào công cụ đo **chỉ ở local** để phân biệt khi tái hiện.
- Ba API mua vé cào đo toàn HTTP: 64,2 / 27,9 / 300,0 ms. Metrics phần `Store.command` cùng ba lệnh: tổng 45,8 ms, tối đa 18,2 ms. Không kết luận PostgreSQL chậm từ số tổng.
- Đo tách pha trên server chẩn đoán local dùng đúng bản app: các lệnh đã ấm khoảng 11–14 ms; lúc hết hạn kiểm tra file 2 giây, việc quét chữ ký asset thêm 27–33 ms, tổng HTTP khoảng 39–46 ms. Chỉ đổi cấu hình chẩn đoán kiểm tra file sang 300 giây cho kết quả khoảng 11–14 ms kể cả sau khi chờ 2,1 giây. Không sửa source server. Cấu hình mặc định nhiều worker dùng 300 giây; không lấy độ trễ quét file Windows để suy ra production. **Chưa tái hiện lại mức 300 ms trong phép đo tách pha**, nên quét file chỉ giải thích phần trễ đã đo, chưa giải thích toàn bộ ngoại lệ cũ.
- Các số FPS là trên máy local hiện tại, không phải cam kết cho mọi điện thoại hoặc tải production. Bản này chưa được kiểm chứng dưới tải production.

## Kiểm chứng

- 86/86 test JS hội chợ đạt sau bản sửa cuối.
- 41/41 test Python phóng dao, xác suất và định danh ván đạt với PostgreSQL test; bao gồm chống xử lý trùng.
- Chromium + WebKit, rộng 390 và 1280: 36/36 kiểm tra ném vòng đạt, không lỗi JavaScript.
- Chromium + WebKit: 6 luồng phóng dao mỗi trình duyệt đạt, không lỗi JavaScript.
- Kiểm tra lại WebKit: 92 trạng thái ứng tuyển hiện đủ nội dung, các nút thao tác tiếp cận được; đóng xong giải phóng modal. Đây là fixture UI/CSS, không phải 92 lần phỏng vấn qua server.
- Diff check các tệp sửa đạt.

## Bằng chứng

- `output/playwright/knife-input-audit/RESULTS.md`, `input-before.json`, `input-after-touch-keyboard.json`.
- `output/playwright/knife-interaction/browser-geometry-fix-flows.json`.
- `output/playwright/ring-geometry/after/results.json` và ảnh từng kích thước/trình duyệt.
- `output/playwright/fair-all-local/fullapp-three-report.json`, `scratch-repeat-http.json`, `final-node-tests.txt`.
- `output/playwright/fair-all-local/scratch-http-phase-report.json`, `final-source-manifest.json`.
- `output/playwright/fair-all-local/chromium-chance-report.json`, `webkit-chance-report.json`.
- `output/playwright/job-application/webkit-results.json`.

Các bản đo chỉ lưu local; không chứa mật khẩu trong báo cáo. Công cụ `fair-local-probe.js` và thay đổi index để bật nó không thuộc bản phát hành.
