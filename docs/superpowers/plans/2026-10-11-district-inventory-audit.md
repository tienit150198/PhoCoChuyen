# Kiểm kê tiện ích và khu nhà trên đảo

Phạm vi: bổ sung đường đi, điểm đến và thẻ mở của tính năng đã triển khai. Không thay đổi giá, lệnh giao dịch, luật trò chơi, quyền vào nhà hoặc dữ liệu cư dân. Dữ liệu bản đồ ở `game/town_layout.json`; danh mục tiện ích ở `public/js/isometric/town-utilities.js`.

## Đối chiếu tuyến thực tế

| Chức năng | Tuyến đang có | Điều kiện hiển thị / hành vi |
| --- | --- | --- |
| Chợ đen | `fair`, `tab: home` | `state.fair.show`; lịch mở cửa, bảo kê, trại tạm giữ vẫn do `fair.js` và máy chủ kiểm tra |
| Hội chợ · ném vòng | `fair`, `tab: ring` | Cùng cổng/luật Chợ đen; tên và gợi ý ghi rõ mối liên hệ, có sân và lối vào riêng |
| Đua chó | `fair`, `tab: dg` | `fair.show && fair.dog`; `fair_dg` vẫn là lệnh máy chủ duy nhất |
| Các trò hội chợ còn lại | `fair`, `tab: oaq/bc/lt/xd/dt/xs/pb` | Ô ăn quan, bầu cua, lô tô, xóc đĩa, phóng dao, vé cào, buồng ảnh; `dt/xs/pb` cần đúng dữ liệu `knife/scratch/photo` |
| Bảng vàng / ăn uống / vay trả ở chợ | `fair`, `tab: board/food/loan` | Cùng điều kiện hiển thị Chợ đen; chỉ mở màn hình, không tự giao dịch |
| Kéo co chó sủa | `liveBark` | Hành trình, live welcome và `flags.bark`; giữ sân thú cưng riêng, không nhầm với đua chó |
| Nhà ở | `house` | Hành trình; phòng thuê/ký túc xá cùng nhóm `rent`, rồi `apartment`, `townhouse`, `villa` lấy đúng `housing.GROUPS/HOMES` |
| Trang trí / sơn / sửa nhà | `jrEnterHome` | Hành trình và `journey.deco`; mở nhà đang ở trong `reno.js`, giữ quyền sửa hiện có |
| Khách / người ở cùng | `homeGuests` | Hành trình; API hiện có kiểm tra mã mời và quyền |
| Con riêng / thú cưng theo ngày sống | `stView`, `view: household` | Hành trình và `journey.household`; khóa ngày sống 10 vẫn hiển thị trong màn hình gốc |
| Gia đình / con chung | `marriage`, `tab: family`, tùy chọn `section: children` | Hành trình; điều kiện kết hôn và sinh/nhận/chăm con vẫn do màn hình và API hiện có |
| Xe máy / ô tô / du thuyền / máy bay | `garage`, `tab: bike/car/boat/plane` | Hành trình và `journey.garage`; xe máy và ô tô thêm biển chỉ dẫn riêng cạnh gara |
| Thú cưng mới | `pets`, mặc định / `tab: adopt/shop/board` | Hành trình và `journey.pets`; nhận nuôi, mua, chăm, trang phục, bảng tuần giữ quy tắc máy chủ |
| Quán / spa / rạp / công đức / phong cách | `spendQuan/spendSpa/spendRap/spendChua/spendStyle` | Hành trình và `journey.spend` |
| Du lịch / sưu tầm / dinh thự / bay / tiệc / khóa học / quyên góp / pháo hoa | `luxTrip/luxSuu/luxNha/luxBay/luxTiec/luxHoc/luxMtq/luxFw` | Hành trình và `journey.lux`; pháo hoa vẫn mở mục hiện có của `luxMtq` |
| Đấu giá / danh thắng | `auction/auctionLands` | Hành trình và `content.journey.auction` |
| Quầy riêng / thiết bị / nước ngoài / chứng chỉ | `quay/gadgets/abroad/jrCerts` | Giữ các cổng dữ liệu máy chủ hiện có |
| Tiền / ngân hàng / bảo hiểm / đầu tư | `money/bank/rui/jrInvest` | Giữ cổng hiện có; không tạo thêm công trình giả cho các mục quản lý |
| Bạn bè / nhóm phố / phố nghề / bảng hạng | `friends/nhom/social/rank` | Giữ tuyến đã có; tiệm người chơi lấy directory thật |
| Đi dạo / hẹn hò / cưới / hát | `liveWalk/liveDate/liveWed/liveKara` | Live welcome và đúng flag từng dịch vụ |
| Câu cá / chèo thuyền / bơi / nghề nghiệp | Các commons và 50 cửa nghề hiện có | Giữ hoạt động, khóa nghề và cảnh gốc |

