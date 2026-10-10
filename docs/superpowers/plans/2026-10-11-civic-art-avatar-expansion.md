# Bổ sung cảnh tiện ích và ngoại hình dùng chung

> Thực hiện theo yêu cầu đã chốt về phong cách 2.5D, ưu tiên cảnh tĩnh; dùng kiểm thử trước cho hành vi, đối chiếu trực quan cho hình.

**Mục tiêu:** Các tiện ích có thật có vị trí và hình nhận diện phù hợp trên đảo; avatar và đồ mặc được lưu chung giữa giao diện thường và 2.5D.

**Kiến trúc:** Giữ action và dữ liệu máy chủ hiện tại. `town_layout.json` là nguồn chung cho vị trí, đường và vật cản. Art tĩnh vẫn tồn tại khi tính năng chưa mở; chỉ nút, biển tương tác và vùng bấm phụ thuộc điều kiện mở. Danh mục wardrobe/avatar dùng chung, không tách bản lưu theo mode.

**Công nghệ:** Phaser + TypeScript; ảnh WebP có alpha; JS v4 SVG/Canvas; Python + PostgreSQL.

## Đối chiếu

- Trước: 22 tiện ích dùng biển chung; công viên có chòi/ghế/ao nhưng thiếu điểm nhìn riêng; góc hẹn hò chỉ có ghế; `fair` đã là chợ đen nhưng tên trên đảo còn là cổng hội chợ.
- Thiếu điểm đến vật lý: phòng hát `liveKara`, sân thú cưng `liveBark`.
- Tiện ích thuần menu như tiền, cài đặt, đầu tư không cần tạo nhà giả. Ngân hàng/đại lý vé giữ biển tại vị trí hiện có khi chưa có lô đất an toàn.
- Hai mode đã dùng cùng wardrobe/avatar. Cần sửa 8 ánh xạ tóc và phụ kiện quay lưng trước khi mở rộng danh mục.

## Công việc

- [x] Bổ sung dữ liệu 24 tiện ích, 17 lô hình, 6 cảnh mới; kiểm tra không chắn đường/cửa và parity vật cản máy chủ.
- [x] Vẽ bằng imagegen: công viên, giàn hoa hẹn hò, hai sạp chợ đen, nhà cưới, phòng hát, sân thú cưng. Giữ ảnh gốc; đóng gói WebP tĩnh tối đa 768px, bảo toàn alpha.
- [x] Tạo `client/isometric/amenity-art.ts` quản lý đường dẫn/neo ảnh, ghép cảnh tĩnh, vùng bấm và biển trên facade; test ảnh không biến mất khi khóa tính năng và không sinh hit trùng.
- [x] Thêm 8 preset avatar và 8 phụ kiện có hình riêng trong danh mục chung. Kiểm thử lưu/mua/nhuộm/đọc lại và 4 hướng.
- [x] Build, kiểm thử bộ Phaser, wardrobe/avatar và đường đi; thử browser desktop/mobile, cảnh mới, bộ chọn avatar và lưu/reload. Parity hai bộ renderer kiểm tra bằng dữ liệu lưu thật + Node; không có nút đổi về renderer classic trên main hiện tại để thử đổi mode qua UI.
- [x] Lưu ảnh sau ghép và ghi rõ phần đã xác minh trong `2026-10-11-civic-avatar-verification.md`. Không commit/push/deploy trong đợt này.

## Tiêu chí

Mỗi khu nhận ra ở zoom chơi bình thường, lối vào đi được, không che biển nhà khác, không có nền vuông đục. Cảnh không thêm vòng animation hay request khi đứng yên. Món đồ và avatar vừa lưu tồn tại sau đổi mode/reload, vật phẩm cũ và quyền sở hữu được giữ nguyên.
