# Đánh giá trải nghiệm và cốt truyện Phố Có Chuyện

Ngày 04/10/2026 · mã nguồn 1.7.2 (`5a9b10e`) · đề xuất, chưa triển khai.

## Phạm vi và kết luận

Đã rà hệ thống hành trình, toàn bộ khai báo truyện nghề, điều kiện thăng tiến, hướng dẫn, điều hướng, các lớp kinh tế/rủi ro; đọc sâu vòng chơi trà sữa, homestay và kế toán. Đối chiếu báo cáo feedback 04/10 và bản chụp chat công khai đã thu thập trước đó; không lấy tên hoặc lời chat cá nhân vào báo cáo. Thử trình duyệt 390×844 trên dữ liệu local: tạo nhân vật, bản đồ/danh sách, hoàn thành ly trà đầu, menu, mở homestay và luồng nhận phòng ban đầu. Homestay được mở bằng sandbox để kiểm tra màn hình, không dùng sandbox để suy luận tốc độ mở khóa thực tế.

Đây là đánh giá mã nguồn và lượt chơi đại diện, không phải đã chơi hết mọi ca trong 41 nghề, hay nghiên cứu với người chơi thật. Chưa có số đo bỏ cuộc/giữ chân để kết luận mức độ phổ biến của từng vấn đề. Không sửa game hoặc dữ liệu production trong lượt đánh giá này.

**Ưu tiên: làm rõ việc cần làm, nối các hệ thống thành một cuộc sống có ý nghĩa, và cho lựa chọn để lại dấu vết.** Game đã có nhiều nội dung; mỗi lớp mới cần được giới thiệu vào đúng lúc và phục vụ một mục tiêu người chơi nhận ra.

## Những phần đã tốt cần giữ

- Có 41 tuyến truyện nghề, mỗi tuyến 5 đoạn: tổng 205 đoạn. Có NPC, lựa chọn, quan hệ và kỷ vật; không cần bắt đầu bằng viết lại toàn bộ.
- Ly trà đầu có nút làm từng bước, phiếu gọi món đánh dấu tiến độ, phản hồi giao thành công và lời cảm ơn/tip của Linh. Lượt thử hoàn thành đơn đầu đúng, quỹ tiệm từ 320 lên 365 xu trong khi ví giữ 60 xu. Đây đồng thời là nơi rất tốt để giải thích hai nguồn tiền.
- Có tự mở ca đầu, hạn chế popup trong ba khách đầu, hướng dẫn theo nghề, tìm kiếm trong hướng dẫn, đi/bay nhanh, nhân viên hỗ trợ và các cách xử lý nhẹ hơn.
- Có phối hợp thứ tự popup, bảo vệ người mới, phòng ngừa rủi ro, giới hạn thiệt hại và không trừ rủi ro theo thời gian offline. Không nên đề xuất lại những thứ đã có như tính năng hoàn toàn mới.
- Phí nghề vắng chủ, tiến độ huy hiệu hội chợ, hướng dẫn máy bay, cách thanh toán và tủ đồ đã được sửa/bổ sung ở đợt trước. Phản ánh cũ được dùng để hiểu kiểu khó khăn, không xem mặc nhiên là lỗi vẫn còn.

## Những điểm nên xử lý trước

