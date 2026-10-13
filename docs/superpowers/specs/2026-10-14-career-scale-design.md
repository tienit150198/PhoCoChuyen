# Mở rộng 54 nghề: từ tự làm đến điều hành cơ sở và chuỗi

Ngày 14/10/2026. **Bản đề xuất để chủ game xem xét, chưa triển khai hoặc deploy.** Căn cứ mã nguồn local `4f7aa3ce`; không truy vấn DB hay đo lại tài sản, thu nhập người chơi ở lần lập phương án này. Giá được tính theo yêu cầu phục vụ cả người có hàng trăm triệu xu, không phải kết quả định giá từ phân bố tài sản live.

## 1. Kết luận thiết kế

Đề nghị làm **quy mô cơ sở có nghiệp vụ quản lý thật**, bắt đầu tạp hóa. Khi lớn lên người chơi chuyển dần từ phục vụ từng khách sang chọn hàng, phân ca, điều phối kho, nhận hợp đồng và kiểm chất lượng. Vẫn vào từng cửa hàng, làm nghề và giao tiếp trong cảnh 2.5D được.

Đã cân nhắc ba hướng: chỉ đổi tên/cộng hệ số tiền (nhanh nhưng ít việc mới); mở một nghề riêng cho mỗi loại siêu thị (tách mất tiến độ); hoặc mở các hình thức cơ sở trong nghề gốc. Chọn hướng thứ ba: giữ XP, chứng chỉ, tay nghề, thi đua và nâng cấp đã mua.

- **34 nghề kinh doanh:** có tài sản, cơ sở, khách hàng, chi nhánh, hàng/vật tư và lời lỗ.
- **19 nghề cơ quan/làm công:** nhận dự án và điều phối đội/đơn vị; tiền cá nhân dùng học chuyên môn và mua tiện ích phù hợp. Không mua chức vụ, quyền xử phạt hoặc sở hữu cơ quan.
- **Chùa:** phát triển công quả và phối hợp cộng đồng; không bán quy mô tín ngưỡng hay lấy tiền cúng làm lợi nhuận cá nhân. Giữ đi chùa, thắp hương, cầu may, thẻ công khai/riêng tư và điểm tinh thần theo cách chơi hiện tại.

Danh sách được so với `game.content.CAREERS`: **54/54 nghề, mỗi nghề có 8 mốc phạm vi = 432 trường hợp tính toán**. Đây là số cấu hình thiết kế, không phải 432 tính năng đã làm.

- [Lộ trình, việc mới và tài nguyên của đủ 54 nghề](career-scale-evidence/careers.md).
- [Giá từng nhóm, lợi nhuận, vốn dự phòng và hoàn vốn](career-scale-evidence/economy-summary.md).
- [CSV 432 trường hợp](career-scale-evidence/economy.csv).
- [Công cụ tính lại](career-scale-evidence/calculate.py).

## 2. Nền tảng đang có và khoảng trống

| Có trong source hiện tại | Cần bổ sung cho phương án này |
|---|---|
| Chứng chỉ kinh doanh cơ bản/nâng cao/quản lý chuỗi; kiểm tra chủ nhiều quầy | Nhận diện cơ sở quy mô lớn và dùng lại chứng chỉ, không tạo giấy trùng quyền |
| Quầy có sổ hàng, nhân viên, khách, thuế và chi phí theo thời gian | Nhóm cơ sở cùng nghề thành chuỗi, kho trung tâm, điều chuyển và báo cáo theo điểm |
| Quyền số quầy lên 50; kho quầy lên 20.000; nhập quầy lên 1.000 | Đồng bộ cơ sở mới vào quyền sở hữu chung, không tự cấp thêm 50 quyền cho mỗi nghề |
| Kho nghề thường lên 4.000/mã; cơ chế riêng cho mẹ bé/dược/trà sữa | Phòng, bàn, máy, ghế, xe, đội có lịch sử dụng thực tế |
| Nhánh nhập kho chung local lên 4.000/dòng; khác nhánh sức chứa | UI phân biệt quy mô, kho, số lượng một lần nhập và công suất phục vụ |
| Thăng tiến, tay nghề, thi đua NPC và tình huống quản lý | Quản lý xuyên suốt nhiều bước, hợp đồng và kết quả theo cơ sở |
| Tạp hóa đã có cân hàng, hạn dùng, khuyến mãi, đối thủ Mây Mart, đơn sỉ và sự cố | Đơn nhiều đợt/liên điểm, hợp đồng nhà cung cấp, nhiều quầy thu ngân, kho trung tâm |
| 540 gói nội dung nghề nằm trong tài liệu đề xuất ngày 13/10 | Chọn gói thật sự cần cho từng bậc, viết nhiệm vụ, nối vào kho/đơn/kiểm tiền; chưa có hệ thống runtime 540 gói |

