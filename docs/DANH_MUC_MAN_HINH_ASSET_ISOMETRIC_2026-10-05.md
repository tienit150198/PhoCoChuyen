# Phố Có Chuyện — danh mục màn hình, nghề và asset đề xuất

Ngày 05/10/2026. Tài liệu tham khảo đi cùng [phương án chuyển đổi](HUONG_CHUYEN_DOI_ISOMETRIC_2026-10-05.md). Các bố trí và số lượng mẫu dưới đây là đề xuất; chưa dựng asset hay thay mã game.

## 1. Quy ước

- **T:** hình tĩnh, không update riêng theo frame.
- **S:** đổi hình/lớp khi trạng thái đổi, giữa các lần đổi vẫn tĩnh.
- **A:** chuyển động cần thiết trong lúc thao tác, kết thúc thì dừng.
- **G:** bảng giao diện đọc/nhập liệu bằng HTML/CSS, đồng bộ chất liệu với game.

Một đối tượng có thể thuộc nhiều mức: cửa tiệm là T, biển mở/đóng là S, khách bước vào là A, phiếu mua hàng là G. Hình tĩnh vẫn có thể nhận bấm và tương tác.

## 2. Màn hình và chức năng chung

| Phần | Biểu hiện trong hướng mới | T/S/A/G | Yêu cầu giữ |
| --- | --- | --- | --- |
| Màn tải | Tranh phố và logo, thanh tiến độ | T, G | Loading/error/retry có thông tin thật |
| Đăng nhập, hồ sơ đầu tiên | Bảng giấy trên cảnh minh họa | T, G | Các cách đăng nhập, tên, ngoại hình và thiết lập |
| Phố và chọn nghề | Công trình, đường, người, biển chỉ dẫn | T, S, A | Nghề khóa/mở, nơi hiện tại, tiến độ và lối vào |
| Hành trình, mục tiêu | Sổ nhiệm vụ và chỉ dẫn tới nơi liên quan | S, G | Điều kiện mở khóa và trạng thái đã làm |
| HUD tiền và giờ | Biểu tượng minh họa, số và nhãn rõ | T, S, G | Phân biệt ví/quỹ và giờ game |
| Khách/công việc | Người đứng chờ và yêu cầu đang chọn | T, S, A, G | Nội dung và bước công việc của từng nghề |
| Kho và nhập hàng | Kệ/thùng hàng trong cảnh, phiếu kiểm | T, S, G | Lô, hạn, giá, tình trạng và kiểm nhận |
| Giá, thu chi, nhân viên | Sổ quản lý | T, S, G | Các thao tác quản lý và lịch sử hiện có |
| Nâng cấp và trang trí | Đổi đồ vật trong cảnh, xem trước | T, S, G; A lúc kéo | Giá, điều kiện và lựa chọn đặt đồ |
| Thoại, tình huống, truyện | Chân dung lớn và lựa chọn | T, S, G | Tên, ký ức, lựa chọn cũ và kết quả có nguồn |
| Nhà, nội thất, đời sống | Các phòng và đồ dùng nhìn chéo | T, S, A, G | Sở hữu, sinh hoạt và dùng chung đồ hiện có |
| Tủ đồ, phương tiện | Chân dung/thử đồ và bãi xe | T, S, G; A khi đi | Ngoại hình và xe đã sở hữu |
| Ngân hàng, đầu tư, bảo hiểm | Nhà trên phố + sổ/bảng giao dịch | T, S, G | Số dư, giao dịch và lịch sử do server xác nhận |
| Quầy của người chơi, ghé nơi làm | Công trình cùng style và trạng thái chủ/khách | T, S, A, G | Phân biệt chủ/nhân viên/khách, đơn ghé và quyền thao tác |
| Chợ/cộng đồng, bạn bè | Bảng tin, cửa tiệm, bảng quan hệ | T, S, G | Danh sách, tìm kiếm, tương tác và báo cáo |
| Chat và phòng live | Bảng chat nổi | G; S/A cho avatar trong cảnh | Nội dung, badge, nối lại và trạng thái phòng |
| Hội chợ và trò nhỏ | Khu hội chợ tĩnh, trò có vùng thao tác | T, S, A, G | Luật/điểm/kết quả và khách đang ở phòng |
| Photobooth, album, ảnh kỷ niệm | Cảnh tạo dáng và bản in | T, S, A lúc chụp, G | Ảnh xuất, sticker, danh tính/ngoại hình người tham gia |
| Hẹn hò, hôn nhân, sự kiện chung | Điểm gặp và bảng tương tác | T, S, A, G | Quyền và đồng bộ người tham gia |
| Cài đặt, hướng dẫn, dữ liệu | Bảng giấy/sổ dễ đọc | T, G | Ngôn ngữ, âm thanh, giảm chuyển động, nhập/xuất và trợ giúp |
| Admin, thống kê | Giao diện công cụ đọc số liệu | G | Rõ chữ, lọc và thao tác quản trị; dùng chung font/token phù hợp |