| Mức | Bằng chứng hiện tại | Ảnh hưởng | Đề xuất |
|---|---|---|---|
| P1 | Guide trà sữa khuyên không chắc thì So phiếu; kiểm tra phát hiện sai lại cộng mistakes. UI có cảnh báo nhưng quy tắc vẫn ngược mục đích học. | Người mới ngại thử và ngại dùng trợ giúp. | Kiểm tra trước giao chỉ báo thiếu/sai, không cộng lỗi. Giữ hao nguyên liệu, thời gian và hậu quả giao sai. |
| P1 | Xét bậc đầu cần ít nhất 70% ngày tốt nhưng thanh thăng tiến không xuất đủ lý do này. Có thể hiện 5/5 ngày tốt trong khi 5/10 ngày làm vẫn chưa đủ. | Người chơi tưởng chức năng hỏng hoặc phải mò. | Hiện từng điều kiện chưa đủ và hành động tiếp theo: “Đủ 5 ngày tốt; tỷ lệ 50%, cần 70%”. Giải thích ngày tốt ngay tại đây. |
| P1 | Mục tiêu chương là dòng đếm thụ động; trên mobile nằm sau danh sách nghề và nhiều thẻ phụ. | Có nhiều nơi để đi nhưng chưa rõ đi đâu vì việc gì. | Đưa một mục tiêu đang theo lên đầu Hành trình; tiến độ, ý nghĩa/phần thưởng, nút đi đúng nơi. Người chơi được đổi/bỏ theo dõi mục tiêu. |
| P1 | Feedback/chat lặp lại câu hỏi đổi nghề, nghỉ nghề, đóng quỹ. FAQ đã có nhưng đường vào là Thêm → Hành trình. | Tên chức năng không khớp việc người chơi muốn làm. | Nút “Đổi nơi làm” cạnh tên nghề. Phân biệt đổi nơi, nghỉ việc nhân viên và tạm đóng tiệm; báo rõ trạng thái ca. |
| P1 | Giờ tiệm, ngày nghề, ngày sống, kỳ 5 ngày sống, kỳ thuế quầy 30 ngày sống, hạn mức 24 giờ thực cùng tồn tại. | Không đoán được một thao tác làm thời gian nào chạy. | Ghi đúng đơn vị ở nơi ra quyết định: “+20 phút trong game”, “canh giây thật”, “qua ngày sống khi khép ca”, “24 giờ thực”. |
| P1 | Ví, tài khoản, tiết kiệm, quỹ nghề, két quầy và quỹ chung có luật khác nhau. Quỹ nghề giữ lại 80 xu và hóa đơn trước khi rút. | Có tiền nhưng không hiểu tại sao không chi/rút được. | Cùng một mẫu: trả từ đâu → số trừ → còn bao nhiêu → thiếu vì sao. Link sang đúng nguồn có sẵn số tiền cần chuyển; không gộp tiền sở hữu khác nhau. |
| P2 | Có hơn 30 điểm đến dưới các nhóm Khu phố, Quan hệ, Ngân hàng & nhà, Chuyện của bạn, Của mình. Nhiều tên gần nghĩa. | Người chơi phải học sơ đồ menu trước khi chơi. | Tìm theo hành động “đổi nghề/rút tiền/thay đồ”; hàng nơi vừa dùng; đổi nhãn mơ hồ và phân biệt hàng xóm NPC với bạn chơi. Dùng hạ tầng tìm hướng dẫn đã có. |
| P2 | Hướng dẫn có thể bị đánh dấu đã học ngay khi xuất hiện; chỉ áp dụng một số save mới. | Người đọc chưa kịp, người quay lại đều dễ mất hướng. | Hoàn thành gợi ý khi đã làm được hành động; nút gợi ý lại; lúc quay lại tóm tắt ngắn “đang làm gì, việc tiếp theo”. |
| P2 | Hệ popup đã tránh chồng nhau nhưng quà/tin mới/x3/truyện/rủi ro vẫn có thể nối tiếp ở lúc nghỉ. | Chuyển cảnh dễ thành chuỗi đóng thông báo. | Gom tin thường vào một thẻ; chỉ tự mở việc cần quyết định. Giữ truyện ở nhịp nghỉ có chủ đích. Cần đo tần suất thực trước khi đổi toàn hệ. |
| P2 | Homestay có dọn phòng sáu bước, sổ an toàn, OTA, bếp, vườn, hao mòn; đã có phụ việc. | Thao tác từng có ý nghĩa thành việc lặp sau khi đã thành thạo. | Làm rõ giao việc cho người phụ; mở tùy chọn quy trình nhanh sau khi học. Giữ lựa chọn phòng, dị ứng, đồ thất lạc và ưu tiên khách. |
| P2 | Nhiều lớp rủi ro có giới hạn riêng, không có bằng chứng một ngân sách căng thẳng chung cho tất cả. Thiếu phí bảo dưỡng được miễn nhưng tăng nguy cơ hỏng về sau. | Người chơi có thể thấy bị phạt liên tục hoặc bị phạt dù vừa được báo miễn. | Điều phối sự cố nặng theo toàn nhân vật; nói trước hệ quả bảo dưỡng. Giữ các tình huống trộm/thuế/hack chủ game muốn, xen phản hồi tích cực và khoảng nghỉ. Chưa kết luận tần suất chồng thực tế. |
| P2 | Kế toán có chứng cứ/quy tắc/dấu quyết định và gợi ý, nhưng loại hồ sơ mở thêm theo ngày. | Quy trình có thể nhanh hơn tốc độ học. | Ví dụ làm mẫu đầu loại việc, bài tập lại riêng phần sai, giải thích “chứng cứ → quy tắc → kết luận” ngay sau kết quả. Không bắt học thêm khóa dài. |

