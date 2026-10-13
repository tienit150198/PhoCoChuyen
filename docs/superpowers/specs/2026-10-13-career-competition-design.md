# Thi đua, ghi nhận và trách nhiệm quản lý cho mọi nghề

Ngày 13/10/2026. **Bản thiết kế đề xuất, chưa triển khai tính năng này và chưa deploy.** Tiếp nối yêu cầu tất cả nghề có cạnh tranh và cấp trên ghi nhận như công an, bao gồm thu gom rác.

## Hiện trạng đã xác minh

- `game/promotion.py`: nghề thông thường đã có bảy bậc thăng tiến, xét ngày làm tốt và ca quản lý từ bậc3; đây chưa phải hệ thống thi đua cá nhân đầy đủ.
- `game/career_mastery.py`: ba mốc tay nghề tích lũy, thi tình huống, thưởng ngày đạt chuẩn6/12/20. Giữ nguyên dữ liệu và quyền đã đạt.
- `game/org_content.py`: chỉ police nối vào CAREER_ORG; các tổ chức khác mới là STUBS. Công an có cấp bậc riêng với chức vụ, đánh giá mỗi10 ngày làm.
- `game/cand_ops.py`: chỉ huy người chơi có thể khen người chơi khác, có kiểm tra quyền và giới hạn ngày; đây là tương tác người thật, không chỉ NPC.
- Thu gom rác đang dùng thang danh hiệu thông thường và được engine phân loại `own`; không tự chuyển nghề này sang hợp đồng hưởng lương chỉ vì thêm tổ trưởng thi đua.

## Hướng chọn và phần cần chốt

Đề xuất khung thi đua chung nhưng tiêu chí, người xét và việc quản lý riêng cho từng nghề. Mỗi người có ba đồng nghiệp/đối thủ NPC để chơi được ngay. Nếu chọn người chơi thật, thêm tổ nghề tự nguyện và bảng xếp hạng cùng nghề/cùng bậc, có trưởng tổ ghi nhận thành tích đã xác minh. Câu hỏi NPC/người thật/kết hợp đang chờ người dùng chọn; bản này mô tả rõ cả hai lớp, chưa coi lựa chọn đó đã được duyệt.

Hai cách còn lại: chỉ thêm bảng xếp hạng tiền sẽ thiếu gameplay và thiên về người giàu; sao nguyên tổ chức công an sang54 nghề sẽ gán sai quyền, chức vụ và cơ chế nghề. Khung dùng chung với nội dung riêng tránh hai vấn đề đó.

## Vòng chơi và cách chấm

Nhận mục tiêu ca → tự làm việc nghề → xem bằng chứng điểm số → kết thúc ca được nhận xét → kết thúc kỳ nhận danh hiệu/thưởng → đủ hồ sơ để dự đợt nâng trách nhiệm.

Mỗi kỳ gồm10 ca làm có kết quả được máy chủ nghiệm thu. Chỉ mở/khép ca trống không tiến kỳ; ngày bỏ dở không được tính tốt. Ca hợp lệ phải hoàn thành ít nhất một công việc chính do game sinh và có kết quả chấm; mỗi nghề xác định loại việc chính, không lấy hoạt động phụ, mua bán tài sản hoặc thắp hương làm điểm. Các ca kém vẫn nằm trong kỳ để người chơi không bỏ dữ liệu xấu. Kỳ bắt đầu từ thời điểm bật tính năng, không suy diễn điểm quá khứ.

Điểm ca0–100: chất lượng50, quy trình/an toàn25, xử lý tình huống15, phối hợp10. Chuẩn hóa trên các cơ hội đánh giá thực sự có trong ca; tiêu chí không có cơ hội được loại khỏi mẫu số và tái chuẩn hóa. Không có bằng chứng tổng thể thì ca không vào thi đua. Tỷ lệ thành công dùng tất cả nhiệm vụ đã nhận trong ca, kể cả hủy/bỏ, không chọn riêng nhiệm vụ đẹp. Nhiệm vụ nhiều bước lấy kết quả cuối, không cộng lại từng lần nhấn. Các module nghề cần adapter riêng; chỉ có cấu hình tên mà thiếu dữ liệu chấm chưa được công bố là hỗ trợ.

