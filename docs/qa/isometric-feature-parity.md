# Đối chiếu tính năng giao diện hiện tại và 2.5D — 11/10/2026

Đã kiểm kê **50 nghề**, **57 nhóm chức năng**, **57 điểm vào menu/địa điểm nghề** và **66 tiện ích có điều kiện khả dụng** từ mã hiện tại. Danh mục máy đọc được nằm trong `isometric-feature-parity.json`; kiểm tra tự động so khớp với catalogue máy chủ, menu thực tế của từng nghề và registry tiện ích.

Phạm vi kiểm chứng là đường truy cập và cách chuyển tiếp hành động. Các bước giao dịch hoàn chỉnh, tương tác bằng chuột/chạm, trình duyệt thiết bị thật và dịch vụ trực tuyến phải được kiểm riêng; tài liệu này không xác nhận đã chơi hết 50 nghề hoặc mọi giao dịch. Các trang quản trị không thuộc phạm vi giao diện người chơi.

## Kết quả và lỗi đã tái hiện

1. Khi đứng ngoài đảo, `railHTML` ẩn những mục được cho là đã có ở thanh công việc, trong khi CSS 2.5D lại ẩn thanh đó. Kiểm tra trên mã HEAD `5c671878` thất bại ở `grocery: queue`; kiểm tra trình duyệt tablet phát hiện danh sách thao tác bổ sung trước đó chỉ xuất hiện trên điện thoại. Bản sửa giữ các mục đó trong Thêm khi thanh công việc không hiện, trên cả điện thoại/tablet/desktop. Ma trận kiểm tra 50 nghề × ba bố cục, bao gồm Kho trà sữa và Sổ bay của tổ bay.
2. Nút Đổi nghề ở màn hình nghề và mục Đổi nghề trong Thêm đều gửi `home`; liên kết Quay lại hành trình cũng dùng cùng hành động. Lớp 2.5D đổi mọi `home` thành `isoTown`, khiến cả ba mất ngữ nghĩa danh sách nghề/hành trình. Bản sửa đưa `home` về `isoCareers`; nút `isoTown` vẫn ra đảo. Rào chặn trại tạm giữ chạy trước các đường này. Kiểm tra trình duyệt của lượt phát hành phát hiện mục Thêm không mang lớp `career-switch`, nên chỉ sửa riêng lớp đó là chưa đủ.
3. Đường chỉ dẫn có vòng RAF riêng, liên tục dựng lại đường và gọi `requestRender` kể cả khi cảnh Phaser ngủ. Bốn kiểm tra hồi quy thất bại trước sửa. Đường nay cập nhật theo `postupdate` của Phaser, bỏ qua cảnh đang bị che/ẩn/tạm dừng, chỉ dựng lại khi tọa độ đổi và gỡ listener khi đến nơi, hủy, đổi đích hoặc gắn lại cảnh.

## Cách đọc danh mục

- **Màn hình dùng chung**: 2.5D mở đúng màn hình/hộp thoại và bộ xử lý hiện có; không phải một bản luật chơi riêng.
- **Cảnh + màn hình dùng chung**: có điểm vào/cảnh trên đảo hoặc bộ chuyển đổi cảnh; các lệnh nghề/giao dịch vẫn dùng mã hiện tại.
- **Cảnh trực tiếp**: điều khiển bản đồ hoặc cảnh hoạt động chuyên biệt.
- `utility:ID` chỉ mục tiện ích có thật trong registry; Chỉ đường có thể gộp nó vào một địa điểm trên đảo nếu địa điểm đó có cùng action/data. Đây không phải lệnh máy chủ mới.
- Điều kiện trong JSON là điều kiện máy chủ/bộ xử lý dùng chung. Các fixture bật cờ chỉ để kiểm tra nhánh hiển thị, không ghi tiến trình hoặc mở khóa tài khoản.

## Bằng chứng tự động