Bằng chứng mã nguồn chính: [So phiếu](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/boba.py:1467), [hướng dẫn trà sữa](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/guide_content.py:125), [điều kiện thăng tiến](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/promotion.py:234), [dữ liệu tiến độ](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/promotion.py:655), [UI thăng tiến](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/public/js/v4/promo.js:46), [mục tiêu chương](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/public/js/v4/journey.js:157), [thứ tự Hành trình](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/public/js/v4/journey.js:231), [menu](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/public/js/app.js:261), [gợi ý lần đầu](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/public/js/tutorial/tips.js:186), [thứ tự popup](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/public/js/v4/break-gate.js:14), [phí bảo dưỡng](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/upkeep.py:179), [rủi ro](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/rui.py:71).

## Vì sao cốt truyện chưa tạo cảm giác cuốn

**Nhịp mở khóa và nhịp kể chuyện kéo về hai hướng.** Hành trình lần lượt yêu cầu làm ở 2, 3, 5 rồi 8 nơi. Một truyện nghề thường cần khoảng 9 ngày tại nghề và 22 việc để tới đoạn cuối. Người chơi đi theo gợi ý đổi nghề có thể gặp rất nhiều mở đầu nhưng ít đoạn kết.

**Thước đo “được tin cậy” còn chủ yếu là số lượng.** Chương yêu cầu số nơi làm, danh hiệu và cấp trưởng thành. Những chỉ số này đo hoạt động, nhưng chưa tự trả lời “ai đã tin mình và vì chuyện gì”.

**Nhiều lựa chọn đổi câu trả lời mà ít đổi phần sau.** Hệ hiện có hỗ trợ lưu lựa chọn và quan hệ; phần lớn nội dung vẫn đi tới cùng kết quả. Trong phạm vi truyện nghề đã rà, ví dụ callback theo lựa chọn rõ nhất là farm. Không cần tách vô số nhánh: một lời hứa được nhắc lại và một cảnh thay đổi cũng có giá trị.

**Con đường trưởng thành bắt buộc đi qua văn phòng.** Chương 5 yêu cầu được nhận việc văn phòng và làm đủ ngày. Người thích quán nhỏ hoặc phục vụ cộng đồng cũng phải rẽ sang lộ trình này để hoàn tất hành trình chung.

**Nhân vật tái xuất chưa tạo thành trí nhớ của cả khu phố.** Cô Ba, Bé Tí, Chú Tư xuất hiện ở nhiều nơi nhưng lựa chọn chủ yếu lưu theo truyện nghề. Cần thống nhất hồ sơ/vai trò nhân vật; một vài tên có nhiều vai trò nhưng chưa được giới thiệu rõ.

**Không biết khi nào có chuyện tiếp.** Thẻ truyện có tiến độ và hint văn chương, nhưng chưa chỉ rõ còn bao nhiêu ca/việc và tóm tắt đoạn trước. Kỷ vật đã có; nên làm chúng xuất hiện ở nơi dễ thấy và dẫn tới lần gặp tiếp theo.

Nguồn: [mục tiêu chương và cast](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/journey.py:76), [điều kiện truyện](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/career_stories.py:37), [xử lý lựa chọn](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/career_stories.py:1809), [dữ liệu thẻ truyện](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/game/career_stories.py:1862), [giao diện truyện](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/public/js/v4/stories.js:131).

## Hướng truyện đề xuất: “Một chỗ ở, một chỗ thuộc về”

Giữ chất đời thường của phố. Từ đầu gieo mục tiêu cùng làm một bữa cơm/đêm hội cuối hẻm. Mỗi nghề là một cách góp sức, còn chuyện của từng người là lý do quay lại. Truyện riêng Linh mùa thi, radio Ông Bảy, thư Bà Nguyệt đã có chất liệu để nối.

