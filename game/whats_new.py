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
