# Kiểm tra hotfix 2.0.1 — 11/10/2026

## Phạm vi

- Nhân vật ngoài phố: sửa biên frame atlas, mảnh ảnh thừa, vị trí kính theo mắt, mũ khi quay lưng, màu vải và vị trí phụ kiện. Bơi/chèo thuyền dùng đường cắt cổ thực tế của sprite, tư thế ngồi có chân nằm trong lòng thuyền.
- Cầu gỗ: lên thuyền từ toàn bộ phần sàn đi được. Bơi tự do: có Lên bờ/Space, phải quay về thang rồi lên, không phải hoàn thành vòng mới được thoát.
- Avatar đứng yên/ngoài màn hình không dựng lại texture và ghi thứ tự vẽ mỗi frame. Đổi màu sprite trực tiếp trên buffer, giữ kết quả từng pixel; không còn cấp phát mảng cho từng pixel.
- Rương chưa nhặt tồn tại qua đợt mới và restart; mỗi 10 phút thêm 3–5. Rương cùng vị trí gom hình và số lượng, mở từng rương. Chỉ người đứng gần có xác nhận vị trí mới nhặt được; server trả 10.000 xu đúng một lần.
- Classic có Ra đảo nhặt rương ở bản đồ và menu Khu phố, dùng cùng Phaser/presence/treasure protocol. Đóng trả lại workplace và giữ newInterface=false.
- Chợ Đen: giảm nhẹ xác suất bắt ngẫu nhiên, giữ điều kiện áp dụng/tiền phạt/thời gian tạm giữ. Không đổi thời hạn Hai ngày vàng, không công bố xác suất.

## Kiểm tra đã chạy

- Build Phaser, TypeScript, kiểm cú pháp JS và Safari 15/iOS 15: 347/347 file JS hợp lệ.
- test:isometric, test:performance-parity, test:living-districts đều đạt. Sau thay đổi classic, chạy lại living-districts và peer tests: shared-island 6/6, peer 11/11.
- Avatar: 38 kiểm tra; đối chiếu bit chính xác trên 24 tư thế atlas × 4 bảng màu × 2 mặt nạ chất liệu với thuật toán cũ.
- Water: 89 kiểm tra Node và 5 backend, gồm cầu tàu, phím Space, thoát bơi chưa hoàn thành, culling giữ người ở mép nhìn. Root đã thử thao tác thực bằng bàn phím trên local.
- Treasure: 22 PostgreSQL/live tests và 12 client tests; đợt cũ, restart, migrate schema38→39, hai người tranh nhặt, lặp request không nhân tiền, refresh phần rương còn lại. Schema39 chỉ thêm hai chỉ mục truy vấn.
- Black-market/jail: 79 tests, 78 pass và 1 skip hiện có do fixture Ông Hai không có ngân hàng. Kiểm biên xác suất và các tác động tiền/tạm giữ không đổi.
- Gate cuối chạy riêng: PostgreSQL/schema/leisure 21/21; live treasure 8/8 trong21,666 giây; black-market/jail 79 trong139,625 giây (1 skip như trên). Lượt gộp trước đó treo khi teardown LISTEN và đã dừng, không tính đạt. Runtime local Python3.10 có race nuốt cancellation trong asyncio.wait_for được tái hiện độc lập; phù hợp dấu hiệu nhưng chưa chứng minh là nguyên nhân chính xác của lượt treo. Không thay mã shutdown trong hotfix này.
- Task compatibility với production2.0.0: 49.440 hàng sinh trong 40 ngày, đủ50 nghề, đạt.

## Quan sát trực tiếp và hiệu năng

Local dùng PostgreSQL riêng ở loopback55439, HTTP18893/live18894; không dùng save người chơi production làm fixture.

- Trình duyệt: lên thuyền ở đầu cầu, chèo/đổi hướng, bị cầu chặn, xuống thuyền; xuống hồ, bơi xa, nút Lên bờ hướng dẫn về thang, về thang và thoát. Pool trên bản đồ nằm lớp nền, không che người trong lượt kiểm hiện tại.
- Classic: tắt Giao diện mới, mở Ra đảo nhặt rương; đi bằng phím và chạm rương; guest bị từ chối nhặt với thông báo đăng nhập đúng như server quy định; đóng về Trà Mây & Trân Châu, ví460 và ngày1 giữ nguyên. Rương cộng dồn có nhãn số lượng.
- Tải lần đầu29 avatar chuyển động trên canvas390×680 trong trình duyệt desktop: baseline RAF max480,2ms, 4 lần >50ms; sau sửa recolour, 1.133 khoảng frame trong15 giây, p95 13,4ms, max13,6ms, không lần >33ms. Texture build max0,7ms; xử lý cả lô peer max11ms. Đây là kịch bản cụ thể trên máy test, không phải kết quả điện thoại thật hoặc 1.000CCU.
- Desktop29 peer đứng yên và người chơi đi: CPU JS p95 từ0,9 xuống0,5ms; frame p95 cùng khoảng13,5ms. Không suy diễn tăng FPS từ số đo này.
- 10.000 rương chưa nhặt/100 vị trí thử: payload khoảng10,5KB, truy vấn local median2,625ms. Bản đồ hiện có92 điểm spawn; số sprite giới hạn theo vị trí, không theo tổng rương. Hàng database vẫn tăng khi không ai nhặt, đúng yêu cầu tích lũy.

## Giới hạn và bằng chứng

- Lượt local ban đầu: IAB viewport override không đổi DOM thực1280×720, không tính là kiểm mobile/tablet. Sau triển khai, tab production áp dụng được override sau reload: DOM xác nhận390×844 (lên thuyền/chèo),834×1112 (phố),1280×720 sau reset (desktop). Đây là kiểm bố cục và thao tác bằng trình duyệt desktop, không thay cho đo FPS/cảm ứng trên điện thoại thật.
- Atlas minh họa vẫn có tóc nam/tóc búi nữ vẽ sẵn. Kính/mũ/màu trang phục đã sửa nhưng chưa có silhouette riêng cho mọi kiểu tóc trong tủ đồ. Không coi đây là kiểm chứng mọi tổ hợp avatar.
- Không tìm thấy lỗi pool đè người trong lượt tái hiện hiện tại; chưa khẳng định mọi tọa độ/thiết bị đều hết lỗi.
- Bằng chứng cục bộ: output/hotfix-2.0.1/ (logs, perf JSON, rowing-fixed-desktop.png, classic-shared-island.png); output/avatar-street-fix/; output/water-review-20261011/.
- Bản sao lưu production trước hotfix hoàn tất mã0, đọc mục lục pg_restore thành công; chưa diễn tập restore. Chi tiết gói và kết quả production được ghi riêng trong báo cáo triển khai sau khi rollout.