| Chặng | Việc người chơi làm | Điều khiến muốn chơi tiếp |
|---|---|---|
| Mới đến | Bà Tám chỉ chỗ ở; làm được một việc đầu tiên ở nghề tự chọn. | Gặp một người có điều đang lo; hẹn gặp lại, chưa giải hết ngay. |
| Quen mặt | Giúp Cô Ba/Bé Tí/Linh qua nghề mình thích. | NPC nhớ một hành động cụ thể, giới thiệu một người khác. |
| Có nghề | Góp món uống, hoa, sửa radio hoặc giao vật dụng cho đêm hội. | Một vật thay đổi trong cảnh và người mới tới vì việc mình làm. |
| Được tin | Mưa làm kế hoạch phải thay đổi; chọn phần mình nhận lo. | Người từng được giúp quay lại giúp mình. Lựa chọn đổi cách sự việc diễn ra. |
| Chọn đường riêng | Chọn gắn bó một nghề, kinh doanh nhỏ, phục vụ cộng đồng hoặc nhận cơ hội văn phòng. | Các đường đều tới trưởng thành, có thử thách/phần thưởng riêng. |
| Người của phố | Bữa cơm/đêm hội hiện ra từ những người và việc đã có trong save. | Lời phát biểu, vật trưng bày và quan hệ phản ánh lựa chọn; mở mùa truyện tiếp theo. |

Ví dụ nhỏ cho một nhánh: ở ca đầu Linh cần món nước trước buổi học; sau vài lần gặp người chơi biết chuyện ôn thi. Chọn giữ góc yên tĩnh hoặc giúp chuẩn bị một nhóm học. Đoạn sau Linh nhắc đúng lựa chọn; tới ngày hội cô ấy đem bản vẽ bảng hiệu hoặc rủ nhóm bạn tới phụ, tùy nhánh. Đây là đề xuất mới dựa trên Linh và “Trà Mùa Thi” hiện có, không phải mô tả tính năng đang chạy.

Mỗi tuyến nên có tối thiểu: một mong muốn, một trở ngại, một lựa chọn đáng cân nhắc, một lần được nhớ lại và một thay đổi thấy được. Có thể xem thêm thoại, bỏ qua hoặc đọc lại; không khóa nội dung vì người chơi không thích đọc dài.

## Một phiên chơi dễ hiểu hơn

1. Khi vào: hiện “Hôm nay mình đang giúp ai/lo việc gì”, cùng một nút tiếp tục. Người muốn đi tự do vẫn mở bản đồ như hiện tại.
2. Khi làm: một bước chính; lỗi nói rõ thiếu gì và cách sửa. Trợ giúp không trừ điểm trước khi giao sản phẩm.
3. Khi hoàn tất: phản hồi nghề, tiền đi vào nguồn nào, một câu từ người vừa được giúp.
4. Khi khép ca: tóm tắt ngắn tiền thực nhận/chi phí; tiến độ mục tiêu; điều đáng chờ ở lần tới. Sổ chi tiết nằm phía sau.
5. Khi nghỉ vài ngày rồi quay lại: tóm tắt một câu “Lần trước…” và việc có thể làm ngay. Không phát lại toàn bộ tour.

Mẫu thẻ đề xuất:

> **Linh đang đợi công thức Trà Mùa Thi**  
> Còn 1 ca ở Trà Mây để nghe chuyện tiếp.  
> **[Đến Trà Mây]** · Đổi mục tiêu · Xem chuyện trước

Các con số trong mẫu minh họa phải lấy từ điều kiện thật trên server; không đoán từ lời thoại.

## Cách trình bày nên giữ chất của game

Thế giới đặc trưng: hẻm nhà, quầy nghề, ca làm, sổ nợ, lời hẹn, mâm cơm hàng xóm, kỷ vật. Màu gợi từ nền kem, mái ngói, cửa xanh, trà nâu, giấy sổ và đèn lồng; giữ bộ theme/tokens hiện có.

