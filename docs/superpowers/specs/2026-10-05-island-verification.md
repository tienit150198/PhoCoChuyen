# Phố Có Chuyện — kiểm tra đảo và hoạt động ngoài trời

Ngày kiểm tra: 05/10/2026. Bản chạy cục bộ, chưa triển khai lên máy chủ chính.

## Bản đồ

- Tên: Đảo Hoàng Sa (Pattle Island), quần đảo Hoàng Sa.
- Tham khảo đường bờ tự nhiên trên ảnh vệ tinh AMTI ngày 01/02/2014: https://amti.csis.org/dao-hoang-sa/?lang=vi.
- Đường bờ giản lược thành 28 điểm điều khiển rồi làm mượt; giữ tỷ lệ trước phép chiếu isometric. Đây là bản đồ game có đường phố giả tưởng, không phải dữ liệu khảo sát.
- Biển bao quanh, khu nghề ở giữa; vùng phía đông và phía tây dự trữ bên trong bờ đảo để bổ sung nội dung sau. Chưa mở đường hay nghề trong các vùng dự trữ.
- Danh mục có 44 mục nhưng chỉ 41 nghề chơi được. Client và server cùng dùng 41 nghề thực, có kiểm tra cửa vào và ô đường. Ba mục chưa chơi được không tạo công trình tương tác.

## Hình và thao tác

- Cảnh, nhà và nhân vật dùng minh họa chibi nét mềm; pixel chỉ áp dụng chữ và giao diện theo xác nhận của người dùng.
- Cần tròn điện thoại, bàn phím, đi tới cửa rồi vào tiệm; thả tay, mất focus và mở hộp thoại dừng di chuyển.
- Câu cá, chèo thuyền, bơi mở toàn màn hình. Có vung cần, chờ cắn, giật cần, cá mắc câu, chèo, bơi và lên/xuống bến.
- Hai người chơi thật qua hai phiên đăng nhập thấy nhau ở cùng khu ngoài trời; động tác/vị trí/ngoại hình công khai. Vòng chơi, cá, ví và nhiệm vụ riêng.
- Vòng thuyền/bơi hết hạn hoặc không hợp lệ khi đang ngoài nước chuyển sang quay về; người chơi điều khiển về bến và lên bờ, không gửi tiếp yêu cầu của vòng đã hết hạn.
- Cảnh ngoài trời đứng yên không giữ vòng requestAnimationFrame. Input, thay đổi từ mạng, động tác hoặc camera đang chuyển mới đánh thức vẽ.

## Kết quả xác minh

| Kiểm tra | Kết quả |
|---|---|
| `npm run typecheck:isometric` | Đạt |
| `npm run build:isometric` | Đạt; gói Phaser 1.280.973 byte, gzip 357.969 byte |
| `npm run test:isometric` | Đạt toàn bộ chuỗi, gồm 17 kiểm tra hoạt động ngoài trời và hợp đồng bản đồ |
| `npm run check` | 758/758 tệp JavaScript hợp lệ |
| Python: live town, activity, socket, leisure | 27 kiểm tra đạt, dùng PostgreSQL riêng cho thử nghiệm |
| Rà soát yêu cầu và chất lượng độc lập | Đạt sau sửa lỗi vòng hết hạn ngoài nước |
| Trình duyệt 390×844, xoay ngang, 1440×900 | Canvas đúng tỷ lệ; toàn đảo vừa khung, HUD gọn; trở về nhân vật khôi phục điều khiển |
| Cần tròn / vào tiệm | Đã giữ/thả cần bằng input trình duyệt; đi tới cửa rồi vào tiệm tạp hóa |
| Hai phiên câu cá | Thấy người khác qua WebSocket thật; kết quả cá riêng từng người |
| Cảnh ngoài trời đứng yên 10 giây | 0 yêu cầu RAF, 0 callback, 0 lần vẽ lại thuộc cảnh; input và chuyển động mạng đánh thức lại |

Ảnh chạy thật nằm trong `output/playwright`:

- `hoang-sa-overview-desktop.png`, `hoang-sa-overview-mobile.png`: toàn đảo.
- `hoang-sa-town-desktop.png`: phố ở khoảng nhìn gần.
- `shared-fishing-two-players.png`, `shared-fishing-peer-mobile.png`: hai phiên trên cùng khu câu cá.
- `cozy-grocery-work-mobile.png`: bảng chuẩn bị ca nghề trên điện thoại.
- `leisure-fishing-wardrobe-poses.png`: kiểm tra bốn tư thế câu với trang phục/phụ kiện.

## Giới hạn còn lại

- Chưa đo FPS, nhiệt và bộ nhớ trên điện thoại vật lý; không dùng kiểm tra desktop để cam kết tốc độ mobile.
- Chưa thử thủ công mọi quy trình của 41 nghề trong lượt này; giữ các module nghề hiện hữu.
- Đường phố hiện là bố cục khởi đầu; cảnh quan đất dự trữ và bộ công trình riêng cho từng nghề còn có thể phát triển thêm.
- Nhân vật dùng hai atlas cơ sở; màu trang phục, váy và phụ kiện được giữ, nhưng chưa có hình dáng tóc riêng cho mọi lựa chọn tóc đã lưu.
- Phố hiện giới hạn 30 người/phòng. Chưa có kiểm thử tải để kết luận sức chứa đồng thời khi mở rộng toàn hệ thống.