Không dùng tổng xu, số lần nhấn hay thời gian bấm nhanh để quyết định thứ hạng. Các nghề an toàn phải làm đúng quy trình; hoàn thành nhanh nhưng sai không thắng. NPC được tạo điểm cho từng ca từ đầu kỳ theo nghề và bậc, không tăng điểm để bám người chơi sau mỗi lượt. Bảng cá nhân có người chơi và ba NPC; điểm kỳ là trung bình10 ca, bằng điểm thì đồng hạng. Mốc tiến bộ xét chất lượng tuyệt đối80 điểm; vị trí trên bảng mang ý nghĩa thi đua, không chặn lên bậc chỉ vì đối thủ giỏi.

Năm hạng thi đua riêng với chức vụ: Mới tham gia → Vững nghề → Nổi bật trong đơn vị → Tiêu biểu khu vực → Dẫn dắt nghề. Chuyển hạng cần lần lượt 2/3/4/6 kỳ đạt từ80 điểm, cùng điều kiện bậc nghề2/3/5/7 đã có. Tổng tối thiểu 15 kỳ = 150 ca hợp lệ đến hạng cao nhất; không tự giáng chức hoặc xóa danh hiệu đã có khi một kỳ kém. Chức vụ thực tế vẫn qua điều kiện và xét thăng tiến đang có.

## Khen thưởng và lợi ích

Kết quả kỳ: dưới60 là cần rèn thêm;60–79 đạt;80–89 tốt;90–100 xuất sắc. Điểm và điều kiện công khai. Danh hiệu/giấy ghi nhận vào hồ sơ nghề, có nhận xét cụ thể gắn sự việc; nội dung mới gồm tình huống giao việc, kiểm tra thành quả, hướng dẫn người mới và đề nghị khen đúng người.

Đề xuất quỹ thưởng kỳ có trần theo năm hạng300/900/2.000/5.000/10.000 xu, đồng thời không quá10% thu nhập nghề hợp lệ kỳ đó. Thu nhập hợp lệ là tiền công/lương và doanh thu dịch vụ game sinh đã đối soát; loại góp vốn, vay, chuyển tiền, bán tài sản, thưởng thi đua/tay nghề/thăng tiến, tiền khách giao hộ và phần do nhân viên tự chạy. Chỉ kỳ đạt80+ nhận thưởng; không nhân các hệ số nghề/thiết bị vào khoản này. Đây là mức đề xuất phải mô phỏng dữ liệu trò chơi trước khi phát hành, không phải doanh thu đã đo.

Thưởng danh hiệu tách khỏi xu; chùa nhận ghi nhận công quả và điểm tinh thần, không có thưởng thi đua bằng xu hoặc so ai cầu nguyện/cúng nhiều hơn. Hoạt động đi chùa/thẻ chúc vẫn giữ cách chơi hiện tại.

Được giao trách nhiệm cao hơn phải có hành động thực: nhận bảng việc của tổ, phân công NPC theo kỹ năng, kiểm lại kết quả, giúp người làm sai sửa và chọn hồ sơ xứng đáng khen. Mỗi nghề có ít nhất 3 tình huống quản lý riêng. Phần thưởng mở nội dung chỉ công bố khi nội dung đó đã được nối vào game;540 gói công thức/mẫu hàng thiết kế trước không được coi là đã triển khai nhờ tính năng này.

## Nếu dùng người chơi thật

Tổ nghề tham gia tự nguyện; bảng xếp hạng theo nghề, cùng hạng và kỳ7 ngày thực để không so ca dài với ca ngắn. Điểm tuần lấy tối đa ca thi đua hợp lệ đầu tiên mỗi ngày, ít nhất3 ngày mới được xếp hạng; không bán thêm lượt tính điểm. Hòa điểm cùng hạng, không dùng số tiền mua nâng cấp làm tiêu chí phụ. Người ít chơi vẫn có tiến trình NPC riêng.