Nguồn: `business_progression.py`, `quay_progression.py`, `capacity_progression.py`, `order_progression.py`, `operations.py`, `career_mastery.py`, `career_competition.py`, `careers/grocery.py`. Trạng thái source local không đồng nghĩa mọi thay đổi này đã phát hành.

## 3. Tạp hóa: giá mở và lợi ích cụ thể

Đơn vị tiền là xu. **Giá mỗi hàng là tiền nâng từ bậc trước**, không phải giá cộng dồn và chưa bao gồm vốn lưu động.

| Bậc | Hình thức | Giá nâng | Tổng đã trả | Điểm điều phối tối đa/ca | Vị trí phục vụ toàn chuỗi | Nội dung mới chính |
|---:|---|---:|---:|---:|---:|---|
| 0 | Tạp hóa hiện có | Giữ nguyên | — | Giữ nguyên | Giữ nguyên | Chơi tiếp nghề và quầy cũ |
| 1 | Tạp hóa mở rộng | 50.000 | 50.000 | 1 | 2 | Chia thu ngân/kiểm kệ; hợp đồng tiếp tế nhỏ |
| 2 | Minimart | 250.000 | 300.000 | 1 | 4 | Quầy thực phẩm khô, đồ lạnh, vệ sinh; đặt lịch giao |
| 3 | Siêu thị mini | 1.000.000 | 1.300.000 | 1 | 6 | Trưởng ca, đối soát nhiều quầy, nhận đơn tổ chức |
| 4 | Siêu thị khu phố | 4.000.000 | 5.300.000 | 2 | 10 | Điểm chính và điểm nhận hàng; điều chuyển nội bộ |
| 5 | Cụm ba siêu thị | 12.000.000 | 17.300.000 | 3 | 16 | Quản lý từng điểm, lịch xe, kiểm lãi từng nơi |
| 6 | Chuỗi năm điểm | 35.000.000 | 52.300.000 | 5 | 24 | Kho trung tâm, thương lượng nhà cung cấp, hợp đồng định kỳ |
| 7 | Chuỗi khu vực | 100.000.000 | 152.300.000 | 8 | 36 | Chọn khu khách, cân tồn giữa điểm, kiểm chất lượng nhiều đội |
| 8 | Hệ thống bán lẻ | 250.000.000 | 402.300.000 | 12 | 50 | Điều hành vùng, đơn nhiều điểm, hàng nhãn riêng và xử lý thu hồi lô |

Vị trí là chỗ tác nghiệp có thể bố trí nhân sự, không phải nhân viên được tặng. Phí quy mô gồm cải tạo, thiết bị chuẩn và hạ tầng các điểm trong gói; phải có quyền sở hữu còn trống trước khi tạo địa điểm mới. Không tự mua hộ nhân viên, hàng hoặc tiện ích. Có thể phân bổ vị trí giữa các điểm, tối thiểu một vị trí và người đủ điều kiện cho mỗi điểm đang nhận việc. Bảng là tổng công suất gói, không lấy 50 nhân 12.

Các điểm trong gói được triển khai dần qua lựa chọn địa điểm và phân công của người chơi, không tự mở khi trừ tiền. Trước khi mua phải kiểm đủ quyền sở hữu cho số điểm người chơi chọn triển khai. Người đã có cơ sở phù hợp có thể đưa vào chuỗi; bảng dự toán giảm đúng phần cải tạo/thiết bị có hóa đơn còn sử dụng, không giảm các khoản đào tạo/tài nguyên khác. Trong bản đầu **chưa hỗ trợ quy đổi quầy bán ngành khác thành siêu thị**; quầy cũ vẫn hoạt động độc lập.