Admin nằm trong phạm vi kiểm kê để tránh bỏ sót; không cần biến mọi bảng quản trị thành cảnh có nhân vật. Mức đổi hình thức admin là quyết định riêng trước triển khai.

## 3. Kiểm kê 41 nghề và hướng cảnh

Nguồn: bốn nghề gốc, ba nghề trong `extra_content.py` và 34 plugin trong `game/careers/` đang tồn tại. Đếm tĩnh theo mã, không khẳng định mọi nghề đã được kiểm chứng end-to-end hay mở trên website.

Chín nhóm dưới đây giúp tái dùng vật liệu và asset, không yêu cầu các nghề cùng nhóm có cùng bàn thao tác. Riêng nhà thuốc, kế toán, sửa đồ, phi công cần giữ các vùng nghiệp vụ rõ ràng.

### Nhóm ăn uống — 8 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `milk_tea` | Tiệm trà sữa | Quầy, bình trà, ly, topping | Quán/kệ T; lớp ly và tồn S | Pha hoặc kéo món khi bước chơi cần A |
| `restaurant` | Quán mì cay | Bếp, nồi, tô, topping | Bếp T; món/chín/bẩn S | Canh thao tác nấu/trụng khi gameplay cần A |
| `cafe_bakery` | Tiệm bánh & cà phê | Máy pha, lò, tủ bánh | Nội thất T; bánh và trạng thái máy S | Chiết, đánh sữa, vẽ latte, viết bánh A |
| `tra_da` | Trà đá vỉa hè | Xe nước, ghế nhựa, bình/ly | Cụm ghế T; ly/đơn S | Thao tác rót/phục vụ khi có bước A |
| `ice_cream` | Bán kem | Xe/tủ kem, cốc và que | Xe T; phần kem đã chọn S | Thao tác nghề theo cơ chế hiện có A |
| `pho` | Bán phở | Quán, nồi, khay thịt, tô | Nhà/kệ T; tô từng bước S | Chế biến cần thiết A; khói trang trí mặc định tĩnh |
| `com` | Bán cơm | Quầy cơm, khay món, hộp | Quầy T; suất cơm S | Xếp/chia món khi cần thao tác A |
| `naucom` | Nấu cơm gia đình | Bếp nhà, mâm cơm, dụng cụ | Nhà/bếp T; nguyên liệu/món S | Bước nấu cần thao tác hoặc thời gian A |

### Nhóm cửa hàng — 7 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `mother_baby` | Tiệm mẹ & bé | Tủ đồ, quầy, giấy gói, đồ chơi | Kệ T; món và gói quà S | Gói/bàn giao nếu cần thao tác A |
| `pharmacy` | Nhà thuốc nhỏ | Kệ mã hộp, quầy kiểm, phiếu | Kệ T; khay/lô chọn S; phiếu G | Đặt/lấy hộp đang thao tác A |
| `florist` | Tiệm hoa | Xô hoa, bàn cắm, giỏ, thiệp | Trang trí T; bó/cành đã chọn S | Kéo/cắt/cắm hoa theo bàn nghề A |
| `grocery` | Tạp hóa đầu hẻm | Kệ hàng, cân, quầy thu ngân | Hàng trang trí T; giỏ/tồn S | Cân, nhận món và thao tác tiền khi cần A |
| `clothing` | Shop quần áo | Giá treo, mannequin, phòng thử | Giá T; bộ thử và kho S | Đồ đang kéo/chọn A nếu bàn nghề cần |
| `pet_shop` | Shop thú cưng | Bể/khu nuôi, thức ăn, quầy | Bể và nền T; trạng thái chăm sóc S | Tương tác trực tiếp A; cá nền không bắt buộc bơi liên tục |
| `fruit` | Bán trái cây | Xe/sạp, sọt trái cây, cân | Sạp T; phần cân/giỏ S | Cân/chuyển hàng trong thao tác A |

