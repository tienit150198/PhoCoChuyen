"""Có gì mới: the release notes players see in a centred card after an update
(public/js/v4/whatsnew.js), and again from Cài đặt → Cách chơi → "Có gì mới".

=====================================================================
ADD AN ENTRY ONLY WHEN THE OWNER ASKS TO ANNOUNCE SOMETHING.
=====================================================================
A new entry pops up for every player on the server, so bug-fix and small releases ship quietly: bump
game.__version__, write the CHANGELOG, and leave this file alone (game.__version__ may be newer than the
latest entry; tests/test_whats_new.py only checks that the notes are never ahead of the game).
When the owner asks for a notice, add it at the top of ENTRIES (newest first):
- version: the release number ("0.9.2"), higher than the entry below it and at most game.__version__;
- date: "YYYY-MM-DD", the day it goes live;
- items: 1 to MAX_ITEMS short bullets in plain player Vietnamese (no developer notes,
  no file names), each a dict(emoji=..., text=...). Whole Vietnamese literals:
  the English pack (scripts/i18n_extract.py) picks them up from this file.
  Optional go=dict(action=..., data={...}) adds a "Thử ngay" button that
  presses the game's own control with that data-action; it only shows when
  such a control exists on the page, so a route that is not built yet is
  simply left out.
Then run `python -m game.whats_new` to rewrite public/js/v4/whatsnew-data.js
(the copy the browser loads lazily, so the first load does not grow).

Players who already saw a version keep it in settings.whatsNewSeen (the save,
so it follows the account). The notes are for returning players: a brand-new save starts
at "", and naming the character in the story intro marks the current notes as read
(journey._welcome_settings), so a new player never gets them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ENTRIES = (
    dict(version="1.6.5", date="2026-10-04", items=(
        dict(emoji="💼", text="Đổi nghề rồi thì nơi làm cũ không trừ tiền nữa (hết dòng “Nơi làm khác”); mở lại nơi tạm đóng cũng miễn phí."),
    )),
    dict(version="1.6.4", date="2026-10-04", items=(
        dict(emoji="📸", text="Buồng chụp ảnh mới: 49 dáng, 14 biểu cảm, 50 sticker kéo thả, xoay, phóng to thoải mái; chọn dáng là thấy ảnh liền!"),
    )),
    dict(version="1.6.3", date="2026-10-04", items=(
        dict(emoji="💑", text="Vợ chồng đi chung xe: ai chọn xe trước thì lái, người kia bấm “Ngồi sau” để cùng đi dạo, đi hội chợ!"),
    )),
    dict(version="1.6.2", date="2026-10-04", items=(
        dict(emoji="🛒", text="Quán đã tới giờ đóng cửa thì đi sang chỗ khác không bị phạt; việc dở vẫn giữ, quay lại khép ca."),
        dict(emoji="🏡", text="Mua thêm nhà không còn tự dọn đi; ở nhà chung với vợ/chồng thì có nút Về ở chung."),
        dict(emoji="📖", text="Hướng dẫn mới: chuyển khoản, bản đồ phố, đi xe, chụp ảnh hội chợ, tự lái và tự bay."),
    )),
    dict(version="1.6.1", date="2026-10-04", items=(
        dict(emoji="✈️", text="Phi công: tự cầm lái! Cất cánh, vòng tránh mây giông, giữ 2 trắng 2 đỏ rồi hạ cánh. Thích nhanh thì bấm ⏩ Bay nhanh."),
        dict(emoji="📸", text="Buồng chụp gọn hơn: chọn dáng, khung, nền, đạo cụ là thấy liền trong buồng, không phải cuộn tìm ảnh."),
        dict(emoji="💸", text="Chuyển khoản bạn bè dễ hơn: tài khoản chỉ cần chơi game đủ 1 ngày (đời thực)."),
    )),
    dict(version="1.6.0", date="2026-10-04", items=(
        dict(emoji="🗺️", text="Màn hình chính giờ là bản đồ phố: đi dạo rồi bước vào nơi làm việc. Muốn danh sách cũ thì bấm 📋 Danh sách."),
        dict(emoji="🛵", text="Có xe là chạy được quanh phố, hội chợ và đi dạo! Xe đỗ ngay cửa, bấm nút để đổi xe hoặc đi bộ."),
        dict(emoji="🛵", text="Giao hàng có chế độ Tự lái: tự chạy xe máy qua phố, dừng trước nhà có người vẫy tay. Muốn nhanh thì bấm ⏩ Đi nhanh."),
        dict(emoji="🚜", text="Nông trại: tự đi trong vườn góc nhìn thứ nhất hoặc thứ ba, thấy luống khát hay chín, chạy xe máy chở hàng tới khách!"),
        dict(emoji="🏪", text="Quầy của bạn: tự đặt menu, giá, tên quầy, màu mái, trang trí; không thuê ai cũng tự đứng bán được."),
        dict(emoji="📱", text="Bật Bán online: đóng gói đơn, tự chạy xe giao hoặc gọi shipper; mỗi ngày vài chuyện oái oăm vui vui."),
        dict(emoji="📸", text="Chụp ảnh hội chợ đẹp hơn: 30 dáng (có dáng cả nhóm), nút 🎲, 6 khung mới, chỉnh màu ảnh, thêm chữ và ngày lên ảnh."),
        dict(emoji="💸", text="Chuyển khoản bạn bè: mở Ngân hàng, chọn bạn, gửi xu kèm lời nhắn. Bạn ấy nhận ngay khi vào game."),
        dict(emoji="🛠️", text="Lớp học báo đúng chỗ sai; xin lỗi kèm hoàn tiền có thể khiến khách sửa sao; trông trẻ, giúp việc, nấu cơm hiện rõ tiền công."),
    )),
    dict(version="1.5.4", date="2026-10-03", items=(
        dict(emoji="📸", text="Buồng chụp hội chợ mở 24/24: tự nối lại khi rớt mạng, mã phòng giữ 2 phút để rủ bạn vào chụp chung."),
        dict(emoji="🧋", text="Quầy trà sữa: chọn nguyên liệu hiện ngay, không còn khựng. Lớp học: bấm trả lời học sinh không còn bị đứng."),
    )),
    dict(version="1.5.3", date="2026-10-03", items=(
        dict(emoji="🧮", text="Sổ kế toán và Học TT99: ô số giờ ghi được số âm, phép tính và đơn vị, như -500.000, 6+4 triệu, 1,5tr."),
        dict(emoji="💍", text="Ly hôn xong chỉ cần chờ 3 tiếng là cầu hôn lại được."),
    )),
    dict(version="1.5.2", date="2026-10-03", items=(
        dict(emoji="🛠️", text="Chạy ổn định hơn sau bản lớn, sửa vài lỗi nhỏ."),
    )),
    dict(version="1.5.1", date="2026-10-03", items=(
        dict(emoji="🎖️", text="Thăng tiến cho mọi nghề: làm tốt để lên chức, thêm thu nhập; từ bậc 3 mở 🧑‍💼 Ca quản lý, chia việc cho cả đội!"),
        dict(emoji="🏪", text="Quầy của bạn: mở xe đẩy, sạp chợ hay ki-ốt, tự đặt lương nhân viên, nhớ thu két mỗi ngày."),
        dict(emoji="💼", text="Làm thêm: nhận ca ở quầy của người chơi khác, làm đúng nghề mình giỏi, khép ca là nhận lương."),
        dict(emoji="🤝", text="Thuê người chơi: đăng ca cho người khác tới đứng quầy, lương giữ sẵn, trả đúng một lần."),
        dict(emoji="🧹", text="Nghề mới: Giúp việc theo giờ. Dọn từng phòng đúng khăn, đúng chai, từ trên xuống, giữ đồ quý cho khách, khách quen boa thêm."),
        dict(emoji="🍲", text="Nghề mới Nấu cơm gia đình: nghe chủ nhà dặn, đi chợ vừa tiền, nấu nóng hổi hợp cả nhà rồi ghi sổ chợ rõ ràng!"),
        dict(emoji="👶", text="Nghề mới: Bảo mẫu trông trẻ! Mỗi ngày một gia đình: đọc giấy dặn, cho bé ăn, ru ngủ, dỗ bé, bàn giao thật lòng."),
        dict(emoji="🛡️", text="Mua bảo hiểm, sắm két sắt để yên tâm trước chuyện bất ngờ. 💰 Tiệm vàng Kim Phát mở cửa: mua vàng, chờ giá lên!"),
        dict(emoji="✨", text="Màn hình gọn hơn, ít chữ hơn: thông báo ngắn, bấm vào để xem đủ; chi tiết gấp gọn trong “Xem thêm”."),
    )),
    dict(version="1.5.0", date="2026-10-03", items=(
        dict(emoji="🍜", text="Nghề mới Bán phở ở quán phở Cây Si: chần bánh, chan nước dùng nóng, nêm vừa miệng từng khách."),
        dict(emoji="🍚", text="Nghề mới Bán cơm ở Cơm tấm Dì Bảy: lên dĩa sườn bì chả nóng hổi, đông khách giờ trưa."),
        dict(emoji="📸", text="Nghề mới Chụp photobooth ở Tiệm ảnh Tách Tách. Hội chợ cũng có photobooth: chụp một mình, với người lạ hay rủ bạn!"),
        dict(emoji="🏠", text="Bước vào tận nhà, phòng trọ hay ký túc xá. Có tủ lạnh cất đồ ăn, đói thì lấy ra ăn."),
        dict(emoji="🧧", text="Đám cưới: gửi phong bì thoải mái, có mức 500 xu. Mạng chập chờn cũng không bao giờ bị trừ tiền hai lần."),
        dict(emoji="🌱", text="Nông trại có phân bón lá thúc: luống rau lớn nhanh hơn."),
        dict(emoji="🌅", text="Cuối ngày có mục Ngày mai để chuẩn bị trước; nhiều nghề dễ nhìn, dễ bấm hơn trên điện thoại."),
        dict(emoji="🔥", text="🔥 Ngày x3: tổng kết cuối ngày giờ hiện rõ dòng thưởng x3 (thưởng vẫn luôn vào ví khi khép ngày)."),
        dict(emoji="⭐", text="Đánh giá chỉ ghi “Đã trả lời” khi bạn trả lời thật. Nhận xét sau chuyến bay thì không cần trả lời."),
    )),
    dict(version="1.4.33", date="2026-10-03", items=(
        dict(emoji="🌐", text="Sửa lỗi game đứng ở màn hình tải trên Cốc Cốc và trình duyệt có bật chặn quảng cáo."),
    )),
    dict(version="1.4.32", date="2026-10-03", items=(
        dict(emoji="🧑‍🍳", text="Nhân viên giờ kiếm thêm cho tiệm: mỗi việc làm xong +3 xu (vui vẻ +4), cộng khi khép ca. Sự cố nhân viên cũng hiếm hơn hẳn."),
        dict(emoji="🏦", text="Menu “Tiền & nhà” đổi tên thành “Ngân hàng & nhà” cho dễ tìm."),
    )),
    dict(version="1.4.31", date="2026-10-03", items=(
        dict(emoji="⏱️", text="Canh mức (máy may, tắm thú, ép nắp…): bấm dừng ở đâu kim dừng đúng ở đó, cả khi máy yếu hay mạng chậm."),
        dict(emoji="🧑‍🍳", text="Nhân viên: thẻ ghi rõ hôm nay làm mấy việc, vì sao đang nghỉ; ai tạm dừng vì sự cố không bị tính lương."),
        dict(emoji="🏦", text="Tiền của bạn: thêm nút “Vào Ngân hàng” để mở ngân hàng nhanh hơn."),
        dict(emoji="💌", text="Bạn quen qua hẹn hò: sửa nút Hủy kết bạn, Chặn, Cầu hôn không bấm được."),
    )),
    dict(version="1.4.30", date="2026-10-03", items=(
        dict(emoji="💞", text="Nhà chung: vợ chồng ở cùng nhà giờ thấy cả đồ người kia bày trí. Món của ai người nấy dời."),
        dict(emoji="🧑‍🍳", text="Sổ tiệm: khi chưa cho nhân viên nghỉ được vì còn sự cố, game chỉ rõ từng bước để khép sự cố."),
    )),
    dict(version="1.4.29", date="2026-10-03", items=(
        dict(emoji="📒", text="Học kế toán: sửa lỗi bản lưu báo “Đáp án đã lưu chưa được chấm đúng”, làm không học, làm việc hay thi tiếp được."),
    )),
    dict(version="1.4.28", date="2026-10-03", items=(
        dict(emoji="🔥", text="🔥 Nghề x3: thưởng giờ tính đủ cả lương trong ngày và phần lời bạn đã rút về ví giữa ca."),
    )),
    dict(version="1.4.27", date="2026-10-03", items=(
        dict(emoji="📚", text="Học kế toán TT99: sửa các đề bị dính số tài khoản với số tiền (như phần 11 câu 2), đọc rõ ràng hơn."),
    )),
    dict(version="1.4.26", date="2026-10-03", items=(
        dict(emoji="🛒", text="Thu gom rác: dán phiếu không thu túi chưa phân loại xong vẫn đẩy xe tới nhà sau được, không còn bị kẹt giữa ngõ."),
    )),
    dict(version="1.4.25", date="2026-10-03", items=(
        dict(emoji="⚡", text="Chơi mượt hơn: mỗi lần chạm tải ít dữ liệu hơn khoảng 5 lần, quán trà sữa vẽ nhẹ hơn, đỡ giật trên máy yếu."),
    )),
    dict(version="1.4.24", date="2026-10-03", items=(
        dict(emoji="🗡️", text="Phi tiêu đổi thành Phóng dao: cắm đủ dao qua màn, dừng nhận thưởng hay liều chơi tiếp, lâu lâu có màn x2!", go=dict(action="fair")),
    )),
    dict(version="1.4.23", date="2026-10-03", items=(
        dict(emoji="📚", text="Học kế toán xong được giới thiệu việc làm: thi đạt mới vào làm, kiểm tra 3 câu đầu ca, lương kế toán x3, ngày lễ x5.", go=dict(action="accountingSchool")),
        dict(emoji="📦", text="Kho gọn hơn: tổng tiền ngay dưới số lượng, giữ ngón tay trên thùng hàng để đếm nhanh. Tổng kết ngày mở đầu bằng “Ngày mai”."),
        dict(emoji="🪟", text="Mỗi lúc chỉ một thẻ thông báo, không còn chồng lên tổng kết ngày hay khách đang chờ. Dòng ví & quỹ tiệm không che nút nữa."),
        dict(emoji="👆", text="Nút chính dưới màn hình luôn chỉ rõ chỗ cần chạm (“👆 Chạm: Ly size M”); thông báo hiện ngay trên nút, không che khách."),
    )),
    dict(version="1.4.22", date="2026-10-03", items=(
        dict(emoji="📱", text="Thanh dưới luôn đủ 5 nút to: Khách, Làm, Kho, Sổ tiệm, Thêm. Kho báo hàng sắp hết, thanh trên gọn hơn trên điện thoại nhỏ."),
        dict(emoji="🧭", text="Hành trình: nút Tiếp tục nằm ngay đầu, nơi làm việc xếp gọn hai cột. Chuẩn bị gọn lại, Kho lên đầu."),
        dict(emoji="👫", text="Hội chợ: bạn chơi trò nào thì người khác thấy bạn đứng ngay gian đó, kèm biểu tượng trò nhỏ.", go=dict(action="fair")),
    )),
    dict(version="1.4.21", date="2026-10-03", items=(
        dict(emoji="⏱️", text="Bấm dừng (ép nắp trà sữa, xả nước, sấy, chiết cà phê, may, vớt mì…) là thanh đứng ngay chỗ bạn thấy, mạng chậm cũng chấm đúng."),
    )),
    dict(version="1.4.20", date="2026-10-03", items=(
        dict(emoji="🔥", text="Nghề x3 mỗi tuần: mỗi ngày vài nghề được lời x3 khi khép ca, tuần nào nghề nào cũng có một ngày. Lịch báo ngay đầu tuần.", go=dict(action="x3Week")),
        dict(emoji="🎟️", text="Dì Hai bán vé số cào ở hội chợ: vé 2–20 xu, tự tay cào lớp bạc, ba ô giống nhau là trúng, có vé trúng gấp 50 lần.", go=dict(action="fair")),
        dict(emoji="🏮", text="Thêm 35 món trang trí nhà đậm chất Việt: sập gỗ, đồng hồ quả lắc, đàn bầu, xe đạp… cùng kệ Trung thu & Tết và 5 bộ mới.", go=dict(action="house")),
        dict(emoji="💬", text="Tin nhắn: giữ một tin để xóa phía mình hoặc thu hồi trong 24 giờ, chọn xóa nhiều cuộc trò chuyện, xem Đã chặn và bỏ chặn.", go=dict(action="liveChat")),
        dict(emoji="🔔", text="Chạm vào thông báo là tắt ngay, không còn che màn chơi."),
        dict(emoji="🍡", text="Hàng ăn vặt hội chợ: no bụng rồi vẫn mua được kẹo bông, nước mía, chè… ăn cho vui, chỉ cần ví đủ xu.", go=dict(action="fair")),
        dict(emoji="🗂️", text="Lọc CV: tin ứng viên rút hồ sơ đến sau khi đã xếp thẻ thì thẻ tự quay về chưa xếp, ghi chú cuộc gọi in ngay trên thẻ."),
    )),
    dict(version="1.4.19", date="2026-10-03", items=(
        dict(emoji="🏆", text="Bảng vàng hội chợ giờ xếp theo tiền lời: ai thắng nhiều xu nhất ở hội chợ đứng top. Quà tặng và tiền vay không tính.", go=dict(action="fair")),
        dict(emoji="👫", text="Vào bãi hội là thấy người chơi khác đang đi dạo quanh các gian, cùng đi hội cho vui.", go=dict(action="fair")),
    )),
    dict(version="1.4.18", date="2026-10-03", items=(
        dict(emoji="🍡", text="Hội chợ có hàng ăn vặt: cô Út bán kẹo bông, bắp nướng, bánh tráng nướng; chú Năm có nước mía, chè, tàu hũ. Ăn no, tỉnh hẳn.", go=dict(action="fair")),
    )),
    dict(version="1.4.17", date="2026-10-03", items=(
        dict(emoji="🦀", text="Bầu cua: chú Tám lắc đủ 5 giây mới mở bát. Lắc dồn mãi một chiếu thì vận nguội nhanh lắm nha.", go=dict(action="fair")),
        dict(emoji="🎱", text="Gánh lô tô cân lại hũ: Kinh ăn khoảng 2,2 lần tiền tờ, thắng thua sát nút như các gian khác.", go=dict(action="fair")),
        dict(emoji="💰", text="Dòng “Hôm nay kiếm” trên đầu hội chợ giờ cộng đủ xu thắng thua ở mọi gian.", go=dict(action="fair")),
    )),
    dict(version="1.4.16", date="2026-10-03", items=(
        dict(emoji="🎲", text="Hội chợ cân lại vận, thắng thua sát nút hơn. Chơi một trò liên tục quá lâu thì vận nguội dần, đổi trò hay nghỉ chút nha.", go=dict(action="fair")),
        dict(emoji="💍", text="Ném vòng giờ chỉ để kiếm xu vui, không tính điểm Bảng vàng nữa.", go=dict(action="fair")),
    )),
    dict(version="1.4.15", date="2026-10-03", items=(
        dict(emoji="📚", text="Học kế toán theo TT99: 84 bài, thi lấy chứng nhận, tập làm sổ công ty Mây Tre Xanh, có gợi ý từng bước và tra cứu tài khoản."),
        dict(emoji="🧾", text="Hồ sơ lương ở văn phòng gọn, dễ nhìn hơn: mỗi ô một thẻ, kết quả một thẻ, sai thì có gợi ý kỹ theo đúng số bạn nhập."),
        dict(emoji="🛕", text="Ở chùa, khách thập phương và thầy trụ trì nói bằng giọng nhà chùa, nhẹ nhàng, không giống lời ngoài phố."),
        dict(emoji="🛁", text="Nhà nào cũng có nhà tắm, biệt thự có hồ bơi. Thêm 15 món đồ nhà tắm, hồ bơi và nút thư giãn mỗi ngày.", go=dict(action="house")),
    )),
    dict(version="1.4.14", date="2026-10-03", items=(
        dict(emoji="🏮", text="Hội chợ thành bãi hội thật: đi dạo dưới dây đèn lồng, tới gánh lô tô, lều bầu cua, sạp phi tiêu… bấm vào là chơi.", go=dict(action="fair")),
        dict(emoji="🎲", text="Hội chợ hên xui hơn: thắng thua tùy vận. Phi tiêu khó hơn, tâm ngắm chạy nhanh, gió hội chợ lộng hơn.", go=dict(action="fair")),
        dict(emoji="💰", text="Mỗi gian hội chợ có dòng “Hôm nay kiếm ở…” để xem xu thắng thua. Kinh lô tô thắng giờ báo luôn điểm hội chợ.", go=dict(action="fair")),
    )),
    dict(version="1.4.13", date="2026-10-03", items=(
        dict(emoji="🎁", text="Vào hội chợ là được ban tổ chức tặng ngay 500 xu tiền vốn chơi hội!", go=dict(action="fair")),
        dict(emoji="💸", text="Thiếu vốn? Bà Sáu ở cổng hội cho vay nóng 50–500 xu, lãi 20%, trả lúc nào cũng được, hội tàn thì thu.", go=dict(action="fair")),
        dict(emoji="🎯", text="Trò mới ở hội chợ: Phóng phi tiêu với anh Sáu. Cắm vòng màu là ăn 1 trả 1, cắm ngay hồng tâm còn có danh hiệu.", go=dict(action="fair")),
        dict(emoji="🎪", text="Hội chợ không còn giới hạn mỗi ngày: lượt chơi, tiền cược, xu kiếm được, điểm đều thoải mái. Lắc nhanh hơn.", go=dict(action="fair")),
        dict(emoji="🦀", text="Bầu cua, chiếu trong ăn 1:1 và dễ thắng hơn hẳn. Công an ít ghé hơn, phạt nhẹ hơn. Ném vòng: một chai ăn nhiều vòng.", go=dict(action="fair")),
        dict(emoji="🎱", text="Lô tô: số vừa gọi sáng lên trên tờ dò của bạn, kinh hụt thoải mái. Ô ăn quan: chọn ô rồi vẫn đổi được.", go=dict(action="fair")),
    )),
    dict(version="1.4.12", date="2026-10-03", items=(
        dict(emoji="🏮", text="Hội chợ mượt hơn: bấm không nhảy trang, lắc nhanh hơn. Chiếu trong có “mấy ván gần đây”, ô ăn quan đã bốc thì không chọn lại.", go=dict(action="fair")),
    )),
    dict(version="1.4.11", date="2026-10-03", items=(
        dict(emoji="🏮", text="Hội chợ đã mở! Bầu cua chơi xong có nút “Lắc tiếp” ngay dưới kết quả, bấm đặt không còn bị nhảy lên đầu trang.", go=dict(action="fair")),
    )),
    dict(version="1.4.10", date="2026-10-02", items=(
        dict(emoji="🛕", text="Vào chùa Gió Lành: đi dạo sân chùa, chánh điện, nhà ăn. Đi tới lư hương, gác chuông, hồ sen là làm được việc ngay tại đó.", go=dict(action="jrView", data={"view": "life"})),
        dict(emoji="🙏", text="Quỳ trước chánh điện tự chọn lời khấn, ngồi gõ mõ tụng kinh cùng Thầy Huệ Minh. Có tiếng chuông, tiếng mõ, tiếng tụng thật."),
    )),
    dict(version="1.4.9", date="2026-10-02", items=(
        dict(emoji="💍", text="Cầu hôn bị từ chối thì chỉ cần chờ 3 tiếng là được ngỏ lời lại, không còn phải đợi 3 ngày."),
        dict(emoji="📦", text="Sửa lỗi nút “Gộp món thiếu vào một đơn” ở tiệm nail và các tiệm: đơn gợi ý giờ vừa 8 món và vừa tiền trong quỹ."),
    )),
    dict(version="1.4.8", date="2026-10-02", items=(
        dict(emoji="🏘️", text="Sở hữu tới 4 căn nhà: mua thêm, cho người thuê lấy tiền nhà mỗi tháng, hoặc dọn qua căn khác ở (20 xu thuê xe tải).", go=dict(action="house")),
        dict(emoji="🛫", text="Nơi làm việc có cả bên trong: sân bay có sảnh ga, cổng ra tàu, khoang khách, buồng lái; tiệm có bếp sau, kho, phòng gội."),
        dict(emoji="🚪", text="Đi tới cửa hoặc bấm tên khu để qua phòng khác. Có việc mới là bạn được đưa tới đúng chỗ làm."),
    )),
    dict(version="1.4.7", date="2026-10-02", items=(
        dict(emoji="💅", text="Nghề mới: Tiệm nail của chị Diệp. Sơn gel, úp móng, đính đá, dưỡng da tay, giữ dụng cụ sạch sẽ để khách yên tâm."),
        dict(emoji="🛕", text="Làm công quả ở chùa Gió Lành, ngôi chùa lâu năm của phố: quét sân, thắp đèn, đón khách thập phương. Không xin tiền ai."),
        dict(emoji="🙏", text="Đi chùa: thắp hương, nghe chuông, viết lời nguyện, phụ quét sân. Miễn phí, mỗi ngày tối đa 3 việc, tinh thần nhẹ nhõm hẳn.", go=dict(action="jrView", data={"view": "life"})),
        dict(emoji="🎱", text="Gánh lô tô ở hội chợ: cô Bảy hô thơ, có nhạc, có người múa. Mua tấm, dò số, hô Kinh! Đặt ít xu cho vui thôi nhé.", go=dict(action="fair")),
        dict(emoji="🧑‍🎤", text="Ảnh đại diện chat: chọn gương mặt, tóc, biểu cảm; áo quần lấy luôn từ Tủ đồ. Hiện cạnh tin nhắn của bạn.", go=dict(action="jrAvatar")),
    )),
    dict(version="1.4.6", date="2026-10-02", items=(
        dict(emoji="🚗", text="Xe & phương tiện: mua xe đạp, xe máy, ô tô, du thuyền, cả máy bay riêng. Trả đủ một lần, chọn màu sơn, đặt biển tên.", go=dict(action="garage")),
        dict(emoji="🛥️", text="Mỗi ngày được lái xe đi chơi một chuyến: ra biển, ngắm hoàng hôn, bay ngắm phố. Tinh thần lên, chỉ tốn ít tiền xăng."),
    )),
    dict(version="1.4.5", date="2026-10-02", items=(
        dict(emoji="💼", text="Thuế & kế toán: mỗi hồ sơ thưởng thêm 2 xu, làm sai nhiều vẫn được ít nhất 14 xu (trước là 10)."),
        dict(emoji="🎓", text="Đang thử việc nghề văn phòng: sai một bước chỉ trừ 2 xu, luôn giữ nửa thưởng, nộp trễ trừ nhẹ hơn, sửa sai đỡ tốn giờ."),
    )),
    dict(version="1.4.4", date="2026-10-02", items=(
        dict(emoji="💡", text="Nút nào chưa làm được giờ mờ đi và ghi lý do (thiếu xu, kho đầy, chưa mở ca…), không còn bấm hoài bị báo lỗi."),
        dict(emoji="❓", text="Hỏi nhanh: 15 câu hay hỏi (đổi nghề, nghỉ việc, rút tiền, dự đám cưới…) ở cuối menu và trong Cài đặt."),
        dict(emoji="🧾", text="Sổ thu chi có nút Thanh toán tất cả: trả mọi hóa đơn một lần, khoản quá hạn trước, không bao giờ âm quỹ."),
        dict(emoji="📐", text="Thuế và kế toán: dòng gợi ý số lấy từ đâu dưới mỗi ô, điền sai thì ô lệch được đánh dấu. Bạn vẫn tự tính nhé."),
        dict(emoji="🎨", text="Salon có Bảng màu tra level và tuýp nhuộm; tạp hóa, trà sữa, mẹ & bé, Sớm Mai chỉ rõ bước tiếp theo hơn."),
    )),
    dict(version="1.4.3", date="2026-10-02", items=(
        dict(emoji="🍢", text="Ăn thêm: đói hay buồn ngủ thì mua bánh bao, xôi, phở hay ly cà phê lúc nào cũng được trong ngày làm, trả bằng ví.", go=dict(action="jrView", data={"view": "life"})),
        dict(emoji="☕", text="Khi bụng đói, ô việc đang làm hiện sẵn món ăn thêm; trang Đời thường lúc nào cũng có."),
    )),
    dict(version="1.4.2", date="2026-10-02", items=(
        dict(emoji="🧋", text="Quán trà sữa: sửa lỗi màn Kho & đặt hàng, Bảng giá đôi khi báo lỗi khi vừa mở."),
    )),
    dict(version="1.4.1", date="2026-10-02", items=(
        dict(emoji="🍚", text="Thêm thanh No bụng và 😴 Tỉnh táo cạnh Tinh thần: trưa chọn món một chạm, tối chọn bữa và giờ đi ngủ."),
        dict(emoji="🌙", text="Cơm nhà luôn miễn phí (đã tính trong tiền cơm nước). Bận quá thì bấm “Như mọi khi” là xong."),
    )),
    dict(version="1.4.0", date="2026-10-02", items=(
        dict(emoji="🪴", text="Bày trí tự do: giữ món đồ kéo đi đâu cũng được, đồ nhỏ đứng trên bàn, kệ, gối và đi theo khi dời.", go=dict(action="house")),
        dict(emoji="🖼️", text="Giấy dán tường, sàn nhà, ga giường mới: nhiều kiểu miễn phí, mua một lần dùng cho mọi phòng."),
        dict(emoji="🐈", text="Nắng đổi theo giờ, đèn sáng về đêm; Mochi đi dạo, ngủ trưa, phòng thật ấm cúng thì bé mèo Bơ dọn tới."),
    )),
    dict(version="1.3.4", date="2026-10-02", items=(
        dict(emoji="🎓", text="Thi đạt chứng chỉ là nhận Giấy chứng nhận thật: xem, tải ảnh về máy và chụp ảnh lưu niệm cùng nhân vật."),
        dict(emoji="📸", text="Chứng chỉ đã thi đạt từ trước cũng có giấy: mở ở Trung tâm chứng chỉ hoặc chạm huy hiệu trong hồ sơ."),
    )),
    dict(version="1.3.3", date="2026-10-02", items=(
        dict(emoji="🎨", text="Bảng màu của bạn: mở một màu một lần là dùng cho áo, quần, giày dép, phụ kiện và cả đồ trong nhà, ký túc xá.", go=dict(action="jrWardrobe")),
        dict(emoji="💝", text="Ai đã mở màu cho phụ kiện ở bản trước thì màu đó giờ dùng được cho mọi món, không mất xu nào."),
    )),
    dict(version="1.3.2", date="2026-10-02", items=(
        dict(emoji="🪴", text="Bày trí phòng: chọn từng món trong túi, chạm hoặc kéo vào chỗ trống. Dời, lật, thu hồi, hoàn tác thoải mái.", go=dict(action="house")),
        dict(emoji="🏠", text="Gác Bà Tám, phòng trọ, góc giường ký túc xá đều bày trí được. Dọn đi đâu, đồ tự gói vào túi theo bạn."),
        dict(emoji="✨", text="65 món đồ xinh, 9 bộ góc (học tập, góc xanh, góc chill…), mèo Mochi chấm điểm Ấm cúng, hàng xóm ghé khen phòng."),
        dict(emoji="📸", text="Chụp căn phòng thành ảnh polaroid, lưu vào album hoặc tải về máy."),
    )),
    dict(version="1.3.1", date="2026-10-02", items=(
        dict(emoji="🎨", text="Phụ kiện đổi màu được rồi! Thử màu ngay trên gương, mở khóa từ 20 xu, kèm gợi ý màu hợp với màu tóc của bạn.", go=dict(action="jrWardrobe")),
    )),
    dict(version="1.3.0", date="2026-10-02", items=(
        dict(emoji="🏮", text="Hội chợ dân gian mở 5 ngày từ 03/10: chơi ô ăn quan với Bé Bi, Ông Hai, ném vòng cổ chai kiếm xu, không cần đặt cược!", go=dict(action="fair")),
        dict(emoji="👑", text="Thử vận may với bầu cua, lô tô, chiếu trong (coi chừng công an phường!). Hội tàn, Top 1 Bảng vàng thành Vua trò chơi."),
        dict(emoji="🍨", text="Nghề mới: bán kem ở Tiệm kem Góc Phượng, cô Hiền kèm ba khách đầu. Múc đủ ký, đậy nắp tủ kẻo kem chảy."),
        dict(emoji="🥥", text="Tự nấu kem dừa, bơ, khoai môn theo sổ cô Hiền: đong, nấu, ngâm đá, đánh kem, mai bán thêm 1 xu. Có Chứng chỉ làm kem."),
        dict(emoji="🛏️", text="Ký túc xá Hẻm 7: giường tầng 7 xu/ngày, ở chung với ba bạn cùng phòng, mỗi người một chuyện.", go=dict(action="house")),
        dict(emoji="🔕", text="Tắt hoặc bật thông báo cho từng nhóm chat, tin nhắn riêng. Góc hẹn hò cho biết ai đang chờ, có nút 📣 Rủ mọi người.", go=dict(action="liveChat")),
        dict(emoji="🔔", text="Tiền về là nghe “ting ting” như app ngân hàng, kèm giọng đọc số tiền. Tắt được trong Cài đặt → Âm thanh."),
        dict(emoji="🧾", text="Bàn tính lương: ô sai được tô đỏ, chạm vào để xem số đúng, cách tính từng bước và quy định áp dụng."),
        dict(emoji="📅", text="Ô ngày giờ ở văn phòng tự thêm dấu / và : khi gõ bằng bàn phím số, hoặc bấm 📅 để chọn ngày trên lịch."),
        dict(emoji="💇", text="Tiệm tóc: khách chê “còn dài” thì luôn cắt thêm được, kể cả khi đã tỉa tầng. Hết cảnh soi gương mãi không chốt được."),
        dict(emoji="🦁", text="Đoàn lân mới về tiệc cưới: đầu lân to rực rỡ, chớp mắt, há miệng, chồm lên đớp lì xì theo tiếng trống.", go=dict(action="liveWed")),
        dict(emoji="🪩", text="Sân khấu cưới có quả cầu disco, đèn màu quét theo nhạc và bốn cái loa góc sân rung theo từng nhịp."),
        dict(emoji="🎧", text="Nhạc cưới mới sôi động, chú rể chọn nhạc cho cả tiệc: EDM, remix, Latin, funk, nhạc chậm. Chú rể vắng thì cô dâu chọn."),
        dict(emoji="🍲", text="Chạm vào bàn cỗ để gắp món: mỗi món thêm tinh thần (tối đa 3 lần). Cụng ly bia “Dzô!” thì say nhẹ."),
        dict(emoji="💃", text="Bước lên sân khấu là nhảy theo nhạc, bấm 💃 Nhảy để xoay một vòng cho cả tiệc cùng xem."),
        dict(emoji="💐", text="Cuối tiệc cô dâu chú rể tung hoa: ai bắt được nhận 20 xu. Có pháo giấy lúc vào, pháo hoa lúc tiệc tàn."),
        dict(emoji="👰", text="Bảng tên cô dâu chú rể to và nổi bật hơn, nhìn là thấy ngay nhân vật chính của buổi tiệc."),
    )),
    dict(version="1.2.3", date="2026-10-02", items=(
        dict(emoji="💍", text="Sửa lỗi mục Kế hoạch cưới không mở được khi kế hoạch của hai bạn đã gửi hoặc đã chốt.", go=dict(action="marriage")),
    )),
    dict(version="1.2.2", date="2026-10-02", items=(
        dict(emoji="😍", text="Thả cảm xúc trong chat: nhấn giữ một tin nhắn rồi chọn ❤️ 😂 😮 😢 👍 🔥. Bấm lại để bỏ, chọn cái khác để đổi.", go=dict(action="liveChat")),
        dict(emoji="💬", text="Dưới mỗi tin hiện số cảm xúc của mọi người; bấm vào một cảm xúc là thả theo ngay."),
        dict(emoji="🌞", text="Thẻ Nhiệm vụ hôm nay ghi rõ cách tính từng việc; nhớ bấm Nhận quà trước khi đóng ca."),
    )),
    dict(version="1.2.0", date="2026-10-01", items=(
        dict(emoji="🏠", text="Vào nhà của mình: xem từng phòng, sửa nhà và trang trí với 27 món đồ. Nhà càng ấm cúng, sáng dậy càng vui.", go=dict(action="house")),
        dict(emoji="🧹", text="Nghề mới Nội trợ (mở từ chương 2): giúp việc nhà chị Thảo, đi chợ mặc cả, nấu cơm hợp khẩu vị, giặt giũ, chăm bà, đưa đón bé Su."),
        dict(emoji="💼", text="Ba vị trí văn phòng mới ở Công ty Cánh Diều (mở từ chương 5): Hành chính – Nhân sự, Thư ký giám đốc, IT văn phòng."),
        dict(emoji="📋", text="Nghề kế toán có thêm tình huống mới: sếp xin ứng quỹ, công nhân xin ứng lương, họp chốt số lúc nửa đêm…"),
    )),
    dict(version="1.1.4", date="2026-10-01", items=(
        dict(emoji="⏱️", text="Ở trong tiệc cưới từ 2 phút trở lên mới được tính là đi ăn cưới: tính vào bảng Khách mời của tuần và tiền mừng của cô dâu chú rể."),
        dict(emoji="🛒", text="Sửa lỗi đơn sỉ của bà Sáu bị treo khi bớt giá kịch khung ngay lần đầu: đơn đang kẹt tự được chốt khi vào game."),
    )),
    dict(version="1.1.3", date="2026-10-01", items=(
        dict(emoji="💍", text="Tiệc cưới mới: 10 phút rộn ràng có MC, cỗ, múa lân, đèn nháy, nhạc cưới, hàng xóm và các bạn nhỏ vào chung vui.", go=dict(action="liveWed")),
        dict(emoji="💰", text="Có mặt trong tiệc cưới được 20 xu mỗi phút. Mỗi khách đến dự, cô dâu chú rể được 15 xu."),
        dict(emoji="✅", text="Vào dự là có lộc ngay từ phút đầu, không phải chờ 5 phút."),
        dict(emoji="🧧", text="Bỏ phong bì mừng cô dâu chú rể ngay trong tiệc, kèm lời chúc cho cả phòng cùng thấy."),
        dict(emoji="📜", text="Bảng Lời chúc trong tiệc cưới: lời mọi người nói được giữ lại, không trôi mất nữa."),
        dict(emoji="🎉", text="Cặp nào đã cưới cũng tổ chức được tiệc: chọn ngày giờ trong Hôn nhân, mời khách miễn phí.", go=dict(action="marriage")),
    )),
    dict(version="1.1.0", date="2026-10-01", items=(
        dict(emoji="💍", text="Đám cưới trực tiếp: chọn ngày giờ thật, cả phố vào dự, khách nhận +15 xu mỗi 5 phút.", go=dict(action="liveWed")),
        dict(emoji="🎂", text="Kỷ niệm 100 ngày, 1 năm, 500 ngày, 1000 ngày cưới: có quà và danh hiệu riêng."),
        dict(emoji="🏆", text="Khách mời của tuần: ai dự nhiều đám cưới nhất nhận danh hiệu và xu."),
    )),
    dict(version="1.0.3", date="2026-10-01", items=(
        dict(emoji="💕", text="Góc hẹn hò: ngồi ghế đá chờ ghép đôi, hẹn 5 phút, cùng thả tim là thành “Đang tìm hiểu”.", go=dict(action="liveDate")),
    )),
    dict(version="1.0.0", date="2026-10-01", items=(
        dict(emoji="💬", text="Chat đã có! Nhắn riêng với bạn bè, hoặc lập nhóm chat tới 20 người.", go=dict(action="liveChat")),
        dict(emoji="🌏", text="Kênh Cả phố: trò chuyện với mọi người đang online, mỗi người 1 tin mỗi 10 giây."),
        dict(emoji="🟢", text="Chấm xanh cho biết bạn bè nào đang online. Muốn ẩn thì tắt trong Cài đặt."),
        dict(emoji="🚶", text="Đi dạo khu phố: Bờ hồ, Chợ đêm, Công viên, Phố đi bộ. Gặp người thật, ngồi bàn tám chuyện, nhặt lì xì.", go=dict(action="liveWalk")),
    )),
    dict(version="0.9.15", date="2026-10-01", items=(
        dict(emoji="🍉", text="Nghề mới: Bán trái cây ở sạp Dì Tư: lựa trái chín, cân đúng từng lạng, trả giá khéo."),
        dict(emoji="🗑️", text="Nghề mới: Thu gom rác ca tối: phân loại đúng ngăn, tách đồ nguy hại, giữ ngõ sạch."),
        dict(emoji="🪠", text="Nghề mới: Thông ống cống với chú Hai: tìm đúng chỗ tắc, báo giá trước khi làm."),
        dict(emoji="✈️", text="Nghề mới: Phi công và Tiếp viên hàng không của Hãng bay Cánh Cò, bay chặng ngắn ra đảo."),
    )),
    dict(version="0.9.13", date="2026-10-01", items=(
        dict(emoji="🏰", text="Mua nhà: thêm biệt thự và 4 loại căn hộ (studio, 1 phòng ngủ, 2 phòng ngủ, penthouse).", go=dict(action="house")),
        dict(emoji="💰", text="Bấm vào tiền trên cùng để xem hết: ví, quỹ từng nơi làm, ngân hàng, nhà.", go=dict(action="money")),
    )),
    dict(version="0.9.10", date="2026-09-30", items=(
        dict(emoji="✅", text="Nâng cấp hạ tầng đã xong! Game đã chạy trên máy chủ mới, mạnh và nhanh hơn."),
        dict(emoji="🎮", text="Tiền, nhà, đồ và tiến độ của bạn vẫn giữ nguyên. Chúc mọi người chơi vui, enjoy nhé!"),
        dict(emoji="🥺", text="Ai mà bảo lag nữa là buồn luôn đó."),
    )),
    dict(version="0.9.9", date="2026-09-30", items=(
        dict(emoji="🔧", text="Bảo trì ngắn từ 21:00 đến 21:10 tối nay (30/09) để chuyển sang máy chủ mới."),
        dict(emoji="⏳", text="Trong lúc đó game có thể tạm dừng hoặc cần tải lại trang. Tiền, nhà, đồ và tiến độ giữ nguyên."),
    )),
    dict(version="0.9.8", date="2026-09-30", items=(
        dict(emoji="🔧", text="Từ 20:00 - 0:00 hôm nay hệ thống sẽ thực hiện nâng cấp hạ tầng."),
        dict(emoji="🎮", text="Người chơi vẫn có thể chơi bình thường nhưng sẽ ảnh hưởng một chút về trải nghiệm, xin vui lòng thông cảm."),
    )),
    dict(version="0.9.7", date="2026-09-30", items=(
        dict(emoji="🛠️", text="Đã sửa lỗi “Dữ kiện gốc của nhiệm vụ không hợp lệ”: rút tiền, mở ngày mới và làm việc lại bình thường."),
        dict(emoji="👕", text="Đơn shop quần áo làm dở từ trước vẫn giữ nguyên, bạn làm tiếp được."),
        dict(emoji="🙏", text="Xin lỗi vì sự bất tiện. Cảm ơn mọi người đã báo lỗi!"),
    )),
    dict(version="0.9.6", date="2026-09-30", items=(
        dict(emoji="🧋", text="Trà sữa: phiếu order ghim trên đầu, làm xong phần nào tích phần đó, chỉ một nút bước tiếp."),
        dict(emoji="👕", text="Shop quần áo, sửa đồ, thú cưng: thẻ “Khách cần” ghim sẵn, món khách cần xếp lên trước."),
        dict(emoji="⚡", text="Game phản hồi nhanh hơn, nhất là giờ đông người."),
        dict(emoji="📚", text="Nhật ký, sổ tiền, bảng tin cũ vẫn còn đủ: bấm “Xem cũ hơn” để xem lại."),
    )),
    dict(version="0.9.5", date="2026-09-30", items=(
        dict(emoji="🏠", text="Mua nhà: trả trước 30%, còn lại vay trả góp. Có nhà là hết tiền phòng.", go=dict(action="house")),
        dict(emoji="💞", text="Vợ chồng góp quỹ chung mua nhà, rồi về ở chung."),
        dict(emoji="🐷", text="Tiết kiệm có kỳ hạn tới 3 năm, lãi theo năm, tới hạn tự gửi tiếp.", go=dict(action="bank")),
        dict(emoji="👗", text="Tủ đồ: đổi tóc, áo quần, giày, phụ kiện. Làm ở Tiệm Áo Chỉ Mây được giảm 20%.", go=dict(action="jrWardrobe")),
        dict(emoji="😊", text="Khách kiên nhẫn hơn một chút."),
        dict(emoji="🪙", text="Tiền đền nhẹ hơn."),
        dict(emoji="💰", text="Nhập hàng, mua sắm, gửi rút tiền: Ví và Quỹ tiệm luôn hiện ở góc trên, thiếu bao nhiêu ghi rõ."),
        dict(emoji="📉", text="Hàng giao thiếu: bấm “Khiếu nại phần thiếu” ngay trong Kho để được hoàn tiền."),
        dict(emoji="🔧", text="Sửa đồ, pet care, shop quần áo: lời dặn và đồ khách đưa kèm hiện ngay chỗ chọn."),
        dict(emoji="🗣️", text="Người trong phố có chính kiến hơn: khen có gai, chê có lý."),
        dict(emoji="🧾", text="Màn hình yên hơn: thông báo từng dòng, Đánh giá, Tổng kết ngày và Sổ tiệm gọn gàng."),
        dict(emoji="⚡", text="Máy chủ cập nhật không làm mất thao tác, nhẹ hơn khi đông người chơi."),
    )),
)

MAX_ITEMS = 18
MAX_TEXT = 130
VERSION = re.compile(r"\d{1,3}(?:\.\d{1,3}){1,2}")
DATE = re.compile(r"20\d\d-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
ACTION = re.compile(r"[A-Za-z][A-Za-z0-9:_-]{0,31}")
DATA_JS = Path(__file__).resolve().parents[1] / "public" / "js" / "v4" / "whatsnew-data.js"


def parse(version: str) -> tuple[int, ...]:
    """"0.9.1" -> (0, 9, 1); "0.9" -> (0, 9, 0) so the two compare equal."""
    parts = tuple(int(x) for x in version.split("."))
    return parts + (0,) * (3 - len(parts))


def valid_seen(value) -> bool:
    """settings.whatsNewSeen: "" (nothing seen yet) or a release number. Only the shape is
    checked, not membership: a save must stay valid when a release is rolled back."""
    return isinstance(value, str) and (value == "" or bool(VERSION.fullmatch(value)))


def newer(a: str, b: str) -> str:
    """The later of two valid settings.whatsNewSeen values ("" is the earliest): a tab still
    running an older release can never lower what the player has already read."""
    if not a or not b:
        return a or b
    return b if parse(b) > parse(a) else a


def validate(entries=ENTRIES) -> None:
    """Raise ValueError when an entry is malformed or the list is not newest first."""
    if not entries:
        raise ValueError("whats_new: no entries")
    seen = set()
    for i, e in enumerate(entries):
        where = f"whats_new entry {i}"
        if not isinstance(e, dict) or set(e) != {"version", "date", "items"}:
            raise ValueError(f"{where}: needs exactly version, date, items")
        v, d, items = e["version"], e["date"], e["items"]
        if not isinstance(v, str) or not VERSION.fullmatch(v) or v in seen:
            raise ValueError(f"{where}: bad or repeated version {v!r}")
        seen.add(v)
        if not isinstance(d, str) or not DATE.fullmatch(d):
            raise ValueError(f"{where}: date must be YYYY-MM-DD")
        if i and not (parse(v) < parse(entries[i - 1]["version"]) and d <= entries[i - 1]["date"]):
            raise ValueError(f"{where}: entries must be newest first ({v} after {entries[i - 1]['version']})")
        if not isinstance(items, (list, tuple)) or not 1 <= len(items) <= MAX_ITEMS:
            raise ValueError(f"{where}: 1 to {MAX_ITEMS} items")
        for it in items:
            if not isinstance(it, dict) or not {"emoji", "text"} <= set(it) <= {"emoji", "text", "go"}:
                raise ValueError(f"{where}: an item needs emoji and text (go is optional)")
            if not isinstance(it["emoji"], str) or not 1 <= len(it["emoji"]) <= 8 or any(c.isalnum() for c in it["emoji"]):
                raise ValueError(f"{where}: emoji {it['emoji']!r}")
            t = it["text"]
            if not isinstance(t, str) or not 8 <= len(t) <= MAX_TEXT or t != t.strip() or "<" in t or "\n" in t:
                raise ValueError(f"{where}: text must be one plain line of 8-{MAX_TEXT} characters: {t!r}")
            if "go" in it:
                go = it["go"]
                if (not isinstance(go, dict) or not {"action"} <= set(go) <= {"action", "data"} or not ACTION.fullmatch(str(go["action"]))
                        or not isinstance(go.get("data", {}), dict)
                        or not all(isinstance(k, str) and re.fullmatch(r"[a-z][a-zA-Z0-9]{0,23}", k) and isinstance(x, str) for k, x in go.get("data", {}).items())):
                    raise ValueError(f"{where}: go must be dict(action=..., data={{str: str}})")


validate()
LATEST = ENTRIES[0]["version"]


def public() -> list[dict]:
    """JSON-ready copy for the browser."""
    return [dict(version=e["version"], date=e["date"], items=[dict(it) for it in e["items"]]) for e in ENTRIES]


def render_js() -> str:
    """public/js/v4/whatsnew-data.js: plain JSON after `export default`, one bullet per line."""
    dump = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    rows = []
    for e in public():
        items = ",\n".join("  " + dump(it) for it in e["items"])
        rows.append(f' {{"version":{dump(e["version"])},"date":{dump(e["date"])},"items":[\n{items}\n ]}}')
    body = "[\n" + ",\n".join(rows) + "\n]"
    return ("/* GENERATED by `python -m game.whats_new` from game/whats_new.py: edit that file, not this one.\n"
            " * Release notes for the \"Có gì mới\" card (whatsnew.js), newest first. Loaded only after the game is up. */\n"
            f"export default {body};\n")


if __name__ == "__main__":
    DATA_JS.write_text(render_js(), encoding="utf-8", newline="\n")
    print(f"wrote {DATA_JS.relative_to(DATA_JS.parents[3])} ({len(ENTRIES)} entries, latest {LATEST})")