Quyền số quầy hiện có là giới hạn tài khoản cho các địa điểm kinh doanh phụ mới; nơi làm nghề gốc của từng nghề vẫn là nơi gốc. Ví dụ 12 điểm tạp hóa gồm một cơ sở gốc và 11 địa điểm phụ, cần 11 chỗ còn trống sau các quầy khác. Người đã mua chỗ được dùng lại. Chủ cũ vượt quyền hiện tại giữ tài sản và cách hoạt động cũ, chỉ cần mua đủ chỗ cho phần tăng thêm. Không thu thêm một nhánh “số chi nhánh” trùng quyền này.

Quy mô và kho có công dụng khác nhau: minimart mở cách tổ chức/phục vụ mới; kho quyết định số hàng giữ; hạn mức nhập quyết định mỗi lần đặt. Giữ nguyên 550 kho/80 mỗi dòng nếu người chơi mới mua kho; hiển thị rõ nút nâng nhập. Nâng quy mô không miễn phí tăng hai nhánh này. Hàng đang về/đã giữ cho đơn vẫn chiếm chỗ.

Kho của chuỗi kế thừa **tổng quyền sức chứa đã mua ở nghề**, chia thành khu chứa theo địa điểm và kho trung tâm. Không nhân một nâng cấp kho cho mọi chi nhánh, cũng không thu lại cùng một quyền. Khi nâng thành chuỗi lần đầu phải đối soát toàn bộ hàng/đơn đang giao trước khi chuyển. Không chuyển hàng giữa quầy cũ và kho nghề nếu chưa có phiếu xuất/nhập và giá vốn tương ứng.

## 4. Người chơi thực sự làm gì khi trở thành quản lý?

Một ca quản lý gồm: xem nhu cầu và nhận hợp đồng → dự toán/quỹ → nhập hoặc phân bổ hàng → xếp người/vị trí → xử lý biến cố → nghiệm thu/đối soát. Mục tiêu 10–20 phút thao tác có ý nghĩa, cần đo khi có bản thử; không buộc người chơi chờ đủ 20 phút để nhận tiền.

- Khách và hợp đồng nêu số lượng, giá, thời hạn, yêu cầu chất lượng. Không tạo giá bán triệu xu cho một gói mì thường; hóa đơn cao phải có khối lượng hoặc dịch vụ tương xứng.
- Mẫu/công thức cao cấp có mã hàng, vật tư, thời gian và thao tác khác. Các gói chuyên môn 10 bậc trước đây mở riêng; quy mô không tự cấp tất cả công thức. Hợp đồng cơ bản theo quy mô dùng danh mục đã mở, không buộc mua hết 10 bậc học mới dùng được cơ sở.
- NPC có năng lực, vai trò, lương và ca làm. Một người/máy/xe không đồng thời nhận hai việc. Thiếu người có thể mở ít điểm hơn, dự toán giảm theo đúng công suất đang bố trí.
- Sự cố gắn nghề: giao thiếu, mất lạnh, đổi trả, nghỉ ca, máy hỏng, khiếu nại hoặc hồ sơ sai. Có cách xử lý và báo cáo nguyên nhân; không tung phạt ngẫu nhiên vô hạn.
- Nhận hàng, điều chuyển, trả hàng và hàng hỏng đều có biên nhận; giữ nguyên giá vốn. Tiền cọc/COD/tiền giữ hộ tách khỏi doanh thu.
- Từng cơ sở có khu đi lại, quầy nhận việc, kho và NPC để nói chuyện/thả reaction. Bảng chuỗi dẫn tới đúng cơ sở; mở cửa hàng phải có nội thất đi được. Kiểm quyền riêng tư và phạm vi chat theo điểm.

Nhân viên tự chạy đơn thường theo hệ thống hiện tại. Phần hợp đồng quản lý mới cần chủ đưa quyết định và nghiệm thu, không trả thưởng lớn khi chỉ để game mở. Không ghi một hợp đồng vừa vào sổ nhân viên, vừa vào sổ ca quản lý.

## 5. Giá cho các nghề khác

Mỗi nhóm có 8 bậc tương tự, nhưng hình thức và tài nguyên khác nhau. Giá và mục tiêu lợi nhuận cùng nhân hệ số để nhóm đắt vốn không vô tình có hoàn vốn nhanh hơn chỉ vì được chọn tên nghề.

