# Hình tiện ích — nguồn và bộ mô tả

Ngày: 2026-10-11. Tạo bằng **built-in imagegen**, xuất nền trong suốt. Đây là bản ghi mô tả sản xuất đã chuẩn hóa; tên PNG gốc được giữ trong manifest để truy vết từng kết quả.

## Quy chuẩn chung

Một cụm cảnh game 2.5D isometric nhìn chéo xuống khoảng 30 độ; khu phố Việt Nam, nét nâu mềm, màu kem, ngói đất nung, xanh lá dịu. Chi tiết đọc được khi thu nhỏ khoảng 380–500px. Ánh sáng từ trên trái, bóng tiếp xúc nhẹ. Vật thể tách nền trong suốt thật, chừa khoảng mép để không cắt bóng. Không nhân vật, không UI, không chữ vẽ sẵn. Hình minh họa cozy, không ảnh chụp, không pixel art, không khối low-poly. Ưu tiên hình tĩnh.

## Sáu cảnh

| File | Nội dung riêng |
|---|---|
| `public/icons/cozy-v4/civic-park.webp` | Chòi nghỉ, đường dạo cong, hai ghế, bụi hoa, cây phía sau, đèn xanh; mép vườn tự nhiên không thành ô vuông. |
| `public/icons/cozy-v4/civic-date.webp` | Giàn hoa giấy, ghế đôi, bàn hai tách trà, đèn lồng và chậu hoa; phía trước thoáng, hàng rào thấp. |
| `public/icons/cozy-v4/civic-market.webp` | Hai sạp bạt chàm và tím mận, radio, đồng hồ, đồ gốm, vải, thùng gỗ; đèn lồng và bảng trống treo cao. |
| `public/icons/cozy-v4/civic-wedding.webp` | Nhà nhỏ cột kem mái ngói, rèm lụa đào, cổng hoa, biểu tượng lễ cưới, bàn đón khách và cây cảnh. |
| `public/icons/cozy-v4/civic-karaoke.webp` | Phòng hát một tầng xanh bạc hà và kem, biểu tượng micro, loa, nốt nhạc, mái hiên đỏ rượu; bảng trống trên mặt tiền. |
| `public/icons/cozy-v4/civic-pets.webp` | Sân cỏ có lối vào mở, hàng rào tre, vòng vận động, cầu dốc, đồ chơi dây, nhà thú nhỏ, bát nước và ghế; không vẽ sẵn thú. |

Chợ và sân thú cưng được chạy thêm lượt chỉnh nền: giữ nguyên hình và bố cục, loại bỏ sương/gradient ngoài vật thể, giữ alpha trong suốt. Kiểm tra alpha trên file thực thay vì chỉ dựa vào màu xem trước.

## Đóng gói

`scripts/package_civic_assets.mjs` nhận thư mục chứa PNG gốc, dùng Sharp thu nhỏ tối đa 768px và nén WebP quality 85 / alpha quality 100. Không thay đổi nội dung hình. Sáu file tổng cộng **931.288 byte**. Manifest: `public/icons/cozy-v4/manifest.json`.

PNG gốc của phiên này: `C:/Users/ADMIN/.codex/generated_images/01a10ac1-359e-7992-8d83-466339b567f2/`. Tên từng PNG nằm trong manifest. Cảnh tải cùng nhóm texture trang trí, không có vòng animation mới.
