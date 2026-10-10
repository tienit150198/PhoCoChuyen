# Kết quả bổ sung tiện ích và ngoại hình

Ngày 2026-10-11. Preview: http://127.0.0.1:18891/.

## Kết quả

- Rà 24 điểm tiện ích: 17 vị trí có cụm hình; sáu hình mới cho công viên, góc hẹn hò, chợ đen, nhà cưới, phòng hát và sân thú cưng. Giữ các chức năng hiện có và điều kiện mở của máy chủ.
- Công viên dẫn đúng `congvien`. Chợ đen giữ action `fair`; đổi nhãn cũ dễ gây hiểu nhầm. Phòng hát và sân thú cưng nối tới tính năng hiện có.
- Hình tĩnh tồn tại cả khi tính năng online chưa mở; vùng bấm/biển tương tác theo trạng thái mở. Không có loop animation mới. Có vật cản tương ứng trên client và server.
- Tám mẫu gương mặt mới; tám phụ kiện: beret, mũ cao bồi, tai nghe, vương miện, tai mèo, vòng hoa, khẩu trang, khăn choàng. Tủ đồ, sở hữu, màu nhuộm và avatar dùng chung bản lưu. Gương mặt hồ sơ/chat và đồ mặc của nhân vật vẫn là hai phần tùy chỉnh riêng như trước.
- Sửa ánh xạ tám kiểu tóc và cách vẽ phụ kiện khi quay lưng. Cùng painter được dùng trong SVG/Canvas cổ điển và overlay nhân vật 2.5D.

## Đã kiểm chứng

| Kiểm tra | Kết quả |
|---|---|
| `npm run typecheck:isometric` và `npm run build:isometric` | Đạt; bundle 1.414.353 byte, gzip 403.469 byte. |
| Bộ `test:isometric` hiện có | Đạt; log ghi 178 bài TAP và các script assertion riêng. Hai file kiểm thử mới đã thêm vào script. |
| Avatar expansion + amenities + guide lifecycle + signs | 43/43 đạt sau bổ sung kiểm tra alpha/kích thước ảnh. |
| Python avatar, wardrobe, wardrobe_plus, collection, home wardrobe, geometry | 62 bài: 61 đạt, 1 bỏ qua theo điều kiện kiểm thử WebSocket có sẵn. |
| PostgreSQL thật trong schema test riêng | Mua từng phụ kiện, nhuộm, lưu preset, đóng/mở pool, đọc lại; đối chiếu hai bộ đọc/render JS từ cùng public state đều đạt. |
| Safari 15 + cú pháp JS đã sửa | 334/334 module trong kiểm tra Safari đạt; các file JS thay đổi parse được. |
| Rà mã độc lập | Không phát hiện lỗi P1/P2 trong phạm vi civic/avatar; không thay thế kiểm tra trực quan. |
| Browser | Cảnh công viên, giàn hoa hẹn hò, sân thú cưng, phòng hát, nhà cưới và chợ đen được quan sát trong cảnh thật. Biển chợ đặt trên sạp. HUD mobile và desktop được chụp. |
| Avatar trên browser | Tám mẫu và tám món mới hiện trong danh mục. Lưu “Gió biển”, nhận “Đang dùng”, reload và mở lại vẫn được chọn. Sau thử trả về “Theo nhân vật”; ví vẫn 460 xu. |

## Ảnh đối chiếu

- `output/civic-avatar-20261011/park-desktop.png` — 1280×800, cảnh công viên và tiện ích liền kề.
- `output/civic-avatar-20261011/park-mobile.png` — màn hẹp, HUD và cảnh.
- `output/civic-avatar-20261011/market-mobile.png` — chợ đen và biển đặt trên sạp.
- `output/civic-avatar-20261011/avatar-saved.png` — tám preset, trạng thái đã lưu.
- `output/wardrobe-expansion-20261011/preview.png` — painter thật cho tám phụ kiện trong classic và bốn hướng 2.5D.

## Giới hạn kiểm chứng

Main hiện chạy Phaser trực tiếp, không có nút đổi renderer classic trong UI. Parity hai renderer được kiểm tra qua mã và bản lưu PostgreSQL, không ghi nhận một lượt chuyển mode qua UI.

Tài khoản khách local chưa mở các hoạt động online hẹn hò/cưới/karaoke/sân thú cưng. Đã kiểm tra hình, dữ liệu route, trạng thái khóa/mở và lifecycle qua test; chưa thử một phiên nhiều người thực ở các khu này. Phụ kiện mới giữ điều kiện mua ở Tiệm Áo Chỉ Mây từ chương 3.

Lượt Python mở rộng ban đầu có kiểm thử socket/chat cũ bị kẹt nên đã dừng; log `python-suite.log` không phải một lượt đạt. Lượt phạm vi tập trung trong `python-focused.log` hoàn thành thành công. Không chạy lại tải 1.000 CCU hay đưa ra cam kết FPS trong đợt bổ sung này.

Bộ mô tả tạo ảnh và file gốc: `2026-10-11-civic-art-prompts.md`; sáu WebP và manifest ở `public/icons/cozy-v4/`, tổng 931.288 byte.