| Nhóm | Số nghề | Hệ số vốn/lãi tạp hóa | Tổng nhánh quy mô | Ví dụ đích đến |
|---|---:|---:|---:|---|
| Bán lẻ | 8 | 1 | 402.300.000 | Thời trang, đồ mẹ bé, nhà thuốc, trái cây, album, hoa, đồ thú và siêu thị |
| Ẩm thực | 8 | 0,8 | 321.840.000 | Chuỗi quán/bếp và cung ứng nhiều điểm |
| Dịch vụ | 8 | 0,7 | 281.610.000 | Salon, nail, giặt, chăm thú, chăm nhà, bảo mẫu, vệ sinh, tour |
| Kỹ thuật | 2 | 1,2 | 482.760.000 | Chuỗi xưởng sửa/đội thoát nước |
| Nông nghiệp | 1 | 1,2 | 482.760.000 | Vùng nguyên liệu và mạng lưới nông trại |
| Lưu trú | 1 | 1,5 | 603.450.000 | Hệ thống lưu trú nhiều cơ sở |
| Hồ sơ | 3 | 0,6 | 241.380.000 | Văn phòng kế toán, thuế–lương, hãng luật |
| Nghệ thuật | 2 | 0,8 | 321.840.000 | Studio ảnh, xưởng vẽ/gallery nhiều điểm |
| Vận chuyển | 1 | 1,2 | 482.760.000 | Mạng giao nhận |

Ví dụ giặt ủi có máy và lịch chu kỳ thật; homestay có phòng và lịch đặt; salon có ghế và thợ; sửa chữa có bàn/thiết bị và thời gian bảo hành; luật sư có nhóm hồ sơ, kiểm xung đột lợi ích và thời hạn. Không thay mọi tài nguyên bằng “sức chứa kho”. Tài nguyên hiện có vượt mức gói được bảo toàn; quyền hiệu lực lấy mức cao hơn, không cắt bớt để bán lại.

19 nghề cơ quan gồm chăm sóc khách hàng, giáo viên, kế toán doanh nghiệp/tập đoàn, thu gom rác, thư viện, phi công/tiếp viên, dầu khí, nhân sự, thư ký, IT, đường sắt, điều dưỡng, hải đăng, tổng đài cứu hộ, cứu hộ hồ bơi, công an và bưu điện. Các mốc là phạm vi công việc được giao, không tự thay chức vụ trong thang nghề.

Phụ cấp quản lý mới mục tiêu lần lượt **250 / 875 / 3.000 / 8.750 / 22.500 / 50.000 / 105.000 / 200.000 xu/ca nghiệm thu đầy đủ**, bằng 25% lãi mục tiêu tạp hóa vì không phải bỏ vốn sở hữu/hàng kinh doanh. Ngân sách tổ chức trả vật tư và đội ngũ; không rút ngân sách đó thành tiền cá nhân. Học phí 10 gói chuyên môn đã đề xuất và tiện ích cá nhân vẫn là chỗ tiêu xu; không thu phí mở cơ quan. Không trả phụ cấp dự án này thêm lần nữa qua dự án của nhánh 540 gói.

## 6. Công thức kinh tế và kiểm tra hoàn vốn

Tất cả là **kịch bản mục tiêu**, chưa mô phỏng bằng các lệnh game mới. Lãi cho cả mạng lưới một nghề trong một ca, không phải mỗi địa điểm. Không áp vào các đơn thường hiện có.

Tạp hóa đầy nhu cầu: hàng 70% doanh thu, lương 8%, mặt bằng/điện/bảo trì 4%, hao hụt dự phòng 2%, thuế doanh thu 4%, còn 12%. Thuế 4% dựa cơ chế nơi làm việc `operations.RULES`; quầy có thuế riêng 7% trên lãi ở `quay_market.py`. Đơn quản lý mới thuộc nơi làm việc, không chạy qua cả hai cách thuế. Khi ghi sổ thực tế, dự phòng thuế phải được cấn với hóa đơn thuế đã phát sinh để không trừ hai lần.

Gọi R là doanh thu ca đầy; V là tỷ lệ chi phí biến đổi gồm hàng + 60% lương + hao hụt + thuế; F là mặt bằng + 40% lương; d là tỷ lệ nhu cầu:

`Lãi(d) = R × [d × (1 − V) − F]`.

Tạp hóa có V = 80,8%, F = 7,2%, nên đầy khách lãi 12%R; 80% nhu cầu còn 8,16%R; 60% còn 4,32%R. Hòa vốn ở 37,5% nhu cầu. Tỷ lệ 80% ở đây là **ít khối lượng bán hơn**, không phải 20% khách trả hàng hay tỷ lệ làm sai. Hủy, lỗi, hoàn tiền phải kiểm thêm bằng dữ liệu nghiệm thu.