### Nhóm dịch vụ — 4 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `repair` | Tiệm sửa đồ | Bàn sửa, thiết bị điện/điện tử, giá sửa xe đạp, dụng cụ, phiếu | Tiệm T; thiết bị/xe và kết quả S | Đo/sửa khi bàn nghề cần A |
| `pet_care` | Chăm sóc thú cưng | Bồn tắm, bàn chăm sóc, thú | Phòng T; tư thế/tình trạng thú S | Tắm/cắt/chăm sóc A lúc làm |
| `salon` | Salon tóc | Ghế, gương, kéo, khay màu | Salon T; tóc theo bước S | Cắt/chải/pha màu A theo cơ chế nghề |
| `nail` | Làm móng | Bàn tay cận, màu, dụng cụ | Tiệm T; móng/màu S | Vẽ/chăm móng theo cử chỉ A |

### Nhóm văn phòng — 8 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `accounting` | Một ngày làm kế toán | Bàn sổ, chứng từ | Văn phòng T; hồ sơ G/S | Chỉ di chuyển/chọn người A nếu có |
| `corp_accounting` | Kế toán doanh nghiệp | Bàn làm, chứng từ, báo cáo | T; nghiệp vụ G/S | Phản hồi ngắn khi xử lý; không cần NPC luôn gõ máy |
| `tax_payroll` | Thuế & tiền lương | Phiếu lương, bảng/tờ khai | T; biểu mẫu G/S | Chỉ chuyển động có phản hồi cụ thể |
| `group_accounting` | Kế toán tập đoàn | Bàn họp, bảng hợp nhất | T; bảng số G/S | Không cần animation cho từng dòng số |
| `customer_care` | Chăm sóc khách hàng | Bàn hỗ trợ, điện thoại, hồ sơ | T; thoại/phiếu G/S | Phản hồi cuộc gọi/tương tác ngắn |
| `hr_admin` | Hành chính – Nhân sự | Bàn hồ sơ, bảng lịch | T; hồ sơ G/S | Di chuyển nhân vật khi cần |
| `secretary` | Thư ký giám đốc | Bàn tiếp nhận, lịch, phòng họp | T; lịch/yêu cầu G/S | Phản hồi cuộc gặp khi cần |
| `it_helpdesk` | IT hỗ trợ | Bàn máy, thiết bị, ticket | T; màn thiết bị/ticket G/S | Thao tác thiết bị chỉ lúc xử lý |

### Nhóm giáo dục — 1 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `teacher` | Một ngày làm giáo viên | Lớp, bàn, bảng, học liệu | Phòng và học sinh ngồi T; bảng/bài S/G | Học sinh/giáo viên chuyển chỗ hoặc hoạt động đang diễn ra A |

### Nhóm nhà và lưu trú — 4 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `homestay` | Homestay nhỏ | Lễ tân, phòng, giường | Phòng T; sạch/bẩn/đặt phòng S/G | Khách vào/ra và thao tác dọn cần thiết A |
| `homemaker` | Nội trợ, giúp việc nhà | Phòng ở, bếp, đồ sinh hoạt | Nhà T; công việc/đồ dùng S | Dọn và phục vụ khi làm A |
| `giupviec` | Giúp việc theo giờ | Căn hộ, dụng cụ, vết cần dọn | Căn hộ T; bẩn/sạch S | Cử chỉ lau/dọn A |
| `babysitter` | Bảo mẫu | Phòng trẻ, đồ chơi, đồ chăm sóc | Phòng T; nhu cầu/tư thế trẻ S | Tương tác chăm sóc đang thực hiện A |