- `tests/isometric-feature-parity.mjs`: chạy nguyên hàm điều hướng `app.js` trích bằng AST và cấu hình dock/nav của nghề, kiểm tra town/work/classic, tổ bay, đổi nghề, 12 đường đi qua rào chặn trại, 19 màn hình dùng chung, catalogue và tính đầy đủ của danh mục.
- `tests/isometric-guide-lifecycle.mjs`: thực thi guide thật trong môi trường DOM/Phaser tối thiểu; kiểm tra tất cả 66 tiện ích truyền đúng action/data, không đổi state, từ chối mục đã mất điều kiện; danh sách 50 nghề giữ 49 khóa khi chỉ một nghề mở, bỏ mục chưa chơi được; vòng đời đường chỉ dẫn và điểm vào vẫn đúng.
- Các mục JSON ghi `source-route` là đối chiếu đường nguồn; `behavioral-routing` là kiểm tra điều hướng không trình duyệt. `transactions: not-executed` không được nâng thành đã kiểm giao dịch.

Chạy kiểm tra (Node và Python có trong PATH, hoặc đặt biến `PYTHON` trỏ Python của môi trường):

```powershell
node --test tests/isometric-feature-parity.mjs tests/isometric-guide-lifecycle.mjs
```

Để tái hiện hai lỗi menu trên bản nền mà không sửa/hoàn tác cây làm việc:

```powershell
$env:PARITY_SOURCE_REF='5c671878'
node --test --test-name-pattern='town More|legacy Home|jail boundary' tests/isometric-feature-parity.mjs
Remove-Item Env:PARITY_SOURCE_REF
```

Lệnh đối chứng phải có hai thất bại (menu và đổi nghề), còn rào chặn trại vẫn đạt. Khi chủ ý thay đổi catalogue hoặc menu, rà soát trước rồi chạy với `UPDATE_ISOMETRIC_PARITY=1` để cập nhật những hàng máy sinh trong JSON.

## Nhóm chức năng