| Bậc tạp hóa | Lãi ca đầy | Lãi ở 80% nhu cầu | Số ca thu hồi phí bậc mới ở đầy / 80% |
|---:|---:|---:|---:|
| 1 | 1.000 | 680 | 50 / 74 |
| 2 | 3.500 | 2.380 | 100 / 148 |
| 3 | 12.000 | 8.160 | 118 / 174 |
| 4 | 35.000 | 23.800 | 174 / 256 |
| 5 | 90.000 | 61.200 | 219 / 321 |
| 6 | 200.000 | 136.000 | 319 / 468 |
| 7 | 420.000 | 285.600 | 455 / 669 |
| 8 | 800.000 | 544.000 | 658 / 968 |

Hoàn vốn = **phí bậc mới / (lãi bậc mới − lãi bậc trước)**, làm tròn số ca lên. Bậc đầu giả định chưa có dòng hợp đồng quản lý, lãi dòng này bằng 0. Ví dụ bậc 8: 250 triệu / (800.000 − 420.000) = 657,89 ca. Nếu làm đủ 4 ca/ngày: khoảng **165 ngày**; ở 80% nhu cầu khoảng **242 ngày**. Chơi một ca/ngày thì lâu gấp bốn. Đây là hoàn phí quy mô tăng thêm, chưa thu hồi học phí, kho, nhập hàng hay vốn lưu động.

So sánh giả định đội/tài nguyên dành cho đơn thường không bị cắt để phục vụ hợp đồng mới. Nếu dùng chung làm mất thu nhập nền, phải trừ cả phần mất đó vào lãi tăng thêm. Không lấy toàn bộ lãi siêu thị làm lãi tăng thêm; không coi tiền bỏ mua hàng vẫn nằm trong kho là giá vốn hàng đã bán.

Ví dụ siêu thị mini bậc 3: R = 100.000/ca; chi 88.000; còn 12.000; cần quỹ hai ca 176.000. Từ bậc 2 lên phải chuẩn bị phí 1 triệu cộng phần thiếu quỹ/nhân sự, không chỉ nhìn nút nâng. Bậc 8: R xấp xỉ 6,667 triệu; tổng chi 5,867 triệu; còn 800.000. Hai ca dự phòng khoảng 11,733 triệu, chưa phải tiền bị tiêu mất ngay khi mua gói.

Một nhánh nâng kho hoặc nhập hàng hiện có tổng giá 152.692.000 xu. Nếu chọn mua đủ **quy mô + kho + nhập + 10 gói nội dung chuyên môn đề xuất**, tổng danh mục tạp hóa là **860.376.000 xu**, chưa gồm quyền quầy nếu thiếu và vốn hàng. Đây là gói tối đa tự chọn; không bắt mua toàn bộ để lên minimart. Khoản đã trả được giữ nguyên, không thu lại. Các giá đề xuất trong tài liệu là giá cuối hiển thị, không đi qua chỉ số giá thêm lần nữa.

**Không nhân chồng** phần lãi quản lý mới với thưởng nhân viên 40%, thưởng quầy 110%, x3 ngày, tăng ca hoặc thiết bị nhân tiền cũ. Các phần cũ vẫn tính cho đơn cũ; kết quả quản lý mới có nguồn tiền và biên nhận riêng. Thưởng thi đua hiện tại giữ trần và loại lãi quản lý khỏi cơ sở tính thưởng tiền, tránh mở thêm vòng nhân.

## 7. Giới hạn và tiến độ để chơi lâu

Đề xuất một ngân sách chung cho **hợp đồng nâng cao và quản lý mới**: tối đa 4 suất/ngày thực theo giờ máy chủ Asia/Bangkok, tích tối đa 12 suất; mở tính năng được 1 suất và ngày đó không cấp thêm. Đổi nghề, đổi chi nhánh, tải lại hoặc đổi ngày nghề không hồi suất. Đây là giới hạn phần hợp đồng tiền lớn, không khóa đi lại, trò chuyện, làm nghề thường hoặc các quyền đang có.