### Nhóm ngoài trời và điểm đặc biệt — 6 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `farm` | Nông trại rau & gà | Luống, chuồng, cây trồng | Nền T; giai đoạn cây/chuồng S | Gieo/tưới/thu hoạch A; gà nền có thể đứng |
| `delivery` | Giao hàng | Đường, xe, điểm giao, bản đồ | Nhà/đường T; tuyến/đơn S/G | Xe và điều khiển lộ trình A là chức năng cốt lõi |
| `tour_guide` | Hướng dẫn viên du lịch | Điểm đến, đoàn, biển chỉ dẫn | Cảnh T; điểm/lịch S/G | Di chuyển đoàn hoặc tương tác khi cần A |
| `garbage` | Thu gom rác | Hẻm, thùng, xe và điểm gom | Đường T; thùng trước/sau S | Lượt di chuyển/gom đang thực hiện A |
| `drain` | Thông ống cống | Điểm sửa, dụng cụ, sơ đồ | Hẻm T; hiện trạng S/G | Thao tác nghề A theo cơ chế cần giữ |
| `pagoda` | Thầy ở chùa | Sân, chánh điện, cây, bến | Kiến trúc/cây/nước T; việc S/G | Đi lại và thao tác cần thiết A |

### Nhóm hàng không — 2 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `pilot` | Phi công | Sân bay, buồng lái, bảng kiểm | Sân bay T; cockpit/checklist S/G | Điều khiển hoặc tình huống chuyến bay A theo nghề |
| `flight_attendant` | Tiếp viên hàng không | Cabin, ghế, xe phục vụ | Cabin T; yêu cầu hành khách S/G | Đi/phục vụ và thao tác cần thiết A |

### Nhóm chụp ảnh — 1 nghề

| ID | Nghề | Cảnh/asset riêng chủ yếu | Tĩnh và đổi trạng thái | Chuyển động cần giữ |
| --- | --- | --- | --- | --- |
| `photobooth` | Photobooth | Buồng, phông, khung, đạo cụ | Phông/khung T; dáng/biểu cảm S | Đếm giờ/chụp A trong lượt; sửa sticker G/A theo thao tác |

## 4. Cấu trúc bộ asset

| Gói | Nội dung | Cách tái dùng và giữ nhẹ |
| --- | --- | --- |
| Nền phố | Đường, vỉa hè, sân, cỏ, bờ nước | Tile/cụm tĩnh; chia vùng, tránh một texture toàn thế giới |
| Kiến trúc | Mặt tiền, tường, mái, sàn, cửa | Dùng chung vật liệu; tách phần cần che/ẩn/nâng cấp |
| Đồ sinh hoạt Việt Nam | Ghế nhựa, bảng menu, xe máy, cột điện, chậu cây, thùng, ô | Atlas chung; vật không tương tác riêng gộp theo cụm |
| Nội thất nhóm nghề | Kệ, quầy, bàn, bồn, máy, phòng | Tái dùng nền và vật liệu; giữ dụng cụ đặc trưng |
| Vật phẩm thao tác | Ly, món, bó hoa, hộp, thiết bị | Kích thước rõ ở bàn cận; frame theo trạng thái |
| Nhân vật nhỏ trong cảnh | Người chơi, khách, người quen, người nền | Tư thế đứng tĩnh; bộ đi chung có kiểm tùy biến ngoại hình |
| Trang phục/phụ kiện | Tóc, quần áo, mũ, kính, balo, đồ cầm tay | Ghép lớp theo pose/hướng; cache tổ hợp đang dùng với giới hạn bộ nhớ |
| Phương tiện | Xe hai bánh, ô tô, thuyền/máy bay đã có trong hệ sở hữu | Xe đỗ tĩnh; tải gói phương tiện hiện dùng; chuyển động chỉ lúc di chuyển |
| Chân dung lớn | Người nói và các biểu cảm | Ảnh tĩnh; tải khi cần thoại; không dùng sprite nhỏ phóng to mờ |
| Thú cưng | Mèo/chó và tư thế tương tác | Đứng/ngồi tĩnh mặc định; đổi tư thế hoặc chạy lúc cần |
| HUD | Sổ, túi, nhà, quà, bản đồ, bảng thoại | Minh họa đồng bộ; chữ/số ở DOM; hình không thay thế nhãn |
| Nâng cấp | Mặt tiền, kệ, thiết bị/đồ mới | Đổi nhóm sprite theo ID nâng cấp được server xác nhận |
| Hội chợ/sự kiện | Cổng, bạt, đèn, sân khấu, gian trò | Gói riêng; phần tĩnh cache, chỉ trò đang chơi cập nhật |
| Âm thanh | Âm tương tác và nhạc theo khu | Dùng lại nguồn đang có; tải khi cần, tôn trọng cài đặt |