| Nhóm | Điểm vào 2.5D | Hình thức | Những phần đã đối chiếu |
|---|---|---|---|
| 50 nghề & đổi nơi làm | `isoCareers` | Màn hình dùng chung | danh sách, cửa nghề trên đảo, đổi nghề, giữ tiến trình từng nghề |
| Ca làm & nhiệm vụ | `isoWork` | Cảnh + màn hình dùng chung | nhận việc, chọn việc, bàn thao tác, mở/khép ca, tổng kết |
| Kho & nhà cung cấp | `isoBag` | Màn hình dùng chung | nhập lẻ/gộp, chọn nhà cung cấp, đếm kiện/khay, nhận hàng, khiếu nại, giữ hàng |
| Nhân viên & đời sống nhân viên | `isoMore` | Màn hình dùng chung | tuyển, phân công, lịch ca, vào/nghỉ ca, đào tạo, thưởng, nhắc nhở, chấm dứt, chat, sự cố nhân viên |
| Thu chi nghề | `isoMore` | Màn hình dùng chung | thuế, hóa đơn, gia hạn, tiền thuê, lương, sổ giao dịch, doanh thu tự động/offline |
| Mặt bằng nghề | `isoMore` | Màn hình dùng chung | chuyển mặt bằng, sức chứa, thuê theo ca |
| An ninh & diễn tập | `isoMore` | Màn hình dùng chung | thiết bị an ninh, hồ sơ trộm, báo tin, kết luận, thu hồi, diễn tập |
| Trang trí & thiết bị nơi làm | `isoMore` | Màn hình dùng chung | nâng cấp góc làm, thiết bị nghề, trang bị năng suất, mua/lắp |
| Giá bán & sổ bay | `isoMore` | Màn hình dùng chung | bảng giá, thực đơn, sổ bay phi công/tiếp viên |
| Ứng tuyển & thăng chức | `isoMore` | Màn hình dùng chung | CV, thư ứng tuyển, phỏng vấn, thử việc, xin lại, cửa sau, thăng chức, ca quản lý |
| Đánh giá khách | `isoMore` | Màn hình dùng chung | lọc sao, trả lời, bồi thường, báo đánh giá, xử lý tiếp |
| Người quen & hội thoại | `isoMore` | Màn hình dùng chung | quan hệ, ký ức, chat NPC, chat theo nhiệm vụ |
| Chuyện phố trên điện thoại | `isoMore` | Màn hình dùng chung | bài viết, phản hồi, lời nhắn, xem cũ |
| Sổ tay, nhiệm vụ & ký ức | `isoMore` | Màn hình dùng chung | câu chuyện, nhật ký, ký ức, thư viện tình huống |
| Tình huống nghề & chuyện đời | `isoMore` | Màn hình dùng chung | tình huống trong ca, chuyện đời, chọn hướng xử lý, bước thực hiện, diễn tập |
| Hộ chiếu & trò nhỏ | `isoMore` | Màn hình dùng chung | huy hiệu nghề, hoạt động, quảng trường, ngày hội |
| Kỷ niệm & ảnh | `isoMore` | Màn hình dùng chung | chụp nơi làm, lưu ảnh, tải ảnh |
| Kế hoạch lớp & dẫn đoàn | `isoWork` | Màn hình dùng chung | lịch lớp, thứ tự giảng dạy, tuyến tham quan |
| Hành trình & chương truyện | `isoCareers` | Màn hình dùng chung | giới thiệu, mục tiêu, mở nghề, nghe lại truyện, câu chuyện dài |
| Tên, giới tính & diện mạo | `isoCareers` | Màn hình dùng chung | tên, giới tính, gương mặt chat, tóc, quần áo, giày, phụ kiện, màu |
| Danh hiệu & chứng chỉ | `isoCareers` | Màn hình dùng chung | đeo/cất danh hiệu, học, thi, chứng chỉ nghề |
| Đời thường & nhu cầu | `isoCareers` | Màn hình dùng chung | tinh thần, xả stress, hàng xóm, ăn trưa, ăn thêm, cơm tối, giờ ngủ |
| Chăm con riêng & thú cưng | `utility:household` | Màn hình dùng chung | con riêng, nuôi thú cưng gia đình, chăm sóc |
| Đi chơi gia đình & giao vặt | `isoCareers` | Màn hình dùng chung | ghé salon, làm móng, handmade/DIY, hiệu sách, CLB, đi chơi gia đình, sổ shipper, giao vặt |
| Ví & quỹ nghề | `money` | Màn hình dùng chung | rút tiền lời, góp vốn, tổng tài sản, sổ ví |
| Ngân hàng | `utility:bank` | Cảnh + màn hình dùng chung | tiết kiệm, vay, trả, chuyển khoản, thẻ, quỹ chung |
| Đầu tư | `utility:jrInvest` | Màn hình dùng chung | chứng khoán, vàng, thị trường, biểu đồ |
| Bảo hiểm | `utility:rui` | Màn hình dùng chung | hợp đồng, rủi ro, chi trả |
| Nhà ở, thuê, mua & thế chấp | `utility:house` | Cảnh + màn hình dùng chung | các khu nhà, thuê phòng, mua nhà, chuyển nhà, bán nhà, vay mua nhà |
| Chợ cho thuê giữa người chơi | `utility:house` | Màn hình dùng chung | đăng cho thuê, giá thuê, thuê lại, thu tiền, hủy đăng, phân trang |
| Nội thất, bố trí & sửa nhà | `utility:jrEnterHome` | Cảnh + màn hình dùng chung | 2D/3D, phòng/tầng, kéo/đặt, xoay, sơn, tường/sàn, cất/bán, hoàn tác, sửa/nâng cấp, ảnh nhà |
| Ngoại thất nhà & khu dân cư | `utility:house` | Cảnh + màn hình dùng chung | mẫu nhà, đảo khu dân cư, mặt tiền theo nhà |
| Khách & người ở cùng | `utility:homeGuests` | Màn hình dùng chung | mời khách, quyền vào nhà, đồng cư, cùng trang trí, nhà vợ/chồng |
| Xe & phương tiện | `utility:garage` | Màn hình dùng chung | xe máy, ô tô, du thuyền, máy bay, mua/bán, chọn xe |
| Điện thoại & công nghệ | `utility:gadgets` | Màn hình dùng chung | mua máy, đổi máy, phụ kiện, màu/skin |
| Thú cưng | `utility:pets` | Màn hình dùng chung | nhận nuôi, chăm sóc, tiệm thú cưng, đồ dùng, bé cưng tuần |
| Quán, spa, phim & công đức | `utility:spend` | Cảnh + màn hình dùng chung | cà phê/quán ăn, spa, rạp phim, công đức, phong cách |
| Mua sắm, du lịch & hoạt động lớn | `utility:lux` | Cảnh + màn hình dùng chung | du lịch, sưu tầm, dinh thự, bay riêng, tiệc, khóa học, Mạnh Thường Quân, pháo hoa |
| Đấu giá đồ & danh thắng | `utility:auction` | Màn hình dùng chung | đặt giá, kết quả, sưu tập, danh thắng |
| Quầy riêng & làm thuê | `utility:quay` | Cảnh + màn hình dùng chung | mở quầy, vốn, kho, thuê nhân viên, phân ca, lời mời, quản lý, khách ghé |
| Hội chợ & Chợ đen | `fair` | Cảnh + màn hình dùng chung | cổng, ném vòng, đua chó, ô ăn quan, bầu cua, lô tô, xóc đĩa, phóng dao, vé số cào, buồng ảnh, bảng vàng, đồ ăn, vay/trả |
| Học kế toán, lịch sử & nước ngoài | `utility:historyCourse` | Màn hình dùng chung | khóa kế toán, lịch sử, du học, làm việc nước ngoài |
| Chat phố & riêng | `isoChat` | Màn hình dùng chung | kênh phố, bạn bè, tin riêng, chưa đọc, chặn, báo cáo |
| Bạn bè & hôn nhân | `utility:friends` | Màn hình dùng chung | kết bạn, đính hôn, hôn nhân, quỹ chung |
| Gia đình chung & con chung | `utility:family-children` | Màn hình dùng chung | nhà chung, con chung, chăm bé, bế bé, đưa bé đi chơi |
| Nhóm phố, phố nghề & ghé thăm | `utility:social` | Cảnh + màn hình dùng chung | bảng tin, tiệm người chơi, quyền ghé thăm, đơn khách, phục vụ khách |
| Đi dạo, hẹn hò, cưới, hát & chó sủa | `utility:liveWalk` | Cảnh + màn hình dùng chung | công viên, ghế hẹn hò, lịch cưới, phòng hát, kéo co chó, thiệp mời |
| Xếp hạng | `utility:rank` | Màn hình dùng chung | toàn phố, nghề đang làm, danh hiệu tuần |
| Câu cá, chèo thuyền & bơi | `isoLeisure` | Cảnh trực tiếp | câu cá, bến thuyền, hồ bơi, điều khiển bàn phím/chạm, hiện diện chung |
| Lái xe giao hàng | `isoWork` | Cảnh + màn hình dùng chung | bản đồ, lái xe, điểm giao, chỉ đường, toàn màn hình |
| Đi lại nông trại | `isoWork` | Cảnh + màn hình dùng chung | đi lại, trồng/chăm/thu hoạch, gia cầm, kho, đơn hàng |
| Điều khiển máy bay | `isoWork` | Cảnh + màn hình dùng chung | hướng dẫn, bay, hạ cánh, sổ bay |
| Cài đặt & tài khoản | `settings` | Màn hình dùng chung | âm thanh, ngôn ngữ, chuyển giao diện, bố cục, chủ đề, giảm chuyển động, tài khoản, đăng nhập |
| Bản lưu & riêng tư | `settings` | Màn hình dùng chung | xuất/nhập bản lưu, đặt lại nghề, AI consent |
| Góp ý, hướng dẫn & cập nhật | `isoMore` | Màn hình dùng chung | góp ý kèm ảnh, hỏi nhanh, hướng dẫn nghề, có gì mới |
| Trại tạm giữ | `isoMore` | Màn hình dùng chung | trại, thủ tục, hạn chế đi lại |
| Bản đồ 2.5D & chỉ đường | `isoGuide` | Cảnh trực tiếp | đi bộ, tự chỉ đường, bản đồ đảo, camera, hiện diện người chơi, kho báu |