Mỗi hợp đồng nhận giữ một suất; bắt đầu công việc tiêu suất. Hủy trước khi bắt đầu trả suất, không đổi seed/khách/giá để reroll. Mất kết nối được tiếp tục cùng ca. Nhân viên có thể hoàn tất bước đã giao nhưng cần chủ nghiệm thu; chưa nghiệm thu không cấp ca khác trên cùng tài nguyên. Không bán thêm suất để vượt trần tiền.

Các gói nội dung ngày 13/10 từng đề xuất 1 ngân sách/giờ, giữ 3. **Phương án mới thay phần ngân sách tiền của đề xuất đó**, không mở cả hai song song. Các đơn chuyên môn trong cùng hợp đồng chia ngân sách thu/chi của hợp đồng; không nhận thêm tiền thưởng theo mỗi gói. Danh mục công thức và học phí giữ để xem xét độc lập.

Điều kiện lên tám mốc quy mô: **3 / 7 / 14 / 30 / 60 / 100 / 160 / 240 ngày thực đạt chuẩn**, cùng **10 / 30 / 70 / 140 / 260 / 450 / 750 / 1.200 việc sạch** tích lũy trong nghề. Một ngày chuẩn có ít nhất 3 việc tự làm và tỷ lệ không lỗi ≥80%; bậc 2 trở đi còn cần ít nhất một ca quản lý được nghiệm thu trong ngày đó. Điều kiện là tích lũy, không cộng lại sau mỗi bậc. Người giàu vẫn phải học cách vận hành; người ít chơi không mất tiến độ vì bỏ vài ngày.

Ngày nghề hiện tại có thể tăng bằng thao tác chơi, nên không dùng nó làm ngày thực. Chỉ công nhận lịch sử có timestamp đáng tin và đủ bằng chứng; không suy ra từ số dư hay số ngày trong save. Việc sạch/tay nghề đã ghi nhận hợp lệ được kế thừa. Ngày thực mới cần bộ đếm riêng; do đó mốc 240 ngày là mục tiêu dài hạn dự kiến, chưa thể tuyên bố người chơi hiện tại đã đạt hay chưa.

Từ minimart/cơ sở tương đương cần chứng chỉ kinh doanh nâng cao; từ ba điểm kinh doanh cần chứng chỉ quản lý chuỗi. Chứng chỉ đã có được công nhận; quy tắc kiểm tra/quyền quầy cũ tiếp tục áp dụng. Nghề cơ quan giữ điều kiện chuyên môn/bổ nhiệm hiện tại ngoài điều kiện dự án. Tên mốc “điều phối” không cấp quyền lên người chơi khác.

Tiện ích trả phí mở dần theo các nhánh đã có: số lượng một lần nhập, số vị trí quản lý trong một thao tác, mẫu phân ca, điều chuyển nhiều dòng. Chức năng mới chỉ bán khi thực sự thực thi, có xem trước chi phí và hạn mức quỹ. Không khóa lại thao tác hoặc tự động hóa người chơi đã mua. Dùng hệ giá 3 nghìn đến 100 triệu cho nhánh tiện ích mới nếu có, nhưng phải trình riêng lợi ích mỗi bậc trước khi thêm; **không tính nhánh chưa thiết kế đó vào 860,376 triệu**.

## 8. Cạnh tranh NPC, ghi nhận và bảo vệ tiến độ

Giữ thi đua NPC theo nghề. Thêm nhận xét dựa trên đúng báo cáo ca: thiếu hàng bao nhiêu, đổi trả do lỗi nào, ca nào bố trí thiếu người, cơ sở nào thua lỗ. NPC có chất lượng/danh mục/chi phí riêng, không tự tăng điểm bám theo người chơi. Tạp hóa dùng đối thủ Mây Mart đã có làm tuyến câu chuyện cạnh tranh theo khu; không lấy hết khách chỉ vì người chơi không online.

Kết quả tốt mở cơ hội hợp đồng/quan hệ nhà cung cấp phù hợp, không tự tăng trần tiền. Điều kiện tiến triển là chất lượng tuyệt đối, không bắt thắng một NPC hạng nhất. Người mua nhiều tài sản không tự được điểm nghề. Cấp trên, hiệp hội, khách hàng hoặc ban công quả ghi nhận đúng loại nghề.