Gợi ý gói mẫu để kiểm chứng: một đoạn phố; 3–5 mặt tiền; một nội thất đầy đủ; khoảng 10–15 cụm đồ sinh hoạt; 6–8 thiết kế người mẫu, trong đó chỉ người cần đi có frame đi; một chân dung nhân vật với 3–4 biểu cảm tĩnh; HUD cốt lõi và một biến thể nâng cấp. Đây là quy mô thử, không phải tổng số asset của cả game.

Không cần làm ngay đủ hành động đi/chạy/ngồi/tưới/câu cá cho mọi nhân vật chỉ vì chúng xuất hiện trên bảng tham chiếu. Mỗi frame phải phục vụ hành động thật. Nhân vật đang có nhiều lựa chọn trang phục cần kiểm phương án ghép lớp hoặc cache theo ngoại hình; không mặc định chỉ thay được một sprite đóng gói sẵn.

## 5. Chuẩn bàn giao một asset

Mỗi asset cần ID ổn định, gói sử dụng, trạng thái T/S/A, kích thước, điểm neo ở chân/đáy, vùng bấm và vùng cản nếu có. Asset che người cần thông tin lớp và thứ tự vẽ; hình có thể ẩn cần mô tả điều kiện.

| Tiêu chí | Kiểm khi nhận |
| --- | --- |
| Hình | Cùng góc nhìn, tỷ lệ, ánh sáng và nét với mẫu đã chọn |
| Nền | Alpha sạch nếu cần; không viền trắng hay cắt bóng |
| Kích thước | Nhìn ở điện thoại vẫn nhận ra; không xuất quá lớn cho vùng hiển thị |
| Lớp | Tách quầy/tường/mái và đồ nâng cấp cần thiết; không tách từng chai trang trí |
| Trạng thái | Có frame mở/đóng, đầy/vơi hoặc trước/sau đúng yêu cầu gameplay |
| Chữ | Biển và UI cần dịch dùng text layer/code; chữ trang trí cố định được ghi rõ |
| Đóng gói | Atlas theo gói sử dụng; metadata thống nhất; padding tránh viền khi scale |
| Nguồn | File nguồn/chỉnh sửa, prompt nếu dùng AI, nguồn/quyền sử dụng |
| Hiệu năng | Dung lượng nén, kích thước giải nén, cache và điều kiện giải phóng |

Bộ ảnh tham chiếu chưa phải asset hoàn chỉnh. Nếu dùng AI sau này, vẫn phải kiểm và tách lớp, chỉnh góc/tỷ lệ, xử lý chữ, bảo toàn alpha và nghiệm thu trong cảnh thật.

## 6. Các ca nghiệm thu cần có trước khi nhân rộng