## 50 nghề và đường thao tác riêng

Mọi nghề có cửa `career:ID` trên danh mục đảo và tiếp tục mở màn hình `job` dùng chung. Cột dưới ghi các điểm thao tác riêng từ `sceneActions`; toàn bộ menu cùng biến thể thanh điện thoại nằm trong JSON. Nhà thuốc, kế toán và chăm sóc khách hàng dùng bàn hồ sơ `desk.js` cho nhiệm vụ mới, vẫn giữ bộ xử lý cũ trong `app.js` cho bản lưu trước bàn hồ sơ.

| Nghề | ID | Điểm thao tác trong cảnh | Nguồn bàn nghề |
|---|---|---|---|
| Tiệm mẹ & bé | `mother_baby` | `queue`, `shelf`, `workbench`, `counter`, `warehouse`, `decor` | `public/js/careers/mother_baby.js` |
| Nhà thuốc nhỏ | `pharmacy` | `queue`, `shelf`, `workbench`, `counter`, `warehouse`, `decor` | `public/js/desk.js` |
| Một ngày làm kế toán | `accounting` | `queue`, `workbench`, `warehouse`, `decor` | `public/js/desk.js` |
| Chăm sóc khách hàng | `customer_care` | `queue`, `workbench`, `warehouse`, `decor` | `public/js/desk.js` |
| Quán ăn nhỏ | `restaurant` | `queue`, `workbench`, `prices`, `inventory` | `public/js/careers/restaurant.js` |
| Cà phê & tiệm bánh | `cafe_bakery` | `queue`, `workbench`, `inventory` | `public/js/careers/cafe_bakery.js` |
| Nông trại ngoại ô | `farm` | `queue`, `workbench`, `inventory` | `public/js/careers/farm.js` |
| Tạp hóa khu phố | `grocery` | `queue`, `workbench`, `inventory` | `public/js/careers/grocery.js` |
| Tiệm chăm sóc thú cưng | `pet_care` | `queue`, `workbench`, `inventory` | `public/js/careers/pet_care.js` |
| Tiệm hoa | `florist` | `queue`, `workbench`, `inventory`, `prices` | `public/js/careers/florist.js` |
| Salon tóc | `salon` | `queue`, `workbench`, `inventory` | `public/js/careers/salon.js` |
| Tiệm sửa chữa đồ dùng | `repair` | `queue`, `workbench`, `inventory` | `public/js/careers/repair.js` |
| Homestay nhỏ | `homestay` | `queue`, `workbench`, `inventory` | `public/js/careers/homestay.js` |
| Một ngày làm giáo viên | `teacher` | `classroom`, `queue`, `workbench` | `public/js/experience-ui.js` |
| Hướng dẫn viên du lịch | `tour_guide` | `queue`, `workbench` | `public/js/experience-ui.js` |
| Tiệm trà sữa | `milk_tea` | `queue`, `workbench` | `public/js/careers/milk_tea.js` |
| Giao hàng | `delivery` | `queue`, `workbench`, `inventory` | `public/js/careers/delivery.js` |
| Kế toán doanh nghiệp | `corp_accounting` | `queue`, `workbench` | `public/js/careers/corp_accounting.js` |
| Thuế & tiền lương | `tax_payroll` | `queue`, `workbench` | `public/js/careers/tax_payroll.js` |
| Kế toán tập đoàn | `group_accounting` | `queue`, `workbench` | `public/js/careers/group_accounting.js` |
| Shop quần áo | `clothing` | `queue`, `workbench`, `inventory`, `car:intro` | `public/js/careers/clothing.js` |
| Shop thú cưng | `pet_shop` | `queue`, `workbench`, `inventory` | `public/js/careers/pet_shop.js` |
| Trà đá vỉa hè | `tra_da` | `queue`, `workbench`, `inventory` | `public/js/careers/tra_da.js` |
| Bán trái cây | `fruit` | `queue`, `workbench`, `inventory` | `public/js/careers/fruit.js` |
| Thu gom rác | `garbage` | `queue`, `workbench`, `inventory` | `public/js/careers/garbage.js` |
| Thông ống cống | `drain` | `queue`, `workbench`, `inventory` | `public/js/careers/drain.js` |
| Nội trợ, giúp việc nhà | `homemaker` | `queue`, `workbench`, `car:notes`, `car:intro` | `public/js/careers/homemaker.js` |
| Bán kem | `ice_cream` | `queue`, `workbench`, `inventory` | `public/js/careers/ice_cream.js` |
| Làm móng | `nail` | `queue`, `workbench`, `inventory` | `public/js/careers/nail.js` |
| Thầy ở chùa | `pagoda` | `queue`, `workbench`, `car:notes`, `car:intro` | `public/js/careers/pagoda.js` |
| Bán phở | `pho` | `queue`, `workbench`, `inventory` | `public/js/careers/pho.js` |
| Bán cơm | `com` | `queue`, `workbench`, `inventory` | `public/js/careers/com.js` |
| Photobooth | `photobooth` | `queue`, `workbench`, `inventory` | `public/js/careers/photobooth.js` |
| Giúp việc theo giờ | `giupviec` | `queue`, `workbench`, `inventory` | `public/js/careers/giupviec.js` |
| Nấu cơm gia đình | `naucom` | `queue`, `workbench` | `public/js/careers/naucom.js` |
| Bảo mẫu | `babysitter` | `queue`, `workbench`, `car:notes`, `car:intro` | `public/js/careers/babysitter.js` |
| Thư viện – Lưu trữ | `library` | `queue`, `workbench`, `inventory` | `public/js/careers/library.js` |
| Phi công | `pilot` | `queue`, `workbench` | `public/js/careers/pilot.js` |
| Tiếp viên hàng không | `flight_attendant` | `queue`, `workbench` | `public/js/careers/flight_attendant.js` |
| Thợ dầu khí | `oil` | `queue`, `workbench` | `public/js/careers/oil.js` |
| Hành chính – Nhân sự | `hr_admin` | `queue`, `workbench` | `public/js/careers/hr_admin.js` |
| Thư ký giám đốc | `secretary` | `queue`, `workbench` | `public/js/careers/secretary.js` |
| IT hỗ trợ | `it_helpdesk` | `queue`, `workbench` | `public/js/careers/it_helpdesk.js` |
| Gác chắn đường sắt | `railway` | `queue`, `workbench` | `public/js/careers/railway.js` |
| Điều dưỡng | `nurse` | `queue`, `workbench` | `public/js/careers/nurse.js` |
| Gác hải đăng | `lighthouse` | `queue`, `workbench` | `public/js/careers/lighthouse.js` |
| Tổng đài cứu hộ | `rescue` | `queue`, `workbench` | `public/js/careers/rescue.js` |
| Cứu hộ hồ bơi | `lifeguard` | `queue`, `workbench` | `public/js/careers/lifeguard.js` |
| Công an phường | `police` | `queue`, `workbench` | `public/js/careers/police.js` |
| Bán album ZPOP | `zpop` | `queue`, `workbench`, `inventory` | `public/js/careers/zpop.js` |

## Phần còn phải kiểm trên môi trường chạy

Chưa chạy xuyên suốt từng đơn nghề, mọi giao dịch thuê/mua/đấu giá, một buổi hội chợ, các phiên chat/ghé thăm nhiều người và thao tác cảm ứng trên toàn bộ thiết bị. Kiểm kê chứng minh điểm vào và việc tái sử dụng bộ xử lý; chưa chứng minh mọi bố cục, hình vẽ hay thanh toán trong các màn hình đó. Các kiểm tra trình duyệt và hiệu năng toàn cảnh do lượt kiểm phát hành tổng hợp bổ sung.