Không mở phòng thuê bằng `house({kind: 'ky_tuc_xa'})`: `openHouse(kind)` chạy `startBuy`, vốn dành cho nhà mua. Cổng khu dân cư dùng `housingGroup` và mở directory thật do lớp tích hợp xử lý; fallback an toàn là `house` không truyền `kind`.

`jrView` chỉ vẽ lại sheet đang mở nên lối vào chăm con dùng `stView({view:'household'})`, là tuyến có `openSheet` thật.

## Dữ liệu khu dân cư

| ID | Nhóm gốc | Điểm đến | Tâm tranh |
| --- | --- | --- | --- |
| `homes-rent` | `rent` | `(-35, 33)` | `(-38, 29.5)` |
| `homes-apartment` | `apartment` | `(12, -1)` | `(10, -4)` |
| `homes-townhouse` | `townhouse` | `(-29, 49)` | `(-32, 45.5)` |
| `homes-villa` | `villa` | `(46, 0)` | `(46, -3)` |
| `fairgrounds` (tiện ích) | `fair`, ném vòng | `(-16, 9)` | `(-19, 5.8)` |
| `dograce` | `fair`, đua chó | `(-34, 18)` | `(-36, 14.5)` |

`homeKinds` là danh mục công khai lấy đúng nhóm nhà gốc; không chứa chủ nhà, cư dân hoặc số nhà trống giả. Bounds đi bộ mở rộng thành `(-42,-7) → (80,58)` trong đường bờ đảo hiện có. Bốn đường mới là đường vòng nối vào mạng đường cũ, không phải lưới vuông hoặc ngõ cụt giữa cỏ.

## Tranh và kiểm thử

Sáu ảnh được tạo bằng built-in `image_gen`, sau khi xem `cozy-v4/civic-market.webp` và `cozy-v4/civic-pets.webp`. Tệp giao là `public/icons/cozy-v5/*.webp`, cạnh dài tối đa 768px, alpha được giữ khi nén bằng Sharp. Manifest lưu tên, mô tả prompt và kích thước. Tổng 1.09 MiB. Tranh đã xem trực tiếp: quầy ném vòng, sân đua hình oval, dãy trọ/ký túc, khối căn hộ, ba nhà phố lệch mái, biệt thự vườn đều có hình dáng riêng.

Đã chạy:

- `node tests/town-district-inventory.mjs`: 6/6; ghi nhận thất bại trước triển khai cho nhóm nhà, tuyến/thẻ mở, điều kiện khả dụng; kiểm tra icon, alpha, ngân sách ảnh.
- `node tests/isometric-amenities.mjs`: 4/4; 23 nền tranh không đè cửa, nền cũ, cây hoặc bề rộng đường.
- `node tests/town-map-contract.mjs`: client/server đồng nhất tại mọi điểm lấy mẫu và các mức mở rộng danh mục nghề.
- `node tests/island-neighbourhoods.mjs`: 103 điểm đến liên thông, 14 khu, đường đi chậm nhất 80ms ở lần kiểm tra.
- `node tests/organic-streets.mjs`: 58 nhánh vào cửa an toàn.
- `node tests/street-connectivity.mjs`: 36 đường nối liền, không có ngõ cụt không giải thích được.
- `node --check public/js/isometric/town-utilities.js`: đạt.
- `python -m unittest tests.test_live_town.Geometry`: 5/5; bỏ giả định cứng 17 tranh, kiểm tra sáu ID mới và nền va chạm thật.
- `node tests/isometric-shell.mjs`: đạt; `node tests/isometric-guide-lifecycle.mjs`: 21/21 sau tích hợp actionData.

Kiểm tra độc lập lớp 3D sau tích hợp đã phát hiện và sửa trong `client/district3d/model.js`: chỗ ở hiện tại tuân theo `home.place` (kể cả nhà ở chung, hợp đồng thuê của người chơi và dinh thự), nhà sở hữu khác không bị gắn nhãn đang ở, nhãn cho thuê lấy từ dữ liệu thật. Directory giữ tối đa 100 tin mỗi trang cộng nhà hiện tại/sở hữu và danh mục; chỉ renderer giới hạn tám tòa nhà. Sáu regression mới đã thất bại trước sửa; `node tests/district3d.mjs` đạt 9/9 sau sửa. Các sửa hướng nhà, tiêu điểm, vòng vẽ và lifecycle của renderer do parent sở hữu.

Lớp tích hợp cần nạp sáu texture mới, truyền `actionData` vào cổng `townServiceAvailable`, định danh item bằng `id` và giữ `actionData` khi mở từ guide/HUD. Kiểm tra trình duyệt của các thẻ và directory do parent thực hiện; phần dữ liệu này không tự khẳng định các luồng trình duyệt đã được kiểm tra.