Điểm nhận diện có thể là **một lời hẹn của hàng xóm xuất hiện xuyên suốt bản đồ → việc đang làm → cuối ca → thẻ truyện → vật trong nhà**. Thay danh sách tính năng ngang hàng bằng một lời hẹn đang theo; thay cảnh đọc thoại tách biệt bằng việc làm dẫn tới lời thoại; thay mưa badge bằng một thay đổi có người/vật chứng kiến. Không cần thay toàn bộ mỹ thuật hoặc xây thêm dashboard.

## Thứ tự làm đề nghị

**Đợt A — Làm rõ và bỏ những hình phạt gây hiểu nhầm.** So phiếu, lý do chưa thăng tiến, mục tiêu có đường dẫn, đổi nơi làm, nhãn thời gian/nguồn tiền. Giữ nguyên nội dung và tự do chọn nghề. Công sức nhỏ–vừa, tác động dự kiến cao; ưu tiên trước mở thêm nghề/rủi ro.

**Đợt B — Thử một đoạn trải nghiệm hoàn chỉnh.** Dùng trà sữa/Linh và sửa đồ/radio làm hai tuyến mẫu nối vào chuyện chung. Thêm tóm tắt, hẹn lần tiếp, một callback và một thay đổi trong cảnh. Kiểm tra cùng người chơi trước khi nhân lên 41 tuyến.

**Đợt C — Điều chỉnh hành trình dài.** Các lộ trình trưởng thành tương đương, dàn NPC dùng chung, đêm hội theo save, giảm thao tác đã thành thạo và điều phối áp lực chung. Công sức lớn hơn, cần giữ tương thích tiến độ của người đang chơi.

Không khuyến nghị ở bước đầu: thêm nhiều đồng tiền/thuế mới, thêm loạt popup hướng dẫn, ép hết tutorial mới được chơi, viết lại 205 đoạn cùng lúc, hoặc tăng thưởng để che việc không hiểu phải làm gì.

## Đo xem đề xuất có giúp thật không

Chưa có baseline nên các mốc dưới đây là **tiêu chí thử nghiệm đề xuất**, không phải số liệu hiện tại:

- Quan sát 5 người mới và một nhóm người quay lại, không nhắc đáp án. Cho làm đơn đầu, tìm nơi đổi nghề, giải thích tiền vừa kiếm nằm đâu, tìm điều kiện chương/thăng tiến và kể lại một NPC đang muốn gì.
- Mục tiêu ban đầu: ít nhất 4/5 người mới tự hoàn thành đơn đầu trong 5 phút; ít nhất 4/5 tự tìm “đổi nơi làm” trong 20 giây. Điều chỉnh sau baseline thực tế.
- Sau 15–20 phút, người chơi nói được “mình muốn chơi tiếp để làm gì” và nhớ một người/câu chuyện cụ thể, thay vì chỉ nhớ số xu.
- Theo dõi bước bỏ dở, dùng trợ giúp, lỗi lặp, mở rồi đóng menu, bắt đầu/hoàn thành từng đoạn truyện và quay lại ngày 1/ngày 7. Không suy ra nguyên nhân chỉ từ một chỉ số.
- Luôn kiểm tra người thích chơi tự do: có bỏ theo dõi nhiệm vụ, đi nhanh, bỏ thoại và đổi nghề mà vẫn chơi bình thường không.

## Nguồn đối chiếu và ảnh kiểm tra

[Xbox Accessibility Guideline 109](https://learn.microsoft.com/en-us/xbox/accessibility/xbox-accessibility-guidelines/109) khuyến nghị mục tiêu có thể xem lại, bước tiếp theo rõ, tóm tắt truyện và tutorial tương tác dùng lại được. [Progressive Disclosure — Nielsen Norman Group](https://www.nngroup.com/articles/progressive-disclosure/) là cơ sở cho việc để tác vụ chính hiện trước, mở phần nâng cao khi cần. Các nguồn này hỗ trợ nguyên tắc thiết kế; không chứng minh mức cải thiện cụ thể của Phố Có Chuyện.

Ảnh bản local: [bản đồ 390px](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/output/playwright/ux-audit-town.png), [đơn trà sữa đầu](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/output/playwright/ux-audit-first-job.png). Ảnh và SQLite thử nằm trong output, không đưa vào gói phát hành. Tài liệu phản hồi dùng đối chiếu: [đợt 04/10](D:/projects/Mot_ngay_lam_nghe/wt-feedback-0410/docs/FEEDBACK_2026-10-04.md).