Trưởng tổ đã đủ bậc nghề được đề nghị khen cấp dưới cùng tổ bằng hồ sơ việc sạch có thật. Không tự khen; một người xét tối đa1 người/ngày thực, một người nhận tối đa1 lần/7 ngày; không lặp hồ sơ. Máy chủ xác minh tư cách hai bên và chống gửi lặp trong một giao dịch. Lời khen người thật là huy hiệu/lời ghi nhận, không sinh xu, cộng điểm xếp hạng hoặc tự thăng chức. Nhờ vậy không thể tạo vòng khen chéo để chiếm thưởng. Công an giữ luật đặc thù đang có, không đổi quyền hiện tại bằng luật chung này.

Không mở quyền phạt/sa thải người chơi khác trên các nghề chỉ có danh hiệu. Chỗ lãnh đạo giới hạn toàn server, quyền loại khỏi tổ và tranh ghế là tính năng khác cần luật riêng; tiến trình tay nghề cá nhân không bị một người giữ ghế khóa lại.

## Ma trận 54 nghề

Cột cuối là nội dung cần xây hoặc nối vào luồng hiện có, không phải khẳng định đã có.

| Nghề (ID) | Người/tổ chức ghi nhận | Bằng chứng đặc thù | Việc để chinh phục khi tiến bộ |
|---|---|---|---|
| Tiệm mẹ & bé (`mother_baby`) | Hội tiểu thương / chủ tiệm lớn | Tư vấn đúng nhu cầu, gói đúng đơn, xử lý đổi trả | Đơn quà theo đoàn và hướng dẫn nhân viên |
| Nhà thuốc nhỏ (`pharmacy`) | Dược sĩ phụ trách / quản lý cụm | Đối chiếu phiếu, đúng mã, nhận ra trường hợp cần chuyển | Kiểm soát quầy và hướng dẫn người mới |
| Một ngày làm kế toán (`accounting`) | Hội nghề / trưởng văn phòng | Đối soát có bằng chứng, phát hiện sai lệch, bảo mật | Nhận bộ sổ phức tạp và kiểm tra hồ sơ nhóm |
| Chăm sóc khách hàng (`customer_care`) | Trưởng ca dịch vụ | Giải quyết đến cùng, lời hẹn đúng, chuyển cấp đúng | Điều phối ca đông và kèm nhân viên |
| Một ngày làm giáo viên (`teacher`) | Tổ chuyên môn / ban giám hiệu | Dạy đúng nội dung, quan tâm học sinh, đánh giá công bằng | Chuyên đề, hướng dẫn giáo viên mới |
| Hướng dẫn viên du lịch (`tour_guide`) | Điều hành tour | Đúng lịch, đủ đoàn, giải quyết sự cố có trách nhiệm | Đoàn khó và điều phối hướng dẫn viên |
| Tiệm trà sữa (`milk_tea`) | Hội chủ quán / giám khảo hội thi | Đúng công thức, vệ sinh, chất lượng và phản hồi | Đơn sự kiện và đào tạo pha chế |
| Quán mì cay (`restaurant`) | Hội đầu bếp / chủ quán | Đúng món, an toàn thực phẩm, xử lý giờ cao điểm | Tiệc đặt trước và điều phối bếp |
| Tiệm bánh & cà phê (`cafe_bakery`) | Trưởng bếp / hội nghề bánh | Mẻ bánh đạt, đồ uống đúng, thời gian phục vụ hợp lý | Đơn bánh riêng và điều phối quầy–lò |
| Tiệm hoa (`florist`) | Hội hoa / chủ cửa hàng | Đúng yêu cầu, hoa tươi, đúng hẹn | Trang trí sự kiện và điều phối thợ |
| Tạp hóa đầu hẻm (`grocery`) | Tổ tiểu thương / chủ chuỗi | Hạn dùng, cân đúng, giá rõ và hóa đơn đúng | Đơn sỉ và hướng dẫn ca kiểm kho |
| Tiệm sửa đồ (`repair`) | Trưởng xưởng | Chẩn đoán đúng, báo giá thật, sửa có kiểm tra | Ca khó và nghiệm thu của thợ mới |
| Nông trại rau & gà (`farm`) | Hợp tác xã / hội nông dân | Chất lượng lô, nhật ký thật, thu hoạch đúng thời điểm | Hợp đồng vụ mùa và hướng dẫn hộ mới |
| Giao hàng (`delivery`) | Trưởng tuyến / điều phối | Đúng người, đủ kiện, đối soát COD và đi an toàn | Tuyến phức tạp và phân việc giao nhận |
| Homestay nhỏ (`homestay`) | Hiệp hội lưu trú / chủ cơ sở | Phòng sạch, đặt phòng đúng, giải quyết phản ánh | Đoàn đặt phòng và điều phối vận hành |
| Chăm sóc thú cưng (`pet_care`) | Trưởng ca chăm thú | Chăm đúng loài, nhận diện nguy cơ, giao nhận rõ | Ca nội trú phức tạp và hướng dẫn chăm sóc |
| Salon tóc (`salon`) | Chủ salon / hội nghề tóc | Tư vấn hợp, kỹ thuật đúng, vệ sinh dụng cụ | Mẫu khó và đào tạo thợ |
| Kế toán doanh nghiệp (`corp_accounting`) | Kế toán trưởng | Hạch toán có căn cứ, kiểm soát sai lệch, đúng hạn | Kiểm tra nhóm hồ sơ và dẫn đội kế toán |
| Thuế & tiền lương (`tax_payroll`) | Trưởng bộ phận thuế–lương | Tính đúng, hồ sơ đủ, bảo mật tiền lương | Kỳ quyết toán và soát xét nhóm |
| Kế toán tập đoàn (`group_accounting`) | Giám đốc tài chính | Đối chiếu nội bộ, loại trừ đúng, trình bày rõ | Dự án hợp nhất nhiều đơn vị |
| Shop quần áo (`clothing`) | Hội chủ shop / quản lý chuỗi | Tư vấn size, đơn chính xác, đổi trả công bằng | Bộ sưu tập và đào tạo bán hàng |
| Shop thú cưng (`pet_shop`) | Hội cửa hàng thú cưng | Tư vấn phù hợp, hàng đúng, bảo quản và đổi trả | Đơn lớn phù hợp và điều phối quầy |
| Trà đá vỉa hè (`tra_da`) | Tổ tiểu thương | Phục vụ đúng, vệ sinh, bố trí gọn và phản hồi tốt | Điều phối ca đông tại vị trí hợp lệ |
| Bán trái cây (`fruit`) | Hợp tác xã / hội tiểu thương | Phân loại, cân đúng, độ tươi và nói rõ chất lượng | Đơn giỏ quà và nghiệm thu lô |
| Thu gom rác (`garbage`) | Chị Hạnh / tổ thu gom | Không bỏ sót tuyến, phân loại đúng, xử lý nguy hại, phản ánh có bằng chứng | Tổ viên → tổ phó → tổ trưởng; phân tuyến và nghiệm thu |
| Thông ống cống (`drain`) | Trưởng đội thoát nước | Chẩn đoán, trang bị, xử lý sạch và nghiệm thu | Điểm tắc khó, điều phối đội xử lý |
| Nội trợ, giúp việc nhà (`homemaker`) | Gia đình / hội nghề chăm nhà | Hoàn thành việc đã nhận, tiết kiệm hợp lý, chăm sóc chu đáo | Điều phối lịch gia đình và truyền nghề |
| Bán kem (`ice_cream`) | Chủ quầy / hội ẩm thực | Bảo quản lạnh, đúng món, phục vụ sạch | Đơn sự kiện và điều phối quầy |
| Làm móng (`nail`) | Chủ tiệm / hội nghề | Tư vấn, vệ sinh, thao tác và mẫu đúng hẹn | Mẫu khó và kèm thợ mới |
| Thầy ở chùa (`pagoda`) | Ban công quả | Giúp việc cộng đồng, giữ nếp, hoàn thành việc đã nhận | Điều phối công quả và giúp người mới; không xếp hạng cầu nguyện |
| Bán phở (`pho`) | Hội nghề bếp / chủ quán | Đúng tô, nước dùng đạt, vệ sinh và giờ cao điểm | Đơn đoàn và hướng dẫn phụ bếp |
| Bán cơm (`com`) | Chủ quán / hội ẩm thực | Món chín đúng, suất đủ, giữ nóng và xử lý đơn | Đơn suất ăn và phân công bếp |
| Photobooth (`photobooth`) | Chủ studio / hội nghề ảnh | Đúng yêu cầu, bố cục, sự đồng ý và chất lượng bàn giao | Gói sự kiện và điều phối chụp |
| Giúp việc theo giờ (`giupviec`) | Điều phối dịch vụ / gia đình | Sạch đúng hạng mục, tài sản nguyên vẹn, đúng hẹn | Lịch nhiều nhà và hướng dẫn nhân viên |
| Nấu cơm gia đình (`naucom`) | Gia đình / điều phối bếp nhà | Khẩu phần phù hợp, an toàn, đủ món và đúng giờ | Bữa nhà nhiều người và hướng dẫn nấu |
| Bảo mẫu (`babysitter`) | Gia đình / điều phối chăm trẻ | An toàn, đúng nếp sinh hoạt, giao nhận và báo cáo | Ca chăm phức tạp và kèm người mới, giữ giới hạn giám sát |
| Thư viện – Lưu trữ (`library`) | Phụ trách thư viện | Mượn trả đúng, tìm sách phù hợp, lưu trữ và phục vụ | Chuyên đề cộng đồng và điều phối thư viện |
| Phi công (`pilot`) | Đội bay / giám sát huấn luyện | Quy trình, xử lý tình huống, quyết định an toàn | Huấn luyện và quản lý khai thác theo cơ chế hiện có |
| Tiếp viên hàng không (`flight_attendant`) | Tiếp viên trưởng | Kiểm tra cabin, hỗ trợ hành khách, phối hợp và an toàn | Dẫn tổ tiếp viên và hướng dẫn người mới |
| Thợ dầu khí (`oil`) | Đốc công / giàn trưởng | Giấy phép công việc, nhận diện nguy cơ, phối hợp và bàn giao | Điều phối tổ và xử lý ca phức tạp |
| Hành chính – Nhân sự (`hr_admin`) | Trưởng phòng nhân sự | Hồ sơ chính xác, công bằng, lịch và bảo mật | Tuyển dụng theo đợt, hướng dẫn đội nhân sự |
| Thư ký giám đốc (`secretary`) | Trưởng văn phòng | Lịch đúng, ưu tiên hợp lý, hồ sơ đủ và bảo mật | Điều phối sự kiện và nhóm văn phòng |
| IT hỗ trợ (`it_helpdesk`) | Trưởng nhóm kỹ thuật | Chẩn đoán, quyền truy cập, khắc phục và bàn giao | Sự cố phức tạp và điều phối hỗ trợ |
| Gác chắn đường sắt (`railway`) | Trưởng cung / quản lý tuyến | Quy trình chắn, liên lạc, cảnh báo và bàn giao | Phân công ca và xử lý tình huống tuyến |
| Điều dưỡng (`nurse`) | Điều dưỡng trưởng | Kiểm tra đúng, chăm sóc, chuyển cấp và ghi nhận | Điều phối ca và kèm điều dưỡng mới |
| Gác hải đăng (`lighthouse`) | Trạm trưởng | Đèn, nhật ký thật, nhận diện sự cố và bàn giao | Phân ca trạm và phối hợp khu vực |
| Tổng đài cứu hộ (`rescue`) | Trưởng ca điều phối | Ưu tiên đúng, điều lực phù hợp, theo dõi và bàn giao | Điều phối nhiều vụ có nguồn lực rõ |
| Cứu hộ hồ bơi (`lifeguard`) | Trưởng ca hồ bơi | Quan sát, phản ứng đúng, hỗ trợ và ghi nhận | Phân khu quan sát và hướng dẫn tổ |
| Công an phường (`police`) | Cấp chỉ huy theo chức vụ hiện có | Hồ sơ đúng, hòa giải, tuần tra, xử lý có căn cứ | Giữ cấp bậc/chức vụ/khen thưởng đang có, nối hiển thị thi đua |
| Bán album ZPOP (`zpop`) | Chủ shop / hội tiểu thương | Đúng mẫu, đủ đơn, đóng gói và giải quyết đổi trả | Đợt mở bán và điều phối nhân viên |
| Xưởng vẽ (`art_studio`) | Chủ xưởng / hội đồng nghệ thuật | Đúng đề bài, kỹ thuật, câu chuyện và chất lượng bàn giao | Triển lãm, đơn riêng và hướng dẫn học viên |
| Luật sư (`lawyer`) | Luật sư hướng dẫn / trưởng văn phòng | Chứng cứ, đối chiếu, lập luận và bảo mật | Hồ sơ phức tạp và soát xét nhóm |
| Giặt ủi (`laundry`) | Chủ tiệm / quản lý xưởng | Phân loại, chọn quy trình, không hỏng đồ và giao đúng | Đơn hợp đồng và điều phối giặt–trả |
| Bưu điện (`post_office`) | Trưởng bưu cục | Cân/cước đúng, giấy tờ đủ, phân tuyến và giao nhận | Ca bưu gửi lớn và điều phối quầy |