1. Mở phố trên điện thoại; cửa vào và người cần chọn không bị HUD che; nhãn đọc được.
2. Kéo bản đồ không đồng thời chọn công trình; zoom không làm nút/chữ phóng theo.
3. Đi sau cây/quầy bị che đúng; đi trước xuất hiện đúng; chạm được lối vào.
4. Vào tiệm, làm một đơn thật từ đầu tới kết quả; tiền, kho, tiến trình đúng server.
5. Khi đủ điều kiện nâng cấp, hình đổi sau xác nhận; tải lại vẫn thấy đúng.
6. Giảm chuyển động hoặc cấu hình nhẹ: cây/đèn/người nền đứng yên nhưng chức năng vẫn đủ.
7. Mở sổ kế toán/phiếu kho, dùng bàn phím và cuộn; nền không tiếp tục animation vô ích.
8. Ra/vào cảnh lặp lại, ẩn/hiện tab và mất/nối mạng; không nhân đôi timer, listener hoặc lệnh.
9. Người chơi thật trong room vẫn được đồng bộ; giảm NPC trang trí không làm mất người/phòng.
10. Chụp ảnh/photobooth xuất đúng khung, tên, ngoại hình, sticker và người tham gia.
11. Đối chiếu bản lưu trước/sau; ID nghề, công việc, quan hệ, đồ sở hữu không bị đổi do renderer.
12. Đo tải đầu, frame khi hoạt động, CPU khi nghỉ, bộ nhớ/texture sau chuyển cảnh; so cùng thiết bị với bản hiện tại.
13. Mũ, tóc, áo và đồ cầm tay không lệch khi nhân vật đổi hướng hoặc lên/xuống xe; giữ ID và màu người chơi đã chọn.
14. Xe đỗ không chạy update riêng; khi đi thì người ngồi, bánh và điểm neo khớp hướng; thử che khuất tại nhà/cây/góc đường.
15. Đổi xe hoặc qua sân bay/bến không giữ toàn bộ atlas phương tiện trong bộ nhớ; kiểm lại khi trở về phố.
16. Bảng bước nhiệm vụ đổi đúng kết quả server; reconnect không tự thêm phần thưởng hoặc phát bù mọi animation.

Chưa chạy các ca nghiệm thu trên một frontend mới vì đợt này chỉ lập tài liệu. Tiêu chí và danh mục sẽ được cập nhật từ mẫu thật nếu người dùng quyết định triển khai.

## 7. Bổ sung bộ nhân vật và phương tiện theo ảnh mới

Tham chiếu: [nhân vật, hoạt động và xe](isometric-reference/nhan-vat-phuong-tien-hoat-dong-tham-chieu.jpg), [chuỗi nhiệm vụ và nghề di chuyển](isometric-reference/nhiem-vu-di-chuyen-nghe-tham-chieu.jpg). Bảng nhân vật được gửi lại đã có cùng SHA256 với file cũ, nên dùng lại [bảng nhân vật](isometric-reference/nhan-vat-tham-chieu.jpg).

### Nhân vật tùy biến

| Thành phần | Asset cần có khi tính năng sử dụng | Mặc định nhẹ |
| --- | --- | --- |
| Thân/dáng | Dáng đứng, dáng đi, dáng ngồi xe; neo tay/chân/đầu | Đứng và ngồi là frame tĩnh; đi chỉ đổi frame khi di chuyển |
| Tóc và mũ | Hình theo hướng/pose, lớp trước và sau nếu cần | Dùng ID hiện có; không render mọi kiểu một lúc |
| Áo/quần/giày | Cùng tỷ lệ và pose với thân; vùng đổi màu nếu có | Ghép/cache ngoại hình đang dùng, giải phóng theo ngân sách |
| Mặt | Mắt, miệng, biểu cảm và chân dung lớn | Đổi biểu cảm theo sự kiện; không bắt buộc lip-sync/chớp mắt |
| Vật cầm tay | Hộp hàng, điện thoại, bát, dụng cụ | Gắn theo điểm neo; chỉ xuất hiện khi có trạng thái tương ứng |
| Tư thế phụ | Ăn, làm việc, vẫy, tưới, câu cá, vui mừng | Chỉ làm khi gameplay dùng; có thể là một tư thế tĩnh |

Không tạo sẵn mọi tổ hợp áo × tóc × mũ × màu × xe × hướng × pose: số ảnh và cache có thể tăng rất nhanh. Đề xuất ghép lớp theo thứ tự có quy chuẩn, rồi cache có giới hạn cho người đang hiện trong cảnh. Cache phải tính cả pose, hướng và phiên bản asset; đổi ngoại hình cần xóa đúng phần cũ.

Chibi trong ảnh có dáng và nét riêng; việc đổi renderer phải giữ toàn bộ lựa chọn ngoại hình được hỗ trợ, không chỉ hai mẫu nam/nữ mặc định. NPC có cá tính cần bộ dáng/biểu cảm phân biệt nhưng không nhất thiết có đủ animation của người chơi.

### Phương tiện và cách chuyển trạng thái

