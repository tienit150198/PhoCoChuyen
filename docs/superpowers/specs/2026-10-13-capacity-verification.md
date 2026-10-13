# Kết quả kiểm tra sức chứa — local, chưa phát hành

Ngày 13/10/2026. Nguồn trước thay đổi: `54f146be`. Không push, đóng gói, deploy hay sửa DB thật. PostgreSQL thử nghiệm chỉ ở 127.0.0.1:55432; trình duyệt chạy server local với dữ liệu giả.

## Lượt tích hợp cuối

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, đặt `TEST_DATABASE_URL` đến DB local, rồi chạy:

```text
python -m pytest -q tests/test_capacity_catalog.py tests/test_shared_storage_expansion.py tests/test_boba_storage_capacity.py tests/test_farm_storage_capacity.py tests/test_prepared_storage_capacity.py tests/test_warehouse_convenience.py tests/test_task_compat.py tests/test_i18n_pack.py
```

**76 passed, 35,57 giây.** Bao gồm danh mục 25 nhánh mới/250 bậc, mua tuần tự/trừ đúng tiền/chống mua lặp, sức chứa có quyền sở hữu, dòng nhập80, hàng giữ/đang giao/trả lại, lô lớn và nhiều lô, hao hụt đúng lượng/giá vốn, tương thích tác vụ đang có, bộ ngôn ngữ và Store mua/lưu/nạp lại.

Ba chương trình Node đều qua: `capacity_equipment.mjs`, `work_equipment.mjs`, `warehouse_convenience.mjs`. Render danh mục đủ25 nghề, giá/quyền/bậc hiện có, sức chứa phụ và hoạt động đếm kho.

`python scripts/browser_capacity_progression.py` qua **8 lượt mua thực** trên ứng dụng/server local: quần áo, cơm, trà sữa, trang trại ×390px/1280px. Mỗi lượt trừ3.000 xu từ100.000 còn97.000, mở đúng bậc1, bậc2 được phép mua và quyền còn sau tải lại. Có kiểm tra không tràn ngang và nội dung thẻ không chồng lên nút; ảnh trang trại390px được xem trực tiếp sau khi sửa lỗi chồng đoạn chữ. Báo cáo/ảnh ở `output/playwright/capacity-progression/`.

Đã so khớp tên, mô tả, đơn vị và các sức chứa phụ của toàn bộ250 bậc với gói tiếng Anh: không thiếu. Kiểm tra diff tính đúng CRLF của repository: qua.

## Các lượt hồi quy và rà soát bổ sung

- Kho chung: 15 module, **720 passed, 1 skipped, 1 failed**. Lỗi duy nhất là `tests.test_inventory_cart.Cancel.test_saves_after_a_cancel_load_on_the_rollback_release`, khôi phục vào bản rất cũ `a9777863` thiếu các nghề mới. Chạy riêng trên bản nguồn trước thay đổi `54f146be` cũng lỗi đúng điều kiện “Bản lưu cần đủ các nghề.” Đây không phải cam kết có thể hạ server về bản cũ đó.
- Trang trại:116 kiểm tra cũ qua; sau sửa hao hụt chạy lại71 kiểm tra farm cũ qua.12 kiểm tra sức chứa mới nằm trong lượt tích hợp cuối.
- Trà sữa:13 kiểm tra mới và40 kiểm tra phòng ngừa/chăm quán qua. Lượt rộng426 trước đó còn3 kỳ vọng cũ (phạt80/40 so với mức đã giới hạn6; số bài154 so với162), được tái hiện khi nạp mã boba/experiences trước thay đổi;2 kiểm tra Store khi ấy thiếu cấu hình DB. Không gọi lượt rộng này là toàn bộ xanh.
- Kho đồ đã chế biến:10 kiểm tra mới và47 kiểm tra cũ được chọn cho cafe/quán ăn/cơm qua; cú pháp3 module JS qua.
- Rà soát độc lập tìm ra giới hạn300 mã lô trong biên bản kiểm tra tạp hóa; đã sửa và kiểm tra với kho vượt300 lô. Sau bổ sung giữ chỗ túi bánh/lò và sửa giới hạn UI, vòng rà soát cuối không còn phát hiện cần sửa;48 kiểm tra sức chứa cốt lõi qua ở thời điểm rà soát.

## Giới hạn sản phẩm giữ nguyên

Bản này mở kho đang có và các bộ đệm đồ đã chế biến nêu trong [phạm vi](2026-10-13-capacity-expansion.md). Chưa tạo phòng/chuồng/máy mới hoặc540 gói nội dung nghề. Không đổi số món trong một đơn, mức an toàn, năng suất mẻ, thời hạn dùng, công thức hay tiền bán. Nồi phở100 phần tự cấp đầu ngày chưa được mở rộng.