## Ví dụ thu gom rác

Đầu ca chị Hạnh giao mục tiêu tuyến sạch, không bỏ sót, phân loại đúng và xử lý vật sắc nhọn đúng cách. Ba đồng nghiệp NPC có thế mạnh khác nhau: kỹ phân loại, giỏi giao tiếp, giỏi sắp xếp tuyến. Kết ca cho xem tuyến hoàn tất, phản ánh được giải quyết và lý do trừ điểm. Kỳ tốt nhận giấy ghi nhận, thưởng giới hạn và hồ sơ đủ điều kiện thăng tiến.

Lên tổ phó có ca phân tuyến, phát hiện tuyến bị bỏ sót và hỗ trợ người mới. Lên tổ trưởng có nghiệm thu, xử lý phản ánh chéo và đề nghị khen người có thành tích. Điểm do kết quả thật của công việc; chọn người quen nhưng hồ sơ không đủ sẽ bị từ chối. Chức danh cao hơn nữa có ca điều phối nhiều tuyến và bài hướng dẫn; xe lớn/kho lớn vẫn mua ở nhánh trang bị riêng và chỉ có lợi khi nhiệm vụ cần.

## Thiết kế kỹ thuật, lưu dữ liệu và kiểm thử

Tách nội dung nghề, bộ chấm bằng chứng, kỳ thi đua và phép khen người khác. Hook hoàn thành nhiệm vụ/kết ca là nguồn duy nhất ghi điểm. Lưu phần mở rộng cóversion, kỳ hiện tại, taskID đã ghi, tổng điểm/mẫu số và mã phần thưởng đã trả; giữ toàn bộ tiến trình promotion/mastery/org cũ. Không tính lại một lần mua hay replayrequest thành việc nghề. NPC có seed ổn định theo người/nghề/kỳ.