| Loại | Vai trò đề xuất | Bộ hình tối thiểu nếu được sử dụng |
| --- | --- | --- |
| Xe đạp/xe điện/xe số/tay ga | Phương tiện dạo phố hoặc nghề giao hàng tùy tính năng hiện có | Xe đỗ, xe theo hướng di chuyển, dáng người ngồi và điểm ghép |
| Ô tô đang sở hữu | Hiển thị tại nhà/showroom và di chuyển nếu tính năng hỗ trợ | Dáng đỗ, hướng đi cần thiết, vùng nhận màu; giữ ID và lựa chọn xe |
| Thuyền/du thuyền | Bến và cảnh chuyến đi riêng | Bến tĩnh, thuyền tĩnh, hình chuyển động khi lượt đi cần |
| Máy bay/trực thăng sở hữu | Sân bay riêng và lượt đi riêng | Dáng đỗ, hình lượt đi; không suy ra cùng cơ chế với nghề phi công |
| Máy bay nghề | Sân bay, cabin/buồng lái và nhiệm vụ hàng không | Bộ theo bước nghề; tải riêng khi vào nhóm hàng không |
| Taxi/xe buýt/xe tải/xích lô/ba gác/tàu hỏa | Ý tưởng bổ sung hoặc vật trang trí | Ưu tiên một sprite tĩnh nếu chỉ trang trí; nghề/lộ trình riêng cần spec bổ sung |

Chuỗi trạng thái đề xuất cho xe được điều khiển: đi bộ tới điểm đỗ → chuyển sang dáng ngồi xe → chạy theo đường hợp lệ → đỗ → trở lại dáng đi bộ. Lên/xuống xe có thể đổi hai tư thế hoặc một chuyển động ngắn; không cần nhiều frame điện ảnh. Góc xe và góc nhân vật phải khớp, không lấy hình xe nhìn ngang để đặt vào đường nhìn chéo.

Xe lớn phải có đường/vùng dừng phù hợp; không dùng cùng hitbox với người đi bộ để chạy qua mọi hẻm. Các loại xe trong bảng là phạm vi mỹ thuật; khả năng chạy và vùng đi phải đối chiếu tính năng đã có trước khi chốt.

## 8. Bổ sung HUD nhiệm vụ và ranh giới tính năng

| Chuỗi trong ảnh | Bảng bước đề xuất | Phạm vi |
| --- | --- | --- |
| Giao đồ ăn | Nhận đơn → lấy món → giao → kết quả | Ánh xạ nghề giao hàng hiện có, không mặc định đổi luật |
| Đi mua sắm | Điểm mua → chọn món → xác nhận mua → về | Dùng màn mua hiện có; giỏ hàng/lộ trình nhiều điểm là mở rộng nếu muốn |
| Phi công | Ra sân bay → chuẩn bị → các bước chuyến bay → kết quả | Nhóm nghề đã có, hiển thị theo bước server thực tế |
| Taxi | Đón khách → tuyến → trả khách | Ý tưởng nghề mới, chưa có trong 41 plugin khảo sát |
| Xe buýt | Đón → đi tuyến → trả khách | Ý tưởng nghề mới, chưa có trong danh mục khảo sát |
| Tài xế xe tải | Lấy hàng → vận chuyển → bàn giao | Ý tưởng nghề mới; không đồng nhất với việc sở hữu ô tô |
| Sửa xe | Nhận xe → kiểm tra/sửa → bàn giao | `repair` đã có sửa xe đạp cùng đồ điện/điện tử; xe máy/ô tô là mở rộng riêng |

Bảng nhiệm vụ dùng chung chỉ trình bày dữ liệu: mã nhiệm vụ, nhãn bước, trạng thái, điểm đến và hành động hiện thời. Tiền, điều kiện, giới hạn giờ và hoàn tất do server quyết định. Đơn vị thưởng hiển thị theo game hiện có; các số tiền đồng trong ảnh không thay đổi luật kinh tế của bản lưu.

Phạm vi chuyển đổi vẫn giữ ma trận 41 nghề ở mục 3. Những ý tưởng ngoài danh mục được ghi riêng để tham khảo, chưa là cam kết thêm gameplay hoặc tăng số nghề.
