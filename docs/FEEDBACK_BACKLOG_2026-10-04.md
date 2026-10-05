# Đối chiếu góp ý và lời hẹn ngày 04/10/2026

Đây là danh sách yêu cầu đã gộp theo nội dung, không phải danh sách triển khai xong. Không thay đổi trạng thái góp ý, không gửi trả lời cho người chơi. Bỏ tên, mã tài khoản và chuyện riêng không liên quan.

## Phạm vi và cách đọc trạng thái

Nguồn lưu tại `_feedback_audit_20261004`: `inbox-and-channels.json` kiểm tra lúc 10:04:32 ngày 04/10 (24 góp ý: #115, #130–152); `chat-24h.json` có 715 tin công khai/nhóm, #14923–18352, từ 03/10 10:10 đến 04/10 10:03 theo thời gian hiển thị; các lần bổ sung `chat-followup.json` và `pre-release-followup.json` tới góp ý #154 và tin #18415. `replied-170.json` ghi 8 phản hồi hoàn tất (#115,147,149–154) lúc 11:30:34. Không suy ra rằng mọi yêu cầu trong một phản hồi gộp đã được làm.

Đối chiếu thêm `docs/FEEDBACK_2026-10-04.md` và ba kế hoạch `2026-10-04-player-feedback`, `2026-10-04-live-feedback-followup`, `2026-10-04-expanded-street-life`. Báo cáo cũ ghi bản 1.7.0 triển khai lúc 11:28:43 UTC+7. Các sửa mới đã phát hành ở 1.7.3; phần kết quả và báo cáo deploy phía dưới ghi bằng chứng mới nhất.

**Quyết định phạm vi mới của chủ dự án:** sửa tính năng hiện có trước; tất cả nghề mới làm ở đợt riêng. Các nghề YouTube, quản lý khách sạn, bác sĩ, diễn viên, ca sĩ, MC, shop giày, tiệm sách cũ và karaoke nghề nghiệp dưới đây được hoãn theo quyết định này. Hoạt động đi chơi với NPC không thay cho nghề được hoãn.

Lần đọc trực tiếp bổ sung gồm các góp ý tới #164, 200 tin công khai #18473–19758 và 42 tin nhắn nhóm; sau đó ghi nhận thêm #19853 và #19887. Các mục ấy được đánh dấu **bổ sung trực tiếp**, không có trong ảnh chụp dữ liệu cũ. Mục ghi “chưa rõ” cần đúng câu, bước hoặc tình huống để tái hiện.

- **Đã hẹn, còn thiếu**: có lời nhận làm nhưng chưa có bằng chứng hoàn thành yêu cầu.
- **Đã triển khai theo báo cáo**: tài liệu/lời hồi đáp ghi đã phát hành; không phải kiểm tra lại trực tiếp bản đang chạy.
- **Có một phần**: một phần cơ chế tồn tại, phần yêu cầu còn thiếu.
- **Đã sửa trong mã hiện tại**: đã đối chiếu, kiểm tra và phát hành trong 1.7.3; tên trạng thái giữ lại để liên hệ bảng đối chiếu ban đầu.
- **Cần xác minh**: thiếu ngữ cảnh hoặc chưa tái hiện; không tự đánh dấu đã sửa.

## Tính năng hiện có: kết quả sửa và những việc cần đối chiếu

Các mục có trạng thái **Đã sửa trong mã hiện tại** đã phát hành trong bản **1.7.3** lúc **17:35:26 ngày 04/10/2026 (UTC+7)**. Các mục cần xác minh, còn thiếu hoặc nghề mới hoãn vẫn giữ nguyên trạng thái; không suy ra toàn bộ backlog đã hoàn tất. Bằng chứng triển khai: `DEPLOY_1.7.3_2026-10-04.md`.

| Nguồn | Nội dung đã gộp | Trạng thái và bằng chứng |
|---|---|---|
| Góp ý #133; yêu cầu hiện tại của chủ dự án | Bỏ giới hạn 60 món trang trí | Đã sửa trong mã hiện tại: bỏ trần tổng số đồ, trần sơn lại và cắt danh sách đồ phối ngẫu ở 120 món. `game/deco.py` và `game/deco_mate.py` trả số lượng thực, không trả trần sở hữu. Có kiểm tra mua vượt 60 và đọc đồ chung. |
| #134 | Xoay đồ nội thất thật sự | Đã sửa TV/sofa: chọn mặt trước/mặt sau, hình mặt sau khác thực sự. `decor_faces` giữ dữ liệu bố trí cũ, mua/di chuyển/bán/hoàn tác và xem nhà chung. Phạm vi là trước/sau; chưa có mọi góc xoay. |
| #135; chat #19121 (bổ sung trực tiếp) | Sống chung vợ/chồng; dùng được đồ trong nhà chung | Đã sửa: `game/family.py` yêu cầu lời mời và đồng ý trước khi dọn vào; `game/deco_mate.py` kiểm tra quan hệ và cùng nhà trước khi dùng đồ. Có luồng tủ lạnh/bồn tắm/giường/tủ đồ, không chuyển sở hữu hoặc lấy quần áo/đồ ăn của người kia. Nhà chung cập nhật mỗi 15 giây khi mở. |
| #135; #160 (bổ sung trực tiếp) | Góp tiền mua/chăm chút nhà chung | Có nguồn thanh toán quỹ chung và kiểm tra chi trên 1.000 xu theo số dư. Ngữ cảnh #160 chưa xác định rõ món/cách mua bị vướng; phần mua cụ thể vẫn cần đối chiếu. |
| #145; #163 (bổ sung trực tiếp); chat #18300,16439,16011–16032; yêu cầu hiện tại của chủ dự án | Con chung, lựa chọn sinh con, hai người cùng chăm | Đã có trong `game/family.py` và `public/js/v4/family.js`: mời nhận nuôi hoặc đón bé mới sinh, chỉ tạo khi người kia đồng ý, cùng xem/chăm một bé; sinh con chờ một ngày lịch Việt Nam. Chăm cùng một việc trong ngày chỉ tính/thu một lần; con cá nhân được giữ riêng. Có kiểm tra đồng thời, lưu/tải lại và bản sao chăm riêng sau chia tay. Giao diện thực đã kiểm tra trả 4 xu, chỉ số 65→100, nút việc đã làm vô hiệu và kết quả còn sau tải lại. |
| #138 | Nhập quần áo đúng cỡ đang thiếu | Đã sửa: đơn lẻ/đơn gộp lưu size, đưa đúng số thực nhận vào size chọn; UI có bộ chọn và phiếu hiển thị size, vẫn có tự chia. Nút gộp nhập thêm giữ size của dòng đã có nếu không chọn size mới. Size giả hoặc xung đột bị từ chối, không trừ tiền. |
| Chat #15393; admin #15429 | Pha trà sữa phản hồi nhanh hơn, bớt lag | Admin đã nhận. `public/js/careers/milk_tea.js` hiện có hiển thị ngay các bước chọn ly/nguyên liệu/đường/đá; `tests/test_milk_tea_quick.py` so khớp với server. `game/boba.py` chuẩn bị trà/trân châu tức thời ngoài đời; 20 phút là lượt trong game. Không đổi tùy tiện tốc độ máy dán nắp. Cần kiểm tra thiết bị/mạng nếu vẫn lag. |
| #150; #157,#158 (bổ sung trực tiếp, cafe_bakery ngày 4) | Chiết nhanh hơn, vạch chuẩn khớp; nướng nhanh hơn | #150 đã báo bản 1.7.0 có máy pha 2×. Mã hiện tại có lựa chọn 1×/2×/4× cả máy pha và lò, giữ lựa chọn/tốc độ mặc định cũ. Mẻ đang nướng giữ tốc độ lúc vào lò; tốc độ mới áp dụng mẻ sau. Vạch sữa dùng độ chính xác 0,1°C như chấm điểm, đồng hồ lò tính cùng nhịp với máy chấm; có kiểm tra vùng, lưu và tải lại. |
| #161; chat #18481,#19853 (bổ sung trực tiếp) | Thuê người phụ nhưng vẫn tự nấu; tìm nơi mời người tự đứng quầy | Đã sửa lời dẫn: Sổ tiệm giải thích người phụ tạo khoản phụ theo việc và lương khi khép ca; quầy trà sữa có nút xem đội. Có liên kết “Quầy của bạn” cho nhân viên tự bán khi kết thúc ngày sống. Mời bạn làm thuê ở Quầy/Làm thêm là luồng khác; câu hỏi #19853 cần hướng dẫn tới đó, không gọi người phụ là tự chơi minigame. |
| #164; chat #14950 và các câu lặp | Dễ tìm đổi nghề | Đã sửa: nút “Đổi nghề” bên tên nơi làm, menu cùng tên; giữ màn chọn nghề, xác nhận bỏ việc đang dở và tiến trình nghề. Trình duyệt di động đã bấm được nút. |
| #162; chat #19640,#19887 (bổ sung trực tiếp) | Không giới hạn chuyển khoản/rút quỹ chung | Đã sửa `game/bank_xfer.py` và `game/couple.py`: bỏ quota gửi/nhận theo ngày, số lần gửi và quota rút quỹ chung. Vẫn kiểm số dư thực, giới hạn biểu diễn số tiền và quan hệ hợp lệ. Người nhận đầy tài khoản thì tiền chờ nhận; hoàn tiền chưa nhận trả đầy đủ và thử lại chỉ trả một lần. Có kiểm tra xác nhận UI gửi 5.000 xu. |
| Chat #19211,#19250 (bổ sung trực tiếp) | Đánh giá không cuộn được/giật | Đã sửa `public/js/app.js` và CSS: phần đầu sheet cuộn dọc; chỉ thanh kéo 22px bắt thao tác đóng. `pointercancel` không đóng. Ba kiểm tra gesture thành công; trình duyệt di động 390px đã cuộn được từ phần đầu. |
| Chat #19627 (bổ sung trực tiếp) | Xem lịch sử lương | Đã sửa lối tìm: thẻ đang làm thuê có “Xem lương trong Sổ ví”; lịch sử giải thích dòng “Lương ngày” đã trả và nút “Xem cũ hơn”. Kiểm tra render/nút đi tới đúng màn thành công. |
| Chat #19723,#19742 (bổ sung trực tiếp) | Hồi phục uy tín khu phố | Đã thêm hướng dẫn cạnh chỉ số trong `public/js/v4/incidents.js`: kết quả lựa chọn ở Chuyện đời mới có thể tăng uy tín của nghề, bỏ dở có thể giảm. Phân biệt “Tình làng nghĩa xóm”; chat/nhậu/karaoke/đọc lại không tăng chỉ số này. Nút tới đời sống mở đúng màn, không thay đổi điểm. |
| Chat #19564; #18391 | Có bảo vệ nhưng vẫn mất đồ/laptop | Cần đối chiếu sự cố và giải thích xác suất bảo vệ. Thiết bị bảo vệ không mặc nhiên bảo đảm không bị trộm. Chưa có bằng chứng lỗi tính tiền hoặc phát hành sửa riêng. |
| #131 | Lỗi/khó tìm lỗi liên quan Threads | Cần đọc ngữ cảnh và tái hiện; snapshot không đủ để chỉ một lỗi cụ thể. |
| #132; #144 | Điều khiển giao hàng, nút xuống/đi | #144 có lời báo đã sửa trước đó. Có sửa điều khiển giao hàng trong mã hiện tại; kết quả và giới hạn được ghi riêng ở `docs/LOCAL_SHIPPER_2026-10-04.md`. Không gộp mọi khó khăn giao hàng thành một lỗi. |
| #140; chat #17242,#17277 | Vào tiệm tạp hóa/tiệm bánh từ bản đồ | Mã đã có hướng dẫn điều kiện chương và mở lại nghề tạm đóng miễn phí. Năm kiểm tra bản đồ/nút điều hướng thành công; không tái hiện lỗi ở luồng đã mở khóa. Cửa bị khóa theo chương vẫn là điều kiện riêng. |
| Chat #15736 | Lô tô có lỗi | Báo cáo cũ chưa tái hiện. Còn cần xác minh, không tự coi đã sửa. |
| Chat #15431,#15450 | Review đã trả lời vẫn hiện hoặc khó phân biệt | Tái hiện nguyên nhân: khách hỏi tiếp (`status=open`) vẫn nằm trong bộ lọc “Chưa trả lời”. Đã đổi thành “Cần trả lời”; chỉ gọi “Khách hỏi lại” khi đã có câu trả lời của chủ. UI đang chờ/đã khép không hiện form; backend chặn gửi lại khi đang chờ/đã đóng. Kiểm tra câu trả lời thật và khách hỏi tiếp thành công; chưa thấy backend tự ghi câu trả lời của chủ trước thao tác. |
| Chat #15809,#15841,#15019 | Xin lỗi/hoàn tiền mà số sao không đổi | Cần đối chiếu cơ chế review thay vì hứa sao tự tăng. Có phản ánh lặp, chưa kết luận lỗi. |
| Chat #16560 | Mã photobooth thay đổi/khó dùng | Cần tái hiện với mã/đơn cụ thể; không lưu danh tính ở đây. |
| Chat #15095–15096 | Không cho nhân viên nghỉ/khó tìm bước xử lý | `game/operations.py` chủ ý chặn cho người liên quan nghỉ khi còn sự cố thật chưa khép; thông báo chỉ rõ kiểm2 nguồn → chọn cách → chờ2 nhịp → hoàn tất. Khi hợp lệ, lương đã làm vẫn được giữ trong sổ. Các kiểm tra tương ứng ở `tests/test_operations.py` đã chạy qua trong batch290; chưa tái hiện lỗi ngoài điều kiện này. |
| Chat #17473 | Muốn thuê ba nhân viên | `PROPERTIES` quy định Góc tiệm nhỏ1, Tiệm cửa sổ nắng2, Tiệm sân vườn4 vị trí. UI hiện số đang thuê/tối đa và “Xem mặt bằng”; backend chặn trùng người/khác nghề/vượt chỗ và yêu cầu xác nhận trước chi. Kiểm tra tuyển/lương/cho nghỉ đã chạy qua. Chưa thấy lỗi tuyển người thứ3 tại mặt bằng đủ4 chỗ. |
| Chat #18364 | Vai trò quản lý ngành phi công | Cần UI đúng nghiệp vụ; chưa có bằng chứng một màn riêng đã triển khai. |
| Chat #14947,#14953 | Kế toán: mục11 câu2 | Cần dữ liệu câu hỏi và câu trả lời mong muốn; không tự sửa đáp án từ một câu chat thiếu ngữ cảnh. |
| Chat #15409 | Lương báo102 nhưng thực nhận82–85 | Cần đối chiếu lương gộp, khấu trừ/chất lượng và bảng kê. Chưa chứng minh là lỗi. |
| Chat #15711,#15716,#15718 | Thi chứng chỉ100 nhưng phỏng vấn40 | Cần tách hai hệ thống điểm và quyền lợi chứng chỉ; không đồng nhất điểm thi và điểm phỏng vấn. |
| #155,#156 (bổ sung trực tiếp, group_accounting ngày 6) | “Khó ợ”, “Đây nữa” | Cần xác minh câu/bước cụ thể; chỉ biết màn 402×601/812. Chưa đủ dữ liệu để sửa hoặc thay đáp án. |
| Chat #15540 (admin) | Lời hẹn cập nhật 04–05 giờ sáng | Lời hẹn vận hành cũ, không phải lịch phát hành mới. Cần đối chiếu phiên bản thực tế khi công bố kết quả. |
| Các câu xin dễ hơn/lương cao/kiếm tiền không làm | Điều chỉnh độ khó và kinh tế | Yêu cầu chưa đủ thông số, không tự tăng toàn bộ thu nhập hoặc bỏ luật. Gộp với luồng cụ thể sau khi có ngữ cảnh. |

## Nghề mới: hoãn theo quyết định hiện tại của chủ dự án

Các lời nhận trước đây được giữ để theo dõi, nhưng chưa đánh dấu hoàn thành. Đợt hiện tại sửa tính năng đang có; nghề mới thuộc đợt riêng.

| Nguồn | Nghề đã đề nghị | Phần còn lại |
|---|---|---|
| #139 | YouTube, quản lý khách sạn, bác sĩ, diễn viên, ca sĩ, MC | Sáu nghề đã được nhận ý tưởng; chưa có sáu nghề tương ứng trong registry. Homestay không thay cho quản lý khách sạn. |
| #141 | Quản lý tiệm sách cũ | Hoạt động đọc sách bí ẩn đã có trong mã mới; nghề quản lý, nhập/bán sách và vận hành tiệm vẫn hoãn. |
| #141 | Nghề karaoke | Hoạt động đi hát đã có trong mã mới; nghề vận hành karaoke vẫn hoãn. |
| Chat #15465 | Shop giày | Chưa có nghề trong registry; hoãn sang đợt nghề mới. |

## Đề xuất mở rộng còn lại

Tách các ý tưởng mới khỏi lỗi chưa tái hiện để không coi một tính năng chưa tồn tại là lỗi đã sửa.

| Nguồn | Đề xuất | Tình trạng và phần còn thiếu |
|---|---|---|
| #141; trao đổi về ông bà/gia đình | Tiệm sách bí ẩn, bốn CLB, karaoke, bữa cơm/chuyện ông bà | `game/community_outings.py` và UI đã có bảy hoạt động với NPC, câu chuyện thay đổi theo lần ghé và sổ kỷ niệm; chỉ thu một lần cho mỗi nơi trong một ngày sống. Sáu kiểm tra gồm lặp lệnh thật qua Store và nút UI thành công. Đây là hoạt động với nhân vật, chưa có CLB/gia đình giữa người chơi thật. |
| #141; chat #19600 (bổ sung trực tiếp) | Chọn beat YouTube cho karaoke | UI có đường dẫn mở beat ở tab riêng. Chưa có phát nhạc đồng bộ trong game hoặc phòng hát nhiều người. |
| #142 | Khu trường học/khu văn phòng kế toán | Đã nhận ý tưởng, chưa có bằng chứng khu riêng hoàn thành; nghề giáo viên/kế toán hiện có không thay cho khu vực này. |
| #159 (bổ sung trực tiếp) | Bạn bè ghé làm khách ở nơi làm việc | Cần thiết kế luồng khách thật ghé/mua. Bạn bè/chat/mời làm thuê hiện có chưa đáp ứng khách vào minigame. |
| Chat #15218 | Menu idol/fan | Chưa rõ thao tác và quyền lợi mong muốn; cần mô tả trước khi triển khai. |
| Chat #15976 | Kết hôn AI/NPC | Chưa có bằng chứng đáp ứng; khác kết hôn giữa người chơi. |
| Chat #15476 | Mở rộng album/chia sẻ ảnh | Album có sẵn; phần mở rộng chưa rõ, chưa đánh dấu hoàn thành. |
| Chat #15004 | Cây lớn nhanh hơn | Chưa có kiểm tra tốc độ/mốc mong muốn; cần xác định cây và thời gian trước khi điều chỉnh. |
| Chat #19590 (bổ sung trực tiếp) | Sticker trong chat | Còn mở; chưa có bằng chứng tính năng hoàn thành. |
| Chat #15505 (admin) | Reply/trích dẫn một tin trong chat | Có lời nêu ý định, chưa có bằng chứng luồng reply được phát hành. |
| Chat #15487–15489 | Nền tảng cộng đồng khác | Chưa chọn nền tảng và phạm vi. |

## Những mục có báo cáo đã phát hành, cần tránh hứa lại hoặc đánh đồng

| Nguồn | Yêu cầu | Bằng chứng và giới hạn |
|---|---|---|
| #147 | Review/khách đe dọa | Báo cáo1.7.0 và phản hồi done trong `replied-170.json`; cần kiểm tra lại nếu có lỗi mới. |
| #149 | Thăng tiến nghề | Báo cáo1.7.0 ghi đã chỉnh; không nghĩa mọi nghề đã có màn quản lý riêng. |
| #150 | Máy pha nhanh2× | Báo cáo1.7.0; lò và4× có trong mã mới, chưa phát hành. |
| #151 | Hộ chiếu/ngày hội | Báo cáo1.7.0 và `tests/test_coffee_passport.py`; điều kiện có thể vẫn cần giải thích. |
| #152 | Bánh bao và váy/đầm | Báo cáo1.7.0; không thay cho nghề mới hay chọn size nhập hàng#138. |
| #154 | Tủ đồ mua rồi phải dễ tìm | Phản hồi1.7.0 và mã tủ đồ; chưa chứng minh album/ảnh mới đã có. |
| Chat #18252 | Homestay | Báo cáo1.7.0 ghi đã chỉnh luồng; khác nghề quản lý khách sạn#139. |
| #143,#148 | Phí nơi làm cũ và hoàn khoản cũ | Báo cáo1.7.0 ghi bỏ phí nơi làm khác/hoàn tiền. Không suy ra mọi sai lệch lương đã giải quyết. |
| #145 và các chat về bé/thú cưng | Con nuôi/vật nuôi cá nhân, đồ và chăm sóc | Báo cáo1.7.0 có; con chung là luồng mới tách riêng trong `game/family.py`, chưa phát hành. |
| Chat #18314 | Khách salon/nail | Có trong báo cáo1.7.0; cần xác minh khi phản ánh mới. |
| Chat #18347 | DIY | Có trong báo cáo1.7.0. |
| Chat #16756,#18307 | Thanh toán trực tiếp từ tài khoản | Có trong báo cáo1.7.0; giới hạn chuyển/rút mới là yêu cầu khác. |
| Chat #18291 | Đón thêm khách quầy không giới hạn tổng số | Có trong báo cáo1.7.0; không có nghĩa bỏ giờ mở cửa hoặc giới hạn khách đồng thời. |
| Chat #18327–18348 | Mời bạn bè đi làm ở quầy | Có trong báo cáo1.7.0; khác ghé làm khách#159. |
| Chat #17314 | Kết bạn từ chat | Có trong báo cáo1.7.0; chat sticker/reply vẫn là mục mới. |
| Chat #16389 | Ảnh trong DM/ô nhập lời mời | Có trong báo cáo1.7.0. |
| Chat #18365 | Cuộn giao diện nhà/tiệm | Có trong báo cáo1.7.0; review sheet mới cần kiểm tra riêng. |
| Chat #18363 | Ghi chú/hướng dẫn thú cưng | Có trong báo cáo1.7.0. |
| Chat #18393 | Máy bay chưa sử dụng | Có trong báo cáo1.7.0; không tự coi mô phỏng bay đã hoàn chỉnh. |
| Chat #15512 | Giáo viên | Có lời sửa ở1.5.4, chưa tái kiểm tra snapshot mới. |
| Chat #15501,#15529 | TT99, dấu âm/công thức kế toán | Có lời sửa ở1.5.3; không tự coi các câu kế toán khác cùng lỗi. |
| Chat #14935 | Nghề thu gom rác | Có lời sửa ở1.4.26. |
| Chat #15206 | Lag đo số đo quần áo | Có lời sửa ở1.4.21; nếu tái diễn cần đo trực tiếp. |
| #136 | Đi chung xe/chia sẻ phương tiện | Có source `game/coride.py`; snapshot không đủ xác nhận phiên bản production hiện tại. |
| #137; chat #15222,#16873 | Chọn/thuê nhà | Có source nhà ở; phần sống chung/tương tác chung vẫn chưa đủ. |
| Chat #14990,#15492,#15725 | Chuyển tiền cho bạn | Có source chuyển khoản; bỏ quota là sửa mới đã có kiểm tra riêng. |

## Câu hỏi hướng dẫn có thể giải quyết bằng luồng thật

Không đánh dấu là lỗi phần mềm nếu chưa có bằng chứng. Cần cung cấp nút đưa tới đúng màn và giải thích điều kiện, không chỉ trả lời chung chung.

| Chủ đề | Nguồn đại diện | Việc cần đối chiếu |
|---|---|---|
| Đổi nghề/đổi lại nơi cũ | #164; #14950 và các câu lặp | Nút mới cạnh tên tiệm và menu; bảo toàn tiến trình, xác nhận bỏ việc còn dở. |
| Khép ca/thoát ca khi hết ly | #14991,#14993 | Cách nhập ly, khép ca, hậu quả bỏ dở; không khóa người chơi ở bàn pha. |
| Văn phòng ba ngày/điều kiện mở nghề | #14946 và các câu lặp | Học/chứng chỉ, hợp đồng, ngày trong nghề và ngày sống là các điều kiện khác nhau. |
| Vào lễ cưới/thời điểm/đổi lịch | Các chat hỏi cưới trong snapshot | Đối chiếu giờ/địa điểm, mã tham gia và quyền đổi lịch theo đúng trường hợp. |
| Nhà, ngủ, mệt | Các chat hỏi nhà/ngủ trong snapshot | Xem chỗ nghỉ, giường và cách hồi sức thay vì mặc định thuê nhà là tự ngủ. |
| Đầu tư, vàng, gửi/rút/chuyển tiền | Các chat ngân hàng trong snapshot | Phân biệt ví cá nhân, quỹ nghề, số dư ngân hàng và quỹ chung; đối chiếu quota. |
| Avatar chat | #17311 | Đúng nơi thay diện mạo; phân biệt avatar chat và trang phục. |
| Đổi nhẫn | #15880 | Quyền chọn/thay nhẫn thực tế. |
| Sức chứa quầy | #16547,#16556 | Vị trí theo loại quầy/nâng cấp, khác với số khách phục vụ cả ngày. |
| Kho lạnh tiệm hoa | #16781,#16789 | Điều kiện mua/dùng và tác dụng giữ hàng. |
| Ô ăn quan | #14979 | Hướng dẫn đi lượt và cách kết thúc ván. |
| Chat tại hội chợ | #14949 | Source có kênh tại chỗ; đối chiếu nút mở và cờ tính năng live. |

Góp ý #115,#130,#146,#153 là lời khen/ghi nhận trong phần dữ liệu đã đọc, không tạo yêu cầu công việc mới. Không sao chép lời trò chuyện riêng không liên quan vào backlog.

## Bằng chứng kiểm tra của đợt hiện tại

`tests/test_feedback_workflows.py` và `.mjs` kiểm tra 4× với chất lượng shot/sữa, lò 2×/4× giữ nhịp qua lưu/tải và đổi lựa chọn, lò cũ vẫn 1×, vùng sữa/lò, size đơn lẻ/đơn gộp, giao thiếu chỉ nhập số thực nhận, size giả/xung đột bị từ chối và dữ liệu không đổi khi từ chối. Kiểm tra mới tái hiện rồi sửa nút gộp nhập thêm vào dòng đã chọn size. UI xác nhận bộ chọn gửi đúng payload, nút đổi nghề và lời giải thích người phụ xuất hiện.

Batch 290 kiểm tra café/quần áo/trà sữa nhanh/kho/đơn gộp/giờ giao/nhân viên/hướng dẫn có một lỗi độ dài câu hướng dẫn đổi nghề; đã sửa. Lượt chốt mới gồm 57 kiểm tra workflow/đơn gộp/review/hướng dẫn thành công, cùng 10/10 kiểm tra Node hành trình. `scripts/browser_feedback_workflows.py` bấm đổi nghề/chọn XL/đặt hàng qua Chromium ở 428×879 và 1280×900 bằng dữ liệu thử, không mở DB người chơi.

Kiểm tra nghiệp vụ kho không tái hiện việc hàng đặt sẽ tự lên kệ: source chủ ý yêu cầu mở thùng và đếm đúng. `v4Restock` đưa từ nút “Nhập hàng” tới thùng đã tới, đơn đang giao hoặc form đặt đúng món; dock có Kho khi nghề có kho. Sửa chọn size bổ sung lời chỉ dẫn ngay trên giá quần áo và các phiếu đơn. Không bỏ bước nhận hàng hoặc tự tạo hàng còn thiếu.

Các nhóm đã xác nhận: 174 kiểm tra đồ/nhà chung (gồm PostgreSQL dùng đồ chung); 62 kiểm tra hướng dẫn uy tín/lương, sự cố, bỏ dở và bản đồ; 18 kiểm tra gia đình sau bổ sung hồi quy thanh toán; nhóm rộng 203 kiểm tra gia đình/hôn nhân/nhà ở/ngân hàng/schema và lượt chốt 64 kiểm tra gia đình/chuyển tiền/hoạt động/hướng dẫn thành công. Kết quả tích hợp toàn bộ và phát hành cần ghi riêng; số kiểm tra riêng không được cộng thành một tổng vì có phần trùng.

Rà soát cuối phát hiện mã thao tác dài cùng phần đầu có thể bị cắt thành cùng mã thanh toán chăm bé. Đã đổi sang mã băm toàn bộ người thao tác và mã yêu cầu; kiểm tra hai mã dài cùng đầu xác nhận trả đủ 4 xu chăm bé + 18 xu quần áo, thử lại không thu lần hai. Kiểm tra chăm bé đồng thời chia tay xác nhận trừ đúng 4 xu, hai bản sao chăm riêng giữ kết quả và không kẹt khóa.

Giao diện gia đình đã được thử trong app thật: khoản chăm bé 4 xu trừ đúng một lần, chỉ số đổi 65→100, việc đã làm bị vô hiệu, tải lại còn kết quả; khối gia đình nằm trước hóa đơn cưới, màn 378px không tràn ngang. Những bằng chứng này xác nhận mã tại máy phát triển, không chứng minh bản dịch vụ đã được cập nhật.