Nếu chọn xã hội: bảngroster/điểm/khen riêng theo namespace, dùng publicID, không lộsessionID. Kiểm tra quyền và ghi sổ trong transaction; inbox là kết quả của hành động trong game, không gửi tin người chơi khi xây tính năng. Không truy cập DB thật để thử.

Kiểm thử phải có: đủ 54 adapter hoặc chỉ rõ nghề chưa hỗ trợ; điểm thật/không có cơ hội; hủy việc/ca trống/chuyển nghề; tiền thưởng không nhân chồng/không trả lặp; NPC không thay điểm theo người chơi; lịch khen theo múi giờgame; đồng thời 2 người khen một người; tự khen/người ngoài tổ/bậc không đủ; lưu cũ và việc đang chơi dở; cảnh thi đua điện thoại/máy tính và bản dịch. Khi triển khai không đổi bản thật nếu chưa có yêu cầu deploy.

## Thứ tự làm đề xuất

1. Chốt NPC/người thật/kết hợp và điều kiện phần thưởng; giữ các thành tích cũ.
2. Xây khung cùng ca mẫu hoàn chỉnh cho thu gom rác; công an dùng adapter đọc cơ chế cũ.
3. Nối từng nhóm nghề theo ma trận, với tiêu chí và tình huống quản lý thật. Đánh dấu hoàn thành theo cả backend/UI/test, không chỉ có tên trong danh mục.
4. Nếu chọn xã hội, thêm tổ nghề và khen giữa người chơi; kiểm tra giao dịch đồng thời trước khi cho dùng.
5. Kiểm tra kinh tế và hồi quy, báo cáo phạm vi thực sự xong; giữ local theo yêu cầu chưa deploy.