Chỉ khấu trừ chi phí của ca mới đã xác nhận, giữ tiền bảo đảm theo dự toán tối đa. Hết quỹ/hàng/nhân sự thì dừng nhận ca, không tự vay hoặc rút ví để cứu tiệm. Mở một ca bị lỗ có bảng giải trình; hạn mức tổn thất không vượt quỹ đã cam kết. Cơ sở đã mua không biến mất khi ngừng hoạt động. Phần chi phí thời gian của quầy cũ giữ theo luật cũ; không áp thêm phí quy mô mới cho cả thời gian người chơi vắng mặt.

## 9. Chia đợt làm và tiêu chí nghiệm thu

**Đợt 1 — nền tảng và tạp hóa bậc 1–3.** Sổ hợp đồng, tiền/quỹ/thuế, tài nguyên có lịch, kiểm kê và UI dự toán; mô hình minimart/siêu thị mini vào đi được. Có danh mục mới cụ thể và nhiệm vụ thu ngân/kiểm kệ/phân ca. Chạy mô phỏng bằng lệnh thật trước khi mở mua trên server.

**Đợt 2 — tạp hóa bậc 4–8 và chuỗi.** Điểm phụ, quản lý từng điểm, kho chung, điều chuyển, chứng chỉ/quyền số quầy, NPC cạnh tranh. Chỉ phát hành bậc có đủ nội dung và cảnh chơi; bậc chưa làm hiển thị dự kiến và chưa thu xu.

**Đợt 3 — 33 nghề kinh doanh còn lại.** Ưu tiên quần áo, giặt ủi, salon, quán ăn vì tài nguyên và doanh thu dễ kiểm; tiếp đến lưu trú, nông nghiệp, hồ sơ, nghệ thuật và vận chuyển. Có adapter riêng cho phòng/xe/máy/hồ sơ; không dùng một hàm tăng kho thay tất cả.

**Đợt 4 — 19 nghề cơ quan và công quả.** Dự án quản lý nhóm gắn thăng tiến, thi đua; tách ngân sách tổ chức và phụ cấp; giữ luật chức vụ công an/phi công và nghiệp vụ an toàn. Chùa mở qua trải nghiệm, không thu học phí hoặc giới hạn số lần đi chùa/thẻ chúc theo ngân sách ca kinh doanh.

Tiêu chí trước phát hành:

1. Bảng đầy đủ 54 ID khớp registry; mỗi bậc bán được có nội dung, tài nguyên thật, chi phí, cách nghiệm thu và lợi ích thực thi.
2. Mua/tái gửi lệnh/đa tab chỉ trừ tiền một lần; sai bậc hoặc thiếu quyền/quỹ từ chối trước khi trừ. Giá công khai đúng số cuối cùng.
3. Nâng cấp giữ XP, giấy, danh hiệu, hàng, đơn đang giao, người và quyền đã mua. Lập báo cáo chênh số lượng/giá vốn/tiền trước-sau migration; chênh phải bằng giao dịch được cho phép.
4. Không bán âm hàng, trùng máy/phòng/xe/người; điều chuyển bảo toàn số lượng và giá vốn; chuỗi không nhân quyền kho hay thưởng theo số điểm.
5. Ngân sách ca dùng chung tài khoản, server clock, ghi nhận một lần; đổi nghề hoặc mở thêm điểm không vượt 4 suất phát sinh/ngày. Có kiểm thử hết ngày, offline, replay, hủy, hoàn và mất kết nối.
6. Sổ thật khớp mô hình trong kịch bản kiểm soát; kiểm 100/80/60% nhu cầu, thiếu người, hàng hỏng và hợp đồng lỗi. Đối chiếu thuế, giá vốn, nhân tiền và chi phí cơ hội. Không phát hành chỉ vì CSV tính đúng.
7. Trước chốt giá live, đọc thống kê tổng hợp tài sản thanh khoản và thu nhập theo nghề (không đưa tên người chơi vào tài liệu), đo thời lượng ca thực và nguồn thu khác. Đặc biệt kiểm tăng cung tiền khi người chơi có sẵn hàng trăm triệu lên bậc cao.
8. Đi được vào từng điểm trên mobile/desktop, nhìn đúng quầy/NPC/tài nguyên, chat/reaction đúng phòng. Màn hình phân biệt rõ “quy mô”, “sức chứa” và “mỗi lần nhập”.

Giá và thời lượng ca là cấu hình thử nghiệm được tính nhất quán, chưa phải cân bằng cuối đã chứng minh trên production. Việc của lượt này hoàn tất ở bản thiết kế và bảng tính; không thay mã game hay phát hành các bậc mới.
